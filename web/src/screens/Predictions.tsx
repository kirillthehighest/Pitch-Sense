// Predicții (the team's request after Phase 21): what a model predicted for a season's played
// matches and what happened. The matches it got right, those it missed, and the surprises: results
// it gave less than a fifth of a chance. Every prediction was made before its match, from earlier
// matches only. Since Phase 23 it also tells how often the model was right when it was sure; since
// Phase 25 the latest matches come week by week, each week with its hits, and only surprises carry
// a badge (the chip's mark already says hit or miss).
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useChosenModel } from "../chosenModel";
import { ColumnsHead, MatchRow } from "../components/MatchRow";
import { Problem } from "../components/Problem";
import { usePageKeys } from "../components/Shortcuts";
import { SkeletonCard, SkeletonRows } from "../components/Skeleton";
import { integer, isoDay, MONTHS, parseDay, percent, quantity, seasonText } from "../format";
import { nextModel } from "./Matches";
import type { Forecast, League, Review, ReviewedMatch } from "../types";
import { MODEL_LABELS, MODELS } from "../types";

type Kind = "all" | "hits" | "misses" | "surprises" | "sure";
type Order = "recent" | "surprising" | "confident";

const PAGE = 40;
export const SURE = 0.65; // a sure prediction gives its most likely result at least this much

export function chosenRows(rows: ReviewedMatch[], kind: Kind, order: Order): ReviewedMatch[] {
  const kept = rows.filter(
    (row) =>
      kind === "all" ||
      (kind === "hits" && row.hit) ||
      (kind === "misses" && !row.hit) ||
      (kind === "surprises" && row.surprise) ||
      (kind === "sure" && row.confidence >= SURE),
  );
  if (order === "surprising") return [...kept].sort((a, b) => a.chance - b.chance);
  if (order === "confident") return [...kept].sort((a, b) => b.confidence - a.confidence);
  return [...kept].reverse(); // the latest first
}

/** The Monday of a day's week (ISO), the key of its group. */
export function weekOf(day: string): string {
  const moment = parseDay(day);
  moment.setDate(moment.getDate() - ((moment.getDay() + 6) % 7));
  return isoDay(moment);
}

/** "27 oct – 2 nov": a week from its Monday. */
export function weekText(monday: string): string {
  const first = parseDay(monday);
  const last = new Date(first);
  last.setDate(last.getDate() + 6);
  const text = (day: Date) => `${day.getDate()} ${MONTHS[day.getMonth()]}`;
  return `${text(first)} – ${text(last)}`;
}

export interface Week {
  monday: string;
  rows: ReviewedMatch[];
  hits: number;
}

/** Consecutive rows of the same week together, in the rows' order. */
export function byWeek(rows: ReviewedMatch[]): Week[] {
  const weeks: Week[] = [];
  for (const row of rows) {
    const monday = weekOf(row.forecast.date);
    const last = weeks[weeks.length - 1];
    if (last && last.monday === monday) {
      last.rows.push(row);
      last.hits += row.hit ? 1 : 0;
    } else weeks.push({ monday, rows: [row], hits: row.hit ? 1 : 0 });
  }
  return weeks;
}

interface Props {
  league: League;
  season: string;
  favourite: string | null;
  ready: string;
  onSeason: (season: string) => void;
  onOpenMatch: (forecast: Forecast) => void;
  active: boolean; // false under a match page
}

