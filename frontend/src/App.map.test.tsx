import type { ReactNode } from "react";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "./api/client";
import App from "./App";

const { mapMock } = vi.hoisted(() => ({
  mapMock: {
    invalidateSize: vi.fn(),
    setView: vi.fn(),
    fitBounds: vi.fn(),
    getSize: vi.fn(() => ({ x: 800, y: 600 })),
  },
}));

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TileLayer: () => null,
  CircleMarker: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Marker: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Polyline: () => null,
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useMap: () => mapMock,
}));

vi.mock("./api/client", () => ({
  api: {
    networkStatus: vi.fn(),
    routes: vi.fn(),
    routeStops: vi.fn(),
    routeGeometry: vi.fn(),
    stops: vi.fn(),
    stopArrivals: vi.fn(),
    realtimeStatus: vi.fn(),
    realtimeVehicles: vi.fn(),
    realtimeAlerts: vi.fn(),
  },
}));

const FIRST_ROUTE_POINTS: [number, number][] = [
  [-36.8638, 174.702],
  [-36.85, 174.75],
  [-36.845, 174.771],
];

const SECOND_ROUTE_POINTS: [number, number][] = [
  [-36.8238, 174.608],
  [-36.8, 174.65],
  [-36.7885, 174.673],
];

const EMPTY_ARRIVALS = {
  stop_id: "S1",
  stop_name: "Britomart",
  included_stop_ids: ["S1"],
  route_id: null,
  window_minutes: 60,
  timezone: "Pacific/Auckland",
  realtime_available: true,
  total: 0,
  items: [],
  note: "Scheduled times come from GTFS stop_times.",
  attribution: "Data source: Auckland Transport, licensed under CC BY 4.0",
};

function geometry(routeId: string, points: [number, number][]) {
  return {
    route_id: routeId,
    source: "shapes" as const,
    approximate: false,
    note: "Route geometry from GTFS shapes.txt.",
    shape_count: 1,
    shapes: [
      {
        shape_id: `SH-${routeId}`,
        label: `${routeId} · 200 scheduled trips`,
        trip_count: 200,
        direction_id: 0,
        headsign: "Outbound",
        points,
        stops: [],
      },
    ],
  };
}

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mapMock.getSize.mockImplementation(() => ({ x: 800, y: 600 }));
  vi.mocked(api.networkStatus).mockResolvedValue({
    has_data: true,
    active_feed: null,
    totals: { routes: 2 },
    attribution: "Data source: Auckland Transport, licensed under CC BY 4.0",
  });
  vi.mocked(api.routes).mockResolvedValue({
    items: [
      {
        route_id: "101-202",
        short_name: "101",
        long_name: "101",
        route_type: 3,
        mode: "Bus",
        colour: null,
      },
      {
        route_id: "112-203",
        short_name: "112",
        long_name: "112",
        route_type: 3,
        mode: "Bus",
        colour: null,
      },
    ],
    total: 2,
    limit: 100,
    offset: 0,
  });
  vi.mocked(api.routeGeometry).mockImplementation((routeId: string) =>
    Promise.resolve(
      routeId === "101-202"
        ? geometry("101-202", FIRST_ROUTE_POINTS)
        : geometry("112-203", SECOND_ROUTE_POINTS),
    ),
  );
  vi.mocked(api.routeStops).mockResolvedValue({ items: [], total: 0, limit: 200, offset: 0 });
  vi.mocked(api.stops).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
  vi.mocked(api.stopArrivals).mockResolvedValue(EMPTY_ARRIVALS);
  vi.mocked(api.realtimeStatus).mockResolvedValue({
    configured: true,
    polling: true,
    has_data: true,
    last_success_at: null,
    feed_timestamp: 1794707735,
    vehicle_count: 10,
    trip_update_count: 10,
    alert_count: 1,
    successful_polls: 1,
    failed_polls: 0,
    last_error: null,
    poll_seconds: 30,
    calls_last_7_days: 1,
    weekly_quota: 35000,
    quota_remaining: 34999,
    source: "https://api.at.govt.nz/realtime/legacy",
    attribution: "Data source: Auckland Transport, licensed under CC BY 4.0",
  });
  vi.mocked(api.realtimeVehicles).mockResolvedValue({ items: [], total: 0, limit: 1000 });
  vi.mocked(api.realtimeAlerts).mockResolvedValue({ items: [], total: 0, limit: 100 });
});

afterEach(() => {
  cleanup();
});

describe("map fit when clicking from the unfiltered route list", () => {
  it("fits the map to the first route's shape after its geometry arrives", async () => {
    renderApp();

    fireEvent.click(await screen.findByRole("button", { name: /101/ }));

    await waitFor(() =>
      expect(mapMock.fitBounds).toHaveBeenCalledWith(
        FIRST_ROUTE_POINTS,
        expect.objectContaining({ maxZoom: 13 }),
      ),
    );
    expect(mapMock.setView).not.toHaveBeenCalled();
  });

  it("re-fits to a second route picked from the same unfiltered list", async () => {
    renderApp();

    fireEvent.click(await screen.findByRole("button", { name: /101/ }));
    await waitFor(() =>
      expect(mapMock.fitBounds).toHaveBeenCalledWith(
        FIRST_ROUTE_POINTS,
        expect.anything(),
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: /112/ }));
    await waitFor(() =>
      expect(mapMock.fitBounds).toHaveBeenLastCalledWith(
        SECOND_ROUTE_POINTS,
        expect.anything(),
      ),
    );
  });
});
