from types import SimpleNamespace

import pytest
from notifyvia_email.v3 import SendResult

import app.services as email_service


class FakeClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            ok=self.result is SendResult.EMAIL_PROVISIONING,
            result=self.result,
            errors=None,
        )


@pytest.fixture
def fake_email(monkeypatch):
    def install(result):
        client = FakeClient(result)
        monkeypatch.setenv("EMAIL_DEV_MODE", "0")
        monkeypatch.setattr(email_service, "_client", lambda: client)
        return client

    return install


def test_login_email_uses_daily_rate_limiter(client, fake_email):
    fake = fake_email(SendResult.EMAIL_PROVISIONING)
    response = client.post(
        "/api/login",
        json={"email_address": "a@example.com"},
        headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"},
    )
    assert response.status_code == 200
    call = fake.calls[0]
    assert call["to"] == "a@example.com"
    assert call["enable_rate_limiter"] is True
    assert call["limit"] == 5
    assert call["within_seconds"] == 86400
    assert call["ipv4_address"] == "203.0.113.7"
    assert "/auth/" in call["html"]


def test_rate_limit_is_reported(client, fake_email):
    fake_email(SendResult.RATE_LIMIT_EXCEEDED)
    response = client.post(
        "/api/login", json={"email_address": "a@example.com"}
    )
    assert response.status_code == 429
    assert response.json["status"] == "rate_limited"
    assert "5 emails a day" in response.json["message"]


def test_other_failures_are_reported(client, fake_email):
    fake_email(SendResult.CONNECTION_ERROR)
    response = client.post(
        "/api/login", json={"email_address": "a@example.com"}
    )
    assert response.status_code == 502
    assert response.json["status"] == "error"
