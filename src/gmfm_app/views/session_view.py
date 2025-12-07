"""
Session Views - With Domain Icons and Delete Feature
"""
import flet as ft
from pathlib import Path
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import SessionRepository, PatientRepository
from gmfm_app.scoring.engine import calculate_gmfm_scores
from gmfm_app.services.report_service import generate_report


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
SUCCESS = "#10B981"
WARNING = "#F59E0B"
ERROR = "#EF4444"
DOMAIN_COLORS = {"A": "#EF4444", "B": "#F59E0B", "C": "#10B981", "D": "#3B82F6", "E": "#8B5CF6"}
DOMAIN_ICONS = {"A": "hotel", "B": "weekend", "C": "child_care", "D": "accessibility_new", "E": "directions_run"}
DOMAIN_NAMES = {"A": "Lying & Rolling", "B": "Sitting", "C": "Crawling & Kneeling", "D": "Standing", "E": "Walking & Running"}


class SessionHistoryView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, patient_id: int, is_dark: bool = False):
        c = get_colors(is_dark)
        super().__init__(route=f"/history?patient_id={patient_id}", padding=0, bgcolor=c["BG"])
        self.page = page
        self.db_context = db_context
        self.patient_id = patient_id
        self.repo = SessionRepository(db_context)
        self.patient_repo = PatientRepository(db_context)
        self.c = c

        patient = self.patient_repo.get_patient(patient_id)
        name = f"{patient.given_name} {patient.family_name}" if patient else "Patient"

        header = ft.Container(
            content=ft.Row([
                ft.IconButton("arrow_back", icon_color=c["TEXT1"], on_click=lambda _: self.page.go("/")),
                ft.Column([
                    ft.Text(name, size=18, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                    ft.Text("Assessment History", size=12, color=c["TEXT2"]),
                ], spacing=2, expand=True),
                ft.Container(
                    content=ft.Row([ft.Icon("add", color="white", size=18), ft.Text("New", color="white", weight=ft.FontWeight.BOLD, size=13)], spacing=4),
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    bgcolor=PRIMARY,
                    border_radius=10,
                    on_click=lambda _: self.page.go(f"/scoring?patient_id={patient_id}"),
                ),
            ]),
            padding=15,
            bgcolor=c["CARD"],
            border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
        )

        self.list = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        self.controls = [header, ft.Container(content=self.list, padding=20, expand=True)]
        self._load()

    def _load(self):
        c = self.c
        sessions = self.repo.list_sessions_for_patient(self.patient_id)
        
        if not sessions:
            self.list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("assignment", size=60, color=c["TEXT3"]),
                        ft.Text("No assessments yet", size=16, color=c["TEXT2"]),
                        ft.TextButton("Start First Assessment", on_click=lambda _: self.page.go(f"/scoring?patient_id={self.patient_id}")),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            if len(sessions) >= 2:
                self.list.controls.append(self._build_progress_chart(sessions))
            
            for s in sessions:
                color = SUCCESS if s.total_score >= 70 else WARNING if s.total_score >= 40 else ERROR
                
                self.list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text(f"{s.total_score:.0f}%", size=16, weight=ft.FontWeight.BOLD, color="white"),
                                width=55, height=55,
                                bgcolor=color,
                                border_radius=14,
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(width=14),
                            ft.Column([
                                ft.Text(f"GMFM-{s.scale}", size=15, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                                ft.Text(s.created_at.strftime("%b %d, %Y • %H:%M"), size=12, color=c["TEXT2"]),
                                ft.Text(s.notes[:40] + "..." if s.notes and len(s.notes) > 40 else s.notes or "", size=11, color=c["TEXT3"]) if s.notes else ft.Container(),
                            ], expand=True, spacing=3),
                            ft.IconButton("delete_outline", icon_color=c["TEXT3"], tooltip="Delete", on_click=lambda _, sid=s.id: self._confirm_delete(sid)),
                            ft.Icon("chevron_right", color=c["TEXT3"]),
                        ]),
                        padding=14,
                        bgcolor=c["CARD"],
                        border_radius=14,
                        border=ft.border.all(1, c["BORDER"]),
                        on_click=lambda _, sid=s.id: self.page.go(f"/session?session_id={sid}"),
                        ink=True,
                    )
                )

    def _confirm_delete(self, session_id):
        def do_delete(e):
            self.repo.delete_session(session_id)
            dlg.open = False
            self.page.update()
            self.page.go(f"/history?patient_id={self.patient_id}")
        
        def cancel(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Delete Assessment?"),
            content=ft.Text("This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Delete", style=ft.ButtonStyle(color=ERROR), on_click=do_delete),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _build_progress_chart(self, sessions):
        c = self.c
        sorted_sessions = sorted(sessions, key=lambda s: s.created_at)
        
        bars = []
        for i, s in enumerate(sorted_sessions[-8:]):
            height = max(4, (s.total_score / 100) * 80)
            is_latest = i == len(sorted_sessions[-8:]) - 1
            color = PRIMARY if is_latest else f"{PRIMARY}60"
            
            bars.append(
                ft.Container(
                    content=ft.Column([
                        ft.Container(height=80 - height),
                        ft.Container(width=28, height=height, bgcolor=color, border_radius=ft.border_radius.only(top_left=6, top_right=6)),
                        ft.Text(s.created_at.strftime("%d"), size=10, color=c["TEXT3"]),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                )
            )
        
        if len(sorted_sessions) >= 2:
            diff = sorted_sessions[-1].total_score - sorted_sessions[0].total_score
            trend_icon = "trending_up" if diff > 0 else "trending_down" if diff < 0 else "trending_flat"
            trend_color = SUCCESS if diff > 0 else ERROR if diff < 0 else c["TEXT2"]
            trend_text = f"+{diff:.0f}%" if diff > 0 else f"{diff:.0f}%"
        else:
            trend_icon, trend_color, trend_text = "trending_flat", c["TEXT2"], "0%"

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Progress", size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Row([ft.Icon(trend_icon, color=trend_color, size=18), ft.Text(trend_text, size=14, weight=ft.FontWeight.BOLD, color=trend_color)], spacing=4),
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        bgcolor=f"{trend_color}20",
                        border_radius=8,
                    ),
                ]),
                ft.Container(height=10),
                ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_AROUND),
            ]),
            padding=20,
            bgcolor=c["CARD"],
            border_radius=16,
            border=ft.border.all(1, c["BORDER"]),
            margin=ft.margin.only(bottom=15),
        )


