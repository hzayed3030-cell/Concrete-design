import sys
sys.path.insert(0, '.')

from modules.flat_slab import get_flat_slab_columns, _geometry_key
from modules.drop_beams_engine import design_drop_beam, recompute_all_drop_beams, remap_beams_on_span_change

print("=== Test 1: Geometry Key with Cantilevers ===")
k1 = _geometry_key([5.0, 5.0], [6.0, 6.0])
k2 = _geometry_key([5.0, 5.0], [6.0, 6.0], {"left": 1.5, "right": 0.0, "bottom": 0.0, "top": 0.0})
assert k1 != k2
print("Geometry key works properly:", k1, "vs", k2)

print("\n=== Test 2: Full Grid & Beams Displacement ===")
# Setup a 4x3 grid (3 spans in X, 2 spans in Y)
old_Lx = [5.0, 6.0, 5.0]
old_Ly = [5.5, 5.5]
old_cant = {"left": 1.2, "right": 1.2, "bottom": 0.0, "top": 0.0}

cols_old, _, _, _, _ = get_flat_slab_columns(old_Lx, old_Ly, bc_cm=30, tc_cm=50)

# Axes:
# Y1: 0.0, Y2: 5.0, Y3: 11.0, Y4: 16.0
# X1: 0.0, X2: 5.5, X3: 11.0
b_h1 = design_drop_beam(p1=[0.0, 5.5], p2=[5.0, 5.5], beam_id="B1", columns_list=cols_old)
b_h1["axis_type"] = "X"
b_h1["axis_index"] = 2
b_h1["axis_name"] = "X2"

b_v2 = design_drop_beam(p1=[5.0, 0.0], p2=[5.0, 5.5], beam_id="B2", columns_list=cols_old)
b_v2["axis_type"] = "Y"
b_v2["axis_index"] = 2
b_v2["axis_name"] = "Y2"

b_v3 = design_drop_beam(p1=[11.0, 0.0], p2=[11.0, 5.5], beam_id="B3", columns_list=cols_old)
b_v3["axis_type"] = "Y"
b_v3["axis_index"] = 3
b_v3["axis_name"] = "Y3"

beams = [b_h1, b_v2, b_v3]

# Now let's change span 0 from 5.0m to 7.0m (increase by 2.0m!)
# And change span 1 from 6.0m to 4.5m (decrease by 1.5m!)
new_Lx = [7.0, 4.5, 5.0]
new_Ly = [5.5, 5.5]
cols_new, _, _, _, _ = get_flat_slab_columns(new_Lx, new_Ly, bc_cm=30, tc_cm=50)

# New axes:
# Y1: 0.0, Y2: 7.0, Y3: 11.5, Y4: 16.5
remapped = remap_beams_on_span_change(
    cur_beams=beams,
    old_Lx_spans=old_Lx,
    new_Lx_spans=new_Lx,
    old_Ly_spans=old_Ly,
    new_Ly_spans=new_Ly,
    old_cantilevers=old_cant,
    new_cantilevers=old_cant,
)

recomputed = recompute_all_drop_beams(remapped, columns_list=cols_new)

# Verify B1: spans from Y1 (0.0) to Y2 (7.0) on X2 (5.5)
assert abs(recomputed[0]['p1_grid'][0] - 0.0) < 0.01
assert abs(recomputed[0]['p2_grid'][0] - 7.0) < 0.01
assert abs(recomputed[0]['p1_grid'][1] - 5.5) < 0.01
assert abs(recomputed[0]['total_span_m'] - 7.0) < 0.01
print("B1 (horizontal on span 0) correctly expanded to 7.0m:", recomputed[0]['p1_grid'], "->", recomputed[0]['p2_grid'])

# Verify B2: vertical on Y2, which moved from 5.0 to 7.0!
assert abs(recomputed[1]['p1_grid'][0] - 7.0) < 0.01
assert abs(recomputed[1]['p2_grid'][0] - 7.0) < 0.01
print("B2 (vertical on Axis Y2) correctly moved from x=5.0 to x=7.0:", recomputed[1]['p1_grid'], "->", recomputed[1]['p2_grid'])

# Verify B3: vertical on Y3, which moved from 11.0 to 11.5!
assert abs(recomputed[2]['p1_grid'][0] - 11.5) < 0.01
assert abs(recomputed[2]['p2_grid'][0] - 11.5) < 0.01
print("B3 (vertical on Axis Y3) correctly moved from x=11.0 to x=11.5:", recomputed[2]['p1_grid'], "->", recomputed[2]['p2_grid'])

print("\nALL VERIFICATIONS PASSED 100%!")
