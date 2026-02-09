import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Player } from "@/types/player";
import { TeamLogo } from "../TeamLogo";
import { cn } from "@/lib/utils";

interface PlayerSearchProps {
  players: Player[];
  season: number;
  onSelect: (player: Player) => void;
  excludeId?: string;
  placeholder?: string;
  filterPosition?: string;
  loading?: boolean;
}

export function PlayerSearch({
  players,
  season,
  onSelect,
  excludeId,
  filterPosition,
  placeholder = "Search players…",
  loading,
}: PlayerSearchProps) {
  const [query, setQuery] = useState("");

  const trimmed = query.trim();
  const shouldRemote = trimmed.length >= 2;

  const { data: remoteResults, isFetching: remoteLoading } = useQuery({
    queryKey: ["compare-search", season, filterPosition || "", trimmed],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("season", String(season));
      params.set("q", trimmed);
      if (filterPosition) params.set("position", filterPosition);
      params.set("limit", "200");
      const res = await fetch(`/api/players?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    enabled: shouldRemote && !!season,
    staleTime: 1000 * 30,
  });

  const { data: defaultResults, isFetching: defaultLoading } = useQuery({
    queryKey: ["compare-default", season, filterPosition || ""],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("season", String(season));
      if (filterPosition) params.set("position", filterPosition);
      params.set("limit", "200");
      const res = await fetch(`/api/players?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    enabled: !!season,
    staleTime: 1000 * 60,
  });

  const results = useMemo(() => {
    const q = trimmed.toLowerCase();
    if (!q) {
      const sourcePlayers: Player[] = (defaultResults?.players || players) as Player[];
      return sourcePlayers
        .filter((p) => {
          if (excludeId && p.player_id === excludeId) return false;
          if (filterPosition && (p.position || "").toUpperCase() !== filterPosition.toUpperCase()) return false;
          return true;
        })
        .slice(0, 60);
    }

    const sourcePlayers: Player[] = shouldRemote ? (remoteResults?.players || []) : players;
    const filtered = sourcePlayers.filter((p) => {
      if (excludeId && p.player_id === excludeId) return false;
      if (filterPosition && (p.position || "").toUpperCase() !== filterPosition.toUpperCase()) return false;
      return p.player_name.toLowerCase().includes(q);
    });
    return filtered.slice(0, 60);
  }, [players, trimmed, excludeId, filterPosition, shouldRemote, remoteResults]);

  return (
    <div className="space-y-3">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        className="w-full h-11 px-3 rounded-lg border border-border bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      />

      <div className="max-h-80 overflow-y-auto pr-1 space-y-2">
        {((loading && players.length === 0) || (remoteLoading && shouldRemote) || (defaultLoading && !shouldRemote)) ? (
          <p className="text-sm text-muted-foreground px-1">Loading players…</p>
        ) : results.length === 0 ? (
          <p className="text-sm text-muted-foreground px-1">No matches yet.</p>
        ) : (
          results.map((p) => (
            <button
              key={p.player_id}
              type="button"
              onClick={() => onSelect(p)}
              className={cn(
                "w-full rounded-lg border border-transparent bg-secondary/40 hover:bg-secondary/70 transition-colors",
                "flex items-center gap-3 px-3 py-2 text-left"
              )}
            >
              <TeamLogo team={p.team} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground truncate">{p.player_name}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {p.team || "FA"} • {p.position || "—"}
                </p>
              </div>
              <span className="text-xs text-muted-foreground font-mono">{p.seasonTotals?.games ?? p.games ?? "—"}g</span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}


