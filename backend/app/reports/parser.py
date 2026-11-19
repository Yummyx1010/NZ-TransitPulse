"""Parse AT's published XLSX workbooks into normalized metric rows.

The reports are official published summaries, not machine APIs. Their sheets contain
explanatory rows before the real header, mixed month label formats and occasional
styling columns. Parsers therefore locate headers by content instead of fixed rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

Cell = Any
Row = tuple[Cell, ...]


@dataclass(frozen=True)
class RouteMetricRow:
    family: str
    metric: str
    mode: str | None
    route_no: str
    route_name: str | None
    rptp_level: str | None
    area: str | None
    region: str | None
    operator: str | None
    month: str
    value: float
    definition_note: str | None
    source_sheet: str
    source_row: int


@dataclass(frozen=True)
class NetworkMetricRow:
    family: str
    metric: str
    mode: str | None
    month: str
    value: float
    source_sheet: str
    source_row: int


@dataclass(frozen=True)
class IssueRow:
    severity: str
    source_sheet: str | None
    source_row: int | None
    message: str


@dataclass(frozen=True)
class ParsedReport:
    route_metrics: tuple[RouteMetricRow, ...] = ()
    network_metrics: tuple[NetworkMetricRow, ...] = ()
    issues: tuple[IssueRow, ...] = ()

    @property
    def row_count(self) -> int:
        return len(self.route_metrics) + len(self.network_metrics)


@dataclass
class _Builder:
    family: str
    route_metrics: list[RouteMetricRow] = field(default_factory=list)
    network_metrics: list[NetworkMetricRow] = field(default_factory=list)
    issues: list[IssueRow] = field(default_factory=list)

    def result(self) -> ParsedReport:
        return ParsedReport(
            route_metrics=tuple(self.route_metrics),
            network_metrics=tuple(self.network_metrics),
            issues=tuple(self.issues),
        )


def _text(value: Cell) -> str:
    if value is None:
        return ""
    return str(value).replace("\u00a0", " ").strip()


def _limited(value: Cell, length: int) -> str | None:
    text = _text(value)
    return text[:length] or None


def parse_month(value: Cell) -> str | None:
    """Return ``YYYY-MM`` for the month labels used across AT workbooks."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m")
    if isinstance(value, date):
        return value.strftime("%Y-%m")
    text = _text(value)
    if not text:
        return None
    iso = text[:10]
    try:
        parsed = date.fromisoformat(iso)
        return parsed.strftime("%Y-%m")
    except ValueError:
        pass
    for pattern in ("%b %Y", "%B %Y", "%b-%y", "%B-%y"):
        try:
            return datetime.strptime(text, pattern).strftime("%Y-%m")
        except ValueError:
            continue
    return None


