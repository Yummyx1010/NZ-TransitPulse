# PHASE-03: Passenger View (ETA and Service Alerts)

- **Status:** Complete (not committed)
- **Date:** 2026-11-17 (initially completed); 2026-11-18 (calendar + route-scope refinement)
- **Depends on:** PHASE-02 (Realtime ingestion)
- **Product scope:** buses only

## 1. Goal

Answer the passenger half of the product: "When is my bus coming, and is it delayed?"
This phase adds a stop-arrival board built from the static timetable plus live delays, a
delay status for each arrival, and a bus-only service alerts panel.

No historical storage, no reliability analytics, no AWS, and no new external API.

## 2. Features delivered

| # | Feature | Outcome |
| --- | --- | --- |
| F1 | `GET /api/v1/stops/{id}/arrivals` | Upcoming bus arrivals in a configurable window (`minutes`, `limit`, `route_id`) |
| F2 | Scheduled times | `stop_times.arrival_seconds` joined to `trips` and `routes`, filtered to `route_type=3` (bus) |
| F3 | Realtime predictions | Trip updates from the in-memory snapshot matched by `trip_id`; a matching `stop_time_update` overrides the trip-level delay; an absolute `arrival.time` is converted into a delay when AT omits `delay` |
| F4 | Delay status | `Early / On time / Delayed / Scheduled`, threshold configurable via `TP_ON_TIME_THRESHOLD_SECONDS` (default 60 s) |
| F4b | Service calendar filter | `calendar.txt` / `calendar_dates.txt` are imported and arrivals are filtered to trips operating on today's Auckland service date |
| F5 | Auckland time | `zoneinfo` + `tzdata` so NZST/NZDT is handled correctly on Windows; GTFS times past `24:00:00` preserved |
| F6 | Station aggregation | GTFS stations (`location_type=1`) have no `stop_times` rows of their own; child platforms are included automatically and listed in the response |
| F7 | Bus-only alerts | `/api/v1/realtime/alerts?mode=Bus` returns only alerts affecting bus routes plus network-wide alerts |
| F8 | React passenger board | Stop search, ETA list with route/headsign/minutes-away/delay badge, realtime source, explanatory note, service alerts column; refreshes every 30 s |
| F9 | Route scoping | The arrival board and stop search are scoped to the selected route by default; an explicit `Show all buses at this stop` button opts out |
| F10 | Pattern UX polish | `Route pattern` renamed to `Direction / branch`; low-frequency shapes grouped under `Short turns / branches`; trip counts labelled `scheduled trips` |
| F11 | Regression safety | Bus-only scope, live bus map, per-shape geometry, auto-fit and all earlier endpoints unchanged |

## 3. Implementation

