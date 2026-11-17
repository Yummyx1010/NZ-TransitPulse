"""Response schemas for the GTFS-Realtime API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..core.constants import ATTRIBUTION


class RealtimeVehicle(BaseModel):
    vehicle_id: str
    lat: float
    lon: float
    bearing: float | None = None
    speed: float | None = None
    route_id: str | None = None
    route_short_name: str | None = None
    mode: str | None = None
    trip_id: str | None = None
    timestamp: int | None = None


class RealtimeVehicleList(BaseModel):
    items: list[RealtimeVehicle]
    total: int
    limit: int


class RealtimeStopTimeUpdate(BaseModel):
    stop_id: str
    stop_sequence: int | None = None
    arrival_delay: int | None = None
    departure_delay: int | None = None
    arrival_time: int | None = None
    departure_time: int | None = None


class RealtimeTripUpdate(BaseModel):
    trip_id: str
    route_id: str | None = None
    route_short_name: str | None = None
    start_date: str | None = None
    start_time: str | None = None
    direction_id: int | None = None
    schedule_relationship: int | None = None
    delay_seconds: int | None = None
    timestamp: int | None = None
    stop_updates: list[RealtimeStopTimeUpdate] = []


class RealtimeTripUpdateList(BaseModel):
    items: list[RealtimeTripUpdate]
    total: int
    limit: int


class RealtimeAlert(BaseModel):
    alert_id: str
    cause: str | None = None
    effect: str | None = None
    header: str | None = None
    description: str | None = None
    active_periods: list[list[int | None]] = []
    route_ids: list[str] = []


class RealtimeAlertList(BaseModel):
    items: list[RealtimeAlert]
    total: int
    limit: int


class RealtimeStatus(BaseModel):
    configured: bool
    polling: bool
    has_data: bool
    last_success_at: datetime | None = None
    feed_timestamp: float | None = None
    vehicle_count: int = 0
    trip_update_count: int = 0
    alert_count: int = 0
    successful_polls: int = 0
    failed_polls: int = 0
    last_error: str | None = None
    poll_seconds: int
    calls_last_7_days: int = 0
    weekly_quota: int
    quota_remaining: int
    source: str
    attribution: str = ATTRIBUTION
