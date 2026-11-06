"""
modules/ground_beam_layout.py
================================================================================
Automated Ground Beams (السملات والميدات الأرضية) and Strap Beams (الشدادات)
Classification, Continuity Derivation, Structural Design, and 3-Model Grouping
Engine for Module 1 (ECP 203-2018).

Key Capabilities:
1. Coordinates & Connectivity Extraction:
   - Reads active columns from Module 1 layout.
   - Extracts orthogonal grid lines (X and Y directions).
   - Identifies adjacent column connections and clear spans.
2. Strap Beams Confirmation (Module 9 & Module 10):
   - Reviews elements identified as edge strap footings or corner diagonal straps.
   - Confirms their classification as Strap Beams (high moment/shear transfer).
3. Ground Beams Filtering & Auto-Classification:
   - Identifies all remaining connections between columns not defined as strap beams.
   - Classifies them as Ground Beams / Tie Beams (GB).
4. Automatic Continuity Derivation (حالة الاستمرارية والدعم):
   - Derives support conditions directly from multi-column grid lines:
     * 2-column line: Simply Supported (حر من الطرفين)
     * >2-column line: Terminal spans = Continuous from One End (مستمر من طرف واحد)
                       Interior spans = Continuous from Both Ends (مستمر من الطرفين)
5. Comprehensive Structural Design (per Module 11 rules):
   - Self-weight + Wall load + Axial Tie Action (10% of max Pu) + Differential settlement.
   - Bending moments, shear forces, recommended depth t_calc.
   - Longitudinal bottom & top rebar, shrinkage side bars, stirrups.
6. Automatic Grouping into 3 Execution Models (B1, B2, B3):
   - Sorts analyzed beams descending by structural demand.
   - Applies Governing Envelope Rule (max t, max As_bot, max As_top, max stirrups).
   - Provides interactive override parameters.
7. Bill of Quantities (BOQ):
   - Concrete volume, rebar weight by diameter, cement, sand, gravel.
================================================================================
"""

import math
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches


# ═══════════════════════════════════════════════════════════════════════════════
# 1. NETWORK CONNECTIVITY & BEAM SEGMENT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════



def _ar(text):
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        if any('\u0600' <= char <= '\u06FF' for char in str(text)):
            reshaped_text = arabic_reshaper.reshape(str(text))
            return get_display(reshaped_text)
        return str(text)
    except Exception:
        return str(text)


def _hdim(ax, y, x1, x2, label, side="top", fs=9.0, offset=0.18, draw_ext=True):
    ym = y + offset if side == "top" else y - offset
    ax.annotate("", xy=(x1, ym), xytext=(x2, ym), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.2))
    if draw_ext:
        ax.plot([x1, x1], [y, ym], color="#94a3b8", lw=0.8, ls="--", alpha=0.7)
        ax.plot([x2, x2], [y, ym], color="#94a3b8", lw=0.8, ls="--", alpha=0.7)
    ax.text((x1 + x2) / 2.0, ym + (0.08 if side == "top" else -0.08),
            label, ha="center", va="bottom" if side == "top" else "top",
            fontsize=fs, fontweight="bold", color="#1e293b")


def _vdim(ax, x, y1, y2, label, side="left", fs=9.0, offset=0.18, draw_ext=True):
    xm = x + offset if side == "right" else x - offset
    ax.annotate("", xy=(xm, y1), xytext=(xm, y2), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.2))
    if draw_ext:
        ax.plot([x, xm], [y1, y1], color="#94a3b8", lw=0.8, ls="--", alpha=0.7)
        ax.plot([x, xm], [y2, y2], color="#94a3b8", lw=0.8, ls="--", alpha=0.7)
    ax.text(xm + (0.08 if side == "right" else -0.08), (y1 + y2) / 2.0,
            label, ha="right" if side == "left" else "left", va="center",
            rotation=90, fontsize=fs, fontweight="bold", color="#1e293b")


def _get_grid_axes_gb(columns_list):
    """
    Extract clean structural grid coordinates and labels from columns list.
    Prioritizes explicit grid_x_m / grid_y_m, with fallback clustering of coordinates
    to prevent shifted/offset columns from generating duplicate or chaotic grid lines.
    """
    if not columns_list:
        return [], [], {}, {}
    has_grid_m = any("grid_x_m" in c for c in columns_list)
    if has_grid_m:
        unique_xs = sorted(list(set(round(float(c["grid_x_m"]), 3) for c in columns_list if "grid_x_m" in c)))
        unique_ys = sorted(list(set(round(float(c["grid_y_m"]), 3) for c in columns_list if "grid_y_m" in c)))
    else:
        def _cluster(coords, tol=0.40):
            if not coords:
                return []
            sc = sorted(coords)
            clusters = [[sc[0]]]
            for val in sc[1:]:
                if val - clusters[-1][-1] <= tol:
                    clusters[-1].append(val)
                else:
                    clusters.append([val])
            return sorted([round(sum(cl) / len(cl), 2) for cl in clusters])

        unique_xs = _cluster([float(c["x"]) for c in columns_list])
        unique_ys = _cluster([float(c["y"]) for c in columns_list])

    label_map_x = {}
    label_map_y = {}
    for c in columns_list:
        gx = float(c.get("grid_x_m", c.get("x", 0.0)))
        gy = float(c.get("grid_y_m", c.get("y", 0.0)))
        if "grid_x" in c and c["grid_x"] and unique_xs:
            best_x = min(unique_xs, key=lambda u: abs(u - gx))
            label_map_x[best_x] = str(c["grid_x"])
        if "grid_y" in c and c["grid_y"] and unique_ys:
            best_y = min(unique_ys, key=lambda u: abs(u - gy))
            label_map_y[best_y] = str(c["grid_y"])

    return unique_xs, unique_ys, label_map_x, label_map_y


