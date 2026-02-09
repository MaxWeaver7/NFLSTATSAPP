from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from src.metrics.definitions import safe_div, weighted_efficiency_score


logger = logging.getLogger(__name__)


def _read_df(conn: sqlite3.Connection, sql: str):
    import pandas as pd  # type: ignore

    return pd.read_sql_query(sql, conn)


def compute_game_level_metrics(conn: sqlite3.Connection) -> None:
    """
    Compute player-game usage & efficiency metrics from:
    - `plays` (nflfastR pbp)
    - `receiving_advanced` (routes if available)
    - `player_game_stats` (snap_pct if available)
    """
    plays = _read_df(
        conn,
        """
        SELECT
            game_id, season, week, posteam,
            receiver_id, complete_pass,
            yards_gained, yards_after_catch,
            air_yards, epa, cpoe
        FROM plays
        WHERE receiver_id IS NOT NULL AND TRIM(receiver_id) != ''
        """,
    )
    if plays.empty:
        logger.info("No receiver plays found; skipping game-level metric computation.")
        return

    import pandas as pd  # type: ignore

    # Some pbp datasets don't include an explicit `target` flag. Since we filtered
    # to rows with receiver_id, treat each row as a target by definition.
    plays["target"] = 1
    plays["complete_pass"] = plays["complete_pass"].fillna(0).astype(int)

    targets = plays.copy()
    receptions = plays[plays["complete_pass"] == 1].copy()

    targets_agg = (
        targets.groupby(["receiver_id", "game_id", "season", "week", "posteam"], as_index=False)
        .agg(
            targets=("target", "size"),
            air_yards=("air_yards", "sum"),
            epa_sum=("epa", "sum"),
            cpoe_avg=("cpoe", "mean"),
        )
        .rename(columns={"posteam": "team_abbr"})
    )

    rec_agg = (
        receptions.groupby(["receiver_id", "game_id"], as_index=False)
        .agg(
            receptions=("complete_pass", "size"),
            rec_yards=("yards_gained", "sum"),
            yac=("yards_after_catch", "sum"),
        )
    )

    # Normalize columns for joining
    base = (
        plays[["receiver_id", "game_id", "season", "week", "posteam"]]
        .drop_duplicates(subset=["receiver_id", "game_id"])
        .rename(columns={"receiver_id": "player_id", "posteam": "team_abbr"})
    )

    # Routes + snap% (best effort)
    routes = _read_df(conn, "SELECT player_id, game_id, routes AS routes_run FROM receiving_advanced")
    snaps = _read_df(conn, "SELECT player_id, game_id, snap_pct FROM player_game_stats")

    # Player-game targets from pbp
    pbp_targets = (
        targets.groupby(["receiver_id", "game_id"], as_index=False)
        .agg(targets=("target", "size"))
        .rename(columns={"receiver_id": "player_id"})
    )

    usage = (
        base.merge(pbp_targets, on=["player_id", "game_id"], how="left")
        .merge(routes, on=["player_id", "game_id"], how="left")
        .merge(snaps, on=["player_id", "game_id"], how="left")
    )
    usage["targets"] = usage["targets"].fillna(0).astype(int)
    usage["targets_per_route"] = usage.apply(
        lambda r: safe_div(float(r["targets"]), float(r["routes_run"])) if pd.notna(r["routes_run"]) else None,
        axis=1,
    )

    # Efficiency (pbp-derived)
    eff = (
        base.merge(targets_agg.rename(columns={"receiver_id": "player_id"}), on=["player_id", "game_id", "season", "week", "team_abbr"], how="left")
        .merge(rec_agg.rename(columns={"receiver_id": "player_id"}), on=["player_id", "game_id"], how="left")
        .merge(routes, on=["player_id", "game_id"], how="left")
    )
    eff["epa_per_target"] = eff.apply(
        lambda r: safe_div(r.get("epa_sum"), r.get("targets")), axis=1
    )
    eff["yac_per_reception"] = eff.apply(
        lambda r: safe_div(r.get("yac"), r.get("receptions")), axis=1
    )
    eff["air_yards_per_target"] = eff.apply(
        lambda r: safe_div(r.get("air_yards"), r.get("targets")), axis=1
    )
    eff["yprr"] = eff.apply(
        lambda r: safe_div(r.get("rec_yards"), r.get("routes_run")), axis=1
    )

    cur = conn.cursor()

    cur.executemany(
        """
        INSERT OR REPLACE INTO player_usage_metrics(
            player_id, game_id, season, week, team_abbr, routes_run, targets, targets_per_route, snap_pct
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["player_id"],
                r["game_id"],
                int(r["season"]),
                int(r["week"]),
                r["team_abbr"],
                int(r["routes_run"]) if pd.notna(r["routes_run"]) else None,
                int(r["targets"]),
                float(r["targets_per_route"]) if pd.notna(r["targets_per_route"]) else None,
                float(r["snap_pct"]) if pd.notna(r["snap_pct"]) else None,
            )
            for _, r in usage.iterrows()
        ],
    )

    cur.executemany(
        """
        INSERT OR REPLACE INTO player_efficiency_metrics(
            player_id, game_id, season, week, team_abbr,
            yprr, epa_per_target, yac_per_reception, cpoe_avg, air_yards_per_target
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["player_id"],
                r["game_id"],
                int(r["season"]),
                int(r["week"]),
                r["team_abbr"],
                float(r["yprr"]) if pd.notna(r["yprr"]) else None,
                float(r["epa_per_target"]) if pd.notna(r["epa_per_target"]) else None,
                float(r["yac_per_reception"]) if pd.notna(r["yac_per_reception"]) else None,
                float(r["cpoe_avg"]) if pd.notna(r["cpoe_avg"]) else None,
                float(r["air_yards_per_target"]) if pd.notna(r["air_yards_per_target"]) else None,
            )
            for _, r in eff.iterrows()
        ],
    )

    conn.commit()
    logger.info("Computed player_game usage & efficiency metrics (%d players)", len(base))


