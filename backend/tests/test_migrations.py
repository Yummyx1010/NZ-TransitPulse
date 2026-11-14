"""Guard against drift between the ORM models and the Alembic migration."""

from __future__ import annotations

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect

from app.cli.gtfs import alembic_config
from app.core.config import get_settings
from app.db.base import Base
from app.models import gtfs  # noqa: F401  (register tables)


def test_initial_migration_creates_every_model_table(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("TP_DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        command.upgrade(alembic_config(), "head")
    finally:
        get_settings.cache_clear()

    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert set(Base.metadata.tables) <= tables
        assert "alembic_version" in tables

        for name, table in Base.metadata.tables.items():
            columns = {column["name"] for column in inspector.get_columns(name)}
            assert {column.name for column in table.columns} <= columns, name
    finally:
        engine.dispose()


def test_migration_is_reversible(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"sqlite:///{tmp_path / 'reversible.db'}"
    monkeypatch.setenv("TP_DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        config = alembic_config()
        command.upgrade(config, "head")
        command.downgrade(config, "base")
    finally:
        get_settings.cache_clear()

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert not (set(Base.metadata.tables) & tables)
    finally:
        engine.dispose()
