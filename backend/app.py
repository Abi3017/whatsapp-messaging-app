"""Flask app: REST API for the dashboard + the Meta webhook.

Routes
  GET  /api/health          config check (names of missing settings only)
  GET  /api/conversations   one row per customer, latest first
  GET  /api/messages        all messages newest first (?phone= to filter)
  GET  /api/templates       approved templates from Meta
  POST /api/send-text       free-form text (inside 24h window)
  POST /api/send-template   approved template with variables
  GET  /webhook             Meta verification handshake
  POST /webhook             incoming messages + status updates from Meta
"""
import hashlib
import hmac
import logging
import os
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import auto_reply
import db
import whatsapp
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")


def run_in_background(fn, *args):
    """Run slow work (auto-reply) after we've answered Meta. Tests replace this to run inline."""
    threading.Thread(target=fn, args=args, daemon=True).start()


def create_app():
    app = Flask(__name__, static_folder=None)
    CORS(app, resources={r"/api/*": {"origins": [Config.FRONTEND_ORIGIN]}})
    db.init_db(Config.DATABASE_URL)

    missing = Config.missing()
    if missing:
        log.warning("Missing settings: %s (see backend/.env.example)", ", ".join(missing))

    # ---------- Dashboard API ----------

    @app.get("/api/health")
    def health():
        return jsonify({"ok": not missing, "missing_settings": missing})

    @app.get("/api/conversations")
    def conversations():
        return jsonify(db.list_conversations())

    @app.get("/api/messages")
    def get_messages():
        phone = request.args.get("phone")
        return jsonify(db.list_messages(phone=phone))

    @app.get("/api/templates")
    def templates():
        return jsonify(whatsapp.list_templates())

    @app.post("/api/send-text")
    def send_text():
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"ok": False, "error_message": "Message text is empty."}), 400
        try:
            to = whatsapp.normalize_phone(data.get("to"))
        except whatsapp.InvalidPhoneNumber as exc:
            return jsonify({"ok": False, "error_message": str(exc)}), 400

        result = whatsapp.send_text(to, text)
        _store_outgoing(to, text, "text", result)
        return jsonify(result), (200 if result["ok"] else 502)

    @app.post("/api/send-template")
    def send_template():
        data = request.get_json(silent=True) or {}
        name = (data.get("template") or "").strip()
        if not name:
            return jsonify({"ok": False, "error_message": "Choose a template."}), 400
        params = [str(p).strip() for p in (data.get("params") or [])]
        if any(p == "" for p in params):
            return jsonify({"ok": False, "error_message": "Fill in every template variable."}), 400
        try:
            to = whatsapp.normalize_phone(data.get("to"))
        except whatsapp.InvalidPhoneNumber as exc:
            return jsonify({"ok": False, "error_message": str(exc)}), 400

        result = whatsapp.send_template(to, name, data.get("language") or "en_US", params)
        body = whatsapp.render_template_body(data.get("body"), params) or f"[template: {name}] {' | '.join(params)}"
        _store_outgoing(to, body, "template", result)
        return jsonify(result), (200 if result["ok"] else 502)

    # ---------- Meta webhook ----------

    @app.get("/webhook")
    def verify_webhook():
        """Meta calls this once when you click Verify in the dashboard."""
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge", "")
        if mode == "subscribe" and Config.VERIFY_TOKEN and hmac.compare_digest(token or "", Config.VERIFY_TOKEN):
            log.info("Webhook verified by Meta")
            return challenge, 200
        log.warning("Webhook verification failed (wrong verify token or mode)")
        return "Forbidden", 403

    @app.post("/webhook")
    def receive_webhook():
        raw = request.get_data()
        if not _signature_is_valid(raw, request.headers.get("X-Hub-Signature-256", "")):
            log.warning("Rejected webhook with invalid signature")
            return "Invalid signature", 403

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            log.warning("Webhook body is not JSON; ignoring")
            return "OK", 200  # Always 200 so Meta doesn't keep retrying junk

        try:
            _handle_payload(payload)
        except Exception:  # Never crash on unexpected shapes; log and acknowledge
            log.exception("Error while processing webhook payload")
        return "OK", 200

    # ---------- Serve the built React app (production) ----------

    if os.path.isdir(FRONTEND_DIST):
        @app.get("/")
        @app.get("/<path:path>")
        def frontend(path="index.html"):
            full = os.path.join(FRONTEND_DIST, path)
            if path != "index.html" and os.path.isfile(full):
                return send_from_directory(FRONTEND_DIST, path)
            return send_from_directory(FRONTEND_DIST, "index.html")

    return app


# ---------- Helpers ----------

def _store_outgoing(to, body, msg_type, result):
    db.save_outgoing(
        phone=to, body=body, msg_type=msg_type,
        wamid=result.get("wamid"),
        status="sent" if result["ok"] else "failed",
        error_code=result.get("error_code"),
        error_message=result.get("error_message"),
    )


def _signature_is_valid(raw_body, header):
    """Meta signs every webhook with your App Secret. Skip only if no secret is configured."""
    if not Config.APP_SECRET:
        return True
    expected = "sha256=" + hmac.new(Config.APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")


def _handle_payload(payload):
    if payload.get("object") != "whatsapp_business_account":
        log.info("Ignoring webhook for object=%s", payload.get("object"))
        return

    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            if change.get("field") != "messages":
                log.info("Ignoring webhook field=%s", change.get("field"))
                continue
            contacts = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts") or []}
            for message in value.get("messages") or []:
                _handle_incoming(message, contacts)
            for status in value.get("statuses") or []:
                _handle_status(status)


def _handle_incoming(message, contacts):
    phone = message.get("from")
    wamid = message.get("id")
    if not phone or not wamid:
        log.warning("Incoming message without sender or id; skipped")
        return

    msg_type = message.get("type", "unknown")
    if msg_type == "text":
        text = (message.get("text") or {}).get("body", "")
    elif msg_type == "button":
        text = (message.get("button") or {}).get("text", "")
    else:
        text = f"[{msg_type} message]"

    timestamp = None
    if str(message.get("timestamp", "")).isdigit():
        timestamp = datetime.fromtimestamp(int(message["timestamp"]), tz=timezone.utc)

    is_new = db.save_incoming(wamid, phone, text, msg_type, contacts.get(phone), timestamp)
    if not is_new:
        log.info("Duplicate webhook for %s ignored (no second auto-reply)", wamid)
        return
    log.info("Incoming %s message from %s", msg_type, _mask(phone))
    run_in_background(_send_auto_reply, phone, text)


def _send_auto_reply(phone, text):
    reply = auto_reply.get_reply(text)
    result = whatsapp.send_text(phone, reply)
    _store_outgoing(phone, reply, "text", result)


def _handle_status(status):
    wamid = status.get("id")
    new_status = status.get("status")
    if not wamid or not new_status:
        return
    code = message = None
    if new_status == "failed" and status.get("errors"):
        err = status["errors"][0]
        code = str(err.get("code"))
        message = (err.get("error_data") or {}).get("details") or err.get("title") or err.get("message")
    changed = db.update_status(wamid, new_status, code, message)
    log.info("Status %s for %s (%s)", new_status, wamid[-12:], "updated" if changed else "no change")


def _mask(phone):
    """Log only the last 4 digits of customer numbers."""
    return "*" * max(len(phone) - 4, 0) + phone[-4:]


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
