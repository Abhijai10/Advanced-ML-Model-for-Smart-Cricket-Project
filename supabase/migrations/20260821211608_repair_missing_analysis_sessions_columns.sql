-- Repair migration-history drift: 20260804080002 was marked applied without
-- executing its analysis_sessions schema and access-control changes remotely.

begin;

alter table public.analysis_sessions
  add column if not exists request_id text,
  add column if not exists clip_hash text,
  add column if not exists model_version text,
  add column if not exists pipeline_version text,
  add column if not exists persistence_source text not null default 'server_verified_inference',
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
  drop constraint if exists analysis_sessions_storage_status_check,
  add constraint analysis_sessions_storage_status_check
    check (storage_status in ('not_retained', 'pending', 'stored', 'failed', 'disabled', 'withdrawn', 'deletion_pending', 'deleted')) not valid;

create index if not exists analysis_sessions_user_created_idx
on public.analysis_sessions (user_id, created_at desc);

create index if not exists analysis_sessions_user_id_idx
on public.analysis_sessions (user_id);

create index if not exists analysis_sessions_clip_hash_idx
on public.analysis_sessions (clip_hash);

create index if not exists analysis_sessions_retention_expires_at_idx
on public.analysis_sessions (retention_expires_at);

create index if not exists analysis_sessions_deleted_at_idx
on public.analysis_sessions (deleted_at);

revoke insert, update on table public.analysis_sessions from authenticated;
grant select, delete on table public.analysis_sessions to authenticated;
grant select, insert, update, delete on table public.analysis_sessions to service_role;

drop policy if exists "Users can create their analyses" on public.analysis_sessions;
drop policy if exists "Users can update their analyses" on public.analysis_sessions;

commit;
