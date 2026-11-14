"""Tests for the transactional GTFS loader."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.gtfs.loader import load_feed
from app.gtfs.parser import GtfsValidationError, read_archive_bytes
from app.models import GtfsFeed, Route, Stop, StopTime, Trip
from tests.fixtures import ROUTES, build_fixture_zip


def test_load_feed_inserts_all_tables(db_session: Session) -> None:
    archive = read_archive_bytes(build_fixture_zip(), "fixture.zip")

    result = load_feed(db_session, archive)

    assert result.status == "loaded"
    assert result.counts == {
        "agencies": 1,
        "routes": 3,
        "stops": 3,
        "trips": 3,
        "stop_times": 4,
    }
    assert result.skipped_stops == 1
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
    assert db_session.scalar(select(func.count()).select_from(Trip)) == 3
    assert db_session.scalar(select(func.count()).select_from(StopTime)) == 4


def test_invalid_bundle_rolls_back(db_session: Session) -> None:
    invalid = read_archive_bytes(
        build_fixture_zip(omit=("trips.txt",)), "invalid.zip"
    )

    with pytest.raises(GtfsValidationError):
        load_feed(db_session, invalid)

    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(GtfsFeed)) == 0
