"""Tests for the transactional GTFS loader."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.gtfs.loader import load_feed
from app.gtfs.parser import GtfsValidationError, read_archive_bytes
from app.models import GtfsFeed, Route, ShapePoint, Stop, StopTime, Trip
from tests.fixtures import ROUTES, SHAPES, build_fixture_zip


def test_load_feed_inserts_all_tables(db_session: Session) -> None:
    archive = read_archive_bytes(build_fixture_zip(), "fixture.zip")

    result = load_feed(db_session, archive)

    assert result.status == "loaded"
    assert result.counts == {
        "agencies": 1,
        "routes": 3,
        "stops": 3,
        "trips": 4,
        "stop_times": 6,
        "shape_points": 7,
    }
    assert result.skipped_stops == 1
    assert result.skipped_shapes == 0
    assert db_session.scalar(select(func.count()).select_from(GtfsFeed)) == 1
    assert db_session.get(GtfsFeed, result.feed_id).is_active is True


def test_after_midnight_times_are_kept_as_seconds(db_session: Session) -> None:
    load_feed(db_session, read_archive_bytes(build_fixture_zip(), "fixture.zip"))

    row = db_session.scalar(
        select(StopTime).where(StopTime.trip_id == "T2", StopTime.stop_sequence == 1)
    )
    assert row is not None
    assert row.arrival_time == "25:10:00"
    assert row.arrival_seconds == 90600


def test_reimporting_the_same_bundle_is_a_noop(db_session: Session) -> None:
    archive = read_archive_bytes(build_fixture_zip(), "fixture.zip")
    first = load_feed(db_session, archive)

    second = load_feed(db_session, archive)

    assert second.status == "unchanged"
    assert second.feed_id == first.feed_id
    assert db_session.scalar(select(func.count()).select_from(GtfsFeed)) == 1


def test_new_bundle_replaces_active_rows(db_session: Session) -> None:
    load_feed(db_session, read_archive_bytes(build_fixture_zip(), "v1.zip"))
    changed = ROUTES.replace("New North Road", "New South Road").replace("WEST,", "WX,")
    archive = read_archive_bytes(
        build_fixture_zip(overrides={"routes.txt": changed}), "v2.zip"
    )

    result = load_feed(db_session, archive)

    assert result.status == "loaded"
    assert db_session.scalar(select(func.count()).select_from(GtfsFeed)) == 2
    active = db_session.scalars(
        select(GtfsFeed).where(GtfsFeed.is_active.is_(True))
    ).all()
    assert len(active) == 1
    assert active[0].id == result.feed_id
    assert db_session.scalar(select(func.count()).select_from(Route)) == 3
    assert db_session.scalar(select(func.count()).select_from(Stop)) == 3
    assert db_session.scalar(select(func.count()).select_from(Trip)) == 4
    assert db_session.scalar(select(func.count()).select_from(StopTime)) == 6
    assert db_session.scalar(select(func.count()).select_from(ShapePoint)) == 7


def test_shape_points_keep_their_sequence_and_association(db_session: Session) -> None:
    load_feed(db_session, read_archive_bytes(build_fixture_zip(), "fixture.zip"))

    sh1 = db_session.scalars(
        select(ShapePoint)
        .where(ShapePoint.shape_id == "SH1")
        .order_by(ShapePoint.shape_pt_sequence)
    ).all()
    trips = db_session.scalars(
        select(Trip).where(Trip.shape_id == "SH1")
    ).all()

    assert [point.shape_pt_sequence for point in sh1] == [1, 2, 3]
    assert [point.lat for point in sh1] == [-36.8443, -36.847, -36.85]
    assert [trip.trip_id for trip in trips] == ["T1"]
    assert all(trip.route_id == "R1" for trip in trips)


def test_shape_loader_skips_invalid_and_duplicate_points(db_session: Session) -> None:
    broken = SHAPES + (
        "SH1,-36.8500,174.7600,3,0.6\n"  # duplicate (shape_id, sequence)
        "SH9,999,174.7600,1,0\n"  # invalid latitude
        "SH9,-36.8500,174.7600,x,0\n"  # invalid sequence
    )
    archive = read_archive_bytes(
        build_fixture_zip(overrides={"shapes.txt": broken}), "shapes.zip"
    )

    result = load_feed(db_session, archive)

    assert result.counts["shape_points"] == 7
    assert result.skipped_shapes == 3


def test_bundle_without_shapes_still_loads(db_session: Session) -> None:
    archive = read_archive_bytes(
        build_fixture_zip(omit=("shapes.txt",)), "no-shapes.zip"
    )

    result = load_feed(db_session, archive)

    assert result.status == "loaded"
    assert result.counts["shape_points"] == 0
    assert db_session.scalar(select(func.count()).select_from(ShapePoint)) == 0


def test_invalid_bundle_rolls_back(db_session: Session) -> None:
    invalid = read_archive_bytes(
        build_fixture_zip(omit=("trips.txt",)), "invalid.zip"
    )

    with pytest.raises(GtfsValidationError):
        load_feed(db_session, invalid)

    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(GtfsFeed)) == 0
