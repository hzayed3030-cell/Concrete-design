import sys
sys.path.insert(0, '.')

from modules.flat_slab import get_flat_slab_columns
from modules.drop_beams_engine import design_drop_beam, recompute_all_drop_beams
from scratch.test_remap_full import remap_beams_on_span_change

# 1. Initial geometry: Lx = [5.0, 5.0, 5.0], Ly = [6.0, 6.0]
Lx_init = [5.0, 5.0, 5.0]
Ly_init = [6.0, 6.0]
cols_init, _, _, _, _ = get_flat_slab_columns(Lx_init, Ly_init, bc_cm=30, tc_cm=50)

# Check col positions
print("Initial column count:", len(cols_init))
# Column at (i=1, j=1) -> Y2-X2 at (5.0, 6.0)
c_y2_x2 = [c for c in cols_init if abs(c['x'] - 5.0) < 0.1 and abs(c['y'] - 6.0) < 0.1][0]
print(f"Col at Y2-X2: id={c_y2_x2['id']}, pos=({c_y2_x2['x']}, {c_y2_x2['y']})")

# 2. Design initial beams:
# Beam 1 on X2 between Y1 (0.0) and Y2 (5.0)
b1 = design_drop_beam(p1=[0.0, 6.0], p2=[5.0, 6.0], beam_id="B1", columns_list=cols_init)
b1["axis_type"] = "X"
b1["axis_index"] = 2
b1["axis_name"] = "X2"

# Beam 2 on Y2 between X1 (0.0) and X2 (6.0)
b2 = design_drop_beam(p1=[5.0, 0.0], p2=[5.0, 6.0], beam_id="B2", columns_list=cols_init)
b2["axis_type"] = "Y"
b2["axis_index"] = 2
b2["axis_name"] = "Y2"

initial_beams = [b1, b2]
print(f"Initial B1: span={b1['total_span_m']}m, p1={b1['p1_grid']}, p2={b1['p2_grid']}, supp1={b1['supp1']['type']}, supp2={b1['supp2']['type']}")
print(f"Initial B2: span={b2['total_span_m']}m, p1={b2['p1_grid']}, p2={b2['p2_grid']}, supp1={b2['supp1']['type']}, supp2={b2['supp2']['type']}")

# 3. User changes span 0 from 5.0m to 6.5m!
Lx_new = [6.5, 5.0, 5.0]
Ly_new = [6.0, 6.0]
cols_new, _, _, _, _ = get_flat_slab_columns(Lx_new, Ly_new, bc_cm=30, tc_cm=50)

c_y2_x2_new = [c for c in cols_new if abs(c['x'] - 6.5) < 0.1 and abs(c['y'] - 6.0) < 0.1][0]
print(f"\nAfter span change: Col at Y2-X2 moved to: ({c_y2_x2_new['x']}, {c_y2_x2_new['y']})")

# 4. Remap beams
remapped = remap_beams_on_span_change(initial_beams, Lx_init, Lx_new, Ly_init, Ly_new)
print(f"Remapped B1: p1={remapped[0]['p1_grid']}, p2={remapped[0]['p2_grid']}")
print(f"Remapped B2: p1={remapped[1]['p1_grid']}, p2={remapped[1]['p2_grid']}")

# 5. Recompute all drop beams with new columns
recomputed = recompute_all_drop_beams(remapped, columns_list=cols_new)
print(f"\nFinal recomputed B1: span={recomputed[0]['total_span_m']}m, p1_face={recomputed[0]['p1']}, p2_face={recomputed[0]['p2']}, supp1={recomputed[0]['supp1']['type']}, supp2={recomputed[0]['supp2']['type']}")
print(f"Final recomputed B2: span={recomputed[1]['total_span_m']}m, p1_face={recomputed[1]['p1']}, p2_face={recomputed[1]['p2']}, supp1={recomputed[1]['supp1']['type']}, supp2={recomputed[1]['supp2']['type']}")
