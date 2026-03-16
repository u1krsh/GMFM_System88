"""Minimal splash test"""
import flet as ft
import base64
from pathlib import Path

SRC = Path(__file__).resolve().parent

def main(page: ft.Page):
    print("[TEST] main called, page ready")
    page.bgcolor = "#FFFFFF"
    page.padding = 0
    
    b1 = base64.b64encode((SRC / "logos/Sathyabama_Institute_of_Science_and_Technology_logo.png").read_bytes()).decode()
    b2 = base64.b64encode((SRC / "logos/The-Spastics-Society-of-Tamil-Nadu-Ngo-Chennai-1.png").read_bytes()).decode()
    print(f"[TEST] images loaded: {len(b1)}, {len(b2)}")
    
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Container(height=40),
                ft.Row([
                    ft.Image(src_base64=b1, width=100, height=100),
                    ft.Container(width=20),
                    ft.Image(src_base64=b2, width=100, height=100),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=20),
                ft.Text("MotorMeasure", size=32, weight=ft.FontWeight.BOLD, color="#1E293B"),
                ft.Text("SPLASH TEST", size=20, color="red"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#FFFFFF",
            expand=True,
            alignment=ft.alignment.center,
        )
    )
    print("[TEST] controls added")

ft.app(target=main)
