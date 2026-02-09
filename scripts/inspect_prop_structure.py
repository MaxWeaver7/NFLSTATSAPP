import logging
import os
import json
from src.ingestion.balldontlie_client import BallDontLieNFLClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    bdl = BallDontLieNFLClient(api_key=os.environ["BALLDONTLIE_API_KEY"])
    
    # Fetch one prop and dump the entire structure
    logger.info("Fetching raw props to inspect structure...")
    raw_props = list(bdl.iter_player_props(game_id=424214, vendors=["draftkings"]))
    
    if raw_props:
        logger.info(f"\nFound {len(raw_props)} props. Full structure of first prop:\n")
        print(json.dumps(raw_props[0], indent=2))
    else:
        logger.warning("No props returned!")

if __name__ == "__main__":
    main()

