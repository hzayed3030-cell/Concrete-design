import sys
sys.path.insert(0, '.')

import modules.flat_slab as fs

Lx = [5.0, 5.0]
Ly = [6.0, 6.0]
cols, all_c, _, _, _ = fs.get_flat_slab_columns(Lx, Ly)
c1 = cols[0]
orig_id = c1["orig_id"]

geom_before = fs.compute_column_geometry(c1["x"], c1["y"], 30, 60, {"direction": "اتجاه X"})
print("Before (Dir X):", geom_before["width_m"], "x", geom_before["height_m"])

trans_new = {"direction": "اتجاه Y", "shift_x": "متمركز على المحور (Centered)", "shift_y": "متمركز على المحور (Centered)"}
geom_after = fs.compute_column_geometry(c1["x"], c1["y"], 30, 60, trans_new)
print("After (Dir Y):", geom_after["width_m"], "x", geom_after["height_m"])

assert geom_before["width_m"] == 0.60 and geom_before["height_m"] == 0.30
assert geom_after["width_m"] == 0.30 and geom_after["height_m"] == 0.60

col_trans = {orig_id: trans_new}
fig = fs.generate_flat_slab_sketch(Lx, Ly, {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0}, col_transforms=col_trans)
assert fig is not None
print("Sketch successfully generated with in-place col_transforms in a single pass!")
