# NZ TransitPulse

A production-oriented public transport monitoring and analytics platform for
**Auckland, New Zealand**.

NZ TransitPulse answers two sets of questions:

- **For passengers:** Where is my bus now? When will it arrive? Is this route delayed?
- **For people who care about transit data:** Which routes are least reliable? At what
  time of day are delays worst? Is reliability improving?

> **Product scope: buses only.** The Auckland Transport feed also contains trains and
> ferries; they remain in the imported static GTFS data, but the UI, live vehicle layer
> and future analytics exclusively cover buses. The API keeps a generic `mode` filter,
> while the dashboard always requests `mode=Bus`.

The project is developed in small, documented phases. See
[`docs/ROADMAP.md`](docs/ROADMAP.md) for the phase plan and
[`docs/WORKFLOW.md`](docs/WORKFLOW.md) for the contribution and commit convention.

> **Current status: Phase 3 - Passenger view.** Routes, stops, trips, scheduled stop
> times and `shapes.txt` geometry are imported from the official Auckland Transport GTFS
> bundle into MySQL and explored on a React/Leaflet map. The aggregated AT GTFS-Realtime
> feed is polled every 30 seconds and held in memory; live bus positions are drawn as
> heading-aware bus icons alongside real route geometry. A stop-arrival board combines
> the static timetable with live delays to show ETAs and delay status, is scoped to the
> selected bus route by default, and filters trips by the imported service calendar for
> today. Bus-only service alerts are shown alongside it. Historical observations and
> reliability analytics arrive in later phases.

## Phase index

Every phase ships one implementation document (features, design, decisions, how to
demo) and one test report (real commands, real results). This table is the fastest way
for a reviewer to see what is implemented and how it was verified.

| Phase | Feature | Implementation | Tests | Tag |
| --- | --- | --- | --- | --- |
| 0 | Foundation: config, MySQL setup, API skeleton, CI | [docs/phases/PHASE-00-foundation.md](docs/phases/PHASE-00-foundation.md) | [docs/test-reports/PHASE-00.md](docs/test-reports/PHASE-00.md) | `phase-00` |
| 1 | Static network explorer: GTFS import, network API, map UI | [docs/phases/PHASE-01-static-network-explorer.md](docs/phases/PHASE-01-static-network-explorer.md) | [docs/test-reports/PHASE-01.md](docs/test-reports/PHASE-01.md) | `phase-01` |
| 1B | Route geometry fix: shapes.txt, per-shape drawing, ordered stops | [docs/phases/PHASE-01B-route-geometry.md](docs/phases/PHASE-01B-route-geometry.md) | [docs/test-reports/PHASE-01B.md](docs/test-reports/PHASE-01B.md) | — |
| 2 | Realtime ingestion: aggregated GTFS-RT, bus-only live map, direction-scoped vehicles, quota-aware poller | [docs/phases/PHASE-02-realtime-ingestion.md](docs/phases/PHASE-02-realtime-ingestion.md) | [docs/test-reports/PHASE-02.md](docs/test-reports/PHASE-02.md) | — |
| 3 | Passenger view: stop ETA board, delay status, bus service alerts, direction/branch UX | [docs/phases/PHASE-03-passenger-view.md](docs/phases/PHASE-03-passenger-view.md) | [docs/test-reports/PHASE-03.md](docs/test-reports/PHASE-03.md) | — |
| 4-7 | Historical observations, analytics dashboard (MVP), hardening, AWS | Planned | Planned | — |

## Technology

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic Settings, SQLAlchemy 2, Alembic, PyMySQL |
| Database | MySQL 8 (local install, Docker Compose optional, Amazon RDS later) |
| Frontend | React 18, TypeScript, Vite, TanStack Query, Leaflet / OpenStreetMap |
| Quality | pytest, pytest-cov, Ruff, Vitest, Testing Library, GitHub Actions |
| Deployment | Local first; AWS (ECS Fargate, RDS, S3/CloudFront) post-MVP |

## Prerequisites

Python 3.12+, Node.js 20+, Git, and a **local MySQL 8 server**. Docker is entirely
optional: the application runs directly with `uvicorn` and `npm run dev`, and
`docker-compose.yml` is only a convenience for developers who do not already have
MySQL.

## Quickstart

### 1. Configure the environment

```bat
copy .env.example .env
```

Edit `.env` so `TP_DATABASE_URL` matches your local MySQL user, and set
`TP_AT_API_KEY` to your Auckland Transport developer portal subscription key. Keep
`TP_AT_REALTIME_URL` at its default aggregated endpoint. Without a key the static
network explorer still works; the live bar explains that realtime is not configured.

### 2. One-time SQL in DataGrip (the only manual SQL)

Open [`sql/001_create_database.sql`](sql/001_create_database.sql) in DataGrip, select
your local MySQL connection as the target, and execute the script. It creates the
`transitpulse` database and a dedicated user. **All tables are created by Alembic** in
the next step — no other hand-written SQL is needed. If you already have a MySQL user
you prefer, skip the `CREATE USER`/`GRANT` statements and just use that user in
`TP_DATABASE_URL`.

See [`docs/DATABASE.md`](docs/DATABASE.md) for the schema and troubleshooting.

