import type { AnalyticsMetric } from "../api/types";

const RATIO_METRICS: AnalyticsMetric[] = ["punctuality", "reliability"];
export const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

export function listMonthValues(firstMonth: string, lastMonth: string): string[] {
  const [firstYear, first] = firstMonth.split("-").map(Number);
  const [lastYear, last] = lastMonth.split("-").map(Number);
  const values: string[] = [];
  for (let year = firstYear; year <= lastYear; year += 1) {
    const start = year === firstYear ? first : 1;
    const end = year === lastYear ? last : 12;
    for (let month = start; month <= end; month += 1) {
      values.push(`${year}-${String(month).padStart(2, "0")}`);
    }
  }
  return values;
}

export function monthLabel(value: string): string {
  const [year, month] = value.split("-");
  const index = Number(month) - 1;
  return `${MONTH_NAMES[index] ?? month} ${year}`;
}

export function yearsForMonths(values: string[]): string[] {
  return [...new Set(values.map((value) => value.slice(0, 4)))];
}

export function monthsForYear(values: string[], year: string): string[] {
  return values.filter((value) => value.startsWith(`${year}-`));
}

export function formatMetricValue(
  metric: AnalyticsMetric,
  value: number | null | undefined,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  if (RATIO_METRICS.includes(metric)) {
    return `${(Math.round(value * 1000) / 10).toFixed(1)}%`;
  }
  if (metric === "boardings") return Math.round(value).toLocaleString("en-NZ");
  return value.toFixed(1);
}

export function formatChange(
  metric: AnalyticsMetric,
  change: number | null | undefined,
): string {
  if (change === null || change === undefined) return "n/a";
  const sign = change > 0 ? "+" : "";
  return RATIO_METRICS.includes(metric)
    ? `${sign}${(change * 100).toFixed(1)}pp`
    : `${sign}${Math.round(change).toLocaleString("en-NZ")}`;
}

export function metricLabel(metric: AnalyticsMetric): string {
  const labels: Record<AnalyticsMetric, string> = {
    punctuality: "Punctuality",
    reliability: "Reliability",
    boardings: "Boardings",
    boardings_per_service_hour: "Boardings / service hour",
  };
  return labels[metric];
}

export function heatColor(
  metric: AnalyticsMetric,
  value: number | null,
): string {
  if (value === null) return "heat-empty";
  const ratio = RATIO_METRICS.includes(metric) ? value : Math.min(value / 100, 1);
  if (ratio >= 0.9) return "heat-4";
  if (ratio >= 0.8) return "heat-3";
  if (ratio >= 0.7) return "heat-2";
  if (ratio >= 0.5) return "heat-1";
  return "heat-0";
}
