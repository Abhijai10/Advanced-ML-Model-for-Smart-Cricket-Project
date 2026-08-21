"""Supabase staging verification harness tests."""

from __future__ import annotations

import io
import ssl
import urllib.error
from unittest.mock import patch

from scripts.verify_supabase_staging import SupabaseVerifier, VerificationConfig


def _config(**overrides) -> VerificationConfig:
    base = VerificationConfig(
        supabase_url="https://project.supabase.co",
        service_role_key="service-secret",
        publishable_key="publishable",
        evidence_bucket=None,
        user_a_id=None,
        user_a_token=None,
        user_b_id=None,
        user_b_token=None,
    )
    return VerificationConfig(**{**base.__dict__, **overrides})


def test_dry_run_skips_writes_and_does_not_expose_secrets() -> None:
    verifier = SupabaseVerifier(_config(user_a_id="00000000-0000-0000-0000-000000000001"), dry_run=True)
    checks = verifier.run()
    text = str([check.__dict__ for check in checks])
    assert "service-secret" not in text
    assert any(check.status == "DRY_RUN" for check in checks)


def test_missing_external_users_are_skipped_not_failed() -> None:
    verifier = SupabaseVerifier(_config(), dry_run=True)
    checks = verifier.run()
    trusted = next(check for check in checks if check.name == "Trusted insert")
    assert trusted.status == "SKIPPED_EXTERNAL_CREDENTIAL"


def test_missing_service_credentials_fail_connectivity() -> None:
    verifier = SupabaseVerifier(_config(supabase_url=None, service_role_key=None), dry_run=True)
    checks = verifier.run()
    connectivity = next(check for check in checks if check.name == "Connectivity")
    assert connectivity.status == "FAIL"


def test_verifier_uses_certifi_backed_tls_verification() -> None:
    verifier = SupabaseVerifier(_config())

    assert verifier._ssl_context.verify_mode == ssl.CERT_REQUIRED
    assert verifier._ssl_context.check_hostname is True


def test_request_passes_certifi_context_to_urlopen() -> None:
    verifier = SupabaseVerifier(_config())

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        @staticmethod
        def read() -> bytes:
            return b"[]"

    with patch("scripts.verify_supabase_staging.urllib.request.urlopen", return_value=Response()) as urlopen:
        status, _ = verifier._request("GET", "/rest/v1/profiles", service=True)

    assert status == 200
    assert urlopen.call_args.kwargs["context"] is verifier._ssl_context


def test_connectivity_reports_tls_failure_details() -> None:
    verifier = SupabaseVerifier(_config())
    tls_error = ssl.SSLCertVerificationError(1, "certificate verify failed: unable to get local issuer certificate")

    with patch("scripts.verify_supabase_staging.urllib.request.urlopen", side_effect=urllib.error.URLError(tls_error)):
        check = verifier._connectivity()

    assert check.status == "FAIL"
    assert "certificate verify failed" in check.detail


def test_request_reports_postgrest_error_body() -> None:
    verifier = SupabaseVerifier(_config())
    error = urllib.error.HTTPError(
        "https://project.supabase.co/rest/v1/analysis_sessions",
        400,
        "Bad Request",
        hdrs=None,
        fp=io.BytesIO(b'{"code":"23502","message":"null value in column user_id"}'),
    )

    with patch("scripts.verify_supabase_staging.urllib.request.urlopen", side_effect=error):
        status, payload = verifier._request("POST", "/rest/v1/analysis_sessions", {}, service=True)

    assert status == 400
    assert payload == {"error": "http_error", "detail": "23502; null value in column user_id"}
    assert "23502" in verifier._response_summary(status, payload)


def test_cleanup_accepts_supabase_missing_storage_object() -> None:
    verifier = SupabaseVerifier(_config(evidence_bucket="analysis-evidence"))
    verifier.created_object_path = "smart_cricket_staging_verification/already-deleted.txt"

    with patch.object(
        verifier,
        "_request",
        return_value=(400, {"error": "http_error", "detail": "404; NoSuchKey; Object not found"}),
    ):
        check = verifier._cleanup()

    assert check.status == "PASS"


def test_cleanup_keeps_real_storage_failure_visible() -> None:
    verifier = SupabaseVerifier(_config(evidence_bucket="analysis-evidence"))
    verifier.created_object_path = "smart_cricket_staging_verification/unavailable.txt"

    with patch.object(verifier, "_request", return_value=(503, {"error": "http_error", "detail": "Service Unavailable"})):
        check = verifier._cleanup()

    assert check.status == "FAIL"
    assert "HTTP 503" in check.detail


def test_user_isolation_reports_rejected_access_token() -> None:
    verifier = SupabaseVerifier(
        _config(
            user_a_id="00000000-0000-0000-0000-000000000001",
            user_a_token="expired-a",
            user_b_id="00000000-0000-0000-0000-000000000002",
            user_b_token="expired-b",
        )
    )
    verifier.created_analysis_id = "00000000-0000-0000-0000-000000000003"

    with patch.object(verifier, "_request", return_value=(401, {"error": "http_error", "detail": "Invalid JWT"})):
        check = verifier._user_isolation()

    assert check.status == "FAIL"
    assert "User A token rejected" in check.detail
    assert "fresh access token" in check.detail
