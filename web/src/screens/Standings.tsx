// Clasament: a league's table with the clubs' crests and their last five results, at the end of a
// season (so far, for the season in progress) or before any day of it; a click opens the team.
// Since Phase 25 the head shows the leader's stadium, the season in progress marks the Champions
// League and relegation places (today's rules; earlier seasons had others, so they stay plain),
// and it can be projected to its end: the remaining fixtures played many times by the server
// from a model's predictions.
import { useEffect, useState } from "react";
import { api } from "../api";
import { Crest } from "../components/Crest";
import { FormSquares } from "../components/FormSquares";
import { ModelSwitch } from "../components/ModelSwitch";
import { Problem } from "../components/Problem";
import { StadiumHead } from "../components/ScreenHead";
import { SkeletonTable } from "../components/Skeleton";
import { dateText, integer, isoDay, number, parseDay, percent, quantity, seasonText, signed, teamName } from "../format";
import type { League, Projection, SeasonDays, Standings as Table } from "../types";
import { MODELS } from "../types";

interface Props {
  title: string;
  description: string;
  league: League;
  season: string;
  favourite: string | null;
  onSeason: (season: string) => void;
  onTeam: (code: string, team: string, season: string) => void;
}

const COLUMNS = ["M", "V", "E", "Î", "GM", "GP", "Dif.", "Pct."];
const TOP_PLACES = 4; // as the server's projection: the Champions League places
const BOTTOM_PLACES = 3; // and relegation (with the play-off place of Bundesliga and Ligue 1)

type Mode = "season" | "before" | "projection";

/** A week before ``lastDay``, never before the season's first day. */
export function weekBefore(lastDay: string, firstDay: string): string {
  const day = parseDay(lastDay);
  day.setDate(day.getDate() - 7);
  const text = isoDay(day);
  return text < firstDay ? firstDay : text;
}

export function difference(value: number): string {
  return value === 0 ? "0" : signed(value, 0);
}

/** The zone of a place in a table of ``teams`` clubs: "top", "bottom" or "". */
export function zoneOf(position: number, teams: number): string {
  if (position <= TOP_PLACES) return "top";
  if (position > teams - BOTTOM_PLACES) return "bottom";
  return "";
}

/** A chance as the projection writes it: "<1%" and ">99%" at the ends, "–" for none at all. */
export function chanceText(value: number): string {
  if (value === 0) return "–";
  if (value < 0.01) return "<1%";
  if (value > 0.99 && value < 1) return ">99%";
  return percent(value, 0);
}

