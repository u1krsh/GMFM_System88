import flet as ft
try:
    print(f"ft.Alignment: {ft.Alignment}")
    print(f"ft.Alignment.CENTER: {ft.Alignment.CENTER}")
except AttributeError as e:
    print(e)

try:
    print(f"ft.alignment.center: {ft.alignment.center}")
except AttributeError as e:
    print(e)
