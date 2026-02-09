import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { usePlayerDetail, useInjuries, type RankedStat, type SnapWeek } from "@/hooks/useApi";
import { getTeamColors } from "@/config/nfl-teams";
import { TeamLogo } from "@/components/TeamLogo";
import { ArrowLeft, Activity, Calendar, BarChart3, ChevronDown } from "lucide-react";
import { cn, ensureReadableColor } from "@/lib/utils";
import {
  type BubbleStat, type GameLogColumn,
  QB_SEASON_BUBBLES, RB_SEASON_BUBBLES, WR_SEASON_BUBBLES, TE_SEASON_BUBBLES,
  QB_GAME_LOG_COLS, RB_GAME_LOG_COLS, WR_GAME_LOG_COLS, TE_GAME_LOG_COLS,
  DEF_GAME_LOG_COLS, KP_GAME_LOG_COLS,
  ADVANCED_STAT_TOOLTIPS,
} from "@/config/advanced-stats-config";
import type { PlayerGameLog } from "@/types/player";

// ─── Position Helpers ────────────────────────────────────────────────

const DEF_POSITIONS = new Set([
  "DL", "LB", "CB", "S", "DB", "DE", "DT", "EDGE", "ILB", "OLB", "FS", "SS",
]);
const KP_POSITIONS = new Set(["K", "P"]);

type PosGroup = "QB" | "RB" | "WR" | "TE" | "DEF" | "KP";

function getPosGroup(pos: string | null | undefined): PosGroup {
  if (!pos) return "DEF";
  const p = pos.toUpperCase();
  if (p === "QB") return "QB";
  if (p === "RB" || p === "FB") return "RB";
  if (p === "WR") return "WR";
  if (p === "TE") return "TE";
  if (DEF_POSITIONS.has(p)) return "DEF";
  if (KP_POSITIONS.has(p)) return "KP";
  return "DEF";
}

function getBubbles(group: PosGroup): BubbleStat[] {
  switch (group) {
    case "QB": return QB_SEASON_BUBBLES;
    case "RB": return RB_SEASON_BUBBLES;
    case "WR": return WR_SEASON_BUBBLES;
    case "TE": return TE_SEASON_BUBBLES;
    default: return [];
  }
}

function getGameLogCols(group: PosGroup): GameLogColumn[] {
  switch (group) {
    case "QB": return QB_GAME_LOG_COLS;
    case "RB": return RB_GAME_LOG_COLS;
    case "WR": return WR_GAME_LOG_COLS;
    case "TE": return TE_GAME_LOG_COLS;
    case "DEF": return DEF_GAME_LOG_COLS;
    case "KP": return KP_GAME_LOG_COLS;
  }
}

// ─── Injury Badge ────────────────────────────────────────────────────

function getInjuryBadge(status: string | null | undefined) {
  if (!status) return null;
  const n = status.toLowerCase().trim();
  if (n === "out") return { label: "OUT", bg: "bg-red-500/20", text: "text-red-400", border: "border-red-500/40" };
  if (n === "doubtful") return { label: "DOUBT", bg: "bg-orange-500/20", text: "text-orange-400", border: "border-orange-500/40" };
  if (n === "questionable") return { label: "Q", bg: "bg-amber-500/20", text: "text-amber-400", border: "border-amber-500/40" };
  if (n === "probable") return { label: "PROB", bg: "bg-yellow-500/20", text: "text-yellow-400", border: "border-yellow-500/40" };
  if (n === "injured reserve" || n === "ir") return { label: "IR", bg: "bg-slate-500/30", text: "text-slate-300", border: "border-slate-500/50" };
  return { label: status.slice(0, 4).toUpperCase(), bg: "bg-gray-500/20", text: "text-gray-400", border: "border-gray-500/40" };
}

// ─── Formatting ──────────────────────────────────────────────────────

function fmtVal(v: number | null | undefined, format: "int" | "float" | "pct"): string {
  if (v == null) return "—";
  if (format === "int") return Math.round(v).toLocaleString();
  if (format === "pct") {
    // Values <= 1.0 are 0-1 scale, otherwise already 0-100
    const pct = v <= 1.0 ? v * 100 : v;
    return pct.toFixed(1) + "%";
  }
  // float: show 1–2 decimal places
  return Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(2);
}

// ─── Rank Badge ──────────────────────────────────────────────────────

