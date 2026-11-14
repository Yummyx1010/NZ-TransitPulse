"""Tests for the GTFS static parser."""

from __future__ import annotations

import pytest

from app.gtfs.parser import (
    GtfsValidationError,
    gtfs_time_to_seconds,
    parse_coordinate,
    parse_int,
    read_archive_bytes,
    validate_archive,
)
from tests.fixtures import ROUTES, build_fixture_zip


def test_archive_reads_nested_files_and_strips_bom() -> None:
    archive = read_archive_bytes(build_fixture_zip(), "fixture.zip")

    assert len(archive.checksum) == 64
    assert archive.source == "fixture.zip"
    assert archive.rows("agency.txt")[0]["agency_name"] == "Auckland Transport"
    assert "route_id" in archive.rows("routes.txt")[0]
    assert archive.rows("routes.txt")[0]["route_short_name"] == "18"


def test_validate_archive_accepts_a_complete_bundle() -> None:
    archive = read_archive_bytes(build_fixture_zip(), "fixture.zip")

    validate_archive(archive)


def test_validate_archive_rejects_a_missing_file() -> None:
    archive = read_archive_bytes(
        build_fixture_zip(omit=("stop_times.txt",)), "incomplete.zip"
    )

    with pytest.raises(GtfsValidationError, match="stop_times.txt"):
        validate_archive(archive)


def test_validate_archive_rejects_a_missing_column() -> None:
    malformed = "route_id,route_short_name\nR1,18\n"
    archive = read_archive_bytes(
        build_fixture_zip(overrides={"routes.txt": malformed}), "malformed.zip"
    )

    with pytest.raises(GtfsValidationError, match="route_type"):
        validate_archive(archive)


def test_checksum_changes_with_content() -> None:
    first = read_archive_bytes(build_fixture_zip(), "a.zip")
    second = read_archive_bytes(
        build_fixture_zip(overrides={"routes.txt": ROUTES.replace("New North", "New South")}),
        "b.zip",
    )

    assert first.checksum != second.checksum


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("08:00:00", 28800),
        ("25:10:00", 90600),
        ("00:00:00", 0),
        ("", None),
        (None, None),
        ("bad", None),
        ("12:99:00", None),
        ("12:00", None),
    ],
)
def test_gtfs_time_to_seconds(value: str | None, expected: int | None) -> None:
    assert gtfs_time_to_seconds(value) == expected


def test_parse_helpers() -> None:
    assert parse_int("4") == 4
    assert parse_int("nope", 3) == 3
    assert parse_coordinate("-36.8443", -90, 90) == -36.8443
    assert parse_coordinate("999", -90, 90) is None
    assert parse_coordinate("abc", -90, 90) is None
