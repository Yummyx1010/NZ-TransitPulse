# Test Report: Phase 05 - Analytics MVP

- **Date:** 2026-11-20
- **Result:** **PASS** — backend 122 passed / 1 skipped / 89% coverage, Ruff clean; frontend 61 passed, TypeScript strict check clean, production build exit 0; real MySQL analytics endpoints verified after the professional dashboard redesign
- **Phase document:** `docs/phases/PHASE-05-analytics-mvp.md`

## 1. Environment

| Item | Value |
| --- | --- |
| OS | Windows (win32), `cmd` shell |
| Python | 3.12.7, `backend/.venv` |
| Node.js / npm | v24.14.0 / 11.9.0 |
| MySQL | Local 8.0.42, `transitpulse`, alembic `0004` |
| Git | Phase 4 committed as `ebd4afa`; Phase 5 changes uncommitted |
| Browser | Not used for visual QA; jsdom component/routing tests only |

## 2. Backend checks

```text
> .venv\Scripts\python.exe -m ruff check .
All checks passed!

> .venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
122 passed, 1 skipped, 1 warning in 56.75s
TOTAL 2247 stmts / 247 missed / 89% coverage
app\analytics\service.py      190     37    81%
app\api\analytics.py           49      0   100%
app\main.py                    48      1    98%
```

### Backend test coverage

| File | Coverage |
| --- | --- |
| `test_analytics_api.py` | Summary/coverage, metric metadata and units, route number mapping, Spearman sample-size rule, data-sufficiency label, route ranking, source-family de-duplication, school-route exclusion/inclusion, trends, heatmap, scatter, static network summary, invalid metric 400 |

## 3. Frontend checks

```text
> npx tsc --noEmit
TSC_OK

> npx vitest run
61 tests, 61 passed, 0 failed

> npm run build
vite v6.4.6 — 155 modules transformed
dist/index.html                   0.56 kB
dist/assets/index-af4WF0sX.css   44.50 kB
dist/assets/index-KLzYZgkw.js   411.80 kB
built in 1.50s
```

New frontend tests:

| File | Coverage |
| --- | --- |
| `src/lib/analytics.test.ts` | Percentage/boardings formatting, change formatting, metric labels, heat colours, English month generation |
| `src/api/client.test.ts` | Analytics ranking, trend and route-averaged scatter URL construction |
| `src/pages/AnalyticsPage.test.tsx` | Overview, ridership and relationships subviews with URL-synced filter context |
| `src/components/analytics/charts/ChartInteractions.test.tsx` | Click and keyboard selection for ridership, scatter and heatmap charts; correlation display; missing cells |
| `src/App.routing.test.tsx` | Default `/` live map, left sidebar, future module placeholders, navigation both ways |

All earlier live-map, geometry, realtime and passenger-board tests still pass.

## 4. Real-data endpoint verification

No extra AT API calls were used; these endpoints read MySQL only.

```text
GET /api/v1/analytics/summary
  200 report_count=13
  punctuality coverage 2019-01..2026-10, 94 months, sufficiency=strong

GET /api/v1/analytics/network
  200 bus_routes=197 stops=6993 scheduled_trips=32949
     shape_points=532630 stop_time_rows=987373 avg_stop_times_per_trip=30.0

GET /api/v1/analytics/route-ranking?metric=punctuality&start_month=2024-07&end_month=2025-06&limit=5
  200 total=5
  392 average=0.557603, 12 average=0.571190, 395 average=0.661933

GET /api/v1/analytics/trends?metric=punctuality&route_no=70&start_month=2024-07&end_month=2025-06
  200 total=12
  2024-07=0.893675, 2024-08=0.833377, 2024-09=0.791783

GET /api/v1/analytics/heatmap?metric=punctuality&start_month=2024-07&end_month=2025-06&limit=3
  200 months=12, items=3
  route 392 values include 0.515088 -> 0.812633

GET /api/v1/analytics/metrics
  200 total=4
  punctuality unit=%, boardings unit=passenger trips
  source coverage returned per metric

GET /api/v1/analytics/routes?q=70
  200 total=6
  route 70 -> GTFS route_id 70-205, matched_in_gtfs=true

GET /api/v1/analytics/patronage-vs-performance?start_month=2019-01&end_month=2026-10&min_boardings=1000&limit=5
  200 aggregation=route_average, total=5
  NX1 avg boardings=298757, avg punctuality=0.9447, 75 months
  70  avg boardings=249327, avg punctuality=0.9338, 75 months
  NX2 avg boardings=176882, avg punctuality=0.9830, 75 months
  correlation=0.3 (Spearman), sample_size=5
```

## 5. Issues found and resolved

| # | Issue | Resolution |
| --- | --- | --- |
| 1 | Existing `App.tsx` was monolithic | Split into `AppShell`, `LiveMapPage`, `AnalyticsPage` and analytics components/hooks |
| 2 | Adding analytics to the same page would crowd the live map | Introduced explicit routes `/` and `/analytics` with navigation |
| 3 | Official report families can duplicate the same route/month | Service-layer de-duplication with family priority |
| 4 | School routes can dominate low-punctuality rankings | `S...` routes excluded by default with an explicit opt-in checkbox |
| 5 | JS percentage rounding produced 87.5% for 0.8755 | Formatting rounds via `Math.round(value * 1000) / 10` |
| 6 | Query string parameter ordering made tests brittle | Centralised ordering in `api/client.ts` and asserted concrete URLs |
| 7 | Native month inputs rendered Chinese labels on a Chinese Windows locale | Replaced with English `Year` / `Month` selects generated from official coverage |
| 8 | Scatter chart plotted dense route-month points | Backend now aggregates one point per route; API supports `min_boardings` and `limit`; labels only highest-ridership routes |
| 9 | Heatmap looked like analysis for its own sake | Moved into a collapsed `Seasonality detail` panel and explained as an optional seasonality diagnostic |
| 10 | Repeated explanation boxes caused explanation fatigue | Replaced with compact panel subtitles and a dedicated Methodology view |
| 11 | Top navigation would not scale to future modules | Replaced with a narrow left sidebar and disabled future-module placeholders |
| 12 | Most used and poor performing routes were mixed | Split Ridership and Performance views with opposite ranking semantics |
| 13 | Metric units and definitions were implicit | Added `/analytics/metrics`, `METRIC_CATALOG`, frontend `metricDefinitions.ts` and UI unit labels |
| 14 | Official route numbers did not match GTFS route IDs | Added a read-only route catalog and Methodology table |
| 15 | Correlation could imply causality without sample-size context | Spearman correlation only shown with `n >= 5`, labelled descriptive |
| 16 | Generic dashboard aesthetic did not fit a civic-data product | New warm off-white / charcoal / forest-green design tokens and five focused subviews |

## 6. Not verified

| Item | Reason |
| --- | --- |
| Real browser visual QA | Component and routing tests used jsdom; no visual screenshot check in this phase |
| Production hosting | AWS/serving setup remains Phase 7 |
| Live-map to analytics route handoff | Route context is shared across analytics views, not yet from the Live map |
| Hardening/load tests | Phase 6 scope |

## 7. Conclusion

Phase 5 reaches the MVP: the live map remains the landing page, analytics is a separate
product area with five focused subviews, backend aggregation is isolated in a service
layer, and the frontend is split into comprehensible, alterable and testable modules. The
professional redesign replaces the generic dashboard look with a civic-data identity,
separates ridership from operational performance, makes metric definitions and coverage
explicit, and adds interactive, keyboard-accessible chart details. All automated checks
pass and the endpoints were verified against real MySQL data. No commit or push was
performed.
