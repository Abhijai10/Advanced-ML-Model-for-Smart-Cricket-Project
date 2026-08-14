"""Observability and runtime security tests."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.observability import METRICS, initialize_sentry, pseudonymous_user_id


def test_security_headers_are_applied_to_api_responses() -> None:
    response = TestClient(app).get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"


def test_sensitive_endpoints_default_to_no_store() -> None:
    response = TestClient(app).post("/analyze", headers={"x-request-id": "security-test"})
    assert response.headers["cache-control"] == "no-store"


def test_metrics_endpoint_reports_requests_without_secrets() -> None:
    METRICS.reset()
    client = TestClient(app)
    client.get("/health", headers={"authorization": "Bearer secret-token"})
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "smart_cricket_request_total" in body
    assert "secret-token" not in body
    assert "authorization" not in body.lower()


def test_unexpected_exception_response_is_safe_and_logs_no_authorization(caplog) -> None:
    client = TestClient(app)
    caplog.set_level(logging.ERROR, logger="smart_cricket.api")
    with patch("backend.api.routes.api_health", side_effect=RuntimeError("internal path /tmp/private")):
        response = client.get("/health", headers={"authorization": "Bearer never-log-this"})
    assert response.status_code == 500
    payload = response.json()
    assert payload["error_code"] == "internal_error"
    assert "Traceback" not in response.text
    assert "/tmp/private" not in response.text
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "never-log-this" not in log_text
    assert "Authorization" not in log_text


def test_pseudonymous_user_hash_is_stable_and_not_raw_user_id() -> None:
    first = pseudonymous_user_id("user-123")
    second = pseudonymous_user_id("user-123")
    assert first == second
    assert first != "user-123"
    assert len(first or "") == 16


def test_sentry_initialization_is_optional_and_redacts_headers() -> None:
    captured = {}
    fake_sentry = SimpleNamespace(init=Mock(side_effect=lambda **kwargs: captured.update(kwargs)))
    with patch("backend.api.observability.SETTINGS", SimpleNamespace(sentry_dsn="https://dsn.example")), patch.dict(
        "sys.modules",
        {"sentry_sdk": fake_sentry},
    ):
        assert initialize_sentry() is True
    event = {"request": {"headers": {"Authorization": "Bearer secret", "Cookie": "session=secret", "x-ok": "ok"}}}
    scrubbed = captured["before_send"](event, {})
    assert scrubbed["request"]["headers"]["Authorization"] == "[redacted]"
    assert scrubbed["request"]["headers"]["Cookie"] == "[redacted]"
    assert scrubbed["request"]["headers"]["x-ok"] == "ok"
