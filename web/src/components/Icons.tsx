// Line icons of the side bar (24-unit grid, round strokes), as in Phase 21.
import type { SVGProps } from "react";

const base: SVGProps<SVGSVGElement> = {
  width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: 1.9, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true,
};

export function MatchesIcon() {
  return (
    <svg {...base}>
      <rect x="4" y="5" width="16" height="15" rx="2.5" />
      <path d="M4 10h16M8 3v4M16 3v4" />
      <path d="M8.5 14.5h.01M12 14.5h.01" />
    </svg>
  );
}

export function StandingsIcon() {
  return (
    <svg {...base}>
      <rect x="9" y="6" width="6" height="14" rx="1" />
      <rect x="3" y="11" width="6" height="9" rx="1" />
      <rect x="15" y="14" width="6" height="6" rx="1" />
    </svg>
  );
}

export function TeamIcon() {
  return (
    <svg {...base}>
      <path d="M12 3l7.5 2.5c0 7.5-2.5 12.5-7.5 15.5C7 18 4.5 13 4.5 5.5z" />
    </svg>
  );
}

export function PredictionsIcon() {
  return (
    <svg {...base}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8 12.2l3 2.8 5.2-5.6" />
    </svg>
  );
}

export function AnalysisIcon() {
  return (
    <svg {...base}>
      <path d="M5 20h14M7 17v-4M12 17V6M17 17v-7" />
    </svg>
  );
}

export function RefreshIcon() {
  return (
    <svg {...base}>
      <path d="M19.5 9A7.5 7.5 0 1 0 19 15.5" />
      <path d="M19.5 4.5V9H15" />
    </svg>
  );
}

export function ChevronIcon({ direction }: { direction: "left" | "right" }) {
  return (
    <svg {...base} width={18} height={18}>
      <path d={direction === "left" ? "M15 5l-7 7 7 7" : "M9 5l7 7-7 7"} />
    </svg>
  );
}
