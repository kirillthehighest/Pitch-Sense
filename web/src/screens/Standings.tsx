// Clasament: a league's table with the clubs' crests and their last five results, at the end of a
// season (so far, for the season in progress) or before any day of it; a click opens the team.
import { useEffect, useState } from "react";
import { api } from "../api";
import { Crest } from "../components/Crest";
import { FormSquares } from "../components/FormSquares";
import { dateText, parseDay, seasonText, signed } from "../format";
import type { League, SeasonDays, Standings as Table } from "../types";

interface Props {
  league: League;
  season: string;
  favourite: string | null;
  onSeason: (season: string) => void;
  onTeam: (code: string, team: string, season: string) => void;
}

const COLUMNS = ["M", "V", "E", "Î", "GM", "GP", "Dif.", "Pct."];

export function difference(value: number): string {
  return value === 0 ? "0" : signed(value, 0);
}

export function Standings({ league, season, favourite, onSeason, onTeam }: Props) {
  const [wholeSeason, setWholeSeason] = useState(true);
  const [days, setDays] = useState<SeasonDays | null>(null);
  const [day, setDay] = useState("");
  const [table, setTable] = useState<Table | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    api.season(league.code, season).then((found) => {
      if (!live) return;
      setDays(found);
      setDay(found.suggested_day);
    });
    return () => {
      live = false;
    };
  }, [league.code, season]);

  useEffect(() => {
    let live = true;
    setError(null);
    api
      .standings(league.code, season, wholeSeason ? undefined : day || undefined)
      .then((found) => live && setTable(found))
      .catch((reason: Error) => live && setError(reason.message));
    return () => {
      live = false;
    };
  }, [league.code, season, wholeSeason, day]);

  let when = "";
  if (table) {
    if (!table.whole_season) when = `înainte de ${dateText(parseDay(table.before))}`;
    else when = table.in_progress ? "până acum (sezon în desfășurare)" : "tot sezonul";
  }

  return (
    <div className="standings-screen">
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
        <button className={`pill${wholeSeason ? " chosen" : ""}`} onClick={() => setWholeSeason(true)}>
          Tot sezonul
        </button>
        <button className={`pill${wholeSeason ? "" : " chosen"}`} onClick={() => setWholeSeason(false)}>
          Înainte de o zi
        </button>
        {!wholeSeason && (
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
      {error && <p className="problem">Clasamentul nu a putut fi citit. {error}</p>}
      {table && (
        <section className="card standings-card">
          <h2>
            {league.name} {seasonText(table.season)} · {when}
          </h2>
          <div className="standings" role="table">
            <div className="standings-row head" role="row">
              <span>#</span>
              <span>Echipă</span>
              {COLUMNS.map((column) => (
                <span key={column}>{column}</span>
              ))}
              <span className="form-head">Ultimele 5</span>
            </div>
            {table.rows.map((row) => {
              const record = row.record;
              return (
                <button
                  key={row.team}
                  role="row"
                  className={`standings-row${row.team === favourite ? " favourite" : ""}`}
                  onClick={() => onTeam(league.code, row.team, table.season)}
                >
                  <span className="position">{row.position}</span>
                  <span className="team">
                    <Crest team={row.team} size={26} ring={row.team === favourite} />
                    <span className="name">{row.team}</span>
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
          <p className="caption">
            M meciuri, V victorii, E egaluri, Î înfrângeri, GM goluri marcate, GP goluri primite. La egalitate de
            puncte decid golaverajul, apoi golurile marcate; deducerile de puncte nu sunt incluse.
          </p>
        </section>
      )}
    </div>
  );
}
