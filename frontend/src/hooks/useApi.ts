import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Player, FilterOptions, PlayerGameLog } from '@/types/player';

const API_BASE = '/api';

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export function useFilterOptions() {
  return useQuery({
    queryKey: ['options'],
    queryFn: () => fetchJson<FilterOptions>(`${API_BASE}/options`),
    staleTime: 1000 * 60 * 10,
  });
}

type PlayersResponse = { players: Player[]; nextOffset?: number; hasMore?: boolean };

export interface RosterPlayer {
  player_id: string;
  player_name: string;
  first_name: string;
  last_name: string;
  position: string;
  depth: number;
  jersey_number: string | number | null;
  height: string;
  weight: string;
  college: string;
  age: number;
  injury_status: string | null;
  photoUrl: string | null;
}

export function usePlayers(
  season?: number,
  position?: string,
  team?: string,
  q?: string,
  offset: number = 0,
  limit: number = 250
) {
  const params = new URLSearchParams();
  if (season) params.set('season', season.toString());
  if (position) params.set('position', position);
  if (team) params.set('team', team);
  if (q) params.set('q', q);
  params.set('offset', String(Math.max(offset || 0, 0)));
  params.set('limit', String(Math.max(limit || 0, 1)));

  return useQuery({
    queryKey: ['players', season, position, team, q || '', offset, limit],
    queryFn: () => fetchJson<PlayersResponse>(`${API_BASE}/players?${params.toString()}`),
    enabled: !!season,
    placeholderData: keepPreviousData,
    staleTime: 1000 * 10,
  });
}


export interface RankedStat {
  value: number | null;
  rank: number;
  total: number;
}

export interface SnapWeek {
  week: number;
  offense_snaps: number;
  offense_pct: number;
  defense_snaps: number;
  defense_pct: number;
  st_snaps: number;
  st_pct: number;
}

export interface PlayerDetailResponse {
  player: Player;
  gameLogs: PlayerGameLog[];
  seasonAdvanced: {
    passing?: Record<string, number | null>;
    rushing?: Record<string, number | null>;
    receiving?: Record<string, number | null>;
  };
  rankings: Record<string, RankedStat>;
  snapHistory: SnapWeek[];
  advancedGameLogs: Record<string, {
    passing?: Record<string, number | null>;
    rushing?: Record<string, number | null>;
    receiving?: Record<string, number | null>;
  }>;
}

export function usePlayerDetail(playerId: string, season: number) {
  return useQuery({
    queryKey: ['player', playerId, season],
    queryFn: () => fetchJson<PlayerDetailResponse>(`${API_BASE}/player/${playerId}?season=${season}`),
    enabled: !!playerId && !!season,
  });
}

export function useSummary() {
  return useQuery({
    queryKey: ['summary'],
    queryFn: () => fetchJson<any>(`${API_BASE}/summary`),
  });
}

// Injury status types
export interface InjuryInfo {
  status: string;
  comment: string;
  injury_date: string;
}

export type InjuryMap = Record<string, InjuryInfo>;

export function useInjuries() {
  return useQuery({
    queryKey: ['injuries'],
    queryFn: () => fetchJson<{ injuries: InjuryMap }>(`${API_BASE}/injuries`),
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
    select: (data) => data.injuries,
  });
}


export interface TeamStanding {
  team: string;
  team_name: string;
  team_id: number;
  wins: number;
  losses: number;
  ties: number;
  pf: number;
  pa: number;
  diff?: number;
  ats_wins: number;
  ats_losses: number;
  ats_pushes: number;
  ats_w?: number;
  ats_l?: number;
  ats_p?: number;
  win_pct: number;
  primary_color: string;
  secondary_color: string;
  division: string;
  games: number;
  pass_yards?: number;
  rush_yards?: number;
  total_yards?: number;
  total_tds?: number;
  turnovers?: number;
  offense_ypg?: number;
  playoff_seed?: number;
  win_streak?: number;
  strk?: number;
  conference_record?: string;
  division_record?: string;
  home_record?: string;
  road_record?: string;
  division_rank?: number;
}

export interface TeamScheduleItem {
  week: number;
  gameday: string | null;
  opponent: string;
  is_home: boolean;
  score: string | null;
  result: "W" | "L" | "T" | null;
  ats_result: "W" | "L" | "P" | null;
  spread: number | null;
}

export interface TeamSeasonStats {
  [key: string]: any;
}

export interface TeamSnapsResponse {
  week: number | null;
  offense: Array<Record<string, any>>;
  defense: Array<Record<string, any>>;
  st: Array<Record<string, any>>;
  season?: {
    offense: Array<Record<string, any>>;
    defense: Array<Record<string, any>>;
    st: Array<Record<string, any>>;
  };
}

export interface TeamLeaders {
  [key: string]: any;
}

export function useStandings(season: number = 2025) {
  return useQuery({
    queryKey: ['standings', season],
    queryFn: () => fetchJson<{ rows: TeamStanding[] }>(`${API_BASE}/teams/standings?season=${season}`),
    staleTime: 1000 * 60 * 5,
    select: (data) => data.rows
  });
}


export interface WeeklyGame {
  nflverse_game_id: string;
  season: number;
  week: number;
  gameday: string;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  spread_line: number | null;
  total_line?: number | null;
  home_moneyline?: number | null;
  away_moneyline?: number | null;
  home_color?: string;
  away_color?: string;
  home_name?: string;
  away_name?: string;
  game_type?: string;
  conference?: string;
}

