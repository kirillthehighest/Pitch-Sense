// A match's page (Phase 19's, in the web interface): both clubs on a head over the home club's
// stadium, what each model expects and why, how both teams came into the match side by side, and
// the likely scores of the Poisson model. A hypothetical match (two teams of a season and a day
// chosen by the user) opens on the same page.
// Since Phase 25 the head carries the verdict: the three models' bars under the score, and which
// club they favour; on the Poisson grid the score that happened is ringed. Since Phase 26 the bars
// are shown once, in the head, each opening its model's reasoning; below them, what the models
// learn from (the teams side by side) and the likely scores.
import { useEffect, useState } from "react";
import { api } from "../api";
import { useChosenModel } from "../chosenModel";
import { Crest } from "../components/Crest";
import { Flag } from "../components/Flag";
import { FormSquares } from "../components/FormSquares";
import { ChevronIcon } from "../components/Icons";
import { HitMark, isPending, isUnsure } from "../components/MatchRow";
import { Problem } from "../components/Problem";
import { SkeletonCard } from "../components/Skeleton";
import { ScoreGrid } from "../components/ScoreGrid";
import { StadiumPhoto } from "../components/StadiumPhoto";
import { capitalised, dateText, integer, longDateText, number, parseDay, percent, quantity, seasonText, stadiumName, teamName, withKickoff } from "../format";
import { MODEL_COLOURS } from "../theme";
import type { Forecast, League, MatchKey, MatchPage as Page, Outcome, Prediction, TeamState } from "../types";
import { MODELS } from "../types";

interface Props {
  matchKey: MatchKey;
  leagues: League[];
  favourite: string | null;
  onBack: () => void;
  onTeam: (code: string, team: string, season: string) => void;
  onSimulate?: (code: string, home: string) => void; // a simulated match: change it in the dialog
}

export function MatchPage({ matchKey, leagues, favourite, onBack, onTeam, onSimulate }: Props) {
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
        {page?.forecast.hypothetical && onSimulate && (
          <button className="button" onClick={() => onSimulate(code, home)}>
            Schimbă meciul simulat
          </button>
        )}
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
          <ScoresCard page={page} />
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
  const [model] = useChosenModel();
  const pick = forecast.predictions.find((p) => p.model === model);
  const pickScore = !played && !pending ? pick?.likely_score : null;
  const top = page.poisson?.top_scores[0];
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
      <h1 className="visually-hidden">
        {teamName(forecast.home_team)} – {teamName(forecast.away_team)}
      </h1>
      <StadiumPhoto team={forecast.home_team} className="behind" />
      <div className="head-shade" />
      <div className="match-head-top">
        <Flag code={league.code} size={20} />
        <span>
          {league.name} · {seasonText(forecast.season)} · {when}
          {page.stadium && ` · ${stadiumName(page.stadium)}`}
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
          <strong>{played ? `${forecast.home_goals}–${forecast.away_goals}` : "VS"}</strong>
          <span className={`state ${played ? "final" : forecast.hypothetical ? "hypothetical" : pending ? "pending" : "upcoming"}`}>
            {pending ? "Fără rezultat" : page.status}
          </span>
          {pick && pickScore && (
            // both scores in one line: Poisson's likeliest overall, then the outlined one of the
            // lists, the likeliest if the chosen model's pick comes true
            <span className="head-likely">
              {top && top.home === pickScore[0] && top.away === pickScore[1] ? (
                "cel mai probabil scor"
              ) : (
                <>
                  {top && `cel mai probabil scor ${top.home}–${top.away} · `}
                  {pick.most_likely === "D" ? "la egal" : `dacă câștigă ${teamName(pick.most_likely === "H" ? forecast.home_team : forecast.away_team)}`}
                </>
              )}{" "}
              <b>
                {pickScore[0]}–{pickScore[1]}
              </b>
            </span>
          )}
        </div>
      </div>
      <Consensus page={page} />
      {page.stadium && <span className="credit">Foto: Wikimedia Commons</span>}
    </section>
  );
}

