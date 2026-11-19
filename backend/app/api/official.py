"""Read-only access to normalized official AT report metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models import OfficialNetworkMetric, OfficialRouteMetric
from ..reports.loader import report_status

ROUTE_METRICS = {
    "punctuality",
    "reliability",
    "boardings",
    "boardings_per_service_hour",
}
NETWORK_METRICS = {
    "total_patronage",
    "bus_patronage",
    "busway_patronage",
    "bus_other_patronage",
    "train_patronage",
    "ferry_patronage",
}


def create_official_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/official", tags=["official-reports"])

    @router.get("/status", summary="Imported official report registry")
    def status(db: Session = Depends(get_db)) -> dict[str, object]:
        reports = report_status(db)
        return {"total": len(reports), "items": reports}

    @router.get("/route-metrics", summary="Official route-level monthly metrics")
    def route_metrics(
        metric: str = Query(..., description="punctuality, reliability, boardings, ..."),
        route_no: str | None = Query(None, description="Official route number, e.g. 70"),
        start_month: str | None = Query(None, description="YYYY-MM inclusive"),
        end_month: str | None = Query(None, description="YYYY-MM inclusive"),
        mode: str = "Bus",
        limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db),
    ) -> dict[str, object]:
        if metric not in ROUTE_METRICS:
            return {"items": [], "total": 0, "error": f"Unknown metric: {metric}"}
        statement = (
            select(OfficialRouteMetric)
            .where(
                OfficialRouteMetric.metric == metric,
                OfficialRouteMetric.mode == mode,
            )
            .order_by(
                OfficialRouteMetric.month,
                OfficialRouteMetric.route_no,
                OfficialRouteMetric.id,
            )
        )
        if route_no:
            statement = statement.where(OfficialRouteMetric.route_no == route_no)
        if start_month:
            statement = statement.where(OfficialRouteMetric.month >= start_month)
        if end_month:
            statement = statement.where(OfficialRouteMetric.month <= end_month)
        rows = db.scalars(statement.limit(limit)).all()
        items = [
            {
                "route_no": row.route_no,
                "route_name": row.route_name,
                "month": row.month,
                "value": float(row.value),
                "family": row.family,
                "source_sheet": row.source_sheet,
                "definition_note": row.definition_note,
            }
            for row in rows
        ]
        return {"items": items, "total": len(items)}

    @router.get("/network-metrics", summary="Official network-level monthly metrics")
    def network_metrics(
        metric: str = Query(..., description="e.g. bus_patronage"),
        start_month: str | None = Query(None, description="YYYY-MM inclusive"),
        end_month: str | None = Query(None, description="YYYY-MM inclusive"),
        limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db),
    ) -> dict[str, object]:
        if metric not in NETWORK_METRICS:
            return {"items": [], "total": 0, "error": f"Unknown metric: {metric}"}
        statement = (
            select(OfficialNetworkMetric)
            .where(OfficialNetworkMetric.metric == metric)
            .order_by(OfficialNetworkMetric.month, OfficialNetworkMetric.id)
        )
        if start_month:
            statement = statement.where(OfficialNetworkMetric.month >= start_month)
        if end_month:
            statement = statement.where(OfficialNetworkMetric.month <= end_month)
        rows = db.scalars(statement.limit(limit)).all()
        items = [
            {
                "month": row.month,
                "value": float(row.value),
                "source_sheet": row.source_sheet,
            }
            for row in rows
        ]
        return {"items": items, "total": len(items)}

    return router
