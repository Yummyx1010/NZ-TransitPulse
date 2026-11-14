"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.gtfs.loader import load_feed
from app.gtfs.parser import read_archive_bytes
from app.main import create_app
from tests.fixtures import build_fixture_zip


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


@pytest.fixture
def sqlite_engine(tmp_path) -> Iterator[Engine]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine: Engine) -> Iterator[Session]:
    with Session(sqlite_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def loaded_session(db_session: Session) -> Session:
    archive = read_archive_bytes(build_fixture_zip(), "fixture.zip")
    load_feed(db_session, archive)
    return db_session


@pytest.fixture
def network_client(settings: Settings, db_session: Session) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def loaded_network_client(
    settings: Settings, loaded_session: Session
) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: loaded_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
