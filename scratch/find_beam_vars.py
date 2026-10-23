with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'(\w*beam\w*)\s*=', text, re.IGNORECASE)
print('beam variables:', set(matches))
