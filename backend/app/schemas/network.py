"""Response schemas for the static network explorer."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..core.constants import ATTRIBUTION


class FeedInfo(BaseModel):
    id: int
    source: str
    checksum: str
    imported_at: datetime
    route_count: int
    stop_count: int
    trip_count: int
    stop_time_count: int


class NetworkStatus(BaseModel):
    has_data: bool
    active_feed: FeedInfo | None = None
    totals: dict[str, int] = {}
    attribution: str = ATTRIBUTION


class RouteSummary(BaseModel):
    route_id: str
    short_name: str
    long_name: str
    route_type: int
    mode: str
    colour: str | None = None


class RouteDetail(RouteSummary):
    agency_id: str | None = None
    description: str | None = None
    url: str | None = None
    stop_count: int = 0


class StopSummary(BaseModel):
    stop_id: str
    code: str | None = None
    name: str
    lat: float
    lon: float
    location_type: int = 0


class StopDetail(StopSummary):
    description: str | None = None
    zone_id: str | None = None
    parent_station: str | None = None
    wheelchair_boarding: int | None = None
    routes: list[RouteSummary] = []


class RouteListResponse(BaseModel):
    items: list[RouteSummary]
    total: int
    limit: int
    offset: int


class StopListResponse(BaseModel):
    items: list[StopSummary]
    total: int
    limit: int
    offset: int
