import { useState } from "react";

import type { AnalyticsMetric, HeatmapItem } from "../../../api/types";
import { formatMetricValue, metricLabel } from "../../../lib/analytics";
import { DataDetail } from "../../ui/DataDetail";
import { EmptyState } from "../../ui/States";

function colourClass(value: number): string {
  if (value >= 0.8) return "observatory-heat-4";
  if (value >= 0.6) return "observatory-heat-3";
  if (value >= 0.4) return "observatory-heat-2";
  if (value >= 0.2) return "observatory-heat-1";
  return "observatory-heat-0";
}

export function SeasonalityHeatmap({
  metric,
  months,
  items,
  normalize,
}: {
  metric: AnalyticsMetric;
  months: string[];
  items: HeatmapItem[];
  normalize: boolean;
}) {
  const [selected, setSelected] = useState<{ route: string; month: string } | null>(null);
  const globalMax = Math.max(
    ...items.flatMap((item) => item.values.filter((value): value is number => value !== null)),
    0.0001,
  );

  if (items.length === 0 || months.length === 0) {
    return <EmptyState>No route-month matrix available for this period.</EmptyState>;
  }

  const selectedItem = selected
    ? items.find((item) => item.route_no === selected.route)
    : null;
  const selectedValue = selectedItem && selected
    ? selectedItem.values[months.indexOf(selected.month)]
    : null;

  return (
    <div>
      <div className="observatory-legend" aria-label="Heatmap legend">
        <span className="observatory-legend-item">
          <span className="observatory-swatch" /> Low
        </span>
        <span className="observatory-legend-item">
          <span className="observatory-swatch is-warning" /> High
        </span>
        <span>
          {normalize ? "Per-route min/max normalization" : `${metricLabel(metric)} scale · max ${formatMetricValue(metric, globalMax)}`}
        </span>
      </div>
      <div className="observatory-heatmap-scroll">
        <table className="observatory-heatmap">
          <thead>
            <tr>
              <th scope="col">Route</th>
              {months.map((month) => (
                <th key={month} scope="col">
                  {month.slice(2)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const present = item.values.filter(
                (value): value is number => value !== null,
              );
              const min = present.length ? Math.min(...present) : 0;
              const max = present.length ? Math.max(...present) : 1;
              return (
                <tr key={item.route_no}>
                  <th scope="row">{item.route_no}</th>
                  {item.values.map((value, index) => {
                    const month = months[index];
                    const ratio =
                      value === null
                        ? 0
                        : normalize
                          ? max === min
                            ? 0.5
                            : (value - min) / (max - min)
                          : metric === "punctuality" || metric === "reliability"
                            ? value
                            : value / globalMax;
                    return (
                      <td
                        key={`${item.route_no}-${month}`}
                        className={
                          value === null
                            ? "observatory-heat-missing"
                            : colourClass(ratio)
                        }
                        tabIndex={value === null ? -1 : 0}
                        role={value === null ? undefined : "button"}
                        aria-label={
                          value === null
                            ? `${item.route_no} ${month}: no data`
                            : `${item.route_no} ${month}: ${formatMetricValue(metric, value)}`
                        }
                        onClick={() => value !== null && setSelected({ route: item.route_no, month })}
                        onKeyDown={(event) => {
                          if (value === null) return;
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            setSelected({ route: item.route_no, month });
                          }
                        }}
                      >
                        {value === null ? "–" : formatMetricValue(metric, value)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {selected && selectedValue !== null ? (
        <DataDetail
          title={`Route ${selected.route} · ${selected.month}`}
          fields={[
            {
              label: metricLabel(metric),
              value: formatMetricValue(metric, selectedValue),
            },
            { label: "Normalized", value: normalize ? "Per route" : "Shared scale" },
          ]}
          onClear={() => setSelected(null)}
        />
      ) : null}
    </div>
  );
}
