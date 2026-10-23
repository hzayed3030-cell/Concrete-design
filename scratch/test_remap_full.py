import math

def remap_beams_on_span_change(
    cur_beams: list,
    old_Lx_spans: list,
    new_Lx_spans: list,
    old_Ly_spans: list,
    new_Ly_spans: list,
    old_cantilevers: dict = None,
    new_cantilevers: dict = None,
) -> list:
    """
    Remap drop beams grid coordinates when spans change (increase or decrease).
    Moves all beams lying on or anchored to an axis along with that axis,
    and updates beam span lengths and positions.
    """
    if not cur_beams:
        return []

    old_cant = old_cantilevers or {}
    new_cant = new_cantilevers or {}

    old_x = [0.0]
    for lx in old_Lx_spans:
        old_x.append(round(old_x[-1] + float(lx), 4))
    new_x = [0.0]
    for lx in new_Lx_spans:
        new_x.append(round(new_x[-1] + float(lx), 4))

    old_y = [0.0]
    for ly in old_Ly_spans:
        old_y.append(round(old_y[-1] + float(ly), 4))
    new_y = [0.0]
    for ly in new_Ly_spans:
        new_y.append(round(new_y[-1] + float(ly), 4))

    old_cl = float(old_cant.get("left", 0.0) or 0.0)
    new_cl = float(new_cant.get("left", 0.0) or 0.0)
    old_cr = float(old_cant.get("right", 0.0) or 0.0)
    new_cr = float(new_cant.get("right", 0.0) or 0.0)
    old_cb = float(old_cant.get("bottom", 0.0) or 0.0)
    new_cb = float(new_cant.get("bottom", 0.0) or 0.0)
    old_ct = float(old_cant.get("top", 0.0) or 0.0)
    new_ct = float(new_cant.get("top", 0.0) or 0.0)

    def map_x_coord(val):
        v = float(val)
        # Snap to nearest old axis if within 0.35m
        best_i, best_d = None, 0.35
        for i, ox in enumerate(old_x):
            d = abs(v - ox)
            if d < best_d:
                best_d = d
                best_i = i
        if best_i is not None and best_i < len(new_x):
            offset = v - old_x[best_i]
            return round(new_x[best_i] + offset, 4)

        # Cantilever left
        if v < old_x[0]:
            dist = old_x[0] - v
            if old_cl > 0.01 and new_cl > 0.01:
                return round(new_x[0] - (dist * (new_cl / old_cl)), 4)
            return round(new_x[0] - dist, 4)

        # Cantilever right
        if v > old_x[-1]:
            dist = v - old_x[-1]
            if old_cr > 0.01 and new_cr > 0.01:
                return round(new_x[-1] + (dist * (new_cr / old_cr)), 4)
            return round(new_x[-1] + dist, 4)

        # Interpolate inside spans
        for k in range(len(old_x) - 1):
            xa, xb = old_x[k], old_x[k + 1]
            if xa <= v <= xb:
                ratio = (v - xa) / (xb - xa) if (xb - xa) > 1e-6 else 0.0
                if k < len(new_x) - 1:
                    return round(new_x[k] + ratio * (new_x[k + 1] - new_x[k]), 4)
                return round(new_x[-1], 4)

        return round(v, 4)

    def map_y_coord(val):
        v = float(val)
        # Snap to nearest old axis if within 0.35m
        best_j, best_d = None, 0.35
        for j, oy in enumerate(old_y):
            d = abs(v - oy)
            if d < best_d:
                best_d = d
                best_j = j
        if best_j is not None and best_j < len(new_y):
            offset = v - old_y[best_j]
            return round(new_y[best_j] + offset, 4)

        # Cantilever bottom
        if v < old_y[0]:
            dist = old_y[0] - v
            if old_cb > 0.01 and new_cb > 0.01:
                return round(new_y[0] - (dist * (new_cb / old_cb)), 4)
            return round(new_y[0] - dist, 4)

        # Cantilever top
        if v > old_y[-1]:
            dist = v - old_y[-1]
            if old_ct > 0.01 and new_ct > 0.01:
                return round(new_y[-1] + (dist * (new_ct / old_ct)), 4)
            return round(new_y[-1] + dist, 4)

        # Interpolate inside spans
        for k in range(len(old_y) - 1):
            ya, yb = old_y[k], old_y[k + 1]
            if ya <= v <= yb:
                ratio = (v - ya) / (yb - ya) if (yb - ya) > 1e-6 else 0.0
                if k < len(new_y) - 1:
                    return round(new_y[k] + ratio * (new_y[k + 1] - new_y[k]), 4)
                return round(new_y[-1], 4)

        return round(v, 4)

    remapped = []
    for b in cur_beams:
        b_copy = dict(b)
        p1 = list(b.get("p1_grid", b.get("p1", [0, 0])))
        p2 = list(b.get("p2_grid", b.get("p2", [0, 0])))
        ax_type = b.get("axis_type")
        ax_idx = b.get("axis_index")

        # Determine orientation if not explicit
        if not ax_type:
            if abs(p2[0] - p1[0]) >= abs(p2[1] - p1[1]):
                ax_type = "X"
            else:
                ax_type = "Y"
            b_copy["axis_type"] = ax_type

        if ax_type == "X":
            # Horizontal beam along X-axis (constant or near-constant Y)
            # Find which horizontal axis if ax_idx is missing or needs validation
            if ax_idx is not None and isinstance(ax_idx, int) and 1 <= ax_idx <= len(new_y):
                target_y = new_y[ax_idx - 1]
            else:
                target_y = map_y_coord((p1[1] + p2[1]) / 2.0)
                # find closest new_y
                c_idx = min(range(len(new_y)), key=lambda idx: abs(new_y[idx] - target_y))
                if abs(new_y[c_idx] - target_y) <= 0.35:
                    target_y = new_y[c_idx]
                    b_copy["axis_index"] = c_idx + 1
                    b_copy["axis_name"] = f"X{c_idx + 1}"

            new_x1 = map_x_coord(p1[0])
            new_x2 = map_x_coord(p2[0])
            b_copy["p1_grid"] = [new_x1, target_y]
            b_copy["p2_grid"] = [new_x2, target_y]
            b_copy["p1"] = [new_x1, target_y]
            b_copy["p2"] = [new_x2, target_y]

        else:
            # Vertical beam along Y-axis (constant or near-constant X)
            if ax_idx is not None and isinstance(ax_idx, int) and 1 <= ax_idx <= len(new_x):
                target_x = new_x[ax_idx - 1]
            else:
                target_x = map_x_coord((p1[0] + p2[0]) / 2.0)
                c_idx = min(range(len(new_x)), key=lambda idx: abs(new_x[idx] - target_x))
                if abs(new_x[c_idx] - target_x) <= 0.35:
                    target_x = new_x[c_idx]
                    b_copy["axis_index"] = c_idx + 1
                    b_copy["axis_name"] = f"Y{c_idx + 1}"

            new_y1 = map_y_coord(p1[1])
            new_y2 = map_y_coord(p2[1])
            b_copy["p1_grid"] = [target_x, new_y1]
            b_copy["p2_grid"] = [target_x, new_y2]
            b_copy["p1"] = [target_x, new_y1]
            b_copy["p2"] = [target_x, new_y2]

        remapped.append(b_copy)

    return remapped

