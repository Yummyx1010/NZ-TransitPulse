import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type {
  AnalyticsQuery,
  AnalyticsMetric,
  RouteIntelligence,
} from "../api/types";

export function useOfficialNetworkMetrics(
  metric: string,
  startMonth?: string,
  endMonth?: string,
) {
  return useQuery({
    queryKey: ["official-network-metrics", metric, startMonth, endMonth],
    queryFn: () => api.officialNetworkMetrics(metric, startMonth, endMonth),
    retry: 1,
  });
}

export function useAnalyticsSummary() {
  return useQuery({
    queryKey: ["analytics-summary"],
    queryFn: () => api.analyticsSummary(),
    retry: 1,
  });
}

export function useAnalyticsMetrics() {
  return useQuery({
    queryKey: ["analytics-metrics"],
    queryFn: () => api.analyticsMetrics(),
    retry: 1,
  });
}

export function useAnalyticsRoutes(q?: string) {
  return useQuery({
    queryKey: ["analytics-routes", q],
    queryFn: () => api.analyticsRoutes(q),
    retry: 1,
    enabled: Boolean(q),
  });
}

export function useAnalyticsNetwork() {
  return useQuery({
    queryKey: ["analytics-network"],
    queryFn: () => api.analyticsNetwork(),
    retry: 1,
  });
}

export function useAnalyticsRanking(query: AnalyticsQuery) {
  return useQuery({
    queryKey: ["analytics-ranking", query],
    queryFn: () => api.analyticsRanking(query),
    retry: 1,
  });
}

export function useAnalyticsTrends(
  metric: AnalyticsMetric,
  routeNo: string | undefined,
  startMonth?: string,
  endMonth?: string,
) {
  return useQuery({
    queryKey: ["analytics-trends", metric, routeNo, startMonth, endMonth],
    queryFn: () => api.analyticsTrends(metric, routeNo, startMonth, endMonth),
    retry: 1,
  });
}

export function useAnalyticsHeatmap(query: AnalyticsQuery) {
  return useQuery({
    queryKey: ["analytics-heatmap", query],
    queryFn: () => api.analyticsHeatmap(query),
    retry: 1,
  });
}

export function useAnalyticsScatter(
  startMonth?: string,
  endMonth?: string,
  includeSchoolRoutes?: boolean,
  minBoardings = 0,
  limit = 30,
) {
  return useQuery({
    queryKey: [
      "analytics-scatter",
      startMonth,
      endMonth,
      includeSchoolRoutes,
      minBoardings,
      limit,
    ],
    queryFn: () =>
      api.analyticsScatter(
        startMonth,
        endMonth,
        includeSchoolRoutes,
        minBoardings,
        limit,
      ),
    retry: 1,
  });
}

export function useRouteIntelligence(routeNo: string | null) {
  return useQuery<RouteIntelligence>({
    queryKey: ["route-intelligence", routeNo],
    queryFn: () => api.routeIntelligence(routeNo ?? ""),
    enabled: Boolean(routeNo),
    retry: 1,
  });
}
