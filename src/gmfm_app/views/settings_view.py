"""
Settings View - App Configuration with Cloud Sync
"""
import flet as ft
from gmfm_app.data.database import DatabaseContext
from gmfm_app.services.haptics import tap, success, warning


PRIMARY = "#0D9488"
SECONDARY = "#7C3AED"
SUCCESS_CLR = "#10B981"
ERROR = "#EF4444"
WARNING_CLR = "#F59E0B"
INFO = "#3B82F6"


def _colors(is_dark):
    if is_dark:
        return {
            "BG": "#0F172A", "CARD": "#1E293B", "BORDER": "#334155",
            "TEXT1": "#F8FAFC", "TEXT2": "#94A3B8", "TEXT3": "#64748B",
        }
    return {
        "BG": "#F8FAFC", "CARD": "#FFFFFF", "BORDER": "#E2E8F0",
        "TEXT1": "#1E293B", "TEXT2": "#64748B", "TEXT3": "#94A3B8",
    }


class SettingsView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, is_dark: bool = False,
                 auth_service=None, sync_service=None, user_id=None,
                 visible_ids=None, can_write=True, unrestricted=False):
        c = _colors(is_dark)
        self._c = c
        super().__init__(route="/settings", padding=0, bgcolor=c["BG"])
        self._page_ref = page
        self.db_context = db_context
        self.auth_service = auth_service
        self.sync_service = sync_service
        self._user_id = user_id
        self._visible_ids = visible_ids
        self._can_write = can_write
        self._unrestricted = unrestricted

        # Header
        header = ft.SafeArea(
            content=ft.Container(
                content=ft.Row([
                    ft.IconButton("arrow_back", icon_color=c["TEXT1"], on_click=lambda _: self._page_ref.go("/")),
                    ft.Text("Settings", size=20, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                ]),
                padding=ft.padding.symmetric(horizontal=10, vertical=10),
                bgcolor=c["CARD"],
                border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
            ),
            minimum_padding=ft.padding.only(top=5),
            bottom=False,
        )

        # Theme Toggle
        self.dark_mode = ft.Switch(
            value=self._page_ref.theme_mode == ft.ThemeMode.DARK,
            on_change=self._toggle_theme,
            active_color=PRIMARY,
        )

        theme_card = self._settings_card(
            "Appearance",
            [self._setting_row("Dark Mode", "Enable dark theme", self.dark_mode)]
        )

        # ── Cloud Sync Section ─────────────────────────────────────
        cloud_card = self._build_cloud_card()

        data_card = self._settings_card(
            "Data Management",
            [
                self._action_row("Export as JSON", "Download all data as JSON", "code", self._export_data),
                self._action_row("Export as CSV", "Download for Excel/Sheets", "table_chart", self._export_csv),
                self._action_row("Export All as PDF", "Export PDF reports for all records", "picture_as_pdf", self._export_all_pdfs),
                self._action_row("Clear All Data", "Delete all students and sessions", "delete_forever", self._clear_data, danger=True),
            ]
        )

        account_rows = []
        if self.auth_service is not None:
            account_rows.append(
                self._action_row("Sign Out", "Lock app and return to login", "logout", self._sign_out)
            )
        account_card = self._settings_card("Account", account_rows) if account_rows else None

        # About
        about_card = self._settings_card(
            "About",
            [
                self._info_row("Version", "0.2.0"),
                self._info_row("GMFM Scale", "GMFM-88"),
                self._info_row("Developer", "MotorMeasure Team (Sathyabama Institute of Science and Technology)"),
            ]
        )

        self.controls = [
            header,
            ft.Container(
                content=ft.Column(
                    [x for x in [theme_card, cloud_card, data_card, account_card, about_card] if x is not None],
                    scroll=ft.ScrollMode.ADAPTIVE,
                ),
                padding=20,
                expand=True,
            )
        ]

    # ── Cloud Sync Card ────────────────────────────────────────────
    def _build_cloud_card(self):
        c = self._c

        # ── Determine the correct cloud email ──────────────────────
        # Priority: current logged-in user's email > sync_service config > client_storage.
        # This prevents stale client_storage values from showing a wrong address.
        cloud_email = ""

        # 1. Best source: the actual logged-in user record
        if self.auth_service:
            try:
                current_user = self.auth_service.current_user(self._page_ref)
                if current_user:
                    cloud_email = (getattr(current_user, 'email', '') or '').strip()
            except Exception:
                pass

        # 2. Fallback: live sync_service config (set by _finalize_cloud_uid after login)
        if not cloud_email and self.sync_service:
            cloud_email = (self.sync_service.config.cloud_email or '').strip()

        # 3. Last resort: client_storage (may be stale, but better than nothing)
        if not cloud_email:
            try:
                from gmfm_app.services.sync_config import load_config
                cloud_email = (load_config(self._page_ref).cloud_email or '').strip()
            except Exception:
                pass

        # Keep sync_service.config.cloud_email aligned with the current user so
        # the worker always authenticates with the right address.
        if cloud_email and self.sync_service and self.sync_service.config.cloud_email != cloud_email:
            self.sync_service.config.cloud_email = cloud_email

        from gmfm_app.services.sync_config import load_config
        config = self.sync_service.config if self.sync_service else load_config(self._page_ref)
        is_configured = config.is_configured()

        is_authed = False
        if self.sync_service:
            is_authed = bool(self.sync_service._user_id) or self.sync_service.ensure_auth()

        pending = 0
        if self.sync_service:
            try:
                pending = self.sync_service.get_pending_count()
            except Exception:
                pass

        # Status display
        if is_authed and pending == 0:
            status_color, status_text, status_icon = SUCCESS_CLR, "Connected", "cloud_done"
        elif is_authed and pending > 0:
            status_color, status_text, status_icon = WARNING_CLR, f"{pending} pending", "cloud_upload"
        elif is_configured and cloud_email:
            status_color, status_text, status_icon = WARNING_CLR, "Not authenticated", "cloud_off"
        else:
            status_color, status_text, status_icon = c["TEXT3"], "Not configured", "cloud_off"

        rows = []

        # Status row
        rows.append(
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(status_icon, color="white", size=20),
                        width=40, height=40, bgcolor=status_color,
                        border_radius=10, alignment=ft.alignment.center,
                    ),
                    ft.Container(width=12),
                    ft.Column([
                        ft.Text("Cloud Sync", size=14, weight=ft.FontWeight.W_600, color=c["TEXT1"]),
                        ft.Text(status_text, size=12, color=status_color),
                    ], spacing=2, expand=True),
                ]),
                padding=ft.padding.symmetric(vertical=8),
            )
        )

        if not is_configured:
            rows.append(ft.Container(
                content=ft.Text(
                    "Cloud sync is auto-configured. Log out and register a new account with a valid email to enable cloud backup.",
                    size=12, color=c["TEXT3"]),
                padding=ft.padding.symmetric(vertical=4),
            ))
        else:
            # Show cloud account info
            if cloud_email:
                rows.append(ft.Container(
                    content=ft.Row([
                        ft.Icon("account_circle", color=PRIMARY, size=18),
                        ft.Container(width=6),
                        ft.Text(cloud_email, size=13, color=c["TEXT1"], expand=True,
                                no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Icon("check_circle" if is_authed else "error_outline",
                                color=SUCCESS_CLR if is_authed else WARNING_CLR, size=16),
                    ]),
                    padding=ft.padding.symmetric(vertical=6),
                ))

            # Action buttons
            rows.append(ft.Divider(color=c["BORDER"]))
            rows.append(
                self._action_row("Sync Now", f"Push & pull ({pending} pending)", "sync",
                                 self._sync_now)
            )
            rows.append(
                self._action_row("Restore from Cloud", "Download all data", "cloud_download",
                                 self._restore_from_cloud)
            )

        return self._settings_card("Cloud Sync", rows)

    def _sync_now(self, e):
        try:
            print("[SETTINGS] Sync Now clicked", flush=True)
            if not self.sync_service:
                self._snack("Cloud sync not available", ERROR)
                return
            try:
                tap(self._page_ref)
            except Exception:
                pass

            if not self.sync_service._user_id and not self.sync_service.ensure_auth():
                # Session expired and no in-memory password available.
                # Show a password prompt so the user can re-authenticate without
                # having to sign out and back in.
                print("[SETTINGS] Not authenticated — showing re-auth dialog", flush=True)
                self._show_reauth_dialog()
                return

            self._do_sync()
        except Exception as ex:
            print(f"[SETTINGS] Sync error: {ex}", flush=True)
            try:
                self._snack(f"Sync error: {str(ex)[:80]}", ERROR)
            except Exception:
                pass

    def _do_sync(self):
        """Run a full push+pull cycle and show the result as a snackbar."""
        try:
            self._snack("Syncing…", INFO)
            result = self.sync_service.sync()
            if result.success and not result.errors:
                try:
                    success(self._page_ref)
                except Exception:
                    pass
                self._snack(f"Sync complete: {result.summary}", SUCCESS_CLR)
            elif result.pushed > 0 or result.pulled > 0:
                self._snack(f"Partial sync: {result.summary}", WARNING_CLR)
            else:
                first_err = result.errors[0] if result.errors else "Unknown error"
                self._snack(f"Sync failed: {first_err}", ERROR)
            print(f"[SETTINGS] Sync result: {result.summary}", flush=True)
            for err in result.errors:
                print(f"[SETTINGS] Sync error detail: {err}", flush=True)
        except Exception as ex:
            print(f"[SETTINGS] _do_sync error: {ex}", flush=True)
            self._snack(f"Sync error: {str(ex)[:80]}", ERROR)

    def _show_reauth_dialog(self):
        """Show a password dialog when the cloud session has expired.
        On success, re-authenticates and immediately runs a sync."""
        c = self._c

        # Resolve the cloud email to display
        cloud_email = ""
        if self.auth_service:
            try:
                cu = self.auth_service.current_user(self._page_ref)
                if cu:
                    cloud_email = (getattr(cu, 'email', '') or '').strip()
            except Exception:
                pass
        if not cloud_email and self.sync_service:
            cloud_email = (self.sync_service.config.cloud_email or '').strip()

        pw_field = ft.TextField(
            label="Cloud Password",
            password=True,
            can_reveal_password=True,
            border_radius=12,
            bgcolor=c["CARD"],
            border_color=c["BORDER"],
            focused_border_color=PRIMARY,
            color=c["TEXT1"],
            label_style=ft.TextStyle(color=c["TEXT3"]),
            autofocus=True,
        )
        err_text = ft.Text("", color=ERROR, size=12, visible=False)

        def do_reauth(e):
            password = (pw_field.value or "").strip()
            if not password:
                err_text.value = "Please enter your password"
                err_text.visible = True
                try:
                    dlg.update()
                except Exception:
                    pass
                return
            if not cloud_email:
                err_text.value = "No cloud email configured"
                err_text.visible = True
                try:
                    dlg.update()
                except Exception:
                    pass
                return

            ok, msg = self.sync_service.login(cloud_email, password)
            if ok:
                self._page_ref.close(dlg)
                self._do_sync()
            else:
                err_text.value = f"Sign-in failed: {msg}"
                err_text.visible = True
                try:
                    dlg.update()
                except Exception:
                    pass

        def cancel(e):
            self._page_ref.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("Session Expired"),
            content=ft.Column([
                ft.Text(
                    f"Your cloud session for\n{cloud_email}\nhas expired. Re-enter your password to sync.",
                    size=13, color=c["TEXT2"],
                ),
                ft.Container(height=10),
                pw_field,
                err_text,
            ], tight=True, spacing=4),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.ElevatedButton(
                    "Sign In & Sync",
                    bgcolor=PRIMARY, color="white",
                    on_click=do_reauth,
                ),
            ],
            on_dismiss=cancel,
        )
        self._page_ref.open(dlg)

    def _restore_from_cloud(self, e):
        if not self.sync_service:
            self._snack("Sync service not available", ERROR)
            return
        tap(self._page_ref)
        self._snack("Restoring from cloud...", INFO)
        try:
            result = self.sync_service.restore_from_cloud()
            if result.pulled > 0:
                success(self._page_ref)
                self._snack(f"Restored {result.pulled} records from cloud! ✓", SUCCESS_CLR)
            else:
                self._snack("No records found in cloud", WARNING_CLR)
        except Exception as ex:
            self._snack(f"Restore error: {str(ex)[:80]}", ERROR)

    def _disconnect_cloud(self, e):
        warning(self._page_ref)
        from gmfm_app.services.sync_config import clear_config
        if self.sync_service:
            self.sync_service.cloud_logout()
        clear_config(self._page_ref)
        self._snack("Cloud disconnected", WARNING_CLR)
        self._page_ref.go("/settings")

    # ── Existing methods (unchanged) ──────────────────────────────

    def _settings_card(self, title, rows):
        c = self._c
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                ft.Container(height=10),
                *rows,
            ]),
            padding=20,
            bgcolor=c["CARD"],
            border_radius=16,
            border=ft.border.all(1, c["BORDER"]),
            margin=ft.margin.only(bottom=15),
        )

    def _setting_row(self, title, subtitle, control):
        c = self._c
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=c["TEXT1"]),
                    ft.Text(subtitle, size=12, color=c["TEXT3"]),
                ], spacing=2, expand=True),
                control,
            ]),
            padding=ft.padding.symmetric(vertical=10),
        )

    def _action_row(self, title, subtitle, icon, on_click, danger=False):
        c = self._c
        color = ERROR if danger else PRIMARY
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color=color, size=20),
                    width=40, height=40,
                    bgcolor=f"{color}20",
                    border_radius=10,
                    alignment=ft.alignment.center,
                ),
                ft.Container(width=12),
                ft.Column([
                    ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=color if danger else c["TEXT1"]),
                    ft.Text(subtitle, size=12, color=c["TEXT3"]),
                ], spacing=2, expand=True),
                ft.Icon("chevron_right", color=c["TEXT3"]),
            ]),
            padding=ft.padding.symmetric(vertical=10),
            on_click=on_click,
            ink=True,
        )

    def _info_row(self, label, value):
        c = self._c
        return ft.Container(
            content=ft.Row([
                ft.Text(label, size=14, color=c["TEXT2"], expand=1),
                ft.Container(
                    content=ft.Text(
                        value, size=14, weight=ft.FontWeight.W_500,
                        color=c["TEXT1"], text_align=ft.TextAlign.RIGHT, no_wrap=False,
                    ),
                    expand=2,
                    alignment=ft.alignment.top_right,
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=8),
        )

    def _snack(self, msg, color):
        self._page_ref.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
        self._page_ref.snack_bar.open = True
        self._page_ref.update()

    def _toggle_theme(self, e):
        tap(self._page_ref)
        if self.dark_mode.value:
            self._page_ref.theme_mode = ft.ThemeMode.DARK
            self._page_ref.bgcolor = "#0F172A"  # matches Theme.DARK_BG in main.py
        else:
            self._page_ref.theme_mode = ft.ThemeMode.LIGHT
            self._page_ref.bgcolor = "#F8FAFC"
        self._page_ref.client_storage.set("dark_mode", self.dark_mode.value)
        self._page_ref.update()

    def _export_data(self, e):
        success(self._page_ref)
        import json
        from pathlib import Path
        from gmfm_app.data.repositories import StudentRepository, SessionRepository

        student_repo = StudentRepository(self.db_context, user_id=self._user_id, visible_ids=self._visible_ids, can_write=self._can_write, unrestricted=self._unrestricted)
        session_repo = SessionRepository(self.db_context, user_id=self._user_id, visible_ids=self._visible_ids, can_write=self._can_write, unrestricted=self._unrestricted)

        students = student_repo.list_students(limit=1000)
        export = {"students": [], "sessions": []}

        for s in students:
            export["students"].append({
                "id": s.id, "given_name": s.given_name, "family_name": s.family_name,
                "dob": str(s.dob) if s.dob else None, "identifier": s.identifier,
            })
            sessions = session_repo.list_sessions_for_student(s.id)
            for sess in sessions:
                export["sessions"].append({
                    "id": sess.id, "student_id": sess.student_id, "scale": sess.scale,
                    "total_score": sess.total_score, "notes": sess.notes,
                    "created_at": sess.created_at.isoformat(),
                })

        import os
        flet_storage = os.getenv("FLET_APP_STORAGE_DATA")
        if flet_storage:
            export_dir = Path(flet_storage) / "GMFM_Reports"
        else:
            try:
                export_dir = Path(os.path.expanduser("~")) / "Documents" / "GMFM_Reports"
            except Exception:
                export_dir = Path(".") / "GMFM_Reports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / "gmfm_export.json"
        export_path.write_text(json.dumps(export, indent=2))

        self._snack(f"Data exported to {export_path}", SUCCESS_CLR)

    def _export_csv(self, e):
        success(self._page_ref)
        import csv
        from pathlib import Path
        from gmfm_app.data.repositories import StudentRepository, SessionRepository

        student_repo = StudentRepository(self.db_context, user_id=self._user_id, visible_ids=self._visible_ids, can_write=self._can_write, unrestricted=self._unrestricted)
        session_repo = SessionRepository(self.db_context, user_id=self._user_id, visible_ids=self._visible_ids, can_write=self._can_write, unrestricted=self._unrestricted)
        students = student_repo.list_students(limit=1000)

        import os
        import sys
        flet_storage = os.getenv("FLET_APP_STORAGE_DATA")
        if flet_storage:
            export_dir = Path(flet_storage) / "GMFM_Reports"
        else:
            try:
                export_dir = Path(os.path.expanduser("~")) / "Documents" / "GMFM_Reports"
            except Exception:
                export_dir = Path(".") / "GMFM_Reports"
        export_dir.mkdir(parents=True, exist_ok=True)

        students_path = export_dir / "students.csv"
        with open(students_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "First Name", "Last Name", "DOB", "Identifier"])
            for s in students:
                writer.writerow([s.id, s.given_name, s.family_name, str(s.dob) if s.dob else "", s.identifier or ""])

        sessions_path = export_dir / "sessions.csv"
        with open(sessions_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Student ID", "Student Name", "Scale", "Total Score", "Notes", "Date"])
            for s in students:
                sessions = session_repo.list_sessions_for_student(s.id)
                for sess in sessions:
                    writer.writerow([
                        sess.id, sess.student_id, f"{s.given_name} {s.family_name}",
                        sess.scale, f"{sess.total_score:.1f}%", sess.notes or "",
                        sess.created_at.strftime("%Y-%m-%d %H:%M")
                    ])

        self._snack(f"CSV files saved to {export_dir}!", SUCCESS_CLR)

        if sys.platform == "win32":
            try:
                import subprocess
                subprocess.Popen(f'explorer "{export_dir}"')
            except Exception:
                pass

    def _export_all_pdfs(self, e):
        success(self._page_ref)
        from pathlib import Path
        import os
        import sys
        from gmfm_app.data.repositories import StudentRepository, SessionRepository
        from gmfm_app.scoring.engine import calculate_gmfm_scores
        from gmfm_app.services.report_service import generate_report

        def on_dir_picked(e_picker: ft.FilePickerResultEvent):
            if not e_picker.path:
                return

            export_dir = Path(e_picker.path)
            export_dir.mkdir(parents=True, exist_ok=True)

            self._snack("Exporting all PDF reports...", INFO)
            self._page_ref.update()

            from gmfm_app.data.repositories import StudentRepository, SessionRepository, get_tester_name
            student_repo = StudentRepository(self.db_context, user_id=self._user_id, visible_ids=self._visible_ids, can_write=self._can_write, unrestricted=self._unrestricted)
            session_repo = SessionRepository(self.db_context, user_id=self._user_id, visible_ids=self._visible_ids, can_write=self._can_write, unrestricted=self._unrestricted)
            students = student_repo.list_students(limit=1000)

            count = 0
            errors = 0
            for s in students:
                sessions = session_repo.list_sessions_for_student(s.id)
                for sess in sessions:
                    try:
                        results = calculate_gmfm_scores(sess.raw_scores, scale=sess.scale)
                        tester = get_tester_name(self.db_context, sess, self._user_id)
                        safe_tester = "".join(c for c in tester if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                        safe_given = "".join(c for c in s.given_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                        safe_family = "".join(c for c in s.family_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                        filename = f"GMFM_{safe_given}_{safe_family}_TestedBy_{safe_tester}_{sess.created_at.strftime('%Y%m%d_%H%M%S')}.pdf"
                        output_path = export_dir / filename

                        generate_report(
                            student=s,
                            session=sess,
                            scoring_result=results,
                            output_path=output_path,
                            tester_name=tester,
                        )
                        count += 1
                    except Exception as ex:
                        print(f"[SETTINGS] Failed to export PDF for session {sess.id}: {ex}", flush=True)
                        errors += 1

            if count > 0:
                msg = f"Successfully exported {count} PDF report(s) to {export_dir}!"
                if errors > 0:
                    msg += f" ({errors} failed)"
                self._snack(msg, SUCCESS_CLR)
                if sys.platform == "win32":
                    try:
                        import subprocess
                        subprocess.Popen(f'explorer "{export_dir}"')
                    except Exception:
                        pass
            elif errors > 0:
                self._snack(f"Failed to export PDFs ({errors} error(s)).", ERROR)
            else:
                self._snack("No assessment sessions found to export.", WARNING_CLR)

        file_picker = ft.FilePicker(on_result=on_dir_picked)
        self._page_ref.overlay.append(file_picker)
        self._page_ref.update()
        file_picker.get_directory_path(dialog_title="Select Folder to Export All Student PDFs")

    def _clear_data(self, e):
        warning(self._page_ref)

        def confirm_clear(e):
            warning(self._page_ref)
            from gmfm_app.data.database import resolve_db_path, _db_initialized
            import os
            db_path = resolve_db_path()
            if db_path.exists():
                os.remove(db_path)
            # Clear the init-cache so get_connection() re-runs init_db on next
            # access (creates a fresh schema rather than hitting missing tables).
            _db_initialized.discard(str(db_path))
            self._page_ref.close(dlg)
            self._snack("All data cleared. Please restart the app.", SUCCESS_CLR)
            # Sign out — all user accounts are gone with the DB
            if self.auth_service:
                try:
                    self.auth_service.logout(self._page_ref)
                except Exception:
                    pass
            else:
                try:
                    from gmfm_app.services.auth_service import SESSION_USER_ID, SESSION_USERNAME
                    self._page_ref.client_storage.remove(SESSION_USER_ID)
                    self._page_ref.client_storage.remove(SESSION_USERNAME)
                except Exception:
                    pass
            self._page_ref.go("/login")

        def cancel(e):
            self._page_ref.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("Clear All Data?"),
            content=ft.Text("This will permanently delete all students and sessions. This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Delete Everything", style=ft.ButtonStyle(color=ERROR), on_click=confirm_clear),
            ],
            on_dismiss=cancel,
        )
        self._page_ref.open(dlg)

    def _sign_out(self, e):
        warning(self._page_ref)
        if self.auth_service is not None:
            self.auth_service.logout(self._page_ref)
        self._page_ref.go("/login")
