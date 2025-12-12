# 3D Print Shop Manager 🚀 (v7.0)

**The ultimate "All-in-One" ERP tool for 3D printing hobbyists and small businesses.**

Stop guessing your prices. Stop failing prints. Stop losing track of your inventory.

This application is a lightweight, single-file solution that combines a **Business Manager** (Inventory, Quoting, Receipts) with a complete **3D Printing Field Manual** (Maintenance Tracking, Troubleshooting, Material Guides).

---

## ✨ New in v7.0: The "Modern UI" Update
* **Fresh Look:** Rebuilt the interface with a clean, flat, modern design (`ttkbootstrap`).
* **Dark Mode:** One-click toggle between **Light** (Flatly) and **Dark** (Darkly) themes.
* **Visual Clarity:** Color-coded buttons (Success/Danger/Info) and zebra-striped tables make data easier to read.

---

## 🛠️ Key Features

### 📦 Inventory & Workflow
* **Auto-Tare:** Automatically subtracts empty spool weight (Plastic/Cardboard).
* **Job Queue:** Save jobs to a "Pending" list and finalize them when printed.
* **Bulk Edit:** Select 50 spools at once to update materials or brands instantly.

### 💰 Business Analytics
* **Smart Calculator:** Handles overhead, labor, filament swaps (waste), and discounts.
* **Profit Dashboard:** Track Revenue, Net Profit, and Tax Write-offs in real-time.
* **Pro Receipts:** Generate detailed invoices with line-item breakdowns.

<img width="518" height="546" alt="Screenshot 2025-12-10 122953" src="https://github.com/user-attachments/assets/dcf40c66-e8eb-4003-b442-a0eaf8cde898" />

### 📚 Maintenance & Knowledge
* **Field Manual:** Integrated guide with Smart Search (e.g., type "pop" to find wet filament fixes).
* **Maintenance Log:** Track deadlines for greasing Z-rods, tightening belts, and cleaning beds.
* **Disaster Recovery:** Full "Backup & Restore" feature to save your entire business data to a single .zip file.

---

## 🚀 How to Install & Use

### Option 1: The Easy Way (.exe)
1.  Download `PrintShopManager.exe` from the **Releases** page.
2.  Double-click to run. (No installation required).

### Option 2: Run from Source (Python)
1.  Clone this repository.
2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the script:
    ```bash
    python print_manager.py
    ```

---

## 🏗️ Building the EXE
If you are a developer compiling this yourself, you must use `--collect-all` for the UI library:

```bash
pyinstaller --noconsole --onefile --name="PrintShopManager" --collect-all ttkbootstrap --add-data "spool_reference.png;." print_manager.py
