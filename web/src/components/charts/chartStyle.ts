// The look the charts share (docs/brand.md, section 6): recessive grid and axes on the card,
// text in the text colours, never in a series' colour.
export const GRID = "#24242A";
export const AXIS = "#9C9CA6";
export const TEXT = "#F5F5F7";
export const SURFACE = "#16161A";
export const ELO_COLOUR = "#4D8DFF";
export const CONTEXT_COLOUR = "#6E6E7A"; // the lines around the chosen one: neutral, recessive
export const BASELINE_COLOUR = "#8E929C";
// The K-Means groups are ordered (0 = strongest): one hue, brightest for the strongest
export const GROUP_COLOURS: Record<number, string> = { 0: "#D2E2FF", 1: "#8EB4FF", 2: "#5585F0", 3: "#3A63C9" };

export const tick = { fill: AXIS, fontSize: 12 };
export const axisLine = { stroke: GRID };
