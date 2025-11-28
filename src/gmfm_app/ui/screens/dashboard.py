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
            return
        
        total_patients = len(self.overview_rows)
        tested_patients = sum(1 for ov in self.overview_rows if ov.latest_session)
        total_sessions = sum(ov.session_count for ov in self.overview_rows)
        
        
        stats_label = self.ids.get("stats_label")
        if stats_label:
            stats_label.text = f"{total_patients} patients • {tested_patients} tested • {total_sessions} total sessions"

        for row in self.overview_rows:
            container.add_widget(self._build_patient_card(row))

    def _build_patient_card(self, overview: PatientOverview) -> MDCard:
        card = MDCard(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(12),
            size_hint_y=None,
            height=dp(180),
            elevation=1,
            radius=[24, 24, 24, 24],
            ripple_behavior=True,
            on_release=lambda *_: self._view_sessions(overview.patient.id),
        )

        # Top Row: Avatar + Name + Edit
        top_row = MDBoxLayout(orientation="horizontal", spacing=dp(16), size_hint_y=None, height=dp(50))
        
        # Avatar (Circle with initials)
        initials = f"{overview.patient.given_name[0]}{overview.patient.family_name[0]}".upper()
        avatar = MDCard(
            size_hint=(None, None), size=(dp(48), dp(48)),
            radius=[24, 24, 24, 24],
            md_bg_color=MDApp.get_running_app().theme_cls.primary_color,
            elevation=0
        )
        avatar.add_widget(MDLabel(
            text=initials, 
            halign="center", 
            theme_text_color="Custom", 
            text_color=(1, 1, 1, 1),
            bold=True,
            font_style="H6"
        ))
        top_row.add_widget(avatar)

        # Name and ID
        name_box = MDBoxLayout(orientation="vertical", spacing=dp(2))
        name_box.add_widget(MDLabel(
            text=f"{overview.patient.given_name} {overview.patient.family_name}",
            bold=True,
            font_style="Subtitle1",
            theme_text_color="Primary"
        ))
        if overview.patient.identifier:
            name_box.add_widget(MDLabel(
                text=f"ID: {overview.patient.identifier}",
                theme_text_color="Secondary",
                font_style="Caption"
            ))
        top_row.add_widget(name_box)

        # Edit Button
        edit_btn = MDIconButton(
            icon="pencil-outline",
            theme_text_color="Secondary",
            on_release=lambda *_: MDApp.get_running_app().open_patient_form(overview.patient),
        )
        top_row.add_widget(edit_btn)
        card.add_widget(top_row)

        # Status Row
        status_row = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(32))
        
        # Status Badge
        status_color = overview.status_color
        status_text = "Tested" if overview.latest_session else "New"
        status_badge = MDCard(
            size_hint=(None, None), height=dp(28), width=dp(80),
            radius=[14, 14, 14, 14],
            md_bg_color=[c * 0.2 for c in status_color[:3]] + [1], # Light tint
            elevation=0,
            padding=(dp(8), dp(4))
        )
        status_badge.add_widget(MDLabel(
            text=status_text,
            halign="center",
            theme_text_color="Custom",
            text_color=status_color,
            bold=True,
            font_style="Caption"
        ))
        status_row.add_widget(status_badge)

        # Score Badge (if exists)
        if overview.latest_session:
            score_text = f"{overview.latest_session.total_score:.0f}%"
            score_badge = MDCard(
                size_hint=(None, None), height=dp(28), width=dp(60),
                radius=[14, 14, 14, 14],
                md_bg_color=MDApp.get_running_app().theme_cls.accent_color,
                elevation=0,
                padding=(dp(8), dp(4))
            )
            score_badge.add_widget(MDLabel(
                text=score_text,
                halign="center",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                bold=True,
                font_style="Caption"
            ))
            status_row.add_widget(score_badge)
            
            # Date
            date_label = MDLabel(
                text=overview.latest_session.created_at.strftime("%b %d"),
                theme_text_color="Secondary",
                font_style="Caption",
                halign="right"
            )
            status_row.add_widget(date_label)

        card.add_widget(status_row)

        actions_box = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(40))
        actions_box.add_widget(MDLabel(text="")) # Spacer
        
        test_btn = MDRaisedButton(
            text="Test",
            icon="play",
            elevation=0,
            md_bg_color=MDApp.get_running_app().theme_cls.primary_color,
            on_release=lambda *_: self._open_scoring(overview.patient.id)
        )
        actions_box.add_widget(test_btn)
        card.add_widget(actions_box)

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
