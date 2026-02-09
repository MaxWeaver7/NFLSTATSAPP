import sqlite3

import pytest

from src.database.schema import create_tables
from src.metrics.calculator import compute_all_metrics
from src.web import queries
from src.validation.checks import (
    check_no_duplicate_plays,
    check_routes_ge_targets,
    check_season_totals_sum_correctly,
    check_targets_pfr_vs_pbp,
    check_yprr_bounds,
    run_all_checks,
)


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON;")
    create_tables(c)
    return c


def seed_minimal_game(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executemany("INSERT OR IGNORE INTO teams(team_abbr) VALUES (?)", [("KC",), ("BUF",)])
    cur.execute(
        """
        INSERT INTO games(game_id, season, week, home_team, away_team)
        VALUES ('G1', 2024, 1, 'KC', 'BUF')
        """
    )
    # player_id values intentionally resemble PFR-style IDs (often used in data-stat="player")
    cur.executemany(
        "INSERT INTO players(player_id, player_name, position, team_abbr) VALUES (?, ?, ?, ?)",
        [
            ("KelcTr00", "Travis Kelce", "TE", "KC"),
            ("RiceRa00", "Rashee Rice", "WR", "KC"),
        ],
    )

    # plays: Rice targeted 3 times, 2 catches for 25 yards and 12 YAC.
    plays = [
        # target, complete, yards, yac, air, epa, cpoe
        ("G1", 1, 2024, 1, "KC", "BUF", 1, 1, 10.0, 5.0, 8.0, 0.2, 1.0, "RiceRa00"),
        ("G1", 2, 2024, 1, "KC", "BUF", 1, 1, 15.0, 7.0, 12.0, 0.3, 2.0, "RiceRa00"),
        ("G1", 3, 2024, 1, "KC", "BUF", 1, 0, 0.0, 0.0, 6.0, -0.1, -1.0, "RiceRa00"),
        # Kelce: 1 target, 1 catch
        ("G1", 4, 2024, 1, "KC", "BUF", 1, 1, 7.0, 2.0, 5.0, 0.1, 0.5, "KelcTr00"),
    ]
    cur.executemany(
        """
        INSERT INTO plays(
            game_id, play_id, season, week, posteam, defteam,
            target, complete_pass, yards_gained, yards_after_catch, air_yards, epa, cpoe, receiver_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        plays,
    )

    # PFR receiving advanced provides routes (needed for YPRR and routes>=targets checks)
    cur.executemany(
        """
        INSERT INTO receiving_advanced(
            player_id, game_id, season, week, team_abbr, targets, receptions, rec_yards, routes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("RiceRa00", "G1", 2024, 1, "KC", 3, 2, 25.0, 12),
            ("KelcTr00", "G1", 2024, 1, "KC", 1, 1, 7.0, 20),
        ],
    )

    # Snap counts (optional, but should be handled)
    cur.executemany(
        """
        INSERT INTO player_game_stats(player_id, game_id, season, week, team_abbr, snaps_offense, snap_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("RiceRa00", "G1", 2024, 1, "KC", 55, 0.85),
            ("KelcTr00", "G1", 2024, 1, "KC", 60, 0.92),
        ],
    )
    conn.commit()


def test_compute_and_validate_happy_path(conn):
    seed_minimal_game(conn)
    compute_all_metrics(conn)

    # No validation issues for seeded data.
    assert run_all_checks(conn) == []


def test_duplicate_play_ids_detected(conn):
    seed_minimal_game(conn)
    # The schema enforces uniqueness via PRIMARY KEY (game_id, play_id),
    # which is stronger than a post-hoc duplicate detector.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO plays(
                game_id, play_id, season, week, posteam, defteam, target, complete_pass, receiver_id
            ) VALUES ('G1', 1, 2024, 1, 'KC', 'BUF', 1, 1, 'RiceRa00')
            """
        )
        conn.commit()


def test_routes_ge_targets_for_wr_te(conn):
    seed_minimal_game(conn)
    compute_all_metrics(conn)
    assert check_routes_ge_targets(conn) == []


def test_yprr_bounds(conn):
    seed_minimal_game(conn)
    compute_all_metrics(conn)
    assert check_yprr_bounds(conn, lo=0.0, hi=30.0) == []


def test_pfr_targets_close_to_pbp(conn):
    seed_minimal_game(conn)
    compute_all_metrics(conn)
    assert check_targets_pfr_vs_pbp(conn, tolerance=2) == []


def test_season_totals_sum(conn):
    seed_minimal_game(conn)
    compute_all_metrics(conn)
    assert check_season_totals_sum_correctly(conn) == []


def test_game_logs_exclude_postseason_by_default(conn):
    cur = conn.cursor()
    cur.executemany("INSERT OR IGNORE INTO teams(team_abbr) VALUES (?)", [("MIN",), ("LA",)])
    # Week 18 regular season, week 19 postseason (nflfastR convention)
    cur.executemany(
        "INSERT INTO games(game_id, season, week, gameday, home_team, away_team) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("G18", 2024, 18, "2025-01-05", "MIN", "LA"),
            ("G19", 2024, 19, "2025-01-13", "LA", "MIN"),
        ],
    )
    pid = "00-0036322"
    cur.execute("INSERT INTO players(player_id, player_name, position, team_abbr) VALUES (?, ?, ?, ?)", (pid, "J.Jefferson", "WR", "MIN"))
    # One receiving play in each game so the gamelog rows exist
    cur.executemany(
        """
        INSERT INTO plays(
            game_id, play_id, season, week, posteam, defteam,
            pass, target, complete_pass, yards_gained, receiver_id
        ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, 1, 10, ?)
        """,
        [
            ("G18", 1, 2024, 18, "MIN", "LA", pid),
            ("G19", 1, 2024, 19, "MIN", "LA", pid),
        ],
    )
    conn.commit()

    rows = queries.get_player_game_logs(conn, pid, 2024)
    assert [r["week"] for r in rows] == [18]

    rows2 = queries.get_player_game_logs(conn, pid, 2024, include_postseason=True)
    assert [r["week"] for r in rows2] == [18, 19]
    assert rows2[-1]["is_postseason"] == 1


