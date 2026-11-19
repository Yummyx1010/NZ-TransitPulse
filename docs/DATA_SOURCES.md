# Data Sources and Compliance

Verified against Auckland Transport (AT) public documentation on 2026-11-14, live
API responses on 2026-11-15, and the official reports page on 2026-11-18. The MVP's
historical analysis uses AT's published reports; a self-hosted live observation
collector is a post-MVP option, not a Phase 4 dependency.

## Sources

| Source | Used for | Format | Access |
| --- | --- | --- | --- |
| AT GTFS static bundle (`agency`, `routes`, `stops`, `trips`, `stop_times`, `shapes`; plus `calendar` and others) | Phase 1 network explorer and route geometry, schedule baseline for delay calculations | GTFS zip (CSV) | Public download, no key required |
| AT aggregated GTFS-Realtime (`realtime/legacy`) | Phase 2: vehicles, trip updates and alerts in one call | GTFS-RT JSON, wrapped in `status/response` envelope | Developer portal subscription key |
| AT GTFS-Realtime: Vehicle Positions | Live positions on the map; separate endpoint kept as optional fallback | GTFS-RT JSON by default, protobuf on request | Developer portal subscription key |
| AT GTFS-Realtime: Trip Updates | Phase 3 ETAs and live delay status only; not used for MVP history | GTFS-RT JSON by default, protobuf on request | Developer portal subscription key |
| AT published reports: punctuality/reliability, bus performance, patronage, hourly bus boardings | Phase 4 historical analysis and Phase 5 dashboard | XLSX workbooks downloaded from the AT reports page | Public download; source page has no explicit open-data licence, so cite and normalise rather than redistribute |
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
- AT public transport reports / patronage / punctuality:
  <https://at.govt.nz/about-us/reports-publications/how-many-people-are-taking-buses-trains-and-ferries>

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

## Official report facts (verified 2026-11-18)

- The reports page provides downloadable **XLSX** files for:
  monthly punctuality and reliability, bus performance, monthly patronage, hourly bus
  boardings, and passenger counts by month/day. Route-specific reviews are PDFs.
- Coverage is much longer than a self-hosted collector could provide: monthly patronage
  goes back to **July 2005**, bus performance reports cover **2019-2025**, and
  punctuality/reliability and hourly boardings cover **July 2023-October 2026**.
- Official definitions shown on the page:
  - **Punctuality**: first stop departs no earlier than 1 minute before schedule and no
    later than 5 minutes after; last stop arrives no later than 5 minutes after schedule.
  - **Reliability**: first stop departs no earlier than 1 minute before schedule and no
    later than 10 minutes after.
  These definitions differ from the Phase 3 ETA badge threshold (±60 s) and must be
  labelled separately in the UI.
- The report page does **not** state an explicit open-data licence; it shows
  `© Auckland Transport 2026`. Treat these as official published reports: store derived
  normalized rows, cite the source page and reporting period, and do not redistribute
  the original workbooks as project data.
- Example report URLs discovered from the page HTML:
  - Punctuality 2023-2024:
    <https://at.govt.nz/media/fonhut3i/auckland-transport-monthly-punctuality-and-reliability-2023-to-2024.xlsx>
  - Punctuality 2024-2025:
    <https://at.govt.nz/media/soieg3up/auckland-transport-monthly-punctuality-and-reliability-2024-to-2025.xlsx>
  - Punctuality 2025-2026:
    <https://at.govt.nz/media/x1loqu23/auckland-transport-monthly-punctuality-and-reliability-june-2026.xlsx>
  - Bus performance 2024:
    <https://at.govt.nz/media/sxnlgvh2/auckland-transport-bus-performance-report-january-2024-to-december-2024.xlsx>
  - Monthly patronage 2005-2025:
    <https://at.govt.nz/media/l4ugvfd4/auckland-transport-monthly-patronage-from-july-2005-to-june-2025.xlsx>

## Compliance decisions for the MVP historical analysis

1. The subscription key lives only in `.env` (server-side) and is never exposed to the
   browser, committed, logged, or included in test fixtures.
2. The MVP does **not** persist GTFS-Realtime payloads or self-collected delay
   observations. Historical analysis is based on AT's published reports.
3. Imported report rows retain source report metadata, reporting period and checksum so
   results can be audited against the official workbook.
4. Original XLSX files are treated as downloadable inputs under `data/reports/` and are
   gitignored; the repository stores only normalized derived tables and source URLs.
5. Official punctuality/reliability definitions are shown in the dashboard, and locally
   computed GTFS network metrics are labelled as project-derived, not AT indicators.
6. Raw report files are not redistributed as NZ TransitPulse datasets. Public pages show
   the AT attribution and state that the project is independent and not endorsed by AT.
7. A self-hosted observation collector remains a post-MVP option for deployments that
   run continuously; enabling it requires a fresh terms-of-use review.

## Time handling

- Store all timestamps in **UTC** in MySQL.
- Render all user-facing times in `Pacific/Auckland` (NZST/NZDT), including daylight
  saving transitions.
- GTFS static times can exceed `24:00:00` for services after midnight; the loader must
  resolve them against a service date rather than a wall-clock date.
