#!/usr/bin/env python3
"""
Sync injuries manually.
"""
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env
from src.ingestion.balldontlie_client import BallDontLieNFLClient
from src.ingestion.balldontlie_ingestor import ingest_injuries

logging.basicConfig(level=logging.INFO)

def main():
    load_env()
    cfg = SupabaseConfig.from_env()
    sb = SupabaseClient(cfg)
    
    api_key = os.getenv("BALLDONTLIE_API_KEY")
    if not api_key:
        print("No API KEY")
        return
        
    bdl = BallDontLieNFLClient(api_key=api_key)
    
    print("Starting injury sync...")
    count = ingest_injuries(supabase=sb, bdl=bdl)
    print(f"Sync complete. Ingested {count} injuries.")

if __name__ == "__main__":
    main()
