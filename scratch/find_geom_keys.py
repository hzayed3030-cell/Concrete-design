with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if any(k in l for k in ['_fs_last_geom_key', '_geometry_key', 'fs_drop_beams']):
        print(f'{i+1}: {l.strip()[:100]}')
