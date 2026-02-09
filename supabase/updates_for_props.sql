-- GOAT Tier upgrade - new stats and prop support

-- Player game stats: add attempts and long plays
ALTER TABLE public.nfl_player_game_stats
  ADD COLUMN IF NOT EXISTS passing_attempts integer,
  ADD COLUMN IF NOT EXISTS rushing_attempts integer,
  ADD COLUMN IF NOT EXISTS longest_rush integer,
  ADD COLUMN IF NOT EXISTS longest_reception integer;

-- Player season stats: add attempts and long plays
ALTER TABLE public.nfl_player_season_stats
  ADD COLUMN IF NOT EXISTS passing_attempts integer,
  ADD COLUMN IF NOT EXISTS rushing_attempts integer,
  ADD COLUMN IF NOT EXISTS longest_rush integer,
  ADD COLUMN IF NOT EXISTS longest_reception integer;

-- Player props: widen supported markets and add market_type
ALTER TABLE public.nfl_player_props
  ADD COLUMN IF NOT EXISTS market_type text;

-- Note: prop_type is text; expected values now include:
-- player_pass_tds, player_pass_att, player_rush_att, player_rush_rec_yds,
-- player_longest_rush, player_longest_rec, first_touchdown.

