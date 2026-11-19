# PHASE-05: Analytics MVP

- **Status:** Complete (not committed)
- **Date:** 2026-11-20
- **Depends on:** Phase 4 (official AT XLSX reports), Phase 1 (GTFS network), Phase 2/3 (live map)
- **Milestone:** **MVP reached**

## 1. Goal

Turn the imported official reports and static GTFS network into a usable analytics product
without sacrificing the existing realtime map. The entry point of the web app remains the
live bus map; analytics lives on its own page so each module can evolve independently.

## 2. Product structure

```text
/                         Live map, route explorer, ETA board, service alerts
/analytics                Overview
/analytics/ridership      Most used routes and ridership trends
/analytics/performance    Routes requiring attention and service trends
/analytics/relationships  Ridership vs punctuality and optional seasonality
/analytics/methodology    Definitions, source coverage and route mapping
```

Navigation is a **narrow left sidebar** in the application shell. The live map is not
moved or embedded inside analytics. Future modules such as `Prediction models` and
`Network analysis` are represented as clearly labelled disabled placeholders so the
navigation scales as the system grows.

## 3. Features delivered

| # | Feature | Outcome |
| --- | --- | --- |
| F1 | Routed application shell | `react-router-dom`; `/` defaults to the live map; `/analytics` is a separate page |
| F2 | Preserved live map | All Phase 2/3 functionality remains on the landing page: bus glyphs, direction-scoped vehicles, geometry, ETA board and alerts |
| F3 | Analytics service layer | `app/analytics/service.py` owns de-duplication, aggregation, school-route filtering and metric selection |
| F4 | Analytics API | `/analytics/summary`, `/route-ranking`, `/trends`, `/heatmap`, `/patronage-vs-performance`, `/network` |
| F5 | Data sufficiency | Summary reports report coverage and labels it `limited`, `moderate` or `strong` |
| F6 | Ranking | Ranks bus routes by punctuality, reliability, boardings or boardings/service hour; school routes hidden by default |
| F7 | Trend and seasonality | Monthly trend for a selected route or the bus network; route × month heatmap moved into an optional `Seasonality detail` disclosure |
| F8 | Patronage vs performance | One point per route, averaged across the selected period; low-ridership routes filtered and highest-ridership routes labelled |
| F9 | Network structure | Reuses static GTFS counts: bus routes, stops, scheduled trips, shape points, stop-time density |
| F10 | Modular frontend | `pages/`, `components/analytics/`, `hooks/`, `api/` and `lib/` keep UI, data fetching and formatting separate |
| F11 | Lightweight charts | SVG charts and tables implemented locally; no large charting dependency |
| F12 | Explicit caveats | AT punctuality/reliability definitions, school-route warning and correlation/causation note shown in UI |
| F13 | Decision-oriented panels | Each view states one business question; definitions and technical metadata are isolated in Methodology |
| F14 | Civic-data visual system | Warm off-white canvas, white surfaces, charcoal type, restrained forest-green accent and limited amber warnings |
| F15 | Locale-independent filters | English `Year` / `Month` selects replace browser-localized native month inputs |
| F16 | Separate ridership semantics | `Most used routes` and `Routes requiring attention` are separate views; ridership is never presented as a performance grade |
| F17 | Metric metadata | API returns units, definitions, source family, reporting period and warnings for out-of-coverage selections |
| F18 | Route number mapping | `/analytics/routes` maps official route numbers to GTFS `route_id` values without changing either dataset |
| F19 | Correlation with validity rules | Relationship chart shows Spearman correlation only when at least five comparable routes are available |
| F20 | Interactive charts | Clicking or keyboard-selecting a point/cell reveals exact values, sample sizes and period details |

## 4. Architecture and maintainability

The Phase 5 refactor was done with three maintainability goals in mind:

### Comprehensibility

- Page responsibilities are explicit: `LiveMapPage` vs `AnalyticsPage` and five focused
  analytics subviews.
