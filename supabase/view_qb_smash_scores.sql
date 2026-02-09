CREATE OR REPLACE VIEW public.model_qb_smash AS

WITH upcoming_games AS (
  SELECT 
    g.id AS game_id,
    g.season,
    g.week,
    g.home_team_id,
    g.visitor_team_id,
    g.date,
    g.status
  FROM nfl_games g
  WHERE g.postseason = false
    AND g.season = 2025
    AND g.week = 17
    AND g.status != 'Final'
),

qb_season_stats AS (
  SELECT
    p.id AS player_id,
    p.first_name,
    p.last_name,
    p.position_abbreviation,
    p.team_id,
    ss.passing_attempts,
    ss.passing_completions,
    ss.passing_yards,
    ss.passing_touchdowns,
    ss.passing_interceptions,
    ss.qb_rating,
    ss.games_played,
    aps.completion_percentage_above_expectation AS cpoe,
    aps.completion_percentage AS comp_pct,
    aps.aggressiveness,
    aps.avg_time_to_throw,
    aps.avg_intended_air_yards AS avg_depth_of_target,
    aps.avg_completed_air_yards,
    aps.passer_rating AS adv_passer_rating,
    CASE WHEN ss.games_played > 0 THEN ss.passing_attempts::numeric / ss.games_played ELSE 0 END AS pass_att_per_game,
    CASE WHEN ss.passing_attempts > 0 THEN ss.passing_yards::numeric / ss.passing_attempts ELSE 0 END AS ypa,
    CASE WHEN ss.passing_interceptions > 0 THEN ss.passing_touchdowns::numeric / ss.passing_interceptions ELSE ss.passing_touchdowns::numeric END AS td_int_ratio
  FROM nfl_players p
  INNER JOIN nfl_player_season_stats ss ON ss.player_id = p.id AND ss.season = 2025 AND ss.postseason = false
  LEFT JOIN nfl_advanced_passing_stats aps ON aps.player_id = p.id AND aps.season = 2025 AND aps.week = 0 AND aps.postseason = false
  WHERE p.position_abbreviation = 'QB' AND ss.passing_attempts >= 100
),

opponent_pass_defense_base AS (
  SELECT DISTINCT ON (ts.team_id)
    ts.team_id,
    ts.opp_passing_yards_per_game,
    ts.opp_net_passing_yards,
    ts.opp_sacks_forced AS sacks_generated,
    ts.opp_interceptions_forced,
    ts.opp_points_per_game,
    ts.opp_red_zone_scoring_pct
  FROM nfl_team_season_stats ts
  WHERE ts.season = 2025 AND ts.postseason = false
),

opponent_pass_defense AS (
  SELECT
    team_id,
    opp_passing_yards_per_game,
    opp_net_passing_yards,
    sacks_generated,
    opp_interceptions_forced,
    opp_points_per_game,
    opp_red_zone_scoring_pct,
    PERCENT_RANK() OVER (ORDER BY opp_passing_yards_per_game ASC) AS pass_def_funnel_percentile,
    PERCENT_RANK() OVER (ORDER BY sacks_generated ASC) AS pass_rush_ease_percentile
  FROM opponent_pass_defense_base
),

team_oline_quality_base AS (
  SELECT DISTINCT ON (ts.team_id)
    ts.team_id,
    ts.sacks_allowed
  FROM nfl_team_season_stats ts
  WHERE ts.season = 2025 AND ts.postseason = false
),

team_oline_quality AS (
  SELECT
    team_id,
    sacks_allowed,
    PERCENT_RANK() OVER (ORDER BY sacks_allowed ASC) AS oline_quality_percentile
  FROM team_oline_quality_base
),

game_betting AS (
  SELECT DISTINCT ON (bo.game_id)
    bo.game_id,
    CAST(bo.spread_home_value AS NUMERIC) AS spread_home,
    CAST(bo.spread_away_value AS NUMERIC) AS spread_away,
    CAST(bo.total_value AS NUMERIC) AS game_total,
    CASE WHEN CAST(bo.total_value AS NUMERIC) >= 50.0 THEN 1.0 WHEN CAST(bo.total_value AS NUMERIC) >= 48.0 THEN 0.80 WHEN CAST(bo.total_value AS NUMERIC) >= 45.0 THEN 0.60 ELSE 0.30 END AS shootout_indicator
  FROM nfl_betting_odds bo
  WHERE bo.vendor ILIKE 'draftkings'
),

