import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import sys
import shutil
import webbrowser
import ctypes.wintypes 
from datetime import datetime, timedelta
from PIL import Image, ImageTk 
import difflib 

# ======================================================
# CONFIGURATION
# ======================================================

APP_NAME = "PrintShopManager"
VERSION = "v5.0 (Maintenance Tracker)"

def get_real_windows_docs_path():
    try:
        CSIDL_PERSONAL = 5       
        SHGFP_TYPE_CURRENT = 0   
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
        return buf.value
    except:
        return os.path.join(os.path.expanduser("~"), "Documents")

if os.name == 'nt':
    DATA_DIR = os.path.join(os.environ['LOCALAPPDATA'], APP_NAME)
else:
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "filament_inventory.json")
HISTORY_FILE = os.path.join(DATA_DIR, "sales_history.json")
MAINT_FILE = os.path.join(DATA_DIR, "maintenance_log.json") # NEW FILE

DOCS_DIR = os.path.join(get_real_windows_docs_path(), "3D_Print_Receipts")
if not os.path.exists(DOCS_DIR):
    try:
        os.makedirs(DOCS_DIR, exist_ok=True)
    except OSError:
        DOCS_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "3D_Print_Receipts")
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
        self.root.geometry("1200x900") 

        self.inventory = self.load_json(DB_FILE)
        self.history = self.load_json(HISTORY_FILE)
        self.maintenance = self.load_json(MAINT_FILE) # Load Maint Data
        
        # Initialize Maintenance Defaults if empty
        if not self.maintenance:
            self.init_default_maintenance()

        self.current_job_filaments = []
        self.last_calculated_price = 0.0
        self.last_calculated_cost = 0.0
        self.editing_index = None
        
        self.init_materials_data()

        # Styles
        self.main_font = ("Segoe UI", 11)
        self.bold_font = ("Segoe UI", 11, "bold")
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(".", font=self.main_font)
        style.configure("Treeview", font=self.main_font, rowheight=28)
        style.configure("Treeview.Heading", font=self.bold_font)
        
        # Tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both", padx=5, pady=5)

        self.tab_calc = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_calc, text=" 🖩 Calculator ")
        self.build_calculator_tab()

        self.tab_inventory = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_inventory, text=" 📦 Inventory ")
        self.build_inventory_tab()

        self.tab_history = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_history, text=" 📜 History ")
        self.build_history_tab()

        self.tab_ref = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ref, text=" ℹ️ Reference ")
        self.build_reference_tab() 

        # NEW TAB: MAINTENANCE
        self.tab_maint = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_maint, text=" 🛠️ Maintenance ")
        self.build_maintenance_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    # --- HELPERS ---
    def load_json(self, filepath):
        if not os.path.exists(filepath): return []
        try:
            with open(filepath, "r") as f: return json.load(f)
        except: return []

    def save_json(self, data, filepath):
        with open(filepath, "w") as f: json.dump(data, f, indent=4)

    def on_tab_change(self, event):
        self.update_filament_dropdown()
        self.refresh_inventory_list()
        self.refresh_history_list()
        self.refresh_maintenance_list() # New refresh
        self.cancel_edit()
    
    def backup_data(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"Inventory_Backup_{datetime.now().strftime('%Y%m%d')}.json")
        if save_path:
            shutil.copy(DB_FILE, save_path)
            messagebox.showinfo("Backup", f"Saved to:\n{save_path}")

    # --- TAB 1: CALCULATOR ---
    def build_calculator_tab(self):
        frame = ttk.Frame(self.tab_calc, padding=10)
        frame.pack(fill="both", expand=True)

        name_frame = ttk.LabelFrame(frame, text=" Job Details ", padding=10)
        name_frame.pack(fill="x", pady=5)
        ttk.Label(name_frame, text="Job Name:").pack(side="left")
        self.entry_job_name = ttk.Entry(name_frame, width=30)
        self.entry_job_name.pack(side="left", padx=10, fill="x", expand=True)

        sel_frame = ttk.LabelFrame(frame, text=" Add Filament ", padding=10)
        sel_frame.pack(fill="x", pady=5)
        
        ttk.Label(sel_frame, text="Spool:").pack(side="left")
        self.combo_filaments = ttk.Combobox(sel_frame, state="readonly", width=30)
        self.combo_filaments.pack(side="left", padx=5)
        
        ttk.Label(sel_frame, text="Grams:").pack(side="left")
        self.entry_calc_grams = ttk.Entry(sel_frame, width=8)
        self.entry_calc_grams.pack(side="left", padx=5)
        
        ttk.Button(sel_frame, text="Add Color", command=self.add_to_job).pack(side="left", padx=10)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, pady=5)
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.list_job = tk.Listbox(list_frame, font=self.main_font, height=5, yscrollcommand=scrollbar.set)
        self.list_job.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.list_job.yview)
        ttk.Button(list_frame, text="Clear List", command=self.clear_job).pack(anchor="ne")

        set_frame = ttk.LabelFrame(frame, text=" Overhead ", padding=10)
        set_frame.pack(fill="x", pady=5)
        ttk.Label(set_frame, text="Time (Hrs):").pack(side="left")
        self.entry_hours = ttk.Entry(set_frame, width=6); self.entry_hours.pack(side="left", padx=5)
        
        ttk.Label(set_frame, text="Waste %:").pack(side="left", padx=10)
        self.entry_waste = ttk.Entry(set_frame, width=6); self.entry_waste.insert(0, "20"); self.entry_waste.pack(side="left", padx=5)
        
        ttk.Label(set_frame, text="Markup (x):").pack(side="left", padx=10)
        self.entry_markup = ttk.Entry(set_frame, width=6); self.entry_markup.insert(0, "2.0"); self.entry_markup.pack(side="left", padx=5)

        btn_frame = ttk.Frame(frame, padding=10)
        btn_frame.pack(fill="x")
        self.btn_calc = ttk.Button(btn_frame, text="CALCULATE", command=self.calculate_quote)
        self.btn_calc.pack(side="left", fill="x", expand=True, padx=5)
        
        self.btn_receipt = ttk.Button(btn_frame, text="💾 Save Pro Receipt", command=self.generate_receipt, state="disabled")
        self.btn_receipt.pack(side="left", fill="x", expand=True, padx=5)
        
        ttk.Button(btn_frame, text="📂 Open Folder", command=self.open_receipt_folder).pack(side="left", padx=5)

        self.result_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.result_var, font=("Courier", 12, "bold"), background="#eee", relief="sunken").pack(fill="x", pady=5)
        
        self.btn_deduct = ttk.Button(frame, text="✅ Print Done (Deduct Stock)", command=self.deduct_inventory, state="disabled")
        self.btn_deduct.pack(fill="x", pady=5)

    def update_filament_dropdown(self):
        vals = [f"{f['name']} ({f['color']}) - {int(f['weight'])}g" for f in self.inventory]
        self.combo_filaments['values'] = vals

    def add_to_job(self):
        idx = self.combo_filaments.current()
        if idx == -1: return
        try:
            spool = self.inventory[idx]
            grams = float(self.entry_calc_grams.get())
            cost = (spool['cost'] / 1000.0) * grams
            self.current_job_filaments.append({"spool": spool, "grams": grams, "cost": cost})
            self.list_job.insert(tk.END, f"{spool['name']} ({spool['color']}): {grams}g (${cost:.2f})")
            self.entry_calc_grams.delete(0, tk.END)
        except ValueError: messagebox.showerror("Error", "Invalid grams")

    def clear_job(self):
        self.current_job_filaments = []
        self.list_job.delete(0, tk.END)
        self.btn_deduct.config(state="disabled")
        self.btn_receipt.config(state="disabled")
        self.result_var.set("")

    def calculate_quote(self):
        if not self.current_job_filaments: return
        try:
            hours = float(self.entry_hours.get() or 0)
            waste = float(self.entry_waste.get()) / 100.0
            markup = float(self.entry_markup.get())
            
            raw_mat_cost = sum(x['cost'] for x in self.current_job_filaments)
            mat_with_waste = raw_mat_cost * (1 + waste)
            machine_cost = hours * 0.75 
            
            self.last_calculated_cost = mat_with_waste + machine_cost
            self.last_calculated_price = self.last_calculated_cost * markup
            
            res = f" Cost: ${self.last_calculated_cost:.2f}  |  Sell: ${self.last_calculated_price:.2f}"
            self.result_var.set(res)
            self.btn_deduct.config(state="normal")
            self.btn_receipt.config(state="normal")
        except ValueError: pass

    def deduct_inventory(self):
        if not messagebox.askyesno("Confirm", "Deduct filament from inventory?"): return
        for item in self.current_job_filaments:
            item['spool']['weight'] -= item['grams']
        
        self.save_json(self.inventory, DB_FILE)
        
        rec = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "job": self.entry_job_name.get() or "Unknown",
            "cost": self.last_calculated_cost,
            "sold_for": self.last_calculated_price
        }
        self.history.append(rec)
        self.save_json(self.history, HISTORY_FILE)
        
        self.clear_job()
        self.update_filament_dropdown()
        messagebox.showinfo("Success", "Inventory Updated!")

    def generate_receipt(self):
        job_name = self.entry_job_name.get() or "Custom Job"
        cust = simpledialog.askstring("Receipt", "Customer Name:") or "Valued Customer"
        
        fname = f"Invoice_{datetime.now().strftime('%Y%m%d-%H%M')}.txt"
        fpath = os.path.join(DOCS_DIR, fname)
        
        lines = [
            "="*60,
            f"{'3D PRINT SHOP INVOICE':^60}",
            "="*60,
            f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"CUSTOMER: {cust}",
            "-"*60,
            f"{'ITEM':<40} {'QTY':<5} {'PRICE':>10}",
            "-"*60,
            f"{job_name:<40} {'1':<5} ${self.last_calculated_price:>10.2f}",
        ]
        
        for f in self.current_job_filaments:
            lines.append(f"  > Material: {f['spool']['name']} {f['spool']['color']}")
            
        lines.extend([
            "-"*60,
            f"{'TOTAL':<40}       ${self.last_calculated_price:>10.2f}",
            "="*60,
            "",
            "CARE INSTRUCTIONS:",
            "* Keep away from high heat (>50C) to prevent warping.",
            "* Not food safe unless specified.",
            "",
            f"{'Thank you for your business!':^60}",
            "="*60
        ])
        
        try:
            with open(fpath, "w", encoding="utf-8") as f: f.write("\n".join(lines))
            os.startfile(fpath)
            messagebox.showinfo("Saved", f"Receipt saved to:\n{fpath}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def open_receipt_folder(self):
        os.startfile(DOCS_DIR)

    # --- TAB 2: INVENTORY ---
    def build_inventory_tab(self):
        frame = ttk.Frame(self.tab_inventory, padding=10)
        frame.pack(fill="both", expand=True)

        add_frame = ttk.LabelFrame(frame, text=" Add New Spool ", padding=10)
        add_frame.pack(fill="x", pady=5)
        
        ttk.Label(add_frame, text="Name:").grid(row=0, column=0, sticky="e")
        self.inv_name = ttk.Entry(add_frame, width=15); self.inv_name.grid(row=0, column=1, padx=5)
        
        ttk.Label(add_frame, text="Color:").grid(row=0, column=2, sticky="e")
        self.inv_color = ttk.Entry(add_frame, width=10); self.inv_color.grid(row=0, column=3, padx=5)
        
        ttk.Label(add_frame, text="Weight (g):").grid(row=0, column=4, sticky="e")
        self.inv_weight = ttk.Entry(add_frame, width=8); self.inv_weight.insert(0,"1000"); self.inv_weight.grid(row=0, column=5, padx=5)
        
        ttk.Label(add_frame, text="Cost ($):").grid(row=0, column=6, sticky="e")
        self.inv_cost = ttk.Entry(add_frame, width=8); self.inv_cost.insert(0,"20.00"); self.inv_cost.grid(row=0, column=7, padx=5)
        
        self.btn_inv_action = ttk.Button(add_frame, text="Add Spool", command=self.save_spool)
        self.btn_inv_action.grid(row=0, column=8, padx=10)
        
        ttk.Button(add_frame, text="Cancel Edit", command=self.cancel_edit).grid(row=0, column=9)

        tree_frame = ttk.Frame(frame); tree_frame.pack(fill="both", expand=True, pady=5)
        cols = ("Name", "Color", "Weight", "Cost")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for c in cols: self.tree.heading(c, text=c)
        
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        
        self.tree.tag_configure('low', background='#FFF2CC')
        self.tree.tag_configure('crit', background='#FFCCCC')
        
        btn_box = ttk.Frame(frame); btn_box.pack(fill="x", pady=5)
        ttk.Button(btn_box, text="Edit Selected", command=self.edit_spool).pack(side="left", padx=5)
        ttk.Button(btn_box, text="Delete Selected", command=self.delete_spool).pack(side="left", padx=5)
        ttk.Button(btn_box, text="Check Price Online", command=self.check_price).pack(side="left", padx=5)
        ttk.Button(btn_box, text="Backup Data", command=self.backup_data).pack(side="right", padx=5)

    def refresh_inventory_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for item in self.inventory:
            w = item['weight']
            tag = 'crit' if w < 50 else ('low' if w < 200 else '')
            self.tree.insert("", "end", values=(item['name'], item['color'], f"{w:.1f}", item['cost']), tags=(tag,))

    def save_spool(self):
        try:
            new_item = {
                "name": self.inv_name.get(),
                "color": self.inv_color.get(),
                "weight": float(self.inv_weight.get()),
                "cost": float(self.inv_cost.get())
            }
            if self.editing_index is not None:
                self.inventory[self.editing_index] = new_item
            else:
                self.inventory.append(new_item)
            
            self.save_json(self.inventory, DB_FILE)
            self.cancel_edit()
            self.refresh_inventory_list()
        except ValueError: messagebox.showerror("Error", "Check numbers")

    def edit_spool(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        item = self.inventory[idx]
        
        self.inv_name.delete(0, tk.END); self.inv_name.insert(0, item['name'])
        self.inv_color.delete(0, tk.END); self.inv_color.insert(0, item['color'])
        self.inv_weight.delete(0, tk.END); self.inv_weight.insert(0, str(item['weight']))
        self.inv_cost.delete(0, tk.END); self.inv_cost.insert(0, str(item['cost']))
        
        self.editing_index = idx
        self.btn_inv_action.config(text="Update Spool")

    def cancel_edit(self):
        self.editing_index = None
        self.inv_name.delete(0, tk.END)
        self.inv_color.delete(0, tk.END)
        self.inv_weight.delete(0, tk.END); self.inv_weight.insert(0, "1000")
        self.inv_cost.delete(0, tk.END); self.inv_cost.insert(0, "20.00")
        self.btn_inv_action.config(text="Add Spool")

    def delete_spool(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Confirm", "Delete?"):
            del self.inventory[self.tree.index(sel[0])]
            self.save_json(self.inventory, DB_FILE)
            self.refresh_inventory_list()

    def check_price(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            name = self.inventory[idx]['name']
            webbrowser.open(f"https://www.google.com/search?q={name} filament price")

    # --- TAB 3: HISTORY ---
    def build_history_tab(self):
        frame = ttk.Frame(self.tab_history, padding=10); frame.pack(fill="both", expand=True)
        cols = ("Date", "Job", "Cost", "Sold For", "Profit")
        self.hist_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols: self.hist_tree.heading(c, text=c)
        
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=sb.set)
        self.hist_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        
        ttk.Button(frame, text="Delete Record", command=self.del_history).pack(anchor="sw", pady=5)

    def refresh_history_list(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        for h in reversed(self.history):
            p = h['sold_for'] - h['cost']
            self.hist_tree.insert("", "end", values=(h['date'], h['job'], f"${h['cost']:.2f}", f"${h['sold_for']:.2f}", f"${p:.2f}"))

    def del_history(self):
        sel = self.hist_tree.selection()
        if sel and messagebox.askyesno("Confirm", "Delete Record?"):
            idx = len(self.history) - 1 - self.hist_tree.index(sel[0])
            del self.history[idx]
            self.save_json(self.history, HISTORY_FILE)
            self.refresh_history_list()

    # --- TAB 4: SMART SEARCH & MANUAL ---
    def build_reference_tab(self):
        main_frame = ttk.Frame(self.tab_ref, padding=10)
        main_frame.pack(fill="both", expand=True)

        # LEFT
        left_col = ttk.LabelFrame(main_frame, text=" Spool Estimator ", padding=10)
        left_col.pack(side="left", fill="both", expand=True, padx=5)
        try:
            spool_img = Image.open(IMAGE_FILE)
            spool_img.thumbnail((550, 750)) 
            self.ref_img_data = ImageTk.PhotoImage(spool_img)
            ttk.Label(left_col, image=self.ref_img_data).pack(anchor="center", pady=10)
        except: 
            ttk.Label(left_col, text="[spool_reference.png] missing").pack(pady=20)

        # RIGHT
        right_col = ttk.LabelFrame(main_frame, text=" Field Manual ", padding=10)
        right_col.pack(side="right", fill="both", expand=True, padx=5)

        # SEARCH
        search_frame = ttk.Frame(right_col)
        search_frame.pack(fill="x", pady=5)
        ttk.Label(search_frame, text="🔍 Search Issue (e.g. 'pop', 'stringing'):").pack(side="left", padx=5)
        self.entry_search = ttk.Entry(search_frame)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(search_frame, text="Search", command=self.perform_search).pack(side="left")
        self.entry_search.bind("<Return>", lambda e: self.perform_search())

        # DROPDOWN
        ttk.Label(right_col, text="Select Topic:").pack(anchor="w", pady=(5, 0))
        self.mat_var = tk.StringVar()
        
        self.combo_vals = (
            "PLA", "Silk PLA", "PETG", "ABS / ASA", "TPU", "Bambu Lab Profiles",
            "First Layer Guide", "Slicer Basics", "Under-Extrusion", "Wet Filament", 
            "Hardware Maintenance", "PEI Sheet", "Troubleshooting Guide"
        )
        self.mat_combo = ttk.Combobox(right_col, textvariable=self.mat_var, values=self.combo_vals, state="readonly")
        self.mat_combo.current(0)
        self.mat_combo.pack(fill="x", pady=5)

        # TEXT AREA
        self.txt_info = tk.Text(right_col, font=("Consolas", 11), wrap="word", bg="#f0f0f0", relief="sunken", padx=15, pady=15)
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
        
        keys = list(self.materials_data.keys())
        close_keys = difflib.get_close_matches(query, keys, n=3, cutoff=0.4)
        for k in close_keys:
            if not any(m[0] == k for m in matches): matches.append((k, 8))
        
        if not matches:
            messagebox.showinfo("No Results", f"No tips found for '{query}'")
            return
        
        matches.sort(key=lambda x: x[1], reverse=True)
        best_topic = matches[0][0]
        
        if len(matches) > 1:
            other_hits = ", ".join([m[0] for m in matches[1:4]]) 
            messagebox.showinfo("Multiple Matches", f"Jumped to: '{best_topic}'\n\nAlso found '{query}' in:\n{other_hits}")
        
        self.mat_combo.set(best_topic)
        self.update_material_view(None)

    def update_material_view(self, event):
        key = self.mat_var.get()
        text_data = self.materials_data.get(key, "No Data")
        
        self.txt_info.config(state="normal") 
        self.txt_info.delete("1.0", tk.END)  
        self.txt_info.insert("1.0", text_data)
        self.txt_info.config(state="disabled") 

    def init_materials_data(self):
        self.materials_data = {
            "PLA": (
                "MATERIAL: PLA (Polylactic Acid)\n"
                "==================================================\n"
                "Nozzle:   190 – 220 °C\n"
                "Bed:      45 – 60 °C\n"
                "Fan:      100% (Always On)\n"
                "Speed:    50 – 100+ mm/s\n"
                "Enclosure: NO (Keep door open)\n\n"
                "--- QUICK GUIDE ---\n"
                "Best For:    Beginners, visual models, prototypes.\n"
                "Adhesion:    Textured PEI (No Glue), Smooth PEI (Glue Optional), or Blue Tape.\n"
                "Critical:    Needs excellent cooling for overhangs.\n\n"
                "⚠️ COMMON ISSUES & FIXES:\n"
                "1. Curling Corners? -> Bed is dirty or too cold. Clean with soap.\n"
                "2. Heat Creep (Jams)? -> Printing too hot or enclosure is closed.\n"
                "3. Warping in Car? -> PLA melts at 55°C. Don't leave in hot cars."
            ),
            "Silk PLA": (
                "MATERIAL: Silk PLA (Shiny Blend)\n"
                "==================================================\n"
                "Nozzle:   205 – 225 °C\n"
                "Bed:      50 – 60 °C\n"
                "Fan:      100%\n"
                "Speed:    40 – 60 mm/s (SLOW)\n"
                "Enclosure: NO (Keep door open)\n\n"
                "--- QUICK GUIDE ---\n"
                "Best For:    Statues, vases, decorative items.\n"
                "Adhesion:    Standard PEI / Glue Stick.\n"
                "Critical:    Print SLOW and HOT for maximum shine.\n\n"
                "⚠️ COMMON ISSUES & FIXES:\n"
                "1. Dull Finish? -> Print hotter and slower.\n"
                "2. Clogs? -> 'Die Swell' (expansion) causes jams. Reduce flow 5%.\n"
                "3. Weak Parts? -> Silk has terrible layer adhesion. Do not use for mechanical parts."
            ),
            "PETG": (
                "MATERIAL: PETG (Polyethylene Terephthalate Glycol)\n"
                "==================================================\n"
                "Nozzle:   230 – 250 °C\n"
                "Bed:      70 – 85 °C\n"
                "Fan:      30 – 50% (Low)\n"
                "Speed:    40 – 60 mm/s\n"
                "Enclosure: NO (Draft-free room)\n\n"
                "--- QUICK GUIDE ---\n"
                "Best For:    Functional parts, snap-fits, outdoor use.\n"
                "Adhesion:    Textured PEI. AVOID SMOOTH GLASS (It fuses).\n"
                "Critical:    Raise Z-Offset +0.05mm. Don't squish the first layer.\n\n"
                "⚠️ COMMON ISSUES & FIXES:\n"
                "1. Stringing/Blobs? -> Filament is wet (Dry it!) or Flow is too high.\n"
                "2. Sticking too well? -> Use Glue Stick as a release agent.\n"
                "3. Poor Bridging? -> Increase fan speed for bridges only."
            ),
            "ABS / ASA": (
                "MATERIAL: ABS & ASA\n"
                "==================================================\n"
                "Nozzle:   230 – 260 °C\n"
                "Bed:      90 – 110 °C\n"
                "Fan:      0% (OFF)\n"
                "Speed:    40 – 60 mm/s\n"
                "Enclosure: YES (Mandatory)\n\n"
                "--- QUICK GUIDE ---\n"
                "Best For:    Car parts, high heat, acetone smoothing.\n"
                "Adhesion:    ABS Slurry (Acetone + Scrap) or Kapton Tape.\n"
                "Info:        ASA is similar to ABS but UV resistant (doesn't yellow in sun).\n\n"
                "⚠️ COMMON ISSUES & FIXES:\n"
                "1. Layer Cracks? -> Drafts in the room or Fan was on. Use enclosure.\n"
                "2. Warping off Bed? -> Use a large Brim (5-10mm) and hotter bed.\n"
                "3. Fumes? -> These release Styrene. Ventilate the room!"
            ),
            "TPU": (
                "MATERIAL: TPU (Flexible / Rubber)\n"
                "==================================================\n"
                "Nozzle:   210 – 230 °C\n"
                "Bed:      40 – 60 °C\n"
                "Fan:      50 – 100%\n"
                "Speed:    15 – 30 mm/s (VERY SLOW)\n"
                "Enclosure: NO\n\n"
                "--- QUICK GUIDE ---\n"
                "Best For:    Phone cases, tires, gaskets, drones.\n"
                "Adhesion:    Sticks too well to PEI. Use Glue Stick to release.\n"
                "Critical:    Disable Retraction on Bowden setups to prevent jams.\n\n"
                "⚠️ COMMON ISSUES & FIXES:\n"
                "1. Filament tangled in gears? -> Printing too fast. Slow down.\n"
                "2. Stringing? -> TPU strings naturally. Dry the filament.\n"
                "3. Under-extrusion? -> Loosen extruder tension arm."
            ),
            "Bambu Lab Profiles": (
                "=== BAMBU LAB CHEAT SHEET (X1/P1/A1) ===\n\n"
                "1. INFILL PATTERN: Gyroid (Always!)\n"
                "   Why? The nozzle hits 'Grid' or 'Cubic' infill at high speeds.\n\n"
                "2. WALL GENERATOR: Arachne\n"
                "   Why? Better quality on small text and variable width walls.\n\n"
                "3. TPU IN AMS? NO.\n"
                "   The Automatic Material System jams with flexible filament.\n"
                "   Use the external spool holder for TPU.\n"
                "   Limit 'Max Volumetric Speed' to 2.5 mm³/s in filament settings.\n\n"
                "4. CARDBOARD SPOOLS IN AMS\n"
                "   Risk: Cardboard dust clogs gears / Spools dent and jam.\n"
                "   Fix: Wrap edges in electrical tape OR print 'Spool Adapter Rings'."
            ),
            "First Layer Guide": (
                "=== THE FIRST LAYER (Z-OFFSET) ===\n"
                "The #1 cause of print failure is the nozzle distance from the bed.\n\n"
                "1. NOZZLE TOO HIGH:\n"
                "   LOOKS LIKE: Round strands of spaghetti. Gaps between lines.\n"
                "   RESULT: Part pops off mid-print.\n"
                "   FIX: Lower Z-Offset (more negative number).\n\n"
                "2. NOZZLE TOO LOW:\n"
                "   LOOKS LIKE: Rough, sandpaper texture. Transparent layers.\n"
                "   RESULT: Clogged nozzle, Elephant's foot.\n"
                "   FIX: Raise Z-Offset.\n\n"
                "3. PERFECT SQUISH:\n"
                "   LOOKS LIKE: Flat surface, lines fused together, smooth touch.\n"
                "   TEST: Print a single layer square. It should be solid, not stringy."
            ),
            "Slicer Basics": (
                "=== SLICER BASICS (Terminology) ===\n\n"
                "1. PERIMETERS (WALLS)\n"
                "   - The outer shell. Strength comes from WALLS, not infill.\n"
                "   - Standard: 2 walls. Strong: 4 walls.\n\n"
                "2. INFILL\n"
                "   - The internal structure. 15-20% is standard.\n"
                "   - Use 'Gyroid' for best strength/speed balance.\n\n"
                "3. SUPPORTS\n"
                "   - Scaffolding for overhangs > 45 degrees.\n"
                "   - Use 'Tree/Organic' supports to save plastic and time.\n\n"
                "4. BRIM vs. SKIRT\n"
                "   - Skirt: A line around the print to prime the nozzle (Does not touch part).\n"
                "   - Brim: A flat hat attached to the part to prevent warping."
            ),
            "Under-Extrusion": (
                "=== UNDER-EXTRUSION (Gaps/Spongy Parts) ===\n\n"
                "SYMPTOM: Missing layers, gaps in walls, weak infill.\n"
                "CAUSE: The printer can't push plastic fast enough.\n\n"
                "1. THE 'CLICKING' SOUND:\n"
                "   - Extruder gear is slipping because nozzle is blocked.\n"
                "   - FIX: Check for clog, increase temp 5°C, or slow down.\n\n"
                "2. PARTIAL CLOG:\n"
                "   - Filament comes out curling to one side.\n"
                "   - FIX: Perform a 'Cold Pull' (Heat to 200, cool to 90, yank filament out).\n\n"
                "3. CRACKED EXTRUDER ARM:\n"
                "   - Common on Creality/Ender printers.\n"
                "   - FIX: Inspect the plastic arm near the gears for hairline cracks."
            ),
            "Wet Filament": (
                "=== WET FILAMENT DIAGNOSIS ===\n\n"
                "Plastic absorbs moisture from the air (Hygroscopic).\n"
                "Even new vacuum-sealed rolls can be wet!\n\n"
                "SYMPTOMS:\n"
                "1. Popping/Hissing sounds while printing.\n"
                "2. Excessive Stringing that retraction settings won't fix.\n"
                "3. Rough/Fuzzy surface texture.\n"
                "4. Brittle filament (snaps when you bend it).\n\n"
                "FIX: You must dry it.\n"
                "- Filament Dryer: 45°C (PLA) / 65°C (PETG) for 6 hours.\n"
                "- Food Dehydrator works well too.\n"
                "- DO NOT use a kitchen oven (inaccurate temps will melt spool)."
            ),
            "Hardware Maintenance": (
                "=== MONTHLY HARDWARE CHECK ===\n\n"
                "1. ECCENTRIC NUTS (Wobble Check):\n"
                "   - Grab the print head and bed. Do they wobble?\n"
                "   - FIX: Tighten the single nut on the inner wheel until wobble stops.\n\n"
                "2. BELT TENSION:\n"
                "   - Loose belts = Oval circles and layer shifts.\n"
                "   - Tight belts = Motor strain.\n"
                "   - FIX: Should twang like a low bass guitar string.\n\n"
                "3. CLEAN THE Z-ROD:\n"
                "   - Clean old grease/dust off the tall lead screw.\n"
                "   - Apply fresh PTFE lube or White Lithium Grease."
            ),
            "PEI Sheet": (
                "=== PEI SHEET (The Gold Standard) ===\n\n"
                "Polyetherimide (PEI) is the most popular modern print surface.\n\n"
                "1. TEXTURED PEI (Rough/Gold):\n"
                "   - Great for PETG and PLA.\n"
                "   - NO GLUE needed for PLA. Let the bed cool, and prints pop off.\n\n"
                "2. SMOOTH PEI (Flat/Black/Gold):\n"
                "   - Gives a mirror finish to the bottom of prints.\n"
                "   - WARNING: PETG and TPU stick too well to smooth PEI and can rip the sheet.\n"
                "   - FIX: Use Glue Stick as a release agent for PETG/TPU."
            ),
            "Troubleshooting Guide": (
                "=== UNIVERSAL TROUBLESHOOTING GUIDE ===\n\n"
                "1. WARPING (Corners lifting off bed)\n"
                "   WHY? Plastic shrinks as it cools. Cool air pulls corners up.\n"
                "   FIX: \n"
                "   - Clean bed with Dish Soap (Grease is the enemy).\n"
                "   - Raise Bed Temp 5-10°C.\n"
                "   - Use a 'Brim' in slicer.\n"
                "   - Stop drafts (Close windows/doors).\n\n"
                "2. STRINGING (Cobwebs between parts)\n"
                "   WHY? Nozzle leaking pressure while moving.\n"
                "   FIX:\n"
                "   - Dry your filament (Wet filament = steam = pressure).\n"
                "   - Lower Nozzle Temp 5-10°C.\n"
                "   - Increase Retraction Distance.\n\n"
                "3. ELEPHANT'S FOOT (Bottom layers flared out)\n"
                "   WHY? Bed is too hot or Nozzle is too close, squishing layers.\n"
                "   FIX:\n"
                "   - Lower Bed Temp 5°C.\n"
                "   - Baby-step Z-Offset UP slightly during first layer.\n\n"
                "4. LAYER SHIFT (Staircase effect)\n"
                "   WHY? Printer hit something or belts slipped.\n"
                "   FIX:\n"
                "   - Tighten Belts (Should twang like a guitar string).\n"
                "   - Check if nozzle hit a curled-up overhang."
            )
        }

    # --- TAB 5: MAINTENANCE TRACKER (NEW!) ---
    def build_maintenance_tab(self):
        frame = ttk.Frame(self.tab_maint, padding=10)
        frame.pack(fill="both", expand=True)

        cols = ("Task", "Freq", "Last Done", "Status")
        self.maint_tree = ttk.Treeview(frame, columns=cols, show="headings", height=15)
        for c in cols: self.maint_tree.heading(c, text=c)
        self.maint_tree.column("Task", width=300)
        self.maint_tree.column("Freq", width=100)
        self.maint_tree.column("Last Done", width=150)
        
        self.maint_tree.pack(side="left", fill="both", expand=True)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side="right", fill="y", padx=10)
        
        ttk.Button(btn_frame, text="✅ Do Task Now", command=self.perform_maintenance).pack(pady=5, fill="x")
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
            self.maint_tree.insert("", "end", iid=idx, values=(item['task'], item['freq'], item['last'], ""))

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
    root = tk.Tk()
    app = FilamentManagerApp(root)
    root.mainloop()