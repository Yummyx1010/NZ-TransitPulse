import type {
  AnalyticsMetric,
  AnalyticsQuery,
  AnalyticsRankingResponse,
  AnalyticsSummary,
  AnalyticsTrendResponse,
  AnalyticsHeatmapResponse,
  CorrelationResult,
  ArrivalsResponse,
  MetricMetadata,
  NetworkStatus,
  OfficialMetricPoint,
  Paginated,
  RealtimeAlertList,
  RealtimeAlertQuery,
  RealtimeStatus,
  RealtimeVehicleList,
  RealtimeVehicleQuery,
  RouteCatalogItem,
  RouteGeometry,
  NetworkSummary,
  ScatterPoint,
  RouteQuery,
  RouteSummary,
  StopArrivalsQuery,
  StopSummary,
} from "./types";

const BASE = "/api/v1";

interface UrlParams {
  q?: string;
  mode?: string;
  route_id?: string;
  shape_id?: string;
  bbox?: string;
  minutes?: number;
  limit?: number;
  metric?: string;
  start_month?: string;
  end_month?: string;
  route_no?: string;
  include_school_routes?: boolean;
  min_months?: number;
  min_boardings?: number;
}

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}): ${path}`);
  }
  return (await response.json()) as T;
}

function queryString(params: UrlParams): string {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.mode) search.set("mode", params.mode);
  if (params.route_id) search.set("route_id", params.route_id);
  if (params.shape_id) search.set("shape_id", params.shape_id);
  if (params.bbox) search.set("bbox", params.bbox);
  if (params.minutes) search.set("minutes", String(params.minutes));
  if (params.metric) search.set("metric", params.metric);
  if (params.route_no) search.set("route_no", params.route_no);
  if (params.start_month) search.set("start_month", params.start_month);
  if (params.end_month) search.set("end_month", params.end_month);
  if (params.include_school_routes !== undefined) {
    search.set("include_school_routes", String(params.include_school_routes));
  }
  if (params.min_months) search.set("min_months", String(params.min_months));
  if (params.min_boardings !== undefined) {
    search.set("min_boardings", String(params.min_boardings));
  }
  if (params.limit) search.set("limit", String(params.limit));
  const value = search.toString();
  return value ? `?${value}` : "";
}

export const api = {
  networkStatus: () => fetchJson<NetworkStatus>("/network/status"),
  routes: (params: RouteQuery = {}) =>
    fetchJson<Paginated<RouteSummary>>(`/routes${queryString(params)}`),
  routeStops: (routeId: string) =>
    fetchJson<Paginated<StopSummary>>(
      `/routes/${encodeURIComponent(routeId)}/stops`,
    ),
  routeGeometry: (routeId: string) =>
    fetchJson<RouteGeometry>(
      `/routes/${encodeURIComponent(routeId)}/geometry`,
    ),
  stops: (q?: string, routeId?: string) =>
    fetchJson<Paginated<StopSummary>>(`/stops${queryString({ q, route_id: routeId })}`),
  stopArrivals: (stopId: string, params: StopArrivalsQuery = {}) =>
    fetchJson<ArrivalsResponse>(
      `/stops/${encodeURIComponent(stopId)}/arrivals${queryString(params)}`,
    ),
  realtimeStatus: () => fetchJson<RealtimeStatus>("/realtime/status"),
  realtimeVehicles: (params: RealtimeVehicleQuery = {}) =>
    fetchJson<RealtimeVehicleList>(`/realtime/vehicles${queryString(params)}`),
  realtimeAlerts: (params: RealtimeAlertQuery = {}) =>
    fetchJson<RealtimeAlertList>(`/realtime/alerts${queryString(params)}`),

  officialNetworkMetrics: (
    metric: string,
    startMonth?: string,
    endMonth?: string,
  ) =>
    fetchJson<{ items: OfficialMetricPoint[]; total: number }>(
      `/official/network-metrics${queryString({
        metric,
        start_month: startMonth,
        end_month: endMonth,
      })}`,
    ),

  analyticsSummary: () =>
    fetchJson<AnalyticsSummary>("/analytics/summary"),
  analyticsMetrics: () =>
    fetchJson<{
      total: number;
      items: Record<string, MetricMetadata>;
    }>("/analytics/metrics"),
  analyticsRoutes: (q?: string) =>
    fetchJson<{ total: number; items: RouteCatalogItem[] }>(
      `/analytics/routes${queryString({ q })}`,
    ),
  analyticsNetwork: () =>
    fetchJson<NetworkSummary>("/analytics/network"),
  analyticsRanking: (query: AnalyticsQuery) =>
    fetchJson<AnalyticsRankingResponse>(
      `/analytics/route-ranking${queryString({
        metric: query.metric,
        start_month: query.startMonth,
        end_month: query.endMonth,
        include_school_routes: query.includeSchoolRoutes,
        limit: query.limit,
      })}`,
    ),
  analyticsTrends: (
    metric: AnalyticsMetric,
    routeNo: string | undefined,
    startMonth?: string,
    endMonth?: string,
  ) =>
    fetchJson<AnalyticsTrendResponse>(
      `/analytics/trends${queryString({
        metric,
        route_no: routeNo,
        start_month: startMonth,
        end_month: endMonth,
      })}`,
    ),
  analyticsHeatmap: (query: AnalyticsQuery) =>
    fetchJson<AnalyticsHeatmapResponse>(
      `/analytics/heatmap${queryString({
        metric: query.metric,
        start_month: query.startMonth,
        end_month: query.endMonth,
        include_school_routes: query.includeSchoolRoutes,
        limit: query.limit,
      })}`,
    ),
  analyticsScatter: (
    startMonth?: string,
    endMonth?: string,
    includeSchoolRoutes?: boolean,
    minBoardings = 0,
    limit = 30,
  ) =>
    fetchJson<{
      aggregation: string;
      total: number;
      points: ScatterPoint[];
      correlation: CorrelationResult;
      unit: string;
      definition: string;
      source_family: string;
      warning: string | null;
    }>(
      `/analytics/patronage-vs-performance${queryString({
        start_month: startMonth,
        end_month: endMonth,
        include_school_routes: includeSchoolRoutes,
        min_boardings: minBoardings,
        limit,
      })}`,
    ),
};