team_offensive_profile AS (
  SELECT
    pg.team_id,
    AVG(pg.passing_attempts) AS avg_pass_attempts_team,
    COUNT(DISTINCT pg.game_id) AS games_played,
    CASE WHEN AVG(pg.passing_attempts) > 35 THEN 1.0 WHEN AVG(pg.passing_attempts) > 32 THEN 0.75 ELSE 0.50 END AS pass_volume_indicator
  FROM nfl_player_game_stats pg
  WHERE pg.season = 2025 AND pg.postseason = false AND pg.passing_attempts > 0
  GROUP BY pg.team_id
),

team_wr_talent AS (
  SELECT
    p.team_id,
    COUNT(DISTINCT p.id) AS wr_count,
    SUM(ar.targets) AS total_wr_targets,
    AVG(ar.avg_separation) AS avg_wr_separation,
    MAX(CASE WHEN ar.targets > 120 THEN 1.0 ELSE 0.0 END) AS has_elite_wr1
  FROM nfl_players p
  INNER JOIN nfl_advanced_receiving_stats ar ON ar.player_id = p.id AND ar.season = 2025 AND ar.week = 0 AND ar.postseason = false
  WHERE p.position_abbreviation IN ('WR', 'TE') AND ar.targets >= 30
  GROUP BY p.team_id
),

player_props AS (
  SELECT DISTINCT ON (pp.player_id, pp.game_id)
    pp.player_id,
    pp.game_id,
    CAST(pp.line_value AS NUMERIC) AS passing_yards_line,
    pp.created_at
  FROM nfl_player_props pp
  WHERE pp.vendor ILIKE 'draftkings' 
    AND pp.prop_type = 'passing_yards'
  ORDER BY pp.player_id, pp.game_id, pp.created_at DESC
),

team_record AS (
  SELECT
    ts.team_id,
    ts.wins,
    ts.losses,
    CASE WHEN (ts.wins + ts.losses) > 0 THEN ts.wins::numeric / (ts.wins + ts.losses) ELSE 0.5 END AS win_pct
  FROM nfl_team_standings ts
  WHERE ts.season = 2025
),

