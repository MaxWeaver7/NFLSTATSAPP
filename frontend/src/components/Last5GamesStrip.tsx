import { useMemo } from "react";
import { PlayerGameLog } from "@/types/player";
import { TeamLogo } from "./TeamLogo";

interface Last5GamesStripProps {
  gameLogs: PlayerGameLog[];
  position: string;
}

function calcFpts(g: PlayerGameLog): number {
  const pass = (g.passing_yards || 0) * 0.04 + (g.passing_tds || 0) * 4 - (g.interceptions || 0) * 2;
  const rush = (g.rush_yards || 0) * 0.1 + (g.rush_tds || 0) * 6;
  const rec = (g.rec_yards || 0) * 0.1 + (g.rec_tds || 0) * 6 + (g.receptions || 0) * 1;
  return Math.round((pass + rush + rec) * 10) / 10;
}

type ColDef = { key: string; label: string; extract: (g: PlayerGameLog) => number };

function getCols(pos: string): ColDef[] {
  const upper = (pos || "").toUpperCase();
  if (upper === "QB") {
    return [
      { key: "p_yds", label: "YDS", extract: (g) => g.passing_yards || 0 },
      { key: "p_td", label: "TD", extract: (g) => g.passing_tds || 0 },
      { key: "int", label: "INT", extract: (g) => g.interceptions || 0 },
      { key: "r_yds", label: "RUSH YDS", extract: (g) => g.rush_yards || 0 },
      { key: "r_td", label: "RUSH TD", extract: (g) => g.rush_tds || 0 },
      { key: "fpts", label: "FPTS", extract: calcFpts },
    ];
  }
  if (upper === "WR" || upper === "TE") {
    return [
      { key: "tgt", label: "TGT", extract: (g) => g.targets || 0 },
      { key: "rec", label: "REC", extract: (g) => g.receptions || 0 },
      { key: "yds", label: "YDS", extract: (g) => g.rec_yards || 0 },
      { key: "fpts", label: "FPTS", extract: calcFpts },
    ];
  }
  // RB / default
  return [
    { key: "att", label: "ATT", extract: (g) => g.rush_attempts || 0 },
    { key: "yds", label: "YDS", extract: (g) => g.rush_yards || 0 },
    { key: "td", label: "TD", extract: (g) => g.rush_tds || 0 },
    { key: "rec", label: "REC", extract: (g) => g.receptions || 0 },
    { key: "rec_yds", label: "REC YDS", extract: (g) => g.rec_yards || 0 },
    { key: "rec_td", label: "REC TD", extract: (g) => g.rec_tds || 0 },
    { key: "fpts", label: "FPTS", extract: calcFpts },
  ];
}

/** Color FPTS by performance tier */
function fptsColor(pts: number): string {
  if (pts >= 20) return "text-emerald-400";
  if (pts >= 14) return "text-lime-400";
  if (pts >= 8) return "text-amber-400";
  return "text-foreground/40";
}

export function Last5GamesStrip({ gameLogs, position }: Last5GamesStripProps) {
  const cols = getCols(position);

  const games = useMemo(() => {
    if (!gameLogs?.length) return [];
    return gameLogs
      .filter((g) => !g.is_postseason && g.week < 19)
      .sort((a, b) => a.week - b.week)
      .slice(-5);
  }, [gameLogs]);

  const averages = useMemo(() => {
    if (games.length === 0) return cols.map(() => 0);
    return cols.map((col) => {
      const sum = games.reduce((s, g) => s + col.extract(g), 0);
      return Math.round((sum / games.length) * 10) / 10;
    });
  }, [games, cols]);

  if (games.length === 0) return null;

  return (
    <div className="mt-4 rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      <div className="px-3 py-2 border-b border-white/[0.06]">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-foreground/30">Recent Form</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-foreground/25 border-b border-white/[0.04]">
              <th className="text-right py-2 px-3 font-medium whitespace-nowrap">WK</th>
              <th className="text-left py-2 px-3 font-medium">OPP</th>
              {cols.map((col) => (
                <th key={col.key} className="text-right py-2 px-3 font-medium whitespace-nowrap">{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {games.map((game, i) => {
              const isHome = game.location === "home";
              const fpts = calcFpts(game);
              return (
                <tr
                  key={game.game_id}
                  className={`hover:bg-white/[0.04] transition-colors ${i % 2 === 1 ? "bg-white/[0.015]" : ""} ${i < games.length - 1 ? "border-b border-white/[0.03]" : ""}`}
                >
                  <td className="py-2 px-3 text-right font-mono font-semibold text-foreground/40">{game.week}</td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="text-foreground/25 text-[10px] w-3">{isHome ? "vs" : "@"}</span>
                      <TeamLogo team={game.opponent} size="sm" />
                      <span className="font-medium text-foreground/60">{game.opponent}</span>
                    </span>
                  </td>
                  {cols.map((col) => {
                    const val = col.extract(game);
                    const isFpts = col.key === "fpts";
                    return (
                      <td key={col.key} className="py-2 px-3 text-right font-mono tabular-nums">
                        <span className={isFpts ? `font-bold ${fptsColor(fpts)}` : "text-foreground/60"}>
                          {isFpts ? val.toFixed(1) : val}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {/* Average row */}
            <tr className="border-t border-white/[0.08] bg-white/[0.03]">
              <td className="py-2 px-3 text-right font-mono font-bold text-foreground/30">AVG</td>
              <td></td>
              {averages.map((avg, i) => {
                const isFpts = cols[i].key === "fpts";
                return (
                  <td key={cols[i].key} className="py-2 px-3 text-right font-mono font-semibold tabular-nums">
                    <span className={isFpts ? `font-bold ${fptsColor(avg)}` : "text-foreground/40"}>
                      {isFpts ? avg.toFixed(1) : avg % 1 !== 0 ? avg.toFixed(1) : Math.round(avg)}
                    </span>
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
