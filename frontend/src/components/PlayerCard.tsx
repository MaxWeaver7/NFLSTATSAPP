import { useState } from "react";
import { Player } from "@/types/player";
import { cn, formatStat } from "@/lib/utils";
import { ArrowLeftRight, ChevronRight } from "lucide-react";
import { TeamLogo } from "./TeamLogo";
import { getTeamColors } from "@/config/nfl-teams";

// Normalize injury status and get display info
function getInjuryBadge(status: string | null | undefined): { label: string; bg: string; text: string; border: string } | null {
  if (!status) return null;

  const normalized = status.toLowerCase().trim();

  if (normalized === 'out') {
    return { label: 'OUT', bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/40' };
  }
  if (normalized === 'doubtful') {
    return { label: 'DOUBT', bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/40' };
  }
  if (normalized === 'questionable') {
    return { label: 'Q', bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/40' };
  }
  if (normalized === 'probable') {
    return { label: 'PROB', bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/40' };
  }
  if (normalized === 'injured reserve' || normalized === 'ir') {
    return { label: 'IR', bg: 'bg-slate-500/30', text: 'text-slate-300', border: 'border-slate-500/50' };
  }
  // Unknown status - still show something
  return { label: status.slice(0, 4).toUpperCase(), bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/40' };
}

interface PlayerCardProps {
  player: Player;
  isSelected?: boolean;
  onClick?: () => void;
  delay?: number;
  onCompare?: (player: Player) => void;
  injuryStatus?: string | null;
}

export function PlayerCard({ player, isSelected, onClick, delay = 0, onCompare, injuryStatus }: PlayerCardProps) {
  const isReceiver = ['WR', 'TE'].includes(player.position || '');
  const isQB = (player.position || '').toUpperCase() === 'QB';
  const seasonTotals = player.seasonTotals || player;
  const { primary, secondary } = getTeamColors(player.team);
  const primaryStat = isQB
    ? (seasonTotals.passingYards || 0)
    : isReceiver
      ? (seasonTotals.receivingYards || 0)
      : (seasonTotals.rushingYards || 0);
  const primaryLabel = isQB ? 'PASS YDS' : (isReceiver ? 'REC YDS' : 'RUSH YDS');
  const photoUrl = player.photoUrl;
  const [imgError, setImgError] = useState(false);
  const showImage = !!photoUrl && !imgError;

  const injuryBadge = getInjuryBadge(injuryStatus);

  return (
    <div
      onClick={onClick}
      className={cn(
        "glass-card rounded-xl p-4 cursor-pointer relative transition-all duration-200 ease-out opacity-0 animate-slide-up group hover:scale-[1.02] hover:shadow-lg hover:z-10",
        isSelected
          ? "ring-2 ring-primary border-2 border-primary/50"
          : "border border-border hover:border-primary/40"
      )}
      style={{
        animationDelay: `${delay}ms`,
        background: isSelected
          ? `linear-gradient(135deg, ${primary}40, ${secondary}30)`
          : `linear-gradient(135deg, ${primary}20, ${secondary}10)`,
      }}
    >
      <div className="flex items-center gap-4">
        <div className="relative">
          <div className="relative w-14 h-14">
            {/* Team Aura */}
            <div
              data-testid="player-team-aura"
              className="absolute inset-0 rounded-full blur-md opacity-50 animate-pulse"
              style={{
                background: `linear-gradient(135deg, ${primary}, ${secondary})`,
              }}
            />

            {/* Image Container */}
            <div
              data-testid="player-headshot-container"
              className="relative w-14 h-14 rounded-full overflow-hidden ring-2 ring-border shadow-inner"
              style={{ backgroundColor: primary }}
            >
              {showImage ? (
                <img
                  src={photoUrl}
                  alt={player.player_name}
                  className="w-full h-full object-cover relative z-10"
                  loading="lazy"
                  onError={() => {
                    setImgError(true);
                  }}
                />
              ) : null}
              <div
                className={cn(
                  "w-full h-full flex items-center justify-center text-white text-lg font-bold",
                  showImage && "hidden"
                )}
              >
                {player.player_name.split(' ').map(n => n[0]).join('')}
              </div>
            </div>
          </div>
          <div className="absolute -bottom-1 -right-1 bg-secondary text-xs font-bold px-1.5 py-0.5 rounded-md border border-border z-20">
            {player.position}
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-foreground truncate">{player.player_name}</h3>
            {injuryBadge && (
              <span
                className={cn(
                  "text-[10px] font-bold px-2 py-0.5 rounded-md border shrink-0",
                  injuryBadge.bg,
                  injuryBadge.text,
                  injuryBadge.border
                )}
                title={`Status: ${injuryStatus}`}
              >
                {injuryBadge.label}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <TeamLogo team={player.team} size="sm" />
            <p className="text-sm text-muted-foreground">{player.team || "FA"}</p>
          </div>

        </div>

        <div className="text-right mr-2">
          <p className="text-xl font-bold font-mono text-primary">
            {primaryStat}
          </p>
          <p className="text-xs text-muted-foreground">{primaryLabel}</p>
        </div>

        <div className="flex items-center gap-2">
          {onCompare ? (
            <button
              type="button"
              aria-label={`Compare ${player.player_name}`}
              className="h-9 w-9 rounded-lg border border-border bg-transparent text-muted-foreground hover:text-primary hover:border-primary/60 transition-colors flex items-center justify-center"
              onClick={(e) => {
                e.stopPropagation();
                onCompare?.(player);
              }}
            >
              <ArrowLeftRight className="w-4 h-4" />
            </button>
          ) : null}
          <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
        </div>
      </div>

      {isQB ? (
        <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-border">
          <div className="text-center">
            <p className="text-lg font-mono font-semibold text-primary">{seasonTotals.passingYards || 0}</p>
            <p className="text-xs text-muted-foreground">PASS YDS</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-mono font-semibold">{seasonTotals.passingTouchdowns || 0}</p>
            <p className="text-xs text-muted-foreground">PASS TD</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-mono font-semibold">{seasonTotals.rushingYards || 0}</p>
            <p className="text-xs text-muted-foreground">RUSH YDS</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-mono font-semibold">{seasonTotals.rushingTouchdowns || 0}</p>
            <p className="text-xs text-muted-foreground">RUSH TD</p>
          </div>
        </div>
      ) : isReceiver ? (
        <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-border">
          <div className="text-center">
            <p className="text-lg font-mono font-semibold">{seasonTotals.targets || 0}</p>
            <p className="text-xs text-muted-foreground">TGT</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-mono font-semibold">{seasonTotals.receptions || 0}</p>
            <p className="text-xs text-muted-foreground">REC</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-mono font-semibold text-primary">{seasonTotals.receivingYards || 0}</p>
            <p className="text-xs text-muted-foreground">YDS</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-mono font-semibold">{seasonTotals.receivingTouchdowns || 0}</p>
            <p className="text-xs text-muted-foreground">TD</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-border">
          <div className="text-center">
            <p className="text-lg font-mono font-semibold">{seasonTotals.rushAttempts || 0}</p>
            <p className="text-xs text-muted-foreground">ATT</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-mono font-semibold text-primary">{formatStat(seasonTotals.avgYardsPerRush || 0)}</p>
            <p className="text-xs text-muted-foreground">YPC</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-mono font-semibold">{seasonTotals.rushingTouchdowns || 0}</p>
            <p className="text-xs text-muted-foreground">TD</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-mono font-semibold">{seasonTotals.receptions || 0}</p>
            <p className="text-xs text-muted-foreground">REC</p>
          </div>
        </div>
      )}
    </div>
  );
}

