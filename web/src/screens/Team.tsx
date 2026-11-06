// Echipe: one club's season, as a club page of a sports channel (Phase 19's, tidied as the team
// asked after Phase 21): the crest and the name on a head lit by the league's colour, the season in
// numbers, the form as an aligned table (home, away, all), the shots, the matches with their
// predictions, the club's profile (K-Means, explained in Analiză) and its charts. Since Phase 25
// the club's head is the screen's head, a season still in progress offers the K-Means groups of
// the last finished one, and the Elo chart shades the seasons that only start the models.
import { lazy, Suspense, useEffect, useState } from "react";
import { api } from "../api";
import { Crest } from "../components/Crest";
import { FormSquares } from "../components/FormSquares";
import { StarIcon } from "../components/Icons";
import { ColumnsHead, MatchRow } from "../components/MatchRow";
import { Problem } from "../components/Problem";
import { SkeletonCard } from "../components/Skeleton";
import { StadiumPhoto } from "../components/StadiumPhoto";
import { number, seasonText, teamName } from "../format";
import { ACCENT } from "../theme";
import type { Favourite, Forecast, League, TeamPage, TeamRecord } from "../types";
import { MODELS } from "../types";

const LAST_RESULTS = 5;
// The charts (and Recharts with them) load when a team page first shows them
const EloChart = lazy(() => import("../components/charts/EloChart").then((module) => ({ default: module.EloChart })));
const GroupsChart = lazy(() =>
  import("../components/charts/GroupsChart").then((module) => ({ default: module.GroupsChart })),
);

interface Props {
  league: League;
  season: string;
  team: string | null;
  favourite: Favourite | null;
  ready: string;
  onChoice: (team: string | null, season: string) => void;
  onOpenMatch: (forecast: Forecast) => void;
  onFavourite: (favourite: Favourite | null) => void;
  onAnalysis: () => void;
}

