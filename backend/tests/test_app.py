from conftest import FakeResponse, signed_post


def incoming_payload(text, wamid="wamid.in1", phone="919876543210", msg_type="text"):
    message = {"from": phone, "id": wamid, "timestamp": "1761580800", "type": msg_type}
    if msg_type == "text":
        message["text"] = {"body": text}
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "987654321", "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"phone_number_id": "123456789"},
            "contacts": [{"wa_id": phone, "profile": {"name": "Abinaya"}}],
            "messages": [message],
        }}]}],
    }


def status_payload(wamid, status, errors=None):
    s = {"id": wamid, "status": status, "timestamp": "1761580900", "recipient_id": "919876543210"}
    if errors:
        s["errors"] = errors
    return {"object": "whatsapp_business_account", "entry": [{"id": "1", "changes": [
        {"field": "messages", "value": {"statuses": [s]}}]}]}


# ---------- Webhook verification (GET) ----------

def test_verify_webhook_success(client):
    r = client.get("/webhook?hub.mode=subscribe&hub.verify_token=my-verify-token&hub.challenge=12345")
    assert r.status_code == 200
    assert r.data == b"12345"


def test_verify_webhook_wrong_token(client):
    r = client.get("/webhook?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=12345")
    assert r.status_code == 403


# ---------- Incoming messages + auto-reply ----------

def test_incoming_message_saved_and_auto_replied(client, fake_meta):
    r = signed_post(client, incoming_payload("What is the PRICE?"))
    assert r.status_code == 200

    msgs = client.get("/api/messages").get_json()
    assert len(msgs) == 2
    reply, incoming = msgs  # newest first
    assert incoming["direction"] == "incoming" and incoming["body"] == "What is the PRICE?"
    assert reply["direction"] == "outgoing" and "₹499" in reply["body"]
    assert reply["status"] == "sent" and reply["wamid"] == "wamid.out1"

    sent = fake_meta.calls[0]
    assert sent["url"].endswith("/123456789/messages")
    assert sent["json"]["to"] == "919876543210"
    assert sent["headers"]["Authorization"] == "Bearer test-token"


def test_fallback_reply_for_unknown_text(client, fake_meta):
    signed_post(client, incoming_payload("asdf qwerty"))
    assert "Try *hi*" in fake_meta.calls[0]["json"]["text"]["body"]


def test_duplicate_webhook_does_not_reply_twice(client, fake_meta):
    signed_post(client, incoming_payload("hi"))
    signed_post(client, incoming_payload("hi"))
    assert len(fake_meta.calls) == 1
    assert len(client.get("/api/messages").get_json()) == 2


def test_non_text_message_is_stored(client, fake_meta):
    signed_post(client, incoming_payload(None, msg_type="image"))
    incoming = client.get("/api/messages").get_json()[-1]
    assert incoming["body"] == "[image message]"


def test_invalid_signature_rejected(client, fake_meta):
    r = signed_post(client, incoming_payload("hi"), secret="wrong-secret")
    assert r.status_code == 403
    assert client.get("/api/messages").get_json() == []


def test_unexpected_payloads_do_not_crash(client):
    for weird in [{}, {"object": "page"}, {"object": "whatsapp_business_account", "entry": "oops"},
                  {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": None}]}]},
                  {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages",
                      "value": {"messages": [{"type": "text"}]}}]}]}]:
        assert signed_post(client, weird).status_code == 200
    # Non-JSON body (signed) also gets 200
    import hashlib, hmac
    body = b"not json"
    sig = "sha256=" + hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()
    assert client.post("/webhook", data=body, headers={"X-Hub-Signature-256": sig}).status_code == 200


# ---------- Status updates ----------

def test_status_updates_flow(client, fake_meta):
    client.post("/api/send-text", json={"to": "+91 98765 43210", "text": "Hello"})
    signed_post(client, status_payload("wamid.out1", "delivered"))
    assert client.get("/api/messages").get_json()[0]["status"] == "delivered"
    signed_post(client, status_payload("wamid.out1", "read"))
    signed_post(client, status_payload("wamid.out1", "delivered"))  # late, must not downgrade
    assert client.get("/api/messages").get_json()[0]["status"] == "read"


