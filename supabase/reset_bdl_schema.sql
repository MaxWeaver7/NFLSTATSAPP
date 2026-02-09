-- COMPLETE BALLDONTLIE SCHEMA RESET
-- This script WIPES and RECREATES all Ball Don't Lie related tables.
-- It ensures a clean slate, correct Foreign Keys, and full alignment with the Master API Doc.

-- 1. DROP EVERYTHING (Reverse Order of Reference)
DROP TABLE IF EXISTS nfl_game_odds CASCADE;
DROP TABLE IF EXISTS nfl_player_props CASCADE;
DROP TABLE IF EXISTS nfl_advanced_receiving_stats CASCADE;
DROP TABLE IF EXISTS nfl_advanced_passing_stats CASCADE;
DROP TABLE IF EXISTS nfl_advanced_rushing_stats CASCADE;
DROP TABLE IF EXISTS nfl_player_game_stats CASCADE;
DROP TABLE IF EXISTS nfl_player_season_stats CASCADE;
DROP TABLE IF EXISTS nfl_rosters CASCADE; -- New
DROP TABLE IF EXISTS nfl_team_game_stats CASCADE;
DROP TABLE IF EXISTS nfl_team_season_stats CASCADE;
DROP TABLE IF EXISTS nfl_team_standings CASCADE;
DROP TABLE IF EXISTS nfl_injuries CASCADE;
DROP TABLE IF EXISTS nfl_games CASCADE;
DROP TABLE IF EXISTS nfl_players CASCADE;
DROP TABLE IF EXISTS nfl_teams CASCADE;

-- 2. CORE TABLES

