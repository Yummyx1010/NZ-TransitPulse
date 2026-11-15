import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { api } from "./api/client";
import type { RouteGeometry, ShapeGeometry, StopSummary } from "./api/types";

const BRITOMART: StopSummary = {
  stop_id: "S1",
  code: "1001",
  name: "Britomart",
  lat: -36.8443,
  lon: 174.767,
  location_type: 0,
};
const NEWMARKET: StopSummary = {
  stop_id: "S2",
  code: "1002",
  name: "Newmarket",
  lat: -36.871,
  lon: 174.777,
  location_type: 0,
};

const SHAPE_A: ShapeGeometry = {
  shape_id: "SH1",
  label: "City Centre · 2 trips",
  trip_count: 2,
  direction_id: 0,
  headsign: "City Centre",
  points: [
    [-36.8443, 174.767],
    [-36.847, 174.763],
    [-36.85, 174.76],
  ],
  stops: [NEWMARKET, BRITOMART],
};
const SHAPE_B: ShapeGeometry = {
  shape_id: "SH4",
  label: "Newmarket · 1 trip",
  trip_count: 1,
  direction_id: 1,
  headsign: "Newmarket",
  points: [
    [-36.871, 174.777],
    [-36.86, 174.77],
  ],
  stops: [BRITOMART, NEWMARKET],
};
const GEOMETRY: RouteGeometry = {
  route_id: "R1",
  source: "shapes",
  approximate: false,
  note: "Route geometry from GTFS shapes.txt (actual road geometry).",
  shape_count: 2,
  shapes: [SHAPE_A, SHAPE_B],
};

vi.mock("./api/client", () => ({
  api: {
    networkStatus: vi.fn().mockResolvedValue({
      has_data: true,
      active_feed: null,
      totals: { routes: 2, stops: 2 },
      attribution: "Data source: Auckland Transport, licensed under CC BY 4.0",
    }),
    routes: vi.fn().mockResolvedValue({
      items: [
        {
          route_id: "R1",
          short_name: "18",
          long_name: "New North Road",
          route_type: 3,
          mode: "Bus",
          colour: "FF0000",
        },
        {
          route_id: "R2",
          short_name: "WEST",
          long_name: "Western Line",
          route_type: 2,
          mode: "Rail",
          colour: "0000FF",
        },
      ],
      total: 2,
      limit: 100,
      offset: 0,
    }),
    routeStops: vi.fn(),
    routeGeometry: vi.fn(),
    stops: vi.fn(),
  },
}));

vi.mock("./components/StopMap", () => ({
  StopMap: ({
    shape,
    approximate,
    note,
  }: {
    shape: ShapeGeometry | null;
    approximate: boolean;
    note: string;
  }) => (
    <div data-testid="map">
      <span data-testid="map-shape">{shape?.shape_id ?? "none"}</span>
      <span data-testid="map-points">{shape?.points.length ?? 0}</span>
      <span data-testid="map-stops">{shape?.stops.length ?? 0}</span>
      {approximate ? (
        <span data-testid="approx-label">Approximate route — {note}</span>
      ) : null}
    </div>
  ),
}));

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

function stopNames(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll(".stop-list li")).map((item) =>
    (item.textContent ?? "").trim(),
  );
}

beforeEach(() => {
  vi.mocked(api.routeGeometry).mockResolvedValue(GEOMETRY);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Network explorer", () => {
  it("renders the header, routes and data attribution", async () => {
    renderApp();

    expect(screen.getByRole("heading", { name: "NZ TransitPulse" })).toBeInTheDocument();
    expect(await screen.findByText("18 · New North Road")).toBeInTheDocument();
    expect(screen.getByText("WEST · Western Line")).toBeInTheDocument();
    expect(screen.getByText(/licensed under CC BY 4.0/)).toBeInTheDocument();
  });

  it("draws only the selected route's default shape and its ordered stops", async () => {
    const { container } = renderApp();

    fireEvent.click(await screen.findByRole("button", { name: /18 · New North Road/ }));

    await waitFor(() =>
      expect(screen.getByTestId("map-shape")).toHaveTextContent("SH1"),
    );
    expect(api.routeGeometry).toHaveBeenCalledWith("R1");
    expect(screen.getByTestId("map-points")).toHaveTextContent("3");
    expect(screen.getByTestId("map-stops")).toHaveTextContent("2");
    await screen.findByText("Britomart (1001)");
    expect(stopNames(container)[0]).toContain("Newmarket");
    expect(stopNames(container)[1]).toContain("Britomart");
    expect(screen.queryByTestId("approx-label")).not.toBeInTheDocument();
  });

  it("switches route patterns without mixing shapes", async () => {
    const { container } = renderApp();
    fireEvent.click(await screen.findByRole("button", { name: /18 · New North Road/ }));
    await waitFor(() =>
      expect(screen.getByTestId("map-shape")).toHaveTextContent("SH1"),
    );

    fireEvent.change(screen.getByLabelText("Route pattern"), {
      target: { value: "SH4" },
    });

    await waitFor(() =>
      expect(screen.getByTestId("map-shape")).toHaveTextContent("SH4"),
    );
    expect(screen.getByTestId("map-points")).toHaveTextContent("2");
    expect(stopNames(container)[0]).toContain("Britomart");
    expect(stopNames(container)[1]).toContain("Newmarket");
  });

  it("labels the stop_times fallback as an approximate route", async () => {
    vi.mocked(api.routeGeometry).mockResolvedValueOnce({
      ...GEOMETRY,
      source: "stop_times",
      approximate: true,
      note: "Approximate route: lines follow scheduled stop order, not actual road geometry.",
      shape_count: 1,
      shapes: [SHAPE_A],
    });
    renderApp();

    fireEvent.click(await screen.findByRole("button", { name: /18 · New North Road/ }));

    expect(await screen.findByTestId("approx-label")).toHaveTextContent(
      "not actual road geometry",
    );
    expect(screen.getByTestId("map-shape")).toHaveTextContent("SH1");
  });

  it("passes the search query to the API", async () => {
    renderApp();
    await screen.findByText("18 · New North Road");

    fireEvent.change(screen.getByPlaceholderText("e.g. 18 or Western"), {
      target: { value: "Western" },
    });

    await waitFor(() => {
      expect(api.routes).toHaveBeenCalledWith({ q: "Western", mode: undefined, limit: 100 });
    });
  });
});
