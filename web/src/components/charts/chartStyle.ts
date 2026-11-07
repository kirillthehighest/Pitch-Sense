// The look the charts share (docs/brand.md, section 6): recessive grid and axes on the card,
// text in the text colours, never in a series' colour.
export const GRID = "#24242A";
export const AXIS = "#9C9CA6";
export const TEXT = "#F5F5F7";
export const SURFACE = "#16161A";
export const ELO_COLOUR = "#4D8DFF";
export const CONTEXT_COLOUR = "#6E6E7A"; // the lines around the chosen one: neutral, recessive
export const BASELINE_COLOUR = "#8E929C";
// The K-Means groups (0 = strongest), told apart by hue as well as lightness (Phase 26: the blue
// ramp was too close to read at a dot's size): light gold, sky, violet, slate
export const GROUP_COLOURS: Record<number, string> = { 0: "#FFD166", 1: "#5CC8FF", 2: "#B794F6", 3: "#8A94A6" };

export const tick = { fill: AXIS, fontSize: 12 };
export const axisLine = { stroke: GRID };
