import json

# Let's test the python portion of bbox_info
x_coords = [0.0, 5.0, 10.0]
y_coords = [0.0, 6.0, 12.0]
active_cols = [{"id": "C1", "center_x": 0.0, "center_y": 0.0, "width_cm": 30.0, "height_cm": 60.0}]
cantilevers = {"left": 1.2, "right": 1.0, "bottom": 0.0, "top": 1.5}
drop_beams = [{"id": "B1", "p1": [0.0, 0.0], "p2": [5.0, 0.0]}]

snaps_list = []
for i, x in enumerate(x_coords):
    for j, y in enumerate(y_coords):
        snaps_list.append({"x": float(x), "y": float(y), "type": "grid", "label": f"محور Y{i+1} × X{j+1}"})
for c in active_cols:
    cx = float(c.get("center_x", 0.0))
    cy = float(c.get("center_y", 0.0))
    cw = float(c.get("width_cm", 30.0)) / 100.0
    ch = float(c.get("height_cm", 30.0)) / 100.0
    cid = str(c.get("id", "C"))
    snaps_list.append({"x": cx, "y": cy, "type": "col_center", "label": f"🎯 مركز العمود {cid}"})
    snaps_list.append({"x": cx - cw/2, "y": cy - ch/2, "type": "col_corner", "label": f"📐 ركن العمود {cid}"})
    snaps_list.append({"x": cx + cw/2, "y": cy - ch/2, "type": "col_corner", "label": f"📐 ركن العمود {cid}"})
    snaps_list.append({"x": cx + cw/2, "y": cy + ch/2, "type": "col_corner", "label": f"📐 ركن العمود {cid}"})
    snaps_list.append({"x": cx - cw/2, "y": cy + ch/2, "type": "col_corner", "label": f"📐 ركن العمود {cid}"})

for b in drop_beams:
    bp1 = b.get("p1")
    bp2 = b.get("p2")
    if bp1: snaps_list.append({"x": float(bp1[0]), "y": float(bp1[1]), "type": "beam_end", "label": f"طرف كمرة {b.get('id', '')}"})
    if bp2: snaps_list.append({"x": float(bp2[0]), "y": float(bp2[1]), "type": "beam_end", "label": f"طرف كمرة {b.get('id', '')}"})

print(f"Generated {len(snaps_list)} snap points successfully.")
