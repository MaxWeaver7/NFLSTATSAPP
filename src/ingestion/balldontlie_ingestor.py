from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from src.database.supabase_client import SupabaseClient
from src.ingestion.balldontlie_client import BallDontLieError, BallDontLieNFLClient


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoreIngestSummary:
    teams_upserted: int
    players_upserted: int
    games_upserted: int


@dataclass(frozen=True)
class StatsIngestSummary:
    season_stats_upserted: int
    game_stats_upserted: int
    adv_receiving_upserted: int
    adv_rushing_upserted: int
    adv_passing_upserted: int


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chunked(items: Iterable[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    buf: list[dict[str, Any]] = []
    for it in items:
        buf.append(it)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def _valid_rows(
    rows: Iterable[dict[str, Any]],
    mapper: Optional[Any] = None,
    *,
    required_fields: list[str],
    abort_threshold: int = 25,
) -> Iterable[dict[str, Any]]:
    """
    Map rows and drop any missing required fields; abort if too many invalids.
    """
    mapper = mapper or (lambda x: x)
    invalid = 0
    for raw in rows:
        mapped = mapper(raw)
        if any(mapped.get(f) is None for f in required_fields):
            invalid += 1
            if invalid > abort_threshold:
                raise ValueError(f"Too many invalid rows missing {required_fields}")
            continue
        yield mapped


def _ensure_defaults(mapped: dict[str, Any], *, season: int, week: int, postseason: bool) -> dict[str, Any]:
    if mapped.get("season") is None:
        mapped["season"] = season
    if mapped.get("week") is None:
        mapped["week"] = week
    if mapped.get("postseason") is None:
        mapped["postseason"] = postseason
    return mapped


def map_team(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": t.get("id"),
        "conference": t.get("conference"),
        "division": t.get("division"),
        "location": t.get("location"),
        "name": t.get("name"),
        "full_name": t.get("full_name"),
        "abbreviation": t.get("abbreviation"),
        "updated_at": _now_iso(),
    }


def map_player(p: dict[str, Any]) -> dict[str, Any]:
    team = p.get("team") if isinstance(p.get("team"), dict) else None
    team_id = team.get("id") if isinstance(team, dict) else None
    return {
        "id": p.get("id"),
        "first_name": p.get("first_name"),
        "last_name": p.get("last_name"),
        "position": p.get("position"),
        "position_abbreviation": p.get("position_abbreviation"),
        "height": p.get("height"),
        "weight": p.get("weight"),
        "jersey_number": p.get("jersey_number"),
        "college": p.get("college"),
        "experience": p.get("experience"),
        "age": p.get("age"),
        "team_id": team_id,
        "updated_at": _now_iso(),
    }


def map_game(g: dict[str, Any]) -> dict[str, Any]:
    home = g.get("home_team") if isinstance(g.get("home_team"), dict) else None
    visitor = g.get("visitor_team") if isinstance(g.get("visitor_team"), dict) else None
    return {
        "id": g.get("id"),
        "season": g.get("season"),
        "week": g.get("week"),
        "date": g.get("date"),
        "postseason": g.get("postseason"),
        "status": g.get("status"),
        "venue": g.get("venue"),
        "summary": g.get("summary"),
        "home_team_id": home.get("id") if isinstance(home, dict) else None,
        "visitor_team_id": visitor.get("id") if isinstance(visitor, dict) else None,
        "home_team_score": g.get("home_team_score"),
        "home_team_q1": g.get("home_team_q1"),
        "home_team_q2": g.get("home_team_q2"),
        "home_team_q3": g.get("home_team_q3"),
        "home_team_q4": g.get("home_team_q4"),
        "home_team_ot": g.get("home_team_ot"),
        "visitor_team_score": g.get("visitor_team_score"),
        "visitor_team_q1": g.get("visitor_team_q1"),
        "visitor_team_q2": g.get("visitor_team_q2"),
        "visitor_team_q3": g.get("visitor_team_q3"),
        "visitor_team_q4": g.get("visitor_team_q4"),
        "visitor_team_ot": g.get("visitor_team_ot"),
        "updated_at": _now_iso(),
    }


def map_player_season_stats(s: dict[str, Any]) -> dict[str, Any]:
    p = s.get("player") if isinstance(s.get("player"), dict) else None
    pid = p.get("id") if isinstance(p, dict) else None
    return {
        "player_id": pid,
        "season": s.get("season"),
        "postseason": s.get("postseason", False),
        "games_played": s.get("games_played"),
        "passing_completions": s.get("passing_completions"),
        "passing_attempts": s.get("passing_attempts"),
        "passing_yards": s.get("passing_yards"),
        "passing_touchdowns": s.get("passing_touchdowns"),
        "passing_interceptions": s.get("passing_interceptions"),
        "qbr": s.get("qbr"),
        "rushing_attempts": s.get("rushing_attempts"),
        "rushing_yards": s.get("rushing_yards"),
        "rushing_touchdowns": s.get("rushing_touchdowns"),
        "receptions": s.get("receptions"),
        "receiving_yards": s.get("receiving_yards"),
        "receiving_touchdowns": s.get("receiving_touchdowns"),
        "receiving_targets": s.get("receiving_targets"),
        "updated_at": _now_iso(),
    }


def map_player_game_stats(s: dict[str, Any]) -> dict[str, Any]:
    p = s.get("player") if isinstance(s.get("player"), dict) else None
    pid = p.get("id") if isinstance(p, dict) else None
    t = s.get("team") if isinstance(s.get("team"), dict) else None
    tid = t.get("id") if isinstance(t, dict) else None
    g = s.get("game") if isinstance(s.get("game"), dict) else None
    gid = g.get("id") if isinstance(g, dict) else None
    return {
        "player_id": pid,
        "game_id": gid,
        "season": g.get("season") if isinstance(g, dict) else None,
        "week": g.get("week") if isinstance(g, dict) else None,
        "team_id": tid,
        "passing_completions": s.get("passing_completions"),
        "passing_attempts": s.get("passing_attempts"),
        "passing_yards": s.get("passing_yards"),
        "passing_touchdowns": s.get("passing_touchdowns"),
        "passing_interceptions": s.get("passing_interceptions"),
        "qbr": s.get("qbr"),
        "rushing_attempts": s.get("rushing_attempts"),
        "rushing_yards": s.get("rushing_yards"),
        "rushing_touchdowns": s.get("rushing_touchdowns"),
        "receptions": s.get("receptions"),
        "receiving_yards": s.get("receiving_yards"),
        "receiving_touchdowns": s.get("receiving_touchdowns"),
        "receiving_targets": s.get("receiving_targets"),
        "updated_at": _now_iso(),
    }


def map_adv_receiving(s: dict[str, Any]) -> dict[str, Any]:
    p = s.get("player") if isinstance(s.get("player"), dict) else None
    pid = p.get("id") if isinstance(p, dict) else None
    return {
        "player_id": pid,
        "season": s.get("season"),
        "week": s.get("week"),
        "postseason": s.get("postseason", False),
        "receptions": s.get("receptions"),
        "targets": s.get("targets"),
        "yards": s.get("yards"),
        # "avg_intended_air_yards": s.get("avg_intended_air_yards"), # Removed: Not in schema
        "avg_yac": s.get("avg_yac"),
        "avg_expected_yac": s.get("avg_expected_yac"),
        "avg_yac_above_expectation": s.get("avg_yac_above_expectation"),
        "catch_percentage": s.get("catch_percentage"),
        "avg_cushion": s.get("avg_cushion"),
        "avg_separation": s.get("avg_separation"),
        "percent_share_of_intended_air_yards": s.get("percent_share_of_intended_air_yards"),
        "updated_at": _now_iso(),
    }


def map_adv_rushing(s: dict[str, Any]) -> dict[str, Any]:
    p = s.get("player") if isinstance(s.get("player"), dict) else None
    pid = p.get("id") if isinstance(p, dict) else None
    return {
        "player_id": pid,
        "season": s.get("season"),
        "week": s.get("week"),
        "postseason": s.get("postseason", False),
        "rush_attempts": s.get("rush_attempts"),
        "rush_yards": s.get("rush_yards"),
        "efficiency": s.get("efficiency"),
        "avg_rush_yards": s.get("avg_rush_yards"),
        "expected_rush_yards": s.get("expected_rush_yards"),
        "rush_yards_over_expected": s.get("rush_yards_over_expected"),
        "rush_yards_over_expected_per_att": s.get("rush_yards_over_expected_per_att"),
        "rush_touchdowns": s.get("rush_touchdowns"),
        "avg_time_to_los": s.get("avg_time_to_los"),
        "rush_pct_over_expected": s.get("rush_pct_over_expected"),
        "percent_attempts_gte_eight_defenders": s.get("percent_attempts_gte_eight_defenders"),
        "updated_at": _now_iso(),
    }


def map_adv_passing(s: dict[str, Any]) -> dict[str, Any]:
    p = s.get("player") if isinstance(s.get("player"), dict) else None
    pid = p.get("id") if isinstance(p, dict) else None
    return {
        "player_id": pid,
        "season": s.get("season"),
        "week": s.get("week"),
        "postseason": s.get("postseason", False),
        "attempts": s.get("attempts"),
        "completions": s.get("completions"),
        "pass_yards": s.get("pass_yards"),
        "pass_touchdowns": s.get("pass_touchdowns"),
        "interceptions": s.get("interceptions"),
        "passer_rating": s.get("passer_rating"),
        # "completion_percentage": s.get("completion_percentage"), # Removed
        "completion_percentage_above_expectation": s.get("completion_percentage_above_expectation"),
        "avg_time_to_throw": s.get("avg_time_to_throw"),
        "avg_intended_air_yards": s.get("avg_intended_air_yards"),
        "avg_completed_air_yards": s.get("avg_completed_air_yards"),
        "aggressiveness": s.get("aggressiveness"),
        "expected_completion_percentage": s.get("expected_completion_percentage"),
        "avg_air_distance": s.get("avg_air_distance"),
        "avg_air_yards_differential": s.get("avg_air_yards_differential"),
        "avg_air_yards_to_sticks": s.get("avg_air_yards_to_sticks"),
        # "max_air_distance": s.get("max_air_distance"), # Removed
        # "max_completed_air_distance": s.get("max_completed_air_distance"), # Removed
        # "games_played": s.get("games_played"), # Removed
        "updated_at": _now_iso(),
    }


def ingest_core(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    batch_size: int = 500,
    game_weeks: Optional[list[int]] = None,
) -> CoreIngestSummary:
    # 1) Teams
    teams_raw = bdl.list_teams()
    teams_rows = [map_team(t) for t in teams_raw]
    teams_upserted = supabase.upsert("nfl_teams", teams_rows, on_conflict="id") if teams_rows else 0
    logger.info("Upserted nfl_teams=%d", teams_upserted)

    # 2) Players (cursor pagination)
    players_upserted = 0
    for chunk in _chunked((map_player(p) for p in bdl.iter_players()), batch_size):
        players_upserted += supabase.upsert("nfl_players", chunk, on_conflict="id")
        if players_upserted % (batch_size * 10) == 0:
            logger.info("Upserted nfl_players=%d", players_upserted)
    logger.info("Upserted nfl_players=%d", players_upserted)

    # 3) Games (for seasons/weeks)
    games_upserted = 0
    for chunk in _chunked((map_game(g) for g in bdl.iter_games(seasons=seasons, weeks=game_weeks)), batch_size):
        games_upserted += supabase.upsert("nfl_games", chunk, on_conflict="id")
        if games_upserted % (batch_size * 10) == 0:
            logger.info("Upserted nfl_games=%d", games_upserted)
    logger.info("Upserted nfl_games=%d", games_upserted)

    return CoreIngestSummary(
        teams_upserted=teams_upserted,
        players_upserted=players_upserted,
        games_upserted=games_upserted,
    )


def ingest_stats_and_advanced(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    batch_size: int = 500,
    include_season_stats: bool = True,
    include_game_stats: bool = True,
    game_weeks: Optional[list[int]] = None,
    include_advanced: bool = True,
    advanced_weeks: Optional[list[int]] = None,
    advanced_include_postseason: bool = False,
    invalid_abort_threshold: int = 25,
) -> StatsIngestSummary:
    season_stats_upserted = 0
    # Season stats
    if include_season_stats:
        for season in seasons:
            for chunk in _chunked(
                (map_player_season_stats(s) for s in bdl.iter_player_season_stats(season=season)),
                batch_size,
            ):
                season_stats_upserted += supabase.upsert(
                    "nfl_player_season_stats", chunk, on_conflict="player_id,season,postseason"
                )
    logger.info("Upserted nfl_player_season_stats=%d", season_stats_upserted)

    # Per-game player stats
    game_stats_upserted = 0
    if include_game_stats:
        for chunk in _chunked(
            _valid_rows(
                (map_player_game_stats(s) for s in bdl.iter_player_game_stats(seasons=seasons)),
                required_fields=["player_id", "game_id"],
                abort_threshold=invalid_abort_threshold,
            ),
            batch_size,
        ):
            game_stats_upserted += supabase.upsert("nfl_player_game_stats", chunk, on_conflict="player_id,game_id")
            if game_stats_upserted % (batch_size * 10) == 0:
                logger.info("Upserted nfl_player_game_stats=%d", game_stats_upserted)
    logger.info("Upserted nfl_player_game_stats=%d", game_stats_upserted)

    # Advanced stats (week 0 = full season)
    adv_receiving_upserted = 0
    adv_rushing_upserted = 0
    adv_passing_upserted = 0
    if include_advanced:
        weeks = advanced_weeks if advanced_weeks is not None else [0]
        for season in seasons:
            for week in weeks:
                try:
                    for chunk in _chunked(
                        _valid_rows(
                            (
                                map_adv_receiving(s)
                                for s in bdl.iter_advanced_receiving(season=season, week=week, postseason=False)
                            ),
                            mapper=lambda m: _ensure_defaults(m, season=season, week=week, postseason=False),
                            required_fields=["player_id", "season", "week", "postseason"],
                            abort_threshold=invalid_abort_threshold,
                        ),
                        batch_size,
                    ):
                        adv_receiving_upserted += supabase.upsert(
                            "nfl_advanced_receiving_stats", chunk, on_conflict="player_id,season,week,postseason"
                        )
                except BallDontLieError as e:
                    logger.warning("Skipping advanced receiving season=%s week=%s due to BDL error: %s", season, week, e)

                try:
                    for chunk in _chunked(
                        _valid_rows(
                            (
                                map_adv_rushing(s)
                                for s in bdl.iter_advanced_rushing(season=season, week=week, postseason=False)
                            ),
                            mapper=lambda m: _ensure_defaults(m, season=season, week=week, postseason=False),
                            required_fields=["player_id", "season", "week", "postseason"],
                            abort_threshold=invalid_abort_threshold,
                        ),
                        batch_size,
                    ):
                        adv_rushing_upserted += supabase.upsert(
                            "nfl_advanced_rushing_stats", chunk, on_conflict="player_id,season,week,postseason"
                        )
                except BallDontLieError as e:
                    logger.warning("Skipping advanced rushing season=%s week=%s due to BDL error: %s", season, week, e)

                try:
                    for chunk in _chunked(
                        _valid_rows(
                            (
                                map_adv_passing(s)
                                for s in bdl.iter_advanced_passing(season=season, week=week, postseason=False)
                            ),
                            mapper=lambda m: _ensure_defaults(m, season=season, week=week, postseason=False),
                            required_fields=["player_id", "season", "week", "postseason"],
                            abort_threshold=invalid_abort_threshold,
                        ),
                        batch_size,
                    ):
                        adv_passing_upserted += supabase.upsert(
                            "nfl_advanced_passing_stats", chunk, on_conflict="player_id,season,week,postseason"
                        )
                except BallDontLieError as e:
                    logger.warning("Skipping advanced passing season=%s week=%s due to BDL error: %s", season, week, e)

            if advanced_include_postseason:
                postseason_week = 0
                try:
                    for chunk in _chunked(
                        _valid_rows(
                            (
                                map_adv_receiving(
                                    s
                                )
                                for s in bdl.iter_advanced_receiving(season=season, week=postseason_week, postseason=True)
                            ),
                            mapper=lambda m: _ensure_defaults(m, season=season, week=postseason_week, postseason=True),
                            required_fields=["player_id", "season", "week", "postseason"],
                            abort_threshold=invalid_abort_threshold,
                        ),
                        batch_size,
                    ):
                        adv_receiving_upserted += supabase.upsert(
                            "nfl_advanced_receiving_stats", chunk, on_conflict="player_id,season,week,postseason"
                        )
                except BallDontLieError as e:
                    logger.warning(
                        "Skipping advanced receiving postseason season=%s week=%s due to BDL error: %s",
                        season,
                        postseason_week,
                        e,
                    )

                try:
                    for chunk in _chunked(
                        _valid_rows(
                            (
                                map_adv_rushing(
                                    s
                                )
                                for s in bdl.iter_advanced_rushing(season=season, week=postseason_week, postseason=True)
                            ),
                            mapper=lambda m: _ensure_defaults(m, season=season, week=postseason_week, postseason=True),
                            required_fields=["player_id", "season", "week", "postseason"],
                            abort_threshold=invalid_abort_threshold,
                        ),
                        batch_size,
                    ):
                        adv_rushing_upserted += supabase.upsert(
                            "nfl_advanced_rushing_stats", chunk, on_conflict="player_id,season,week,postseason"
                        )
                except BallDontLieError as e:
                    logger.warning(
                        "Skipping advanced rushing postseason season=%s week=%s due to BDL error: %s",
                        season,
                        postseason_week,
                        e,
                    )

                try:
                    for chunk in _chunked(
                        _valid_rows(
                            (
                                map_adv_passing(
                                    s
                                )
                                for s in bdl.iter_advanced_passing(season=season, week=postseason_week, postseason=True)
                            ),
                            mapper=lambda m: _ensure_defaults(m, season=season, week=postseason_week, postseason=True),
                            required_fields=["player_id", "season", "week", "postseason"],
                            abort_threshold=invalid_abort_threshold,
                        ),
                        batch_size,
                    ):
                        adv_passing_upserted += supabase.upsert(
                            "nfl_advanced_passing_stats", chunk, on_conflict="player_id,season,week,postseason"
                        )
                except BallDontLieError as e:
                    logger.warning(
                        "Skipping advanced passing postseason season=%s week=%s due to BDL error: %s",
                        season,
                        postseason_week,
                        e,
                    )
    logger.info(
        "Upserted advanced stats: receiving=%d rushing=%d passing=%d",
        adv_receiving_upserted,
        adv_rushing_upserted,
        adv_passing_upserted,
    )

    return StatsIngestSummary(
        season_stats_upserted=season_stats_upserted,
        game_stats_upserted=game_stats_upserted,
        adv_receiving_upserted=adv_receiving_upserted,
        adv_rushing_upserted=adv_rushing_upserted,
        adv_passing_upserted=adv_passing_upserted,
    )


# =============================================================================
# NEW: Injuries, Standings, Team Stats, and Filtered Props Ingestion
# =============================================================================



def should_ingest_prop(prop: dict[str, Any]) -> bool:
    """
    Filter player props based on Master Doc requirements.
    - KEEP: market_type == 'over_under'
    - KEEP: market_type == 'milestone' AND prop_type == 'anytime_td'
    - DISCARD: All others
    """
    market = prop.get("market", {})
    market_type = market.get("type", "")
    prop_type = prop.get("prop_type", "")

    if market_type == "over_under":
        return True

    if market_type == "milestone" and prop_type == "anytime_td":
        return True

    return False


def map_injury(inj: dict[str, Any]) -> dict[str, Any]:
    """Map injury to match existing nfl_injuries table schema."""
    player = inj.get("player") if isinstance(inj.get("player"), dict) else {}
    return {
        "player_id": player.get("id"),
        "status": inj.get("status"),
        "comment": inj.get("comment"),
        "date": inj.get("date"),
        "updated_at": _now_iso(),
    }


def map_standing(s: dict[str, Any]) -> dict[str, Any]:
    team = s.get("team") if isinstance(s.get("team"), dict) else {}
    return {
        "team_id": team.get("id"),
        "season": s.get("season"),
        "wins": s.get("wins"),
        "losses": s.get("losses"),
        "ties": s.get("ties"),
        "points_for": s.get("points_for"),
        "points_against": s.get("points_against"),
        "point_differential": s.get("point_differential"),
        "playoff_seed": s.get("playoff_seed"),
        "overall_record": s.get("overall_record"),
        "conference_record": s.get("conference_record"),
        "division_record": s.get("division_record"),
        "home_record": s.get("home_record"),
        "road_record": s.get("road_record"),
        "win_streak": s.get("win_streak"),
        "updated_at": _now_iso(),
    }


def map_team_season_stat(s: dict[str, Any], season_override: int) -> dict[str, Any]:
    """Map team stats to match Exhaustive Master Schema."""
    team = s.get("team") if isinstance(s.get("team"), dict) else {}
    season_type = s.get("season_type")
    # Derived from season_type: 2=Reg, 3=Post
    postseason = season_type == 3 if season_type is not None else False

    # Use override if missing in API response
    final_season = s.get("season")
    if final_season is None:
        final_season = season_override

    return {
        # Identity
        "team_id": team.get("id"),
        "season": final_season,
        "season_type": season_type,
        "postseason": postseason,
        "games_played": s.get("games_played"),
        "stats_json": s,

        # Scoring & Totals
        "total_points": s.get("total_points"),
        "total_points_per_game": s.get("total_points_per_game"),
        "total_offensive_yards": s.get("total_offensive_yards"),
        "total_offensive_yards_per_game": s.get("total_offensive_yards_per_game"),
        "net_total_offensive_yards": s.get("net_total_offensive_yards"),
        "net_total_offensive_yards_per_game": s.get("net_total_offensive_yards_per_game"),

        # Passing
        "passing_attempts": s.get("passing_attempts"),
        "passing_completions": s.get("passing_completions"),
        "passing_completion_pct": s.get("passing_completion_pct"),
        "passing_yards": s.get("passing_yards"),
        "passing_yards_per_game": s.get("passing_yards_per_game"),
        "passing_touchdowns": s.get("passing_touchdowns"),
        "passing_interceptions": s.get("passing_interceptions"),
        "net_passing_yards": s.get("net_passing_yards"),
        "net_passing_yards_per_game": s.get("net_passing_yards_per_game"),
        "yards_per_pass_attempt": s.get("yards_per_pass_attempt"),
        "net_yards_per_pass_attempt": s.get("net_yards_per_pass_attempt"),
        "passing_first_downs": s.get("misc_first_downs_passing"),
        "passing_first_down_pct": s.get("passing_first_down_pct"),
        "passing_20_plus_yards": s.get("passing_20_plus_yards"),
        "passing_40_plus_yards": s.get("passing_40_plus_yards"),
        "passing_sacks": s.get("passing_sacks"),
        "passing_sack_yards": s.get("passing_sack_yards_lost"), # Note field mismatch in json sample vs doc name? Doc says passing_sack_yards, JSON usually passing_sack_yards_lost. Using API key from sample.
        "qb_rating": s.get("passing_qb_rating"),
        "passing_long": s.get("passing_long"),

        # Rushing
        "rushing_attempts": s.get("rushing_attempts"),
        "rushing_yards": s.get("rushing_yards"),
        "rushing_yards_per_game": s.get("rushing_yards_per_game"),
        "rushing_touchdowns": s.get("rushing_touchdowns"),
        "rushing_average": s.get("rushing_yards_per_rush_attempt"), # Doc says rushing_average, JSON usually has rushing_yards_per_rush_attempt
        "rushing_first_downs": s.get("misc_first_downs_rushing"),
        "rushing_first_down_pct": s.get("rushing_first_down_pct"),
        "rushing_20_plus_yards": s.get("rushing_20_plus_yards"),
        "rushing_40_plus_yards": s.get("rushing_40_plus_yards"),
        "rushing_fumbles": s.get("rushing_fumbles"),
        "rushing_fumbles_lost": s.get("rushing_fumbles_lost"),
        "rushing_long": s.get("rushing_long"),

        # Receiving
        "receiving_receptions": s.get("receiving_receptions"),
        "receiving_yards": s.get("receiving_yards"),
        "receiving_touchdowns": s.get("receiving_touchdowns"),
        "receiving_targets": s.get("receiving_targets"),
        "receiving_average": s.get("receiving_yards_per_reception"),
        "receiving_first_downs": s.get("receiving_first_downs"),
        "receiving_yards_per_game": s.get("receiving_yards_per_game"),
        "receiving_fumbles": s.get("receiving_fumbles"),
        "receiving_fumbles_lost": s.get("receiving_fumbles_lost"),
        "receiving_long": s.get("receiving_long"),

        # Efficiency & Misc
        "misc_first_downs": s.get("misc_first_downs"),
        "misc_first_downs_passing": s.get("misc_first_downs_passing"),
        "misc_first_downs_rushing": s.get("misc_first_downs_rushing"),
        "misc_first_downs_penalty": s.get("misc_first_downs_penalty"),
        "third_down_efficiency": (
            f"{s.get('misc_third_down_convs')}-{s.get('misc_third_down_attempts')}"
            if s.get("misc_third_down_convs") is not None and s.get("misc_third_down_attempts") is not None
            else None
        ),
        "third_down_conv_pct": s.get("misc_third_down_conv_pct"),
        "misc_third_down_convs": s.get("misc_third_down_convs"),
        "misc_third_down_attempts": s.get("misc_third_down_attempts"),
        # "misc_third_down_convs": 32, "misc_third_down_attempts": 85
        
        "fourth_down_efficiency": (
            f"{s.get('misc_fourth_down_convs')}-{s.get('misc_fourth_down_attempts')}"
            if s.get("misc_fourth_down_convs") is not None and s.get("misc_fourth_down_attempts") is not None
            else None
        ),
        "misc_fourth_down_convs": s.get("misc_fourth_down_convs"),
        "misc_fourth_down_attempts": s.get("misc_fourth_down_attempts"),
        "red_zone_efficiency": s.get("misc_red_zone_efficiency"), # Not in Step 118 sample?
        "goal_to_go_efficiency": s.get("misc_goal_to_go_efficiency"), # Not in Step 118 sample?
        "misc_total_penalties": s.get("misc_total_penalties"),
        "misc_total_penalty_yards": s.get("misc_total_penalty_yards"),
        "misc_total_takeaways": s.get("misc_total_takeaways"),
        "misc_total_giveaways": s.get("misc_total_giveaways"),
        
        # Special Teams
        "kicking_field_goals_made": s.get("kicking_field_goals_made"),
        "kicking_field_goals_attempted": s.get("kicking_field_goal_attempts"),
        "kicking_pct": s.get("kicking_field_goal_pct"),
        "punting_punts": s.get("punting_punts"),
        "punting_yards": s.get("punting_punt_yards"),
        "punting_average": s.get("punting_gross_avg_punt_yards"),
        "punting_net_average": s.get("punting_net_avg_punt_yards"),
        "punts_inside_20": s.get("punting_punts_inside_20"),
        "kick_returns": s.get("returning_kick_returns"),
        "kick_return_yards": s.get("returning_kick_return_yards"),
        "kick_return_average": s.get("returning_yards_per_kick_return"),
        "kick_return_touchdowns": s.get("returning_kick_return_touchdowns"),
        "punt_returns": s.get("returning_punt_returns"),
        "punt_return_yards": s.get("returning_punt_return_yards"),
        "punt_return_average": s.get("returning_yards_per_punt_return"),
        "punt_return_touchdowns": s.get("returning_punt_return_touchdowns"),
        "returning_long_kick_return": s.get("returning_long_kick_return"),
        "returning_long_punt_return": s.get("returning_long_punt_return"),
        "returning_punt_return_fair_catches": s.get("returning_punt_return_fair_catches"),
        "kicking_long_field_goal_made": s.get("kicking_long_field_goal_made"),
        "kicking_field_goals_made_1_19": s.get("kicking_field_goals_made_1_19"),
        "kicking_field_goals_made_20_29": s.get("kicking_field_goals_made_20_29"),
        "kicking_field_goals_made_30_39": s.get("kicking_field_goals_made_30_39"),
        "kicking_field_goals_made_40_49": s.get("kicking_field_goals_made_40_49"),
        "kicking_field_goals_made_50": s.get("kicking_field_goals_made_50"),
        "kicking_field_goal_attempts_1_19": s.get("kicking_field_goal_attempts_1_19"),
        "kicking_field_goal_attempts_20_29": s.get("kicking_field_goal_attempts_20_29"),
        "kicking_field_goal_attempts_30_39": s.get("kicking_field_goal_attempts_30_39"),
        "kicking_field_goal_attempts_40_49": s.get("kicking_field_goal_attempts_40_49"),
        "kicking_field_goal_attempts_50": s.get("kicking_field_goal_attempts_50"),
        "kicking_extra_points_made": s.get("kicking_extra_points_made"),
        "kicking_extra_point_attempts": s.get("kicking_extra_point_attempts"),
        "kicking_extra_point_pct": s.get("kicking_extra_point_pct"),
        "punting_long_punt": s.get("punting_long_punt"),
        "punting_punts_blocked": s.get("punting_punts_blocked"),
        "punting_touchbacks": s.get("punting_touchbacks"),
        "punting_fair_catches": s.get("punting_fair_catches"),
        "punting_punt_returns": s.get("punting_punt_returns"),
        "punting_punt_return_yards": s.get("punting_punt_return_yards"),
        "punting_avg_punt_return_yards": s.get("punting_avg_punt_return_yards"),

        # Defense & Turnovers
        "defensive_interceptions": s.get("defensive_interceptions"),
        "fumbles_forced": s.get("defensive_fumbles_forced"), # Check if exists
        "fumbles_recovered": s.get("fumbles_recovered"), # Or opp_fumbles_lost? Main team fumbles recovered usually means defensive recovery? 
        # Wait, "fumbles_recovered": 4 in step 118 sample (for Lions). 
        # "opp_fumbles_recovered": 2.
        # "misc_total_takeaways": 11.
        
        "turnovers": s.get("misc_total_giveaways"), 
        "turnover_differential": s.get("misc_turnover_differential"),
        "fumbles_lost": s.get("fumbles_lost"),

        # Possession
        "possession_time": s.get("possession_time"), # Often in Game stats, not always Season stats. 
        # Step 118 sample DOES NOT show possession time in season stats.
        "possession_time_seconds": s.get("possession_time_seconds"), 

        # Opponent block
        "opp_games_played": s.get("opp_games_played"),
        "opp_fumbles_recovered": s.get("opp_fumbles_recovered"),
        "opp_fumbles_lost": s.get("opp_fumbles_lost"),
        "opp_total_offensive_yards": s.get("opp_total_offensive_yards"),
        "opp_total_offensive_yards_per_game": s.get("opp_total_offensive_yards_per_game"),
        "opp_net_passing_yards": s.get("opp_net_passing_yards"),
        "opp_net_passing_yards_per_game": s.get("opp_net_passing_yards_per_game"),
        "opp_total_points": s.get("opp_total_points"),
        "opp_total_points_per_game": s.get("opp_total_points_per_game"),
        "opp_passing_completions": s.get("opp_passing_completions"),
        "opp_passing_yards": s.get("opp_passing_yards"),
        "opp_passing_yards_per_game": s.get("opp_passing_yards_per_game"),
        "opp_passing_attempts": s.get("opp_passing_attempts"),
        "opp_passing_completion_pct": s.get("opp_passing_completion_pct"),
        "opp_net_total_offensive_yards": s.get("opp_net_total_offensive_yards"),
        "opp_net_total_offensive_yards_per_game": s.get("opp_net_total_offensive_yards_per_game"),
        "opp_net_yards_per_pass_attempt": s.get("opp_net_yards_per_pass_attempt"),
        "opp_yards_per_pass_attempt": s.get("opp_yards_per_pass_attempt"),
        "opp_passing_long": s.get("opp_passing_long"),
        "opp_passing_touchdowns": s.get("opp_passing_touchdowns"),
        "opp_passing_interceptions": s.get("opp_passing_interceptions"),
        "opp_passing_sacks": s.get("opp_passing_sacks"),
        "opp_passing_sack_yards_lost": s.get("opp_passing_sack_yards_lost"),
        "opp_passing_qb_rating": s.get("opp_passing_qb_rating"),
        "opp_rushing_yards": s.get("opp_rushing_yards"),
        "opp_rushing_yards_per_game": s.get("opp_rushing_yards_per_game"),
        "opp_rushing_attempts": s.get("opp_rushing_attempts"),
        "opp_rushing_yards_per_rush_attempt": s.get("opp_rushing_yards_per_rush_attempt"),
        "opp_rushing_long": s.get("opp_rushing_long"),
        "opp_rushing_touchdowns": s.get("opp_rushing_touchdowns"),
        "opp_rushing_fumbles": s.get("opp_rushing_fumbles"),
        "opp_rushing_fumbles_lost": s.get("opp_rushing_fumbles_lost"),
        "opp_receiving_receptions": s.get("opp_receiving_receptions"),
        "opp_receiving_yards": s.get("opp_receiving_yards"),
        "opp_receiving_yards_per_reception": s.get("opp_receiving_yards_per_reception"),
        "opp_receiving_long": s.get("opp_receiving_long"),
        "opp_receiving_touchdowns": s.get("opp_receiving_touchdowns"),
        "opp_receiving_fumbles": s.get("opp_receiving_fumbles"),
        "opp_receiving_fumbles_lost": s.get("opp_receiving_fumbles_lost"),
        "opp_receiving_yards_per_game": s.get("opp_receiving_yards_per_game"),
        "opp_misc_first_downs": s.get("opp_misc_first_downs"),
        "opp_misc_first_downs_rushing": s.get("opp_misc_first_downs_rushing"),
        "opp_misc_first_downs_passing": s.get("opp_misc_first_downs_passing"),
        "opp_misc_first_downs_penalty": s.get("opp_misc_first_downs_penalty"),
        "opp_misc_third_down_convs": s.get("opp_misc_third_down_convs"),
        "opp_misc_third_down_attempts": s.get("opp_misc_third_down_attempts"),
        "opp_misc_third_down_conv_pct": s.get("opp_misc_third_down_conv_pct"),
        "opp_misc_fourth_down_convs": s.get("opp_misc_fourth_down_convs"),
        "opp_misc_fourth_down_attempts": s.get("opp_misc_fourth_down_attempts"),
        "opp_misc_fourth_down_conv_pct": s.get("opp_misc_fourth_down_conv_pct"),
        "opp_misc_total_penalties": s.get("opp_misc_total_penalties"),
        "opp_misc_total_penalty_yards": s.get("opp_misc_total_penalty_yards"),
        "opp_misc_turnover_differential": s.get("opp_misc_turnover_differential"),
        "opp_misc_total_takeaways": s.get("opp_misc_total_takeaways"),
        "opp_misc_total_giveaways": s.get("opp_misc_total_giveaways"),
        "opp_returning_kick_returns": s.get("opp_returning_kick_returns"),
        "opp_returning_kick_return_yards": s.get("opp_returning_kick_return_yards"),
        "opp_returning_yards_per_kick_return": s.get("opp_returning_yards_per_kick_return"),
        "opp_returning_long_kick_return": s.get("opp_returning_long_kick_return"),
        "opp_returning_kick_return_touchdowns": s.get("opp_returning_kick_return_touchdowns"),
        "opp_returning_punt_returns": s.get("opp_returning_punt_returns"),
        "opp_returning_punt_return_yards": s.get("opp_returning_punt_return_yards"),
        "opp_returning_yards_per_punt_return": s.get("opp_returning_yards_per_punt_return"),
        "opp_returning_long_punt_return": s.get("opp_returning_long_punt_return"),
        "opp_returning_punt_return_touchdowns": s.get("opp_returning_punt_return_touchdowns"),
        "opp_returning_punt_return_fair_catches": s.get("opp_returning_punt_return_fair_catches"),
        "opp_kicking_field_goals_made": s.get("opp_kicking_field_goals_made"),
        "opp_kicking_field_goal_attempts": s.get("opp_kicking_field_goal_attempts"),
        "opp_kicking_field_goal_pct": s.get("opp_kicking_field_goal_pct"),
        "opp_kicking_long_field_goal_made": s.get("opp_kicking_long_field_goal_made"),
        "opp_kicking_field_goals_made_1_19": s.get("opp_kicking_field_goals_made_1_19"),
        "opp_kicking_field_goals_made_20_29": s.get("opp_kicking_field_goals_made_20_29"),
        "opp_kicking_field_goals_made_30_39": s.get("opp_kicking_field_goals_made_30_39"),
        "opp_kicking_field_goals_made_40_49": s.get("opp_kicking_field_goals_made_40_49"),
        "opp_kicking_field_goals_made_50": s.get("opp_kicking_field_goals_made_50"),
        "opp_kicking_field_goal_attempts_1_19": s.get("opp_kicking_field_goal_attempts_1_19"),
        "opp_kicking_field_goal_attempts_20_29": s.get("opp_kicking_field_goal_attempts_20_29"),
        "opp_kicking_field_goal_attempts_30_39": s.get("opp_kicking_field_goal_attempts_30_39"),
        "opp_kicking_field_goal_attempts_40_49": s.get("opp_kicking_field_goal_attempts_40_49"),
        "opp_kicking_field_goal_attempts_50": s.get("opp_kicking_field_goal_attempts_50"),
        "opp_kicking_extra_points_made": s.get("opp_kicking_extra_points_made"),
        "opp_kicking_extra_point_attempts": s.get("opp_kicking_extra_point_attempts"),
        "opp_kicking_extra_point_pct": s.get("opp_kicking_extra_point_pct"),
        "opp_punting_punts": s.get("opp_punting_punts"),
        "opp_punting_punt_yards": s.get("opp_punting_punt_yards"),
        "opp_punting_long_punt": s.get("opp_punting_long_punt"),
        "opp_punting_gross_avg_punt_yards": s.get("opp_punting_gross_avg_punt_yards"),
        "opp_punting_net_avg_punt_yards": s.get("opp_punting_net_avg_punt_yards"),
        "opp_punting_punts_blocked": s.get("opp_punting_punts_blocked"),
        "opp_punting_punts_inside_20": s.get("opp_punting_punts_inside_20"),
        "opp_punting_touchbacks": s.get("opp_punting_touchbacks"),
        "opp_punting_fair_catches": s.get("opp_punting_fair_catches"),
        "opp_punting_punt_returns": s.get("opp_punting_punt_returns"),
        "opp_punting_punt_return_yards": s.get("opp_punting_punt_return_yards"),
        "opp_punting_avg_punt_return_yards": s.get("opp_punting_avg_punt_return_yards"),
        "opp_defensive_interceptions": s.get("opp_defensive_interceptions"),

        "updated_at": _now_iso(),
    }


def map_player_prop(p: dict[str, Any]) -> dict[str, Any]:
    market = p.get("market", {})
    market_type = market.get("type", "")
    return {
        "id": str(p.get("id")), # Converted to String as per Postgres Schema change
        "game_id": p.get("game_id"),
        "player_id": p.get("player_id"),
        "vendor": p.get("vendor"),
        "prop_type": p.get("prop_type"),
        "market_type": market_type,
        "line_value": p.get("line_value"),
        "over_odds": market.get("over_odds"),
        "under_odds": market.get("under_odds"),
        "milestone_odds": market.get("odds"), 
        "updated_at": _now_iso(),
    }


def ingest_injuries(
    *,
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    team_ids: Optional[list[int]] = None,
    batch_size: int = 500,
) -> int:
    """Ingest current injury reports from BallDontLie."""
    logger.info("Fetching current injury reports from BallDontLie...")
    all_rows = []
    for inj in bdl.iter_injuries(team_ids=team_ids):
        row = map_injury(inj)
        if row.get("player_id"):
            all_rows.append(row)
            
    logger.info("Fetched %d injury records.", len(all_rows))
    
    if not team_ids:
        logger.info("Full sync: Truncating nfl_injuries table...")
        try:
            deleted_count = supabase.delete("nfl_injuries", filters={"player_id": "gt.0"})
            logger.info("Deleted %d stale injury records", deleted_count)
        except Exception as e:
            logger.warning("Failed to truncate nfl_injuries: %s. Proceeding with upsert.", e)
            
    injuries_upserted = 0
    for chunk in _chunked(all_rows, batch_size):
        if chunk:
            injuries_upserted += supabase.upsert(
                "nfl_injuries", chunk, on_conflict="player_id,date"
            )
    
    logger.info("Ingested nfl_injuries=%d", injuries_upserted)
    return injuries_upserted


def ingest_standings(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    batch_size: int = 500,
) -> int:
    """Ingest team standings from BallDontLie."""
    standings_upserted = 0
    
    for season in seasons:
        for chunk in _chunked(
            (map_standing(s) for s in bdl.iter_standings(season=season)),
            batch_size,
        ):
            valid = [r for r in chunk if r.get("team_id")]
            if valid:
                standings_upserted += supabase.upsert(
                    "nfl_team_standings", valid, on_conflict="team_id,season"
                )
    
    logger.info("Upserted nfl_team_standings=%d", standings_upserted)
    return standings_upserted


def ingest_team_season_stats(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    batch_size: int = 500,
) -> int:
    """Ingest team season stats from BallDontLie."""
    stats_upserted = 0
    
    for season in seasons:
        logger.info(f"Fetching team stats for season {season}")
        for chunk in _chunked(
            (map_team_season_stat(s) for s in bdl.iter_team_season_stats(season=season)),
            batch_size,
        ):
            # Debug check
            if chunk and chunk[0].get("season") is None:
                logger.error(f"CHUNK HAS NULL SEASON: {chunk[0]}")
            
            valid = [r for r in chunk if r.get("team_id")]
            if valid:
                stats_upserted += supabase.upsert(
                    "nfl_team_season_stats", valid, on_conflict="team_id,season,season_type"
                )
    
    logger.info("Upserted nfl_team_season_stats=%d", stats_upserted)
    return stats_upserted


def ingest_player_props_filtered(
    *,
    game_ids: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    vendors: Optional[list[str]] = None,
    batch_size: int = 500,
) -> int:
    """
    Ingest player props with filtering.
    Only ingests over_under markets and anytime_td milestones.
    """
    props_upserted = 0
    filtered_out = 0
    
    for game_id in game_ids:
        try:
            raw_props = list(bdl.iter_player_props(game_id=game_id, vendors=vendors))
            
            # Apply filter
            filtered = [p for p in raw_props if should_ingest_prop(p)]
            filtered_out += len(raw_props) - len(filtered)
            
            for chunk in _chunked([map_player_prop(p) for p in filtered], batch_size):
                valid = [r for r in chunk if r.get("player_id") and r.get("game_id")]
                if valid:
                    props_upserted += supabase.upsert(
                        "nfl_player_props", valid, on_conflict="id"
                    )
        except BallDontLieError as e:
            logger.warning("Skipping props for game_id=%s: %s", game_id, e)
    
    logger.info(
        "Upserted nfl_player_props=%d (filtered out %d milestone bloat)",
        props_upserted,
        filtered_out,
    )
    return props_upserted


def map_injury(inj: dict[str, Any]) -> dict[str, Any]:
    """Map injury to match existing nfl_injuries table schema."""
    player = inj.get("player") if isinstance(inj.get("player"), dict) else {}
    return {
        "player_id": player.get("id"),
        # Only columns that exist in the table:
        "status": inj.get("status"),
        "comment": inj.get("comment"),
        "date": inj.get("date"),
        "updated_at": _now_iso(),
    }


def map_standing(s: dict[str, Any]) -> dict[str, Any]:
    team = s.get("team") if isinstance(s.get("team"), dict) else {}
    return {
        "team_id": team.get("id"),
        "season": s.get("season"),
        "wins": s.get("wins"),
        "losses": s.get("losses"),
        "ties": s.get("ties"),
        "points_for": s.get("points_for"),
        "points_against": s.get("points_against"),
        "point_differential": s.get("point_differential"),
        "playoff_seed": s.get("playoff_seed"),
        "overall_record": s.get("overall_record"),
        "conference_record": s.get("conference_record"),
        "division_record": s.get("division_record"),
        "home_record": s.get("home_record"),
        "road_record": s.get("road_record"),
        "win_streak": s.get("win_streak"),
        "updated_at": _now_iso(),
    }





def map_player_prop(p: dict[str, Any]) -> dict[str, Any]:
    market = p.get("market", {})
    market_type = market.get("type", "")
    return {
        "id": p.get("id"),
        "game_id": p.get("game_id"),
        "player_id": p.get("player_id"),
        "vendor": p.get("vendor"),
        "prop_type": p.get("prop_type"),
        "market_type": market_type,
        "line_value": p.get("line_value"),
        "over_odds": market.get("over_odds") if market_type == "over_under" else None,
        "under_odds": market.get("under_odds") if market_type == "over_under" else None,
        "milestone_odds": market.get("odds") if market_type == "milestone" else None,
        "updated_at": _now_iso(),
    }


def ingest_injuries(
    *,
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    team_ids: Optional[list[int]] = None,
    batch_size: int = 500,
) -> int:
    """Ingest current injury reports from BallDontLie.
    
    Performs a FULL SYNC:
    1. Fetches all current injuries from API.
    2. Deletes ALL existing injuries in DB (if no team filter).
    3. Inserts valid new records.
    This ensures cleared injuries are removed from the database.
    """
    logger.info("Fetching current injury reports from BallDontLie...")
    all_rows = []
    for inj in bdl.iter_injuries(team_ids=team_ids):
        row = map_injury(inj)
        if row.get("player_id"):
            all_rows.append(row)
            
    logger.info("Fetched %d injury records.", len(all_rows))
    
    # Full sync: Delete existing records before inserting
    # Only if we are not filtering by team (full ingest)
    if not team_ids:
        logger.info("Full sync: Truncating nfl_injuries table...")
        # Deleting all rows where player_id > 0 (effectively all)
        try:
            # Fix: Use the new delete method on the client instance
            deleted_count = supabase.delete("nfl_injuries", filters={"player_id": "gt.0"})
            logger.info("Deleted %d stale injury records", deleted_count)
        except Exception as e:
            logger.warning("Failed to truncate nfl_injuries: %s. Proceeding with upsert.", e)
            # If delete fails, fall back to upsert
            
    injuries_upserted = 0
    # Insert in chunks
    for chunk in _chunked(all_rows, batch_size):
        if chunk:
            # Use upsert just in case delete failed or partial update
            injuries_upserted += supabase.upsert(
                "nfl_injuries", chunk, on_conflict="player_id,date"
            )
    
    logger.info("Ingested nfl_injuries=%d", injuries_upserted)
    return injuries_upserted


def ingest_standings(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    batch_size: int = 500,
) -> int:
    """Ingest team standings from BallDontLie."""
    standings_upserted = 0
    
    for season in seasons:
        for chunk in _chunked(
            (map_standing(s) for s in bdl.iter_standings(season=season)),
            batch_size,
        ):
            valid = [r for r in chunk if r.get("team_id")]
            if valid:
                standings_upserted += supabase.upsert(
                    "nfl_team_standings", valid, on_conflict="team_id,season"
                )
    
    logger.info("Upserted nfl_team_standings=%d", standings_upserted)
    return standings_upserted


def ingest_team_season_stats(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    batch_size: int = 500,
) -> int:
    """Ingest team season stats from BallDontLie."""
    stats_upserted = 0
    
    # Fetch all team IDs (required by API)
    logger.info("Fetching team IDs for team season stats...")
    teams = list(bdl.iter_teams())
    team_ids = [t["id"] for t in teams if t.get("id")]
    logger.info(f"Found {len(team_ids)} teams")
    
    for season in seasons:
        for chunk in _chunked(
            (map_team_season_stat(s, season_override=season) for s in bdl.iter_team_season_stats(season=season, team_ids=team_ids)),
            batch_size,
        ):
            valid = [r for r in chunk if r.get("team_id")]
            if valid:
                stats_upserted += supabase.upsert(
                    "nfl_team_season_stats", valid, on_conflict="team_id,season,season_type"
                )
    
    logger.info("Upserted nfl_team_season_stats=%d", stats_upserted)
    return stats_upserted


def ingest_player_props_filtered(
    *,
    game_ids: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    vendors: Optional[list[str]] = None,
    batch_size: int = 500,
) -> int:
    """
    Ingest player props with filtering.
    Only ingests over_under markets and anytime_td milestones.
    """
    props_upserted = 0
    filtered_out = 0
    
    for game_id in game_ids:
        try:
            raw_props = list(bdl.iter_player_props(game_id=game_id, vendors=vendors))
            
            # Apply filter
            filtered = [p for p in raw_props if should_ingest_prop(p)]
            filtered_out += len(raw_props) - len(filtered)
            
            for chunk in _chunked([map_player_prop(p) for p in filtered], batch_size):
                valid = [r for r in chunk if r.get("player_id") and r.get("game_id")]
                if valid:
                    props_upserted += supabase.upsert(
                        "nfl_player_props", valid, on_conflict="id"
                    )
        except BallDontLieError as e:
            logger.warning("Skipping props for game_id=%s: %s", game_id, e)
    
    logger.info(
        "Upserted nfl_player_props=%d (filtered out %d milestone bloat)",
        props_upserted,
        filtered_out,
    )
    return props_upserted


# -----------------------------------------------------------------------------
# Extra Mappers for Full Coverage
# -----------------------------------------------------------------------------

def map_team_game_stat(s: dict[str, Any]) -> dict[str, Any]:
    team = s.get("team") if isinstance(s.get("team"), dict) else {}
    game = s.get("game") if isinstance(s.get("game"), dict) else {}
    return {
        "team_id": team.get("id"),
        "game_id": game.get("id"),
        "season": game.get("season"),
        "week": game.get("week"),
        "home_away": s.get("home_away"),
        "first_downs": s.get("first_downs"),
        "first_downs_passing": s.get("first_downs_passing"),
        "first_downs_rushing": s.get("first_downs_rushing"),
        "first_downs_penalty": s.get("first_downs_penalty"),
        "third_down_efficiency": s.get("third_down_efficiency"),
        "third_down_conversions": s.get("third_down_conversions"),
        "third_down_attempts": s.get("third_down_attempts"),
        "fourth_down_efficiency": s.get("fourth_down_efficiency"),
        "fourth_down_conversions": s.get("fourth_down_conversions"),
        "fourth_down_attempts": s.get("fourth_down_attempts"),
        "total_offensive_plays": s.get("total_offensive_plays"),
        "total_yards": s.get("total_yards"),
        "yards_per_play": s.get("yards_per_play"),
        "total_drives": s.get("total_drives"),
        "net_passing_yards": s.get("net_passing_yards"),
        "passing_completions": s.get("passing_completions"),
        "passing_attempts": s.get("passing_attempts"),
        "yards_per_pass": s.get("yards_per_pass"),
        "sacks": s.get("sacks"),
        "sack_yards_lost": s.get("sack_yards_lost"),
        "rushing_yards": s.get("rushing_yards"),
        "rushing_attempts": s.get("rushing_attempts"),
        "yards_per_rush_attempt": s.get("yards_per_rush_attempt"),
        "red_zone_scores": s.get("red_zone_scores"),
        "red_zone_attempts": s.get("red_zone_attempts"),
        "penalties": s.get("penalties"),
        "penalty_yards": s.get("penalty_yards"),
        "turnovers": s.get("turnovers"),
        "fumbles_lost": s.get("fumbles_lost"),
        "interceptions_thrown": s.get("interceptions_thrown"),
        "defensive_touchdowns": s.get("defensive_touchdowns"),
        "possession_time": s.get("possession_time"),
        "possession_time_seconds": s.get("possession_time_seconds"),
        "updated_at": _now_iso(),
    }

def map_player_season_stat(s: dict[str, Any]) -> dict[str, Any]:
    player = s.get("player") if isinstance(s.get("player"), dict) else {}
    return {
        "player_id": player.get("id"),
        "season": s.get("season"),
        "postseason": s.get("postseason", False),
        "games_played": s.get("games_played"),
        "passing_completions": s.get("passing_completions"),
        "passing_attempts": s.get("passing_attempts"),
        "passing_yards": s.get("passing_yards"),
        "passing_touchdowns": s.get("passing_touchdowns"),
        "passing_interceptions": s.get("passing_interceptions"),
        "passing_yards_per_game": s.get("passing_yards_per_game"),
        "passing_completion_pct": s.get("passing_completion_pct"),
        "qbr": s.get("qbr"),
        "rushing_attempts": s.get("rushing_attempts"),
        "rushing_yards": s.get("rushing_yards"),
        "rushing_yards_per_game": s.get("rushing_yards_per_game"),
        "rushing_touchdowns": s.get("rushing_touchdowns"),
        "rushing_fumbles": s.get("rushing_fumbles"),
        "rushing_first_downs": s.get("rushing_first_downs"),
        "receptions": s.get("receptions"),
        "receiving_yards": s.get("receiving_yards"),
        "receiving_yards_per_game": s.get("receiving_yards_per_game"),
        "receiving_touchdowns": s.get("receiving_touchdowns"),
        "receiving_targets": s.get("receiving_targets"),
        "receiving_first_downs": s.get("receiving_first_downs"),
        "fumbles_forced": s.get("fumbles_forced"),
        "fumbles_recovered": s.get("fumbles_recovered"),
        "total_tackles": s.get("total_tackles"),
        "defensive_sacks": s.get("defensive_sacks"),
        "defensive_interceptions": s.get("defensive_interceptions"),
        "updated_at": _now_iso(),
    }

def map_player_game_stat(s: dict[str, Any]) -> dict[str, Any]:
    player = s.get("player") if isinstance(s.get("player"), dict) else {}
    game = s.get("game") if isinstance(s.get("game"), dict) else {}
    team = s.get("team") if isinstance(s.get("team"), dict) else {}
    return {
        "player_id": player.get("id"),
        "game_id": game.get("id"),
        "team_id": team.get("id"),
        "season": game.get("season"),
        "week": game.get("week"),
        
        "passing_completions": s.get("passing_completions"),
        "passing_attempts": s.get("passing_attempts"),
        "passing_yards": s.get("passing_yards"),
        "passing_touchdowns": s.get("passing_touchdowns"),
        "passing_interceptions": s.get("passing_interceptions"),
        "sacks": s.get("sacks"),
        "qbr": s.get("qbr"),
        "qb_rating": s.get("qb_rating"),
        
        "rushing_attempts": s.get("rushing_attempts"),
        "rushing_yards": s.get("rushing_yards"),
        "rushing_touchdowns": s.get("rushing_touchdowns"),
        
        "receptions": s.get("receptions"),
        "receiving_yards": s.get("receiving_yards"),
        "receiving_touchdowns": s.get("receiving_touchdowns"),
        "receiving_targets": s.get("receiving_targets"),
        
        "fumbles": s.get("fumbles"),
        "fumbles_lost": s.get("fumbles_lost"),
        "fumbles_recovered": s.get("fumbles_recovered"),
        "total_tackles": s.get("total_tackles"),
        "defensive_sacks": s.get("defensive_sacks"),
        "defensive_interceptions": s.get("defensive_interceptions"),
        
        "updated_at": _now_iso(),
    }

def map_game_odds(o: dict[str, Any]) -> dict[str, Any]:
    # Need game_id from wrapping loop usually, but BDL /odds response includes it.
    return {
        "id": str(o.get("id")),
        "game_id": o.get("game_id"),
        "vendor": o.get("vendor"),
        "spread_home_value": o.get("spread_home_value"),
        "spread_home_odds": o.get("spread_home_odds"),
        "spread_away_value": o.get("spread_away_value"),
        "spread_away_odds": o.get("spread_away_odds"),
        "moneyline_home_odds": o.get("moneyline_home_odds"),
        "moneyline_away_odds": o.get("moneyline_away_odds"),
        "total_value": o.get("total_value"),
        "total_over_odds": o.get("total_over_odds"),
        "total_under_odds": o.get("total_under_odds"),
        "updated_at": _now_iso(),
    }

# -----------------------------------------------------------------------------
# New Ingestors
# -----------------------------------------------------------------------------

def ingest_full_stats(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    batch_size: int = 500,
) -> None:
    """Ingest ALL team/player stats (Game & Season level)."""
    
    for season in seasons:
        logger.info(f"== Season {season}: Team Game Stats ==")
        tg_upserted = 0
        try:
            for chunk in _chunked(
                (map_team_game_stat(s) for s in bdl.iter_team_game_stats(season=season)),
                batch_size
            ):
                valid = [r for r in chunk if r.get("team_id") and r.get("game_id")]
                if valid:
                    tg_upserted += supabase.upsert("nfl_team_game_stats", valid, on_conflict="team_id,game_id")
            logger.info(f"Upserted {tg_upserted} team game stats")
        except Exception as e:
            logger.error(f"Failed to ingest Team Game Stats for {season}: {e}")
        
        logger.info(f"== Season {season}: Player Season Stats ==")
        ps_upserted = 0
        try:
            for chunk in _chunked(
                (map_player_season_stat(s) for s in bdl.iter_player_season_stats(season=season)),
                batch_size
            ):
                valid = [r for r in chunk if r.get("player_id")]
                if valid:
                    ps_upserted += supabase.upsert("nfl_player_season_stats", valid, on_conflict="player_id,season,postseason")
            logger.info(f"Upserted {ps_upserted} player season stats")
        except Exception as e:
            logger.error(f"Failed to ingest Player Season Stats for {season}: {e}")
        
        logger.info(f"== Season {season}: Player Game Stats (Basic) ==")
        pg_upserted = 0
        try:
            for chunk in _chunked(
                (map_player_game_stat(s) for s in bdl.iter_player_game_stats(seasons=[season])),
                batch_size
            ):
                valid = [r for r in chunk if r.get("player_id") and r.get("game_id")]
                if valid:
                    pg_upserted += supabase.upsert("nfl_player_game_stats", valid, on_conflict="player_id,game_id")
            logger.info(f"Upserted {pg_upserted} player game stats")
        except Exception as e:
            logger.error(f"Failed to ingest Player Game Stats for {season}: {e}")

def ingest_odds(
    *,
    game_ids: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    batch_size: int = 500,
) -> None:
    """Ingest betting odds for given games."""
    upserted = 0
    # Batch game_ids for query? API takes array. Max length?
    # BDL URL length limits might apply. Chunk game_ids.
    
    game_chunks = _chunked(game_ids, 50) # Safe chunk size for URL params
    for g_chunk in game_chunks:
        try:
            odds_iter = bdl.iter_betting_odds(game_ids=g_chunk)
            rows = [map_game_odds(o) for o in odds_iter]
            for r_chunk in _chunked(rows, batch_size):
                if r_chunk:
                    upserted += supabase.upsert("nfl_game_odds", r_chunk, on_conflict="id")
        except Exception as e:
            logger.warning(f"Error fetching odds for chunk: {e}")
            
    logger.info(f"Upserted {upserted} odds records")

# -----------------------------------------------------------------------------
# Roster & Active Logic
# -----------------------------------------------------------------------------

def map_roster_entry(r: dict[str, Any], team_id: int, season: int) -> dict[str, Any]:
    player_data = r.get("player") or {}
    return {
        "team_id": team_id,
        "player_id": player_data.get("id"),
        "season": season,
        "position": r.get("position"),
        "depth": r.get("depth"),
        "injury_status": r.get("injury_status"),
        "updated_at": _now_iso(),
    }

def ingest_rosters(
    *,
    seasons: list[int],
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    batch_size: int = 500,
) -> None:
    # Iterate all teams (we need team IDs first).
    # We can fetch teams from API or DB.
    # Let's fetch from API to be self-contained.
    logger.info("Fetching Team IDs for Roster ingestion...")
    teams = list(bdl.iter_teams())
    team_ids = [t["id"] for t in teams]
    logger.info(f"Found {len(team_ids)} teams.")
    
    upserted = 0
    
    for season in seasons:
        logger.info(f"== Season {season}: Rosters ==")
        roster_rows = []
        for tid in team_ids:
            try:
                # iter_team_roster returns list or items
                for r in bdl.iter_team_roster(team_id=tid, season=season):
                    mapped = map_roster_entry(r, tid, season)
                    if mapped["player_id"]:
                        roster_rows.append(mapped)
            except Exception as e:
                logger.warning(f"Error fetching roster for team {tid}: {e}")
        
        # Deduplicate: prefer offensive/defensive position over ST (KR/PR/LS/P/PK/H)
        _ST_POSITIONS = {"KR", "PR", "LS", "P", "PK", "H"}
        seen_keys: dict[tuple, dict] = {}
        for row in roster_rows:
            key = (row["team_id"], row["player_id"], row["season"])
            existing = seen_keys.get(key)
            if existing is None:
                seen_keys[key] = row
            elif row.get("position") not in _ST_POSITIONS:
                # New row is offensive/defensive — always prefer it
                seen_keys[key] = row
            # else: new row is ST and we already have a better position — skip
        dedupe_rows = list(seen_keys.values())
        
        # Batch upsert
        for chunk in _chunked(dedupe_rows, batch_size):
            if chunk:
                upserted += supabase.upsert("nfl_rosters", chunk, on_conflict="team_id,player_id,season")
                
    logger.info(f"Upserted {upserted} roster entries.")

def ingest_active_players(
    *,
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
) -> None:
    """
    Fetches all active players and updates the 'is_active' flag in nfl_players.
    Assumption: nfl_players has already been populated with everyone.
    """
    logger.info("Fetching Active Players list...")
    active_ids = []
    try:
        count = 0
        for p in bdl.iter_active_players():
            count += 1
            if p.get("id"):
                active_ids.append(p["id"])
        
        logger.info(f"Found {len(active_ids)} active players.")
        
        if not active_ids:
            return

        # Update in batches. Supabase doesn't have a simple "UPDATE ... WHERE ID IN ..." bulk easily via py client 
        # unless using RPC or careful filters.
        # Alternatively, we can Upsert with only id and is_active=True?
        # Upsert requires all non-null columns if we are inserting new, but for updates it might work 
        # handled by ON CONFLICT DO UPDATE.
        # However, we don't want to wipe other fields if row missing (unlikely if we ingested core).
        # Safest: Use a custom update or just iterate and upsert minimal payload IF we are sure they exist?
        # Actually, if we upsert {"id": X, "is_active": True}, and the row exists, does it keep other columns?
        # Supabase/PostgREST upsert replaces unless specified.
        # Better approach:
        # Use simple update. PostgREST `in_` filter.
        
        # We also need to set EVERYONE to is_active=False first?
        # The Schema default is FALSE. If we wiped the DB, they are False.
        # If we re-run, we might want to reset? 
        # For now, let's just set True for the ones we find.
        
        # Update in chunks
        chunk_size = 200 # Smaller chunk for URL length safety
        total_updated = 0
        
        for i in range(0, len(active_ids), chunk_size):
            chunk = active_ids[i:i+chunk_size]
            ids_str = ",".join(map(str, chunk))
            try:
                # Use custom update method with PostgREST "in." filter
                res = supabase.update(
                    "nfl_players", 
                    {"is_active": True}, 
                    filters={"id": f"in.({ids_str})"}
                )
                total_updated += len(res) # res is list of updated rows
            except Exception as e:
                logger.error(f"Error updating active chunk {i}: {e}")

        logger.info(f"Updated {total_updated} players to Active status.")

    except Exception as e:
        logger.error(f"Error updating active players: {e}")

