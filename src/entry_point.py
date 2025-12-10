import sys
import os
import time
import traceback

# Force unbuffered output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

def log(msg):
    print(f"[ENTRY_POINT] {msg}", flush=True)

log("SCRIPT STARTING")
log(f"Python version: {sys.version}")
log(f"Platform: {sys.platform}")

try:
    import logging
    import shutil
    log("Imports successful (standard lib)")
    
    # Setup basic logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("entry_point")
except Exception as e:
    log(f"CRITICAL IMPORT ERROR: {e}")
    log(traceback.format_exc())

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    log(f"Current Dir: {current_dir}")
    
    files = os.listdir(current_dir)
    log(f"File count: {len(files)}")
    
    # ---------------------------------------------------------------------------
    # ROBUST FIX FOR FLATTENED PATHS
    # ---------------------------------------------------------------------------
    flattened_files = [f for f in files if "\\" in f]
    if flattened_files:
        log(f"Found {len(flattened_files)} flattened files. Repairing...")
        
        for filename in flattened_files:
            try:
                # "gmfm_app\data\database.py" -> "gmfm_app/data/database.py"
                parts = filename.split("\\")
                
                # Create destination directory structure
                dest_dir = os.path.join(current_dir, *parts[:-1])
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                
                # Move file
                src_path = os.path.join(current_dir, filename)
                dst_path = os.path.join(current_dir, *parts)
                
                if src_path != dst_path:
                    os.rename(src_path, dst_path)
                    # log(f"Fixed: {filename}") # Reduce noise
            except Exception as fix_err:
                log(f"Failed to fix {filename}: {fix_err}")
        
        log("Repair complete.")
        log(f"New Root Contents: {os.listdir(current_dir)}")
    else:
        log("No flattened files found. Structure seems OK.")
    # ---------------------------------------------------------------------------

except Exception as e:
    log(f"CRITICAL ERROR DURING SETUP: {e}")

# Try to import Flet and App
try:
    log("Importing flet...")
    import flet as ft
    log(f"Flet version: {ft.version.version}")
    
    # Log environment variables for debugging
    log(f"FLET_PLATFORM: {os.getenv('FLET_PLATFORM')}")
    log(f"FLET_SERVER_UDS_PATH: {os.getenv('FLET_SERVER_UDS_PATH')}")
    log(f"FLET_SERVER_PORT: {os.getenv('FLET_SERVER_PORT')}")
    log(f"FLET_APP_STORAGE_DATA: {os.getenv('FLET_APP_STORAGE_DATA')}")
    log(f"FLET_APP_STORAGE_TEMP: {os.getenv('FLET_APP_STORAGE_TEMP')}")
    
    # Manually try to resolve the app module
    log("Attempting to import gmfm_app.main...")
    from gmfm_app.main import main
    log("SUCCESS: Imported gmfm_app.main")
    
    log("Launching Flet app...")
    ft.app(target=main)
    
except ImportError as e:
    log(f"IMPORT ERROR: {e}")
    log(traceback.format_exc())
    # Dump structure again to help debug
    try:
        log(f"Current dir contents: {os.listdir(current_dir)}")
        gmfm_dir = os.path.join(current_dir, 'gmfm_app')
        if os.path.exists(gmfm_dir):
            log(f"gmfm_app contents: {os.listdir(gmfm_dir)}")
    except Exception as list_err:
        log(f"Failed to list dir: {list_err}")
    
    # Try to show error in Flet UI
    error_msg = str(e)
    error_trace = traceback.format_exc()
    try:
        def show_error(page: ft.Page):
            page.title = "GMFM Pro - Import Error"
            page.bgcolor = "#FEE2E2"
            page.scroll = ft.ScrollMode.AUTO
            page.add(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("error_outline", size=60, color="#DC2626"),
                        ft.Text("Import Error", size=22, weight=ft.FontWeight.BOLD, color="#991B1B"),
                        ft.Text(error_msg, size=14, color="#7F1D1D"),
                        ft.Container(
                            content=ft.Text(error_trace, size=9, color="#6B7280", selectable=True),
                            bgcolor="#FFFFFF",
                            padding=10,
                            border_radius=8,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                )
            )
        ft.app(target=show_error)
    except:
        raise e

except Exception as e:
    log(f"RUNTIME ERROR: {e}")
    log(traceback.format_exc())
    
    # Try to show error in Flet UI
    error_msg = str(e)
    error_trace = traceback.format_exc()
    try:
        def show_error(page: ft.Page):
            page.title = "GMFM Pro - Runtime Error"
            page.bgcolor = "#FEE2E2"
            page.scroll = ft.ScrollMode.AUTO
            page.add(
                ft.Container(
                    content=ft.Column([
                        ft.Icon("error_outline", size=60, color="#DC2626"),
                        ft.Text("Runtime Error", size=22, weight=ft.FontWeight.BOLD, color="#991B1B"),
                        ft.Text(error_msg, size=14, color="#7F1D1D"),
                        ft.Container(
                            content=ft.Text(error_trace, size=9, color="#6B7280", selectable=True),
                            bgcolor="#FFFFFF",
                            padding=10,
                            border_radius=8,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                )
            )
        ft.app(target=show_error)
    except:
        raise e
