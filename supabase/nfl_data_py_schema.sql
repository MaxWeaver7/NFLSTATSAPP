-- NFL Data Py Tables
-- Run this in Supabase SQL Editor to create the required tables

-- Player ID Mapping Table (cross-reference between data sources)
CREATE TABLE IF NOT EXISTS nfl_player_id_mapping (
    gsis_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    position TEXT,
    team TEXT,
    espn_id BIGINT,
    yahoo_id BIGINT,
    sleeper_id TEXT,
    pfr_id TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for name lookups
CREATE INDEX IF NOT EXISTS idx_player_id_mapping_name ON nfl_player_id_mapping(name);
CREATE INDEX IF NOT EXISTS idx_player_id_mapping_espn ON nfl_player_id_mapping(espn_id);

-- Historic Game Lines Table (from nfl_data_py schedules)
CREATE TABLE IF NOT EXISTS nfl_game_lines (
    nflverse_game_id TEXT PRIMARY KEY,
    season INT NOT NULL,
    week INT NOT NULL,
    game_type TEXT,
    gameday TEXT,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_score INT,
    away_score INT,
    -- Betting lines
    spread_line DECIMAL,
    total_line DECIMAL,
    over_odds INT,
    under_odds INT,
    home_moneyline INT,
    away_moneyline INT,
    home_spread_odds INT,
    away_spread_odds INT,
    -- Weather and venue
    roof TEXT,
    surface TEXT,
    temp INT,
    wind INT,
    stadium TEXT,
    -- Context
    home_coach TEXT,
    away_coach TEXT,
    referee TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_game_lines_season_week ON nfl_game_lines(season, week);
CREATE INDEX IF NOT EXISTS idx_game_lines_teams ON nfl_game_lines(home_team, away_team);

-- Snap Counts Table
CREATE TABLE IF NOT EXISTS nfl_snap_counts (
    pfr_player_id TEXT NOT NULL,
    player_name TEXT,
    season INT NOT NULL,
    week INT NOT NULL,
    game_type TEXT DEFAULT 'REG',
    team TEXT,
    position TEXT,
    offense_snaps INT DEFAULT 0,
    offense_pct DECIMAL DEFAULT 0,
    defense_snaps INT DEFAULT 0,
    defense_pct DECIMAL DEFAULT 0,
    st_snaps INT DEFAULT 0,
    st_pct DECIMAL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (pfr_player_id, season, week)
);

-- Index for player lookups
CREATE INDEX IF NOT EXISTS idx_snap_counts_player ON nfl_snap_counts(pfr_player_id);
CREATE INDEX IF NOT EXISTS idx_snap_counts_season_week ON nfl_snap_counts(season, week);

-- Add column to track market type on player props (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'nfl_player_props' AND column_name = 'market_type'
    ) THEN
        ALTER TABLE nfl_player_props ADD COLUMN market_type TEXT;
    END IF;
END $$;
