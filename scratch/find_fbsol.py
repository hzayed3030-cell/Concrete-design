with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def _find_beam_spans_on_line' in l:
        print('Found at', i+1)
