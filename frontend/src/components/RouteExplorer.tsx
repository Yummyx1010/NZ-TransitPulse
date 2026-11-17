import type { RouteSummary } from "../api/types";
import { displayRouteName } from "../lib/format";

interface RouteExplorerProps {
  routes: RouteSummary[];
  total: number;
  query: string;
  selectedId: string | null;
  loading: boolean;
  error: string | null;
  onQueryChange: (value: string) => void;
  onSelect: (routeId: string) => void;
}

export function RouteExplorer({
  routes,
  total,
  query,
  selectedId,
  loading,
  error,
  onQueryChange,
  onSelect,
}: RouteExplorerProps) {
  return (
    <aside className="panel explorer" aria-label="Route explorer">
      <h2>Bus routes</h2>
      <p className="bus-only-note">NZ TransitPulse covers buses only.</p>
      <label className="field">
        <span>Search by route number or name</span>
        <input
          type="search"
          value={query}
          placeholder="e.g. 70 or 18"
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </label>

      <p className="result-count" role="status">
        {loading ? "Loading routes..." : `${total} bus route${total === 1 ? "" : "s"} found`}
      </p>
      {error ? <p className="error">{error}</p> : null}

      <ul className="route-list">
        {routes.map((route) => (
          <li key={route.route_id}>
            <button
              type="button"
              className={`route-item${selectedId === route.route_id ? " is-selected" : ""}`}
              onClick={() => onSelect(route.route_id)}
              aria-pressed={selectedId === route.route_id}
            >
              <span className="route-code" style={{ borderColor: `#${route.colour ?? "64748b"}` }}>
                {route.short_name || "—"}
              </span>
              <span className="route-name">{displayRouteName(route)}</span>
              <span className="badge badge-bus">Bus</span>
            </button>
          </li>
        ))}
      </ul>

      {!loading && routes.length === 0 && !error ? (
        <p className="empty">No bus routes match your search.</p>
      ) : null}
    </aside>
  );
}
