// Colour arithmetic for what the interface paints from data: a heat map's cells mix the league's
// accent into the card by the size of their value, and their numbers take whichever ink reads
// better on the result (WCAG contrast), as tests/test_themes.py checks the window's colours.

export const LIGHT_INK = "#F5F5F7";
export const DARK_INK = "#0A0A0C";

export function channels(colour: string): [number, number, number] {
  const value = colour.replace("#", "");
  return [0, 2, 4].map((start) => parseInt(value.slice(start, start + 2), 16)) as [number, number, number];
}

function hex(values: number[]): string {
  return `#${values.map((value) => Math.round(value).toString(16).padStart(2, "0")).join("")}`;
}

/** The colour `share` of the way from `first` to `second` (blend in app/ui/themes.py). */
export function mix(first: string, second: string, share: number): string {
  const a = channels(first);
  const b = channels(second);
  return hex(a.map((value, index) => value + (b[index] - value) * share));
}

/** WCAG relative luminance. */
export function luminance(colour: string): number {
  const linear = channels(colour).map((value) => {
    const c = value / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

/** WCAG contrast ratio of two colours, from 1 to 21. */
export function contrast(first: string, second: string): number {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

/** The ink that reads better on `fill`, of a light and a dark one (by default the text and the
 * night). Pure white and black always reach 4.5:1 on some side; the text and the night, a little
 * softer, fall to 4.3:1 on mid-tones. */
export function inkOn(fill: string, light = LIGHT_INK, dark = DARK_INK): string {
  return contrast(light, fill) >= contrast(dark, fill) ? light : dark;
}

// A crest whose visible pixels are nearly all darker than this vanishes on the dark surfaces
// (Juventus, Tottenham, Derby...), so it sits on a light disc: the rule of is_dark in
// app/ui/brand.py, on the same weights of the stored channels.
const LIGHT_LUMINANCE = 0.25;
const LIGHT_SHARE = 0.1;
export const CREST_DISC = "#E9EDF5";

/** True when fewer than a tenth of the visible pixels (RGBA, 0–255) are light. */
export function isDark(pixels: Uint8ClampedArray): boolean {
  let visible = 0;
  let light = 0;
  for (let index = 0; index < pixels.length; index += 4) {
    if (pixels[index + 3] <= 127) continue;
    visible += 1;
    const value = (0.2126 * pixels[index] + 0.7152 * pixels[index + 1] + 0.0722 * pixels[index + 2]) / 255;
    if (value > LIGHT_LUMINANCE) light += 1;
  }
  return visible === 0 || light / visible < LIGHT_SHARE;
}
