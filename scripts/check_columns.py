import os
import json
from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env

load_env()

def check():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    sb = SupabaseClient(SupabaseConfig(url=url, service_role_key=key))
    
    # Introspect columns for nfl_team_season_stats
    # Supabase (PostgREST) exposes openapi usually, or we can just try to select * and look at keys,
    # but I want to know what columns EXIST to know what to ALTER ADD.
    # I'll just check a single row again and list ALL keys.
    
    try:
        res = sb.select("nfl_team_season_stats", select="*", limit=1)
        if res:
            print("Columns found:", list(res[0].keys()))
        else:
            print("Table empty or no access.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
