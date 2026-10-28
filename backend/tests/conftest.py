import hashlib
import hmac
import json
import os
import sys

import pytest

# Test settings must be set before config.py is imported. No real token is used.
os.environ.update({
    "WHATSAPP_ACCESS_TOKEN": "test-token",
    "WHATSAPP_PHONE_NUMBER_ID": "123456789",
    "WHATSAPP_BUSINESS_ACCOUNT_ID": "987654321",
    "WEBHOOK_VERIFY_TOKEN": "my-verify-token",
    "META_APP_SECRET": "test-app-secret",
    "DATABASE_URL": "sqlite:///:memory:",
})

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._data


class FakeMeta:
    """Stands in for requests.post/get to graph.facebook.com and records every call."""

    def __init__(self):
        self.calls = []
        self.next_response = None
        self.counter = 0

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        if self.next_response:
            resp, self.next_response = self.next_response, None
            return resp
        self.counter += 1
        return FakeResponse(200, {"messages": [{"id": f"wamid.out{self.counter}"}]})


@pytest.fixture
def fake_meta(monkeypatch):
    import whatsapp
    fake = FakeMeta()
    monkeypatch.setattr(whatsapp.requests, "post", fake.post)
    return fake


@pytest.fixture
def client(fake_meta, monkeypatch):
    import app as app_module
    import db
    db.init_db("sqlite:///:memory:")  # fresh database per test
    monkeypatch.setattr(app_module, "run_in_background", lambda fn, *args: fn(*args))
    return app_module.app.test_client()


def signed_post(client, payload, secret="test-app-secret"):
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhook", data=body, headers={
        "Content-Type": "application/json", "X-Hub-Signature-256": sig,
    })
