import json

with open('profiles.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Root keys:', list(data.keys()))
if 'profiles' in data:
    for pname in list(data['profiles'].keys())[:3]:
        pdata = data['profiles'][pname]
        beams = pdata.get('fs_drop_beams', [])
        print(f'Profile {pname}: {len(beams)} drop beams')
        if beams:
            b0 = beams[0]
            print('  sample beam:', {k: b0[k] for k in ['id', 'p1_grid', 'p2_grid', 'axis_type', 'axis_name', 'axis_index'] if k in b0})
