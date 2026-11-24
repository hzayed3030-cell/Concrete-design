# -*- coding: utf-8 -*-
import re

with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

pat = re.compile(r"(_render_fs_zoomable_figure|st\.pyplot|st\.image|render_3d_bim_viewer|plt\.subplots|plt\.figure|make_subplots|st\.plotly_chart|draw_\w+|plot_\w+)")
for i in range(21355, len(lines) + 1):
    line = lines[i - 1]
    s = line.strip()
    if s.startswith("#") or s.startswith("def ") or s.startswith("from ") or s.startswith("import "):
        continue
    if pat.search(line):
        indent = len(line) - len(line.lstrip())
        print(f"L{i:5d} [ind={indent:2d}]: {s[:135]}")
