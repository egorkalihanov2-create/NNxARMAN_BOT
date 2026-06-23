create table if not exists public.players (
  telegram_id bigint primary key,
  username text,
  first_name text,
  last_name text,
  current_act text not null default 'act_1',
  current_segment text not null default 'start',
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  finished_at timestamptz
);

create table if not exists public.player_state (
  telegram_id bigint primary key references public.players(telegram_id) on delete cascade,
  vars jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.events (
  id bigserial primary key,
  telegram_id bigint references public.players(telegram_id) on delete set null,
  event_type text not null,
  act_id text,
  segment_id text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.uploads (
  id bigserial primary key,
  telegram_id bigint not null references public.players(telegram_id) on delete cascade,
  act_id text,
  segment_id text,
  storage_bucket text not null,
  storage_path text not null unique,
  original_name text,
  mime_type text,
  size_bytes integer not null,
  telegram_file_id text not null,
  telegram_file_unique_id text,
  status text not null default 'accepted',
  created_at timestamptz not null default now()
);

create table if not exists public.timers (
  id bigserial primary key,
  telegram_id bigint not null references public.players(telegram_id) on delete cascade,
  trigger_at timestamptz not null,
  priority integer not null default 0,
  action jsonb not null,
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  executed_at timestamptz
);

create index if not exists events_telegram_id_created_at_idx
  on public.events (telegram_id, created_at desc);

create index if not exists uploads_telegram_id_created_at_idx
  on public.uploads (telegram_id, created_at desc);

create index if not exists timers_status_trigger_at_idx
  on public.timers (status, trigger_at, priority desc);

alter table public.players enable row level security;
alter table public.player_state enable row level security;
alter table public.events enable row level security;
alter table public.uploads enable row level security;
alter table public.timers enable row level security;

insert into storage.buckets
  (id, name, public, file_size_limit, allowed_mime_types)
values
  ('player-uploads', 'player-uploads', false, 10485760, array['image/png', 'image/jpeg'])
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
