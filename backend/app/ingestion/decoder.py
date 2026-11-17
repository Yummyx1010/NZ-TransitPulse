"""Decode the AT aggregated GTFS-Realtime JSON envelope.

AT wraps the GTFS-RT message in ``{status, response: {header, entity}, error}`` and
serialises single-element repeated fields as objects instead of arrays. This decoder
accepts both shapes and skips malformed entities rather than failing the whole feed.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from .models import (
    RealtimeSnapshot,
    ServiceAlert,
    StopTimeUpdate,
    TripUpdate,
    VehiclePosition,
)


class FeedDecodeError(ValueError):
    """Raised when the feed envelope is unusable."""


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    number = _as_float(value)
    return int(number) if number is not None else None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _translation_text(value: Any) -> str | None:
    """Read GTFS translated text such as ``header_text`` / ``description_text``."""
    if isinstance(value, str):
        return value
    for item in _as_list(value.get("translation") if isinstance(value, dict) else None):
        if isinstance(item, dict) and item.get("text"):
            return _as_str(item.get("text"))
    return None


def _decode_vehicle(entity: dict[str, Any]) -> VehiclePosition | None:
    vehicle = entity.get("vehicle")
    if not isinstance(vehicle, dict):
        return None
    position = vehicle.get("position")
    if not isinstance(position, dict):
        return None
    lat = _as_float(position.get("latitude"))
    lon = _as_float(position.get("longitude"))
    if lat is None or lon is None:
        return None
    descriptor = vehicle.get("vehicle")
    trip = vehicle.get("trip")
    descriptor = descriptor if isinstance(descriptor, dict) else {}
    trip = trip if isinstance(trip, dict) else {}
    return VehiclePosition(
        vehicle_id=_as_str(descriptor.get("id")) or _as_str(entity.get("id")) or "",
        lat=lat,
        lon=lon,
        bearing=_as_float(position.get("bearing")),
        speed=_as_float(position.get("speed")),
        timestamp=_as_int(vehicle.get("timestamp")),
        trip_id=_as_str(trip.get("trip_id")),
        route_id=_as_str(trip.get("route_id")),
    )


def _decode_stop_time_updates(value: Any) -> tuple[StopTimeUpdate, ...]:
    updates: list[StopTimeUpdate] = []
    for raw in _as_list(value):
        if not isinstance(raw, dict):
            continue
        arrival = raw.get("arrival")
        departure = raw.get("departure")
        arrival = arrival if isinstance(arrival, dict) else {}
        departure = departure if isinstance(departure, dict) else {}
        stop_id = _as_str(raw.get("stop_id"))
        if stop_id is None:
            continue
        updates.append(
            StopTimeUpdate(
                stop_id=stop_id,
                stop_sequence=_as_int(raw.get("stop_sequence")),
                arrival_delay=_as_int(arrival.get("delay")),
                departure_delay=_as_int(departure.get("delay")),
                arrival_time=_as_int(arrival.get("time")),
                departure_time=_as_int(departure.get("time")),
            )
        )
    return tuple(updates)


def _decode_trip_update(entity: dict[str, Any]) -> TripUpdate | None:
    update = entity.get("trip_update")
    if not isinstance(update, dict):
        return None
    trip = update.get("trip")
    trip = trip if isinstance(trip, dict) else {}
    trip_id = _as_str(trip.get("trip_id"))
    if trip_id is None:
        return None
    return TripUpdate(
        trip_id=trip_id,
        route_id=_as_str(trip.get("route_id")),
        start_date=_as_str(trip.get("start_date")),
        start_time=_as_str(trip.get("start_time")),
        direction_id=_as_int(trip.get("direction_id")),
        schedule_relationship=_as_int(trip.get("schedule_relationship")),
        delay_seconds=_as_int(update.get("delay")),
        timestamp=_as_int(update.get("timestamp")),
        stop_updates=_decode_stop_time_updates(update.get("stop_time_update")),
    )


def _decode_alert(entity: dict[str, Any]) -> ServiceAlert | None:
    alert = entity.get("alert")
    if not isinstance(alert, dict):
        return None
    periods: list[tuple[int | None, int | None]] = []
    for raw in _as_list(alert.get("active_period")):
        if isinstance(raw, dict):
            periods.append((_as_int(raw.get("start")), _as_int(raw.get("end"))))
    route_ids: list[str] = []
    for informed in _as_list(alert.get("informed_entity")):
        if isinstance(informed, dict):
            route_id = _as_str(informed.get("route_id"))
            if route_id:
                route_ids.append(route_id)
    return ServiceAlert(
        alert_id=_as_str(entity.get("id")) or "",
        cause=_as_str(alert.get("cause")),
        effect=_as_str(alert.get("effect")),
        header=_translation_text(alert.get("header_text")),
        description=_translation_text(alert.get("description_text")),
        active_periods=tuple(periods),
        route_ids=tuple(route_ids),
    )


def decode_feed(
    payload: Any, *, fetched_at: datetime | None = None
) -> RealtimeSnapshot:
    """Turn one aggregated AT response into a typed snapshot."""
    if not isinstance(payload, dict):
        raise FeedDecodeError("feed payload must be a JSON object")
    if payload.get("status") != "OK":
        raise FeedDecodeError(f"feed status is not OK: {payload.get('status')!r}")
    response = payload.get("response")
    if not isinstance(response, dict):
        raise FeedDecodeError("feed response is missing")
    header = response.get("header")
    header = header if isinstance(header, dict) else {}

    vehicles: list[VehiclePosition] = []
    trip_updates: list[TripUpdate] = []
    alerts: list[ServiceAlert] = []

    for entity in _as_list(response.get("entity")):
        if not isinstance(entity, dict) or entity.get("is_deleted"):
            continue
        if "vehicle" in entity:
            decoded = _decode_vehicle(entity)
            if decoded is not None:
                vehicles.append(decoded)
        elif "trip_update" in entity:
            decoded = _decode_trip_update(entity)
            if decoded is not None:
                trip_updates.append(decoded)
        elif "alert" in entity:
            decoded = _decode_alert(entity)
            if decoded is not None:
                alerts.append(decoded)

    # Many AT vehicle entities omit the trip descriptor. Recover route_id from the
    # trip updates in the same snapshot so the map can label those vehicles.
    route_by_trip = {
        update.trip_id: update.route_id
        for update in trip_updates
        if update.route_id
    }
    vehicles = [
        replace(vehicle, route_id=route_by_trip.get(vehicle.trip_id))
        if vehicle.route_id is None and vehicle.trip_id in route_by_trip
        else vehicle
        for vehicle in vehicles
    ]

    return RealtimeSnapshot(
        feed_timestamp=_as_float(header.get("timestamp")),
        fetched_at=fetched_at or datetime.now(UTC).replace(tzinfo=None),
        vehicles=tuple(vehicles),
        trip_updates=tuple(trip_updates),
        alerts=tuple(alerts),
    )
