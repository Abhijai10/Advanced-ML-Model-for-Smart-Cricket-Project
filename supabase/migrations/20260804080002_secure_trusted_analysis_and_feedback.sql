-- Trusted analysis history must be server-created only.
-- Browser clients may read/delete their own rows, but cannot fabricate or edit
-- predictions, confidence scores, model provenance, or full_result payloads.

revoke insert, update on table public.analysis_sessions from authenticated;
grant select, delete on table public.analysis_sessions to authenticated;
grant select, insert, update, delete on table public.analysis_sessions to service_role;

drop policy if exists "Users can create their analyses" on public.analysis_sessions;
drop policy if exists "Users can update their analyses" on public.analysis_sessions;

alter table public.analysis_sessions
  add column if not exists model_provenance jsonb not null default '{}'::jsonb,
  add column if not exists checkpoint_sha256 text,
  add column if not exists feature_contract_version text,
  add column if not exists feature_schema_sha256 text,
  add column if not exists scaler_mean_sha256 text,
  add column if not exists scaler_std_sha256 text,
  add column if not exists label_mapping_sha256 text,
  add column if not exists scoring_template_sha256 text,
  add column if not exists feedback_engine_version text,
  add column if not exists storage_status text not null default 'not_retained',
  add column if not exists consent_scope text not null default 'none',
  add column if not exists consent_version text,
  add column if not exists consented_at timestamptz,
  add column if not exists retention_expires_at timestamptz,
  add column if not exists evidence_object_path text,
  add column if not exists evidence_metadata jsonb not null default '{}'::jsonb,
  add column if not exists withdrawn_at timestamptz,
  add column if not exists deleted_at timestamptz;

alter table public.analysis_sessions
  add constraint analysis_sessions_storage_status_check
  check (storage_status in ('not_retained', 'pending', 'stored', 'failed', 'withdrawn', 'deleted')) not valid;

alter table public.analysis_sessions
  validate constraint analysis_sessions_storage_status_check;

alter table public.analysis_feedback
  add column if not exists feature_contract_version text,
  add column if not exists feature_schema_sha256 text,
  add column if not exists checkpoint_sha256 text,
  add column if not exists consent_version text,
  add column if not exists consented_at timestamptz,
  add column if not exists retention_expires_at timestamptz,
  add column if not exists storage_status text not null default 'not_retained',
  add column if not exists evidence_object_path text,
  add column if not exists evidence_metadata jsonb not null default '{}'::jsonb,
  add column if not exists reviewer_id uuid references auth.users(id) on delete set null,
  add column if not exists reviewed_at timestamptz,
  add column if not exists reviewer_label text,
  add column if not exists second_review_required boolean not null default false,
  add column if not exists disagreement_notes text,
  add column if not exists rejection_reason text,
  add column if not exists unsafe_content_flag boolean not null default false,
  add column if not exists dataset_eligibility_status text not null default 'not_eligible',
  add column if not exists split_assignment text,
  add column if not exists training_inclusion_version text,
  add column if not exists withdrawn_at timestamptz,
  add column if not exists deleted_at timestamptz,
  add column if not exists provenance_completeness_score double precision,
  add column if not exists label_quality_score double precision;

alter table public.analysis_feedback
  add constraint analysis_feedback_review_status_check
  check (review_status in ('product_feedback', 'not_consented', 'candidate', 'needs_second_review', 'approved', 'rejected', 'withdrawn', 'deleted')) not valid;

alter table public.analysis_feedback
  validate constraint analysis_feedback_review_status_check;

alter table public.analysis_feedback
  add constraint analysis_feedback_dataset_eligibility_check
  check (dataset_eligibility_status in ('not_eligible', 'pending_review', 'eligible', 'rejected', 'withdrawn', 'deleted')) not valid;

alter table public.analysis_feedback
  validate constraint analysis_feedback_dataset_eligibility_check;
