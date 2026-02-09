#!/usr/bin/env python3
"""
Export the NFL database for sharing with other contexts/AIs.
Creates a portable package with schema, sample data, and full DB.
"""
import sqlite3
import json
import subprocess
from pathlib import Path
from datetime import datetime
import shutil

DB_PATH = Path("data/nfl_data.db")
EXPORT_DIR = Path("exports")


def checkpoint_wal(db_path: Path) -> None:
    """Checkpoint WAL to consolidate into main DB file."""
    print(f"📦 Checkpointing WAL for {db_path.name}...")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA wal_checkpoint(FULL)")
    conn.close()
    print("   ✓ WAL checkpointed")


def export_schema(db_path: Path, output_path: Path) -> None:
    """Export complete schema as SQL."""
    print("📋 Exporting schema...")
    conn = sqlite3.connect(db_path)
    schema_sql = "\n\n".join([
        row[0] for row in conn.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name"
        ).fetchall()
    ])
    output_path.write_text(schema_sql + ";\n")
    conn.close()
    print(f"   ✓ Schema saved to {output_path}")


def export_schema_docs(db_path: Path, output_path: Path) -> None:
    """Export human-readable schema documentation."""
    print("📖 Generating schema documentation...")
    conn = sqlite3.connect(db_path)
    
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    
    docs = ["# NFL Database Schema\n\n"]
    docs.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    for (table_name,) in tables:
        docs.append(f"## Table: `{table_name}`\n\n")
        
        # Get columns
        columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        docs.append("| Column | Type | Not Null | Default | Primary Key |\n")
        docs.append("|--------|------|----------|---------|-------------|\n")
        for col in columns:
            cid, name, type_, notnull, dflt_value, pk = col
            docs.append(f"| `{name}` | {type_} | {bool(notnull)} | {dflt_value or 'NULL'} | {bool(pk)} |\n")
        
        # Get row count
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        docs.append(f"\n**Row count:** {count:,}\n\n")
        
        # Sample rows
        sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 2").fetchall()
        if sample:
            docs.append("**Sample rows:**\n```\n")
            docs.append(str(sample[:2]))
            docs.append("\n```\n\n")
        
        docs.append("---\n\n")
    
    output_path.write_text("".join(docs))
    conn.close()
    print(f"   ✓ Documentation saved to {output_path}")


def export_sample_data(db_path: Path, output_dir: Path) -> None:
    """Export sample data as JSON for quick reference."""
    print("📊 Exporting sample data...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    samples = {}
    tables = ["players", "plays", "games"]
    
    for table in tables:
        try:
            rows = conn.execute(f"SELECT * FROM {table} LIMIT 10").fetchall()
            samples[table] = [dict(row) for row in rows]
        except sqlite3.OperationalError:
            samples[table] = []
    
    sample_file = output_dir / "sample_data.json"
    sample_file.write_text(json.dumps(samples, indent=2, default=str))
    conn.close()
    print(f"   ✓ Sample data saved to {sample_file}")


def create_export_package(db_path: Path, export_name: str = None) -> Path:
    """Create a complete export package."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    # Create export directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_name = export_name or f"nfl_db_export_{timestamp}"
    export_path = EXPORT_DIR / export_name
    export_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🚀 Creating export package: {export_name}\n")
    
    # 1. Checkpoint WAL
    checkpoint_wal(db_path)
    
    # 2. Copy DB file
    print("💾 Copying database file...")
    shutil.copy2(db_path, export_path / db_path.name)
    print(f"   ✓ Database copied ({db_path.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # 3. Export schema
    export_schema(db_path, export_path / "schema.sql")
    
    # 4. Export documentation
    export_schema_docs(db_path, export_path / "SCHEMA.md")
    
    # 5. Export sample data
    export_sample_data(db_path, export_path)
    
    # 6. Create README
    readme = f"""# NFL Database Export

**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Database:** {db_path.name}
**Size:** {db_path.stat().st_size / 1024 / 1024:.1f} MB

## Contents

- `{db_path.name}` - Full SQLite database (ready to query)
- `schema.sql` - Complete schema definition
- `SCHEMA.md` - Human-readable schema documentation
- `sample_data.json` - Sample rows from key tables

## Quick Start (for AI/new context)

### Option 1: Use the full DB
```bash
# Copy the DB to your project
cp {db_path.name} /path/to/your/project/data/

# Query it
sqlite3 {db_path.name} "SELECT COUNT(*) FROM players;"
```

### Option 2: Recreate from schema + data
```bash
# Create new DB from schema
sqlite3 new_db.db < schema.sql

# Then import your own data
```

### Option 3: Just understand the structure
Read `SCHEMA.md` for complete documentation of all tables and columns.

## Key Tables

- **players** - Player roster info (name, position, team)
- **plays** - Play-by-play data (all offensive plays)
- **games** - Game metadata (teams, dates, scores)

## Usage in Python

```python
import sqlite3
conn = sqlite3.connect('{db_path.name}')
conn.row_factory = sqlite3.Row

# Example: Get all WRs from 2024
players = conn.execute('''
    SELECT DISTINCT player_name, team_abbr 
    FROM players 
    WHERE position = 'WR' AND season = 2024
''').fetchall()
```

## Notes

- This DB uses WAL mode by default (you may see .db-wal/.db-shm files appear)
- All play-by-play data is from nfl_data_py (nflfastR)
- Player photos use ESPN/Sleeper IDs (see `data/db_playerids.csv` mapping)
"""
    (export_path / "README.md").write_text(readme)
    print(f"   ✓ README created")
    
    # 7. Create archive
    print("\n📦 Creating ZIP archive...")
    archive_path = EXPORT_DIR / f"{export_name}.zip"
    shutil.make_archive(str(EXPORT_DIR / export_name), 'zip', export_path)
    print(f"   ✓ Archive created: {archive_path}")
    
    print(f"\n✅ Export complete!\n")
    print(f"📁 Package location: {export_path}")
    print(f"📦 Archive: {archive_path}")
    print(f"💾 Size: {archive_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    return export_path


if __name__ == "__main__":
    import sys
    
    export_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        create_export_package(DB_PATH, export_name)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

