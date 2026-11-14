"""Tests for the command line tools the developer runs by hand."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

from app.cli import gtfs as cli
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_engine
from app.gtfs.loader import LoadResult, result_as_dict
from tests.fixtures import build_fixture_zip


@pytest.fixture
def cli_database(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Point the CLI at a disposable SQLite database."""
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    monkeypatch.setenv("TP_DATABASE_URL", url)
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield tmp_path, url
    get_engine.cache_clear()
    get_settings.cache_clear()


def test_alembic_config_is_anchored_to_the_package() -> None:
    config = cli.alembic_config()

    assert Path(config.get_main_option("script_location")).name == "migrations"
    assert Path(config.get_main_option("script_location")).is_dir()


def test_result_as_dict_is_serialisable() -> None:
    result = LoadResult("loaded", 7, "abc", {"routes": 3})

    assert result_as_dict(result)["feed_id"] == 7
    assert result_as_dict(result)["counts"] == {"routes": 3}


def test_cli_migrate_creates_schema(cli_database, capsys) -> None:
    _, url = cli_database

    cli.main(["migrate"])

    assert "Migrations applied" in capsys.readouterr().out
    engine = create_engine(url)
    try:
        assert "routes" in set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_cli_load_and_status(cli_database, capsys) -> None:
    tmp_path, url = cli_database
    Base.metadata.create_all(create_engine(url))
    zip_path = tmp_path / "feed.zip"
    zip_path.write_bytes(build_fixture_zip())

    cli.main(["load", "--file", str(zip_path)])
    load_output = capsys.readouterr().out
    assert '"status": "loaded"' in load_output
    assert '"routes": 3' in load_output

    cli.main(["load", "--file", str(zip_path)])
    assert '"status": "unchanged"' in capsys.readouterr().out

    cli.main(["status"])
    assert '"routes": 3' in capsys.readouterr().out


def test_cli_status_with_no_feed(cli_database, capsys) -> None:
    _, url = cli_database
    Base.metadata.create_all(create_engine(url))

    cli.main(["status"])

    assert "No active GTFS feed" in capsys.readouterr().out


def test_missing_dependencies_reports_only_absent_modules() -> None:
    assert cli.missing_dependencies(["json"]) == []
    assert cli.missing_dependencies(["definitely_not_a_real_module_xyz"]) == [
        "definitely_not_a_real_module_xyz"
    ]


def test_ensure_dependencies_explains_the_virtual_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "missing_dependencies", lambda: ["pydantic_settings"])

    with pytest.raises(SystemExit) as raised:
        cli.ensure_dependencies()

    message = str(raised.value)
    assert "Missing Python dependencies: pydantic_settings" in message
    assert ".venv\\Scripts\\activate" in message
    assert "conda activate transitpulse" in message


def test_check_db_prints_an_actionable_error(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    def broken_engine():
        raise SQLAlchemyError("(1045, 'Access denied for user')")

    monkeypatch.setattr(cli, "get_engine", broken_engine)

    with pytest.raises(SystemExit) as raised:
        cli.main(["check-db"])

    assert raised.value.code == 1
    stderr = capsys.readouterr().err
    assert "Cannot connect to MySQL" in stderr
    assert "sql/001_create_database.sql" in stderr
