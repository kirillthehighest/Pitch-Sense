// The Poisson probability of every score from 0–0 to 6–6, drawn as a grid:
// home goals down, away goals across; each cell mixes the chosen league's accent into the card by its
// share of the most likely score, and its number takes the ink that reads on it. Once the match is
// played, the score that happened is ringed (Phase 25).
import { inkOn, mix } from "../colour";
import { percent } from "../format";

const CELL_BASE = "#1E1E23"; // the raised surface: an unlikely score almost disappears
const FAINTEST = 0.04;

export function cellColours(probability: number, largest: number, accent: string): [string, string] {
  const share = FAINTEST + (1 - FAINTEST) * (probability / largest);
  const fill = mix(CELL_BASE, accent, share);
  return [fill, inkOn(fill, "#FFFFFF", "#000000")]; // pure inks: readable on every mid-tone
}

/** 12%, 8,7%, or <0,1% for a score too rare to write with one decimal. */
export function cellText(probability: number): string {
  if (probability < 0.0005) return "<0,1%";
  return percent(probability, 1); // one decimal, as the list of likely scores beside the grid
}

interface Props {
  grid: number[][];
  home: string;
  away: string;
  accent: string;
  actual?: [number, number] | null; // the final score, once played
}

export function ScoreGrid({ grid, home, away, accent, actual = null }: Props) {
  const largest = Math.max(...grid.flat());
  const goals = grid.map((_, index) => index);
  return (
    <div className="score-grid-box">
      <div className="score-grid-away caption">Goluri {away} (oaspeți) →</div>
      <div className="score-grid-body">
        <div className="score-grid-home caption">Goluri {home} (gazde) →</div>
        <div className="score-grid" style={{ gridTemplateColumns: `22px repeat(${goals.length}, minmax(0, 1fr))` }}>
          <span />
          {goals.map((goal) => (
            <span key={`away-${goal}`} className="axis">
              {goal}
            </span>
          ))}
          {grid.map((row, homeGoals) => (
            <Row
              key={homeGoals}
              row={row}
              homeGoals={homeGoals}
              largest={largest}
              accent={accent}
              actualAway={actual && actual[0] === homeGoals ? actual[1] : null}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function Row({
  row, homeGoals, largest, accent, actualAway,
}: { row: number[]; homeGoals: number; largest: number; accent: string; actualAway: number | null }) {
  return (
    <>
      <span className="axis">{homeGoals}</span>
      {row.map((probability, awayGoals) => {
        const [fill, ink] = cellColours(probability, largest, accent);
        return (
          <span
            key={awayGoals}
            className={`cell${actualAway === awayGoals ? " actual" : ""}`}
            style={{ background: fill, color: ink }}
            title={`${homeGoals}–${awayGoals}: ${percent(probability)}${actualAway === awayGoals ? " · scorul final" : ""}`}
          >
            {cellText(probability)}
          </span>
        );
      })}
    </>
  );
}
