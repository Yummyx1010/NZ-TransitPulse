import { describe, expect, it } from "vitest";

import {
  delayStatusClass,
  displayRouteName,
  displayStopName,
  formatCoordinate,
  formatDelay,
  formatFeedTime,
  formatMinutesAway,
  modeClass,
} from "./format";
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

  it("formats coordinates and the bus mode class", () => {
    expect(formatCoordinate(-36.8443)).toBe("-36.84430");
    expect(modeClass("Bus")).toBe("badge badge-bus");
  });

  it("formats feed timestamps in Auckland time", () => {
    expect(formatFeedTime(null)).toBe("No feed yet");
    expect(formatFeedTime(undefined)).toBe("No feed yet");
    const formatted = formatFeedTime(1794707735);
    expect(formatted).not.toBe("No feed yet");
    expect(formatted.length).toBeGreaterThan(0);
  });

  it("formats ETA minutes, delays and status classes", () => {
    expect(formatMinutesAway(0)).toBe("Due");
    expect(formatMinutesAway(17)).toBe("17 min");
    expect(formatDelay(120)).toBe("+2 min");
    expect(formatDelay(-120)).toBe("-2 min");
    expect(formatDelay(0)).toBe("On time");
    expect(formatDelay(null)).toBe("timetable only");
    expect(delayStatusClass("On time")).toBe("delay-badge delay-on-time");
    expect(delayStatusClass("Delayed")).toBe("delay-badge delay-delayed");
  });
});
