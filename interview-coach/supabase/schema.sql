-- Interview Coach: Supabase / Postgres schema (Phase B).
-- Run once in the Supabase SQL editor. The server uses the service-role key (bypasses RLS) and filters on
-- user_id itself; the policies below protect the tables if a browser queries Supabase directly.
-- Timestamps are epoch seconds (double precision) so rows match the local SQLite store exactly.

create table if not exists public.attempts (
    id             bigint generated always as identity primary key,
    user_id        text not null,                       -- auth.users.id as text ('local' for migrated rows)
    question_id    text not null,
    stack          text not null,
    topic          text not null default '',
    level          text not null default '',
    answer_text    text not null,
    check_json     jsonb not null,
    total_score    double precision not null,
    provider       text not null,
    prompt_version text not null default '',
    created_at     double precision not null,
    saved          boolean not null default false,
    label          text not null default ''
);
create index if not exists ix_attempts_q on public.attempts (user_id, question_id, created_at desc);
create index if not exists ix_attempts_time on public.attempts (created_at);

create table if not exists public.submissions (
    id           bigint generated always as identity primary key,
    attempt_id   bigint not null references public.attempts (id) on delete cascade,
    user_id      text not null,
    question_id  text not null,
    stack        text not null,
    angle        text not null default '',
    answer_text  text not null,
    status       text not null check (status in ('pending', 'approved', 'rejected', 'promoted')),
    gate_json    jsonb not null,
    provider     text not null default '',
    review_note  text not null default '',
    reviewer_id  text not null default '',
    promoted_to  text not null default '',
    created_at   double precision not null,
    updated_at   double precision not null
);
create index if not exists ix_submissions_status on public.submissions (status, created_at desc);

-- ---------------------------------------------------------------- Row Level Security
alter table public.attempts enable row level security;
alter table public.submissions enable row level security;

-- Learners: only their own rows.
create policy attempts_own on public.attempts
    for all using (user_id = auth.uid()::text) with check (user_id = auth.uid()::text);
create policy submissions_own_read on public.submissions
    for select using (user_id = auth.uid()::text);
create policy submissions_own_insert on public.submissions
    for insert with check (user_id = auth.uid()::text and status in ('pending', 'rejected'));

-- Reviewers (app_metadata.role = 'reviewer', set in the Supabase dashboard): read and decide on everything.
create policy submissions_reviewer on public.submissions
    for all using ((auth.jwt() -> 'app_metadata' ->> 'role') = 'reviewer')
    with check ((auth.jwt() -> 'app_metadata' ->> 'role') = 'reviewer');
create policy attempts_reviewer_read on public.attempts
    for select using ((auth.jwt() -> 'app_metadata' ->> 'role') = 'reviewer');

-- ---------------------------------------------------------------- not used yet
-- pgvector for semantic retrieval is planned (docs/SELF_IMPROVING_DESIGN.md section 6) but needs an
-- embedding model, which this app does not call yet. Retrieval is still the keyword search in retrieve.py.
-- create extension if not exists vector;