function rankColor(rank: number, total: number, higher_is_better: boolean): string {
  // For "lower is better" stats (INT, TTT), invert the ranking
  const effectiveRank = higher_is_better ? rank : total - rank + 1;
  const pct = effectiveRank / total;
  if (pct <= 0.1) return "text-emerald-400 bg-emerald-500/20 border-emerald-500/30";
  if (pct <= 0.25) return "text-lime-400 bg-lime-500/15 border-lime-500/25";
  if (pct <= 0.5) return "text-amber-400 bg-amber-500/15 border-amber-500/25";
  if (pct <= 0.75) return "text-orange-400 bg-orange-500/15 border-orange-500/25";
  return "text-red-400 bg-red-500/15 border-red-500/25";
}

// ─── Hero Key Stats ──────────────────────────────────────────────────

function getHeroStats(group: PosGroup, player: any): { label: string; value: string }[] {
  const st = player.seasonTotals || {};
  switch (group) {
    case "QB":
      return [
        { label: "Pass YDS", value: (st.passingYards || 0).toLocaleString() },
        { label: "Pass TD", value: String(st.passingTouchdowns || 0) },
        { label: "INT", value: String(st.passingInterceptions || 0) },
      ];
    case "RB":
      return [
        { label: "Rush YDS", value: (st.rushingYards || 0).toLocaleString() },
        { label: "Rush TD", value: String(st.rushingTouchdowns || 0) },
        { label: "Scrimmage", value: ((st.rushingYards || 0) + (st.receivingYards || 0)).toLocaleString() },
      ];
    case "WR":
    case "TE":
      return [
        { label: "Rec YDS", value: (st.receivingYards || 0).toLocaleString() },
        { label: "REC", value: String(st.receptions || 0) },
        { label: "Rec TD", value: String(st.receivingTouchdowns || 0) },
      ];
    default:
      return [
        { label: "Games", value: String(st.games || player.games || 0) },
      ];
  }
}

// ─── StatBubble Component ────────────────────────────────────────────

function StatBubble({
  stat,
  value,
  ranking,
}: {
  stat: BubbleStat;
  value: number | null | undefined;
  ranking?: RankedStat;
  teamColor: string;
}) {
  const tooltip = ADVANCED_STAT_TOOLTIPS[stat.key] || stat.label;

  return (
    <div
      className="relative group flex flex-col items-center justify-center rounded-xl border border-white/8 bg-white/[0.03] px-3 py-3 min-w-[90px] hover:bg-white/[0.06] transition-colors"
      title={tooltip}
    >
      {/* Label */}
      <div className="text-[10px] font-semibold uppercase tracking-wider text-foreground/40 mb-1">
        {stat.label}
      </div>

      {/* Value */}
      <div className="font-mono text-lg font-bold text-foreground/90">
        {fmtVal(value, stat.format)}
      </div>

      {/* Rank badge */}
      {ranking && ranking.total > 0 && (
        <div
          className={cn(
            "mt-1.5 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold border",
            rankColor(ranking.rank, ranking.total, stat.higher_is_better)
          )}
        >
          #{ranking.rank}
          <span className="text-foreground/30 ml-0.5">/{ranking.total}</span>
        </div>
      )}
    </div>
  );
}

// ─── Game Log Value Resolver ─────────────────────────────────────────

function resolveValue(
  col: GameLogColumn,
  game: PlayerGameLog,
  advWeek: Record<string, Record<string, number | null>> | undefined,
  snap: SnapWeek | undefined
): number | null {
  if (col.source === "snap") {
    if (!snap) return null;
    return (snap as any)[col.key] ?? null;
  }
  if (col.source === "base") {
    return (game as any)[col.key] ?? null;
  }
  // advanced: passing, rushing, receiving
  const catData = advWeek?.[col.source];
  return catData?.[col.key] ?? null;
}

// ═════════════════════════════════════════════════════════════════════
// Main Component
// ═════════════════════════════════════════════════════════════════════

