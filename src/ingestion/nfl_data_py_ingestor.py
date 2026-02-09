"""
NFL Data Py Ingestor

Ingests data from nfl_data_py (nflfastR/nflverse) into Supabase.
This complements the BallDontLie ingestor with historic data.
"""
from __future__ import annotations

import logging
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

import pandas as pd

from src.database.supabase_client import SupabaseClient

# Fix SSL certificate issue on macOS
ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chunked(items: list[dict], size: int) -> Iterator[list[dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


@dataclass(frozen=True)
class NFLPyIngestSummary:
    player_ids_upserted: int
    game_lines_upserted: int
    snap_counts_upserted: int


def ingest_player_id_mappings(
    *, 
    supabase: SupabaseClient, 
    batch_size: int = 500
) -> int:
    """
    Ingest player ID mappings from nfl_data_py.
    Creates cross-reference between gsis_id, espn_id, and player names.
    """
    import nfl_data_py as nfl
    
    logger.info("Fetching player IDs from nfl_data_py...")
    ids_df = nfl.import_ids()
    
    rows = []
    for _, row in ids_df.iterrows():
        # Skip rows without gsis_id (needed for PBP matching)
        if pd.isna(row.get('gsis_id')):
            continue
            
        rows.append({
            "gsis_id": row.get("gsis_id"),
            "name": row.get("name"),
            "position": row.get("position"),
            "team": row.get("team"),
            "espn_id": int(row["espn_id"]) if pd.notna(row.get("espn_id")) else None,
            "yahoo_id": int(row["yahoo_id"]) if pd.notna(row.get("yahoo_id")) else None,
            "sleeper_id": row.get("sleeper_id") if pd.notna(row.get("sleeper_id")) else None,
            "pfr_id": row.get("pfr_id") if pd.notna(row.get("pfr_id")) else None,
            "updated_at": _now_iso(),
        })
    
    logger.info("Upserting %d player ID mappings...", len(rows))
    upserted = 0
    for chunk in _chunked(rows, batch_size):
        upserted += supabase.upsert(
            "nfl_player_id_mapping", 
            chunk, 
            on_conflict="gsis_id"
        )
    
    logger.info("Upserted nfl_player_id_mapping=%d", upserted)
    return upserted


def ingest_historic_game_lines(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    batch_size: int = 500,
) -> int:
    """
    Ingest historic betting lines from nfl_data_py schedules.
    Includes spreads, totals, moneylines, and weather data.
    """
    import nfl_data_py as nfl
    
    logger.info("Fetching schedules for seasons %s...", seasons)
    sched = nfl.import_schedules(seasons)
    
    rows = []
    for _, row in sched.iterrows():
        # Skip if no betting data
        if pd.isna(row.get("spread_line")):
            continue
            
        rows.append({
            "nflverse_game_id": row.get("game_id"),
            "season": int(row.get("season")),
            "week": int(row.get("week")),
            "game_type": row.get("game_type"),
            "gameday": str(row.get("gameday")) if pd.notna(row.get("gameday")) else None,
            "home_team": row.get("home_team"),
            "away_team": row.get("away_team"),
            "home_score": int(row["home_score"]) if pd.notna(row.get("home_score")) else None,
            "away_score": int(row["away_score"]) if pd.notna(row.get("away_score")) else None,
            "spread_line": float(row["spread_line"]) if pd.notna(row.get("spread_line")) else None,
            "total_line": float(row["total_line"]) if pd.notna(row.get("total_line")) else None,
            "over_odds": int(row["over_odds"]) if pd.notna(row.get("over_odds")) else None,
            "under_odds": int(row["under_odds"]) if pd.notna(row.get("under_odds")) else None,
            "home_moneyline": int(row["home_moneyline"]) if pd.notna(row.get("home_moneyline")) else None,
            "away_moneyline": int(row["away_moneyline"]) if pd.notna(row.get("away_moneyline")) else None,
            "home_spread_odds": int(row["home_spread_odds"]) if pd.notna(row.get("home_spread_odds")) else None,
            "away_spread_odds": int(row["away_spread_odds"]) if pd.notna(row.get("away_spread_odds")) else None,
            # Weather and venue
            "roof": row.get("roof") if pd.notna(row.get("roof")) else None,
            "surface": row.get("surface") if pd.notna(row.get("surface")) else None,
            "temp": int(row["temp"]) if pd.notna(row.get("temp")) else None,
            "wind": int(row["wind"]) if pd.notna(row.get("wind")) else None,
            "stadium": row.get("stadium") if pd.notna(row.get("stadium")) else None,
            # Extra context
            "home_coach": row.get("home_coach") if pd.notna(row.get("home_coach")) else None,
            "away_coach": row.get("away_coach") if pd.notna(row.get("away_coach")) else None,
            "referee": row.get("referee") if pd.notna(row.get("referee")) else None,
            "updated_at": _now_iso(),
        })
    
    logger.info("Upserting %d game lines...", len(rows))
    upserted = 0
    for chunk in _chunked(rows, batch_size):
        upserted += supabase.upsert(
            "nfl_game_lines",
            chunk,
            on_conflict="nflverse_game_id"
        )
    
    logger.info("Upserted nfl_game_lines=%d", upserted)
    return upserted


def ingest_snap_counts(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    batch_size: int = 500,
) -> int:
    """
    Ingest weekly snap count data from nfl_data_py.
    """
    import nfl_data_py as nfl
    
    logger.info("Fetching snap counts for seasons %s...", seasons)
    snaps = nfl.import_snap_counts(seasons)
    
    rows = []
    for _, row in snaps.iterrows():
        # Need player identification
        if pd.isna(row.get("pfr_player_id")):
            continue
            
        rows.append({
            "pfr_player_id": row.get("pfr_player_id"),
            "player_name": row.get("player"),
            "season": int(row.get("season")),
            "week": int(row.get("week")),
            "game_type": row.get("game_type") if pd.notna(row.get("game_type")) else "REG",
            "team": row.get("team"),
            "position": row.get("position"),
            "offense_snaps": int(row["offense_snaps"]) if pd.notna(row.get("offense_snaps")) else 0,
            "offense_pct": float(row["offense_pct"]) if pd.notna(row.get("offense_pct")) else 0.0,
            "defense_snaps": int(row["defense_snaps"]) if pd.notna(row.get("defense_snaps")) else 0,
            "defense_pct": float(row["defense_pct"]) if pd.notna(row.get("defense_pct")) else 0.0,
            "st_snaps": int(row["st_snaps"]) if pd.notna(row.get("st_snaps")) else 0,
            "st_pct": float(row["st_pct"]) if pd.notna(row.get("st_pct")) else 0.0,
            "updated_at": _now_iso(),
        })
    
    logger.info("Upserting %d snap count records...", len(rows))
    upserted = 0
    for chunk in _chunked(rows, batch_size):
        upserted += supabase.upsert(
            "nfl_snap_counts",
            chunk,
            on_conflict="pfr_player_id,season,week"
        )
    
    logger.info("Upserted nfl_snap_counts=%d", upserted)
    return upserted


def ingest_all(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    include_player_ids: bool = True,
    include_game_lines: bool = True,
    include_snap_counts: bool = True,
    batch_size: int = 500,
) -> NFLPyIngestSummary:
    """
    Run all nfl_data_py ingestion.
    """
    player_ids = 0
    game_lines = 0
    snap_counts = 0
    
    if include_player_ids:
        player_ids = ingest_player_id_mappings(supabase=supabase, batch_size=batch_size)
    
    if include_game_lines:
        game_lines = ingest_historic_game_lines(
            seasons=seasons, 
            supabase=supabase, 
            batch_size=batch_size
        )
    
    if include_snap_counts:
        snap_counts = ingest_snap_counts(
            seasons=seasons,
            supabase=supabase,
            batch_size=batch_size
        )
    
    return NFLPyIngestSummary(
        player_ids_upserted=player_ids,
        game_lines_upserted=game_lines,
        snap_counts_upserted=snap_counts,
    )
