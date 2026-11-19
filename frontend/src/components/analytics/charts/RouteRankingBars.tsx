import type { RouteRankingItem, AnalyticsMetric } from "../../../api/types";
import { EmptyState } from "../../ui/States";
import { formatChange, formatMetricValue } from "../../../lib/analytics";
import { getMetricDefinition } from "../../../lib/metricDefinitions";

interface RouteRankingBarsProps {
  metric: AnalyticsMetric;
  items: RouteRankingItem[];
  intent: "most-used" | "attention";
  selectedRoute: string | null;
  onSelectRoute: (routeNo: string) => void;
}

export function RouteRankingBars({
  metric,
  items,
  intent,
  selectedRoute,
  onSelectRoute,
}: RouteRankingBarsProps) {
  const definition = getMetricDefinition(metric);
  const sorted = [...items].sort((a, b) =>
    intent === "most-used"
      ? b.average_value - a.average_value
      : a.average_value - b.average_value,
  );
  const max = Math.max(...sorted.map((item) => Math.abs(item.average_value)), 0.0001);

  if (sorted.length === 0) {
    return <EmptyState>No routes match the current filters.</EmptyState>;
  }

  return (
    <ol className="observatory-ranking-list">
      {sorted.map((item) => (
        <li key={item.route_no}>
          <button
            type="button"
            className={`observatory-ranking-row${selectedRoute === item.route_no ? " is-selected" : ""}`}
            onClick={() => onSelectRoute(item.route_no)}
            aria-label={`Select route ${item.route_no}`}
          >
            <span className="observatory-ranking-route">{item.route_no}</span>
            <span className="observatory-ranking-name">
              {item.route_name ?? "Unnamed route"}
            </span>
            <span className="observatory-bar-track" aria-hidden="true">
              <span
                className={`observatory-bar-fill${intent === "attention" ? " is-warning" : ""}`}
                style={{ width: `${(Math.abs(item.average_value) / max) * 100}%` }}
              />
            </span>
            <span className="observatory-ranking-value">
              {formatMetricValue(metric, item.average_value)}
            </span>
            <span className="observatory-ranking-change">
              {formatChange(metric, item.change)} · {item.sample_months}m
            </span>
          </button>
        </li>
      ))}
      <li className="observatory-panel-meta" aria-hidden="true">
        {definition.unit} · {intent === "most-used" ? "highest first" : "lowest first"}
      </li>
    </ol>
  );
}
