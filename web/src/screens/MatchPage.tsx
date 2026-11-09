// A match's page (Phase 19's, in the web interface): both clubs on a head lit by the deep colour
// of the match's league, what each model expects and why, how both teams came into the match side
// by side, and the likely scores of the Poisson model. A hypothetical match (two teams of a season
// and a day chosen by the user) opens on the same page. Since Phase 27 the page wears the chosen
// league's colours, as the list it was opened from.
// Since Phase 25 the head carries the verdict: the three models' bars under the score, and which
// club they favour; on the Poisson grid the score that happened is ringed. Since Phase 27 the bars
// are shown once, in the head, and each opens its model's reasoning.
import { useEffect, useState } from "react";
import { api } from "../api";
import { Crest } from "../components/Crest";
import { Flag } from "../components/Flag";
import { FormSquares } from "../components/FormSquares";
import { ChevronIcon } from "../components/Icons";
import { HitMark, isPending } from "../components/MatchRow";
import { Problem } from "../components/Problem";
import { SkeletonCard } from "../components/Skeleton";
import { ScoreGrid } from "../components/ScoreGrid";
import { StadiumPhoto } from "../components/StadiumPhoto";
import { capitalised, dateText, integer, longDateText, number, parseDay, percent, seasonText, teamName, withKickoff } from "../format";
import { MODEL_COLOURS, themeFor } from "../theme";
import type { Forecast, League, MatchKey, MatchPage as Page, Outcome, Prediction, TeamState } from "../types";
import { MODELS } from "../types";

interface Props {
  matchKey: MatchKey;
  leagues: League[];
  favourite: string | null;
  onBack: () => void;
  onTeam: (code: string, team: string, season: string) => void;
  chosen: string; // the chosen league, whose colours the page wears
}

export function MatchPage({ matchKey, leagues, favourite, onBack, onTeam, chosen }: Props) {
  const [page, setPage] = useState<Page | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { code, season, day, home, away } = matchKey;

  useEffect(() => {
    let live = true;
    setPage(null);
    setError(null);
    api
      .match({ code, season, day, home, away })
      .then((found) => live && setPage(found))
      .catch((reason: Error) => live && setError(reason.message));
    return () => {
      live = false;
    };
  }, [code, season, day, home, away]);

  const league = leagues.find((item) => item.code === code);
  const openTeam = (team: string) => onTeam(code, team, season);
  return (
    <div className="match-page">
      <div className="page-actions">
        <button className="link back" onClick={onBack}>
          ‹ Înapoi
        </button>
      </div>
      {error && (
        <Problem detail={error}>Meciul nu a putut fi deschis. Întoarce-te la listă și încearcă din nou.</Problem>
      )}
      {!page && !error && (
        <>
          <SkeletonCard height={250} title={false} />
          <div className="match-grid">
            <SkeletonCard height={300} />
            <SkeletonCard height={300} />
          </div>
        </>
      )}
      {page && league && (
        <>
          <MatchHead page={page} league={league} favourite={favourite} onTeam={openTeam} />
          <div className="match-grid">
            <TeamsCard page={page} favourite={favourite} onTeam={openTeam} />
            <PoissonCard page={page} />
          </div>
          {page.poisson && <ScoresCard page={page} accent={themeFor(chosen).accent} />}
        </>
      )}
    </div>
  );
}

function MatchHead({
  page, league, favourite, onTeam,
}: { page: Page; league: League; favourite: string | null; onTeam: (team: string) => void }) {
  const { forecast } = page;
  const played = forecast.result !== null;
  const pending = isPending(forecast);
  const when = withKickoff(
    capitalised(longDateText(parseDay(forecast.date))),
    forecast.kickoff,
    played || forecast.postponed || pending || forecast.hypothetical,
  );
  const sides: [TeamState, "home" | "away"][] = [
    [page.home, "home"],
    [page.away, "away"],
  ];
  return (
    <section className="match-head">
      <StadiumPhoto team={forecast.home_team} className="behind" />
      <div className="head-shade" />
      <div className="match-head-top">
        <Flag code={league.code} size={20} />
        <span>
          {league.name} · {seasonText(forecast.season)} · {when}
          {page.stadium && ` · ${page.stadium}`}
        </span>
      </div>
      <div className="match-head-teams">
        {sides.map(([state, side]) => (
          <button key={side} className={`head-team ${side}`} onClick={() => onTeam(state.team)}>
            <Crest team={state.team} size={84} ring={state.team === favourite} />
            <strong>{teamName(state.team)}</strong>
            <span>
              Locul {state.position} din {page.teams}
            </span>
          </button>
        ))}
        <div className="head-score">
          <strong>{played ? `${forecast.home_goals} – ${forecast.away_goals}` : "VS"}</strong>
          <span className={`state ${played ? "final" : forecast.hypothetical ? "hypothetical" : pending ? "pending" : "upcoming"}`}>
            {pending ? "Fără rezultat" : page.status}
          </span>

        </div>
      </div>
      <Consensus page={page} />
      {page.stadium && <span className="credit">Foto: Wikimedia Commons</span>}
    </section>
  );
}

