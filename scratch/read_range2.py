import sys

sys.stdout.reconfigure(encoding='utf-8')
with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx in range(11480, 11600):
    print(f"{idx+1}: {lines[idx]}", end='')
