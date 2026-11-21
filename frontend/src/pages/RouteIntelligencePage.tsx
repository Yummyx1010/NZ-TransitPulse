import { useState } from "react";
import { Link } from "react-router-dom";

import { Panel } from "../components/ui/Panel";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState } from "../components/ui/States";
import { useAnalyticsRoutes } from "../hooks/useAnalytics";
import { useRouteContext } from "../hooks/useRouteContext";

export function RouteIntelligencePage() {
  const [query, setQuery] = useState("");
  const { routeNo, routeId, routeIds, routeLabel, matchedInGtfs, setRoute } =
    useRouteContext();
  const results = useAnalyticsRoutes(query.trim());

  return (
    <div className="observatory-content">
      <PageHeader
        title="Route Intelligence"
        description="Find an Auckland bus route and keep that route context as you move through the product."
        meta={[routeNo ? `Route ${routeNo}` : "No route selected"]}
      />

      <Panel
        title="Find a route"
        subtitle="Search by the official route number used in AT performance reports."
        meta="Official route numbers"
      >
        <form
          className="observatory-route-search"
          onSubmit={(event) => {
            event.preventDefault();
            if (query.trim()) setRoute(query.trim());
          }}
        >
          <input
            aria-label="Route number"
            value={query}
            placeholder="e.g. 70"
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit">Track route</button>
        </form>

        {results.data?.items.length ? (
          <ul className="observatory-route-results">
            {results.data.items.slice(0, 8).map((item) => (
              <li key={item.route_no}>
                <button type="button" onClick={() => setRoute(item.route_no)}>
                  <strong>{item.route_no}</strong>
                  <span>{item.route_name ?? "Unnamed route"}</span>
                  <small>
                    {item.matched_in_gtfs ? `GTFS ${item.route_ids[0]}` : "No GTFS match"}
                  </small>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </Panel>

      {routeNo ? (
        <Panel
          title={`Route ${routeNo}`}
          subtitle="Context is now shared with analytics views."
          meta={matchedInGtfs ? "Matched in GTFS" : "Official report only"}
        >
          <p>
            <strong>{routeLabel ?? routeNo}</strong>
          </p>
          <p>
            GTFS route IDs: {routeIds.length ? routeIds.join(", ") : "none"}
            {routeId ? ` · primary ${routeId}` : ""}
          </p>
          <Link to={`/analytics/performance?route=${encodeURIComponent(routeNo)}`}>
            View official performance for this route
          </Link>
        </Panel>
      ) : (
        <EmptyState>
          Select a route to carry it across Service Health, Network Analytics and Route
          Comparison. The full route workspace arrives in v0.6.3.
        </EmptyState>
      )}
    </div>
  );
}
