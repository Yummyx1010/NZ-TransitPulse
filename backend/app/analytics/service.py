"""Pure query/aggregation services for the analytics dashboard.

The service layer owns metric selection, de-duplication and aggregation so the API layer
only validates input and serializes results. All values are derived from tables imported
in Phase 1/4; no external requests are made here.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    GtfsFeed,
    OfficialReport,
    OfficialRouteMetric,
    Route,
    ShapePoint,
    Stop,
    StopTime,
    Trip,
)

PUNCTUALITY_METRICS = {"punctuality", "reliability"}
FAMILY_PRIORITY = {
    "punctuality_report": 0,
    "bus_performance_report": 1,
    "hourly_boardings_report": 2,
}
SCHOOL_PREFIXES = ("S",)

METRIC_CATALOG: dict[str, dict[str, object]] = {
    "punctuality": {
        "label": "Official punctuality",
        "short_label": "Punctuality",
        "unit": "%",
        "definition": (
            "AT punctuality: departs the first stop no earlier than 1 minute and no "
            "later than 5 minutes; arrives at the last stop no later than 5 minutes "
            "after schedule."
        ),
        "source_family": "Monthly punctuality and reliability",
        "kind": "service",
        "higher_is_better": True,
    },
    "reliability": {
        "label": "Official reliability",
        "short_label": "Reliability",
        "unit": "%",
        "definition": (
            "AT reliability: departs the first stop no earlier than 1 minute and no "
            "later than 10 minutes after schedule."
        ),
        "source_family": "Monthly punctuality and reliability",
        "kind": "service",
        "higher_is_better": True,
    },
    "boardings": {
        "label": "Estimated boardings",
        "short_label": "Boardings",
        "unit": "passenger trips",
        "definition": (
            "Monthly boardings estimated from AT fare transactions. Ridership is not "
            "an operational performance measure."
        ),
        "source_family": "AT bus performance reports",
        "kind": "ridership",
        "higher_is_better": True,
    },
    "boardings_per_service_hour": {
        "label": "Boardings per service hour",
        "short_label": "Boardings / hour",
        "unit": "boardings per service hour",
        "definition": (
            "Weekday boardings divided by scheduled weekday service hours. A higher "
            "value indicates stronger use of scheduled supply, not better punctuality."
        ),
        "source_family": "AT hourly bus boardings reports",
        "kind": "ridership",
        "higher_is_better": True,
    },
}


def _float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _is_school_route(route_no: str) -> bool:
    upper = route_no.strip().upper()
    return any(upper.startswith(prefix) for prefix in SCHOOL_PREFIXES) and not upper.isdigit()


def _service_level(month_count: int) -> str:
    if month_count == 0:
        return "none"
    if month_count < 6:
        return "limited"
    if month_count < 18:
        return "moderate"
    return "strong"


def metric_metadata(db: Session) -> dict[str, dict[str, object]]:
    """Static definitions enriched with actual source coverage."""
    coverage = {
        metric: {"first": first, "last": last, "months": months}
        for metric, first, last, months in db.execute(
            select(
                OfficialRouteMetric.metric,
                func.min(OfficialRouteMetric.month),
                func.max(OfficialRouteMetric.month),
                func.count(func.distinct(OfficialRouteMetric.month)),
            )
            .where(OfficialRouteMetric.mode == "Bus")
            .group_by(OfficialRouteMetric.metric)
        ).all()
    }
    result: dict[str, dict[str, object]] = {}
    for metric, definition in METRIC_CATALOG.items():
        source = coverage.get(metric, {"first": None, "last": None, "months": 0})
        result[metric] = {
            **definition,
            "first_month": source["first"],
            "last_month": source["last"],
            "months": source["months"],
            "sufficiency": _service_level(int(source["months"] or 0)),
        }
    return result


def definition_warning(
    metadata: dict[str, object],
    start_month: str | None,
    end_month: str | None,
) -> str | None:
    first = metadata.get("first_month")
    last = metadata.get("last_month")
    if first and start_month and start_month < str(first):
        return (
            f"Selected range starts before the first observed month ({first}). "
            "No values are filled for unavailable months."
        )
    if last and end_month and end_month > str(last):
        return (
            f"Selected range extends beyond the last observed month ({last}). "
            "No values are projected beyond source coverage."
        )
    return None


def route_catalog(db: Session, query: str | None = None) -> list[dict[str, object]]:
    """Map official route numbers to GTFS route ids without changing either source."""
    feed_id = db.scalar(
        select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True)).limit(1)
    )
    static_routes: dict[str, list[dict[str, object]]] = {}
    if feed_id is not None:
        for short_name, route_id, long_name in db.execute(
            select(Route.short_name, Route.route_id, Route.long_name).where(
                Route.feed_id == feed_id,
                Route.route_type == 3,
            )
        ).all():
            key = (short_name or "").strip()
            static_routes.setdefault(key, []).append(
                {"route_id": route_id, "long_name": long_name}
            )

    official_numbers = {
        (row[0] or "").strip()
        for row in db.execute(
            select(OfficialRouteMetric.route_no).where(
                OfficialRouteMetric.mode == "Bus"
            )
        ).all()
        if row[0]
    }
    route_numbers = sorted(set(static_routes) | official_numbers)
    if query:
        needle = query.strip().lower()
        route_numbers = [
            route_no for route_no in route_numbers if needle in route_no.lower()
        ]

    return [
        {
            "route_no": route_no,
            "route_ids": [item["route_id"] for item in static_routes.get(route_no, [])],
            "route_name": next(
                (
                    item["long_name"]
                    for item in static_routes.get(route_no, [])
                    if item["long_name"]
                ),
                None,
            ),
            "matched_in_gtfs": route_no in static_routes,
        }
        for route_no in route_numbers
    ]


def route_intelligence(db: Session, route_no: str) -> dict[str, object]:
    """Evidence-based route summary derived only from imported official reports."""
    clean_route = route_no.strip()
    identity = next(
        (item for item in route_catalog(db, clean_route) if item["route_no"] == clean_route),
        None,
    )
    catalog = metric_metadata(db)
    changes: list[dict[str, object]] = []
    seasonality: dict[str, dict[str, object]] = {}
    warnings: list[str] = []

    for metric in ("punctuality", "reliability", "boardings"):
        rows = _deduplicate(_route_rows(db, metric, None, None, True))
        rows = [row for row in rows if row.route_no.strip() == clean_route]
        if not rows:
            continue
        ordered = sorted(rows, key=lambda row: row.month)
        latest = ordered[-1]
        previous = ordered[-2] if len(ordered) > 1 else None
        window = ordered[-12:]
        latest_value = _float(latest.value)
        previous_value = _float(previous.value) if previous is not None else None
        window_average = (
            round(sum(float(row.value) for row in window) / len(window), 6)
            if window
            else None
        )
        families = sorted({row.family for row in ordered})
        definition_note = next(
            (row.definition_note for row in reversed(ordered) if row.definition_note), None
        )
        if len(families) > 1:
            warnings.append(
                f"{metric} values for this route use more than one AT report family."
            )
        change = (
            None
            if latest_value is None or previous_value is None
            else round(latest_value - previous_value, 6)
        )
        changes.append(
            {
                "metric": metric,
                "label": catalog[metric]["label"],
                "unit": catalog[metric]["unit"],
                "source_family": catalog[metric]["source_family"],
                "definition": catalog[metric]["definition"],
                "definition_note": definition_note,
                "first_month": ordered[0].month,
                "last_month": latest.month,
                "sample_months": len(ordered),
                "sufficiency": _service_level(len(ordered)),
                "latest_value": latest_value,
                "latest_month": latest.month,
                "previous_value": previous_value,
                "previous_month": previous.month if previous is not None else None,
                "change": change,
                "rolling_12m_average": window_average,
                "families": families,
            }
        )
        seasonality[metric] = {
            "months": [row.month for row in ordered],
            "values": [_float(row.value) for row in ordered],
        }

    return {
        "route_no": clean_route,
        "route_name": identity["route_name"] if identity else None,
        "route_ids": identity["route_ids"] if identity else [],
        "matched_in_gtfs": identity["matched_in_gtfs"] if identity else False,
        "has_official_data": bool(changes),
        "changes": changes,
        "seasonality": seasonality,
        "warnings": sorted(set(warnings)),
        "attribution": "Data source: Auckland Transport, licensed under CC BY 4.0",
    }


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        average_rank = (index + 1 + end) / 2
        for position in order[index:end]:
            ranks[position] = average_rank
        index = end
    return ranks


def correlation(points: list[dict[str, object]]) -> dict[str, object]:
    """Spearman correlation with a conservative minimum sample size."""
    if len(points) < 5:
        return {
            "available": False,
            "method": "spearman",
            "sample_size": len(points),
            "reason": "At least five routes are required.",
        }
    xs = [float(point["boardings"]) for point in points]
    ys = [float(point["punctuality"]) for point in points]
    rx, ry = _ranks(xs), _ranks(ys)
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    numerator = sum((x - mx) * (y - my) for x, y in zip(rx, ry, strict=True))
    denominator = (
        sum((x - mx) ** 2 for x in rx) * sum((y - my) ** 2 for y in ry)
    ) ** 0.5
    if denominator == 0:
        return {
            "available": False,
            "method": "spearman",
            "sample_size": len(points),
            "reason": "No variation in the selected values.",
        }
    return {
        "available": True,
        "method": "spearman",
        "coefficient": round(numerator / denominator, 4),
        "sample_size": len(points),
        "reason": None,
    }


def _route_rows(
    db: Session,
    metric: str,
    start_month: str | None,
    end_month: str | None,
    include_school_routes: bool,
) -> list[OfficialRouteMetric]:
    statement = (
        select(OfficialRouteMetric)
        .where(
            OfficialRouteMetric.metric == metric,
            OfficialRouteMetric.mode == "Bus",
        )
        .order_by(
            OfficialRouteMetric.route_no,
            OfficialRouteMetric.month,
            OfficialRouteMetric.family,
        )
    )
    if start_month:
        statement = statement.where(OfficialRouteMetric.month >= start_month)
    if end_month:
        statement = statement.where(OfficialRouteMetric.month <= end_month)
    rows = db.scalars(statement).all()
    if include_school_routes:
        return list(rows)
    return [row for row in rows if not _is_school_route(row.route_no)]


def _deduplicate(
    rows: list[OfficialRouteMetric],
) -> list[OfficialRouteMetric]:
    """Keep one value per route/month, preferring the dedicated report family."""
    best: dict[tuple[str, str], OfficialRouteMetric] = {}
    for row in rows:
        key = (row.route_no.strip(), row.month)
        current = best.get(key)
        if current is None or FAMILY_PRIORITY.get(row.family, 99) < FAMILY_PRIORITY.get(
            current.family, 99
        ):
            best[key] = row
    return sorted(best.values(), key=lambda row: (row.route_no, row.month))


def _as_point(row: OfficialRouteMetric) -> dict[str, object]:
    return {
        "route_no": row.route_no,
        "route_name": row.route_name,
        "month": row.month,
        "value": _float(row.value),
        "family": row.family,
        "definition_note": row.definition_note,
    }


def summary(db: Session) -> dict[str, object]:
    report_count = db.scalar(select(func.count()).select_from(OfficialReport)) or 0
    coverage = db.execute(
        select(
            OfficialRouteMetric.metric,
            func.min(OfficialRouteMetric.month),
            func.max(OfficialRouteMetric.month),
            func.count(func.distinct(OfficialRouteMetric.month)),
        )
        .where(OfficialRouteMetric.mode == "Bus")
        .group_by(OfficialRouteMetric.metric)
    ).all()
    metrics = {
        metric: {
            "first_month": first,
            "last_month": last,
            "months": months,
            "sufficiency": _service_level(months),
        }
        for metric, first, last, months in coverage
    }
    return {
        "report_count": report_count,
        "metrics": metrics,
        "attribution": "Data source: Auckland Transport, licensed under CC BY 4.0",
    }


def route_ranking(
    db: Session,
    metric: str,
    start_month: str | None,
    end_month: str | None,
    limit: int,
    min_months: int,
    include_school_routes: bool,
) -> list[dict[str, object]]:
    rows = _deduplicate(
        _route_rows(db, metric, start_month, end_month, include_school_routes)
    )
    grouped: dict[str, list[OfficialRouteMetric]] = defaultdict(list)
    names: dict[str, str] = {}
    for row in rows:
        route_no = row.route_no.strip()
        grouped[route_no].append(row)
        if row.route_name:
            names[route_no] = row.route_name

    results: list[dict[str, object]] = []
    for route_no, values in grouped.items():
        if len(values) < min_months:
            continue
        ordered = sorted(values, key=lambda row: row.month)
        first = _float(ordered[0].value)
        latest = _float(ordered[-1].value)
        average = round(sum(float(row.value) for row in ordered) / len(ordered), 6)
        results.append(
            {
                "route_no": route_no,
                "route_name": names.get(route_no),
                "sample_months": len(ordered),
                "first_month": ordered[0].month,
                "last_month": ordered[-1].month,
                "first_value": first,
                "latest_value": latest,
                "change": None if first is None or latest is None else latest - first,
                "average_value": average,
            }
        )

    reverse = metric not in PUNCTUALITY_METRICS
    results.sort(
        key=lambda item: (
            item["average_value"] is None,
            item["average_value"],
        ),
        reverse=reverse,
    )
    return results[:limit]


def trends(
    db: Session,
    metric: str,
    route_no: str | None,
    start_month: str | None,
    end_month: str | None,
    include_school_routes: bool,
) -> list[dict[str, object]]:
    rows = _deduplicate(
        _route_rows(db, metric, start_month, end_month, include_school_routes)
    )
    if route_no:
        rows = [row for row in rows if row.route_no.strip() == route_no.strip()]
    by_month: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        value = _float(row.value)
        if value is not None:
            by_month[row.month].append(value)
    return [
        {
            "month": month,
            "value": round(sum(values) / len(values), 6),
            "sample_count": len(values),
        }
        for month, values in sorted(by_month.items())
    ]


def heatmap(
    db: Session,
    metric: str,
    start_month: str | None,
    end_month: str | None,
    limit: int,
    include_school_routes: bool,
) -> tuple[list[str], list[dict[str, object]]]:
    ranking = route_ranking(
        db,
        metric,
        start_month,
        end_month,
        limit=limit,
        min_months=1,
        include_school_routes=include_school_routes,
    )
    route_numbers = [str(item["route_no"]) for item in ranking]
    rows = _deduplicate(
        _route_rows(db, metric, start_month, end_month, include_school_routes)
    )
    values: dict[str, dict[str, float | None]] = {
        route_no: {} for route_no in route_numbers
    }
    months: set[str] = set()
    for row in rows:
        route_no = row.route_no.strip()
        if route_no not in values:
            continue
        month = row.month
        months.add(month)
        values[route_no][month] = _float(row.value)
    ordered_months = sorted(months)
    items = [
        {
            "route_no": route_no,
            "route_name": next(
                (item["route_name"] for item in ranking if item["route_no"] == route_no),
                None,
            ),
            "values": [values[route_no].get(month) for month in ordered_months],
        }
        for route_no in route_numbers
    ]
    return ordered_months, items


def patronage_vs_performance(
    db: Session,
    start_month: str | None,
    end_month: str | None,
    include_school_routes: bool,
) -> dict[str, object]:
    """Aggregate to one point per route to answer a business comparison question."""
    boardings = _deduplicate(
        _route_rows(db, "boardings", start_month, end_month, include_school_routes)
    )
    punctuality = _deduplicate(
        _route_rows(db, "punctuality", start_month, end_month, include_school_routes)
    )
    lookup = {
        (row.route_no.strip(), row.month): row for row in punctuality
    }
    grouped: dict[str, dict[str, object]] = {}
    for boarding in boardings:
        key = (boarding.route_no.strip(), boarding.month)
        performance = lookup.get(key)
        boarding_value = _float(boarding.value)
        punctuality_value = (
            _float(performance.value) if performance is not None else None
        )
        if boarding_value is None or punctuality_value is None:
            continue
        route_no = key[0]
        group = grouped.setdefault(
            route_no,
            {
                "route_name": boarding.route_name,
                "boardings": [],
                "punctuality": [],
                "months": [],
            },
        )
        if not group["route_name"] and boarding.route_name:
            group["route_name"] = boarding.route_name
        group["boardings"].append(boarding_value)  # type: ignore[union-attr]
        group["punctuality"].append(punctuality_value)  # type: ignore[union-attr]
        group["months"].append(key[1])  # type: ignore[union-attr]

    points: list[dict[str, object]] = []
    for route_no, group in grouped.items():
        boarding_values = group["boardings"]  # type: ignore[assignment]
        punctuality_values = group["punctuality"]  # type: ignore[assignment]
        months = group["months"]  # type: ignore[assignment]
        if not boarding_values or not punctuality_values or not months:
            continue
        points.append(
            {
                "route_no": route_no,
                "route_name": group["route_name"],
                "boardings": round(sum(boarding_values) / len(boarding_values), 2),
                "punctuality": round(
                    sum(punctuality_values) / len(punctuality_values), 6
                ),
                "sample_months": len(months),
                "first_month": min(months),
                "last_month": max(months),
            }
        )
    points.sort(key=lambda item: item["boardings"], reverse=True)
    return {
        "aggregation": "route_average",
        "points": points,
        "correlation": correlation(points),
    }


def network_summary(db: Session) -> dict[str, object]:
    feed_id = db.scalar(
        select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True)).limit(1)
    )
    if feed_id is None:
        return {
            "has_data": False,
            "bus_routes": 0,
            "stops": 0,
            "scheduled_trips": 0,
            "shape_points": 0,
        }
    bus_routes = db.scalar(
        select(func.count())
        .select_from(Route)
        .where(Route.feed_id == feed_id, Route.route_type == 3)
    ) or 0
    stops = db.scalar(
        select(func.count()).select_from(Stop).where(Stop.feed_id == feed_id)
    ) or 0
    trips = db.scalar(
        select(func.count()).select_from(Trip).where(Trip.feed_id == feed_id)
    ) or 0
    shape_points = db.scalar(
        select(func.count()).select_from(ShapePoint).where(ShapePoint.feed_id == feed_id)
    ) or 0
    stop_time_rows = db.scalar(
        select(func.count()).select_from(StopTime).where(StopTime.feed_id == feed_id)
    ) or 0
    return {
        "has_data": True,
        "bus_routes": bus_routes,
        "stops": stops,
        "scheduled_trips": trips,
        "shape_points": shape_points,
        "stop_time_rows": stop_time_rows,
        "avg_stop_times_per_trip": (
            round(stop_time_rows / trips, 1) if trips else None
        ),
    }
