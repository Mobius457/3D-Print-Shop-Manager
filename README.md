# 3D Print Shop Manager 🚀 (v13.1)

**The "All-in-One" ERP tool for 3D printing businesses and hobbyists.**

Stop guessing your prices. Stop failing prints. Stop losing track of your inventory.

This lightweight Python application combines a **Business Manager** (Inventory, Quoting, Receipts) with a **Field Manual** (Maintenance, Troubleshooting). It features multi-user **Cloud Sync** and a built-in **Auto-Updater**.

---

## ✨ Key Features

### ☁️ Cloud & Sync
* **Multi-User Sync:** Automatically detects **OneDrive**, **Dropbox**, or **Google Drive**. Install this app on two different computers, and they will sync inventory instantly.
* **Smart Updater:** The app checks this GitHub repository for updates. If a new version is released, it can auto-update itself (Script mode) or direct you to the download page (EXE mode).
* **Retroactive Logging:** Forgot to log a job yesterday? Use the "Log Past Job" feature to record history and deduct inventory with a custom date.

### 📦 Inventory & Workflow
* **Visual Swatch Library:** Tracks which spools have a physical "Benchy" swatch printed (✅/❌ indicators).
* **Auto-Tare:** Automatically subtracts empty spool weight (Plastic/Cardboard).
* **Job Queue:** Save jobs to a "Pending" list and duplicate them for repeat orders.
* **Searchable Inventory:** Type "Silk" or "Red" to filter spools instantly.

### 💰 Business Analytics
* **Smart Calculator:** Handles overhead, labor, filament swaps (waste), and discounts.
* **Failure Logging:** One-click "Log Failure" button to deduct wasted filament and record the loss without deleting your job settings.
* **Profit Dashboard:** Track Revenue, Net Profit, and Tax Write-offs in real-time.

---

## 🚀 How to Install & Use

### Option 1: The Easy Way (.exe)
1.  Download `PrintShopManager.exe` from the [Releases Page](../../releases).
2.  Double-click to run. (No installation required).

### Option 2: Run from Source (Python)
1.  Clone this repository.
2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the script:
    ```bash
    python print_manager.py
    ```

---

## 📂 Configuration
### Cloud Sync Setup
To share data between two people (e.g., You and a Partner):
1.  **Create a Folder:** On Computer A, create a folder named `PrintShopManager` inside your **OneDrive** or **Dropbox**.
2.  **Share It:** Right-click that folder and **Share** it with Computer B's email (Select "Can Edit").
3.  **Link It (Crucial):** On Computer B, go to the OneDrive/Dropbox website, find the shared folder, and click **"Add shortcut to My files"**.
    * *This forces the folder to appear on the hard drive, not just the website.*

### Auto-Update Setup
If you are forking this repo, edit the `GITHUB_RAW_URL` and `GITHUB_REPO_URL` variables at the top of `print_manager.py` to point to your own repository.

---

## 🏗️ Building the EXE
To compile this into a single executable file for Windows:

```bash
pyinstaller --noconsole --onefile --name="PrintShopManager" --collect-all ttkbootstrap --add-data "spool_reference.png;." print_manager.py