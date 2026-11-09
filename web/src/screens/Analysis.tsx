// Analiză (Phase 19's, in the web interface): how the algorithms work in plain words (with the
// K-Means profiles the team pages name), how the models did on the season in progress, the full
// chronological evaluation of the league's models, the comparison of the five leagues, and the
// sources. Tables have measured columns; each card ends with its content. Since Phase 25 each tab
// opens with its finding in one sentence (written from the numbers on screen), "Cum funcționează"
// draws each algorithm, and the statistical tables wait behind "Detalii statistice".
import { lazy, type ReactNode, Suspense, useEffect, useState } from "react";
import { api } from "../api";
import { ConfusionGrid, HomeAdvantage } from "../components/AnalysisGrids";
import { type Column, DataTable } from "../components/DataTable";
import { EloDiagram, KMeansDiagram, LogisticDiagram, PoissonDiagram, TimelineDiagram } from "../components/Diagrams";
import { Problem } from "../components/Problem";
import { SkeletonCard } from "../components/Skeleton";
import { Flag } from "../components/Flag";
import { capitalised, dateText, integer, number, parseDay, percent, quantity, seasonText, signed } from "../format";
import { themeFor } from "../theme";
import type {
  About,
  BookmakerComparison,
  ConfidentAccuracy,
  Difference,
  Evaluation,
  League,
  LeaguesComparison,
  ModelEvaluation,
  SeasonCheck,
  Subset,
} from "../types";
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
const SURE = 0.65; // the threshold of "when the model is sure" shown beside the bookmakers
const chartFallback = <p className="caption chart-message">Se încarcă graficul…</p>;
const loading = (
  <div className="analysis-stack">
    <SkeletonCard height={70} title={false} />
    <SkeletonCard height={220} />
  </div>
);
const MODELS_COMPARED = ["Logistic regression", "Elo", "Poisson"];
/** A model's name inside a sentence: "regresia logistică", "modelul Elo". */
const IN_SENTENCE: Record<string, string> = {
  "Logistic regression": "regresia logistică",
  Elo: "modelul Elo",
  Poisson: "modelul Poisson",
};
const named = (model: string, label: string) => IN_SENTENCE[model] ?? label;
const REFERENCE = "Past frequencies";

