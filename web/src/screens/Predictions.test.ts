import { describe, expect, it } from "vitest";
import type { Forecast, ReviewedMatch } from "../types";
import { byWeek, chosenRows, weekOf, weekText } from "./Predictions";

function row(day: string, chance: number, hit: boolean, home: number): ReviewedMatch {
  const forecast = {
    date: day,
    predictions: [{ model: "Elo", home, draw: (1 - home) / 2, away: (1 - home) / 2 }],
  } as unknown as Forecast;
  return { forecast, chance, hit, surprise: chance < 0.2, confidence: Math.max(home, (1 - home) / 2) };
}

describe("the matches of a review", () => {
  const rows = [row("2025-08-16", 0.5, true, 0.5), row("2025-08-23", 0.1, false, 0.7), row("2025-08-30", 0.3, false, 0.4)];

  it("keeps the kind asked for", () => {
    expect(chosenRows(rows, "all", "recent")).toHaveLength(3);
    expect(chosenRows(rows, "hits", "recent").map((r) => r.forecast.date)).toEqual(["2025-08-16"]);
    expect(chosenRows(rows, "misses", "recent")).toHaveLength(2);
    expect(chosenRows(rows, "surprises", "recent").map((r) => r.chance)).toEqual([0.1]);
    expect(chosenRows(rows, "sure", "recent").map((r) => r.forecast.date)).toEqual(["2025-08-23"]); // 70% ≥ 65%
  });

  it("orders the latest first, the biggest surprises first or the surest first", () => {
    expect(chosenRows(rows, "all", "recent").map((r) => r.forecast.date)[0]).toBe("2025-08-30");
    expect(chosenRows(rows, "all", "surprising").map((r) => r.chance)).toEqual([0.1, 0.3, 0.5]);
    expect(chosenRows(rows, "all", "confident").map((r) => r.forecast.date)[0]).toBe("2025-08-23");
  });
});

describe("the latest matches week by week", () => {
  it("starts a week on Monday", () => {
    expect(weekOf("2026-11-01")).toBe("2026-10-26"); // a Sunday
    expect(weekOf("2026-10-26")).toBe("2026-10-26");
    expect(weekText("2026-10-26")).toBe("26 oct. – 1 nov.");
  });

  it("groups consecutive matches of a week and counts their hits", () => {
    const rows = [row("2025-08-24", 0.5, true, 0.5), row("2025-08-23", 0.3, false, 0.4), row("2025-08-16", 0.5, true, 0.6)];
    const weeks = byWeek(rows);
    expect(weeks.map((week) => [week.monday, week.rows.length, week.hits])).toEqual([
      ["2025-08-18", 2, 1],
      ["2025-08-11", 1, 1],
    ]);
  });
});
