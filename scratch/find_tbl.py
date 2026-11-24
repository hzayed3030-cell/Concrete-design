# -*- coding: utf-8 -*-
with open('modules/module_15_masonry_plaster.py', 'r', encoding='utf-8') as f:
    m15 = f.read()

p_tbl = m15.find('id="m15-boq-table"')
p_script = m15.find('<script>', p_tbl)
p_script_end = m15.find('</script>', p_script)
print(m15[p_script+17000:p_script_end+9])
