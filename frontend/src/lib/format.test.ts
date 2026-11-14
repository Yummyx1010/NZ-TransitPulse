import { describe, expect, it } from "vitest";

import { displayRouteName, displayStopName, formatCoordinate, modeClass } from "./format";
import type { RouteSummary, StopSummary } from "../api/types";

const route: RouteSummary = {
  route_id: "R1",
  short_name: "18",
  long_name: "New North Road",
  route_type: 3,
  mode: "Bus",
  colour: null,
};

const stop: StopSummary = {
  stop_id: "S1",
  code: "1001",
  name: "Britomart",
  lat: -36.8443,
  lon: 174.767,
  location_type: 0,
};

describe("formatting helpers", () => {
  it("combines short and long route names", () => {
    expect(displayRouteName(route)).toBe("18 · New North Road");
    expect(displayRouteName({ ...route, long_name: "18" })).toBe("18");
    expect(displayRouteName({ ...route, short_name: "" })).toBe("New North Road");
  });

  it("appends a stop code when available", () => {
    expect(displayStopName(stop)).toBe("Britomart (1001)");
    expect(displayStopName({ ...stop, code: null })).toBe("Britomart");
  });

  it("formats coordinates and mode classes", () => {
    expect(formatCoordinate(-36.8443)).toBe("-36.84430");
    expect(modeClass("Ferry")).toBe("badge badge-ferry");
    expect(modeClass("Light Rail")).toBe("badge badge-light-rail");
  });
});
