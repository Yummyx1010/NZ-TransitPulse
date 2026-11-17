"""Auckland local-time helpers for GTFS schedule comparisons.

GTFS times are seconds since midnight on a *service day* and may exceed 24 hours for
services that run past midnight. All user-facing times are rendered in Pacific/Auckland,
including daylight-saving transitions (NZST / NZDT).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TIMEZONE_NAME = "Pacific/Auckland"
AUCKLAND = ZoneInfo(TIMEZONE_NAME)


def auckland_now() -> datetime:
    return datetime.now(AUCKLAND)


def service_seconds(moment: datetime | None = None) -> int:
    """Seconds since midnight, local Auckland time."""
    current = moment or auckland_now()
    return current.hour * 3600 + current.minute * 60 + current.second


def service_date(moment: datetime | None = None) -> date:
    """Auckland local calendar date used to select GTFS service calendars."""
    current = moment or auckland_now()
    return current.date()


def service_date_key(moment: datetime | None = None) -> str:
    """GTFS ``YYYYMMDD`` key for the Auckland service date."""
    return service_date(moment).strftime("%Y%m%d")


WEEKDAY_COLUMNS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def service_weekday_column(moment: datetime | None = None) -> str:
    """Name of the calendar.txt boolean column for the service date."""
    return WEEKDAY_COLUMNS[service_date(moment).weekday()]


def service_seconds_to_timestamp(date_key: str, seconds: int) -> int:
    """Convert a GTFS service-day second offset to a Unix timestamp."""
    service_day = datetime.strptime(date_key, "%Y%m%d").date()
    moment = datetime.combine(service_day, time.min, tzinfo=AUCKLAND)
    moment = (moment + timedelta(seconds=seconds)).astimezone(UTC)
    return int(moment.timestamp())


def format_service_time(seconds: int | None) -> str | None:
    """Render GTFS seconds as HH:MM:SS, preserving values above 24:00:00."""
    if seconds is None:
        return None
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