### 3. Apply migrations and import the GTFS feed

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m app.cli.gtfs check-db
python -m app.cli.gtfs migrate
python -m app.cli.gtfs load --download
python -m app.cli.gtfs status
```

`load --download` fetches `https://gtfs.at.govt.nz/gtfs.zip`. To use a file you
downloaded yourself, run `python -m app.cli.gtfs load --file C:\path\to\gtfs.zip`.
Re-importing an unchanged bundle is a no-op; a changed bundle is staged and activated
atomically.

**Prefer a conda environment?** That works too — the CLI only checks that the
dependencies are importable, not which environment manager created them. In an
**Anaconda Prompt**:

```bat
conda create -n transitpulse python=3.12
conda activate transitpulse
cd backend
python -m pip install -e ".[dev]"
python -m app.cli.gtfs check-db
```

The prompt then shows `(transitpulse)`. Do not mix environments: install with the same
interpreter you use to run the CLI. The existing `.venv` folder is gitignored and can
be left in place or deleted.

> **Common pitfall:** `ModuleNotFoundError: No module named 'pydantic_settings'` means
> the **system/Anaconda base Python** was used instead of an environment with the
> requirements installed. The prompt must show `(.venv)` or `(transitpulse)` after
> activation, or call `.venv\Scripts\python.exe -m app.cli.gtfs check-db` directly.
> See [`docs/DATABASE.md`](docs/DATABASE.md) for the full troubleshooting table.

### 4. Run the API and the dashboard

In one terminal:

```bat
cd backend
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bat
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000`.

### 5. Demo in 60 seconds

1. Open `http://localhost:8000/docs` and try `GET /api/v1/network/status`.
2. Open the dashboard (`http://localhost:5173`, or the port Vite prints; use
   `npm run dev -- --port 5174` if 5173 is occupied).
3. Search bus routes (try `70`), select one, and see its real drawn geometry, ordered
   stops and the buses serving that route. The map auto-fits the selected route; `Fit to
   view` re-centres it. Use `Direction / branch` to switch `D0`/`D1`; short-turn
   patterns are grouped separately, and the buses shown are re-filtered to the selected
   pattern.
4. Orange bus icons show heading and can be hidden with `Show live buses`; the live bar
   reports the feed timestamp and weekly API quota usage.
5. In the **Passenger view** panel, the selected route scopes the board by default.
   Search a stop (e.g. `Britomart`) and pick it to see that route's upcoming buses with
   scheduled/predicted times, minutes away and `Early / On time / Delayed` badges; rows
   without a live prediction say `timetable only`. Use `Show all buses at this stop` to
   opt out. The right column lists bus-only service alerts.
6. Check the footer for the Auckland Transport CC BY 4.0 attribution.

## API (Phase 1 + 1B + 2 + 3)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe |
| `GET` | `/api/v1/meta` | Service metadata and data attribution |
| `GET` | `/api/v1/network/status` | Active GTFS feed and record counts |
| `GET` | `/api/v1/routes` | List/search routes (`q`, `mode`, `limit`, `offset`) |
| `GET` | `/api/v1/routes/{route_id}` | Route detail and stop count |
| `GET` | `/api/v1/routes/{route_id}/stops` | Stops served by a route |
| `GET` | `/api/v1/routes/{route_id}/geometry` | Per-shape route geometry with ordered stops; `stop_times` fallback is marked `approximate` |
| `GET` | `/api/v1/stops` | List/search stops (`q`, `route_id`, or `lat`+`lon`+`radius_m`) |
| `GET` | `/api/v1/stops/{stop_id}` | Stop detail and routes serving it |
| `GET` | `/api/v1/stops/{stop_id}/arrivals` | Upcoming bus arrivals with scheduled/predicted times and delay status (`minutes`, `limit`, `route_id`) |
| `GET` | `/api/v1/realtime/status` | Poller health, entity counts, weekly quota usage |
| `GET` | `/api/v1/realtime/vehicles` | Live vehicle positions (`mode=Bus`, `route_id`, `shape_id`, `bbox`, `limit`) |
| `GET` | `/api/v1/realtime/trip-updates` | Live trip delays and stop-time predictions |
| `GET` | `/api/v1/realtime/alerts` | Service alerts (`mode=Bus`, `route_id`, `limit`) |

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phases, deliverables, MVP boundary |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Components, data flow, design decisions |
| [`docs/DATABASE.md`](docs/DATABASE.md) | Schema, migrations, DataGrip setup |
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | AT feeds, licences, compliance decisions |
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | Language, commit policy, phase definition of done |
| [`docs/phases/`](docs/phases/) | One feature/implementation document per phase |
| [`docs/test-reports/`](docs/test-reports/) | One test report per phase |

## Docker and AWS

Docker is **optional** for local development; the app is not containerised in Phase 0-5.
`docker compose up -d mysql` merely starts an alternative MySQL 8 instance for anyone
who needs one. Amazon RDS (Phase 7) changes only `TP_DATABASE_URL`. Even an ECS Fargate
deployment does not require Docker on your machine: a `Dockerfile` can be added in
Phase 7 and the image built by CI (GitHub Actions -> ECR), or the backend can be
deployed from source with App Runner / Elastic Beanstalk.

## Data attribution

Public transport data is sourced from **Auckland Transport** and is licensed under
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
Map tiles are © OpenStreetMap contributors. See
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for the compliance decisions governing
historical observation collection.

This is an independent project. It is not affiliated with or endorsed by Auckland
Transport.

## Licence

Code: MIT (see [`LICENSE`](LICENSE)). Data: CC BY 4.0, attributed to Auckland Transport.
