import { describe, expect, it } from "vitest";

import { prepareDisplayGeometry } from "./geometry";

describe("prepareDisplayGeometry", () => {
  it("reduces collinear points to a straight segment", () => {
    const points: [number, number][] = [
      [-36.85, 174.76],
      [-36.85005, 174.7601],
      [-36.8501, 174.7602],
      [-36.85015, 174.7603],
      [-36.8502, 174.7604],
    ];

    const result = prepareDisplayGeometry(points);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual(points[0]);
    expect(result[result.length - 1]).toEqual(points[points.length - 1]);
  });

  it("rounds a sharp corner while preserving endpoints", () => {
    const points: [number, number][] = [
      [-36.85, 174.76],
      [-36.85, 174.761],
      [-36.851, 174.761],
    ];

    const result = prepareDisplayGeometry(points);

    expect(result.length).toBeGreaterThan(3);
    expect(result[0]).toEqual(points[0]);
    expect(result[result.length - 1]).toEqual(points[points.length - 1]);
    expect(result).not.toContainEqual(points[1]);
  });

  it("does not invent geometry for short or simple lines", () => {
    const points: [number, number][] = [
      [-36.85, 174.76],
      [-36.8502, 174.7602],
    ];

    expect(prepareDisplayGeometry(points)).toEqual(points);
  });
});
