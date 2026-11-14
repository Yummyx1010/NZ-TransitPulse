# PHASE-01: Static Network Explorer

- **Status:** Complete
- **Date:** 2026-11-14
- **Branch (suggested):** `phase/01-static-network-explorer`
- **Tag (suggested):** `phase-01`
- **Depends on:** PHASE-00 (Foundation)

## 1. Features delivered

| # | Feature | User-visible outcome |
| --- | --- | --- |
| F1 | MySQL schema + Alembic migration | Six versioned GTFS tables exist in the local MySQL database |
| F2 | GTFS static loader CLI | `load --download` / `load --file` imports the official AT bundle atomically and idempotently |
| F3 | Feed status | `network/status` reports the active feed, checksum and record counts; the UI shows a status pill |
| F4 | Route search | Search by number/name and filter by Bus / Rail / Ferry |
| F5 | Route detail | Stop count and an ordered list of stops served by the route |
| F6 | Stop search | Search by name/code/id, or by latitude + longitude + radius |
| F7 | Map explorer | Leaflet + OpenStreetMap map with stop markers, popups and a route polyline |
| F8 | Attribution | CC BY 4.0 credit to Auckland Transport in the API metadata and UI footer |
| F9 | CLI operations | `check-db`, `migrate`, `status`, `load` |
| F10 | CI | GitHub Actions now lints/tests the backend and typechecks/tests/builds the frontend |
| F11 | Actionable CLI diagnostics | A wrong Python interpreter or unreachable MySQL produces a short hint instead of a long traceback |

**Not in this phase:** realtime vehicle positions, ETAs, service alerts, historical
observation storage, reliability analytics, authentication, AWS deployment.

## 2. Problem and approach

Before passengers can ask "where is my bus", the application needs a trustworthy map
of the network: which routes exist, which stops they serve, and what the schedule says.
Phase 1 builds that static foundation from the official Auckland Transport GTFS bundle.

The main design risk is a **half-imported network**. A naive loader that deletes and
re-inserts rows can leave the API showing empty results while an import is running, and
a failed import can destroy the previous good data. The chosen approach stages every
bundle under a new `feed_id`, activates it inside a single transaction, and only then
prunes the previous version's rows.

Alternative rejected: storing GTFS files as-is and parsing them on every request. It
avoids a database but cannot support the joins needed for stop arrivals, route
analytics or the later realtime/history work. Loading into MySQL is the right long-term
base.

## 3. Implementation

| Area | Files |
| --- | --- |
| Manual SQL | `sql/001_create_database.sql` |
| DB layer | `backend/app/db/base.py`, `backend/app/db/session.py` |
| ORM models | `backend/app/models/gtfs.py` |
| Migration | `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/migrations/versions/0001_initial_gtfs_schema.py` |
| GTFS parser | `backend/app/gtfs/parser.py` |
| GTFS loader | `backend/app/gtfs/loader.py` |
| CLI | `backend/app/cli/gtfs.py` |
| API | `backend/app/api/network.py`, `backend/app/schemas/network.py`, `backend/app/core/constants.py`, `backend/app/core/modes.py` |
| App wiring | `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/api/ops.py` |
| Frontend | `frontend/` (Vite, React, TypeScript, TanStack Query, Leaflet) |
| Tests | `backend/tests/` (7 test modules + fixtures), `frontend/src/**/*.test.ts(x)` |
| CI | `.github/workflows/ci.yml` |
| Docs | `README.md`, `docs/DATABASE.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md`, this document, `docs/test-reports/PHASE-01.md` |

## 4. Interfaces

### REST API

| Method | Path | Query parameters |
| --- | --- | --- |
| `GET` | `/api/v1/network/status` | — |
| `GET` | `/api/v1/routes` | `q`, `mode`, `limit`, `offset` |
| `GET` | `/api/v1/routes/{route_id}` | — |
| `GET` | `/api/v1/routes/{route_id}/stops` | `limit`, `offset` |
| `GET` | `/api/v1/stops` | `q`, or `lat` + `lon` + `radius_m`, `limit`, `offset` |
| `GET` | `/api/v1/stops/{stop_id}` | — |

Example:

```json
{
  "route_id": "R1",
  "short_name": "18",
  "long_name": "New North Road",
  "route_type": 3,
  "mode": "Bus",
  "colour": "FF0000",
  "agency_id": "AT",
  "description": null,
  "url": null,
  "stop_count": 2
}
```

Error contract: `400` for invalid filters, `404` for unknown route/stop, `503` with
`{"detail": "Database unavailable"}` when MySQL cannot be reached.

### CLI

```text
python -m app.cli.gtfs check-db
python -m app.cli.gtfs migrate
python -m app.cli.gtfs load --download | --file PATH [--force]
python -m app.cli.gtfs status
```

### Configuration

New `.env` keys: `TP_DATABASE_ECHO`, `TP_GTFS_STATIC_URL`, `TP_GTFS_DATA_DIR`.
`TP_DATABASE_URL` now defaults to `127.0.0.1` for a local MySQL server.

## 5. Design decisions

1. **Composite `feed_id` keys** — supports atomic feed-version staging and an import
   audit trail.
2. **SHA-256 checksum identity** — re-importing an unchanged bundle is a no-op.
3. **Batch inserts of 5,000 rows** — keeps real AT bundles (hundreds of thousands of
   stop times) manageable without a bespoke bulk-load tool.
