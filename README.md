# 3D Print Shop Manager 🚀

**The ultimate "All-in-One" tool for 3D printing hobbyists and small businesses.**

Stop guessing your prices. Stop running out of filament mid-print. Stop losing track of your sales.

This application is a lightweight, single-file solution that manages your **Inventory**, calculates **Perfect Prices** based on professional formulas (Material + Electricity + Machine Wear), and tracks your **Sales History** automatically.

---
## ✨ New in v6.3: Bulk Management & Business Tools

### 📦 Inventory Power-Ups
* **Bulk Editing:** Select multiple spools (hold `Ctrl` or `Shift`) and click **"Edit Selected"** to mass-update materials, brand names, or colors instantly.
* **Smart Filtering:** Filter your inventory by Brand Name OR Material Type (e.g., type "PETG" to see all PETG spools, regardless of brand).
* **Auto-Tare:** Automatically subtracts empty spool weight (Plastic/Cardboard) when weighing used filament.

### 💰 Business Analytics
* **Profit Dashboard:** Track your Total Revenue, Net Profit, and Tax Write-offs (Donations) in real-time.
* **Smart Quoting:**
    * **Post-Processing:** Add fees for assembly, painting, or sanding.
    * **Discounts:** Apply "Friends & Family" discounts instantly.
    * **Donation Mode:** Track the value of prints you donate for tax purposes.

### 📚 Field Manual & Maintenance
* **Smart Search:** Type "pop" or "clog" to find relevant troubleshooting guides.
* **Maintenance Tracker:** Keep a log of when you last greased Z-rods or tightened belts.
* **Bambu Lab Profiles:** Specific tips for X1/P1/A1 users.
---    

## ✨ Key Features

### 💰 Professional Quoting Engine
* **Smart Calculator:** Input your material cost, print time, and desired markup to get a suggested sell price instantly.
* **Overhead Calculation:** Automatically accounts for electricity, machine wear-and-tear, and waste.

### 🧾 Professional Invoicing (New!)
* **Automated Receipts:** Generates beautiful, text-based invoices automatically.
* **Wife-Approved Layout:** Includes line-item breakdowns, technical specs (layer height/material), and care instructions for your customers.
* **Auto-Save:** Receipts are instantly saved to `Documents/3D_Print_Receipts`.

> <img width="518" height="546" alt="Screenshot 2025-12-10 122953" src="https://github.com/user-attachments/assets/dcf40c66-e8eb-4003-b442-a0eaf8cde898" />

### 📦 Intelligent Inventory System
* **Live Tracking:** Automatically subtracts grams from your spools when you finish a job.
* **Visual Low-Stock Alerts:**
    * 🟡 **Yellow:** Low Stock (< 200g)
    * 🔴 **Red:** Critical Stock (< 50g)
* **One-Click Price Search:** Don't know what a spool costs? Click "🔍 Check Price Online" to instantly query Google Shopping.

---

## 🚀 How to Install & Use

### For Users (The ".exe" Method)
1.  Download `PrintShopManager.exe` from the **Releases** page.
2.  Double-click to run. Your data is safely stored in your Windows AppData folder.

### For Developers (Running from Source)
1.  Clone this repository.
2.  Ensure you have Python installed.
3.  Run the script:
    ```bash
    python print_manager_v6.py
    ```

---

## 🛠️ How to Build the EXE (for Developers)

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Run the build command:**
    ```bash
    pyinstaller --noconsole --onefile --name="PrintShopManager" print_manager_v6.py
    ```

---

## 📂 Where is my Data?
This app uses a "Clean Desktop" philosophy.
* **Inventory & History:** Saved in `%LOCALAPPDATA%\PrintShopManager\`
* **Receipts:** Saved in `Documents\3D_Print_Receipts`

---

## ⚖️ License
Free to use for personal or commercial printing businesses. Happy Printing!
