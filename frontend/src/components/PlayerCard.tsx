import { useState } from "react";
import { Player } from "@/types/player";
import { cn } from "@/lib/utils";
import { ArrowLeftRight } from "lucide-react";
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
  const { primary, secondary } = getTeamColors(player.team);
  const st = player.seasonTotals || player;
  const totalYards = (st.passingYards || 0) + (st.rushingYards || 0) + (st.receivingYards || 0);
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
          : "border border-white/[0.06] hover:border-primary/40"
      )}
      style={{
        animationDelay: `${delay}ms`,
        background: isSelected
          ? `linear-gradient(135deg, ${primary}40, ${secondary}30)`
          : `linear-gradient(135deg, ${primary}20, ${secondary}10)`,
      }}
    >
      <div className="flex items-center gap-4">
        <div className="relative shrink-0">
          <div className="relative w-14 h-14">
            {/* Team Aura */}
            <div
              className="absolute inset-0 rounded-full blur-md opacity-50 animate-pulse"
              style={{
                background: `linear-gradient(135deg, ${primary}, ${secondary})`,
              }}
            />

            {/* Image Container */}
            <div
              className="relative w-14 h-14 rounded-full overflow-hidden ring-2 ring-white/10 shadow-inner"
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
                  "w-full h-full flex items-center justify-center text-white text-lg font-bold",
                  showImage && "hidden"
                )}
              >
                {player.player_name.split(' ').map(n => n[0]).join('')}
              </div>
            </div>
          </div>
          <span className="absolute -bottom-0.5 -right-0.5 text-[9px] font-semibold px-1 py-px rounded z-20 bg-black/60 text-white/90 backdrop-blur-sm">
            {player.position}
          </span>
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

        <div className="text-right shrink-0">
          <p className="text-xl font-bold font-mono text-foreground leading-tight">
            {totalYards.toLocaleString()}
          </p>
          <p className="text-[10px] text-muted-foreground">TOT YDS</p>
        </div>

        {onCompare && (
          <button
            type="button"
            aria-label={`Compare ${player.player_name}`}
            className="h-8 w-8 rounded-lg border border-white/[0.06] bg-white/[0.03] text-muted-foreground hover:text-primary hover:border-primary/60 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100 shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              onCompare(player);
            }}
          >
            <ArrowLeftRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
