// Meciuri: the matches of a day in every league, the chosen league first, with the match of the
// day on top; any day of any season can be chosen. On the right: your team and the table.
// Since Phase 25 every league's group and "your team" wear their own league's colours, the
// arrows move a day and M changes the model; since Phase 26 the model switch carries each model's
// record of the season.
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Crest } from "../components/Crest";
import { DayStrip } from "../components/DayStrip";
import { FeaturedMatch } from "../components/FeaturedMatch";
import { FormSquares } from "../components/FormSquares";
import { Flag } from "../components/Flag";
import { ChipLegend, ColumnsHead, likelyScore, MatchRow } from "../components/MatchRow";
import { usePageKeys } from "../components/Shortcuts";
import { SkeletonCard, SkeletonRows } from "../components/Skeleton";
import { ModelSwitch } from "../components/ModelSwitch";
import { capitalised, dayName, isoDay, parseDay, quantity, seasonText, shortDateText, teamName } from "../format";
import type { Day, Days, Forecast, League, Preferences, Standings } from "../types";
import { MODELS } from "../types";

interface Props {
  leagues: League[];
  league: League;
  preferences: Preferences | null;
  ready: string; // changes when a league's predictions become ready
  onOpenMatch: (forecast: Forecast) => void;
  onStandings: (code: string) => void;
}

function seasonStart(season: string): string {
  return `${season.slice(0, 4)}-07-01`;
}

/** The next model of the list, after the last the first: the M key. */
export function nextModel(model: string): string {
  const index = MODELS.indexOf(model as (typeof MODELS)[number]);
  return MODELS[(index + 1) % MODELS.length];
}

/** The day ``days`` after ``day`` (ISO). */
function shifted(day: string, days: number): string {
  const moved = parseDay(day);
  moved.setDate(moved.getDate() + days);
  return isoDay(moved);
}

export function Matches({ leagues, league, preferences, ready, onOpenMatch, onStandings }: Props) {
  const [days, setDays] = useState<Days | null>(null);
  const [day, setDay] = useState<string | null>(null);
  const [answer, setAnswer] = useState<Day | null>(null);
  const [model, setModel] = useState<string>(MODELS[0]);
  const [onlyLeague, setOnlyLeague] = useState(false);
  const favourite = preferences?.favourite?.team ?? null;

  useEffect(() => {
    api.days().then((found) => {
      setDays(found);
      setDay((current) => current ?? found.next_day);
    });
  }, [ready]);

  useEffect(() => {
    if (day) api.day(day, league.code).then(setAnswer);
  }, [day, league.code, ready]);

  const matchDays = useMemo(() => new Set(days?.days ?? []), [days]);
  const seasonOfDay = useMemo(() => {
    if (!day) return league.seasons[league.seasons.length - 1];
    return [...league.seasons].reverse().find((season) => seasonStart(season) <= day) ?? league.seasons[0];
  }, [day, league.seasons]);

  usePageKeys((key) => {
    if (!day) return false;
    if (key === "ArrowLeft") setDay(shifted(day, -1));
    else if (key === "ArrowRight") setDay(shifted(day, 1));
    else if (key === "m" || key === "M") setModel(nextModel);
    else if ((key === "t" || key === "T") && days) setDay(days.today);
    else return false;
    return true;
  });

  if (!days || !day) {
    return (
      <div className="matches-layout">
        <div className="matches-main">
          <SkeletonCard height={190} title={false} />
          <section className="card league-day">
            <SkeletonRows rows={5} label="Se pregătesc predicțiile…" />
          </section>
        </div>
        <aside className="matches-side">
          <SkeletonCard height={160} />
        </aside>
      </div>
    );
  }

  const groups = (answer?.leagues ?? []).filter((group) => !onlyLeague || group.code === league.code);
  const name = dayName(parseDay(day), parseDay(days.today));
  const dateName = shortDateText(parseDay(day));
  const featuredLeague = leagues.find((item) => item.code === answer?.featured?.competition);

  return (
    <div className="matches-layout">
      <div className="matches-main">
        {answer?.featured && featuredLeague && (
          <FeaturedMatch
            forecast={answer.featured}
            day={day}
            league={featuredLeague}
            model={model}
            favourite={favourite}
            onOpen={onOpenMatch}
          />
        )}
        <DayStrip day={day} today={days.today} matchDays={matchDays} onDay={setDay} />
        <div className="controls">
          <h2 className="visually-hidden">{name === dateName ? capitalised(dateName) : `${name} · ${dateName}`}</h2>
          <div className="control-row">
            <button className={`pill${onlyLeague ? "" : " chosen"}`} aria-pressed={!(onlyLeague)} onClick={() => setOnlyLeague(false)}>
              Toate ligile
            </button>
            <button className={`pill${onlyLeague ? " chosen" : ""}`} aria-pressed={onlyLeague} onClick={() => setOnlyLeague(true)}>
              Doar {league.name}
            </button>
            <span className="grow" />
            <label className="caption" htmlFor="matches-season">
              Sezon
            </label>
            <select
              id="matches-season"
              value={seasonOfDay}
              onChange={(event) => {
                const start = seasonStart(event.target.value);
                const first = days.days.find((found) => found >= start);
                if (first) setDay(first);
              }}
            >
              {[...league.seasons].reverse().map((season) => (
                <option key={season} value={season}>
                  {seasonText(season)}
                </option>
              ))}
            </select>
            <ModelSwitch league={league} model={model} ready={ready} onModel={setModel} />
          </div>
          <details className="legend-toggle">
            <summary>Ce înseamnă semnele din listă</summary>
            <ChipLegend />
          </details>
        </div>
        {answer && groups.length === 0 && (
          <EmptyDay day={day} days={days.days} onlyLeague={onlyLeague ? league.name : null} onDay={setDay} />
        )}
        {!answer && (
          <section className="card league-day">
            <SkeletonRows rows={4} />
          </section>
        )}
        {groups.map((group, index) => (
          <section key={group.code} className="card league-day">
            <header>
              <Flag code={group.code} size={34} />
              <div>
                <h3>{group.name}</h3>
                <div className="caption">
                  {group.country}
                  {group.prepared ? ` · ${quantity(group.forecasts.length, "meci", "meciuri")}` : ""}
                </div>
              </div>
              <button className="link" onClick={() => onStandings(group.code)}>
                Clasament ›
              </button>
            </header>
            {group.prepared ? (
              <>
                {index === 0 && (
                  <ColumnsHead likely={group.forecasts.some((forecast) => forecast.result === null && likelyScore(forecast) !== null)} />
                )}
                <div className="match-list">
                  {group.forecasts.map((forecast) => (
                    <MatchRow
                      key={`${forecast.home_team}-${forecast.away_team}`}
                      forecast={forecast}
                      model={model}
                      favourite={favourite}
                      onOpen={onOpenMatch}
                    />
                  ))}
                </div>
              </>
            ) : (
              <SkeletonRows rows={Math.min(group.forecasts.length || 3, 4)} label="Se pregătesc predicțiile…" />
            )}
          </section>
        ))}
      </div>
      <aside className="matches-side">
        <FavouriteCard preferences={preferences} leagues={leagues} model={model} ready={ready} onOpenMatch={onOpenMatch} />
        <MiniTable league={league} favourite={favourite} onStandings={onStandings} />
      </aside>
    </div>
  );
}

