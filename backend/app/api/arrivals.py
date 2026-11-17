"""Passenger-facing stop arrivals (ETA) built from static and realtime data.

Scheduled times come from MySQL (GTFS stop_times joined to trips/routes). Realtime
delays come from the in-memory GTFS-Realtime snapshot, matched by trip_id. Only bus
routes are returned.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.time import (
    TIMEZONE_NAME,
    format_service_time,
    service_date_key,
    service_seconds,
    service_seconds_to_timestamp,
    service_weekday_column,
)
from ..db.session import get_db
from ..ingestion.snapshot import SnapshotStore
from ..models import (
    GtfsFeed,
    Route,
    ServiceCalendar,
    ServiceCalendarDate,
    Stop,
    StopTime,
    Trip,
)
from ..schemas.arrivals import ArrivalItem, ArrivalsResponse

BUS_ROUTE_TYPE = 3

CALENDAR_NOTE = (
    "Scheduled times come from GTFS stop_times. Service calendars (calendar.txt / "
    "calendar_dates.txt) are not imported yet, so trips that do not operate today may "
    "appear. Realtime delays are applied when a matching trip update exists."
)

CALENDAR_FILTERED_NOTE = (
    "Scheduled times come from GTFS stop_times, filtered by the service calendar for "
    "today (Pacific/Auckland). Realtime delays are applied when a matching trip update "
    "exists."
)


def current_service_seconds() -> int:
    """Indirection point so tests can freeze Auckland local time."""
    return service_seconds()


def current_service_date_key() -> str:
    """Indirection point so tests can freeze the Auckland service date."""
    return service_date_key()


def current_weekday_column() -> str:
    """Indirection point so tests can freeze the calendar weekday column."""
    return service_weekday_column()


def classify_delay(delay: int | None, threshold: int) -> str:
    if delay is None:
        return "Scheduled"
    if delay <= -threshold:
        return "Early"
    if delay >= threshold:
        return "Delayed"
    return "On time"


def create_arrivals_router(settings: Settings, store: SnapshotStore) -> APIRouter:
    router = APIRouter(prefix=settings.api_v1_prefix, tags=["passenger"])

    @router.get(
        "/stops/{stop_id}/arrivals",
        response_model=ArrivalsResponse,
        summary="Upcoming bus arrivals at a stop",
    )
    def stop_arrivals(
        stop_id: str,
        route_id: str | None = None,
        minutes: int = Query(60, ge=5, le=240),
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db),
    ) -> ArrivalsResponse:
        feed_id = db.scalar(
            select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True)).limit(1)
        )
        stop = (
            db.scalar(
                select(Stop).where(Stop.feed_id == feed_id, Stop.stop_id == stop_id)
            )
            if feed_id is not None
            else None
        )
        if stop is None:
            raise HTTPException(status_code=404, detail="Stop not found")

        # A GTFS station (location_type=1) groups several platforms; the scheduled
        # stop_times rows belong to the child platforms, not to the station itself.
        included_stop_ids = {stop_id}
        children = db.execute(
            select(Stop.stop_id).where(
                Stop.feed_id == feed_id, Stop.parent_station == stop_id
            )
        ).scalars().all()
        included_stop_ids.update(children)
        platform_ids = sorted(included_stop_ids)

        now_seconds = current_service_seconds()
        upper = now_seconds + minutes * 60
        calendar_count = (
            db.scalar(
                select(func.count())
                .select_from(ServiceCalendar)
                .where(ServiceCalendar.feed_id == feed_id)
            )
            or 0
        )
        has_calendars = calendar_count > 0

        statement = (
            select(
                StopTime.trip_id,
                StopTime.arrival_seconds,
                Trip.route_id,
                Trip.headsign,
                Trip.direction_id,
                Route.short_name,
            )
            .join(
                Trip,
                and_(
                    Trip.feed_id == StopTime.feed_id,
                    Trip.trip_id == StopTime.trip_id,
                ),
            )
            .join(
                Route,
                and_(
                    Route.feed_id == Trip.feed_id,
                    Route.route_id == Trip.route_id,
                ),
            )
            .where(
                StopTime.feed_id == feed_id,
                StopTime.stop_id.in_(platform_ids),
                StopTime.arrival_seconds.is_not(None),
                StopTime.arrival_seconds >= now_seconds,
                StopTime.arrival_seconds <= upper,
                Route.route_type == BUS_ROUTE_TYPE,
            )
        )

        date_key = current_service_date_key()
        if has_calendars:
            weekday_column = current_weekday_column()
            removed = exists(
                select(ServiceCalendarDate.feed_id).where(
                    ServiceCalendarDate.feed_id == ServiceCalendar.feed_id,
                    ServiceCalendarDate.service_id == ServiceCalendar.service_id,
                    ServiceCalendarDate.date == date_key,
                    ServiceCalendarDate.exception_type == 2,
                )
            )
            added = exists(
                select(ServiceCalendarDate.feed_id).where(
                    ServiceCalendarDate.feed_id == ServiceCalendar.feed_id,
                    ServiceCalendarDate.service_id == ServiceCalendar.service_id,
                    ServiceCalendarDate.date == date_key,
                    ServiceCalendarDate.exception_type == 1,
                )
            )
            regular_service = and_(
                ServiceCalendar.start_date <= date_key,
                ServiceCalendar.end_date >= date_key,
                getattr(ServiceCalendar, weekday_column) == 1,
                ~removed,
            )
            statement = (
                statement.join(
                    ServiceCalendar,
                    and_(
                        ServiceCalendar.feed_id == Trip.feed_id,
                        ServiceCalendar.service_id == Trip.service_id,
                    ),
                )
                .where(or_(regular_service, added))
                .distinct()
            )

        if route_id:
            statement = statement.where(Trip.route_id == route_id)
        statement = statement.order_by(
            StopTime.arrival_seconds, StopTime.trip_id
        ).limit(limit)
        rows = db.execute(statement).all()

        snapshot = store.snapshot
        updates = (
            {update.trip_id: update for update in snapshot.trip_updates}
            if snapshot is not None
            else {}
        )

        items: list[ArrivalItem] = []
        for trip_id, scheduled, route, headsign, direction, short_name in rows:
            delay: int | None = None
            source = "schedule"
            update = updates.get(trip_id)
            if update is not None:
                delay = update.delay_seconds
                for stop_update in update.stop_updates:
                    if stop_update.stop_id not in platform_ids:
                        continue
                    if stop_update.arrival_delay is not None:
                        delay = stop_update.arrival_delay
                        break
                    if stop_update.arrival_time is not None:
                        scheduled_epoch = service_seconds_to_timestamp(
                            date_key, scheduled
                        )
                        delay = stop_update.arrival_time - scheduled_epoch
                        break
                source = "realtime"
            predicted = scheduled + delay if delay is not None else None
            effective = predicted if predicted is not None else scheduled
            items.append(
                ArrivalItem(
                    trip_id=trip_id,
                    route_id=route,
                    route_short_name=short_name,
                    headsign=headsign,
                    direction_id=direction,
                    scheduled_seconds=scheduled,
                    scheduled_time=format_service_time(scheduled) or "",
                    predicted_seconds=predicted,
                    predicted_time=format_service_time(predicted),
                    delay_seconds=delay,
                    minutes_away=max(0, round((effective - now_seconds) / 60)),
                    status=classify_delay(delay, settings.on_time_threshold_seconds),
                    source=source,
                )
            )

        note = (
            f"{CALENDAR_FILTERED_NOTE} Service date: {date_key}."
            if has_calendars
            else CALENDAR_NOTE
        )
        if len(platform_ids) > 1:
            note += (
                f" Arrivals from {len(platform_ids) - 1} child platform(s) of this "
                "station are included."
            )
        return ArrivalsResponse(
            stop_id=stop_id,
            stop_name=stop.name,
            included_stop_ids=platform_ids,
            route_id=route_id,
            window_minutes=minutes,
            timezone=TIMEZONE_NAME,
            realtime_available=snapshot is not None,
            total=len(items),
            items=items,
            note=note,
        )

    return router
