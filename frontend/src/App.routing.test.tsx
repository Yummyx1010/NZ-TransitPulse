import { createElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const pageTestId = (name: string) => `${name}-page`;

vi.mock("./pages/NetworkOverviewPage", () => ({
  NetworkOverviewPage: () => createElement("div", { "data-testid": "network-overview-page" }),
}));
vi.mock("./pages/LiveMapPage", () => ({
  default: () => createElement("div", { "data-testid": "live-network-page" }),
}));
vi.mock("./pages/RouteIntelligencePage", () => ({
  RouteIntelligencePage: () => createElement("div", { "data-testid": "route-intelligence-page" }),
}));
vi.mock("./pages/ServiceHealthPage", () => ({
  ServiceHealthPage: () => createElement("div", { "data-testid": "service-health-page" }),
}));
vi.mock("./pages/RouteComparisonPage", () => ({
  RouteComparisonPage: () => createElement("div", { "data-testid": "route-comparison-page" }),
}));
vi.mock("./pages/DataMethodologyPage", () => ({
  DataMethodologyPage: () => createElement("div", { "data-testid": "data-methodology-page" }),
}));
vi.mock("./pages/AnalyticsPage", () => ({
  default: () => createElement("div", { "data-testid": "analytics-page" }),
}));

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  window.history.pushState({}, "", "/");
});

afterEach(() => {
  cleanup();
  window.history.pushState({}, "", "/");
});

describe("v0.6.1 application routing", () => {
  it("opens Network Overview as the default module", () => {
    renderApp();

    expect(screen.getByRole("complementary", { name: "Main navigation" })).toBeInTheDocument();
    expect(screen.getByTestId("network-overview-page")).toBeInTheDocument();
  });

  it("exposes all product modules in the sidebar", () => {
    renderApp();

    expect(screen.getByRole("link", { name: "Network Overview" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Live Network" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Route Intelligence" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Service Health" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Route Comparison" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ridership" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Performance" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Relationships" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Data and Methodology" })).toBeInTheDocument();
  });

  it("navigates between overview, live network and route modules", () => {
    renderApp();

    fireEvent.click(screen.getByRole("link", { name: "Live Network" }));
    expect(screen.getByTestId("live-network-page")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Route Intelligence" }));
    expect(screen.getByTestId("route-intelligence-page")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Service Health" }));
    expect(screen.getByTestId("service-health-page")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Route Comparison" }));
    expect(screen.getByTestId("route-comparison-page")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Data and Methodology" }));
    expect(screen.getByTestId("data-methodology-page")).toBeInTheDocument();
  });

  it("keeps the legacy analytics route reachable", () => {
    window.history.pushState({}, "", "/analytics");
    renderApp();

    expect(screen.getByTestId(pageTestId("analytics"))).toBeInTheDocument();
  });
});
