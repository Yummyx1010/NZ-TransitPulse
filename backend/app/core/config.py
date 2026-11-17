"""Application settings loaded from environment variables.

All configuration uses the ``TP_`` prefix. Secrets are never read from source files
or exposed through the API.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AT_MIN_POLL_SECONDS = 30


class Settings(BaseSettings):
    """Runtime configuration for the API and, later, the ingestion workers."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_prefix="TP_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    app_name: str = "NZ TransitPulse API"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "mysql+pymysql://transitpulse:transitpulse@127.0.0.1:3306/transitpulse"
    database_echo: bool = False
    gtfs_static_url: str = "https://gtfs.at.govt.nz/gtfs.zip"
    gtfs_data_dir: str = "data/gtfs"

    at_api_base_url: str = "https://api.at.govt.nz"
    at_api_key: str = ""
    # Aggregated GTFS-Realtime feed: one call returns vehicles, trip updates and alerts.
    at_realtime_url: str = "https://api.at.govt.nz/realtime/legacy"
    # Kept for an optional per-feed mode; the aggregated endpoint is the Phase 2 default.
    at_vehicle_positions_url: str = ""
    at_trip_updates_url: str = ""
    at_service_alerts_url: str = ""
    at_realtime_poll_seconds: int = AT_MIN_POLL_SECONDS
    at_realtime_timeout_seconds: float = 15.0
    at_realtime_max_retries: int = 3
    at_max_calls_per_week: int = 35000
    at_realtime_auto_start: bool = True
    on_time_threshold_seconds: int = 60

    @field_validator("at_max_calls_per_week")
    @classmethod
    def validate_quota(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("at_max_calls_per_week must be positive")
        return value

    @field_validator("at_realtime_poll_seconds")
    @classmethod
    def validate_poll_interval(cls, value: int) -> int:
        """AT refreshes GTFS-Realtime at least every 30 seconds."""
        if value < AT_MIN_POLL_SECONDS:
            raise ValueError(
                f"poll interval must be >= {AT_MIN_POLL_SECONDS}s "
                "(AT GTFS-Realtime feeds are not updated more often)"
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated CORS allow-list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def realtime_configured(self) -> bool:
        """True when the aggregated realtime feed can be polled."""
        return bool(self.at_api_key and self.at_realtime_url)

    @property
    def realtime_polling_enabled(self) -> bool:
        """Never start a live poller in unit tests or with missing credentials."""
        return (
            self.realtime_configured
            and self.at_realtime_auto_start
            and self.environment != "test"
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
