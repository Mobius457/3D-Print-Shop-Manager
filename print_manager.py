import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import sys
import shutil
import webbrowser
import ctypes.wintypes 
from datetime import datetime
from PIL import Image, ImageTk 
import difflib 
import math

# ======================================================
# CONFIGURATION
# ======================================================

APP_NAME = "PrintShopManager"
VERSION = "v6.4 (Inventory Restore)"

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
MAINT_FILE = os.path.join(DATA_DIR, "maintenance_log.json")

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
        self.root.geometry("1280x950") 

        self.inventory = self.load_json(DB_FILE)
        self.history = self.load_json(HISTORY_FILE)
        self.maintenance = self.load_json(MAINT_FILE)
        
        if not self.maintenance:
            self.init_default_maintenance()

        self.current_job_filaments = []
        self.calc_vals = {
            "mat_cost": 0.0, "overhead": 0.0, "labor": 0.0, 
            "subtotal": 0.0, "total": 0.0, "profit": 0.0, "margin": 0.0
        }
        self.editing_index = None
        
        self.init_materials_data()

        # Styles
        self.main_font = ("Segoe UI", 10)
        self.bold_font = ("Segoe UI", 10, "bold")
        
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
        self.notebook.add(self.tab_history, text=" 📜 History & Analytics ")
        self.build_history_tab()

        self.tab_ref = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ref, text=" ℹ️ Reference ")
        self.build_reference_tab() 

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
        self.refresh_maintenance_list()
        self.cancel_edit()
    
    def backup_data(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"Inventory_Backup_{datetime.now().strftime('%Y%m%d')}.json")
        if save_path:
            shutil.copy(DB_FILE, save_path)
            messagebox.showinfo("Backup", f"Saved to:\n{save_path}")

    # --- TAB 1: CALCULATOR ---
    def build_calculator_tab(self):
        paned = ttk.PanedWindow(self.tab_calc, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        # LEFT PANEL
        frame_left = ttk.Frame(paned)
        paned.add(frame_left, weight=1)

        # 1. Job Info
        f_job = ttk.LabelFrame(frame_left, text="1. Job Details", padding=10)
        f_job.pack(fill="x", pady=5)
        ttk.Label(f_job, text="Name:").pack(side="left")
        self.entry_job_name = ttk.Entry(f_job)
        self.entry_job_name.pack(side="left", fill="x", expand=True, padx=5)

        # 2. Materials
        f_mat = ttk.LabelFrame(frame_left, text="2. Materials", padding=10)
        f_mat.pack(fill="x", pady=5)
        
        ttk.Label(f_mat, text="Spool:").grid(row=0, column=0, sticky="w")
        self.combo_filaments = ttk.Combobox(f_mat, state="readonly", width=25)
        self.combo_filaments.grid(row=0, column=1, padx=5, sticky="ew")
        
        ttk.Label(f_mat, text="Grams:").grid(row=0, column=2, sticky="w")
        self.entry_calc_grams = ttk.Entry(f_mat, width=8)
        self.entry_calc_grams.grid(row=0, column=3, padx=5)
        
        ttk.Button(f_mat, text="Add", command=self.add_to_job).grid(row=0, column=4, padx=5)
        
        self.list_job = tk.Listbox(f_mat, height=4, font=("Segoe UI", 9))
        self.list_job.grid(row=1, column=0, columnspan=5, sticky="ew", pady=5)
        ttk.Button(f_mat, text="Clear List", command=self.clear_job).grid(row=2, column=4, sticky="e")

        # 3. Overhead & Labor
        f_over = ttk.LabelFrame(frame_left, text="3. Labor & Overhead", padding=10)
        f_over.pack(fill="x", pady=5)
        
        ttk.Label(f_over, text="Print Time (h):").grid(row=0, column=0, sticky="e")
        self.entry_hours = ttk.Entry(f_over, width=6); self.entry_hours.grid(row=0, column=1, padx=5)
        
        ttk.Label(f_over, text="Waste %:").grid(row=0, column=2, sticky="e")
        self.entry_waste = ttk.Entry(f_over, width=6); self.entry_waste.insert(0,"20"); self.entry_waste.grid(row=0, column=3, padx=5)
        
        ttk.Label(f_over, text="Processing ($):").grid(row=1, column=0, sticky="e", pady=5)
        self.entry_processing = ttk.Entry(f_over, width=6); self.entry_processing.insert(0,"0.00"); self.entry_processing.grid(row=1, column=1, padx=5)
        ttk.Label(f_over, text="(Assembly/Paint)").grid(row=1, column=2, columnspan=2, sticky="w")

        # 4. Pricing Strategy
        f_price = ttk.LabelFrame(frame_left, text="4. Pricing Strategy", padding=10)
        f_price.pack(fill="x", pady=5)
        
        ttk.Label(f_price, text="Markup (x):").grid(row=0, column=0, sticky="e")
        self.entry_markup = ttk.Entry(f_price, width=6); self.entry_markup.insert(0,"2.5"); self.entry_markup.grid(row=0, column=1, padx=5)
        
        ttk.Label(f_price, text="Discount (%):").grid(row=0, column=2, sticky="e")
        self.entry_discount = ttk.Entry(f_price, width=6); self.entry_discount.insert(0,"0"); self.entry_discount.grid(row=0, column=3, padx=5)
        
        self.var_round = tk.BooleanVar(value=False)
        self.var_donate = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(f_price, text="Round to nearest $", variable=self.var_round).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Checkbutton(f_price, text="Donation (Tax Write-off)", variable=self.var_donate).grid(row=1, column=2, columnspan=2, sticky="w", pady=5)

        # RIGHT PANEL
        frame_right = ttk.Frame(paned, padding=10)
        paned.add(frame_right, weight=1)
        
        ttk.Button(frame_right, text="CALCULATE QUOTE", command=self.calculate_quote).pack(fill="x", pady=10)
        
        self.lbl_breakdown = ttk.Label(frame_right, text="Enter details...", font=("Consolas", 11), justify="left", background="white", relief="sunken", padding=10)
        self.lbl_breakdown.pack(fill="both", expand=True)
        
        self.lbl_profit_warn = ttk.Label(frame_right, text="", font=("Arial", 12, "bold"))
        self.lbl_profit_warn.pack(pady=5)

        self.btn_receipt = ttk.Button(frame_right, text="💾 Save Receipt", command=self.generate_receipt, state="disabled")
        self.btn_receipt.pack(fill="x", pady=5)
        
        self.btn_deduct = ttk.Button(frame_right, text="✅ Finalize Sale", command=self.deduct_inventory, state="disabled")
        self.btn_deduct.pack(fill="x", pady=5)
        
        ttk.Button(frame_right, text="📂 Open Receipts", command=self.open_receipt_folder).pack(side="bottom", pady=5)

    # --- LOGIC: CALCULATOR ---
    def update_filament_dropdown(self):
        vals = []
        for f in self.inventory:
            mat = f.get('material', 'PLA')
            vals.append(f"{f['name']} ({mat}) - {int(f['weight'])}g")
        self.combo_filaments['values'] = vals

    def add_to_job(self):
        idx = self.combo_filaments.current()
        if idx == -1: return
        try:
            spool = self.inventory[idx]
            grams = float(self.entry_calc_grams.get())
            cost = (spool['cost'] / 1000.0) * grams
            self.current_job_filaments.append({"spool": spool, "grams": grams, "cost": cost})
            
            mat = spool.get('material', 'PLA')
            self.list_job.insert(tk.END, f"{spool['name']} ({mat}): {grams}g (${cost:.2f})")
            self.entry_calc_grams.delete(0, tk.END)
        except ValueError: messagebox.showerror("Error", "Invalid grams")

    def clear_job(self):
        self.current_job_filaments = []
        self.list_job.delete(0, tk.END)
        self.btn_deduct.config(state="disabled")
        self.btn_receipt.config(state="disabled")
        self.lbl_breakdown.config(text="")
        self.lbl_profit_warn.config(text="")

    def calculate_quote(self):
        if not self.current_job_filaments: return
        try:
            hours = float(self.entry_hours.get() or 0)
            waste = float(self.entry_waste.get()) / 100.0
            process_fee = float(self.entry_processing.get())
            markup = float(self.entry_markup.get())
            discount_pct = float(self.entry_discount.get()) / 100.0
            
            raw_mat_cost = sum(x['cost'] for x in self.current_job_filaments)
            mat_total = raw_mat_cost * (1 + waste)
            machine_cost = hours * 0.75 
            base_cost = mat_total + machine_cost + process_fee 
            
            subtotal = base_cost * markup
            discount_amt = subtotal * discount_pct
            final_price = subtotal - discount_amt
            
            if self.var_round.get(): final_price = round(final_price)
            is_donation = self.var_donate.get()
            if is_donation: final_price = 0.00
            
            profit = final_price - base_cost
            margin = (profit / final_price * 100) if final_price > 0 else 0
            
            self.calc_vals = {
                "mat": mat_total, "mach": machine_cost, "proc": process_fee,
                "cost": base_cost, "price": final_price, "profit": profit, 
                "margin": margin, "disc_amt": discount_amt
            }
            
            txt = (
                f"--- COST BREAKDOWN ---\n"
                f"Materials:      ${mat_total:.2f}\n"
                f"Machine Time:   ${machine_cost:.2f}\n"
                f"Processing:     ${process_fee:.2f}\n"
                f"TOTAL COST:     ${base_cost:.2f}\n"
                f"----------------------\n"
                f"Base Price:     ${subtotal:.2f}\n"
                f"Discount:      -${discount_amt:.2f}\n"
                f"----------------------\n"
                f"FINAL PRICE:    ${final_price:.2f}\n"
                f"Net Profit:     ${profit:.2f}"
            )
            
            if is_donation: txt += "\n(DONATION - Tax Write-off)"
            
            self.lbl_breakdown.config(text=txt)
            
            if is_donation:
                self.lbl_profit_warn.config(text="DONATION", foreground="blue")
            elif margin >= 50:
                self.lbl_profit_warn.config(text=f"Great Margin ({margin:.0f}%)", foreground="green")
            elif margin >= 30:
                self.lbl_profit_warn.config(text=f"Good Margin ({margin:.0f}%)", foreground="#AA8800")
            else:
                self.lbl_profit_warn.config(text=f"Low Margin ({margin:.0f}%)", foreground="red")

            self.btn_deduct.config(state="normal")
            self.btn_receipt.config(state="normal")
            
        except ValueError: messagebox.showerror("Error", "Check inputs")

    def deduct_inventory(self):
        if not messagebox.askyesno("Confirm", "Finalize Sale?"): return
        
        # Save snapshot of items used for potential restoration later
        items_snapshot = []
        for item in self.current_job_filaments:
            item['spool']['weight'] -= item['grams']
            items_snapshot.append({
                "name": item['spool']['name'],
                "material": item['spool'].get('material', 'Unknown'),
                "color": item['spool']['color'],
                "grams": item['grams']
            })
            
        self.save_json(self.inventory, DB_FILE)
        
        rec = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "job": self.entry_job_name.get() or "Unknown",
            "cost": self.calc_vals['cost'],
            "sold_for": self.calc_vals['price'],
            "is_donation": self.var_donate.get(),
            "profit": self.calc_vals['profit'],
            "items": items_snapshot # Save for restore
        }
        self.history.append(rec)
        self.save_json(self.history, HISTORY_FILE)
        
        self.clear_job()
        self.update_filament_dropdown()
        self.refresh_history_list() 
        messagebox.showinfo("Success", "Inventory Updated!")

    def generate_receipt(self):
        job_name = self.entry_job_name.get() or "Custom Job"
        cust = simpledialog.askstring("Receipt", "Customer Name:") or "Valued Customer"
        
        fname = f"Invoice_{datetime.now().strftime('%Y%m%d-%H%M')}.txt"
        fpath = os.path.join(DOCS_DIR, fname)
        
        header = "DONATION RECEIPT" if self.var_donate.get() else "INVOICE"
        
        lines = [
            "="*60,
            f"{'3D PRINT SHOP ' + header:^60}",
            "="*60,
            f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"CUSTOMER: {cust}",
            "-"*60,
            f"{'ITEM':<35} {'DETAILS':<15} {'PRICE':>8}",
            "-"*60,
            f"{job_name:<35} {'Custom Print':<15} ${self.calc_vals['price'] + self.calc_vals['disc_amt']:>8.2f}",
        ]
        
        for f in self.current_job_filaments:
            mat = f['spool'].get('material', 'PLA')
            lines.append(f"  > {f['spool']['name']} ({mat})")
            
        if self.calc_vals['proc'] > 0:
            lines.append(f"  > Post-Processing Included")

        lines.append("-" * 60)
        
        if self.calc_vals['disc_amt'] > 0:
             lines.append(f"{'DISCOUNT APPLIED:':<35}               -${self.calc_vals['disc_amt']:>8.2f}")

        lines.extend([
            f"{'TOTAL':<35}               ${self.calc_vals['price']:>8.2f}",
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
        try:
            os.startfile(DOCS_DIR)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open folder: {e}")

    # --- TAB 2: INVENTORY (v6.3) ---
    def build_inventory_tab(self):
        frame = ttk.Frame(self.tab_inventory, padding=10)
        frame.pack(fill="both", expand=True)

        add_frame = ttk.LabelFrame(frame, text=" Add New Spool ", padding=10)
        add_frame.pack(fill="x", pady=5)
        
        ttk.Label(add_frame, text="Brand/Name:").grid(row=0, column=0, sticky="e")
        self.inv_name = ttk.Entry(add_frame, width=15); self.inv_name.grid(row=0, column=1, padx=5)
        
        ttk.Label(add_frame, text="Material:").grid(row=0, column=2, sticky="e")
        self.inv_mat_var = tk.StringVar()
        self.cb_inv_mat = ttk.Combobox(add_frame, textvariable=self.inv_mat_var, values=("PLA", "PETG", "TPU", "ABS", "ASA", "Silk", "Other"), width=8)
        self.cb_inv_mat.grid(row=0, column=3, padx=5)
        
        ttk.Label(add_frame, text="Color:").grid(row=0, column=4, sticky="e")
        self.inv_color = ttk.Entry(add_frame, width=10); self.inv_color.grid(row=0, column=5, padx=5)
        
        ttk.Label(add_frame, text="Cost ($):").grid(row=0, column=6, sticky="e")
        self.inv_cost = ttk.Entry(add_frame, width=6); self.inv_cost.insert(0,"20.00"); self.inv_cost.grid(row=0, column=7, padx=5)

        ttk.Label(add_frame, text="Weight (g):").grid(row=1, column=0, sticky="e", pady=5)
        self.inv_weight = ttk.Entry(add_frame, width=8); self.inv_weight.insert(0,"1000"); self.inv_weight.grid(row=1, column=1, padx=5)
        
        self.tare_var = tk.IntVar(value=0)
        ttk.Radiobutton(add_frame, text="Net", variable=self.tare_var, value=0).grid(row=1, column=2)
        ttk.Radiobutton(add_frame, text="Plastic Spool", variable=self.tare_var, value=220).grid(row=1, column=3, columnspan=2)
        ttk.Radiobutton(add_frame, text="Cardboard", variable=self.tare_var, value=140).grid(row=1, column=5, columnspan=2)
        
        self.btn_inv_action = ttk.Button(add_frame, text="Add Spool", command=self.save_spool)
        self.btn_inv_action.grid(row=1, column=7, padx=5)
        ttk.Button(add_frame, text="Cancel", command=self.cancel_edit).grid(row=1, column=8)

        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill="x", pady=5)
        ttk.Label(filter_frame, text="🔍 Filter (Brand or Material):").pack(side="left")
        self.inv_filter_var = tk.StringVar()
        self.inv_filter_var.trace("w", lambda name, index, mode: self.refresh_inventory_list())
        ttk.Entry(filter_frame, textvariable=self.inv_filter_var).pack(side="left", fill="x", expand=True, padx=5)

        cols = ("Name", "Material", "Color", "Weight", "Cost")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=12)
        for c in cols: self.tree.heading(c, text=c)
        self.tree.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="right", fill="y")
        
        self.tree.tag_configure('low', background='#FFF2CC')
        self.tree.tag_configure('crit', background='#FFCCCC')
        
        self.lbl_inv_total = ttk.Label(frame, text="Total: 0 Spools", font=("Segoe UI", 10, "bold"), background="#ddd", anchor="center")
        self.lbl_inv_total.pack(fill="x")

        btn_box = ttk.Frame(self.tab_inventory, padding=5); btn_box.pack(fill="x")
        ttk.Button(btn_box, text="Edit Selected", command=self.edit_spool).pack(side="left", padx=5)
        ttk.Button(btn_box, text="Set Material (Bulk)", command=self.bulk_set_material).pack(side="left", padx=5)
        ttk.Button(btn_box, text="Delete", command=self.delete_spool).pack(side="left", padx=5)
        ttk.Button(btn_box, text="Check Price", command=self.check_price).pack(side="left", padx=5)
        
        self.refresh_inventory_list() 

    def refresh_inventory_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        filter_txt = self.inv_filter_var.get().lower().strip()
        total_grams = 0
        count = 0
        
        for idx, item in enumerate(self.inventory): 
            mat = item.get('material', 'Unknown')
            # Check filter
            if filter_txt and (filter_txt not in item['name'].lower() and filter_txt not in mat.lower()):
                continue
                
            w = item['weight']
            total_grams += w
            count += 1
            
            tag = 'crit' if w < 50 else ('low' if w < 200 else '')
            # IID matches index in main list for consistency
            self.tree.insert("", "end", iid=idx, values=(item['name'], mat, item['color'], f"{w:.1f}", item['cost']), tags=(tag,))
            
        self.lbl_inv_total.config(text=f"Total: {count} Spools  |  {total_grams/1000:.1f} kg Filament")

    def save_spool(self):
        try:
            raw_weight = float(self.inv_weight.get())
            tare = self.tare_var.get()
            final_weight = raw_weight - tare
            if final_weight <= 0:
                messagebox.showerror("Error", "Weight too low!")
                return

            new_item = {
                "name": self.inv_name.get(),
                "material": self.cb_inv_mat.get(),
                "color": self.inv_color.get(),
                "weight": final_weight,
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
        if not sel:
            messagebox.showinfo("Select", "Select items to edit.")
            return

        if len(sel) > 1:
            self.open_bulk_edit(sel)
            return

        try:
            idx = int(sel[0]) 
            item = self.inventory[idx]
            self.inv_name.delete(0, tk.END); self.inv_name.insert(0, item['name'])
            self.cb_inv_mat.set(item.get('material', 'PLA'))
            self.inv_color.delete(0, tk.END); self.inv_color.insert(0, item['color'])
            self.inv_weight.delete(0, tk.END); self.inv_weight.insert(0, str(item['weight']))
            self.inv_cost.delete(0, tk.END); self.inv_cost.insert(0, str(item['cost']))
            self.tare_var.set(0)
            self.editing_index = idx
            self.btn_inv_action.config(text="Update Spool")
        except:
            messagebox.showerror("Error", "Could not load item.")

    def open_bulk_edit(self, selection):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Bulk Edit ({len(selection)} items)")
        dialog.geometry("400x350")
        
        ttk.Label(dialog, text="Check box to apply change:", font=("Segoe UI", 9, "bold")).pack(pady=10)
        
        f = ttk.Frame(dialog, padding=10)
        f.pack(fill="both", expand=True)
        
        chk_name = tk.BooleanVar(); val_name = tk.StringVar()
        chk_mat = tk.BooleanVar(); val_mat = tk.StringVar()
        chk_col = tk.BooleanVar(); val_col = tk.StringVar()
        chk_cost = tk.BooleanVar(); val_cost = tk.StringVar()
        
        ttk.Checkbutton(f, text="Name:", variable=chk_name).grid(row=0, column=0, sticky="w")
        ttk.Entry(f, textvariable=val_name).grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Checkbutton(f, text="Material:", variable=chk_mat).grid(row=1, column=0, sticky="w")
        ttk.Combobox(f, textvariable=val_mat, values=("PLA", "PETG", "TPU", "ABS", "ASA", "Silk"), width=10).grid(row=1, column=1, sticky="ew", padx=5)
        
        ttk.Checkbutton(f, text="Color:", variable=chk_col).grid(row=2, column=0, sticky="w")
        ttk.Entry(f, textvariable=val_col).grid(row=2, column=1, sticky="ew", padx=5)
        
        ttk.Checkbutton(f, text="Cost ($):", variable=chk_cost).grid(row=3, column=0, sticky="w")
        ttk.Entry(f, textvariable=val_cost).grid(row=3, column=1, sticky="ew", padx=5)
        
        ttk.Label(f, text="*Note: Name/Color apply identical values to all.*", font=("Arial", 8), foreground="gray").grid(row=4, column=0, columnspan=2, pady=10)

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
                count += 1
            
            self.save_json(self.inventory, DB_FILE)
            self.refresh_inventory_list()
            dialog.destroy()
            messagebox.showinfo("Success", f"Updated {count} items!")
            
        ttk.Button(dialog, text="APPLY CHANGES", command=apply_bulk).pack(pady=10)

    # Simplified Bulk Material only button (Keep for convenience)
    def bulk_set_material(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select items first.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Quick Material Set")
        dialog.geometry("300x150")
        ttk.Label(dialog, text=f"Set Material for {len(sel)} items:").pack(pady=10)
        
        m_var = tk.StringVar()
        cb = ttk.Combobox(dialog, textvariable=m_var, values=("PLA Basic", "PETG", "TPU", "ABS", "ASA", "Silk", "Other"), state="readonly")
        cb.pack(pady=5)
        cb.current(0)
        
        def commit():
            new_mat = m_var.get()
            for iid in sel:
                self.inventory[int(iid)]['material'] = new_mat
            self.save_json(self.inventory, DB_FILE)
            self.refresh_inventory_list()
            dialog.destroy()
            messagebox.showinfo("Success", "Materials Updated!")
            
        ttk.Button(dialog, text="Update", command=commit).pack(pady=10)

    def cancel_edit(self):
        self.editing_index = None
        self.inv_name.delete(0, tk.END)
        self.inv_color.delete(0, tk.END)
        self.inv_weight.delete(0, tk.END); self.inv_weight.insert(0, "1000")
        self.inv_cost.delete(0, tk.END); self.inv_cost.insert(0, "20.00")
        self.tare_var.set(0)
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
            if self.inv_filter_var.get(): self.inv_filter_var.set("")
            idx = int(sel[0]) 
            name = self.inventory[idx]['name']
            mat = self.inventory[idx].get('material', '')
            webbrowser.open(f"https://www.google.com/search?q={name} {mat} filament price")

    # --- TAB 3: HISTORY & ANALYTICS ---
    def build_history_tab(self):
        frame = ttk.Frame(self.tab_history, padding=10)
        frame.pack(fill="both", expand=True)

        f_bar = ttk.LabelFrame(frame, text=" Filters ", padding=5)
        f_bar.pack(fill="x", pady=5)
        
        self.hist_month = tk.StringVar(value="All")
        self.hist_year = tk.StringVar(value="All")
        self.hist_type = tk.StringVar(value="All")
        
        months = ["All"] + [str(i).zfill(2) for i in range(1,13)]
        years = ["All", "2024", "2025", "2026", "2027"]
        
        ttk.Label(f_bar, text="Month:").pack(side="left")
        ttk.Combobox(f_bar, textvariable=self.hist_month, values=months, width=5, state="readonly").pack(side="left", padx=5)
        ttk.Label(f_bar, text="Year:").pack(side="left")
        ttk.Combobox(f_bar, textvariable=self.hist_year, values=years, width=6, state="readonly").pack(side="left", padx=5)
        ttk.Label(f_bar, text="Type:").pack(side="left")
        ttk.Combobox(f_bar, textvariable=self.hist_type, values=("All", "Sales", "Donations"), width=10, state="readonly").pack(side="left", padx=5)
        
        ttk.Button(f_bar, text="Apply Filters", command=self.refresh_history_list).pack(side="left", padx=10)

        cols = ("Date", "Job", "Cost", "Sold For", "Profit", "Type")
        self.hist_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols: self.hist_tree.heading(c, text=c)
        self.hist_tree.pack(side="top", fill="both", expand=True)
        
        db_frame = ttk.Frame(frame, relief="raised", borderwidth=1)
        db_frame.pack(side="bottom", fill="x", pady=10)
        
        self.lbl_sales = ttk.Label(db_frame, text="Sales: $0", font=("Arial", 11, "bold"), padding=10)
        self.lbl_sales.pack(side="left")
        self.lbl_profit = ttk.Label(db_frame, text="Profit: $0", font=("Arial", 11, "bold"), foreground="green", padding=10)
        self.lbl_profit.pack(side="left")
        self.lbl_donate = ttk.Label(db_frame, text="Donations: $0", font=("Arial", 11), foreground="blue", padding=10)
        self.lbl_donate.pack(side="right")
        
        ttk.Button(self.tab_history, text="Delete Record", command=self.del_history).pack(anchor="sw", padx=10)

    def refresh_history_list(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        
        total_sales = 0.0
        total_profit = 0.0
        total_donations = 0.0
        
        m_filter = self.hist_month.get()
        y_filter = self.hist_year.get()
        t_filter = self.hist_type.get()
        
        for idx, h in enumerate(reversed(self.history)):
            # NOTE: iterating reversed, so real index is len - 1 - idx
            try:
                h_date = datetime.strptime(h['date'], "%Y-%m-%d %H:%M")
                h_month = str(h_date.month).zfill(2)
                h_year = str(h_date.year)
            except: continue 
                
            if m_filter != "All" and m_filter != h_month: continue
            if y_filter != "All" and y_filter != h_year: continue
            
            is_don = h.get('is_donation', False)
            if t_filter == "Sales" and is_don: continue
            if t_filter == "Donations" and not is_don: continue
            
            cost = h.get('cost', 0)
            sold = h.get('sold_for', 0)
            profit = h.get('profit', sold - cost)
            
            if is_don:
                total_donations += cost 
                type_str = "DONATION"
            else:
                total_sales += sold
                total_profit += profit
                type_str = "Sale"
            
            # Using the loop index from reversed list for display, but we need real index for deletion
            # We can store real index in IID? 
            # Actually, easiest to just store unique ID or handle deletion carefully.
            # Here we just insert. Deletion logic handles index math.
            self.hist_tree.insert("", "end", values=(h['date'], h['job'], f"${cost:.2f}", f"${sold:.2f}", f"${profit:.2f}", type_str))
            
        self.lbl_sales.config(text=f"Revenue: ${total_sales:.2f}")
        self.lbl_profit.config(text=f"Net Profit: ${total_profit:.2f}")
        self.lbl_donate.config(text=f"Tax Write-offs: ${total_donations:.2f}")

    def del_history(self):
        sel = self.hist_tree.selection()
        if not sel: return
        
        if self.hist_month.get() != "All" or self.hist_type.get() != "All":
            messagebox.showerror("Error", "Reset filters to 'All' before deleting.")
            return
            
        # Get index (Remember tree is displayed normally, but list is reversed in memory or display?)
        # Wait, in refresh_history_list we iterate `reversed(self.history)`.
        # So top item in tree = last item in list.
        # Tree index 0 = List index (Len - 1)
        tree_index = self.hist_tree.index(sel[0])
        real_index = len(self.history) - 1 - tree_index
        
        record = self.history[real_index]
        
        # RESTORE LOGIC
        if "items" in record:
            if messagebox.askyesno("Restore Inventory?", "Do you want to add the filament back to inventory?"):
                restore_count = 0
                for item in record["items"]:
                    for spool in self.inventory:
                        if (spool['name'] == item['name'] and 
                            spool['color'] == item['color'] and 
                            spool.get('material') == item.get('material')):
                            spool['weight'] += item['grams']
                            restore_count += 1
                            break
                if restore_count > 0:
                    self.save_json(self.inventory, DB_FILE)
                    messagebox.showinfo("Restored", f"Restored stock for {restore_count} spools.")
                else:
                    messagebox.showwarning("Warning", "Could not find original spools.")

        if messagebox.askyesno("Confirm", "Delete this record permanently?"):
            del self.history[real_index]
            self.save_json(self.history, HISTORY_FILE)
            self.refresh_history_list()

    # --- TAB 4: SMART SEARCH & MANUAL ---
    def build_reference_tab(self):
        main_frame = ttk.Frame(self.tab_ref, padding=10)
        main_frame.pack(fill="both", expand=True)

        left_col = ttk.LabelFrame(main_frame, text=" Spool Estimator ", padding=10)
        left_col.pack(side="left", fill="both", expand=True, padx=5)
        try:
            spool_img = Image.open(IMAGE_FILE)
            spool_img.thumbnail((550, 750)) 
            self.ref_img_data = ImageTk.PhotoImage(spool_img)
            ttk.Label(left_col, image=self.ref_img_data).pack(anchor="center", pady=10)
        except: 
            ttk.Label(left_col, text="[spool_reference.png] missing").pack(pady=20)

        right_col = ttk.LabelFrame(main_frame, text=" Field Manual ", padding=10)
        right_col.pack(side="right", fill="both", expand=True, padx=5)

        search_frame = ttk.Frame(right_col)
        search_frame.pack(fill="x", pady=5)
        ttk.Label(search_frame, text="🔍 Search Issue (e.g. 'pop', 'stringing'):").pack(side="left", padx=5)
        self.entry_search = ttk.Entry(search_frame)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(search_frame, text="Search", command=self.perform_search).pack(side="left")
        self.entry_search.bind("<Return>", lambda e: self.perform_search())

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

    # --- TAB 5: MAINTENANCE TRACKER ---
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