with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if any(k in l for k in ['_fs_Lx_spans', '_fs_Ly_spans', 'prev_lx', 'last_lx', 'prev_spans']):
        print(f'{i+1}: {l.strip()[:100]}')
