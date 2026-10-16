// The window of the web interface (Phase 22): the side bar on the left (layout A), the screen on
// the right. The chosen league's colours are set on the whole page; the predictions of every league
// are prepared by the server, and the screens follow as each league becomes ready.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { api } from "./api";
import { OtherMatch } from "./components/OtherMatch";
import { type ScreenName, SCREENS, Sidebar } from "./components/Sidebar";
import { MatchPage } from "./screens/MatchPage";
import { Matches } from "./screens/Matches";
import { applyTheme } from "./theme";
import type { Forecast, League, MatchKey, Preferences } from "./types";

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

  const chooseLeague = useCallback(
    (code: string) => {
      setLeague(code);
      api.setPreferences({ competition: code, favourite: preferences?.favourite ?? null }).then(setPreferences);
    },
    [preferences],
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

  const current = leagues.find((item) => item.code === league);
  const about = SCREENS.find((item) => item.name === screen);
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
              favourite={preferences?.favourite?.team ?? null}
              onBack={() => setMatch(null)}
              onTeam={() => undefined}
              onOther={() => setOtherMatch(true)}
            />
          )}
          <div className="screen-page" hidden={match !== null}>
            <div className="page-head">
              <div>
                <h1>{about?.title}</h1>
                <p>{about?.description}</p>
              </div>
              {screen === "matches" && (
                <button className="button" onClick={() => setOtherMatch(true)}>
                  Alt meci…
                </button>
              )}
            </div>
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
          </div>
        </div>
      </main>
      {otherMatch && current && (
        <OtherMatch leagues={leagues} league={current} onClose={() => setOtherMatch(false)} onOpen={showMatch} />
      )}
    </div>
  );
}
