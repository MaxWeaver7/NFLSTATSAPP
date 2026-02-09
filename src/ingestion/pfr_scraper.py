from __future__ import annotations

import csv
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup, Comment

from src.ingestion.pfr_urls import build_pfr_boxscore_url


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PfrSummary:
    games_attempted: int
    games_scraped: int
    rows_player_game_stats: int
    rows_receiving_advanced: int
    rows_rushing_advanced: int


def _coerce_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip()
    if s in {"", "None", "NA", "NaN"}:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def _coerce_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if s in {"", "None", "NA", "NaN"}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _extract_table_html(soup: BeautifulSoup, table_id: str) -> Optional[str]:
    table = soup.find("table", {"id": table_id})
    if table is not None:
        return str(table)

    # PFR commonly wraps tables in HTML comments.
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        if f'id="{table_id}"' in c:
            return str(c)
    return None


def _parse_table(table_html: str) -> list[dict[str, str]]:
    inner_soup = BeautifulSoup(table_html, "html.parser")
    table = inner_soup.find("table")
    if table is None:
        return []
    tbody = table.find("tbody")
    if tbody is None:
        return []

    rows: list[dict[str, str]] = []
    for tr in tbody.find_all("tr"):
        if tr.get("class") and "thead" in tr.get("class", []):
            continue
        row: dict[str, str] = {}
        for cell in tr.find_all(["th", "td"]):
            key = cell.get("data-stat") or ""
            if not key:
                continue
            row[key] = cell.get_text(strip=True)
        if row:
            rows.append(row)
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def scrape_pfr_for_games(
    conn: sqlite3.Connection,
    *,
    cache_dir: str = "data/pfr_cache",
    delay_seconds: float = 2.5,
    enabled: bool = False,
    game_ids: Optional[list[str]] = None,
    max_games: Optional[int] = None,
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
) -> PfrSummary:
    """
    Best-effort PFR scraper.

    - Only scrapes games where `games.pfr_boxscore_url` is populated.
    - Caches raw HTML and parsed CSVs to disk for debugging/reprocessing.
    - Never fabricates data; missing tables are skipped.
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    if not enabled:
        logger.info("PFR scraping disabled (PFR_ENABLE=false).")
        return PfrSummary(0, 0, 0, 0, 0)

    cur = conn.cursor()
    # If URLs aren't populated yet, best-effort generate them from gameday + home_team.
    # (We only fill missing urls; never overwrite.)
    candidates = cur.execute(
        """
        SELECT game_id, gameday, home_team, pfr_boxscore_url
        FROM games
        WHERE pfr_boxscore_url IS NULL OR TRIM(pfr_boxscore_url) = ''
        """
    ).fetchall()
    to_update = []
    for g in candidates:
        info = build_pfr_boxscore_url(gameday_iso=g["gameday"], home_team=g["home_team"])
        if info:
            to_update.append((info.url, g["game_id"]))
    if to_update:
        cur.executemany("UPDATE games SET pfr_boxscore_url = ? WHERE game_id = ? AND (pfr_boxscore_url IS NULL OR TRIM(pfr_boxscore_url)='')", to_update)
        conn.commit()
        logger.info("Populated pfr_boxscore_url for %d games (best effort).", len(to_update))

    where = "WHERE pfr_boxscore_url IS NOT NULL AND TRIM(pfr_boxscore_url) != ''"
    params: list[Any] = []
    if game_ids:
        placeholders = ",".join(["?"] * len(game_ids))
        where += f" AND game_id IN ({placeholders})"
        params.extend(game_ids)

    sql = f"""
        SELECT game_id, season, week, pfr_boxscore_url
        FROM games
        {where}
        ORDER BY season, week
    """
    games = cur.execute(sql, params).fetchall()
    if max_games is not None:
        games = games[: max_games]

    session = requests.Session()
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    attempted = 0
    scraped = 0
    rows_stats = 0
    rows_recv = 0
    rows_rush = 0

    for g in games:
        attempted += 1
        game_id = g["game_id"]
        season = int(g["season"])
        week = int(g["week"])
        url = g["pfr_boxscore_url"]
        logger.info("Scraping PFR game_id=%s url=%s", game_id, url)

        html_path = cache_path / f"{game_id}.html"
        html_text: Optional[str] = None

        # Offline-friendly: if the HTML is already cached (e.g. saved manually from a browser),
        # parse it without making a web request.
        if html_path.exists():
            html_text = html_path.read_text(encoding="utf-8")
            logger.info("Using cached HTML for game_id=%s (%s)", game_id, html_path)
        else:
            try:
                # Seed cookies (some sites behave differently without a landing request)
                session.get("https://www.pro-football-reference.com/", headers=headers, timeout=30)
                resp = session.get(url, headers={**headers, "Referer": "https://www.pro-football-reference.com/"}, timeout=30)
                resp.raise_for_status()
                html_text = resp.text
                html_path.write_text(html_text, encoding="utf-8")
            except Exception as e:
                logger.warning(
                    "PFR request failed game_id=%s err=%s. "
                    "Tip: open the URL in a browser, save page source to %s, and re-run.",
                    game_id,
                    e,
                    html_path,
                )
                continue

        soup = BeautifulSoup(html_text, "html.parser")

        # Snap counts
        snap_html = _extract_table_html(soup, "snap_counts")
        snap_rows = _parse_table(snap_html) if snap_html else []
        parsed_snaps: list[dict[str, Any]] = []
        for r in snap_rows:
            pid = r.get("player")
            if not pid:
                continue
            parsed_snaps.append(
                {
                    "player_id": pid,
                    "game_id": game_id,
                    "season": season,
                    "week": week,
                    "team_abbr": r.get("team"),
                    "snaps_offense": _coerce_int(r.get("offense")),
                    "snap_pct": _coerce_float(r.get("off_pct")),
                }
            )

        if parsed_snaps:
            _write_csv(cache_path / f"{game_id}_snap_counts.csv", parsed_snaps)
            cur.executemany(
                """
                INSERT OR REPLACE INTO player_game_stats(
                    player_id, game_id, season, week, team_abbr, snaps_offense, snap_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r["player_id"],
                        r["game_id"],
                        r["season"],
                        r["week"],
                        r["team_abbr"],
                        r["snaps_offense"],
                        r["snap_pct"],
                    )
                    for r in parsed_snaps
                ],
            )
            rows_stats += len(parsed_snaps)

        # Advanced receiving
        recv_html = _extract_table_html(soup, "receiving_advanced")
        recv_rows = _parse_table(recv_html) if recv_html else []
        parsed_recv: list[dict[str, Any]] = []
        for r in recv_rows:
            pid = r.get("player")
            if not pid:
                continue
            parsed_recv.append(
                {
                    "player_id": pid,
                    "game_id": game_id,
                    "season": season,
                    "week": week,
                    "team_abbr": r.get("team"),
                    "targets": _coerce_int(r.get("targets")),
                    "receptions": _coerce_int(r.get("rec")),
                    "rec_yards": _coerce_float(r.get("yds")),
                    "air_yards": _coerce_float(r.get("air_yds")),
                    "ybc": _coerce_float(r.get("ybc")),
                    "yac": _coerce_float(r.get("yac")),
                    "adot": _coerce_float(r.get("adot")),
                    "drops": _coerce_int(r.get("drops")),
                    "drop_pct": _coerce_float(r.get("drop_pct")),
                    "broken_tackles": _coerce_int(r.get("brk_tkl")),
                    "routes": _coerce_int(r.get("routes")),
                }
            )

        if parsed_recv:
            _write_csv(cache_path / f"{game_id}_receiving_advanced.csv", parsed_recv)
            cur.executemany(
                """
                INSERT OR REPLACE INTO receiving_advanced(
                    player_id, game_id, season, week, team_abbr,
                    targets, receptions, rec_yards, air_yards, ybc, yac, adot,
                    drops, drop_pct, broken_tackles, routes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r["player_id"],
                        r["game_id"],
                        r["season"],
                        r["week"],
                        r["team_abbr"],
                        r["targets"],
                        r["receptions"],
                        r["rec_yards"],
                        r["air_yards"],
                        r["ybc"],
                        r["yac"],
                        r["adot"],
                        r["drops"],
                        r["drop_pct"],
                        r["broken_tackles"],
                        r["routes"],
                    )
                    for r in parsed_recv
                ],
            )
            rows_recv += len(parsed_recv)

        # Advanced rushing
        rush_html = _extract_table_html(soup, "rushing_advanced")
        rush_rows = _parse_table(rush_html) if rush_html else []
        parsed_rush: list[dict[str, Any]] = []
        for r in rush_rows:
            pid = r.get("player")
            if not pid:
                continue
            parsed_rush.append(
                {
                    "player_id": pid,
                    "game_id": game_id,
                    "season": season,
                    "week": week,
                    "team_abbr": r.get("team"),
                    "attempts": _coerce_int(r.get("att")),
                    "rush_yards": _coerce_float(r.get("yds")),
                    "ybc": _coerce_float(r.get("ybc")),
                    "yac": _coerce_float(r.get("yac")),
                    "broken_tackles": _coerce_int(r.get("brk_tkl")),
                }
            )

        if parsed_rush:
            _write_csv(cache_path / f"{game_id}_rushing_advanced.csv", parsed_rush)
            cur.executemany(
                """
                INSERT OR REPLACE INTO rushing_advanced(
                    player_id, game_id, season, week, team_abbr,
                    attempts, rush_yards, ybc, yac, broken_tackles
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r["player_id"],
                        r["game_id"],
                        r["season"],
                        r["week"],
                        r["team_abbr"],
                        r["attempts"],
                        r["rush_yards"],
                        r["ybc"],
                        r["yac"],
                        r["broken_tackles"],
                    )
                    for r in parsed_rush
                ],
            )
            rows_rush += len(parsed_rush)

        conn.commit()
        scraped += 1

        time.sleep(delay_seconds)

    logger.info(
        "PFR scraping done: attempted=%s scraped=%s snap_rows=%s recv_rows=%s rush_rows=%s",
        attempted,
        scraped,
        rows_stats,
        rows_recv,
        rows_rush,
    )
    return PfrSummary(attempted, scraped, rows_stats, rows_recv, rows_rush)


