
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.getcwd())
from src.database.supabase_client import SupabaseClient, SupabaseConfig

def main():
    try:
        sb = SupabaseClient(SupabaseConfig.from_env())
        print("Connected to Supabase.")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Check nfl_teams
    try:
        teams = sb.select("nfl_teams", select="id,abbreviation,name,primary_color", limit=5)
        print(f"\n--- nfl_teams ({len(teams)} sample) ---")
        for t in teams:
            print(t)
    except Exception as e:
        print(f"Error fetching nfl_teams: {e}")

    # Check nfl_game_lines for season 2024/2025
    try:
        games = sb.select("nfl_game_lines", select="week,home_team,away_team,home_score,away_score", filters={"season": "eq.2024"}, limit=5)
        print(f"\n--- nfl_game_lines 2024 ({len(games)} sample) ---")
        for g in games:
            print(g)
            
        games25 = sb.select("nfl_game_lines", select="week,home_team,away_team,home_score,away_score", filters={"season": "eq.2025"}, limit=5)
        print(f"\n--- nfl_game_lines 2025 ({len(games25)} sample) ---")
        if not games25:
            print("No games for 2025 found!")
        for g in games25:
            print(g)

    except Exception as e:
        print(f"Error fetching nfl_game_lines: {e}")

if __name__ == "__main__":
    main()