| Area | Files |
| --- | --- |
| Backend config | `backend/app/core/config.py` (`on_time_threshold_seconds`), `backend/pyproject.toml` (`tzdata`) |
| Backend time | `backend/app/core/time.py` (service date, weekday column, absolute timestamp conversion) |
| Backend GTFS | `backend/app/gtfs/{parser,loader}.py`, `backend/migrations/versions/0003_service_calendars.py` |
| Backend models | `backend/app/models/gtfs.py` (`ServiceCalendar`, `ServiceCalendarDate`) |
| Backend API | `backend/app/api/arrivals.py`, `backend/app/api/realtime.py`, `backend/app/api/network.py`, `backend/app/main.py` |
| Backend schemas | `backend/app/schemas/arrivals.py` |
| Backend tests | `backend/tests/test_arrivals_api.py`, `backend/tests/test_realtime_api.py`, `backend/tests/test_gtfs_loader.py`, `backend/tests/test_network_api.py` |
| Frontend | `frontend/src/components/PassengerBoard.tsx`, `App.tsx`, `api/{types,client}.ts`, `lib/format.ts`, `index.css` |
| Frontend tests | `frontend/src/components/PassengerBoard.test.tsx`, `App.test.tsx`, `api/client.test.ts`, `lib/format.test.ts` |
| Docs | `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, this document, `docs/test-reports/PHASE-03.md` |

## 4. API contract

`GET /api/v1/stops/{stop_id}/arrivals?minutes=60&limit=20&route_id=...`

```json
{
  "stop_id": "1420-5a7bc8d2",
  "stop_name": "Britomart Place",
  "included_stop_ids": ["1420-5a7bc8d2"],
  "window_minutes": 60,
  "timezone": "Pacific/Auckland",
  "realtime_available": true,
  "total": 3,
  "items": [
    {
      "trip_id": "...",
      "route_id": "70-205",
      "route_short_name": "70",
      "headsign": "Britomart To Botany Via Panmure",
      "direction_id": 0,
      "scheduled_seconds": 70500,
      "scheduled_time": "19:35:00",
      "predicted_seconds": 70446,
      "predicted_time": "19:34:46",
      "delay_seconds": -54,
      "minutes_away": 1,
      "status": "On time",
      "source": "realtime"
    }
  ],
  "note": "Scheduled times come from GTFS stop_times, filtered by the service calendar for today (Pacific/Auckland). ... Service date: 20261118."
}
```

`total` is the number of arrivals returned (capped by `limit`). `source` is `realtime`
when a matching trip update exists, otherwise `schedule`.

## 5. Design decisions

1. **Static timetable as the base, realtime as an overlay** — even when a trip update has
   no stop-level prediction, the scheduled arrival is still useful. Realtime delays are
   applied only when a `trip_id` match exists.
2. **Only bus routes** — `Route.route_type == 3`, consistent with the bus-only product
   scope; rail and ferry trips never reach the passenger board.
3. **Station-to-platform aggregation** — discovered from real data: `Britomart`
   (`location_type=1`) has three child platforms and zero `stop_times` rows of its own.
   Searching the station without this would always show an empty board.
4. **Auckland time via `zoneinfo` + `tzdata`** — Windows has no system tz database;
   `tzdata` is now an explicit dependency. GTFS seconds are service-day relative, so
   times above `24:00:00` are preserved rather than wrapped.
5. **Service calendar is the source of truth for "runs today"** — `calendar.txt` provides
   weekly patterns and `calendar_dates.txt` provides added/removed exceptions. The ETA
   query applies both for the Auckland service date, so inactive service variants no
   longer create duplicate scheduled rows. If a feed has no calendar tables the legacy
   unfiltered behaviour remains and the response note says so.
6. **Delay thresholds are configurable** — `Early` / `Delayed` at ±60 s by default.
7. **Mode filter on alerts server-side** — the browser never receives rail/ferry alerts.
8. **Short-turn patterns grouped** — route 70 has 5 shapes; the three with 1–5 trips
   are separated so the main directions stay easy to find.

## 6. How reviewers can verify

```bat
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/api/v1/stops/1420-5a7bc8d2/arrivals?minutes=60` and
`http://localhost:8000/api/v1/realtime/alerts?mode=Bus`. Start the frontend
(`npm run dev -- --port 5174`), search `Britomart` in the passenger board and pick a
stop to see the ETA list.

## 7. Tests

Backend: Ruff clean, **109 passed / 1 skipped / 94% coverage**. Frontend: TypeScript
strict check clean, **46 tests passed**, production build exit 0. Live verification
against the real AT feed produced populated arrival boards and bus alerts with realtime
delay status; the map was additionally verified in a real Chromium browser. Details:
`docs/test-reports/PHASE-03.md`.

## 7.1 Post-completion bug fixes (2026-11-17)

Three defects were reported after the phase was implemented and were fixed before the
phase is committed:

1. **Every stop appeared to have no arrivals.** The board implicitly passed the currently
   selected `route_id` to `/stops/{id}/arrivals`. After selecting a route (for example
   11T), searching any stop queried only that route's buses at that stop, so unrelated
   stops returned `total=0`. Diagnosis with real data at 19:50 NZDT showed 42,998 bus
   `stop_times` rows in the 60-minute window and `total=5` for every sampled stop without
   a `route_id`, but `total=0` for all of them with an unrelated `route_id`. The first fix
   made route filtering an explicit default-off toggle. The 2026-11-18 refinement then
   made **the selected route the default scope** (because that is the product intent),
   while keeping an explicit `Show all buses at this stop` button so the filter is never
   hidden. The stop search is scoped the same way.
2. **The map jumped to an unrelated location when a route was clicked from the full
   list.** While route geometry was loading, `StopMap` fell back to using all live
   vehicle positions for `fitBounds` (framing the whole city), and an empty dataset
   unmounted `MapContainer` entirely, destroying and recreating the Leaflet instance.
   Bounds now come **only** from the selected shape (`lib/mapBounds.ts`); with no geometry
   the viewport is left untouched, and the map container stays mounted. Searching first
   happened to mask the race, which is why the bug appeared only when clicking from the
   unfiltered list.

