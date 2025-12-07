"""Entry point for running the GMFM app as a module."""
import flet as ft
from gmfm_app.main import main

if __name__ == "__main__":
    ft.app(target=main)
