import type {
  NetworkStatus,
  Paginated,
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

function queryString(params: RouteQuery): string {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.mode) search.set("mode", params.mode);
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
  stops: (q?: string) =>
    fetchJson<Paginated<StopSummary>>(
      `/stops${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
};
