CREATE OR REPLACE VIEW public.model_rb_smash AS

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

rb_season_stats AS (
  SELECT
    p.id AS player_id,
    p.first_name,
    p.last_name,
    p.position_abbreviation,
    p.team_id,
    ss.rushing_attempts,
    ss.rushing_yards,
    ss.rushing_touchdowns,
    ss.games_played,
    ss.receiving_targets,
    ss.receptions,
    ss.receiving_yards,
    ss.receiving_touchdowns,
    ars.rush_yards_over_expected_per_att AS ryoe_per_att,
    ars.efficiency AS rush_efficiency,
    ars.percent_attempts_gte_eight_defenders AS stacked_box_rate,
    ars.avg_time_to_los,
    ars.rush_yards_over_expected AS total_ryoe,
    arec.catch_percentage AS rec_catch_pct,
    arec.avg_yac,
    arec.targets AS rec_targets_adv,
    CASE WHEN ss.games_played > 0 THEN (ss.rushing_attempts + COALESCE(ss.receptions, 0))::numeric / ss.games_played ELSE 0 END AS touches_per_game,
    CASE WHEN ss.games_played > 0 THEN ss.rushing_attempts::numeric / ss.games_played ELSE 0 END AS rush_att_per_game,
    CASE WHEN ss.rushing_attempts > 0 THEN ss.rushing_yards::numeric / ss.rushing_attempts ELSE 0 END AS ypc
  FROM nfl_players p
  INNER JOIN nfl_player_season_stats ss ON ss.player_id = p.id AND ss.season = 2025 AND ss.postseason = false
  LEFT JOIN nfl_advanced_rushing_stats ars ON ars.player_id = p.id AND ars.season = 2025 AND ars.week = 0 AND ars.postseason = false
  LEFT JOIN nfl_advanced_receiving_stats arec ON arec.player_id = p.id AND arec.season = 2025 AND arec.week = 0 AND arec.postseason = false
  WHERE p.position_abbreviation IN ('RB', 'HB')
    AND ss.rushing_attempts >= 30
    -- DUPLICATE-PROOF INJURY CHECK
    AND NOT EXISTS (
      SELECT 1 FROM nfl_injuries inj 
      WHERE inj.player_id = p.id 
      AND inj.status IN ('Out', 'Injured Reserve', 'Doubtful')
    )
),

opponent_run_defense_base AS (
  SELECT DISTINCT ON (ts.team_id)
    ts.team_id,
    ts.opp_rushing_yards_per_game,
    ts.opp_points_per_game,
    ts.turnover_differential,
    ts.opp_third_down_pct
  FROM nfl_team_season_stats ts
  WHERE ts.season = 2025 AND ts.postseason = false
),

opponent_run_defense AS (
  SELECT
    team_id,
    opp_rushing_yards_per_game,
    opp_points_per_game,
    turnover_differential,
    opp_third_down_pct,
    PERCENT_RANK() OVER (ORDER BY opp_rushing_yards_per_game ASC) AS run_def_funnel_percentile
  FROM opponent_run_defense_base
),

game_betting AS (
  -- DISTINCT ON to prevent duplicates
  SELECT DISTINCT ON (bo.game_id)
    bo.game_id,
    CAST(bo.spread_home_value AS NUMERIC) AS spread_home,
    CAST(bo.spread_away_value AS NUMERIC) AS spread_away,
    CAST(bo.total_value AS NUMERIC) AS game_total
  FROM nfl_betting_odds bo
  WHERE bo.vendor ILIKE 'draftkings'
),

team_offensive_profile AS (
  SELECT
    pg.team_id,
    AVG(pg.rushing_attempts) AS avg_rush_attempts_team,
    AVG(pg.passing_attempts) AS avg_pass_attempts_team,
    CASE WHEN AVG(pg.rushing_attempts) > 28 THEN 1.0 ELSE 0.0 END AS is_run_heavy
  FROM nfl_player_game_stats pg
  WHERE pg.season = 2025 AND pg.postseason = false
  GROUP BY pg.team_id
),

player_props AS (
  -- DISTINCT ON to prevent duplicates
  SELECT DISTINCT ON (pp.player_id, pp.game_id)
    pp.player_id,
    pp.game_id,
    CAST(pp.line_value AS NUMERIC) AS rushing_yards_line,
    pp.created_at
  FROM nfl_player_props pp
  WHERE pp.vendor ILIKE 'draftkings' 
    AND pp.prop_type = 'rushing_yards'
  ORDER BY pp.player_id, pp.game_id, pp.created_at DESC
),

