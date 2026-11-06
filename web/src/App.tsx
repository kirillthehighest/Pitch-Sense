// The window of the web interface (Phase 22): the side bar on the left (layout A), the screen on
// the right. The chosen league's colours are set on the whole page; the predictions of every league
// are prepared by the server, and the screens follow as each league becomes ready.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { api, askUntilAnswered } from "./api";
import { FavouriteDialog } from "./components/FavouriteDialog";
import { CrossIcon, SimulateIcon } from "./components/Icons";
import { OtherMatch } from "./components/OtherMatch";
import { Problem } from "./components/Problem";
import { ScreenHead } from "./components/ScreenHead";
import { ShortcutsDialog, usePageKeys } from "./components/Shortcuts";
import { TeamSearch } from "./components/TeamSearch";
import { type ScreenName, SCREENS, Sidebar, updatedText } from "./components/Sidebar";
import { Analysis } from "./screens/Analysis";
import { MatchPage } from "./screens/MatchPage";
import { Matches } from "./screens/Matches";
import { Predictions } from "./screens/Predictions";
import { Standings } from "./screens/Standings";
import { Team } from "./screens/Team";
import { reveal } from "./reveal";
import { applyTheme } from "./theme";
import type { Favourite, Forecast, League, MatchKey, Preferences } from "./types";

const COMPACT_WIDTH = 1200;
const RETRY_MS = 1000; // the first questions, asked again while the server starts
const BUSY_POLL_MS = 1500; // the server's state while it prepares or updates
const IDLE_POLL_MS = 30000; // and otherwise: the season in progress is updated on its own
const FAILURES_SHOWN = 3; // unanswered for about three seconds: say so, and keep asking
const STALE_HOURS = 48; // older data is said on Meciuri: results after it may be missing