def test_failed_status_records_error(client, fake_meta):
    client.post("/api/send-text", json={"to": "919876543210", "text": "Hello"})
    signed_post(client, status_payload("wamid.out1", "failed", [
        {"code": 131047, "title": "Re-engagement message",
         "error_data": {"details": "More than 24 hours have passed since the customer last replied."}}]))
    msg = client.get("/api/messages").get_json()[0]
    assert msg["status"] == "failed" and msg["error_code"] == "131047"
    assert "24 hours" in msg["error_message"]


# ---------- Sending ----------

def test_send_template_with_variables(client, fake_meta):
    r = client.post("/api/send-template", json={
        "to": "919876543210", "template": "order_update", "language": "en_US",
        "params": ["Abinaya", "#1234"], "body": "Hi {{1}}, your order {{2}} is ready.",
    })
    assert r.status_code == 200 and r.get_json()["ok"] is True
    tpl = fake_meta.calls[0]["json"]["template"]
    assert tpl["name"] == "order_update"
    assert [p["text"] for p in tpl["components"][0]["parameters"]] == ["Abinaya", "#1234"]
    assert client.get("/api/messages").get_json()[0]["body"] == "Hi Abinaya, your order #1234 is ready."


def test_send_template_without_variables(client, fake_meta):
    r = client.post("/api/send-template", json={"to": "919876543210", "template": "hello_world"})
    assert r.status_code == 200
    assert "components" not in fake_meta.calls[0]["json"]["template"]


def test_invalid_phone_rejected_before_calling_meta(client, fake_meta):
    r = client.post("/api/send-text", json={"to": "12", "text": "hi"})
    assert r.status_code == 400
    assert "country code" in r.get_json()["error_message"]
    assert fake_meta.calls == []


def test_missing_template_variable_rejected(client, fake_meta):
    r = client.post("/api/send-template", json={"to": "919876543210", "template": "x", "params": ["a", ""]})
    assert r.status_code == 400 and fake_meta.calls == []


def test_expired_token_returns_clear_error(client, fake_meta):
    fake_meta.next_response = FakeResponse(401, {"error": {
        "message": "Error validating access token: Session has expired", "type": "OAuthException", "code": 190}})
    r = client.post("/api/send-text", json={"to": "919876543210", "text": "hi"})
    body = r.get_json()
    assert r.status_code == 502 and body["ok"] is False and body["error_code"] == "190"
    assert "expired" in body["error_message"]
    assert "test-token" not in r.get_data(as_text=True)  # token never leaks to the client
    assert client.get("/api/messages").get_json()[0]["status"] == "failed"


def test_recipient_not_allowed_error(client, fake_meta):
    fake_meta.next_response = FakeResponse(400, {"error": {
        "message": "(#131030) Recipient phone number not in allowed list", "code": 131030,
        "error_data": {"details": "Recipient phone number not in allowed list"}}})
    body = client.post("/api/send-text", json={"to": "919876543210", "text": "hi"}).get_json()
    assert body["error_code"] == "131030" and "allowed list" in body["error_message"]


def test_network_failure_does_not_crash(client, monkeypatch):
    import requests
    import whatsapp

    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(whatsapp.requests, "post", boom)
    r = client.post("/api/send-text", json={"to": "919876543210", "text": "hi"})
    assert r.status_code == 502 and r.get_json()["error_code"] == "network"


def test_conversations_endpoint(client, fake_meta):
    signed_post(client, incoming_payload("hours", wamid="wamid.a", phone="911111111111"))
    convs = client.get("/api/conversations").get_json()
    assert len(convs) == 1 and convs[0]["contact_name"] == "Abinaya"


def test_health_reports_only_names(client):
    body = client.get("/api/health").get_json()
    assert body == {"ok": True, "missing_settings": []}
