# Roadmap

NZ TransitPulse is built in small, reviewable phases. Every phase is self-contained: it
ships working code, an implementation document, a test report, and a manual commit.
The MVP is reached at the end of **Phase 5**. AWS deployment is deliberately post-MVP.

## Product goals

| Audience | Question | Answered by |
| --- | --- | --- |
| Passengers | Where is my bus, and when will it arrive? | Phases 1-3 |
| Passengers | Is this route delayed right now? | Phases 2-3 |
| Data-minded users | Which bus routes are least reliable? When are delays worst? | Phases 4-5 |
| Data-minded users | Is reliability improving over time? | Phase 5 |
| Data-minded users | How is patronage related to service performance? | Phases 4-5 |

## Phases

| Phase | Name | Outcome | Main deliverables | MVP |
| --- | --- | --- | --- | --- |
| 0 | Foundation | Local development environment and project conventions | Repo layout, docs, config, MySQL container, FastAPI skeleton, CI, health/meta endpoints, first test report |  |
| 1 | Static network explorer | Browse Auckland routes, stops and timetables | GTFS static loader, MySQL schema + migrations, routes/stops/trips API, React map and search |  |
| 2 | Realtime ingestion | Live vehicles, trip updates and service alerts in the API **and on the map** | Aggregated AT client (auth, retry, quota budget), tolerant GTFS-RT decoder, 30 s poller, in-memory snapshot, realtime endpoints, live vehicle markers |  |
| 3 | Passenger view | A passenger can answer "where is it, when does it arrive, is it delayed?" | Stop arrivals endpoint, ETA board, delay status, bus service alerts, direction/branch UX |  |
| 4 | Official historical reports | Import AT's published punctuality, reliability, patronage and bus-performance workbooks | Report registry, resilient XLSX parser, normalized MySQL tables, route aliases, data-quality checks, reproducible download/import CLI |  |
| 5 | Analytics dashboard | MVP: a modern dashboard answering the analytics questions | Official punctuality/reliability trends, worst-route ranking, monthly heatmap, patronage vs performance, GTFS network analysis, filters, full docs and tests | ✅ |
| 6 | Hardening | Production readiness before cloud deployment | Caching, observability (metrics/logs/traces), error budgets, security review, load tests, runbook |  |
| 7 | AWS deployment | Runs on AWS | RDS MySQL, ECS Fargate, ALB, S3 + CloudFront, Secrets Manager, IaC, deployment runbook |  |

**Post-MVP optional:** a self-hosted observation collector may still be added when the
project runs continuously on a server. It is not part of the MVP and does not block
Phase 6 onwards. Historical analysis in the MVP is based on AT's published reports.

**Status (2026-11-20):** Phase 0, Phase 1, Phase 1B, Phase 2, Phase 3 and Phase 4 are
complete, verified and pushed. Phase 4 imported 13 official AT XLSX reports into normalized
MySQL tables, replacing self-hosted observation collection for the MVP. **Phase 5 is
complete in the working tree but not yet committed**: the live map remains the landing
page, analytics is a separate product area with Overview, Ridership, Performance,
Relationships and Methodology subviews. The backend has a dedicated analytics service
with metric metadata, route mapping, ranking, trend, heatmap, correlation and network
endpoints. The UI uses a narrow civic-data shell, English date controls, explicit units,
interactive charts and a compact methodology area. **MVP is reached.** Phase 6
(Hardening) is next. See `docs/phases/PHASE-05-analytics-mvp.md`.

**v0.6 product upgrade:** v0.6.1 reorganizes the product into Network Overview, Live
Network, Route Intelligence, Service Health, Network Analytics, Route Comparison and Data
& Methodology without rewriting backend calculations. See
`docs/releases/v0.6.1.md`. v0.6.2 establishes the global visual system across the shell,
live map and analytics without changing backend calculations. See
`docs/releases/v0.6.2.md`. v0.6.3 adds the Route Intelligence workspace and display-only
GTFS shape smoothing for clearer map geometry. See `docs/releases/v0.6.3.md`.

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
- Metrics distinguish **official published indicators** from locally computed network
  metrics from GTFS. Official punctuality/reliability definitions must be shown in the UI.
- Raw source reports are treated as inputs, not redistributed as project data. Imported
  rows keep report metadata and AT attribution for auditability.
