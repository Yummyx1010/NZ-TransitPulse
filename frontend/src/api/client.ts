import type {
  ArrivalsResponse,
  NetworkStatus,
  Paginated,
  RealtimeAlertList,
  RealtimeAlertQuery,
  RealtimeStatus,
  RealtimeVehicleList,
  RealtimeVehicleQuery,
  RouteGeometry,
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
};
