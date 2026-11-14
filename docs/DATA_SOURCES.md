# Data Sources and Compliance

Verified against Auckland Transport (AT) public documentation on 2026-11-14.
Re-check these pages before enabling the historical collector in Phase 4.

## Sources

| Source | Used for | Format | Access |
| --- | --- | --- | --- |
| AT GTFS static bundle (routes, stops, trips, stop_times, shapes, calendar) | Phase 1 network explorer, schedule baseline for delay calculations | GTFS zip (CSV) | Public download, no key required |
| AT GTFS-Realtime: Vehicle Positions | Phase 2 live map | GTFS-RT JSON by default, protobuf on request | Developer portal subscription key |
| AT GTFS-Realtime: Trip Updates | Phase 2/3 ETAs, Phase 4/5 delay observations | GTFS-RT JSON by default, protobuf on request | Developer portal subscription key |
| AT GTFS-Realtime: Service Alerts | Phase 3 disruption panel | GTFS-RT JSON by default, protobuf on request | Developer portal subscription key |

### References

- AT data sources (licence overview): <https://at.govt.nz/about-us/at-data-sources>
- AT GTFS static download and specification page:
  <https://at.govt.nz/bus-train-ferry/more-services/google-transit-feed>
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
- A third-party API directory reports a quota of roughly 600 calls/minute and 35,000
  calls/week. **Verify the actual quota in your own portal subscription** before
  choosing a polling cadence. At one aggregated call per 30 seconds the budget is about
  2,880 calls/day (20,160/week), which leaves comfortable headroom.
- Exact endpoint paths differ between the legacy GTFS-RT endpoints and the newer
  "Realtime Compat" API. Confirm the paths attached to your subscription and configure
  them with `TP_AT_*_URL`; do not hard-code them in source code.

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
