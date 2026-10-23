from scratch.test_remap_full import remap_beams_on_span_change

cant_beams = [
    {"id": "B_cant_right", "axis_type": "X", "axis_index": 2, "axis_name": "X2", "p1_grid": [15.0, 6.0], "p2_grid": [16.5, 6.0], "is_continuous": "cantilever"},
    {"id": "B_cant_top", "axis_type": "Y", "axis_index": 2, "axis_name": "Y2", "p1_grid": [5.0, 12.0], "p2_grid": [5.0, 13.5], "is_continuous": "cantilever"},
]

print("--- Test 4: Cantilever beams with increase in Lx0 and Ly0 ---")
res4 = remap_beams_on_span_change(
    cant_beams,
    [5.0, 5.0, 5.0], [6.0, 5.0, 5.0],
    [6.0, 6.0], [7.0, 6.0],
    old_cantilevers={"right": 1.5, "top": 1.5},
    new_cantilevers={"right": 1.5, "top": 1.5},
)
for b in res4:
    print(f"{b['id']} ({b['axis_name']}): p1={b['p1_grid']} p2={b['p2_grid']}")
