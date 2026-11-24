# -*- coding: utf-8 -*-
import ast, re

with open("modules/module_15_masonry_plaster.py", "r", encoding="utf-8") as f:
    m15 = f.read()

p1 = m15.find("def _render_presets_library_manager(presets: list):")
p2 = m15.find("def _render_manual_boq_items_manager():")
p3 = m15.find("def _section_plaster_boq")

presets_src = m15[p1:p2]
manual_src = m15[p2:p3]

# 1. Adapt presets_src
p_code = presets_src
p_code = p_code.replace("def _render_presets_library_manager(presets: list):", "def _render_cw_presets_library_manager(presets: list, prefix: str = ''):")
p_code = p_code.replace('m15-preset-library-marker', 'm1-preset-library-marker')
p_code = p_code.replace('"_m15_fill_add_preset"', 'f"_{prefix}m1_fill_add_preset"')
p_code = p_code.replace('"m15_man_new_name"', 'f"{prefix}m1_man_new_name"')
p_code = p_code.replace('"m15_man_new_unit"', 'f"{prefix}m1_man_new_unit"')
p_code = p_code.replace('"m15_man_new_price"', 'f"{prefix}m1_man_new_price"')
p_code = p_code.replace('"m15_man_new_desc"', 'f"{prefix}m1_man_new_desc"')
p_code = p_code.replace('"m15_add_preset_name"', 'f"{prefix}m1_add_preset_name"')
p_code = p_code.replace('"m15_add_preset_unit"', 'f"{prefix}m1_add_preset_unit"')
p_code = p_code.replace('"m15_add_preset_price"', 'f"{prefix}m1_add_preset_price"')
p_code = p_code.replace('"m15_add_preset_desc"', 'f"{prefix}m1_add_preset_desc"')
p_code = p_code.replace('"m15_btn_save_new_preset"', 'f"{prefix}m1_btn_save_new_preset"')
p_code = p_code.replace('"m15_btn_fill_from_current"', 'f"{prefix}m1_btn_fill_from_current"')
p_code = p_code.replace('"m15_edit_preset_sel"', 'f"{prefix}m1_edit_preset_sel"')
p_code = p_code.replace('"_m15_last_edit_preset"', 'f"_{prefix}m1_last_edit_preset"')
p_code = p_code.replace('"m15_edit_preset_name"', 'f"{prefix}m1_edit_preset_name"')
p_code = p_code.replace('"m15_edit_preset_unit"', 'f"{prefix}m1_edit_preset_unit"')
p_code = p_code.replace('"m15_edit_preset_price"', 'f"{prefix}m1_edit_preset_price"')
p_code = p_code.replace('"m15_edit_preset_desc"', 'f"{prefix}m1_edit_preset_desc"')
p_code = p_code.replace('"m15_btn_save_edit_preset"', 'f"{prefix}m1_btn_save_edit_preset"')
p_code = p_code.replace('"m15_del_preset_sel"', 'f"{prefix}m1_del_preset_sel"')
p_code = p_code.replace('"m15_btn_del_preset"', 'f"{prefix}m1_btn_del_preset"')
p_code = p_code.replace('"m15_man_preset_sel"', 'f"{prefix}m1_man_preset_sel"')
p_code = p_code.replace('"_m15_last_manual_preset"', 'f"_{prefix}m1_last_manual_preset"')
p_code = p_code.replace('_save_manual_boq_presets_list', '_save_cw_manual_boq_presets_list')
p_code = p_code.replace('MANUAL_BOQ_UNIT_OPTIONS', 'CW_MANUAL_BOQ_UNIT_OPTIONS')

# 2. Adapt manual_src
m_code = manual_src
m_code = m_code.replace("def _render_manual_boq_items_manager():", "def _render_cw_manual_boq_items_manager(cur_factor=1.00, prefix: str = ''):")
m_code = m_code.replace("_get_manual_boq_items_list()", "_get_cw_manual_boq_items_list(prefix=prefix)")
m_code = m_code.replace("_get_manual_boq_presets_list()", "_get_cw_manual_boq_presets_list()")
m_code = m_code.replace("_save_manual_boq_presets_list", "_save_cw_manual_boq_presets_list")
m_code = m_code.replace("_persist_manual_boq_items(manual_items)", "_persist_cw_manual_boq_items(manual_items, prefix=prefix)")
m_code = m_code.replace("_persist_manual_boq_items(new_items)", "_persist_cw_manual_boq_items(new_items, prefix=prefix)")
m_code = m_code.replace("_persist_manual_boq_items(", "_persist_cw_manual_boq_items(")
m_code = m_code.replace("MANUAL_BOQ_UNIT_OPTIONS", "CW_MANUAL_BOQ_UNIT_OPTIONS")

# Remove internal _render_presets_library_manager call since Section 2 is independent!
m_code = m_code.replace("_render_presets_library_manager(presets)", "# _render_cw_presets_library_manager is called independently in Section 2")

# Remove factor number input from bottom of manual_src since factor is in Section 1!
factor_marker = m_code.find('# ═════════════════════════════════════════════════════════════════════════\n    #  ثالثاً: صندوق معامل الزيادة العام لكافة بنود المقايسة')
if factor_marker != -1:
    m_code = m_code[:factor_marker] + "    return\n"

# Replace session keys in m_code
m_code = m_code.replace('"m15_man_', 'f"{prefix}m1_man_')
m_code = m_code.replace('"_m15_', 'f"_{prefix}m1_')
m_code = m_code.replace("'m15_man_", "f'{prefix}m1_man_")
m_code = m_code.replace('m15_3d_sync_payload', '{_cw_sync_aria_lbl}')
m_code = m_code.replace('table#m15-manual-boq-table', 'table#m1-manual-boq-table')
m_code = m_code.replace('m15-manual-boq-table', 'm1-manual-boq-table')
m_code = m_code.replace('m15_man_boq_col_widths_v2', 'm1_man_boq_col_widths_v1')
m_code = m_code.replace('m15_man_boq_row_heights_v2', 'm1_man_boq_row_heights_v1')

# Add _cw_sync_aria_lbl definition at start of m_code
m_code = m_code.replace("manual_items = _get_cw_manual_boq_items_list(prefix=prefix)", "_cw_sync_aria_lbl = f'{prefix}cw_boq_sync_payload'\n    manual_items = _get_cw_manual_boq_items_list(prefix=prefix)")

print("Testing AST of p_code...")
ast.parse(p_code)
print("p_code AST OK!")

print("Testing AST of m_code...")
ast.parse(m_code)
print("m_code AST OK!")