def align_ground_beam_coords(
    gb,
    unique_xs=None,
    unique_ys=None,
    active_columns=None,
    col_props=None,
    col_transforms=None,
    edge_columns=None,
    slab_bounds=None,
):
    """
    Computes exact engineering coordinates and face-alignment offset (Eccentricity)
    for Ground Beams and Strap Beams according to ECP 203:
    - Calculates the offset so that the Ground Beam face aligns 100% flush with the connected Column Face.
    - Considers column dimensions, column orientation, and user-defined shift (±6 cm / center).
    - Exterior Facade Priority: Exterior ground beams align with the building's exterior perimeter face.
    - Differing Column Sizes: If connected columns differ in size or eccentricity, aligns with the dominant/larger column or exterior face.
    """
    import streamlit as st
    try:
        from modules.settings import S
    except Exception:
        S = None

    if active_columns is None and "fs_active_columns" in st.session_state:
        active_columns = st.session_state.get("fs_active_columns", [])
    if col_transforms is None:
        col_transforms = (
            st.session_state.get("fs_col_transforms")
            or (S.cfg_val("fs_col_transforms", {}) if S else {})
            or {}
        )
    if col_props is None:
        col_props = (
            st.session_state.get("fs_col_props")
            or (S.cfg_val("fs_col_props", {}) if S else {})
            or {}
        )
    if edge_columns is None and "fs_ftg_analysis" in st.session_state:
        edge_columns = st.session_state.get("fs_ftg_analysis", {}).get("edge_columns")

    c1 = gb.get("col1", {})
    c2 = gb.get("col2", {})
    cid1 = str(gb.get("col1_id") or c1.get("id") or c1.get("orig_id") or "")
    cid2 = str(gb.get("col2_id") or c2.get("id") or c2.get("orig_id") or "")

    cols_by_id = {}
    if active_columns:
        for c in active_columns:
            cid = str(c.get("id") or "")
            orig_id = str(c.get("orig_id") or "")
            name = str(c.get("name") or "")
            if cid:
                cols_by_id[cid] = c
            if orig_id:
                cols_by_id[orig_id] = c
            if name:
                cols_by_id[name] = c
            i_idx, j_idx = c.get("i"), c.get("j")
            if i_idx is not None and j_idx is not None:
                cols_by_id[f"{i_idx},{j_idx}"] = c
            gx_val = round(float(c.get("grid_x_m", c.get("x", 0.0))), 2)
            gy_val = round(float(c.get("grid_y_m", c.get("y", 0.0))), 2)
            cols_by_id[(gx_val, gy_val)] = c

    col_match1 = cols_by_id.get(cid1)
    if not col_match1:
        c1_gx = round(float(c1.get("x", 0.0)), 2)
        c1_gy = round(float(c1.get("y", 0.0)), 2)
        col_match1 = cols_by_id.get((c1_gx, c1_gy), c1)

    col_match2 = cols_by_id.get(cid2)
    if not col_match2:
        c2_gx = round(float(c2.get("x", 0.0)), 2)
        c2_gy = round(float(c2.get("y", 0.0)), 2)
        col_match2 = cols_by_id.get((c2_gx, c2_gy), c2)

    def _resolve_col_geom(col_dict):
        from modules.flat_slab import compute_column_geometry
        cid = str(col_dict.get("id") or col_dict.get("orig_id") or "")
        orig_id = str(col_dict.get("orig_id") or cid)
        i_idx = col_dict.get("i")
        j_idx = col_dict.get("j")

        c_prop = {}
        if isinstance(col_props, dict):
            c_prop = (
                col_props.get(orig_id)
                or col_props.get(cid)
                or (col_props.get(f"{i_idx},{j_idx}") if i_idx is not None and j_idx is not None else {})
                or {}
            )
        c_w_cm = float(c_prop.get("b_cm") or col_dict.get("b_cm") or col_dict.get("bc") or 30.0)
        c_d_cm = float(c_prop.get("t_cm") or col_dict.get("t_cm") or col_dict.get("tc") or 60.0)

        c_trans = {}
        if isinstance(col_transforms, dict):
            c_trans = dict(
                col_transforms.get(orig_id)
                or col_transforms.get(cid)
                or (col_transforms.get(f"{i_idx},{j_idx}") if i_idx is not None and j_idx is not None else {})
                or {}
            )

        if isinstance(c_prop, dict):
            if not c_trans.get("direction") and c_prop.get("direction"):
                c_trans["direction"] = c_prop["direction"]
            if not c_trans.get("shift_x") and c_prop.get("shift_x"):
                c_trans["shift_x"] = c_prop["shift_x"]
            if not c_trans.get("shift_y") and c_prop.get("shift_y"):
                c_trans["shift_y"] = c_prop["shift_y"]

        if not c_trans.get("direction") and col_dict.get("direction"):
            c_trans["direction"] = col_dict.get("direction")
        if not c_trans.get("shift_x") and col_dict.get("shift_x"):
            c_trans["shift_x"] = col_dict.get("shift_x")
        if not c_trans.get("shift_y") and col_dict.get("shift_y"):
            c_trans["shift_y"] = col_dict.get("shift_y")

        gx = float(col_dict.get("grid_x_m", col_dict.get("x", 0.0)))
        gy = float(col_dict.get("grid_y_m", col_dict.get("y", 0.0)))

        res = compute_column_geometry(gx, gy, c_w_cm, c_d_cm, c_trans)
        res["orig_id"] = orig_id
        res["cid"] = cid
        return res

    g1 = _resolve_col_geom(col_match1)
    g2 = _resolve_col_geom(col_match2)
    gb_w = float(gb.get("b_cm", 25.0)) / 100.0

    c1_x = g1["grid_x"]
    c1_y = g1["grid_y"]
    c2_x = g2["grid_x"]
    c2_y = g2["grid_y"]

    dx = c2_x - c1_x
    dy = c2_y - c1_y
    dir_b = gb.get("dir")
    if not dir_b:
        if abs(dx) > 0.35 and abs(dy) > 0.35:
            dir_b = "DIAG"
        elif abs(dx) >= abs(dy):
            dir_b = "X"
        else:
            dir_b = "Y"

    def _get_edge_dirs(col_geom, cid_val):
        dirs = []
        if edge_columns and isinstance(edge_columns, dict):
            ed = edge_columns.get(cid_val) or edge_columns.get(str(col_geom.get("orig_id", ""))) or {}
            if isinstance(ed, dict) and ed.get("is_edge") == "Yes":
                d_str = ed.get("direction", "").lower()
                dirs.append(d_str)
        return dirs

    if dir_b == "X" or (abs(dx) >= abs(dy) and abs(dy) <= 0.45):
        mean_y = (c1_y + c2_y) / 2.0
        cl_y = min(unique_ys, key=lambda u: abs(u - mean_y)) if unique_ys else mean_y

        if unique_xs:
            best_x1 = min(unique_xs, key=lambda u: abs(u - c1_x))
            x1 = best_x1 if abs(best_x1 - c1_x) <= 0.45 else c1_x
            best_x2 = min(unique_xs, key=lambda u: abs(u - c2_x))
            x2 = best_x2 if abs(best_x2 - c2_x) <= 0.45 else c2_x
        else:
            x1 = c1_x
            x2 = c2_x

        bx0 = min(x1, x2)
        bw = abs(x2 - x1)

        # Building footprint limits in Y
        min_y_bldg = min(unique_ys) if unique_ys else min(c1_y, c2_y)
        max_y_bldg = max(unique_ys) if unique_ys else max(c1_y, c2_y)
        if slab_bounds and isinstance(slab_bounds, dict):
            min_y_bldg = min(min_y_bldg, float(slab_bounds.get("y_min", min_y_bldg)))
            max_y_bldg = max(max_y_bldg, float(slab_bounds.get("y_max", max_y_bldg)))

        is_bottom_facade = abs(cl_y - min_y_bldg) <= 0.40
        is_top_facade = abs(cl_y - max_y_bldg) <= 0.40

        ed_dirs1 = _get_edge_dirs(g1, cid1)
        ed_dirs2 = _get_edge_dirs(g2, cid2)
        all_ed_dirs = ed_dirs1 + ed_dirs2
        if any(any(k in d for k in ["bottom", "south", "أسفل"]) for d in all_ed_dirs):
            is_bottom_facade = True
        if any(any(k in d for k in ["top", "north", "أعلى"]) for d in all_ed_dirs):
            is_top_facade = True

        s1 = str(g1.get("shift_y", "") or "")
        s2 = str(g2.get("shift_y", "") or "")
        h1 = g1["height_m"]
        h2 = g2["height_m"]

        g_dom = g1 if h1 >= h2 else g2
        dom_shift = str(g_dom.get("shift_y", "") or "")

        def _is_shift_up(s):
            return "لأعلى" in s or s.startswith("أعلى") or "up" in s.lower() or "top" in s.lower()

        def _is_shift_down(s):
            return "لأسفل" in s or s.startswith("أسفل") or "down" in s.lower() or "bottom" in s.lower()

        # Exact face alignment offset calculation
        if is_bottom_facade and not is_top_facade:
            by0 = min(g1["y_min"], g2["y_min"])
        elif is_top_facade and not is_bottom_facade:
            by0 = max(g1["y_max"], g2["y_max"]) - gb_w
        else:
            is_up1 = _is_shift_up(s1)
            is_up2 = _is_shift_up(s2)
            is_down1 = _is_shift_down(s1)
            is_down2 = _is_shift_down(s2)

            if (is_up1 or is_up2) and not (is_down1 or is_down2):
                ref_col = g1 if is_up1 and (h1 >= h2 or not is_up2) else g2
                by0 = ref_col["y_min"]
            elif (is_down1 or is_down2) and not (is_up1 or is_up2):
                ref_col = g1 if is_down1 and (h1 >= h2 or not is_down2) else g2
                by0 = ref_col["y_max"] - gb_w
            elif (is_up1 or is_up2) and (is_down1 or is_down2):
                if _is_shift_up(dom_shift):
                    by0 = g_dom["y_min"]
                elif _is_shift_down(dom_shift):
                    by0 = g_dom["y_max"] - gb_w
                else:
                    by0 = cl_y - gb_w / 2.0
            else:
                by0 = cl_y - gb_w / 2.0

        mid_x = bx0 + bw / 2.0
        mid_y = by0 + gb_w / 2.0
        p1 = [bx0, mid_y]
        p2 = [bx0 + bw, mid_y]

        return {
            "dir": "X",
            "cl_coord": cl_y,
            "cl_y": cl_y,
            "p1": p1,
            "p2": p2,
            "bx0": bx0,
            "bw": bw,
            "by0": by0,
            "bh": gb_w,
            "gb_w": gb_w,
            "mid_x": mid_x,
            "mid_y": mid_y,
            "_is_aligned": True,
        }
    elif dir_b == "Y" or (abs(dy) > abs(dx) and abs(dx) <= 0.45):
        mean_x = (c1_x + c2_x) / 2.0
        cl_x = min(unique_xs, key=lambda u: abs(u - mean_x)) if unique_xs else mean_x

        if unique_ys:
            best_y1 = min(unique_ys, key=lambda u: abs(u - c1_y))
            y1 = best_y1 if abs(best_y1 - c1_y) <= 0.45 else c1_y
            best_y2 = min(unique_ys, key=lambda u: abs(u - c2_y))
            y2 = best_y2 if abs(best_y2 - c2_y) <= 0.45 else c2_y
        else:
            y1 = c1_y
            y2 = c2_y

        by0 = min(y1, y2)
        bh = abs(y2 - y1)

        # Building footprint limits in X
        min_x_bldg = min(unique_xs) if unique_xs else min(c1_x, c2_x)
        max_x_bldg = max(unique_xs) if unique_xs else max(c1_x, c2_x)
        if slab_bounds and isinstance(slab_bounds, dict):
            min_x_bldg = min(min_x_bldg, float(slab_bounds.get("x_min", min_x_bldg)))
            max_x_bldg = max(max_x_bldg, float(slab_bounds.get("x_max", max_x_bldg)))

        is_left_facade = abs(cl_x - min_x_bldg) <= 0.40
        is_right_facade = abs(cl_x - max_x_bldg) <= 0.40

        ed_dirs1 = _get_edge_dirs(g1, cid1)
        ed_dirs2 = _get_edge_dirs(g2, cid2)
        all_ed_dirs = ed_dirs1 + ed_dirs2
        if any(any(k in d for k in ["left", "west", "يسار"]) for d in all_ed_dirs):
            is_left_facade = True
        if any(any(k in d for k in ["right", "east", "يمين"]) for d in all_ed_dirs):
            is_right_facade = True

        s1 = str(g1.get("shift_x", "") or "")
        s2 = str(g2.get("shift_x", "") or "")
        w1 = g1["width_m"]
        w2 = g2["width_m"]

        g_dom = g1 if w1 >= w2 else g2
        dom_shift = str(g_dom.get("shift_x", "") or "")

        def _is_shift_right(s):
            return "يميناً" in s or s.startswith("يمين") or "right" in s.lower()

        def _is_shift_left(s):
            return "يساراً" in s or s.startswith("يسار") or "left" in s.lower()

        if is_left_facade and not is_right_facade:
            bx0 = min(g1["x_min"], g2["x_min"])
        elif is_right_facade and not is_left_facade:
            bx0 = max(g1["x_max"], g2["x_max"]) - gb_w
        else:
            is_right1 = _is_shift_right(s1)
            is_right2 = _is_shift_right(s2)
            is_left1 = _is_shift_left(s1)
            is_left2 = _is_shift_left(s2)

            if (is_right1 or is_right2) and not (is_left1 or is_left2):
                ref_col = g1 if is_right1 and (w1 >= w2 or not is_right2) else g2
                bx0 = ref_col["x_min"]
            elif (is_left1 or is_left2) and not (is_right1 or is_right2):
                ref_col = g1 if is_left1 and (w1 >= w2 or not is_left2) else g2
                bx0 = ref_col["x_max"] - gb_w
            elif (is_right1 or is_right2) and (is_left1 or is_left2):
                if _is_shift_right(dom_shift):
                    bx0 = g_dom["x_min"]
                elif _is_shift_left(dom_shift):
                    bx0 = g_dom["x_max"] - gb_w
                else:
                    bx0 = cl_x - gb_w / 2.0
            else:
                bx0 = cl_x - gb_w / 2.0

        mid_x = bx0 + gb_w / 2.0
        mid_y = by0 + bh / 2.0
        p1 = [mid_x, by0]
        p2 = [mid_x, by0 + bh]

        return {
            "dir": "Y",
            "cl_coord": cl_x,
            "cl_x": cl_x,
            "p1": p1,
            "p2": p2,
            "bx0": bx0,
            "bw": gb_w,
            "by0": by0,
            "bh": bh,
            "gb_w": gb_w,
            "mid_x": mid_x,
            "mid_y": mid_y,
            "_is_aligned": True,
        }
    else:
        p1 = [g1["center_x"], g1["center_y"]]
        p2 = [g2["center_x"], g2["center_y"]]
        dx_val = p2[0] - p1[0]
        dy_val = p2[1] - p1[1]
        return {
            "dir": "DIAG",
            "p1": p1,
            "p2": p2,
            "bx0": min(p1[0], p2[0]),
            "by0": min(p1[1], p2[1]),
            "bw": abs(dx_val),
            "bh": abs(dy_val),
            "gb_w": gb_w,
            "mid_x": (p1[0] + p2[0]) / 2.0,
            "mid_y": (p1[1] + p2[1]) / 2.0,
            "_is_aligned": True,
        }


