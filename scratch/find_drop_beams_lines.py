with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'fs_drop_beams' in l:
        print(f'{i+1}: {l.strip()[:100]}')
