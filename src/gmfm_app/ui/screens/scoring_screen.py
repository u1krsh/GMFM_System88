from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

from kivy.metrics import dp
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.button import Button
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.chip import MDChip
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar

from gmfm_app.data.models import Patient, Session
from gmfm_app.data.repositories import PatientRepository, SessionRepository
from gmfm_app.scoring.engine import calculate_gmfm_scores
from gmfm_app.scoring.items_catalog import GMFMDomain, GMFMItem, get_domains
from gmfm_app.services.chart_service import render_score_dashboard
from gmfm_app.services.report_service import generate_report
from gmfm_app.services.scoring_service import ScoringService, ScoreRequest
from gmfm_app.ui.widgets import ScoreSelector


class ScoringScreen(MDScreen):
    def __init__(self, db_context, **kwargs: Any):  # type: ignore[override]
        self.patient_repo = PatientRepository(db_context)
        self.session_repo = SessionRepository(db_context)
        self.scoring_service = ScoringService(SessionRepository(db_context))
        self.current_patient: Optional[Patient] = None
        self.current_sessions: List[Session] = []
        self.scale: str = "88"
        self.domains: List[GMFMDomain] = []
        self.raw_scores: Dict[int, int] = {}
        self._selectors: Dict[int, ScoreSelector] = {}
        self.domain_cards: Dict[str, MDCard] = {}
        self.total_items: int = 0
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    def on_kv_post(self, base_widget):  # type: ignore[override]
        self._sync_scale_chips()
        self._load_domains()
        self._update_patient_header()
        self.update_summary()

    # patient context ---------------------------------------------------
    def load_patient(self, patient_id: Optional[int]) -> None:
        if patient_id is None:
            self.current_patient = None
            self.current_sessions = []
        else:
            self.current_patient = self.patient_repo.get_patient(patient_id)
            self.current_sessions = self.session_repo.list_sessions_for_patient(patient_id)
        self.clear_scores()
        self._update_patient_header()

    # scale handling ----------------------------------------------------
    def set_scale(self, scale: str) -> None:
        normalized = "66" if scale == "66" else "88"
        if self.scale == normalized:
            return
        self.scale = normalized
        self._sync_scale_chips()
        self.clear_scores()
        self._load_domains()
        self.update_summary()

    def _sync_scale_chips(self) -> None:
        chip66 = self.ids.get("scale66_chip")
        chip88 = self.ids.get("scale88_chip")
        if chip66:
            chip66.active = self.scale == "66"
        if chip88:
            chip88.active = self.scale == "88"

    # score controls ----------------------------------------------------
    def clear_scores(self) -> None:
        self.raw_scores.clear()
        for selector in self._selectors.values():
            selector.update_state(None)
        self.update_summary()

    def _load_domains(self) -> None:
        self.domains = get_domains(self.scale)
        self._build_domain_cards()
        self._refresh_domain_filter_bar()

    def _refresh_domain_filter_bar(self) -> None:
        bar = self.ids.get("domain_filter_bar")
        if not bar:
            return
        bar.clear_widgets()
        for i, domain in enumerate(self.domains):
            chip = MDChip(
                text=f"{domain.dimension}. {domain.title.title()}",
                on_release=lambda _, dim=domain.dimension: self._scroll_to_domain(dim),
                icon_left="chevron-right",
                md_bg_color=MDApp.get_running_app().theme_cls.primary_color if i % 2 == 0 else MDApp.get_running_app().theme_cls.primary_dark,
                text_color=[1, 1, 1, 1],
            )
            bar.add_widget(chip)

    def _scroll_to_domain(self, dimension: str) -> None:
        scroll = self.ids.get("score_scroll")
        card = self.domain_cards.get(dimension)
        if scroll and card:
            scroll.scroll_to(card)

    def _build_domain_cards(self) -> None:
        container: MDBoxLayout = self.ids.get("domains_container")  # type: ignore[assignment]
        if not container:
            return
        self.total_items = sum(len(domain.items) for domain in self.domains)
        summary_label: MDLabel = self.ids.get("domain_count_label")  # type: ignore[assignment]
        if summary_label:
            summary_label.text = f"GMFM-{self.scale}: {self.total_items} items total"
        container.clear_widgets()
        self._selectors.clear()
        self.domain_cards.clear()
        for domain in self.domains:
            card = self._create_domain_card(domain)
            container.add_widget(card)
            self.domain_cards[domain.dimension] = card

    def _create_domain_card(self, domain: GMFMDomain) -> MDCard:
        card = MDCard(orientation="vertical", padding=dp(16), spacing=dp(12), size_hint_y=None, elevation=1, radius=[20, 20, 20, 20])
        card.bind(minimum_height=card.setter("height"))
        content = MDBoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        content.bind(minimum_height=lambda _, value: setattr(card, "height", value + dp(32)))
        
        # Title row
        title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(36))
        gmfm66_count = sum(1 for item in domain.items if item.gmfm66)
        title_row.add_widget(MDLabel(
            text=f"Domain {domain.dimension}: {domain.title}",
            bold=True,
            font_style="H6",
        ))
        count_chip = MDChip(
            text=f"{len(domain.items)} items",
            icon_left="format-list-numbered",
            md_bg_color=[0.2, 0.7, 0.3, 1],
            text_color=[1, 1, 1, 1],
        )
        title_row.add_widget(count_chip)
        if gmfm66_count < len(domain.items):
            chip66 = MDChip(
                text=f"{gmfm66_count} in GMFM-66",
                icon_left="star",
                md_bg_color=[0.9, 0.7, 0.1, 1],
                text_color=[0, 0, 0, 1],
            )
            title_row.add_widget(chip66)
        content.add_widget(title_row)

        # Column headers
        column_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), padding=(0, dp(8), 0, 0))
        column_row.add_widget(MDLabel(text="Item", bold=True, size_hint_x=0.5))
        column_row.add_widget(MDLabel(text="Score (0-3)", halign="center", bold=True, size_hint_x=0.5))
        content.add_widget(column_row)

        items_box = MDBoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None)
        items_box.bind(minimum_height=items_box.setter("height"))
        for item in domain.items:
            row = self._create_item_row(item)
            items_box.add_widget(row)
        content.add_widget(items_box)
        card.add_widget(content)
        return card

    def _create_item_row(self, item: GMFMItem) -> MDBoxLayout:
        row = MDBoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(52), padding=(dp(8), dp(4)))
        label_box = MDBoxLayout(orientation="vertical", spacing=dp(2), size_hint_x=0.5)
        number_label = MDLabel(
            text=f"#{item.number}",
            font_size="11sp",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(14),
        )
        label_box.add_widget(number_label)
        desc_label = MDLabel(
            text=item.description,
            halign="left",
            valign="middle",
            font_size="13sp",
        )
        desc_label.bind(texture_size=lambda inst, *_: setattr(inst, "text_size", (inst.width, None)))
        label_box.add_widget(desc_label)
        row.add_widget(label_box)
        
        # Score Selector
        selector = ScoreSelector(item_number=item.number, callback=self._on_score_change)
        selector.size_hint_x = 0.5
        row.add_widget(selector)
        self._selectors[item.number] = selector
        
        return row

    def _on_score_change(self, item_number: int, score: Optional[int]) -> None:
        if score is None:
            self.raw_scores.pop(item_number, None)
        else:
            self.raw_scores[item_number] = score
        self.update_summary()

    # summary + persistence ---------------------------------------------

    def update_summary(self, cached_result: Optional[Dict[str, Any]] = None) -> None:
        summary_label: MDLabel = self.ids.get("summary_label")  # type: ignore[assignment]
        if not summary_label:
            return
        
        scored_count = len(self.raw_scores)
        progress_pct = (scored_count / self.total_items * 100) if self.total_items > 0 else 0
        
        if cached_result is None:
            if not self.raw_scores:
                summary_label.text = f"Progress: 0/{self.total_items} items scored (0%)\n\nTap score buttons (0-3) for each test item, or NT if not tested."
                return
            cached_result = calculate_gmfm_scores(self.raw_scores, scale=self.scale)
        
        lines = [
            f"Progress: {scored_count}/{self.total_items} items ({progress_pct:.0f}%)",
            f"\nGMFM-{self.scale} Total Score: {cached_result['total_percent']:.1f}%",
            "\nDomain Scores:"
        ]
        domains = cached_result.get("domains", {})
        for domain, payload in domains.items():
            lines.append(
                f"  • {domain}: {payload['percent']:.1f}% ({payload['n_items_scored']}/{payload['n_items_total']} scored)"
            )
        summary_label.text = "\n".join(lines)

    def save_session(self, export: bool = False) -> None:
        if not self.current_patient or self.current_patient.id is None:
            Snackbar(text="Select a patient first.").open()
            return
        if not self.raw_scores:
            Snackbar(text="Enter at least one score.").open()
            return
        payload = ScoreRequest(patient_id=self.current_patient.id, scale=self.scale, raw_scores=self.raw_scores)
        session, result = self.scoring_service.score_session(payload)
        self.current_sessions.insert(0, session)
        self.update_summary(result)
        message = f"✓ Session #{session.id} saved"
        if export:
            try:
                chart_bytes = render_score_dashboard(self.current_sessions)
                pdf_path = Path("reports") / f"patient_{session.patient_id}_session_{session.id}.pdf"
                patient = self.current_patient
                generate_report(patient, session, result, pdf_path, trend_chart=chart_bytes)
                message = f"✓ PDF exported to {pdf_path.absolute()}"
                # Open the PDF
                import os
                import subprocess
                if os.name == 'nt':  # Windows
                    os.startfile(str(pdf_path.absolute()))
                else:  # macOS/Linux
                    subprocess.run(['open' if os.name == 'posix' else 'xdg-open', str(pdf_path.absolute())])
            except Exception as e:
                Snackbar(text=f"Error exporting PDF: {str(e)}", duration=4).open()
                return
        Snackbar(text=message, duration=3).open()

    # header ------------------------------------------------------------
    def _update_patient_header(self) -> None:
        name_label: MDLabel = self.ids.get("patient_name_label")  # type: ignore[assignment]
        meta_label: MDLabel = self.ids.get("patient_meta_label")  # type: ignore[assignment]
        if not name_label or not meta_label:
            return
        if not self.current_patient:
            name_label.text = "No patient selected"
            meta_label.text = "Use the dashboard to pick a patient before testing."
            return
        patient = self.current_patient
        name_label.text = f"Testing: {patient.given_name} {patient.family_name} (#{patient.id})"
        if self.current_sessions:
            latest = self.current_sessions[0]
            score = latest.total_score or 0
            meta_label.text = f"Last session: GMFM-{latest.scale} · {score:.1f}% on {latest.created_at.strftime('%Y-%m-%d')}"
        else:
            meta_label.text = "No prior sessions recorded."