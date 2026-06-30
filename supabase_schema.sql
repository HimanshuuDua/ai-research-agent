-- AI Research Agent — Supabase schema
-- Run this once in Supabase → SQL Editor → New query → Run.
-- After this, conversation data appears in Supabase → Table Editor.

create table if not exists public.sessions (
    session_key   text primary key,
    ip_hash       text not null,
    first_seen    timestamptz not null default now(),
    last_seen     timestamptz not null default now(),
    message_count integer default 0
);

create table if not exists public.messages (
    id          bigint generated always as identity primary key,
    session_key text not null,
    role        text not null,
    content     text not null,
    mode        text,
    model_used  text,
    created_at  timestamptz not null default now()
);

create table if not exists public.usage_logs (
    id           bigint generated always as identity primary key,
    session_key  text not null,
    ip_hash      text not null,
    prompt       text not null,
    output       text not null,
    mode         text,
    model_used   text,
    email_status text,
    created_at   timestamptz not null default now()
);

create index if not exists idx_messages_session on public.messages (session_key, id);
create index if not exists idx_usage_session on public.usage_logs (session_key, id);

-- Row Level Security: keep tables private. The app uses the service_role key,
-- which bypasses RLS, so no public policies are needed.
alter table public.sessions   enable row level security;
alter table public.messages   enable row level security;
alter table public.usage_logs enable row level security;
