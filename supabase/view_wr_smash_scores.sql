CREATE OR REPLACE VIEW public.model_wr_smash AS

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

wr_season_stats AS (
  SELECT
    p.id AS player_id,
    p.first_name,
    p.last_name,
    p.position_abbreviation,
    p.team_id,
    ss.receptions,
    ss.receiving_yards,
    ss.receiving_touchdowns,
    ss.receiving_targets,
    ss.games_played,
    ar.avg_intended_air_yards AS adot,
    ar.avg_separation,
    ar.avg_cushion,
    ar.catch_percentage,
    ar.percent_share_of_intended_air_yards AS air_yards_share,
    ar.avg_yac,
    ar.avg_yac_above_expectation AS yac_plus,
    CASE WHEN ss.games_played > 0 THEN ss.receiving_targets::numeric / ss.games_played ELSE 0 END AS targets_per_game,
    CASE WHEN ss.receiving_targets > 0 THEN ss.receiving_yards::numeric / ss.receiving_targets ELSE 0 END AS yards_per_target
  FROM nfl_players p
  INNER JOIN nfl_player_season_stats ss ON ss.player_id = p.id AND ss.season = 2025 AND ss.postseason = false
  LEFT JOIN nfl_advanced_receiving_stats ar ON ar.player_id = p.id AND ar.season = 2025 AND ar.week = 0 AND ar.postseason = false
  WHERE p.position_abbreviation IN ('WR', 'TE')
    AND ss.receiving_targets >= 20
    -- DUPLICATE-PROOF INJURY CHECK
    AND NOT EXISTS (
      SELECT 1 FROM nfl_injuries inj 
      WHERE inj.player_id = p.id 
      AND inj.status IN ('Out', 'Injured Reserve', 'Doubtful')
    )
),

team_qb_stats AS (
  SELECT
    p.team_id,
    SUM(ap.attempts) AS total_attempts,
    SUM(ap.avg_time_to_throw * ap.attempts) / NULLIF(SUM(ap.attempts), 0) AS avg_time_to_throw,
    SUM(ap.completion_percentage * ap.attempts) / NULLIF(SUM(ap.attempts), 0) AS completion_pct,
    SUM(ap.completion_percentage_above_expectation * ap.attempts) / NULLIF(SUM(ap.attempts), 0) AS cpoe,
    SUM(ap.aggressiveness * ap.attempts) / NULLIF(SUM(ap.attempts), 0) AS aggressiveness,
    SUM(ap.avg_intended_air_yards * ap.attempts) / NULLIF(SUM(ap.attempts), 0) AS avg_air_yards
  FROM nfl_players p
  INNER JOIN nfl_advanced_passing_stats ap ON ap.player_id = p.id AND ap.season = 2025 AND ap.week = 0 AND ap.postseason = false
  WHERE p.position_abbreviation = 'QB' AND ap.attempts >= 50
  GROUP BY p.team_id
),

opponent_pass_defense_base AS (
  SELECT DISTINCT ON (ts.team_id)
    ts.team_id,
    ts.opp_passing_yards_per_game,
    ts.opp_sacks_forced AS sacks_generated,
    ts.opp_interceptions_forced,
    ts.opp_third_down_pct
  FROM nfl_team_season_stats ts
  WHERE ts.season = 2025 AND ts.postseason = false
),

opponent_pass_defense AS (
  SELECT
    team_id,
    opp_passing_yards_per_game,
    sacks_generated,
    opp_interceptions_forced,
    opp_third_down_pct,
    PERCENT_RANK() OVER (ORDER BY opp_passing_yards_per_game ASC) AS pass_def_funnel_percentile
  FROM opponent_pass_defense_base
),

game_betting AS (
  -- DISTINCT ON to prevent duplicates
  SELECT DISTINCT ON (bo.game_id)
    bo.game_id,
    CAST(bo.spread_home_value AS NUMERIC) AS spread_home,
    CAST(bo.total_value AS NUMERIC) AS game_total,
    CASE WHEN CAST(bo.total_value AS NUMERIC) > 48.0 THEN 1.0 ELSE 0.0 END AS is_high_total
  FROM nfl_betting_odds bo
  WHERE bo.vendor ILIKE 'draftkings'
),

team_pass_volume AS (
  SELECT
    pg.team_id,
    AVG(pg.passing_attempts) AS avg_pass_attempts_per_game,
    COUNT(DISTINCT pg.game_id) AS games_played
  FROM nfl_player_game_stats pg
  WHERE pg.season = 2025 AND pg.postseason = false AND pg.passing_attempts > 0
  GROUP BY pg.team_id
),

