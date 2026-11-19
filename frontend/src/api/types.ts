export interface RouteSummary {
  route_id: string;
  short_name: string;
  long_name: string;
  route_type: number;
  mode: string;
  colour: string | null;
}

export interface StopSummary {
  stop_id: string;
  code: string | null;
  name: string;
  lat: number;
  lon: number;
  location_type: number;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ActiveFeed {
  id: number;
  source: string;
  checksum: string;
  imported_at: string;
  route_count: number;
  stop_count: number;
  trip_count: number;
  stop_time_count: number;
}

export interface NetworkStatus {
  has_data: boolean;
  active_feed: ActiveFeed | null;
  totals: Record<string, number>;
  attribution: string;
}

export interface RouteQuery {
  q?: string;
  mode?: string;
  limit?: number;
}

export interface ShapeGeometry {
  shape_id: string;
  label: string;
  trip_count: number;
  direction_id: number | null;
  headsign: string | null;
  points: [number, number][];
  stops: StopSummary[];
}

export interface RouteGeometry {
  route_id: string;
  source: "shapes" | "stop_times";
  approximate: boolean;
  note: string;
  shape_count: number;
  shapes: ShapeGeometry[];
}

export interface RealtimeVehicle {
  vehicle_id: string;
  lat: number;
  lon: number;
  bearing: number | null;
  speed: number | null;
  route_id: string | null;
  route_short_name: string | null;
  mode: string | null;
  trip_id: string | null;
  timestamp: number | null;
}

export interface RealtimeVehicleList {
  items: RealtimeVehicle[];
  total: number;
  limit: number;
}

export interface RealtimeVehicleQuery {
  route_id?: string;
  mode?: string;
  shape_id?: string;
  bbox?: string;
  limit?: number;
}

export interface ArrivalItem {
  trip_id: string;
  route_id: string;
  route_short_name: string;
  headsign: string | null;
  direction_id: number | null;
  scheduled_seconds: number;
  scheduled_time: string;
  predicted_seconds: number | null;
  predicted_time: string | null;
  delay_seconds: number | null;
  minutes_away: number;
  status: string;
  source: string;
}

export interface ArrivalsResponse {
  stop_id: string;
  stop_name: string;
  included_stop_ids: string[];
  route_id: string | null;
  window_minutes: number;
  timezone: string;
  realtime_available: boolean;
  total: number;
  items: ArrivalItem[];
  note: string;
  attribution: string;
}

export interface RealtimeAlert {
  alert_id: string;
  cause: string | null;
  effect: string | null;
  header: string | null;
  description: string | null;
  active_periods: (number | null)[][];
  route_ids: string[];
}

export interface RealtimeAlertList {
  items: RealtimeAlert[];
  total: number;
  limit: number;
}

export interface StopArrivalsQuery {
  route_id?: string;
  minutes?: number;
  limit?: number;
}

export interface RealtimeAlertQuery {
  route_id?: string;
  mode?: string;
  limit?: number;
}

export interface RealtimeStatus {
  configured: boolean;
  polling: boolean;
  has_data: boolean;
  last_success_at: string | null;
  feed_timestamp: number | null;
  vehicle_count: number;
  trip_update_count: number;
  alert_count: number;
  successful_polls: number;
  failed_polls: number;
  last_error: string | null;
  poll_seconds: number;
  calls_last_7_days: number;
  weekly_quota: number;
  quota_remaining: number;
  source: string;
  attribution: string;
}

export type AnalyticsMetric =
  | "punctuality"
  | "reliability"
  | "boardings"
  | "boardings_per_service_hour";

export interface AnalyticsQuery {
  metric: AnalyticsMetric;
  startMonth?: string;
  endMonth?: string;
  includeSchoolRoutes?: boolean;
  limit?: number;
}

export interface AnalyticsSummary {
  report_count: number;
  metrics: Record<
    string,
    {
      first_month: string;
      last_month: string;
      months: number;
      sufficiency: "none" | "limited" | "moderate" | "strong";
    }
  >;
  attribution: string;
}

export interface RouteRankingItem {
  route_no: string;
  route_name: string | null;
  sample_months: number;
  first_month: string;
  last_month: string;
  first_value: number | null;
  latest_value: number | null;
  change: number | null;
  average_value: number;
}

export interface TrendPoint {
  month: string;
  value: number;
  sample_count: number;
}

export interface HeatmapItem {
  route_no: string;
  route_name: string | null;
  values: (number | null)[];
}

export interface ScatterPoint {
  route_no: string;
  route_name: string | null;
  boardings: number;
  punctuality: number;
  sample_months: number;
  first_month: string;
  last_month: string;
}

export interface NetworkSummary {
  has_data: boolean;
  bus_routes: number;
  stops: number;
  scheduled_trips: number;
  shape_points: number;
  stop_time_rows: number;
  avg_stop_times_per_trip: number | null;
}

export interface MetricMetadata {
  label: string;
  short_label: string;
  unit: string;
  definition: string;
  source_family: string;
  kind: "service" | "ridership";
  higher_is_better: boolean;
  first_month: string | null;
  last_month: string | null;
  months: number;
  sufficiency: "none" | "limited" | "moderate" | "strong";
}

export interface RouteCatalogItem {
  route_no: string;
  route_ids: string[];
  route_name: string | null;
  matched_in_gtfs: boolean;
}

export interface OfficialMetricPoint {
  month: string;
  value: number;
}

export interface CorrelationResult {
  available: boolean;
  method: "spearman";
  coefficient?: number;
  sample_size: number;
  reason: string | null;
}

export interface AnalyticsMeta {
  unit?: string;
  definition?: string;
  source_family?: string;
  metric_kind?: "service" | "ridership";
  higher_is_better?: boolean;
  source_coverage?: {
    first_month: string | null;
    last_month: string | null;
    months: number;
    sufficiency: string;
  };
  warning?: string | null;
}

export interface AnalyticsRankingResponse extends AnalyticsMeta {
  metric: string;
  total: number;
  items: RouteRankingItem[];
}

export interface AnalyticsTrendResponse extends AnalyticsMeta {
  metric: string;
  route_no: string | null;
  total: number;
  items: TrendPoint[];
}

export interface AnalyticsHeatmapResponse extends AnalyticsMeta {
  metric: string;
  months: string[];
  total: number;
  items: HeatmapItem[];
}
