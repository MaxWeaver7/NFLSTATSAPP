"""
Build WR/TE receiving feature matrices (train + inference) using Supabase data,
nfl_data_py externals, and advanced receiver/QB stats already stored in the DB.

Usage:
  python -m scripts.build_wr_features --seasons 2024 2025 --write

Environment:
  SUPABASE_DB_URI or DB_URI must point to the Postgres instance.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

import pandas as pd

from src.ingestion.features_wr_receiving import (
    FEATURE_COLUMNS,
    build_feature_matrices,
    get_engine,
    persist_features,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build WR/TE receiving feature tables")
    parser.add_argument("--seasons", nargs="+", type=int, default=[2024, 2025], help="Seasons to include")
    parser.add_argument("--playerid-csv", type=Path, default=Path("NFLAdvancedStats/data/db_playerids.csv"), help="Player ID mapping CSV")
    parser.add_argument("--write", action="store_true", help="Persist to database tables")
    parser.add_argument("--db-uri", type=str, default=None, help="Override DB URI (otherwise env SUPABASE_DB_URI or DB_URI)")
    return parser.parse_args()


def main(seasons: Sequence[int], playerid_csv: Path, write: bool, db_uri: str | None) -> int:
    logger.info("Building WR/TE features seasons=%s write=%s", seasons, write)
    engine = get_engine(db_uri)
    train, inf = build_feature_matrices(engine, seasons, str(playerid_csv))

    logger.info("Train rows=%s, columns=%s", len(train), len(train.columns))
    logger.info("Inference rows=%s, columns=%s", len(inf), len(inf.columns))
    missing_cols = [c for c in FEATURE_COLUMNS if c not in train.columns]
    if missing_cols:
        logger.warning("Missing feature columns: %s", missing_cols)

    if write:
        persist_features(train, inf, engine)
        logger.info("Persisted feature tables to database")

    preview_cols = ["player_id", "season", "week", "team_id", "label_receiving_yards", "prop_line_yards", "wopr", "snap_pct", "def_epa"]
    logger.info("Sample rows:\n%s", train[preview_cols].head(5).to_string(index=False) if not train.empty else "No data")

    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(main(args.seasons, args.playerid_csv, args.write, args.db_uri))


