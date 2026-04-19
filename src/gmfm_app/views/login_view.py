"""Login view with role selection and automatic Supabase registration."""

import flet as ft
from gmfm_app.services.auth_service import AuthService, VALID_ROLES


PRIMARY = "#0D9488"
ACCENT = "#7C3AED"
ERROR_CLR = "#EF4444"
SUCCESS_CLR = "#10B981"

ROLE_CONFIG = {
    "teacher": {"label": "Teacher", "icon": "school", "color": "#0D9488"},
    "admin": {"label": "Admin", "icon": "admin_panel_settings", "color": "#7C3AED"},
    "parent": {"label": "Parent", "icon": "family_restroom", "color": "#F59E0B"},
    "sponsor": {"label": "Sponsor", "icon": "volunteer_activism", "color": "#EC4899"},
}


def _colors(is_dark: bool):
    if is_dark:
        return {
            "BG": "#0F172A", "CARD": "#1E293B",
            "INPUT_BG": "#0F172A", "BORDER": "#334155",
            "TEXT1": "#F1F5F9", "TEXT2": "#94A3B8", "TEXT3": "#64748B",
        }
    return {
        "BG": "#F8FAFC", "CARD": "#FFFFFF",
        "INPUT_BG": "#F1F5F9", "BORDER": "#E2E8F0",
        "TEXT1": "#0F172A", "TEXT2": "#475569", "TEXT3": "#94A3B8",
    }


