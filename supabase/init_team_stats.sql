-- Add totals to Season Stats
ALTER TABLE nfl_team_season_stats 
ADD COLUMN IF NOT EXISTS passing_yards INT,
ADD COLUMN IF NOT EXISTS rushing_yards INT,
ADD COLUMN IF NOT EXISTS total_yards INT,
ADD COLUMN IF NOT EXISTS total_points INT,
ADD COLUMN IF NOT EXISTS passing_touchdowns INT,
ADD COLUMN IF NOT EXISTS rushing_touchdowns INT,
ADD COLUMN IF NOT EXISTS passing_completions INT,
ADD COLUMN IF NOT EXISTS passing_attempts INT,
ADD COLUMN IF NOT EXISTS rushing_attempts INT,
ADD COLUMN IF NOT EXISTS first_downs INT,
ADD COLUMN IF NOT EXISTS third_down_conversions INT,
ADD COLUMN IF NOT EXISTS fourth_down_conversions INT,
ADD COLUMN IF NOT EXISTS penalties INT,
ADD COLUMN IF NOT EXISTS penalty_yards INT,
ADD COLUMN IF NOT EXISTS fumbles_lost INT,
ADD COLUMN IF NOT EXISTS possession_time_seconds INT;

-- Create Team Game Stats table for Game Logs / Matchup History
CREATE TABLE IF NOT EXISTS nfl_team_game_stats (
    team_id INT NOT NULL,
    game_id INT NOT NULL,
    season INT,
    week INT,
    opponent_id INT, -- implied from game
    is_home BOOLEAN,
    
    -- Stats
    total_yards INT,
    passing_yards INT,
    rushing_yards INT,
    total_points INT,
    turnovers INT,
    first_downs INT,
    possession_time_seconds INT,
    third_down_conversions INT,
    third_down_attempts INT,
    fourth_down_conversions INT,
    fourth_down_attempts INT,
    red_zone_scores INT,
    red_zone_attempts INT,
    penalties INT,
    penalty_yards INT,
    sacks_allowed INT,
    
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (team_id, game_id)
);

CREATE INDEX IF NOT EXISTS idx_team_game_stats_team_season ON nfl_team_game_stats(team_id, season);
CREATE INDEX IF NOT EXISTS idx_team_game_stats_game ON nfl_team_game_stats(game_id);
