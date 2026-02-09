#!/usr/bin/env python3
"""
Manage multiple versions of the NFL database.
Useful when making schema changes or improvements.
"""
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
import json

DATA_DIR = Path("data")
VERSION_FILE = DATA_DIR / "db_versions.json"


def load_versions() -> dict:
    """Load version registry."""
    if VERSION_FILE.exists():
        return json.loads(VERSION_FILE.read_text())
    return {}


def save_versions(versions: dict) -> None:
    """Save version registry."""
    VERSION_FILE.write_text(json.dumps(versions, indent=2))


def list_versions() -> None:
    """List all DB versions."""
    versions = load_versions()
    
    if not versions:
        print("No versions registered yet.")
        return
    
    print("\n📚 Available database versions:\n")
    for version, info in sorted(versions.items()):
        active = " ✓ (ACTIVE)" if info.get("active") else ""
        print(f"  {version}{active}")
        print(f"    File: {info['file']}")
        print(f"    Created: {info['created']}")
        print(f"    Description: {info['description']}")
        print()


def create_version(version_name: str, description: str, from_version: str = None) -> None:
    """Create a new DB version."""
    versions = load_versions()
    
    # Determine source
    if from_version:
        if from_version not in versions:
            print(f"❌ Source version '{from_version}' not found.")
            return
        source_file = DATA_DIR / versions[from_version]["file"]
    else:
        # Use current active or nfl_data.db
        active = next((v for v, info in versions.items() if info.get("active")), None)
        source_file = DATA_DIR / (versions[active]["file"] if active else "nfl_data.db")
    
    if not source_file.exists():
        print(f"❌ Source database not found: {source_file}")
        return
    
    # Create new version file
    new_file = f"nfl_data_{version_name}.db"
    new_path = DATA_DIR / new_file
    
    if new_path.exists():
        print(f"❌ Version file already exists: {new_file}")
        return
    
    print(f"📦 Creating version '{version_name}' from {source_file.name}...")
    
    # Checkpoint WAL if it exists
    if source_file.with_suffix(".db-wal").exists():
        conn = sqlite3.connect(source_file)
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        conn.close()
    
    # Copy DB
    shutil.copy2(source_file, new_path)
    
    # Register version
    versions[version_name] = {
        "file": new_file,
        "created": datetime.now().isoformat(),
        "description": description,
        "active": False
    }
    save_versions(versions)
    
    print(f"✅ Version '{version_name}' created: {new_file}")
    print(f"   Run: python scripts/manage_db_versions.py activate {version_name}")


def activate_version(version_name: str) -> None:
    """Set a version as active (creates symlink to nfl_data.db)."""
    versions = load_versions()
    
    if version_name not in versions:
        print(f"❌ Version '{version_name}' not found.")
        return
    
    version_file = DATA_DIR / versions[version_name]["file"]
    if not version_file.exists():
        print(f"❌ Version file not found: {version_file}")
        return
    
    main_db = DATA_DIR / "nfl_data.db"
    
    # Backup current if it's not a symlink
    if main_db.exists() and not main_db.is_symlink():
        backup = main_db.with_suffix(".db.backup")
        print(f"📦 Backing up current DB to {backup.name}")
        shutil.copy2(main_db, backup)
    
    # Remove old symlink/file
    if main_db.exists() or main_db.is_symlink():
        main_db.unlink()
    
    # Create symlink (or copy on Windows)
    try:
        main_db.symlink_to(version_file.name)
        link_type = "symlink"
    except OSError:
        # Windows might not support symlinks
        shutil.copy2(version_file, main_db)
        link_type = "copy"
    
    # Update active flags
    for v in versions.values():
        v["active"] = False
    versions[version_name]["active"] = True
    save_versions(versions)
    
    print(f"✅ Version '{version_name}' activated ({link_type})")
    print(f"   nfl_data.db -> {version_file.name}")


def compare_versions(v1: str, v2: str) -> None:
    """Compare schemas of two versions."""
    versions = load_versions()
    
    if v1 not in versions or v2 not in versions:
        print("❌ One or both versions not found.")
        return
    
    file1 = DATA_DIR / versions[v1]["file"]
    file2 = DATA_DIR / versions[v2]["file"]
    
    def get_schema(db_path):
        conn = sqlite3.connect(db_path)
        schema = {}
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        for (table,) in tables:
            cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
            schema[table] = {col[1]: col[2] for col in cols}  # name: type
        conn.close()
        return schema
    
    print(f"\n📊 Comparing '{v1}' vs '{v2}':\n")
    
    schema1 = get_schema(file1)
    schema2 = get_schema(file2)
    
    all_tables = set(schema1.keys()) | set(schema2.keys())
    
    for table in sorted(all_tables):
        if table not in schema1:
            print(f"  ➕ Table '{table}' added in {v2}")
        elif table not in schema2:
            print(f"  ➖ Table '{table}' removed in {v2}")
        elif schema1[table] != schema2[table]:
            print(f"  ⚠️  Table '{table}' schema changed:")
            cols1 = set(schema1[table].keys())
            cols2 = set(schema2[table].keys())
            for col in cols2 - cols1:
                print(f"      ➕ Column added: {col}")
            for col in cols1 - cols2:
                print(f"      ➖ Column removed: {col}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/manage_db_versions.py list")
        print("  python scripts/manage_db_versions.py create <version> <description> [from_version]")
        print("  python scripts/manage_db_versions.py activate <version>")
        print("  python scripts/manage_db_versions.py compare <v1> <v2>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_versions()
    elif command == "create" and len(sys.argv) >= 4:
        version = sys.argv[2]
        description = sys.argv[3]
        from_version = sys.argv[4] if len(sys.argv) > 4 else None
        create_version(version, description, from_version)
    elif command == "activate" and len(sys.argv) >= 3:
        activate_version(sys.argv[2])
    elif command == "compare" and len(sys.argv) >= 4:
        compare_versions(sys.argv[2], sys.argv[3])
    else:
        print("❌ Invalid command or arguments.")
        sys.exit(1)

