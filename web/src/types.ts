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
