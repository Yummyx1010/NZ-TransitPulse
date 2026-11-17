# Test Report: Phase 02 - Realtime Ingestion and Live Vehicle Positions

- **Date:** 2026-11-15
- **Result:** **PASS** — backend 92 passed / 1 skipped / 95% coverage, Ruff clean; frontend 26 passed, TypeScript strict check clean, production build exit 0; live AT feed, bus-only filtering, direction-scoped vehicles and full-stack HTTP verified
- **Phase document:** `docs/phases/PHASE-02-realtime-ingestion.md`

## 1. Environment

| Item | Value |
| --- | --- |
| OS | Windows (win32), `cmd` shell |
| Python | 3.12.7, `backend/.venv` |
| Node.js / npm | v24.14.0 / 11.9.0 |
| MySQL | Local 8.0.42 with real AT GTFS feed (feed_id=2) |
| AT subscription | 600 calls/minute, 35,000 calls/week (owner-confirmed) |
| Git | `main` at `69dd963` (Phase 1B); no new commit created |

## 2. Endpoint and quota probe (before implementation)

```text
https://api.at.govt.nz/realtime/legacy/  -> 200, 1,387,697 bytes
https://api.at.govt.nz/realtime/legacy   -> 200, 1,387,735 bytes
  envelope: {status: OK, response: {header, entity}, error: null}
  header: {timestamp, gtfs_realtime_version: 1.0, incrementality: 0}
  entity kinds: trip_update 1455 | vehicle 1547 | alert 166 | total 3168
  sample vehicle: position{latitude, longitude, bearing:"286", speed} + vehicle{id}
  sample trip_update: trip{trip_id, route_id, start_date, ...}, delay, stop_time_update
  sample alert: active_period[{start, end}], header_text.translation[]

404 for: realtime/legacy/realtime, realtime/legacy/all, realtime/compat/*,
         realtime/compat/realtime, v2/gtfs/realtime
```

Quota arithmetic: three feeds × every 30 s = 60,480 calls/week (over quota); one
aggregated call × every 30 s = 20,160 calls/week (58%). The aggregated endpoint was
chosen.

## 3. Backend

```text
cd backend
.venv\Scripts\python.exe -m ruff check .
All checks passed!

.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
92 passed, 1 skipped, 1 warning in 23.50s
TOTAL 1283 stmts / 69 missed / 95% coverage
app\ingestion\client.py    97%
app\ingestion\decoder.py   92%
app\ingestion\poller.py    98%
app\ingestion\snapshot.py 100%
app\api\realtime.py        90%
```

The single skip is the opt-in MySQL integration test; the warning is the known
Starlette `TestClient` deprecation.

### New backend tests

| File | Coverage |
| --- | --- |
| `test_realtime_decoder.py` | Three entity kinds, string bearing, `is_deleted`, object/array `stop_time_update`, negative delay, null `active_period` end, route_id enrichment, invalid envelope, malformed entity skipping |
| `test_realtime_client.py` | Subscription-key header, one recorded call, 5xx retry with backoff, no retry on 401, missing credentials, quota exhaustion, network error wrapping |
| `test_realtime_snapshot.py` | Health counters, route/bbox/limit filters, successful/failed poller cycles, clean start/stop |
| `test_realtime_api.py` | Status/quota fields, static route label join, route and bbox filters, **bus-only mode filtering (case-insensitive)**, **shape-scoped vehicles (`SH1` vs `SH2` vs unknown shape, plus mode+shape combination)**, invalid bbox 400, negative delay, alerts with null periods, empty snapshot |
| `test_config.py` | Updated for the aggregated URL, polling switch and positive weekly quota |

## 4. Frontend

```text
> npx tsc --noEmit
TSC_OK

> npx vitest run
26 tests, 26 passed, 0 failed

> npm run build
vite v6.4.6 — 122 modules transformed
dist/index.html                   0.56 kB
dist/assets/index-C2RVya2n.css   21.32 kB
dist/assets/index-0-iGc_gQ.js   350.56 kB
built in 1.37s
```

