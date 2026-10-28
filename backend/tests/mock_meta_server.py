"""A tiny fake of the Meta Graph API for local end-to-end testing without a real token.

Run:  python tests/mock_meta_server.py      (listens on port 8099)
Then start the backend with META_API_BASE=http://localhost:8099
"""
import itertools

from flask import Flask, jsonify, request

app = Flask(__name__)
counter = itertools.count(1)
sent = []


@app.post("/<version>/<phone_id>/messages")
def messages(version, phone_id):
    if request.headers.get("Authorization") != "Bearer test-token":
        return jsonify({"error": {"message": "Error validating access token: Session has expired",
                                  "type": "OAuthException", "code": 190}}), 401
    body = request.get_json()
    if body.get("to") == "910000000000":
        return jsonify({"error": {"message": "(#131030) Recipient phone number not in allowed list",
                                  "code": 131030,
                                  "error_data": {"details": "Recipient phone number not in allowed list"}}}), 400
    sent.append(body)
    return jsonify({"messaging_product": "whatsapp",
                    "contacts": [{"input": body["to"], "wa_id": body["to"]}],
                    "messages": [{"id": f"wamid.MOCK{next(counter)}"}]})


@app.get("/<version>/<waba_id>/message_templates")
def templates(version, waba_id):
    return jsonify({"data": [
        {"name": "hello_world", "language": "en_US", "status": "APPROVED", "category": "UTILITY",
         "components": [{"type": "BODY", "text": "Hello World"}]},
        {"name": "order_update", "language": "en", "status": "APPROVED", "category": "UTILITY",
         "components": [{"type": "BODY", "text": "Hi {{1}}, your order {{2}} is ready for pickup."}]},
        {"name": "pending_one", "language": "en", "status": "PENDING", "category": "MARKETING",
         "components": [{"type": "BODY", "text": "Not approved yet"}]},
    ]})


@app.get("/sent")
def sent_log():
    return jsonify(sent)


if __name__ == "__main__":
    app.run(port=8099)
