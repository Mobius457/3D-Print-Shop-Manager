# 3D Print Shop Manager 🚀 (v12.3)

**The "All-in-One" ERP tool for 3D printing businesses and hobbyists.** *Now with Multi-User Cloud Sync!*

Stop guessing your prices. Stop failing prints. Stop losing track of your inventory.

This lightweight Python application combines a **Business Manager** (Inventory, Quoting, Receipts) with a **Field Manual** (Maintenance, Troubleshooting). It is designed to be "Drop-in and Run"—no servers, no subscriptions.

---

## ✨ New in v12.3: Cloud Sync & Team Features
* **☁️ Multi-User Sync:** Automatically detects **OneDrive**, **Dropbox**, or **Google Drive**. Install this app on two different computers, and they will sync inventory instantly via the cloud.
* **🔍 Instant Filter:** New dedicated search bar above the inventory list. Type "Silk" or "Red" to filter spools in real-time.
* **🏷️ Benchy ID System:** Assign short codes (e.g., `#042`) to spools to match them with physical swatch samples.
* **⚡ Live Refresh:** Switching tabs automatically reloads data from the disk/cloud, so you see your partner's changes immediately.

---

## 🛠️ Key Features

### 📦 Inventory & Workflow
* **Smart Search:** Filter inventory by Name, Material, or ID tag.
* **Auto-Tare:** Automatically subtracts empty spool weight (Plastic/Cardboard).
* **Job Queue:** Save jobs to a "Pending" list. Duplicate old jobs for repeat orders.
* **Action Toolbar:** Quick access to Edit, Bulk Set Material, and Price Checking.

### 💰 Business Analytics
* **Smart Calculator:** Handles overhead, labor, filament swaps (waste), and discounts.
* **Failure Logging:** One-click "Log Failure" button to deduct wasted filament and record the loss without deleting your job settings.
* **Profit Dashboard:** Track Revenue, Net Profit, and Tax Write-offs in real-time.

> <img width="518" height="546" alt="Screenshot 2025-12-10 122953" src="https://github.com/user-attachments/assets/dcf40c66-e8eb-4003-b442-a0eaf8cde898" />

### 📚 Maintenance & Knowledge
* **Field Manual:** Integrated guide with Smart Search (e.g., type "pop" to find wet filament fixes).
* **Maintenance Log:** Track deadlines for greasing Z-rods, tightening belts, and cleaning beds.

---

## 🚀 How to Use "Cloud Sync"
To share data between two people (e.g., You and a Partner):

1.  **Create a Folder:** On Computer A, create a folder named `PrintShopManager` inside your **OneDrive** or **Dropbox**.
2.  **Share It:** Right-click that folder and **Share** it with Computer B's email (Select "Can Edit").
3.  **Link It (Crucial):** On Computer B, go to the OneDrive/Dropbox website, find the shared folder, and click **"Add shortcut to My files"**.
    * *This forces the folder to appear on the hard drive, not just the website.*
4.  **Run the App:** The script will automatically find that folder on both computers and sync your inventory.

---

## 📦 Installation (Source)

1.  **Clone the repo:**
    ```bash
    git clone [https://github.com/YourUsername/PrintShopManager.git](https://github.com/YourUsername/PrintShopManager.git)
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the app:**
    ```bash
    python print_manager.py
    ```

---

## 🏗️ Building an .EXE
To compile this into a single executable file for Windows:

```bash
pyinstaller --noconsole --onefile --name="PrintShopManager" --collect-all ttkbootstrap --add-data "spool_reference.png;." print_manager.py
