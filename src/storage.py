import os
import json
import sys
import shutil
import glob
import zipfile
import ctypes.wintypes
from datetime import datetime
from src.config import APP_NAME

# ======================================================
# PATH & SYSTEM LOGIC
# ======================================================

def get_app_data_folder():
    user_profile = os.environ.get('USERPROFILE') or os.path.expanduser("~")
    if os.name == 'nt':
        local = os.path.join(os.environ.get('LOCALAPPDATA', user_profile), APP_NAME)
    else:
        local = os.path.join(user_profile, ".local", "share", APP_NAME)
    if not os.path.exists(local):
        os.makedirs(local, exist_ok=True)
    return local

CONFIG_FILE = os.path.join(get_app_data_folder(), "config.json")

def get_data_path():
    # 1. Check Config Override (Useful for Test Zone)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                custom_path = cfg.get('data_folder', '')
                if custom_path and os.path.exists(custom_path):
                    return custom_path
        except: pass

    # 2. Priority: Check for Cloud Storage roots
    user_profile = os.environ.get('USERPROFILE') or os.path.expanduser("~")
    cloud_candidates = [
        os.path.join(user_profile, "Dropbox"),
        os.path.join(user_profile, "OneDrive"),
        os.path.join(user_profile, "OneDrive - Personal"),
        os.path.join(user_profile, "Google Drive"),
    ]
    if os.path.exists(user_profile):
        for item in os.listdir(user_profile):
            if "OneDrive" in item and os.path.isdir(os.path.join(user_profile, item)):
                cloud_candidates.append(os.path.join(user_profile, item))

    for root in cloud_candidates:
        if os.path.exists(root):
            app_folder = os.path.join(root, "PrintShopManager")
            if os.path.exists(app_folder): return app_folder

    return get_app_data_folder()

DATA_DIR = get_data_path()
if not os.path.exists(DATA_DIR):
    try: os.makedirs(DATA_DIR, exist_ok=True)
    except: DATA_DIR = get_app_data_folder()

DB_FILE = os.path.join(DATA_DIR, "filament_inventory.json")
HISTORY_FILE = os.path.join(DATA_DIR, "sales_history.json")
MAINT_FILE = os.path.join(DATA_DIR, "maintenance_log.json")
QUEUE_FILE = os.path.join(DATA_DIR, "job_queue.json")

def get_real_windows_docs_path():
    try:
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
        return buf.value
    except: return os.path.join(os.path.expanduser("~"), "Documents")

DOCS_DIR = os.path.join(get_real_windows_docs_path(), "3D_Print_Receipts")
if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR, exist_ok=True)

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.dirname(os.path.abspath(__file__))
    # Adjust for src/ui location if needed, but standard sys._MEIPASS check usually works for compiled.
    # For dev mode, we need to be careful where __file__ is relative to the asset.
    # If this is called from src/storage.py, the asset might be in root or src/ui.
    # The original code assumed relative to the script.

    # Assuming assets are in the root where main.py is, or bundled.
    # If running from src/storage.py, we might need to go up one level if assets are in root.
    return os.path.join(base_path, relative_path)

# Logic to find the image in root if running from src
def find_asset(filename):
    # 1. Try standard resource_path (works for PyInstaller)
    path = resource_path(filename)
    if os.path.exists(path): return path

    # 2. Try looking up one or two levels (Development mode)
    # src/storage.py -> src/ -> root/
    base = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(base) # src
    root_root = os.path.dirname(root) # .

    candidates = [
        os.path.join(base, filename),
        os.path.join(root, filename),
        os.path.join(root_root, filename)
    ]

    for c in candidates:
        if os.path.exists(c): return c
    return path # Return default even if missing

IMAGE_FILE = find_asset("spool_reference.png")

def load_json(filepath):
    if not os.path.exists(filepath): return []
    try:
        with open(filepath, "r") as f: return json.load(f)
    except: return []

def save_json(data, filepath):
    with open(filepath, "w") as f: json.dump(data, f, indent=4)

def perform_auto_backup():
    """Silently zips DB files to 'Backups' folder on startup."""
    try:
        backup_dir = os.path.join(DATA_DIR, "Backups")
        if not os.path.exists(backup_dir): os.makedirs(backup_dir)

        # Create Backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(backup_dir, f"AutoBackup_{timestamp}.zip")

        # Check if source files exist before zipping
        has_files = False
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            if os.path.exists(DB_FILE): zipf.write(DB_FILE, arcname="filament_inventory.json"); has_files=True
            if os.path.exists(HISTORY_FILE): zipf.write(HISTORY_FILE, arcname="sales_history.json"); has_files=True
            if os.path.exists(MAINT_FILE): zipf.write(MAINT_FILE, arcname="maintenance_log.json"); has_files=True
            if os.path.exists(QUEUE_FILE): zipf.write(QUEUE_FILE, arcname="job_queue.json"); has_files=True

        # If no files were found, remove empty zip
        if not has_files:
            os.remove(zip_path)
            return

        # Cleanup: Keep only last 5 backups
        backups = sorted(glob.glob(os.path.join(backup_dir, "AutoBackup_*.zip")))
        while len(backups) > 5:
            os.remove(backups.pop(0))
    except Exception:
        pass # Fail silently on startup backups
