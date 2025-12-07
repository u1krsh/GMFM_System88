"""
GMFM Pro - Full Featured Edition
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
from gmfm_app.views.session_view import SessionHistoryView, SessionDetailView
from gmfm_app.views.settings_view import SettingsView


class GMFMApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "GMFM Pro"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = "#F8FAFC"
        self.page.window_width = 1100
        self.page.window_height = 800
        self.page.padding = 0
        
        self.db_context = DatabaseContext()
        self.page.on_route_change = self.route_change
        self.page.on_view_pop = self.view_pop
        self.page.go("/")

    def route_change(self, route):
        self.page.views.clear()
        
        if self.page.route == "/":
            self.page.views.append(DashboardView(self.page, self.db_context))
        elif self.page.route == "/patient":
            self.page.views.append(PatientView(self.page, self.db_context))
        elif self.page.route == "/settings":
            self.page.views.append(SettingsView(self.page, self.db_context))
        elif self.page.route.startswith("/scoring"):
            pid = self._param("patient_id")
            sid = self._param("session_id")
            if pid:
                self.page.views.append(ScoringView(self.page, self.db_context, int(pid), int(sid) if sid else None))
        elif self.page.route.startswith("/history"):
            pid = self._param("patient_id")
            if pid:
                self.page.views.append(SessionHistoryView(self.page, self.db_context, int(pid)))
        elif self.page.route.startswith("/session"):
            sid = self._param("session_id")
            if sid:
                self.page.views.append(SessionDetailView(self.page, self.db_context, int(sid)))
                
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
