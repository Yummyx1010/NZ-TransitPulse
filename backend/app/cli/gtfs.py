"""CLI for database migrations and GTFS static feed imports.

Run from the `backend/` directory with any Python 3.12 environment that has the
project dependencies installed - a `venv` or a conda environment both work:

    .venv\\Scripts\\activate                 (venv)
    conda create -n transitpulse python=3.12  (once, conda)
    conda activate transitpulse               (conda)
    python -m pip install -e ".[dev]"
    python -m app.cli.gtfs check-db

Or call an interpreter that already has the dependencies directly:

    .venv\\Scripts\\python.exe -m app.cli.gtfs check-db
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Iterable
from pathlib import Path

REQUIRED_MODULES = ("pydantic_settings", "sqlalchemy", "alembic", "pymysql", "httpx")

VENV_HINT = (
    "Dependencies are missing from the current Python interpreter.\n"
    "Activate the environment you created (a venv or a conda env both work):\n"
    "  .venv\\Scripts\\activate           (Windows venv)\n"
    "  conda activate transitpulse       (Anaconda / Miniconda)\n"
    "  python -m pip install -e \".[dev]\"  (run from the backend/ directory)\n"
    "Or call an interpreter that already has the dependencies, e.g.\n"
    "  .venv\\Scripts\\python.exe -m app.cli.gtfs check-db"
)

DATABASE_HINT = (
    "Check TP_DATABASE_URL in .env, confirm the local MySQL service is running,\n"
    "and execute sql/001_create_database.sql in DataGrip (see docs/DATABASE.md)."
)


def missing_dependencies(modules: Iterable[str] = REQUIRED_MODULES) -> list[str]:
    """Return required third-party modules that are not importable right now."""
    return [name for name in modules if importlib.util.find_spec(name) is None]


def ensure_dependencies() -> None:
    """Fail with an actionable message when the system Python is used by mistake."""
    missing = missing_dependencies()
    if missing:
        raise SystemExit(
            "Missing Python dependencies: " + ", ".join(missing) + "\n" + VENV_HINT
        )


ensure_dependencies()

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.util.exc import CommandError  # noqa: E402
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from ..core.config import get_settings  # noqa: E402
from ..db.session import get_engine  # noqa: E402
from ..gtfs.loader import download_gtfs, load_feed, result_as_dict  # noqa: E402
from ..gtfs.parser import read_archive  # noqa: E402
from ..models import GtfsFeed  # noqa: E402


def report_database_error(exc: Exception) -> None:
    """Print a short, actionable message instead of a long SQLAlchemy traceback."""
    cause = getattr(exc, "orig", exc)
    print(f"Cannot connect to MySQL: {cause}", file=sys.stderr)
    print(DATABASE_HINT, file=sys.stderr)
    raise SystemExit(1) from exc


def alembic_config() -> Config:
    """Build an Alembic config anchored to this package, independent of cwd."""
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("prepend_sys_path", str(backend_root))
    return config


def cmd_migrate() -> None:
    try:
        command.upgrade(alembic_config(), "head")
    except (SQLAlchemyError, CommandError) as exc:
        report_database_error(exc)
    print("Migrations applied: head")


def cmd_check_db() -> None:
    try:
        with get_engine().connect() as connection:
            version = connection.execute(text("SELECT VERSION()")).scalar()
            tables = (
                connection.execute(
                    text(
                        "SELECT TABLE_NAME FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME"
                    )
                )
                .scalars()
                .all()
            )
    except SQLAlchemyError as exc:
        report_database_error(exc)
    print(f"Connected to MySQL: {version}")
    print(f"Tables ({len(tables)}): {', '.join(tables) if tables else 'none yet'}")


def cmd_status() -> None:
    try:
        with Session(get_engine()) as session:
            feed = session.scalar(
                select(GtfsFeed).where(GtfsFeed.is_active.is_(True))
            )
    except SQLAlchemyError as exc:
        report_database_error(exc)
    if feed is None:
        print("No active GTFS feed. Run `python -m app.cli.gtfs load --download`.")
        return
    print(
        json.dumps(
            {
                "feed_id": feed.id,
                "source": feed.source,
                "checksum": feed.checksum,
                "imported_at": feed.imported_at.isoformat(),
                "routes": feed.route_count,
                "stops": feed.stop_count,
                "trips": feed.trip_count,
                "stop_times": feed.stop_time_count,
            },
            indent=2,
        )
    )


def cmd_load(args: argparse.Namespace) -> None:
    settings = get_settings()
    if args.download:
        path = download_gtfs(settings.gtfs_static_url, settings.gtfs_data_dir)
        print(f"Downloaded feed to {path}")
    else:
        path = Path(args.file)
    archive = read_archive(path)
    try:
        with Session(get_engine()) as session:
            result = load_feed(session, archive, force=args.force)
    except SQLAlchemyError as exc:
        report_database_error(exc)
    print(json.dumps(result_as_dict(result), indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="gtfs", description="NZ TransitPulse GTFS static feed tools"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="Apply all Alembic migrations")
    sub.add_parser("check-db", help="Verify the MySQL connection")
    sub.add_parser("status", help="Show the active GTFS feed")
    load = sub.add_parser("load", help="Import a GTFS bundle")
    source = load.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", help="Path to a local GTFS zip")
    source.add_argument("--download", action="store_true", help="Download from AT")
    load.add_argument("--force", action="store_true", help="Re-import an unchanged feed")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        cmd_migrate()
    elif args.command == "check-db":
        cmd_check_db()
    elif args.command == "status":
        cmd_status()
    else:
        cmd_load(args)


if __name__ == "__main__":
    main()
