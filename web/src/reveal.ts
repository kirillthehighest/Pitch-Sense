// The change of league, as in the earlier PySide6 window (Phase 21, the team's request): the
// page in the new league's colours is uncovered by a circle growing from the top-left corner in
// 0.8 s, its edge two travelling waves that calm as it grows (Material You-like). It uses the browser's view
// transitions; where they are missing, or the user asked for less motion, the change is
// immediate.

const DURATION = 800; // ms
const FRAMES = 32;
const POINTS = 120; // around the edge
const WAVES = 9; // crests around the whole circle
const RIPPLE = 4; // a second, faster wave
const START_HEIGHT = 18; // px, the waves' height at the start...
const END_HEIGHT = 4; // ...and at the end

/** A polygon (CSS) of a circle around (cx, cy) whose edge carries two waves at ``phase``. */
export function wavyCircle(cx: number, cy: number, radius: number, height: number, phase: number): string {
  const points: string[] = [];
  for (let index = 0; index < POINTS; index += 1) {
    const angle = (2 * Math.PI * index) / POINTS;
    const edge =
      radius +
      height * (0.65 * Math.sin(WAVES * angle + phase) + 0.35 * Math.sin(WAVES * RIPPLE * 0.5 * angle - 2 * phase));
    const r = Math.max(0, edge);
    points.push(`${(cx + r * Math.cos(angle)).toFixed(1)}px ${(cy + r * Math.sin(angle)).toFixed(1)}px`);
  }
  return `polygon(${points.join(", ")})`;
}

/** The keyframes of the reveal over a window of ``width`` x ``height``. */
export function revealFrames(width: number, height: number): Keyframe[] {
  const end = Math.hypot(width, height) + START_HEIGHT * 2; // the waves too leave the window
  return Array.from({ length: FRAMES + 1 }, (_, frame) => {
    const t = frame / FRAMES;
    const eased = 1 - (1 - t) ** 3; // OutCubic, as in Phase 21
    const waves = START_HEIGHT + (END_HEIGHT - START_HEIGHT) * t;
    return { clipPath: wavyCircle(0, 0, eased * end, frame === 0 ? 0 : waves, 4 * Math.PI * t) };
  });
}

type ViewTransitionDocument = Document & {
  startViewTransition?: (update: () => void) => { ready: Promise<void> };
};

/** Run ``change`` (which must update the page at once) under the wavy reveal. */
export function reveal(change: () => void): void {
  const page = document as ViewTransitionDocument;
  const still = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  if (!page.startViewTransition || still) {
    change();
    return;
  }
  const transition = page.startViewTransition(change);
  transition.ready
    .then(() => {
      document.documentElement.animate(revealFrames(window.innerWidth, window.innerHeight), {
        duration: DURATION,
        easing: "linear", // the easing is in the frames
        pseudoElement: "::view-transition-new(root)",
      });
    })
    .catch(() => undefined); // a transition skipped by the browser: the change happened anyway
}
