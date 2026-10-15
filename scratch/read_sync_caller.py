import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(12240, 12285):
    print(f"{i+1}: {lines[i]}", end='')
