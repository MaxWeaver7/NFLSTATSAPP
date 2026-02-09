# Smash Score Views - Execution Guide

## Phase 1: Create SQL Views in Supabase ✅ CREATED

**Steps to Deploy:**

1. Open **Supabase Dashboard** → SQL Editor
2. Run these files in order:
   ```sql
   -- File 1: WR Model
   \i view_wr_smash_scores.sql
   
   -- File 2: RB Model  
   \i view_rb_smash_scores.sql
   
   -- File 3: QB Model
   \i view_qb_smash_scores.sql
   ```

3. **Test the views:**
   ```sql
   \i test_smash_views.sql
   ```

4. **Expected Output:**
   - `model_wr_smash`: 20-40 WRs with scores 40-95
   - `model_rb_smash`: 25-50 RBs with scores 35-90
   - `model_qb_smash`: 15-32 QBs with scores 45-95

---

## Phase 2: Python API Layer (NEXT)

### File: `src/web/queries_supabase.py`

**New Function:**
```python
def smash_feed(
    sb: SupabaseClient, 
    season: int, 
    week: int, 
    limit: int = 50
) -> list[dict[str, Any]]:
    """
    Unified Smash Spot feed across all positions.
    Returns top betting opportunities sorted by smash_score.
    """
```

**Implementation:**
- Query all 3 views
- Union results
- Sort by `smash_score DESC`
- Generate matchup flags for top 3 scoring factors
- Return top N results

### File: `src/web/server.py`

**New Endpoint:**
```python
GET /api/feed/smash-spots?season=2025&week=17&limit=50
```

---

## Phase 3: Frontend Components (AFTER API)

### Components to Create:
1. `SmashCard.tsx` - Individual bet card
2. `SmashFeed.tsx` - Grid layout page
3. Update `main.tsx` routing
4. Update `Header.tsx` navigation

---

## Data Quality Checks

Before deploying, verify:

- [ ] Week 17 games exist in `nfl_games`
- [ ] DraftKings odds in `nfl_betting_odds`
- [ ] Team defensive stats populated for 2025
- [ ] Player props available (optional, views handle NULL)
- [ ] No SQL syntax errors in views

---

## Troubleshooting

**If views return 0 rows:**
1. Check `upcoming_games` CTE - are games scheduled for Week 17?
2. Verify `vendor = 'DraftKings'` odds exist
3. Check minimum thresholds (targets >= 20, attempts >= 30, etc.)

**If smash_scores all near 50:**
1. Verify opponent stats are populated (not all NULL)
2. Check PERCENT_RANK calculations (need multiple teams for percentiles)
3. Validate betting odds are being cast to NUMERIC correctly




