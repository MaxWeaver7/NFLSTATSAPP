# NFL Stats App — Source of Truth

> Last updated: February 2026
> Author: Max Weaver
> License: MIT

This is the authoritative reference for the NFL Stats App — a full-stack analytics platform for NFL player statistics, team analysis, betting lines, and advanced metrics.

---

## Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS |
| **UI Components** | Shadcn/ui (Radix primitives) + Framer Motion + Recharts |
| **State/Data** | TanStack React Query (server state) + React Context (theme) |
| **Backend** | Python HTTP server (ThreadingHTTPServer, no framework) |
| **Database** | Supabase (PostgreSQL via PostgREST) with SQLite fallback |
| **Data Sources** | BallDontLie API (GOAT tier), nfl_data_py, nflfastR, Pro Football Reference |

---

## Architecture

```
Browser (React SPA)
   │
   │  /api/* requests
   ▼
Python HTTP Server (port 8000 prod / 5001 dev)
   │
   ├── queries_supabase.py ──► Supabase (PostgreSQL)
   │                              ▲
   │                              │ Data ingested by:
   │                              │  - balldontlie_ingestor.py (BDL API)
   │                              │  - nfl_data_py_ingestor.py (nflfastR)
   │                              │  - ingest_betting_and_extras.py (odds/props)
   │                              │  - pfr_scraper.py (Pro Football Reference)
   │
   └── queries.py ──► SQLite fallback (data/nfl_data.db)
```

**Data flow**: External APIs → Python ingestion scripts → Supabase tables → Python server reads via PostgREST → JSON API → React frontend renders

---

## Directory Structure

