import { useState, ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  teamColor?: string;
  badge?: string | number;
  children: ReactNode;
  className?: string;
}

export function CollapsibleSection({
  title,
  defaultOpen = false,
  teamColor,
  badge,
  children,
  className,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={cn("rounded-xl border border-white/[0.06] overflow-hidden", className)}>
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-white/[0.02] hover:bg-white/[0.04] transition-colors text-left"
      >
        {/* Left accent bar */}
        {teamColor && (
          <div
            className="w-1 h-5 rounded-full flex-shrink-0"
            style={{ backgroundColor: teamColor }}
          />
        )}

        <span className="text-sm font-semibold uppercase tracking-wider text-foreground/70 flex-1">
          {title}
        </span>

        {badge !== undefined && badge !== null && (
          <span className="text-[10px] font-mono text-foreground/40 bg-white/[0.04] px-2 py-0.5 rounded-full">
            {badge}
          </span>
        )}

        <ChevronDown
          className={cn(
            "w-4 h-4 text-foreground/40 transition-transform duration-200",
            open && "rotate-180"
          )}
        />
      </button>

      {/* Content */}
      <div className="collapsible-content" data-open={open}>
        <div>
          <div className="px-4 py-4">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
