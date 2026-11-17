import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import type { ArrivalsResponse, StopSummary } from "../api/types";
import { PassengerBoard } from "./PassengerBoard";

const STOP: StopSummary = {
  stop_id: "S1",
  code: "1001",
  name: "Britomart",
  lat: -36.8443,
  lon: 174.767,
  location_type: 0,
};

const ARRIVALS: ArrivalsResponse = {
  stop_id: "S1",
  stop_name: "Britomart",
  included_stop_ids: ["S1"],
  route_id: null,
  window_minutes: 60,
  timezone: "Pacific/Auckland",
  realtime_available: true,
  total: 2,
  items: [
    {
      trip_id: "T1",
      route_id: "70-205",
      route_short_name: "70",
      headsign: "To Botany",
      direction_id: 0,
      scheduled_seconds: 29700,
      scheduled_time: "08:15:00",
      predicted_seconds: 29820,
      predicted_time: "08:17:00",
      delay_seconds: 120,
      minutes_away: 17,
      status: "Delayed",
      source: "realtime",
    },
    {
      trip_id: "T4",
      route_id: "70-205",
      route_short_name: "70",
      headsign: "To Britomart",
      direction_id: 1,
      scheduled_seconds: 32400,
      scheduled_time: "09:00:00",
      predicted_seconds: null,
      predicted_time: null,
      delay_seconds: null,
      minutes_away: 60,
      status: "Scheduled",
      source: "schedule",
    },
  ],
  note: "Service calendars are not imported yet.",
  attribution: "Data source: Auckland Transport, licensed under CC BY 4.0",
};

const ALERTS = {
  items: [
    {
      alert_id: "a1",
      cause: "CONSTRUCTION",
      effect: "STOP_MOVED",
      header: "Stop moved: Route 70",
      description: "Temporary stop relocation near Britomart.",
      active_periods: [],
      route_ids: ["70-205"],
    },
  ],
  total: 1,
  limit: 100,
};

vi.mock("../api/client", () => ({
  api: {
    stops: vi.fn(),
    stopArrivals: vi.fn(),
    realtimeAlerts: vi.fn(),
  },
}));

function renderBoard(routeId: string | null = null) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <PassengerBoard routeId={routeId} routeLabel="Route 70" />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.stops).mockResolvedValue({ items: [STOP], total: 1, limit: 50, offset: 0 });
  vi.mocked(api.stopArrivals).mockResolvedValue(ARRIVALS);
  vi.mocked(api.realtimeAlerts).mockResolvedValue(ALERTS);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Passenger board", () => {
  it("renders the stop search prompt and bus-only alerts", async () => {
    renderBoard();

    expect(screen.getByText("Next bus arrivals")).toBeInTheDocument();
    expect(screen.getByText(/Pick a stop above/)).toBeInTheDocument();
    expect(await screen.findByText("Stop moved: Route 70")).toBeInTheDocument();
    expect(api.realtimeAlerts).toHaveBeenCalledWith({
      mode: "Bus",
      route_id: undefined,
    });
  });

  it("hides the stop suggestions after a stop is chosen", async () => {
    renderBoard();

    fireEvent.change(screen.getByPlaceholderText("e.g. Britomart or Newmarket"), {
      target: { value: "Brit" },
    });
    expect(await screen.findByTestId("stop-options")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Britomart/ }));

    await waitFor(() =>
      expect(screen.queryByTestId("stop-options")).not.toBeInTheDocument(),
    );
    expect(screen.getByPlaceholderText("e.g. Britomart or Newmarket")).toHaveValue("");
  });

  it("shows scheduled and predicted arrivals after choosing a stop", async () => {
    renderBoard();

    fireEvent.change(screen.getByPlaceholderText("e.g. Britomart or Newmarket"), {
      target: { value: "Brit" },
    });
    fireEvent.click(await screen.findByRole("button", { name: /Britomart/ }));

    expect(await screen.findByText("17 min")).toBeInTheDocument();
    expect(screen.getByText("Delayed")).toBeInTheDocument();
    expect(screen.getByText("Scheduled")).toBeInTheDocument();
    expect(screen.getByText(/08:17:00/)).toBeInTheDocument();
    expect(api.stopArrivals).toHaveBeenCalledWith("S1", {
      route_id: undefined,
      minutes: 60,
      limit: 20,
    });
  });

  it("scopes arrivals and stop search to the selected route by default", async () => {
    renderBoard("R1");

    expect(screen.getByText("Route 70 arrivals")).toBeInTheDocument();
    expect(screen.getByTestId("route-filter")).toHaveTextContent(
      "Show all buses at this stop",
    );
    fireEvent.change(screen.getByPlaceholderText("e.g. Britomart or Newmarket"), {
      target: { value: "Brit" },
    });
    fireEvent.click(await screen.findByRole("button", { name: /Britomart/ }));

    await waitFor(() =>
      expect(api.stopArrivals).toHaveBeenCalledWith("S1", {
        route_id: "R1",
        minutes: 60,
        limit: 20,
      }),
    );
    expect(api.stops).toHaveBeenCalledWith("Brit", "R1");
  });

  it("can show all buses at the stop via the explicit toggle", async () => {
    renderBoard("R1");

    fireEvent.click(screen.getByTestId("route-filter"));
    fireEvent.change(screen.getByPlaceholderText("e.g. Britomart or Newmarket"), {
      target: { value: "Brit" },
    });
    fireEvent.click(await screen.findByRole("button", { name: /Britomart/ }));

    await waitFor(() =>
      expect(api.stopArrivals).toHaveBeenCalledWith("S1", {
        route_id: undefined,
        minutes: 60,
        limit: 20,
      }),
    );
    expect(api.stops).toHaveBeenCalledWith("Brit", undefined);
  });

  it("explains an empty route-scoped board", async () => {
    vi.mocked(api.stopArrivals).mockResolvedValue({ ...ARRIVALS, total: 0, items: [] });
    renderBoard("R1");

    fireEvent.change(screen.getByPlaceholderText("e.g. Britomart or Newmarket"), {
      target: { value: "Brit" },
    });
    fireEvent.click(await screen.findByRole("button", { name: /Britomart/ }));

    expect(
      await screen.findByText(/No Route 70 buses in the next 60 minutes/),
    ).toBeInTheDocument();
  });

  it("explains when there are no upcoming buses", async () => {
    vi.mocked(api.stopArrivals).mockResolvedValue({ ...ARRIVALS, total: 0, items: [] });
    renderBoard();

    fireEvent.change(screen.getByPlaceholderText("e.g. Britomart or Newmarket"), {
      target: { value: "Brit" },
    });
    fireEvent.click(await screen.findByRole("button", { name: /Britomart/ }));

    expect(
      await screen.findByText(/No bus arrivals in the next 60 minutes/),
    ).toBeInTheDocument();
  });
});
