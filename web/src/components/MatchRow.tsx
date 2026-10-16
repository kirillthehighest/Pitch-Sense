// One match of a list, as in the score apps the team chose: the kickoff (or "Final"), the home
// team on the left and the away team on the right of the score (or "vs"), and the chosen model's
// three probabilities; the most likely is filled with the league's accent and, once the match is
// played, carries a tick (it happened) or a cross (it did not), and the chip of the result that
// happened is ringed.
import type { ReactNode } from "react";
import { percent } from "../format";
import type { Forecast, Outcome, Prediction } from "../types";
import { Crest } from "./Crest";

const OUTCOMES: Outcome[] = ["H", "D", "A"];

export function chance(prediction: Prediction, outcome: Outcome): number {
  return outcome === "H" ? prediction.home : outcome === "D" ? prediction.draw : prediction.away;
}

/** What the left column says: the day (in a team's list), "Final", "Amânat" or the kickoff. */
export function statusText(forecast: Forecast, showDate = false): string {
  if (showDate) return `${forecast.date.slice(8, 10)}.${forecast.date.slice(5, 7)}`;
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

export function Chips({ prediction, result = null }: { prediction: Prediction | undefined; result?: Outcome | null }) {
  if (!prediction) return <span className="chips caption">fără predicție</span>;
  return (
    <span className="chips">
      {OUTCOMES.map((outcome) => {
        const chosen = prediction.most_likely === outcome;
        return (
          <span
            key={outcome}
            className={`chip${chosen ? " chosen" : ""}${result === outcome ? " actual" : ""}`}
            title={result === outcome ? "Rezultatul meciului" : undefined}
          >
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
  stacked?: boolean; // a narrow column: home over away, each with its goals, the chips below
  showDate?: boolean; // a team's matches: the day instead of the kickoff
  extra?: ReactNode; // a last column (the review's verdict)
  onOpen: (forecast: Forecast) => void;
}

function StackedTeam({ team, goals, favourite, won }: { team: string; goals: number | null; favourite: boolean; won: boolean }) {
  return (
    <span className={`team${favourite ? " favourite" : ""}${won ? " won" : ""}`}>
      <Crest team={team} size={22} ring={favourite} />
      <span className="name">{team}</span>
      {goals !== null && <b className="goals">{goals}</b>}
    </span>
  );
}

export function MatchRow({ forecast, model, favourite, stacked = false, showDate = false, extra, onOpen }: Props) {
  const played = forecast.result !== null;
  const prediction = forecast.predictions.find((p) => p.model === model);
  const upcoming = !played && !forecast.postponed;
  if (stacked) {
    return (
      <button className="match-row stacked" onClick={() => onOpen(forecast)}>
        <span className={`status${upcoming ? " upcoming" : ""}`}>{statusText(forecast, showDate)}</span>
        <span className="stack">
          <StackedTeam team={forecast.home_team} goals={forecast.home_goals} favourite={favourite === forecast.home_team} won={forecast.result === "H"} />
          <StackedTeam team={forecast.away_team} goals={forecast.away_goals} favourite={favourite === forecast.away_team} won={forecast.result === "A"} />
        </span>
        <Chips prediction={prediction} result={forecast.result} />
      </button>
    );
  }
  return (
    <button className={`match-row${extra ? " with-extra" : ""}`} onClick={() => onOpen(forecast)}>
      <span className={`status${upcoming ? " upcoming" : ""}`}>{statusText(forecast, showDate)}</span>
      <span className="teams">
        <Team team={forecast.home_team} side="home" favourite={favourite === forecast.home_team} won={forecast.result === "H"} />
        <span className="score">
          {played ? `${forecast.home_goals} : ${forecast.away_goals}` : <span className="vs">vs</span>}
        </span>
        <Team team={forecast.away_team} side="away" favourite={favourite === forecast.away_team} won={forecast.result === "A"} />
      </span>
      <Chips prediction={prediction} result={forecast.result} />
      {extra}
    </button>
  );
}
