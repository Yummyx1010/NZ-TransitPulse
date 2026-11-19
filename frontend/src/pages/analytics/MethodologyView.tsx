import { useState } from "react";

import { Panel } from "../../components/ui/Panel";
import { LoadingState } from "../../components/ui/States";
import {
  useAnalyticsMetrics,
  useAnalyticsRoutes,
  useAnalyticsSummary,
} from "../../hooks/useAnalytics";
import { METRIC_DEFINITIONS } from "../../lib/metricDefinitions";

export function MethodologyView() {
  const [query, setQuery] = useState("70");
  const summary = useAnalyticsSummary();
  const metrics = useAnalyticsMetrics();
  const routes = useAnalyticsRoutes(query);

  return (
    <div>
      <Panel
        title="Metric definitions"
        subtitle="Official definitions are kept distinct from any locally derived network measures."
        meta="AT published reports"
      >
        <table className="observatory-method-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Definition</th>
              <th>Unit</th>
              <th>Source family</th>
            </tr>
          </thead>
          <tbody>
            {Object.values(METRIC_DEFINITIONS).map((metric) => {
              const live = metrics.data?.items[metric.key];
              return (
                <tr key={metric.key}>
                  <th scope="row">{metric.label}</th>
                  <td>{metric.definition}</td>
                  <td>{metric.unit}</td>
                  <td>
                    {metric.sourceFamily}
                    <br />
                    <span className="observatory-panel-meta">
                      {live?.first_month ?? "—"} – {live?.last_month ?? "—"} · {live?.months ?? 0} months
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>

      <Panel
        title="Data sources and ingestion"
        subtitle="Technical report registry is kept here, away from decision views."
        meta={`${summary.data?.report_count ?? "—"} reports`}
      >
        <table className="observatory-method-table">
          <tbody>
            <tr>
              <th>Static network</th>
              <td colSpan={3}>Official AT GTFS bundle. Routes, stops, trips, stop times and road geometry.</td>
            </tr>
            <tr>
              <th>Performance</th>
              <td colSpan={3}>AT monthly punctuality and reliability XLSX reports.</td>
            </tr>
            <tr>
              <th>Ridership</th>
              <td colSpan={3}>AT bus performance and hourly boardings XLSX reports.</td>
            </tr>
            <tr>
              <th>Missing data</th>
              <td colSpan={3}>Missing cells are displayed as gaps. No target, benchmark or projection is invented.</td>
            </tr>
            <tr>
              <th>School routes</th>
              <td colSpan={3}>Hidden by default because near-zero punctuality can distort network rankings.</td>
            </tr>
            <tr>
              <th>Self-collected history</th>
              <td colSpan={3}>Not used in this MVP. Official multi-year reports provide the historical baseline.</td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <Panel
        title="Route number matching"
        subtitle="Official reports use route numbers; GTFS uses route IDs with service suffixes."
        meta="read-only mapping"
      >
        <label className="observatory-field" htmlFor="route-map-query">
          <span>Find route</span>
          <input
            id="route-map-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="70"
          />
        </label>
        {routes.isLoading ? <LoadingState label="Loading route map…" /> : null}
        <table className="observatory-method-table">
          <thead>
            <tr>
              <th>Official route number</th>
              <th>GTFS route IDs</th>
              <th>Name</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {(routes.data?.items ?? []).slice(0, 20).map((item) => (
              <tr key={item.route_no}>
                <th scope="row">{item.route_no}</th>
                <td>{item.route_ids.length ? item.route_ids.join(", ") : "—"}</td>
                <td>{item.route_name ?? "—"}</td>
                <td>{item.matched_in_gtfs ? "Matched" : "Official only"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