team_record AS (
  SELECT
    ts.team_id,
    ts.wins,
    ts.losses,
    ts.point_differential,
    CASE WHEN (ts.wins + ts.losses) > 0 THEN ts.wins::numeric / (ts.wins + ts.losses) ELSE 0.5 END AS win_pct
  FROM nfl_team_standings ts
  WHERE ts.season = 2025
),

rb_matchups AS (
  SELECT
    ug.game_id,
    ug.season,
    ug.week,
    rb.player_id,
    rb.first_name || ' ' || rb.last_name AS player_name,
    rb.position_abbreviation AS position,
    rb.team_id,
    tm_player.abbreviation AS team,
    CASE WHEN rb.team_id = ug.home_team_id THEN ug.visitor_team_id ELSE ug.home_team_id END AS opponent_team_id,
    tm_opp.abbreviation AS opponent,
    gb.spread_home,
    gb.game_total,
    CASE 
      WHEN rb.team_id = ug.home_team_id AND gb.spread_home < -3.5 THEN 1.0
      WHEN rb.team_id = ug.visitor_team_id AND ABS(gb.spread_home) > 3.5 AND gb.spread_home > 0 THEN 1.0
      ELSE 0.0
    END AS is_favorite,
    CASE WHEN rb.team_id = ug.home_team_id THEN gb.spread_home ELSE gb.spread_away END AS team_spread,
    rb.rushing_attempts,
    rb.rushing_yards,
    rb.rush_att_per_game,
    rb.ypc,
    rb.ryoe_per_att,
    rb.rush_efficiency,
    rb.stacked_box_rate,
    rb.total_ryoe,
    rb.receiving_targets,
    rb.rec_targets_adv,
    DENSE_RANK() OVER (PARTITION BY rb.team_id ORDER BY rb.touches_per_game DESC) AS rb_team_rank,
    rb.receptions,
    rb.receiving_yards,
    rb.rec_catch_pct,
    rb.touches_per_game,
    opp.opp_rushing_yards_per_game AS opp_rush_yards_allowed,
    opp.run_def_funnel_percentile AS opp_run_def_rank,
    opp.opp_points_per_game AS opp_points_pg, 
    opp.turnover_differential AS opp_turnover_diff,
    top.is_run_heavy AS team_run_heavy,
    tr.win_pct AS team_win_pct,
    pp.rushing_yards_line AS dk_line,
    
    (COALESCE(opp.run_def_funnel_percentile, 0.5)) * 15.0 AS run_funnel_score,
    (CASE 
      WHEN opp.turnover_differential <= -8 THEN 1.0
      WHEN opp.turnover_differential <= -5 THEN 0.85
      WHEN opp.turnover_differential <= -3 THEN 0.65
      WHEN opp.turnover_differential <= 0 THEN 0.45
      ELSE 0.2
    END) * 15.0 AS turnover_score,
    (CASE 
      WHEN (CASE WHEN rb.team_id = ug.home_team_id AND gb.spread_home < -3.5 THEN 1.0 WHEN rb.team_id = ug.visitor_team_id AND ABS(gb.spread_home) > 3.5 AND gb.spread_home > 0 THEN 1.0 ELSE 0.0 END) = 1.0 AND (CASE WHEN rb.team_id = ug.home_team_id THEN gb.spread_home ELSE gb.spread_away END) <= -7.0 THEN 1.0
      WHEN (CASE WHEN rb.team_id = ug.home_team_id AND gb.spread_home < -3.5 THEN 1.0 WHEN rb.team_id = ug.visitor_team_id AND ABS(gb.spread_home) > 3.5 AND gb.spread_home > 0 THEN 1.0 ELSE 0.0 END) = 1.0 AND (CASE WHEN rb.team_id = ug.home_team_id THEN gb.spread_home ELSE gb.spread_away END) <= -3.5 THEN 0.80
      WHEN (CASE WHEN rb.team_id = ug.home_team_id AND gb.spread_home < -3.5 THEN 1.0 WHEN rb.team_id = ug.visitor_team_id AND ABS(gb.spread_home) > 3.5 AND gb.spread_home > 0 THEN 1.0 ELSE 0.0 END) = 1.0 THEN 0.60
      WHEN (CASE WHEN rb.team_id = ug.home_team_id THEN gb.spread_home ELSE gb.spread_away END) BETWEEN -3.0 AND 3.0 THEN 0.45 
      ELSE 0.25
    END) * 15.0 AS favorite_score,
    (CASE WHEN rb.ryoe_per_att >= 0.3 THEN 1.0 WHEN rb.ryoe_per_att >= 0.15 THEN 0.85 WHEN rb.ryoe_per_att >= 0.0 THEN 0.65 WHEN rb.ryoe_per_att >= -0.15 THEN 0.40 ELSE 0.15 END) * 20.0 AS efficiency_score,
    (CASE 
      WHEN opp.opp_points_per_game >= 26.0 THEN 1.0 
      WHEN opp.opp_points_per_game >= 24.0 THEN 0.80 
      WHEN opp.opp_points_per_game >= 22.0 THEN 0.60 
      WHEN opp.opp_points_per_game >= 20.0 THEN 0.40 
      ELSE 0.2 
    END) * 10.0 AS discipline_score,
    (CASE WHEN rb.rush_att_per_game >= 18.0 THEN 1.0 WHEN rb.rush_att_per_game >= 15.0 THEN 0.85 WHEN rb.rush_att_per_game >= 12.0 THEN 0.65 WHEN rb.rush_att_per_game >= 9.0 THEN 0.40 ELSE 0.15 END)
      * (
        CASE 
          WHEN DENSE_RANK() OVER (PARTITION BY rb.team_id ORDER BY rb.touches_per_game DESC) = 1 THEN 1.0
          WHEN DENSE_RANK() OVER (PARTITION BY rb.team_id ORDER BY rb.touches_per_game DESC) = 2 THEN 0.75
          ELSE 0.50
        END
      )
      * 18.0 AS volume_score,
    (CASE WHEN rb.receiving_targets >= 60 THEN 1.0 WHEN rb.receiving_targets >= 40 THEN 0.75 WHEN rb.receiving_targets >= 25 THEN 0.50 WHEN rb.receiving_targets >= 10 THEN 0.25 ELSE 0.0 END) * 8.0 AS receiving_upside_score
  FROM rb_season_stats rb
  INNER JOIN upcoming_games ug ON rb.team_id IN (ug.home_team_id, ug.visitor_team_id)
  INNER JOIN nfl_teams tm_player ON tm_player.id = rb.team_id
  INNER JOIN nfl_teams tm_opp ON tm_opp.id = CASE WHEN rb.team_id = ug.home_team_id THEN ug.visitor_team_id ELSE ug.home_team_id END
  LEFT JOIN opponent_run_defense opp ON opp.team_id = CASE WHEN rb.team_id = ug.home_team_id THEN ug.visitor_team_id ELSE ug.home_team_id END
  LEFT JOIN game_betting gb ON gb.game_id = ug.game_id
  LEFT JOIN team_offensive_profile top ON top.team_id = rb.team_id
  
  -- STRICT MODE: INNER JOIN
  INNER JOIN player_props pp ON pp.player_id = rb.player_id AND pp.game_id = ug.game_id
  
  LEFT JOIN team_record tr ON tr.team_id = rb.team_id
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
  ROUND(rush_att_per_game::numeric, 1) AS rush_att_per_game,
  ROUND(touches_per_game::numeric, 1) AS touches_per_game,
  ROUND(ypc::numeric, 2) AS ypc,
  ROUND(ryoe_per_att::numeric, 3) AS ryoe_per_att,
  ROUND((stacked_box_rate * 100)::numeric, 1) AS stacked_box_pct,
  rec_targets_adv AS rec_targets,
  receptions,
  receiving_yards AS rec_yards,
  ROUND(opp_rush_yards_allowed::numeric, 1) AS opp_rush_ypg,
  ROUND((opp_run_def_rank * 100)::numeric, 0) AS opp_def_rank_pct,
  ROUND(opp_points_pg::numeric, 1) AS opp_points_pg,
  opp_turnover_diff,
  ROUND(team_spread::numeric, 1) AS spread,
  ROUND(COALESCE(game_total, 0)::numeric, 1) AS game_total,
  is_favorite::int AS is_favorite,
  dk_line,
  ROUND(COALESCE(run_funnel_score, 0)::numeric, 1) AS run_funnel_score,
  ROUND(COALESCE(turnover_score, 0)::numeric, 1) AS turnover_score,
  ROUND(COALESCE(favorite_score, 0)::numeric, 1) AS favorite_score,
  ROUND(COALESCE(efficiency_score, 0)::numeric, 1) AS efficiency_score,
  ROUND(COALESCE(discipline_score, 0)::numeric, 1) AS discipline_score,
  ROUND(COALESCE(volume_score, 0)::numeric, 1) AS volume_score,
  ROUND(COALESCE(receiving_upside_score, 0)::numeric, 1) AS receiving_upside_score,
  ROUND(
    (
      COALESCE(run_funnel_score, 0) + 
      COALESCE(turnover_score, 0) + 
      COALESCE(favorite_score, 0) + 
      COALESCE(efficiency_score, 0) + 
      COALESCE(discipline_score, 0) + 
      COALESCE(volume_score, 0) + 
      COALESCE(receiving_upside_score, 0)
    )::numeric,
    1
  ) AS smash_score
FROM rb_matchups
ORDER BY smash_score DESC;

GRANT SELECT ON public.model_rb_smash TO service_role;