# PHASE-01B: Route Geometry Fix

- **Status:** Complete (not committed)
- **Date:** 2026-11-15
- **Depends on:** PHASE-01 (Static Network Explorer)
- **Scope:** Fix the crossing blue lines on the selected route's map. No realtime API
  integration, no fake vehicle markers, no mock live data.

## 1. Problem and root cause

Selecting a route drew many blue lines criss-crossing the map. Two defects combined:

1. `GET /api/v1/routes/{route_id}/stops` merged `DISTINCT` stop ids from **every trip**
   of the route and sorted them with `ORDER BY Stop.name` (alphabetical). Travel order,
   direction and branch information were discarded.
2. `frontend/src/components/StopMap.tsx` fed that alphabetically sorted array into a
   **single** `<Polyline>`, connecting unrelated stops with straight lines.

Real data evidence for route 70 (`70-205`): 590 trips, **5 distinct `shape_id` values**
and 83 distinct stops, including different stop ids with the same name. Sorting those
83 stops by name and joining them with one line is guaranteed to cut across the city.

`shapes.txt` was present in the bundle all along (26.8 MB, 532,630 rows, 609 shapes) and
all 32,949 trips carry a `shape_id`, but Phase 1 deliberately deferred `shapes.txt`, so
no geometry table existed. Task 2/3 of this fix therefore applies: import real shapes
and draw them per shape.

## 2. Features delivered

| # | Feature | Outcome |
| --- | --- | --- |
| F1 | Import `shapes.txt` into a new `shape_points` table | 532,630 ordered points available in MySQL |
| F2 | `GET /routes/{id}/geometry` | Returns one geometry object per distinct `shape_id`, with ordered points and ordered stops |
| F3 | Route -> trip -> shape association | Trips are grouped by their own `shape_id`; unrelated directions/branches are never merged |
| F4 | `stop_times` fallback | When `shapes.txt` is missing, trips are grouped by exact ordered stop sequence and the response is marked `approximate` with an explicit UI label |
| F5 | Route 70 isolation | Only the selected route's shapes and that pattern's stops are drawn; a `Route pattern` selector switches direction/branch |
| F6 | Better zoom and bounds | `fitBounds` uses all shape points with padding and a `maxZoom`, with single-point and empty fallbacks |
| F7 | Regression safety | Route search, mode filter, `/stops`, `/routes/{id}/stops` and all Phase 1 endpoints still work |
| F8 | Tests | Backend tests for shape associations, point ordering, stop ordering, route isolation and fallback; frontend tests for shape selection, ordered stops and the approximate label |

## 3. Implementation

| Area | Files |
| --- | --- |
| Model | `backend/app/models/gtfs.py`, `backend/app/models/__init__.py` (`ShapePoint`, `GtfsFeed.shape_point_count`) |
| Migration | `backend/migrations/versions/0002_route_shape_points.py`, `backend/migrations/env.py` (SQLite batch mode for reversible `drop_column`) |
| Parser | `backend/app/gtfs/parser.py` (`OPTIONAL_FILES`, `SHAPE_COLUMNS`, `parse_float`) |
| Loader | `backend/app/gtfs/loader.py` (`_shape_rows`, batched insert, counts, skipped-row reporting) |
| API | `backend/app/api/network.py`, `backend/app/schemas/network.py` (`ShapeGeometry`, `RouteGeometry`) |
| Frontend | `frontend/src/api/types.ts`, `client.ts`, `components/StopMap.tsx`, `App.tsx`, `index.css` |
| Tests | `backend/tests/fixtures.py`, `test_gtfs_loader.py`, `test_geometry_api.py`, `frontend/src/App.test.tsx`, `frontend/src/api/client.test.ts` |
| Docs | `README.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, this document, `docs/test-reports/PHASE-01B.md` |

## 4. API contract

`GET /api/v1/routes/{route_id}/geometry`

```json
{
  "route_id": "70-205",
  "source": "shapes",
  "approximate": false,
  "note": "Route geometry from GTFS shapes.txt (actual road geometry). ...",
  "shape_count": 5,
  "shapes": [
    {
      "shape_id": "1153-07006-7290bbd3",
      "label": "... · 292 trips",
      "trip_count": 292,
      "direction_id": 0,
      "headsign": "...",
      "points": [[-36.8454, 174.77], "..."],
      "stops": [{ "stop_id": "...", "name": "...", "lat": 0, "lon": 0, "...": "..." }]
    }
  ]
}
```

With no `shapes.txt`: `source` is `stop_times`, `approximate` is `true`, `shape_id`
becomes `stop-times-N`, `points` are stop coordinates, and `note` states that the lines
are not road geometry. Unknown routes still return `404`.

## 5. Design decisions

1. **Composite primary key on `shape_points`** — `(feed_id, shape_id, shape_pt_sequence)`
   both de-duplicates points and provides the ordered lookup path.
2. **One polyline per shape, selected explicitly** — the UI draws only the active shape
   by default (the one used by most trips), so a route with 5 patterns does not overlay
   five lines at once. The selector keeps the other patterns reachable.
3. **Stop order from `min(stop_sequence)`** — distinct stops of a shape's trips are
   ordered by their first scheduled appearance, not by name.
4. **JOIN instead of `IN (subquery)`** — joining `trips` keeps the query on indexed
   paths. Route 70 geometry fell from 4.216 s to 0.404 s.
5. **Fallback groups identical stop sequences** — 590 trips collapse into a few
   patterns instead of hundreds of duplicate lines.
6. **Fallback is labelled**, because connecting stops is not road geometry.
7. **Phase 1 endpoints untouched** — `route_stops` and `stops` remain available for
   other consumers; only the map switched to the geometry endpoint.

## 6. How reviewers can verify

```bat
cd backend
.venv\Scripts\activate
python -m app.cli.gtfs migrate
python -m app.cli.gtfs load --file data\gtfs\gtfs-<hash>.zip --force
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/api/v1/routes/70-205/geometry` and confirm
`shape_count: 5`, `source: "shapes"` and five independent `points` arrays. Then open
`http://localhost:5174`, search `70`, and switch the `Route pattern` selector.

## 7. Tests

Backend: Ruff clean, **63 passed / 1 skipped / 94% coverage**. Frontend: TypeScript
strict check clean, **12 tests passed**, production build exit 0. Full commands, outputs
and real-data timings are in `docs/test-reports/PHASE-01B.md`.

## 8. Known limitations

- Automated tests mock Leaflet, so the final visual rendering in a real browser is
  verified manually rather than by an automated screenshot test.
- `shape_points` adds 532,630 rows; the geometry response for a route with many long
  shapes can be a few hundred KB. A simplification/tile step can be added later.
- The `stop_times` fallback still draws straight segments between stops; it is
  intentionally labelled approximate.
- `calendar`, `calendar_dates` and `transfers` remain deferred.

## 9. Next phase

Phase 2 (Auckland Transport GTFS-Realtime ingestion) is unchanged. Its client can now
rely on the static `shape_id`/`route_id` associations established here.

## 10. Commit

No commit or push was performed, as requested. All changes remain in the working tree.
