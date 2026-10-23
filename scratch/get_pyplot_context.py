with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('scratch/pyplot_context.txt', 'w', encoding='utf-8') as out:
    for i in range(16000, 19000):
        l = lines[i]
        if any(term in l for term in ['st.expander', 'st.pyplot', 'generate_', 'fig =', 'fig,', 'plt.figure']):
            out.write(f'{i+1}: {l.strip()[:100]}\n')
