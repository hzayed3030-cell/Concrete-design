import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(1120, 1160):
    print(f"{i+1}: {lines[i]}", end='')