export default function PlayerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"overview" | "gamelog">("overview");
  const [season, setSeason] = useState(2025);

  const { data, isLoading } = usePlayerDetail(id || "", season);
  const { data: injuryMap } = useInjuries();

  // Derived
  const player = data?.player;
  const gameLogs = data?.gameLogs || [];
  const seasonAdvanced = data?.seasonAdvanced || {};
  const rankings = data?.rankings || {};
  const snapHistory = data?.snapHistory || [];
  const advancedGameLogs = data?.advancedGameLogs || {};

  const posGroup = useMemo(() => getPosGroup(player?.position), [player?.position]);
  const bubbles = useMemo(() => getBubbles(posGroup), [posGroup]);
  const gameLogCols = useMemo(() => getGameLogCols(posGroup), [posGroup]);
  const heroStats = useMemo(() => player ? getHeroStats(posGroup, player) : [], [posGroup, player]);

  // Build snap lookup by week
  const snapByWeek = useMemo(() => {
    const m = new Map<number, SnapWeek>();
    snapHistory.forEach(s => m.set(s.week, s));
    return m;
  }, [snapHistory]);

  // Group bubbles by category
  const bubbleGroups = useMemo(() => {
    const groups: { category: string; items: BubbleStat[] }[] = [];
    let current: { category: string; items: BubbleStat[] } | null = null;
    for (const b of bubbles) {
      if (!current || current.category !== b.category) {
        current = { category: b.category, items: [] };
        groups.push(current);
      }
      current.items.push(b);
    }
    return groups;
  }, [bubbles]);

  // Snap summary for DEF/KP overview
  const snapSummary = useMemo(() => {
    if (snapHistory.length === 0) return null;
    const totalOff = snapHistory.reduce((s, w) => s + w.offense_snaps, 0);
    const totalDef = snapHistory.reduce((s, w) => s + w.defense_snaps, 0);
    const totalSt = snapHistory.reduce((s, w) => s + w.st_snaps, 0);
    const avgDefPct = snapHistory.filter(w => w.defense_pct > 0).length > 0
      ? snapHistory.reduce((s, w) => s + w.defense_pct, 0) / snapHistory.filter(w => w.defense_pct > 0).length
      : 0;
    const avgOffPct = snapHistory.filter(w => w.offense_pct > 0).length > 0
      ? snapHistory.reduce((s, w) => s + w.offense_pct, 0) / snapHistory.filter(w => w.offense_pct > 0).length
      : 0;
    const avgStPct = snapHistory.filter(w => w.st_pct > 0).length > 0
      ? snapHistory.reduce((s, w) => s + w.st_pct, 0) / snapHistory.filter(w => w.st_pct > 0).length
      : 0;
    const offPerGame = snapHistory.length > 0 ? totalOff / snapHistory.length : 0;
    const defPerGame = snapHistory.length > 0 ? totalDef / snapHistory.length : 0;
    const stPerGame = snapHistory.length > 0 ? totalSt / snapHistory.length : 0;
    return { totalOff, totalDef, totalSt, avgDefPct, avgOffPct, avgStPct, offPerGame, defPerGame, stPerGame, weeks: snapHistory.length };
  }, [snapHistory]);

  if (isLoading || !player) {
    return (
      <div className="flex items-center justify-center min-h-screen text-foreground/50">
        Loading player details...
      </div>
    );
  }

  const injuryStatus = injuryMap?.[player.player_id]?.status;
  const injuryBadge = getInjuryBadge(injuryStatus);
  const { primary: rawPrimary } = getTeamColors(player.team);
  const primary = rawPrimary;
  const readablePrimary = ensureReadableColor(rawPrimary);

  const categoryLabels: Record<string, string> = {
    passing: "Advanced Passing",
    rushing: "Advanced Rushing",
    receiving: "Advanced Receiving",
  };

  return (
    <div className="min-h-screen bg-background text-foreground pb-20">
      {/* Back Button */}
      <div className="fixed top-4 left-4 z-50">
        <button onClick={() => navigate(-1)} className="p-2 rounded-full glass-card hover:bg-white/10 transition-colors">
          <ArrowLeft className="w-6 h-6" />
        </button>
      </div>

      {/* Hero Section */}
      <div className="relative pt-20 pb-12 px-6 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-[500px] opacity-10 pointer-events-none" style={{ background: `radial-gradient(circle at 50% 0%, ${primary}, transparent 70%)` }} />

        <div className="container mx-auto max-w-5xl relative z-10">
          <div className="flex flex-col md:flex-row items-center gap-8">
            {/* Player Photo */}
            <div className="relative group">
              <div className="absolute inset-0 rounded-full blur-xl opacity-40 animate-pulse" style={{ background: primary }} />
              <div className="relative rounded-full overflow-hidden border-4 border-background shadow-2xl z-10 w-40 h-40 md:w-48 md:h-48" style={{ backgroundColor: primary, borderColor: primary }}>
                <img
                  src={player.photoUrl || `https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/${player.player_id}.png`}
                  alt={player.player_name}
                  className="w-full h-full object-cover"
                  onError={(e) => { e.currentTarget.style.display = "none"; }}
                />
              </div>
              <div className="w-40 h-40 md:w-48 md:h-48 rounded-full border-4 border-background bg-secondary flex items-center justify-center text-5xl font-bold absolute top-0 left-0 z-0">
                {player.player_name.charAt(0)}
              </div>
            </div>

            {/* Info */}
            <div className="text-center md:text-left flex-1">
              <div className="flex items-center justify-center md:justify-start gap-3 mb-2">
                <TeamLogo team={player.team} size="md" />
                <span className="text-lg text-foreground/60 font-medium">{player.team}</span>

                {/* Season Selector */}
                <div className="relative ml-2">
                  <select
                    value={season}
                    onChange={(e) => setSeason(Number(e.target.value))}
                    className="appearance-none bg-white/[0.06] border border-white/10 rounded-lg pl-3 pr-8 py-1.5 text-sm font-mono font-medium text-foreground/80 cursor-pointer hover:bg-white/10 transition-colors focus:outline-none focus:ring-1 focus:ring-white/20"
                  >
                    {[2025, 2024, 2023].map(y => (
                      <option key={y} value={y} className="bg-zinc-900">{y}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-foreground/40 pointer-events-none" />
                </div>
              </div>

              <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-3">{player.player_name}</h1>

              <div className="flex flex-wrap items-center justify-center md:justify-start gap-3">
                {player.position && (
                  <span className="px-3 py-1 rounded-md glass-card text-base font-semibold border border-white/10">
                    {player.position}
                  </span>
                )}
                {player.jersey_number && (
                  <span className="font-mono text-foreground/50 text-base">#{player.jersey_number}</span>
                )}
                {injuryBadge && (
                  <span className={cn("px-3 py-1 rounded-md text-sm font-bold border flex items-center gap-1.5", injuryBadge.bg, injuryBadge.text, injuryBadge.border)}>
                    <Activity className="w-4 h-4" />
                    {injuryBadge.label}
                  </span>
                )}
              </div>
            </div>

            {/* Hero Key Stats */}
            <div className="flex gap-4">
              {heroStats.map((hs) => (
                <div
                  key={hs.label}
                  className="glass-card p-4 rounded-xl text-center min-w-[100px]"
                  style={{ borderLeft: `3px solid ${primary}`, background: `linear-gradient(135deg, ${primary}10, rgba(255,255,255,0.03))` }}
                >
                  <div className="text-[10px] text-foreground/40 uppercase tracking-wider mb-1">{hs.label}</div>
                  <div className="text-2xl font-mono font-bold" style={{ color: readablePrimary }}>{hs.value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="container mx-auto max-w-5xl px-6">
        <div className="flex items-center gap-1 border-b border-border mb-8">
          {[
            { id: "overview" as const, label: "Overview", icon: BarChart3 },
            { id: "gamelog" as const, label: "Game Log", icon: Calendar },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-6 py-4 text-sm font-medium transition-colors relative whitespace-nowrap",
                activeTab === tab.id ? "" : "text-foreground/40 hover:text-foreground/70"
              )}
              style={{ color: activeTab === tab.id ? readablePrimary : undefined }}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 w-full h-0.5" style={{ backgroundColor: readablePrimary }} />
              )}
            </button>
          ))}
        </div>

        {/* ─── Overview Tab ──────────────────────────────────────── */}
        {activeTab === "overview" && (
          <div className="space-y-8 animate-fade-in">

            {/* Season Stat Bubbles */}
            {bubbleGroups.length > 0 ? (
              bubbleGroups.map((grp) => (
                <div key={grp.category}>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground/50 mb-3 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: primary }} />
                    {categoryLabels[grp.category] || grp.category}
                  </h3>
                  <div className="flex flex-wrap gap-2.5">
                    {grp.items.map((stat) => {
                      const catData = seasonAdvanced[stat.category as keyof typeof seasonAdvanced];
                      const val = catData?.[stat.key] ?? null;
                      const rk = rankings[stat.key];
                      return (
                        <StatBubble
                          key={stat.key}
                          stat={stat}
                          value={val}
                          ranking={rk}
                          teamColor={primary}
                        />
                      );
                    })}
                  </div>
                </div>
              ))
            ) : (
              /* DEF / KP — show snap summary */
              snapSummary && (
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground/50 mb-3 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: primary }} />
                    Snap Counts ({snapSummary.weeks} weeks)
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    {posGroup === "DEF" && (
                      <>
                        <SnapBubble label="DEF SNAPS" value={snapSummary.totalDef} teamColor={primary} />
                        <SnapBubble label="DEF/G" value={snapSummary.defPerGame.toFixed(1)} teamColor={primary} />
                        <SnapBubble label="AVG DEF%" value={`${(snapSummary.avgDefPct * 100).toFixed(1)}%`} teamColor={primary} />
                        <SnapBubble label="OFF SNAPS" value={snapSummary.totalOff} teamColor={primary} />
                        <SnapBubble label="ST SNAPS" value={snapSummary.totalSt} teamColor={primary} />
                      </>
                    )}
                    {posGroup === "KP" && (
                      <>
                        <SnapBubble label="ST SNAPS" value={snapSummary.totalSt} teamColor={primary} />
                        <SnapBubble label="AVG ST%" value={`${(snapSummary.avgStPct * 100).toFixed(1)}%`} teamColor={primary} />
                      </>
                    )}
                  </div>
                </div>
              )
            )}

            {/* Snap summary for offensive players too */}
            {bubbleGroups.length > 0 && snapSummary && (
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground/50 mb-3 flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: primary }} />
                  Snap Counts ({snapSummary.weeks} weeks)
                </h3>
                <div className="flex flex-wrap gap-3">
                  <SnapBubble label="OFF SNAPS" value={snapSummary.totalOff} teamColor={primary} />
                  <SnapBubble label="OFF/G" value={snapSummary.offPerGame.toFixed(1)} teamColor={primary} />
                  <SnapBubble label="AVG OFF%" value={`${(snapSummary.avgOffPct * 100).toFixed(1)}%`} teamColor={primary} />
                  {snapSummary.totalSt > 0 && (
                    <SnapBubble label="ST SNAPS" value={snapSummary.totalSt} teamColor={primary} />
                  )}
                </div>
              </div>
            )}

            {/* Bio info */}
            {(player.height || player.weight || player.college || player.age || player.experience) && (
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground/50 mb-3 flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: primary }} />
                  Bio
                </h3>
                <div className="flex flex-wrap gap-3">
                  {player.age && <BioChip label="Age" value={String(player.age)} />}
                  {player.height && <BioChip label="Height" value={player.height} />}
                  {player.weight && <BioChip label="Weight" value={`${player.weight} lbs`} />}
                  {player.college && <BioChip label="College" value={player.college} />}
                  {player.experience && <BioChip label="Exp" value={`${player.experience} yr`} />}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── Game Log Tab ──────────────────────────────────────── */}
        {activeTab === "gamelog" && (
          <div className="glass-card rounded-xl overflow-hidden animate-fade-in">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-white/[0.04] text-foreground/50 text-[11px] uppercase tracking-wider">
                    <th className="sticky left-0 z-10 bg-zinc-900/95 backdrop-blur px-3 py-3 text-left font-semibold">WK</th>
                    <th className="sticky left-[52px] z-10 bg-zinc-900/95 backdrop-blur px-3 py-3 text-left font-semibold">OPP</th>
                    {gameLogCols.map((col) => (
                      <th
                        key={col.key}
                        className="px-3 py-3 text-right font-semibold whitespace-nowrap"
                        title={ADVANCED_STAT_TOOLTIPS[col.key] || col.label}
                      >
                        {col.label}
                      </th>
                    ))}
                    <th className="px-3 py-3 text-right font-semibold">FPTS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {gameLogs.map((game) => {
                    const snap = snapByWeek.get(game.week);
                    const advWeek = advancedGameLogs[String(game.week)];
                    const isHome = game.location === "home";
                    const fpts = calcFpts(game);

                    return (
                      <tr key={game.game_id} className="hover:bg-white/[0.03] transition-colors">
                        <td className="sticky left-0 z-10 bg-zinc-900/80 backdrop-blur px-3 py-2.5 font-mono text-xs font-bold text-foreground/70">
                          {game.week}
                        </td>
                        <td className="sticky left-[52px] z-10 bg-zinc-900/80 backdrop-blur px-3 py-2.5 text-xs whitespace-nowrap">
                          <span className="text-foreground/40 mr-1">{isHome ? "vs" : "@"}</span>
                          <span className="font-medium text-foreground/80">{game.opponent}</span>
                        </td>
                        {gameLogCols.map((col) => {
                          const v = resolveValue(col, game, advWeek, snap);
                          return (
                            <td key={col.key} className="px-3 py-2.5 text-right font-mono text-xs text-foreground/70">
                              {fmtCell(v, col.format)}
                            </td>
                          );
                        })}
                        <td className="px-3 py-2.5 text-right font-mono text-xs font-bold text-foreground/90">
                          {fpts.toFixed(1)}
                        </td>
                      </tr>
                    );
                  })}
                  {/* Season totals row */}
                  {gameLogs.length > 0 && (
                    <tr className="bg-white/[0.04] font-bold">
                      <td className="sticky left-0 z-10 bg-zinc-800/95 backdrop-blur px-3 py-3 font-mono text-xs text-foreground/60" colSpan={2}>
                        TOTAL ({gameLogs.length}G)
                      </td>
                      {gameLogCols.map((col) => (
                        <td key={col.key} className="px-3 py-3 text-right font-mono text-xs text-foreground/80">
                          {fmtTotalCell(col, gameLogs, advancedGameLogs, snapByWeek)}
                        </td>
                      ))}
                      <td className="px-3 py-3 text-right font-mono text-xs font-bold" style={{ color: readablePrimary }}>
                        {gameLogs.reduce((s, g) => s + calcFpts(g), 0).toFixed(1)}
                      </td>

                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Helper Components ───────────────────────────────────────────────

function SnapBubble({ label, value, teamColor }: { label: string; value: number | string; teamColor: string }) {
  const readableColor = ensureReadableColor(teamColor);
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3 min-w-[100px]">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-foreground/40 mb-1">{label}</div>
      <div className="font-mono text-xl font-bold" style={{ color: readableColor }}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
    </div>
  );
}

function BioChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2">
      <span className="text-[10px] uppercase tracking-wider text-foreground/40 mr-2">{label}</span>
      <span className="text-sm font-medium text-foreground/80">{value}</span>
    </div>
  );
}

// ─── Fantasy Points Calculation ──────────────────────────────────────

function calcFpts(g: PlayerGameLog): number {
  const pass = (g.passing_yards || 0) * 0.04 + (g.passing_tds || 0) * 4 - (g.interceptions || 0) * 2;
  const rush = (g.rush_yards || 0) * 0.1 + (g.rush_tds || 0) * 6;
  const rec = (g.rec_yards || 0) * 0.1 + (g.rec_tds || 0) * 6 + (g.receptions || 0) * 1;
  return pass + rush + rec;
}

// ─── Cell Formatting ─────────────────────────────────────────────────

function fmtCell(v: number | null | undefined, format: "int" | "float" | "pct"): string {
  if (v == null) return "—";
  if (format === "int") return String(Math.round(v));
  if (format === "pct") {
    const pct = v <= 1.0 ? v * 100 : v;
    return `${Math.round(pct)}`;
  }
  return v.toFixed(1);
}

function fmtTotalCell(
  col: GameLogColumn,
  games: PlayerGameLog[],
  advLogs: Record<string, any>,
  snapMap: Map<number, SnapWeek>
): string {
  // For snap pct columns, show average
  if (col.format === "pct") {
    let sum = 0, count = 0;
    for (const g of games) {
      const v = resolveValue(col, g, advLogs[String(g.week)], snapMap.get(g.week));
      if (v != null) { sum += v; count++; }
    }
    if (count === 0) return "—";
    const avg = sum / count;
    const pct = avg <= 1.0 ? avg * 100 : avg;
    return `${Math.round(pct)}`;
  }
  // For float stats (advanced), show average
  if (col.format === "float") {
    let sum = 0, count = 0;
    for (const g of games) {
      const v = resolveValue(col, g, advLogs[String(g.week)], snapMap.get(g.week));
      if (v != null) { sum += v; count++; }
    }
    if (count === 0) return "—";
    return (sum / count).toFixed(1);
  }
  // For int stats, show sum
  let sum = 0;
  for (const g of games) {
    const v = resolveValue(col, g, advLogs[String(g.week)], snapMap.get(g.week));
    if (v != null) sum += v;
  }
  return String(Math.round(sum));
}