const SIDES: Record<Outcome, string> = { H: "home", D: "draw", A: "away" };

/** Whom the models favour: "Toate cele trei modele o văd favorită pe Napoli", "2 din 3 modele văd
 * egalul cel mai probabil", "Modelele nu cad de acord"; "la limită" when their favourite leads
 * the next result by less than five points on average. */
export function consensusText(forecast: Forecast): string {
  const predictions = forecast.predictions;
  if (predictions.length === 0) return "Niciun model nu are destule meciuri anterioare";
  const counts = new Map<Outcome, number>();
  for (const prediction of predictions) counts.set(prediction.most_likely, (counts.get(prediction.most_likely) ?? 0) + 1);
  const [outcome, count] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
  const total = predictions.length;
  if (count === 1 && total > 1) return "Modelele nu cad de acord";
  let who = `${count} din ${total} modele`;
  if (count === total) who = total === 1 ? "Singurul model" : total === 3 ? "Toate cele trei modele" : "Toate modelele";
  const one = count === 1;
  const backing = predictions.filter((prediction) => prediction.most_likely === outcome);
  const lead =
    backing.reduce((sum, prediction) => {
      const chances = [prediction.home, prediction.draw, prediction.away].sort((a, b) => b - a);
      return sum + chances[0] - chances[1];
    }, 0) / backing.length;
  const close = lead < 0.05 ? ", la limită" : "";
  if (outcome === "D") return `${who} ${one ? "vede" : "văd"} egalul cel mai probabil${close}`;
  const team = teamName(outcome === "H" ? forecast.home_team : forecast.away_team);
  return `${who} o ${one ? "vede" : "văd"} favorită pe ${team}${close}`;
}

const FORM_POINTS: Record<string, number> = { W: 3, D: 1, L: 0 };

/** Whether the values listed for logistic regression (points per match, form, Elo; `lead` is
 * how many favour the home side minus how many favour the away side) agree with its favourite,
 * and, when they do not, what else it weighs: home advantage, learnt from past matches as its
 * intercept, and the goal difference and shots on target of the latest home and away matches. */
export function logisticVerdict(lead: number, favourite: string | undefined, home: string, away: string): string {
  const others = "golaverajul și șuturile pe poartă din ultimele meciuri acasă și în deplasare";
  if (favourite === "H" && lead < 0) {
    return `Aceste cifre o avantajează pe ${away}; modelul o vede totuși favorită pe ${home}, din avantajul terenului propriu, învățat din meciurile trecute, și din celelalte valori pe care le cântărește (${others}).`;
  }
  if (favourite === "A" && lead > 0) {
    return `Aceste cifre o avantajează pe ${home}; modelul o vede totuși favorită pe ${away}, din celelalte valori pe care le cântărește (${others}), chiar cu avantajul terenului de partea gazdelor.`;
  }
  if (favourite === "D") return "Diferențele aproape se anulează, așa că modelul socotește egalul cel mai probabil.";
  if (favourite === undefined) return "";
  return `Aceste cifre și avantajul terenului propriu, învățat din meciurile trecute, o arată favorită pe ${favourite === "H" ? home : away}.`;
}

/** Why one model sees this match as it does, from the numbers it starts from (the server's):
 * Elo's ratings and home advantage, Poisson's expected goals, the differences the logistic
 * regression weighs. Each sentence is about this match, not the model in general. */
