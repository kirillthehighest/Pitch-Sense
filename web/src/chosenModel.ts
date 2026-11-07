// The model chosen in the interface (Phase 26): one choice for the whole app, so Meciuri,
// Clasament's projection and Predicții always show the same model's chances. It lives for the
// session; the default is logistic regression (the lowest pooled Brier score, docs/leagues.md).
import { useSyncExternalStore } from "react";
import { MODELS } from "./types";

let chosen: string = MODELS[0];
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Sets the chosen model, from a name or from the current one (`setModel(nextModel)`). */
export function setChosenModel(next: string | ((current: string) => string)): void {
  const value = typeof next === "function" ? next(chosen) : next;
  if (value === chosen) return;
  chosen = value;
  listeners.forEach((listener) => listener());
}

/** The chosen model and its setter, as `useState` gives them. */
export function useChosenModel(): [string, typeof setChosenModel] {
  return [useSyncExternalStore(subscribe, () => chosen), setChosenModel];
}
