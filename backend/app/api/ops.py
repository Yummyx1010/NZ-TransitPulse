"""Operational endpoints: liveness and service metadata."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..core.config import Settings
from ..core.constants import ATTRIBUTION


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str
    realtime_feed: str = Field(
        description="'configured' or 'not_configured'; never exposes the key"
    )


class MetaResponse(BaseModel):
    name: str
    version: str
    region: str
    timezone: str
    api_prefix: str
    phase: str
    attribution: str
    data_sources: list[str]


def create_ops_router(settings: Settings) -> APIRouter:
    """Build the operations router bound to a settings instance."""
    router = APIRouter(tags=["operations"])

    @router.get("/health", response_model=HealthResponse, summary="Liveness probe")
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            environment=settings.environment,
            version="0.1.0",
            realtime_feed="configured" if settings.realtime_configured else "not_configured",
        )

    @router.get(
        f"{settings.api_v1_prefix}/meta",
        response_model=MetaResponse,
        summary="Service metadata and data attribution",
    )
    def meta() -> MetaResponse:
        return MetaResponse(
            name="NZ TransitPulse",
            version="0.1.0",
            region="Auckland, New Zealand",
            timezone="Pacific/Auckland",
            api_prefix=settings.api_v1_prefix,
            phase="0 - Foundation",
            attribution=ATTRIBUTION,
            data_sources=[
                "Auckland Transport GTFS static",
                "Auckland Transport GTFS-Realtime",
            ],
        )

    return router
