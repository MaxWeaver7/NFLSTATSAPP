-- =====================================================
-- DROP AND RECREATE SMASH VIEWS WITH FIXED DEFENSE LOGIC
-- =====================================================
-- 
-- This script fixes the inverted defense ranking logic.
-- Previously: High percentile (best defense) = high score (WRONG)
-- Now: High percentile (bad defense, allows more yards) = high score (CORRECT)
--
-- Run this in Supabase SQL Editor to apply the fix.
-- =====================================================

-- Drop existing views
DROP VIEW IF EXISTS public.model_qb_smash CASCADE;
DROP VIEW IF EXISTS public.model_wr_smash CASCADE;
DROP VIEW IF EXISTS public.model_rb_smash CASCADE;

-- Recreate views with fixed logic
-- The updated view files should be executed in this order:

-- 1. QB Smash View
\i view_qb_smash_scores.sql

-- 2. WR Smash View  
\i view_wr_smash_scores.sql

-- 3. RB Smash View
\i view_rb_smash_scores.sql

-- Verify the fix
SELECT 
  'QB' as position,
  player_name,
  opp_pass_ypg,
  opp_def_rank_pct,
  pass_funnel_score,
  smash_score
FROM model_qb_smash
WHERE season = 2025 AND week = 17
ORDER BY smash_score DESC
LIMIT 5;

SELECT 
  'WR' as position,
  player_name,
  opp_pass_ypg,
  opp_def_rank_pct,
  matchup_score,
  smash_score
FROM model_wr_smash
WHERE season = 2025 AND week = 17
ORDER BY smash_score DESC
LIMIT 5;

SELECT 
  'RB' as position,
  player_name,
  opp_rush_ypg,
  opp_def_rank_pct,
  run_funnel_score,
  smash_score
FROM model_rb_smash
WHERE season = 2025 AND week = 17
ORDER BY smash_score DESC
LIMIT 5;

-- Expected: Players facing worse defenses (higher YPG) should have higher funnel scores



