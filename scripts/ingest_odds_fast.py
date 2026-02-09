"""
Fast test script for props and odds ingestion.
Only fetches data for TODAY'S games.
"""
import logging
import os
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient
from src.ingestion.ingest_betting_and_extras import ingest_extras

logging.basicConfig(level=logging.WARNING)  # Less verbose
logger = logging.getLogger(__name__)

def main():
    seasons = [2025]
    dates = ["2026-01-03", "2026-01-04", "2026-01-05"]  # This weekend only
    
    cfg = SupabaseConfig.from_env()
    supabase = SupabaseClient(cfg)
    bdl = BallDontLieNFLClient(api_key=os.environ["BALLDONTLIE_API_KEY"])
    
    print(f"Fetching props and odds for {dates} only (fast test)...")
    result = ingest_extras(supabase=supabase, bdl=bdl, seasons=seasons, dates=dates, batch_size=200)
    print(f"\n✅ Results: {result}")

if __name__ == "__main__":
    main()

