#!/usr/bin/env python3
"""
Comprehensive data diagnostic - shows exactly what's in the database.
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

print("=" * 60)
print("COMPREHENSIVE DATA DIAGNOSTIC")
print("=" * 60)

# 1. PLAYERS
print("\n== PLAYERS ==")
try:
    # Total count
    all_players = sb.select("nfl_players", select="id,first_name,last_name,team_id,position", limit=15000)
    print(f"Total players: {len(all_players)}")
    
    # Check for Bijan Robinson specifically
    bijan = [p for p in all_players if 'bijan' in (p.get('first_name') or '').lower() or 'robinson' in (p.get('last_name') or '').lower()]
    print(f"Players with 'Bijan' or 'Robinson': {len(bijan)}")
    for p in bijan[:5]:
        print(f"  - {p.get('first_name')} {p.get('last_name')} (ID: {p.get('id')}, pos: {p.get('position')})")
    
    # Active players
    active = [p for p in all_players if p.get('is_active')]
    print(f"Active players (is_active=true): {len(active)}")
    
except Exception as e:
    print(f"ERROR: {e}")

# 2. PLAYER SEASON STATS
print("\n== PLAYER SEASON STATS ==")
try:
    stats = sb.select("nfl_player_season_stats", select="player_id,season,games_played,rushing_yards,receiving_yards,passing_yards", limit=10000)
    print(f"Total season stat rows: {len(stats)}")
    
    # By season
    seasons = {}
    for s in stats:
        yr = s.get('season')
        seasons[yr] = seasons.get(yr, 0) + 1
    print(f"By season: {seasons}")
    
    # Players with rushing yards
    rushers = [s for s in stats if (s.get('rushing_yards') or 0) > 0]
    print(f"Players with rushing yards: {len(rushers)}")
    
    # Top rushers
    top_rush = sorted(rushers, key=lambda x: x.get('rushing_yards') or 0, reverse=True)[:5]
    print("Top 5 rushers (season stats):")
    for r in top_rush:
        print(f"  - Player ID {r.get('player_id')}: {r.get('rushing_yards')} yards")
        
except Exception as e:
    print(f"ERROR: {e}")

# 3. PLAYER GAME STATS (Weekly)
print("\n== PLAYER GAME STATS (WEEKLY) ==")
try:
    game_stats = sb.select("nfl_player_game_stats", select="player_id,season,week,rushing_yards,receiving_yards,passing_yards", limit=20000)
    print(f"Total game stat rows: {len(game_stats)}")
    
    # By season
    seasons = {}
    for s in game_stats:
        yr = s.get('season')
        seasons[yr] = seasons.get(yr, 0) + 1
    print(f"By season: {seasons}")
    
    # By week (2025)
    weeks = {}
    for s in game_stats:
        if s.get('season') == 2025:
            wk = s.get('week')
            weeks[wk] = weeks.get(wk, 0) + 1
    print(f"2025 by week: {dict(sorted(weeks.items()))}")
    
except Exception as e:
    print(f"ERROR: {e}")

# 4. ADVANCED STATS
print("\n== ADVANCED STATS ==")
try:
    adv_rec = sb.select("nfl_advanced_receiving_stats", select="player_id,season", limit=1000)
    print(f"Advanced receiving stats: {len(adv_rec)}")
except Exception as e:
    print(f"Advanced receiving: {e}")

try:
    adv_rush = sb.select("nfl_advanced_rushing_stats", select="player_id,season", limit=1000)
    print(f"Advanced rushing stats: {len(adv_rush)}")
except Exception as e:
    print(f"Advanced rushing: {e}")

try:
    adv_pass = sb.select("nfl_advanced_passing_stats", select="player_id,season", limit=1000)
    print(f"Advanced passing stats: {len(adv_pass)}")
except Exception as e:
    print(f"Advanced passing: {e}")

# 5. TEAM DATA
print("\n== TEAM DATA ==")
try:
    standings = sb.select("nfl_team_standings", select="team_id,season,wins,losses", limit=100)
    print(f"Team standings: {len(standings)}")
    
    # Check for ATS columns
    full_standings = sb.select("nfl_team_standings", select="*", limit=1)
    if full_standings:
        cols = list(full_standings[0].keys())
        print(f"Standings columns: {cols}")
        ats_cols = [c for c in cols if 'ats' in c.lower()]
        print(f"ATS columns: {ats_cols if ats_cols else 'NONE'}")
except Exception as e:
    print(f"ERROR: {e}")

# 6. NFL_DATA_PY TABLES
print("\n== NFL_DATA_PY TABLES ==")
try:
    game_lines = sb.select("nfl_game_lines", select="nflverse_game_id,season,week", limit=100)
    print(f"Game lines: {len(game_lines)}")
except Exception as e:
    print(f"Game lines: {e}")

try:
    id_mapping = sb.select("nfl_player_id_mapping", select="gsis_id,espn_id", limit=100)
    print(f"Player ID mapping: {len(id_mapping)}")
except Exception as e:
    print(f"ID mapping: {e}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