```
NFLSTATSAPP/
├── SOURCE_OF_TRUTH.md              # This file — authoritative project guide
├── FullBALLDONTLIEAPI.md           # Complete BallDontLie API reference
├── README.md                       # Quick-start setup guide
├── LICENSE                         # MIT License
├── main.py                         # Data ingestion entry point
├── .gitignore                      # Git ignore rules
│
├── package.json                    # Node dependencies & npm scripts
├── package-lock.json               # Locked Node versions
├── requirements.txt                # Python dependencies
├── vite.config.ts                  # Vite bundler config (proxy: /api → :8000)
├── tsconfig.json                   # TypeScript compiler config
├── tsconfig.node.json              # TypeScript for build tools
├── tailwind.config.ts              # Tailwind CSS theme & extensions
├── postcss.config.js               # PostCSS (required by Tailwind)
├── vitest.config.ts                # Vitest test runner config
├── pytest.ini                      # Python test runner config
│
├── config/
│   └── env.example                 # Environment variable template (no secrets)
│
├── src/                            # Python backend
│   ├── web/
│   │   ├── server.py               # HTTP server — all API routes
│   │   ├── queries_supabase.py     # Supabase query layer (primary)
│   │   └── queries.py              # SQLite query layer (fallback)
│   ├── database/
│   │   ├── supabase_client.py      # Supabase client wrapper
│   │   ├── connection.py           # SQLite connection manager
│   │   └── schema.py               # SQLite table creation
│   ├── ingestion/
│   │   ├── balldontlie_client.py   # BDL API HTTP client
│   │   ├── balldontlie_ingestor.py # BDL data → Supabase pipeline
│   │   ├── nfl_data_py_ingestor.py # nflfastR play-by-play → Supabase
│   │   ├── nflfastr_ingestor.py    # nflfastR → SQLite (legacy path)
│   │   ├── ingest_betting_and_extras.py  # Odds & props ingestion
│   │   ├── pfr_scraper.py          # Pro Football Reference scraper
│   │   ├── pfr_urls.py             # PFR URL mappings
│   │   ├── features_wr_receiving.py # WR feature engineering
│   │   ├── coordinators.py         # Coach/coordinator data
│   │   ├── add_team_colors.py      # Team color metadata
│   │   ├── fantasy_api.py          # Fantasy API helpers
│   │   ├── create_nfl_data_py_tables.py  # Schema setup for nfl_data_py tables
│   │   ├── run_nfl_data_py.py      # nfl_data_py runner
│   │   ├── run_ingest_v2.py        # V2 ingestion pipeline
│   │   └── restore_nfl_data_py_schema.py # Schema recovery utility
│   ├── metrics/
│   │   ├── calculator.py           # Metric computation engine
│   │   └── definitions.py          # Metric definitions & formulas
│   ├── validation/
│   │   └── checks.py               # Data integrity validations
│   └── utils/
│       ├── env.py                  # Environment variable loading
│       └── logging.py              # Logging configuration
│
├── frontend/                       # React frontend
│   ├── index.html                  # HTML entry point
│   └── src/
│       ├── main.tsx                # React bootstrap
│       ├── App.tsx                 # Router & route definitions
│       ├── index.css               # Global styles, CSS variables, utilities
│       ├── pages/                  # Page components (one per route)
│       │   ├── Index.tsx           # Home — player browser + dossier
│       │   ├── Leaderboards.tsx    # Stat leaderboards (weekly/season)
│       │   ├── Teams.tsx           # Team standings by division
│       │   ├── TeamDetail.tsx      # Team deep-dive (4 tabs)
│       │   ├── PlayerDetail.tsx    # Player deep-dive (stats/gamelog/advanced)
│       │   ├── GameDetail.tsx      # Game analysis + props + comparison
│       │   ├── Matchup.tsx         # Weekly schedule/matchups
│       │   ├── PlayoffBracket.tsx  # Playoff bracket visualization
│       │   └── SmashFeed.tsx       # DFS smash spots feed
│       ├── components/             # Reusable UI components
│       │   ├── Header.tsx          # App header + navigation
│       │   ├── PlayerCard.tsx      # Player card (sidebar list)
│       │   ├── SeasonSummary.tsx   # Season stats summary block
│       │   ├── StatCard.tsx        # Individual stat display card
│       │   ├── AdvancedStatsTable.tsx  # Game log table
│       │   ├── GoatAdvancedStats.tsx   # GOAT-tier advanced stats display
│       │   ├── CollapsibleSection.tsx  # Reusable accordion (CSS grid animation)
│       │   ├── SmashCard.tsx       # Smash spot recommendation card
│       │   ├── TeamLogo.tsx        # Team logo display
│       │   ├── ui/                 # Shadcn primitives (table, button, select)
│       │   ├── charts/             # StatSparkline (Recharts)
│       │   ├── common/             # AnimatedSelect, CountUp
│       │   ├── comparison/         # ComparisonModal, PlayerSearch
│       │   └── skeletons/          # Loading state components
│       ├── hooks/
│       │   └── useApi.ts           # All API hooks (React Query)
│       ├── config/
│       │   ├── nfl-teams.ts        # Team name/abbreviation/logo mappings
│       │   └── advanced-stats-config.ts  # Stat column definitions per position
│       ├── context/
│       │   └── theme.tsx           # Dark mode theme provider
│       ├── types/
│       │   └── player.ts           # Player TypeScript types
│       └── lib/
│           └── utils.ts            # Helpers: cn(), formatStat(), ensureReadableColor()
│
├── supabase/                       # Database schema (SQL)
│   ├── schema_core.sql             # Core tables: teams, players, games, game_lines
│   ├── schema_stats.sql            # Stats: season_stats, game_stats, advanced stats
│   ├── nfl_data_py_schema.sql      # Player ID mapping, weekly/seasonal data tables
│   ├── add_perf_indexes.sql        # Performance indexes
│   ├── add_team_colors.sql         # Team color columns
│   ├── schema_team_colors.sql      # Team colors table
│   ├── seed_team_colors.sql        # Team color seed data
│   ├── add_ats_columns.sql         # Against-the-spread columns
│   ├── init_team_stats.sql         # Team stats initialization
│   ├── updates_for_props.sql       # Betting props schema
│   ├── fix_betting_odds_pk.sql     # Betting odds primary key fix
│   ├── reset_bdl_schema.sql        # Schema reset utility
│   ├── view_qb_smash_scores.sql    # QB smash score materialized view
│   ├── view_rb_smash_scores.sql    # RB smash score materialized view
│   ├── view_wr_smash_scores.sql    # WR smash score materialized view
│   ├── test_smash_views.sql        # Smash view test queries
│   ├── update_smash_views_fix_defense.sql  # Defense fix for smash views
│   ├── drop_uq_nfl_games_season_week_teams.sql  # Drop unique constraint migration
│   └── team_season_stats_migration_proposed.sql  # Proposed migration
│
├── scripts/                        # Utility & maintenance scripts
│   ├── README.md                   # Scripts documentation
│   ├── run_goat_update.py          # Update GOAT advanced stats
│   ├── ingest_odds.py              # Ingest betting odds
│   ├── ingest_odds_fast.py         # Fast odds ingestion
│   ├── ingest_props_odds_only.py   # Props-only ingestion
│   ├── build_wr_features.py        # Build WR feature set
│   ├── sync_injuries.py            # Sync injury reports
│   ├── audit_database.py           # Database audit/health check
│   ├── export_db.py                # Export database package (DB + schema + docs)
│   ├── manage_db_versions.py       # Database version control
│   ├── inspect_data.py             # Data inspection utility
│   ├── inspect_prop_structure.py   # Props data structure inspection
│   └── test_*.py                   # Various test/debug scripts
│
├── tests/                          # Python test suite
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_data_integrity.py      # Data integrity tests
│   ├── test_data_integrity_full.py # Full integrity suite
│   ├── test_player_photos.py       # Player photo URL tests
│   ├── test_features_wr_receiving.py  # WR feature tests
│   ├── test_balldontlie_supabase_units.py  # BDL API unit tests
│   └── test_supabase_stats_queries.py  # Query layer tests
│
├── data/                           # Runtime data (mostly gitignored)
│   ├── db_playerids.csv            # Player ID cross-reference (gsis↔espn↔yahoo↔sleeper↔pfr)
│   └── db_versions.json            # Database version tracking
│
└── docs/                           # Documentation
    ├── AI_HANDOFF.md               # Project context for AI collaboration
    ├── AI_HANDOFF_UPDATE.md        # Latest handoff updates
    ├── DATABASE_MANAGEMENT_GUIDE.md # DB operations guide
    ├── MASTER_API_INTEGRATION_GUIDE.md  # BDL + nfl_data_py integration deep-dive
    ├── PERFORMANCE.md              # Performance & scaling notes
    └── [historical fix docs]       # SMASH_FEED_*, DEFENSE_LOGIC_FIX, etc.
```

