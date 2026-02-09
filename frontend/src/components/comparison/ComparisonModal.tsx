import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { Player } from "@/types/player";
import { PlayerSearch } from "./PlayerSearch";
import { Button } from "../ui/button";
import { cn, formatStat } from "@/lib/utils";
import { getTeamColors } from "@/config/nfl-teams";
import {
  ADVANCED_PASSING_COLUMNS,
  ADVANCED_RECEIVING_COLUMNS,
  ADVANCED_RUSHING_COLUMNS,
  type AdvancedColumn,
} from "@/config/advanced-stats-config";

type StatDescriptor = {
  key: string;
  label: string;
  higherIsBetter?: boolean;
  decimals?: number;
  integer?: boolean;
};

const STAT_CONFIGS: Record<
  "qb" | "receiver" | "rb",
  { core: StatDescriptor[]; advanced: StatDescriptor[] }
> = {
  qb: {
    core: [
      { key: "passingYards", label: "Pass Yards" },
      { key: "passingTouchdowns", label: "Pass TDs" },
      { key: "passingInterceptions", label: "INT", higherIsBetter: false },
      { key: "rushingYards", label: "Rush Yards" },
      { key: "rushingTouchdowns", label: "Rush TDs" },
    ],
    advanced: [],
  },
  receiver: {
    core: [
      { key: "receptions", label: "Receptions" },
      { key: "receivingYards", label: "Rec Yards" },
      { key: "receivingTouchdowns", label: "Rec TDs" },
      { key: "targets", label: "Targets" },
    ],
    advanced: [],
  },
  rb: {
    core: [
      { key: "rushAttempts", label: "Rush Attempts" },
      { key: "rushingYards", label: "Rush Yards" },
      { key: "rushingTouchdowns", label: "Rush TDs" },
      { key: "receptions", label: "Receptions" },
    ],
    advanced: [],
  },
};

function positionBucket(player?: Player | null): "qb" | "receiver" | "rb" {
  const pos = (player?.position || "").toUpperCase();
  if (pos === "QB") return "qb";
  if (pos === "WR" || pos === "TE") return "receiver";
  return "rb";
}

function mapAdvancedColumns(columns: AdvancedColumn[]): StatDescriptor[] {
  return columns.map((c) => ({
    key: c.k,
    label: c.label,
    integer: c.type === "int",
    higherIsBetter: c.k === "interceptions" ? false : true,
  }));
}

const ADVANCED_BY_BUCKET: Record<"qb" | "receiver" | "rb", StatDescriptor[]> = {
  qb: mapAdvancedColumns(ADVANCED_PASSING_COLUMNS),
  receiver: mapAdvancedColumns(ADVANCED_RECEIVING_COLUMNS),
  rb: mapAdvancedColumns(ADVANCED_RUSHING_COLUMNS),
};

function extractAdvancedTotals(data: any, bucket: "qb" | "receiver" | "rb") {
  if (!data?.goatAdvanced?.regular) return null;
  const key = bucket === "qb" ? "passing" : bucket === "receiver" ? "receiving" : "rushing";
  const rows = data.goatAdvanced.regular[key] || [];
  return rows.find((r: any) => r.week === 0) || null;
}

function getStatValue(
  player: Player | null | undefined,
  advancedTotals: any,
  key: string,
): number | undefined {
  const advVal = advancedTotals ? advancedTotals[key] : undefined;
  if (advVal !== undefined && advVal !== null) {
    const num = Number(advVal);
    return Number.isFinite(num) ? num : undefined;
  }

  if (!player) return undefined;
  const totals = (player.seasonTotals as any) || {};
  const base = player as any;

  const direct = totals[key] ?? base[key];
  if (typeof direct === "number") return direct;
  const num = Number(direct);
  return Number.isFinite(num) ? num : undefined;
}

function winner(
  a: number | undefined,
  b: number | undefined,
  higherIsBetter: boolean = true,
): "A" | "B" | "tie" {
  const aValid = Number.isFinite(a);
  const bValid = Number.isFinite(b);
  if (!aValid && !bValid) return "tie";
  if (!aValid && bValid) return "B";
  if (aValid && !bValid) return "A";
  const aVal = a as number;
  const bVal = b as number;
  if (aVal === bVal) return "tie";
  if (higherIsBetter) return aVal > bVal ? "A" : "B";
  return aVal < bVal ? "A" : "B";
}

