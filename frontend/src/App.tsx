import { useDeferredValue, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "./api/client";
import { Attribution } from "./components/Attribution";
import { RouteExplorer } from "./components/RouteExplorer";
import { StopMap } from "./components/StopMap";
import { displayRouteName, displayStopName } from "./lib/format";

export default function App() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("");
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [selectedShapeId, setSelectedShapeId] = useState<string | null>(null);
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    setSelectedShapeId(null);
  }, [selectedRouteId]);

  const statusQuery = useQuery({
    queryKey: ["network-status"],
    queryFn: () => api.networkStatus(),
  });
  const routesQuery = useQuery({
    queryKey: ["routes", deferredQuery, mode],
    queryFn: () =>
      api.routes({
        q: deferredQuery || undefined,
        mode: mode || undefined,
        limit: 100,
      }),
  });
  const geometryQuery = useQuery({
    queryKey: ["route-geometry", selectedRouteId],
    queryFn: () => api.routeGeometry(selectedRouteId ?? ""),
    enabled: selectedRouteId !== null,
  });

  const routes = routesQuery.data?.items ?? [];
  const geometry = geometryQuery.data ?? null;
  const selectedRoute = routes.find((route) => route.route_id === selectedRouteId) ?? null;
  const shape =
    geometry?.shapes.find((item) => item.shape_id === selectedShapeId) ??
    geometry?.shapes[0] ??
    null;
  const orderedStops = shape?.stops ?? [];
  const hasData = statusQuery.data?.has_data ?? false;
  const statusLabel = statusQuery.isError
    ? "API offline"
    : hasData
      ? `${statusQuery.data?.totals.routes ?? 0} routes in the current GTFS feed`
      : "Awaiting GTFS data";

  return (
    <div className="app">
      <header className="header">
        <div>
          <p className="eyebrow">Auckland, New Zealand</p>
          <h1>NZ TransitPulse</h1>
          <p className="subtitle">Explore public transport routes and stops across Tāmaki Makaurau.</p>
        </div>
        <span className={`status-pill${hasData ? " is-ready" : ""}`} role="status">
          {statusLabel}
        </span>
      </header>

      {!hasData && !statusQuery.isLoading ? (
        <div className="notice" role="alert">
          No GTFS feed loaded yet. Run <code>python -m app.cli.gtfs load --download</code> from
          the <code>backend</code> directory, then refresh this page.
        </div>
      ) : null}

      <main className="layout">
        <RouteExplorer
          routes={routes}
          total={routesQuery.data?.total ?? 0}
          query={query}
          mode={mode}
          selectedId={selectedRouteId}
          loading={routesQuery.isLoading}
          error={routesQuery.isError ? "Could not load routes. Is the API running on :8000?" : null}
          onQueryChange={setQuery}
          onModeChange={setMode}
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
                  {geometry ? ` · ${geometry.shape_count} route pattern${geometry.shape_count === 1 ? "" : "s"}` : ""}
                </p>
              ) : (
                <p className="muted">Choose a route to see its geometry on the map.</p>
              )}
            </div>
            {geometry && geometry.shapes.length > 1 ? (
              <label className="shape-select">
                <span>Route pattern</span>
                <select
                  aria-label="Route pattern"
                  value={shape?.shape_id ?? ""}
                  onChange={(event) => setSelectedShapeId(event.target.value)}
                >
                  {geometry.shapes.map((item) => (
                    <option key={item.shape_id} value={item.shape_id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>

          <StopMap
            shape={shape}
            approximate={geometry?.approximate ?? false}
            note={geometry?.note ?? ""}
            emptyMessage={
              geometryQuery.isLoading
                ? "Loading route geometry..."
                : selectedRoute
                  ? "No geometry available for this route."
                  : "Select a route to see its geometry on the map."
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
      </main>

      <Attribution text={statusQuery.data?.attribution} />
    </div>
  );
}
