import type { AnalyticsMetric } from "../../api/types";
import { useAnalyticsFilters } from "../../hooks/useAnalyticsFilters";
import {
  listMonthValues,
  MONTH_NAMES,
  monthLabel,
  monthsForYear,
  yearsForMonths,
} from "../../lib/analytics";
import { METRIC_DEFINITIONS } from "../../lib/metricDefinitions";

interface FilterBarProps {
  firstMonth: string;
  lastMonth: string;
  showNormalize?: boolean;
  allowedMetrics?: AnalyticsMetric[];
}

function MonthSelect({
  label,
  value,
  values,
  onChange,
}: {
  label: string;
  value: string;
  values: string[];
  onChange: (value: string) => void;
}) {
  const years = yearsForMonths(values);
  const year = value.slice(0, 4);
  const month = value.slice(5, 7);
  const monthsInYear = monthsForYear(values, year);

  function handleYearChange(nextYear: string) {
    const candidates = monthsForYear(values, nextYear);
    const preferred =
      candidates.find((candidate) => candidate.slice(5, 7) === month) ?? candidates[0];
    if (preferred) onChange(preferred);
  }

  function handleMonthChange(nextMonth: string) {
    const next = `${year}-${nextMonth}`;
    if (values.includes(next)) {
      onChange(next);
      return;
    }
    const nearest = [...monthsInYear].sort(
      (a, b) =>
        Math.abs(Number(a.slice(5, 7)) - Number(nextMonth)) -
        Math.abs(Number(b.slice(5, 7)) - Number(nextMonth)),
    )[0];
    if (nearest) onChange(nearest);
  }

  return (
    <div className="observatory-field" role="group" aria-label={`${label} date`}>
      <span>{label}</span>
      <div className="observatory-field-row">
        <select
          aria-label={`${label} year`}
          value={year}
          onChange={(event) => handleYearChange(event.target.value)}
        >
          {years.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <select
          aria-label={`${label} month`}
          value={month}
          onChange={(event) => handleMonthChange(event.target.value)}
        >
          {MONTH_NAMES.map((name, index) => {
            const number = String(index + 1).padStart(2, "0");
            return (
              <option
                key={number}
                value={number}
                disabled={!monthsInYear.some((item) => item.slice(5, 7) === number)}
              >
                {name}
              </option>
            );
          })}
        </select>
      </div>
    </div>
  );
}

export function FilterBar({
  firstMonth,
  lastMonth,
  showNormalize = false,
  allowedMetrics,
}: FilterBarProps) {
  const { filters, setMetric, setRange, setIncludeSchoolRoutes, setNormalizeHeatmap } =
    useAnalyticsFilters();
  const values = listMonthValues(firstMonth, lastMonth);
  const metricKeys = allowedMetrics ?? (Object.keys(METRIC_DEFINITIONS) as AnalyticsMetric[]);
  const metricOptions = metricKeys.map((metric) => METRIC_DEFINITIONS[metric]);

  return (
    <div className="observatory-filter-bar" aria-label="Analytics filters">
      <label className="observatory-field">
        <span>Metric</span>
        <select
          aria-label="Analytics metric"
          value={filters.metric}
          onChange={(event) => setMetric(event.target.value as AnalyticsMetric)}
        >
          {metricOptions.map((metric) => (
            <option key={metric.key} value={metric.key}>
              {metric.label}
            </option>
          ))}
        </select>
      </label>
      <MonthSelect
        label="From"
        value={filters.from}
        values={values}
        onChange={(from) => setRange(from, filters.to)}
      />
      <MonthSelect
        label="To"
        value={filters.to}
        values={values}
        onChange={(to) => setRange(filters.from, to)}
      />
      <label className="observatory-checkbox">
        <input
          type="checkbox"
          checked={filters.includeSchoolRoutes}
          onChange={(event) => setIncludeSchoolRoutes(event.target.checked)}
        />
        Include school routes
      </label>
      {showNormalize ? (
        <label className="observatory-checkbox">
          <input
            type="checkbox"
            checked={filters.normalizeHeatmap}
            onChange={(event) => setNormalizeHeatmap(event.target.checked)}
          />
          Normalize each route
        </label>
      ) : null}
      <span className="observatory-panel-meta">
        {monthLabel(filters.from)} – {monthLabel(filters.to)}
      </span>
    </div>
  );
}
