create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.analysis_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  video_file_name text not null,
  predicted_shot text,
  shot_confidence double precision,
  technique_match_score double precision,
  shot_start_frame integer,
  shot_end_frame integer,
  shot_duration_seconds double precision,
  spoken_feedback text,
  coaching_tips jsonb not null default '[]'::jsonb,
  full_result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.shot_timeline_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  analysis_session_id uuid not null references public.analysis_sessions(id) on delete cascade,
  shot_label text not null,
  duration_seconds double precision not null default 0,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.analysis_sessions enable row level security;
alter table public.shot_timeline_events enable row level security;

grant select, insert, update, delete on table public.profiles to authenticated;
grant select, insert, update, delete on table public.analysis_sessions to authenticated;
grant select, insert, update, delete on table public.shot_timeline_events to authenticated;

create policy "Users can read their profile"
on public.profiles for select
to authenticated
using ((select auth.uid()) = id);

create policy "Users can create their profile"
on public.profiles for insert
to authenticated
with check ((select auth.uid()) = id);

create policy "Users can update their profile"
on public.profiles for update
to authenticated
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

create policy "Users can read their analyses"
on public.analysis_sessions for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "Users can create their analyses"
on public.analysis_sessions for insert
to authenticated
with check ((select auth.uid()) = user_id);

create policy "Users can update their analyses"
on public.analysis_sessions for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "Users can delete their analyses"
on public.analysis_sessions for delete
to authenticated
using ((select auth.uid()) = user_id);

create policy "Users can read their shot timeline"
on public.shot_timeline_events for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "Users can create their shot timeline"
on public.shot_timeline_events for insert
to authenticated
with check ((select auth.uid()) = user_id);

create policy "Users can delete their shot timeline"
on public.shot_timeline_events for delete
to authenticated
using ((select auth.uid()) = user_id);

create index if not exists analysis_sessions_user_created_idx
on public.analysis_sessions (user_id, created_at desc);

create index if not exists shot_timeline_user_created_idx
on public.shot_timeline_events (user_id, created_at desc);
