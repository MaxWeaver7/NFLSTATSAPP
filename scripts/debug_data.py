import os
import json
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env

def check_data():
    load_env()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return

    sb = SupabaseClient(SupabaseConfig(url=url, service_role_key=key))

    print("--- Checking nfl_team_season_stats for 2025 ---")
    try:
        stats = sb.select("nfl_team_season_stats", select="*", filters={"season": "eq.2025"}, limit=5)
        print(f"Found {len(stats)} rows.")
        if stats:
            print("Sample row:", json.dumps(stats[0], indent=2, default=str))
    except Exception as e:
        print(f"Error querying nfl_team_season_stats: {e}")

    print("\n--- Checking nfl_game_lines for 2025 ---")
    try:
        games = sb.select("nfl_game_lines", select="*", filters={"season": "eq.2025"}, limit=5)
        print(f"Found {len(games)} rows.")
        if games:
            print("Sample row:", json.dumps(games[0], indent=2, default=str))
    except Exception as e:
        print(f"Error querying nfl_game_lines: {e}")

    print("\n--- Checking nfl_player_game_stats for 2025 ---")
    try:
        p_stats = sb.select("nfl_player_game_stats", select="*", filters={"season": "eq.2025"}, limit=5)
        print(f"Found {len(p_stats)} rows.")
        if p_stats:
            print("Sample row:", json.dumps(p_stats[0], indent=2, default=str))
    except Exception as e:
        print(f"Error querying nfl_player_game_stats: {e}")

if __name__ == "__main__":
    check_data()
