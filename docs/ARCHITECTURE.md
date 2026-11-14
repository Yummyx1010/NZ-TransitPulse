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
| `backend/app` | Python 3.12, FastAPI, Pydantic | REST API, configuration, validation, OpenAPI docs |
| `backend/app/ingestion` (Phase 2+) | `httpx`, scheduled worker | Poll AT feeds, decode GTFS-RT, publish snapshot |
| `backend/app/collector` (Phase 4+) | SQLAlchemy | Persist derived delay observations, enforce retention |
| `backend/app/analytics` (Phase 5+) | SQL / aggregations | Punctuality, route ranking, heatmaps, trends |
| `backend/migrations` (Phase 1+) | Alembic | Versioned MySQL schema |
| Database | MySQL 8 (Docker Compose locally, RDS later) | Static network, observations, aggregates |
| `frontend` (Phase 1+) | React, TypeScript, Vite, TanStack Query, Leaflet, Recharts | Explorer, live map, analytics dashboard |
| CI | GitHub Actions | Lint and test on every push |

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

## Local topology (Phase 0-5)

```text
localhost:3306  MySQL 8 (Docker Compose or local install)
localhost:8000  FastAPI  (uvicorn --reload)
localhost:5173  Vite dev server (proxies /api to :8000)
```

## Target AWS topology (Phase 7, post-MVP)

```text
Route 53 / CloudFront -> S3 (React build)
                      -> ALB -> ECS Fargate (FastAPI + workers)
                                  -> RDS MySQL (Multi-AZ optional)
                                  -> Secrets Manager (AT API key)
CloudWatch (logs, metrics, alarms), ECR (images), IaC (CDK or Terraform)
```
