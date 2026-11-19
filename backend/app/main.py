"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .api.analytics import create_analytics_router
from .api.arrivals import create_arrivals_router
from .api.network import create_network_router
from .api.official import create_official_router
from .api.ops import create_ops_router
from .api.realtime import create_realtime_router
from .core.config import Settings, get_settings
from .ingestion.client import ATRealtimeClient, CallBudget
from .ingestion.poller import RealtimePoller
from .ingestion.snapshot import SnapshotStore

DESCRIPTION = (
    "Public transport monitoring and analytics for Auckland, New Zealand. "
    "Data sourced from Auckland Transport (CC BY 4.0). "
    "This is an independent project, not affiliated with Auckland Transport."
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory; passing settings explicitly keeps tests deterministic."""
    active_settings = settings or get_settings()

    store = SnapshotStore()
    budget = CallBudget(active_settings.at_max_calls_per_week)
    client = ATRealtimeClient(active_settings, budget=budget)
    poller = RealtimePoller(client, store, active_settings.at_realtime_poll_seconds)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if active_settings.realtime_polling_enabled:
            poller.start()
        try:
            yield
        finally:
            poller.stop()
            client.close()

    app = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        description=DESCRIPTION,
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.exception_handler(SQLAlchemyError)
    async def database_unavailable(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    app.state.settings = active_settings
    app.state.realtime_store = store
    app.state.realtime_budget = budget
    app.state.realtime_poller = poller
    app.include_router(create_ops_router(active_settings))
    app.include_router(create_network_router(active_settings))
    app.include_router(create_realtime_router(active_settings, store, budget, poller))
    app.include_router(create_arrivals_router(active_settings, store))
    app.include_router(create_official_router())
    app.include_router(create_analytics_router())
    return app


app = create_app()
