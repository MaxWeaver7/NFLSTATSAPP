#!/usr/bin/env python3
"""
Manually create nfl_data_py tables by executing SQL statements one at a time.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.supabase_client import SupabaseClient
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def main():
    sb = SupabaseClient(
        url=os.getenv("SUPABASE_URL"),
        service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    # SQL statements to execute
    statements = [
        # Player ID Mapping
        """
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
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_player_id_mapping_name ON nfl_player_id_mapping(name)",
        "CREATE INDEX IF NOT EXISTS idx_player_id_mapping_espn ON nfl_player_id_mapping(espn_id)",
        
        # Game Lines
        """
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
            spread_line DECIMAL,
            total_line DECIMAL,
            over_odds INT,
            under_odds INT,
            home_moneyline INT,
            away_moneyline INT,
            home_spread_odds INT,
            away_spread_odds INT,
            roof TEXT,
            surface TEXT,
            temp INT,
            wind INT,
            stadium TEXT,
            home_coach TEXT,
            away_coach TEXT,
            referee TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_game_lines_season_week ON nfl_game_lines(season, week)",
        "CREATE INDEX IF NOT EXISTS idx_game_lines_teams ON nfl_game_lines(home_team, away_team)",
        
        # Snap Counts
        """
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
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_snap_counts_player ON nfl_snap_counts(pfr_player_id)",
        "CREATE INDEX IF NOT EXISTS idx_snap_counts_season_week ON nfl_snap_counts(season, week)",
    ]
    
    logger.info("Creating nfl_data_py tables...")
    
    # Use Supabase RPC to execute SQL
    for i, sql in enumerate(statements):
        try:
            logger.info(f"Executing statement {i+1}/{len(statements)}...")
            # Supabase doesn't have a direct SQL execution endpoint via REST API
            # We need to use PostgREST's RPC endpoint
            # For now, let's just print the SQL
            print(sql.strip())
            print()
        except Exception as e:
            logger.error(f"Failed on statement {i+1}: {e}")
    
    print("\n\n=== COPY THIS SQL TO SUPABASE SQL EDITOR ===\n")

if __name__ == "__main__":
    main()
