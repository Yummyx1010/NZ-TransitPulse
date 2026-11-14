# Architecture

## System context

```mermaid
flowchart LR
    AT[Auckland Transport\nGTFS static + GTFS-Realtime] -->|HTTPS| ING[Python ingestion workers]
    ING -->|SQLAlchemy| DB[(MySQL 8)]
    DB --> API[FastAPI backend]
    ING --> SNAP[In-memory realtime snapshot]
    SNAP --> API
    API -->|REST / JSON| WEB[React + Vite dashboard]
    WEB --> USER[Passenger / analyst]
```

## Components

| Component | Technology | Responsibility |
| --- | --- | --- |
| `backend/app/api` | Python 3.12, FastAPI, Pydantic | REST API, validation, OpenAPI docs |
| `backend/app/gtfs` | `zipfile`, `csv`, `httpx` | Parse and transactionally load the AT static bundle |
| `backend/app/cli/gtfs.py` | argparse, Alembic | `migrate`, `check-db`, `load`, `status` commands |
| `backend/app/models` | SQLAlchemy 2 ORM | GTFS static tables keyed by `feed_id` |
| `backend/migrations` | Alembic | Versioned MySQL schema |
| `backend/app/ingestion` (Phase 2+) | `httpx`, scheduled worker | Poll AT feeds, decode GTFS-RT, publish snapshot |
| `backend/app/collector` (Phase 4+) | SQLAlchemy | Persist derived delay observations, enforce retention |
| `backend/app/analytics` (Phase 5+) | SQL / aggregations | Punctuality, route ranking, heatmaps, trends |
| Database | MySQL 8 (local install; Docker Compose optional; RDS later) | Static network, observations, aggregates |
| `frontend` | React 18, TypeScript, Vite, TanStack Query, Leaflet | Static network explorer with a stop map (live vehicles in Phase 3, analytics in Phase 5) |
| CI | GitHub Actions | Backend lint/tests and frontend typecheck/tests/build |

## Data flow

1. **Static load** (Phase 1): download the AT GTFS zip, validate it, load routes/stops/
   trips/stop_times/shapes into MySQL with a feed version marker. Runs on demand, then
   on a schedule.
2. **Realtime poll** (Phase 2): one poll per configured interval (minimum 30 s) fetches
   vehicle positions, trip updates and alerts. The response is decoded into a typed
   snapshot and cached in memory for low-latency reads.
3. **Passenger reads** (Phase 3): the browser calls the API for stop arrivals and live
   vehicles; the API joins the realtime snapshot with the static schedule.
4. **Observation collection** (Phase 4): each poll writes compact derived delay records.
   Data quality checks reject impossible values and duplicates.
5. **Analytics** (Phase 5): scheduled aggregation produces daily/hourly reliability
   metrics; the dashboard reads only aggregates, not raw observations.

## Key decisions

| Decision | Rationale |
| --- | --- |
| UTC in storage, `Pacific/Auckland` in UI | Correct handling of NZST/NZDT and GTFS times past midnight |
| Derived observations only | Compliance, small storage footprint, fast analytics queries |
| PyMySQL driver instead of `mysqlclient` | Pure Python, works on Windows without a C toolchain |
| In-memory snapshot for live state | Live data is ephemeral; the database holds history, not current positions |
| Leaflet + OpenStreetMap | No paid token or API key needed for the MVP |
| Server-side API key | The browser never sees the AT subscription key |
| Full snapshots, no diffing | The AT feed does not support incremental updates |
| Configurable endpoint URLs | Legacy and Compat API paths differ per subscription |
| Data-sufficiency labels | Reliability claims require weeks of observations, not minutes |
| Feed-version staging | A new GTFS bundle is loaded under a new `feed_id` and activated in one transaction, so readers never see a half-imported network |
| BOM and nested-folder tolerant parsing | Real GTFS bundles differ in encoding and archive layout |
| GTFS times stored as both raw string and seconds | Supports scheduled times past `24:00:00` without losing the original value |
| Geo search uses a bounding box | Adequate for "stops near me" at city scale; a spatial index can replace it later |
| No database-level FKs between child tables | Keeps bulk inserts fast; referential integrity is enforced by the loader transaction |

## Local topology (Phase 0-5)

```text
localhost:3306  MySQL 8 (local install; container optional)
localhost:8000  FastAPI  (uvicorn --reload)
localhost:5173  Vite dev server (proxies /api to :8000)
```

Phase 1 runs entirely against the local MySQL server. Phase 0-5 unit and API tests use
an in-memory/file SQLite database so they never require MySQL credentials; the opt-in
`integration` test verifies the real MySQL schema.

## Target AWS topology (Phase 7, post-MVP)

```text
Route 53 / CloudFront -> S3 (React build)
                      -> ALB -> ECS Fargate (FastAPI + workers)
                                  -> RDS MySQL (Multi-AZ optional)
                                  -> Secrets Manager (AT API key)
CloudWatch (logs, metrics, alarms), ECR (images), IaC (CDK or Terraform)
```
