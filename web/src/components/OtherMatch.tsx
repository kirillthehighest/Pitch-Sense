// "Alt meci": any two teams of a season on a day of it, predicted only from the matches played
// before that day (the window's hypothetical match). The answer opens on the match page.
import { type FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { seasonText } from "../format";
import type { League, MatchKey, SeasonDays } from "../types";
import { Flag } from "./Flag";

interface Props {
  leagues: League[];
  league: League;
  onClose: () => void;
  onOpen: (key: MatchKey) => void;
}

export function OtherMatch({ leagues, league, onClose, onOpen }: Props) {
  const [code, setCode] = useState(league.code);
  const chosen = leagues.find((item) => item.code === code) ?? league;
  const [season, setSeason] = useState(chosen.seasons[chosen.seasons.length - 1]);
  const [seasonDays, setSeasonDays] = useState<SeasonDays | null>(null);
  const [home, setHome] = useState("");
  const [away, setAway] = useState("");
  const [day, setDay] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setSeasonDays(null);
    api
      .season(code, season)
      .then((found) => {
        if (!live) return;
        setSeasonDays(found);
        setHome(found.teams[0]);
        setAway(found.teams[1] ?? found.teams[0]);
        setDay(found.suggested_day);
      })
      .catch((reason: Error) => live && setMessage(reason.message));
    return () => {
      live = false;
    };
  }, [code, season]);

  useEffect(() => {
    const close = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [onClose]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (home === away) {
      setMessage("Alege două echipe diferite.");
      return;
    }
    onOpen({ code, season, day, home, away });
  };

  return (
    <div className="overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <form className="dialog card" onSubmit={submit} role="dialog" aria-label="Alt meci">
        <div className="dialog-head">
          <Flag code={code} size={22} />
          <h2>Alt meci</h2>
        </div>
        <p className="caption">
          Oricare două echipe ale unui sezon, la data aleasă. Predicția folosește doar meciurile jucate înainte de acea
          dată.
        </p>
        <div className="form-grid">
          <label htmlFor="other-league">Liga</label>
          <select
            id="other-league"
            value={code}
            onChange={(event) => {
              const next = leagues.find((item) => item.code === event.target.value) ?? league;
              setCode(next.code);
              setSeason(next.seasons[next.seasons.length - 1]);
            }}
          >
            {leagues.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
          <label htmlFor="other-season">Sezon</label>
          <select id="other-season" value={season} onChange={(event) => setSeason(event.target.value)}>
            {[...chosen.seasons].reverse().map((item) => (
              <option key={item} value={item}>
                {seasonText(item)}
              </option>
            ))}
          </select>
          <label htmlFor="other-home">Gazde</label>
          <select id="other-home" value={home} onChange={(event) => setHome(event.target.value)} disabled={!seasonDays}>
            {seasonDays?.teams.map((team) => <option key={team}>{team}</option>)}
          </select>
          <label htmlFor="other-away">Oaspeți</label>
          <select id="other-away" value={away} onChange={(event) => setAway(event.target.value)} disabled={!seasonDays}>
            {seasonDays?.teams.map((team) => <option key={team}>{team}</option>)}
          </select>
          <label htmlFor="other-day">Data</label>
          <input
            id="other-day"
            type="date"
            value={day}
            min={seasonDays?.first_day}
            max={seasonDays?.last_day}
            onChange={(event) => setDay(event.target.value)}
            disabled={!seasonDays}
            required
          />
        </div>
        {message && <p className="problem">{message}</p>}
        <div className="dialog-actions">
          <button type="button" className="button" onClick={onClose}>
            Renunță
          </button>
          <button type="submit" className="button primary" disabled={!seasonDays}>
            Calculează predicția
          </button>
        </div>
      </form>
    </div>
  );
}
