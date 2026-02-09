import logging
import os
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient
from src.ingestion.ingest_betting_and_extras import _get_best_props, VENDOR_PRIORITY

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
    
    # Test first game
    gid = game_ids[0]
    logger.info(f"\nFetching props for game {gid}...")
    
    api_vendors = list(VENDOR_PRIORITY.keys())
    logger.info(f"Vendors: {api_vendors}")
    
    # Fetch raw props
    raw_props = list(bdl.iter_player_props(game_id=gid, vendors=api_vendors))
    logger.info(f"Fetched {len(raw_props)} raw props from API")
    
    # Debug: Show first few props
    logger.info("\n=== Sample Raw Props ===")
    for i, prop in enumerate(raw_props[:3]):
        logger.info(f"\nProp {i+1}:")
        logger.info(f"  ID: {prop.get('id')}")
        logger.info(f"  Game ID: {prop.get('game_id')}")
        logger.info(f"  Prop Type: {prop.get('prop_type')}")
        logger.info(f"  Line Value: {prop.get('line_value')}")
        logger.info(f"  Vendor/Bookmaker: {prop.get('vendor')} / {prop.get('bookmaker')}")
        logger.info(f"  Market: {prop.get('market')}")
        player = prop.get('player', {})
        logger.info(f"  Player Object: {player}")
        logger.info(f"  Player ID: {player.get('id') if player else 'NO PLAYER OBJECT'}")
    
    # Now run through the filter
    logger.info("\n=== Running _get_best_props() ===")
    best_props = _get_best_props(raw_props)
    logger.info(f"Props after filtering: {len(best_props)}")
    
    if len(best_props) < len(raw_props):
        logger.info(f"Filtered out {len(raw_props) - len(best_props)} props")
    
    if best_props:
        logger.info("\n=== Attempting Database Upsert ===")
        try:
            supabase.upsert("nfl_player_props", best_props, on_conflict="id")
            logger.info(f"✅ Successfully inserted {len(best_props)} props!")
        except Exception as e:
            logger.error(f"❌ Database error: {e}")
            logger.info("\nFirst prop that would be inserted:")
            logger.info(best_props[0])
    else:
        logger.warning("No props passed filtering!")

if __name__ == "__main__":
    main()

