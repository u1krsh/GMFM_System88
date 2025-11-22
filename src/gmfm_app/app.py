from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

# Allow running "python src/gmfm_app/app.py" without installing the package.
if __package__ is None or __package__ == "":
    FILE_PATH = Path(__file__).resolve()
    SRC_DIR = FILE_PATH.parents[1]
    REPO_ROOT = FILE_PATH.parents[2]
    for candidate in (SRC_DIR, REPO_ROOT):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)

from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager

# Handle KivyMD version differences for AppBar
try:
    from kivymd.uix.appbar import MDTopAppBar
except ImportError:
    try:
        from kivymd.uix.toolbar import MDTopAppBar
    except ImportError:
        from kivymd.uix.toolbar import MDToolbar as MDTopAppBar

from gmfm_app.data.database import DatabaseContext
from gmfm_app.services.security import SecurityProvider
from gmfm_app.ui.screens.dashboard import DashboardScreen
from gmfm_app.ui.screens.patient_form import PatientFormScreen
from gmfm_app.ui.screens.scoring_screen import ScoringScreen
from gmfm_app.ui.screens.session_detail import SessionDetailScreen


class GMFMApp(MDApp):
    """KivyMD entry point."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.security = SecurityProvider()
        self.db_context = DatabaseContext(security=self.security)

    def build(self):
        self.title = "GMFM Companion"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Teal"
        Builder.load_file(str(Path(__file__).with_name("main.kv")))
        self.manager = MDScreenManager()
        self.manager.add_widget(DashboardScreen(name="dashboard", db_context=self.db_context))
        self.manager.add_widget(PatientFormScreen(name="patient_form", db_context=self.db_context))
        self.manager.add_widget(ScoringScreen(name="scoring", db_context=self.db_context))
        self.manager.add_widget(SessionDetailScreen(name="session_detail", db_context=self.db_context))
        return self.manager

    def on_start(self):
        dirs_to_create = ["reports", "exports"]
        for dirname in dirs_to_create:
            Path(dirname).mkdir(parents=True, exist_ok=True)

    # navigation helpers
    def open_patient_form(self, patient=None):
        screen: PatientFormScreen = self.manager.get_screen("patient_form")
        screen.load_patient(patient)
        self.manager.current = "patient_form"

    def open_session_form(self, patient_id: int | None = None):
        screen: ScoringScreen = self.manager.get_screen("scoring")
        screen.load_patient(patient_id)
        self.manager.current = "scoring"

    def back_to_dashboard(self):
        self.manager.current = "dashboard"
        dashboard: DashboardScreen = self.manager.get_screen("dashboard")
        dashboard.refresh()

    def show_sessions(self, patient_id: int):
        if patient_id is None:
            return
        screen: SessionDetailScreen = self.manager.get_screen("session_detail")
        screen.load_sessions(patient_id)
        self.manager.current = "session_detail"


if __name__ == "__main__":
    GMFMApp().run()