function formatValue(stat: StatDescriptor, value: number | undefined) {
  const opts = {
    decimals: stat.decimals,
    integer: stat.integer,
    empty: "Stat Unavailable",
  };
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return opts.empty;
  }
  return formatStat(value, opts);
}

function PlayerBadge({ player }: { player: Player }) {
  const { primary, secondary } = getTeamColors(player.team);
  return (
    <div className="flex items-center gap-3">
      <div className="relative">
        <div
          className="absolute inset-0 rounded-full blur-md opacity-50"
          style={{ background: `linear-gradient(135deg, ${primary}, ${secondary})` }}
        />
        <div
          className="relative w-12 h-12 rounded-full overflow-hidden ring-2 ring-border shadow-inner flex items-center justify-center text-sm font-semibold text-white"
          style={{ backgroundColor: primary }}
        >
          {player.photoUrl ? (
            <img src={player.photoUrl} alt={player.player_name} className="w-full h-full object-cover" />
          ) : (
            <span>{player.player_name.split(" ").map((n) => n[0]).join("")}</span>
          )}
        </div>
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-foreground truncate">{player.player_name}</p>
        <p className="text-xs text-muted-foreground truncate">
          {player.team || "FA"} • {player.position || "—"}
        </p>
      </div>
    </div>
  );
}

interface ComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  playerA: Player | null;
  playerB?: Player | null;
  players: Player[];
  season: number;
  includePostseason?: boolean;
}