player_props AS (
  -- DISTINCT ON to prevent duplicates
  SELECT DISTINCT ON (pp.player_id, pp.game_id)
    pp.player_id,
    pp.game_id,
    CAST(pp.line_value AS NUMERIC) AS receiving_yards_line,
    pp.created_at
  FROM nfl_player_props pp
  WHERE pp.vendor ILIKE 'draftkings' 
    AND pp.prop_type = 'receiving_yards'
  ORDER BY pp.player_id, pp.game_id, pp.created_at DESC
),

wr_matchups AS (
  SELECT
    ug.game_id,
    ug.season,
    ug.week,
    wr.player_id,
    wr.first_name || ' ' || wr.last_name AS player_name,
    wr.position_abbreviation AS position,
    wr.team_id,
    tm_player.abbreviation AS team,
    CASE WHEN wr.team_id = ug.home_team_id THEN ug.visitor_team_id ELSE ug.home_team_id END AS opponent_team_id,
    tm_opp.abbreviation AS opponent,
    gb.spread_home,
    gb.game_total,
    gb.is_high_total,
    CASE 
      WHEN wr.team_id = ug.home_team_id AND gb.spread_home > 0 THEN 1.0
      WHEN wr.team_id = ug.visitor_team_id AND gb.spread_home < 0 THEN 1.0
      ELSE 0.0
    END AS is_underdog,
    wr.receiving_targets,
    wr.targets_per_game,
    wr.receiving_yards,
    wr.adot,
    wr.avg_separation,
    wr.catch_percentage,
    wr.air_yards_share,
    wr.yac_plus,
    wr.yards_per_target,
    qb.avg_time_to_throw AS qb_time_to_throw,
    qb.completion_pct AS qb_completion_pct,
    qb.cpoe AS qb_cpoe,
    qb.aggressiveness AS qb_aggressiveness,
    opp.opp_passing_yards_per_game AS opp_pass_yards_allowed,
    opp.pass_def_funnel_percentile AS opp_pass_def_rank,
    opp.sacks_generated AS opp_sacks,
    tpv.avg_pass_attempts_per_game AS team_pass_volume,
    pp.receiving_yards_line AS dk_line,
    
    (CASE WHEN wr.air_yards_share >= 0.40 THEN 1.0 WHEN wr.air_yards_share >= 0.35 THEN 0.85 WHEN wr.air_yards_share >= 0.30 THEN 0.65 WHEN wr.air_yards_share >= 0.25 THEN 0.45 WHEN wr.air_yards_share >= 0.20 THEN 0.25 ELSE 0.1 END) * 25.0 AS air_share_score,
    (CASE WHEN wr.adot >= 14.0 THEN 1.0 WHEN wr.adot >= 12.0 THEN 0.85 WHEN wr.adot >= 10.0 THEN 0.65 WHEN wr.adot >= 8.0 THEN 0.45 ELSE 0.2 END) * 15.0 AS adot_score,
    (CASE WHEN wr.avg_separation >= 3.5 THEN 1.0 WHEN wr.avg_separation >= 3.0 THEN 0.80 WHEN wr.avg_separation >= 2.5 THEN 0.55 WHEN wr.avg_separation >= 2.0 THEN 0.30 ELSE 0.1 END) * 10.0 AS separation_score,
    (COALESCE(opp.pass_def_funnel_percentile, 0.5)) * 12.0 AS matchup_score,
    (CASE WHEN qb.avg_time_to_throw >= 3.0 THEN 1.0 WHEN qb.avg_time_to_throw >= 2.8 THEN 0.80 WHEN qb.avg_time_to_throw >= 2.6 THEN 0.60 WHEN qb.avg_time_to_throw >= 2.4 THEN 0.40 ELSE 0.2 END) * 5.0 AS qb_time_score,
    (CASE WHEN qb.cpoe >= 3.0 THEN 1.0 WHEN qb.cpoe >= 2.0 THEN 0.80 WHEN qb.cpoe >= 1.0 THEN 0.60 WHEN qb.cpoe >= 0.0 THEN 0.40 ELSE 0.2 END) * 5.0 AS qb_efficiency_score,
    (CASE 
      WHEN gb.is_high_total = 1.0 AND (CASE WHEN wr.team_id = ug.home_team_id AND gb.spread_home > 0 THEN 1.0 WHEN wr.team_id = ug.visitor_team_id AND gb.spread_home < 0 THEN 1.0 ELSE 0.0 END) = 1.0 THEN 1.0
      WHEN gb.is_high_total = 1.0 OR (CASE WHEN wr.team_id = ug.home_team_id AND gb.spread_home > 0 THEN 1.0 WHEN wr.team_id = ug.visitor_team_id AND gb.spread_home < 0 THEN 1.0 ELSE 0.0 END) = 1.0 THEN 0.70
      WHEN gb.game_total >= 45.0 THEN 0.50
      ELSE 0.25
    END) * 10.0 AS game_script_score,
    (CASE WHEN wr.catch_percentage >= 70.0 THEN 1.0 WHEN wr.catch_percentage >= 65.0 THEN 0.80 WHEN wr.catch_percentage >= 60.0 THEN 0.55 WHEN wr.catch_percentage >= 55.0 THEN 0.30 ELSE 0.1 END) * 5.0 AS catch_rate_score,
    (CASE WHEN wr.targets_per_game >= 10.0 THEN 1.0 WHEN wr.targets_per_game >= 8.0 THEN 0.80 WHEN wr.targets_per_game >= 6.0 THEN 0.55 WHEN wr.targets_per_game >= 4.0 THEN 0.30 ELSE 0.1 END)
      * (CASE WHEN DENSE_RANK() OVER (PARTITION BY wr.team_id ORDER BY wr.targets_per_game DESC) = 1 THEN 1.0 WHEN DENSE_RANK() OVER (PARTITION BY wr.team_id ORDER BY wr.targets_per_game DESC) = 2 THEN 0.75 ELSE 0.50 END)
      * 15.0 AS volume_score

  FROM wr_season_stats wr
  INNER JOIN upcoming_games ug ON wr.team_id IN (ug.home_team_id, ug.visitor_team_id)
  INNER JOIN nfl_teams tm_player ON tm_player.id = wr.team_id
  INNER JOIN nfl_teams tm_opp ON tm_opp.id = CASE WHEN wr.team_id = ug.home_team_id THEN ug.visitor_team_id ELSE ug.home_team_id END
  LEFT JOIN team_qb_stats qb ON qb.team_id = wr.team_id
  LEFT JOIN opponent_pass_defense opp ON opp.team_id = CASE WHEN wr.team_id = ug.home_team_id THEN ug.visitor_team_id ELSE ug.home_team_id END
  LEFT JOIN game_betting gb ON gb.game_id = ug.game_id
  LEFT JOIN team_pass_volume tpv ON tpv.team_id = wr.team_id
  
  -- STRICT MODE: INNER JOIN
  INNER JOIN player_props pp ON pp.player_id = wr.player_id AND pp.game_id = ug.game_id
)

