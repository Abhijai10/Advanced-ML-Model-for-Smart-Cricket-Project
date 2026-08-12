"""Static checks for Supabase security migrations.

These tests do not replace Supabase-local RLS verification. They guard the
repository migration contract so browser roles cannot regain trusted-history
write access by accident.
"""

from __future__ import annotations

from pathlib import Path


MIGRATION = Path("supabase/migrations/20260804080002_secure_trusted_analysis_and_feedback.sql")
LIFECYCLE_MIGRATION = Path("supabase/migrations/20260812135543_product_feedback_and_evidence_lifecycle.sql")


def test_trusted_analysis_history_is_server_written_only() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "revoke insert, update on table public.analysis_sessions from authenticated" in sql
    assert 'drop policy if exists "users can create their analyses"' in sql
    assert 'drop policy if exists "users can update their analyses"' in sql
    assert "grant select, delete on table public.analysis_sessions to authenticated" in sql
    assert "grant select, insert, update, delete on table public.analysis_sessions to service_role" in sql


def test_feedback_review_schema_tracks_consent_evidence_and_adjudication() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    for required_column in [
        "consent_version",
        "consented_at",
        "retention_expires_at",
        "evidence_object_path",
        "reviewer_id",
        "reviewer_label",
        "second_review_required",
        "dataset_eligibility_status",
        "training_inclusion_version",
        "withdrawn_at",
        "deleted_at",
        "provenance_completeness_score",
        "label_quality_score",
    ]:
        assert required_column in sql


def test_product_feedback_has_dedicated_non_ml_table() -> None:
    sql = LIFECYCLE_MIGRATION.read_text(encoding="utf-8").lower()
    assert "create table if not exists public.product_feedback" in sql
    assert "analysis_session_id" not in sql
    assert "accepted_for_review" not in sql
    assert "grant select, insert on table public.product_feedback to authenticated" in sql
    assert "enable row level security" in sql
    assert "users can create product feedback" in sql


def test_evidence_lifecycle_statuses_include_disabled_and_pending_deletion() -> None:
    sql = LIFECYCLE_MIGRATION.read_text(encoding="utf-8").lower()
    assert "disabled" in sql
    assert "deletion_pending" in sql
    assert "drop constraint if exists analysis_sessions_storage_status_check" in sql
