from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env

load_env()

try:
    sb = SupabaseClient(SupabaseConfig.from_env())
    rows = sb.select("nfl_players", select="*", filters={"last_name": "ilike.Lamb"})
    print(f"Found {len(rows)} players matching 'Lamb':")
    for r in rows:
        pid = r.get('id')
        print(f"ID: {pid} | Name: {r.get('first_name')} {r.get('last_name')} | Team: {r.get('team_id')}")
        
        # Check stats
        stats = sb.select("nfl_player_season_stats", select="*", filters={"player_id": f"eq.{pid}", "season": "eq.2025"})
        if stats:
            print(f"  -> Has 2025 stats: {stats[0].get('receiving_yards')} yards")
        else:
            print(f"  -> NO 2025 STATS found!")

except Exception as e:
    print(e)
