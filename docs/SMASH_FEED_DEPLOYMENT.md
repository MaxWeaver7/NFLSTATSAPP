# 🚀 Smash Feed Deployment Guide

## ✅ What's Been Built

### 1. **SQL Views (Supabase)** - READY ✅
- `model_wr_smash` - WR "Alpha" Model (8 factors)
- `model_rb_smash` - RB "Ground & Pound" Model (7 factors + receiving)  
- `model_qb_smash` - QB "Gunslinger" Model (7 factors)

**Files:**
- `/supabase/view_wr_smash_scores.sql`
- `/supabase/view_rb_smash_scores.sql`
- `/supabase/view_qb_smash_scores.sql`

### 2. **Python API** - READY ✅
- `smash_feed()` function in `queries_supabase.py`
- `/api/feed/smash-spots` endpoint in `server.py`
- Matchup flags generation
- 100% Supabase (no SQLite)

### 3. **React Frontend** - READY ✅
- `SmashCard.tsx` component
- `SmashFeed.tsx` page
- `/smash-feed` route added
- Navigation link in `Header.tsx`

---

## 🔧 Deployment Steps

### Step 1: Deploy SQL Views to Supabase

Open **Supabase Dashboard** → **SQL Editor** and run these files **in order**:

```sql
-- 1. WR Model
\i supabase/view_wr_smash_scores.sql

-- 2. RB Model  
\i supabase/view_rb_smash_scores.sql

-- 3. QB Model
\i supabase/view_qb_smash_scores.sql
```

**Or copy/paste directly** from each file in Supabase SQL Editor.

### Step 2: Test the Views

```sql
-- Quick test
SELECT COUNT(*) as wr_count FROM model_wr_smash WHERE season = 2025 AND week = 17;
SELECT COUNT(*) as rb_count FROM model_rb_smash WHERE season = 2025 AND week = 17;
SELECT COUNT(*) as qb_count FROM model_qb_smash WHERE season = 2025 AND week = 17;

-- Sample output
SELECT player_name, position, smash_score, team, opponent 
FROM model_wr_smash 
WHERE season = 2025 AND week = 17 
ORDER BY smash_score DESC 
LIMIT 5;
```

**Expected:** 
- WRs: 20-50 rows
- RBs: 25-50 rows  
- QBs: 15-32 rows

If you get **0 rows**, check:
1. Do games exist for Week 17 in `nfl_games`?
2. Do betting odds exist in `nfl_betting_odds` for those games?
3. Are there player season stats in `nfl_player_season_stats` for 2025?

### Step 3: Start the Backend Server

```bash
cd NFLAdvancedStats

# Make sure env vars are set
export SUPABASE_URL="your_url"
export SUPABASE_SERVICE_ROLE_KEY="your_key"

# Start server
PYTHONPATH=$(pwd) python3 -m src.web.server --host 127.0.0.1 --port 8000
```

**Verify:**
```bash
curl 'http://127.0.0.1:8000/api/feed/smash-spots?season=2025&week=17&limit=5' | jq
```

### Step 4: Access the Frontend

Open browser: **http://127.0.0.1:8000/smash-feed**

You should see:
- Season/Week filters at the top
- Grid of "Smash Cards" with:
  - Player photo
  - Position & team
  - Smash Score badge (color-coded)
  - Matchup flags ("🔥 Elite Matchup", etc.)
  - "Bet Now" button
  - Opponent info

---

## 🐛 Troubleshooting

### Issue: API returns empty `spots` array

**Fix:** The SQL views are returning 0 rows. Check:
```sql
-- Are there games for Week 17?
SELECT * FROM nfl_games WHERE season = 2025 AND week = 17 LIMIT 5;

-- Are there betting odds?
SELECT * FROM nfl_betting_odds WHERE vendor = 'DraftKings' LIMIT 5;

-- Are there player stats?
SELECT COUNT(*) FROM nfl_player_season_stats WHERE season = 2025;
```

### Issue: Server crashes with "NoneType" errors

**Fix:** This was already fixed in the code. If you still see it:
1. Pull latest changes from `queries_supabase.py`
2. Restart the server

### Issue: "Supabase not configured" error

**Fix:** Set environment variables:
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

Or create `.env` file in `NFLAdvancedStats/`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key
```

###Issue: Views created but scores are all ~50

**Fix:** This means opponent stats are NULL or percentile calculations aren't working:
1. Verify `nfl_team_season_stats` has data for 2025
2. Check that opponent defensive stats are populated (run the view CTEs separately)

---

## 📊 Model Weights Summary

### WR "Alpha" Model (100 points)
- Air Yards Share: 30%
- aDOT: 15%
- Separation: 10%
- Matchup: 15%
- QB Time to Throw: 5%
- QB Efficiency: 5%
- Game Script: 10%
- Catch Rate: 5%
- Volume: 5%

### RB "Ground & Pound" Model (100 points)
- Run Funnel: 20%
- Turnover Diff: 15%
- Favorite Status: 15%
- Efficiency (RYOE): 20%
- Discipline: 10%
- Volume: 15%
- Receiving Upside: 5%

### QB "Gunslinger" Model (100 points)
- Pocket Protection: 15%
- Shootout Potential: 25%
- Pass Funnel: 15%
- Efficiency (CPOE): 15%
- Aggressiveness: 10%
- Script: 10%
- Red Zone: 10%

---

## 🎯 Next Steps

1. **Load Real Data**: Ensure Week 17 games, betting odds, and player stats are ingested
2. **Test Live**: Access http://127.0.0.1:8000/smash-feed
3. **Adjust Filters**: Try different weeks to see historical smash spots
4. **Fine-Tune Models**: Adjust weights in SQL views based on results

---

## 📁 File Reference

**SQL:**
- `supabase/view_wr_smash_scores.sql` - WR model (412 lines)
- `supabase/view_rb_smash_scores.sql` - RB model (420 lines)
- `supabase/view_qb_smash_scores.sql` - QB model (461 lines)
- `supabase/test_smash_views.sql` - Test script (126 lines)

**Python:**
- `src/web/queries_supabase.py` - Added `smash_feed()` function (~150 lines)
- `src/web/server.py` - Added `/api/feed/smash-spots` endpoint (~15 lines)

**React:**
- `frontend/src/components/SmashCard.tsx` - Card component (~120 lines)
- `frontend/src/pages/SmashFeed.tsx` - Feed page (~110 lines)
- `frontend/src/App.tsx` - Added route (~5 lines)
- `frontend/src/components/Header.tsx` - Added nav link (~10 lines)

---

## ✨ You're All Set!

The Smash Feed is ready to go. Just deploy the SQL views and start the server! 🚀



