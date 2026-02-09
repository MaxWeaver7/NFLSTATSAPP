#!/usr/bin/env python3
"""
Diagnostic script to check database state vs query expectations.
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.supabase_client import SupabaseClient, SupabaseConfig
from dotenv import load_dotenv

load_dotenv()

cfg = SupabaseConfig(
    url=os.getenv("SUPABASE_URL"),
    service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)
sb = SupabaseClient(cfg)

print("=== DATABASE DIAGNOSTIC ===\n")

# Check key tables
tables_to_check = [
    "nfl_teams",
    "nfl_players", 
    "nfl_games",
    "nfl_team_standings",
    "nfl_player_season_stats",
    "nfl_player_game_stats",
    "nfl_injuries",
    "nfl_game_lines"
]

for table in tables_to_check:
    try:
        # Get one row to see columns
        rows = sb.select(table, select="*", limit=1)
        if rows:
            cols = list(rows[0].keys())
            print(f"✅ {table}: {len(cols)} columns")
            print(f"   Columns: {', '.join(cols[:10])}")
            if len(cols) > 10:
                print(f"   ... and {len(cols)-10} more")
        else:
            print(f"⚠️  {table}: exists but EMPTY")
        
        # Get count
        count_rows = sb.select(table, select="id", limit=10000)
        print(f"   Rows: {len(count_rows)}\n")
        
    except Exception as e:
        print(f"❌ {table}: {str(e)}\n")

# Check specific columns queries need
print("\n=== CRITICAL COLUMN CHECKS ===\n")

checks = [
    ("nfl_teams", ["primary_color", "secondary_color", "logo_url"]),
    ("nfl_players", ["is_active"]),
    ("nfl_player_season_stats", ["qbr", "postseason"]),
]

for table, cols in checks:
    try:
        row = sb.select(table, select=",".join(cols), limit=1)
        print(f"✅ {table} has: {', '.join(cols)}")
    except Exception as e:
        print(f"❌ {table} missing: {e}")

print("\n=== DONE ===")
