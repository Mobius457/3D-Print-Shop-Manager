import os
import warnings

# --- SUPPRESS WARNINGS & CONFIG ENV ---
os.environ["QT_API"] = "pyqt5"
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import json
import sys
import shutil
import glob
import webbrowser
import ctypes.wintypes
from datetime import datetime, timedelta
from PIL import Image, ImageTk, ImageDraw, ImageFont
import zipfile
import urllib.request
import re
import csv
import threading
import time
import uuid
import hashlib
import ssl

# --- OPTIONAL DEPENDENCIES ---
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.ticker import MaxNLocator
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
VERSION = "v38.0 (Simplified Settings)"

# ======================================================
# PATH & SYSTEM LOGIC
# ======================================================

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

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
DATA_DIR = get_app_data_folder()
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR, exist_ok=True)

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

    def analyze_spool_image(self, image_path):
        if not self.model: return None
        try:
            img = Image.open(image_path)
            prompt = """Analyze this filament spool label. Return ONLY a JSON object with keys: {"brand", "material", "color", "weight"}. Do not include markdown formatting."""
            response = self.model.generate_content([prompt, img])
            txt = response.text.replace('```json', '').replace('```', '').strip()
            print(f"DEBUG AI INV: {txt}")
            return json.loads(txt)
        except Exception as e:
            print(f"AI Error: {e}")
            return {"error": str(e)}

    def analyze_slicer_screenshot(self, image_path):
        if not self.model: return None
        try:
            img = Image.open(image_path)
            prompt = """Analyze this 3D printer slicer screenshot. Extract the print time, filament usage (grams), and estimated cost.
            Return ONLY a JSON object with these keys: {"hours": float, "minutes": float, "grams": float, "cost": float}.
            Example: If time is "1h 30m", return {"hours": 1, "minutes": 30, "grams": 50.5, "cost": 1.25}. Do not include markdown."""
            
            response = self.model.generate_content([prompt, img])
            txt = response.text.replace('```json', '').replace('```', '').strip()
            print(f"DEBUG AI SLICER: {txt}")
            return json.loads(txt)
        except Exception as e:
            print(f"AI Error: {e}")
            return {"error": str(e)}

    def estimate_price(self, brand, material, color):
        if not self.model: return None
        try:
            prompt = f"Estimate the average retail price in USD for a 1kg spool of {brand} {material} filament in {color}. Return JSON: {{'price_estimate': '$XX.XX'}}"
            response = self.model.generate_content(prompt)
            txt = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(txt)
        except: return None