function FavouriteCard({
  preferences, leagues, model, ready, onOpenMatch,
}: {
  preferences: Preferences | null;
  leagues: League[];
  model: string;
  ready: string;
  onOpenMatch: (forecast: Forecast) => void;
}) {
  const favourite = preferences?.favourite ?? null;
  const league = leagues.find((item) => item.code === favourite?.competition);
  const [matches, setMatches] = useState<Forecast[]>([]);
  useEffect(() => {
    if (favourite) api.teamMatches(favourite.competition, favourite.team).then(setMatches);
  }, [favourite?.competition, favourite?.team, ready]);
  if (!favourite || !league) {
    return (
      <section className="card">
        <h2>Echipa ta</h2>
        <p className="caption">Alege echipa pe care o urmărești din bara din stânga: meciurile ei vor fi evidențiate.</p>
      </section>
    );
  }
  const played = matches.filter((match) => match.result !== null);
  const next = matches.find((match) => match.result === null);
  const shown = [next, played[played.length - 1]].filter(Boolean) as Forecast[];
  const form = played.slice(-5).map((match) => {
    const home = match.home_team === favourite.team;
    if (match.result === "D") return "D";
    return (match.result === "H") === home ? "W" : "L";
  });
  return (
    <section className="card favourite-card">
      <h2>Echipa ta</h2>
      <div className="favourite-identity">
        <Crest team={favourite.team} size={56} ring />
        <div>
          <strong>{teamName(favourite.team)}</strong>
          <div className="caption">
            {league.name} · {seasonText(league.seasons[league.seasons.length - 1])}
          </div>
        </div>
      </div>
      <FormSquares results={form} />
      <div>
        <ColumnsHead stacked />
        <div className="match-list">
          {shown.map((forecast) => (
            <MatchRow key={forecast.date} forecast={forecast} model={model} favourite={favourite.team} stacked showDate onOpen={onOpenMatch} />
          ))}
        </div>
      </div>
    </section>
  );
}

function MiniTable({ league, favourite, onStandings }: { league: League; favourite: string | null; onStandings: (code: string) => void }) {
  const [table, setTable] = useState<Standings | null>(null);
  useEffect(() => {
    api.standings(league.code).then(setTable);
  }, [league.code]);
  return (
    <section className="card mini-table">
      <h2>
        {league.name} {table ? seasonText(table.season) : ""}
      </h2>
      {table?.rows.slice(0, 6).map((row) => (
        <div key={row.team} className={`mini-row${row.team === favourite ? " favourite" : ""}`}>
          <span className="position">{row.position}</span>
          <Crest team={row.team} size={22} />
          <span className="name">{teamName(row.team)}</span>
          <span className="caption">{row.record.played}</span>
          <strong>{row.record.points}</strong>
        </div>
      ))}
      <button className="link" onClick={() => onStandings(league.code)}>
        Tot clasamentul ›
      </button>
    </section>
  );
}

/** A day without matches: says so, and offers the nearest day that has some. */
function EmptyDay({
  day, days, onlyLeague, onDay,
}: { day: string; days: string[]; onlyLeague: string | null; onDay: (day: string) => void }) {
  const next = days.find((found) => found > day);
  const previous = [...days].reverse().find((found) => found < day);
  return (
    <section className="card empty-state">
      <h3>{onlyLeague ? `${onlyLeague} nu joacă în această zi` : "Nu sunt meciuri în această zi"}</h3>
      <p className="caption">Alege altă zi din bara de mai sus sau sari direct la cea mai apropiată zi cu meciuri.</p>
      <div className="empty-actions">
        {previous && (
          <button className="button" onClick={() => onDay(previous)}>
            ‹ {capitalised(shortDateText(parseDay(previous)))}
          </button>
        )}
        {next && (
          <button className="button primary" onClick={() => onDay(next)}>
            {capitalised(shortDateText(parseDay(next)))} ›
          </button>
        )}
      </div>
    </section>
  );
}
