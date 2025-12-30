import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import json
import os
import sys
import shutil
import webbrowser
import ctypes.wintypes
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw
import difflib
import zipfile
import base64
import io
import urllib.request
import re

# ======================================================
# CONFIGURATION
# ======================================================

APP_NAME = "PrintShopManager"
VERSION = "v13.2 (Custom Data Path)"

# 🔧 GITHUB SETTINGS
GITHUB_RAW_URL = "https://raw.githubusercontent.com/Mobius457/3D-Print-Shop-Manager/refs/heads/main/print_manager.py"
GITHUB_REPO_URL = "https://github.com/Mobius457/3D-Print-Shop-Manager/releases"

# ======================================================
# PATH FINDER LOGIC
# ======================================================

def get_app_data_folder():
    """Returns the local folder where we store the config file (NOT the database)."""
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
    """
    Determines where the JSON database lives.
    1. Checks config.json for a user-defined override.
    2. Scans standard Cloud paths.
    3. Falls back to Local AppData.
    """
    # 1. Check Config Override
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                custom_path = cfg.get('data_folder', '')
                if custom_path and os.path.exists(custom_path):
                    return custom_path
        except:
            pass # Config corrupt or unreadable, ignore it

    # 2. Priority: Check for Cloud Storage roots
    user_profile = os.environ.get('USERPROFILE') or os.path.expanduser("~")
    cloud_candidates = [
        os.path.join(user_profile, "Dropbox"),
        os.path.join(user_profile, "OneDrive"),
        os.path.join(user_profile, "OneDrive - Personal"),
        os.path.join(user_profile, "Google Drive"),
    ]
    
    # Check "OneDrive - [Anything]" for business accounts
    if os.path.exists(user_profile):
        for item in os.listdir(user_profile):
            if "OneDrive" in item and os.path.isdir(os.path.join(user_profile, item)):
                cloud_candidates.append(os.path.join(user_profile, item))

    for root in cloud_candidates:
        if os.path.exists(root):
            app_folder = os.path.join(root, "PrintShopManager")
            # Only use it if the folder actually exists (don't create pollution)
            if os.path.exists(app_folder):
                return app_folder

    # 3. Fallback: Local AppData (Default)
    return get_app_data_folder()

# Set Global Data Directory
DATA_DIR = get_data_path()

# Ensure it exists (if it's the fallback or a new cloud create)
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except:
        DATA_DIR = get_app_data_folder() # Ultimate fallback

DB_FILE = os.path.join(DATA_DIR, "filament_inventory.json")
HISTORY_FILE = os.path.join(DATA_DIR, "sales_history.json")
MAINT_FILE = os.path.join(DATA_DIR, "maintenance_log.json")
QUEUE_FILE = os.path.join(DATA_DIR, "job_queue.json")

def get_real_windows_docs_path():
    try:
        CSIDL_PERSONAL = 5
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
        return buf.value
    except:
        return os.path.join(os.path.expanduser("~"), "Documents")

DOCS_DIR = os.path.join(get_real_windows_docs_path(), "3D_Print_Receipts")
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR, exist_ok=True)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

IMAGE_FILE = resource_path("spool_reference.png")

# ======================================================
# MAIN APPLICATION
# ======================================================

class FilamentManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"3D Print Shop Manager ({VERSION})")
        self.root.geometry("1280x950")
        
        self.load_icons()
        self.load_all_data()

        if not self.maintenance:
            self.init_default_maintenance()
        
        self.current_job_filaments = []
        self.calc_vals = {"mat_cost": 0, "overhead": 0, "labor": 0, "subtotal": 0, "total": 0, "profit": 0, "margin": 0, "hours": 0, "grams": 0}
        self.editing_index = None
        self.current_theme = "flatly"
        self.style = ttk.Style()
        self.full_filament_list = [] 
        self.sort_col = "ID"
        self.sort_reverse = False

        self.init_materials_data()
        self.init_resource_links()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self.tab_home = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_home, text=" 🏠 Dashboard ")
        self.build_dashboard_tab()

        self.tab_calc = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_calc, text=" 🖩 Calculator ")
        self.build_calculator_tab()

        self.tab_queue = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_queue, text=" ⏳ Job Queue ")
        self.build_queue_tab()

        self.tab_inventory = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_inventory, text=" 📦 Inventory ")
        self.build_inventory_tab()

        self.tab_history = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_history, text=" 📜 History ")
        self.build_history_tab()

        self.tab_ref = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ref, text=" ℹ️ Reference ")
        self.build_reference_tab() 

        self.tab_maint = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_maint, text=" 🛠️ Maintenance ")
        self.build_maintenance_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def load_icons(self):
        try:
            img_yes = Image.new('RGBA', (16, 16), (0, 0, 0, 0)) 
            draw_yes = ImageDraw.Draw(img_yes)
            draw_yes.line([(3, 8), (7, 12), (13, 4)], fill='#2ecc71', width=3)
            self.icon_yes = ImageTk.PhotoImage(img_yes)
            
            img_no = Image.new('RGBA', (16, 16), (0, 0, 0, 0)) 
            draw_no = ImageDraw.Draw(img_no)
            draw_no.line([(4, 4), (12, 12)], fill='#e74c3c', width=3)
            draw_no.line([(4, 12), (12, 4)], fill='#e74c3c', width=3)
            self.icon_no = ImageTk.PhotoImage(img_no)
        except Exception as e:
            self.icon_yes = None
            self.icon_no = None

    def load_json(self, filepath):
        if not os.path.exists(filepath): return []
        try:
            with open(filepath, "r") as f: return json.load(f)
        except: return []

    def save_json(self, data, filepath):
        with open(filepath, "w") as f: json.dump(data, f, indent=4)

    def load_all_data(self):
        self.inventory = self.load_json(DB_FILE)
        self.history = self.load_json(HISTORY_FILE)
        self.maintenance = self.load_json(MAINT_FILE)
        self.queue = self.load_json(QUEUE_FILE)

    def on_tab_change(self, event):
        self.load_all_data() 
        self.update_filament_dropdown()
        self.refresh_inventory_list()
        self.refresh_history_list()
        self.refresh_maintenance_list()
        self.refresh_queue_list()
        self.refresh_dashboard()
        self.update_row_colors()
        self.cancel_edit()

    def set_custom_data_path(self):
        # Allow user to pick a folder
        new_dir = filedialog.askdirectory(title="Select Folder to Store Data (OneDrive/Dropbox/etc)")
        if new_dir:
            # 1. Create Config File
            cfg_data = {"data_folder": new_dir}
            try:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(cfg_data, f)
                
                # 2. Check if data exists there, if not, offer to move it
                new_db = os.path.join(new_dir, "filament_inventory.json")
                if not os.path.exists(new_db) and os.path.exists(DB_FILE):
                    if messagebox.askyesno("Move Data?", f"No data found in selected folder.\nMove current data from:\n{DATA_DIR}\n\nTo:\n{new_dir}?"):
                        try:
                            shutil.copy(DB_FILE, new_db)
                            if os.path.exists(HISTORY_FILE): shutil.copy(HISTORY_FILE, os.path.join(new_dir, "sales_history.json"))
                            if os.path.exists(MAINT_FILE): shutil.copy(MAINT_FILE, os.path.join(new_dir, "maintenance_log.json"))
                            if os.path.exists(QUEUE_FILE): shutil.copy(QUEUE_FILE, os.path.join(new_dir, "job_queue.json"))
                        except Exception as e:
                            messagebox.showerror("Error Moving", str(e))

                messagebox.showinfo("Restart Required", "Data folder updated.\nPlease restart the application.")
                self.root.destroy()
            except Exception as e:
                messagebox.showerror("Config Error", f"Could not save config: {e}")

    def backup_data(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"Inventory_Backup_{datetime.now().strftime('%Y%m%d')}.json")
        if save_path:
            shutil.copy(DB_FILE, save_path)
            messagebox.showinfo("Backup", f"Saved to:\n{save_path}")

    def toggle_theme(self):
        if self.current_theme == "flatly":
            self.style.theme_use("darkly")
            self.current_theme = "darkly"
        else:
            self.style.theme_use("flatly")
            self.current_theme = "flatly"
        self.update_row_colors()

    def update_row_colors(self):
        if self.current_theme == "darkly":
            odd_bg = "#4d4d4d"; odd_fg = "white"
        else:
            odd_bg = "#f2f2f2"; odd_fg = "black"

        warn_fg = "black"; low_bg = "#FFF2CC"; crit_bg = "#FFCCCC"

        for tree in [getattr(self, 'tree', None), getattr(self, 'hist_tree', None), getattr(self, 'maint_tree', None), getattr(self, 'queue_tree', None)]:
            if tree:
                tree.tag_configure('oddrow', background=odd_bg, foreground=odd_fg)
                tree.tag_configure('low', background=low_bg, foreground=warn_fg)
                tree.tag_configure('crit', background=crit_bg, foreground=warn_fg)

    # --- AUTO-UPDATE LOGIC ---
    def check_for_updates(self):
        if "YOUR_USERNAME" in GITHUB_RAW_URL:
            messagebox.showwarning("Update Config", "Please update GITHUB_RAW_URL in the script to point to your repository.")
            return

        try:
            self.lbl_alerts.config(text="Checking for updates...", foreground="blue")
            self.root.update()
            
            with urllib.request.urlopen(GITHUB_RAW_URL) as response:
                remote_code = response.read().decode('utf-8')

            match = re.search(r'VERSION\s*=\s*"([^"]+)"', remote_code)
            
            if match:
                remote_version = match.group(1)
                if remote_version != VERSION:
                    if getattr(sys, 'frozen', False):
                        if messagebox.askyesno("Update Available", f"New version {remote_version} available!\nOpen download page?"):
                            webbrowser.open(GITHUB_REPO_URL)
                    else:
                        if messagebox.askyesno("Update Available", f"New version {remote_version} found.\nAuto-update now?"):
                            self.perform_script_update(remote_code)
                else:
                    messagebox.showinfo("Up to Date", f"You are on the latest version ({VERSION}).")
            else:
                messagebox.showerror("Error", "Could not verify version.")
            self.refresh_dashboard()
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to check updates:\n{e}")
            self.refresh_dashboard()

    def perform_script_update(self, new_code):
        try:
            current_file = os.path.abspath(__file__)
            shutil.copy(current_file, current_file + ".bak")
            with open(current_file, "w", encoding="utf-8") as f: f.write(new_code)
            messagebox.showinfo("Success", "Updated! Restarting...")
            python = sys.executable; os.execl(python, python, *sys.argv)
        except Exception as e: messagebox.showerror("Update Failed", f"Error: {e}")

    # --- TAB 0: DASHBOARD ---
    def build_dashboard_tab(self):
        main = ttk.Frame(self.tab_home, padding=20)
        main.pack(fill="both", expand=True)

        head_frame = ttk.Frame(main); head_frame.pack(fill="x", pady=10)
        ttk.Label(head_frame, text="Print Shop Command Center", font=("Segoe UI", 24, "bold"), bootstyle="primary").pack(side="left")
        ttk.Button(head_frame, text="🌗 Toggle Theme", command=self.toggle_theme, bootstyle="secondary-outline").pack(side="right")
        ttk.Button(head_frame, text="🔄 Updates", command=self.check_for_updates, bootstyle="info-outline").pack(side="right", padx=10)

        # Show Current Path
        self.lbl_path = ttk.Label(head_frame, text=f"📂 Storage: {DATA_DIR}", font=("Arial", 8), foreground="gray")
        self.lbl_path.pack(side="bottom", anchor="w")

        grid_frame = ttk.Frame(main); grid_frame.pack(fill="both", expand=True)
        grid_frame.columnconfigure(0, weight=1); grid_frame.columnconfigure(1, weight=1)
        
        f_alert = ttk.Labelframe(grid_frame, text=" ⚠️ Inventory Alerts ", padding=15, bootstyle="danger")
        f_alert.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.lbl_alerts = ttk.Label(f_alert, text="Scanning...", font=("Segoe UI", 11)); self.lbl_alerts.pack(anchor="w")
        
        f_queue = ttk.Labelframe(grid_frame, text=" ⏳ Pending Jobs ", padding=15, bootstyle="warning")
        f_queue.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.lbl_queue_status = ttk.Label(f_queue, text="Scanning...", font=("Segoe UI", 11)); self.lbl_queue_status.pack(anchor="w")
        
        f_money = ttk.Labelframe(grid_frame, text=" 💰 Monthly Performance ", padding=15, bootstyle="success")
        f_money.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.lbl_finance = ttk.Label(f_money, text="Calc...", font=("Segoe UI", 11)); self.lbl_finance.pack(anchor="w")
        
        f_sys = ttk.Labelframe(grid_frame, text=" 💾 System Actions ", padding=15, bootstyle="info")
        f_sys.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        
        ttk.Button(f_sys, text="📦 Backup All Data (.zip)", command=self.backup_all_data, bootstyle="info").pack(fill="x", pady=5)
        
        # NEW BUTTON: Set Data Folder
        ttk.Button(f_sys, text="📂 Set Data Folder", command=self.set_custom_data_path, bootstyle="warning-outline").pack(fill="x", pady=5)
        
        ttk.Button(f_sys, text="📂 Open Data Folder", command=lambda: os.startfile(DATA_DIR), bootstyle="link").pack(fill="x", pady=5)
        self.refresh_dashboard()

    def refresh_dashboard(self):
        low_stock = []
        for item in self.inventory:
            if item['weight'] < 200:
                low_stock.append(f"• {item['name']} ({item.get('material','')}): {item['weight']:.0f}g")
        if low_stock: self.lbl_alerts.config(text="\n".join(low_stock[:8]), bootstyle="danger")
        else: self.lbl_alerts.config(text="✅ All Stock Healthy", bootstyle="success")
        if self.queue: self.lbl_queue_status.config(text=f"• {len(self.queue)} jobs pending.\n• Go to 'Job Queue' tab to process.", bootstyle="warning")
        else: self.lbl_queue_status.config(text="✅ Queue is Empty", bootstyle="success")
        this_month_sales = 0.0; this_month_profit = 0.0
        curr_m = str(datetime.now().month).zfill(2); curr_y = str(datetime.now().year)
        for h in self.history:
            try:
                d = datetime.strptime(h['date'], "%Y-%m-%d %H:%M")
                if str(d.month).zfill(2) == curr_m and str(d.year) == curr_y:
                    if not h.get('is_donation', False):
                        this_month_sales += h.get('sold_for', 0); this_month_profit += h.get('profit', 0)
            except: pass
        self.lbl_finance.config(text=f"Month: {datetime.now().strftime('%B %Y')}\n\n💵 Revenue: ${this_month_sales:.2f}\n📈 Profit:    ${this_month_profit:.2f}")

    def backup_all_data(self):
        fname = f"PrintShop_Backup_{datetime.now().strftime('%Y-%m-%d')}.zip"
        save_path = filedialog.asksaveasfilename(defaultextension=".zip", initialfile=fname, filetypes=[("Zip Archive", "*.zip")])
        if not save_path: return
        try:
            with zipfile.ZipFile(save_path, 'w') as zipf:
                if os.path.exists(DB_FILE): zipf.write(DB_FILE, arcname="filament_inventory.json")
                if os.path.exists(HISTORY_FILE): zipf.write(HISTORY_FILE, arcname="sales_history.json")
                if os.path.exists(MAINT_FILE): zipf.write(MAINT_FILE, arcname="maintenance_log.json")
                if os.path.exists(QUEUE_FILE): zipf.write(QUEUE_FILE, arcname="job_queue.json")
            messagebox.showinfo("Backup", f"Full backup saved to:\n{save_path}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def restore_all_data(self):
        if not messagebox.askyesno("Confirm Restore", "This will OVERWRITE all current data.\nAre you sure?"): return
        load_path = filedialog.askopenfilename(filetypes=[("Zip Archive", "*.zip")])
        if not load_path: return
        try:
            with zipfile.ZipFile(load_path, 'r') as zipf: zipf.extractall(DATA_DIR)
            self.load_all_data(); self.refresh_dashboard()
            messagebox.showinfo("Success", "Data restored successfully!")
        except Exception as e: messagebox.showerror("Error", f"Restore failed: {e}")

    # --- TAB 1: CALCULATOR ---
    def build_calculator_tab(self):
        paned = ttk.Panedwindow(self.tab_calc, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=5, pady=5)
        frame_left = ttk.Frame(paned); paned.add(frame_left, weight=1)
        f_job = ttk.Labelframe(frame_left, text="1. Job Details", padding=10); f_job.pack(fill="x", pady=5)
        ttk.Label(f_job, text="Name:").pack(side="left")
        self.entry_job_name = ttk.Entry(f_job); self.entry_job_name.pack(side="left", fill="x", expand=True, padx=5)
        f_mat = ttk.Labelframe(frame_left, text="2. Materials", padding=10); f_mat.pack(fill="x", pady=5)
        search_frame = ttk.Frame(f_mat); search_frame.grid(row=0, column=0, columnspan=5, sticky="ew", pady=(0, 5))
        ttk.Label(search_frame, text="🔍 Filter:").pack(side="left")
        self.entry_search_mat = ttk.Entry(search_frame); self.entry_search_mat.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_search_mat.bind('<KeyRelease>', self.filter_filament_dropdown)
        ttk.Label(f_mat, text="Spool:").grid(row=1, column=0, sticky="w")
        self.combo_filaments = ttk.Combobox(f_mat, state="readonly", width=35, height=20); self.combo_filaments.grid(row=1, column=1, padx=5, sticky="ew")
        ttk.Label(f_mat, text="Grams:").grid(row=1, column=2, sticky="w")
        self.entry_calc_grams = ttk.Entry(f_mat, width=8); self.entry_calc_grams.grid(row=1, column=3, padx=5)
        ttk.Button(f_mat, text="Add", command=self.add_to_job, bootstyle="success").grid(row=1, column=4, padx=5)
        list_frame = ttk.Frame(f_mat); list_frame.grid(row=2, column=0, columnspan=5, sticky="ew", pady=5)
        self.list_job = tk.Listbox(list_frame, height=4, font=("Segoe UI", 9)); self.list_job.pack(side="left", fill="x", expand=True)
        sb_list = ttk.Scrollbar(list_frame, orient="vertical", command=self.list_job.yview); sb_list.pack(side="right", fill="y"); self.list_job.config(yscrollcommand=sb_list.set)
        ttk.Button(f_mat, text="Clear List", command=self.clear_job, bootstyle="danger-outline").grid(row=3, column=4, sticky="e")
        f_over = ttk.Labelframe(frame_left, text="3. Labor & Overhead", padding=10); f_over.pack(fill="x", pady=5)
        ttk.Label(f_over, text="Print Time (h):").grid(row=0, column=0, sticky="e")
        self.entry_hours = ttk.Entry(f_over, width=6); self.entry_hours.grid(row=0, column=1, padx=5)
        ttk.Label(f_over, text="Processing ($):").grid(row=0, column=2, sticky="e")
        self.entry_processing = ttk.Entry(f_over, width=6); self.entry_processing.insert(0,"0.00"); self.entry_processing.grid(row=0, column=3, padx=5)
        ttk.Label(f_over, text="Swaps (#):").grid(row=1, column=0, sticky="e", pady=5)
        self.entry_swaps = ttk.Entry(f_over, width=6); self.entry_swaps.grid(row=1, column=1, padx=5); self.entry_swaps.bind("<KeyRelease>", self.update_waste_estimate)
        ttk.Label(f_over, text="Waste %:").grid(row=1, column=2, sticky="e", pady=5)
        self.entry_waste = ttk.Entry(f_over, width=6); self.entry_waste.insert(0,"20"); self.entry_waste.grid(row=1, column=3, padx=5)
        f_price = ttk.Labelframe(frame_left, text="4. Pricing Strategy", padding=10); f_price.pack(fill="x", pady=5)
        ttk.Label(f_price, text="Markup (x):").grid(row=0, column=0, sticky="e")
        self.entry_markup = ttk.Entry(f_price, width=6); self.entry_markup.insert(0,"2.5"); self.entry_markup.grid(row=0, column=1, padx=5)
        ttk.Label(f_price, text="Discount (%):").grid(row=0, column=2, sticky="e")
        self.entry_discount = ttk.Entry(f_price, width=6); self.entry_discount.insert(0,"0"); self.entry_discount.grid(row=0, column=3, padx=5)
        self.var_round = tk.BooleanVar(value=False); self.var_donate = tk.BooleanVar(value=False); self.var_detailed_receipt = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_price, text="Round to nearest $", variable=self.var_round, command=self.calculate_quote, bootstyle="round-toggle").grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(f_price, text="Donation (Tax Write-off)", variable=self.var_donate, command=self.calculate_quote, bootstyle="round-toggle").grid(row=1, column=2, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(f_price, text="Detailed Receipt (Line Items)", variable=self.var_detailed_receipt, bootstyle="round-toggle").grid(row=2, column=0, columnspan=3, sticky="w", pady=5)
        ttk.Button(frame_left, text="CALCULATE QUOTE", command=self.calculate_quote, bootstyle="primary").pack(fill="x", pady=10)
        frame_right = ttk.Frame(paned, padding=10); paned.add(frame_right, weight=1)
        self.lbl_breakdown = ttk.Label(frame_right, text="Enter details...", font=("Consolas", 11), justify="left", padding=10, relief="sunken", bootstyle="secondary-inverse"); self.lbl_breakdown.pack(fill="both", expand=True)
        self.lbl_profit_warn = ttk.Label(frame_right, text="", font=("Arial", 12, "bold")); self.lbl_profit_warn.pack(pady=5)
        self.btn_receipt = ttk.Button(frame_right, text="💾 Save Receipt", command=self.generate_receipt, state="disabled"); self.btn_receipt.pack(fill="x", pady=5)
        self.btn_queue = ttk.Button(frame_right, text="⏳ Save to Queue", command=self.save_to_queue, state="disabled", bootstyle="warning"); self.btn_queue.pack(fill="x", pady=5)
        self.btn_fail = ttk.Button(frame_right, text="⚠️ Log Print Failure", command=self.log_failure, state="disabled", bootstyle="danger-outline"); self.btn_fail.pack(fill="x", pady=5)
        self.btn_deduct = ttk.Button(frame_right, text="✅ Finalize Sale Now", command=self.deduct_inventory, state="disabled", bootstyle="success"); self.btn_deduct.pack(fill="x", pady=5)
        ttk.Button(frame_right, text="📂 Open Receipts", command=self.open_receipt_folder, bootstyle="link").pack(side="bottom", pady=5)

    def update_waste_estimate(self, event=None):
        try:
            total_grams = sum(item['grams'] for item in self.current_job_filaments)
            if total_grams == 0: return
            swaps = float(self.entry_swaps.get())
            waste_grams = swaps * 2.0; waste_pct = (waste_grams / total_grams) * 100
            self.entry_waste.delete(0, tk.END); self.entry_waste.insert(0, f"{waste_pct:.1f}")
        except ValueError: pass

    def update_filament_dropdown(self):
        self.full_filament_list = []
        for f in self.inventory:
            fid = f.get('id', ''); id_prefix = f"[{fid}] " if fid else ""
            mat = f.get('material', 'PLA'); col = f.get('color', 'Unknown')
            self.full_filament_list.append(f"{id_prefix}{f['name']} ({mat} - {col}) - {int(f['weight'])}g")
        self.combo_filaments['values'] = self.full_filament_list

    def filter_filament_dropdown(self, event):
        typed = self.entry_search_mat.get().lower()
        if typed == '': self.combo_filaments['values'] = self.full_filament_list
        else:
            filtered_list = [item for item in self.full_filament_list if typed in item.lower()]
            self.combo_filaments['values'] = filtered_list
            if filtered_list: self.combo_filaments.current(0) 

    def add_to_job(self):
        selected_text = self.combo_filaments.get()
        if not selected_text: messagebox.showerror("Error", "Please select a spool."); return
        try:
            grams = float(self.entry_calc_grams.get()); found_spool = None
            for f in self.inventory:
                fid = f.get('id', ''); id_prefix = f"[{fid}] " if fid else ""
                mat = f.get('material', 'PLA'); col = f.get('color', 'Unknown')
                entry_str = f"{id_prefix}{f['name']} ({mat} - {col}) - {int(f['weight'])}g"
                if entry_str == selected_text: found_spool = f; break
            if not found_spool: messagebox.showerror("Error", "Selected spool not found."); return
            cost = (found_spool['cost'] / 1000.0) * grams
            self.current_job_filaments.append({"spool": found_spool, "grams": grams, "cost": cost})
            mat = found_spool.get('material', 'PLA'); col = found_spool.get('color', 'Unknown')
            self.list_job.insert(tk.END, f"{found_spool['name']} {col} ({mat}): {grams}g (${cost:.2f})")
            self.entry_calc_grams.delete(0, tk.END); self.update_waste_estimate()
        except ValueError: messagebox.showerror("Error", "Invalid grams")

    def clear_job(self):
        self.current_job_filaments = []
        self.list_job.delete(0, tk.END)
        for btn in [self.btn_deduct, self.btn_receipt, self.btn_queue, self.btn_fail]: btn.config(state="disabled")
        self.lbl_breakdown.config(text=""); self.lbl_profit_warn.config(text=""); self.entry_swaps.delete(0, tk.END)

    def calculate_quote(self):
        if not self.current_job_filaments: return
        try:
            hours = float(self.entry_hours.get() or 0); waste = float(self.entry_waste.get()) / 100.0
            process_fee = float(self.entry_processing.get()); markup = float(self.entry_markup.get()); discount_pct = float(self.entry_discount.get()) / 100.0
            raw_mat_cost = sum(x['cost'] for x in self.current_job_filaments)
            mat_total = raw_mat_cost * (1 + waste); machine_cost = hours * 0.75; base_cost = mat_total + machine_cost + process_fee
            subtotal = base_cost * markup; discount_amt = subtotal * discount_pct; final_price = subtotal - discount_amt
            if self.var_round.get(): final_price = round(final_price)
            if self.var_donate.get(): final_price = 0.00
            profit = final_price - base_cost; margin = (profit / final_price * 100) if final_price > 0 else 0
            self.calc_vals = {"mat": mat_total, "mach": machine_cost, "proc": process_fee, "cost": base_cost, "price": final_price, "profit": profit, "margin": margin, "disc_amt": discount_amt, "hours": hours, "grams": sum(x['grams'] for x in self.current_job_filaments)}
            txt = (f"--- COST BREAKDOWN ---\nMaterials:      ${mat_total:.2f} (w/ {waste*100:.0f}% waste)\nMachine Time:   ${machine_cost:.2f} ({hours}h @ $0.75/hr)\nProcessing:     ${process_fee:.2f} (Labor/Paint)\n----------------------\nTOTAL COST:     ${base_cost:.2f}\n----------------------\nBase Price:     ${subtotal:.2f} (Markup {markup}x)\nDiscount:      -${discount_amt:.2f}\n----------------------\nFINAL PRICE:    ${final_price:.2f}\nNet Profit:     ${profit:.2f}")
            if self.var_donate.get(): txt += "\n(DONATION - Tax Write-off)"
            self.lbl_breakdown.config(text=txt)
            if self.var_donate.get(): self.lbl_profit_warn.config(text="DONATION", bootstyle="info")
            elif margin >= 50: self.lbl_profit_warn.config(text=f"Great Margin ({margin:.0f}%)", bootstyle="success")
            elif margin >= 30: self.lbl_profit_warn.config(text=f"Good Margin ({margin:.0f}%)", bootstyle="warning")
            else: self.lbl_profit_warn.config(text=f"Low Margin ({margin:.0f}%)", bootstyle="danger")
            for btn in [self.btn_deduct, self.btn_receipt, self.btn_queue, self.btn_fail]: btn.config(state="normal")
        except ValueError: 
            if self.current_job_filaments: messagebox.showerror("Error", "Check inputs")

    def deduct_inventory(self):
        if not messagebox.askyesno("Confirm", "Finalize Sale?"): return
        items_snapshot = []
        for item in self.current_job_filaments:
            item['spool']['weight'] -= item['grams']
            items_snapshot.append({"name": item['spool']['name'], "material": item['spool'].get('material', 'Unknown'), "color": item['spool'].get('color', 'Unknown'), "grams": item['grams']})
        self.save_json(self.inventory, DB_FILE)
        rec = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "job": self.entry_job_name.get() or "Unknown", "cost": self.calc_vals['cost'], "sold_for": self.calc_vals['price'], "is_donation": self.var_donate.get(), "profit": self.calc_vals['profit'], "items": items_snapshot}
        self.history.append(rec); self.save_json(self.history, HISTORY_FILE)
        self.entry_job_name.delete(0, tk.END); self.clear_job(); self.update_filament_dropdown(); self.refresh_dashboard()
        messagebox.showinfo("Success", "Inventory Updated!")

    def log_failure(self):
        if not messagebox.askyesno("Log Failure", "Record as FAILED PRINT?\n\n• Deducts filament from inventory.\n• Records 0 revenue (loss).\n• KEEPS job details here for retry."): return
        items_snapshot = []
        for item in self.current_job_filaments:
            item['spool']['weight'] -= item['grams']
            items_snapshot.append({"name": item['spool']['name'], "material": item['spool'].get('material', 'Unknown'), "color": item['spool'].get('color', 'Unknown'), "grams": item['grams']})
        self.save_json(self.inventory, DB_FILE)
        rec = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "job": f"FAILED: {self.entry_job_name.get()}", "cost": self.calc_vals['mat'], "sold_for": 0.0, "is_donation": False, "profit": -self.calc_vals['mat'], "items": items_snapshot}
        self.history.append(rec); self.save_json(self.history, HISTORY_FILE)
        self.update_filament_dropdown(); self.refresh_dashboard()
        messagebox.showinfo("Logged", "Failure logged. Inventory deducted.\nAdjust settings and try again.")

    def save_to_queue(self):
        job_name = self.entry_job_name.get() or "Untitled Job"
        items_needed = []
        for item in self.current_job_filaments:
            items_needed.append({"name": item['spool']['name'], "material": item['spool'].get('material', 'Unknown'), "color": item['spool'].get('color', 'Unknown'), "grams": item['grams']})
        queue_item = {"date_added": datetime.now().strftime("%Y-%m-%d %H:%M"), "job": job_name, "cost": self.calc_vals['cost'], "sold_for": self.calc_vals['price'], "is_donation": self.var_donate.get(), "profit": self.calc_vals['profit'], "items": items_needed}
        self.queue.append(queue_item); self.save_json(self.queue, QUEUE_FILE)
        self.entry_job_name.delete(0, tk.END); self.clear_job(); self.refresh_queue_list(); self.refresh_dashboard()
        messagebox.showinfo("Queued", f"Job '{job_name}' saved to Queue.")

    def build_queue_tab(self):
        frame = ttk.Frame(self.tab_queue, padding=10); frame.pack(fill="both", expand=True)
        cols = ("Date Added", "Job Name", "Price", "Material(s)")
        self.queue_tree = ttk.Treeview(frame, columns=cols, show="headings", height=15, bootstyle="info")
        for c in cols: self.queue_tree.heading(c, text=c)
        self.queue_tree.column("Date Added", width=120); self.queue_tree.column("Job Name", width=250); self.queue_tree.column("Price", width=100); self.queue_tree.column("Material(s)", width=300)
        self.queue_tree.pack(side="left", fill="both", expand=True)
        btn_frame = ttk.Frame(frame); btn_frame.pack(side="right", fill="y", padx=10)
        ttk.Button(btn_frame, text="✅ Complete & Finalize", command=self.complete_queued_job, bootstyle="success").pack(pady=5, fill="x")
        ttk.Button(btn_frame, text="⬆️ Load to Calculator", command=self.load_from_queue, bootstyle="primary-outline").pack(pady=5, fill="x")
        ttk.Button(btn_frame, text="🔄 Duplicate Job", command=self.duplicate_queue_job, bootstyle="warning").pack(pady=5, fill="x")
        ttk.Button(btn_frame, text="❌ Delete / Cancel", command=self.delete_from_queue, bootstyle="danger").pack(pady=5, fill="x")
        self.refresh_queue_list(); self.update_row_colors()

    def refresh_queue_list(self):
        if not hasattr(self, 'queue_tree'): return
        for i in self.queue_tree.get_children(): self.queue_tree.delete(i)
        for idx, item in enumerate(self.queue):
            mat_str = ", ".join([f"{x['name']} ({x['grams']}g)" for x in item['items']])
            tags = ('oddrow',) if idx % 2 != 0 else ()
            self.queue_tree.insert("", "end", iid=idx, values=(item['date_added'], item['job'], f"${item['sold_for']:.2f}", mat_str), tags=tags)

    def complete_queued_job(self):
        sel = self.queue_tree.selection()
        if not sel: return
        idx = int(sel[0]); job = self.queue[idx]
        if not messagebox.askyesno("Confirm", f"Mark '{job['job']}' as complete?\nThis will deduct materials now."): return
        for needed in job['items']:
            found = False
            for spool in self.inventory:
                if (spool['name'] == needed['name'] and spool['color'] == needed['color'] and spool.get('material') == needed.get('material')):
                    spool['weight'] -= needed['grams']; found = True; break
            if not found: messagebox.showwarning("Inventory Mismatch", f"Could not find exact spool for: {needed['name']}")
        self.save_json(self.inventory, DB_FILE)
        rec = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "job": job['job'], "cost": job['cost'], "sold_for": job['sold_for'], "is_donation": job.get('is_donation', False), "profit": job.get('profit', 0), "items": job['items']}
        self.history.append(rec); self.save_json(self.history, HISTORY_FILE); del self.queue[idx]; self.save_json(self.queue, QUEUE_FILE)
        self.refresh_queue_list(); self.refresh_history_list(); self.refresh_inventory_list(); self.refresh_dashboard(); messagebox.showinfo("Success", "Job Completed & Inventory Updated.")

    def duplicate_queue_job(self):
        sel = self.queue_tree.selection()
        if not sel: return
        idx = int(sel[0]); job = self.queue[idx].copy()
        job['job'] = f"{job['job']} (Copy)"; job['date_added'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.queue.append(job); self.save_json(self.queue, QUEUE_FILE); self.refresh_queue_list(); self.refresh_dashboard()

    def delete_from_queue(self):
        sel = self.queue_tree.selection()
        if not sel: return
        if messagebox.askyesno("Confirm", "Delete this job? Inventory will NOT be deducted."):
            del self.queue[int(sel[0])]; self.save_json(self.queue, QUEUE_FILE); self.refresh_queue_list(); self.refresh_dashboard()

    def load_from_queue(self):
        sel = self.queue_tree.selection()
        if not sel: return
        idx = int(sel[0]); job = self.queue[idx]
        if messagebox.askyesno("Load Job", "Load this into calculator? Current inputs will be cleared."):
            self.clear_job(); self.entry_job_name.insert(0, job['job'])
            for item in job['items']:
                cost_per_g = 0.02; matched_spool = None
                for spool in self.inventory:
                    if (spool['name'] == item['name'] and spool['color'] == item['color']):
                        cost_per_g = spool['cost'] / 1000.0; matched_spool = spool; break
                if matched_spool: self.current_job_filaments.append({"spool": matched_spool, "grams": item['grams'], "cost": cost_per_g * item['grams']})
                else:
                    mock_spool = {"name": item['name'], "material": item.get('material',''), "color": item['color'], "weight": 0, "cost": 20.00}
                    self.current_job_filaments.append({"spool": mock_spool, "grams": item['grams'], "cost": 0.02 * item['grams']})
                self.list_job.insert(tk.END, f"{item['name']} {item['color']}: {item['grams']}g")
            self.notebook.select(self.tab_calc); messagebox.showinfo("Loaded", "Job loaded. Please verify settings and Recalculate.")

    def generate_receipt(self):
        job_name = self.entry_job_name.get() or "Custom Job"; cust = simpledialog.askstring("Receipt", "Customer Name:") or "Valued Customer"
        fname = f"Invoice_{datetime.now().strftime('%Y%m%d-%H%M')}.txt"; fpath = os.path.join(DOCS_DIR, fname); header = "DONATION RECEIPT" if self.var_donate.get() else "INVOICE"
        lines = ["="*60, f"{'3D PRINT SHOP ' + header:^60}", "="*60, f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M')}", f"CUSTOMER: {cust}", "-"*60, f"{'ITEM':<35} {'DETAILS':<15} {'PRICE':>8}", "-"*60, f"{job_name:<35} {'Custom Print':<15} ${self.calc_vals['price'] + self.calc_vals['disc_amt']:>8.2f}"]
        if self.var_detailed_receipt.get():
            lines.append(""); lines.append("--- BILLABLE LINE ITEMS ---"); lines.append(f"  > Machine Time: {self.calc_vals['hours']} hours @ $0.75/hr"); lines.append(f"  > Filament Used: {self.calc_vals['grams']:.1f} grams")
            if self.calc_vals['proc'] > 0: lines.append(f"  > Post-Processing Labor: ${self.calc_vals['proc']:.2f}")
            lines.append("-" * 60)
        else:
            for f in self.current_job_filaments:
                mat = f['spool'].get('material', 'PLA'); col = f['spool'].get('color', '')
                lines.append(f"  > {f['spool']['name']} {col} ({mat})")
            if self.calc_vals['proc'] > 0: lines.append(f"  > Post-Processing Included")
            lines.append("-" * 60)
        if self.calc_vals['disc_amt'] > 0: lines.append(f"{'DISCOUNT APPLIED:':<35}               -${self.calc_vals['disc_amt']:>8.2f}")
        lines.extend([f"{'TOTAL':<35}               ${self.calc_vals['price']:>8.2f}", "="*60, "", "CARE INSTRUCTIONS:", "* Keep away from high heat (>50C) to prevent warping.", "* Not food safe unless specified.", "", f"{'Thank you for your business!':^60}", "="*60])
        try:
            with open(fpath, "w", encoding="utf-8") as f: f.write("\n".join(lines))
            os.startfile(fpath); messagebox.showinfo("Saved", f"Receipt saved to:\n{fpath}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def open_receipt_folder(self):
        try: os.startfile(DOCS_DIR)
        except Exception as e: messagebox.showerror("Error", f"Cannot open folder: {e}")

    # --- TAB 2: INVENTORY ---
    def build_inventory_tab(self):
        frame = ttk.Frame(self.tab_inventory, padding=10); frame.pack(fill="both", expand=True)
        add_frame = ttk.Labelframe(frame, text=" Add New Spool ", padding=10); add_frame.pack(fill="x", pady=5)
        
        # Row 0
        ttk.Label(add_frame, text="Brand/Name:").grid(row=0, column=0, sticky="e")
        self.inv_name = ttk.Entry(add_frame, width=15); self.inv_name.grid(row=0, column=1, padx=5)
        
        ttk.Label(add_frame, text="ID / Label:").grid(row=0, column=2, sticky="e")
        id_frame = ttk.Frame(add_frame); id_frame.grid(row=0, column=3, padx=5)
        self.inv_id = ttk.Entry(id_frame, width=5); self.inv_id.pack(side="left")
        ttk.Button(id_frame, text="Auto", command=self.auto_gen_id, style="secondary.TButton", width=4).pack(side="left", padx=2)

        ttk.Label(add_frame, text="Material:").grid(row=0, column=4, sticky="e")
        self.inv_mat_var = tk.StringVar(); self.cb_inv_mat = ttk.Combobox(add_frame, textvariable=self.inv_mat_var, values=("PLA", "PETG", "TPU", "ABS", "ASA", "Silk", "Other"), width=8); self.cb_inv_mat.grid(row=0, column=5, padx=5)
        
        ttk.Label(add_frame, text="Color:").grid(row=0, column=6, sticky="e")
        self.inv_color = ttk.Entry(add_frame, width=10); self.inv_color.grid(row=0, column=7, padx=5)
        
        # Row 1
        ttk.Label(add_frame, text="Cost ($):").grid(row=1, column=0, sticky="e")
        self.inv_cost = ttk.Entry(add_frame, width=6); self.inv_cost.insert(0,"20.00"); self.inv_cost.grid(row=1, column=1, padx=5)
        ttk.Label(add_frame, text="Weight (g):").grid(row=1, column=2, sticky="e", pady=5)
        self.inv_weight = ttk.Entry(add_frame, width=8); self.inv_weight.insert(0,"1000"); self.inv_weight.grid(row=1, column=3, padx=5)
        
        self.tare_var = tk.IntVar(value=0)
        ttk.Radiobutton(add_frame, text="Net", variable=self.tare_var, value=0).grid(row=1, column=4, padx=5)
        ttk.Radiobutton(add_frame, text="Plastic", variable=self.tare_var, value=220).grid(row=1, column=5, padx=5)
        ttk.Radiobutton(add_frame, text="Cardboard", variable=self.tare_var, value=140).grid(row=1, column=6, columnspan=2, padx=5)

        # NEW: Benchy Checkbox
        self.var_benchy = tk.BooleanVar(value=False)
        ttk.Checkbutton(add_frame, text="Benchy?", variable=self.var_benchy, bootstyle="round-toggle").grid(row=1, column=8, padx=5)

        self.btn_inv_action = ttk.Button(add_frame, text="Add Spool", command=self.save_spool, bootstyle="success"); self.btn_inv_action.grid(row=1, column=9, padx=5)
        ttk.Button(add_frame, text="Cancel", command=self.cancel_edit, bootstyle="secondary").grid(row=1, column=10, padx=5)

        # Toolbar
        btn_box = ttk.Frame(frame); btn_box.pack(fill="x", pady=5)
        ttk.Button(btn_box, text="Edit Selected", command=self.edit_spool, bootstyle="primary").pack(side="left", padx=5)
        ttk.Button(btn_box, text="Set Material", command=self.bulk_set_material, bootstyle="info").pack(side="left", padx=5)
        ttk.Button(btn_box, text="Delete", command=self.delete_spool, bootstyle="danger").pack(side="left", padx=5)
        ttk.Button(btn_box, text="Check Price", command=self.check_price, bootstyle="secondary").pack(side="left", padx=5)

        filter_frame = ttk.Frame(frame); filter_frame.pack(fill="x", pady=5)
        ttk.Label(filter_frame, text="🔍 Filter (ID, Brand, Benchy):").pack(side="left")
        self.inv_filter_var = tk.StringVar(); self.inv_filter_var.trace("w", lambda n, i, m: self.refresh_inventory_list())
        ttk.Entry(filter_frame, textvariable=self.inv_filter_var).pack(side="left", fill="x", expand=True, padx=5)

        # NEW: Benchy Column using Tree Column (#0)
        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Material", "Color", "Weight", "Cost"), show="tree headings", height=12, bootstyle="info")
        
        # Configure #0 Column (The Tree/Icon Column)
        self.tree.column("#0", width=80, anchor="center")
        self.tree.heading("#0", text="Benchy")
        
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Weight", width=80, anchor="e")
        self.tree.column("Cost", width=80, anchor="e")
        
        cols = ("ID", "Name", "Material", "Color", "Weight", "Cost")
        for c in cols: self.tree.heading(c, text=c, command=lambda _col=c: self.sort_column(_col, False))
        
        self.lbl_inv_total = ttk.Label(frame, text="Total: 0 Spools", font=("Segoe UI", 10, "bold"), bootstyle="secondary-inverse", anchor="w", padding=5)
        self.lbl_inv_total.pack(side="bottom", fill="x", pady=5) 
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview); sb.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=sb.set)
        self.tree.tag_configure('low', background='#FFF2CC'); self.tree.tag_configure('crit', background='#FFCCCC')
        self.refresh_inventory_list()

    def auto_gen_id(self):
        # Find numeric IDs
        max_id = 0
        for item in self.inventory:
            try:
                val = int(item.get('id', 0))
                if val > max_id: max_id = val
            except: pass
        
        # Next ID is max + 1
        next_id = str(max_id + 1).zfill(3) # e.g. "045"
        self.inv_id.delete(0, tk.END)
        self.inv_id.insert(0, next_id)

    def sort_column(self, col, reverse):
        self.sort_col = col; self.sort_reverse = reverse; self.refresh_inventory_list()
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def refresh_inventory_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        filter_txt = self.inv_filter_var.get().lower().strip()
        total_grams = 0; count = 0; total_value = 0.0
        
        # Sort Data
        try:
            if self.sort_col in ("ID", "Weight", "Cost"):
                def num_sort(x):
                    try: return float(x.get(self.sort_col.lower(), 0))
                    except: return 0
                sorted_inv = sorted(self.inventory, key=num_sort, reverse=self.sort_reverse)
            else:
                sorted_inv = sorted(self.inventory, key=lambda x: str(x.get(self.sort_col.lower(), "")).lower(), reverse=self.sort_reverse)
        except: sorted_inv = self.inventory

        for item in sorted_inv: 
            mat = item.get('material', 'Unknown'); fid = item.get('id', '')
            has_benchy = item.get('has_benchy', False)
            
            # Select Icon
            display_img = self.icon_yes if has_benchy else self.icon_no

            # Filter logic
            search_str = f"{item['name']} {mat} {fid}".lower()
            if "benchy" in filter_txt: # Special filter keyword
                if "yes" in filter_txt and not has_benchy: continue
                if "no" in filter_txt and has_benchy: continue
            elif filter_txt and filter_txt not in search_str: continue
                
            w = item['weight']; total_grams += w; count += 1
            fraction_left = w / 1000.0; total_value += (item['cost'] * fraction_left)
            
            tags = []
            if w < 50: tags.append('crit')
            elif w < 200: tags.append('low')
            if count % 2 != 0: tags.append('oddrow')
            
            real_idx = self.inventory.index(item)
            # Insert using image in #0 column, other data in values
            self.tree.insert("", "end", iid=real_idx, text="", image=display_img, values=(fid, item['name'], mat, item['color'], f"{w:.1f}", item['cost']), tags=tuple(tags))
            
        self.lbl_inv_total.config(text=f"  Total: {count} Spools  |  {total_grams/1000:.1f} kg Filament  |  Est. Value: ${total_value:.2f}")
        self.update_row_colors()

    def save_spool(self):
        try:
            raw_weight = float(self.inv_weight.get()); tare = self.tare_var.get(); final_weight = raw_weight - tare
            if final_weight <= 0: messagebox.showerror("Error", "Weight too low!"); return
            new_item = {
                "id": self.inv_id.get(), "name": self.inv_name.get(), "material": self.cb_inv_mat.get(),
                "color": self.inv_color.get(), "weight": final_weight, "cost": float(self.inv_cost.get()),
                "has_benchy": self.var_benchy.get()
            }
            if self.editing_index is not None: self.inventory[self.editing_index] = new_item
            else: self.inventory.append(new_item)
            self.save_json(self.inventory, DB_FILE); self.cancel_edit(); self.refresh_inventory_list()
        except ValueError: messagebox.showerror("Error", "Check numbers")

    def edit_spool(self):
        sel = self.tree.selection()
        if not sel: return
        try:
            idx = int(sel[0]); item = self.inventory[idx]
            self.inv_id.delete(0, tk.END); self.inv_id.insert(0, item.get('id', ''))
            self.inv_name.delete(0, tk.END); self.inv_name.insert(0, item['name'])
            self.cb_inv_mat.set(item.get('material', 'PLA'))
            self.inv_color.delete(0, tk.END); self.inv_color.insert(0, item['color'])
            self.inv_weight.delete(0, tk.END); self.inv_weight.insert(0, str(item['weight']))
            self.inv_cost.delete(0, tk.END); self.inv_cost.insert(0, str(item['cost']))
            self.tare_var.set(0)
            self.var_benchy.set(item.get('has_benchy', False)) # Load Benchy status
            self.editing_index = idx; self.btn_inv_action.config(text="Update Spool")
        except: messagebox.showerror("Error", "Could not load item.")
    
    def open_bulk_edit(self, selection):
        dialog = tk.Toplevel(self.root); dialog.title(f"Bulk Edit ({len(selection)} items)"); dialog.geometry("400x400")
        ttk.Label(dialog, text="Check box to apply change:", font=("Segoe UI", 9, "bold")).pack(pady=10)
        f = ttk.Frame(dialog, padding=10); f.pack(fill="both", expand=True)
        chk_name = tk.BooleanVar(); val_name = tk.StringVar(); chk_mat = tk.BooleanVar(); val_mat = tk.StringVar()
        chk_col = tk.BooleanVar(); val_col = tk.StringVar(); chk_cost = tk.BooleanVar(); val_cost = tk.StringVar()
        chk_benchy = tk.BooleanVar(); val_benchy = tk.BooleanVar() # New Bulk Benchy
        
        ttk.Checkbutton(f, text="Name:", variable=chk_name).grid(row=0, column=0, sticky="w")
        ttk.Entry(f, textvariable=val_name).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Checkbutton(f, text="Material:", variable=chk_mat).grid(row=1, column=0, sticky="w")
        ttk.Combobox(f, textvariable=val_mat, values=("PLA", "PETG", "TPU", "ABS", "ASA", "Silk"), width=10).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Checkbutton(f, text="Color:", variable=chk_col).grid(row=2, column=0, sticky="w")
        ttk.Entry(f, textvariable=val_col).grid(row=2, column=1, sticky="ew", padx=5)
        ttk.Checkbutton(f, text="Cost ($):", variable=chk_cost).grid(row=3, column=0, sticky="w")
        ttk.Entry(f, textvariable=val_cost).grid(row=3, column=1, sticky="ew", padx=5)
        ttk.Checkbutton(f, text="Has Benchy:", variable=chk_benchy).grid(row=4, column=0, sticky="w")
        ttk.Checkbutton(f, text="Yes/No", variable=val_benchy).grid(row=4, column=1, sticky="w", padx=5)

        def apply_bulk():
            count = 0
            for iid in selection:
                idx = int(iid)
                if chk_name.get() and val_name.get(): self.inventory[idx]['name'] = val_name.get()
                if chk_mat.get() and val_mat.get(): self.inventory[idx]['material'] = val_mat.get()
                if chk_col.get() and val_col.get(): self.inventory[idx]['color'] = val_col.get()
                if chk_cost.get():
                    try: self.inventory[idx]['cost'] = float(val_cost.get())
                    except: pass
                if chk_benchy.get(): self.inventory[idx]['has_benchy'] = val_benchy.get()
                count += 1
            self.save_json(self.inventory, DB_FILE); self.refresh_inventory_list(); dialog.destroy(); messagebox.showinfo("Success", f"Updated {count} items!")
        ttk.Button(dialog, text="APPLY CHANGES", command=apply_bulk, bootstyle="primary").pack(pady=10)

    def bulk_set_material(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showinfo("Info", "Select items first."); return
        dialog = tk.Toplevel(self.root); dialog.title("Quick Material Set"); dialog.geometry("300x150")
        ttk.Label(dialog, text=f"Set Material for {len(sel)} items:").pack(pady=10)
        m_var = tk.StringVar(); cb = ttk.Combobox(dialog, textvariable=m_var, values=("PLA", "PETG", "TPU", "ABS", "ASA", "Silk", "Other"), state="readonly"); cb.pack(pady=5); cb.current(0)
        def commit():
            new_mat = m_var.get()
            for iid in sel: self.inventory[int(iid)]['material'] = new_mat
            self.save_json(self.inventory, DB_FILE); self.refresh_inventory_list(); dialog.destroy(); messagebox.showinfo("Success", "Materials Updated!")
        ttk.Button(dialog, text="Update", command=commit, bootstyle="success").pack(pady=10)

    def cancel_edit(self):
        self.editing_index = None
        self.inv_name.delete(0, tk.END); self.inv_color.delete(0, tk.END); self.inv_id.delete(0, tk.END)
        self.inv_weight.delete(0, tk.END); self.inv_weight.insert(0, "1000")
        self.inv_cost.delete(0, tk.END); self.inv_cost.insert(0, "20.00")
        self.tare_var.set(0); self.var_benchy.set(False)
        self.btn_inv_action.config(text="Add Spool")

    def delete_spool(self):
        sel = self.tree.selection()
        if not sel: return
        if self.inv_filter_var.get(): 
            self.inv_filter_var.set("")
            return
        if messagebox.askyesno("Confirm", "Delete?"):
            del self.inventory[int(sel[0])]
            self.save_json(self.inventory, DB_FILE)
            self.refresh_inventory_list()

    def check_price(self):
        sel = self.tree.selection()
        if sel:
            idx = int(sel[0]); name = self.inventory[idx]['name']; mat = self.inventory[idx].get('material', '')
            webbrowser.open(f"https://www.google.com/search?q={name} {mat} filament price")
            
    # History/Maint Tabs
    def build_history_tab(self):
        frame = ttk.Frame(self.tab_history, padding=10); frame.pack(fill="both", expand=True)
        f_bar = ttk.Labelframe(frame, text=" Filters ", padding=5); f_bar.pack(fill="x", pady=5)
        self.hist_month = tk.StringVar(value="All"); self.hist_year = tk.StringVar(value="All"); self.hist_type = tk.StringVar(value="All")
        ttk.Label(f_bar, text="Month:").pack(side="left"); ttk.Combobox(f_bar, textvariable=self.hist_month, values=["All"]+[str(i).zfill(2) for i in range(1,13)], width=5, state="readonly").pack(side="left", padx=5)
        ttk.Label(f_bar, text="Year:").pack(side="left"); ttk.Combobox(f_bar, textvariable=self.hist_year, values=["All", "2024", "2025", "2026"], width=6, state="readonly").pack(side="left", padx=5)
        ttk.Label(f_bar, text="Type:").pack(side="left"); ttk.Combobox(f_bar, textvariable=self.hist_type, values=("All", "Sales", "Donations"), width=10, state="readonly").pack(side="left", padx=5)
        ttk.Label(f_bar, text="Search:").pack(side="left", padx=5); self.hist_search_var = tk.StringVar(); self.hist_search_var.trace("w", lambda n, i, m: self.refresh_history_list()); ttk.Entry(f_bar, textvariable=self.hist_search_var, width=15).pack(side="left", padx=5)
        ttk.Button(f_bar, text="Apply", command=self.refresh_history_list, bootstyle="primary").pack(side="left", padx=10)
        
        # New "Manual Add" button frame in filter bar for easy access
        ttk.Button(f_bar, text="➕ Log Past Job", command=self.open_manual_history_dialog, bootstyle="success").pack(side="right", padx=10)

        cols = ("Date", "Job", "Cost", "Sold For", "Profit", "Type"); self.hist_tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info"); 
        for c in cols: self.hist_tree.heading(c, text=c)
        self.hist_tree.pack(side="top", fill="both", expand=True)
        db_frame = ttk.Frame(frame, relief="raised", borderwidth=1); db_frame.pack(side="bottom", fill="x", pady=10)
        self.lbl_sales = ttk.Label(db_frame, text="Sales: $0", font=("Arial", 11, "bold"), padding=10); self.lbl_sales.pack(side="left")
        self.lbl_profit = ttk.Label(db_frame, text="Profit: $0", font=("Arial", 11, "bold"), foreground="green", padding=10); self.lbl_profit.pack(side="left")
        self.lbl_donate = ttk.Label(db_frame, text="Donations: $0", font=("Arial", 11), foreground="blue", padding=10); self.lbl_donate.pack(side="right")
        btn_frame = ttk.Frame(self.tab_history); btn_frame.pack(anchor="sw", padx=10, pady=5)
        ttk.Button(btn_frame, text="Edit Record", command=self.edit_history_record, bootstyle="info").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Duplicate to Calc", command=self.duplicate_history_job, bootstyle="warning").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Record", command=self.del_history, bootstyle="danger").pack(side="left", padx=5)
        self.refresh_history_list()

    def open_manual_history_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Manually Log Past Job")
        dialog.geometry("450x650") # Taller window
        
        # 1. Job Details
        f_details = ttk.Labelframe(dialog, text="1. Job Details", padding=10)
        f_details.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(f_details, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="e")
        e_date = ttk.Entry(f_details)
        e_date.grid(row=0, column=1, sticky="ew", padx=5)
        e_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        ttk.Label(f_details, text="Job Name:").grid(row=1, column=0, sticky="e")
        e_name = ttk.Entry(f_details)
        e_name.grid(row=1, column=1, sticky="ew", padx=5)
        
        ttk.Label(f_details, text="Sold Price ($):").grid(row=2, column=0, sticky="e")
        e_price = ttk.Entry(f_details)
        e_price.grid(row=2, column=1, sticky="ew", padx=5)

        ttk.Label(f_details, text="Material Cost ($):").grid(row=3, column=0, sticky="e")
        e_cost = ttk.Entry(f_details)
        e_cost.grid(row=3, column=1, sticky="ew", padx=5)
        e_cost.insert(0, "0.00") # Manual override field
        
        var_donate = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_details, text="Is Donation?", variable=var_donate).grid(row=4, column=1, sticky="w", padx=5)
        
        # 2. Filament Details (Optional / Manual)
        f_fil = ttk.Labelframe(dialog, text="2. Filament Details (Optional)", padding=10)
        f_fil.pack(fill="x", padx=10, pady=5)

        ttk.Label(f_fil, text="Material / Color:").grid(row=0, column=0, sticky="e")
        e_material = ttk.Entry(f_fil)
        e_material.grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(f_fil, text="Grams Used:").grid(row=1, column=0, sticky="e")
        e_grams = ttk.Entry(f_fil)
        e_grams.grid(row=1, column=1, sticky="ew", padx=5)
        e_grams.insert(0, "0")

        # 3. Inventory Link (Optional)
        f_inv = ttk.Labelframe(dialog, text="3. Link to Inventory (Auto-Deduct)", padding=10, bootstyle="info")
        f_inv.pack(fill="x", padx=10, pady=5)
        
        var_deduct = tk.BooleanVar(value=False)
        chk_deduct = ttk.Checkbutton(f_inv, text="Deduct from Inventory?", variable=var_deduct, bootstyle="round-toggle")
        chk_deduct.pack(anchor="w")
        
        ttk.Label(f_inv, text="Select Spool:").pack(anchor="w", pady=(5,0))
        spool_list = []
        for f in self.inventory:
            fid = f.get('id', ''); id_prefix = f"[{fid}] " if fid else ""
            mat = f.get('material', 'PLA'); col = f.get('color', 'Unknown')
            spool_list.append(f"{id_prefix}{f['name']} ({mat} - {col}) - {int(f['weight'])}g")
        
        cb_spool = ttk.Combobox(f_inv, values=spool_list, state="readonly")
        cb_spool.pack(fill="x", pady=2)
        
        def on_spool_select(event=None):
            if not var_deduct.get(): return
            try:
                sel = cb_spool.get()
                # Find spool
                found_spool = None
                for f in self.inventory:
                    fid = f.get('id', ''); id_prefix = f"[{fid}] " if fid else ""
                    mat = f.get('material', 'PLA'); col = f.get('color', 'Unknown')
                    entry = f"{id_prefix}{f['name']} ({mat} - {col}) - {int(f['weight'])}g"
                    if entry == sel:
                        found_spool = f
                        break
                
                if found_spool:
                    # Auto-fill text fields
                    mat = found_spool.get('material', 'PLA')
                    col = found_spool.get('color', 'Unknown')
                    e_material.delete(0, tk.END); e_material.insert(0, f"{mat} {col}")
                    
                    # Calc cost if grams present
                    g = float(e_grams.get())
                    if g > 0:
                        c = (found_spool['cost'] / 1000.0) * g
                        e_cost.delete(0, tk.END); e_cost.insert(0, f"{c:.2f}")

            except: pass

        cb_spool.bind("<<ComboboxSelected>>", on_spool_select)
        e_grams.bind("<KeyRelease>", on_spool_select) # Recalc cost on gram change

        def submit():
            try:
                # Validation
                d_str = e_date.get()
                datetime.strptime(d_str, "%Y-%m-%d") 
                
                name = e_name.get()
                if not name:
                    messagebox.showerror("Error", "Job Name is required")
                    return
                
                sold = float(e_price.get())
                cost = float(e_cost.get())
                
                items_snapshot = []
                
                # Logic Branch: Deduct vs Manual
                if var_deduct.get():
                    sel = cb_spool.get()
                    if not sel:
                        messagebox.showerror("Error", "Check 'Deduct' is on, but no spool selected.")
                        return
                    
                    # Find and Deduct
                    grams = float(e_grams.get())
                    found_spool = None
                    for f in self.inventory:
                        fid = f.get('id', ''); id_prefix = f"[{fid}] " if fid else ""
                        mat = f.get('material', 'PLA'); col = f.get('color', 'Unknown')
                        entry = f"{id_prefix}{f['name']} ({mat} - {col}) - {int(f['weight'])}g"
                        if entry == sel:
                            found_spool = f
                            break
                    
                    if found_spool:
                        found_spool['weight'] -= grams
                        items_snapshot.append({
                            "name": found_spool['name'],
                            "material": found_spool.get('material', 'Unknown'),
                            "color": found_spool.get('color', 'Unknown'),
                            "grams": grams
                        })
                        self.save_json(self.inventory, DB_FILE)
                else:
                    # Manual Entry (No deduction)
                    mat_text = e_material.get()
                    g_text = e_grams.get()
                    if mat_text or g_text != "0":
                         items_snapshot.append({
                            "name": "Manual Entry",
                            "material": mat_text,
                            "color": "",
                            "grams": float(g_text)
                        })

                # Save History
                rec = {
                    "date": f"{d_str} 12:00", 
                    "job": name,
                    "cost": cost,
                    "sold_for": sold,
                    "is_donation": var_donate.get(),
                    "profit": sold - cost,
                    "items": items_snapshot
                }
                
                self.history.append(rec)
                self.history.sort(key=lambda x: x['date']) # Keep timeline sorted
                self.save_json(self.history, HISTORY_FILE)
                
                self.refresh_history_list()
                self.refresh_dashboard()
                self.refresh_inventory_list()
                
                messagebox.showinfo("Success", "Job logged.")
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("Error", "Check numbers (Price, Cost, Grams).")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(dialog, text="Save Job", command=submit, bootstyle="success").pack(pady=15, fill="x", padx=20)

    def refresh_history_list(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        total_sales = 0.0; total_profit = 0.0; total_donations = 0.0; m_filter = self.hist_month.get(); y_filter = self.hist_year.get(); t_filter = self.hist_type.get(); search_txt = self.hist_search_var.get().lower()
        count = 0
        for idx, h in enumerate(reversed(self.history)):
            if search_txt and search_txt not in h['job'].lower(): continue
            try: h_date = datetime.strptime(h['date'], "%Y-%m-%d %H:%M"); h_month = str(h_date.month).zfill(2); h_year = str(h_date.year)
            except: 
                # Fallback for manual entries that might just have YYYY-MM-DD
                try: 
                    h_date = datetime.strptime(h['date'], "%Y-%m-%d")
                    h_month = str(h_date.month).zfill(2); h_year = str(h_date.year)
                except: continue
                
            if m_filter != "All" and m_filter != h_month: continue
            if y_filter != "All" and y_filter != h_year: continue
            is_don = h.get('is_donation', False)
            if t_filter == "Sales" and is_don: continue
            if t_filter == "Donations" and not is_don: continue
            cost = h.get('cost', 0); sold = h.get('sold_for', 0); profit = h.get('profit', sold - cost)
            if is_don: total_donations += cost; type_str = "DONATION"
            else: total_sales += sold; total_profit += profit; type_str = "Sale"
            tags = ('oddrow',) if count % 2 != 0 else (); self.hist_tree.insert("", "end", values=(h['date'], h['job'], f"${cost:.2f}", f"${sold:.2f}", f"${profit:.2f}", type_str), tags=tags); count += 1
        self.lbl_sales.config(text=f"Revenue: ${total_sales:.2f}"); self.lbl_profit.config(text=f"Net Profit: ${total_profit:.2f}"); self.lbl_donate.config(text=f"Tax Write-offs: ${total_donations:.2f}"); self.update_row_colors()

    def edit_history_record(self):
        sel = self.hist_tree.selection()
        if not sel: return
        tree_index = self.hist_tree.index(sel[0]); real_index = len(self.history) - 1 - tree_index; record = self.history[real_index]
        dialog = tk.Toplevel(self.root); dialog.title("Edit Record"); dialog.geometry("300x300")
        ttk.Label(dialog, text="Date:").pack(); e_date = ttk.Entry(dialog); e_date.pack(); e_date.insert(0, record['date'])
        ttk.Label(dialog, text="Job:").pack(); e_job = ttk.Entry(dialog); e_job.pack(); e_job.insert(0, record['job'])
        ttk.Label(dialog, text="Sold ($):").pack(); e_price = ttk.Entry(dialog); e_price.pack(); e_price.insert(0, str(record.get('sold_for', 0)))
        def save():
            try: record['date'] = e_date.get(); record['job'] = e_job.get(); record['sold_for'] = float(e_price.get()); record['profit'] = record['sold_for'] - record.get('cost', 0); self.save_json(self.history, HISTORY_FILE); self.refresh_history_list(); dialog.destroy(); messagebox.showinfo("Success", "Updated.")
            except: pass
        ttk.Button(dialog, text="Save", command=save).pack(pady=10)

    def duplicate_history_job(self):
        sel = self.hist_tree.selection(); 
        if not sel: return
        values = self.hist_tree.item(sel[0], 'values'); job_name = values[1]; job_date = values[0]; found_job = None
        for record in self.history:
            if record['date'] == job_date and record['job'] == job_name: found_job = record; break
        if not found_job: return
        if messagebox.askyesno("Duplicate", f"Load job '{found_job['job']}'?"):
            self.clear_job(); self.entry_job_name.insert(0, found_job['job'])
            if "items" in found_job:
                for item in found_job['items']:
                    cost_per_g = 0.02; matched_spool = None
                    for spool in self.inventory:
                        if (spool['name'] == item['name'] and spool['color'] == item['color']): cost_per_g = spool['cost'] / 1000.0; matched_spool = spool; break
                    if matched_spool: self.current_job_filaments.append({"spool": matched_spool, "grams": item['grams'], "cost": cost_per_g * item['grams']})
                    else: 
                        mock_spool = {"name": item['name'], "material": item.get('material',''), "color": item['color'], "weight": 0, "cost": 20.00}
                        self.current_job_filaments.append({"spool": mock_spool, "grams": item['grams'], "cost": 0.02 * item['grams']})
                    self.list_job.insert(tk.END, f"{item['name']} {item['color']}: {item['grams']}g")
            self.notebook.select(self.tab_calc); messagebox.showinfo("Loaded", "Job duplicated.")

    def del_history(self):
        sel = self.hist_tree.selection() 
        if not sel: return
        values = self.hist_tree.item(sel[0], 'values'); job_name = values[1]; job_date = values[0]; real_index = -1
        for i, record in enumerate(self.history):
            if record['date'] == job_date and record['job'] == job_name: real_index = i; break
        if real_index == -1: return
        if messagebox.askyesno("Confirm", "Delete record?"): del self.history[real_index]; self.save_json(self.history, HISTORY_FILE); self.refresh_history_list()

    def build_reference_tab(self):
        main_frame = ttk.Frame(self.tab_ref, padding=10); main_frame.pack(fill="both", expand=True)
        left_col = ttk.Labelframe(main_frame, text=" Spool Estimator ", padding=10); left_col.pack(side="left", fill="both", expand=True, padx=5)
        try:
            spool_img = Image.open(IMAGE_FILE); spool_img.thumbnail((550, 750)); self.ref_img_data = ImageTk.PhotoImage(spool_img); ttk.Label(left_col, image=self.ref_img_data).pack(anchor="center", pady=10)
        except: ttk.Label(left_col, text="[spool_reference.png] missing").pack(pady=20)
        right_col = ttk.Labelframe(main_frame, text=" Field Manual ", padding=10); right_col.pack(side="right", fill="both", expand=True, padx=5)
        search_frame = ttk.Frame(right_col); search_frame.pack(fill="x", pady=5)
        ttk.Label(search_frame, text="🔍 Search Issue:").pack(side="left", padx=5); self.entry_search = ttk.Entry(search_frame); self.entry_search.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(search_frame, text="Search", command=self.perform_search, bootstyle="primary").pack(side="left")
        self.entry_search.bind("<Return>", lambda e: self.perform_search())
        ttk.Label(right_col, text="Select Topic:").pack(anchor="w", pady=(5, 0)); self.mat_var = tk.StringVar()
        self.combo_vals = ("PLA", "Silk PLA", "PETG", "ABS / ASA", "TPU", "Bambu Lab Profiles", "First Layer Guide", "Slicer Basics", "Under-Extrusion", "Wet Filament", "Hardware Maintenance", "PEI Sheet", "Troubleshooting Guide")
        self.mat_combo = ttk.Combobox(right_col, textvariable=self.mat_var, values=self.combo_vals, state="readonly"); self.mat_combo.current(0); self.mat_combo.pack(fill="x", pady=5)
        self.txt_info = tk.Text(right_col, font=("Consolas", 11), wrap="word", bg="#f0f0f0", relief="sunken", padx=15, pady=15); self.txt_info.pack(fill="both", expand=True, pady=10)
        self.btn_web_help = ttk.Button(right_col, text="🌐 Open Online Guide", command=self.open_current_link, bootstyle="info-outline"); self.btn_web_help.pack(fill="x", pady=5)
        self.mat_combo.bind("<<ComboboxSelected>>", self.update_material_view); self.update_material_view(None)

    def perform_search(self):
        query = self.entry_search.get().lower().strip()
        if not query: return
        matches = []
        for key, content in self.materials_data.items():
            score = 0
            if query in key.lower(): score += 10 
            if query in content.lower(): score += 5 
            if score > 0: matches.append((key, score))
        if not matches: messagebox.showinfo("No Results", f"No tips found for '{query}'"); return
        matches.sort(key=lambda x: x[1], reverse=True); best_topic = matches[0][0]; self.mat_combo.set(best_topic); self.update_material_view(None)

    def update_material_view(self, event):
        key = self.mat_var.get(); text_data = self.materials_data.get(key, "No Data")
        self.txt_info.config(state="normal"); self.txt_info.delete("1.0", tk.END); self.txt_info.insert("1.0", text_data); self.txt_info.config(state="disabled")
        if key in self.resource_links: self.btn_web_help.config(state="normal")
        else: self.btn_web_help.config(state="disabled")

    def open_current_link(self):
        key = self.mat_var.get(); url = self.resource_links.get(key); 
        if url: webbrowser.open(url)

    def init_resource_links(self):
        self.resource_links = {
            "PLA": "https://all3dp.com/1/pla-filament-3d-printing-guide/",
            "Silk PLA": "https://all3dp.com/2/silk-filament-guide/",
            "PETG": "https://all3dp.com/2/petg-3d-printing-temperature-nozzle-bed-settings/",
            "ABS / ASA": "https://all3dp.com/2/abs-print-settings-temperature-speed-retraction/",
            "TPU": "https://all3dp.com/2/3d-printing-tpu-filament-all-you-need-to-know/",
            "Bambu Lab Profiles": "https://wiki.bambulab.com/en/home",
            "First Layer Guide": "https://ellis3dp.com/Print-Tuning-Guide/articles/first_layer_squish.html",
            "Slicer Basics": "https://help.prusa3d.com/category/prusaslicer_204",
            "Under-Extrusion": "https://www.simplify3d.com/resources/print-quality-troubleshooting/under-extrusion/",
            "Wet Filament": "https://www.matterhackers.com/news/filament-drying-101",
            "Hardware Maintenance": "https://all3dp.com/2/3d-printer-maintenance-checklist/",
            "PEI Sheet": "https://help.prusa3d.com/article/flexible-steel-sheets-guide_2738",
            "Troubleshooting Guide": "https://www.simplify3d.com/resources/print-quality-troubleshooting/"
        }

    def init_materials_data(self):
        self.materials_data = {
            "PLA": ("MATERIAL: PLA (Polylactic Acid)\n==================================================\nNozzle:   190 – 220 °C\nBed:      45 – 60 °C\nFan:      100% (Always On)\nSpeed:    50 – 100+ mm/s\nEnclosure: NO (Keep door open)\n\n--- QUICK GUIDE ---\nBest For:    Beginners, visual models, prototypes.\nAdhesion:    Textured PEI (No Glue), Smooth PEI (Glue Optional), or Blue Tape.\nCritical:    Needs excellent cooling for overhangs.\n\n⚠️ COMMON ISSUES & FIXES:\n1. Curling Corners? -> Bed is dirty or too cold. Clean with soap.\n2. Heat Creep (Jams)? -> Printing too hot or enclosure is closed.\n3. Warping in Car? -> PLA melts at 55°C. Don't leave in hot cars."),
            "Silk PLA": ("MATERIAL: Silk PLA (Shiny Blend)\n==================================================\nNozzle:   205 – 225 °C\nBed:      50 – 60 °C\nFan:      100%\nSpeed:    40 – 60 mm/s (SLOW)\nEnclosure: NO (Keep door open)\n\n--- QUICK GUIDE ---\nBest For:    Statues, vases, decorative items.\nAdhesion:    Standard PEI / Glue Stick.\nCritical:    Print SLOW and HOT for maximum shine.\n\n⚠️ COMMON ISSUES & FIXES:\n1. Dull Finish? -> Print hotter and slower.\n2. Clogs? -> 'Die Swell' (expansion) causes jams. Reduce flow 5%.\n3. Weak Parts? -> Silk has terrible layer adhesion. Do not use for mechanical parts."),
            "PETG": ("MATERIAL: PETG (Polyethylene Terephthalate Glycol)\n==================================================\nNozzle:   230 – 250 °C\nBed:      70 – 85 °C\nFan:      30 – 50% (Low)\nSpeed:    40 – 60 mm/s\nEnclosure: NO (Draft-free room)\n\n--- QUICK GUIDE ---\nBest For:    Functional parts, snap-fits, outdoor use.\nAdhesion:    Textured PEI. AVOID SMOOTH GLASS (It fuses).\nCritical:    Raise Z-Offset +0.05mm. Don't squish the first layer.\n\n⚠️ COMMON ISSUES & FIXES:\n1. Stringing/Blobs? -> Filament is wet (Dry it!) or Flow is too high.\n2. Sticking too well? -> Use Glue Stick as a release agent.\n3. Poor Bridging? -> Increase fan speed for bridges only."),
            "ABS / ASA": ("MATERIAL: ABS & ASA\n==================================================\nNozzle:   230 – 260 °C\nBed:      90 – 110 °C\nFan:      0% (OFF)\nSpeed:    40 – 60 mm/s\nEnclosure: YES (Mandatory)\n\n--- QUICK GUIDE ---\nBest For:    Car parts, high heat, acetone smoothing.\nAdhesion:    ABS Slurry (Acetone + Scrap) or Kapton Tape.\nInfo:        ASA is similar to ABS but UV resistant (doesn't yellow in sun).\n\n⚠️ COMMON ISSUES & FIXES:\n1. Layer Cracks? -> Drafts in the room or Fan was on. Use enclosure.\n2. Warping off Bed? -> Use a large Brim (5-10mm) and hotter bed.\n3. Fumes? -> These release Styrene. Ventilate the room!"),
            "TPU": ("MATERIAL: TPU (Flexible / Rubber)\n==================================================\nNozzle:   210 – 230 °C\nBed:      40 – 60 °C\nFan:      50 – 100%\nSpeed:    15 – 30 mm/s (VERY SLOW)\nEnclosure: NO\n\n--- QUICK GUIDE ---\nBest For:    Phone cases, tires, gaskets, drones.\nAdhesion:    Sticks too well to PEI. Use Glue Stick to release.\nCritical:    Disable Retraction on Bowden setups to prevent jams.\n\n⚠️ COMMON ISSUES & FIXES:\n1. Filament tangled in gears? -> Printing too fast. Slow down.\n2. Stringing? -> TPU strings naturally. Dry the filament.\n3. Under-extrusion? -> Loosen extruder tension arm."),
            "Bambu Lab Profiles": ("=== BAMBU LAB CHEAT SHEET (X1/P1/A1) ===\n\n1. INFILL PATTERN: Gyroid (Always!)\n   Why? The nozzle hits 'Grid' or 'Cubic' infill at high speeds.\n\n2. WALL GENERATOR: Arachne\n   Why? Better quality on small text and variable width walls.\n\n3. TPU IN AMS? NO.\n   The Automatic Material System jams with flexible filament.\n   Use the external spool holder for TPU.\n   Limit 'Max Volumetric Speed' to 2.5 mm³/s in filament settings.\n\n4. CARDBOARD SPOOLS IN AMS\n   Risk: Cardboard dust clogs gears / Spools dent and jam.\n   Fix: Wrap edges in electrical tape OR print 'Spool Adapter Rings'."),
            "First Layer Guide": ("=== THE FIRST LAYER (Z-OFFSET) ===\nThe #1 cause of print failure is the nozzle distance from the bed.\n\n1. NOZZLE TOO HIGH:\n   LOOKS LIKE: Round strands of spaghetti. Gaps between lines.\n   RESULT: Part pops off mid-print.\n   FIX: Lower Z-Offset (more negative number).\n\n2. NOZZLE TOO LOW:\n   LOOKS LIKE: Rough, sandpaper texture. Transparent layers.\n   RESULT: Clogged nozzle, Elephant's foot.\n   FIX: Raise Z-Offset.\n\n3. PERFECT SQUISH:\n   LOOKS LIKE: Flat surface, lines fused together, smooth touch.\n   TEST: Print a single layer square. It should be solid, not stringy."),
            "Slicer Basics": ("=== SLICER BASICS (Terminology) ===\n\n1. PERIMETERS (WALLS)\n   - The outer shell. Strength comes from WALLS, not infill.\n   - Standard: 2 walls. Strong: 4 walls.\n\n2. INFILL\n   - The internal structure. 15-20% is standard.\n   - Use 'Gyroid' for best strength/speed balance.\n\n3. SUPPORTS\n   - Scaffolding for overhangs > 45 degrees.\n   - Use 'Tree/Organic' supports to save plastic and time.\n\n4. BRIM vs. SKIRT\n   - Skirt: A line around the print to prime the nozzle (Does not touch part).\n   - Brim: A flat hat attached to the part to prevent warping."),
            "Under-Extrusion": ("=== UNDER-EXTRUSION (Gaps/Spongy Parts) ===\n\nSYMPTOM: Missing layers, gaps in walls, weak infill.\nCAUSE: The printer can't push plastic fast enough.\n\n1. THE 'CLICKING' SOUND:\n   - Extruder gear is slipping because nozzle is blocked.\n   - FIX: Check for clog, increase temp 5°C, or slow down.\n\n2. PARTIAL CLOG:\n   - Filament comes out curling to one side.\n   - FIX: Perform a 'Cold Pull' (Heat to 200, cool to 90, yank filament out).\n\n3. CRACKED EXTRUDER ARM:\n   - Common on Creality/Ender printers.\n   - FIX: Inspect the plastic arm near the gears for hairline cracks."),
            "Wet Filament": ("=== WET FILAMENT DIAGNOSIS ===\n\nPlastic absorbs moisture from the air (Hygroscopic).\nEven new vacuum-sealed rolls can be wet!\n\nSYMPTOMS:\n1. Popping/Hissing sounds while printing.\n2. Excessive Stringing that retraction settings won't fix.\n3. Rough/Fuzzy surface texture.\n4. Brittle filament (snaps when you bend it).\n\nFIX: You must dry it.\n- Filament Dryer: 45°C (PLA) / 65°C (PETG) for 6 hours.\n- Food Dehydrator works well too.\n- DO NOT use a kitchen oven (inaccurate temps will melt spool)."),
            "Hardware Maintenance": ("=== MONTHLY HARDWARE CHECK ===\n\n1. ECCENTRIC NUTS (Wobble Check):\n   - Grab the print head and bed. Do they wobble?\n   - FIX: Tighten the single nut on the inner wheel until wobble stops.\n\n2. BELT TENSION:\n   - Loose belts = Oval circles and layer shifts.\n   - Tight belts = Motor strain.\n   - FIX: Should twang like a low bass guitar string.\n\n3. CLEAN THE Z-ROD:\n   - Clean old grease/dust off the tall lead screw.\n   - Apply fresh PTFE lube or White Lithium Grease."),
            "PEI Sheet": ("=== PEI SHEET (The Gold Standard) ===\n\nPolyetherimide (PEI) is the most popular modern print surface.\n\n1. TEXTURED PEI (Rough/Gold):\n   - Great for PETG and PLA.\n   - NO GLUE needed for PLA. Let the bed cool, and prints pop off.\n\n2. SMOOTH PEI (Flat/Black/Gold):\n   - Gives a mirror finish to the bottom of prints.\n   - WARNING: PETG and TPU stick too well to smooth PEI and can rip the sheet.\n   - FIX: Use Glue Stick as a release agent for PETG/TPU."),
            "Troubleshooting Guide": ("=== UNIVERSAL TROUBLESHOOTING GUIDE ===\n\n1. WARPING (Corners lifting off bed)\n   WHY? Plastic shrinks as it cools. Cool air pulls corners up.\n   FIX: \n   - Clean bed with Dish Soap (Grease is the enemy).\n   - Raise Bed Temp 5-10°C.\n   - Use a 'Brim' in slicer.\n   - Stop drafts (Close windows/doors).\n\n2. STRINGING (Cobwebs between parts)\n   WHY? Nozzle leaking pressure while moving.\n   FIX:\n   - Dry your filament (Wet filament = steam = pressure).\n   - Lower Nozzle Temp 5-10°C.\n   - Increase Retraction Distance.\n\n3. ELEPHANT'S FOOT (Bottom layers flared out)\n   WHY? Bed is too hot or Nozzle is too close, squishing layers.\n   FIX:\n   - Lower Bed Temp 5°C.\n   - Baby-step Z-Offset UP slightly during first layer.\n\n4. LAYER SHIFT (Staircase effect)\n   WHY? Printer hit something or belts slipped.\n   FIX:\n   - Tighten Belts (Should twang like a guitar string).\n   - Check if nozzle hit a curled-up overhang.")
        }

    # --- TAB 5: MAINTENANCE TRACKER ---
    def build_maintenance_tab(self):
        frame = ttk.Frame(self.tab_maint, padding=10)
        frame.pack(fill="both", expand=True)
        cols = ("Task", "Freq", "Last Done", "Status")
        self.maint_tree = ttk.Treeview(frame, columns=cols, show="headings", height=15, bootstyle="info")
        for c in cols: self.maint_tree.heading(c, text=c)
        self.maint_tree.column("Task", width=300)
        self.maint_tree.column("Freq", width=100)
        self.maint_tree.column("Last Done", width=150)
        self.maint_tree.pack(side="left", fill="both", expand=True)
        self.maint_tree.tag_configure('oddrow', background='#f2f2f2')
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side="right", fill="y", padx=10)
        ttk.Button(btn_frame, text="✅ Do Task Now", command=self.perform_maintenance, style="Success.TButton").pack(pady=5, fill="x")
        ttk.Button(btn_frame, text="Reset", command=self.init_default_maintenance).pack(pady=5, fill="x")
        self.refresh_maintenance_list()

    def init_default_maintenance(self):
        defaults = [
            {"task": "Clean Build Plate (Soap)", "freq": "Daily", "last": "Never"},
            {"task": "Check Belt Tension", "freq": "Monthly", "last": "Never"},
            {"task": "Lubricate Z-Rods", "freq": "Quarterly", "last": "Never"},
            {"task": "Clean Extruder Gears", "freq": "Monthly", "last": "Never"},
            {"task": "Tighten Eccentric Nuts", "freq": "Monthly", "last": "Never"},
            {"task": "Dry Filament", "freq": "As Needed", "last": "Never"}
        ]
        self.maintenance = defaults
        self.save_json(self.maintenance, MAINT_FILE)
        self.refresh_maintenance_list()

    def refresh_maintenance_list(self):
        if not hasattr(self, 'maint_tree'): return
        for i in self.maint_tree.get_children(): self.maint_tree.delete(i)
        for idx, item in enumerate(self.maintenance):
            tags = ('oddrow',) if idx % 2 != 0 else ()
            self.maint_tree.insert("", "end", iid=idx, values=(item['task'], item['freq'], item['last'], ""), tags=tags)
        self.update_row_colors()

    def perform_maintenance(self):
        sel = self.maint_tree.selection()
        if not sel: return
        idx = int(sel[0])
        now_str = datetime.now().strftime("%Y-%m-%d")
        self.maintenance[idx]['last'] = now_str
        self.save_json(self.maintenance, MAINT_FILE)
        self.refresh_maintenance_list()
        messagebox.showinfo("Done", f"Marked '{self.maintenance[idx]['task']}' as done today!")

if __name__ == "__main__":
    app = ttk.Window(themename="flatly") # BOOTSTRAP INIT
    FilamentManagerApp(app)
    app.mainloop()