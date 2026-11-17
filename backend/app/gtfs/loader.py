"""Load a GTFS bundle into the database in a single transaction."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

from ..models import (
    Agency,
    GtfsFeed,
    Route,
    ServiceCalendar,
    ServiceCalendarDate,
    ShapePoint,
    Stop,
    StopTime,
    Trip,
)
from .parser import (
    CALENDAR_COLUMNS,
    CALENDAR_DATE_COLUMNS,
    SHAPE_COLUMNS,
    FeedArchive,
    gtfs_time_to_seconds,
    parse_coordinate,
    parse_float,
    parse_gtfs_date,
    parse_int,
    validate_archive,
)

BATCH_SIZE = 5000
CHILD_MODELS = (
    Agency,
    Route,
    Stop,
    StopTime,
    Trip,
    ShapePoint,
    ServiceCalendar,
    ServiceCalendarDate,
)


@dataclass(frozen=True)
class LoadResult:
    """Outcome of a load attempt."""

    status: str
    feed_id: int
    checksum: str
    counts: dict[str, int]
    skipped_stops: int = 0
    skipped_shapes: int = 0
    skipped_calendars: int = 0
    skipped_calendar_dates: int = 0


def _optional(row: dict[str, str], key: str, limit: int) -> str | None:
    value = row.get(key, "").strip()
    return value[:limit] or None


def _agency_rows(archive: FeedArchive, feed_id: int) -> list[dict[str, object]]:
    return [
        {
            "feed_id": feed_id,
            "agency_id": row.get("agency_id") or row.get("agency_name", "unknown"),
            "name": row.get("agency_name") or "Unknown agency",
            "url": _optional(row, "agency_url", 512),
            "timezone": _optional(row, "agency_timezone", 64),
            "lang": _optional(row, "agency_lang", 16),
            "phone": _optional(row, "agency_phone", 64),
        }
        for row in archive.rows("agency.txt")
    ]


def _route_rows(archive: FeedArchive, feed_id: int) -> list[dict[str, object]]:
    return [
        {
            "feed_id": feed_id,
            "route_id": row["route_id"],
            "agency_id": _optional(row, "agency_id", 64),
            "short_name": _optional(row, "route_short_name", 64) or "",
            "long_name": _optional(row, "route_long_name", 255) or "",
            "description": _optional(row, "route_desc", 65535),
            "route_type": parse_int(row.get("route_type"), 3) or 3,
            "colour": (_optional(row, "route_color", 6) or "").lstrip("#") or None,
            "text_colour": (_optional(row, "route_text_color", 6) or "").lstrip("#") or None,
            "url": _optional(row, "route_url", 512),
        }
        for row in archive.rows("routes.txt")
    ]


def _stop_rows(
    archive: FeedArchive, feed_id: int
) -> tuple[list[dict[str, object]], int]:
    rows: list[dict[str, object]] = []
    skipped = 0
    for row in archive.rows("stops.txt"):
        lat = parse_coordinate(row.get("stop_lat"), -90.0, 90.0)
        lon = parse_coordinate(row.get("stop_lon"), -180.0, 180.0)
        if lat is None or lon is None:
            skipped += 1
            continue
        rows.append(
            {
                "feed_id": feed_id,
                "stop_id": row["stop_id"],
                "code": _optional(row, "stop_code", 32),
                "name": _optional(row, "stop_name", 255) or row["stop_id"],
                "description": _optional(row, "stop_desc", 65535),
                "lat": lat,
                "lon": lon,
                "zone_id": _optional(row, "zone_id", 64),
                "location_type": parse_int(row.get("location_type"), 0) or 0,
                "parent_station": _optional(row, "parent_station", 64),
                "wheelchair_boarding": parse_int(row.get("wheelchair_boarding")),
            }
        )
    return rows, skipped


def _trip_rows(archive: FeedArchive, feed_id: int) -> list[dict[str, object]]:
    return [
        {
            "feed_id": feed_id,
            "trip_id": row["trip_id"],
            "route_id": row["route_id"],
            "service_id": _optional(row, "service_id", 64) or "",
            "headsign": _optional(row, "trip_headsign", 255),
            "direction_id": parse_int(row.get("direction_id")),
            "block_id": _optional(row, "block_id", 64),
            "shape_id": _optional(row, "shape_id", 64),
            "wheelchair_accessible": parse_int(row.get("wheelchair_accessible")),
        }
        for row in archive.rows("trips.txt")
    ]


def _stop_time_rows(archive: FeedArchive, feed_id: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()
    for row in archive.rows("stop_times.txt"):
        sequence = parse_int(row.get("stop_sequence"))
        if sequence is None:
            continue
        key = (row["trip_id"], sequence)
        if key in seen:
            continue
        seen.add(key)
        arrival = row.get("arrival_time", "")
        departure = row.get("departure_time", "")
        rows.append(
            {
                "feed_id": feed_id,
                "trip_id": row["trip_id"],
                "stop_sequence": sequence,
                "stop_id": row["stop_id"],
                "arrival_time": arrival[:16] or None,
                "departure_time": departure[:16] or None,
                "arrival_seconds": gtfs_time_to_seconds(arrival),
                "departure_seconds": gtfs_time_to_seconds(departure),
                "stop_headsign": _optional(row, "stop_headsign", 255),
                "pickup_type": parse_int(row.get("pickup_type")),
                "drop_off_type": parse_int(row.get("drop_off_type")),
                "timepoint": parse_int(row.get("timepoint")),
            }
        )
    return rows


def _shape_rows(
    archive: FeedArchive, feed_id: int
) -> tuple[list[dict[str, object]], int]:
    """Parse shapes.txt, keeping only points with a valid id, sequence and position."""
    source_rows = archive.rows("shapes.txt")
    if source_rows and any(column not in source_rows[0] for column in SHAPE_COLUMNS):
        return [], len(source_rows)

    rows: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()
    skipped = 0
    for row in source_rows:
        shape_id = row.get("shape_id", "").strip()
        sequence = parse_int(row.get("shape_pt_sequence"))
        lat = parse_coordinate(row.get("shape_pt_lat"), -90.0, 90.0)
        lon = parse_coordinate(row.get("shape_pt_lon"), -180.0, 180.0)
        if not shape_id or sequence is None or lat is None or lon is None:
            skipped += 1
            continue
        key = (shape_id, sequence)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        rows.append(
            {
                "feed_id": feed_id,
                "shape_id": shape_id[:64],
                "shape_pt_sequence": sequence,
                "lat": lat,
                "lon": lon,
                "dist_traveled": parse_float(row.get("shape_dist_traveled")),
            }
        )
    return rows, skipped


def _calendar_rows(
    archive: FeedArchive, feed_id: int
) -> tuple[list[dict[str, object]], int]:
    source_rows = archive.rows("calendar.txt")
    if source_rows and any(column not in source_rows[0] for column in CALENDAR_COLUMNS):
        return [], len(source_rows)

    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    skipped = 0
    for row in source_rows:
        service_id = row.get("service_id", "").strip()
        start = parse_gtfs_date(row.get("start_date"))
        end = parse_gtfs_date(row.get("end_date"))
        if not service_id or start is None or end is None or service_id in seen:
            skipped += 1
            continue
        seen.add(service_id)
        row_data: dict[str, object] = {
            "feed_id": feed_id,
            "service_id": service_id[:64],
            "start_date": start,
            "end_date": end,
        }
        for day in (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ):
            row_data[day] = parse_int(row.get(day), 0) or 0
        rows.append(row_data)
    return rows, skipped


def _calendar_date_rows(
    archive: FeedArchive, feed_id: int
) -> tuple[list[dict[str, object]], int]:
    source_rows = archive.rows("calendar_dates.txt")
    if source_rows and any(
        column not in source_rows[0] for column in CALENDAR_DATE_COLUMNS
    ):
        return [], len(source_rows)

    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    skipped = 0
    for row in source_rows:
        service_id = row.get("service_id", "").strip()
        date = parse_gtfs_date(row.get("date"))
        exception_type = parse_int(row.get("exception_type"))
        if (
            not service_id
            or date is None
            or exception_type not in (1, 2)
            or (service_id, date) in seen
        ):
            skipped += 1
            continue
        seen.add((service_id, date))
        rows.append(
            {
                "feed_id": feed_id,
                "service_id": service_id[:64],
                "date": date,
                "exception_type": exception_type,
            }
        )
    return rows, skipped


def _insert_batches(
    session: Session, model: type, rows: list[dict[str, object]]
) -> None:
    for start in range(0, len(rows), BATCH_SIZE):
        session.execute(insert(model), rows[start : start + BATCH_SIZE])


def _counts_from_feed(feed: GtfsFeed) -> dict[str, int]:
    return {
        "agencies": feed.agency_count,
        "routes": feed.route_count,
        "stops": feed.stop_count,
        "trips": feed.trip_count,
        "stop_times": feed.stop_time_count,
        "shape_points": feed.shape_point_count,
        "calendars": feed.calendar_count,
        "calendar_dates": feed.calendar_date_count,
    }


def load_feed(session: Session, archive: FeedArchive, *, force: bool = False) -> LoadResult:
    """Stage a feed, activate it atomically, and prune the previous version's rows."""
    validate_archive(archive)
    active = session.scalar(select(GtfsFeed).where(GtfsFeed.is_active.is_(True)))
    if active is not None and active.checksum == archive.checksum and not force:
        return LoadResult("unchanged", active.id, active.checksum, _counts_from_feed(active))

    try:
        feed = GtfsFeed(
            source=archive.source[:512],
            checksum=archive.checksum,
            imported_at=datetime.now(UTC).replace(tzinfo=None),
            is_active=False,
        )
        session.add(feed)
        session.flush()
        feed_id = feed.id

        stop_rows, skipped = _stop_rows(archive, feed_id)
        shape_rows, skipped_shapes = _shape_rows(archive, feed_id)
        calendar_rows, skipped_calendars = _calendar_rows(archive, feed_id)
        calendar_date_rows, skipped_calendar_dates = _calendar_date_rows(
            archive, feed_id
        )
        table_rows: list[tuple[type, list[dict[str, object]]]] = [
            (Agency, _agency_rows(archive, feed_id)),
            (Route, _route_rows(archive, feed_id)),
            (Stop, stop_rows),
            (Trip, _trip_rows(archive, feed_id)),
            (StopTime, _stop_time_rows(archive, feed_id)),
            (ShapePoint, shape_rows),
            (ServiceCalendar, calendar_rows),
            (ServiceCalendarDate, calendar_date_rows),
        ]
        for model, rows in table_rows:
            _insert_batches(session, model, rows)

        feed.agency_count = len(table_rows[0][1])
        feed.route_count = len(table_rows[1][1])
        feed.stop_count = len(stop_rows)
        feed.trip_count = len(table_rows[3][1])
        feed.stop_time_count = len(table_rows[4][1])
        feed.shape_point_count = len(shape_rows)
        feed.calendar_count = len(calendar_rows)
        feed.calendar_date_count = len(calendar_date_rows)

        session.execute(update(GtfsFeed).values(is_active=False))
        feed.is_active = True
        for model in CHILD_MODELS:
            session.execute(delete(model).where(model.feed_id != feed_id))
        session.commit()
    except Exception:
        session.rollback()
        raise

    return LoadResult(
        status="loaded",
        feed_id=feed_id,
        checksum=archive.checksum,
        counts=_counts_from_feed(feed),
        skipped_stops=skipped,
        skipped_shapes=skipped_shapes,
        skipped_calendars=skipped_calendars,
        skipped_calendar_dates=skipped_calendar_dates,
    )


def download_gtfs(url: str, destination: str | Path) -> Path:
    """Download the GTFS bundle and store it under a content-addressed filename."""
    folder = Path(destination)
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "gtfs-download.zip"
    with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_bytes(1 << 20):
                handle.write(chunk)
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()[:12]
    target = folder / f"gtfs-{digest}.zip"
    temporary.replace(target)
    return target


def result_as_dict(result: LoadResult) -> dict[str, object]:
    """Serialisable form used by the CLI."""
    return asdict(result)
