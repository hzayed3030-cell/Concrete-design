import sys
import json
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))

from modules import settings as S

print("==================== VERIFYING PROFILES & SETTINGS ====================")

# 1. Load profiles data through settings module
pdata = S.load_profiles_data()
profiles = pdata.get("profiles", {})
print(f"Total profiles loaded: {len(profiles)}")

# 2. Check "بلاطة دور السطح - فلات سلاب"
p_surf = profiles.get("بلاطة دور السطح - فلات سلاب", {})
d_surf = p_surf.get("data", {})
en_surf = S.get_project_enabled_modules("بلاطة دور السطح - فلات سلاب")
print("\n--- Project: بلاطة دور السطح - فلات سلاب ---")
print(f"  Enabled modules: {en_surf} (Total: {len(en_surf)})")
print(f"  Grid: {d_surf.get('fs_n_lx')} x {d_surf.get('fs_n_ly')}")
print(f"  Lx spans: {[d_surf.get(f'fs_lx_{i}') for i in range(d_surf.get('fs_n_lx', 0))]}")
print(f"  Ly spans: {[d_surf.get(f'fs_ly_{j}') for j in range(d_surf.get('fs_n_ly', 0))]}")
print(f"  Removed columns count: {len(d_surf.get('fs_removed_cols', []))}")
print(f"  Column transforms count: {len(d_surf.get('fs_col_transforms', {}))}")
print(f"  Void panels count: {len(d_surf.get('fs_void_panels', []))}")

assert len(en_surf) == 12, "بلاطة دور السطح must have all 12 modules enabled!"
assert d_surf.get('fs_n_lx') == 5, "fs_n_lx must be 5!"
assert d_surf.get('fs_n_ly') == 4, "fs_n_ly must be 4!"
assert len(d_surf.get('fs_removed_cols', [])) == 14, "Must have 14 removed columns!"
assert len(d_surf.get('fs_col_transforms', {})) == 16, "Must have 16 column transforms!"
assert len(d_surf.get('fs_void_panels', [])) == 2, "Must have 2 void panels!"
print("  >>> PASS: بلاطة دور السطح - فلات سلاب is 100% verified!")

# 3. Check "try1"
p_try1 = profiles.get("try1", {})
d_try1 = p_try1.get("data", {})
en_try1 = S.get_project_enabled_modules("try1")
print("\n--- Project: try1 ---")
print(f"  Enabled modules: {en_try1} (Total: {len(en_try1)})")
print(f"  Total keys: {len(d_try1)}")
print(f"  Grid: {d_try1.get('fs_n_lx')} x {d_try1.get('fs_n_ly')}")
print(f"  Lx spans: {[d_try1.get(f'fs_lx_{i}') for i in range(d_try1.get('fs_n_lx', 0))]}")
print(f"  Ly spans: {[d_try1.get(f'fs_ly_{j}') for j in range(d_try1.get('fs_n_ly', 0))]}")
print(f"  Module 9 P1_w: {d_try1.get('module_9_strap_footing', {}).get('P1_w')}")
print(f"  Concrete survey cs_price_steel: {d_try1.get('cs_price_steel')}")

assert len(en_try1) == 12, "try1 must have all 12 modules enabled!"
assert d_try1.get('fs_n_lx') == 4, "try1 fs_n_lx must be 4!"
assert d_try1.get('fs_n_ly') == 3, "try1 fs_n_ly must be 3!"
assert len(d_try1) >= 390, f"try1 must have full historical keys (has {len(d_try1)})!"
print("  >>> PASS: try1 is 100% verified!")

# 4. Check all 18 projects enabled_modules
print("\n--- Checking All 18 Projects for Hidden Modules ---")
for pname, p in profiles.items():
    en = S.get_project_enabled_modules(pname)
    d = p.get('data', {})
    fs_cnt = sum(1 for k in d if k.startswith('fs_'))
    print(f"  {pname:35s}: enabled={len(en):2d} modules | fs_keys={fs_cnt:2d} | total_keys={len(d):3d}")
    assert len(en) > 0, f"{pname} has 0 enabled modules!"
    # Ensure structural projects are not trapped in a single module
    if fs_cnt > 10:
        assert len(en) == 12, f"{pname} with structural data must have all 12 modules visible!"

print("\n==================== ALL 18 PROFILES VERIFIED SUCCESSFULLY! ====================")
