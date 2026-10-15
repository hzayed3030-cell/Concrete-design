import sys

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines[:100]):
    if 'import settings' in l or 'import modules.settings' in l or 'S.' in l:
        print(f"{i+1}: {l.strip()}")

for i, l in enumerate(lines):
    if 'save_settings' in l:
        print(f"{i+1}: {l.strip()}")
        if i > 120: break