/** The finding a tab opens with: one sentence, and the numbers behind it. */
function Finding({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="finding">
      <h2>{title}</h2>
      <p>{children}</p>
    </section>
  );
}

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
      <div className="tabs" role="tablist" aria-label="Analiză">
        {TABS.map(([name, title]) => (
          <button
            key={name}
            role="tab"
            aria-selected={tab === name}
            className={`pill${tab === name ? " chosen" : ""}`}
            onClick={() => setTab(name)}
          >
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

const DIAGRAMS: Record<string, () => ReactNode> = {
  "Ratingul Elo": EloDiagram,
  "Modelul Poisson": PoissonDiagram,
  "Regresia logistică": LogisticDiagram,
  "K‑Means": KMeansDiagram,
  "Cum sunt verificate": TimelineDiagram,
};

function HowItWorks() {
  const about = useAbout();
  if (!about) return loading;
  const algorithms = about.explanations.filter((item) => item.title in DIAGRAMS && item.title !== "Cum sunt verificate");
  const others = about.explanations.filter((item) => !algorithms.includes(item));
  return (
    <div className="analysis-stack">
      <Finding title="Trei modele prezic, unul descrie">
        Elo, Poisson și regresia logistică dau fiecare meci șanse de victorie, egal și înfrângere; K-Means nu prezice, ci
        grupează echipele după felul în care joacă. Toate sunt scrise de noi, după formulele lor.
      </Finding>
      <div className="explanations">
        {algorithms.map((item) => {
          const Diagram = DIAGRAMS[item.title];
          return (
            <section key={item.title} className="card explanation">
              <figure className="diagram">
                <Diagram />
              </figure>
              <h2>{item.title}</h2>
              {/* K-Means once: the detailed text of the team pages' groups, not a second summary */}
              <p>{item.title === "K‑Means" ? about.groups : item.text}</p>
            </section>
          );
        })}
      </div>
      <div className="explanations">
        {others.map((item) => {
          const Diagram = DIAGRAMS[item.title];
          return (
            <section key={item.title} className="card explanation">
              {Diagram && (
                <figure className="diagram">
                  <Diagram />
                </figure>
              )}
              <h2>{item.title}</h2>
              <p>{item.text}</p>
            </section>
          );
        })}
      </div>
      <p className="caption">Schemele arată ideea fiecărui algoritm; cifrele de pe ele sunt exemple, nu rezultate.</p>
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
    { label: "Model", width: "minmax(150px, 1.6fr)" },
    { label: "Meciuri", width: EVEN },
    { label: "Acuratețe", width: EVEN },
    { label: "Scor Brier", width: "minmax(0, 1.4fr)" },
    { label: "Pierdere logaritmică", width: "minmax(0, 1.4fr)" },
  ];
  const ranked = check.state === "ready" ? [...check.models].sort((a, b) => a.brier.value - b.brier.value) : [];
  const [best, runnerUp] = ranked;
  const overlap =
    best && runnerUp && best.brier.margin !== null && runnerUp.brier.margin !== null
      ? best.brier.value + best.brier.margin >= runnerUp.brier.value - runnerUp.brier.margin
      : false;
  return (
    <div className="analysis-stack">
      {best && (
        <Finding title={`În ${seasonText(check.season as string)}, până acum, ${named(best.model, best.label)} are cel mai mic scor Brier`}>
          {number(best.brier.value)} pe {quantity(check.matches, "meci", "meciuri")}, cu o acuratețe de{" "}
          {percent(best.accuracy)}.
          {overlap && " Marjele de 95% se suprapun încă, așa că sezonul nu decide un câștigător."}
        </Finding>
      )}
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
    </div>
  );
}

function Backtest({ text, busy, onRun, detail }: { text: string; busy: boolean; onRun: () => void; detail?: string | null }) {
  return (
    <section className="card backtest">
      <div>
        <p>{busy ? "Backtestul rulează…" : text}</p>
        {detail && !busy && (
          <details>
            <summary>Detalii tehnice</summary>
            <code>{detail}</code>
          </details>
        )}
      </div>
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

  if (error) return <Problem detail={error}>Rezultatele evaluării nu au putut fi citite. Încearcă din nou.</Problem>;
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
        text="Rezultatele nu pot fi citite. Rulează din nou backtestul ca să refaci jurnalul predicțiilor."
        detail={evaluation.problem}
      />
    );
  }

  const accent = themeFor(league.code).accent;
  const lowestBrier = Math.min(...evaluation.models.map((m) => m.brier ?? Infinity));
  const confusion = evaluation.models.find((m) => m.model === confusionModel) ?? evaluation.models[0];
  const subsets: Subset[] = evaluation[breakdown];
  const compared = evaluation.models.filter((m) => MODELS_COMPARED.includes(m.model) && m.brier !== null);
  const ranked = [...compared].sort((a, b) => (a.brier as number) - (b.brier as number));
  const reference = evaluation.models.find((m) => m.model === REFERENCE);
  const [first, second] = ranked;
  const versus = first && second
    ? evaluation.differences.find(
        (d) => d.measure === "Brier score" && [d.first, d.second].includes(first.model) && [d.first, d.second].includes(second.model),
      )
    : undefined;
  return (
    <div className="analysis-stack">
      {first && (
        <Finding title={`În ${league.name}, ${named(first.model, first.label)} prezice cel mai bine`}>
          Cel mai mic scor Brier, {number(first.brier)}
          {reference?.brier
            ? `, cu ${percent(1 - (first.brier as number) / reference.brier, 0)} mai puțină eroare decât frecvențele trecute (${number(reference.brier)})`
            : ""}
          .{" "}
          {second &&
            (versus?.better
              ? `Față de ${named(second.model, second.label)} (${number(second.brier)}), diferența e reală: intervalul ei de 95% nu conține 0.`
              : `Față de ${named(second.model, second.label)} (${number(second.brier)}), diferența e prea mică pentru a fi sigură.`)}
        </Finding>
      )}
      <p className="caption">
        {league.name}: {quantity(evaluation.matches, "meci", "meciuri")}, sezoanele{" "}
        {seasonText(evaluation.first_season as string)}–{seasonText(evaluation.last_season as string)}; fiecare model a
        prezis în ordine cronologică, doar din meciurile dinaintea fiecărei zile.
      </p>
      <section className="card">
        <h2>Măsurile generale</h2>
        <DataTable
          columns={[
            { label: "Model", width: "minmax(150px, 1.6fr)" },
            { label: "Acuratețe", width: EVEN },
            { label: "Scor Brier", width: EVEN },
            { label: "Pierdere logaritmică", width: EVEN },
            { label: "Eroare de calibrare", width: EVEN },
            { label: "Eroarea golurilor", width: EVEN },
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
                className={`pill${model.model === confusion.model ? " chosen" : ""}`} aria-pressed={model.model === confusion.model}
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
      <WhenSure models={evaluation.models.filter((m) => m.confident.length > 0)} />
      {evaluation.bookmakers && <Bookmakers comparison={evaluation.bookmakers} />}
      <details className="more-details">
        <summary>
          <span>Detalii statistice</span>
          <span className="caption">Diferențele meci cu meci, unde se descurcă fiecare model, cât de des sunt de acord</span>
        </summary>
        <div className="analysis-stack">
      <section className="card">
        <h2>Diferențele meci cu meci</h2>
        <DataTable
          columns={[
            { label: "Comparație", width: "minmax(170px, 1.5fr)" },
            { label: "Măsură", width: "minmax(0, 1.2fr)", align: "left" },
            { label: "Diferență", width: EVEN },
            { label: "Interval de 95%", width: "minmax(0, 1.4fr)" },
            { label: "Mai bun", width: "minmax(0, 1.2fr)", align: "left" },
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
            <button key={name} className={`pill${breakdown === name ? " chosen" : ""}`} aria-pressed={breakdown === name} onClick={() => setBreakdown(name)}>
              {title}
            </button>
          ))}
        </div>
        <DataTable
          columns={[
            { label: "Categorie", width: "minmax(140px, 1.6fr)" },
            { label: "Meciuri", width: EVEN },
            ...evaluation.compared.map((model) => ({ label: label(model), width: EVEN })),
            { label: "Cel mai bun", width: "minmax(0, 1.3fr)", align: "left" as const },
            { label: "Avantaj real", width: EVEN, align: "center" as const },
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
            { label: "Modele", width: "minmax(170px, 1.6fr)" },
            { label: "Același rezultat prezis", width: EVEN },
            { label: "Distanța medie", width: EVEN },
          ]}
          rows={evaluation.agreements.map((a) => [`${a.first_label} – ${a.second_label}`, percent(a.same), number(a.distance)])}
        />
        {evaluation.all_agree !== null && (
          <p className="caption table-note">Toate cele trei modele prezic același rezultat în {percent(evaluation.all_agree)} dintre meciuri.</p>
        )}
      </section>
        </div>
      </details>
    </div>
  );
}

/** 72,4% · 1.234 (21%): the accuracy among the sure matches, how many and their share. */
function sureCell(found: ConfidentAccuracy | undefined): ReactNode {
  if (!found) return "–"; // a model without probabilities
  if (found.accuracy === null) return <span className="caption">niciun meci</span>;
  return (
    <span className="sure-cell">
      <strong>{percent(found.accuracy)}</strong>
      <small>
        {integer(found.matches)} ({percent(found.share, 0)})
      </small>
    </span>
  );
}

function WhenSure({ models }: { models: ModelEvaluation[] }) {
  if (models.length === 0) return null;
  const thresholds = models[0].confident.map((c) => c.threshold);
  return (
    <section className="card">
      <h2>Când modelul e sigur</h2>
      <DataTable
        columns={[
          { label: "Model", width: "minmax(150px, 1.6fr)" },
          ...thresholds.map((threshold) => ({ label: `Peste ${percent(threshold, 0)}`, width: EVEN })),
        ]}
        rows={models.map((model) => [
          model.label,
          ...thresholds.map((threshold) => sureCell(model.confident.find((c) => c.threshold === threshold))),
        ])}
      />
      <p className="caption table-note">
        Acuratețea pe meciurile în care modelul dădea rezultatului socotit cel mai probabil cel puțin pragul din coloană,
        apoi câte meciuri au fost și ce parte din toate. Cu cât pragul e mai mare, cu atât meciurile sunt mai puține, dar
        mai des nimerite. Un model bine calibrat nimerește pe aceste meciuri cel puțin cât arată pragul.
      </p>
    </section>
  );
}

function Bookmakers({ comparison }: { comparison: BookmakerComparison }) {
  const lowestBrier = Math.min(...comparison.models.map((m) => m.brier ?? Infinity));
  return (
    <section className="card">
      <h2>Față de casele de pariuri</h2>
      <DataTable
        columns={[
          { label: "Model", width: "minmax(150px, 1.6fr)" },
          { label: "Acuratețe", width: EVEN },
          { label: "Scor Brier", width: EVEN },
          { label: "Pierdere logaritmică", width: EVEN },
          { label: `Peste ${percent(SURE, 0)}`, width: EVEN },
        ]}
        rows={comparison.models.filter((model) => model.model === "Bookmakers").map((model) => [
          model.label,
          percent(model.accuracy),
          model.brier === lowestBrier ? <strong className="best">{number(model.brier)}</strong> : number(model.brier),
          number(model.log_loss),
          sureCell(model.confident.find((c) => c.threshold === SURE)),
        ])}
      />
      <DataTable
        columns={[
          { label: "Comparație (scor Brier)", width: "minmax(220px, 2fr)" },
          { label: "Diferență", width: EVEN },
          { label: "Interval de 95%", width: "minmax(0, 1.4fr)" },
          { label: "Mai bun", width: "minmax(0, 1.2fr)", align: "left" },
        ]}
        rows={comparison.differences.map((d) => [
          `${d.first_label} – ${d.second_label}`,
          signed(d.mean),
          `[${signed(d.lower)}; ${signed(d.upper)}]`,
          d.better_label ? <strong className="best">{d.better_label}</strong> : <span className="caption">nicio diferență reală</span>,
        ])}
      />
      <p className="caption table-note">
        Cotele medii ale caselor de pariuri, luate înainte de fiecare meci (Football-Data.co.uk), transformate în
        probabilități fără marja lor. Sunt doar o referință: nu intră în niciun model. Comparația folosește{" "}
        {quantity(comparison.matches, "meci", "meciuri")} cu cote
        {comparison.missing > 0 ? ` (${comparison.missing === 1 ? "un meci nu are" : `${quantity(comparison.missing, "meci", "meciuri")} nu au`})` : ""}; o diferență pozitivă
        înseamnă că modelul greșește mai mult decât casele de pariuri.
      </p>
    </section>
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

  if (error) return <Problem detail={error}>Comparația ligilor nu a putut fi citită. Încearcă din nou.</Problem>;
  if (!comparison) return loading;
  if (comparison.missing.length > 0 || comparison.problem) {
    const names = comparison.missing.map((code) => leagues.find((item) => item.code === code)?.name ?? code).join(", ");
    return (
      <Backtest
        busy={busy}
        onRun={run}
        detail={comparison.problem}
        text={
          comparison.problem
            ? "Rezultatele nu pot fi citite. Rulează din nou backtestul ligilor."
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
  const wins = new Map<string, number>();
  for (const result of comparison.results) wins.set(result.best, (wins.get(result.best) ?? 0) + 1);
  const [best, leaderWins] = [...wins.entries()].sort((a, b) => b[1] - a[1])[0] ?? ["", 0];
  const leader = best ? capitalised(named(best, label(best))) : "";
  const homeWins = comparison.results.map((r) => r.character.home_win);
  const strongest = comparison.results[homeWins.indexOf(Math.max(...homeWins))];
  const weakest = comparison.results[homeWins.indexOf(Math.min(...homeWins))];
  return (
    <div className="analysis-stack">
      {leader && (
        <Finding
          title={
            leaderWins === comparison.results.length
              ? `${leader} are cel mai mic scor Brier în toate cele ${comparison.results.length} ligi`
              : `${leader} are cel mai mic scor Brier în ${leaderWins} din ${comparison.results.length} ligi`
          }
        >
          Ligile diferă mult: gazdele câștigă {percent(strongest.character.home_win, 0)} din meciuri în {strongest.name} și{" "}
          {percent(weakest.character.home_win, 0)} în {weakest.name}. Fiecare ligă își are propriii parametri, aleși pe
          sezoanele ei de calibrare.
        </Finding>
      )}
      <div className="league-cards">
        {comparison.results.map((result) => (
          <button
            key={result.code}
            className={`card league-card${result.code === league.code ? " current" : ""}`}
            onClick={() => onLeague(result.code)}
            aria-pressed={result.code === league.code}
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
          {source.title === "Fotografiile stadioanelor" && (
            <p className="caption">{quantity(about.stadiums, "fotografie", "fotografii")} în aplicație.</p>
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