/** The data was downloaded more than ``STALE_HOURS`` ago (``now`` in milliseconds). */
export function isStale(updatedAt: string | null, now: number = Date.now()): boolean {
  if (!updatedAt) return false;
  return now - new Date(updatedAt).getTime() > STALE_HOURS * 3600 * 1000;
}

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
  const [favouriteDialog, setFavouriteDialog] = useState(false);
  const [updating, setUpdating] = useState(false); // the user's update
  const [serverUpdating, setServerUpdating] = useState(false); // any update, the automatic one too
  const seenVersion = useRef<number | null>(null); // the server's data the screens show
  const [notice, setNotice] = useState<{ text: string; problem: boolean; detail?: string } | null>(null);
  const [search, setSearch] = useState(false);
  const [shortcuts, setShortcuts] = useState(false);
  const [generation, setGeneration] = useState(0); // a new one after each update of the data
  const scroller = useRef<HTMLElement>(null);
  const screenScroll = useRef(0); // where the screen was when a match opened over it

  // The leagues and the user's choices, asked again until the server answers: a server that is
  // still starting is not an error, one silent for a few seconds is shown (and the message goes
  // when it answers)
  useEffect(() => {
    let live = true;
    askUntilAnswered(
      () => Promise.all([api.leagues(), api.preferences()]),
      (message) => setError(message),
      () => !live,
      RETRY_MS,
      FAILURES_SHOWN,
    ).then((answer) => {
      if (!live || !answer) return;
      const [found, chosen] = answer;
      setError(null);
      setLeagues(found);
      setPreferences(chosen);
      const first = found.find((item) => item.code === chosen.competition)?.code ?? found[0]?.code;
      if (first) setLeague(first);
    });
    return () => {
      live = false;
    };
  }, []);

  // The server's state, asked all along: which leagues are ready (the screens re-read when it
  // changes), whether an update runs, and the version of its data. When an update (the user's or
  // the automatic one) replaces a league's data, the screens read everything again.
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const status = await api.status();
        if (!live) return;
        const key = Object.entries(status.prepared).filter(([, done]) => done).map(([code]) => code).join(",");
        setReady(`${generation}|${key}`);
        setServerUpdating(status.updating);
        if (seenVersion.current !== null && status.version !== seenVersion.current) {
          seenVersion.current = status.version;
          setNotice((current) => current ?? { text: "Predicțiile au fost actualizate cu datele noi.", problem: false });
          setGeneration((value) => value + 1); // the screens re-read; this effect starts again
          return;
        }
        seenVersion.current = status.version;
        const busy = status.updating || status.preparing !== null || Object.values(status.prepared).some((done) => !done);
        timer = setTimeout(poll, busy ? BUSY_POLL_MS : IDLE_POLL_MS);
      } catch {
        if (live) timer = setTimeout(poll, BUSY_POLL_MS);
      }
    };
    poll();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [generation]);

  useEffect(() => {
    if (!notice) return;
    const hide = setTimeout(() => setNotice(null), 15000);
    return () => clearTimeout(hide);
  }, [notice]);

  const update = useCallback(() => {
    setUpdating(true);
    setNotice(null);
    api
      .update()
      .then((answer) => {
        setNotice({ text: `Date actualizate. ${answer.summary}`, problem: false });
        setGeneration((value) => value + 1);
      })
      .catch((reason: Error) =>
        setNotice({
          text: "Datele nu au putut fi actualizate; au rămas cele de până acum. Verificați conexiunea la internet și încercați din nou.",
          problem: true,
          detail: reason.message,
        }),
      )
      .finally(() => setUpdating(false));
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
      if (code !== league) {
        // the page in the new league's colours, uncovered by the wave
        reveal(() => {
          applyTheme(code);
          flushSync(() => setLeague(code));
        });
      }
      api.setPreferences({ competition: code, favourite: preferences?.favourite ?? null }).then(setPreferences);
    },
    [league, preferences],
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

  // The page's keys: 1–5 choose a league, / finds a team, S simulates a match, ? lists them all
  usePageKeys((key) => {
    const index = Number(key) - 1;
    if (Number.isInteger(index) && index >= 0 && index < leagues.length) chooseLeague(leagues[index].code);
    else if (key === "/") setSearch(true);
    else if (key === "s" || key === "S") setOtherMatch(true);
    else if (key === "?") setShortcuts(true);
  });

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
        onFavourite={() => setFavouriteDialog(true)}
        onUpdate={update}
        updating={updating || serverUpdating}
        updatedAt={current?.updated_at ?? null}
        compact={compact}
        onSimulate={() => setOtherMatch(true)}
        onSearch={() => setSearch(true)}
        onShortcuts={() => setShortcuts(true)}
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
                <button className="button" onClick={() => setOtherMatch(true)} aria-keyshortcuts="S" title="Tasta S">
                  <SimulateIcon />
                  Simulează un meci
                </button>
              </div>
            ) : (
              current &&
              about &&
              (screen === "predictions" || screen === "analysis") && (
                <ScreenHead
                  league={current}
                  title={about.title}
                  description={about.description}
                  variant={screen === "analysis" ? "lab" : "league"}
                />
              )
            )}
            {error && (
              <Problem detail={error}>
                Serverul aplicației nu răspunde încă. Dacă mesajul nu dispare în câteva secunde, închide și redeschide
                PitchSense.
              </Problem>
            )}
            {current && screen === "matches" && isStale(current.updated_at) && !serverUpdating && (
              <div className="stale-note" role="status">
                <p>
                  Datele sezonului în desfășurare sunt din {updatedText(current.updated_at as string)}. Meciurile jucate de
                  atunci apar „Fără rezultat” până la actualizare.
                </p>
                <button className="button" onClick={update} disabled={updating}>
                  Actualizează acum
                </button>
              </div>
            )}
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
                onPredictions={() => chooseScreen("predictions")}
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
            {current && screen === "standings" && about && (
              <Standings
                title={about.title}
                description={about.description}
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
      {favouriteDialog && current && (
        <FavouriteDialog
          leagues={leagues}
          league={current}
          favourite={preferences?.favourite ?? null}
          onClose={() => setFavouriteDialog(false)}
          onChoose={(chosen) => {
            chooseFavourite(chosen);
            setFavouriteDialog(false);
          }}
          onOpenTeam={(chosen) => {
            setFavouriteDialog(false);
            const chosenLeague = leagues.find((item) => item.code === chosen.competition);
            if (chosenLeague) openTeam(chosen.competition, chosen.team, chosenLeague.seasons[chosenLeague.seasons.length - 1]);
          }}
        />
      )}
      {notice && (
        <div className={`notice${notice.problem ? " problem" : ""}`} role="status">
          <div>
            <span>{notice.text}</span>
            {notice.detail && (
              <details>
                <summary>Detalii tehnice</summary>
                <code>{notice.detail}</code>
              </details>
            )}
          </div>
          <button className="round small" onClick={() => setNotice(null)} aria-label="Închide">
            <CrossIcon size={12} />
          </button>
        </div>
      )}
      {otherMatch && current && (
        <OtherMatch leagues={leagues} league={current} onClose={() => setOtherMatch(false)} onOpen={showMatch} />
      )}
      {search && (
        <TeamSearch
          leagues={leagues}
          onClose={() => setSearch(false)}
          onOpen={(code, chosen, chosenSeason) => {
            setSearch(false);
            openTeam(code, chosen, chosenSeason);
          }}
        />
      )}
      {shortcuts && <ShortcutsDialog onClose={() => setShortcuts(false)} />}
    </div>
  );
}
