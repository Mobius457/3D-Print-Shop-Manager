# 3D Print Shop Manager 🚀

**The ultimate "All-in-One" tool for 3D printing hobbyists, small businesses, and beginners.**

Stop guessing your prices. Stop failing prints. Stop losing track of your inventory.

This application is a lightweight, single-file solution that combines a **Business Manager** (Inventory, Quoting, Receipts) with a complete **3D Printing Field Manual** (Maintenance Tracking, Troubleshooting, Material Guides).

---

## ✨ Key Features

### 🛠️ Maintenance Tracker (New!)
* **Live Logging:** Track exactly when you last cleaned your bed, greased Z-rods, or tightened belts.
* **Persistent Data:** Remembers your maintenance history even after you restart the app.

### 🧠 Smart Search & Diagnostics
* **Fuzzy Logic Search:** Type "pop", "click", or "stringing" and the app instantly finds the relevant guide, even if you make a typo.
* **Multi-Hit Detection:** If a problem has multiple causes, the app points you to the best fix but lists other possibilities.

### 📚 Expert Knowledge Base
* **First Layer "Holy Grail":** A dedicated guide to mastering Z-Offset vs. Leveling.
* **Material Database:** Deep dives on PLA, PETG, TPU, ABS/ASA, and Silk PLA.
* **Bambu Lab Profiles:** Specific tips for X1/P1/A1 users (Grid Infill warnings, AMS compatibility).

### 💰 Professional Quoting Engine
* **Smart Calculator:** Input material cost, print time, and markup to get a sell price instantly.
* **Pro Receipts:** Generates beautiful text-file invoices saved to your Documents folder.

---

## 🚀 How to Install & Use

### Option 1: The Easy Way (.exe)
1.  Download `PrintShopManager.exe` from the **Releases** page on the right.
2.  Double-click to run. (No installation required).

### Option 2: Run from Source (Python)
If you want to run the raw code:
1.  Clone this repository.
2.  Install the required image library:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the script:
    ```bash
    python print_manager.py
    ```

---

## 🏗️ How to Build the EXE (For Developers)
To compile the script into a standalone executable, use the following command. This ensures the reference image is bundled correctly inside the file.

```bash
pyinstaller --noconsole --onefile --name="PrintShopManager" --add-data "spool_reference.png;." print_manager.py
```

---

## 📂 Where is my Data?
This app uses a "Clean Desktop" philosophy.

Inventory & History: Saved in %LOCALAPPDATA%\PrintShopManager\

Receipts: Saved in Documents\3D_Print_Receipts (Auto-detects OneDrive).

## ⚖️ License
Free to use for personal or commercial printing businesses. Happy Printing!

