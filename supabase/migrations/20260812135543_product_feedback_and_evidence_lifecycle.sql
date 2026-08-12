-- Separate product feedback from ML feedback and make evidence deletion states explicit.

create table if not exists public.product_feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  usability_rating integer check (usability_rating between 1 and 5),
  bug_category text,
  feature_request text,
  notes text not null,
  page_context text,
  request_id text,
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  status text not null default 'new',
  constraint product_feedback_status_check
    check (status in ('new', 'triaged', 'in_progress', 'resolved', 'rejected', 'duplicate'))
);

alter table public.product_feedback enable row level security;

revoke all on table public.product_feedback from anon;
grant select, insert on table public.product_feedback to authenticated;
grant select, insert, update, delete on table public.product_feedback to service_role;

drop policy if exists "Users can create product feedback" on public.product_feedback;
create policy "Users can create product feedback"
on public.product_feedback for insert
to authenticated
with check (user_id = (select auth.uid()));

drop policy if exists "Users can read their product feedback" on public.product_feedback;
create policy "Users can read their product feedback"
on public.product_feedback for select
to authenticated
using (user_id = (select auth.uid()));

create index if not exists product_feedback_user_created_idx
on public.product_feedback (user_id, created_at desc);

create index if not exists product_feedback_status_created_idx
on public.product_feedback (status, created_at desc);

alter table public.analysis_sessions
  drop constraint if exists analysis_sessions_storage_status_check;

alter table public.analysis_sessions
  add constraint analysis_sessions_storage_status_check
  check (storage_status in ('not_retained', 'pending', 'stored', 'failed', 'disabled', 'withdrawn', 'deletion_pending', 'deleted'));

alter table public.analysis_feedback
  drop constraint if exists analysis_feedback_review_status_check;

alter table public.analysis_feedback
  add constraint analysis_feedback_review_status_check
  check (review_status in ('product_feedback', 'not_consented', 'metadata_only', 'awaiting_evidence', 'evidence_not_retained', 'candidate', 'needs_second_review', 'approved', 'rejected', 'withdrawn', 'deletion_pending', 'deleted'));

alter table public.analysis_feedback
  drop constraint if exists analysis_feedback_dataset_eligibility_check;

alter table public.analysis_feedback
  add constraint analysis_feedback_dataset_eligibility_check
  check (dataset_eligibility_status in ('not_eligible', 'pending_review', 'eligible', 'rejected', 'withdrawn', 'deleted'));
