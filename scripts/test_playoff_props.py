import logging
import os
from datetime import datetime, timezone
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient
from src.ingestion.ingest_betting_and_extras import _get_best_props, VENDOR_PRIORITY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    cfg = SupabaseConfig.from_env()
    supabase = SupabaseClient(cfg)
    bdl = BallDontLieNFLClient(api_key=os.environ["BALLDONTLIE_API_KEY"])
    
    # Look for all 2025 season games
    logger.info("Fetching 2025 season games...")
    all_games = list(bdl.iter_games(seasons=[2025]))
    logger.info(f"Total 2025 games: {len(all_games)}")
    
    # Show first 10 games with dates
    logger.info("\nFirst 10 games:")
    for g in all_games[:10]:
        logger.info(f"  Game {g['id']}: {g.get('home_team', {}).get('abbreviation')} vs {g.get('visitor_team', {}).get('abbreviation')} on {g.get('date')}")
    
    if not all_games:
        logger.warning("No games found!")
        return
    
    # Test props for the first game
    test_game = all_games[0]
    game_id = test_game["id"]
    logger.info(f"\nTesting props for first game {game_id}...")
    logger.info(f"  Matchup: {test_game.get('home_team', {}).get('abbreviation')} vs {test_game.get('visitor_team', {}).get('abbreviation')}")
    logger.info(f"  Date: {test_game.get('date')}")
    
    # Test with all priority vendors
    vendors = list(VENDOR_PRIORITY.keys())
    logger.info(f"  Vendors: {vendors}")
    
    all_raw_props = []
    for vendor in vendors:
        try:
            props = list(bdl.iter_player_props(game_id=game_id, vendors=[vendor]))
            logger.info(f"    {vendor}: {len(props)} props")
            all_raw_props.extend(props)
            
            if props and vendor == "draftkings":  # Show samples from DK
                for i, p in enumerate(props[:3]):
                    player = p.get('player', {})
                    logger.info(f"      Sample {i+1}: {player.get('first_name')} {player.get('last_name')} - {p.get('prop_type')} @ {p.get('line_value')}")
        except Exception as e:
            logger.error(f"    {vendor} error: {e}")
    
    logger.info(f"\nTotal raw props from all vendors: {len(all_raw_props)}")
    
    if all_raw_props:
        # Test the deduplication logic
        logger.info("\nTesting _get_best_props() deduplication...")
        best_props = _get_best_props(all_raw_props)
        logger.info(f"Props after deduplication: {len(best_props)}")
        logger.info(f"Reduction: {len(all_raw_props) - len(best_props)} props filtered ({((len(all_raw_props) - len(best_props)) / len(all_raw_props) * 100):.1f}%)")
        
        # Show vendor distribution
        vendor_counts = {}
        for prop in best_props:
            v = prop.get('vendor', 'unknown')
            vendor_counts[v] = vendor_counts.get(v, 0) + 1
        
        logger.info("\nFinal vendor distribution:")
        for vendor, count in sorted(vendor_counts.items(), key=lambda x: VENDOR_PRIORITY.get(x[0], 99)):
            logger.info(f"  {vendor}: {count} props")

if __name__ == "__main__":
    main()