---

## Key Files (Read These First)

| File | Why It Matters |
|------|---------------|
| `src/web/server.py` | Every API route — the contract between frontend and backend |
| `src/web/queries_supabase.py` | All database queries — where data becomes API responses |
| `frontend/src/hooks/useApi.ts` | Frontend API client — all hooks, types, and fetch logic |
| `frontend/src/pages/TeamDetail.tsx` | Most complex page — 4-tab layout with CollapsibleSections |
| `frontend/src/pages/PlayerDetail.tsx` | Player deep-dive with position-specific stat rendering |
| `frontend/src/pages/Leaderboards.tsx` | Stat tables with sorting, filtering, mode switching |
| `frontend/src/config/advanced-stats-config.ts` | Stat column definitions for game logs per position |
| `frontend/src/lib/utils.ts` | Utilities: `cn()`, `formatStat()`, `ensureReadableColor()` |
| `frontend/src/index.css` | Global styles, CSS variables, collapsible animation, glass-card |
| `config/env.example` | All environment variables documented |

---

## Data Sources

### BallDontLie NFL API (GOAT Tier)
- **What**: Real-time NFL data — players, games, stats, standings, advanced metrics, betting odds, player props
- **Auth**: API key in `BALLDONTLIE_API_KEY` env var, sent as `Authorization` header
- **Docs**: See `FullBALLDONTLIEAPI.md` at repo root
- **Endpoints used**: Teams, Players, Games, Stats, Season Stats, Advanced Rushing/Passing/Receiving, Team Season Stats, Team Roster, Injuries, Betting Odds, Player Props
- **Ingestion**: `src/ingestion/balldontlie_ingestor.py` → Supabase tables
- **Rate limits**: Cursor-based pagination, max 100 per page

