# 3D Print Shop Manager 🚀 (v4.0)

**The ultimate "All-in-One" tool for 3D printing hobbyists, small businesses, and beginners.**

Stop guessing your prices. Stop failing prints. Stop losing track of your inventory.

This application is a lightweight, single-file solution that combines a **Business Manager** (Inventory, Quoting, Receipts) with a complete **3D Printing Field Manual** (Troubleshooting, Material Guides, Hardware Maintenance).

---

## ✨ New in v4.0: The "Field Manual" Update

### 🧠 Smart Search & Diagnostics
* **Fuzzy Logic Search:** Type "pop", "click", or "stringing" and the app instantly finds the relevant guide, even if you make a typo.
* **Multi-Hit Detection:** If your search term appears in multiple guides (e.g., "Clog"), the app jumps to the best match but notifies you of other relevant sections.

### 📚 The Expert Knowledge Base
* **First Layer "Holy Grail":** A dedicated guide to mastering Z-Offset vs. Leveling.
* **Material Database:** Deep dives on PLA, PETG, TPU, ABS/ASA, and Silk PLA (Temps, Fan Speeds, Enclosure rules).
* **Bambu Lab Profiles:** Specific tips for X1/P1/A1 users (Grid Infill warnings, AMS compatibility).
* **Hardware Maintenance:** Monthly checklists for Eccentric Nuts, Belts, and Z-Rods.

---

## 🛠️ Key Features

### 💰 Professional Quoting Engine
* **Smart Calculator:** Input material cost, print time, and markup to get a sell price instantly.
* **Overhead Calculation:** Automatically accounts for electricity, machine wear, and waste.
* **Pro Receipts:** Generates beautiful text-file invoices saved to `Documents/3D_Print_Receipts`.
> <img width="518" height="546" alt="Screenshot 2025-12-10 122953" src="https://github.com/user-attachments/assets/dcf40c66-e8eb-4003-b442-a0eaf8cde898" />


### 📦 Intelligent Inventory System
* **Live Tracking:** Subtract grams from spools as you print.
* **Visual Alerts:** 🟡 Yellow (Low Stock) and 🔴 Red (Critical) indicators.
* **Price Check:** One-click Google Shopping search for selected filaments.

---

## 🚀 How to Install & Use

### Option 1: The Easy Way (.exe)
1.  Download `PrintShopManager.exe` from the **Releases** page.
2.  Double-click to run. (No installation required).

### Option 2: Run from Source (Python)
1.  Clone this repository.
2.  Install the required image library:
    ```bash
    pip install Pillow
    ```
3.  Run the script:
    ```bash
    python print_manager.py
    ```

---

## 🏗️ How to Build the EXE (For Developers)
If you want to modify the code and build your own executable, use this command to ensure the Images and Pillow library are bundled correctly:

```bash
pyinstaller --noconsole --onefile --name="PrintShopManager" --add-data "*.png;." print_manager.py
