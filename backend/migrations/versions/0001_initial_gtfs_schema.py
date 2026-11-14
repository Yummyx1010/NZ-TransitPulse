"""Initial GTFS static network schema.

Revision ID: 0001
Revises:
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gtfs_feeds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(512), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("agency_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("route_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stop_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stop_time_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_gtfs_feeds_checksum", "gtfs_feeds", ["checksum"])

    op.create_table(
        "agencies",
        sa.Column("feed_id", sa.Integer(), primary_key=True),
        sa.Column("agency_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(512)),
        sa.Column("timezone", sa.String(64)),
        sa.Column("lang", sa.String(16)),
        sa.Column("phone", sa.String(64)),
    )

    op.create_table(
        "routes",
        sa.Column("feed_id", sa.Integer(), primary_key=True),
        sa.Column("route_id", sa.String(64), primary_key=True),
        sa.Column("agency_id", sa.String(64)),
        sa.Column("short_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("long_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("description", sa.Text()),
        sa.Column("route_type", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("colour", sa.String(6)),
        sa.Column("text_colour", sa.String(6)),
        sa.Column("url", sa.String(512)),
    )
    op.create_index("ix_routes_feed_type", "routes", ["feed_id", "route_type"])

    op.create_table(
        "stops",
        sa.Column("feed_id", sa.Integer(), primary_key=True),
        sa.Column("stop_id", sa.String(64), primary_key=True),
        sa.Column("code", sa.String(32)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("zone_id", sa.String(64)),
        sa.Column("location_type", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parent_station", sa.String(64)),
        sa.Column("wheelchair_boarding", sa.Integer()),
    )
    op.create_index("ix_stops_feed_position", "stops", ["feed_id", "lat", "lon"])

    op.create_table(
        "trips",
        sa.Column("feed_id", sa.Integer(), primary_key=True),
        sa.Column("trip_id", sa.String(128), primary_key=True),
        sa.Column("route_id", sa.String(64), nullable=False),
        sa.Column("service_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("headsign", sa.String(255)),
        sa.Column("direction_id", sa.Integer()),
        sa.Column("block_id", sa.String(64)),
        sa.Column("shape_id", sa.String(64)),
        sa.Column("wheelchair_accessible", sa.Integer()),
    )
    op.create_index("ix_trips_feed_route", "trips", ["feed_id", "route_id"])

    op.create_table(
        "stop_times",
        sa.Column("feed_id", sa.Integer(), primary_key=True),
        sa.Column("trip_id", sa.String(128), primary_key=True),
        sa.Column("stop_sequence", sa.Integer(), primary_key=True),
        sa.Column("stop_id", sa.String(64), nullable=False),
        sa.Column("arrival_time", sa.String(16)),
        sa.Column("departure_time", sa.String(16)),
        sa.Column("arrival_seconds", sa.Integer()),
        sa.Column("departure_seconds", sa.Integer()),
        sa.Column("stop_headsign", sa.String(255)),
        sa.Column("pickup_type", sa.Integer()),
        sa.Column("drop_off_type", sa.Integer()),
        sa.Column("timepoint", sa.Integer()),
    )
    op.create_index("ix_stop_times_feed_stop", "stop_times", ["feed_id", "stop_id"])


def downgrade() -> None:
    op.drop_index("ix_stop_times_feed_stop", table_name="stop_times")
    op.drop_table("stop_times")
    op.drop_index("ix_trips_feed_route", table_name="trips")
    op.drop_table("trips")
    op.drop_index("ix_stops_feed_position", table_name="stops")
    op.drop_table("stops")
    op.drop_index("ix_routes_feed_type", table_name="routes")
    op.drop_table("routes")
    op.drop_table("agencies")
    op.drop_index("ix_gtfs_feeds_checksum", table_name="gtfs_feeds")
    op.drop_table("gtfs_feeds")
