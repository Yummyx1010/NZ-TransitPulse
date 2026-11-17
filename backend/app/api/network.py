"""Read-only API for exploring the Auckland static transit network."""

from __future__ import annotations

import math
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.constants import ATTRIBUTION
from ..core.modes import mode_from_label, mode_label
from ..db.session import get_db
from ..models import GtfsFeed, Route, ShapePoint, Stop, StopTime, Trip
from ..schemas.network import (
    FeedInfo,
    NetworkStatus,
    RouteDetail,
    RouteGeometry,
    RouteListResponse,
    RouteSummary,
    ShapeGeometry,
    StopDetail,
    StopListResponse,
    StopSummary,
)


def route_summary(route: Route) -> RouteSummary:
    return RouteSummary(
        route_id=route.route_id,
        short_name=route.short_name,
        long_name=route.long_name,
        route_type=route.route_type,
        mode=mode_label(route.route_type),
        colour=route.colour,
    )


def stop_summary(stop: Stop) -> StopSummary:
    return StopSummary(
        stop_id=stop.stop_id,
        code=stop.code,
        name=stop.name,
        lat=stop.lat,
        lon=stop.lon,
        location_type=stop.location_type,
    )


def _active_feed_id(db: Session) -> int | None:
    return db.scalar(select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True)).limit(1))


def _stop_ids_for_route(db: Session, feed_id: int, route_id: str):
    trip_ids = select(Trip.trip_id).where(
        Trip.feed_id == feed_id, Trip.route_id == route_id
    )
    return (
        select(StopTime.stop_id)
        .where(StopTime.feed_id == feed_id, StopTime.trip_id.in_(trip_ids))
        .distinct()
    )


def _shape_groups(db: Session, feed_id: int, route_id: str):
    """Distinct shapes used by this route, ordered by how many trips use them."""
    return db.execute(
        select(
            Trip.shape_id,
            func.count(Trip.trip_id),
            func.min(Trip.direction_id),
            func.min(Trip.headsign),
        )
        .where(
            Trip.feed_id == feed_id,
            Trip.route_id == route_id,
            Trip.shape_id.is_not(None),
            Trip.shape_id != "",
        )
        .group_by(Trip.shape_id)
        .order_by(func.count(Trip.trip_id).desc(), Trip.shape_id)
    ).all()


def _ordered_stop_ids(
    db: Session, feed_id: int, route_id: str, shape_id: str
) -> list[str]:
    """Distinct stop ids ordered by their first scheduled stop_sequence."""
    statement = (
        select(StopTime.stop_id, func.min(StopTime.stop_sequence).label("first_seq"))
        .join(
            Trip,
            and_(
                Trip.feed_id == StopTime.feed_id,
                Trip.trip_id == StopTime.trip_id,
            ),
        )
        .where(
            StopTime.feed_id == feed_id,
            Trip.route_id == route_id,
            Trip.shape_id == shape_id,
        )
        .group_by(StopTime.stop_id)
        .order_by(func.min(StopTime.stop_sequence), StopTime.stop_id)
    )
    return [row[0] for row in db.execute(statement).all()]


def _summaries_for_stop_ids(
    db: Session, feed_id: int, stop_ids: list[str]
) -> list[StopSummary]:
    """Load stop details while preserving the requested order."""
    if not stop_ids:
        return []
    found = db.scalars(
        select(Stop).where(Stop.feed_id == feed_id, Stop.stop_id.in_(stop_ids))
    ).all()
    by_id = {stop.stop_id: stop_summary(stop) for stop in found}
    return [by_id[stop_id] for stop_id in stop_ids if stop_id in by_id]


def _shape_points(db: Session, feed_id: int, shape_id: str) -> list[list[float]]:
    """Return shape points in their GTFS sequence order."""
    rows = db.execute(
        select(ShapePoint.lat, ShapePoint.lon)
        .where(ShapePoint.feed_id == feed_id, ShapePoint.shape_id == shape_id)
        .order_by(ShapePoint.shape_pt_sequence)
    ).all()
    return [[row[0], row[1]] for row in rows]


