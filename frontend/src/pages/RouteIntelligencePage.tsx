import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { AnalyticsMetric, RouteChange } from "../api/types";
import { StopMap } from "../components/StopMap";
import { SeasonalityHeatmap } from "../components/analytics/charts/SeasonalityHeatmap";
import { DataSourceNote, DataWarning } from "../components/ui/DataSourceNote";
import { MetricStrip } from "../components/ui/MetricStrip";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { EmptyState, LoadingState } from "../components/ui/States";
import {
  useAnalyticsRoutes,
  useAnalyticsTrends,
  useRouteIntelligence,
} from "../hooks/useAnalytics";
import { useRouteContext } from "../hooks/useRouteContext";
import { getMetricDefinition } from "../lib/metricDefinitions";
import { formatMetricValue, metricLabel } from "../lib/analytics";

function formatChange(change: RouteChange): string {
  if (change.change === null) return "No comparable previous month";
  if (change.unit === "%") {
    const points = change.change * 100;
    return `${points >= 0 ? "+" : ""}${points.toFixed(1)} percentage points`;
  }
  const value = Math.round(change.change);
  return `${value >= 0 ? "+" : ""}${value.toLocaleString("en-NZ")} ${change.unit}`;
}

export function RouteIntelligencePage() {
  const { routeNo: pathRoute } = useParams();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const { routeNo, routeIds, routeLabel, matchedInGtfs, setRoute } = useRouteContext();
  const activeRoute = pathRoute ?? routeNo;

  useEffect(() => {
    if (pathRoute && pathRoute !== routeNo) setRoute(pathRoute);
  }, [pathRoute, routeNo, setRoute]);

  function selectRoute(next: string) {
    setRoute(next);
    navigate(`/routes/${encodeURIComponent(next)}`);
  }

  const search = useAnalyticsRoutes(query.trim());
  const intelligence = useRouteIntelligence(activeRoute);
  const primaryRouteId = matchedInGtfs ? routeIds[0] ?? null : null;

  const geometry = useQuery({
    queryKey: ["route-intelligence-geometry", primaryRouteId],
    queryFn: () => api.routeGeometry(primaryRouteId ?? ""),
    enabled: Boolean(primaryRouteId),
    retry: 1,
  });
  const vehicles = useQuery({
    queryKey: ["route-intelligence-vehicles", primaryRouteId],
    queryFn: () =>
      api.realtimeVehicles({
        route_id: primaryRouteId ?? undefined,
        mode: "Bus",
        limit: 200,
      }),
    enabled: Boolean(primaryRouteId),
    refetchInterval: 30_000,
    retry: 1,
  });
  const alerts = useQuery({
    queryKey: ["route-intelligence-alerts", primaryRouteId],
    queryFn: () =>
      api.realtimeAlerts({
        route_id: primaryRouteId ?? undefined,
        mode: "Bus",
        limit: 5,
      }),
    enabled: Boolean(primaryRouteId),
    refetchInterval: 30_000,
    retry: 1,
  });

  const punctualityTrend = useAnalyticsTrends("punctuality", activeRoute ?? undefined);
  const reliabilityTrend = useAnalyticsTrends("reliability", activeRoute ?? undefined);
  const boardingsTrend = useAnalyticsTrends("boardings", activeRoute ?? undefined);

  const shape = useMemo(
    () => geometry.data?.shapes[0] ?? null,
    [geometry.data?.shapes],
  );
  const changes = intelligence.data?.changes ?? [];
  const latest = (metric: AnalyticsMetric) =>
    changes.find((change) => change.metric === metric);
  const seasonalityMetric: AnalyticsMetric = "punctuality";
  const seasonality = intelligence.data?.seasonality[seasonalityMetric];
  const seasonalityItem = useMemo(
    () =>
      seasonality
        ? [
            {
              route_no: activeRoute ?? "",
              route_name: intelligence.data?.route_name ?? null,
              values: seasonality.values,
            },
          ]
        : [],
    [activeRoute, intelligence.data?.route_name, seasonality],
  );

  return (
    <div className="observatory-content">
      <PageHeader
        title="Route Intelligence"
        description="Search an official route number to connect its current map, live buses, alerts and historical performance evidence."
        meta={
          activeRoute
            ? [`Route ${activeRoute}`, routeLabel ?? ""].filter(Boolean)
            : ["No route selected"]
        }
      />

      <Panel
        title="Find a route"
        subtitle="Search by official route number, then the route stays selected across analytics views."
        meta="Official + GTFS"
      >
        <form
          className="observatory-route-search"
          onSubmit={(event) => {
            event.preventDefault();
            if (query.trim()) selectRoute(query.trim());
          }}
        >
          <input
            aria-label="Route number"
            value={query}
            placeholder="e.g. 70"
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit">Inspect route</button>
        </form>
        {search.data?.items.length ? (
          <ul className="observatory-route-results">
            {search.data.items.slice(0, 8).map((item) => (
              <li key={item.route_no}>
                <button type="button" onClick={() => selectRoute(item.route_no)}>
                  <strong>{item.route_no}</strong>
                  <span>{item.route_name ?? "Unnamed route"}</span>
                  <small>
                    {item.matched_in_gtfs
                      ? item.route_ids.join(", ")
                      : "Official reports only"}
                  </small>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </Panel>

      {!activeRoute ? (
        <EmptyState>
          Select a route to see its map, live service status and historical evidence.
        </EmptyState>
      ) : intelligence.isLoading ? (
        <LoadingState />
      ) : !intelligence.data?.has_official_data ? (
        <EmptyState>
          No official report rows are available for {activeRoute}. The route may be GTFS-only
          or use a different official route number.
        </EmptyState>
      ) : (
        <>
          {intelligence.data.warnings.map((warning) => (
            <DataWarning key={warning}>{warning}</DataWarning>
          ))}

          <MetricStrip
            items={[
              {
                label: "Observed months",
                value: String(latest("punctuality")?.sample_months ?? "—"),
                note: "Official punctuality series",
              },
              {
                label: "Latest punctuality",
                value: formatMetricValue(
                  "punctuality",
                  latest("punctuality")?.latest_value,
                ),
                note: latest("punctuality")?.latest_month ?? "No month",
              },
              {
                label: "Latest boardings",
                value: formatMetricValue("boardings", latest("boardings")?.latest_value),
                note: latest("boardings")?.latest_month ?? "No month",
              },
              {
                label: "Current buses",
                value: String(vehicles.data?.total ?? 0),
                note: `${alerts.data?.total ?? 0} current alerts`,
              },
            ]}
          />

          <Panel
            title={`Route ${activeRoute} map`}
            subtitle={
              matchedInGtfs
                ? `GTFS route ${primaryRouteId}, with real shape geometry and live buses.`
                : "No GTFS route match; official historical evidence is still shown below."
            }
            meta={matchedInGtfs ? "Matched in GTFS" : "Official report only"}
          >
            {matchedInGtfs ? (
              <StopMap
                shape={shape}
                vehicles={vehicles.data?.items ?? []}
                approximate={geometry.data?.approximate ?? false}
                note={geometry.data?.note ?? ""}
                fitSignal={0}
                emptyMessage="Loading route geometry..."
              />
            ) : (
              <p className="observatory-empty">
                This official route number has no matching GTFS route id, so no map is shown.
              </p>
            )}
          </Panel>

          <Panel
            title="What Changed?"
            subtitle="Evidence-based comparison of the latest observed month against the previous observed month. No causal claim is made."
            meta="Official reports"
          >
            <div className="route-change-grid">
              {changes.map((change) => (
                <article key={change.metric} className="route-change-item">
                  <p className="eyebrow">{metricLabel(change.metric)}</p>
                  <strong>{formatMetricValue(change.metric, change.latest_value)}</strong>
                  <span>{change.latest_month}</span>
                  <p>{formatChange(change)}</p>
                  <small>
                    12-month average:{" "}
                    {formatMetricValue(change.metric, change.rolling_12m_average)} ·{" "}
                    {change.sample_months} observed months
                  </small>
                </article>
              ))}
            </div>
          </Panel>

          <Panel
            title="Historical metrics"
            subtitle="Monthly official values for the selected route. Values are not filled for months without source data."
            meta={getMetricDefinition("punctuality").unit}
          >
            <div className="route-trend-grid">
              <div>
                <p className="eyebrow">Punctuality</p>
                {punctualityTrend.data?.items.length ? (
                  <Sparkline values={punctualityTrend.data.items.map((p) => p.value)} />
                ) : (
                  <p className="muted">No punctuality months available.</p>
                )}
              </div>
              <div>
                <p className="eyebrow">Reliability</p>
                {reliabilityTrend.data?.items.length ? (
                  <Sparkline values={reliabilityTrend.data.items.map((p) => p.value)} />
                ) : (
                  <p className="muted">No reliability months available.</p>
                )}
              </div>
              <div>
                <p className="eyebrow">Boardings</p>
                {boardingsTrend.data?.items.length ? (
                  <Sparkline values={boardingsTrend.data.items.map((p) => p.value)} />
                ) : (
                  <p className="muted">No boardings months available.</p>
                )}
              </div>
            </div>
          </Panel>

          {seasonality ? (
            <SeasonalityHeatmap
              metric={seasonalityMetric}
              months={seasonality.months}
              items={seasonalityItem}
              normalize={false}
            />
          ) : null}

          <Panel
            title="Current service status"
            subtitle="Realtime view for the matched GTFS route. This is current-state data, not part of the historical series."
            meta="Realtime"
          >
            <p>
              {vehicles.data?.total ?? 0} live buses · {alerts.data?.total ?? 0} service
              alerts
            </p>
            {alerts.data?.items.map((alert) => (
              <p key={alert.alert_id} className="route-alert">
                <strong>{alert.header ?? alert.effect ?? "Service alert"}</strong>
              </p>
            ))}
          </Panel>

          <DataSourceNote>
            {intelligence.data.attribution}. Route number mapping is read-only; no source
            dataset is modified.
          </DataSourceNote>
        </>
      )}
    </div>
  );
}

function Sparkline({ values }: { values: number[] }) {
  const width = 260;
  const height = 70;
  const padding = 6;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values
    .map((value, index) => {
      const x = padding + (index / Math.max(values.length - 1, 1)) * (width - padding * 2);
      const y = height - padding - ((value - min) / span) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="route-sparkline" aria-hidden="true">
      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth="2" />
    </svg>
  );
}