export function Standings({ title, description, league, season, favourite, onSeason, onTeam }: Props) {
  const [mode, setMode] = useState<Mode>("season");
  const [days, setDays] = useState<SeasonDays | null>(null);
  const [day, setDay] = useState("");
  const [table, setTable] = useState<Table | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inProgress = season === league.current_season;

  useEffect(() => {
    if (mode === "projection" && !inProgress) setMode("season");
  }, [mode, inProgress]);

  useEffect(() => {
    let live = true;
    api.season(league.code, season).then((found) => {
      if (!live) return;
      setDays(found);
      // in the season in progress the server offers the day after the last match: a week earlier
      // shows a table that differs from the one so far
      setDay(season === league.current_season ? weekBefore(found.suggested_day, found.first_day) : found.suggested_day);
    });
    return () => {
      live = false;
    };
  }, [league.code, season]);

  useEffect(() => {
    let live = true;
    setError(null);
    api
      .standings(league.code, season, mode === "before" ? day || undefined : undefined)
      .then((found) => live && setTable(found))
      .catch((reason: Error) => live && setError(reason.message));
    return () => {
      live = false;
    };
  }, [league.code, season, mode, day]);

  let when = "";
  if (table) {
    if (!table.whole_season) when = `înainte de ${dateText(parseDay(table.before))}`;
    else when = table.in_progress ? "până acum (sezon în desfășurare)" : "tot sezonul";
  }
  const current = table && table.competition === league.code && table.season === season ? table : null;
  const leader = current?.rows[0]?.team ?? null;

  return (
    <div className="standings-screen">
      <StadiumHead league={league} team={leader} title={title} description={description} />
      <div className="control-row">
        <label className="caption" htmlFor="standings-season">
          Sezon
        </label>
        <select id="standings-season" value={season} onChange={(event) => onSeason(event.target.value)}>
          {[...league.seasons].reverse().map((item) => (
            <option key={item} value={item}>
              {seasonText(item)}
            </option>
          ))}
        </select>
        <span className="grow" />
        <div className="segmented" role="group" aria-label="Ce clasament">
          <button className={`pill${mode === "season" ? " chosen" : ""}`} aria-pressed={mode === "season"} onClick={() => setMode("season")}>
            {inProgress ? "Până acum" : "Tot sezonul"}
          </button>
          <button className={`pill${mode === "before" ? " chosen" : ""}`} aria-pressed={mode === "before"} onClick={() => setMode("before")}>
            Înainte de o zi
          </button>
          {inProgress && (
            <button
              className={`pill${mode === "projection" ? " chosen" : ""}`}
              aria-pressed={mode === "projection"}
              onClick={() => setMode("projection")}
            >
              Proiecția finalului
            </button>
          )}
        </div>
        {mode === "before" && (
          <input
            type="date"
            aria-label="Ziua"
            value={day}
            min={days?.first_day}
            max={days?.last_day}
            onChange={(event) => event.target.value && setDay(event.target.value)}
          />
        )}
      </div>
      {mode === "projection" ? (
        <ProjectedTable league={league} favourite={favourite} onTeam={(team) => onTeam(league.code, team, season)} />
      ) : (
        <>
          {error && (
            <Problem detail={error}>Clasamentul nu a putut fi citit. Alege alt sezon sau încearcă din nou.</Problem>
          )}
          {!current && !error && <SkeletonTable rows={10} />}
          {current && (
            <section className="card standings-card">
              <h2>
                {league.name} {seasonText(current.season)} · {when}
              </h2>
              <div className="standings">
                <div className="standings-row head" aria-hidden="true">
                  <span>#</span>
                  <span>Echipă</span>
                  {COLUMNS.map((column) => (
                    <span key={column}>
                      {column}
                    </span>
                  ))}
                  <span className="form-head">
                    Ultimele 5
                  </span>
                </div>
                {current.rows.map((row) => {
                  const record = row.record;
                  const zone = current.in_progress ? zoneOf(row.position, current.rows.length) : "";
                  return (
                    <button
                      key={row.team}
                     
                      className={`standings-row${row.team === favourite ? " favourite" : ""}`}
                      aria-label={`Locul ${row.position}: ${teamName(row.team)}, ${record.points} puncte din ${record.played} meciuri, golaveraj ${difference(record.goal_difference)}`}
                      onClick={() => onTeam(league.code, row.team, current.season)}
                    >
                      <span className={`position${zone ? ` zone-${zone}` : ""}`}>
                        {row.position}
                      </span>
                      <span className="team">
                        <Crest team={row.team} size={26} ring={row.team === favourite} />
                        <span className="name">{teamName(row.team)}</span>
                      </span>
                      <span>{record.played}</span>
                      <span>{record.wins}</span>
                      <span>{record.draws}</span>
                      <span>{record.losses}</span>
                      <span>{record.goals_for}</span>
                      <span>{record.goals_against}</span>
                      <span>{difference(record.goal_difference)}</span>
                      <strong>{record.points}</strong>
                      <span className="form-cell">
                        <FormSquares results={row.form} />
                      </span>
                    </button>
                  );
                })}
              </div>
              {current.in_progress && <ZoneLegend code={league.code} />}
              <p className="caption">
                M meciuri, V victorii, E egaluri, Î înfrângeri, GM goluri marcate, GP goluri primite. La egalitate de
                puncte decid golaverajul, apoi golurile marcate; deducerile de puncte nu sunt incluse.
              </p>
            </section>
          )}
        </>
      )}
    </div>
  );
}

/** The leagues whose third-from-bottom club plays a relegation play-off. */
const PLAY_OFF_LEAGUES = ["D1", "F1"];

function ZoneLegend({ code }: { code: string }) {
  return (
    <div className="zone-legend">
      <span>
        <i className="zone-key top" /> Locurile 1–{TOP_PLACES}: Liga Campionilor
      </span>
      <span>
        <i className="zone-key bottom" /> Ultimele {BOTTOM_PLACES}: retrogradare
        {PLAY_OFF_LEAGUES.includes(code) && " (a treia de la coadă joacă barajul)"}
      </span>
    </div>
  );
}

