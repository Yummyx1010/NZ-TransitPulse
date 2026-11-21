import { createContext, useContext, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { AnalyticsMetric } from "../api/types";
import { useRouteContext } from "./useRouteContext";

const METRICS: AnalyticsMetric[] = [
  "punctuality",
  "reliability",
  "boardings",
  "boardings_per_service_hour",
];

export interface AnalyticsFilterState {
  metric: AnalyticsMetric;
  from: string;
  to: string;
  includeSchoolRoutes: boolean;
  route: string | null;
  normalizeHeatmap: boolean;
}

interface AnalyticsFilterContextValue {
  filters: AnalyticsFilterState;
  setMetric: (value: AnalyticsMetric) => void;
  setRange: (from: string, to: string) => void;
  setIncludeSchoolRoutes: (value: boolean) => void;
  setRoute: (value: string | null) => void;
  setNormalizeHeatmap: (value: boolean) => void;
}

const AnalyticsFilterContext = createContext<AnalyticsFilterContextValue | null>(null);

function parseMetric(value: string | null): AnalyticsMetric {
  return METRICS.includes(value as AnalyticsMetric)
    ? (value as AnalyticsMetric)
    : "punctuality";
}

export function AnalyticsFilterProvider({ children }: { children: React.ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const { routeNo, setRoute } = useRouteContext();

  const filters = useMemo<AnalyticsFilterState>(
    () => ({
      metric: parseMetric(searchParams.get("metric")),
      from: searchParams.get("from") ?? "2019-01",
      to: searchParams.get("to") ?? "2026-10",
      includeSchoolRoutes: searchParams.get("schools") === "true",
      route: routeNo,
      normalizeHeatmap: searchParams.get("normalize") === "true",
    }),
    [routeNo, searchParams],
  );

  function updateParam(key: string, value: string | null) {
    const next = new URLSearchParams(searchParams);
    if (value === null || value === "") next.delete(key);
    else next.set(key, value);
    setSearchParams(next, { replace: true });
  }

  const value: AnalyticsFilterContextValue = {
    filters,
    setMetric: (metric) => updateParam("metric", metric),
    setRange: (from, to) => {
      const next = new URLSearchParams(searchParams);
      next.set("from", from);
      next.set("to", to);
      setSearchParams(next, { replace: true });
    },
    setIncludeSchoolRoutes: (schools) =>
      updateParam("schools", schools ? "true" : null),
    setRoute,
    setNormalizeHeatmap: (normalize) =>
      updateParam("normalize", normalize ? "true" : null),
  };

  return (
    <AnalyticsFilterContext.Provider value={value}>
      {children}
    </AnalyticsFilterContext.Provider>
  );
}

export function useAnalyticsFilters(): AnalyticsFilterContextValue {
  const context = useContext(AnalyticsFilterContext);
  if (!context) {
    throw new Error("useAnalyticsFilters must be used inside AnalyticsFilterProvider");
  }
  return context;
}
