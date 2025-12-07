"""
Scoring View - Light Mode with Clickable Score Buttons
"""
import flet as ft
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import PatientRepository, SessionRepository
from gmfm_app.data.models import Session
from gmfm_app.scoring.items_catalog import get_domains
from gmfm_app.scoring.engine import calculate_gmfm_scores


# Light Theme
BG = "#F8FAFC"
CARD = "#FFFFFF"
PRIMARY = "#0D9488"
TEXT1 = "#1E293B"
TEXT2 = "#64748B"
TEXT3 = "#94A3B8"
BORDER = "#E2E8F0"
SUCCESS = "#10B981"

DOMAIN_COLORS = {"A": "#EF4444", "B": "#F59E0B", "C": "#10B981", "D": "#3B82F6", "E": "#8B5CF6"}


class ScoringView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, patient_id: int, session_id: int = None):
        super().__init__(route=f"/scoring?patient_id={patient_id}", padding=0, bgcolor=BG)
        self.page = page
        self.db_context = db_context
        self.patient_id = patient_id
        self.session_id = session_id
        self.patient_repo = PatientRepository(db_context)
        self.session_repo = SessionRepository(db_context)
        self.scores = {}
        self.score_buttons = {}  # Store button references for updating

        patient = self.patient_repo.get_patient(patient_id)
        name = f"{patient.given_name} {patient.family_name}" if patient else "Patient"

        # Load existing scores if continuing
        if session_id:
            existing = self.session_repo.get_session(session_id)
            if existing:
                self.scores = dict(existing.raw_scores)

        # Header
        self.score_text = ft.Text(f"{len(self.scores)} / 88", size=14, weight=ft.FontWeight.BOLD, color=PRIMARY)
        
        header = ft.Container(
            content=ft.Row([
                ft.IconButton("arrow_back", icon_color=TEXT1, on_click=lambda _: self.page.go("/")),
                ft.Column([
                    ft.Text(name, size=16, weight=ft.FontWeight.BOLD, color=TEXT1),
                    ft.Text("GMFM-88 Assessment", size=12, color=TEXT2),
                ], spacing=2, expand=True),
                ft.Container(
                    content=self.score_text,
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    bgcolor=f"{PRIMARY}20",
                    border_radius=10,
                ),
            ]),
            padding=15,
            bgcolor=CARD,
            border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
        )

        # Tabs
        self.tabs = ft.Tabs(
            selected_index=0,
            expand=True,
            indicator_color=PRIMARY,
            label_color=PRIMARY,
            unselected_label_color=TEXT2,
            divider_color=BORDER,
        )

        # Save Button
        save_btn = ft.Container(
            content=ft.ElevatedButton(
                "Save Assessment",
                icon="save",
                bgcolor=PRIMARY,
                color="white",
                height=48,
                on_click=self._save,
            ),
            padding=15,
            alignment=ft.alignment.center,
        )

        self.controls = [header, self.tabs, save_btn]
        self._load_domains()

    def _load_domains(self):
        domains = get_domains("88")
        self.tabs.tabs.clear()

        for domain in domains:
            color = DOMAIN_COLORS.get(domain.dimension, PRIMARY)
            items_list = ft.Column(spacing=8, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

            # Domain header
            items_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(domain.dimension, size=20, weight=ft.FontWeight.BOLD, color="white"),
                            width=45, height=45,
                            bgcolor=color,
                            border_radius=12,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Text(domain.title.title(), size=15, weight=ft.FontWeight.BOLD, color=TEXT1),
                            ft.Text(f"{len(domain.items)} items", size=12, color=TEXT2),
                        ], spacing=2),
                    ]),
                    padding=15,
                    margin=ft.margin.only(left=12, right=12, top=12, bottom=5),
                    bgcolor=CARD,
                    border_radius=14,
                    border=ft.border.all(2, color),
                )
            )

            for item in domain.items:
                items_list.controls.append(self._item_card(item, color))

            self.tabs.tabs.append(ft.Tab(text=domain.dimension, content=items_list))

    def _item_card(self, item, color):
        existing = self.scores.get(item.number)
        
        # Create score buttons
        buttons = []
        for val in ["0", "1", "2", "3"]:
            is_selected = str(existing) == val if existing is not None else False
            btn = ft.Container(
                content=ft.Text(val, size=16, weight=ft.FontWeight.BOLD, color="white" if is_selected else TEXT1),
                width=48, height=48,
                bgcolor=color if is_selected else CARD,
                border=ft.border.all(2, color),
                border_radius=12,
                alignment=ft.alignment.center,
                on_click=lambda e, iid=item.number, v=val: self._set_score(iid, v),
                ink=True,
                data={"item": item.number, "value": val},
            )
            buttons.append(btn)
            # Store reference
            if item.number not in self.score_buttons:
                self.score_buttons[item.number] = {}
            self.score_buttons[item.number][val] = btn
        
        # NT button
        nt_selected = existing is None or existing == "NT"
        nt_btn = ft.Container(
            content=ft.Text("NT", size=14, weight=ft.FontWeight.BOLD, color=TEXT3),
            width=48, height=48,
            bgcolor=BORDER if nt_selected else CARD,
            border=ft.border.all(1, BORDER),
            border_radius=12,
            alignment=ft.alignment.center,
            on_click=lambda e, iid=item.number: self._set_score(iid, "NT"),
            ink=True,
        )
        self.score_buttons[item.number]["NT"] = nt_btn

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Text(str(item.number), size=12, weight=ft.FontWeight.BOLD, color="white"),
                        width=28, height=28,
                        bgcolor=color,
                        border_radius=8,
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(width=10),
                    ft.Text(item.description, size=13, color=TEXT1, expand=True),
                ]),
                ft.Container(height=10),
                ft.Row([*buttons, ft.Container(width=10), nt_btn], spacing=8),
            ]),
            padding=14,
            margin=ft.margin.symmetric(horizontal=12),
            bgcolor=CARD,
            border_radius=12,
            border=ft.border.all(1, BORDER),
        )

    def _set_score(self, item_id, value):
        # Get domain color for this item
        domains = get_domains("88")
        color = PRIMARY
        for domain in domains:
            for item in domain.items:
                if item.number == item_id:
                    color = DOMAIN_COLORS.get(domain.dimension, PRIMARY)
                    break
        
        # Update scores
        if value == "NT":
            self.scores.pop(item_id, None)
        else:
            self.scores[item_id] = int(value)
        
        # Update button visuals
        if item_id in self.score_buttons:
            for v, btn in self.score_buttons[item_id].items():
                if v == "NT":
                    is_sel = value == "NT"
                    btn.bgcolor = BORDER if is_sel else CARD
                else:
                    is_sel = str(value) == v
                    btn.bgcolor = color if is_sel else CARD
                    btn.content.color = "white" if is_sel else TEXT1
                btn.update()
        
        # Update counter
        self.score_text.value = f"{len(self.scores)} / 88"
        self.score_text.update()

    def _save(self, e):
        result = calculate_gmfm_scores(self.scores, scale="88")
        total = result["total_percent"]

        session = Session(patient_id=self.patient_id, scale="88", raw_scores=self.scores, total_score=total)
        self.session_repo.create_session(session)

        self.page.snack_bar = ft.SnackBar(ft.Text(f"Saved! Total: {total:.1f}%"), bgcolor=SUCCESS)
        self.page.snack_bar.open = True
        self.page.update()
        self.page.go(f"/history?patient_id={self.patient_id}")
