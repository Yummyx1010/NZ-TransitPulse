import { afterEach, describe, expect, it, vi } from "vitest";

import { api, fetchJson } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API client", () => {
  it("builds a routes query string", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) });
    vi.stubGlobal("fetch", fetchMock);

    await api.routes({ q: "18", mode: "Bus", limit: 25 });

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/routes?q=18&mode=Bus&limit=25");
  });

  it("encodes route ids in stop requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) });
    vi.stubGlobal("fetch", fetchMock);

    await api.routeStops("R 1/2");

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/routes/R%201%2F2/stops");
  });

  it("builds a route-scoped stop search query", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.stops("Britomart", "70-205");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/stops?q=Britomart&route_id=70-205",
    );
  });

  it("builds a route geometry request", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.routeGeometry("R 1/2");

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/routes/R%201%2F2/geometry");
  });

  it("builds a realtime vehicles query", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.realtimeVehicles({ route_id: "70-205", limit: 300 });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/realtime/vehicles?route_id=70-205&limit=300",
    );
  });

  it("includes the bus-only mode filter", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.realtimeVehicles({ mode: "Bus", route_id: "70-205", limit: 300 });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/realtime/vehicles?mode=Bus&route_id=70-205&limit=300",
    );
  });

  it("includes the selected shape filter", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.realtimeVehicles({
      mode: "Bus",
      route_id: "70-205",
      shape_id: "1153-07006-7290bbd3",
      limit: 300,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/realtime/vehicles?mode=Bus&route_id=70-205&shape_id=1153-07006-7290bbd3&limit=300",
    );
  });

  it("requests realtime status", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.realtimeStatus();

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/realtime/status");
  });

  it("builds a stop arrivals query", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.stopArrivals("9103-0e65d9b8", {
      route_id: "70-205",
      minutes: 60,
      limit: 20,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/stops/9103-0e65d9b8/arrivals?route_id=70-205&minutes=60&limit=20",
    );
  });

  it("builds a bus-only service alerts query", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.realtimeAlerts({ mode: "Bus", route_id: "70-205" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/realtime/alerts?mode=Bus&route_id=70-205",
    );
  });

  it("builds analytics ranking and trend queries", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.analyticsRanking({
      metric: "punctuality",
      startMonth: "2024-01",
      endMonth: "2024-12",
      includeSchoolRoutes: false,
      limit: 10,
    });
    await api.analyticsTrends("reliability", "70", "2024-01", "2024-12");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/analytics/route-ranking?metric=punctuality&start_month=2024-01&end_month=2024-12&include_school_routes=false&limit=10",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/analytics/trends?metric=reliability&route_no=70&start_month=2024-01&end_month=2024-12",
    );
  });

  it("builds a route-averaged scatter query", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.analyticsScatter("2019-01", "2026-10", false, 1000, 24);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/analytics/patronage-vs-performance?start_month=2019-01&end_month=2026-10&include_school_routes=false&min_boardings=1000&limit=24",
    );
  });

  it("builds a route intelligence URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await api.routeIntelligence("70");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/analytics/routes/70/intelligence",
    );
  });

  it("throws a descriptive error on a failed response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));

    await expect(fetchJson("/network/status")).rejects.toThrow("Request failed (503)");
  });
});
