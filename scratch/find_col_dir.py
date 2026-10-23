with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('scratch/col_dir_controls.txt', 'w', encoding='utf-8') as out:
    for i in range(13828, 14800):
        l = lines[i]
        if any(term in l for term in ['direction', 'rotation', 'اتجاه', 'ضرب', 'رأسي', 'أفقي', 'fs_col_transforms', 'col_transforms']):
            out.write(f'{i+1}: {l.strip()[:100]}\n')
