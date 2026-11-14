# Test Report: Phase 01 - Static Network Explorer

- **Date:** 2026-11-14
- **Result:** **PASS** — backend 52 passed / 1 skipped / 93% coverage, plus the opt-in MySQL integration test passed separately; frontend 9 passed; typecheck and production build clean; the real Auckland Transport GTFS bundle was imported into local MySQL and all API endpoints were verified against it
- **Phase document:** `docs/phases/PHASE-01-static-network-explorer.md`
- **Final re-verification (2026-11-14, before commit):** Ruff clean; backend
  `52 passed, 1 skipped, 93%` + MySQL integration `1 passed`; frontend `9 passed`;
  `npm run build` exit 0. Timings quoted in the sections below are from earlier real
  runs of the same suite.

## 1. Environment

| Item | Value |
| --- | --- |
| OS | Windows (win32), `cmd` shell |
| Python | 3.12.7, virtual environment `backend/.venv` |
| Node.js / npm | v24.14.0 / 11.9.0 |
| MySQL | Local MySQL **8.0.42** on `127.0.0.1:3306`, connected via the machine's own `root` account; `transitpulse` database and 7 tables created |
| Docker | Not installed and not required |
| Git | 2.55.0.windows.3, branch `main` tracking `origin/main` (Phase 0 committed) |

Key versions: `fastapi 0.162.7`, `SQLAlchemy 2.1.8`, `alembic 1.20.1`, `PyMySQL 1.2.4`,
`pydantic-settings 2.16.3`, `pytest 8.4.2`, `pytest-cov 6.3.0`, `ruff 0.17.5`,
`vite 6.4.6`, `vitest 3.2.7`, `react 18.3.x`, `react-leaflet 4.2.x`,
`@tanstack/react-query 5.x`, `typescript 5.x`.

## 2. Backend

### 2.1 Lint

```text
cd backend
.venv\Scripts\python.exe -m ruff check .
```

```text
All checks passed!
```

### 2.2 Unit, API, loader, CLI and migration tests

```text
.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

```text
s....................................................                    [100%]

Name                      Stmts   Miss  Cover
---------------------------------------------
app\__init__.py               1      0   100%
app\api\__init__.py           0      0   100%
app\api\network.py           94      3    97%
app\api\ops.py               28      0   100%
app\cli\__init__.py           0      0   100%
app\cli\gtfs.py              98     13    87%
app\core\__init__.py          0      0   100%
app\core\config.py           37      0   100%
app\core\constants.py         1      0   100%
app\core\modes.py             9      0   100%
app\db\__init__.py            0      0   100%
app\db\base.py                3      0   100%
app\db\session.py            17      4    76%
app\gtfs\__init__.py          0      0   100%
app\gtfs\loader.py          102     17    83%
app\gtfs\parser.py           81      4    95%
app\main.py                  21      0   100%
app\models\__init__.py        2      0   100%
app\models\gtfs.py           80      0   100%
app\schemas\__init__.py       0      0   100%
app\schemas\network.py       53      0   100%
---------------------------------------------
TOTAL                       627     41    93%
52 passed, 1 skipped, 1 warning in 3.77s
```

The single warning is the known non-blocking
`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`
originating from the installed FastAPI/Starlette `TestClient`.

The single skip is the opt-in MySQL integration test
(`tests/integration/test_mysql_connection.py`), which requires
`TP_RUN_MYSQL_INTEGRATION=1` plus a configured local MySQL.

### 2.3 Coverage by behaviour

| Area | Tests | Representative cases |
| --- | --- | --- |
| GTFS parser | 12 | nested folder lookup, UTF-8 BOM, checksum, missing file, missing column, `25:10:00` -> `90600`, invalid coordinates |
| GTFS loader | 5 | all-table counts, skipped invalid stop, unchanged re-import, new version activation and pruning, rollback on invalid bundle |
| Network API | 12 | empty status, loaded status, search, mode filter, pagination, route detail/stops, stop detail, geo radius, `400`/`404`/`503` |
| Migrations | 2 | migration creates every ORM table/column; migration is reversible |
| CLI | 8 | Alembic config, result serialisation, `migrate`, `load` + `status`, empty status, missing-dependency detection, virtual-environment hint, friendly database error |
| Phase 0 regression | 12 | health, meta, CORS, OpenAPI, config validation |

## 3. Frontend

### 3.1 Typecheck and build

```text
cd frontend
npx tsc --noEmit
npm run build
```

```text
vite v6.4.6 building for production...
✓ 121 modules transformed.
dist/index.html                   0.56 kB │ gzip:   0.34 kB
dist/assets/index-BkYvqP4u.css   19.20 kB │ gzip:   7.61 kB
dist/assets/index-B0aFcFNh.js   344.62 kB │ gzip: 105.87 kB
✓ built in 873ms
BUILD_EXIT=0
```

### 3.2 Unit tests

```text
npx vitest run
```

```text
suites: 6  tests: 9  passed: 9  failed: 0  success: True
  - App.test.tsx      passed
  - client.test.ts    passed
  - format.test.ts    passed
