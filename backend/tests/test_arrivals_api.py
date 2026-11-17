"""Tests for the passenger stop-arrival board."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.arrivals import classify_delay
from app.core.config import Settings
from app.core.time import format_service_time, service_seconds_to_timestamp
from app.db.session import get_db
from app.ingestion.models import RealtimeSnapshot, StopTimeUpdate, TripUpdate
from app.main import create_app
from app.models import (
    GtfsFeed,
    ServiceCalendar,
    ServiceCalendarDate,
    Stop,
    StopTime,
    Trip,
)

FROZEN_SECONDS = 8 * 3600  # 08:00 Auckland local time
FROZEN_DATE_KEY = "20261118"  # Wednesday
FROZEN_WEEKDAY = "wednesday"


def _snapshot(updates: tuple[TripUpdate, ...] = ()) -> RealtimeSnapshot:
    return RealtimeSnapshot(
        feed_timestamp=1794707735.0,
        fetched_at=datetime(2026, 11, 17, 8, 0, 0),
        vehicles=(),
        trip_updates=updates,
        alerts=(),
    )


def _client(
    settings: Settings,
    db_session: Session,
    updates: tuple[TripUpdate, ...] = (),
    *,
    realtime: bool = True,
) -> TestClient:
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db_session
    if realtime:
        app.state.realtime_store.publish(_snapshot(updates))
    return TestClient(app)


@pytest.fixture(autouse=True)
def freeze_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.arrivals.current_service_seconds", lambda: FROZEN_SECONDS
    )
    monkeypatch.setattr(
        "app.api.arrivals.current_service_date_key", lambda: FROZEN_DATE_KEY
    )
    monkeypatch.setattr(
        "app.api.arrivals.current_weekday_column", lambda: FROZEN_WEEKDAY
    )


def test_arrivals_return_only_bus_routes(settings: Settings, loaded_session: Session) -> None:
    body = _client(settings, loaded_session, realtime=False).get(
        "/api/v1/stops/S1/arrivals"
    ).json()

    assert body["stop_id"] == "S1"
    assert body["stop_name"] == "Britomart"
    assert body["total"] == 2
    assert {item["route_short_name"] for item in body["items"]} == {"18"}
    assert body["timezone"] == "Pacific/Auckland"
    assert body["realtime_available"] is False
    assert all(item["source"] == "schedule" for item in body["items"])
    assert all(item["status"] == "Scheduled" for item in body["items"])
    assert "service calendar" in body["note"]
    assert FROZEN_DATE_KEY in body["note"]


def test_arrivals_are_ordered_by_scheduled_time(
    settings: Settings, loaded_session: Session
) -> None:
    body = _client(settings, loaded_session, realtime=False).get(
        "/api/v1/stops/S1/arrivals"
    ).json()

    assert [item["scheduled_seconds"] for item in body["items"]] == [29700, 32400]
    assert [item["scheduled_time"] for item in body["items"]] == ["08:15:00", "09:00:00"]
    assert body["items"][0]["minutes_away"] == 15


def test_non_bus_routes_are_excluded(settings: Settings, loaded_session: Session) -> None:
    body = _client(settings, loaded_session, realtime=False).get(
        "/api/v1/stops/S3/arrivals"
    ).json()

    assert body["total"] == 0  # S3 is served only by the ferry trip


def test_trip_level_realtime_delay_is_applied(
    settings: Settings, loaded_session: Session
) -> None:
    updates = (
        TripUpdate(trip_id="T1", route_id="R1", delay_seconds=120),
    )

    body = _client(settings, loaded_session, updates).get(
        "/api/v1/stops/S1/arrivals"
    ).json()

    first = body["items"][0]
    assert body["realtime_available"] is True
    assert first["source"] == "realtime"
    assert first["delay_seconds"] == 120
    assert first["predicted_seconds"] == 29820
    assert first["predicted_time"] == "08:17:00"
    assert first["status"] == "Delayed"
    assert first["minutes_away"] == 17
    assert body["items"][1]["source"] == "schedule"


def test_stop_level_prediction_overrides_trip_delay(
    settings: Settings, loaded_session: Session
) -> None:
    updates = (
        TripUpdate(
            trip_id="T1",
            route_id="R1",
            delay_seconds=120,
            stop_updates=(
                StopTimeUpdate(stop_id="S1", stop_sequence=2, arrival_delay=180),
            ),
        ),
    )

    body = _client(settings, loaded_session, updates).get(
        "/api/v1/stops/S1/arrivals"
    ).json()

    assert body["items"][0]["delay_seconds"] == 180
    assert body["items"][0]["predicted_seconds"] == 29880


def test_absolute_arrival_time_fallback_creates_a_delay(
    settings: Settings, loaded_session: Session
) -> None:
    scheduled = service_seconds_to_timestamp(FROZEN_DATE_KEY, 29700)
    updates = (
        TripUpdate(
            trip_id="T1",
            route_id="R1",
            delay_seconds=None,
            stop_updates=(
                StopTimeUpdate(
                    stop_id="S1",
                    stop_sequence=2,
                    arrival_time=scheduled + 180,
                ),
            ),
        ),
    )

    body = _client(settings, loaded_session, updates).get(
        "/api/v1/stops/S1/arrivals"
    ).json()

    assert body["items"][0]["delay_seconds"] == 180
    assert body["items"][0]["status"] == "Delayed"
    assert body["items"][0]["source"] == "realtime"


def test_delay_status_thresholds(settings: Settings, loaded_session: Session) -> None:
    updates = (
        TripUpdate(trip_id="T1", route_id="R1", delay_seconds=-120),
        TripUpdate(trip_id="T4", route_id="R1", delay_seconds=30),
    )

    body = _client(settings, loaded_session, updates).get(
        "/api/v1/stops/S1/arrivals"
    ).json()

    assert {item["status"] for item in body["items"]} == {"Early", "On time"}


def test_route_filter_and_window(settings: Settings, loaded_session: Session) -> None:
    client = _client(settings, loaded_session, realtime=False)

    assert client.get("/api/v1/stops/S1/arrivals?route_id=R1").json()["total"] == 2
    assert client.get("/api/v1/stops/S1/arrivals?route_id=NOPE").json()["total"] == 0
    assert client.get("/api/v1/stops/S1/arrivals?minutes=30").json()["total"] == 1
    assert client.get("/api/v1/stops/S1/arrivals?minutes=4").status_code == 422


def test_unknown_stop_returns_404(settings: Settings, loaded_session: Session) -> None:
    assert (
        _client(settings, loaded_session, realtime=False)
        .get("/api/v1/stops/NOPE/arrivals")
        .status_code
        == 404
    )


def test_station_arrivals_include_child_platforms(
    settings: Settings, loaded_session: Session
) -> None:
    feed_id = loaded_session.scalar(
        select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True))
    )
    loaded_session.add_all(
        [
            Stop(
                feed_id=feed_id,
                stop_id="P1",
                name="Parent Station",
                lat=-36.84,
                lon=174.76,
                location_type=1,
            ),
            Stop(
                feed_id=feed_id,
                stop_id="C1",
                name="Platform 1",
                lat=-36.84,
                lon=174.76,
                parent_station="P1",
            ),
            StopTime(
                feed_id=feed_id,
                trip_id="T1",
                stop_sequence=3,
                stop_id="C1",
                arrival_seconds=30600,
                departure_seconds=30600,
            ),
        ]
    )
    loaded_session.commit()

    body = _client(settings, loaded_session, realtime=False).get(
        "/api/v1/stops/P1/arrivals"
    ).json()

    assert body["included_stop_ids"] == ["C1", "P1"]
    assert body["total"] == 1
    assert body["items"][0]["scheduled_time"] == "08:30:00"
    assert "child platform" in body["note"]

    live = _client(
        settings,
        loaded_session,
        (
            TripUpdate(
                trip_id="T1",
                route_id="R1",
                delay_seconds=30,
                stop_updates=(
                    StopTimeUpdate(
                        stop_id="C1", stop_sequence=3, arrival_delay=90
                    ),
                ),
            ),
        ),
    ).get("/api/v1/stops/P1/arrivals").json()
    assert live["items"][0]["delay_seconds"] == 90
    assert live["items"][0]["source"] == "realtime"


def test_non_operating_service_is_excluded(
    settings: Settings, loaded_session: Session
) -> None:
    feed_id = loaded_session.scalar(
        select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True))
    )
    loaded_session.add_all(
        [
            Trip(
                feed_id=feed_id,
                trip_id="W1",
                route_id="R1",
                service_id="WEEKEND",
                headsign="Weekend only",
            ),
            StopTime(
                feed_id=feed_id,
                trip_id="W1",
                stop_sequence=1,
                stop_id="S1",
                arrival_seconds=30600,
            ),
        ]
    )
    loaded_session.commit()

    body = _client(settings, loaded_session, realtime=False).get(
        "/api/v1/stops/S1/arrivals"
    ).json()

    assert body["total"] == 2
    assert "W1" not in {item["trip_id"] for item in body["items"]}


def test_calendar_exception_removes_service(
    settings: Settings, loaded_session: Session
) -> None:
    feed_id = loaded_session.scalar(
        select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True))
    )
    loaded_session.add(
        ServiceCalendarDate(
            feed_id=feed_id,
            service_id="WEEKDAY",
            date=FROZEN_DATE_KEY,
            exception_type=2,
        )
    )
    loaded_session.commit()

    body = _client(settings, loaded_session, realtime=False).get(
        "/api/v1/stops/S1/arrivals"
    ).json()

    assert body["total"] == 0


def test_calendar_exception_adds_service(
    settings: Settings, loaded_session: Session
) -> None:
    feed_id = loaded_session.scalar(
        select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True))
    )
    loaded_session.add_all(
        [
            ServiceCalendar(
                feed_id=feed_id,
                service_id="SUMMER",
                start_date="20261201",
                end_date="20270131",
            ),
            ServiceCalendarDate(
                feed_id=feed_id,
                service_id="SUMMER",
                date=FROZEN_DATE_KEY,
                exception_type=1,
            ),
            Trip(
                feed_id=feed_id,
                trip_id="X1",
                route_id="R1",
                service_id="SUMMER",
                headsign="Summer special",
            ),
            StopTime(
                feed_id=feed_id,
                trip_id="X1",
                stop_sequence=1,
                stop_id="S1",
                arrival_seconds=31500,
            ),
        ]
    )
    loaded_session.commit()

    body = _client(settings, loaded_session, realtime=False).get(
        "/api/v1/stops/S1/arrivals"
    ).json()

    assert {item["trip_id"] for item in body["items"]} >= {"T1", "T4", "X1"}
    assert body["total"] == 3


def test_delay_classifier_and_time_formatting() -> None:
    assert classify_delay(None, 60) == "Scheduled"
    assert classify_delay(-90, 60) == "Early"
    assert classify_delay(0, 60) == "On time"
    assert classify_delay(59, 60) == "On time"
    assert classify_delay(60, 60) == "Delayed"
    assert format_service_time(90600) == "25:10:00"
    assert format_service_time(None) is None
