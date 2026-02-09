from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env
from src.web.queries_supabase import get_players_list

load_env()
sb = SupabaseClient(SupabaseConfig.from_env())

print("Testing get_players_list with q='lamb'...")
try:
    results = get_players_list(sb, season=2025, position=None, team=None, q="lamb", limit=250)
    print(f"Found {len(results)} results")
    # print first one
    if results:
        print(results[0])
except Exception as e:
    print(f"ERROR: {e}")