/** The season in progress played to its end, from one model's predictions (server side). */
function ProjectedTable({ league, favourite, onTeam }: { league: League; favourite: string | null; onTeam: (team: string) => void }) {
  const [model, setModel] = useState<string>(MODELS[0]);
  const [projection, setProjection] = useState<Projection | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setError(null);
    setProjection(null);
    if (!league.prepared) return;
    api
      .projection(league.code, model)
      .then((found) => live && setProjection(found))
      .catch((reason: Error) => live && setError(reason.message));
    return () => {
      live = false;
    };
  }, [league.code, league.prepared, model]);

  if (error) {
    return <Problem detail={error}>Proiecția nu a putut fi calculată. Încearcă din nou după actualizarea datelor.</Problem>;
  }
  if (!projection) return <SkeletonTable rows={10} />;
  const teams = projection.teams.length;
  return (
    <section className="card standings-card projection-card">
      <div className="projection-head">
        <div>
          <h2>Cum s-ar putea termina {league.name} {seasonText(projection.season)}</h2>
          <p className="caption">
            Cele {quantity(projection.fixtures, "meci rămas", "meciuri rămase")}, jucate de {integer(projection.simulations)} de ori cu
            probabilitățile modelului. Ordinea: punctele așteptate la final.
          </p>
        </div>
        <ModelSwitch league={league} model={model} ready="" onModel={setModel} />
      </div>
      <div className="projection">
        <div className="projection-row head" aria-hidden="true">
          <span>#</span>
          <span>Echipă</span>
          <span>Acum</span>
          <span title="Punctele așteptate la finalul sezonului">
            Pct. finale
          </span>
          <span>Campioană</span>
          <span>Top {projection.top_places}</span>
          <span>Retrogradare</span>
          <span className="places-head">
            Locul final: 1 → {teams}
          </span>
        </div>
        {projection.teams.map((team, index) => (
          <button
            key={team.team}
           
            className={`projection-row${team.team === favourite ? " favourite" : ""}`}
            aria-label={`${teamName(team.team)}: ${team.points} puncte acum, ${number(team.expected_points, 0)} așteptate la final; campioană ${chanceText(team.places[0])}, top ${projection.top_places} ${chanceText(team.top)}, retrogradare ${chanceText(team.bottom)}; ${placesLabel(team.places)}`}
            onClick={() => onTeam(team.team)}
          >
            <span className={`position${zoneOf(index + 1, teams) ? ` zone-${zoneOf(index + 1, teams)}` : ""}`}>
              {index + 1}
            </span>
            <span className="team">
              <Crest team={team.team} size={26} ring={team.team === favourite} />
              <span className="name">{teamName(team.team)}</span>
            </span>
            <span className="caption" title={`${team.played} meciuri jucate, ${team.remaining} rămase`}>
              {team.points}
            </span>
            <strong>{number(team.expected_points, 0)}</strong>
            <span>{chanceText(team.places[0])}</span>
            <span>{chanceText(team.top)}</span>
            <span>{chanceText(team.bottom)}</span>
            <span className="places" aria-hidden="true">
              {team.places.map((chance, place) => (
                <i
                  key={place}
                  className={place + 1 === projection.top_places || place + 1 === teams - projection.bottom_places ? "edge" : undefined}
                  style={{ opacity: placeOpacity(chance) }}
                  title={`Locul ${place + 1}: ${chanceText(chance)}`}
                />
              ))}
            </span>
          </button>
        ))}
      </div>
      <ZoneLegend code={league.code} />
      <p className="caption">
        Fiecare meci rămas se termină cu victoria gazdelor, egal sau victoria oaspeților, cu șansele date de{" "}
        {projection.label}. Sunt simulate doar rezultatele, nu și golurile, așa că la egalitate de puncte rămâne ordinea
        de azi. Proiecția e cât de bună e modelul: arată ce urmează dacă echipele joacă de acum încolo cum le vede el.
        {projection.unpredicted > 0 && ` ${projection.unpredicted} meciuri fără predicție nu sunt incluse.`}
      </p>
    </section>
  );
}

/** How strongly a place's cell is lit: its chance, on a square-root scale so that a place a club
 * reaches one time in twenty still shows; a place it never reaches stays almost dark. */
export function placeOpacity(chance: number): number {
  return chance === 0 ? 0.06 : 0.12 + 0.88 * Math.sqrt(chance);
}

/** "Locul 1: 62%, locul 2: 30%": the places a club can finish in, for a screen reader. */
function placesLabel(places: number[]): string {
  return places
    .map((chance, place) => [place, chance] as const)
    .filter(([, chance]) => chance >= 0.01)
    .map(([place, chance]) => `locul ${place + 1}: ${percent(chance, 0)}`)
    .join(", ");
}
