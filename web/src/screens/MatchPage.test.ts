import { describe, expect, it } from "vitest";
import type { Forecast, Outcome, Prediction } from "../types";
import { consensusText, modelReason } from "./MatchPage";

function prediction(model: string, most_likely: Outcome): Prediction {
  return { model, label: model, home: 0.4, draw: 0.3, away: 0.3, most_likely, hit: null, expected_goals: null, likely_score: null };
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
    expect(consensusText(match(all))).toBe("Toate cele trei modele o văd favorită pe Napoli");
  });

  it("counts a majority, a draw included", () => {
    const two = [prediction("Elo", "D"), prediction("Poisson", "D"), prediction("Logistic regression", "A")];
    expect(consensusText(match(two))).toBe("2 din 3 modele văd egalul cel mai probabil");
  });

  it("says when the favourite leads by a hair", () => {
    const close = [{ ...prediction("Elo", "A"), home: 0.36, draw: 0.27, away: 0.37 }];
    expect(consensusText(match(close))).toBe("Singurul model o vede favorită pe Lazio, la limită");
  });

  it("writes the clubs' full names", () => {
    const forecast = { ...match([prediction("Elo", "H")]), home_team: "Ath Madrid" };
    expect(consensusText(forecast)).toBe("Singurul model o vede favorită pe Atlético Madrid");
  });

  it("says when the models disagree or none could predict", () => {
    const split = [prediction("Elo", "H"), prediction("Poisson", "D"), prediction("Logistic regression", "A")];
    expect(consensusText(match(split))).toBe("Modelele nu cad de acord");
    expect(consensusText(match([]))).toBe("Niciun model nu are destule meciuri anterioare");
  });
});

describe("why a model sees a match as it does", () => {
  const page = {
    forecast: match([{ ...prediction("Poisson", "H"), likely_score: [1, 0] as [number, number] }]),
    home: { team: "Napoli", position: 2, record: { played: 10, points: 22 }, form: ["W", "D", "L", "W", "W"], rating: 1650 },
    away: { team: "Lazio", position: 8, record: { played: 10, points: 14 }, form: ["L", "L", "D", "W", "D"], rating: 1580 },
    poisson: { expected_goals: [1.62, 0.94], top_scores: [], grid: [] },
    elo_home_advantage: 100,
  } as unknown as Parameters<typeof modelReason>[1];

  it("states Elo's ratings and the home advantage", () => {
    expect(modelReason("Elo", page)).toBe(
      "Ratingul Elo: Napoli 1.650, Lazio 1.580. Terenul propriu valorează 100 de puncte, deci Napoli pornește cu 170 de puncte înainte.",
    );
  });

  it("states Poisson's expected goals and its favourite's likeliest score", () => {
    expect(modelReason("Poisson", page)).toContain("Goluri așteptate: Napoli 1,62, Lazio 0,94.");
    expect(modelReason("Poisson", page)).toContain("scorul cel mai probabil e 1–0");
  });

  it("states the differences the logistic regression weighs", () => {
    expect(modelReason("Logistic regression", page)).toContain("Napoli 2,20 puncte pe meci, Lazio 1,40");
    expect(modelReason("Logistic regression", page)).toContain("forma, 10 față de 5 puncte");
  });
});
