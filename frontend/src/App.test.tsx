import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { api } from "./api/client";

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
    routeStops: vi.fn().mockResolvedValue({
      items: [
        {
          stop_id: "S1",
          code: "1001",
          name: "Britomart",
          lat: -36.8443,
          lon: 174.767,
          location_type: 0,
        },
      ],
      total: 1,
      limit: 200,
      offset: 0,
    }),
    stops: vi.fn(),
  },
}));

vi.mock("./components/StopMap", () => ({
  StopMap: ({ stops }: { stops: unknown[] }) => (
    <div data-testid="map">stops: {stops.length}</div>
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

  it("loads and lists stops when a route is selected", async () => {
    renderApp();

    fireEvent.click(await screen.findByRole("button", { name: /18 · New North Road/ }));

    expect(await screen.findByText("Britomart (1001)")).toBeInTheDocument();
    expect(api.routeStops).toHaveBeenCalledWith("R1");
    expect(screen.getByTestId("map")).toHaveTextContent("stops: 1");
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
