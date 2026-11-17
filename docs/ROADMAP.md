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
| 2 | Realtime ingestion | Live vehicles, trip updates and service alerts in the API **and on the map** | Aggregated AT client (auth, retry, quota budget), tolerant GTFS-RT decoder, 30 s poller, in-memory snapshot, realtime endpoints, live vehicle markers |  |
| 3 | Passenger view | A passenger can answer "where is it, when does it arrive, is it delayed?" | Stop arrivals endpoint, ETA board, delay status, bus service alerts, direction/branch UX |  |
| 4 | Historical observations | Permitted, auditable history collection | Compliance and retention notes, observation schema, collector worker, data quality checks, backfill from recorded snapshots |  |
| 5 | Reliability analytics | MVP: a modern dashboard answering the analytics questions | Punctuality / OTP metrics, worst-route ranking, time-of-day heatmap, trend charts, filters, full docs and test suite | ✅ |
| 6 | Hardening | Production readiness before cloud deployment | Caching, observability (metrics/logs/traces), error budgets, security review, load tests, runbook |  |
| 7 | AWS deployment | Runs on AWS | RDS MySQL, ECS Fargate, ALB, S3 + CloudFront, Secrets Manager, IaC, deployment runbook |  |

**Status (2026-11-17):** Phase 0, Phase 1, Phase 1B and Phase 2 are complete, verified
and pushed. **Phase 3 is complete but not yet committed**: buses-only scope, a stop-ETA
board combining the static timetable with live delays, delay status, bus service alerts,
direction/branch UX polish, imported service calendars and route-scoped stop/ETA search.
Phase 4 (historical observations) is next. See
`docs/phases/PHASE-03-passenger-view.md` for the delivered passenger view.

## Phase dependencies

```text
Phase 0 ──> Phase 1 ──> Phase 3 ──> Phase 5 ──> Phase 6 ──> Phase 7
              │            ▲          ▲
              └──> Phase 2 ┘          │
                     └──> Phase 4 ────┘
```

## Scope control

- **Buses only.** Trains, ferries and other modes remain in the imported static GTFS data
  but are never shown in the UI, the live vehicle layer, or the analytics. The dashboard
  always requests `mode=Bus` and the route explorer has no mode selector.
- Phase 0-5 run entirely locally (`localhost`), with no AWS account required. From
  Phase 2 onwards an Auckland Transport developer portal subscription key is needed;
  see `docs/DATA_SOURCES.md`.
- No authentication, payments, or user accounts in the MVP.
- No raw GTFS-Realtime payload redistribution; see `DATA_SOURCES.md`.
- Map tiles come from OpenStreetMap via Leaflet so no paid map token is required.
- Metrics are only shown with a clearly labelled data-sufficiency indicator, because a
  meaningful reliability trend needs several weeks of observations.
