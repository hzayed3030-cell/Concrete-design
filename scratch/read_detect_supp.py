with open('modules/drop_beams_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def detect_support_at_point' in l:
        print('detect_support_at_point at', i+1)
        for j in range(i, min(i+100, len(lines))):
            print(f'{j+1}: {lines[j].strip()[:90]}')
        break
