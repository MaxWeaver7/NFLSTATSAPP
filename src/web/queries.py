from __future__ import annotations

import sqlite3
from typing import Any, Optional

from functools import lru_cache
from pathlib import Path

import pandas as pd  # type: ignore
import requests


_PLAYER_IDS_URL = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/db_playerids.csv"


@lru_cache(maxsize=1)
def _player_ids_df() -> "pd.DataFrame":
    """
    Load a GSIS->(ESPN/NFL/Sleeper/...) id mapping.

    Why: our DB uses GSIS ids like `00-0036900`, but most headshot CDNs require
    ESPN id (numeric) or Sleeper id. We fetch the canonical dynastyprocess map
    (same dataset used widely in the NFL analytics ecosystem) and cache it to disk.
    """
    repo_root = Path(__file__).resolve().parents[2]  # hrb/
    cache_path = repo_root / "data" / "db_playerids.csv"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if not cache_path.exists():
        resp = requests.get(_PLAYER_IDS_URL, timeout=30)
        resp.raise_for_status()
        cache_path.write_bytes(resp.content)

    # Ensure ids stay strings (espn_id often numeric, but keep as string)
    return pd.read_csv(cache_path, dtype=str)


def player_photo_url(player_id: str) -> Optional[str]:
    """
    Best-effort player headshot URL for a GSIS player_id.
    Prefers ESPN (high quality) then Sleeper.
    """
    try:
        df = _player_ids_df()
    except Exception:
        return None

    if "gsis_id" not in df.columns:
        return None

    row = df[df["gsis_id"] == player_id]
    if row.empty:
        return None

    rec = row.iloc[0].to_dict()
    espn_id = (rec.get("espn_id") or "").strip()
    sleeper_id = (rec.get("sleeper_id") or "").strip()

    if espn_id and espn_id.lower() != "nan":
        return f"https://a.espncdn.com/i/headshots/nfl/players/full/{espn_id}.png"
    if sleeper_id and sleeper_id.lower() != "nan":
        return f"https://sleepercdn.com/content/nfl/players/{sleeper_id}.jpg"
    return None

