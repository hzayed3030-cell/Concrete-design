import json

with open('profiles.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for prof_name, prof_data in list(data.items())[:3]:
    print('Profile:', prof_name)
    lx_keys = [k for k in prof_data.keys() if 'lx' in k.lower() or 'ly' in k.lower() or 'beam' in k.lower() or 'span' in k.lower()]
    print('  Keys:', lx_keys)
    if 'fs_drop_beams' in prof_data:
        beams = prof_data['fs_drop_beams']
        print(f'  fs_drop_beams count: {len(beams)}')
        if beams:
            b0 = beams[0]
            print('  sample beam:', {k: b0[k] for k in ['id', 'p1_grid', 'p2_grid', 'axis_type', 'axis_name'] if k in b0})
