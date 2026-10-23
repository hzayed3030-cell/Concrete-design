with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

heavy_calls = []
for i in range(16000, len(lines)):
    l = lines[i]
    if any(k in l for k in [
        'calculate_', 'compute_', 'generate_', 'optimize_',
        'solve_', 'analyze_', 'run_', 'recompute_', 'export_',
        'st.pyplot', 'plt.', 'savefig', 'to_b64'
    ]) and not l.strip().startswith('def '):
        heavy_calls.append(f"{i+1}: {l.strip()[:100]}")

with open('scratch/heavy_calls.txt', 'w', encoding='utf-8') as out:
    out.write('\n'.join(heavy_calls))

print(f"Found {len(heavy_calls)} potential heavy operations between 16000 and {len(lines)}")