def _stop_time_patterns(
    db: Session, feed_id: int, route_id: str
) -> list[tuple[tuple[str, ...], int]]:
    """Group trips by their exact ordered stop sequence (shapes.txt fallback)."""
    rows = db.execute(
        select(StopTime.trip_id, StopTime.stop_sequence, StopTime.stop_id)
        .join(
            Trip,
            and_(
                Trip.feed_id == StopTime.feed_id,
                Trip.trip_id == StopTime.trip_id,
            ),
        )
        .where(StopTime.feed_id == feed_id, Trip.route_id == route_id)
        .order_by(StopTime.trip_id, StopTime.stop_sequence)
    ).all()
    by_trip: dict[str, list[str]] = defaultdict(list)
    for trip_id, _, stop_id in rows:
        by_trip[trip_id].append(stop_id)
    patterns: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for trip_id, sequence in by_trip.items():
        if sequence:
            patterns[tuple(sequence)].append(trip_id)
    ordered = sorted(
        patterns.items(), key=lambda item: (-len(item[1]), item[0])
    )
    return [(sequence, len(trip_ids)) for sequence, trip_ids in ordered]


def create_network_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix=settings.api_v1_prefix, tags=["network"])

    @router.get("/network/status", response_model=NetworkStatus, summary="Feed status")
    def network_status(db: Session = Depends(get_db)) -> NetworkStatus:
        feed = db.scalar(select(GtfsFeed).where(GtfsFeed.is_active.is_(True)))
        if feed is None:
            return NetworkStatus(has_data=False, attribution=ATTRIBUTION)
        return NetworkStatus(
            has_data=True,
            active_feed=FeedInfo.model_validate(feed, from_attributes=True),
            totals={
                "agencies": feed.agency_count,
                "routes": feed.route_count,
                "stops": feed.stop_count,
                "trips": feed.trip_count,
                "stop_times": feed.stop_time_count,
            },
            attribution=ATTRIBUTION,
        )

    @router.get("/routes", response_model=RouteListResponse, summary="List routes")
    def list_routes(
        q: str | None = Query(None, description="Search short name, long name or id"),
        mode: str | None = Query(None, description="Bus, Rail, Ferry or a GTFS route type"),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db),
    ) -> RouteListResponse:
        feed_id = _active_feed_id(db)
        if feed_id is None:
            return RouteListResponse(items=[], total=0, limit=limit, offset=offset)
        conditions = [Route.feed_id == feed_id]
        if q:
            pattern = f"%{q}%"
            conditions.append(
                or_(
                    Route.short_name.ilike(pattern),
                    Route.long_name.ilike(pattern),
                    Route.route_id.ilike(pattern),
                )
            )
        if mode:
            code = int(mode) if mode.isdigit() else mode_from_label(mode)
            if code is None:
                raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")
            conditions.append(Route.route_type == code)
        total = db.scalar(select(func.count()).select_from(Route).where(*conditions)) or 0
        routes = db.scalars(
            select(Route)
            .where(*conditions)
            .order_by(Route.short_name, Route.route_id)
            .limit(limit)
            .offset(offset)
        ).all()
        return RouteListResponse(
            items=[route_summary(route) for route in routes],
            total=total,
            limit=limit,
            offset=offset,
        )

    @router.get("/routes/{route_id}", response_model=RouteDetail, summary="Route detail")
    def route_detail(route_id: str, db: Session = Depends(get_db)) -> RouteDetail:
        feed_id = _active_feed_id(db)
        route = (
            db.scalar(
                select(Route).where(
                    Route.feed_id == feed_id, Route.route_id == route_id
                )
            )
            if feed_id is not None
            else None
        )
        if route is None:
            raise HTTPException(status_code=404, detail="Route not found")
        stop_ids = _stop_ids_for_route(db, feed_id, route_id)
        count = db.scalar(
            select(func.count()).select_from(stop_ids.subquery())
        ) or 0
        return RouteDetail(
            **route_summary(route).model_dump(),
            agency_id=route.agency_id,
            description=route.description,
            url=route.url,
            stop_count=count,
        )

    @router.get(
        "/routes/{route_id}/stops",
        response_model=StopListResponse,
        summary="Stops served by a route",
    )
    def route_stops(
        route_id: str,
        limit: int = Query(200, ge=1, le=500),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db),
    ) -> StopListResponse:
        feed_id = _active_feed_id(db)
        if feed_id is None:
            raise HTTPException(status_code=404, detail="Route not found")
        stop_ids = _stop_ids_for_route(db, feed_id, route_id)
        total = db.scalar(select(func.count()).select_from(stop_ids.subquery())) or 0
        stops = db.scalars(
            select(Stop)
            .where(Stop.feed_id == feed_id, Stop.stop_id.in_(stop_ids))
            .order_by(Stop.name)
            .limit(limit)
            .offset(offset)
        ).all()
        return StopListResponse(
            items=[stop_summary(stop) for stop in stops],
            total=total,
            limit=limit,
            offset=offset,
        )

    @router.get(
        "/routes/{route_id}/geometry",
        response_model=RouteGeometry,
        summary="Route geometry grouped by shape, never combined across trips",
    )
    def route_geometry(
        route_id: str, db: Session = Depends(get_db)
    ) -> RouteGeometry:
        feed_id = _active_feed_id(db)
        exists = (
            db.scalar(
                select(Route.route_id).where(
                    Route.feed_id == feed_id, Route.route_id == route_id
                )
            )
            if feed_id is not None
            else None
        )
        if exists is None:
            raise HTTPException(status_code=404, detail="Route not found")

        has_points = (
            db.scalar(
                select(func.count())
                .select_from(ShapePoint)
                .where(ShapePoint.feed_id == feed_id)
            )
            or 0
        )
        groups = _shape_groups(db, feed_id, route_id) if has_points else []
        shapes: list[ShapeGeometry] = []

        if groups:
            for shape_id, trip_count, direction_id, headsign in groups:
                stop_ids = _ordered_stop_ids(db, feed_id, route_id, shape_id)
                stops = _summaries_for_stop_ids(db, feed_id, stop_ids)
                points = _shape_points(db, feed_id, shape_id)
                if not points:
                    points = [[stop.lat, stop.lon] for stop in stops]
                heading = (headsign or "").strip()
                base = heading or (
                    f"Direction {direction_id}"
                    if direction_id is not None
                    else "Route pattern"
                )
                shapes.append(
                    ShapeGeometry(
                        shape_id=shape_id,
                        label=f"{base[:80]} · {trip_count} scheduled trips",
                        trip_count=trip_count,
                        direction_id=direction_id,
                        headsign=heading or None,
                        points=points,
                        stops=stops,
                    )
                )
            source = "shapes"
            approximate = False
            note = (
                "Route geometry from GTFS shapes.txt (actual road geometry). "
                "Each shape is drawn separately; directions and branches are not combined."
            )
        else:
            for index, (sequence, trip_count) in enumerate(
                _stop_time_patterns(db, feed_id, route_id), start=1
            ):
                stops = _summaries_for_stop_ids(db, feed_id, list(sequence))
                shapes.append(
                    ShapeGeometry(
                        shape_id=f"stop-times-{index}",
                        label=f"Pattern {index} · {trip_count} trips",
                        trip_count=trip_count,
                        points=[[stop.lat, stop.lon] for stop in stops],
                        stops=stops,
                    )
                )
            source = "stop_times"
            approximate = True
            note = (
                "Approximate route: shapes.txt is unavailable, so lines follow the "
                "scheduled stop order from stop_times. This is not actual road geometry."
            )

        return RouteGeometry(
            route_id=route_id,
            source=source,
            approximate=approximate,
            note=note,
            shape_count=len(shapes),
            shapes=shapes,
        )

    @router.get("/stops", response_model=StopListResponse, summary="List or locate stops")
    def list_stops(
        q: str | None = Query(None, description="Search stop name, code or id"),
        route_id: str | None = Query(
            None, description="Only stops served by this route"
        ),
        lat: float | None = Query(None, ge=-90, le=90),
        lon: float | None = Query(None, ge=-180, le=180),
        radius_m: int | None = Query(None, ge=50, le=50000),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db),
    ) -> StopListResponse:
        geo_fields = (lat, lon, radius_m)
        if any(value is not None for value in geo_fields) and not all(
            value is not None for value in geo_fields
        ):
            raise HTTPException(
                status_code=400, detail="lat, lon and radius_m must be supplied together"
            )
        feed_id = _active_feed_id(db)
        if feed_id is None:
            return StopListResponse(items=[], total=0, limit=limit, offset=offset)
        conditions = [Stop.feed_id == feed_id]
        if route_id:
            served = set(db.scalars(_stop_ids_for_route(db, feed_id, route_id)).all())
            if served:
                parents = db.scalars(
                    select(Stop.parent_station).where(
                        Stop.feed_id == feed_id,
                        Stop.stop_id.in_(served),
                        Stop.parent_station.is_not(None),
                    )
                ).all()
                children = db.scalars(
                    select(Stop.stop_id).where(
                        Stop.feed_id == feed_id,
                        Stop.parent_station.in_(served),
                    )
                ).all()
                served.update(parent for parent in parents if parent)
                served.update(children)
            conditions.append(Stop.stop_id.in_(served))
        if q:
            pattern = f"%{q}%"
            conditions.append(
                or_(
                    Stop.name.ilike(pattern),
                    Stop.code.ilike(pattern),
                    Stop.stop_id.ilike(pattern),
                )
            )
        if lat is not None and lon is not None and radius_m is not None:
            delta_lat = radius_m / 111_320
            cosine = max(math.cos(math.radians(lat)), 0.01)
            delta_lon = radius_m / (111_320 * cosine)
            conditions.extend(
                [
                    Stop.lat.between(lat - delta_lat, lat + delta_lat),
                    Stop.lon.between(lon - delta_lon, lon + delta_lon),
                ]
            )
        total = db.scalar(select(func.count()).select_from(Stop).where(*conditions)) or 0
        stops = db.scalars(
            select(Stop)
            .where(*conditions)
            .order_by(Stop.name)
            .limit(limit)
            .offset(offset)
        ).all()
        return StopListResponse(
            items=[stop_summary(stop) for stop in stops],
            total=total,
            limit=limit,
            offset=offset,
        )

    @router.get("/stops/{stop_id}", response_model=StopDetail, summary="Stop detail")
    def stop_detail(stop_id: str, db: Session = Depends(get_db)) -> StopDetail:
        feed_id = _active_feed_id(db)
        stop = (
            db.scalar(
                select(Stop).where(Stop.feed_id == feed_id, Stop.stop_id == stop_id)
            )
            if feed_id is not None
            else None
        )
        if stop is None:
            raise HTTPException(status_code=404, detail="Stop not found")
        trip_ids = select(StopTime.trip_id).where(
            StopTime.feed_id == feed_id, StopTime.stop_id == stop_id
        )
        route_ids = (
            select(Trip.route_id)
            .where(Trip.feed_id == feed_id, Trip.trip_id.in_(trip_ids))
            .distinct()
        )
        routes = db.scalars(
            select(Route)
            .where(Route.feed_id == feed_id, Route.route_id.in_(route_ids))
            .order_by(Route.short_name)
        ).all()
        return StopDetail(
            **stop_summary(stop).model_dump(),
            description=stop.description,
            zone_id=stop.zone_id,
            parent_station=stop.parent_station,
            wheelchair_boarding=stop.wheelchair_boarding,
            routes=[route_summary(route) for route in routes],
        )

    return router
