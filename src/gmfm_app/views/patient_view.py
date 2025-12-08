"""
Patient Form - With Edit and Delete Support
"""
import flet as ft
from datetime import datetime
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import PatientRepository, SessionRepository
from gmfm_app.data.models import Patient


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


class PatientView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, is_dark: bool = False, patient_id: int = None):
        c = get_colors(is_dark)
        route = f"/patient?id={patient_id}" if patient_id else "/patient"
        super().__init__(route=route, padding=0, bgcolor=c["BG"])
        self.page = page
        self.db_context = db_context
        self.repo = PatientRepository(db_context)
        self.session_repo = SessionRepository(db_context)
        self.patient_id = patient_id
        self.c = c
        self.is_edit = patient_id is not None
        self.existing_patient = None

        # Load existing patient data if editing
        if self.is_edit:
            self.existing_patient = self.repo.get_patient(patient_id)

        # Header
        title = "Edit Patient" if self.is_edit else "New Patient"
        header = ft.Container(
            content=ft.Row([
                ft.IconButton("arrow_back", icon_color=c["TEXT1"], on_click=lambda _: self.page.go("/")),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=c["TEXT1"], expand=True),
                ft.IconButton("delete", icon_color=ERROR, on_click=self._confirm_delete) if self.is_edit else ft.Container(),
            ]),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            bgcolor=c["CARD"],
            border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
        )

        self.given_name = self._field("First Name", c)
        self.family_name = self._field("Last Name", c)
        self.identifier = self._field("Patient ID / MRN", c)
        
        self.dob_picker = ft.DatePicker(first_date=datetime(1950, 1, 1), last_date=datetime.now(), on_change=self._set_dob)
        self.selected_dob = None
        self.dob_text = ft.Text("Select date", size=15, color=c["TEXT3"])

        # Pre-fill if editing
        if self.existing_patient:
            self.given_name.value = self.existing_patient.given_name
            self.family_name.value = self.existing_patient.family_name
            self.identifier.value = self.existing_patient.identifier or ""
            if self.existing_patient.dob:
                self.selected_dob = self.existing_patient.dob
                self.dob_text.value = self.existing_patient.dob.strftime("%B %d, %Y")
                self.dob_text.color = c["TEXT1"]

        form = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon("edit" if self.is_edit else "person_add", size=40, color="white"),
                    width=80, height=80,
                    bgcolor=PRIMARY,
                    border_radius=20,
                    alignment=ft.alignment.center,
                ),
                ft.Container(height=25),
                self.given_name,
                ft.Container(height=12),
                self.family_name,
                ft.Container(height=12),
                self.identifier,
                ft.Container(height=12),
                ft.Container(
                    content=ft.Row([
                        ft.Icon("calendar_today", color=PRIMARY, size=22),
                        ft.Container(width=12),
                        ft.Column([ft.Text("Date of Birth", size=12, color=c["TEXT2"]), self.dob_text], spacing=2, expand=True),
                        ft.IconButton("edit", icon_color=PRIMARY, on_click=lambda _: self.page.open(self.dob_picker)),
                    ]),
                    padding=14,
                    bgcolor=c["CARD"],
                    border_radius=12,
                    border=ft.border.all(1, c["BORDER"]),
                ),
                ft.Container(height=25),
                ft.ElevatedButton(
                    "Update Patient" if self.is_edit else "Save Patient",
                    icon="save",
                    bgcolor=PRIMARY,
                    color="white",
                    width=200,
                    height=48,
                    on_click=self._save,
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30,
            bgcolor=c["CARD"],
            border_radius=20,
            border=ft.border.all(1, c["BORDER"]),
            width=400,
        )

        self.controls = [
            header,
            ft.Container(content=form, alignment=ft.alignment.center, expand=True, padding=20),
        ]

    def _field(self, label, c):
        return ft.TextField(
            label=label,
            border_radius=12,
            bgcolor=c["CARD"],
            border_color=c["BORDER"],
            focused_border_color=PRIMARY,
            color=c["TEXT1"],
            label_style=ft.TextStyle(color=c["TEXT2"]),
            height=55,
        )

    def _set_dob(self, e):
        if self.dob_picker.value:
            self.selected_dob = self.dob_picker.value.date()
            self.dob_text.value = self.selected_dob.strftime("%B %d, %Y")
            self.dob_text.color = self.c["TEXT1"]
            self.update()

    def _confirm_delete(self, e):
        c = self.c
        
        def do_delete(e):
            # Delete all sessions first
            sessions = self.session_repo.list_sessions_for_patient(self.patient_id)
            for s in sessions:
                self.session_repo.delete_session(s.id)
            # Delete patient
            self.repo.delete_patient(self.patient_id)
            dlg.open = False
            self.page.update()
            self.page.snack_bar = ft.SnackBar(ft.Text("Patient deleted"), bgcolor=WARNING)
            self.page.snack_bar.open = True
            self.page.go("/")
        
        def cancel(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Delete Patient?"),
            content=ft.Text("This will delete all assessments for this patient. This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Delete", style=ft.ButtonStyle(color=ERROR), on_click=do_delete),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _save(self, e):
        if not self.given_name.value or not self.family_name.value:
            self.page.snack_bar = ft.SnackBar(ft.Text("Please fill name fields"), bgcolor=ERROR)
            self.page.snack_bar.open = True
            self.page.update()
            return

        try:
            if self.is_edit and self.existing_patient:
                # Update existing
                self.existing_patient.given_name = self.given_name.value
                self.existing_patient.family_name = self.family_name.value
                self.existing_patient.identifier = self.identifier.value
                self.existing_patient.dob = self.selected_dob
                self.repo.update_patient(self.existing_patient)
                self.page.snack_bar = ft.SnackBar(ft.Text("Patient updated!"), bgcolor=SUCCESS)
            else:
                # Create new
                patient = Patient(
                    given_name=self.given_name.value,
                    family_name=self.family_name.value,
                    identifier=self.identifier.value,
                    dob=self.selected_dob
                )
                self.repo.create_patient(patient)
                self.page.snack_bar = ft.SnackBar(ft.Text("Patient saved!"), bgcolor=SUCCESS)
            
            self.page.snack_bar.open = True
            self.page.update()
            self.page.go("/")
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor=ERROR)
            self.page.snack_bar.open = True
            self.page.update()
