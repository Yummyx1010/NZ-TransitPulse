import { useEffect } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";

import type { StopSummary } from "../api/types";
import { displayStopName, formatCoordinate } from "../lib/format";

const AUCKLAND_CENTRE: [number, number] = [-36.8485, 174.7633];

function FitBounds({ stops }: { stops: StopSummary[] }) {
  const map = useMap();
  useEffect(() => {
    const bounds: [number, number][] = stops.map((stop) => [stop.lat, stop.lon]);
    map.fitBounds(bounds, { padding: [48, 48], maxZoom: 15 });
  }, [map, stops]);
  return null;
}

interface StopMapProps {
  stops: StopSummary[];
  emptyMessage?: string;
}

export function StopMap({ stops, emptyMessage }: StopMapProps) {
  if (stops.length === 0) {
    return (
      <div className="map-placeholder">
        {emptyMessage ?? "Select a route to see its stops on the map."}
      </div>
    );
  }

  const positions: [number, number][] = stops.map((stop) => [stop.lat, stop.lon]);

  return (
    <MapContainer center={AUCKLAND_CENTRE} zoom={12} className="map" scrollWheelZoom={false}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      <FitBounds stops={stops} />
      {positions.length > 1 ? (
        <Polyline positions={positions} pathOptions={{ color: "#2563eb", weight: 3 }} />
      ) : null}
      {stops.map((stop) => (
        <CircleMarker
          key={stop.stop_id}
          center={[stop.lat, stop.lon]}
          radius={7}
          pathOptions={{ color: "#ffffff", fillColor: "#2563eb", fillOpacity: 1, weight: 2 }}
        >
          <Popup>
            <strong>{displayStopName(stop)}</strong>
            <br />
            {formatCoordinate(stop.lat)}, {formatCoordinate(stop.lon)}
            <br />
            Stop ID: {stop.stop_id}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
