import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import AnalyticsPage from "./AnalyticsPage";
import { OverviewView } from "./analytics/OverviewView";
import { RidershipView } from "./analytics/RidershipView";
import { PerformanceView } from "./analytics/PerformanceView";
import { RelationshipsView } from "./analytics/RelationshipsView";

vi.mock("../api/client", () => ({
  api: {
    analyticsSummary: vi.fn(),
    analyticsMetrics: vi.fn(),
    analyticsNetwork: vi.fn(),
    analyticsRanking: vi.fn(),
    analyticsTrends: vi.fn(),
    analyticsHeatmap: vi.fn(),
    analyticsScatter: vi.fn(),
    officialNetworkMetrics: vi.fn(),
    analyticsRoutes: vi.fn(),
  },
}));

function renderAnalytics(path = "/analytics") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/analytics" element={<AnalyticsPage />}>
            <Route index element={<OverviewView />} />
            <Route path="ridership" element={<RidershipView />} />
            <Route path="performance" element={<PerformanceView />} />
            <Route path="relationships" element={<RelationshipsView />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.analyticsSummary).mockResolvedValue({
    report_count: 13,
    metrics: {
      punctuality: {
        first_month: "2023-07",
        last_month: "2026-10",
        months: 40,
        sufficiency: "strong",
      },
    },
    attribution: "Data source: Auckland Transport, licensed under CC BY 4.0",
  });
  vi.mocked(api.analyticsMetrics).mockResolvedValue({
    total: 4,
    items: {
      punctuality: {
        label: "Official punctuality",
        short_label: "Punctuality",
        unit: "%",
        definition: "AT punctuality definition",
        source_family: "Monthly punctuality and reliability",
        kind: "service",
        higher_is_better: true,
        first_month: "2023-07",
        last_month: "2026-10",
        months: 40,
        sufficiency: "strong",
      },
      boardings: {
        label: "Estimated boardings",
        short_label: "Boardings",
        unit: "passenger trips",
        definition: "Monthly boardings",
        source_family: "AT bus performance reports",
        kind: "ridership",
        higher_is_better: true,
        first_month: "2019-01",
        last_month: "2025-03",
        months: 75,
        sufficiency: "strong",
      },
    },
  });
  vi.mocked(api.analyticsNetwork).mockResolvedValue({
    has_data: true,
    bus_routes: 197,
    stops: 6993,
    scheduled_trips: 32949,
    shape_points: 532630,
    stop_time_rows: 987373,
    avg_stop_times_per_trip: 30,
  });
  vi.mocked(api.analyticsRanking).mockResolvedValue({
    metric: "punctuality",
    total: 1,
    warning: null,
    unit: "%",
    definition: "AT punctuality",
    items: [
      {
        route_no: "70",
        route_name: "Botany To Britomart",
        sample_months: 12,
        first_month: "2024-01",
        last_month: "2024-12",
        first_value: 0.8,
        latest_value: 0.85,
        change: 0.05,
        average_value: 0.825,
      },
    ],
  });
  vi.mocked(api.analyticsTrends).mockResolvedValue({
    metric: "punctuality",
    route_no: null,
    total: 2,
    warning: null,
    unit: "%",
    definition: "AT punctuality",
    items: [
      { month: "2024-01", value: 0.8, sample_count: 10 },
      { month: "2024-02", value: 0.82, sample_count: 10 },
    ],
  });
  vi.mocked(api.analyticsHeatmap).mockResolvedValue({
    metric: "punctuality",
    months: ["2024-01", "2024-02"],
    total: 1,
    warning: null,
    unit: "%",
    items: [
      { route_no: "70", route_name: "Botany To Britomart", values: [0.8, 0.82] },
    ],
  });
  vi.mocked(api.analyticsScatter).mockResolvedValue({
    aggregation: "route_average",
    total: 1,
    correlation: {
      available: false,
      method: "spearman",
      sample_size: 1,
      reason: "At least five routes are required.",
    },
    unit: "boardings vs %",
    definition: "One point per route.",
    source_family: "AT bus performance + punctuality reports",
    warning: null,
    points: [
      {
        route_no: "70",
        route_name: "Botany To Britomart",
        boardings: 55000,
        punctuality: 0.85,
        sample_months: 2,
        first_month: "2024-01",
        last_month: "2024-02",
      },
    ],
  });
  vi.mocked(api.officialNetworkMetrics).mockResolvedValue({
    total: 2,
    items: [
      { month: "2024-01", value: 3000000 },
      { month: "2024-02", value: 3200000 },
    ],
  });
  vi.mocked(api.analyticsRoutes).mockResolvedValue({ total: 0, items: [] });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("analytics views", () => {
  it("opens the overview with separated ridership and attention rankings", async () => {
    renderAnalytics();

    expect(screen.getByRole("heading", { name: "Analytics" })).toBeInTheDocument();
    expect(await screen.findByText("13")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Most used routes" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Routes requiring attention" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ridership" })).toBeInTheDocument();
  });

  it("opens ridership as a separate view with total and average series", async () => {
    renderAnalytics("/analytics/ridership");

    expect(
      await screen.findByRole("heading", { name: "Most used routes" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Ridership trend" }),
    ).toBeInTheDocument();
  });

  it("opens relationships with route-level explanation and seasonality detail", async () => {
    renderAnalytics("/analytics/relationships");

    expect(
      await screen.findByRole("heading", { name: /Are busier routes also more punctual/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Seasonality detail" })).toBeInTheDocument();
  });
});
