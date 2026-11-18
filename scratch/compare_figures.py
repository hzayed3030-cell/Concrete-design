import sys
import json
import io
import base64
sys.path.insert(0, '.')

with open('profiles.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

p1 = d['profiles'].get('Control room (نسخة)', {}).get('data', {})
p2 = d['profiles'].get('Control room (مباني)', {}).get('data', {})

# 1. Flat Slab Plan
from modules.flat_slab import generate_flat_slab_sketch, get_flat_slab_columns, sync_all_columns_with_models

n_lx = p1.get('fs_n_lx', 0)
n_ly = p1.get('fs_n_ly', 0)
lx = [p1.get(f'fs_lx_{k}', 6.0) for k in range(n_lx)]
ly = [p1.get(f'fs_ly_{k}', 6.0) for k in range(n_ly)]
cantilevers = {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0}

active_cols, _, _, _, _ = get_flat_slab_columns(
    lx, ly,
    bc_cm=float(p1.get('slab_bc', 30.0)),
    tc_cm=float(p1.get('slab_tc', 50.0)),
    removed_ids=p1.get('fs_removed_cols'),
    col_transforms=p1.get('fs_col_transforms'),
    edge_columns=p1.get('fs_edge_columns'),
    placed_cols=p1.get('fs_placed_cols'),
    zero_col_mode=bool(p1.get('fs_zero_col_mode', False)),
    col_props=p1.get('fs_col_props')
)
confirmed = p1.get('fs_confirmed_col_dims') or {}
active_cols = sync_all_columns_with_models(active_cols, confirmed)

fig_fs = generate_flat_slab_sketch(
    lx, ly, cantilevers,
    active_cols=active_cols,
    col_transforms=p1.get('fs_col_transforms'),
    col_props=p1.get('fs_col_props'),
)
print("=== Flat Slab Figure ===")
print("Figure size (inches):", fig_fs.get_size_inches())
print("DPI:", fig_fs.dpi)
ax_fs = fig_fs.axes[0]
print("xlim:", ax_fs.get_xlim())
print("ylim:", ax_fs.get_ylim())

# 2. Module 15 Plan
# We need to simulate streamlit session state for module 15
import streamlit as st
m15 = p2.get('module_15_masonry_plaster', {})
st.session_state["m15_x_axes"] = m15.get("x_axes")
st.session_state["m15_y_axes"] = m15.get("y_axes")
st.session_state["m15_col_placed"] = {tuple(c) for c in m15.get("col_placed", [])}
st.session_state["m15_col_removed"] = {tuple(c) for c in m15.get("col_removed", [])}
st.session_state["m15_wall_removed"] = set()
st.session_state["m15_walls_placed"] = []
st.session_state["m15_wall_thickness"] = {}
st.session_state["m15_col_props"] = {tuple(int(x) for x in k.split(',')): v for k, v in m15.get("col_props", {}).items()}
st.session_state["m15_col_dirs"] = {tuple(int(x) for x in k.split(',')): v for k, v in m15.get("col_dirs", {}).items()}
st.session_state["m15_col_shifts"] = {tuple(int(x) for x in k.split(',')): v for k, v in m15.get("col_shifts", {}).items()}
st.session_state["m15_col_shifted"] = {tuple(int(x) for x in k.split(',')): tuple(v) for k, v in m15.get("col_shifted", {}).items()}
st.session_state["m15_windows"] = {}
st.session_state["m15_doors"] = {}
st.session_state["m15_parapet_walls"] = set()
st.session_state["m15_named_spaces"] = []

from modules.module_15_masonry_plaster import _draw_plan
buf_m15 = _draw_plan(with_dim=True)
print("\n=== Module 15 Plan ===")
print("Buffer size (bytes):", len(buf_m15.getvalue()))
