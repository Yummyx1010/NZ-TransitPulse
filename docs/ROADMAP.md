# Roadmap

NZ TransitPulse is built in small, reviewable phases. Every phase is self-contained: it
ships working code, an implementation document, a test report, and a manual commit.
The MVP is reached at the end of **Phase 5**. AWS deployment is deliberately post-MVP.

## Product goals

| Audience | Question | Answered by |
| --- | --- | --- |
| Passengers | Where is my bus / train / ferry, and when will it arrive? | Phases 1-3 |
| Passengers | Is this route delayed right now? | Phases 2-3 |
| Data-minded users | Which routes are least reliable? When are delays worst? | Phases 4-5 |
| Data-minded users | Is reliability improving over time? | Phase 5 |

## Phases

| Phase | Name | Outcome | Main deliverables | MVP |
| --- | --- | --- | --- | --- |
| 0 | Foundation | Local development environment and project conventions | Repo layout, docs, config, MySQL container, FastAPI skeleton, CI, health/meta endpoints, first test report |  |
| 1 | Static network explorer | Browse Auckland routes, stops and timetables | GTFS static loader, MySQL schema + migrations, routes/stops/trips API, React map and search |  |
| 2 | Realtime ingestion | Live vehicles, trip updates and service alerts available in the API | AT API client (auth, retry, rate limiting), GTFS-RT decoding, scheduled poller, in-memory snapshot, realtime endpoints |  |
| 3 | Passenger view | A passenger can answer "where is it, when does it arrive, is it delayed?" | Stop/route pages, ETA list, live map, delay status, service alerts panel |  |
| 4 | Historical observations | Permitted, auditable history collection | Compliance and retention notes, observation schema, collector worker, data quality checks, backfill from recorded snapshots |  |
| 5 | Reliability analytics | MVP: a modern dashboard answering the analytics questions | Punctuality / OTP metrics, worst-route ranking, time-of-day heatmap, trend charts, filters, full docs and test suite | ✅ |
| 6 | Hardening | Production readiness before cloud deployment | Caching, observability (metrics/logs/traces), error budgets, security review, load tests, runbook |  |
| 7 | AWS deployment | Runs on AWS | RDS MySQL, ECS Fargate, ALB, S3 + CloudFront, Secrets Manager, IaC, deployment runbook |  |

**Status (2026-11-15):** Phase 0, Phase 1 and the Phase 1B route-geometry fix are
complete and verified; Phase 2 (GTFS-Realtime ingestion) is next. Phase 1 added the
MySQL schema and Alembic migrations, the GTFS static loader CLI, six read-only network
endpoints, and the React network explorer. Phase 1B imported `shapes.txt`, added the
per-shape geometry endpoint, and replaced the straight-line stop map with real route
geometry (see `docs/phases/PHASE-01B-route-geometry.md`).

## Phase dependencies

```text
Phase 0 ──> Phase 1 ──> Phase 3 ──> Phase 5 ──> Phase 6 ──> Phase 7
              │            ▲          ▲
              └──> Phase 2 ┘          │
                     └──> Phase 4 ────┘
```

## Scope control

- Phase 0-5 run entirely locally (`localhost`), with no AWS account required. From
  Phase 2 onwards an Auckland Transport developer portal subscription key is needed;
  see `docs/DATA_SOURCES.md`.
- No authentication, payments, or user accounts in the MVP.
- No raw GTFS-Realtime payload redistribution; see `DATA_SOURCES.md`.
- Map tiles come from OpenStreetMap via Leaflet so no paid map token is required.
- Metrics are only shown with a clearly labelled data-sufficiency indicator, because a
  meaningful reliability trend needs several weeks of observations.
