# 3D Print Shop Manager 🚀 (v16.7)

**The "Fleet Commander" ERP for Modern Makers.**

Designed for multi-printer setups (Bambu Lab P1/P2/A1 series), this tool manages inventory, estimates costs with "Fair Pricing" logic, and tracks machine maintenance.

> **v16.7 "Fleet Commander Update"**: Features AMS Slot Mapping, Abrasive Material Safety, detailed Reference Encyclopedia, and a Professional Blue Theme.

---

## ✨ Key Features

### 🏢 Fleet & Inventory Management
* **AMS Mapping:** Assign specific spools to specific slots (e.g., *AMS-A Slot 3*, *External Spool*). Never lose track of which "Black PLA" is loaded where.
* **Abrasive Safety:** Flag spools as "⚠️ Abrasive" (CF, Glow, Wood) so you don't accidentally run them through a 0.2mm stainless nozzle.
* **Calibration Tracking:** Track not just *if* a Benchy was printed, but *which nozzle* (0.2, 0.4, 0.6) verified it.

### 🧠 Smart Pricing Engine ("Huntsville Logic")
* **Nozzle-Based Pricing:** Calculator accepts Nozzle Size inputs. (Faster 0.6mm prints = lower machine time cost).
* **Batch Pricing:** Calculates total plate cost, then divides by quantity for a precise **Unit Price** (rounded to the nearest dollar), preventing "sticker shock."
* **Dynamic Markup:** automatically adjusts profit margins based on automation level (High Swaps = Lower Margin).

### 📚 The "Encyclopedia" Reference
* **Detailed Manual:** Built-in data sheets for 12+ material types (PLA, ASA, PC, Nylon, etc.) covering temps, cooling, and fleet specific warnings.
* **Zoomable Charts:** Click any reference image (Nozzle charts, Bed adhesion guides) to open a full-screen, scrollable viewer.

### 🤖 AI Diagnostics (Gemini)
* **Slicer Reader:** Drag & drop slicer screenshots to auto-fill print time and gram usage.
* **Model Hunter:** "Test AI" button automatically detects the best available Google Gemini model (`flash`, `pro`, etc.) to prevent API errors.

---

## 🛠️ Installation

### Option 1: The Executable (Windows)
1.  Download `PrintShopManager.exe` from [Releases](../../releases).
2.  Run it. (No Python required).

### Option 2: Source Code
1.  Clone the repo:
    ```bash
    git clone [https://github.com/Mobius457/3D-Print-Shop-Manager.git](https://github.com/Mobius457/3D-Print-Shop-Manager.git)
    ```
2.  Install dependencies:
    ```bash
    pip install ttkbootstrap pillow paho-mqtt google-generativeai matplotlib
    ```
3.  Run:
    ```bash
    python print_manager.py
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