### nfl_data_py / nflfastR
- **What**: Historical play-by-play data with EPA, WPA, CPOE, target share, air yards
- **Library**: `nfl_data_py` Python package (wraps nflfastR R datasets)
- **Key functions**: `import_pbp_data()`, `import_weekly_data()`, `import_seasonal_data()`, `import_ids()`
- **Ingestion**: `src/ingestion/nfl_data_py_ingestor.py` → Supabase tables
- **Data**: 2002–current seasons, 370+ play-level columns

### Pro Football Reference (PFR)
- **What**: Supplemental stats scraped from pro-football-reference.com
- **Ingestion**: `src/ingestion/pfr_scraper.py` (best-effort, rate-limited)
- **Cache**: `data/pfr_cache/` (gitignored)
- **Config**: `PFR_ENABLE`, `PFR_REQUEST_DELAY_SECONDS`, `PFR_CACHE_DIR`

---

## Database Schema

All SQL files live in `supabase/`. Apply in this order for a fresh setup:

1. **`schema_core.sql`** — Core entities: `nfl_teams`, `nfl_players`, `nfl_games`, `nfl_game_lines`
2. **`schema_stats.sql`** — Stats: `nfl_player_season_stats`, `nfl_player_game_stats`, `nfl_advanced_rushing_season`, `nfl_advanced_passing_season`, `nfl_advanced_receiving_season`, and weekly variants
3. **`nfl_data_py_schema.sql`** — Player ID mapping (`nfl_player_id_mapping`), weekly data, seasonal data
4. **`add_perf_indexes.sql`** — Performance indexes for common queries
5. **`schema_team_colors.sql`** + **`seed_team_colors.sql`** — Team primary/secondary colors
6. **`updates_for_props.sql`** — Betting props tables
7. **`add_ats_columns.sql`** — Against-the-spread columns on game lines

### Important: Team Abbreviation Mismatches
nflverse (used by `nfl_game_lines`) and `nfl_teams` use different abbreviations:
- `LA` (nflverse) vs `LAR` (DB) for Rams
- `WAS` (nflverse) vs `WSH` (DB) for Commanders

Handled via `_NFLVERSE_TO_DB_TEAM` / `_DB_TO_NFLVERSE_TEAM` alias dicts in `queries_supabase.py`.

---

## API Endpoints

### Players
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/players` | List players with filters (season, position, team, search, pagination) |
| GET | `/api/player/{id}` | Full player detail: bio, game logs, season stats, advanced stats, snap history, team colors |
| GET | `/api/injuries` | Current injury reports keyed by player_id |

### Leaderboards (Weekly)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/receiving_dashboard` | Game-level receiving stats (targets, yards, EPA) |
| GET | `/api/rushing_dashboard` | Game-level rushing stats (attempts, yards, EPA) |
| GET | `/api/passing_dashboard` | Game-level passing stats |
| GET | `/api/total_yards_dashboard` | Combined yards |

### Leaderboards (Season)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/receiving_season` | Season receiving totals + shares |
| GET | `/api/rushing_season` | Season rushing totals + shares |
| GET | `/api/passing_season` | Season passing totals |
| GET | `/api/total_yards_season` | Season combined yards |

