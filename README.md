# 3D Print Shop Manager 🚀 (v15.0)

**The "Smart" ERP for 3D Printing Businesses.**

From simple inventory tracking to **AI-powered estimation** and **Live Printer Monitoring**, PrintShopManager is the all-in-one dashboard for the modern maker.

---

## ✨ What's New in v15?
### 🤖 The AI Era
* **AI Slicer Reader:** Drag & drop a screenshot of your slicer (Bambu/Orca/Cura). The built-in Google Gemini AI extracts print time and gram usage automatically. No more manual data entry!
* **Price Estimator:** Ask the AI to estimate fair market value for specific filament brands/types.

### 📡 Live Operations
* **Bambu Lab Integration:** Connect directly to your X1/P1/A1 printers via MQTT.
* **Real-Time Dashboard:** See nozzle temps, bed temps, and print progress % directly in your shop dashboard.

### 🖥️ Modern UI Overhaul
* **Sidebar Navigation:** We ditched the cluttered tabs for a clean, professional sidebar layout.
* **Dark/Light Mode:** Instant theme toggling with persistent preferences.

### 📚 The Knowledge Base
* **Dynamic Reference Gallery:** Auto-loads reference images (`ref_*.png`) into tabs.
* **Filament Wiki:** Built-in cheat sheets for Temp, Fan Speed, and Plate Prep for all major materials (PLA, PETG, ABS, TPU, Nylon, CF).

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

## 🔐 Configuration & Privacy
**⚠️ IMPORTANT:** This app stores data in local JSON files.
* **Cloud Sync:** To sync between computers, set your Data Folder to OneDrive/Dropbox via *Settings -> Configure Printer/Paths*.
* **Privacy:** We use a strict `.gitignore`. Your `filament_inventory.json`, `sales_history.json`, and API Keys (`config.json`) are **NEVER** uploaded to GitHub.

---

## 🤖 Setting up AI Features (Free)
To use the **Slicer Screenshot Reader** or **Price Estimator**, you need a free Google Gemini API Key.

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **"Create API Key"**.
3. Copy the key string (starts with `AIza...`).
4. Open **PrintShopManager** -> **Settings** (or try to use an AI feature).
5. Paste your key when prompted.



## ⚖️ License
MIT License - Free for personal and commercial use.