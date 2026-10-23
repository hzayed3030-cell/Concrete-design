import json

with open('profiles.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for pname in list(data.get('profiles', {}).keys())[:5]:
    pdata = data['profiles'][pname]
    beams = pdata.get('fs_drop_beams', [])
    print(f'Profile has {len(beams)} drop beams')
    if beams:
        b0 = beams[0]
        res = {k: b0.get(k) for k in ['id', 'p1_grid', 'p2_grid', 'axis_type', 'axis_name', 'axis_index']}
        print('  sample beam:', json.dumps(res))
