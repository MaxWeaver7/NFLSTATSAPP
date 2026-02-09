import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components/Header";
import { AnimatedSelect } from "@/components/common/AnimatedSelect";
import { SmashCard } from "@/components/SmashCard";
import { useFilterOptions } from "@/hooks/useApi";

type SmashSpot = {
  player_id: string;
  player_name: string;
  position: string;
  team: string;
  opponent: string;
  smash_score: number;
  dk_line?: number | null;
  game_total: number;
  opponent_rank: number;
  matchup_flags: string[];
  photoUrl?: string | null;
  stat1: string;
  stat2: string;
  stat3: string;
};

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export default function SmashFeed() {
  const { data: options } = useFilterOptions();
  const DEFAULT_SEASON = 2025;
  const DEFAULT_WEEK = 17;

  const [season, setSeason] = useState<number>(options?.seasons?.[0] || DEFAULT_SEASON);
  const [week, setWeek] = useState<number>(DEFAULT_WEEK);
  const [positionFilter, setPositionFilter] = useState<string>("ALL");

  // Fetch smash spots
  const {
    data: feedData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["smashFeed", season, week],
    queryFn: () => {
      const params = new URLSearchParams({
        season: String(season),
        week: String(week),
        limit: "50",
      });
      return fetchJson<{ rows: SmashSpot[] }>(`/api/feed/smash-spots?${params.toString()}`);
    },
    enabled: !!season && !!week,
  });

  const spots = feedData?.rows || [];

  // Filter and sort
  const displaySpots = useMemo(() => {
    let filtered = spots;

    // Position filter
    if (positionFilter !== "ALL") {
      filtered = filtered.filter((s) => s.position === positionFilter);
    }

    // Already sorted by score from API
    return filtered;
  }, [spots, positionFilter]);

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="container mx-auto px-4 py-8">
        {/* Hero Section */}
        <div className="mb-8 opacity-0 animate-fade-in">
          <div className="flex items-start justify-between mb-2">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">
              Smash Spot Feed
            </h1>
            <p className="text-muted-foreground text-lg">
              Proprietary betting algorithm ranking the top NFL opportunities of the week
            </p>
          </div>
          </div>
          <div className="h-1 w-24 bg-gradient-to-r from-primary to-emerald-500 rounded-full" />
        </div>

        {/* Filters */}
        <div className="mb-6 relative" style={{ zIndex: 1000 }}>
          <div className="glass-card rounded-xl p-4 opacity-0 animate-slide-up">
            <h3 className="font-medium text-foreground mb-3">Filters & Sort</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm text-muted-foreground mb-2 block">Season</label>
                <AnimatedSelect
                  label="Select season"
                  options={(options?.seasons || []).map((s) => s.toString())}
                  value={season.toString()}
                  onChange={(value) => setSeason(Number(value))}
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground mb-2 block">Week</label>
                <AnimatedSelect
                  label="Select week"
                  options={Array.from({ length: 18 }, (_, i) => `Week ${i + 1}`)}
                  value={`Week ${week}`}
                  onChange={(val) => setWeek(Number(val.replace("Week ", "")))}
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground mb-2 block">Position</label>
                <AnimatedSelect
                  label="All Positions"
                  options={["All Positions", "QB", "RB", "WR", "TE"]}
                  value={positionFilter === "ALL" ? "All Positions" : positionFilter}
                  onChange={(val) => setPositionFilter(val === "All Positions" ? "ALL" : val)}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-block w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
            <p className="mt-4 text-muted-foreground">Loading smash spots...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="glass-card rounded-xl p-8 text-center">
            <p className="text-destructive font-semibold">Error loading data</p>
            <p className="text-muted-foreground text-sm mt-2">
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && displaySpots.length === 0 && (
          <div className="glass-card rounded-xl p-12 text-center">
            <p className="text-muted-foreground text-lg">
              No smash spots found for Week {week}, {season}
            </p>
            <p className="text-muted-foreground text-sm mt-2">
              Try a different week or check if games are scheduled.
            </p>
          </div>
        )}

        {/* Smash Cards Grid */}
        {!isLoading && !error && displaySpots.length > 0 && (
          <>
            {/* Stats Summary */}
            <div className="mb-6 flex items-center justify-between opacity-0 animate-fade-in">
              <div className="text-sm text-muted-foreground">
                Showing <span className="text-primary font-semibold">{displaySpots.length}</span> spots
                {positionFilter !== "ALL" && ` • Filtered by ${positionFilter}`}
              </div>
              <div className="text-sm text-muted-foreground">
                Week {week}, {season}
              </div>
            </div>

            {/* Masonry-style Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {displaySpots.map((spot, idx) => (
                <SmashCard key={spot.player_id} spot={spot} delay={idx * 30} />
              ))}
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-12 py-6">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>
            Smash Score Algorithm • Powered by Advanced Stats, Opponent Defense, Vegas Odds
          </p>
          <p className="mt-2 text-xs">
            Data sourced from BallDontLie NFL API • GOAT Analytics • DraftKings
          </p>
        </div>
      </footer>
    </div>
  );
}

