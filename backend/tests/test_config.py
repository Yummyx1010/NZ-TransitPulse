"""Tests for configuration loading and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import AT_MIN_POLL_SECONDS, Settings, get_settings


def _test_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "_env_file": None,
        "environment": "test",
        "at_api_key": "",
    }
    return Settings(**{**base, **overrides})


def test_defaults_are_safe_for_local_development(settings: Settings) -> None:
    assert settings.environment == "test"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.at_realtime_poll_seconds == AT_MIN_POLL_SECONDS
    assert settings.database_url.startswith("mysql+pymysql://")
    assert settings.realtime_configured is False


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = _test_settings(
        cors_origins="http://localhost:5173, https://example.org , ,"
    )

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "https://example.org",
    ]


def test_realtime_requires_key_and_all_three_feed_urls() -> None:
    partial = _test_settings(
        at_api_key="test-key",
        at_vehicle_positions_url="https://example.invalid/vehicles",
    )
    complete = _test_settings(
        at_api_key="test-key",
        at_vehicle_positions_url="https://example.invalid/vehicles",
        at_trip_updates_url="https://example.invalid/trips",
        at_service_alerts_url="https://example.invalid/alerts",
    )

    assert partial.realtime_configured is False
    assert complete.realtime_configured is True


def test_poll_interval_below_feed_refresh_rate_is_rejected() -> None:
    with pytest.raises(ValidationError, match="poll interval must be >= 30s"):
        _test_settings(at_realtime_poll_seconds=10)


def test_environment_variables_use_tp_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TP_AT_API_KEY", "from-environment")
    monkeypatch.setenv("TP_ENVIRONMENT", "staging")

    settings = Settings(_env_file=None)

    assert settings.at_api_key == "from-environment"
    assert settings.environment == "staging"


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()
