import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RidershipTrendChart } from "./RidershipTrendChart";
import { RelationshipScatter } from "./RelationshipScatter";
import { SeasonalityHeatmap } from "./SeasonalityHeatmap";

afterEach(cleanup);

describe("chart interactions", () => {
  it("shows a selected ridership value after clicking or pressing a point", () => {
    const renderChart = () =>
      render(
        <RidershipTrendChart
          totals={[
            { month: "2024-01", value: 3000000 },
            { month: "2024-02", value: 3200000 },
          ]}
          averages={[]}
        />,
      );

    const { unmount } = renderChart();
    fireEvent.click(screen.getByRole("button", { name: /2024-02/ }));
    expect(screen.getAllByText("3,200,000").length).toBeGreaterThan(1);
    unmount();

    renderChart();
    const point = screen.getByRole("button", { name: /2024-01/ });
    fireEvent.keyDown(point, { key: "Enter" });
    expect(screen.getByText("3,000,000")).toBeInTheDocument();
  });

  it("shows route details and correlation status in the relationship chart", () => {
    const onSelectRoute = vi.fn();
    render(
      <RelationshipScatter
        points={[
          {
            route_no: "70",
            route_name: "Botany To Britomart",
            boardings: 55000,
            punctuality: 0.85,
            sample_months: 2,
            first_month: "2024-01",
            last_month: "2024-02",
          },
        ]}
        correlation={{
          available: false,
          method: "spearman",
          sample_size: 1,
          reason: "At least five routes are required.",
        }}
        selectedRoute={null}
        onSelectRoute={onSelectRoute}
      />,
    );

    expect(screen.getByText(/At least five routes are required/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Route 70/ }));
    expect(screen.getByText("2024-01 – 2024-02")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Track route 70 across views" }));
    expect(onSelectRoute).toHaveBeenCalledWith("70");
  });

  it("shows a selected heatmap cell with explicit missing values", () => {
    render(
      <SeasonalityHeatmap
        metric="punctuality"
        months={["2024-01", "2024-02"]}
        items={[
          {
            route_no: "70",
            route_name: "Botany To Britomart",
            values: [0.8, null],
          },
        ]}
        normalize={false}
      />,
    );

    expect(screen.getByText("–")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /70 2024-01/ }));
    expect(screen.getAllByText("80.0%").length).toBeGreaterThan(1);
  });
});
