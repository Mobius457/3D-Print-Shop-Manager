# 3D Print Shop Manager 🚀 (v15.15)

**The "Smart" ERP for 3D Printing Businesses.**

From simple inventory tracking to **AI-powered estimation** and **Live Printer Monitoring**, PrintShopManager is the all-in-one dashboard for the modern maker.

> **v15.15 "The Wife-Approved Update"**: Features Smart Retail Pricing, Batch Calculations, AI Diagnostics, and Reference Image Zooming.

---

## ✨ Key Features

### 🧠 Smart Pricing Engine ("Huntsville Logic")
Stop scaring away customers with $50 quotes for small multi-color prints. The calculator now uses **Dynamic Complexity Logic**:
* **Volume Discount on Swaps:**
    * **< 100 Swaps:** Retail Rate ($0.15) for manual effort.
    * **> 100 Swaps:** Wholesale Rate ($0.03) for automated AMS labor.
* **Batch Pricing:** Calculates the total cost for a full plate, then divides by quantity to give you a precise **Unit Price**.
* **Retail Rounding:** It calculates the Unit Price, rounds it to the nearest dollar (e.g., $6.74 → $7.00), *then* calculates the Batch Total. No more awkward "$6.75" price tags.

### 🤖 The AI Era (Google Gemini)
* **Slicer Reader:** Drag & drop a screenshot of your slicer (Bambu/Orca). The AI extracts print time and gram usage automatically.
* **Model Hunter:** New **Diagnostic Tool** in Settings detects which Gemini models are available to your API key (`gemini-1.5-flash`, `gemini-pro`, etc.) to prevent "404 Not Found" crashes.

### 🔍 Reference Library
* **Zoom & Pan:** Click any reference chart (Filament specs, troubleshooting guides) to open it in a full-screen, scrollable viewer. No more squinting at 4K images!
* **Expanded Materials:** Dropdowns now support ASA, Nylon, PC, HIPS, PVA, Wood, and Carbon Fiber.

### 📋 Queue Manager
* **Edit Jobs:** Right-click any queued job to rename it or update dates.
* **Reload to Calculator:** Send a queued job back to the Calculator tab with **all** settings (Time, Swaps, Fees, Markup, Batch Qty) restored for adjustments.

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
2.  Install dependencies (Critical for AI features):
    ```bash
    pip install ttkbootstrap pillow paho-mqtt google-generativeai matplotlib
    ```
    *Note: If you get AI errors, run `pip install --upgrade google-generativeai`*
3.  Run:
    ```bash
    python print_manager.py
    ```

---

## 🔐 Configuration & Privacy

**⚠️ IMPORTANT:** This app stores data in local JSON files.
* **Cloud Sync:** To sync between computers, set your Data Folder to OneDrive/Dropbox via *Settings*.
* **Privacy:** Your `filament_inventory.json`, `sales_history.json`, and API Keys (`config.json`) are **NEVER** uploaded to GitHub.

### 🤖 Setting up AI Features (Free)
1.  Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Create a free API Key.
3.  Open **PrintShopManager** -> **Settings**.
4.  Paste your key.
5.  Click **"🔍 Test AI & List Models"** to auto-configure the best model for your computer.

---

## ⚖️ License
MIT License - Free for personal and commercial use.