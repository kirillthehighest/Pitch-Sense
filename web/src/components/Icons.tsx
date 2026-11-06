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

const CHEVRONS = { left: "M15 5l-7 7 7 7", right: "M9 5l7 7-7 7", up: "M5 15l7-7 7 7", down: "M5 9l7 7 7-7" };

export function ChevronIcon({ direction }: { direction: "left" | "right" | "up" | "down" }) {
  return (
    <svg {...base} width={18} height={18}>
      <path d={CHEVRONS[direction]} />
    </svg>
  );
}

/** The marks of a prediction that came true or did not: drawn, so they read at any size. */
export function CheckIcon({ size = 12 }: { size?: number }) {
  return (
    <svg {...base} width={size} height={size} strokeWidth={3.2}>
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </svg>
  );
}

export function CrossIcon({ size = 12 }: { size?: number }) {
  return (
    <svg {...base} width={size} height={size} strokeWidth={3.2}>
      <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />
    </svg>
  );
}

export function SearchIcon() {
  return (
    <svg {...base}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16 16l4.5 4.5" />
    </svg>
  );
}

/** "Simulează un meci": two teams' paths meeting at one point. */
export function SimulateIcon() {
  return (
    <svg {...base}>
      <circle cx="6" cy="6.5" r="2.5" />
      <circle cx="18" cy="6.5" r="2.5" />
      <path d="M6 9v1.5a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4V9M12 14.5V20" />
    </svg>
  );
}

export function KeyboardIcon() {
  return (
    <svg {...base}>
      <rect x="3" y="6" width="18" height="12" rx="2.5" />
      <path d="M7 10h.01M11 10h.01M15 10h.01M7 14h10" />
    </svg>
  );
}

export function StarIcon({ filled = false }: { filled?: boolean }) {
  return (
    <svg {...base} width={16} height={16} fill={filled ? "currentColor" : "none"}>
      <path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" />
    </svg>
  );
}
