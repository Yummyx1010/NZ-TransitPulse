"""Download and import AT's published XLSX reports into MySQL."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..models import (
    OfficialImportIssue,
    OfficialNetworkMetric,
    OfficialReport,
    OfficialRouteMetric,
)
from .parser import parse_report
from .registry import ReportSpec


@dataclass(frozen=True)
class ReportLoadResult:
    source_key: str
    status: str
    rows: int = 0
    issues: int = 0
    message: str = ""


def report_path(settings: Settings, spec: ReportSpec) -> Path:
    return Path(settings.report_data_dir) / spec.file_name


def download_report(settings: Settings, spec: ReportSpec) -> Path:
    """Download a report if it is not already cached locally."""
    target = report_path(settings, spec)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return target
    response = httpx.get(spec.url, follow_redirects=True, timeout=120)
    response.raise_for_status()
    target.write_bytes(response.content)
    return target


def load_report(
    session: Session,
    settings: Settings,
    spec: ReportSpec,
    *,
    force: bool = False,
) -> ReportLoadResult:
    """Parse and transactionally replace one official report's normalized rows."""
    path = report_path(settings, spec)
    if not path.exists():
        return ReportLoadResult(spec.source_key, "missing", message=str(path))
    data = path.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()

    existing = session.scalar(
        select(OfficialReport).where(OfficialReport.source_key == spec.source_key)
    )
    if existing and existing.checksum == checksum and not force:
        return ReportLoadResult(
            spec.source_key, "unchanged", existing.row_count, existing.issue_count
        )

    parsed = parse_report(data, spec.family)

    seen_routes: set[tuple[str, str, str, str, int]] = set()
    route_rows = []
    for row in parsed.route_metrics:
        key = (row.metric, row.route_no, row.month, row.source_sheet, row.source_row)
        if key in seen_routes:
            continue
        seen_routes.add(key)
        route_rows.append(row)

    seen_network: set[tuple[str, str, str, int]] = set()
    network_rows = []
    for row in parsed.network_metrics:
        key = (row.metric, row.month, row.source_sheet, row.source_row)
        if key in seen_network:
            continue
        seen_network.add(key)
        network_rows.append(row)

    report = existing or OfficialReport(source_key=spec.source_key)
    if existing is not None:
        session.execute(
            delete(OfficialImportIssue).where(OfficialImportIssue.report_id == report.id)
        )
        session.execute(
            delete(OfficialRouteMetric).where(OfficialRouteMetric.report_id == report.id)
        )
        session.execute(
            delete(OfficialNetworkMetric).where(OfficialNetworkMetric.report_id == report.id)
        )

    report.family = spec.family
    report.title = spec.title
    report.source_url = spec.url
    report.file_name = spec.file_name
    report.checksum = checksum
    report.reporting_period = spec.reporting_period
    report.imported_at = datetime.now(UTC).replace(tzinfo=None)
    report.row_count = len(route_rows) + len(network_rows)
    report.issue_count = len(parsed.issues)
    session.add(report)
    session.flush()

    session.add_all(
        OfficialRouteMetric(
            report_id=report.id,
            family=row.family,
            metric=row.metric,
            mode=row.mode,
            route_no=row.route_no,
            route_name=row.route_name,
            rptp_level=row.rptp_level,
            area=row.area,
            region=row.region,
            operator=row.operator,
            month=row.month,
            value=row.value,
            definition_note=row.definition_note,
            source_sheet=row.source_sheet,
            source_row=row.source_row,
        )
        for row in route_rows
    )
    session.add_all(
        OfficialNetworkMetric(
            report_id=report.id,
            family=row.family,
            metric=row.metric,
            mode=row.mode,
            month=row.month,
            value=row.value,
            source_sheet=row.source_sheet,
            source_row=row.source_row,
        )
        for row in network_rows
    )
    session.add_all(
        OfficialImportIssue(
            report_id=report.id,
            severity=row.severity,
            source_sheet=row.source_sheet,
            source_row=row.source_row,
            message=row.message,
        )
        for row in parsed.issues
    )
    session.commit()
    return ReportLoadResult(
        spec.source_key, "loaded", report.row_count, len(parsed.issues)
    )


def load_reports(
    session: Session,
    settings: Settings,
    specs: list[ReportSpec],
    *,
    download: bool = False,
    force: bool = False,
) -> list[ReportLoadResult]:
    results: list[ReportLoadResult] = []
    for spec in specs:
        if download:
            try:
                download_report(settings, spec)
            except Exception as exc:  # keep other reports importable
                results.append(
                    ReportLoadResult(
                        spec.source_key,
                        "download_failed",
                        message=f"{type(exc).__name__}: {exc}"[:255],
                    )
                )
                continue
        results.append(load_report(session, settings, spec, force=force))
    return results


def report_status(session: Session) -> list[dict[str, object]]:
    reports = session.scalars(
        select(OfficialReport).order_by(OfficialReport.source_key)
    ).all()
    return [
        {
            "source_key": report.source_key,
            "family": report.family,
            "period": report.reporting_period,
            "rows": report.row_count,
            "issues": report.issue_count,
            "checksum": report.checksum[:12],
            "imported_at": report.imported_at.isoformat() + "Z",
        }
        for report in reports
    ]