def compute_season_aggregates(conn: sqlite3.Connection) -> None:
    import pandas as pd  # type: ignore

    usage = _read_df(
        conn,
        """
        SELECT player_id, game_id, season, team_abbr, routes_run, targets
        FROM player_usage_metrics
        """,
    )
    eff = _read_df(
        conn,
        """
        SELECT player_id, game_id, season, team_abbr, yprr, epa_per_target
        FROM player_efficiency_metrics
        """,
    )
    rec = _read_df(
        conn,
        """
        SELECT
            receiver_id AS player_id,
            game_id,
            season,
            posteam AS team_abbr,
            SUM(CASE WHEN complete_pass = 1 THEN 1 ELSE 0 END) AS receptions,
            SUM(CASE WHEN complete_pass = 1 THEN yards_gained ELSE 0 END) AS rec_yards
        FROM plays
        WHERE receiver_id IS NOT NULL AND TRIM(receiver_id) != ''
        GROUP BY receiver_id, game_id, season, posteam
        """,
    )
    air = _read_df(
        conn,
        """
        SELECT
            receiver_id AS player_id,
            game_id,
            season,
            posteam AS team_abbr,
            SUM(COALESCE(air_yards, 0)) AS air_yards
        FROM plays
        WHERE receiver_id IS NOT NULL AND TRIM(receiver_id) != ''
        GROUP BY receiver_id, game_id, season, posteam
        """,
    )
    players = _read_df(conn, "SELECT player_id, position FROM players")

    if usage.empty:
        logger.info("No usage metrics available; skipping season aggregates.")
        return

    game_level = (
        usage.merge(rec, on=["player_id", "game_id", "season", "team_abbr"], how="left")
        .merge(air, on=["player_id", "game_id", "season", "team_abbr"], how="left")
        .merge(eff, on=["player_id", "game_id", "season", "team_abbr"], how="left")
        .merge(players, on=["player_id"], how="left")
    )
    # pandas groupby drops NaN keys by default; keep unknown positions so we still
    # compute aggregates even when position isn't available from sources.
    game_level["position"] = game_level["position"].fillna("UNK")
    game_level = game_level[game_level["team_abbr"].notna() & (game_level["team_abbr"].astype(str).str.strip() != "")]

    # Team denominators
    team_pass = _read_df(
        conn,
        """
        SELECT season, posteam AS team_abbr, COUNT(*) AS team_pass_attempts
        FROM plays
        WHERE pass = 1 AND posteam IS NOT NULL AND TRIM(posteam) != ''
        GROUP BY season, posteam
        """,
    )
    team_air = _read_df(
        conn,
        """
        SELECT season, posteam AS team_abbr, SUM(COALESCE(air_yards, 0)) AS team_air_yards
        FROM plays
        WHERE receiver_id IS NOT NULL AND TRIM(receiver_id) != ''
          AND posteam IS NOT NULL AND TRIM(posteam) != ''
        GROUP BY season, posteam
        """,
    )

    season = (
        game_level.groupby(["player_id", "season", "team_abbr", "position"], as_index=False)
        .agg(
            total_routes=("routes_run", "sum"),
            targets=("targets", "sum"),
            receptions=("receptions", "sum"),
            rec_yards=("rec_yards", "sum"),
            air_yards=("air_yards", "sum"),
            yprr=("yprr", "mean"),
            epa_per_target=("epa_per_target", "mean"),
        )
        .merge(team_pass, on=["season", "team_abbr"], how="left")
        .merge(team_air, on=["season", "team_abbr"], how="left")
    )

    season["target_share"] = season.apply(
        lambda r: safe_div(r.get("targets"), r.get("team_pass_attempts")), axis=1
    )
    season["air_yards_share"] = season.apply(
        lambda r: safe_div(r.get("air_yards"), r.get("team_air_yards")), axis=1
    )
    season["weighted_efficiency_score"] = season.apply(
        lambda r: weighted_efficiency_score(
            yprr=r.get("yprr"),
            epa_per_target=r.get("epa_per_target"),
            target_share=r.get("target_share"),
        ),
        axis=1,
    )

    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR REPLACE INTO season_aggregates(
            player_id, season, team_abbr, position,
            total_routes, targets, receptions, rec_yards, air_yards,
            target_share, air_yards_share, weighted_efficiency_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["player_id"],
                int(r["season"]),
                r["team_abbr"],
                r["position"],
                int(r["total_routes"]) if pd.notna(r["total_routes"]) else None,
                int(r["targets"]) if pd.notna(r["targets"]) else 0,
                int(r["receptions"]) if pd.notna(r["receptions"]) else 0,
                float(r["rec_yards"]) if pd.notna(r["rec_yards"]) else 0.0,
                float(r["air_yards"]) if pd.notna(r["air_yards"]) else 0.0,
                float(r["target_share"]) if pd.notna(r["target_share"]) else None,
                float(r["air_yards_share"]) if pd.notna(r["air_yards_share"]) else None,
                float(r["weighted_efficiency_score"]) if pd.notna(r["weighted_efficiency_score"]) else None,
            )
            for _, r in season.iterrows()
        ],
    )
    conn.commit()
    logger.info("Computed season aggregates (%d rows)", len(season))


def compute_all_metrics(conn: sqlite3.Connection) -> None:
    compute_game_level_metrics(conn)
    compute_season_aggregates(conn)


