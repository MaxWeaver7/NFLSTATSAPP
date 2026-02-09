from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env
from src.web.queries_supabase import get_players_list

load_env()
sb = SupabaseClient(SupabaseConfig.from_env())

print("Testing search logic for 'CeeDee'...")
try:
    results = get_players_list(sb, season=2025, position=None, team=None, q="CeeDee", limit=10)
    print(f"Found {len(results)} results")
    for r in results:
        print(r.get("player_name"))
except Exception as e:
    print(f"ERROR: {e}")
