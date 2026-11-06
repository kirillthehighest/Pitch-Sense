// The models' record of the season on Meciuri (Phase 25): for each model, how often its most
// likely result happened this season, and in its latest week of matches; the bar is the share,
// in the model's identity colour. A click opens Predicții.
import { useEffect, useState } from "react";
import { api } from "../api";
import { dateText, integer, parseDay, percent, seasonText } from "../format";
import { MODEL_COLOURS } from "../theme";
import type { League, TrackRecord as Record } from "../types";
import { SkeletonLine } from "./Skeleton";

interface Props {
  league: League;
  ready: string;
  onOpen: () => void;
}

export function TrackRecord({ league, ready, onOpen }: Props) {
  const [record, setRecord] = useState<Record | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    setFailed(false);
    if (!league.prepared) return;
    api
      .trackRecord(league.code)
      .then((found) => live && setRecord(found))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [league.code, league.prepared, ready]);

  if (failed) return null; // the strip is a summary: the screen works without it
  const shown = record?.competition === league.code ? record : null;
  const best = shown ? Math.max(...shown.models.map((model) => (model.matches ? model.hits / model.matches : 0))) : 0;
  return (
    <section className="track-record" aria-label="Bilanțul modelelor">
      <header>
        <h2>
          {shown ? `Cât au nimerit modelele în ${seasonText(shown.season)}` : "Cât au nimerit modelele"}
        </h2>
        <button className="link" onClick={onOpen}>
          Toate predicțiile ›
        </button>
      </header>
      <div className="track-models">
        {shown
          ? shown.models.map((model) => {
              const share = model.matches ? model.hits / model.matches : 0;
              return (
                <button key={model.model} className="track-model" onClick={onOpen}>
                  <span className="track-name">
                    <i style={{ background: MODEL_COLOURS[model.model] }} />
                    {model.label}
                    {model.matches > 0 && share === best && <span className="track-lead">în frunte</span>}
                  </span>
                  <strong>{model.matches ? percent(share, 0) : "–"}</strong>
                  <span className="track-bar" aria-hidden="true">
                    <span style={{ width: `${100 * share}%`, background: MODEL_COLOURS[model.model] }} />
                  </span>
                  <span className="caption">
                    {integer(model.hits)} din {integer(model.matches)} meciuri
                    {model.recent_matches > 0 && (
                      <>
                        <br />
                        Ultima săptămână: {model.recent_hits} din {model.recent_matches}
                      </>
                    )}
                  </span>
                </button>
              );
            })
          : [0, 1, 2].map((index) => (
              <div key={index} className="track-model">
                <SkeletonLine width="60%" />
                <SkeletonLine width={72} height={34} />
                <SkeletonLine width="80%" />
              </div>
            ))}
      </div>
      {shown?.last_day && (
        <p className="caption track-note">
          Un meci e nimerit când rezultatul socotit cel mai probabil s-a întâmplat. Ultimul meci: {dateText(parseDay(shown.last_day))}.
        </p>
      )}
    </section>
  );
}
