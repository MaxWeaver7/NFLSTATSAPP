from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env

load_env()
sb = SupabaseClient(SupabaseConfig.from_env())

print("Testing search syntax for 'nfl_players.or' filter...")
try:
    # Try filtering via 'filters' dict scoped to embedded resource
    res = sb.select(
        "nfl_player_season_stats",
        select="player_id,receiving_yards,nfl_players!inner(id,first_name,last_name)",
        filters={
            "season": "eq.2025",
            "nfl_players.or": "(first_name.ilike.*CeeDee*,last_name.ilike.*CeeDee*)"
        },
        limit=5
    )
    print(f"Success! Found {len(res)} rows")
    print(res)
except Exception as e:
    print(f"FAILED: {e}")
