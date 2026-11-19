"""Official AT report registry and normalized metric tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "official_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_key", sa.String(64), nullable=False, unique=True),
        sa.Column("family", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("reporting_period", sa.String(64), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issue_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "official_route_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("family", sa.String(32), nullable=False),
        sa.Column("metric", sa.String(48), nullable=False),
        sa.Column("mode", sa.String(32)),
        sa.Column("route_no", sa.String(32), nullable=False),
        sa.Column("route_name", sa.String(255)),
        sa.Column("rptp_level", sa.String(64)),
        sa.Column("area", sa.String(64)),
        sa.Column("region", sa.String(64)),
        sa.Column("operator", sa.String(128)),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("value", sa.Numeric(14, 6), nullable=False),
        sa.Column("definition_note", sa.String(255)),
        sa.Column("source_sheet", sa.String(128), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "report_id", "metric", "route_no", "month", "source_sheet", "source_row",
            name="uq_official_route_metric",
        ),
    )
    op.create_index(
        "ix_official_route_metric_lookup",
        "official_route_metrics",
        ["metric", "route_no", "month"],
    )
    op.create_table(
        "official_network_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("family", sa.String(32), nullable=False),
        sa.Column("metric", sa.String(48), nullable=False),
        sa.Column("mode", sa.String(32)),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("value", sa.Numeric(14, 6), nullable=False),
        sa.Column("source_sheet", sa.String(128), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "report_id", "metric", "month", name="uq_official_network_metric",
        ),
    )
    op.create_index(
        "ix_official_network_metric_lookup",
        "official_network_metrics",
        ["metric", "month"],
    )
    op.create_table(
        "official_import_issues",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("source_sheet", sa.String(128)),
        sa.Column("source_row", sa.Integer()),
        sa.Column("message", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("official_import_issues")
    op.drop_index("ix_official_network_metric_lookup", table_name="official_network_metrics")
    op.drop_table("official_network_metrics")
    op.drop_index("ix_official_route_metric_lookup", table_name="official_route_metrics")
    op.drop_table("official_route_metrics")
    op.drop_table("official_reports")
