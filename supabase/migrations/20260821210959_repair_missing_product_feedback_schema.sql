-- Repair a migration-history drift where the original product_feedback migration
-- was recorded as applied without creating the remote table.

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

-- Make the repair safe if a previous manual attempt created only part of the table.
alter table public.product_feedback
  add column if not exists id uuid default gen_random_uuid(),
  add column if not exists user_id uuid references auth.users(id) on delete set null,
  add column if not exists usability_rating integer,
  add column if not exists bug_category text,
  add column if not exists feature_request text,
  add column if not exists notes text,
  add column if not exists page_context text,
  add column if not exists request_id text,
  add column if not exists created_at timestamptz default now(),
  add column if not exists resolved_at timestamptz,
  add column if not exists status text default 'new';

alter table public.product_feedback
  alter column id set default gen_random_uuid(),
  alter column created_at set default now(),
  alter column status set default 'new';

alter table public.product_feedback
  drop constraint if exists product_feedback_usability_rating_check,
  add constraint product_feedback_usability_rating_check
    check (usability_rating between 1 and 5) not valid,
  drop constraint if exists product_feedback_status_check,
  add constraint product_feedback_status_check
    check (status in ('new', 'triaged', 'in_progress', 'resolved', 'rejected', 'duplicate')) not valid;

create index if not exists product_feedback_user_created_idx
on public.product_feedback (user_id, created_at desc);

create index if not exists product_feedback_status_created_idx
on public.product_feedback (status, created_at desc);

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
