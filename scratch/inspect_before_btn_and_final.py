# -*- coding: utf-8 -*-
import re

with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=== 1. DRAWINGS BEFORE LINE 21355 (INPUTS SECTION) ===")
pat = re.compile(r"(_render_fs_zoomable_figure|st\.pyplot|st\.image|render_3d|plt\.subplots|plt\.figure|draw_\w+|plot_\w+|generate_flat_slab\w*|savefig|_render_gb_interactive_viewer|components\.html)")
for i in range(19903, 21356):
    line = lines[i - 1]
    s = line.strip()
    if s.startswith("#") or s.startswith("def ") or s.startswith("from ") or s.startswith("import "):
        continue
    if pat.search(line):
        indent = len(line) - len(line.lstrip())
        print(f"L{i:5d} [ind={indent:2d}]: {s[:135]}")

print("\n=== 2. CHECK L26703-L27091 INDENTATION & VARIABLES ===")
for i in range(26703, 27092):
    line = lines[i - 1]
    indent = len(line) - len(line.lstrip())
    s = line.strip()
    if s and indent <= 16 and not s.startswith("#"):
        print(f"L{i:5d} [ind={indent:2d}]: {s[:120]}")
