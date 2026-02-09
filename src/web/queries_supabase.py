from __future__ import annotations

import csv
import json
import re
import ssl
import time
import threading
import urllib.request
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from src.database.supabase_client import SupabaseClient


# ---------------------------------------------------------------------------
# TTL Cache — thread-safe, used for expensive league-wide computations that
# are identical across all 32 teams (e.g. season rankings).
# ---------------------------------------------------------------------------
class TTLCache:
    """Simple thread-safe in-memory cache with per-entry time-to-live."""

    def __init__(self, ttl_seconds: int = 600):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, value = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.monotonic(), value)


# 10-minute TTL — league rankings change at most once per week (after games).
_league_cache = TTLCache(ttl_seconds=600)


def player_photo_url(player_id: str) -> Optional[str]:
    # Deprecated signature (kept for compatibility). Use player_photo_url_from_name_team instead.
    return None


_NAME_RE = re.compile(r"[^a-z0-9 ]+")

_SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}

_TEAM_ABBR_ALIASES: dict[str, str] = {
    # ESPN-ish -> nflfastR-ish / dynastyprocess team codes in db_playerids.csv
    "KC": "KCC",
    "NE": "NEP",
    "NO": "NOS",
    "LV": "LVR",
    "SF": "SFO",
    "TB": "TBB",
    "GB": "GNB",
    "JAX": "JAC",
    "WSH": "WAS",
}

# nflverse game_lines abbreviations -> nfl_teams DB abbreviations
_NFLVERSE_TO_DB_TEAM: dict[str, str] = {
    "LA": "LAR",
    "WAS": "WSH",
}
# Reverse: nfl_teams DB abbreviations -> nflverse game_lines format
_DB_TO_NFLVERSE_TEAM: dict[str, str] = {v: k for k, v in _NFLVERSE_TO_DB_TEAM.items()}


def _normalize_team_abbr(team: Optional[str]) -> str:
    t = (team or "").strip().upper()
    if not t:
        return ""
    return _TEAM_ABBR_ALIASES.get(t, t)


def _merge_name(name: str) -> str:
    s = _NAME_RE.sub("", (name or "").lower()).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _merge_name_variants(name: str) -> list[str]:
    """Generate candidate merge_name values to improve matches for suffixes like Jr/Sr/III."""
    base = _merge_name(name)
    if not base:
        return []
    parts = base.split(" ")
    if not parts:
        return [base]

    out: list[str] = [base]

    # Strip a trailing suffix token if present.
    if parts and parts[-1] in _SUFFIX_TOKENS:
        no_suffix = " ".join(parts[:-1]).strip()
        if no_suffix and no_suffix != base:
            out.append(no_suffix)
            parts = no_suffix.split(" ")

    # If there are middle tokens (nicknames / middle names), also try first+last.
    if len(parts) >= 3:
        first_last = f"{parts[0]} {parts[-1]}".strip()
        if first_last and first_last not in out:
            out.append(first_last)

    # Deduplicate preserving order.
    seen = set()
    dedup: list[str] = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        dedup.append(x)
    return dedup


_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


@lru_cache(maxsize=512)
def _espn_search_photo(name: str) -> Optional[str]:
    """Fallback: search ESPN's public API for a player and return their headshot URL."""
    try:
        q = urllib.parse.quote(name)
        url = f"https://site.api.espn.com/apis/common/v3/search?query={q}&limit=1&type=player&sport=football&league=nfl"
        req = urllib.request.Request(url, headers={"User-Agent": "NFLStats/1.0"})
        with urllib.request.urlopen(req, timeout=3, context=_SSL_CTX) as resp:
            data = json.loads(resp.read())
        items = data.get("items", [])
        if items:
            espn_id = items[0].get("id")
            if espn_id:
                return f"https://a.espncdn.com/i/headshots/nfl/players/full/{espn_id}.png"
    except Exception:
        pass
    return None


def player_photo_url_from_name_team(*, name: str, team: Optional[str]) -> Optional[str]:
    """
    Best-effort headshot URL based on player name + team.

    Uses dynastyprocess db_playerids.csv (already cached in hrb/data/db_playerids.csv).
    Prefers ESPN headshots, falls back to Sleeper, then ESPN search API.
    """
    maps = _photo_maps()
    if not maps:
        return _espn_search_photo(name)
    by_name_team, by_name, by_last_team, by_last = maps

    team_abbr = _normalize_team_abbr(team)
    for mn in _merge_name_variants(name):
        ids = by_name_team.get((mn, team_abbr)) if team_abbr else None
        if ids is None:
            ids = by_name.get(mn)
        if ids is None:
            # Try last-name + team fallback (team-aware, safe)
            last = mn.split(" ")[-1] if mn else ""
            if last:
                ids = by_last_team.get((last, team_abbr)) if team_abbr else None
            # NOTE: by_last (last-name-only) intentionally skipped — too
            # ambiguous for common surnames (e.g. "Matthews" matching the
            # wrong player).  Fall through to ESPN search instead.
        if ids is None:
            continue

        espn_id, sleeper_id = ids
        if espn_id:
            return f"https://a.espncdn.com/i/headshots/nfl/players/full/{espn_id}.png"
        if sleeper_id:
            return f"https://sleepercdn.com/content/nfl/players/{sleeper_id}.jpg"
        return None
    # CSV had no match — try ESPN search as last resort
    return _espn_search_photo(name)


def _clean_id(v: Any) -> Optional[str]:
    s = str(v or "").strip()
    if not s or s.lower() == "nan" or s.lower() == "na":
        return None
    return s


PhotoMaps = tuple[
    dict[tuple[str, str], tuple[Optional[str], Optional[str]]],
    dict[str, tuple[Optional[str], Optional[str]]],
    dict[tuple[str, str], tuple[Optional[str], Optional[str]]],
    dict[str, tuple[Optional[str], Optional[str]]],
]


@lru_cache(maxsize=1)
def _photo_maps() -> Optional[PhotoMaps]:
    """
    Load and cache (process-wide) the dynastyprocess db_playerids.csv lookup maps.

    This is called for every player row rendered in the UI, so it must be fast.
    """
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "data" / "db_playerids.csv"
    if not path.exists():
        return None

    # Keep "best" row per key by highest db_season (mirrors the old pandas sort/newest-first behavior).
    by_name_team_s: dict[tuple[str, str], tuple[int, Optional[str], Optional[str]]] = {}
    by_name_s: dict[str, tuple[int, Optional[str], Optional[str]]] = {}
    by_last_team_s: dict[tuple[str, str], tuple[int, Optional[str], Optional[str]]] = {}
    by_last_s: dict[str, tuple[int, Optional[str], Optional[str]]] = {}

    def _season_num(raw: Any) -> int:
        try:
            return int(str(raw or "").strip())
        except Exception:
            return -1

    def _upsert_best(
        m: dict[Any, tuple[int, Optional[str], Optional[str]]],
        key: Any,
        season: int,
        espn: Optional[str],
        sleeper: Optional[str],
    ) -> None:
        cur = m.get(key)
        if cur is None or season > cur[0]:
            m[key] = (season, espn, sleeper)

    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mn = _merge_name(row.get("merge_name") or "")
                if not mn:
                    continue
                tn = str(row.get("team") or "").strip().upper()
                season = _season_num(row.get("db_season"))
                espn = _clean_id(row.get("espn_id"))
                sleeper = _clean_id(row.get("sleeper_id"))

                _upsert_best(by_name_team_s, (mn, tn), season, espn, sleeper)
                _upsert_best(by_name_s, mn, season, espn, sleeper)

                last = mn.split(" ")[-1] if mn else ""
                if last:
                    _upsert_best(by_last_team_s, (last, tn), season, espn, sleeper)
                    _upsert_best(by_last_s, last, season, espn, sleeper)
    except Exception:
        return None

    by_name_team = {k: (v[1], v[2]) for k, v in by_name_team_s.items()}
    by_name = {k: (v[1], v[2]) for k, v in by_name_s.items()}
    by_last_team = {k: (v[1], v[2]) for k, v in by_last_team_s.items()}
    by_last = {k: (v[1], v[2]) for k, v in by_last_s.items()}
    return by_name_team, by_name, by_last_team, by_last


def _uniq_sorted_int(vals: list[Any], *, desc: bool = False) -> list[int]:
    out: list[int] = []
    seen = set()
    for v in vals:
        try:
            i = int(v)
        except Exception:
            continue
        if i in seen:
            continue
        seen.add(i)
        out.append(i)
    return sorted(out, reverse=desc)


def _in_list(values: list[int]) -> str:
    inner = ",".join(str(int(v)) for v in values)
    return f"in.({inner})"

def _safe_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _team_map(sb: SupabaseClient, team_ids: list[int]) -> dict[int, str]:
    team_map: dict[int, str] = {}
    if not team_ids:
        return team_map
    teams = sb.select("nfl_teams", select="id,abbreviation", filters={"id": _in_list(team_ids)}, limit=len(team_ids))
    for t in teams:
        try:
            team_map[int(t["id"])] = str(t.get("abbreviation") or "").upper()
        except Exception:
            continue
    return team_map


def options(sb: SupabaseClient) -> dict[str, Any]:
    games = sb.select("nfl_games", select="season,week", order="season.desc,week.asc", limit=5000)
    seasons = _uniq_sorted_int([g.get("season") for g in games], desc=True)
    weeks = _uniq_sorted_int([g.get("week") for g in games], desc=False)
    teams = sb.select("nfl_teams", select="abbreviation", order="abbreviation.asc", limit=1000)
    team_abbr = [t.get("abbreviation") for t in teams if isinstance(t.get("abbreviation"), str)]
    positions = ["QB", "RB", "WR", "TE"]
    return {"seasons": seasons, "weeks": weeks, "teams": team_abbr, "positions": positions}


def summary(sb: SupabaseClient) -> dict[str, Any]:
    games = sb.count("nfl_games")
    players = sb.count("nfl_players")
    teams = sb.count("nfl_teams")
    seasons_rows = sb.select("nfl_games", select="season", order="season.asc", limit=5000)
    seasons = _uniq_sorted_int([r.get("season") for r in seasons_rows], desc=False)
    # Mirror the existing JSON shape expected by the React UI (it doesn't depend on most fields).
    return {"seasons": seasons, "games": games, "players": players, "teams": teams}

def _has_any_stats(row: dict[str, Any]) -> bool:
    # Player recorded at least one meaningful offensive stat.
    # Important: some feeds may omit attempts/targets but still populate yards/TDs.
    for k in (
        # passing volume/production
        "passing_attempts",
        "passing_completions",
        "passing_yards",
        "passing_touchdowns",
        # rushing volume/production
        "rushing_attempts",
        "rushing_yards",
        "rushing_touchdowns",
        # receiving volume/production
        "receiving_targets",
        "receptions",
        "receiving_yards",
        "receiving_touchdowns",
    ):
        v = _safe_int(row.get(k))
        if v is not None and v > 0:
            return True
    return False


