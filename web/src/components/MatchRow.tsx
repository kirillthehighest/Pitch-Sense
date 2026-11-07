// One match of a list, as in the score apps the team chose: the kickoff (or "Final"), the home
// team on the left and the away team on the right of the score, and the chosen model's three
// probabilities; the most likely is filled with the match's league accent and, once the match is
// played, carries a drawn mark: a light disc with a tick (it happened) or a dark one with a cross
// (it did not), so the marks never borrow a league's green or red. The chip of the result that
// happened is ringed. A match whose day is past but has no result yet says so (Phase 25).
// Since Phase 26 the most likely chip is always PitchSense's accent (hatched when the model gives
// it under UNSURE), and a coming match shows, outlined between the teams, the likeliest score of
// the chosen model's favourite result (read from the Poisson score grid), so the score and the
// chips beside it always agree; the real score replaces it once played.
import type { ReactNode } from "react";
import { isoDay, percent, teamName } from "../format";
import type { Forecast, Outcome, Prediction } from "../types";
import { Crest } from "./Crest";
import { CheckIcon, CrossIcon } from "./Icons";

const OUTCOMES: Outcome[] = ["H", "D", "A"];
export const UNSURE = 45; // a favourite shown under 45% is hatched: the model is far from sure

/** Whether a chance is "unsure", judged on the rounded percent the chip shows (45% is not). */
export function isUnsure(value: number): boolean {
  return Math.round(value * 100) < UNSURE;
}
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
    parts.push(isUnsure(chance(prediction, outcome)) ? "cel mai probabil, dar nesigur" : "cel mai probabil");
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
        const unsure = chosen && isUnsure(chance(prediction, outcome));
        return (
          <span
            key={outcome}
            className={`chip${chosen ? " chosen" : ""}${unsure ? " unsure" : ""}${result === outcome ? " actual" : ""}`}
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

/** The names over a list's columns: the likely score between the teams (when the list has coming
 * matches), then Gazde, Egal, Oaspeți over the chips. */
export function ColumnsHead({ stacked = false, extra = false, likely = false }: { stacked?: boolean; extra?: boolean; likely?: boolean }) {
  if (stacked) {
    return (
      <div className="columns-head stacked" aria-hidden="true">
        <span />
        <span>Gazde</span>
        <span>Egal</span>
        <span>Oaspeți</span>
      </div>
    );
  }
  return (
    <div className={`columns-head${extra ? " with-extra" : ""}`} aria-hidden="true">
      <span />
      <span className="columns-teams">
        {likely && <span title="Cel mai probabil scor al rezultatului ales de model, după grila de scoruri Poisson">scor probabil</span>}
      </span>
      <span className="columns-chips">
        <span>Gazde</span>
        <span>Egal</span>
        <span>Oaspeți</span>
      </span>
      {extra && <span />}
    </div>
  );
}

/** The likeliest score of a model's favourite result, for a match still to come (never for a
 * played match, nor for one past its day without a result: it would read as the result). */
export function likelyScore(forecast: Forecast, model: string): [number, number] | null {
  if (forecast.result !== null || forecast.postponed || isPending(forecast)) return null;
  return forecast.predictions.find((p) => p.model === model)?.likely_score ?? null;
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
  const likely = prediction ? likelyScore(forecast, prediction.model) : null;
  const state = forecast.result !== null ? "" : `, ${statusText(forecast)}${likely ? `, scor probabil ${likely[0]}–${likely[1]}` : ""}`;
  const chances = prediction
    ? OUTCOMES.map((outcome) => chipLabel(prediction, outcome, forecast.result)).join("; ")
    : "fără predicție";
  return `${teamName(forecast.home_team)}${score} ${teamName(forecast.away_team)}, ${day}${state}. ${prediction?.label ?? ""}: ${chances}`;
}

/** Between the teams: the real score once played, else the likeliest score of the model's
 * favourite result, outlined. */
function CentreScore({ forecast, model }: { forecast: Forecast; model: string }) {
  if (forecast.result !== null) return <span className="score">{`${forecast.home_goals}–${forecast.away_goals}`}</span>;
  const likely = likelyScore(forecast, model);
  if (!likely) return <span className="score empty">–</span>;
  return (
    <span className="score ghost" title={`Cel mai probabil scor al rezultatului ales: ${likely[0]}–${likely[1]}`}>
      {likely[0]}–{likely[1]}
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
        <CentreScore forecast={forecast} model={model} />
        <Team team={forecast.away_team} side="away" favourite={favourite === forecast.away_team} won={forecast.result === "A"} />
      </span>
      <Chips prediction={prediction} result={forecast.result} />
      {extra}
    </button>
  );
}

/** What the marks of a list mean, once per screen (the chips carry no words of their own). */
export function ChipLegend() {
  return (
    <p className="chip-legend" id="chip-legend">
      <span>
        <i className="legend-chip chosen" /> cel mai probabil
      </span>
      <span>
        <i className="legend-chip chosen unsure" /> nesigur (sub 45%)
      </span>
      <span>
        <i className="legend-chip actual" /> rezultatul meciului
      </span>
      <span>
        <HitMark hit /> nimerit
      </span>
      <span>
        <HitMark hit={false} /> ratat
      </span>
      <span>
        <i className="legend-ghost">1–0</i> scorul cel mai probabil al rezultatului ales
      </span>
    </p>
  );
}
