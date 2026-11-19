import type { AnalyticsMetric } from "../../api/types";
import { Panel } from "../../components/ui/Panel";
import { MetricStrip } from "../../components/ui/MetricStrip";
import { DataWarning } from "../../components/ui/DataSourceNote";
import { LoadingState } from "../../components/ui/States";
import { RouteRankingBars } from "../../components/analytics/charts/RouteRankingBars";
import { useAnalyticsFilters } from "../../hooks/useAnalyticsFilters";
import {
  useAnalyticsNetwork,
  useAnalyticsRanking,
  useAnalyticsSummary,
} from "../../hooks/useAnalytics";
import { getMetricDefinition } from "../../lib/metricDefinitions";

const attentionMetric: AnalyticsMetric = "punctuality";
const ridershipMetric: AnalyticsMetric = "boardings";

export function OverviewView() {
  const { filters, setRoute } = useAnalyticsFilters();
  const summary = useAnalyticsSummary().data;
  const network = useAnalyticsNetwork().data;
  const common = {
    startMonth: filters.from,
    endMonth: filters.to,
    includeSchoolRoutes: filters.includeSchoolRoutes,
    limit: 8,
  };
  const attention = useAnalyticsRanking({ ...common, metric: attentionMetric });
  const used = useAnalyticsRanking({ ...common, metric: ridershipMetric });
  const loading = attention.isLoading || used.isLoading || !summary || !network;
  const coverage = summary?.metrics.punctuality;

  return (
    <div>
      <MetricStrip
        items={[
          {
            label: "Official reports",
            value: String(summary?.report_count ?? "—"),
            note: "Downloaded from Auckland Transport",
          },
          {
            label: "Punctuality coverage",
            value: coverage ? `${coverage.first_month} – ${coverage.last_month}` : "—",
            note: coverage ? `${coverage.months} observed months` : "Loading coverage",
          },
          {
            label: "Bus network",
            value: String(network?.bus_routes ?? "—"),
            note: `${network?.stops ?? "—"} stops in the active GTFS feed`,
          },
        ]}
      />

      {attention.data?.warning ? <DataWarning>{attention.data.warning}</DataWarning> : null}
      {used.data?.warning ? <DataWarning>{used.data.warning}</DataWarning> : null}

      {loading ? <LoadingState /> : null}

      <Panel
        title="Most used routes"
        subtitle={`Highest average ${getMetricDefinition(ridershipMetric).label.toLowerCase()} in the selected period. Ridership is not a performance grade.`}
        meta={getMetricDefinition(ridershipMetric).unit}
      >
        <RouteRankingBars
          metric={ridershipMetric}
          items={used.data?.items ?? []}
          intent="most-used"
          selectedRoute={filters.route}
          onSelectRoute={setRoute}
        />
      </Panel>

      <Panel
        title="Routes requiring attention"
        subtitle="Lowest average official punctuality. Routes with fewer than three observed months are excluded."
        meta={getMetricDefinition(attentionMetric).unit}
      >
        <RouteRankingBars
          metric={attentionMetric}
          items={attention.data?.items ?? []}
          intent="attention"
          selectedRoute={filters.route}
          onSelectRoute={setRoute}
        />
      </Panel>
    </div>
  );
}
