# 3D Print Shop Manager 🚀 (v13.2)

**The "All-in-One" ERP tool for 3D printing businesses and hobbyists.**

Stop guessing your prices. Stop failing prints. Stop losing track of your inventory.

This lightweight Python application combines a **Business Manager** (Inventory, Quoting, Receipts) with a **Field Manual** (Maintenance, Troubleshooting). It features multi-user **Cloud Sync** and a built-in **Auto-Updater**.

---

## ✨ Key Features

### ☁️ Cloud & Sync (Enterprise Ready)
* **Custom Data Path:** Works with **Work OneDrive**, **SharePoint**, **Syncthing**, or any specific folder you choose.
* **Multi-User Sync:** Install on multiple computers and point them to the same shared folder to see inventory updates instantly.
* **Auto-Updater:** Automatically checks GitHub for updates. Script users get auto-patched; EXE users get a download alert.

### 📦 Inventory & Workflow
* **Visual Swatch Library:** Tracks which spools have a physical "Benchy" swatch printed (✅/❌ indicators).
* **Auto-Tare:** Automatically subtracts empty spool weight (Plastic/Cardboard).
* **Job Queue:** Save jobs to a "Pending" list and duplicate them for repeat orders.
* **Searchable Inventory:** Type "Silk" or "Red" to filter spools instantly.

### 💰 Business Analytics
* **Smart Calculator:** Handles overhead, labor, filament swaps (waste), and discounts.
* **Retroactive Logging:** Forgot to log a job yesterday? Use the "Log Past Job" feature to record history and deduct inventory with a custom date.
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
### Setting up Sync (Crucial for Multiple Users)
If you are using **OneDrive (Personal/Business)** or **Dropbox**:

1.  **Run the App.**
2.  Go to the **🏠 Dashboard** tab.
3.  Look at the "System Actions" box.
4.  Click **"📂 Set Data Folder"**.
5.  Select the shared folder where you want your database to live (e.g., `OneDrive - MyCompany\PrintShopData`).
6.  The app will restart and remember this location forever.

### Auto-Update Setup
If you are forking this repo, edit the `GITHUB_RAW_URL` and `GITHUB_REPO_URL` variables at the top of `print_manager.py` to point to your own repository.

---

## 🏗️ Building the EXE
To compile this into a single executable file for Windows:

```bash
pyinstaller --noconsole --onefile --name="PrintShopManager" --collect-all ttkbootstrap --add-data "spool_reference.png;." print_manager.py
```

## ⚖️ License
Free to use for personal or commercial printing businesses. Happy Printing!


---

### 2. Git Commands to Push v13.2
Run these in your VS Code terminal to send the new code and Readme to GitHub:

```powershell
git add .
git commit -m "Update to v13.2: Added Manual Data Path selector for Work OneDrive support"
git push origin main
