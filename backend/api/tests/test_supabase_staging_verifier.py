"""Supabase staging verification harness tests."""

from __future__ import annotations

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
