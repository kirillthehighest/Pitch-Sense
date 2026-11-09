// A match's page (Phase 19's, in the web interface): both clubs on a head lit by the deep colour
// of the match's league, what each model expects and why, how both teams came into the match side
// by side, and the likely scores of the Poisson model. A hypothetical match (two teams of a season
// and a day chosen by the user) opens on the same page. On the Poisson grid the score that
// happened is ringed (Phase 25). Since Phase 27 the models' bars are shown once, in "Ce spun
// modelele", each with its reasoning about this match, and the page wears the chosen league's
// colours, as the list it was opened from.
import { useEffect, useState } from "react";
import { api } from "../api";
import { Crest } from "../components/Crest";
import { Flag } from "../components/Flag";
import { FormSquares } from "../components/FormSquares";
import { CheckIcon, CrossIcon } from "../components/Icons";
import { isPending } from "../components/MatchRow";
import { Problem } from "../components/Problem";
import { ProbabilityBar } from "../components/ProbabilityBar";
import { SkeletonCard } from "../components/Skeleton";
import { ScoreGrid } from "../components/ScoreGrid";
import { StadiumPhoto } from "../components/StadiumPhoto";
import { capitalised, dateText, integer, longDateText, number, parseDay, percent, seasonText, teamName, withKickoff } from "../format";
import { MODEL_COLOURS, themeFor } from "../theme";
import type { League, MatchKey, MatchPage as Page, Prediction, TeamState } from "../types";
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
            <ModelsCard page={page} />
            <TeamsCard page={page} favourite={favourite} onTeam={openTeam} />
          </div>
          <PoissonCard page={page} chosen={chosen} />
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
      {page.stadium && <span className="credit">Foto: Wikimedia Commons</span>}
    </section>
  );
}

function ordered(predictions: Prediction[]): Prediction[] {
  return MODELS.map((model) => predictions.find((p) => p.model === model)).filter(Boolean) as Prediction[];
}

function ModelsCard({ page }: { page: Page }) {
  const { forecast } = page;
  const predictions = ordered(forecast.predictions);
  return (
    <section className="card models-card">
      <h2>Ce spun modelele</h2>
      <div className="bar-legend">
        <span>
          <i className="key home" />
          {teamName(forecast.home_team)} câștigă
        </span>
        <span>
          <i className="key draw" />
          Egal
        </span>
        <span>
          <i className="key away" />
          {teamName(forecast.away_team)} câștigă
        </span>
      </div>
      {predictions.length === 0 && (
        <p className="caption">Niciun model nu are destule meciuri anterioare pentru această dată.</p>
      )}
      {predictions.map((prediction) => (
        <div key={prediction.model} className="model-block">
          <div className="model-head">
            <i className="model-dot" style={{ background: MODEL_COLOURS[prediction.model] }} />
            <strong>{prediction.label}</strong>
            {prediction.hit !== null && (
              <span className={`verdict-pill ${prediction.hit ? "hit" : "miss"}`}>
                {prediction.hit ? <CheckIcon size={12} /> : <CrossIcon size={11} />}
                {prediction.hit ? "Nimerit" : "Ratat"}
              </span>
            )}
          </div>
          <ProbabilityBar prediction={prediction} />
          <p className="caption">{page.explanations[prediction.model]}</p>
        </div>
      ))}
      {page.verdict && <p className="verdict">{page.verdict}</p>}
      <p className="caption">{page.knowledge}</p>
    </section>
  );
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

function PoissonCard({ page, chosen }: { page: Page; chosen: string }) {
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
      <div className="poisson-layout">
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
        <ScoreGrid
          grid={poisson.grid}
          home={teamName(forecast.home_team)}
          away={teamName(forecast.away_team)}
          accent={themeFor(chosen).accent}
          actual={forecast.result !== null ? [forecast.home_goals as number, forecast.away_goals as number] : null}
        />
      </div>
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
