# Test Report: Phase 04 - Official Historical Reports

- **Date:** 2026-11-18
- **Result:** **PASS** — backend 114 passed / 1 skipped / 90% coverage, Ruff clean; frontend 46 passed from the previous phase still green; 13 official AT XLSX reports downloaded and imported into MySQL
- **Phase document:** `docs/phases/PHASE-04-official-historical-reports.md`

## 1. Environment

| Item | Value |
| --- | --- |
| OS | Windows (win32), `cmd` shell |
| Python | 3.12.7, `backend/.venv` |
| Node.js / npm | v24.14.0 / 11.9.0 |
| MySQL | Local 8.0.42, `transitpulse`, alembic `0004` |
| Report storage | `backend/data/reports/` (gitignored) |
| Git | Phase 3 is committed as `f2ad952`; Phase 4 changes remain uncommitted in the working tree |

## 2. Spike verification

The AT reports page was fetched and parsed for real hrefs. Key files confirmed:

```text
Monthly punctuality/reliability  XLSX  2023-07..2026-10
Bus performance                  XLSX  2019..2025-03
Bus boardings per service hour   XLSX  2023-07..2026-06
Monthly patronage                XLSX  2005-07..2025-06
```

Representative workbooks were downloaded and inspected with `openpyxl`:

```text
punctuality_2024_2025.xlsx
  sheets: Punctuality, Reliability
  real header row: Mode | Route No | Route Name | RPTP Level of Service | Area | month...
  values: ratios such as 0.8755

bus_performance_2024.xlsx
  sheets: Boardings, Boardings per service hour, Punctuality, Reliability,
          older "to Jun-23" sheets, Route changes
  real header row: Region | Number | Type | Route | Operator | Unit | ... | Number | month...

patronage_2005_2025.xlsx
  sheet: AT Web
  header row: Month-Year | Total | Bus Total | Busway | Bus other | Train | Ferry
```

## 3. Backend checks

```text
> .venv\Scripts\python.exe -m ruff check .
All checks passed!

> .venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
114 passed, 1 skipped, 1 warning in 45.82s
TOTAL 2006 stmts / 210 missed / 90% coverage
app\api\official.py            42      6    86%
app\models\reports.py          57      0   100%
app\reports\loader.py          91     21    77%
app\reports\parser.py         249     60    76%
app\reports\registry.py        13      0   100%
```

The skip is the opt-in MySQL integration test; the warning is the known Starlette
`TestClient` deprecation.

### Backend test coverage

| File | Coverage |
| --- | --- |
| `test_official_reports.py` | Synthetic AT workbooks, punctuality/reliability parsing, patronage parsing, bus-performance parsing, idempotent loader, forced reload, read-only API endpoints |

## 4. Real import

```text
> python -m app.cli.gtfs migrate
Migrations applied: head

> python -m app.cli.reports load
[
  {"source_key": "punctuality_2023_2024", "status": "unchanged", "rows": 12032, "issues": 0},
  {"source_key": "punctuality_2024_2025", "status": "unchanged", "rows": 12229, "issues": 0},
  {"source_key": "punctuality_2025_2026", "status": "unchanged", "rows": 12414, "issues": 0},
  {"source_key": "punctuality_2026_10",  "status": "unchanged", "rows": 4144,  "issues": 0},
  {"source_key": "bus_performance_2019_2020", "status": "unchanged", "rows": 18120, "issues": 0},
  {"source_key": "bus_performance_2020_2023", "status": "loaded",    "rows": 26204, "issues": 0},
  {"source_key": "bus_performance_2023",      "status": "loaded",    "rows": 13224, "issues": 0},
  {"source_key": "bus_performance_2024",      "status": "loaded",    "rows": 13149, "issues": 0},
  {"source_key": "bus_performance_2025_q1",   "status": "loaded",    "rows": 6610,  "issues": 0},
  {"source_key": "hourly_boardings_2023_2024", "status": "loaded", "rows": 2200, "issues": 0},
  {"source_key": "hourly_boardings_2024_2025", "status": "loaded", "rows": 2212, "issues": 0},
  {"source_key": "hourly_boardings_2025_2026", "status": "loaded", "rows": 2223, "issues": 0},
  {"source_key": "patronage_2005_2025", "status": "loaded", "rows": 1400, "issues": 0}
]
```

Final database counts:

```text
official_reports          13
official_route_metrics   124,761
official_network_metrics  1,400
official_import_issues        0

route metric families:
  punctuality_report       40,819
  bus_performance_report   77,307
  hourly_boardings_report   6,635
```

Example analytical query result — lowest bus punctuality by route over
`2024-07..2025-06` from the dedicated punctuality report:

```text
S036 St Marys Primary To Bayview                  0.0000
S046X St Josephs To Silverdale Express            0.0689
S062 Rangitoto College To Browns Bay Shops        0.0735
S220 Waiheke High School To Oneroa                0.0855
S027H Carmel College To Beach Haven               0.0907
```

These are mostly school services, which is why Phase 5 must expose service type and
allow filtering before publishing headline rankings.

Patronage samples:

```text
2005-07 bus patronage 3433.7 thousand
2015-07 bus patronage 5019.8 thousand
2025-06 bus patronage 5507.647 thousand
```

## 5. API verification against real MySQL

```text
GET /api/v1/official/status
  200 total=13

GET /api/v1/official/route-metrics?metric=punctuality&route_no=70
    &start_month=2024-07&end_month=2025-06&limit=3
  200 total=3
  sample: route 70, 2024-07, value 0.893675, family punctuality_report

GET /api/v1/official/network-metrics?metric=bus_patronage
    &start_month=2005-07&end_month=2005-09
  200 total=3
  sample: 2005-07 = 3433.7, 2005-08 = 4226.7
```

## 6. Issues found and resolved

| # | Issue | Resolution |
| --- | --- | --- |
| 1 | Official report page did not expose hrefs in `web_fetch` text output | Fetched raw HTML and extracted absolute `/media/...` XLSX links |
| 2 | Windows console could not print bullet characters in workbook notes | Spike scripts reconfigured stdout to UTF-8; removed after use |
| 3 | Old bus-performance workbook had duplicate route/month values | Added duplicate month-column filtering and loader-level deduplication |
| 4 | Old workbooks contained footer rows such as `entire network` and long explanatory text | Parser skips summary labels and limits text fields to schema lengths |
| 5 | Unique key initially too narrow for repeated route labels | Added `source_row` to the unique key in model and migration |
| 6 | New `OfficialReport` row was flushed before non-null fields were assigned | Assign all metadata before flush |

## 7. Not verified

| Item | Reason |
| --- | --- |
| Frontend analytics dashboard | Phase 5 scope |
| Route 64/65 PDF reviews | PDF parsing not in Phase 4 scope; XLSX families imported instead |
| `npm ci` on a clean runner | Still deferred to first CI run after user push |
| Self-hosted realtime observation collector | Deliberately removed from the MVP |

## 8. Conclusion

Phase 4 successfully replaces self-collected history with official AT historical reports.
Thirteen XLSX reports were downloaded, parsed and imported into normalized MySQL tables
with full source metadata. The read-only API and analytical queries work against real
data. No commit or push was performed.
