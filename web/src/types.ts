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
  "Past frequencies": "Frecvențele trecute", // the references of the evaluation
  "Always home win": "Mereu victoria gazdelor",
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

// --- Analiză ---

export interface About {
  explanations: { title: string; text: string }[];
  groups: string;
  sources: { title: string; text: string }[];
  crests: number;
  photos: string[];
  images_note: string;
}

export interface Estimate {
  value: number;
  margin: number | null;
}

export interface SeasonCheck {
  competition: string;
  season: string | null;
  state: "ready" | "missing" | "preparing" | "empty";
  matches: number;
  first_day: string | null;
  last_day: string | null;
  models: { model: string; label: string; accuracy: number; brier: Estimate; log_loss: Estimate }[];
}

export interface Difference {
  first: string;
  second: string;
  first_label: string;
  second_label: string;
  measure: string;
  measure_label: string;
  mean: number;
  lower: number;
  upper: number;
  better: string | null;
  better_label: string | null;
}

export interface CalibrationBin {
  lower: number;
  upper: number;
  count: number;
  predicted: number | null;
  observed: number | null;
}

export interface ModelEvaluation {
  model: string;
  label: string;
  matches: number;
  accuracy: number;
  brier: number | null;
  log_loss: number | null;
  calibration_error: number | null;
  goals_error: number | null;
  calibration: CalibrationBin[] | null;
  confusion: number[][];
}

export interface Subset {
  key: string;
  label: string;
  matches: number;
  brier: Record<string, number>;
  best: string;
  best_label: string;
  real: boolean;
}

export interface Agreement {
  first: string;
  second: string;
  first_label: string;
  second_label: string;
  same: number;
  distance: number;
}

export interface Evaluation {
  competition: string;
  has_log: boolean;
  problem: string | null;
  matches: number;
  first_season: string | null;
  last_season: string | null;
  compared: string[];
  models: ModelEvaluation[];
  differences: Difference[];
  by_season: Subset[];
  by_outcome: Subset[];
  by_matchup_type: Subset[];
  agreements: Agreement[];
  all_agree: number | null;
}

export interface LeagueResult {
  code: string;
  name: string;
  character: {
    matches: number;
    home_win: number;
    draw: number;
    away_win: number;
    goals: number;
    home_margin: number;
    closed_doors_home_win: number | null;
    other_seasons_home_win: number | null;
  };
  brier: Record<string, number>;
  best: string;
  best_label: string;
  skill: Record<string, number>;
  differences: Difference[];
}

export interface LeaguesComparison {
  missing: string[];
  problem: string | null;
  matches: number;
  compared: string[];
  reference: string;
  results: LeagueResult[];
  pooled: Difference[];
}
