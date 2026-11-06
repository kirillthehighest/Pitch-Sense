import { describe, expect, it } from "vitest";
import { chanceText, placeOpacity, zoneOf } from "./Standings";

describe("the table's zones and the projection", () => {
  it("puts the first four and the last three in their zones", () => {
    expect([1, 4, 5, 17, 18, 20].map((place) => zoneOf(place, 20))).toEqual(["top", "top", "", "", "bottom", "bottom"]);
    expect(zoneOf(16, 18)).toBe("bottom"); // the play-off place of an 18-club league
  });

  it("writes chances without false precision at the ends", () => {
    expect([0, 0.004, 0.42, 0.996, 1].map(chanceText)).toEqual(["–", "<1%", "42%", ">99%", "100%"]);
  });

  it("lights a place by its chance, a place never reached almost dark", () => {
    expect(placeOpacity(0)).toBeLessThan(placeOpacity(0.01));
    expect(placeOpacity(1)).toBeCloseTo(1);
    expect(placeOpacity(0.25)).toBeCloseTo(0.56);
  });
});
