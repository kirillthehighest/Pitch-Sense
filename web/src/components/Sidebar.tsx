// The side bar (layout A, chosen by the team): the logo, the screens, the leagues, and at the
// bottom "your team", the update of the season in progress and the sources.
import type { ReactNode } from "react";
import type { League, Preferences } from "../types";
import { Crest } from "./Crest";
import { Flag } from "./Flag";
import {
  AnalysisIcon, MatchesIcon, PredictionsIcon, RefreshIcon, StandingsIcon, TeamIcon,
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
}

export function Sidebar(props: Props) {
  const favourite = props.preferences?.favourite;
  return (
    <aside className="sidebar">
      <Lockup />
      <div className="sidebar-label">Meniu</div>
      {SCREENS.map(({ name, title, icon: Icon }) => (
        <button
          key={name}
          className={`side-item${props.screen === name ? " chosen" : ""}`}
          onClick={() => props.onScreen(name)}
          title={title}
        >
          <Icon />
          <span className="side-text">{title}</span>
        </button>
      ))}
      <div className="sidebar-label">Competiții</div>
      {props.leagues.map((league) => (
        <button
          key={league.code}
          className={`side-item league-item${props.league === league.code ? " chosen" : ""}`}
          onClick={() => props.onLeague(league.code)}
          title={`${league.name} · ${league.country}`}
        >
          <Flag code={league.code} size={26} />
          <span className="side-text">
            {league.name}
            <br />
            <span className="country">{league.country}</span>
          </span>
        </button>
      ))}
      <div className="spacer" />
      <button className="side-item" onClick={props.onFavourite} title="Echipa ta">
        {favourite ? <Crest team={favourite.team} size={22} ring /> : <TeamIcon />}
        <span className="side-text">{favourite ? favourite.team : "Alege echipa ta"}</span>
      </button>
      <button className="side-item" onClick={props.onUpdate} disabled={props.updating} title="Actualizează datele">
        <RefreshIcon />
        <span className="side-text">{props.updating ? "Se actualizează…" : "Actualizează datele"}</span>
      </button>
      <div className="sidebar-note">
        Rezultate: Football-Data.co.uk
        <br />
        Calendar: openfootball (CC0)
        <br />
        UTM · APA · TI-251
      </div>
    </aside>
  );
}
