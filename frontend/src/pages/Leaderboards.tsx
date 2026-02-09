import { useEffect, useMemo, useRef, useState } from "react";
// lucide icons removed - not used
import { getTeamColors } from "@/config/nfl-teams";
import { Header } from "@/components/Header";
import { AnimatedSelect } from "@/components/common/AnimatedSelect";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useFilterOptions } from "@/hooks/useApi";
import { TeamLogo } from "@/components/TeamLogo";
import { useNavigate } from "react-router-dom";
import { formatStat } from "@/lib/utils";
import {
  ADVANCED_RECEIVING_COLUMNS,
  ADVANCED_RUSHING_COLUMNS,
  ADVANCED_PASSING_COLUMNS,
} from "@/config/advanced-stats-config";

type Mode = "weekly" | "season";
type Category = "receiving" | "rushing" | "passing" | "total_yards";
type StatsMode = "standard" | "advanced";

type Row = Record<string, any>;

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export default function Leaderboards() {
  const { data: options } = useFilterOptions();
  const navigate = useNavigate();

  const loadTimerStarted = useRef(false);
  const loadTimerEnded = useRef(false);
  const hasStartedInitialLoad = useRef(false);

  const DEFAULT_SEASON = 2025;
  const [mode, setMode] = useState<Mode>("weekly");
  const [statsMode, setStatsMode] = useState<StatsMode>("standard");
  const [category, setCategory] = useState<Category>("receiving");
  const [season, setSeason] = useState<number>(options?.seasons?.[0] || DEFAULT_SEASON);
  const [week, setWeek] = useState<number>(options?.weeks?.[0] || 1);
  const [team, setTeam] = useState<string>("");
  const [position, setPosition] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [sortKey, setSortKey] = useState<string>("rank");
  const [asc, setAsc] = useState<boolean>(false);

  // When options load (async), prefer the latest season unless user already chose something valid.
  useEffect(() => {
    const seasons = options?.seasons || [];
    if (seasons.length === 0) return;
    if (!seasons.includes(season)) setSeason(seasons[0]);
  }, [options?.seasons, season]);

  // Reset animation flag on unmount (so it plays again on re-navigation)
  useEffect(() => {
    if (!loadTimerStarted.current) {
      console.time("LeaderboardLoad");
      loadTimerStarted.current = true;
    }
    return;
  }, []);

  const endpoint = useMemo(() => {
    const base = new URLSearchParams();
    base.set("season", String(season));
    // Fetch broadly and filter client-side to avoid backend filter inconsistencies.
    // We do client-side search on `rows`, so requesting too few rows makes many valid players
    // impossible to find. Backend caps responses to 200 rows, so we request up to that cap.
    base.set("limit", mode === "season" ? "800" : "200");
    if (mode === "weekly") base.set("week", String(week));

    // If the user is searching, pass it to the backend so we can find players that aren't in the
    // current top-N slice. Keep this conservative to avoid hammering the API on single-char input.
    // Advanced stats mode (season only)
    if (statsMode === "advanced" && mode === "season") {
      if (category === "receiving") {
        return `/api/advanced/receiving/season?${base.toString()}`;
      }
      if (category === "rushing") {
        return `/api/advanced/rushing/season?${base.toString()}`;
      }
      if (category === "passing") {
        return `/api/advanced/passing/season?${base.toString()}`;
      }
      // total_yards not available in advanced mode - fall back to standard
    }

    // Standard stats mode
    if (category === "receiving") {
      return mode === "weekly"
        ? `/api/receiving_dashboard?${base.toString()}`
        : `/api/receiving_season?${base.toString()}`;
    }
    if (category === "rushing") {
      return mode === "weekly"
        ? `/api/rushing_dashboard?${base.toString()}`
        : `/api/rushing_season?${base.toString()}`;
    }
    if (category === "passing") {
      return mode === "weekly"
        ? `/api/passing_dashboard?${base.toString()}`
        : `/api/passing_season?${base.toString()}`;
    }
    // total_yards
    return mode === "weekly"
      ? `/api/total_yards_dashboard?${base.toString()}`
      : `/api/total_yards_season?${base.toString()}`;
  }, [mode, statsMode, category, season, week, team, position, search]);

  const [rows, setRows] = useState<Row[]>([]);
  // Start in "loading" to avoid flashing empty/no-results before the first request begins.
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // lightweight fetch-on-change (keeps this page isolated from react-query setup)
  useEffect(() => {
    let cancelled = false;
    hasStartedInitialLoad.current = true;
    // Clear stale data immediately to prevent "stuck" display
    setRows([]);
    setLoading(true);
    setErr(null);

    // Debug logging to verify API calls
    console.log(`[Leaderboards] Fetching: ${endpoint}`);

    fetchJson<{ rows: Row[] }>(endpoint)
      .then((data) => {
        if (cancelled) return;
        console.log(`[Leaderboards] Received ${data.rows?.length || 0} rows`);
        setRows(data.rows || []);
        setLoading(false);
        if (loadTimerStarted.current && !loadTimerEnded.current) {
          console.timeEnd("LeaderboardLoad");
          loadTimerEnded.current = true;
        }
      })
      .catch((e) => {
        if (cancelled) return;
        console.error(`[Leaderboards] Error fetching data:`, e);
        setErr(String(e?.message || e));
        setRows([]);
        setLoading(false);
        if (loadTimerStarted.current && !loadTimerEnded.current) {
          console.timeEnd("LeaderboardLoad");
          loadTimerEnded.current = true;
        }
      });
    return () => {
      cancelled = true;
    };
  }, [endpoint]);

  const displayRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    let out = rows;
    if (q) {
      out = out.filter((r) => {
        const name = String(r.player_name || "").toLowerCase();
        const teamMatch = String(r.team || "").toLowerCase();
        return name.includes(q) || teamMatch.includes(q);
      });
    }
    if (team) {
      const t = team.toUpperCase();
      out = out.filter((r) => String(r.team || "").toUpperCase() === t);
    }
    if (position && position !== "ALL") {
      const p = position.toUpperCase();
      out = out.filter((r) => String(r.position || "").toUpperCase() === p);
    }
    const getVal = (r: Row, k: string): any => {
      if (k === "rank") return 0;
      return r[k];
    };

    // DEBUG: Log first few raw values before sorting
    console.log(`[Sort PRE] sortKey=${sortKey}, first5 raw values:`, out.slice(0, 5).map(r => r[sortKey]));

    const sorted = [...out].sort((a, b) => {
      const av = getVal(a, sortKey);
      const bv = getVal(b, sortKey);
      const an = typeof av === "number" ? av : Number(av);
      const bn = typeof bv === "number" ? bv : Number(bv);
      const bothNum = Number.isFinite(an) && Number.isFinite(bn);
      if (bothNum) return asc ? an - bn : bn - an;
      const as = (av ?? "").toString();
      const bs = (bv ?? "").toString();
      return asc ? as.localeCompare(bs) : bs.localeCompare(as);
    });
    // DEBUG: Log sort results
    console.log(`[Sort POST] sortKey=${sortKey}, asc=${asc}, first5 sorted values:`, sorted.slice(0, 5).map(r => r[sortKey]));
    return sorted;
  }, [rows, search, sortKey, asc, team, position]);

  useEffect(() => {
    // CRITICAL: Clear rows immediately when category changes
    // This prevents stale sorted data from persisting across tab switches
    setRows([]);

    if (statsMode === "advanced") {
      if (category === "receiving") setSortKey("yards");
      else if (category === "rushing") setSortKey("rush_yards");
      else if (category === "passing") setSortKey("pass_yards");
    } else {
      if (category === "receiving") setSortKey("rec_yards");
      else if (category === "rushing") setSortKey("rush_yards");
      else if (category === "passing") setSortKey("passing_yards");
      else if (category === "total_yards") setSortKey("total_yards");
    }

    setAsc(false);
    setPosition("ALL"); // Reset position filter to prevent stuck empty states
  }, [category, statsMode]);

  const skeletonColumns = useMemo(() => {
    if (category === "receiving") return 6; // Player, Team, TGT, REC, YDS, TD
    if (category === "passing") return 7; // Player, Team, CMP, ATT, YDS, TD, INT
    if (category === "total_yards") return 6; // Player, Team, RUSH, REC, TOTAL, TD
    // rushing
    return mode === "weekly" ? 8 : 11;
  }, [category, mode]);

  function TableSkeleton({ columns, rows: rowCount = 10 }: { columns: number; rows?: number }) {
    return (
      <>
        {Array.from({ length: rowCount }).map((_, rIdx) => (
          <TableRow key={`sk-${rIdx}`} className="border-border">
            {Array.from({ length: columns }).map((__, cIdx) => (
              <TableCell key={`sk-${rIdx}-${cIdx}`}>
                <div className="h-4 w-full rounded bg-muted/40 animate-pulse" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </>
    );
  }

  const SortHead = ({ k, label, className }: { k: string; label: string; className?: string }) => {
    const active = sortKey === k;
    const arrow = active ? (asc ? "▲" : "▼") : "";
    return (
      <TableHead className={className}>
        <button
          type="button"
          className={`w-full inline-flex items-center gap-2 text-muted-foreground font-medium hover:text-foreground transition-colors ${className?.includes('text-center') ? 'justify-center' : ''}`}
          onClick={() => {
            if (sortKey === k) setAsc((v) => !v);
            else {
              setSortKey(k);
              setAsc(false);
            }
          }}
        >
          <span>{label}</span>
          <span className="text-xs font-mono opacity-70">{arrow}</span>
        </button>
      </TableHead>
    );
  };

  const title =
    mode === "weekly"
      ? `Weekly Leaders • Week ${week} • ${season}`
      : `Season Leaders • ${season}`;

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="container mx-auto px-4 py-6 space-y-4">
        <div className="px-1">
          <div className="flex flex-wrap items-center gap-2">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search…"
                className="h-[28px] w-32 px-2 rounded-md border border-white/[0.06] bg-white/[0.03] text-xs text-foreground/80 placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-white/20"
              />

              <div className="flex items-center gap-0.5 p-0.5 bg-white/[0.03] rounded-md border border-white/[0.06]">
                {(["Weekly", "Season"] as const).map((m) => {
                  const modeValue: Mode = m.toLowerCase() as Mode;
                  const isActive = mode === modeValue;
                  return (
                    <button
                      key={m}
                      type="button"
                      onClick={() => {
                        const newMode = modeValue;
                        setMode(newMode);
                        if (newMode === "weekly") setStatsMode("standard");
                      }}
                      className={`
                        px-2 py-0.5 text-[11px] font-medium rounded transition-all
                        ${isActive
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                        }
                      `}
                      aria-label={`Set mode to ${m}`}
                    >
                      {m}
                    </button>
                  );
                })}
              </div>

              {mode === "season" && category !== "total_yards" && (
                <div className="flex items-center gap-0.5 p-0.5 bg-white/[0.03] rounded-md border border-white/[0.06]">
                  {(["Std", "Adv"] as const).map((sm, i) => {
                    const smValue: StatsMode = (i === 0 ? "standard" : "advanced") as StatsMode;
                    const isActive = statsMode === smValue;
                    return (
                      <button
                        key={sm}
                        type="button"
                        onClick={() => setStatsMode(smValue)}
                        className={`
                          px-2 py-0.5 text-[11px] font-medium rounded transition-all
                          ${isActive
                            ? "bg-primary text-primary-foreground shadow-sm"
                            : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                          }
                        `}
                      >
                        {sm}
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="flex items-center gap-0.5 p-0.5 bg-white/[0.03] rounded-md border border-white/[0.06]">
                {(["Rec", "Rush", "Pass", "Total"] as const).map((cat, i) => {
                  const catValues: Category[] = ["receiving", "rushing", "passing", "total_yards"];
                  const catValue = catValues[i];
                  const isActive = category === catValue;
                  return (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setCategory(catValue)}
                      className={`
                        px-2 py-0.5 text-[11px] font-medium rounded transition-all
                        ${isActive
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                        }
                      `}
                    >
                      {cat}
                    </button>
                  );
                })}
              </div>

              <AnimatedSelect
                label="Season"
                options={(options?.seasons || []).map(s => String(s))}
                value={String(season)}
                onChange={(v) => setSeason(Number(v))}
              />

              {mode === "weekly" ? (
                <AnimatedSelect
                  label="Week"
                  options={(options?.weeks || []).map(w => `Week ${w}`)}
                  value={`Week ${week}`}
                  onChange={(v) => setWeek(Number(v.replace("Week ", "")))}
                />
              ) : null}

              <AnimatedSelect
                label="Team"
                options={["All Teams", ...(options?.teams || [])]}
                value={team || "All Teams"}
                onChange={(v) => setTeam(v === "All Teams" ? "" : v)}
              />

              <AnimatedSelect
                label="Position"
                options={["All Positions", "QB", "RB", "WR", "TE"]}
                value={position === "ALL" ? "All Positions" : position}
                onChange={(v) => setPosition(v === "All Positions" ? "ALL" : v)}
              />

              <span className="ml-auto text-[11px] text-muted-foreground font-medium tracking-wide hidden md:inline">{title}</span>
          </div>
        </div>

        <div className="glass-card rounded-xl overflow-hidden">
          {err && (
            <div className="p-3 border-b border-border text-sm text-destructive">
              Error: {err}
            </div>
          )}

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-muted-foreground font-medium">Player</TableHead>
                  <SortHead k="team" label="Team" className="text-muted-foreground font-medium" />
                  {statsMode === "advanced" ? (
                    <>
                      {category === "receiving" && ADVANCED_RECEIVING_COLUMNS.map(col => (
                        <SortHead key={col.k} k={col.k} label={col.label} className="text-center" />
                      ))}
                      {category === "rushing" && ADVANCED_RUSHING_COLUMNS.map(col => (
                        <SortHead key={col.k} k={col.k} label={col.label} className="text-center" />
                      ))}
                      {category === "passing" && ADVANCED_PASSING_COLUMNS.map(col => (
                        <SortHead key={col.k} k={col.k} label={col.label} className="text-center" />
                      ))}
                    </>
                  ) : (
                    <>
                      {category === "receiving" ? (
                        <>
                          <SortHead k="targets" label="TGT" className="text-center" />
                          <SortHead k="receptions" label="REC" className="text-center" />
                          <SortHead k="rec_yards" label="YDS" className="text-center" />
                          <SortHead k="rec_tds" label="TD" className="text-center" />
                        </>
                      ) : category === "rushing" ? (
                        <>
                          <SortHead k="rush_attempts" label="ATT" className="text-center" />
                          <SortHead k="rush_yards" label="YDS" className="text-center" />
                          <SortHead k="ypc" label="YPC" className="text-center" />
                          {mode === "weekly" ? null : <SortHead k="ypg" label="YPG" className="text-center" />}
                          <SortHead k="receptions" label="REC" className="text-center" />
                          {mode === "weekly" ? null : <SortHead k="rpg" label="RPG" className="text-center" />}
                          <SortHead k="rec_yards" label="REC YDS" className="text-center" />
                          {mode === "weekly" ? null : <SortHead k="rec_ypg" label="REC YPG" className="text-center" />}
                          <SortHead k="rush_tds" label="TD" className="text-center" />
                        </>
                      ) : category === "passing" ? (
                        <>
                          <SortHead k="passing_completions" label="CMP" className="text-center" />
                          <SortHead k="passing_attempts" label="ATT" className="text-center" />
                          <SortHead k="passing_yards" label="YDS" className="text-center" />
                          <SortHead k="passing_tds" label="TD" className="text-center" />
                          <SortHead k="interceptions" label="INT" className="text-center" />
                        </>
                      ) : (
                        <>
                          <SortHead k="rush_yards" label="RUSH" className="text-center" />
                          <SortHead k="rec_yards" label="REC" className="text-center" />
                          <SortHead k="total_yards" label="TOTAL" className="text-center" />
                          <SortHead k="total_tds" label="TD" className="text-center" />
                        </>
                      )}
                    </>
                  )}
                </TableRow>
              </TableHeader>
              {loading ? (
                <TableBody>
                  <TableSkeleton columns={skeletonColumns} />
                </TableBody>
              ) : (
                <TableBody>
                  {displayRows.length === 0 ? (
                    <TableRow className="border-border">
                      <TableCell
                        colSpan={skeletonColumns}
                        className="py-10 text-center text-sm text-muted-foreground"
                      >
                        No results found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    displayRows.map((r, idx) => {
                      const pid = String(r.player_id || "").trim();
                      // Include index and sortKey in key to force React to re-order DOM nodes when sorted
                      const stableKey = `${idx}-${sortKey}-${asc}-${r.player_id || r.id || `${r.player_name}-${r.team}`}`;
                      const { primary } = getTeamColors(r.team);

                      return (
                        <TableRow
                          key={stableKey}
                          className="data-row border-border cursor-pointer relative transition-all duration-200 ease-out hover:scale-[1.01] hover:shadow-sm hover:z-10 group"
                          style={{
                            background: `linear-gradient(90deg, ${primary}15, transparent)`,
                            borderLeft: `3px solid ${primary}`
                          }}
                          onClick={() => {
                            if (!pid) return;
                            navigate(`/player/${pid}`);
                          }}
                        >
                          <TableCell className="font-medium py-1.5">
                            <div className="flex items-center gap-2">
                              <div
                                className="w-7 h-7 rounded-full overflow-hidden ring-1 ring-border shrink-0"
                                style={{ backgroundColor: primary }}
                              >
                                {r.photoUrl ? (
                                  <img
                                    src={r.photoUrl}
                                    className="w-full h-full object-cover"
                                    loading="lazy"
                                    onError={(e) => {
                                      // Hide broken image, fallback will show
                                      (e.currentTarget as HTMLImageElement).style.display = "none";
                                    }}
                                  />
                                ) : null}
                                <div
                                  className={`w-full h-full flex items-center justify-center text-muted-foreground text-xs font-bold ${r.photoUrl ? "hidden" : ""
                                    }`}
                                >
                                  {(r.player_name || r.player_id || "?")
                                    .toString()
                                    .split(" ")
                                    .filter(Boolean)
                                    .slice(0, 2)
                                    .map((n: string) => n[0])
                                    .join("")
                                    .toUpperCase()}
                                </div>
                              </div>
                              <div className="min-w-0">
                                <div className="truncate">{r.player_name || r.player_id}</div>
                                <div className="text-xs text-muted-foreground">{r.position || "UNK"}</div>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="text-sm py-1.5">
                            <div className="flex items-center gap-1.5">
                              <TeamLogo team={r.team} size="sm" />
                              <span>{r.team || "FA"}</span>
                            </div>
                          </TableCell>

                          {statsMode === "advanced" ? (
                            <>
                              {category === "receiving" && ADVANCED_RECEIVING_COLUMNS.map(col => (
                                <TableCell key={col.k} className="text-center">
                                  {formatStat(r[col.k] ?? 0, { integer: col.type === "int" })}
                                </TableCell>
                              ))}
                              {category === "rushing" && ADVANCED_RUSHING_COLUMNS.map(col => (
                                <TableCell key={col.k} className="text-center">
                                  {formatStat(r[col.k] ?? 0, { integer: col.type === "int" })}
                                </TableCell>
                              ))}
                              {category === "passing" && ADVANCED_PASSING_COLUMNS.map(col => (
                                <TableCell key={col.k} className="text-center">
                                  {formatStat(r[col.k] ?? 0, { integer: col.type === "int" })}
                                </TableCell>
                              ))}
                            </>
                          ) : (
                            <>
                              {category === "receiving" ? (
                                <>
                                  <TableCell className="text-center">{r.targets ?? 0}</TableCell>
                                  <TableCell className="text-center">{r.receptions ?? 0}</TableCell>
                                  <TableCell className="text-center font-semibold">{r.rec_yards ?? 0}</TableCell>
                                  <TableCell className="text-center">{r.rec_tds ?? 0}</TableCell>
                                </>
                              ) : category === "rushing" ? (
                                <>
                                  <TableCell className="text-center">{r.rush_attempts ?? 0}</TableCell>
                                  <TableCell className="text-center font-semibold">{r.rush_yards ?? 0}</TableCell>
                                  <TableCell className="text-center">{formatStat(r.ypc ?? 0)}</TableCell>
                                  {mode === "weekly" ? null : (
                                    <TableCell className="text-center">{formatStat(r.ypg ?? 0)}</TableCell>
                                  )}
                                  <TableCell className="text-center">{r.receptions ?? 0}</TableCell>
                                  {mode === "weekly" ? null : (
                                    <TableCell className="text-center">{formatStat(r.rpg ?? 0)}</TableCell>
                                  )}
                                  <TableCell className="text-center">{r.rec_yards ?? 0}</TableCell>
                                  {mode === "weekly" ? null : (
                                    <TableCell className="text-center">{formatStat(r.rec_ypg ?? 0)}</TableCell>
                                  )}
                                  <TableCell className="text-center">{r.rush_tds ?? 0}</TableCell>
                                </>
                              ) : category === "passing" ? (
                                <>
                                  <TableCell className="text-center">{r.passing_completions ?? 0}</TableCell>
                                  <TableCell className="text-center">{r.passing_attempts ?? 0}</TableCell>
                                  <TableCell className="text-center font-semibold">{r.passing_yards ?? 0}</TableCell>
                                  <TableCell className="text-center">{r.passing_tds ?? 0}</TableCell>
                                  <TableCell className="text-center">{r.interceptions ?? 0}</TableCell>
                                </>
                              ) : (
                                <>
                                  <TableCell className="text-center">{r.rush_yards ?? 0}</TableCell>
                                  <TableCell className="text-center">{r.rec_yards ?? 0}</TableCell>
                                  <TableCell className="text-center font-semibold">{r.total_yards ?? 0}</TableCell>
                                  <TableCell className="text-center">{r.total_tds ?? 0}</TableCell>
                                </>
                              )}
                            </>
                          )}
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              )}
            </Table>
          </div>
        </div>
      </main>
    </div>
  );
}


