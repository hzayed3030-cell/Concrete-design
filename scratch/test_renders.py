# -*- coding: utf-8 -*-
"""
Test render functions for presets manager and manual boq items manager
"""
import ast

with open("modules/module_15_masonry_plaster.py", "r", encoding="utf-8") as f:
    m15_text = f.read()

p1 = m15_text.find("def _render_presets_library_manager(presets: list):")
p2 = m15_text.find("def _render_manual_boq_items_manager():")
p3 = m15_text.find("def _section_plaster_boq")

presets_src = m15_text[p1:p2]
manual_src = m15_text[p2:p3]

print(f"Presets length: {len(presets_src)}, Manual length: {len(manual_src)}")