- API access lives only in `api/client.ts`; analytics data fetching lives in `hooks/useAnalytics.ts`.
- Aggregation logic lives only in `app/analytics/service.py`; FastAPI endpoints validate and serialize.
- Metric definitions live in one place on both sides: `METRIC_CATALOG` and
  `metricDefinitions.ts`.
- Shared filter state is URL-synced through `useAnalyticsFilters`, so route selection can
  carry across views.
- UI components are small and named after what they render.

### Alterability

- Adding a new analytics metric requires: validate in API, add definition/unit, add UI option.
- Adding a new chart requires a new component under `components/analytics/charts/` without
  touching map code or other views.
- The live map and analytics share only the application shell and API client.
- Source-family priority and school-route rules are constants in the service layer.
- Design tokens are separated into `styles/tokens.css`, layout into `layout.css`, chart
  primitives into `charts.css` and analytics controls into `analytics.css`.

### Testability

- Analytics services are tested through the API with synthetic official rows.
- Frontend views are tested with mocked API responses and a router.
- Chart interactions are tested directly with click and keyboard events.
- Route mapping, metric metadata, correlation validity and school-route behaviour have
  backend tests.
- Formatting helpers are pure functions with unit tests.
- No test depends on AT API credentials or browser layout.

### Professional redesign after audit

A formal audit found repeated explanation panels, weak hierarchy, mixed business meanings,
dense charts and inconsistent spacing. The redesign:

- adopts a civic-data identity: `#F7F7F4` canvas, white surfaces, `#202B31` type,
  `#25685F` forest-green accent and limited `#C58B45` amber warnings;
- removes dark blue sidebar, gradients and generic dashboard card language;
- organizes Analytics into Overview, Ridership, Performance, Relationships and
  Methodology;
- isolates report counts and definitions in Methodology;
- separates "Most used routes" from "Routes requiring attention";
- distinguishes network boardings totals from per-route averages;
- maps official route numbers to GTFS `route_id` values for cross-view selection;
- returns metric units, definitions, source families and coverage from the API;
- shows a warning when the selected period falls outside source coverage;
- provides click/keyboard selection with exact values on charts;
- shows Spearman correlation only when at least five comparable routes exist;
- displays a sequential heatmap palette with a legend and optional per-route normalization.

## 5. Backend implementation

| Area | Files |
| --- | --- |
| Analytics service | `backend/app/analytics/service.py` |
| API | `backend/app/api/analytics.py`, `backend/app/main.py` |
| Tests | `backend/tests/test_analytics_api.py` |

Key service decisions:

1. **One value per route/month** — de-duplicates official report families with priority:
   `punctuality_report` > `bus_performance_report` > `hourly_boardings_report`.
2. **School routes hidden by default** — official `S...` routes have near-zero punctuality
   and would dominate lowest-ranking charts.
3. **Averages rounded to 6 decimals** — stable API output and frontend formatting.
4. **Static network metrics read from active feed** — no external requests.
5. **Scatter is route-level, not route-month level** — the service averages boardings and
   punctuality by route over the selected period; the API supports `min_boardings` and
   `limit` so the chart answers a business comparison instead of showing dense raw rows.
6. **Heatmap is an optional diagnostic** — route × month values are useful only for
   seasonality checks, so they are folded into `Seasonality detail` rather than occupying
   the default decision flow.
7. **Metric semantics are data, not UI copy** — `METRIC_CATALOG` carries labels, units,
   definitions, source families and kinds; endpoints attach this metadata to responses.
8. **Route mapping is read-only** — official `route_no` values are mapped to GTFS
   `route_id` values by `short_name`; unmatched official-only rows are labelled as such.
9. **Correlation has validity rules** — Spearman is returned only when at least five
   comparable route averages are available.

## 6. Frontend implementation

