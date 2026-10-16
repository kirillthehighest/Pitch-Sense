// The window of the web interface (Phase 22): the side bar on the left (layout A), the screen on
// the right. The chosen league's colours are set on the whole page; the predictions of every league
// are prepared by the server, and the screens follow as each league becomes ready.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { api } from "./api";
import { OtherMatch } from "./components/OtherMatch";
import { ScreenHead } from "./components/ScreenHead";
import { type ScreenName, SCREENS, Sidebar } from "./components/Sidebar";
import { Analysis } from "./screens/Analysis";
import { MatchPage } from "./screens/MatchPage";
import { Matches } from "./screens/Matches";
import { Predictions } from "./screens/Predictions";
import { Standings } from "./screens/Standings";
import { Team } from "./screens/Team";
import { applyTheme } from "./theme";
import type { Favourite, Forecast, League, MatchKey, Preferences } from "./types";

const COMPACT_WIDTH = 1200;

export default function App() {
  const [leagues, setLeagues] = useState<League[]>([]);
  const [league, setLeague] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [screen, setScreen] = useState<ScreenName>("matches");
  const [ready, setReady] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [compact, setCompact] = useState(window.innerWidth < COMPACT_WIDTH);
  const [match, setMatch] = useState<MatchKey | null>(null);
  const [otherMatch, setOtherMatch] = useState(false);
  const [seasons, setSeasons] = useState<Record<string, string>>({}); // the season shown, by league
  const [team, setTeam] = useState<{ code: string; team: string; season: string } | null>(null);
  const scroller = useRef<HTMLElement>(null);
  const screenScroll = useRef(0); // where the screen was when a match opened over it

  useEffect(() => {
    Promise.all([api.leagues(), api.preferences()])
      .then(([found, chosen]) => {
        setLeagues(found);
        setPreferences(chosen);
        const first = found.find((item) => item.code === chosen.competition)?.code ?? found[0]?.code;
        if (first) setLeague(first);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  // Which leagues are ready, until all are: the screens re-read when it changes
  useEffect(() => {
    let live = true;
    const poll = async () => {
      try {
        const status = await api.status();
        if (!live) return;
        const key = Object.entries(status.prepared).filter(([, done]) => done).map(([code]) => code).join(",");
        setReady(key);
        if (Object.values(status.prepared).some((done) => !done)) setTimeout(poll, 1500);
      } catch {
        if (live) setTimeout(poll, 1500);
      }
    };
    poll();
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    const resize = () => setCompact(window.innerWidth < COMPACT_WIDTH);
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  useEffect(() => {
    if (league) applyTheme(league);
  }, [league]);

  // A league's state (its predictions ready) as the server prepares them
  useEffect(() => {
    if (ready) api.leagues().then(setLeagues);
  }, [ready]);

  const chooseLeague = useCallback(
    (code: string) => {
      setLeague(code);
      api.setPreferences({ competition: code, favourite: preferences?.favourite ?? null }).then(setPreferences);
    },
    [preferences],
  );

  const chooseFavourite = useCallback(
    (favourite: Favourite | null) => {
      api.setPreferences({ competition: league, favourite }).then(setPreferences);
    },
    [league],
  );

  // A match opens over the screen, which stays as it was (its day, its scroll) for "Înapoi"
  const showMatch = useCallback((key: MatchKey) => {
    setMatch((open) => {
      if (open === null) screenScroll.current = scroller.current?.scrollTop ?? 0;
      return key;
    });
    setOtherMatch(false);
  }, []);

  const openMatch = useCallback(
    (forecast: Forecast) =>
      showMatch({
        code: forecast.competition,
        season: forecast.season,
        day: forecast.date,
        home: forecast.home_team,
        away: forecast.away_team,
      }),
    [showMatch],
  );

  useLayoutEffect(() => {
    if (scroller.current) scroller.current.scrollTop = match ? 0 : screenScroll.current;
  }, [match]);

  const chooseScreen = useCallback((name: ScreenName) => {
    setMatch(null);
    setScreen(name);
  }, []);

  const openTeam = useCallback(
    (code: string, chosen: string, season: string) => {
      if (code !== league) chooseLeague(code);
      setSeasons((shown) => ({ ...shown, [code]: season }));
      setTeam({ code, team: chosen, season });
      setMatch(null);
      setScreen("team");
    },
    [league, chooseLeague],
  );

  const current = leagues.find((item) => item.code === league);
  const about = SCREENS.find((item) => item.name === screen);
  const season = current ? (seasons[current.code] ?? current.seasons[current.seasons.length - 1]) : "";
  const favourite = preferences?.favourite?.team ?? null;
  return (
    <div className={`app${compact ? " compact" : ""}`}>
      <Sidebar
        screen={screen}
        onScreen={chooseScreen}
        leagues={leagues}
        league={league ?? ""}
        onLeague={chooseLeague}
        preferences={preferences}
        onFavourite={() => undefined}
        onUpdate={() => undefined}
        updating={false}
      />
      <main className="screen" ref={scroller}>
        <div className="screen-inner">
          {match && current && (
            <MatchPage
              matchKey={match}
              leagues={leagues}
              favourite={favourite}
              onBack={() => setMatch(null)}
              onTeam={openTeam}
              onOther={() => setOtherMatch(true)}
            />
          )}
          <div className="screen-page" hidden={match !== null}>
            {screen === "matches" ? (
              <div className="page-head">
                <div>
                  <h1>{about?.title}</h1>
                  <p>{about?.description}</p>
                </div>
                <button className="button" onClick={() => setOtherMatch(true)}>
                  Alt meci…
                </button>
              </div>
            ) : (
              current && about && <ScreenHead league={current} title={about.title} description={about.description} />
            )}
            {error && <p className="problem">Serverul nu răspunde: {error}</p>}
            {current && screen === "matches" && (
              <Matches
                leagues={leagues}
                league={current}
                preferences={preferences}
                ready={ready}
                onOpenMatch={openMatch}
                onStandings={(code) => {
                  chooseLeague(code);
                  chooseScreen("standings");
                }}
              />
            )}
            {current && screen === "team" && (
              <Team
                league={current}
                season={season}
                team={team?.code === current.code ? team.team : null}
                favourite={preferences?.favourite ?? null}
                ready={ready}
                onChoice={(chosen, chosenSeason) => {
                  setSeasons((shown) => ({ ...shown, [current.code]: chosenSeason }));
                  setTeam(chosen ? { code: current.code, team: chosen, season: chosenSeason } : null);
                }}
                onOpenMatch={openMatch}
                onFavourite={chooseFavourite}
                onAnalysis={() => chooseScreen("analysis")}
              />
            )}
            {current && screen === "analysis" && (
              <Analysis league={current} leagues={leagues} ready={ready} onLeague={chooseLeague} />
            )}
            {current && screen === "predictions" && (
              <Predictions
                league={current}
                season={season}
                favourite={favourite}
                ready={ready}
                onSeason={(chosen) => setSeasons((shown) => ({ ...shown, [current.code]: chosen }))}
                onOpenMatch={openMatch}
              />
            )}
            {current && screen === "standings" && (
              <Standings
                league={current}
                season={season}
                favourite={favourite}
                onSeason={(chosen) => setSeasons((shown) => ({ ...shown, [current.code]: chosen }))}
                onTeam={openTeam}
              />
            )}
          </div>
        </div>
      </main>
      {otherMatch && current && (
        <OtherMatch leagues={leagues} league={current} onClose={() => setOtherMatch(false)} onOpen={showMatch} />
      )}
    </div>
  );
}
