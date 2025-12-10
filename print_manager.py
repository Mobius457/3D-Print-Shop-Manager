import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
import shutil
import subprocess
import webbrowser
from datetime import datetime

# ======================================================
# PATH SETUP
# ======================================================

APP_NAME = "PrintShopManager"

if os.name == 'nt':
    DATA_DIR = os.path.join(os.environ['LOCALAPPDATA'], APP_NAME)
else:
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "filament_inventory.json")
HISTORY_FILE = os.path.join(DATA_DIR, "sales_history.json")

def get_receipts_folder():
    user_home = os.path.expanduser("~")
    candidates = [
        os.path.join(user_home, "Documents", "3D_Print_Receipts"),
        os.path.join(user_home, "OneDrive", "Documents", "3D_Print_Receipts"),
        os.path.join(user_home, "Desktop", "3D_Print_Receipts"),
        os.path.join(DATA_DIR, "Receipts")
    ]
    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except OSError:
            continue
    return os.getcwd()

DOCS_DIR = get_receipts_folder()

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

IMAGE_FILE = resource_path("spool_reference.png")

# ======================================================

class FilamentManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("3D Print Shop Manager (v8.0)")
        # Start slightly larger to accommodate font size
        self.root.geometry("900x900")

        self.inventory = self.load_json(DB_FILE)
        self.history = self.load_json(HISTORY_FILE)
        self.current_job_filaments = []
        self.last_calculated_price = 0.0
        self.last_calculated_cost = 0.0
        self.editing_index = None

        # --- UI POLISH: FONTS & STYLES ---
        # Set a global font for all widgets
        self.main_font = ("Segoe UI", 12) # "Segoe UI" is standard for modern Windows
        self.bold_font = ("Segoe UI", 12, "bold")
        
        style = ttk.Style()
        style.theme_use('clam') # 'clam' usually looks cleaner than default on Windows
        
        # Apply font to everything
        style.configure(".", font=self.main_font)
        style.configure("Treeview", font=self.main_font, rowheight=30) # Taller rows for list
        style.configure("Treeview.Heading", font=self.bold_font)
        style.configure("TLabelframe.Label", font=self.bold_font) # Bold Frame Titles

        # Treeview Colors
        style.map("Treeview", foreground=[('selected', 'black')], background=[('selected', '#3498db')])
        # ---------------------------------

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both")

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

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

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
        self.cancel_edit()

    def backup_data(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"Inventory_Backup_{datetime.now().strftime('%Y%m%d')}.json")
        if save_path:
            shutil.copy(DB_FILE, save_path)
            messagebox.showinfo("Backup", f"Saved to:\n{save_path}")

    # --- TAB 1: CALCULATOR (RE-DESIGNED) ---
    def build_calculator_tab(self):
        # Main container with less padding
        frame = ttk.Frame(self.tab_calc, padding=10)
        frame.pack(fill="both", expand=True)

        # 1. Job Name (Stays at top, doesn't expand)
        name_frame = ttk.LabelFrame(frame, text=" Job Details ", padding=10)
        name_frame.pack(fill="x", pady=5)
        ttk.Label(name_frame, text="Job Name:").pack(side="left", padx=5)
        self.entry_job_name = ttk.Entry(name_frame, width=30)
        self.entry_job_name.pack(side="left", padx=5, fill="x", expand=True)

        # 2. Filament Input (Stays at top)
        sel_frame = ttk.LabelFrame(frame, text=" Add Filament ", padding=10)
        sel_frame.pack(fill="x", pady=5)
        
        # Grid layout for inputs to align them nicely
        sel_frame.columnconfigure(1, weight=1) # Make combo box expandable
        
        ttk.Label(sel_frame, text="Spool:").grid(row=0, column=0, padx=5, sticky="e")
        self.combo_filaments = ttk.Combobox(sel_frame, state="readonly")
        self.combo_filaments.grid(row=0, column=1, padx=5, sticky="ew")
        
        ttk.Label(sel_frame, text="Grams:").grid(row=0, column=2, padx=5, sticky="e")
        self.entry_calc_grams = ttk.Entry(sel_frame, width=8)
        self.entry_calc_grams.grid(row=0, column=3, padx=5)
        
        ttk.Button(sel_frame, text="Add Color", command=self.add_to_job).grid(row=0, column=4, padx=10)

        # 3. The Job List (THIS IS THE ELASTIC PART)
        # We put this in a frame that expands to fill all available space
        list_container = ttk.Frame(frame)
        list_container.pack(fill="both", expand=True, pady=5)
        
        # Scrollbar for the list
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")
        
        self.list_job = tk.Listbox(list_container, font=self.main_font, height=6, yscrollcommand=scrollbar.set)
        self.list_job.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.list_job.yview)
        
        ttk.Button(list_container, text="Clear List", command=self.clear_job).pack(anchor="ne")

        # 4. Settings (Stays at bottom)
        set_frame = ttk.LabelFrame(frame, text=" Settings ", padding=10)
        set_frame.pack(fill="x", pady=5)
        
        ttk.Label(set_frame, text="Hrs:").pack(side="left", padx=5)
        self.entry_hours = ttk.Entry(set_frame, width=6); self.entry_hours.pack(side="left", padx=5)
        
        ttk.Label(set_frame, text="Waste %:").pack(side="left", padx=5)
        self.entry_waste = ttk.Entry(set_frame, width=6); self.entry_waste.insert(0, "20"); self.entry_waste.pack(side="left", padx=5)
        
        ttk.Label(set_frame, text="Markup:").pack(side="left", padx=5)
        self.entry_markup = ttk.Entry(set_frame, width=6); self.entry_markup.insert(0, "2.0"); self.entry_markup.pack(side="left", padx=5)

        # 5. Actions & Results (Stays at bottom)
        btn_frame = ttk.Frame(frame, padding=10)
        btn_frame.pack(fill="x", pady=5)
        
        self.btn_calc = ttk.Button(btn_frame, text="CALCULATE", command=self.calculate_quote)
        self.btn_calc.pack(side="left", padx=5, fill="x", expand=True)
        
        self.btn_receipt = ttk.Button(btn_frame, text="💾 Receipt", command=self.generate_receipt, state="disabled")
        self.btn_receipt.pack(side="left", padx=5, fill="x", expand=True)
        
        ttk.Button(btn_frame, text="📂 Folder", command=self.open_receipt_folder).pack(side="left", padx=5)

        self.result_var = tk.StringVar()
        self.lbl_result = ttk.Label(frame, textvariable=self.result_var, font=("Courier", 12, "bold"), justify="left", background="#f0f0f0", relief="sunken")
        self.lbl_result.pack(pady=5, fill="x")

        self.btn_deduct = ttk.Button(frame, text="✅ Print Done (Update Stock)", command=self.deduct_inventory, state="disabled")
        self.btn_deduct.pack(pady=5, fill="x")

    def update_filament_dropdown(self):
        options = []
        for f in self.inventory: options.append(f"{f['name']} ({f['color']}) - [{int(f['weight'])}g left]")
        self.combo_filaments['values'] = options

    def add_to_job(self):
        index = self.combo_filaments.current()
        if index == -1: return
        try:
            selected_spool = self.inventory[index]
            grams = float(self.entry_calc_grams.get())
            cost = (selected_spool['cost'] / 1000) * grams
            self.current_job_filaments.append({"spool": selected_spool, "grams": grams, "cost": cost})
            self.list_job.insert(tk.END, f"{selected_spool['name']} ({selected_spool['color']}): {grams}g (${cost:.2f})")
            self.entry_calc_grams.delete(0, tk.END)
        except ValueError: messagebox.showerror("Error", "Enter valid grams.")

    def clear_job(self):
        self.current_job_filaments = []
        self.list_job.delete(0, tk.END)
        self.btn_deduct.config(state="disabled")
        self.btn_receipt.config(state="disabled")
        self.result_var.set("")
        self.entry_job_name.delete(0, tk.END)

    def calculate_quote(self):
        if not self.current_job_filaments: return
        try:
            hours = float(self.entry_hours.get())
            waste = float(self.entry_waste.get()) / 100
            markup = float(self.entry_markup.get())
            raw_mat = sum(i['cost'] for i in self.current_job_filaments)
            mat_buf = raw_mat * (1 + waste)
            machine = hours * 0.75
            self.last_calculated_cost = mat_buf + machine
            self.last_calculated_price = round(self.last_calculated_cost * markup)
            res = f" Materials: ${mat_buf:.2f}  |  Machine: ${machine:.2f}\n Total Cost: ${self.last_calculated_cost:.2f}\n --------------------------------------\n SELL PRICE: ${self.last_calculated_price:.2f}"
            self.result_var.set(res)
            self.btn_deduct.config(state="normal")
            self.btn_receipt.config(state="normal")
        except ValueError: pass

    def generate_receipt(self):
        job = self.entry_job_name.get() or "Custom_Print"
        clean = "".join([c for c in job if c.isalnum() or c in (' ', '-', '_')]).strip()
        date = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(DOCS_DIR, f"{date}_{clean}.txt")
        try:
            with open(path, "w") as f:
                f.write(f"INVOICE\nDate: {date}\nItem: {job}\n\nBreakdown:\n")
                for item in self.current_job_filaments: f.write(f" - {item['spool']['name']} ({item['spool']['color']}): {item['grams']}g\n")
                f.write(f"\nTotal: ${self.last_calculated_price:.2f}")
            messagebox.showinfo("Saved", f"Receipt Saved!\n\nLocation:\n{path}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def open_receipt_folder(self):
        try: os.startfile(DOCS_DIR)
        except Exception: messagebox.showerror("Error", f"Could not open folder:\n{DOCS_DIR}")

    def deduct_inventory(self):
        if messagebox.askyesno("Confirm", "Finalize sale?"):
            for job_item in self.current_job_filaments:
                job_item['spool']['weight'] -= job_item['grams']
            self.save_json(self.inventory, DB_FILE)
            self.history.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "job": self.entry_job_name.get(), "cost": self.last_calculated_cost, "sold_for": self.last_calculated_price})
            self.save_json(self.history, HISTORY_FILE)
            self.update_filament_dropdown()
            messagebox.showinfo("Success", "Updated!")
            self.clear_job()

    # --- TAB 2: INVENTORY (ELASTIC) ---
    def build_inventory_tab(self):
        frame = ttk.Frame(self.tab_inventory, padding=10)
        frame.pack(fill="both", expand=True)

        # Input Frame (Static at top)
        self.input_frame = ttk.LabelFrame(frame, text=" Add New Spool ", padding=10)
        self.input_frame.pack(fill="x", pady=5)
        
        # Using grid for better alignment
        ttk.Label(self.input_frame, text="Name:").grid(row=0, column=0, padx=5, sticky="e")
        self.inv_name = ttk.Entry(self.input_frame, width=15); self.inv_name.grid(row=0, column=1, padx=5, sticky="ew")
        
        ttk.Label(self.input_frame, text="Color:").grid(row=0, column=2, padx=5, sticky="e")
        self.inv_color = ttk.Entry(self.input_frame, width=10); self.inv_color.grid(row=0, column=3, padx=5, sticky="ew")
        
        ttk.Label(self.input_frame, text="Weight:").grid(row=0, column=4, padx=5, sticky="e")
        self.inv_weight = ttk.Entry(self.input_frame, width=8); self.inv_weight.insert(0,"1000"); self.inv_weight.grid(row=0, column=5, padx=5, sticky="ew")
        
        ttk.Label(self.input_frame, text="Cost ($):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.inv_cost = ttk.Entry(self.input_frame, width=8); self.inv_cost.insert(0,"20.00"); self.inv_cost.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        self.btn_search = ttk.Button(self.input_frame, text="🔍 Price", command=self.check_online_price)
        self.btn_search.grid(row=1, column=2, padx=5, sticky="w")

        self.btn_save_inv = ttk.Button(self.input_frame, text="Save to Stock", command=self.save_inventory_item)
        self.btn_save_inv.grid(row=1, column=4, columnspan=2, padx=10, sticky="ew")

        self.btn_cancel_edit = ttk.Button(self.input_frame, text="Cancel", command=self.cancel_edit)

        # List Frame (Elastic - Fills space)
        list_frame = ttk.LabelFrame(frame, text=" Stock ", padding=10)
        list_frame.pack(fill="both", expand=True, pady=10)
        
        cols = ("Name", "Color", "Rem(g)", "Cost")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=10)
        for c in cols: self.tree.heading(c, text=c); self.tree.column(c, width=100)
        self.tree.tag_configure('low', background='#fff3cd'); self.tree.tag_configure('crit', background='#f8d7da')
        
        # Scrollbar for tree
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        btn_box = ttk.Frame(frame); btn_box.pack(pady=5, fill="x")
        ttk.Button(btn_box, text="✏️ Edit", command=self.edit_inventory_item).pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(btn_box, text="🗑️ Delete", command=self.delete_inventory_item).pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(btn_box, text="💾 Backup", command=self.backup_data).pack(side="left", padx=5, expand=True, fill="x")

    def check_online_price(self):
        name = self.inv_name.get()
        if not name: messagebox.showwarning("Empty Name", "Type a Brand or Filament Name first!"); return
        webbrowser.open(f"https://www.google.com/search?q={name} filament price&tbm=shop")

    def edit_inventory_item(self):
        sel = self.tree.selection()
        if not sel: return
        index = self.tree.index(sel[0])
        item = self.inventory[index]
        self.inv_name.delete(0, tk.END); self.inv_name.insert(0, item['name'])
        self.inv_color.delete(0, tk.END); self.inv_color.insert(0, item['color'])
        self.inv_weight.delete(0, tk.END); self.inv_weight.insert(0, str(item['weight']))
        self.inv_cost.delete(0, tk.END); self.inv_cost.insert(0, str(item['cost']))
        self.editing_index = index
        self.input_frame.config(text=f" Editing: {item['name']} ")
        self.btn_save_inv.config(text="Update Item")
        self.btn_cancel_edit.grid(row=1, column=6, padx=5)

    def cancel_edit(self):
        self.editing_index = None
        self.input_frame.config(text=" Add New Spool ")
        self.btn_save_inv.config(text="Save to Stock")
        self.btn_cancel_edit.grid_forget()
        self.inv_name.delete(0, tk.END)
        self.inv_color.delete(0, tk.END)
        self.inv_weight.delete(0, tk.END); self.inv_weight.insert(0, "1000")
        self.inv_cost.delete(0, tk.END); self.inv_cost.insert(0, "20.00")

    def save_inventory_item(self):
        try:
            new_item = {"name": self.inv_name.get(), "color": self.inv_color.get(), "cost": float(self.inv_cost.get()), "weight": float(self.inv_weight.get())}
            if self.editing_index is not None:
                self.inventory[self.editing_index] = new_item
                self.cancel_edit()
            else:
                self.inventory.append(new_item)
                self.inv_name.delete(0, tk.END)
            self.save_json(self.inventory, DB_FILE)
            self.refresh_inventory_list()
        except ValueError: messagebox.showerror("Error", "Check numbers.")

    def refresh_inventory_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for item in self.inventory:
            w = item['weight']
            tag = 'crit' if w < 50 else ('low' if w < 200 else '')
            self.tree.insert("", "end", values=(item["name"], item["color"], w, item["cost"]), tags=(tag,))

    def delete_inventory_item(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            del self.inventory[idx]
            self.save_json(self.inventory, DB_FILE)
            self.refresh_inventory_list()
            self.cancel_edit()

    # --- TAB 3: HISTORY (ELASTIC) ---
    def build_history_tab(self):
        frame = ttk.Frame(self.tab_history, padding=10)
        frame.pack(fill="both", expand=True)
        
        cols = ("Date", "Job", "Cost", "Sold", "Profit")
        self.hist_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols: self.hist_tree.heading(c, text=c); self.hist_tree.column(c, width=100)
        
        # Scrollbar
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=vsb.set)
        
        self.hist_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        # Buttons at bottom
        btn_frame = ttk.Frame(self.tab_history, padding=5); btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_history_list).pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(btn_frame, text="Delete Record", command=self.delete_history_item).pack(side="left", padx=5, expand=True, fill="x")

    def refresh_history_list(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        total_p = 0.0
        for h in reversed(self.history):
            p = h.get('sold_for',0) - h.get('cost',0)
            total_p += p
            self.hist_tree.insert("", "end", values=(h['date'], h['job'], f"${h.get('cost',0):.2f}", f"${h.get('sold_for',0):.2f}", f"${p:.2f}"))
        self.tab_history.master.tab(self.tab_history, text=f" 📜 History (Profit: ${total_p:.2f}) ")

    def delete_history_item(self):
        sel = self.hist_tree.selection()
        if sel and messagebox.askyesno("Confirm", "Delete record?"):
            idx = len(self.history) - 1 - self.hist_tree.index(sel[0])
            del self.history[idx]
            self.save_json(self.history, HISTORY_FILE)
            self.refresh_history_list()

    def build_reference_tab(self):
        frame = ttk.Frame(self.tab_ref, padding=20); frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Spool Reference Chart", font=("Arial", 16, "bold")).pack(pady=10)
        try:
            self.ref_img_data = tk.PhotoImage(file=IMAGE_FILE)
            ttk.Label(frame, image=self.ref_img_data).pack()
        except: ttk.Label(frame, text="Image not found").pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = FilamentManagerApp(root)
    root.mainloop()