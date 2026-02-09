import os
import sys
import logging
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient
from src.ingestion.balldontlie_ingestor import (
    ingest_core,
    ingest_team_season_stats,
    ingest_standings,
    ingest_stats_and_advanced,
    ingest_injuries,
    ingest_full_stats,
    ingest_odds,
    ingest_rosters,
    ingest_active_players
)
from src.utils.env import load_env

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest_v2")

def main():
    load_env()
    
    # Init Supabase
    sb_url = os.getenv("SUPABASE_URL")
    sb_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not sb_url or not sb_key:
        logger.error("Missing Supabase credentials")
        return

    sb = SupabaseClient(SupabaseConfig(url=sb_url, service_role_key=sb_key))
    
    # Init BDL
    bdl_key = os.getenv("BALLDONTLIE_API_KEY")
    if not bdl_key:
        logger.error("Missing BallDontLie API Key")
        return
        
    bdl = BallDontLieNFLClient(api_key=bdl_key)
    
    seasons = [2024, 2025] # Added 2024 for history
    
    logger.info("--- Starting Ingestion V2 (Full) for Seasons 2024-2025 ---")
    
    # 1. Core (Teams, Players, Games)
    logger.info("Ingesting Core Data...")
    ingest_core(seasons=seasons, supabase=sb, bdl=bdl)
    
    # 2. Team Season Stats & Standings & Advanced
    logger.info("Ingesting Team Season Stats, Standings, Advanced...")
    ingest_team_season_stats(seasons=seasons, supabase=sb, bdl=bdl)
    ingest_standings(seasons=seasons, supabase=sb, bdl=bdl)
    ingest_stats_and_advanced(seasons=seasons, supabase=sb, bdl=bdl, include_advanced=True)
    
    # 3. Full Extra Stats (New coverage)
    logger.info("Ingesting Full Game/Season Stats...")
    ingest_full_stats(seasons=seasons, supabase=sb, bdl=bdl)
    
    # 4. Injuries
    logger.info("Ingesting Injuries...")
    ingest_injuries(supabase=sb, bdl=bdl)
    
    # 5. Rosters
    logger.info("Ingesting Rosters...")
    ingest_rosters(seasons=seasons, supabase=sb, bdl=bdl)
    
    # 6. Active Players (Update Flags)
    logger.info("Updating Active Players Status...")
    ingest_active_players(supabase=sb, bdl=bdl)
    
    # 7. Odds (Optional - needs game_ids). 
    # Let's fetch game_ids for 2025 first.
    # We can get them from supabase or just use what core ingested?
    # For now, skipping explicit Odds trigger unless we fetch game IDs.
    # Assuming user wants data populated.
    # Let's iterate games to get IDs?
    # Using ingest_core populates them.
    # Let's query SB for game_ids to feed to odds ingestor?
    # For simplicity, we can skip ODDS for now or do a quick query.
    
    logger.info("--- Ingestion V2 Complete ---")

if __name__ == "__main__":
    main()
