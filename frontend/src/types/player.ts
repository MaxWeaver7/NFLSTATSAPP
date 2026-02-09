export interface PlayerGameLog {
  season: number;
  week: number;
  game_id: string;
  team: string;
  opponent: string;
  home_team: string;
  away_team: string;
  location: 'home' | 'away';
  is_postseason?: number | boolean;
  // Receiving
  targets: number;
  receptions: number;
  rec_yards: number;
  rec_tds: number;
  air_yards: number;
  yac: number;
  // Rushing
  rush_attempts: number;
  rush_yards: number;
  rush_tds: number;
  // Passing (for QBs)
  passing_attempts?: number;
  passing_completions?: number;
  passing_yards?: number;
  passing_tds?: number;
  interceptions?: number;
  qb_rating?: number | null;
  qbr?: number | null;
}

export interface Player {
  player_id: string;
  player_name: string;
  team: string | null;
  position: string | null;
  // Bio (BallDontLie roster fields)
  height?: string | null;
  weight?: string | null;
  jersey_number?: string | null;
  college?: string | null;
  experience?: string | null;
  age?: number | null;
  teamColors?: { primary?: string | null; secondary?: string | null };
  season?: number;
  games?: number;
  targets?: number;
  receptions?: number;
  receivingYards?: number;
  receivingTouchdowns?: number;
  avgYardsPerCatch?: number;
  rushAttempts?: number;
  rushingYards?: number;
  rushingTouchdowns?: number;
  avgYardsPerRush?: number;
  passingAttempts?: number;
  passingCompletions?: number;
  passingYards?: number;
  passingTouchdowns?: number;
  passingInterceptions?: number;
  qbRating?: number | null;
  qbr?: number | null;
  photoUrl?: string;
  gameLogs?: PlayerGameLog[];
  seasonTotals?: {
    season: number;
    games: number;
    targets: number;
    receptions: number;
    receivingYards: number;
    receivingTouchdowns: number;
    avgYardsPerCatch: number;
    rushAttempts: number;
    rushingYards: number;
    rushingTouchdowns: number;
    avgYardsPerRush: number;
    passingAttempts?: number;
    passingCompletions?: number;
    passingYards?: number;
    passingTouchdowns?: number;
    passingInterceptions?: number;
    qbRating?: number | null;
    qbr?: number | null;
  };
}

export type GoatAdvancedRow = Record<string, any>;

export interface GoatAdvancedPayload {
  regular: {
    receiving: GoatAdvancedRow[];
    rushing: GoatAdvancedRow[];
    passing: GoatAdvancedRow[];
  };
  postseasonTotals?: {
    receiving: GoatAdvancedRow[];
    rushing: GoatAdvancedRow[];
    passing: GoatAdvancedRow[];
  };
}

export interface FilterOptions {
  seasons: number[];
  weeks: number[];
  teams: string[];
  positions: string[];
}

