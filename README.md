
# 3D Print Shop Manager 🚀

The ultimate "All-in-One" tool for 3D printing hobbyists and small businesses.

Stop guessing your prices. Stop running out of filament mid-print. Stop losing track of your sales.

This application is a lightweight, single-file solution that manages your Inventory, calculates Perfect Prices based on professional formulas (Material + Electricity + Machine Wear), and tracks your Sales History automatically.


## ✨ Key Features

### 💰 Professional Quoting Engine
* Smart Calculator: Input your material cost, print time, and desired markup to get a suggested sell price instantly.
* Multi-Color Support: Perfect for Bambu Lab AMS or Mosaic Palette users. Mix 4+ colors in a single quote.
* Overhead Calculation: Automatically accounts for electricity, machine wear-and-tear, and waste (poop/purge lines).

### 📦 Intelligent Inventory System
* Live Tracking: Automatically subtracts grams from your spools when you finish a job.
* Visual Low-Stock Alerts:
  * 🟡 Yellow: Low Stock (< 200g)
  * 🔴 Red: Critical Stock (< 50g)
* One-Click Price Search: Don't know what a spool costs? Click "🔍 Check Price Online" to instantly query Google Shopping.

### 📄 Sales & Receipts
* Automatic History Log: Keeps a permanent record of every print you've ever sold, including profit margins.
* Instant Invoices: Generates professional text-file receipts automatically saved to your Documents/3D_Print_Receipts folder.
* Bulletproof Saving: Intelligently detects OneDrive/Windows folder structures to ensure your data never gets lost.

### ℹ️ Built-in References
* Includes a visual "Cheat Sheet" to help you estimate how much filament is left on a partial spool without unspooling it.


## 🚀 How to Install & Use

### For Users (The ".exe" Method)
1. Download `PrintShopManager.exe` from the Releases page.
2. Double-click to run. Your data is safely stored in your Windows AppData folder.

### For Developers (Running from Source)
1. Clone this repository.
2. Ensure you have Python installed.
3. Run the script:
   ```bash
   python print_manager_v6.py
   ```

### 🛠️ How to Build the EXE (for Developers)
1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Run the build command:
   ```bash
   pyinstaller --noconsole --onefile --name="PrintShopManager" --add-data "spool_reference.png;." print_manager_v6.py
   ```

## 📂 Where is my Data?

This app uses a "Clean Desktop" philosophy. It does not clutter your desktop with data files.

* Inventory & History: Saved in `%LOCALAPPDATA%\PrintShopManager\` (Hidden Windows System Folder).
* Receipts: Saved in `Documents\3D_Print_Receipts`.

⚖️ License
Free to use for personal or commercial printing businesses. Happy Printing!