class SessionDetailView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, session_id: int, is_dark: bool = False):
        c = get_colors(is_dark)
        super().__init__(route=f"/session?session_id={session_id}", padding=0, bgcolor=c["BG"])
        self.page = page
        self.db_context = db_context
        self.session_id = session_id
        self.repo = SessionRepository(db_context)
        self.patient_repo = PatientRepository(db_context)
        self.c = c

        self.session = self.repo.get_session(session_id)
        if not self.session:
            self.controls = [ft.Text("Session not found", color=c["TEXT1"])]
            return

        self.patient = self.patient_repo.get_patient(self.session.patient_id)
        self.results = calculate_gmfm_scores(self.session.raw_scores, scale=self.session.scale)
        domains = self.results["domains"]
        total = self.results["total_percent"]

        header = ft.Container(
            content=ft.Row([
                ft.IconButton("arrow_back", icon_color=c["TEXT1"], on_click=lambda _: self.page.go(f"/history?patient_id={self.session.patient_id}")),
                ft.Text("Results", size=18, weight=ft.FontWeight.BOLD, color=c["TEXT1"], expand=True),
                ft.IconButton("compare_arrows", icon_color=c["TEXT2"], tooltip="Compare", on_click=lambda _: self._show_compare()),
                ft.IconButton("picture_as_pdf", icon_color=PRIMARY, on_click=self._export_pdf),
            ]),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            bgcolor=c["CARD"],
            border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
        )

        score_card = ft.Container(
            content=ft.Column([
                ft.Text(f"{total:.0f}%", size=48, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("Total Score", size=14, color="white"),
                ft.Text(f"GMFM-{self.session.scale} • {self.session.created_at.strftime('%b %d, %Y')}", size=12, color="white"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30,
            bgcolor=PRIMARY,
            border_radius=18,
            margin=20,
            alignment=ft.alignment.center,
        )

        # Notes
        notes_card = None
        if self.session.notes:
            notes_card = ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon("notes", color=c["TEXT2"], size=18), ft.Text("Notes", size=14, weight=ft.FontWeight.BOLD, color=c["TEXT1"])], spacing=8),
                    ft.Container(height=8),
                    ft.Text(self.session.notes, size=13, color=c["TEXT2"]),
                ]),
                padding=16,
                bgcolor=c["CARD"],
                border_radius=14,
                border=ft.border.all(1, c["BORDER"]),
                margin=ft.margin.symmetric(horizontal=20),
            )

        # Domain cards with icons
        domain_cards = []
        for d_key, d_val in domains.items():
            color = DOMAIN_COLORS.get(d_key, PRIMARY)
            icon = DOMAIN_ICONS.get(d_key, "category")
            percent = d_val["percent"]
            
            domain_cards.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(content=ft.Icon(icon, color="white", size=20), width=42, height=42, bgcolor=color, border_radius=12, alignment=ft.alignment.center),
                        ft.Container(width=12),
                        ft.Column([ft.Text(DOMAIN_NAMES.get(d_key, d_key), size=13, weight=ft.FontWeight.W_600, color=c["TEXT1"]), ft.ProgressBar(value=percent / 100, color=color, bgcolor=c["BORDER"], bar_height=8)], expand=True, spacing=5),
                        ft.Text(f"{percent:.0f}%", size=16, weight=ft.FontWeight.BOLD, color=color),
                    ]),
                    padding=14,
                    bgcolor=c["CARD"],
                    border_radius=12,
                    border=ft.border.all(1, c["BORDER"]),
                    margin=ft.margin.only(bottom=10),
                )
            )

        export_btn = ft.ElevatedButton("Export PDF", icon="picture_as_pdf", bgcolor=PRIMARY, color="white", height=48, on_click=self._export_pdf)

        content_list = [score_card]
        if notes_card:
            content_list.append(notes_card)
            content_list.append(ft.Container(height=15))
        content_list.append(ft.Container(content=ft.Column(domain_cards), padding=ft.padding.symmetric(horizontal=20)))
        content_list.append(ft.Container(content=export_btn, padding=20, alignment=ft.alignment.center))

        self.controls = [header, ft.Container(content=ft.Column(content_list, scroll=ft.ScrollMode.ADAPTIVE), expand=True)]

    def _show_compare(self):
        sessions = self.repo.list_sessions_for_patient(self.session.patient_id)
        other_sessions = [s for s in sessions if s.id != self.session_id]
        
        if not other_sessions:
            self.page.snack_bar = ft.SnackBar(ft.Text("No other sessions to compare"), bgcolor=self.c["TEXT2"])
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        def select_session(e, sid):
            dlg.open = False
            self.page.update()
            self.page.go(f"/compare?session1={self.session_id}&session2={sid}")
        
        options = [ft.ListTile(title=ft.Text(f"GMFM-{s.scale} - {s.total_score:.0f}%"), subtitle=ft.Text(s.created_at.strftime("%b %d, %Y")), on_click=lambda e, sid=s.id: select_session(e, sid)) for s in other_sessions[:5]]
        
        dlg = ft.AlertDialog(title=ft.Text("Compare with..."), content=ft.Column(options, tight=True))
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _export_pdf(self, e):
        if not self.session or not self.patient:
            return
        import os
        docs_folder = Path(os.path.expanduser("~")) / "Documents" / "GMFM_Reports"
        docs_folder.mkdir(parents=True, exist_ok=True)
        filename = f"GMFM_{self.patient.given_name}_{self.patient.family_name}_{self.session.created_at.strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = docs_folder / filename
        try:
            generate_report(patient=self.patient, session=self.session, scoring_result=self.results, output_path=output_path)
            self.page.snack_bar = ft.SnackBar(ft.Text(f"PDF saved!"), bgcolor=SUCCESS, duration=5000)
            self.page.snack_bar.open = True
            self.page.update()
            import subprocess
            subprocess.Popen(f'explorer "{docs_folder}"')
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"), bgcolor=ERROR)
            self.page.snack_bar.open = True
            self.page.update()


