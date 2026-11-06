// The small diagrams of "Cum funcționează" (Phase 25): how each algorithm thinks, drawn as a
// sketch. They explain the idea and carry no results: the numbers on them are made-up examples,
// and each says so. Colours are the models' identity colours (docs/brand.md, section 6).
import { MODEL_COLOURS } from "../theme";

const INK = "#F5F5F7";
const MUTED = "#9C9CA6";
const LINE = "#2A2A30";
const RAISED = "#1E1E23";
const label = { fill: MUTED, fontSize: 11, fontFamily: "inherit", fontWeight: 600 } as const;

/** Elo: the winner takes points from the loser, more after beating a stronger side. */
export function EloDiagram() {
  const colour = MODEL_COLOURS.Elo;
  return (
    <svg viewBox="0 0 320 120" role="img" aria-label="Schemă: după un meci, câștigătoarea ia puncte de rating de la învinsă">
      {[
        { x: 40, before: 62, after: 74, name: "Câștigă", delta: "+12" },
        { x: 190, before: 78, after: 66, name: "Pierde", delta: "−12" },
      ].map((team) => (
        <g key={team.name}>
          <rect x={team.x} y={100 - team.before} width="34" height={team.before} rx="5" fill={RAISED} />
          <rect x={team.x + 44} y={100 - team.after} width="34" height={team.after} rx="5" fill={colour} opacity={team.after > team.before ? 1 : 0.55} />
          <text x={team.x + 17} y="114" textAnchor="middle" {...label}>
            înainte
          </text>
          <text x={team.x + 61} y="114" textAnchor="middle" {...label}>
            după
          </text>
          <text x={team.x + 39} y="16" textAnchor="middle" fill={INK} fontSize="12" fontWeight="700">
            {team.name} {team.delta}
          </text>
        </g>
      ))}
      <path d="M182 56 H132" stroke={MUTED} strokeWidth="1.6" markerEnd="url(#elo-arrow)" />
      <text x="157" y="48" textAnchor="middle" {...label}>
        puncte
      </text>
      <defs>
        <marker id="elo-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0 0 L10 5 L0 10z" fill={MUTED} />
        </marker>
      </defs>
    </svg>
  );
}

/** Poisson: two expected goal counts become a grid of score chances. */
export function PoissonDiagram() {
  const colour = MODEL_COLOURS.Poisson;
  const home = [0.22, 0.33, 0.25, 0.12];
  const away = [0.35, 0.37, 0.19, 0.07];
  const largest = Math.max(...home.flatMap((h) => away.map((a) => h * a)));
  return (
    <svg viewBox="0 0 320 120" role="img" aria-label="Schemă: din golurile așteptate ale fiecărei echipe rezultă șansa fiecărui scor">
      <text x="0" y="14" {...label}>
        goluri gazde
      </text>
      {home.map((value, goals) => (
        <g key={`h${goals}`}>
          <rect x={4} y={26 + goals * 22} width={value * 180} height="16" rx="4" fill={colour} opacity="0.75" />
          <text x={value * 180 + 10} y={38 + goals * 22} {...label}>
            {goals}
          </text>
        </g>
      ))}
      <text x="150" y="68" textAnchor="middle" fill={MUTED} fontSize="18">
        →
      </text>
      <text x="190" y="14" {...label}>
        scoruri
      </text>
      {home.map((h, i) =>
        away.map((a, j) => (
          <rect
            key={`${i}-${j}`}
            x={190 + j * 30}
            y={24 + i * 23}
            width="26"
            height="19"
            rx="4"
            fill={colour}
            opacity={0.08 + 0.92 * ((h * a) / largest)}
          />
        )),
      )}
    </svg>
  );
}

