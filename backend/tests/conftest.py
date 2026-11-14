"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    """Deterministic settings: no .env file, no realtime credentials."""
    return Settings(
        _env_file=None,
        environment="test",
        api_v1_prefix="/api/v1",
        cors_origins="http://localhost:5173",
        at_api_key="",
        at_vehicle_positions_url="",
        at_trip_updates_url="",
        at_service_alerts_url="",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
