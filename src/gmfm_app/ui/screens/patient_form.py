from __future__ import annotations

from typing import Any, Optional

from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp

from gmfm_app.data.models import Patient
from gmfm_app.data.repositories import PatientRepository


class PatientFormScreen(MDScreen):
    def __init__(self, db_context, **kwargs: Any):  # type: ignore[override]
        super().__init__(**kwargs)
        self.repo = PatientRepository(db_context)
        self.current_patient: Optional[Patient] = None

    def load_patient(self, patient: Optional[Patient]) -> None:
        self.current_patient = patient
        if not self.ids:
            return
        given = self.ids.get("given_name_field")
        family = self.ids.get("family_name_field")
        identifier = self.ids.get("identifier_field")
        if patient:
            given.text = patient.given_name
            family.text = patient.family_name
            identifier.text = patient.identifier or ""
        else:
            given.text = ""
            family.text = ""
            identifier.text = ""

    def save_patient(self) -> None:
        given = self.ids.get("given_name_field").text.strip()
        family = self.ids.get("family_name_field").text.strip()
        identifier = self.ids.get("identifier_field").text.strip() or None
        
        # Validation with feedback
        if not given or not family:
            from kivymd.uix.snackbar import Snackbar
            errors = []
            if not given:
                errors.append("Given name required")
            if not family:
                errors.append("Family name required")
            Snackbar(text=" | ".join(errors), duration=3).open()
            return
        
        patient_id: Optional[int] = None
        try:
            if self.current_patient:
                updated = self.current_patient.copy(update={
                    "given_name": given,
                    "family_name": family,
                    "identifier": identifier,
                })
                self.repo.update_patient(updated)
                patient_id = updated.id
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text="✓ Patient updated successfully", duration=2).open()
            else:
                patient = Patient(given_name=given, family_name=family, identifier=identifier)
                saved = self.repo.create_patient(patient)
                patient_id = saved.id
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text="✓ Patient saved successfully", duration=2).open()
        except Exception as e:
            from kivymd.uix.snackbar import Snackbar
            error_msg = str(e)
            if "UNIQUE constraint" in error_msg or "unique" in error_msg.lower():
                Snackbar(text=f"Patient identifier '{identifier}' already exists", duration=4).open()
            else:
                Snackbar(text=f"Error saving patient: {error_msg}", duration=4).open()
            return

        # Refresh dashboard
        try:
            dashboard = self.manager.get_screen("dashboard")
            dashboard.refresh()
        except Exception:
            pass  # Dashboard might not be ready yet

        # Navigate based on whether editing or creating
        if self.current_patient:
            # Editing existing patient - go back to dashboard
            self.manager.current = "dashboard"
        else:
            # New patient - offer to start a test session
            if patient_id:
                try:
                    app: MDApp = MDApp.get_running_app()
                    self.current_patient = None
                    app.open_session_form(patient_id)
                except Exception as e:
                    # If session form fails, just go to dashboard
                    from kivymd.uix.snackbar import Snackbar
                    Snackbar(text=f"Going to dashboard. Error: {str(e)}", duration=3).open()
                    self.manager.current = "dashboard"
            else:
                self.manager.current = "dashboard"
