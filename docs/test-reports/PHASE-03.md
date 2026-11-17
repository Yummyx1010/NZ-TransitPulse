# Test Report: Phase 03 - Passenger View

- **Date:** 2026-11-17 (initial); 2026-11-18 (calendar + route-scope refinement)
- **Result:** **PASS** — backend 109 passed / 1 skipped / 94% coverage, Ruff clean; frontend 46 passed, TypeScript strict check clean, production build exit 0; verified against the live AT feed, real MySQL timetable, imported service calendars and a real Chromium browser
- **Phase document:** `docs/phases/PHASE-03-passenger-view.md`

## 1. Environment

| Item | Value |
| --- | --- |
| OS | Windows (win32), `cmd` shell |
| Python | 3.12.7, `backend/.venv` (with `tzdata` for Windows zoneinfo) |
| Node.js / npm | v24.14.0 / 11.9.0 |
| MySQL | Local 8.0.42, `transitpulse`, active feed id=3 after the calendar reload, alembic `0003` |
| Git | `main` at `90d4ac7` (Phase 2 pushed); no new commit created |

## 2. Backend

```text
cd backend
.venv\Scripts\python.exe -m ruff check .
All checks passed!

.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
s....................................................................... [ 65%]
......................................                                   [100%]
TOTAL                       1512     85    94%
app\api\arrivals.py            83      4    95%
app\api\realtime.py            86      8    91%
app\core\time.py               30      7    77%
app\gtfs\loader.py            170     22    87%
app\schemas\arrivals.py        29      0   100%
109 passed, 1 skipped, 1 warning in 18.43s
```

The skip is the opt-in MySQL integration test; the warning is the known Starlette
`TestClient` deprecation.

### New / updated backend tests

| File | Coverage |
| --- | --- |
| `test_arrivals_api.py` | Bus-only filtering, ordering, ferry exclusion, trip-level delay, stop-level override, **absolute `arrival.time` fallback**, `Early`/`On time`/`Delayed` thresholds, route filter, window bounds, unknown stop 404, parent-station platform aggregation, **calendar weekday filter**, **exception type 2 removal**, **exception type 1 addition**, **child-platform prediction matching**, delay classifier, `25:10:00` formatting |
| `test_gtfs_loader.py` | Calendar/date parsing, deduplication, invalid-row skipping, row counts |
| `test_network_api.py` | Stop search scoped by `route_id` |
| `test_realtime_api.py` | Added bus-only service alert filtering (`mode=Bus` vs `mode=Rail`) |

## 3. Frontend

```text
> npx tsc --noEmit
TSC_OK

> npx vitest run
46 tests, 46 passed, 0 failed

> npm run build
vite v6.4.6 — 124 modules transformed
dist/index.html                   0.56 kB
dist/assets/index-B2HoJ4AU.css   23.92 kB
dist/assets/index-CRNRqwek.js   355.06 kB
built in 1.40s
```

New frontend tests: `PassengerBoard` stop search and selection, ETA rendering with delay
badges, **default route-scoped arrivals with explicit toggle**, route-scoped stop search,
route-specific empty-board message, bus-only alert query; URL construction for
`/stops?route_id=`, `/stops/{id}/arrivals` and `/realtime/alerts`; ETA/delay/status
formatting helpers including `timetable only`, and the regression that the stop suggestion
dropdown closes after selection. All Phase 1B and Phase 2 tests still pass.

## 4. Live verification against real data

Two findings drove fixes during verification:

1. `zoneinfo` on Windows could not resolve `Pacific/Auckland` → added `tzdata` to
   `backend/pyproject.toml`. `datetime.now(ZoneInfo("Pacific/Auckland"))` now returns
   `2026-11-17T18:34:35+13:00` (NZDT, correct for November).
2. The first live run returned **0 arrivals** for `Britomart`. Diagnosis:
   `11814-b1f9e8ce` is a GTFS station (`location_type=1`) with three child platforms and
   no `stop_times` rows of its own, while 151,817 bus `stop_times` rows existed in the
   current time window. The arrivals endpoint now aggregates child platforms.

Post-fix live run (19:34 NZDT):

```text
SAMPLE STOPS: Britomart (station), Customs St/Britomart, Britomart Queens Arcade,
              Britomart Place, Mangere Town Centre, Stop A Westfield Newmarket

ARRIVALS Britomart              200 total=5  27H 19:34:00 Scheduled (schedule)
ARRIVALS Customs St/Britomart   200 total=5  INN 19:37:59 -> 19:35:39 Early (realtime)
ARRIVALS Britomart Queens Arcade 200 total=5 INN 19:35:59 -> 19:26:02 Early (realtime)
ARRIVALS Britomart Place        200 total=5  70 19:35:00 1min Scheduled (schedule)
ARRIVALS Mangere Town Centre    200 total=5  38 19:34:59 1min Scheduled (schedule)
ARRIVALS Stop A Westfield Newmarket 200 total=5
                                  64 19:35:00 -> 19:34:46 1min On time (realtime)
BUS ALERTS (mode=Bus)          200 total=141
  Stops skipped: Route 313 - Robertson Road, Mangere
  Stops moved: Route 805 - Ngataringa Road, Devonport
AT CALLS THIS WEEK: 3 / 35000
```

`total=5` is the requested `limit=5`, not the full window count. Realtime status values
(`Early`, `On time`) and predicted times confirm the trip-update overlay works on
production data. Only a handful of AT API calls were consumed by the verification runs.

## 5. Not verified

