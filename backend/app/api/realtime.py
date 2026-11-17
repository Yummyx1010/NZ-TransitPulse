"""Read-only API over the in-memory GTFS-Realtime snapshot."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.modes import mode_label
from ..db.session import get_db
from ..ingestion.client import CallBudget
from ..ingestion.poller import RealtimePoller
from ..ingestion.snapshot import BoundingBox, SnapshotStore
from ..models import GtfsFeed, Route, Trip
from ..schemas.realtime import (
    RealtimeAlert,
    RealtimeAlertList,
    RealtimeStatus,
    RealtimeStopTimeUpdate,
    RealtimeTripUpdate,
    RealtimeTripUpdateList,
    RealtimeVehicle,
    RealtimeVehicleList,
)


def _parse_bbox(value: str | None) -> BoundingBox | None:
    if value is None:
        return None
    parts = value.split(",")
    if len(parts) != 4:
        raise HTTPException(400, "bbox must be min_lat,min_lon,max_lat,max_lon")
    try:
        min_lat, min_lon, max_lat, max_lon = (float(part.strip()) for part in parts)
    except ValueError as exc:
        raise HTTPException(400, "bbox values must be numbers") from exc
    if not (
        -90 <= min_lat < max_lat <= 90 and -180 <= min_lon < max_lon <= 180
    ):
        raise HTTPException(400, "bbox bounds are invalid or out of range")
    return min_lat, min_lon, max_lat, max_lon


def _route_labels(
    db: Session, route_ids: set[str]
) -> dict[str, tuple[str | None, str]]:
    """Best-effort static join; realtime reads survive a database outage."""
    if not route_ids:
        return {}
    try:
        feed_id = db.scalar(
            select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True)).limit(1)
        )
        rows = db.execute(
            select(Route.route_id, Route.short_name, Route.route_type).where(
                Route.feed_id == feed_id, Route.route_id.in_(route_ids)
            )
        ).all()
        return {row[0]: (row[1], mode_label(row[2])) for row in rows}
    except SQLAlchemyError:
        return {}


def _trip_ids_for_shape(db: Session, shape_id: str) -> set[str] | None:
    """Trip ids running one GTFS shape; None means the lookup is unavailable."""
    try:
        feed_id = db.scalar(
            select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True)).limit(1)
        )
        if feed_id is None:
            return None
        rows = db.execute(
            select(Trip.trip_id).where(
                Trip.feed_id == feed_id, Trip.shape_id == shape_id
            )
        ).scalars().all()
        return set(rows)
    except SQLAlchemyError:
        return None


def create_realtime_router(
    settings: Settings,
    store: SnapshotStore,
    budget: CallBudget,
    poller: RealtimePoller,
) -> APIRouter:
    router = APIRouter(prefix=f"{settings.api_v1_prefix}/realtime", tags=["realtime"])

    @router.get("/status", response_model=RealtimeStatus, summary="Realtime feed health")
    def status() -> RealtimeStatus:
        health = store.health()
        return RealtimeStatus(
            configured=settings.realtime_configured,
            polling=poller.is_running,
            has_data=bool(health["has_data"]),
            last_success_at=health["last_success_at"],
            feed_timestamp=health["feed_timestamp"],
            vehicle_count=int(health["vehicle_count"]),
            trip_update_count=int(health["trip_update_count"]),
            alert_count=int(health["alert_count"]),
            successful_polls=int(health["successful_polls"]),
            failed_polls=int(health["failed_polls"]),
            last_error=health["last_error"],
            poll_seconds=settings.at_realtime_poll_seconds,
            calls_last_7_days=budget.calls_in_window(),
            weekly_quota=budget.limit,
            quota_remaining=budget.remaining(),
            source=settings.at_realtime_url,
        )

    @router.get("/vehicles", response_model=RealtimeVehicleList, summary="Live vehicles")
    def vehicles(
        route_id: str | None = None,
        mode: str | None = Query(None, description="Bus, Rail, Ferry, ..."),
        shape_id: str | None = Query(
            None, description="Only vehicles running this shape's trips"
        ),
        bbox: str | None = Query(None, description="min_lat,min_lon,max_lat,max_lon"),
        limit: int = Query(500, ge=1, le=2000),
        db: Session = Depends(get_db),
    ) -> RealtimeVehicleList:
        all_vehicles = store.vehicles(
            route_id=route_id, bbox=_parse_bbox(bbox), limit=5000
        )
        labels = _route_labels(
            db, {vehicle.route_id for vehicle in all_vehicles if vehicle.route_id}
        )
        if mode:
            wanted = mode.strip().lower()
            all_vehicles = [
                vehicle
                for vehicle in all_vehicles
                if (labels.get(vehicle.route_id, (None, None))[1] or "").lower() == wanted
            ]
        if shape_id:
            trip_ids = _trip_ids_for_shape(db, shape_id)
            if trip_ids is not None:
                all_vehicles = [
                    vehicle for vehicle in all_vehicles if vehicle.trip_id in trip_ids
                ]
        page = all_vehicles[:limit]
        items = []
        for vehicle in page:
            short_name, mode = labels.get(vehicle.route_id, (None, None))
            items.append(
                RealtimeVehicle(
                    vehicle_id=vehicle.vehicle_id,
                    lat=vehicle.lat,
                    lon=vehicle.lon,
                    bearing=vehicle.bearing,
                    speed=vehicle.speed,
                    route_id=vehicle.route_id,
                    route_short_name=short_name,
                    mode=mode,
                    trip_id=vehicle.trip_id,
                    timestamp=vehicle.timestamp,
                )
            )
        return RealtimeVehicleList(items=items, total=len(all_vehicles), limit=limit)

    @router.get(
        "/trip-updates",
        response_model=RealtimeTripUpdateList,
        summary="Live trip updates",
    )
    def trip_updates(
        route_id: str | None = None,
        limit: int = Query(200, ge=1, le=1000),
        db: Session = Depends(get_db),
    ) -> RealtimeTripUpdateList:
        all_updates = store.trip_updates(route_id=route_id, limit=2000)
        labels = _route_labels(
            db, {update.route_id for update in all_updates if update.route_id}
        )
        page = all_updates[:limit]
        items = [
            RealtimeTripUpdate(
                trip_id=update.trip_id,
                route_id=update.route_id,
                route_short_name=labels.get(update.route_id, (None, None))[0],
                start_date=update.start_date,
                start_time=update.start_time,
                direction_id=update.direction_id,
                schedule_relationship=update.schedule_relationship,
                delay_seconds=update.delay_seconds,
                timestamp=update.timestamp,
                stop_updates=[
                    RealtimeStopTimeUpdate(
                        stop_id=stop.stop_id,
                        stop_sequence=stop.stop_sequence,
                        arrival_delay=stop.arrival_delay,
                        departure_delay=stop.departure_delay,
                        arrival_time=stop.arrival_time,
                        departure_time=stop.departure_time,
                    )
                    for stop in update.stop_updates
                ],
            )
            for update in page
        ]
        return RealtimeTripUpdateList(items=items, total=len(all_updates), limit=limit)

    @router.get("/alerts", response_model=RealtimeAlertList, summary="Service alerts")
    def alerts(
        route_id: str | None = None,
        mode: str | None = Query(None, description="Only alerts affecting this mode"),
        limit: int = Query(100, ge=1, le=500),
        db: Session = Depends(get_db),
    ) -> RealtimeAlertList:
        all_alerts = store.alerts(route_id=route_id, limit=1000)
        if mode:
            route_ids = {rid for alert in all_alerts for rid in alert.route_ids}
            labels = _route_labels(db, route_ids)
            wanted = mode.strip().lower()
            all_alerts = [
                alert
                for alert in all_alerts
                if not alert.route_ids
                or any(
                    (labels.get(rid, (None, None))[1] or "").lower() == wanted
                    for rid in alert.route_ids
                )
            ]
        page = all_alerts[:limit]
        items = [
            RealtimeAlert(
                alert_id=alert.alert_id,
                cause=alert.cause,
                effect=alert.effect,
                header=alert.header,
                description=alert.description,
                active_periods=[list(period) for period in alert.active_periods],
                route_ids=list(alert.route_ids),
            )
            for alert in page
        ]
        return RealtimeAlertList(items=items, total=len(all_alerts), limit=limit)

    return router