def dict_rows(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    cols = [c[0] for c in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def options(conn: sqlite3.Connection) -> dict[str, Any]:
    cur = conn.cursor()
    seasons = [r[0] for r in cur.execute("SELECT DISTINCT season FROM games ORDER BY season DESC").fetchall()]
    weeks = [r[0] for r in cur.execute("SELECT DISTINCT week FROM games ORDER BY week").fetchall()]
    teams = [r[0] for r in cur.execute("SELECT team_abbr FROM teams WHERE team_abbr IS NOT NULL ORDER BY team_abbr").fetchall()]
    positions = ['QB', 'RB', 'WR', 'TE']
    return {"seasons": seasons, "weeks": weeks, "teams": teams, "positions": positions}


def summary(conn: sqlite3.Connection) -> dict[str, Any]:
    cur = conn.cursor()
    seasons = [r[0] for r in cur.execute("SELECT DISTINCT season FROM plays ORDER BY season").fetchall()]
    games = cur.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    plays = cur.execute("SELECT COUNT(*) FROM plays").fetchone()[0]
    players = cur.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    pum = cur.execute("SELECT COUNT(*) FROM player_usage_metrics").fetchone()[0]
    sa = cur.execute("SELECT COUNT(*) FROM season_aggregates").fetchone()[0]
    routes_nonnull = cur.execute("SELECT COUNT(*) FROM player_usage_metrics WHERE routes_run IS NOT NULL").fetchone()[0]
    return {
        "seasons": seasons,
        "games": games,
        "plays": plays,
        "players": players,
        "player_usage_metrics": pum,
        "season_aggregates": sa,
        "routes_coverage_pct": (100.0 * routes_nonnull / pum) if pum else 0.0,
    }


def _filters(where: list[str], params: list[Any], *, season: Optional[int], week: Optional[int], team: Optional[str]) -> None:
    if season is not None:
        where.append("p.season = ?")
        params.append(season)
    if week is not None:
        where.append("p.week = ?")
        params.append(week)
    if team:
        where.append("p.posteam = ?")
        params.append(team)


def player_game_receiving(
    conn: sqlite3.Connection,
    *,
    season: Optional[int],
    week: Optional[int],
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    where = ["p.receiver_id IS NOT NULL", "TRIM(p.receiver_id) != ''"]
    params: list[Any] = []
    _filters(where, params, season=season, week=week, team=team)

    sql = f"""
      SELECT
        p.season,
        p.week,
        p.posteam AS team,
        p.receiver_id AS player_id,
        COALESCE(pl.player_name, p.receiver_id) AS player_name,
        COALESCE(pl.position, 'UNK') AS position,
        COUNT(*) AS targets,
        SUM(CASE WHEN p.complete_pass = 1 THEN 1 ELSE 0 END) AS receptions,
        ROUND(SUM(CASE WHEN p.complete_pass = 1 THEN COALESCE(p.yards_gained, 0) ELSE 0 END), 0) AS rec_yards,
        ROUND(SUM(CASE WHEN p.complete_pass = 1 THEN COALESCE(p.yards_after_catch, 0) ELSE 0 END), 0) AS yac,
        ROUND(SUM(COALESCE(p.air_yards, 0)), 0) AS air_yards,
        ROUND(SUM(COALESCE(p.epa, 0)) * 1.0 / COUNT(*), 3) AS epa_per_target
      FROM plays p
      LEFT JOIN players pl ON pl.player_id = p.receiver_id
      WHERE {" AND ".join(where)}
      GROUP BY p.season, p.week, p.posteam, p.receiver_id
      ORDER BY targets DESC
      LIMIT ?
    """
    params.append(limit)
    cur = conn.cursor()
    cur.execute(sql, params)
    return dict_rows(cur)


def player_game_rushing(
    conn: sqlite3.Connection,
    *,
    season: Optional[int],
    week: Optional[int],
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    where = ["p.rusher_id IS NOT NULL", "TRIM(p.rusher_id) != ''", "p.rush = 1"]
    params: list[Any] = []
    if season is not None:
        where.append("p.season = ?")
        params.append(season)
    if week is not None:
        where.append("p.week = ?")
        params.append(week)
    if team:
        where.append("p.posteam = ?")
        params.append(team)

    sql = f"""
      SELECT
        p.season,
        p.week,
        p.posteam AS team,
        p.rusher_id AS player_id,
        COALESCE(pl.player_name, p.rusher_id) AS player_name,
        COALESCE(pl.position, 'UNK') AS position,
        COUNT(*) AS rush_attempts,
        ROUND(SUM(COALESCE(p.yards_gained, 0)), 0) AS rush_yards,
        ROUND(SUM(COALESCE(p.epa, 0)) * 1.0 / COUNT(*), 3) AS epa_per_rush
      FROM plays p
      LEFT JOIN players pl ON pl.player_id = p.rusher_id
      WHERE {" AND ".join(where)}
      GROUP BY p.season, p.week, p.posteam, p.rusher_id
      ORDER BY rush_yards DESC
      LIMIT ?
    """
    params.append(limit)
    cur = conn.cursor()
    cur.execute(sql, params)
    return dict_rows(cur)


def season_receiving(
    conn: sqlite3.Connection,
    *,
    season: Optional[int],
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    where = ["p.receiver_id IS NOT NULL", "TRIM(p.receiver_id) != ''"]
    params: list[Any] = []
    if season is not None:
        where.append("p.season = ?")
        params.append(season)
    if team:
        where.append("p.posteam = ?")
        params.append(team)

    sql = f"""
      WITH agg AS (
        SELECT
          p.season,
          p.posteam AS team,
          p.receiver_id AS player_id,
          COUNT(*) AS targets,
          SUM(CASE WHEN p.complete_pass = 1 THEN 1 ELSE 0 END) AS receptions,
          ROUND(SUM(CASE WHEN p.complete_pass = 1 THEN COALESCE(p.yards_gained, 0) ELSE 0 END), 0) AS rec_yards,
          ROUND(SUM(COALESCE(p.air_yards, 0)), 0) AS air_yards
        FROM plays p
        WHERE {" AND ".join(where)}
        GROUP BY p.season, p.posteam, p.receiver_id
      ),
      team_den AS (
        SELECT season, team, SUM(targets) AS team_targets
        FROM agg
        GROUP BY season, team
      )
      SELECT
        a.season,
        a.team,
        a.player_id,
        COALESCE(pl.player_name, a.player_id) AS player_name,
        COALESCE(pl.position, 'UNK') AS position,
        a.targets,
        a.receptions,
        a.rec_yards,
        a.air_yards,
        ROUND(a.targets * 1.0 / NULLIF(d.team_targets, 0), 4) AS team_target_share
      FROM agg a
      JOIN team_den d ON d.season = a.season AND d.team = a.team
      LEFT JOIN players pl ON pl.player_id = a.player_id
      ORDER BY a.targets DESC
      LIMIT ?
    """
    params.append(limit)
    cur = conn.cursor()
    cur.execute(sql, params)
    return dict_rows(cur)


def season_rushing(
    conn: sqlite3.Connection,
    *,
    season: Optional[int],
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    where = ["p.rusher_id IS NOT NULL", "TRIM(p.rusher_id) != ''", "p.rush = 1"]
    params: list[Any] = []
    if season is not None:
        where.append("p.season = ?")
        params.append(season)
    if team:
        where.append("p.posteam = ?")
        params.append(team)

    sql = f"""
      WITH agg AS (
        SELECT
          p.season,
          p.posteam AS team,
          p.rusher_id AS player_id,
          COUNT(*) AS rush_attempts,
          ROUND(SUM(COALESCE(p.yards_gained, 0)), 0) AS rush_yards
        FROM plays p
        WHERE {" AND ".join(where)}
        GROUP BY p.season, p.posteam, p.rusher_id
      ),
      team_den AS (
        SELECT season, team, SUM(rush_attempts) AS team_rush_attempts
        FROM agg
        GROUP BY season, team
      )
      SELECT
        a.season,
        a.team,
        a.player_id,
        COALESCE(pl.player_name, a.player_id) AS player_name,
        COALESCE(pl.position, 'UNK') AS position,
        a.rush_attempts,
        a.rush_yards,
        ROUND(a.rush_attempts * 1.0 / NULLIF(d.team_rush_attempts, 0), 4) AS team_rush_share
      FROM agg a
      JOIN team_den d ON d.season = a.season AND d.team = a.team
      LEFT JOIN players pl ON pl.player_id = a.player_id
      ORDER BY a.rush_yards DESC
      LIMIT ?
    """
    params.append(limit)
    cur = conn.cursor()
    cur.execute(sql, params)
    return dict_rows(cur)


def team_game_summary(
    conn: sqlite3.Connection,
    *,
    season: Optional[int],
    week: Optional[int],
    team: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    where = ["g.game_id IS NOT NULL"]
    params: list[Any] = []
    if season is not None:
        where.append("g.season = ?")
        params.append(season)
    if week is not None:
        where.append("g.week = ?")
        params.append(week)
    if team:
        where.append("(g.home_team = ? OR g.away_team = ?)")
        params.extend([team, team])

    sql = f"""
      SELECT
        g.season,
        g.week,
        g.game_id,
        g.gameday,
        g.home_team,
        g.away_team,
        SUM(CASE WHEN p.posteam = g.home_team AND p.pass = 1 THEN 1 ELSE 0 END) AS home_pass_attempts,
        SUM(CASE WHEN p.posteam = g.away_team AND p.pass = 1 THEN 1 ELSE 0 END) AS away_pass_attempts,
        SUM(CASE WHEN p.posteam = g.home_team AND p.rush = 1 THEN 1 ELSE 0 END) AS home_rush_attempts,
        SUM(CASE WHEN p.posteam = g.away_team AND p.rush = 1 THEN 1 ELSE 0 END) AS away_rush_attempts
      FROM games g
      LEFT JOIN plays p ON p.game_id = g.game_id
      WHERE {" AND ".join(where)}
      GROUP BY g.game_id
      ORDER BY g.season DESC, g.week DESC
      LIMIT ?
    """
    params.append(limit)
    cur = conn.cursor()
    cur.execute(sql, params)
    return dict_rows(cur)


def get_players_list(
    conn: sqlite3.Connection,
    *,
    season: Optional[int],
    position: Optional[str],
    team: Optional[str],
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get list of players with season totals for filtering and display."""
    where = ["1=1"]
    params: list[Any] = []
    
    if season is not None:
        where.append("season = ?")
        params.append(season)
    if position:
        where.append("player_position = ?")
        params.append(position)
    if team:
        where.append("team = ?")
        params.append(team)

    # Derive position from play types - receivers get WR, rushers get RB
    sql = f"""
    WITH recv_stats AS (
        SELECT 
            receiver_id AS player_id,
            posteam AS team,
            season,
            COUNT(DISTINCT game_id) AS games,
            COUNT(*) AS targets,
            SUM(CASE WHEN complete_pass = 1 THEN 1 ELSE 0 END) AS receptions,
            SUM(CASE WHEN complete_pass = 1 THEN COALESCE(yards_gained, 0) ELSE 0 END) AS rec_yards,
            0 AS rec_tds
        FROM plays
        WHERE receiver_id IS NOT NULL AND TRIM(receiver_id) != ''
        GROUP BY receiver_id, posteam, season
    ),
    rush_stats AS (
        SELECT 
            rusher_id AS player_id,
            posteam AS team,
            season,
            COUNT(DISTINCT game_id) AS games,
            COUNT(*) AS attempts,
            SUM(COALESCE(yards_gained, 0)) AS yards,
            0 AS tds
        FROM plays
        WHERE rusher_id IS NOT NULL AND TRIM(rusher_id) != '' AND rush = 1
        GROUP BY rusher_id, posteam, season
    ),
    all_players AS (
        SELECT player_id, team, season FROM recv_stats
        UNION
        SELECT player_id, team, season FROM rush_stats
    ),
    player_stats AS (
        SELECT 
            ap.player_id,
            COALESCE(p.player_name, ap.player_id) AS player_name,
            CASE 
                WHEN COALESCE(recv.targets, 0) > 50 AND COALESCE(rush.attempts, 0) < 50 THEN 'WR'
                WHEN COALESCE(rush.attempts, 0) > 50 AND COALESCE(recv.targets, 0) < 50 THEN 'RB'
                WHEN COALESCE(recv.targets, 0) > 30 AND COALESCE(rush.attempts, 0) > 30 THEN 'RB'
                WHEN COALESCE(recv.targets, 0) >= 20 THEN 'WR'
                WHEN COALESCE(rush.attempts, 0) >= 20 THEN 'RB'
                ELSE 'RB'
            END AS player_position,
            ap.team,
            ap.season,
            MAX(COALESCE(recv.games, 0), COALESCE(rush.games, 0)) AS games,
            COALESCE(recv.targets, 0) AS targets,
            COALESCE(recv.receptions, 0) AS receptions,
            COALESCE(recv.rec_yards, 0) AS receivingYards,
            COALESCE(recv.rec_tds, 0) AS receivingTouchdowns,
            CASE WHEN COALESCE(recv.receptions, 0) > 0 
                THEN ROUND(CAST(COALESCE(recv.rec_yards, 0) AS REAL) / recv.receptions, 1) 
                ELSE 0 END AS avgYardsPerCatch,
            COALESCE(rush.attempts, 0) AS rushAttempts,
            COALESCE(rush.yards, 0) AS rushingYards,
            COALESCE(rush.tds, 0) AS rushingTouchdowns,
            CASE WHEN COALESCE(rush.attempts, 0) > 0 
                THEN ROUND(CAST(COALESCE(rush.yards, 0) AS REAL) / rush.attempts, 1) 
                ELSE 0 END AS avgYardsPerRush
        FROM all_players ap
        LEFT JOIN recv_stats recv ON recv.player_id = ap.player_id AND recv.season = ap.season AND recv.team = ap.team
        LEFT JOIN rush_stats rush ON rush.player_id = ap.player_id AND rush.season = ap.season AND rush.team = ap.team
        LEFT JOIN players p ON p.player_id = ap.player_id
    )
    SELECT * FROM player_stats
    WHERE {" AND ".join(where)}
    ORDER BY 
        CASE 
            WHEN player_position IN ('WR', 'TE') THEN receivingYards
            WHEN player_position = 'RB' THEN rushingYards + receivingYards
            ELSE rushingYards
        END DESC
    LIMIT ?
    """
    params.append(limit)
    cur = conn.cursor()
    cur.execute(sql, params)
    return dict_rows(cur)


def get_player_game_logs(
    conn: sqlite3.Connection,
    player_id: str,
    season: int,
    *,
    include_postseason: bool = False,
) -> list[dict[str, Any]]:
    """Get game-by-game stats for a player in a specific season."""
    season_clause = ""
    params: list[Any] = []
    if not include_postseason:
        # nflfastR play-by-play encodes postseason as weeks 19-22 for a given season.
        # Default UX should show only regular season; postseason can be toggled on.
        season_clause = " AND p.week <= 18 "

    sql = f"""
    WITH game_stats AS (
        SELECT 
            p.season,
            p.week,
            p.game_id,
            p.posteam AS team,
            g.gameday,
            g.home_team,
            g.away_team,
            CASE WHEN p.posteam = g.home_team THEN 'home' ELSE 'away' END AS location,
            CASE WHEN p.posteam = g.home_team THEN g.away_team ELSE g.home_team END AS opponent,
            CASE WHEN p.week >= 19 THEN 1 ELSE 0 END AS is_postseason,
            COUNT(CASE WHEN p.receiver_id = ? THEN 1 END) AS targets,
            SUM(CASE WHEN p.receiver_id = ? AND p.complete_pass = 1 THEN 1 ELSE 0 END) AS receptions,
            SUM(CASE WHEN p.receiver_id = ? AND p.complete_pass = 1 THEN COALESCE(p.yards_gained, 0) ELSE 0 END) AS rec_yards,
            0 AS rec_tds,
            SUM(CASE WHEN p.receiver_id = ? THEN COALESCE(p.air_yards, 0) ELSE 0 END) AS air_yards,
            SUM(CASE WHEN p.receiver_id = ? AND p.complete_pass = 1 THEN COALESCE(p.yards_after_catch, 0) ELSE 0 END) AS yac,
            ROUND(
                SUM(CASE WHEN p.receiver_id = ? THEN COALESCE(p.epa, 0) ELSE 0 END)
                / NULLIF(COUNT(CASE WHEN p.receiver_id = ? THEN 1 END), 0),
                3
            ) AS epa_per_target,
            COUNT(CASE WHEN p.rusher_id = ? AND p.rush = 1 THEN 1 END) AS rush_attempts,
            SUM(CASE WHEN p.rusher_id = ? AND p.rush = 1 THEN COALESCE(p.yards_gained, 0) ELSE 0 END) AS rush_yards,
            0 AS rush_tds,
            ROUND(
                SUM(CASE WHEN p.rusher_id = ? AND p.rush = 1 THEN COALESCE(p.epa, 0) ELSE 0 END)
                / NULLIF(COUNT(CASE WHEN p.rusher_id = ? AND p.rush = 1 THEN 1 END), 0),
                3
            ) AS epa_per_rush
        FROM plays p
        JOIN games g ON g.game_id = p.game_id
        WHERE p.season = ? {season_clause} AND (p.receiver_id = ? OR p.rusher_id = ?)
        GROUP BY p.game_id, p.week, p.posteam
        ORDER BY p.week
    )
    SELECT * FROM game_stats
    """
    cur = conn.cursor()
    # params map to each ? in order
    params.extend(
        [
            player_id,  # targets count
            player_id,  # receptions
            player_id,  # rec_yards
            player_id,  # air_yards
            player_id,  # yac
            player_id,  # epa sum
            player_id,  # epa denom count
            player_id,  # rush_attempts
            player_id,  # rush_yards
            player_id,  # epa rush sum
            player_id,  # epa rush denom count
            season,
            player_id,
            player_id,
        ]
    )
    cur.execute(sql, params)
    return dict_rows(cur)


