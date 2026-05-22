-- Games you support automation for
create extension if not exists pgcrypto;

create table if not exists idle_games (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  package_name text not null,
  platform text not null default 'android',
  base_payout_cents integer not null,
  est_minutes integer not null,
  config_json jsonb not null,
  is_active boolean not null default true
);

-- Each automation run
create table if not exists idle_sessions (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references idle_games(id) on delete cascade,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  status text not null default 'running' check (status in ('running', 'completed', 'failed', 'aborted')),
  notes text,
  earned_cents integer not null default 0
);

-- Milestones (offerwall conditions)
create table if not exists idle_milestones (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references idle_games(id) on delete cascade,
  label text not null,
  target_desc text not null,
  est_minutes integer not null,
  payout_cents integer not null,
  order_index integer not null
);
