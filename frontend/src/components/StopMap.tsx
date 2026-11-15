import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";

import type { ShapeGeometry } from "../api/types";
import { displayStopName, formatCoordinate } from "../lib/format";

const AUCKLAND_CENTRE: [number, number] = [-36.8485, 174.7633];

type LatLng = [number, number];

function FitBounds({ points, shapeId }: { points: LatLng[]; shapeId: string }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) {
      map.setView(AUCKLAND_CENTRE, 12);
      return;
    }
    if (points.length === 1) {
      map.setView(points[0], 14);
      return;
    }
    map.fitBounds(points, { padding: [56, 56], maxZoom: 14, animate: false });
  }, [map, points, shapeId]);
  return null;
}

interface StopMapProps {
  shape: ShapeGeometry | null;
  approximate: boolean;
  note: string;
  emptyMessage?: string;
}

export function StopMap({ shape, approximate, note, emptyMessage }: StopMapProps) {
  const points = useMemo<LatLng[]>(
    () => (shape ? shape.points.map((point) => [point[0], point[1]] as LatLng) : []),
    [shape],
  );

  if (!shape || points.length === 0) {
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
        <FitBounds points={points} shapeId={shape.shape_id} />
        {points.length > 1 ? (
          <Polyline
            positions={points}
            pathOptions={{ color: "#2563eb", weight: 4, opacity: 0.85 }}
          />
        ) : null}
        {shape.stops.map((stop, index) => (
          <CircleMarker
            key={`${stop.stop_id}-${index}`}
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
              Stop ID: {stop.stop_id}
              <br />
              Stop {index + 1} of {shape.stops.length}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
