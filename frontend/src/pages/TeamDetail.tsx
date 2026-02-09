import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useStandings, useTeamSchedule, useTeamRoster, RosterPlayer, useTeamSeasonStats, useTeamSnaps, useTeamLeaders } from "@/hooks/useApi";
import { Header } from "@/components/Header";
import { TeamLogo } from "@/components/TeamLogo";
import { StatCard } from "@/components/StatCard";
import { CollapsibleSection } from "@/components/CollapsibleSection";
import { Calendar, Users, Activity, BarChart3 } from "lucide-react";
import { cn, formatStat, ensureReadableColor } from "@/lib/utils";

/** Format "2025-01-25" → "Sat, Jan 25" */
function fmtDate(raw: string | null | undefined): string {
    if (!raw) return "";
    try {
        const d = new Date(raw + "T12:00:00");
        return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
    } catch { return raw; }
}

const POSITION_GROUPS = [
    { title: "Quarterbacks", pos: ["QB"] },
    { title: "Running Backs", pos: ["RB", "FB"] },
    { title: "Wide Receivers", pos: ["WR", "WR-2", "WR-3"] },
    { title: "Tight Ends", pos: ["TE"] },
    { title: "Offensive Line", pos: ["T", "G", "C", "OL", "OT", "OG", "LT", "RT", "LG", "RG"] },
    { title: "Defensive Line", pos: ["DE", "DT", "NT", "DL", "LDE", "RDE", "LDT", "RDT"] },
    { title: "Linebackers", pos: ["LB", "ILB", "OLB", "MLB", "LILB", "RILB", "SLB", "WLB"] },
    { title: "Defensive Backs", pos: ["CB", "S", "SS", "FS", "DB", "LCB", "RCB", "NB"] },
    { title: "Special Teams", pos: ["K", "P", "H", "LS", "PK", "KR", "PR"] },
];

type TabId = 'overview' | 'stats' | 'roster' | 'schedule';