export function Predictions({ league, season, favourite, ready, onSeason, onOpenMatch, active }: Props) {
  const [model, setModel] = useChosenModel(); // one choice for every screen
  const [kind, setKind] = useState<Kind>("all");
  const [order, setOrder] = useState<Order>("recent");
  const [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shown, setShown] = useState(PAGE);
  usePageKeys((key) => {
    if (active && (key === "m" || key === "M")) setModel(nextModel); // not under a match page
  });

  useEffect(() => {
    let live = true;
    setError(null);
    if (!league.prepared) return;
    api
      .review(league.code, season, model)
      .then((found) => live && setReview(found))
      .catch((reason: Error) => live && setError(reason.message));
    return () => {
      live = false;
    };
  }, [league.code, league.prepared, season, model, ready]);

  useEffect(() => setShown(PAGE), [league.code, season, model, kind, order]);

  const rows = useMemo(() => (review ? chosenRows(review.rows, kind, order) : []), [review, kind, order]);
  const counts: [Kind, string, number][] = review
    ? [
        ["all", "Toate", review.matches],
        ["hits", "Nimerite", review.hits],
        ["misses", "Ratate", review.matches - review.hits],
        ["surprises", "Surprize", review.surprises],
        ["sure", `Sigure (peste ${percent(SURE, 0)})`, review.sure.find((s) => s.threshold === SURE)?.matches ?? 0],
      ]
    : [];

  return (
    <div className="predictions-screen">
      <div className="control-row">
        <label className="caption" htmlFor="review-season">
          Sezon
        </label>
        <select id="review-season" value={season} onChange={(event) => onSeason(event.target.value)}>
          {[...league.seasons].reverse().map((item) => (
            <option key={item} value={item}>
              {seasonText(item)}
            </option>
          ))}
        </select>
        <label className="caption" htmlFor="review-model">
          Model
        </label>
        <select id="review-model" value={model} onChange={(event) => setModel(event.target.value)} aria-keyshortcuts="M">
          {MODELS.map((item) => (
            <option key={item} value={item}>
              {MODEL_LABELS[item]}
            </option>
          ))}
        </select>
      </div>
      {(!league.prepared || (!review && !error)) && (
        <>
          <div className="review-summary">
            <SkeletonCard height={110} />
            <SkeletonCard height={110} />
          </div>
          <section className="card review-list">
            <SkeletonRows rows={6} label="Se pregătesc predicțiile…" />
          </section>
        </>
      )}
      {error && (
        <Problem detail={error}>Predicțiile sezonului nu au putut fi citite. Alege alt sezon sau încearcă mai târziu.</Problem>
      )}
      {review && review.matches === 0 && (
        <p className="caption">
          Modelul nu are predicții pentru meciurile acestui sezon: are nevoie de meciuri anterioare din care să învețe.
        </p>
      )}
      {review && review.matches > 0 && (
        <>
          <div className="review-summary">
            <section className="card review-score">
              <h2>Bilanțul modelului</h2>
              <div className="big-number">
                <strong>{percent(review.hits / review.matches, 0)}</strong>
                <span>
                  {integer(review.hits)} nimerite din {quantity(review.matches, "meci jucat", "meciuri jucate")}
                </span>
              </div>
              <HomeReference review={review} />
              <p className="caption">
                Un meci e nimerit când s-a întâmplat rezultatul pe care modelul îl considera cel mai probabil. Surpriză
                înseamnă un rezultat căruia modelul îi dădea sub {percent(review.surprise_chance, 0)}; au fost{" "}
                {integer(review.surprises)}.
              </p>
            </section>
            <section className="card review-results">
              <h2>După rezultatul meciului</h2>
              {review.by_result.map((result) => (
                <div key={result.result} className="result-line">
                  <span>{result.label}</span>
                  <span className="track">
                    <span style={{ width: result.matches ? `${(100 * result.hits) / result.matches}%` : 0 }} />
                  </span>
                  <strong>{result.matches ? percent(result.hits / result.matches, 0) : "–"}</strong>
                  <span className="caption">
                    {result.hits} din {result.matches}
                  </span>
                </div>
              ))}
              <p className="caption">Din meciurile terminate așa, câte a ghicit modelul.</p>
              <DrawNote review={review} />
            </section>
            <WhenSure review={review} />
          </div>
          <div className="control-row">
            {counts.map(([name, label, count]) => (
              <button key={name} className={`pill${kind === name ? " chosen" : ""}`} aria-pressed={kind === name} onClick={() => setKind(name)}>
                {label} <span className="count">{integer(count)}</span>
              </button>
            ))}
            <span className="grow" />
            <label className="caption" htmlFor="review-order">
              Ordine
            </label>
            <select id="review-order" value={order} onChange={(event) => setOrder(event.target.value as Order)}>
              <option value="recent">Cele mai recente</option>
              <option value="surprising">Cele mai mari surprize</option>
              <option value="confident">Cele mai sigure predicții</option>
            </select>
          </div>
          <section className="card review-list">
            <ColumnsHead extra />
            {order === "recent" ? (
              byWeek(rows.slice(0, shown)).map((week) => (
                <div key={week.monday} className="week">
                  <h3 className="week-head">
                    <span>{weekText(week.monday)}</span>
                    <span className="caption">
                      {week.hits} din {week.rows.length} nimerite
                    </span>
                  </h3>
                  <div className="match-list">
                    {week.rows.map((row) => (
                      <ReviewRow key={`${row.forecast.date}-${row.forecast.home_team}`} row={row} model={model} favourite={favourite} onOpen={onOpenMatch} />
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div className="match-list">
                {rows.slice(0, shown).map((row) => (
                  <ReviewRow key={`${row.forecast.date}-${row.forecast.home_team}`} row={row} model={model} favourite={favourite} onOpen={onOpenMatch} />
                ))}
              </div>
            )}
            {rows.length === 0 && <p className="caption">Niciun meci de acest fel.</p>}
            {rows.length > shown && (
              <button className="button more" onClick={() => setShown(shown + PAGE)}>
                Arată încă {Math.min(PAGE, rows.length - shown)} din {integer(rows.length - shown)}
              </button>
            )}
          </section>
        </>
      )}
    </div>
  );
}

const FEW = 30; // fewer matches than this: a share that can still swing a lot

/** The simplest guess to compare with: always the home side, right in every home win. */
function HomeReference({ review }: { review: Review }) {
  const home = review.by_result.find((result) => result.result === "H");
  if (!home) return null;
  return (
    <p className="review-reference">
      Pentru comparație: cine ar alege mereu victoria gazdelor ar nimeri {percent(home.matches / review.matches, 0)}.
    </p>
  );
}

function WhenSure({ review }: { review: Review }) {
  return (
    <section className="card review-sure">
      <h2>Când modelul era sigur</h2>
      <div className="sure-tiles">
        {review.sure.map((sure) => (
          <div
            key={sure.threshold}
            className={`sure-tile${sure.threshold === SURE ? " chosen" : ""}${sure.matches < FEW ? " few" : ""}`}
          >
            <span className="caption">Peste {percent(sure.threshold, 0)}</span>
            <strong>{sure.matches ? percent(sure.hits / sure.matches, 0) : "–"}</strong>
            <span className="caption">
              {integer(sure.hits)} din {quantity(sure.matches, "meci", "meciuri")}
              {sure.matches > 0 && sure.matches < FEW && " · puține"}
            </span>
          </div>
        ))}
      </div>
      <p className="caption">
        Cât de des a nimerit modelul când era sigur pe el: „Peste 65%” înseamnă meciurile în care favoritul lui avea cel
        puțin 65% șansă. De obicei, cu cât e mai sigur, cu atât greșește mai rar.
        {review.sure.some((sure) => sure.matches > 0 && sure.matches < FEW) &&
          " Sub 30 de meciuri, procentul e doar orientativ."}
      </p>
    </section>
  );
}

function ReviewRow({
  row, model, favourite, onOpen,
}: { row: ReviewedMatch; model: string; favourite: string | null; onOpen: (forecast: Forecast) => void }) {
  return (
    <MatchRow
      forecast={row.forecast}
      model={model}
      favourite={favourite}
      showDate
      onOpen={onOpen}
      extra={
        row.surprise ? (
          <span className="verdict-badge surprise" title="Rezultatul avea o șansă mică în predicție">
            Surpriză · {percent(row.chance, 0)}
          </span>
        ) : (
          <span />
        )
      }
    />
  );
}

/** Why the draws are missed: the most likely result is almost never a draw. */
function DrawNote({ review }: { review: Review }) {
  const draws = review.by_result.find((result) => result.result === "D");
  if (!draws || draws.matches === 0 || draws.hits / draws.matches > 0.1) return null;
  return (
    <p className="caption draw-note">
      Egalul iese rar favorit: chiar și într-un meci echilibrat, o victorie are de obicei o șansă puțin mai mare. Șansa
      egalului apare totuși în fiecare predicție.
    </p>
  );
}