export function Team({ league, season, team, favourite, ready, onChoice, onOpenMatch, onFavourite, onAnalysis }: Props) {
  const [page, setPage] = useState<TeamPage | null>(null);
  const [teams, setTeams] = useState<string[]>([]);
  const [matches, setMatches] = useState<Forecast[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"elo" | "groups">("elo");
  const [earlier, setEarlier] = useState<TeamPage | null>(null); // the last finished season's groups
  useEffect(() => setEarlier(null), [league.code, season, team]);

  useEffect(() => {
    let live = true;
    api.season(league.code, season).then((found) => live && setTeams(found.teams));
    return () => {
      live = false;
    };
  }, [league.code, season]);

  useEffect(() => {
    let live = true;
    setError(null);
    // a team that did not play the season gives way to the server's choice
    const asked = team && (teams.length === 0 || teams.includes(team)) ? team : null;
    api
      .team(league.code, season, asked)
      .then((found) => live && setPage(found))
      .catch((reason: Error) => live && setError(reason.message));
    return () => {
      live = false;
    };
  }, [league.code, season, team, teams]);

  useEffect(() => {
    let live = true;
    setMatches(null);
    if (page && league.prepared) {
      api.teamMatches(league.code, page.team, page.season).then((found) => live && setMatches(found));
    }
    return () => {
      live = false;
    };
  }, [league.code, league.prepared, page?.team, page?.season, ready]);

  const accent = ACCENT;
  const isFavourite = !!page && favourite?.competition === league.code && favourite.team === page.team;
  return (
    <div className="team-screen">
      <div className="control-row">
        <label className="caption" htmlFor="team-season">
          Sezon
        </label>
        <select id="team-season" value={season} onChange={(event) => onChoice(page?.team ?? team, event.target.value)}>
          {[...league.seasons].reverse().map((item) => (
            <option key={item} value={item}>
              {seasonText(item)}
            </option>
          ))}
        </select>
        <label className="caption" htmlFor="team-name">
          Echipă
        </label>
        <select id="team-name" value={page?.team ?? ""} onChange={(event) => onChoice(event.target.value, season)}>
          {teams.map((item) => (
            <option key={item} value={item}>
              {teamName(item)}
            </option>
          ))}
        </select>
      </div>
      {error && <Problem detail={error}>Pagina echipei nu a putut fi citită. Alege altă echipă sau alt sezon.</Problem>}
      {!page && !error && (
        <>
          <SkeletonCard height={150} title={false} />
          <div className="team-grid">
            <SkeletonCard height={260} />
            <SkeletonCard height={260} />
          </div>
        </>
      )}
      {page && (
        <>
          <section className="team-head">
            <StadiumPhoto team={page.team} className="beside" />
            <Crest team={page.team} size={104} ring={isFavourite} />
            <div className="team-head-text">
              <h1>{teamName(page.team)}</h1>
              <span>
                {league.name} {seasonText(page.season)} · locul {page.position} din {page.teams} ·{" "}
                {page.in_progress ? "sezon în desfășurare" : "sezon încheiat"}
              </span>
              {page.stadium && <span className="stadium-name">Stadion: {page.stadium}</span>}
            </div>
            <button
              className={`button${isFavourite ? "" : " primary"}`}
              aria-pressed={isFavourite}
              onClick={() => onFavourite(isFavourite ? null : { competition: league.code, team: page.team })}
            >
              <StarIcon filled={isFavourite} />
              {isFavourite ? "Echipa ta" : "Alege ca echipa ta"}
            </button>
            {page.stadium && <span className="credit">Foto: Wikimedia Commons</span>}
          </section>
          <div className="tiles">
            {(
              [
                ["Loc", page.position],
                ["Meciuri", page.record.played],
                ["Victorii", page.record.wins],
                ["Goluri marcate", page.record.goals_for],
                ["Goluri primite", page.record.goals_against],
                ["Puncte", page.record.points],
              ] as [string, number][]
            ).map(([name, value]) => (
              <div key={name} className="tile">
                <strong>{value}</strong>
                <span>{name}</span>
              </div>
            ))}
          </div>
          <div className="team-grid">
            <div className="team-column">
              <FormCard page={page} />
              <ProfileCard page={page} onAnalysis={onAnalysis} />
            </div>
            <MatchesCard page={page} matches={matches} prepared={league.prepared} favourite={isFavourite ? page.team : null} onOpenMatch={onOpenMatch} />
          </div>
          <section className="card charts-card">
            <div className="tabs">
              <button className={`pill${view === "elo" ? " chosen" : ""}`} aria-pressed={view === "elo"} onClick={() => setView("elo")}>
                Rating Elo
              </button>
              <button className={`pill${view === "groups" ? " chosen" : ""}`} aria-pressed={view === "groups"} onClick={() => setView("groups")}>
                Grupuri K-Means
              </button>
            </div>
            <Suspense fallback={<p className="caption chart-message">Se încarcă graficul…</p>}>
              {view === "elo" && (
                <EloChart
                  team={page.team}
                  history={page.elo}
                  season={page.season}
                  accent={accent}
                  warmUpUntil={page.first_evaluated_season}
                />
              )}
              {view === "groups" && earlier?.groups && !page.groups && (
                <>
                  <div className="chart-note">
                    <span className="caption">
                      Grupurile sezonului {seasonText(earlier.season)}, ultimul încheiat
                    </span>
                    <button className="link" onClick={() => setEarlier(null)}>
                      Înapoi la {seasonText(page.season)}
                    </button>
                  </div>
                  <GroupsChart groups={earlier.groups} team={earlier.team} accent={accent} />
                </>
              )}
              {view === "groups" &&
                !(earlier?.groups && !page.groups) &&
                (page.groups ? (
                  <>
                    <GroupsChart groups={page.groups} team={page.team} accent={accent} />
                    <p className="caption">
                      Grupurile vin din șase valori pe meci, așa că o echipă poate sta mai aproape de centrul altui grup pe
                      aceste două axe.
                    </p>
                  </>
                ) : (
                  <div className="chart-message">
                    <p className="caption">{page.groups_problem}</p>
                    {page.in_progress && previousSeason(league.seasons, page.season) && (
                      <button
                        className="button"
                        onClick={() =>
                          api
                            .team(league.code, previousSeason(league.seasons, page.season) as string, page.team)
                            .then(setEarlier)
                            .catch(() => setEarlier(null))
                        }
                      >
                        Vezi grupurile din {seasonText(previousSeason(league.seasons, page.season) as string)}
                      </button>
                    )}
                  </div>
                ))}
            </Suspense>
          </section>
        </>
      )}
    </div>
  );
}

/** The season before ``season`` in the league's list, if any. */
export function previousSeason(seasons: string[], season: string): string | null {
  const index = seasons.indexOf(season);
  return index > 0 ? seasons[index - 1] : null;
}

function FormCard({ page }: { page: TeamPage }) {
  const rows: [string, TeamRecord][] = [
    ["Acasă", page.home],
    ["Deplasare", page.away],
    ["Total", page.record],
  ];
  const shots = page.shots;
  return (
    <section className="card form-card">
      <h2>Forma</h2>
      <div className="form-line">
        <span className="caption">Ultimele 5 meciuri</span>
        <FormSquares results={page.form} />
      </div>
      <div className="record-table" role="table">
        <div className="record-row head" role="row">
          <span />
          {["M", "V", "E", "Î", "GM", "GP", "Pct."].map((column) => (
            <span key={column}>{column}</span>
          ))}
        </div>
        {rows.map(([name, record]) => (
          <div key={name} className={`record-row${name === "Total" ? " total" : ""}`} role="row">
            <span>{name}</span>
            <span>{record.played}</span>
            <span>{record.wins}</span>
            <span>{record.draws}</span>
            <span>{record.losses}</span>
            <span>{record.goals_for}</span>
            <span>{record.goals_against}</span>
            <strong>{record.points}</strong>
          </div>
        ))}
      </div>
      <h3>Șuturi pe meci</h3>
      {shots.matches === 0 ? (
        <p className="caption">Sezonul nu are statistici de șuturi.</p>
      ) : (
        <div className="shots">
          <ShotsRow name="Pe poartă" own={shots.shots_on_target} opponent={shots.opponent_shots_on_target} />
          <ShotsRow name="Toate" own={shots.shots} opponent={shots.opponent_shots} />
          <div className="shots-legend caption">
            <span>
              <i className="key home" /> Echipa
            </span>
            <span>
              <i className="key away" /> Adversarii
            </span>
          </div>
        </div>
      )}
    </section>
  );
}

function ShotsRow({ name, own, opponent }: { name: string; own: number | null; opponent: number | null }) {
  const total = (own ?? 0) + (opponent ?? 0) || 1;
  return (
    <div className="shots-row">
      <span className="caption">{name}</span>
      <div className="shots-bar">
        <span className="segment home" style={{ flexGrow: (own ?? 0) / total }}>
          {number(own, 1)}
        </span>
        <span className="segment away" style={{ flexGrow: (opponent ?? 0) / total }}>
          {number(opponent, 1)}
        </span>
      </div>
    </div>
  );
}

function MatchesCard({
  page, matches, prepared, favourite, onOpenMatch,
}: {
  page: TeamPage;
  matches: Forecast[] | null;
  prepared: boolean;
  favourite: string | null;
  onOpenMatch: (forecast: Forecast) => void;
}) {
  const [all, setAll] = useState(false);
  useEffect(() => setAll(false), [page.team, page.season]);
  if (!prepared || matches === null) {
    return (
      <section className="card">
        <h2>Meciurile echipei</h2>
        <p className="caption">Predicțiile ligii se pregătesc; meciurile apar imediat ce sunt gata.</p>
      </section>
    );
  }
  const upcoming = matches.filter((match) => match.result === null);
  const played = matches.filter((match) => match.result !== null);
  const shown = all ? matches : [...upcoming.slice(0, 1), ...played.slice(-LAST_RESULTS).reverse()];
  return (
    <section className="card matches-card">
      <h2>Meciurile echipei</h2>
      <ColumnsHead stacked />
      <div className="match-list">
        {shown.map((forecast) => (
          <MatchRow
            key={`${forecast.date}-${forecast.home_team}`}
            forecast={forecast}
            model={MODELS[0]}
            favourite={favourite}
            stacked
            showDate
            onOpen={onOpenMatch}
          />
        ))}
      </div>
      <div className="card-foot">
        <span className="caption">Probabilitățile sunt ale regresiei logistice; apasă pe un meci pentru toate modelele.</span>
        <button className="link" onClick={() => setAll(!all)}>
          {all ? "Mai puține ‹" : `Toate cele ${matches.length} ›`}
        </button>
      </div>
    </section>
  );
}

function ProfileCard({ page, onAnalysis }: { page: TeamPage; onAnalysis: () => void }) {
  return (
    <section className="card profile-card">
      <h2>Profilul echipei</h2>
      <div className="profile-item">
        <span className="caption">Înaintea sezonului</span>
        <strong>{page.pre_season_group}</strong>
      </div>
      <div className="profile-item">
        <span className="caption">Sezonul {seasonText(page.season)}</span>
        {page.season_group ? (
          <strong>{page.season_group}</strong>
        ) : (
          <span className="caption">Se stabilește după ultimul meci al sezonului.</span>
        )}
      </div>
      <button className="link" onClick={onAnalysis}>
        Cum se formează profilurile ›
      </button>
    </section>
  );
}
