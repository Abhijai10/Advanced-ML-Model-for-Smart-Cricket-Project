"""Static checks for Supabase security migrations.

These tests do not replace Supabase-local RLS verification. They guard the
repository migration contract so browser roles cannot regain trusted-history
write access by accident.
"""

from __future__ import annotations

from pathlib import Path


MIGRATIONS_DIR = Path("supabase/migrations")


def _migration_with_prefix(prefix: str) -> Path:
    matches = sorted(path for path in MIGRATIONS_DIR.glob(f"*_{prefix}.sql") if not path.name.startswith("._"))
    assert len(matches) == 1, f"expected one migration ending in {prefix!r}, found {matches}"
    return matches[0]


MIGRATION = _migration_with_prefix("secure_trusted_analysis_and_feedback")
LIFECYCLE_MIGRATION = _migration_with_prefix("product_feedback_and_evidence_lifecycle")
PRODUCT_FEEDBACK_REPAIR_MIGRATION = _migration_with_prefix("repair_missing_product_feedback_schema")
ANALYSIS_SESSIONS_REPAIR_MIGRATION = _migration_with_prefix("repair_missing_analysis_sessions_columns")
ANALYSIS_FEEDBACK_REPAIR_MIGRATION = _migration_with_prefix("repair_missing_analysis_feedback_columns")


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


def test_product_feedback_repair_migration_restores_schema_and_access_controls() -> None:
    sql = PRODUCT_FEEDBACK_REPAIR_MIGRATION.read_text(encoding="utf-8").lower()
    for required_column in [
        "id uuid",
        "user_id uuid",
        "usability_rating integer",
        "bug_category text",
        "feature_request text",
        "notes text",
        "page_context text",
        "request_id text",
        "created_at timestamptz",
        "resolved_at timestamptz",
        "status text",
    ]:
        assert required_column in sql
    assert "create index if not exists product_feedback_user_created_idx" in sql
    assert "create index if not exists product_feedback_status_created_idx" in sql
    assert "alter table public.product_feedback enable row level security" in sql
    assert "revoke all on table public.product_feedback from anon" in sql
    assert "grant select, insert on table public.product_feedback to authenticated" in sql
    assert "grant select, insert, update, delete on table public.product_feedback to service_role" in sql
    assert "users can create product feedback" in sql
    assert "users can read their product feedback" in sql


def test_analysis_sessions_repair_migration_restores_server_inference_contract() -> None:
    sql = ANALYSIS_SESSIONS_REPAIR_MIGRATION.read_text(encoding="utf-8").lower()
    for required_column in [
        "request_id text",
        "clip_hash text",
        "model_version text",
        "pipeline_version text",
        "persistence_source text",
        "model_provenance jsonb",
        "checkpoint_sha256 text",
        "feature_contract_version text",
        "feature_schema_sha256 text",
        "scaler_mean_sha256 text",
        "scaler_std_sha256 text",
        "label_mapping_sha256 text",
        "scoring_template_sha256 text",
        "feedback_engine_version text",
        "storage_status text",
        "consent_scope text",
        "consent_version text",
        "consented_at timestamptz",
        "retention_expires_at timestamptz",
        "evidence_object_path text",
        "evidence_metadata jsonb",
        "withdrawn_at timestamptz",
        "deleted_at timestamptz",
    ]:
        assert f"add column if not exists {required_column}" in sql
    assert "create index if not exists analysis_sessions_clip_hash_idx" in sql
    assert "create index if not exists analysis_sessions_retention_expires_at_idx" in sql
    assert "revoke insert, update on table public.analysis_sessions from authenticated" in sql
    assert "grant select, insert, update, delete on table public.analysis_sessions to service_role" in sql


def test_analysis_feedback_repair_migration_restores_feedback_contract() -> None:
    sql = ANALYSIS_FEEDBACK_REPAIR_MIGRATION.read_text(encoding="utf-8").lower()
    for required_column in [
        "client_analysis_id text",
        "clip_hash text",
        "prediction_was_correct text",
        "accepted_for_review boolean",
        "review_status text",
        "request_id text",
        "feature_contract_version text",
        "storage_status text",
        "dataset_eligibility_status text",
        "label_quality_score double precision",
    ]:
        assert f"add column if not exists {required_column}" in sql
    assert "analysis_feedback_review_candidate_dedupe_idx" in sql
    assert "analysis_feedback_review_status_check" in sql
    assert "users can read their feedback" in sql


def test_evidence_lifecycle_statuses_include_disabled_and_pending_deletion() -> None:
    sql = LIFECYCLE_MIGRATION.read_text(encoding="utf-8").lower()
    assert "disabled" in sql
    assert "deletion_pending" in sql
    assert "drop constraint if exists analysis_sessions_storage_status_check" in sql
