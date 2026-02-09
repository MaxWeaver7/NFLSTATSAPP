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

    print("\n--- Diagnostic: Check Derrick Henry Duplicates ---")
    try:
        # Call the ACTUAL function
        rows = queries_supabase.get_players_list(
            sb, 
            season=2025, 
            q="Henry", 
            limit=50,
            position=None,
            team=None
        )
        print(f"Found {len(rows)} entries for Henry:")
        for r in rows:
            print(f"PID: {r.get('player_id')} | {r.get('player_name')} | Tm: {r.get('team')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug()
