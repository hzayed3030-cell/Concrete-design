# -*- coding: utf-8 -*-
"""
Script to apply the complete BOQ and Takeoff patch to modules/flat_slab.py
"""
import ast, os, re

def main():
    with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
        flat_slab_src = f.read()

    # 1. Read helpers from test_combined_helpers.py
    with open("scratch/test_combined_helpers.py", "r", encoding="utf-8") as f:
        helpers_content = f.read()
    # Strip the import test lines from top and bottom
    h_start = helpers_content.find("# ═════════════════════════════════════════════════════════════════════════════")
    helpers_src = helpers_content[h_start:]

    # Also extract cw_presets_func and cw_manual_func
    with open("scratch/apply_full_patch_to_flat_slab.py", "r", encoding="utf-8") as f:
        app_full = f.read()

    with open("modules/module_15_masonry_plaster.py", "r", encoding="utf-8") as f:
        m15 = f.read()

    p1 = m15.find("def _render_presets_library_manager(presets: list):")
    p2 = m15.find("def _render_manual_boq_items_manager():")
    p3 = m15.find("def _section_plaster_boq")
    presets_src = m15[p1:p2]
    manual_src = m15[p2:p3]

    cw_presets_func = presets_src.replace(
        "def _render_presets_library_manager(presets: list):",
        "def _render_cw_presets_library_manager(presets: list, prefix: str = ''):"
    )
    cw_presets_func = cw_presets_func.replace('m15-preset-library-marker', 'm1-preset-library-marker')
    cw_presets_func = cw_presets_func.replace('"_m15_fill_add_preset"', 'f"_{prefix}m1_fill_add_preset"')
    cw_presets_func = cw_presets_func.replace('"m15_man_new_name"', 'f"{prefix}m1_man_new_name"')
    cw_presets_func = cw_presets_func.replace('"m15_man_new_unit"', 'f"{prefix}m1_man_new_unit"')
    cw_presets_func = cw_presets_func.replace('"m15_man_new_price"', 'f"{prefix}m1_man_new_price"')
    cw_presets_func = cw_presets_func.replace('"m15_man_new_desc"', 'f"{prefix}m1_man_new_desc"')
    cw_presets_func = cw_presets_func.replace('"m15_add_preset_name"', 'f"{prefix}m1_add_preset_name"')
    cw_presets_func = cw_presets_func.replace('"m15_add_preset_unit"', 'f"{prefix}m1_add_preset_unit"')
    cw_presets_func = cw_presets_func.replace('"m15_add_preset_price"', 'f"{prefix}m1_add_preset_price"')
    cw_presets_func = cw_presets_func.replace('"m15_add_preset_desc"', 'f"{prefix}m1_add_preset_desc"')
    cw_presets_func = cw_presets_func.replace('"m15_btn_save_new_preset"', 'f"{prefix}m1_btn_save_new_preset"')
    cw_presets_func = cw_presets_func.replace('"m15_btn_fill_from_current"', 'f"{prefix}m1_btn_fill_from_current"')
    cw_presets_func = cw_presets_func.replace('"m15_edit_preset_sel"', 'f"{prefix}m1_edit_preset_sel"')
    cw_presets_func = cw_presets_func.replace('"_m15_last_edit_preset"', 'f"_{prefix}m1_last_edit_preset"')
    cw_presets_func = cw_presets_func.replace('"m15_edit_preset_name"', 'f"{prefix}m1_edit_preset_name"')
    cw_presets_func = cw_presets_func.replace('"m15_edit_preset_unit"', 'f"{prefix}m1_edit_preset_unit"')
    cw_presets_func = cw_presets_func.replace('"m15_edit_preset_price"', 'f"{prefix}m1_edit_preset_price"')
    cw_presets_func = cw_presets_func.replace('"m15_edit_preset_desc"', 'f"{prefix}m1_edit_preset_desc"')
    cw_presets_func = cw_presets_func.replace('"m15_btn_save_edit_preset"', 'f"{prefix}m1_btn_save_edit_preset"')
    cw_presets_func = cw_presets_func.replace('"m15_del_preset_sel"', 'f"{prefix}m1_del_preset_sel"')
    cw_presets_func = cw_presets_func.replace('"m15_btn_del_preset"', 'f"{prefix}m1_btn_del_preset"')
    cw_presets_func = cw_presets_func.replace('"m15_man_preset_sel"', 'f"{prefix}m1_man_preset_sel"')
    cw_presets_func = cw_presets_func.replace('"_m15_last_manual_preset"', 'f"_{prefix}m1_last_manual_preset"')
    cw_presets_func = cw_presets_func.replace('_save_manual_boq_presets_list', '_save_cw_manual_boq_presets_list')
    cw_presets_func = cw_presets_func.replace('MANUAL_BOQ_UNIT_OPTIONS', 'CW_MANUAL_BOQ_UNIT_OPTIONS')

    cw_manual_func = manual_src.replace(
        "def _render_manual_boq_items_manager():",
        "def _render_cw_manual_boq_items_manager(cur_factor=1.00, prefix: str = ''):"
    )
    cw_manual_func = cw_manual_func.replace(
        'cur_factor = float(st.session_state.get("m15_input_plaster_qty_factor", 1.20))',
        'cur_factor = float(cur_factor)'
    )
    cw_manual_func = cw_manual_func.replace("_get_manual_boq_items_list()", "_get_cw_manual_boq_items_list(prefix=prefix)")
    cw_manual_func = cw_manual_func.replace("_get_manual_boq_presets_list()", "_get_cw_manual_boq_presets_list()")
    cw_manual_func = cw_manual_func.replace("_save_manual_boq_presets_list", "_save_cw_manual_boq_presets_list")
    cw_manual_func = cw_manual_func.replace("_persist_manual_boq_items(manual_items)", "_persist_cw_manual_boq_items(manual_items, prefix=prefix)")
    cw_manual_func = cw_manual_func.replace("_persist_manual_boq_items(new_items)", "_persist_cw_manual_boq_items(new_items, prefix=prefix)")
    cw_manual_func = cw_manual_func.replace("MANUAL_BOQ_UNIT_OPTIONS", "CW_MANUAL_BOQ_UNIT_OPTIONS")
    cw_manual_func = cw_manual_func.replace("_render_presets_library_manager(presets)", "# _render_cw_presets_library_manager is called independently in Section 2")

    f_marker = cw_manual_func.find('# ═════════════════════════════════════════════════════════════════════════\n    #  ثالثاً: صندوق معامل الزيادة العام لكافة بنود المقايسة')
    if f_marker != -1:
        cw_manual_func = cw_manual_func[:f_marker] + "    return\n"

    cw_manual_func = cw_manual_func.replace('"m15_man_', 'f"{prefix}m1_man_')
    cw_manual_func = cw_manual_func.replace('"_m15_', 'f"_{prefix}m1_')
    cw_manual_func = cw_manual_func.replace("'m15_man_", "f'{prefix}m1_man_")
    cw_manual_func = cw_manual_func.replace('table#m15-manual-boq-table', 'table#m1-manual-boq-table')
    cw_manual_func = cw_manual_func.replace('m15-manual-boq-table', 'm1-manual-boq-table')
    cw_manual_func = cw_manual_func.replace('m15_man_boq_col_widths_v2', 'm1_man_boq_col_widths_v1')
    cw_manual_func = cw_manual_func.replace('m15_man_boq_row_heights_v2', 'm1_man_boq_row_heights_v1')
    cw_manual_func = cw_manual_func.replace("manual_items = _get_cw_manual_boq_items_list(prefix=prefix)", "_cw_sync_aria_lbl = f'{prefix}cw_boq_sync_payload'\n    manual_items = _get_cw_manual_boq_items_list(prefix=prefix)")
    cw_manual_func = cw_manual_func.replace('m15_3d_sync_payload', '{_cw_sync_aria_lbl}')

    all_top_helpers = f"""
{helpers_src}

{cw_presets_func}

{cw_manual_func}
"""

    # Insert all_top_helpers before `def render(is_standalone: bool = False):`
    render_idx = flat_slab_src.find("def render(is_standalone: bool = False):")
    if render_idx == -1:
        raise ValueError("Could not find def render in flat_slab.py")

    new_flat_slab_src = flat_slab_src[:render_idx] + all_top_helpers + "\n\n" + flat_slab_src[render_idx:]

    print("Top helpers inserted successfully. Testing AST of patched source...")
    ast.parse(new_flat_slab_src)
    print("Patched source AST OK! Writing to test file...")

    with open("scratch/flat_slab_patched_helpers.py", "w", encoding="utf-8") as f:
        f.write(new_flat_slab_src)

if __name__ == "__main__":
    main()
