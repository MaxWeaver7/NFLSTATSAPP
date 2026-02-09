// Shared configuration for advanced stats display
// Used by both GoatAdvancedStats (player dossier) and Leaderboards (season leaderboard)

export type ColumnType = "int" | "float";

export interface AdvancedColumn {
  k: string;
  label: string;
  type: ColumnType;
}

// Tooltip definitions for all advanced stats
export const ADVANCED_STAT_TOOLTIPS: Record<string, string> = {
  // Receiving
  targets: "Total times the player was targeted by a pass",
  receptions: "Total number of passes caught",
  yards: "Total receiving yards gained",
  avg_intended_air_yards: "Average distance the ball traveled in the air on targets",
  avg_yac: "Average yards gained after the catch",
  avg_expected_yac: "Expected yards after catch based on catch location and defense",
  avg_yac_above_expectation: "Difference between actual and expected yards after catch",
  avg_cushion: "Average distance the nearest defender was at time of catch",
  avg_separation: "Average distance from the nearest defender when ball arrived",
  catch_percentage: "Percentage of targets that resulted in receptions",
  percent_share_of_intended_air_yards: "Player's share of team's total intended air yards",
  rec_touchdowns: "Total receiving touchdowns",

  // Rushing
  rush_attempts: "Total number of rushing attempts",
  rush_yards: "Total rushing yards gained",
  rush_touchdowns: "Total rushing touchdowns",
  avg_time_to_los: "Average time (seconds) from snap to crossing line of scrimmage",
  expected_rush_yards: "Expected rushing yards based on blockers and defenders",
  rush_yards_over_expected: "Rushing yards gained above expectation",
  rush_yards_over_expected_per_att: "Average yards over expected per rushing attempt",
  rush_pct_over_expected: "Percentage of rushes that exceeded expected yards",
  efficiency: "Overall rushing efficiency rating",
  percent_attempts_gte_eight_defenders: "Percentage of rushes against 8+ defenders in box",
  avg_rush_yards: "Average yards per rushing attempt",

  // Passing
  attempts: "Total passing attempts",
  completions: "Total completed passes",
  pass_yards: "Total passing yards",
  pass_touchdowns: "Total passing touchdowns",
  interceptions: "Total interceptions thrown",
  passer_rating: "Traditional NFL passer rating",
  completion_percentage: "Percentage of passes completed",
  completion_percentage_above_expectation: "Completion % above expected based on throw difficulty",
  expected_completion_percentage: "Expected completion % based on throw characteristics",
  avg_time_to_throw: "Average time (seconds) from snap to throw",
  avg_completed_air_yards: "Average air yards on completed passes",
  avg_air_distance: "Average distance ball traveled in air (all attempts)",
  avg_air_yards_differential: "Difference between intended and completed air yards",
  avg_air_yards_to_sticks: "Average air yards relative to first down marker",
  max_air_distance: "Longest air yards on any attempt",
  max_completed_air_distance: "Longest completed pass (air yards)",
  aggressiveness: "Percentage of throws into tight coverage",
  games_played: "Number of games played"
};

// Column definitions for receiving stats (for player dossier - includes week)
export const ADVANCED_RECEIVING_COLUMNS_WITH_WEEK: AdvancedColumn[] = [
  { k: "week", label: "WK", type: "int" },
  { k: "targets", label: "TGT", type: "int" },
  { k: "receptions", label: "REC", type: "int" },
  { k: "yards", label: "YDS", type: "int" },
  { k: "avg_yac", label: "aYAC", type: "float" },
  { k: "avg_separation", label: "SEP", type: "float" },
  { k: "avg_cushion", label: "CUSH", type: "float" },
  { k: "catch_percentage", label: "CATCH%", type: "float" },
];

// Column definitions for rushing stats (for player dossier - includes week)
export const ADVANCED_RUSHING_COLUMNS_WITH_WEEK: AdvancedColumn[] = [
  { k: "week", label: "WK", type: "int" },
  { k: "rush_attempts", label: "ATT", type: "int" },
  { k: "rush_yards", label: "YDS", type: "int" },
  { k: "rush_touchdowns", label: "TD", type: "int" },
  { k: "avg_time_to_los", label: "TTLOS", type: "float" },
  { k: "expected_rush_yards", label: "xRushY", type: "float" },
  { k: "rush_yards_over_expected", label: "RYOE", type: "float" },
  { k: "efficiency", label: "EFF", type: "float" },
  { k: "avg_rush_yards", label: "AVG", type: "float" },
];

