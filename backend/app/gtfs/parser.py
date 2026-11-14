"""Read and validate a GTFS static zip bundle.

The parser is deliberately independent of the database: it returns plain dictionaries,
which makes the loader easy to test with a small synthetic feed.
"""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

REQUIRED_FILES = ("agency.txt", "routes.txt", "stops.txt", "trips.txt", "stop_times.txt")

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "agency.txt": ("agency_name",),
    "routes.txt": ("route_id", "route_type"),
    "stops.txt": ("stop_id", "stop_name", "stop_lat", "stop_lon"),
    "trips.txt": ("trip_id", "route_id"),
    "stop_times.txt": ("trip_id", "stop_id", "stop_sequence"),
}


class GtfsValidationError(ValueError):
    """Raised when a bundle cannot be loaded safely."""


@dataclass(frozen=True)
class FeedArchive:
    """A parsed GTFS bundle and its SHA-256 identity."""

    source: str
    checksum: str
    tables: dict[str, list[dict[str, str]]]

    def rows(self, filename: str) -> list[dict[str, str]]:
        return self.tables.get(filename, [])


def _member_named(archive: zipfile.ZipFile, filename: str) -> str | None:
    """Find a member by basename; AT bundles may contain a top-level folder."""
    return next(
        (
            name
            for name in archive.namelist()
            if not name.endswith("/") and Path(name).name == filename
        ),
        None,
    )


def _read_table(archive: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    wrapper = io.TextIOWrapper(
        io.BytesIO(archive.read(member)),
        encoding="utf-8-sig",
        newline="",
    )
    reader = csv.DictReader(wrapper)
    if not reader.fieldnames:
        return []
    headers = [(name or "").strip() for name in reader.fieldnames]
    rows: list[dict[str, str]] = []
    for raw in reader:
        row: dict[str, str] = {}
        for header, value in zip(headers, raw.values(), strict=False):
            if header:
                row[header] = "" if value is None else str(value).strip()
        rows.append(row)
    return rows


def read_archive_bytes(data: bytes, source: str) -> FeedArchive:
    """Parse a GTFS zip held in memory."""
    checksum = hashlib.sha256(data).hexdigest()
    tables: dict[str, list[dict[str, str]]] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for filename in REQUIRED_FILES:
            member = _member_named(archive, filename)
            if member is not None:
                tables[filename] = _read_table(archive, member)
    return FeedArchive(source=source, checksum=checksum, tables=tables)


def read_archive(path: str | Path) -> FeedArchive:
    """Parse a GTFS zip from disk."""
    file_path = Path(path)
    return read_archive_bytes(file_path.read_bytes(), str(file_path))


def validate_archive(archive: FeedArchive) -> None:
    """Ensure required tables and columns are present and non-empty."""
    for filename in REQUIRED_FILES:
        rows = archive.rows(filename)
        if not rows:
            raise GtfsValidationError(f"missing or empty required file: {filename}")
        missing = [column for column in REQUIRED_COLUMNS[filename] if column not in rows[0]]
        if missing:
            raise GtfsValidationError(f"{filename} is missing columns: {', '.join(missing)}")


def gtfs_time_to_seconds(value: str | None) -> int | None:
    """Convert ``HH:MM:SS`` to seconds; GTFS allows hours above 23 (after midnight)."""
    if not value or not value.strip():
        return None
    parts = value.strip().split(":")
    if len(parts) != 3:
        return None
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return None
    if hours < 0 or hours > 71 or not 0 <= minutes <= 59 or not 0 <= seconds <= 59:
        return None
    return hours * 3600 + minutes * 60 + seconds


def parse_int(value: str | None, default: int | None = None) -> int | None:
    """Parse an optional GTFS integer field."""
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def parse_coordinate(value: str | None, lower: float, upper: float) -> float | None:
    """Parse a latitude/longitude and reject values outside the valid range."""
    if value is None or not value.strip():
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if lower <= number <= upper else None
