"""
GMFM Pro - Flet Build Entry Point
This is the entry point used by serious_python on Android.
"""
import sys
import os
import traceback


def _log(msg):
    """Safe logging that works even when stdout is redirected."""
    try:
        print(f"[GMFM] {msg}", flush=True)
    except Exception:
        pass


_log(f"Starting GMFM Pro | Python {sys.version_info[:3]} | {sys.platform}")
_log(f"CWD: {os.getcwd()}")

import flet as ft

try:
    flet_ver = ft.version.version if hasattr(ft.version, 'version') else ft.__version__
except Exception:
    flet_ver = "unknown"
_log(f"Flet {flet_ver}")


def _make_error_view(title, msg, trace=""):
    """Create a visible error view — guaranteed no exceptions."""
    controls = [
        ft.Icon("error_outline", size=60, color="#DC2626"),
        ft.Text(str(title), size=20, weight=ft.FontWeight.BOLD, color="#991B1B"),
        ft.Container(height=10),
        ft.Text(str(msg), size=13, color="#7F1D1D", selectable=True),
    ]
    if trace:
        controls.append(ft.Container(height=10))
        controls.append(
            ft.Container(
                content=ft.Text(str(trace), size=9, color="#6B7280", selectable=True),
                bgcolor="#FFFFFF",
                padding=10,
                border_radius=8,
            )
        )
    return ft.View(
        route="/error",
        bgcolor="#FEE2E2",
        scroll=ft.ScrollMode.AUTO,
        padding=0,
        controls=[
            ft.SafeArea(
                content=ft.Container(
                    content=ft.Column(
                        controls,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=30,
                ),
                expand=True,
            )
        ],
    )


def main(page: ft.Page):
    _log("main(page) called")

    # Show a loading screen immediately so the user sees something
    page.title = "GMFM Pro"
    page.bgcolor = "#F8FAFC"
    page.padding = 0
    page.views.clear()
    page.views.append(
        ft.View(
            route="/loading",
            bgcolor="#F8FAFC",
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    [
                        ft.ProgressRing(color="#0D9488"),
                        ft.Container(height=20),
                        ft.Text("Loading GMFM Pro...", size=16, color="#64748B"),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            ],
        )
    )
    page.update()
    _log("Loading screen displayed")

    # Now try to import and start the real app
    try:
        _log("Importing gmfm_app.main ...")
        from gmfm_app.main import main as app_main
        _log("Import OK — launching app")
        app_main(page)
        _log("app_main() returned")
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        _log(f"FATAL: {error_msg}\n{error_trace}")
        try:
            page.views.clear()
            page.views.append(_make_error_view("Startup Error", error_msg, error_trace))
            page.update()
        except Exception as e2:
            _log(f"Could not show error view: {e2}")


_log("Calling ft.app()")
ft.app(target=main)