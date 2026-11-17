import type {
  NetworkStatus,
  Paginated,
  RealtimeStatus,
  RealtimeVehicleList,
  RealtimeVehicleQuery,
  RouteGeometry,
  RouteQuery,
  RouteSummary,
  StopSummary,
} from "./types";

const BASE = "/api/v1";

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}): ${path}`);
  }
  return (await response.json()) as T;
}

function queryString(params: RouteQuery | RealtimeVehicleQuery): string {
  const search = new URLSearchParams();
  if ("q" in params && params.q) search.set("q", params.q);
  if ("mode" in params && params.mode) search.set("mode", params.mode);
  if ("route_id" in params && params.route_id) search.set("route_id", params.route_id);
  if ("shape_id" in params && params.shape_id) search.set("shape_id", params.shape_id);
  if ("bbox" in params && params.bbox) search.set("bbox", params.bbox);
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
  stops: (q?: string) =>
    fetchJson<Paginated<StopSummary>>(
      `/stops${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
  realtimeStatus: () => fetchJson<RealtimeStatus>("/realtime/status"),
  realtimeVehicles: (params: RealtimeVehicleQuery = {}) =>
    fetchJson<RealtimeVehicleList>(`/realtime/vehicles${queryString(params)}`),
};
