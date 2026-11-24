# -*- coding: utf-8 -*-
import re

with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

render_start = 19903

print("=== EXPANDERS WITH/WITHOUT on_change='rerun' AFTER LINE 21355 ===")
for i in range(21355, len(lines) + 1):
    line = lines[i - 1]
    if "st.expander(" in line:
        block = "".join(lines[i - 1 : min(i + 8, len(lines))])
        has_rerun = 'on_change="rerun"' in block or "on_change='rerun'" in block
        exp_val = re.search(r"expanded\s*=\s*([^,\)\n]+)", block)
        exp_str = exp_val.group(1).strip() if exp_val else "?"
        title_m = re.search(r'st\.expander\(\s*(f?"[^"]+"|\'[^\']+\')', block)
        title_str = title_m.group(1)[:85] if title_m else block.replace("\n", " ")[:85]
        print(f"L{i:5d} | rerun={str(has_rerun):5s} | expanded={exp_str:25s} | {title_str}")

print("\n=== ALL DRAWING/PLOT/VIEWER CALLS AFTER LINE 21355 ===")
draw_pat = re.compile(r"\b(draw_\w+|plot_\w+|render_3d\w*|st\.pyplot|st\.image|fig_to_b64|_render_\w*fig\w*|show_fig\w*)\s*\(")
for i in range(21355, len(lines) + 1):
    line = lines[i - 1]
    s = line.strip()
    if s.startswith("#") or s.startswith("def ") or s.startswith("from ") or s.startswith("import "):
        continue
    m = draw_pat.search(line)
    if m:
        indent = len(line) - len(line.lstrip())
        print(f"L{i:5d} [ind={indent:2d}]: {s[:130]}")
