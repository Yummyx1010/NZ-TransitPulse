# PHASE-02: Realtime Ingestion and Live Vehicle Positions

- **Status:** Complete (not committed)
- **Date:** 2026-11-15
- **Depends on:** PHASE-01B (Route Geometry)
- **Scope change:** the live vehicle map, originally scheduled for Phase 3, was pulled
  forward into Phase 2 so the realtime feed is visible end-to-end immediately.

## 1. Goal

Poll Auckland Transport's GTFS-Realtime feed, decode Vehicle Positions / Trip Updates /
Service Alerts into a typed in-memory snapshot, expose them through read-only endpoints,
and draw **real** vehicle positions on the existing Leaflet map. No historical storage,
no fake vehicle markers, no mock live data.

## 2. Preconditions verified before implementation

- Subscription quota confirmed by the repository owner: **600 calls/minute up to
  35,000 calls/week**. The weekly cap is the binding constraint (≈3.47 calls/min).
- Polling the three separate feeds every 30 s would be 6 calls/min = 60,480/week and
  would exceed the quota.
- The **aggregated endpoint** `https://api.at.govt.nz/realtime/legacy` was probed and
  returns all three entity kinds in one response (1,547 vehicles + 1,455 trip updates +
  166 alerts in the probe). `realtime/legacy/` (trailing slash) behaves identically.
  `v2/gtfs/*`, `realtime/compat/*` and `realtime/legacy/realtime` return 404.
- Live payload quirks: `status/response/error` envelope, `incrementality: 0` (full
  snapshot), `stop_time_update` serialised as an object when it has one element,
  `active_period` entries with `null` endpoints, string-valued `bearing`, negative
  `delay`, `is_deleted` entities, and many vehicle entities with no `trip` descriptor.

## 3. Quota design

| Strategy | Calls/day | Calls/week | Share |
| --- | --- | --- | --- |
| Three separate feeds every 30 s | 8,640 | 60,480 | 173% (over quota) |
| **Aggregated feed every 30 s (chosen)** | **2,880** | **20,160** | **58%** |
| Aggregated feed every 60 s | 1,440 | 10,080 | 29% |

A rolling seven-day `CallBudget` reserves 10% of the quota for retries/manual checks,
and the poller halves its rate once 80% of the weekly budget is used. Retries use bounded
exponential backoff; permanent 4xx responses are not retried. Unit tests and CI use
recorded/synthetic payloads and never consume the live key.

## 4. Features delivered

| # | Feature | Outcome |
| --- | --- | --- |
| F1 | Configuration | `TP_AT_REALTIME_URL`, timeout, retries, weekly quota, auto-start flag |
| F2 | `ingestion/client.py` | `Ocp-Apim-Subscription-Key`, retries, backoff, rolling quota budget |
| F3 | `ingestion/decoder.py` | Tolerant decoder for the AT envelope and all field quirks above |
| F4 | `ingestion/snapshot.py` | Thread-safe single-snapshot store with route/bbox filtering and health |
| F5 | `ingestion/poller.py` | Daemon-thread 30 s poller owned by the FastAPI lifespan |
| F6 | Route enrichment | Vehicles missing `route_id` are matched to trip updates by `trip_id` |
| F7 | Realtime API | `/status`, `/vehicles`, `/trip-updates`, `/alerts` |
| F8 | Static join | `/vehicles` and `/trip-updates` add `route_short_name` / `mode` from MySQL, but degrade gracefully if MySQL is down |
| F9 | **Live vehicle map** | Orange vehicle markers with route labels, timestamps and a legend; optional toggle; route filtering |
| F10 | Realtime status bar | Feed timestamp in `Pacific/Auckland`, counts, quota usage, last error, explicit "not configured" message |
| F11 | Regression safety | Route search, per-shape geometry, approximate-route label and all Phase 1 endpoints unchanged |
| F12 | Bus-only view | `/realtime/vehicles?mode=Bus` filters out trains and ferries; the UI requests buses only and labels the bar "Live buses" |
| F13 | Bus glyph markers | Real vehicles are drawn as a small top-down bus SVG rotated to their reported bearing (15-degree buckets, cached icons) instead of coloured dots |
| F14 | Reliable auto-fit | `invalidateSize` + deferred `fitBounds`, larger padding and `maxZoom 13`; re-fits when route geometry or pattern changes, plus a manual `Fit to view` button |
| F15 | Pattern-scoped vehicles | Selecting a route pattern (for example the outbound shape) shows **only the buses running that pattern's trips**. `/realtime/vehicles?shape_id=...` resolves the shape to static `trips.trip_id` values and filters the live snapshot; the selector also shows `D0`/`D1` direction codes |

## 5. Implementation

