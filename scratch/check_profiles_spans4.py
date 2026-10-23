import json

with open('profiles.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for pname, pdata in data.get('profiles', {}).items():
    beams = pdata.get('fs_drop_beams', [])
    if beams:
        print(f'Found {len(beams)} drop beams in profile!')
        b0 = beams[0]
        res = {k: b0.get(k) for k in ['id', 'p1_grid', 'p2_grid', 'axis_type', 'axis_name', 'axis_index']}
        print('  sample beam:', json.dumps(res))
        break
else:
    print('No profiles currently have beams saved.')