### Advanced Stats (Season, GOAT tier)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/advanced/receiving/season` | YAC above expected, separation, cushion |
| GET | `/api/advanced/rushing/season` | Yards over expected, efficiency, time to LOS |
| GET | `/api/advanced/passing/season` | Air distance, time to throw, CPOE, aggressiveness |

### Teams
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/teams` | All teams with standings |
| GET | `/api/teams/standings` | Standings with ATS records |
| GET | `/api/team/roster` | Team roster |
| GET | `/api/team/season-stats` | Full team season statistics |
| GET | `/api/team/snaps` | Snap counts (offense/defense/ST) |
| GET | `/api/team/leaders` | Top players per category |
| GET | `/api/teams/schedule` | Team schedule with results, spreads, ATS |

### Games & Schedule
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/schedule` | Weekly schedule or team schedule |
| GET | `/api/game/{id}` | Full game detail: comparison stats, leaders, props, history, environment |
| GET | `/api/matchup_history` | Head-to-head history between two teams |
| GET | `/api/playoffs` | Playoff bracket games |
| GET | `/api/latest-week` | Most recent week with data |

### Betting & DFS
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/feed/smash-spots` | DFS smash spot opportunities |

### Utility
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/summary` | Database summary stats |
| GET | `/api/options` | Available filter options (seasons, weeks, teams) |

All endpoints accept standard query params (`season`, `week`, `team`, `position`, `q`, `limit`, `offset`). Most require Supabase; SQLite fallback supports basic player/receiving/rushing leaderboards only.

---

## Frontend Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `Index` | Home page — player browser with filters, sidebar card list, dossier panel with game log + advanced stats |
| `/leaderboards` | `Leaderboards` | Stat tables — weekly/season modes, receiving/rushing/passing/total, standard/advanced toggle |
| `/teams` | `Teams` | 32 teams organized by AFC/NFC divisions, with records, ATS, point differential |
| `/team/:id` | `TeamDetail` | Team deep-dive — 4 tabs: Overview, Stats, Roster, Schedule. Extensive CollapsibleSections |
| `/player/:id` | `PlayerDetail` | Player deep-dive — position-specific stats, game log, snap counts, advanced metrics |
| `/matchup` | `Matchup` | Weekly schedule grid — game cards with scores, betting lines (hover to reveal) |
| `/game/:gameId` | `GameDetail` | Game analysis — team comparison bars, top players, H2H history, collapsible betting props |
| `/playoffs` | `PlayoffBracket` | Playoff bracket visualization |

---

## Setup & Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- Supabase account with project created
- BallDontLie API key (GOAT tier recommended)

### First-Time Setup

```bash
# 1. Clone and enter
git clone https://github.com/MaxWeaver7/NFLSTATSAPP.git
cd NFLSTATSAPP

# 2. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Node dependencies
npm install

# 4. Environment variables
cp config/env.example .env
# Edit .env with your Supabase URL, service role key, and BDL API key

# 5. Create Supabase tables (run in Supabase SQL Editor, in order)
#    - supabase/schema_core.sql
#    - supabase/schema_stats.sql
#    - supabase/nfl_data_py_schema.sql
#    - supabase/add_perf_indexes.sql
#    - supabase/schema_team_colors.sql + seed_team_colors.sql
#    - supabase/updates_for_props.sql

# 6. Ingest data
python3 main.py
```

### Development

```bash
# Terminal 1: Python API server
python3 -m src.web.server --db data/nfl_data.db --host 127.0.0.1 --port 8000

# Terminal 2: React dev server (hot reload, proxies /api to :8000)
npm run dev -- --host 127.0.0.1 --port 5173
```

### Production Build

