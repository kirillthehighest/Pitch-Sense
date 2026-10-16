// The shapes of the server's answers (app/api/schemas.py).

export type Outcome = "H" | "D" | "A";

export interface League {
  code: string;
  name: string;
  country: string;
  seasons: string[];
  current_season: string | null;
  updated_at: string | null;
  prepared: boolean;
  photo_credit: string | null;
  photo_top: number;
  problem: string | null;
}

export interface Status {
  prepared: Record<string, boolean>;
  preparing: string | null;
  failures: Record<string, string>;
}

export interface Prediction {
  model: string;
  label: string;
  home: number;
  draw: number;
  away: number;
  most_likely: Outcome;
  hit: boolean | null;
  expected_goals: [number, number] | null;
}

export interface Forecast {
  competition: string;
  season: string;
  date: string;
  kickoff: string | null;
  home_team: string;
  away_team: string;
  home_goals: number | null;
  away_goals: number | null;
  result: Outcome | null;
  postponed: boolean;
  as_of: string | null;
  hypothetical: boolean;
  predictions: Prediction[];
}

export interface LeagueDay {
  code: string;
  name: string;
  country: string;
  prepared: boolean;
  forecasts: Forecast[];
}

export interface Day {
  day: string;
  leagues: LeagueDay[];
  featured: Forecast | null;
}

export interface Days {
  days: string[];
  today: string;
  next_day: string | null;
}

export interface Favourite {
  competition: string;
  team: string;
}

export interface Preferences {
  competition: string | null;
  favourite: Favourite | null;
}

export const MODELS = ["Logistic regression", "Elo", "Poisson"] as const;
export const MODEL_LABELS: Record<string, string> = {
  Elo: "Elo",
  Poisson: "Poisson",
  "Logistic regression": "Regresie logistică",
};

export interface TeamRecord {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
}

export interface StandingRow {
  position: number;
  team: string;
  record: TeamRecord;
  form: string[];
}

export interface Standings {
  competition: string;
  season: string;
  before: string;
  whole_season: boolean;
  in_progress: boolean;
  rows: StandingRow[];
}

export interface TeamState {
  team: string;
  position: number;
  record: TeamRecord;
  form: string[];
  rating: number;
}

export interface ScoreChance {
  home: number;
  away: number;
  probability: number;
}

export interface PoissonScores {
  expected_goals: [number, number];
  top_scores: ScoreChance[];
  grid: number[][]; // grid[i][j]: the home team scores i and the away team j
}

export interface MatchPage {
  forecast: Forecast;
  status: string;
  knowledge: string;
  verdict: string | null;
  explanations: Record<string, string>;
  poisson: PoissonScores | null;
  before: string;
  teams: number;
  home: TeamState;
  away: TeamState;
}

/** A match to open: of the calendar, or two teams of a season on a day (hypothetical). */
export interface MatchKey {
  code: string;
  season: string;
  day: string;
  home: string;
  away: string;
}

export interface SeasonDays {
  season: string;
  teams: string[];
  first_day: string;
  last_day: string;
  suggested_day: string;
}

export interface Shots {
  matches: number;
  shots: number | null;
  opponent_shots: number | null;
  shots_on_target: number | null;
  opponent_shots_on_target: number | null;
}

export interface RatingSeason {
  season: string;
  points: { day: string; rating: number }[];
}

export interface GroupPoint {
  team?: string;
  goals_scored: number;
  goals_conceded: number;
  group: number;
}

export interface Groups {
  teams: GroupPoint[];
  centres: GroupPoint[];
  names: Record<string, string>;
}

export interface TeamPage {
  competition: string;
  team: string;
  season: string;
  position: number;
  teams: number;
  in_progress: boolean;
  record: TeamRecord;
  home: TeamRecord;
  away: TeamRecord;
  form: string[];
  shots: Shots;
  pre_season_group: string;
  season_group: string | null;
  elo: RatingSeason[];
  groups: Groups | null;
  groups_problem: string | null;
}

export interface ReviewedMatch {
  forecast: Forecast;
  chance: number;
  hit: boolean;
  surprise: boolean;
}

export interface Review {
  competition: string;
  season: string;
  model: string;
  label: string;
  surprise_chance: number;
  matches: number;
  hits: number;
  surprises: number;
  by_result: { result: Outcome; label: string; hits: number; matches: number }[];
  rows: ReviewedMatch[];
}
