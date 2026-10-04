import re

with open('modules/settings.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if line.startswith('def save_settings'):
            print(f"save_settings defined at line {i+1}")
            break
