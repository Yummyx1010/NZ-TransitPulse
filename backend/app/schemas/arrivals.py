"""Response schemas for the passenger stop-arrival board."""

from __future__ import annotations

from pydantic import BaseModel

from ..core.constants import ATTRIBUTION


class ArrivalItem(BaseModel):
    trip_id: str
    route_id: str
    route_short_name: str
    headsign: str | None = None
    direction_id: int | None = None
    scheduled_seconds: int
    scheduled_time: str
    predicted_seconds: int | None = None
    predicted_time: str | None = None
    delay_seconds: int | None = None
    minutes_away: int
    status: str
    source: str


class ArrivalsResponse(BaseModel):
    stop_id: str
    stop_name: str
    included_stop_ids: list[str] = []
    route_id: str | None = None
    window_minutes: int
    timezone: str
    realtime_available: bool
    total: int
    items: list[ArrivalItem]
    note: str
    attribution: str = ATTRIBUTION