qb_matchups AS (
  SELECT
    ug.game_id,
    ug.season,
    ug.week,
    qb.player_id,
    qb.first_name || ' ' || qb.last_name AS player_name,
    qb.position_abbreviation AS position,
    qb.team_id,
    tm_player.abbreviation AS team,
    CASE WHEN qb.team_id = ug.home_team_id THEN ug.visitor_team_id ELSE ug.home_team_id END AS opponent_team_id,
    tm_opp.abbreviation AS opponent,
    gb.spread_home,
    gb.game_total,
    gb.shootout_indicator,
    CASE WHEN qb.team_id = ug.home_team_id AND gb.spread_home > 0 THEN 1.0 WHEN qb.team_id = ug.visitor_team_id AND gb.spread_home < 0 THEN 1.0 ELSE 0.0 END AS is_underdog,
    CASE WHEN qb.team_id = ug.home_team_id THEN gb.spread_home ELSE gb.spread_away END AS team_spread,
    qb.passing_attempts,
    qb.passing_yards,
    qb.passing_touchdowns,
    qb.pass_att_per_game,
    qb.ypa,
    qb.cpoe,
    qb.comp_pct,
    qb.aggressiveness,
    qb.avg_time_to_throw,
    qb.td_int_ratio,
    qb.qb_rating,
    opp.opp_passing_yards_per_game AS opp_pass_yards_allowed,
    opp.pass_def_funnel_percentile AS opp_pass_def_rank,
    opp.sacks_generated AS opp_sacks,
    opp.pass_rush_ease_percentile AS opp_pass_rush_ease,
    opp.opp_red_zone_scoring_pct,
    opp.opp_points_per_game AS opp_points_pg, 
    oline.oline_quality_percentile AS oline_quality,
    oline.sacks_allowed AS team_sacks_allowed,
    top.pass_volume_indicator AS team_pass_volume,
    wr.has_elite_wr1,
    wr.avg_wr_separation,
    pp.passing_yards_line AS dk_line,
    
    (LEAST((COALESCE(opp.pass_rush_ease_percentile, 0.5) * 0.60) + (COALESCE(oline.oline_quality_percentile, 0.5) * 0.40), 1.0)) * 12.0 AS pocket_protection_score,
    (COALESCE(gb.shootout_indicator, 0)) * 20.0 AS shootout_score,
    (COALESCE(opp.pass_def_funnel_percentile, 0.5)) * 12.0 AS pass_funnel_score,
    (CASE WHEN qb.cpoe >= 4.0 THEN 1.0 WHEN qb.cpoe >= 2.5 THEN 0.85 WHEN qb.cpoe >= 1.0 THEN 0.70 WHEN qb.cpoe >= 0.0 THEN 0.50 WHEN qb.cpoe >= -1.0 THEN 0.30 ELSE 0.15 END) * 15.0 AS efficiency_score,
    (CASE WHEN qb.aggressiveness >= 18.0 THEN 1.0 WHEN qb.aggressiveness >= 15.0 THEN 0.80 WHEN qb.aggressiveness >= 12.0 THEN 0.60 WHEN qb.aggressiveness >= 9.0 THEN 0.40 ELSE 0.20 END) * 10.0 AS aggressiveness_score,
    (CASE WHEN qb.pass_att_per_game >= 36.0 THEN 1.0 WHEN qb.pass_att_per_game >= 32.0 THEN 0.85 WHEN qb.pass_att_per_game >= 28.0 THEN 0.65 WHEN qb.pass_att_per_game >= 24.0 THEN 0.40 ELSE 0.15 END) * 12.0 AS volume_score,
    (CASE 
      WHEN (CASE WHEN qb.team_id = ug.home_team_id AND gb.spread_home > 0 THEN 1.0 WHEN qb.team_id = ug.visitor_team_id AND gb.spread_home < 0 THEN 1.0 ELSE 0.0 END) = 1.0 AND (CASE WHEN qb.team_id = ug.home_team_id THEN gb.spread_home ELSE gb.spread_away END) >= 7.0 THEN 1.0
      WHEN (CASE WHEN qb.team_id = ug.home_team_id AND gb.spread_home > 0 THEN 1.0 WHEN qb.team_id = ug.visitor_team_id AND gb.spread_home < 0 THEN 1.0 ELSE 0.0 END) = 1.0 AND (CASE WHEN qb.team_id = ug.home_team_id THEN gb.spread_home ELSE gb.spread_away END) >= 3.5 THEN 0.80
      WHEN (CASE WHEN qb.team_id = ug.home_team_id AND gb.spread_home > 0 THEN 1.0 WHEN qb.team_id = ug.visitor_team_id AND gb.spread_home < 0 THEN 1.0 ELSE 0.0 END) = 1.0 AND (CASE WHEN qb.team_id = ug.home_team_id THEN gb.spread_home ELSE gb.spread_away END) >= 3.5 THEN 0.60
      WHEN (CASE WHEN qb.team_id = ug.home_team_id THEN gb.spread_home ELSE gb.spread_away END) BETWEEN -3.0 AND 3.0 THEN 0.50 
      ELSE 0.30
    END) * 8.0 AS script_score,
    (CASE WHEN opp.opp_red_zone_scoring_pct >= 65.0 THEN 1.0 WHEN opp.opp_red_zone_scoring_pct >= 60.0 THEN 0.85 WHEN opp.opp_red_zone_scoring_pct >= 55.0 THEN 0.65 WHEN opp.opp_red_zone_scoring_pct >= 50.0 THEN 0.45 ELSE 0.25 END) * 8.0 AS red_zone_score
  FROM qb_season_stats qb
  INNER JOIN upcoming_games ug ON qb.team_id IN (ug.home_team_id, ug.visitor_team_id)
  INNER JOIN nfl_teams tm_player ON tm_player.id = qb.team_id
  INNER JOIN nfl_teams tm_opp ON tm_opp.id = CASE WHEN qb.team_id = ug.home_team_id THEN ug.visitor_team_id ELSE ug.home_team_id END
  LEFT JOIN opponent_pass_defense opp ON opp.team_id = CASE WHEN qb.team_id = ug.home_team_id THEN ug.visitor_team_id ELSE ug.home_team_id END
  LEFT JOIN team_oline_quality oline ON oline.team_id = qb.team_id
  LEFT JOIN game_betting gb ON gb.game_id = ug.game_id
  LEFT JOIN team_offensive_profile top ON top.team_id = qb.team_id
  LEFT JOIN team_wr_talent wr ON wr.team_id = qb.team_id
  
  -- CHANGED TO INNER JOIN (Strict Mode: Must have prop to exist)
  INNER JOIN player_props pp ON pp.player_id = qb.player_id AND pp.game_id = ug.game_id
  
  LEFT JOIN team_record tr ON tr.team_id = qb.team_id
)

