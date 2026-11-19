import { useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { PageHeader } from "../components/ui/PageHeader";
import { FilterBar } from "../components/ui/FilterBar";
import {
  AnalyticsFilterProvider,
  useAnalyticsFilters,
} from "../hooks/useAnalyticsFilters";
import {
  useAnalyticsMetrics,
  useAnalyticsSummary,
} from "../hooks/useAnalytics";
import type { AnalyticsMetric } from "../api/types";

const tabs = [
  { to: "/analytics", label: "Overview", end: true },
  { to: "/analytics/ridership", label: "Ridership", end: false },
  { to: "/analytics/performance", label: "Performance", end: false },
  { to: "/analytics/relationships", label: "Relationships", end: false },
  { to: "/analytics/methodology", label: "Methodology", end: false },
];

function allowedMetricsForPath(pathname: string): AnalyticsMetric[] {
  if (pathname.includes("/ridership")) return ["boardings", "boardings_per_service_hour"];
  if (pathname.includes("/performance")) return ["punctuality", "reliability"];
  if (pathname.includes("/relationships")) return ["punctuality"];
  return ["punctuality", "reliability", "boardings", "boardings_per_service_hour"];
}

function AnalyticsLayout() {
  const location = useLocation();
  const { filters, setMetric, setRange } = useAnalyticsFilters();
  const summaryQuery = useAnalyticsSummary();
  const metricsQuery = useAnalyticsMetrics();
  const coverage = metricsQuery.data?.items[filters.metric];
  const allowed = allowedMetricsForPath(location.pathname);

  useEffect(() => {
    if (!allowed.includes(filters.metric)) setMetric(allowed[0]);
  }, [allowed.join(","), filters.metric, setMetric]);

  useEffect(() => {
    if (!coverage?.first_month || !coverage?.last_month) return;
    if (filters.from < coverage.first_month || filters.to > coverage.last_month) {
      setRange(coverage.first_month, coverage.last_month);
    }
  }, [coverage?.first_month, coverage?.last_month, filters.from, filters.to, setRange]);

  return (
    <div className="observatory-content">
      <PageHeader
        title="Analytics"
        description="Official AT performance and ridership reports, read as a transport observatory. Each view answers one operational question."
        meta={[
          `${summaryQuery.data?.report_count ?? "—"} official reports`,
          coverage?.sufficiency ? `Data sufficiency: ${coverage.sufficiency}` : "Loading coverage",
        ]}
      />

      <nav className="observatory-tabs" aria-label="Analytics views">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `observatory-tab${isActive ? " is-active" : ""}`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>

      <FilterBar
        firstMonth={coverage?.first_month ?? "2019-01"}
        lastMonth={coverage?.last_month ?? "2026-10"}
        showNormalize={location.pathname.includes("/relationships")}
        allowedMetrics={allowed}
      />

      <Outlet />
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <AnalyticsFilterProvider>
      <AnalyticsLayout />
    </AnalyticsFilterProvider>
  );
}