const SIDES: Record<Outcome, string> = { H: "home", D: "draw", A: "away" };

/** Whom the models favour: "Toate cele trei modele mizează pe Napoli", "2 din 3 modele mizează pe
 * egal", "Modelele nu cad de acord"; "la limită" when their favourite leads the next result by
 * less than five points on average. */
export function consensusText(forecast: Forecast): string {
  const predictions = forecast.predictions;
  if (predictions.length === 0) return "Niciun model nu are destule meciuri anterioare";
  const counts = new Map<Outcome, number>();
  for (const prediction of predictions) counts.set(prediction.most_likely, (counts.get(prediction.most_likely) ?? 0) + 1);
  const [outcome, count] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
  const total = predictions.length;
  if (count === 1 && total > 1) return "Modelele nu cad de acord";
  const choice = outcome === "D" ? "egal" : teamName(outcome === "H" ? forecast.home_team : forecast.away_team);
  let who = `${count} din ${total} modele`;
  if (count === total) who = total === 1 ? "Singurul model" : total === 3 ? "Toate cele trei modele" : "Toate modelele";
  const backing = predictions.filter((prediction) => prediction.most_likely === outcome);
  const lead =
    backing.reduce((sum, prediction) => {
      const chances = [prediction.home, prediction.draw, prediction.away].sort((a, b) => b - a);
      return sum + chances[0] - chances[1];
    }, 0) / backing.length;
  return `${who} mizează pe ${choice}${lead < 0.05 ? ", la limită" : ""}`;
}

/** The three models' bars, one under the other, under the score of the head; a click on a model
 * opens the server's sentence on why it sees the match so. */
function Consensus({ page }: { page: Page }) {
  const [open, setOpen] = useState<string | null>(null);
  const { forecast } = page;
  const predictions = ordered(forecast.predictions);
  if (predictions.length === 0) {
    return <p className="consensus-verdict">Niciun model nu are destule meciuri anterioare pentru această dată.</p>;
  }
  const played = forecast.result !== null;
  const right = predictions.filter((prediction) => prediction.hit).length;
  return (
    <div className="consensus">
      <p className="consensus-verdict">
        {played ? `${right} din ${predictions.length} modele au nimerit rezultatul` : consensusText(forecast)}
      </p>
      <div className="consensus-sides" aria-hidden="true">
        <span>{teamName(forecast.home_team)}</span>
        <span>Egal</span>
        <span>{teamName(forecast.away_team)}</span>
      </div>
      {predictions.map((prediction) => {
        const expanded = open === prediction.model;
        const id = `motiv-${prediction.model.replace(/\s+/g, "-")}`;
        return (
          <div key={prediction.model} className={`consensus-item${expanded ? " open" : ""}`}>
            <button
              className="consensus-row"
              aria-expanded={expanded}
              aria-controls={id}
              onClick={() => setOpen(expanded ? null : prediction.model)}
            >
              <span className="consensus-name">
                <i style={{ background: MODEL_COLOURS[prediction.model] }} />
                {prediction.label}
              </span>
              <span
                className="consensus-bar"
                aria-label={`${teamName(forecast.home_team)} ${percent(prediction.home, 0)}, egal ${percent(prediction.draw, 0)}, ${teamName(forecast.away_team)} ${percent(prediction.away, 0)}`}
              >
                {(["H", "D", "A"] as Outcome[]).map((outcome) => {
                  const value = outcome === "H" ? prediction.home : outcome === "D" ? prediction.draw : prediction.away;
                  return (
                    <span
                      key={outcome}
                      className={`part ${SIDES[outcome]}${prediction.most_likely === outcome ? " likely" : ""}${forecast.result === outcome ? " actual" : ""}`}
                      style={{ flexGrow: value }}
                    >
                      {percent(value, 0)}
                    </span>
                  );
                })}
              </span>
              <span className="consensus-mark">{prediction.hit !== null && <HitMark hit={prediction.hit} />}</span>
              <span className="consensus-why-icon" aria-hidden="true">
                <ChevronIcon direction="right" />
              </span>
            </button>
            {expanded && (
              <p id={id} className="consensus-why">
                {page.explanations[prediction.model]}
              </p>
            )}
          </div>
        );
      })}
      <p className="consensus-note">
        {page.verdict && `${page.verdict} `}
        {page.knowledge} Apasă pe un model ca să vezi de ce vede meciul așa.
      </p>
    </div>
  );
}

function ordered(predictions: Prediction[]): Prediction[] {
  return MODELS.map((model) => predictions.find((p) => p.model === model)).filter(Boolean) as Prediction[];
}

type Better = "home" | "away" | null;

function better(home: number, away: number, higher = true): Better {
  if (home === away) return null;
  return home > away === higher ? "home" : "away";
}

