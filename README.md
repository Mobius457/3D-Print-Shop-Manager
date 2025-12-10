# 3D Print Shop Manager 🚀

**The ultimate "All-in-One" tool for 3D printing hobbyists and small businesses.**

Stop guessing your prices. Stop running out of filament mid-print. Stop losing track of your sales.

This application is a lightweight, single-file solution that manages your **Inventory**, calculates **Perfect Prices** based on professional formulas (Material + Electricity + Machine Wear), and tracks your **Sales History** automatically.

## ✨ Key Features

### 💰 Professional Quoting Engine
* **Smart Calculator:** Input your material cost, print time, and desired markup to get a suggested sell price instantly.
* **Overhead Calculation:** Automatically accounts for electricity, machine wear-and-tear, and waste.

### 🧾 Professional Invoicing (New!)
* **Automated Receipts:** Generates beautiful, text-based invoices automatically.
* **Wife-Approved Layout:** Includes line-item breakdowns, technical specs (layer height/material), and care instructions for your customers.
* **Auto-Save:** Receipts are instantly saved to `Documents/3D_Print_Receipts`.

> **[INSERT SCREENSHOT OF YOUR RECEIPT HERE]**

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