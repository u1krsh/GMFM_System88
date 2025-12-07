"""
Dashboard - With Recent Activity and Quick Actions
"""
import flet as ft
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import PatientRepository, SessionRepository


def get_colors(is_dark):
    if is_dark:
        return {
            "BG": "#0F172A", "CARD": "#1E293B", "BORDER": "#334155",
            "TEXT1": "#F8FAFC", "TEXT2": "#94A3B8", "TEXT3": "#64748B"
        }
    return {
        "BG": "#F8FAFC", "CARD": "#FFFFFF", "BORDER": "#E2E8F0",
        "TEXT1": "#1E293B", "TEXT2": "#64748B", "TEXT3": "#94A3B8"
    }


PRIMARY = "#0D9488"
SECONDARY = "#7C3AED"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
ERROR = "#EF4444"


class DashboardView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, is_dark: bool = False):
        c = get_colors(is_dark)
        super().__init__(route="/", padding=0, bgcolor=c["BG"])
        self.page = page
        self.db_context = db_context
        self.repo = PatientRepository(db_context)
        self.session_repo = SessionRepository(db_context)
        self.c = c

        # Header
        self.search = ft.TextField(
            hint_text="Search patients...",
            prefix_icon="search",
            border_radius=12,
            bgcolor=c["CARD"],
            border_color=c["BORDER"],
            focused_border_color=PRIMARY,
            color=c["TEXT1"],
            hint_style=ft.TextStyle(color=c["TEXT3"]),
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
                        ft.Text("GMFM Pro", size=24, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                        ft.Text("Patient Management", size=13, color=c["TEXT2"]),
                    ], spacing=2, expand=True),
                    ft.IconButton("settings", icon_color=c["TEXT2"], on_click=lambda _: self.page.go("/settings")),
                ]),
                ft.Container(height=15),
                self.search,
            ]),
            padding=25,
            bgcolor=c["CARD"],
            border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
        )

        # Stats
        self.stat_patients = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=c["TEXT1"])
        self.stat_sessions = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=c["TEXT1"])
        self.stat_avg = ft.Text("0%", size=24, weight=ft.FontWeight.BOLD, color=c["TEXT1"])
        
        stats_row = ft.Container(
            content=ft.Row([
                self._stat_card("Patients", self.stat_patients, "people", PRIMARY),
                self._stat_card("Sessions", self.stat_sessions, "assessment", SECONDARY),
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

        # Recent Activity Section
        self.recent_list = ft.Column(spacing=8)
        recent_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("history", color=c["TEXT2"], size=18),
                    ft.Text("Recent Activity", size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                ], spacing=8),
                ft.Container(height=10),
                self.recent_list,
            ]),
            padding=ft.padding.symmetric(horizontal=25, vertical=10),
        )

        # Patients Section
        self.patient_list = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

        self.controls = [
            header,
            stats_row,
            actions,
            recent_section,
            ft.Container(
                content=ft.Text("Patients", size=18, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                padding=ft.padding.only(left=25, bottom=10, top=10),
            ),
            ft.Container(content=self.patient_list, padding=ft.padding.symmetric(horizontal=25), expand=True),
        ]

        self.load_patients()
        self._load_recent_activity()

    def _load_recent_activity(self):
        """Load last 3 sessions across all patients."""
        c = self.c
        all_sessions = []
        for p in self.all_patients:
            sessions = self.session_repo.list_sessions_for_patient(p.id)
            for s in sessions:
                all_sessions.append((p, s))
        
        # Sort by date, most recent first
        all_sessions.sort(key=lambda x: x[1].created_at, reverse=True)
        
        self.recent_list.controls.clear()
        
        if not all_sessions:
            self.recent_list.controls.append(
                ft.Text("No recent activity", size=13, color=c["TEXT3"])
            )
        else:
            for p, s in all_sessions[:3]:
                color = SUCCESS if s.total_score >= 70 else WARNING if s.total_score >= 40 else ERROR
                self.recent_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text(f"{s.total_score:.0f}%", size=12, weight=ft.FontWeight.BOLD, color="white"),
                                width=42, height=42,
                                bgcolor=color,
                                border_radius=10,
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(width=10),
                            ft.Column([
                                ft.Text(f"{p.given_name} {p.family_name}", size=13, weight=ft.FontWeight.W_600, color=c["TEXT1"]),
                                ft.Text(s.created_at.strftime("%b %d, %H:%M"), size=11, color=c["TEXT3"]),
                            ], spacing=2, expand=True),
                            ft.Icon("chevron_right", color=c["TEXT3"], size=18),
                        ]),
                        padding=12,
                        bgcolor=c["CARD"],
                        border_radius=12,
                        border=ft.border.all(1, c["BORDER"]),
                        on_click=lambda _, sid=s.id: self.page.go(f"/session?session_id={sid}"),
                        ink=True,
                    )
                )

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
                ft.Column([value_widget, ft.Text(title, size=12, color=self.c["TEXT2"])], spacing=0),
            ]),
            padding=15,
            bgcolor=self.c["CARD"],
            border_radius=14,
            border=ft.border.all(1, self.c["BORDER"]),
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
        self.stat_patients.value = str(len(self.all_patients))
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
        c = self.c
        
        if not patients:
            self.patient_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("person_search", size=60, color=c["TEXT3"]),
                        ft.Text("No patients found", size=16, color=c["TEXT2"]),
                        ft.TextButton("Add New Patient", on_click=lambda _: self.page.go("/patient")),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            for p in patients:
                latest = self.session_repo.get_latest_session_for_patient(p.id)
                has_session = latest is not None
                last_score = f"{latest.total_score:.0f}%" if latest else "New"
                
                # Determine score color
                score_color = c["TEXT2"]
                if latest:
                    score_color = SUCCESS if latest.total_score >= 70 else WARNING if latest.total_score >= 40 else ERROR
                
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
                                ft.Text(f"{p.given_name} {p.family_name}", size=15, weight=ft.FontWeight.W_600, color=c["TEXT1"]),
                                ft.Row([
                                    ft.Text("Last:", size=12, color=c["TEXT2"]),
                                    ft.Text(last_score, size=12, weight=ft.FontWeight.BOLD, color=score_color),
                                ], spacing=4),
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
                            ft.IconButton("history", icon_color=c["TEXT2"], on_click=lambda _, pid=p.id: self.page.go(f"/history?patient_id={pid}")),
                        ]),
                        padding=14,
                        bgcolor=c["CARD"],
                        border_radius=16,
                        border=ft.border.all(1, c["BORDER"]),
                        on_click=lambda _, pid=p.id: self.page.go(f"/history?patient_id={pid}"),
                        ink=True,
                    )
                )

    def _start_scoring(self, patient_id, session_id=None):
        if session_id:
            # Continue existing session
            self.page.go(f"/scoring?patient_id={patient_id}&session_id={session_id}")
        else:
            # Show scale selection dialog
            self._show_scale_dialog(patient_id)

    def _show_scale_dialog(self, patient_id):
        c = self.c
        
        def select_scale(scale):
            dlg.open = False
            self.page.update()
            self.page.go(f"/scoring?patient_id={patient_id}&scale={scale}")
        
        dlg = ft.AlertDialog(
            title=ft.Text("Select Assessment Scale"),
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text("66", size=24, weight=ft.FontWeight.BOLD, color="white"),
                            width=50, height=50,
                            bgcolor=PRIMARY,
                            border_radius=12,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Text("GMFM-66", size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                            ft.Text("66 items (subset)", size=12, color=c["TEXT2"]),
                        ], expand=True),
                    ]),
                    padding=16,
                    bgcolor=c["CARD"],
                    border_radius=12,
                    border=ft.border.all(1, c["BORDER"]),
                    on_click=lambda _: select_scale("66"),
                    ink=True,
                ),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text("88", size=24, weight=ft.FontWeight.BOLD, color="white"),
                            width=50, height=50,
                            bgcolor=SUCCESS,
                            border_radius=12,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Text("GMFM-88", size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                            ft.Text("88 items (complete)", size=12, color=c["TEXT2"]),
                        ], expand=True),
                    ]),
                    padding=16,
                    bgcolor=c["CARD"],
                    border_radius=12,
                    border=ft.border.all(1, c["BORDER"]),
                    on_click=lambda _: select_scale("88"),
                    ink=True,
                ),
            ], tight=True),
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
