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

from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, utils
from cryptography.hazmat.primitives import hashes

from backend.api import services


def _b64(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _jwt(header: dict, payload: dict, secret: str = "test-secret") -> str:
    header_b64 = _b64(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode("ascii"), hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64(signature)}"


def _rsa_fixture(kid: str = "rsa-1") -> tuple[rsa.RSAPrivateKey, dict]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "alg": "RS256",
        "n": _b64(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")),
        "e": _b64(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")),
    }
    return private_key, jwk


def _ec_fixture(kid: str = "ec-1") -> tuple[ec.EllipticCurvePrivateKey, dict]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public = private_key.public_key().public_numbers()
    jwk = {
        "kty": "EC",
        "kid": kid,
        "alg": "ES256",
        "crv": "P-256",
        "x": _b64(public.x.to_bytes(32, "big")),
        "y": _b64(public.y.to_bytes(32, "big")),
    }
    return private_key, jwk


def _asymmetric_jwt(header: dict, payload: dict, private_key) -> str:
    header_b64 = _b64(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    if header["alg"] == "RS256":
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    elif header["alg"] == "ES256":
        der = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        r, s = utils.decode_dss_signature(der)
        signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    else:
        raise ValueError("unsupported test algorithm")
    return f"{header_b64}.{payload_b64}.{_b64(signature)}"


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self) -> bytes:
        return self.payload


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

    def test_valid_rs256(self) -> None:
        private_key, jwk = _rsa_fixture()
        token = _asymmetric_jwt({"alg": "RS256", "kid": jwk["kid"]}, self.payload, private_key)
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            return_value=FakeResponse(json.dumps({"keys": [jwk]}).encode()),
        ):
            claims = services._verify_asymmetric_jwt(token)
        self.assertEqual(claims["sub"], "user-1")

    def test_invalid_rs256_signature(self) -> None:
        private_key, jwk = _rsa_fixture()
        wrong_private_key, _ = _rsa_fixture("wrong")
        token = _asymmetric_jwt({"alg": "RS256", "kid": jwk["kid"]}, self.payload, wrong_private_key)
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            return_value=FakeResponse(json.dumps({"keys": [jwk]}).encode()),
        ):
            with self.assertRaises(services.APIValidationError) as ctx:
                services._verify_asymmetric_jwt(token)
        self.assertEqual(ctx.exception.error_code, "invalid_token")

    def test_unknown_kid_refreshes_jwks_for_key_rotation(self) -> None:
        private_key, rotated_jwk = _rsa_fixture("rotated")
        token = _asymmetric_jwt({"alg": "RS256", "kid": "rotated"}, self.payload, private_key)
        services._JWKS_CACHE["loaded_at"] = time.time()
        services._JWKS_CACHE["keys"] = [{"kid": "old", "alg": "RS256", "kty": "RSA", "n": "AQ", "e": "AQ"}]
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            return_value=FakeResponse(json.dumps({"keys": [rotated_jwk]}).encode()),
        ) as urlopen:
            claims = services._verify_asymmetric_jwt(token)
        self.assertEqual(claims["sub"], "user-1")
        urlopen.assert_called_once()

    def test_empty_jwks_keys_rejects_token(self) -> None:
        private_key, jwk = _rsa_fixture()
        token = _asymmetric_jwt({"alg": "RS256", "kid": jwk["kid"]}, self.payload, private_key)
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            return_value=FakeResponse(json.dumps({"keys": []}).encode()),
        ):
            with self.assertRaises(services.APIValidationError) as ctx:
                services._verify_asymmetric_jwt(token)
        self.assertEqual(ctx.exception.error_code, "invalid_token")

    def test_valid_es256(self) -> None:
        private_key, jwk = _ec_fixture()
        token = _asymmetric_jwt({"alg": "ES256", "kid": jwk["kid"]}, self.payload, private_key)
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            return_value=FakeResponse(json.dumps({"keys": [jwk]}).encode()),
        ):
            claims = services._verify_asymmetric_jwt(token)
        self.assertEqual(claims["sub"], "user-1")

    def test_invalid_es256_signature(self) -> None:
        private_key, jwk = _ec_fixture()
        wrong_private_key, _ = _ec_fixture("wrong")
        token = _asymmetric_jwt({"alg": "ES256", "kid": jwk["kid"]}, self.payload, wrong_private_key)
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            return_value=FakeResponse(json.dumps({"keys": [jwk]}).encode()),
        ):
            with self.assertRaises(services.APIValidationError) as ctx:
                services._verify_asymmetric_jwt(token)
        self.assertEqual(ctx.exception.error_code, "invalid_token")

    def test_malformed_es256_signature(self) -> None:
        private_key, jwk = _ec_fixture()
        token = _asymmetric_jwt({"alg": "ES256", "kid": jwk["kid"]}, self.payload, private_key)
        header_b64, payload_b64, _signature_b64 = token.split(".")
        malformed = f"{header_b64}.{payload_b64}.{_b64(b'short')}"
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            return_value=FakeResponse(json.dumps({"keys": [jwk]}).encode()),
        ):
            with self.assertRaises(services.APIValidationError) as ctx:
                services._verify_asymmetric_jwt(malformed)
        self.assertEqual(ctx.exception.error_code, "invalid_token")

    def test_asymmetric_route_level_jwks_outage_returns_503(self) -> None:
        class RequestState:
            request_id = "request-1"

        request = SimpleNamespace(state=RequestState())
        private_key, jwk = _rsa_fixture()
        token = _asymmetric_jwt({"alg": "RS256", "kid": jwk["kid"]}, self.payload, private_key)
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            side_effect=TimeoutError("timeout"),
        ):
            with self.assertRaises(Exception) as ctx:
                services.enforce_auth(request, authorization=f"Bearer {token}")
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail["error_code"], "jwks_unavailable")

    def test_jwks_endpoint_timeout_or_http_failure_is_controlled(self) -> None:
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            side_effect=TimeoutError("timeout"),
        ):
            with self.assertRaises(services.JWKSUnavailableError):
                services._load_jwks()

    def test_jwks_invalid_json_is_controlled(self) -> None:
        with patch("backend.api.services.SETTINGS", _settings(supabase_jwt_secret=None, supabase_url="https://supabase.example")), patch(
            "backend.api.services.urllib.request.urlopen",
            return_value=FakeResponse(b"{not-json"),
        ):
            with self.assertRaises(services.JWKSUnavailableError):
                services._load_jwks()


if __name__ == "__main__":
    unittest.main()
