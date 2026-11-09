// One match of a list, as in the score apps the team chose: the kickoff (or "Final"), the home
// team on the left and the away team on the right of the score, and the chosen model's three
// probabilities; the most likely is filled with the match's league accent and, once the match is
// played, carries a drawn mark: a light disc with a tick (it happened) or a dark one with a cross
// (it did not), so the marks never borrow a league's green or red. The chip of the result that
// happened is ringed. A match whose day is past but has no result yet says so (Phase 25).
// Between the teams of a coming match, the Poisson model's most likely score, outlined (Phase 27).
import type { ReactNode } from "react";
import { isoDay, percent, teamName } from "../format";
import type { Forecast, Outcome, Prediction } from "../types";
import { Crest } from "./Crest";
import { CheckIcon, CrossIcon } from "./Icons";

const OUTCOMES: Outcome[] = ["H", "D", "A"];
const OUTCOME_NAMES: Record<Outcome, string> = { H: "Gazde", D: "Egal", A: "Oaspeți" };

export function chance(prediction: Prediction, outcome: Outcome): number {
  return outcome === "H" ? prediction.home : outcome === "D" ? prediction.draw : prediction.away;
}

/** A match of the calendar whose day has passed without a result reaching the app. */
export function isPending(forecast: Forecast, today: string = isoDay(new Date())): boolean {
  return forecast.result === null && !forecast.hypothetical && !forecast.postponed && forecast.date < today;
}

/** What the left column says: the day (in a team's list), "Final", "Amânat", a past match still
 * without its result, or the kickoff. */
export function statusText(forecast: Forecast, showDate = false, today?: string): string {
  if (showDate) return `${forecast.date.slice(8, 10)}.${forecast.date.slice(5, 7)}`;
  if (forecast.result !== null) return "Final";
  if (forecast.postponed) return "Amânat";
  if (isPending(forecast, today)) return "Fără rezultat";
  return forecast.kickoff ?? "–";
}

/** What a screen reader says for one chip: "Gazde 45%, cel mai probabil, nimerit". */
export function chipLabel(prediction: Prediction, outcome: Outcome, result: Outcome | null): string {
  const parts = [`${OUTCOME_NAMES[outcome]} ${percent(chance(prediction, outcome), 0)}`];
  if (prediction.most_likely === outcome) {
    parts.push("cel mai probabil");
    if (prediction.hit !== null) parts.push(prediction.hit ? "nimerit" : "ratat");
  }
  if (result === outcome) parts.push("rezultatul meciului");
  return parts.join(", ");
}

export function HitMark({ hit }: { hit: boolean }) {
  return (
    <span className={`mark ${hit ? "hit" : "miss"}`} aria-hidden="true">
      {hit ? <CheckIcon size={11} /> : <CrossIcon size={10} />}
    </span>
  );
}

function Team({ team, favourite, won, side }: { team: string; favourite: boolean; won: boolean; side: "home" | "away" }) {
  return (
    <span className={`team ${side}${favourite ? " favourite" : ""}${won ? " won" : ""}`}>
      <Crest team={team} size={26} ring={favourite} />
      <span className="name">{teamName(team)}</span>
    </span>
  );
}

export function Chips({ prediction, result = null }: { prediction: Prediction | undefined; result?: Outcome | null }) {
  if (!prediction) return <span className="chips caption">fără predicție</span>;
  return (
    <span className="chips" aria-hidden="true">
      {OUTCOMES.map((outcome) => {
        const chosen = prediction.most_likely === outcome;
        return (
          <span
            key={outcome}
            className={`chip${chosen ? " chosen" : ""}${result === outcome ? " actual" : ""}`}
            title={chipLabel(prediction, outcome, result)}
          >
            {percent(chance(prediction, outcome), 0)}
            {chosen && prediction.hit !== null && <HitMark hit={prediction.hit} />}
          </span>
        );
      })}
    </span>
  );
}

/** The names over the chips of a list: Gazde, Egal, Oaspeți, and, over a day's list with
 * coming matches, "scor probabil" over the outlined scores. */
export function ColumnsHead({ stacked = false, extra = false, likely = false }: { stacked?: boolean; extra?: boolean; likely?: boolean }) {
  if (likely) {
    return (
      <div className="columns-head with-likely" aria-hidden="true">
        <span />
        <span className="columns-likely">scor probabil · Poisson</span>
        <span className="columns-chips">
          <span>Gazde</span>
          <span>Egal</span>
          <span>Oaspeți</span>
        </span>
      </div>
    );
  }
  return (
    <div className={`columns-head${stacked ? " stacked" : ""}${extra ? " with-extra" : ""}`} aria-hidden="true">
      {stacked && <span />}
      <span>Gazde</span>
      <span>Egal</span>
      <span>Oaspeți</span>
      {extra && <span />}
    </div>
  );
}

