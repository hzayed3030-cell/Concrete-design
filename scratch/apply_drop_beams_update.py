with open('modules/drop_beams_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """        if root_is_s1:
            cb["reaction_s1_ton"] = round(Vu_cant, 2)
            cb["reaction_s2_ton"] = 0.0
        else:
            cb["reaction_s1_ton"] = 0.0
            cb["reaction_s2_ton"] = round(Vu_cant, 2)

    return updated"""

replacement = """        if root_is_s1:
            cb["reaction_s1_ton"] = round(Vu_cant, 2)
            cb["reaction_s2_ton"] = 0.0
        else:
            cb["reaction_s1_ton"] = 0.0
            cb["reaction_s2_ton"] = round(Vu_cant, 2)

    return updated


def remap_beams_on_span_change(
    cur_beams: list,
    old_Lx_spans: list,
    new_Lx_spans: list,
    old_Ly_spans: list,
    new_Ly_spans: list,
    old_cantilevers: dict = None,
    new_cantilevers: dict = None,
) -> list:
    \"\"\"
    إعادة ربط وإزاحة إحداثيات الكمرات الساقطة عند تعديل أي بحر إنشائي (span) بالزيادة أو النقصان.
    تضمن تحريك المحور بكل ما يقع عليه من أعمدة وكمرات ساقطة وكوابيل تلقائياً وبدقة هندسية تامة.
    \"\"\"
    if not cur_beams:
        return []

    old_cant = old_cantilevers or {}
    new_cant = new_cantilevers or {}

    old_x = [0.0]
    for lx in (old_Lx_spans or []):
        old_x.append(round(old_x[-1] + float(lx), 4))
    new_x = [0.0]
    for lx in (new_Lx_spans or []):
        new_x.append(round(new_x[-1] + float(lx), 4))

    old_y = [0.0]
    for ly in (old_Ly_spans or []):
        old_y.append(round(old_y[-1] + float(ly), 4))
    new_y = [0.0]
    for ly in (new_Ly_spans or []):
        new_y.append(round(new_y[-1] + float(ly), 4))

    if not old_x or not new_x or not old_y or not new_y:
        return cur_beams

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
                span_len = xb - xa
                ratio = (v - xa) / span_len if span_len > 1e-6 else 0.0
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
                span_len = yb - ya
                ratio = (v - ya) / span_len if span_len > 1e-6 else 0.0
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
            # Horizontal beam along X-axis
            if ax_idx is not None and isinstance(ax_idx, int) and ax_idx > len(new_y):
                continue
            if ax_idx is not None and isinstance(ax_idx, int) and 1 <= ax_idx <= len(new_y):
                target_y = new_y[ax_idx - 1]
                b_copy["axis_index"] = ax_idx
                b_copy["axis_name"] = f"X{ax_idx}"
            else:
                target_y = map_y_coord((p1[1] + p2[1]) / 2.0)
                c_idx = min(range(len(new_y)), key=lambda idx: abs(new_y[idx] - target_y))
                if abs(new_y[c_idx] - target_y) <= 0.35:
                    target_y = new_y[c_idx]
                    b_copy["axis_index"] = c_idx + 1
                    b_copy["axis_name"] = f"X{c_idx + 1}"

            new_x1 = map_x_coord(p1[0])
            new_x2 = map_x_coord(p2[0])
            if abs(new_x2 - new_x1) < 0.20:
                continue

            b_copy["p1_grid"] = [new_x1, target_y]
            b_copy["p2_grid"] = [new_x2, target_y]
            b_copy["p1"] = [new_x1, target_y]
            b_copy["p2"] = [new_x2, target_y]
            b_copy["p1_face"] = [new_x1, target_y]
            b_copy["p2_face"] = [new_x2, target_y]

        else:
            # Vertical beam along Y-axis
            if ax_idx is not None and isinstance(ax_idx, int) and ax_idx > len(new_x):
                continue
            if ax_idx is not None and isinstance(ax_idx, int) and 1 <= ax_idx <= len(new_x):
                target_x = new_x[ax_idx - 1]
                b_copy["axis_index"] = ax_idx
                b_copy["axis_name"] = f"Y{ax_idx}"
            else:
                target_x = map_x_coord((p1[0] + p2[0]) / 2.0)
                c_idx = min(range(len(new_x)), key=lambda idx: abs(new_x[idx] - target_x))
                if abs(new_x[c_idx] - target_x) <= 0.35:
                    target_x = new_x[c_idx]
                    b_copy["axis_index"] = c_idx + 1
                    b_copy["axis_name"] = f"Y{c_idx + 1}"

            new_y1 = map_y_coord(p1[1])
            new_y2 = map_y_coord(p2[1])
            if abs(new_y2 - new_y1) < 0.20:
                continue

            b_copy["p1_grid"] = [target_x, new_y1]
            b_copy["p2_grid"] = [target_x, new_y2]
            b_copy["p1"] = [target_x, new_y1]
            b_copy["p2"] = [target_x, new_y2]
            b_copy["p1_face"] = [target_x, new_y1]
            b_copy["p2_face"] = [target_x, new_y2]

        b_copy["total_span_m"] = round(math.hypot(b_copy["p2_grid"][0] - b_copy["p1_grid"][0], b_copy["p2_grid"][1] - b_copy["p1_grid"][1]), 2)
        remapped.append(b_copy)

    return remapped"""

assert target in content, "Target string not found!"
new_content = content.replace(target, replacement, 1)

with open('modules/drop_beams_engine.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Successfully updated modules/drop_beams_engine.py!")
