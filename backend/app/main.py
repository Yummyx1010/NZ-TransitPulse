"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .api.network import create_network_router
from .api.ops import create_ops_router
from .core.config import Settings, get_settings

DESCRIPTION = (
    "Public transport monitoring and analytics for Auckland, New Zealand. "
    "Data sourced from Auckland Transport (CC BY 4.0). "
    "This is an independent project, not affiliated with Auckland Transport."
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory; passing settings explicitly keeps tests deterministic."""
    active_settings = settings or get_settings()

    app = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        description=DESCRIPTION,
        docs_url="/docs",
        openapi_url="/openapi.json",
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
    app.include_router(create_ops_router(active_settings))
    app.include_router(create_network_router(active_settings))
    return app


app = create_app()
