// The client of the local server (app/api). In the desktop shell, Tauri starts the server and
// tells its address; while developing, the address comes from VITE_BACKEND.
import type { Day, Days, Forecast, League, Preferences, Standings, Status } from "./types";

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
      const url = await invoke<string | null>("backend_url");
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${await backend()}${path}`, init);
  if (!response.ok) {
    throw new Error(`${response.status}: ${await response.text()}`);
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
  preferences: () => request<Preferences>("/api/preferences"),
  setPreferences: (preferences: Preferences) =>
    request<Preferences>("/api/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(preferences),
    }),
};
