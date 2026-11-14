import type { RouteSummary } from "../api/types";
import { displayRouteName, modeClass } from "../lib/format";

interface RouteExplorerProps {
  routes: RouteSummary[];
  total: number;
  query: string;
  mode: string;
  selectedId: string | null;
  loading: boolean;
  error: string | null;
  onQueryChange: (value: string) => void;
  onModeChange: (value: string) => void;
  onSelect: (routeId: string) => void;
}

const MODES = ["", "Bus", "Rail", "Ferry"];

export function RouteExplorer({
  routes,
  total,
  query,
  mode,
  selectedId,
  loading,
  error,
  onQueryChange,
  onModeChange,
  onSelect,
}: RouteExplorerProps) {
  return (
    <aside className="panel explorer" aria-label="Route explorer">
      <h2>Routes</h2>
      <label className="field">
        <span>Search by route number or name</span>
        <input
          type="search"
          value={query}
          placeholder="e.g. 18 or Western"
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </label>
      <label className="field">
        <span>Mode</span>
        <select value={mode} onChange={(event) => onModeChange(event.target.value)}>
          {MODES.map((option) => (
            <option key={option} value={option}>
              {option || "All modes"}
            </option>
          ))}
        </select>
      </label>

      <p className="result-count" role="status">
        {loading ? "Loading routes..." : `${total} route${total === 1 ? "" : "s"} found`}
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
              <span className={modeClass(route.mode)}>{route.mode}</span>
            </button>
          </li>
        ))}
      </ul>

      {!loading && routes.length === 0 && !error ? (
        <p className="empty">No routes match your search.</p>
      ) : null}
    </aside>
  );
}
