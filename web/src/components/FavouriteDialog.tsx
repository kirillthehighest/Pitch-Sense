// "Echipa ta": the club the user follows, chosen from any league's latest season. Its matches are
// highlighted everywhere, its card leads Meciuri and the match of the day prefers it.
import { type FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Favourite, League } from "../types";
import { Crest } from "./Crest";

interface Props {
  leagues: League[];
  league: League;
  favourite: Favourite | null;
  onClose: () => void;
  onChoose: (favourite: Favourite | null) => void;
  onOpenTeam: (favourite: Favourite) => void;
}

export function FavouriteDialog({ leagues, league, favourite, onClose, onChoose, onOpenTeam }: Props) {
  const [code, setCode] = useState(favourite?.competition ?? league.code);
  const [teams, setTeams] = useState<string[]>([]);
  const [team, setTeam] = useState(favourite?.team ?? "");
  const chosen = leagues.find((item) => item.code === code) ?? league;

  useEffect(() => {
    let live = true;
    api.season(chosen.code, chosen.seasons[chosen.seasons.length - 1]).then((found) => {
      if (!live) return;
      setTeams(found.teams);
      setTeam((current) => (found.teams.includes(current) ? current : found.teams[0]));
    });
    return () => {
      live = false;
    };
  }, [chosen.code, chosen.seasons]);

  useEffect(() => {
    const close = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [onClose]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onChoose({ competition: code, team });
  };

  return (
    <div className="overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <form className="dialog card" onSubmit={submit} role="dialog" aria-label="Echipa ta">
        <div className="dialog-head">
          {team && <Crest team={team} size={40} ring />}
          <h2>Echipa ta</h2>
        </div>
        <p className="caption">
          Meciurile ei sunt evidențiate peste tot, cardul ei apare pe primul ecran, iar meciul zilei îi dă întâietate.
        </p>
        <div className="form-grid">
          <label htmlFor="favourite-league">Liga</label>
          <select id="favourite-league" value={code} onChange={(event) => setCode(event.target.value)}>
            {leagues.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
          <label htmlFor="favourite-team">Echipa</label>
          <select id="favourite-team" value={team} onChange={(event) => setTeam(event.target.value)} disabled={!teams.length}>
            {teams.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </div>
        <div className="dialog-actions">
          {favourite && (
            <>
              <button type="button" className="link left" onClick={() => onOpenTeam(favourite)}>
                Pagina echipei ›
              </button>
              <button type="button" className="button" onClick={() => onChoose(null)}>
                Fără echipă
              </button>
            </>
          )}
          <button type="button" className="button" onClick={onClose}>
            Renunță
          </button>
          <button type="submit" className="button primary" disabled={!team}>
            Alege
          </button>
        </div>
      </form>
    </div>
  );
}
