# -*- coding: utf-8 -*-
"""
Generate and test the complete inner BOQ replacement block for flat_slab.py
"""
import ast

def get_inner_boq_code():
    with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
        fs = f.read()

    p_start = fs.find('# ── جسر المزامنة الفورية لتوصيفات البنود (Hidden Sync Bridge) ──')
    p_end = fs.find('# ── 💾 SAVE & EXPORT COMPLETE CALCULATION SHEET (COLLAPSED EXPANDER) ────────')
    old_inner = fs[p_start:p_end]
    print(f"Old inner block length: {len(old_inner)}")
    return old_inner

if __name__ == '__main__':
    get_inner_boq_code()
