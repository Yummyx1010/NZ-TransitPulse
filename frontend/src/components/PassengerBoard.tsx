import { useDeferredValue, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { StopSummary } from "../api/types";
import { delayStatusClass, formatDelay, formatMinutesAway } from "../lib/format";

interface PassengerBoardProps {
  routeId: string | null;
  routeLabel?: string | null;
}

export function PassengerBoard({ routeId, routeLabel }: PassengerBoardProps) {
  const [query, setQuery] = useState("");
  const [selectedStop, setSelectedStop] = useState<StopSummary | null>(null);
  const [showAllRoutes, setShowAllRoutes] = useState(false);
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    setShowAllRoutes(false);
    setSelectedStop(null);
  }, [routeId]);

  // The selected route scopes the board by default; the toggle is an explicit escape
  // hatch so passengers are never left guessing why other buses are hidden.
  const effectiveRouteId = routeId && !showAllRoutes ? routeId : null;

  const stopsQuery = useQuery({
    queryKey: ["stop-search", deferredQuery, effectiveRouteId],
    queryFn: () => api.stops(deferredQuery, effectiveRouteId ?? undefined),
    enabled: deferredQuery.trim().length >= 2,
    retry: 1,
  });
  const arrivalsQuery = useQuery({
    queryKey: ["stop-arrivals", selectedStop?.stop_id, effectiveRouteId],
    queryFn: () =>
      api.stopArrivals(selectedStop!.stop_id, {
        route_id: effectiveRouteId ?? undefined,
        minutes: 60,
        limit: 20,
      }),
    enabled: selectedStop !== null,
    refetchInterval: 30_000,
    retry: 1,
  });
  const alertsQuery = useQuery({
    queryKey: ["bus-alerts", routeId],
    queryFn: () =>
      api.realtimeAlerts({ mode: "Bus", route_id: routeId ?? undefined }),
    refetchInterval: 60_000,
    retry: 1,
  });

  const arrivals = arrivalsQuery.data;
  const alerts = alertsQuery.data?.items ?? [];

  return (
    <section className="panel passenger" aria-label="Passenger view">
      <div className="passenger-header">
        <div>
          <p className="eyebrow">Passenger view</p>
          <h2>
            {effectiveRouteId
              ? `${routeLabel ?? "Selected route"} arrivals`
              : "Next bus arrivals"}
          </h2>
          <p className="muted">
            {effectiveRouteId
              ? `Showing ${routeLabel ?? "the selected route"} buses at this stop.`
              : "Search an Auckland bus stop to see all upcoming buses, with scheduled and predicted times."}
          </p>
        </div>
        {routeId ? (
          <button
            type="button"
            className="route-filter-toggle"
            data-testid="route-filter"
            onClick={() => setShowAllRoutes((value) => !value)}
          >
            {showAllRoutes ? "Show selected route only" : "Show all buses at this stop"}
          </button>
        ) : null}
      </div>

      <div className="passenger-grid">
        <div className="arrivals-column">
          <label className="field">
            <span>Search a stop</span>
            <input
              type="search"
              value={query}
              placeholder="e.g. Britomart or Newmarket"
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>

          {deferredQuery.trim().length >= 2 && (stopsQuery.data?.items.length ?? 0) > 0 ? (
            <ul className="stop-options" data-testid="stop-options">
              {stopsQuery.data?.items.slice(0, 6).map((stop) => (
                <li key={stop.stop_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedStop(stop);
                      setQuery("");
                    }}
                  >
                    {stop.name} <span className="muted">{stop.stop_id}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          {selectedStop ? (
            <>
              <p className="arrivals-stop">
                {selectedStop.name} <span className="muted">{selectedStop.stop_id}</span>
                {arrivals && arrivals.included_stop_ids.length > 1 ? (
                  <span className="muted">
                    {" "}
                    · {arrivals.included_stop_ids.length - 1} platforms
                  </span>
                ) : null}
              </p>
              {arrivalsQuery.isLoading ? (
                <p className="empty">Loading arrivals...</p>
              ) : null}
              {arrivals && arrivals.total === 0 ? (
                <p className="empty">
                  {effectiveRouteId
                    ? `No ${routeLabel ?? "selected route"} buses in the next ${arrivals.window_minutes} minutes. This stop may not be served by this route.`
                    : `No bus arrivals in the next ${arrivals.window_minutes} minutes.`}
                </p>
              ) : null}
              <ul className="arrival-list">
                {arrivals?.items.map((item) => (
                  <li key={`${item.trip_id}-${item.scheduled_seconds}`}>
                    <span className="arrival-route">{item.route_short_name}</span>
                    <span className="arrival-headsign">
                      {item.headsign ?? `D${item.direction_id ?? "-"}`}
                    </span>
                    <span className="arrival-time">
                      {formatMinutesAway(item.minutes_away)}
                    </span>
                    <span className={delayStatusClass(item.status)}>{item.status}</span>
                    <span className="muted">
                      {item.predicted_time ?? item.scheduled_time} ·{" "}
                      {formatDelay(item.delay_seconds)}
                    </span>
                  </li>
                ))}
              </ul>
              {arrivals ? <p className="arrivals-note">{arrivals.note}</p> : null}
            </>
          ) : (
            <p className="empty">Pick a stop above to see the next buses.</p>
          )}
        </div>

        <div className="alerts-column">
          <h3>Bus service alerts</h3>
          {alerts.length === 0 ? (
            <p className="empty" data-testid="no-alerts">
              No current bus service alerts.
            </p>
          ) : (
            <ul className="alert-list">
              {alerts.slice(0, 8).map((alert) => (
                <li key={alert.alert_id}>
                  <strong>{alert.header ?? "Service alert"}</strong>
                  <p>{alert.description ?? alert.effect ?? "No detail provided."}</p>
                  <span className="muted">
                    {alert.route_ids.length
                      ? `Routes: ${alert.route_ids.join(", ")}`
                      : "Network-wide"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
