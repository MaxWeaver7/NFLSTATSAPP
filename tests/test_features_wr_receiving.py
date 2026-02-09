import pandas as pd

from src.ingestion.features_wr_receiving import ensure_feature_columns, FEATURE_COLUMNS, _compute_derived


def test_ensure_feature_columns_adds_and_fills():
    df = pd.DataFrame({"a": [1.0]})
    out = ensure_feature_columns(df, ["a", "missing_col"])
    assert "missing_col" in out.columns
    assert out["missing_col"].iloc[0] == 0


def test_compute_derived_basic_signals():
    rows = [
        {
            "player_id": 1,
            "team_id": 10,
            "season": 2025,
            "week": 1,
            "game_id": 100,
            "receptions": 5,
            "receiving_targets": 7,
            "receiving_yards": 80,
            "adv_avg_intended_air_yards": 10.0,
            "adv_share_air_yards": 0.3,
            "adv_yac_aoe": 1.2,
            "team_proe": 0.05,
            "is_home": 1,
            "spread_home_value": -3.5,
            "total_value": 45.5,
            "date": "2025-09-01",
        },
        {
            "player_id": 1,
            "team_id": 10,
            "season": 2025,
            "week": 2,
            "game_id": 101,
            "receptions": 6,
            "receiving_targets": 9,
            "receiving_yards": 90,
            "adv_avg_intended_air_yards": 9.0,
            "adv_share_air_yards": 0.35,
            "adv_yac_aoe": 0.5,
            "team_proe": 0.02,
            "is_home": 0,
            "spread_home_value": 2.5,
            "total_value": 48.0,
            "date": "2025-09-08",
        },
    ]
    base = pd.DataFrame(rows)
    derived = _compute_derived(base)
    for col in [
        "target_share",
        "wopr",
        "racr",
        "catch_rate",
        "games_played_prior",
        "targets_cum",
        "rec_yards_cum",
        "rec_yards_per_game_prior",
        "team_spread",
        "implied_total",
        "log_week",
    ]:
        assert col in derived.columns
        assert pd.notnull(derived[col]).any()


