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
import csv
import math 

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
VERSION = "v17.0 (Inventory Detail & Context Logic)"

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

# ======================================================
# COLOR & ICON MANAGER
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

    def get_icon(self, color_name, is_abrasive=False):
        hex_code = self.get_hex(color_name)
        cache_key = f"{color_name}_{hex_code}_{is_abrasive}"
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
            
        if is_abrasive:
            draw.text((4, -2), "!", fill="red")

        tk_img = ImageTk.PhotoImage(img)
        self.cache[cache_key] = tk_img
        return tk_img

# ======================================================
# AI MANAGER
# ======================================================
class AIManager:
    def __init__(self):
        self.config = self.load_config()
        self.api_key = self.config.get('gemini_api_key', '')
        self.preferred_model = self.config.get('gemini_model', 'gemini-1.5-flash')
        self.model = None
        if HAS_GENAI and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.setup_model(self.preferred_model)
            except: pass

    def setup_model(self, model_name):
        try:
            self.model = genai.GenerativeModel(model_name)
            self.preferred_model = model_name
            return True
        except: return False

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try: return json.load(open(CONFIG_FILE))
            except: pass
        return {}

    def save_config(self, key, model):
        self.api_key = key
        self.preferred_model = model
        d = self.load_config()
        d['gemini_api_key'] = key
        d['gemini_model'] = model
        json.dump(d, open(CONFIG_FILE,'w'))
        if HAS_GENAI: 
            genai.configure(api_key=key)
            self.setup_model(model)

    def analyze_slicer_screenshot(self, image_path):
        if not self.model: return {'error': "AI Model not loaded. Go to Settings -> Test AI."}
        try:
            img = Image.open(image_path)
            prompt = """Analyze this 3D printer slicer screenshot. Extract the print time, filament usage (grams), and estimated cost.
            Return ONLY a JSON object with these keys: {"hours": float, "minutes": float, "grams": float, "cost": float}.
            Example: {"hours": 1, "minutes": 30, "grams": 50.5, "cost": 1.25}. Do not include markdown."""
            response = self.model.generate_content([prompt, img])
            txt = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(txt)
        except Exception as e: return {'error': f"AI Error: {str(e)}"}

    def estimate_price(self, brand, material, color):
        if not self.model: return None
        try:
            prompt = f"Estimate retail price USD for 1kg spool {brand} {material} {color}. Return JSON: {{'price_estimate': '$XX.XX'}}"
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
        self.calc_vals = {"mat_cost": 0, "electricity": 0, "labor": 0, "swaps": 0, "subtotal": 0, "total": 0, "profit": 0, "hours": 0, "rate": 0, "batch": 1, "unit_price": 0}

        # --- LAYOUT ---
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill="both", expand=True)
        
        self.sidebar = ttk.Frame(self.main_container, style='Sidebar.TFrame', width=250, padding=10)
        self.sidebar.pack(side="left", fill="y")
        
        ttk.Label(self.sidebar, text="Print Shop Manager", font=("Segoe UI", 18, "bold"), foreground=self.ACCENT_COLOR, background=self.CARD_BG).pack(pady=20, anchor="w", padx=10)
        
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
        self.style.configure('Accent.TButton', background=self.ACCENT_COLOR, foreground='white', font=("Segoe UI", 9, "bold"))
        self.style.configure('Ghost.TButton', background=self.CARD_BG, foreground=self.ACCENT_COLOR, font=("Segoe UI", 9), borderwidth=1)
        self.style.configure('Nav.TButton', background=self.CARD_BG, foreground=self.TEXT_COLOR, font=("Segoe UI", 11), anchor="w", padding=15, relief="flat")
        self.style.map('Nav.TButton', background=[('active', self.ACCENT_LIGHT)], foreground=[('active', self.ACCENT_COLOR)])
        self.style.configure('TLabel', background=self.BG_COLOR, foreground=self.TEXT_COLOR)
        self.style.configure('Card.TLabel', background=self.CARD_BG, foreground=self.TEXT_COLOR)
        self.style.configure('Stat.TLabel', background=self.CARD_BG, foreground=self.TEXT_COLOR, font=("Segoe UI", 24, "bold"))
        self.style.configure('Sub.TLabel', background=self.CARD_BG, foreground=self.TEXT_SECONDARY, font=("Segoe UI", 9))

    def setup_theme_colors(self):
        if self.current_theme_name == "litera":
            self.ACCENT_COLOR = "#2563eb"; self.ACCENT_LIGHT = "#eff6ff"; self.BG_COLOR = "#f8f9fa"; self.CARD_BG = "#ffffff"; self.TEXT_COLOR = "#333333"; self.TEXT_SECONDARY = "#6b7280"
        else:
            self.ACCENT_COLOR = "#3b82f6"; self.ACCENT_LIGHT = "#1e293b"; self.BG_COLOR = "#0f172a"; self.CARD_BG = "#1e293b"; self.TEXT_COLOR = "#ffffff"; self.TEXT_SECONDARY = "#aaaaaa"

    def toggle_theme(self):
        new_theme = "darkly" if self.current_theme_name == "litera" else "litera"
        self.current_theme_name = new_theme
        self.style.theme_use(new_theme)
        self.setup_theme_colors()
        self.configure_styles()
        self.sidebar.configure(style='Sidebar.TFrame')
        for widget in self.sidebar.winfo_children():
            if isinstance(widget, ttk.Label): widget.configure(background=self.CARD_BG, foreground=self.ACCENT_COLOR)
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
        ttk.Label(head, text="Fleet Dashboard", font=("Segoe UI", 24, "bold")).pack(side="left")
        self.lbl_printer_status = ttk.Label(head, text="Printer: Offline", font=("Segoe UI", 10), foreground=self.TEXT_SECONDARY, background=self.BG_COLOR)
        self.lbl_printer_status.pack(side="right", padx=10)
        ttk.Button(head, text="Refresh", style='Ghost.TButton', command=self.refresh_dashboard).pack(side="right")

        grid = ttk.Frame(self.content_area); grid.pack(fill="x")
        grid.columnconfigure(0, weight=1); grid.columnconfigure(1, weight=1); grid.columnconfigure(2, weight=1); grid.columnconfigure(3, weight=1)

        c1, self.lbl_stat_proj, self.lbl_sub_proj = self.create_stat_card(grid, "Total Projects", "...", "...", "📦")
        c1.grid(row=0, column=0, sticky="ew", padx=10)
        c2, self.lbl_stat_cost, self.lbl_sub_cost = self.create_stat_card(grid, "Avg Cost", "...", "...", "◎")
        c2.grid(row=0, column=1, sticky="ew", padx=10)
        c3, self.lbl_stat_inv, self.lbl_sub_inv = self.create_stat_card(grid, "Inventory", "...", "...", "📉")
        c3.grid(row=0, column=2, sticky="ew", padx=10)
        c4, self.lbl_stat_low, self.lbl_sub_low = self.create_stat_card(grid, "Low Stock", "...", "...", "⚠️")
        c4.grid(row=0, column=3, sticky="ew", padx=10)

        if HAS_MATPLOTLIB:
            chart_wrapper = ttk.Frame(self.content_area)
            chart_wrapper.pack(fill="both", expand=True, pady=20)
            chart_wrapper.columnconfigure(0, weight=1); chart_wrapper.rowconfigure(0, weight=1)
            chart_frame = self.create_card(chart_wrapper, "Revenue Trend (Last 7 Days)", row=0, col=0)
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
        ax.plot(display_dates, display_vals, color=self.ACCENT_COLOR, marker='o', linewidth=2, markersize=6)
        ax.set_facecolor(self.CARD_BG)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['left'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        ax.tick_params(axis='x', colors=self.TEXT_COLOR, rotation=45, labelsize=8) 
        ax.tick_params(axis='y', colors=self.TEXT_COLOR)
        for i, v in enumerate(display_vals):
            ax.text(i, v + (max(display_vals)*0.05 if display_vals else 1), f"${int(v)}", ha='center', va='bottom', fontsize=8, color=self.TEXT_COLOR)
        f.tight_layout()
        canvas = FigureCanvasTkAgg(f, parent); canvas.get_tk_widget().pack(fill="both", expand=True)

    def refresh_dashboard(self): 
        self.load_all_data(); self.refresh_dashboard_data()

    def refresh_dashboard_data(self):
        total_p = len(self.history); active_p = len(self.queue)
        self.lbl_stat_proj.config(text=str(total_p))
        self.lbl_sub_proj.config(text=f"{active_p} active in queue")
        costs = [float(h.get('cost', 0)) for h in self.history]
        avg_cost = sum(costs) / len(costs) if costs else 0
        self.lbl_stat_cost.config(text=f"${avg_cost:.2f}")
        self.lbl_sub_cost.config(text="Per finished project")
        total_g = sum(int(i.get('weight', 0)) for i in self.inventory)
        self.lbl_stat_inv.config(text=f"{total_g/1000:.1f} kg")
        self.lbl_sub_inv.config(text="Total filament remaining")
        low_count = sum(1 for i in self.inventory if int(i.get('weight',0)) < 200)
        self.lbl_stat_low.config(text=str(low_count))
        self.lbl_sub_low.config(text="Spools < 200g")

    # --- INVENTORY ---
    def show_inventory(self):
        self.current_page_method = self.show_inventory
        self.clear_content()
        form_frame = ttk.Frame(self.content_area, style='Card.TFrame', padding=15)
        form_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(form_frame, text="Add/Edit Spool", font=("Segoe UI", 10, "bold"), background=self.CARD_BG).grid(row=0, column=0, sticky="w", padx=5)
        
        self.v_brand = tk.StringVar(); self.v_id = tk.StringVar(); self.v_mat = tk.StringVar(value="PLA"); self.v_color = tk.StringVar()
        self.v_cost = tk.StringVar(value="20.00"); self.v_weight = tk.StringVar(value="1000")
        self.v_benchy = tk.BooleanVar(value=False); self.v_type = tk.StringVar(value="Plastic")
        
        # New V16 Fields
        self.v_abrasive = tk.BooleanVar(value=False)
        self.v_ams_slot = tk.StringVar(value="External")
        
        # --- V17.0: BENCHY NOZZLE TRACKING ---
        self.v_benchy_nozzle = tk.StringVar(value="0.4mm")
        
        f1 = ttk.Frame(form_frame, style='Card.TFrame'); f1.grid(row=1, column=0, columnspan=10, sticky="w", pady=5)
        ttk.Label(f1, text="Brand:", background=self.CARD_BG).pack(side="left", padx=(5,0))
        ttk.Entry(f1, textvariable=self.v_brand, width=15).pack(side="left", padx=5)
        ttk.Label(f1, text="ID:", background=self.CARD_BG).pack(side="left", padx=(10,0))
        ttk.Entry(f1, textvariable=self.v_id, width=5).pack(side="left", padx=5)
        ttk.Button(f1, text="Auto", style='Secondary.TButton', command=self.auto_gen_id).pack(side="left")
        ttk.Label(f1, text="Material:", background=self.CARD_BG).pack(side="left", padx=(10,0))
        mat_options = ["PLA", "PETG", "ABS", "ASA", "TPU", "Nylon", "PC", "PVA", "HIPS", "Wood", "Carbon Fiber"]
        ttk.Combobox(f1, textvariable=self.v_mat, values=mat_options, width=10).pack(side="left", padx=5)
        ttk.Label(f1, text="Color:", background=self.CARD_BG).pack(side="left", padx=(10,0))
        ttk.Entry(f1, textvariable=self.v_color, width=10).pack(side="left", padx=5)
        
        f2 = ttk.Frame(form_frame, style='Card.TFrame'); f2.grid(row=2, column=0, columnspan=10, sticky="w", pady=5)
        ttk.Label(f2, text="Cost ($):", background=self.CARD_BG).pack(side="left", padx=(5,0))
        ttk.Entry(f2, textvariable=self.v_cost, width=6).pack(side="left", padx=5)
        ttk.Label(f2, text="Weight (g):", background=self.CARD_BG).pack(side="left", padx=(10,0))
        ttk.Entry(f2, textvariable=self.v_weight, width=6).pack(side="left", padx=5)
        
        # AMS Slot Mapping
        ttk.Label(f2, text="AMS Slot:", background=self.CARD_BG).pack(side="left", padx=(15,0))
        slots = ["External", "A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "Lite-1", "Lite-2", "Lite-3", "Lite-4"]
        ttk.Combobox(f2, textvariable=self.v_ams_slot, values=slots, width=8).pack(side="left", padx=5)

        ttk.Checkbutton(f2, text="Benchy?", variable=self.v_benchy, bootstyle="round-toggle").pack(side="left", padx=15)
        
        # Benchy Nozzle Selection
        ttk.Combobox(f2, textvariable=self.v_benchy_nozzle, values=["0.2mm", "0.4mm", "0.6mm", "0.8mm"], width=6, state="readonly").pack(side="left", padx=2)
        
        ttk.Checkbutton(f2, text="Abrasive (⚠️)", variable=self.v_abrasive, bootstyle="round-toggle").pack(side="left", padx=5)
        
        ttk.Button(f2, text="Save Spool", style='Success.TButton', command=self.save_spool).pack(side="left", padx=15)
        ttk.Button(f2, text="Clear", style='Secondary.TButton', command=self.clear_form).pack(side="left", padx=5)

        act_frame = ttk.Frame(self.content_area); act_frame.pack(fill="x", pady=5)
        ttk.Button(act_frame, text="Edit Selected", style='Primary.TButton', command=self.edit_selected).pack(side="left", padx=2)
        ttk.Button(act_frame, text="Set Material", style='Primary.TButton', command=self.bulk_set_material).pack(side="left", padx=2)
        ttk.Button(act_frame, text="Delete", style='Danger.TButton', command=self.delete_spool).pack(side="left", padx=2)
        ttk.Button(act_frame, text="Check Price", style='Secondary.TButton', command=self.check_price).pack(side="left", padx=2)
        ttk.Button(act_frame, text="✅/❌ Benchy", style='Ghost.TButton', command=self.toggle_benchy).pack(side="left", padx=10)
        ttk.Button(act_frame, text="💾 Export CSV", style='Success.TButton', command=self.export_inventory_to_csv).pack(side="left", padx=10)

        ttk.Label(act_frame, text="🔍 Filter:", background=self.BG_COLOR).pack(side="left", padx=(20, 5))
        self.entry_search = ttk.Entry(act_frame); self.entry_search.pack(side="left", fill="x", expand=True)
        self.entry_search.bind("<KeyRelease>", self.filter_inventory)

        cols = ("ID", "Name", "Material", "Color", "Weight", "AMS", "Cost", "Benchy", "Type")
        self.tree = ttk.Treeview(self.content_area, columns=cols, show="tree headings", height=15)
        self.tree.column("#0", width=40, anchor="center"); self.tree.heading("#0", text="Icon")
        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Name", width=180, anchor="w")
        self.tree.column("Material", width=80, anchor="center")
        self.tree.column("Color", width=100, anchor="w")
        self.tree.column("Weight", width=70, anchor="center")
        self.tree.column("AMS", width=70, anchor="center")
        self.tree.column("Cost", width=70, anchor="center")
        self.tree.column("Benchy", width=100, anchor="center") # Widened for nozzle info
        self.tree.column("Type", width=70, anchor="center")
        for c in cols: self.tree.heading(c, text=c)
        self.tree.pack(fill="both", expand=True, pady=5)
        self.refresh_inventory_list()

    def export_inventory_to_csv(self):
        fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")], title="Export Inventory")
        if not fpath: return
        try:
            with open(fpath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["ID", "Name", "Material", "Color", "Weight", "AMS", "Cost", "Benchy", "Benchy Nozzle", "Abrasive"])
                for item in self.inventory:
                    writer.writerow([item.get('id',''), item.get('name',''), item.get('material',''), item.get('color',''), item.get('weight',0), item.get('ams_slot','External'), item.get('cost',0), item.get('benchy','❌'), item.get('benchy_nozzle', ''), item.get('abrasive','No')])
            messagebox.showinfo("Success", f"Exported to {fpath}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def auto_gen_id(self):
        next_id = 1
        existing = [int(i['id']) for i in self.inventory if str(i['id']).isdigit()]
        if existing: next_id = max(existing) + 1
        self.v_id.set(str(next_id).zfill(3))

    def clear_form(self):
        self.v_brand.set(""); self.v_color.set(""); self.v_id.set(""); self.v_weight.set("1000"); self.v_cost.set("20.00"); self.v_ams_slot.set("External"); self.v_abrasive.set(False); self.v_benchy.set(False); self.v_benchy_nozzle.set("0.4mm")

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel: return
        val = self.tree.item(sel[0])['values']
        self.v_id.set(str(val[0])); self.v_brand.set(val[1]); self.v_mat.set(val[2]); self.v_color.set(val[3]); self.v_weight.set(val[4])
        self.v_ams_slot.set(val[5]); self.v_cost.set(str(val[6]).replace("$","")); 
        
        # Parse Benchy String "✅ (0.4mm)"
        b_str = str(val[7])
        self.v_benchy.set("✅" in b_str)
        if "(" in b_str:
            noz = b_str.split("(")[1].replace(")", "")
            self.v_benchy_nozzle.set(noz)
        else:
            self.v_benchy_nozzle.set("0.4mm")

        is_abr = "⚠️" in str(val[8])
        self.v_abrasive.set(is_abr)

    def bulk_set_material(self):
        mat = simpledialog.askstring("Bulk Update", "Enter Material:")
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
                curr = item.get('benchy','❌')
                if curr == '❌': item['benchy'] = '✅'; item['benchy_nozzle'] = '0.4mm' # Default if quick-toggled
                else: item['benchy'] = '❌'
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
                self.insert_tree_item(item)

    def save_spool(self):
        try:
            sid = self.v_id.get(); 
            if not sid: self.auto_gen_id(); sid = self.v_id.get()
            item = {
                "id": sid, "name": self.v_brand.get(), "material": self.v_mat.get(), "color": self.v_color.get(), 
                "weight": float(self.v_weight.get()), "cost": float(self.v_cost.get()), 
                "benchy": "✅" if self.v_benchy.get() else "❌", "benchy_nozzle": self.v_benchy_nozzle.get(),
                "ams_slot": self.v_ams_slot.get(), "abrasive": self.v_abrasive.get()
            }
            self.inventory = [i for i in self.inventory if str(i.get('id')) != sid]
            self.inventory.append(item)
            self.inventory.sort(key=lambda x: int(x['id']) if str(x['id']).isdigit() else 9999)
            self.save_json(self.inventory, DB_FILE); self.refresh_inventory_list(); self.clear_form(); messagebox.showinfo("Success", "Spool Saved")
        except: messagebox.showerror("Error", "Check numeric fields")

    def refresh_inventory_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for item in self.inventory: self.insert_tree_item(item)

    def insert_tree_item(self, item):
        w = int(item.get('weight', 0)); c = float(item.get('cost', 0))
        is_abr = item.get('abrasive', False)
        icon = self.color_manager.get_icon(item.get('color', ''), is_abrasive=is_abr)
        type_str = "⚠️ ABRASIVE" if is_abr else "Standard"
        
        # Format Benchy String
        benchy_display = item.get('benchy', '❌')
        if benchy_display == '✅':
            benchy_display += f" ({item.get('benchy_nozzle', '0.4mm')})"
            
        self.tree.insert("", "end", image=icon, values=(item.get('id', '?'), item.get('name'), item.get('material'), item.get('color'), w, item.get('ams_slot','Ext'), f"${c:.2f}", benchy_display, type_str))

    def check_price(self):
        sel = self.tree.selection()
        if not sel: return
        val = self.tree.item(sel[0])['values']
        webbrowser.open(f"https://www.google.com/search?q={val[1]} {val[2]} {val[3]} filament price&tbm=shop")
        if self.ai_manager.api_key:
            def run():
                res = self.ai_manager.estimate_price(val[1], val[2], val[3])
                if res and 'price_estimate' in res: messagebox.showinfo("AI Estimate", f"Estimated: {res['price_estimate']}")
            threading.Thread(target=run).start()

    def configure_ai(self):
        key = simpledialog.askstring("Google AI Studio", "Enter Gemini API Key:", initialvalue=self.ai_manager.api_key)
        if key:
            self.ai_manager.save_config(key, "gemini-1.5-flash")
            messagebox.showinfo("Success", "API Key Saved.")

    # --- AI SLICER READER ---
    def show_ai_reader(self):
        self.current_page_method = self.show_ai_reader
        self.clear_content()
        container = ttk.Frame(self.content_area); container.place(relx=0.5, rely=0.5, anchor="center")
        icon_lbl = ttk.Label(container, text="⛶", font=("Segoe UI", 30), foreground=self.ACCENT_COLOR, background=self.BG_COLOR); icon_lbl.pack()
        ttk.Label(container, text="AI Slicer Reader", font=("Segoe UI", 24, "bold"), foreground=self.ACCENT_COLOR).pack(pady=(0,10))
        ttk.Label(container, text=f"Model: {self.ai_manager.preferred_model}", font=("Segoe UI", 10), foreground="gray").pack(pady=0)
        card = ttk.Frame(container, style='Card.TFrame', padding=40); card.pack(ipadx=20)
        self.btn_slicer_scan = ttk.Button(card, text="↥ Choose File", style='Accent.TButton', command=self.open_slicer_scanner); self.btn_slicer_scan.pack(fill="x", pady=5)
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
        if not res or 'error' in res: messagebox.showerror("AI Error", f"Failed: {res.get('error') if res else 'Unknown'}"); return
        self.show_calculator()
        if 'grams' in res: self.entry_calc_grams.delete(0, tk.END); self.entry_calc_grams.insert(0, str(res['grams']))
        if 'hours' in res or 'minutes' in res:
            total_h = res.get('hours', 0) + (res.get('minutes', 0) / 60)
            self.entry_hours.delete(0, tk.END); self.entry_hours.insert(0, f"{total_h:.2f}")
        messagebox.showinfo("Success", "Slicer data extracted!")

    # --- CALCULATOR ---
    def show_calculator(self):
        self.current_page_method = self.show_calculator
        self.clear_content()
        ttk.Label(self.content_area, text="Calculator", font=("Segoe UI", 20, "bold")).pack(pady=10)
        paned = ttk.Panedwindow(self.content_area, orient=tk.HORIZONTAL); paned.pack(fill="both", expand=True)
        f_left = ttk.Frame(paned, padding=10); paned.add(f_left, weight=1)
        f_right = ttk.Frame(paned, padding=10); paned.add(f_right, weight=2)
        
        lf_job = ttk.Labelframe(f_left, text="Job Details (Builder)", padding=10); lf_job.pack(fill="x", pady=5)
        ttk.Label(lf_job, text="Job Name:").pack(anchor="w"); self.entry_job_name = ttk.Entry(lf_job); self.entry_job_name.pack(fill="x")
        
        # Nozzle Selector (New v16)
        ttk.Label(lf_job, text="Nozzle Size:").pack(anchor="w")
        self.v_nozzle = tk.StringVar(value="0.4mm")
        ttk.Combobox(lf_job, textvariable=self.v_nozzle, values=["0.2mm (Detail)", "0.4mm (Standard)", "0.6mm (Speed)", "0.8mm (Draft)"], state="readonly").pack(fill="x")

        ttk.Label(lf_job, text="Select Spool:").pack(anchor="w"); self.combo_filaments = ttk.Combobox(lf_job, state="readonly"); self.combo_filaments.pack(fill="x")
        self.update_filament_dropdown()
        ttk.Label(lf_job, text="Grams:").pack(anchor="w"); self.entry_calc_grams = ttk.Entry(lf_job); self.entry_calc_grams.pack(fill="x")
        ttk.Button(lf_job, text="➕ Add Segment", command=self.add_to_job, style="Success.TButton").pack(fill="x", pady=5)

        lf_cost = ttk.Labelframe(f_left, text="Time & Labor", padding=10); lf_cost.pack(fill="x", pady=5)
        r1 = ttk.Frame(lf_cost); r1.pack(fill="x", pady=2); ttk.Label(r1, text="Time (h):").pack(side="left"); self.entry_hours = ttk.Entry(r1, width=6); self.entry_hours.pack(side="right")
        r2 = ttk.Frame(lf_cost); r2.pack(fill="x", pady=2); ttk.Label(r2, text="Rate ($/h):").pack(side="left"); self.entry_mach_rate = ttk.Entry(r2, width=6); self.entry_mach_rate.pack(side="right")
        r3 = ttk.Frame(lf_cost); r3.pack(fill="x", pady=2); ttk.Label(r3, text="Labor ($):").pack(side="left"); self.entry_processing = ttk.Entry(r3, width=6); self.entry_processing.pack(side="right")
        r4 = ttk.Frame(lf_cost); r4.pack(fill="x", pady=2); ttk.Label(r4, text="Markup (x):").pack(side="left"); self.entry_markup = ttk.Entry(r4, width=6); self.entry_markup.pack(side="right")
        r5 = ttk.Frame(lf_cost); r5.pack(fill="x", pady=2); ttk.Label(r5, text="Swaps (#):").pack(side="left"); self.entry_swaps = ttk.Entry(r5, width=6); self.entry_swaps.pack(side="right")
        r6 = ttk.Frame(lf_cost); r6.pack(fill="x", pady=2); ttk.Label(r6, text="Swap Fee ($):").pack(side="left"); self.entry_swap_fee = ttk.Entry(r6, width=6); self.entry_swap_fee.pack(side="right")
        r7 = ttk.Frame(lf_cost); r7.pack(fill="x", pady=2); ttk.Label(r7, text="Batch Qty:").pack(side="left"); self.entry_batch_qty = ttk.Entry(r7, width=6); self.entry_batch_qty.pack(side="right")

        self.entry_hours.insert(0,"0"); self.entry_mach_rate.insert(0, self.defaults.get('rate', "0.05")); self.entry_processing.insert(0, self.defaults.get('labor', "0"))
        self.entry_markup.insert(0, self.defaults.get('markup', "2.5")); self.entry_swaps.insert(0, "0"); self.entry_swap_fee.insert(0, self.defaults.get('swap_fee', "0.15")); self.entry_batch_qty.insert(0, "1")

        self.var_round = tk.BooleanVar(); self.var_donate = tk.BooleanVar()
        ttk.Checkbutton(f_left, text="Round to Nearest $", variable=self.var_round).pack(anchor="w")
        ttk.Checkbutton(f_left, text="Donation", variable=self.var_donate).pack(anchor="w")
        ttk.Button(f_left, text="CALCULATE", style='Accent.TButton', command=self.calculate_quote).pack(fill="x", pady=15)

        self.lbl_breakdown = ttk.Label(f_right, text="Quote Breakdown...", font=("Consolas", 11), background="#f0f0f0", relief="sunken", padding=10, anchor="n"); self.lbl_breakdown.pack(fill="x", pady=(0, 10))
        list_head = ttk.Frame(f_right); list_head.pack(fill="x"); ttk.Label(list_head, text="Job Material List:", font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(list_head, text="🗑️ Clear", style="Link.TButton", command=self.clear_job).pack(side="right")
        self.list_job = tk.Listbox(f_right, font=("Segoe UI", 10), relief="flat", bg="#ffffff", borderwidth=1); self.list_job.pack(fill="both", expand=True, pady=5)
        
        b_box = ttk.Frame(f_right); b_box.pack(fill="x", pady=10)
        self.btn_receipt = ttk.Button(b_box, text="💾 Save", state="disabled", command=self.generate_receipt); self.btn_receipt.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_queue = ttk.Button(b_box, text="⏳ Queue", state="disabled", command=self.save_to_queue); self.btn_queue.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_deduct = ttk.Button(b_box, text="✅ Deduct", state="disabled", command=self.deduct_inventory); self.btn_deduct.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_fail = ttk.Button(b_box, text="⚠️ Fail", state="disabled", command=self.log_failure, style="Danger.TButton"); self.btn_fail.pack(side="left", fill="x", expand=True, padx=2)

    def calculate_quote(self):
        if self.combo_filaments.get() and self.entry_calc_grams.get(): self.add_to_job()
        try:
            hours = float(self.entry_hours.get() or 0); rate = float(self.entry_mach_rate.get()); labor = float(self.entry_processing.get() or 0)
            batch = max(1, int(self.entry_batch_qty.get() or 1)); swaps = int(self.entry_swaps.get() or 0)
            
            # Dynamic Logic: Context-aware "Sticky" logic could be enhanced here later.
            effective_swap_fee = 0.03 if swaps > 100 else 0.15
            effective_markup = 1.5 if swaps > 100 else 2.5
            
            # Update UI for transparency (and saving to sticky)
            self.entry_swap_fee.delete(0, tk.END); self.entry_swap_fee.insert(0, str(effective_swap_fee))
            self.entry_markup.delete(0, tk.END); self.entry_markup.insert(0, str(effective_markup))
            
            self.save_sticky_settings()
            
            raw_mat_cost = sum(x['cost'] for x in self.current_job_filaments)
            elec_cost = hours * rate; swap_cost = swaps * effective_swap_fee
            base_cost = raw_mat_cost + elec_cost + labor + swap_cost
            final_price = 0 if self.var_donate.get() else base_cost * effective_markup
            
            # Unit Rounding Logic
            raw_unit_price = final_price / batch
            unit_price = round(raw_unit_price) if self.var_round.get() else raw_unit_price
            if self.var_round.get() and unit_price == 0 and raw_unit_price > 0: unit_price = 1
            display_price = unit_price * batch
            profit = display_price - base_cost
            
            self.calc_vals = {"mat_cost": raw_mat_cost, "electricity": elec_cost, "labor": labor, "swaps_cost": swap_cost, "subtotal": base_cost, "total": display_price, "profit": profit, "hours": hours, "rate": rate, "swaps": swaps, "batch": batch, "unit_price": unit_price}
            
            txt = (f"--- QUOTE BREAKDOWN ---\nNozzle: {self.v_nozzle.get()}\nMaterials: ${raw_mat_cost:.2f}\nElec: ${elec_cost:.2f} ({hours}h @ ${rate}/h)\nLabor: ${labor:.2f} | AMS: ${swap_cost:.2f}\n-----------------------\nBASE: ${base_cost:.2f}\nTOTAL JOB: ${display_price:.2f}\nUNIT PRICE: ${unit_price:.2f} (Qty: {batch})")
            if self.var_donate.get(): txt += " (DONATION)"
            self.lbl_breakdown.config(text=txt)
            for b in [self.btn_receipt, self.btn_queue, self.btn_deduct, self.btn_fail]: b.config(state="normal")
        except Exception as e: messagebox.showerror("Error", str(e))

    def add_to_job(self):
        txt = self.combo_filaments.get(); 
        if not txt: return
        try:
            g = float(self.entry_calc_grams.get())
            match = re.search(r"\[(\d+)\]", txt)
            spool = next((s for s in self.inventory if str(s.get('id')) == match.group(1)), None) if match else next((s for s in self.inventory if s['name'] in txt), None)
            if spool:
                cost = (spool['cost'] / 1000) * g
                self.current_job_filaments.append({'spool': spool, 'cost': cost, 'grams': g})
                self.list_job.insert(tk.END, f"{spool['name']} ({spool.get('material','?')}): {g}g (${cost:.2f})")
                self.entry_calc_grams.delete(0, tk.END); self.combo_filaments.set('')
        except: pass

    def clear_job(self):
        self.current_job_filaments = []; self.list_job.delete(0, tk.END); self.lbl_breakdown.config(text="...")
        for b in [self.btn_receipt, self.btn_queue, self.btn_deduct, self.btn_fail]: b.config(state="disabled")

    def generate_receipt(self):
        fname = f"Receipt_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        fpath = os.path.join(DOCS_DIR, fname)
        vals = self.calc_vals
        lines = ["="*40, "INVOICE", "="*40, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", f"Job: {self.entry_job_name.get()}", f"Nozzle: {self.v_nozzle.get()}", "-"*40, f"Materials: ${vals['mat_cost']:.2f}", f"Energy: ${vals['electricity']:.2f}", f"Labor/AMS: ${vals['labor']+vals['swaps_cost']:.2f}", "-"*40, f"TOTAL: ${vals['total']:.2f}", f"UNIT: ${vals['unit_price']:.2f} (Qty {vals['batch']})", "="*40]
        try:
            with open(fpath, 'w') as f: f.write("\n".join(lines))
            os.startfile(fpath)
        except: pass

    def save_to_queue(self):
        job = {"job": self.entry_job_name.get(), "date_added": datetime.now().strftime("%Y-%m-%d"), "items": self.current_job_filaments, "params": {
            "hours": self.entry_hours.get(), "rate": self.entry_mach_rate.get(), "labor": self.entry_processing.get(), "markup": self.entry_markup.get(), "swaps": self.entry_swaps.get(), "swap_fee": self.entry_swap_fee.get(), "batch": self.entry_batch_qty.get(), "nozzle": self.v_nozzle.get()
        }}
        self.queue.append(job); self.save_json(self.queue, QUEUE_FILE); self.clear_job(); messagebox.showinfo("Success", "Queued.")

    def deduct_inventory(self):
        if messagebox.askyesno("Confirm", "Deduct?"):
            for item in self.current_job_filaments: item['spool']['weight'] -= item['grams']
            self.save_json(self.inventory, DB_FILE)
            self.history.append({"date": datetime.now().strftime("%Y-%m-%d"), "job": self.entry_job_name.get(), "sold_for": self.calc_vals['total'], "profit": self.calc_vals['profit'], "cost": self.calc_vals['subtotal']})
            self.save_json(self.history, HISTORY_FILE); self.clear_job()

    def log_failure(self): pass 

    # --- RESTORED HELPERS (With Video Support) ---
    def update_filament_dropdown(self):
        self.full_filament_list = [f"[{i.get('id','?')}] {i['name']} - {i.get('material','?')} - {i.get('color','')}" for i in self.inventory]
        self.combo_filaments['values'] = self.full_filament_list

    def show_reference(self):
        self.current_page_method = self.show_reference; self.clear_content()
        ttk.Label(self.content_area, text="Reference Library", font=("Segoe UI", 20, "bold")).pack(pady=(0,20))
        self.gallery_notebook = ttk.Notebook(self.content_area); self.gallery_notebook.pack(fill="both", expand=True)
        self.build_wiki_tabs(); self.build_dynamic_gallery_tabs(); self.build_manual_tab()

    def build_dynamic_gallery_tabs(self):
        extensions = ["png", "jpg", "jpeg", "mp4"]
        image_files = []
        for ext in extensions: image_files.extend(glob.glob(os.path.join(get_base_path(), f"ref_*.{ext}")))
        
        for fpath in image_files:
            try:
                tab_frame = ttk.Frame(self.gallery_notebook)
                title = os.path.splitext(os.path.basename(fpath))[0].replace("ref_", "")
                self.gallery_notebook.add(tab_frame, text=f" 📷 {title} ")
                
                if fpath.endswith(".mp4"):
                    ttk.Label(tab_frame, text="🎥 Video Content", font=("Segoe UI", 20)).pack(pady=50)
                    ttk.Button(tab_frame, text="▶️ Watch Video", style='Success.TButton', command=lambda p=fpath: os.startfile(p)).pack()
                else:
                    pil = Image.open(fpath); pil.thumbnail((1000, 600)); tk_img = ImageTk.PhotoImage(pil); self.ref_images_cache.append(tk_img)
                    lbl = ttk.Label(tab_frame, image=tk_img, cursor="hand2"); lbl.pack(expand=True)
                    lbl.bind("<Button-1>", lambda e, p=fpath: self.view_full_image(p))
                    ttk.Label(tab_frame, text="(Click to Zoom)", font=("Segoe UI", 8), foreground="gray").pack(pady=5)
            except: pass

    def view_full_image(self, img_path):
        top = tk.Toplevel(self.root); top.title(f"Zoom: {os.path.basename(img_path)}"); top.state('zoomed')
        canvas = tk.Canvas(top, bg="black"); v_scroll = ttk.Scrollbar(top, orient="vertical", command=canvas.yview); h_scroll = ttk.Scrollbar(top, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side="right", fill="y"); h_scroll.pack(side="bottom", fill="x"); canvas.pack(side="left", fill="both", expand=True)
        pil = Image.open(img_path); tk_full = ImageTk.PhotoImage(pil); canvas.image = tk_full 
        canvas.create_image(0, 0, image=tk_full, anchor="nw"); canvas.config(scrollregion=canvas.bbox("all"))

    # --- MISSING FUNCTIONS RESTORED ---
    def configure_printer(self):
        d = tk.Toplevel(self.root); d.title("Settings"); d.geometry("400x450")
        ttk.Label(d, text="Settings", font=("Segoe UI", 12, "bold")).pack(pady=10)
        f = ttk.Frame(d, padding=20); f.pack(fill="x")
        ttk.Label(f, text="Printer IP:").pack(anchor="w"); e_ip = ttk.Entry(f); e_ip.pack(fill="x"); e_ip.insert(0, self.printer_cfg.get('ip',''))
        ttk.Label(f, text="Access Code:").pack(anchor="w"); e_ac = ttk.Entry(f); e_ac.pack(fill="x"); e_ac.insert(0, self.printer_cfg.get('access_code',''))
        ttk.Label(f, text="Serial:").pack(anchor="w"); e_sn = ttk.Entry(f); e_sn.pack(fill="x"); e_sn.insert(0, self.printer_cfg.get('serial',''))
        ttk.Label(f, text="AI Key:").pack(anchor="w"); e_ai = ttk.Entry(f, show="*"); e_ai.pack(fill="x"); e_ai.insert(0, self.ai_manager.api_key)
        
        lbl_model = ttk.Label(f, text=f"Current Model: {self.ai_manager.preferred_model}", font=("Segoe UI", 8), foreground="gray")
        lbl_model.pack(anchor="w")

        def run_diagnostic():
            key = e_ai.get()
            if not key: messagebox.showerror("Error", "Enter Key First"); return
            genai.configure(api_key=key)
            try:
                models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                if not models: messagebox.showwarning("Warning", "No compatible models found."); return
                diag = tk.Toplevel(d); diag.title("Select Model")
                ttk.Label(diag, text="Select model:", padding=10).pack()
                box = ttk.Combobox(diag, values=models, state="readonly"); box.pack(padx=20, pady=10); box.current(0)
                def confirm():
                    self.ai_manager.save_config(key, box.get()); lbl_model.config(text=f"Selected: {box.get()}"); diag.destroy()
                ttk.Button(diag, text="Use Selected", command=confirm).pack(pady=10)
            except Exception as e: messagebox.showerror("Error", str(e))

        ttk.Button(f, text="🔍 Test AI & List Models", style="Secondary.TButton", command=run_diagnostic).pack(fill="x", pady=5)
        
        def save():
            self.save_printer_config(e_ip.get(), e_ac.get(), e_sn.get(), True, "local", "")
            if e_ai.get() != self.ai_manager.api_key: self.ai_manager.save_config(e_ai.get(), self.ai_manager.preferred_model)
            d.destroy()
        ttk.Button(f, text="Save & Close", style='Accent.TButton', command=save).pack(pady=20)

    # --- MAINTENANCE (UPDATED FOR FLEET) ---
    def init_default_maintenance(self):
        self.maintenance = [
            {"task": "A1: Clean 0.2mm Nozzle (Cold Pull)", "freq": "Weekly", "last": "Never"},
            {"task": "P1S: Clean Carbon Rods (IPA)", "freq": "Monthly", "last": "Never"},
            {"task": "P2S: Inspect Hardened Gears", "freq": "Quarterly", "last": "Never"},
            {"task": "AMS 1: Replace Desiccant", "freq": "Monthly", "last": "Never"},
            {"task": "AMS 2: Replace Desiccant", "freq": "Monthly", "last": "Never"},
            {"task": "Wash Textured PEI (Dish Soap)", "freq": "Weekly", "last": "Never"}
        ]
        self.save_json(self.maintenance, MAINT_FILE)

    def init_materials_data(self):
        self.materials_data = {
            "PLA Basics": "=== PLA (Polylactic Acid) ===\nNOZZLE: 190-220°C\nBED: 45-60°C\nFAN: 100%\n\n> DOOR: OPEN (Critical for A1/P1S to prevent heat creep).\n> ADHESION: Textured PEI (No glue) or Cool Plate (Glue stick).\n> NOTES: Simplest to print. Biodegradable-ish.",
            "PLA Silk / Matte": "=== PLA Special (Silk/Matte) ===\nNOZZLE: 210-230°C (Hotter than normal!)\nSPEED: Outer Wall < 50mm/s for shine.\n\n> ISSUES: Silk swells (Die Swell). If jamming, lower Flow Ratio to 0.95.\n> STRENGTH: Weak layer adhesion. Decorative only.",
            "PETG Standard": "=== PETG (Polyethylene) ===\nNOZZLE: 230-250°C\nBED: 70-85°C\nFAN: 30-50%\n\n> ADHESION: Windex or Glue Stick acts as a RELEASE agent. Do not print on bare PEI (it rips).\n> STRINGING: Needs drying if stringy (65°C for 6h).",
            "ABS / ASA": "=== ABS & ASA ===\nNOZZLE: 250-270°C\nBED: 90-100°C\nCHAMBER: Enclosed (P1S/P2S Only).\n\n> TOXICITY: ASA is UV stable. ABS smells bad. Ventilation required.\n> WARPING: Use Brim. Preheat chamber for 15 mins.",
            "TPU (Flexible)": "=== TPU (95A / 85A) ===\nNOZZLE: 220-240°C\nBED: 35-45°C\nSPEED: < 40mm/s\n\n> AMS: NO! DO NOT PUT IN AMS. External spool only.\n> RETRACTION: Disable or set very low (0.5mm).",
            "PC (Polycarbonate)": "=== PC (Engineering) ===\nNOZZLE: 260-290°C\nBED: 110°C\n\n> STRENGTH: Strongest material.\n> ADHESION: Engineering Plate + Glue Stick essential.\n> ANNEALING: Bake part at 100°C for max strength.",
            "Nylon (PA / PA-CF)": "=== NYLON (PA) ===\nNOZZLE: 260-300°C\nBED: 100°C\n\n> HYGROSCOPIC: Absorbs water in minutes. Print from dry box ONLY.\n> NOZZLE: Hardened Steel required for PA-CF.",
            "PVA / Support": "=== PVA (Water Soluble) ===\nNOZZLE: 210-220°C\nBED: 50°C\nAMS: Yes.\n\n> STORAGE: Must be kept bone dry or it melts in the extruder.\n> USE: Support interface only (expensive).",
            "Carbon Fiber / Abrasive": "⚠️ ABRASIVE MATERIAL ⚠️\n(PA-CF, PLA-CF, Glow-in-the-Dark, Wood)\n\n> HARDWARE: Hardened Steel Nozzle & Gears REQUIRED.\n> NOZZLE: 0.4mm minimum, 0.6mm recommended to avoid clogs.\n> PATH: Avoid sharp bends in PTFE tubes."
        }

    def init_resource_links(self): 
        self.resource_links = {"PLA": "https://all3dp.com", "Bambu": "https://wiki.bambulab.com"}

    # --- REINSERTING MISSING METHODS TO ENSURE COMPLETE SCRIPT ---
    def show_history(self): 
        self.current_page_method = self.show_history; self.clear_content(); ttk.Label(self.content_area, text="Projects History", font=("Segoe UI", 20, "bold")).pack(pady=(0,20))
        cols = ("Date", "Job", "Cost", "Price", "Profit"); self.hist_tree = ttk.Treeview(self.content_area, columns=cols, show="headings"); self.hist_tree.pack(fill="both", expand=True)
        for c in cols: self.hist_tree.heading(c, text=c)
        self.refresh_history_list()
    
    def refresh_history_list(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        for h in self.history: self.hist_tree.insert("", "end", values=(h.get('date'), h.get('job'), f"${float(h.get('cost',0)):.2f}", f"${float(h.get('sold_for',0)):.2f}", f"${float(h.get('profit',0)):.2f}"))

    def show_queue(self): 
        self.current_page_method = self.show_queue; self.clear_content(); self.build_queue_tab_internal()

    def build_queue_tab_internal(self):
        ttk.Label(self.content_area, text="Job Queue", font=("Segoe UI", 20, "bold")).pack(pady=10)
        cols = ("Job", "Date"); self.queue_tree = ttk.Treeview(self.content_area, columns=cols, show="headings"); self.queue_tree.pack(fill="both", expand=True)
        for c in cols: self.queue_tree.heading(c, text=c)
        for q in self.queue: self.queue_tree.insert("", "end", values=(q.get('job'), q.get('date_added')))
        action_frame = ttk.Frame(self.content_area, padding=10); action_frame.pack(fill="x")
        ttk.Button(action_frame, text="✏️ Edit", style="Secondary.TButton", command=self.edit_queue_job).pack(side="left", padx=5)
        ttk.Button(action_frame, text="🔄 Load", style="Primary.TButton", command=self.load_queue_to_calculator).pack(side="left", padx=5)
        ttk.Button(action_frame, text="❌ Delete", style="Danger.TButton", command=self.delete_queue_job).pack(side="right", padx=5)
        self.queue_menu = Menu(self.content_area, tearoff=0); self.queue_menu.add_command(label="Load", command=self.load_queue_to_calculator); self.queue_menu.add_command(label="Delete", command=self.delete_queue_job)
        self.queue_tree.bind("<Button-3>", self.show_queue_context_menu)

    def show_queue_context_menu(self, event):
        try: self.queue_tree.selection_set(self.queue_tree.identify_row(event.y)); self.queue_menu.tk_popup(event.x_root, event.y_root)
        finally: self.queue_menu.grab_release()

    def edit_queue_job(self):
        sel = self.queue_tree.selection()
        if not sel: return
        idx = self.queue_tree.index(sel[0]); job = self.queue[idx]; new_name = simpledialog.askstring("Edit", "Name:", initialvalue=job.get('job'))
        if new_name: self.queue[idx]['job'] = new_name; self.save_json(self.queue, QUEUE_FILE); self.refresh_queue_list()

    def load_queue_to_calculator(self):
        sel = self.queue_tree.selection()
        if not sel: return
        job = self.queue[self.queue_tree.index(sel[0])]; self.show_calculator()
        self.entry_job_name.delete(0, tk.END); self.entry_job_name.insert(0, job.get('job', '')); self.clear_job()
        if 'items' in job: self.current_job_filaments = job['items']; 
        for item in self.current_job_filaments: self.list_job.insert(tk.END, f"{item['spool']['name']}: {item['grams']}g")
        if 'params' in job:
            p = job['params']; self.entry_hours.delete(0, tk.END); self.entry_hours.insert(0, str(p.get('hours', 0)))
            self.entry_swaps.delete(0, tk.END); self.entry_swaps.insert(0, str(p.get('swaps', 0)))
            if 'nozzle' in p: self.v_nozzle.set(p['nozzle'])

    def delete_queue_job(self):
        sel = self.queue_tree.selection()
        if not sel: return
        if messagebox.askyesno("Delete", "Remove?"): self.queue.pop(self.queue_tree.index(sel[0])); self.save_json(self.queue, QUEUE_FILE); self.refresh_queue_list()

    def show_maintenance(self): 
        self.current_page_method = self.show_maintenance; self.clear_content(); ttk.Label(self.content_area, text="Maintenance", font=("Segoe UI", 20, "bold")).pack(pady=10)
        self.build_maintenance_tab_internal()

    def build_maintenance_tab_internal(self):
        cols = ("Task", "Freq", "Last Done"); self.maint_tree = ttk.Treeview(self.content_area, columns=cols, show="headings"); self.maint_tree.pack(fill="both", expand=True)
        for c in cols: self.maint_tree.heading(c, text=c)
        ttk.Button(self.content_area, text="✅ Mark Done", command=self.perform_maintenance, style="Success.TButton").pack(pady=10)
        self.refresh_maintenance_list()

    def refresh_maintenance_list(self):
        for i in self.maint_tree.get_children(): self.maint_tree.delete(i)
        for item in self.maintenance: self.maint_tree.insert("", "end", values=(item['task'], item.get('freq', 'Monthly'), item['last']))

    def perform_maintenance(self):
        sel = self.maint_tree.selection()
        if not sel: return
        val = self.maint_tree.item(sel[0])['values']; task_name = val[0]
        for item in self.maintenance:
            if item['task'] == task_name: item['last'] = datetime.now().strftime("%Y-%m-%d"); break
        self.save_json(self.maintenance, MAINT_FILE); self.refresh_maintenance_list()

    def load_all_data(self):
        self.inventory = self.load_json(DB_FILE); self.history = self.load_json(HISTORY_FILE)
        self.maintenance = self.load_json(MAINT_FILE); self.queue = self.load_json(QUEUE_FILE)
        # Ensure IDs exist
        next_id = 1
        for item in self.inventory:
            if 'id' in item and str(item['id']).isdigit(): val = int(item['id']); 
            if val >= next_id: next_id = val + 1
        for item in self.inventory:
            if 'id' not in item: item['id'] = str(next_id).zfill(3); next_id += 1
    
    def load_json(self, f): 
        if os.path.exists(f): 
            try: return json.load(open(f))
            except: return []
        return []
    def save_json(self, d, f): json.dump(d, open(f,'w'), indent=4)
    def perform_auto_backup(self): pass # Stub for brevity
    # --- ADDED MISSING LOAD_CONFIG HELPER IN MAIN APP ---
    def load_config(self):
        if os.path.exists(CONFIG_FILE): return json.load(open(CONFIG_FILE))
        return {}
        
    def load_sticky_settings(self):
        if os.path.exists(CONFIG_FILE): return json.load(open(CONFIG_FILE)).get('sticky_settings', {})
        return {}
    def save_sticky_settings(self):
        d = self.load_config(); d['sticky_settings'] = {"markup": self.entry_markup.get(), "labor": self.entry_processing.get(), "rate": self.entry_mach_rate.get(), "swap_fee": self.entry_swap_fee.get()}
        json.dump(d, open(CONFIG_FILE, 'w'))
    def load_printer_config(self): 
        if os.path.exists(CONFIG_FILE): return json.load(open(CONFIG_FILE)).get('printer_cfg', {})
        return {}
    def save_printer_config(self, ip, ac, sn, en, mode, token):
        d = self.load_config(); d['printer_cfg'] = {"ip":ip, "access_code":ac, "serial":sn, "enabled":en, "mode":mode, "token":token}; json.dump(d, open(CONFIG_FILE,'w'))
        self.printer_cfg = d['printer_cfg']
    def start_printer_listener(self, override_token=None):
        if self.printer_client: self.printer_client.disconnect()
        if self.printer_cfg.get('access_code'): self.printer_client = BambuPrinterClient(self.printer_cfg.get('ip'), "bblp", self.printer_cfg.get('access_code'), self.printer_cfg.get('serial'), self.on_printer_status_update, None); self.printer_client.connect()
    def on_printer_status_update(self, data): self.root.after(0, lambda: self._update_ui_safe(data))
    def _update_ui_safe(self, data):
        if hasattr(self, 'lbl_printer_status') and self.lbl_printer_status.winfo_exists(): self.lbl_printer_status.config(text=f"Online: {data.get('gcode_state', 'IDLE')}", foreground=self.ACCENT_COLOR)
    
    # --- RESTORED PROFILE SCANNER & INSPECTOR ---
    def scan_for_custom_profiles(self):
        custom_rows = []
        scan_dirs = [get_base_path(), os.path.join(get_base_path(), "profiles")]
        for d in scan_dirs:
            if not os.path.exists(d): continue
            for file in os.listdir(d):
                if file.endswith(".json") and file not in ["filament_inventory.json", "sales_history.json", "maintenance_log.json", "job_queue.json", "config.json"]:
                    try:
                        fpath = os.path.join(d, file)
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            data = json.load(f)
                            name = data.get('name', file)
                            custom_rows.append((name, f"File: {fpath}"))
                    except: pass
        return custom_rows

    def on_guide_double_click(self, event):
        item_id = self.fil_tree.selection()
        if not item_id: return
        val = self.fil_tree.item(item_id[0])['values']
        # Path is in the last column
        if len(val) > 1 and "File: " in str(val[-1]):
            path = str(val[-1]).replace("File: ", "").strip()
            if os.path.exists(path): self.open_profile_inspector(path)

    def open_profile_inspector(self, fpath):
        try:
            with open(fpath, 'r') as f: data = json.load(f)
            top = tk.Toplevel(self.root); top.title(f"Inspector: {os.path.basename(fpath)}"); top.geometry("500x600")
            t = ttk.Treeview(top, columns=("Key","Value"), show="headings"); t.heading("Key", text="Setting"); t.heading("Value", text="Value"); t.pack(fill="both", expand=True)
            for k, v in data.items(): t.insert("", "end", values=(k, str(v)))
        except: pass

    def build_wiki_tabs(self): 
        f_comp = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f_comp, text=" 📂 My Profiles ")
        ttk.Label(f_comp, text="(Double-click to inspect)", font=("Segoe UI", 8), foreground="gray").pack(pady=5)
        self.fil_tree = ttk.Treeview(f_comp, columns=("Name", "Path"), show="headings")
        self.fil_tree.heading("Name", text="Profile Name"); self.fil_tree.heading("Path", text="Location")
        self.fil_tree.pack(fill="both", expand=True)
        self.fil_tree.bind("<Double-1>", self.on_guide_double_click)
        data = self.scan_for_custom_profiles()
        for row in data: self.fil_tree.insert("", "end", values=row)

    def build_manual_tab(self):
        f = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f, text=" 📖 Manual ")
        
        # Dropdown for topics (Cleaned up in v16.6)
        self.manual_topic = tk.StringVar()
        cb = ttk.Combobox(f, textvariable=self.manual_topic, values=list(self.materials_data.keys()), state="readonly")
        cb.pack(fill="x", padx=10, pady=5)
        cb.bind("<<ComboboxSelected>>", self.update_manual_view)
        
        self.txt_info = tk.Text(f, font=("Consolas", 11)); self.txt_info.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Initialize
        if self.materials_data: 
            self.manual_topic.set(list(self.materials_data.keys())[0])
            self.update_manual_view(None)

    def update_manual_view(self, e):
        topic = self.manual_topic.get()
        if topic in self.materials_data:
            self.txt_info.delete("1.0", tk.END)
            self.txt_info.insert("1.0", self.materials_data[topic])

if __name__ == "__main__":
    app = ttk.Window(themename="litera") 
    FilamentManagerApp(app)
    app.mainloop()