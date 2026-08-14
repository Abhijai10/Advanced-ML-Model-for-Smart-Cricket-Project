"""Production configuration and readiness tests."""

from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.config import APISettings, normalize_origins, production_config_report
from backend.api.services import api_health, api_readiness


def _settings(**overrides):
    base = APISettings(environment="test")
    return replace(base, **overrides)


class ConfigReadinessTests(unittest.TestCase):
    def test_invalid_environment_fails_fast(self) -> None:
        with self.assertRaises(ValueError):
            APISettings(environment="demo")

    def test_cors_origins_are_normalized_without_wildcard_expansion(self) -> None:
        self.assertEqual(
            normalize_origins(("https://app.example.com/", "https://app.example.com", "*")),
            ("https://app.example.com", "*"),
        )

    def test_production_rejects_wildcard_cors_and_memory_rate_limit(self) -> None:
        report = production_config_report(
            _settings(
                environment="production",
                allowed_origins=("*",),
                require_auth=True,
                supabase_url="https://project.supabase.co",
                jwt_audience="authenticated",
                jwt_issuer="https://project.supabase.co/auth/v1",
                supabase_service_role_key="service-secret",
                audio_signing_secret="a" * 40,
                rate_limit_backend="memory",
            ),
        )
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("wildcard_cors_origin", codes)
        self.assertIn("memory_rate_limit_in_production", codes)

    def test_staging_secure_config_passes(self) -> None:
        report = production_config_report(
            _settings(
                environment="staging",
                allowed_origins=("https://staging.smartcricket.example",),
                require_auth=True,
                supabase_url="https://project.supabase.co",
                jwt_audience="authenticated",
                jwt_issuer="https://project.supabase.co/auth/v1",
                supabase_service_role_key="service-secret",
                audio_signing_secret="a" * 40,
                rate_limit_backend="gateway",
            ),
        )
        self.assertEqual(report["issues"], [])

    def test_readiness_includes_production_configuration_without_affecting_health(self) -> None:
        settings = _settings(
            environment="production",
            allowed_origins=("*",),
            require_auth=True,
            rate_limit_backend="memory",
        )
        with patch("backend.api.services.SETTINGS", settings):
            health = api_health()
            ready = api_readiness()
        self.assertEqual(health["status"], "ok")
        self.assertIn("production_configuration", ready["checks"])
        self.assertFalse(ready["checks"]["production_configuration"]["ok"])

    def test_capabilities_reports_safe_api_version_only(self) -> None:
        response = TestClient(app).get("/capabilities")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("api_version", payload)
        self.assertNotIn("supabase_service_role_key", payload)
        self.assertNotIn("audio_signing_secret", payload)


if __name__ == "__main__":
    unittest.main()
