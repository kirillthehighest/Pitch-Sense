// One match of a list, as in the score apps the team chose: the kickoff (or "Final"), the home
// team on the left and the away team on the right of the score (or "vs"), and the chosen model's
// three probabilities; the most likely is filled with the league's accent and, once the match is
// played, carries a tick (it happened) or a cross (it did not).
import { percent } from "../format";
import type { Forecast, Outcome, Prediction } from "../types";
import { Crest } from "./Crest";

const OUTCOMES: Outcome[] = ["H", "D", "A"];

export function chance(prediction: Prediction, outcome: Outcome): number {
  return outcome === "H" ? prediction.home : outcome === "D" ? prediction.draw : prediction.away;
}

export function statusText(forecast: Forecast): string {
  if (forecast.result !== null) return "Final";
  if (forecast.postponed) return "Amânat";
  return forecast.kickoff ?? "–";
}

function Team({ team, favourite, won, side }: { team: string; favourite: boolean; won: boolean; side: "home" | "away" }) {
  return (
    <span className={`team ${side}${favourite ? " favourite" : ""}${won ? " won" : ""}`}>
      <Crest team={team} size={26} ring={favourite} />
      <span className="name">{team}</span>
    </span>
  );
}

export function Chips({ prediction }: { prediction: Prediction | undefined }) {
  if (!prediction) return <span className="chips caption">fără predicție</span>;
  return (
    <span className="chips">
      {OUTCOMES.map((outcome) => {
        const chosen = prediction.most_likely === outcome;
        return (
          <span key={outcome} className={`chip${chosen ? " chosen" : ""}`}>
            {percent(chance(prediction, outcome), 0)}
            {chosen && prediction.hit !== null && (
              <span className={`mark ${prediction.hit ? "hit" : "miss"}`} aria-label={prediction.hit ? "nimerit" : "ratat"}>
                {prediction.hit ? "✓" : "✕"}
              </span>
            )}
          </span>
        );
      })}
    </span>
  );
}

interface Props {
  forecast: Forecast;
  model: string;
  favourite?: string | null;
  onOpen: (forecast: Forecast) => void;
}

export function MatchRow({ forecast, model, favourite, onOpen }: Props) {
  const played = forecast.result !== null;
  const prediction = forecast.predictions.find((p) => p.model === model);
  const upcoming = !played && !forecast.postponed;
  return (
    <button className="match-row" onClick={() => onOpen(forecast)} title="Deschide meciul">
      <span className={`status${upcoming ? " upcoming" : ""}`}>{statusText(forecast)}</span>
      <span className="teams">
        <Team team={forecast.home_team} side="home" favourite={favourite === forecast.home_team} won={forecast.result === "H"} />
        <span className="score">
          {played ? `${forecast.home_goals} : ${forecast.away_goals}` : <span className="vs">vs</span>}
        </span>
        <Team team={forecast.away_team} side="away" favourite={favourite === forecast.away_team} won={forecast.result === "A"} />
      </span>
      <Chips prediction={prediction} />
    </button>
  );
}