class LoginView(ft.View):
    def __init__(self, page: ft.Page, auth_service: AuthService, is_dark: bool = False):
        self._page = page
        self._auth = auth_service
        self._c = _colors(is_dark)
        self._is_dark = is_dark
        self._register_mode = not self._auth.has_users()
        self._selected_role = "teacher"
        super().__init__(route="/login", padding=0, bgcolor=self._c["BG"],
                         scroll=ft.ScrollMode.AUTO)
        self.controls = [self._build()]

    def _build(self):
        c = self._c

        # ── Logo ───────────────────────────────────────────────────
        logo = ft.Container(
            content=ft.Text("M", size=36, color="white", weight=ft.FontWeight.BOLD),
            width=72, height=72, border_radius=18,
            bgcolor=PRIMARY,
            alignment=ft.alignment.center,
        )

        # ── Title ──────────────────────────────────────────────────
        title = ft.Column([
            ft.Text("MotorMeasure", size=24, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
            ft.Container(height=2),
            ft.Text(
                "Create your account" if self._register_mode else "Sign in to continue",
                size=13, color=c["TEXT2"],
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)

        # ── Form ───────────────────────────────────────────────────
        self.full_name = self._field("Full Name", "badge")
        self.email = self._field("Email", "email", keyboard=ft.KeyboardType.EMAIL)
        self.username = self._field("Username", "person_outline", autofocus=True)
        self.password = self._field("Password", "lock_outline", password=True,
                                    on_submit=self._submit)
        self.confirm_pw = self._field("Confirm Password", "lock_outline", password=True,
                                      on_submit=self._submit)
        self.error_text = ft.Text("", color=ERROR_CLR, size=12, visible=False)

        # ── Role chips ─────────────────────────────────────────────
        self.role_row = self._build_role_row()

        # ── Button ─────────────────────────────────────────────────
        btn_label = "Create Account" if self._register_mode else "Sign In"
        self.action_btn = ft.Container(
            content=ft.Text(btn_label, color="white", weight=ft.FontWeight.BOLD, size=15),
            height=50, bgcolor=PRIMARY, border_radius=12,
            alignment=ft.alignment.center,
            on_click=self._submit, ink=True,
        )

        # ── Toggle link ────────────────────────────────────────────
        toggle_text = ("Already have an account? Sign In" if self._register_mode
                       else "Create a new account")
        self.toggle_link = ft.Container(
            content=ft.Text(toggle_text, color=PRIMARY, size=13,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER),
            on_click=self._toggle_mode,
            padding=ft.padding.symmetric(vertical=6),
        )

        # ── Layout ─────────────────────────────────────────────────
        reg_only = [self.role_row, self.full_name, self.email]

        form_children = []
        if self._register_mode:
            form_children.extend(reg_only)
        form_children.extend([
            self.username, self.password,
        ])
        if self._register_mode:
            form_children.append(self.confirm_pw)
        form_children.extend([
            self.error_text,
            ft.Container(height=4),
            self.action_btn,
            self.toggle_link,
        ])

        card = ft.Container(
            content=ft.Column(form_children, spacing=10),
            width=380, bgcolor=c["CARD"], padding=24, border_radius=16,
            border=ft.border.all(1, c["BORDER"]),
        )

        # ── Footer badges ──────────────────────────────────────────
        badges = ft.Row([
            self._badge("offline", "Offline First", c),
            self._badge("security", "Encrypted", c),
            self._badge("cloud_sync", "Cloud Sync", c),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=6)

        footer = ft.Text("GMFM-88 Clinical Assessment System", size=10,
                         color=c["TEXT3"], text_align=ft.TextAlign.CENTER)

        return ft.SafeArea(
            content=ft.Container(
                content=ft.Column([
                    ft.Container(height=32),
                    logo,
                    ft.Container(height=14),
                    title,
                    ft.Container(height=18),
                    card,
                    ft.Container(height=14),
                    badges,
                    ft.Container(expand=True),
                    footer,
                    ft.Container(height=10),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                padding=ft.padding.symmetric(horizontal=24),
                expand=True, alignment=ft.alignment.center,
            ),
            expand=True,
        )

    # ── Helpers ────────────────────────────────────────────────────

    def _field(self, label, icon, password=False, autofocus=False,
               on_submit=None, keyboard=None):
        c = self._c
        return ft.TextField(
            label=label, prefix_icon=icon,
            border_radius=12, border_color=c["BORDER"],
            focused_border_color=PRIMARY, bgcolor=c["INPUT_BG"],
            color=c["TEXT1"], label_style=ft.TextStyle(color=c["TEXT3"]),
            text_size=14, height=50,
            password=password, can_reveal_password=password,
            autofocus=autofocus, on_submit=on_submit,
            keyboard_type=keyboard,
        )

    def _badge(self, icon, text, c):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=13, color=PRIMARY),
                ft.Text(text, size=10, color=c["TEXT2"]),
            ], spacing=4),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            bgcolor=f"{PRIMARY}08", border_radius=16,
        )

    def _build_role_row(self):
        c = self._c
        chips = []
        for key, cfg in ROLE_CONFIG.items():
            selected = key == self._selected_role
            chip = ft.Container(
                content=ft.Column([
                    ft.Icon(cfg["icon"], size=20,
                            color="white" if selected else cfg["color"]),
                    ft.Text(cfg["label"], size=9,
                            weight=ft.FontWeight.BOLD if selected else ft.FontWeight.W_500,
                            color="white" if selected else c["TEXT2"],
                            text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.CENTER, spacing=3),
                width=72, height=60, border_radius=12,
                bgcolor=cfg["color"] if selected else f"{cfg['color']}12",
                border=ft.border.all(1.5, cfg["color"] if selected else "transparent"),
                alignment=ft.alignment.center,
                on_click=lambda _, r=key: self._select_role(r),
                ink=True,
            )
            chips.append(chip)

        return ft.Container(
            content=ft.Column([
                ft.Text("Account Type", size=11, weight=ft.FontWeight.W_600,
                         color=c["TEXT2"]),
                ft.Container(height=4),
                ft.Row(chips, alignment=ft.MainAxisAlignment.CENTER, spacing=6,
                       wrap=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            visible=self._register_mode,
        )

    def _select_role(self, role: str):
        self._selected_role = role
        new_row = self._build_role_row()
        self.role_row.content = new_row.content
        self.update()

    def _toggle_mode(self, _):
        self._register_mode = not self._register_mode
        # Rebuild the entire view to toggle fields
        self.controls = [self._build()]
        self.update()

    def _show_error(self, msg: str):
        self.error_text.value = msg
        self.error_text.visible = True
        self.update()

    def _submit(self, _):
        self.error_text.visible = False
        self.update()

        username = (self.username.value or "").strip()
        password = self.password.value or ""
        if not username or not password:
            return self._show_error("Username and password are required")

        if self._register_mode:
            name = (self.full_name.value or "").strip()
            email = (self.email.value or "").strip()
            confirm = self.confirm_pw.value or ""
            role = self._selected_role

            if not name:
                return self._show_error("Full name is required")
            if not email or "@" not in email:
                return self._show_error("A valid email is required for cloud sync")
            if len(password) < 6:
                return self._show_error("Password must be at least 6 characters")
            if password != confirm:
                return self._show_error("Passwords do not match")
            try:
                self._auth.create_user_account(name, username, password,
                                               email=email, role=role)
            except ValueError as exc:
                return self._show_error(str(exc))
            except Exception as exc:
                return self._show_error(f"Error: {str(exc)[:80]}")

        user = self._auth.login(self._page, username, password)
        if not user:
            return self._show_error("Invalid username or password")
        self._page.go("/")
