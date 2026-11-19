import { Panel } from "../../components/ui/Panel";
import { DataWarning, DataSourceNote } from "../../components/ui/DataSourceNote";
import { LoadingState } from "../../components/ui/States";
import { RelationshipScatter } from "../../components/analytics/charts/RelationshipScatter";
import { SeasonalityHeatmap } from "../../components/analytics/charts/SeasonalityHeatmap";
import { useAnalyticsFilters } from "../../hooks/useAnalyticsFilters";
import {
  useAnalyticsHeatmap,
  useAnalyticsScatter,
} from "../../hooks/useAnalytics";

export function RelationshipsView() {
  const { filters, setRoute } = useAnalyticsFilters();
  const scatter = useAnalyticsScatter(
    filters.from,
    filters.to,
    filters.includeSchoolRoutes,
    1000,
    24,
  );
  const heatmap = useAnalyticsHeatmap({
    metric: "punctuality",
    startMonth: filters.from,
    endMonth: filters.to,
    includeSchoolRoutes: filters.includeSchoolRoutes,
    limit: 8,
  });

  return (
    <div>
      <DataSourceNote>
        One point is one bus route averaged across the selected period. Correlation is
        shown only with at least five comparable routes and is descriptive, not causal.
      </DataSourceNote>
      {scatter.data?.warning ? <DataWarning>{scatter.data.warning}</DataWarning> : null}
      {heatmap.data?.warning ? <DataWarning>{heatmap.data.warning}</DataWarning> : null}
      {scatter.isLoading || heatmap.isLoading ? <LoadingState /> : null}

      <Panel
        title="Are busier routes also more punctual?"
        subtitle="X: average monthly boardings. Y: official punctuality percentage."
        meta={`${filters.from} – ${filters.to}`}
      >
        <RelationshipScatter
          points={scatter.data?.points ?? []}
          correlation={scatter.data?.correlation ?? null}
          selectedRoute={filters.route}
          onSelectRoute={setRoute}
        />
      </Panel>

      <Panel
        title="Seasonality detail"
        subtitle="Optional diagnostic for recurring monthly peaks and dips. Read one row left to right."
        meta={filters.normalizeHeatmap ? "Per-route scale" : "Shared scale"}
      >
        <SeasonalityHeatmap
          metric="punctuality"
          months={heatmap.data?.months ?? []}
          items={heatmap.data?.items ?? []}
          normalize={filters.normalizeHeatmap}
        />
      </Panel>
    </div>
  );
}
