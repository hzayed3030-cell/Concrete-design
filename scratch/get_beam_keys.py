import re
with open('modules/drop_beams_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()
keys = set(re.findall(r'"([a-zA-Z0-9_]+)"\s*:', text))
beam_keys = [k for k in keys if any(w in k for w in ['grid', 'axis', 'supp', 'p1', 'p2', 'coord', 'span'])]
print('Relevant keys in drop_beams_engine:', sorted(beam_keys))
