"""Tests for the in-memory snapshot store and the background poller."""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.ingestion.client import ATRealtimeClient, CallBudget
from app.ingestion.decoder import decode_feed
from app.ingestion.poller import RealtimePoller
from app.ingestion.snapshot import SnapshotStore
from tests.fixtures import build_realtime_payload


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "_env_file": None,
        "environment": "test",
        "at_api_key": "test-key",
        "at_realtime_url": "https://example.invalid/feed",
        "at_realtime_poll_seconds": 30,
    }
    return Settings(**{**base, **overrides})


def _client(payload, store: SnapshotStore) -> ATRealtimeClient:
    return ATRealtimeClient(
        _settings(),
        budget=CallBudget(100),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload)
        ),
        sleeper=lambda _: None,
    )


def test_health_reports_counts_and_poll_history() -> None:
    store = SnapshotStore()
    assert store.health()["has_data"] is False

    store.publish(decode_feed(build_realtime_payload()))
    health = store.health()

    assert health["has_data"] is True
    assert health["vehicle_count"] == 2
    assert health["trip_update_count"] == 2
    assert health["alert_count"] == 1
    assert health["successful_polls"] == 1
    assert health["last_error"] is None


def test_vehicle_filters_by_route_bbox_and_limit() -> None:
    store = SnapshotStore()
    store.publish(decode_feed(build_realtime_payload()))

    assert len(store.vehicles()) == 2
    assert [v.vehicle_id for v in store.vehicles(route_id="70-205")] == ["BUS1"]
    assert len(store.vehicles(bbox=(-36.85, 174.76, -36.84, 174.77))) == 1
    assert len(store.vehicles(limit=1)) == 1


def test_trip_update_and_alert_filters() -> None:
    store = SnapshotStore()
    store.publish(decode_feed(build_realtime_payload()))

    assert len(store.trip_updates(route_id="WEST-201")) == 1
    assert len(store.alerts(route_id="70-205")) == 1
    assert store.alerts(route_id="NOPE") == []


def test_poller_publishes_a_snapshot_and_records_failures() -> None:
    store = SnapshotStore()
    client = _client(build_realtime_payload(), store)
    poller = RealtimePoller(client, store, 30)
    try:
        snapshot = poller.poll_once()
        assert snapshot is not None
        assert store.health()["vehicle_count"] == 2
        assert poller.is_running is False
    finally:
        client.close()

    broken = ATRealtimeClient(
        _settings(at_api_key=""),
        budget=CallBudget(100),
        sleeper=lambda _: None,
    )
    failing = RealtimePoller(broken, store, 30)
    try:
        assert failing.poll_once() is None
        assert "RealtimeNotConfigured" in str(store.health()["last_error"])
        assert store.health()["failed_polls"] == 1
    finally:
        broken.close()


def test_poller_can_start_and_stop_cleanly() -> None:
    store = SnapshotStore()
    client = _client(build_realtime_payload(), store)
    poller = RealtimePoller(client, store, 3600)
    try:
        poller.start()
        assert poller.is_running is True
        poller.start()  # idempotent
        poller.stop()
        assert poller.is_running is False
    finally:
        poller.stop()
        client.close()
