"""
Dashboard - With Recent Activity and Quick Actions
"""
import flet as ft
from datetime import datetime
from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.repositories import StudentRepository, SessionRepository
from gmfm_app.services.haptics import tap, select, success, warning
from gmfm_app.services.docx_import_service import parse_docx, import_assessment_to_db


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
SECONDARY = "#7C3AED"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
ERROR = "#EF4444"
INFO = "#3B82F6"


def get_greeting(display_name: str | None = None):
    """Return a time-appropriate greeting, optionally personalized."""
    hour = datetime.now().hour
    if hour < 12:
        base = "Good Morning"
    elif hour < 17:
        base = "Good Afternoon"
    else:
        base = "Good Evening"

    if display_name:
        return f"{base}, {display_name}!"
    return f"{base}!"


class DashboardView(ft.View):
    def __init__(self, page: ft.Page, db_context: DatabaseContext, is_dark: bool = False, current_user=None, user_id=None):
        c = get_colors(is_dark)
        super().__init__(route="/", padding=0, bgcolor=c["BG"], scroll=ft.ScrollMode.AUTO)
        self._page_ref = page
        self.db_context = db_context
        self.repo = StudentRepository(db_context, user_id=user_id)
        self.session_repo = SessionRepository(db_context, user_id=user_id)
        self.c = c
        self.search_term = ""  # For search highlighting

        display_name = None
        if current_user is not None:
            full_name = (getattr(current_user, "full_name", "") or "").strip()
            username = (getattr(current_user, "username", "") or "").strip()
            display_name = full_name.split(" ")[0] if full_name else username

        # Header with search
        self.search = ft.TextField(
            hint_text="Search students...",
            prefix_icon="search",
            border_radius=12,
            bgcolor=c["CARD"],
            border_color=c["BORDER"],
            focused_border_color=PRIMARY,
            color=c["TEXT1"],
            hint_style=ft.TextStyle(color=c["TEXT3"]),
            height=46,
            expand=True,
            on_change=self.filter_students,
            suffix=ft.IconButton(
                icon="close",
                icon_size=18,
                icon_color=c["TEXT3"],
                on_click=self._clear_search,
                visible=False,
            ),
        )

        header = ft.SafeArea(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Text("M", size=22, weight=ft.FontWeight.BOLD, color="white"),
                            width=46, height=46,
                            bgcolor=PRIMARY,
                            border_radius=12,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(width=10),
                        ft.Column([
                            ft.Text(get_greeting(display_name), size=14, color=c["TEXT2"]),
                            ft.Text("MotorMeasure", size=22, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                        ], spacing=0, expand=True),
                        self._build_sync_indicator(c),
                        ft.IconButton("settings", icon_color=c["TEXT2"], on_click=lambda _: self._page_ref.go("/settings")),
                    ]),
                    ft.Container(height=12),
                    self.search,
                ]),
                padding=ft.padding.only(left=16, right=16, top=8, bottom=12),
                bgcolor=c["CARD"],
                border=ft.border.only(bottom=ft.BorderSide(1, c["BORDER"])),
            ),
            minimum_padding=ft.padding.only(top=10),
            bottom=False,
        )

        # Stats
        self.stat_students = ft.Text("0", size=20, weight=ft.FontWeight.BOLD, color=c["TEXT1"], no_wrap=True)
        self.stat_sessions = ft.Text("0", size=20, weight=ft.FontWeight.BOLD, color=c["TEXT1"], no_wrap=True)
        self.stat_avg = ft.Text("0%", size=20, weight=ft.FontWeight.BOLD, color=c["TEXT1"], no_wrap=True)
        
        stats_row = ft.Container(
            content=ft.Row([
                self._stat_card("Students", self.stat_students, "people", PRIMARY),
                self._stat_card("Sessions", self.stat_sessions, "assessment", SECONDARY),
                self._stat_card("Avg", self.stat_avg, "trending_up", SUCCESS),
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
        )

        # Quick Actions
        actions = ft.Container(
            content=ft.Row([
                self._action("person_add", "New Student", PRIMARY, lambda _: self._page_ref.go("/student")),
                self._action("file_upload", "Import DOCX", SECONDARY, self._import_docx),
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=20, vertical=5),
        )

        # Recent Activity Section
        self.recent_list = ft.Column(spacing=8)
        recent_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon("history", color=c["TEXT2"], size=18),
                    ft.Text("Recent Activity", size=16, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                ], spacing=8),
                ft.Container(height=10),
                self.recent_list,
            ]),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
        )

        # Tip of the day
        tip_card = self._build_tip_card()

        # Students Section
        self.student_list = ft.Column(spacing=8)

        self.controls = [
            header,
            stats_row,
            actions,
            recent_section,
            tip_card,
            ft.Container(
                content=ft.Text("Students", size=18, weight=ft.FontWeight.BOLD, color=c["TEXT1"]),
                padding=ft.padding.only(left=20, bottom=8, top=8),
            ),
            ft.Container(
                content=self.student_list, 
                padding=ft.padding.only(left=20, right=20, bottom=100),  # Bottom padding for nav bar
            ),
        ]

        self.load_students()

    def _load_recent_activity(self):
        """Load last 3 sessions across all students — single SQL query."""
        c = self.c
        recent = self.session_repo.get_recent_sessions(limit=3)
        
        self.recent_list.controls.clear()
        
        if not recent:
            self.recent_list.controls.append(
                ft.Text("No recent activity", size=13, color=c["TEXT3"])
            )
        else:
            for item in recent:
                sess = item["session"]
                given = item["given_name"] or ""
                family = item["family_name"] or ""
                score = sess.total_score or 0
                color = SUCCESS if score >= 70 else WARNING if score >= 40 else ERROR
                self.recent_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text(f"{score:.0f}%", size=12, weight=ft.FontWeight.BOLD, color="white"),
                                width=42, height=42,
                                bgcolor=color,
                                border_radius=10,
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(width=10),
                            ft.Column([
                                ft.Text(f"{given} {family}", size=13, weight=ft.FontWeight.W_600, color=c["TEXT1"], no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(sess.created_at.strftime("%b %d, %H:%M"), size=11, color=c["TEXT3"], no_wrap=True),
                            ], spacing=2, expand=True),
                            ft.Icon("chevron_right", color=c["TEXT3"], size=18),
                        ]),
                        padding=12,
                        bgcolor=c["CARD"],
                        border_radius=12,
                        border=ft.border.all(1, c["BORDER"]),
                        on_click=lambda _, sid=sess.id: self._page_ref.go(f"/session?session_id={sid}"),
                        ink=True,
                    )
                )

    def _stat_card(self, title, value_widget, icon, color):
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon(icon, color=color, size=20),
                    width=36, height=36,
                    bgcolor=f"{color}20",
                    border_radius=10,
                    alignment=ft.alignment.center,
                ),
                ft.Container(height=6),
                value_widget,
                ft.Text(title, size=11, color=self.c["TEXT2"], no_wrap=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=12,
            bgcolor=self.c["CARD"],
            border_radius=14,
            border=ft.border.all(1, self.c["BORDER"]),
            expand=True,
        )

    def _action(self, icon, text, color, on_click):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color="white", size=20),
                ft.Container(width=8),
                ft.Text(text, color="white", weight=ft.FontWeight.BOLD, size=14),
            ]),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            bgcolor=color,
            border_radius=12,
            on_click=on_click,
            ink=True,
        )

    def _build_sync_indicator(self, c):
        """Build a small cloud sync status icon for the header."""
        try:
            from gmfm_app.services.sync_config import load_config
            config = load_config(self._page_ref)
            if not config.is_configured():
                return ft.Container()  # Empty — no indicator if not configured

            # Try to get pending count from sync_queue directly
            pending = 0
            try:
                with self.db_context.connect() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM sync_queue WHERE synced = 0")
                    row = cur.fetchone()
                    pending = int(row[0]) if row else 0
            except Exception:
                pass

            if pending > 0:
                return ft.Container(
                    content=ft.Stack([
                        ft.Icon("cloud_upload", color="#F59E0B", size=22),
                        ft.Container(
                            content=ft.Text(str(pending), size=8, weight=ft.FontWeight.BOLD, color="white"),
                            width=16, height=16,
                            bgcolor="#EF4444",
                            border_radius=8,
                            alignment=ft.alignment.center,
                            top=0, right=0,
                        ),
                    ], width=28, height=28),
                    on_click=lambda _: self._page_ref.go("/settings"),
                    tooltip=f"{pending} pending syncs",
                )
            else:
                is_logged_in = config.is_logged_in()
                return ft.Container(
                    content=ft.Icon(
                        "cloud_done" if is_logged_in else "cloud_off",
                        color="#10B981" if is_logged_in else c["TEXT3"],
                        size=22,
                    ),
                    on_click=lambda _: self._page_ref.go("/settings"),
                    tooltip="Cloud synced" if is_logged_in else "Cloud not connected",
                )
        except Exception:
            return ft.Container()  # Graceful fallback

    def _build_tip_card(self):
        """Build a motivational tip card that changes based on data."""
        import random
        c = self.c
        
        tips = [
            ("💡", "Tip", "Consistent practice leads to better motor function outcomes."),
            ("📊", "Insight", "Regular assessments help track progress over time."),
            ("🎯", "Focus", "Set small, achievable goals for each therapy session."),
            ("🌟", "Motivation", "Every improvement, no matter how small, is progress!"),
            ("📝", "Documentation", "Detailed session notes help identify patterns."),
            ("👨‍👩‍👧", "Family", "Involve caregivers for better therapy outcomes."),
        ]
        
        tip = random.choice(tips)
        
        return ft.Container(
            content=ft.Row([
                ft.Text(tip[0], size=28),
                ft.Container(width=12),
                ft.Column([
                    ft.Text(tip[1], size=12, weight=ft.FontWeight.BOLD, color=PRIMARY),
                    ft.Text(tip[2], size=13, color=c["TEXT1"]),
                ], spacing=2, expand=True),
            ]),
            padding=16,
            margin=ft.margin.symmetric(horizontal=20, vertical=8),
            bgcolor=f"{PRIMARY}10",
            border_radius=14,
            border=ft.border.all(1, f"{PRIMARY}30"),
        )

    def load_students(self):
        self.all_students = self.repo.list_students(limit=100)
        self._update_stats()
        self._load_recent_activity()
        # Pre-fetch latest sessions for all students in one query
        self._latest_sessions = self.session_repo.get_latest_session_per_student()
        self._render(self.all_students)

    def _update_stats(self):
        self.stat_students.value = str(len(self.all_students))
        stats = self.session_repo.get_dashboard_stats()
        self.stat_sessions.value = str(stats["total_sessions"])
        avg = stats["avg_score"]
        self.stat_avg.value = f"{avg:.0f}%" if stats["total_sessions"] > 0 else "N/A"

    def filter_students(self, e):
        term = self.search.value.lower()
        self.search_term = term  # Store for highlighting
        # Show/hide clear button
        self.search.suffix.visible = bool(term)
        self.search.update()
        
        if not term:
            self._render(self.all_students)
        else:
            filtered = [s for s in self.all_students if term in f"{s.given_name} {s.family_name}".lower()]
            self._render(filtered)
        self.student_list.update()

    def _clear_search(self, e):
        """Clear the search field and show all students."""
        self.search.value = ""
        self.search_term = ""
        self.search.suffix.visible = False
        self.search.update()
        self._render(self.all_students)
        self.student_list.update()

    def _highlight_text(self, text, term, c):
        """Return text with search term highlighted."""
        if not term:
            return ft.Text(text, size=14, weight=ft.FontWeight.W_600, color=c["TEXT1"], no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1)
        
        lower_text = text.lower()
        lower_term = term.lower()
        
        if lower_term not in lower_text:
            return ft.Text(text, size=14, weight=ft.FontWeight.W_600, color=c["TEXT1"], no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1)
        
        idx = lower_text.find(lower_term)
        before = text[:idx]
        match = text[idx:idx+len(term)]
        after = text[idx+len(term):]
        
        return ft.Row([
            ft.Text(before, size=14, weight=ft.FontWeight.W_600, color=c["TEXT1"], no_wrap=True),
            ft.Container(
                content=ft.Text(match, size=14, weight=ft.FontWeight.BOLD, color=PRIMARY),
                bgcolor=f"{PRIMARY}20",
                border_radius=4,
                padding=ft.padding.symmetric(horizontal=2),
            ),
            ft.Text(after, size=14, weight=ft.FontWeight.W_600, color=c["TEXT1"], no_wrap=True),
        ], spacing=0, tight=True)

    def _render(self, students):
        self.student_list.controls.clear()
        c = self.c
        
        if not students:
            self.student_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("person_search", size=60, color=c["TEXT3"]),
                        ft.Text("No students found", size=16, color=c["TEXT2"]),
                        ft.TextButton("Add New Student", on_click=lambda _: self._page_ref.go("/student")),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            for s in students:
                latest = getattr(self, '_latest_sessions', {}).get(s.id)
                has_session = latest is not None
                score_val = latest.total_score if latest and latest.total_score is not None else 0
                last_score = f"{score_val:.0f}%" if latest else "New"
                
                # Determine score color
                score_color = c["TEXT2"]
                if latest:
                    score_color = SUCCESS if score_val >= 70 else WARNING if score_val >= 40 else ERROR
                
                self.student_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text(f"{s.given_name[0]}{s.family_name[0]}".upper(), size=14, weight=ft.FontWeight.BOLD, color="white"),
                                width=42, height=42,
                                bgcolor=PRIMARY,
                                border_radius=12,
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(width=8),
                            ft.Column([
                                self._highlight_text(f"{s.given_name} {s.family_name}", self.search_term, c),
                                ft.Row([
                                    ft.Text("Last:", size=10, color=c["TEXT2"]),
                                    ft.Text(last_score, size=10, weight=ft.FontWeight.BOLD, color=score_color),
                                ], spacing=3),
                            ], expand=True, spacing=1),
                            ft.Container(
                                content=ft.Icon("play_arrow", color="white", size=18),
                                width=36, height=36,
                                bgcolor=SUCCESS if has_session else PRIMARY,
                                border_radius=10,
                                alignment=ft.alignment.center,
                                on_click=lambda _, sid=s.id, sess_id=latest.id if latest else None: self._start_scoring(sid, sess_id),
                            ),
                            ft.Container(
                                content=ft.Icon("edit", color=c["TEXT3"], size=18),
                                width=36, height=36,
                                border_radius=10,
                                alignment=ft.alignment.center,
                                on_click=lambda _, sid=s.id: self._page_ref.go(f"/student?id={sid}"),
                            ),
                            ft.Container(
                                content=ft.Icon("history", color=c["TEXT2"], size=18),
                                width=36, height=36,
                                border_radius=10,
                                alignment=ft.alignment.center,
                                on_click=lambda _, sid=s.id: self._page_ref.go(f"/history?student_id={sid}"),
                            ),
                        ], spacing=4),
                        padding=10,
                        bgcolor=c["CARD"],
                        border_radius=12,
                        border=ft.border.all(1, c["BORDER"]),
                        on_click=lambda _, sid=s.id: self._page_ref.go(f"/history?student_id={sid}"),
                        ink=True,
                    )
                )

    def _start_scoring(self, student_id, session_id=None):
        tap(self._page_ref)  # Haptic feedback
        if session_id:
            # Continue existing session
            self._page_ref.go(f"/scoring?student_id={student_id}&session_id={session_id}")
        else:
            # Start new GMFM-88 assessment directly
            self._page_ref.go(f"/scoring?student_id={student_id}&scale=88")

    def _import_docx(self, e):
        """Import student data from one or more DOCX files."""
        tap(self._page_ref)
        
        def on_file_picked(e: ft.FilePickerResultEvent):
            if not e.files:
                return
            
            total_sessions = 0
            total_files = 0
            errors = []
            
            for picked in e.files:
                file_path = picked.path
                try:
                    assessments = parse_docx(file_path)
                    valid = [a for a in assessments if a.is_valid or a.raw_scores]
                    if not valid:
                        errors.append(f"{picked.name}: no valid data found")
                        continue
                    
                    total_files += 1
                    for assessment in valid:
                        import_assessment_to_db(
                            assessment, self.db_context, scale="88", user_id=getattr(self, '_user_id', 1)
                        )
                        total_sessions += 1
                    
                except FileNotFoundError:
                    errors.append(f"{picked.name}: file not found")
                except Exception as ex:
                    errors.append(f"{picked.name}: {str(ex)}")
            
            # Refresh list
            self.load_students()
            self._page_ref.update()
            
            if total_sessions > 0:
                msg = f"Imported {total_sessions} session(s) from {total_files} file(s)"
                if errors:
                    msg += f" ({len(errors)} failed)"
                self._page_ref.snack_bar = ft.SnackBar(
                    ft.Text(msg), bgcolor=SUCCESS
                )
            else:
                self._page_ref.snack_bar = ft.SnackBar(
                    ft.Text(errors[0] if errors else "No data imported"),
                    bgcolor=ERROR
                )
            self._page_ref.snack_bar.open = True
            self._page_ref.update()
        
        # Create and open file picker
        file_picker = ft.FilePicker(on_result=on_file_picked)
        self._page_ref.overlay.append(file_picker)
        self._page_ref.update()
        file_picker.pick_files(
            dialog_title="Select GMFM Assessment DOCX",
            allowed_extensions=["docx"],
            allow_multiple=True,
        )
