# -*- coding: utf-8 -*-
import ast

with open("scratch/generate_helpers_code.py", "r", encoding="utf-8") as f:
    hc = f.read()

# Get the code inside get_helpers_code()
idx1 = hc.find("return '''") + len("return '''")
idx2 = hc.rfind("'''")
helpers_core = hc[idx1:idx2]

with open("scratch/apply_flat_slab_boq.py", "r", encoding="utf-8") as f:
    af = f.read()

# Now combine helpers_core + cw_presets_func + cw_manual_func
# Let's test this in a python script
test_script = f"""
import os, json, math, re, io, html, uuid
import streamlit as st
from modules import settings as S

{helpers_core}
"""

ast.parse(test_script)
print("Combined helpers AST OK!")
