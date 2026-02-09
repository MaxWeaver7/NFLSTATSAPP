from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from typing import Iterable, Optional


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestSummary:
    seasons: list[int]
    games_inserted: int
    players_inserted: int
    plays_inserted: int


def _first_existing_col(df, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_int(x):
    try:
        if x is None:
            return None
        if x != x:  # NaN
            return None
        return int(x)
    except Exception:
        return None


def _safe_float(x):
    try:
        if x is None:
            return None
        if x != x:  # NaN
            return None
        return float(x)
    except Exception:
        return None


def ingest_pbp(
    seasons: list[int],
    conn: sqlite3.Connection,
    *,
    chunk_size: int = 50_000,
) -> IngestSummary:
    """
    Ingest nflfastR play-by-play via nfl_data_py into SQLite.

    This function is deterministic: it inserts raw plays and basic dimensions,
    but does not compute derived metrics.
    """
    # On some macOS Python installs, urllib SSL verification can fail because the
    # system CA bundle isn't wired up. pandas may use urllib under the hood when
    # reading remote parquet URLs. Prefer certifi's CA bundle when available.
    if not os.getenv("SSL_CERT_FILE"):
        try:
            import certifi  # type: ignore

            os.environ["SSL_CERT_FILE"] = certifi.where()
            os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        except Exception:
            pass

    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("pandas is required for ingestion") from e

    try:
        import nfl_data_py as nfl  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("nfl_data_py is required for ingestion") from e

    logger.info("Importing play-by-play for seasons=%s", seasons)
    dfs = []
    ingested_seasons: list[int] = []
    for season in seasons:
        try:
            season_df = nfl.import_pbp_data([season])
            dfs.append(season_df)
            ingested_seasons.append(season)
        except Exception as e:
            # nfl_data_py currently has brittle error handling in some failure cases
            # (e.g., upstream 404 for an unpublished season parquet). We treat this
            # as best-effort and continue with other seasons.
            logger.warning("Failed to import pbp for season=%s; skipping. err=%s", season, e)

    if not dfs:
        raise RuntimeError(f"No seasons could be imported. requested={seasons}")

    df = pd.concat(dfs, ignore_index=True)

    required = {"game_id", "play_id", "season", "week", "posteam", "defteam"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required pbp columns: {missing}")

    receiver_id_col = _first_existing_col(df, ["receiver_player_id", "receiver_id"])
    rusher_id_col = _first_existing_col(df, ["rusher_player_id", "rusher_id"])
    passer_id_col = _first_existing_col(df, ["passer_player_id", "passer_id"])

    receiver_name_col = _first_existing_col(df, ["receiver_player_name", "receiver"])
    rusher_name_col = _first_existing_col(df, ["rusher_player_name", "rusher"])
    passer_name_col = _first_existing_col(df, ["passer_player_name", "passer"])

    # Teams
    teams = set()
    for col in ["posteam", "defteam", "home_team", "away_team"]:
        if col in df.columns:
            teams |= set(df[col].dropna().unique().tolist())
    teams = {t for t in teams if isinstance(t, str) and t.strip()}
    cur = conn.cursor()
    cur.executemany(
        "INSERT OR IGNORE INTO teams(team_abbr) VALUES (?)",
        [(t,) for t in sorted(teams)],
    )

    # Games
    home_col = _first_existing_col(df, ["home_team"])
    away_col = _first_existing_col(df, ["away_team"])
    gameday_col = _first_existing_col(df, ["game_date", "gameday"])

    games_inserted = 0
    if home_col and away_col:
        games_df = (
            df[["game_id", "season", "week", home_col, away_col] + ([gameday_col] if gameday_col else [])]
            .drop_duplicates(subset=["game_id"])
            .copy()
        )
        rows = []
        for _, r in games_df.iterrows():
            rows.append(
                (
                    str(r["game_id"]),
                    _safe_int(r["season"]),
                    _safe_int(r["week"]),
                    str(r[gameday_col]) if gameday_col and r.get(gameday_col) == r.get(gameday_col) else None,
                    r.get(home_col),
                    r.get(away_col),
                )
            )
        cur.executemany(
            """
            INSERT OR IGNORE INTO games(game_id, season, week, gameday, home_team, away_team)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        games_inserted = cur.rowcount if cur.rowcount != -1 else 0
    else:
        logger.warning("home_team/away_team missing from pbp; games table will not be populated.")

    # Players (best effort: receiver/rusher/passer IDs + names)
    player_rows = {}

    def add_players(id_col: Optional[str], name_col: Optional[str]):
        if not id_col:
            return
        subset = df[[id_col] + ([name_col] if name_col else [])].dropna(subset=[id_col]).drop_duplicates(subset=[id_col])
        for _, r in subset.iterrows():
            pid = r[id_col]
            if not isinstance(pid, str) or not pid.strip():
                continue
            name = None
            if name_col:
                val = r.get(name_col)
                if isinstance(val, str) and val.strip():
                    name = val.strip()
            player_rows[pid] = name or player_rows.get(pid)

    add_players(receiver_id_col, receiver_name_col)
    add_players(rusher_id_col, rusher_name_col)
    add_players(passer_id_col, passer_name_col)

    cur.executemany(
        "INSERT OR IGNORE INTO players(player_id, player_name) VALUES (?, ?)",
        [(pid, pname) for pid, pname in player_rows.items()],
    )
    players_inserted = cur.rowcount if cur.rowcount != -1 else 0

    # Plays (raw pbp subset)
    play_cols = {
        "game_id": "game_id",
        "play_id": "play_id",
        "season": "season",
        "week": "week",
        "posteam": "posteam",
        "defteam": "defteam",
        "play_type": "play_type",
        "desc": "desc",
        "qtr": "qtr",
        "down": "down",
        "ydstogo": "ydstogo",
        "yardline_100": "yardline_100",
        "yards_gained": "yards_gained",
        "pass": "pass",
        "rush": "rush",
        "complete_pass": "complete_pass",
        "incomplete_pass": "incomplete_pass",
        "interception": "interception",
        "target": "target",
        "air_yards": "air_yards",
        "yards_after_catch": "yards_after_catch",
        "epa": "epa",
        "cp": "cp",
        "cpoe": "cpoe",
        "xyac_epa": "xyac_epa",
        "xyac_mean_yardage": "xyac_mean_yardage",
    }
    if receiver_id_col:
        play_cols["receiver_id"] = receiver_id_col
    if rusher_id_col:
        play_cols["rusher_id"] = rusher_id_col
    if passer_id_col:
        play_cols["passer_id"] = passer_id_col

    existing = [src for src in play_cols.values() if src in df.columns]
    plays_df = df[existing].copy()

    def iter_rows(rows_df) -> Iterable[tuple]:
        for _, r in rows_df.iterrows():
            yield (
                str(r.get("game_id")),
                _safe_int(r.get("play_id")),
                _safe_int(r.get("season")),
                _safe_int(r.get("week")),
                r.get("posteam"),
                r.get("defteam"),
                r.get("play_type"),
                r.get("desc"),
                _safe_int(r.get("qtr")),
                _safe_int(r.get("down")),
                _safe_int(r.get("ydstogo")),
                _safe_float(r.get("yardline_100")),
                _safe_float(r.get("yards_gained")),
                _safe_int(r.get("pass")),
                _safe_int(r.get("rush")),
                _safe_int(r.get("complete_pass")),
                _safe_int(r.get("incomplete_pass")),
                _safe_int(r.get("interception")),
                _safe_int(r.get("target")),
                r.get(receiver_id_col) if receiver_id_col else None,
                r.get(rusher_id_col) if rusher_id_col else None,
                r.get(passer_id_col) if passer_id_col else None,
                _safe_float(r.get("air_yards")),
                _safe_float(r.get("yards_after_catch")),
                _safe_float(r.get("epa")),
                _safe_float(r.get("cp")),
                _safe_float(r.get("cpoe")),
                _safe_float(r.get("xyac_epa")),
                _safe_float(r.get("xyac_mean_yardage")),
            )

    insert_sql = """
        INSERT OR REPLACE INTO plays(
            game_id, play_id, season, week, posteam, defteam, play_type, desc,
            qtr, down, ydstogo, yardline_100, yards_gained,
            pass, rush, complete_pass, incomplete_pass, interception,
            target, receiver_id, rusher_id, passer_id,
            air_yards, yards_after_catch, epa, cp, cpoe, xyac_epa, xyac_mean_yardage
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    plays_inserted = 0
    if len(plays_df) == 0:
        logger.warning("No plays returned from nfl_data_py for seasons=%s", seasons)
    else:
        logger.info("Inserting %d plays...", len(plays_df))
        rows_iter = iter_rows(plays_df)
        while True:
            chunk = []
            try:
                for _ in range(chunk_size):
                    chunk.append(next(rows_iter))
            except StopIteration:
                pass

            if not chunk:
                break

            cur.executemany(insert_sql, chunk)
            plays_inserted += len(chunk)

    conn.commit()
    logger.info(
        "Ingestion done: games_inserted=%s players_inserted=%s plays_inserted=%s",
        games_inserted,
        players_inserted,
        plays_inserted,
    )
    return IngestSummary(seasons=ingested_seasons, games_inserted=games_inserted, players_inserted=players_inserted, plays_inserted=plays_inserted)


