with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'st.expander' in line:
            print(f'{i+1}: {line.strip()[:100]}')
