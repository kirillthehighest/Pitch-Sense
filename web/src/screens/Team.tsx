// Echipe: one club's season, as a club page of a sports channel (Phase 19's, tidied as the team
// asked after Phase 21): the crest and the name on a head lit by the league's colour, the season in
// numbers, the form as an aligned table (home, away, all), the shots, the matches with their
// predictions, the club's profile (K-Means, explained in Analiză) and its charts.
import { lazy, Suspense, useEffect, useState } from "react";
import { api } from "../api";
import { Crest } from "../components/Crest";
import { FormSquares } from "../components/FormSquares";
import { MatchRow } from "../components/MatchRow";
import { number, seasonText } from "../format";
import { themeFor } from "../theme";
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

  const accent = themeFor(league.code).accent;
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
            <option key={item}>{item}</option>
          ))}
        </select>
      </div>
      {error && <p className="problem">Pagina echipei nu a putut fi citită. {error}</p>}
      {page && (
        <>
          <section className="team-head">
            <Crest team={page.team} size={104} ring={isFavourite} />
            <div className="team-head-text">
              <span className="eyebrow">{isFavourite ? `Echipa ta · ${league.name}` : league.name}</span>
              <h2>{page.team}</h2>
              <span>
                {seasonText(page.season)} · locul {page.position} din {page.teams} ·{" "}
                {page.in_progress ? "sezon în desfășurare" : "sezon încheiat"}
              </span>
            </div>
            <button
              className={`button${isFavourite ? "" : " primary"}`}
              onClick={() => onFavourite(isFavourite ? null : { competition: league.code, team: page.team })}
            >
              {isFavourite ? "★ Echipa ta" : "☆ Alege ca echipa ta"}
            </button>
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
            <FormCard page={page} />
            <MatchesCard page={page} matches={matches} prepared={league.prepared} favourite={isFavourite ? page.team : null} onOpenMatch={onOpenMatch} />
            <ProfileCard page={page} onAnalysis={onAnalysis} />
          </div>
          <section className="card charts-card">
            <div className="tabs">
              <button className={`pill${view === "elo" ? " chosen" : ""}`} onClick={() => setView("elo")}>
                Rating Elo
              </button>
              <button className={`pill${view === "groups" ? " chosen" : ""}`} onClick={() => setView("groups")}>
                Grupuri K-Means
              </button>
            </div>
            <Suspense fallback={<p className="caption chart-message">Se încarcă graficul…</p>}>
              {view === "elo" && <EloChart team={page.team} history={page.elo} season={page.season} accent={accent} />}
              {view === "groups" &&
                (page.groups ? (
                  <>
                    <GroupsChart groups={page.groups} team={page.team} accent={accent} />
                    <p className="caption">
                      Grupurile vin din șase valori pe meci, așa că o echipă poate sta mai aproape de centrul altui grup pe
                      aceste două axe.
                    </p>
                  </>
                ) : (
                  <p className="caption chart-message">{page.groups_problem}</p>
                ))}
            </Suspense>
          </section>
        </>
      )}
    </div>
  );
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
        <strong>{page.season_group ?? "Sezonul nu este încheiat"}</strong>
      </div>
      <button className="link" onClick={onAnalysis}>
        Cum se formează profilurile ›
      </button>
    </section>
  );
}