| Area | Files |
| --- | --- |
| Config | `backend/app/core/config.py`, `.env.example` |
| Ingestion | `backend/app/ingestion/{__init__,models,decoder,client,snapshot,poller}.py` |
| API | `backend/app/api/realtime.py`, `backend/app/schemas/realtime.py`, `backend/app/main.py` |
| Frontend | `frontend/src/api/{types,client}.ts`, `components/StopMap.tsx`, `App.tsx`, `lib/format.ts`, `index.css` |
| Tests | `backend/tests/fixtures.py`, `test_config.py`, `test_realtime_*.py`, `frontend/src/App.test.tsx`, `api/client.test.ts`, `lib/format.test.ts` |
| Docs | `README.md`, `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md`, `docs/ROADMAP.md`, this document, `docs/test-reports/PHASE-02.md` |

## 6. API contract

```text
GET /api/v1/realtime/status
GET /api/v1/realtime/vehicles?route_id=&bbox=min_lat,min_lon,max_lat,max_lon&limit=
GET /api/v1/realtime/trip-updates?route_id=&limit=
GET /api/v1/realtime/alerts?route_id=&limit=
```

`/status` reports `configured`, `polling`, entity counts, `last_error`, `poll_seconds`,
`calls_last_7_days`, `weekly_quota`, `quota_remaining` and `source` — never the key.
`/vehicles` returns `vehicle_id`, coordinates, bearing, `route_id`, `route_short_name`,
`mode`, `trip_id` and the vehicle timestamp. Invalid `bbox` returns `400`.

## 7. Design decisions

1. **One aggregated call per cycle** — 58% quota usage at 30 s instead of 173%.
2. **Raw feeds never persisted** — frames expire in 30 s; Phase 4 will persist only
   derived observations. This also keeps the compliance surface small.
3. **In-process snapshot** — no Redis/broker needed for a single-instance local MVP;
   the store is abstracted so a shared cache can replace it later.
4. **Poller owned by lifespan** — clean shutdown, and `realtime_polling_enabled` ensures
   tests never start a live worker.
5. **Best-effort static join** — a MySQL outage must not hide live vehicles.
6. **Decoder tolerates, does not crash** — malformed entities are skipped and counted
   implicitly; one bad row never drops a whole 3,000-entity frame.
7. **No key in logs, responses or tests** — CI uses `httpx.MockTransport` and a synthetic
   payload; only the manual live smoke test used the real subscription.
8. **Mode filtering happens server-side** — the browser never downloads train/ferry
   positions it will not draw. Matching is case-insensitive against the static
   `route_type` label; vehicles with no known route are intentionally excluded because
   their mode cannot be confirmed.
9. **DivIcon bus glyphs with cached rotations** — recognisable at a glance, show heading,
   and avoid creating a unique Leaflet icon object per vehicle.
10. **Auto-fit belongs to the data, not the user** — bounds come from the selected shape's
   full geometry (or from all buses when no route is selected), measured after the
   container settles; a manual button remains as an escape hatch.
11. **Pattern selection scopes vehicles, not just the drawn line** — a shape is a set of
    trips (`trips.shape_id`), and live vehicles carry the matching `trip_id`. Filtering by
    `shape_id` prevents outbound and inbound buses from being mixed, matching the
    direction tabs in Baidu / Amap. If the static lookup is unavailable the filter is
    skipped rather than hiding every bus.

## 8. How reviewers can verify

```bat
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/api/v1/realtime/status` (expect `has_data: true` within
a few seconds) and `http://localhost:8000/api/v1/realtime/vehicles?route_id=70-205`.
Start the frontend with `npm run dev -- --port 5174` and open `http://localhost:5174` to
see orange vehicle markers over the real route geometry.

## 9. Tests

Backend: Ruff clean, **92 passed / 1 skipped / 95% coverage**. Frontend: TypeScript
strict check clean, **26 tests passed**, production build exit 0. Live verification
found 1,545 vehicles in the feed, of which **606 are buses** (20 rail, 9 ferry). On
route 70, 26 buses split into 16 on the D1 shape and 10 on the D0 shape, with no overlap.
Details: `docs/test-reports/PHASE-02.md`.

## 10. Known limitations

- Automated tests mock Leaflet, so the visual rendering of vehicle markers is verified
  manually rather than by screenshot tests.
- Vehicle markers are capped at 1,000 per request; a viewport-based `bbox` filter exists
  in the API but the UI does not yet send map bounds.
- Vehicles with no trip descriptor and no matching trip update remain unlabelled
  (`route_id: null`). This is upstream data, not a parsing failure; such vehicles are
  also intentionally excluded when a specific pattern is selected, because their
  direction cannot be confirmed.
- The snapshot is process-local; multiple uvicorn workers would each hold their own.
- ETAs, stop-level arrival boards and delay status remain Phase 3.

## 11. Next phase

Phase 3 builds the passenger view: stop/route pages, an ETA list derived from
`trip_updates.stop_updates` joined with the static schedule, delay status and a service
alerts panel. Realtime data is already available; no new external API is required.

## 12. Commit

No commit or push was performed. All changes remain in the working tree.
