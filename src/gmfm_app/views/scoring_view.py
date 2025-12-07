"""
Scoring View - With Timer, Bulk Actions, Domain Icons
"""
import flet as ft
import time
import threading
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import PatientRepository, SessionRepository
from gmfm_app.data.models import Session
from gmfm_app.scoring.items_catalog import get_domains
from gmfm_app.scoring.engine import calculate_gmfm_scores


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


class ScoringView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, patient_id: int, session_id: int = None, is_dark: bool = False, scale: str = "88"):
        c = get_colors(is_dark)
        super().__init__(route=f"/scoring?patient_id={patient_id}", padding=0, bgcolor=c["BG"])
        self.page = page
        self.db_context = db_context
        self.patient_id = patient_id
        self.session_id = session_id
        self.scale = scale  # "66" or "88"
        self.patient_repo = PatientRepository(db_context)
        self.session_repo = SessionRepository(db_context)
        self.scores = {}
        self.score_buttons = {}
        self.c = c
        self.is_dark = is_dark
        
        # Timer
        self.start_time = time.time()
        self.timer_running = True

        patient = self.patient_repo.get_patient(patient_id)
        self.patient_name = f"{patient.given_name} {patient.family_name}" if patient else "Patient"
        
        # Get total items for this scale
        domains = get_domains(self.scale)
        self.total_items = sum(len(d.items) for d in domains)

        # Load existing scores
        if session_id:
            existing = self.session_repo.get_session(session_id)
            if existing:
                self.scale = existing.scale  # Use session's scale
                self.scores = dict(existing.raw_scores)

        # Header
        self.score_text = ft.Text(f"{len(self.scores)} / {self.total_items}", size=14, weight=ft.FontWeight.BOLD, color=PRIMARY)
        self.timer_text = ft.Text("0:00", size=12, color=c["TEXT2"])
        self.progress = ft.ProgressBar(value=len(self.scores) / self.total_items if self.total_items > 0 else 0, color=PRIMARY, bgcolor=c["BORDER"], bar_height=4)
        
        header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton("arrow_back", icon_color=c["TEXT1"], on_click=self._go_back),
                    ft.Column([
                        ft.Text(self.patient_name, size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                        ft.Row([ft.Icon("timer", size=14, color=c["TEXT3"]), self.timer_text], spacing=4),
                    ], spacing=2, expand=True),
                    ft.PopupMenuButton(
                        icon="more_vert",
                        icon_color=c["TEXT2"],
                        items=[
                            ft.PopupMenuItem(text="Score all as 0", icon="exposure_zero", on_click=lambda _: self._bulk_score(0)),
                            ft.PopupMenuItem(text="Score all as 3", icon="looks_3", on_click=lambda _: self._bulk_score(3)),
                            ft.PopupMenuItem(text="Clear all scores", icon="clear_all", on_click=self._clear_all),
                            ft.PopupMenuItem(),
                            ft.PopupMenuItem(text="Copy summary", icon="content_copy", on_click=self._copy_summary),
                        ],
                    ),
                    ft.Container(
                        content=ft.Row([ft.Icon("skip_next", color=PRIMARY, size=18), ft.Text("Jump", size=12, weight=ft.FontWeight.BOLD, color=PRIMARY)], spacing=4),
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        bgcolor=f"{PRIMARY}20",
                        border_radius=8,
                        on_click=self._jump_to_unscored,
                    ),
                    ft.Container(width=8),
                    self.score_text,
                ]),
                self.progress,
            ], spacing=10),
            padding=15,
            bgcolor=c["CARD"],
            border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
        )

        # Notes
        self.notes_field = ft.TextField(
            hint_text="Add notes...",
            multiline=True,
            min_lines=1,
            max_lines=3,
            border_radius=12,
            bgcolor=c["CARD"],
            border_color=c["BORDER"],
            focused_border_color=PRIMARY,
            color=c["TEXT1"],
            hint_style=ft.TextStyle(color=c["TEXT3"]),
        )

        # Tabs
        self.tabs = ft.Tabs(
            selected_index=0,
            expand=True,
            indicator_color=PRIMARY,
            label_color=c["TEXT1"],
            unselected_label_color=c["TEXT3"],
            divider_color=c["BORDER"],
        )

        # Bottom
        bottom = ft.Container(
            content=ft.Row([
                ft.Container(content=self.notes_field, expand=True),
                ft.Container(width=10),
                ft.ElevatedButton("Save", icon="save", bgcolor=PRIMARY, color="white", height=50, on_click=self._save),
            ]),
            padding=15,
            bgcolor=c["CARD"],
        )

        self.controls = [header, self.tabs, bottom]
        self._load_domains()
        self._start_timer()

    def _go_back(self, e):
        self.timer_running = False
        self.page.go("/")

    def _start_timer(self):
        def update_timer():
            while self.timer_running:
                elapsed = int(time.time() - self.start_time)
                mins, secs = divmod(elapsed, 60)
                try:
                    self.timer_text.value = f"{mins}:{secs:02d}"
                    self.timer_text.update()
                except:
                    break
                time.sleep(1)
        thread = threading.Thread(target=update_timer, daemon=True)
        thread.start()

    def _bulk_score(self, value):
        domains = get_domains("88")
        for domain in domains:
            for item in domain.items:
                self.scores[item.number] = value
                if item.number in self.score_buttons:
                    color = DOMAIN_COLORS.get(domain.dimension, PRIMARY)
                    for v, btn in self.score_buttons[item.number].items():
                        if v == "NT":
                            btn.bgcolor = self.c["CARD"]
                        else:
                            is_sel = str(value) == v
                            btn.bgcolor = color if is_sel else self.c["CARD"]
                            btn.content.color = "white" if is_sel else self.c["TEXT1"]
        self._update_progress()
        self.page.snack_bar = ft.SnackBar(ft.Text(f"All items scored as {value}"), bgcolor=SUCCESS)
        self.page.snack_bar.open = True
        self.page.update()

    def _clear_all(self, e):
        self.scores.clear()
        for item_id, buttons in self.score_buttons.items():
            for v, btn in buttons.items():
                if v == "NT":
                    btn.bgcolor = self.c["BORDER"]
                else:
                    btn.bgcolor = self.c["CARD"]
                    btn.content.color = self.c["TEXT1"]
        self._update_progress()
        self.page.snack_bar = ft.SnackBar(ft.Text("All scores cleared"), bgcolor=WARNING)
        self.page.snack_bar.open = True
        self.page.update()

    def _copy_summary(self, e):
        result = calculate_gmfm_scores(self.scores, scale=self.scale)
        summary = f"GMFM-{self.scale} Assessment - {self.patient_name}\n"
        summary += f"Total: {result['total_percent']:.1f}%\n"
        summary += f"Items scored: {len(self.scores)}/{self.total_items}\n\n"
        for d, vals in result["domains"].items():
            summary += f"{DOMAIN_NAMES.get(d, d)}: {vals['percent']:.1f}%\n"
        self.page.set_clipboard(summary)
        self.page.snack_bar = ft.SnackBar(ft.Text("Summary copied to clipboard!"), bgcolor=SUCCESS)
        self.page.snack_bar.open = True
        self.page.update()

    def _jump_to_unscored(self, e):
        domains = get_domains(self.scale)
        for i, domain in enumerate(domains):
            for item in domain.items:
                if item.number not in self.scores:
                    self.tabs.selected_index = i
                    self.tabs.update()
                    self.page.snack_bar = ft.SnackBar(ft.Text(f"Jumped to item {item.number}"), bgcolor=PRIMARY)
                    self.page.snack_bar.open = True
                    self.page.update()
                    return
        # All scored - celebration!
        self._show_celebration()

    def _show_celebration(self):
        self.page.snack_bar = ft.SnackBar(
            ft.Row([
                ft.Icon("celebration", color="white"),
                ft.Text(f"All {self.total_items} items scored! 🎉", weight=ft.FontWeight.BOLD, color="white"),
            ], spacing=10),
            bgcolor=SUCCESS,
            duration=3000,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _update_progress(self):
        self.score_text.value = f"{len(self.scores)} / {self.total_items}"
        self.progress.value = len(self.scores) / self.total_items if self.total_items > 0 else 0
        self.score_text.update()
        self.progress.update()
        
        # Check if all scored
        if len(self.scores) == self.total_items:
            self._show_celebration()

    def _load_domains(self):
        domains = get_domains(self.scale)
        c = self.c
        self.tabs.tabs.clear()

        for domain in domains:
            color = DOMAIN_COLORS.get(domain.dimension, PRIMARY)
            icon = DOMAIN_ICONS.get(domain.dimension, "category")
            scored = sum(1 for item in domain.items if item.number in self.scores)
            
            items_list = ft.Column(spacing=8, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

            # Domain header with icon
            items_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(icon, size=24, color="white"),
                            width=50, height=50,
                            bgcolor=color,
                            border_radius=14,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Text(DOMAIN_NAMES.get(domain.dimension, domain.title), size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                            ft.Text(f"{scored}/{len(domain.items)} items scored", size=12, color=c["TEXT2"]),
                        ], spacing=2, expand=True),
                        ft.Container(
                            content=ft.Text(f"{int(scored/len(domain.items)*100)}%", size=16, weight=ft.FontWeight.BOLD, color=color),
                            padding=ft.padding.symmetric(horizontal=12, vertical=6),
                            bgcolor=f"{color}20",
                            border_radius=10,
                        ),
                    ]),
                    padding=16,
                    margin=ft.margin.only(left=12, right=12, top=12, bottom=8),
                    bgcolor=c["CARD"],
                    border_radius=16,
                    border=ft.border.all(2, color),
                )
            )

            for item in domain.items:
                items_list.controls.append(self._item_card(item, color))

            self.tabs.tabs.append(ft.Tab(text=f"{domain.dimension}", content=items_list))

    def _item_card(self, item, color):
        c = self.c
        existing = self.scores.get(item.number)
        
        buttons = []
        for val in ["0", "1", "2", "3"]:
            is_selected = str(existing) == val if existing is not None else False
            btn = ft.Container(
                content=ft.Text(val, size=16, weight=ft.FontWeight.BOLD, color="white" if is_selected else c["TEXT1"]),
                width=48, height=48,
                bgcolor=color if is_selected else c["CARD"],
                border=ft.border.all(2, color),
                border_radius=12,
                alignment=ft.alignment.center,
                on_click=lambda e, iid=item.number, v=val, clr=color: self._set_score(iid, v, clr),
                ink=True,
            )
            buttons.append(btn)
            if item.number not in self.score_buttons:
                self.score_buttons[item.number] = {}
            self.score_buttons[item.number][val] = btn
        
        nt_btn = ft.Container(
            content=ft.Text("NT", size=14, weight=ft.FontWeight.BOLD, color=c["TEXT3"]),
            width=48, height=48,
            bgcolor=c["BORDER"] if existing is None else c["CARD"],
            border=ft.border.all(1, c["BORDER"]),
            border_radius=12,
            alignment=ft.alignment.center,
            on_click=lambda e, iid=item.number: self._set_score(iid, "NT", color),
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
                    ft.Text(item.description, size=13, color=c["TEXT1"], expand=True),
                ]),
                ft.Container(height=10),
                ft.Row([*buttons, ft.Container(width=10), nt_btn], spacing=8),
            ]),
            padding=14,
            margin=ft.margin.symmetric(horizontal=12),
            bgcolor=c["CARD"],
            border_radius=12,
            border=ft.border.all(1, c["BORDER"]),
        )

    def _set_score(self, item_id, value, color):
        c = self.c
        
        if value == "NT":
            self.scores.pop(item_id, None)
        else:
            self.scores[item_id] = int(value)
        
        if item_id in self.score_buttons:
            for v, btn in self.score_buttons[item_id].items():
                if v == "NT":
                    is_sel = value == "NT"
                    btn.bgcolor = c["BORDER"] if is_sel else c["CARD"]
                else:
                    is_sel = str(value) == v
                    btn.bgcolor = color if is_sel else c["CARD"]
                    btn.content.color = "white" if is_sel else c["TEXT1"]
                btn.update()
        
        self._update_progress()

    def _save(self, e):
        self.timer_running = False
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        
        result = calculate_gmfm_scores(self.scores, scale=self.scale)
        total = result["total_percent"]

        notes = self.notes_field.value or ""
        if elapsed > 0:
            notes = f"[Duration: {mins}m {secs}s] {notes}"

        session = Session(
            patient_id=self.patient_id,
            scale=self.scale,
            raw_scores=self.scores,
            total_score=total,
            notes=notes.strip() if notes.strip() else None
        )
        self.session_repo.create_session(session)

        self.page.snack_bar = ft.SnackBar(ft.Text(f"Saved! Total: {total:.1f}% ({mins}:{secs:02d})"), bgcolor=SUCCESS)
        self.page.snack_bar.open = True
        self.page.update()
        self.page.go(f"/history?patient_id={self.patient_id}")
