import { useDeferredValue, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { Attribution } from "../components/Attribution";
import { PassengerBoard } from "../components/PassengerBoard";
import { RouteExplorer } from "../components/RouteExplorer";
import { StopMap } from "../components/StopMap";
import { displayRouteName, displayStopName, formatFeedTime } from "../lib/format";

export default function LiveMapPage() {
  const [query, setQuery] = useState("");
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [selectedShapeId, setSelectedShapeId] = useState<string | null>(null);
  const [showVehicles, setShowVehicles] = useState(true);
  const [fitSignal, setFitSignal] = useState(0);
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    setSelectedShapeId(null);
  }, [selectedRouteId]);

  const statusQuery = useQuery({
    queryKey: ["network-status"],
    queryFn: () => api.networkStatus(),
  });
  const routesQuery = useQuery({
    queryKey: ["routes", deferredQuery],
    queryFn: () =>
      api.routes({
        q: deferredQuery || undefined,
        mode: "Bus",
        limit: 100,
      }),
  });
  const geometryQuery = useQuery({
    queryKey: ["route-geometry", selectedRouteId],
    queryFn: () => api.routeGeometry(selectedRouteId ?? ""),
    enabled: selectedRouteId !== null,
  });
  const realtimeStatusQuery = useQuery({
    queryKey: ["realtime-status"],
    queryFn: () => api.realtimeStatus(),
    refetchInterval: 15_000,
    retry: 1,
  });
  const geometry = geometryQuery.data ?? null;
  const shape =
    geometry?.shapes.find((item) => item.shape_id === selectedShapeId) ??
    geometry?.shapes[0] ??
    null;
  const shapeFilter =
    geometry?.source === "shapes" ? (shape?.shape_id ?? undefined) : undefined;

  const vehiclesQuery = useQuery({
    queryKey: ["realtime-vehicles", selectedRouteId, shapeFilter],
    queryFn: () =>
      api.realtimeVehicles({
        mode: "Bus",
        route_id: selectedRouteId ?? undefined,
        shape_id: shapeFilter,
        limit: 1000,
      }),
    refetchInterval: 30_000,
    retry: 1,
  });

  const routes = routesQuery.data?.items ?? [];
  const realtimeStatus = realtimeStatusQuery.data ?? null;
  const vehicles = showVehicles ? (vehiclesQuery.data?.items ?? []) : [];
  const selectedRoute = routes.find((route) => route.route_id === selectedRouteId) ?? null;
  const orderedStops = shape?.stops ?? [];

  useEffect(() => {
    setFitSignal((value) => value + 1);
  }, [geometry?.route_id, shape?.shape_id]);

  const hasData = statusQuery.data?.has_data ?? false;
  const statusLabel = statusQuery.isError
    ? "API offline"
    : hasData
      ? `${statusQuery.data?.totals.routes ?? 0} routes in the current GTFS feed`
      : "Awaiting GTFS data";

  return (
    <main className="page live-map-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Auckland, New Zealand</p>
          <h1>Live bus map</h1>
          <p className="subtitle">
            Explore Auckland bus routes, real road geometry and live vehicles.
          </p>
        </div>
        <span className={`status-pill${hasData ? " is-ready" : ""}`} role="status">
          {statusLabel}
        </span>
      </div>

      <div className="realtime-bar" role="status">
        <span className={`live-dot${realtimeStatus?.has_data ? " is-live" : ""}`} />
        <div className="realtime-summary">
          <strong>Live buses</strong>
          {realtimeStatus ? (
            <span>
              {vehicles.length} shown · {realtimeStatus.vehicle_count} vehicles in AT feed ·
              updated {formatFeedTime(realtimeStatus.feed_timestamp)} ·{" "}
              {realtimeStatus.calls_last_7_days}/{realtimeStatus.weekly_quota} API calls this week
            </span>
          ) : (
            <span>Realtime status unavailable</span>
          )}
          {realtimeStatus && !realtimeStatus.configured ? (
            <span className="realtime-error">
              Set TP_AT_API_KEY in .env to enable live vehicles.
            </span>
          ) : null}
          {realtimeStatus?.last_error ? (
            <span className="realtime-error">Feed error: {realtimeStatus.last_error}</span>
          ) : null}
        </div>
        <label className="realtime-toggle">
          <input
            type="checkbox"
            checked={showVehicles}
            onChange={(event) => setShowVehicles(event.target.checked)}
          />
          Show live buses
        </label>
      </div>

      {!hasData && !statusQuery.isLoading ? (
        <div className="notice" role="alert">
          No GTFS feed loaded yet. Run <code>python -m app.cli.gtfs load --download</code> from
          the <code>backend</code> directory, then refresh this page.
        </div>
      ) : null}

      <div className="layout">
        <RouteExplorer
          routes={routes}
          total={routesQuery.data?.total ?? 0}
          query={query}
          selectedId={selectedRouteId}
          loading={routesQuery.isLoading}
          error={routesQuery.isError ? "Could not load bus routes. Is the API running on :8000?" : null}
          onQueryChange={setQuery}
          onSelect={setSelectedRouteId}
        />

        <section className="panel detail" aria-label="Route detail">
          <div className="detail-heading">
            <div>
              <p className="eyebrow">Network explorer</p>
              <h2>{selectedRoute ? displayRouteName(selectedRoute) : "Select a route"}</h2>
              {selectedRoute ? (
                <p className="muted">
                  {selectedRoute.mode} route · {orderedStops.length} stop
                  {orderedStops.length === 1 ? "" : "s"} shown
                  {geometry
                    ? ` · ${geometry.shape_count} direction${geometry.shape_count === 1 ? "" : "s"} / branch${geometry.shape_count === 1 ? "" : "es"}`
                    : ""}
                  {shapeFilter ? " · buses on this pattern only" : ""}
                </p>
              ) : (
                <p className="muted">Choose a route to see its geometry, or view all live vehicles.</p>
              )}
            </div>
            <div className="heading-actions">
              {geometry && geometry.shapes.length > 1 ? (
                <label className="shape-select">
                  <span>Direction / branch</span>
                  <select
                    aria-label="Direction / branch"
                    value={shape?.shape_id ?? ""}
                    onChange={(event) => setSelectedShapeId(event.target.value)}
                  >
                    {geometry.shapes
                      .filter((item) => item.trip_count >= 10)
                      .map((item) => (
                        <option key={item.shape_id} value={item.shape_id}>
                          {item.label}
                          {item.direction_id !== null ? ` · D${item.direction_id}` : ""}
                        </option>
                      ))}
                    {geometry.shapes.some((item) => item.trip_count < 10) ? (
                      <optgroup label="Short turns / branches">
                        {geometry.shapes
                          .filter((item) => item.trip_count < 10)
                          .map((item) => (
                            <option key={item.shape_id} value={item.shape_id}>
                              {item.label} · Short turn
                            </option>
                          ))}
                      </optgroup>
                    ) : null}
                  </select>
                </label>
              ) : null}
              <button
                type="button"
                className="fit-button"
                onClick={() => setFitSignal((value) => value + 1)}
              >
                Fit to view
              </button>
            </div>
          </div>

          <StopMap
            shape={shape}
            vehicles={vehicles}
            approximate={geometry?.approximate ?? false}
            note={geometry?.note ?? ""}
            fitSignal={fitSignal}
            emptyMessage={
              geometryQuery.isLoading
                ? "Loading route geometry..."
                : selectedRoute
                  ? "No geometry or vehicles available for this route."
                  : "Waiting for live vehicle positions..."
            }
          />

          {orderedStops.length > 0 ? (
            <ol className="stop-list">
              {orderedStops.map((stop, index) => (
                <li key={`${stop.stop_id}-${index}`}>
                  <span>{displayStopName(stop)}</span>
                  <span className="muted">{stop.stop_id}</span>
                </li>
              ))}
            </ol>
          ) : null}
        </section>
      </div>

      <PassengerBoard
        routeId={selectedRouteId}
        routeLabel={selectedRoute ? displayRouteName(selectedRoute) : null}
      />

      <Attribution text={statusQuery.data?.attribution} />
    </main>
  );
}
