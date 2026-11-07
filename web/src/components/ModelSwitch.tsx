// The model switch (Phase 26): the three models side by side, each with its share of hits in the
// league's season so far, so the proof sits where the model is chosen, and under them why the
// default is the default (the long run, which a short season can contradict). The chosen model's
// chances fill the lists; M moves to the next model.
import { useEffect, useState } from "react";
import { api } from "../api";
import { integer, percent, seasonText } from "../format";
import { MODEL_COLOURS } from "../theme";
import type { League, ModelRecord, TrackRecord } from "../types";
import { MODEL_LABELS, MODELS } from "../types";

interface Props {
  league: League;
  model: string;
  ready: string;
  onModel: (model: string) => void;
  showRecord?: boolean; // false where the screen shows the record itself (Predicții)
}

/** Why logistic regression is chosen by default: the lowest Brier score over all the evaluation
 * seasons of the five leagues together (docs/leagues.md). */
export const DEFAULT_REASON = "implicit: regresia logistică, cel mai mic scor Brier pe 16 sezoane";

/** "55,0%" of a model's hits, or nothing before its first reviewed match. */
export function recordText(record: ModelRecord | undefined): string {
  return record && record.matches > 0 ? percent(record.hits / record.matches) : "";
}

export function ModelSwitch({ league, model, ready, onModel, showRecord = true }: Props) {
  const [record, setRecord] = useState<TrackRecord | null>(null);
  useEffect(() => {
    let live = true;
    if (!league.prepared || !showRecord) return;
    api
      .trackRecord(league.code)
      .then((found) => live && setRecord(found))
      .catch(() => live && setRecord(null)); // the switch works without the record
    return () => {
      live = false;
    };
  }, [league.code, league.prepared, ready, showRecord]);

  const shown = record?.competition === league.code ? record : null;
  const of = (name: string) => shown?.models.find((item) => item.model === name);
  // a radio group moves with the arrows, as the platform's own
  const step = (direction: number) => {
    const index = MODELS.indexOf(model as (typeof MODELS)[number]);
    onModel(MODELS[(index + direction + MODELS.length) % MODELS.length]);
  };
  return (
    <div className="model-choice">
      <div
        className="model-switch"
        role="radiogroup"
        aria-label="Modelul"
        aria-keyshortcuts="M"
        title="Implicit: regresia logistică, cel mai mic scor Brier pe toate ligile la un loc, în 16 sezoane"
        onKeyDown={(event) => {
          if (event.key === "ArrowRight" || event.key === "ArrowDown") step(1);
          else if (event.key === "ArrowLeft" || event.key === "ArrowUp") step(-1);
          else return;
          event.preventDefault();
          event.stopPropagation();
        }}
      >
        {MODELS.map((name) => {
          const found = of(name);
          const text = recordText(found);
          return (
            <button
              key={name}
              role="radio"
              aria-checked={model === name}
              tabIndex={model === name ? 0 : -1}
              className={model === name ? "chosen" : undefined}
              onClick={() => onModel(name)}
              title={
                found && found.matches > 0
                  ? `${MODEL_LABELS[name]}: ${integer(found.hits)} din ${integer(found.matches)} meciuri nimerite în ${league.name} ${seasonText(shown?.season ?? "")}`
                  : MODEL_LABELS[name]
              }
            >
              <i style={{ background: MODEL_COLOURS[name] }} />
              <span>{MODEL_LABELS[name]}</span>
              {text && <b>{text}</b>}
            </button>
          );
        })}
      </div>
      <span className="model-scope">
        {shown && shown.models.some((item) => item.matches > 0) && (
          <>
            nimerite în {league.name} {seasonText(shown.season)}
            {" · "}
          </>
        )}
        {DEFAULT_REASON}
      </span>
    </div>
  );
}
