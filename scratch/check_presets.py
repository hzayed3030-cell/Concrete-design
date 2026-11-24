import json
with open('m1_manual_boq_presets.json', 'r', encoding='utf-8') as f:
    presets = json.load(f)
print('Presets count:', len(presets))
for i, p in enumerate(presets, 1):
    print(f"{i}. {p['label']} -> {p['unit']} @ {p['unit_price']}")