export default function TeamDetail() {
    const { id: teamAbbr } = useParams();
    const navigate = useNavigate();
    const [season] = useState(2025);
    const [activeTab, setActiveTab] = useState<TabId>('overview');

    const { data: standings } = useStandings(season);
    const team = standings?.find(t => t.team === teamAbbr);
    const { data: rosterData, isLoading: rosterLoading } = useTeamRoster(teamAbbr || '', season);
    const { data: schedule } = useTeamSchedule(teamAbbr || '', season);
    const { data: seasonStats, isLoading: seasonStatsLoading } = useTeamSeasonStats(teamAbbr || '', season);
    const { data: teamSnaps } = useTeamSnaps(teamAbbr || '', season);
    const { data: teamLeaders } = useTeamLeaders(teamAbbr || '', season);

    const groupedRoster = useMemo(() => {
        if (!rosterData) return {};
        const groups: Record<string, RosterPlayer[]> = {};
        const getGroup = (p: string) => {
            for (const g of POSITION_GROUPS) {
                if (g.pos.includes(p)) return g.title;
            }
            return "Other";
        };
        rosterData.forEach(player => {
            if ((player.depth ?? 99) >= 3 && (!player.jersey_number || String(player.jersey_number) === 'None')) return;
            const group = getGroup(player.position);
            if (!groups[group]) groups[group] = [];
            groups[group].push(player);
        });
        return groups;
    }, [rosterData]);

    if (!team && !standings) return <div className="min-h-screen bg-background flex items-center justify-center">Loading...</div>;

    const teamColors = team ? { primary: team.primary_color, secondary: team.secondary_color } : undefined;
    const tc = team?.primary_color;

    // Computed stats
    const passRate = seasonStats?.pass_rate ?? (
        seasonStats?.passing_attempts && seasonStats?.rushing_attempts
            ? (seasonStats.passing_attempts / (seasonStats.passing_attempts + seasonStats.rushing_attempts)) * 100
            : null
    );
    const netYardsDiff = seasonStats?.net_yards_diff ?? (
        seasonStats?.net_total_offensive_yards && seasonStats?.opp_total_offensive_yards
            ? seasonStats.net_total_offensive_yards - seasonStats.opp_total_offensive_yards
            : null
    );
    const pointsPerDrive = seasonStats?.points_per_100_yards ?? (
        seasonStats?.total_points && seasonStats?.total_offensive_yards
            ? (seasonStats.total_points / (seasonStats.total_offensive_yards || 1)) * 100
            : null
    );
    const formatPct = (value: unknown) => (value === null || value === undefined) ? "—" : `${formatStat(value, { decimals: 1 })}%`;
    const calcPct = (conv?: number, att?: number, fallback?: unknown) => {
        if (conv !== undefined && att !== undefined && att > 0) return (conv / att) * 100;
        return fallback as any;
    };
    const parseEfficiency = (value?: string | null) => {
        if (!value || typeof value !== "string" || !value.includes("-")) return null;
        const [madeRaw, attRaw] = value.split("-");
        const made = Number(madeRaw);
        const att = Number(attRaw);
        if (!Number.isFinite(made) || !Number.isFinite(att) || att <= 0) return null;
        return (made / att) * 100;
    };
    const fgPct = calcPct(
        seasonStats?.kicking_field_goals_made,
        seasonStats?.kicking_field_goals_attempted,
        seasonStats?.kicking_field_goal_pct ?? seasonStats?.kicking_pct
    );
    const pointDiffRank = (() => {
        if (!standings || !team) return undefined;
        const index = standings
            .filter(s => typeof s.diff === "number")
            .sort((a, b) => (b.diff ?? 0) - (a.diff ?? 0))
            .findIndex(s => s.team === team.team);
        return index >= 0 ? index + 1 : undefined;
    })();
    const atsCoverRank = (() => {
        if (!standings || !team) return undefined;
        const withPct = standings
            .map(s => {
                const games = s.games || 0;
                const pct = games ? (s.ats_wins / games) * 100 : null;
                return { team: s.team, pct };
            })
            .filter(s => typeof s.pct === "number")
            .sort((a, b) => (b.pct ?? 0) - (a.pct ?? 0));
        const index = withPct.findIndex(s => s.team === team.team);
        return index >= 0 ? index + 1 : undefined;
    })();
    const ranks = { ...(seasonStats?.ranks || {}), point_diff: pointDiffRank, ats_cover_pct: atsCoverRank };
    const statCard = (
        label: string,
        value: React.ReactNode,
        rankKey?: string,
        subValue?: string,
        trend?: "positive" | "negative" | "neutral"
    ) => (
        <StatCard
            label={label}
            value={value}
            subValue={subValue}
            teamColors={teamColors}
            trend={trend}
            rank={rankKey ? ranks[rankKey] : undefined}
        />
    );
    const formatDuration = (seconds?: number | null) => {
        if (!seconds && seconds !== 0) return "—";
        const total = Math.round(seconds);
        const mins = Math.floor(total / 60);
        const secs = total % 60;
        return `${mins}:${secs.toString().padStart(2, "0")}`;
    };
    const bgStyle = team ? {
        background: `linear-gradient(to bottom, ${team.primary_color}20, transparent)`
    } : {};

    // Tabs config
    const TABS: { id: TabId; label: string; icon: typeof Activity }[] = [
        { id: 'overview', label: 'Overview', icon: Activity },
        { id: 'stats', label: 'Stats', icon: BarChart3 },
        { id: 'roster', label: 'Roster', icon: Users },
        { id: 'schedule', label: 'Schedule', icon: Calendar },
    ];

    return (
        <div className="min-h-screen bg-background text-foreground pb-20">
            <Header />

            {/* Hero — slightly more compact */}
            <div className="relative pt-8 pb-6 px-4 overflow-hidden border-b border-white/5" style={bgStyle}>
                <div className="container mx-auto max-w-5xl flex flex-col md:flex-row items-center gap-8 relative z-10">
                    <div className="relative group">
                        <div className="absolute inset-0 bg-white/10 blur-3xl rounded-full" />
                        {/* Team color glow ring */}
                        {tc && <div className="absolute -inset-2 rounded-full blur-xl opacity-20" style={{ background: tc }} />}
                        <TeamLogo team={teamAbbr} size="lg" className="scale-125 relative z-10 drop-shadow-2xl" />
                    </div>

                    <div className="text-center md:text-left">
                        <h1 className="text-5xl font-bold mb-2">{team?.team_name || teamAbbr}</h1>
                        <div className="flex items-center justify-center md:justify-start gap-4 text-xl font-mono text-muted-foreground">
                            <span className="text-foreground font-bold">{team?.wins}-{team?.losses}{(team?.ties ?? 0) > 0 && `-${team?.ties}`}</span>
                            <span>|</span>
                            <span>ATS: {team?.ats_wins}-{team?.ats_losses}</span>
                            {team?.win_streak != null && team.win_streak !== 0 && (
                                <>
                                    <span>|</span>
                                    <span className={team.win_streak > 0 ? "text-emerald-400" : "text-red-400"}>
                                        {team.win_streak > 0 ? `W${team.win_streak}` : `L${Math.abs(team.win_streak)}`}
                                    </span>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Record Splits */}
            {team && (team.conference_record || team.division_record || team.home_record || team.road_record) && (
                <div className="container mx-auto max-w-5xl px-4 mt-4">
                    <div className="flex items-center justify-center gap-4 text-xs font-mono text-muted-foreground">
                        {team.conference_record && <span>CONF <span className="text-foreground">{team.conference_record}</span></span>}
                        {team.division_record && <><span className="text-white/20">&middot;</span><span>DIV <span className="text-foreground">{team.division_record}</span></span></>}
                        {team.home_record && <><span className="text-white/20">&middot;</span><span>HOME <span className="text-foreground">{team.home_record}</span></span></>}
                        {team.road_record && <><span className="text-white/20">&middot;</span><span>AWAY <span className="text-foreground">{team.road_record}</span></span></>}
                    </div>
                </div>
            )}

            {/* 4 Tabs */}
            <div className="container mx-auto max-w-5xl px-4 mt-6">
                <div className="flex items-center border-b border-border mb-6">
                    {TABS.map(tab => {
                        const readableColor = ensureReadableColor(team?.primary_color);
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={cn(
                                    "flex items-center gap-1.5 px-4 py-3 text-sm font-semibold uppercase tracking-wider transition-colors relative whitespace-nowrap",
                                    activeTab === tab.id ? "" : "text-muted-foreground hover:text-foreground"
                                )}
                                style={{ color: activeTab === tab.id && team ? readableColor : undefined }}
                            >
                                <tab.icon className="w-4 h-4" />
                                {tab.label}
                                {activeTab === tab.id && team && (
                                    <div className="absolute bottom-0 left-0 w-full h-0.5" style={{ backgroundColor: readableColor }} />
                                )}
                            </button>
                        );
                    })}
                </div>

                <div className="animate-fade-in">
                    {/* ═══ OVERVIEW TAB ═══ */}
                    {activeTab === 'overview' && team && (
                        <div className="space-y-4">
                            <CollapsibleSection title="Points & Record" defaultOpen teamColor={tc}>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                    {statCard("Points For", formatStat(team.pf, { integer: true }), "total_points", "Season total")}
                                    {statCard("Points Allowed", formatStat(team.pa, { integer: true }), "opp_total_points", "Defense")}
                                    {statCard("Point Diff", formatStat(team.diff, { integer: true }), "point_diff", "Margin")}
                                    {statCard("ATS Cover %", formatPct((team.ats_wins / (team.games || 1)) * 100), "ats_cover_pct", "Against spread")}
                                    {statCard("Pass Rate", formatPct(passRate), "pass_rate", "Pass / total plays")}
                                    {statCard("Net Yards Diff", formatStat(netYardsDiff, { integer: true }), "net_yards_diff", "Net off - opp")}
                                    {statCard("Yards / Play", formatStat(seasonStats?.yards_per_pass_attempt), "yards_per_pass_attempt", "Offense")}
                                    {statCard("Pts / 100 Yds", formatStat(pointsPerDrive), "points_per_100_yards", "Efficiency")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Pace & Possession" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Total Plays", formatStat(seasonStats?.game_total_plays, { integer: true }), "game_total_plays")}
                                    {statCard("Plays / G", formatStat(seasonStats?.game_total_plays_pg), "game_total_plays_pg")}
                                    {statCard("Total Yards", formatStat(seasonStats?.game_total_yards, { integer: true }), "game_total_yards")}
                                    {statCard("Yards / G", formatStat(seasonStats?.game_total_yards_pg), "game_total_yards_pg")}
                                    {statCard("Total Drives", formatStat(seasonStats?.game_total_drives, { integer: true }), "game_total_drives")}
                                    {statCard("Drives / G", formatStat(seasonStats?.game_total_drives_pg), "game_total_drives_pg")}
                                    {statCard("Poss Time", formatDuration(seasonStats?.game_possession_seconds), "game_possession_seconds")}
                                    {statCard("Poss / G", formatDuration(seasonStats?.game_possession_pg), "game_possession_pg")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Conversions" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard(
                                        "3rd Down",
                                        seasonStats?.third_down_efficiency || "—",
                                        "third_down_pct",
                                        formatPct(calcPct(seasonStats?.misc_third_down_convs, seasonStats?.misc_third_down_attempts, seasonStats?.third_down_pct))
                                    )}
                                    {statCard("3rd Convs", formatStat(seasonStats?.misc_third_down_convs, { integer: true }), "misc_third_down_convs")}
                                    {statCard("3rd Att", formatStat(seasonStats?.misc_third_down_attempts, { integer: true }), "misc_third_down_attempts")}
                                    {statCard(
                                        "4th Down",
                                        seasonStats?.fourth_down_efficiency || "—",
                                        "fourth_down_pct",
                                        formatPct(calcPct(seasonStats?.misc_fourth_down_convs, seasonStats?.misc_fourth_down_attempts, seasonStats?.fourth_down_pct))
                                    )}
                                    {statCard("4th Convs", formatStat(seasonStats?.misc_fourth_down_convs, { integer: true }), "misc_fourth_down_convs")}
                                    {statCard("4th Att", formatStat(seasonStats?.misc_fourth_down_attempts, { integer: true }), "misc_fourth_down_attempts")}
                                    {(seasonStats?.red_zone_scores !== null && seasonStats?.red_zone_scores !== undefined && seasonStats?.red_zone_attempts !== null && seasonStats?.red_zone_attempts !== undefined) || seasonStats?.red_zone_efficiency ? statCard(
                                        "Red Zone",
                                        seasonStats?.red_zone_scores !== null && seasonStats?.red_zone_scores !== undefined && seasonStats?.red_zone_attempts !== null && seasonStats?.red_zone_attempts !== undefined
                                            ? `${formatStat(seasonStats.red_zone_scores, { integer: true })}-${formatStat(seasonStats.red_zone_attempts, { integer: true })}`
                                            : (seasonStats?.red_zone_efficiency || "—"),
                                        "red_zone_pct",
                                        formatPct(seasonStats?.red_zone_pct ?? parseEfficiency(seasonStats?.red_zone_efficiency))
                                    ) : null}
                                    {seasonStats?.goal_to_go_efficiency ? statCard(
                                        "Goal To Go",
                                        seasonStats?.goal_to_go_efficiency || "—",
                                        "goal_to_go_pct",
                                        formatPct(parseEfficiency(seasonStats?.goal_to_go_efficiency))
                                    ) : null}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Turnovers & Discipline" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Penalties", formatStat(seasonStats?.misc_total_penalties, { integer: true }), "misc_total_penalties")}
                                    {statCard("Penalty Yds", formatStat(seasonStats?.misc_total_penalty_yards, { integer: true }), "misc_total_penalty_yards")}
                                    {statCard("Giveaways", formatStat(seasonStats?.misc_total_giveaways, { integer: true }), "misc_total_giveaways")}
                                    {statCard("Takeaways", formatStat(seasonStats?.misc_total_takeaways, { integer: true }), "misc_total_takeaways")}
                                    {statCard("Turnover Diff", formatStat(seasonStats?.turnover_differential, { integer: true }), "turnover_differential")}
                                    {statCard("Fumbles Lost", formatStat(seasonStats?.fumbles_lost, { integer: true }), "fumbles_lost")}
                                    {statCard("Def TD", formatStat(seasonStats?.defensive_touchdowns, { integer: true }), "defensive_touchdowns")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Top Players" teamColor={tc}>
                                {teamLeaders && Object.keys(teamLeaders).length ? (
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {[
                                            { key: "passer", title: "Top Passer" },
                                            { key: "rusher", title: "Top Rusher" },
                                            { key: "receiver", title: "Top Receiver" },
                                            { key: "tackler", title: "Tackle Leader" },
                                            { key: "int_leader", title: "INT Leader" },
                                            { key: "sack_leader", title: "Sack Leader" },
                                        ].map(({ key, title }) => {
                                            const leader = teamLeaders[key];
                                            if (!leader) return null;
                                            return (
                                                <div key={key} className="glass-card rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:bg-white/5 transition-colors" onClick={() => navigate(`/player/${leader.player_id}`)}>
                                                    {leader.photoUrl ? (
                                                        <img src={leader.photoUrl} alt="" className="w-14 h-14 rounded-full object-cover flex-shrink-0" loading="lazy" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                                                    ) : (
                                                        <div className="w-14 h-14 rounded-full bg-white/10 flex-shrink-0" />
                                                    )}
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</div>
                                                        <div className="font-semibold text-sm truncate">{leader.player_name}</div>
                                                        <div className="text-xs text-muted-foreground">{leader.position}</div>
                                                        <div className="flex gap-3 mt-1.5">
                                                            {leader.stats?.map((s: any) => (
                                                                <div key={s.label} className="text-center">
                                                                    <div className="text-sm font-bold font-mono">{formatStat(s.value, { integer: s.label !== 'CMP%', decimals: s.label === 'CMP%' ? 1 : undefined })}</div>
                                                                    <div className="text-[9px] text-muted-foreground uppercase">{s.label}</div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                ) : (
                                    <div className="text-sm text-muted-foreground">Top players not available.</div>
                                )}
                            </CollapsibleSection>

                            {seasonStatsLoading && (
                                <div className="glass-card rounded-xl p-6 animate-pulse h-32" />
                            )}
                        </div>
                    )}

                    {/* ═══ STATS TAB (Offense + Defense + Special merged) ═══ */}
                    {activeTab === 'stats' && (
                        <div className="space-y-4">
                            {/* OFFENSE */}
                            <CollapsibleSection title="Passing" defaultOpen teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Attempts", formatStat(seasonStats?.passing_attempts, { integer: true }), "passing_attempts")}
                                    {statCard("Completions", formatStat(seasonStats?.passing_completions, { integer: true }), "passing_completions")}
                                    {statCard("Comp %", formatPct(seasonStats?.passing_completion_pct), "passing_completion_pct")}
                                    {statCard("Pass Yards", formatStat(seasonStats?.passing_yards, { integer: true }), "passing_yards")}
                                    {statCard("Pass Y/G", formatStat(seasonStats?.passing_yards_per_game), "passing_yards_per_game")}
                                    {statCard("Net Pass Y/G", formatStat(seasonStats?.net_passing_yards_per_game), "net_passing_yards_per_game")}
                                    {statCard("Y/A", formatStat(seasonStats?.yards_per_pass_attempt), "yards_per_pass_attempt")}
                                    {statCard("Net Y/A", formatStat(seasonStats?.net_yards_per_pass_attempt), "net_yards_per_pass_attempt")}
                                    {statCard("Pass TD", formatStat(seasonStats?.passing_touchdowns, { integer: true }), "passing_touchdowns")}
                                    {statCard("INT", formatStat(seasonStats?.passing_interceptions, { integer: true }), "passing_interceptions")}
                                    {statCard("Sacks", formatStat(seasonStats?.passing_sacks, { integer: true }), "passing_sacks")}
                                    {statCard("QB Rating", formatStat(seasonStats?.qb_rating), "qb_rating")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Rushing" defaultOpen teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Rush Att", formatStat(seasonStats?.rushing_attempts, { integer: true }), "rushing_attempts")}
                                    {statCard("Rush Yards", formatStat(seasonStats?.rushing_yards, { integer: true }), "rushing_yards")}
                                    {statCard("Rush Y/G", formatStat(seasonStats?.rushing_yards_per_game), "rushing_yards_per_game")}
                                    {statCard("Y/R", formatStat(seasonStats?.rushing_average), "rushing_average")}
                                    {statCard("Rush TD", formatStat(seasonStats?.rushing_touchdowns, { integer: true }), "rushing_touchdowns")}
                                    {statCard("Rush Fum", formatStat(seasonStats?.rushing_fumbles, { integer: true }), "rushing_fumbles")}
                                    {statCard("Rush Fum Lost", formatStat(seasonStats?.rushing_fumbles_lost, { integer: true }), "rushing_fumbles_lost")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Receiving" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Receptions", formatStat(seasonStats?.receiving_receptions, { integer: true }), "receiving_receptions")}
                                    {statCard("Rec Yards", formatStat(seasonStats?.receiving_yards, { integer: true }), "receiving_yards")}
                                    {statCard("Rec Y/G", formatStat(seasonStats?.receiving_yards_per_game), "receiving_yards_per_game")}
                                    {statCard("Y/Rec", formatStat(seasonStats?.receiving_average), "receiving_average")}
                                    {statCard("Rec TD", formatStat(seasonStats?.receiving_touchdowns, { integer: true }), "receiving_touchdowns")}
                                    {statCard("Rec Fum", formatStat(seasonStats?.receiving_fumbles, { integer: true }), "receiving_fumbles")}
                                    {statCard("Rec Fum Lost", formatStat(seasonStats?.receiving_fumbles_lost, { integer: true }), "receiving_fumbles_lost")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="First Downs & Explosives" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Total 1D", formatStat(seasonStats?.misc_first_downs, { integer: true }), "misc_first_downs")}
                                    {statCard("Pass 1D", formatStat(seasonStats?.misc_first_downs_passing, { integer: true }), "misc_first_downs_passing")}
                                    {statCard("Rush 1D", formatStat(seasonStats?.misc_first_downs_rushing, { integer: true }), "misc_first_downs_rushing")}
                                    {statCard("Pen 1D", formatStat(seasonStats?.misc_first_downs_penalty, { integer: true }), "misc_first_downs_penalty")}
                                    {seasonStats?.passing_sack_yards_lost ? statCard("Sack Yds", formatStat(seasonStats?.passing_sack_yards_lost, { integer: true }), "passing_sack_yards_lost") : null}
                                    {statCard("Pass Long", formatStat(seasonStats?.passing_long, { integer: true }), "passing_long")}
                                    {statCard("Rush Long", formatStat(seasonStats?.rushing_long, { integer: true }), "rushing_long")}
                                    {statCard("Rec Long", formatStat(seasonStats?.receiving_long, { integer: true }), "receiving_long")}
                                </div>
                            </CollapsibleSection>

                            {/* DEFENSE */}
                            <CollapsibleSection title="Defense: Opponent Passing" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Attempts Allowed", formatStat(seasonStats?.opp_passing_attempts, { integer: true }), "opp_passing_attempts")}
                                    {statCard("Completions Allowed", formatStat(seasonStats?.opp_passing_completions, { integer: true }), "opp_passing_completions")}
                                    {statCard("Completion % Allowed", formatPct(seasonStats?.opp_passing_completion_pct), "opp_passing_completion_pct")}
                                    {statCard("Pass Yds Allowed", formatStat(seasonStats?.opp_passing_yards, { integer: true }), "opp_passing_yards")}
                                    {statCard("Pass Y/G Allowed", formatStat(seasonStats?.opp_passing_yards_per_game), "opp_passing_yards_per_game")}
                                    {statCard("Net Pass Y/G", formatStat(seasonStats?.opp_net_passing_yards_per_game), "opp_net_passing_yards_per_game")}
                                    {statCard("Y/A Allowed", formatStat(seasonStats?.opp_yards_per_pass_attempt), "opp_yards_per_pass_attempt")}
                                    {statCard("Net Y/A Allowed", formatStat(seasonStats?.opp_net_yards_per_pass_attempt), "opp_net_yards_per_pass_attempt")}
                                    {statCard("Pass TD Allowed", formatStat(seasonStats?.opp_passing_touchdowns, { integer: true }), "opp_passing_touchdowns")}
                                    {statCard("INTs", formatStat(seasonStats?.opp_passing_interceptions, { integer: true }), "opp_passing_interceptions")}
                                    {statCard("Sacks", formatStat(seasonStats?.opp_passing_sacks, { integer: true }), "opp_passing_sacks")}
                                    {statCard("QB Rating Allowed", formatStat(seasonStats?.opp_passing_qb_rating), "opp_passing_qb_rating")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Defense: Opponent Rushing" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Rush Att Allowed", formatStat(seasonStats?.opp_rushing_attempts, { integer: true }), "opp_rushing_attempts")}
                                    {statCard("Rush Yds Allowed", formatStat(seasonStats?.opp_rushing_yards, { integer: true }), "opp_rushing_yards")}
                                    {statCard("Rush Y/G Allowed", formatStat(seasonStats?.opp_rushing_yards_per_game), "opp_rushing_yards_per_game")}
                                    {statCard("Y/R Allowed", formatStat(seasonStats?.opp_rushing_yards_per_rush_attempt), "opp_rushing_yards_per_rush_attempt")}
                                    {statCard("Rush TD Allowed", formatStat(seasonStats?.opp_rushing_touchdowns, { integer: true }), "opp_rushing_touchdowns")}
                                    {statCard("Long Allowed", formatStat(seasonStats?.opp_rushing_long, { integer: true }), "opp_rushing_long")}
                                    {statCard("Rush Fumbles Forced", formatStat(seasonStats?.opp_rushing_fumbles, { integer: true }), "opp_rushing_fumbles")}
                                    {statCard("Rush Fumbles Recovered", formatStat(seasonStats?.opp_rushing_fumbles_lost, { integer: true }), "opp_rushing_fumbles_lost")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Defense: Opponent Receiving" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Receptions Allowed", formatStat(seasonStats?.opp_receiving_receptions, { integer: true }), "opp_receiving_receptions")}
                                    {statCard("Rec Yds Allowed", formatStat(seasonStats?.opp_receiving_yards, { integer: true }), "opp_receiving_yards")}
                                    {statCard("Rec Y/G Allowed", formatStat(seasonStats?.opp_receiving_yards_per_game), "opp_receiving_yards_per_game")}
                                    {statCard("Y/Rec Allowed", formatStat(seasonStats?.opp_receiving_yards_per_reception), "opp_receiving_yards_per_reception")}
                                    {statCard("Rec TD Allowed", formatStat(seasonStats?.opp_receiving_touchdowns, { integer: true }), "opp_receiving_touchdowns")}
                                    {statCard("Long Allowed", formatStat(seasonStats?.opp_receiving_long, { integer: true }), "opp_receiving_long")}
                                    {statCard("Rec Fumbles Forced", formatStat(seasonStats?.opp_receiving_fumbles, { integer: true }), "opp_receiving_fumbles")}
                                    {statCard("Rec Fumbles Recovered", formatStat(seasonStats?.opp_receiving_fumbles_lost, { integer: true }), "opp_receiving_fumbles_lost")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Defense: Opponent First Downs" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Total 1D", formatStat(seasonStats?.opp_misc_first_downs, { integer: true }), "opp_misc_first_downs")}
                                    {statCard("Pass 1D", formatStat(seasonStats?.opp_misc_first_downs_passing, { integer: true }), "opp_misc_first_downs_passing")}
                                    {statCard("Rush 1D", formatStat(seasonStats?.opp_misc_first_downs_rushing, { integer: true }), "opp_misc_first_downs_rushing")}
                                    {statCard("Pen 1D", formatStat(seasonStats?.opp_misc_first_downs_penalty, { integer: true }), "opp_misc_first_downs_penalty")}
                                    {statCard("Pass Long", formatStat(seasonStats?.opp_passing_long, { integer: true }), "opp_passing_long")}
                                    {statCard("Rush Long", formatStat(seasonStats?.opp_rushing_long, { integer: true }), "opp_rushing_long")}
                                    {statCard("Rec Long", formatStat(seasonStats?.opp_receiving_long, { integer: true }), "opp_receiving_long")}
                                    {statCard("Sack Yds", formatStat(seasonStats?.opp_passing_sack_yards_lost, { integer: true }), "opp_passing_sack_yards_lost")}
                                </div>
                            </CollapsibleSection>

                            {/* SPECIAL TEAMS */}
                            <CollapsibleSection title="Kicking" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("FG Made", formatStat(seasonStats?.kicking_field_goals_made, { integer: true }), "kicking_field_goals_made")}
                                    {statCard("FG Att", formatStat(seasonStats?.kicking_field_goals_attempted, { integer: true }), "kicking_field_goals_attempted")}
                                    {statCard("FG %", formatPct(fgPct), "fg_pct")}
                                    {statCard("Long FG", formatStat(seasonStats?.kicking_long_field_goal_made, { integer: true }), "kicking_long_field_goal_made")}
                                    {statCard("XP Made", formatStat(seasonStats?.kicking_extra_points_made, { integer: true }), "kicking_extra_points_made")}
                                    {statCard("XP Att", formatStat(seasonStats?.kicking_extra_point_attempts, { integer: true }), "kicking_extra_point_attempts")}
                                    {statCard("XP %", formatPct(seasonStats?.kicking_extra_point_pct), "kicking_extra_point_pct")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Punting" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("Punts", formatStat(seasonStats?.punting_punts, { integer: true }), "punting_punts")}
                                    {statCard("Punt Yds", formatStat(seasonStats?.punting_yards, { integer: true }), "punting_yards")}
                                    {statCard("Gross Avg", formatStat(seasonStats?.punting_average), "punting_average")}
                                    {statCard("Net Avg", formatStat(seasonStats?.punting_net_average), "punting_net_average")}
                                    {statCard("Long", formatStat(seasonStats?.punting_long_punt, { integer: true }), "punting_long_punt")}
                                    {statCard("Inside 20", formatStat(seasonStats?.punts_inside_20, { integer: true }), "punts_inside_20")}
                                    {statCard("Touchbacks", formatStat(seasonStats?.punting_touchbacks, { integer: true }), "punting_touchbacks")}
                                    {statCard("Fair Catches", formatStat(seasonStats?.punting_fair_catches, { integer: true }), "punting_fair_catches")}
                                </div>
                            </CollapsibleSection>

                            <CollapsibleSection title="Returns" teamColor={tc}>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {statCard("KR", formatStat(seasonStats?.kick_returns, { integer: true }), "kick_returns")}
                                    {statCard("KR Yds", formatStat(seasonStats?.kick_return_yards, { integer: true }), "kick_return_yards")}
                                    {statCard("KR Avg", formatStat(seasonStats?.kick_return_average), "kick_return_average")}
                                    {statCard("KR Long", formatStat(seasonStats?.returning_long_kick_return, { integer: true }), "returning_long_kick_return")}
                                    {statCard("PR", formatStat(seasonStats?.punt_returns, { integer: true }), "punt_returns")}
                                    {statCard("PR Yds", formatStat(seasonStats?.punt_return_yards, { integer: true }), "punt_return_yards")}
                                    {statCard("PR Avg", formatStat(seasonStats?.punt_return_average), "punt_return_average")}
                                    {statCard("PR Long", formatStat(seasonStats?.returning_long_punt_return, { integer: true }), "returning_long_punt_return")}
                                    {statCard("PR Fair Catch", formatStat(seasonStats?.returning_punt_return_fair_catches, { integer: true }), "returning_punt_return_fair_catches")}
                                </div>
                            </CollapsibleSection>
                        </div>
                    )}

                    {/* ═══ ROSTER TAB (Depth + Roster + Snaps merged) ═══ */}
                    {activeTab === 'roster' && (() => {
                        const injBadge = (status: string | null) => {
                            if (!status) return null;
                            const s = status.toLowerCase().trim();
                            if (s === 'out') return { label: 'OUT', cls: 'text-red-400 bg-red-500/20 border-red-500/40' };
                            if (s === 'doubtful') return { label: 'DOUBT', cls: 'text-orange-400 bg-orange-500/20 border-orange-500/40' };
                            if (s === 'questionable') return { label: 'Q', cls: 'text-amber-400 bg-amber-500/20 border-amber-500/40' };
                            if (s === 'probable') return { label: 'PROB', cls: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/40' };
                            if (s === 'injured reserve' || s === 'ir') return { label: 'IR', cls: 'text-slate-300 bg-slate-500/30 border-slate-500/50' };
                            return { label: status.slice(0, 4).toUpperCase(), cls: 'text-gray-400 bg-gray-500/20 border-gray-500/40' };
                        };

                        // Depth chart
                        const OFF_SLOTS = ["QB","RB","FB","WR","WR-2","WR-3","TE","LT","LG","C","RG","RT"];
                        const DEF_SLOTS = ["LDE","LDT","NT","RDT","RDE","SLB","LILB","MLB","RILB","WLB","LCB","SS","FS","RCB","NB"];
                        const ST_SLOTS = ["PK","P","H","KR","PR","LS"];

                        const posMap: Record<string, RosterPlayer[]> = {};
                        rosterData?.forEach(p => {
                            if (!posMap[p.position]) posMap[p.position] = [];
                            posMap[p.position].push(p);
                        });
                        Object.values(posMap).forEach(arr => arr.sort((a, b) => (a.depth || 99) - (b.depth || 99)));

                        const positions = new Set(Object.keys(posMap));
                        const defLabel = (positions.has("NT") && (positions.has("LILB") || positions.has("RILB")))
                            ? "Base 3-4 D"
                            : (positions.has("LDT") && positions.has("RDT") && positions.has("MLB"))
                                ? "Base 4-3 D"
                                : "Defense";

                        const depthChartUnit = (title: string, slots: string[]) => {
                            const activeSlots = slots.filter(s => posMap[s]?.length);
                            if (!activeSlots.length) return null;
                            return (
                                <div className="glass-card rounded-xl overflow-hidden">
                                    <div className="px-3 py-2 bg-white/[0.02] text-xs font-bold uppercase tracking-wider text-muted-foreground">{title}</div>
                                    <table className="w-full text-sm">
                                        <thead className="bg-white/5 text-[11px] text-muted-foreground uppercase tracking-wider">
                                            <tr>
                                                <th className="py-2 px-3 text-left w-16">Pos</th>
                                                <th className="py-2 px-3 text-left">1st</th>
                                                <th className="py-2 px-3 text-left hidden sm:table-cell">2nd</th>
                                                <th className="py-2 px-3 text-left hidden md:table-cell">3rd</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                            {activeSlots.map(slot => {
                                                const players = posMap[slot] || [];
                                                const playerCell = (p: RosterPlayer | undefined, isStarter: boolean, hidden?: string) => {
                                                    if (!p) return <td className={cn("py-2 px-3", hidden)}></td>;
                                                    const badge = injBadge(p.injury_status);
                                                    return (
                                                        <td className={cn("py-2 px-3", hidden)}>
                                                            <span
                                                                className={cn("cursor-pointer hover:text-primary transition-colors", isStarter ? "font-semibold text-foreground" : "text-muted-foreground")}
                                                                onClick={() => navigate(`/player/${p.player_id}`)}
                                                            >
                                                                {p.player_name}
                                                            </span>
                                                            {badge && <span className={cn("text-[9px] font-bold px-1 py-0.5 rounded border ml-1.5", badge.cls)}>{badge.label}</span>}
                                                        </td>
                                                    );
                                                };
                                                return (
                                                    <tr key={slot} className="hover:bg-white/[0.03]">
                                                        <td className="py-2 px-3 font-mono font-bold text-xs text-muted-foreground">{slot}</td>
                                                        {playerCell(players[0], true)}
                                                        {playerCell(players[1], false, "hidden sm:table-cell")}
                                                        {playerCell(players[2], false, "hidden md:table-cell")}
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            );
                        };

                        // Full roster sections
                        const ROSTER_SECTIONS = [
                            { header: "Offense", groups: ["Quarterbacks", "Running Backs", "Wide Receivers", "Tight Ends", "Offensive Line"] },
                            { header: "Defense", groups: ["Defensive Line", "Linebackers", "Defensive Backs"] },
                            { header: "Special Teams", groups: ["Special Teams"] },
                        ];
                        const allRosterPlayers = ROSTER_SECTIONS.flatMap(sec =>
                            sec.groups.flatMap(g => {
                                const ps = groupedRoster[g];
                                return ps ? [{ sectionHeader: sec.header, groupTitle: g, players: [...ps].sort((a, b) => (a.depth || 99) - (b.depth || 99)) }] : [];
                            })
                        );

                        // Snap labels
                        const SNAP_LABELS: Record<string, string> = { offense: "Offense", defense: "Defense", st: "Special Teams" };

                        return (
                            <div className="space-y-4">
                                {rosterLoading ? (
                                    <div className="space-y-4">
                                        {[...Array(3)].map((_, i) => <div key={i} className="h-16 glass-card rounded-xl animate-pulse" />)}
                                    </div>
                                ) : (
                                    <>
                                        <CollapsibleSection title="Depth Chart" defaultOpen teamColor={tc}>
                                            <div className="space-y-4">
                                                {depthChartUnit("3WR 1TE", OFF_SLOTS)}
                                                {depthChartUnit(defLabel, DEF_SLOTS)}
                                                {depthChartUnit("Special Teams", ST_SLOTS)}
                                            </div>
                                        </CollapsibleSection>

                                        <CollapsibleSection title="Full Roster" teamColor={tc}>
                                            <div className="space-y-6">
                                                {ROSTER_SECTIONS.map(sec => {
                                                    const sectionGroups = allRosterPlayers.filter(g => g.sectionHeader === sec.header);
                                                    if (!sectionGroups.length) return null;
                                                    const sectionPlayers = sectionGroups.flatMap(g => g.players);
                                                    return (
                                                        <div key={sec.header}>
                                                            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">{sec.header}</h4>
                                                            <div className="glass-card rounded-xl overflow-hidden">
                                                                <table className="w-full text-sm">
                                                                    <thead className="bg-white/5 text-[11px] text-muted-foreground uppercase tracking-wider">
                                                                        <tr>
                                                                            <th className="py-2 px-3 w-10"></th>
                                                                            <th className="py-2 px-2 w-10">#</th>
                                                                            <th className="py-2 px-2 text-left">Name</th>
                                                                            <th className="py-2 px-2 text-left">Pos</th>
                                                                            <th className="py-2 px-2 text-left hidden sm:table-cell">Age</th>
                                                                            <th className="py-2 px-2 text-left hidden md:table-cell">Ht</th>
                                                                            <th className="py-2 px-2 text-left hidden md:table-cell">Wt</th>
                                                                            <th className="py-2 px-2 text-left hidden lg:table-cell">College</th>
                                                                            <th className="py-2 px-2 text-center">Status</th>
                                                                        </tr>
                                                                    </thead>
                                                                    <tbody className="divide-y divide-white/5">
                                                                        {sectionPlayers.map(player => {
                                                                            const badge = injBadge(player.injury_status);
                                                                            return (
                                                                                <tr key={player.player_id} className="hover:bg-white/5 cursor-pointer transition-colors" onClick={() => navigate(`/player/${player.player_id}`)}>
                                                                                    <td className="py-1.5 px-3">
                                                                                        {player.photoUrl ? (
                                                                                            <img src={player.photoUrl} alt="" className="w-7 h-7 rounded-full object-cover" loading="lazy" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                                                                                        ) : null}
                                                                                    </td>
                                                                                    <td className="py-1.5 px-2 font-mono text-muted-foreground text-xs">{player.jersey_number && String(player.jersey_number) !== 'None' ? player.jersey_number : ''}</td>
                                                                                    <td className="py-1.5 px-2 font-medium">{player.player_name}</td>
                                                                                    <td className="py-1.5 px-2 text-muted-foreground">{player.position}</td>
                                                                                    <td className="py-1.5 px-2 text-muted-foreground hidden sm:table-cell">{player.age ?? '—'}</td>
                                                                                    <td className="py-1.5 px-2 text-muted-foreground hidden md:table-cell">{player.height || '—'}</td>
                                                                                    <td className="py-1.5 px-2 text-muted-foreground hidden md:table-cell">{player.weight || '—'}</td>
                                                                                    <td className="py-1.5 px-2 text-muted-foreground hidden lg:table-cell truncate max-w-[120px]">{player.college || '—'}</td>
                                                                                    <td className="py-1.5 px-2 text-center">
                                                                                        {badge && <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded border", badge.cls)}>{badge.label}</span>}
                                                                                    </td>
                                                                                </tr>
                                                                            );
                                                                        })}
                                                                    </tbody>
                                                                </table>
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </CollapsibleSection>

                                        <CollapsibleSection title={`Snap Counts${teamSnaps?.week ? ` (Week ${teamSnaps.week})` : ''}`} teamColor={tc}>
                                            {teamSnaps ? (
                                                <div className="space-y-6">
                                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                                        {(["offense", "defense", "st"] as const).map((key) => (
                                                            <div key={`latest-${key}`} className="glass-card rounded-xl p-4">
                                                                <h3 className="font-semibold mb-3 uppercase text-xs tracking-wider text-muted-foreground">{SNAP_LABELS[key]}</h3>
                                                                <div className="space-y-2">
                                                                    {teamSnaps[key].map((row: any, idx: number) => {
                                                                        const pct = (row[`${key}_pct`] || 0) * 100;
                                                                        const snaps = row[`${key}_snaps`] || 0;
                                                                        const pctClass = pct >= 10 ? "text-emerald-300" : "text-muted-foreground";
                                                                        return (
                                                                            <div key={`${row.player_name}-${idx}`} className="flex items-center justify-between text-sm">
                                                                                <div className="truncate">
                                                                                    {row.player_name} <span className="text-muted-foreground">{row.position}</span>
                                                                                </div>
                                                                                <div className={cn("font-mono", pctClass)}>
                                                                                    {formatStat(pct, { decimals: 1 })}% <span className="text-xs text-muted-foreground">({formatStat(snaps, { integer: true })})</span>
                                                                                </div>
                                                                            </div>
                                                                        );
                                                                    })}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                    {teamSnaps?.season && (
                                                        <>
                                                            <div className="text-sm text-muted-foreground">Season-long snap share</div>
                                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                                                {(["offense", "defense", "st"] as const).map((key) => (
                                                                    <div key={`season-${key}`} className="glass-card rounded-xl p-4">
                                                                        <h3 className="font-semibold mb-3 uppercase text-xs tracking-wider text-muted-foreground">{SNAP_LABELS[key]}</h3>
                                                                        <div className="space-y-2">
                                                                            {(teamSnaps.season?.[key] || []).map((row: any, idx: number) => {
                                                                                const pct = (row[`${key}_pct`] || 0) * 100;
                                                                                const snaps = row[`${key}_snaps`] || 0;
                                                                                const pctClass = pct >= 10 ? "text-emerald-300" : "text-muted-foreground";
                                                                                return (
                                                                                    <div key={`${row.player_name}-${idx}`} className="flex items-center justify-between text-sm">
                                                                                        <div className="truncate">
                                                                                            {row.player_name} <span className="text-muted-foreground">{row.position}</span>
                                                                                        </div>
                                                                                        <div className={cn("font-mono", pctClass)}>
                                                                                            {formatStat(pct, { decimals: 1 })}% <span className="text-xs text-muted-foreground">({formatStat(snaps, { integer: true })})</span>
                                                                                        </div>
                                                                                    </div>
                                                                                );
                                                                            })}
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </>
                                                    )}
                                                </div>
                                            ) : (
                                                <div className="text-sm text-muted-foreground">No snap data found.</div>
                                            )}
                                        </CollapsibleSection>
                                    </>
                                )}
                            </div>
                        );
                    })()}

                    {/* ═══ SCHEDULE TAB ═══ */}
                    {activeTab === 'schedule' && (() => {
                        const played = schedule?.filter(g => g.result) || [];
                        const upcoming = schedule?.filter(g => !g.result) || [];

                        const scheduleRow = (game: typeof played[0], i: number) => (
                            <tr key={i} className="hover:bg-white/5 transition-colors">
                                <td className="p-3 font-mono text-sm">{game.week}</td>
                                <td className="p-3 text-xs text-foreground/50">{fmtDate(game.gameday)}</td>
                                <td className="p-3 text-sm">
                                    <div className="flex items-center gap-2">
                                        <span className={cn(
                                            "text-[10px] font-semibold uppercase w-6 text-center",
                                            game.is_home ? "text-foreground/60" : "text-foreground/40"
                                        )}>
                                            {game.is_home ? "vs" : "at"}
                                        </span>
                                        <span className="font-bold">{game.opponent}</span>
                                    </div>
                                </td>
                                <td className="p-3 text-center">
                                    {game.result ? (
                                        <span className={cn(
                                            "px-2 py-0.5 rounded text-xs font-bold",
                                            game.result === "W" ? "bg-green-500/20 text-green-400" :
                                                game.result === "L" ? "bg-red-500/20 text-red-400" : "bg-gray-500/20 text-gray-400"
                                        )}>
                                            {game.result}
                                        </span>
                                    ) : <span className="text-xs text-muted-foreground">—</span>}
                                </td>
                                <td className="p-3 text-center font-mono text-sm">{game.score || "—"}</td>
                                <td className="p-3 text-center font-mono text-sm text-foreground/60">
                                    {game.spread !== null && game.spread !== undefined ? (
                                        <>{(game.spread > 0 ? "+" : "")}{game.spread}</>
                                    ) : "—"}
                                </td>
                                <td className="p-3 text-center">
                                    {game.ats_result ? (
                                        <span className={cn(
                                            "px-2 py-0.5 rounded text-xs font-bold",
                                            game.ats_result === "W" ? "text-emerald-400 border border-emerald-500/30" :
                                                game.ats_result === "L" ? "text-red-400 opacity-50" : "text-yellow-400"
                                        )}>
                                            {game.ats_result}
                                        </span>
                                    ) : null}
                                </td>
                            </tr>
                        );

                        const tableHead = (
                            <thead className="bg-white/5 text-left text-muted-foreground text-xs uppercase tracking-wider">
                                <tr>
                                    <th className="p-3">Wk</th>
                                    <th className="p-3">Date</th>
                                    <th className="p-3">Opponent</th>
                                    <th className="p-3 text-center">Result</th>
                                    <th className="p-3 text-center">Score</th>
                                    <th className="p-3 text-center">Spread</th>
                                    <th className="p-3 text-center">ATS</th>
                                </tr>
                            </thead>
                        );

                        return (
                            <div className="space-y-4">
                                {played.length > 0 && (
                                    <div className="glass-card rounded-xl overflow-hidden">
                                        <table className="w-full text-sm">
                                            {tableHead}
                                            <tbody className="divide-y divide-border">
                                                {played.map((g, i) => scheduleRow(g, i))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}

                                {upcoming.length > 0 && (
                                    <>
                                        <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold mt-2">
                                            Upcoming
                                        </div>
                                        <div className="glass-card rounded-xl overflow-hidden">
                                            <table className="w-full text-sm">
                                                {tableHead}
                                                <tbody className="divide-y divide-border">
                                                    {upcoming.map((g, i) => scheduleRow(g, i))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </>
                                )}
                            </div>
                        );
                    })()}
                </div>
            </div>
        </div>
    );
}
