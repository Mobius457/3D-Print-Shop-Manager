import pandas as pd
import json
import os

# --- CONFIGURATION ---
EXCEL_FILE = "3D Filament.xlsx"
OUTPUT_FILE = "filament_inventory.json"

inventory = []

try:
    # Read the entire Excel file (all sheets)
    # sheet_name=None means "read all sheets and return a dictionary"
    print(f"📂 Reading {EXCEL_FILE}...")
    xls = pd.read_excel(EXCEL_FILE, sheet_name=None)
    
    print(f"found {len(xls.keys())} sheets: {list(xls.keys())}")

    for sheet_name, df in xls.items():
        # Use the Sheet Name as the Material (e.g., "PLA", "PETG")
        material_type = sheet_name.strip()
        
        # Skip empty sheets
        if df.empty:
            continue

        # Standardize column names (strip whitespace, lower case for matching)
        df.columns = [str(c).strip() for c in df.columns]
        
        # We expect columns like 'ID', 'Name' (for color), 'Benchy'
        # Let's try to map them dynamically
        
        for index, row in df.iterrows():
            try:
                # 1. Get ID (and clean it up)
                if 'ID' in df.columns:
                    raw_id = row['ID']
                elif 'id' in df.columns:
                    raw_id = row['id']
                else:
                    # If no ID column, maybe it's the first column?
                    raw_id = row.iloc[0]

                # Convert to string and remove decimals like "101.0" -> "101"
                id_val = str(raw_id)
                if id_val == "nan": id_val = ""
                if id_val.endswith(".0"): id_val = id_val[:-2]

                # 2. Get Color (Name)
                if 'Name' in df.columns:
                    color_val = str(row['Name'])
                elif 'Color' in df.columns:
                    color_val = str(row['Color'])
                else:
                    # Fallback to 2nd column
                    color_val = str(row.iloc[1])
                
                if color_val == "nan": color_val = "Unknown"

                # 3. Check Benchy
                has_benchy = False
                if 'Benchy' in df.columns:
                    val = str(row['Benchy']).lower().strip()
                    if val == 'yes' or val == 'y' or val == 'true':
                        has_benchy = True
                
                # 4. Build Item
                # Skip if ID and Color are both empty (empty row)
                if not id_val and color_val == "Unknown":
                    continue

                item = {
                    "id": id_val,
                    "name": "Generic",      # Excel doesn't seem to have Brand, defaulting
                    "material": material_type,
                    "color": color_val,
                    "weight": 1000.0,       # Default to full spool
                    "cost": 20.00,          # Default cost
                    "has_benchy": has_benchy
                }
                
                inventory.append(item)
                print(f"  [{material_type}] Added #{id_val}: {color_val}")

            except Exception as e:
                print(f"  ⚠️ Skipped row in {sheet_name}: {e}")

    # Save to JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(inventory, f, indent=4)

    print(f"\n✅ SUCCESS! Processed {len(inventory)} spools from Excel.")
    print(f"File saved to: {os.path.abspath(OUTPUT_FILE)}")
    print("-> Move this file to your PrintShopManager cloud folder.")

except FileNotFoundError:
    print(f"❌ Error: Could not find '{EXCEL_FILE}'. Make sure it's in this folder.")
except Exception as e:
    print(f"❌ Critical Error: {e}")