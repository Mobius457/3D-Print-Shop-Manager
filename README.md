# 3D Print Shop Manager 🚀 (v14.3)

**The "Central Nervous System" for your 3D Printing Business.**

PrintShopManager is a desktop ERP (Enterprise Resource Planning) application designed specifically for micro-manufacturing, print farms, and side-hustles. It bridges the gap between basic spreadsheets and expensive, complex industrial software.

### 🎯 Why use this?
* **Stop guessing prices:** Know exactly what a print costs you in electricity, material, and labor.
* **Stop running out of filament:** Track every gram. The app warns you *before* you start a print if a spool is too low.
* **Stop losing data:** Automated daily backups ensure your business history is safe.

---

## 🏁 Getting Started Guide (Zero to Hero)

Follow these 4 steps to get your shop running in under 5 minutes.

### Step 1: Initial Setup 📂
When you first run `PrintShopManager.exe`:
1.  Navigate to the **🏠 Dashboard** tab.
2.  Look at the "System Actions" panel.
3.  Click **📂 Set Data Folder**.
4.  **Crucial Step:** Select a folder in your Cloud Storage (OneDrive, Dropbox, or Google Drive).
    * *Why?* This ensures your inventory lives in the cloud. You can access it from your workshop PC and your office laptop simultaneously.

### Step 2: Add Your First Spool 📦
You can't quote a job without plastic!
1.  Go to the **📦 Inventory** tab.
2.  **Brand/Name:** Enter "Polymaker PLA" or similar.
3.  **Material:** Select "PLA" (or your specific type).
4.  **Weight:** Enter the *net* weight (usually `1000`g).
    * *Tip:* Use the "Tare" radio buttons if you are weighing a partially used spool.
5.  **Cost:** Enter what you paid (e.g., `21.99`).
6.  **Color:** Type a color (e.g., "Red"). The app will auto-generate a color dot for visual scanning.
7.  Click **Add Spool**.

### Step 3: Calculate a Price 🖩
A customer wants a "Flexi-Rex". Let's quote it.
1.  Go to the **🖩 Calculator** tab.
2.  **Select Spool:** Pick the "Polymaker PLA" you just added.
3.  **Grams:** Enter the estimate from your slicer (e.g., `45`g). Click **Add**.
4.  **Labor & Overhead:**
    * *Print Time:* Enter `3.5` hours. (Calculates electricity/wear @ $0.75/hr).
    * *Processing:* Enter `5.00` if you need to paint or sand it.
    * *Markup:* Default is `2.5x`. This covers your business profit.
5.  Click **CALCULATE QUOTE**.
    * *Result:* You will see a detailed breakdown: "Material Cost: $0.99... Final Price: $15.00".

### Step 4: The Workflow (Queue -> Sale) 🔄
You have two choices:
* **A. Save to Queue:** If the customer accepts the quote but you haven't printed it yet, click **⏳ Save to Queue**. It waits there until you are ready.
* **B. Finalize Sale:** If the print is done and paid for, click **✅ Finalize Sale Now**.
    * *Magic Moment:* The app permanently subtracts `45g` from that specific Red Spool in your inventory and logs the profit in your History.

---

## ✨ Advanced Features

### 🛡️ Safety Systems
* **Smart Auto-Backup:** Every time you launch the app, it zips your database. It keeps a rolling history of the last 2 days (Today + Yesterday). If you accidentally delete a spool, you can recover it from the `Backups/` folder.
* **Negative Inventory Guard:** If you try to print a `500g` helmet but only have `200g` left on the spool, the app will scream at you (politely) before letting you proceed.

### 📚 Digital Field Manual
Go to the **ℹ️ Reference** tab to find:
* **Filament Guide:** A built-in database of nozzle temps, bed temps, and fan speeds for common materials (PLA, PETG, ABS, TPU, Nylon, etc.).
* **Dynamic Gallery:** Drag any image named `ref_BedLeveling.png` or `ref_Infill.jpg` into the application folder. The app automatically builds a new tab to display it. Use this for calibration charts or pricing cheat sheets.

### 🛠️ Maintenance Tracker
Go to the **🛠️ Maintenance** tab to track:
* When you last greased your Z-rods.
* When you last dried your filament.
* *Action:* Click "Do Task Now" to update the timestamp to today.

---

## 🚀 Installation

### Option 1: The End User (.exe)
**Recommended for most users.**
1.  Download `PrintShopManager.exe` from the [Releases Page](../../releases).
2.  Place it in a folder (e.g., `Documents/3D Print Shop`).
3.  Double-click to run. No install wizard required.

### Option 2: The Developer (Python Source)
**For those who want to modify the code.**
1.  Clone this repository.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run: `python print_manager.py`

---

## 🧩 Technical Details
* **Language:** Python 3.x
* **GUI Framework:** `tkinter` + `ttkbootstrap` (Modern Flat Design)
* **Data Storage:** Local JSON files (`filament_inventory.json`).
* **Privacy:** This application is "Cloud Agnostic". It does not send data to any server. It simply reads/writes text files in the folder you choose.

*Created by Mobius457 for the 3D Printing Community.*
