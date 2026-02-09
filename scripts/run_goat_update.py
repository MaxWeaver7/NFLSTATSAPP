import logging
import os
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient
from src.ingestion.ingest_betting_and_extras import ingest_extras

logging.basicConfig(level=logging.INFO)

def main():
    config = SupabaseConfig.from_env()
    supabase = SupabaseClient(config.url, config.key)
    
    bdl_key = os.environ.get("BALLDONTLIE_API_KEY")
    bdl = BallDontLieNFLClient(api_key=bdl_key)

    # 2025 Season - Full Ingest
    SEASON = [2025]
    
    print(f"Starting Ingestion for Season {SEASON} (DraftKings / Over-Under Only)...")
    
    # Passing dates=None to fetch the entire season history
    result = ingest_extras(
        supabase=supabase, 
        bdl=bdl, 
        seasons=SEASON, 
        dates=None 
    )
    print("Ingestion Result:", result)

if __name__ == "__main__":
    main()