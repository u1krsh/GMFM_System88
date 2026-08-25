"""
MotorMeasure - GMFM Assessment App
Main application module — imported by src/main.py
"""
"""flet build apk --product MotorMeasure --project MotorMeasure --org com.motormeasure --verbose"""

"""adb install -r D:\PROGRAM\COMPRO\GMFM\GMFM_System88\src\build\apk\app-release.apk"""

import sys
import os
import base64
import threading
import traceback
from pathlib import Path


def _log(msg):
    try:
        print(f"[GMFM_APP] {msg}", flush=True)
    except Exception:
        pass


# Ensure the src directory is on sys.path so gmfm_app package is importable
try:
    FILE_PATH = Path(__file__).resolve()
    SRC_DIR = FILE_PATH.parents[1]
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
except Exception:
    pass

import flet as ft


def _make_error_view(route: str, error_msg: str, stack_trace: str = "") -> ft.View:
    """Create an error View (works with views-based routing)."""
    return ft.View(
        route=route,
        bgcolor="#FEE2E2",
        scroll=ft.ScrollMode.AUTO,
        padding=0,
        controls=[
            ft.SafeArea(
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon("error_outline", size=60, color="#DC2626"),
                        ft.Text("App Error", size=22, weight=ft.FontWeight.BOLD, color="#991B1B"),
                        ft.Container(height=10),
                        ft.Text(str(error_msg), size=14, color="#7F1D1D"),
                        ft.Container(height=10),
                        ft.Container(
                            content=ft.Text(stack_trace, size=10, color="#6B7280", selectable=True),
                            bgcolor="#FFFFFF",
                            padding=10,
                            border_radius=8,
                        ) if stack_trace else ft.Container(),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
                    padding=30,
                ),
                expand=True,
            )
        ],
    )


def show_error_page(page: ft.Page, error_msg: str, stack_trace: str = ""):
    """Display an error message — works whether views routing is active or not."""
    try:
        page.views.clear()
        page.views.append(_make_error_view(page.route or "/", error_msg, stack_trace))
        page.update()
    except Exception:
        # Absolute last-resort fallback — use controls
        try:
            page.controls.clear()
            page.controls.append(
                ft.SafeArea(
                    ft.Container(
                        ft.Column([
                            ft.Text("MotorMeasure Error", size=20, weight=ft.FontWeight.BOLD),
                            ft.Text(str(error_msg), size=13),
                        ]),
                        padding=30,
                    ),
                    expand=True,
                )
            )
            page.update()
        except Exception:
            pass


# Import with error handling — deferred so we can always show errors
IMPORTS_OK = False
IMPORT_ERROR = None

try:
    _log("Importing app modules...")
    from gmfm_app.data.database import DatabaseContext
    _log("  database OK")
    from gmfm_app.views.dashboard_view import DashboardView
    _log("  dashboard_view OK")
    from gmfm_app.views.student_view import StudentView
    _log("  student_view OK")
    from gmfm_app.views.scoring_view import ScoringView
    _log("  scoring_view OK")
    from gmfm_app.views.session_view import SessionHistoryView, SessionDetailView, CompareView
    _log("  session_view OK")
    from gmfm_app.views.settings_view import SettingsView
    _log("  settings_view OK")
    from gmfm_app.views.admin_view import AdminConsoleView
    _log("  admin_view OK")
    from gmfm_app.views.parent_view import ParentDashboardView
    _log("  parent_view OK")
    from gmfm_app.views.login_view import LoginView
    _log("  login_view OK")
    from gmfm_app.services.auth_service import AuthService
    _log("  auth_service OK")
    from gmfm_app.services.access_service import AccessService
    _log("  access_service OK")
    from gmfm_app.services.ui_scale import apply_android_scale
    _log("  ui_scale OK")
    IMPORTS_OK = True
    _log("All imports successful")
except Exception as e:
    IMPORT_ERROR = (str(e), traceback.format_exc())
    _log(f"IMPORT FAILED: {e}")
    _log(traceback.format_exc())


