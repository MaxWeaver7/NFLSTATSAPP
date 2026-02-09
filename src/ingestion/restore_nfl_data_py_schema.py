#!/usr/bin/env python3
"""
Restore nfl_data_py schema tables via Supabase client.
Run this to create the non-overlapping tables for betting lines, snap counts, etc.
"""

import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.supabase_client import SupabaseClient
from dotenv import load_dotenv

load_dotenv()

def main():
    sb = SupabaseClient(
        url=os.getenv("SUPABASE_URL"),
        service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    # Read the schema file
    schema_path = Path(__file__).parent.parent / "supabase" / "nfl_data_py_schema.sql"
    with open(schema_path) as f:
        sql = f.read()
    
    # Execute via POST to Supabase SQL endpoint
    # Note: Supabase REST API doesn't directly execute DDL, so we'll use RPC or direct SQL endpoint
    # For now, let's just print instructions
    
    print("=" * 60)
    print("RESTORE NFL_DATA_PY SCHEMA")
    print("=" * 60)
    print("\nPlease run the following SQL in your Supabase SQL Editor:")
    print(f"\n{sql}\n")
    print("=" * 60)
    print("\nOr if you have psql:")
    print('psql "$DATABASE_URL" -f supabase/nfl_data_py_schema.sql')
    print("=" * 60)

if __name__ == "__main__":
    main()
