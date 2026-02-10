import { Player } from "@/types/player";
import { StatCard } from "./StatCard";
import { CountUp } from "./common/CountUp";
import { cn } from "@/lib/utils";
import { TeamLogo } from "./TeamLogo";
import { useState } from "react";
import { getTeamColors } from "@/config/nfl-teams";
import type { RankedStat } from "@/hooks/useApi";

interface SeasonSummaryProps {
  player: Player;
  rankings?: Record<string, RankedStat>;
  seasonAdvanced?: Record<string, Record<string, number | null> | undefined>;
}

export function SeasonSummary({ player, rankings = {}, seasonAdvanced = {} }: SeasonSummaryProps) {
  const stats = player.seasonTotals || player;
  const isQB = (player.position || '').toUpperCase() === 'QB';
  const isReceiver = ['WR', 'TE'].includes(player.position || '');
  const photoUrl = player.photoUrl;
  const [imgError, setImgError] = useState(false);
  const showImage = !!photoUrl && !imgError;
  const { primary, secondary } = getTeamColors(player.team);

  const advPassing = seasonAdvanced?.passing as Record<string, number | null> | undefined;
  const advRushing = seasonAdvanced?.rushing as Record<string, number | null> | undefined;
  const advReceiving = seasonAdvanced?.receiving as Record<string, number | null> | undefined;

  const getRank = (key: string): number | undefined => {
    return rankings[key]?.rank;
  };

  const fmtDec = (val: number | null | undefined, decimals = 1): string => {
    if (val == null) return "\u2014";
    return val.toFixed(decimals);
  };

  const fmtPct = (val: number | null | undefined): string => {
    if (val == null) return "\u2014";
    const pct = val <= 1.0 ? val * 100 : val;
    return pct.toFixed(1) + "%";
  };

  return (
    <div className="relative">
      <div className="space-y-4">
        {/* Header: photo + name + team */}
        <div className="flex items-center gap-4 relative z-10 opacity-0 animate-slide-up" style={{ animationDelay: '100ms' }}>
          <div className="relative">
            <div
              className="absolute inset-0 rounded-full blur-md opacity-40 animate-pulse"
              style={{ background: `linear-gradient(135deg, ${primary}, ${secondary})` }}
            />
            <div
              className="relative z-10 w-20 h-20 rounded-full overflow-hidden ring-2 ring-white/10 shadow-inner"
              style={{ backgroundColor: primary }}
            >
              {showImage ? (
                <img
                  src={photoUrl}
                  alt={player.player_name}
                  className="w-full h-full object-cover relative z-10"
                  loading="lazy"
                  onError={() => setImgError(true)}
                />
              ) : null}
              <div
                className={cn(
                  "w-full h-full flex items-center justify-center text-white text-2xl font-bold",
                  showImage && "hidden"
                )}
              >
                {player.player_name.split(' ').map(n => n[0]).join('')}
              </div>
            </div>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">{player.player_name}</h2>
            <div className="flex items-center gap-2 text-muted-foreground">
              <TeamLogo team={player.team} size="md" />
              <p>{player.team} &middot; {player.position} &middot; {stats.season || player.season} Season</p>
            </div>
          </div>
        </div>

        {/* Stats — 6 cards per position */}
        {isQB ? (
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            <StatCard label="PASS YDS" value={<CountUp end={stats.passingYards || 0} />}
              delay={150} teamColors={{ primary, secondary }} rank={getRank("pass_yards")} />
            <StatCard label="PASS TD" value={<CountUp end={stats.passingTouchdowns || 0} />}
              delay={200} teamColors={{ primary, secondary }} rank={getRank("pass_touchdowns")} />
            <StatCard label="INT" value={<CountUp end={stats.passingInterceptions || 0} />}
              delay={250} teamColors={{ primary, secondary }} rank={getRank("interceptions")} />
            <StatCard label="RATING" value={fmtDec(advPassing?.passer_rating)}
              delay={300} teamColors={{ primary, secondary }} rank={getRank("passer_rating")} />
            <StatCard label="RUSH YDS" value={<CountUp end={stats.rushingYards || 0} />}
              delay={350} teamColors={{ primary, secondary }} rank={getRank("rush_yards")} />
            <StatCard label="RUSH TD" value={<CountUp end={stats.rushingTouchdowns || 0} />}
              delay={400} teamColors={{ primary, secondary }} rank={getRank("rush_touchdowns")} />
          </div>
        ) : isReceiver ? (
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            <StatCard label="REC" value={<CountUp end={stats.receptions || 0} />}
              delay={150} teamColors={{ primary, secondary }} rank={getRank("receptions")} />
            <StatCard label="TGT" value={<CountUp end={stats.targets || 0} />}
              delay={200} teamColors={{ primary, secondary }} rank={getRank("targets")} />
            <StatCard label="REC YDS" value={<CountUp end={stats.receivingYards || 0} />}
              delay={250} teamColors={{ primary, secondary }} rank={getRank("yards")} />
            <StatCard label="REC TD" value={<CountUp end={stats.receivingTouchdowns || 0} />}
              delay={300} teamColors={{ primary, secondary }} />
            <StatCard label="IAY%" value={fmtPct(advReceiving?.percent_share_of_intended_air_yards)}
              delay={350} teamColors={{ primary, secondary }} rank={getRank("percent_share_of_intended_air_yards")} />
            <StatCard label="CATCH%" value={fmtPct(advReceiving?.catch_percentage)}
              delay={400} teamColors={{ primary, secondary }} rank={getRank("catch_percentage")} />
          </div>
        ) : (
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            <StatCard label="RUSH YDS" value={<CountUp end={stats.rushingYards || 0} />}
              delay={150} teamColors={{ primary, secondary }} rank={getRank("rush_yards")} />
            <StatCard label="RUSH TD" value={<CountUp end={stats.rushingTouchdowns || 0} />}
              delay={200} teamColors={{ primary, secondary }} rank={getRank("rush_touchdowns")} />
            <StatCard label="YPC" value={fmtDec(advRushing?.avg_rush_yards)}
              delay={250} teamColors={{ primary, secondary }} rank={getRank("avg_rush_yards")} />
            <StatCard label="REC YDS" value={<CountUp end={stats.receivingYards || 0} />}
              delay={300} teamColors={{ primary, secondary }} rank={getRank("yards")} />
            <StatCard label="REC TD" value={<CountUp end={stats.receivingTouchdowns || 0} />}
              delay={350} teamColors={{ primary, secondary }} />
            <StatCard label="REC" value={<CountUp end={stats.receptions || 0} />}
              delay={400} teamColors={{ primary, secondary }} rank={getRank("receptions")} />
          </div>
        )}
      </div>
    </div>
  );
}