// Column definitions for passing stats (for player dossier - includes week)
export const ADVANCED_PASSING_COLUMNS_WITH_WEEK: AdvancedColumn[] = [
  { k: "week", label: "WK", type: "int" },
  { k: "attempts", label: "ATT", type: "int" },
  { k: "completions", label: "COMP", type: "int" },
  { k: "pass_yards", label: "YDS", type: "int" },
  { k: "pass_touchdowns", label: "TD", type: "int" },
  { k: "interceptions", label: "INT", type: "int" },
  { k: "passer_rating", label: "RATE", type: "float" },
  { k: "avg_time_to_throw", label: "TTT", type: "float" },
  { k: "avg_intended_air_yards", label: "IAY", type: "float" },
  { k: "aggressiveness", label: "AGG", type: "float" },
];

// Column definitions for leaderboards (season totals - no week column)
export const ADVANCED_RECEIVING_COLUMNS: AdvancedColumn[] = [
  { k: "targets", label: "TGT", type: "int" },
  { k: "receptions", label: "REC", type: "int" },
  { k: "yards", label: "YDS", type: "int" },
  { k: "avg_yac", label: "aYAC", type: "float" },
  { k: "avg_yac_above_expectation", label: "YAC+", type: "float" },
  { k: "avg_separation", label: "SEP", type: "float" },
  { k: "avg_cushion", label: "CUSH", type: "float" },
  { k: "catch_percentage", label: "CATCH%", type: "float" },
];

export const ADVANCED_RUSHING_COLUMNS: AdvancedColumn[] = [
  { k: "rush_attempts", label: "ATT", type: "int" },
  { k: "rush_yards", label: "YDS", type: "int" },
  { k: "rush_touchdowns", label: "TD", type: "int" },
  { k: "avg_rush_yards", label: "YPC", type: "float" },
  { k: "rush_yards_over_expected", label: "RYOE", type: "float" },
  { k: "rush_yards_over_expected_per_att", label: "RYOE/A", type: "float" },
  { k: "efficiency", label: "EFF", type: "float" },
  { k: "avg_time_to_los", label: "TTLOS", type: "float" },
  { k: "expected_rush_yards", label: "xRushY", type: "float" },
];

export const ADVANCED_PASSING_COLUMNS: AdvancedColumn[] = [
  { k: "attempts", label: "ATT", type: "int" },
  { k: "completions", label: "COMP", type: "int" },
  { k: "pass_yards", label: "YDS", type: "int" },
  { k: "pass_touchdowns", label: "TD", type: "int" },
  { k: "interceptions", label: "INT", type: "int" },
  { k: "passer_rating", label: "RATE", type: "float" },
  { k: "completion_percentage_above_expectation", label: "CPOE", type: "float" },
  { k: "avg_air_distance", label: "AIR", type: "float" },
  { k: "avg_intended_air_yards", label: "IAY", type: "float" },
  { k: "avg_time_to_throw", label: "TTT", type: "float" },
  { k: "aggressiveness", label: "AGG", type: "float" },
];

// ─── Season Bubble Definitions ───────────────────────────────────────

export interface BubbleStat {
  key: string;
  label: string;
  category: "passing" | "rushing" | "receiving";
  format: "int" | "float" | "pct";
  higher_is_better: boolean;
}

export const QB_SEASON_BUBBLES: BubbleStat[] = [
  // Passing
  { key: "attempts", label: "ATT", category: "passing", format: "int", higher_is_better: true },
  { key: "completions", label: "COMP", category: "passing", format: "int", higher_is_better: true },
  { key: "pass_yards", label: "YDS", category: "passing", format: "int", higher_is_better: true },
  { key: "pass_touchdowns", label: "TD", category: "passing", format: "int", higher_is_better: true },
  { key: "interceptions", label: "INT", category: "passing", format: "int", higher_is_better: false },
  { key: "passer_rating", label: "RATE", category: "passing", format: "float", higher_is_better: true },
  { key: "completion_percentage_above_expectation", label: "CPOE", category: "passing", format: "float", higher_is_better: true },
  { key: "expected_completion_percentage", label: "xCMP%", category: "passing", format: "float", higher_is_better: true },
  { key: "avg_time_to_throw", label: "TTT", category: "passing", format: "float", higher_is_better: false },
  { key: "avg_intended_air_yards", label: "IAY", category: "passing", format: "float", higher_is_better: true },
  { key: "avg_completed_air_yards", label: "CAY", category: "passing", format: "float", higher_is_better: true },
  { key: "avg_air_distance", label: "AIR", category: "passing", format: "float", higher_is_better: true },
  { key: "avg_air_yards_differential", label: "AY DIFF", category: "passing", format: "float", higher_is_better: false },
  { key: "avg_air_yards_to_sticks", label: "AYTS", category: "passing", format: "float", higher_is_better: true },
  { key: "aggressiveness", label: "AGG%", category: "passing", format: "float", higher_is_better: true },
];

