import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGameDetail, ComparisonStat, PlayerProp } from "@/hooks/useApi";
import { Header } from "@/components/Header";
import { TeamLogo } from "@/components/TeamLogo";
import { CollapsibleSection } from "@/components/CollapsibleSection";
import { ArrowLeft, MapPin, Thermometer, Wind, User, TrendingUp, BarChart3 } from "lucide-react";

function fmtOdds(odds: number | null | undefined): string {
    if (odds == null) return "N/A";
    return odds > 0 ? `+${odds}` : `${odds}`;
}

function gameTypeLabel(game: any): string {
    const gt = game.game_type;
    const week = game.week;
    if (gt === "SB") return "Super Bowl";
    if (gt === "CON" || week === 21) return "Conference Championship";
    if (gt === "DIV" || week === 20) return "Divisional Round";
    if (gt === "WC" || week === 19) return "Wild Card";
    return `Week ${week}`;
}

/** Lighten a hex color by a percentage */
function lightenColor(hex: string, pct: number): string {
    hex = hex.replace("#", "");
    if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    const lr = Math.min(255, Math.round(r + (255 - r) * pct));
    const lg = Math.min(255, Math.round(g + (255 - g) * pct));
    const lb = Math.min(255, Math.round(b + (255 - b) * pct));
    return `rgb(${lr}, ${lg}, ${lb})`;
}

export default function GameDetail() {
    const { gameId } = useParams<{ gameId: string }>();
    const navigate = useNavigate();
    const { data, isLoading, isError } = useGameDetail(gameId || "");
    const [activeTab, setActiveTab] = useState<"overview" | "betting">("overview");

    if (isLoading) {
        return (
            <div className="min-h-screen bg-background text-foreground">
                <Header />
                <div className="container mx-auto px-4 py-20 text-center">
                    <div className="animate-pulse space-y-6">
                        <div className="h-40 glass-card rounded-xl max-w-3xl mx-auto" />
                        <div className="h-24 glass-card rounded-xl max-w-3xl mx-auto" />
                        <div className="h-64 glass-card rounded-xl max-w-3xl mx-auto" />
                    </div>
                </div>
            </div>
        );
    }

    if (isError || !data || data.error) {
        return (
            <div className="min-h-screen bg-background text-foreground">
                <Header />
                <div className="container mx-auto px-4 py-20 text-center">
                    <p className="text-red-400 text-lg mb-4">Game not found</p>
                    <button onClick={() => navigate("/matchup")} className="text-primary underline">
                        Back to Schedule
                    </button>
                </div>
            </div>
        );
    }

    const { game, win_probability, comparison, leaders, props, history, preview_text } = data;
    const isPlayed = game.is_played;
    const hasProps = !isPlayed && (props.anytime_td.length > 0 || props.over_under.length > 0);

    return (
        <div className="min-h-screen bg-background text-foreground">
            <Header />

            <main className="container mx-auto max-w-5xl px-4 py-6 space-y-6">
                {/* Back Button */}
                <button
                    onClick={() => navigate("/matchup")}
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" /> Back to Schedule
                </button>

                {/* 1. Hero Banner */}
                <HeroBanner game={game} winProb={win_probability} isPlayed={isPlayed} />

                {/* Tab Bar */}
                {hasProps && (
                    <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/10">
                        <button
                            onClick={() => setActiveTab("overview")}
                            className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                                activeTab === "overview"
                                    ? "bg-primary/15 text-primary border border-primary/30"
                                    : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                            }`}
                        >
                            <BarChart3 className="w-4 h-4" /> Overview
                        </button>
                        <button
                            onClick={() => setActiveTab("betting")}
                            className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                                activeTab === "betting"
                                    ? "bg-primary/15 text-primary border border-primary/30"
                                    : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                            }`}
                        >
                            <TrendingUp className="w-4 h-4" /> Betting Lines
                        </button>
                    </div>
                )}

                {/* Tab Content */}
                {activeTab === "overview" ? (
                    <div className="space-y-6 animate-fade-in">
                        {/* 2. Betting Lines Summary */}
                        <BettingLines game={game} winProb={win_probability} />

                        {/* 3. Game Preview */}
                        <PreviewCard text={preview_text} />

                        {/* 4. Team Comparison */}
                        {comparison.stats.length > 0 && (
                            <ComparisonSection stats={comparison.stats} game={game} />
                        )}

                        {/* 5. Top Players */}
                        {(Object.keys(leaders.home).length > 0 || Object.keys(leaders.away).length > 0) && (
                            <LeadersSection home={leaders.home} away={leaders.away} game={game} />
                        )}

                        {/* 6. H2H History */}
                        {history.length > 0 && (
                            <HistorySection history={history} />
                        )}

                        {/* 8. Game Environment */}
                        <EnvironmentFooter game={game} />
                    </div>
                ) : (
                    <div className="space-y-6 animate-fade-in">
                        {/* Betting Lines Summary at top of betting tab too */}
                        <BettingLines game={game} winProb={win_probability} />

                        {/* 7. Player Props */}
                        <PropsSection props={props} homeTeamId={game.home_team_id} game={game} />
                    </div>
                )}

                {/* If no props (played game), show everything inline without tabs */}
                {!hasProps && activeTab === "overview" && null}
            </main>
        </div>
    );
}


