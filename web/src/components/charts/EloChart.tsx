// A team's Elo rating before each of its matches, one line per season (the window's chart): the
// chosen season in the league's accent and on top, the others thin and grey as its context (the
// Elo blue was too close to Serie A's cyan); gaps are summers and seasons outside the league.
// "Doar sezonul" narrows it to the chosen season.
import { useState } from "react";
import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { dateText, integer, seasonText, shortDateText } from "../../format";
import type { RatingSeason } from "../../types";
import { axisLine, CONTEXT_COLOUR, GRID, tick } from "./chartStyle";

interface Point {
  x: number;
  y: number;
  season: string;
}

function points(season: RatingSeason): Point[] {
  return season.points.map((point) => {
    const [year, month, day] = point.day.split("-").map(Number);
    return { x: new Date(year, month - 1, day).getTime(), y: point.rating, season: season.season };
  });
}

function EloTooltip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{integer(Math.round(point.y))}</strong>
      <span>
        {shortDateText(new Date(point.x))} {new Date(point.x).getFullYear()} · {seasonText(point.season)}
      </span>
    </div>
  );
}

interface Props {
  team: string;
  history: RatingSeason[];
  season: string;
  accent: string;
}

export function EloChart({ team, history, season, accent }: Props) {
  const [onlySeason, setOnlySeason] = useState(false);
  const chosen = history.find((item) => item.season === season);
  const shown = onlySeason && chosen ? [chosen] : [...history.filter((item) => item !== chosen), ...(chosen ? [chosen] : [])];
  const yearOf = (value: number) => String(new Date(value).getFullYear());
  const dayOf = (value: number) => dateText(new Date(value)).slice(0, 5);
  return (
    <div className="chart-box">
      <div className="chart-head">
        <div className="legend">
          {chosen && (
            <span>
              <i style={{ background: accent }} /> {seasonText(season)}
            </span>
          )}
          {!onlySeason && (
            <span>
              <i style={{ background: CONTEXT_COLOUR }} /> Celelalte sezoane
            </span>
          )}
        </div>
        {chosen && (
          <div className="segmented">
            <button className={`pill${onlySeason ? "" : " chosen"}`} onClick={() => setOnlySeason(false)}>
              Toate sezoanele
            </button>
            <button className={`pill${onlySeason ? " chosen" : ""}`} onClick={() => setOnlySeason(true)}>
              Doar sezonul
            </button>
          </div>
        )}
      </div>
      <LineChart
        responsive
        style={{ width: "100%", height: 340 }}
        margin={{ top: 8, right: 12, bottom: 4, left: 0 }}
        accessibilityLayer
        title={`${team}: ratingul Elo înaintea fiecărui meci`}
      >
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis
          type="number"
          dataKey="x"
          scale="time"
          domain={["dataMin", "dataMax"]}
          tickFormatter={onlySeason ? dayOf : yearOf}
          tick={tick}
          axisLine={axisLine}
          tickLine={false}
          minTickGap={24}
        />
        <YAxis
          dataKey="y"
          domain={["auto", "auto"]}
          tickFormatter={(value: number) => integer(Math.round(value))}
          tick={tick}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip content={<EloTooltip />} cursor={{ stroke: GRID }} isAnimationActive={false} />
        {shown.map((item) => {
          const isChosen = item.season === season;
          return (
            <Line
              key={item.season}
              data={points(item)}
              dataKey="y"
              stroke={isChosen ? accent : CONTEXT_COLOUR}
              strokeWidth={isChosen ? 2.6 : 1.4}
              dot={false}
              activeDot={{ r: 4, stroke: "#16161A", strokeWidth: 2 }}
              isAnimationActive={false}
            />
          );
        })}
      </LineChart>
    </div>
  );
}
