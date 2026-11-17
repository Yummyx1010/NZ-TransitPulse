import type { ShapeGeometry } from "../api/types";

export type LatLng = [number, number];

/**
 * Bounds for the map come exclusively from the selected route's shape geometry.
 * Vehicle positions must never decide the viewport: while geometry is loading they
 * would frame the entire city and make the selected route look unrelated.
 */
export function boundsForShape(shape: ShapeGeometry | null): LatLng[] {
  return shape
    ? shape.points.map((point) => [point[0], point[1]] as LatLng)
    : [];
}

export function shouldFitBounds(points: LatLng[]): boolean {
  return points.length > 0;
}
