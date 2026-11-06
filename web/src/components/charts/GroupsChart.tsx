// A completed season's teams by goals scored and conceded per match, coloured by their K-Means
// group (the groups chart of Phase 12), the group centres as crosses and the chosen team ringed in the
// league's accent and named. The groups come from six values, so a team can sit nearer another
// group's centre on these two axes; the note under the chart says so.
import { CartesianGrid, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { number, teamName } from "../../format";
import type { GroupPoint, Groups } from "../../types";
import { AXIS, axisLine, GRID, GROUP_COLOURS, SURFACE, TEXT, tick } from "./chartStyle";

function GroupTooltip({ active, payload, names }: { active?: boolean; payload?: { payload: GroupPoint }[]; names: Record<string, string> }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{point.team ?? "Centrul grupului"}</strong>
      <span>{names[String(point.group)]}</span>
      <span>
        {number(point.goals_scored, 2)} goluri marcate, {number(point.goals_conceded, 2)} primite pe meci
      </span>
    </div>
  );
}

function Cross({ cx = 0, cy = 0, fill }: { cx?: number; cy?: number; fill?: string }) {
  const size = 7;
  return (
    <path
      d={`M${cx - size},${cy - size}L${cx + size},${cy + size}M${cx + size},${cy - size}L${cx - size},${cy + size}`}
      stroke={fill}
      strokeWidth={3}
      strokeLinecap="round"
    />
  );
}

interface ChosenProps {
  cx?: number;
  cy?: number;
  fill?: string;
  accent: string;
  team: string;
  labelLeft: boolean; // in the right half the name goes on the left, inside the chart
}

function ChosenDot({ cx = 0, cy = 0, fill, accent, team, labelLeft }: ChosenProps) {
  return (
    <g>
      <circle cx={cx} cy={cy} r={12} fill="none" stroke={accent} strokeWidth={2.5} />
      <circle cx={cx} cy={cy} r={6.5} fill={fill} stroke={SURFACE} strokeWidth={1.5} />
      <text
        x={labelLeft ? cx - 18 : cx + 18}
        y={cy + 4}
        textAnchor={labelLeft ? "end" : "start"}
        fill={TEXT}
        fontSize={13}
        fontWeight={700}
      >
        {teamName(team)}
      </text>
    </g>
  );
}

interface Props {
  groups: Groups;
  team: string;
  accent: string;
}

export function GroupsChart({ groups, team, accent }: Props) {
  const order = Object.keys(groups.names).map(Number).sort();
  const chosen = groups.teams.filter((point) => point.team === team);
  const scored = groups.teams.map((point) => point.goals_scored);
  const middle = (Math.min(...scored) + Math.max(...scored)) / 2;
  return (
    <div className="chart-box">
      <div className="chart-head">
        <div className="legend">
          {order.map((group) => (
            <span key={group}>
              <i style={{ background: GROUP_COLOURS[group] }} /> {groups.names[String(group)]}
            </span>
          ))}
          <span>
            <i className="cross" /> Centrul grupului
          </span>
        </div>
      </div>
      <ScatterChart responsive style={{ width: "100%", height: 420 }} margin={{ top: 12, right: 24, bottom: 20, left: 4 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis
          type="number"
          dataKey="goals_scored"
          domain={["auto", "auto"]}
          tickFormatter={(value: number) => number(value, 1)}
          tick={tick}
          axisLine={axisLine}
          tickLine={false}
          label={{ value: "Goluri marcate pe meci", position: "insideBottom", offset: -14, fill: AXIS, fontSize: 12 }}
        />
        <YAxis
          type="number"
          dataKey="goals_conceded"
          domain={["auto", "auto"]}
          tickFormatter={(value: number) => number(value, 1)}
          tick={tick}
          axisLine={false}
          tickLine={false}
          width={56}
          label={{ value: "Goluri primite pe meci", angle: -90, position: "insideLeft", offset: 10, fill: AXIS, fontSize: 12 }}
        />
        <ZAxis range={[100, 100]} />
        <Tooltip content={<GroupTooltip names={groups.names} />} cursor={false} isAnimationActive={false} />
        {order.map((group) => (
          <Scatter
            key={`centre-${group}`}
            data={groups.centres.filter((centre) => centre.group === group)}
            fill={GROUP_COLOURS[group]}
            shape={<Cross />}
            isAnimationActive={false}
          />
        ))}
        {order.map((group) => (
          <Scatter
            key={group}
            data={groups.teams.filter((point) => point.group === group && point.team !== team)}
            fill={GROUP_COLOURS[group]}
            stroke={SURFACE}
            strokeWidth={1.5}
            isAnimationActive={false}
          />
        ))}
        {chosen.length > 0 && (
          <Scatter
            data={chosen}
            fill={GROUP_COLOURS[chosen[0].group]}
            shape={<ChosenDot accent={accent} team={team} labelLeft={chosen[0].goals_scored > middle} />}
            isAnimationActive={false}
          />
        )}
      </ScatterChart>
    </div>
  );
}
