"""Service calendars and date exceptions from GTFS calendar files.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gtfs_feeds",
        sa.Column("calendar_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "gtfs_feeds",
        sa.Column(
            "calendar_date_count", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.create_table(
        "service_calendars",
        sa.Column("feed_id", sa.Integer(), primary_key=True),
        sa.Column("service_id", sa.String(64), primary_key=True),
        sa.Column("monday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tuesday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wednesday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thursday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("friday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("saturday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sunday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_date", sa.String(8), nullable=False),
        sa.Column("end_date", sa.String(8), nullable=False),
    )
    op.create_table(
        "service_calendar_dates",
        sa.Column("feed_id", sa.Integer(), primary_key=True),
        sa.Column("service_id", sa.String(64), primary_key=True),
        sa.Column("date", sa.String(8), primary_key=True),
        sa.Column("exception_type", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("service_calendar_dates")
    op.drop_table("service_calendars")
    op.drop_column("gtfs_feeds", "calendar_date_count")
    op.drop_column("gtfs_feeds", "calendar_count")
