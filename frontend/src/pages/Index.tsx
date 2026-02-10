import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Header } from "@/components/Header";
import { PlayerCard } from "@/components/PlayerCard";
import { SeasonSummary } from "@/components/SeasonSummary";
import { ComparisonModal } from "@/components/comparison/ComparisonModal";
import { PlayerDossierSkeleton } from "@/components/skeletons/PlayerDossierSkeleton";
import { Last5GamesStrip } from "@/components/Last5GamesStrip";
import { AnimatedSelect } from "@/components/common/AnimatedSelect";
import { useFilterOptions, usePlayers, useInjuries, usePlayerDetail } from "@/hooks/useApi";
import { Player } from "@/types/player";
import { useSearchParams, useNavigate } from "react-router-dom";
import { ensureReadableColor } from "@/lib/utils";

const Index = () => {
  const navigate = useNavigate();
  const { data: options } = useFilterOptions();
  const { data: injuryMap } = useInjuries();
  const [searchParams] = useSearchParams();
  const DEFAULT_SEASON = 2025;
  const requestedPlayerId = (searchParams.get("player_id") || "").trim();
  const requestedSeason = Number(searchParams.get("season") || "");
  const initialSeason =
    Number.isFinite(requestedSeason) && requestedSeason > 0 ? requestedSeason : (options?.seasons?.[0] || DEFAULT_SEASON);

  const [selectedSeason, setSelectedSeason] = useState<number>(initialSeason);
  const [selectedPosition, setSelectedPosition] = useState<string>('');
  const [selectedTeam, setSelectedTeam] = useState<string>('');
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [compareTarget, setCompareTarget] = useState<Player | null>(null);
  const [compareOpen, setCompareOpen] = useState<boolean>(false);
  const includePostseason = false;
  const [search, setSearch] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");
  const [offset, setOffset] = useState<number>(0);
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const PAGE_SIZE = 250;
  const serverSearch = debouncedSearch.trim().length >= 2 ? debouncedSearch.trim() : "";
  const isServerSearchActive = serverSearch.length >= 2;

  // Infinite scroll sentinel ref
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // Debounce search
  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search), 250);
    return () => window.clearTimeout(t);
  }, [search]);

  // Reset paging when filters/search change
  useEffect(() => {
    setOffset(0);
    setAllPlayers([]);
    setSelectedPlayer(null);
  }, [selectedSeason, selectedPosition, selectedTeam, serverSearch]);

  const { data: playersData, isLoading: playersLoading, isFetching: playersFetching } = usePlayers(
    selectedSeason,
    selectedPosition || undefined,
    selectedTeam || undefined,
    serverSearch || undefined,
    offset,
    PAGE_SIZE
  );

  // Allow deep-linking to a player even if they are not in the currently loaded list page.
  const activePlayerId = (selectedPlayer?.player_id || requestedPlayerId || "").trim();

  // Use the full player detail hook — gives us rankings + seasonAdvanced for bubbles
  const { data: playerDetail, isLoading: detailLoading } = usePlayerDetail(activePlayerId, selectedSeason);

  // Merge pages (server returns stable objects; de-dupe by player_id)
  useEffect(() => {
    const page = playersData?.players || [];
    if (offset === 0) {
      setAllPlayers(page);
      return;
    }
    if (page.length === 0) return;
    setAllPlayers((prev) => {
      const seen = new Set(prev.map((p) => p.player_id));
      const next = [...prev];
      for (const p of page) {
        if (!seen.has(p.player_id)) {
          seen.add(p.player_id);
          next.push(p);
        }
      }
      return next;
    });
  }, [playersData?.players, offset]);

  const visiblePlayers = useMemo(() => {
    const base = allPlayers;
    const q = search.trim().toLowerCase();
    const team = selectedTeam.trim().toUpperCase();
    const pos = selectedPosition.trim().toUpperCase();

    const filtered = base.filter((p) => {
      if (team && String(p.team || "").toUpperCase() !== team) return false;
      if (pos && String(p.position || "").toUpperCase() !== pos) return false;
      if (q && !p.player_name.toLowerCase().includes(q)) return false;
      return true;
    });

    // Sort by total yards descending
    filtered.sort((a, b) => {
      const sa = a.seasonTotals || a;
      const sb = b.seasonTotals || b;
      const totA = (sa.passingYards || 0) + (sa.rushingYards || 0) + (sa.receivingYards || 0);
      const totB = (sb.passingYards || 0) + (sb.rushingYards || 0) + (sb.receivingYards || 0);
      return totB - totA;
    });

    return filtered;
  }, [allPlayers, search, selectedTeam, selectedPosition]);

  // Honor ?season= query param
  useEffect(() => {
    if (!Number.isFinite(requestedSeason) || requestedSeason <= 0) return;
    if (requestedSeason !== selectedSeason) setSelectedSeason(requestedSeason);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedSeason]);

  // When options load, prefer the latest season
  useEffect(() => {
    const seasons = options?.seasons || [];
    if (seasons.length === 0) return;
    if (!seasons.includes(selectedSeason)) {
      setSelectedSeason(seasons[0]);
    }
  }, [options?.seasons, selectedSeason]);

  // When deep-linking, sync selection state
  useEffect(() => {
    if (!requestedPlayerId) return;
    const p = playerDetail?.player;
    if (!p) return;
    if (selectedPlayer?.player_id === p.player_id) return;
    setSelectedPlayer(p);
  }, [requestedPlayerId, playerDetail?.player, selectedPlayer?.player_id]);

  // Auto-select first player when list changes
  useEffect(() => {
    if (requestedPlayerId) return;
    if (visiblePlayers.length > 0 && !selectedPlayer) {
      setSelectedPlayer(visiblePlayers[0]);
    }
  }, [visiblePlayers, selectedPlayer, requestedPlayerId]);

  // Infinite scroll
  const hasMore = !isServerSearchActive && (playersData?.hasMore ?? false);
  const loadMore = useCallback(() => {
    if (!hasMore || playersLoading || playersFetching) return;
    setOffset(playersData?.nextOffset ?? offset + PAGE_SIZE);
  }, [hasMore, playersLoading, playersFetching, playersData?.nextOffset, offset]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) loadMore(); },
      { rootMargin: "200px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [loadMore]);

  const currentPlayer = playerDetail?.player || selectedPlayer;
  const gameLogs = playerDetail?.gameLogs || [];
  const rankings = playerDetail?.rankings || {};
  const seasonAdvanced = playerDetail?.seasonAdvanced || {};
  const accent = (currentPlayer as any)?.teamColors?.primary || "";
  const readableAccent = ensureReadableColor(accent);

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="container mx-auto px-4 py-8">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 mb-5 opacity-0 animate-slide-up relative z-[100]">
          <AnimatedSelect
            label="Season"
            options={(options?.seasons || []).map(s => s.toString())}
            value={selectedSeason.toString()}
            onChange={(value) => setSelectedSeason(Number(value))}
          />
          <AnimatedSelect
            label="Position"
            options={["All Positions", "QB", "RB", "WR", "TE"]}
            value={selectedPosition || "All Positions"}
            onChange={(val) => setSelectedPosition(val === "All Positions" ? "" : val)}
          />
          <AnimatedSelect
            label="Team"
            options={["All Teams", ...(options?.teams || [])]}
            value={selectedTeam || "All Teams"}
            onChange={(val) => setSelectedTeam(val === "All Teams" ? "" : val)}
          />
        </div>

        <div className="grid lg:grid-cols-12 gap-6 relative z-0">
          {/* Player List Sidebar — sticky */}
          <div className="lg:col-span-4">
            <div className="lg:sticky lg:top-4 space-y-1.5">
              <div className="opacity-0 animate-fade-in">
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search players..."
                  className="w-full h-[30px] px-2.5 rounded-lg border border-white/[0.06] bg-white/[0.03] text-xs text-foreground/80 placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-white/20"
                />
                {(playersLoading || playersFetching) && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {playersLoading ? 'Loading...' : 'Updating...'}
                  </p>
                )}
              </div>

              <div className="space-y-1.5 max-h-[calc(100vh-160px)] overflow-y-auto pr-1 scrollbar-thin">
                {visiblePlayers.map((player, idx) => (
                  <PlayerCard
                    key={player.player_id}
                    player={player}
                    isSelected={currentPlayer?.player_id === player.player_id}
                    onClick={() => setSelectedPlayer(player)}
                    onCompare={(p) => {
                      setCompareTarget(p);
                      setCompareOpen(true);
                    }}
                    delay={idx < 16 ? 60 + idx * 20 : 0}
                    injuryStatus={injuryMap?.[player.player_id]?.status}
                  />
                ))}

                {!playersLoading && visiblePlayers.length === 0 && (
                  <div className="glass-card rounded-xl p-8 text-center">
                    <p className="text-muted-foreground">No players found for the selected filters.</p>
                  </div>
                )}

                {/* Infinite scroll sentinel */}
                {hasMore && <div ref={sentinelRef} className="h-4" />}
              </div>
            </div>
          </div>

          {/* Main Content — Dossier */}
          <div className="lg:col-span-8">
            {currentPlayer ? (
              <div
                id="player-dossier"
                className="glass-card rounded-xl p-5 opacity-0 animate-slide-up relative overflow-hidden"
                style={{
                  animationDelay: "150ms",
                  borderLeftWidth: "3px",
                  borderLeftStyle: "solid",
                  borderLeftColor: accent || "transparent",
                  background: accent
                    ? `linear-gradient(135deg, ${accent}25, ${accent}10, transparent)`
                    : undefined,
                }}
              >
                {detailLoading ? (
                  <PlayerDossierSkeleton position={currentPlayer.position || undefined} />
                ) : (
                  <>
                    <SeasonSummary player={{ ...currentPlayer, gameLogs }} rankings={rankings} seasonAdvanced={seasonAdvanced} />

                    {/* Last 5 Games */}
                    {gameLogs.length > 0 && (
                      <Last5GamesStrip
                        gameLogs={gameLogs}
                        position={currentPlayer.position || "RB"}
                      />
                    )}
                  </>
                )}

                {/* View Full Profile */}
                <button
                  onClick={() => navigate(`/player/${currentPlayer.player_id}`)}
                  className="w-full mt-5 py-3 rounded-lg text-sm font-semibold tracking-wide uppercase transition-all hover:brightness-125 hover:scale-[1.01]"
                  style={{
                    background: accent
                      ? `linear-gradient(90deg, ${accent}50, ${accent}30)`
                      : "rgba(255,255,255,0.08)",
                    color: readableAccent || "inherit",
                    border: `1px solid ${accent ? accent + "60" : "rgba(255,255,255,0.12)"}`,
                  }}
                >
                  View Full Profile
                </button>
              </div>
            ) : (
              <div className="glass-card rounded-xl p-12 text-center opacity-0 animate-fade-in">
                <p className="text-muted-foreground">Select a player to view detailed metrics</p>
              </div>
            )}
          </div>
        </div>
      </main>

      <ComparisonModal
        isOpen={compareOpen}
        onClose={() => {
          setCompareOpen(false);
          setCompareTarget(null);
        }}
        playerA={compareTarget}
        players={allPlayers}
        season={selectedSeason}
        includePostseason={includePostseason}
      />
    </div>
  );
};

export default Index;
