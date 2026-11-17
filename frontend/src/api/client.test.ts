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

  it("throws a descriptive error on a failed response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));

    await expect(fetchJson("/network/status")).rejects.toThrow("Request failed (503)");
  });
});
