# PHASE-04: Official Historical Reports

- **Status:** Complete (not committed)
- **Date:** 2026-11-18
- **Depends on:** Phase 1 (static GTFS and MySQL schema)
- **Product scope:** buses only in the UI; official rows are normalized with their mode

## 1. Goal

Provide multi-year historical context without asking the user to keep a local collector
running. Instead of persisting self-collected GTFS-Realtime observations, this phase
imports Auckland Transport's published XLSX reports into normalized MySQL tables.

The MVP can then answer questions such as:

- Which bus routes have the lowest official punctuality/reliability?
- How did a route perform across months and years?
- How did bus patronage change over time?
- How do patronage and performance relate?
- Which routes have high boardings per service hour?

## 2. Spike result

The official reports page was verified, and representative workbooks were downloaded and
inspected:

```text
Monthly punctuality/reliability:
  sheets: Punctuality, Reliability
  header row found by content, not fixed position
  columns: Mode, Route No, Route Name, RPTP Level of Service, Area, then monthly dates

Bus performance report:
  sheets: Boardings, Boardings per service hour, Punctuality, Reliability,
          older "to Jun-23" variants, Route changes
  route-level wide tables with monthly columns and explanatory rows

Monthly patronage:
  sheet: AT Web
  columns: Month-Year, Total, Bus Total, Busway, Bus other, Train, Ferry
  coverage: 2005-07 to 2025-06

Hourly bus boardings:
  sheet: Route
  actually reports weekday boardings per scheduled service hour by month
```

Conclusion: all four report families are usable. No proprietary conversion or external
data source is needed.

## 3. Features delivered

| # | Feature | Outcome |
| --- | --- | --- |
| F1 | Official report registry | 13 workbooks registered with source URL, checksum, period and import metadata |
| F2 | Resilient XLSX parser | Locates headers by content, tolerates notes, duplicate month columns and old/new month labels |
| F3 | Route metrics | 124,761 route-month rows: punctuality, reliability, boardings, boardings per service hour |
| F4 | Network metrics | 1,400 network-month patronage rows from 2005-2025 |
| F5 | Idempotent CLI | `python -m app.cli.reports load` downloads, parses, imports; unchanged checksums are skipped; `--force` and `--only` supported |
| F6 | Read-only API | `/api/v1/official/status`, `/route-metrics`, `/network-metrics` |
| F7 | Data quality | Tracks non-fatal parse issues; skips footer rows, duplicate months and invalid values |
| F8 | Compliance | Original XLSX files stay in gitignored `data/reports/`; normalized rows retain family, sheet, row and definition metadata |

## 4. Implementation

| Area | Files |
| --- | --- |
| Models | `backend/app/models/reports.py` |
| Migration | `backend/migrations/versions/0004_official_reports.py` |
| Parser | `backend/app/reports/parser.py`, `backend/app/reports/registry.py` |
| Loader | `backend/app/reports/loader.py` |
| CLI | `backend/app/cli/reports.py` |
| API | `backend/app/api/official.py`, `backend/app/main.py` |
| Config | `backend/app/core/config.py` (`report_data_dir`), `.env.example` |
| Tests | `backend/tests/test_official_reports.py` |
| Docs | This document, `docs/test-reports/PHASE-04.md`, `README.md`, `docs/DATABASE.md`, `docs/DATA_SOURCES.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md` |

## 5. Database tables

| Table | Purpose |
| --- | --- |
| `official_reports` | One imported workbook: source key, URL, checksum, period, row/issue counts |
| `official_route_metrics` | Route-level monthly metrics with route number/name, mode, region/area/operator, value and source row |
| `official_network_metrics` | Network-level monthly metrics, mainly patronage by mode |
| `official_import_issues` | Non-fatal parsing issues for auditability |

Unique keys include the source sheet and source row because older AT workbooks contain
repeated route labels and summary/footer rows.

## 6. CLI

```bat
cd backend
python -m app.cli.gtfs migrate
python -m app.cli.reports load
python -m app.cli.reports status
```

Options:

```bat
python -m app.cli.reports load --only punctuality_2024_2025
python -m app.cli.reports load --no-download --force
```

## 7. API contract

```text
GET /api/v1/official/status
GET /api/v1/official/route-metrics?metric=punctuality&route_no=70&start_month=2024-07&end_month=2025-06
GET /api/v1/official/network-metrics?metric=bus_patronage&start_month=2005-07&end_month=2025-06
```

Supported route metrics:

```text
punctuality
reliability
boardings
boardings_per_service_hour
```

Supported network metrics:

```text
total_patronage
bus_patronage
busway_patronage
bus_other_patronage
train_patronage
ferry_patronage
```

The API returns every source family. Some months exist in both the dedicated punctuality
reports and the bus performance reports; Phase 5 should either choose a preferred source
or display the source family so users do not silently double-count.

## 8. Imported data

```text
13 reports
124,761 route metric rows
  40,819 punctuality_report
  77,307 bus_performance_report
   6,635 hourly_boardings_report
1,400 network metric rows
0 reported import issues
```

Coverage:

```text
punctuality / reliability  2023-07 .. 2026-10
bus performance            2019 .. 2025-03
boardings per service hour 2023-07 .. 2026-06
network patronage          2005-07 .. 2025-06
```

## 9. Design decisions

1. **Official reports, not self-collection** — trusted multi-year data with no always-on
   local process and no extra realtime API usage.
2. **No raw workbook redistribution** — downloaded files remain local and gitignored;
   only normalized rows and source metadata are stored.
3. **Header detection by content** — AT workbooks place explanatory notes above headers;
   fixed row numbers would break between years.
4. **Source row in unique keys** — old reports contain repeated route labels and footer
   rows; preserving the source row allows auditability without crashing the loader.
5. **Mode retained** — official workbooks include train and ferry rows. They are stored
   but future UI queries default to bus-only.
6. **Official definitions stay explicit** — AT punctuality/reliability definitions differ
   from the Phase 3 ETA badge threshold and must not be mixed.
7. **Self-hosted observation collector deferred** — it remains an optional post-MVP
   enhancement for continuously deployed instances.

## 10. Known limitations

- Original XLSX formatting and colours are not preserved; only metric values are loaded.
- Route 64/65 PDF reviews are not parsed in this phase.
- Some school-service routes have near-zero official punctuality; Phase 5 must label
  service type and allow filtering so they do not distort headline rankings.
- Duplicate metric values can exist across report families for the same route/month;
  the source family must be shown or prioritised in the dashboard.
- Patronage and performance correlation is descriptive, not causal.

## 11. Next phase

Phase 5 builds the analytics MVP on top of these tables plus the static GTFS network:
punctuality ranking, trend charts, monthly heatmap, patronage vs performance, and
GTFS-derived network metrics. No new data source is required.

## 12. Commit

No commit or push was performed. All changes remain in the working tree.
