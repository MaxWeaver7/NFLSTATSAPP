# Team Season Stats Gap Report (BDL payload vs DB schema)

Scope: Compare BDL `team_season_stats` payload fields (from FullBALLDONTLIEAPI sample) to current table `nfl_team_season_stats`.

## 1) Present in payload but **missing** from DB schema

### Totals / Net
- net_total_offensive_yards
- net_total_offensive_yards_per_game
- net_passing_yards_per_game
- net_yards_per_pass_attempt

### Explosives / Longs
- passing_long
- rushing_long
- receiving_long
- returning_long_kick_return
- returning_long_punt_return

### Rushing / Receiving details
- rushing_fumbles_lost
- receiving_yards_per_game
- receiving_fumbles
- receiving_fumbles_lost

### Misc / Situational (raw conv/attempts + discipline)
- misc_first_downs_passing
- misc_first_downs_rushing
- misc_first_downs_penalty
- misc_third_down_convs
- misc_third_down_attempts
- misc_fourth_down_convs
- misc_fourth_down_attempts
- misc_total_penalties
- misc_total_penalty_yards
- misc_total_takeaways
- misc_total_giveaways

### Kicking / Punting extras
- kicking_long_field_goal_made
- kicking_field_goals_made_1_19
- kicking_field_goals_made_20_29
- kicking_field_goals_made_30_39
- kicking_field_goals_made_40_49
- kicking_field_goals_made_50
- kicking_field_goal_attempts_1_19
- kicking_field_goal_attempts_20_29
- kicking_field_goal_attempts_30_39
- kicking_field_goal_attempts_40_49
- kicking_field_goal_attempts_50
- kicking_extra_points_made
- kicking_extra_point_attempts
- kicking_extra_point_pct
- punting_long_punt
- punting_punts_blocked
- punting_touchbacks
- punting_fair_catches
- punting_punt_returns
- punting_punt_return_yards
- punting_avg_punt_return_yards

### Opponent block (entirely missing)
All `opp_*` fields are missing from schema (e.g., opp_total_points, opp_passing_yards, opp_misc_* , opp_kicking_*, opp_punting_*, opp_defensive_interceptions, etc.).

### Turnovers
- fumbles_lost (team-level) is in payload but not in schema.

## 2) Present in schema but **not in payload sample**
These currently remain null unless the live API actually returns them:
- passing_first_downs
- passing_first_down_pct
- passing_20_plus_yards
- passing_40_plus_yards
- rushing_first_downs
- rushing_first_down_pct
- rushing_20_plus_yards
- rushing_40_plus_yards
- receiving_targets
- receiving_first_downs
- red_zone_efficiency
- goal_to_go_efficiency
- possession_time
- possession_time_seconds
- fumbles_forced

## 3) What can be computed without schema changes
Using `nfl_team_game_stats` (season aggregation):
- third_down_conversions/attempts (sum)
- fourth_down_conversions/attempts (sum)
- red_zone_scores/attempts (sum)
- penalties/penalty_yards (sum)
- possession_time (sum of seconds)

## 4) Impact on UI
- Current team page only uses a small subset of standings + season totals.
- Missing columns prevent full “all-data” panels (explosives, situational, opponent, special teams breakdown, XP splits).

## 5) Recommendation
Best practice for completeness and future-proofing:
- Add `stats_json` (JSONB) to store full payload unmodified.
- Add high-value columns you want indexed/queried.
- Compute season-level situational metrics from team_game_stats when feasible.

This ensures web development is seamless without repeated schema blocks.
