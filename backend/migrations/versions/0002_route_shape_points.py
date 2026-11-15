"""Route shape geometry from GTFS shapes.txt.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gtfs_feeds",
        sa.Column(
            "shape_point_count", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.create_table(
        "shape_points",
        sa.Column("feed_id", sa.Integer(), primary_key=True),
        sa.Column("shape_id", sa.String(64), primary_key=True),
        sa.Column("shape_pt_sequence", sa.Integer(), primary_key=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("dist_traveled", sa.Float()),
    )


def downgrade() -> None:
    op.drop_table("shape_points")
    op.drop_column("gtfs_feeds", "shape_point_count")
