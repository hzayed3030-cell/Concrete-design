import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/module_15_masonry_plaster.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's search around pending_delete
for m in re.finditer(r'pending_delete', text):
    start = max(0, m.start() - 200)
    end = min(len(text), m.end() + 800)
    print("--- PENDING DELETE SNIPPET ---")
    print(text[start:end])
    print("\n" + "="*50 + "\n")
