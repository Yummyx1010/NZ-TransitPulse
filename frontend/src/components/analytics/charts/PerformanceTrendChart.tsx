import { useState } from "react";

import type { AnalyticsMetric, TrendPoint } from "../../../api/types";
import { formatMetricValue } from "../../../lib/analytics";
import { getMetricDefinition } from "../../../lib/metricDefinitions";
import { DataDetail } from "../../ui/DataDetail";
import { EmptyState } from "../../ui/States";

export function PerformanceTrendChart({
  metric,
  points,
}: {
  metric: AnalyticsMetric;
  points: TrendPoint[];
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const definition = getMetricDefinition(metric);
  const width = 720;
  const height = 260;
  const padding = { left: 52, right: 18, top: 18, bottom: 34 };
  const max = Math.max(...points.map((point) => point.value), 1);
  const coords = points.map((point, index) => {
    const x =
      padding.left +
      (index / Math.max(points.length - 1, 1)) *
        (width - padding.left - padding.right);
    const y =
      height -
      padding.bottom -
      (point.value / max) * (height - padding.top - padding.bottom);
    return { point, x, y, index };
  });
  const selectedPoint = selected === null ? null : coords[selected];
  const labelStep = Math.max(1, Math.ceil(points.length / 6));

  if (points.length === 0) {
    return <EmptyState>No service observations in this period.</EmptyState>;
  }

  return (
    <div>
      <svg
        className="observatory-chart is-performance"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${definition.label} trend`}
      >
        {[0, 0.5, 1].map((ratio) => {
          const value = max * ratio;
          const y =
            height -
            padding.bottom -
            ratio * (height - padding.top - padding.bottom);
          return (
            <g key={ratio}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                className="observatory-grid"
              />
              <text x={padding.left - 8} y={y + 3} textAnchor="end" className="observatory-axis-label">
                {(value * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}
        <line
          x1={padding.left}
          y1={height - padding.bottom}
          x2={width - padding.right}
          y2={height - padding.bottom}
          className="observatory-axis"
        />
        <polyline
          className="observatory-series"
          points={coords.map((item) => `${item.x},${item.y}`).join(" ")}
        />
        {coords.map((item) => (
          <circle
            key={item.point.month}
            className={`observatory-point${selected === item.index ? " is-selected" : ""}`}
            cx={item.x}
            cy={item.y}
            r={selected === item.index ? 5 : 3.5}
            tabIndex={0}
            role="button"
            aria-label={`${item.point.month}: ${formatMetricValue(metric, item.point.value)}`}
            onClick={() => setSelected(item.index)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setSelected(item.index);
              }
            }}
          >
            <title>{`${item.point.month}: ${formatMetricValue(metric, item.point.value)}`}</title>
          </circle>
        ))}
        {coords
          .filter((item) => item.index % labelStep === 0 || item.index === coords.length - 1)
          .map((item) => (
            <text
              key={`label-${item.point.month}`}
              x={item.x}
              y={height - 10}
              textAnchor="middle"
              className="observatory-axis-label"
            >
              {item.point.month.slice(2)}
            </text>
          ))}
      </svg>
      {selectedPoint ? (
        <DataDetail
          title={selectedPoint.point.month}
          fields={[
            {
              label: definition.shortLabel,
              value: formatMetricValue(metric, selectedPoint.point.value),
            },
            { label: "Reporting routes", value: String(selectedPoint.point.sample_count) },
          ]}
          onClear={() => setSelected(null)}
        />
      ) : null}
    </div>
  );
}
