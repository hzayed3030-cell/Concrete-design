import sys
import inspect

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

for fn in ['generate_flat_slab_sketch', 'generate_flat_slab_master_steel_layout_sketch', 'calculate_flat_slab_deflections']:
    m = re.search(r'def ' + fn + r'\s*\(', text)
    if m:
        start = m.start()
        end = text.find('):', start)
        print(f"=== {fn} ===")
        print(text[start:end+2])
        print()
