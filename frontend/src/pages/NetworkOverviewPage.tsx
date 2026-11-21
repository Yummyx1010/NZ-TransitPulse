import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { RouteRankingBars } from "../components/analytics/charts/RouteRankingBars";
import { DataSourceNote, DataWarning } from "../components/ui/DataSourceNote";
import { MetricStrip } from "../components/ui/MetricStrip";
import { Panel } from "../components/ui/Panel";
import { LoadingState } from "../components/ui/States";
import { PageHeader } from "../components/ui/PageHeader";
import { useAnalyticsMetrics, useAnalyticsNetwork, useAnalyticsRanking, useAnalyticsSummary } from "../hooks/useAnalytics";
import { useRouteContext } from "../hooks/useRouteContext";
import { getMetricDefinition } from "../lib/metricDefinitions";

export function NetworkOverviewPage() {
  const { routeNo, setRoute } = useRouteContext();
  const summary = useAnalyticsSummary().data;
  const network = useAnalyticsNetwork().data;
  const metrics = useAnalyticsMetrics().data;
  const realtime = useQuery({
    queryKey: ["network-overview-realtime"],
    queryFn: () => api.realtimeStatus(),
    refetchInterval: 15_000,
    retry: 1,
  });
  const alerts = useQuery({
    queryKey: ["network-overview-alerts"],
    queryFn: () => api.realtimeAlerts({ mode: "Bus", limit: 3 }),
    refetchInterval: 30_000,
    retry: 1,
  });

  const boardingsCoverage = metrics?.items.boardings;
  const punctualityCoverage = metrics?.items.punctuality;
  const used = useAnalyticsRanking({
    metric: "boardings",
    startMonth: boardingsCoverage?.first_month ?? undefined,
    endMonth: boardingsCoverage?.last_month ?? undefined,
    limit: 5,
  });
  const attention = useAnalyticsRanking({
    metric: "punctuality",
    startMonth: punctualityCoverage?.first_month ?? undefined,
    endMonth: punctualityCoverage?.last_month ?? undefined,
    limit: 5,
  });

  const loading = summaryQueryLoading(summary, network, metrics);

  return (
    <div className="observatory-content">
      <PageHeader
        title="Network Overview"
        description="A quick read on Auckland's bus network: what is used, what needs attention, and whether live data is fresh."
        meta={[
          `${summary?.report_count ?? "—"} official reports`,
          realtime.data?.has_data ? "Realtime feed live" : "Realtime feed unavailable",
        ]}
      />

      <MetricStrip
        items={[
          {
            label: "Bus routes",
            value: String(network?.bus_routes ?? "—"),
            note: `${network?.stops ?? "—"} stops in active GTFS`,
          },
          {
            label: "Live buses",
            value: String(realtime.data?.vehicle_count ?? "—"),
            note: realtime.data?.feed_timestamp ? "Current AT feed" : "No live snapshot",
          },
          {
            label: "Service alerts",
            value: String(alerts.data?.total ?? "—"),
            note: "Bus-only alerts in current feed",
          },
        ]}
      />

      {used.data?.warning ? <DataWarning>{used.data.warning}</DataWarning> : null}
      {attention.data?.warning ? <DataWarning>{attention.data.warning}</DataWarning> : null}
      {loading ? <LoadingState /> : null}

      <Panel
        title="Most used routes"
        subtitle="Highest average boardings in the available reporting period. Ridership is not a performance grade."
        meta={getMetricDefinition("boardings").unit}
      >
        <RouteRankingBars
          metric="boardings"
          items={used.data?.items ?? []}
          intent="most-used"
          selectedRoute={routeNo}
          onSelectRoute={setRoute}
        />
      </Panel>

      <Panel
        title="Routes requiring attention"
        subtitle="Lowest average official punctuality in the available reporting period."
        meta={getMetricDefinition("punctuality").unit}
      >
        <RouteRankingBars
          metric="punctuality"
          items={attention.data?.items ?? []}
          intent="attention"
          selectedRoute={routeNo}
          onSelectRoute={setRoute}
        />
      </Panel>

      <Panel
        title="Current disruptions"
        subtitle="Bus-only service alerts from the current AT realtime feed."
        meta="Realtime"
      >
        {alerts.data?.items.length ? (
          <ul className="observatory-alert-list">
            {alerts.data.items.map((alert) => (
              <li key={alert.alert_id}>
                <strong>{alert.header ?? alert.effect ?? "Service alert"}</strong>
                {alert.description ? <p>{alert.description}</p> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="observatory-empty">No current bus alerts in the live feed.</p>
        )}
      </Panel>

      <DataSourceNote>
        Choose a route above, then continue to{" "}
        <Link to={routeNo ? `/routes?route=${encodeURIComponent(routeNo)}` : "/routes"}>
          Route Intelligence
        </Link>{" "}
        or <Link to="/live">Live Network</Link>. Full overview analysis arrives in v0.6.5.
      </DataSourceNote>
    </div>
  );
}

function summaryQueryLoading(
  summary: unknown,
  network: unknown,
  metrics: unknown,
): boolean {
  return !summary || !network || !metrics;
}
