
import { useNavigate } from "react-router-dom";
import { useStandings } from "@/hooks/useApi";
import { TeamLogo } from "@/components/TeamLogo";
import { Header } from "@/components/Header";
import { TrendingUp } from "lucide-react";

export default function Teams() {
    const navigate = useNavigate();
    const { data: standings, isLoading } = useStandings(2025);
    const divisions = ["AFC East", "AFC North", "AFC South", "AFC West", "NFC East", "NFC North", "NFC South", "NFC West"];

    const groupedTeams = divisions.reduce((acc, div) => {
        if (standings) {
            acc[div] = standings
                .filter(t => t.division === div)
                .sort((a, b) => (a.division_rank ?? 99) - (b.division_rank ?? 99));
        } else {
            acc[div] = [];
        }
        return acc;
    }, {} as Record<string, typeof standings>);

    return (
        <div className="min-h-screen bg-background text-foreground">
            <Header />

            <main className="container mx-auto px-4 py-8">
                <div className="mb-8 animate-fade-in">
                    <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/50">
                        Teams
                    </h1>
                </div>

                {isLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
                        {[...Array(8)].map((_, i) => (
                            <div key={i} className="h-40 glass-card rounded-xl" />
                        ))}
                    </div>
                ) : (
                    <div className="space-y-12 animate-slide-up">
                        {divisions.map((div) => {
                            const teams = groupedTeams[div];
                            if (!teams || teams.length === 0) return null;
                            const isAFC = div.startsWith("AFC");

                            return (
                                <div key={div}>
                                    <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-white/80 pb-2"
                                        style={{ borderBottom: `2px solid ${isAFC ? 'rgba(30, 58, 138, 0.4)' : 'rgba(153, 27, 27, 0.4)'}` }}
                                    >
                                        {div}
                                    </h2>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                        {teams.map((team) => {
                                            const diff = (team.pf || 0) - (team.pa || 0);
                                            const streak = team.win_streak ?? team.strk ?? 0;

                                            return (
                                                <div
                                                    key={team.team}
                                                    onClick={() => navigate(`/team/${team.team}`)}
                                                    className="glass-card glass-card-interactive p-4 rounded-xl cursor-pointer group relative overflow-hidden"
                                                    style={{
                                                        borderLeft: `4px solid ${team.primary_color}`,
                                                        background: `linear-gradient(135deg, ${team.primary_color}18, ${team.secondary_color}08, transparent)`
                                                    }}
                                                >
                                                    {/* Gradient top accent strip */}
                                                    <div
                                                        className="absolute top-0 left-0 w-full h-[2px]"
                                                        style={{ background: `linear-gradient(90deg, ${team.primary_color}, ${team.secondary_color})` }}
                                                    />

                                                    <div className="flex items-start justify-between mb-3">
                                                        <TeamLogo team={team.team} size="md" />
                                                        <div className="text-right">
                                                            <div className="text-2xl font-bold font-mono">
                                                                {team.wins}-{team.losses}{team.ties > 0 && `-${team.ties}`}
                                                            </div>
                                                            <div className="text-xs text-muted-foreground">
                                                                {(team.win_pct * 100).toFixed(1)}% Win
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <div>
                                                        <h3 className="text-lg font-bold leading-tight mb-2 group-hover:text-primary transition-colors">
                                                            {team.team_name}
                                                        </h3>

                                                        {/* ATS + Streak row */}
                                                        <div className="flex items-center gap-3 text-xs font-mono mb-2">
                                                            <div className="flex items-center gap-1">
                                                                <TrendingUp className="w-3 h-3 text-emerald-400" />
                                                                <span className="text-muted-foreground">ATS:</span>
                                                                <span className={team.ats_wins > team.ats_losses ? "text-emerald-400" : "text-foreground"}>
                                                                    {team.ats_wins ?? team.ats_w ?? 0}-{team.ats_losses ?? team.ats_l ?? 0}{(team.ats_p ?? 0) > 0 ? `-${team.ats_p}` : ""}
                                                                </span>
                                                            </div>
                                                            {streak !== 0 && (
                                                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                                                    streak > 0
                                                                        ? "text-emerald-400 bg-emerald-500/15"
                                                                        : "text-red-400 bg-red-500/15"
                                                                }`}>
                                                                    {streak > 0 ? `W${streak}` : `L${Math.abs(streak)}`}
                                                                </span>
                                                            )}
                                                        </div>

                                                        {/* Stat mini-grid */}
                                                        <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-muted-foreground">
                                                            <div>
                                                                <span className="uppercase">PF </span>
                                                                <span className="text-foreground/70">{team.pf || 0}</span>
                                                            </div>
                                                            <div>
                                                                <span className="uppercase">PA </span>
                                                                <span className="text-foreground/70">{team.pa || 0}</span>
                                                            </div>
                                                            <div>
                                                                <span className="uppercase">DIFF </span>
                                                                <span className={diff > 0 ? "text-emerald-400" : diff < 0 ? "text-red-400" : "text-foreground"}>
                                                                    {diff > 0 ? `+${diff}` : diff}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Hover effect */}
                                                    <div
                                                        className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 pointer-events-none"
                                                        style={{ background: team.primary_color }}
                                                    />
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </main>
        </div>
    );
}
