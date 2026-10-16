// The colours of each league (as app/ui/themes.py, Phase 21): neutral surfaces shared by every
// league, and each league's accent, the ink on it, the accent written on the dark and its deep
// colour. Choosing a league sets them as CSS variables on the whole page.

export interface Theme {
  accent: string;
  accentInk: string;
  accentText: string;
  brand: string;
}

export const THEMES: Record<string, Theme> = {
  E0: { accent: "#00FF85", accentInk: "#0A0A0C", accentText: "#00FF85", brand: "#37003C" },
  SP1: { accent: "#FF7A3D", accentInk: "#0A0A0C", accentText: "#FF8B55", brand: "#6E140E" },
  I1: { accent: "#3DDCFF", accentInk: "#0A0A0C", accentText: "#3DDCFF", brand: "#0B2A6F" },
  D1: { accent: "#E2001A", accentInk: "#FFFFFF", accentText: "#FF5A6A", brand: "#7A0410" },
  F1: { accent: "#D4FF3D", accentInk: "#0A0A0C", accentText: "#D4FF3D", brand: "#0E1D45" },
};

export const DEFAULT_THEME = THEMES.SP1;

export function themeFor(code: string): Theme {
  return THEMES[code] ?? DEFAULT_THEME;
}

export function applyTheme(code: string, root: HTMLElement = document.documentElement): void {
  const theme = themeFor(code);
  root.style.setProperty("--accent", theme.accent);
  root.style.setProperty("--accent-ink", theme.accentInk);
  root.style.setProperty("--accent-text", theme.accentText);
  root.style.setProperty("--brand", theme.brand);
}

/** The models' identity colours (app/visualization/palette.py): fixed, never reassigned. */
export const MODEL_COLOURS: Record<string, string> = {
  Elo: "#4D8DFF",
  Poisson: "#EF5A6F",
  "Logistic regression": "#00A3A8",
};

/** A league's colours as CSS variables on one element: a match of another league in its own. */
export function themeStyle(code: string): Record<string, string> {
  const theme = themeFor(code);
  return {
    "--accent": theme.accent,
    "--accent-ink": theme.accentInk,
    "--accent-text": theme.accentText,
    "--brand": theme.brand,
  };
}
