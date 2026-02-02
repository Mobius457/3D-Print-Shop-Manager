# 3D Print Shop Manager 🚀 (v17.0)

**The "Fleet Commander" ERP for Modern Makers.**

Designed for multi-printer setups (Bambu Lab P1/P2/A1 series), this tool manages inventory, estimates costs with "Fair Pricing" logic, and tracks machine maintenance.

> **v17.0 Update**: Now features detailed Calibration Tracking, Fleet Validation tools, and a Professional Blue interface.

---

## ✨ Key Features

### 🏢 Fleet & Inventory Management
* **AMS Mapping:** Assign specific spools to specific slots (e.g., *AMS-A Slot 3*, *External Spool*). Never lose track of which "Black PLA" is loaded where.
* **Abrasive Safety:** Flag spools as "⚠️ Abrasive" (CF, Glow, Wood). Icons turn Yellow/Red to prevent ruining a standard nozzle.
* **Calibration Detail:** Track not just *if* a Benchy was printed, but specifically **which nozzle** (0.2, 0.4, 0.6) was verified.

### 🧠 Smart Pricing Engine ("Huntsville Logic")
* **Nozzle-Based Pricing:** Calculator accepts Nozzle Size inputs to adjust for machine time (Fast 0.6mm vs Detail 0.2mm).
* **Batch Pricing:** Calculates total plate cost, then divides by quantity for a precise **Unit Price**, rounded to the nearest dollar.
* **Dynamic Markup:** Automatically adjusts profit margins based on complexity and labor.

### 📚 The "Encyclopedia" Reference
* **Detailed Manual:** Built-in data sheets for 12+ material types (PLA, ASA, PC, Nylon, etc.) covering temps, cooling, and fleet-specific warnings.
* **Zoomable Charts:** Click any reference image (Nozzle charts, Bed adhesion guides) to open a full-screen, scrollable viewer.

### 🛠️ Fleet Utilities
* **Profile Auditor:** Includes a Python script (`validate_fleet_v2.py`) that scans your inventory and your `.json` print profiles to ensure you never load a spool you don't have settings for.
* **AI Diagnostics:** "Test AI" button automatically detects the best available Google Gemini model to prevent API errors.

---

## 🛠️ Installation

### Option 1: The Executable (Windows)
1.  Download `PrintShopManager.exe` from [Releases](../../releases).
2.  Run it. (No Python required).
3.  *Note: Keep the `.exe` in the same folder as your `profiles/` folder and `.json` data files.*

### Option 2: Source Code
1.  Clone the repo:
    ```bash
    git clone [https://github.com/Mobius457/3D-Print-Shop-Manager.git](https://github.com/Mobius457/3D-Print-Shop-Manager.git)
    ```
2.  Install dependencies:
    ```bash
    pip install ttkbootstrap pillow paho-mqtt google-generativeai matplotlib
    ```
3.  Run the App:
    ```bash
    python print_manager.py
    ```
4.  Run the Fleet Validator (Optional):
    ```bash
    python validate_fleet_v2.py
    ```

---

## 🔐 Configuration

**⚠️ Privacy First:** Your inventory, sales history, and API keys are stored locally in `.json` files. They are never uploaded to the cloud.

### 🤖 Setting up AI (Optional)
1.  Get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Go to **Settings** -> **Test AI & List Models**.
3.  The app will auto-configure the fastest model for your key.

---

## ⚖️ License
MIT License - Free for personal and commercial use.