# -*- coding: utf-8 -*-
"""
Apply fixes requested by user:
1. Remove redundant outer expanders for Presets Library and Manual Items Manager (single expander each).
2. Clean up any remaining m15_ keys in manual manager.
3. Rename the main expander to: جداول الحصر والتكلفة لجميع البنود
"""
import ast, py_compile

def main():
    with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Remove duplicate outer expanders in render()
    old_call_block = """            # ═════════════════════════════════════════════════════════════════════════
            #  2. إدارة وتخصيص مكتبة القوالب الجاهزة (12 قالب متاح لجميع المشاريع)
            # ═════════════════════════════════════════════════════════════════════════
            _cw_presets = _get_cw_manual_boq_presets_list()
            with st.expander(
                f"⚙️ 📚 إدارة وتخصيص مكتبة القوالب الجاهزة ({len(_cw_presets)} قالب متاح لجميع المشاريع)",
                expanded=False,
            ):
                _render_cw_presets_library_manager(_cw_presets, prefix=prefix)

            # ═════════════════════════════════════════════════════════════════════════
            #  3. إضافة وإدارة بنود الحصر اليدوية الإضافية (رخام سلالم، حجر فرعوني، وبنود أخرى)
            # ═════════════════════════════════════════════════════════════════════════
            with st.expander(
                "➕ إضافة وإدارة بنود الحصر اليدوية الإضافية (رخام سلالم، حجر فرعوني، وبنود أخرى)",
                expanded=False,
            ):
                _render_cw_manual_boq_items_manager(cur_factor=cw_qty_factor, prefix=prefix)"""

    new_call_block = """            # ═════════════════════════════════════════════════════════════════════════
            #  2. إدارة وتخصيص مكتبة القوالب الجاهزة (12 قالب متاح لجميع المشاريع)
            # ═════════════════════════════════════════════════════════════════════════
            _cw_presets = _get_cw_manual_boq_presets_list()
            _render_cw_presets_library_manager(_cw_presets, prefix=prefix)

            # ═════════════════════════════════════════════════════════════════════════
            #  3. إضافة وإدارة بنود الحصر اليدوية الإضافية (رخام سلالم، حجر فرعوني، وبنود أخرى)
            # ═════════════════════════════════════════════════════════════════════════
            _render_cw_manual_boq_items_manager(cur_factor=cw_qty_factor, prefix=prefix)"""

    if old_call_block in src:
        src = src.replace(old_call_block, new_call_block, 1)
        print("Successfully removed redundant outer expanders for sections 2 and 3.")
    else:
        print("Warning: old_call_block not found exactly.")

    # 2. Rename outer expander
    old_exp_title = 'f"🏗️ حصر شامل لجميع الأعمال الخاصة بالمبنى{_ftg_exp_suf}"'
    new_exp_title = 'f"جداول الحصر والتكلفة لجميع البنود{_ftg_exp_suf}"'
    if old_exp_title in src:
        src = src.replace(old_exp_title, new_exp_title, 1)
        print("Successfully renamed main expander to 'جداول الحصر والتكلفة لجميع البنود'.")
    else:
        print("Warning: old_exp_title not found.")

    # 3. Clean up manual manager internal factors and keys
    p_man = src.find("def _render_cw_manual_boq_items_manager")
    p_render = src.find("def render(", p_man)
    if p_man != -1 and p_render != -1:
        man_part = src[p_man:p_render]
        
        # Replace m15_manual_boq_items
        man_part = man_part.replace(
            'st.session_state["m15_manual_boq_items"] = [dict(x) for x in manual_items]',
            '_persist_cw_manual_boq_items(manual_items, prefix=prefix)'
        )
        
        # Replace factor reading with passed cur_factor
        old_factor_code = """    cur_factor = float(
        st.session_state.get(
            "m15_input_plaster_qty_factor",
            st.session_state.get("m15_plaster_qty_factor", 1.00),
        )
    )
    plaster_qty_factor = cur_factor"""
        new_factor_code = """    cur_factor = float(cur_factor)
    plaster_qty_factor = cur_factor"""
        if old_factor_code in man_part:
            man_part = man_part.replace(old_factor_code, new_factor_code)
            print("Successfully updated cur_factor in manual manager.")

        # Replace key="m15_quick_save_as_preset"
        man_part = man_part.replace('key="m15_quick_save_as_preset"', 'key=f"{prefix}m1_quick_save_as_preset"')

        src = src[:p_man] + man_part + src[p_render:]

    # Validate AST
    print("Validating AST...")
    ast.parse(src)
    print("AST parse OK!")

    with open("modules/flat_slab.py", "w", encoding="utf-8") as f:
        f.write(src)

    print("Compiling modules/flat_slab.py with py_compile...")
    py_compile.compile("modules/flat_slab.py", doraise=True)
    print("All fixes applied and verified successfully!")

if __name__ == "__main__":
    main()
