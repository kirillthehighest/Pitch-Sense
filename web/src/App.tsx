// The window of the web interface (Phase 22): the side bar on the left (layout A), the screen on
// the right. The chosen league's colours are set on the whole page; the predictions of every league
// are prepared by the server, and the screens follow as each league becomes ready.
import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { type ScreenName, SCREENS, Sidebar } from "./components/Sidebar";
import { Matches } from "./screens/Matches";
import { applyTheme } from "./theme";
import type { Forecast, League, Preferences } from "./types";

const COMPACT_WIDTH = 1200;

export default function App() {
  const [leagues, setLeagues] = useState<League[]>([]);
  const [league, setLeague] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [screen, setScreen] = useState<ScreenName>("matches");
  const [ready, setReady] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [compact, setCompact] = useState(window.innerWidth < COMPACT_WIDTH);

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

  const openMatch = useCallback((forecast: Forecast) => {
    // the match page comes with the next screens
    console.info("open", forecast.home_team, forecast.away_team);
  }, []);

  const current = leagues.find((item) => item.code === league);
  return (
    <div className={`app${compact ? " compact" : ""}`}>
      <Sidebar
        screen={screen}
        onScreen={setScreen}
        leagues={leagues}
        league={league ?? ""}
        onLeague={chooseLeague}
        preferences={preferences}
        onFavourite={() => undefined}
        onUpdate={() => undefined}
        updating={false}
      />
      <main className="screen">
        <div className="screen-inner">
          <div className="page-head">
            <h1>{SCREENS.find((item) => item.name === screen)?.title}</h1>
            <p>Meciurile fiecărei zile, cu predicțiile modelelor. Fiecare predicție folosește doar meciurile jucate înaintea ei.</p>
          </div>
          {error && <p className="caption">Serverul nu răspunde: {error}</p>}
          {current && screen === "matches" && (
            <Matches
              leagues={leagues}
              league={current}
              preferences={preferences}
              ready={ready}
              onOpenMatch={openMatch}
              onStandings={(code) => {
                chooseLeague(code);
                setScreen("standings");
              }}
            />
          )}
        </div>
      </main>
    </div>
  );
}
