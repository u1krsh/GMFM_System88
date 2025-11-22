from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.chip import MDChip
from kivymd.uix.label import MDLabel
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.screen import MDScreen

from gmfm_app.data.models import Patient, Session
from gmfm_app.data.repositories import PatientRepository, SessionRepository


@dataclass
class PatientOverview:
    patient: Patient
    latest_session: Optional[Session]
    session_count: int = 0

    @property
    def status_text(self) -> str:
        if not self.latest_session:
            return "Not tested"
        return f"Tested {self.latest_session.created_at.strftime('%Y-%m-%d')}"

    @property
    def status_icon(self) -> str:
        return "check" if self.latest_session else "alert"

    @property
    def status_color(self) -> list[float]:  # type: ignore[type-var]
        return [0.16, 0.65, 0.36, 1] if self.latest_session else [0.91, 0.36, 0.11, 1]

    @property
    def score_text(self) -> str:
        if not self.latest_session:
            return "—"
        total = self.latest_session.total_score or 0.0
        return f"{total:.1f}% (GMFM-{self.latest_session.scale})"


class DashboardScreen(MDScreen):
    def __init__(self, db_context, **kwargs: Any):  # type: ignore[override]
        self.db_context = db_context
        self.patient_repo = PatientRepository(db_context)
        self.session_repo = SessionRepository(db_context)
        self.overview_rows: List[PatientOverview] = []
        self.search_query: str = ""
        super().__init__(**kwargs)

    def on_pre_enter(self):  # type: ignore[override]
        self.refresh()
        self._update_stats()

    def refresh(self) -> None:
        patients = self.patient_repo.list_patients(limit=50)
        self.overview_rows = []
        for patient in patients:
            latest = None
            session_count = 0
            if patient.id is not None:
                latest = self.session_repo.get_latest_session_for_patient(patient.id)
                session_count = len(self.session_repo.list_sessions_for_patient(patient.id))
            self.overview_rows.append(PatientOverview(patient=patient, latest_session=latest, session_count=session_count))
        self._render_patients()
        self._update_stats()

    @property
    def greeting(self) -> str:
        hour = datetime.now().hour
        bucket = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
        return f"Good {bucket}!"

    @property
    def primary_patient_id(self) -> int | None:
        return self.overview_rows[0].patient.id if self.overview_rows else None

    # UI helpers ---------------------------------------------------------
    def _render_patients(self) -> None:
        container = self.ids.get("patient_list_container")
        if not container:
            return
        container.clear_widgets()
        if not self.overview_rows:
            empty_card = MDCard(orientation="vertical", padding=dp(32), spacing=dp(12), size_hint_y=None, height=dp(160))
            empty_card.add_widget(MDLabel(text="📋", font_style="H3", halign="center"))
            empty_card.add_widget(MDLabel(text="No patients yet", font_style="H6", halign="center", bold=True))
            empty_card.add_widget(MDLabel(text="Tap the + button above to add your first patient", halign="center", theme_text_color="Secondary"))
            container.add_widget(empty_card)
            return
        for row in self.overview_rows:
            container.add_widget(self._build_patient_card(row))

    def _build_patient_card(self, overview: PatientOverview) -> MDCard:
        card = MDCard(orientation="vertical", padding=dp(16), spacing=dp(12), size_hint_y=None, height=dp(200), elevation=1, radius=[20, 20, 20, 20])

        # Header with name and edit button
        header = MDBoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(40))
        name_box = MDBoxLayout(orientation="vertical", spacing=dp(4))
        name = f"{overview.patient.given_name} {overview.patient.family_name}"
        name_box.add_widget(MDLabel(text=name, bold=True, font_style="H6"))
        if overview.patient.identifier:
            name_box.add_widget(MDLabel(text=f"ID: {overview.patient.identifier}", theme_text_color="Secondary", font_size="12sp"))
        header.add_widget(name_box)
        edit_btn = MDIconButton(
            icon="pencil",
            on_release=lambda *_: MDApp.get_running_app().open_patient_form(overview.patient),
        )
        header.add_widget(edit_btn)
        card.add_widget(header)

        # Status chip with session count badge
        status_row = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(40))
        status_chip = MDChip(
            text=overview.status_text,
            icon_left=overview.status_icon,
            md_bg_color=overview.status_color,
            text_color=[1, 1, 1, 1],
        )
        status_row.add_widget(status_chip)
        
        # Session count badge
        if overview.session_count > 0:
            count_chip = MDChip(
                text=f"{overview.session_count} session{'s' if overview.session_count != 1 else ''}",
                icon_left="history",
                md_bg_color=[0.3, 0.5, 0.9, 0.8],
                text_color=[1, 1, 1, 1],
            )
            status_row.add_widget(count_chip)
        
        if overview.latest_session:
            score_label = MDLabel(
                text=f"Score: {overview.score_text}",
                theme_text_color="Primary",
                bold=True,
                size_hint_x=None,
                width=dp(200),
            )
            status_row.add_widget(score_label)
        card.add_widget(status_row)

        # Action buttons
        buttons = MDBoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(52))
        test_label = "Test Again" if overview.latest_session else "Start Test"
        test_icon = "reload" if overview.latest_session else "play-circle"
        buttons.add_widget(
            MDRaisedButton(
                text=test_label,
                icon=test_icon,
                on_release=lambda *_: self._open_scoring(overview.patient.id),
            )
        )
        buttons.add_widget(
            MDRaisedButton(
                text="View History",
                icon="chart-line",
                on_release=lambda *_: self._view_sessions(overview.patient.id),
            )
        )
        card.add_widget(buttons)
        return card

    def _open_scoring(self, patient_id: Optional[int]) -> None:
        if patient_id is None:
            return
        app: MDApp = MDApp.get_running_app()
        app.open_session_form(patient_id)

    def _update_stats(self) -> None:
        """Update quick stats display."""
        stats_label = self.ids.get("stats_label")
        if not stats_label:
            return
        
        total_patients = len(self.overview_rows)
        tested_patients = sum(1 for ov in self.overview_rows if ov.latest_session)
        total_sessions = sum(ov.session_count for ov in self.overview_rows)
        
        stats_label.text = f"{total_patients} patients • {tested_patients} tested • {total_sessions} total sessions"

    def _view_sessions(self, patient_id: int) -> None:
        if patient_id is None:
            return
        app: MDApp = MDApp.get_running_app()
        app.show_sessions(patient_id)

    def show_docs_placeholder(self) -> None:
        Snackbar(text="Documentation workspace coming soon.", duration=2).open()
