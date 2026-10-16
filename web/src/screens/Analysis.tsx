// Analiză (Phase 19's, in the web interface): how the algorithms work in plain words (with the
// K-Means profiles the team pages name), how the models did on the season in progress, the full
// chronological evaluation of the league's models, the comparison of the five leagues, and the
// sources. Tables have measured columns; each card ends with its content.
import { lazy, type ReactNode, Suspense, useEffect, useState } from "react";
import { api } from "../api";
import { ConfusionGrid, HomeAdvantage } from "../components/AnalysisGrids";
import { type Column, DataTable } from "../components/DataTable";
import { Flag } from "../components/Flag";
import { dateText, integer, number, parseDay, percent, quantity, seasonText, signed } from "../format";
import { themeFor } from "../theme";
import type { About, Difference, Evaluation, League, LeaguesComparison, SeasonCheck, Subset } from "../types";
import { MODEL_LABELS } from "../types";

const CalibrationChart = lazy(() =>
  import("../components/charts/AnalysisCharts").then((module) => ({ default: module.CalibrationChart })),
);
const SkillChart = lazy(() =>
  import("../components/charts/AnalysisCharts").then((module) => ({ default: module.SkillChart })),
);

type Tab = "how" | "season" | "models" | "leagues" | "sources";
const TABS: [Tab, string][] = [
  ["how", "Cum funcționează"],
  ["season", "Sezonul curent"],
  ["models", "Modele"],
  ["leagues", "Ligi"],
  ["sources", "Surse"],
];

/** 0,5776 ± 0,0123: a value with the half-width of its 95% interval. */
export function interval(value: number, margin: number | null, digits = 4): string {
  return margin === null ? number(value, digits) : `${number(value, digits)} ± ${number(margin, digits)}`;
}

function differenceText(difference: Difference): string {
  return `${signed(difference.mean)} · ${difference.better_label ?? "nicio diferență reală"}`;
}

const label = (model: string) => MODEL_LABELS[model] ?? model;
const EVEN = "minmax(0, 1fr)"; // number columns that share a table's width evenly
const chartFallback = <p className="caption chart-message">Se încarcă graficul…</p>;
const loading = <p className="caption">Se încarcă…</p>;

interface Props {
  league: League;
  leagues: League[];
  ready: string;
  onLeague: (code: string) => void;
}

export function Analysis({ league, leagues, ready, onLeague }: Props) {
  const [tab, setTab] = useState<Tab>("how");
  return (
    <div className="analysis-screen">
      <div className="tabs">
        {TABS.map(([name, title]) => (
          <button key={name} className={`pill${tab === name ? " chosen" : ""}`} onClick={() => setTab(name)}>
            {title}
          </button>
        ))}
      </div>
      {tab === "how" && <HowItWorks />}
      {tab === "season" && <SeasonCheckTab league={league} ready={ready} />}
      {tab === "models" && <Models league={league} />}
      {tab === "leagues" && <Leagues league={league} leagues={leagues} onLeague={onLeague} />}
      {tab === "sources" && <Sources />}
    </div>
  );
}

function useAbout(): About | null {
  const [about, setAbout] = useState<About | null>(null);
  useEffect(() => {
    api.about().then(setAbout);
  }, []);
  return about;
}

function HowItWorks() {
  const about = useAbout();
  if (!about) return loading;
  return (
    <div className="explanations">
      {about.explanations.map((item) => (
        <section key={item.title} className="card explanation">
          <h2>{item.title}</h2>
          <p>{item.text}</p>
        </section>
      ))}
      <section className="card explanation">
        <h2>Profilurile echipelor (K-Means)</h2>
        <p>{about.groups}</p>
      </section>
    </div>
  );
}

