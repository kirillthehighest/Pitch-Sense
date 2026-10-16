// The charts of Analiză drawn with Recharts (the calibration and skill charts of Phases 12 and 15): every
// model keeps its identity colour, the reference is grey and dashed, text stays in the text
// colours, and each chart has its legend.
import { Bar, BarChart, CartesianGrid, ReferenceLine, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { integer, percent } from "../../format";
import { MODEL_COLOURS } from "../../theme";
import type { LeagueResult, ModelEvaluation } from "../../types";
import { MODEL_LABELS } from "../../types";
import { AXIS, axisLine, BASELINE_COLOUR, GRID, SURFACE, tick } from "./chartStyle";

const share = (value: number) => percent(value, 0);
const colourOf = (model: string) => MODEL_COLOURS[model] ?? BASELINE_COLOUR;

interface CalibrationPoint {
  x: number;
  y: number;
  count: number;
  model: string;
}

function CalibrationTooltip({ active, payload }: { active?: boolean; payload?: { payload: CalibrationPoint }[] }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{MODEL_LABELS[point.model] ?? point.model}</strong>
      <span>
        A spus în medie {percent(point.x)}; s-a întâmplat {percent(point.y)}
      </span>
      <span>{integer(point.count)} probabilități în interval</span>
    </div>
  );
}

/** Predicted probability against observed frequency, pooled over the three outcomes. */
export function CalibrationChart({ models, labels }: { models: ModelEvaluation[]; labels: Record<string, string> }) {
  const shown = models.filter((model) => model.calibration);
  return (
    <div className="chart-box">
      <div className="legend">
        {shown.map((model) => (
          <span key={model.model}>
            <i style={{ background: colourOf(model.model) }} /> {labels[model.model] ?? model.label}
          </span>
        ))}
        <span>
          <i style={{ background: AXIS }} /> Calibrare perfectă
        </span>
      </div>
      <ScatterChart responsive style={{ width: "100%", height: 380 }} margin={{ top: 8, right: 16, bottom: 22, left: 4 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis
          type="number"
          dataKey="x"
          domain={[0, 1]}
          ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          tickFormatter={share}
          tick={tick}
          axisLine={axisLine}
          tickLine={false}
          label={{ value: "Probabilitatea prezisă", position: "insideBottom", offset: -14, fill: AXIS, fontSize: 12 }}
        />
        <YAxis
          type="number"
          dataKey="y"
          domain={[0, 1]}
          ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          tickFormatter={share}
          tick={tick}
          axisLine={false}
          tickLine={false}
          width={52}
          label={{ value: "Frecvența observată", angle: -90, position: "insideLeft", offset: 10, fill: AXIS, fontSize: 12 }}
        />
        <ReferenceLine
          segment={[
            { x: 0, y: 0 },
            { x: 1, y: 1 },
          ]}
          stroke={AXIS}
          strokeWidth={1}
        />
        <Tooltip content={<CalibrationTooltip />} cursor={false} isAnimationActive={false} />
        {shown.map((model) => {
          const reference = !MODEL_COLOURS[model.model];
          const points: CalibrationPoint[] = (model.calibration ?? [])
            .filter((bin) => bin.count > 0 && bin.predicted !== null && bin.observed !== null)
            .map((bin) => ({ x: bin.predicted as number, y: bin.observed as number, count: bin.count, model: model.model }));
          return (
            <Scatter
              key={model.model}
              data={points}
              fill={colourOf(model.model)}
              stroke={SURFACE}
              strokeWidth={1.5}
              line={{ stroke: colourOf(model.model), strokeWidth: 2, strokeDasharray: reference ? "5 4" : undefined }}
              isAnimationActive={false}
            />
          );
        })}
      </ScatterChart>
    </div>
  );
}

function SkillTooltip({ active, payload, label }: { active?: boolean; payload?: { dataKey: string; value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {payload.map((item) => (
        <span key={item.dataKey}>
          {MODEL_LABELS[item.dataKey] ?? item.dataKey}: {percent(item.value)}
        </span>
      ))}
    </div>
  );
}

/** How much of the reference's Brier score each model removes, league by league. */
export function SkillChart({ results, models }: { results: LeagueResult[]; models: string[] }) {
  const data = results.map((result) => ({ league: result.name, ...result.skill }));
  return (
    <div className="chart-box">
      <div className="legend">
        {models.map((model) => (
          <span key={model}>
            <i style={{ background: colourOf(model) }} /> {MODEL_LABELS[model] ?? model}
          </span>
        ))}
      </div>
      <BarChart
        responsive
        layout="vertical"
        data={data}
        style={{ width: "100%", height: 64 * results.length + 40 }}
        margin={{ top: 4, right: 16, bottom: 4, left: 0 }}
        barGap={3}
        barCategoryGap="22%"
      >
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" tickFormatter={(value: number) => percent(value, 0)} tick={tick} axisLine={axisLine} tickLine={false} />
        <YAxis type="category" dataKey="league" tick={{ ...tick, fill: "#F5F5F7" }} axisLine={false} tickLine={false} width={116} />
        <Tooltip content={<SkillTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} isAnimationActive={false} />
        {models.map((model) => (
          <Bar key={model} dataKey={model} fill={colourOf(model)} radius={[0, 4, 4, 0]} isAnimationActive={false} />
        ))}
      </BarChart>
    </div>
  );
}
