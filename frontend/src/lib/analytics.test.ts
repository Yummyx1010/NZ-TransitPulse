import { describe, expect, it } from "vitest";

import {
  formatChange,
  formatMetricValue,
  heatColor,
  listMonthValues,
  metricLabel,
  monthLabel,
  MONTH_NAMES,
} from "./analytics";

describe("analytics formatting", () => {
  it("formats punctuality and reliability as percentages", () => {
    expect(formatMetricValue("punctuality", 0.8755)).toBe("87.6%");
    expect(formatMetricValue("reliability", null)).toBe("n/a");
  });

  it("formats boardings and service-hour values differently", () => {
    expect(formatMetricValue("boardings", 54321)).toBe("54,321");
    expect(formatMetricValue("boardings_per_service_hour", 12.345)).toBe("12.3");
  });

  it("formats changes in percentage points and counts", () => {
    expect(formatChange("punctuality", 0.0523)).toBe("+5.2pp");
    expect(formatChange("punctuality", -0.021)).toBe("-2.1pp");
    expect(formatChange("boardings", 1200)).toBe("+1,200");
  });

  it("labels metrics and assigns heat colours", () => {
    expect(metricLabel("boardings_per_service_hour")).toBe("Boardings / service hour");
    expect(heatColor("punctuality", 0.95)).toBe("heat-4");
    expect(heatColor("punctuality", 0.2)).toBe("heat-0");
    expect(heatColor("punctuality", null)).toBe("heat-empty");
  });

  it("generates English month labels without browser locale", () => {
    expect(MONTH_NAMES.slice(0, 3)).toEqual(["Jan", "Feb", "Mar"]);
    expect(monthLabel("2026-11")).toBe("Nov 2026");
    expect(listMonthValues("2024-11", "2025-02")).toEqual([
      "2024-11",
      "2024-12",
      "2025-01",
      "2025-02",
    ]);
  });
});
