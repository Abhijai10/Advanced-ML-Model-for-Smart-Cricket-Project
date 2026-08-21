create table if not exists public.analysis_feedback (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    analysis_session_id uuid references public.analysis_sessions(id) on delete cascade,
    created_at timestamptz default now()
);