function SeasonCheckTab({ league, ready }: { league: League; ready: string }) {
  const [check, setCheck] = useState<SeasonCheck | null>(null);
  useEffect(() => {
    api.seasonCheck(league.code).then(setCheck);
  }, [league.code, ready]);
  if (!check) return loading;
  const messages: Record<string, string> = {
    missing: "Sezonul în desfășurare nu a fost descărcat. Apasă „Actualizează datele”.",
    preparing: "Predicțiile ligii se pregătesc…",
    empty: `Niciun meci al sezonului ${check.season ? seasonText(check.season) : ""} nu are încă predicțiile tuturor modelelor.`,
  };
  const columns: Column[] = [
    { label: "Model", width: "minmax(180px, 1fr)" },
    { label: "Meciuri", width: "96px" },
    { label: "Acuratețe", width: "112px" },
    { label: "Scor Brier", width: "168px" },
    { label: "Pierdere logaritmică", width: "184px" },
  ];
  return (
    <section className="card">
      <h2>Cum au prezis modelele sezonul în desfășurare</h2>
      {check.state !== "ready" ? (
        <p className="caption">{messages[check.state]}</p>
      ) : (
        <>
          <DataTable
            columns={columns}
            rows={check.models.map((model) => [
              model.label,
              integer(check.matches),
              percent(model.accuracy),
              interval(model.brier.value, model.brier.margin),
              interval(model.log_loss.value, model.log_loss.margin),
            ])}
          />
          <p className="caption table-note">
            {league.name} {seasonText(check.season as string)}: {quantity(check.matches, "meci jucat", "meciuri jucate")}{" "}
            între {dateText(parseDay(check.first_day as string))} și {dateText(parseDay(check.last_day as string))}, fiecare
            prezis înainte să se joace. Marjele (±) sunt intervale de 95%. Sunt puține meciuri, așa că diferențele dintre
            modele nu sunt încă sigure; evaluarea completă, pe 16 sezoane, este în fila Modele. Acest sezon nu face parte
            din ea.
          </p>
        </>
      )}
    </section>
  );
}

function Backtest({ text, busy, onRun }: { text: string; busy: boolean; onRun: () => void }) {
  return (
    <section className="card backtest">
      <p>{busy ? "Backtestul rulează…" : text}</p>
      <button className="button primary" disabled={busy} onClick={onRun}>
        Rulează backtestul
      </button>
    </section>
  );
}

const BREAKDOWNS: ["by_season" | "by_outcome" | "by_matchup_type", string][] = [
  ["by_season", "Pe sezoane"],
  ["by_outcome", "Pe rezultatul real"],
  ["by_matchup_type", "Pe tipuri de meciuri"],
];

