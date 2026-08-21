-- Repair migration-history drift for the analysis_feedback contract.
-- Existing rows are retained; constraints added as NOT VALID still protect all
-- future writes without rejecting legacy rows that predate this schema.

begin;

alter table public.analysis_feedback
  add column if not exists client_analysis_id text,
  add column if not exists clip_hash text,
  add column if not exists predicted_shot text,
  add column if not exists prediction_was_correct text,
  add column if not exists corrected_shot text,
  add column if not exists technique_feedback_rating integer,
  add column if not exists tip_flags jsonb not null default '[]'::jsonb,
  add column if not exists notes text,
  add column if not exists consent_to_model_improvement boolean not null default false,
  add column if not exists accepted_for_review boolean not null default false,
  add column if not exists review_status text not null default 'candidate',
  add column if not exists model_version text,
  add column if not exists pipeline_version text,
  add column if not exists request_id text,
  add column if not exists auth_present boolean not null default false,
  add column if not exists provenance jsonb not null default '{}'::jsonb,
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
  drop constraint if exists analysis_feedback_clip_hash_required,
  add constraint analysis_feedback_clip_hash_required check (clip_hash is not null) not valid,
  drop constraint if exists analysis_feedback_predicted_shot_check,
  add constraint analysis_feedback_predicted_shot_check
    check (predicted_shot in ('cover_drive', 'defensive_shot', 'pull_shot', 'sweep_shot')) not valid,
  drop constraint if exists analysis_feedback_prediction_was_correct_check,
  add constraint analysis_feedback_prediction_was_correct_check
    check (prediction_was_correct in ('correct', 'incorrect', 'unsure')) not valid,
  drop constraint if exists analysis_feedback_corrected_shot_check,
  add constraint analysis_feedback_corrected_shot_check
    check (corrected_shot is null or corrected_shot in ('cover_drive', 'defensive_shot', 'pull_shot', 'sweep_shot')) not valid,
  drop constraint if exists analysis_feedback_technique_feedback_rating_check,
  add constraint analysis_feedback_technique_feedback_rating_check
    check (technique_feedback_rating is null or technique_feedback_rating between 1 and 5) not valid,
  drop constraint if exists analysis_feedback_request_id_required,
  add constraint analysis_feedback_request_id_required check (request_id is not null) not valid,
  drop constraint if exists analysis_feedback_corrected_label_required,
  add constraint analysis_feedback_corrected_label_required
    check (prediction_was_correct <> 'incorrect' or corrected_shot is not null) not valid,
  drop constraint if exists analysis_feedback_review_status_check,
  add constraint analysis_feedback_review_status_check
    check (review_status in ('product_feedback', 'not_consented', 'metadata_only', 'awaiting_evidence', 'evidence_not_retained', 'candidate', 'needs_second_review', 'approved', 'rejected', 'withdrawn', 'deletion_pending', 'deleted')) not valid,
  drop constraint if exists analysis_feedback_dataset_eligibility_check,
  add constraint analysis_feedback_dataset_eligibility_check
    check (dataset_eligibility_status in ('not_eligible', 'pending_review', 'eligible', 'rejected', 'withdrawn', 'deleted')) not valid;

create index if not exists analysis_feedback_analysis_session_id_idx
on public.analysis_feedback (analysis_session_id);

create index if not exists analysis_feedback_user_id_idx
on public.analysis_feedback (user_id);

create index if not exists analysis_feedback_user_created_idx
on public.analysis_feedback (user_id, created_at desc);

create index if not exists analysis_feedback_clip_hash_idx
on public.analysis_feedback (clip_hash);

create index if not exists analysis_feedback_review_status_idx
on public.analysis_feedback (review_status);

create index if not exists analysis_feedback_dataset_eligibility_status_idx
on public.analysis_feedback (dataset_eligibility_status);

create index if not exists analysis_feedback_retention_expires_at_idx
on public.analysis_feedback (retention_expires_at);

create index if not exists analysis_feedback_deleted_at_idx
on public.analysis_feedback (deleted_at);

create unique index if not exists analysis_feedback_review_candidate_dedupe_idx
on public.analysis_feedback (user_id, clip_hash, coalesce(model_version, ''), coalesce(pipeline_version, ''))
where consent_to_model_improvement = true;

alter table public.analysis_feedback enable row level security;
grant select on table public.analysis_feedback to authenticated;

drop policy if exists "Users can read their feedback" on public.analysis_feedback;
create policy "Users can read their feedback"
on public.analysis_feedback for select
to authenticated
using ((select auth.uid()) = user_id);

commit;
