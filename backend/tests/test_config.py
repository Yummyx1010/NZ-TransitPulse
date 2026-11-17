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


def test_realtime_readiness_requires_a_key_and_the_aggregated_url() -> None:
    without_key = _test_settings(at_api_key="")
    without_url = _test_settings(at_api_key="test-key", at_realtime_url="")
    ready = _test_settings(at_api_key="test-key")

    assert without_key.realtime_configured is False
    assert without_url.realtime_configured is False
    assert ready.realtime_configured is True
    assert ready.realtime_polling_enabled is False


def test_polling_is_enabled_only_outside_tests_with_credentials() -> None:
    local = _test_settings(environment="local", at_api_key="test-key")
    disabled = _test_settings(
        environment="local", at_api_key="test-key", at_realtime_auto_start=False
    )

    assert local.realtime_polling_enabled is True
    assert disabled.realtime_polling_enabled is False


def test_weekly_quota_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="must be positive"):
        _test_settings(at_max_calls_per_week=0)


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
