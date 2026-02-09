#!/usr/bin/env python3
"""
Run nfl_data_py ingestion for snap counts, game lines, and player ID mapping.
This complements BDL data with EPA, betting lines, weather, and snap counts.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.nfl_data_py_ingestor import (
    ingest_historic_game_lines,
    ingest_snap_counts,
    ingest_player_id_mappings
)
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def main():
    logger.info("=== Starting nfl_data_py Ingestion (Complementary Data) ===")
    
    cfg = SupabaseConfig(
        url=os.getenv("SUPABASE_URL"),
        service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    sb = SupabaseClient(cfg)
    
   # Ingest for 2024 and 2025 seasons
    seasons = [2024, 2025]
    
    logger.info("Running complete nfl_data_py ingestion...")
    try:
        from src.ingestion.nfl_data_py_ingestor import ingest_all
        result = ingest_all(
            seasons=seasons,
            supabase=sb,
            include_player_ids=True,
            include_game_lines=True,
            include_snap_counts=True
        )
        logger.info(f"✅ Complete! Player IDs: {result.player_ids_upserted}, Game Lines: {result.game_lines_upserted}, Snap Counts: {result.snap_counts_upserted}")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
     
    logger.info("=== nfl_data_py Ingestion Complete ===")

if __name__ == "__main__":
    main()