interface Props {
  forecast: Forecast;
  model: string;
  favourite?: string | null;
  stacked?: boolean; // a narrow column: home over away, each with its goals, the chips below
  showDate?: boolean; // a team's matches: the day instead of the kickoff
  extra?: ReactNode; // a last column (the review's surprise)
  onOpen: (forecast: Forecast) => void;
}

function StackedTeam({ team, goals, favourite, won }: { team: string; goals: number | null; favourite: boolean; won: boolean }) {
  return (
    <span className={`team${favourite ? " favourite" : ""}${won ? " won" : ""}`}>
      <Crest team={team} size={22} ring={favourite} />
      <span className="name">{teamName(team)}</span>
      {goals !== null && <b className="goals">{goals}</b>}
    </span>
  );
}

/** The row for a screen reader: the teams, the score or the state, the day and the model's three
 * chances ("Gazde 45%, cel mai probabil, nimerit; Egal 28%; Oaspeți 27%"). */
export function rowName(forecast: Forecast, prediction: Prediction | undefined): string {
  const score = forecast.result !== null ? ` ${forecast.home_goals}–${forecast.away_goals}` : "";
  const day = `${forecast.date.slice(8, 10)}.${forecast.date.slice(5, 7)}`;
  const likely = likelyScore(forecast);
  const state = forecast.result !== null ? "" : `, ${statusText(forecast)}${likely ? `, scor probabil ${likely[0]}–${likely[1]}` : ""}`;
  const chances = prediction
    ? OUTCOMES.map((outcome) => chipLabel(prediction, outcome, forecast.result)).join("; ")
    : "fără predicție";
  return `${teamName(forecast.home_team)}${score} ${teamName(forecast.away_team)}, ${day}${state}. ${prediction?.label ?? ""}: ${chances}`;
}

/** Poisson's most likely score of a match still to come; none once played or past its day. */
export function likelyScore(forecast: Forecast): [number, number] | null {
  if (forecast.result !== null || forecast.postponed || isPending(forecast)) return null;
  return forecast.predictions.find((p) => p.model === "Poisson")?.likely_score ?? null;
}

/** Between the teams: the score once played, else Poisson's most likely score, outlined. */
function CentreScore({ forecast }: { forecast: Forecast }) {
  if (forecast.result !== null) return <span className="score">{`${forecast.home_goals} : ${forecast.away_goals}`}</span>;
  const likely = likelyScore(forecast);
  if (!likely) return <span className="score empty">–</span>;
  return (
    <span className="score likely" title="Cel mai probabil scor după modelul Poisson">
      {likely[0]} : {likely[1]}
    </span>
  );
}

export function MatchRow({ forecast, model, favourite, stacked = false, showDate = false, extra, onOpen }: Props) {
  const played = forecast.result !== null;
  const prediction = forecast.predictions.find((p) => p.model === model);
  const pending = isPending(forecast);
  const upcoming = !played && !forecast.postponed && !pending;
  const status = (
    <span className={`status${upcoming ? " upcoming" : ""}${pending ? " pending" : ""}`}>
      {statusText(forecast, showDate)}
      {showDate && upcoming && forecast.kickoff && <small>{forecast.kickoff}</small>}
      {showDate && pending && <small>fără rezultat</small>}
    </span>
  );
  if (stacked) {
    return (
      <button className={`match-row stacked${pending ? " pending" : ""}`} onClick={() => onOpen(forecast)} aria-label={rowName(forecast, prediction)}>
        {status}
        <span className="stack">
          <StackedTeam team={forecast.home_team} goals={forecast.home_goals} favourite={favourite === forecast.home_team} won={forecast.result === "H"} />
          <StackedTeam team={forecast.away_team} goals={forecast.away_goals} favourite={favourite === forecast.away_team} won={forecast.result === "A"} />
        </span>
        <Chips prediction={prediction} result={forecast.result} />
      </button>
    );
  }
  return (
    <button
      className={`match-row${extra !== undefined ? " with-extra" : ""}${pending ? " pending" : ""}`}
      onClick={() => onOpen(forecast)}
      aria-label={rowName(forecast, prediction)}
    >
      {status}
      <span className="teams">
        <Team team={forecast.home_team} side="home" favourite={favourite === forecast.home_team} won={forecast.result === "H"} />
        <CentreScore forecast={forecast} />
        <Team team={forecast.away_team} side="away" favourite={favourite === forecast.away_team} won={forecast.result === "A"} />
      </span>
      <Chips prediction={prediction} result={forecast.result} />
      {extra}
    </button>
  );
}
