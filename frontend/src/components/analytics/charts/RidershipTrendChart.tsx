import { useState } from "react";

import type { OfficialMetricPoint, TrendPoint } from "../../../api/types";
import { DataDetail } from "../../ui/DataDetail";
import { EmptyState } from "../../ui/States";

interface RidershipTrendChartProps {
  totals: OfficialMetricPoint[];
  averages: TrendPoint[];
}

type Mode = "total" | "average";

export function RidershipTrendChart({ totals, averages }: RidershipTrendChartProps) {
  const [mode, setMode] = useState<Mode>(totals.length > 0 ? "total" : "average");
  const [selected, setSelected] = useState<number | null>(null);
  const points = mode === "total" ? totals : averages;
  const width = 720;
  const height = 260;
  const padding = { left: 58, right: 18, top: 18, bottom: 34 };
  const values = points.map((point) => point.value);
  const max = Math.max(...values, 1);
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
  const ticks = [0, 0.5, 1].map((ratio) => ({
    ratio,
    value: max * ratio,
    y: height - padding.bottom - ratio * (height - padding.top - padding.bottom),
  }));
  const selectedPoint = selected === null ? null : coords[selected];
  const labelStep = Math.max(1, Math.ceil(points.length / 6));

  if (points.length === 0) {
    return <EmptyState>No ridership observations in this period.</EmptyState>;
  }

  return (
    <div>
      <div className="observatory-legend" aria-label="Ridership series">
        <button
          type="button"
          className={`observatory-tab${mode === "total" ? " is-active" : ""}`}
          onClick={() => {
            setMode("total");
            setSelected(null);
          }}
        >
          Network total
        </button>
        <button
          type="button"
          className={`observatory-tab${mode === "average" ? " is-active" : ""}`}
          onClick={() => {
            setMode("average");
            setSelected(null);
          }}
        >
          Average per route
        </button>
      </div>

      <svg
        className="observatory-chart is-ridership"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${mode === "total" ? "Network total" : "Average per route"} ridership trend`}
      >
        {ticks.map((tick) => (
          <g key={tick.ratio}>
            <line
              x1={padding.left}
              y1={tick.y}
              x2={width - padding.right}
              y2={tick.y}
              className="observatory-grid"
            />
            <text x={padding.left - 8} y={tick.y + 3} textAnchor="end" className="observatory-axis-label">
              {Math.round(tick.value).toLocaleString("en-NZ")}
            </text>
          </g>
        ))}
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
          <g key={item.point.month}>
            <circle
              className={`observatory-point${selected === item.index ? " is-selected" : ""}`}
              cx={item.x}
              cy={item.y}
              r={selected === item.index ? 5 : 3.5}
              tabIndex={0}
              role="button"
              aria-label={`${item.point.month}: ${Math.round(item.point.value).toLocaleString("en-NZ")} ${mode === "total" ? "total boardings" : "average boardings"}`}
              onClick={() => setSelected(item.index)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setSelected(item.index);
                }
              }}
            >
              <title>{`${item.point.month}: ${Math.round(item.point.value).toLocaleString("en-NZ")}`}</title>
            </circle>
          </g>
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
              label: mode === "total" ? "Network boardings" : "Average boardings per route",
              value: Math.round(selectedPoint.point.value).toLocaleString("en-NZ"),
            },
            {
              label: "Series",
              value: mode === "total" ? "Network total" : "Average per reporting route",
            },
          ]}
          onClear={() => setSelected(null)}
        />
      ) : null}
    </div>
  );
}
