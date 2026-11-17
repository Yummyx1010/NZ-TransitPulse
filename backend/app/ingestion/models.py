"""Typed, immutable views of the decoded AT realtime feed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VehiclePosition:
    vehicle_id: str
    lat: float
    lon: float
    bearing: float | None = None
    speed: float | None = None
    timestamp: int | None = None
    trip_id: str | None = None
    route_id: str | None = None


@dataclass(frozen=True)
class StopTimeUpdate:
    stop_id: str
    stop_sequence: int | None = None
    arrival_delay: int | None = None
    departure_delay: int | None = None
    arrival_time: int | None = None
    departure_time: int | None = None


@dataclass(frozen=True)
class TripUpdate:
    trip_id: str
    route_id: str | None = None
    start_date: str | None = None
    start_time: str | None = None
    direction_id: int | None = None
    schedule_relationship: int | None = None
    delay_seconds: int | None = None
    timestamp: int | None = None
    stop_updates: tuple[StopTimeUpdate, ...] = ()


@dataclass(frozen=True)
class ServiceAlert:
    alert_id: str
    cause: str | None = None
    effect: str | None = None
    header: str | None = None
    description: str | None = None
    active_periods: tuple[tuple[int | None, int | None], ...] = ()
    route_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RealtimeSnapshot:
    """One full snapshot of the aggregated GTFS-Realtime feed."""

    feed_timestamp: float | None
    fetched_at: datetime
    vehicles: tuple[VehiclePosition, ...]
    trip_updates: tuple[TripUpdate, ...]
    alerts: tuple[ServiceAlert, ...]
