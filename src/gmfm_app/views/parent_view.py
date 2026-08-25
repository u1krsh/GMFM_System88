"""Parent Dashboard — cloud-direct, read-only view of a parent's linked children.

Parents hold no local data; this view reads their children and session history
live from the cloud via :class:`ParentService` and renders progress read-only.
Fails soft to an empty state when offline or when no children are linked yet.
"""

import threading

import flet as ft

from gmfm_app.data.database import DatabaseContext
from gmfm_app.services.parent_service import ParentService


PRIMARY = "#0D9488"
SECONDARY = "#7C3AED"
INFO = "#3B82F6"
SUCCESS_CLR = "#10B981"


def _colors(is_dark):
    if is_dark:
        return {
            "BG": "#0F172A", "CARD": "#1E293B", "BORDER": "#334155",
            "TEXT1": "#F8FAFC", "TEXT2": "#94A3B8", "TEXT3": "#64748B",
        }
    return {
        "BG": "#F8FAFC", "CARD": "#FFFFFF", "BORDER": "#E2E8F0",
        "TEXT1": "#1E293B", "TEXT2": "#64748B", "TEXT3": "#94A3B8",
    }


class ParentDashboardView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, is_dark: bool = False,
                 sync_service=None, current_user=None):
        c = _colors(is_dark)
        self._c = c
        super().__init__(route="/", padding=0, bgcolor=c["BG"])
        self._page_ref = page
        self.db_context = db_context
        self.parent_service = ParentService(sync_service)

        name = ""
        if current_user is not None:
            full = (getattr(current_user, "full_name", "") or "").strip()
            name = full.split(" ")[0] if full else (getattr(current_user, "username", "") or "").strip()

        header = ft.SafeArea(
            content=ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon("family_restroom", color="white", size=24),
                        width=46, height=46, bgcolor=INFO, border_radius=12,
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(f"Hello{', ' + name if name else ''}!", size=14, color=c["TEXT2"]),
                        ft.Text("Your children's progress", size=20, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                    ], spacing=0, expand=True),
                    ft.IconButton("refresh", icon_color=c["TEXT2"], tooltip="Refresh", on_click=lambda _: self._reload()),
                    ft.IconButton("settings", icon_color=c["TEXT2"], on_click=lambda _: self._page_ref.go("/settings")),
                ]),
                padding=ft.padding.only(left=16, right=8, top=8, bottom=12),
                bgcolor=c["CARD"],
                border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
            ),
            minimum_padding=ft.padding.only(top=10),
            bottom=False,
        )

        self.body = ft.Container(content=self._loading(), expand=True)
        self.controls = [ft.Column([header, self.body], spacing=0, expand=True)]
        self._reload()

    # ── states ────────────────────────────────────────────────────────────────

    def _loading(self):
        c = self._c
        return ft.Container(
            content=ft.Column([
                ft.ProgressRing(color=PRIMARY),
                ft.Container(height=12),
                ft.Text("Loading your children's progress…", size=14, color=c["TEXT2"]),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER),
            alignment=ft.alignment.center, expand=True,
        )

    def _message(self, icon, title, msg):
        c = self._c
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=64, color=c["TEXT3"]),
                ft.Container(height=12),
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=c["TEXT1"], text_align=ft.TextAlign.CENTER),
                ft.Container(height=6),
                ft.Text(msg, size=13, color=c["TEXT2"], text_align=ft.TextAlign.CENTER),
                ft.Container(height=20),
                ft.ElevatedButton("Retry", icon="refresh", bgcolor=PRIMARY, color="white",
                                  on_click=lambda _: self._reload()),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER),
            alignment=ft.alignment.center, expand=True, padding=30,
        )

    # ── loading ────────────────────────────────────────────────────────────────

    def _reload(self):
        self.body.content = self._loading()
        self._safe_update()

        def work():
            children = self.parent_service.children()
            self.body.content = self._render(children)
            self._safe_update()

        threading.Thread(target=work, daemon=True).start()

    def _safe_update(self):
        try:
            self._page_ref.update()
        except Exception:
            pass

    # ── render ────────────────────────────────────────────────────────────────

    def _render(self, children):
        c = self._c
        if children is None:
            return self._message("cloud_off", "You're offline",
                                 "Connect to the internet to see your\nchildren's latest assessments.")
        if not children:
            return self._message("child_care", "No children linked yet",
                                 "Ask your child's teacher or the administrator\nto link your account to your child.")

        cards = [self._note()]
        for ch in children:
            cards.append(self._child_card(ch))
        return ft.Container(
            content=ft.Column(cards, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True),
            padding=16, expand=True,
        )

    def _note(self):
        c = self._c
        return ft.Container(
            content=ft.Row([
                ft.Icon("visibility", size=16, color=INFO),
                ft.Text("Read-only — contact your child's teacher to make changes.",
                        size=12, color=c["TEXT2"], expand=True),
            ], spacing=8),
            bgcolor=INFO + "14", border_radius=10, padding=10,
        )

    def _child_card(self, ch):
        c = self._c
        # Session history rows (newest first).
        if ch.sessions:
            history = []
            for s in ch.sessions:
                score = f"{s.score:.0f}" if s.score is not None else "—"
                history.append(ft.Row([
                    ft.Icon("assessment", size=14, color=c["TEXT3"]),
                    ft.Text(s.date or "—", size=13, color=c["TEXT1"], expand=True),
                    ft.Container(
                        content=ft.Text(f"GMFM-{s.scale}", size=10, weight=ft.FontWeight.BOLD, color=SECONDARY),
                        bgcolor=SECONDARY + "18", padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=6,
                    ),
                    ft.Text(score, size=14, weight=ft.FontWeight.BOLD, color=PRIMARY),
                ], spacing=8))
            history_col = ft.Column(history, spacing=8)
        else:
            history_col = ft.Text("No assessments recorded yet.", size=12, color=c["TEXT3"], italic=True)

        latest = ch.latest_score
        latest_badge = ft.Container(
            content=ft.Column([
                ft.Text("Latest", size=10, color=c["TEXT3"]),
                ft.Text(f"{latest:.0f}" if latest is not None else "—",
                        size=20, weight=ft.FontWeight.BOLD, color=PRIMARY),
            ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END),
        )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Text((ch.given_name[:1] or "?").upper(), size=18, weight=ft.FontWeight.BOLD, color="white"),
                        width=44, height=44, bgcolor=INFO, border_radius=22, alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(ch.full_name, size=17, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                        ft.Text(f"{len(ch.sessions)} assessment{'s' if len(ch.sessions) != 1 else ''}"
                                + (f" · DOB {ch.dob}" if ch.dob else ""),
                                size=12, color=c["TEXT2"]),
                    ], spacing=1, expand=True),
                    latest_badge,
                ], spacing=12),
                ft.Divider(height=1, color=c["BORDER"]),
                history_col,
            ], spacing=10),
            bgcolor=c["CARD"], border=ft.border.all(1, c["BORDER"]),
            border_radius=14, padding=14,
        )
