"""
Settings View - App Configuration
"""
import flet as ft
from gmfm_app.data.database import DatabaseContext, db_context
from gmfm_app.services.haptics import tap, success, warning


PRIMARY = "#0D9488"
SUCCESS = "#10B981"
ERROR = "#EF4444"


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
    def __init__(self, page: ft.Page, db_context: DatabaseContext, is_dark: bool = False):
        c = _colors(is_dark)
        self._c = c
        super().__init__(route="/settings", padding=0, bgcolor=c["BG"])
        self._page_ref = page
        self.db_context = db_context

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
            [
                self._setting_row("Dark Mode", "Enable dark theme", self.dark_mode),
            ]
        )

        # Data Management
        data_card = self._settings_card(
            "Data Management",
            [
                self._action_row("Export as JSON", "Download all data as JSON", "code", self._export_data),
                self._action_row("Export as CSV", "Download for Excel/Sheets", "table_chart", self._export_csv),
                self._action_row("Clear All Data", "Delete all students and sessions", "delete_forever", self._clear_data, danger=True),
            ]
        )

        # About
        about_card = self._settings_card(
            "About",
            [
                self._info_row("Version", "1.0.0"),
                self._info_row("GMFM Scale", "GMFM-88"),
                self._info_row("Developer", "MotorMeasure Team"),
            ]
        )

        self.controls = [
            header,
            ft.Container(
                content=ft.Column([theme_card, data_card, about_card], scroll=ft.ScrollMode.ADAPTIVE),
                padding=20,
                expand=True,
            )
        ]

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
                ft.Text(label, size=14, color=c["TEXT2"], expand=True),
                ft.Text(value, size=14, weight=ft.FontWeight.W_500, color=c["TEXT1"]),
            ]),
            padding=ft.padding.symmetric(vertical=8),
        )

    def _toggle_theme(self, e):
        tap(self._page_ref)  # Haptic feedback on toggle
        if self.dark_mode.value:
            self._page_ref.theme_mode = ft.ThemeMode.DARK
            self._page_ref.bgcolor = "#1A1A2E"
        else:
            self._page_ref.theme_mode = ft.ThemeMode.LIGHT
            self._page_ref.bgcolor = "#F8FAFC"
        # Persist preference
        self._page_ref.client_storage.set("dark_mode", self.dark_mode.value)
        self._page_ref.update()

    def _export_data(self, e):
        success(self._page_ref)  # Haptic feedback
        import json
        from pathlib import Path
        from gmfm_app.data.repositories import StudentRepository, SessionRepository
        
        student_repo = StudentRepository(self.db_context)
        session_repo = SessionRepository(self.db_context)
        
        students = student_repo.list_students(limit=1000)
        export = {"students": [], "sessions": []}
        
        for s in students:
            export["students"].append({
                "id": s.id,
                "given_name": s.given_name,
                "family_name": s.family_name,
                "dob": str(s.dob) if s.dob else None,
                "identifier": s.identifier,
            })
            sessions = session_repo.list_sessions_for_student(s.id)
            for sess in sessions:
                export["sessions"].append({
                    "id": sess.id,
                    "student_id": sess.student_id,
                    "scale": sess.scale,
                    "total_score": sess.total_score,
                    "notes": sess.notes,
                    "created_at": sess.created_at.isoformat(),
                })
        
        import os
        import sys
        # Use Android-safe path
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
        
        self._page_ref.snack_bar = ft.SnackBar(ft.Text(f"Data exported to {export_path}"), bgcolor=SUCCESS)
        self._page_ref.snack_bar.open = True
        self._page_ref.update()

    def _export_csv(self, e):
        """Export data as CSV for Excel/Sheets."""
        success(self._page_ref)  # Haptic feedback
        import csv
        from pathlib import Path
        from gmfm_app.data.repositories import StudentRepository, SessionRepository
        
        student_repo = StudentRepository(self.db_context)
        session_repo = SessionRepository(self.db_context)
        
        students = student_repo.list_students(limit=1000)
        
        import os
        import sys
        # Use Android-safe path
        flet_storage = os.getenv("FLET_APP_STORAGE_DATA")
        if flet_storage:
            export_dir = Path(flet_storage) / "GMFM_Reports"
        else:
            try:
                export_dir = Path(os.path.expanduser("~")) / "Documents" / "GMFM_Reports"
            except Exception:
                export_dir = Path(".") / "GMFM_Reports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Export students CSV
        students_path = export_dir / "students.csv"
        with open(students_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "First Name", "Last Name", "DOB", "Identifier"])
            for s in students:
                writer.writerow([s.id, s.given_name, s.family_name, str(s.dob) if s.dob else "", s.identifier or ""])
        
        # Export sessions CSV
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
        
        self._page_ref.snack_bar = ft.SnackBar(ft.Text(f"CSV files saved to {export_dir}!"), bgcolor=SUCCESS)
        self._page_ref.snack_bar.open = True
        self._page_ref.update()
        
        # Only open explorer on desktop
        if sys.platform == "win32":
            try:
                import subprocess
                subprocess.Popen(f'explorer "{export_dir}"')
            except Exception:
                pass

    def _clear_data(self, e):

        warning(self._page_ref)  # Warning haptic for dangerous action
        def confirm_clear(e):
            warning(self._page_ref)  # Another warning haptic on confirm
            from gmfm_app.data.database import resolve_db_path
            import os
            db_path = resolve_db_path()
            if db_path.exists():
                os.remove(db_path)
            dlg.open = False
            self._page_ref.update()
            self._page_ref.snack_bar = ft.SnackBar(ft.Text("All data cleared"), bgcolor=SUCCESS)
            self._page_ref.snack_bar.open = True
            self._page_ref.go("/")

        def cancel(e):
            dlg.open = False
            self._page_ref.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Clear All Data?"),
            content=ft.Text("This will permanently delete all students and sessions. This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Delete Everything", style=ft.ButtonStyle(color=ERROR), on_click=confirm_clear),
            ],
        )
        self._page_ref.overlay.append(dlg)
        dlg.open = True
        self._page_ref.update()
