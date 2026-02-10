import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  subValue?: string;
  trend?: 'positive' | 'negative' | 'neutral';
  sparkline?: ReactNode;
  className?: string;
  delay?: number;
  rank?: number | string;
  teamColors?: { primary: string; secondary: string };
}

export function StatCard({ label, value, subValue, trend = 'neutral', sparkline, className, delay = 0, rank, teamColors }: StatCardProps) {
  const rankNumber = typeof rank === 'string' ? Number(rank) : rank;
  const rankClass = (() => {
    if (!rankNumber || Number.isNaN(rankNumber)) return "text-primary bg-primary/10";
    if (rankNumber <= 5) return "text-emerald-300 bg-emerald-400/15 shadow-[0_0_8px_rgba(52,211,153,0.3)]";
    if (rankNumber <= 10) return "text-lime-300 bg-lime-400/15";
    if (rankNumber <= 20) return "text-amber-300 bg-amber-400/15";
    if (rankNumber <= 28) return "text-orange-300 bg-orange-400/15";
    return "text-red-300 bg-red-500/20";
  })();

  return (
    <div
      className={cn(
        "glass-card glass-card-interactive rounded-xl p-4 opacity-0 animate-slide-up border border-border relative overflow-hidden",
        className
      )}
      style={{
        animationDelay: `${delay}ms`,
        background: "rgba(255,255,255,0.02)",
      }}
    >
      {/* Gradient top accent strip */}
      {teamColors && (
        <div
          className="absolute top-0 left-0 w-full h-[2px]"
          style={{ background: `linear-gradient(90deg, ${teamColors.primary}, ${teamColors.secondary})` }}
        />
      )}

      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </p>
        {rank && (
          <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-full", rankClass)}>
            #{rank}
          </span>
        )}
      </div>
      <div className={cn(
        "text-3xl font-bold font-mono leading-tight text-center",
        trend === 'positive' && "text-primary",
        trend === 'negative' && "text-destructive",
        trend === 'neutral' && "text-foreground"
      )}>
        {value}
      </div>
      {subValue && (
        <p className="text-xs text-muted-foreground mt-1 text-center">
          {subValue}
        </p>
      )}
      {sparkline && (
        <div className="mt-2 -mx-2 -mb-2">
          {sparkline}
        </div>
      )}
    </div>
  );
}
