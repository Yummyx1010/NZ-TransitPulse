"""Tests for the health and metadata endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": "test",
        "version": "0.1.0",
        "realtime_feed": "not_configured",
    }


def test_health_never_exposes_the_api_key(settings: Settings) -> None:
    configured = settings.model_copy(
        update={
            "at_api_key": "super-secret-subscription-key",
            "at_vehicle_positions_url": "https://example.invalid/vehicles",
            "at_trip_updates_url": "https://example.invalid/trips",
            "at_service_alerts_url": "https://example.invalid/alerts",
        }
    )
    app = create_app(configured)

    with TestClient(app) as client:
        body = client.get("/health").json()

    assert body["realtime_feed"] == "configured"
    assert "super-secret-subscription-key" not in str(body)
    assert "key" not in body


def test_meta_reports_region_timezone_and_attribution(client: TestClient) -> None:
    response = client.get("/api/v1/meta")

    assert response.status_code == 200
    body = response.json()
    assert body["region"] == "Auckland, New Zealand"
    assert body["timezone"] == "Pacific/Auckland"
    assert body["phase"].startswith("0")
    assert "Auckland Transport" in body["attribution"]
    assert "CC BY 4.0" in body["attribution"]
    assert len(body["data_sources"]) == 2


def test_cors_allows_only_the_configured_origin(client: TestClient) -> None:
    allowed = client.get("/health", headers={"Origin": "http://localhost:5173"})
    denied = client.get("/health", headers={"Origin": "https://untrusted.example"})

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


def test_openapi_documentation_is_available(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health" in paths
    assert "/api/v1/meta" in paths


def test_unknown_route_returns_404(client: TestClient) -> None:
    assert client.get("/does-not-exist").status_code == 404
