# -*- coding: utf-8 -*-
"""
Helper to verify flat_slab BOQ code blocks syntax and integration.
"""
import ast

with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    orig_code = f.read()

print("Original code length:", len(orig_code))
ast.parse(orig_code)
print("Original code AST parse OK!")
