import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'generate_flat_slab_sketch(' in l:
        print(f"Call at line {i+1}")