export function ComparisonModal({ isOpen, onClose, playerA, playerB, players, season, includePostseason }: ComparisonModalProps) {
  const [selectedPlayerB, setSelectedPlayerB] = useState<Player | null>(playerB ?? null);

  useEffect(() => {
    setSelectedPlayerB(playerB ?? null);
  }, [playerB, playerA?.player_id]);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  const bucket = positionBucket(playerA || selectedPlayerB || undefined);
  const statConfig = {
    ...STAT_CONFIGS[bucket],
    advanced: ADVANCED_BY_BUCKET[bucket],
  };

  const qs = useMemo(() => {
    const params = new URLSearchParams({ season: String(season) });
    if (includePostseason) params.set("include_postseason", "1");
    return params.toString();
  }, [season, includePostseason]);

  async function fetchPlayerDetail(pid: string) {
    const res = await fetch(`/api/player/${pid}?${qs}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  const { data: playerAData } = useQuery({
    queryKey: ["comparison-player", playerA?.player_id, season, includePostseason],
    queryFn: () => fetchPlayerDetail(playerA?.player_id || ""),
    enabled: isOpen && !!playerA?.player_id && !!season,
    staleTime: 1000 * 60,
  });

  const { data: playerBData } = useQuery({
    queryKey: ["comparison-player", selectedPlayerB?.player_id, season, includePostseason],
    queryFn: () => fetchPlayerDetail(selectedPlayerB?.player_id || ""),
    enabled: isOpen && !!selectedPlayerB?.player_id && !!season,
    staleTime: 1000 * 60,
  });

  const comparePlayers = players;
  const compareLoading = false;

  const advancedTotalsA = useMemo(() => extractAdvancedTotals(playerAData, bucket), [playerAData, bucket]);
  const advancedTotalsB = useMemo(() => extractAdvancedTotals(playerBData, bucket), [playerBData, bucket]);

  const title = useMemo(() => {
    if (playerA && selectedPlayerB) return `${playerA.player_name} vs ${selectedPlayerB.player_name}`;
    if (playerA) return `Compare ${playerA.player_name}`;
    return "Head-to-Head";
  }, [playerA, selectedPlayerB]);

  if (!isOpen || !playerA) return null;

  const renderStatRow = (stat: StatDescriptor) => {
    const aVal = getStatValue(playerA, advancedTotalsA, stat.key);
    const bVal = getStatValue(selectedPlayerB, advancedTotalsB, stat.key);
    const whoWon = winner(aVal, bVal, stat.higherIsBetter !== false);
    const aClass =
      whoWon === "A" ? "text-primary font-semibold" : whoWon === "B" ? "text-muted-foreground" : "text-foreground";
    const bClass =
      whoWon === "B" ? "text-primary font-semibold" : whoWon === "A" ? "text-muted-foreground" : "text-foreground";

    return (
      <div
        key={stat.key}
        className="grid grid-cols-[1fr,auto,1fr] items-center gap-4 rounded-xl border border-border/70 px-3 py-2.5 bg-secondary/40"
      >
        <div className={cn("text-right font-mono", aClass)}>{formatValue(stat, aVal)}</div>
        <div className="text-xs uppercase tracking-wide text-muted-foreground font-semibold text-center">
          {stat.label}
        </div>
        <div className={cn("text-left font-mono", bClass)}>
          {selectedPlayerB ? formatValue(stat, bVal) : "—"}
        </div>
      </div>
    );
  };

  return (
    <>
      <div className="fixed inset-0 z-[1000] bg-black/60 backdrop-blur-sm" onClick={onClose} aria-label="Close modal" />
      <div className="fixed inset-0 z-[1001] overflow-y-auto">
        <div className="min-h-full flex items-start justify-center px-4 py-8">
          <div className="relative w-full max-w-5xl glass-card rounded-2xl p-6 shadow-2xl">
            <button
              type="button"
              aria-label="Close comparison"
              className="absolute top-4 right-4 p-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-primary/60 transition-colors"
              onClick={onClose}
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pr-10">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Head-to-Head</p>
                <h3 className="text-2xl font-bold text-foreground">{title}</h3>
              </div>
              <div className="flex items-center gap-2">
                {selectedPlayerB ? (
                  <Button variant="outline" size="sm" onClick={() => setSelectedPlayerB(null)}>
                    Change Player
                  </Button>
                ) : null}
                <span className="text-xs px-3 py-1 rounded-full bg-primary/10 text-primary font-semibold">
                  Season Totals
                </span>
              </div>
            </div>

            {!selectedPlayerB ? (
              <div className="grid md:grid-cols-2 gap-5 mt-6">
                <div className="rounded-xl border border-border/60 p-4 bg-secondary/40 space-y-4">
                  <div className="flex items-center gap-3">
                    <PlayerBadge player={playerA} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {statConfig.core.slice(0, 4).map((stat) => (
                      <div key={stat.key} className="rounded-lg border border-border/60 px-3 py-2 bg-secondary/60">
                        <p className="text-xs text-muted-foreground uppercase">{stat.label}</p>
                        <p className="text-lg font-semibold text-primary">
                          {formatValue(stat, getStatValue(playerA, undefined, stat.key))}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-border/60 p-4 bg-secondary/40">
                  <p className="text-sm font-semibold text-foreground mb-2">Select Player</p>
                  <PlayerSearch
                    players={comparePlayers}
                    season={season}
                    excludeId={playerA.player_id}
                    filterPosition={playerA.position || undefined}
                    loading={compareLoading}
                    onSelect={(p) => setSelectedPlayerB(p)}
                    placeholder="Search by name…"
                  />
                  <p className="text-xs text-muted-foreground mt-3">
                    Tip: Search pulls from the full player list. Only season totals are compared.
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-6 space-y-6">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="rounded-xl border border-border/60 p-3 bg-secondary/40">
                    <PlayerBadge player={playerA} />
                  </div>
                  <div className="rounded-xl border border-border/60 p-3 bg-secondary/40">
                    <PlayerBadge player={selectedPlayerB} />
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-foreground uppercase tracking-wide">Core Stats</h4>
                    <span className="text-xs text-muted-foreground">Higher value wins unless noted</span>
                  </div>
                  <div className="space-y-2">
                    {statConfig.core.map((stat) => renderStatRow(stat))}
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-foreground uppercase tracking-wide">Advanced Stats</h4>
                    <span className="text-xs text-muted-foreground">Season advanced metrics</span>
                  </div>
                  <div className="space-y-2">
                    {statConfig.advanced.map((stat) => renderStatRow(stat))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}


