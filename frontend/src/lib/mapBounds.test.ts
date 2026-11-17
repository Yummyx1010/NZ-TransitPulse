import { describe, expect, it } from "vitest";

import type { ShapeGeometry } from "../api/types";
import { boundsForShape, shouldFitBounds } from "./mapBounds";

const SHAPE: ShapeGeometry = {
  shape_id: "SH1",
  label: "Outbound",
  trip_count: 200,
  direction_id: 0,
  headsign: "To Botany",
  points: [
    [-36.8443, 174.767],
    [-36.847, 174.763],
    [-36.85, 174.76],
  ],
  stops: [],
};

describe("map bounds", () => {
  it("uses the selected shape geometry", () => {
    expect(boundsForShape(SHAPE)).toEqual([
      [-36.8443, 174.767],
      [-36.847, 174.763],
      [-36.85, 174.76],
    ]);
    expect(shouldFitBounds(boundsForShape(SHAPE))).toBe(true);
  });

  it("returns nothing while geometry is loading, even with live vehicles around", () => {
    // This is the regression: vehicles must never be used as bounds fallback.
    expect(boundsForShape(null)).toEqual([]);
    expect(shouldFitBounds(boundsForShape(null))).toBe(false);
  });

  it("keeps the viewport when a shape has no points", () => {
    const empty: ShapeGeometry = { ...SHAPE, points: [] };
    expect(shouldFitBounds(boundsForShape(empty))).toBe(false);
  });
});
