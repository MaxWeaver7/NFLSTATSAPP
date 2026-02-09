from __future__ import annotations

import os

from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.ingestion.balldontlie_client import BallDontLieNFLClient
from src.ingestion.ingest_betting_and_extras import ingest_extras


def main() -> None:
    seasons = [2025]
    dates = None  # Fetch ALL games for the season

    cfg = SupabaseConfig.from_env()
    supabase = SupabaseClient(cfg)
    bdl = BallDontLieNFLClient(api_key=os.environ["BALLDONTLIE_API_KEY"])

    print(f"Fetching props and odds for Season {seasons} (all games)...")
    result = ingest_extras(supabase=supabase, bdl=bdl, seasons=seasons, dates=dates, batch_size=200)
    print("Ingest extras result:", result)


if __name__ == "__main__":
    main()