SELECT
  game_id,
  season,
  week,
  player_id,
  player_name,
  position,
  team,
  opponent,
  ROUND(targets_per_game::numeric, 1) AS targets_per_game,
  ROUND(air_yards_share::numeric, 1) AS air_share_pct,
  ROUND(adot::numeric, 1) AS adot,
  ROUND(catch_percentage::numeric, 1) AS catch_rate,
  ROUND(avg_separation::numeric, 2) AS separation,
  ROUND(qb_time_to_throw::numeric, 2) AS qb_time_to_throw,
  ROUND(qb_completion_pct::numeric, 1) AS qb_comp_pct,
  ROUND(qb_cpoe::numeric, 1) AS qb_cpoe,
  ROUND(opp_pass_yards_allowed::numeric, 1) AS opp_pass_ypg,
  ROUND((opp_pass_def_rank * 100)::numeric, 0) AS opp_def_rank_pct,
  opp_sacks,
  ROUND(COALESCE(game_total, 0)::numeric, 1) AS game_total,
  spread_home,
  is_underdog::int AS is_underdog,
  dk_line,
  ROUND(COALESCE(air_share_score, 0)::numeric, 1) AS air_share_score,
  ROUND(COALESCE(adot_score, 0)::numeric, 1) AS adot_score,
  ROUND(COALESCE(separation_score, 0)::numeric, 1) AS separation_score,
  ROUND(COALESCE(matchup_score, 0)::numeric, 1) AS matchup_score,
  ROUND(COALESCE(qb_time_score, 0)::numeric, 1) AS qb_time_score,
  ROUND(COALESCE(qb_efficiency_score, 0)::numeric, 1) AS qb_efficiency_score,
  ROUND(COALESCE(game_script_score, 0)::numeric, 1) AS game_script_score,
  ROUND(COALESCE(catch_rate_score, 0)::numeric, 1) AS catch_rate_score,
  ROUND(COALESCE(volume_score, 0)::numeric, 1) AS volume_score,
  ROUND(
    (
      COALESCE(air_share_score, 0) + 
      COALESCE(adot_score, 0) + 
      COALESCE(separation_score, 0) + 
      COALESCE(matchup_score, 0) + 
      COALESCE(qb_time_score, 0) + 
      COALESCE(qb_efficiency_score, 0) + 
      COALESCE(game_script_score, 0) + 
      COALESCE(catch_rate_score, 0) + 
      COALESCE(volume_score, 0)
    )::numeric,
    1
  ) AS smash_score
FROM wr_matchups
ORDER BY smash_score DESC;

GRANT SELECT ON public.model_wr_smash TO service_role;O