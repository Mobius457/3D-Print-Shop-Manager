# 3D Print Shop Manager 🚀 (v14.19)

**The "Central Nervous System" for your 3D Printing Business.**

PrintShopManager is a desktop ERP (Enterprise Resource Planning) application designed specifically for micro-manufacturing, print farms, and side-hustles. It bridges the gap between basic spreadsheets and expensive, complex industrial software.

### 🎯 Core Features
* **🖩 Smart Calculator:** Calculate exact print costs (Material + Electricity + Labor + Markup). Includes a built-in **Spool Weight Estimator** chart.
* **📦 Inventory Tracking:** Track every gram. The app warns you *before* you start a print if a spool is too low.
* **📂 Profile Repository:** Auto-scans your Bambu Studio `.json` profiles. Inspect settings or export them directly from the app.
* **📚 Built-in Knowledge Base:** Integrated Bambu Lab Wiki data for Specs, Prep, Settings, and Annealing.
* **🛡️ Auto-Backups:** Daily automated backups of your inventory and sales history.

---

## 🏁 Getting Started Guide (Zero to Hero)

Follow these steps to get your shop running in under 5 minutes.

### Step 1: Initial Setup 📂
1.  **Download & Run:** Launch `PrintShopManager.exe`.
2.  **Cloud Sync (Optional but Recommended):**
    * Go to the **🏠 Dashboard** tab.
    * Click **📂 Set Data Folder**.
    * Select a folder in your Cloud Storage (OneDrive, Dropbox, Google Drive) to sync your inventory across multiple PCs.

### Step 2: Add Your First Spool 📦
You can't quote a job without plastic!
1.  Go to the **📦 Inventory** tab.
2.  **Brand/Name:** Enter "Polymaker PLA" or similar.
3.  **Material:** Select "PLA" (or your specific type).
4.  **Weight:** Enter the *net* weight (usually `1000`g).
    * *Tip:* Use the "Tare" radio buttons if you are weighing a partially used spool to subtract the empty spool weight automatically.
5.  **Cost:** Enter what you paid (e.g., `21.99`).
6.  **Color:** Type a color (e.g., "Red"). The app auto-generates a color dot.
7.  Click **Add Spool**.

### Step 3: Populate Your Profile Repository ⚙️
Turn the app into a library for your slicer profiles.
1.  Open the folder where `PrintShopManager.exe` is located.
2.  Create a new folder named **`profiles`**.
3.  **Copy** your `.json` filament profiles from Bambu Studio.
    * *System Profiles:* `%APPDATA%\BambuStudio\system\BBL\filament`
    * *User Profiles:* `%APPDATA%\BambuStudio\user\[YOUR_ID]\filament`
4.  **Paste** them into the `profiles` folder.
5.  **Restart the App.** Go to the **Reference** tab -> **📂 My Profiles** to see them. Double-click any row to Inspect or Export.

### Step 4: Calculate a Price 🖩
A customer wants a print. Let's quote it.
1.  Go to the **🖩 Calculator** tab.
2.  **Select Spool:** Pick the "Polymaker PLA" you just added.
3.  **Grams:** Enter the estimate from your slicer (e.g., `45`g). Click **Add**.
4.  **Labor & Overhead:**
    * *Print Time:* Enter `3.5` hours (Calculates electricity/wear).
    * *Processing:* Enter `5.00` if you need to paint/sand.
    * *Markup:* Default is `2.5x` (Adjustable).
5.  Click **CALCULATE QUOTE**.
    * *Result:* See the breakdown: "Material Cost: $0.99... Final Price: $15.00".
    * *Spool Check:* Use the **Spool Estimator Image** at the bottom left to see if your physical spool has enough filament left. Click the image to enlarge it.

---

## 📚 The Reference System (Wiki Data)

The **ℹ️ Reference** tab is your digital field manual. It is split into 4 sections based on the official Bambu Lab Filament Guide:

1.  **📂 My Profiles:**
    * Lists your custom `.json` files.
    * **Smart Inference:** Automatically detects if a nozzle needs to be Hardened Steel (e.g., for CF/Glow filaments) and estimates printing Difficulty.
    * **Action:** Double-click a row to **Inspect** the file (view raw settings) or **Export** it (save to desktop).

2.  **🧪 Wiki: Specs:**
    * Mechanical properties table (Impact Strength, Stiffness, Heat Deflection). Use this to decide *which* material to use for a functional part.

3.  **🔥 Wiki: Prep:**
    * Drying times, Enclosure requirements, and AMS compatibility rules. Check this *before* loading filament.

4.  **🎛️ Wiki: Settings:**
    * Official recommended temperature and speed ranges for generic material categories.

5.  **📷 Dynamic Gallery:**
    * Drag any image named `ref_MyChart.png` into the app folder to create a new tab automatically.
    * *Note:* The "Estimator" chart is now permanently located in the Calculator tab for easier access.

---

## 🛠️ Maintenance Tracker
Go to the **🛠️ Maintenance** tab to track:
* When you last greased Z-rods.
* When you last dried your desiccant.
* **Action:** Click "Do Task Now" to stamp the current date.

---

## 🚀 Installation

### Option 1: The End User (.exe)
**Recommended for most users.**
1.  Download `PrintShopManager.exe`.
2.  Place it in a dedicated folder (e.g., `Documents/3D Print Shop`).
3.  (Optional) Create a `profiles` folder next to it and drop in your JSON files.
4.  Double-click to run.

### Option 2: The Developer (Python Source)
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