New frontend tests: bus SVG glyph markup, 15-degree bearing buckets and icon caching,
bus-only request parameters, **shape-scoped vehicle requests and re-filtering when the
pattern changes**, **stop_times fallback not sending a fake shape id**, "Live buses"
status copy, hide-buses toggle, auto-fit on route selection and the manual `Fit to view`
control, plus the earlier realtime URL and Auckland-time formatting tests. All 1B tests
(shape grouping, stop ordering, approximate label, search) still pass.

## 5. Live full-stack verification

Backend (with the real subscription key, poller enabled) and Vite were started,
exercised, then stopped:

```text
READY backend: True | frontend: True

REALTIME STATUS 200 configured True polling True
  vehicles 1543 | trip_updates 1457 | alerts 165
  calls 1 / 35000 | last_error None

vehicles             200 total=1543 returned=5
  sample: {vehicle_id: 538070349, lat: -36.8396, lon: 174.75284,
           bearing: 286.0, route_id: None, ...}
route 70 vehicles    200 total=16 returned=5
  sample: {vehicle_id: 24605, route_id: '70-205', route_short_name: '70',
           mode: 'Bus', trip_id: '1153-07006-52800-2-d8771538', ...}
trip updates         200 total=1457 returned=3
alerts               200 total=165 returned=3
VITE PROXY realtime status 200 has_data True
VITE PAGE            200 NZ TransitPulse title: True
Both processes stopped.
```

The first verification consumed a single AT API call; the later bus-filter check used
only a handful more. Unlabelled vehicles are expected upstream behaviour: they have no
trip descriptor and no matching trip update.

A second live run verified the bus-only filter against the same feed:

```text
ALL VEHICLES IN FEED: 1545
BUS-ONLY:   606  (modes: {'Bus': 606})
RAIL-ONLY:  20
FERRY-ONLY: 9
ROUTE 70 BUSES: 16
  sample: {vehicle_id: 24605, route_id: '70-205', route_short_name: '70',
           mode: 'Bus', bearing: 106.0, speed: 52.0, ...}
```

606 buses exceeds the original 600-item request cap, so the UI cap was raised to 1,000.

A third live run verified that outbound and inbound buses are no longer mixed when a
route pattern is selected (26 of 26 route-70 vehicle `trip_id` values matched the static
`trips` table):

```text
ALL ROUTE 70 BUSES (no shape filter): 26
PATTERNS: 5
  D1 1153-07006-7290bbd3  trips=292 vehicles=16  Britomart To Botany Via
  D0 1153-07005-24cdecf9  trips=291 vehicles=10  Botany To Britomart Via
  D0 1153-07009-1939c415  trips=  5 vehicles= 0  Panmure To Britomart Via
  D0 1153-07007-4000b202  trips=  1 vehicles= 0  Ellerslie To Britomart
  D1 1153-07008-858e8ec1  trips=  1 vehicles= 0  Panmure To Botany
SUM OF PATTERN-SCOPED BUSES: 26  (= all route 70 buses, no overlap)
```

## 6. Not verified

| Item | Reason |
| --- | --- |
| Leaflet SVG marker rendering in a real browser | Automated tests mock the map component; verified manually by opening the dashboard |
| Long-running multi-hour quota behaviour | The rolling budget and backoff are unit-tested but not exercised for seven days |
| Multi-worker deployment | Snapshot is process-local by design for the single-instance MVP |
| GitHub Actions | No push was made |

## 7. Conclusion

Phase 2 delivers real Auckland Transport **bus** positions on the map as recognisable,
heading-aware bus glyphs, using a single aggregated feed call every 30 seconds that stays
comfortably inside the confirmed weekly quota. Trains and ferries are filtered out, the
map re-fits itself whenever a route or pattern is selected, and selecting an
outbound/inbound pattern now shows only that pattern's buses. Decoder tolerance,
retry/backoff, quota protection, static joins, bus filtering, direction scoping, icon
generation and auto-fit are all covered by automated tests, and the live feed was
verified end-to-end against production data. No commit or push was performed.
