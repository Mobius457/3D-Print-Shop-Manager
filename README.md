# 3D Print Shop Manager 🚀 (v15.12)

**The "Smart" ERP for 3D Printing Businesses.**

From simple inventory tracking to **AI-powered estimation** and **Live Printer Monitoring**, PrintShopManager is the all-in-one dashboard for the modern maker.

> **v15.12 "The Golden Release"**: Features "Wife-Approved" Retail Pricing Logic, AI Diagnostics, and advanced Queue Management.

---

## ✨ Key Features

### 🧠 Smart Pricing Engine ("Huntsville Logic")
Stop scaring away customers with $50 quotes for small multi-color prints. The calculator now uses **Dynamic Complexity Logic**:
* **Volume Discount on Swaps:**
    * **< 100 Swaps:** Retail Rate ($0.15) for manual effort.
    * **> 100 Swaps:** Wholesale Rate ($0.03) for automated AMS labor.
* **Tiered Markup:** Automatically lowers profit margin (1.5x) on high-automation jobs to keep prices competitive.
* **Retail Rounding:** Calculates the **Unit Price** first, rounds it to the nearest dollar (e.g., $6.74 → $7.00), *then* calculates the Batch Total.

### 🤖 The AI Era (Google Gemini)
* **Slicer Reader:** Drag & drop a screenshot of your slicer (Bambu/Orca). The AI extracts print time and gram usage automatically.
* **Model Hunter:** New **Diagnostic Tool** in Settings detects which Gemini models are available to your API key (`gemini-1.5-flash`, `gemini-pro`, etc.) to prevent crashes.

### 📋 Queue Manager
* **Edit Jobs:** Right-click any queued job to rename it or update dates.
* **Reload to Calculator:** Send a queued job back to the Calculator tab with **all** settings (Time, Swaps, Fees, Markup) restored for adjustments.

### 💾 Data & Operations
* **Inventory Export:** Export your spool list to CSV for tax season.
* **Live Dashboard:** View revenue trends and spool usage statistics.
* **Bambu Lab Integration:** Connect via MQTT to see live nozzle/bed temps and status.

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