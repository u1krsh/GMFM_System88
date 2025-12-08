import sys
import os
import time

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

def log(msg):
    print(f"[ENTRY_POINT] {msg}", flush=True)

log("SCRIPT STARTING")

try:
    import logging
    import shutil
    log("Imports successful (standard lib)")
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("entry_point")
except Exception as e:
    log(f"CRITICAL IMPORT ERROR: {e}")

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
    import flet as ft
    # Manually try to resolve the app module
    log("Attempting to import gmfm_app.main...")
    from gmfm_app.main import main
    log("SUCCESS: Imported gmfm_app.main")
    
    log("Launching Flet app...")
    ft.app(target=main)
    
except ImportError as e:
    log(f"IMPORT ERROR: {e}")
    # Dump structure again to help debug
    try:
        log(f"Recursive Dir Dump: {os.listdir(current_dir)}")
    except: 
        pass
    raise e
except Exception as e:
    log(f"RUNTIME ERROR: {e}")
    raise e
