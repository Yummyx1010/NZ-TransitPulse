"""Engine and session management.

The engine is created lazily on first use, so importing the application never opens a
database connection. This keeps unit tests and `/health` independent of MySQL.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import Settings, get_settings


def build_engine(settings: Settings) -> Engine:
    """Create an engine for MySQL (production) or SQLite (tests)."""
    if settings.database_url.startswith("sqlite"):
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=settings.database_echo,
        )
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.database_echo,
    )


@lru_cache
def get_engine() -> Engine:
    """Process-wide engine; callers can override in tests."""
    return build_engine(get_settings())


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    with factory() as session:
        yield session
