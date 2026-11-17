"""Tests for the AT realtime HTTP client and its weekly call budget."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.ingestion.client import (
    ATRealtimeClient,
    CallBudget,
    QuotaExceeded,
    RealtimeFetchError,
    RealtimeNotConfigured,
)
from tests.fixtures import build_realtime_payload


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "_env_file": None,
        "environment": "test",
        "at_api_key": "test-key",
        "at_realtime_url": "https://example.invalid/feed",
        "at_realtime_max_retries": 3,
    }
    return Settings(**{**base, **overrides})


def _client(handler, settings: Settings, budget: CallBudget | None = None):
    return ATRealtimeClient(
        settings,
        budget=budget,
        transport=httpx.MockTransport(handler),
        sleeper=lambda _: None,
    )


def test_fetch_sends_the_subscription_key_and_records_one_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Ocp-Apim-Subscription-Key"] == "test-key"
        assert request.headers["Accept"] == "application/json"
        return httpx.Response(200, json=build_realtime_payload())

    client = _client(handler, _settings(), CallBudget(100))
    try:
        payload = client.fetch()
        assert payload["status"] == "OK"
        assert client.budget.calls_in_window() == 1
    finally:
        client.close()


def test_transient_5xx_is_retried_with_backoff() -> None:
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(503, json={"error": "upstream"})
        return httpx.Response(200, json=build_realtime_payload())

    client = _client(handler, _settings(), CallBudget(100))
    try:
        assert client.fetch()["status"] == "OK"
        assert len(attempts) == 3
        assert client.budget.calls_in_window() == 3
    finally:
        client.close()


def test_client_4xx_is_not_retried() -> None:
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(401, json={"message": "invalid key"})

    client = _client(handler, _settings(), CallBudget(100))
    try:
        with pytest.raises(RealtimeFetchError, match="HTTP 401"):
            client.fetch()
        assert len(attempts) == 1
    finally:
        client.close()


def test_missing_credentials_fail_without_a_request() -> None:
    client = _client(lambda request: httpx.Response(200, json={}), _settings(at_api_key=""))
    try:
        with pytest.raises(RealtimeNotConfigured):
            client.fetch()
        assert client.budget.calls_in_window() == 0
    finally:
        client.close()


def test_quota_budget_blocks_calls_before_hitting_the_limit() -> None:
    budget = CallBudget(10)
    for _ in range(9):
        budget.record()
    assert budget.allow() is False
    assert budget.remaining() == 1

    client = _client(
        lambda request: httpx.Response(200, json={}), _settings(), budget
    )
    try:
        with pytest.raises(QuotaExceeded):
            client.fetch()
        assert budget.calls_in_window() == 9
    finally:
        client.close()


def test_network_error_is_wrapped_after_retries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client(handler, _settings(at_realtime_max_retries=2), CallBudget(100))
    try:
        with pytest.raises(RealtimeFetchError, match="could not fetch"):
            client.fetch()
        assert client.budget.calls_in_window() == 2
    finally:
        client.close()