```

Cases: header/attribution rendering, route selection loads stops, search query reaches
the API, query-string construction, route-id encoding, HTTP error handling, and
formatting helpers.

## 4. End-to-end HTTP smoke test

A temporary script loaded the synthetic GTFS bundle into a disposable SQLite database
and started a real `uvicorn` process, then issued HTTP requests:

```text
LOAD: loaded {'agencies': 1, 'routes': 3, 'stops': 3, 'trips': 3, 'stop_times': 4}

GET /api/v1/routes           200 3 ['18', 'DEV', 'WEST']
GET /api/v1/network/status   200 {'agencies': 1, 'routes': 3, 'stops': 3,
                                  'trips': 3, 'stop_times': 4}
GET /api/v1/routes/R1        200 2
SMOKE TEST: PASS
```

The temporary script and all temporary logs were deleted after the run.

### 4.1 CLI diagnostics (verified with both interpreters)

```text
> python -m app.cli.gtfs check-db            (D:\anaconda\python.exe)
Missing Python dependencies: pydantic_settings
Dependencies are missing from the current Python interpreter.
Activate the environment you created (a venv or a conda env both work):
  .venv\Scripts\activate           (Windows venv)
  conda activate transitpulse       (Anaconda / Miniconda)
  python -m pip install -e ".[dev]"  (run from the backend/ directory)
Or call an interpreter that already has the dependencies, e.g.
  .venv\Scripts\python.exe -m app.cli.gtfs check-db

> .venv\Scripts\python.exe -m app.cli.gtfs check-db
Cannot connect to MySQL: (1045, "Access denied for user 'transitpulse'@'localhost' (using password: YES)")
Check TP_DATABASE_URL in .env, confirm the local MySQL service is running,
and execute sql/001_create_database.sql in DataGrip (see docs/DATABASE.md).
```

Both paths exit cleanly with actionable guidance instead of a traceback. The first
block was re-captured after the CLI hint was generalised to support conda. The second
block is a **pre-fix** snapshot: it was the symptom of the password mismatch described
in issue 11; §4.2 shows the connection succeeding after the credentials were corrected.

### 4.2 Live MySQL verification with the real AT feed

After pointing `TP_DATABASE_URL` at the machine's own MySQL account, the full Phase 1
chain was executed against the real database:

```text
> python -m app.cli.gtfs check-db
Connected to MySQL: 8.0.42
Tables (0): none yet

> python -m app.cli.gtfs migrate
Migrations applied: head

> python -m app.cli.gtfs check-db
Connected to MySQL: 8.0.42
Tables (7): agencies, alembic_version, gtfs_feeds, routes, stop_times, stops, trips

> python -m app.cli.gtfs load --download
Downloaded feed to data\gtfs\gtfs-8307d05c9a8b.zip
{
  "status": "loaded",
  "feed_id": 1,
  "checksum": "8307d05c9a8b9de5f2e2c1d6bb965a8cee8813706bb30320c78d4808700a8ba9",
  "counts": {
    "agencies": 17, "routes": 218, "stops": 6993,
    "trips": 32949, "stop_times": 987373
  },
  "skipped_stops": 0
}
```

The downloaded archive was 24,659,311 bytes from `https://gtfs.at.govt.nz/gtfs.zip`.
No rows had invalid coordinates. Re-running the same import reports
`"status": "unchanged"` (checksum idempotence on real data).

Opt-in integration test (previously skipped):

```text
> set "TP_RUN_MYSQL_INTEGRATION=1"
> python -m pytest tests/integration -m integration
1 passed, 1 warning in 0.08s
```

API responses against the 987,373-row `stop_times` table, measured through
`TestClient` with a real MySQL session:

| Request | Status | Total | Time |
| --- | --- | --- | --- |
| `GET /api/v1/network/status` | 200 | — | 0.087s |
| `GET /api/v1/routes?limit=3` | 200 | 218 | 0.057s |
| `GET /api/v1/routes?mode=Rail&limit=3` | 200 | 4 | 0.053s |
| `GET /api/v1/stops?q=Britomart` | 200 | 5 | 0.084s |
| `GET /api/v1/stops?lat=-36.8443&lon=174.7670&radius_m=500` | 200 | 72 | 0.046s |
| `GET /api/v1/routes/18` | 404 | — | 0.039s |
| `GET /api/v1/routes/18/stops?limit=5` | 200 | 0 | 0.055s |

The last two lines expose a real API usability gap: AT `route_id` values are not the
same as the public route number (`route_short_name`), so `/routes/18` returns 404. The
React UI is unaffected because it passes `route_id` from the list response. Recorded as
a known limitation for Phase 3, where a `short_name` lookup will be added.

## 5. Configuration file validation

