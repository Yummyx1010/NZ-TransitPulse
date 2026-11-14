import { useDeferredValue, useState } from "react";
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
  const deferredQuery = useDeferredValue(query);

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
  const stopsQuery = useQuery({
    queryKey: ["route-stops", selectedRouteId],
    queryFn: () => api.routeStops(selectedRouteId ?? ""),
    enabled: selectedRouteId !== null,
  });

  const routes = routesQuery.data?.items ?? [];
  const stops = selectedRouteId ? (stopsQuery.data?.items ?? []) : [];
  const selectedRoute = routes.find((route) => route.route_id === selectedRouteId) ?? null;
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
                  {selectedRoute.mode} route · {stops.length} stop{stops.length === 1 ? "" : "s"}{" "}
                  shown
                </p>
              ) : (
                <p className="muted">Choose a route to see its stops on the map.</p>
              )}
            </div>
          </div>

          <StopMap
            stops={stops}
            emptyMessage={
              stopsQuery.isLoading
                ? "Loading stops..."
                : "Select a route to see its stops on the map."
            }
          />

          {stops.length > 0 ? (
            <ol className="stop-list">
              {stops.map((stop) => (
                <li key={stop.stop_id}>
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
