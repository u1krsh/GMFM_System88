"""
GMFM Pro - Mobile Optimized (Android/iOS)
Main application module — imported by src/main.py
"""
import sys
import os
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
    """Create an error View (works with views-based routingx)."""
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
                            ft.Text("GMFM Pro Error", size=20, weight=ft.FontWeight.BOLD),
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


class GMFMApp:
    def __init__(self, page: ft.Page):
        _log("GMFMApp.__init__ starting")
        self.page = page
        self.page.title = "GMFM Pro"
        self._navigating_back = False
        
        # Mobile optimizations
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = Theme.LIGHT_BG
        self.page.padding = 0
        
        # Set dark status bar icons for light theme (makes icons visible)
        self.page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=Theme.PRIMARY,
                surface=Theme.LIGHT_BG,
            ),
        )
        
        # Disable scroll on page level (views handle their own scroll)
        self.page.scroll = None
        
        # Route handling
        self.page.on_route_change = self.route_change
        self.page.on_view_pop = self.view_pop
        
        # Navigation history for back button
        self.route_history = ["/"]
        
        # Init database — wrap in try/except
        try:
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
            self._navigating_back = False
            return True
        else:
            self._navigating_back = True  
            self.page.go("/")
            self._navigating_back = False
            return True

    def route_change(self, route):
        try:
            # Track history (avoid duplicates and skip when navigating back)
            if not getattr(self, '_navigating_back', False):
                if not self.route_history or self.route_history[-1] != self.page.route:
                    self.route_history.append(self.page.route)
            # Keep history manageable
            if len(self.route_history) > 20:
                self.route_history = self.route_history[-10:]
            self._handle_route()
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

    def _create_view(self, route: str):
        """Create a view for the given route. Never raises — returns error view on failure."""
        try:
            is_dark = self.page.theme_mode == ft.ThemeMode.DARK
            
            if route == "/":
                return DashboardView(self.page, self.db_context, is_dark)
            elif route.startswith("/student"):
                pid = self._param_from_route(route, "id")
                return StudentView(self.page, self.db_context, is_dark, int(pid) if pid else None)
            elif route == "/settings":
                return SettingsView(self.page, self.db_context)
            elif route.startswith("/scoring"):
                pid = self._param_from_route(route, "student_id")
                sid = self._param_from_route(route, "session_id")
                scale = self._param_from_route(route, "scale") or "88"
                if pid:
                    return ScoringView(self.page, self.db_context, int(pid), int(sid) if sid else None, is_dark, scale)
            elif route.startswith("/history"):
                pid = self._param_from_route(route, "student_id")
                if pid:
                    return SessionHistoryView(self.page, self.db_context, int(pid), is_dark)
            elif route.startswith("/compare"):
                s1 = self._param_from_route(route, "session1")
                s2 = self._param_from_route(route, "session2")
                if s1 and s2:
                    return CompareView(self.page, self.db_context, int(s1), int(s2), is_dark)
            elif route.startswith("/session"):
                sid = self._param_from_route(route, "session_id")
                if sid:
                    return SessionDetailView(self.page, self.db_context, int(sid), is_dark)
            return None
        except Exception as e:
            return _make_error_view(route, f"View error ({route}): {e}", traceback.format_exc())

    def _param_from_route(self, route: str, key: str):
        """Extract a parameter from a route string."""
        try:
            return dict(p.split("=") for p in route.split("?")[1].split("&")).get(key)
        except:
            return None

    def _handle_route(self):
        """Build the view stack based on route history."""
        try:
            if self._navigating_back:
                self.page.views.clear()
                for route in self.route_history:
                    view = self._create_view(route)
                    if view:
                        self.page.views.append(view)
            else:
                # Forward navigation — rebuild from history
                new_views = []
                for route in self.route_history:
                    v = self._create_view(route)
                    if v:
                        new_views.append(v)
                if new_views:
                    self.page.views.clear()
                    self.page.views.extend(new_views)
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
        
        # Pop the top view
        self.page.views.pop()
        
        # Update route history
        if len(self.route_history) > 1:
            self.route_history.pop()
        
        # Update the route to match top view
        if self.page.views:
            top_view = self.page.views[-1]
            # Update route without triggering route_change
            self.page.route = top_view.route
        
        self.page.update()

    def _param(self, key):
        try:
            return dict(p.split("=") for p in self.page.route.split("?")[1].split("&")).get(key)
        except:
            return None


def main(page: ft.Page):
    """Entry point — called by src/main.py with the Flet page."""
    _log("gmfm_app.main.main() called")
    
    # Check if imports succeeded
    if not IMPORTS_OK:
        _log(f"Showing import error: {IMPORT_ERROR[0]}")
        show_error_page(page, IMPORT_ERROR[0], IMPORT_ERROR[1])
        return
    
    try:
        GMFMApp(page)
        _log("GMFMApp initialized successfully")
    except Exception as e:
        _log(f"GMFMApp init FAILED: {e}")
        _log(traceback.format_exc())
        show_error_page(page, str(e), traceback.format_exc())


# Only call ft.app() when running this file directly (desktop dev mode)
# When imported by src/main.py (Android), main() is called with the page
if __name__ == "__main__":
    ft.app(target=main)
