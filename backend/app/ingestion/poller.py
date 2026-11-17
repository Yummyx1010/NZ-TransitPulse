"""Background poller for the aggregated AT realtime feed."""

from __future__ import annotations

import threading

from .client import ATRealtimeClient
from .decoder import decode_feed
from .models import RealtimeSnapshot
from .snapshot import SnapshotStore


class RealtimePoller:
    """Polls in a daemon thread; the FastAPI lifespan owns start/stop."""

    def __init__(
        self,
        client: ATRealtimeClient,
        store: SnapshotStore,
        interval_seconds: int,
    ) -> None:
        self._client = client
        self._store = store
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def poll_once(self) -> RealtimeSnapshot | None:
        """Fetch, decode and publish exactly one snapshot. Safe to call manually."""
        try:
            snapshot = decode_feed(self._client.fetch())
        except Exception as exc:  # noqa: BLE001 - keep the worker alive on any upstream failure
            self._store.record_error(f"{type(exc).__name__}: {exc}")
            return None
        self._store.publish(snapshot)
        return snapshot

    def start(self) -> None:
        if self.is_running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="at-realtime-poller", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _interval_with_backoff(self) -> int:
        """Halve the polling rate once 80% of the weekly quota has been used."""
        budget = self._client.budget
        if budget.calls_in_window() > int(budget.limit * 0.8):
            return self._interval * 2
        return self._interval

    def _run(self) -> None:
        while not self._stop.is_set():
            self.poll_once()
            self._stop.wait(self._interval_with_backoff())
