import { useState } from "react";

import type { CorrelationResult, ScatterPoint } from "../../../api/types";
import { DataDetail } from "../../ui/DataDetail";
import { EmptyState } from "../../ui/States";

export function RelationshipScatter({
  points,
  correlation,
  onSelectRoute,
  selectedRoute,
}: {
  points: ScatterPoint[];
  correlation: CorrelationResult | null;
  onSelectRoute: (routeNo: string) => void;
  selectedRoute: string | null;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const width = 720;
  const height = 320;
  const padding = { left: 58, right: 20, top: 20, bottom: 46 };
  const maxX = Math.max(...points.map((point) => point.boardings), 1);
  const coords = points.map((point) => ({
    point,
    x:
      padding.left +
      (point.boardings / maxX) * (width - padding.left - padding.right),
    y:
      height -
      padding.bottom -
      point.punctuality * (height - padding.top - padding.bottom),
  }));
  const labelled = new Set(
    [...points]
      .sort((a, b) => b.boardings - a.boardings)
      .slice(0, 5)
      .map((point) => point.route_no),
  );
  const selectedPoint = coords.find((item) => item.point.route_no === selected);

  if (points.length === 0) {
    return <EmptyState>No route has both ridership and punctuality in this period.</EmptyState>;
  }

  return (
    <div>
      <svg
        className="observatory-chart is-relationship"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Average monthly boardings versus official punctuality by route"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = height - padding.bottom - ratio * (height - padding.top - padding.bottom);
          return (
            <g key={ratio}>
              <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} className="observatory-grid" />
              <text x={padding.left - 8} y={y + 3} textAnchor="end" className="observatory-axis-label">
                {(ratio * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}
        {[0, 0.5, 1].map((ratio) => {
          const x = padding.left + ratio * (width - padding.left - padding.right);
          return (
            <text key={ratio} x={x} y={height - 22} textAnchor="middle" className="observatory-axis-label">
              {Math.round(maxX * ratio).toLocaleString("en-NZ")}
            </text>
          );
        })}
        <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} className="observatory-axis" />
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} className="observatory-axis" />
        {coords.map(({ point, x, y }) => (
          <g key={point.route_no}>
            <circle
              className={`observatory-point${selected === point.route_no || selectedRoute === point.route_no ? " is-selected" : ""}`}
              cx={x}
              cy={y}
              r={5}
              tabIndex={0}
              role="button"
              aria-label={`Route ${point.route_no}, ${Math.round(point.boardings).toLocaleString("en-NZ")} average boardings, ${(point.punctuality * 100).toFixed(1)} percent punctual, ${point.sample_months} months`}
              onClick={() => setSelected(point.route_no)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setSelected(point.route_no);
                }
              }}
            >
              <title>{`${point.route_no}: ${point.sample_months} months`}</title>
            </circle>
            {labelled.has(point.route_no) ? (
              <text x={x + 8} y={y - 8} className="observatory-axis-label">
                {point.route_no}
              </text>
            ) : null}
          </g>
        ))}
        <text x={width - padding.right} y={height - 8} textAnchor="end" className="observatory-axis-label">
          Average monthly boardings
        </text>
      </svg>

      <div className="observatory-legend" aria-label="Correlation summary">
        <span className="observatory-legend-item">
          <span className="observatory-swatch" />
          Spearman correlation
        </span>
        <span>
          {correlation?.available
            ? `${correlation.coefficient} · n=${correlation.sample_size}`
            : correlation?.reason ?? "Correlation unavailable"}
        </span>
      </div>

      {selectedPoint ? (
        <DataDetail
          title={`Route ${selectedPoint.point.route_no}`}
          fields={[
            {
              label: "Average boardings",
              value: Math.round(selectedPoint.point.boardings).toLocaleString("en-NZ"),
            },
            {
              label: "Punctuality",
              value: `${(selectedPoint.point.punctuality * 100).toFixed(1)}%`,
            },
            { label: "Sample months", value: String(selectedPoint.point.sample_months) },
            { label: "Period", value: `${selectedPoint.point.first_month} – ${selectedPoint.point.last_month}` },
          ]}
          onClear={() => setSelected(null)}
        />
      ) : null}
      {selectedPoint ? (
        <button
          type="button"
          className="observatory-clear"
          onClick={() => onSelectRoute(selectedPoint.point.route_no)}
        >
          Track route {selectedPoint.point.route_no} across views
        </button>
      ) : null}
    </div>
  );
}
