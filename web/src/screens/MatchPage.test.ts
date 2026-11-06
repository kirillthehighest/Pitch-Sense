import { describe, expect, it } from "vitest";
import type { Forecast, Outcome, Prediction } from "../types";
import { consensusText } from "./MatchPage";

function prediction(model: string, most_likely: Outcome): Prediction {
  return { model, label: model, home: 0.4, draw: 0.3, away: 0.3, most_likely, hit: null, expected_goals: null };
}

function match(predictions: Prediction[]): Forecast {
  return {
    competition: "I1",
    season: "2026-27",
    date: "2026-11-08",
    kickoff: null,
    home_team: "Napoli",
    away_team: "Lazio",
    home_goals: null,
    away_goals: null,
    result: null,
    postponed: false,
    as_of: null,
    hypothetical: false,
    predictions,
  };
}

describe("the models' consensus in the match head", () => {
  it("names the club all models favour", () => {
    const all = [prediction("Elo", "H"), prediction("Poisson", "H"), prediction("Logistic regression", "H")];
    expect(consensusText(match(all))).toBe("Toate trei modelele mizează pe Napoli");
  });

  it("counts a majority, a draw included", () => {
    const two = [prediction("Elo", "D"), prediction("Poisson", "D"), prediction("Logistic regression", "A")];
    expect(consensusText(match(two))).toBe("2 din 3 modele mizează pe egal");
  });

  it("says when the models disagree or none could predict", () => {
    const split = [prediction("Elo", "H"), prediction("Poisson", "D"), prediction("Logistic regression", "A")];
    expect(consensusText(match(split))).toBe("Modelele nu cad de acord");
    expect(consensusText(match([]))).toBe("Niciun model nu are destule meciuri anterioare");
  });
});
