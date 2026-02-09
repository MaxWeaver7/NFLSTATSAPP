from __future__ import annotations

import sqlite3
from typing import Iterable


DDL: list[str] = [
    # Core lookup tables
    """
    CREATE TABLE IF NOT EXISTS teams (
        team_abbr TEXT PRIMARY KEY,
        team_name TEXT,
        conference TEXT,
        division TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS players (
        player_id TEXT PRIMARY KEY,
        player_name TEXT,
        position TEXT,
        team_abbr TEXT,
        FOREIGN KEY(team_abbr) REFERENCES teams(team_abbr)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS games (
        game_id TEXT PRIMARY KEY,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        gameday TEXT,
        home_team TEXT,
        away_team TEXT,
        pfr_boxscore_url TEXT,
        FOREIGN KEY(home_team) REFERENCES teams(team_abbr),
        FOREIGN KEY(away_team) REFERENCES teams(team_abbr),
        UNIQUE(season, week, home_team, away_team)
    );
    """,
    # Raw play-by-play
    """
    CREATE TABLE IF NOT EXISTS plays (
        game_id TEXT NOT NULL,
        play_id INTEGER NOT NULL,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        posteam TEXT,
        defteam TEXT,
        play_type TEXT,
        desc TEXT,
        qtr INTEGER,
        down INTEGER,
        ydstogo INTEGER,
        yardline_100 REAL,
        yards_gained REAL,
        pass INTEGER,
        rush INTEGER,
        complete_pass INTEGER,
        incomplete_pass INTEGER,
        interception INTEGER,
        target INTEGER,
        receiver_id TEXT,
        rusher_id TEXT,
        passer_id TEXT,
        air_yards REAL,
        yards_after_catch REAL,
        epa REAL,
        cp REAL,
        cpoe REAL,
        xyac_epa REAL,
        xyac_mean_yardage REAL,
        PRIMARY KEY (game_id, play_id),
        FOREIGN KEY(game_id) REFERENCES games(game_id),
        FOREIGN KEY(posteam) REFERENCES teams(team_abbr),
        FOREIGN KEY(defteam) REFERENCES teams(team_abbr),
        FOREIGN KEY(receiver_id) REFERENCES players(player_id),
        FOREIGN KEY(rusher_id) REFERENCES players(player_id),
        FOREIGN KEY(passer_id) REFERENCES players(player_id)
    );
    """,
    # PFR (best-effort) supplemental tables
    """
    CREATE TABLE IF NOT EXISTS player_game_stats (
        player_id TEXT NOT NULL,
        game_id TEXT NOT NULL,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        team_abbr TEXT,
        snaps_offense INTEGER,
        snap_pct REAL,
        PRIMARY KEY (player_id, game_id),
        FOREIGN KEY(player_id) REFERENCES players(player_id),
        FOREIGN KEY(game_id) REFERENCES games(game_id),
        FOREIGN KEY(team_abbr) REFERENCES teams(team_abbr)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS receiving_advanced (
        player_id TEXT NOT NULL,
        game_id TEXT NOT NULL,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        team_abbr TEXT,
        targets INTEGER,
        receptions INTEGER,
        rec_yards REAL,
        air_yards REAL,
        ybc REAL,
        yac REAL,
        adot REAL,
        drops INTEGER,
        drop_pct REAL,
        broken_tackles INTEGER,
        routes INTEGER,
        PRIMARY KEY (player_id, game_id),
        FOREIGN KEY(player_id) REFERENCES players(player_id),
        FOREIGN KEY(game_id) REFERENCES games(game_id),
        FOREIGN KEY(team_abbr) REFERENCES teams(team_abbr)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS rushing_advanced (
        player_id TEXT NOT NULL,
        game_id TEXT NOT NULL,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        team_abbr TEXT,
        attempts INTEGER,
        rush_yards REAL,
        ybc REAL,
        yac REAL,
        broken_tackles INTEGER,
        PRIMARY KEY (player_id, game_id),
        FOREIGN KEY(player_id) REFERENCES players(player_id),
        FOREIGN KEY(game_id) REFERENCES games(game_id),
        FOREIGN KEY(team_abbr) REFERENCES teams(team_abbr)
    );
    """,
    # Derived tables
    """
    CREATE TABLE IF NOT EXISTS player_usage_metrics (
        player_id TEXT NOT NULL,
        game_id TEXT NOT NULL,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        team_abbr TEXT,
        routes_run INTEGER,
        targets INTEGER,
        targets_per_route REAL,
        snap_pct REAL,
        PRIMARY KEY (player_id, game_id),
        FOREIGN KEY(player_id) REFERENCES players(player_id),
        FOREIGN KEY(game_id) REFERENCES games(game_id),
        FOREIGN KEY(team_abbr) REFERENCES teams(team_abbr)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS player_efficiency_metrics (
        player_id TEXT NOT NULL,
        game_id TEXT NOT NULL,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        team_abbr TEXT,
        yprr REAL,
        epa_per_target REAL,
        yac_per_reception REAL,
        cpoe_avg REAL,
        air_yards_per_target REAL,
        PRIMARY KEY (player_id, game_id),
        FOREIGN KEY(player_id) REFERENCES players(player_id),
        FOREIGN KEY(game_id) REFERENCES games(game_id),
        FOREIGN KEY(team_abbr) REFERENCES teams(team_abbr)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS season_aggregates (
        player_id TEXT NOT NULL,
        season INTEGER NOT NULL,
        team_abbr TEXT,
        position TEXT,
        total_routes INTEGER,
        targets INTEGER,
        receptions INTEGER,
        rec_yards REAL,
        air_yards REAL,
        target_share REAL,
        air_yards_share REAL,
        weighted_efficiency_score REAL,
        PRIMARY KEY (player_id, season, team_abbr),
        FOREIGN KEY(player_id) REFERENCES players(player_id),
        FOREIGN KEY(team_abbr) REFERENCES teams(team_abbr)
    );
    """,
    # Indexes for query performance
    "CREATE INDEX IF NOT EXISTS idx_plays_season_week ON plays(season, week);",
    "CREATE INDEX IF NOT EXISTS idx_plays_receiver ON plays(receiver_id);",
    "CREATE INDEX IF NOT EXISTS idx_plays_passer ON plays(passer_id);",
    "CREATE INDEX IF NOT EXISTS idx_games_season_week ON games(season, week);",
]


def create_tables(conn: sqlite3.Connection, ddl: Iterable[str] = DDL) -> None:
    cur = conn.cursor()
    for stmt in ddl:
        cur.execute(stmt)
    conn.commit()


