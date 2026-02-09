## NFLAdvancedStats — Supabase + BALLDONTLIE NFL (with React UI)

This repo contains:
- A **React UI** (Vite dev server) at `http://127.0.0.1:5173/`
- A **Python API server** at `http://127.0.0.1:8000/` (also serves the built React UI from `dist/` when present)
- A **Supabase (Postgres) schema + ingestion pipeline** that loads NFL data from the **BALLDONTLIE NFL API**
- A legacy local **SQLite + nflfastR** ingestion path (optional fallback)

### Setup

Create a virtualenv, install deps, and set environment variables:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp config/env.example .env  # optional (if your env supports dotfiles)
```

### Supabase + BALLDONTLIE (recommended)

1) **Create tables in Supabase**

Open Supabase Dashboard → SQL Editor, and run:
- `supabase/schema_core.sql`
- `supabase/schema_stats.sql`

Optional (recommended for speed if Players/Leaderboards feel slow):
- `supabase/add_perf_indexes.sql`

If you ran an older schema that created a strict unique index on games, run once:
- `supabase/drop_uq_nfl_games_season_week_teams.sql`

### AI handoff / project context
- `docs/AI_HANDOFF.md`
- Performance + scalability notes:
  - `docs/PERFORMANCE.md`
- BALLDONTLIE AI/OpenAPI context:
  - `notes/ai-context.txt`

2) **Set env vars** in `.env`:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side only)
- `BALLDONTLIE_API_KEY`

3) **Ingest**:

```bash
python3 main.py
```

Optional:
- `BDL_INCLUDE_ADVANCED=1` to attempt GOAT advanced endpoints (may be unstable at times).
- `BDL_ADVANCED_ONLY=1` to run advanced-only (skips core + season/game stats).

### Run the web app

#### Dev (recommended)

Terminal A (backend):

```bash
python3 -m src.web.server --db ../data/nfl_data.db --host 127.0.0.1 --port 8000
```

Terminal B (React UI):

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open: `http://127.0.0.1:5173/`

#### Build (serve React from Python)

If you have built the frontend to `dist/`, run:

```bash
npm install
npm run build
python3 -m src.web.server --db ../data/nfl_data.db --host 127.0.0.1 --port 8000
```

Open: `http://127.0.0.1:8000/`

### Legacy (SQLite + nflfastR)
If Supabase vars are not set, `main.py` falls back to ingesting nflfastR → SQLite.

```bash
python3 main.py
```

### Tests

```bash
pytest
```

### Notes

- The PFR scraper is **best-effort** and will **never fabricate data**. If `games.pfr_boxscore_url` is empty, scraping is skipped.