// ─── Hero Banner ─────────────────────────────────────────────

function HeroBanner({ game, winProb, isPlayed }: { game: any; winProb: { home: number; away: number }; isPlayed: boolean }) {
    const homeColor = game.home_color || '#4a90d9';
    const awayColor = game.away_color || '#d94a4a';
    // Use secondary color as fallback when primaries are too similar
    const homeBarColor = lightenColor(homeColor, 0.15);
    const awayBarColor = lightenColor(awayColor, 0.25);

    return (
        <div
            className="glass-card rounded-2xl p-6 relative overflow-hidden"
            style={{
                background: `linear-gradient(135deg, ${awayColor}20, transparent 40%, transparent 60%, ${homeColor}20)`
            }}
        >
            {/* Game type label */}
            <div className="text-center mb-5">
                <span className="text-sm font-medium text-foreground/70 uppercase tracking-wider">
                    {game.season} {gameTypeLabel(game)}
                </span>
                {game.gameday && (
                    <span className="text-sm text-muted-foreground ml-2">{game.gameday}</span>
                )}
            </div>

            <div className="flex items-center justify-between gap-4">
                {/* Away Team */}
                <div className="flex-1 text-center">
                    <TeamLogo team={game.away_abbr} size="lg" className="mx-auto !w-16 !h-16 mb-2" />
                    <div className="font-bold text-xl text-foreground">{game.away_name}</div>
                    <div className="text-sm text-foreground/60 mt-0.5">{game.away_record}</div>
                    {isPlayed && (
                        <div className="text-4xl font-bold mt-2 text-foreground">{game.away_score}</div>
                    )}
                </div>

                {/* Center */}
                <div className="flex flex-col items-center gap-1">
                    {isPlayed ? (
                        <span className="text-xs px-3 py-1 rounded-full bg-white/10 border border-white/20 font-medium text-foreground/80">FINAL</span>
                    ) : (
                        <span className="text-xs px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 font-medium">UPCOMING</span>
                    )}
                    <div className="w-px h-8 bg-white/15" />
                </div>

                {/* Home Team */}
                <div className="flex-1 text-center">
                    <TeamLogo team={game.home_abbr} size="lg" className="mx-auto !w-16 !h-16 mb-2" />
                    <div className="font-bold text-xl text-foreground">{game.home_name}</div>
                    <div className="text-sm text-foreground/60 mt-0.5">{game.home_record}</div>
                    {isPlayed && (
                        <div className="text-4xl font-bold mt-2 text-foreground">{game.home_score}</div>
                    )}
                </div>
            </div>

            {/* Win Probability Bar */}
            {!isPlayed && (
                <div className="mt-6">
                    <div className="flex justify-between text-xs mb-1.5">
                        <span className="font-bold text-foreground" style={{ color: awayBarColor }}>
                            {game.away_abbr} {winProb.away}%
                        </span>
                        <span className="text-foreground/60 text-[10px] uppercase tracking-wider">Win Probability</span>
                        <span className="font-bold text-foreground" style={{ color: homeBarColor }}>
                            {winProb.home}% {game.home_abbr}
                        </span>
                    </div>
                    <div className="h-4 rounded-full overflow-hidden flex bg-white/5 relative">
                        <div
                            className="h-full transition-all duration-500 flex items-center justify-end pr-2"
                            style={{
                                width: `${winProb.away}%`,
                                background: `linear-gradient(90deg, ${awayColor}90, ${awayBarColor})`,
                            }}
                        >
                            {winProb.away >= 25 && (
                                <span className="text-[10px] font-bold text-white drop-shadow-md">{winProb.away}%</span>
                            )}
                        </div>
                        <div className="w-[2px] bg-white/60 z-10 flex-shrink-0" />
                        <div
                            className="h-full transition-all duration-500 flex items-center pl-2"
                            style={{
                                width: `${winProb.home}%`,
                                background: `linear-gradient(90deg, ${homeBarColor}, ${homeColor}90)`,
                            }}
                        >
                            {winProb.home >= 25 && (
                                <span className="text-[10px] font-bold text-white drop-shadow-md">{winProb.home}%</span>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


// ─── Betting Lines ───────────────────────────────────────────

function BettingLines({ game, winProb }: { game: any; winProb: { home: number; away: number } }) {
    const spread = game.spread_line;
    const total = game.total_line;
    const homeML = game.home_moneyline;
    const awayML = game.away_moneyline;

    return (
        <div className="glass-card rounded-xl p-5">
            <div className="grid grid-cols-3 divide-x divide-white/10 text-center">
                <div className="px-4">
                    <div className="text-[10px] text-foreground/60 uppercase tracking-wider mb-2">Spread</div>
                    <div className="text-lg font-bold">
                        {spread != null
                            ? `${game.home_abbr} ${spread > 0 ? "+" : ""}${spread}`
                            : "N/A"
                        }
                    </div>
                </div>
                <div className="px-4">
                    <div className="text-[10px] text-foreground/60 uppercase tracking-wider mb-2">Moneyline</div>
                    <div className="flex justify-center items-center gap-3 text-lg">
                        <span className="text-foreground/50 text-xs">{game.away_abbr}</span>
                        <span className="font-bold">{fmtOdds(awayML)}</span>
                        <span className="text-white/15">|</span>
                        <span className="font-bold">{fmtOdds(homeML)}</span>
                        <span className="text-foreground/50 text-xs">{game.home_abbr}</span>
                    </div>
                </div>
                <div className="px-4">
                    <div className="text-[10px] text-foreground/60 uppercase tracking-wider mb-2">Total</div>
                    <div className="text-lg font-bold">
                        {total != null ? `O/U ${total}` : "N/A"}
                    </div>
                </div>
            </div>
            {!game.is_played && (
                <div className="mt-3 pt-3 border-t border-white/5 flex justify-center gap-6 text-xs text-foreground/50">
                    <span>{game.away_abbr} {winProb.away}%</span>
                    <span className="text-white/15">|</span>
                    <span>{game.home_abbr} {winProb.home}%</span>
                </div>
            )}
        </div>
    );
}


// ─── Preview Card ────────────────────────────────────────────

function PreviewCard({ text }: { text: string | null }) {
    return (
        <div className="glass-card rounded-xl p-5">
            <h3 className="text-xs text-foreground/60 uppercase tracking-wider mb-3">Game Preview</h3>
            <p className="text-sm text-foreground/50 italic">
                {text || "AI-powered game analysis coming soon."}
            </p>
        </div>
    );
}


// ─── Team Comparison ─────────────────────────────────────────

function ComparisonSection({ stats, game }: { stats: ComparisonStat[]; game: any }) {
    const offenseStats = stats.filter(s => ["ppg", "ypg", "pass_ypg", "rush_ypg", "third_down_pct", "rz_pct", "ypa"].includes(s.key));
    const defenseStats = stats.filter(s => ["opp_ppg", "opp_ypg", "sacks", "def_ints", "fum_rec"].includes(s.key));
    const turnoverStats = stats.filter(s => ["to_diff"].includes(s.key));

    return (
        <div className="glass-card rounded-xl p-5">
            <h3 className="text-xs text-foreground/60 uppercase tracking-wider mb-4">Team Comparison</h3>
            <div className="flex justify-between text-xs text-foreground/60 mb-3 px-1">
                <span className="font-medium">{game.away_abbr}</span>
                <span className="font-medium">{game.home_abbr}</span>
            </div>

            {offenseStats.length > 0 && (
                <>
                    <div className="text-[10px] text-foreground/50 uppercase tracking-widest mb-2">Offense</div>
                    {offenseStats.map(s => <StatBar key={s.key} stat={s} awayColor={game.away_color} homeColor={game.home_color} />)}
                </>
            )}
            {defenseStats.length > 0 && (
                <>
                    <div className="text-[10px] text-foreground/50 uppercase tracking-widest mb-2 mt-4">Defense</div>
                    {defenseStats.map(s => <StatBar key={s.key} stat={s} awayColor={game.away_color} homeColor={game.home_color} />)}
                </>
            )}
            {turnoverStats.length > 0 && (
                <>
                    <div className="text-[10px] text-foreground/50 uppercase tracking-widest mb-2 mt-4">Turnover</div>
                    {turnoverStats.map(s => <StatBar key={s.key} stat={s} awayColor={game.away_color} homeColor={game.home_color} />)}
                </>
            )}
        </div>
    );
}

function StatBar({ stat, awayColor, homeColor }: { stat: ComparisonStat; awayColor?: string; homeColor?: string }) {
    const h = stat.home ?? 0;
    const a = stat.away ?? 0;
    const max = Math.max(Math.abs(h), Math.abs(a), 0.01);

    const homeBetter = stat.higher_is_better ? h >= a : h <= a;
    const awayBetter = !homeBetter;

    const hPct = (Math.abs(h) / max) * 50;
    const aPct = (Math.abs(a) / max) * 50;

    const aw = awayColor || '#6b9bd2';
    const hc = homeColor || '#d26b6b';

    return (
        <div className="mb-2.5">
            <div className="flex justify-between items-center text-xs mb-1">
                <span className={awayBetter ? "text-foreground font-bold" : "text-foreground/50"}>
                    {stat.away != null ? stat.away : "-"}
                </span>
                <span className="text-[10px] text-foreground/60 uppercase">{stat.label}</span>
                <span className={homeBetter ? "text-foreground font-bold" : "text-foreground/50"}>
                    {stat.home != null ? stat.home : "-"}
                </span>
            </div>
            <div className="flex h-2 gap-0.5">
                <div className="flex-1 flex justify-end">
                    <div
                        className="h-full rounded-l-full transition-all duration-500"
                        style={{
                            width: `${aPct}%`,
                            backgroundColor: awayBetter ? lightenColor(aw, 0.1) : 'rgba(255,255,255,0.06)',
                            opacity: awayBetter ? 1 : 0.5,
                        }}
                    />
                </div>
                <div className="flex-1">
                    <div
                        className="h-full rounded-r-full transition-all duration-500"
                        style={{
                            width: `${hPct}%`,
                            backgroundColor: homeBetter ? lightenColor(hc, 0.1) : 'rgba(255,255,255,0.06)',
                            opacity: homeBetter ? 1 : 0.5,
                        }}
                    />
                </div>
            </div>
        </div>
    );
}


// ─── Top Players ─────────────────────────────────────────────

function LeadersSection({ home, away, game }: { home: Record<string, any>; away: Record<string, any>; game: any }) {
    const categories = ["passer", "rusher", "receiver"];
    const navigate = useNavigate();

    return (
        <div className="glass-card rounded-xl p-5">
            <h3 className="text-xs text-foreground/60 uppercase tracking-wider mb-4">Top Players</h3>
            <div className="grid grid-cols-2 gap-6">
                {/* Away */}
                <div>
                    <div className="text-xs text-foreground/60 mb-3 flex items-center gap-2 font-medium">
                        <TeamLogo team={game.away_abbr} size="sm" />
                        {game.away_abbr}
                    </div>
                    {categories.map(cat => {
                        const p = away[cat];
                        if (!p) return null;
                        return (
                            <div
                                key={cat}
                                className="flex items-center gap-3 mb-3 cursor-pointer hover:bg-white/5 rounded-lg p-1.5 -mx-1.5 transition-colors"
                                onClick={() => p.player_id && navigate(`/player/${p.player_id}`)}
                            >
                                {p.photoUrl ? (
                                    <img src={p.photoUrl} alt="" className="w-10 h-10 rounded-full object-cover bg-white/5" />
                                ) : (
                                    <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
                                        <User className="w-5 h-5 text-foreground/50" />
                                    </div>
                                )}
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm font-medium truncate">{p.player_name}</div>
                                    <div className="flex gap-2 text-[10px] text-foreground/50">
                                        {p.stats?.map((s: any) => (
                                            <span key={s.label}>{s.value} {s.label}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Home */}
                <div>
                    <div className="text-xs text-foreground/60 mb-3 flex items-center gap-2 font-medium">
                        <TeamLogo team={game.home_abbr} size="sm" />
                        {game.home_abbr}
                    </div>
                    {categories.map(cat => {
                        const p = home[cat];
                        if (!p) return null;
                        return (
                            <div
                                key={cat}
                                className="flex items-center gap-3 mb-3 cursor-pointer hover:bg-white/5 rounded-lg p-1.5 -mx-1.5 transition-colors"
                                onClick={() => p.player_id && navigate(`/player/${p.player_id}`)}
                            >
                                {p.photoUrl ? (
                                    <img src={p.photoUrl} alt="" className="w-10 h-10 rounded-full object-cover bg-white/5" />
                                ) : (
                                    <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
                                        <User className="w-5 h-5 text-foreground/50" />
                                    </div>
                                )}
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm font-medium truncate">{p.player_name}</div>
                                    <div className="flex gap-2 text-[10px] text-foreground/50">
                                        {p.stats?.map((s: any) => (
                                            <span key={s.label}>{s.value} {s.label}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}


// ─── H2H History ─────────────────────────────────────────────

function HistorySection({ history }: { history: any[] }) {
    return (
        <div className="glass-card rounded-xl p-5">
            <h3 className="text-xs text-foreground/60 uppercase tracking-wider mb-4">Head-to-Head History</h3>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-xs text-foreground/50 border-b border-white/5">
                            <th className="text-left py-2 font-normal">Date</th>
                            <th className="text-left py-2 font-normal">Matchup</th>
                            <th className="text-center py-2 font-normal">Score</th>
                            <th className="text-right py-2 font-normal">Spread</th>
                        </tr>
                    </thead>
                    <tbody>
                        {history.map((g, i) => {
                            const hs = g.home_score ?? "-";
                            const as_ = g.away_score ?? "-";
                            return (
                                <tr key={i} className="border-b border-white/5 last:border-0">
                                    <td className="py-2 text-foreground/50">{g.gameday || `${g.season} Wk${g.week}`}</td>
                                    <td className="py-2">{g.away_team} @ {g.home_team}</td>
                                    <td className="py-2 text-center font-medium">{as_} - {hs}</td>
                                    <td className="py-2 text-right text-foreground/50">
                                        {g.spread_line != null ? (g.spread_line > 0 ? `+${g.spread_line}` : g.spread_line) : ""}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}


// ─── Player Props ────────────────────────────────────────────

function PropsSection({ props, homeTeamId, game }: { props: { anytime_td: PlayerProp[]; over_under: PlayerProp[] }; homeTeamId?: number; game: any }) {
    return (
        <div className="space-y-4">
            {/* Anytime TD — collapsed by default */}
            {props.anytime_td.length > 0 && (
                <CollapsibleSection
                    title="Anytime Touchdown Scorer"
                    badge={`${props.anytime_td.length} players`}
                >
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 -mx-4 -my-4 px-4 py-3">
                        {props.anytime_td.map((p, i) => (
                            <div key={i} className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors">
                                <div className="flex items-center gap-2">
                                    <TeamLogo team={p.team_id === homeTeamId ? game.home_abbr : game.away_abbr} size="sm" />
                                    <div>
                                        <span className="text-sm font-medium">{p.player_name}</span>
                                        <span className="text-[10px] text-foreground/60 ml-1.5">{p.position}</span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={`text-sm font-bold ${
                                        (p.best_odds ?? 0) < 0 ? "text-emerald-400" : "text-foreground"
                                    }`}>
                                        {fmtOdds(p.best_odds ?? null)}
                                    </span>
                                    <span className="text-[9px] text-foreground/50 uppercase">{p.best_vendor}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </CollapsibleSection>
            )}

            {/* Over/Under grouped by prop type — each category collapsed */}
            {props.over_under.length > 0 && (
                <CollapsibleSection
                    title="Player Prop Lines"
                    badge={`${props.over_under.length} lines`}
                >
                    <PropsByCategory
                        props={props.over_under}
                        game={game}
                        homeTeamId={homeTeamId}
                    />
                </CollapsibleSection>
            )}
        </div>
    );
}

function PropsByCategory({ props, game, homeTeamId }: {
    props: PlayerProp[];
    game: any;
    homeTeamId?: number;
}) {
    const groups: Record<string, PlayerProp[]> = {};
    for (const p of props) {
        const cat = p.prop_type || "other";
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(p);
    }

    const CATEGORY_ORDER = ["passing_yards", "rushing_yards", "receiving_yards", "player_pass_tds", "player_rush_att", "player_pass_att"];
    const sorted = Object.entries(groups).sort(([a], [b]) => {
        const ai = CATEGORY_ORDER.indexOf(a);
        const bi = CATEGORY_ORDER.indexOf(b);
        return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });

    const CATEGORY_LABELS: Record<string, string> = {
        passing_yards: "Passing Yards",
        rushing_yards: "Rushing Yards",
        receiving_yards: "Receiving Yards",
        player_pass_tds: "Pass TDs",
        player_rush_att: "Rush Attempts",
        player_pass_att: "Pass Attempts",
        player_rush_rec_yds: "Rush+Rec Yards",
        player_longest_rush: "Longest Rush",
        player_longest_rec: "Longest Reception",
    };

    return (
        <div className="space-y-3 -mx-4 -my-4 px-1 py-1">
            {sorted.map(([cat, items]) => (
                <CollapsibleSection
                    key={cat}
                    title={CATEGORY_LABELS[cat] || cat.replace(/_/g, " ")}
                    badge={`${items.length} lines`}
                >
                    <table className="w-full text-xs -mx-4 -my-4">
                        <thead>
                            <tr className="text-foreground/25 border-b border-white/5">
                                <th className="text-left py-1.5 font-normal">Player</th>
                                <th className="text-center py-1.5 font-normal">Line</th>
                                <th className="text-center py-1.5 font-normal">Over</th>
                                <th className="text-center py-1.5 font-normal">Under</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map((p, i) => (
                                <tr key={i} className="border-b border-white/[0.03] last:border-0">
                                    <td className="py-2">
                                        <div className="flex items-center gap-1.5">
                                            <TeamLogo team={p.team_id === homeTeamId ? game.home_abbr : game.away_abbr} size="sm" />
                                            <span className="text-sm font-medium">{p.player_name}</span>
                                            <span className="text-foreground/25 text-[10px]">{p.position}</span>
                                        </div>
                                    </td>
                                    <td className="text-center font-medium text-foreground/70">{p.line_value}</td>
                                    <td className="text-center">
                                        <span className="text-emerald-400 font-medium">{fmtOdds(p.best_over_odds ?? null)}</span>
                                        <span className="text-[8px] text-foreground/20 ml-0.5">{p.best_over_vendor}</span>
                                    </td>
                                    <td className="text-center">
                                        <span className="text-red-400 font-medium">{fmtOdds(p.best_under_odds ?? null)}</span>
                                        <span className="text-[8px] text-foreground/20 ml-0.5">{p.best_under_vendor}</span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </CollapsibleSection>
            ))}
        </div>
    );
}


// ─── Game Environment ────────────────────────────────────────

function EnvironmentFooter({ game }: { game: any }) {
    const parts: string[] = [];
    if (game.stadium) parts.push(game.stadium);
    if (game.surface) parts.push(game.surface);
    if (game.roof) parts.push(game.roof);

    const hasMeta = parts.length > 0 || game.temp != null || game.wind != null || game.referee || game.home_coach || game.away_coach;
    if (!hasMeta) return null;

    return (
        <div className="glass-card rounded-xl p-4">
            <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5 text-xs text-foreground/60">
                {parts.length > 0 && (
                    <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" /> {parts.join(" \u2022 ")}
                    </span>
                )}
                {game.temp != null && (
                    <span className="flex items-center gap-1">
                        <Thermometer className="w-3 h-3" /> {game.temp}&deg;F
                    </span>
                )}
                {game.wind != null && (
                    <span className="flex items-center gap-1">
                        <Wind className="w-3 h-3" /> {game.wind} mph
                    </span>
                )}
                {game.referee && <span>Ref: {game.referee}</span>}
                {game.home_coach && <span>{game.home_abbr}: {game.home_coach}</span>}
                {game.away_coach && <span>{game.away_abbr}: {game.away_coach}</span>}
            </div>
        </div>
    );
}
