"""
Session Views - Light Mode
"""
import flet as ft
from pathlib import Path
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import SessionRepository, PatientRepository
from gmfm_app.scoring.engine import calculate_gmfm_scores
from gmfm_app.services.report_service import generate_report


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

DOMAIN_COLORS = {"A": "#EF4444", "B": "#F59E0B", "C": "#10B981", "D": "#3B82F6", "E": "#8B5CF6"}
DOMAIN_NAMES = {"A": "Lying & Rolling", "B": "Sitting", "C": "Crawling & Kneeling", "D": "Standing", "E": "Walking & Running"}


class SessionHistoryView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, patient_id: int):
        super().__init__(route=f"/history?patient_id={patient_id}", padding=0, bgcolor=BG)
        self.page = page
        self.db_context = db_context
        self.patient_id = patient_id
        self.repo = SessionRepository(db_context)
        self.patient_repo = PatientRepository(db_context)

        patient = self.patient_repo.get_patient(patient_id)
        name = f"{patient.given_name} {patient.family_name}" if patient else "Patient"

        # Header
        header = ft.Container(
            content=ft.Row([
                ft.IconButton("arrow_back", icon_color=TEXT1, on_click=lambda _: self.page.go("/")),
                ft.Column([
                    ft.Text(name, size=18, weight=ft.FontWeight.BOLD, color=TEXT1),
                    ft.Text("Assessment History", size=12, color=TEXT2),
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
            bgcolor=CARD,
            border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
        )

        self.list = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

        self.controls = [header, ft.Container(content=self.list, padding=20, expand=True)]
        self._load()

    def _load(self):
        sessions = self.repo.list_sessions_for_patient(self.patient_id)
        
        if not sessions:
            self.list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("assignment", size=60, color=TEXT3),
                        ft.Text("No assessments yet", size=16, color=TEXT2),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            for s in sessions:
                color = SUCCESS if s.total_score >= 70 else "#F59E0B" if s.total_score >= 40 else ERROR
                
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
                                ft.Text(f"GMFM-{s.scale}", size=15, weight=ft.FontWeight.BOLD, color=TEXT1),
                                ft.Text(s.created_at.strftime("%b %d, %Y • %H:%M"), size=12, color=TEXT2),
                            ], expand=True, spacing=3),
                            ft.Icon("chevron_right", color=TEXT3),
                        ]),
                        padding=14,
                        bgcolor=CARD,
                        border_radius=14,
                        border=ft.border.all(1, BORDER),
                        on_click=lambda _, sid=s.id: self.page.go(f"/session?session_id={sid}"),
                        ink=True,
                    )
                )


class SessionDetailView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, session_id: int):
        super().__init__(route=f"/session?session_id={session_id}", padding=0, bgcolor=BG)
        self.page = page
        self.db_context = db_context
        self.session_id = session_id
        self.repo = SessionRepository(db_context)
        self.patient_repo = PatientRepository(db_context)

        self.session = self.repo.get_session(session_id)
        if not self.session:
            self.controls = [ft.Text("Session not found", color=TEXT1)]
            return

        self.patient = self.patient_repo.get_patient(self.session.patient_id)
        self.results = calculate_gmfm_scores(self.session.raw_scores, scale=self.session.scale)
        domains = self.results["domains"]
        total = self.results["total_percent"]

        # Header
        header = ft.Container(
            content=ft.Row([
                ft.IconButton("arrow_back", icon_color=TEXT1, on_click=lambda _: self.page.go(f"/history?patient_id={self.session.patient_id}")),
                ft.Text("Results", size=18, weight=ft.FontWeight.BOLD, color=TEXT1, expand=True),
                ft.IconButton("picture_as_pdf", icon_color=PRIMARY, on_click=self._export_pdf),
            ]),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            bgcolor=CARD,
            border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
        )

        # Score Card
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

        # Domain breakdown
        domain_cards = []
        for d_key, d_val in domains.items():
            color = DOMAIN_COLORS.get(d_key, PRIMARY)
            percent = d_val["percent"]
            
            domain_cards.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(d_key, weight=ft.FontWeight.BOLD, color="white"),
                            width=38, height=38,
                            bgcolor=color,
                            border_radius=10,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Text(DOMAIN_NAMES.get(d_key, d_key), size=13, weight=ft.FontWeight.W_600, color=TEXT1),
                            ft.ProgressBar(value=percent / 100, color=color, bgcolor=BORDER, bar_height=8),
                        ], expand=True, spacing=5),
                        ft.Text(f"{percent:.0f}%", size=16, weight=ft.FontWeight.BOLD, color=color),
                    ]),
                    padding=14,
                    bgcolor=CARD,
                    border_radius=12,
                    border=ft.border.all(1, BORDER),
                    margin=ft.margin.only(bottom=10),
                )
            )

        # Export button
        export_btn = ft.ElevatedButton("Export PDF Report", icon="picture_as_pdf", bgcolor=PRIMARY, color="white", height=48, on_click=self._export_pdf)

        self.controls = [
            header,
            ft.Container(
                content=ft.Column([score_card, ft.Container(content=ft.Column(domain_cards), padding=ft.padding.symmetric(horizontal=20)), ft.Container(content=export_btn, padding=20, alignment=ft.alignment.center)], scroll=ft.ScrollMode.ADAPTIVE),
                expand=True,
            )
        ]

    def _export_pdf(self, e):
        if not self.session or not self.patient:
            self.page.snack_bar = ft.SnackBar(ft.Text("No session data to export"), bgcolor=ERROR)
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        # Use user's Documents folder for reliability
        import os
        docs_folder = Path(os.path.expanduser("~")) / "Documents" / "GMFM_Reports"
        docs_folder.mkdir(parents=True, exist_ok=True)
        
        filename = f"GMFM_{self.patient.given_name}_{self.patient.family_name}_{self.session.created_at.strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = docs_folder / filename
        
        try:
            generate_report(
                patient=self.patient, 
                session=self.session, 
                scoring_result=self.results, 
                output_path=output_path
            )
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"PDF saved to Documents/GMFM_Reports/{filename}"),
                bgcolor=SUCCESS,
                duration=5000,
            )
            self.page.snack_bar.open = True
            self.page.update()
            
            # Open the folder
            import subprocess
            subprocess.Popen(f'explorer "{docs_folder}"')
        except Exception as ex:
            import traceback
            traceback.print_exc()
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"), bgcolor=ERROR)
            self.page.snack_bar.open = True
            self.page.update()
