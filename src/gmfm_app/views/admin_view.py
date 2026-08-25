"""Admin Console — cloud-backed multi-user overview.

Lists every teacher with their caseload + stats, every parent with their linked
children, every child with its owner/co-teachers/parents, and every account with
role management. Reads and writes go through :class:`AdminService`, which talks
to Supabase directly under the admin's session. The console is online-only and
fails soft to an empty state when offline.
"""

import threading

import flet as ft

from gmfm_app.data.database import DatabaseContext
from gmfm_app.services.admin_service import AdminService
from gmfm_app.services.haptics import tap, success, warning


PRIMARY = "#0D9488"
SECONDARY = "#7C3AED"
SUCCESS_CLR = "#10B981"
ERROR = "#EF4444"
WARNING_CLR = "#F59E0B"
INFO = "#3B82F6"

_ROLE_COLORS = {
    "admin": "#7C3AED", "teacher": "#0D9488", "parent": "#3B82F6", "sponsor": "#F59E0B",
}


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


def _fmt_date(iso: str) -> str:
    return (iso or "")[:10] or "—"


def _fmt_avg(avg) -> str:
    return f"{avg:.0f}" if avg is not None else "—"


class AdminConsoleView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, is_dark: bool = False,
                 auth_service=None, sync_service=None, current_user=None):
        c = _colors(is_dark)
        self._c = c
        super().__init__(route="/admin", padding=0, bgcolor=c["BG"])
        self._page_ref = page
        self.db_context = db_context
        self.sync_service = sync_service
        self.auth_service = auth_service
        self.admin_service = AdminService(sync_service)
        self._snapshot = None

        header = ft.SafeArea(
            content=ft.Container(
                content=ft.Row([
                    ft.IconButton("arrow_back", icon_color=c["TEXT1"], on_click=lambda _: self._page_ref.go("/")),
                    ft.Icon("admin_panel_settings", color=SECONDARY, size=24),
                    ft.Text("Admin Console", size=20, weight=ft.FontWeight.BOLD, color=c["TEXT1"], expand=True),
                    ft.IconButton("refresh", icon_color=c["TEXT2"], tooltip="Refresh", on_click=lambda _: self._reload()),
                ]),
                padding=ft.padding.only(left=8, right=8, top=8, bottom=10),
                bgcolor=c["CARD"],
                border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
            ),
            minimum_padding=ft.padding.only(top=10),
            bottom=False,
        )

        # Body swaps between loading / empty / loaded (tabs).
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
                ft.Text("Loading admin console…", size=14, color=c["TEXT2"]),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER),
            alignment=ft.alignment.center, expand=True,
        )

    _NOTICE_STYLE = {
        "offline":        ("cloud_off", "Admin console is offline"),
        "not_configured": ("cloud_off", "Cloud sync isn't available"),
        "no_session":     ("no_accounts", "Not signed in to the cloud"),
        "not_admin":      ("gpp_maybe", "This account isn't an admin on the server"),
        "error":          ("error_outline", "Couldn't load the admin console"),
    }

    def _notice(self, status):
        """Empty state that says *which* of the failure modes actually happened."""
        c = self._c
        icon, title = self._NOTICE_STYLE.get(status.get("state"),
                                             ("cloud_off", "Admin console unavailable"))
        body = [
            ft.Icon(icon, size=64, color=c["TEXT3"]),
            ft.Container(height=12),
            ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=c["TEXT1"],
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=6),
            ft.Text(status.get("detail", ""), size=13, color=c["TEXT2"],
                    text_align=ft.TextAlign.CENTER),
        ]
        if status.get("email"):
            body += [
                ft.Container(height=10),
                ft.Text(f"Signed in as {status['email']}"
                        + (f" · server role: {status['role']}" if status.get("role") else ""),
                        size=11, color=c["TEXT3"], text_align=ft.TextAlign.CENTER),
            ]
        body += [
            ft.Container(height=20),
            ft.ElevatedButton("Retry", icon="refresh", bgcolor=PRIMARY, color="white",
                              on_click=lambda _: self._reload()),
        ]
        return ft.Container(
            content=ft.Column(body, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                              alignment=ft.MainAxisAlignment.CENTER,
                              scroll=ft.ScrollMode.AUTO),
            alignment=ft.alignment.center, expand=True, padding=30,
        )

    # ── loading ────────────────────────────────────────────────────────────────

    def _reload(self):
        self.body.content = self._loading()
        self._safe_update()

        def work():
            # Network latency guarantees the view is mounted before we update.
            # status() first: an empty console has several causes (offline, no
            # cloud session, cloud role isn't admin) and they must not all render
            # as the same silent empty state.
            status = self.admin_service.status()
            if status.get("state") != "ok":
                self._snapshot = None
                self.body.content = self._notice(status)
                self._safe_update()
                return
            snap = self.admin_service.snapshot()
            self._snapshot = snap
            self.body.content = (self._notice({"state": "error",
                                               "detail": "The cloud query failed. Check your "
                                                         "connection and retry.",
                                               "email": status.get("email", ""),
                                               "role": status.get("role")})
                                 if snap is None else self._build_tabs())
            self._safe_update()

        threading.Thread(target=work, daemon=True).start()

    def _safe_update(self):
        try:
            self._page_ref.update()
        except Exception:
            pass

    # ── tabs ────────────────────────────────────────────────────────────────

    def _build_tabs(self):
        snap = self._snapshot
        return ft.Tabs(
            selected_index=0,
            animation_duration=200,
            label_color=PRIMARY,
            indicator_color=PRIMARY,
            tabs=[
                ft.Tab(text=f"Teachers ({len(snap.teachers)})", content=self._tab_teachers()),
                ft.Tab(text=f"Parents ({len(snap.parents)})", content=self._tab_parents()),
                ft.Tab(text=f"Children ({len(snap.children)})", content=self._tab_children()),
                ft.Tab(text=f"Accounts ({len(snap.accounts)})", content=self._tab_accounts()),
            ],
            expand=True,
        )

    def _scroll(self, controls, empty_msg):
        c = self._c
        if not controls:
            return ft.Container(
                content=ft.Text(empty_msg, size=14, color=c["TEXT2"], text_align=ft.TextAlign.CENTER),
                alignment=ft.alignment.center, expand=True, padding=30,
            )
        return ft.Container(
            content=ft.Column(controls, spacing=10, scroll=ft.ScrollMode.AUTO, expand=True),
            padding=16, expand=True,
        )

    # ── shared pieces ────────────────────────────────────────────────────────

    def _role_badge(self, role):
        color = _ROLE_COLORS.get(role, "#64748B")
        return ft.Container(
            content=ft.Text(role.capitalize() or "—", size=10, weight=ft.FontWeight.BOLD, color=color),
            bgcolor=color + "22", padding=ft.padding.symmetric(horizontal=8, vertical=3), border_radius=8,
        )

    def _chip(self, label, color, on_remove=None):
        c = self._c
        row = [ft.Text(label, size=11, color=c["TEXT1"])]
        if on_remove is not None:
            row.append(ft.IconButton("close", icon_size=12, icon_color=c["TEXT3"],
                                     padding=0, width=20, height=20, on_click=on_remove))
        return ft.Container(
            content=ft.Row(row, spacing=2, tight=True),
            bgcolor=color + "18", border=ft.border.all(1, color + "44"),
            padding=ft.padding.only(left=8, right=2 if on_remove else 8, top=2, bottom=2),
            border_radius=10,
        )

    def _stats_row(self, children_count, session_count, avg, last):
        c = self._c
        def cell(icon, val):
            return ft.Row([ft.Icon(icon, size=13, color=c["TEXT3"]),
                           ft.Text(val, size=12, color=c["TEXT2"])], spacing=3, tight=True)
        cells = []
        if children_count is not None:
            cells.append(cell("people", f"{children_count} children"))
        cells.append(cell("assessment", f"{session_count} sessions"))
        cells.append(cell("trending_up", f"avg {_fmt_avg(avg)}"))
        cells.append(cell("event", _fmt_date(last)))
        return ft.Row(cells, spacing=14, wrap=True)

    def _card(self, *content):
        c = self._c
        return ft.Container(
            content=ft.Column(list(content), spacing=8),
            bgcolor=c["CARD"], border=ft.border.all(1, c["BORDER"]),
            border_radius=14, padding=14,
        )

    # ── Teachers tab ────────────────────────────────────────────────────────

    def _tab_teachers(self):
        c = self._c
        cards = []
        for t in self._snapshot.teachers:
            child_rows = [
                ft.Row([
                    ft.Icon("child_care", size=14, color=c["TEXT3"]),
                    ft.Text(ch.full_name, size=13, color=c["TEXT1"], expand=True),
                    ft.Text(f"{ch.session_count} sessions", size=11, color=c["TEXT3"]),
                ], spacing=6)
                for ch in t.children
            ] or [ft.Text("No children assigned yet", size=12, color=c["TEXT3"], italic=True)]
            cards.append(self._card(
                ft.Row([
                    ft.Text(t.display_name, size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"], expand=True),
                    self._role_badge(t.role),
                ]),
                ft.Text(t.email, size=12, color=c["TEXT2"]),
                self._stats_row(len(t.children), t.session_count, t.avg_score, t.last_assessment),
                ft.Divider(height=1, color=c["BORDER"]),
                ft.Column(child_rows, spacing=6),
            ))
        return self._scroll(cards, "No teacher accounts yet.")

    # ── Parents tab ────────────────────────────────────────────────────────

    def _tab_parents(self):
        c = self._c
        cards = []
        for p in self._snapshot.parents:
            child_rows = [
                ft.Row([
                    ft.Icon("child_care", size=14, color=c["TEXT3"]),
                    ft.Text(ch.full_name, size=13, color=c["TEXT1"], expand=True),
                    ft.Text(f"via {ch.owner_name}", size=11, color=c["TEXT3"]),
                ], spacing=6)
                for ch in p.children
            ] or [ft.Text("No children linked. Assign from the Children tab.",
                          size=12, color=c["TEXT3"], italic=True)]
            cards.append(self._card(
                ft.Row([
                    ft.Text(p.display_name, size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"], expand=True),
                    self._role_badge(p.role),
                ]),
                ft.Text(p.email, size=12, color=c["TEXT2"]),
                ft.Divider(height=1, color=c["BORDER"]),
                ft.Column(child_rows, spacing=6),
            ))
        return self._scroll(cards, "No parent accounts yet.")

    # ── Children tab ────────────────────────────────────────────────────────

    def _tab_children(self):
        c = self._c
        profiles = self._snapshot.profiles_by_id
        cards = []
        for ch in self._snapshot.children:
            # Co-teacher chips (everyone but the owner) — removable.
            teacher_chips = []
            for uid in ch.teacher_ids:
                is_owner = uid == ch.created_by
                name = _display_name(profiles.get(uid))
                label = f"{name} (owner)" if is_owner else name
                teacher_chips.append(self._chip(
                    label, PRIMARY,
                    on_remove=None if is_owner else self._remover(ch.id, uid),
                ))
            parent_chips = [
                self._chip(_display_name(profiles.get(uid)), INFO, on_remove=self._remover(ch.id, uid))
                for uid in ch.parent_ids
            ] or [ft.Text("None", size=11, color=c["TEXT3"], italic=True)]

            cards.append(self._card(
                ft.Row([
                    ft.Text(ch.full_name, size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"], expand=True),
                ]),
                self._stats_row(None, ch.session_count, ch.avg_score, ch.last_assessment),
                ft.Text("Teachers", size=11, weight=ft.FontWeight.BOLD, color=c["TEXT2"]),
                ft.Row(teacher_chips, spacing=6, wrap=True),
                ft.Text("Parents", size=11, weight=ft.FontWeight.BOLD, color=c["TEXT2"]),
                ft.Row(parent_chips, spacing=6, wrap=True),
                ft.Row([
                    ft.OutlinedButton("Assign parent", icon="family_restroom",
                                      on_click=self._assigner(ch, "parent")),
                    ft.OutlinedButton("Add co-teacher", icon="group_add",
                                      on_click=self._assigner(ch, "teacher")),
                ], spacing=8, wrap=True),
            ))
        return self._scroll(cards, "No children records yet.")

    # ── Accounts tab ────────────────────────────────────────────────────────

    def _tab_accounts(self):
        c = self._c
        my_uid = getattr(self.sync_service, "_user_id", None)
        admin_count = sum(1 for p in self._snapshot.accounts if p.get("role") == "admin")
        rows = [self._card(
            ft.Row([
                ft.Icon("admin_panel_settings", color=SECONDARY, size=22),
                ft.Column([
                    ft.Text("Administrators", size=14, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                    ft.Text(f"{admin_count} admin account{'s' if admin_count != 1 else ''}",
                            size=11, color=c["TEXT2"]),
                ], spacing=0, expand=True),
                ft.ElevatedButton("Add admin", icon="person_add", bgcolor=SECONDARY,
                                  color="white",
                                  on_click=lambda _: self._open_add_admin_dialog()),
            ], spacing=10),
        )]
        for p in self._snapshot.accounts:
            uid = p["id"]
            is_me = uid == my_uid
            role = p.get("role", "teacher")
            options = ["admin", "teacher", "parent"]
            if role == "sponsor" and "sponsor" not in options:
                options.append("sponsor")
            dd = ft.Dropdown(
                value=role if role in options else "teacher",
                width=130, dense=True, disabled=is_me,
                options=[ft.dropdown.Option(r, r.capitalize()) for r in options],
                on_change=self._role_changer(uid),
            )
            rows.append(self._card(
                ft.Row([
                    ft.Column([
                        ft.Text(_display(p) + (" (you)" if is_me else ""),
                                size=15, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                        ft.Text(p.get("email", ""), size=12, color=c["TEXT2"]),
                    ], spacing=2, expand=True),
                    dd,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ))
        return self._scroll(rows, "No accounts yet.")

    # ── actions ────────────────────────────────────────────────────────────

    def _remover(self, student_id, user_uid):
        def handler(e):
            tap(self._page_ref)
            ok, msg = self.admin_service.remove_access(student_id, user_uid)
            self._after_write(ok, msg)
        return handler

    def _role_changer(self, uid):
        def handler(e):
            tap(self._page_ref)
            ok, msg = self.admin_service.set_role(uid, e.control.value)
            self._after_write(ok, msg)
        return handler

    def _assigner(self, child, kind):
        def handler(e):
            self._open_assign_dialog(child, kind)
        return handler

    def _open_assign_dialog(self, child, kind):
        c = self._c
        snap = self._snapshot
        if kind == "parent":
            title = f"Assign a parent to {child.full_name}"
            pool = [p for p in snap.parents if p.id not in child.parent_ids]
            empty_msg = "No parent accounts available. Ask a parent to sign up first."
        else:
            title = f"Add a co-teacher to {child.full_name}"
            pool = [t for t in snap.teachers if t.id not in child.teacher_ids]
            empty_msg = "No other teacher accounts available."

        def pick(person):
            def handler(e):
                tap(self._page_ref)
                self._page_ref.close(dlg)
                if kind == "parent":
                    ok, msg = self.admin_service.assign_parent(child.id, person.id)
                else:
                    ok, msg = self.admin_service.add_coteacher(child.id, person.id)
                self._after_write(ok, msg)
            return handler

        if pool:
            items = [
                ft.Container(
                    content=ft.Row([
                        ft.Icon("person", size=18, color=c["TEXT3"]),
                        ft.Column([
                            ft.Text(person.display_name, size=14, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                            ft.Text(person.email, size=11, color=c["TEXT2"]),
                        ], spacing=0, expand=True),
                        ft.Icon("add_circle", size=20, color=PRIMARY),
                    ], spacing=10),
                    padding=10, border_radius=10, ink=True,
                    on_click=pick(person),
                )
                for person in pool
            ]
            content = ft.Column(items, spacing=6, scroll=ft.ScrollMode.AUTO, tight=True, width=340, height=min(len(items) * 62, 360))
        else:
            content = ft.Container(content=ft.Text(empty_msg, size=13, color=c["TEXT2"]), width=340, padding=10)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=16),
            content=content,
            actions=[ft.TextButton("Cancel", on_click=lambda _: self._page_ref.close(dlg))],
        )
        self._page_ref.open(dlg)

    # ── add administrator ───────────────────────────────────────────────────

    def _open_add_admin_dialog(self, mode: str = "promote"):
        """Add an administrator.

        Two modes, because the client holds only the Supabase anon key:
        * **promote** — grant admin to an account that already exists in the cloud.
          This is the only path that produces a *cloud* admin, and it takes effect
          immediately (RLS ``is_admin()`` + the ``protect_profile_role`` trigger
          both allow an admin to change roles).
        * **create** — make a brand-new admin account in this device's local
          database. Needed for offline/local-only use; the cloud side still has to
          be finished by promoting them once they've signed in.
        """
        c = self._c
        snap = self._snapshot

        def switch(to):
            def handler(e):
                tap(self._page_ref)
                self._page_ref.close(dlg)
                self._open_add_admin_dialog(to)
            return handler

        def tab_btn(label, target):
            active = mode == target
            return ft.Container(
                content=ft.Text(label, size=12,
                                weight=ft.FontWeight.BOLD if active else ft.FontWeight.W_500,
                                color="white" if active else c["TEXT2"]),
                padding=ft.padding.symmetric(horizontal=12, vertical=7),
                bgcolor=SECONDARY if active else "transparent",
                border_radius=8, ink=True,
                on_click=None if active else switch(target),
            )

        toggle = ft.Container(
            content=ft.Row([tab_btn("Promote existing", "promote"),
                            tab_btn("Create new", "create")], spacing=4),
            bgcolor=f"{SECONDARY}14", border_radius=10, padding=3,
        )

        if mode == "promote":
            pool = [p for p in snap.accounts if p.get("role") != "admin"]

            def pick(person):
                def handler(e):
                    tap(self._page_ref)
                    self._page_ref.close(dlg)
                    ok, msg = self.admin_service.promote_to_admin(person["id"])
                    self._after_write(ok, "Administrator added" if ok else msg)
                return handler

            if pool:
                items = [
                    ft.Container(
                        content=ft.Row([
                            ft.Icon("person", size=18, color=c["TEXT3"]),
                            ft.Column([
                                ft.Text(_display(p), size=14, weight=ft.FontWeight.BOLD,
                                        color=c["TEXT1"]),
                                ft.Text(f"{p.get('email', '')} · {p.get('role', '')}",
                                        size=11, color=c["TEXT2"]),
                            ], spacing=0, expand=True),
                            ft.Icon("admin_panel_settings", size=20, color=SECONDARY),
                        ], spacing=10),
                        padding=10, border_radius=10, ink=True, on_click=pick(p),
                    )
                    for p in pool
                ]
                body = ft.Column(items, spacing=6, scroll=ft.ScrollMode.AUTO, tight=True,
                                 width=340, height=min(len(items) * 62, 280))
            else:
                body = ft.Container(
                    content=ft.Text("Every cloud account is already an administrator.\n"
                                    "Use \"Create new\" to add another account.",
                                    size=13, color=c["TEXT2"]),
                    width=340, padding=10)
            content = ft.Column([toggle, body], spacing=10, tight=True, width=340)
            actions = [ft.TextButton("Cancel", on_click=lambda _: self._page_ref.close(dlg))]
        else:
            f_name = ft.TextField(label="Full name", dense=True)
            f_user = ft.TextField(label="Username", dense=True)
            f_mail = ft.TextField(label="Email", dense=True, keyboard_type=ft.KeyboardType.EMAIL)
            f_pass = ft.TextField(label="Password", dense=True, password=True,
                                  can_reveal_password=True)
            err = ft.Text("", size=12, color=ERROR, visible=False)
            note = ft.Container(
                content=ft.Row([
                    ft.Icon("info_outline", size=15, color=WARNING_CLR),
                    ft.Text("Creates an admin account on this device. Their cloud role "
                            "starts as teacher when they first sign in online — come "
                            "back and promote them to finish.",
                            size=11, color=c["TEXT2"], expand=True),
                ], spacing=6),
                bgcolor=f"{WARNING_CLR}14", border_radius=8, padding=8, width=340,
            )

            def create(e):
                tap(self._page_ref)
                err.visible = False
                if not self.auth_service:
                    err.value = "Local account creation isn't available here."
                    err.visible = True
                    return self._safe_update()
                try:
                    self.auth_service.create_user_account(
                        (f_name.value or "").strip(),
                        (f_user.value or "").strip(),
                        f_pass.value or "",
                        email=(f_mail.value or "").strip(),
                        role="admin",
                        allow_privileged=True,   # admin may mint a privileged role
                        skip_cloud=True,         # don't hijack this admin's session
                    )
                except ValueError as ex:
                    err.value = str(ex)
                    err.visible = True
                    return self._safe_update()
                except Exception as ex:
                    err.value = f"Failed: {str(ex)[:70]}"
                    err.visible = True
                    return self._safe_update()
                self._page_ref.close(dlg)
                self._after_write(True, "Local admin account created")

            content = ft.Column([toggle, note, f_name, f_user, f_mail, f_pass, err],
                                spacing=9, tight=True, width=340)
            actions = [
                ft.TextButton("Cancel", on_click=lambda _: self._page_ref.close(dlg)),
                ft.ElevatedButton("Create", bgcolor=SECONDARY, color="white", on_click=create),
            ]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add administrator", size=16),
            content=content,
            actions=actions,
        )
        self._page_ref.open(dlg)

    def _after_write(self, ok, msg):
        if ok:
            success(self._page_ref)
        else:
            warning(self._page_ref)
        self._page_ref.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=SUCCESS_CLR if ok else ERROR)
        self._page_ref.snack_bar.open = True
        self._safe_update()
        if ok:
            self._reload()  # re-pull the snapshot so the change is reflected


def _display(profile) -> str:
    if not profile:
        return "Unknown"
    return ((profile.get("full_name") or "").strip()
            or (profile.get("username") or "").strip()
            or (profile.get("email") or "").strip() or "Unknown")


def _display_name(profile) -> str:
    return _display(profile)
