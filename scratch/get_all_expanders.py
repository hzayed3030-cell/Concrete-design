with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('scratch/all_expanders.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if 'st.expander' in line:
            # get the next 3 lines to see expanded=
            snippet = ' '.join(l.strip() for l in lines[i:i+4])
            out.write(f'{i+1}: {snippet[:120]}\n')
