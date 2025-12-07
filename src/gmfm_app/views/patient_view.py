"""
Patient Form - Light Mode
"""
import flet as ft
from datetime import datetime
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import PatientRepository
from gmfm_app.data.models import Patient


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


class PatientView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, patient_id: int = None):
        super().__init__(route="/patient", padding=0, bgcolor=BG)
        self.page = page
        self.db_context = db_context
        self.repo = PatientRepository(db_context)
        self.patient_id = patient_id

        # Header
        header = ft.Container(
            content=ft.Row([
                ft.IconButton("arrow_back", icon_color=TEXT1, on_click=lambda _: self.page.go("/")),
                ft.Text("New Patient", size=20, weight=ft.FontWeight.BOLD, color=TEXT1),
            ]),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            bgcolor=CARD,
            border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
        )

        self.given_name = self._field("First Name")
        self.family_name = self._field("Last Name")
        self.identifier = self._field("Patient ID / MRN")
        
        self.dob_picker = ft.DatePicker(first_date=datetime(1950, 1, 1), last_date=datetime.now(), on_change=self._set_dob)
        self.selected_dob = None
        self.dob_text = ft.Text("Select date", size=15, color=TEXT3)

        form = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon("person_add", size=40, color="white"),
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
                        ft.Column([ft.Text("Date of Birth", size=12, color=TEXT2), self.dob_text], spacing=2, expand=True),
                        ft.IconButton("edit", icon_color=PRIMARY, on_click=lambda _: self.page.open(self.dob_picker)),
                    ]),
                    padding=14,
                    bgcolor=CARD,
                    border_radius=12,
                    border=ft.border.all(1, BORDER),
                ),
                ft.Container(height=25),
                ft.ElevatedButton(
                    "Save Patient",
                    icon="save",
                    bgcolor=PRIMARY,
                    color="white",
                    width=200,
                    height=48,
                    on_click=self._save,
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30,
            bgcolor=CARD,
            border_radius=20,
            border=ft.border.all(1, BORDER),
            width=400,
        )

        self.controls = [
            header,
            ft.Container(content=form, alignment=ft.alignment.center, expand=True, padding=20),
        ]

    def _field(self, label):
        return ft.TextField(
            label=label,
            border_radius=12,
            bgcolor=CARD,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            color=TEXT1,
            label_style=ft.TextStyle(color=TEXT2),
            height=55,
        )

    def _set_dob(self, e):
        if self.dob_picker.value:
            self.selected_dob = self.dob_picker.value.date()
            self.dob_text.value = self.selected_dob.strftime("%B %d, %Y")
            self.dob_text.color = TEXT1
            self.update()

    def _save(self, e):
        if not self.given_name.value or not self.family_name.value:
            self.page.snack_bar = ft.SnackBar(ft.Text("Please fill name fields"), bgcolor=ERROR)
            self.page.snack_bar.open = True
            self.page.update()
            return

        patient = Patient(given_name=self.given_name.value, family_name=self.family_name.value, identifier=self.identifier.value, dob=self.selected_dob)
        try:
            self.repo.create_patient(patient)
            self.page.snack_bar = ft.SnackBar(ft.Text("Patient saved!"), bgcolor=SUCCESS)
            self.page.snack_bar.open = True
            self.page.update()
            self.page.go("/")
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor=ERROR)
            self.page.snack_bar.open = True
            self.page.update()
