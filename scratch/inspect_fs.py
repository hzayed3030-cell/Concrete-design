import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    text = f.read()

print("File loaded successfully. Length:", len(text))

# Find how beams are referenced currently (if any)
beam_matches = re.findall(r'.*beam.*', text, re.IGNORECASE)
print("Beam occurrences:", len(beam_matches))
for b in beam_matches[:10]:
    print("  ", b.strip())
