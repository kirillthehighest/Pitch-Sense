// The command field's dialog (key /): every club of the five leagues' latest seasons, found as you
// type by its short or full name (accents and case do not matter), and the match simulation.
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { teamName } from "../format";
import type { League } from "../types";
import { Crest } from "./Crest";
import { Flag } from "./Flag";
import { SearchIcon, SimulateIcon } from "./Icons";
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
  "Man United": "Manchester United Man Utd",
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
  const starts = (item: Found) => {
    if (plain(item.team).startsWith(wanted) || plain(teamName(item.team)).startsWith(wanted)) return 0;
    return names(item).split(" ").some((word) => word.startsWith(wanted)) ? 1 : 2;
  };
  return [...matching].sort((a, b) => starts(a) - starts(b) || a.team.localeCompare(b.team)).slice(0, limit);
}

interface Props {
  leagues: League[];
  current?: string | null; // the league on screen: its clubs come first
  favourite?: string | null; // "your team": first of all
  onClose: () => void;
  onOpen: (code: string, team: string, season: string) => void;
  onSimulate: (code: string | null, home: string | null) => void; // a match from scratch, or with this team at home
}

/** The command field's one dialog (Phase 26): find a club and open its page, or simulate a match,
 * from scratch (the first row) or with a found club at home (⇧ Enter, or its button). */
export function TeamSearch({ leagues, current = null, favourite = null, onClose, onOpen, onSimulate }: Props) {
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
    ).then((found) => {
      if (!live) return;
      const rank = (item: Found) => (item.team === favourite ? 0 : item.code === current ? 1 : 2);
      setTeams(found.flat().sort((a, b) => rank(a) - rank(b)));
    });
    return () => {
      live = false;
    };
  }, [leagues, current, favourite]);

  const shown = useMemo(() => searchTeams(teams, query, 7), [teams, query]);
  // typing a name points Enter at the first club found; an empty field, at the simulation
  useEffect(() => setChosen(query.trim() && shown.length ? 1 : 0), [query, shown.length]);
  const rows = shown.length + 1; // the simulation first, then the clubs

  const choose = (index: number, simulate: boolean) => {
    if (index === 0) return onSimulate(null, null);
    const item = shown[index - 1];
    if (!item) return;
    if (simulate) onSimulate(item.code, item.team);
    else onOpen(item.code, item.team, item.season);
  };

  return (
    <Modal label="Caută o echipă sau simulează un meci" onClose={onClose}>
      <div className="dialog card search-dialog">
        <label className="search-field">
          <SearchIcon />
          <input
            autoFocus
            value={query}
            placeholder="Caută o echipă sau simulează un meci"
            aria-label="Numele echipei"
            aria-controls="search-results"
            aria-activedescendant={`found-${chosen}`}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setChosen((index) => Math.min(index + 1, rows - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setChosen((index) => Math.max(index - 1, 0));
              } else if (event.key === "Enter") {
                event.preventDefault();
                choose(chosen, event.shiftKey);
              }
            }}
          />
          <kbd>Esc</kbd>
        </label>
        <ul id="search-results" className="search-results" role="listbox" aria-label="Acțiuni și echipe">
          <li
            id="found-0"
            role="option"
            aria-selected={chosen === 0}
            className={`search-action${chosen === 0 ? " chosen" : ""}`}
            onMouseEnter={() => setChosen(0)}
            onMouseDown={(event) => {
              event.preventDefault();
              choose(0, true);
            }}
          >
            <span className="search-action-icon">
              <SimulateIcon />
            </span>
            <span className="search-team">
              Simulează un meci
              <small>Oricare două echipe ale unui sezon, la o zi aleasă</small>
            </span>
            <kbd>S</kbd>
          </li>
          {shown.map((item, index) => (
            <li
              key={`${item.code}-${item.team}`}
              id={`found-${index + 1}`}
              role="option"
              aria-selected={index + 1 === chosen}
              className={index + 1 === chosen ? "chosen" : undefined}
              onMouseEnter={() => setChosen(index + 1)}
              onMouseDown={(event) => {
                event.preventDefault();
                choose(index + 1, false);
              }}
            >
              <Crest team={item.team} size={28} />
              <span className="search-team">{teamName(item.team)}</span>
              <span className="search-league">
                <Flag code={item.code} size={16} />
                {item.league}
              </span>
              <button
                type="button"
                className="search-simulate"
                tabIndex={-1}
                aria-label={`Simulează un meci cu ${teamName(item.team)} gazdă`}
                onMouseDown={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  choose(index + 1, true);
                }}
              >
                Simulează
              </button>
            </li>
          ))}
          {teams.length > 0 && shown.length === 0 && <li className="search-empty">Nicio echipă cu acest nume.</li>}
          {teams.length === 0 && <li className="search-empty">Se încarcă echipele…</li>}
        </ul>
        <p className="caption search-hint">
          <kbd>↑</kbd> <kbd>↓</kbd> alegi · <kbd>Enter</kbd> deschizi · <kbd>⇧</kbd> <kbd>Enter</kbd> simulezi cu echipa gazdă
        </p>
      </div>
    </Modal>
  );
}
