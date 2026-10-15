import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/module_15_masonry_plaster.py', 'r', encoding='utf-8') as f:
    text = f.read()

m = re.search(r'def _render_floating_delete_panel', text)
if m:
    start = m.start()
    print(text[start:start+2500])
