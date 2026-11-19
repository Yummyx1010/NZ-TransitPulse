import type { AnalyticsMetric } from "../../api/types";
import { Panel } from "../../components/ui/Panel";
import { DataWarning, DataSourceNote } from "../../components/ui/DataSourceNote";
import { LoadingState } from "../../components/ui/States";
import { RouteRankingBars } from "../../components/analytics/charts/RouteRankingBars";
import { PerformanceTrendChart } from "../../components/analytics/charts/PerformanceTrendChart";
import { useAnalyticsFilters } from "../../hooks/useAnalyticsFilters";
import { useAnalyticsRanking, useAnalyticsTrends } from "../../hooks/useAnalytics";
import { getMetricDefinition } from "../../lib/metricDefinitions";

export function PerformanceView() {
  const { filters, setRoute } = useAnalyticsFilters();
  const metric: AnalyticsMetric =
    filters.metric === "reliability" ? "reliability" : "punctuality";
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

  return (
    <div>
      <DataSourceNote>{definition.definition} Unit: {definition.unit}.</DataSourceNote>
      {ranking.data?.warning ? <DataWarning>{ranking.data.warning}</DataWarning> : null}
      {trends.data?.warning ? <DataWarning>{trends.data.warning}</DataWarning> : null}
      {ranking.isLoading || trends.isLoading ? <LoadingState /> : null}

      <Panel
        title="Routes requiring attention"
        subtitle={`Lowest average ${definition.label.toLowerCase()}, not the busiest routes. Minimum three observed months.`}
        meta={definition.unit}
      >
        <RouteRankingBars
          metric={metric}
          items={ranking.data?.items ?? []}
          intent="attention"
          selectedRoute={filters.route}
          onSelectRoute={setRoute}
        />
      </Panel>

      <Panel
        title={filters.route ? `${definition.label} · route ${filters.route}` : `${definition.label} trend`}
        subtitle="Network average or the selected route, depending on the current route context."
        meta={`${filters.from} – ${filters.to}`}
      >
        <PerformanceTrendChart metric={metric} points={trends.data?.items ?? []} />
      </Panel>
    </div>
  );
}
