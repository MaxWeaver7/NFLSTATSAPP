// ... imports ...
import { useState } from "react";
import { usePlayoffs } from "@/hooks/useApi";
import { Header } from "@/components/Header";
import { Trophy } from "lucide-react";
import { TeamLogo } from "@/components/TeamLogo";
import { WeeklyGame } from "@/hooks/useApi";

const BracketGame = ({ game, align: _align = "left" }: { game: WeeklyGame, align?: "left" | "right" | "center" }) => {
    if (!game) return <div className="h-24 w-[200px] border border-dashed border-white/5 rounded-lg opacity-20" />;

    const isWinner = (score: number | null | undefined, oppScore: number | null | undefined) => {
        if (score == null || oppScore == null) return false;
        return score > oppScore;
    };

    return (
        <div className={`glass-card mb-4 w-[220px] overflow-hidden rounded-lg border border-white/10 relative group hover:border-white/30 transition-colors`}>
            {/* Gradient Background */}
            <div className="absolute inset-0 opacity-10" style={{ background: `linear-gradient(to right, ${game.away_color || '#333'}, ${game.home_color || '#333'})` }} />

            <div className="relative p-3">
                <div className="flex justify-between items-center mb-2 border-b border-white/5 pb-1">
                    <div className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">{game.gameday.split(' ')[0]}</div>
                    <div className="text-[10px] bg-white/10 px-1.5 rounded text-white/80">FINAL</div>
                </div>

                {/* Teams */}
                <div className="space-y-2">
                    {/* Away */}
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <TeamLogo team={game.away_team} size="sm" />
                            <span className={isWinner(game.away_score, game.home_score) ? "font-bold text-white shadow-glow-sm" : "text-muted-foreground"}>
                                {game.away_team}
                            </span>
                        </div>
                        <span className="font-mono text-sm">{game.away_score ?? "-"}</span>
                    </div>

                    {/* Home */}
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <TeamLogo team={game.home_team} size="sm" />
                            <span className={isWinner(game.home_score, game.away_score) ? "font-bold text-white shadow-glow-sm" : "text-muted-foreground"}>
                                {game.home_team}
                            </span>
                        </div>
                        <span className="font-mono text-sm">{game.home_score ?? "-"}</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default function PlayoffBracket() {
    const [season, setSeason] = useState(2025);
    const { data: games, isLoading } = usePlayoffs(season);

    // Filter Helper
    const getGames = (conf: string, round: string) => {
        if (!games) return [];
        if (conf === "SB") return games.filter(g => g.game_type === "SB");
        return games.filter(g => g.game_type === round && (g.conference === conf || g.conference === "Unknown"));
        // Note: backend ensures 'conference' is set to Home Team's conference.
        // For WC/DIV/CON, this effectively separates them.
    };

    // AFC
    const afcWC = getGames("AFC", "WC");
    const afcDiv = getGames("AFC", "DIV");
    const afcCon = getGames("AFC", "CON");

    // NFC
    const nfcWC = getGames("NFC", "WC");
    const nfcDiv = getGames("NFC", "DIV");
    const nfcCon = getGames("NFC", "CON");

    // SB
    const sbGame = getGames("SB", "SB");

    return (
        <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
            <Header />

            <main className="container mx-auto px-4 py-8">
                <div className="flex justify-between items-center mb-8 animate-fade-in">
                    <div>
                        <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-yellow-200 to-yellow-500 mb-2">
                            Playoff Bracket
                        </h1>
                        <p className="text-muted-foreground flex items-center gap-2">
                            <Trophy className="w-4 h-4 text-yellow-500" />
                            Road to the Super Bowl
                        </p>
                    </div>

                    <div className="flex gap-2">
                        {[2024, 2025].map(y => (
                            <button
                                key={y}
                                onClick={() => setSeason(y)}
                                className={`px-4 py-2 rounded-lg font-bold transition-all ${season === y ? "bg-primary text-black shadow-lg shadow-primary/25" : "bg-black/20 text-muted-foreground hover:bg-white/10"}`}
                            >
                                {y}
                            </button>
                        ))}
                    </div>
                </div>

                {isLoading ? (
                    <div className="text-center py-20 text-muted-foreground animate-pulse">Loading Bracket data...</div>
                ) : (
                    <div className="overflow-x-auto pb-8">
                        {/* Layout: AFC Left, NFC Right, SB Center */}
                        <div className="flex justify-center items-center gap-8 min-w-[1400px]">

                            {/* AFC Side */}
                            <div className="flex gap-8">
                                <RoundColumn title="Wild Card" games={afcWC} />
                                <RoundColumn title="Divisional" games={afcDiv} />
                                <RoundColumn title="Conf. Champ" games={afcCon} />
                            </div>

                            {/* Super Bowl */}
                            <div className="flex flex-col items-center justify-center h-full px-8 border-l border-r border-white/5">
                                <div className="mb-4 text-center">
                                    <Trophy className="w-12 h-12 text-yellow-400 mx-auto mb-2 drop-shadow-[0_0_10px_rgba(250,204,21,0.5)]" />
                                    <h3 className="text-xl font-bold text-yellow-100 uppercase tracking-widest">Super Bowl</h3>
                                </div>
                                {sbGame.length > 0 ? (
                                    <div className="scale-125">
                                        <BracketGame game={sbGame[0]} align="center" />
                                    </div>
                                ) : (
                                    <div className="h-32 w-64 glass-card border-dashed border-white/20 flex items-center justify-center text-muted-foreground">
                                        TBD
                                    </div>
                                )}
                            </div>

                            {/* NFC Side (Reversed Order for Symmetry if needed, but standard left-to-right flow for round progression implies
                               WC -> DIV -> CON -> SB <- CON <- DIV <- WC? 
                               Yes, user said "come from both sides".
                            */}
                            <div className="flex gap-8 flex-row-reverse">
                                <RoundColumn title="Wild Card" games={nfcWC} />
                                <RoundColumn title="Divisional" games={nfcDiv} />
                                <RoundColumn title="Conf. Champ" games={nfcCon} />
                            </div>

                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}

const RoundColumn = ({ title, games }: { title: string, games: WeeklyGame[] }) => (
    <div className="flex flex-col justify-around min-w-[220px]">
        <h3 className="text-center text-xs font-bold uppercase tracking-widest text-muted-foreground mb-6 opacity-50">
            {title}
        </h3>
        <div className="flex flex-col gap-6 justify-center h-full">
            {games.length > 0 ? (
                games.map(game => <BracketGame key={game.nflverse_game_id} game={game} />)
            ) : (
                <div className="text-center text-xs text-muted-foreground py-8 border border-dashed border-white/10 rounded-lg">
                    TBD
                </div>
            )}
        </div>
    </div>
);