export function useWeeklySchedule(season: number, week: number) {
  return useQuery({
    queryKey: ['schedule', season, week],
    queryFn: () => fetchJson<{ rows: WeeklyGame[] }>(`${API_BASE}/schedule?season=${season}&week=${week}`),
    select: (data) => data.rows,
  });
}

export function usePlayoffs(season: number) {
  return useQuery({
    queryKey: ['playoffs', season],
    queryFn: () => fetchJson<{ rows: WeeklyGame[] }>(`${API_BASE}/playoffs?season=${season}`),
    select: (data) => data.rows,
  });
}

export function useTeamRoster(team: string, season: number = 2025) {
  return useQuery({
    queryKey: ['roster', team, season],
    queryFn: () => fetchJson<{ players: RosterPlayer[] }>(`${API_BASE}/team/roster?team=${team}&season=${season}`),
    enabled: !!team,
    select: (data) => data.players
  });
}

export function useTeamSchedule(team: string, season: number = 2025) {
  return useQuery({
    queryKey: ['schedule', team, season],
    queryFn: () => fetchJson<{ rows: TeamScheduleItem[] }>(`${API_BASE}/teams/schedule?team=${team}&season=${season}`),
    enabled: !!team,
    select: (data) => data.rows
  });
}

export function useTeamSeasonStats(team: string, season: number = 2025, seasonType: number = 2) {
  return useQuery({
    queryKey: ['team-season-stats', team, season, seasonType],
    queryFn: () => fetchJson<{ row: TeamSeasonStats }>(`${API_BASE}/team/season-stats?team=${team}&season=${season}&season_type=${seasonType}`),
    enabled: !!team,
    staleTime: 1000 * 60 * 10,
    select: (data) => data.row
  });
}

export function useTeamSnaps(team: string, season: number = 2025) {
  return useQuery({
    queryKey: ['team-snaps', team, season],
    queryFn: () => fetchJson<{ rows: TeamSnapsResponse }>(`${API_BASE}/team/snaps?team=${team}&season=${season}`),
    enabled: !!team,
    staleTime: 1000 * 60 * 10,
    select: (data) => data.rows
  });
}

export function useTeamLeaders(team: string, season: number = 2025) {
  return useQuery({
    queryKey: ['team-leaders', team, season],
    queryFn: () => fetchJson<{ row: TeamLeaders }>(`${API_BASE}/team/leaders?team=${team}&season=${season}`),
    enabled: !!team,
    staleTime: 1000 * 60 * 10,
    select: (data) => data.row
  });
}

export function useMatchupHistory(teamA: string, teamB: string) {
  return useQuery({
    queryKey: ['matchup_history', teamA, teamB],
    queryFn: () => fetchJson<{ rows: WeeklyGame[] }>(`${API_BASE}/matchup_history?team_a=${teamA}&team_b=${teamB}&limit=5`),
    enabled: !!teamA && !!teamB,
    select: (data) => data.rows
  });
}


// --- Game Detail ---

export interface ComparisonStat {
  label: string;
  key: string;
  home: number | null;
  away: number | null;
  higher_is_better: boolean;
}

export interface PropVendor {
  vendor: string;
  odds?: number;
  over_odds?: number;
  under_odds?: number;
  line_value?: number;
}

export interface PlayerProp {
  player_name: string;
  player_id: number;
  position: string;
  team_id: number;
  prop_type: string;
  market_type: "anytime_td" | "over_under";
  line_value: number | null;
  best_odds?: number;
  best_vendor?: string;
  best_over_odds?: number;
  best_over_vendor?: string;
  best_under_odds?: number;
  best_under_vendor?: string;
  all_vendors: PropVendor[];
}

export interface GameDetailResponse {
  game: WeeklyGame & {
    home_abbr: string;
    away_abbr: string;
    home_name: string;
    away_name: string;
    home_color: string;
    away_color: string;
    home_team_id?: number;
    away_team_id?: number;
    home_secondary?: string;
    away_secondary?: string;
    home_conference?: string;
    away_conference?: string;
    home_record: string;
    away_record: string;
    home_seed?: number;
    away_seed?: number;
    home_conf_record?: string;
    away_conf_record?: string;
    home_div_record?: string;
    away_div_record?: string;
    is_played: boolean;
    total_line?: number;
    home_moneyline?: number;
    away_moneyline?: number;
    overtime?: string;
    stadium?: string;
    roof?: string;
    surface?: string;
    temp?: number;
    wind?: number;
    referee?: string;
    home_coach?: string;
    away_coach?: string;
    game_type?: string;
  };
  win_probability: { home: number; away: number };
  comparison: { stats: ComparisonStat[] };
  leaders: {
    home: Record<string, any>;
    away: Record<string, any>;
  };
  props: {
    anytime_td: PlayerProp[];
    over_under: PlayerProp[];
  };
  history: WeeklyGame[];
  preview_text: string | null;
  error?: string;
}

export function useGameDetail(gameId: string) {
  return useQuery({
    queryKey: ['game-detail', gameId],
    queryFn: () => fetchJson<GameDetailResponse>(`${API_BASE}/game/${gameId}`),
    enabled: !!gameId,
    staleTime: 1000 * 60 * 5,
  });
}

export function useLatestWeek(season: number) {
  return useQuery({
    queryKey: ['latest-week', season],
    queryFn: () => fetchJson<{ week: number }>(`${API_BASE}/latest-week?season=${season}`),
    staleTime: 1000 * 60 * 5,
    select: (data) => data.week,
  });
}
