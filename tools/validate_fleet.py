import json
import os
import glob
import re

# Configuration
INVENTORY_FILE = "filament_inventory.json"
PROFILES_DIR = "profiles"

# Colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return None

def normalize_material(text):
    """ Cleans up material names for better matching (e.g., 'PLA Basic' -> 'PLA') """
    if not text: return "UNKNOWN"
    t = text.upper().replace("-", " ").replace("_", " ")
    
    # Keyword mapping
    if "PLA" in t: return "PLA"
    if "PETG" in t: return "PETG"
    if "PCTG" in t: return "PCTG"
    if "ASA" in t: return "ASA"
    if "ABS" in t: return "ABS"
    if "TPU" in t: return "TPU"
    if "NYLON" in t or "PA" in t: return "NYLON"
    if "PC" in t or "POLYCARB" in t: return "PC"
    if "WOOD" in t: return "WOOD"
    if "PVA" in t: return "PVA"
    if "SILK" in t: return "PLA" # Usually Silk is PLA based
    
    return t.strip()

def main():
    print(f"{Colors.HEADER}{'='*40}")
    print(f"   FLEET READINESS AUDIT (v2)   ")
    print(f"{'='*40}{Colors.ENDC}\n")

    # 1. Load Inventory
    if not os.path.exists(INVENTORY_FILE):
        print(f"{Colors.FAIL}❌ Critical: {INVENTORY_FILE} not found.{Colors.ENDC}")
        return

    inventory = load_json(INVENTORY_FILE)
    owned_materials = set()
    for item in inventory:
        raw_mat = item.get('material', 'Unknown')
        norm_mat = normalize_material(raw_mat)
        owned_materials.add(norm_mat)

    print(f"📦 Inventory: {len(inventory)} spools")
    print(f"🧪 Materials Needed: {', '.join(sorted(owned_materials))}\n")

    # 2. Scan Profiles
    if not os.path.exists(PROFILES_DIR):
        os.makedirs(PROFILES_DIR)
    
    profile_files = glob.glob(os.path.join(PROFILES_DIR, "*.json"))
    supported_materials = {}

    print(f"📂 Scanning '{PROFILES_DIR}'...")
    
    if not profile_files:
        print(f"{Colors.FAIL}⚠️  NO PROFILES FOUND!{Colors.ENDC}")
        print(f"   Make sure you saved your .json files inside the '{PROFILES_DIR}' folder.")
        return

    for p_path in profile_files:
        data = load_json(p_path)
        fname = os.path.basename(p_path)
        
        # Strategy 1: Look for explicit key
        mat_guess = "Unknown"
        if data:
            if 'filament_type' in data:
                val = data['filament_type']
                mat_guess = val[0] if isinstance(val, list) else val
            # Strategy 2: Look at Profile Name
            elif 'name' in data:
                mat_guess = data['name']
            # Strategy 3: Look at Filename
            else:
                mat_guess = fname

        norm_mat = normalize_material(str(mat_guess))
        
        if norm_mat not in supported_materials:
            supported_materials[norm_mat] = []
        supported_materials[norm_mat].append(fname)
        
        # Debug print
        print(f"   📄 Found: {fname:<25} -> Detected as: {Colors.BOLD}{norm_mat}{Colors.ENDC}")

    # 3. Gap Analysis
    print(f"\n{Colors.HEADER}--- GAP ANALYSIS ---{Colors.ENDC}")
    all_good = True
    
    for mat in sorted(owned_materials):
        if mat in supported_materials:
            count = len(supported_materials[mat])
            print(f"{Colors.OKGREEN}✅ {mat:<10} : OK ({count} profiles){Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ {mat:<10} : MISSING PROFILE!{Colors.ENDC}")
            all_good = False

    print(f"\n{Colors.HEADER}{'='*40}{Colors.ENDC}")
    if all_good:
        print(f"{Colors.OKGREEN}🚀 FLEET READY{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}⚠️  ACTION REQUIRED{Colors.ENDC}")
    
    input("\nPress Enter to close...")

if __name__ == "__main__":
    os.system('color')
    main()