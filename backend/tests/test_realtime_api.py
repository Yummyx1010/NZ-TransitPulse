"""Tests for the read-only realtime API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.ingestion.decoder import decode_feed
from app.main import create_app
from app.models import GtfsFeed, Route, Trip
from tests.fixtures import build_realtime_payload


def _client(
    settings: Settings, db_session: Session, *, publish: bool = True
) -> TestClient:
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db_session
    if publish:
        app.state.realtime_store.publish(decode_feed(build_realtime_payload()))
    return TestClient(app)


def _seed_route(db_session: Session) -> None:
    feed = GtfsFeed(
        source="fixture",
        checksum="fixture-checksum",
        imported_at=datetime.now(UTC).replace(tzinfo=None),
        is_active=True,
    )
    db_session.add(feed)
    db_session.flush()
    db_session.add(
        Route(
            feed_id=feed.id,
            route_id="70-205",
            short_name="70",
            long_name="70",
            route_type=3,
        )
    )
    db_session.add_all(
        [
            Trip(
                feed_id=feed.id,
                trip_id="T1",
                route_id="70-205",
                shape_id="SH1",
                service_id="WEEKDAY",
            ),
            Trip(
                feed_id=feed.id,
                trip_id="T2",
                route_id="WEST-201",
                shape_id="SH2",
                service_id="WEEKDAY",
            ),
        ]
    )
    db_session.commit()


def test_status_reports_health_and_quota(settings: Settings, db_session: Session) -> None:
    configured = settings.model_copy(update={"at_api_key": "test-key"})

    body = _client(configured, db_session).get("/api/v1/realtime/status").json()

    assert body["configured"] is True
    assert body["polling"] is False
    assert body["has_data"] is True
    assert body["vehicle_count"] == 2
    assert body["trip_update_count"] == 2
    assert body["alert_count"] == 1
    assert body["weekly_quota"] == 35000
    assert body["poll_seconds"] == 30
    assert "test-key" not in str(body)
    assert "Auckland Transport" in body["attribution"]


def test_vehicles_join_static_route_labels(
    settings: Settings, db_session: Session
) -> None:
    _seed_route(db_session)

    body = _client(settings, db_session).get("/api/v1/realtime/vehicles").json()

    assert body["total"] == 2
    first = next(item for item in body["items"] if item["vehicle_id"] == "BUS1")
    assert first["route_id"] == "70-205"
    assert first["route_short_name"] == "70"
    assert first["mode"] == "Bus"
    assert first["bearing"] == 286.0


def test_vehicles_filter_by_route_and_bbox(
    settings: Settings, db_session: Session
) -> None:
    client = _client(settings, db_session)

    assert client.get("/api/v1/realtime/vehicles?route_id=70-205").json()["total"] == 1
    assert (
        client.get(
            "/api/v1/realtime/vehicles?bbox=-36.85,174.76,-36.84,174.77"
        ).json()["total"]
        == 1
    )
    assert client.get("/api/v1/realtime/vehicles?bbox=bad").status_code == 400
    assert client.get("/api/v1/realtime/vehicles?bbox=1,2,3").status_code == 400


def test_vehicles_can_be_filtered_to_buses_only(
    settings: Settings, db_session: Session
) -> None:
    _seed_route(db_session)
    client = _client(settings, db_session)

    buses = client.get("/api/v1/realtime/vehicles?mode=Bus").json()
    assert buses["total"] == 1
    assert buses["items"][0]["route_short_name"] == "70"
    assert buses["items"][0]["mode"] == "Bus"
    assert client.get("/api/v1/realtime/vehicles?mode=bus").json()["total"] == 1
    assert client.get("/api/v1/realtime/vehicles?mode=Rail").json()["total"] == 0


def test_vehicles_can_be_filtered_to_the_selected_shape(
    settings: Settings, db_session: Session
) -> None:
    _seed_route(db_session)
    client = _client(settings, db_session)

    outbound = client.get("/api/v1/realtime/vehicles?shape_id=SH1").json()
    inbound = client.get("/api/v1/realtime/vehicles?shape_id=SH2").json()

    assert outbound["total"] == 1
    assert [item["vehicle_id"] for item in outbound["items"]] == ["BUS1"]
    assert inbound["total"] == 1
    assert [item["vehicle_id"] for item in inbound["items"]] == ["BUS2"]
    assert client.get("/api/v1/realtime/vehicles?shape_id=NOPE").json()["total"] == 0

    combined = client.get("/api/v1/realtime/vehicles?mode=Bus&shape_id=SH1").json()
    assert combined["total"] == 1


def test_trip_updates_include_negative_delay_and_stop_updates(
    settings: Settings, db_session: Session
) -> None:
    body = _client(settings, db_session).get("/api/v1/realtime/trip-updates").json()

    assert body["total"] == 2
    first = body["items"][0]
    assert first["delay_seconds"] == -30
    assert len(first["stop_updates"]) == 1
    assert first["stop_updates"][0]["arrival_delay"] == -30
    assert len(body["items"][1]["stop_updates"]) == 2


def test_alerts_tolerate_null_active_periods(
    settings: Settings, db_session: Session
) -> None:
    body = _client(settings, db_session).get("/api/v1/realtime/alerts").json()

    assert body["total"] == 1
    alert = body["items"][0]
    assert alert["header"] == "Stops skipped: Route 313"
    assert alert["active_periods"] == [[1795258800, None]]
    assert alert["route_ids"] == ["70-205"]


def test_alerts_can_be_filtered_to_buses_only(
    settings: Settings, db_session: Session
) -> None:
    _seed_route(db_session)
    client = _client(settings, db_session)

    assert client.get("/api/v1/realtime/alerts?mode=Bus").json()["total"] == 1
    assert client.get("/api/v1/realtime/alerts?mode=Rail").json()["total"] == 0


def test_empty_snapshot_returns_empty_lists(
    settings: Settings, db_session: Session
) -> None:
    client = _client(settings, db_session, publish=False)

    assert client.get("/api/v1/realtime/vehicles").json()["items"] == []
    assert client.get("/api/v1/realtime/alerts").json()["total"] == 0
    assert client.get("/api/v1/realtime/status").json()["has_data"] is False
