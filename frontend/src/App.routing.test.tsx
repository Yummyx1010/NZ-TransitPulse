import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./pages/LiveMapPage", () => ({
  default: () => createElement("div", { "data-testid": "live-map-page" }),
}));
vi.mock("./pages/AnalyticsPage", () => ({
  default: () => createElement("div", { "data-testid": "analytics-page" }),
}));

beforeEach(() => {
  window.history.pushState({}, "", "/");
});

afterEach(() => {
  cleanup();
  window.history.pushState({}, "", "/");
});

describe("application routing", () => {
  it("opens the live map first inside a left sidebar shell", () => {
    render(<App />);

    expect(screen.getByRole("complementary", { name: "Main navigation" })).toBeInTheDocument();
    expect(screen.getByText("Prediction models")).toBeInTheDocument();
    expect(screen.getByText("Network analysis")).toBeInTheDocument();
    expect(screen.getByTestId("live-map-page")).toBeInTheDocument();
    expect(screen.queryByTestId("analytics-page")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Analytics" }));

    expect(screen.getByTestId("analytics-page")).toBeInTheDocument();
    expect(screen.queryByTestId("live-map-page")).not.toBeInTheDocument();
  });

  it("returns to the live map from analytics", () => {
    window.history.pushState({}, "", "/analytics");
    render(<App />);

    fireEvent.click(screen.getByRole("link", { name: "Live map" }));

    expect(screen.getByTestId("live-map-page")).toBeInTheDocument();
  });
});
