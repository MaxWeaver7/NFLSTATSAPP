import os
import sys
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.web import queries_supabase
from src.utils.env import load_env

def debug():
    load_env()
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    sb = SupabaseClient(SupabaseConfig(url=url, service_role_key=key))

    print("\n--- Diagnostic: Check Team Standings Data Types ---")
    try:
        rows = queries_supabase.get_team_standings(sb, season=2025)
        if rows:
            r = rows[0]
            print(f"Sample Team: {r.get('team')}")
            # Check fields user mentioned
            fields = ["win_pct", "points_for", "points_against"]
            for f in fields:
                val = r.get(f)
                print(f"Field '{f}': {val} (Type: {type(val)})")
                
            # Also check if we can fetch the 'hidden' stats from advanced table if it exists
            # The user pasted a blob that looked like nfl_team_season_stats
            print("\n--- Diagnostic: Check nfl_team_season_stats ---")
            advanced_rows = sb.select("nfl_team_season_stats", limit=1)
            if advanced_rows:
                ar = advanced_rows[0]
                print(f"Advanced Row Keys: {list(ar.keys())[:10]}...")
                print(f"3rd Down: {ar.get('third_down_conv_pct')} (Type: {type(ar.get('third_down_conv_pct'))})")
        else:
             print("No standings rows found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug()