def _number(value: Cell) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _text(value).replace(",", "").replace("%", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return float(text)
    except ValueError:
        return None


def _fraction(value: Cell) -> float | None:
    number = _number(value)
    if number is None:
        return None
    # Most workbooks store ratios; a few store whole percentages.
    return number / 100 if abs(number) > 1.5 else number


def _rows(sheet: Any) -> list[Row]:
    return [tuple(row) for row in sheet.iter_rows(values_only=True)]


def _find_header(rows: list[Row], required: tuple[str, ...]) -> int | None:
    for index, row in enumerate(rows):
        values = {_text(cell).lower() for cell in row}
        if all(word.lower() in values for word in required):
            return index
    return None


def _month_columns(header: Row, start: int = 0) -> list[tuple[int, str]]:
    columns: list[tuple[int, str]] = []
    seen: set[str] = set()
    for index, cell in enumerate(header):
        month = parse_month(cell) if index >= start else None
        if month is None or month in seen:
            continue
        seen.add(month)
        columns.append((index, month))
    return columns


def _parse_punctuality_workbook(workbook: Any, builder: _Builder) -> None:
    metric_by_sheet = {"punctuality": "punctuality", "reliability": "reliability"}
    for sheet in workbook.worksheets:
        key = _text(sheet.title).lower()
        metric = metric_by_sheet.get(key)
        if metric is None:
            continue
        rows = _rows(sheet)
        header_index = _find_header(rows, ("Mode", "Route No"))
        if header_index is None:
            builder.issues.append(
                IssueRow("warning", sheet.title, None, "Header row not found")
            )
            continue
        header = rows[header_index]
        months = _month_columns(header, start=5)
        for row_number, row in enumerate(
            rows[header_index + 1 :], start=header_index + 2
        ):
            mode = _text(row[0]) if len(row) > 0 else ""
            route_no = _text(row[1]) if len(row) > 1 else ""
            if not mode or not route_no:
                continue
            for column, month in months:
                if column >= len(row):
                    continue
                value = _fraction(row[column])
                if value is None:
                    continue
                builder.route_metrics.append(
                    RouteMetricRow(
                        family="punctuality_report",
                        metric=metric,
                        mode=mode,
                        route_no=route_no,
                        route_name=_text(row[2]) if len(row) > 2 else None,
                        rptp_level=_text(row[3]) if len(row) > 3 else None,
                        area=_text(row[4]) if len(row) > 4 else None,
                        region=None,
                        operator=None,
                        month=month,
                        value=value,
                        definition_note=None,
                        source_sheet=sheet.title,
                        source_row=row_number,
                    )
                )


def _metric_for_performance_sheet(title: str) -> str | None:
    normalized = title.lower().strip()
    if normalized.startswith("boardings per service hour"):
        return "boardings_per_service_hour"
    if normalized.startswith("boardings"):
        return "boardings"
    if normalized.startswith("punctuality"):
        return "punctuality"
    if normalized.startswith("reliability"):
        return "reliability"
    return None


def _parse_bus_performance_workbook(workbook: Any, builder: _Builder) -> None:
    for sheet in workbook.worksheets:
        metric = _metric_for_performance_sheet(_text(sheet.title))
        if metric is None:
            continue
        rows = _rows(sheet)
        header_index = _find_header(rows, ("Region", "Number", "Type", "Route"))
        if header_index is None:
            builder.issues.append(
                IssueRow("warning", sheet.title, None, "Header row not found")
            )
            continue
        header = rows[header_index]
        months = _month_columns(header, start=8)
        if not months:
            builder.issues.append(
                IssueRow("warning", sheet.title, header_index + 1, "No month columns found")
            )
            continue
        note = None
        if "to jun-23" in _text(sheet.title).lower():
            note = "Earlier AT definition, effective up to 30 June 2023"
        for row_number, row in enumerate(
            rows[header_index + 1 :], start=header_index + 2
        ):
            route_no = _text(row[9]) if len(row) > 9 else ""
            route_no = route_no or (_text(row[2]) if len(row) > 2 else "")
            if not route_no or route_no.lower() in {
                "entire network",
                "network",
                "total",
                "grand total",
                "region",
                "route no",
            }:
                continue
            route_no = route_no[:32]
            for column, month in months:
                if column >= len(row):
                    continue
                ratio_metric = "punctuality" in metric or "reliability" in metric
                value = _fraction(row[column]) if ratio_metric else _number(row[column])
                if value is None:
                    continue
                builder.route_metrics.append(
                    RouteMetricRow(
                        family="bus_performance_report",
                        metric=metric,
                        mode="Bus",
                        route_no=route_no,
                        route_name=_limited(row[4], 255) if len(row) > 4 else None,
                        rptp_level=_limited(row[3], 64) if len(row) > 3 else None,
                        area=None,
                        region=_limited(row[1], 64) if len(row) > 1 else None,
                        operator=_limited(row[5], 128) if len(row) > 5 else None,
                        month=month,
                        value=value,
                        definition_note=note,
                        source_sheet=sheet.title,
                        source_row=row_number,
                    )
                )


def _parse_hourly_boardings_workbook(workbook: Any, builder: _Builder) -> None:
    for sheet in workbook.worksheets:
        if _text(sheet.title).lower() != "route":
            continue
        rows = _rows(sheet)
        header_index = _find_header(rows, ("Route No", "Route Name"))
        if header_index is None:
            continue
        header = rows[header_index]
        months = _month_columns(header, start=6)
        for row_number, row in enumerate(
            rows[header_index + 1 :], start=header_index + 2
        ):
            route_no = _text(row[0])
            if not route_no:
                continue
            for column, month in months:
                if column >= len(row):
                    continue
                value = _number(row[column])
                if value is None:
                    continue
                builder.route_metrics.append(
                    RouteMetricRow(
                        family="hourly_boardings_report",
                        metric="boardings_per_service_hour",
                        mode="Bus",
                        route_no=route_no,
                        route_name=_text(row[1]) if len(row) > 1 else None,
                        rptp_level=_text(row[2]) if len(row) > 2 else None,
                        area=_text(row[5]) if len(row) > 5 else None,
                        region=None,
                        operator=None,
                        month=month,
                        value=value,
                        definition_note="Weekday boardings per scheduled service hour",
                        source_sheet=sheet.title,
                        source_row=row_number,
                    )
                )


def _parse_patronage_workbook(workbook: Any, builder: _Builder) -> None:
    for sheet in workbook.worksheets:
        rows = _rows(sheet)
        header_index = _find_header(rows, ("Month-Year", "Total"))
        if header_index is None:
            continue
        header = rows[header_index]
        metric_columns = {
            index: ("total_patronage", None)
            for index, cell in enumerate(header)
            if _text(cell).lower() == "total"
        }
        for index, cell in enumerate(header):
            label = _text(cell).lower()
            if label.startswith("bus total"):
                metric_columns[index] = ("bus_patronage", "Bus")
            elif label.startswith("busway"):
                metric_columns[index] = ("busway_patronage", "Bus")
            elif label.startswith("bus -"):
                metric_columns[index] = ("bus_other_patronage", "Bus")
            elif label.startswith("train"):
                metric_columns[index] = ("train_patronage", "Train")
            elif label.startswith("ferry"):
                metric_columns[index] = ("ferry_patronage", "Ferry")
        for row_number, row in enumerate(
            rows[header_index + 1 :], start=header_index + 2
        ):
            month = parse_month(row[0]) if row else None
            if month is None:
                continue
            for column, (metric, mode) in metric_columns.items():
                if column >= len(row):
                    continue
                value = _number(row[column])
                if value is None:
                    continue
                builder.network_metrics.append(
                    NetworkMetricRow(
                        family="monthly_patronage",
                        metric=metric,
                        mode=mode,
                        month=month,
                        value=value,
                        source_sheet=sheet.title,
                        source_row=row_number,
                    )
                )


def parse_report(data: bytes, family: str) -> ParsedReport:
    """Parse workbook bytes for a known report family."""
    builders = {
        "punctuality": _parse_punctuality_workbook,
        "bus_performance": _parse_bus_performance_workbook,
        "hourly_boardings": _parse_hourly_boardings_workbook,
        "patronage": _parse_patronage_workbook,
    }
    parser = builders.get(family)
    if parser is None:
        raise ValueError(f"Unknown report family: {family}")
    workbook = load_workbook(BytesIO(data), read_only=True, data_only=True)
    builder = _Builder(family=family)
    try:
        parser(workbook, builder)
    finally:
        workbook.close()
    return builder.result()