export const RB_SEASON_BUBBLES: BubbleStat[] = [
  // Rushing
  { key: "rush_attempts", label: "ATT", category: "rushing", format: "int", higher_is_better: true },
  { key: "rush_yards", label: "YDS", category: "rushing", format: "int", higher_is_better: true },
  { key: "rush_touchdowns", label: "TD", category: "rushing", format: "int", higher_is_better: true },
  { key: "avg_rush_yards", label: "YPC", category: "rushing", format: "float", higher_is_better: true },
  { key: "rush_yards_over_expected", label: "RYOE", category: "rushing", format: "float", higher_is_better: true },
  { key: "rush_yards_over_expected_per_att", label: "RYOE/A", category: "rushing", format: "float", higher_is_better: true },
  { key: "rush_pct_over_expected", label: "R% OE", category: "rushing", format: "float", higher_is_better: true },
  { key: "efficiency", label: "EFF", category: "rushing", format: "float", higher_is_better: true },
  { key: "avg_time_to_los", label: "TTLOS", category: "rushing", format: "float", higher_is_better: false },
  { key: "expected_rush_yards", label: "xRUSH", category: "rushing", format: "float", higher_is_better: true },
  { key: "percent_attempts_gte_eight_defenders", label: "8+BOX%", category: "rushing", format: "float", higher_is_better: true },
  // Receiving
  { key: "targets", label: "TGT", category: "receiving", format: "int", higher_is_better: true },
  { key: "receptions", label: "REC", category: "receiving", format: "int", higher_is_better: true },
  { key: "yards", label: "RecYDS", category: "receiving", format: "int", higher_is_better: true },
  { key: "avg_yac", label: "YAC", category: "receiving", format: "float", higher_is_better: true },
  { key: "avg_separation", label: "SEP", category: "receiving", format: "float", higher_is_better: true },
  { key: "catch_percentage", label: "CATCH%", category: "receiving", format: "pct", higher_is_better: true },
];

export const WR_SEASON_BUBBLES: BubbleStat[] = [
  // Receiving
  { key: "targets", label: "TGT", category: "receiving", format: "int", higher_is_better: true },
  { key: "receptions", label: "REC", category: "receiving", format: "int", higher_is_better: true },
  { key: "yards", label: "YDS", category: "receiving", format: "int", higher_is_better: true },
  { key: "avg_yac", label: "YAC", category: "receiving", format: "float", higher_is_better: true },
  { key: "avg_expected_yac", label: "xYAC", category: "receiving", format: "float", higher_is_better: true },
  { key: "avg_yac_above_expectation", label: "YAC+", category: "receiving", format: "float", higher_is_better: true },
  { key: "avg_cushion", label: "CUSH", category: "receiving", format: "float", higher_is_better: true },
  { key: "avg_separation", label: "SEP", category: "receiving", format: "float", higher_is_better: true },
  { key: "catch_percentage", label: "CATCH%", category: "receiving", format: "pct", higher_is_better: true },
  { key: "percent_share_of_intended_air_yards", label: "IAY%", category: "receiving", format: "pct", higher_is_better: true },
];

export const TE_SEASON_BUBBLES: BubbleStat[] = WR_SEASON_BUBBLES;

// ─── Game Log Column Definitions ─────────────────────────────────────

export interface GameLogColumn {
  key: string;
  label: string;
  source: "base" | "passing" | "rushing" | "receiving" | "snap";
  format: "int" | "float" | "pct";
}

