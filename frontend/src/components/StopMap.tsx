import { useEffect, useMemo } from "react";
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
import { displayStopName, formatCoordinate, formatFeedTime } from "../lib/format";
import { createBusIcon } from "./busIcon";

const AUCKLAND_CENTRE: [number, number] = [-36.8485, 174.7633];

type LatLng = [number, number];

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
  useEffect(() => {
    // Defer one tick so the container has its final size before Leaflet measures it.
    const timer = window.setTimeout(() => {
      map.invalidateSize();
      if (points.length === 0) {
        map.setView(AUCKLAND_CENTRE, 11);
        return;
      }
      if (points.length === 1) {
        map.setView(points[0], 14);
        return;
      }
      map.fitBounds(points, {
        paddingTopLeft: [72, 72],
        paddingBottomRight: [72, 72],
        maxZoom: 13,
        animate: false,
      });
    }, 0);
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
  const geometryPoints = useMemo<LatLng[]>(
    () => (shape ? shape.points.map((point) => [point[0], point[1]] as LatLng) : []),
    [shape],
  );
  const vehiclePoints = useMemo<LatLng[]>(
    () => vehicles.map((vehicle) => [vehicle.lat, vehicle.lon] as LatLng),
    [vehicles],
  );
  const boundsPoints = geometryPoints.length > 0 ? geometryPoints : vehiclePoints;
  const viewKey = shape?.shape_id ?? "vehicles-only";

  if (boundsPoints.length === 0) {
    return (
      <div className="map-placeholder">
        {emptyMessage ?? "Select a route to see its geometry on the map."}
      </div>
    );
  }

  return (
    <div className="map-wrapper">
      {approximate ? (
        <div className="map-note" role="note">
          <strong>Approximate route</strong> — {note}
        </div>
      ) : null}
      {vehicles.length > 0 ? (
        <div className="map-legend" aria-label="Map legend">
          <span><i className="legend-dot legend-route" /> Route geometry / stops</span>
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
        <FitBounds points={boundsPoints} viewKey={viewKey} fitSignal={fitSignal} />
        {geometryPoints.length > 1 ? (
          <Polyline
            positions={geometryPoints}
            pathOptions={{ color: "#2563eb", weight: 4, opacity: 0.85 }}
          />
        ) : null}
        {shape?.stops.map((stop, index) => (
          <CircleMarker
            key={`stop-${stop.stop_id}-${index}`}
            center={[stop.lat, stop.lon]}
            radius={6}
            pathOptions={{
              color: "#ffffff",
              fillColor: "#1d4ed8",
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
