from __future__ import annotations

from pathlib import Path
from typing import Any, List

from kivymd.uix.screen import MDScreen

from gmfm_app.data.models import Session
from gmfm_app.data.repositories import SessionRepository, PatientRepository
from gmfm_app.services.chart_service import render_score_dashboard
from gmfm_app.services.report_service import generate_report
from gmfm_app.scoring.engine import calculate_gmfm66, calculate_gmfm88


class SessionDetailScreen(MDScreen):
    def __init__(self, db_context, **kwargs: Any):  # type: ignore[override]
        super().__init__(**kwargs)
        self.repo = SessionRepository(db_context)
        self.patient_repo = PatientRepository(db_context)
        self.patient_id: int | None = None
        self.sessions: List[Session] = []

    def load_sessions(self, patient_id: int) -> None:
        self.patient_id = patient_id
        self.sessions = self.repo.list_sessions_for_patient(patient_id)
        text_widget = self.ids.get("session_list")
        if not self.sessions:
            text_widget.text = "No sessions yet."
            self._update_chart(None)
            return
        lines = []
        for sess in self.sessions:
            lines.append(f"#{sess.id} GMFM-{sess.scale} -> {sess.total_score}%")
        text_widget.text = "\n".join(lines)
        self._update_chart(self.sessions)

    def _update_chart(self, sessions: List[Session] | None):
        image_widget = self.ids.get("trend_image")
        if not sessions:
            if image_widget:
                image_widget.source = ""
            return
        chart_bytes = render_score_dashboard(sessions)
        if not chart_bytes:
            return
        output_path = Path("exports") / f"patient_{self.patient_id}_trend.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(chart_bytes)
        if image_widget:
            image_widget.source = str(output_path)
            image_widget.reload()

    def export_latest_report(self) -> None:
        if not self.sessions or self.patient_id is None:
            self._set_status("No sessions to export")
            return
        session = self.sessions[0]
        patient = self.patient_repo.get_patient(self.patient_id)
        if not patient:
            self._set_status("Patient missing")
            return
        chart_bytes = render_score_dashboard(self.sessions)
        scoring_result = (
            calculate_gmfm66(session.raw_scores)
            if session.scale == "66"
            else calculate_gmfm88(session.raw_scores)
        )
        output_path = Path("reports") / f"patient_{patient.id}_session_{session.id}.pdf"
        generate_report(patient, session, scoring_result, output_path, trend_chart=chart_bytes)
        self._set_status(f"Report saved to {output_path}")

    def _set_status(self, message: str) -> None:
        status_label = self.ids.get("status_label")
        if status_label:
            status_label.text = message
