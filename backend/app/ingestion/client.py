"""HTTP client for the AT aggregated realtime feed.

A rolling seven-day call budget keeps the subscription under its weekly quota, and a
bounded exponential backoff prevents an AT outage from burning that quota.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ..core.config import Settings


class RealtimeNotConfigured(RuntimeError):
    """Raised when no subscription key or feed URL is configured."""


class RealtimeFetchError(RuntimeError):
    """Raised after all retries fail or the response is unusable."""


class QuotaExceeded(RuntimeError):
    """Raised when the rolling weekly budget is nearly exhausted."""


class CallBudget:
    """Thread-safe rolling seven-day counter of outbound AT API calls."""

    def __init__(self, limit: int, *, window_days: int = 7, reserve: float = 0.9):
        self._limit = limit
        self._window = timedelta(days=window_days)
        self._reserve = reserve
        self._calls: deque[datetime] = deque()
        self._lock = threading.Lock()

    @property
    def limit(self) -> int:
        return self._limit

    def _prune(self, now: datetime) -> None:
        cutoff = now - self._window
        while self._calls and self._calls[0] < cutoff:
            self._calls.popleft()

    def calls_in_window(self) -> int:
        with self._lock:
            self._prune(datetime.now(UTC))
            return len(self._calls)

    def remaining(self) -> int:
        return max(0, self._limit - self.calls_in_window())

    def allow(self) -> bool:
        with self._lock:
            self._prune(datetime.now(UTC))
            return len(self._calls) < int(self._limit * self._reserve)

    def record(self) -> None:
        with self._lock:
            now = datetime.now(UTC)
            self._prune(now)
            self._calls.append(now)


class ATRealtimeClient:
    """Fetch one aggregated feed snapshot; never logs or stores the API key."""

    def __init__(
        self,
        settings: Settings,
        *,
        budget: CallBudget | None = None,
        transport: httpx.BaseTransport | None = None,
        sleeper=time.sleep,
    ):
        self._settings = settings
        self._budget = budget or CallBudget(settings.at_max_calls_per_week)
        self._sleeper = sleeper
        self._client = httpx.Client(
            timeout=settings.at_realtime_timeout_seconds,
            transport=transport,
            follow_redirects=True,
        )

    @property
    def budget(self) -> CallBudget:
        return self._budget

    def close(self) -> None:
        self._client.close()

    def fetch(self) -> dict[str, Any]:
        if not self._settings.realtime_configured:
            raise RealtimeNotConfigured("TP_AT_API_KEY or TP_AT_REALTIME_URL is missing")
        if not self._budget.allow():
            raise QuotaExceeded("weekly AT API call budget is nearly exhausted")

        retries = max(1, self._settings.at_realtime_max_retries)
        last_error: Exception | None = None
        for attempt in range(retries):
            self._budget.record()
            try:
                response = self._client.get(
                    self._settings.at_realtime_url,
                    headers={
                        "Ocp-Apim-Subscription-Key": self._settings.at_api_key,
                        "Accept": "application/json",
                    },
                )
                if response.status_code == 200:
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise RealtimeFetchError("feed response is not a JSON object")
                    return payload
                last_error = RealtimeFetchError(
                    f"AT realtime feed returned HTTP {response.status_code}"
                )
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    break
            except (httpx.RequestError, ValueError) as exc:
                last_error = exc
            if attempt + 1 < retries:
                self._sleeper(min(2**attempt, 8))
        raise RealtimeFetchError(f"could not fetch AT realtime feed: {last_error}")
