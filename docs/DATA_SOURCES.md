# Data Sources and Compliance

Verified against Auckland Transport (AT) public documentation on 2026-11-14 and live
API responses on 2026-11-15. Re-check these pages before enabling the historical
collector in Phase 4.

## Sources

| Source | Used for | Format | Access |
| --- | --- | --- | --- |
| AT GTFS static bundle (`agency`, `routes`, `stops`, `trips`, `stop_times`, `shapes`; plus `calendar` and others) | Phase 1 network explorer and route geometry, schedule baseline for delay calculations | GTFS zip (CSV) | Public download, no key required |
| AT aggregated GTFS-Realtime (`realtime/legacy`) | Phase 2: vehicles, trip updates and alerts in one call | GTFS-RT JSON, wrapped in `status/response` envelope | Developer portal subscription key |
| AT GTFS-Realtime: Vehicle Positions | Live positions on the map; separate endpoint kept as optional fallback | GTFS-RT JSON by default, protobuf on request | Developer portal subscription key |
| AT GTFS-Realtime: Trip Updates | Phase 3 ETAs, Phase 4/5 delay observations | GTFS-RT JSON by default, protobuf on request | Developer portal subscription key |
| AT GTFS-Realtime: Service Alerts | Phase 3 disruption panel | GTFS-RT JSON by default, protobuf on request | Developer portal subscription key |

### References

- AT data sources (licence overview): <https://at.govt.nz/about-us/at-data-sources>
- AT GTFS static download and specification page:
  <https://at.govt.nz/bus-train-ferry/more-services/google-transit-feed>
- Official GTFS bundle URL used by the loader (confirmed via the Mobility Database
  producer URL and Transitland feed registry): <https://gtfs.at.govt.nz/gtfs.zip>
- AT developer portal: <https://dev-portal.at.govt.nz>
- Getting started with the Realtime API: <https://pp-dev-portal.at.govt.nz/realtime-api>
- API terms of use: <https://pp-dev-portal.at.govt.nz/api-terms-of-use>

## Verified technical facts

- AT open data is published under **Creative Commons Attribution 4.0 International
  (CC BY 4.0)**. Attribution to Auckland Transport is required in the UI, README and API
  metadata.
- The developer portal is a separate service governed by its own **API conditions of
  use**. Registration yields a subscription key sent as the
  `Ocp-Apim-Subscription-Key` header (or query parameter).
- The realtime API returns **JSON by default**; protobuf is available by setting
  `Accept: application/x-protobuf`. JSON is the MVP default to keep the parser simple.
- The feed is refreshed **at least every 30 seconds** and returns **full snapshots**,
  not incremental/differential updates. Polling faster than 30 seconds wastes quota;
  the configuration enforces a 30-second minimum.
- Trip updates provide `trip`, `vehicle`, `timestamp` and `stop_time_update` with
  `stop_sequence`, `stop_id`, and arrival/departure `delay` and `time`. Delay values may
  be negative (early running), especially for buses.
- Vehicle positions provide `trip`, `vehicle`, `position` (latitude, longitude, optional
  bearing) and `timestamp`; `speed` and `odometer` are not provided. Vehicle IDs are
  opaque and must not be used to infer routes.
- Service alerts may contain `null` values inside `active_period` where the GTFS-RT
  specification expects omitted fields. Parsers must tolerate this.
- The subscription quota is **600 calls/minute up to a maximum of 35,000 calls/week**
  (confirmed in the AT developer portal). The weekly cap is the binding constraint:
  35,000/week = 5,000/day ≈ 3.47 calls/minute. Polling all three separate feeds every
  30 seconds would be 6 calls/min (60,480/week) and would exceed it.
- The **aggregated endpoint** `https://api.at.govt.nz/realtime/legacy` (verified
  2026-11-15) returns Vehicle Positions, Trip Updates and Service Alerts in one
  response (~3,168 entities). Phase 2 polls it once every 30 seconds: 2,880 calls/day
  = 20,160/week (58% of the quota). A rolling seven-day call counter reserves 10% of
  the budget for retries and halves the polling rate once 80% has been used.
- The three separate legacy endpoints (`.../vehiclelocations`, `.../tripupdates`,
  `.../servicealerts`) remain as an optional per-feed fallback. The `v2/gtfs/*` and
  "Realtime Compat" paths returned 404 for this subscription.
- AT wraps the standard GTFS-RT message in
  `{"status": "OK", "response": {"header", "entity"}, "error": null}` with
  `header.incrementality = 0` (full snapshot). Repeated fields with a single element
  (for example `stop_time_update`) are serialised as an object instead of an array;
  `active_period` entries may contain `null` `start`/`end`; `bearing` may be a string;
  many vehicle entities have no `trip` descriptor. The decoder tolerates all of these.
- Confirm the paths attached to your own subscription and configure them with
  `TP_AT_REALTIME_URL` (aggregated) or the optional `TP_AT_*_URL` values; do not
  hard-code subscription-specific paths in source code.

## Compliance decisions for "permitted historical observations"

1. The subscription key lives only in `.env` (server-side) and is never exposed to the
   browser, committed, logged, or included in test fixtures.
2. Historical collection stores **derived observations** (trip, route, stop, scheduled
   time, predicted time, delay, observation timestamp, feed timestamp), not raw feed
   dumps. This keeps storage small and avoids redistributing the upstream feed.
3. A documented retention window is implemented in Phase 4 (default: 90 days of raw
   observations, longer-lived daily aggregates). Retention is configurable.
4. Aggregates displayed publicly are computed values, with the AT attribution visible
   on every dashboard page.
5. Before the Phase 4 collector is enabled, the current API terms of use must be read
   in full and the outcome recorded in `docs/phases/PHASE-04-*.md`. If the terms
   restrict retention or derived storage, the collector stays disabled and the
   analytics phase uses only locally generated sample data.
6. No personal data is collected. Vehicle identifiers are operational, not personal,
   and are treated as opaque strings.
7. The project states it is an independent project and is not affiliated with or
   endorsed by Auckland Transport.

## Time handling

- Store all timestamps in **UTC** in MySQL.
- Render all user-facing times in `Pacific/Auckland` (NZST/NZDT), including daylight
  saving transitions.
- GTFS static times can exceed `24:00:00` for services after midnight; the loader must
  resolve them against a service date rather than a wall-clock date.
