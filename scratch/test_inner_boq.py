# -*- coding: utf-8 -*-
"""
Test inner BOQ replacement block for flat_slab.py
"""
import ast

with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
    text = f.read()

# Check start and end of the block to replace inside render()
p_start = text.find('# ── جسر المزامنة الفورية لتوصيفات البنود (Hidden Sync Bridge) ──')
p_end = text.find('# ── 💾 SAVE & EXPORT COMPLETE CALCULATION SHEET (COLLAPSED EXPANDER) ────────')

print(f"p_start: {p_start}, p_end: {p_end}, length: {p_end - p_start}")
