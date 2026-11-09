import { describe, expect, it } from "vitest";
import { isStale } from "../App";
import { isPageKey } from "../components/Shortcuts";
import { nextModel } from "./Matches";
import { previousSeason } from "./Team";

describe("small rules of the screens", () => {
  it("cycles the models with M", () => {
    expect(nextModel("Logistic regression")).toBe("Elo");
    expect(nextModel("Poisson")).toBe("Logistic regression");
  });

  it("finds the season before another", () => {
    expect(previousSeason(["2024-25", "2025-26", "2026-27"], "2026-27")).toBe("2025-26");
    expect(previousSeason(["2024-25"], "2024-25")).toBeNull();
  });

  it("calls data stale after two days", () => {
    const now = new Date("2026-11-06T12:00:00Z").getTime();
    expect(isStale("2026-11-05T12:00:00Z", now)).toBe(false);
    expect(isStale("2026-11-03T12:00:00Z", now)).toBe(true);
    expect(isStale(null, now)).toBe(false);
  });

  it("leaves keys typed into a field or with a modifier to the page", () => {
    const input = document.createElement("input");
    document.body.append(input);
    const typed = new KeyboardEvent("keydown", { key: "m" });
    Object.defineProperty(typed, "target", { value: input });
    expect(isPageKey(typed)).toBe(false);
    expect(isPageKey(new KeyboardEvent("keydown", { key: "m", metaKey: true }))).toBe(false);
    expect(isPageKey(new KeyboardEvent("keydown", { key: "m" }))).toBe(true);
    input.remove();
  });
});
