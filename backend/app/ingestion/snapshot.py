"""Thread-safe in-memory store for the latest realtime snapshot."""

from __future__ import annotations

import threading
from collections.abc import Iterable
from datetime import datetime

from .models import RealtimeSnapshot, ServiceAlert, TripUpdate, VehiclePosition

BoundingBox = tuple[float, float, float, float]  # min_lat, min_lon, max_lat, max_lon


class SnapshotStore:
    """Holds exactly one full snapshot plus polling health information."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snapshot: RealtimeSnapshot | None = None
        self._last_error: str | None = None
        self._successful_polls = 0
        self._failed_polls = 0
        self._last_success_at: datetime | None = None

    def publish(self, snapshot: RealtimeSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot
            self._successful_polls += 1
            self._last_success_at = snapshot.fetched_at
            self._last_error = None

    def record_error(self, message: str) -> None:
        with self._lock:
            self._failed_polls += 1
            self._last_error = message[:300]

    @property
    def snapshot(self) -> RealtimeSnapshot | None:
        with self._lock:
            return self._snapshot

    def health(self) -> dict[str, object]:
        with self._lock:
            snapshot = self._snapshot
            return {
                "has_data": snapshot is not None,
                "last_success_at": self._last_success_at,
                "feed_timestamp": snapshot.feed_timestamp if snapshot else None,
                "vehicle_count": len(snapshot.vehicles) if snapshot else 0,
                "trip_update_count": len(snapshot.trip_updates) if snapshot else 0,
                "alert_count": len(snapshot.alerts) if snapshot else 0,
                "successful_polls": self._successful_polls,
                "failed_polls": self._failed_polls,
                "last_error": self._last_error,
            }

    def vehicles(
        self,
        *,
        route_id: str | None = None,
        bbox: BoundingBox | None = None,
        limit: int = 500,
    ) -> list[VehiclePosition]:
        return list(self._filter(self._vehicles(), route_id, bbox, limit))

    def trip_updates(
        self, *, route_id: str | None = None, limit: int = 200
    ) -> list[TripUpdate]:
        items: Iterable[TripUpdate] = self._trip_updates()
        if route_id:
            items = (item for item in items if item.route_id == route_id)
        return list(items)[:limit]

    def alerts(self, *, route_id: str | None = None, limit: int = 100) -> list[ServiceAlert]:
        items: Iterable[ServiceAlert] = self._alerts()
        if route_id:
            items = (item for item in items if route_id in item.route_ids)
        return list(items)[:limit]

    def _vehicles(self) -> tuple[VehiclePosition, ...]:
        snapshot = self.snapshot
        return snapshot.vehicles if snapshot else ()

    def _trip_updates(self) -> tuple[TripUpdate, ...]:
        snapshot = self.snapshot
        return snapshot.trip_updates if snapshot else ()

    def _alerts(self) -> tuple[ServiceAlert, ...]:
        snapshot = self.snapshot
        return snapshot.alerts if snapshot else ()

    @staticmethod
    def _filter(items, route_id, bbox, limit):
        count = 0
        for item in items:
            if route_id and item.route_id != route_id:
                continue
            if bbox is not None:
                min_lat, min_lon, max_lat, max_lon = bbox
                if not (min_lat <= item.lat <= max_lat and min_lon <= item.lon <= max_lon):
                    continue
            yield item
            count += 1
            if count >= limit:
                return