/** Logistic regression: weighted differences add up, softmax turns them into three chances. */
export function LogisticDiagram() {
  const colour = MODEL_COLOURS["Logistic regression"];
  const inputs = ["rating Elo", "puncte", "goluri", "formă", "șuturi"];
  const outputs: [string, number][] = [
    ["gazde", 0.48],
    ["egal", 0.27],
    ["oaspeți", 0.25],
  ];
  return (
    <svg viewBox="0 0 320 120" role="img" aria-label="Schemă: diferențele dintre echipe, cântărite, dau trei șanse care însumează 100%">
      {inputs.map((name, index) => (
        <g key={name}>
          <text x="0" y={18 + index * 22} {...label}>
            {name}
          </text>
          <path d={`M72 ${14 + index * 22} C 120 ${14 + index * 22}, 120 60, 160 60`} stroke={colour} strokeOpacity={0.35 + index * 0.12} strokeWidth="1.6" fill="none" />
        </g>
      ))}
      <circle cx="166" cy="60" r="12" fill={RAISED} stroke={colour} strokeWidth="2" />
      <text x="166" y="64" textAnchor="middle" fill={INK} fontSize="12" fontWeight="700">
        Σ
      </text>
      {outputs.map(([name, value], index) => (
        <g key={name}>
          <path d={`M178 60 C 196 60, 196 ${30 + index * 30}, 212 ${30 + index * 30}`} stroke={LINE} strokeWidth="1.6" fill="none" />
          <rect x="216" y={22 + index * 30} width={value * 150} height="16" rx="4" fill={colour} opacity={index === 0 ? 1 : 0.5} />
          <text x={220 + value * 150} y={34 + index * 30} {...label}>
            {name}
          </text>
        </g>
      ))}
    </svg>
  );
}

/** K-Means: clubs as points, four centres, each club joining its nearest. */
export function KMeansDiagram() {
  const groups = ["#D2E2FF", "#8EB4FF", "#5585F0", "#3A63C9"];
  const centres: [number, number][] = [
    [262, 26],
    [196, 52],
    [118, 74],
    [52, 96],
  ];
  const offsets: [number, number][] = [
    [-14, -6],
    [12, 8],
    [-6, 12],
    [16, -8],
    [2, -14],
  ];
  return (
    <svg viewBox="0 0 320 120" role="img" aria-label="Schemă: echipele asemănătoare ajung în același grup, în jurul unui centru">
      <path d="M20 8 V108 H310" stroke={LINE} strokeWidth="1.4" fill="none" />
      <text x="24" y="16" {...label}>
        goluri marcate
      </text>
      <text x="306" y="102" textAnchor="end" {...label}>
        goluri primite ←
      </text>
      {centres.map(([x, y], group) => (
        <g key={group}>
          {offsets.map(([dx, dy], index) => (
            <circle key={index} cx={x + dx} cy={y + dy} r="4" fill={groups[group]} opacity="0.85" />
          ))}
          <path d={`M${x - 6} ${y - 6} l12 12 M${x + 6} ${y - 6} l-12 12`} stroke={INK} strokeWidth="2.2" strokeLinecap="round" />
        </g>
      ))}
    </svg>
  );
}

/** The chronological check: the seasons that start the models, those that tune them, the report. */
export function TimelineDiagram() {
  const parts: [string, string, number, string][] = [
    ["2006/07", "pornește modelele", 1, "#5E5E68"],
    ["2007/08–2009/10", "alegerea setărilor", 3, "#9C9CA6"],
    ["2010/11–2025/26", "rezultatele raportate", 16, MODEL_COLOURS["Logistic regression"]],
  ];
  const total = parts.reduce((sum, part) => sum + part[2], 0);
  const widths = parts.map((part) => (part[2] / total) * 316);
  return (
    <svg viewBox="0 0 320 104" role="img" aria-label="Schemă: 2006/07 pornește modelele, 2007/08–2009/10 aleg setările, 2010/11–2025/26 dau rezultatele">
      {parts.map(([seasons, name, , colour], index) => {
        const start = widths.slice(0, index).reduce((sum, width) => sum + width + 2, 0);
        return (
          <g key={name}>
            <rect x={start} y="4" width={widths[index]} height="20" rx="5" fill={colour} />
            <rect x="0" y={40 + index * 22} width="12" height="12" rx="3" fill={colour} />
            <text x="20" y={50 + index * 22} fill={INK} fontSize="11" fontWeight="700">
              {seasons}
            </text>
            <text x="150" y={50 + index * 22} {...label}>
              {name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
