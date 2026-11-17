"""Tests for the read-only network API."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.db.session import get_db
from app.main import create_app


def test_status_with_no_loaded_feed(network_client: TestClient) -> None:
    body = network_client.get("/api/v1/network/status").json()

    assert body["has_data"] is False
    assert body["active_feed"] is None
    assert "Auckland Transport" in body["attribution"]


def test_status_with_loaded_feed(loaded_network_client: TestClient) -> None:
    response = loaded_network_client.get("/api/v1/network/status")

    assert response.status_code == 200
    body = response.json()
    assert body["has_data"] is True
    assert body["totals"]["routes"] == 3
    assert body["totals"]["stops"] == 3
    assert body["active_feed"]["checksum"]


def test_list_routes_supports_search_and_mode(loaded_network_client: TestClient) -> None:
    all_routes = loaded_network_client.get("/api/v1/routes").json()
    buses = loaded_network_client.get("/api/v1/routes?mode=Bus").json()
    ferries = loaded_network_client.get("/api/v1/routes?mode=4").json()
    named = loaded_network_client.get("/api/v1/routes?q=Western").json()

    assert all_routes["total"] == 3
    assert [item["short_name"] for item in buses["items"]] == ["18"]
    assert [item["mode"] for item in buses["items"]] == ["Bus"]
    assert [item["short_name"] for item in ferries["items"]] == ["DEV"]
    assert [item["short_name"] for item in named["items"]] == ["WEST"]


def test_unknown_mode_returns_400(loaded_network_client: TestClient) -> None:
    response = loaded_network_client.get("/api/v1/routes?mode=Spaceship")

    assert response.status_code == 400
    assert "Unknown mode" in response.json()["detail"]


def test_pagination_is_applied(loaded_network_client: TestClient) -> None:
    page = loaded_network_client.get("/api/v1/routes?limit=2&offset=1").json()

    assert page["total"] == 3
    assert page["limit"] == 2
    assert page["offset"] == 1
    assert len(page["items"]) == 2


def test_stop_search_can_be_scoped_to_a_route(loaded_network_client: TestClient) -> None:
    buses = loaded_network_client.get("/api/v1/stops?route_id=R1").json()
    ferries = loaded_network_client.get("/api/v1/stops?route_id=R3").json()

    assert {item["stop_id"] for item in buses["items"]} == {"S1", "S2"}
    assert {item["stop_id"] for item in ferries["items"]} == {"S3"}


def test_route_detail_and_stops(loaded_network_client: TestClient) -> None:
    detail = loaded_network_client.get("/api/v1/routes/R1").json()
    stops = loaded_network_client.get("/api/v1/routes/R1/stops").json()

    assert detail["short_name"] == "18"
    assert detail["mode"] == "Bus"
    assert detail["stop_count"] == 2
    assert stops["total"] == 2
    assert {item["stop_id"] for item in stops["items"]} == {"S1", "S2"}


def test_stop_detail_lists_serving_routes(loaded_network_client: TestClient) -> None:
    body = loaded_network_client.get("/api/v1/stops/S2").json()

    assert body["name"] == "Newmarket"
    assert {route["short_name"] for route in body["routes"]} == {"18", "WEST"}


def test_stop_search_and_geo_radius(loaded_network_client: TestClient) -> None:
    by_name = loaded_network_client.get("/api/v1/stops?q=Britomart").json()
    nearby = loaded_network_client.get(
        "/api/v1/stops?lat=-36.8443&lon=174.7670&radius_m=1000"
    ).json()

    assert [item["stop_id"] for item in by_name["items"]] == ["S1"]
    assert [item["stop_id"] for item in nearby["items"]] == ["S1"]


def test_partial_geo_arguments_are_rejected(loaded_network_client: TestClient) -> None:
    response = loaded_network_client.get("/api/v1/stops?lat=-36.8443")

    assert response.status_code == 400
    assert "supplied together" in response.json()["detail"]


def test_unknown_ids_return_404(loaded_network_client: TestClient) -> None:
    assert loaded_network_client.get("/api/v1/routes/NOPE").status_code == 404
    assert loaded_network_client.get("/api/v1/stops/NOPE").status_code == 404


def test_database_failure_returns_503(settings: Settings) -> None:
    def broken_db():
        raise SQLAlchemyError("connection refused")

    app = create_app(settings)
    app.dependency_overrides[get_db] = broken_db

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/routes")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"
