import logging
from typing import Any, Iterable, Optional, Dict
from datetime import datetime, timezone
from src.database.supabase_client import SupabaseClient
from src.ingestion.balldontlie_client import BallDontLieNFLClient, BallDontLieError

logger = logging.getLogger(__name__)

# 1. Define Priority List (1 = Highest Priority)
VENDOR_PRIORITY = {
    "draftkings": 1,
    "fanduel": 2,
    "betmgm": 3,
    "bet365": 4,
    "betway": 5
}

# Allowed props map (API Key -> DB Column)
PROP_MAP = {
    "passing_yards": "player_pass_yds",
    "rushing_yards": "player_rush_yds",
    "receiving_yards": "player_rec_yds",
    "passing_tds": "player_pass_tds",
    "passing_attempts": "player_pass_att",
    "rushing_attempts": "player_rush_att",
    "rushing_receiving_yards": "player_rush_rec_yds",
    "longest_rush": "player_longest_rush",
    "longest_reception": "player_longest_rec",
    # No milestones per request
}

def _chunked(items: Iterable[Any], size: int) -> Iterable[list[Any]]:
    buf = []
    for it in items:
        buf.append(it)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

def _dedupe(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    seen = {}
    for r in rows:
        k = tuple(r.get(f) for f in keys)
        seen[k] = r
    return list(seen.values())

def is_valid_prop(row: dict[str, Any]) -> bool:
    # 1. Vendor Check: Only allow vendors in our priority list
    vendor = (row.get("vendor") or row.get("bookmaker") or "").lower()
    if vendor not in VENDOR_PRIORITY:
        return False
        
    # 2. Defense check (skip DST) - Note: API may not have position data in props endpoint
    # Removing this check since player object is no longer returned
        
    # 3. Market Type: STRICT Over/Under Only
    market = row.get("market") or {}
    m_type = market.get("type")
    
    if m_type == "over_under":
        return True
        
    return False

def map_player_prop(row: dict[str, Any]) -> dict[str, Any]:
    game_id = row.get("game_id")
    raw_type = row.get("prop_type")
    db_prop_type = PROP_MAP.get(raw_type)
    
    if not db_prop_type:
        return None 
    
    # player_id is at root level in API response
    player_id = row.get("player_id")
    if not player_id:
        # Skip props without valid player_id
        return None

    market = row.get("market") or {}
    vendor = (row.get("vendor") or row.get("bookmaker") or "").lower()
    
    return {
        "id": row.get("id"),
        "game_id": game_id,
        "player_id": player_id,
        "vendor": vendor,
        "prop_type": db_prop_type,
        "market_type": market.get("type"),
        "line_value": row.get("line_value"),
        "over_odds": market.get("over_odds"),
        "under_odds": market.get("under_odds"),
        "updated_at": row.get("updated_at") or datetime.now(timezone.utc).isoformat()
    }

def _get_best_props(props_list: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Deduplicates props. If multiple vendors offer the same prop for the same player,
    keep ONLY the one with the highest vendor priority (DraftKings > FanDuel > etc).
    """
    best_map: Dict[str, dict] = {} # Key: "player_id|prop_type"

    for row in props_list:
        # Validate first
        if not is_valid_prop(row):
            continue
            
        mapped = map_player_prop(row)
        if not mapped:
            continue

        player_id = mapped["player_id"]
        prop_type = mapped["prop_type"]
        vendor = mapped["vendor"]
        
        # Unique Key for this prop
        key = f"{player_id}|{prop_type}"
        
        current_priority = VENDOR_PRIORITY.get(vendor, 99)
        
        # Logic: If we haven't seen this prop, OR this vendor is higher priority (lower number)
        # than what we have stored, replace it.
        if key not in best_map:
            best_map[key] = mapped
        else:
            existing_vendor = best_map[key]["vendor"]
            existing_priority = VENDOR_PRIORITY.get(existing_vendor, 99)
            
            if current_priority < existing_priority:
                best_map[key] = mapped # Upgrade to better vendor

    return list(best_map.values())

def map_team_season_stats(row: dict[str, Any], season: int) -> dict[str, Any]:
    # Inject season manually to avoid null errors
    row_season = row.get("season") or season
    t = row.get("team") or {}
    
    return {
        "team_id": row.get("team_id") or t.get("id"),
        "season": int(row_season),
        "postseason": False,
        "opp_rushing_yards": row.get("opp_rushing_yards"),
        "opp_rushing_yards_per_game": row.get("opp_rushing_yards_per_game"),
        "opp_passing_yards": row.get("opp_passing_yards"),
        "opp_total_points": row.get("opp_total_points"),
        "opp_sacks": row.get("opp_sacks"),
        "stats_json": row, # Dump full data for safety
        "updated_at": row.get("updated_at") or datetime.now(timezone.utc).isoformat()
    }

def map_injury(r: dict[str, Any]) -> dict[str, Any]:
    p = r.get("player") or {}
    return {
        "player_id": p.get("id") or r.get("player_id"),
        "status": r.get("status"),
        "comment": r.get("comment"),
        "injury_date": r.get("date"),
        "updated_at": r.get("updated_at") or datetime.now(timezone.utc).isoformat()
    }

def map_standing(r: dict[str, Any]) -> dict[str, Any]:
    t = r.get("team") or {}
    return {
        "team_id": t.get("id"),
        "season": r.get("season"),
        "wins": r.get("wins"),
        "losses": r.get("losses"),
        "ties": r.get("ties"),
        "playoff_seed": r.get("playoff_seed"),
        "points_for": r.get("points_for"),
        "points_against": r.get("points_against"),
        "updated_at": r.get("updated_at") or datetime.now(timezone.utc).isoformat()
    }

def map_game_odds(r: dict[str, Any]) -> dict[str, Any]:
    """Map game-level betting odds (spread, total) from DraftKings only"""
    return {
        "id": r.get("id"),
        "game_id": r.get("game_id"),
        "vendor": "draftkings",
        "spread_home_value": r.get("spread_home_value"),
        "spread_home_odds": r.get("spread_home_odds"),
        "spread_away_value": r.get("spread_away_value"),
        "spread_away_odds": r.get("spread_away_odds"),
        "total_value": r.get("total_value"),
        "total_over_odds": r.get("total_over_odds"),
        "total_under_odds": r.get("total_under_odds"),
        "moneyline_home_odds": r.get("moneyline_home_odds"),
        "moneyline_away_odds": r.get("moneyline_away_odds"),
        "updated_at": r.get("updated_at") or datetime.now(timezone.utc).isoformat()
    }

def ingest_extras(
    *,
    supabase: SupabaseClient,
    bdl: BallDontLieNFLClient,
    seasons: list[int],
    dates: Optional[list[str]] = None,
    batch_size: int = 500,
) -> dict[str, int]:
    logger.info(f"Starting extras ingestion for seasons={seasons}...")
    
    stats_upserted = 0
    standings_upserted = 0
    injuries_upserted = 0
    props_upserted = 0
    game_odds_upserted = 0

    # 1. Fetch Games for IDs (Season wide or specific dates)
    game_ids = []
    try:
        logger.info("Fetching game IDs...")
        all_games = list(bdl.iter_games(seasons=seasons))
        
        if dates:
            wanted = set(dates)
            games = [g for g in all_games if str(g.get("date","")).split("T")[0] in wanted]
        else:
            games = all_games
            
        game_ids = [g["id"] for g in games if g.get("id")]
        logger.info(f"Found {len(game_ids)} games to process")
    except Exception as e:
        logger.error(f"Failed to fetch games: {e}")

    for season in seasons:
        # Team Stats
        try:
            rows = []
            for r in bdl.iter_team_season_stats(season=season):
                rows.append(map_team_season_stats(r, season))
            
            if rows:
                deduped = _dedupe(rows, ["team_id", "season", "postseason"])
                for chunk in _chunked(deduped, batch_size):
                    stats_upserted += supabase.upsert("nfl_team_season_stats", chunk, on_conflict="team_id,season,postseason")
        except Exception as e:
            logger.error(f"Team stats error: {e}")

        # Standings
        try:
            for chunk in _chunked((map_standing(r) for r in bdl.iter_standings(season=season)), batch_size):
                standings_upserted += supabase.upsert("nfl_team_standings", chunk, on_conflict="team_id,season")
        except Exception as e:
             logger.error(f"Standings error: {e}")

        # Player Props (Game Loop with Priority Filter)
        if game_ids:
            logger.info(f"Processing props for {len(game_ids)} games...")
            # We request ALL priority vendors from the API
            api_vendors = list(VENDOR_PRIORITY.keys())
            
            for i, gid in enumerate(game_ids):
                try:
                    # 1. Fetch RAW props from all accepted vendors
                    raw_props = list(bdl.iter_player_props(game_id=gid, vendors=api_vendors))
                    
                    # 2. Filter & Deduplicate (Keep only the single best line per prop)
                    best_props = _get_best_props(raw_props)
                    
                    if best_props:
                        supabase.upsert("nfl_player_props", best_props, on_conflict="id")
                        props_upserted += len(best_props)
                    
                    if (i+1) % 10 == 0:
                        logger.info(f"Processed {i+1}/{len(game_ids)} games. Props: {props_upserted}")
                except Exception as e:
                    logger.error(f"Props error game {gid}: {e}")
        
        # Game Odds (Spreads, Totals) - DraftKings only
        if game_ids:
            logger.info(f"Fetching game odds (spreads/totals) for {len(game_ids)} games...")
            try:
                # Fetch odds for all games at once
                game_odds_raw = list(bdl.iter_betting_odds(game_ids=game_ids))
                logger.info(f"Fetched {len(game_odds_raw)} raw odds records")
                
                # Filter for DraftKings only
                dk_odds = [map_game_odds(r) for r in game_odds_raw if (r.get("vendor") or "").lower() == "draftkings"]
                
                if dk_odds:
                    # Insert/update game odds - using id as natural key
                    supabase.upsert("nfl_betting_odds", dk_odds, on_conflict="id")
                    game_odds_upserted += len(dk_odds)
                    logger.info(f"Upserted {len(dk_odds)} DraftKings game odds")
            except Exception as e:
                logger.error(f"Game odds error: {e}")

    # Injuries
    try:
        for chunk in _chunked((map_injury(r) for r in bdl.iter_injuries()), batch_size):
            injuries_upserted += supabase.upsert("nfl_injuries", chunk, on_conflict="player_id")
    except Exception as e:
        logger.error(f"Injuries error: {e}")

    return {
        "team_season_stats": stats_upserted,
        "standings": standings_upserted,
        "injuries": injuries_upserted,
        "player_props": props_upserted,
        "game_odds": game_odds_upserted
    }