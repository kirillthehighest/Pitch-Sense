// The side bar (layout A, chosen by the team): the logo, the screens, the leagues, the tools
// (Phase 25: simulate a match, find a team), and at the bottom "your team", the update of the
// season in progress and the sources. In the narrow rail every item keeps its name as a tooltip.
import type { ReactNode } from "react";
import { teamName } from "../format";
import type { League, Preferences } from "../types";
import { Crest } from "./Crest";
import { Flag } from "./Flag";
import {
  AnalysisIcon, MatchesIcon, PredictionsIcon, RefreshIcon, SearchIcon, SimulateIcon, StandingsIcon, TeamIcon,
} from "./Icons";
import { Lockup } from "./Logo";

export type ScreenName = "matches" | "standings" | "team" | "predictions" | "analysis";

export const SCREENS: { name: ScreenName; title: string; description: string; icon: () => ReactNode }[] = [
  {
    name: "matches",
    title: "Meciuri",
    description: "Meciurile fiecărei zile, cu predicțiile modelelor. Fiecare predicție folosește doar meciurile jucate înaintea ei.",
    icon: MatchesIcon,
  },
  {
    name: "standings",
    title: "Clasament",
    description: "Clasamentul oricărui sezon, la final sau înaintea oricărei zile, cu forma fiecărei echipe.",
    icon: StandingsIcon,
  },
  {
    name: "team",
    title: "Echipe",
    description: "Sezonul unei echipe: rezultate, formă, șuturi, ratingul Elo și profilul ei.",
    icon: TeamIcon,
  },
  {
    name: "predictions",
    title: "Predicții",
    description: "Ce au prezis modelele și ce s-a întâmplat: meciuri nimerite, ratate și surprize.",
    icon: PredictionsIcon,
  },
  {
    name: "analysis",
    title: "Analiză",
    description: "Cum lucrează modelele, cât de bine prezic și cum se compară ligile.",
    icon: AnalysisIcon,
  },
];

interface Props {
  screen: ScreenName;
  onScreen: (screen: ScreenName) => void;
  leagues: League[];
  league: string;
  onLeague: (code: string) => void;
  preferences: Preferences | null;
  onFavourite: () => void;
  onUpdate: () => void;
  updating: boolean;
  updatedAt: string | null; // when the season in progress was downloaded (UTC, ISO)
  compact: boolean; // the narrow rail: names only as tooltips
  onSimulate: () => void;
  onSearch: () => void;
  onShortcuts: () => void;
}

/** 15.10.2026, 16:01 in the computer's time zone, as docs/brand.md writes dates. */
export function updatedText(iso: string): string {
  const moment = new Date(iso);
  const two = (value: number) => String(value).padStart(2, "0");
  return `${two(moment.getDate())}.${two(moment.getMonth() + 1)}.${moment.getFullYear()}, ${two(moment.getHours())}:${two(moment.getMinutes())}`;
}

export function Sidebar(props: Props) {
  const favourite = props.preferences?.favourite;
  const tip = (text: string) => (props.compact ? text : undefined);
  return (
    <aside className="sidebar">
      <Lockup />
      <nav aria-label="Ecrane">
        <div className="sidebar-label">Meniu</div>
        {SCREENS.map(({ name, title, icon: Icon }) => (
          <button
            key={name}
            className={`side-item${props.screen === name ? " chosen" : ""}`}
            onClick={() => props.onScreen(name)}
            aria-current={props.screen === name ? "page" : undefined}
            aria-label={props.compact ? title : undefined}
            title={tip(title)}
          >
            <Icon />
            <span className="side-text">{title}</span>
          </button>
        ))}
      </nav>
      <nav aria-label="Competiții">
        <div className="sidebar-label">Competiții</div>
        {props.leagues.map((league) => (
          <button
            key={league.code}
            className={`side-item league-item${props.league === league.code ? " chosen" : ""}`}
            onClick={() => props.onLeague(league.code)}
            aria-current={props.league === league.code ? "true" : undefined}
            aria-label={props.compact ? `${league.name}, ${league.country}` : undefined}
            title={tip(`${league.name} · ${league.country}`)}
          >
            <Flag code={league.code} size={26} />
            <span className="side-text">
              {league.name}
              <br />
              <span className="country">{league.country}</span>
            </span>
          </button>
        ))}
      </nav>
      <div className="sidebar-label">Unelte</div>
      <button className="side-item" onClick={props.onSimulate} aria-label={props.compact ? "Simulează un meci" : undefined} title={tip("Simulează un meci")}>
        <SimulateIcon />
        <span className="side-text">Simulează un meci</span>
      </button>
      <button
        className="side-item"
        onClick={props.onSearch}
        aria-label={props.compact ? "Caută o echipă" : undefined}
        aria-keyshortcuts="/"
        title={props.compact ? "Caută o echipă (/)" : "Tasta /"}
      >
        <SearchIcon />
        <span className="side-text">Caută o echipă</span>
        <kbd className="side-text">/</kbd>
      </button>
      <div className="spacer" />
      <button
        className="side-item"
        onClick={props.onFavourite}
        aria-label={favourite ? `Echipa ta: ${teamName(favourite.team)}` : "Alege echipa ta"}
        title={tip(favourite ? `Echipa ta: ${teamName(favourite.team)}` : "Alege echipa ta")}
      >
        {favourite ? <Crest team={favourite.team} size={22} ring /> : <TeamIcon />}
        <span className="side-text">{favourite ? teamName(favourite.team) : "Alege echipa ta"}</span>
      </button>
      <button
        className="side-item"
        onClick={props.onUpdate}
        disabled={props.updating}
        aria-label={props.compact ? (props.updating ? "Se actualizează…" : "Actualizează datele") : undefined}
        title={tip(props.updating ? "Se actualizează…" : "Actualizează datele")}
      >
        <span className={props.updating ? "spinning" : undefined}>
          <RefreshIcon />
        </span>
        <span className="side-text">{props.updating ? "Se actualizează…" : "Actualizează datele"}</span>
      </button>
      <div className="sidebar-note">
        Rezultate: Football-Data.co.uk
        <br />
        Calendar: openfootball (CC0)
        <br />
        {props.updatedAt ? `Actualizat: ${updatedText(props.updatedAt)}` : "Sezonul curent: —"}
        <br />
        UTM · APA · TI-251
        <br />
        <button className="link note-link" onClick={props.onShortcuts} aria-keyshortcuts="?">
          Scurtăturile tastaturii <kbd>?</kbd>
        </button>
      </div>
    </aside>
  );
}
