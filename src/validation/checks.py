from __future__ import annotations

import sqlite3
from typing import Iterable


def check_no_duplicate_plays(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT game_id, play_id, COUNT(*) AS c
        FROM plays
        GROUP BY game_id, play_id
        HAVING c > 1
        """
    ).fetchall()
    return [f"Duplicate play: game_id={r['game_id']} play_id={r['play_id']} count={r['c']}" for r in rows]


def check_derived_player_ids_exist(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(
        f"""
        SELECT d.player_id, COUNT(*) AS c
        FROM {table} d
        LEFT JOIN players p ON p.player_id = d.player_id
        WHERE p.player_id IS NULL
        GROUP BY d.player_id
        """
    ).fetchall()
    return [f"Missing player_id referenced in {table}: player_id={r['player_id']} rows={r['c']}" for r in rows]


def check_targets_pfr_vs_pbp(conn: sqlite3.Connection, *, tolerance: int = 2) -> list[str]:
    rows = conn.execute(
        """
        WITH pbp AS (
            SELECT receiver_id AS player_id, game_id, COUNT(*) AS pbp_targets
            FROM plays
            WHERE target = 1 AND receiver_id IS NOT NULL AND TRIM(receiver_id) != ''
            GROUP BY receiver_id, game_id
        )
        SELECT
            r.player_id,
            r.game_id,
            r.targets AS pfr_targets,
            COALESCE(p.pbp_targets, 0) AS pbp_targets
        FROM receiving_advanced r
        LEFT JOIN pbp p ON p.player_id = r.player_id AND p.game_id = r.game_id
        WHERE r.targets IS NOT NULL
        """
    ).fetchall()

    errs: list[str] = []
    for r in rows:
        diff = abs(int(r["pfr_targets"]) - int(r["pbp_targets"]))
        if diff > tolerance:
            errs.append(
                f"PFR vs PBP targets mismatch: player_id={r['player_id']} game_id={r['game_id']} "
                f"pfr={r['pfr_targets']} pbp={r['pbp_targets']} diff={diff} tol={tolerance}"
            )
    return errs


def check_routes_ge_targets(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT u.player_id, u.game_id, u.routes_run, u.targets
        FROM player_usage_metrics u
        JOIN players p ON p.player_id = u.player_id
        WHERE p.position IN ('WR', 'TE')
          AND u.routes_run IS NOT NULL
          AND u.targets IS NOT NULL
          AND u.routes_run < u.targets
        """
    ).fetchall()
    return [
        f"Routes < targets for WR/TE: player_id={r['player_id']} game_id={r['game_id']} routes={r['routes_run']} targets={r['targets']}"
        for r in rows
    ]


def check_yprr_bounds(conn: sqlite3.Connection, *, lo: float = 0.0, hi: float = 30.0) -> list[str]:
    rows = conn.execute(
        """
        SELECT player_id, game_id, yprr
        FROM player_efficiency_metrics
        WHERE yprr IS NOT NULL AND (yprr < ? OR yprr > ?)
        """,
        (lo, hi),
    ).fetchall()
    return [f"YPRR out of bounds: player_id={r['player_id']} game_id={r['game_id']} yprr={r['yprr']}" for r in rows]


def check_season_totals_sum_correctly(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        WITH usage AS (
            SELECT player_id, season, team_abbr, SUM(COALESCE(targets, 0)) AS targets
            FROM player_usage_metrics
            GROUP BY player_id, season, team_abbr
        )
        SELECT
            s.player_id,
            s.season,
            s.team_abbr,
            s.targets AS season_targets,
            COALESCE(u.targets, 0) AS summed_targets
        FROM season_aggregates s
        LEFT JOIN usage u
          ON u.player_id = s.player_id AND u.season = s.season AND u.team_abbr = s.team_abbr
        WHERE s.targets IS NOT NULL AND s.targets != COALESCE(u.targets, 0)
        """
    ).fetchall()
    return [
        f"Season totals mismatch: player_id={r['player_id']} season={r['season']} team={r['team_abbr']} season_targets={r['season_targets']} summed_targets={r['summed_targets']}"
        for r in rows
    ]


def run_all_checks(conn: sqlite3.Connection) -> list[str]:
    errors: list[str] = []

    errors.extend(check_no_duplicate_plays(conn))

    for table in [
        "player_usage_metrics",
        "player_efficiency_metrics",
        "season_aggregates",
        "player_game_stats",
        "receiving_advanced",
        "rushing_advanced",
    ]:
        errors.extend(check_derived_player_ids_exist(conn, table))

    errors.extend(check_targets_pfr_vs_pbp(conn, tolerance=2))
    errors.extend(check_routes_ge_targets(conn))
    errors.extend(check_yprr_bounds(conn))
    errors.extend(check_season_totals_sum_correctly(conn))
    return errors


