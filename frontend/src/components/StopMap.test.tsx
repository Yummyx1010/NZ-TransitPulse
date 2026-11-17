import type { ReactNode } from "react";

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RealtimeVehicle, ShapeGeometry } from "../api/types";
import { StopMap } from "./StopMap";

const { mapMock } = vi.hoisted(() => ({
  mapMock: {
    invalidateSize: vi.fn(),
    setView: vi.fn(),
    fitBounds: vi.fn(),
    getSize: vi.fn(() => ({ x: 800, y: 600 })),
  },
}));

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => null,
  CircleMarker: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Marker: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Polyline: () => null,
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useMap: () => mapMock,
}));

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

const VEHICLES: RealtimeVehicle[] = [
  {
    vehicle_id: "BUS1",
    lat: -36.71,
    lon: 174.9,
    bearing: 90,
    speed: 40,
    route_id: "70-205",
    route_short_name: "70",
    mode: "Bus",
    trip_id: "T1",
    timestamp: 1794707698,
  },
];

function renderMap(shape: ShapeGeometry | null) {
  return render(
    <StopMap
      shape={shape}
      vehicles={VEHICLES}
      approximate={false}
      note=""
      fitSignal={0}
      emptyMessage="Waiting for geometry"
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mapMock.getSize.mockImplementation(() => ({ x: 800, y: 600 }));
});

afterEach(() => {
  cleanup();
});

describe("StopMap viewport", () => {
  it("keeps the map mounted but does not move it while geometry is loading", async () => {
    renderMap(null);

    expect(screen.getByTestId("map-container")).toBeInTheDocument();
    expect(screen.getByText("Live buses (1)")).toBeInTheDocument();
    // Vehicles are drawn, but must not be used to fit the viewport.
    expect(mapMock.fitBounds).not.toHaveBeenCalled();
    expect(mapMock.setView).not.toHaveBeenCalled();
    expect(mapMock.invalidateSize).not.toHaveBeenCalled();
  });

  it("fits only the selected shape geometry, not vehicle positions", async () => {
    renderMap(SHAPE);

    await waitFor(() =>
      expect(mapMock.fitBounds).toHaveBeenCalledWith(
        [
          [-36.8443, 174.767],
          [-36.847, 174.763],
          [-36.85, 174.76],
        ],
        expect.objectContaining({ maxZoom: 13 }),
      ),
    );
    expect(mapMock.setView).not.toHaveBeenCalled();
  });

  it("waits for a usable container size instead of fitting a zero-sized map", async () => {
    let measurements = 0;
    mapMock.getSize.mockImplementation(() => {
      measurements += 1;
      return measurements < 4 ? { x: 0, y: 0 } : { x: 800, y: 600 };
    });

    renderMap(SHAPE);

    await waitFor(() => expect(mapMock.fitBounds).toHaveBeenCalledTimes(1));
    expect(measurements).toBeGreaterThanOrEqual(4);
    expect(mapMock.invalidateSize).toHaveBeenCalled();
  });
});