# Theme colors
class Theme:
    DARK_BG = "#0F172A"
    LIGHT_BG = "#F8FAFC"
    PRIMARY = "#0D9488"


def _load_image_b64(relative_path: str) -> str:
    """Load an image from src/ directory as a base64 string. Tries multiple paths for Android compatibility."""
    candidates = [
        SRC_DIR / relative_path,
        Path(os.getcwd()) / relative_path,
        Path(__file__).resolve().parent / relative_path,
        Path(__file__).resolve().parent.parent / relative_path,
    ]
    for img_path in candidates:
        try:
            if img_path.exists():
                _log(f"Found image at: {img_path}")
                return base64.b64encode(img_path.read_bytes()).decode("utf-8")
        except Exception:
            pass
    _log(f"Failed to load image {relative_path} from any path")
    return ""


def _build_splash():
    """Build the splash screen with animated logo slot + static app logo."""
    # Use embedded base64 constants — file-based loading fails on Android
    from gmfm_app.splash_assets import LOGO1_B64, LOGO2_B64, APP_IMG_B64
    logo1_b64 = LOGO1_B64
    logo2_b64 = LOGO2_B64
    app_img_b64 = APP_IMG_B64

    # Logo containers with fade animation — we'll swap visibility via opacity
    logo1 = ft.Container(
        content=ft.Image(src_base64=logo1_b64, width=110, height=110, fit=ft.ImageFit.CONTAIN)
        if logo1_b64 else ft.Container(width=110, height=110),
        opacity=1,
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
    )
    logo2 = ft.Container(
        content=ft.Image(src_base64=logo2_b64, width=110, height=110, fit=ft.ImageFit.CONTAIN)
        if logo2_b64 else ft.Container(width=110, height=110),
        opacity=0,
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
    )

    # Stack both logos on top of each other so the swap looks clean
    logo_slot = ft.Container(
        content=ft.Stack([logo1, logo2]),
        width=120, height=120,
        alignment=ft.alignment.center,
    )

    splash = ft.Container(
        content=ft.Column(
            [
                ft.Container(height=40),
                logo_slot,
                ft.Container(height=20),
                ft.Image(src_base64=app_img_b64, width=160, height=160, fit=ft.ImageFit.CONTAIN)
                if app_img_b64 else ft.Container(width=160, height=160),
                ft.Container(height=20),
                ft.Text("MotorMeasure", size=32, weight=ft.FontWeight.BOLD, color="#1E293B"),
                ft.Text("GMFM Assessment System", size=14, color="#64748B"),
                ft.Container(height=30),
                ft.ProgressRing(color="#0D9488", width=30, height=30, stroke_width=3),
                ft.Container(height=10),
                ft.Text("Loading...", size=12, color="#94A3B8"),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor="#FFFFFF",
        expand=True,
        alignment=ft.alignment.center,
        animate_opacity=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT),
    )

    return splash, logo1, logo2


class GMFMApp:
    def __init__(self, page: ft.Page, db_context=None):
        _log("GMFMApp.__init__ starting")
        self.page = page
        self.page.title = "MotorMeasure"
        self._navigating_back = False
        self._nav_lock = False  # Prevent concurrent navigation
        
        # Mobile optimizations — restore saved theme preference
        try:
            saved_dark = self.page.client_storage.get("dark_mode")
        except Exception:
            saved_dark = False
        if saved_dark:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = Theme.DARK_BG
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = Theme.LIGHT_BG
        self.page.padding = 0
        
        # Set status bar theme
        self.page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=Theme.PRIMARY,
                surface=Theme.DARK_BG if saved_dark else Theme.LIGHT_BG,
            ),
        )
        
        # Disable scroll on page level (views handle their own scroll)
        self.page.scroll = None
        
        # Route handling
        self.page.on_route_change = self.route_change
        self.page.on_view_pop = self.view_pop
        
        # Navigation history for back button
        self.route_history = ["/"]
        
        # Init database — use pre-loaded context or create new one
        try:
            if db_context is not None:
                self.db_context = db_context
                _log("Using pre-loaded DatabaseContext")
            else:
                _log("Initializing DatabaseContext...")
                self.db_context = DatabaseContext()
                _log("DatabaseContext ready")
        except Exception as e:
            _log(f"DatabaseContext FAILED: {e}")
            self.page.views.clear()
            self.page.views.append(
                _make_error_view("/", f"Database init failed: {e}", traceback.format_exc())
            )
            self.page.update()
            return

        self.auth_service = AuthService(self.db_context)

        # Init cloud sync service (non-blocking)
        self.sync_service = None
        self.sync_worker = None
        try:
            from gmfm_app.services.sync_config import load_config
            from gmfm_app.services.sync_service import SyncService
            from gmfm_app.services.sync_worker import SyncWorker
            sync_config = load_config(self.page)
            if sync_config.is_configured():
                self.sync_service = SyncService(self.db_context, sync_config)
                self.sync_worker = SyncWorker(self.sync_service, interval_seconds=60)
                self.sync_worker.start()
                _log("Cloud sync service initialized")
            else:
                self.sync_service = SyncService(self.db_context, sync_config)
                _log("Cloud sync service created (not configured)")
            # Give auth_service access to the sync service for cloud auth
            self.auth_service.sync_service = self.sync_service

            # Re-authenticate to Supabase if user is already logged in locally
            # (session doesn't persist across app restarts)
            try:
                current = self.auth_service.current_user(self.page)
                if current and self.sync_service:
                    user_email = (getattr(current, 'email', '') or '').strip()
                    if user_email:
                        # Always align sync_config with the actual logged-in user's email,
                        # overwriting any stale address from a previous session in client_storage.
                        if self.sync_service.config.cloud_email != user_email:
                            _log(f"Aligning sync email: '{self.sync_service.config.cloud_email}' -> '{user_email}'")
                            self.sync_service.config.cloud_email = user_email
                            from gmfm_app.services.sync_config import save_config
                            save_config(self.page, self.sync_service.config)

                        if not self.sync_service.ensure_auth():
                            _log(f"Session expired for {user_email}. Will re-auth on next login.")
                        else:
                            _log(f"Restored cloud session for {user_email}")
            except Exception as e:
                _log(f"Cloud re-auth check skipped: {e}")

        except Exception as e:
            _log(f"Sync service init skipped: {e}")
        
        _log("Navigating to /")
        self.page.go("/")

    def _handle_back(self):
        """Navigate back or allow exit if on home."""
        if self.page.route == "/" or self.page.route == "":
            return False
        
        if len(self.route_history) > 1:
            self.route_history.pop()
            prev_route = self.route_history[-1] if self.route_history else "/"
            self._navigating_back = True
            self.page.go(prev_route)
            return True
        else:
            self._navigating_back = True
            self.page.go("/")
            return True

    def route_change(self, route):
        # Prevent concurrent navigation (fixes "back too fast = blank screen")
        if self._nav_lock:
            return
        self._nav_lock = True
        try:
            is_back = self._navigating_back
            self._navigating_back = False  # Reset AFTER reading it

            if not is_back:
                # Forward navigation — track history
                if not self.route_history or self.route_history[-1] != self.page.route:
                    self.route_history.append(self.page.route)
                # Keep history manageable
                if len(self.route_history) > 20:
                    self.route_history = self.route_history[-10:]

            self._handle_route(is_back)
        except Exception as e:
            # Use views-based error display (not page.controls)
            try:
                self.page.views.clear()
                self.page.views.append(
                    _make_error_view(self.page.route or "/", f"Navigation error: {e}", traceback.format_exc())
                )
                self.page.update()
            except Exception:
                show_error_page(self.page, f"Navigation error: {e}", traceback.format_exc())
        finally:
            self._nav_lock = False

    def _create_view(self, route: str):
        """Create a view for the given route with role-based access control."""
        try:
            is_dark = self.page.theme_mode == ft.ThemeMode.DARK
            current_user = self.auth_service.current_user(self.page)
            user_id = int(current_user.id) if current_user and current_user.id else None
            user_role = getattr(current_user, 'role', 'teacher') if current_user else 'teacher'

            if route.startswith("/login"):
                return LoginView(self.page, self.auth_service, is_dark)

            # ── Role-based route guards ────────────────────────────
            # Admin console: admins only.
            if route.startswith("/admin") and user_role != "admin":
                return self._access_denied_view(route, "The admin console is restricted to administrators")

            # Sponsor: only dashboard (aggregate stats)
            if user_role == "sponsor" and route != "/":
                return self._access_denied_view(route, "Sponsors can only view aggregate statistics")

            # Parent: dashboard + session detail (read-only)
            if user_role == "parent":
                allowed = route == "/" or route.startswith("/session") or route.startswith("/history") or route.startswith("/student") or route.startswith("/settings")
                if not allowed:
                    return self._access_denied_view(route, "Parents can view progress but cannot create or modify data")

            # Determine data scope via the unified access model.
            # admin  -> visible_ids=None (unrestricted local read), can_write=True
            # teacher-> owned ∪ co-taught ids, can_write=True
            # parent -> only linked ids, can_write=False (read-only)
            scope = AccessService(self.db_context).scope_for(current_user)

            # Parents hold no local data — give them a cloud-direct, read-only
            # dashboard of the children linked to them (Phase 3).
            if user_role == "parent" and route == "/":
                return ParentDashboardView(self.page, self.db_context, is_dark,
                                           sync_service=self.sync_service, current_user=current_user)

            # ── Build views ────────────────────────────────────────
            if route == "/":
                return DashboardView(self.page, self.db_context, is_dark,
                                     current_user=current_user, user_id=scope.user_id,
                                     visible_ids=scope.visible_ids, can_write=scope.can_write, unrestricted=scope.unrestricted)
            elif route.startswith("/admin"):
                return AdminConsoleView(self.page, self.db_context, is_dark,
                                        auth_service=self.auth_service,
                                        sync_service=self.sync_service, current_user=current_user)
            elif route.startswith("/student"):
                pid = self._param_from_route(route, "id")
                return StudentView(self.page, self.db_context, is_dark,
                                   int(pid) if pid else None, user_id=scope.user_id,
                                   current_user=current_user,
                                   visible_ids=scope.visible_ids, can_write=scope.can_write, unrestricted=scope.unrestricted)
            elif route == "/settings":
                return SettingsView(self.page, self.db_context, is_dark,
                                   auth_service=self.auth_service,
                                   sync_service=self.sync_service, user_id=scope.user_id,
                                   visible_ids=scope.visible_ids, can_write=scope.can_write, unrestricted=scope.unrestricted)
            elif route.startswith("/scoring"):
                pid = self._param_from_route(route, "student_id")
                sid = self._param_from_route(route, "session_id")
                scale = self._param_from_route(route, "scale") or "88"
                if pid:
                    return ScoringView(self.page, self.db_context, int(pid),
                                       int(sid) if sid else None, is_dark, scale,
                                       user_id=scope.user_id,
                                       visible_ids=scope.visible_ids, can_write=scope.can_write, unrestricted=scope.unrestricted)
            elif route.startswith("/history"):
                pid = self._param_from_route(route, "student_id")
                if pid:
                    return SessionHistoryView(self.page, self.db_context, int(pid), is_dark,
                                              user_id=scope.user_id,
                                              visible_ids=scope.visible_ids, can_write=scope.can_write, unrestricted=scope.unrestricted)
            elif route.startswith("/compare"):
                s1 = self._param_from_route(route, "session1")
                s2 = self._param_from_route(route, "session2")
                if s1 and s2:
                    return CompareView(self.page, self.db_context, int(s1), int(s2), is_dark,
                                       user_id=scope.user_id,
                                       visible_ids=scope.visible_ids, can_write=scope.can_write, unrestricted=scope.unrestricted)
            elif route.startswith("/session"):
                sid = self._param_from_route(route, "session_id")
                if sid:
                    return SessionDetailView(self.page, self.db_context, int(sid), is_dark,
                                             user_id=scope.user_id,
                                             visible_ids=scope.visible_ids, can_write=scope.can_write, unrestricted=scope.unrestricted)
            return None
        except Exception as e:
            return _make_error_view(route, f"View error ({route}): {e}", traceback.format_exc())

    def _access_denied_view(self, route: str, message: str):
        """Create a view showing access denied for the user's role."""
        c = self._c if hasattr(self, '_c') else {"TEXT1": "#0F172A", "TEXT2": "#475569"}
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        bg = "#0F172A" if is_dark else "#F8FAFC"
        text1 = "#F8FAFC" if is_dark else "#0F172A"
        text2 = "#94A3B8" if is_dark else "#475569"
        return ft.View(
            route=route, bgcolor=bg, padding=0,
            controls=[ft.SafeArea(
                content=ft.Container(
                    content=ft.Column([
                        ft.Container(height=60),
                        ft.Icon("lock_outline", size=64, color="#F59E0B"),
                        ft.Container(height=16),
                        ft.Text("Access Restricted", size=22,
                                weight=ft.FontWeight.BOLD, color=text1),
                        ft.Container(height=8),
                        ft.Text(message, size=14, color=text2,
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(height=24),
                        ft.Container(
                            content=ft.Text("Go Back", color="white",
                                            weight=ft.FontWeight.BOLD, size=14),
                            height=44, bgcolor="#0D9488", border_radius=12,
                            alignment=ft.alignment.center, width=160,
                            on_click=lambda _: self.page.go("/"),
                            ink=True,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=30, expand=True, alignment=ft.alignment.center,
                ),
                expand=True,
            )],
        )

    def _create_scaled_view(self, route: str):
        """Create a route view and apply Android accessibility scale when needed."""
        view = self._create_view(route)
        if view is not None:
            try:
                apply_android_scale(self.page, view)
            except Exception as e:
                _log(f"Scaling failed for {route}: {e}")
        return view

    def _param_from_route(self, route: str, key: str):
        """Extract a parameter from a route string."""
        try:
            return dict(p.split("=") for p in route.split("?")[1].split("&")).get(key)
        except Exception:
            return None

    def _handle_route(self, is_back=False):
        """Build/update the view stack efficiently."""
        try:
            current_route = self.page.route or "/"

            # All routes are protected except /login.
            is_public_route = current_route.startswith("/login")
            is_authenticated = self.auth_service.is_authenticated(self.page)

            if not is_authenticated and not is_public_route:
                self.page.route = "/login"
                self.route_history = ["/login"]
                self.page.views.clear()
                self.page.views.append(self._create_scaled_view("/login"))
                self.page.update()
                return

            if is_authenticated and is_public_route:
                self.page.route = "/"
                current_route = "/"
                self.route_history = ["/"]
                self.page.views.clear()
                self.page.views.append(self._create_scaled_view("/"))
                self.page.update()
                return
            
            if is_back:
                # Back navigation — just pop the top view, don't rebuild
                if len(self.page.views) > 1:
                    self.page.views.pop()
                else:
                    # Stack is empty or single — rebuild the target view
                    view = self._create_scaled_view(current_route)
                    if view:
                        self.page.views.clear()
                        self.page.views.append(view)
            else:
                # Forward navigation — only create the NEW view and append
                if not self.page.views:
                    # First load — create the initial view
                    view = self._create_scaled_view(current_route)
                    if view:
                        self.page.views.append(view)
                else:
                    # Append new view on top of existing stack
                    view = self._create_scaled_view(current_route)
                    if view:
                        self.page.views.append(view)
        except Exception as e:
            # Ensure at least an error view is visible
            self.page.views.clear()
            self.page.views.append(
                _make_error_view(self.page.route or "/", f"Navigation error: {e}", traceback.format_exc())
            )
        
        # Guarantee at least one view exists
        if not self.page.views:
            self.page.views.append(
                _make_error_view("/", "No view could be created. Check app data files.")
            )
        
        self.page.update()

    def view_pop(self, e):
        """Handle view pop - triggered by Android gesture back button."""
        # If only one view (home), let app close
        if len(self.page.views) <= 1:
            return

        # Prevent concurrent navigation
        if self._nav_lock:
            return
        self._nav_lock = True

        try:
            # Pop the top view
            self.page.views.pop()

            # Update route history
            if len(self.route_history) > 1:
                self.route_history.pop()

            # Clean up stale overlays to prevent memory leaks
            self.page.overlay.clear()

            # Update the route to match top view
            if self.page.views:
                top_view = self.page.views[-1]
                # Update route without triggering route_change
                self.page.route = top_view.route

            self.page.update()
        finally:
            self._nav_lock = False

    def _param(self, key):
        try:
            return dict(p.split("=") for p in self.page.route.split("?")[1].split("&")).get(key)
        except Exception:
            return None


def _is_mobile() -> bool:
    """Detect if running on Android/iOS (serious_python runtime)."""
    return sys.platform not in ("win32", "darwin", "linux") or os.getenv("FLET_PLATFORM") in ("android", "ios")


def main(page: ft.Page):
    """Entry point — called by src/main.py with the Flet page."""
    _log("gmfm_app.main.main() called")
    
    # Check if imports succeeded
    if not IMPORTS_OK:
        _log(f"Showing import error: {IMPORT_ERROR[0]}")
        show_error_page(page, IMPORT_ERROR[0], IMPORT_ERROR[1])
        return
    
    try:
        if _is_mobile():
            # On Android/iOS: src/main.py already shows the splash with logos.
            # Just init DB and launch the app — splash stays visible until GMFMApp calls page.go("/").
            _log("Mobile platform detected — init DB and launch")
            try:
                db_ctx = DatabaseContext()
                _log("DatabaseContext ready")
            except Exception as e:
                show_error_page(page, f"Database init failed: {e}", traceback.format_exc())
                return
            GMFMApp(page, db_context=db_ctx)
            _log("GMFMApp initialized successfully")
        else:
            # Desktop: show animated splash with logo sequence
            page.bgcolor = "#FFFFFF"
            page.padding = 0
            splash, logo1, logo2 = _build_splash()
            page.add(splash)
            _log("Splash screen shown")

            # Initialize database in background thread
            db_result = [None, None]  # [context, error]

            def _init_db():
                try:
                    db_result[0] = DatabaseContext()
                    _log("Background: DatabaseContext ready")
                except Exception as e:
                    db_result[1] = (str(e), traceback.format_exc())

            db_thread = threading.Thread(target=_init_db, daemon=True)
            db_thread.start()

            # Animate logo sequence then transition to app
            def _animate_and_finish():
                import time

                # Logo 1 visible for 1.5s
                time.sleep(1.5)

                # Fade out logo 1, fade in logo 2
                logo1.opacity = 0
                logo2.opacity = 1
                page.update()

                # Logo 2 visible for 1.5s
                time.sleep(1.5)

                # Wait for DB init to complete
                db_thread.join(timeout=15)

                # Fade out entire splash
                splash.opacity = 0
                page.update()
                time.sleep(0.7)

                # Clear splash and launch app
                page.controls.clear()
                page.update()

                if db_result[1]:
                    show_error_page(page, f"Database init failed: {db_result[1][0]}", db_result[1][1])
                    return

                if db_result[0] is None:
                    show_error_page(page, "Database initialization timed out")
                    return

                GMFMApp(page, db_context=db_result[0])
                _log("GMFMApp initialized successfully")

            # Start the animation sequence immediately in a background thread
            threading.Thread(target=_animate_and_finish, daemon=True).start()

    except Exception as e:
        _log(f"GMFMApp init FAILED: {e}")
        _log(traceback.format_exc())
        show_error_page(page, str(e), traceback.format_exc())


# Only call ft.app() when running this file directly (desktop dev mode)
# When imported by src/main.py (Android), main() is called with the page
if __name__ == "__main__":
    ft.app(target=main, assets_dir=str(SRC_DIR))
