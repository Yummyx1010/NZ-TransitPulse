"""Read-only analytics API for the Phase 5 dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..analytics import service
from ..db.session import get_db

ALLOWED_METRICS = {
    "punctuality",
    "reliability",
    "boardings",
    "boardings_per_service_hour",
}


def _validate_metric(metric: str) -> None:
    if metric not in ALLOWED_METRICS:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")


def _metric_envelope(
    db: Session, metric: str, start_month: str | None, end_month: str | None
) -> dict[str, object]:
    metadata = service.metric_metadata(db).get(metric, {})
    return {
        "unit": metadata.get("unit"),
        "definition": metadata.get("definition"),
        "source_family": metadata.get("source_family"),
        "metric_kind": metadata.get("kind"),
        "higher_is_better": metadata.get("higher_is_better"),
        "source_coverage": {
            "first_month": metadata.get("first_month"),
            "last_month": metadata.get("last_month"),
            "months": metadata.get("months"),
            "sufficiency": metadata.get("sufficiency"),
        },
        "warning": service.definition_warning(metadata, start_month, end_month),
    }


def create_analytics_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

    @router.get("/summary", summary="Official report coverage and data sufficiency")
    def analytics_summary(db: Session = Depends(get_db)) -> dict[str, object]:
        return service.summary(db)

    @router.get("/metrics", summary="Metric definitions, units and source coverage")
    def metrics(db: Session = Depends(get_db)) -> dict[str, object]:
        catalog = service.metric_metadata(db)
        return {"total": len(catalog), "items": catalog}

    @router.get("/routes", summary="Official route numbers mapped to GTFS route ids")
    def routes(
        q: str | None = Query(None, description="Filter by route number"),
        db: Session = Depends(get_db),
    ) -> dict[str, object]:
        items = service.route_catalog(db, q)
        return {"total": len(items), "items": items}

    @router.get("/route-ranking", summary="Rank routes by an official metric")
    def route_ranking(
        metric: str = "punctuality",
        start_month: str | None = None,
        end_month: str | None = None,
        limit: int = Query(12, ge=1, le=50),
        min_months: int = Query(3, ge=1, le=36),
        include_school_routes: bool = False,
        db: Session = Depends(get_db),
    ) -> dict[str, object]:
        _validate_metric(metric)
        items = service.route_ranking(
            db,
            metric,
            start_month,
            end_month,
            limit,
            min_months,
            include_school_routes,
        )
        return {
            "metric": metric,
            "total": len(items),
            "items": items,
            **_metric_envelope(db, metric, start_month, end_month),
        }

    @router.get("/trends", summary="Monthly trend for a route or the bus network")
    def route_trends(
        metric: str = "punctuality",
        route_no: str | None = None,
        start_month: str | None = None,
        end_month: str | None = None,
        include_school_routes: bool = False,
        db: Session = Depends(get_db),
    ) -> dict[str, object]:
        _validate_metric(metric)
        items = service.trends(
            db,
            metric,
            route_no,
            start_month,
            end_month,
            include_school_routes,
        )
        return {
            "metric": metric,
            "route_no": route_no,
            "total": len(items),
            "items": items,
            **_metric_envelope(db, metric, start_month, end_month),
        }

    @router.get("/heatmap", summary="Route-by-month metric matrix")
    def route_heatmap(
        metric: str = "punctuality",
        start_month: str | None = None,
        end_month: str | None = None,
        limit: int = Query(10, ge=1, le=30),
        include_school_routes: bool = False,
        db: Session = Depends(get_db),
    ) -> dict[str, object]:
        _validate_metric(metric)
        months, items = service.heatmap(
            db,
            metric,
            start_month,
            end_month,
            limit,
            include_school_routes,
        )
        return {
            "metric": metric,
            "months": months,
            "total": len(items),
            "items": items,
            **_metric_envelope(db, metric, start_month, end_month),
        }

    @router.get(
        "/patronage-vs-performance",
        summary="Route-level ridership versus punctuality",
    )
    def ridership_vs_performance(
        start_month: str | None = None,
        end_month: str | None = None,
        include_school_routes: bool = False,
        min_boardings: float = Query(0, ge=0),
        limit: int = Query(30, ge=1, le=100),
        db: Session = Depends(get_db),
    ) -> dict[str, object]:
        result = service.patronage_vs_performance(
            db, start_month, end_month, include_school_routes
        )
        points = [
            point
            for point in result["points"]  # type: ignore[union-attr]
            if float(point["boardings"]) >= min_boardings
        ][:limit]
        return {
            "aggregation": result["aggregation"],
            "total": len(points),
            "points": points,
            "correlation": service.correlation(points),
            "unit": "boardings vs %",
            "definition": (
                "One point per route. X is average monthly boardings; Y is average "
                "official punctuality over the selected period."
            ),
            "source_family": "AT bus performance + punctuality reports",
            "warning": service.definition_warning(
                service.metric_metadata(db).get("punctuality", {}),
                start_month,
                end_month,
            ),
        }

    @router.get("/network", summary="Static GTFS network structure metrics")
    def network_summary(db: Session = Depends(get_db)) -> dict[str, object]:
        return service.network_summary(db)

    return router
