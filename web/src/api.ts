// The client of the local server (app/api). In the desktop shell, Tauri starts the server and
// tells its address; while developing, the address comes from VITE_BACKEND.
import type {
  About,
  Day,
  Days,
  Evaluation,
  Forecast,
  League,
  LeaguesComparison,
  MatchKey,
  MatchPage,
  Preferences,
  Projection,
  Review,
  SeasonCheck,
  SeasonDays,
  Standings,
  Status,
  TeamPage,
  TrackRecord,
} from "./types";

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

let base: Promise<string> | null = null;

async function resolveBase(): Promise<string> {
  if (window.__TAURI_INTERNALS__) {
    const { invoke } = await import("@tauri-apps/api/core");
    for (;;) {
      let url: string | null;
      try {
        url = await invoke<string | null>("backend_url");
      } catch (problem) {
        throw new Error(String(problem)); // the server stopped before it listened, and why
      }
      if (url) return url;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  return import.meta.env.VITE_BACKEND ?? "http://127.0.0.1:8765";
}

export function backend(): Promise<string> {
  base ??= resolveBase();
  return base;
}

/**
 * Ask until the server answers: while it starts it may not take questions yet. Asks again every
 * `retryMs`; once `failuresShown` attempts in a row have failed, tells `onSilent` why (after each
 * further failure). Gives up, with `undefined`, when `cancelled` says so.
 */
export async function askUntilAnswered<T>(
  ask: () => Promise<T>,
  onSilent: (message: string) => void,
  cancelled: () => boolean,
  retryMs = 1000,
  failuresShown = 3,
): Promise<T | undefined> {
  for (let failures = 1; ; failures += 1) {
    try {
      return await ask();
    } catch (reason) {
      if (cancelled()) return undefined;
      if (failures >= failuresShown) onSilent(reason instanceof Error ? reason.message : String(reason));
    }
    await new Promise((resolve) => setTimeout(resolve, retryMs));
    if (cancelled()) return undefined;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${await backend()}${path}`, init);
  if (!response.ok) {
    let detail = await response.text();
    try {
      detail = JSON.parse(detail).detail ?? detail; // FastAPI's {"detail": "..."}
    } catch {
      // not JSON: keep the text
    }
    throw new Error(`${response.status}: ${detail}`);
  }
  return (await response.json()) as T;
}

export async function imageUrl(path: string): Promise<string> {
  return `${await backend()}${path}`;
}

export const api = {
  leagues: () => request<League[]>("/api/leagues"),
  status: () => request<Status>("/api/status"),
  days: () => request<Days>("/api/days"),
  day: (day: string, league: string) =>
    request<Day>(`/api/day/${day}?league=${encodeURIComponent(league)}`),
  standings: (code: string, season?: string, before?: string) => {
    const query = new URLSearchParams();
    if (season) query.set("season", season);
    if (before) query.set("before", before);
    return request<Standings>(`/api/standings/${code}?${query}`);
  },
  teams: (code: string, season?: string) =>
    request<string[]>(`/api/teams/${code}${season ? `?season=${season}` : ""}`),
  teamMatches: (code: string, team: string, season?: string) =>
    request<Forecast[]>(
      `/api/team-matches/${code}?team=${encodeURIComponent(team)}${season ? `&season=${season}` : ""}`,
    ),
  match: (key: MatchKey) => {
    const query = new URLSearchParams({ season: key.season, day: key.day, home: key.home, away: key.away });
    return request<MatchPage>(`/api/match/${key.code}?${query}`);
  },
  season: (code: string, season: string) =>
    request<SeasonDays>(`/api/season/${code}?season=${encodeURIComponent(season)}`),
  team: (code: string, season: string, team?: string | null) => {
    const query = new URLSearchParams({ season });
    if (team) query.set("team", team);
    return request<TeamPage>(`/api/team/${code}?${query}`);
  },
  review: (code: string, season: string, model: string) =>
    request<Review>(`/api/review/${code}?${new URLSearchParams({ season, model })}`),
  trackRecord: (code: string) => request<TrackRecord>(`/api/track-record/${code}`),
  projection: (code: string, model: string) =>
    request<Projection>(`/api/projection/${code}?${new URLSearchParams({ model })}`),
  about: () => request<About>("/api/about"),
  seasonCheck: (code: string) => request<SeasonCheck>(`/api/season-check/${code}`),
  evaluation: (code: string) => request<Evaluation>(`/api/evaluation/${code}`),
  backtest: (code: string) => request<Evaluation>(`/api/evaluation/${code}/backtest`, { method: "POST" }),
  leaguesComparison: () => request<LeaguesComparison>("/api/leagues-comparison"),
  leaguesBacktest: () => request<LeaguesComparison>("/api/leagues-comparison/backtest", { method: "POST" }),
  update: () => request<{ summary: string }>("/api/update", { method: "POST" }),
  preferences: () => request<Preferences>("/api/preferences"),
  setPreferences: (preferences: Preferences) =>
    request<Preferences>("/api/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(preferences),
    }),
};