def extract_structural_links_and_beams(
    active_columns: list,
    ftg_analysis: dict = None,
    b_unified: float = 25.0,
    level_type: str = "Above Footing Level (أعلى منسوب القواعد / رقاب الأعمدة)",
    has_wall: bool = True,
    h_wall: float = 3.0,
    t_wall: float = 12.0,
    gamma_brick: float = 1.80,
    axial_tie_ratio: float = 0.10,
    delta_settle_mm: float = 10.0,
    fcu: float = 250.0,
    fy: float = 4000.0,
    fy_st: float = 2400.0,
    cover_cm: float = 4.0,
    phi_bot: int = 16,
    phi_top: int = 12,
    phi_st: int = 8,
    phi_side: int = 10,
    stirrups_per_m: int = 6,
    user_overrides: dict = None,
) -> dict:
    """
    Extracts all structural links between active columns in Module 1,
    distinguishes Strap Beams (Module 9/10) from Ground Beams (Module 11),
    derives continuity condition, performs structural design, and groups into 3 models (B1, B2, B3).
    """
    if not active_columns:
        return {
            "all_links": [],
            "strap_beams": [],
            "ground_beams": [],
            "models_schedule": [],
            "models_dict": {},
            "boq": {
                "conc_vol_rc": 0.0, "steel_kg_tot": 0.0, "steel_ton_tot": 0.0,
                "cement_ton": 0.0, "cement_bags": 0, "sand_m3": 0.0, "gravel_m3": 0.0,
                "dia_map": {},
            },
            "classification_rows": [],
            "detailed_schedule_rows": [],
        }

    for idx, c in enumerate(active_columns):
        if "id" not in c:
            c["id"] = str(c.get("label", c.get("name", f"C{idx+1}")))
    cols_map = {c["id"]: c for c in active_columns}
    unique_xs, unique_ys, label_map_x, label_map_y = _get_grid_axes_gb(active_columns)

    # ── Step A: Identify Strap Beams from ftg_analysis (Module 9 & 10) ─────────
    strap_pair_keys = set()
    strap_beams = []

    if ftg_analysis:
        # 1. Edge Strap Footings (Module 9)
        for idx, sf in enumerate(ftg_analysis.get("edge_strap_footings", []), start=1):
            c1_id = sf["col1"]["id"]
            c2_id = sf["col2"]["id"]
            pair_key = tuple(sorted([c1_id, c2_id]))
            strap_pair_keys.add(pair_key)

            c1 = cols_map.get(c1_id, sf["col1"])
            c2 = cols_map.get(c2_id, sf["col2"])
            sD_cm = float(sf.get("strap_D", 100.0))
            sb_cm = float(sf.get("strap_b", 40.0))
            S_m = float(sf.get("S_m", math.dist((c1["x"], c1["y"]), (c2["x"], c2["y"]))))
            r9 = sf.get("calc_res", {})

            # Clear span
            c1_dim = float(c1.get("tc", 50.0)) / 100.0 if abs(c2["x"] - c1["x"]) >= abs(c2["y"] - c1["y"]) else float(c1.get("bc", 30.0)) / 100.0
            c2_dim = float(c2.get("tc", 50.0)) / 100.0 if abs(c2["x"] - c1["x"]) >= abs(c2["y"] - c1["y"]) else float(c2.get("bc", 30.0)) / 100.0
            Ln_m = max(0.50, S_m - (c1_dim / 2.0 + c2_dim / 2.0))

            n_top = int(r9.get("n_top", 5))
            n_bot = int(r9.get("n_bot", 2))
            st_per_m = int(round(r9.get("stirrup_per_m", 5.0)))
            n_br = int(r9.get("n_branches", 4))

            strap_beams.append({
                "elem_id": f"ST-{idx}",
                "tag": f"ST{idx}",
                "type": "Strap Beam (شداد جار جانبي)",
                "sub_type": "Edge Strap",
                "col1_id": c1_id,
                "col2_id": c2_id,
                "col1": c1,
                "col2": c2,
                "col_str": f"{c1_id} (جار) — {c2_id} (داخلي)",
                "axis_str": f"{c1.get('grid_x', '')}-{c1.get('grid_y', '')} إلى {c2.get('grid_x', '')}-{c2.get('grid_y', '')}",
                "span_m": S_m,
                "clear_span_m": Ln_m,
                "b_cm": sb_cm,
                "t_cm": sD_cm,
                "dimensions_str": f"{int(sb_cm)} × {int(sD_cm)}",
                "Mu_tm": abs(r9.get("Mu_neg", 0.0)),
                "Vu_ton": float(r9.get("Vu_ton", 0.0)),
                "Pu_tie_ton": 0.0,  # Moments and shear dominate strap beams
                "rft_top_str": f"{n_top}Ø22",
                "rft_bot_str": f"{n_bot}Ø16",
                "stirrups_str": f"{st_per_m}Ø10/m ({n_br} فروع)",
                "behavior": "نقل عزوم وقوى قص عالية ناتجة عن لامركزية عمود الجار (Moment & Shear Transfer)",
                "status": "✅ Safe",
            })

        # 2. Corner Diagonal Strap Footings (Module 10)
        start_dsf = len(strap_beams) + 1
        for idx, dsf in enumerate(ftg_analysis.get("corner_strap_footings", []), start=start_dsf):
            c1_id = dsf["col1"]["id"]
            c2_id = dsf["col2"]["id"]
            pair_key = tuple(sorted([c1_id, c2_id]))
            strap_pair_keys.add(pair_key)

            c1 = cols_map.get(c1_id, dsf["col1"])
            c2 = cols_map.get(c2_id, dsf["col2"])
            rec10 = dsf.get("rec", {})
            r10 = dsf.get("calc_res", {})
            sD_cm = float(r10.get("sD_cm", rec10.get("strap_D", 120.0)))
            sb_cm = float(dsf.get("strap_b", 40.0))
            S_m = float(dsf.get("S_m", math.dist((c1["x"], c1["y"]), (c2["x"], c2["y"]))))

            diag1 = math.sqrt((c1.get("tc", 50.0)/100.0)**2 + (c1.get("bc", 30.0)/100.0)**2)
            diag2 = math.sqrt((c2.get("tc", 50.0)/100.0)**2 + (c2.get("bc", 30.0)/100.0)**2)
            Ln_m = max(0.50, S_m - (diag1 / 2.0 + diag2 / 2.0))

            n_top = int(r10.get("n_top", 4))
            n_bot = int(r10.get("n_bot", 2))
            st_per_m = int(round(r10.get("stirrup_per_m", 5.0)))
            n_br = int(r10.get("n_branches", 2))

            strap_beams.append({
                "elem_id": f"DST-{len(strap_beams)+1}",
                "tag": f"ST{len(strap_beams)+1}",
                "type": "Diagonal Strap (شداد ركن مائل)",
                "sub_type": "Corner Diagonal Strap",
                "col1_id": c1_id,
                "col2_id": c2_id,
                "col1": c1,
                "col2": c2,
                "col_str": f"{c1_id} (ركن) — {c2_id} (داخلي)",
                "axis_str": f"مائل ({c1.get('grid_x', '')}-{c1.get('grid_y', '')} ↔ {c2.get('grid_x', '')}-{c2.get('grid_y', '')})",
                "span_m": S_m,
                "clear_span_m": Ln_m,
                "b_cm": sb_cm,
                "t_cm": sD_cm,
                "dimensions_str": f"{int(sb_cm)} × {int(sD_cm)}",
                "Mu_tm": abs(r10.get("Mu_neg_tm", 0.0)),
                "Vu_ton": float(r10.get("Vu_ton", 0.0)),
                "Pu_tie_ton": 0.0,
                "rft_top_str": f"{n_top}Ø22",
                "rft_bot_str": f"{n_bot}Ø16",
                "stirrups_str": f"{st_per_m}Ø10/m ({n_br} فروع)",
                "behavior": "نقل عزوم انحناء وقص ولي لعمود الجار الركني (Bending, Shear & Torsion)",
                "status": "✅ Safe",
            })

    # ── Step B: Extract Grid Lines and Find Connecting Ground Beams ───────────
    # Group columns into horizontal lines (same y) and vertical lines (same x)
    def _cluster_cols_by_axis(columns, axis="y", tol=0.35):
        sc = sorted(columns, key=lambda c: c[axis])
        lines = []
        if not sc:
            return lines
        cur_line = [sc[0]]
        cur_val = sc[0][axis]
        for c in sc[1:]:
            if abs(c[axis] - cur_val) <= tol:
                cur_line.append(c)
                cur_val = sum(x[axis] for x in cur_line) / len(cur_line)
            else:
                lines.append(cur_line)
                cur_line = [c]
                cur_val = c[axis]
        if cur_line:
            lines.append(cur_line)
        return lines

    h_lines = _cluster_cols_by_axis(active_columns, axis="y")
    v_lines = _cluster_cols_by_axis(active_columns, axis="x")

    raw_ground_spans = []

    # 1. Process Horizontal Grid Lines (X-Direction Beams)
    for line in h_lines:
        line_cols = sorted(line, key=lambda c: c["x"])
        m = len(line_cols)
        if m < 2:
            continue

        for k in range(m - 1):
            cA = line_cols[k]
            cB = line_cols[k + 1]
            pair_key = tuple(sorted([cA["id"], cB["id"]]))

            # Check if this span is already a Strap Beam
            if pair_key in strap_pair_keys:
                continue

            # Support Condition derivation:
            if m == 2:
                supp_cond = "Simply Supported (حر من الطرفين)"
            else:
                if k == 0 or k == m - 2:
                    supp_cond = "Continuous from One End (مستمر من طرف واحد)"
                else:
                    supp_cond = "Continuous from Both Ends (مستمر من الطرفين)"

            S_m = math.dist((cA["x"], cA["y"]), (cB["x"], cB["y"]))
            if S_m > 7.50:
                continue
            colA_w = float(cA.get("width_m", cA.get("tc", 50.0)/100.0))
            colB_w = float(cB.get("width_m", cB.get("tc", 50.0)/100.0))
            Ln_m = max(0.40, S_m - (colA_w / 2.0 + colB_w / 2.0))

            axis_name = cA.get("grid_y", f"X-Line @ y={cA['y']:.2f}")

            raw_ground_spans.append({
                "dir": "X",
                "col1": cA,
                "col2": cB,
                "col1_id": cA["id"],
                "col2_id": cB["id"],
                "axis_name": axis_name,
                "S_m": S_m,
                "Ln_m": Ln_m,
                "supp_cond": supp_cond,
                "m_cols_on_line": m,
                "span_idx": k,
            })

    # 2. Process Vertical Grid Lines (Y-Direction Beams)
    for line in v_lines:
        line_cols = sorted(line, key=lambda c: c["y"])
        n = len(line_cols)
        if n < 2:
            continue

        for k in range(n - 1):
            cA = line_cols[k]
            cB = line_cols[k + 1]
            pair_key = tuple(sorted([cA["id"], cB["id"]]))

            # Check if this span is already a Strap Beam
            if pair_key in strap_pair_keys:
                continue

            # Support Condition derivation:
            if n == 2:
                supp_cond = "Simply Supported (حر من الطرفين)"
            else:
                if k == 0 or k == n - 2:
                    supp_cond = "Continuous from One End (مستمر من طرف واحد)"
                else:
                    supp_cond = "Continuous from Both Ends (مستمر من الطرفين)"

            S_m = math.dist((cA["x"], cA["y"]), (cB["x"], cB["y"]))
            if S_m > 7.50:
                continue
            colA_h = float(cA.get("height_m", cA.get("bc", 30.0)/100.0))
            colB_h = float(cB.get("height_m", cB.get("bc", 30.0)/100.0))
            Ln_m = max(0.40, S_m - (colA_h / 2.0 + colB_h / 2.0))

            axis_name = cA.get("grid_x", f"Y-Line @ x={cA['x']:.2f}")

            raw_ground_spans.append({
                "dir": "Y",
                "col1": cA,
                "col2": cB,
                "col1_id": cA["id"],
                "col2_id": cB["id"],
                "axis_name": axis_name,
                "S_m": S_m,
                "Ln_m": Ln_m,
                "supp_cond": supp_cond,
                "m_cols_on_line": n,
                "span_idx": k,
            })

    # ── Step B.2: Enforce ECP 203 Section 6 Connectivity & Minimum 3-Way Framing ──
    # Strict compliance with ECP 203:
    # 1. Strict span limitation: S <= 7.50 m (prevents huge illogical spans across void bays)
    # 2. Orthogonal inward T-joints for edge columns to prevent diagonal slicing across bays
    # 3. Localized corner diagonal ties strictly for true building envelope corners (S <= 8.50 m)
    # 4. Perimeter gap ties (S <= 6.50 m) for re-entrant / missing corner bays
    # 5. Fallback tie search ensuring every column has >= 3 distinct directional restraints

    MAX_SPAN_GRID = 7.50
    # MAX_SPAN_DIAG removed per ECP 203 (no diagonal corner ties)

    connected_pairs = set()
    for sb in strap_beams:
        c1_id = sb["col1_id"]
        c2_id = sb["col2_id"]
        connected_pairs.add(tuple(sorted([c1_id, c2_id])))

    for sp in raw_ground_spans:
        connected_pairs.add(tuple(sorted([sp["col1_id"], sp["col2_id"]])))

    cen_x = sum(c["x"] for c in active_columns) / max(1, len(active_columns))
    cen_y = sum(c["y"] for c in active_columns) / max(1, len(active_columns))

    def _get_col_links(cid):
        conns = []
        for sp in raw_ground_spans:
            if sp["col1_id"] == cid:
                conns.append((sp["col2"], sp["dir"]))
            elif sp["col2_id"] == cid:
                conns.append((sp["col1"], sp["dir"]))
        for sb in strap_beams:
            if sb["col1_id"] == cid:
                conns.append((sb["col2"], "Strap"))
            elif sb["col2_id"] == cid:
                conns.append((sb["col1"], "Strap"))
        return conns

    def _add_tie_span(cA, cB, dir_code, axis_lbl, supp_cond_desc, is_t_joint=False):
        pair_k = tuple(sorted([cA["id"], cB["id"]]))
        if pair_k in connected_pairs:
            return False
        connected_pairs.add(pair_k)
        S_m = math.dist((cA["x"], cA["y"]), (cB["x"], cB["y"]))
        colA_w = float(cA.get("width_m", cA.get("tc", 50.0) / 100.0))
        colB_w = float(cB.get("width_m", cB.get("tc", 50.0) / 100.0))
        Ln_m = max(0.40, S_m - (colA_w / 2.0 + colB_w / 2.0))

        raw_ground_spans.append({
            "dir": dir_code,
            "col1": cA,
            "col2": cB,
            "col1_id": cA["id"],
            "col2_id": cB["id"],
            "axis_name": axis_lbl,
            "S_m": S_m,
            "Ln_m": Ln_m,
            "supp_cond": supp_cond_desc,
            "m_cols_on_line": 2,
            "span_idx": 0,
            "is_3way_tie": True,
            "is_t_joint": is_t_joint,
        })
        return True

    # 1. Inward Orthogonal T-Joints for Edge Columns (ECP 203 Section 6)
    # If an edge column lacks an inward tie, it drops a perpendicular tie into the nearest parallel beam
    for c in active_columns:
        links = _get_col_links(c["id"])
        x_links = [nb for (nb, d) in links if d == "X" or abs(nb["y"] - c["y"]) <= 0.35]
        y_links = [nb for (nb, d) in links if d == "Y" or abs(nb["x"] - c["x"]) <= 0.35]
        inward_y_dir = +1 if cen_y > c["y"] else -1
        inward_x_dir = +1 if cen_x > c["x"] else -1

        has_inward_y = any((nb["y"] - c["y"]) * inward_y_dir > 0.4 for nb in y_links)
        if not has_inward_y and len(x_links) >= 1:
            best_tj = None
            min_tj_dy = 999.0
            for sp in list(raw_ground_spans):
                if sp["dir"] == "X":
                    sp_y = (sp["col1"]["y"] + sp["col2"]["y"]) / 2.0
                    dy = (sp_y - c["y"]) * inward_y_dir
                    if 0.5 <= dy <= MAX_SPAN_GRID:
                        x_min_sp = min(sp["col1"]["x"], sp["col2"]["x"]) - 1.50
                        x_max_sp = max(sp["col1"]["x"], sp["col2"]["x"]) + 1.50
                        if x_min_sp <= c["x"] <= x_max_sp:
                            if dy < min_tj_dy:
                                min_tj_dy = dy
                                best_tj = (sp, c["x"], sp_y)
            if best_tj:
                target_sp, tj_x, tj_y = best_tj
                tj_node = {
                    "id": f"TJ-{c['id']}-H",
                    "x": tj_x,
                    "y": tj_y,
                    "tc": 30.0,
                    "bc": 30.0,
                    "pu_tot": float(c.get("pu_tot", 60.0)) * 0.5,
                    "grid_x": f"TJ-{c['id']}",
                    "grid_y": f"TJ-{c['id']}",
                    "is_t_joint": True,
                }
                _add_tie_span(
                    c, tj_node, "Y",
                    f"سملة تفرعية متعامدة Y ({c['id']} ➔ {target_sp['axis_name']})",
                    "Simply Supported (سملة تفرعية متعامدة Y)",
                    is_t_joint=True
                )

        has_inward_x = any((nb["x"] - c["x"]) * inward_x_dir > 0.4 for nb in x_links)
        if not has_inward_x and len(y_links) >= 1:
            best_tj = None
            min_tj_dx = 999.0
            for sp in list(raw_ground_spans):
                if sp["dir"] == "Y":
                    sp_x = (sp["col1"]["x"] + sp["col2"]["x"]) / 2.0
                    dx = (sp_x - c["x"]) * inward_x_dir
                    if 0.5 <= dx <= MAX_SPAN_GRID:
                        y_min_sp = min(sp["col1"]["y"], sp["col2"]["y"]) - 1.50
                        y_max_sp = max(sp["col1"]["y"], sp["col2"]["y"]) + 1.50
                        if y_min_sp <= c["y"] <= y_max_sp:
                            if dx < min_tj_dx:
                                min_tj_dx = dx
                                best_tj = (sp, sp_x, c["y"])
            if best_tj:
                target_sp, tj_x, tj_y = best_tj
                tj_node = {
                    "id": f"TJ-{c['id']}-V",
                    "x": tj_x,
                    "y": tj_y,
                    "tc": 30.0,
                    "bc": 30.0,
                    "pu_tot": float(c.get("pu_tot", 60.0)) * 0.5,
                    "grid_x": f"TJ-{c['id']}",
                    "grid_y": f"TJ-{c['id']}",
                    "is_t_joint": True,
                }
                _add_tie_span(
                    c, tj_node, "X",
                    f"سملة تفرعية متعامدة X ({c['id']} ➔ {target_sp['axis_name']})",
                    "Simply Supported (سملة تفرعية متعامدة X)",
                    is_t_joint=True
                )

    # 2. Strict ECP 203 Rule for Corner Isolated Footings & Orthogonal Ties:
    # Under ECP 203 Section 6 & ECP 202, connecting isolated footings requires ties in
    # the 2 principal orthogonal directions (X and Y).
    # Corner footings naturally connect to their 2 adjacent edge columns via 2 orthogonal
    # ground beams (1 along X, 1 along Y). This provides complete 2D translational restraint
    # (Rx, Ry), transmits the 10% Pu axial tie action, and mitigates differential settlement.
    # Therefore, exactly 2 orthogonal tie beams are completely sufficient per code.
    # Strictly NO diagonal or inclined ground beams are permitted for corner footings.

    def _is_col_fully_braced(cid):
        links = _get_col_links(cid)
        c = cols_map.get(cid)
        if not c:
            return True
        has_x = any(d == "X" or abs(nb["y"] - c["y"]) <= 0.35 for (nb, d) in links)
        has_y = any(d == "Y" or abs(nb["x"] - c["x"]) <= 0.35 for (nb, d) in links)
        return has_x and has_y

    # 3. Perimeter Orthogonal Gap Ties (Strictly Collinear X or Y only, NO Diagonals)
    # If any non-corner column still lacks bracing in X or Y, connect strictly along the collinear axis.
    for c in active_columns:
        if _is_col_fully_braced(c["id"]):
            continue
        links = _get_col_links(c["id"])
        has_x = any(d == "X" or abs(nb["y"] - c["y"]) <= 0.35 for (nb, d) in links)
        has_y = any(d == "Y" or abs(nb["x"] - c["x"]) <= 0.35 for (nb, d) in links)

        # Missing X tie: look for collinear candidate in X (same Y within 0.35m)
        if not has_x:
            best_cand_x = None
            min_dx = 999.0
            for cand in active_columns:
                if cand["id"] == c["id"]:
                    continue
                if abs(cand["y"] - c["y"]) <= 0.35:
                    dx = abs(cand["x"] - c["x"])
                    if 0.5 <= dx <= MAX_SPAN_GRID and dx < min_dx:
                        min_dx = dx
                        best_cand_x = cand
            if best_cand_x:
                _add_tie_span(
                    c, best_cand_x, "X",
                    f"سملة ربط متعامدة X ({c['id']} ↔ {best_cand_x['id']})",
                    "Simply Supported (سملة ربط متعامدة X)"
                )

        # Missing Y tie: look for collinear candidate in Y (same X within 0.35m)
        if not has_y:
            best_cand_y = None
            min_dy = 999.0
            for cand in active_columns:
                if cand["id"] == c["id"]:
                    continue
                if abs(cand["x"] - c["x"]) <= 0.35:
                    dy = abs(cand["y"] - c["y"])
                    if 0.5 <= dy <= MAX_SPAN_GRID and dy < min_dy:
                        min_dy = dy
                        best_cand_y = cand
            if best_cand_y:
                _add_tie_span(
                    c, best_cand_y, "Y",
                    f"سملة ربط متعامدة Y ({c['id']} ↔ {best_cand_y['id']})",
                    "Simply Supported (سملة ربط متعامدة Y)"
                )


    # ── Step C: Structural Design of Each Ground Beam per Module 11 Rules ──────
    is_at_footing = "At Footing Level" in level_type
    w_wall = h_wall * (t_wall / 100.0) * gamma_brick if has_wall else 0.0

    analyzed_ground_beams = []
    for idx, sp in enumerate(raw_ground_spans, start=1):
        cA = sp["col1"]
        cB = sp["col2"]
        S_m = sp["S_m"]
        Ln_m = sp["Ln_m"]
        supp_cond = sp["supp_cond"]

        # Governing column load for tie action
        PuA = float(cA.get("pu_tot", cA.get("Pu", 60.0)))
        PuB = float(cB.get("pu_tot", cB.get("Pu", 60.0)))
        Pu_max_col = max(PuA, PuB)
        Pu_tie = axial_tie_ratio * Pu_max_col  # ton

        # Preliminary trial depth for own-weight & deflection
        if "Simply Supported" in supp_cond or "حر" in supp_cond:
            L_d_limit = 16.0
            coeff_pos = 1.0 / 8.0
            coeff_neg = 1.0 / 24.0
            coeff_V = 0.50
        elif "One End" in supp_cond or "طرف واحد" in supp_cond:
            L_d_limit = 18.5
            coeff_pos = 1.0 / 10.0
            coeff_neg = 1.0 / 10.0
            coeff_V = 0.60
        else:
            L_d_limit = 21.0
            coeff_pos = 1.0 / 12.0
            coeff_neg = 1.0 / 12.0
            coeff_V = 0.55

        # Effective design span L
        d_trial_m = (S_m * 100.0 / L_d_limit - cover_cm) / 100.0
        L_des = min(S_m, Ln_m + max(0.20, d_trial_m))

        # Trial section
        t_trial = max(40.0, math.ceil((L_des * 100.0 / L_d_limit + cover_cm) / 5.0) * 5.0)
        w_ow = (b_unified / 100.0) * (t_trial / 100.0) * 2.50
        w_DL = w_ow + w_wall
        w_u_grav = 1.4 * w_DL

        # Internal gravity forces
        Mu_pos_grav = coeff_pos * w_u_grav * (L_des ** 2)
        Mu_neg_grav = coeff_neg * w_u_grav * (L_des ** 2)
        Qu_grav = coeff_V * w_u_grav * L_des

        # Differential settlement calculations (if at footing level)
        if is_at_footing:
            Ec = 44000.0 * math.sqrt(max(1.0, fcu / 10.0))  # kg/cm²
            Ig = (b_unified * (t_trial ** 3)) / 12.0
            Ie = 0.35 * Ig
            delta_cm = delta_settle_mm / 10.0
            L_cm = L_des * 100.0
            M_delta_kgcm = (6.0 * Ec * Ie * delta_cm) / (L_cm ** 2) if L_cm > 0 else 0.0
            M_delta_tonm = M_delta_kgcm / 100000.0
            Mu_delta = 1.4 * M_delta_tonm
            Qu_delta = 1.4 * ((2.0 * M_delta_tonm) / max(0.5, L_des))
        else:
            Mu_delta = 0.0
            Qu_delta = 0.0

        Mu_pos = Mu_pos_grav + Mu_delta
        Mu_neg = Mu_neg_grav + Mu_delta
        Qu = Qu_grav + Qu_delta

        # Depth requirement (t_calc)
        d_defl = (L_des * 100.0) / L_d_limit
        d_flex = 3.50 * math.sqrt((Mu_pos * 100000.0) / (max(1.0, fcu) * b_unified)) if Mu_pos > 0 else 25.0
        t_calc = float(math.ceil(max(d_defl + cover_cm, d_flex + cover_cm, 40.0) / 5.0) * 5.0)

        # Flexural + Axial Tie Design
        d_exec = max(10.0, t_calc - cover_cm)
        denom = math.sqrt((Mu_pos * 100000.0) / (max(1.0, fcu) * b_unified)) if Mu_pos > 0 else 1.0
        C1 = d_exec / denom if denom > 0 else 5.0
        if C1 >= 4.85:
            J = 0.826
        elif C1 < 2.78:
            J = 0.670
        else:
            term = max(0.0, 1.0 - (2.0 * Mu_pos * 100000.0) / (0.85 * fcu * b_unified * (d_exec ** 2)))
            cd_ratio = (1.0 - math.sqrt(term)) / 0.80
            J = min(0.826, max(0.67, 1.0 - 0.40 * cd_ratio))

        # Bottom steel: Flexure + half of axial tie action
        As_bot_flex = (Mu_pos * 100000.0) / (fy * J * d_exec) if (fy * J * d_exec) > 0 else 0.0
        As_tie = (Pu_tie * 1000.0) / (fy / 1.15) if fy > 0 else 0.0  # cm²
        As_min = max(0.0015 * b_unified * d_exec, (1.1 / fy) * b_unified * d_exec)
        As_bot_req = max(As_bot_flex + As_tie / 2.0, As_min)

        # Top steel: Negative moment + half of axial tie action
        As_top_flex = (Mu_neg * 100000.0) / (fy * 0.826 * d_exec) if (fy * 0.826 * d_exec) > 0 else 0.0
        As_top_min = max(0.20 * As_bot_req, 0.0015 * b_unified * d_exec)
        As_top_req = max(As_top_flex + As_tie / 2.0, As_top_min)

        # Rebar bar counts
        area_1bot = math.pi * ((phi_bot / 10.0) ** 2) / 4.0
        n_bot = max(2, int(math.ceil(As_bot_req / max(0.01, area_1bot))))
        area_1top = math.pi * ((phi_top / 10.0) ** 2) / 4.0
        n_top = max(2, int(math.ceil(As_top_req / max(0.01, area_1top))))

        # Shrinkage side bars
        if t_calc >= 60.0:
            side_spaces = math.ceil((t_calc - 2.0 * cover_cm) / 30.0)
            n_side_rows = max(1, side_spaces - 1)
        else:
            n_side_rows = 0
        total_side_bars = 2 * n_side_rows

        # Shear & Stirrups
        qu = (Qu * 1000.0) / (b_unified * d_exec) if (b_unified * d_exec) > 0 else 0.0
        qcu = 0.75 * math.sqrt(fcu / 1.5)
        qu_max = 2.20 * math.sqrt(fcu / 1.5)
        n_branches = 4 if b_unified >= 40.0 else 2
        area_1st = math.pi * ((phi_st / 10.0) ** 2) / 4.0
        As_st_prov = n_branches * area_1st * stirrups_per_m

        if qu > qu_max:
            shear_status = "⚠️ غير آمن قصاً (يلزم زيادة القطاع)"
            st_req_per_m = stirrups_per_m
        elif qu > qcu:
            qsu = qu - (qcu / 2.0)
            As_st_req = (qsu * b_unified * 100.0) / (fy_st / 1.15) if fy_st > 0 else 0.0
            st_req_per_m = max(stirrups_per_m, int(math.ceil(As_st_req / (n_branches * area_1st))))
            shear_status = "✅ آمن بالكانات"
        else:
            st_req_per_m = stirrups_per_m
            shear_status = "✅ آمن خرسانة فقط"

        # Demand Index for Sorting & Grouping: Mu or As_bot * t_calc
        demand_score = round(Mu_pos * 10.0 + As_bot_req * (t_calc / 10.0), 2)

        analyzed_ground_beams.append({
            "elem_id": f"GB-{idx}",
            "beam_id": f"GB-{idx}",
            "dir": sp["dir"],
            "col1_id": cA["id"],
            "col2_id": cB["id"],
            "col1": cA,
            "col2": cB,
            "axis_name": sp["axis_name"],
            "col_str": f"{cA['id']} — {cB['id']}",
            "axis_str": f"{cA.get('grid_x', '')}-{cA.get('grid_y', '')} إلى {cB.get('grid_x', '')}-{cB.get('grid_y', '')}",
            "span_m": S_m,
            "clear_span_m": Ln_m,
            "L_des": L_des,
            "supp_cond": supp_cond,
            "Pu_max_col": Pu_max_col,
            "Pu_tie": Pu_tie,
            "b_cm": b_unified,
            "t_calc": t_calc,
            "Mu_pos": Mu_pos,
            "Mu_neg": Mu_neg,
            "Qu": Qu,
            "As_bot_req": As_bot_req,
            "As_top_req": As_top_req,
            "n_bot": n_bot,
            "phi_bot": phi_bot,
            "n_top": n_top,
            "phi_top": phi_top,
            "total_side_bars": total_side_bars,
            "phi_side": phi_side,
            "stirrups_per_m": st_req_per_m,
            "phi_st": phi_st,
            "n_branches": n_branches,
            "demand_score": demand_score,
            "shear_status": shear_status,
            "coeff_pos": coeff_pos,
            "coeff_neg": coeff_neg,
            "coeff_V": coeff_V,
            "Mu_delta": Mu_delta,
            "Qu_delta": Qu_delta,
            "w_wall": w_wall,
            "As_tie": As_tie,
        })

    # ── Step D: AUTOMATIC GROUPING INTO 3 TYPES (B1, B2, B3) ───────────────────
    # Sort all analyzed beams in descending order based on structural demand
    analyzed_ground_beams.sort(key=lambda b: b["demand_score"], reverse=True)

    n_tot_gb = len(analyzed_ground_beams)
    group_assignments = {}  # elem_id -> "GB1", "GB2", or "GB3"

    if n_tot_gb == 0:
        pass
    elif n_tot_gb == 1:
        group_assignments[analyzed_ground_beams[0]["elem_id"]] = "GB1"
    elif n_tot_gb == 2:
        group_assignments[analyzed_ground_beams[0]["elem_id"]] = "GB1"
        group_assignments[analyzed_ground_beams[1]["elem_id"]] = "GB2"
    else:
        cut1 = int(math.ceil(n_tot_gb / 3.0))
        cut2 = int(math.ceil(2.0 * n_tot_gb / 3.0))
        for i, b in enumerate(analyzed_ground_beams):
            if i < cut1:
                group_assignments[b["elem_id"]] = "GB1"
            elif i < cut2:
                group_assignments[b["elem_id"]] = "GB2"
            else:
                group_assignments[b["elem_id"]] = "GB3"

    # Compute Governing Envelope for each group
    models_dict = {}
    overrides = user_overrides or {}

    for mark, label in [
        ("GB1", "GB1 (Heavy — قطاع ثقيل لأعلى عزوم وبحور)"),
        ("GB2", "GB2 (Medium — قطاع متوسط للمتطلبات الإنشائية الوسطى)"),
        ("GB3", "GB3 (Light — قطاع خفيف للبحور القصيرة وقواطيع الحوائط)"),
    ]:
        grp_beams = [b for b in analyzed_ground_beams if group_assignments.get(b["elem_id"]) == mark]
        if not grp_beams:
            continue

        env_t = max(b["t_calc"] for b in grp_beams)
        env_t = float(math.ceil(env_t / 5.0) * 5.0)
        ov_t = float(overrides.get(f"{mark}_t", overrides.get(f"B{mark[2:]}_t", env_t)))
        m_phi_bot = int(overrides.get(f"{mark}_phi_bot", overrides.get(f"B{mark[2:]}_phi_bot", phi_bot)))
        m_phi_top = int(overrides.get(f"{mark}_phi_top", overrides.get(f"B{mark[2:]}_phi_top", phi_top)))

        # Dynamic Recalculation of Section Forces & Reinforcement for all beams with depth ov_t and diameters m_phi_bot, m_phi_top
        for b in grp_beams:
            d_exec = max(10.0, ov_t - cover_cm)
            w_ow = (b_unified / 100.0) * (ov_t / 100.0) * 2.50
            w_DL = w_ow + b.get("w_wall", 0.0)
            w_u_grav = 1.4 * w_DL
            L_des = b["L_des"]
            Mu_pos = b.get("coeff_pos", 0.125) * w_u_grav * (L_des ** 2) + b.get("Mu_delta", 0.0)
            Mu_neg = b.get("coeff_neg", 0.0833) * w_u_grav * (L_des ** 2) + b.get("Mu_delta", 0.0)
            Qu = b.get("coeff_V", 0.5) * w_u_grav * L_des + b.get("Qu_delta", 0.0)

            denom = math.sqrt((Mu_pos * 100000.0) / (max(1.0, fcu) * b_unified)) if Mu_pos > 0 else 1.0
            C1 = d_exec / denom if denom > 0 else 5.0
            if C1 >= 4.85:
                J = 0.826
            elif C1 < 2.78:
                J = 0.670
            else:
                term = max(0.0, 1.0 - (2.0 * Mu_pos * 100000.0) / (0.85 * fcu * b_unified * (d_exec ** 2)))
                cd_ratio = (1.0 - math.sqrt(term)) / 0.80
                J = min(0.826, max(0.67, 1.0 - 0.40 * cd_ratio))

            As_bot_flex = (Mu_pos * 100000.0) / (fy * J * d_exec) if (fy * J * d_exec) > 0 else 0.0
            As_min = max(0.0015 * b_unified * d_exec, (1.1 / fy) * b_unified * d_exec)
            As_bot_req = max(As_bot_flex + b.get("As_tie", 0.0) / 2.0, As_min)

            As_top_flex = (Mu_neg * 100000.0) / (fy * 0.826 * d_exec) if (fy * 0.826 * d_exec) > 0 else 0.0
            As_top_min = max(0.20 * As_bot_req, 0.0015 * b_unified * d_exec)
            As_top_req = max(As_top_flex + b.get("As_tie", 0.0) / 2.0, As_top_min)

            qu = (Qu * 1000.0) / (b_unified * d_exec) if (b_unified * d_exec) > 0 else 0.0
            qcu = 0.75 * math.sqrt(fcu / 1.5)
            qu_max = 2.20 * math.sqrt(fcu / 1.5)
            n_branches = 4 if b_unified >= 40.0 else 2
            area_1st = math.pi * ((phi_st / 10.0) ** 2) / 4.0
            fy_st = 2400.0 if phi_st <= 8 else 4000.0

            if qu > qu_max:
                shear_status = "⚠️ غير آمن قصاً (يلزم زيادة القطاع)"
                st_req_per_m = stirrups_per_m
            elif qu > qcu:
                qsu = qu - (qcu / 2.0)
                As_st_req = (qsu * b_unified * 100.0) / (fy_st / 1.15) if fy_st > 0 else 0.0
                st_req_per_m = max(stirrups_per_m, int(math.ceil(As_st_req / (n_branches * area_1st))))
                shear_status = "✅ آمن بالكانات"
            else:
                st_req_per_m = stirrups_per_m
                shear_status = "✅ آمن خرسانة فقط"

            area_1bot = math.pi * ((m_phi_bot / 10.0) ** 2) / 4.0
            n_bot_des = max(2, int(math.ceil(As_bot_req / max(0.01, area_1bot))))
            area_1top = math.pi * ((m_phi_top / 10.0) ** 2) / 4.0
            n_top_des = max(2, int(math.ceil(As_top_req / max(0.01, area_1top))))

            b["Mu_pos"] = Mu_pos
            b["Mu_neg"] = Mu_neg
            b["Qu"] = Qu
            b["As_bot_req"] = As_bot_req
            b["As_top_req"] = As_top_req
            b["n_bot"] = n_bot_des
            b["n_top"] = n_top_des
            b["phi_bot"] = m_phi_bot
            b["phi_top"] = m_phi_top
            b["stirrups_per_m"] = st_req_per_m
            b["shear_status"] = shear_status

        # Governing Envelope based on execution depth ov_t
        env_As_bot = max(b["As_bot_req"] for b in grp_beams)
        env_As_top = max(b["As_top_req"] for b in grp_beams)
        env_st_m = max(b["stirrups_per_m"] for b in grp_beams)
        env_branches = 4 if b_unified >= 40.0 else 2

        area_1bot = math.pi * ((m_phi_bot / 10.0) ** 2) / 4.0
        env_nbot = max(2, int(math.ceil(env_As_bot / max(0.01, area_1bot))))
        area_1top = math.pi * ((m_phi_top / 10.0) ** 2) / 4.0
        env_ntop = max(2, int(math.ceil(env_As_top / max(0.01, area_1top))))

        # Apply User Interactive Overrides if provided (or default to dynamically recalculated env_nbot, env_ntop, env_st_m)
        ov_nbot = int(overrides.get(f"{mark}_nbot", overrides.get(f"B{mark[2:]}_nbot", env_nbot)))
        ov_ntop = int(overrides.get(f"{mark}_ntop", overrides.get(f"B{mark[2:]}_ntop", env_ntop)))
        ov_st = int(overrides.get(f"{mark}_stirrups", overrides.get(f"B{mark[2:]}_stirrups", env_st_m)))

        if ov_t >= 60.0:
            side_spaces = math.ceil((ov_t - 2.0 * cover_cm) / 30.0)
            env_side_rows = max(1, side_spaces - 1)
        else:
            env_side_rows = 0
        env_side_bars = 2 * env_side_rows

        tot_len_m = sum(b["span_m"] for b in grp_beams)

        models_dict[mark] = {
            "mark": mark,
            "label": label,
            "count": len(grp_beams),
            "total_len_m": tot_len_m,
            "b_cm": b_unified,
            "t_cm": ov_t,
            "t_env_calc": env_t,
            "n_bot": ov_nbot,
            "phi_bot": m_phi_bot,
            "n_top": ov_ntop,
            "phi_top": m_phi_top,
            "total_side_bars": env_side_bars,
            "phi_side": phi_side,
            "stirrups_per_m": ov_st,
            "phi_st": phi_st,
            "n_branches": env_branches,
            "rft_bot_str": f"{ov_nbot}Ø{m_phi_bot}",
            "rft_top_str": f"{ov_ntop}Ø{m_phi_top}",
            "rft_side_str": f"{env_side_bars}Ø{phi_side} (براندات)" if env_side_bars > 0 else "—",
            "stirrups_str": f"{ov_st}Ø{phi_st}/m ({env_branches} فروع)",
            "dimensions_str": f"{int(b_unified)} × {int(ov_t)}",
        }

    # Assign Model Tag & Final Exec Values to Each Ground Beam
    for b in analyzed_ground_beams:
        b["model_mark"] = group_assignments.get(b["elem_id"], "GB1")
        b["tag"] = b["model_mark"]
        m_info = models_dict.get(b["model_mark"], {})
        b["exec_t_cm"] = m_info.get("t_cm", b["t_calc"])
        b["exec_n_bot"] = m_info.get("n_bot", b["n_bot"])
        b["exec_n_top"] = m_info.get("n_top", b["n_top"])
        b["phi_bot"] = m_info.get("phi_bot", m_phi_bot)
        b["phi_top"] = m_info.get("phi_top", m_phi_top)
        b["exec_stirrups_per_m"] = m_info.get("stirrups_per_m", b["stirrups_per_m"])
        b["exec_side_bars"] = m_info.get("total_side_bars", 0)
        alg = align_ground_beam_coords(b, unique_xs, unique_ys)
        b["p1"] = alg["p1"]
        b["p2"] = alg["p2"]
        b["cl_coord"] = alg.get("cl_coord")
        b["cl_y"] = alg.get("cl_y")
        b["cl_x"] = alg.get("cl_x")
        b["bx0"] = alg.get("bx0")
        b["by0"] = alg.get("by0")
        b["bw"] = alg.get("bw")
        b["bh"] = alg.get("bh")
        b["_is_aligned"] = True

    # ── Step E: Master Ground Beams Schedule Table ─────────────────────────────
    models_schedule = []
    for mark in ["GB1", "GB2", "GB3"]:
        if mark in models_dict:
            m = models_dict[mark]
            models_schedule.append({
                "النموذج (Mark)": m["mark"],
                "التصنيف والأهمية الإنشائية": m["label"].split("—")[1].strip(" )") if "—" in m["label"] else m["label"],
                "الأبعاد b × t (cm)": m["dimensions_str"],
                "التسليح السفلي (Bottom Rft)": m["rft_bot_str"],
                "التسليح العلوي (Top Rft)": m["rft_top_str"],
                "براندات الانكماش (Side Bars)": m["rft_side_str"],
                "الكانات (Stirrups)": m["stirrups_str"],
                "العدد بالمشروع (Count)": f"{m['count']} سملة",
                "إجمالي الأطوال (Total Length)": f"{m['total_len_m']:.2f} m",
            })

    # ── Step F: Final Unified Classification Table (Strap + Ground Beams) ─────
    classification_rows = []
    # 1. Strap Beams
    for sb in strap_beams:
        classification_rows.append({
            "Element ID": sb["elem_id"],
            "Tag / Mark": sb["tag"],
            "Type (التصنيف الإنشائي)": sb["type"],
            "From Column — To Column": sb["col_str"],
            "From Axis — To Axis": sb["axis_str"],
            "Span L (m)": f"{sb['span_m']:.2f} m (صافي {sb['clear_span_m']:.2f}m)",
            "Cross-Section (b × t)": sb["dimensions_str"],
            "Structural Behavior / Notes": sb["behavior"],
            "Design Capacity / Forces": f"Mu = {sb['Mu_tm']:.1f} t.m | Vu = {sb['Vu_ton']:.1f} t",
            "Reinforcement Summary": f"علوي: {sb['rft_top_str']} | سفلي: {sb['rft_bot_str']} | كانات: {sb['stirrups_str']}",
        })

    # 2. Ground Beams
    for gb in analyzed_ground_beams:
        rft_str = f"سفلي: {gb['exec_n_bot']}Ø{gb['phi_bot']} | علوي: {gb['exec_n_top']}Ø{gb['phi_top']} | كانات: {gb['exec_stirrups_per_m']}Ø{gb['phi_st']}/m"
        if gb.get("exec_side_bars", 0) > 0:
            rft_str += f" | براندات: {gb['exec_side_bars']}Ø{gb['phi_side']}"

        classification_rows.append({
            "Element ID": gb["elem_id"],
            "Tag / Mark": gb["tag"],
            "Type (التصنيف الإنشائي)": f"Ground Beam (سمل أرضي — نموذج {gb['tag']})",
            "From Column — To Column": gb["col_str"],
            "From Axis — To Axis": gb["axis_str"],
            "Span L (m)": f"{gb['span_m']:.2f} m (صافي {gb['clear_span_m']:.2f}m)",
            "Cross-Section (b × t)": f"{int(gb['b_cm'])} × {int(gb['exec_t_cm'])}",
            "Structural Behavior / Notes": f"{gb['supp_cond']} | ربط محوري P_tie={gb['Pu_tie']:.1f}t (10% Pu)",
            "Design Capacity / Forces": f"Mu = {gb['Mu_pos']:.2f} t.m | Qu = {gb['Qu']:.2f} t",
            "Reinforcement Summary": rft_str,
        })

    # ── Step G: Ground Beams Detailed Bar Bending Schedule ─────────────────────
    detailed_schedule_rows = []
    for gb in analyzed_ground_beams:
        detailed_schedule_rows.append({
            "السمل (ID)": gb["elem_id"],
            "النموذج (Mark)": gb["tag"],
            "المحور الرابط (Axis)": gb["axis_str"],
            "الأعمدة المربوطة (Columns)": gb["col_str"],
            "البحر S (m)": f"{gb['span_m']:.2f}",
            "البحر الصافي Ln (m)": f"{gb['clear_span_m']:.2f}",
            "القطاع b × t (cm)": f"{int(gb['b_cm'])} × {int(gb['exec_t_cm'])}",
            "حالة الاستمرارية (Continuity)": gb["supp_cond"].split("(")[0].strip(),
            "عزم التصميم Mu (t.m)": f"{gb['Mu_pos']:.2f}",
            "قوة القص Qu (ton)": f"{gb['Qu']:.2f}",
            "قوة الربط المحوري P_tie (ton)": f"{gb['Pu_tie']:.2f}",
            "التسليح السفلي (Bottom Steel)": f"{gb['exec_n_bot']}Ø{gb['phi_bot']}",
            "التسليح العلوي (Top Steel)": f"{gb['exec_n_top']}Ø{gb['phi_top']}",
            "براندات الجوانب (Side Bars)": f"{gb['exec_side_bars']}Ø{gb['phi_side']}" if gb['exec_side_bars'] > 0 else "—",
            "الكانات (Stirrups)": f"{gb['exec_stirrups_per_m']}Ø{gb['phi_st']}/m",
            "حالة التحقق (Status)": gb["shear_status"],
        })

    # ── Step H: Bill of Quantities (BOQ) for Ground Beams ──────────────────────
    conc_vol_rc = 0.0
    steel_kg_tot = 0.0
    dia_map = {}

    def _add_dia_wt(d_mm, wt_kg, app_desc):
        if wt_kg <= 0:
            return
        if d_mm not in dia_map:
            dia_map[d_mm] = {"weight_kg": 0.0, "apps": app_desc}
        dia_map[d_mm]["weight_kg"] += wt_kg

    for gb in analyzed_ground_beams:
        b_m = gb["b_cm"] / 100.0
        t_m = gb["exec_t_cm"] / 100.0
        L_m = gb["span_m"]

        v_b = b_m * t_m * L_m
        conc_vol_rc += v_b

        # Steel weights
        L_bar_bot = L_m + 2.0 * max(0.40, (50.0 * gb["phi_bot"]) / 1000.0)
        wt_bot = gb["exec_n_bot"] * L_bar_bot * ((gb["phi_bot"] ** 2) / 162.0)

        L_bar_top = L_m + 2.0 * max(0.40, (50.0 * gb["phi_top"]) / 1000.0)
        wt_top = gb["exec_n_top"] * L_bar_top * ((gb["phi_top"] ** 2) / 162.0)

        wt_side = 0.0
        if gb["exec_side_bars"] > 0:
            L_bar_side = L_m + 0.30
            wt_side = gb["exec_side_bars"] * L_bar_side * ((gb["phi_side"] ** 2) / 162.0)

        st_w_m = (gb["b_cm"] - 2.0 * cover_cm) / 100.0
        st_h_m = (gb["exec_t_cm"] - 2.0 * cover_cm) / 100.0
        st_perim = 2.0 * (st_w_m + st_h_m) + 0.15
        if gb["n_branches"] == 4:
            st_perim *= 2.0
        n_st = max(5, int(math.ceil(gb["exec_stirrups_per_m"] * L_m)))
        wt_st = n_st * st_perim * ((gb["phi_st"] ** 2) / 162.0)

        wt_b_tot = wt_bot + wt_top + wt_side + wt_st
        steel_kg_tot += wt_b_tot

        _add_dia_wt(gb["phi_bot"], wt_bot, "تسليح سفلي رئيسي للسملات والميدات (Ground Beams Bottom Rebar)")
        _add_dia_wt(gb["phi_top"], wt_top, "تسليح علوي للسملات والميدات (Ground Beams Top Rebar)")
        if wt_side > 0:
            _add_dia_wt(gb["phi_side"], wt_side, "براندات انكماش جانبية للسملات (Ground Beams Side Shrinkage)")
        _add_dia_wt(gb["phi_st"], wt_st, "كانات السملات والميدات (Ground Beams Stirrups)")

    steel_ton_tot = steel_kg_tot / 1000.0
    cement_ton = (conc_vol_rc * 350.0) / 1000.0
    cement_bags = int(round(cement_ton * 1000.0 / 50.0))
    sand_m3 = conc_vol_rc * 0.40
    gravel_m3 = conc_vol_rc * 0.80

    boq = {
        "conc_vol_rc": conc_vol_rc,
        "steel_kg_tot": steel_kg_tot,
        "steel_ton_tot": steel_ton_tot,
        "cement_ton": cement_ton,
        "cement_bags": cement_bags,
        "sand_m3": sand_m3,
        "gravel_m3": gravel_m3,
        "dia_map": dia_map,
        "steel_ratio_kg_m3": (steel_kg_tot / conc_vol_rc) if conc_vol_rc > 0 else 0.0,
    }

    return {
        "all_links": classification_rows,
        "strap_beams": strap_beams,
        "ground_beams": analyzed_ground_beams,
        "models_schedule": models_schedule,
        "models_dict": models_dict,
        "boq": boq,
        "classification_rows": classification_rows,
        "detailed_schedule_rows": detailed_schedule_rows,
    }



