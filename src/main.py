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
    from gmfm_app.services.ui_scale import apply_android_scale
except Exception:
    apply_android_scale = None

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


def _build_splash_view():
    """Build a splash View with stacked logos (for sequential fade animation).
    Returns (view, logo1_container, logo2_container) or (None, None, None)."""
    try:
        from gmfm_app.splash_assets import LOGO1_B64, LOGO2_B64, APP_IMG_B64
        _log("splash_assets imported OK")
    except Exception as e:
        _log(f"splash_assets import failed: {e}")
        return None, None, None

    # Two logo containers stacked on top of each other — we animate opacity to swap
    logo1 = ft.Container(
        content=ft.Image(src_base64=LOGO1_B64, width=110, height=110, fit=ft.ImageFit.CONTAIN)
        if LOGO1_B64 else ft.Container(width=110, height=110),
        opacity=1,
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
    )
    logo2 = ft.Container(
        content=ft.Image(src_base64=LOGO2_B64, width=110, height=110, fit=ft.ImageFit.CONTAIN)
        if LOGO2_B64 else ft.Container(width=110, height=110),
        opacity=0,
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
    )

    # Stack logos so they overlap — only one visible at a time
    logo_slot = ft.Container(
        content=ft.Stack([logo1, logo2]),
        width=120, height=120,
        alignment=ft.alignment.center,
    )

    splash_col = ft.Column(
        [
            ft.Container(height=60),
            logo_slot,
            ft.Container(height=20),
            ft.Image(src_base64=APP_IMG_B64, width=150, height=150, fit=ft.ImageFit.CONTAIN)
            if APP_IMG_B64 else ft.Container(width=150, height=150),
            ft.Container(height=20),
            ft.Text("MotorMeasure", size=30, weight=ft.FontWeight.BOLD, color="#1E293B"),
            ft.Text("GMFM Assessment System", size=14, color="#64748B"),
            ft.Container(height=30),
            ft.ProgressRing(color="#0D9488", width=30, height=30, stroke_width=3),
            ft.Container(height=10),
            ft.Text("Loading...", size=12, color="#94A3B8"),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    view = ft.View(
        route="/splash",
        bgcolor="#FFFFFF",
        padding=0,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.SafeArea(
                content=ft.Container(
                    content=splash_col,
                    alignment=ft.alignment.center,
                    expand=True,
                ),
                expand=True,
            )
        ],
    )

    return view, logo1, logo2


def main(page: ft.Page):
    import time

    _log("main(page) called")

    page.title = "MotorMeasure"
    page.bgcolor = "#FFFFFF"
    page.padding = 0

    # Step 1: Show splash with logo1 visible — before any heavy imports.
    splash_view, logo1, logo2 = _build_splash_view()
    if splash_view:
        if apply_android_scale is not None:
            try:
                apply_android_scale(page, splash_view)
            except Exception as e:
                _log(f"Splash scaling failed: {e}")
        page.views.clear()
        page.views.append(splash_view)
        page.update()
        _log("Splash shown — logo1 visible")

        # Step 2: Animate logo swap (time.sleep blocks Python only, Flutter UI stays responsive)
        time.sleep(2.0)

        # Fade out logo1, fade in logo2
        logo1.opacity = 0
        logo2.opacity = 1
        page.update()
        _log("Logo swap — logo2 visible")

        time.sleep(2.0)
    else:
        # Fallback: plain loading screen if splash_assets fails
        page.views.clear()
        page.views.append(
            ft.View(
                route="/loading",
                bgcolor="#FFFFFF",
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        [
                            ft.ProgressRing(color="#0D9488"),
                            ft.Container(height=20),
                            ft.Text("Loading MotorMeasure...", size=16, color="#64748B"),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                ],
            )
        )
        page.update()
        _log("Fallback loading screen displayed")

    # Step 3: Now do the heavy imports — splash stays visible the whole time.
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