# ======================================================
# BAMBU CLIENT (THREAD SAFE)
# ======================================================
class BambuPrinterClient:
    def __init__(self, host, username, password, serial, status_callback, finish_callback):
        self.host = host
        self.username = username
        self.password = password
        self.serial = serial
        self.status_callback = status_callback
        self.finish_callback = finish_callback
        self.client = None
        self.connected = False
        self.seq_id = 0
        self.last_state = {"gcode_state": "OFFLINE", "mc_percent": 0, "mc_remaining_time": 0, "nozzle_temper": 0, "bed_temper": 0, "subtask_name": "No Job"}

    def connect(self):
        if not HAS_MQTT: return False
        if not self.password or self.password == "None": return False
        try:
            cid = f"PrintShop_{uuid.uuid4().hex[:8]}"
            self.client = mqtt.Client(client_id=cid, callback_api_version=mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            self.client.tls_set_context(ssl_ctx)
            self.client.tls_insecure_set(True)
            self.client.username_pw_set(self.username, self.password)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            self.client.connect(self.host, 8883, 60)
            self.client.loop_start()
            self.start_heartbeat()
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
            print(">>> MQTT CONNECTED!")
            self.connected = True
            client.subscribe(f"device/{self.serial}/report")
            self.send_pushall()

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        self.connected = False
        print(">>> Disconnected")

    def on_message(self, client, userdata, msg):
        try:
            raw_txt = msg.payload.decode()
            payload = json.loads(raw_txt)
            p = payload.get('print', payload)
            if 'gcode_state' in p: print(f"[PRINTER DATA]: {p['gcode_state']} - {p.get('mc_percent')}%")
            keys = ["gcode_state", "mc_percent", "mc_remaining_time", "nozzle_temper", "bed_temper", "subtask_name"]
            for key in keys:
                if key in p: self.last_state[key] = p[key]
            data = {
                "state": self.last_state.get('gcode_state', 'IDLE'),
                "percent": self.last_state.get('mc_percent', 0),
                "time_rem": self.last_state.get('mc_remaining_time', 0),
                "nozzle": self.last_state.get('nozzle_temper', 0),
                "bed": self.last_state.get('bed_temper', 0),
                "file": self.last_state.get('subtask_name', 'No Job')
            }
            self.status_callback(data)
        except: pass

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

# ======================================================
# MAIN APP
# ======================================================
class FilamentManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"3D Print Manager - {VERSION}")
        self.root.geometry("1400x900")
        self.style = ttk.Style(theme="litera")
        self.PURPLE_MAIN = "#7c3aed"
        self.PURPLE_LIGHT = "#f3e8ff"
        self.BG_COLOR = "#f8f9fa"
        self.CARD_BG = "#ffffff"
        self.style.configure('TFrame', background=self.BG_COLOR)
        self.style.configure('Card.TFrame', background=self.CARD_BG, relief="flat", borderwidth=0)
        self.style.configure('Sidebar.TFrame', background=self.CARD_BG)
        self.style.configure('Purple.TButton', background=self.PURPLE_MAIN, foreground='white', font=("Segoe UI", 10, "bold"), borderwidth=0)
        self.style.map('Purple.TButton', background=[('active', '#6d28d9')])
        self.style.configure('Ghost.TButton', background='white', foreground=self.PURPLE_MAIN, font=("Segoe UI", 10), borderwidth=1, bordercolor=self.PURPLE_MAIN)
        self.style.configure('Nav.TButton', background=self.CARD_BG, foreground='#555', font=("Segoe UI", 11), anchor="w", padding=15, relief="flat")
        self.style.map('Nav.TButton', background=[('active', self.PURPLE_LIGHT)], foreground=[('active', self.PURPLE_MAIN)])
        self.style.configure('Clean.TEntry', fieldbackground='white', bordercolor='#e5e7eb', borderwidth=1, relief='flat')
        
        self.perform_auto_backup()
        self.defaults = self.load_sticky_settings()
        self.printer_cfg = self.load_printer_config()
        self.ai_manager = AIManager() 
        self.icon_cache = {} 
        self.ref_images_cache = [] 
        self.load_all_data()
        if not self.maintenance: self.init_default_maintenance()
        self.current_job_filaments = []
        self.calc_vals = {"mat_cost": 0, "electricity": 0, "labor": 0, "subtotal": 0, "total": 0, "profit": 0, "hours": 0, "rate": 0}
        
        self.init_materials_data()
        self.init_resource_links()
        self.load_icons()

        main_container = ttk.Frame(root)
        main_container.pack(fill="both", expand=True)
        self.sidebar = ttk.Frame(main_container, style='Sidebar.TFrame', width=250, padding=10)
        self.sidebar.pack(side="left", fill="y")
        ttk.Label(self.sidebar, text="Filametrics", font=("Segoe UI", 16, "bold"), foreground=self.PURPLE_MAIN, background=self.CARD_BG).pack(pady=20, anchor="w", padx=10)
        
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

        self.content_area = ttk.Frame(main_container, style='TFrame', padding=20)
        self.content_area.pack(side="right", fill="both", expand=True)

        self.printer_client = None
        if self.printer_cfg.get("enabled"):
            self.start_printer_listener()
            
        self.show_dashboard()

    # --- AI ACTION METHODS ---
    def configure_ai(self):
        key = simpledialog.askstring("Google AI Studio", "Enter Gemini API Key:\n(Get one from aistudio.google.com)", initialvalue=self.ai_manager.api_key)
        if key:
            self.ai_manager.save_api_key(key)
            messagebox.showinfo("Success", "API Key Saved.")

    def check_price(self):
        sel = self.tree.selection()
        if not sel: return
        item = self.inventory[int(sel[0])]
        brand = item.get('name', ''); mat = item.get('material', ''); col = item.get('color', '')
        webbrowser.open(f"https://www.google.com/search?q={brand} {mat} {col} filament price&tbm=shop")
        if self.ai_manager.api_key:
            def run():
                res = self.ai_manager.estimate_price(brand, mat, col)
                if res and 'price_estimate' in res:
                    messagebox.showinfo("AI Estimate", f"Estimated Market Price: {res['price_estimate']}")
            threading.Thread(target=run).start()

    def open_ai_scanner(self):
        if not self.ai_manager.api_key: self.configure_ai(); return
        path = filedialog.askopenfilename()
        if not path: return
        self.btn_inv_action.config(text="Scanning...", state="disabled")
        def run():
             res = self.ai_manager.analyze_spool_image(path)
             self.root.after(0, lambda: self._fill_inventory_form(res))
        threading.Thread(target=run).start()

    def _fill_inventory_form(self, res):
        self.btn_inv_action.config(text="Add Spool", state="normal")
        if not res or 'error' in res: messagebox.showerror("AI Error", f"Failed: {res.get('error')}"); return
        if res.get('brand'): self.inv_name.delete(0, tk.END); self.inv_name.insert(0, res.get('brand'))
        if res.get('color'): self.inv_color.delete(0, tk.END); self.inv_color.insert(0, res.get('color'))
        if res.get('material'): self.cb_inv_mat.set(res.get('material'))
        if res.get('weight'): self.inv_weight.delete(0, tk.END); self.inv_weight.insert(0, str(res.get('weight')))
        messagebox.showinfo("AI Scan", "Label scanned! Check the form fields.")

    # --- SLICER SCANNER LOGIC ---
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
            if "404" in str(err_msg): err_msg = "Model outdated. Try 'Configure AI' again."
            if "429" in str(err_msg): err_msg = "Quota Exceeded. Try again later."
            messagebox.showerror("AI Error", f"Failed: {err_msg}"); return

        self.show_calculator()
        if 'grams' in res: 
            self.entry_calc_grams.delete(0, tk.END)
            self.entry_calc_grams.insert(0, str(res['grams']))
        
        if 'hours' in res or 'minutes' in res:
            total_h = res.get('hours', 0) + (res.get('minutes', 0) / 60)
            self.entry_hours.delete(0, tk.END)
            self.entry_hours.insert(0, f"{total_h:.2f}")
            
        messagebox.showinfo("Success", "Slicer data extracted!\nSelect a Spool to finish the quote.")

    # --- ACTION METHODS ---
    def generate_receipt(self):
        fname = f"Receipt_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        fpath = os.path.join(DOCS_DIR, fname)
        vals = self.calc_vals; is_don = self.var_donate.get()
        header = "DONATION RECEIPT (TAX EXEMPT)" if is_don else "INVOICE"
        lines = ["="*50, f"{header:^50}", "="*50, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", f"Job Name: {self.entry_job_name.get() or 'Custom Job'}", "-"*50, "COST BREAKDOWN:", f" > Materials:       ${vals['mat_cost']:.2f}", f" > Machine/Power:   ${vals['electricity']:.2f} ({vals['hours']}h @ ${vals['rate']}/h)", f" > Labor/Prep:      ${vals['labor']:.2f}", "-"*50, f"SUBTOTAL COST:      ${vals['subtotal']:.2f}", f"MARKUP:             x{self.entry_markup.get()}", "="*50]
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
            rec = {"date": datetime.now().strftime("%Y-%m-%d"), "job": self.entry_job_name.get(), "sold_for": self.calc_vals['total'], "profit": self.calc_vals['profit']}
            self.history.append(rec)
            self.save_json(self.history, HISTORY_FILE)
            self.clear_job()

    def log_failure(self):
        if messagebox.askyesno("Confirm", "Log Failure (Cost only)?"): pass

    def calculate_quote(self):
        if not self.current_job_filaments: self.add_to_job()
        try:
            hours = float(self.entry_hours.get() or 0); rate = float(self.entry_mach_rate.get() or 0.75); labor = float(self.entry_processing.get() or 0); markup = float(self.entry_markup.get() or 1)
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
                if g > spool['weight']: messagebox.showwarning("Low Stock", f"Spool only has {int(spool['weight'])}g remaining!")
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

    # --- HELPERS ---
    def init_materials_data(self):
        self.materials_data = {"PLA Basics": "MATERIAL: Standard PLA\n========================\nNozzle: 190-220°C | Bed: 45-60°C", "PETG Basics": "MATERIAL: PETG\n========================\nNozzle: 230-250°C | Bed: 70-80°C"}

    def init_resource_links(self): self.resource_links = {"Bambu Wiki": "https://wiki.bambulab.com"}
    def load_icons(self): pass

    def create_nav_btn(self, text, command):
        btn = ttk.Button(self.sidebar, text=f"  {text}", style='Nav.TButton', command=command)
        btn.pack(fill="x", pady=2)
        self.nav_btns[text] = btn

    def clear_content(self):
        for widget in self.content_area.winfo_children(): widget.destroy()

    def create_card(self, parent, title=None, row=0, col=0, colspan=1, rowspan=1):
        card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        card.grid(row=row, column=col, columnspan=colspan, rowspan=rowspan, sticky="nsew", padx=10, pady=10)
        if title: ttk.Label(card, text=title, font=("Segoe UI", 11, "bold"), background=self.CARD_BG).pack(anchor="w", pady=(0, 10))
        return card

    def create_stat_card(self, parent, title, value, subtext="", icon_char=""):
        container = ttk.Frame(parent, style='Card.TFrame', padding=5) # Wrapper for grid margins if needed, but we'll use grid padding
        card = ttk.Frame(parent, style='Card.TFrame', padding=25)

        # Header Row
        head = ttk.Frame(card, style='Card.TFrame')
        head.pack(fill="x", pady=(0, 10))
        ttk.Label(head, text=title, font=("Segoe UI", 11, "bold"), foreground="#4b5563", background=self.CARD_BG).pack(side="left")
        if icon_char:
            ttk.Label(head, text=icon_char, font=("Segoe UI", 14), foreground="#9ca3af", background=self.CARD_BG).pack(side="right")

        # Value
        ttk.Label(card, text=value, font=("Segoe UI", 28, "bold"), foreground="#111827", background=self.CARD_BG).pack(anchor="w", pady=(0, 5))

        # Subtext
        if subtext:
            ttk.Label(card, text=subtext, font=("Segoe UI", 9), foreground="#6b7280", background=self.CARD_BG).pack(anchor="w")

        return card

    # --- DASHBOARD ---
    def show_dashboard(self):
        self.clear_content()
        # Top Header
        head = ttk.Frame(self.content_area); head.pack(fill="x", pady=(0, 30))
        # Left: Title
        h_left = ttk.Frame(head); h_left.pack(side="left")
        ttk.Label(h_left, text="Projects Dashboard", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(h_left, text="Overview of your printing metrics", font=("Segoe UI", 11), foreground="gray").pack(anchor="w")

        # Right: Actions
        ttk.Button(head, text="⚙️ Settings", style='Ghost.TButton', command=self.configure_printer).pack(side="right", padx=5)
        ttk.Button(head, text="Refresh", style='Ghost.TButton', command=self.refresh_dashboard).pack(side="right")
        self.lbl_printer_status = ttk.Label(head, text="Printer: Offline", font=("Segoe UI", 10, "bold"), foreground="gray")
        self.lbl_printer_status.pack(side="right", padx=15)
        
        # Stats Grid
        stats_frame = ttk.Frame(self.content_area)
        stats_frame.pack(fill="x", pady=(0, 30))
        stats_frame.columnconfigure(0, weight=1); stats_frame.columnconfigure(1, weight=1)

        # Row 1
        self.card_total = self.create_stat_card(stats_frame, "Total Projects", "0", "0 active, 0 completed", "📦")
        self.card_total.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.card_avg = self.create_stat_card(stats_frame, "Average Filament Cost", "$0.00", "Per delivered project (actual usage)", "💲")
        self.card_avg.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.card_usage = self.create_stat_card(stats_frame, "Remaining Usage", "0g", "Total inventory weight", "🧶")
        self.card_usage.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.card_low = self.create_stat_card(stats_frame, "Low Stock", "0", "Spools with < 200g remaining", "⚠️")
        self.card_low.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Live Status & Analytics Row
        row2 = ttk.Frame(self.content_area); row2.pack(fill="both", expand=True)
        row2.columnconfigure(0, weight=1); row2.columnconfigure(1, weight=2)

        # Live Status
        c_live = self.create_card(row2, "Live Printer Status", 0, 0)
        self.lbl_live_state = ttk.Label(c_live, text="OFFLINE", font=("Segoe UI", 16, "bold"), foreground="gray", background=self.CARD_BG)
        self.lbl_live_state.pack(anchor="w", pady=(5,0))
        self.lbl_live_temps = ttk.Label(c_live, text="Nozzle: -- | Bed: --", background=self.CARD_BG); self.lbl_live_temps.pack(anchor="w")
        
        self.dash_progress = ttk.Progressbar(c_live, value=0, maximum=100, style="success.Horizontal.TProgressbar")
        self.dash_progress.pack(fill="x", pady=15)
        
        d_row = ttk.Frame(c_live, style='Card.TFrame'); d_row.pack(fill="x")
        self.lbl_live_file = ttk.Label(d_row, text="File: --", font=("Segoe UI", 9), background=self.CARD_BG); self.lbl_live_file.pack(side="left")
        self.lbl_live_time = ttk.Label(d_row, text="Time: --", font=("Segoe UI", 9), background=self.CARD_BG); self.lbl_live_time.pack(side="right")
        self.lbl_live_pct = ttk.Label(c_live, text="0%", font=("Segoe UI", 12, "bold"), background=self.CARD_BG); self.lbl_live_pct.pack(anchor="e")

        # Analytics
        if HAS_MATPLOTLIB:
            c_an = self.create_card(row2, "Revenue Trend", 0, 1)
            f = plt.Figure(figsize=(5, 3), dpi=100, facecolor=self.CARD_BG)
            ax = f.add_subplot(111)
            dates = [h['date'][:5] for h in self.history[-10:]]
            vals = [h.get('sold_for', 0) for h in self.history[-10:]]
            if not dates: dates = ["-"]; vals = [0]

            # Style the plot
            ax.plot(dates, vals, color=self.PURPLE_MAIN, marker='o', linewidth=2)
            ax.fill_between(dates, vals, color=self.PURPLE_LIGHT, alpha=0.3)
            ax.set_facecolor(self.CARD_BG)
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['left'].set_visible(False)
            ax.tick_params(axis='x', colors='gray'); ax.tick_params(axis='y', colors='gray')
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            canvas = FigureCanvasTkAgg(f, c_an); canvas.get_tk_widget().pack(fill="both", expand=True)

        self.refresh_dashboard_data()

    def refresh_dashboard(self): self.load_all_data(); self.refresh_dashboard_data()
    def refresh_dashboard_data(self):
        # Update Total Projects
        count = len(self.history)
        # Hacky way to update labels inside the complex card structure without storing references to every sub-label
        # Actually, I should store references. But for now, I'll just traverse or rebuild.
        # Better: Rebuild? No, flickers.
        # Best: traverse children.

        def set_card_val(card_frame, val, sub=""):
            # Child 1 is Header, Child 2 is Value Label, Child 3 is Subtext
            try:
                ch = card_frame.winfo_children()
                # ch[0] is header, ch[1] is Value, ch[2] is Subtext
                if len(ch) > 1: ch[1].config(text=val)
                if len(ch) > 2 and sub: ch[2].config(text=sub)
            except: pass

        set_card_val(self.card_total, str(count), f"{count} completed")

        # Avg Cost
        avg = 0
        if count > 0:
            # Try to find cost. If missing, estimate from profit
            total_cost = 0
            for h in self.history:
                if 'cost' in h: total_cost += float(h['cost'])
                elif 'sold_for' in h and 'profit' in h: total_cost += (float(h['sold_for']) - float(h['profit']))
            avg = total_cost / count
        set_card_val(self.card_avg, f"${avg:.2f}")

        # Usage
        total_w = sum(int(i.get('weight', 0)) for i in self.inventory)
        set_card_val(self.card_usage, f"{total_w}g")

        # Low Stock
        low_count = sum(1 for i in self.inventory if int(i.get('weight',0)) < 200)
        set_card_val(self.card_low, str(low_count), f"{low_count} items need restock")

    # --- INVENTORY ---
    def show_inventory(self):
        self.clear_content()
        
        # Header
        head = ttk.Frame(self.content_area)
        head.pack(fill="x", pady=(0, 20))
        
        ttk.Label(head, text="Filament Inventory", font=("Segoe UI", 24, "bold")).pack(side="left")

        # Right Controls
        # Note: open_add_filament_modal will be defined in the next step
        btn_add = ttk.Button(head, text="+ New Filament", style='Purple.TButton', command=self.open_add_filament_modal)
        btn_add.pack(side="right")

        # Search
        f_search = ttk.Frame(head)
        f_search.pack(side="right", padx=15)
        self.entry_search = ttk.Entry(f_search, style='Clean.TEntry', width=25)
        self.entry_search.pack(side="left")
        self.entry_search.insert(0, "Search...")

        # Tree Card
        tree_card = ttk.Frame(self.content_area, style='Card.TFrame', padding=15)
        tree_card.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_card, columns=("Brand", "Mat", "Color", "Weight", "Cost", "Loc"), show="headings", height=20)
        cols = {"Brand": 150, "Mat": 80, "Color": 100, "Weight": 80, "Cost": 80, "Loc": 100}
        for c, w in cols.items():
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)

        self.tree.pack(fill="both", expand=True)
        self.refresh_inventory_list()

    # --- AI SLICER READER ---
    def show_ai_reader(self):
        self.clear_content()
        center = ttk.Frame(self.content_area); center.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(center, text="AI Slicer Reader", font=("Segoe UI", 24, "bold"), foreground=self.PURPLE_MAIN).pack(pady=10)
        ttk.Label(center, text="Upload a screenshot from your slicer to extract data.", font=("Segoe UI", 11), foreground="gray").pack(pady=5)
        box = ttk.Frame(center, style='Card.TFrame', padding=40); box.pack(ipadx=50, ipady=30)
        self.btn_slicer_scan = ttk.Button(box, text="Upload Slicer Screenshot", style='Purple.TButton', command=self.open_slicer_scanner)
        self.btn_slicer_scan.pack(pady=10)
        if not self.ai_manager.api_key: ttk.Button(box, text="⚙️ Configure API Key", style='Ghost.TButton', command=self.configure_ai).pack(pady=5)

    # --- CALCULATOR ---
    def show_calculator(self):
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
        self.entry_hours.insert(0,"0"); self.entry_mach_rate.insert(0,"0.75")
        
        r2 = ttk.Frame(f); r2.pack(fill="x", pady=5)
        ttk.Label(r2, text="Labor ($):").pack(side="left"); self.entry_processing = ttk.Entry(r2, width=5); self.entry_processing.pack(side="left", padx=5)
        ttk.Label(r2, text="Markup (x):").pack(side="left"); self.entry_markup = ttk.Entry(r2, width=5); self.entry_markup.pack(side="left", padx=5)
        self.entry_processing.insert(0,"0"); self.entry_markup.insert(0,"2.5")

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
        
        self.list_job = tk.Listbox(f) # Hidden but required

    # --- REFERENCE ---
    def show_reference(self):
        self.clear_content()
        ttk.Label(self.content_area, text="Reference Library", font=("Segoe UI", 20, "bold")).pack(pady=(0,20))
        self.gallery_notebook = ttk.Notebook(self.content_area); self.gallery_notebook.pack(fill="both", expand=True)
        self.build_wiki_tabs()
        self.build_manual_tab()

    def build_wiki_tabs(self):
        f = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f, text="My Profiles")
        cols = ("Material", "Nozzle", "Temp", "Bed", "Fan", "Note")
        self.fil_tree = ttk.Treeview(f, columns=cols, show="headings"); self.fil_tree.pack(fill="both", expand=True)
        for c in cols: self.fil_tree.heading(c, text=c)
        data = self.scan_for_custom_profiles()
        for r in data: self.fil_tree.insert("", "end", values=r)

    def scan_for_custom_profiles(self):
        custom_rows = []
        for root_dir, dirs, files in os.walk(get_base_path()):
            for file in files:
                if file.endswith(".json"):
                    try:
                        with open(os.path.join(root_dir, file), 'r') as f:
                            d = json.load(f)
                            if 'nozzle_temperature' in d:
                                name = d.get('filament_settings_id', [file])[0]
                                row = (name, "0.4", d.get('nozzle_temperature', ['220'])[0], d.get('bed_temperature', ['60'])[0], "100%", file)
                                custom_rows.append(row)
                    except: pass
        return custom_rows

    def build_manual_tab(self):
        f = ttk.Frame(self.gallery_notebook); self.gallery_notebook.add(f, text="Manual")
        self.mat_var = tk.StringVar()
        cb = ttk.Combobox(f, textvariable=self.mat_var, values=list(self.materials_data.keys()), state="readonly")
        cb.pack(fill="x", padx=10, pady=10)
        self.txt_info = tk.Text(f, font=("Consolas", 11), height=15); self.txt_info.pack(fill="both", expand=True, padx=10)
        cb.bind("<<ComboboxSelected>>", self.update_material_view)

    # --- OTHER PAGES ---
    def show_history(self): 
        self.clear_content()
        ttk.Label(self.content_area, text="Projects History", font=("Segoe UI", 20, "bold")).pack(pady=(0,20))
        cols = ("Date", "Job", "Cost", "Price", "Profit")
        self.hist_tree = ttk.Treeview(self.content_area, columns=cols, show="headings"); self.hist_tree.pack(fill="both", expand=True)
        for c in cols: self.hist_tree.heading(c, text=c)
        self.refresh_history_list()

    def show_queue(self): self.clear_content(); self.build_queue_tab_internal()
    def show_maintenance(self): self.clear_content(); self.build_maintenance_tab_internal()
    
    def build_queue_tab_internal(self):
        cols = ("Job", "Date"); t = ttk.Treeview(self.content_area, columns=cols, show="headings"); t.pack(fill="both", expand=True)
        for c in cols: t.heading(c, text=c)
        for q in self.queue: t.insert("", "end", values=(q.get('job'), q.get('date_added')))

    def build_maintenance_tab_internal(self):
        cols = ("Task", "Last Done"); t = ttk.Treeview(self.content_area, columns=cols, show="headings"); t.pack(fill="both", expand=True)
        for c in cols: t.heading(c, text=c)
        for m in self.maintenance: t.insert("", "end", values=(m.get('task'), m.get('last')))

    def configure_printer(self):
        d = tk.Toplevel(self.root); d.title("Settings"); d.geometry("400x500")
        
        # --- TABS FOR LOCAL VS CLOUD ---
        nb = ttk.Notebook(d); nb.pack(expand=True, fill="both", padx=10, pady=10)
        
        # TAB 1: LOCAL
        t_local = ttk.Frame(nb); nb.add(t_local, text="🏠 Local (Home)")
        ttk.Label(t_local, text="IP Address:").pack(pady=(10,0)); e_ip = ttk.Entry(t_local); e_ip.pack()
        e_ip.insert(0, self.printer_cfg.get('ip',''))
        ttk.Label(t_local, text="Access Code (from screen):").pack(pady=(5,0)); e_ac = ttk.Entry(t_local); e_ac.pack()
        e_ac.insert(0, self.printer_cfg.get('access_code',''))
        ttk.Label(t_local, text="Serial Number:").pack(pady=(5,0)); e_sn_l = ttk.Entry(t_local); e_sn_l.pack()
        e_sn_l.insert(0, self.printer_cfg.get('serial',''))
        
        def save_local():
            self.save_printer_config(e_ip.get(), e_ac.get(), e_sn_l.get(), True, "local", "")
            self.start_printer_listener()
            d.destroy()
        ttk.Button(t_local, text="Save & Connect Local", style='Purple.TButton', command=save_local).pack(pady=20)
        
        # TAB 2: CLOUD
        t_cloud = ttk.Frame(nb); nb.add(t_cloud, text="☁️ Cloud (Remote)")
        ttk.Label(t_cloud, text="Access Token (Long String):").pack(pady=(10,0))
        e_tok = ttk.Entry(t_cloud); e_tok.pack()
        ttk.Label(t_cloud, text="Serial Number:").pack(pady=(5,0))
        e_sn_c = ttk.Entry(t_cloud); e_sn_c.pack()
        e_sn_c.insert(0, self.printer_cfg.get('serial',''))
        
        def save_cloud():
            # CLEAN THE TOKEN
            raw_token = e_tok.get().strip().replace("\n", "").replace("\r", "")
            self.save_printer_config("", "", e_sn_c.get(), True, "cloud", raw_token)
            self.start_printer_listener()
            d.destroy()
        ttk.Button(t_cloud, text="Save & Connect Cloud", style='Purple.TButton', command=save_cloud).pack(pady=20)

    # --- BACKEND LOGIC ---
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
    def perform_auto_backup(self): pass
    def load_sticky_settings(self): return {}
    def save_sticky_settings(self): pass
    
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
        
        mode = self.printer_cfg.get('mode', 'local')
        if mode == 'local':
             # LOCAL MODE: Use IP and Access Code
             host = self.printer_cfg.get('ip')
             user = "bblp"
             password = self.printer_cfg.get('access_code')
             serial = self.printer_cfg.get('serial')
        else:
             # CLOUD MODE: Use US Server and Token
             host = "us.mqtt.bambulab.com"
             user = "bblp"
             password = self.printer_cfg.get('token')
             serial = self.printer_cfg.get('serial')

        if password and serial:
            self.printer_client = BambuPrinterClient(host, user, password, serial, self.on_printer_status_update, lambda x: None)
            self.printer_client.connect()

    def on_printer_status_update(self, data):
        # THREAD-SAFE UPDATE
        self.root.after(0, lambda: self._update_ui_safe(data))

    def _update_ui_safe(self, data):
        # --- ZOMBIE CHECK: Stop if widget is dead ---
        if not hasattr(self, 'lbl_live_state') or not self.lbl_live_state.winfo_exists():
            return 

        self.lbl_printer_status.config(text="Online", foreground=self.PURPLE_MAIN)
        self.lbl_live_state.config(text=data.get('state', 'IDLE'))
        
        pct = data.get('percent', 0)
        self.dash_progress['value'] = pct
        self.lbl_live_pct.config(text=f"{pct}%")
        
        rem = data.get('time_rem', 0)
        hours = rem // 60
        mins = rem % 60
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        self.lbl_live_time.config(text=f"Time Left: {time_str}")
        
        fname = data.get('file', 'No Job').replace(".gcode", "")
        self.lbl_live_file.config(text=fname[:25] + "..." if len(fname) > 25 else fname)
        
        self.lbl_live_temps.config(text=f"Nozzle: {int(data.get('nozzle',0))}°C | Bed: {int(data.get('bed',0))}°C")

    def open_add_filament_modal(self):
        self.add_win = tk.Toplevel(self.root)
        self.add_win.title("New Filament")
        self.add_win.geometry("800x700")
        self.add_win.configure(bg="white")

        # Header
        h = ttk.Frame(self.add_win, padding=20, style="Card.TFrame")
        h.pack(fill="x")
        ttk.Label(h, text="+ New Filament", font=("Segoe UI", 16, "bold"), background=self.CARD_BG).pack(anchor="w")
        ttk.Label(h, text="Enter the details of your new filament spool", font=("Segoe UI", 10), foreground="gray", background=self.CARD_BG).pack(anchor="w")

        # Scrollable Content if needed, but 800x700 fits. We'll use a frame.
        body = ttk.Frame(self.add_win, padding=20)
        body.pack(fill="both", expand=True)

        # 1. Quick Setup (Purple)
        f_qs = ttk.Frame(body, style='Card.TFrame', padding=15)
        f_qs.configure(style='Purple.TFrame') # Need to config this or just color it
        # Actually standard Card is white. I'll make a custom frame for purple bg effect or just use label
        f_qs.pack(fill="x", pady=(0, 15))
        # Purple strip hack: Use a label or frame with bg
        qs_head = ttk.Frame(f_qs, style='Card.TFrame'); qs_head.pack(fill="x")
        # Since I can't easily make a purple bg frame without defining style, I'll stick to white card with purple accent

        ttk.Label(qs_head, text="Quick Setup", font=("Segoe UI", 11, "bold"), background=self.CARD_BG).pack(anchor="w")
        ttk.Label(qs_head, text="Scan any filament label to auto-populate fields", font=("Segoe UI", 9), foreground="gray", background=self.CARD_BG).pack(anchor="w")
        ttk.Button(qs_head, text="Scan Label", style='Purple.TButton', command=self.open_ai_scanner_modal).pack(anchor="e", pady=(0, 10))

        # 2. Basic Info
        f_bi = ttk.Frame(body, style='Card.TFrame', padding=15)
        f_bi.pack(fill="x", pady=(0, 15))
        ttk.Label(f_bi, text="Basic Information", font=("Segoe UI", 11, "bold"), foreground=self.PURPLE_MAIN, background=self.CARD_BG).pack(anchor="w", pady=(0, 10))

        # Grid for inputs
        g_bi = ttk.Frame(f_bi, style='Card.TFrame'); g_bi.pack(fill="x")

        ttk.Label(g_bi, text="Brand", background=self.CARD_BG).grid(row=0, column=0, sticky="w", padx=5)
        self.entry_add_brand = ttk.Entry(g_bi, style='Clean.TEntry', width=20); self.entry_add_brand.grid(row=1, column=0, padx=5, pady=(0, 10))

        ttk.Label(g_bi, text="Material", background=self.CARD_BG).grid(row=0, column=1, sticky="w", padx=5)
        self.entry_add_mat = ttk.Combobox(g_bi, values=["PLA", "PETG", "ABS", "TPU", "ASA"], width=18); self.entry_add_mat.grid(row=1, column=1, padx=5, pady=(0, 10))

        ttk.Label(g_bi, text="Color", background=self.CARD_BG).grid(row=0, column=2, sticky="w", padx=5)
        self.entry_add_col = ttk.Entry(g_bi, style='Clean.TEntry', width=20); self.entry_add_col.grid(row=1, column=2, padx=5, pady=(0, 10))

        # 3. Storage & Cost
        f_sc = ttk.Frame(body, style='Card.TFrame', padding=15)
        f_sc.pack(fill="x", pady=(0, 15))
        ttk.Label(f_sc, text="Storage & Cost", font=("Segoe UI", 11, "bold"), foreground=self.PURPLE_MAIN, background=self.CARD_BG).pack(anchor="w", pady=(0, 10))

        g_sc = ttk.Frame(f_sc, style='Card.TFrame'); g_sc.pack(fill="x")
        ttk.Label(g_sc, text="Location", background=self.CARD_BG).grid(row=0, column=0, sticky="w", padx=5)
        self.entry_add_loc = ttk.Entry(g_sc, style='Clean.TEntry', width=30); self.entry_add_loc.grid(row=1, column=0, padx=5)
        self.entry_add_loc.insert(0, "General")

        ttk.Label(g_sc, text="Cost ($)", background=self.CARD_BG).grid(row=0, column=1, sticky="w", padx=5)
        self.entry_add_cost = ttk.Entry(g_sc, style='Clean.TEntry', width=15); self.entry_add_cost.grid(row=1, column=1, padx=5)

        # 4. Spool Management
        f_sm = ttk.Frame(body, style='Card.TFrame', padding=15)
        f_sm.pack(fill="x", pady=(0, 15))
        ttk.Label(f_sm, text="Spool Management", font=("Segoe UI", 11, "bold"), foreground=self.PURPLE_MAIN, background=self.CARD_BG).pack(anchor="w", pady=(0, 10))

        g_sm = ttk.Frame(f_sm, style='Card.TFrame'); g_sm.pack(fill="x")
        ttk.Label(g_sm, text="Total Weight (g)", background=self.CARD_BG).grid(row=0, column=0, sticky="w", padx=5)
        self.entry_add_weight = ttk.Entry(g_sm, style='Clean.TEntry', width=15); self.entry_add_weight.grid(row=1, column=0, padx=5)
        self.entry_add_weight.insert(0, "1000")

        # Footer Actions
        foot = ttk.Frame(self.add_win, padding=20)
        foot.pack(fill="x", side="bottom")

        self.var_add_another = tk.BooleanVar()
        ttk.Checkbutton(foot, text="Add another", variable=self.var_add_another).pack(side="left")

        ttk.Button(foot, text="+ Add Filament", style='Purple.TButton', command=self.save_new_filament).pack(side="right")

    def open_ai_scanner_modal(self):
        # Wrapper to target the new modal fields
        path = filedialog.askopenfilename()
        if not path: return
        res = self.ai_manager.analyze_spool_image(path)
        if res and not 'error' in res:
             if res.get('brand'): self.entry_add_brand.delete(0, tk.END); self.entry_add_brand.insert(0, res.get('brand'))
             if res.get('color'): self.entry_add_col.delete(0, tk.END); self.entry_add_col.insert(0, res.get('color'))
             if res.get('material'): self.entry_add_mat.set(res.get('material'))
             if res.get('weight'): self.entry_add_weight.delete(0, tk.END); self.entry_add_weight.insert(0, str(res.get('weight')))

    def save_new_filament(self):
        try:
            item = {
                "id": str(len(self.inventory)+1).zfill(3),
                "name": self.entry_add_brand.get(),
                "material": self.entry_add_mat.get(),
                "color": self.entry_add_col.get(),
                "weight": float(self.entry_add_weight.get()),
                "cost": float(self.entry_add_cost.get()),
                "location": self.entry_add_loc.get()
            }
            self.inventory.append(item)
            self.save_json(self.inventory, DB_FILE)
            self.refresh_inventory_list()
            messagebox.showinfo("Success", "Filament Added")
            if not self.var_add_another.get():
                self.add_win.destroy()
            else:
                # Clear fields
                self.entry_add_brand.delete(0, tk.END)
                self.entry_add_col.delete(0, tk.END)
        except Exception as e: messagebox.showerror("Error", f"Check inputs: {e}")

    def refresh_inventory_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for item in self.inventory:
            # Clean display of weight (int cast)
            w = int(item.get('weight', 0))
            # Clean cost display (2 decimal places)
            c = float(item.get('cost', 0))
            l = item.get('location', '-')
            self.tree.insert("", "end", values=(item.get('name'), item.get('material'), item.get('color'), w, f"${c:.2f}", l))

    def refresh_history_list(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        for h in self.history:
            # Clean formatting for history table
            cost = float(h.get('cost', 0))
            price = float(h.get('sold_for', 0))
            profit = float(h.get('profit', 0))
            
            self.hist_tree.insert("", "end", values=(
                h.get('date'), 
                h.get('job'), 
                f"${cost:.2f}", 
                f"${price:.2f}", 
                f"${profit:.2f}"
            ))

    def cancel_edit(self):
        self.inv_name.delete(0, tk.END)
        self.inv_weight.delete(0, tk.END)

    def open_ai_scanner(self):
        path = filedialog.askopenfilename()
        if path:
             res = self.ai_manager.analyze_spool_image(path)
             if res:
                 self.inv_name.insert(0, res.get('brand', ''))
                 self.inv_color.insert(0, res.get('color', ''))
    
    # --- LEGACY METHODS ---
    def auto_gen_id(self): pass
    def edit_spool(self): pass
    def bulk_set_material(self): pass
    def delete_spool(self): pass
    def check_price(self): pass
    def generate_qr_label(self): pass
    def sort_column(self, c, r): pass
    def update_waste_estimate(self, e): pass
    def filter_filament_dropdown(self, e): pass
    def duplicate_queue_job(self): pass
    def delete_from_queue(self): pass
    def perform_maintenance(self): pass
    def on_guide_double_click(self, e): pass
    def perform_search(self): pass
    def update_material_view(self, e): 
        k = self.mat_var.get()
        if k in self.materials_data:
            self.txt_info.config(state="normal"); self.txt_info.delete("1.0", tk.END); self.txt_info.insert("1.0", self.materials_data[k]); self.txt_info.config(state="disabled")

if __name__ == "__main__":
    app = ttk.Window(themename="litera") 
    FilamentManagerApp(app)
    app.mainloop()