class CompareView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, session1_id: int, session2_id: int, is_dark: bool = False):
        c = get_colors(is_dark)
        super().__init__(route=f"/compare?session1={session1_id}&session2={session2_id}", padding=0, bgcolor=c["BG"])
        self.page = page
        self.c = c
        repo = SessionRepository(db_context)
        
        s1 = repo.get_session(session1_id)
        s2 = repo.get_session(session2_id)
        
        if not s1 or not s2:
            self.controls = [ft.Text("Sessions not found")]
            return
        
        r1 = calculate_gmfm_scores(s1.raw_scores, scale=s1.scale)
        r2 = calculate_gmfm_scores(s2.raw_scores, scale=s2.scale)
        
        header = ft.Container(
            content=ft.Row([
                ft.IconButton("arrow_back", icon_color=c["TEXT1"], on_click=lambda _: self.page.go(f"/session?session_id={session1_id}")),
                ft.Text("Comparison", size=18, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
            ]),
            padding=15,
            bgcolor=c["CARD"],
            border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
        )
        
        diff = r1["total_percent"] - r2["total_percent"]
        diff_color = SUCCESS if diff > 0 else ERROR if diff < 0 else c["TEXT2"]
        
        score_row = ft.Container(
            content=ft.Row([
                self._score_card(s1, r1, "Current", c),
                ft.Container(content=ft.Column([ft.Icon("compare_arrows", color=c["TEXT3"], size=24), ft.Text(f"{'+' if diff > 0 else ''}{diff:.0f}%", size=18, weight=ft.FontWeight.BOLD, color=diff_color)], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=10),
                self._score_card(s2, r2, "Previous", c),
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
            padding=20,
        )
        
        domain_rows = []
        for d_key in ["A", "B", "C", "D", "E"]:
            p1 = r1["domains"].get(d_key, {}).get("percent", 0)
            p2 = r2["domains"].get(d_key, {}).get("percent", 0)
            d_diff = p1 - p2
            d_color = SUCCESS if d_diff > 0 else ERROR if d_diff < 0 else c["TEXT2"]
            icon = DOMAIN_ICONS.get(d_key, "category")
            
            domain_rows.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(content=ft.Icon(icon, color="white", size=18), width=38, height=38, bgcolor=DOMAIN_COLORS.get(d_key), border_radius=10, alignment=ft.alignment.center),
                        ft.Container(width=12),
                        ft.Text(DOMAIN_NAMES.get(d_key, d_key), size=13, color=c["TEXT1"], expand=True),
                        ft.Text(f"{p1:.0f}%", size=14, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                        ft.Container(content=ft.Text(f"{'+' if d_diff > 0 else ''}{d_diff:.0f}", size=12, weight=ft.FontWeight.BOLD, color=d_color), padding=ft.padding.symmetric(horizontal=8, vertical=4), bgcolor=f"{d_color}20", border_radius=6, width=50, alignment=ft.alignment.center),
                        ft.Text(f"{p2:.0f}%", size=14, color=c["TEXT2"]),
                    ]),
                    padding=14,
                    bgcolor=c["CARD"],
                    border_radius=12,
                    border=ft.border.all(1, c["BORDER"]),
                    margin=ft.margin.only(bottom=8),
                )
            )
        
        self.controls = [header, ft.Container(content=ft.Column([score_row, ft.Container(content=ft.Column(domain_rows), padding=ft.padding.symmetric(horizontal=20))], scroll=ft.ScrollMode.ADAPTIVE), expand=True)]
    
    def _score_card(self, session, result, label, c):
        return ft.Container(
            content=ft.Column([
                ft.Text(f"{result['total_percent']:.0f}%", size=32, weight=ft.FontWeight.BOLD, color=PRIMARY),
                ft.Text(label, size=12, color=c["TEXT2"]),
                ft.Text(session.created_at.strftime("%b %d"), size=11, color=c["TEXT3"]),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            bgcolor=c["CARD"],
            border_radius=16,
            border=ft.border.all(1, c["BORDER"]),
            width=120,
        )
