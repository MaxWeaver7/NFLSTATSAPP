from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env
from src.web.queries_supabase import advanced_receiving_leaderboard

load_env()
sb = SupabaseClient(SupabaseConfig.from_env())

print("Testing advanced receiving search for 'CeeDee'...")
try:
    rows = advanced_receiving_leaderboard(
        sb, season=2025, q="CeeDee", limit=10
    )
    print(f"Found {len(rows)} results")
    for r in rows:
        print(f"{r.get('player_name')} - {r.get('player_id')}")
except Exception as e:
    print(f"ERROR: {e}")
