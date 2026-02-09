-- Supabase Postgres schema for BALLDONTLIE NFL API (GOAT/ALL-STAR extensions)
-- Phase 2: season stats + per-game player stats + advanced stats (weekly/season)
--
-- Apply this in Supabase SQL Editor after schema_core.sql.

begin;

-- Player season totals (regular season or postseason)
create table if not exists public.nfl_player_season_stats (
  player_id bigint not null references public.nfl_players(id) on delete cascade,
  season integer not null,
  postseason boolean not null default false,
  games_played integer,

  -- passing
  passing_completions integer,
  passing_attempts integer,
  passing_yards integer,
  passing_touchdowns integer,
  passing_interceptions integer,
  qbr double precision,
  qb_rating double precision,

  -- rushing
  rushing_attempts integer,
  rushing_yards integer,
  rushing_touchdowns integer,

  -- receiving
  receptions integer,
  receiving_yards integer,
  receiving_touchdowns integer,
  receiving_targets integer,

  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),

  primary key (player_id, season, postseason)
);

create index if not exists idx_nfl_player_season_stats_season on public.nfl_player_season_stats(season, postseason);

-- Player game stats (boxscore-level per game)
create table if not exists public.nfl_player_game_stats (
  player_id bigint not null references public.nfl_players(id) on delete cascade,
  game_id bigint not null references public.nfl_games(id) on delete cascade,
  season integer not null,
  week integer not null,
  postseason boolean not null default false,
  team_id bigint references public.nfl_teams(id) on delete set null,

  -- passing
  passing_completions integer,
  passing_attempts integer,
  passing_yards integer,
  passing_touchdowns integer,
  passing_interceptions integer,
  qbr double precision,
  qb_rating double precision,

  -- rushing
  rushing_attempts integer,
  rushing_yards integer,
  rushing_touchdowns integer,

  -- receiving
  receptions integer,
  receiving_yards integer,
  receiving_touchdowns integer,
  receiving_targets integer,

  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),

  primary key (player_id, game_id)
);

create index if not exists idx_nfl_player_game_stats_season_week on public.nfl_player_game_stats(season, week, postseason);
create index if not exists idx_nfl_player_game_stats_game on public.nfl_player_game_stats(game_id);
create index if not exists idx_nfl_player_game_stats_player on public.nfl_player_game_stats(player_id);

-- GOAT advanced stats are returned per season + week (week 0 = full season).
create table if not exists public.nfl_advanced_receiving_stats (
  player_id bigint not null references public.nfl_players(id) on delete cascade,
  season integer not null,
  week integer not null,
  postseason boolean not null default false,

  receptions integer,
  targets integer,
  yards integer,
  avg_intended_air_yards double precision,
  avg_yac double precision,
  avg_expected_yac double precision,
  avg_yac_above_expectation double precision,
  catch_percentage double precision,
  -- Additional GOAT fields (additive; safe to add later via ALTER TABLE below too)
  avg_cushion double precision,
  avg_separation double precision,
  percent_share_of_intended_air_yards double precision,
  rec_touchdowns integer,

  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),

  primary key (player_id, season, week, postseason)
);

create index if not exists idx_adv_recv_season_week on public.nfl_advanced_receiving_stats(season, week, postseason);

create table if not exists public.nfl_advanced_rushing_stats (
  player_id bigint not null references public.nfl_players(id) on delete cascade,
  season integer not null,
  week integer not null,
  postseason boolean not null default false,

  rush_attempts integer,
  rush_yards integer,
  rush_touchdowns integer,
  efficiency double precision,
  avg_rush_yards double precision,
  avg_time_to_los double precision,
  expected_rush_yards double precision,
  rush_yards_over_expected double precision,
  rush_yards_over_expected_per_att double precision,
  rush_pct_over_expected double precision,
  percent_attempts_gte_eight_defenders double precision,

  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),

  primary key (player_id, season, week, postseason)
);

create index if not exists idx_adv_rush_season_week on public.nfl_advanced_rushing_stats(season, week, postseason);

create table if not exists public.nfl_advanced_passing_stats (
  player_id bigint not null references public.nfl_players(id) on delete cascade,
  season integer not null,
  week integer not null,
  postseason boolean not null default false,

  attempts integer,
  completions integer,
  pass_yards integer,
  pass_touchdowns integer,
  interceptions integer,
  passer_rating double precision,
  completion_percentage double precision,
  completion_percentage_above_expectation double precision,
  expected_completion_percentage double precision,
  avg_time_to_throw double precision,
  avg_intended_air_yards double precision,
  avg_completed_air_yards double precision,
  avg_air_distance double precision,
  avg_air_yards_differential double precision,
  avg_air_yards_to_sticks double precision,
  max_air_distance double precision,
  max_completed_air_distance double precision,
  aggressiveness double precision,
  games_played integer,

  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),

  primary key (player_id, season, week, postseason)
);

create index if not exists idx_adv_pass_season_week on public.nfl_advanced_passing_stats(season, week, postseason);

-- Additive-only column migration helpers (safe to re-run)
-- These keep schema drift manageable without requiring drop/recreate.

alter table if exists public.nfl_advanced_receiving_stats
  add column if not exists avg_cushion double precision;
alter table if exists public.nfl_advanced_receiving_stats
  add column if not exists avg_separation double precision;
alter table if exists public.nfl_advanced_receiving_stats
  add column if not exists percent_share_of_intended_air_yards double precision;
alter table if exists public.nfl_advanced_receiving_stats
  add column if not exists rec_touchdowns integer;

alter table if exists public.nfl_advanced_rushing_stats
  add column if not exists rush_touchdowns integer;
alter table if exists public.nfl_advanced_rushing_stats
  add column if not exists avg_time_to_los double precision;
alter table if exists public.nfl_advanced_rushing_stats
  add column if not exists rush_pct_over_expected double precision;
alter table if exists public.nfl_advanced_rushing_stats
  add column if not exists percent_attempts_gte_eight_defenders double precision;

alter table if exists public.nfl_advanced_passing_stats
  add column if not exists expected_completion_percentage double precision;
alter table if exists public.nfl_advanced_passing_stats
  add column if not exists avg_air_distance double precision;
alter table if exists public.nfl_advanced_passing_stats
  add column if not exists avg_air_yards_differential double precision;
alter table if exists public.nfl_advanced_passing_stats
  add column if not exists avg_air_yards_to_sticks double precision;
alter table if exists public.nfl_advanced_passing_stats
  add column if not exists max_air_distance double precision;
alter table if exists public.nfl_advanced_passing_stats
  add column if not exists max_completed_air_distance double precision;
alter table if exists public.nfl_advanced_passing_stats
  add column if not exists games_played integer;

commit;


