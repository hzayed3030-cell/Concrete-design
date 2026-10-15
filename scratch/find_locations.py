import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Total lines:", len(lines))

for i, l in enumerate(lines):
    if 'def render(' in l:
        print(f"render() defined at line {i+1}")
    if '_render_fs_interactive_plan' in l:
        print(f"_render_fs_interactive_plan called or defined at line {i+1}")
    if 'exp_stl = st.expander' in l:
        print(f"Steel Layout expander at line {i+1}")