function TeamsCard({ page, favourite, onTeam }: { page: Page; favourite: string | null; onTeam: (team: string) => void }) {
  const { home, away } = page;
  const difference = (state: TeamState) => state.record.goals_for - state.record.goals_against;
  const record = (state: TeamState) => `${state.record.wins}–${state.record.draws}–${state.record.losses}`;
  const goals = (state: TeamState) => `${state.record.goals_for}–${state.record.goals_against}`;
  const rows: [string, string, string, Better][] = [
    ["Loc în clasament", `${home.position}`, `${away.position}`, better(home.position, away.position, false)],
    ["Puncte", `${home.record.points}`, `${away.record.points}`, better(home.record.points, away.record.points)],
    ["Meciuri jucate", `${home.record.played}`, `${away.record.played}`, null],
    ["Victorii – egaluri – înfrângeri", record(home), record(away), null],
    ["Goluri marcate – primite", goals(home), goals(away), better(difference(home), difference(away))],
    ["Rating Elo", integer(Math.round(home.rating)), integer(Math.round(away.rating)), better(home.rating, away.rating)],
  ];
  return (
    <section className="card teams-card">
      <h2>Cum vin echipele</h2>
      <div className="compare-head">
        {[home, away].map((state, index) => (
          <button key={state.team} className={`compare-team ${index ? "away" : "home"}`} onClick={() => onTeam(state.team)}>
            <Crest team={state.team} size={30} ring={state.team === favourite} />
            <span>{teamName(state.team)}</span>
          </button>
        ))}
      </div>
      <div className="compare">
        {rows.map(([label, homeValue, awayValue, best]) => (
          <div key={label} className="compare-row">
            <span className={best === "home" ? "best" : ""}>{homeValue}</span>
            <span className="compare-label">{label}</span>
            <span className={best === "away" ? "best" : ""}>{awayValue}</span>
          </div>
        ))}
        <div className="compare-row">
          <FormSquares results={home.form} />
          <span className="compare-label">Ultimele 5 meciuri</span>
          <span className="form-right">
            <FormSquares results={away.form} />
          </span>
        </div>
      </div>
      <p className="caption">
        Înainte de {dateText(parseDay(page.before))}. În evidență: valoarea mai bună a fiecărui rând.
      </p>
    </section>
  );
}

function PoissonCard({ page }: { page: Page }) {
  const { forecast, poisson } = page;
  if (!poisson) {
    return (
      <section className="card">
        <h2>Scoruri probabile · Poisson</h2>
        <p className="caption">Nu există o predicție Poisson pentru acest meci.</p>
      </section>
    );
  }
  const largest = poisson.top_scores[0]?.probability ?? 1;
  const [homeGoals, awayGoals] = poisson.expected_goals;
  return (
    <section className="card poisson-card">
      <h2>Scoruri probabile · Poisson</h2>
      <div className="poisson-side">
          <div className="expected-goals">
            <div>
              <strong>{number(homeGoals, 2)}</strong>
              <span>{teamName(forecast.home_team)}</span>
            </div>
            <div>
              <strong>{number(awayGoals, 2)}</strong>
              <span>{teamName(forecast.away_team)}</span>
            </div>
          </div>
          <p className="caption">Goluri așteptate: câte ar marca în medie fiecare echipă în acest meci.</p>
          {forecast.result !== null && (
            <ActualScore grid={poisson.grid} home={forecast.home_goals as number} away={forecast.away_goals as number} />
          )}
          <h3>Cele mai probabile scoruri</h3>
          <div className="top-scores">
            {poisson.top_scores.map((score) => (
              <div key={`${score.home}-${score.away}`} className="top-score">
                <strong>
                  {score.home}–{score.away}
                </strong>
                <span className="track">
                  <span style={{ width: `${(100 * score.probability) / largest}%` }} />
                </span>
                <span>{percent(score.probability)}</span>
              </div>
            ))}
          </div>
      </div>
    </section>
  );
}

/** Every score from 0–0 to 6–6, in its own card under the two above. */
function ScoresCard({ page, accent }: { page: Page; accent: string }) {
  const { forecast, poisson } = page;
  if (!poisson) return null;
  return (
    <section className="card scores-card">
      <h2>Șansa fiecărui scor, de la 0–0 la 6–6</h2>
      <ScoreGrid
        grid={poisson.grid}
        home={teamName(forecast.home_team)}
        away={teamName(forecast.away_team)}
        accent={accent}
        actual={forecast.result !== null ? [forecast.home_goals as number, forecast.away_goals as number] : null}
      />
    </section>
  );
}

/** The score that happened, as the Poisson model saw it: its chance and its rank among all scores. */
function ActualScore({ grid, home, away }: { grid: number[][]; home: number; away: number }) {
  const chance = grid[home]?.[away];
  if (chance === undefined) {
    return <p className="actual-score">Scorul final, {home}–{away}, iese din grila 0–6 a modelului.</p>;
  }
  const rank = grid.flat().filter((value) => value > chance).length + 1;
  return (
    <p className="actual-score">
      Scorul final, <strong>{home}–{away}</strong>, avea {percent(chance)} în modelul Poisson:{" "}
      {rank === 1 ? "era cel mai probabil scor." : `al ${rank}-lea cel mai probabil scor.`}
    </p>
  );
}
