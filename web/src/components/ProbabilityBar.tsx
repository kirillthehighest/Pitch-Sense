// One model's three probabilities as a bar of three segments, home win, draw and away win in that
// order: the side the model backs in the league's accent, the side it expects to lose light grey,
// the draw dark grey (the team's choice, 0.9.2). A segment too narrow for its number shows it on hover.
import { percent } from "../format";
import type { Outcome, Prediction } from "../types";
import { chance } from "./MatchRow";

const SEGMENTS: [Outcome, string][] = [
  ["H", "Gazde"],
  ["D", "Egal"],
  ["A", "Oaspeți"],
];

/** What a segment is to the model: its pick, the side it expects to lose, or the draw. */
export function segmentRole(prediction: Prediction, outcome: Outcome): "pick" | "other" | "draw" {
  if (prediction.most_likely === outcome) return "pick";
  return outcome === "D" ? "draw" : "other";
}
const NARROWEST_LABEL = 0.06; // below this a segment is too narrow for its number

export function ProbabilityBar({ prediction }: { prediction: Prediction }) {
  return (
    <div className="probability-bar" role="img" aria-label={SEGMENTS.map(([o, label]) => `${label} ${percent(chance(prediction, o), 0)}`).join(", ")}>
      {SEGMENTS.map(([outcome, label]) => {
        const value = chance(prediction, outcome);
        return (
          <span
            key={outcome}
            className={`segment ${segmentRole(prediction, outcome)}`}
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
