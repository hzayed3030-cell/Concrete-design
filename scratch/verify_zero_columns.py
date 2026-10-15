import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')
import json
from modules.flat_slab import remap_columns_after_axis_insertion, get_flat_slab_columns

# Test 1: Verification on تدريب فلات سلاب profile
with open('profiles.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
p = d['profiles']['تدريب فلات سلاب']['data']

Lx = [p[f'fs_lx_{i}'] for i in range(p['fs_n_lx'])]
Ly = [p[f'fs_ly_{j}'] for j in range(p['fs_n_ly'])]

print('Testing تدريب فلات سلاب:')
print('Lx:', Lx)
print('Ly:', Ly)

act_cols, all_cols, _, _, _ = get_flat_slab_columns(
    Lx, Ly,
    bc_cm=p['slab_bc'],
    tc_cm=p['slab_tc'],
    removed_ids=set(p.get('fs_removed_cols', [])),
    col_transforms=p.get('fs_col_transforms', {}),
    edge_columns=p.get('fs_edge_columns', {}),
    placed_cols=p.get('fs_placed_cols', None),
    zero_col_mode=p.get('fs_zero_col_mode', False),
    col_props=p.get('fs_col_props', {}),
)

print(f'Total active columns: {len(act_cols)}')
assert len(act_cols) == 16, f'Expected 16 active columns, got {len(act_cols)}'

cols_on_y2 = [c for c in act_cols if c['i'] == 1]
print(f'Columns on Y2 (new axis): {len(cols_on_y2)}')
assert len(cols_on_y2) == 0, f'Expected ZERO columns on Y2, got {len(cols_on_y2)}'

c1 = next(c for c in act_cols if c['i'] == 0 and c['j'] == 0)
print(f"C1 properties: b={c1['b_cm']}, t={c1['t_cm']}, dir={c1['direction']}, sx={c1['shift_x']}")
assert c1['t_cm'] == 50.0
assert 'يمين' in c1['shift_x']

# Test 2: Simulate another split on X (e.g., splitting Lx[2]=6.0m into 2.0m + 4.0m)
# Current grid has 5 axes (nx=5) and 4 axes (ny=4).
# We split span 2 (between Y3 and Y4).
# New axis inserted at index 3 (new Y4).
# Previous Y4 and Y5 shift to Y5 and Y6.
new_rem, new_pl, new_pr, new_tr, new_ed, new_nx, new_ny = remap_columns_after_axis_insertion(
    axis_dir='X',
    span_index=2,
    old_nx=5,
    old_ny=4,
    removed_cols=p.get('fs_removed_cols', []),
    placed_cols=p.get('fs_placed_cols', None),
    col_props=p.get('fs_col_props', {}),
    col_trans=p.get('fs_col_transforms', {}),
    edge_cols=p.get('fs_edge_columns', {}),
    zero_col_mode=True,
    default_b=30.0,
    default_t=50.0,
)

new_Lx = [1.5, 4.5, 2.0, 4.0, 6.0]
act_cols_after, all_after, _, _, _ = get_flat_slab_columns(
    new_Lx, Ly,
    bc_cm=30, tc_cm=50,
    removed_ids=set(new_rem),
    col_transforms=new_tr,
    edge_columns=new_ed,
    placed_cols=new_pl,
    zero_col_mode=True,
    col_props=new_pr,
)

print(f'After 2nd split on X: total active columns = {len(act_cols_after)}')
assert len(act_cols_after) == 16, f'Expected still 16 active columns, got {len(act_cols_after)}'
cols_on_new_axis = [c for c in act_cols_after if c['i'] == 3]
print(f'Columns on newly inserted axis (i=3): {len(cols_on_new_axis)}')
assert len(cols_on_new_axis) == 0, 'New axis should have ZERO columns!'

# Test 3: Simulate split on Y (e.g. splitting Ly[0]=6.0m into 2.5m + 3.5m)
new_rem_y, new_pl_y, new_pr_y, new_tr_y, new_ed_y, ny_nx, ny_ny = remap_columns_after_axis_insertion(
    axis_dir='Y',
    span_index=0,
    old_nx=5,
    old_ny=4,
    removed_cols=p.get('fs_removed_cols', []),
    placed_cols=p.get('fs_placed_cols', None),
    col_props=p.get('fs_col_props', {}),
    col_trans=p.get('fs_col_transforms', {}),
    edge_cols=p.get('fs_edge_columns', {}),
    zero_col_mode=True,
    default_b=30.0,
    default_t=50.0,
)

new_Ly = [2.5, 3.5, 2.25, 3.75]
act_cols_y, _, _, _, _ = get_flat_slab_columns(
    Lx, new_Ly,
    bc_cm=30, tc_cm=50,
    removed_ids=set(new_rem_y),
    col_transforms=new_tr_y,
    edge_columns=new_ed_y,
    placed_cols=new_pl_y,
    zero_col_mode=True,
    col_props=new_pr_y,
)

print(f'After split on Y: total active columns = {len(act_cols_y)}')
assert len(act_cols_y) == 16, f'Expected still 16 active columns, got {len(act_cols_y)}'
cols_on_new_y_axis = [c for c in act_cols_y if c['j'] == 1]
print(f'Columns on newly inserted horizontal axis (j=1): {len(cols_on_new_y_axis)}')
assert len(cols_on_new_y_axis) == 0, 'New horizontal axis should have ZERO columns!'

print('ALL TESTS PASSED WITH 100% SUCCESS!')
