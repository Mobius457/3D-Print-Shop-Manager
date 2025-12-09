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

# 1. DATABASE (Hidden in AppData)
if os.name == 'nt':
    DATA_DIR = os.path.join(os.environ['LOCALAPPDATA'], APP_NAME)
else:
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "filament_inventory.json")
HISTORY_FILE = os.path.join(DATA_DIR, "sales_history.json")

# 2. ROBUST RECEIPTS FOLDER (V6.3 FIX)
def get_receipts_folder():
    """
    Bulletproof folder creation.
    It actually ATTEMPTS to make the folder. If it fails, it moves to the next option.
    """
    user_home = os.path.expanduser("~")
    
    # List of places we WANT to save receipts, in order of preference
    candidates = [
        os.path.join(user_home, "Documents", "3D_Print_Receipts"),
        os.path.join(user_home, "OneDrive", "Documents", "3D_Print_Receipts"),
        os.path.join(user_home, "Desktop", "3D_Print_Receipts"), # Fallback 1: Desktop
        os.path.join(DATA_DIR, "Receipts")                        # Fallback 2: Hidden AppData
    ]

    for path in candidates:
        try:
            # Try to create the directory
            os.makedirs(path, exist_ok=True)
            # If we reach this line, it worked! Return this path.
            return path
        except OSError:
            # If Windows gives Error 2 or 3, just ignore and try the next one
            continue
    
    # If all else fails, use the current folder
    return os.getcwd()

DOCS_DIR = get_receipts_folder()

# 3. IMAGE RESOURCE
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

IMAGE_FILE = resource_path("spool_reference.png")

# ======================================================

class FilamentManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("3D Print Shop Manager (v6.3)")
        self.root.geometry("780x880")

        self.inventory = self.load_json(DB_FILE)
        self.history = self.load_json(HISTORY_FILE)
        self.current_job_filaments = []
        self.last_calculated_price = 0.0
        self.last_calculated_cost = 0.0

        style = ttk.Style()
        style.map("Treeview", foreground=[('selected', 'black')], background=[('selected', '#3498db')])

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
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except:
            return []

    def save_json(self, data, filepath):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    def on_tab_change(self, event):
        self.update_filament_dropdown()
        self.refresh_inventory_list()
        self.refresh_history_list()

    def backup_data(self):
        save_path = filedialog.asksaveasfilename(
            defaultextension=".json", 
            filetypes=[("JSON", "*.json")], 
            initialfile=f"Inventory_Backup_{datetime.now().strftime('%Y%m%d')}.json"
        )
        if save_path:
            shutil.copy(DB_FILE, save_path)
            messagebox.showinfo("Backup", f"Saved to:\n{save_path}")

    # --- TAB 1: CALCULATOR ---
    def build_calculator_tab(self):
        frame = ttk.Frame(self.tab_calc, padding=20)
        frame.pack(fill="both", expand=True)

        name_frame = ttk.LabelFrame(frame, text=" Job Details ", padding=10)
        name_frame.pack(fill="x", pady=5)
        ttk.Label(name_frame, text="Job Name:").grid(row=0, column=0, padx=5)
        self.entry_job_name = ttk.Entry(name_frame, width=30)
        self.entry_job_name.grid(row=0, column=1, padx=5)

        sel_frame = ttk.LabelFrame(frame, text=" 1. Select Filament ", padding=10)
        sel_frame.pack(fill="x", pady=5)
        ttk.Label(sel_frame, text="Spool:").grid(row=0, column=0, padx=5)
        self.combo_filaments = ttk.Combobox(sel_frame, state="readonly", width=30)
        self.combo_filaments.grid(row=0, column=1, padx=5)
        ttk.Label(sel_frame, text="Grams:").grid(row=0, column=2, padx=5)
        self.entry_calc_grams = ttk.Entry(sel_frame, width=8)
        self.entry_calc_grams.grid(row=0, column=3, padx=5)
        ttk.Button(sel_frame, text="Add Color", command=self.add_to_job).grid(row=0, column=4, padx=10)

        self.list_job = tk.Listbox(sel_frame, height=4)
        self.list_job.grid(row=1, column=0, columnspan=5, sticky="ew", pady=10)
        ttk.Button(sel_frame, text="Clear Job", command=self.clear_job).grid(row=2, column=4, sticky="e")

        set_frame = ttk.LabelFrame(frame, text=" 2. Settings ", padding=10)
        set_frame.pack(fill="x", pady=5)
        ttk.Label(set_frame, text="Hrs:").grid(row=0, column=0, padx=5)
        self.entry_hours = ttk.Entry(set_frame, width=8)
        self.entry_hours.grid(row=0, column=1, padx=5)
        ttk.Label(set_frame, text="Waste %:").grid(row=0, column=2, padx=5)
        self.entry_waste = ttk.Entry(set_frame, width=5)
        self.entry_waste.insert(0, "20")
        self.entry_waste.grid(row=0, column=3, padx=5)
        ttk.Label(set_frame, text="Markup:").grid(row=0, column=4, padx=5)
        self.entry_markup = ttk.Entry(set_frame, width=5)
        self.entry_markup.insert(0, "2.0")
        self.entry_markup.grid(row=0, column=5, padx=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        self.btn_calc = ttk.Button(btn_frame, text="CALCULATE", command=self.calculate_quote)
        self.btn_calc.pack(side="left", padx=5)
        self.btn_receipt = ttk.Button(btn_frame, text="💾 Save Receipt", command=self.generate_receipt, state="disabled")
        self.btn_receipt.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📂 Open Folder", command=self.open_receipt_folder).pack(side="left", padx=5)

        self.result_var = tk.StringVar()
        self.lbl_result = ttk.Label(frame, textvariable=self.result_var, font=("Courier", 10), justify="left")
        self.lbl_result.pack(pady=5, fill="both", expand=True)

        self.btn_deduct = ttk.Button(frame, text="✅ Print Done (Update Stock)", command=self.deduct_inventory, state="disabled")
        self.btn_deduct.pack(pady=5)

    def update_filament_dropdown(self):
        options = []
        for f in self.inventory:
            options.append(f"{f['name']} ({f['color']}) - [{int(f['weight'])}g left]")
        self.combo_filaments['values'] = options

    def add_to_job(self):
        selection = self.combo_filaments.get()
        if not selection: return
        try:
            name_part = selection.split(" (")[0]
            selected_spool = next((item for item in self.inventory if item["name"] == name_part), None)
            grams = float(self.entry_calc_grams.get())
            if selected_spool:
                cost = (selected_spool['cost'] / 1000) * grams
                self.current_job_filaments.append({"spool": selected_spool, "grams": grams, "cost": cost})
                self.list_job.insert(tk.END, f"{selected_spool['name']}: {grams}g (${cost:.2f})")
                self.entry_calc_grams.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Enter valid grams.")

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
            res = f"Materials: ${mat_buf:.2f}\nMachine:   ${machine:.2f}\nTotal Cost: ${self.last_calculated_cost:.2f}\n------------------\nSELL PRICE: ${self.last_calculated_price:.2f}"
            self.result_var.set(res)
            self.btn_deduct.config(state="normal")
            self.btn_receipt.config(state="normal")
        except ValueError:
            pass

    def generate_receipt(self):
        job = self.entry_job_name.get() or "Custom_Print"
        clean_job_name = "".join([c for c in job if c.isalnum() or c in (' ', '-', '_')]).strip()
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{clean_job_name}.txt"
        file_path = os.path.join(DOCS_DIR, filename)

        try:
            with open(file_path, "w") as f:
                f.write(f"INVOICE\nDate: {date_str}\nItem: {job}\n\nBreakdown:\n")
                for item in self.current_job_filaments:
                    f.write(f" - {item['spool']['name']}: {item['grams']}g\n")
                f.write(f"\nTotal: ${self.last_calculated_price:.2f}")
            messagebox.showinfo("Saved", f"Receipt Saved!\n\nLocation:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_receipt_folder(self):
        try:
            os.startfile(DOCS_DIR)
        except Exception:
            messagebox.showerror("Error", f"Could not open folder:\n{DOCS_DIR}")

    def deduct_inventory(self):
        if messagebox.askyesno("Confirm", "Finalize sale?"):
            for job_item in self.current_job_filaments:
                spool_ref = next((s for s in self.inventory if s['name'] == job_item['spool']['name']), None)
                if spool_ref:
                    spool_ref['weight'] -= job_item['grams']
            self.save_json(self.inventory, DB_FILE)
            self.history.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "job": self.entry_job_name.get(), "cost": self.last_calculated_cost, "sold_for": self.last_calculated_price})
            self.save_json(self.history, HISTORY_FILE)
            self.update_filament_dropdown()
            messagebox.showinfo("Success", "Updated!")
            self.clear_job()

    # --- TAB 2: INVENTORY ---
    def build_inventory_tab(self):
        frame = ttk.Frame(self.tab_inventory, padding=20)
        frame.pack(fill="both", expand=True)

        input_frame = ttk.LabelFrame(frame, text=" Add New ", padding=10)
        input_frame.pack(fill="x", pady=5)
        
        # Row 1
        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, padx=5)
        self.inv_name = ttk.Entry(input_frame, width=15)
        self.inv_name.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Color:").grid(row=0, column=2, padx=5)
        self.inv_color = ttk.Entry(input_frame, width=10)
        self.inv_color.grid(row=0, column=3, padx=5)

        ttk.Label(input_frame, text="Weight:").grid(row=0, column=4, padx=5)
        self.inv_weight = ttk.Entry(input_frame, width=8)
        self.inv_weight.insert(0,"1000")
        self.inv_weight.grid(row=0, column=5, padx=5)

        # Row 2 (Cost and Search)
        ttk.Label(input_frame, text="Cost ($):").grid(row=1, column=0, padx=5, pady=5)
        self.inv_cost = ttk.Entry(input_frame, width=8)
        self.inv_cost.insert(0,"20.00")
        self.inv_cost.grid(row=1, column=1, padx=5, pady=5)

        self.btn_search = ttk.Button(input_frame, text="🔍 Check Price Online", command=self.check_online_price)
        self.btn_search.grid(row=1, column=2, columnspan=2, padx=5)

        ttk.Button(input_frame, text="Save to Stock", command=self.add_to_inventory).grid(row=1, column=4, columnspan=2, padx=10)

        # List
        list_frame = ttk.LabelFrame(frame, text=" Stock ", padding=10)
        list_frame.pack(fill="both", expand=True, pady=10)
        cols = ("Name", "Color", "Rem(g)", "Cost")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=15)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100)
        self.tree.tag_configure('low', background='#fff3cd')
        self.tree.tag_configure('crit', background='#f8d7da')
        self.tree.pack(fill="both", expand=True)
        
        btn_box = ttk.Frame(list_frame)
        btn_box.pack(pady=5)
        ttk.Button(btn_box, text="Delete Selected", command=self.delete_inventory_item).pack(side="left", padx=5)
        ttk.Button(btn_box, text="💾 Backup Inventory", command=self.backup_data).pack(side="left", padx=5)

    def check_online_price(self):
        name = self.inv_name.get()
        if not name:
            messagebox.showwarning("Empty Name", "Type a Brand or Filament Name first!")
            return
        query = f"{name} filament price"
        url = f"https://www.google.com/search?q={query}&tbm=shop"
        webbrowser.open(url)

    def add_to_inventory(self):
        try:
            self.inventory.append({"name": self.inv_name.get(), "color": self.inv_color.get(), "cost": float(self.inv_cost.get()), "weight": float(self.inv_weight.get())})
            self.save_json(self.inventory, DB_FILE)
            self.refresh_inventory_list()
            self.inv_name.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Check numbers.")

    def refresh_inventory_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for item in self.inventory:
            w = item['weight']
            tag = 'crit' if w < 50 else ('low' if w < 200 else '')
            self.tree.insert("", "end", values=(item["name"], item["color"], w, item["cost"]), tags=(tag,))

    def delete_inventory_item(self):
        sel = self.tree.selection()
        if sel:
            val = self.tree.item(sel[0])['values']
            self.inventory = [i for i in self.inventory if i['name'] != val[0]]
            self.save_json(self.inventory, DB_FILE)
            self.refresh_inventory_list()

    def build_history_tab(self):
        frame = ttk.Frame(self.tab_history, padding=20)
        frame.pack(fill="both", expand=True)
        cols = ("Date", "Job", "Cost", "Sold", "Profit")
        self.hist_tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for c in cols:
            self.hist_tree.heading(c, text=c)
            self.hist_tree.column(c, width=100)
        self.hist_tree.pack(fill="both", expand=True)
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_history_list).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Delete Record", command=self.delete_history_item).pack(side="left", padx=10)

    def refresh_history_list(self):
        for i in self.hist_tree.get_children():
            self.hist_tree.delete(i)
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
        frame = ttk.Frame(self.tab_ref, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Spool Reference Chart", font=("Arial", 14)).pack(pady=10)
        try:
            self.ref_img_data = tk.PhotoImage(file=IMAGE_FILE)
            ttk.Label(frame, image=self.ref_img_data).pack()
        except:
            ttk.Label(frame, text="Image not found").pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = FilamentManagerApp(root)
    root.mainloop()