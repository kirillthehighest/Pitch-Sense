import { describe, expect, it } from "vitest";
import { contrast, inkOn, isDark, mix } from "./colour";
import { cellColours, cellText } from "./components/ScoreGrid";
import { THEMES } from "./theme";

describe("colours painted from data", () => {
  it("mixes and measures colours as app/ui/themes.py and tests/test_themes.py do", () => {
    expect(mix("#000000", "#FFFFFF", 0)).toBe("#000000");
    expect(mix("#000000", "#FFFFFF", 1)).toBe("#ffffff");
    expect(mix("#000000", "#FF8000", 0.5)).toBe("#804000");
    expect(contrast("#FFFFFF", "#000000")).toBeCloseTo(21);
    expect(inkOn("#FFFFFF")).toBe("#0A0A0C");
    expect(inkOn("#000000")).toBe("#F5F5F7");
  });

  it("finds the crests that would vanish on the dark surfaces", () => {
    const pixels = (colours: number[][]) => new Uint8ClampedArray(colours.flat());
    const black = [0, 0, 0, 255];
    const white = [255, 255, 255, 255];
    const clear = [255, 255, 255, 0];
    expect(isDark(pixels([black, black, black, black]))).toBe(true);
    expect(isDark(pixels([black, black, black, white]))).toBe(false); // a quarter is light
    expect(isDark(pixels([black, clear, clear, clear]))).toBe(true); // transparency is not light
    expect(isDark(pixels([clear]))).toBe(true);
    expect(isDark(pixels([...Array(10).fill(black), white]))).toBe(true); // under a tenth
  });

  it("writes each score's chance in the grid", () => {
    expect(cellText(0.1234)).toBe("12%");
    expect(cellText(0.0871)).toBe("8,7%");
    expect(cellText(0.0004)).toBe("<0,1%");
  });

  it.each(Object.entries(THEMES))("keeps every number of the score grid readable in %s", (_, theme) => {
    for (let step = 0; step <= 100; step += 1) {
      const [fill, ink] = cellColours(step / 100, 1, theme.accent);
      expect(contrast(ink, fill)).toBeGreaterThanOrEqual(4.5);
    }
  });
});
