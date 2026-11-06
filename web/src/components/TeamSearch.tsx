// "Caută o echipă" (Phase 25, key /): every club of the five leagues' latest seasons, found as
// you type (accents and case do not matter); the arrows choose, Enter opens the club's page.
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { League } from "../types";
import { Crest } from "./Crest";
import { Flag } from "./Flag";
import { SearchIcon } from "./Icons";
import { Modal } from "./Modal";

interface Found {
  code: string;
  league: string;
  season: string;
  team: string;
}

/** The full names people type for Football-Data's short ones (the data keeps the short names). */
export const FULL_NAMES: Record<string, string> = {
  "Ath Madrid": "Atlético Madrid",
  "Ath Bilbao": "Athletic Bilbao",
  Sociedad: "Real Sociedad",
  Betis: "Real Betis",
  Espanol: "Espanyol",
  Vallecano: "Rayo Vallecano",
  Celta: "Celta Vigo",
  "Man City": "Manchester City",
  "Man United": "Manchester United",
  "Nott'm Forest": "Nottingham Forest",
  Wolves: "Wolverhampton",
  Tottenham: "Tottenham Hotspur Spurs",
  "Ein Frankfurt": "Eintracht Frankfurt",
  "M'gladbach": "Borussia Mönchengladbach",
  Dortmund: "Borussia Dortmund",
  Leverkusen: "Bayer Leverkusen",
  "FC Koln": "Köln Cologne",
  "Bayern Munich": "Bayern München",
  Inter: "Internazionale Inter Milano",
  Milan: "AC Milan",
  Verona: "Hellas Verona",
  "Paris SG": "Paris Saint-Germain PSG",
  "St Etienne": "Saint-Étienne",
};

/** "Atlético" and "atletico" match: lower case without diacritics. */
export function plain(text: string): string {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/** The clubs whose name contains the query, those starting with it first. */
export function searchTeams(teams: Found[], query: string, limit = 8): Found[] {
  const wanted = plain(query.trim());
  if (!wanted) return teams.slice(0, limit);
  const names = (item: Found) => plain(`${item.team} ${FULL_NAMES[item.team] ?? ""}`);
  const matching = teams.filter((item) => names(item).includes(wanted));
  const starts = (item: Found) => (names(item).split(" ").some((word) => word.startsWith(wanted)) ? 0 : 1);
  return [...matching].sort((a, b) => starts(a) - starts(b) || a.team.localeCompare(b.team)).slice(0, limit);
}

interface Props {
  leagues: League[];
  onClose: () => void;
  onOpen: (code: string, team: string, season: string) => void;
}

export function TeamSearch({ leagues, onClose, onOpen }: Props) {
  const [teams, setTeams] = useState<Found[]>([]);
  const [query, setQuery] = useState("");
  const [chosen, setChosen] = useState(0);

  useEffect(() => {
    let live = true;
    Promise.all(
      leagues.map((league) => {
        const season = league.seasons[league.seasons.length - 1];
        return api
          .season(league.code, season)
          .then((found) => found.teams.map((team) => ({ code: league.code, league: league.name, season, team })))
          .catch(() => [] as Found[]);
      }),
    ).then((found) => live && setTeams(found.flat()));
    return () => {
      live = false;
    };
  }, [leagues]);

  const shown = useMemo(() => searchTeams(teams, query), [teams, query]);
  useEffect(() => setChosen(0), [query]);

  const open = (item: Found | undefined) => {
    if (item) onOpen(item.code, item.team, item.season);
  };

  return (
    <Modal label="Caută o echipă" onClose={onClose}>
      <div className="dialog card search-dialog">
        <label className="search-field">
          <SearchIcon />
          <input
            autoFocus
            value={query}
            placeholder="Caută o echipă din cele cinci ligi"
            aria-label="Numele echipei"
            aria-controls="search-results"
            aria-activedescendant={shown[chosen] ? `found-${chosen}` : undefined}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setChosen((index) => Math.min(index + 1, shown.length - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setChosen((index) => Math.max(index - 1, 0));
              } else if (event.key === "Enter") {
                event.preventDefault();
                open(shown[chosen]);
              }
            }}
          />
          <kbd>Esc</kbd>
        </label>
        <ul id="search-results" className="search-results" role="listbox" aria-label="Echipe găsite">
          {shown.map((item, index) => (
            <li
              key={`${item.code}-${item.team}`}
              id={`found-${index}`}
              role="option"
              aria-selected={index === chosen}
              className={index === chosen ? "chosen" : undefined}
              onMouseEnter={() => setChosen(index)}
              onMouseDown={(event) => {
                event.preventDefault();
                open(item);
              }}
            >
              <Crest team={item.team} size={28} />
              <span className="search-team">
                {item.team}
                {FULL_NAMES[item.team] && <small>{FULL_NAMES[item.team].split(" ").slice(0, 3).join(" ")}</small>}
              </span>
              <span className="search-league">
                <Flag code={item.code} size={16} />
                {item.league}
              </span>
            </li>
          ))}
          {teams.length > 0 && shown.length === 0 && <li className="search-empty">Nicio echipă cu acest nume.</li>}
          {teams.length === 0 && <li className="search-empty">Se încarcă echipele…</li>}
        </ul>
        <p className="caption search-hint">
          <kbd>↑</kbd> <kbd>↓</kbd> alegi · <kbd>Enter</kbd> deschizi pagina echipei
        </p>
      </div>
    </Modal>
  );
}
