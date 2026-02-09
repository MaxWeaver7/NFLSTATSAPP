import logging
import os
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient
from src.ingestion.ingest_betting_and_extras import map_game_odds

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    cfg = SupabaseConfig.from_env()
    supabase = SupabaseClient(cfg)
    bdl = BallDontLieNFLClient(api_key=os.environ["BALLDONTLIE_API_KEY"])
    
    seasons = [2025]
    dates = ["2026-01-03"]  # Today's games
    
    # Fetch game IDs
    logger.info(f"Fetching games for {dates}...")
    all_games = list(bdl.iter_games(seasons=seasons))
    wanted = set(dates)
    games = [g for g in all_games if str(g.get("date","")).split("T")[0] in wanted]
    game_ids = [g["id"] for g in games if g.get("id")]
    
    logger.info(f"Found {len(game_ids)} games: {game_ids}")
    
    if not game_ids:
        logger.warning("No games found!")
        return
    
    # Fetch game odds (spreads)
    logger.info(f"\nFetching game odds for games {game_ids}...")
    game_odds_raw = list(bdl.iter_betting_odds(game_ids=game_ids))
    logger.info(f"Fetched {len(game_odds_raw)} raw odds records")
    
    # Show sample
    if game_odds_raw:
        logger.info("\n=== Sample Game Odds ===")
        for i, odd in enumerate(game_odds_raw[:3]):
            logger.info(f"\nOdds {i+1}:")
            logger.info(f"  Game ID: {odd.get('game_id')}")
            logger.info(f"  Vendor: {odd.get('vendor')}")
            logger.info(f"  Spread Home: {odd.get('spread_home_value')} ({odd.get('spread_home_odds')})")
            logger.info(f"  Spread Away: {odd.get('spread_away_value')} ({odd.get('spread_away_odds')})")
            logger.info(f"  Total: {odd.get('total_value')} (O:{odd.get('total_over_odds')}, U:{odd.get('total_under_odds')})")
            logger.info(f"  Moneyline: Home {odd.get('moneyline_home')}, Away {odd.get('moneyline_away')}")
        
        # Filter for DraftKings
        dk_odds = [map_game_odds(r) for r in game_odds_raw if (r.get("vendor") or "").lower() == "draftkings"]
        logger.info(f"\n=== DraftKings Odds Only ===")
        logger.info(f"DraftKings odds: {len(dk_odds)}")
        
        if dk_odds:
            logger.info("\n=== Attempting Database Upsert ===")
            try:
                supabase.upsert("nfl_betting_odds", dk_odds, on_conflict="game_id,vendor")
                logger.info(f"✅ Successfully inserted {len(dk_odds)} game odds!")
            except Exception as e:
                logger.error(f"❌ Database error: {e}")
                if dk_odds:
                    logger.info("\nFirst odds record that would be inserted:")
                    logger.info(dk_odds[0])
    else:
        logger.warning("No game odds returned!")

if __name__ == "__main__":
    main()

