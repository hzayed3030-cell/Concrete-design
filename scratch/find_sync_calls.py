import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '_handle_fs_sync_payload' in l:
        print(f"Line {i+1}: {l.strip()}")
