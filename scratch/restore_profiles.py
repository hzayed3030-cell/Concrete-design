import subprocess
import json
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 1. First make a safe timestamped copy of profiles.json
shutil.copy('profiles.json', 'profiles.json.pre_restore_bak')

with open('profiles.json', 'r', encoding='utf-8') as f:
    profiles_data = json.load(f)

profiles = profiles_data.get('profiles', {})

# 2. Fix "بلاطة دور السطح - فلات سلاب"
if 'بلاطة دور السطح - فلات سلاب' in profiles:
    p_surface = profiles['بلاطة دور السطح - فلات سلاب']
    p_data = p_surface.get('data', {})
    p_data['enabled_modules'] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    p_data['selected_module_idx'] = 0
    p_data['nav_view'] = 'module'
    print("Fixed 'بلاطة دور السطح - فلات سلاب': enabled_modules=[0..11], selected_module_idx=0")

# 3. Restore "try1" from commit b8bd36bb
try:
    content = subprocess.check_output(['git', 'show', 'b8bd36bb:profiles.json'], encoding='utf-8')
    hist_profiles = json.loads(content).get('profiles', {})
    if 'try1' in hist_profiles:
        hist_try1_data = hist_profiles['try1'].get('data', {})
        # Keep any newer Module 12 or custom keys if present, but restore the rich 4x3 structural data
        curr_try1_data = profiles.get('try1', {}).get('data', {})
        merged_try1_data = dict(hist_try1_data)
        # Overlay any specific Module 12 state from current if it exists
        if 'module_12_brick_survey' in curr_try1_data:
            merged_try1_data['module_12_brick_survey'] = curr_try1_data['module_12_brick_survey']
        merged_try1_data['enabled_modules'] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        merged_try1_data['selected_module_idx'] = 0
        merged_try1_data['nav_view'] = 'module'
        
        if 'try1' not in profiles:
            profiles['try1'] = {'name': 'try1', 'description': 'مشروع try1', 'data': {}}
        profiles['try1']['data'] = merged_try1_data
        print(f"Restored 'try1' data from commit b8bd36bb: {len(merged_try1_data)} keys restored (grid: {merged_try1_data.get('fs_n_lx')}x{merged_try1_data.get('fs_n_ly')})")
except Exception as e:
    print(f"Error restoring try1: {e}")

# 4. Save updated profiles.json and backup to profiles.json.bak
profiles_data['profiles'] = profiles
with open('profiles.json', 'w', encoding='utf-8') as f:
    json.dump(profiles_data, f, indent=2, ensure_ascii=False)

shutil.copy('profiles.json', 'profiles.json.bak')
print("Successfully saved profiles.json and updated profiles.json.bak")
