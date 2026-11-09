import { describe, expect, it } from "vitest";
import type { Forecast, Prediction } from "../types";
import { chipLabel, isPending, likelyScore, rowName, statusText } from "./MatchRow";

const prediction: Prediction = {
  model: "Elo",
  label: "Elo",
  home: 0.5,
  draw: 0.3,
  away: 0.2,
  most_likely: "H",
  hit: true,
  expected_goals: null,
  likely_score: null,
};

function match(changes: Partial<Forecast>): Forecast {
  return {
    competition: "SP1",
    season: "2026-27",
    date: "2026-10-30",
    kickoff: "21:00",
    home_team: "Villarreal",
    away_team: "Espanol",
    home_goals: null,
    away_goals: null,
    result: null,
    postponed: false,
    as_of: "2026-10-30",
    hypothetical: false,
    predictions: [prediction],
    ...changes,
  };
}

describe("a match of a list", () => {
  it("is pending when its day has passed without a result", () => {
    expect(isPending(match({}), "2026-11-06")).toBe(true);
    expect(isPending(match({}), "2026-10-30")).toBe(false); // today: still to come
    expect(isPending(match({ result: "H", home_goals: 2, away_goals: 0 }), "2026-11-06")).toBe(false);
    expect(isPending(match({ postponed: true }), "2026-11-06")).toBe(false);
    expect(isPending(match({ hypothetical: true }), "2026-11-06")).toBe(false);
  });

  it("says what its left column shows", () => {
    expect(statusText(match({}), false, "2026-10-29")).toBe("21:00");
    expect(statusText(match({}), false, "2026-11-06")).toBe("Fără rezultat");
    expect(statusText(match({ postponed: true }), false, "2026-11-06")).toBe("Amânat");
    expect(statusText(match({ result: "D", home_goals: 1, away_goals: 1 }))).toBe("Final");
    expect(statusText(match({}), true)).toBe("30.10");
  });

  it("names each chip for a screen reader", () => {
    expect(chipLabel(prediction, "H", "H")).toBe("Gazde 50%, cel mai probabil, nimerit, rezultatul meciului");
    expect(chipLabel(prediction, "D", "H")).toBe("Egal 30%");
  });

  it("names the whole row with the score and the chances", () => {
    const played = match({ result: "H", home_goals: 2, away_goals: 0 });
    expect(rowName(played, prediction)).toBe(
      "Villarreal 2–0 Espanyol, 30.10. Elo: Gazde 50%, cel mai probabil, nimerit, rezultatul meciului; Egal 30%; Oaspeți 20%",
    );
  });
});

describe("the likely score between the teams", () => {
  const elo: Prediction = { ...prediction, likely_score: [1, 0] };
  const poisson: Prediction = { ...prediction, model: "Poisson", most_likely: "A", likely_score: [0, 1] };
  const coming = match({ date: "2099-01-01", predictions: [elo, poisson] });

  it("is the chosen model's own, for a match still to come only", () => {
    expect(likelyScore(coming, "Elo")).toEqual([1, 0]);
    expect(likelyScore(coming, "Poisson")).toEqual([0, 1]);
    expect(likelyScore({ ...coming, result: "H", home_goals: 2, away_goals: 0 }, "Elo")).toBeNull();
    expect(likelyScore({ ...coming, date: "2020-01-01" }, "Elo")).toBeNull(); // past, no result yet
    expect(likelyScore({ ...coming, postponed: true }, "Elo")).toBeNull();
  });
});