export function modelReason(model: string, page: Page): string {
  const { forecast, home, away } = page;
  const homeName = teamName(home.team);
  const awayName = teamName(away.team);
  if (model === "Elo") {
    const lead = home.rating + page.elo_home_advantage - away.rating;
    const points = (value: number) => quantity(Math.round(Math.abs(value)), "punct", "puncte");
    const ahead = lead >= 0 ? `${homeName} pornește cu ${points(lead)} înainte` : `${awayName} rămâne cu ${points(lead)} înainte`;
    return `Ratingul Elo: ${homeName} ${integer(Math.round(home.rating))}, ${awayName} ${integer(Math.round(away.rating))}. Terenul propriu valorează ${points(page.elo_home_advantage)}, deci ${ahead}.`;
  }
  if (model === "Poisson" && page.poisson) {
    const [homeGoals, awayGoals] = page.poisson.expected_goals;
    const prediction = forecast.predictions.find((p) => p.model === "Poisson");
    const likely = prediction ? favouriteScore(page.poisson.grid, prediction.most_likely) : null;
    const top = page.poisson.top_scores[0];
    let scores = "";
    if (prediction && likely) {
      const favourite = prediction.most_likely === "D" ? "egalul" : prediction.most_likely === "H" ? homeName : awayName;
      const chanceOf = page.poisson.grid[likely[0]]?.[likely[1]];
      const among = prediction.most_likely === "D" ? "dintre egaluri" : `dintre victoriile ${prediction.most_likely === "H" ? "gazdelor" : "oaspeților"}`;
      scores = ` Îl vede favorit pe ${favourite}; ${among}, cel mai probabil e ${likely[0]}–${likely[1]}${chanceOf !== undefined ? ` (${percent(chanceOf)})` : ""}.`;
      if (top && (top.home !== likely[0] || top.away !== likely[1])) {
        scores += ` Cel mai probabil scor în general: ${top.home}–${top.away} (${percent(top.probability)}).`;
      }
    }
    return `Goluri așteptate: ${homeName} ${number(homeGoals, 2)}, ${awayName} ${number(awayGoals, 2)}.${scores}`;
  }
  const perMatch = (points: number, played: number) => (played ? number(points / played, 2) : "–");
  const form = (results: string[]) => results.reduce((sum, result) => sum + (FORM_POINTS[result] ?? 0), 0);
  const listed = `În acest sezon: ${homeName} ${perMatch(home.record.points, home.record.played)} puncte pe meci, ${awayName} ${perMatch(away.record.points, away.record.played)}; forma, ${form(home.form)} față de ${form(away.form)} puncte din ultimele 5 meciuri; ratingul Elo, ${integer(Math.round(home.rating))} față de ${integer(Math.round(away.rating))}.`;
  const rate = (record: { points: number; played: number }) => (record.played ? record.points / record.played : 0);
  const lead =
    Math.sign(rate(home.record) - rate(away.record)) + Math.sign(form(home.form) - form(away.form)) + Math.sign(home.rating - away.rating);
  const favourite = forecast.predictions.find((p) => p.model === model)?.most_likely;
  return `Cântărește diferențele dintre echipe. ${listed} ${logisticVerdict(lead, favourite, homeName, awayName)}`;
}

/** The three models' bars, one under the other, under the score of the head: the most likely
 * result of each in the accent, as everywhere; a click on a model opens why it thinks so. */
