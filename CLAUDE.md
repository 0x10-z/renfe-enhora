# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Andén** is a real-time Spanish train delay dashboard for Renfe Cercanías and AVE/Larga Distancia. It has two clearly separated parts:

1. **Python pipeline** — runs every hour on a VPS via cron, fetches GTFS static + real-time data from Renfe, processes it, and writes JSON to `public/data/`
2. **Astro frontend** — static site built by Vercel on each push, reads the pre-generated JSON to render the analytics dashboard at enhora.info

## Commands

### Frontend (Astro)

```bash
npm run dev       # Dev server at localhost:3000
npm run build     # Build static site → dist/
npm run preview   # Preview built output
```

### Python Pipeline

```bash
# Activate venv first
source venv/bin/activate          # Linux/Mac
# or: . venv/Scripts/activate     # Windows

python -m scripts.main            # Run all services
python -m scripts.main cercanias  # Single service
python -m scripts.main media larga # Filter by keyword
```

### Deployment (VPS)

```bash
./deploy.sh   # git pull → python pipeline → git commit & push
# Cron: 0 * * * * /path/to/deploy.sh >> /path/to/logs/cron.log 2>&1
```

## Architecture

### Data Flow

```
Renfe GTFS APIs
    ↓
scripts/ingestion/     # Download & cache GTFS static (24h) + fetch GTFS-RT
    ↓
scripts/processing/    # Merge static+RT, compute stats, generate insights
    ↓
scripts/output/        # Write JSON → public/data/{service}/
    ↓
GitHub commit & push
    ↓
Vercel build → enhora.info
```

### Python Pipeline (`scripts/`)

| Module | Role |
|--------|------|
| `main.py` | Orchestrator — iterates services, calls all pipeline stages |
| `config.py` | Service definitions, API URLs, delay thresholds |
| `ingestion/gtfs_static.py` | Downloads GTFS ZIP, 24h file cache |
| `ingestion/gtfs_realtime.py` | Fetches RT updates (JSON primary, protobuf fallback) |
| `processing/merger.py` | Core logic: merges static+RT, classifies delays, 60-min lookahead window |
| `processing/stats.py` | Aggregates global metrics (totals, on-time %, busiest/worst stations) |
| `processing/insights.py` | Generates up to 9 natural-language insights (A–C current, D–I historical ≥8 records) |
| `output/writer.py` | Writes `stations/{id}.json`, `stats.json`, `history.json`, `insights.json` |

**Delay classification thresholds (config.py):**

- `≤300s` → `en_hora`
- `301–600s` → `retraso_leve`
- `>600s` → `retraso_alto`
- `-1` → `cancelado`

### Generated JSON (`public/data/{service}/`)

- `stats.json` — global metrics + station list
- `history.json` — append-only time-series (one record per cron run)
- `insights.json` — up to 9 insight objects with `id`, `text`, `severity`
- `stations/{stop_id}.json` — per-station arrivals for the next 60 minutes

### Frontend (`src/`)

- `pages/index.astro` — main dashboard: service tabs, stat cards, ECharts history chart, station browser
- `pages/sobre.astro` — about/methodology page
- `pages/cercanias/[id].astro` and `pages/ave-larga-distancia/[id].astro` — dynamic station detail pages
- `components/StationBoard.astro` — reusable arrival table with status badges
- `layouts/Layout.astro` — global HTML shell, CSS theme

### Services

Two services are tracked, each with independent data directories:

- **cercanias** — suburban trains; GTFS static cached from `ssl.renfe.com/ftransit/...`
- **ave-larga-distancia** — high-speed/long distance; GTFS static from `ssl.renfe.com/gtransit/...`

Both share the same GTFS-RT endpoint: `https://gtfsrt.renfe.com/trip_updates.json`

## Key Conventions

- The pipeline is stateless per run except for `history.json` (append-only) and the 24h GTFS static cache
- `scripts/main.py` filters services by CLI args using substring matching against service names/IDs
- The frontend consumes only pre-generated JSON — no server-side logic at request time
- SSL verification is intentionally disabled for Renfe endpoints (see `gtfs_static.py`)
