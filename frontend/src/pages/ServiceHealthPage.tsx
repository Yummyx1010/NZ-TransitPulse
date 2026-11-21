import { useEffect } from "react";

import { FilterBar } from "../components/ui/FilterBar";
import { PageHeader } from "../components/ui/PageHeader";
import { AnalyticsFilterProvider, useAnalyticsFilters } from "../hooks/useAnalyticsFilters";
import { useAnalyticsMetrics } from "../hooks/useAnalytics";
import type { AnalyticsMetric } from "../api/types";
import { PerformanceView } from "./analytics/PerformanceView";

const ALLOWED: AnalyticsMetric[] = ["punctuality", "reliability"];

function ServiceHealthLayout() {
  const { filters, setMetric, setRange } = useAnalyticsFilters();
  const metrics = useAnalyticsMetrics().data;
  const coverage = metrics?.items[filters.metric];

  useEffect(() => {
    if (!ALLOWED.includes(filters.metric)) setMetric(ALLOWED[0]);
  }, [filters.metric, setMetric]);

  useEffect(() => {
    if (!coverage?.first_month || !coverage?.last_month) return;
    if (filters.from < coverage.first_month || filters.to > coverage.last_month) {
      setRange(coverage.first_month, coverage.last_month);
    }
  }, [coverage?.first_month, coverage?.last_month, filters.from, filters.to, setRange]);

  return (
    <div className="observatory-content">
      <PageHeader
        title="Service Health"
        description="Find routes with weaker official punctuality or reliability, with transparent definitions and sample sizes."
        meta={["Official service metrics only"]}
      />
      <FilterBar
        firstMonth={coverage?.first_month ?? "2019-01"}
        lastMonth={coverage?.last_month ?? "2026-10"}
        allowedMetrics={ALLOWED}
      />
      <PerformanceView />
    </div>
  );
}

export function ServiceHealthPage() {
  return (
    <AnalyticsFilterProvider>
      <ServiceHealthLayout />
    </AnalyticsFilterProvider>
  );
}