function Consensus({ page }: { page: Page }) {
  const { forecast } = page;
  const [open, setOpen] = useState<string | null>(null);
  const predictions = ordered(forecast.predictions);
  if (predictions.length === 0) return <p className="consensus-verdict">{consensusText(forecast)}</p>;
  const played = forecast.result !== null;
  const right = predictions.filter((prediction) => prediction.hit).length;
  return (
    <div className="consensus" aria-label="Ce spun modelele">
      <p className="consensus-verdict">
        {played ? `${right} din ${predictions.length} modele au nimerit rezultatul` : consensusText(forecast)}
      </p>
      <div className="consensus-sides" aria-hidden="true">
        <span />
        <span>{teamName(forecast.home_team)}</span>
        <span>Egal</span>
        <span>{teamName(forecast.away_team)}</span>
        <span />
      </div>
      {predictions.map((prediction) => {
        const expanded = open === prediction.model;
        return (
          <div key={prediction.model} className={`consensus-item${expanded ? " open" : ""}`}>
            <button
              className="consensus-row"
              aria-expanded={expanded}
              aria-label={`${prediction.label}: ${teamName(forecast.home_team)} ${percent(prediction.home, 0)}, egal ${percent(prediction.draw, 0)}, ${teamName(forecast.away_team)} ${percent(prediction.away, 0)}${prediction.hit === null ? "" : prediction.hit ? ", nimerit" : ", ratat"}. De ce?`}
              onClick={() => setOpen(expanded ? null : prediction.model)}
            >
              <span className="consensus-name">
                <i style={{ background: MODEL_COLOURS[prediction.model] }} />
                {prediction.label}
              </span>
              <span className="consensus-bar" aria-hidden="true">
                {(["H", "D", "A"] as Outcome[]).map((outcome) => {
                  const value = outcome === "H" ? prediction.home : outcome === "D" ? prediction.draw : prediction.away;
                  return (
                    <span
                      key={outcome}
                      className={`part ${SIDES[outcome]}${prediction.most_likely === outcome ? " likely" : ""}${prediction.most_likely === outcome && isUnsure(value) ? " unsure" : ""}${forecast.result === outcome ? " actual" : ""}`}
                      style={{ flexGrow: value }}
                    >
                      {percent(value, 0)}
                    </span>
                  );
                })}
              </span>
              <span className="consensus-mark">{prediction.hit !== null && <HitMark hit={prediction.hit} />}</span>
              <span className="consensus-why" aria-hidden="true">
                <ChevronIcon direction={expanded ? "up" : "down"} />
              </span>
            </button>
            {expanded && (
              <div className="consensus-reason">
                <p>{modelReason(prediction.model, page)}</p>
                <p className="consensus-general">{page.explanations[prediction.model]}</p>
              </div>
            )}
          </div>
        );
      })}
      <p className="consensus-note">
        {page.knowledge} Apasă pe un model ca să vezi de ce vede meciul așa.
      </p>
    </div>
  );
}

function ordered(predictions: Prediction[]): Prediction[] {
  return MODELS.map((model) => predictions.find((p) => p.model === model)).filter(Boolean) as Prediction[];
}

/** The day before ``day`` (ISO): the last day whose matches the page knows. */
function dayBefore(day: string): Date {
  const moment = parseDay(day);
  moment.setDate(moment.getDate() - 1);
  return moment;
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
    ["Puncte", `${home.record.points}`, `${away.record.points}`, better(home.record.points, away.record.points)],
    ["Victorii – egaluri – înfrângeri", record(home), record(away), null],
    ["Goluri marcate – primite", goals(home), goals(away), better(difference(home), difference(away))],
    ["Rating Elo", integer(Math.round(home.rating)), integer(Math.round(away.rating)), better(home.rating, away.rating)],
  ];
  return (
    <section className="card teams-card">
      <h2>Ce contează în acest meci</h2>
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
        Cum vin echipele după meciurile jucate până pe {dateText(dayBefore(page.before))}: din aceste valori învață modelele. În
        evidență, valoarea mai bună a fiecărui rând.
      </p>
    </section>
  );
}

/** The likeliest score giving one result, read off the server's score grid (rows home goals,
 * columns away goals): Poisson's favourite result told as a score. */
export function favouriteScore(grid: number[][], outcome: string): [number, number] | null {
  let best: [number, number] | null = null;
  let chance = -1;
  grid.forEach((row, home) =>
    row.forEach((value, away) => {
      const result = home > away ? "H" : home < away ? "A" : "D";
      if (result === outcome && value > chance) {
        best = [home, away];
        chance = value;
      }
    }),
  );
  return best;
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
          <div
            key={`${score.home}-${score.away}`}
            className="top-score"
          >
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
    </section>
  );
}

/** Every score from 0–0 to 6–6 with its Poisson chance, the final one ringed once played. */
function ScoresCard({ page }: { page: Page }) {
  const { forecast, poisson } = page;
  if (!poisson) return null;
  return (
    <section className="card scores-card">
      <h2>Șansa fiecărui scor, de la 0–0 la 6–6</h2>
      <ScoreGrid
        grid={poisson.grid}
        home={teamName(forecast.home_team)}
        away={teamName(forecast.away_team)}
        accent={MODEL_COLOURS.Poisson}
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
