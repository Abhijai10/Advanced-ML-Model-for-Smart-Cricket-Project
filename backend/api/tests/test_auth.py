"""Direct JWT verification tests for API authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.api import services


def _b64(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _jwt(header: dict, payload: dict, secret: str = "test-secret") -> str:
    header_b64 = _b64(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode("ascii"), hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64(signature)}"


def _settings(**overrides):
    base = {
        "require_auth": True,
        "supabase_jwt_secret": "test-secret",
        "supabase_url": None,
        "jwt_audience": "authenticated",
        "jwt_issuer": "https://issuer.example",
        "jwks_timeout_seconds": 1,
        "jwks_cache_ttl_seconds": 600,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class AuthVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        services._JWKS_CACHE["loaded_at"] = 0.0
        services._JWKS_CACHE["keys"] = []
        self.payload = {
            "sub": "user-1",
            "exp": int(time.time()) + 3600,
            "aud": "authenticated",
            "iss": "https://issuer.example",
        }

    def test_valid_hs256(self) -> None:
        with patch("backend.api.services.SETTINGS", _settings()):
            claims = services._verify_hs256_jwt(_jwt({"alg": "HS256"}, self.payload), "test-secret")
        self.assertEqual(claims["sub"], "user-1")

    def test_invalid_hs256_signature(self) -> None:
        with patch("backend.api.services.SETTINGS", _settings()):
            with self.assertRaises(services.APIValidationError) as ctx:
                services._verify_hs256_jwt(_jwt({"alg": "HS256"}, self.payload), "wrong-secret")
        self.assertEqual(ctx.exception.error_code, "invalid_token")

    def test_missing_signature_segment(self) -> None:
        token = ".".join(_jwt({"alg": "HS256"}, self.payload).split(".")[:2])
        with patch("backend.api.services.SETTINGS", _settings()):
            with self.assertRaises(services.APIValidationError):
                services._verify_hs256_jwt(token, "test-secret")

    def test_malformed_header(self) -> None:
        token = f"not-json.{_b64(json.dumps(self.payload).encode())}.sig"
        with patch("backend.api.services.SETTINGS", _settings()):
            with self.assertRaises(services.APIValidationError):
                services._verify_hs256_jwt(token, "test-secret")

    def test_expired_future_nbf_missing_sub_wrong_audience_wrong_issuer(self) -> None:
        cases = [
            ({**self.payload, "exp": int(time.time()) - 1}, "expired_token"),
            ({**self.payload, "nbf": int(time.time()) + 3600}, "invalid_token"),
            ({**self.payload, "sub": ""}, "invalid_token"),
            ({**self.payload, "aud": "wrong"}, "invalid_token"),
            ({**self.payload, "iss": "wrong"}, "invalid_token"),
        ]
        with patch("backend.api.services.SETTINGS", _settings()):
            for payload, code in cases:
                with self.subTest(code=code):
                    with self.assertRaises(services.APIValidationError) as ctx:
                        services._verify_hs256_jwt(_jwt({"alg": "HS256"}, payload), "test-secret")
                    self.assertEqual(ctx.exception.error_code, code)

    def test_unsupported_algorithm(self) -> None:
        with patch("backend.api.services.SETTINGS", _settings()):
            with self.assertRaises(services.APIValidationError):
                services._verify_hs256_jwt(_jwt({"alg": "none"}, self.payload), "test-secret")

    def test_jwks_endpoint_timeout_or_http_failure_is_controlled(self) -> None:
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            side_effect=TimeoutError("timeout"),
        ):
            with self.assertRaises(services.JWKSUnavailableError):
                services._load_jwks()

    def test_jwks_invalid_json_is_controlled(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self) -> bytes:
                return b"{not-json"

        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            return_value=FakeResponse(),
        ):
            with self.assertRaises(services.JWKSUnavailableError):
                services._load_jwks()


if __name__ == "__main__":
    unittest.main()
