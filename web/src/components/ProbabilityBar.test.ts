import { describe, expect, it } from "vitest";
import type { Prediction } from "../types";
import { segmentRole } from "./ProbabilityBar";

const prediction: Prediction = {
  model: "Elo",
  label: "Elo",
  home: 0.23,
  draw: 0.26,
  away: 0.51,
  most_likely: "A",
  hit: null,
  expected_goals: null,
};

describe("a model's bar", () => {
  it("colours the side it backs, the side it expects to lose and the draw", () => {
    expect(segmentRole(prediction, "A")).toBe("pick");
    expect(segmentRole(prediction, "H")).toBe("other");
    expect(segmentRole(prediction, "D")).toBe("draw");
  });

  it("backs the draw when the draw is its pick, both sides then expected to lose", () => {
    const draw = { ...prediction, most_likely: "D" as const };
    expect(segmentRole(draw, "D")).toBe("pick");
    expect(segmentRole(draw, "H")).toBe("other");
    expect(segmentRole(draw, "A")).toBe("other");
  });
});
