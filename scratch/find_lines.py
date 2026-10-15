import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

for term in ['def generate_flat_slab_sketch', 'def generate_flat_slab_master_steel_layout_sketch', 'def calculate_flat_slab_deflections', 'def _render_fs_interactive_plan', 'def _handle_fs_sync_payload', 'def _section_fs_add_columns']:
    m = re.search(r'' + term, text)
    if m:
        line_num = text[:m.start()].count('\n') + 1
        print(f"{term} is at line {line_num}")
