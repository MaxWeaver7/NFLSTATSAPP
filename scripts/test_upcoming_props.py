import logging
import os
from datetime import datetime, timedelta
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    cfg = SupabaseConfig.from_env()
    supabase = SupabaseClient(cfg)
    bdl = BallDontLieNFLClient(api_key=os.environ["BALLDONTLIE_API_KEY"])
    
    # Look for upcoming games in 2025 season (playoffs)
    logger.info("Fetching 2025 season games...")
    all_games = list(bdl.iter_games(seasons=[2025]))
    logger.info(f"Total 2025 games: {len(all_games)}")
    
    # Find games in the near future
    now = datetime.utcnow()
    upcoming = []
    for g in all_games:
        try:
            game_date = datetime.fromisoformat(g.get("date", "").replace("Z", "+00:00"))
            days_away = (game_date - now).days
            if -1 <= days_away <= 7:  # Games within next week or yesterday
                upcoming.append((g, days_away))
        except:
            pass
    
    upcoming.sort(key=lambda x: x[1])
    
    logger.info(f"Found {len(upcoming)} upcoming games in next 7 days")
    for g, days in upcoming[:5]:
        logger.info(f"  Game {g['id']}: {g.get('home_team', {}).get('abbreviation')} vs {g.get('visitor_team', {}).get('abbreviation')} - {days} days away on {g.get('date')}")
    
    if not upcoming:
        logger.warning("No upcoming games found to test props!")
        return
    
    # Test props for the next upcoming game
    test_game = upcoming[0][0]
    game_id = test_game["id"]
    logger.info(f"\nTesting props for game {game_id}...")
    
    vendors = ["draftkings", "fanduel", "betmgm"]
    total_props = 0
    for vendor in vendors:
        try:
            props = list(bdl.iter_player_props(game_id=game_id, vendors=[vendor]))
            logger.info(f"  {vendor}: {len(props)} props")
            total_props += len(props)
            if props:
                sample = props[0]
                logger.info(f"    Sample: {sample.get('player', {}).get('first_name')} {sample.get('player', {}).get('last_name')} - {sample.get('prop_type')} @ {sample.get('line_value')}")
        except Exception as e:
            logger.error(f"  {vendor} error: {e}")
    
    logger.info(f"\nTotal props before deduplication: {total_props}")

if __name__ == "__main__":
    main()

