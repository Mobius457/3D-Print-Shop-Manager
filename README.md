# 3D Print Shop Manager 🚀 (v13.9)

**The "All-in-One" ERP tool for 3D printing businesses and hobbyists.**

Stop guessing your prices. Stop failing prints. Stop losing track of your inventory.

This Python application combines a **Business Manager** (Inventory, Quoting, Receipts) with a **Field Manual** (Maintenance, Digital Reference Guide). It features multi-user **Cloud Sync** and a built-in **Auto-Updater**.

---

## ✨ New in v13.9
* **📊 Digital Filament Guide:** No more blurry charts. A crisp, searchable, sortable table of Temps, Fans, and Nozzle types for every material.
* **🖼️ Dynamic Reference Gallery:** Automatically loads any reference image (`ref_*.png` or `ref_*.jpg`) you drop into the folder as a new tab.
* **📈 Smart Analytics:** Dashboard graph now shows exact dollar amounts for monthly net profit.
* **🎨 Visual Inventory:** Inventory list now features dynamic color swatches and clear "Benchy" status text.
* **🧠 Sticky Settings:** The calculator remembers your Markup, Labor Rate, and Waste % between sessions.

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
1.  **Run the App.**
2.  Go to **🏠 Dashboard** -> **System Actions** -> **📂 Set Data Folder**.
3.  Select your shared folder (OneDrive, Dropbox, Google Drive).
4.  The app will restart and sync instantly.

---

## ⚖️ License
Free to use for personal or commercial printing businesses. Happy Printing!