3. **The line was still invisible when clicking from the unfiltered list (real root
   cause).** A browser inspection showed the geometry *was* rendered (27 SVG paths) but
   at y≈3031 inside a Leaflet container **6088 px tall**, while the viewport was 900 px.
   The unfiltered route list contains 100 routes and stretched `.layout` / `.explorer` /
   `.detail` to 6405 px; `fitBounds` then centred the line far outside the visible area.
   Searching first shortened the list and restored a normal height, which is exactly why
   only the unfiltered case failed. Fix: `.layout` now has a bounded height
   (`clamp(480px, 68vh, 720px)`), `.explorer` / `.route-list` / `.detail` have
   `min-height: 0` so the route list scrolls internally, and `.map` has a smaller
   `min-height`. Additional hardening in `FitBounds`: wait for a usable `map.getSize()`
   (retry up to 40 frames) and use a monotonic token so a pending fit from a previous
   route can never frame stale geometry.

Regression tests: `frontend/src/lib/mapBounds.test.ts`,
`frontend/src/components/StopMap.test.tsx` (mock Leaflet viewport calls, zero-size
container retry), `frontend/src/App.map.test.tsx` (clicking a route from the full list and
switching to a second one), and updated `PassengerBoard.test.tsx` cases for default-on /
toggle-off route filtering.

Real-browser verification (Chromium, 1440x900, `http://localhost:5174`):

```text
BEFORE FIX  map container 920x6088 | 27 paths drawn | SVG d starts at y=3031
AFTER FIX   map container 920x461  | layout height 612px
  unfiltered list -> 101 : 27/27 paths inside the visible map
  unfiltered list -> 112 : 29/29 paths inside the visible map
  search 11T -> click     : 34/34 paths inside the visible map
  console: 0 errors, 0 warnings
```

An API sweep of all 100 routes in the default list confirmed the backend was never at
fault: 100/100 returned geometry (204–533 points per shape), 0 non-200, 0 empty shapes.

### 7.2 Route-scope and service-calendar refinement (2026-11-18)

A reviewer reported that a stop search listed many near-duplicate scheduled rows
(11:04:57 and 11:04:58 for the same route/headsign) and almost every row said
`No live delay`. Root cause: `calendar.txt` / `calendar_dates.txt` had not been imported,
so the ETA query returned trips from every service variant in the GTFS bundle, including
services that do not operate today. Those trips naturally have no live trip update.

The calendars are **not** an external API; they were already inside the downloaded bundle
(`backend/data/gtfs/gtfs-8307d05c9a8b.zip`): `calendar.txt` (119 rows),
`calendar_dates.txt` (927 rows). This refinement:

- adds Alembic `0003` and two feed-keyed tables: `service_calendars`,
  `service_calendar_dates`;
- extends parser/loader to import both files with deduplication and validation;
- filters arrivals by today's Auckland service date (weekly flag + date range, minus
  `exception_type=2`, plus `exception_type=1`);
- matches stop-level predictions against every included platform of a parent station;
- derives a delay from absolute `arrival.time` when AT omits `arrival.delay`;
- makes the selected route the default ETA/stop-search scope, with an explicit opt-out
  button and a route-specific empty-state message;
- changes the no-prediction text from `No live delay` to `timetable only`;
- clears the stop search box after a stop is selected, so the suggestion dropdown closes.

Real-data verification on `1420-5a7bc8d2` (Britomart Place), route `70-205`, 180-minute
window, service date `20261118` (Wednesday):

```text
RAW stop_times rows in window:        54
ACTIVE trips after calendar filter:   18
API ETA: 11:10, 11:20, 11:30 ...      (clean 10-minute headway, no 1-second duplicates)
Route-scoped stop search:             1 stop (Britomart Place)
```

A live snapshot with 1,757 trip updates was also polled; for this stop/route AT provided
no matching stop prediction at that moment, so the rows correctly stayed `Scheduled`.
The absolute-time fallback is covered by a deterministic test.

## 8. Known limitations

- Calendars are imported and filtered, but times are service-day relative; arrivals after
  midnight on the previous service day are not yet mapped onto the current calendar day.
- `total` counts returned rows, not all rows in the time window.
- Times are service-day relative; arrivals after midnight on a previous service day are
  not mapped onto the current calendar day.
- The board is a single-stop view; multi-route trip planning is out of scope.
- Some AT trip updates carry only one `stop_time_update`, so stop-level predictions are
  not available for every arrival; trip-level delay is used instead.

## 9. Next phase

Phase 4 (official historical reports): import AT's published punctuality, reliability,
patronage and bus-performance workbooks into normalized MySQL tables. Service calendars
are already imported in Phase 3, and a self-hosted live observation collector is no
longer an MVP dependency. Phase 5 then produces the analytics dashboard (the MVP).

## 10. Commit

No commit or push was performed, as requested. All changes remain in the working tree.
