with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('scratch/sections_list.txt', 'w', encoding='utf-8') as out:
    for i in range(15600, len(lines)):
        line = lines[i]
        if line.startswith('    # ── ') or line.startswith('    with st.expander') or (line.strip().startswith('def ') and not line.startswith('        ')):
            out.write(f'{i+1}: {line.strip()[:80]}\n')
