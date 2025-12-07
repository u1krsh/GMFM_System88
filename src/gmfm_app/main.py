"""
GMFM Pro - Dark Mode Edition with Innovations
"""
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    FILE_PATH = Path(__file__).resolve()
    SRC_DIR = FILE_PATH.parents[1]
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

import flet as ft
from gmfm_app.data.database import DatabaseContext
from gmfm_app.views.dashboard_view import DashboardView
from gmfm_app.views.patient_view import PatientView
from gmfm_app.views.scoring_view import ScoringView
from gmfm_app.views.session_view import SessionHistoryView, SessionDetailView, CompareView
from gmfm_app.views.settings_view import SettingsView


# Theme colors - shared across app
class Theme:
    # Dark Mode
    DARK_BG = "#0F172A"
    DARK_CARD = "#1E293B"
    DARK_BORDER = "#334155"
    
    # Light Mode
    LIGHT_BG = "#F8FAFC"
    LIGHT_CARD = "#FFFFFF"
    LIGHT_BORDER = "#E2E8F0"
    
    # Shared
    PRIMARY = "#0D9488"
    SECONDARY = "#7C3AED"
    ACCENT = "#F43F5E"
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"
    
    # Text
    DARK_TEXT1 = "#F8FAFC"
    DARK_TEXT2 = "#94A3B8"
    DARK_TEXT3 = "#64748B"
    LIGHT_TEXT1 = "#1E293B"
    LIGHT_TEXT2 = "#64748B"
    LIGHT_TEXT3 = "#94A3B8"


class GMFMApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "GMFM Pro"
        
        # Start in Light Mode by default
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = Theme.LIGHT_BG
        
        self.page.window_width = 1100
        self.page.window_height = 800
        self.page.padding = 0
        
        self.db_context = DatabaseContext()
        self.page.on_route_change = self.route_change
        self.page.on_view_pop = self.view_pop
        self.page.go("/")

    def route_change(self, route):
        self.page.views.clear()
        
        # Pass theme mode to views
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        
        if self.page.route == "/":
            self.page.views.append(DashboardView(self.page, self.db_context, is_dark))
        elif self.page.route == "/patient":
            self.page.views.append(PatientView(self.page, self.db_context, is_dark))
        elif self.page.route == "/settings":
            self.page.views.append(SettingsView(self.page, self.db_context))
        elif self.page.route.startswith("/scoring"):
            pid = self._param("patient_id")
            sid = self._param("session_id")
            scale = self._param("scale") or "88"  # Default to 88
            if pid:
                self.page.views.append(ScoringView(self.page, self.db_context, int(pid), int(sid) if sid else None, is_dark, scale))
        elif self.page.route.startswith("/history"):
            pid = self._param("patient_id")
            if pid:
                self.page.views.append(SessionHistoryView(self.page, self.db_context, int(pid), is_dark))
        elif self.page.route.startswith("/compare"):
            s1 = self._param("session1")
            s2 = self._param("session2")
            if s1 and s2:
                self.page.views.append(CompareView(self.page, self.db_context, int(s1), int(s2), is_dark))
        elif self.page.route.startswith("/session"):
            sid = self._param("session_id")
            if sid:
                self.page.views.append(SessionDetailView(self.page, self.db_context, int(sid), is_dark))
                
        self.page.update()

    def view_pop(self, view):
        self.page.views.pop()
        if self.page.views:
            self.page.go(self.page.views[-1].route)

    def _param(self, key):
        try:
            return dict(p.split("=") for p in self.page.route.split("?")[1].split("&")).get(key)
        except:
            return None


def main(page: ft.Page):
    GMFMApp(page)


if __name__ == "__main__":
    ft.app(target=main)
