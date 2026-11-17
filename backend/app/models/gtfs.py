"""GTFS static network schema.

Every table is keyed by ``feed_id`` so a newly imported feed can be staged and
atomically activated. Bulk-loaded reference data deliberately has no database-level
foreign keys between child tables; integrity is enforced by the loader transaction.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class GtfsFeed(Base):
    """One imported GTFS bundle and its activation state."""

    __tablename__ = "gtfs_feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    agency_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    route_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stop_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stop_time_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shape_point_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calendar_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calendar_date_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Agency(Base):
    __tablename__ = "agencies"

    feed_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(512))
    timezone: Mapped[str | None] = mapped_column(String(64))
    lang: Mapped[str | None] = mapped_column(String(16))
    phone: Mapped[str | None] = mapped_column(String(64))


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (Index("ix_routes_feed_type", "feed_id", "route_type"),)

    feed_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agency_id: Mapped[str | None] = mapped_column(String(64))
    short_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    long_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text)
    route_type: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    colour: Mapped[str | None] = mapped_column(String(6))
    text_colour: Mapped[str | None] = mapped_column(String(6))
    url: Mapped[str | None] = mapped_column(String(512))


class Stop(Base):
    __tablename__ = "stops"
    __table_args__ = (Index("ix_stops_feed_position", "feed_id", "lat", "lon"),)

    feed_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str | None] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    zone_id: Mapped[str | None] = mapped_column(String(64))
    location_type: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_station: Mapped[str | None] = mapped_column(String(64))
    wheelchair_boarding: Mapped[int | None] = mapped_column(Integer)


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (Index("ix_trips_feed_route", "feed_id", "route_id"),)

    feed_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    route_id: Mapped[str] = mapped_column(String(64), nullable=False)
    service_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    headsign: Mapped[str | None] = mapped_column(String(255))
    direction_id: Mapped[int | None] = mapped_column(Integer)
    block_id: Mapped[str | None] = mapped_column(String(64))
    shape_id: Mapped[str | None] = mapped_column(String(64))
    wheelchair_accessible: Mapped[int | None] = mapped_column(Integer)


class ServiceCalendar(Base):
    """Weekly service pattern from GTFS calendar.txt."""

    __tablename__ = "service_calendars"

    feed_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    monday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tuesday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wednesday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thursday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    friday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saturday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sunday: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_date: Mapped[str] = mapped_column(String(8), nullable=False)
    end_date: Mapped[str] = mapped_column(String(8), nullable=False)


class ServiceCalendarDate(Base):
    """One date exception from GTFS calendar_dates.txt (1 added, 2 removed)."""

    __tablename__ = "service_calendar_dates"

    feed_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    date: Mapped[str] = mapped_column(String(8), primary_key=True)
    exception_type: Mapped[int] = mapped_column(Integer, nullable=False)


class ShapePoint(Base):
    """One ordered point of a GTFS shape (a drawn route path)."""

    __tablename__ = "shape_points"

    feed_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shape_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    shape_pt_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    dist_traveled: Mapped[float | None] = mapped_column(Float)


class StopTime(Base):
    __tablename__ = "stop_times"
    __table_args__ = (Index("ix_stop_times_feed_stop", "feed_id", "stop_id"),)

    feed_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    arrival_time: Mapped[str | None] = mapped_column(String(16))
    departure_time: Mapped[str | None] = mapped_column(String(16))
    arrival_seconds: Mapped[int | None] = mapped_column(Integer)
    departure_seconds: Mapped[int | None] = mapped_column(Integer)
    stop_headsign: Mapped[str | None] = mapped_column(String(255))
    pickup_type: Mapped[int | None] = mapped_column(Integer)
    drop_off_type: Mapped[int | None] = mapped_column(Integer)
    timepoint: Mapped[int | None] = mapped_column(Integer)
