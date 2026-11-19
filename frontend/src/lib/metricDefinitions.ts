import type { AnalyticsMetric } from "../api/types";

export type MetricKind = "service" | "ridership";

export interface MetricDefinition {
  key: AnalyticsMetric;
  label: string;
  shortLabel: string;
  unit: string;
  definition: string;
  sourceFamily: string;
  kind: MetricKind;
  higherIsBetter: boolean;
}

export const METRIC_DEFINITIONS: Record<AnalyticsMetric, MetricDefinition> = {
  punctuality: {
    key: "punctuality",
    label: "Official punctuality",
    shortLabel: "Punctuality",
    unit: "%",
    definition:
      "AT punctuality: departs the first stop no earlier than 1 minute and no later than 5 minutes; arrives at the last stop no later than 5 minutes after schedule.",
    sourceFamily: "Monthly punctuality and reliability",
    kind: "service",
    higherIsBetter: true,
  },
  reliability: {
    key: "reliability",
    label: "Official reliability",
    shortLabel: "Reliability",
    unit: "%",
    definition:
      "AT reliability: departs the first stop no earlier than 1 minute and no later than 10 minutes after schedule.",
    sourceFamily: "Monthly punctuality and reliability",
    kind: "service",
    higherIsBetter: true,
  },
  boardings: {
    key: "boardings",
    label: "Estimated boardings",
    shortLabel: "Boardings",
    unit: "passenger trips",
    definition:
      "Monthly boardings estimated from AT fare transactions. Ridership is not an operational performance measure.",
    sourceFamily: "AT bus performance reports",
    kind: "ridership",
    higherIsBetter: true,
  },
  boardings_per_service_hour: {
    key: "boardings_per_service_hour",
    label: "Boardings per service hour",
    shortLabel: "Boardings / hour",
    unit: "boardings per service hour",
    definition:
      "Weekday boardings divided by scheduled weekday service hours. A higher value indicates stronger use of scheduled supply, not better punctuality.",
    sourceFamily: "AT hourly bus boardings reports",
    kind: "ridership",
    higherIsBetter: true,
  },
};

export function getMetricDefinition(metric: AnalyticsMetric): MetricDefinition {
  return METRIC_DEFINITIONS[metric];
}