-- [SELECT Statement remains the same as before]
SELECT
  game_id,
  season,
  week,
  player_id,
  player_name,
  position,
  team,
  opponent,
  ROUND(pass_att_per_game::numeric, 1) AS pass_att_per_game,
  ROUND(ypa::numeric, 2) AS ypa,
  ROUND(comp_pct::numeric, 1) AS comp_pct,
  ROUND(cpoe::numeric, 2) AS cpoe,
  ROUND(aggressiveness::numeric, 1) AS aggressiveness,
  ROUND(td_int_ratio::numeric, 2) AS td_int_ratio,
  ROUND(qb_rating::numeric, 1) AS qb_rating,
  ROUND(avg_time_to_throw::numeric, 2) AS time_to_throw,
  team_sacks_allowed,
  ROUND((oline_quality * 100)::numeric, 0) AS oline_rank_pct,
  ROUND(opp_pass_yards_allowed::numeric, 1) AS opp_pass_ypg,
  ROUND((opp_pass_def_rank * 100)::numeric, 0) AS opp_def_rank_pct,
  opp_sacks,
  ROUND(opp_red_zone_scoring_pct::numeric, 1) AS opp_rz_pct,
  ROUND(opp_points_pg::numeric, 1) AS opp_points_pg,
  ROUND(team_spread::numeric, 1) AS spread,
  ROUND(COALESCE(game_total, 0)::numeric, 1) AS game_total,
  is_underdog::int AS is_underdog,
  has_elite_wr1::int AS has_elite_wr1,
  ROUND(avg_wr_separation::numeric, 2) AS avg_wr_separation,
  dk_line,
  ROUND(COALESCE(pocket_protection_score, 0)::numeric, 1) AS pocket_score,
  ROUND(COALESCE(shootout_score, 0)::numeric, 1) AS shootout_score,
  ROUND(COALESCE(pass_funnel_score, 0)::numeric, 1) AS pass_funnel_score,
  ROUND(COALESCE(efficiency_score, 0)::numeric, 1) AS efficiency_score,
  ROUND(COALESCE(aggressiveness_score, 0)::numeric, 1) AS aggressiveness_score,
  ROUND(COALESCE(script_score, 0)::numeric, 1) AS script_score,
  ROUND(COALESCE(red_zone_score, 0)::numeric, 1) AS red_zone_score,
  ROUND(
    (
      COALESCE(pocket_protection_score, 0) + 
      COALESCE(shootout_score, 0) + 
      COALESCE(pass_funnel_score, 0) + 
      COALESCE(efficiency_score, 0) + 
      COALESCE(aggressiveness_score, 0) + 
      COALESCE(volume_score, 0) + 
      COALESCE(script_score, 0) + 
      COALESCE(red_zone_score, 0)
    )::numeric,
    1
  ) AS smash_score
FROM qb_matchups
ORDER BY smash_score DESC;

GRANT SELECT ON public.model_qb_smash TO service_role;