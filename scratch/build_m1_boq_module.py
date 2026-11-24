# -*- coding: utf-8 -*-
"""
Script to generate and validate the Module 1 BOQ additions.
"""
import ast

with open("modules/module_15_masonry_plaster.py", "r", encoding="utf-8") as f:
    m15_text = f.read()

# Extract _render_presets_library_manager from m15 and adapt to Module 1
p1 = m15_text.find("def _render_presets_library_manager(presets: list):")
p2 = m15_text.find("def _render_manual_boq_items_manager():")
presets_code = m15_text[p1:p2]

# Replace function name and keys
cw_presets_code = presets_code.replace("def _render_presets_library_manager(presets: list):", "def _render_cw_presets_library_manager(presets: list, prefix: str = ''):")
cw_presets_code = cw_presets_code.replace('m15-preset-library-marker', 'm1-preset-library-marker')
cw_presets_code = cw_presets_code.replace('"_m15_fill_add_preset"', 'f"_{prefix}m1_fill_add_preset"')
cw_presets_code = cw_presets_code.replace('"m15_man_new_name"', 'f"{prefix}m1_man_new_name"')
cw_presets_code = cw_presets_code.replace('"m15_man_new_unit"', 'f"{prefix}m1_man_new_unit"')
cw_presets_code = cw_presets_code.replace('"m15_man_new_price"', 'f"{prefix}m1_man_new_price"')
cw_presets_code = cw_presets_code.replace('"m15_man_new_desc"', 'f"{prefix}m1_man_new_desc"')
cw_presets_code = cw_presets_code.replace('"m15_add_preset_name"', 'f"{prefix}m1_add_preset_name"')
cw_presets_code = cw_presets_code.replace('"m15_add_preset_unit"', 'f"{prefix}m1_add_preset_unit"')
cw_presets_code = cw_presets_code.replace('"m15_add_preset_price"', 'f"{prefix}m1_add_preset_price"')
cw_presets_code = cw_presets_code.replace('"m15_add_preset_desc"', 'f"{prefix}m1_add_preset_desc"')
cw_presets_code = cw_presets_code.replace('"m15_btn_save_new_preset"', 'f"{prefix}m1_btn_save_new_preset"')
cw_presets_code = cw_presets_code.replace('"m15_btn_fill_from_current"', 'f"{prefix}m1_btn_fill_from_current"')
cw_presets_code = cw_presets_code.replace('"m15_edit_preset_sel"', 'f"{prefix}m1_edit_preset_sel"')
cw_presets_code = cw_presets_code.replace('"_m15_last_edit_preset"', 'f"_{prefix}m1_last_edit_preset"')
cw_presets_code = cw_presets_code.replace('"m15_edit_preset_name"', 'f"{prefix}m1_edit_preset_name"')
cw_presets_code = cw_presets_code.replace('"m15_edit_preset_unit"', 'f"{prefix}m1_edit_preset_unit"')
cw_presets_code = cw_presets_code.replace('"m15_edit_preset_price"', 'f"{prefix}m1_edit_preset_price"')
cw_presets_code = cw_presets_code.replace('"m15_edit_preset_desc"', 'f"{prefix}m1_edit_preset_desc"')
cw_presets_code = cw_presets_code.replace('"m15_btn_save_edit_preset"', 'f"{prefix}m1_btn_save_edit_preset"')
cw_presets_code = cw_presets_code.replace('"m15_del_preset_sel"', 'f"{prefix}m1_del_preset_sel"')
cw_presets_code = cw_presets_code.replace('"m15_btn_del_preset"', 'f"{prefix}m1_btn_del_preset"')
cw_presets_code = cw_presets_code.replace('"m15_man_preset_sel"', 'f"{prefix}m1_man_preset_sel"')
cw_presets_code = cw_presets_code.replace('"_m15_last_manual_preset"', 'f"_{prefix}m1_last_manual_preset"')
cw_presets_code = cw_presets_code.replace('_save_manual_boq_presets_list', '_save_cw_manual_boq_presets_list')
cw_presets_code = cw_presets_code.replace('MANUAL_BOQ_UNIT_OPTIONS', 'CW_MANUAL_BOQ_UNIT_OPTIONS')

print("cw_presets_code adapted. Parsing AST...")
ast.parse(cw_presets_code)
print("cw_presets_code AST OK!")
