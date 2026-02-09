import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { getTeamColors } from "@/config/nfl-teams";
import { TeamLogo } from "./TeamLogo";
import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

interface SmashCardProps {
  spot: {
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
    raw_stats?: Record<string, any>;
  };
  delay?: number;
}

export function SmashCard({ spot, delay = 0 }: SmashCardProps) {
  const navigate = useNavigate();
  const teamColors = getTeamColors(spot.team);
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Color-code based on smash_score
  const getScoreColor = (score: number) => {
    if (score >= 80) return "from-green-500 to-emerald-600";
    if (score >= 70) return "from-green-600 to-teal-600";
    if (score >= 60) return "from-yellow-500 to-orange-500";
    if (score >= 50) return "from-orange-500 to-red-500";
    return "from-gray-500 to-gray-600";
  };


  const positionColors: Record<string, string> = {
    QB: "bg-purple-500/20 text-purple-300",
    RB: "bg-blue-500/20 text-blue-300",
    WR: "bg-green-500/20 text-green-300",
    TE: "bg-teal-500/20 text-teal-300",
  };

  return (
    <div
      className={cn(
        "glass-card rounded-xl p-5 opacity-0 animate-slide-up hover:scale-[1.02] transition-transform duration-200",
        "cursor-pointer border-2 relative isolate"
      )}
      style={{ 
        animationDelay: `${delay}ms`,
        background: `linear-gradient(135deg, ${teamColors.primary}30, ${teamColors.secondary}20)`,
        borderColor: teamColors.primary,
        borderWidth: '2px',
        zIndex: 1,
      }}
    >
      {/* Header: Score Badge + Player Info */}
      <div className="flex items-start gap-4 mb-4">
        {/* Smash Score Badge */}
        <div className="flex-shrink-0">
          <div
            className={cn(
              "w-16 h-16 rounded-full flex flex-col items-center justify-center",
              "bg-gradient-to-br shadow-lg",
              getScoreColor(spot.smash_score)
            )}
          >
            <div className="text-2xl font-bold font-mono text-white">
              {Math.round(spot.smash_score)}
            </div>
            <div className="text-[10px] text-white/80 font-medium uppercase tracking-wide">
              Score
            </div>
          </div>
        </div>

        {/* Player Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-lg font-bold text-foreground truncate">
              {spot.player_name}
            </h3>
            <span
              className={cn(
                "px-2 py-0.5 rounded-md text-xs font-bold uppercase",
                positionColors[spot.position] || "bg-gray-500/20 text-gray-300"
              )}
            >
              {spot.position}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <TeamLogo team={spot.team} size="sm" />
            <span className="font-medium">{spot.team}</span>
            <span>vs</span>
            <TeamLogo team={spot.opponent} size="sm" />
            <span className="font-medium">{spot.opponent}</span>
            {spot.game_total > 0 && (
              <>
                <span className="text-muted-foreground/50">•</span>
                <span className="font-mono">{spot.game_total.toFixed(1)} O/U</span>
              </>
            )}
          </div>
        </div>

        {/* Player Photo with Team Aura */}
        <div className="relative w-16 h-16 flex-shrink-0">
          {/* Team Aura Glow */}
          <div
            className="absolute inset-0 rounded-full blur-md opacity-50 animate-pulse"
            style={{
              background: `linear-gradient(135deg, ${teamColors.primary}, ${teamColors.secondary})`,
            }}
          />
          
          {/* Headshot Container */}
          <div
            className="relative w-16 h-16 rounded-full overflow-hidden ring-2 ring-border shadow-inner"
            style={{ backgroundColor: teamColors.primary }}
          >
            {spot.photoUrl ? (
              <img
                src={spot.photoUrl}
                alt={spot.player_name}
                className="w-full h-full object-cover relative z-10"
                loading="lazy"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).style.display = "none";
                }}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-white text-lg font-bold">
                {spot.player_name.split(' ').map(n => n[0]).join('')}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Green Flags Section */}
      {spot.matchup_flags.length > 0 && (
        <div className="mb-4 space-y-2">
          {spot.matchup_flags.map((flag, idx) => (
            <div
              key={idx}
              className="flex items-start gap-2 p-2 rounded-lg bg-primary/10 border border-primary/20"
            >
              <span className="text-xs leading-relaxed text-foreground/90">{flag}</span>
            </div>
          ))}
        </div>
      )}

      {/* Stats Row with Tooltips */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="text-center p-2 rounded-lg bg-secondary/50 group relative">
          <div className="text-xs text-muted-foreground mb-0.5">Stat 1</div>
          <div className="text-sm font-mono font-semibold text-foreground">{spot.stat1}</div>
          {/* Tooltip */}
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 border border-border">
            Most impactful metric
          </div>
        </div>
        <div className="text-center p-2 rounded-lg bg-secondary/50 group relative">
          <div className="text-xs text-muted-foreground mb-0.5">Stat 2</div>
          <div className="text-sm font-mono font-semibold text-foreground">{spot.stat2}</div>
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 border border-border">
            2nd key metric
          </div>
        </div>
        <div className="text-center p-2 rounded-lg bg-secondary/50 group relative">
          <div className="text-xs text-muted-foreground mb-0.5">Stat 3</div>
          <div className="text-sm font-mono font-semibold text-foreground">{spot.stat3}</div>
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 border border-border">
            3rd key metric
          </div>
        </div>
      </div>

      {/* Expand/Collapse Button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setIsExpanded(!isExpanded);
        }}
        className="w-full flex items-center justify-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors mb-3"
      >
        {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {isExpanded ? "Show Less" : "Show All Metrics"}
      </button>

      {/* Expanded Metrics View */}
      {isExpanded && spot.raw_stats && (
        <div className="mb-4 p-3 rounded-lg bg-secondary/30 border border-border space-y-2 text-xs animate-slide-down max-h-96 overflow-y-auto">
          <div className="font-semibold text-foreground mb-2">Raw Stats for {spot.player_name}</div>
          
          {/* Core Info */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 pb-2 border-b border-border">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Position:</span>
              <span className="font-mono">{spot.position}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Team:</span>
              <span className="font-mono">{spot.team}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Opponent:</span>
              <span className="font-mono">{spot.opponent}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Vegas O/U:</span>
              <span className="font-mono font-semibold text-primary">{spot.game_total.toFixed(1)}</span>
            </div>
            {spot.raw_stats.spread_home != null && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Spread:</span>
                <span className="font-mono">{spot.raw_stats.spread_home > 0 ? '+' : ''}{spot.raw_stats.spread_home.toFixed(1)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Smash Score:</span>
              <span className="font-mono font-bold text-primary">{Math.round(spot.smash_score)}</span>
            </div>
          </div>
          
          {/* Raw Stats Only - Filter out algorithm scores */}
          <div className="pt-2">
            <div className="text-muted-foreground font-semibold mb-2">Raw Performance Data:</div>
            <div className="grid grid-cols-1 gap-y-1">
              {Object.entries(spot.raw_stats)
                .filter(([key]) => {
                  // Exclude IDs, timestamps, and algorithm score fields
                  const excludeFields = ['created_at', 'updated_at', 'game_id', 'player_id', 'dk_line',
                    'air_share_score', 'adot_score', 'separation_score', 'matchup_score', 
                    'qb_time_score', 'qb_efficiency_score', 'game_script_score', 'catch_rate_score',
                    'volume_score', 'smash_score', 'efficiency_score', 'run_funnel_score',
                    'favorite_score', 'receiving_upside_score', 'shootout_score', 'aggressiveness_score',
                    'pass_funnel_score', 'pocket_score', 'rushing_upside_score', 'spread_home',
                    'opp_def_rank_pct'
                  ];
                  return !excludeFields.includes(key);
                })
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center py-0.5 hover:bg-secondary/20 px-1 rounded">
                    <span className="text-muted-foreground text-[10px]">{key.replace(/_/g, ' ')}:</span>
                    <span className="font-mono text-[10px]">
                      {typeof value === 'number' 
                        ? (Number.isInteger(value) ? value : value.toFixed(2))
                        : value?.toString() || 'N/A'}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* DK Line + Action - Temporarily Hidden */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        {/* DraftKings line temporarily hidden - data accuracy issues
        Code preserved but disabled:
        {spot.dk_line != null && (
          <div>
            <div className="text-xs text-muted-foreground">
              DK {spot.position === 'QB' ? 'Pass' : spot.position === 'RB' ? 'Rush' : 'Rec'} Yards
            </div>
            <div className="text-lg font-bold font-mono text-primary">
              {spot.dk_line.toFixed(1)}
            </div>
            <div className="text-[10px] text-muted-foreground/70">
              O/U Line
            </div>
          </div>
        )}
        */}

        <button
          className={cn(
            "px-4 py-2 rounded-lg font-semibold text-sm transition-all duration-200",
            "bg-gradient-to-r from-primary to-emerald-500",
            "hover:shadow-lg hover:scale-105",
            "text-primary-foreground w-full"
          )}
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/?player_id=${spot.player_id}&season=2025`);
          }}
        >
          View Player
        </button>
      </div>
    </div>
  );
}

