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

  it("throws a descriptive error on a failed response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));

    await expect(fetchJson("/network/status")).rejects.toThrow("Request failed (503)");
  });
});
