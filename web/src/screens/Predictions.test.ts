import { describe, expect, it } from "vitest";
import type { Forecast, ReviewedMatch } from "../types";
import { chosenRows } from "./Predictions";

function row(day: string, chance: number, hit: boolean, home: number): ReviewedMatch {
  const forecast = {
    date: day,
    predictions: [{ model: "Elo", home, draw: (1 - home) / 2, away: (1 - home) / 2 }],
  } as unknown as Forecast;
  return { forecast, chance, hit, surprise: chance < 0.2 };
}

describe("the matches of a review", () => {
  const rows = [row("2025-08-16", 0.5, true, 0.5), row("2025-08-23", 0.1, false, 0.7), row("2025-08-30", 0.3, false, 0.4)];

  it("keeps the kind asked for", () => {
    expect(chosenRows(rows, "all", "recent", "Elo")).toHaveLength(3);
    expect(chosenRows(rows, "hits", "recent", "Elo").map((r) => r.forecast.date)).toEqual(["2025-08-16"]);
    expect(chosenRows(rows, "misses", "recent", "Elo")).toHaveLength(2);
    expect(chosenRows(rows, "surprises", "recent", "Elo").map((r) => r.chance)).toEqual([0.1]);
  });

  it("orders the latest first, the biggest surprises first or the surest first", () => {
    expect(chosenRows(rows, "all", "recent", "Elo").map((r) => r.forecast.date)[0]).toBe("2025-08-30");
    expect(chosenRows(rows, "all", "surprising", "Elo").map((r) => r.chance)).toEqual([0.1, 0.3, 0.5]);
    expect(chosenRows(rows, "all", "confident", "Elo").map((r) => r.forecast.date)[0]).toBe("2025-08-23");
  });
});
