# Complete Database Management Guide

This guide explains every method for sharing, versioning, and managing your NFL database.

---

## Table of Contents
1. [Quick Reference](#quick-reference)
2. [Method 1: Export for Sharing](#method-1-export-for-sharing)
3. [Method 2: Version Management](#method-2-version-management)
4. [Common Scenarios](#common-scenarios)
5. [Understanding What's Created](#understanding-whats-created)

---

## Quick Reference

```bash
# Share DB with another AI/context
python3 scripts/export_db.py [optional_name]

# Create a version backup
python3 scripts/manage_db_versions.py create <version_name> "<description>"

# List all versions
python3 scripts/manage_db_versions.py list

# Switch to a version
python3 scripts/manage_db_versions.py activate <version_name>

# Compare two versions
python3 scripts/manage_db_versions.py compare <v1> <v2>
```

---

## Method 1: Export for Sharing

### What It Does
Creates a **complete package** of your database that you can share with:
- Another AI in a new context/chat
- A teammate/colleague
- Another project
- For archival/backup

### How to Use

#### Basic Export (auto-named with timestamp)
```bash
cd /Users/maxweaver/.cursor/worktrees/FantasyAppTest/hrb
python3 scripts/export_db.py
```

**What happens:**
1. ✓ Checkpoints WAL (consolidates all changes into main DB)
2. ✓ Copies `data/nfl_data.db` to exports directory
3. ✓ Extracts schema as SQL
4. ✓ Generates human-readable documentation
5. ✓ Exports sample data as JSON
6. ✓ Creates README with usage instructions
7. ✓ Packages everything into a ZIP file

**Output:**
```
exports/
  nfl_db_export_20241222_153000/     ← Directory with all files
    nfl_data.db                       ← Full database (13.9 MB)
    schema.sql                        ← Schema definition
    SCHEMA.md                         ← Human-readable docs
    sample_data.json                  ← Sample rows
    README.md                         ← Usage guide
  nfl_db_export_20241222_153000.zip  ← Shareable ZIP (4.3 MB)
```

#### Custom Named Export
```bash
python3 scripts/export_db.py "2024_season_final"
```

Creates `exports/2024_season_final/` and `exports/2024_season_final.zip`

### When to Use Export

**Use Case 1: Share with AI in New Context**
- You start a new chat/context
- New AI needs to understand your data
- **Share:** Just `SCHEMA.md` and `sample_data.json` (lightweight, explains structure)

**Use Case 2: AI Needs to Query Your Data**
- AI needs to run actual SQL queries
- **Share:** The `.zip` file (contains full `nfl_data.db`)
- AI extracts and uses the DB directly

**Use Case 3: Long-term Archive**
- You want to preserve current state before major changes
- **Share:** Keep the `.zip` as backup (includes everything)

**Use Case 4: Collaborate with Someone**
- Teammate needs your data
- **Share:** The `.zip` via cloud storage, email, etc.

### What Each File Is For

| File | Purpose | Who Needs It |
|------|---------|--------------|
| `nfl_data.db` | Full database, ready to query | AI that needs to run SQL |
| `SCHEMA.md` | Human-readable table/column docs | AI that just needs to understand structure |
| `schema.sql` | SQL to recreate empty DB | Someone rebuilding from scratch |
| `sample_data.json` | Example rows from key tables | Quick reference for data format |
| `README.md` | How to use the package | Anyone receiving the export |

### Example: Sharing with Another AI

**Scenario:** You start a new Cursor chat and want the AI to help analyze your data.

```bash
# 1. Create export
python3 scripts/export_db.py "my_analysis"

# 2. In new chat, tell AI:
"I have an NFL database. Here's the structure:"
[Paste contents of exports/my_analysis/SCHEMA.md]

# If AI needs to query:
"Here's the full database:"
[Upload exports/my_analysis/nfl_data.db or share the zip]
```

---

## Method 2: Version Management

### What It Does
Creates **multiple versions** of your database so you can:
- Make changes safely (always have rollback option)
- Test experimental schemas
- Work on improvements without losing original
- Switch between versions instantly

### How to Use

#### Create Your First Version (Backup Current State)
```bash
python3 scripts/manage_db_versions.py create v1 "Original FantasyAppV2 - before improvements"
```

**What happens:**
1. ✓ Checkpoints WAL (if active)
2. ✓ Copies `data/nfl_data.db` → `data/nfl_data_v1.db`
3. ✓ Registers in `data/db_versions.json`

**Result:** You now have a safe backup. Current `nfl_data.db` is unchanged.

#### List All Versions
```bash
python3 scripts/manage_db_versions.py list
```

**Output:**
```
📚 Available database versions:

  v1 ✓ (ACTIVE)
    File: nfl_data_v1.db
    Created: 2024-12-22T15:45:00
    Description: Original FantasyAppV2 - before improvements
```

#### Create a New Version for Improvements
```bash
python3 scripts/manage_db_versions.py create v2 "Added advanced metrics tables"
```

**What happens:**
- Copies currently active version (v1) → `data/nfl_data_v2.db`
- New v2 starts as exact copy of v1
- v1 remains untouched

**Result:** You have v1 (safe backup) and v2 (for new work)

#### Switch to a Version (Make It Active)
```bash
python3 scripts/manage_db_versions.py activate v2
```

**What happens:**
1. ✓ Backs up current `nfl_data.db` (if it exists and isn't a symlink)
2. ✓ Creates symlink: `nfl_data.db` → `nfl_data_v2.db`
   - (On Windows: copies instead of symlink)
3. ✓ Your app now uses v2

**Result:** All queries now use v2. v1 is still safe.

#### Compare Two Versions (See What Changed)
```bash
python3 scripts/manage_db_versions.py compare v1 v2
```

**Output example:**
```
📊 Comparing 'v1' vs 'v2':

  ➕ Table 'player_efficiency' added in v2
  ⚠️  Table 'plays' schema changed:
      ➕ Column added: epa_per_play
      ➕ Column added: success_rate
```

### When to Use Version Management

**Scenario 1: Before Making Big Changes**
```bash
# Always do this first!
python3 scripts/manage_db_versions.py create backup "Before schema changes"

# Now make your changes...
# If something breaks:
python3 scripts/manage_db_versions.py activate backup
```

**Scenario 2: Working on Improvements**
```bash
# Create v2 for new features
python3 scripts/manage_db_versions.py create v2 "Adding efficiency metrics"
python3 scripts/manage_db_versions.py activate v2

# Work on v2 (add tables, change schema, etc.)
# Your app uses v2
# v1 remains unchanged

# When v2 is ready:
# Just keep using it! Or...
# If you want to go back:
python3 scripts/manage_db_versions.py activate v1
```

**Scenario 3: Testing Risky Changes**
```bash
# Create experimental version
python3 scripts/manage_db_versions.py create experimental "Testing new aggregation logic"
python3 scripts/manage_db_versions.py activate experimental

# Test your changes
# If it works: keep using experimental
# If it breaks:
python3 scripts/manage_db_versions.py activate v1  # Instant rollback
```

**Scenario 4: Multiple Feature Branches**
```bash
# Like git branches, but for your DB
python3 scripts/manage_db_versions.py create feature_efficiency "Efficiency metrics"
python3 scripts/manage_db_versions.py create feature_usage "Usage metrics"

# Work on one at a time
python3 scripts/manage_db_versions.py activate feature_efficiency
# ... make changes ...

# Switch to other feature
python3 scripts/manage_db_versions.py activate feature_usage
# ... make changes ...
```

### Version Naming Best Practices

```bash
# Semantic versioning
v1, v2, v3

# Feature-based
feature_advanced_stats
feature_leaderboards

# Date-based
2024-12-22
before_improvements

# Descriptive
backup_before_schema_change
working_stable
experimental_new_agg
```

---

## Common Scenarios

### Scenario A: "I want to add new tables without breaking current app"

```bash
# 1. Save current state
python3 scripts/manage_db_versions.py create v1 "Current working version"

# 2. Create v2 for improvements
python3 scripts/manage_db_versions.py create v2 "Adding new tables"
python3 scripts/manage_db_versions.py activate v2

# 3. Now add your tables to data/nfl_data.db
#    (it's pointing to v2)

# 4. Test your app with v2

# 5. If something breaks:
python3 scripts/manage_db_versions.py activate v1  # Rollback instantly

# 6. If it works:
#    Just keep using v2!
```

### Scenario B: "Share my DB with an AI in a new context"

```bash
# 1. Export
python3 scripts/export_db.py "for_analysis"

# 2. Choose what to share based on need:

# Option A: AI just needs to understand structure
#   → Share: exports/for_analysis/SCHEMA.md

# Option B: AI needs to query data
#   → Share: exports/for_analysis.zip
#   → AI extracts nfl_data.db

# Option C: AI needs sample data for context
#   → Share: exports/for_analysis/sample_data.json
```

### Scenario C: "I broke something and need to go back"

```bash
# 1. List versions to see what's available
python3 scripts/manage_db_versions.py list

# 2. Activate a working version
python3 scripts/manage_db_versions.py activate v1

# Done! Your app now uses v1
```

### Scenario D: "I want to experiment but keep current DB safe"

```bash
# 1. Create experimental version
python3 scripts/manage_db_versions.py create experiment "Testing new approach"

# 2. Activate it
python3 scripts/manage_db_versions.py activate experiment

# 3. Make wild changes
#    (current version is safe)

# 4. Test
#    - Works? Keep it!
#    - Breaks? Rollback:
python3 scripts/manage_db_versions.py activate v1
```

### Scenario E: "What changed between my versions?"

```bash
# Compare schemas
python3 scripts/manage_db_versions.py compare v1 v2

# Shows:
# - Tables added/removed
# - Columns added/removed
# - What's different
```

---

## Understanding What's Created

### Export Creates (`exports/` directory)

```
exports/
├── my_export/                  ← Directory with all files
│   ├── nfl_data.db            ← Full database (can query immediately)
│   ├── schema.sql             ← SQL to recreate empty DB
│   ├── SCHEMA.md              ← Human-readable docs
│   ├── sample_data.json       ← Example rows
│   └── README.md              ← Usage instructions
└── my_export.zip              ← Everything zipped (easiest to share)
```

**Sizes (for your current DB):**
- Directory: ~14 MB
- ZIP: ~4.3 MB (compressed)

### Version Management Creates (`data/` directory)

```
data/
├── nfl_data.db                 ← Current active (symlink to version)
├── nfl_data_v1.db             ← Version 1
├── nfl_data_v2.db             ← Version 2
├── nfl_data_experimental.db   ← Experimental version
└── db_versions.json           ← Registry of all versions
```

**db_versions.json** looks like:
```json
{
  "v1": {
    "file": "nfl_data_v1.db",
    "created": "2024-12-22T15:45:00",
    "description": "Original FantasyAppV2",
    "active": false
  },
  "v2": {
    "file": "nfl_data_v2.db",
    "created": "2024-12-22T16:30:00",
    "description": "Added advanced metrics",
    "active": true
  }
}
```

---

## Important Notes

### 1. Always Stop Server Before Version Operations
```bash
# Stop server
lsof -ti:8003 | xargs kill -9

# Then do version operations
python3 scripts/manage_db_versions.py create v2 "..."

# Restart server
python3 -m src.web.server --db data/nfl_data.db --host 127.0.0.1 --port 8003 &
```

### 2. WAL Mode and Checkpointing
SQLite uses WAL (Write-Ahead Logging) mode, creating `-wal` and `-shm` files.
- Scripts automatically checkpoint WAL before copying
- This consolidates all changes into main `.db` file
- Safe to share just the `.db` file after checkpoint

### 3. Disk Space
Each version is a full copy (~14 MB). Plan accordingly:
- 5 versions = ~70 MB
- Delete old versions you don't need:
  ```bash
  rm data/nfl_data_old.db
  # Then manually edit data/db_versions.json to remove entry
  ```

### 4. Git and Versions
- Export packages (`exports/`) are not committed to git
- Version files (`data/nfl_data_*.db`) are not committed (in `.gitignore`)
- Only `db_versions.json` could be committed (just metadata)

---

## Troubleshooting

### "Database is locked"
- **Cause:** Server is running
- **Fix:** Stop server first: `lsof -ti:8003 | xargs kill -9`

### "Version not found"
- **Cause:** Typo in version name
- **Fix:** Run `python3 scripts/manage_db_versions.py list` to see exact names

### "File already exists"
- **Cause:** Version name already used
- **Fix:** Choose different name or delete old version

### Export creates huge files
- **Normal:** Your DB has a lot of data
- **Solution:** If sharing structure only, share just `SCHEMA.md` (tiny file)

---

## Quick Command Reference Card

```bash
# EXPORT (for sharing)
python3 scripts/export_db.py                      # Auto-named export
python3 scripts/export_db.py "custom_name"       # Custom name

# VERSION MANAGEMENT
python3 scripts/manage_db_versions.py list                          # Show all versions
python3 scripts/manage_db_versions.py create v2 "description"       # Create new version
python3 scripts/manage_db_versions.py activate v2                   # Switch to version
python3 scripts/manage_db_versions.py compare v1 v2                 # Compare schemas

# USEFUL COMMANDS
ls -lh data/nfl_data*.db                          # See all DB files and sizes
ls -lh exports/                                   # See all exports
sqlite3 data/nfl_data.db ".schema"                # View current schema
sqlite3 data/nfl_data.db "SELECT COUNT(*) FROM players"  # Quick query
```

---

## Need Help?

- Read `scripts/README.md` for quick tips
- Check export package's `README.md` for sharing instructions
- Scripts create helpful error messages if something goes wrong

