import { useEffect, useMemo, useRef } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";

import type { RealtimeVehicle, ShapeGeometry } from "../api/types";
import { prepareDisplayGeometry } from "../lib/geometry";
import { displayStopName, formatCoordinate, formatFeedTime } from "../lib/format";
import { type LatLng, boundsForShape, shouldFitBounds } from "../lib/mapBounds";
import { createBusIcon } from "./busIcon";

const AUCKLAND_CENTRE: [number, number] = [-36.8485, 174.7633];

function FitBounds({
  points,
  viewKey,
  fitSignal,
}: {
  points: LatLng[];
  viewKey: string;
  fitSignal: number;
}) {
  const map = useMap();
  const tokenRef = useRef(0);

  useEffect(() => {
    // Always invalidate a pending fit, including when geometry disappears between two
    // route selections: otherwise a stale timer would frame the previous route.
    const token = ++tokenRef.current;
    if (!shouldFitBounds(points)) {
      return;
    }
    let timer = 0;
    let attempts = 0;

    const apply = () => {
      // A newer route selection supersedes this pending fit.
      if (token !== tokenRef.current) return;
      map.invalidateSize({ animate: false });
      const size = map.getSize();
      // A freshly mounted flex container can still measure 0. Fitting now computes a
      // meaningless zoom/centre, so wait until the map has a usable size.
      if ((size.x < 50 || size.y < 50) && attempts < 40) {
        attempts += 1;
        timer = window.setTimeout(apply, 16);
        return;
      }
      if (points.length === 1) {
        map.setView(points[0], 14, { animate: false });
        return;
      }
      map.fitBounds(points, {
        paddingTopLeft: [72, 72],
        paddingBottomRight: [72, 72],
        maxZoom: 13,
        animate: false,
      });
    };

    timer = window.setTimeout(apply, 0);
    return () => window.clearTimeout(timer);
  }, [map, points, viewKey, fitSignal]);
  return null;
}

interface StopMapProps {
  shape: ShapeGeometry | null;
  vehicles: RealtimeVehicle[];
  approximate: boolean;
  note: string;
  fitSignal: number;
  emptyMessage?: string;
}

export function StopMap({
  shape,
  vehicles,
  approximate,
  note,
  fitSignal,
  emptyMessage,
}: StopMapProps) {
  const rawGeometryPoints = useMemo<LatLng[]>(() => boundsForShape(shape), [shape]);
  const geometryPoints = useMemo<LatLng[]>(
    () => prepareDisplayGeometry(rawGeometryPoints),
    [rawGeometryPoints],
  );
  const viewKey = shape?.shape_id ?? "no-shape";
  const hasContent = shape !== null || vehicles.length > 0;

  // The MapContainer stays mounted even with no data. Unmounting it between route
  // selections destroys the Leaflet instance and makes fitBounds unreliable.
  return (
    <div className="map-wrapper">
      {!hasContent ? (
        <div className="map-notice" role="status">
          {emptyMessage ?? "Select a route to see its geometry on the map."}
        </div>
      ) : null}
      {approximate ? (
        <div className="map-note" role="note">
          <strong>Approximate route</strong> — {note}
        </div>
      ) : null}
      {vehicles.length > 0 ? (
        <div className="map-legend" aria-label="Map legend">
          <span title="GTFS shape points are simplified and gently rounded for display only">
            <i className="legend-dot legend-route" /> Route geometry / stops
          </span>
          <span><i className="legend-dot legend-vehicle" /> Live buses ({vehicles.length})</span>
        </div>
      ) : null}
      <MapContainer
        center={AUCKLAND_CENTRE}
        zoom={12}
        className="map"
        scrollWheelZoom={false}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        <FitBounds points={geometryPoints} viewKey={viewKey} fitSignal={fitSignal} />
        {geometryPoints.length > 1 ? (
          <Polyline
            positions={geometryPoints}
            pathOptions={{ color: "#25685f", weight: 4, opacity: 0.9 }}
          />
        ) : null}
        {shape?.stops.map((stop, index) => (
          <CircleMarker
            key={`stop-${stop.stop_id}-${index}`}
            center={[stop.lat, stop.lon]}
            radius={6}
            pathOptions={{
              color: "#ffffff",
              fillColor: "#426f9c",
              fillOpacity: 1,
              weight: 2,
            }}
          >
            <Popup>
              <strong>{displayStopName(stop)}</strong>
              <br />
              {formatCoordinate(stop.lat)}, {formatCoordinate(stop.lon)}
              <br />
              Stop {index + 1} of {shape.stops.length}
            </Popup>
          </CircleMarker>
        ))}
        {vehicles.map((vehicle, index) => (
          <Marker
            key={`bus-${vehicle.vehicle_id}-${index}`}
            position={[vehicle.lat, vehicle.lon]}
            icon={createBusIcon(vehicle.bearing)}
          >
            <Popup>
              <strong>Bus</strong>{" "}
              {vehicle.route_short_name ? `· Route ${vehicle.route_short_name}` : ""}
              <br />
              Vehicle ID: {vehicle.vehicle_id}
              <br />
              Heading {vehicle.bearing ?? "unknown"}° · {formatCoordinate(vehicle.lat)},{" "}
              {formatCoordinate(vehicle.lon)}
              <br />
              Reported {formatFeedTime(vehicle.timestamp)}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
