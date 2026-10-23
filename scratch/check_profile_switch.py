with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(15150, 15260):
    if any(k in lines[i] for k in ['profile', 'active_', 'S.', 'cfg']):
        print(f'{i+1}: {lines[i].strip()[:90]}')