| Item | Reason |
| --- | --- |
| Leaflet / passenger board rendering in a real browser | Automated tests cover behaviour with mocked APIs; visual check is manual |
| Service-calendar correctness | `calendar.txt` / `calendar_dates.txt` are not imported; the API states this limitation |
| Seven-day quota behaviour | Rolling budget and backoff are unit-tested, not exercised over a week |
| GitHub Actions | No push was made, as requested |

## 5.1 Post-completion defect verification (2026-11-17, 19:50 NZDT)

```text
GTFS bundle contains: calendar.txt (119 rows), calendar_dates.txt (927 rows)
BUS stop_times in current 60min window: 42,998
stop_times with time >= 24:00: 9,607

Britomart               plain 200 total=5  |  with unrelated route_id 200 total=0
Customs St/Britomart    plain 200 total=5  |  with unrelated route_id 200 total=0
Britomart Queens Arcade plain 200 total=5  |  with unrelated route_id 200 total=0
Britomart Place         plain 200 total=5  |  with unrelated route_id 200 total=0
```

This proves the "all stops empty" report was caused by the implicit `route_id` filter,
not by missing service calendars or by an empty timetable. After the fix the browser's
default request has no `route_id`.

Additional regression tests (8 new frontend cases):

| Test | Verifies |
| --- | --- |
| `mapBounds.test.ts` | Bounds come only from shape geometry; `null` / empty shape yields no fit |
| `StopMap.test.tsx` | With geometry loading, `fitBounds`/`setView` are never called; with a shape, `fitBounds` receives exactly the shape points; a zero-sized container retries until measurable |
| `App.map.test.tsx` | Clicking a route from the full list fits its shape; switching to a second route re-fits |
| `PassengerBoard.test.tsx` | Arrivals are unfiltered by default; `route_id` is sent only after the toggle is enabled |

Final verification after the fixes: backend `103 passed / 1 skipped / 95%`, frontend
`43 passed`, TypeScript strict check clean, `npm run build` exit 0 (124 modules).

## 5.2 Map layout defect and real-browser verification

The user reported that clicking a route from the unfiltered list still showed no line.
An API sweep proved the backend was healthy:

```text
BUS ROUTES IN DEFAULT LIST: 197 total, 100 returned
OK ROUTES: 100 | NON-200: 0 | EMPTY SHAPES: 0 | THIN POINTS: 0
sample: 101-202 2 shapes / 308 points, 111-203 1 shape / 513 points, ...
```

A real Chromium session (1440x900) then exposed the actual cause — the line was drawn
but positioned outside the viewport because the flex/grid layout was not height-bounded:

```text
BEFORE  .app 6935px | .layout 6405px | .explorer 6405px | .map 6088px
        paths=27, first SVG d = "M271 3031L271 3056..."  (viewport height 900)

AFTER   .layout 612px | .map 461px
        unfiltered -> 101 : 27/27 path bounding boxes inside the map rect
        unfiltered -> 112 : 29/29 path bounding boxes inside the map rect
        search 11T -> click: 34/34 path bounding boxes inside the map rect
        browser console: 0 errors, 0 warnings
```

The fix bounds `.layout` height, adds `min-height: 0` to `.explorer`, `.route-list` and
`.detail` (so the 100-item list scrolls internally), and reduces `.map` min-height.
`FitBounds` additionally waits for `map.getSize()` to be usable and uses a monotonic
token so a stale pending fit cannot frame the previous route.

## 5.3 Service-calendar import and route-scope verification (2026-11-18)

The reviewer reported many near-duplicate scheduled rows (`11:04:57` and `11:04:58` for the
same route/headsign) and almost every row showing `No live delay`. Because calendars were
not imported, the ETA query had been returning trips from every service variant in the
GTFS bundle.

```text
> python -m app.cli.gtfs migrate
Migrations applied: head

> python -m app.cli.gtfs load --file data\gtfs\gtfs-8307d05c9a8b.zip --force
counts: routes 218 | stops 6,993 | trips 32,949 | stop_times 987,373
        shape_points 532,630 | calendars 119 | calendar_dates 927
skipped: 0 / 0 / 0 / 0

Tables (10): agencies, alembic_version, gtfs_feeds, routes, service_calendar_dates,
             service_calendars, shape_points, stop_times, stops, trips
```

Service date `20261118` (Wednesday), stop `1420-5a7bc8d2`, route `70-205`, 180-minute
window:

```text
RAW stop_times rows in window:      54
ACTIVE trips after calendar filter: 18
API total (limit 8):                8
API ETA: 11:10, 11:20, 11:30, 11:40, 11:50, 12:00, 12:10, 12:20
Route-scoped stop search:           [('Britomart Place', '1420-5a7bc8d2')]
API note: "...filtered by the service calendar for today ... Service date: 20261118."
```

The 1-second duplicates disappeared and the headway became a clean 10 minutes. A live
poll in the same run returned 1,671 vehicles / 1,757 trip updates with `last_error=None`;
AT had no matching stop prediction for these scheduled trips at that moment, so the rows
correctly remained `Scheduled`. The absolute `arrival.time` fallback is covered by a
deterministic test rather than depending on a lucky live snapshot.

## 6. Conclusion

Phase 3 delivers a working bus ETA board by joining the static timetable in MySQL with
live delays from the in-memory realtime snapshot, with correct Auckland time handling,
parent-station aggregation, bus-only alerts and a clearer direction/branch selector.
All automated tests pass and the feature was verified against real AT data. No commit or
push was performed.