| Area | Files |
| --- | --- |
| Routing shell | `frontend/src/App.tsx`, `frontend/src/components/AppShell.tsx` |
| Live page | `frontend/src/pages/LiveMapPage.tsx` |
| Analytics layout | `frontend/src/pages/AnalyticsPage.tsx` |
| Analytics views | `frontend/src/pages/analytics/{Overview,Ridership,Performance,Relationships,Methodology}View.tsx` |
| Reusable UI | `frontend/src/components/ui/*` |
| Analytics charts | `frontend/src/components/analytics/charts/*` |
| Hooks | `frontend/src/hooks/useAnalytics.ts`, `frontend/src/hooks/useAnalyticsFilters.tsx` |
| Domain helpers | `frontend/src/lib/metricDefinitions.ts`, `frontend/src/lib/analytics.ts` |
| Styling | `frontend/src/styles/{tokens,layout,charts,analytics}.css` |

No existing map component was deleted: `StopMap`, `RouteExplorer`, `PassengerBoard`,
`busIcon`, `mapBounds` and their tests are unchanged apart from being composed under
`LiveMapPage`.

## 7. API contract

```text
GET /api/v1/analytics/summary
GET /api/v1/analytics/metrics
GET /api/v1/analytics/routes?q=
GET /api/v1/analytics/network
GET /api/v1/analytics/route-ranking?metric=punctuality&start_month=&end_month=&limit=&min_months=&include_school_routes=
GET /api/v1/analytics/trends?metric=&route_no=&start_month=&end_month=
GET /api/v1/analytics/heatmap?metric=&start_month=&end_month=&limit=
GET /api/v1/analytics/patronage-vs-performance?start_month=&end_month=&min_boardings=&limit=
```

Supported metrics:

```text
punctuality
reliability
boardings
boardings_per_service_hour
```

## 8. Real-data verification

Examples from the real imported tables:

```text
summary:
  report_count 13
  punctuality coverage 2019-01 .. 2026-10, 94 months, sufficiency=strong

network:
  bus_routes 197
  stops 6993
  scheduled_trips 32949
  shape_points 532630
  stop_time_rows 987373

lowest average punctuality 2024-07..2025-06, school routes hidden:
  392 Pukekohe Northwest Loop          0.557603
  12  Henderson to Constellation...   0.571190 (3 sample months)
  395 Waiuku To Papakura Interchange  0.661933

route 70 punctuality trend:
  2024-07 0.893675
  2024-08 0.833377
  2024-09 0.791783

scatter, route averages 2019-01..2026-10, min_boardings=1000:
  NX1 average boardings 298757, punctuality 0.9447, 75 months
  70  average boardings 249327, punctuality 0.9338, 75 months
  NX2 average boardings 176882, punctuality 0.9830, 75 months
  Spearman correlation 0.3, sample_size 5

metric metadata:
  4 metrics
  punctuality unit %, boardings unit "passenger trips"
  source coverage returned per metric

route mapping q=70:
  6 matches
  route 70 -> GTFS route_id 70-205
```

## 9. Tests

Backend: Ruff clean, **122 passed / 1 skipped / 89% coverage**.
Frontend: TypeScript strict check clean, **61 tests passed**, production build exit 0.
Details: `docs/test-reports/PHASE-05.md`.

## 10. Known limitations

- No geographic reliability map yet; analytics charts use official route numbers.
- Route mapping is available in Methodology, but route context is not yet carried from the
  Live map into Analytics.
- Patronage vs performance is descriptive and can be biased by route length/service type.
- The heatmap is intentionally collapsed; it is a seasonality diagnostic, not a headline KPI.
- Browser visual QA was not performed; component and routing tests cover behaviour.

## 11. Next phase

Phase 6 (Hardening): caching, observability, error budgets, security review, load tests and
runbook. AWS deployment remains Phase 7.

The official metrics are a **monthly unbalanced panel time series** (`route_no + month ->
punctuality / reliability / boardings`). Time-series analysis is worth pursuing in a future
`Prediction models` module: seasonality decomposition, route-level SARIMA/Prophet baselines,
lag-feature gradient boosting, anomaly detection and hierarchical forecasts are all
reasonable. The caveats are sparse route-month coverage, route-number changes, missing
months and AT definition changes around 2023. High-frequency real-time ETA forecasting
would still require stop-level observations that the current project deliberately does not
collect.

## 12. Commit

No commit or push was performed. All changes remain in the working tree.
