import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import json
import os
import sys
import shutil
import glob
import webbrowser
import ctypes.wintypes
from datetime import datetime, timedelta
from PIL import Image, ImageTk, ImageDraw
import zipfile
import urllib.request
import re

# Try to import Matplotlib (Safe Failover if not installed)
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ======================================================
# CONFIGURATION
# ======================================================

APP_NAME = "PrintShopManager"
VERSION = "v14.1 (Stability Update)"

# 🔧 GITHUB SETTINGS
GITHUB_RAW_URL = "https://raw.githubusercontent.com/Mobius457/3D-Print-Shop-Manager/refs/heads/main/print_manager.py"
GITHUB_REPO_URL = "https://github.com/Mobius457/3D-Print-Shop-Manager/releases"

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
    return os.path.join(base_path, relative_path)

IMAGE_FILE = resource_path("spool_reference.png")

# ======================================================
# MAIN APPLICATION
# ======================================================

class FilamentManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"3D Print Shop Manager ({VERSION})")
        self.root.geometry("1300x950")
        
        # 1. Perform Auto-Backup on Launch
        self.perform_auto_backup()

        self.defaults = self.load_sticky_settings()
        self.icon_cache = {} 
        self.ref_images_cache = [] 
        self.load_all_data()

        if not self.maintenance: self.init_default_maintenance()
        
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
        self.load_icons()

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

    # --- HELPERS ---
    def load_icons(self):
        pass

    def perform_auto_backup(self):
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

    def load_sticky_settings(self):
        defaults = {"markup": "2.5", "labor": "0.75", "waste": "20", "discount": "0"}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
                    defaults.update(cfg.get('calc_defaults', {}))
            except: pass
        return defaults

    def save_sticky_settings(self):
        new_defaults = {
            "markup": self.entry_markup.get(),
            "labor": self.entry_processing.get(), 
            "waste": self.entry_waste.get(),
            "discount": self.entry_discount.get()
        }
        current_cfg = {}
        if os.path.exists(CONFIG_FILE):
            try: 
                with open(CONFIG_FILE, 'r') as f: current_cfg = json.load(f)
            except: pass
        
        current_cfg['calc_defaults'] = new_defaults
        with open(CONFIG_FILE, 'w') as f: json.dump(current_cfg, f)

    def generate_color_swatch(self, color_name):
        c_name = color_name.lower()
        hex_col = "#bdc3c7"
        
        colors = {
            "red": "#e74c3c", "blue": "#3498db", "green": "#2ecc71", "black": "#2c3e50",
            "white": "#ecf0f1", "grey": "#95a5a6", "gray": "#95a5a6", "orange": "#e67e22",
            "yellow": "#f1c40f", "purple": "#9b59b6", "pink": "#fd79a8", "gold": "#f1c40f",
            "silver": "#bdc3c7", "transparent": "#dfe6e9", "clear": "#dfe6e9", "brown": "#795548",
            "glow": "#55efc4", "wood": "#d35400", "silk": "#a29bfe", "teal": "#008080", "cyan": "#00FFFF"
        }
        
        for k, v in colors.items():
            if k in c_name:
                hex_col = v; break
        
        img = Image.new('RGBA', (20, 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([2, 2, 18, 18], fill=hex_col, outline="black", width=1)
        return ImageTk.PhotoImage(img)

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

    # --- SYSTEM ACTIONS ---
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

    def set_custom_data_path(self):
        new_dir = filedialog.askdirectory(title="Select Folder to Store Data (OneDrive/Dropbox/etc)")
        if new_dir:
            cfg_data = {"data_folder": new_dir}
            try:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(cfg_data, f)
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

    def check_for_updates(self):
        if "YOUR_USERNAME" in GITHUB_RAW_URL: messagebox.showwarning("Update Config", "Please update GITHUB_RAW_URL in the script."); return
        try:
            self.lbl_alerts.config(text="Checking for updates...", foreground="blue"); self.root.update()
            with urllib.request.urlopen(GITHUB_RAW_URL) as response: remote_code = response.read().decode('utf-8')
            match = re.search(r'VERSION\s*=\s*"([^"]+)"', remote_code)
            if match:
                remote_version = match.group(1)
                if remote_version != VERSION:
                    if getattr(sys, 'frozen', False):
                        if messagebox.askyesno("Update Available", f"New version {remote_version} available!\nOpen download page?"): webbrowser.open(GITHUB_REPO_URL)
                    else:
                        if messagebox.askyesno("Update Available", f"New version {remote_version} found.\nAuto-update now?"): self.perform_script_update(remote_code)
                else: messagebox.showinfo("Up to Date", f"You are on the latest version ({VERSION}).")
            self.refresh_dashboard()
        except Exception as e: messagebox.showerror("Update Error", f"Failed to check updates:\n{e}"); self.refresh_dashboard()

    def perform_script_update(self, new_code):
        try:
            current_file = os.path.abspath(__file__)
            shutil.copy(current_file, current_file + ".bak")
            with open(current_file, "w", encoding="utf-8") as f: f.write(new_code)
            messagebox.showinfo("Success", "Updated! Restarting..."); python = sys.executable; os.execl(python, python, *sys.argv)
        except Exception as e: messagebox.showerror("Update Failed", f"Error: {e}")

    # --- TAB 0: DASHBOARD ---
    def build_dashboard_tab(self):
        main = ttk.Frame(self.tab_home, padding=20)
        main.pack(fill="both", expand=True)

        head_frame = ttk.Frame(main); head_frame.pack(fill="x", pady=10)
        ttk.Label(head_frame, text="Print Shop Command Center", font=("Segoe UI", 24, "bold"), bootstyle="primary").pack(side="left")
        ttk.Button(head_frame, text="🌗 Toggle Theme", command=self.toggle_theme, bootstyle="secondary-outline").pack(side="right")
        ttk.Button(head_frame, text="🔄 Updates", command=self.check_for_updates, bootstyle="info-outline").pack(side="right", padx=10)

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
        
        self.f_graph = ttk.Labelframe(grid_frame, text=" 📊 Performance Analytics ", padding=10, bootstyle="success")
        self.f_graph.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        f_sys = ttk.Labelframe(grid_frame, text=" 💾 System Actions ", padding=15, bootstyle="info")
        f_sys.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        
        ttk.Button(f_sys, text="📦 Backup All Data (.zip)", command=self.backup_all_data, bootstyle="info").pack(fill="x", pady=5)
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

        if HAS_MATPLOTLIB:
            self.draw_performance_chart()
        else:
            ttk.Label(self.f_graph, text="Matplotlib not installed.\nAnalytics unavailable.").pack(expand=True)

    def draw_performance_chart(self):
        for widget in self.f_graph.winfo_children(): widget.destroy()

        today = datetime.now()
        data = {}
        for i in range(5, -1, -1):
            month_key = (today - timedelta(days=30*i)).strftime("%b")
            data[month_key] = 0.0

        for h in self.history:
            try:
                d_str = h['date'].split(" ")[0] if " " in h['date'] else h['date']
                d_obj = datetime.strptime(d_str, "%Y-%m-%d")
                m_key = d_obj.strftime("%b")
                
                if m_key in data and not h.get('is_donation', False):
                    data[m_key] += h.get('profit', 0)
            except: pass

        months = list(data.keys())
        profits = list(data.values())

        bg_col = '#2b2b2b' if self.current_theme == "darkly" else '#ffffff'
        fg_col = 'white' if self.current_theme == "darkly" else 'black'
        bar_col = '#2ecc71'

        fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
        fig.patch.set_facecolor(bg_col)
        ax.set_facecolor(bg_col)
        
        bars = ax.bar(months, profits, color=bar_col)
        ax.set_title("Net Profit (Last 6 Months)", color=fg_col, fontsize=10)
        ax.tick_params(axis='x', colors=fg_col)
        ax.tick_params(axis='y', colors=fg_col)
        ax.spines['bottom'].set_color(fg_col)
        ax.spines['left'].set_color(fg_col) 
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # DATA LABELS
        ax.bar_label(bars, fmt='$%.0f', label_type='edge', color=fg_col, padding=3)

        canvas = FigureCanvasTkAgg(fig, master=self.f_graph)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

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
        self.entry_waste = ttk.Entry(f_over, width=6)
        self.entry_waste.insert(0, self.defaults.get("waste", "20"))
        self.entry_waste.grid(row=1, column=3, padx=5)
        
        f_price = ttk.Labelframe(frame_left, text="4. Pricing Strategy", padding=10); f_price.pack(fill="x", pady=5)
        ttk.Label(f_price, text="Markup (x):").grid(row=0, column=0, sticky="e")
        self.entry_markup = ttk.Entry(f_price, width=6)
        self.entry_markup.insert(0, self.defaults.get("markup", "2.5"))
        self.entry_markup.grid(row=0, column=1, padx=5)
        
        ttk.Label(f_price, text="Discount (%):").grid(row=0, column=2, sticky="e")
        self.entry_discount = ttk.Entry(f_price, width=6)
        self.entry_discount.insert(0, self.defaults.get("discount", "0"))
        self.entry_discount.grid(row=0, column=3, padx=5)
        
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
            
            # Note: We do NOT hard stop here. The 'Last Line of Defense' is in deduct_inventory.
            if grams > found_spool['weight']:
                messagebox.showwarning("Low Stock", f"Warning: This job requires {grams}g, but the spool only has {int(found_spool['weight'])}g remaining.")

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
            self.save_sticky_settings()
            
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
        # 1. First Confirmation
        if not messagebox.askyesno("Confirm", "Finalize Sale?"): return

        # 2. NEW: Pre-Check for Negative Inventory
        warnings = []
        for item in self.current_job_filaments:
            current_w = item['spool']['weight']
            needed_w = item['grams']
            if (current_w - needed_w) < 0:
                warnings.append(f"• {item['spool']['name']}: Has {current_w:.0f}g, Needs {needed_w:.0f}g")
        
        # 3. If negatives found, force a second confirmation
        if warnings:
            msg = "⚠️ WARNING: The following spools will go into NEGATIVE quantity:\n\n" + "\n".join(warnings) + "\n\nProceed anyway?"
            if not messagebox.askyesno("Negative Inventory", msg, icon='warning'):
                return

        # 4. Commit Changes
        items_snapshot = []
        for item in self.current_job_filaments:
            item['spool']['weight'] -= item['grams']
            items_snapshot.append({"name": item['spool']['name'], "material": item['spool'].get('material', 'Unknown'), "color": item['spool'].get('color', 'Unknown'), "grams": item['grams']})
        
        self.save_json(self.inventory, DB_FILE)
        
        rec = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "job": self.entry_job_name.get() or "Unknown", "cost": self.calc_vals['cost'], "sold_for": self.calc_vals['price'], "is_donation": self.var_donate.get(), "profit": self.calc_vals['profit'], "items": items_snapshot}
        self.history.append(rec)
        self.save_json(self.history, HISTORY_FILE)
        
        self.entry_job_name.delete(0, tk.END)
        self.clear_job()
        self.update_filament_dropdown()
        self.refresh_dashboard()
        self.refresh_inventory_list() 
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
        
        # --- LOGIC START ---
        
        # 1. Match Spools & Check for Negatives
        spool_map = [] # Stores tuple (spool_reference, grams_needed)
        missing_spools = False
        negative_warnings = []

        for needed in job['items']:
            found = False
            for spool in self.inventory:
                # Fuzzy match logic
                if (spool['name'] == needed['name'] and spool['color'] == needed['color'] and spool.get('material') == needed.get('material')):
                    
                    # Check if this will go negative
                    if (spool['weight'] - needed['grams']) < 0:
                        negative_warnings.append(f"• {spool['name']}: Has {spool['weight']:.0f}g, Needs {needed['grams']:.0f}g")
                    
                    spool_map.append((spool, needed['grams']))
                    found = True
                    break
            if not found:
                missing_spools = True

        # 2. Handle "Missing" Spools (Deleted from inventory)
        if missing_spools:
             if not messagebox.askyesno("Missing Spool", "Some spools were not found in inventory (Orphaned).\n\nRecord the sale anyway without deducting materials?"):
                 return
             # If yes, we skip the deduction loop below but still save history
             spool_map = [] 

        # 3. Handle "Negative" Spools (Exists, but low weight)
        if negative_warnings:
            msg = "⚠️ WARNING: The following spools will go into NEGATIVE quantity:\n\n" + "\n".join(negative_warnings) + "\n\nProceed anyway?"
            if not messagebox.askyesno("Negative Inventory", msg, icon='warning'):
                return

        # 4. Execute Deductions
        for spool, grams in spool_map:
            spool['weight'] -= grams

        # 5. Save & Cleanup
        self.save_json(self.inventory, DB_FILE)
        
        rec = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "job": job['job'], "cost": job['cost'], "sold_for": job['sold_for'], "is_donation": job.get('is_donation', False), "profit": job.get('profit', 0), "items": job['items']}
        self.history.append(rec)
        self.save_json(self.history, HISTORY_FILE)
        
        del self.queue[idx]
        self.save_json(self.queue, QUEUE_FILE)
        
        self.refresh_queue_list()
        self.refresh_history_list()
        self.refresh_inventory_list()
        self.refresh_dashboard()
        messagebox.showinfo("Success", "Job Completed & Inventory Updated.")

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

    # --- TAB 2: INVENTORY (UPDATED FOR SPLIT COLUMNS) ---
    def build_inventory_tab(self):
        frame = ttk.Frame(self.tab_inventory, padding=10); frame.pack(fill="both", expand=True)
        add_frame = ttk.Labelframe(frame, text=" Add New Spool ", padding=10); add_frame.pack(fill="x", pady=5)
        
        ttk.Label(add_frame, text="Brand/Name:").grid(row=0, column=0, sticky="e")
        self.inv_name = ttk.Entry(add_frame, width=15); self.inv_name.grid(row=0, column=1, padx=5)
        
        ttk.Label(add_frame, text="ID / Label:").grid(row=0, column=2, sticky="e")
        id_frame = ttk.Frame(add_frame); id_frame.grid(row=0, column=3, padx=5)
        self.inv_id = ttk.Entry(id_frame, width=5); self.inv_id.pack(side="left")
        ttk.Button(id_frame, text="Auto", command=self.auto_gen_id, style="secondary.TButton", width=4).pack(side="left", padx=2)

        ttk.Label(add_frame, text="Material:").grid(row=0, column=4, sticky="e")
        self.inv_mat_var = tk.StringVar()
        self.cb_inv_mat = ttk.Combobox(add_frame, textvariable=self.inv_mat_var, width=10, 
            values=("PLA", "PLA+", "PLA Matte", "PLA Silk", "PLA Dual", "PLA Tri", 
                    "PETG", "PETG Trans", "PCTG", "TPU", "TPU 95A", "ABS", "ASA", 
                    "Nylon", "PC", "Carbon Fiber", "Wood Fill", "Glow", "Other"))
        self.cb_inv_mat.grid(row=0, column=5, padx=5)
        
        ttk.Label(add_frame, text="Color:").grid(row=0, column=6, sticky="e")
        self.inv_color = ttk.Entry(add_frame, width=10); self.inv_color.grid(row=0, column=7, padx=5)
        
        ttk.Label(add_frame, text="Cost ($):").grid(row=1, column=0, sticky="e")
        self.inv_cost = ttk.Entry(add_frame, width=6); self.inv_cost.insert(0,"20.00"); self.inv_cost.grid(row=1, column=1, padx=5)
        ttk.Label(add_frame, text="Weight (g):").grid(row=1, column=2, sticky="e", pady=5)
        self.inv_weight = ttk.Entry(add_frame, width=8); self.inv_weight.insert(0,"1000"); self.inv_weight.grid(row=1, column=3, padx=5)
        
        self.tare_var = tk.IntVar(value=0)
        ttk.Radiobutton(add_frame, text="Net", variable=self.tare_var, value=0).grid(row=1, column=4, padx=5)
        ttk.Radiobutton(add_frame, text="Plastic", variable=self.tare_var, value=220).grid(row=1, column=5, padx=5)
        ttk.Radiobutton(add_frame, text="Cardboard", variable=self.tare_var, value=140).grid(row=1, column=6, columnspan=2, padx=5)

        self.var_benchy = tk.BooleanVar(value=False)
        ttk.Checkbutton(add_frame, text="Benchy?", variable=self.var_benchy, bootstyle="round-toggle").grid(row=1, column=8, padx=5)

        self.btn_inv_action = ttk.Button(add_frame, text="Add Spool", command=self.save_spool, bootstyle="success"); self.btn_inv_action.grid(row=1, column=9, padx=5)
        ttk.Button(add_frame, text="Cancel", command=self.cancel_edit, bootstyle="secondary").grid(row=1, column=10, padx=5)

        btn_box = ttk.Frame(frame); btn_box.pack(fill="x", pady=5)
        ttk.Button(btn_box, text="Edit Selected", command=self.edit_spool, bootstyle="primary").pack(side="left", padx=5)
        ttk.Button(btn_box, text="Set Material", command=self.bulk_set_material, bootstyle="info").pack(side="left", padx=5)
        ttk.Button(btn_box, text="Delete", command=self.delete_spool, bootstyle="danger").pack(side="left", padx=5)
        ttk.Button(btn_box, text="Check Price", command=self.check_price, bootstyle="secondary").pack(side="left", padx=5)

        filter_frame = ttk.Frame(frame); filter_frame.pack(fill="x", pady=5)
        ttk.Label(filter_frame, text="🔍 Filter (ID, Brand, Benchy):").pack(side="left")
        self.inv_filter_var = tk.StringVar(); self.inv_filter_var.trace("w", lambda n, i, m: self.refresh_inventory_list())
        ttk.Entry(filter_frame, textvariable=self.inv_filter_var).pack(side="left", fill="x", expand=True, padx=5)

        # UPDATE: Separate columns for Image (#0) and Benchy
        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Material", "Color", "Weight", "Cost", "Benchy"), show="tree headings", height=12, bootstyle="info")
        
        self.tree.column("#0", width=60, anchor="center")
        self.tree.heading("#0", text="Color") # Image Column is now just Color
        
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Benchy", width=70, anchor="center") # New Text Column
        self.tree.column("Weight", width=80, anchor="e")
        self.tree.column("Cost", width=80, anchor="e")
        
        cols = ("ID", "Name", "Material", "Color", "Weight", "Cost", "Benchy")
        for c in cols: self.tree.heading(c, text=c, command=lambda _col=c: self.sort_column(_col, False))
        
        self.lbl_inv_total = ttk.Label(frame, text="Total: 0 Spools", font=("Segoe UI", 10, "bold"), bootstyle="secondary-inverse", anchor="w", padding=5)
        self.lbl_inv_total.pack(side="bottom", fill="x", pady=5) 
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview); sb.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=sb.set)
        self.tree.tag_configure('low', background='#FFF2CC'); self.tree.tag_configure('crit', background='#FFCCCC')
        self.refresh_inventory_list()

    def auto_gen_id(self):
        max_id = 0
        for item in self.inventory:
            try:
                val = int(item.get('id', 0))
                if val > max_id: max_id = val
            except: pass
        next_id = str(max_id + 1).zfill(3)
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
            color_name = item.get('color', 'grey')
            
            # Generate Color Swatch ONLY
            color_icon = self.generate_color_swatch(color_name)
            self.icon_cache[item['id']] = color_icon 

            # Benchy Text
            benchy_txt = "✅ Yes" if has_benchy else "❌ No"

            search_str = f"{item['name']} {mat} {fid}".lower()
            if "benchy" in filter_txt: 
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
            self.tree.insert("", "end", iid=real_idx, text="", image=color_icon, values=(fid, item['name'], mat, item['color'], f"{w:.1f}", item['cost'], benchy_txt), tags=tuple(tags))
            
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
        ttk.Combobox(f, textvariable=val_mat, width=10,
            values=("PLA", "PLA+", "PLA Matte", "PLA Silk", "PLA Dual", "PLA Tri", 
                    "PETG", "PETG Trans", "PCTG", 
                    "TPU", "TPU 95A", 
                    "ABS", "ASA", 
                    "Nylon", "PC", "Carbon Fiber", "Wood Fill", "Glow", 
                    "Other")).grid(row=1, column=1, sticky="ew", padx=5)
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
        m_var = tk.StringVar()
        cb = ttk.Combobox(dialog, textvariable=m_var, state="readonly", 
            values=("PLA", "PLA+", "PLA Matte", "PLA Silk", "PLA Dual", "PLA Tri", 
                    "PETG", "PETG Trans", "PCTG", 
                    "TPU", "TPU 95A", 
                    "ABS", "ASA", 
                    "Nylon", "PC", "Carbon Fiber", "Wood Fill", "Glow", 
                    "Other"))
        cb.pack(pady=5); cb.current(0)
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
        
        # --- NOTEBOOK FOR ALL REFERENCES (Data + Images) ---
        self.gallery_notebook = ttk.Notebook(main_frame)
        self.gallery_notebook.pack(fill="both", expand=True)
        
        # --- TAB 1: FILAMENT DATA TABLE (The Fix) ---
        f_tab = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f_tab, text=" 📊 Filament Guide ")
        
        cols = ("Material", "Nozzle Type", "Print Temp", "Bed Temp", "Fan Speed", "Difficulty", "Notes")
        fil_tree = ttk.Treeview(f_tab, columns=cols, show="headings", height=20, bootstyle="info")
        for c in cols: fil_tree.heading(c, text=c)
        fil_tree.column("Material", width=120)
        fil_tree.column("Nozzle Type", width=150) # The column you asked for
        fil_tree.column("Print Temp", width=100)
        fil_tree.column("Bed Temp", width=100)
        fil_tree.column("Fan Speed", width=80)
        fil_tree.column("Difficulty", width=80)
        fil_tree.column("Notes", width=300)
        fil_tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # The Data from your chart + Nozzle Info
        data = [
            ("PLA", "Brass / Standard", "190-220°C", "45-60°C", "100%", "Low", "Easy to print. Keep door open."),
            ("PLA Silk", "Brass / Standard", "210-230°C", "50-60°C", "100%", "Low-Med", "Print slow/hot for shine. Expands."),
            ("PLA Carbon Fiber", "Hardened Steel", "210-230°C", "50-60°C", "100%", "Med", "Abrasive! Wears out brass nozzles."),
            ("PLA Glow", "Hardened Steel", "210-230°C", "50-60°C", "100%", "Med", "Highly abrasive."),
            ("PLA Wood", "Hardened (0.6mm)", "190-210°C", "50-60°C", "100%", "Med", "Clogs easily. Use larger nozzle."),
            ("PETG", "Brass / Standard", "230-250°C", "70-85°C", "30-50%", "Med", "Stringy. Sticks well to PEI."),
            ("TPU (Flex)", "Brass / Standard", "220-240°C", "40-60°C", "50-100%", "High", "Print SLOW (20mm/s). Dry first."),
            ("ABS", "Brass / Standard", "240-260°C", "90-110°C", "0%", "High", "Needs enclosure. Toxic fumes."),
            ("ASA", "Brass / Standard", "240-260°C", "90-110°C", "0-20%", "High", "UV Resistant. Outdoor use."),
            ("Nylon (PA)", "Hardened Steel", "250-270°C", "70-90°C", "0%", "Very High", "Must be dry box fed. Warps."),
            ("PC", "Hardened Steel", "260-280°C", "110°C+", "0%", "Very High", "Strongest. High heat resistance.")
        ]
        
        for idx, row in enumerate(data):
            tag = 'odd' if idx % 2 else 'even'
            fil_tree.insert("", "end", values=row, tags=(tag,))
        
        fil_tree.tag_configure('odd', background='#f0f0f0')

        # --- TAB 2+: DYNAMIC IMAGES ---
        image_files = []
        if os.path.exists(IMAGE_FILE): image_files.append(IMAGE_FILE)
        
        search_folder = os.path.dirname(IMAGE_FILE)
        extensions = ["png", "jpg", "jpeg"]
        for ext in extensions:
            pattern = os.path.join(search_folder, f"ref_*.{ext}")
            found_extras = glob.glob(pattern)
            image_files.extend(found_extras)
        
        image_files = list(set(image_files)) # Remove duplicates
        
        for img_path in image_files:
            try:
                tab_frame = ttk.Frame(self.gallery_notebook)
                fname = os.path.basename(img_path)
                if "spool_reference" in fname: title = "Estimator"
                else: title = os.path.splitext(fname)[0].replace("ref_", "")
                
                self.gallery_notebook.add(tab_frame, text=f" 📷 {title} ")
                
                pil_img = Image.open(img_path)
                pil_img.thumbnail((800, 600)) # Larger view for charts
                tk_img = ImageTk.PhotoImage(pil_img)
                self.ref_images_cache.append(tk_img)
                
                ttk.Label(tab_frame, image=tk_img).pack(anchor="center", pady=10)
            except: pass

        # --- TAB LAST: FIELD MANUAL ---
        man_tab = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(man_tab, text=" 📖 Manual ")
        
        search_frame = ttk.Frame(man_tab); search_frame.pack(fill="x", pady=5)
        ttk.Label(search_frame, text="🔍 Search Issue:").pack(side="left", padx=5)
        self.entry_search = ttk.Entry(search_frame); self.entry_search.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(search_frame, text="Search", command=self.perform_search, bootstyle="primary").pack(side="left")
        
        self.mat_var = tk.StringVar()
        self.combo_vals = list(self.materials_data.keys())
        self.mat_combo = ttk.Combobox(man_tab, textvariable=self.mat_var, values=self.combo_vals, state="readonly")
        self.mat_combo.current(0); self.mat_combo.pack(fill="x", pady=5)
        
        self.txt_info = tk.Text(man_tab, font=("Consolas", 11), wrap="word", bg="#f0f0f0", relief="sunken", padx=15, pady=15)
        self.txt_info.pack(fill="both", expand=True, pady=10)
        self.mat_combo.bind("<<ComboboxSelected>>", self.update_material_view)
        self.update_material_view(None)

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

    def open_current_link(self):
        key = self.mat_var.get(); url = self.resource_links.get(key); 
        if url: webbrowser.open(url)

    def init_resource_links(self):
        self.resource_links = {
            "PLA Basics": "https://all3dp.com/1/pla-filament-3d-printing-guide/",
            "PLA Specials (Silk/Dual/Tri)": "https://all3dp.com/2/silk-filament-guide/",
            "PETG Standard": "https://all3dp.com/2/petg-3d-printing-temperature-nozzle-bed-settings/",
            "Transparent (PETG/PCTG)": "https://all3dp.com/2/transparent-3d-printing-guide/",
            "ABS / ASA": "https://all3dp.com/2/abs-print-settings-temperature-speed-retraction/",
            "TPU (Flexible)": "https://all3dp.com/2/3d-printing-tpu-filament-all-you-need-to-know/",
            "Nylon / PC (Engineering)": "https://all3dp.com/2/nylon-3d-printing-guide/",
            "Abrasives (CF / Glow / Wood)": "https://all3dp.com/2/carbon-fiber-3d-printer-filament-guide/",
            "Bambu Lab Profiles": "https://wiki.bambulab.com/en/home",
            "First Layer Guide": "https://ellis3dp.com/Print-Tuning-Guide/articles/first_layer_squish.html",
            "Wet Filament Symptoms": "https://www.matterhackers.com/news/filament-drying-101",
            "Hardware Maintenance": "https://all3dp.com/2/3d-printer-maintenance-checklist/",
        }

    def init_materials_data(self):
        self.materials_data = {
            "PLA Basics": ("MATERIAL: Standard PLA\n========================\nNozzle: 190-220°C | Bed: 45-60°C\n\nThe standard workhorse. Keep the door OPEN and lid OFF to prevent heat creep (clogs). If corners curl, clean the bed with soap."),
            "PLA Specials (Silk/Dual/Tri)": ("MATERIAL: Silk, Dual-Color, Tri-Color\n=======================================\nNozzle: 210-230°C (Print Hotter!)\nSpeed:  Slow down outer walls (30-50mm/s)\n\n1. SHINE: The slower and hotter you print, the shinier it gets.\n2. CLOGS: Silk expands ('die swell'). If it jams, lower Flow Ratio to 0.95.\n3. DUAL COLOR: Ensure your 'Flush Volumes' are high enough so colors don't look muddy."),
            "PLA Matte": ("MATERIAL: Matte PLA\n========================\nNozzle: 200-220°C\n\n1. TEXTURE: Hides layer lines beautifully.\n2. WEAKNESS: Matte PLA has weaker layer adhesion than regular PLA. Do not use for structural parts that need to hold weight."),
            "Transparent (PETG/PCTG)": ("MATERIAL: Transparent / Clear Filaments\n=======================================\nTo get 'Glass-Like' parts:\n1. LAYER HEIGHT: 0.1mm or lower.\n2. SPEED: Very Slow (20-30 mm/s).\n3. INFILL: 100% Aligned Rectilinear (Do not use Gyroid/Grid).\n4. TEMP: Print +5°C hotter than normal to melt layers together completely."),
            "PETG Standard": ("MATERIAL: PETG\n========================\nNozzle: 230-250°C | Bed: 70-85°C\n\n1. STICKING: Sticks TOO well to PEI. Use Glue Stick or Windex as a release agent.\n2. STRINGING: Wet PETG strings badly. Dry it if you see cobwebs.\n3. FAN: Keep fan low (30-50%) for better strength."),
            "TPU (Flexible)": ("MATERIAL: TPU (95A / 85A)\n========================\nNozzle: 220-240°C | Speed: 20-40mm/s\n\n1. RETRACTION: Turn OFF or very low (0.5mm) to prevent jams.\n2. AMS/MMU: Do NOT put TPU in multi-material systems (it jams). Use external spool.\n3. HYGROSCOPIC: Absorbs water instantly. Must be dried before use."),
            "ABS / ASA": ("MATERIAL: ABS & ASA\n========================\nNozzle: 240-260°C | Bed: 100°C+\nREQUIRED: Enclosure (Draft Shield)\n\n1. WARPING: Use a large Brim (5-10mm) and pre-heat the chamber.\n2. TOXICITY: ABS releases styrene. ASA is UV resistant (outdoor safe).\n3. COOLING: Turn cooling fan OFF for maximum strength."),
            "Nylon / PC (Engineering)": ("MATERIAL: Nylon (PA) & Polycarbonate (PC)\n=========================================\nNozzle: 260-300°C | Bed: 100-110°C\n\n1. MOISTURE: These absorb water in minutes. You MUST print directly from a dry box.\n2. ADHESION: Use Magigoo PA or PVA Glue. They warp aggressively.\n3. NOZZLE: Use Hardened Steel (especially for CF/GF variants)."),
            "Abrasives (CF / Glow / Wood)": ("⚠️ WARNING: ABRASIVE MATERIALS\n==============================\nIncludes: Carbon Fiber (CF), Glass Fiber (GF), Glow-in-the-Dark, Wood Fill.\n\n1. HARDWARE: Do NOT use a brass nozzle. It will wear out in <500g.\n   -> Use Hardened Steel, Ruby, or Tungsten Carbide nozzles.\n2. CLOGS: Use a 0.6mm nozzle if possible (0.4mm clogs easily with Wood/CF).\n3. PATH: These filaments can cut through plastic PTFE tubes over time."),
            "Bambu Lab Profiles": ("=== BAMBU LAB CHEAT SHEET ===\n\n1. INFILL: Gyroid (Prevents nozzle scraping).\n2. WALLS: Arachne (Better for variable widths).\n3. SILENT MODE: Cuts speed by 50%. Use for tall/wobbly prints.\n4. AUX FAN: Turn OFF for ABS/ASA/PETG to prevent warping."),
            "First Layer Guide": ("=== Z-OFFSET DIAGNOSIS ===\n1. GAPS between lines? -> Nozzle too high. Lower Z-Offset.\n2. ROUGH / RIPPLES? -> Nozzle too low. Raise Z-Offset.\n3. PEELING? -> Wash plate with Dish Soap & Water (IPA is not enough)."),
            "Wet Filament Symptoms": ("=== IS MY FILAMENT WET? ===\n\n1. POPPING NOISES: Steam escaping the nozzle.\n2. FUZZY TEXTURE: Surface looks rough.\n3. WEAKNESS: Parts snap easily.\n\nFIX: Dry it.\nPLA: 45°C (4-6h)\nPETG: 65°C (6h)\nNylon: 75°C (12h+)"),
            "Hardware Maintenance": ("=== MONTHLY CHECKLIST ===\n1. CLEAN RODS: Wipe old grease, apply fresh White Lithium Grease.\n2. BELTS: Pluck them like a guitar string. Low note = too loose.\n3. SCREWS: Check frame screws (thermal expansion loosens them).")
        }

    # --- TAB 5: MAINTENANCE TRACKER ---
    def build_maintenance_tab(self):
        frame = ttk.Frame(self.tab_maint, padding=10); frame.pack(fill="both", expand=True)
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
            {"task": "Check Nozzle Wear (Abrasives)", "freq": "Monthly", "last": "Never"},
            {"task": "Check Bowden/PTFE Tubes", "freq": "Monthly", "last": "Never"},
            {"task": "Clean Extruder Gears", "freq": "Monthly", "last": "Never"},
            {"task": "Lubricate Z-Rods", "freq": "Quarterly", "last": "Never"},
            {"task": "Tighten Frame Screws", "freq": "Quarterly", "last": "Never"},
            {"task": "Replace/Charge Desiccant", "freq": "As Needed", "last": "Never"}
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
    app = ttk.Window(themename="flatly")
    FilamentManagerApp(app)
    app.mainloop()