function Models({ league }: { league: League }) {
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [breakdown, setBreakdown] = useState<(typeof BREAKDOWNS)[number][0]>("by_season");
  const [confusionModel, setConfusionModel] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setEvaluation(null);
    api
      .evaluation(league.code)
      .then((found) => live && setEvaluation(found))
      .catch((reason: Error) => live && setError(reason.message));
    return () => {
      live = false;
    };
  }, [league.code]);

  const run = () => {
    setBusy(true);
    setError(null);
    api
      .backtest(league.code)
      .then(setEvaluation)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setBusy(false));
  };

  if (error) return <p className="problem">Rezultatele nu au putut fi citite. {error}</p>;
  if (!evaluation) return loading;
  if (!evaluation.has_log) {
    return (
      <Backtest
        busy={busy}
        onRun={run}
        text={`Nu există încă un jurnal al predicțiilor pentru ${league.name}. Rulează backtestul (aproximativ 10 secunde) ca să vezi comparația.`}
      />
    );
  }
  if (evaluation.problem) {
    return (
      <Backtest
        busy={busy}
        onRun={run}
        text={`Rezultatele nu pot fi citite. Rulează din nou backtestul ca să refaci jurnalul predicțiilor. Detalii: ${evaluation.problem}`}
      />
    );
  }

  const accent = themeFor(league.code).accent;
  const lowestBrier = Math.min(...evaluation.models.map((m) => m.brier ?? Infinity));
  const confusion = evaluation.models.find((m) => m.model === confusionModel) ?? evaluation.models[0];
  const subsets: Subset[] = evaluation[breakdown];
  return (
    <div className="analysis-stack">
      <p className="caption">
        {league.name}: {quantity(evaluation.matches, "meci", "meciuri")}, sezoanele{" "}
        {seasonText(evaluation.first_season as string)}–{seasonText(evaluation.last_season as string)}; fiecare model a
        prezis în ordine cronologică, doar din meciurile dinaintea fiecărei zile.
      </p>
      <section className="card">
        <h2>Măsurile generale</h2>
        <DataTable
          columns={[
            { label: "Model", width: "minmax(190px, 1fr)" },
            { label: "Acuratețe", width: "104px" },
            { label: "Scor Brier", width: "112px" },
            { label: "Pierdere logaritmică", width: "164px" },
            { label: "Eroare de calibrare", width: "156px" },
            { label: "Eroarea golurilor", width: "144px" },
          ]}
          rows={evaluation.models.map((model) => [
            model.label,
            percent(model.accuracy),
            model.brier === lowestBrier ? <strong className="best">{number(model.brier)}</strong> : number(model.brier),
            number(model.log_loss),
            number(model.calibration_error),
            number(model.goals_error, 3),
          ])}
        />
        <p className="caption table-note">
          Acuratețea: mai mare e mai bine. Scorul Brier, pierderea logaritmică și erorile: mai mic e mai bine; cel mai
          mic scor Brier este evidențiat. Eroarea golurilor (doar Poisson): cât greșesc în medie golurile așteptate.
        </p>
      </section>
      <div className="analysis-pair">
        <section className="card">
          <h2>Calibrarea</h2>
          <Suspense fallback={chartFallback}>
            <CalibrationChart models={evaluation.models.filter((m) => m.calibration)} labels={MODEL_LABELS} />
          </Suspense>
          <p className="caption table-note">Pe diagonală, „60%” s-a întâmplat în 60% din cazuri. Toate rezultatele, 10 intervale.</p>
        </section>
        <section className="card">
          <h2>Matricea de confuzie</h2>
          <div className="segmented wrap">
            {evaluation.models.map((model) => (
              <button
                key={model.model}
                className={`pill${model.model === confusion.model ? " chosen" : ""}`}
                onClick={() => setConfusionModel(model.model)}
              >
                {model.label}
              </button>
            ))}
          </div>
          <ConfusionGrid matrix={confusion.confusion} accent={accent} />
          <p className="caption table-note">
            Meciurile după rezultatul real (rânduri) și cel prezis (coloane); procentele sunt din fiecare rând.
          </p>
        </section>
      </div>
      <section className="card">
        <h2>Diferențele meci cu meci</h2>
        <DataTable
          columns={[
            { label: "Comparație", width: "minmax(220px, 1fr)" },
            { label: "Măsură", width: "176px", align: "left" },
            { label: "Diferență", width: "104px" },
            { label: "Interval de 95%", width: "176px" },
            { label: "Mai bun", width: "minmax(150px, 0.6fr)", align: "left" },
          ]}
          rows={evaluation.differences.map((d) => [
            `${d.first_label} – ${d.second_label}`,
            d.measure_label,
            signed(d.mean),
            `[${signed(d.lower)}; ${signed(d.upper)}]`,
            d.better_label ? <strong className="best">{d.better_label}</strong> : <span className="caption">nicio diferență reală</span>,
          ])}
        />
        <p className="caption table-note">O diferență este reală doar când intervalul ei de 95% nu conține 0.</p>
      </section>
      <section className="card">
        <h2>Unde se descurcă fiecare model</h2>
        <div className="segmented wrap">
          {BREAKDOWNS.map(([name, title]) => (
            <button key={name} className={`pill${breakdown === name ? " chosen" : ""}`} onClick={() => setBreakdown(name)}>
              {title}
            </button>
          ))}
        </div>
        <DataTable
          columns={[
            { label: "Categorie", width: "minmax(190px, 1fr)" },
            { label: "Meciuri", width: "84px" },
            ...evaluation.compared.map((model) => ({ label: label(model), width: "128px" })),
            { label: "Cel mai bun", width: "150px", align: "left" as const },
            { label: "Avantaj real", width: "104px", align: "center" as const },
          ]}
          rows={subsets.map((subset) => [
            subset.label,
            integer(subset.matches),
            ...evaluation.compared.map((model) =>
              model === subset.best ? <strong className="best">{number(subset.brier[model])}</strong> : number(subset.brier[model] ?? null),
            ),
            subset.best_label,
            subset.real ? "da" : "nu",
          ])}
        />
        <p className="caption table-note">Scorul Brier pe fiecare subset (mai mic e mai bine).</p>
      </section>
      <section className="card">
        <h2>Cât de diferite sunt predicțiile</h2>
        <DataTable
          columns={[
            { label: "Modele", width: "minmax(220px, 1fr)" },
            { label: "Același rezultat prezis", width: "200px" },
            { label: "Distanța medie", width: "150px" },
          ]}
          rows={evaluation.agreements.map((a) => [`${a.first_label} – ${a.second_label}`, percent(a.same), number(a.distance)])}
        />
        {evaluation.all_agree !== null && (
          <p className="caption table-note">Toate trei modelele prezic același rezultat în {percent(evaluation.all_agree)} dintre meciuri.</p>
        )}
      </section>
    </div>
  );
}