# Test suite
sample_beams = [
    {"id": "B1", "axis_type": "X", "axis_index": 2, "axis_name": "X2", "p1_grid": [0.0, 6.0], "p2_grid": [5.0, 6.0]},
    {"id": "B2", "axis_type": "X", "axis_index": 2, "axis_name": "X2", "p1_grid": [5.0, 6.0], "p2_grid": [10.0, 6.0]},
    {"id": "B3", "axis_type": "Y", "axis_index": 2, "axis_name": "Y2", "p1_grid": [5.0, 0.0], "p2_grid": [5.0, 6.0]},
    {"id": "B4", "axis_type": "Y", "axis_index": 3, "axis_name": "Y3", "p1_grid": [10.0, 0.0], "p2_grid": [10.0, 6.0]},
]

print("--- Test 1: Increase span 0 from 5.0 to 6.0 ---")
res1 = remap_beams_on_span_change(sample_beams, [5.0, 5.0, 5.0], [6.0, 5.0, 5.0], [6.0, 6.0], [6.0, 6.0])
for b in res1:
    print(f"{b['id']} ({b['axis_name']}): p1={b['p1_grid']} p2={b['p2_grid']}")

print("\n--- Test 2: Decrease span 0 from 5.0 to 4.0 ---")
res2 = remap_beams_on_span_change(sample_beams, [5.0, 5.0, 5.0], [4.0, 5.0, 5.0], [6.0, 6.0], [6.0, 6.0])
for b in res2:
    print(f"{b['id']} ({b['axis_name']}): p1={b['p1_grid']} p2={b['p2_grid']}")

print("\n--- Test 3: Increase Ly span 0 from 6.0 to 7.0 ---")
res3 = remap_beams_on_span_change(sample_beams, [5.0, 5.0, 5.0], [5.0, 5.0, 5.0], [6.0, 6.0], [7.0, 6.0])
for b in res3:
    print(f"{b['id']} ({b['axis_name']}): p1={b['p1_grid']} p2={b['p2_grid']}")
