"""
Sync Worker — background thread that auto-syncs when connectivity is available.
Checks every 60 seconds, pushes pending changes, optionally pulls.
Also auto-provisions cloud accounts for users created offline.
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

    def _provision_pending_accounts(self):
        """Auto-provision cloud accounts for users created while offline.

        Since we don't store plaintext passwords, we can't call
        register_with_metadata() directly.  However, if the current Supabase
        session is active, the authenticated user's cloud_uid can be back-
        filled.  For *other* users, provisioning happens automatically on
        their next login via AuthService._cloud_provision().

        This method still logs pending accounts so operators can track them.
        """
        try:
            pending = self.sync_service.get_unsynced_users()
            if not pending:
                return

            _log(f"{len(pending)} user(s) pending cloud registration")

            # If the current session has an active user, check if any pending
            # account matches and backfill the cloud_uid.
            current_uid = self.sync_service._user_id
            if current_uid:
                client = self.sync_service._get_client()
                if client:
                    try:
                        session = client.auth.get_session()
                        session_user = getattr(session, 'user', None) if session else None
                        if session_user:
                            session_email = getattr(session_user, 'email', '') or ''
                            for u in pending:
                                if u['email'].lower() == session_email.lower():
                                    # This pending user is the currently logged-in user
                                    try:
                                        with self.sync_service.db_context.connect() as conn:
                                            cur = conn.cursor()
                                            cur.execute(
                                                "UPDATE app_users SET cloud_uid = ? WHERE id = ?",
                                                (session_user.id, u['id']),
                                            )
                                        _log(f"Backfilled cloud_uid for {u['email']}: {session_user.id[:8]}")
                                    except Exception as e:
                                        _log(f"Failed to backfill cloud_uid: {e}")
                    except Exception as e:
                        _log(f"Session check for backfill failed: {e}")

            # Log remaining pending users (will be provisioned on their next login)
            still_pending = self.sync_service.get_unsynced_users()
            if still_pending:
                emails = [u['email'] for u in still_pending]
                _log(f"Still pending cloud registration (will provision on next login): {emails}")
        except Exception as e:
            _log(f"Pending account provision error: {e}")

    def _run_loop(self):
        # Initial delay to let app fully load
        time.sleep(5)

        while self._running:
            try:
                is_online = self.sync_service.is_online()
                if not is_online:
                    _log("Offline — skipping sync cycle")
                else:
                    # Auto-provision any accounts created while offline
                    self._provision_pending_accounts()

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

