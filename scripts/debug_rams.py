
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env

def get_supabase_client():
    load_env()
    config = SupabaseConfig.from_env()
    return SupabaseClient(config)

def debug_rams_data():
    sb = get_supabase_client()
    
    # 1. Get Rams ID
    print("--- Fetching Rams Team ID ---")
    rams = sb.select("nfl_teams", select="id, abbreviation, name", filters={"abbreviation": "eq.LAR"}, limit=1)
    if not rams:
        print("Rams (LAR) not found!")
        return
    rams_id = rams[0]['id']
    print(f"Rams ID: {rams_id}")

    # 2. Check Standings (ATS data source)
    print("\n--- Fetching Rams Standings (ATS Source) ---")
    standings = sb.select("nfl_team_standings", filters={"team_id": f"eq.{rams_id}", "season": "eq.2024"}, limit=1)
    if standings:
        print("Standings Row:", standings[0])
    else:
        print("No Standings found for Rams 2024.")

    # 3. Check Team Season Stats (Offense YPG source)
    print("\n--- Fetching Rams Season Stats (Offense Source) ---")
    season_stats = sb.select("nfl_team_season_stats", filters={"team_id": f"eq.{rams_id}", "season": "eq.2024"}, limit=1)
    if season_stats:
        print("Season Stats Row:", season_stats[0])
    else:
        print("No Season Stats found for Rams 2024.")

    # 4. Check Advanced Stats in queries_supabase.py logic? 
    # The user mentioned "18-18 -" -> likely means ties is missing or None.
    
    # 5. Check Roster Count
    print("\n--- Fetching Roster Count ---")
    # 5. Check Game Odds (for ATS calculation)
    print("\n--- Fetching Game Odds (ATS Spread Source) ---")
    try:
        odds = sb.select("nfl_game_odds", limit=5)
        print(f"Game Odds Count (sample): {len(odds)}")
        if odds:
            print(f"Sample Odds Row: {odds[0]}")
    except Exception as e:
        print(f"Error fetching game odds: {e}")

    # 6. Check Rosters
    print("\n--- Fetching Rosters ---")
    try:
        rosters = sb.select("nfl_rosters", filters={"team_id": f"eq.{rams_id}", "season": "eq.2024"}, limit=10)
        print(f"Roster Count (Rams 2024): {len(rosters)}")
        if rosters:
            print(f"Sample Roster Row: {rosters[0]}")
    except Exception as e:
        print(f"Error fetching rosters: {e}")

    # 7. Check actual column names in team_season_stats
    print("\n--- Verifying nfl_team_season_stats Column Names ---")
    if season_stats:
        print("Available Columns:", list(season_stats[0].keys()))

if __name__ == "__main__":
    debug_rams_data()
