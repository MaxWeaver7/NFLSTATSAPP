"""
Props and Odds ONLY ingestion - skips team stats, standings, injuries
"""
import logging
import os
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient
from src.ingestion.ingest_betting_and_extras import _get_best_props, VENDOR_PRIORITY, map_game_odds

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    seasons = [2025]
    dates = None  # All games
    
    cfg = SupabaseConfig.from_env()
    supabase = SupabaseClient(cfg)
    bdl = BallDontLieNFLClient(api_key=os.environ["BALLDONTLIE_API_KEY"])
    
    # Fetch game IDs
    print(f"Fetching games for season {seasons}...")
    all_games = list(bdl.iter_games(seasons=seasons))
    
    if dates:
        wanted = set(dates)
        games = [g for g in all_games if str(g.get("date","")).split("T")[0] in wanted]
    else:
        games = all_games
        
    game_ids = [g["id"] for g in games if g.get("id")]
    print(f"✓ Found {len(game_ids)} games")
    
    props_count = 0
    odds_count = 0
    
    # SPREADS/ODDS - One batch call
    print(f"\n📊 Fetching game odds (spreads/totals)...")
    try:
        game_odds_raw = list(bdl.iter_betting_odds(game_ids=game_ids))
        dk_odds = [map_game_odds(r) for r in game_odds_raw if (r.get("vendor") or "").lower() == "draftkings"]
        
        if dk_odds:
            supabase.upsert("nfl_betting_odds", dk_odds, on_conflict="id")
            odds_count = len(dk_odds)
            print(f"✓ Upserted {odds_count} DraftKings odds")
    except Exception as e:
        print(f"✗ Odds error: {e}")
    
    # PROPS - Game by game with progress
    print(f"\n🎯 Fetching player props (5 vendors with dedup)...")
    api_vendors = list(VENDOR_PRIORITY.keys())
    
    for i, gid in enumerate(game_ids):
        try:
            raw_props = list(bdl.iter_player_props(game_id=gid, vendors=api_vendors))
            best_props = _get_best_props(raw_props)
            
            if best_props:
                supabase.upsert("nfl_player_props", best_props, on_conflict="id")
                props_count += len(best_props)
            
            if (i + 1) % 25 == 0:
                print(f"  Progress: {i+1}/{len(game_ids)} games, {props_count} props so far...")
        except Exception as e:
            print(f"✗ Props error game {gid}: {e}")
    
    print(f"\n✅ DONE!")
    print(f"  Game Odds: {odds_count}")
    print(f"  Player Props: {props_count}")

if __name__ == "__main__":
    main()

