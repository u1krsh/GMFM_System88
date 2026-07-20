"""
Student Form - With Edit and Delete Support
"""
import flet as ft
from datetime import datetime
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import StudentRepository, SessionRepository
from gmfm_app.data.models import Student
from gmfm_app.services.haptics import tap, success, warning
from gmfm_app.theme import get_colors, PRIMARY, SUCCESS, WARNING, ERROR


class StudentView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, is_dark: bool = False, student_id: int = None, user_id=None, current_user=None):
        c = get_colors(is_dark)
        route = f"/student?id={student_id}" if student_id else "/student"
        super().__init__(route=route, padding=0, bgcolor=c["BG"])
        self._page_ref = page  # consistent naming with all other views
        self.db_context = db_context
        self.repo = StudentRepository(db_context, user_id=user_id)
        self.session_repo = SessionRepository(db_context, user_id=user_id)
        self.student_id = student_id
        self.c = c
        self.is_edit = student_id is not None
        self.existing_student = None
        self.is_read_only = getattr(current_user, 'role', 'teacher') == 'parent'

        # Load existing student data if editing
        if self.is_edit:
            self.existing_student = self.repo.get_student(student_id)

        # Header
        title = "Student Profile" if self.is_read_only else ("Edit Student" if self.is_edit else "New Student")
        header = ft.SafeArea(
            content=ft.Container(
                content=ft.Row([
                    ft.IconButton("arrow_back", icon_color=c["TEXT1"], on_click=lambda _: self._page_ref.go("/")),
                    ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=c["TEXT1"], expand=True),
                    ft.IconButton("delete", icon_color=ERROR, on_click=self._confirm_delete) if (self.is_edit and not self.is_read_only) else ft.Container(),
                ]),
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
                bgcolor=c["CARD"],
                border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
            ),
            minimum_padding=ft.padding.only(top=5),
            bottom=False,
        )

        self.given_name = self._field("First Name", c)
        self.family_name = self._field("Last Name", c)
        self.identifier = self._field("Student ID / MRN", c)
        
        self.dob_picker = ft.DatePicker(first_date=datetime(1950, 1, 1), last_date=datetime.now(), on_change=self._set_dob)
        self.selected_dob = None
        self.dob_text = ft.Text("Select date", size=15, color=c["TEXT3"])

        # Pre-fill if editing
        if self.existing_student:
            self.given_name.value = self.existing_student.given_name
            self.family_name.value = self.existing_student.family_name
            self.identifier.value = self.existing_student.identifier or ""
            if self.existing_student.dob:
                self.selected_dob = self.existing_student.dob
                self.dob_text.value = self.existing_student.dob.strftime("%B %d, %Y")
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
                        ft.IconButton("edit", icon_color=PRIMARY, on_click=lambda _: self._page_ref.open(self.dob_picker)) if not self.is_read_only else ft.Container(),
                    ]),
                    padding=14,
                    bgcolor=c["CARD"],
                    border_radius=12,
                    border=ft.border.all(1, c["BORDER"]),
                ),
                ft.Container(height=25),
                ft.ElevatedButton(
                    "Update Student" if self.is_edit else "Save Student",
                    icon="save",
                    bgcolor=PRIMARY,
                    color="white",
                    width=200,
                    height=48,
                    on_click=self._save,
                ) if not self.is_read_only else ft.Container(),
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
            read_only=self.is_read_only,
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
            sessions = self.session_repo.list_sessions_for_student(self.student_id)
            for s in sessions:
                self.session_repo.delete_session(s.id)
            # Delete student
            self.repo.delete_student(self.student_id)
            self._page_ref.close(dlg)
            self._page_ref.snack_bar = ft.SnackBar(ft.Text("Student deleted"), bgcolor=WARNING)
            self._page_ref.snack_bar.open = True
            self._page_ref.go("/")

        def cancel(e):
            self._page_ref.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("Delete Student?"),
            content=ft.Text("This will delete all assessments for this student. This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Delete", style=ft.ButtonStyle(color=ERROR), on_click=do_delete),
            ],
            on_dismiss=cancel,
        )
        self._page_ref.open(dlg)

    def _save(self, e):
        if not self.given_name.value or not self.family_name.value:
            warning(self._page_ref)  # Warning haptic for validation error
            self._page_ref.snack_bar = ft.SnackBar(ft.Text("Please fill name fields"), bgcolor=ERROR)
            self._page_ref.snack_bar.open = True
            self._page_ref.update()
            return

        try:
            success(self._page_ref)  # Success haptic
            if self.is_edit and self.existing_student:
                # Update existing
                self.existing_student.given_name = self.given_name.value
                self.existing_student.family_name = self.family_name.value
                self.existing_student.identifier = self.identifier.value
                self.existing_student.dob = self.selected_dob
                self.repo.update_student(self.existing_student)
                self._page_ref.snack_bar = ft.SnackBar(ft.Text("Student updated!"), bgcolor=SUCCESS)
            else:
                # Create new
                student = Student(
                    given_name=self.given_name.value,
                    family_name=self.family_name.value,
                    identifier=self.identifier.value,
                    dob=self.selected_dob
                )
                self.repo.create_student(student)
                self._page_ref.snack_bar = ft.SnackBar(ft.Text("Student saved!"), bgcolor=SUCCESS)

            self._page_ref.snack_bar.open = True
            self._page_ref.update()
            self._page_ref.go("/")
        except Exception as ex:
            self._page_ref.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor=ERROR)
            self._page_ref.snack_bar.open = True
            self._page_ref.update()
