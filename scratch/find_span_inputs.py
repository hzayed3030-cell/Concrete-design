with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if any(k in l for k in ['fs_lx_', 'fs_ly_', 'Lx_spans', 'Ly_spans', 'number_input']) and ('span' in l.lower() or 'بحر' in l or 'lx' in l.lower() or 'ly' in l.lower()):
        if any(w in l for w in ['st.number_input', 'st.slider', 'st.text_input', '= [', 'append', 'cfg_val']):
            print(f'{i+1}: {l.strip()[:100]}')
