"""Opt-in integration test against the developer's local MySQL server.

Run only after executing sql/001_create_database.sql and applying migrations:

    set TP_RUN_MYSQL_INTEGRATION=1
    pytest tests/integration -m integration -q
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.db.session import get_engine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TP_RUN_MYSQL_INTEGRATION", "").strip() != "1",
        reason="set TP_RUN_MYSQL_INTEGRATION=1 to run against local MySQL",
    ),
]

EXPECTED_TABLES = {
    "gtfs_feeds",
    "agencies",
    "routes",
    "stops",
    "trips",
    "stop_times",
}


def test_local_mysql_has_the_phase_1_schema() -> None:
    with get_engine().connect() as connection:
        database = connection.execute(text("SELECT DATABASE()")).scalar()
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT TABLE_NAME FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE()"
                )
            )
        }

    assert database == "transitpulse"
    assert EXPECTED_TABLES <= tables
