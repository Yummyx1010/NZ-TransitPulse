import type { AnalyticsMetric } from "../../api/types";
import { Panel } from "../../components/ui/Panel";
import { DataWarning, DataSourceNote } from "../../components/ui/DataSourceNote";
import { LoadingState } from "../../components/ui/States";
import { RouteRankingBars } from "../../components/analytics/charts/RouteRankingBars";
import { RidershipTrendChart } from "../../components/analytics/charts/RidershipTrendChart";
import { useAnalyticsFilters } from "../../hooks/useAnalyticsFilters";
import {
  useAnalyticsRanking,
  useAnalyticsTrends,
  useOfficialNetworkMetrics,
} from "../../hooks/useAnalytics";
import { getMetricDefinition } from "../../lib/metricDefinitions";

export function RidershipView() {
  const { filters, setRoute } = useAnalyticsFilters();
  const metric: AnalyticsMetric =
    filters.metric === "boardings_per_service_hour"
      ? "boardings_per_service_hour"
      : "boardings";
  const definition = getMetricDefinition(metric);
  const common = {
    startMonth: filters.from,
    endMonth: filters.to,
    includeSchoolRoutes: filters.includeSchoolRoutes,
  };
  const ranking = useAnalyticsRanking({ ...common, metric, limit: 12 });
  const trends = useAnalyticsTrends(
    metric,
    filters.route ?? undefined,
    filters.from,
    filters.to,
  );
  const totals = useOfficialNetworkMetrics(
    "bus_patronage",
    filters.from,
    filters.to,
  );

  return (
    <div>
      <DataSourceNote>
        {definition.definition} Unit: {definition.unit}. High ridership does not imply
        poor operational performance.
      </DataSourceNote>
      {ranking.data?.warning ? <DataWarning>{ranking.data.warning}</DataWarning> : null}
      {trends.data?.warning ? <DataWarning>{trends.data.warning}</DataWarning> : null}

      {ranking.isLoading || trends.isLoading ? <LoadingState /> : null}

      <Panel
        title="Most used routes"
        subtitle="Routes are ordered by the selected ridership measure, highest first."
        meta={definition.unit}
      >
        <RouteRankingBars
          metric={metric}
          items={ranking.data?.items ?? []}
          intent="most-used"
          selectedRoute={filters.route}
          onSelectRoute={setRoute}
        />
      </Panel>

      <Panel
        title={filters.route ? `Ridership trend · route ${filters.route}` : "Ridership trend"}
        subtitle="Network total shows absolute boardings. Average per route shows the mean across reporting bus routes."
        meta={`${filters.from} – ${filters.to}`}
      >
        <RidershipTrendChart
          totals={metric === "boardings" ? (totals.data?.items ?? []) : []}
          averages={trends.data?.items ?? []}
        />
      </Panel>
    </div>
  );
}
