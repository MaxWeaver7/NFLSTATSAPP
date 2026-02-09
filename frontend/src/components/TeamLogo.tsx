interface TeamLogoProps {
  team: string | null | undefined;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const TEAM_LOGO_MAP: Record<string, string> = {
  ARI: "https://a.espncdn.com/i/teamlogos/nfl/500/ari.png",
  ATL: "https://a.espncdn.com/i/teamlogos/nfl/500/atl.png",
  BAL: "https://a.espncdn.com/i/teamlogos/nfl/500/bal.png",
  BUF: "https://a.espncdn.com/i/teamlogos/nfl/500/buf.png",
  CAR: "https://a.espncdn.com/i/teamlogos/nfl/500/car.png",
  CHI: "https://a.espncdn.com/i/teamlogos/nfl/500/chi.png",
  CIN: "https://a.espncdn.com/i/teamlogos/nfl/500/cin.png",
  CLE: "https://a.espncdn.com/i/teamlogos/nfl/500/cle.png",
  DAL: "https://a.espncdn.com/i/teamlogos/nfl/500/dal.png",
  DEN: "https://a.espncdn.com/i/teamlogos/nfl/500/den.png",
  DET: "https://a.espncdn.com/i/teamlogos/nfl/500/det.png",
  GNB: "https://a.espncdn.com/i/teamlogos/nfl/500/gb.png",
  HOU: "https://a.espncdn.com/i/teamlogos/nfl/500/hou.png",
  IND: "https://a.espncdn.com/i/teamlogos/nfl/500/ind.png",
  JAX: "https://a.espncdn.com/i/teamlogos/nfl/500/jax.png",
  KCC: "https://a.espncdn.com/i/teamlogos/nfl/500/kc.png",
  LVR: "https://a.espncdn.com/i/teamlogos/nfl/500/lv.png",
  LAC: "https://a.espncdn.com/i/teamlogos/nfl/500/lac.png",
  LAR: "https://a.espncdn.com/i/teamlogos/nfl/500/lar.png",
  MIA: "https://a.espncdn.com/i/teamlogos/nfl/500/mia.png",
  MIN: "https://a.espncdn.com/i/teamlogos/nfl/500/min.png",
  NEP: "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png",
  NOS: "https://a.espncdn.com/i/teamlogos/nfl/500/no.png",
  NYG: "https://a.espncdn.com/i/teamlogos/nfl/500/nyg.png",
  NYJ: "https://a.espncdn.com/i/teamlogos/nfl/500/nyj.png",
  PHI: "https://a.espncdn.com/i/teamlogos/nfl/500/phi.png",
  PIT: "https://a.espncdn.com/i/teamlogos/nfl/500/pit.png",
  SFO: "https://a.espncdn.com/i/teamlogos/nfl/500/sf.png",
  SEA: "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
  TBB: "https://a.espncdn.com/i/teamlogos/nfl/500/tb.png",
  TEN: "https://a.espncdn.com/i/teamlogos/nfl/500/ten.png",
  WAS: "https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png",
  // nflverse / ESPN-style aliases
  LA: "https://a.espncdn.com/i/teamlogos/nfl/500/lar.png",
  KC: "https://a.espncdn.com/i/teamlogos/nfl/500/kc.png",
  NO: "https://a.espncdn.com/i/teamlogos/nfl/500/no.png",
  WSH: "https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png",
  LV: "https://a.espncdn.com/i/teamlogos/nfl/500/lv.png",
  SF: "https://a.espncdn.com/i/teamlogos/nfl/500/sf.png",
  NE: "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png",
  TB: "https://a.espncdn.com/i/teamlogos/nfl/500/tb.png",
  GB: "https://a.espncdn.com/i/teamlogos/nfl/500/gb.png",
};

export function TeamLogo({ team, size = "sm", className = "" }: TeamLogoProps) {
  const teamUpper = (team || "").toUpperCase();
  const logoUrl = TEAM_LOGO_MAP[teamUpper];

  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  };

  // If no team or logo, show a placeholder (Free Agent / Rookie indicator)
  if (!logoUrl || !team) {
    return (
      <div 
        className={`${sizeClasses[size]} rounded-full bg-muted/20 border border-border flex items-center justify-center ${className}`}
        title="Free Agent / No Team"
      >
        <span className="text-[8px] text-muted-foreground font-bold">FA</span>
      </div>
    );
  }

  return (
    <img
      src={logoUrl}
      alt={`${team} logo`}
      className={`${sizeClasses[size]} object-contain ${className}`}
      loading="lazy"
      onError={(e) => {
        (e.currentTarget as HTMLImageElement).style.display = "none";
      }}
    />
  );
}

