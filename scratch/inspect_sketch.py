import sys

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
m = re.search(r'def generate_flat_slab_sketch\(', text)
start = m.start()
# find end of generate_flat_slab_sketch
m_end = re.search(r'\ndef generate_flat_slab_data_card\(', text)
end = m_end.start()
print("generate_flat_slab_sketch spans lines:", text[:start].count('\n')+1, "to", text[:end].count('\n')+1)

sketch_code = text[start:end]
print("Lines count:", sketch_code.count('\n'))
# Search for return fig or axes
for l in sketch_code.split('\n'):
    if 'return ' in l:
        print("  Return line:", l.strip())
