"""Tests for the Phase 5 analytics API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import service as analytics_service
from app.core.config import Settings
from app.db.session import get_db
from app.main import create_app
from app.models import (
    GtfsFeed,
    OfficialNetworkMetric,
    OfficialReport,
    OfficialRouteMetric,
    Route,
)


def _seed_official(db: Session) -> None:
    punctuality = OfficialReport(
        source_key="test-punctuality",
        family="punctuality",
        title="Punctuality",
        source_url="https://example.invalid/punctuality.xlsx",
        file_name="punctuality.xlsx",
        checksum="a" * 64,
        reporting_period="2024-01..2024-03",
        imported_at=datetime.now(UTC).replace(tzinfo=None),
        row_count=0,
        issue_count=0,
    )
    performance = OfficialReport(
        source_key="test-performance",
        family="bus_performance",
        title="Performance",
        source_url="https://example.invalid/performance.xlsx",
        file_name="performance.xlsx",
        checksum="b" * 64,
        reporting_period="2024-01..2024-03",
        imported_at=datetime.now(UTC).replace(tzinfo=None),
        row_count=0,
        issue_count=0,
    )
    db.add_all([punctuality, performance])
    db.flush()

    db.add_all(
        [
            OfficialRouteMetric(
                report_id=punctuality.id,
                family="punctuality_report",
                metric="punctuality",
                mode="Bus",
                route_no="70",
                route_name="Botany To Britomart",
                month="2024-01",
                value=0.8,
                source_sheet="Punctuality",
                source_row=2,
            ),
            OfficialRouteMetric(
                report_id=punctuality.id,
                family="punctuality_report",
                metric="punctuality",
                mode="Bus",
                route_no="70",
                route_name="Botany To Britomart",
                month="2024-02",
                value=0.9,
                source_sheet="Punctuality",
                source_row=3,
            ),
            OfficialRouteMetric(
                report_id=performance.id,
                family="bus_performance_report",
                metric="punctuality",
                mode="Bus",
                route_no="70",
                route_name="Botany To Britomart",
                month="2024-01",
                value=0.99,
                source_sheet="Punctuality",
                source_row=2,
            ),
            OfficialRouteMetric(
                report_id=punctuality.id,
                family="punctuality_report",
                metric="punctuality",
                mode="Bus",
                route_no="S1",
                route_name="School service",
                month="2024-01",
                value=0.05,
                source_sheet="Punctuality",
                source_row=4,
            ),
            OfficialRouteMetric(
                report_id=punctuality.id,
                family="punctuality_report",
                metric="punctuality",
                mode="Bus",
                route_no="S1",
                route_name="School service",
                month="2024-02",
                value=0.06,
                source_sheet="Punctuality",
                source_row=5,
            ),
            OfficialRouteMetric(
                report_id=performance.id,
                family="bus_performance_report",
                metric="boardings",
                mode="Bus",
                route_no="70",
                route_name="Botany To Britomart",
                month="2024-01",
                value=50000,
                source_sheet="Boardings",
                source_row=2,
            ),
            OfficialRouteMetric(
                report_id=performance.id,
                family="bus_performance_report",
                metric="boardings",
                mode="Bus",
                route_no="70",
                route_name="Botany To Britomart",
                month="2024-02",
                value=60000,
                source_sheet="Boardings",
                source_row=6,
            ),
            OfficialRouteMetric(
                report_id=performance.id,
                family="bus_performance_report",
                metric="boardings",
                mode="Bus",
                route_no="S1",
                route_name="School service",
                month="2024-01",
                value=90000,
                source_sheet="Boardings",
                source_row=3,
            ),
            OfficialNetworkMetric(
                report_id=punctuality.id,
                family="monthly_patronage",
                metric="bus_patronage",
                mode="Bus",
                month="2024-01",
                value=100000,
                source_sheet="AT Web",
                source_row=2,
            ),
        ]
    )
    db.commit()


def _client(settings: Settings, db: Session) -> TestClient:
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_summary_reports_coverage_and_sufficiency(
    settings: Settings, db_session: Session
) -> None:
    _seed_official(db_session)

    body = _client(settings, db_session).get("/api/v1/analytics/summary").json()

    assert body["report_count"] == 2
    assert body["metrics"]["punctuality"]["first_month"] == "2024-01"
    assert body["metrics"]["punctuality"]["sufficiency"] == "limited"


def test_route_ranking_deduplicates_and_excludes_school_routes(
    settings: Settings, db_session: Session
) -> None:
    client = _client(settings, db_session)
    _seed_official(db_session)

    body = client.get(
        "/api/v1/analytics/route-ranking?metric=punctuality&min_months=2"
    ).json()
    assert [item["route_no"] for item in body["items"]] == ["70"]
    assert body["items"][0]["average_value"] == 0.85
    assert round(body["items"][0]["change"], 2) == 0.1

    included = client.get(
        "/api/v1/analytics/route-ranking?metric=punctuality"
        "&min_months=2&include_school_routes=true"
    ).json()
    assert "S1" in {item["route_no"] for item in included["items"]}


def test_trends_heatmap_and_scatter_use_official_rows(
    settings: Settings, db_session: Session
) -> None:
    client = _client(settings, db_session)
    _seed_official(db_session)

    trends = client.get("/api/v1/analytics/trends?metric=punctuality&route_no=70").json()
    assert [point["month"] for point in trends["items"]] == ["2024-01", "2024-02"]
    assert [point["value"] for point in trends["items"]] == [0.8, 0.9]

    heatmap = client.get("/api/v1/analytics/heatmap?metric=punctuality").json()
    assert heatmap["months"] == ["2024-01", "2024-02"]
    assert heatmap["items"][0]["values"] == [0.8, 0.9]

    scatter = client.get("/api/v1/analytics/patronage-vs-performance").json()
    assert scatter["aggregation"] == "route_average"
    assert scatter["points"][0]["route_no"] == "70"
    assert scatter["points"][0]["boardings"] == 55000
    assert scatter["points"][0]["sample_months"] == 2


def test_network_summary_uses_static_gtfs(settings: Settings, loaded_session: Session) -> None:
    body = _client(settings, loaded_session).get("/api/v1/analytics/network").json()

    assert body["has_data"] is True
    assert body["bus_routes"] == 1
    assert body["stops"] == 3
    assert body["scheduled_trips"] > 0
    assert body["shape_points"] > 0


def test_unknown_metric_returns_400(settings: Settings, db_session: Session) -> None:
    response = _client(settings, db_session).get(
        "/api/v1/analytics/route-ranking?metric=spaceship"
    )
    assert response.status_code == 400


def test_metric_metadata_includes_units_and_source_coverage(
    settings: Settings, db_session: Session
) -> None:
    _seed_official(db_session)
    body = _client(settings, db_session).get("/api/v1/analytics/metrics").json()

    assert body["items"]["punctuality"]["unit"] == "%"
    assert body["items"]["boardings"]["unit"] == "passenger trips"
    assert body["items"]["punctuality"]["first_month"] == "2024-01"
    assert body["items"]["punctuality"]["sufficiency"] == "limited"


def test_route_catalog_matches_official_number_to_gtfs_route(
    settings: Settings, loaded_session: Session
) -> None:
    body = _client(settings, loaded_session).get(
        "/api/v1/analytics/routes?q=18"
    ).json()

    route = next(item for item in body["items"] if item["route_no"] == "18")
    assert route["route_ids"] == ["R1"]
    assert route["matched_in_gtfs"] is True


def test_route_intelligence_uses_official_rows_and_gtfs_mapping(
    settings: Settings, loaded_session: Session
) -> None:
    _seed_official(loaded_session)
    feed_id = loaded_session.execute(
        select(GtfsFeed.id).where(GtfsFeed.is_active.is_(True))
    ).scalar_one()
    loaded_session.add(
        Route(
            feed_id=feed_id,
            route_id="70-205",
            short_name="70",
            long_name="Botany To Britomart",
            route_type=3,
        )
    )
    loaded_session.commit()
    body = _client(settings, loaded_session).get(
        "/api/v1/analytics/routes/70/intelligence"
    ).json()

    assert body["route_no"] == "70"
    assert body["matched_in_gtfs"] is True
    assert "70-205" in body["route_ids"]
    assert body["has_official_data"] is True
    changes = {item["metric"]: item for item in body["changes"]}
    assert changes["punctuality"]["latest_value"] == 0.9
    assert changes["punctuality"]["previous_value"] == 0.8
    assert changes["boardings"]["rolling_12m_average"] == 55000
    assert body["seasonality"]["punctuality"]["months"] == ["2024-01", "2024-02"]


def test_correlation_is_hidden_for_small_samples() -> None:
    points = [
        {"boardings": 100, "punctuality": 0.8},
        {"boardings": 200, "punctuality": 0.9},
    ]
    result = analytics_service.correlation(points)

    assert result["available"] is False
    assert result["sample_size"] == 2
    assert result["method"] == "spearman"
