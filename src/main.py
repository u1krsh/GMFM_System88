"""
GMFM Pro - Flet Build Entry Point
"""
import flet as ft
import traceback


def show_error_page(page, msg, trace=""):
    page.title = "GMFM Pro - Error"
    page.bgcolor = "#FEE2E2"
    page.scroll = ft.ScrollMode.AUTO
    page.controls.clear()
    page.controls.append(
        ft.SafeArea(
            ft.Container(
                content=ft.Column([
                    ft.Icon("error_outline", size=60, color="#DC2626"),
                    ft.Text("App Error", size=22, weight=ft.FontWeight.BOLD, color="#991B1B"),
                    ft.Container(height=10),
                    ft.Text(str(msg), size=14, color="#7F1D1D"),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text(trace, size=10, color="#6B7280", selectable=True),
                        bgcolor="#FFFFFF", padding=10, border_radius=8,
                    ) if trace else ft.Container(),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
                padding=30,
            ), expand=True,
        )
    )
    page.update()


def main(page: ft.Page):
    try:
        from gmfm_app.main import main as app_main
        app_main(page)
    except Exception as e:
        show_error_page(page, str(e), traceback.format_exc())


ft.app(target=main)