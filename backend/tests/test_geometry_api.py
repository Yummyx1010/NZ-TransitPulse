"""Tests for route -> trip -> shape associations, geometry and stop ordering."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.gtfs.loader import load_feed
from app.gtfs.parser import read_archive_bytes
from app.main import create_app
from tests.fixtures import build_fixture_zip


def _geometry(client: TestClient, route_id: str) -> dict:
    response = client.get(f"/api/v1/routes/{route_id}/geometry")
    assert response.status_code == 200, response.text
    return response.json()


def test_geometry_groups_shapes_by_route(loaded_network_client: TestClient) -> None:
    body = _geometry(loaded_network_client, "R1")

    assert body["route_id"] == "R1"
    assert body["source"] == "shapes"
    assert body["approximate"] is False
    assert body["shape_count"] == 2
    assert {shape["shape_id"] for shape in body["shapes"]} == {"SH1", "SH4"}


def test_unrelated_shapes_are_not_combined_into_one_line(
    loaded_network_client: TestClient,
) -> None:
    body = _geometry(loaded_network_client, "R1")

    point_counts = {
        shape["shape_id"]: len(shape["points"]) for shape in body["shapes"]
    }
    assert point_counts == {"SH1": 3, "SH4": 2}
    assert all(shape["trip_count"] == 1 for shape in body["shapes"])


def test_shape_points_follow_gtfs_sequence_order(
    loaded_network_client: TestClient,
) -> None:
    body = _geometry(loaded_network_client, "R1")
    sh1 = next(shape for shape in body["shapes"] if shape["shape_id"] == "SH1")

    assert sh1["points"] == [
        [-36.8443, 174.767],
        [-36.847, 174.763],
        [-36.85, 174.76],
    ]


def test_stops_follow_stop_sequence_not_alphabetical_order(
    loaded_network_client: TestClient,
) -> None:
    body = _geometry(loaded_network_client, "R1")
    order = {
        shape["shape_id"]: [stop["stop_id"] for stop in shape["stops"]]
        for shape in body["shapes"]
    }

    assert order["SH1"] == ["S2", "S1"]
    assert order["SH4"] == ["S1", "S2"]


def test_geometry_does_not_include_other_routes(
    loaded_network_client: TestClient,
) -> None:
    r1 = _geometry(loaded_network_client, "R1")
    r2 = _geometry(loaded_network_client, "R2")
    r3 = _geometry(loaded_network_client, "R3")

    assert {shape["shape_id"] for shape in r1["shapes"]} == {"SH1", "SH4"}
    assert {shape["shape_id"] for shape in r2["shapes"]} == {"SH2"}
    assert {shape["shape_id"] for shape in r3["shapes"]} == {"SH3"}


def test_unknown_route_geometry_returns_404(loaded_network_client: TestClient) -> None:
    assert loaded_network_client.get("/api/v1/routes/NOPE/geometry").status_code == 404


def test_geometry_without_active_feed_returns_404(network_client: TestClient) -> None:
    assert network_client.get("/api/v1/routes/R1/geometry").status_code == 404


def test_fallback_uses_stop_times_when_shapes_are_missing(
    settings: Settings, db_session: Session
) -> None:
    archive = read_archive_bytes(
        build_fixture_zip(omit=("shapes.txt",)), "no-shapes.zip"
    )
    load_feed(db_session, archive)

    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        body = _geometry(client, "R1")

    assert body["source"] == "stop_times"
    assert body["approximate"] is True
    assert "Approximate route" in body["note"]
    assert "not actual road geometry" in body["note"]
    assert body["shape_count"] == 2

    patterns = {
        tuple(stop["stop_id"] for stop in shape["stops"]): shape
        for shape in body["shapes"]
    }
    assert ("S2", "S1") in patterns
    assert ("S1", "S2") in patterns
    assert patterns[("S2", "S1")]["points"][0] == [-36.871, 174.777]