function Leagues({ league, leagues, onLeague }: { league: League; leagues: League[]; onLeague: (code: string) => void }) {
  const [comparison, setComparison] = useState<LeaguesComparison | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .leaguesComparison()
      .then(setComparison)
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const run = () => {
    setBusy(true);
    api
      .leaguesBacktest()
      .then(setComparison)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setBusy(false));
  };

  if (error) return <p className="problem">Comparația nu a putut fi citită. {error}</p>;
  if (!comparison) return loading;
  if (comparison.missing.length > 0 || comparison.problem) {
    const names = comparison.missing.map((code) => leagues.find((item) => item.code === code)?.name ?? code).join(", ");
    return (
      <Backtest
        busy={busy}
        onRun={run}
        text={
          comparison.problem
            ? `Rezultatele nu pot fi citite. Detalii: ${comparison.problem}`
            : `Lipsesc jurnalele predicțiilor pentru: ${names}. Rulează backtestul lor (aproximativ 10 secunde pentru fiecare ligă) ca să vezi comparația.`
        }
      />
    );
  }
  const current = (index: number) => comparison.results[index]?.code === league.code;
  const models = [...comparison.compared, comparison.reference];
  const leagueCell = (code: string, name: string): ReactNode => (
    <span className="league-cell">
      <Flag code={code} size={18} />
      {name}
    </span>
  );
  return (
    <div className="analysis-stack">
      <div className="league-cards">
        {comparison.results.map((result) => (
          <button
            key={result.code}
            className={`card league-card${result.code === league.code ? " current" : ""}`}
            onClick={() => onLeague(result.code)}
          >
            <span className="league-card-head">
              <Flag code={result.code} size={24} />
              <strong>{result.name}</strong>
            </span>
            <span className="big">{percent(result.character.home_win, 0)}</span>
            <span className="caption">victorii ale gazdelor</span>
            <span className="caption">{number(result.character.goals, 2)} goluri pe meci</span>
            <span className="league-card-best">
              <span className="caption">Cel mai mic scor Brier</span>
              <strong>{result.best_label}</strong>
            </span>
          </button>
        ))}
      </div>
      <p className="caption">
        {quantity(comparison.results.length, "ligă", "ligi")}, {quantity(comparison.matches, "meci", "meciuri")} de evaluare,
        sezoanele 2010/11–2025/26. Fiecare ligă are propriii parametri, aleși pe sezoanele ei de calibrare. Liga aleasă este
        evidențiată.
      </p>
      <section className="card">
        <h2>Caracterul ligilor</h2>
        <DataTable
          highlight={current}
          columns={[
            { label: "Ligă", width: "minmax(150px, 1.5fr)" },
            { label: "Meciuri", width: EVEN },
            { label: "Victorii gazde", width: EVEN },
            { label: "Egaluri", width: EVEN },
            { label: "Victorii oaspeți", width: EVEN },
            { label: "Goluri pe meci", width: EVEN },
            { label: "Marja gazdelor", width: EVEN },
            { label: "Gazde 2020/21", width: EVEN },
            { label: "Gazde, alte sezoane", width: EVEN },
          ]}
          rows={comparison.results.map((r) => {
            const c = r.character;
            return [
              leagueCell(r.code, r.name),
              integer(c.matches),
              percent(c.home_win),
              percent(c.draw),
              percent(c.away_win),
              number(c.goals, 2),
              signed(c.home_margin, 2),
              c.closed_doors_home_win === null ? "–" : percent(c.closed_doors_home_win),
              c.other_seasons_home_win === null ? "–" : percent(c.other_seasons_home_win),
            ];
          })}
        />
      </section>
      <section className="card">
        <h2>Modelele în fiecare ligă</h2>
        <DataTable
          highlight={current}
          columns={[
            { label: "Ligă", width: "minmax(150px, 1.5fr)" },
            ...models.map((model) => ({ label: label(model), width: EVEN })),
            { label: "Cel mai mic scor", width: "minmax(0, 1.4fr)", align: "left" as const },
            { label: "Abilitatea lui", width: EVEN },
          ]}
          rows={comparison.results.map((r) => [
            leagueCell(r.code, r.name),
            ...models.map((model) =>
              model === r.best ? <strong className="best">{number(r.brier[model])}</strong> : number(r.brier[model] ?? null),
            ),
            r.best_label,
            percent(r.skill[r.best]),
          ])}
        />
        <p className="caption table-note">
          Scorul Brier (mai mic e mai bine). Abilitatea: partea din scorul Brier al frecvențelor trecute pe care o elimină
          modelul.
        </p>
      </section>
      <section className="card">
        <h2>Care model e mai bun, meci cu meci</h2>
        <DataTable
          highlight={current}
          columns={[
            { label: "Ligă", width: "minmax(150px, 1.5fr)" },
            ...comparison.pooled.map((d) => ({ label: `${d.first_label} – ${d.second_label}`, width: "minmax(0, 1.5fr)", align: "left" as const })),
          ]}
          rows={[
            ...comparison.results.map((r) => [leagueCell(r.code, r.name), ...r.differences.map(differenceText)]),
            [<strong key="all">Toate ligile</strong>, ...comparison.pooled.map(differenceText)],
          ]}
        />
        <p className="caption table-note">
          Diferența scorului Brier: negativă înseamnă că primul model e mai bun; după ea este modelul real mai bun (intervalul de
          95% nu conține 0). „Toate ligile” compară modelele pe toate meciurile la un loc.
        </p>
      </section>
      <div className="analysis-pair">
        <section className="card">
          <h2>Abilitatea modelelor</h2>
          <Suspense fallback={chartFallback}>
            <SkillChart results={comparison.results} models={comparison.compared} />
          </Suspense>
          <p className="caption table-note">Cât elimină fiecare model din eroarea frecvențelor trecute (abilitate Brier).</p>
        </section>
        <section className="card">
          <h2>Avantajul gazdelor</h2>
          <HomeAdvantage results={comparison.results} />
          <p className="caption table-note">
            Victoriile gazdelor cu spectatori și în 2020/21, sezon jucat în mare parte fără spectatori.
          </p>
        </section>
      </div>
    </div>
  );
}

function Sources() {
  const about = useAbout();
  if (!about) return loading;
  return (
    <section className="card sources">
      <h2>Sursele datelor și ale imaginilor</h2>
      {about.sources.map((source) => (
        <div key={source.title} className="source">
          <span className="overline">{source.title}</span>
          <p>{source.text}</p>
          {source.title === "Stemele cluburilor" && (
            <p className="caption">{quantity(about.crests, "stemă", "steme")} în aplicație.</p>
          )}
        </div>
      ))}
      <div className="source">
        <span className="overline">Imaginile ligilor</span>
        {(about.photos.length ? about.photos : ["Nicio imagine inclusă."]).map((line) => (
          <p key={line}>{line}</p>
        ))}
        <p className="caption">{about.images_note}</p>
      </div>
    </section>
  );
}
