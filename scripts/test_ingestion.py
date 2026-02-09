#!/usr/bin/env python3
"""
Test script to verify data ingestion from both sources.
Run this to test the ingestion before running full ingest.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_nfl_data_py():
    """Test nfl_data_py ingestion functions."""
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    
    print("\n" + "=" * 60)
    print("TESTING NFL_DATA_PY INGESTION")
    print("=" * 60)
    
    load_env()
    cfg = SupabaseConfig.from_env()
    sb = SupabaseClient(cfg)
    
    from src.ingestion.nfl_data_py_ingestor import (
        ingest_player_id_mappings,
        ingest_historic_game_lines,
        ingest_snap_counts,
    )
    
    # Test 1: Player ID mappings
    print("\n📋 Testing player ID mappings...")
    try:
        count = ingest_player_id_mappings(supabase=sb, batch_size=500)
        print(f"   ✅ Upserted {count} player ID mappings")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Historic game lines (just 2024 for now)
    print("\n📊 Testing historic game lines...")
    try:
        count = ingest_historic_game_lines(seasons=[2024, 2025], supabase=sb, batch_size=500)
        print(f"   ✅ Upserted {count} game lines with betting data")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Snap counts
    print("\n🏃 Testing snap counts...")
    try:
        count = ingest_snap_counts(seasons=[2024], supabase=sb, batch_size=500)
        print(f"   ✅ Upserted {count} snap count records")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    return True


def test_balldontlie():
    """Test BallDontLie ingestion functions."""
    print("\n" + "=" * 60)
    print("TESTING BALLDONTLIE INGESTION")
    print("=" * 60)
    
    load_env()
    cfg = SupabaseConfig.from_env()
    sb = SupabaseClient(cfg)
    
    from src.ingestion.balldontlie_client import BallDontLieNFLClient
    from src.ingestion.balldontlie_ingestor import (
        ingest_injuries,
        ingest_standings,
        ingest_team_season_stats,
    )
    
    api_key = os.getenv("BALLDONTLIE_API_KEY")
    if not api_key:
        print("❌ BALLDONTLIE_API_KEY not set")
        return False
    
    bdl = BallDontLieNFLClient(api_key=api_key)
    
    # Test 1: Injuries
    print("\n🏥 Testing injury ingestion...")
    try:
        count = ingest_injuries(supabase=sb, bdl=bdl)
        print(f"   ✅ Upserted {count} injuries")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Standings
    print("\n🏆 Testing standings ingestion...")
    try:
        count = ingest_standings(seasons=[2024, 2025], supabase=sb, bdl=bdl)
        print(f"   ✅ Upserted {count} standings")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Team season stats
    print("\n📈 Testing team season stats...")
    try:
        count = ingest_team_season_stats(seasons=[2024, 2025], supabase=sb, bdl=bdl)
        print(f"   ✅ Upserted {count} team stats")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    return True


def verify_data():
    """Verify data was ingested correctly."""
    print("\n" + "=" * 60)
    print("VERIFYING INGESTED DATA")
    print("=" * 60)
    
    load_env()
    cfg = SupabaseConfig.from_env()
    sb = SupabaseClient(cfg)
    
    tables = [
        ("nfl_player_id_mapping", "gsis_id,name", 5),
        ("nfl_game_lines", "nflverse_game_id,home_team,spread_line,total_line", 3),
        ("nfl_snap_counts", "player_name,season,week,offense_pct", 3),
        ("nfl_injuries", "player_id,status,comment", 5),
        ("nfl_team_standings", "team_id,season,wins,losses", 5),
    ]
    
    for table, cols, limit in tables:
        print(f"\n📊 {table}:")
        try:
            rows = sb.select(table, select=cols, limit=limit)
            if rows:
                for r in rows:
                    print(f"   {r}")
            else:
                print("   (no data)")
        except Exception as e:
            print(f"   ⚠️ Error querying: {e}")


if __name__ == "__main__":
    print("🏈 NFL DATA INGESTION TEST")
    print("This will test ingestion from both nfl_data_py and BallDontLie")
    print()
    
    # Run tests
    nfl_py_ok = test_nfl_data_py()
    bdl_ok = test_balldontlie()
    
    # Verify
    verify_data()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"nfl_data_py: {'✅ OK' if nfl_py_ok else '❌ FAILED'}")
    print(f"BallDontLie: {'✅ OK' if bdl_ok else '❌ FAILED'}")
