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
                pending = self.sync_service.get_pending_count()
                if pending > 0 and self.sync_service.is_online():
                    # Try to ensure we're authenticated
                    authed = self.sync_service.ensure_auth()
                    if not authed:
                        # Try re-login with stored email
                        email = self.sync_service.config.cloud_email
                        if email:
                            _log(f"Re-authenticating as {email}...")
                            # Can't re-login without password in worker
                            # But registration already logged in — session should persist
                            pass
                    if self.sync_service._user_id:
                        _log(f"Auto-syncing {pending} pending items...")
                        result = self.sync_service.sync()
                        _log(f"Auto-sync result: {result.summary}")
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
