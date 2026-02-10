import { useMemo, useId } from "react";
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { PlayerGameLog } from "@/types/player";

interface SeasonTrendChartsProps {
  gameLogs: PlayerGameLog[];
  position: string;
  teamColor: string;
}

/** PPR fantasy points from a single game log */
function fantasyPts(g: PlayerGameLog): number {
  let pts = 0;
  // Passing
  pts += (g.passing_yards || 0) * 0.04;
  pts += (g.passing_tds || 0) * 4;
  pts -= (g.interceptions || 0) * 2;
  // Rushing
  pts += (g.rush_yards || 0) * 0.1;
  pts += (g.rush_tds || 0) * 6;
  // Receiving (PPR)
  pts += (g.receptions || 0) * 1;
  pts += (g.rec_yards || 0) * 0.1;
  pts += (g.rec_tds || 0) * 6;
  return Math.round(pts * 10) / 10;
}

type ChartDef = { key: string; label: string; extract: (g: PlayerGameLog) => number; unit: string };

function getChartDefs(pos: string): ChartDef[] {
  const upper = (pos || "").toUpperCase();
  if (upper === "QB") {
    return [
      { key: "pass_yds", label: "Pass Yards", extract: (g) => g.passing_yards || 0, unit: "yds" },
      { key: "pass_td", label: "Pass TDs", extract: (g) => g.passing_tds || 0, unit: "TD" },
      { key: "fpts", label: "Fantasy Pts", extract: (g) => fantasyPts(g), unit: "pts" },
    ];
  }
  if (upper === "WR" || upper === "TE") {
    return [
      { key: "rec_yds", label: "Rec Yards", extract: (g) => g.rec_yards || 0, unit: "yds" },
      { key: "tgt", label: "Targets", extract: (g) => g.targets || 0, unit: "tgt" },
      { key: "fpts", label: "Fantasy Pts", extract: (g) => fantasyPts(g), unit: "pts" },
    ];
  }
  // RB / default
  return [
    { key: "rush_yds", label: "Rush Yards", extract: (g) => g.rush_yards || 0, unit: "yds" },
    { key: "rush_td", label: "Rush TDs", extract: (g) => g.rush_tds || 0, unit: "TD" },
    { key: "fpts", label: "Fantasy Pts", extract: (g) => fantasyPts(g), unit: "pts" },
  ];
}

export function SeasonTrendCharts({ gameLogs, position, teamColor }: SeasonTrendChartsProps) {
  const defs = getChartDefs(position);

  const games = useMemo(() => {
    if (!gameLogs?.length) return [];
    return gameLogs
      .filter((g) => !g.is_postseason && g.week < 19)
      .sort((a, b) => a.week - b.week)
      .slice(-10);
  }, [gameLogs]);

  if (games.length < 2) return null;

  return (
    <div className="grid grid-cols-3 gap-3 mt-4">
      {defs.map((def) => (
        <MiniTrend
          key={def.key}
          label={def.label}
          unit={def.unit}
          data={games.map((g) => ({ week: g.week, value: def.extract(g) }))}
          color={teamColor}
        />
      ))}
    </div>
  );
}

function MiniTrend({
  label,
  unit,
  data,
  color,
}: {
  label: string;
  unit: string;
  data: { week: number; value: number }[];
  color: string;
}) {
  const reactId = useId();
  const gradId = `trend-${reactId}-${label}`.replace(/:/g, "").replace(/\s/g, "");
  const avg = data.reduce((s, d) => s + d.value, 0) / data.length;

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.[0]) return null;
    const { value, week } = payload[0].payload;
    return (
      <div className="bg-black/90 backdrop-blur text-white text-[10px] rounded-md px-2 py-1 shadow-lg border border-white/10">
        <span className="font-mono font-bold">{value} {unit}</span>
        <span className="text-white/50 ml-1.5">Wk {week}</span>
      </div>
    );
  };

  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5 overflow-hidden">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">{label}</span>
        <span className="text-[10px] font-mono text-foreground/50">{avg.toFixed(unit === "pts" ? 1 : 0)} avg</span>
      </div>
      <div style={{ width: "100%", height: 48 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: 2 }}>
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color || "#10b981"} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color || "#10b981"} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="week" hide />
            <Tooltip content={<CustomTooltip />} cursor={false} />
            <Area
              type="monotone"
              dataKey="value"
              stroke={color || "#10b981"}
              strokeWidth={2}
              fill={`url(#${gradId})`}
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