def draw_ground_beams_layout_sketch(
    active_columns: list,
    gb_analysis: dict,
    slab_bounds: dict = None,
    title: str = "ECP 203 — Ground Beams & Tie Beams 2D Framing Plan",
):
    """
    Renders comprehensive 2D ground beams and tie beams framing plan sketch:
    - B1 Heavy Ground Beams: Royal Blue / Indigo (#1d4ed8)
    - B2 Medium Ground Beams: Emerald Green (#15803d)
    - B3 Light Ground Beams: Soft Violet / Purple (#7e22ce)
    - Strap Beams (ST): Warm Coral / Orange (#ea580c)
    - Strict Centerline Continuity: Adjacent spans share the exact same structural grid axis centerline
    - Outer building/slab footprint
    - Structural grid lines with circular bubbles, bay spans, and total dimensions
    - Shaded column rectangles with column IDs
    - Full Legend matching Master Models Schedule (100% data consistency)
    """
    if not active_columns:
        fig, ax = plt.subplots(figsize=(10, 8), dpi=160, facecolor="#ffffff")
        ax.text(0.5, 0.5, "No Active Columns Found / No columns active", ha="center", va="center", fontsize=14, color="#64748b")
        ax.axis("off")
        return fig

    # ── 1. Prepare Legend Rows & Data Model Ahead of Canvas Construction ──
    models_dict = gb_analysis.get("models_dict", {})
    strap_list = gb_analysis.get("strap_beams", [])
    color_meta = {
        "GB1": {"color": "#1d4ed8", "name": "Heavy Section"},
        "GB2": {"color": "#15803d", "name": "Medium Section"},
        "GB3": {"color": "#7e22ce", "name": "Light Section"},
        "ST":  {"color": "#ea580c", "name": "Strap Beams"},
    }

    leg_rows = []
    for mk in ["GB1", "GB2", "GB3"]:
        if mk in models_dict:
            m = models_dict[mk]
            meta = color_meta.get(mk, {"color": "#1e293b", "name": "Ground Beam"})
            sec_s = f"{int(m.get('b_cm', 25))} × {int(m.get('t_cm', 60))} cm"
            rft_parts = [
                f"Bottom: {m.get('n_bot', 2)}Ø{m.get('phi_bot', 16)}",
                f"Top: {m.get('n_top', 2)}Ø{m.get('phi_top', 12)}",
                f"Stirrups: {m.get('stirrups_per_m', 6)}Ø{m.get('phi_st', 8)}/m ({m.get('n_branches', 2)}-legs)",
            ]
            if m.get("total_side_bars", 0) > 0:
                rft_parts.append(f"Side: {m['total_side_bars']}Ø{m.get('phi_side', 10)}")

            rft_s = "   |   ".join(rft_parts)
            cnt_s = f"{m.get('count', 0)} Beams ({m.get('total_len_m', 0.0):.1f} m)"
            leg_rows.append({
                "mark": mk,
                "label": meta["name"],
                "color": meta["color"],
                "sec": sec_s,
                "rft": rft_s,
                "cnt": cnt_s,
            })

    if strap_list:
        meta_st = color_meta["ST"]
        leg_rows.append({
            "mark": "ST",
            "label": meta_st["name"],
            "color": meta_st["color"],
            "sec": "Design Specific",
            "rft": "Eccentricity ties for neighbor footings",
            "cnt": f"{len(strap_list)} Beams",
        })

    unique_xs, unique_ys, label_map_x, label_map_y = _get_grid_axes_gb(active_columns)

    col_xs = [float(c["x"]) for c in active_columns]
    col_ys = [float(c["y"]) for c in active_columns]

    eff_sb = slab_bounds or {}
    x_slab_min = float(eff_sb.get("min_x", unique_xs[0] if unique_xs else min(col_xs))) - float(eff_sb.get("cant_left", 0.0) or 0.0)
    x_slab_max = float(eff_sb.get("max_x", unique_xs[-1] if unique_xs else max(col_xs))) + float(eff_sb.get("cant_right", 0.0) or 0.0)
    y_slab_min = float(eff_sb.get("min_y", unique_ys[0] if unique_ys else min(col_ys))) - float(eff_sb.get("cant_bottom", 0.0) or 0.0)
    y_slab_max = float(eff_sb.get("max_y", unique_ys[-1] if unique_ys else max(col_ys))) + float(eff_sb.get("cant_top", 0.0) or 0.0)

    min_gx = unique_xs[0] if unique_xs else x_slab_min
    max_gx = unique_xs[-1] if unique_xs else x_slab_max
    min_gy = unique_ys[0] if unique_ys else y_slab_min
    max_gy = unique_ys[-1] if unique_ys else y_slab_max

    y_top_ref = max(y_slab_max, max_gy) + 0.6
    x_left_ref = min(x_slab_min, min_gx) - 0.6
    y_bottom_ref = min(y_slab_min, min_gy) - 0.6
    x_right_ref = max(x_slab_max, max_gx) + 0.6

    y_dim1 = y_top_ref + 0.5
    y_dim2 = y_top_ref + 1.2
    y_bubble = y_top_ref + 2.1

    x_dim1 = x_left_ref - 0.5
    x_dim2 = x_left_ref - 1.2
    x_bubble = x_left_ref - 2.1

    # ── 2. Algorithmic Plan Area & Aspect Ratio Optimization ──
    x_min_bound = x_bubble - 0.9
    x_max_bound = x_right_ref + 0.9
    y_min_bound = y_bottom_ref - 0.9
    y_max_bound = y_bubble + 0.9

    W_span = x_max_bound - x_min_bound
    H_span = y_max_bound - y_min_bound
    R_data = W_span / max(0.5, H_span)

    W_fig = 16.0
    W_box_in = 0.93 * W_fig  # ~14.88 in
    H_plan_target = W_box_in / R_data
    H_plan_in = max(7.5, min(15.5, H_plan_target))
    R_box = W_box_in / H_plan_in

    # Symmetrically pad limits so data aspect perfectly fills the subplot viewport (Zero letterbox waste)
    if R_data > R_box:
        delta_H = (W_span / R_box) - H_span
        y_min_eff = y_min_bound - delta_H / 2.0
        y_max_eff = y_max_bound + delta_H / 2.0
        x_min_eff = x_min_bound
        x_max_eff = x_max_bound
    else:
        delta_W = (H_span * R_box) - W_span
        x_min_eff = x_min_bound - delta_W / 2.0
        x_max_eff = x_max_bound + delta_W / 2.0
        y_min_eff = y_min_bound
        y_max_eff = y_max_bound

    n_leg = max(1, len(leg_rows))
    H_leg_in = max(1.8, 0.85 + n_leg * 0.44)
    H_fig = H_plan_in + H_leg_in + 0.35

    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, (ax, ax_leg) = plt.subplots(
        2, 1, figsize=(W_fig, H_fig), dpi=160, facecolor="#ffffff",
        gridspec_kw={"height_ratios": [H_plan_in, H_leg_in], "hspace": 0.04}
    )
    ax.set_facecolor("#f8fafc")
    ax_leg.set_facecolor("#ffffff")
    ax_leg.axis("off")

    # 1. Building Footprint
    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min
    if slab_w > 0 and slab_h > 0:
        slab_rect = patches.Rectangle(
            (x_slab_min, y_slab_min), slab_w, slab_h,
            facecolor="#f8fafc", edgecolor="#475569", lw=2.0, ls="-", zorder=1
        )
        ax.add_patch(slab_rect)
        ax.text(
            x_slab_min + 0.15, y_slab_max - 0.25, _ar("حدود المبنى الإنشائية (Building Perimeter)"),
            fontsize=8.5, color="#64748b", fontweight="bold", zorder=2
        )

    # 2. Structural Grid Lines, Bubbles & Dimensions
    for idx, gx in enumerate(unique_xs, start=1):
        lbl = label_map_x.get(gx, f"Y{idx}")
        ax.plot([gx, gx], [y_bottom_ref, y_bubble], color="#94a3b8", ls="--", lw=1.1, zorder=1.5)
        ax.text(gx, y_bubble, lbl, ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=10.5,
                bbox=dict(boxstyle="circle,pad=0.30", fc="#f8fafc", ec="#334155", lw=1.5), zorder=8)

    for idx, gy in enumerate(unique_ys, start=1):
        lbl = label_map_y.get(gy, f"X{idx}")
        ax.plot([x_bubble, x_right_ref], [gy, gy], color="#94a3b8", ls="--", lw=1.1, zorder=1.5)
        ax.text(x_bubble, gy, lbl, ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=10.5,
                bbox=dict(boxstyle="circle,pad=0.30", fc="#f8fafc", ec="#334155", lw=1.5), zorder=8)

    if len(unique_xs) > 1:
        for i in range(len(unique_xs) - 1):
            _hdim(ax, y_top_ref, unique_xs[i], unique_xs[i + 1], f"{unique_xs[i+1]-unique_xs[i]:.2f} m", side="top", fs=9.0, offset=0.5, draw_ext=False)
        _hdim(ax, y_top_ref, unique_xs[0], unique_xs[-1], f"Total L = {unique_xs[-1]-unique_xs[0]:.2f} m", side="top", fs=10.0, offset=1.2, draw_ext=False)

    if len(unique_ys) > 1:
        for j in range(len(unique_ys) - 1):
            _vdim(ax, x_left_ref, unique_ys[j], unique_ys[j + 1], f"{unique_ys[j+1]-unique_ys[j]:.2f} m", side="left", fs=9.0, offset=0.5, draw_ext=False)
        _vdim(ax, x_left_ref, unique_ys[0], unique_ys[-1], f"Total B = {unique_ys[-1]-unique_ys[0]:.2f} m", side="left", fs=10.0, offset=1.2, draw_ext=False)

    # 3. Ground Beams & Strap Beams Drawing
    color_map = {
        "GB1": {"fc": "#dbeafe", "ec": "#1d4ed8", "tc": "#1e40af", "badge_bg": "#eff6ff"},
        "GB2": {"fc": "#dcfce7", "ec": "#15803d", "tc": "#166534", "badge_bg": "#f0fdf4"},
        "GB3": {"fc": "#f3e8ff", "ec": "#7e22ce", "tc": "#6b21a8", "badge_bg": "#faf5ff"},
        "B1": {"fc": "#dbeafe", "ec": "#1d4ed8", "tc": "#1e40af", "badge_bg": "#eff6ff"},
        "B2": {"fc": "#dcfce7", "ec": "#15803d", "tc": "#166534", "badge_bg": "#f0fdf4"},
        "B3": {"fc": "#f3e8ff", "ec": "#7e22ce", "tc": "#6b21a8", "badge_bg": "#faf5ff"},
        "ST1": {"fc": "#ffedd5", "ec": "#ea580c", "tc": "#9a3412", "badge_bg": "#fff7ed"},
        "ST2": {"fc": "#ffedd5", "ec": "#ea580c", "tc": "#9a3412", "badge_bg": "#fff7ed"},
        "ST": {"fc": "#ffedd5", "ec": "#ea580c", "tc": "#9a3412", "badge_bg": "#fff7ed"},
    }

    all_gbs = gb_analysis.get("ground_beams", [])
    strap_list = gb_analysis.get("strap_beams", [])
    combined_elements = list(all_gbs) + list(strap_list)

    if not combined_elements:
        mid_x_c = (x_slab_min + x_slab_max) / 2.0
        mid_y_c = (y_slab_min + y_slab_max) / 2.0
        ax.text(
            mid_x_c, mid_y_c,
            _ar("لم يتم استخراج أي سملات أرضية بعد\nتأكد من وجود أعمدة مفعلة وشبكة محاور"),
            ha="center", va="center", fontsize=10.5, fontweight="bold", color="#92400e",
            bbox=dict(boxstyle="round,pad=0.7", fc="#fef3c7", ec="#f59e0b", lw=1.5, alpha=0.96),
            zorder=10
        )

    for b in combined_elements:
        alg = align_ground_beam_coords(b, unique_xs, unique_ys, active_columns=active_columns, slab_bounds=slab_bounds)
        p1 = alg["p1"]
        p2 = alg["p2"]
        dir_b = alg["dir"]
        bw_m = float(b.get("b_cm", 25.0)) / 100.0
        t_cm = int(b.get("exec_t_cm", b.get("t_calc", b.get("t_cm", 50.0))))
        b_cm = int(b.get("b_cm", 25.0))
        tag = b.get("tag", b.get("model_mark", "GB1"))
        cfg = color_map.get(tag, color_map.get("ST" if "ST" in str(tag) else "GB1", {"fc": "#f1f5f9", "ec": "#475569", "tc": "#334155", "badge_bg": "#ffffff"}))

        if dir_b == "X":
            bx0 = alg.get("bx0", min(p1[0], p2[0]))
            bw = alg.get("bw", abs(p2[0] - p1[0]))
            by0 = alg.get("by0", alg["cl_y"] - bw_m / 2.0)
            mid_y = alg.get("mid_y", by0 + bw_m / 2.0)
            rect = patches.Rectangle(
                (bx0, by0), bw, bw_m,
                facecolor=cfg["fc"], edgecolor=cfg["ec"], lw=1.8, alpha=0.92, zorder=3
            )
            ax.add_patch(rect)
            mid_x = bx0 + bw / 2.0
            rot = 0
        elif dir_b == "Y":
            by0 = alg.get("by0", min(p1[1], p2[1]))
            bh = alg.get("bh", abs(p2[1] - p1[1]))
            bx0 = alg.get("bx0", alg["cl_x"] - bw_m / 2.0)
            mid_x = alg.get("mid_x", bx0 + bw_m / 2.0)
            rect = patches.Rectangle(
                (bx0, by0), bw_m, bh,
                facecolor=cfg["fc"], edgecolor=cfg["ec"], lw=1.8, alpha=0.92, zorder=3
            )
            ax.add_patch(rect)
            mid_y = by0 + bh / 2.0
            rot = 90
        else: # DIAG
            p1_c = alg.get("p1", p1)
            p2_c = alg.get("p2", p2)
            dx_val = p2_c[0] - p1_c[0]
            dy_val = p2_c[1] - p1_c[1]
            th = math.atan2(dy_val, dx_val)
            nx = -math.sin(th) * bw_m / 2.0
            ny = math.cos(th) * bw_m / 2.0
            poly = patches.Polygon([
                (p1_c[0] + nx, p1_c[1] + ny), (p2_c[0] + nx, p2_c[1] + ny),
                (p2_c[0] - nx, p2_c[1] - ny), (p1_c[0] - nx, p1_c[1] - ny)
            ], facecolor=cfg["fc"], edgecolor=cfg["ec"], lw=1.8, alpha=0.92, zorder=3)
            ax.add_patch(poly)
            mid_x = alg.get("mid_x", (p1_c[0] + p2_c[0]) / 2.0)
            mid_y = alg.get("mid_y", (p1_c[1] + p2_c[1]) / 2.0)
            rot = math.degrees(th)
            if rot > 90:
                rot -= 180
            elif rot < -90:
                rot += 180

        lbl = str(tag)

        ax.text(
            mid_x, mid_y, lbl,
            ha="center", va="center", rotation=rot, fontsize=8.5, fontweight="bold", color=cfg["tc"],
            bbox=dict(boxstyle="round,pad=0.20", fc=cfg["badge_bg"], ec=cfg["ec"], lw=1.0, alpha=0.95),
            zorder=6
        )

    # 4. Columns
    for c in active_columns:
        w_m = float(c.get("width_m", c.get("bc", 30.0) / 100.0))
        h_m = float(c.get("height_m", c.get("tc", 50.0) / 100.0))
        cx = float(c["x"])
        cy = float(c["y"])
        col_r = patches.Rectangle(
            (cx - w_m / 2.0, cy - h_m / 2.0), w_m, h_m,
            facecolor="#1e293b", edgecolor="#0f172a", lw=1.5, zorder=5
        )
        ax.add_patch(col_r)
        c_lbl = str(c.get("orig_id", c.get("id", "C")))
        ax.text(
            cx, cy, c_lbl,
            ha="center", va="center", color="#ffffff", fontweight="bold", fontsize=8.2, zorder=7
        )

    ax.set_xlim(x_min_eff, x_max_eff)
    ax.set_ylim(y_min_eff, y_max_eff)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(title, fontsize=13.5, fontweight="bold", color="#0f172a", pad=20)

    # ── 5. Dedicated Legend Subplot (Below Framing Plan — Algorithmic Font Sizing & Proportions) ──
    ax_leg.axis("off")
    ax_leg.set_facecolor("#ffffff")
    ax_leg.set_xlim(0, 1)
    ax_leg.set_ylim(0, 1)

    # Outer decorative card border
    card_patch = patches.FancyBboxPatch(
        (0.01, 0.02), 0.98, 0.96,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        facecolor="#ffffff", edgecolor="#cbd5e1", lw=1.5, zorder=1
    )
    ax_leg.add_patch(card_patch)

    # Algorithmic vertical slot & font size calculations based on row density and text length
    h_row = 0.70 / n_leg
    fs_base = max(7.8, min(10.8, 6.8 + 12.0 * h_row))
    max_len = max(len(r.get("rft", "") + r.get("sec", "")) for r in leg_rows) if leg_rows else 60
    scale_w = min(1.0, 80.0 / max(1, max_len))
    fs_rft = max(7.2, min(fs_base, fs_base * scale_w))
    fs_badge = fs_base
    fs_title = min(11.5, fs_base + 1.5)
    fs_cnt = max(7.4, fs_base - 0.4)

    # Title header (English only)
    ax_leg.text(
        0.025, 0.88, "GROUND BEAMS & TIE BEAMS SCHEDULE LEGEND (ECP 203)",
        fontsize=fs_title, fontweight="bold", color="#1e3a8a", va="center", ha="left", zorder=3
    )
    ax_leg.plot([0.025, 0.975], [0.77, 0.77], color="#e2e8f0", lw=1.2, zorder=2)

    if not leg_rows:
        ax_leg.text(
            0.5, 0.40, "No ground beams or tie links identified yet.",
            fontsize=fs_base, fontweight="bold", color="#64748b", ha="center", va="center"
        )
    else:
        y_slots = [0.75 - (i + 0.5) * h_row for i in range(n_leg)]
        for r_item, y_s in zip(leg_rows, y_slots):
            # Model badge
            ax_leg.text(
                0.025, y_s, f"■ {r_item['mark']} ({r_item['label']}):",
                fontsize=fs_badge, fontweight="bold", color=r_item["color"], va="center", ha="left", zorder=3
            )
            # Cross-section
            ax_leg.text(
                0.20, y_s, f"Sec: {r_item['sec']}",
                fontsize=fs_rft, fontweight="bold", color="#1e293b", va="center", ha="left", zorder=3
            )
            # Rebar details
            ax_leg.text(
                0.35, y_s, r_item["rft"],
                fontsize=fs_rft, fontweight="normal", color="#334155", va="center", ha="left", zorder=3
            )
            # Count & Length
            ax_leg.text(
                0.975, y_s, r_item["cnt"],
                fontsize=fs_cnt, fontweight="bold", color="#475569", va="center", ha="right", zorder=3
            )

    try:
        fig.subplots_adjust(top=0.97, bottom=0.03, left=0.035, right=0.965)
    except Exception:
        pass

    return fig

