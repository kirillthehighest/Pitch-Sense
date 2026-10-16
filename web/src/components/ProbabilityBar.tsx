// One model's three probabilities as a bar of three segments, as in the window (Phase 21): the
// home win in the league's accent, the draw dark grey, the away win light grey; the most likely
// outcome's number is bold. A segment too narrow for its number leaves it to the legend.
import { percent } from "../format";
import type { Outcome, Prediction } from "../types";
import { chance } from "./MatchRow";

const SEGMENTS: [Outcome, string][] = [
  ["H", "home"],
  ["D", "draw"],
  ["A", "away"],
];
const NARROWEST_LABEL = 0.09;

export function ProbabilityBar({ prediction }: { prediction: Prediction }) {
  return (
    <div className="probability-bar" role="img" aria-label={SEGMENTS.map(([o]) => percent(chance(prediction, o), 0)).join(", ")}>
      {SEGMENTS.map(([outcome, name]) => {
        const value = chance(prediction, outcome);
        return (
          <span
            key={outcome}
            className={`segment ${name}${prediction.most_likely === outcome ? " likely" : ""}`}
            style={{ flexGrow: value }}
          >
            {value >= NARROWEST_LABEL && percent(value, 0)}
          </span>
        );
      })}
    </div>
  );
}
