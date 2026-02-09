-- ======================================================================================
-- SMASH SCORE VIEWS - TEST SCRIPT
-- ======================================================================================
-- Run this in Supabase SQL Editor to test all 3 views after creation
-- Expected: Each view should return 10-30 rows for Week 17, 2025
-- ======================================================================================

-- Test 1: WR Smash Scores
SELECT 
  player_name,
  team,
  opponent,
  smash_score,
  air_share_pct,
  adot,
  catch_rate,
  qb_comp_pct,
  opp_pass_ypg,
  game_total
FROM model_wr_smash
WHERE season = 2025 AND week = 17
ORDER BY smash_score DESC
LIMIT 10;

-- Test 2: RB Smash Scores
SELECT 
  player_name,
  team,
  opponent,
  smash_score,
  rush_att_per_game,
  touches_per_game,
  ryoe_per_att,
  opp_rush_ypg,
  is_favorite,
  spread
FROM model_rb_smash
WHERE season = 2025 AND week = 17
ORDER BY smash_score DESC
LIMIT 10;

-- Test 3: QB Smash Scores
SELECT 
  player_name,
  team,
  opponent,
  smash_score,
  pass_att_per_game,
  cpoe,
  aggressiveness,
  opp_pass_ypg,
  game_total,
  is_underdog
FROM model_qb_smash
WHERE season = 2025 AND week = 17
ORDER BY smash_score DESC
LIMIT 10;

-- Test 4: Combined Feed (Top 20 across all positions)
SELECT 
  'WR' AS position_type,
  player_name,
  team,
  opponent,
  smash_score
FROM model_wr_smash
WHERE season = 2025 AND week = 17

UNION ALL

SELECT 
  'RB' AS position_type,
  player_name,
  team,
  opponent,
  smash_score
FROM model_rb_smash
WHERE season = 2025 AND week = 17

UNION ALL

SELECT 
  'QB' AS position_type,
  player_name,
  team,
  opponent,
  smash_score
FROM model_qb_smash
WHERE season = 2025 AND week = 17

ORDER BY smash_score DESC
LIMIT 20;

-- Test 5: Validate data availability
SELECT 
  'Games for Week 17' AS metric,
  COUNT(*)::text AS value
FROM nfl_games
WHERE season = 2025 AND week = 17 AND postseason = false

UNION ALL

SELECT 
  'Betting odds available',
  COUNT(DISTINCT game_id)::text
FROM nfl_betting_odds
WHERE game_id IN (SELECT id FROM nfl_games WHERE season = 2025 AND week = 17)

UNION ALL

SELECT 
  'Team defensive stats',
  COUNT(*)::text
FROM nfl_team_season_stats
WHERE season = 2025 AND postseason = false

UNION ALL

SELECT 
  'Player props (DK)',
  COUNT(*)::text
FROM nfl_player_props
WHERE vendor = 'DraftKings'
  AND game_id IN (SELECT id FROM nfl_games WHERE season = 2025 AND week = 17);



