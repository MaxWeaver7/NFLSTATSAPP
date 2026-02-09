from __future__ import annotations

import logging
import os
import sys

from src.database.connection import connect
from src.database.schema import create_tables
from src.ingestion.nflfastr_ingestor import ingest_pbp
from src.ingestion.pfr_scraper import scrape_pfr_for_games
from src.metrics.calculator import compute_all_metrics
from src.utils.env import getenv_bool, getenv_float, load_env
from src.utils.logging import configure_logging
from src.validation.checks import run_all_checks


logger = logging.getLogger(__name__)


def _parse_seasons(raw: str) -> list[int]:
    seasons: list[int] = []
    for part in raw.split(","):
        s = part.strip()
        if not s:
            continue
        seasons.append(int(s))
    return seasons


def main() -> int:
    load_env()
    configure_logging()

    db_path = os.getenv("NFL_DB_PATH", "data/nfl_data.db")
    seasons = _parse_seasons(os.getenv("NFL_SEASONS", "2024,2025"))
    pfr_enabled = getenv_bool("PFR_ENABLE", default=False)
    pfr_delay = getenv_float("PFR_REQUEST_DELAY_SECONDS", default=2.5)
    pfr_cache_dir = os.getenv("PFR_CACHE_DIR", "data/pfr_cache")
    pfr_game_ids_raw = os.getenv("PFR_GAME_IDS", "").strip()
    pfr_game_ids = [s.strip() for s in pfr_game_ids_raw.split(",") if s.strip()] if pfr_game_ids_raw else None
    pfr_max_games_raw = os.getenv("PFR_MAX_GAMES", "").strip()
    pfr_max_games = int(pfr_max_games_raw) if pfr_max_games_raw else None

    logger.info("DB=%s seasons=%s PFR=%s", db_path, seasons, pfr_enabled)

    conn = connect(db_path)
    create_tables(conn)

    # 1) Ingest pbp
    ingest_pbp(seasons, conn)

    # 2) Best-effort PFR scrape (skips games without URL)
    scrape_pfr_for_games(
        conn,
        cache_dir=pfr_cache_dir,
        delay_seconds=pfr_delay,
        enabled=pfr_enabled,
        game_ids=pfr_game_ids,
        max_games=pfr_max_games,
    )

    # 3) Compute derived metrics
    compute_all_metrics(conn)

    # 4) Run validations
    errors = run_all_checks(conn)
    if errors:
        logger.error("Validation failed (%d issues):", len(errors))
        for e in errors[:50]:
            logger.error(" - %s", e)
        if len(errors) > 50:
            logger.error(" ... and %d more", len(errors) - 50)
        return 1

    logger.info("Done. No validation issues found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