`docker-compose.yml` and `.github/workflows/ci.yml` were parsed with PyYAML to confirm
valid YAML syntax. `docker-compose.yml` remains optional and was not executed.

## 6. Issues found and resolved

| # | Issue | Resolution |
| --- | --- | --- |
| 1 | Ruff `B008` flagged standard FastAPI `Depends(...)` defaults (6 occurrences) | Added `extend-immutable-calls = ["fastapi.Depends", "fastapi.Query"]` to `pyproject.toml` |
| 2 | Ruff `UP017` on `timezone.utc` | Switched to `from datetime import UTC` and `datetime.now(UTC)` |
| 3 | Ruff `B905` on `zip()` | Added explicit `strict=False` |
| 4 | Ruff `I001` unsorted imports in `test_network_api.py` | Reordered imports |
| 5 | TypeScript `TS2769`: `@vitejs/plugin-react` (Vite 6) incompatible with Vitest 2's nested Vite types | Upgraded `vitest` to `^3.2.4`; `npm ls vite` now shows a single deduped `vite@6.4.6` |
| 6 | Two frontend tests failed with "Found multiple elements" because Testing Library auto-cleanup was inactive | Added explicit `cleanup()` in `afterEach` of `App.test.tsx` |
| 7 | Alembic `DeprecationWarning: No path_separator found in configuration` | Added `path_separator = os` to `alembic.ini` |
| 8 | Starlette `httpx` deprecation warning | Recorded, not suppressed; no functional impact |
| 9 | `npm ci` was aborted locally by the environment's bulk-deletion guard (`SAFE_DELETE_BULK_CONFIRM_REQUIRED`, 1048 files in `node_modules`), leaving the local install incomplete | Restored with `npm install` and re-ran the full frontend suite (9/9) and build (exit 0). Local instructions now use `npm install`; CI keeps `npm ci` on a clean runner where no deletion is needed |
| 10 | Running the CLI with the system/Anaconda Python produced `ModuleNotFoundError: No module named 'pydantic_settings'`; `check-db` also emitted a long SQLAlchemy traceback when MySQL credentials were missing | Added `ensure_dependencies()` with an actionable environment hint (later generalised for conda, issue 13) and `report_database_error()` with a short MySQL hint; documented both in `README.md` and `docs/DATABASE.md`; added 3 CLI tests and re-ran the full suite (52 passed, 93%) |
| 11 | `check-db` returned `1045 Access denied for user 'transitpulse'@'localhost'` even though the SQL script had been run | `CREATE USER IF NOT EXISTS` does not reset an existing account's password, so the account existed with a different password. Switched `TP_DATABASE_URL` to the machine's own MySQL account (verified `CURRENT_USER()` and MySQL 8.0.42), documented how to find the account in DataGrip, and added the `ALTER USER` escape hatch |
| 12 | `set TP_RUN_MYSQL_INTEGRATION=1 && pytest ...` still reported `1 skipped` on Windows cmd | `set VAR=1 &&` leaves a trailing space in the value. Made the skip condition use `.strip()`, and documented the quoted form `set "TP_RUN_MYSQL_INTEGRATION=1"` |
| 13 | A conda environment should be usable instead of `.venv`, but the CLI hint only mentioned `venv` | Generalised `VENV_HINT` and the CLI docstring, added a conda setup section to `README.md` and `docs/DATABASE.md`, and extended the CLI test |
| 14 | `GET /api/v1/routes/18` returned 404 on real AT data | AT `route_id` is not the public route number. Not a code defect (the UI passes `route_id`); recorded as a known limitation with a `short_name` lookup planned for Phase 3 |

## 7. Not verified in this phase

| Item | Reason | Owner / planned verification |
| --- | --- | --- |
| Leaflet map rendering in a real browser | Automated tests mock `StopMap` to avoid jsdom layout limits | Manual check at `http://localhost:5173` |
| GitHub Actions workflow | No push made by the assistant | First push of Phase 1 |
| `npm ci` from a populated `node_modules` | Blocked by the local bulk-deletion guard; see issue 9 above | CI runs it on a clean GitHub Actions runner on the first push |
| `docker compose up -d mysql` | Docker not installed; not required | Optional, never a release gate |
| Conda environment end-to-end | A conda env was not created in this environment; the CLI dependency check accepts any interpreter with the requirements installed | Repository owner, using the commands in `README.md` |

All MySQL-dependent items that were previously listed here are now verified; see
§4.2.

## 8. Conclusion

Phase 1 meets its definition of done: all features are implemented, both automated
suites are green (52 backend + 1 opt-in integration + 9 frontend), the CLI and API are
verified end-to-end against **real Auckland Transport data in local MySQL** (218
routes, 6,993 stops, 987,373 stop times), the documentation set is complete, and no
secrets or generated artefacts are staged. The remaining unverified items are
environmental (browser rendering, first CI run, conda) and do not block Phase 2.
