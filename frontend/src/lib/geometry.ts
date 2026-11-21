export type GeometryPoint = [number, number];

interface GeometryOptions {
  simplifyToleranceMeters?: number;
  cornerRadiusMeters?: number;
  minCornerAngleDegrees?: number;
}

const EARTH_RADIUS = 6_371_000;

function toMeters(point: GeometryPoint, originLat: number): [number, number] {
  const latRad = (point[0] * Math.PI) / 180;
  const originRad = (originLat * Math.PI) / 180;
  return [
    EARTH_RADIUS * (point[1] * Math.PI) / 180 * Math.cos(originRad),
    EARTH_RADIUS * latRad,
  ];
}

function distanceMeters(a: GeometryPoint, b: GeometryPoint, originLat: number): number {
  const pa = toMeters(a, originLat);
  const pb = toMeters(b, originLat);
  return Math.hypot(pb[0] - pa[0], pb[1] - pa[1]);
}

function perpendicularDistance(
  point: GeometryPoint,
  start: GeometryPoint,
  end: GeometryPoint,
  originLat: number,
): number {
  const p = toMeters(point, originLat);
  const a = toMeters(start, originLat);
  const b = toMeters(end, originLat);
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  const t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / lengthSquared;
  const clamped = Math.max(0, Math.min(1, t));
  return Math.hypot(p[0] - (a[0] + clamped * dx), p[1] - (a[1] + clamped * dy));
}

function simplifyRdp(
  points: GeometryPoint[],
  tolerance: number,
  originLat: number,
): GeometryPoint[] {
  if (points.length <= 2) return points;
  let farthestIndex = 0;
  let farthestDistance = 0;
  for (let index = 1; index < points.length - 1; index += 1) {
    const distance = perpendicularDistance(
      points[index],
      points[0],
      points[points.length - 1],
      originLat,
    );
    if (distance > farthestDistance) {
      farthestDistance = distance;
      farthestIndex = index;
    }
  }
  if (farthestDistance <= tolerance) {
    return [points[0], points[points.length - 1]];
  }
  const left = simplifyRdp(points.slice(0, farthestIndex + 1), tolerance, originLat);
  const right = simplifyRdp(points.slice(farthestIndex), tolerance, originLat);
  return [...left.slice(0, -1), ...right];
}

function turnAngleDegrees(
  previous: GeometryPoint,
  current: GeometryPoint,
  next: GeometryPoint,
  originLat: number,
): number {
  const a = toMeters(previous, originLat);
  const b = toMeters(current, originLat);
  const c = toMeters(next, originLat);
  const v1: [number, number] = [b[0] - a[0], b[1] - a[1]];
  const v2: [number, number] = [c[0] - b[0], c[1] - b[1]];
  const n1 = Math.hypot(v1[0], v1[1]);
  const n2 = Math.hypot(v2[0], v2[1]);
  if (n1 === 0 || n2 === 0) return 0;
  const dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2);
  return (Math.acos(Math.max(-1, Math.min(1, dot))) * 180) / Math.PI;
}

function roundCorners(
  points: GeometryPoint[],
  radius: number,
  minAngle: number,
  originLat: number,
): GeometryPoint[] {
  if (points.length <= 2) return points;
  const output: GeometryPoint[] = [points[0]];
  for (let index = 1; index < points.length - 1; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const next = points[index + 1];
    const incoming = distanceMeters(previous, current, originLat);
    const outgoing = distanceMeters(current, next, originLat);
    const angle = turnAngleDegrees(previous, current, next, originLat);
    const localRadius = Math.min(radius, incoming * 0.32, outgoing * 0.32);
    if (angle < minAngle || incoming < 1 || outgoing < 1 || localRadius < 1) {
      output.push(current);
      continue;
    }
    const entry: GeometryPoint = [
      current[0] + ((previous[0] - current[0]) / incoming) * localRadius,
      current[1] + ((previous[1] - current[1]) / incoming) * localRadius,
    ];
    const exit: GeometryPoint = [
      current[0] + ((next[0] - current[0]) / outgoing) * localRadius,
      current[1] + ((next[1] - current[1]) / outgoing) * localRadius,
    ];
    for (const t of [0.25, 0.5, 0.75]) {
      const inverse = 1 - t;
      output.push([
        inverse * inverse * entry[0] + 2 * inverse * t * current[0] + t * t * exit[0],
        inverse * inverse * entry[1] + 2 * inverse * t * current[1] + t * t * exit[1],
      ]);
    }
    output.push(exit);
  }
  output.push(points[points.length - 1]);
  return output;
}

/**
 * Prepare GTFS shape points for display: remove sub-metre duplicates, simplify near-collinear
 * runs, then round only sharp corners. The source geometry in the API/database is unchanged.
 */
export function prepareDisplayGeometry(
  points: GeometryPoint[],
  options: GeometryOptions = {},
): GeometryPoint[] {
  if (points.length < 3) return points;
  const originLat = points[0][0];
  const deduped = points.filter((point, index) => {
    if (index === 0) return true;
    return distanceMeters(point, points[index - 1], originLat) >= 1;
  });
  if (deduped.length < 3) return deduped;
  const simplified = simplifyRdp(
    deduped,
    options.simplifyToleranceMeters ?? 5,
    originLat,
  );
  return roundCorners(
    simplified,
    options.cornerRadiusMeters ?? 9,
    options.minCornerAngleDegrees ?? 22,
    originLat,
  );
}