export const QB_GAME_LOG_COLS: GameLogColumn[] = [
  { key: "offense_snaps", label: "SNP", source: "snap", format: "int" },
  { key: "offense_pct", label: "SNP%", source: "snap", format: "pct" },
  { key: "completions", label: "CMP", source: "passing", format: "int" },
  { key: "attempts", label: "ATT", source: "passing", format: "int" },
  { key: "pass_yards", label: "YDS", source: "passing", format: "int" },
  { key: "pass_touchdowns", label: "TD", source: "passing", format: "int" },
  { key: "interceptions", label: "INT", source: "passing", format: "int" },
  { key: "passer_rating", label: "RATE", source: "passing", format: "float" },
  { key: "completion_percentage_above_expectation", label: "CPOE", source: "passing", format: "float" },
  { key: "avg_time_to_throw", label: "TTT", source: "passing", format: "float" },
  { key: "avg_intended_air_yards", label: "IAY", source: "passing", format: "float" },
  { key: "aggressiveness", label: "AGG", source: "passing", format: "float" },
  { key: "rush_attempts", label: "RuATT", source: "base", format: "int" },
  { key: "rush_yards", label: "RuYDS", source: "base", format: "int" },
  { key: "rush_tds", label: "RuTD", source: "base", format: "int" },
];

export const RB_GAME_LOG_COLS: GameLogColumn[] = [
  { key: "offense_snaps", label: "SNP", source: "snap", format: "int" },
  { key: "offense_pct", label: "SNP%", source: "snap", format: "pct" },
  { key: "rush_attempts", label: "ATT", source: "base", format: "int" },
  { key: "rush_yards", label: "YDS", source: "base", format: "int" },
  { key: "rush_tds", label: "TD", source: "base", format: "int" },
  { key: "avg_rush_yards", label: "YPC", source: "rushing", format: "float" },
  { key: "rush_yards_over_expected", label: "RYOE", source: "rushing", format: "float" },
  { key: "efficiency", label: "EFF", source: "rushing", format: "float" },
  { key: "targets", label: "TGT", source: "base", format: "int" },
  { key: "receptions", label: "REC", source: "base", format: "int" },
  { key: "rec_yards", label: "RecYDS", source: "base", format: "int" },
  { key: "rec_tds", label: "RecTD", source: "base", format: "int" },
  { key: "avg_yac", label: "YAC", source: "receiving", format: "float" },
  { key: "avg_separation", label: "SEP", source: "receiving", format: "float" },
];

export const WR_GAME_LOG_COLS: GameLogColumn[] = [
  { key: "offense_snaps", label: "SNP", source: "snap", format: "int" },
  { key: "offense_pct", label: "SNP%", source: "snap", format: "pct" },
  { key: "targets", label: "TGT", source: "base", format: "int" },
  { key: "receptions", label: "REC", source: "base", format: "int" },
  { key: "rec_yards", label: "YDS", source: "base", format: "int" },
  { key: "rec_tds", label: "TD", source: "base", format: "int" },
  { key: "catch_percentage", label: "CATCH%", source: "receiving", format: "pct" },
  { key: "avg_yac", label: "YAC", source: "receiving", format: "float" },
  { key: "avg_yac_above_expectation", label: "YAC+", source: "receiving", format: "float" },
  { key: "avg_separation", label: "SEP", source: "receiving", format: "float" },
  { key: "avg_cushion", label: "CUSH", source: "receiving", format: "float" },
  { key: "rush_attempts", label: "RuATT", source: "base", format: "int" },
  { key: "rush_yards", label: "RuYDS", source: "base", format: "int" },
];

export const TE_GAME_LOG_COLS: GameLogColumn[] = WR_GAME_LOG_COLS;

export const DEF_GAME_LOG_COLS: GameLogColumn[] = [
  { key: "offense_snaps", label: "OFF", source: "snap", format: "int" },
  { key: "defense_snaps", label: "DEF", source: "snap", format: "int" },
  { key: "defense_pct", label: "DEF%", source: "snap", format: "pct" },
  { key: "st_snaps", label: "ST", source: "snap", format: "int" },
];

export const KP_GAME_LOG_COLS: GameLogColumn[] = [
  { key: "st_snaps", label: "ST", source: "snap", format: "int" },
  { key: "st_pct", label: "ST%", source: "snap", format: "pct" },
];