4. **Parser independent of the database** — the loader can be tested with a tiny
   in-memory synthetic GTFS zip; no network and no MySQL required for unit tests.
5. **BOM / nested-folder tolerance** — real agency bundles vary in layout and
   encoding.
6. **Times stored twice** — raw `HH:MM:SS` plus seconds since service-day midnight,
   preserving `25:10:00` style values that GTFS permits.
7. **Invalid coordinates skipped with a counter** — one bad stop must not abort a
   whole import; `skipped_stops` is reported by the CLI.
8. **No foreign keys on child tables** — bulk-load speed; integrity enforced by the
   loader transaction.
9. **Lazy engine creation** — `/health` and unit tests work even when MySQL is down;
   an app-level exception handler turns DB errors into `503`.
10. **SQLite for tests, MySQL for reality** — the automated suite never needs
    credentials; an opt-in `integration` marker verifies the real MySQL schema.
11. **`CircleMarker` instead of Leaflet icons** — avoids bundler issues with default
    marker image paths.
12. **Bounding-box geo search** — adequate at Auckland city scale; documented as an
    approximation rather than pretending to be geodesic.

## 6. How reviewers can verify in 60 seconds

1. `copy .env.example .env` and set `TP_DATABASE_URL` to your own MySQL account
   (see `docs/DATABASE.md` -> "Which account am I using?"). A conda environment works
   just as well as `.venv`.
2. Run `sql/001_create_database.sql` in DataGrip (the only manual SQL).
3. Activate `backend\.venv\Scripts\activate` (or `conda activate transitpulse`), then
   run `python -m app.cli.gtfs check-db`, `migrate`, `load --download`, `status`.
4. `uvicorn app.main:app --reload --port 8000`, then open `/docs` and try
   `GET /api/v1/network/status`.
5. `npm install && npm run dev`, open `http://localhost:5173`, search `18`, select the
   route, and see stops plotted on the map.

Alternatively, without any MySQL setup:

```bat
cd backend
pytest --cov=app --cov-report=term-missing
cd ..\frontend
npm test
npm run build
```

## 7. Tests

**Backend:** 52 passed, 1 skipped by default (opt-in MySQL integration, **which passed
when enabled**), 93% statement coverage, Ruff clean. Covers GTFS parsing (BOM, nested
folders, checksums, missing files/columns, after-midnight times, invalid coordinates),
loader idempotence/rollback/version activation, all six API endpoints, error contracts,
CLI commands (including the environment and MySQL failure diagnostics), and
migration/ORM drift plus reversibility.

**Frontend:** 9 passed across 3 suites, TypeScript strict typecheck clean, production
build succeeds. Covers the explorer rendering, route selection and stop loading, search
query propagation, API URL construction/encoding/error handling, and formatting helpers.

**End-to-end:** a real `uvicorn` process backed by a loaded SQLite database returned
`200` for `/api/v1/routes`, `/api/v1/network/status` and `/api/v1/routes/R1`.

**Live MySQL:** the real AT bundle (24.7 MB) was imported into local MySQL 8.0.42 —
17 agencies, 218 routes, 6,993 stops, 32,949 trips, 987,373 stop times, zero invalid
coordinates. All six API endpoints were exercised against that data with sub-100 ms
responses. Details in §4.2 of the test report.

Full environment, commands, outputs, resolved issues and unverified items are in
[`docs/test-reports/PHASE-01.md`](../test-reports/PHASE-01.md).

## 8. Known limitations and risks

- The opt-in MySQL integration test is skipped by default; run it with
  `set "TP_RUN_MYSQL_INTEGRATION=1"` and
  `python -m pytest tests/integration -m integration` (quotes matter on Windows cmd).
  It has been executed successfully against the local MySQL 8.0.42 instance.
- `GET /api/v1/routes/{id}` expects the GTFS `route_id`, which is **not** the public
  route number. On real AT data `/api/v1/routes/18` returns 404. The React UI is
  unaffected because it passes the `route_id` from the list response; a
  `short_name` lookup is planned for Phase 3.
- `CREATE USER IF NOT EXISTS` in `sql/001_create_database.sql` does not reset the
  password of an account that already exists. If you hit `1045`, either use your own
  MySQL account in `TP_DATABASE_URL` or `ALTER USER` the dedicated account.
- `calendar`, `calendar_dates` and `shapes` are parsed by the upstream feed but not yet
  loaded, so the map connects stops with straight lines rather than route geometry and
  "which services run today" is not yet available. This is intentional for Phase 1.
- `route_stops` returns distinct stops ordered alphabetically, not in travel order;
  travel order requires a chosen trip/direction and belongs in Phase 3.
- Geo search uses a latitude/longitude bounding box, which is approximate.
- No pagination UI yet; the API caps `limit` at 200 (500 for route stops).
- GitHub Actions has not executed yet; it runs on the first push of this phase.
- Starlette emits a non-blocking `StarletteDeprecationWarning` about
  `httpx`/`httpx2` in `TestClient`.

## 9. Next phase

Phase 2 adds the Auckland Transport GTFS-Realtime client (subscription key, retry,
rate limiting), decodes Vehicle Positions / Trip Updates / Service Alerts, runs a
30-second poller, and exposes realtime endpoints. The first real AT static import is
already complete (see §7); Phase 2 will confirm the developer portal quota.

## 10. Manual commit

Commands are provided in chat at phase completion. The assistant does not run any Git
write command.
