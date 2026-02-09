
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWeeklySchedule, useLatestWeek } from "@/hooks/useApi";
import { Header } from "@/components/Header";
import { Calendar } from "lucide-react";
import { TeamLogo } from "@/components/TeamLogo";
import { cn } from "@/lib/utils";

const WEEK_LABELS: Record<number, string> = {
    19: "Wild Card",
    20: "Divisional",
    21: "Conf Championship",
    22: "Super Bowl",
};

function weekLabel(w: number): string {
    return WEEK_LABELS[w] || `Week ${w}`;
}

const SHORT_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function formatGameday(raw: string | null | undefined): string {
    if (!raw) return "";
    // Handle ISO date like "2026-01-25"
    const parts = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (parts) {
        const d = new Date(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3]));
        return `${SHORT_DAYS[d.getDay()]}, ${SHORT_MONTHS[d.getMonth()]} ${d.getDate()}`;
    }
    return raw;
}

export default function Matchup() {
    const [season, setSeason] = useState(2025);
    const [week, setWeek] = useState<number | null>(null);
    const navigate = useNavigate();

    const { data: latestWeek } = useLatestWeek(season);

    useEffect(() => {
        if (latestWeek && week === null) {
            setWeek(latestWeek);
        }
    }, [latestWeek, week]);

    // Reset week when season changes
    useEffect(() => {
        setWeek(null);
    }, [season]);

    const activeWeek = week ?? latestWeek ?? 1;
    const { data: games, isLoading } = useWeeklySchedule(season, activeWeek);

    // Build week options: 1-18 regular + 19-22 playoff, reversed
    const weeks = [
        ...Array.from({ length: 4 }, (_, i) => 22 - i),   // 22,21,20,19
        ...Array.from({ length: 18 }, (_, i) => 18 - i),   // 18,17,...,1
    ];

    return (
        <div className="min-h-screen bg-background text-foreground">
            <Header />

            <main className="container mx-auto px-4 py-8">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 animate-fade-in">
                    <div>
                        <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/50 mb-2">
                            Weekly Schedule
                        </h1>
                        <p className="text-muted-foreground flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-primary" />
                            Scores & Lines
                        </p>
                    </div>

                    <div className="flex gap-2">
                        <select
                            value={season}
                            onChange={(e) => setSeason(Number(e.target.value))}
                            className="bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5 text-sm text-foreground/80 focus:outline-none focus:ring-1 focus:ring-white/20"
                        >
                            <option value={2025}>2025</option>
                            <option value={2024}>2024</option>
                            <option value={2023}>2023</option>
                        </select>
                        <select
                            value={activeWeek}
                            onChange={(e) => setWeek(Number(e.target.value))}
                            className="bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5 text-sm text-foreground/80 focus:outline-none focus:ring-1 focus:ring-white/20"
                        >
                            {weeks.map(w => (
                                <option key={w} value={w}>{weekLabel(w)}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {isLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="h-32 glass-card rounded-xl" />
                        ))}
                    </div>
                ) : !games?.length ? (
                    <div className="text-center text-muted-foreground py-16 text-lg">
                        No games found for {weekLabel(activeWeek)}, {season}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 animate-slide-up">
                        {games.map((game) => {
                            const isPlayed = game.home_score != null && game.away_score != null;
                            const spread = game.spread_line;
                            const total = (game as any).total_line;
                            const homeML = (game as any).home_moneyline;
                            const awayML = (game as any).away_moneyline;
                            const gameType = (game as any).game_type;
                            const awayWon = isPlayed && (game.away_score ?? 0) > (game.home_score ?? 0);
                            const homeWon = isPlayed && (game.home_score ?? 0) > (game.away_score ?? 0);

                            return (
                                <div
                                    key={game.nflverse_game_id}
                                    onClick={() => navigate(`/game/${game.nflverse_game_id}`)}
                                    className="glass-card glass-card-interactive rounded-xl relative overflow-hidden cursor-pointer group"
                                >
                                    {/* Top gradient accent */}
                                    <div
                                        className="absolute top-0 left-0 w-full h-[2px]"
                                        style={{ background: `linear-gradient(90deg, ${game.away_color || '#444'}, ${game.home_color || '#444'})` }}
                                    />

                                    <div className="p-5">
                                        {/* Header row */}
                                        <div className="flex justify-between items-center mb-4">
                                            <div className="text-xs text-muted-foreground tracking-wide">
                                                {formatGameday(game.gameday) || weekLabel(game.week)}
                                            </div>
                                            {isPlayed ? (
                                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                                                    Final
                                                </span>
                                            ) : (
                                                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                    {gameType === "SB" ? "Super Bowl" : "Upcoming"}
                                                </span>
                                            )}
                                        </div>

                                        {/* Matchup */}
                                        <div className="flex items-center justify-between">
                                            {/* Away */}
                                            <div className="flex items-center gap-3 flex-1 min-w-0">
                                                <TeamLogo team={game.away_team} size="md" />
                                                <div className="min-w-0">
                                                    <div className={cn(
                                                        "font-bold text-sm",
                                                        isPlayed && !awayWon && "text-foreground/40"
                                                    )}>{game.away_team}</div>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-4 px-2">
                                                <span className={cn(
                                                    "text-2xl font-mono font-bold tabular-nums",
                                                    isPlayed
                                                        ? awayWon ? "text-white" : "text-foreground/30"
                                                        : "text-foreground/50"
                                                )}>
                                                    {game.away_score ?? "-"}
                                                </span>
                                                <div className="w-px h-5 bg-white/10" />
                                                <span className={cn(
                                                    "text-2xl font-mono font-bold tabular-nums",
                                                    isPlayed
                                                        ? homeWon ? "text-white" : "text-foreground/30"
                                                        : "text-foreground/50"
                                                )}>
                                                    {game.home_score ?? "-"}
                                                </span>
                                            </div>

                                            {/* Home */}
                                            <div className="flex items-center gap-3 flex-1 min-w-0 justify-end">
                                                <div className="min-w-0 text-right">
                                                    <div className={cn(
                                                        "font-bold text-sm",
                                                        isPlayed && !homeWon && "text-foreground/40"
                                                    )}>{game.home_team}</div>
                                                </div>
                                                <TeamLogo team={game.home_team} size="md" />
                                            </div>
                                        </div>

                                        {/* Betting lines — collapsed, revealed on hover */}
                                        {(spread != null || total != null) && (
                                            <div className="mt-3 pt-3 border-t border-white/[0.04] flex items-center justify-center gap-4 text-[10px] font-mono text-muted-foreground max-h-0 opacity-0 group-hover:max-h-8 group-hover:opacity-100 overflow-hidden transition-all duration-200">
                                                {spread != null && (
                                                    <span>{game.home_team} {spread > 0 ? "+" : ""}{spread}</span>
                                                )}
                                                {total != null && (
                                                    <span>O/U {total}</span>
                                                )}
                                                {homeML != null && awayML != null && (
                                                    <span>ML {awayML > 0 ? "+" : ""}{awayML} / {homeML > 0 ? "+" : ""}{homeML}</span>
                                                )}
                                            </div>
                                        )}
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
