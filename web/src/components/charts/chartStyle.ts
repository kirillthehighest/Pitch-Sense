// The look the charts share (docs/brand.md, section 6): recessive grid and axes on the card,
// text in the text colours, never in a series' colour.
export const GRID = "#24242A";
export const AXIS = "#9C9CA6";
export const TEXT = "#F5F5F7";
export const SURFACE = "#16161A";
export const CONTEXT_COLOUR = "#6E6E7A"; // the lines around the chosen one: neutral, recessive
export const BASELINE_COLOUR = "#8E929C";
// The K-Means groups are ordered (0 = strongest): one hue, brightest for the strongest
// one blue ramp, brightest for the strongest group, its steps far enough apart to tell on the dark card
export const GROUP_COLOURS: Record<number, string> = { 0: "#E6EEFF", 1: "#A3C0FF", 2: "#5F8DF5", 3: "#2E5BC8" };
// and a shape each, so the groups part even without colour
export const GROUP_SHAPES = { 0: "circle", 1: "square", 2: "triangle", 3: "diamond" } as const;

export const tick = { fill: AXIS, fontSize: 12 };
export const axisLine = { stroke: GRID };
