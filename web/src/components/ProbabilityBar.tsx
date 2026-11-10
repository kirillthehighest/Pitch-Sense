// One model's three probabilities as a bar of three segments, as in Phase 21: the
// home win in the league's accent, the draw dark grey, the away win light grey; the most likely
// outcome's number is bold. A segment too narrow for its number shows it on hover.
import { percent } from "../format";
import type { Outcome, Prediction } from "../types";
import { chance } from "./MatchRow";

const SEGMENTS: [Outcome, string, string][] = [
  ["H", "home", "Gazde"],
  ["D", "draw", "Egal"],
  ["A", "away", "Oaspeți"],
];
const NARROWEST_LABEL = 0.06; // below this a segment is too narrow for its number

export function ProbabilityBar({ prediction }: { prediction: Prediction }) {
  return (
    <div className="probability-bar" role="img" aria-label={SEGMENTS.map(([o, , label]) => `${label} ${percent(chance(prediction, o), 0)}`).join(", ")}>
      {SEGMENTS.map(([outcome, name, label]) => {
        const value = chance(prediction, outcome);
        return (
          <span
            key={outcome}
            className={`segment ${name}${prediction.most_likely === outcome ? " likely" : ""}`}
            style={{ flexGrow: value }}
            title={`${label}: ${percent(value, 0)}`}
          >
            {value >= NARROWEST_LABEL && percent(value, 0)}
          </span>
        );
      })}
    </div>
  );
}