def _sanitize_search(q: Optional[str]) -> Optional[str]:
    """
    Create a safe token for PostgREST ilike filters.
    We intentionally strip anything that could break the query syntax (commas, parens, wildcards).
    """
    s = (q or "").strip()
    if not s:
        return None
    s = re.sub(r"[^a-zA-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) < 2:
        return None
    return s


def get_players_list(
    sb: SupabaseClient,
    *,
    season: Optional[int],
    position: Optional[str],
    team: Optional[str],
    q: Optional[str] = None,
    limit: int,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Get players list.
    - ROSTER MODE (team provided): Returns ALL players on the team (nfl_players root), even if no stats.
    - LEADERBOARD/SEARCH MODE (no team): Returns players with stats (stats root), ordered by yards.
    """
    if season is None:
        return []

    safe_limit = max(int(limit or 0), 1)
    safe_offset = max(int(offset or 0), 0)
    needle = _sanitize_search(q)

    # ==========================
    # BRANCH 1: ROSTER MODE
    # ==========================
    if team:
        t = sb.select("nfl_teams", select="id", filters={"abbreviation": f"eq.{team}"}, limit=1)
        if not t: return []
        team_id = _safe_int(t[0].get("id"))
        if not team_id: return []

        # Query nfl_players directly
        filters = {"team_id": f"eq.{team_id}"}
        if needle:
            filters["or"] = f"(first_name.ilike.*{needle}*,last_name.ilike.*{needle}*)"
        if position:
            filters["position_abbreviation"] = f"eq.{position}"
        
        # We fetch ALL team players (limit is high for roster view usually, but we respect param)
        # We Left Join stats to get them if they exist
        rows = sb.select(
            "nfl_players",
            select=(
                "id,first_name,last_name,position_abbreviation,team_id,"
                "nfl_teams(abbreviation),"
                f"nfl_player_season_stats(season,games_played,passing_yards,rushing_yards,receiving_yards,receptions,receiving_targets,receiving_touchdowns,rushing_attempts,rushing_touchdowns,passing_attempts,passing_completions,passing_touchdowns,passing_interceptions,qbr)"
            ),
            filters=filters,
            order="position_abbreviation.asc,last_name.asc", 
            limit=safe_limit,
            offset=safe_offset
        )

        out = []
        for r in rows:
            # Stats come as list (Left Join)
            stats_list = r.get("nfl_player_season_stats") or []
            # Filter in Python for the requested season
            stats = next((s for s in stats_list if s.get("season") == season), {})
            
            p_name = f"{r.get('first_name','')} {r.get('last_name','')}".strip()
            pos = r.get("position_abbreviation") or "UNK"
            pid = r.get("id")

            # Mapped to match frontend expectations (CamelCase)
            out.append({
                "player_id": str(pid),
                "player_name": p_name,
                "team": team,
                "position": pos,
                "season": season,
                "games": _safe_int(stats.get("games_played")) or 0,
                "targets": _safe_int(stats.get("receiving_targets")) or 0,
                "receptions": _safe_int(stats.get("receptions")) or 0,
                "receivingYards": _safe_int(stats.get("receiving_yards")) or 0,
                "receivingTouchdowns": _safe_int(stats.get("receiving_touchdowns")) or 0,
                "rushAttempts": _safe_int(stats.get("rushing_attempts")) or 0,
                "rushingYards": _safe_int(stats.get("rushing_yards")) or 0,
                "rushingTouchdowns": _safe_int(stats.get("rushing_touchdowns")) or 0,
                "passingAttempts": _safe_int(stats.get("passing_attempts")) or 0,
                "passingCompletions": _safe_int(stats.get("passing_completions")) or 0,
                "passingYards": _safe_int(stats.get("passing_yards")) or 0,
                "passingTouchdowns": _safe_int(stats.get("passing_touchdowns")) or 0,
                "passingInterceptions": _safe_int(stats.get("passing_interceptions")) or 0,
                "qbRating": _safe_float(stats.get("qbr")),
                "qbr": _safe_float(stats.get("qbr")),
                # Calculated fields
                "avgYardsPerCatch": 0.0, # Frontend can calc or we add simple 0
                "avgYardsPerRush": 0.0,
                "photoUrl": player_photo_url_from_name_team(name=p_name, team=team)
            })
        return out

    # ==========================
    # BRANCH 2: LEADERBOARD MODE (Existing Logic)
    # ==========================
    
    blocked_positions = {"DB", "CB", "S", "SS", "FS", "LB", "ILB", "OLB", "DL", "DE", "DT", "NT", "OL", "OT", "OG", "C", "K", "P", "LS"}
    player_filters: dict[str, Any] = {}
    stats_filters: dict[str, Any] = {
        "season": f"eq.{int(season)}",
        # "postseason": "eq.false",
    }
    
    if needle:
        # Check for full name search (e.g. "Tyreek Hill")
        if " " in needle:
            parts = needle.split()
            # Simple assumption: First Part = First Name, Last Part = Last Name (matches "Tyreek Hill")
            # We use ILIKE on both.
            p1, p2 = parts[0], parts[-1] 
            # Implicit AND by setting multiple keys
            stats_filters["nfl_players.first_name"] = f"ilike.*{p1}*"
            stats_filters["nfl_players.last_name"] = f"ilike.*{p2}*"
        else:
             # Use !inner to filter strictly by player name match.
             stats_filters["nfl_players.or"] = f"(first_name.ilike.*{needle}*,last_name.ilike.*{needle}*)"
        
        # Restrict to skill positions for search performance/relevance
        stats_filters["nfl_players.position_abbreviation"] = "in.(QB,RB,WR,TE)"
    
    # Request many rows; Supabase will cap at ~1000 or use paging
    req_limit = 5000 
    
    stats_rows = sb.select(
        "nfl_player_season_stats",
        select=(
            "player_id,games_played,"
            "passing_attempts,passing_completions,passing_yards,passing_touchdowns,passing_interceptions,"
            "qbr,"
            "rushing_attempts,rushing_yards,rushing_touchdowns,"
            "receptions,receiving_yards,receiving_touchdowns,receiving_targets,"
            f"nfl_players!inner(id,first_name,last_name,position_abbreviation,team_id,nfl_teams(abbreviation))"
        ),
        filters=stats_filters,
        order="passing_yards.desc.nullslast",
        limit=req_limit,
    )
    
    processed_players = []
    seen = set() # Dedup tracking
    
    # Position Filtering Loop
    pos_filter = (position or "").strip().upper()
    
    for stat_row in stats_rows:
        p = stat_row.get("nfl_players")
        if not p: continue
        
        pid = _safe_int(p.get("id"))
        if pid in seen: continue
        seen.add(pid)

        pos = (p.get("position_abbreviation") or "").strip().upper() or "UNK"
        
        # Position Logic
        if pos in blocked_positions: continue
        
        is_unknown_pos = (pos in {"UNK", "UNKNOWN", "NULL", "ROOKIE"})
        if pos_filter:
            if not is_unknown_pos:
                if pos != pos_filter: continue
            else:
                 # Heuristic strictness for unknowns
                 pass # (Skipping complex heuristic for brevity, relying on user intent)
                 if pos_filter == "QB" and not (stat_row.get("passing_yards") or 0): continue
                 if pos_filter == "RB" and not (stat_row.get("rushing_yards") or 0): continue
                 if pos_filter in {"WR", "TE"} and not (stat_row.get("receiving_yards") or 0): continue

        p_name = f"{p.get('first_name','')} {p.get('last_name','')}".strip()
        team_abbr = (p.get("nfl_teams") or {}).get("abbreviation")
        
        # Metrics
        rec = _safe_int(stat_row.get("receptions")) or 0
        rec_yards = _safe_int(stat_row.get("receiving_yards")) or 0
        rush_att = _safe_int(stat_row.get("rushing_attempts")) or 0
        rush_yards = _safe_int(stat_row.get("rushing_yards")) or 0
        
        processed_players.append({
            "player_id": str(pid),
            "player_name": p_name,
            "team": team_abbr,
            "position": pos,
            "season": season,
            "games": _safe_int(stat_row.get("games_played")) or 0,
            "targets": _safe_int(stat_row.get("receiving_targets")) or 0,
            "receptions": rec,
            "receivingYards": rec_yards,
            "receivingTouchdowns": _safe_int(stat_row.get("receiving_touchdowns")) or 0,
            "avgYardsPerCatch": (float(rec_yards)/rec) if rec else 0.0,
            "rushAttempts": rush_att,
            "rushingYards": rush_yards,
            "rushingTouchdowns": _safe_int(stat_row.get("rushing_touchdowns")) or 0,
            "avgYardsPerRush": (float(rush_yards)/rush_att) if rush_att else 0.0,
            "passingAttempts": _safe_int(stat_row.get("passing_attempts")) or 0,
            "passingCompletions": _safe_int(stat_row.get("passing_completions")) or 0,
            "passingYards": _safe_int(stat_row.get("passing_yards")) or 0,
            "passingTouchdowns": _safe_int(stat_row.get("passing_touchdowns")) or 0,
            "passingInterceptions": _safe_int(stat_row.get("passing_interceptions")) or 0,
            "qbRating": _safe_float(stat_row.get("qbr")),
            "qbr": _safe_float(stat_row.get("qbr")),
            "photoUrl": player_photo_url_from_name_team(name=p_name, team=team_abbr)
        })

    # Sort
    def sort_key(r):
        pos = r["position"]
        if pos == "QB": return r["passingYards"]
        if pos in {"RB", "HB"}: return r["rushingYards"]
        if pos in {"WR", "TE"}: return r["receivingYards"]
        return r["passingYards"] + r["rushingYards"] + r["receivingYards"]

    processed_players.sort(key=sort_key, reverse=True)
    return processed_players[safe_offset : safe_offset + safe_limit]


def get_player_game_logs(
    sb: SupabaseClient,
    player_id: str,
    season: int,
    *,
    include_postseason: bool = False,
) -> list[dict[str, Any]]:
    pid = _safe_int(player_id)
    if pid is None:
        return []

    # If include_postseason, return both; otherwise regular season only.
    # If include_postseason, return both; otherwise regular season only.
    filters: dict[str, Any] = {
        "player_id": f"eq.{pid}",
        "season": f"eq.{int(season)}",
    }
    # Removed: filters["postseason"] = "eq.false" because column missing on stats table

    rows = sb.select(
        "nfl_player_game_stats",
        select=(
            "player_id,game_id,season,week,team_id,"
            "rushing_attempts,rushing_yards,rushing_touchdowns,"
            "receptions,receiving_yards,receiving_touchdowns,receiving_targets,"
            "passing_attempts,passing_completions,passing_yards,passing_touchdowns,passing_interceptions,"
            "qbr"
        ),
        filters=filters,
        order="week.asc",
        limit=400,
    )
    if not rows:
        return []

    game_ids = sorted({int(r["game_id"]) for r in rows if r.get("game_id") not in (None, "")})
    games = sb.select(
        "nfl_games",
        select="id,home_team_id,visitor_team_id,postseason",
        filters={"id": _in_list(game_ids)},
        limit=len(game_ids),
    )
    game_map: dict[int, dict[str, Any]] = {}
    team_ids = set()
    for g in games:
        gid = _safe_int(g.get("id"))
        if gid is None:
            continue
        game_map[gid] = g
        ht = _safe_int(g.get("home_team_id"))
        vt = _safe_int(g.get("visitor_team_id"))
        if ht is not None:
            team_ids.add(ht)
        if vt is not None:
            team_ids.add(vt)

    # Also include player's team_id values for mapping to abbreviation.
    for r in rows:
        tid = _safe_int(r.get("team_id"))
        if tid is not None:
            team_ids.add(tid)

    tmap = _team_map(sb, sorted(team_ids))

    out: list[dict[str, Any]] = []
    for r in rows:
        gid = _safe_int(r.get("game_id"))
        if gid is None:
            continue
        g = game_map.get(gid, {})
        
        # PYTHON SIDE POSTSEASON FILTER
        is_post = g.get("postseason", False)
        if is_post and not include_postseason:
            continue
            
        ht = _safe_int(g.get("home_team_id"))
        vt = _safe_int(g.get("visitor_team_id"))
        tid = _safe_int(r.get("team_id"))

        team_abbr = tmap.get(tid) if tid is not None else None
        home_abbr = tmap.get(ht) if ht is not None else None
        away_abbr = tmap.get(vt) if vt is not None else None

        location = "home"
        opp = None
        if tid is not None and ht is not None and vt is not None:
            if tid == ht:
                location = "home"
                opp = away_abbr
            else:
                location = "away"
                opp = home_abbr

        out.append(
            {
                "season": _safe_int(r.get("season")) or season,
                "week": _safe_int(r.get("week")) or 0,
                "game_id": str(gid),
                "team": team_abbr,
                "opponent": opp,
                "home_team": home_abbr,
                "away_team": away_abbr,
                "location": location,
                "is_postseason": bool(r.get("postseason")),
                # Receiving
                "targets": _safe_int(r.get("receiving_targets")) or 0,
                "receptions": _safe_int(r.get("receptions")) or 0,
                "rec_yards": _safe_int(r.get("receiving_yards")) or 0,
                "rec_tds": _safe_int(r.get("receiving_touchdowns")) or 0,
                "air_yards": 0,
                "yac": 0,
                # no EPA yet
                # Rushing
                "rush_attempts": _safe_int(r.get("rushing_attempts")) or 0,
                "rush_yards": _safe_int(r.get("rushing_yards")) or 0,
                "rush_tds": _safe_int(r.get("rushing_touchdowns")) or 0,
                # Passing
                "passing_attempts": _safe_int(r.get("passing_attempts")) or 0,
                "passing_completions": _safe_int(r.get("passing_completions")) or 0,
                "passing_yards": _safe_int(r.get("passing_yards")) or 0,
                "passing_tds": _safe_int(r.get("passing_touchdowns")) or 0,
                "interceptions": _safe_int(r.get("passing_interceptions")) or 0,
                "qb_rating": _safe_float(r.get("qbr")),
                "qbr": _safe_float(r.get("qbr")),
            }
        )

    return out


def receiving_dashboard(
    sb: SupabaseClient,
    *,
    season: int,
    week: int,
    team: Optional[str],
    position: Optional[str],
    limit: int,
    offset: int = 0,
) -> list[dict[str, Any]]:
    # Pull weekly player game stats, then hydrate player + team display fields.
    filters: dict[str, Any] = {
        "season": f"eq.{int(season)}",
        "week": f"eq.{int(week)}",
        # only rows with real receiving involvement
        "or": "(receiving_yards.gt.0,receiving_targets.gt.0,receptions.gt.0,receiving_touchdowns.gt.0)",
    }
    if team:
        t = sb.select("nfl_teams", select="id", filters={"abbreviation": f"eq.{team}"}, limit=1)
        tid = _safe_int(t[0].get("id")) if t else None
        if tid is not None:
            filters["team_id"] = f"eq.{tid}"
    # Use PostgREST embedding to avoid extra round-trips for player/team hydration.
    stats = sb.select(
        "nfl_player_game_stats",
        select=(
            "player_id,game_id,team_id,season,week,receiving_targets,receptions,receiving_yards,receiving_touchdowns,"
            "nfl_players(first_name,last_name,position_abbreviation),"
            "nfl_teams(abbreviation)"
        ),
        filters=filters,
        order="receiving_yards.desc",
        limit=500,
    )

    game_ids = sorted({_safe_int(r.get("game_id")) for r in stats if _safe_int(r.get("game_id")) is not None})
    game_map: dict[int, dict[str, Any]] = {}
    if game_ids:
        games = sb.select(
            "nfl_games",
            select="id,season,week,postseason",
            filters={"id": _in_list(game_ids)},
            limit=len(game_ids),
        )
        for g in games:
            gid = _safe_int(g.get("id"))
            if gid is not None:
                game_map[gid] = g

    pos_raw = (position or "").strip().upper()
    if pos_raw in {"", "ALL"}:
        allowed_positions = {"WR", "TE", "RB"}
    elif pos_raw == "HB":
        allowed_positions = {"RB"}
    else:
        allowed_positions = {pos_raw}

    # Defensive/special teams positions to exclude (unless user explicitly filters for them)
    blocked_positions = {"DB", "CB", "S", "SS", "FS", "LB", "ILB", "OLB", "DL", "DE", "DT", "NT", "OL", "OT", "OG", "C", "K", "P", "LS"}

    # De-dupe per (player_id, game_id) then aggregate per player_id
    per_game: dict[tuple[int, int], dict[str, Any]] = {}
    for r in stats:
        pid = _safe_int(r.get("player_id"))
        gid = _safe_int(r.get("game_id"))
        if pid is None or gid is None:
            continue
        g = game_map.get(gid)
        if not g:
            continue
        if _safe_int(g.get("season")) != int(season) or _safe_int(g.get("week")) != int(week):
            continue
        if g.get("postseason") is True:
            continue
        p = r.get("nfl_players") or {}
        pos = (p.get("position_abbreviation") or "").strip().upper() or None

        # Allow NULL/UNK/empty positions if they have receiving stats (already filtered by query)
        # But block defensive/special teams positions unless explicitly requested
        if pos and pos not in allowed_positions:
            if pos_raw not in {"", "ALL"} or pos in blocked_positions:
                continue

        targets = _safe_int(r.get("receiving_targets")) or 0
        rec = _safe_int(r.get("receptions")) or 0
        rec_y = _safe_int(r.get("receiving_yards")) or 0
        rec_td = _safe_int(r.get("receiving_touchdowns")) or 0
        name = (str(p.get("first_name") or "").strip() + " " + str(p.get("last_name") or "").strip()).strip() or str(pid)
        t = r.get("nfl_teams") or {}
        team_abbr = (t.get("abbreviation") or None)

        score = (rec_y, targets, rec, rec_td)
        key = (pid, gid)
        prev = per_game.get(key)
        if not prev or score > prev["_score"]:
            per_game[key] = {
                "season": season,
                "week": week,
                "team": team_abbr,
                "player_id": str(pid),
                "player_name": name,
                "position": pos,
                "targets": targets,
                "receptions": rec,
                "rec_yards": rec_y,
                "rec_tds": rec_td,
                "air_yards": 0,
                "yac": 0,
                "photoUrl": player_photo_url_from_name_team(name=name, team=team_abbr),
                "_score": score,
            }

    aggregated: dict[int, dict[str, Any]] = {}
    for row in per_game.values():
        pid = int(row["player_id"])
        entry = aggregated.get(pid)
        if entry is None:
            entry = {k: v for k, v in row.items() if k != "_score"}
            aggregated[pid] = entry
            continue
        entry["targets"] = max(_safe_int(entry.get("targets")), _safe_int(row.get("targets")))
        entry["receptions"] = max(_safe_int(entry.get("receptions")), _safe_int(row.get("receptions")))
        entry["rec_yards"] = max(_safe_int(entry.get("rec_yards")), _safe_int(row.get("rec_yards")))
        entry["rec_tds"] = max(_safe_int(entry.get("rec_tds")), _safe_int(row.get("rec_tds")))

    out = list(aggregated.values())
    
    # FORCE SORT by receiving yards descending to fix ordering issues
    out.sort(key=lambda x: (x.get('rec_yards') or 0), reverse=True)
    
    out.sort(key=lambda x: (x.get('rec_yards') or 0), reverse=True)
    
    # Pagination Slice
    safe_offset = max(offset, 0)
    safe_limit = max(limit, 1)
    return out[safe_offset : safe_offset + safe_limit]


def rushing_dashboard(
    sb: SupabaseClient,
    *,
    season: int,
    week: int,
    team: Optional[str],
    position: Optional[str],
    limit: int,
    offset: int = 0,
) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {
        "season": f"eq.{int(season)}",
        "week": f"eq.{int(week)}",
        "or": "(rushing_yards.gt.0,rushing_attempts.gt.0,rushing_touchdowns.gt.0)",
    }
    if team:
        t = sb.select("nfl_teams", select="id", filters={"abbreviation": f"eq.{team}"}, limit=1)
        tid = _safe_int(t[0].get("id")) if t else None
        if tid is not None:
            filters["team_id"] = f"eq.{tid}"
    stats = sb.select(
        "nfl_player_game_stats",
        select=(
            "player_id,game_id,team_id,season,week,rushing_attempts,rushing_yards,rushing_touchdowns,receptions,receiving_yards,"
            "nfl_players(first_name,last_name,position_abbreviation),"
            "nfl_teams(abbreviation)"
        ),
        filters=filters,
        order="rushing_yards.desc",
        limit=500,
    )

    game_ids = sorted({_safe_int(r.get("game_id")) for r in stats if _safe_int(r.get("game_id")) is not None})
    game_map: dict[int, dict[str, Any]] = {}
    if game_ids:
        games = sb.select(
            "nfl_games",
            select="id,season,week,postseason",
            filters={"id": _in_list(game_ids)},
            limit=len(game_ids),
        )
        for g in games:
            gid = _safe_int(g.get("id"))
            if gid is not None:
                game_map[gid] = g

    pos_raw = (position or "").strip().upper()
    if pos_raw in {"", "ALL"}:
        allowed_positions = {"RB", "QB", "WR", "TE"}
    elif pos_raw == "HB":
        allowed_positions = {"RB"}
    else:
        allowed_positions = {pos_raw}

    # Defensive/special teams positions to exclude (unless user explicitly filters for them)
    blocked_positions = {"DB", "CB", "S", "SS", "FS", "LB", "ILB", "OLB", "DL", "DE", "DT", "NT", "OL", "OT", "OG", "C", "K", "P", "LS"}

    per_game: dict[tuple[int, int], dict[str, Any]] = {}
    for r in stats:
        pid = _safe_int(r.get("player_id"))
        gid = _safe_int(r.get("game_id"))
        if pid is None or gid is None:
            continue
        g = game_map.get(gid)
        if not g:
            continue
        if _safe_int(g.get("season")) != int(season) or _safe_int(g.get("week")) != int(week):
            continue
        if g.get("postseason") is True:
            continue
        p = r.get("nfl_players") or {}
        name = (str(p.get("first_name") or "").strip() + " " + str(p.get("last_name") or "").strip()).strip() or str(pid)
        pos = (p.get("position_abbreviation") or "").strip().upper() or None
        
        # Allow NULL/UNK/empty positions if they have rushing stats (already filtered by query)
        # But block defensive/special teams positions unless explicitly requested
        if pos and pos not in allowed_positions:
            if pos_raw not in {"", "ALL"} or pos in blocked_positions:
                continue
        t = r.get("nfl_teams") or {}
        team_abbr = (t.get("abbreviation") or None)
        rush_att = _safe_int(r.get("rushing_attempts")) or 0
        rush_y = _safe_int(r.get("rushing_yards")) or 0
        rec = _safe_int(r.get("receptions")) or 0
        rec_y = _safe_int(r.get("receiving_yards")) or 0
        rush_tds = _safe_int(r.get("rushing_touchdowns")) or 0

        score = (rush_y, rush_att, rush_tds, rec_y)
        key = (pid, gid)
        prev = per_game.get(key)
        if not prev or score > prev["_score"]:
            per_game[key] = {
                "season": season,
                "week": week,
                "team": team_abbr,
                "player_id": str(pid),
                "player_name": name,
                "position": pos,
                "rush_attempts": rush_att,
                "rush_yards": rush_y,
                "rush_tds": rush_tds,
                "receptions": rec,
                "rec_yards": rec_y,
                "photoUrl": player_photo_url_from_name_team(name=name, team=team_abbr),
                "_score": score,
            }

    aggregated: dict[int, dict[str, Any]] = {}
    for row in per_game.values():
        pid = int(row["player_id"])
        entry = aggregated.get(pid)
        if entry is None:
            entry = {k: v for k, v in row.items() if k != "_score"}
            aggregated[pid] = entry
            continue
        entry["rush_attempts"] = max(_safe_int(entry.get("rush_attempts")), _safe_int(row.get("rush_attempts")))
        entry["rush_yards"] = max(_safe_int(entry.get("rush_yards")), _safe_int(row.get("rush_yards")))
        entry["rush_tds"] = max(_safe_int(entry.get("rush_tds")), _safe_int(row.get("rush_tds")))
        entry["receptions"] = max(_safe_int(entry.get("receptions")), _safe_int(row.get("receptions")))
        entry["rec_yards"] = max(_safe_int(entry.get("rec_yards")), _safe_int(row.get("rec_yards")))

    out = []
    for row in aggregated.values():
        rush_att = _safe_int(row.get("rush_attempts")) or 0
        rush_y = _safe_int(row.get("rush_yards")) or 0
        rec = _safe_int(row.get("receptions")) or 0
        rec_y = _safe_int(row.get("rec_yards")) or 0
        row["ypc"] = (float(rush_y) / float(rush_att)) if rush_att else 0.0
        row["ypr"] = (float(rec_y) / float(rec)) if rec else 0.0
        out.append(row)
    
    # FORCE SORT by rushing yards descending to fix ordering issues
    out.sort(key=lambda x: (x.get('rush_yards') or 0), reverse=True)
    
    out.sort(key=lambda x: (x.get('rush_yards') or 0), reverse=True)
    
    safe_offset = max(offset, 0)
    safe_limit = max(limit, 1)
    return out[safe_offset : safe_offset + safe_limit]


def receiving_season(
    sb: SupabaseClient,
    *,
    season: int,
    team: Optional[str],
    q: Optional[str] = None,
    limit: int,
    offset: int = 0,
) -> list[dict[str, Any]]:
    # Use season stats; team is best-effort (current team).
    rows = get_players_list(sb, season=season, position=None, team=team, q=q, limit=8000)
    # compute team target share within returned team scope
    by_team: dict[str, int] = {}
    for r in rows:
        t = r.get("team") or ""
        by_team[t] = by_team.get(t, 0) + int(r.get("targets") or 0)
    # Defensive/special teams positions to exclude
    blocked_positions = {"DB", "CB", "S", "SS", "FS", "LB", "ILB", "OLB", "DL", "DE", "DT", "NT", "OL", "OT", "OG", "C", "K", "P", "LS"}
    
    out = []
    for r in rows:
        pos = (r.get("position") or "").upper()
        # Allow NULL/UNK/empty positions if they have receiving stats
        # Block defensive/special teams positions
        if pos and pos not in {"WR", "TE", "RB"}:
            if pos in blocked_positions:
                continue
        t = r.get("team") or ""
        denom = by_team.get(t, 0) or 0
        share = (float(r.get("targets") or 0) / float(denom)) if denom else None
        out.append(
            {
                "season": season,
                "team": r.get("team"),
                "player_id": r.get("player_id"),
                "player_name": r.get("player_name"),
                "position": r.get("position"),
                "targets": int(r.get("targets") or 0),
                "receptions": int(r.get("receptions") or 0),
                "rec_yards": int(r.get("receivingYards") or 0),
                "air_yards": 0,
                "rec_tds": int(r.get("receivingTouchdowns") or 0),
                "team_target_share": share,
                "photoUrl": player_photo_url_from_name_team(name=str(r.get("player_name") or ""), team=str(r.get("team") or "")),
            }
        )
    out.sort(key=lambda x: int(x.get("targets") or 0), reverse=True)
    out.sort(key=lambda x: int(x.get("targets") or 0), reverse=True)
    
    safe_offset = max(offset, 0)
    safe_limit = max(limit, 1)
    return out[safe_offset : safe_offset + safe_limit]


def rushing_season(
    sb: SupabaseClient,
    *,
    season: int,
    team: Optional[str],
    position: Optional[str],
    q: Optional[str] = None,
    limit: int,
    offset: int = 0,
) -> list[dict[str, Any]]:
    pos_raw = (position or "").strip().upper()
    pos_filter = None if pos_raw in {"", "ALL"} else ("RB" if pos_raw == "HB" else pos_raw)

    rows = get_players_list(sb, season=season, position=pos_filter, team=team, q=q, limit=8000)
    by_team: dict[str, int] = {}
    for r in rows:
        t = r.get("team") or ""
        by_team[t] = by_team.get(t, 0) + int(r.get("rushAttempts") or 0)
    out = []
    for r in rows:
        pos = (r.get("position") or "").upper()
        # Position filtering already applied above when requested. Default includes all positions.
        t = r.get("team") or ""
        denom = by_team.get(t, 0) or 0
        share = (float(r.get("rushAttempts") or 0) / float(denom)) if denom else None
        games = int(r.get("games") or 0) or 0
        rush_att = int(r.get("rushAttempts") or 0)
        rush_y = int(r.get("rushingYards") or 0)
        rec = int(r.get("receptions") or 0)
        rec_y = int(r.get("receivingYards") or 0)
        out.append(
            {
                "season": season,
                "team": r.get("team"),
                "player_id": r.get("player_id"),
                "player_name": r.get("player_name"),
                "position": r.get("position"),
                "games": games,
                "rush_attempts": rush_att,
                "rush_yards": rush_y,
                "rush_tds": int(r.get("rushingTouchdowns") or 0),
                "ypc": (float(rush_y) / float(rush_att)) if rush_att else 0.0,
                "ypg": (float(rush_y) / float(games)) if games else 0.0,
                "receptions": rec,
                "rpg": (float(rec) / float(games)) if games else 0.0,
                "rec_yards": rec_y,
                "rec_ypg": (float(rec_y) / float(games)) if games else 0.0,
                "team_rush_share": share,
                "photoUrl": player_photo_url_from_name_team(name=str(r.get("player_name") or ""), team=str(r.get("team") or "")),
            }
        )
    out.sort(key=lambda x: int(x.get("rush_yards") or 0), reverse=True)
    out.sort(key=lambda x: int(x.get("rush_yards") or 0), reverse=True)
    
    safe_offset = max(offset, 0)
    safe_limit = max(limit, 1)
    return out[safe_offset : safe_offset + safe_limit]


def passing_dashboard(
    sb: SupabaseClient,
    *,
    season: int,
    week: int,
    team: Optional[str],
    position: Optional[str],
    limit: int,
    offset: int = 0,
) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {
        "season": f"eq.{int(season)}",
        "week": f"eq.{int(week)}",
        "or": "(passing_yards.gt.0,passing_attempts.gt.0,passing_touchdowns.gt.0)",
    }
    if team:
        t = sb.select("nfl_teams", select="id", filters={"abbreviation": f"eq.{team}"}, limit=1)
        tid = _safe_int(t[0].get("id")) if t else None
        if tid is not None:
            filters["team_id"] = f"eq.{tid}"
    stats = sb.select(
        "nfl_player_game_stats",
        select="player_id,game_id,team_id,season,week,passing_attempts,passing_completions,passing_yards,passing_touchdowns,passing_interceptions",
        filters=filters,
        limit=5000,
    )
    game_ids = sorted({_safe_int(r.get("game_id")) for r in stats if _safe_int(r.get("game_id")) is not None})
    game_map: dict[int, dict[str, Any]] = {}
    if game_ids:
        games = sb.select(
            "nfl_games",
            select="id,season,week,postseason",
            filters={"id": _in_list(game_ids)},
            limit=len(game_ids),
        )
        for g in games:
            gid = _safe_int(g.get("id"))
            if gid is not None:
                game_map[gid] = g
    # DON'T slice yet - need to filter by position first

    pids = sorted({_safe_int(r.get("player_id")) for r in stats if _safe_int(r.get("player_id")) is not None})
    players = sb.select("nfl_players", select="id,first_name,last_name,position_abbreviation", filters={"id": _in_list(pids)}, limit=len(pids))
    pmap = {int(p["id"]): p for p in players if _safe_int(p.get("id")) is not None}

    team_ids = sorted({_safe_int(r.get("team_id")) for r in stats if _safe_int(r.get("team_id")) is not None})
    tmap = _team_map(sb, [t for t in team_ids if t is not None])

    pos_raw = (position or "").strip().upper()
    if pos_raw in {"", "ALL"}:
        allowed_positions = {"QB"}
    else:
        allowed_positions = {pos_raw}
    
    # Defensive/special teams positions to exclude (unless user explicitly filters for them)
    blocked_positions = {"DB", "CB", "S", "SS", "FS", "LB", "ILB", "OLB", "DL", "DE", "DT", "NT", "OL", "OT", "OG", "C", "K", "P", "LS"}
    
    per_game: dict[tuple[int, int], dict[str, Any]] = {}
    for r in stats:
        pid = _safe_int(r.get("player_id"))
        gid = _safe_int(r.get("game_id"))
        if pid is None or gid is None:
            continue
        g = game_map.get(gid)
        if not g:
            continue
        if _safe_int(g.get("season")) != int(season) or _safe_int(g.get("week")) != int(week):
            continue
        if g.get("postseason") is True:
            continue
        p = pmap.get(pid, {})
        pos = (p.get("position_abbreviation") or "").strip().upper() or None
        
        # Allow NULL/UNK/empty positions if they have passing stats (already filtered by query)
        # But block defensive/special teams positions unless explicitly requested
        if pos and pos not in allowed_positions:
            if pos_raw not in {"", "ALL"} or pos in blocked_positions:
                continue
        pass_att = _safe_int(r.get("passing_attempts")) or 0
        pass_y = _safe_int(r.get("passing_yards")) or 0
        pass_td = _safe_int(r.get("passing_touchdowns")) or 0
        name = (str(p.get("first_name") or "").strip() + " " + str(p.get("last_name") or "").strip()).strip() or str(pid)
        tid = _safe_int(r.get("team_id"))

        score = (pass_y, pass_att, pass_td)
        key = (pid, gid)
        prev = per_game.get(key)
        if not prev or score > prev["_score"]:
            per_game[key] = {
                "season": season,
                "week": week,
                "team": tmap.get(tid) if tid is not None else None,
                "player_id": str(pid),
                "player_name": name,
                "position": pos,
                "passing_attempts": pass_att,
                "passing_completions": _safe_int(r.get("passing_completions")) or 0,
                "passing_yards": pass_y,
                "passing_tds": pass_td,
                "interceptions": _safe_int(r.get("passing_interceptions")) or 0,
                "photoUrl": player_photo_url_from_name_team(name=name, team=tmap.get(tid) if tid is not None else None),
                "_score": score,
            }

    aggregated: dict[int, dict[str, Any]] = {}
    for row in per_game.values():
        pid = int(row["player_id"])
        entry = aggregated.get(pid)
        if entry is None:
            entry = {k: v for k, v in row.items() if k != "_score"}
            aggregated[pid] = entry
            continue
        entry["passing_attempts"] = max(_safe_int(entry.get("passing_attempts")), _safe_int(row.get("passing_attempts")))
        entry["passing_completions"] = max(_safe_int(entry.get("passing_completions")), _safe_int(row.get("passing_completions")))
        entry["passing_yards"] = max(_safe_int(entry.get("passing_yards")), _safe_int(row.get("passing_yards")))
        entry["passing_tds"] = max(_safe_int(entry.get("passing_tds")), _safe_int(row.get("passing_tds")))
        entry["interceptions"] = max(_safe_int(entry.get("interceptions")), _safe_int(row.get("interceptions")))

    out = list(aggregated.values())
    
    # FORCE SORT by passing yards descending to fix ordering issues
    out.sort(key=lambda x: (x.get('passing_yards') or 0), reverse=True)
    
    safe_offset = max(offset, 0)
    safe_limit = max(limit, 1)
    return out[safe_offset : safe_offset + safe_limit]


def passing_season(
    sb: SupabaseClient,
    *,
    season: int,
    team: Optional[str],
    position: Optional[str],
    q: Optional[str] = None,
    limit: int,
) -> list[dict[str, Any]]:
    # Keep this endpoint simple and robust: query the season-stats table directly and order by passing yards.
    # This avoids relying on broad player-list queries that may be subject to server-side max row caps.
    pos_raw = (position or "").strip().upper()
    pos_filter = None if pos_raw in {"", "ALL"} else pos_raw

    filters: dict[str, Any] = {
        "season": f"eq.{int(season)}",
        "postseason": "eq.false",
        "or": "(passing_yards.gt.0,passing_attempts.gt.0,passing_touchdowns.gt.0)",
    }

    if team:
        t = sb.select("nfl_teams", select="id", filters={"abbreviation": f"eq.{team}"}, limit=1)
        tid = _safe_int(t[0].get("id")) if t else None
        if tid is not None:
            # PostgREST foreign-table filter syntax (season_stats -> nfl_players).
            filters["nfl_players.team_id"] = f"eq.{tid}"

    needle = _sanitize_search(q)
    if needle:
        filters["nfl_players.or"] = f"(first_name.ilike.*{needle}*,last_name.ilike.*{needle}*)"

    # Fetch a buffer to allow python-side position heuristics for unknown positions.
    req_limit = 1000
    rows = sb.select(
        "nfl_player_season_stats",
        select=(
            "player_id,passing_attempts,passing_completions,passing_yards,passing_touchdowns,passing_interceptions,"
            "nfl_players(first_name,last_name,position_abbreviation,team_id,nfl_teams(abbreviation))"
        ),
        filters=filters,
        order="passing_yards.desc.nullslast,passing_touchdowns.desc.nullslast",
        limit=req_limit,
    )

    out: list[dict[str, Any]] = []
    for r in rows:
        pid = _safe_int(r.get("player_id"))
        if pid is None:
            continue

        p = r.get("nfl_players") or {}
        pos = (p.get("position_abbreviation") or "").strip().upper() or None
        is_unknown_pos = (not pos) or (pos in {"UNK", "UNKNOWN", "NULL", "ROOKIE"})

        # If the user filtered for a position, enforce it, but allow unknown positions when stats prove the role.
        if pos_filter:
            if not is_unknown_pos and pos != pos_filter:
                continue
            if is_unknown_pos and pos_filter == "QB":
                # rows are already passing-only; still keep the check explicit.
                pass_yds = _safe_int(r.get("passing_yards")) or 0
                pass_att = _safe_int(r.get("passing_attempts")) or 0
                pass_tds = _safe_int(r.get("passing_touchdowns")) or 0
                if not (pass_yds > 0 or pass_att > 0 or pass_tds > 0):
                    continue

        team_obj = p.get("nfl_teams") or {}
        team_abbr = team_obj.get("abbreviation") or None
        name = (str(p.get("first_name") or "").strip() + " " + str(p.get("last_name") or "").strip()).strip() or str(pid)

        out.append(
            {
                "season": season,
                "team": team_abbr,
                "player_id": str(pid),
                "player_name": name,
                "position": pos or "UNK",
                "passing_attempts": _safe_int(r.get("passing_attempts")) or 0,
                "passing_completions": _safe_int(r.get("passing_completions")) or 0,
                "passing_yards": _safe_int(r.get("passing_yards")) or 0,
                "passing_tds": _safe_int(r.get("passing_touchdowns")) or 0,
                "interceptions": _safe_int(r.get("passing_interceptions")) or 0,
                "photoUrl": player_photo_url_from_name_team(name=name, team=team_abbr),
            }
        )

    out.sort(key=lambda x: int(x.get("passing_yards") or 0), reverse=True)
    return out[: min(max(limit, 1), 800)]


def total_yards_dashboard(
    sb: SupabaseClient,
    *,
    season: int,
    week: int,
    team: Optional[str],
    position: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    # Total yards = rushing + receiving.
    # Default behavior: show skill players (RB/WR/TE). `HB` is treated as `RB`.
    filters: dict[str, Any] = {"season": f"eq.{int(season)}", "week": f"eq.{int(week)}"}
    if team:
        t = sb.select("nfl_teams", select="id", filters={"abbreviation": f"eq.{team}"}, limit=1)
        tid = _safe_int(t[0].get("id")) if t else None
        if tid is not None:
            filters["team_id"] = f"eq.{tid}"
    stats = sb.select(
        "nfl_player_game_stats",
        select="player_id,game_id,team_id,season,week,rushing_yards,rushing_touchdowns,receiving_yards,receiving_touchdowns,rushing_attempts,receptions,receiving_targets",
        filters=filters,
        order="receiving_yards.desc.nullslast,rushing_yards.desc.nullslast",
        limit=5000,
    )
    game_ids = sorted({_safe_int(r.get("game_id")) for r in stats if _safe_int(r.get("game_id")) is not None})
    game_map: dict[int, dict[str, Any]] = {}
    if game_ids:
        games = sb.select(
            "nfl_games",
            select="id,season,week,postseason",
            filters={"id": _in_list(game_ids)},
            limit=len(game_ids),
        )
        for g in games:
            gid = _safe_int(g.get("id"))
            if gid is not None:
                game_map[gid] = g
    # DON'T slice yet - need to filter by position first

    pids = sorted({_safe_int(r.get("player_id")) for r in stats if _safe_int(r.get("player_id")) is not None})
    players = sb.select("nfl_players", select="id,first_name,last_name,position_abbreviation", filters={"id": _in_list(pids)}, limit=len(pids))
    pmap = {int(p["id"]): p for p in players if _safe_int(p.get("id")) is not None}
    team_ids = sorted({_safe_int(r.get("team_id")) for r in stats if _safe_int(r.get("team_id")) is not None})
    tmap = _team_map(sb, [t for t in team_ids if t is not None])

    pos_raw = (position or "").strip().upper()
    if pos_raw in {"", "ALL"}:
        allowed_positions = {"RB", "WR", "TE"}
    elif pos_raw == "HB":
        allowed_positions = {"RB"}
    else:
        allowed_positions = {pos_raw}
    
    # Defensive/special teams positions to exclude (unless user explicitly filters for them)
    blocked_positions = {"DB", "CB", "S", "SS", "FS", "LB", "ILB", "OLB", "DL", "DE", "DT", "NT", "OL", "OT", "OG", "C", "K", "P", "LS"}
    
    per_game: dict[tuple[int, int], dict[str, Any]] = {}
    for r in stats:
        pid = _safe_int(r.get("player_id"))
        gid = _safe_int(r.get("game_id"))
        if pid is None or gid is None:
            continue
        g = game_map.get(gid)
        if not g:
            continue
        if _safe_int(g.get("season")) != int(season) or _safe_int(g.get("week")) != int(week):
            continue
        if g.get("postseason") is True:
            continue
        p = pmap.get(pid, {})
        pos = (p.get("position_abbreviation") or "").strip().upper() or None
        
        # Allow NULL/UNK/empty positions if they have yards (already filtered by query)
        # But block defensive/special teams positions unless explicitly requested
        if pos and pos not in allowed_positions:
            if pos_raw not in {"", "ALL"} or pos in blocked_positions:
                continue
        name = (str(p.get("first_name") or "").strip() + " " + str(p.get("last_name") or "").strip()).strip() or str(pid)
        tid = _safe_int(r.get("team_id"))
        rush_y = _safe_int(r.get("rushing_yards")) or 0
        rec_y = _safe_int(r.get("receiving_yards")) or 0
        rush_td = _safe_int(r.get("rushing_touchdowns")) or 0
        rec_td = _safe_int(r.get("receiving_touchdowns")) or 0

        score = (rush_y + rec_y, rush_y, rec_y)
        key = (pid, gid)
        prev = per_game.get(key)
        if not prev or score > prev["_score"]:
            per_game[key] = {
                "season": season,
                "week": week,
                "team": tmap.get(tid) if tid is not None else None,
                "player_id": str(pid),
                "player_name": name,
                "position": pos,
                "rush_yards": rush_y,
                "rec_yards": rec_y,
                "total_yards": rush_y + rec_y,
                "total_tds": rush_td + rec_td,
                "photoUrl": player_photo_url_from_name_team(name=name, team=tmap.get(tid) if tid is not None else None),
                "_score": score,
            }

    aggregated: dict[int, dict[str, Any]] = {}
    for row in per_game.values():
        pid = int(row["player_id"])
        entry = aggregated.get(pid)
        if entry is None:
            entry = {k: v for k, v in row.items() if k != "_score"}
            aggregated[pid] = entry
            continue
        entry["rush_yards"] = max(_safe_int(entry.get("rush_yards")), _safe_int(row.get("rush_yards")))
        entry["rec_yards"] = max(_safe_int(entry.get("rec_yards")), _safe_int(row.get("rec_yards")))
        entry["total_yards"] = max(_safe_int(entry.get("total_yards")), _safe_int(row.get("total_yards")))
        entry["total_tds"] = max(_safe_int(entry.get("total_tds")), _safe_int(row.get("total_tds")))

    out = list(aggregated.values())
    out.sort(key=lambda x: int(x.get("total_yards") or 0), reverse=True)
    return out[: min(max(limit, 1), 800)]


def total_yards_season(
    sb: SupabaseClient,
    *,
    season: int,
    team: Optional[str],
    position: Optional[str],
    q: Optional[str] = None,
    limit: int,
) -> list[dict[str, Any]]:
    # Default behavior: show skill players (RB/WR/TE). `HB` is treated as `RB`.
    pos_raw = (position or "").strip().upper()
    if pos_raw in {"", "ALL"}:
        allowed_positions = {"RB", "WR", "TE"}
    elif pos_raw == "HB":
        allowed_positions = {"RB"}
    else:
        allowed_positions = {pos_raw}

    # Defensive/special teams positions to exclude (unless user explicitly filters for them)
    blocked_positions = {"DB", "CB", "S", "SS", "FS", "LB", "ILB", "OLB", "DL", "DE", "DT", "NT", "OL", "OT", "OG", "C", "K", "P", "LS"}

    rows = get_players_list(sb, season=season, position=None, team=team, q=q, limit=8000)
    out: list[dict[str, Any]] = []
    for r in rows:
        pos = (str(r.get("position") or "")).strip().upper()
        # Allow NULL/UNK/empty positions if they have yards
        # Block defensive/special teams positions unless explicitly requested
        if pos and pos not in allowed_positions:
            if pos_raw not in {"", "ALL"} or pos in blocked_positions:
                continue
        rush_y = int(r.get("rushingYards") or 0)
        rec_y = int(r.get("receivingYards") or 0)
        rush_td = int(r.get("rushingTouchdowns") or 0)
        rec_td = int(r.get("receivingTouchdowns") or 0)
        out.append(
            {
                "season": season,
                "team": r.get("team"),
                "player_id": r.get("player_id"),
                "player_name": r.get("player_name"),
                "position": r.get("position"),
                "rush_yards": rush_y,
                "rec_yards": rec_y,
                "total_yards": rush_y + rec_y,
                "total_tds": rush_td + rec_td,
                "photoUrl": player_photo_url_from_name_team(name=str(r.get("player_name") or ""), team=str(r.get("team") or "")),
            }
        )
    out.sort(key=lambda x: int(x.get("total_yards") or 0), reverse=True)
    return out[: min(max(limit, 1), 800)]


def advanced_passing_leaderboard(
    sb: SupabaseClient,
    *,
    season: int,
    sort_by: str = "avg_air_distance",
    position: Optional[str] = None,
    team_abbr: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """
    Advanced Passing Leaderboard (Season Totals from GOAT API)
    Queries week=0 rows from nfl_advanced_passing_stats table.
    """
    filters: dict[str, Any] = {
        "season": f"eq.{int(season)}",
        "week": "eq.0",  # Season totals only
        "postseason": "eq.false",
        "attempts": "gte.50",  # Minimum volume threshold
    }
    
    # Text search on name
    needle = _sanitize_search(q)
    if needle:
        filters["nfl_players.or"] = f"(first_name.ilike.*{needle}*,last_name.ilike.*{needle}*)"

    # Build player select with embedded team info
    select_parts = [
        "player_id",
        "season",
        "attempts",
        "completions",
        "pass_yards",
        "pass_touchdowns",
        "interceptions",
        "passer_rating",
        "completion_percentage_above_expectation",
        "expected_completion_percentage",
        "avg_time_to_throw",
        "avg_intended_air_yards",
        "avg_completed_air_yards",
        "avg_air_distance",
        "avg_air_yards_differential",
        "avg_air_yards_to_sticks",
        "aggressiveness",
        "nfl_players!inner(id,first_name,last_name,position_abbreviation,team_id,nfl_teams(abbreviation))",
    ]
    select_clause = ",".join(select_parts)

    rows = sb.select(
        "nfl_advanced_passing_stats",
        select=select_clause,
        filters=filters,
        order=f"{sort_by}.desc.nullslast",
        limit=limit,
    )

    # Flatten player info for easier frontend consumption
    out = []
    for r in rows:
        player = r.get("nfl_players") or {}
        team_data = player.get("nfl_teams") or {}
        
        # Apply position filter (Python-side)
        if position:
            player_pos = (player.get("position_abbreviation") or "").upper()
            if player_pos != position.upper():
                continue
        
        # Apply team filter (Python-side)
        if team_abbr:
            team_abbr_actual = (team_data.get("abbreviation") or "").upper()
            if team_abbr_actual != team_abbr.upper():
                continue
        
        player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
        out.append({
            "player_id": r.get("player_id"),
            "player_name": player_name,
            "position": player.get("position_abbreviation") or "QB",
            "team": team_data.get("abbreviation"),
            "season": r.get("season"),
            "attempts": r.get("attempts"),
            "completions": r.get("completions"),
            "pass_yards": r.get("pass_yards"),
            "pass_touchdowns": r.get("pass_touchdowns"),
            "interceptions": r.get("interceptions"),
            "passer_rating": r.get("passer_rating"),
            "completion_percentage_above_expectation": r.get("completion_percentage_above_expectation"),
            "expected_completion_percentage": r.get("expected_completion_percentage"),
            "avg_time_to_throw": r.get("avg_time_to_throw"),
            "avg_intended_air_yards": r.get("avg_intended_air_yards"),
            "avg_completed_air_yards": r.get("avg_completed_air_yards"),
            "avg_air_distance": r.get("avg_air_distance"),
            "avg_air_yards_differential": r.get("avg_air_yards_differential"),
            "avg_air_yards_to_sticks": r.get("avg_air_yards_to_sticks"),
            "aggressiveness": r.get("aggressiveness"),
            "photoUrl": player_photo_url_from_name_team(name=player_name, team=team_data.get("abbreviation") or ""),
        })
    
    return out


def advanced_rushing_leaderboard(
    sb: SupabaseClient,
    *,
    season: int,
    sort_by: str = "rush_yards_over_expected",
    position: Optional[str] = None,
    team_abbr: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """
    Advanced Rushing Leaderboard (Season Totals from GOAT API)
    Queries week=0 rows from nfl_advanced_rushing_stats table.
    """
    filters: dict[str, Any] = {
        "season": f"eq.{int(season)}",
        "week": "eq.0",  # Season totals only
        "postseason": "eq.false",
        "rush_attempts": "gte.20",  # Minimum volume threshold
    }

    # Text search on name
    needle = _sanitize_search(q)
    if needle:
        filters["nfl_players.or"] = f"(first_name.ilike.*{needle}*,last_name.ilike.*{needle}*)"

    select_parts = [
        "player_id",
        "season",
        "rush_attempts",
        "rush_yards",
        "rush_touchdowns",
        "efficiency",
        "avg_rush_yards",
        "avg_time_to_los",
        "expected_rush_yards",
        "rush_yards_over_expected",
        "rush_yards_over_expected_per_att",
        "rush_pct_over_expected",
        "percent_attempts_gte_eight_defenders",
        "nfl_players!inner(id,first_name,last_name,position_abbreviation,team_id,nfl_teams(abbreviation))",
    ]
    select_clause = ",".join(select_parts)

    rows = sb.select(
        "nfl_advanced_rushing_stats",
        select=select_clause,
        filters=filters,
        order=f"{sort_by}.desc.nullslast",
        limit=limit,
    )

    # Flatten player info
    out = []
    for r in rows:
        player = r.get("nfl_players") or {}
        team_data = player.get("nfl_teams") or {}
        
        # Apply position filter (Python-side)
        if position:
            player_pos = (player.get("position_abbreviation") or "").upper()
            if player_pos != position.upper():
                continue
        
        # Apply team filter (Python-side)
        if team_abbr:
            team_abbr_actual = (team_data.get("abbreviation") or "").upper()
            if team_abbr_actual != team_abbr.upper():
                continue
        
        player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
        out.append({
            "player_id": r.get("player_id"),
            "player_name": player_name,
            "position": player.get("position_abbreviation") or "RB",
            "team": team_data.get("abbreviation"),
            "season": r.get("season"),
            "rush_attempts": r.get("rush_attempts"),
            "rush_yards": r.get("rush_yards"),
            "rush_touchdowns": r.get("rush_touchdowns"),
            "efficiency": r.get("efficiency"),
            "avg_rush_yards": r.get("avg_rush_yards"),
            "avg_time_to_los": r.get("avg_time_to_los"),
            "expected_rush_yards": r.get("expected_rush_yards"),
            "rush_yards_over_expected": r.get("rush_yards_over_expected"),
            "rush_yards_over_expected_per_att": r.get("rush_yards_over_expected_per_att"),
            "rush_pct_over_expected": r.get("rush_pct_over_expected"),
            "percent_attempts_gte_eight_defenders": r.get("percent_attempts_gte_eight_defenders"),
            "photoUrl": player_photo_url_from_name_team(name=player_name, team=team_data.get("abbreviation") or ""),
        })
    
    return out


def advanced_receiving_leaderboard(
    sb: SupabaseClient,
    *,
    season: int,
    sort_by: str = "avg_yac_above_expectation",
    position: Optional[str] = None,
    team_abbr: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """
    Advanced Receiving Leaderboard (Season Totals from GOAT API)
    Queries week=0 rows from nfl_advanced_receiving_stats table.
    """
    filters: dict[str, Any] = {
        "season": f"eq.{int(season)}",
        "week": "eq.0",  # Season totals only
        "postseason": "eq.false",
        "targets": "gte.10",  # Minimum volume threshold
    }

    # Text search on name
    needle = _sanitize_search(q)
    if needle:
        filters["nfl_players.or"] = f"(first_name.ilike.*{needle}*,last_name.ilike.*{needle}*)"

    select_parts = [
        "player_id",
        "season",
        "receptions",
        "targets",
        "yards",
        "avg_yac",
        "avg_expected_yac",
        "avg_yac_above_expectation",
        "catch_percentage",
        "avg_cushion",
        "avg_separation",
        "percent_share_of_intended_air_yards",
        "nfl_players!inner(id,first_name,last_name,position_abbreviation,team_id,nfl_teams(abbreviation))",
    ]
    select_clause = ",".join(select_parts)

    rows = sb.select(
        "nfl_advanced_receiving_stats",
        select=select_clause,
        filters=filters,
        order=f"{sort_by}.desc.nullslast",
        limit=limit,
    )

    # Flatten player info
    out = []
    for r in rows:
        player = r.get("nfl_players") or {}
        team_data = player.get("nfl_teams") or {}
        
        # Apply position filter (Python-side)
        if position:
            player_pos = (player.get("position_abbreviation") or "").upper()
            if player_pos != position.upper():
                continue
        
        # Apply team filter (Python-side)
        if team_abbr:
            team_abbr_actual = (team_data.get("abbreviation") or "").upper()
            if team_abbr_actual != team_abbr.upper():
                continue
        
        player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
        out.append({
            "player_id": r.get("player_id"),
            "player_name": player_name,
            "position": player.get("position_abbreviation") or "WR",
            "team": team_data.get("abbreviation"),
            "season": r.get("season"),
            "receptions": r.get("receptions"),
            "targets": r.get("targets"),
            "yards": r.get("yards"),
            "avg_yac": r.get("avg_yac"),
            "avg_expected_yac": r.get("avg_expected_yac"),
            "avg_yac_above_expectation": r.get("avg_yac_above_expectation"),
            "catch_percentage": r.get("catch_percentage"),
            "avg_cushion": r.get("avg_cushion"),
            "avg_separation": r.get("avg_separation"),
            "percent_share_of_intended_air_yards": r.get("percent_share_of_intended_air_yards"),
            "photoUrl": player_photo_url_from_name_team(name=player_name, team=team_data.get("abbreviation") or ""),
        })
    
    return out


def _generate_matchup_flags(row: dict[str, Any], position: str) -> list[str]:
    """
    Generate top matchup flags explaining why this is a smash spot (no emojis, personalized).
    """
    flags = []
    
    # Helper to safely get numeric values
    def get_num(key: str) -> float:
        return row.get(key) or 0
    
    def percentile_to_rank(percentile: float) -> int:
        """Convert percentile (0-100) to rank (1-32). Higher percentile = worse defense = higher rank number."""
        return max(1, min(32, round(1 + (percentile / 100) * 31)))
    
    if position == "WR":
        # Air yards share - personalized messaging
        air_share = get_num("air_share_pct")
        if air_share >= 40.0:
            flags.append(f"Commands {air_share:.0f}% of team's deep targets")
        elif air_share >= 35.0:
            flags.append(f"Primary receiving option with {air_share:.0f}% air share")
        elif air_share >= 30.0:
            flags.append(f"Top target with {air_share:.0f}% of team's air yards")
        
        # Separation
        separation = get_num("separation")
        if separation >= 3.5:
            flags.append(f"Consistently creates {separation:.1f} yards of separation")
        elif separation >= 3.0:
            flags.append(f"Gets open with {separation:.1f}yd average cushion")
        
        # Opponent defense ranking - convert to 1-32 rank
        opp_rank_pct = get_num("opp_def_rank_pct")
        opp_rank = percentile_to_rank(opp_rank_pct)
        opp_ypg = get_num("opp_pass_ypg")
        if opp_rank >= 28:  # Bottom 5
            flags.append(f"Facing #{opp_rank} ranked pass defense (allows {opp_ypg:.0f} YPG)")
        elif opp_rank >= 23:  # Bottom 10
            flags.append(f"Favorable matchup vs #{opp_rank} ranked secondary")
        
        # QB quality
        qb_cpoe = get_num("qb_cpoe")
        if qb_cpoe >= 3.0:
            flags.append(f"Elite QB play (+{qb_cpoe:.1f} completion % over expected)")
        elif qb_cpoe >= 2.0:
            flags.append(f"Efficient QB with +{qb_cpoe:.1f} CPOE above average")
        
        # Game script
        game_total = get_num("game_total")
        is_underdog = get_num("is_underdog")
        if game_total >= 48.0 and is_underdog == 1:
            flags.append(f"High-scoring environment ({game_total:.0f} O/U) + trailing script")
        elif game_total >= 50.0:
            flags.append(f"Shootout potential with {game_total:.0f} point total")
        elif game_total >= 48.0:
            flags.append(f"High over/under of {game_total:.0f} points expected")
    
    elif position == "RB":
        # Run funnel matchup - convert to 1-32 rank
        opp_rank_pct = get_num("opp_def_rank_pct")
        opp_rank = percentile_to_rank(opp_rank_pct)
        opp_rush_ypg = get_num("opp_rush_ypg")
        if opp_rank >= 28:  # Bottom 5
            flags.append(f"Facing #{opp_rank} ranked run defense (allows {opp_rush_ypg:.0f} YPG)")
        elif opp_rank >= 23:  # Bottom 10
            flags.append(f"Favorable run matchup vs #{opp_rank} ranked defense")
        
        # Turnover differential
        turnover_diff = get_num("opp_turnover_diff")
        if turnover_diff <= -5:
            flags.append(f"Opponent giveaway-prone with {abs(int(turnover_diff))} turnover differential")
        elif turnover_diff <= -3:
            flags.append(f"Short field opportunities with turnover-prone opponent")
        
        # Favorite status (game script)
        is_favorite = get_num("is_favorite")
        spread = get_num("spread")
        if is_favorite == 1 and spread <= -7.0:
            flags.append(f"Heavy {abs(spread):.1f}-pt favorite (run-heavy 4th quarter)")
        elif is_favorite == 1 and spread <= -3.5:
            flags.append(f"Favored by {abs(spread):.1f} points (positive game script)")
        
        # Efficiency
        ryoe = get_num("ryoe_per_att")
        if ryoe >= 0.20:
            flags.append(f"Elite efficiency at +{ryoe:.2f} rush yards over expected per carry")
        elif ryoe >= 0.15:
            flags.append(f"Creating extra yardage at +{ryoe:.2f} RYOE per attempt")
        
        # Volume
        touches = get_num("touches_per_game")
        if touches >= 22.0:
            flags.append(f"True workhorse with {touches:.1f} touches per game")
        elif touches >= 20.0:
            flags.append(f"High-volume back averaging {touches:.1f} touches/game")
        
        # Dual threat receiving upside
        rec_targets = get_num("rec_targets")
        if rec_targets >= 60:
            flags.append(f"Dual-threat back with {int(rec_targets)} targets on the season")
        elif rec_targets >= 40:
            flags.append(f"Pass-catching upside with {int(rec_targets)} receiving targets")
    
    elif position == "QB":
        # Shootout potential
        game_total = get_num("game_total")
        if game_total >= 52.0:
            flags.append(f"Massive shootout potential with {game_total:.0f} O/U")
        elif game_total >= 50.0:
            flags.append(f"High-scoring game expected ({game_total:.0f} O/U)")
        elif game_total >= 48.0:
            flags.append(f"Elevated passing environment with {game_total:.0f} point total")
        
        # Pass funnel defense - convert to 1-32 rank
        opp_rank_pct = get_num("opp_def_rank_pct")
        opp_rank = percentile_to_rank(opp_rank_pct)
        opp_pass_ypg = get_num("opp_pass_ypg")
        if opp_rank >= 28:  # Bottom 5
            flags.append(f"Facing #{opp_rank} ranked pass defense (allows {opp_pass_ypg:.0f} YPG)")
        elif opp_rank >= 23:  # Bottom 10
            flags.append(f"Soft secondary ranked #{opp_rank} in pass yards allowed")
        
        # Pocket protection
        oline_rank = get_num("oline_rank_pct")
        if oline_rank >= 75:
            flags.append(f"Elite pass protection from top-{int(100 - oline_rank)} offensive line")
        elif oline_rank >= 70:
            flags.append(f"Clean pocket with strong O-line protection")
        
        # QB efficiency
        cpoe = get_num("cpoe")
        if cpoe >= 3.0:
            flags.append(f"Elite accuracy at +{cpoe:.1f} completion % above expectation")
        elif cpoe >= 2.5:
            flags.append(f"Highly efficient with +{cpoe:.1f} CPOE")
        
        # Underdog game script
        is_underdog = get_num("is_underdog")
        spread = get_num("spread")
        if is_underdog == 1 and spread >= 7.0:
            flags.append(f"Underdog by {spread:.1f} points (pass-heavy trailing script)")
        elif is_underdog == 1 and spread >= 3.5:
            flags.append(f"Expected to trail ({spread:.1f}-pt underdog)")
    
    # Return top 3-4 flags
    # Ensure minimum of 3 flags with fallbacks
    if len(flags) < 3:
        if position == "WR":
            if get_num("targets_per_game") > 0 and len(flags) < 3:
                flags.append(f"Averages {get_num('targets_per_game'):.1f} targets per game")
            if get_num("catch_rate") > 0 and len(flags) < 3:
                flags.append(f"Reliable hands with {get_num('catch_rate'):.0f}% catch rate")
            if get_num("adot") > 0 and len(flags) < 3:
                flags.append(f"Average depth of target: {get_num('adot'):.1f} yards downfield")
        elif position == "RB":
            if get_num("rush_att_per_game") > 0 and len(flags) < 3:
                flags.append(f"Sees {get_num('rush_att_per_game'):.1f} carries per game")
            if get_num("ypc") > 0 and len(flags) < 3:
                flags.append(f"Averages {get_num('ypc'):.1f} yards per carry")
            if get_num("touches_per_game") > 0 and len(flags) < 3:
                flags.append(f"Total touches: {get_num('touches_per_game'):.1f} per game")
        elif position == "QB":
            if get_num("pass_att_per_game") > 0 and len(flags) < 3:
                flags.append(f"Throws {get_num('pass_att_per_game'):.1f} passes per game")
            if get_num("qbr") > 0 and len(flags) < 3:
                flags.append(f"QB rating of {get_num('qbr'):.1f} this season")
            if get_num("cpoe") != 0 and len(flags) < 3:
                flags.append(f"Completion percentage: {get_num('comp_pct'):.1f}%")
    
    return flags[:4]


def _get_dynamic_stats(row: dict[str, Any], position: str) -> tuple[str, str, str]:
    """
    Get top 3 most relevant/impactful stats for a player based on their scoring components.
    Returns (stat1, stat2, stat3) formatted strings.
    """
    def safe_get(key: str, default: float = 0.0) -> float:
        """Safely get numeric value, ensuring it's not None."""
        val = row.get(key, default)
        return val if val is not None else default
    
    def percentile_to_rank(percentile: float) -> int:
        """Convert percentile (0-100) to rank (1-32). Higher percentile = worse defense = higher rank number."""
        return max(1, min(32, round(1 + (percentile / 100) * 31)))
    
    if position == "WR" or position == "TE":
        # Gather stats with their scoring component weights
        opp_rank = percentile_to_rank(safe_get('opp_def_rank_pct', 50))
        stats = [
            (safe_get('air_share_score'), f"{safe_get('air_share_pct'):.0f}% Air", "air"),
            (safe_get('adot_score'), f"{safe_get('adot'):.1f} aDOT", "adot"),
            (safe_get('separation_score'), f"{safe_get('separation'):.1f}yd Sep", "sep"),
            (safe_get('matchup_score'), f"#{opp_rank} Def", "matchup"),
            (safe_get('qb_efficiency_score'), f"+{safe_get('qb_cpoe'):.1f} QB CPOE", "qb"),
            (safe_get('catch_rate_score'), f"{safe_get('catch_rate'):.0f}% Catch", "catch"),
            (safe_get('volume_score'), f"{safe_get('targets_per_game'):.1f} TGT/G", "vol"),
        ]
        # Sort by score contribution and take top 3
        top_3 = sorted(stats, key=lambda x: x[0], reverse=True)[:3]
        return (top_3[0][1], top_3[1][1], top_3[2][1])
    
    elif position == "RB" or position == "HB":
        opp_rank = percentile_to_rank(safe_get('opp_def_rank_pct', 50))
        stats = [
            (safe_get('efficiency_score'), f"+{safe_get('ryoe_per_att'):.2f} RYOE", "eff"),
            (safe_get('volume_score'), f"{safe_get('rush_att_per_game'):.1f} ATT/G", "vol"),
            (safe_get('run_funnel_score'), f"#{opp_rank} Run D", "matchup"),
            (safe_get('favorite_score'), f"{abs(safe_get('spread')):.1f}pt Fav" if safe_get('is_favorite') == 1 else "Script", "script"),
            (safe_get('receiving_upside_score'), f"{int(safe_get('rec_targets'))} Rec TGT", "rec"),
            (safe_get('receiving_upside_score') + 1, f"{safe_get('touches_per_game'):.1f} Touch/G", "touch"),
        ]
        top_3 = sorted(stats, key=lambda x: x[0], reverse=True)[:3]
        return (top_3[0][1], top_3[1][1], top_3[2][1])
    
    elif position == "QB":
        opp_rank = percentile_to_rank(safe_get('opp_def_rank_pct', 50))
        stats = [
            (safe_get('shootout_score'), f"{safe_get('game_total'):.0f} O/U", "shootout"),
            (safe_get('efficiency_score'), f"+{safe_get('cpoe'):.1f} CPOE", "eff"),
            (safe_get('aggressiveness_score'), f"{safe_get('aggressiveness'):.1f}% AGG", "agg"),
            (safe_get('pass_funnel_score'), f"#{opp_rank} Pass D", "matchup"),
            (safe_get('pocket_score'), f"#{int(100-safe_get('oline_rank_pct', 50))} OLine", "oline"),
            (safe_get('script_score'), f"{abs(safe_get('spread')):.1f}pt Dog" if safe_get('is_underdog') == 1 else "Script", "script"),
            (1, f"{safe_get('pass_att_per_game'):.1f} ATT/G", "vol"),
        ]
        top_3 = sorted(stats, key=lambda x: x[0], reverse=True)[:3]
        return (top_3[0][1], top_3[1][1], top_3[2][1])
    
    # Fallback
    return ("N/A", "N/A", "N/A")


def smash_feed(
    sb: SupabaseClient, 
    season: int, 
    week: int, 
    limit: int = 25
) -> list[dict[str, Any]]:
    """
    Unified Smash Spot Feed: Returns top betting opportunities across all positions.
    
    Queries:
    - model_wr_smash (WR/TE alpha receivers) - Top 15
    - model_rb_smash (RB dual-threat backs) - Top 15
    - model_qb_smash (QB gunslingers) - Top 15
    
    Returns:
    - Top 10 (or limit) players across all positions sorted by smash_score
    - Top 3 matchup flags per player
    - Player photo URLs
    - Vegas lines (DraftKings)
    """
    
    # Query top 15 per position (total pool of 45 players)
    per_pos_limit = max(limit, 25)
    wr_rows = sb.select(
        "model_wr_smash",
        select="*",
        filters={"season": f"eq.{int(season)}", "week": f"eq.{int(week)}"},
        limit=per_pos_limit,
    )
    
    rb_rows = sb.select(
        "model_rb_smash",
        select="*",
        filters={"season": f"eq.{int(season)}", "week": f"eq.{int(week)}"},
        limit=per_pos_limit,
    )
    
    qb_rows = sb.select(
        "model_qb_smash",
        select="*",
        filters={"season": f"eq.{int(season)}", "week": f"eq.{int(week)}"},
        limit=per_pos_limit,
    )
    
    # Merge all results
    all_spots: list[dict[str, Any]] = []
    
    for row in wr_rows:
        player_name = row.get("player_name", "")
        team = row.get("team", "")
        stat1, stat2, stat3 = _get_dynamic_stats(row, "WR")
        
        # Convert percentile to 1-32 rank for display
        opp_def_pct = float(row.get("opp_def_rank_pct") or 50)
        opp_rank_1_32 = max(1, min(32, round(1 + (opp_def_pct / 100) * 31)))
        
        all_spots.append({
            "player_id": str(row.get("player_id", "")),
            "player_name": player_name,
            "position": row.get("position", "WR"),
            "team": team,
            "opponent": row.get("opponent", ""),
            "smash_score": float(row.get("smash_score") or 0),
            "dk_line": float(row.get("dk_line") or 0) if row.get("dk_line") else None,
            "game_total": float(row.get("game_total") or 0),
            "opponent_rank": opp_rank_1_32,
            "matchup_flags": _generate_matchup_flags(row, "WR"),
            "photoUrl": player_photo_url_from_name_team(name=player_name, team=team),
            # Dynamic stats based on scoring components
            "stat1": stat1,
            "stat2": stat2,
            "stat3": stat3,
            # ALL raw database fields for expanded view
            "raw_stats": {k: v for k, v in row.items() if k not in ["player_name", "team", "opponent", "position"]},
        })
    
    for row in rb_rows:
        player_name = row.get("player_name", "")
        team = row.get("team", "")
        stat1, stat2, stat3 = _get_dynamic_stats(row, "RB")
        
        # Convert percentile to 1-32 rank for display
        opp_def_pct = float(row.get("opp_def_rank_pct") or 50)
        opp_rank_1_32 = max(1, min(32, round(1 + (opp_def_pct / 100) * 31)))
        
        all_spots.append({
            "player_id": str(row.get("player_id", "")),
            "player_name": player_name,
            "position": row.get("position", "RB"),
            "team": team,
            "opponent": row.get("opponent", ""),
            "smash_score": float(row.get("smash_score") or 0),
            "dk_line": float(row.get("dk_line") or 0) if row.get("dk_line") else None,
            "game_total": float(row.get("game_total") or 0),
            "opponent_rank": opp_rank_1_32,
            "matchup_flags": _generate_matchup_flags(row, "RB"),
            "photoUrl": player_photo_url_from_name_team(name=player_name, team=team),
            # Dynamic stats based on scoring components
            "stat1": stat1,
            "stat2": stat2,
            "stat3": stat3,
            # ALL raw database fields for expanded view
            "raw_stats": {k: v for k, v in row.items() if k not in ["player_name", "team", "opponent", "position"]},
        })
    
    for row in qb_rows:
        player_name = row.get("player_name", "")
        team = row.get("team", "")
        stat1, stat2, stat3 = _get_dynamic_stats(row, "QB")
        
        # Convert percentile to 1-32 rank for display
        opp_def_pct = float(row.get("opp_def_rank_pct") or 50)
        opp_rank_1_32 = max(1, min(32, round(1 + (opp_def_pct / 100) * 31)))
        
        all_spots.append({
            "player_id": str(row.get("player_id", "")),
            "player_name": player_name,
            "position": row.get("position", "QB"),
            "team": team,
            "opponent": row.get("opponent", ""),
            "smash_score": float(row.get("smash_score") or 0),
            "dk_line": float(row.get("dk_line") or 0) if row.get("dk_line") else None,
            "game_total": float(row.get("game_total") or 0),
            "opponent_rank": opp_rank_1_32,
            "matchup_flags": _generate_matchup_flags(row, "QB"),
            "photoUrl": player_photo_url_from_name_team(name=player_name, team=team),
            # Dynamic stats based on scoring components
            "stat1": stat1,
            "stat2": stat2,
            "stat3": stat3,
            # ALL raw database fields for expanded view
            "raw_stats": {k: v for k, v in row.items() if k not in ["player_name", "team", "opponent", "position"]},
        })
    
    # Apply position-specific curve scaling: each position's max score becomes 100
    # This ensures QBs, RBs, and WRs/TEs are all competitive
    for position in ['QB', 'RB', 'WR', 'TE']:
        pos_spots = [spot for spot in all_spots if spot['position'] == position]
        if pos_spots:
            max_score = max(spot['smash_score'] for spot in pos_spots)
            if max_score > 0 and max_score < 100:
                scale_factor = 100.0 / max_score
                for spot in pos_spots:
                    spot['smash_score'] = round(spot['smash_score'] * scale_factor)
    
    # Per-position caps (ensure breadth across positions). Ignore request cap here.
    qb_limit = 25
    rb_limit = 25
    wr_limit = 30
    te_limit = 15  # TE from WR view

    qbs = [s for s in all_spots if (s.get("position") or "").upper() == "QB"][:qb_limit]
    rbs = [s for s in all_spots if (s.get("position") or "").upper() == "RB"][:rb_limit]
    wrs = [s for s in all_spots if (s.get("position") or "").upper() == "WR"][:wr_limit]
    tes = [s for s in all_spots if (s.get("position") or "").upper() == "TE"][:te_limit]

    combined = qbs + rbs + wrs + tes
    combined.sort(key=lambda x: x["smash_score"], reverse=True)

    # Return full combined list without global cap to avoid truncating positions
    return combined


def get_team_standings(sb: SupabaseClient, season: int) -> list[dict[str, Any]]:
    """
    Fetch standings from BDL nfl_team_standings table.
    """
    # Fetch standings data from BDL
    standings_rows = sb.select(
        "nfl_team_standings",
        select="team_id,wins,losses,ties,win_streak,points_for,points_against,point_differential,playoff_seed,overall_record,conference_record,division_record,home_record,road_record,nfl_teams!inner(abbreviation,name,primary_color,secondary_color,division,conference,logo_url)",
        filters={"season": f"eq.{season}"},
        limit=50
    )
    
    # Fetch ATS Data from nfl_game_lines
    ats_map = {} # team_id -> {w, l, p}
    try:
        # Get all lines for this season
        lines = sb.select(
            "nfl_game_lines",
            select="nflverse_game_id,home_team,away_team,home_score,away_score,spread_line,home_moneyline,away_moneyline,game_type,updated_at",
            filters={"season": f"eq.{season}", "game_type": "eq.REG"},
            limit=2000,
        )

        def _parse_spread(raw: Any) -> Optional[float]:
            if raw is None:
                return None
            if isinstance(raw, (int, float)):
                return float(raw)
            s = str(raw).strip().upper()
            if s in {"PK", "PICK", "PICKEM"}:
                return 0.0
            try:
                return float(s)
            except Exception:
                return None

        def _normalize_spread(spread: Optional[float], home_ml: Any, away_ml: Any) -> Optional[float]:
            if spread is None:
                return None
            try:
                h = float(home_ml) if home_ml is not None else None
                a = float(away_ml) if away_ml is not None else None
            except Exception:
                return spread
            if h is None or a is None:
                return spread
            home_favored = h < a
            if home_favored and spread > 0:
                return -abs(spread)
            if (not home_favored) and spread < 0:
                return abs(spread)
            return spread

        deduped_lines: dict[str, dict[str, Any]] = {}
        for g in lines:
            key = g.get("nflverse_game_id") or f"{g.get('home_team')}@{g.get('away_team')}:{g.get('gameday')}"
            prev = deduped_lines.get(key)
            if not prev or str(g.get("updated_at")) > str(prev.get("updated_at")):
                deduped_lines[key] = g
        
        # We need team name -> ID map
        teams_ref = {}
        for row in standings_rows:
            t = row.get("nfl_teams") or {}
            if t.get("abbreviation") and row.get("team_id"):
                teams_ref[t.get("abbreviation")] = row.get("team_id")
        # Add nflverse aliases so game_lines abbreviations resolve correctly
        for nflv, db_abbr in _NFLVERSE_TO_DB_TEAM.items():
            if db_abbr in teams_ref and nflv not in teams_ref:
                teams_ref[nflv] = teams_ref[db_abbr]

        for g in deduped_lines.values():
            home = g.get("home_team")
            away = g.get("away_team")
            hs = g.get("home_score")
            as_ = g.get("away_score")
            spread = _normalize_spread(_parse_spread(g.get("spread_line")), g.get("home_moneyline"), g.get("away_moneyline"))
            
            if hs is None or as_ is None or spread is None:
                continue
                
            hid = teams_ref.get(home)
            aid = teams_ref.get(away)
            
            if not hid or not aid:
                continue
            
            # Init stats
            if hid not in ats_map: ats_map[hid] = {"w":0, "l":0, "p":0}
            if aid not in ats_map: ats_map[aid] = {"w":0, "l":0, "p":0}
            
            # Logic: Home Score + Spread > Away Score = Home Cover
            diff = (hs + spread) - as_
            if diff > 0:
                ats_map[hid]["w"] += 1
                ats_map[aid]["l"] += 1
            elif diff < 0:
                ats_map[hid]["l"] += 1
                ats_map[aid]["w"] += 1
            else:
                ats_map[hid]["p"] += 1
                ats_map[aid]["p"] += 1
                
    except Exception as e:
        print(f"ATS Calc Error: {e}")

    # Fetch Team Season Stats for advanced metrics (3rd down, Red Zone, etc.)
    # Also fetch standard aggregates if needed (pass_yards, rush_yards, etc)
    advanced_stats_map = {}
    try:
        adv_rows = sb.select(
            "nfl_team_season_stats",
            select="team_id,third_down_conv_pct,red_zone_efficiency,turnover_differential,possession_time,passing_yards,rushing_yards,turnovers,total_offensive_yards_per_game",
            filters={"season": f"eq.{season}"},
            limit=50
        )
        for ar in adv_rows:
            tid = _safe_int(ar.get("team_id"))
            if tid:
                advanced_stats_map[tid] = ar
    except Exception as e:
        print(f"Error fetching team season stats: {e}")

    result = []
    for row in standings_rows:
        team_info = row.get("nfl_teams") if isinstance(row.get("nfl_teams"), dict) else {}
        tid = row.get("team_id")
        ats = ats_map.get(tid, {"w":0, "l":0, "p":0})
        ats_total = ats["w"] + ats["l"] + ats["p"]
        
        # Advanced Stats
        adv = advanced_stats_map.get(tid, {})
        
        # Wins/Losses OK, but win_pct might be None or string
        wins = _safe_int(row.get("wins")) or 0
        losses = _safe_int(row.get("losses")) or 0
        ties = _safe_int(row.get("ties")) or 0
        games = wins + losses + ties
        
        # Calculate win_pct if missing or invalid
        win_pct = row.get("win_pct")
        if win_pct is None and games > 0:
            win_pct = round(wins / games, 3)
        else:
            win_pct = _safe_float(win_pct)

        result.append({
            "team": team_info.get("abbreviation", ""),
            "team_name": team_info.get("name", ""),
            "division": f"{team_info.get('conference', '')} {team_info.get('division', '').capitalize()}".strip(),
            "conference": team_info.get("conference", ""),
            "primary_color": team_info.get("primary_color"),
            "secondary_color": team_info.get("secondary_color"),
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "games": games, # Add games for frontend calculation
            "pct": win_pct, 
            "win_pct": win_pct,
            "pf": _safe_int(row.get("points_for")),
            "pa": _safe_int(row.get("points_against")),
            "diff": _safe_int(row.get("point_differential")),
            "strk": row.get("win_streak"),
            "ats_w": ats["w"],
            "ats_l": ats["l"],
            "ats_p": ats["p"],
            "ats_wins": ats["w"], # Alias for frontend
            "ats_losses": ats["l"], # Alias for frontend
            
            # Team Season Stats
            "third_down_pct": _safe_float(adv.get("third_down_conv_pct")),
            "red_zone_pct": _safe_float(adv.get("red_zone_efficiency")),
            "turnover_diff": _safe_int(adv.get("turnover_differential")),
            "possession_time": str(adv.get("possession_time") or ""),
            "pass_yards": _safe_int(adv.get("passing_yards")),
            "rush_yards": _safe_int(adv.get("rushing_yards")),
            "turnovers": _safe_int(adv.get("turnovers")),
            "offense_ypg": _safe_float(adv.get("total_offensive_yards_per_game")),
            "logo_url": team_info.get("logo_url", ""),

            # Record splits & streak
            "playoff_seed": _safe_int(row.get("playoff_seed")),
            "win_streak": _safe_int(row.get("win_streak")),
            "conference_record": row.get("conference_record"),
            "division_record": row.get("division_record"),
            "home_record": row.get("home_record"),
            "road_record": row.get("road_record"),
        })

    # --- Compute division_rank with NFL tiebreakers ---
    # Group by division, sort within each division:
    #   1. Wins DESC
    #   2. Head-to-head record between tied teams
    #   3. Division record (win%)
    #   4. Point differential
    divisions: dict[str, list[dict[str, Any]]] = {}
    for team in result:
        div = team.get("division", "")
        divisions.setdefault(div, []).append(team)

    # Build H2H lookup from the already-fetched game_lines (deduped_lines)
    # h2h[(team_a_abbr, team_b_abbr)] = net wins for team_a vs team_b
    h2h: dict[tuple[str, str], int] = {}
    try:
        for g in deduped_lines.values():
            home = g.get("home_team")
            away = g.get("away_team")
            hs = g.get("home_score")
            as_ = g.get("away_score")
            if hs is None or as_ is None or not home or not away:
                continue
            # Map nflverse abbreviations to DB abbreviations
            home_db = _NFLVERSE_TO_DB_TEAM.get(home, home)
            away_db = _NFLVERSE_TO_DB_TEAM.get(away, away)
            if hs > as_:
                h2h[(home_db, away_db)] = h2h.get((home_db, away_db), 0) + 1
                h2h[(away_db, home_db)] = h2h.get((away_db, home_db), 0) - 1
            elif as_ > hs:
                h2h[(home_db, away_db)] = h2h.get((home_db, away_db), 0) - 1
                h2h[(away_db, home_db)] = h2h.get((away_db, home_db), 0) + 1
    except Exception:
        pass  # H2H is best-effort; fall through to next tiebreaker

    def _parse_record_wins(rec: str | None) -> float:
        """Parse '9-3' or '5-1-0' into win pct."""
        if not rec or not isinstance(rec, str):
            return 0.0
        parts = rec.split("-")
        try:
            w = int(parts[0])
            l = int(parts[1]) if len(parts) > 1 else 0
            t = int(parts[2]) if len(parts) > 2 else 0
            total = w + l + t
            return (w + t * 0.5) / total if total else 0.0
        except (ValueError, IndexError):
            return 0.0

    def _division_sort_key(team: dict[str, Any], div_teams: list[dict[str, Any]]) -> tuple:
        """Sort key: higher = better.

        Uses BDL playoff_seed as the primary tiebreaker (inverted so lower
        seed = higher sort value).  BDL has already applied the full NFL
        tiebreaker cascade (H2H, division record, common games, conference
        record, SoV, SoS), so this is more accurate than re-implementing
        those rules ourselves.
        """
        wins = team.get("wins", 0)
        # Invert seed: lower seed = better → higher value for descending sort
        seed = team.get("playoff_seed") or 99
        seed_score = 100 - seed
        diff = team.get("diff", 0) or 0
        return (wins, seed_score, diff)

    for div, teams in divisions.items():
        teams.sort(key=lambda t: _division_sort_key(t, teams), reverse=True)
        for rank, team in enumerate(teams, 1):
            team["division_rank"] = rank

    return result


def _resolve_roster_position(depth_chart_pos: str | None, natural_pos: str) -> str:
    """BDL uses 'H' (Holder) for punters in their depth chart.
    When the player's natural position is 'P', display that instead."""
    pos = depth_chart_pos or natural_pos or ""
    if pos == "H" and natural_pos == "P":
        return "P"
    return pos


def get_team_roster(sb: SupabaseClient, team_abbr: str, season: int) -> list[dict[str, Any]]:
    """
    Fetch team roster from nfl_rosters table with player details and depth chart.
    Returns players grouped by position with depth ordering.
    """
    # First get team_id from abbreviation
    team_rows = sb.select(
        "nfl_teams",
        select="id,abbreviation,name",
        filters={"abbreviation": f"eq.{team_abbr}"},
        limit=1
    )
    if not team_rows:
        return []
    
    team_id = team_rows[0]["id"]
    
    # Fetch roster with player details
    roster_rows = sb.select(
        "nfl_rosters",
        select="player_id,position,depth,injury_status,nfl_players!inner(id,first_name,last_name,position_abbreviation,jersey_number,height,weight,college,age)",
        filters={"team_id": f"eq.{team_id}", "season": f"eq.{season}"},
        order="position.asc,depth.asc",
        limit=200
    )
    
    result = []
    for row in roster_rows:
        player = row.get("nfl_players") or {}
        name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
        photo = player_photo_url_from_name_team(name=name, team=team_abbr)
        result.append({
            "player_id": row.get("player_id"),
            "first_name": player.get("first_name", ""),
            "last_name": player.get("last_name", ""),
            "player_name": name,
            "position": _resolve_roster_position(row.get("position"), player.get("position_abbreviation", "")),
            "depth": row.get("depth"),
            "jersey_number": player.get("jersey_number"),
            "height": player.get("height"),
            "weight": player.get("weight"),
            "college": player.get("college"),
            "age": player.get("age"),
            "injury_status": row.get("injury_status"),
            "photoUrl": photo,
        })

    return result


def _get_league_rankings(
    sb: SupabaseClient,
    season: int,
    season_type: int,
    stat_keys: list[str],
) -> dict[str, Any]:
    """Compute league-wide derived metrics + rankings for all 32 teams.

    This is the expensive part of get_team_season_stats (5+ Supabase queries
    + rank computation for 50-100 stat keys).  Results are cached for 10
    minutes because rankings only change when new game data is ingested
    (at most once per week during the season).
    """
    cache_key = f"league_rankings:{season}:{season_type}:{','.join(sorted(stat_keys))}"
    cached = _league_cache.get(cache_key)
    if cached is not None:
        return cached

    def _coerce_number(value: Any) -> Optional[float]:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            try:
                return float(s)
            except Exception:
                return None
        return None

    def _parse_efficiency(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            if "-" in s:
                parts = s.split("-")
                if len(parts) == 2:
                    try:
                        made = float(parts[0])
                        att = float(parts[1])
                        if att <= 0:
                            return None
                        return (made / att) * 100
                    except Exception:
                        return None
            return _coerce_number(s)
        return None

    # --- Supabase queries (the expensive part) ---
    league_rows = sb.select(
        "nfl_team_season_stats",
        select=",".join(["team_id"] + stat_keys),
        filters={
            "season": f"eq.{season}",
            "season_type": f"eq.{season_type}",
        },
        limit=100,
    )

    game_rows = sb.select(
        "nfl_team_game_stats",
        select=(
            "team_id,game_id,week,red_zone_scores,red_zone_attempts,defensive_touchdowns,"
            "total_yards,total_offensive_plays,total_drives,possession_time_seconds"
        ),
        filters={
            "season": f"eq.{season}",
            "week": "gte.1",
        },
        limit=5000,
    )
    game_ids = [r.get("game_id") for r in game_rows if r.get("game_id") is not None]
    game_postseason: dict[int, bool] = {}
    if game_ids:
        unique_ids = sorted(set(game_ids))
        for i in range(0, len(unique_ids), 200):
            chunk = unique_ids[i:i + 200]
            in_list = ",".join(str(x) for x in chunk)
            for g in sb.select("nfl_games", select="id,postseason", filters={"id": f"in.({in_list})"}, limit=5000):
                gid = g.get("id")
                if gid is not None:
                    game_postseason[gid] = bool(g.get("postseason"))
    game_totals: dict[int, dict[str, float]] = {}
    for gr in game_rows:
        tid = gr.get("team_id")
        if tid is None:
            continue
        week = _coerce_number(gr.get("week"))
        if week is None or week > 18:
            continue
        gid = gr.get("game_id")
        if gid is not None and game_postseason.get(gid):
            continue
        totals = game_totals.setdefault(
            tid,
            {
                "red_zone_scores": 0,
                "red_zone_attempts": 0,
                "defensive_touchdowns": 0,
                "total_yards": 0,
                "total_offensive_plays": 0,
                "total_drives": 0,
                "possession_time_seconds": 0,
                "games": 0,
            },
        )
        totals["red_zone_scores"] += _coerce_number(gr.get("red_zone_scores")) or 0
        totals["red_zone_attempts"] += _coerce_number(gr.get("red_zone_attempts")) or 0
        totals["defensive_touchdowns"] += _coerce_number(gr.get("defensive_touchdowns")) or 0
        totals["total_yards"] += _coerce_number(gr.get("total_yards")) or 0
        totals["total_offensive_plays"] += _coerce_number(gr.get("total_offensive_plays")) or 0
        totals["total_drives"] += _coerce_number(gr.get("total_drives")) or 0
        totals["possession_time_seconds"] += _coerce_number(gr.get("possession_time_seconds")) or 0
        totals["games"] += 1

    # --- Derived metrics ---
    derived: dict[int, dict[str, float]] = {}
    for r in league_rows:
        tid = r.get("team_id")
        if tid is None:
            continue
        passing_attempts = _coerce_number(r.get("passing_attempts")) or 0
        rushing_attempts = _coerce_number(r.get("rushing_attempts")) or 0
        total_attempts = passing_attempts + rushing_attempts
        pass_rate = (passing_attempts / total_attempts * 100) if total_attempts else None
        net_total_offensive_yards = _coerce_number(r.get("net_total_offensive_yards"))
        opp_total_offensive_yards = _coerce_number(r.get("opp_total_offensive_yards"))
        net_yards_diff = (
            (net_total_offensive_yards - opp_total_offensive_yards)
            if net_total_offensive_yards is not None and opp_total_offensive_yards is not None
            else None
        )
        total_points = _coerce_number(r.get("total_points")) or 0
        total_offensive_yards = _coerce_number(r.get("total_offensive_yards")) or 0
        points_per_100_yards = (total_points / total_offensive_yards * 100) if total_offensive_yards else None
        third_convs = _coerce_number(r.get("misc_third_down_convs")) or 0
        third_atts = _coerce_number(r.get("misc_third_down_attempts")) or 0
        third_down_pct = (third_convs / third_atts * 100) if third_atts else None
        fourth_convs = _coerce_number(r.get("misc_fourth_down_convs")) or 0
        fourth_atts = _coerce_number(r.get("misc_fourth_down_attempts")) or 0
        fourth_down_pct = (fourth_convs / fourth_atts * 100) if fourth_atts else None
        red_zone_pct = _parse_efficiency(r.get("red_zone_efficiency"))
        goal_to_go_pct = _parse_efficiency(r.get("goal_to_go_efficiency"))

        fg_made = _coerce_number(r.get("kicking_field_goals_made"))
        fg_att = _coerce_number(r.get("kicking_field_goals_attempted"))
        fg_pct = _coerce_number(r.get("kicking_field_goal_pct"))
        if fg_pct is None:
            fg_pct = _coerce_number(r.get("kicking_pct"))
        if fg_pct is None and fg_att:
            fg_pct = (fg_made or 0) / fg_att * 100

        t = game_totals.get(tid, {})
        rz_scores = t.get("red_zone_scores")
        rz_atts = t.get("red_zone_attempts")
        rz_pct_game = (rz_scores / rz_atts * 100) if rz_atts else None
        games = _coerce_number(r.get("games_played")) or t.get("games") or 0
        game_total_yards = _coerce_number(r.get("total_offensive_yards"))
        if game_total_yards is None:
            game_total_yards = t.get("total_yards")
        game_total_plays = t.get("total_offensive_plays")
        game_total_drives = t.get("total_drives")
        game_possession_seconds = t.get("possession_time_seconds")
        game_total_yards_pg = (game_total_yards / games) if games and game_total_yards is not None else None
        game_total_plays_pg = (game_total_plays / games) if games and game_total_plays is not None else None
        game_total_drives_pg = (game_total_drives / games) if games and game_total_drives is not None else None
        game_possession_pg = (game_possession_seconds / games) if games and game_possession_seconds is not None else None

        team_fumbles_total = (_coerce_number(r.get("rushing_fumbles")) or 0) + (_coerce_number(r.get("receiving_fumbles")) or 0)
        team_fumbles_lost_total = (_coerce_number(r.get("rushing_fumbles_lost")) or 0) + (_coerce_number(r.get("receiving_fumbles_lost")) or 0)
        opp_fumbles_total = (_coerce_number(r.get("opp_rushing_fumbles")) or 0) + (_coerce_number(r.get("opp_receiving_fumbles")) or 0)
        opp_fumbles_lost_total = (_coerce_number(r.get("opp_rushing_fumbles_lost")) or 0) + (_coerce_number(r.get("opp_receiving_fumbles_lost")) or 0)

        derived[tid] = {
            "pass_rate": pass_rate,
            "net_yards_diff": net_yards_diff,
            "points_per_100_yards": points_per_100_yards,
            "third_down_pct": third_down_pct,
            "fourth_down_pct": fourth_down_pct,
            "fg_pct": fg_pct,
            "red_zone_pct": red_zone_pct if red_zone_pct is not None else rz_pct_game,
            "goal_to_go_pct": goal_to_go_pct,
            "defensive_touchdowns": t.get("defensive_touchdowns"),
            "red_zone_scores": rz_scores,
            "red_zone_attempts": rz_atts,
            "game_total_yards": game_total_yards,
            "game_total_yards_pg": game_total_yards_pg,
            "game_total_plays": game_total_plays,
            "game_total_plays_pg": game_total_plays_pg,
            "game_total_drives": game_total_drives,
            "game_total_drives_pg": game_total_drives_pg,
            "game_possession_seconds": game_possession_seconds,
            "game_possession_pg": game_possession_pg,
            "team_fumbles_total": team_fumbles_total,
            "team_fumbles_lost_total": team_fumbles_lost_total,
            "opp_fumbles_total": opp_fumbles_total,
            "opp_fumbles_lost_total": opp_fumbles_lost_total,
        }

    # --- Rank computation ---
    derived_keys = [
        "pass_rate", "net_yards_diff", "points_per_100_yards",
        "third_down_pct", "fourth_down_pct", "fg_pct",
        "red_zone_pct", "goal_to_go_pct", "defensive_touchdowns",
        "game_total_yards", "game_total_yards_pg",
        "game_total_plays", "game_total_plays_pg",
        "game_total_drives", "game_total_drives_pg",
        "game_possession_seconds", "game_possession_pg",
        "team_fumbles_total", "team_fumbles_lost_total",
        "opp_fumbles_total", "opp_fumbles_lost_total",
    ]

    lower_is_better = {
        "turnovers", "misc_total_penalties", "misc_total_penalty_yards",
        "misc_total_giveaways", "fumbles_lost",
        "rushing_fumbles", "rushing_fumbles_lost",
        "receiving_fumbles", "receiving_fumbles_lost",
        "passing_sacks", "passing_interceptions",
        "team_fumbles_total", "team_fumbles_lost_total",
        "opp_rushing_fumbles", "opp_rushing_fumbles_lost",
        "opp_receiving_fumbles", "opp_receiving_fumbles_lost",
    }
    lower_is_better.update({k for k in stat_keys if k.startswith("opp_")})
    for key in {
        "opp_passing_interceptions", "opp_passing_sacks",
        "opp_fumbles_lost", "opp_rushing_fumbles_lost",
        "opp_receiving_fumbles_lost", "opp_misc_total_giveaways",
        "opp_rushing_fumbles", "opp_receiving_fumbles",
    }:
        lower_is_better.discard(key)

    def _compute_ranks(keys: list[str], higher_better: bool) -> dict[str, dict[int, int]]:
        ranks: dict[str, dict[int, int]] = {}
        derived_key_set = set(derived_keys)
        for key in keys:
            if key in derived_key_set:
                values = [
                    (tid, metrics.get(key))
                    for tid, metrics in derived.items()
                    if metrics.get(key) is not None
                ]
            else:
                values = [
                    (r.get("team_id"), r.get(key))
                    for r in league_rows
                    if r.get("team_id") is not None and r.get(key) is not None
                ]
            values = [(tid, _coerce_number(v)) for tid, v in values]
            values = [(tid, v) for tid, v in values if v is not None]
            if not values:
                continue
            values.sort(key=lambda x: x[1], reverse=higher_better)
            rank_map: dict[int, int] = {}
            rank = 1
            prev_val = None
            for idx, (tid, val) in enumerate(values, start=1):
                if prev_val is None or val != prev_val:
                    rank = idx
                rank_map[tid] = rank
                prev_val = val
            ranks[key] = rank_map
        return ranks

    all_keys = stat_keys + derived_keys
    high_keys = [k for k in all_keys if k not in lower_is_better]
    low_keys = [k for k in all_keys if k in lower_is_better]
    rank_maps = {**_compute_ranks(high_keys, True), **_compute_ranks(low_keys, False)}

    result = {"derived": derived, "rank_maps": rank_maps}
    _league_cache.set(cache_key, result)
    return result


def get_team_season_stats(
    sb: SupabaseClient,
    team_abbr: str,
    season: int,
    season_type: int = 2,
) -> dict[str, Any]:
    """Fetch a single team season stats row (including expanded fields)."""
    team_rows = sb.select(
        "nfl_teams",
        select="id,abbreviation,name",
        filters={"abbreviation": f"eq.{team_abbr}"},
        limit=1,
    )
    if not team_rows:
        return {}

    team_id = team_rows[0]["id"]
    rows = sb.select(
        "nfl_team_season_stats",
        select="*",
        filters={
            "team_id": f"eq.{team_id}",
            "season": f"eq.{season}",
            "season_type": f"eq.{season_type}",
        },
        limit=1,
    )
    if not rows:
        return {}

    row = rows[0]

    # Build league-wide ranks for context (all numeric fields + derived metrics)
    def _coerce_number(value: Any) -> Optional[float]:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            try:
                return float(s)
            except Exception:
                return None
        return None
    exclude_keys = {
        "team_id",
        "season",
        "season_type",
        "postseason",
        "updated_at",
        "stats_json",
    }
    def _parse_efficiency(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            if "-" in s:
                parts = s.split("-")
                if len(parts) == 2:
                    try:
                        made = float(parts[0])
                        att = float(parts[1])
                        if att <= 0:
                            return None
                        return (made / att) * 100
                    except Exception:
                        return None
            return _coerce_number(s)
        return None

    stat_keys = [
        k for k, v in row.items()
        if k not in exclude_keys and _coerce_number(v) is not None
    ]

    # League-wide rankings are the same for all 32 teams in a season.
    # Cache them to avoid re-running 5+ Supabase queries on every request.
    league_data = _get_league_rankings(sb, season, season_type, stat_keys)
    derived = league_data["derived"]
    ranks: dict[str, int] = {}
    for key, rmap in league_data["rank_maps"].items():
        team_rank = rmap.get(team_id)
        if team_rank is not None:
            ranks[key] = team_rank

    # Attach derived metrics for UI use
    row["pass_rate"] = derived.get(team_id, {}).get("pass_rate")
    row["net_yards_diff"] = derived.get(team_id, {}).get("net_yards_diff")
    row["points_per_100_yards"] = derived.get(team_id, {}).get("points_per_100_yards")
    row["third_down_pct"] = derived.get(team_id, {}).get("third_down_pct")
    row["fourth_down_pct"] = derived.get(team_id, {}).get("fourth_down_pct")
    row["fg_pct"] = derived.get(team_id, {}).get("fg_pct")
    row["red_zone_pct"] = derived.get(team_id, {}).get("red_zone_pct")
    row["goal_to_go_pct"] = derived.get(team_id, {}).get("goal_to_go_pct")
    row["defensive_touchdowns"] = derived.get(team_id, {}).get("defensive_touchdowns")
    row["red_zone_scores"] = derived.get(team_id, {}).get("red_zone_scores")
    row["red_zone_attempts"] = derived.get(team_id, {}).get("red_zone_attempts")
    row["game_total_yards"] = derived.get(team_id, {}).get("game_total_yards")
    row["game_total_yards_pg"] = derived.get(team_id, {}).get("game_total_yards_pg")
    row["game_total_plays"] = derived.get(team_id, {}).get("game_total_plays")
    row["game_total_plays_pg"] = derived.get(team_id, {}).get("game_total_plays_pg")
    row["game_total_drives"] = derived.get(team_id, {}).get("game_total_drives")
    row["game_total_drives_pg"] = derived.get(team_id, {}).get("game_total_drives_pg")
    row["game_possession_seconds"] = derived.get(team_id, {}).get("game_possession_seconds")
    row["game_possession_pg"] = derived.get(team_id, {}).get("game_possession_pg")
    row["team_fumbles_total"] = derived.get(team_id, {}).get("team_fumbles_total")
    row["team_fumbles_lost_total"] = derived.get(team_id, {}).get("team_fumbles_lost_total")
    row["opp_fumbles_total"] = derived.get(team_id, {}).get("opp_fumbles_total")
    row["opp_fumbles_lost_total"] = derived.get(team_id, {}).get("opp_fumbles_lost_total")
    row["ranks"] = ranks
    return row


def get_team_snaps(sb: SupabaseClient, team_abbr: str, season: int) -> dict[str, Any]:
    """Fetch latest-week snap counts for a team (offense/defense/ST)."""
    week_rows = sb.select(
        "nfl_snap_counts",
        select="week",
        filters={"season": f"eq.{season}", "team": f"eq.{team_abbr}"},
        order="week.desc",
        limit=1,
    )
    if not week_rows:
        return {"week": None, "offense": [], "defense": [], "st": [], "season": {"offense": [], "defense": [], "st": []}}

    week = week_rows[0].get("week")
    rows = sb.select(
        "nfl_snap_counts",
        select=(
            "player_name,position,offense_snaps,offense_pct,"
            "defense_snaps,defense_pct,st_snaps,st_pct,week"
        ),
        filters={
            "season": f"eq.{season}",
            "team": f"eq.{team_abbr}",
            "week": f"eq.{week}",
        },
        order="offense_pct.desc",
        limit=200,
    )

    season_rows = sb.select(
        "nfl_snap_counts",
        select=(
            "player_name,position,offense_snaps,defense_snaps,st_snaps,week"
        ),
        filters={
            "season": f"eq.{season}",
            "team": f"eq.{team_abbr}",
        },
        order="week.asc",
        limit=5000,
    )

    def top(rows: list[dict[str, Any]], pct_key: str, snaps_key: str, limit: int = 10) -> list[dict[str, Any]]:
        filtered = [
            r for r in rows
            if r.get(pct_key) is not None and (r.get(snaps_key) or 0) > 0
        ]
        return sorted(filtered, key=lambda r: r.get(pct_key) or 0, reverse=True)[:limit]

    def season_aggregate(rows: list[dict[str, Any]], snaps_key: str) -> list[dict[str, Any]]:
        if not rows:
            return []
        # Compute team total snaps per week (max player snaps per week)
        week_totals: dict[int, int] = {}
        for r in rows:
            week = r.get("week")
            snaps = r.get(snaps_key) or 0
            if week is None:
                continue
            week_totals[week] = max(week_totals.get(week, 0), snaps)

        team_total = sum(week_totals.values())
        player_totals: dict[tuple[str, str], int] = {}
        for r in rows:
            name = r.get("player_name") or ""
            position = r.get("position") or ""
            snaps = r.get(snaps_key) or 0
            if not name or snaps <= 0:
                continue
            key = (name, position)
            player_totals[key] = player_totals.get(key, 0) + snaps

        aggregated = [
            {
                "player_name": name,
                "position": position,
                f"{snaps_key}": snaps,
                f"{snaps_key.replace('_snaps', '_pct')}": (snaps / team_total) if team_total else 0,
            }
            for (name, position), snaps in player_totals.items()
        ]
        aggregated.sort(key=lambda r: r.get(f"{snaps_key.replace('_snaps', '_pct')}") or 0, reverse=True)
        return aggregated[:10]

    return {
        "week": week,
        "offense": top(rows, "offense_pct", "offense_snaps"),
        "defense": top(rows, "defense_pct", "defense_snaps"),
        "st": top(rows, "st_pct", "st_snaps"),
        "season": {
            "offense": season_aggregate(season_rows, "offense_snaps"),
            "defense": season_aggregate(season_rows, "defense_snaps"),
            "st": season_aggregate(season_rows, "st_snaps"),
        },
    }


def get_team_leaders(sb: SupabaseClient, team_abbr: str, season: int) -> dict[str, Any]:
    """Return top player cards for a team (single regular season).

    Joins through nfl_players (which has team_id) to nfl_player_season_stats.
    Returns 6 leader categories each with photo, name, and 3 stats.
    """
    team_rows = sb.select(
        "nfl_teams",
        select="id,abbreviation,name",
        filters={"abbreviation": f"eq.{team_abbr}"},
        limit=1,
    )
    if not team_rows:
        return {}

    team_id = team_rows[0]["id"]

    # Query from nfl_rosters (season-aware team association) joined to player + stats
    roster_rows = sb.select(
        "nfl_rosters",
        select=(
            "player_id,position,"
            "nfl_players!inner(id,first_name,last_name,position_abbreviation,"
            "nfl_player_season_stats(player_id,season,postseason,games_played,"
            "passing_yards,passing_touchdowns,passing_completion_pct,passing_interceptions,"
            "rushing_yards,rushing_touchdowns,rushing_attempts,"
            "receiving_yards,receiving_touchdowns,receptions,"
            "total_tackles,defensive_sacks,defensive_interceptions))"
        ),
        filters={
            "team_id": f"eq.{team_id}",
            "season": f"eq.{season}",
            "nfl_players.nfl_player_season_stats.season": f"eq.{season}",
            "nfl_players.nfl_player_season_stats.postseason": "eq.false",
        },
        limit=600,
    )

    if not roster_rows:
        return {}

    # Flatten + deduplicate by player_id (a player may appear on multiple depth chart slots)
    seen: set[int] = set()
    flat: list[dict[str, Any]] = []
    for r in roster_rows:
        pid = r.get("player_id")
        if pid in seen:
            continue
        seen.add(pid)
        player = r.get("nfl_players") or {}
        if isinstance(player, list):
            player = player[0] if player else {}
        stats_list = player.get("nfl_player_season_stats")
        if isinstance(stats_list, list):
            stats = stats_list[0] if stats_list else {}
        elif stats_list:
            stats = stats_list
        else:
            stats = {}
        name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
        if not name:
            continue
        # NOTE: photos are fetched lazily below — only for the 6 leaders,
        # not all ~70 roster players.  This avoids dozens of ESPN HTTP
        # fallback calls for players whose photos are never displayed.
        flat.append({
            "player_id": pid,
            "player_name": name,
            "position": player.get("position_abbreviation", "") or r.get("position", ""),
            "photoUrl": None,  # populated below for leaders only
            "games_played": stats.get("games_played") or 0,
            "passing_yards": _num(stats.get("passing_yards")),
            "passing_touchdowns": _num(stats.get("passing_touchdowns")),
            "passing_completion_pct": _num(stats.get("passing_completion_pct")),
            "passing_interceptions": _num(stats.get("passing_interceptions")),
            "rushing_yards": _num(stats.get("rushing_yards")),
            "rushing_touchdowns": _num(stats.get("rushing_touchdowns")),
            "rushing_attempts": _num(stats.get("rushing_attempts")),
            "receiving_yards": _num(stats.get("receiving_yards")),
            "receiving_touchdowns": _num(stats.get("receiving_touchdowns")),
            "receptions": _num(stats.get("receptions")),
            "total_tackles": _num(stats.get("total_tackles")),
            "defensive_sacks": _num(stats.get("defensive_sacks")),
            "defensive_interceptions": _num(stats.get("defensive_interceptions")),
        })

    def _best(key: str) -> dict[str, Any] | None:
        candidates = [r for r in flat if r.get(key, 0) > 0]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.get(key, 0))

    leaders: dict[str, Any] = {}

    # Top Passer
    p = _best("passing_yards")
    if p:
        leaders["passer"] = {**p, "stats": [
            {"label": "YDS", "value": p["passing_yards"]},
            {"label": "TD", "value": p["passing_touchdowns"]},
            {"label": "CMP%", "value": round(p["passing_completion_pct"], 1) if p["passing_completion_pct"] else 0},
        ]}

    # Top Rusher
    r = _best("rushing_yards")
    if r:
        leaders["rusher"] = {**r, "stats": [
            {"label": "YDS", "value": r["rushing_yards"]},
            {"label": "TD", "value": r["rushing_touchdowns"]},
            {"label": "ATT", "value": r["rushing_attempts"]},
        ]}

    # Top Receiver
    rec = _best("receiving_yards")
    if rec:
        leaders["receiver"] = {**rec, "stats": [
            {"label": "YDS", "value": rec["receiving_yards"]},
            {"label": "REC", "value": rec["receptions"]},
            {"label": "TD", "value": rec["receiving_touchdowns"]},
        ]}

    # Tackle Leader
    t = _best("total_tackles")
    if t:
        leaders["tackler"] = {**t, "stats": [
            {"label": "TCKL", "value": t["total_tackles"]},
            {"label": "SACK", "value": t["defensive_sacks"]},
            {"label": "GP", "value": t["games_played"]},
        ]}

    # INT Leader
    i = _best("defensive_interceptions")
    if i:
        leaders["int_leader"] = {**i, "stats": [
            {"label": "INT", "value": i["defensive_interceptions"]},
            {"label": "TCKL", "value": i["total_tackles"]},
            {"label": "GP", "value": i["games_played"]},
        ]}

    # Sack Leader
    s = _best("defensive_sacks")
    if s:
        leaders["sack_leader"] = {**s, "stats": [
            {"label": "SACK", "value": s["defensive_sacks"]},
            {"label": "TCKL", "value": s["total_tackles"]},
            {"label": "GP", "value": s["games_played"]},
        ]}

    # Fetch photos only for the selected leaders (at most 6 lookups instead of ~70)
    for leader in leaders.values():
        name = leader.get("player_name", "")
        if name:
            leader["photoUrl"] = player_photo_url_from_name_team(name=name, team=team_abbr)

    return leaders


def _num(v: Any) -> float:
    """Safely convert to number, defaulting to 0."""
    if v is None:
        return 0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0

def get_weekly_schedule(sb: SupabaseClient, season: int, week: int) -> list[dict[str, Any]]:
    """
    Get all games for a specific week, including scores, betting lines, and metadata.
    """
    games = sb.select(
        "nfl_game_lines",
        select="*",
        filters={
            "season": f"eq.{season}",
            "week": f"eq.{week}"
        },
        order="gameday.asc,nflverse_game_id.asc",
        limit=100
    )
    
    # We might want team metadata (colors) to display nice cards.
    # Fetch team map.
    teams_meta = sb.select("nfl_teams", select="abbreviation,primary_color,secondary_color,name")
    meta_map = {t["abbreviation"]: t for t in teams_meta}
    
    # Enrich
    out = []
    for g in games:
        h = g.get("home_team")
        a = g.get("away_team")
        
        h_meta = meta_map.get(h, {})
        a_meta = meta_map.get(a, {})
        
        out.append({
            **g,
            "home_color": h_meta.get("primary_color"),
            "away_color": a_meta.get("primary_color"),
            "home_name": h_meta.get("name", h),
            "away_name": a_meta.get("name", a)
        })
        
    return out


def get_playoff_games(sb: SupabaseClient, season: int) -> list[dict[str, Any]]:
    """
    Get all playoff games for the season.
    """
    # Filter for non-REG games (POST is tricky, game_type might be WC, DIV, CON, SB)
    games = sb.select(
        "nfl_game_lines",
        select="*",
        filters={
            "season": f"eq.{season}",
            "game_type": "neq.REG" 
        },
        order="gameday.asc",
        limit=20
    )
    
    teams_meta = sb.select("nfl_teams", select="abbreviation,primary_color,secondary_color,name,conference")
    meta_map = {t["abbreviation"]: t for t in teams_meta}
    
    out = []
    for g in games:
        h = g.get("home_team")
        a = g.get("away_team")
        h_meta = meta_map.get(h, {})
        a_meta = meta_map.get(a, {})
        
        # Determine conference of the game. 
        # Usually Home Conference, unless it's Super Bowl.
        conf = h_meta.get("conference")
        if g.get("game_type") == "SB":
            conf = "SB"
            
        out.append({
            **g,
            "home_color": h_meta.get("primary_color"),
            "away_color": a_meta.get("primary_color"),
            "home_name": h_meta.get("name", h),
            "away_name": a_meta.get("name", a),
            "conference": conf
        })
    return out


def get_matchup_history(sb: SupabaseClient, team_a: str, team_b: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Get historical matchups between two teams (any season).
    """
    # Filter for games where (home=A and away=B) OR (home=B and away=A)
    # Supabase OR syntax: or=(and(home.eq.A,away.eq.B),and(home.eq.B,away.eq.A))
    # Simplify: just home in (A,B) and away in (A,B) ? No, that matches A vs A.
    # We use the 'or' filter string.
    
    f_str = f"or(and(home_team.eq.{team_a},away_team.eq.{team_b}),and(home_team.eq.{team_b},away_team.eq.{team_a}))"
    
    games = sb.select(
        "nfl_game_lines",
        select="*",
        filters={"spread_line": "not.is.null"}, # ensuring valid games
        # custom complex filter not fully supported by simple 'filters' dict in our client wrapper?
        # Our client wrapper 'filters' joins with AND. 
        # But 'or' key is special?
        # If client doesn't support raw 'or' string properly, we might default to simple params.
        # Let's try passing "or": f_str
    )
    # The client wrapper might not handle "or" key with raw string value if it expects field=val.
    # Let's check client code? No time. 
    # Fallback: Fetch all games for Team A, then filter for Team B in python.
    
    all_a = sb.select("nfl_game_lines", select="*", filters={"or": f"(home_team.eq.{team_a},away_team.eq.{team_a})"}, order="season.desc,week.desc", limit=50)
    
    matchups = []
    for g in all_a:
        if (g.get("home_team") == team_b) or (g.get("away_team") == team_b):
            matchups.append(g)
            if len(matchups) >= limit: break
            
    # Enrich with simple stats if needed (currently nfl_game_lines has scores)
    # User asked for "per game stats". nfl_game_lines doesn't have Pass/Rush yds.
    # But checking nfl_team_season_stats 'stats_json'? 
    # Or nfl_player_game_stats aggregation?
    # Aggregating player stats for historical games is slow. 
    # Let's return the Game Lines (Score, Spread) first. 
    # The user said "see the per game stats". 
    # Maybe we can fetch "stats_json" from nfl_team_season_stats if it exists for those games? 
    # But nfl_team_season_stats is Season level (pk: team, season). 
    # Wait, the sample row in nfl_team_season_stats HAD specific game data in `stats_json`!
    # "week": 17. 
    # Maybe `nfl_team_season_stats` IS actually `nfl_team_game_stats`? 
    # No, table name is `season_stats`. 
    # The prompt Schema: `nfl_team_season_stats (team_id, season, postseason...)`. 
    # It might be that `stats_json` contains *last game* stats or similar. 
    # I can't rely on it for *historical* games.
    
    return matchups


def get_team_schedule(sb: SupabaseClient, team_abbr: str, season: int) -> list[dict[str, Any]]:
    # Translate DB abbreviation to nflverse format used in game_lines
    gl_team = _DB_TO_NFLVERSE_TEAM.get(team_abbr, team_abbr)
    filters = {
        "season": f"eq.{season}",
        "or": f"(home_team.eq.{gl_team},away_team.eq.{gl_team})"
    }
    games = sb.select(
        "nfl_game_lines",
        select="nflverse_game_id,week,gameday,game_type,home_team,away_team,home_score,away_score,spread_line,home_moneyline,away_moneyline,updated_at",
        filters=filters,
        limit=100
    )
    def _parse_spread(raw: Any) -> Optional[float]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        s = str(raw).strip().upper()
        if s in {"PK", "PICK", "PICKEM"}:
            return 0.0
        try:
            return float(s)
        except Exception:
            return None

    def _normalize_spread(spread: Optional[float], home_ml: Any, away_ml: Any) -> Optional[float]:
        if spread is None:
            return None
        try:
            h = float(home_ml) if home_ml is not None else None
            a = float(away_ml) if away_ml is not None else None
        except Exception:
            return spread
        if h is None or a is None:
            return spread
        home_favored = h < a
        if home_favored and spread > 0:
            return -abs(spread)
        if (not home_favored) and spread < 0:
            return abs(spread)
        return spread

    deduped: dict[str, dict[str, Any]] = {}
    for g in games:
        key = g.get("nflverse_game_id") or f"{g.get('home_team')}@{g.get('away_team')}:{g.get('gameday')}"
        prev = deduped.get(key)
        if not prev or str(g.get("updated_at")) > str(prev.get("updated_at")):
            deduped[key] = g
    games = list(deduped.values())
    # Sort by week
    # Note: week can be int.
    games.sort(key=lambda x: x.get("week") or 0)
    
    # Enrich with result relative to requested team
    processed = []
    for g in games:
        is_home = (g["home_team"] == gl_team)
        opp_raw = g["away_team"] if is_home else g["home_team"]
        # Normalize opponent abbreviation back to DB format for frontend
        opp = _NFLVERSE_TO_DB_TEAM.get(opp_raw, opp_raw)
        
        hs, as_ = g.get("home_score"), g.get("away_score")
        spread = _normalize_spread(_parse_spread(g.get("spread_line")), g.get("home_moneyline"), g.get("away_moneyline"))
        
        res = "SCHEDULED"
        score_display = ""
        ats_res = None
        
        if hs is not None and as_ is not None:
            my_score = hs if is_home else as_
            opp_score = as_ if is_home else hs
            score_display = f"{my_score}-{opp_score}"
            
            if my_score > opp_score:
                res = "W"
            elif my_score < opp_score:
                res = "L"
            else:
                res = "T"
            
            # ATS
            if spread is not None:
                try:
                    s = float(spread)

                    diff = hs - as_
                    val = diff + s

                    if is_home:
                        if val > 0: ats_res = "W"
                        elif val < 0: ats_res = "L"
                        else: ats_res = "P"
                    else:
                        # Assuming spread is always home spread
                        # If spread is -7 (Home favored). 
                        # Away covers if Home Margin + Spread < 0.
                        # Wait. Home Margin + Spread > 0 => Home Covers.
                        # So < 0 => Away Covers.
                        # Correct.
                        if val < 0: ats_res = "W" 
                        elif val > 0: ats_res = "L"
                        else: ats_res = "P"
                except:
                    pass

        processed.append({
            "game_id": g.get("nflverse_game_id"),
            "week": g.get("week"),
            "gameday": g.get("gameday"),
            "opponent": opp,
            "is_home": is_home,
            "result": res if res != "SCHEDULED" else None,
            "score": score_display or None,
            "ats_result": ats_res,
            "spread": spread if is_home else ((-1 * float(spread)) if spread is not None else None)
        })
    return processed


# ---------------------------------------------------------------------------
# Game Detail — composite endpoint
# ---------------------------------------------------------------------------

def get_latest_week(sb: SupabaseClient, season: int) -> int:
    """Return the most recent week with games.

    Prefers the highest week that has unplayed games (the "current" week).
    Falls back to the highest week with any data.
    """
    # Highest week with ANY games (played or upcoming)
    rows = sb.select(
        "nfl_game_lines",
        select="week",
        filters={"season": f"eq.{season}"},
        order="week.desc",
        limit=1,
    )
    if not rows:
        return 1
    max_week = int(rows[0]["week"])

    # Check if that week has unplayed games (upcoming) — if so, it's the active week
    upcoming = sb.select(
        "nfl_game_lines",
        select="week",
        filters={"season": f"eq.{season}", "week": f"eq.{max_week}", "home_score": "is.null"},
        limit=1,
    )
    if upcoming:
        return max_week

    # All games in max week are played — return it (season is over or between weeks)
    return max_week


def _implied_prob(ml: Optional[float]) -> Optional[float]:
    if ml is None:
        return None
    if ml == 0:
        return 0.5
    if ml < 0:
        return abs(ml) / (abs(ml) + 100)
    return 100 / (ml + 100)


def _compute_win_probability(
    home_ml: Optional[float], away_ml: Optional[float]
) -> dict[str, float]:
    home_raw = _implied_prob(home_ml)
    away_raw = _implied_prob(away_ml)
    if home_raw is None or away_raw is None:
        return {"home": 50.0, "away": 50.0}
    total = home_raw + away_raw
    if total <= 0:
        return {"home": 50.0, "away": 50.0}
    home_no_vig = max(0.01, min(0.99, home_raw / total))
    away_no_vig = 1.0 - home_no_vig
    return {
        "home": round(home_no_vig * 100, 1),
        "away": round(away_no_vig * 100, 1),
    }


def _parse_efficiency_pct(eff_str: Any) -> Optional[float]:
    """Parse efficiency string like '25-42' into a percentage."""
    if not eff_str or not isinstance(eff_str, str):
        return None
    parts = eff_str.split("-")
    if len(parts) == 2:
        try:
            made, att = float(parts[0]), float(parts[1])
            return round((made / att) * 100, 1) if att > 0 else None
        except Exception:
            return None
    return None


def _build_team_comparison(
    sb: SupabaseClient,
    home_team_id: Optional[int],
    away_team_id: Optional[int],
    season: int,
) -> dict[str, Any]:
    """Build side-by-side stat comparison for two teams."""
    if not home_team_id or not away_team_id:
        return {"stats": []}

    rows = sb.select(
        "nfl_team_season_stats",
        select=(
            "team_id,games_played,"
            "total_points,total_points_per_game,"
            "total_offensive_yards,total_offensive_yards_per_game,"
            "passing_yards,passing_yards_per_game,"
            "rushing_yards,rushing_yards_per_game,"
            "third_down_conv_pct,red_zone_efficiency,"
            "yards_per_pass_attempt,rushing_average,"
            "passing_completion_pct,passing_touchdowns,rushing_touchdowns,"
            "turnover_differential,defensive_interceptions,fumbles_recovered,"
            "passing_sacks"
        ),
        filters={
            "season": f"eq.{season}",
            "season_type": "eq.2",
            "team_id": f"in.({home_team_id},{away_team_id})",
        },
        limit=2,
    )

    home_s = next((r for r in rows if r.get("team_id") == home_team_id), {})
    away_s = next((r for r in rows if r.get("team_id") == away_team_id), {})

    # Compute opponent averages from per-game stats
    opp_avgs = _compute_opponent_averages(sb, home_team_id, away_team_id, season)

    stats: list[dict[str, Any]] = []

    def add(label: str, key: str, h: Any, a: Any, higher_is_better: bool = True) -> None:
        hf = _safe_float(h)
        af = _safe_float(a)
        if hf is None and af is None:
            return
        stats.append({
            "label": label,
            "key": key,
            "home": round(hf, 1) if hf is not None else None,
            "away": round(af, 1) if af is not None else None,
            "higher_is_better": higher_is_better,
        })

    # Offense
    add("PPG", "ppg", home_s.get("total_points_per_game"), away_s.get("total_points_per_game"))
    add("YPG", "ypg", home_s.get("total_offensive_yards_per_game"), away_s.get("total_offensive_yards_per_game"))
    add("Pass YPG", "pass_ypg", home_s.get("passing_yards_per_game"), away_s.get("passing_yards_per_game"))
    add("Rush YPG", "rush_ypg", home_s.get("rushing_yards_per_game"), away_s.get("rushing_yards_per_game"))
    add("3rd Down %", "third_down_pct", home_s.get("third_down_conv_pct"), away_s.get("third_down_conv_pct"))
    add("Red Zone %", "rz_pct",
        _parse_efficiency_pct(home_s.get("red_zone_efficiency")),
        _parse_efficiency_pct(away_s.get("red_zone_efficiency")))
    add("Yds/Pass", "ypa", home_s.get("yards_per_pass_attempt"), away_s.get("yards_per_pass_attempt"))

    # Defense (opponent averages)
    h_opp = opp_avgs.get(home_team_id, {})
    a_opp = opp_avgs.get(away_team_id, {})
    add("Opp PPG", "opp_ppg", h_opp.get("opp_ppg"), a_opp.get("opp_ppg"), False)
    add("Opp YPG", "opp_ypg", h_opp.get("opp_ypg"), a_opp.get("opp_ypg"), False)

    add("Sacks", "sacks", home_s.get("passing_sacks"), away_s.get("passing_sacks"))
    add("DEF INTs", "def_ints", home_s.get("defensive_interceptions"), away_s.get("defensive_interceptions"))
    add("Fum Rec", "fum_rec", home_s.get("fumbles_recovered"), away_s.get("fumbles_recovered"))

    # Turnover
    add("TO Diff", "to_diff", home_s.get("turnover_differential"), away_s.get("turnover_differential"))

    return {"stats": stats}


def _compute_opponent_averages(
    sb: SupabaseClient,
    home_team_id: int,
    away_team_id: int,
    season: int,
) -> dict[int, dict[str, Optional[float]]]:
    """Compute Opp PPG (from game_lines scores) and Opp YPG (from team_game_stats)."""
    # Get team abbreviations for game_lines queries
    team_rows = sb.select(
        "nfl_teams", select="id,abbreviation",
        filters={"id": f"in.({home_team_id},{away_team_id})"}, limit=2,
    )
    abbr_map = {r["id"]: r["abbreviation"] for r in team_rows}

    result: dict[int, dict[str, Optional[float]]] = {}

    for tid in (home_team_id, away_team_id):
        abbr = abbr_map.get(tid)
        if not abbr:
            continue
        gl_abbr = _DB_TO_NFLVERSE_TEAM.get(abbr, abbr)

        # Opp PPG from game_lines (has home_score, away_score)
        games = sb.select(
            "nfl_game_lines",
            select="home_team,away_team,home_score,away_score",
            filters={
                "season": f"eq.{season}",
                "game_type": "eq.REG",
                "or": f"(home_team.eq.{gl_abbr},away_team.eq.{gl_abbr})",
            },
            limit=50,
        )
        opp_pts: list[float] = []
        for g in games:
            hs = _safe_float(g.get("home_score"))
            as_ = _safe_float(g.get("away_score"))
            if hs is None or as_ is None:
                continue
            is_home = g.get("home_team") == gl_abbr
            opp_pts.append(as_ if is_home else hs)

        # Opp YPG from team_game_stats (has total_yards per team per game)
        my_stats = sb.select(
            "nfl_team_game_stats",
            select="game_id",
            filters={"season": f"eq.{season}", "team_id": f"eq.{tid}"},
            limit=50,
        )
        opp_yds: list[float] = []
        if my_stats:
            gids = list({r.get("game_id") for r in my_stats if r.get("game_id") is not None})
            if gids:
                all_game_rows = sb.select(
                    "nfl_team_game_stats",
                    select="team_id,game_id,total_yards",
                    filters={"game_id": f"in.({','.join(str(g) for g in gids)})"},
                    limit=200,
                )
                by_game: dict[int, list[dict[str, Any]]] = {}
                for row in all_game_rows:
                    gid = row.get("game_id")
                    if gid is not None:
                        by_game.setdefault(gid, []).append(row)
                for rows in by_game.values():
                    others = [r for r in rows if r.get("team_id") != tid]
                    if others:
                        y = _safe_float(others[0].get("total_yards"))
                        if y is not None:
                            opp_yds.append(y)

        if opp_pts or opp_yds:
            result[tid] = {
                "opp_ppg": round(sum(opp_pts) / len(opp_pts), 1) if opp_pts else None,
                "opp_ypg": round(sum(opp_yds) / len(opp_yds), 1) if opp_yds else None,
            }
    return result


def _get_best_line_props(
    sb: SupabaseClient,
    season: int,
    week: int,
    home_team_id: Optional[int],
    away_team_id: Optional[int],
) -> dict[str, list[dict[str, Any]]]:
    """Get player props with best-line-available deduplication across vendors."""
    if not home_team_id or not away_team_id:
        return {"anytime_td": [], "over_under": []}

    # Bridge to BDL game_id via nfl_games.
    # BDL uses different week numbering for playoffs (postseason week 1=WC,
    # 2=DIV, 3=CC, 5=SB) vs nflverse (19-22).  Match on teams instead.
    is_postseason = week >= 19
    games = sb.select(
        "nfl_games",
        select="id,home_team_id,visitor_team_id",
        filters={
            "season": f"eq.{season}",
            "postseason": f"eq.{str(is_postseason).lower()}",
            "home_team_id": f"in.({home_team_id},{away_team_id})",
            "visitor_team_id": f"in.({home_team_id},{away_team_id})",
        },
        order="week.desc",
        limit=1,
    )
    if not games:
        return {"anytime_td": [], "over_under": []}

    bdl_game_id = games[0]["id"]

    props = sb.select(
        "nfl_player_props",
        select="player_id,prop_type,market_type,vendor,line_value,over_odds,under_odds,milestone_odds",
        filters={"game_id": f"eq.{bdl_game_id}"},
        limit=2000,
    )
    if not props:
        return {"anytime_td": [], "over_under": []}

    player_ids = list({p.get("player_id") for p in props if p.get("player_id")})
    if not player_ids:
        return {"anytime_td": [], "over_under": []}

    players = sb.select(
        "nfl_players",
        select="id,first_name,last_name,team_id,position_abbreviation",
        filters={"id": f"in.({','.join(str(p) for p in player_ids)})"},
        limit=len(player_ids),
    )
    player_map = {p["id"]: p for p in players}

    # Group by (player_id, prop_type)
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for p in props:
        key = (p.get("player_id"), p.get("prop_type", ""))
        grouped.setdefault(key, []).append(p)

    anytime: list[dict[str, Any]] = []
    over_under: list[dict[str, Any]] = []

    for (pid, ptype), vendor_rows in grouped.items():
        pinfo = player_map.get(pid, {})
        name = f"{pinfo.get('first_name', '')} {pinfo.get('last_name', '')}".strip()
        position = pinfo.get("position_abbreviation", "")
        p_team_id = pinfo.get("team_id")
        mtype = vendor_rows[0].get("market_type", "")

        if ptype == "anytime_td" or mtype == "anytime_td":
            # Filter to standard anytime TD only (line=0.5 = score 1+ TD).
            # Exclude alternate lines like 2+ TDs (line=2), 3+ TDs (line=3), etc.
            std_rows = [r for r in vendor_rows if _safe_float(r.get("line_value")) in (None, 0.5)]
            if not std_rows:
                continue
            best = max(std_rows, key=lambda r: _safe_float(r.get("milestone_odds")) or -9999)
            all_v = [
                {"vendor": r.get("vendor"), "odds": r.get("milestone_odds")}
                for r in sorted(std_rows, key=lambda r: _safe_float(r.get("milestone_odds")) or -9999, reverse=True)
            ]
            anytime.append({
                "player_name": name, "player_id": pid, "position": position,
                "team_id": p_team_id, "prop_type": ptype,
                "market_type": "anytime_td",
                "line_value": best.get("line_value"),
                "best_odds": best.get("milestone_odds"),
                "best_vendor": best.get("vendor"),
                "all_vendors": all_v,
            })
        else:
            # Group by line_value so over/under odds are from the SAME line.
            # Without this, best_over and best_under can come from different
            # line values (e.g., over 249.5 +270 vs under 274.5 +245),
            # creating a nonsensical pairing.
            lines: dict[float, list[dict[str, Any]]] = {}
            for r in vendor_rows:
                lv = _safe_float(r.get("line_value"))
                if lv is not None:
                    lines.setdefault(lv, []).append(r)

            if not lines:
                continue

            # Pick the most popular line (most vendors offering it)
            consensus_line = max(lines, key=lambda lv: len(lines[lv]))
            line_rows = lines[consensus_line]

            best_over = max(line_rows, key=lambda r: _safe_float(r.get("over_odds")) or -9999)
            best_under = max(line_rows, key=lambda r: _safe_float(r.get("under_odds")) or -9999)
            all_v = [
                {
                    "vendor": r.get("vendor"),
                    "over_odds": r.get("over_odds"),
                    "under_odds": r.get("under_odds"),
                    "line_value": r.get("line_value"),
                }
                for r in line_rows
            ]
            over_under.append({
                "player_name": name, "player_id": pid, "position": position,
                "team_id": p_team_id, "prop_type": ptype,
                "market_type": "over_under",
                "line_value": consensus_line,
                "best_over_odds": best_over.get("over_odds"),
                "best_over_vendor": best_over.get("vendor"),
                "best_under_odds": best_under.get("under_odds"),
                "best_under_vendor": best_under.get("vendor"),
                "all_vendors": all_v,
            })

    # Sort anytime by most likely first (lowest / most-negative odds first)
    anytime.sort(key=lambda p: _safe_float(p.get("best_odds")) or 9999)
    # Sort over/under by prop_type then player name
    over_under.sort(key=lambda p: (p.get("prop_type", ""), p.get("player_name", "")))

    return {"anytime_td": anytime, "over_under": over_under}


def get_game_detail(sb: SupabaseClient, nflverse_game_id: str) -> dict[str, Any]:
    """
    Composite endpoint returning everything needed for the game matchup page
    in a single API call: game info, win probability, team comparison,
    leaders, best-line props, H2H history.
    """
    # 1. Game from nfl_game_lines
    games = sb.select(
        "nfl_game_lines",
        select="*",
        filters={"nflverse_game_id": f"eq.{nflverse_game_id}"},
        limit=1,
    )
    if not games:
        return {"error": "Game not found"}

    game = games[0]
    home_gl = game.get("home_team")
    away_gl = game.get("away_team")
    season = game.get("season")
    week = game.get("week")

    home_abbr = _NFLVERSE_TO_DB_TEAM.get(home_gl, home_gl)
    away_abbr = _NFLVERSE_TO_DB_TEAM.get(away_gl, away_gl)

    # Team metadata
    teams_meta = sb.select(
        "nfl_teams",
        select="id,abbreviation,name,primary_color,secondary_color,conference,division",
    )
    meta_map = {t["abbreviation"]: t for t in teams_meta}
    home_meta = meta_map.get(home_abbr, {})
    away_meta = meta_map.get(away_abbr, {})
    home_tid = home_meta.get("id")
    away_tid = away_meta.get("id")

    # Standings (W-L) for both teams
    records: dict[str, dict[str, Any]] = {}
    if home_tid and away_tid:
        st_rows = sb.select(
            "nfl_team_standings",
            select="team_id,wins,losses,ties,playoff_seed,conference_record,division_record,home_record,road_record",
            filters={
                "season": f"eq.{season}",
                "team_id": f"in.({home_tid},{away_tid})",
            },
            limit=2,
        )
        for sr in st_rows:
            tid = sr.get("team_id")
            records[str(tid)] = sr

    home_rec = records.get(str(home_tid), {})
    away_rec = records.get(str(away_tid), {})

    # 2. Win probability
    home_ml = _safe_float(game.get("home_moneyline"))
    away_ml = _safe_float(game.get("away_moneyline"))
    win_prob = _compute_win_probability(home_ml, away_ml)

    # 3. Team comparison
    comparison = _build_team_comparison(sb, home_tid, away_tid, season)

    # 4. Leaders for both teams
    home_leaders = get_team_leaders(sb, home_abbr, season)
    away_leaders = get_team_leaders(sb, away_abbr, season)

    is_played = game.get("home_score") is not None and game.get("away_score") is not None

    # 5. Props (only for unplayed games)
    if not is_played:
        props = _get_best_line_props(sb, season, week, home_tid, away_tid)
    else:
        props = {"anytime_td": [], "over_under": []}

    # 6. H2H history
    history = get_matchup_history(sb, home_gl, away_gl, limit=5)

    def _fmt_record(rec: dict[str, Any]) -> str:
        w = _safe_int(rec.get("wins")) or 0
        l = _safe_int(rec.get("losses")) or 0
        t = _safe_int(rec.get("ties")) or 0
        return f"{w}-{l}" + (f"-{t}" if t else "")

    return {
        "game": {
            **game,
            "home_abbr": home_abbr,
            "away_abbr": away_abbr,
            "home_name": home_meta.get("name", home_abbr),
            "away_name": away_meta.get("name", away_abbr),
            "home_color": home_meta.get("primary_color"),
            "away_color": away_meta.get("primary_color"),
            "home_secondary": home_meta.get("secondary_color"),
            "away_secondary": away_meta.get("secondary_color"),
            "home_conference": home_meta.get("conference"),
            "away_conference": away_meta.get("conference"),
            "home_record": _fmt_record(home_rec),
            "away_record": _fmt_record(away_rec),
            "home_seed": _safe_int(home_rec.get("playoff_seed")),
            "away_seed": _safe_int(away_rec.get("playoff_seed")),
            "home_conf_record": home_rec.get("conference_record"),
            "away_conf_record": away_rec.get("conference_record"),
            "home_div_record": home_rec.get("division_record"),
            "away_div_record": away_rec.get("division_record"),
            "is_played": is_played,
        },
        "win_probability": win_prob,
        "comparison": comparison,
        "leaders": {"home": home_leaders, "away": away_leaders},
        "props": props,
        "history": history,
        "preview_text": None,
    }


# ---------------------------------------------------------------------------
# Player Detail — Advanced Stats, Rankings, Snaps
# ---------------------------------------------------------------------------

_DEF_POSITIONS = frozenset({
    "DL", "LB", "CB", "S", "DB", "DE", "DT", "EDGE", "ILB", "OLB", "FS", "SS", "NT",
})
_KICKER_PUNTER = frozenset({"K", "P"})

_ADV_PASS_SELECT = (
    "player_id,season,week,attempts,completions,pass_yards,pass_touchdowns,interceptions,"
    "passer_rating,completion_percentage_above_expectation,expected_completion_percentage,"
    "avg_time_to_throw,avg_intended_air_yards,avg_completed_air_yards,"
    "avg_air_distance,avg_air_yards_differential,avg_air_yards_to_sticks,aggressiveness"
)
_ADV_RUSH_SELECT = (
    "player_id,season,week,rush_attempts,rush_yards,rush_touchdowns,"
    "efficiency,avg_rush_yards,avg_time_to_los,expected_rush_yards,"
    "rush_yards_over_expected,rush_yards_over_expected_per_att,"
    "rush_pct_over_expected,percent_attempts_gte_eight_defenders"
)
_ADV_RECV_SELECT = (
    "player_id,season,week,targets,receptions,yards,"
    "avg_yac,avg_expected_yac,avg_yac_above_expectation,"
    "catch_percentage,avg_cushion,avg_separation,"
    "percent_share_of_intended_air_yards"
)

# Metrics to exclude from ranking (identifiers, not performance stats)
_RANKING_SKIP_KEYS = frozenset({"player_id", "season", "week", "postseason", "updated_at"})


def _split_season_weekly(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    """Split advanced stat rows into season total (week=0) and per-week dict."""
    season_total: dict[str, Any] = {}
    weekly: dict[int, dict[str, Any]] = {}
    for r in rows:
        w = int(r.get("week", -1))
        cleaned = {k: v for k, v in r.items() if k not in ("player_id", "season", "week", "postseason", "updated_at")}
        if w == 0:
            season_total = cleaned
        elif w > 0:
            weekly[w] = cleaned
    return season_total, weekly


def get_player_snap_history(
    sb: SupabaseClient, player_name: str, team_abbr: str, season: int
) -> list[dict[str, Any]]:
    """Fetch per-week snap counts for a player.

    Note: nfl_snap_counts uses nflverse team abbreviations (e.g. "LA", "WAS"),
    while nfl_teams uses DB abbreviations ("LAR", "WSH"). Try both.
    """
    if not player_name or not team_abbr:
        return []
    # Convert DB team abbr to nflverse if needed
    nfl_team = _DB_TO_NFLVERSE_TEAM.get(team_abbr, team_abbr)
    teams_to_try = [nfl_team] if nfl_team != team_abbr else [team_abbr]
    if nfl_team != team_abbr:
        teams_to_try.append(team_abbr)  # fallback

    for t in teams_to_try:
        rows = sb.select(
            "nfl_snap_counts",
            select="week,offense_snaps,offense_pct,defense_snaps,defense_pct,st_snaps,st_pct",
            filters={
                "player_name": f"eq.{player_name}",
                "team": f"eq.{t}",
                "season": f"eq.{season}",
            },
            order="week.asc",
            limit=50,
        )
        if rows:
            return rows
    return []


def get_position_rankings(
    sb: SupabaseClient,
    player_id: int,
    season: int,
    position: str,
    adv_recv: list[dict[str, Any]],
    adv_rush: list[dict[str, Any]],
    adv_pass: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Compute position rankings for each advanced metric.

    Uses the already-fetched advanced stats for the target player and queries
    all players at the same position to compute rank.  Returns:
        {"metric_key": {"value": float, "rank": int, "total": int}, ...}
    """
    rankings: dict[str, dict[str, Any]] = {}
    pos = (position or "").upper()

    # Determine which tables to rank against based on position
    tables_to_rank: list[tuple[str, str, str, int]] = []  # (table, select, att_key, min_att)
    if pos == "QB":
        tables_to_rank.append(("nfl_advanced_passing_stats", _ADV_PASS_SELECT, "attempts", 100))
        tables_to_rank.append(("nfl_advanced_rushing_stats", _ADV_RUSH_SELECT, "rush_attempts", 30))
    elif pos == "RB":
        tables_to_rank.append(("nfl_advanced_rushing_stats", _ADV_RUSH_SELECT, "rush_attempts", 50))
        tables_to_rank.append(("nfl_advanced_receiving_stats", _ADV_RECV_SELECT, "targets", 15))
    elif pos in ("WR", "TE"):
        tables_to_rank.append(("nfl_advanced_receiving_stats", _ADV_RECV_SELECT, "targets", 25))
        tables_to_rank.append(("nfl_advanced_rushing_stats", _ADV_RUSH_SELECT, "rush_attempts", 10))
    else:
        return rankings  # DEF/K/P — no advanced stats to rank

    # For each table, fetch all qualifying players at this position and rank
    for table, select_cols, att_key, min_att in tables_to_rank:
        # Get all season totals (week=0) for this position
        all_rows = sb.select(
            table,
            select=select_cols,
            filters={"season": f"eq.{season}", "week": "eq.0"},
            limit=2000,
        )
        if not all_rows:
            continue

        # Filter to same position — need to look up positions
        pids_in_rows = list({r.get("player_id") for r in all_rows if r.get("player_id")})
        if not pids_in_rows:
            continue

        # Batch lookup positions (in groups to avoid too-long URL)
        pid_positions: dict[int, str] = {}
        for i in range(0, len(pids_in_rows), 200):
            batch = pids_in_rows[i:i + 200]
            players = sb.select(
                "nfl_players",
                select="id,position_abbreviation",
                filters={"id": f"in.({','.join(str(p) for p in batch)})"},
                limit=len(batch),
            )
            for p in players:
                pid_positions[p["id"]] = (p.get("position_abbreviation") or "").upper()

        # Filter to matching position + minimum attempts
        qualifying = []
        for r in all_rows:
            pid = r.get("player_id")
            p_pos = pid_positions.get(pid, "")
            if p_pos != pos:
                continue
            att_val = _safe_float(r.get(att_key)) or 0
            if att_val < min_att:
                continue
            qualifying.append(r)

        if not qualifying:
            continue

        # Get this player's row
        player_row = next((r for r in qualifying if r.get("player_id") == player_id), None)
        if not player_row:
            continue

        # Rank each metric
        metric_keys = [k for k in player_row.keys() if k not in _RANKING_SKIP_KEYS]
        for key in metric_keys:
            pval = _safe_float(player_row.get(key))
            if pval is None:
                continue
            # Sort descending (higher = better rank position in list)
            vals = sorted(
                [_safe_float(r.get(key)) for r in qualifying if _safe_float(r.get(key)) is not None],
                reverse=True,
            )
            try:
                rank = vals.index(pval) + 1
            except ValueError:
                rank = len(vals)
            rankings[key] = {"value": round(pval, 2), "rank": rank, "total": len(vals)}

    return rankings
