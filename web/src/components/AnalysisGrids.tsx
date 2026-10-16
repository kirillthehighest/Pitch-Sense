// Two pictures of Analiză drawn as grids: a model's confusion matrix (matches by the result that
// happened and the one predicted, each cell in the league's accent by its count) and the home
// teams' wins with fans and in 2020/21, mostly behind closed doors, league by league.
import { integer, percent } from "../format";
import type { LeagueResult } from "../types";
import { cellColours } from "./ScoreGrid";

const OUTCOMES = ["Victorie gazde", "Egal", "Victorie oaspeți"];
const WITH_FANS = "#4D8DFF";
const CLOSED_DOORS = "#EF5A6F"; // a pair validated for colour-blind readers (palette.py)

export function ConfusionGrid({ matrix, accent }: { matrix: number[][]; accent: string }) {
  const largest = Math.max(1, ...matrix.flat());
  return (
    <div className="confusion">
      <span className="confusion-corner caption">Real ↓ · Prezis →</span>
      {OUTCOMES.map((name) => (
        <span key={`head-${name}`} className="confusion-head">
          {name}
        </span>
      ))}
      {matrix.map((row, actual) => {
        const total = row.reduce((sum, count) => sum + count, 0) || 1;
        return [
          <span key={`row-${actual}`} className="confusion-head row">
            {OUTCOMES[actual]}
          </span>,
          ...row.map((count, predicted) => {
            const [fill, ink] = cellColours(count, largest, accent);
            return (
              <span key={`${actual}-${predicted}`} className="confusion-cell" style={{ background: fill, color: ink }}>
                <strong>{integer(count)}</strong>
                <small>{percent(count / total, 0)}</small>
              </span>
            );
          }),
        ];
      })}
    </div>
  );
}

export function HomeAdvantage({ results }: { results: LeagueResult[] }) {
  const shown = results.filter(
    (result) => result.character.closed_doors_home_win !== null && result.character.other_seasons_home_win !== null,
  );
  if (shown.length === 0) return <p className="caption">Nicio ligă nu are atât sezonul 2020/21, cât și altele.</p>;
  const values = shown.flatMap((r) => [r.character.closed_doors_home_win as number, r.character.other_seasons_home_win as number]);
  const low = Math.floor(Math.min(...values) * 20) / 20; // to the 5% below
  const high = Math.ceil(Math.max(...values) * 20) / 20;
  const position = (value: number) => `${(100 * (value - low)) / (high - low || 1)}%`;
  return (
    <div className="dumbbells">
      <div className="legend">
        <span>
          <i style={{ background: WITH_FANS }} /> Celelalte sezoane
        </span>
        <span>
          <i style={{ background: CLOSED_DOORS }} /> 2020/21
        </span>
      </div>
      {shown.map((result) => {
        const fans = result.character.other_seasons_home_win as number;
        const closed = result.character.closed_doors_home_win as number;
        return (
          <div key={result.code} className="dumbbell">
            <span className="dumbbell-name">{result.name}</span>
            <span className="dumbbell-track">
              <span
                className="dumbbell-line"
                style={{ left: position(Math.min(fans, closed)), right: `calc(100% - ${position(Math.max(fans, closed))})` }}
              />
              <i style={{ left: position(fans), background: WITH_FANS }} title={`Celelalte sezoane: ${percent(fans)}`} />
              <i style={{ left: position(closed), background: CLOSED_DOORS }} title={`2020/21: ${percent(closed)}`} />
            </span>
            <span className="dumbbell-values">
              {percent(fans, 0)} → {percent(closed, 0)}
            </span>
          </div>
        );
      })}
      <div className="dumbbell-axis caption">
        <span>{percent(low, 0)}</span>
        <span>Meciuri câștigate de gazde</span>
        <span>{percent(high, 0)}</span>
      </div>
    </div>
  );
}
