# Database Management Scripts

These scripts help you share, version, and manage your NFL database.

## 🚀 Quick Start

### Share DB with another AI/context

```bash
# Create a complete export package (DB + schema + docs + samples)
python scripts/export_db.py

# Or give it a custom name
python scripts/export_db.py "my_analysis_2024"
```

This creates:
- `exports/nfl_db_export_[timestamp]/` - directory with all files
- `exports/nfl_db_export_[timestamp].zip` - ready to share

**What the other AI gets:**
- Full DB file (ready to query immediately)
- Schema documentation (human-readable markdown)
- Sample data (JSON, for quick understanding)
- README with usage examples

### Manage DB versions (for improvements)

```bash
# List all versions
python scripts/manage_db_versions.py list

# Create a new version for your improvements
python scripts/manage_db_versions.py create v2 "Added advanced metrics tables"

# Switch to a version
python scripts/manage_db_versions.py activate v2

# Compare two versions (see schema differences)
python scripts/manage_db_versions.py compare v1 v2
```

## 📋 Scenarios

### Scenario 1: "Explain my DB to another AI"
```bash
python scripts/export_db.py
# Share the SCHEMA.md and sample_data.json from exports/
```
The AI can understand your structure without needing the full DB.

### Scenario 2: "Let another AI query my data"
```bash
python scripts/export_db.py
# Share the .zip file
```
The other AI can extract and use `nfl_data.db` directly.

### Scenario 3: "I want to add new tables/metrics"
```bash
# Save current state as v1
python scripts/manage_db_versions.py create v1 "Original FantasyAppTest data"

# Create v2 for new work
python scripts/manage_db_versions.py create v2 "Adding efficiency metrics"

# Activate v2 to work on it
python scripts/manage_db_versions.py activate v2

# Now your app uses v2, but v1 is preserved
```

### Scenario 4: "Test something risky, may need to rollback"
```bash
# Create experimental version
python scripts/manage_db_versions.py create experimental "Testing new schema"
python scripts/manage_db_versions.py activate experimental

# If it works: keep it
# If it breaks: rollback
python scripts/manage_db_versions.py activate v1
```

## 🗂️ Files Created

### Export creates:
```
exports/
  nfl_db_export_20241222_153000/
    nfl_data.db              # Full database
    schema.sql               # SQL schema definition
    SCHEMA.md                # Human-readable docs
    sample_data.json         # Sample rows
    README.md                # Usage guide
  nfl_db_export_20241222_153000.zip  # Shareable archive
```

### Version management creates:
```
data/
  nfl_data.db              # Current active (symlink or copy)
  nfl_data_v1.db           # Version 1
  nfl_data_v2.db           # Version 2
  db_versions.json         # Version registry
```

## 💡 Tips

1. **Before making schema changes**, create a version:
   ```bash
   python scripts/manage_db_versions.py create backup "Before changes"
   ```

2. **Share just the structure** (no data):
   - Export, then share only `SCHEMA.md` and `schema.sql`

3. **Keep exports small**:
   - Exports include full DB; if it's huge, consider sharing schema only

4. **Version naming**:
   - Use semantic names: `v1`, `v2`, `experimental`, `prod`, `dev`
   - Or dates: `2024-12-22`, `before_improvements`

