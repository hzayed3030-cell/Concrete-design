with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('scratch/sketch_calls.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if any(fn in line for fn in [
            'generate_flat_slab_sketch',
            'generate_flat_slab_punching_shear_sketch',
            'generate_flat_slab_moment_contour',
            'generate_flat_slab_deflection',
            'generate_flat_slab_plan_sketch',
            '_fig_to_b64',
            'plt.figure',
            'plt.subplots',
            'st.pyplot',
        ]):
            out.write(f'{i+1}: {line.strip()[:90]}\n')