```bash
npm run build          # Builds React app to dist/
# Python server serves dist/ automatically in production mode
python3 -m src.web.server --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Python tests
pytest

# Frontend tests
npx vitest run

# TypeScript type check
npx tsc --noEmit
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (server-side only) |
| `BALLDONTLIE_API_KEY` | Yes | BallDontLie API key |
| `BDL_INCLUDE_ADVANCED` | No | Set to `1` to include GOAT advanced endpoints during ingestion |
| `BDL_ADVANCED_ONLY` | No | Set to `1` to run only advanced endpoint ingestion |
| `NFL_DB_PATH` | No | SQLite database path (default: `data/nfl_data.db`) |
| `NFL_SEASONS` | No | Comma-separated seasons to ingest (default: `2024,2025`) |
| `PFR_ENABLE` | No | Enable Pro Football Reference scraping (`true`/`false`) |
| `PFR_REQUEST_DELAY_SECONDS` | No | Rate limit for PFR requests (default: `2.5`) |
| `PFR_CACHE_DIR` | No | PFR cache directory (default: `data/pfr_cache`) |

---

## Ingestion Pipeline

### Full Ingestion (`python3 main.py`)
1. Loads environment config
2. Connects to database (Supabase or SQLite)
3. Creates tables if needed
4. Ingests nflfastR play-by-play data → weekly/seasonal aggregates
5. Optionally scrapes Pro Football Reference
6. Computes derived metrics
7. Runs data validation checks

### Targeted Ingestion (scripts/)
| Script | Purpose |
|--------|---------|
| `scripts/run_goat_update.py` | Update GOAT advanced stats only |
| `scripts/ingest_odds.py` | Ingest betting odds from BDL |
| `scripts/ingest_odds_fast.py` | Fast odds ingestion (skips existing) |
| `scripts/ingest_props_odds_only.py` | Props/player props only |
| `scripts/sync_injuries.py` | Sync injury reports |
| `scripts/build_wr_features.py` | Build WR feature engineering data |

### Database Management
| Script | Purpose |
|--------|---------|
| `scripts/export_db.py` | Export complete DB package (DB + schema + docs + samples) |
| `scripts/manage_db_versions.py` | Version control for database (list/create/activate/compare) |
| `scripts/audit_database.py` | Database health check and audit |

---

## UI Design System

- **Theme**: Dark glassmorphic (`bg-background` = deep dark navy, glass-card = frosted glass with border)
- **Font**: Inter with `font-variant-numeric: tabular-nums` for clean numeric rendering (open zeros)
- **Colors**: Team primary/secondary colors used for gradients, accents, tab indicators
- **Dark color handling**: `ensureReadableColor()` lightens dark team colors (e.g., Raiders black) for text visibility
- **Animations**: Framer Motion for dropdowns, CSS `@keyframes` for slide-up/fade-in, CSS grid for collapsible sections
- **CollapsibleSection**: Reusable accordion component using `grid-template-rows: 0fr → 1fr` trick for smooth height animation
- **Betting lines**: Hidden by default, revealed on hover via `group-hover:max-h-8 group-hover:opacity-100`

---

## Common Tasks

### Add a new stat to game logs
1. Add column definition in `frontend/src/config/advanced-stats-config.ts` (find the position's config array)
2. Ensure the backend returns the field in game log data (`queries_supabase.py` → `get_player_game_logs()`)

### Add a new page
1. Create `frontend/src/pages/NewPage.tsx`
2. Add route in `frontend/src/App.tsx`
3. Add nav link in `frontend/src/components/Header.tsx`

### Add a new API endpoint
1. Add handler in `src/web/server.py` (follow existing pattern: parse params, call query function, return JSON)
2. Add query function in `src/web/queries_supabase.py`
3. Add React Query hook in `frontend/src/hooks/useApi.ts`

### Run data ingestion
```bash
python3 main.py                              # Full ingestion
python3 scripts/run_goat_update.py           # GOAT advanced stats only
python3 scripts/ingest_odds.py               # Betting odds
python3 scripts/sync_injuries.py             # Injury reports
```

### Deploy
```bash
npm run build                                 # Build React → dist/
python3 -m src.web.server --host 0.0.0.0 --port 8000  # Serves both API and built frontend
```
