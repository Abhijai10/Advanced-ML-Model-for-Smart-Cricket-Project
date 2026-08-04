"""Static checks for Supabase security migrations.

These tests do not replace Supabase-local RLS verification. They guard the
repository migration contract so browser roles cannot regain trusted-history
write access by accident.
"""

from __future__ import annotations

from pathlib import Path


MIGRATION = Path("supabase/migrations/20260804080002_secure_trusted_analysis_and_feedback.sql")


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
