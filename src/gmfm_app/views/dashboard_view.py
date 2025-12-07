"""
Dashboard - Light Mode with Stats and Settings
"""
import flet as ft
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import PatientRepository, SessionRepository


# Light Theme Colors
BG = "#F8FAFC"
CARD = "#FFFFFF"
PRIMARY = "#0D9488"
SECONDARY = "#7C3AED"
ACCENT = "#F43F5E"
TEXT1 = "#1E293B"
TEXT2 = "#64748B"
TEXT3 = "#94A3B8"
SUCCESS = "#10B981"
BORDER = "#E2E8F0"


class DashboardView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext):
        super().__init__(route="/", padding=0, bgcolor=BG)
        self.page = page
        self.db_context = db_context
        self.repo = PatientRepository(db_context)
        self.session_repo = SessionRepository(db_context)

        # Header with Search and Settings
        self.search = ft.TextField(
            hint_text="Search patients...",
            prefix_icon="search",
            border_radius=12,
            bgcolor=CARD,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            color=TEXT1,
            hint_style=ft.TextStyle(color=TEXT3),
            height=50,
            expand=True,
            on_change=self.filter_patients,
        )

        header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Text("G", size=24, weight=ft.FontWeight.BOLD, color="white"),
                        width=50, height=50,
                        bgcolor=PRIMARY,
                        border_radius=14,
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(width=12),
                    ft.Column([
                        ft.Text("GMFM Pro", size=24, weight=ft.FontWeight.BOLD, color=TEXT1),
                        ft.Text("Patient Management", size=13, color=TEXT2),
                    ], spacing=2, expand=True),
                    ft.IconButton("settings", icon_color=TEXT2, on_click=lambda _: self.page.go("/settings")),
                ]),
                ft.Container(height=15),
                self.search,
            ]),
            padding=25,
            bgcolor=CARD,
            border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
        )

        # Stats Row
        self.stat_patients = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=TEXT1)
        self.stat_sessions = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=TEXT1)
        self.stat_avg = ft.Text("0%", size=24, weight=ft.FontWeight.BOLD, color=TEXT1)
        
        stats_row = ft.Container(
            content=ft.Row([
                self._stat_card("Patients", self.stat_patients, "people", PRIMARY),
                self._stat_card("Assessments", self.stat_sessions, "assessment", SECONDARY),
                self._stat_card("Avg Score", self.stat_avg, "trending_up", SUCCESS),
            ], spacing=15),
            padding=ft.padding.symmetric(horizontal=25, vertical=15),
        )

        # Quick Actions
        actions = ft.Container(
            content=ft.Row([
                self._action("person_add", "New Patient", PRIMARY, lambda _: self.page.go("/patient")),
            ], spacing=15),
            padding=ft.padding.symmetric(horizontal=25, vertical=5),
        )

        self.patient_list = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

        self.controls = [
            header,
            stats_row,
            actions,
            ft.Container(
                content=ft.Text("Patients", size=18, weight=ft.FontWeight.BOLD, color=TEXT1),
                padding=ft.padding.only(left=25, bottom=10, top=10),
            ),
            ft.Container(content=self.patient_list, padding=ft.padding.symmetric(horizontal=25), expand=True),
        ]

        self.load_patients()

    def _stat_card(self, title, value_widget, icon, color):
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color=color, size=22),
                    width=44, height=44,
                    bgcolor=f"{color}20",
                    border_radius=12,
                    alignment=ft.alignment.center,
                ),
                ft.Container(width=12),
                ft.Column([
                    value_widget,
                    ft.Text(title, size=12, color=TEXT2),
                ], spacing=0),
            ]),
            padding=15,
            bgcolor=CARD,
            border_radius=14,
            border=ft.border.all(1, BORDER),
            expand=True,
        )

    def _action(self, icon, text, color, on_click):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color="white", size=20),
                ft.Container(width=8),
                ft.Text(text, color="white", weight=ft.FontWeight.BOLD, size=14),
            ]),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            bgcolor=color,
            border_radius=12,
            on_click=on_click,
            ink=True,
        )

    def load_patients(self):
        self.all_patients = self.repo.list_patients(limit=100)
        self._update_stats()
        self._render(self.all_patients)

    def _update_stats(self):
        patient_count = len(self.all_patients)
        self.stat_patients.value = str(patient_count)
        
        # Count all sessions and calculate average
        total_sessions = 0
        total_score = 0
        for p in self.all_patients:
            sessions = self.session_repo.list_sessions_for_patient(p.id)
            total_sessions += len(sessions)
            for s in sessions:
                total_score += s.total_score or 0
        
        self.stat_sessions.value = str(total_sessions)
        self.stat_avg.value = f"{total_score / total_sessions:.0f}%" if total_sessions > 0 else "N/A"

    def filter_patients(self, e):
        term = self.search.value.lower()
        if not term:
            self._render(self.all_patients)
        else:
            filtered = [p for p in self.all_patients if term in f"{p.given_name} {p.family_name}".lower()]
            self._render(filtered)

    def _render(self, patients):
        self.patient_list.controls.clear()
        
        if not patients:
            self.patient_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("person_search", size=60, color=TEXT3),
                        ft.Text("No patients found", size=16, color=TEXT2),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            for p in patients:
                latest = self.session_repo.get_latest_session_for_patient(p.id)
                has_session = latest is not None
                last_score = f"{latest.total_score:.0f}%" if latest else "No assessments"
                
                self.patient_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text(f"{p.given_name[0]}{p.family_name[0]}".upper(), size=16, weight=ft.FontWeight.BOLD, color="white"),
                                width=48, height=48,
                                bgcolor=PRIMARY,
                                border_radius=14,
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(width=14),
                            ft.Column([
                                ft.Text(f"{p.given_name} {p.family_name}", size=15, weight=ft.FontWeight.W_600, color=TEXT1),
                                ft.Text(f"Last: {last_score}", size=12, color=TEXT2),
                            ], expand=True, spacing=3),
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon("play_arrow", color="white", size=18),
                                    ft.Text("Continue" if has_session else "Start", color="white", size=12, weight=ft.FontWeight.BOLD),
                                ], spacing=4),
                                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                                bgcolor=SUCCESS if has_session else PRIMARY,
                                border_radius=10,
                                on_click=lambda _, pid=p.id, sid=latest.id if latest else None: self._start_scoring(pid, sid),
                            ),
                            ft.Container(width=8),
                            ft.IconButton("history", icon_color=TEXT2, tooltip="History", on_click=lambda _, pid=p.id: self.page.go(f"/history?patient_id={pid}")),
                        ]),
                        padding=14,
                        bgcolor=CARD,
                        border_radius=16,
                        border=ft.border.all(1, BORDER),
                        on_click=lambda _, pid=p.id: self.page.go(f"/history?patient_id={pid}"),
                        ink=True,
                    )
                )

    def _start_scoring(self, patient_id, session_id=None):
        if session_id:
            self.page.go(f"/scoring?patient_id={patient_id}&session_id={session_id}")
        else:
            self.page.go(f"/scoring?patient_id={patient_id}")
