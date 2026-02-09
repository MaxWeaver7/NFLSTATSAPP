# AI Handoff Update (Feb 7, 2026)

## Purpose
Concise walkthrough of the current system and the *only* folders/files worth touching. Use this to avoid legacy/garbage paths. Focus next on fixing ATS totals.

## System Overview (Current)
- **Backend**: `NFLAdvancedStats/src/web/server.py`
  - Python HTTP server serving React build and API endpoints.
  - Uses Supabase/PostgREST for data access.
- **Data Access**: `NFLAdvancedStats/src/web/queries_supabase.py`
  - All team stats, ranks, snaps, leaders, and season aggregates are computed here.
  - Important: Some derived metrics are computed server-side and attached to `row`.
- **Frontend**: `NFLAdvancedStats/frontend/src/pages/TeamDetail.tsx`
  - Team detail UI with tabs and all stat cards.
  - Uses `StatCard` to show rank badges and values.
- **Frontend hooks**: `NFLAdvancedStats/frontend/src/hooks/useApi.ts`
  - API hooks for team season stats, snaps, leaders, standings.

## High-Signal Files Only
- Backend:
  - `NFLAdvancedStats/src/web/server.py`
  - `NFLAdvancedStats/src/web/queries_supabase.py`
- Frontend:
  - `NFLAdvancedStats/frontend/src/pages/TeamDetail.tsx`
  - `NFLAdvancedStats/frontend/src/components/StatCard.tsx`
  - `NFLAdvancedStats/frontend/src/hooks/useApi.ts`

Avoid legacy/other folders unless needed:
- Ignore root-level scripts except when explicitly instructed.
- Ignore old docs unless referenced in tasks.

## Key API Endpoints
- `/api/team/season-stats?team=NE&season=2025&season_type=2`
- `/api/team/snaps?team=NE&season=2025`
- `/api/team/leaders?team=NE&season=2025`
- `/api/teams/standings?season=2025`

## What Was Implemented / Fixed
- **Full team season stats mapping** (BDL) including `stats_json` and all `opp_*` fields.
- **Ranks for all numeric fields** computed in `get_team_season_stats`.
- **Derived metrics** added with ranks:
  - `pass_rate`, `net_yards_diff`, `points_per_100_yards`, `third_down_pct`, `fourth_down_pct`, `fg_pct`.
- **Red zone + defensive TDs** aggregated from `nfl_team_game_stats` and displayed.
- **Pace & Possession** aggregated from `nfl_team_game_stats`:
  - `game_total_plays`, `game_total_plays_pg`, `game_total_yards`, `game_total_yards_pg`,
    `game_total_drives`, `game_total_drives_pg`, `game_possession_seconds`, `game_possession_pg`.
- **Postseason filtering for aggregates**:
  - Use `nfl_games.postseason` to exclude postseason games from game-based aggregates.
  - Filtering is inside `get_team_season_stats`.
- **Snaps**:
  - Latest week + season-long aggregated snap share (top 10) with counts.
- **Team Leaders**:
  - Fixed to avoid inner join breaking results when player metadata missing.
- **UI**:
  - Tabs: Overview/Offense/Defense/Situational/Special/Snaps/Depth Chart/Schedule.
  - Ranks shown on all stat cards; rank badge color from green (1) to red (32).
  - Removed raw stats_json display from Overview.
  - Added pace/possession block to Offense.
  - Tuned kicking section to avoid overloading.

## Known Fumble Semantics (Important)
- BDL splits fumbles by **rushing** and **receiving**.
- These do **not** include sacks, bad snaps, or special teams.
- Therefore, **rush+rec fumbles** will not match ESPN total fumbles.
- Opponent fumble fields are *season totals vs all opponents* (not a single team).

Current labels in Defense:
- `Rush Fumbles Forced` = `opp_rushing_fumbles`
- `Rush Fumbles Recovered` = `opp_rushing_fumbles_lost`
- `Rec Fumbles Forced` = `opp_receiving_fumbles`
- `Rec Fumbles Recovered` = `opp_receiving_fumbles_lost`

## Verified: NE 2025 Regular-Season Aggregates
Computed via `nfl_team_game_stats` with postseason excluded:
- Total Plays: 1044
- Plays/G: 61.41
- Total Yards: 6650
- Yards/G: 391.18
- Total Drives: 175
- Drives/G: 10.29
- Possession: 31,921 sec
- Poss/G: 31:17

## Current Priority (User Request)
Fix ATS (Against the Spread):
- Some teams show ATS 0-0 or inconsistent counts (14/15/16 games).
- Investigate source and computation in standings pipeline.
- Do not touch legacy folders; focus in:
  - `src/web/queries_supabase.py` (standings/ATS computation)
  - `src/web/server.py` (API endpoint wiring)
  - `frontend` if display logic is wrong

## Notes for ATS Investigation
- Determine where ATS is computed (likely `get_standings` or similar in `queries_supabase.py`).
- Validate ATS counts against `nfl_game_lines` and `nfl_betting_odds` tables.
- Ensure only regular-season games are counted (exclude preseason/postseason).
- Ensure pushes are handled consistently.

---
If fixing ATS, prioritize correctness and reproducible validation checks (query outputs).