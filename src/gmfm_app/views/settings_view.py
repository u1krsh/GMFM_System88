"""
Settings View - App Configuration
"""
import flet as ft
from gmfm_app.data.database import DatabaseContext, db_context


# Light Theme
BG = "#F8FAFC"
CARD = "#FFFFFF"
PRIMARY = "#0D9488"
TEXT1 = "#1E293B"
TEXT2 = "#64748B"
TEXT3 = "#94A3B8"
BORDER = "#E2E8F0"
SUCCESS = "#10B981"
ERROR = "#EF4444"


class SettingsView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext):
        super().__init__(route="/settings", padding=0, bgcolor=BG)
        self.page = page
        self.db_context = db_context

        # Header
        header = ft.Container(
            content=ft.Row([
                ft.IconButton("arrow_back", icon_color=TEXT1, on_click=lambda _: self.page.go("/")),
                ft.Text("Settings", size=20, weight=ft.FontWeight.BOLD, color=TEXT1),
            ]),
            padding=ft.padding.symmetric(horizontal=10, vertical=10),
            bgcolor=CARD,
            border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
        )

        # Theme Toggle
        self.dark_mode = ft.Switch(
            value=self.page.theme_mode == ft.ThemeMode.DARK,
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
                self._action_row("Clear All Data", "Delete all patients and sessions", "delete_forever", self._clear_data, danger=True),
            ]
        )

        # About
        about_card = self._settings_card(
            "About",
            [
                self._info_row("Version", "1.0.0"),
                self._info_row("GMFM Scale", "GMFM-88 / GMFM-66"),
                self._info_row("Developer", "GMFM Pro Team"),
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
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=TEXT1),
                ft.Container(height=10),
                *rows,
            ]),
            padding=20,
            bgcolor=CARD,
            border_radius=16,
            border=ft.border.all(1, BORDER),
            margin=ft.margin.only(bottom=15),
        )

    def _setting_row(self, title, subtitle, control):
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=TEXT1),
                    ft.Text(subtitle, size=12, color=TEXT3),
                ], spacing=2, expand=True),
                control,
            ]),
            padding=ft.padding.symmetric(vertical=10),
        )

    def _action_row(self, title, subtitle, icon, on_click, danger=False):
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
                    ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=color if danger else TEXT1),
                    ft.Text(subtitle, size=12, color=TEXT3),
                ], spacing=2, expand=True),
                ft.Icon("chevron_right", color=TEXT3),
            ]),
            padding=ft.padding.symmetric(vertical=10),
            on_click=on_click,
            ink=True,
        )

    def _info_row(self, label, value):
        return ft.Container(
            content=ft.Row([
                ft.Text(label, size=14, color=TEXT2, expand=True),
                ft.Text(value, size=14, weight=ft.FontWeight.W_500, color=TEXT1),
            ]),
            padding=ft.padding.symmetric(vertical=8),
        )

    def _toggle_theme(self, e):
        if self.dark_mode.value:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = "#1A1A2E"
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = "#F8FAFC"
        self.page.update()

    def _export_data(self, e):
        import json
        from pathlib import Path
        from gmfm_app.data.repositories import PatientRepository, SessionRepository
        
        patient_repo = PatientRepository(self.db_context)
        session_repo = SessionRepository(self.db_context)
        
        patients = patient_repo.list_patients(limit=1000)
        export = {"patients": [], "sessions": []}
        
        for p in patients:
            export["patients"].append({
                "id": p.id,
                "given_name": p.given_name,
                "family_name": p.family_name,
                "dob": str(p.dob) if p.dob else None,
                "identifier": p.identifier,
            })
            sessions = session_repo.list_sessions_for_patient(p.id)
            for s in sessions:
                export["sessions"].append({
                    "id": s.id,
                    "patient_id": s.patient_id,
                    "scale": s.scale,
                    "total_score": s.total_score,
                    "notes": s.notes,
                    "created_at": s.created_at.isoformat(),
                })
        
        import os
        export_path = Path(os.path.expanduser("~")) / "Documents" / "GMFM_Reports" / "gmfm_export.json"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(json.dumps(export, indent=2))
        
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Data exported to {export_path}"), bgcolor=SUCCESS)
        self.page.snack_bar.open = True
        self.page.update()

    def _export_csv(self, e):
        """Export data as CSV for Excel/Sheets."""
        import csv
        from pathlib import Path
        from gmfm_app.data.repositories import PatientRepository, SessionRepository
        
        patient_repo = PatientRepository(self.db_context)
        session_repo = SessionRepository(self.db_context)
        
        patients = patient_repo.list_patients(limit=1000)
        
        import os
        export_dir = Path(os.path.expanduser("~")) / "Documents" / "GMFM_Reports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Export patients CSV
        patients_path = export_dir / "patients.csv"
        with open(patients_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "First Name", "Last Name", "DOB", "Identifier"])
            for p in patients:
                writer.writerow([p.id, p.given_name, p.family_name, str(p.dob) if p.dob else "", p.identifier or ""])
        
        # Export sessions CSV
        sessions_path = export_dir / "sessions.csv"
        with open(sessions_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Patient ID", "Patient Name", "Scale", "Total Score", "Notes", "Date"])
            for p in patients:
                sessions = session_repo.list_sessions_for_patient(p.id)
                for s in sessions:
                    writer.writerow([
                        s.id, s.patient_id, f"{p.given_name} {p.family_name}",
                        s.scale, f"{s.total_score:.1f}%", s.notes or "",
                        s.created_at.strftime("%Y-%m-%d %H:%M")
                    ])
        
        self.page.snack_bar = ft.SnackBar(ft.Text(f"CSV files saved to Documents/GMFM_Reports!"), bgcolor=SUCCESS)
        self.page.snack_bar.open = True
        self.page.update()
        
        import subprocess
        subprocess.Popen(f'explorer "{export_dir}"')

    def _clear_data(self, e):
        def confirm_clear(e):
            from gmfm_app.data.database import resolve_db_path
            import os
            db_path = resolve_db_path()
            if db_path.exists():
                os.remove(db_path)
            dlg.open = False
            self.page.update()
            self.page.snack_bar = ft.SnackBar(ft.Text("All data cleared"), bgcolor=SUCCESS)
            self.page.snack_bar.open = True
            self.page.go("/")

        def cancel(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Clear All Data?"),
            content=ft.Text("This will permanently delete all patients and sessions. This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Delete Everything", style=ft.ButtonStyle(color=ERROR), on_click=confirm_clear),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
