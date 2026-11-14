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