-- Teams
CREATE TABLE nfl_teams (
    id INT PRIMARY KEY,
    conference TEXT,
    division TEXT,
    location TEXT,
    name TEXT,
    full_name TEXT,
    abbreviation TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Players (Added is_active)
CREATE TABLE nfl_players (
    id INT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    position TEXT,
    position_abbreviation TEXT,
    height TEXT,
    weight TEXT,
    jersey_number TEXT,
    college TEXT,
    experience TEXT,
    age INT,
    team_id INT REFERENCES nfl_teams(id), -- Latest known team
    is_active BOOLEAN DEFAULT FALSE, -- New flag for "Active Players" logic
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_players_team ON nfl_players(team_id);
CREATE INDEX idx_players_active ON nfl_players(is_active);

-- Games
CREATE TABLE nfl_games (
    id INT PRIMARY KEY,
    date TIMESTAMPTZ,
    season INT,
    week INT,
    postseason BOOLEAN,
    status TEXT,
    home_team_id INT REFERENCES nfl_teams(id),
    visitor_team_id INT REFERENCES nfl_teams(id),
    home_team_score INT,
    visitor_team_score INT,
    venue TEXT,
    -- Enhanced Score details
    home_team_q1 INT, home_team_q2 INT, home_team_q3 INT, home_team_q4 INT, home_team_ot INT,
    visitor_team_q1 INT, visitor_team_q2 INT, visitor_team_q3 INT, visitor_team_q4 INT, visitor_team_ot INT,
    summary TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_games_season_week ON nfl_games(season, week);
CREATE INDEX idx_games_teams ON nfl_games(home_team_id, visitor_team_id);

-- 3. RELATIONAL / AUX TABLES

-- Injuries
CREATE TABLE nfl_injuries (
    id SERIAL PRIMARY KEY, -- No BDL ID provided, synthetic PK
    player_id INT REFERENCES nfl_players(id),
    status TEXT,
    comment TEXT,
    date TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(player_id, date) -- Constraint to prevent duplicate records for same report
);

-- Rosters (New)
CREATE TABLE nfl_rosters (
    id SERIAL PRIMARY KEY,
    team_id INT REFERENCES nfl_teams(id),
    player_id INT REFERENCES nfl_players(id),
    season INT NOT NULL,
    position TEXT, -- e.g. "Center"
    depth INT, -- e.g. 1, 2, 3
    injury_status TEXT, -- Captured from roster endpoint if present
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, player_id, season)
);

-- Team Standings
CREATE TABLE nfl_team_standings (
    team_id INT NOT NULL REFERENCES nfl_teams(id),
    season INT NOT NULL,
    wins INT,
    losses INT,
    ties INT,
    win_streak INT,
    points_for INT,
    points_against INT,
    point_differential INT,
    playoff_seed INT,
    overall_record TEXT,
    conference_record TEXT,
    division_record TEXT,
    home_record TEXT,
    road_record TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (team_id, season)
);

-- 4. STATS TABLES

-- Team Season Stats
CREATE TABLE nfl_team_season_stats (
    team_id INT NOT NULL REFERENCES nfl_teams(id),
    season INT NOT NULL,
    season_type INT DEFAULT 2, 
    postseason BOOLEAN DEFAULT FALSE,
    games_played INT,
    total_points DECIMAL,
    total_points_per_game DECIMAL,
    total_offensive_yards DECIMAL,
    total_offensive_yards_per_game DECIMAL,
    passing_attempts INT,
    passing_completions INT,
    passing_completion_pct DECIMAL,
    passing_yards DECIMAL,
    passing_yards_per_game DECIMAL,
    passing_touchdowns INT,
    passing_interceptions INT,
    net_passing_yards DECIMAL,
    yards_per_pass_attempt DECIMAL,
    passing_first_downs INT,
    passing_first_down_pct DECIMAL,
    passing_20_plus_yards INT,
    passing_40_plus_yards INT,
    passing_sacks INT,
    passing_sack_yards INT,
    qb_rating DECIMAL,
    rushing_attempts INT,
    rushing_yards DECIMAL,
    rushing_yards_per_game DECIMAL,
    rushing_touchdowns INT,
    rushing_average DECIMAL,
    rushing_first_downs INT,
    rushing_first_down_pct DECIMAL,
    rushing_20_plus_yards INT,
    rushing_40_plus_yards INT,
    rushing_fumbles INT,
    receiving_receptions INT,
    receiving_yards DECIMAL,
    receiving_touchdowns INT,
    receiving_targets INT,
    receiving_average DECIMAL,
    receiving_first_downs INT,
    misc_first_downs INT,
    third_down_efficiency TEXT,
    third_down_conv_pct DECIMAL,
    fourth_down_efficiency TEXT,
    red_zone_efficiency TEXT,
    goal_to_go_efficiency TEXT,
    kicking_field_goals_made INT,
    kicking_field_goals_attempted INT,
    kicking_pct DECIMAL,
    punting_punts INT,
    punting_yards DECIMAL,
    punting_average DECIMAL,
    punting_net_average DECIMAL,
    punts_inside_20 INT,
    kick_returns INT,
    kick_return_yards DECIMAL,
    kick_return_average DECIMAL,
    kick_return_touchdowns INT,
    punt_returns INT,
    punt_return_yards DECIMAL,
    punt_return_average DECIMAL,
    punt_return_touchdowns INT,
    defensive_interceptions INT,
    fumbles_forced INT,
    fumbles_recovered INT,
    turnovers INT,
    turnover_differential INT,
    possession_time TEXT,
    possession_time_seconds DECIMAL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (team_id, season, season_type)
);

-- Team Game Stats
CREATE TABLE nfl_team_game_stats (
    id SERIAL PRIMARY KEY,
    team_id INT NOT NULL REFERENCES nfl_teams(id),
    game_id INT NOT NULL REFERENCES nfl_games(id),
    season INT, 
    week INT,   
    home_away TEXT, 
    first_downs INT,
    first_downs_passing INT,
    first_downs_rushing INT,
    first_downs_penalty INT,
    third_down_efficiency TEXT,
    third_down_conversions INT,
    third_down_attempts INT,
    fourth_down_efficiency TEXT,
    fourth_down_conversions INT,
    fourth_down_attempts INT,
    total_offensive_plays INT,
    total_yards DECIMAL,
    yards_per_play DECIMAL,
    total_drives INT,
    net_passing_yards DECIMAL,
    passing_completions INT,
    passing_attempts INT,
    yards_per_pass DECIMAL,
    sacks INT,
    sack_yards_lost INT,
    rushing_yards DECIMAL,
    rushing_attempts INT,
    yards_per_rush_attempt DECIMAL,
    red_zone_scores INT,
    red_zone_attempts INT,
    penalties INT,
    penalty_yards INT,
    turnovers INT,
    fumbles_lost INT,
    interceptions_thrown INT,
    defensive_touchdowns INT,
    possession_time TEXT,
    possession_time_seconds DECIMAL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (team_id, game_id)
);

-- Player Season Stats
CREATE TABLE nfl_player_season_stats (
    player_id INT NOT NULL REFERENCES nfl_players(id),
    season INT NOT NULL,
    postseason BOOLEAN DEFAULT FALSE,
    team_id INT REFERENCES nfl_teams(id), 
    games_played INT,
    passing_completions INT,
    passing_attempts INT,
    passing_yards DECIMAL,
    passing_touchdowns INT,
    passing_interceptions INT,
    passing_yards_per_game DECIMAL,
    passing_completion_pct DECIMAL,
    qbr DECIMAL,
    rushing_attempts INT,
    rushing_yards DECIMAL,
    rushing_yards_per_game DECIMAL,
    rushing_touchdowns INT,
    rushing_fumbles INT,
    rushing_first_downs INT,
    receptions INT,
    receiving_yards DECIMAL,
    receiving_yards_per_game DECIMAL,
    receiving_touchdowns INT,
    receiving_targets INT,
    receiving_first_downs INT,
    fumbles_forced INT,
    fumbles_recovered INT,
    total_tackles INT,
    defensive_sacks DECIMAL,
    defensive_interceptions INT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (player_id, season, postseason)
);

-- Player Game Stats
CREATE TABLE nfl_player_game_stats (
    id SERIAL PRIMARY KEY,
    player_id INT NOT NULL REFERENCES nfl_players(id),
    game_id INT NOT NULL REFERENCES nfl_games(id),
    team_id INT REFERENCES nfl_teams(id),
    season INT,
    week INT,
    passing_completions INT,
    passing_attempts INT,
    passing_yards DECIMAL,
    passing_touchdowns INT,
    passing_interceptions INT,
    sacks INT,
    qbr DECIMAL,
    qb_rating DECIMAL,
    rushing_attempts INT,
    rushing_yards DECIMAL,
    rushing_touchdowns INT,
    receptions INT,
    receiving_yards DECIMAL,
    receiving_touchdowns INT,
    receiving_targets INT,
    fumbles INT,
    fumbles_lost INT,
    fumbles_recovered INT,
    total_tackles INT,
    defensive_sacks DECIMAL,
    defensive_interceptions INT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (player_id, game_id)
);

-- Advanced Stats
CREATE TABLE nfl_advanced_rushing_stats (
    player_id INT NOT NULL REFERENCES nfl_players(id),
    season INT NOT NULL,
    week INT NOT NULL DEFAULT 0,
    postseason BOOLEAN DEFAULT FALSE,
    efficiency DECIMAL,
    percent_attempts_gte_eight_defenders DECIMAL,
    avg_time_to_los DECIMAL,
    expected_rush_yards DECIMAL,
    rush_yards_over_expected DECIMAL,
    rush_yards_over_expected_per_att DECIMAL,
    rush_pct_over_expected DECIMAL,
    avg_rush_yards DECIMAL,
    rush_attempts INT,
    rush_yards DECIMAL,
    rush_touchdowns INT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (player_id, season, week, postseason)
);

CREATE TABLE nfl_advanced_passing_stats (
    player_id INT NOT NULL REFERENCES nfl_players(id),
    season INT NOT NULL,
    week INT NOT NULL DEFAULT 0,
    postseason BOOLEAN DEFAULT FALSE,
    aggressiveness DECIMAL,
    avg_time_to_throw DECIMAL,
    avg_air_distance DECIMAL,
    avg_intended_air_yards DECIMAL,
    avg_completed_air_yards DECIMAL,
    avg_air_yards_differential DECIMAL,
    avg_air_yards_to_sticks DECIMAL,
    completion_percentage_above_expectation DECIMAL,
    expected_completion_percentage DECIMAL,
    passer_rating DECIMAL,
    attempts INT,
    completions INT,
    pass_yards DECIMAL,
    pass_touchdowns INT,
    interceptions INT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (player_id, season, week, postseason)
);

CREATE TABLE nfl_advanced_receiving_stats (
    player_id INT NOT NULL REFERENCES nfl_players(id),
    season INT NOT NULL,
    week INT NOT NULL DEFAULT 0,
    postseason BOOLEAN DEFAULT FALSE,
    avg_separation DECIMAL,
    avg_cushion DECIMAL,
    avg_yac DECIMAL,
    avg_expected_yac DECIMAL,
    avg_yac_above_expectation DECIMAL,
    percent_share_of_intended_air_yards DECIMAL,
    catch_percentage DECIMAL,
    receptions INT,
    targets INT,
    yards DECIMAL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (player_id, season, week, postseason)
);

-- Player Props
CREATE TABLE nfl_player_props (
    id TEXT PRIMARY KEY,
    game_id INT REFERENCES nfl_games(id),
    player_id INT REFERENCES nfl_players(id),
    prop_type TEXT,
    market_type TEXT,
    vendor TEXT,
    line_value DECIMAL,
    over_odds INT,
    under_odds INT,
    milestone_odds INT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_player_props_game ON nfl_player_props(game_id);

-- Game Odds
CREATE TABLE nfl_game_odds (
    id TEXT PRIMARY KEY,
    game_id INT REFERENCES nfl_games(id),
    vendor TEXT,
    spread_home_value DECIMAL,
    spread_home_odds INT,
    spread_away_value DECIMAL,
    spread_away_odds INT,
    moneyline_home_odds INT,
    moneyline_away_odds INT,
    total_value DECIMAL,
    total_over_odds INT,
    total_under_odds INT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_game_odds_game ON nfl_game_odds(game_id);
