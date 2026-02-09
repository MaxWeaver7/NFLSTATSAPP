from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd
import nfl_data_py as nfl
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Team code normalization used across data sources
TEAM_FIX = {
    "WSH": "WAS",
    "BLT": "BAL",
    "CLV": "CLE",
    "HST": "HOU",
    "JAC": "JAX",
    "SD": "LAC",
    "SL": "LA",
    "LAR": "LA",
    "ARZ": "ARI",
}


# ------------------------------
# Helpers
# ------------------------------
def clean_name(name: str | None) -> str:
    if not name:
        return ""
    return (
        str(name)
        .replace(".", "")
        .replace(" Jr", "")
        .replace(" Sr", "")
        .replace(" III", "")
        .replace(" II", "")
        .strip()
        .lower()
    )


def downcast_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if pd.api.types.is_float_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], downcast="float")
        elif pd.api.types.is_integer_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], downcast="integer")
    return df


def safe_read_sql(engine: Engine, query: str, **kwargs) -> pd.DataFrame:
    try:
        return pd.read_sql(query, engine, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Query failed; returning empty df: %s", exc)
        return pd.DataFrame()


# ------------------------------
# Data loading
# ------------------------------
@dataclass
class Lookups:
    players: pd.DataFrame
    teams: pd.DataFrame
    merge_to_player: dict[str, int]
    gsis_to_merge: dict[str, str]
    merge_to_team_abbr: dict[str, str]


def load_player_lookup(engine: Engine, playerid_csv: str) -> Lookups:
    players = safe_read_sql(
        engine,
        "select id as player_id, first_name, last_name, position_abbreviation, team_id "
        "from public.nfl_players",
    )
    teams = safe_read_sql(
        engine,
        "select id as team_id, abbreviation from public.nfl_teams",
    )
    players["merge_name"] = (
        players[["first_name", "last_name"]]
        .fillna("")
        .agg(" ".join, axis=1)
        .map(clean_name)
    )
    teams["abbreviation"] = teams["abbreviation"].map(lambda x: TEAM_FIX.get(x, x))
    merge_to_player = dict(zip(players["merge_name"], players["player_id"]))
    merge_to_team_abbr = dict(
        zip(players["merge_name"], players["team_id"].map(dict(zip(teams.team_id, teams.abbreviation))))
    )

    gsis_map = pd.read_csv(playerid_csv)
    gsis_map["merge_name"] = gsis_map["merge_name"].map(clean_name)
    gsis_to_merge = dict(zip(gsis_map["gsis_id"], gsis_map["merge_name"]))

    return Lookups(
        players=players,
        teams=teams,
        merge_to_player=merge_to_player,
        gsis_to_merge=gsis_to_merge,
        merge_to_team_abbr=merge_to_team_abbr,
    )


@dataclass
class ExternalData:
    pbp: pd.DataFrame
    snap_counts: pd.DataFrame
    ngs: pd.DataFrame
    depth: pd.DataFrame


def load_external_data(seasons: Sequence[int]) -> ExternalData:
    try:
        pbp = nfl.import_pbp_data(list(seasons))
        pbp["defteam"] = pbp["defteam"].replace(TEAM_FIX)
        pbp["posteam"] = pbp["posteam"].replace(TEAM_FIX)
    except Exception as exc:  # pragma: no cover - downstream will guard
        logger.warning("Failed to load PBP: %s", exc)
        pbp = pd.DataFrame()

    try:
        sc = nfl.import_snap_counts(list(seasons))
        sc["merge_name"] = sc["player"].map(clean_name)
        sc["team"] = sc["team"].replace(TEAM_FIX)
        snap_counts = sc[["merge_name", "season", "week", "offense_pct"]].rename(
            columns={"offense_pct": "snap_pct"}
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to load snap counts: %s", exc)
        snap_counts = pd.DataFrame(columns=["merge_name", "season", "week", "snap_pct"])

    try:
        ng = nfl.import_ngs_data(stat_type="receiving", years=list(seasons))
        ng["merge_name"] = ng["player_display_name"].map(clean_name)
        cols = [c for c in ["avg_separation", "catch_percentage_above_expectation", "avg_intended_air_yards"] if c in ng.columns]
        ngs = ng[["merge_name", "season", "week"] + cols].rename(
            columns={"avg_intended_air_yards": "ngs_adot"}
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to load NGS: %s", exc)
        ngs = pd.DataFrame(columns=["merge_name", "season", "week"])

    try:
        depth_raw = nfl.import_depth_charts(list(seasons))
        depth_raw = depth_raw[depth_raw["formation"] == "Offense"]
        depth_raw["merge_name"] = depth_raw["full_name"].map(clean_name)
        depth_raw["depth_rank"] = depth_raw["depth_position"]
        depth_raw["is_starter"] = (depth_raw["depth_rank"].astype(str) == "1").astype(int)
        depth_raw["is_slot"] = (depth_raw["depth_position"] == "SWR").astype(int)
        depth = depth_raw[["merge_name", "season", "week", "depth_rank", "is_starter", "is_slot"]]
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to load depth charts: %s", exc)
        depth = pd.DataFrame(columns=["merge_name", "season", "week", "depth_rank", "is_starter", "is_slot"])

    return ExternalData(pbp=pbp, snap_counts=snap_counts, ngs=ngs, depth=depth)


# ------------------------------
# Core builders
# ------------------------------
def _aggregate_defense(pbp: pd.DataFrame) -> pd.DataFrame:
    if pbp.empty:
        return pd.DataFrame(
            columns=[
                "team_abbr",
                "season",
                "week",
                "def_epa",
                "def_success",
                "def_adot",
                "def_td_rate",
                "def_pressure_pct",
                "def_sack_rate",
            ]
        )
    passing = pbp[pbp["play_type"] == "pass"].copy()
    agg = (
        passing.groupby(["defteam", "season", "week"])
        .agg(
            def_epa=("epa", "mean"),
            def_success=("success", "mean"),
            def_adot=("air_yards", "mean"),
            def_td_rate=("pass_touchdown", "mean"),
            def_pressure_pct=("was_pressure", "mean"),
            def_sack_rate=("sack", "mean"),
        )
        .reset_index()
        .rename(columns={"defteam": "team_abbr"})
    )
    return downcast_numeric(agg)


def _aggregate_game_script(pbp: pd.DataFrame) -> pd.DataFrame:
    if pbp.empty:
        return pd.DataFrame(columns=["team_abbr", "season", "week", "team_pace", "team_proe", "neutral_pace", "neutral_pass_rate"])
    pbp = pbp.copy()
    pbp["seconds_elapsed"] = pbp["game_seconds_remaining"].diff().abs().fillna(0)
    neutral = pbp[(pbp["wp"] >= 0.20) & (pbp["wp"] <= 0.80) & (pbp["play_type"].isin(["pass", "run"]))]
    pace = (
        neutral.groupby(["posteam", "season", "week"])["seconds_elapsed"]
        .mean()
        .reset_index()
        .rename(columns={"posteam": "team_abbr", "seconds_elapsed": "team_pace"})
    )
    if "xpass" in pbp.columns and "pass" in pbp.columns:
        pbp["pass_oe"] = pbp["pass"] - pbp["xpass"]
        proe = (
            pbp.groupby(["posteam", "season", "week"])["pass_oe"]
            .mean()
            .reset_index()
            .rename(columns={"posteam": "team_abbr", "pass_oe": "team_proe"})
        )
    else:
        proe = pd.DataFrame(columns=["team_abbr", "season", "week", "team_proe"])
    out = pace.merge(proe, on=["team_abbr", "season", "week"], how="outer")
    out["neutral_pace"] = out["team_pace"]
    out["neutral_pass_rate"] = out["team_proe"]
    return out


def _aggregate_receiver_pbp(pbp: pd.DataFrame, lookups: Lookups) -> pd.DataFrame:
    if pbp.empty:
        return pd.DataFrame(columns=["merge_name", "season", "week", "wopr", "racr", "target_share", "air_yards_share", "rz_targets"])

    pbp = pbp.copy()
    pbp["merge_name"] = pbp["receiver_player_id"].map(lookups.gsis_to_merge)
    pbp = pbp[pbp["merge_name"].notna()]

    p_agg = (
        pbp.groupby(["merge_name", "posteam", "season", "week"])
        .agg(
            targets=("play_id", "count"),
            air_yards=("air_yards", "sum"),
            rec_yards=("receiving_yards", "sum"),
            rz_targets=("yardline_100", lambda x: (x <= 20).sum()),
        )
        .reset_index()
    )

    t_agg = (
        pbp.groupby(["posteam", "season", "week"])
        .agg(team_targets=("play_id", "count"), team_air_yards=("air_yards", "sum"))
        .reset_index()
    )

    merged = p_agg.merge(
        t_agg,
        on=["posteam", "season", "week"],
        how="left",
    )
    merged["target_share"] = merged["targets"] / merged["team_targets"]
    merged["air_yards_share"] = merged["air_yards"] / merged["team_air_yards"]
    merged["wopr"] = 1.5 * merged["target_share"] + 0.7 * merged["air_yards_share"]
    merged["racr"] = merged["rec_yards"] / merged["air_yards"].replace(0, np.nan)
    merged = merged.replace([np.inf, -np.inf], np.nan)
    merged = merged.rename(columns={"posteam": "team_abbr"})
    return merged[["merge_name", "team_abbr", "season", "week", "wopr", "racr", "target_share", "air_yards_share", "rz_targets"]]


def _aggregate_weather(pbp: pd.DataFrame) -> pd.DataFrame:
    if pbp.empty:
        return pd.DataFrame(columns=["game_id", "temp", "wind_speed", "precip", "surface", "roof", "is_precip", "is_wind_cold"])
    cols = [c for c in ["game_id", "temp", "wind", "weather", "roof", "surface"] if c in pbp.columns]
    if not cols:
        return pd.DataFrame(columns=["game_id", "temp", "wind_speed", "precip", "surface", "roof", "is_precip", "is_wind_cold"])
    wx = pbp[cols].drop_duplicates(subset=["game_id"])
    wx = wx.rename(columns={"wind": "wind_speed"})
    wx["precip"] = wx.get("weather")
    wx["is_precip"] = wx["precip"].astype(str).str.contains("rain|snow|drizzle|sleet", case=False, na=False).astype(int)
    wx["is_wind_cold"] = (
        (pd.to_numeric(wx.get("wind_speed"), errors="coerce").fillna(0) >= 15)
        & (pd.to_numeric(wx.get("temp"), errors="coerce").fillna(60) <= 40)
    ).astype(int)
    return wx


def _rolling_features(df: pd.DataFrame, cols: Sequence[str], group: str = "player_id") -> pd.DataFrame:
    df = df.sort_values([group, "season", "week"])
    for c in cols:
        if c in df.columns:
            df[f"{c}_last3"] = df.groupby(group)[c].transform(lambda x: x.rolling(3).mean().shift(1))
            df[f"{c}_last5"] = df.groupby(group)[c].transform(lambda x: x.rolling(5).mean().shift(1))
    return df


def _qb_features(passing: pd.DataFrame) -> pd.DataFrame:
    needed = {"team_id", "season", "week"}
    if passing.empty or not needed.issubset(set(passing.columns)):
        return pd.DataFrame(columns=["team_id", "season", "week", "qb_cpoe", "qb_aggressiveness", "qb_ttt", "qb_adot"])
    passing = passing.copy()
    passing["attempts"] = passing["attempts"].fillna(0)
    passing = passing.sort_values(["team_id", "season", "week", "attempts"], ascending=[True, True, True, False])
    top = passing.groupby(["team_id", "season", "week"]).head(1)
    top = top.rename(
        columns={
            "completion_percentage_above_expectation": "qb_cpoe",
            "aggressiveness": "qb_aggressiveness",
            "avg_time_to_throw": "qb_ttt",
            "avg_intended_air_yards": "qb_adot",
            "avg_air_distance": "qb_air_distance",
        }
    )
    keep = ["team_id", "season", "week", "qb_cpoe", "qb_aggressiveness", "qb_ttt", "qb_adot", "qb_air_distance"]
    return downcast_numeric(top[keep])


# ------------------------------
# Feature assembly
# ------------------------------
def build_base_training(engine: Engine, seasons: Sequence[int]) -> pd.DataFrame:
    query = f"""
        select 
            pgs.player_id,
            pgs.game_id,
            pgs.team_id,
            pgs.season,
            pgs.week,
            pgs.postseason,
            pgs.receptions,
            pgs.receiving_targets,
            pgs.receiving_yards,
            pgs.receiving_touchdowns,
            g.home_team_id,
            g.visitor_team_id,
            g.date,
            g.season as game_season,
            g.week as game_week
        from public.nfl_player_game_stats pgs
        join public.nfl_games g on g.id = pgs.game_id
        where pgs.receiving_targets is not null
          and pgs.season in ({",".join(str(s) for s in seasons)})
    """
    return safe_read_sql(engine, query)


def build_inference_candidates(engine: Engine, seasons: Sequence[int]) -> pd.DataFrame:
    query = f"""
        select 
            pp.player_id,
            pp.game_id,
            g.season,
            g.week,
            g.home_team_id,
            g.visitor_team_id,
            g.date,
            pp.line_value as prop_line_yards,
            pp.over_odds,
            pp.under_odds
        from public.nfl_player_props pp
        join public.nfl_games g on g.id = pp.game_id
        where pp.prop_type in ('player_rec_yds','receiving_yards')
          and g.season in ({",".join(str(s) for s in seasons)})
    """
    return safe_read_sql(engine, query)


def load_advanced(engine: Engine, seasons: Sequence[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    recv = safe_read_sql(
        engine,
        f"""
        select * from public.nfl_advanced_receiving_stats
        where season in ({",".join(str(s) for s in seasons)})
        """,
    )
    pass_adv = safe_read_sql(
        engine,
        f"""
        select * from public.nfl_advanced_passing_stats
        where season in ({",".join(str(s) for s in seasons)})
        """,
    )
    return recv, pass_adv


def load_betting(engine: Engine, seasons: Sequence[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Some deployments may not store season on these tables; fall back to full table if filter fails.
    odds = safe_read_sql(
        engine,
        f"""
        select * from public.nfl_betting_odds
        """,
    )
    props = safe_read_sql(
        engine,
        f"""
        select * from public.nfl_player_props
        where prop_type in ('player_rec_yds','receiving_yards')
        """,
    )
    # If season column exists, keep only requested seasons
    if "season" in odds.columns:
        odds = odds[odds["season"].isin(seasons)]
    if "season" in props.columns:
        props = props[props["season"].isin(seasons)]
    return odds, props


def _defense_allowance(engine: Engine, seasons: Sequence[int], lookups: Lookups) -> pd.DataFrame:
    pgs = safe_read_sql(
        engine,
        f"""
        select 
            pgs.player_id,
            pgs.game_id,
            pgs.team_id,
            pgs.season,
            pgs.week,
            pgs.receiving_yards,
            pgs.passing_completions,
            pgs.passing_attempts
        from public.nfl_player_game_stats pgs
        where pgs.season in ({",".join(str(s) for s in seasons)})
        """,
    )
    games = safe_read_sql(
        engine,
        f"""
        select id as game_id, home_team_id, visitor_team_id
        from public.nfl_games
        where season in ({",".join(str(s) for s in seasons)})
        """,
    )
    if pgs.empty or games.empty:
        return pd.DataFrame(columns=["team_abbr", "season", "opp_pass_yards_allowed_pg_prior", "opp_comp_pct_allowed"])
    merged = pgs.merge(games, on="game_id", how="left")
    if "season" not in merged.columns:
        if "season_x" in merged.columns:
            merged["season"] = merged["season_x"]
        elif "season_y" in merged.columns:
            merged["season"] = merged["season_y"]
    if "week" not in merged.columns:
        if "week_x" in merged.columns:
            merged["week"] = merged["week_x"]
        elif "week_y" in merged.columns:
            merged["week"] = merged["week_y"]
    merged["def_team_id"] = np.where(merged["team_id"] == merged["home_team_id"], merged["visitor_team_id"], merged["home_team_id"])
    per_game = (
        merged.groupby(["def_team_id", "season", "game_id"])
        .agg(
            rec_yards=("receiving_yards", "sum"),
            comp=("passing_completions", "sum"),
            att=("passing_attempts", "sum"),
        )
        .reset_index()
    )
    allow = (
        per_game.groupby(["def_team_id", "season"])
        .agg(
            opp_pass_yards_allowed_pg_prior=("rec_yards", "mean"),
            comp=("comp", "sum"),
            att=("att", "sum"),
        )
        .reset_index()
    )
    allow["opp_comp_pct_allowed"] = allow["comp"] / allow["att"].replace(0, np.nan)
    team_map = dict(zip(lookups.teams.team_id, lookups.teams.abbreviation))
    allow["team_abbr"] = allow["def_team_id"].map(team_map).map(lambda x: TEAM_FIX.get(x, x))
    return downcast_numeric(allow.drop(columns=["comp", "att"]))


def _attach_team_abbr(df: pd.DataFrame, lookups: Lookups) -> pd.DataFrame:
    df = df.copy()
    for col in ["team_id", "home_team_id", "visitor_team_id", "season", "week"]:
        if col not in df.columns:
            df[col] = np.nan

    team_map = dict(zip(lookups.teams.team_id, lookups.teams.abbreviation))
    df["team_abbr"] = df["team_id"].map(team_map).map(lambda x: TEAM_FIX.get(x, x))
    df["home_team_abbr"] = df["home_team_id"].map(team_map).map(lambda x: TEAM_FIX.get(x, x))
    df["opponent_team_abbr"] = np.where(
        df["team_id"] == df["home_team_id"],
        df["visitor_team_id"].map(team_map),
        df["home_team_id"].map(team_map),
    )
    df["opponent_team_abbr"] = df["opponent_team_abbr"].map(lambda x: TEAM_FIX.get(x, x))
    df["is_home"] = (df["team_id"] == df["home_team_id"]).astype(int)
    return df


def _merge_player_features(
    base: pd.DataFrame,
    adv_recv: pd.DataFrame,
    receiver_pbp: pd.DataFrame,
    snap_counts: pd.DataFrame,
    ngs: pd.DataFrame,
    depth: pd.DataFrame,
    lookups: Lookups,
) -> pd.DataFrame:
    df = base.copy()
    df["merge_name"] = df["player_id"].map(dict(zip(lookups.players.player_id, lookups.players.merge_name)))

    required_adv_cols = [
        "avg_intended_air_yards",
        "avg_yac",
        "avg_expected_yac",
        "avg_yac_above_expectation",
        "avg_cushion",
        "avg_separation",
        "percent_share_of_intended_air_yards",
        "catch_percentage",
    ]
    for col in required_adv_cols:
        if col not in adv_recv.columns:
            adv_recv[col] = np.nan

    adv_recv = adv_recv.rename(
        columns={
            "avg_intended_air_yards": "adv_avg_intended_air_yards",
            "avg_yac": "adv_avg_yac",
            "avg_expected_yac": "adv_avg_expected_yac",
            "avg_yac_above_expectation": "adv_yac_aoe",
            "avg_cushion": "adv_avg_cushion",
            "avg_separation": "adv_avg_separation",
            "percent_share_of_intended_air_yards": "adv_share_air_yards",
            "catch_percentage": "adv_catch_pct",
        }
    )
    adv_required = [
        "player_id",
        "season",
        "week",
        "adv_avg_intended_air_yards",
        "adv_avg_yac",
        "adv_avg_expected_yac",
        "adv_yac_aoe",
        "adv_avg_cushion",
        "adv_avg_separation",
        "adv_share_air_yards",
        "adv_catch_pct",
    ]
    for col in adv_required:
        if col not in adv_recv.columns:
            adv_recv[col] = np.nan
    adv_sel = adv_recv.reindex(columns=adv_required)
    df = df.merge(
        adv_sel,
        on=["player_id", "season", "week"],
        how="left",
    )

    for ext_df in (receiver_pbp, snap_counts, ngs, depth):
        if ext_df.empty:
            continue
        df = df.merge(
            ext_df,
            on=["merge_name", "season", "week"],
            how="left",
        )
    return df


def _merge_defense_context(df: pd.DataFrame, defense: pd.DataFrame, script: pd.DataFrame, allowance: pd.DataFrame) -> pd.DataFrame:
    if not defense.empty:
        df = df.merge(
            defense,
            left_on=["opponent_team_abbr", "season", "week"],
            right_on=["team_abbr", "season", "week"],
            how="left",
        ).drop(columns=["team_abbr"], errors="ignore")
    if not allowance.empty:
        df = df.merge(
            allowance,
            left_on=["opponent_team_abbr", "season"],
            right_on=["team_abbr", "season"],
            how="left",
        ).drop(columns=["team_abbr"], errors="ignore")
    if not script.empty:
        df = df.merge(
            script,
            left_on=["team_abbr", "season", "week"],
            right_on=["team_abbr", "season", "week"],
            how="left",
        )
    return df


def _merge_betting_weather_qb(
    df: pd.DataFrame,
    odds: pd.DataFrame,
    props: pd.DataFrame,
    weather: pd.DataFrame,
    qb: pd.DataFrame,
) -> pd.DataFrame:
    if not odds.empty:
        df = df.merge(
            odds[
                [
                    "game_id",
                    "spread_home_value",
                    "spread_home_odds",
                    "spread_away_value",
                    "total_value",
                    "total_over_odds",
                    "total_under_odds",
                ]
            ],
            on="game_id",
            how="left",
        )
    if not props.empty:
        df = df.merge(
            props[["player_id", "game_id", "line_value", "over_odds", "under_odds"]].rename(
                columns={"line_value": "prop_line_yards"}
            ),
            on=["player_id", "game_id"],
            how="left",
        )
    if not weather.empty:
        df = df.merge(weather, on="game_id", how="left")
    if not qb.empty:
        df = df.merge(
            qb,
            left_on=["team_id", "season", "week"],
            right_on=["team_id", "season", "week"],
            how="left",
        )
    return df


def _compute_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "team_proe" not in df.columns:
        df["team_proe"] = 0
    for col in ["receiving_targets", "receptions", "receiving_yards", "team_id", "season", "week"]:
        if col not in df.columns:
            df[col] = 0
    df["spread_home_value"] = (
        pd.to_numeric(df["spread_home_value"], errors="coerce").fillna(0)
        if "spread_home_value" in df.columns
        else 0
    )
    df["total_value"] = pd.to_numeric(df["total_value"], errors="coerce").fillna(0) if "total_value" in df.columns else 0
    df["is_wind_cold"] = (
        pd.to_numeric(df["is_wind_cold"], errors="coerce").fillna(0) if "is_wind_cold" in df.columns else 0
    )
    df["wind_speed"] = (
        pd.to_numeric(df["wind_speed"], errors="coerce").fillna(0) if "wind_speed" in df.columns else 0
    )
    df["adv_avg_intended_air_yards"] = (
        pd.to_numeric(df["adv_avg_intended_air_yards"], errors="coerce").fillna(0)
        if "adv_avg_intended_air_yards" in df.columns
        else 0
    )
    df["label_receiving_yards"] = df.get("receiving_yards")
    df["target_share"] = df["receiving_targets"] / df.groupby(["team_id", "season", "week"])["receiving_targets"].transform("sum")
    df["air_yards_est"] = df["receiving_targets"] * df["adv_avg_intended_air_yards"]
    df["air_yards_share"] = df["adv_share_air_yards"]
    df["wopr"] = 1.5 * df["target_share"] + 0.7 * df["air_yards_share"]
    df["racr"] = df["receiving_yards"] / df["air_yards_est"].replace(0, np.nan)
    df["catch_rate"] = df["receptions"] / df["receiving_targets"].replace(0, np.nan)
    df["yac_oe"] = df["adv_yac_aoe"]
    df = df.sort_values(["player_id", "season", "week"])
    df["games_played_prior"] = df.groupby(["player_id", "season"]).cumcount()
    df["targets_cum"] = df.groupby(["player_id", "season"])["receiving_targets"].cumsum().shift(1)
    df["rec_yards_cum"] = df.groupby(["player_id", "season"])["receiving_yards"].cumsum().shift(1)
    df["targets_per_game_prior"] = df["targets_cum"] / df["games_played_prior"].replace(0, np.nan)
    df["rec_yards_per_game_prior"] = df["rec_yards_cum"] / df["games_played_prior"].replace(0, np.nan)
    df["rec_yards_last3_avg"] = df.groupby(["player_id", "season"])["receiving_yards"].transform(lambda x: x.rolling(3).mean().shift(1))
    df["targets_last3_avg"] = df.groupby(["player_id", "season"])["receiving_targets"].transform(lambda x: x.rolling(3).mean().shift(1))
    df["yards_per_target_prior"] = df["rec_yards_cum"] / df["targets_cum"].replace(0, np.nan)
    df["rest_days"] = pd.to_datetime(df.get("date")).groupby(df["team_id"]).diff().dt.days
    df["rest_days"] = df["rest_days"].fillna(df["rest_days"].median())
    df["log_week"] = np.log1p(df["week"])
    df["season_week_index"] = df["season"] * 100 + df["week"]
    df["script_volatility"] = df.groupby("team_id")["team_proe"].transform(lambda x: x.rolling(4).std())
    df["team_spread"] = np.where(df["is_home"] == 1, df["spread_home_value"], -df["spread_home_value"])
    df["team_spread_abs"] = df["team_spread"].abs()
    df["implied_spread"] = df["team_spread"]
    df["implied_total"] = df["total_value"]
    df["prop_edge"] = 0.0
    df["prop_edge_pct"] = 0.0
    df["neutral_pace"] = df.get("neutral_pace")
    df["neutral_pass_rate"] = df.get("neutral_pass_rate")
    df["wind_pass_interaction"] = pd.to_numeric(df.get("wind_speed"), errors="coerce") * pd.to_numeric(
        df.get("adv_avg_intended_air_yards"), errors="coerce"
    )
    df["cold_wind_interaction"] = df.get("is_wind_cold") * pd.to_numeric(
        df.get("adv_avg_intended_air_yards"), errors="coerce"
    )
    return df.replace([np.inf, -np.inf], np.nan)


FEATURE_COLUMNS: list[str] = [
    # Opportunity / role
    "snap_pct",
    "snap_pct_last3",
    "snap_pct_last5",
    "target_share",
    "target_share_last3",
    "target_share_last5",
    "air_yards_share",
    "air_yards_share_last3",
    "air_yards_share_last5",
    "wopr",
    "wopr_last3",
    "wopr_last5",
    "racr",
    "racr_last3",
    "racr_last5",
    "rz_targets",
    "depth_rank",
    "is_starter",
    "is_slot",
    "receiving_targets",
    "receptions",
    "receiving_yards",
    "receiving_touchdowns",
    "games_played_prior",
    "targets_cum",
    "rec_yards_cum",
    "targets_per_game_prior",
    "rec_yards_per_game_prior",
    "rec_yards_last3_avg",
    "targets_last3_avg",
    "yards_per_target_prior",
    # Efficiency
    "adv_avg_separation",
    "adv_avg_cushion",
    "adv_catch_pct",
    "adv_avg_intended_air_yards",
    "adv_avg_yac",
    "adv_avg_expected_yac",
    "adv_yac_aoe",
    "catch_rate",
    "catch_rate_last3",
    "catch_rate_last5",
    "ngs_adot",
    "ngs_adot_last3",
    "ngs_adot_last5",
    "avg_separation_last3",
    "avg_separation_last5",
    "adv_avg_intended_air_yards_last3",
    "adv_avg_intended_air_yards_last5",
    "adv_yac_aoe_last3",
    "adv_yac_aoe_last5",
    "adv_avg_yac_last3",
    "adv_avg_yac_last5",
    "adv_avg_expected_yac_last3",
    "adv_avg_expected_yac_last5",
    "yac_oe",
    # Form / recency extras
    "rec_yards_per_game_prior",
    "rec_yards_per_game_prior_last3",
    "rec_yards_per_game_prior_last5",
    "targets_per_game_prior_last3",
    "targets_per_game_prior_last5",
    "racr_last3",
    "racr_last5",
    # Defense / matchup
    "def_epa",
    "def_success",
    "def_adot",
    "def_td_rate",
    "def_pressure_pct",
    "def_sack_rate",
    "opp_pass_yards_allowed_pg_prior",
    "opp_comp_pct_allowed",
    # Game context
    "team_pace",
    "team_proe",
    "script_volatility",
    "neutral_pace",
    "neutral_pass_rate",
    "spread_home_value",
    "spread_home_odds",
    "spread_away_value",
    "team_spread",
    "team_spread_abs",
    "total_value",
    "total_over_odds",
    "total_under_odds",
    "prop_line_yards",
    "over_odds",
    "under_odds",
    "is_home",
    "postseason",
    "season",
    "week",
    "log_week",
    "season_week_index",
    "rest_days",
    # Usage / alignment placeholders (filled if available)
    "slot_rate",
    "wide_rate",
    "two_minute_rate",
    "third_down_target_share",
    "red_zone_target_share",
    "first_read_rate",
    "created_reception_rate",
    "contested_catch_rate",
    "drop_rate",
    "no_huddle_rate",
    "motion_rate",
    "rpo_rate",
    "screen_rate",
    "play_action_rate",
    "shotgun_rate",
    "n_blitzers_avg",
    "n_pass_rushers_avg",
    # Betting alignment extras
    "implied_total",
    "implied_spread",
    "prop_edge",
    "prop_edge_pct",
    "wind_pass_interaction",
    "cold_wind_interaction",
    # Weather
    "temp",
    "wind_speed",
    "precip",
    "is_precip",
    "is_wind_cold",
    "humidity",
    "temp_feels_like",
    # Defense advanced placeholders
    "def_blitz_pct",
    "def_missed_tackle_pct",
    "def_man_rate",
    "def_zone_rate",
    "def_coverage_unknown_rate",
    "def_pressure_to_sack",
    "def_explosive_pass_rate",
    # Opponent tendencies placeholders
    "opp_pace",
    "opp_pass_rate",
    "opp_no_huddle_rate",
    "opp_rpo_rate",
    "opp_screen_rate",
    "opp_motion_rate",
    # QB linkage
    "qb_cpoe",
    "qb_aggressiveness",
    "qb_ttt",
    "qb_adot",
    "qb_air_distance",
    # Alignment placeholders
    "slot_snap_pct",
    "wide_snap_pct",
    "backfield_snap_pct",
    "inline_snap_pct",
    # Stability / data quality
    "samples_targets",
    "samples_air_yards",
    "samples_ngs",
    "samples_snap_counts",
    "samples_depth",
]


def ensure_feature_columns(df: pd.DataFrame, features: Sequence[str]) -> pd.DataFrame:
    for f in features:
        if f not in df.columns:
            df[f] = np.nan
        df[f] = pd.to_numeric(df[f], errors="coerce").fillna(0)
    return df


def build_feature_matrices(
    engine: Engine,
    seasons: Sequence[int],
    playerid_csv: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookups = load_player_lookup(engine, playerid_csv)
    external = load_external_data(seasons)
    defense = _aggregate_defense(external.pbp)
    script = _aggregate_game_script(external.pbp)
    receiver_pbp = _aggregate_receiver_pbp(external.pbp, lookups)
    weather = _aggregate_weather(external.pbp)
    allowance = _defense_allowance(engine, seasons, lookups)
    adv_recv, adv_pass = load_advanced(engine, seasons)
    odds, props = load_betting(engine, seasons)
    qb = _qb_features(adv_pass)

    train = build_base_training(engine, seasons)
    inf = build_inference_candidates(engine, seasons)

    train = _attach_team_abbr(train, lookups)
    inf = _attach_team_abbr(inf, lookups)

    train = _merge_player_features(train, adv_recv, receiver_pbp, external.snap_counts, external.ngs, external.depth, lookups)
    inf = _merge_player_features(inf, adv_recv, receiver_pbp, external.snap_counts, external.ngs, external.depth, lookups)

    train = _merge_defense_context(train, defense, script, allowance)
    inf = _merge_defense_context(inf, defense, script, allowance)

    train = _merge_betting_weather_qb(train, odds, props, weather, qb)
    inf = _merge_betting_weather_qb(inf, odds, props, weather, qb)

    train = _compute_derived(train)
    inf = _compute_derived(inf)

    roll_cols = [
        "snap_pct",
        "target_share",
        "air_yards_share",
        "wopr",
        "racr",
        "adv_avg_separation",
        "adv_avg_intended_air_yards",
        "adv_yac_aoe",
        "ngs_adot",
        "catch_rate",
        "rec_yards_per_game_prior",
        "targets_per_game_prior",
        "adv_avg_yac",
        "adv_avg_expected_yac",
    ]
    train = _rolling_features(train, roll_cols)
    inf = _rolling_features(inf, roll_cols)

    train = ensure_feature_columns(train, FEATURE_COLUMNS)
    inf = ensure_feature_columns(inf, FEATURE_COLUMNS)

    train = downcast_numeric(train)
    inf = downcast_numeric(inf)

    return train, inf


def persist_features(
    train: pd.DataFrame,
    inf: pd.DataFrame,
    engine: Engine,
    train_table: str = "features_wr_receiving_training_v2",
    inf_table: str = "features_wr_receiving_week18_v2",
) -> None:
    train.to_sql(train_table, engine, if_exists="replace", index=False)
    inf.to_sql(inf_table, engine, if_exists="replace", index=False)


def get_engine(db_uri: Optional[str] = None) -> Engine:
    uri = db_uri or os.getenv("SUPABASE_DB_URI") or os.getenv("DB_URI")
    if not uri:
        raise RuntimeError("Missing DB URI. Set SUPABASE_DB_URI or DB_URI.")
    return create_engine(uri)


__all__ = [
    "build_feature_matrices",
    "persist_features",
    "get_engine",
    "FEATURE_COLUMNS",
]


