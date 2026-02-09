import logging
import os
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    cfg = SupabaseConfig.from_env()
    supabase = SupabaseClient(cfg)
    bdl = BallDontLieNFLClient(api_key=os.environ["BALLDONTLIE_API_KEY"])
    
    # Test 1: Fetch games for specific dates
    seasons = [2024]
    dates = ["2025-01-04", "2025-01-05"]
    
    logger.info(f"Fetching games for seasons {seasons}")
    all_games = list(bdl.iter_games(seasons=seasons))
    logger.info(f"Total games: {len(all_games)}")
    
    if dates:
        wanted = set(dates)
        games = [g for g in all_games if str(g.get("date","")).split("T")[0] in wanted]
        logger.info(f"Games on {dates}: {len(games)}")
        
        for g in games:
            logger.info(f"  Game {g['id']}: {g.get('home_team', {}).get('abbreviation')} vs {g.get('visitor_team', {}).get('abbreviation')} on {g.get('date')}")
    else:
        games = all_games
    
    if not games:
        logger.warning("No games found for the specified dates!")
        return
    
    # Test 2: Try fetching props for first game
    first_game_id = games[0]["id"]
    logger.info(f"\nTesting props for game {first_game_id}...")
    
    vendors = ["draftkings", "fanduel", "betmgm", "bet365", "betway"]
    for vendor in vendors:
        logger.info(f"  Trying vendor: {vendor}")
        try:
            props = list(bdl.iter_player_props(game_id=first_game_id, vendors=[vendor]))
            logger.info(f"    Found {len(props)} props from {vendor}")
            if props:
                sample = props[0]
                logger.info(f"    Sample prop: player={sample.get('player', {}).get('first_name')} {sample.get('player', {}).get('last_name')}, type={sample.get('prop_type')}, vendor={sample.get('bookmaker')}")
        except Exception as e:
            logger.error(f"    Error fetching {vendor}: {e}")

if __name__ == "__main__":
    main()

