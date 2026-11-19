"""Normalized rows imported from AT's published XLSX reports."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class OfficialReport(Base):
    """One downloaded official workbook and its import outcome."""

    __tablename__ = "official_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    family: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    reporting_period: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class OfficialRouteMetric(Base):
    """A route-level metric for one reporting month."""

    __tablename__ = "official_route_metrics"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "metric", "route_no", "month", "source_sheet", "source_row",
            name="uq_official_route_metric",
        ),
        Index("ix_official_route_metric_lookup", "metric", "route_no", "month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(Integer, nullable=False)
    family: Mapped[str] = mapped_column(String(32), nullable=False)
    metric: Mapped[str] = mapped_column(String(48), nullable=False)
    mode: Mapped[str | None] = mapped_column(String(32))
    route_no: Mapped[str] = mapped_column(String(32), nullable=False)
    route_name: Mapped[str | None] = mapped_column(String(255))
    rptp_level: Mapped[str | None] = mapped_column(String(64))
    area: Mapped[str | None] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(64))
    operator: Mapped[str | None] = mapped_column(String(128))
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)
    definition_note: Mapped[str | None] = mapped_column(String(255))
    source_sheet: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)


class OfficialNetworkMetric(Base):
    """A network-level metric for one reporting month."""

    __tablename__ = "official_network_metrics"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "metric", "month", name="uq_official_network_metric",
        ),
        Index("ix_official_network_metric_lookup", "metric", "month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(Integer, nullable=False)
    family: Mapped[str] = mapped_column(String(32), nullable=False)
    metric: Mapped[str] = mapped_column(String(48), nullable=False)
    mode: Mapped[str | None] = mapped_column(String(32))
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)


class OfficialImportIssue(Base):
    """A non-fatal data-quality issue found while parsing a report."""

    __tablename__ = "official_import_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    source_sheet: Mapped[str | None] = mapped_column(String(128))
    source_row: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text, nullable=False)
