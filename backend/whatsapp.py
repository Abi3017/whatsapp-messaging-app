"""All communication with the Meta WhatsApp Cloud API lives here.

The access token is only used in request headers in this file. It is never
returned to the frontend and never logged.
"""
import logging
import re

import requests

from config import Config

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15


class InvalidPhoneNumber(ValueError):
    pass


def normalize_phone(raw):
    """Strip spaces, dashes, '+' and leading zeros. WhatsApp expects country code + number."""
    digits = re.sub(r"\D", "", raw or "").lstrip("0")
    if not 8 <= len(digits) <= 15:
        raise InvalidPhoneNumber("Enter the number with country code, e.g. 919876543210")
    return digits


def _url(path):
    return f"{Config.META_API_BASE}/{Config.GRAPH_API_VERSION}/{path}"


def _headers():
    return {
        "Authorization": f"Bearer {Config.ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def _result_from_response(response):
    """Turn Meta's response into {ok, wamid, error_code, error_message}."""
    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.ok and data.get("messages"):
        return {"ok": True, "wamid": data["messages"][0].get("id")}

    error = data.get("error", {}) if isinstance(data, dict) else {}
    code = str(error.get("code", response.status_code))
    message = error.get("error_data", {}).get("details") or error.get("message") or "Unknown error from Meta"
    # Code 190 = expired/invalid token. Make the fix obvious.
    if code == "190":
        message = "Access token is invalid or expired. Generate a new one in Meta > WhatsApp > API Setup and update .env."
    log.warning("Meta API error code=%s http=%s: %s", code, response.status_code, message)
    return {"ok": False, "error_code": code, "error_message": message, "http_status": response.status_code}


def _post_message(payload):
    if not Config.ACCESS_TOKEN or not Config.PHONE_NUMBER_ID:
        return {"ok": False, "error_code": "config",
                "error_message": "Backend is missing WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID."}
    try:
        response = requests.post(
            _url(f"{Config.PHONE_NUMBER_ID}/messages"),
            headers=_headers(), json=payload, timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        log.error("Network error calling Meta: %s", type(exc).__name__)
        return {"ok": False, "error_code": "network",
                "error_message": "Could not reach the WhatsApp API. Check your internet connection."}
    return _result_from_response(response)


def send_text(to, text):
    """Free-form text. Only works inside the 24-hour customer service window."""
    return _post_message({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    })


def send_template(to, template_name, language_code="en_US", body_params=None):
    """Approved template. Works any time, including outside the 24-hour window."""
    template = {"name": template_name, "language": {"code": language_code}}
    if body_params:
        template["components"] = [{
            "type": "body",
            "parameters": [{"type": "text", "text": str(p)} for p in body_params],
        }]
    return _post_message({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template,
    })


def list_templates():
    """Approved templates from the WhatsApp Business Account, for the send form dropdown."""
    if not Config.ACCESS_TOKEN or not Config.BUSINESS_ACCOUNT_ID:
        return {"ok": False, "error_message": "WHATSAPP_BUSINESS_ACCOUNT_ID is not set.", "templates": []}
    try:
        response = requests.get(
            _url(f"{Config.BUSINESS_ACCOUNT_ID}/message_templates"),
            headers=_headers(),
            params={"fields": "name,language,status,category,components", "limit": 100},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        log.error("Could not load templates: %s", type(exc).__name__)
        return {"ok": False, "error_message": "Could not load templates from Meta.", "templates": []}

    if not response.ok:
        return {"ok": False, "error_message": data.get("error", {}).get("message", "Meta error"), "templates": []}

    templates = []
    for t in data.get("data", []):
        if t.get("status") != "APPROVED":
            continue
        body = next((c.get("text", "") for c in t.get("components", []) if c.get("type") == "BODY"), "")
        templates.append({
            "name": t["name"],
            "language": t.get("language", "en_US"),
            "category": t.get("category"),
            "body": body,
            # Count {{1}}, {{2}} ... so the form knows how many inputs to show
            "param_count": len(set(re.findall(r"\{\{(\d+)\}\}", body))),
        })
    return {"ok": True, "templates": templates}


def render_template_body(body, params):
    """Fill {{1}}, {{2}} with values so the inbox shows the real text that was sent."""
    def replace(match):
        index = int(match.group(1)) - 1
        return str(params[index]) if 0 <= index < len(params) else match.group(0)
    return re.sub(r"\{\{(\d+)\}\}", replace, body or "")
