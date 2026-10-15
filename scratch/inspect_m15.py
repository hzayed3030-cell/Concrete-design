import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/module_15_masonry_plaster.py', 'r', encoding='utf-8') as f:
    text = f.read()

print("Module 15 length:", len(text))

# Let's search for delete confirmation / modal / buttons / drop beams / walls / etc.
del_matches = re.findall(r'.*(?:delete|حذف|تأكيد|confirm).*', text, re.IGNORECASE)
print("Delete/confirm matches count:", len(del_matches))
for m in del_matches[:15]:
    if len(m.strip()) < 120:
        print("  ", m.strip())

# Search for UI sections or drawing tool activation
draw_matches = re.findall(r'.*(?:draw|إسقاط|رسم|mouse|فأرة).*', text, re.IGNORECASE)
print("Draw/mouse matches count:", len(draw_matches))
for m in draw_matches[:15]:
    if len(m.strip()) < 120:
        print("  ", m.strip())
