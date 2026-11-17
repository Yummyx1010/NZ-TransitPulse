"""Tests for decoding AT's aggregated GTFS-Realtime JSON envelope."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.ingestion.decoder import FeedDecodeError, decode_feed
from tests.fixtures import build_realtime_payload


def test_decodes_all_three_entity_types() -> None:
    snapshot = decode_feed(build_realtime_payload(), fetched_at=datetime(2026, 11, 15))

    assert snapshot.feed_timestamp == 1794707735.359
    assert len(snapshot.vehicles) == 2  # the is_deleted entity is skipped
    assert len(snapshot.trip_updates) == 2
    assert len(snapshot.alerts) == 1


def test_vehicle_fields_and_string_bearing() -> None:
    snapshot = decode_feed(build_realtime_payload())

    vehicle = snapshot.vehicles[0]
    assert vehicle.vehicle_id == "BUS1"
    assert vehicle.lat == -36.8443
    assert vehicle.bearing == 286.0
    assert vehicle.route_id == "70-205"
    assert vehicle.timestamp == 1794707698


def test_missing_vehicle_route_is_recovered_from_trip_updates() -> None:
    snapshot = decode_feed(build_realtime_payload())

    vehicle = next(item for item in snapshot.vehicles if item.vehicle_id == "BUS2")
    assert vehicle.route_id == "WEST-201"


def test_stop_time_update_accepts_object_and_array() -> None:
    snapshot = decode_feed(build_realtime_payload())

    first, second = snapshot.trip_updates
    assert len(first.stop_updates) == 1
    assert first.stop_updates[0].arrival_delay == -30
    assert first.delay_seconds == -30
    assert [update.stop_id for update in second.stop_updates] == ["S2", "S1"]


def test_alert_tolerates_null_active_period_end() -> None:
    snapshot = decode_feed(build_realtime_payload())

    alert = snapshot.alerts[0]
    assert alert.header == "Stops skipped: Route 313"
    assert alert.description == "Bus stop moved"
    assert alert.active_periods == ((1795258800, None),)
    assert alert.route_ids == ("70-205",)


def test_invalid_envelope_is_rejected() -> None:
    payload = build_realtime_payload()
    payload["status"] = "ERROR"

    with pytest.raises(FeedDecodeError, match="status is not OK"):
        decode_feed(payload)


def test_missing_response_is_rejected() -> None:
    with pytest.raises(FeedDecodeError, match="response is missing"):
        decode_feed({"status": "OK"})


def test_malformed_entities_are_skipped() -> None:
    payload = build_realtime_payload()
    payload["response"]["entity"].extend(
        [
            {"id": "bad-vehicle", "vehicle": {"position": {"latitude": "nope"}}},
            {"id": "bad-update", "trip_update": {"trip": {}}},
            {"id": "bad-alert", "alert": "not-a-dict"},
        ]
    )

    snapshot = decode_feed(payload)

    assert len(snapshot.vehicles) == 2
    assert len(snapshot.trip_updates) == 2
    assert len(snapshot.alerts) == 1
