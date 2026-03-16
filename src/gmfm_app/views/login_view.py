"""Mobile-first login and first-admin setup view."""

import flet as ft

from gmfm_app.services.auth_service import AuthService


PRIMARY = "#0D9488"
ERROR = "#DC2626"


def _colors(is_dark: bool):
    if is_dark:
        return {
            "BG": "#0B1220",
            "CARD": "#162033",
            "BORDER": "#334155",
            "TEXT1": "#F8FAFC",
            "TEXT2": "#94A3B8",
        }
    return {
        "BG": "#E6FFFA",
        "CARD": "#FFFFFF",
        "BORDER": "#D1FAE5",
        "TEXT1": "#0F172A",
        "TEXT2": "#475569",
    }


class LoginView(ft.View):
    def __init__(self, page: ft.Page, auth_service: AuthService, is_dark: bool = False):
        self._page = page
        self._auth = auth_service
        self._c = _colors(is_dark)
        self._setup_mode = not self._auth.has_users()
        super().__init__(route="/login", padding=0, bgcolor=self._c["BG"], scroll=ft.ScrollMode.AUTO)

        self.username = ft.TextField(
            label="Username",
            border_radius=12,
            border_color=self._c["BORDER"],
            focused_border_color=PRIMARY,
            text_size=15,
            height=50,
            autofocus=True,
        )
        self.password = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            border_radius=12,
            border_color=self._c["BORDER"],
            focused_border_color=PRIMARY,
            text_size=15,
            height=50,
            on_submit=self._submit,
        )
        self.full_name = ft.TextField(
            label="Full Name",
            border_radius=12,
            border_color=self._c["BORDER"],
            focused_border_color=PRIMARY,
            text_size=15,
            height=50,
            visible=self._setup_mode,
        )
        self.confirm_password = ft.TextField(
            label="Confirm Password",
            password=True,
            can_reveal_password=True,
            border_radius=12,
            border_color=self._c["BORDER"],
            focused_border_color=PRIMARY,
            text_size=15,
            height=50,
            visible=self._setup_mode,
            on_submit=self._submit,
        )
        self.error_text = ft.Text("", color=ERROR, size=12, visible=False)

        self.action_btn = ft.ElevatedButton(
            text="Create Admin Account" if self._setup_mode else "Sign In",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                bgcolor=PRIMARY,
                color="#FFFFFF",
                padding=ft.padding.symmetric(vertical=14),
            ),
            on_click=self._submit,
            width=320,
            height=48,
        )

        self.controls = [self._build_layout()]

    def _build_layout(self):
        c = self._c
        title = "Set up your admin account" if self._setup_mode else "Sign in to MotorMeasure"
        subtitle = (
            "First launch detected. Create a secure admin account to continue."
            if self._setup_mode
            else "Use your account to access assessments and reports."
        )

        form_controls = [
            self.full_name,
            self.username,
            self.password,
            self.confirm_password,
            self.error_text,
            ft.Container(height=4),
            self.action_btn,
        ]

        return ft.SafeArea(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Container(
                            content=ft.Text("M", size=36, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                            width=84,
                            height=84,
                            border_radius=20,
                            bgcolor=PRIMARY,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(height=16),
                        ft.Text(title, size=24, weight=ft.FontWeight.BOLD, color=c["TEXT1"], text_align=ft.TextAlign.CENTER),
                        ft.Text(subtitle, size=13, color=c["TEXT2"], text_align=ft.TextAlign.CENTER),
                        ft.Container(height=20),
                        ft.Container(
                            content=ft.Column(form_controls, spacing=12),
                            width=380,
                            bgcolor=c["CARD"],
                            padding=20,
                            border_radius=16,
                            border=ft.border.all(1, c["BORDER"]),
                        ),
                        ft.Container(height=20),
                        ft.Text(
                            "Tip: Keep your password private. Online sign-in providers can be added later without changing this screen.",
                            size=11,
                            color=c["TEXT2"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=10),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    tight=False,
                    spacing=0,
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                expand=True,
                alignment=ft.alignment.center,
            ),
            expand=True,
        )

    def _show_error(self, message: str):
        self.error_text.value = message
        self.error_text.visible = True
        self.update()

    def _submit(self, _):
        self.error_text.visible = False
        self.update()

        username = (self.username.value or "").strip()
        password = self.password.value or ""
        if not username or not password:
            self._show_error("Username and password are required")
            return

        if self._setup_mode:
            full_name = (self.full_name.value or "").strip()
            confirm = self.confirm_password.value or ""
            if not full_name:
                self._show_error("Full name is required")
                return
            if password != confirm:
                self._show_error("Passwords do not match")
                return
            try:
                self._auth.create_first_admin(full_name, username, password)
            except ValueError as exc:
                self._show_error(str(exc))
                return
            except Exception:
                self._show_error("Could not create account. Please try again.")
                return

            self._setup_mode = False
            self.full_name.visible = False
            self.confirm_password.visible = False
            self.action_btn.text = "Sign In"

        user = self._auth.login(self._page, username, password)
        if not user:
            self._show_error("Invalid username or password")
            return

        self._page.go("/")
