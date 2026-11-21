import { createElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { RouteContextProvider } from "../hooks/useRouteContext";
import { RouteIntelligencePage } from "./RouteIntelligencePage";

vi.mock("../api/client", () => ({
  api: {
    analyticsRoutes: vi.fn(),
    routeIntelligence: vi.fn(),
    routeGeometry: vi.fn(),
    realtimeVehicles: vi.fn(),
    realtimeAlerts: vi.fn(),
    analyticsTrends: vi.fn(),
  },
}));

vi.mock("../components/StopMap", () => ({
  StopMap: () => createElement("div", { "data-testid": "route-map" }),
}));

function renderRoute() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/routes/70"]}>
        <RouteContextProvider>
          <Routes>
            <Route path="/routes/:routeNo" element={<RouteIntelligencePage />} />
          </Routes>
        </RouteContextProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.analyticsRoutes).mockResolvedValue({
    total: 1,
    items: [
      {
        route_no: "70",
        route_ids: ["70-205"],
        route_name: "Botany To Britomart",
        matched_in_gtfs: true,
      },
    ],
  });
  vi.mocked(api.routeIntelligence).mockResolvedValue({
    route_no: "70",
    route_name: "Botany To Britomart",
    route_ids: ["70-205"],
    matched_in_gtfs: true,
    has_official_data: true,
    changes: [
      {
        metric: "punctuality",
        label: "Official punctuality",
        unit: "%",
        source_family: "Monthly punctuality and reliability",
        definition: "AT official punctuality",
        definition_note: null,
        first_month: "2024-01",
        last_month: "2024-02",
        sample_months: 2,
        sufficiency: "limited",
        latest_value: 0.9,
        latest_month: "2024-02",
        previous_value: 0.8,
        previous_month: "2024-01",
        change: 0.1,
        rolling_12m_average: 0.85,
        families: ["punctuality_report"],
      },
      {
        metric: "boardings",
        label: "Estimated boardings",
        unit: "passenger trips",
        source_family: "AT bus performance reports",
        definition: "Monthly boardings",
        definition_note: null,
        first_month: "2024-01",
        last_month: "2024-02",
        sample_months: 2,
        sufficiency: "limited",
        latest_value: 60000,
        latest_month: "2024-02",
        previous_value: 50000,
        previous_month: "2024-01",
        change: 10000,
        rolling_12m_average: 55000,
        families: ["bus_performance_report"],
      },
    ],
    seasonality: {
      punctuality: { months: ["2024-01", "2024-02"], values: [0.8, 0.9] },
    },
    warnings: [],
    attribution: "Data source: Auckland Transport, licensed under CC BY 4.0",
  });
  vi.mocked(api.routeGeometry).mockResolvedValue({
    route_id: "70-205",
    source: "shapes",
    approximate: false,
    note: "Route geometry from GTFS shapes.txt.",
    shape_count: 1,
    shapes: [
      {
        shape_id: "SH70",
        label: "Botany To Britomart",
        trip_count: 20,
        direction_id: 1,
        headsign: "Botany",
        points: [
          [-36.84, 174.76],
          [-36.85, 174.77],
        ],
        stops: [],
      },
    ],
  });
  vi.mocked(api.realtimeVehicles).mockResolvedValue({
    items: [],
    total: 4,
    limit: 200,
  });
  vi.mocked(api.realtimeAlerts).mockResolvedValue({ items: [], total: 1, limit: 5 });
  vi.mocked(api.analyticsTrends).mockImplementation(async (metric) => ({
    metric,
    route_no: "70",
    total: 2,
    items: [
      { month: "2024-01", value: 0.8, sample_count: 1 },
      { month: "2024-02", value: 0.9, sample_count: 1 },
    ],
  }));
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("RouteIntelligencePage", () => {
  it("connects map, live status and evidence-based changes for a route", async () => {
    renderRoute();

    expect(screen.getByRole("heading", { name: "Route Intelligence" })).toBeInTheDocument();
    expect(await screen.findByTestId("route-map")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What Changed?" })).toBeInTheDocument();
    expect(screen.getByText("+10.0 percentage points")).toBeInTheDocument();
    expect(screen.getByText("Current buses")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Current service status" }),
    ).toBeInTheDocument();
    expect(api.routeGeometry).toHaveBeenCalledWith("70-205");
    expect(api.realtimeVehicles).toHaveBeenCalledWith({
      route_id: "70-205",
      mode: "Bus",
      limit: 200,
    });
  });
});
