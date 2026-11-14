# PHASE-00: Foundation

- **Status:** Complete
- **Date:** 2026-11-14
- **Branch (suggested):** `phase/00-foundation`
- **Tag (suggested):** `phase-00`

## 1. Scope

Establishes everything needed to build the product in small, reviewable increments:
repository conventions, documentation structure, local configuration, MySQL container
definition, a runnable FastAPI skeleton, CI, and the first automated test suite.

Deliberately **not** included: GTFS import, realtime ingestion, database schema, React
UI, analytics, and AWS deployment. No AT API key is required for this phase.

## 2. Problem and approach

A monitoring platform has three very different workloads: polling an external feed,
serving low-latency reads, and computing historical aggregates. Building all of them at
once makes the project hard to review and even harder to test. Phase 0 therefore fixes
the boundaries first (config, docs, test/CI conventions, application factory) and keeps
the running system minimal: two read-only endpoints that prove the process boots and
that compliance metadata is visible from the API.

Alternative rejected: a full microservice split with a message broker. It adds
operational overhead before there is any data to process. The current design can grow
into separate API and worker processes in Phase 2 without changing the config contract.

## 3. Implementation

| Area | Files |
| --- | --- |
| Conventions | `docs/ROADMAP.md`, `docs/WORKFLOW.md`, `docs/phases/_TEMPLATE.md` |
| Design | `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md` |
| Front page | `README.md` |
| Root config | `.gitignore`, `.env.example`, `docker-compose.yml` |
| CI | `.github/workflows/ci.yml` |
| Backend package | `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/main.py` |
| Configuration | `backend/app/core/config.py` |
| HTTP layer | `backend/app/api/ops.py` |
| Tests | `backend/tests/conftest.py`, `backend/tests/test_ops.py`, `backend/tests/test_config.py` |
| Phase record | `docs/phases/PHASE-00-foundation.md`, `docs/test-reports/PHASE-00.md` |

## 4. Interfaces

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe with environment and realtime-configuration status |
| `GET` | `/api/v1/meta` | Service metadata, region, time zone, phase, data attribution |
| `GET` | `/docs`, `/openapi.json` | Interactive OpenAPI documentation |

Example response:

```json
{
  "status": "ok",
  "environment": "local",
  "version": "0.1.0",
  "realtime_feed": "not_configured"
}
```

Configuration variables (prefix `TP_`) are documented in `.env.example`. Key variables:
`TP_ENVIRONMENT`, `TP_DATABASE_URL`, `TP_CORS_ORIGINS`, `TP_AT_API_KEY`,
`TP_AT_VEHICLE_POSITIONS_URL`, `TP_AT_TRIP_UPDATES_URL`, `TP_AT_SERVICE_ALERTS_URL`,
`TP_AT_REALTIME_POLL_SECONDS`.

No database tables are created in this phase. `docker-compose.yml` provisions MySQL 8
with a health check and an optional Adminer profile for Phase 1.

## 5. Design decisions

1. **Application factory (`create_app(settings)`)** - tests inject deterministic settings
   instead of mutating global environment state, and later phases can create separate
   API and worker contexts.
2. **All settings use the `TP_` prefix** - avoids collisions with other tooling and makes
   the deployment migration to AWS Secrets Manager explicit.
3. **Realtime feed URLs are configuration, not constants** - AT exposes both legacy
   GTFS-RT and newer Compat endpoints; the correct paths depend on the subscription.
4. **Minimum 30-second poll interval enforced in config** - AT states the feed is
   refreshed at least every 30 seconds; polling faster only consumes quota.
5. **`realtime_configured` requires a key and all three URLs** - `/health` reports
   readiness honestly without leaking the key.
6. **PyMySQL over `mysqlclient`** - pure Python, so Windows developers do not need a C
   toolchain.
7. **Comma-separated CORS string** - simpler than JSON-in-`.env`, which is a common
   source of configuration errors with Pydantic Settings.
8. **Attribution in the API metadata** - CC BY 4.0 compliance starts at the API layer,
   not as an afterthought in the UI.
9. **UTC storage / `Pacific/Auckland` display** - recorded now so Phase 1 schema work
   does not have to be migrated later.

## 6. How to verify locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                 # Windows
pip install -e ".[dev]"
ruff check .
pytest --cov=app --cov-report=term-missing
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/health`, `http://localhost:8000/api/v1/meta` and
`http://localhost:8000/docs`.

MySQL can be started with `docker compose up -d mysql` (optional in Phase 0).

## 7. Tests

12 automated tests cover endpoint responses, CORS, OpenAPI, secret non-disclosure,
configuration defaults, environment overrides, CORS parsing, realtime readiness and
poll-interval validation. Result: **12 passed, 100% statement coverage**, plus a real
`uvicorn` HTTP smoke test. Full details: `docs/test-reports/PHASE-00.md`.

## 8. Known limitations and risks

- Docker is not installed in the environment used for this phase, so
  `docker-compose.yml` was reviewed but not executed. It will be verified in Phase 1.
- The GitHub Actions workflow has not run yet; it executes after the first push.
- No AT developer portal subscription key was available, so live feed access is
  unverified. The exact endpoint paths and quota must be confirmed in Phase 2.
- Starlette emits a non-blocking `StarletteDeprecationWarning` about
  `httpx`/`httpx2` in `TestClient`; it does not affect results and will be revisited
  when the dependency ecosystem settles.
- The API does not connect to MySQL yet; `TP_DATABASE_URL` is validated only as a
  string. Connection handling and migrations arrive in Phase 1.
- A repository `LICENSE` file is not added yet; it will be added at repository
  initialisation.

## 9. Next phase

Phase 1 downloads the AT GTFS static bundle, introduces Alembic migrations and the
MySQL schema, exposes routes/stops/trips endpoints, and adds the React map-based
network explorer. It will also verify the MySQL container and the CI workflow.

## 10. Manual commit

Provided in chat at phase completion. The assistant does not run any Git write command.
