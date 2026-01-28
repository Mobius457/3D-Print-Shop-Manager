import os
import warnings

# --- SUPPRESS WARNINGS & CONFIG ENV ---
os.environ["QT_API"] = "pyqt5"
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, Menu
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import json
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
import threading
import time
import uuid
import ssl
import csv  # <--- Added for Export Feature

# --- OPTIONAL DEPENDENCIES ---
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except: pass

# ======================================================
# CONFIGURATION
# ======================================================

APP_NAME = "PrintShopManager"
VERSION = "v15.1 (Smart Shop + Export)"

# ======================================================
# PATH & SYSTEM LOGIC
# ======================================================

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

DATA_DIR = get_base_path()
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# DATABASE FILES
DB_FILE = os.path.join(DATA_DIR, "filament_inventory.json")
HISTORY_FILE = os.path.join(DATA_DIR, "sales_history.json")
MAINT_FILE = os.path.join(DATA_DIR, "maintenance_log.json")
QUEUE_FILE = os.path.join(DATA_DIR, "job_queue.json")
DOCS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "3D_Print_Receipts")
if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR, exist_ok=True)

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

IMAGE_FILE = resource_path("spool_reference.png")

# ======================================================
# COLOR MANAGER
# ======================================================
class ColorManager:
    def __init__(self):
        self.cache = {}
        self.color_map = {
            'red': '#FF0000', 'crimson': '#DC143C', 'maroon': '#800000', 'ruby': '#E0115F',
            'blue': '#0000FF', 'navy': '#000080', 'royal': '#4169E1', 'sky': '#87CEEB', 'cyan': '#00FFFF', 'teal': '#008080',
            'green': '#008000', 'lime': '#00FF00', 'olive': '#808000', 'forest': '#228B22',
            'yellow': '#FFFF00', 'gold': '#FFD700', 'orange': '#FFA500', 'coral': '#FF7F50',
            'purple': '#800080', 'violet': '#EE82EE', 'lavender': '#E6E6FA', 'magenta': '#FF00FF',
            'black': '#101010', 'charcoal': '#36454F', 'matte black': '#202020',
            'white': '#FFFFFF', 'ivory': '#FFFFF0', 'grey': '#808080', 'gray': '#808080', 'silver': '#C0C0C0',
            'brown': '#A52A2A', 'beige': '#F5F5DC', 'tan': '#D2B48C', 'wood': '#DEB887',
            'pink': '#FFC0CB', 'clear': '#E0E0E0', 'transparent': '#E0E0E0', 'rainbow': 'RAINBOW'
        }

    def get_hex(self, color_name):
        c = color_name.lower()
        clean = re.sub(r'(matte|silk|basic|pla|petg|abs|tpu|\+|pro|tough|hyper|high speed)', '', c).strip()
        if clean in self.color_map: return self.color_map[clean]
        for key, hex_val in self.color_map.items():
            if key in clean: return hex_val
        return "#CCCCCC"

    def get_icon(self, color_name):
        hex_code = self.get_hex(color_name)
        cache_key = f"{color_name}_{hex_code}"
        if cache_key in self.cache: return self.cache[cache_key]
        size = 16
        img = Image.new("RGBA", (size, size), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        if hex_code == 'RAINBOW':
            colors = ['#FF0000', '#FFA500', '#FFFF00', '#008000', '#0000FF', '#4B0082', '#EE82EE']
            for i, col in enumerate(colors):
                draw.arc([1, 1, size-2, size-2], start=(i*(360/7)), end=((i+1)*(360/7)), fill=col, width=6)
        else:
            draw.ellipse([1, 1, size-2, size-2], fill=hex_code, outline="#666666", width=1)
        tk_img = ImageTk.PhotoImage(img)
        self.cache[cache_key] = tk_img
        return tk_img

# ======================================================
# AI MANAGER
# ======================================================
class AIManager:
    def __init__(self):
        self.api_key = self.load_api_key()
        self.model = None
        if HAS_GENAI and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except: pass

    def load_api_key(self):
        if os.path.exists(CONFIG_FILE):
            try: return json.load(open(CONFIG_FILE)).get('gemini_api_key', '')
            except: pass
        return ''

    def save_api_key(self, key):
        self.api_key = key
        d = {}
        if os.path.exists(CONFIG_FILE): d = json.load(open(CONFIG_FILE))
        d['gemini_api_key'] = key
        json.dump(d, open(CONFIG_FILE,'w'))
        if HAS_GENAI: genai.configure(api_key=key); self.model = genai.GenerativeModel('gemini-1.5-flash')

    def analyze_slicer_screenshot(self, image_path):
        if not self.model: return {'error': "AI Model not loaded. Check API Key."}
        try:
            img = Image.open(image_path)
            prompt = """Analyze this 3D printer slicer screenshot. Extract the print time, filament usage (grams), and estimated cost.
            Return ONLY a JSON object with these keys: {"hours": float, "minutes": float, "grams": float, "cost": float}.
            Example: {"hours": 1, "minutes": 30, "grams": 50.5, "cost": 1.25}. Do not include markdown."""
            response = self.model.generate_content([prompt, img])
            txt = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(txt)
        except Exception as e: return {'error': str(e)}

    def estimate_price(self, brand, material, color):
        if not self.model: return None
        try:
            prompt = f"Estimate the retail price in USD for a 1kg spool of {brand} {material} filament in {color}. Return JSON: {{'price_estimate': '$XX.XX'}}"
            response = self.model.generate_content(prompt)
            txt = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(txt)
        except: return None

# ======================================================
# BAMBU CLIENT
# ======================================================
class BambuPrinterClient:
    def __init__(self, host, username, password, serial, status_callback, finish_callback):
        self.host = host; self.username = username; self.password = password; self.serial = serial
        self.status_callback = status_callback; self.finish_callback = finish_callback
        self.client = None; self.connected = False; self.seq_id = 0
        self.last_state = {"gcode_state": "OFFLINE", "mc_percent": 0, "nozzle_temper": 0, "bed_temper": 0}

    def connect(self):
        if not HAS_MQTT: return False
        if not self.password or self.password == "None": return False
        try:
            cid = f"PrintShop_{uuid.uuid4().hex[:8]}"
            self.client = mqtt.Client(client_id=cid, callback_api_version=mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
            ssl_ctx = ssl.create_default_context(); ssl_ctx.check_hostname = False; ssl_ctx.verify_mode = ssl.CERT_NONE
            self.client.tls_set_context(ssl_ctx); self.client.tls_insecure_set(True)
            self.client.username_pw_set(self.username, self.password)
            self.client.on_connect = self.on_connect; self.client.on_disconnect = self.on_disconnect; self.client.on_message = self.on_message
            self.client.connect(self.host, 8883, 60); self.client.loop_start(); self.start_heartbeat()
            return True
        except: return False

    def start_heartbeat(self):
        def loop():
            while True:
                if self.connected: self.send_pushall()
                time.sleep(5)
        threading.Thread(target=loop, daemon=True).start()

    def send_pushall(self):
        self.seq_id += 1
        payload = {"pushing": {"sequence_id": str(self.seq_id), "command": "pushall"}}
        try: self.client.publish(f"device/{self.serial}/request", json.dumps(payload))
        except: pass

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            client.subscribe(f"device/{self.serial}/report")
            self.send_pushall()

    def on_disconnect(self, client, userdata, flags, rc, properties=None): self.connected = False
    def on_message(self, client, userdata, msg):
        try:
            raw_txt = msg.payload.decode()
            payload = json.loads(raw_txt)
            p = payload.get('print', payload)
            for key in ["gcode_state", "mc_percent", "mc_remaining_time", "nozzle_temper", "bed_temper", "subtask_name"]:
                if key in p: self.last_state[key] = p[key]
            self.status_callback(self.last_state)
        except: pass
    def disconnect(self):
        if self.client: self.client.loop_stop(); self.client.disconnect(); self.connected = False

# ======================================================
# MAIN APP
# ======================================================
class FilamentManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Print Shop Manager - {VERSION}")
        self.root.geometry("1600x900")
        
        self.current_theme_name = "litera"
        self.setup_theme_colors()
        self.style = ttk.Style(theme=self.current_theme_name)
        self.configure_styles()
        
        self.ai_manager = AIManager()
        self.color_manager = ColorManager()
        self.icon_cache = {}; self.ref_images_cache = [] 
        
        self.perform_auto_backup()
        self.defaults = self.load_sticky_settings()
        self.printer_cfg = self.load_printer_config()
        self.load_all_data() 
        self.init_materials_data()
        self.init_resource_links()
        if not self.maintenance: self.init_default_maintenance()
            
        self.current_job_filaments = []
        self.calc_vals = {"mat_cost": 0, "electricity": 0, "labor": 0, "subtotal": 0, "total": 0, "profit": 0, "hours": 0, "rate": 0}

        # --- LAYOUT ---
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill="both", expand=True)
        
        self.sidebar = ttk.Frame(self.main_container, style='Sidebar.TFrame', width=250, padding=10)
        self.sidebar.pack(side="left", fill="y")
        
        ttk.Label(self.sidebar, text="Print Shop Manager", font=("Segoe UI", 18, "bold"), foreground=self.PURPLE_MAIN, background=self.CARD_BG).pack(pady=20, anchor="w", padx=10)
        
        self.nav_btns = {}
        self.create_nav_btn("Dashboard", self.show_dashboard)
        self.create_nav_btn("Projects", self.show_history)
        self.create_nav_btn("Inventory", self.show_inventory)
        self.create_nav_btn("Calculator", self.show_calculator)
        self.create_nav_btn("Slicer Reader (AI)", self.show_ai_reader)
        ttk.Separator(self.sidebar).pack(fill="x", pady=10, padx=5)
        self.create_nav_btn("Reference", self.show_reference)
        self.create_nav_btn("Queue", self.show_queue)
        self.create_nav_btn("Maintenance", self.show_maintenance)
        self.create_nav_btn("Settings", self.configure_printer)
        
        ttk.Button(self.sidebar, text="🌗 Toggle Theme", style='Ghost.TButton', command=self.toggle_theme).pack(side="bottom", fill="x", pady=10)

        self.content_area = ttk.Frame(self.main_container, style='TFrame', padding=20)
        self.content_area.pack(side="right", fill="both", expand=True)

        self.current_page_method = self.show_dashboard 
        self.printer_client = None
        if self.printer_cfg.get("enabled"): self.start_printer_listener()
            
        self.show_dashboard()

    def configure_styles(self):
        self.style.configure("Treeview", rowheight=30, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        self.style.configure('TFrame', background=self.BG_COLOR)
        self.style.configure('Card.TFrame', background=self.CARD_BG, relief="flat")
        self.style.configure('Sidebar.TFrame', background=self.CARD_BG)
        self.style.configure('Success.TButton', font=("Segoe UI", 9), background='#28a745', foreground='white')
        self.style.configure('Primary.TButton', font=("Segoe UI", 9), background='#007bff', foreground='white')
        self.style.configure('Danger.TButton', font=("Segoe UI", 9), background='#dc3545', foreground='white')
        self.style.configure('Secondary.TButton', font=("Segoe UI", 9), background='#6c757d', foreground='white')
        self.style.configure('Purple.TButton', background=self.PURPLE_MAIN, foreground='white', font=("Segoe UI", 9, "bold"))
        self.style.configure('Ghost.TButton', background=self.CARD_BG, foreground=self.PURPLE_MAIN, font=("Segoe UI", 9), borderwidth=1)
        self.style.configure('Nav.TButton', background=self.CARD_BG, foreground=self.TEXT_COLOR, font=("Segoe UI", 11), anchor="w", padding=15, relief="flat")
        self.style.map('Nav.TButton', background=[('active', self.PURPLE_LIGHT)], foreground=[('active', self.PURPLE_MAIN)])
        self.style.configure('TLabel', background=self.BG_COLOR, foreground=self.TEXT_COLOR)
        self.style.configure('Card.TLabel', background=self.CARD_BG, foreground=self.TEXT_COLOR)
        self.style.configure('Stat.TLabel', background=self.CARD_BG, foreground=self.TEXT_COLOR, font=("Segoe UI", 24, "bold"))
        self.style.configure('Sub.TLabel', background=self.CARD_BG, foreground=self.TEXT_SECONDARY, font=("Segoe UI", 9))

    def setup_theme_colors(self):
        if self.current_theme_name == "litera":
            self.PURPLE_MAIN = "#7c3aed"; self.PURPLE_LIGHT = "#f3e8ff"; self.BG_COLOR = "#f8f9fa"; self.CARD_BG = "#ffffff"; self.TEXT_COLOR = "#333333"; self.TEXT_SECONDARY = "#6b7280"
        else:
            self.PURPLE_MAIN = "#a29bfe"; self.PURPLE_LIGHT = "#444444"; self.BG_COLOR = "#222222"; self.CARD_BG = "#303030"; self.TEXT_COLOR = "#ffffff"; self.TEXT_SECONDARY = "#aaaaaa"

    def toggle_theme(self):
        new_theme = "darkly" if self.current_theme_name == "litera" else "litera"
        self.current_theme_name = new_theme
        self.style.theme_use(new_theme)
        self.setup_theme_colors()
        self.configure_styles()
        self.sidebar.configure(style='Sidebar.TFrame')
        for widget in self.sidebar.winfo_children():
            if isinstance(widget, ttk.Label): widget.configure(background=self.CARD_BG, foreground=self.PURPLE_MAIN)
            if isinstance(widget, ttk.Button): widget.configure(style='Nav.TButton' if 'Nav' in str(widget.winfo_name) else 'Ghost.TButton')
        self.current_page_method() 

    # --- UI HELPERS ---
    def clear_content(self):
        for widget in self.content_area.winfo_children(): widget.destroy()

    def create_card(self, parent, title=None, row=0, col=0, colspan=1, rowspan=1, padding=20):
        card = ttk.Frame(parent, style='Card.TFrame', padding=padding) 
        card.grid(row=row, column=col, columnspan=colspan, rowspan=rowspan, sticky="nsew", padx=10, pady=10)
        if title: ttk.Label(card, text=title, font=("Segoe UI", 12, "bold"), background=self.CARD_BG, foreground=self.TEXT_COLOR).pack(anchor="w", pady=(0, 15))
        return card

    def create_stat_card(self, parent, title, value, subtext, icon_text="📦"):
        card = ttk.Frame(parent, style='Card.TFrame', padding=20)
        h = ttk.Frame(card, style='Card.TFrame'); h.pack(fill="x", pady=(0, 10))
        ttk.Label(h, text=title, font=("Segoe UI", 10, "bold"), background=self.CARD_BG, foreground=self.TEXT_COLOR).pack(side="left")
        ttk.Label(h, text=icon_text, font=("Segoe UI", 14), background=self.CARD_BG, foreground=self.TEXT_SECONDARY).pack(side="right")
        
        # Save references to update later
        val_lbl = ttk.Label(card, text=value, style='Stat.TLabel')
        val_lbl.pack(anchor="w")
        sub_lbl = ttk.Label(card, text=subtext, style='Sub.TLabel')
        sub_lbl.pack(anchor="w", pady=(5,0))
        
        return card, val_lbl, sub_lbl

    def create_nav_btn(self, text, command):
        def wrapper():
            self.current_page_method = command
            command()
        btn = ttk.Button(self.sidebar, text=f"  {text}", style='Nav.TButton', command=wrapper)
        btn.pack(fill="x", pady=2)
        self.nav_btns[text] = btn

    # --- DASHBOARD ---
    def show_dashboard(self):
        self.current_page_method = self.show_dashboard
        self.clear_content()
        head = ttk.Frame(self.content_area); head.pack(fill="x", pady=(0, 30))
        ttk.Label(head, text="Projects Dashboard", font=("Segoe UI", 24, "bold")).pack(side="left")
        self.lbl_printer_status = ttk.Label(head, text="Printer: Offline", font=("Segoe UI", 10), foreground=self.TEXT_SECONDARY, background=self.BG_COLOR)
        self.lbl_printer_status.pack(side="right", padx=10)
        ttk.Button(head, text="Refresh", style='Ghost.TButton', command=self.refresh_dashboard).pack(side="right")

        grid = ttk.Frame(self.content_area); grid.pack(fill="x")
        grid.columnconfigure(0, weight=1); grid.columnconfigure(1, weight=1); grid.columnconfigure(2, weight=1); grid.columnconfigure(3, weight=1)

        # Create Cards (Init with 0/loading)
        c1, self.lbl_stat_proj, self.lbl_sub_proj = self.create_stat_card(grid, "Total Projects", "...", "...", "📦")
        c1.grid(row=0, column=0, sticky="ew", padx=10)

        c2, self.lbl_stat_cost, self.lbl_sub_cost = self.create_stat_card(grid, "Avg Cost", "...", "...", "◎")
        c2.grid(row=0, column=1, sticky="ew", padx=10)

        c3, self.lbl_stat_inv, self.lbl_sub_inv = self.create_stat_card(grid, "Inventory", "...", "...", "📉")
        c3.grid(row=0, column=2, sticky="ew", padx=10)

        c4, self.lbl_stat_low, self.lbl_sub_low = self.create_stat_card(grid, "Low Stock", "...", "...", "⚠️")
        c4.grid(row=0, column=3, sticky="ew", padx=10)

        # Graph
        if HAS_MATPLOTLIB:
            chart_wrapper = ttk.Frame(self.content_area)
            chart_wrapper.pack(fill="both", expand=True, pady=20)
            chart_frame = self.create_card(chart_wrapper, "Revenue Trend (Last 7 Days)", row=0, col=0)
            chart_wrapper.columnconfigure(0, weight=1) 
            self.draw_dashboard_chart(chart_frame)

        self.refresh_dashboard_data()

    def draw_dashboard_chart(self, parent):
        f = plt.Figure(figsize=(5, 3), dpi=100, facecolor=self.CARD_BG)
        ax = f.add_subplot(111)
        
        daily_totals = {}
        for h in self.history:
            try:
                d_str = h['date'][:10]
                val = float(h.get('sold_for', 0))
                daily_totals[d_str] = daily_totals.get(d_str, 0) + val
            except: pass
        
        sorted_dates = sorted(daily_totals.keys())
        display_dates = sorted_dates[-7:] if sorted_dates else ["Today"]
        display_vals = [daily_totals[d] for d in display_dates] if sorted_dates else [0]
        
        ax.plot(display_dates, display_vals, color=self.PURPLE_MAIN, marker='o', linewidth=2, markersize=6)
        ax.set_facecolor(self.CARD_BG)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['left'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        ax.tick_params(axis='x', colors=self.TEXT_COLOR, rotation=45, labelsize=8) 
        ax.tick_params(axis='y', colors=self.TEXT_COLOR)
        
        for i, v in enumerate(display_vals):
            ax.text(i, v + (max(display_vals)*0.05 if display_vals else 1), f"${int(v)}", 
                    ha='center', va='bottom', fontsize=8, color=self.TEXT_COLOR)

        f.tight_layout()
        canvas = FigureCanvasTkAgg(f, parent); canvas.get_tk_widget().pack(fill="both", expand=True)

    def refresh_dashboard(self): 
        self.load_all_data()
        self.refresh_dashboard_data()

    def refresh_dashboard_data(self):
        # 1. Projects
        total_p = len(self.history)
        active_p = len(self.queue)
        self.lbl_stat_proj.config(text=str(total_p))
        self.lbl_sub_proj.config(text=f"{active_p} active in queue")

        # 2. Avg Cost
        costs = [float(h.get('cost', 0)) for h in self.history]
        avg_cost = sum(costs) / len(costs) if costs else 0
        self.lbl_stat_cost.config(text=f"${avg_cost:.2f}")
        self.lbl_sub_cost.config(text="Per finished project")

        # 3. Inventory
        total_g = sum(int(i.get('weight', 0)) for i in self.inventory)
        self.lbl_stat_inv.config(text=f"{total_g/1000:.1f} kg")
        self.lbl_sub_inv.config(text="Total filament remaining")

        # 4. Low Stock
        low_count = sum(1 for i in self.inventory if int(i.get('weight',0)) < 200)
        self.lbl_stat_low.config(text=str(low_count))
        self.lbl_sub_low.config(text="Spools < 200g")

    # --- INVENTORY ---
    def show_inventory(self):
        self.current_page_method = self.show_inventory
        self.clear_content()
        
        form_frame = ttk.Frame(self.content_area, style='Card.TFrame', padding=15)
        form_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(form_frame, text="Add New Spool", font=("Segoe UI", 10, "bold"), background=self.CARD_BG).grid(row=0, column=0, sticky="w", padx=5)
        
        self.v_brand = tk.StringVar(); self.v_id = tk.StringVar(); self.v_mat = tk.StringVar(value="PLA"); self.v_color = tk.StringVar()
        self.v_cost = tk.StringVar(value="20.00"); self.v_weight = tk.StringVar(value="1000")
        self.v_benchy = tk.BooleanVar(value=False); self.v_type = tk.StringVar(value="Plastic")
        
        f1 = ttk.Frame(form_frame, style='Card.TFrame'); f1.grid(row=1, column=0, columnspan=10, sticky="w", pady=5)
        ttk.Label(f1, text="Brand/Name:", background=self.CARD_BG).pack(side="left", padx=(5,0))
        ttk.Entry(f1, textvariable=self.v_brand, width=20).pack(side="left", padx=5)
        ttk.Label(f1, text="ID / Label:", background=self.CARD_BG).pack(side="left", padx=(10,0))
        ttk.Entry(f1, textvariable=self.v_id, width=8).pack(side="left", padx=5)
        ttk.Button(f1, text="Auto", style='Secondary.TButton', command=self.auto_gen_id).pack(side="left")
        ttk.Label(f1, text="Material:", background=self.CARD_BG).pack(side="left", padx=(10,0))
        ttk.Combobox(f1, textvariable=self.v_mat, values=["PLA", "PETG", "ABS", "TPU"], width=8).pack(side="left", padx=5)
        ttk.Label(f1, text="Color:", background=self.CARD_BG).pack(side="left", padx=(10,0))
        ttk.Entry(f1, textvariable=self.v_color, width=12).pack(side="left", padx=5)
        
        f2 = ttk.Frame(form_frame, style='Card.TFrame'); f2.grid(row=2, column=0, columnspan=10, sticky="w", pady=5)
        ttk.Label(f2, text="Cost ($):", background=self.CARD_BG).pack(side="left", padx=(5,0))
        ttk.Entry(f2, textvariable=self.v_cost, width=8).pack(side="left", padx=5)
        ttk.Label(f2, text="Weight (g):", background=self.CARD_BG).pack(side="left", padx=(10,0))
        ttk.Entry(f2, textvariable=self.v_weight, width=8).pack(side="left", padx=5)
        ttk.Checkbutton(f2, text="Benchy?", variable=self.v_benchy, bootstyle="round-toggle").pack(side="left", padx=15)
        ttk.Button(f2, text="Add Spool", style='Success.TButton', command=self.save_spool).pack(side="left", padx=5)
        ttk.Button(f2, text="Cancel", style='Secondary.TButton', command=self.clear_form).pack(side="left")

        act_frame = ttk.Frame(self.content_area); act_frame.pack(fill="x", pady=5)
        ttk.Button(act_frame, text="Edit Selected", style='Primary.TButton', command=self.edit_selected).pack(side="left", padx=2)
        ttk.Button(act_frame, text="Set Material", style='Primary.TButton', command=self.bulk_set_material).pack(side="left", padx=2)
        ttk.Button(act_frame, text="Delete", style='Danger.TButton', command=self.delete_spool).pack(side="left", padx=2)
        ttk.Button(act_frame, text="Check Price", style='Secondary.TButton', command=self.check_price).pack(side="left", padx=2)
        ttk.Button(act_frame, text="✅/❌ Benchy", style='Ghost.TButton', command=self.toggle_benchy).pack(side="left", padx=10)
        
        # --- NEW EXPORT BUTTON ---
        ttk.Button(act_frame, text="💾 Export CSV", style='Success.TButton', command=self.export_inventory_to_csv).pack(side="left", padx=10)
        # -------------------------

        ttk.Label(act_frame, text="🔍 Filter:", background=self.BG_COLOR).pack(side="left", padx=(20, 5))
        self.entry_search = ttk.Entry(act_frame)
        self.entry_search.pack(side="left", fill="x", expand=True)
        self.entry_search.bind("<KeyRelease>", self.filter_inventory)

        cols = ("ID", "Name", "Material", "ColorName", "Weight", "Cost", "Benchy")
        self.tree = ttk.Treeview(self.content_area, columns=cols, show="tree headings", height=15)
        
        self.tree.column("#0", width=50, anchor="center")
        self.tree.heading("#0", text="Color")
        self.tree.column("ID", width=60, anchor="center")
        self.tree.column("Name", width=200, anchor="w")
        self.tree.column("Material", width=80, anchor="center")
        self.tree.column("ColorName", width=120, anchor="w")
        self.tree.column("Weight", width=80, anchor="center")
        self.tree.column("Cost", width=80, anchor="center")
        self.tree.column("Benchy", width=80, anchor="center")
        
        for c in cols: self.tree.heading(c, text=c)
        self.tree.pack(fill="both", expand=True, pady=5)
        
        self.refresh_inventory_list()

    def export_inventory_to_csv(self):
        fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")], title="Export Inventory")
        if not fpath: return
        try:
            with open(fpath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["ID", "Name", "Material", "Color", "Weight (g)", "Cost ($)", "Benchy"])
                for item in self.inventory:
                    writer.writerow([
                        item.get('id', ''),
                        item.get('name', ''),
                        item.get('material', ''),
                        item.get('color', ''),
                        item.get('weight', 0),
                        item.get('cost', 0),
                        item.get('benchy', '❌')
                    ])
            messagebox.showinfo("Success", f"Inventory exported to:\n{fpath}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def auto_gen_id(self):
        next_id = 1
        existing_ids = [int(i['id']) for i in self.inventory if str(i['id']).isdigit()]
        if existing_ids: next_id = max(existing_ids) + 1
        self.v_id.set(str(next_id).zfill(3))

    def clear_form(self):
        self.v_brand.set(""); self.v_color.set(""); self.v_id.set(""); self.v_weight.set("1000"); self.v_cost.set("20.00")

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel: return
        val = self.tree.item(sel[0])['values']
        self.v_id.set(str(val[0])); self.v_brand.set(val[1]); self.v_mat.set(val[2])
        self.v_color.set(val[3]); self.v_weight.set(val[4]); self.v_cost.set(str(val[5]).replace("$",""))
        self.v_benchy.set(True if "✅" in str(val[6]) else False)

    def bulk_set_material(self):
        mat = simpledialog.askstring("Bulk Update", "Enter Material (e.g., PLA):")
        if mat:
            for item_id in self.tree.selection():
                val = self.tree.item(item_id)['values']; spool_id = str(val[0])
                for i in self.inventory:
                    if str(i.get('id')) == spool_id: i['material'] = mat
            self.save_json(self.inventory, DB_FILE); self.refresh_inventory_list()

    def toggle_benchy(self):
        sel = self.tree.selection()
        if not sel: return
        val = self.tree.item(sel[0])['values']; spool_id = str(val[0])
        for item in self.inventory:
            if str(item.get('id')) == spool_id:
                curr = item.get('benchy', '❌')
                item['benchy'] = '❌' if curr == '✅' else '✅'
                break
        self.save_json(self.inventory, DB_FILE); self.refresh_inventory_list()

    def delete_spool(self):
        sel = self.tree.selection()
        if not sel: return
        val = self.tree.item(sel[0])['values']; spool_id = str(val[0])
        if messagebox.askyesno("Confirm", f"Delete Spool {spool_id}?"):
            self.inventory = [i for i in self.inventory if str(i.get('id')) != spool_id]
            self.save_json(self.inventory, DB_FILE); self.refresh_inventory_list()

    def filter_inventory(self, event):
        query = self.entry_search.get().lower()
        for item in self.tree.get_children(): self.tree.delete(item)
        for item in self.inventory:
            if query in str(item).lower():
                c = float(item.get('cost', 0))
                icon = self.color_manager.get_icon(item.get('color', ''))
                self.tree.insert("", "end", image=icon, values=(item.get('id', '???'), item.get('name'), item.get('material'), item.get('color'), int(item.get('weight',0)), f"${c:.2f}", item.get('benchy', '❌')))

    def save_spool(self):
        try:
            sid = self.v_id.get()
            if not sid: self.auto_gen_id(); sid = self.v_id.get()
            item = {"id": sid, "name": self.v_brand.get(), "material": self.v_mat.get(), "color": self.v_color.get(), "weight": float(self.v_weight.get()), "cost": float(self.v_cost.get()), "benchy": "✅" if self.v_benchy.get() else "❌"}
            self.inventory = [i for i in self.inventory if str(i.get('id')) != sid]
            self.inventory.append(item)
            self.inventory.sort(key=lambda x: int(x['id']) if str(x['id']).isdigit() else 9999)
            self.save_json(self.inventory, DB_FILE); self.refresh_inventory_list(); self.clear_form(); messagebox.showinfo("Success", "Spool Saved")
        except: messagebox.showerror("Error", "Check numeric fields")

    def refresh_inventory_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for item in self.inventory:
            w = int(item.get('weight', 0)); c = float(item.get('cost', 0))
            icon = self.color_manager.get_icon(item.get('color', ''))
            self.tree.insert("", "end", image=icon, values=(item.get('id', '???'), item.get('name'), item.get('material'), item.get('color'), w, f"${c:.2f}", item.get('benchy', '❌')))

    def check_price(self):
        sel = self.tree.selection()
        if not sel: return
        val = self.tree.item(sel[0])['values']
        brand = val[1]; mat = val[2]; col = val[3]
        webbrowser.open(f"https://www.google.com/search?q={brand} {mat} {col} filament price&tbm=shop")
        if self.ai_manager.api_key:
            def run():
                res = self.ai_manager.estimate_price(brand, mat, col)
                if res and 'price_estimate' in res:
                    messagebox.showinfo("AI Estimate", f"Estimated Market Price: {res['price_estimate']}")
            threading.Thread(target=run).start()

    def configure_ai(self):
        key = simpledialog.askstring("Google AI Studio", "Enter Gemini API Key:\n(Get one from aistudio.google.com)", initialvalue=self.ai_manager.api_key)
        if key:
            self.ai_manager.save_api_key(key)
            messagebox.showinfo("Success", "API Key Saved.")

    # --- AI SLICER READER ---
    def show_ai_reader(self):
        self.current_page_method = self.show_ai_reader
        self.clear_content()
        container = ttk.Frame(self.content_area); container.place(relx=0.5, rely=0.5, anchor="center")
        icon_lbl = ttk.Label(container, text="⛶", font=("Segoe UI", 30), foreground=self.PURPLE_MAIN, background=self.BG_COLOR)
        icon_lbl.pack()
        ttk.Label(container, text="AI Slicer Reader", font=("Segoe UI", 24, "bold"), foreground=self.PURPLE_MAIN).pack(pady=(0,10))
        ttk.Label(container, text="Upload a screenshot from your slicer to extract data.", font=("Segoe UI", 11), foreground="gray").pack(pady=5)
        card = ttk.Frame(container, style='Card.TFrame', padding=40)
        card.pack(ipadx=20)
        ttk.Label(card, text="📄", font=("Segoe UI", 24), background=self.CARD_BG).pack()
        ttk.Label(card, text="Upload Slicer Screenshot", font=("Segoe UI", 12, "bold"), background=self.CARD_BG).pack(pady=10)
        ttk.Label(card, text="Drag and drop or click to browse (PNG, JPG)", foreground="gray", background=self.CARD_BG).pack(pady=(0, 20))
        self.btn_slicer_scan = ttk.Button(card, text="↥ Choose File", style='Purple.TButton', command=self.open_slicer_scanner)
        self.btn_slicer_scan.pack(fill="x", pady=5)
        if not self.ai_manager.api_key: ttk.Button(container, text="⚙️ Configure API Key", style='Ghost.TButton', command=self.configure_ai).pack(pady=5)

    def open_slicer_scanner(self):
        if not self.ai_manager.api_key: self.configure_ai(); return
        path = filedialog.askopenfilename()
        if not path: return
        self.btn_slicer_scan.config(text="⏳ Analyzing...", state="disabled")
        def run():
             res = self.ai_manager.analyze_slicer_screenshot(path)
             self.root.after(0, lambda: self._process_slicer_results(res))
        threading.Thread(target=run).start()

    def _process_slicer_results(self, res):
        self.btn_slicer_scan.config(text="Upload Slicer Screenshot", state="normal")
        if not res or 'error' in res:
            err_msg = res.get('error') if res else "Unknown error"
            messagebox.showerror("AI Error", f"Failed: {err_msg}"); return
        self.show_calculator()
        if 'grams' in res: 
            self.entry_calc_grams.delete(0, tk.END)
            self.entry_calc_grams.insert(0, str(res['grams']))
        if 'hours' in res or 'minutes' in res:
            total_h = res.get('hours', 0) + (res.get('minutes', 0) / 60)
            self.entry_hours.delete(0, tk.END)
            self.entry_hours.insert(0, f"{total_h:.2f}")
        messagebox.showinfo("Success", "Slicer data extracted!")

    # --- CALCULATOR ---
    def show_calculator(self):
        self.current_page_method = self.show_calculator
        self.clear_content()
        ttk.Label(self.content_area, text="Calculator", font=("Segoe UI", 20, "bold")).pack(pady=10)
        self.tab_calc = ttk.Frame(self.content_area); self.tab_calc.pack(fill="both", expand=True)
        
        f = ttk.Frame(self.tab_calc); f.pack(fill="both", expand=True, padx=20)
        ttk.Label(f, text="Job Name:").pack(anchor="w"); self.entry_job_name = ttk.Entry(f); self.entry_job_name.pack(fill="x")
        ttk.Label(f, text="Spool:").pack(anchor="w"); self.combo_filaments = ttk.Combobox(f, state="readonly"); self.combo_filaments.pack(fill="x")
        self.update_filament_dropdown()
        ttk.Label(f, text="Grams:").pack(anchor="w"); self.entry_calc_grams = ttk.Entry(f); self.entry_calc_grams.pack(fill="x")
        
        r1 = ttk.Frame(f); r1.pack(fill="x", pady=5)
        ttk.Label(r1, text="Time (h):").pack(side="left"); self.entry_hours = ttk.Entry(r1, width=5); self.entry_hours.pack(side="left", padx=5)
        ttk.Label(r1, text="Rate ($/h):").pack(side="left"); self.entry_mach_rate = ttk.Entry(r1, width=5); self.entry_mach_rate.pack(side="left", padx=5)
        self.entry_hours.insert(0,"0")
        self.entry_mach_rate.insert(0, self.defaults.get('rate', "0.75"))
        
        r2 = ttk.Frame(f); r2.pack(fill="x", pady=5)
        ttk.Label(r2, text="Labor ($):").pack(side="left"); self.entry_processing = ttk.Entry(r2, width=5); self.entry_processing.pack(side="left", padx=5)
        ttk.Label(r2, text="Markup (x):").pack(side="left"); self.entry_markup = ttk.Entry(r2, width=5); self.entry_markup.pack(side="left", padx=5)
        self.entry_processing.insert(0, self.defaults.get('labor', "0"))
        self.entry_markup.insert(0, self.defaults.get('markup', "2.5"))

        self.var_round = tk.BooleanVar(); self.var_donate = tk.BooleanVar()
        ttk.Checkbutton(f, text="Round to $", variable=self.var_round).pack(anchor="w")
        ttk.Checkbutton(f, text="Donation", variable=self.var_donate).pack(anchor="w")
        
        ttk.Button(f, text="Calculate", style='Purple.TButton', command=self.calculate_quote).pack(pady=10)
        self.lbl_breakdown = ttk.Label(f, text="...", font=("Consolas", 12)); self.lbl_breakdown.pack()
        
        b_box = ttk.Frame(f); b_box.pack(fill="x", pady=10)
        self.btn_receipt = ttk.Button(b_box, text="Receipt", state="disabled", command=self.generate_receipt); self.btn_receipt.pack(side="left", padx=5)
        self.btn_queue = ttk.Button(b_box, text="Queue", state="disabled", command=self.save_to_queue); self.btn_queue.pack(side="left", padx=5)
        self.btn_deduct = ttk.Button(b_box, text="Sell", state="disabled", command=self.deduct_inventory); self.btn_deduct.pack(side="left", padx=5)
        self.btn_fail = ttk.Button(b_box, text="Fail", state="disabled", command=self.log_failure); self.btn_fail.pack(side="left", padx=5)
        
        self.list_job = tk.Listbox(f)

    def calculate_quote(self):
        if not self.current_job_filaments: self.add_to_job()
        try:
            hours = float(self.entry_hours.get() or 0); rate = float(self.entry_mach_rate.get() or 0.75); labor = float(self.entry_processing.get() or 0); markup = float(self.entry_markup.get() or 1)
            self.save_sticky_settings()
            
            raw_mat_cost = sum(x['cost'] for x in self.current_job_filaments)
            elec_cost = hours * rate; base_cost = raw_mat_cost + elec_cost + labor
            final_price = base_cost * markup
            if self.var_round.get(): final_price = round(final_price)
            display_price = final_price
            if self.var_donate.get(): display_price = 0.00
            profit = display_price - base_cost
            self.calc_vals = {"mat_cost": raw_mat_cost, "electricity": elec_cost, "labor": labor, "subtotal": base_cost, "total": display_price, "profit": profit, "hours": hours, "rate": rate}
            txt = (f"--- QUOTE BREAKDOWN ---\nMaterials:   ${raw_mat_cost:.2f}\nElectricity: ${elec_cost:.2f} ({hours}h @ ${rate}/h)\nLabor:       ${labor:.2f}\n-----------------------\nBASE COST:   ${base_cost:.2f}\nMARKUP:      x{markup}\n=======================\nTOTAL:       ${display_price:.2f}")
            if self.var_donate.get(): txt += " (DONATION)"
            self.lbl_breakdown.config(text=txt)
            for b in [self.btn_receipt, self.btn_queue, self.btn_deduct, self.btn_fail]: b.config(state="normal")
        except Exception as e: messagebox.showerror("Error", str(e))

    def add_to_job(self):
        txt = self.combo_filaments.get()
        if not txt: return
        try:
            g = float(self.entry_calc_grams.get())
            spool = next((s for s in self.inventory if s['name'] in txt), None)
            if spool:
                cost = (spool['cost'] / 1000) * g
                self.current_job_filaments.append({'spool': spool, 'cost': cost, 'grams': g})
                self.list_job.insert(tk.END, f"{spool['name']}: {g}g (${cost:.2f})")
                self.entry_calc_grams.delete(0, tk.END)
        except: pass

    def clear_job(self):
        self.current_job_filaments = []
        self.list_job.delete(0, tk.END)
        self.lbl_breakdown.config(text="...")
        for b in [self.btn_receipt, self.btn_queue, self.btn_deduct, self.btn_fail]: b.config(state="disabled")

    def generate_receipt(self):
        fname = f"Receipt_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        fpath = os.path.join(DOCS_DIR, fname)
        vals = self.calc_vals; is_don = self.var_donate.get()
        header = "DONATION RECEIPT (TAX EXEMPT)" if is_don else "INVOICE"
        lines = ["="*50, f"{header:^50}", "="*50, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", f"Job Name: {self.entry_job_name.get() or 'Custom Job'}", "-"*50, "COST BREAKDOWN:", f" > Materials:       ${vals['mat_cost']:.2f}", f" > Machine/Power:   ${vals['electricity']:.2f} ({vals['hours']}h @ ${vals['rate']}/h)", f" > Labor/Prep:      ${vals['labor']:.2f}", "-"*50, f"SUBTOTAL COST:      ${vals['subtotal']:.2f}", f"MARKUP:              x{self.entry_markup.get()}", "="*50]
        if is_don: lines.append(f"TOTAL DUE:          $0.00"); lines.append(f"TAX DEDUCTIBLE VAL: ${vals['total']:.2f}")
        else: lines.append(f"TOTAL DUE:          ${vals['total']:.2f}")
        lines.append("="*50); lines.append("\nThank you for your business!")
        try:
            with open(fpath, 'w') as f: f.write("\n".join(lines))
            os.startfile(fpath)
        except Exception as e: messagebox.showerror("Error", f"Failed to save receipt: {e}")

    def save_to_queue(self):
        job = {"job": self.entry_job_name.get(), "date_added": datetime.now().strftime("%Y-%m-%d"), "items": self.current_job_filaments}
        self.queue.append(job)
        self.save_json(self.queue, QUEUE_FILE)
        self.clear_job()

    def deduct_inventory(self):
        if messagebox.askyesno("Confirm", "Deduct inventory?"):
            for item in self.current_job_filaments: item['spool']['weight'] -= item['grams']
            self.save_json(self.inventory, DB_FILE)
            rec = {"date": datetime.now().strftime("%Y-%m-%d"), "job": self.entry_job_name.get(), "sold_for": self.calc_vals['total'], "profit": self.calc_vals['profit'], "cost": self.calc_vals['subtotal']}
            self.history.append(rec)
            self.save_json(self.history, HISTORY_FILE)
            self.clear_job()

    def log_failure(self):
        if messagebox.askyesno("Confirm", "Log Failure (Cost only)?"): pass

    # --- RESTORED PAGES ---
    def show_history(self): 
        self.current_page_method = self.show_history
        self.clear_content()
        ttk.Label(self.content_area, text="Projects History", font=("Segoe UI", 20, "bold")).pack(pady=(0,20))
        cols = ("Date", "Job", "Cost", "Price", "Profit")
        self.hist_tree = ttk.Treeview(self.content_area, columns=cols, show="headings"); self.hist_tree.pack(fill="both", expand=True)
        for c in cols: self.hist_tree.heading(c, text=c)
        if not self.history: ttk.Label(self.content_area, text="No projects found.", foreground="gray").pack()
        else: self.refresh_history_list()

    def show_queue(self): 
        self.current_page_method = self.show_queue
        self.clear_content()
        self.build_queue_tab_internal()

    def show_maintenance(self): 
        self.current_page_method = self.show_maintenance
        self.clear_content()
        ttk.Label(self.content_area, text="Maintenance Tracker", font=("Segoe UI", 20, "bold")).pack(pady=10)
        self.build_maintenance_tab_internal()

    def build_queue_tab_internal(self):
        cols = ("Job", "Date"); t = ttk.Treeview(self.content_area, columns=cols, show="headings"); t.pack(fill="both", expand=True)
        for c in cols: t.heading(c, text=c)
        for q in self.queue: t.insert("", "end", values=(q.get('job'), q.get('date_added')))

    def build_maintenance_tab_internal(self):
        cols = ("Task", "Freq", "Last Done"); self.maint_tree = ttk.Treeview(self.content_area, columns=cols, show="headings")
        self.maint_tree.pack(fill="both", expand=True)
        for c in cols: self.maint_tree.heading(c, text=c)
        
        btn_frame = ttk.Frame(self.content_area)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="✅ Do Task Now", command=self.perform_maintenance, style="Success.TButton").pack(side="right")
        self.refresh_maintenance_list()

    def refresh_maintenance_list(self):
        for i in self.maint_tree.get_children(): self.maint_tree.delete(i)
        for item in self.maintenance:
            self.maint_tree.insert("", "end", values=(item['task'], item.get('freq', 'Monthly'), item['last']))

    def perform_maintenance(self):
        sel = self.maint_tree.selection()
        if not sel: return
        val = self.maint_tree.item(sel[0])['values']
        task_name = val[0]
        for item in self.maintenance:
            if item['task'] == task_name:
                item['last'] = datetime.now().strftime("%Y-%m-%d")
                break
        self.save_json(self.maintenance, MAINT_FILE)
        self.refresh_maintenance_list()
        messagebox.showinfo("Done", f"Marked '{task_name}' as done!")

    def refresh_history_list(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        for h in self.history:
            cost = float(h.get('cost', 0))
            price = float(h.get('sold_for', 0))
            profit = float(h.get('profit', 0))
            self.hist_tree.insert("", "end", values=(h.get('date'), h.get('job'), f"${cost:.2f}", f"${price:.2f}", f"${profit:.2f}"))

    # --- RESTORED HELPERS ---
    def init_default_maintenance(self):
        self.maintenance = [
            {"task": "Clean Build Plate (Soap)", "freq": "Daily", "last": "Never"},
            {"task": "Check Nozzle Wear", "freq": "Monthly", "last": "Never"},
            {"task": "Lubricate Z-Rods", "freq": "Quarterly", "last": "Never"},
            {"task": "Tighten Frame Screws", "freq": "Quarterly", "last": "Never"}
        ]
        self.save_json(self.maintenance, MAINT_FILE)

    def load_all_data(self):
        self.inventory = self.load_json(DB_FILE)
        next_id = 1
        for item in self.inventory:
            if 'id' in item and str(item['id']).isdigit():
                val = int(item['id'])
                if val >= next_id: next_id = val + 1
        for item in self.inventory:
            if 'id' not in item: item['id'] = str(next_id).zfill(3); next_id += 1
        self.save_json(self.inventory, DB_FILE)
        self.history = self.load_json(HISTORY_FILE)
        self.maintenance = self.load_json(MAINT_FILE)
        self.queue = self.load_json(QUEUE_FILE)

    def load_json(self, f): 
        if os.path.exists(f): 
            try: return json.load(open(f))
            except: return []
        return []

    def save_json(self, d, f): json.dump(d, open(f,'w'), indent=4)
    
    def perform_auto_backup(self):
        # Auto-backup functionality
        backup_dir = os.path.join(DATA_DIR, "backups")
        if not os.path.exists(backup_dir): os.makedirs(backup_dir)
        fname = f"Backup_Auto_{datetime.now().strftime('%Y%m%d')}.zip"
        fpath = os.path.join(backup_dir, fname)
        if not os.path.exists(fpath):
            try:
                with zipfile.ZipFile(fpath, 'w') as zipf:
                    if os.path.exists(DB_FILE): zipf.write(DB_FILE, arcname="filament_inventory.json")
                    if os.path.exists(HISTORY_FILE): zipf.write(HISTORY_FILE, arcname="sales_history.json")
            except: pass

    def load_sticky_settings(self):
        if os.path.exists(CONFIG_FILE):
            try: return json.load(open(CONFIG_FILE)).get('sticky_settings', {})
            except: pass
        return {}

    def save_sticky_settings(self):
        d = {}
        if os.path.exists(CONFIG_FILE):
            try: d = json.load(open(CONFIG_FILE))
            except: pass
        d['sticky_settings'] = {
            "markup": self.entry_markup.get(),
            "labor": self.entry_processing.get(),
            "rate": self.entry_mach_rate.get()
        }
        json.dump(d, open(CONFIG_FILE, 'w'))

    def update_filament_dropdown(self):
        self.full_filament_list = [f"{i['name']} - {i.get('color','')}" for i in self.inventory]
        self.combo_filaments['values'] = self.full_filament_list

    def load_printer_config(self): 
        if os.path.exists(CONFIG_FILE):
             try: return json.load(open(CONFIG_FILE)).get('printer_cfg', {})
             except: pass
        return {}

    def save_printer_config(self, ip, ac, sn, en, mode, token):
        d = {}
        if os.path.exists(CONFIG_FILE): d = json.load(open(CONFIG_FILE))
        d['printer_cfg'] = {"ip":ip, "access_code":ac, "serial":sn, "enabled":en, "mode":mode, "token":token}
        json.dump(d, open(CONFIG_FILE,'w'))
        self.printer_cfg = d['printer_cfg']

    def start_printer_listener(self, override_token=None):
        if self.printer_client: self.printer_client.disconnect()
        host = self.printer_cfg.get('ip')
        user = "bblp"
        password = self.printer_cfg.get('access_code')
        serial = self.printer_cfg.get('serial')
        if password and serial:
            self.printer_client = BambuPrinterClient(host, user, password, serial, self.on_printer_status_update, lambda x: None)
            self.printer_client.connect()

    def on_printer_status_update(self, data):
        self.root.after(0, lambda: self._update_ui_safe(data))

    def _update_ui_safe(self, data):
        if not hasattr(self, 'lbl_printer_status') or not self.lbl_printer_status.winfo_exists(): return 
        self.lbl_printer_status.config(text=f"Online: {data.get('gcode_state', 'IDLE')}", foreground=self.PURPLE_MAIN)

    # --- RESTORED HELPERS ---
    def init_materials_data(self):
        self.materials_data = {
            "PLA Basics": ("MATERIAL: Standard PLA\n========================\nNozzle: 190-220°C | Bed: 45-60°C\n\nThe standard workhorse. Keep the door OPEN and lid OFF to prevent heat creep (clogs). If corners curl, clean the bed with soap."),
            "PLA Specials (Silk/Dual/Tri)": ("MATERIAL: Silk, Dual-Color, Tri-Color\n=======================================\nNozzle: 210-230°C (Print Hotter!)\nSpeed:  Slow down outer walls (30-50mm/s)\n\n1. SHINE: The slower and hotter you print, the shinier it gets.\n2. CLOGS: Silk expands ('die swell'). If it jams, lower Flow Ratio to 0.95.\n3. DUAL COLOR: Ensure your 'Flush Volumes' are high enough so colors don't look muddy."),
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

    def init_resource_links(self): 
        self.resource_links = {
            "PLA Basics": "https://all3dp.com/1/pla-filament-3d-printing-guide/",
            "PLA Specials (Silk/Dual/Tri)": "https://all3dp.com/2/silk-filament-guide/",
            "PETG Standard": "https://all3dp.com/2/petg-3d-printing-temperature-nozzle-bed-settings/",
            "ABS / ASA": "https://all3dp.com/2/abs-print-settings-temperature-speed-retraction/",
            "TPU (Flexible)": "https://all3dp.com/2/3d-printing-tpu-filament-all-you-need-to-know/",
            "Nylon / PC (Engineering)": "https://all3dp.com/2/nylon-3d-printing-guide/",
            "Abrasives (CF / Glow / Wood)": "https://all3dp.com/2/carbon-fiber-3d-printer-filament-guide/",
            "Bambu Lab Profiles": "https://wiki.bambulab.com/en/home"
        }

    # --- REFERENCE PAGE HELPERS ---
    def show_reference(self):
        self.current_page_method = self.show_reference
        self.clear_content()
        ttk.Label(self.content_area, text="Reference Library", font=("Segoe UI", 20, "bold")).pack(pady=(0,20))
        self.gallery_notebook = ttk.Notebook(self.content_area); self.gallery_notebook.pack(fill="both", expand=True)
        self.build_wiki_tabs()
        self.build_dynamic_gallery_tabs()
        self.build_manual_tab()

    def build_wiki_tabs(self):
        # 1. COMPARISON
        f_comp = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f_comp, text=" 📂 My Profiles ")
        ttk.Label(f_comp, text="ℹ️ Double-click to open/export JSON.", font=("Segoe UI", 9, "italic"), foreground="gray").pack(pady=5)
        cols = ("Material", "Nozzle", "Temp", "Bed", "Fan", "Difficulty", "Path")
        self.fil_tree = ttk.Treeview(f_comp, columns=cols, show="headings")
        for c in cols: self.fil_tree.heading(c, text=c)
        self.fil_tree.column("Path", width=0, stretch=False) # Hide Path
        self.fil_tree.pack(fill="both", expand=True, padx=10)
        self.fil_tree.bind("<Double-1>", self.on_guide_double_click)
        
        data = self.scan_for_custom_profiles()
        if not data: self.fil_tree.insert("", "end", values=("No Profiles Found", "-", "-", "-", "-", "-", ""))
        for row in data: self.fil_tree.insert("", "end", values=row)

        # 2. SPECS
        f_prop = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f_prop, text=" 🧪 Specs ")
        cols_p = ("Material", "Impact (kJ/m²)", "Tensile (MPa)", "Stiffness (MPa)", "HDT (°C)")
        tree_p = ttk.Treeview(f_prop, columns=cols_p, show="headings")
        for c in cols_p: tree_p.heading(c, text=c)
        tree_p.pack(fill="both", expand=True, padx=10)
        props = [("PLA", "26.6", "76", "2750", "57"), ("PETG", "52.7", "81", "1790", "69"), ("ABS", "41.0", "68", "1880", "87"), ("TPU", "125+", "N/A", "N/A", "N/A"), ("PC", "29.5", "112", "2080", "117")]
        for r in props: tree_p.insert("", "end", values=r)

        # 3. SETTINGS
        f_set = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f_set, text=" 🎛️ Settings ")
        cols_s = ("Material", "Speed", "Nozzle", "Bed", "Fan")
        tree_s = ttk.Treeview(f_set, columns=cols_s, show="headings")
        for c in cols_s: tree_s.heading(c, text=c)
        tree_s.pack(fill="both", expand=True, padx=10)
        settings = [("PLA", "<300mm/s", "190-230", "45-60", "100%"), ("PETG", "<200mm/s", "240-270", "70-80", "30-50%"), ("ABS", "<300mm/s", "240-280", "100", "0-20%"), ("TPU", "<40mm/s", "220-240", "35", "100%")]
        for r in settings: tree_s.insert("", "end", values=r)

        # 4. PREP
        f_prep = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f_prep, text=" 🔥 Prep ")
        cols_prep = ("Material", "Dry Temp", "Time", "Enclosure", "Plate")
        tree_prep = ttk.Treeview(f_prep, columns=cols_prep, show="headings")
        for c in cols_prep: tree_prep.heading(c, text=c)
        tree_prep.pack(fill="both", expand=True, padx=10)
        prep = [("PLA", "45°C", "4h", "Open", "Cool/Tex"), ("PETG", "65°C", "6h", "Open", "Tex/Eng"), ("ABS", "80°C", "8h", "Closed", "High Temp"), ("TPU", "55°C", "6h", "Open", "Cool/Tex")]
        for r in prep: tree_prep.insert("", "end", values=r)

        # 5. POST
        f_post = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f_post, text=" 🔨 Post ")
        cols_post = ("Material", "Smoothing", "Annealing", "Glue")
        tree_post = ttk.Treeview(f_post, columns=cols_post, show="headings")
        for c in cols_post: tree_post.heading(c, text=c)
        tree_post.pack(fill="both", expand=True, padx=10)
        post = [("PLA", "Sand/Paint", "55°C", "Superglue"), ("ABS", "Acetone Vapor", "90°C", "ABS Slurry"), ("PETG", "Heat Gun", "70°C", "Superglue")]
        for r in post: tree_post.insert("", "end", values=r)

    def build_dynamic_gallery_tabs(self):
        extensions = ["png", "jpg", "jpeg"]
        image_files = []
        for ext in extensions:
            image_files.extend(glob.glob(os.path.join(get_base_path(), f"ref_*.{ext}")))
        
        for img_path in image_files:
            try:
                tab_frame = ttk.Frame(self.gallery_notebook)
                title = os.path.splitext(os.path.basename(img_path))[0].replace("ref_", "")
                self.gallery_notebook.add(tab_frame, text=f" 📷 {title} ")
                
                pil = Image.open(img_path)
                pil.thumbnail((1000, 600))
                tk_img = ImageTk.PhotoImage(pil)
                self.ref_images_cache.append(tk_img) # Keep ref
                ttk.Label(tab_frame, image=tk_img).pack(expand=True)
            except: pass

    def scan_for_custom_profiles(self):
        custom_rows = []
        sys_files = ["filament_inventory.json", "sales_history.json", "maintenance_log.json", "job_queue.json", "config.json"]
        
        # Scan root and /profiles
        scan_dirs = [get_base_path(), os.path.join(get_base_path(), "profiles")]
        
        for d in scan_dirs:
            if not os.path.exists(d): continue
            for file in os.listdir(d):
                if file.endswith(".json") and file not in sys_files:
                    try:
                        fpath = os.path.join(d, file)
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            data = json.load(f)
                            name = data.get('name', file)
                            if 'filament_settings_id' in data: name = data['filament_settings_id'][0]
                            
                            nozzle = "N/A"
                            if 'nozzle_temperature' in data: nozzle = str(data['nozzle_temperature'][0])
                            elif 'print_temperature' in data: nozzle = str(data['print_temperature'][0])
                            
                            bed = "N/A"
                            if 'bed_temperature' in data: bed = str(data['bed_temperature'][0])
                            
                            diff = "Medium"
                            n_lower = name.lower()
                            if "pla" in n_lower: diff="Easy"
                            elif "abs" in n_lower or "asa" in n_lower: diff="Hard"
                            elif "pc" in n_lower or "nylon" in n_lower: diff="Expert"
                            
                            custom_rows.append((name, "0.4mm", f"{nozzle}°C", f"{bed}°C", "N/A", diff, f"File: {fpath}"))
                    except: pass
        return custom_rows

    def on_guide_double_click(self, event):
        item_id = self.fil_tree.selection()
        if not item_id: return
        val = self.fil_tree.item(item_id[0])['values']
        note = val[6] # Path column
        if "File: " in note:
            path = note.replace("File: ", "").strip()
            if os.path.exists(path):
                self.open_profile_inspector(path)

    def open_profile_inspector(self, fpath):
        try:
            with open(fpath, 'r') as f: data = json.load(f)
            top = tk.Toplevel(self.root); top.title(f"Inspector: {os.path.basename(fpath)}")
            top.geometry("500x600")
            t = ttk.Treeview(top, columns=("Key","Value"), show="headings")
            t.heading("Key", text="Setting"); t.heading("Value", text="Value")
            t.pack(fill="both", expand=True)
            for k, v in data.items():
                t.insert("", "end", values=(k, str(v)))
        except: pass

    def build_manual_tab(self):
        f = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f, text=" 📖 Manual ")
        
        # Search Bar
        sf = ttk.Frame(f); sf.pack(fill="x", pady=5, padx=5)
        ttk.Label(sf, text="🔍 Search Issue:").pack(side="left")
        self.entry_search = ttk.Entry(sf); self.entry_search.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(sf, text="Go", command=self.perform_search).pack(side="left")
        
        # Topic List
        self.mat_var = tk.StringVar()
        cb = ttk.Combobox(f, textvariable=self.mat_var, values=list(self.materials_data.keys()), state="readonly")
        cb.pack(fill="x", padx=10, pady=5)
        
        # Content
        self.txt_info = tk.Text(f, font=("Consolas", 11), padx=15, pady=15, wrap="word")
        self.txt_info.pack(fill="both", expand=True, padx=10, pady=10)
        
        cb.bind("<<ComboboxSelected>>", self.update_material_view)
        
        # Initial Load
        if self.materials_data:
            cb.current(0)
            self.update_material_view(None)

    def perform_search(self):
        q = self.entry_search.get().lower()
        if not q: return
        for k, v in self.materials_data.items():
            if q in k.lower() or q in v.lower():
                self.mat_var.set(k)
                self.update_material_view(None)
                return
        messagebox.showinfo("Result", "No matches found in Manual.")

    def update_material_view(self, e): 
        k = self.mat_var.get()
        if k in self.materials_data:
            self.txt_info.config(state="normal"); self.txt_info.delete("1.0", tk.END); self.txt_info.insert("1.0", self.materials_data[k]); self.txt_info.config(state="disabled")

    def configure_printer(self):
        d = tk.Toplevel(self.root); d.title("Settings"); d.geometry("400x350")
        ttk.Label(d, text="Printer Settings (Local)", font=("Segoe UI", 12, "bold")).pack(pady=10)
        f = ttk.Frame(d, padding=20); f.pack(fill="x")
        ttk.Label(f, text="IP Address:").pack(anchor="w"); e_ip = ttk.Entry(f); e_ip.pack(fill="x")
        e_ip.insert(0, self.printer_cfg.get('ip',''))
        ttk.Label(f, text="Access Code:").pack(anchor="w", pady=(10,0)); e_ac = ttk.Entry(f); e_ac.pack(fill="x")
        e_ac.insert(0, self.printer_cfg.get('access_code',''))
        ttk.Label(f, text="Serial Number:").pack(anchor="w", pady=(10,0)); e_sn_l = ttk.Entry(f); e_sn_l.pack(fill="x")
        e_sn_l.insert(0, self.printer_cfg.get('serial',''))
        
        # ADDED AI KEY FIELD
        ttk.Label(f, text="Google AI API Key:").pack(anchor="w", pady=(10,0)); e_ai = ttk.Entry(f, show="*"); e_ai.pack(fill="x")
        e_ai.insert(0, self.ai_manager.api_key)

        def save_local():
            self.save_printer_config(e_ip.get(), e_ac.get(), e_sn_l.get(), True, "local", "")
            self.ai_manager.save_api_key(e_ai.get())
            self.start_printer_listener()
            d.destroy()
        ttk.Button(f, text="Save & Connect", style='Purple.TButton', command=save_local).pack(pady=20)

if __name__ == "__main__":
    app = ttk.Window(themename="litera") 
    FilamentManagerApp(app)
    app.mainloop()