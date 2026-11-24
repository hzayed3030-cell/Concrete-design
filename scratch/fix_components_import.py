# -*- coding: utf-8 -*-
"""
Fix UnboundLocalError: components in modules/flat_slab.py
"""
import ast, py_compile

def main():
    with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Add module-level import if not present
    if "import streamlit.components.v1 as components\n" not in src[:2000]:
        target1 = "import streamlit as st\nimport pandas as pd"
        rep1 = "import streamlit as st\nimport streamlit.components.v1 as components\nimport pandas as pd"
        if target1 in src:
            src = src.replace(target1, rep1, 1)
            print("Added module-level import of components.")
        else:
            print("Warning: target1 not found")

    # 2. Add import at the top of def render(is_standalone: bool = False):
    target2 = "def render(is_standalone: bool = False):\n    inject_module1_drawings_pan_zoom()"
    rep2 = "def render(is_standalone: bool = False):\n    import streamlit.components.v1 as components\n    inject_module1_drawings_pan_zoom()"
    if target2 in src:
        src = src.replace(target2, rep2, 1)
        print("Added import of components at start of render().")
    else:
        print("Warning: target2 not found")

    # 3. Add import at top of def _render_cw_manual_boq_items_manager
    target3 = "def _render_cw_manual_boq_items_manager(cur_factor=1.00, prefix: str = ''):\n    \"\"\""
    rep3 = "def _render_cw_manual_boq_items_manager(cur_factor=1.00, prefix: str = ''):\n    import streamlit.components.v1 as components\n    \"\"\""
    if target3 in src:
        src = src.replace(target3, rep3, 1)
        print("Added import of components at start of _render_cw_manual_boq_items_manager.")
    else:
        print("Warning: target3 not found")

    # 4. Add import directly before components.html(_cw_full_table_html, ...)
    target4 = "            components.html(_cw_full_table_html, height=_cw_tbl_calc_height, scrolling=False)"
    rep4 = "            import streamlit.components.v1 as components\n            components.html(_cw_full_table_html, height=_cw_tbl_calc_height, scrolling=False)"
    if target4 in src:
        src = src.replace(target4, rep4, 1)
        print("Added local import directly before components.html(_cw_full_table_html).")
    else:
        print("Warning: target4 not found")

    print("Checking AST of patched flat_slab.py...")
    ast.parse(src)
    print("AST parse OK!")

    with open("modules/flat_slab.py", "w", encoding="utf-8") as f:
        f.write(src)

    print("Compiling modules/flat_slab.py with py_compile...")
    py_compile.compile("modules/flat_slab.py", doraise=True)
    print("py_compile successful!")

if __name__ == "__main__":
    main()
