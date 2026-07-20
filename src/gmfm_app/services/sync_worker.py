"""
Sync Worker — background thread that auto-syncs when connectivity is available.
Checks every 60 seconds, pushes pending changes, optionally pulls.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from gmfm_app.services.sync_service import SyncService, SyncResult


def _log(msg):
    try:
        print(f"[SYNC_WORKER] {msg}", flush=True)
    except Exception:
        pass


class SyncWorker:
    """Background auto-sync thread."""

    def __init__(
        self,
        sync_service: SyncService,
        interval_seconds: int = 60,
        on_sync_complete: Optional[Callable[[SyncResult], None]] = None,
    ):
        self.sync_service = sync_service
        self.interval = interval_seconds
        self.on_sync_complete = on_sync_complete
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        _log(f"Started (interval={self.interval}s)")

    def stop(self):
        self._running = False
        _log("Stopped")

    def _run_loop(self):
        # Initial delay to let app fully load
        time.sleep(5)

        while self._running:
            try:
                is_online = self.sync_service.is_online()
                if not is_online:
                    _log("Offline — skipping sync cycle")
                else:
                    pending = self.sync_service.get_pending_count()

                    # Always try to maintain authentication when online
                    authed = self.sync_service._user_id is not None or self.sync_service.ensure_auth()

                    if authed:
                        if pending > 0:
                            _log(f"Auto-syncing {pending} pending items...")
                            result = self.sync_service.sync()
                            _log(f"Auto-sync result: {result.summary}")
                        else:
                            # No pending pushes — still pull to get remote changes
                            result = self.sync_service.pull()
                            if result.pulled > 0:
                                _log(f"Pull-only sync: pulled {result.pulled}")

                        if self.on_sync_complete:
                            try:
                                self.on_sync_complete(result)
                            except Exception:
                                pass
                    else:
                        _log(f"Skipping sync — not authenticated ({pending} pending)")
            except Exception as e:
                _log(f"Auto-sync error: {e}")

            # Sleep in small increments so we can stop quickly
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)
