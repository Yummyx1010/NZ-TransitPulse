# Test Report: Phase 01B - Route Geometry Fix

- **Date:** 2026-11-15
- **Result:** **PASS** — backend 63 passed / 1 skipped / 94% coverage, Ruff clean; frontend 12 passed, TypeScript strict check clean, production build exit 0; real MySQL data and full-stack HTTP verified
- **Phase document:** `docs/phases/PHASE-01B-route-geometry.md`

## 1. Environment

| Item | Value |
| --- | --- |
| OS | Windows (win32), `cmd` shell |
| Python | 3.12.7, `backend/.venv` |
| Node.js / npm | v24.14.0 / 11.9.0 |
| MySQL | Local 8.0.42, `transitpulse` database, real AT GTFS feed |
| Git | `main` at `9062c53` + tag `phase-01` (no new commit created) |

## 2. Cause verification (before the fix)

```text
shapes.txt in gtfs-8307d05c9a8b.zip: YES, 26,817,642 bytes, 532,630 rows, 609 shapes
trips with shape_id: 32,949 / 32,949
tables before fix: agencies, alembic_version, gtfs_feeds, routes, stop_times, stops, trips
route 70 (70-205): 590 trips, 5 distinct shape_id, 83 distinct stops
route_stops ordering: ORDER BY Stop.name (alphabetical)
StopMap: one <Polyline> built from that alphabetically sorted array
```

## 3. Backend

```text
cd backend
.venv\Scripts\python.exe -m ruff check .
All checks passed!

.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
63 passed, 1 skipped, 1 warning in 9.18s
TOTAL 740 stmts / 47 missed / 94% coverage
```

The single skip is the opt-in MySQL integration test, which was separately executed
successfully in Phase 1. The warning is the known Starlette `TestClient` deprecation.

### New backend tests (`backend/tests/test_geometry_api.py`)

| Test | Verifies |
| --- | --- |
| `test_geometry_groups_shapes_by_route` | R1 returns exactly SH1 + SH4, `source=shapes`, `approximate=false` |
| `test_unrelated_shapes_are_not_combined_into_one_line` | SH1 has 3 points, SH4 has 2 points — no merged 5-point line |
| `test_shape_points_follow_gtfs_sequence_order` | Points return in `shape_pt_sequence` order even though the fixture lists them out of order |
| `test_stops_follow_stop_sequence_not_alphabetical_order` | SH1 stops are `[S2, S1]`, SH4 are `[S1, S2]`; alphabetical would be `[S1, S2]` |
| `test_geometry_does_not_include_other_routes` | R1/R2/R3 expose only their own shape ids |
| `test_unknown_route_geometry_returns_404` | Error contract |
| `test_geometry_without_active_feed_returns_404` | Empty-database behaviour |
| `test_fallback_uses_stop_times_when_shapes_are_missing` | `source=stop_times`, `approximate=true`, grouped patterns, points from ordered stops |

Additional loader tests: shape sequence/association, invalid and duplicate shape point
skipping, and loading a bundle without `shapes.txt`. Migration drift and reversibility
tests now also cover `shape_points` and `gtfs_feeds.shape_point_count`.

## 4. Migration and real data import

```text
> python -m app.cli.gtfs migrate
Migrations applied: head

> python -m app.cli.gtfs check-db
Connected to MySQL: 8.0.42
Tables (8): agencies, alembic_version, gtfs_feeds, routes, shape_points, stop_times, stops, trips

> python -m app.cli.gtfs load --file data\gtfs\gtfs-8307d05c9a8b.zip --force
{
  "status": "loaded",
  "feed_id": 2,
  "counts": {
    "agencies": 17, "routes": 218, "stops": 6993, "trips": 32949,
    "stop_times": 987373, "shape_points": 532630
  },
  "skipped_stops": 0,
  "skipped_shapes": 0
}
```

## 5. Live geometry verification (real MySQL)

```text
70-205: 200 source=shapes shapes=5 approximate=False (0.404s)
  1153-07006-7290bbd3  trips=292 points=847 stops=41
  1153-07005-24cdecf9  trips=291 points=879 stops=43
  1153-07009-1939c415  trips=  5 points=604 stops=31
  1153-07007-4000b202  trips=  1 points=428 stops=22
  1153-07008-858e8ec1  trips=  1 points=271 stops= 9
  ordered first stops: ['Britomart Place', 'Anzac Avenue/Beach Road',
                        'Stop A Waterloo Quadrant', ...]
  alphabetical:       ['Anzac Avenue/Beach Road', 'Britomart Place',
                        'Stop A Waterloo Quadrant', ...]

70H-205: 200 source=shapes shapes=1 approximate=False (0.177s)
search '70': 3 routes (170, 70, 70H)
legacy /api/v1/routes/70-205/stops: 83 stops (unchanged)
```

Before the JOIN optimisation the same `70-205` request took **4.216 s**; replacing
`StopTime.trip_id.in_(subquery)` with a `JOIN` on `trips` reduced it to **0.404 s**.

## 6. Frontend

```text
> npx tsc --noEmit
TSC_OK

> npx vitest run
12 tests, 12 passed, 0 failed

> npm run build
vite v6.4.6 — 121 modules transformed
dist/index.html                   0.56 kB
dist/assets/index-C0A-vgLW.css   19.69 kB
dist/assets/index-CLpuoTWa.js   345.82 kB
built in 1.30s
```

New/updated frontend tests: default shape drawing for the selected route, ordered stop
list, shape switching without mixing patterns, the `Approximate route` label, route
search, and the geometry request URL encoding.

## 7. Full-stack HTTP smoke test

Both processes were started, exercised and then stopped (ports 8000 and 5174 released):

```text
READY backend: True | frontend: True
GET :8000/api/v1/routes/70-205/geometry  200 source=shapes shapes=5 approximate=False
  first shape: 1153-07006-7290bbd3 points=847 stops=41
GET :5174 proxy geometry                 200 shapes=5
GET :5174/                               200 NZ TransitPulse title: True
GET :8000/api/v1/routes?q=70             200 total=3
Both processes stopped.
```

## 8. Not verified

| Item | Reason |
| --- | --- |
| Leaflet SVG rendering in a real browser | Automated tests mock the map component because jsdom has no layout engine; verified manually by opening `http://localhost:5174` |
| GitHub Actions | No push was made, as requested |
| `stop_times` fallback against the real AT feed | `shapes.txt` is present in the real bundle; the fallback is covered by synthetic-fixture tests |

## 9. Conclusion

The crossing lines were caused by merging all trips' stops and sorting them
alphabetically before drawing a single polyline. The fix imports real GTFS shape
geometry, groups trips by `shape_id`, keeps stops in scheduled order, isolates the
selected route, and labels the `stop_times` fallback as approximate. All automated tests
pass and the complete chain was verified against the real 532,630-point AT dataset.
No commit or push was performed.
