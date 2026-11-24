# -*- coding: utf-8 -*-
import re

with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find def render(is_standalone: bool = False):
render_start = None
for i, line in enumerate(lines, 1):
    if line.startswith("def render(is_standalone: bool = False):"):
        render_start = i
        break

print(f"render() starts at line {render_start}, total lines: {len(lines)}")

# Find design button
for i in range(render_start, len(lines) + 1):
    if "إبدأ التصميم الإنشائي" in lines[i - 1] or "ابدأ التصميم الإنشائي" in lines[i - 1]:
        print(f"Design button mention at line {i}: {lines[i-1].strip()[:120]}")

print("\n=== ALL EXPANDERS IN render() ===")
for i in range(render_start, len(lines) + 1):
    line = lines[i - 1]
    if "st.expander(" in line:
        indent = len(line) - len(line.lstrip())
        snippet = "".join(lines[i - 1 : min(i + 5, len(lines))]).replace("\n", " ")
        snippet = re.sub(r"\s+", " ", snippet).strip()
        print(f"L{i:5d} [ind={indent:2d}]: {snippet[:160]}")

print("\n=== ALL PYPLOT / IMAGE / 3D / COMPONENTS.HTML IN render() ===")
patterns = ["st.pyplot(", "st.image(", "components.html(", "st.plotly_chart(", "render_3d", "BIM", "viewer", "draw_"]
for i in range(render_start, len(lines) + 1):
    line = lines[i - 1]
    stripped = line.strip()
    if stripped.startswith("#"):
        continue
    if any(p in line for p in ["st.pyplot(", "st.image(", "components.html(", "st.plotly_chart(", "render_3d_"]):
        indent = len(line) - len(line.lstrip())
        print(f"L{i:5d} [ind={indent:2d}]: {stripped[:140]}")
