with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if any(k in l for k in ['active_profile', 'switch_project', 'load_profile', 'select_profile']):
        print(f'{i+1}: {l.strip()[:90]}')
