// The colours of PitchSense. Since Phase 26 one constant palette for every league (the team's
// choice of the category standard): the accent marks the pick and the selection, the leagues are
// told apart by their flag, name and image, never by repainting the interface. The values mirror
// the CSS variables of styles.css for the places that paint from code (charts, the score grid).

export const ACCENT = "#FF7A3D";
/** The deep colour the league images run into at their edge: neutral, as every surface. */
export const IMAGE_FILL = "#141418";

/** The models' identity colours (docs/brand.md, section 6): fixed, never reassigned. */
export const MODEL_COLOURS: Record<string, string> = {
  Elo: "#4D8DFF",
  Poisson: "#EF5A6F",
  "Logistic regression": "#00A3A8",
};
