"""Tests for official AT XLSX report parsing and import."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.session import get_db
from app.main import create_app
from app.models import OfficialReport, OfficialRouteMetric
from app.reports.loader import load_report
from app.reports.parser import parse_report
from app.reports.registry import ReportSpec


def _bytes(workbook: Workbook) -> bytes:
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _punctuality_workbook() -> bytes:
    workbook = Workbook()
    for title in ("Punctuality", "Reliability"):
        sheet = workbook.active if title == "Punctuality" else workbook.create_sheet()
        sheet.title = title
        sheet.append([None, title])
        sheet.append([None, "Notes before the real header"])
        sheet.append(
            [
                "Mode",
                "Route No",
                "Route Name",
                "RPTP Level of Service",
                "Area",
                datetime(2024, 1, 1),
                datetime(2024, 2, 1),
            ]
        )
        sheet.append(["Bus", "70", "Botany To Britomart", "Frequent", "South", 0.8, 0.9])
        sheet.append(["Train", "ONE", "Onehunga Line", None, None, 0.95, 0.96])
    return _bytes(workbook)


def _patronage_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "AT Web"
    sheet.append(["Source:", "Official report"])
    sheet.append(
        ["Month-Year", "Total", "Bus Total", "Train - (Rapid)", "Ferry"]
    )
    sheet.append([datetime(2005, 7, 1), 100.5, 80.25, 10.25, 10])
    return _bytes(workbook)


def _performance_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Punctuality "
    sheet.append([None, None, "PUNCTUALITY"])
    sheet.append(
        [
            None,
            "Region",
            "Number",
            "Type",
            "Route",
            "Operator",
            "Unit",
            None,
            None,
            "Number",
            datetime(2024, 1, 1),
        ]
    )
    sheet.append(
        [
            None,
            "South",
            "70",
            "Frequent",
            "Botany To Britomart",
            "NZ Bus",
            "1",
            None,
            None,
            "70",
            0.88,
        ]
    )
    return _bytes(workbook)


def test_parse_punctuality_workbook() -> None:
    parsed = parse_report(_punctuality_workbook(), "punctuality")

    assert len(parsed.route_metrics) == 8
    assert {row.metric for row in parsed.route_metrics} == {"punctuality", "reliability"}
    bus = [
        row
        for row in parsed.route_metrics
        if row.mode == "Bus"
        and row.month == "2024-01"
        and row.metric == "punctuality"
    ]
    assert [row.value for row in bus] == [0.8]


def test_parse_patronage_workbook() -> None:
    parsed = parse_report(_patronage_workbook(), "patronage")

    assert {row.metric for row in parsed.network_metrics} == {
        "total_patronage",
        "bus_patronage",
        "train_patronage",
        "ferry_patronage",
    }
    assert all(row.month == "2005-07" for row in parsed.network_metrics)


def test_parse_bus_performance_workbook() -> None:
    parsed = parse_report(_performance_workbook(), "bus_performance")

    assert len(parsed.route_metrics) == 1
    row = parsed.route_metrics[0]
    assert (row.metric, row.route_no, row.month, row.value) == (
        "punctuality",
        "70",
        "2024-01",
        0.88,
    )


def test_loader_is_idempotent_and_force_replaces_rows(
    settings: Settings, db_session, tmp_path
) -> None:
    settings.report_data_dir = str(tmp_path)
    spec = ReportSpec(
        "punctuality_test",
        "punctuality",
        "Test punctuality",
        "https://example.invalid/report.xlsx",
        "report.xlsx",
        "2024-01..2024-02",
    )
    (tmp_path / spec.file_name).write_bytes(_punctuality_workbook())

    first = load_report(db_session, settings, spec)
    second = load_report(db_session, settings, spec)
    forced = load_report(db_session, settings, spec, force=True)

    assert first.status == "loaded"
    assert first.rows == 8
    assert second.status == "unchanged"
    assert forced.status == "loaded"
    assert db_session.scalar(select(func.count()).select_from(OfficialReport)) == 1
    assert db_session.scalar(select(func.count()).select_from(OfficialRouteMetric)) == 8


def test_official_api_reads_imported_metrics(
    settings: Settings, db_session, tmp_path
) -> None:
    settings.report_data_dir = str(tmp_path)
    route_spec = ReportSpec(
        "punctuality_api",
        "punctuality",
        "API punctuality",
        "https://example.invalid/route.xlsx",
        "route.xlsx",
        "2024-01..2024-02",
    )
    (tmp_path / route_spec.file_name).write_bytes(_punctuality_workbook())
    load_report(db_session, settings, route_spec)

    network_spec = ReportSpec(
        "patronage_api",
        "patronage",
        "API patronage",
        "https://example.invalid/network.xlsx",
        "network.xlsx",
        "2005-07",
    )
    (tmp_path / network_spec.file_name).write_bytes(_patronage_workbook())
    load_report(db_session, settings, network_spec)

    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    status = client.get("/api/v1/official/status").json()
    routes = client.get(
        "/api/v1/official/route-metrics?metric=punctuality&route_no=70"
    ).json()
    network = client.get(
        "/api/v1/official/network-metrics?metric=bus_patronage"
    ).json()

    assert status["total"] == 2
    assert routes["total"] == 2
    assert all(row["route_no"] == "70" for row in routes["items"])
    assert network["total"] == 1
    assert network["items"][0]["value"] == 80.25
