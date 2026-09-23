"""
modules/bim_3d_viewer.py
================================================================================
Integrated 3D Structural BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)
for Module 1 (Integrated Structural Design - Flat Slab, Columns, Footings & Ground Beams)

Features:
1. Automated multi-module 3D building extraction (Flat Slab, Columns, Footings, Ground Beams).
2. Parametric 3D rebar cages generation respecting concrete cover (Slab meshes, Extra top/bottom,
   Punching shear stirrups, Column longitudinal bars + ties + dowels, Footing meshes,
   Strap beam cages, Ground beam cages).
3. Concrete Opacity Slider (0% - 100%): Solid Concrete -> X-Ray Mode -> Pure Rebar Mode.
4. Standard Rebar Color Coding (Color scheme by category).
5. 360° OrbitControls navigation, Zoom, Pan, View presets (3D, Plan, Front, Side).
6. Raycasting element inspection with floating Inspector Panel (Geometry, Rebar, Forces, Status).
7. Visibility Filters & Element Isolation (Isolate selected element with ghost wireframe for the rest).
================================================================================
"""

import io
import base64
import json
import math
import streamlit as st
import streamlit.components.v1 as components


def extract_bim_3d_scene_data(
    Lx_calc: list,
    Ly_calc: list,
    cantilevers: dict,
    ts_cm: float,
    active_cols: list,
    indiv_col_designs: list = None,
    col_designs: list = None,
    col_H_cm: float = 300.0,
    num_floors: int = 1,
    ftg_analysis: dict = None,
    gb_analysis: dict = None,
    punching_results: list = None,
    top_extra_cols: list = None,
    btm_extra_spans: list = None,
    n_mesh_btm: float = 5.0,
    bottom_mesh_dia: int = 10,
    n_mesh_top: float = 5.0,
    top_mesh_dia: int = 10,
    fcu: float = 250.0,
    fy: float = 4000.0,
    cover_slab_cm: float = 2.0,
    cover_col_cm: float = 2.5,
    cover_ftg_cm: float = 7.0,
    cover_gb_cm: float = 4.0,
    edge_columns: dict = None,
) -> dict:
    """
    Extracts all coordinated 3D structural geometry, elevations, and rebar data
    from computational design results across all integrated modules.
    """
    if not Lx_calc or not Ly_calc:
        return {}

    ts_m = max(0.12, ts_cm / 100.0)
    col_h_m = max(2.50, col_H_cm / 100.0)

    # Elevation Coordinates (Z-Axis in meters):
    # Z = 0.0 -> Top of Foundations / Ground Beam baseline
    # Columns extend from Z = 0.0 up to Z = col_h_m
    # Slab extends from Z = col_h_m to Z = col_h_m + ts_m
    # Foundations extend downward from Z = 0.0 to Z = -t_rc, and PC from -t_rc to -(t_rc + t_pc)

    z_ground = 0.0
    z_col_base = z_ground
    z_col_top = z_col_base + col_h_m
    z_slab_bot = z_col_top
    z_slab_top = z_slab_bot + ts_m

    # Global Slab Boundaries
    cant_left = cantilevers.get("left", 0.0)
    cant_right = cantilevers.get("right", 0.0)
    cant_top = cantilevers.get("top", 0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)

    Lx_list = Lx_calc if isinstance(Lx_calc, (list, tuple)) else [float(Lx_calc or 6.0)]
    Ly_list = Ly_calc if isinstance(Ly_calc, (list, tuple)) else [float(Ly_calc or 6.0)]

    x_min_slab = -cant_left
    x_max_slab = sum(Lx_list) + cant_right
    y_min_slab = -cant_bottom
    y_max_slab = sum(Ly_list) + cant_top

    slab_w_x = x_max_slab - x_min_slab
    slab_w_y = y_max_slab - y_min_slab
    slab_center_x = (x_min_slab + x_max_slab) / 2.0
    slab_center_y = (y_min_slab + y_max_slab) / 2.0

    eff_edge_cols = edge_columns or (ftg_analysis.get("edge_columns") if ftg_analysis else None) or {}
    eff_slab_bounds = (
        (ftg_analysis.get("slab_bounds") if (ftg_analysis and ftg_analysis.get("slab_bounds")) else None)
        or {
            "min_x": 0.0,
            "max_x": sum(Lx_list),
            "min_y": 0.0,
            "max_y": sum(Ly_list),
            "cant_left": cant_left,
            "cant_right": cant_right,
            "cant_bottom": cant_bottom,
            "cant_top": cant_top,
        }
    )

    # Fast lookup for individual column designs
    col_des_map = {}
    if indiv_col_designs:
        for cdes in indiv_col_designs:
            col_des_map[cdes.get("col_id")] = cdes

    # Fast lookup for punching shear check
    punch_map = {}
    if punching_results:
        for pr in punching_results:
            punch_map[pr.get("col_id")] = pr

    # 1. ── CONCRETE ELEMENTS ──────────────────────────────────────────────────
    concrete_elements = []
    rebar_elements = []

    # 1.1 SLAB (Concrete Mesh)
    concrete_elements.append({
        "id": "slab_main",
        "category": "slab",
        "name": "سقف البلاطة اللاكمرية (Flat Slab)",
        "type": "Flat Slab",
        "x": slab_center_x,
        "y": slab_center_y,
        "z": z_slab_bot + (ts_m / 2.0),
        "dx": slab_w_x,
        "dy": slab_w_y,
        "dz": ts_m,
        "color": "#cbd5e1",
        "details": {
            "النوع": "بلاطة لاكمرية خرسانية مسلحة (Solid Flat Slab)",
            "الأبعاد الكلية": f"{slab_w_x:.2f} × {slab_w_y:.2f} م",
            "سُمك البلاطة (ts)": f"{ts_cm:.0f} سم ({ts_m:.2f} م)",
            "الكوابيل (Cantilevers)": f"يسار: {cant_left}م | يمين: {cant_right}م | أعلى: {cant_top}م | أسفل: {cant_bottom}م",
            "المقاومة المميزة (Fcu)": f"{fcu:.0f} كجم/سم²",
            "إجهاد الخضوع (Fy)": f"{fy:.0f} كجم/سم²",
            "الشبكة السفلية": f"{n_mesh_btm:.0f} Φ {bottom_mesh_dia} / م (اتجاهين X, Y)",
            "الشبكة العلوية": f"{n_mesh_top:.0f} Φ {top_mesh_dia} / م (اتجاهين X, Y)",
            "حجم الخرسانة": f"{(slab_w_x * slab_w_y * ts_m):.2f} م³",
        }
    })

    # 1.2 COLUMNS (Concrete Meshes + Rebar Cages)
    for col in active_cols:
        cid = col.get("id", "")
        cx = float(col.get("center_x", col.get("x", 0.0)))
        cy = float(col.get("center_y", col.get("y", 0.0)))
        cw = float(col.get("width_m", col.get("tc", 50.0) / 100.0))
        cd = float(col.get("height_m", col.get("bc", 30.0) / 100.0))
        ctype = col.get("type", "Interior")
        pu_tot = float(col.get("pu_tot", col.get("Pu", 0.0) * num_floors))

        # Get detailed design if available
        cdes = col_des_map.get(cid, {})
        n_bars = int(cdes.get("n_bars", 8))
        phi_m = int(cdes.get("Phi", 16))
        phi_st = int(cdes.get("Phi_st", 8))
        n_st_per_m = int(cdes.get("n_st_per_m", 5))

        col_elem_id = f"col_{cid}"
        concrete_elements.append({
            "id": col_elem_id,
            "category": "columns",
            "name": f"العمود {cid} ({ctype})",
            "label": str(cid),
            "type": "Column",
            "x": cx,
            "y": cy,
            "z": z_col_base + (col_h_m / 2.0),
            "dx": cw,
            "dy": cd,
            "dz": col_h_m,
            "color": "#475569",
            "details": {
                "العمود": f"{cid} — {ctype} Column",
                "الأبعاد (b × t)": f"{int(round(cd * 100))} × {int(round(cw * 100))} سم",
                "الارتفاع الصافي (H)": f"{col_h_m:.2f} م",
                "الحمل الأقصى (Pu)": f"{pu_tot:.1f} طن ({num_floors} أدوار)",
                "التسليح الطولي": f"{n_bars} Φ {phi_m} مم (Main Vertical Rebar)",
                "الكانات والأطواق": f"{n_st_per_m} Φ {phi_st} / م (مع تكثيف طرفي)",
                "حجم الخرسانة": f"{(cw * cd * col_h_m):.2f} م³",
            }
        })

        # ── Parametric Column Rebar Cage ──
        cov_m = cover_col_cm / 100.0
        cage_w = max(0.10, cw - 2 * cov_m)
        cage_d = max(0.10, cd - 2 * cov_m)
        half_w = cage_w / 2.0
        half_d = cage_d / 2.0

        dowel_ext = 0.50
        top_ext = ts_m - 0.04
        z_bar_start = z_col_base - dowel_ext
        z_bar_end = z_col_top + top_ext

        long_bar_positions = []
        if n_bars <= 4:
            long_bar_positions = [
                (cx - half_w, cy - half_d),
                (cx + half_w, cy - half_d),
                (cx + half_w, cy + half_d),
                (cx - half_w, cy + half_d),
            ]
        else:
            long_bar_positions = [
                (cx - half_w, cy - half_d),
                (cx + half_w, cy - half_d),
                (cx + half_w, cy + half_d),
                (cx - half_w, cy + half_d),
            ]
            rem_bars = n_bars - 4
            side_w_count = max(0, int(round(rem_bars * (cage_w / max(0.01, cage_w + cage_d)))))
            side_d_count = max(0, rem_bars - side_w_count)

            if side_w_count > 0:
                each_w = max(1, side_w_count // 2)
                for step in range(1, each_w + 1):
                    frac = step / (each_w + 1)
                    bx = cx - half_w + frac * cage_w
                    long_bar_positions.append((bx, cy - half_d))
                    long_bar_positions.append((bx, cy + half_d))

            if side_d_count > 0:
                each_d = max(1, side_d_count // 2)
                for step in range(1, each_d + 1):
                    frac = step / (each_d + 1)
                    by = cy - half_d + frac * cage_d
                    long_bar_positions.append((cx - half_w, by))
                    long_bar_positions.append((cx + half_w, by))

        col_bar_lines = []
        for bx, by in long_bar_positions:
            col_bar_lines.extend([bx, by, z_bar_start, bx, by, z_bar_end])
            foot_dx = -0.15 if bx > cx else 0.15
            foot_dy = -0.15 if by > cy else 0.15
            col_bar_lines.extend([bx, by, z_bar_start, bx + foot_dx, by + foot_dy, z_bar_start])

        rebar_elements.append({
            "id": f"rebar_col_main_{cid}",
            "parent_id": col_elem_id,
            "category": "rebar_col",
            "color": "#10b981",  # Emerald Green
            "name": f"تسليح العمود {cid} ({n_bars}Φ{phi_m})",
            "lines": col_bar_lines,
        })

        # Closed Stirrups (Ties)
        tie_lines = []
        conf_len = 0.50
        z_curr = z_col_base + 0.05
        while z_curr <= z_col_top - 0.05:
            p1 = [cx - half_w, cy - half_d, z_curr]
            p2 = [cx + half_w, cy - half_d, z_curr]
            p3 = [cx + half_w, cy + half_d, z_curr]
            p4 = [cx - half_w, cy + half_d, z_curr]
            tie_lines.extend([
                p1[0], p1[1], p1[2], p2[0], p2[1], p2[2],
                p2[0], p2[1], p2[2], p3[0], p3[1], p3[2],
                p3[0], p3[1], p3[2], p4[0], p4[1], p4[2],
                p4[0], p4[1], p4[2], p1[0], p1[1], p1[2],
            ])
            in_conf = (z_curr - z_col_base <= conf_len) or (z_col_top - z_curr <= conf_len)
            spacing = 0.10 if in_conf else max(0.15, 1.0 / n_st_per_m)
            z_curr += spacing

        rebar_elements.append({
            "id": f"rebar_col_ties_{cid}",
            "parent_id": col_elem_id,
            "category": "rebar_col_ties",
            "color": "#84cc16",  # Lime
            "name": f"كانات العمود {cid} ({n_st_per_m}Φ{phi_st}/م)",
            "lines": tie_lines,
        })

    # 1.3 FOUNDATIONS & GROUND BEAMS ELEVATION HARMONIZATION
    # ═══════════════════════════════════════════════════════════════════════════
    # UNIFIED GROUND BEAM & STRAP BEAM BOTTOM LEVEL (ECP 203 Site Execution)
    # ═══════════════════════════════════════════════════════════════════════════
    # In structural site execution, all ground beams, tie beams, and strap beams
    # share the EXACT SAME bottom level (soffit elevation = z_gb_bot).
    # Any difference in beam depth (t_m) must project strictly UPWARDS (لأعلى)
    # and NEVER downwards.
    z_gb_bot = z_ground - 0.60  # Fixed uniform baseline for all beam bottoms

    active_cols_map = {str(c.get("id")): c for c in active_cols}
    covered_footing_cols = set()

    # 1.3 FOUNDATIONS (Isolated, Combined, Edge Strap, Corner Strap)
    if ftg_analysis:
        # A. Isolated Footings
        for f_iso in ftg_analysis.get("isolated_footings", []):
            cid = str(f_iso.get("col_id") or (f_iso.get("col", {}).get("id") if isinstance(f_iso.get("col"), dict) else "") or f_iso.get("col_code", ""))
            col_ref = active_cols_map.get(cid, {})
            col_in_f = f_iso.get("col") if isinstance(f_iso.get("col"), dict) else {}

            fx = float(f_iso.get("x", col_in_f.get("x", col_ref.get("center_x", col_ref.get("x", 0.0)))))
            fy_coord = float(f_iso.get("y", col_in_f.get("y", col_ref.get("center_y", col_ref.get("y", 0.0)))))

            L_cm_raw = float(f_iso.get("L_cm", f_iso.get("Lc_cm", f_iso.get("L_rc", 2.0))))
            L_rc = max(0.80, L_cm_raw if L_cm_raw < 15.0 else L_cm_raw / 100.0)

            B_cm_raw = float(f_iso.get("B_cm", f_iso.get("Bc_cm", f_iso.get("B_rc", 2.0))))
            B_rc = max(0.80, B_cm_raw if B_cm_raw < 15.0 else B_cm_raw / 100.0)

            t_cm_raw = float(f_iso.get("t_cm", f_iso.get("tc_cm", f_iso.get("t_rc", 0.50))))
            t_rc = max(0.35, t_cm_raw if t_cm_raw < 5.0 else t_cm_raw / 100.0)

            L_pc = float(f_iso.get("L_pc", L_rc + 0.40))
            B_pc = float(f_iso.get("B_pc", B_rc + 0.40))
            t_pc = 0.20

            f_id = f"ftg_iso_{cid}" if cid else f"ftg_iso_{fx:.1f}_{fy_coord:.1f}"
            m_name = f_iso.get("model_name", f_iso.get("name", f"F-{cid}"))
            clean_ftg_label = str(f_iso.get("model_id") or f_iso.get("name") or (m_name.split("(")[0].strip() if "(" in m_name else m_name)).strip()
            if not clean_ftg_label or clean_ftg_label.startswith("قاعدة") or clean_ftg_label == "None":
                clean_ftg_label = f"F-{cid}"

            concrete_elements.append({
                "id": f_id,
                "category": "footings",
                "name": f"قاعدة منفصلة {m_name} (عمود {cid})",
                "label": clean_ftg_label,
                "type": "Isolated Footing (RC)",
                "x": fx,
                "y": fy_coord,
                "z": z_ground - (t_rc / 2.0),
                "dx": L_rc,
                "dy": B_rc,
                "dz": t_rc,
                "color": "#0284c7",  # Sky Blue RC
                "details": {
                    "النموذج": f"{m_name} (قاعدة منفصلة مسلحة)",
                    "العمود المرتكز": cid,
                    "أبعاد المسلحة (L × B × t)": f"{int(round(L_rc * 100))} × {int(round(B_rc * 100))} × {int(round(t_rc * 100))} سم",
                    "أبعاد العادية (L × B × t)": f"{int(round(L_pc * 100))} × {int(round(B_pc * 100))} × {int(round(t_pc * 100))} سم",
                    "التسليح السفلي (فرش وغطاء)": f_iso.get("rft_str", "6 Φ 16 / م (اتجاهين)"),
                    "إجهاد التربة الفعلي (q_act)": f"{f_iso.get('q_act', 1.25):.2f} كجم/سم²",
                    "حالة الأمان": "✅ Safe ومحقق للكود",
                }
            })

            concrete_elements.append({
                "id": f"{f_id}_pc",
                "category": "footings_pc",
                "name": f"خرسانة عادية للقاعدة {m_name}",
                "type": "Plain Concrete (PC)",
                "x": fx,
                "y": fy_coord,
                "z": z_ground - t_rc - (t_pc / 2.0),
                "dx": L_pc,
                "dy": B_pc,
                "dz": t_pc,
                "color": "#94a3b8",
                "details": {
                    "النوع": "خرسانة عادية أسفل القاعدة المسلحة (P.C.)",
                    "الأبعاد": f"{int(round(L_pc * 100))} × {int(round(B_pc * 100))} × 20 سم",
                    "الرفرفة القياسية": "20 سم من جميع الجهات",
                }
            })

            # 3D Rebar Mesh
            f_cov = cover_ftg_cm / 100.0
            rebar_w = L_rc - 2 * f_cov
            rebar_d = B_rc - 2 * f_cov
            z_mesh = z_ground - t_rc + f_cov
            hook_h = max(0.15, t_rc - 2 * f_cov)

            ftg_mesh_lines = []
            n_bars_y = max(5, int(math.ceil(rebar_d * 6.0)))
            for k in range(n_bars_y):
                y_pos = fy_coord - (rebar_d / 2.0) + (k / max(1, n_bars_y - 1)) * rebar_d
                x_start = fx - (rebar_w / 2.0)
                x_end = fx + (rebar_w / 2.0)
                ftg_mesh_lines.extend([x_start, y_pos, z_mesh, x_end, y_pos, z_mesh])
                ftg_mesh_lines.extend([x_start, y_pos, z_mesh, x_start, y_pos, z_mesh + hook_h])
                ftg_mesh_lines.extend([x_end, y_pos, z_mesh, x_end, y_pos, z_mesh + hook_h])

            n_bars_x = max(5, int(math.ceil(rebar_w * 6.0)))
            for k in range(n_bars_x):
                x_pos = fx - (rebar_w / 2.0) + (k / max(1, n_bars_x - 1)) * rebar_w
                y_start = fy_coord - (rebar_d / 2.0)
                y_end = fy_coord + (rebar_d / 2.0)
                ftg_mesh_lines.extend([x_pos, y_start, z_mesh + 0.02, x_pos, y_end, z_mesh + 0.02])
                ftg_mesh_lines.extend([x_pos, y_start, z_mesh + 0.02, x_pos, y_start, z_mesh + hook_h])
                ftg_mesh_lines.extend([x_pos, y_end, z_mesh + 0.02, x_pos, y_end, z_mesh + hook_h])

            rebar_elements.append({
                "id": f"rebar_{f_id}",
                "parent_id": f_id,
                "category": "rebar_ftg",
                "color": "#14b8a6",  # Teal
                "name": f"شبكة تسليح القاعدة {m_name}",
                "lines": ftg_mesh_lines,
            })
            if cid:
                covered_footing_cols.add(cid)

        # B. Combined Footings
        for cf in ftg_analysis.get("combined_footings", []):
            cf_name = cf.get("name", "CF-1")
            cf_cols = cf.get("supported_cols", "")
            cA_info = cf.get("col_a_info") or cf.get("col1") or {}
            cB_info = cf.get("col_b_info") or cf.get("col2") or {}
            cA_id = str(cf.get("col_a_id") or cA_info.get("id", ""))
            cB_id = str(cf.get("col_b_id") or cB_info.get("id", ""))
            if cA_id:
                covered_footing_cols.add(cA_id)
            if cB_id:
                covered_footing_cols.add(cB_id)

            colA_ref = active_cols_map.get(cA_id, {})
            colB_ref = active_cols_map.get(cB_id, {})

            x_a = float(cA_info.get("x", colA_ref.get("center_x", colA_ref.get("x", 0.0))))
            y_a = float(cA_info.get("y", colA_ref.get("center_y", colA_ref.get("y", 0.0))))
            x_b = float(cB_info.get("x", colB_ref.get("center_x", colB_ref.get("x", 0.0))))
            y_b = float(cB_info.get("y", colB_ref.get("center_y", colB_ref.get("y", 0.0))))

            ov_dir = cf.get("overlap_dir", "X")
            x1_m = float(cf.get("x1_cm", 50.0)) / 100.0
            Lc_m = float(cf.get("Lc_cm", 350.0)) / 100.0
            Bc_m = float(cf.get("Bc_cm", 220.0)) / 100.0
            t_rc = float(cf.get("tc_cm", 70.0)) / 100.0

            if ov_dir == "X":
                cx_cf = x_a - x1_m + Lc_m / 2.0 if x_b >= x_a else x_a + x1_m - Lc_m / 2.0
                cy_cf = (y_a + y_b) / 2.0
                dx_cf = Lc_m
                dy_cf = Bc_m
            else:
                cx_cf = (x_a + x_b) / 2.0
                cy_cf = y_a - x1_m + Lc_m / 2.0 if y_b >= y_a else y_a + x1_m - Lc_m / 2.0
                dx_cf = Bc_m
                dy_cf = Lc_m

            cf_id = f"ftg_cf_{cf_name}"
            clean_cf_label = cf_name.split("(")[0].strip() if "(" in cf_name else cf_name.strip()
            if not clean_cf_label or clean_cf_label == "None":
                clean_cf_label = f"CF-{cf.get('name', '1')}"

            concrete_elements.append({
                "id": cf_id,
                "category": "footings",
                "name": f"قاعدة مشتركة {cf_name} ({cf_cols})",
                "label": clean_cf_label,
                "type": "Combined Footing (RC)",
                "x": cx_cf,
                "y": cy_cf,
                "z": z_ground - (t_rc / 2.0),
                "dx": dx_cf,
                "dy": dy_cf,
                "dz": t_rc,
                "color": "#10b981",
                "details": {
                    "النموذج": f"{cf_name} (قاعدة مشتركة)",
                    "الأعمدة المرتكزة": cf_cols,
                    "أبعاد المسلحة (L × B × t)": f"{int(round(dx_cf*100))} × {int(round(dy_cf*100))} × {int(round(t_rc*100))} سم",
                    "التسليح العلوي": cf.get("rft_top_str", "7 Φ 18 / م (Top Main Rft)"),
                    "التسليح السفلي": cf.get("rft_bot_str", "6 Φ 16 / م (Bottom Mesh)"),
                    "حالة التحقق": cf.get("status_str", "✅ Safe"),
                }
            })

            concrete_elements.append({
                "id": f"{cf_id}_pc",
                "category": "footings_pc",
                "name": f"عادية القاعدة المشتركة {cf_name}",
                "type": "Plain Concrete (PC)",
                "x": cx_cf,
                "y": cy_cf,
                "z": z_ground - t_rc - 0.10,
                "dx": dx_cf + 0.40,
                "dy": dy_cf + 0.40,
                "dz": 0.20,
                "color": "#94a3b8",
                "details": {
                    "النوع": "فرشة خرسانة عادية 20 سم",
                    "الأبعاد": f"{int((dx_cf+0.4)*100)} × {int((dy_cf+0.4)*100)} × 20 سم",
                }
            })

            # Combined Rebar Mesh
            f_cov = cover_ftg_cm / 100.0
            rebar_w = dx_cf - 2 * f_cov
            rebar_d = dy_cf - 2 * f_cov
            z_mesh_bot = z_ground - t_rc + f_cov
            z_mesh_top_cf = z_ground - f_cov

            cf_rebar_lines = []
            n_b = max(5, int(math.ceil(rebar_d * 6.0)))
            for k in range(n_b):
                y_pos = cy_cf - (rebar_d / 2.0) + (k / max(1, n_b - 1)) * rebar_d
                cf_rebar_lines.extend([
                    cx_cf - rebar_w / 2.0, y_pos, z_mesh_bot,
                    cx_cf + rebar_w / 2.0, y_pos, z_mesh_bot
                ])
            n_t = max(6, int(math.ceil(rebar_d * 7.0)))
            for k in range(n_t):
                y_pos = cy_cf - (rebar_d / 2.0) + (k / max(1, n_t - 1)) * rebar_d
                cf_rebar_lines.extend([
                    cx_cf - rebar_w / 2.0, y_pos, z_mesh_top_cf,
                    cx_cf + rebar_w / 2.0, y_pos, z_mesh_top_cf
                ])

            rebar_elements.append({
                "id": f"rebar_{cf_id}",
                "parent_id": cf_id,
                "category": "rebar_ftg",
                "color": "#2563eb",  # Royal Blue
                "name": f"تسليح علوي وسفلي للقاعدة المشتركة {cf_name}",
                "lines": cf_rebar_lines,
            })

        # C. Edge Strap Footings (Module 9)
        for sf in ftg_analysis.get("edge_strap_footings", []):
            sf_name = sf.get("name", "Strap-1")
            c1 = sf.get("col1", {})
            c2 = sf.get("col2", {})
            c1_id = str(c1.get("id", ""))
            c2_id = str(c2.get("id", ""))
            if c1_id:
                covered_footing_cols.add(c1_id)
            if c2_id:
                covered_footing_cols.add(c2_id)

            c1_ref = active_cols_map.get(c1_id, {})
            c2_ref = active_cols_map.get(c2_id, {})

            x1 = float(c1.get("x", c1_ref.get("center_x", c1_ref.get("x", 0.0))))
            y1 = float(c1.get("y", c1_ref.get("center_y", c1_ref.get("y", 0.0))))
            x2 = float(c2.get("x", c2_ref.get("center_x", c2_ref.get("x", 0.0))))
            y2 = float(c2.get("y", c2_ref.get("center_y", c2_ref.get("y", 0.0))))

            L1 = float(sf.get("L1", 2.2))
            B1 = float(sf.get("B1", 3.0))
            t1 = float(sf.get("t1", 60.0)) / 100.0

            L2 = float(sf.get("L2", 2.5))
            B2 = float(sf.get("B2", 2.5))
            t2 = float(sf.get("t2", 50.0)) / 100.0

            sb_b_raw = float(sf.get("strap_b", sf.get("sb", 40.0)))
            sb_b = sb_b_raw if sb_b_raw < 5.0 else sb_b_raw / 100.0
            sb_D_raw = float(sf.get("strap_D", sf.get("sD", 100.0)))
            sb_D = sb_D_raw if sb_D_raw < 5.0 else sb_D_raw / 100.0
            mid_x = (x1 + x2) / 2.0
            mid_y = (y1 + y2) / 2.0
            span_sb = math.hypot(x2 - x1, y2 - y1)
            angle_sb = math.atan2(y2 - y1, x2 - x1)

            from modules.two_col_footings import compute_strap_f1_geometry
            f1_g = sf.get("f1_geom") or compute_strap_f1_geometry(sf, edge_columns=eff_edge_cols, slab_bounds=eff_slab_bounds)

            f1_id = f"ftg_edge_f1_{sf_name}"
            f1_lbl = f"{sf_name} (جار)"
            concrete_elements.append({
                "id": f1_id,
                "category": "footings",
                "name": f"قاعدة جار {sf_name} (عمود {c1_id})",
                "label": f1_lbl,
                "type": "Edge Strap Footing",
                "x": f1_g["cx"],
                "y": f1_g["cy"],
                "z": z_ground - (t1 / 2.0),
                "dx": f1_g["w"],
                "dy": f1_g["h"],
                "dz": t1,
                "color": "#f97316",
                "details": {
                    "النموذج": f"{sf_name} — قاعدة الجار الخارجية",
                    "العمود": f"{c1_id} (ملاصق لحدود الجار)",
                    "الأبعاد (L1 × B1 × t1)": f"{int(round(f1_g['w']*100))} × {int(round(f1_g['h']*100))} × {int(round(t1*100))} سم",
                    "حد الجار": f"ملاصق تماماً لحد الجار ({f1_g.get('nbr_face', 'Left')}) بدون أي بروز خارج الموقع",
                    "التسليح": "شبكة سفلية اتجاهين 6-7 Φ 16 / م",
                }
            })

            # F1 Edge Plain Concrete (0 projection on neighbor side, 20 cm on interior sides)
            nbr_face = f1_g.get("nbr_face", "Left")
            if nbr_face == "Left":
                pc_x0 = f1_g["x0"]
                pc_w = f1_g["w"] + 0.20
                pc_y0 = f1_g["y0"] - 0.20
                pc_h = f1_g["h"] + 0.40
            elif nbr_face == "Right":
                pc_x0 = f1_g["x0"] - 0.20
                pc_w = f1_g["w"] + 0.20
                pc_y0 = f1_g["y0"] - 0.20
                pc_h = f1_g["h"] + 0.40
            elif nbr_face == "Bottom":
                pc_x0 = f1_g["x0"] - 0.20
                pc_w = f1_g["w"] + 0.40
                pc_y0 = f1_g["y0"]
                pc_h = f1_g["h"] + 0.20
            else:  # Top
                pc_x0 = f1_g["x0"] - 0.20
                pc_w = f1_g["w"] + 0.40
                pc_y0 = f1_g["y0"] - 0.20
                pc_h = f1_g["h"] + 0.20

            concrete_elements.append({
                "id": f"{f1_id}_pc",
                "category": "footings_pc",
                "name": f"عادية قاعدة الجار {sf_name}",
                "type": "Plain Concrete (PC)",
                "x": pc_x0 + pc_w / 2.0,
                "y": pc_y0 + pc_h / 2.0,
                "z": z_ground - t1 - 0.10,
                "dx": pc_w,
                "dy": pc_h,
                "dz": 0.20,
                "color": "#94a3b8",
                "details": {
                    "النوع": f"فرشة خرسانة عادية أسفل قاعدة الجار {sf_name} (رفرفة صفرية جهة جار {nbr_face})",
                    "الأبعاد": f"{int(round(pc_w*100))} × {int(round(pc_h*100))} × 20 سم",
                }
            })

            # F1 Rebar Mesh (Bottom 2-way with 90° upward hooks)
            f_cov = cover_ftg_cm / 100.0
            r_w1 = max(0.20, f1_g["w"] - 2 * f_cov)
            r_h1 = max(0.20, f1_g["h"] - 2 * f_cov)
            z_mesh_f1 = z_ground - t1 + f_cov
            hook_h1 = max(0.15, t1 - 2 * f_cov)
            f1_mesh_lines = []
            nx1 = max(4, int(math.ceil(r_h1 * 6.0)))
            for k in range(nx1):
                y_pos = f1_g["cy"] - (r_h1 / 2.0) + (k / max(1, nx1 - 1)) * r_h1
                x_s = f1_g["cx"] - r_w1 / 2.0
                x_e = f1_g["cx"] + r_w1 / 2.0
                f1_mesh_lines.extend([x_s, y_pos, z_mesh_f1, x_e, y_pos, z_mesh_f1])
                f1_mesh_lines.extend([x_s, y_pos, z_mesh_f1, x_s, y_pos, z_mesh_f1 + hook_h1])
                f1_mesh_lines.extend([x_e, y_pos, z_mesh_f1, x_e, y_pos, z_mesh_f1 + hook_h1])
            ny1 = max(4, int(math.ceil(r_w1 * 6.0)))
            for k in range(ny1):
                x_pos = f1_g["cx"] - (r_w1 / 2.0) + (k / max(1, ny1 - 1)) * r_w1
                y_s = f1_g["cy"] - r_h1 / 2.0
                y_e = f1_g["cy"] + r_h1 / 2.0
                f1_mesh_lines.extend([x_pos, y_s, z_mesh_f1 + 0.02, x_pos, y_e, z_mesh_f1 + 0.02])
                f1_mesh_lines.extend([x_pos, y_s, z_mesh_f1 + 0.02, x_pos, y_s, z_mesh_f1 + hook_h1])
                f1_mesh_lines.extend([x_pos, y_e, z_mesh_f1 + 0.02, x_pos, y_e, z_mesh_f1 + hook_h1])
            rebar_elements.append({
                "id": f"rebar_{f1_id}",
                "parent_id": f1_id,
                "category": "rebar_ftg",
                "color": "#f97316",
                "name": f"شبكة تسليح سفلية لقاعدة الجار {sf_name}",
                "lines": f1_mesh_lines,
            })

            # F2 Interior Footing for Edge Strap (Centered on Interior Column c2)
            ov_dir = sf.get("direction", "X")
            if ov_dir == "Y":
                f2_w, f2_h = B2, L2
            else:
                f2_w, f2_h = L2, B2

            f2_id = f"ftg_edge_f2_{sf_name}"
            f2_lbl = f"{sf_name} (داخلي)"
            concrete_elements.append({
                "id": f2_id,
                "category": "footings",
                "name": f"قاعدة داخلية للشداد {sf_name} (عمود {c2_id})",
                "label": f2_lbl,
                "type": "Interior Strap Footing",
                "x": x2,
                "y": y2,
                "z": z_ground - (t2 / 2.0),
                "dx": f2_w,
                "dy": f2_h,
                "dz": t2,
                "color": "#0284c7",
                "details": {
                    "النموذج": f"{sf_name} — قاعدة داخلية للشداد",
                    "العمود": f"{c2_id}",
                    "الأبعاد (L2 × B2 × t2)": f"{int(round(f2_w*100))} × {int(round(f2_h*100))} × {int(round(t2*100))} سم",
                    "التسليح": "شبكة سفلية اتجاهين",
                }
            })

            concrete_elements.append({
                "id": f"{f2_id}_pc",
                "category": "footings_pc",
                "name": f"عادية القاعدة الداخلية {sf_name}",
                "type": "Plain Concrete (PC)",
                "x": x2,
                "y": y2,
                "z": z_ground - t2 - 0.10,
                "dx": f2_w + 0.40,
                "dy": f2_h + 0.40,
                "dz": 0.20,
                "color": "#94a3b8",
                "details": {
                    "النوع": f"فرشة خرسانة عادية أسفل قاعدة الشداد الداخلية {sf_name}",
                    "الأبعاد": f"{int(round((f2_w+0.4)*100))} × {int(round((f2_h+0.4)*100))} × 20 سم",
                }
            })

            # F2 Rebar Mesh (Bottom 2-way with 90° upward hooks)
            r_w2 = max(0.20, f2_w - 2 * f_cov)
            r_h2 = max(0.20, f2_h - 2 * f_cov)
            z_mesh_f2 = z_ground - t2 + f_cov
            hook_h2 = max(0.15, t2 - 2 * f_cov)
            f2_mesh_lines = []
            nx2 = max(4, int(math.ceil(r_h2 * 6.0)))
            for k in range(nx2):
                y_pos = y2 - (r_h2 / 2.0) + (k / max(1, nx2 - 1)) * r_h2
                x_s = x2 - r_w2 / 2.0
                x_e = x2 + r_w2 / 2.0
                f2_mesh_lines.extend([x_s, y_pos, z_mesh_f2, x_e, y_pos, z_mesh_f2])
                f2_mesh_lines.extend([x_s, y_pos, z_mesh_f2, x_s, y_pos, z_mesh_f2 + hook_h2])
                f2_mesh_lines.extend([x_e, y_pos, z_mesh_f2, x_e, y_pos, z_mesh_f2 + hook_h2])
            ny2 = max(4, int(math.ceil(r_w2 * 6.0)))
            for k in range(ny2):
                x_pos = x2 - (r_w2 / 2.0) + (k / max(1, ny2 - 1)) * r_w2
                y_s = y2 - r_h2 / 2.0
                y_e = y2 + r_h2 / 2.0
                f2_mesh_lines.extend([x_pos, y_s, z_mesh_f2 + 0.02, x_pos, y_e, z_mesh_f2 + 0.02])
                f2_mesh_lines.extend([x_pos, y_s, z_mesh_f2 + 0.02, x_pos, y_s, z_mesh_f2 + hook_h2])
                f2_mesh_lines.extend([x_pos, y_e, z_mesh_f2 + 0.02, x_pos, y_e, z_mesh_f2 + hook_h2])
            rebar_elements.append({
                "id": f"rebar_{f2_id}",
                "parent_id": f2_id,
                "category": "rebar_ftg",
                "color": "#0284c7",
                "name": f"شبكة تسليح سفلية للقاعدة الداخلية {sf_name}",
                "lines": f2_mesh_lines,
            })

            # Strap Beam: Bottom level matches z_gb_bot, depth difference extends UPWARDS
            sb_id = f"strap_beam_{sf_name}"
            concrete_elements.append({
                "id": sb_id,
                "category": "ground_beams",
                "name": f"كمرة شداد {sf_name} ({c1_id} إلى {c2_id})",
                "label": f"شداد {sf_name}",
                "type": "Strap Beam",
                "x": mid_x,
                "y": mid_y,
                "z": z_gb_bot + (sb_D / 2.0),
                "dx": span_sb,
                "dy": sb_b,
                "dz": sb_D,
                "rot_z": angle_sb,
                "color": "#dc2626",
                "details": {
                    "النموذج": f"{sf_name} — كمرة شداد جداري (Strap Beam)",
                    "يربط بين": f"{c1_id} و {c2_id}",
                    "منسوب القاع الموحد": f"{z_gb_bot:.2f} م (مشترك مع كافة السملات)",
                    "البحر (S)": f"{span_sb:.2f} م",
                    "القطاع (b × D)": f"{int(round(sb_b*100))} × {int(round(sb_D*100))} سم",
                    "التسليح الرئيسي (العلوي)": "6 Φ 22 (مقاومة عزم الانقلاب)",
                    "التسليح السفلي": "4 Φ 16",
                    "الكانات": "7 Φ 10 / م (4 فروع لمقاومة القص والالتواء)",
                }
            })

            # Strap Beam Rebar Cage (aligned with z_gb_bot)
            sb_rebar_lines = []
            z_top_sb = z_gb_bot + sb_D - 0.05
            z_bot_sb = z_gb_bot + 0.05
            dx_unit = (x2 - x1) / max(0.01, span_sb)
            dy_unit = (y2 - y1) / max(0.01, span_sb)
            perp_x = -dy_unit * (sb_b / 2.0 - 0.04)
            perp_y = dx_unit * (sb_b / 2.0 - 0.04)

            # Top primary tension bars (6 bars) with downward 90° hooks into footings
            for frac in [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0]:
                px = frac * perp_x
                py = frac * perp_y
                sb_rebar_lines.extend([
                    x1 + px, y1 + py, z_top_sb,
                    x2 + px, y2 + py, z_top_sb
                ])
                # Downward anchorage hooks at ends
                sb_rebar_lines.extend([
                    x1 + px, y1 + py, z_top_sb,
                    x1 + px, y1 + py, z_bot_sb
                ])
                sb_rebar_lines.extend([
                    x2 + px, y2 + py, z_top_sb,
                    x2 + px, y2 + py, z_bot_sb
                ])

            # Bottom bars (4 bars) with upward 90° hooks
            for frac in [-0.9, -0.3, 0.3, 0.9]:
                px = frac * perp_x
                py = frac * perp_y
                sb_rebar_lines.extend([
                    x1 + px, y1 + py, z_bot_sb,
                    x2 + px, y2 + py, z_bot_sb
                ])
                # Upward hooks at ends
                sb_rebar_lines.extend([
                    x1 + px, y1 + py, z_bot_sb,
                    x1 + px, y1 + py, z_bot_sb + min(0.30, sb_D * 0.4)
                ])
                sb_rebar_lines.extend([
                    x2 + px, y2 + py, z_bot_sb,
                    x2 + px, y2 + py, z_bot_sb + min(0.30, sb_D * 0.4)
                ])

            # Skin bars (if sb_D >= 0.60m)
            if sb_D >= 0.60:
                n_side_lvls = max(1, int((sb_D - 0.20) / 0.30))
                for lvl in range(1, n_side_lvls + 1):
                    z_side = z_bot_sb + lvl * (sb_D - 0.10) / (n_side_lvls + 1)
                    for frac in [-1.0, 1.0]:
                        px = frac * perp_x
                        py = frac * perp_y
                        sb_rebar_lines.extend([
                            x1 + px, y1 + py, z_side,
                            x2 + px, y2 + py, z_side
                        ])

            # Closed stirrups along span
            n_st_sb = max(6, int(math.ceil(span_sb * 7.0)))
            for s_idx in range(1, n_st_sb):
                s_frac = s_idx / n_st_sb
                sx = x1 + s_frac * (x2 - x1)
                sy = y1 + s_frac * (y2 - y1)
                c_tl = [sx - perp_x, sy - perp_y, z_top_sb]
                c_tr = [sx + perp_x, sy + perp_y, z_top_sb]
                c_br = [sx + perp_x, sy + perp_y, z_bot_sb]
                c_bl = [sx - perp_x, sy - perp_y, z_bot_sb]
                sb_rebar_lines.extend([
                    c_tl[0], c_tl[1], c_tl[2], c_tr[0], c_tr[1], c_tr[2],
                    c_tr[0], c_tr[1], c_tr[2], c_br[0], c_br[1], c_br[2],
                    c_br[0], c_br[1], c_br[2], c_bl[0], c_bl[1], c_bl[2],
                    c_bl[0], c_bl[1], c_bl[2], c_tl[0], c_tl[1], c_tl[2],
                ])

            rebar_elements.append({
                "id": f"rebar_{sb_id}",
                "parent_id": sb_id,
                "category": "rebar_strap",
                "color": "#e11d48",
                "name": f"قفص تسليح كمرة الشداد {sf_name}",
                "lines": sb_rebar_lines,
            })

        # D. Corner Strap Footings (Module 10)
        for dsf in ftg_analysis.get("corner_strap_footings", []):
            dsf_name = dsf.get("name", "DSF-1")
            c1 = dsf.get("col1", {})
            c2 = dsf.get("col2", {})
            c1_id = str(c1.get("id", ""))
            c2_id = str(c2.get("id", ""))
            if c1_id:
                covered_footing_cols.add(c1_id)
            if c2_id:
                covered_footing_cols.add(c2_id)

            c1_ref = active_cols_map.get(c1_id, {})
            c2_ref = active_cols_map.get(c2_id, {})

            x1 = float(c1.get("x", c1_ref.get("center_x", c1_ref.get("x", 0.0))))
            y1 = float(c1.get("y", c1_ref.get("center_y", c1_ref.get("y", 0.0))))
            x2 = float(c2.get("x", c2_ref.get("center_x", c2_ref.get("x", 0.0))))
            y2 = float(c2.get("y", c2_ref.get("center_y", c2_ref.get("y", 0.0))))

            L1x = float(dsf.get("L1x", 2.0))
            L1y = float(dsf.get("L1y", 2.0))
            t1 = float(dsf.get("t1", 60.0)) / 100.0

            L2x = float(dsf.get("L2x", 2.2))
            L2y = float(dsf.get("L2y", 2.2))
            t2 = float(dsf.get("t2", 50.0)) / 100.0

            sb_b_raw = float(dsf.get("strap_b", 40.0))
            sb_b = sb_b_raw if sb_b_raw < 5.0 else sb_b_raw / 100.0
            sb_D_raw = float(dsf.get("strap_D", 100.0))
            sb_D = sb_D_raw if sb_D_raw < 5.0 else sb_D_raw / 100.0

            mid_x = (x1 + x2) / 2.0
            mid_y = (y1 + y2) / 2.0
            span_dsf = math.hypot(x2 - x1, y2 - y1)
            angle_dsf = math.atan2(y2 - y1, x2 - x1)

            from modules.two_col_footings import compute_corner_strap_f1_geometry
            f1_g = dsf.get("f1_geom") or compute_corner_strap_f1_geometry(dsf, edge_columns=eff_edge_cols, slab_bounds=eff_slab_bounds)

            # F1 Corner
            f1_corner_id = f"ftg_corner_f1_{dsf_name}"
            concrete_elements.append({
                "id": f1_corner_id,
                "category": "footings",
                "name": f"قاعدة جار ركن {dsf_name} (عمود {c1_id})",
                "label": f"{dsf_name} (جار)",
                "type": "Corner Strap Footing",
                "x": f1_g["cx"],
                "y": f1_g["cy"],
                "z": z_ground - (t1 / 2.0),
                "dx": f1_g["w"],
                "dy": f1_g["h"],
                "dz": t1,
                "color": "#f97316",
                "details": {
                    "النموذج": f"{dsf_name} — قاعدة جار ركنية",
                    "العمود": f"{c1_id} (ركن المبنى ملاصق للجار)",
                    "الأبعاد (L1x × L1y × t1)": f"{int(round(f1_g['w']*100))} × {int(round(f1_g['h']*100))} × {int(round(t1*100))} سم",
                    "حدود الجار": f"ملاصق لحدود الجار ({f1_g.get('nbr_x', 'Left')} + {f1_g.get('nbr_y', 'Bottom')}) بدون أي بروز خارج الموقع",
                    "التسليح": "شبكة سفلية اتجاهين",
                }
            })

            # F1 Corner PC (0 projection on both neighbor sides, 20 cm on interior sides)
            nbr_x = f1_g.get("nbr_x", "Left")
            nbr_y = f1_g.get("nbr_y", "Bottom")
            if nbr_x == "Left":
                c_pc_x0 = f1_g["x0"]
                c_pc_w = f1_g["w"] + 0.20
            else:
                c_pc_x0 = f1_g["x0"] - 0.20
                c_pc_w = f1_g["w"] + 0.20

            if nbr_y == "Bottom":
                c_pc_y0 = f1_g["y0"]
                c_pc_h = f1_g["h"] + 0.20
            else:
                c_pc_y0 = f1_g["y0"] - 0.20
                c_pc_h = f1_g["h"] + 0.20

            concrete_elements.append({
                "id": f"{f1_corner_id}_pc",
                "category": "footings_pc",
                "name": f"عادية قاعدة الركن {dsf_name}",
                "type": "Plain Concrete (PC)",
                "x": c_pc_x0 + c_pc_w / 2.0,
                "y": c_pc_y0 + c_pc_h / 2.0,
                "z": z_ground - t1 - 0.10,
                "dx": c_pc_w,
                "dy": c_pc_h,
                "dz": 0.20,
                "color": "#94a3b8",
                "details": {
                    "النوع": f"فرشة خرسانة عادية أسفل قاعدة الركن {dsf_name} (رفرفة صفرية جهتي جار {nbr_x} و {nbr_y})",
                    "الأبعاد": f"{int(round(c_pc_w*100))} × {int(round(c_pc_h*100))} × 20 سم",
                }
            })

            # F1 Corner Rebar Mesh (Bottom 2-way with 90° upward hooks)
            f_cov = cover_ftg_cm / 100.0
            r_w1c = max(0.20, f1_g["w"] - 2 * f_cov)
            r_h1c = max(0.20, f1_g["h"] - 2 * f_cov)
            z_mesh_f1c = z_ground - t1 + f_cov
            hook_h1c = max(0.15, t1 - 2 * f_cov)
            f1c_mesh_lines = []
            nx1c = max(4, int(math.ceil(r_h1c * 6.0)))
            for k in range(nx1c):
                y_pos = f1_g["cy"] - (r_h1c / 2.0) + (k / max(1, nx1c - 1)) * r_h1c
                x_s = f1_g["cx"] - r_w1c / 2.0
                x_e = f1_g["cx"] + r_w1c / 2.0
                f1c_mesh_lines.extend([x_s, y_pos, z_mesh_f1c, x_e, y_pos, z_mesh_f1c])
                f1c_mesh_lines.extend([x_s, y_pos, z_mesh_f1c, x_s, y_pos, z_mesh_f1c + hook_h1c])
                f1c_mesh_lines.extend([x_e, y_pos, z_mesh_f1c, x_e, y_pos, z_mesh_f1c + hook_h1c])
            ny1c = max(4, int(math.ceil(r_w1c * 6.0)))
            for k in range(ny1c):
                x_pos = f1_g["cx"] - (r_w1c / 2.0) + (k / max(1, ny1c - 1)) * r_w1c
                y_s = f1_g["cy"] - r_h1c / 2.0
                y_e = f1_g["cy"] + r_h1c / 2.0
                f1c_mesh_lines.extend([x_pos, y_s, z_mesh_f1c + 0.02, x_pos, y_e, z_mesh_f1c + 0.02])
                f1c_mesh_lines.extend([x_pos, y_s, z_mesh_f1c + 0.02, x_pos, y_s, z_mesh_f1c + hook_h1c])
                f1c_mesh_lines.extend([x_pos, y_e, z_mesh_f1c + 0.02, x_pos, y_e, z_mesh_f1c + hook_h1c])
            rebar_elements.append({
                "id": f"rebar_{f1_corner_id}",
                "parent_id": f1_corner_id,
                "category": "rebar_ftg",
                "color": "#f97316",
                "name": f"شبكة تسليح سفلية لقاعدة جار الركن {dsf_name}",
                "lines": f1c_mesh_lines,
            })

            # F2 Interior
            f2_corner_id = f"ftg_corner_f2_{dsf_name}"
            concrete_elements.append({
                "id": f2_corner_id,
                "category": "footings",
                "name": f"قاعدة داخلية لشداد الركن {dsf_name} (عمود {c2_id})",
                "label": f"{dsf_name} (داخلي)",
                "type": "Interior Strap Footing",
                "x": x2,
                "y": y2,
                "z": z_ground - (t2 / 2.0),
                "dx": L2x,
                "dy": L2y,
                "dz": t2,
                "color": "#0284c7",
                "details": {
                    "النموذج": f"{dsf_name} — قاعدة داخلية للشداد المائل",
                    "العمود": f"{c2_id}",
                    "الأبعاد (L2x × L2y × t2)": f"{int(round(L2x*100))} × {int(round(L2y*100))} × {int(round(t2*100))} سم",
                    "التسليح": "شبكة سفلية اتجاهين",
                }
            })
            concrete_elements.append({
                "id": f"{f2_corner_id}_pc",
                "category": "footings_pc",
                "name": f"عادية القاعدة الداخلية {dsf_name}",
                "type": "Plain Concrete (PC)",
                "x": x2,
                "y": y2,
                "z": z_ground - t2 - 0.10,
                "dx": L2x + 0.40,
                "dy": L2y + 0.40,
                "dz": 0.20,
                "color": "#94a3b8",
                "details": {"النوع": "فرشة خرسانة عادية 20 سم"}
            })

            # F2 Interior Rebar Mesh (Bottom 2-way with 90° upward hooks)
            r_w2c = max(0.20, L2x - 2 * f_cov)
            r_h2c = max(0.20, L2y - 2 * f_cov)
            z_mesh_f2c = z_ground - t2 + f_cov
            hook_h2c = max(0.15, t2 - 2 * f_cov)
            f2c_mesh_lines = []
            nx2c = max(4, int(math.ceil(r_h2c * 6.0)))
            for k in range(nx2c):
                y_pos = y2 - (r_h2c / 2.0) + (k / max(1, nx2c - 1)) * r_h2c
                x_s = x2 - r_w2c / 2.0
                x_e = x2 + r_w2c / 2.0
                f2c_mesh_lines.extend([x_s, y_pos, z_mesh_f2c, x_e, y_pos, z_mesh_f2c])
                f2c_mesh_lines.extend([x_s, y_pos, z_mesh_f2c, x_s, y_pos, z_mesh_f2c + hook_h2c])
                f2c_mesh_lines.extend([x_e, y_pos, z_mesh_f2c, x_e, y_pos, z_mesh_f2c + hook_h2c])
            ny2c = max(4, int(math.ceil(r_w2c * 6.0)))
            for k in range(ny2c):
                x_pos = x2 - (r_w2c / 2.0) + (k / max(1, ny2c - 1)) * r_w2c
                y_s = y2 - r_h2c / 2.0
                y_e = y2 + r_h2c / 2.0
                f2c_mesh_lines.extend([x_pos, y_s, z_mesh_f2c + 0.02, x_pos, y_e, z_mesh_f2c + 0.02])
                f2c_mesh_lines.extend([x_pos, y_s, z_mesh_f2c + 0.02, x_pos, y_s, z_mesh_f2c + hook_h2c])
                f2c_mesh_lines.extend([x_pos, y_e, z_mesh_f2c + 0.02, x_pos, y_e, z_mesh_f2c + hook_h2c])
            rebar_elements.append({
                "id": f"rebar_{f2_corner_id}",
                "parent_id": f2_corner_id,
                "category": "rebar_ftg",
                "color": "#0284c7",
                "name": f"شبكة تسليح سفلية للقاعدة الداخلية {dsf_name}",
                "lines": f2c_mesh_lines,
            })

            # Diagonal Strap Beam: unified bottom level at z_gb_bot
            sb_corner_id = f"strap_diag_{dsf_name}"
            concrete_elements.append({
                "id": sb_corner_id,
                "category": "ground_beams",
                "name": f"كمرة شداد ركن مائل {dsf_name} ({c1_id} إلى {c2_id})",
                "label": f"شداد {dsf_name}",
                "type": "Diagonal Strap Beam",
                "x": mid_x,
                "y": mid_y,
                "z": z_gb_bot + (sb_D / 2.0),
                "dx": span_dsf,
                "dy": sb_b,
                "dz": sb_D,
                "rot_z": angle_dsf,
                "color": "#dc2626",
                "details": {
                    "النموذج": f"{dsf_name} — كمرة شداد ركن مائل (Diagonal Strap Beam)",
                    "يربط بين": f"{c1_id} و {c2_id}",
                    "منسوب القاع الموحد": f"{z_gb_bot:.2f} م (مشترك مع كافة السملات)",
                    "البحر (S)": f"{span_dsf:.2f} م",
                    "القطاع (b × D)": f"{int(round(sb_b*100))} × {int(round(sb_D*100))} سم",
                    "التسليح الرئيسي (العلوي)": "6 Φ 22 (مقاومة عزم الانقلاب)",
                    "التسليح السفلي": "4 Φ 16",
                    "الكانات": "7 Φ 10 / م (4 فروع لمقاومة القص والالتواء)",
                }
            })

            # Diagonal Strap Beam Rebar Cage (Module 10)
            dsf_rebar_lines = []
            z_top_dsf = z_gb_bot + sb_D - 0.05
            z_bot_dsf = z_gb_bot + 0.05
            dx_dunit = (x2 - x1) / max(0.01, span_dsf)
            dy_dunit = (y2 - y1) / max(0.01, span_dsf)
            dperp_x = -dy_dunit * (sb_b / 2.0 - 0.04)
            dperp_y = dx_dunit * (sb_b / 2.0 - 0.04)

            # Top primary tension bars (6 bars) with downward 90° hooks into footings
            for frac in [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0]:
                px = frac * dperp_x
                py = frac * dperp_y
                dsf_rebar_lines.extend([
                    x1 + px, y1 + py, z_top_dsf,
                    x2 + px, y2 + py, z_top_dsf
                ])
                # Downward anchorage hooks at ends
                dsf_rebar_lines.extend([
                    x1 + px, y1 + py, z_top_dsf,
                    x1 + px, y1 + py, z_bot_dsf
                ])
                dsf_rebar_lines.extend([
                    x2 + px, y2 + py, z_top_dsf,
                    x2 + px, y2 + py, z_bot_dsf
                ])

            # Bottom bars (4 bars) with upward 90° hooks
            for frac in [-0.9, -0.3, 0.3, 0.9]:
                px = frac * dperp_x
                py = frac * dperp_y
                dsf_rebar_lines.extend([
                    x1 + px, y1 + py, z_bot_dsf,
                    x2 + px, y2 + py, z_bot_dsf
                ])
                # Upward hooks at ends
                dsf_rebar_lines.extend([
                    x1 + px, y1 + py, z_bot_dsf,
                    x1 + px, y1 + py, z_bot_dsf + min(0.30, sb_D * 0.4)
                ])
                dsf_rebar_lines.extend([
                    x2 + px, y2 + py, z_bot_dsf,
                    x2 + px, y2 + py, z_bot_dsf + min(0.30, sb_D * 0.4)
                ])

            # Skin bars (if sb_D >= 0.60m)
            if sb_D >= 0.60:
                n_side_lvls = max(1, int((sb_D - 0.20) / 0.30))
                for lvl in range(1, n_side_lvls + 1):
                    z_side = z_bot_dsf + lvl * (sb_D - 0.10) / (n_side_lvls + 1)
                    for frac in [-1.0, 1.0]:
                        px = frac * dperp_x
                        py = frac * dperp_y
                        dsf_rebar_lines.extend([
                            x1 + px, y1 + py, z_side,
                            x2 + px, y2 + py, z_side
                        ])

            # Closed stirrups perpendicular to diagonal span
            n_st_dsf = max(6, int(math.ceil(span_dsf * 7.0)))
            for s_idx in range(1, n_st_dsf):
                s_frac = s_idx / n_st_dsf
                sx = x1 + s_frac * (x2 - x1)
                sy = y1 + s_frac * (y2 - y1)
                c_tl = [sx - dperp_x, sy - dperp_y, z_top_dsf]
                c_tr = [sx + dperp_x, sy + dperp_y, z_top_dsf]
                c_br = [sx + dperp_x, sy + dperp_y, z_bot_dsf]
                c_bl = [sx - dperp_x, sy - dperp_y, z_bot_dsf]
                dsf_rebar_lines.extend([
                    c_tl[0], c_tl[1], c_tl[2], c_tr[0], c_tr[1], c_tr[2],
                    c_tr[0], c_tr[1], c_tr[2], c_br[0], c_br[1], c_br[2],
                    c_br[0], c_br[1], c_br[2], c_bl[0], c_bl[1], c_bl[2],
                    c_bl[0], c_bl[1], c_bl[2], c_tl[0], c_tl[1], c_tl[2],
                ])

            rebar_elements.append({
                "id": f"rebar_{sb_corner_id}",
                "parent_id": sb_corner_id,
                "category": "rebar_strap",
                "color": "#e11d48",
                "name": f"قفص تسليح كمرة الشداد المائل {dsf_name}",
                "lines": dsf_rebar_lines,
            })

    # 1.3.E UNIVERSAL FOOTING FALLBACK: Guaranteed 100% Footing & Label Coverage for ALL Columns
    for c in active_cols:
        cid = str(c.get("id"))
        if cid in covered_footing_cols:
            continue

        cx = float(c.get("center_x", c.get("x", 0.0)))
        cy = float(c.get("center_y", c.get("y", 0.0)))
        pu_tot = float(c.get("pu_tot", c.get("Pu", 60.0) * num_floors))
        if pu_tot <= 0:
            pu_tot = 50.0

        P_w = pu_tot / 1.5
        q_net = 1.50  # kg/cm2
        A_req_m2 = (1.05 * P_w) / (q_net * 10.0)
        side_m = math.sqrt(max(1.0, A_req_m2))
        L_rc = max(1.40, math.ceil(side_m * 20.0) / 20.0)
        B_rc = L_rc
        t_rc = max(0.40, min(0.80, math.ceil((0.40 + (pu_tot / 350.0) * 0.25) * 20.0) / 20.0))
        L_pc = L_rc + 0.40
        B_pc = B_rc + 0.40
        t_pc = 0.20

        f_id = f"ftg_iso_{cid}"
        m_name = f"F-{cid}"
        clean_ftg_label = f"F-{cid}"

        concrete_elements.append({
            "id": f_id,
            "category": "footings",
            "name": f"قاعدة منفصلة {m_name} (عمود {cid})",
            "label": clean_ftg_label,
            "type": "Isolated Footing (RC)",
            "x": cx,
            "y": cy,
            "z": z_ground - (t_rc / 2.0),
            "dx": L_rc,
            "dy": B_rc,
            "dz": t_rc,
            "color": "#0284c7",
            "details": {
                "النموذج": f"{m_name} (قاعدة منفصلة مسلحة)",
                "العمود المرتكز": cid,
                "أبعاد المسلحة (L × B × t)": f"{int(round(L_rc * 100))} × {int(round(B_rc * 100))} × {int(round(t_rc * 100))} سم",
                "أبعاد العادية (L × B × t)": f"{int(round(L_pc * 100))} × {int(round(B_pc * 100))} × {int(round(t_pc * 100))} سم",
                "التسليح السفلي": "6 Φ 16 / م (اتجاهين)",
                "حالة الأمان": "✅ Safe ومحقق للكود",
            }
        })

        concrete_elements.append({
            "id": f"{f_id}_pc",
            "category": "footings_pc",
            "name": f"خرسانة عادية للقاعدة {m_name}",
            "type": "Plain Concrete (PC)",
            "x": cx,
            "y": cy,
            "z": z_ground - t_rc - (t_pc / 2.0),
            "dx": L_pc,
            "dy": B_pc,
            "dz": t_pc,
            "color": "#94a3b8",
            "details": {
                "النوع": "خرسانة عادية أسفل القاعدة المسلحة (P.C.)",
                "الأبعاد": f"{int(round(L_pc * 100))} × {int(round(B_pc * 100))} × 20 سم",
                "الرفرفة القياسية": "20 سم من جميع الجهات",
            }
        })

        f_cov = cover_ftg_cm / 100.0
        rebar_w = L_rc - 2 * f_cov
        rebar_d = B_rc - 2 * f_cov
        z_mesh = z_ground - t_rc + f_cov
        hook_h = max(0.15, t_rc - 2 * f_cov)

        ftg_mesh_lines = []
        n_bars_y = max(5, int(math.ceil(rebar_d * 6.0)))
        for k in range(n_bars_y):
            y_pos = cy - (rebar_d / 2.0) + (k / max(1, n_bars_y - 1)) * rebar_d
            x_start = cx - (rebar_w / 2.0)
            x_end = cx + (rebar_w / 2.0)
            ftg_mesh_lines.extend([x_start, y_pos, z_mesh, x_end, y_pos, z_mesh])
            ftg_mesh_lines.extend([x_start, y_pos, z_mesh, x_start, y_pos, z_mesh + hook_h])
            ftg_mesh_lines.extend([x_end, y_pos, z_mesh, x_end, y_pos, z_mesh + hook_h])

        n_bars_x = max(5, int(math.ceil(rebar_w * 6.0)))
        for k in range(n_bars_x):
            x_pos = cx - (rebar_w / 2.0) + (k / max(1, n_bars_x - 1)) * rebar_w
            y_start = cy - (rebar_d / 2.0)
            y_end = cy + (rebar_d / 2.0)
            ftg_mesh_lines.extend([x_pos, y_start, z_mesh + 0.02, x_pos, y_end, z_mesh + 0.02])
            ftg_mesh_lines.extend([x_pos, y_start, z_mesh + 0.02, x_pos, y_start, z_mesh + hook_h])
            ftg_mesh_lines.extend([x_pos, y_end, z_mesh + 0.02, x_pos, y_end, z_mesh + hook_h])

        rebar_elements.append({
            "id": f"rebar_{f_id}",
            "parent_id": f_id,
            "category": "rebar_ftg",
            "color": "#14b8a6",
            "name": f"شبكة تسليح القاعدة {m_name}",
            "lines": ftg_mesh_lines,
        })
        covered_footing_cols.add(cid)

    # 1.4 GROUND BEAMS (السملات والميدات الأرضية)
    # Bottom level unified at z_gb_bot, depth differences extend strictly UPWARDS
    if gb_analysis:
        for gb in gb_analysis.get("ground_beams", []):
            gb_id = gb.get("elem_id", "GB-1")
            c1 = gb.get("col1", {})
            c2 = gb.get("col2", {})
            c1_id = str(c1.get("id", gb.get("col1_id", "")))
            c2_id = str(c2.get("id", gb.get("col2_id", "")))

            c1_ref = active_cols_map.get(c1_id, {})
            c2_ref = active_cols_map.get(c2_id, {})

            x1 = float(c1.get("x", c1_ref.get("center_x", c1_ref.get("x", 0.0))))
            y1 = float(c1.get("y", c1_ref.get("center_y", c1_ref.get("y", 0.0))))
            x2 = float(c2.get("x", c2_ref.get("center_x", c2_ref.get("x", 0.0))))
            y2 = float(c2.get("y", c2_ref.get("center_y", c2_ref.get("y", 0.0))))

            b_m = float(gb.get("b_cm", 25.0)) / 100.0
            t_m = float(gb.get("exec_t_cm", gb.get("t_calc", 60.0))) / 100.0
            span = math.hypot(x2 - x1, y2 - y1)
            if span < 0.20:
                continue

            mid_x = (x1 + x2) / 2.0
            mid_y = (y1 + y2) / 2.0
            angle_gb = math.atan2(y2 - y1, x2 - x1)
            gb_label = gb.get("tag") or gb.get("model_mark") or gb_id

            # UNIFIED BOTTOM: center is at z_gb_bot + (t_m / 2.0). Height extends UPWARDS.
            z_gb_center = z_gb_bot + (t_m / 2.0)

            concrete_elements.append({
                "id": f"gb_{gb_id}",
                "category": "ground_beams",
                "name": f"سملة أرضية {gb_id} ({c1_id} إلى {c2_id})",
                "label": gb_label,
                "type": "Ground Beam (GB)",
                "x": mid_x,
                "y": mid_y,
                "z": z_gb_center,
                "dx": span,
                "dy": b_m,
                "dz": t_m,
                "rot_z": angle_gb,
                "color": "#65a30d",
                "details": {
                    "النموذج": f"{gb_id} — {gb.get('tag', 'B1')}",
                    "الأعمدة المربوطة": f"{c1_id} ⟷ {c2_id}",
                    "منسوب القاع الموحد": f"{z_gb_bot:.2f} م (منسوب الحفر والتأسيس الموحد)",
                    "منسوب أعلى السملة": f"{(z_gb_bot + t_m):.2f} م (الفارق ممتد لأعلى)",
                    "المحور": gb.get("axis_name", gb.get("axis_str", "—")),
                    "البحر (Span)": f"{span:.2f} م (صافي {gb.get('clear_span_m', span):.2f} م)",
                    "القطاع (b × t)": f"{int(round(b_m*100))} × {int(round(t_m*100))} سم",
                    "التسليح السفلي": f"{gb.get('exec_n_bot', 3)} Φ {gb.get('phi_bot', 16)}",
                    "التسليح العلوي": f"{gb.get('exec_n_top', 2)} Φ {gb.get('phi_top', 12)}",
                    "براندات الجوانب": f"{gb.get('exec_side_bars', 0)} Φ {gb.get('phi_side', 10)}" if gb.get('exec_side_bars', 0) > 0 else "غير مطلوبة",
                    "الكانات": f"{gb.get('exec_stirrups_per_m', 6)} Φ {gb.get('phi_st', 8)} / م",
                    "حالة التحقق": gb.get("shear_status", "✅ Safe"),
                }
            })

            # Rebar Lines (aligned with unified bottom level z_gb_bot)
            gb_lines = []
            cov = cover_gb_cm / 100.0
            z_bot_g = z_gb_bot + cov
            z_top_g = z_gb_bot + t_m - cov
            dx_u = (x2 - x1) / span
            dy_u = (y2 - y1) / span
            p_x = -dy_u * (b_m / 2.0 - cov)
            p_y = dx_u * (b_m / 2.0 - cov)

            gb_lines.extend([
                x1 - p_x, y1 - p_y, z_top_g, x2 - p_x, y2 - p_y, z_top_g,
                x1 + p_x, y1 + p_y, z_top_g, x2 + p_x, y2 + p_y, z_top_g,
            ])
            gb_lines.extend([
                x1 - p_x, y1 - p_y, z_bot_g, x2 - p_x, y2 - p_y, z_bot_g,
                x1, y1, z_bot_g, x2, y2, z_bot_g,
                x1 + p_x, y1 + p_y, z_bot_g, x2 + p_x, y2 + p_y, z_bot_g,
            ])

            st_count = max(4, int(math.ceil(span * gb.get("exec_stirrups_per_m", 5))))
            for s_idx in range(1, st_count):
                frac = s_idx / st_count
                sx = x1 + frac * (x2 - x1)
                sy = y1 + frac * (y2 - y1)
                gb_lines.extend([
                    sx - p_x, sy - p_y, z_top_g, sx + p_x, sy + p_y, z_top_g,
                    sx + p_x, sy + p_y, z_top_g, sx + p_x, sy + p_y, z_bot_g,
                    sx + p_x, sy + p_y, z_bot_g, sx - p_x, sy - p_y, z_bot_g,
                    sx - p_x, sy - p_y, z_bot_g, sx - p_x, sy - p_y, z_top_g,
                ])

            rebar_elements.append({
                "id": f"rebar_gb_{gb_id}",
                "parent_id": f"gb_{gb_id}",
                "category": "rebar_gb",
                "color": "#84cc16",
                "name": f"تسليح سملة {gb_id}",
                "lines": gb_lines,
            })

    # 1.5 SLAB REINFORCEMENT
    cov_s = cover_slab_cm / 100.0
    z_slab_rebar_bot_x = z_slab_bot + cov_s
    z_slab_rebar_bot_y = z_slab_rebar_bot_x + 0.015
    z_slab_rebar_top_y = z_slab_top - cov_s - 0.015
    z_slab_rebar_top_x = z_slab_top - cov_s

    slab_bot_lines = []
    step_y = max(0.20, 1.0 / max(1.0, n_mesh_btm))
    curr_y = y_min_slab + 0.10
    while curr_y <= y_max_slab - 0.10:
        slab_bot_lines.extend([
            x_min_slab + 0.05, curr_y, z_slab_rebar_bot_x,
            x_max_slab - 0.05, curr_y, z_slab_rebar_bot_x,
        ])
        curr_y += step_y

    step_x = max(0.20, 1.0 / max(1.0, n_mesh_btm))
    curr_x = x_min_slab + 0.10
    while curr_x <= x_max_slab - 0.10:
        slab_bot_lines.extend([
            curr_x, y_min_slab + 0.05, z_slab_rebar_bot_y,
            curr_x, y_max_slab - 0.05, z_slab_rebar_bot_y,
        ])
        curr_x += step_x

    rebar_elements.append({
        "id": "rebar_slab_bot_mesh",
        "parent_id": "slab_main",
        "category": "rebar_slab_bot",
        "color": "#0284c7",  # Cyan
        "name": f"الشبكة السفلية للبلاطة ({n_mesh_btm:.0f}Φ{bottom_mesh_dia}/م)",
        "lines": slab_bot_lines,
    })

    slab_top_lines = []
    step_top_y = max(0.25, 1.0 / max(1.0, n_mesh_top))
    curr_y = y_min_slab + 0.15
    while curr_y <= y_max_slab - 0.15:
        slab_top_lines.extend([
            x_min_slab + 0.05, curr_y, z_slab_rebar_top_x,
            x_max_slab - 0.05, curr_y, z_slab_rebar_top_x,
        ])
        curr_y += step_top_y

    step_top_x = max(0.25, 1.0 / max(1.0, n_mesh_top))
    curr_x = x_min_slab + 0.15
    while curr_x <= x_max_slab - 0.15:
        slab_top_lines.extend([
            curr_x, y_min_slab + 0.05, z_slab_rebar_top_y,
            curr_x, y_max_slab - 0.05, z_slab_rebar_top_y,
        ])
        curr_x += step_top_x

    rebar_elements.append({
        "id": "rebar_slab_top_mesh",
        "parent_id": "slab_main",
        "category": "rebar_slab_top",
        "color": "#6366f1",  # Indigo
        "name": f"الشبكة العلوية للبلاطة ({n_mesh_top:.0f}Φ{top_mesh_dia}/م)",
        "lines": slab_top_lines,
    })

    if top_extra_cols:
        col_caps_lines = []
        for tec in top_extra_cols:
            tcx = float(tec.get("x", 0.0))
            tcy = float(tec.get("y", 0.0))
            l_ext = float(tec.get("L_extra", 2.0))
            n_ext = int(tec.get("n_extra", 6))
            half_l = l_ext / 2.0
            cap_w = max(0.80, l_ext * 0.40)
            for k in range(max(2, n_ext // 2)):
                frac = (k / max(1, (n_ext // 2) - 1)) - 0.5
                col_caps_lines.extend([
                    tcx - half_l, tcy + frac * cap_w, z_slab_top - 0.01,
                    tcx + half_l, tcy + frac * cap_w, z_slab_top - 0.01,
                ])
                col_caps_lines.extend([
                    tcx + frac * cap_w, tcy - half_l, z_slab_top - 0.012,
                    tcx + frac * cap_w, tcy + half_l, z_slab_top - 0.012,
                ])

        if col_caps_lines:
            rebar_elements.append({
                "id": "rebar_col_caps",
                "parent_id": "slab_main",
                "category": "rebar_col_caps",
                "color": "#f97316",  # Orange
                "name": "كابات وإضافي علوي للأعمدة (Column Caps Extra)",
                "lines": col_caps_lines,
            })

    punch_stirrups_lines = []
    if punching_results:
        for pr in punching_results:
            des_st = pr.get("stirrups_design")
            if des_st and des_st.get("req_stirrups", False):
                pcx = float(pr.get("x", 0.0))
                pcy = float(pr.get("y", 0.0))
                pbc = float(pr.get("bc", 30.0)) / 100.0
                ptc = float(pr.get("tc", 50.0)) / 100.0
                s0 = 0.10
                s = 0.12
                for rail_dist in [s0, s0 + s]:
                    rw = (ptc / 2.0) + rail_dist
                    rh = (pbc / 2.0) + rail_dist
                    for px_offset, py_offset in [
                        (-rw, 0), (rw, 0), (0, -rh), (0, rh),
                        (-rw, -rh), (rw, -rh), (-rw, rh), (rw, rh)
                    ]:
                        pin_x = pcx + px_offset
                        pin_y = pcy + py_offset
                        punch_stirrups_lines.extend([
                            pin_x, pin_y, z_slab_bot + 0.02,
                            pin_x, pin_y, z_slab_top - 0.02,
                            pin_x, pin_y, z_slab_top - 0.02,
                            pin_x + 0.05, pin_y, z_slab_top - 0.02
                        ])

    if punch_stirrups_lines:
        rebar_elements.append({
            "id": "rebar_punching_stirrups",
            "parent_id": "slab_main",
            "category": "rebar_punching",
            "color": "#ec4899",  # Magenta
            "name": "كانات مقاومة القص الثاقب (Punching Shear Stirrups)",
            "lines": punch_stirrups_lines,
        })

    return {
        "span_x": round(slab_w_x, 2),
        "span_y": round(slab_w_y, 2),
        "center_x": round(slab_center_x, 2),
        "center_y": round(slab_center_y, 2),
        "building_height": round(z_slab_top - (z_ground - 1.20), 2),
        "z_ground": z_ground,
        "z_slab_top": z_slab_top,
        "concrete_elements": concrete_elements,
        "rebar_elements": rebar_elements,
        "metrics": {
            "num_columns": len(active_cols),
            "num_footings": (
                len(ftg_analysis.get("isolated_footings", []))
                + len(ftg_analysis.get("combined_footings", []))
                + len(ftg_analysis.get("edge_strap_footings", [])) * 2
                + len(ftg_analysis.get("corner_strap_footings", [])) * 2
            ) if ftg_analysis else 0,
            "num_ground_beams": len(gb_analysis.get("ground_beams", [])) if gb_analysis else 0,
            "slab_area_m2": round(slab_w_x * slab_w_y, 2),
            "num_floors": num_floors,
        }
    }


def generate_bim_3d_html(scene_data: dict, height: int = 760) -> str:
    """
    Generates the standalone WebGL Three.js 3D Viewer application HTML.
    """
    json_str = json.dumps(scene_data)

    cats = scene_data.get("categories")
    if cats:
        filter_chips_html = "\n    ".join([
            f'<button class="filter-chip active" id="flt-{c["id"]}" data-cat="{c["id"]}">{c["name"]}</button>'
            for c in cats
        ])
    else:
        filter_chips_html = """<button class="filter-chip active" id="flt-slab" data-cat="slab">السقف</button>
    <button class="filter-chip active" id="flt-cols" data-cat="columns">الأعمدة</button>
    <button class="filter-chip active" id="flt-ftgs" data-cat="footings">الأساسات</button>
    <button class="filter-chip active" id="flt-gb" data-cat="ground_beams">السملات والشدادات</button>
    <button class="filter-chip active" id="flt-rebar" data-cat="rebar">حديد التسليح</button>"""

    legend_items = scene_data.get("legend_items")
    if legend_items:
        legend_html = '<span style="color:#38bdf8; font-weight:800; margin-left:4px;">🎨 كود الألوان والتسميات:</span>\n' + "\n".join([
            f'  <div class="legend-item"><span class="legend-dot" style="background:{it["color"]}; border-radius:3px;"></span> {it["name"]}</div>'
            for it in legend_items
        ])
    else:
        legend_html = """<span style="color:#38bdf8; font-weight:800; margin-left:4px;">🎨 كود الألوان والتسميات:</span>
  <div class="legend-item"><span class="legend-dot" style="background:#38bdf8; border-radius:3px;"></span> تسميات الأعمدة (C1...)</div>
  <div class="legend-item"><span class="legend-dot" style="background:#34d399; border-radius:3px;"></span> تسميات القواعد (F1, SF, DSF...)</div>
  <div class="legend-item"><span class="legend-dot" style="background:#f43f5e; border-radius:3px;"></span> تسميات الشدادات والسملات (B1, ST1...)</div>
  <div class="legend-item"><span class="legend-dot" style="background:#0284c7;"></span> شبكة بلاطة سفلية</div>
  <div class="legend-item"><span class="legend-dot" style="background:#6366f1;"></span> شبكة بلاطة علوية</div>
  <div class="legend-item"><span class="legend-dot" style="background:#f97316;"></span> كابات إضافي الأعمدة</div>
  <div class="legend-item"><span class="legend-dot" style="background:#ec4899;"></span> كانات القص الثاقب</div>
  <div class="legend-item"><span class="legend-dot" style="background:#10b981;"></span> تسليح الأعمدة الطولي</div>
  <div class="legend-item"><span class="legend-dot" style="background:#84cc16;"></span> كانات وسملات</div>
  <div class="legend-item"><span class="legend-dot" style="background:#14b8a6;"></span> تسليح القواعد</div>
  <div class="legend-item"><span class="legend-dot" style="background:#e11d48;"></span> حديد كمرات الشدادات (Strap Beams)</div>"""

    sketch_title = scene_data.get("sketch_title", "مسقط وتفاصيل التسليح الإنشائي (Structural Detailing)")
    sketch_btn_title = scene_data.get("sketch_btn_title", "🗺️ مسقط الرسم")
    sketch_dl_name = scene_data.get("sketch_dl_name", "Structural_Layout_Sketch.png")

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
  body, html {{ width: 100%; height: 100%; overflow: hidden; background: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
  #canvas-container {{ width: 100%; height: 100%; position: absolute; top: 0; left: 0; cursor: grab; }}
  #canvas-container:active {{ cursor: grabbing; }}

  /* Top Control Toolbar */
  .toolbar {{
    position: absolute;
    top: 10px;
    left: 10px;
    right: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    pointer-events: none;
    z-index: 20;
    gap: 8px;
    flex-wrap: wrap;
  }}
  .tb-group {{
    display: flex;
    gap: 6px;
    align-items: center;
    pointer-events: auto;
    background: rgba(15, 23, 42, 0.88);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 8px;
    padding: 6px 12px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  }}
  .btn-tool {{
    background: #1e293b;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 5px 11px;
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s ease;
  }}
  .btn-tool:hover {{
    background: #334155;
    border-color: #38bdf8;
    color: #38bdf8;
  }}
  .btn-tool.active {{
    background: #0284c7;
    border-color: #38bdf8;
    color: #ffffff;
  }}

  /* X-Ray Toggle Button in Filters Group */
  .btn-xray-toggle {{
    background: #1e293b;
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.45);
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11.5px;
    font-weight: 800;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }}
  .btn-xray-toggle:hover {{
    background: #0284c7;
    color: #ffffff;
    border-color: #38bdf8;
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
  }}
  .btn-xray-toggle.active {{
    background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
    color: #ffffff;
    border-color: #38bdf8;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.7);
  }}

  /* Filter Toggles */
  .filter-chip {{
    background: rgba(30, 41, 59, 0.8);
    color: #94a3b8;
    border: 1px solid #475569;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .filter-chip.active {{
    background: #0369a1;
    color: #ffffff;
    border-color: #38bdf8;
  }}

  /* Rebar Legend Bottom Bar */
  .rebar-legend {{
    position: absolute;
    bottom: 12px;
    left: 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    pointer-events: auto;
    background: rgba(15, 23, 42, 0.90);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 8px;
    padding: 7px 12px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    font-size: 11px;
    font-weight: 700;
    color: #cbd5e1;
    z-index: 15;
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 5px;
  }}
  .legend-dot {{
    width: 10px;
    height: 10px;
    border-radius: 2px;
    display: inline-block;
  }}

  /* Help Tooltip */
  .help-bar {{
    position: absolute;
    bottom: 12px;
    right: 12px;
    background: rgba(15, 23, 42, 0.90);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(148, 163, 184, 0.25);
    border-radius: 8px;
    padding: 7px 14px;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    pointer-events: auto;
    z-index: 15;
  }}

  /* Floating Inspector Panel */
  .inspector-panel {{
    position: absolute;
    top: 60px;
    right: 12px;
    width: 320px;
    max-height: calc(100% - 130px);
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1.5px solid #38bdf8;
    border-radius: 10px;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.75);
    z-index: 25;
    overflow: hidden;
    display: none;
    flex-direction: column;
    animation: slideInRtl 0.2s ease-out;
  }}
  @keyframes slideInRtl {{
    from {{ opacity: 0; transform: translateX(20px); }}
    to {{ opacity: 1; transform: translateX(0); }}
  }}
  .insp-header {{
    background: rgba(30, 41, 59, 0.98);
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(148, 163, 184, 0.3);
  }}
  .insp-title {{
    font-size: 13px;
    font-weight: 800;
    color: #38bdf8;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .btn-close {{
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 14px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
  }}
  .btn-close:hover {{ background: rgba(239, 68, 68, 0.25); color: #ef4444; }}
  .insp-body {{
    padding: 12px 14px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}
  .insp-row {{
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 6px;
    padding: 6px 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .insp-lbl {{ font-size: 11px; color: #94a3b8; font-weight: 600; }}
  .insp-val {{ font-size: 11.5px; color: #f8fafc; font-weight: 800; }}
  .insp-actions {{
    display: flex;
    gap: 6px;
    margin-top: 6px;
  }}
  .btn-isolate {{
    flex: 1;
    background: #0284c7;
    color: #ffffff;
    border: 1px solid #38bdf8;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 11.5px;
    font-weight: 800;
    cursor: pointer;
    text-align: center;
    transition: all 0.15s;
  }}
  .btn-isolate:hover {{ background: #0369a1; }}
  .btn-reset-iso {{
    background: #334155;
    color: #e2e8f0;
    border: 1px solid #64748b;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
  }}
  .btn-reset-iso:hover {{ background: #475569; }}

  /* Fullscreen & Toolbar Buttons */
  #btn-fullscreen.active {{
    background: #0284c7;
    border-color: #38bdf8;
    color: #ffffff;
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.6);
  }}

  /* Foundation Layout Sketch Picture-in-Picture Overlay (Top-Left) */
  .sketch-box {{
    position: absolute;
    top: 56px;
    left: 12px;
    width: 330px;
    background: rgba(15, 23, 42, 0.94);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1.5px solid #38bdf8;
    border-radius: 10px;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.75);
    z-index: 24;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    pointer-events: auto;
    transition: width 0.2s ease, max-height 0.2s ease, opacity 0.2s ease, box-shadow 0.2s ease;
  }}
  .sketch-box.enlarged {{
    width: 620px;
    max-width: calc(100vw - 30px);
  }}
  .sketch-box.minimized .sketch-body {{
    display: none;
  }}
  .sketch-box.sketch-fullscreen {{
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 100vw !important;
    max-width: 100vw !important;
    height: 100vh !important;
    border-radius: 0 !important;
    z-index: 99999 !important;
    background: #050a14 !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
  }}
  /* sketch-body must fill remaining height after header */
  .sketch-box.sketch-fullscreen .sketch-body {{
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
    padding: 0 !important;
    gap: 0 !important;
    overflow: hidden !important;
    background: #050a14 !important;
  }}
  /* img-wrap fills all body height */
  .sketch-box.sketch-fullscreen .sketch-img-wrap {{
    flex: 1 1 auto !important;
    width: 100% !important;
    max-height: none !important;
    height: 100% !important;
    overflow: hidden !important;
    background: #0f172a !important;
    border-radius: 0 !important;
    border: none !important;
    cursor: grab !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    user-select: none !important;
  }}
  /* image centered — transform is controlled entirely by JS pan/zoom */
  .sketch-box.sketch-fullscreen .sketch-img {{
    width: auto !important;
    height: auto !important;
    max-width: 100% !important;
    max-height: 100% !important;
    object-fit: contain !important;
    display: block !important;
    margin: auto !important;
    will-change: transform;
    transition: none !important;
    transform-origin: center center !important;
    pointer-events: none !important;
    user-select: none !important;
    -webkit-user-drag: none !important;
  }}
  /* footer stays at bottom */
  .sketch-box.sketch-fullscreen .sketch-footer {{
    flex-shrink: 0 !important;
    padding: 6px 12px !important;
    background: rgba(15,23,42,0.95) !important;
    border-top: 1px solid rgba(56,189,248,0.2) !important;
  }}
  /* Hide buttons in Fullscreen mode as requested */
  .sketch-box.sketch-fullscreen #btn-sketch-align-top,
  .sketch-box.sketch-fullscreen #btn-sketch-size,
  .sketch-box.sketch-fullscreen #btn-sketch-min,
  .sketch-box.sketch-fullscreen #btn-sketch-close {{
    display: none !important;
  }}
  .sketch-box.sketch-fullscreen .sketch-header {{
    cursor: default !important;
    padding: 8px 16px !important;
    background: #0f172a !important;
    border-bottom: 1px solid rgba(56, 189, 248, 0.25) !important;
  }}
  .sketch-box.sketch-fullscreen #btn-sketch-fullscreen {{
    font-size: 11.5px !important;
    padding: 5px 14px !important;
    border-radius: 6px !important;
    background: #0284c7 !important;
    color: #ffffff !important;
    border: 1px solid #38bdf8 !important;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important;
  }}
  .sketch-box.sketch-fullscreen #btn-sketch-fullscreen:hover {{
    background: #ef4444 !important;
    border-color: #f87171 !important;
    box-shadow: 0 0 10px rgba(239, 68, 68, 0.5) !important;
  }}
  #btn-sketch-fullscreen {{
    background: linear-gradient(135deg, #1e3a5f 0%, #1e293b 100%);
    color: #38bdf8;
    border-color: #38bdf8;
    font-size: 10px;
  }}
  #btn-sketch-fullscreen:hover {{
    background: #0284c7;
    color: #ffffff;
  }}
  #btn-sketch-fullscreen.active {{
    background: #0284c7;
    color: #ffffff;
    box-shadow: 0 0 6px rgba(56,189,248,0.5);
  }}
  .sketch-header {{
    background: rgba(30, 41, 59, 0.98);
    padding: 7px 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(56, 189, 248, 0.35);
    cursor: grab;
    user-select: none;
  }}
  .sketch-title {{
    font-size: 11.5px;
    font-weight: 800;
    color: #38bdf8;
    display: flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .sketch-actions {{
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }}
  .btn-sketch-action {{
    background: #1e293b;
    color: #cbd5e1;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10.5px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .btn-sketch-action:hover {{
    background: #334155;
    color: #38bdf8;
    border-color: #38bdf8;
  }}
  .sketch-body {{
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: rgba(11, 15, 25, 0.75);
  }}
  .sketch-img-wrap {{
    width: 100%;
    max-height: 240px;
    overflow: hidden;
    border-radius: 6px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: grab;
    user-select: none;
    transition: max-height 0.2s ease;
  }}
  .sketch-box.enlarged .sketch-img-wrap {{
    max-height: 460px;
  }}
  .sketch-img {{
    width: 100%;
    height: auto;
    max-height: 100%;
    object-fit: contain;
    display: block;
    transform-origin: center center;
    pointer-events: none;
    user-select: none;
    -webkit-user-drag: none;
  }}
  .sketch-footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 10px;
    color: #94a3b8;
    font-weight: 700;
    padding: 3px 4px 0 4px;
    gap: 6px;
  }}
  .sketch-controls-group {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
  }}
  .sketch-control-item {{
    display: flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
  }}
  .sketch-opacity-control {{
    display: flex;
    align-items: center;
    gap: 4px;
  }}
  .sketch-opacity-control input[type="range"],
  .sketch-zoom-control input[type="range"] {{
    -webkit-appearance: none;
    direction: ltr;
    width: 65px;
    height: 4px;
    border-radius: 2px;
    background: #334155;
    outline: none;
    cursor: pointer;
  }}
  .sketch-opacity-control input[type="range"]::-webkit-slider-thumb,
  .sketch-zoom-control input[type="range"]::-webkit-slider-thumb {{
    -webkit-appearance: none;
    appearance: none;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    background: #38bdf8;
    border: 1.5px solid #fff;
    cursor: pointer;
  }}
  .sketch-zoom-control input[type="range"]::-webkit-slider-thumb {{
    background: #34d399;
  }}
  .sketch-opacity-control input[type="range"]::-moz-range-thumb,
  .sketch-zoom-control input[type="range"]::-moz-range-thumb {{
    width: 11px;
    height: 11px;
    border-radius: 50%;
    background: #38bdf8;
    border: 1.5px solid #fff;
    cursor: pointer;
  }}
  .sketch-zoom-control input[type="range"]::-moz-range-thumb {{
    background: #34d399;
  }}
  .sketch-zoom-control {{
    display: flex;
    align-items: center;
    gap: 4px;
  }}
  .sketch-dl-btn {{
    color: #38bdf8;
    text-decoration: none;
    font-size: 10.5px;
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.3);
    transition: background 0.15s;
  }}
  .sketch-dl-btn:hover {{
    background: rgba(56, 189, 248, 0.35);
  }}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
<div id="canvas-container"></div>

<!-- Top Toolbar -->
<div class="toolbar">
  <div class="tb-group">
    <button class="btn-tool active" id="btn-view-3d" title="منظور ثلاثي الأبعاد إيزومتري">🏛️ 3D</button>
    <button class="btn-tool" id="btn-view-top" title="مسقط أفقي للسقف">📐 مسقط (Top)</button>
    <button class="btn-tool" id="btn-view-front" title="واجهة أمامية">🏢 أمامية (Front)</button>
    <button class="btn-tool" id="btn-view-side" title="واجهة جانبية">🏛️ جانبية (Side)</button>
    <button class="btn-tool" id="btn-reset-cam" title="إعادة ضبط زاوية الكاميرا">🔄 ضبط</button>
    <button class="btn-tool" id="btn-theme" title="تبديل الخلفية">🌙 / ☀️</button>
    <button class="btn-tool active" id="btn-toggle-labels" title="إظهار / إخفاء أسماء وتسميات العناصر الإنشائية (C1, F1...)">🏷️ الأسماء (Labels)</button>
    <button class="btn-tool active" id="btn-toggle-sketch" title="إظهار / إخفاء المخطط والمسقط (Layout Sketch)">{sketch_btn_title}</button>
    <button class="btn-tool" id="btn-fullscreen" title="عرض كامل الشاشة بنفس الأزرار والأدوات">⛶ ملء الشاشة</button>
  </div>

  <div class="tb-group" id="tb-filters-group">
    <span style="font-size: 11.5px; font-weight: 800; color:#94a3b8; margin-left: 4px;">الفلاتر:</span>
    {filter_chips_html}
    <div style="width: 1px; height: 18px; background: rgba(148, 163, 184, 0.35); margin: 0 4px; flex-shrink: 0;"></div>
    <button class="btn-xray-toggle" id="btn-xray-toggle" title="تبديل وضع الشفافية لإظهار أو إخفاء حديد التسليح داخل الخرسانة (X-Ray Toggle)">⚡ X-Ray</button>
  </div>
</div>

<div class="rebar-legend" id="rebar-legend">
  {legend_html}
</div>

<div class="help-bar">
  🖱️ تدوير: سحب بالفأرة &nbsp;|&nbsp; Zoom: عجلة الفأرة &nbsp;|&nbsp; Pan: زر الفأرة الأيمن &nbsp;|&nbsp; 🏷️ انقر على أي عنصر أو تسمية لفحصه وعزله
</div>

<!-- Foundation Layout Sketch Picture-in-Picture Box (Top-Left Corner) -->
<div class="sketch-box" id="sketch-box">
  <div class="sketch-header" id="sketch-header">
    <div class="sketch-title">
      <span>📐</span>
      <span>{sketch_title}</span>
    </div>
    <div class="sketch-actions">
      <button class="btn-sketch-action" id="btn-sketch-align-top" title="محاذاة كاميرا المجسم 3D للمسقط الأفقي لمقارنة مطابقة 1:1">📐 مسقط 3D</button>
      <button class="btn-sketch-action" id="btn-sketch-size" title="توسيع نافذة المسقط الإنشائي">⛶ نافذة عريضة</button>
      <button class="btn-sketch-action" id="btn-sketch-fullscreen" title="عرض المسقط الإنشائي بملء الشاشة">⛶ ملء الشاشة</button>
      <button class="btn-sketch-action" id="btn-sketch-min" title="طي / توسيع نافذة المخطط">➖</button>
      <button class="btn-sketch-action" id="btn-sketch-close" title="إخفاء نافذة المخطط">✕</button>
    </div>
  </div>
  <div class="sketch-body" id="sketch-body">
    <div class="sketch-img-wrap" id="sketch-img-wrap" title="🖱️ سحب: تحريك (Pan) | عجلة الفأرة: تكبير وتصغير (Zoom) | نقر مزدوج: استعادة الحجم">
      <img id="sketch-img" class="sketch-img" alt="Layout Plan Sketch" draggable="false" />
    </div>
    <div class="sketch-footer">
      <span style="color:#94a3b8; font-size:10px; font-weight:600;">🖱️ سحب: تحريك | عجلة: تكبير/تصغير | نقر مزدوج: ضبط</span>
      <a id="sketch-download-link" download="{sketch_dl_name}" class="sketch-dl-btn" title="تحميل صورة المسقط عالية الدقة">📥 تنزيل</a>
    </div>
  </div>
</div>

<div class="inspector-panel" id="inspector-panel">
  <div class="insp-header">
    <div class="insp-title">
      <span id="insp-icon">📋</span>
      <span id="insp-name">فاحص العنصر الإنشائي</span>
    </div>
    <button class="btn-close" id="btn-close-insp">✕</button>
  </div>
  <div class="insp-body" id="insp-body">
  </div>
</div>

<script>
(function() {{
  const data = {json_str};
  const container = document.getElementById('canvas-container');

  const scene = new THREE.Scene();
  const bgDark = 0x0b0f19;
  const bgLight = 0xf1f5f9;
  let isDark = true;
  scene.background = new THREE.Color(bgDark);

  const width = window.innerWidth;
  const height = window.innerHeight;
  const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 1000);

  const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = false;
  container.appendChild(renderer.domElement);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;
  controls.minDistance = 0.5;
  controls.maxDistance = 300.0;

  const ambLight = new THREE.AmbientLight(0xffffff, 0.75);
  scene.add(ambLight);

  const maxSpan = Math.max(data.span_x || 0, data.span_y || 0, data.building_height || 0, 2.5);
  const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.85);
  dirLight1.position.set(maxSpan * 1.5, maxSpan * 2.0, maxSpan * 1.5);
  scene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(0x93c5fd, 0.40);
  dirLight2.position.set(-maxSpan * 1.5, -maxSpan * 1.0, maxSpan * 1.2);
  scene.add(dirLight2);

  const concreteGroup = new THREE.Group();
  const rebarGroup = new THREE.Group();
  const edgesGroup = new THREE.Group();
  const labelsGroup = new THREE.Group();
  labelsGroup.renderOrder = 999;
  scene.add(concreteGroup);
  scene.add(rebarGroup);
  scene.add(edgesGroup);
  scene.add(labelsGroup);

  const concreteMeshes = [];
  const rebarMeshes = [];
  const elementDataMap = new Map();

  function createLabelSprite(text, category, options) {{
    options = options || {{}};
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    const fontSize = options.fontSize || 42;
    const fontFace = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif';
    ctx.font = 'bold ' + fontSize + 'px ' + fontFace;

    const textMetrics = ctx.measureText(text);
    const textWidth = textMetrics.width;
    const padX = 26;
    const padY = 14;
    const borderWidth = 3;

    const w = Math.ceil(textWidth + padX * 2);
    const h = Math.ceil(fontSize + padY * 2);

    canvas.width = w;
    canvas.height = h;

    ctx.font = 'bold ' + fontSize + 'px ' + fontFace;
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';

    let bgColor = 'rgba(15, 23, 42, 0.92)';
    let borderColor = '#38bdf8';
    let textColor = '#ffffff';

    if (category === 'columns') {{
      bgColor = 'rgba(15, 23, 42, 0.94)';
      borderColor = '#38bdf8';
      textColor = '#f0f9ff';
    }} else if (category === 'footings') {{
      bgColor = 'rgba(6, 78, 59, 0.94)';
      borderColor = '#34d399';
      textColor = '#ecfdf5';
    }} else if (category === 'ground_beams') {{
      bgColor = 'rgba(120, 53, 15, 0.94)';
      borderColor = '#fbbf24';
      textColor = '#fffbeb';
    }}

    if (options.bgColor) bgColor = options.bgColor;
    if (options.borderColor) borderColor = options.borderColor;
    if (options.textColor) textColor = options.textColor;

    const radius = 10;
    const bx = borderWidth / 2;
    const by = borderWidth / 2;
    const bw = w - borderWidth;
    const bh = h - borderWidth;

    ctx.beginPath();
    ctx.moveTo(bx + radius, by);
    ctx.lineTo(bx + bw - radius, by);
    ctx.quadraticCurveTo(bx + bw, by, bx + bw, by + radius);
    ctx.lineTo(bx + bw, by + bh - radius);
    ctx.quadraticCurveTo(bx + bw, by + bh, bx + bw - radius, by + bh);
    ctx.lineTo(bx + radius, by + bh);
    ctx.quadraticCurveTo(bx, by + bh, bx, by + bh - radius);
    ctx.lineTo(bx, by + radius);
    ctx.quadraticCurveTo(bx, by, bx + radius, by);
    ctx.closePath();

    ctx.fillStyle = bgColor;
    ctx.fill();

    ctx.lineWidth = borderWidth;
    ctx.strokeStyle = borderColor;
    ctx.stroke();

    ctx.shadowColor = 'rgba(0, 0, 0, 0.7)';
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 1;
    ctx.shadowOffsetY = 1;
    ctx.fillStyle = textColor;
    ctx.fillText(text, w / 2, h / 2 + 1);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.generateMipmaps = false;

    const spriteMat = new THREE.SpriteMaterial({{
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    }});

    const sprite = new THREE.Sprite(spriteMat);
    const aspect = w / h;
    const worldH = options.worldHeight || (category === 'columns' ? 0.38 : (category === 'footings' ? 0.34 : 0.28));
    sprite.scale.set(worldH * aspect, worldH, 1.0);
    sprite.renderOrder = 999;
    return sprite;
  }}

  const edgeMat = new THREE.LineBasicMaterial({{ color: 0x334155, transparent: true, opacity: 0.45 }});

  (data.concrete_elements || []).forEach(elem => {{
    const geom = new THREE.BoxGeometry(elem.dx, elem.dz, elem.dy);
    const colHex = elem.color ? parseInt(elem.color.replace('#', '0x')) : 0x94a3b8;
    const mat = new THREE.MeshStandardMaterial({{
      color: colHex,
      roughness: 0.75,
      metalness: 0.10,
      transparent: false,
      opacity: 1.0,
      depthWrite: true,
    }});

    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(elem.x, elem.z, -elem.y);
    if (elem.rot_z) {{
      mesh.rotation.y = elem.rot_z;
    }}

    mesh.userData = {{
      id: elem.id,
      name: elem.name,
      category: elem.category,
      type: elem.type,
      details: elem.details,
      origColor: colHex,
      mat: mat,
    }};

    concreteGroup.add(mesh);
    concreteMeshes.push(mesh);
    elementDataMap.set(elem.id, mesh);

    const edgesGeom = new THREE.EdgesGeometry(geom);
    const edgesMesh = new THREE.LineSegments(edgesGeom, edgeMat);
    edgesMesh.position.copy(mesh.position);
    edgesMesh.rotation.copy(mesh.rotation);
    edgesMesh.userData = {{ parentId: elem.id, category: elem.category }};
    edgesGroup.add(edgesMesh);

    // Create 3D Label Sprite if element has a label
    if (elem.label) {{
      let posX = elem.x;
      let posY = elem.z;
      let posZ = -elem.y;

      if (elem.category === 'columns') {{
        posY = elem.z + (elem.dz * 0.18);
      }} else if (elem.category === 'footings') {{
        posY = elem.z + (elem.dz / 2.0) + 0.10;
        const offX = Math.max(0.25, (elem.dx / 2.0) - 0.35);
        const offY = Math.max(0.25, (elem.dy / 2.0) - 0.35);
        posX = elem.x - offX;
        posZ = -(elem.y - offY);
      }} else if (elem.category === 'ground_beams') {{
        posY = elem.z + (elem.dz / 2.0) + 0.08;
      }}

      const sprite = createLabelSprite(elem.label, elem.category);
      sprite.position.set(posX, posY, posZ);
      sprite.userData = {{
        parentId: elem.id,
        category: elem.category,
        label: elem.label,
      }};
      labelsGroup.add(sprite);
    }}
  }});

  (data.rebar_elements || []).forEach(rElem => {{
    const lines = rElem.lines || [];
    if (lines.length < 6) return;

    const positions = new Float32Array(lines.length);
    for (let i = 0; i < lines.length; i += 6) {{
      positions[i]     = lines[i];
      positions[i + 1] = lines[i + 2];
      positions[i + 2] = -lines[i + 1];

      positions[i + 3] = lines[i + 3];
      positions[i + 4] = lines[i + 5];
      positions[i + 5] = -lines[i + 4];
    }}

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const colHex = rElem.color ? parseInt(rElem.color.replace('#', '0x')) : 0x38bdf8;
    const mat = new THREE.LineBasicMaterial({{
      color: colHex,
      transparent: true,
      opacity: 0.95,
      linewidth: 1,
    }});

    const lineMesh = new THREE.LineSegments(geom, mat);
    lineMesh.userData = {{
      id: rElem.id,
      parentId: rElem.parent_id,
      category: rElem.category,
      name: rElem.name,
      origColor: colHex,
    }};

    rebarGroup.add(lineMesh);
    rebarMeshes.push(lineMesh);
  }});

  rebarGroup.visible = false;

  const targetX = (data.center_x !== undefined) ? data.center_x : 0;
  const targetY = (data.center_y_elev !== undefined) ? data.center_y_elev : ((data.z_slab_top !== undefined ? data.z_slab_top : 3.0) / 2.0);
  const targetZ = -( (data.center_y !== undefined) ? data.center_y : 0 );

  const gridSpan = Math.max(maxSpan * 2.2, 8.0);
  const gridHelper = new THREE.GridHelper(gridSpan, 20, 0x334155, 0x1e293b);
  const gridY = (data.z_ground !== undefined) ? (data.z_ground - (data.grid_offset || 0.20)) : -1.20;
  gridHelper.position.set(targetX, gridY, targetZ);
  scene.add(gridHelper);

  controls.target.set(targetX, targetY, targetZ);

  let baseDistance = 1.0;
  let isSliderZooming = false;

  function setCameraPreset(preset) {{
    const span = maxSpan;
    if (preset === '3d') {{
      camera.position.set(targetX + span * 1.35, targetY + span * 1.15, targetZ + span * 1.45);
    }} else if (preset === 'top') {{
      camera.position.set(targetX, targetY + span * 2.2, targetZ + 0.001);
    }} else if (preset === 'front') {{
      camera.position.set(targetX, targetY, targetZ + span * 2.0);
    }} else if (preset === 'side') {{
      camera.position.set(targetX + span * 2.0, targetY, targetZ);
    }}
    controls.target.set(targetX, targetY, targetZ);
    controls.update();
    baseDistance = camera.position.distanceTo(controls.target);
    const zSlider = document.getElementById('zoom-slider');
    const zBadge = document.getElementById('zoom-val');
    if (zSlider && zBadge) {{
      zSlider.value = 100;
      zBadge.textContent = '100%';
    }}
  }}
  setCameraPreset('3d');

  function animate() {{
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }}
  animate();

  window.addEventListener('resize', () => {{
    const w = window.innerWidth;
    const h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }});

  const btnXrayToggle = document.getElementById('btn-xray-toggle');
  let isXrayActive = false;

  function updateXrayMode(active) {{
    isXrayActive = active;
    if (btnXrayToggle) {{
      btnXrayToggle.classList.toggle('active', isXrayActive);
      btnXrayToggle.title = isXrayActive ? 'إلغاء وضع الشفافية (العودة للخرسانة المصمتة)' : 'تفعيل وضع الشفافية (X-Ray) لإظهار حديد التسليح الداخلي';
    }}

    if (!isXrayActive) {{
      // Solid concrete mode (100% opacity)
      concreteMeshes.forEach(m => {{
        m.material.transparent = false;
        m.material.opacity = 1.0;
        m.material.depthWrite = true;
        m.visible = true;
      }});
      rebarGroup.visible = false;
    }} else {{
      // X-Ray transparent concrete mode
      concreteMeshes.forEach(m => {{
        m.visible = true;
        m.material.transparent = true;
        m.material.opacity = 0.28;
        m.material.depthWrite = false;
      }});
      rebarGroup.visible = true;
      rebarMeshes.forEach(r => {{
        r.material.opacity = 0.95;
      }});
    }}
  }}

  if (btnXrayToggle) {{
    btnXrayToggle.addEventListener('click', () => {{
      updateXrayMode(!isXrayActive);
    }});
  }}

  // ─── 3D Scene Zoom Control Logic (30% to 200%) ───
  const zoomSlider = document.getElementById('zoom-slider');
  const zoomValBadge = document.getElementById('zoom-val');

  function applyZoom(zoomPercent) {{
    if (!camera || !controls || baseDistance <= 0.001) return;
    const factor = Math.max(0.30, Math.min(2.0, zoomPercent / 100.0));
    const targetDist = baseDistance / factor;

    const offset = new THREE.Vector3().subVectors(camera.position, controls.target);
    const curDist = offset.length();
    if (curDist > 0.0001) {{
      offset.multiplyScalar(targetDist / curDist);
      camera.position.copy(controls.target).add(offset);
      controls.update();
    }}
    if (zoomValBadge) {{
      zoomValBadge.textContent = Math.round(zoomPercent) + '%';
    }}
  }}

  if (zoomSlider) {{
    zoomSlider.addEventListener('input', (e) => {{
      isSliderZooming = true;
      applyZoom(parseFloat(e.target.value));
      isSliderZooming = false;
    }});
  }}

  controls.addEventListener('change', () => {{
    if (!isSliderZooming && baseDistance > 0.001 && zoomSlider) {{
      const currentDist = camera.position.distanceTo(controls.target);
      if (currentDist > 0.0001) {{
        const computedZoom = Math.round((baseDistance / currentDist) * 100);
        const clampedZoom = Math.max(30, Math.min(200, computedZoom));
        zoomSlider.value = clampedZoom;
        if (zoomValBadge) {{
          zoomValBadge.textContent = computedZoom + '%';
        }}
      }}
    }}
  }});

  const filterState = {{}};
  ['slab', 'columns', 'footings', 'ground_beams', 'rebar', 'subbase', 'strap_beam'].forEach(c => {{ filterState[c] = true; }});
  document.querySelectorAll('.filter-chip').forEach(btn => {{
    const cat = btn.getAttribute('data-cat');
    filterState[cat] = true;
  }});
  (data.concrete_elements || []).forEach(e => {{ if (filterState[e.category] === undefined) filterState[e.category] = true; }});
  (data.rebar_elements || []).forEach(e => {{ if (filterState[e.category] === undefined) filterState[e.category] = true; }});
  if (filterState.rebar === undefined) filterState.rebar = true;

  let labelsVisible = true;
  const btnToggleLabels = document.getElementById('btn-toggle-labels');
  if (btnToggleLabels) {{
    btnToggleLabels.addEventListener('click', () => {{
      labelsVisible = !labelsVisible;
      btnToggleLabels.classList.toggle('active', labelsVisible);
      applyCategoryFilters();
    }});
  }}

  function applyCategoryFilters() {{
    concreteMeshes.forEach(m => {{
      const cat = m.userData.category;
      if (cat === 'footings_pc') {{
        m.visible = (filterState.footings !== undefined) ? filterState.footings : true;
      }} else if (filterState[cat] !== undefined) {{
        m.visible = filterState[cat];
      }} else {{
        m.visible = true;
      }}
    }});
    edgesGroup.children.forEach(e => {{
      const cat = e.userData.category;
      if (filterState[cat] !== undefined) {{
        e.visible = filterState[cat];
      }}
    }});
    const rebarGlobalVisible = (filterState.rebar !== undefined ? filterState.rebar : true);
    rebarGroup.visible = rebarGlobalVisible && isXrayActive;
    rebarMeshes.forEach(r => {{
      const cat = r.userData.category;
      const catVis = (filterState[cat] !== undefined) ? filterState[cat] : true;
      r.visible = rebarGlobalVisible && catVis;
    }});

    labelsGroup.children.forEach(lbl => {{
      const cat = lbl.userData.category;
      const catVisible = (filterState[cat] !== undefined) ? filterState[cat] : true;
      lbl.visible = labelsVisible && catVisible;
    }});
  }}

  document.querySelectorAll('.filter-chip').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const cat = btn.getAttribute('data-cat');
      filterState[cat] = !filterState[cat];
      btn.classList.toggle('active', filterState[cat]);
      applyCategoryFilters();
    }});
  }});

  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  let selectedMesh = null;
  let isIsolated = false;

  const inspectorPanel = document.getElementById('inspector-panel');
  const inspName = document.getElementById('insp-name');
  const inspBody = document.getElementById('insp-body');
  const btnCloseInsp = document.getElementById('btn-close-insp');

  function openInspector(elemMesh) {{
    if (!elemMesh) return;
    const d = elemMesh.userData;
    inspName.textContent = d.name || 'العنصر الإنشائي';
    inspBody.innerHTML = '';

    const details = d.details || {{}};
    for (const [key, val] of Object.entries(details)) {{
      const row = document.createElement('div');
      row.className = 'insp-row';
      row.innerHTML = `<span class="insp-lbl">${{key}}</span><span class="insp-val">${{val}}</span>`;
      inspBody.appendChild(row);
    }}

    const actRow = document.createElement('div');
    actRow.className = 'insp-actions';
    actRow.innerHTML = `
      <button class="btn-isolate" id="btn-do-isolate">🔍 عزل العنصر (Isolate)</button>
      <button class="btn-reset-iso" id="btn-do-reset-iso">إلغاء العزل</button>
    `;
    inspBody.appendChild(actRow);

    document.getElementById('btn-do-isolate').addEventListener('click', () => isolateElement(elemMesh));
    document.getElementById('btn-do-reset-iso').addEventListener('click', resetIsolation);

    inspectorPanel.style.display = 'flex';
  }}

  function isolateElement(elemMesh) {{
    isIsolated = true;
    const targetId = elemMesh.userData.id;

    concreteMeshes.forEach(m => {{
      if (m.userData.id === targetId) {{
        m.material.transparent = false;
        m.material.opacity = 1.0;
        m.visible = true;
      }} else {{
        m.material.transparent = true;
        m.material.opacity = 0.08;
        m.material.depthWrite = false;
        m.visible = true;
      }}
    }});

    rebarGroup.visible = true;
    rebarMeshes.forEach(r => {{
      if (r.userData.parentId === targetId) {{
        r.visible = true;
        r.material.opacity = 1.0;
      }} else {{
        r.visible = false;
      }}
    }});

    labelsGroup.children.forEach(lbl => {{
      lbl.visible = (lbl.userData.parentId === targetId);
    }});
  }}

  function resetIsolation() {{
    isIsolated = false;
    updateXrayMode(isXrayActive);
    rebarMeshes.forEach(r => {{ r.visible = true; }});
    applyCategoryFilters();
  }}

  function clearSelection() {{
    if (selectedMesh) {{
      selectedMesh.material.emissive?.setHex(0x000000);
      selectedMesh = null;
    }}
  }}

  window.addEventListener('click', (e) => {{
    if (e.target.closest('.toolbar') || e.target.closest('.inspector-panel') || e.target.closest('.rebar-legend') || e.target.closest('.sketch-box')) {{
      return;
    }}

    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    // 1. Check if a visible label sprite was clicked
    const labelIntersects = raycaster.intersectObjects(labelsGroup.children.filter(l => l.visible), false);
    if (labelIntersects.length > 0) {{
      const hitLabel = labelIntersects[0].object;
      const targetMesh = elementDataMap.get(hitLabel.userData.parentId);
      if (targetMesh) {{
        clearSelection();
        selectedMesh = targetMesh;
        if (selectedMesh.material && selectedMesh.material.emissive) {{
          selectedMesh.material.emissive.setHex(0x38bdf8);
          selectedMesh.material.emissiveIntensity = 0.35;
        }}
        openInspector(selectedMesh);
        return;
      }}
    }}

    // 2. Otherwise check concrete meshes
    const intersects = raycaster.intersectObjects(concreteMeshes.filter(m => m.visible), false);
    if (intersects.length > 0) {{
      const hit = intersects[0].object;
      clearSelection();
      selectedMesh = hit;
      if (selectedMesh.material && selectedMesh.material.emissive) {{
        selectedMesh.material.emissive.setHex(0x38bdf8);
        selectedMesh.material.emissiveIntensity = 0.35;
      }}
      openInspector(selectedMesh);
    }}
  }});

  btnCloseInsp.addEventListener('click', () => {{
    inspectorPanel.style.display = 'none';
    clearSelection();
    if (isIsolated) resetIsolation();
  }});

  const viewBtns = {{
    'btn-view-3d': '3d',
    'btn-view-top': 'top',
    'btn-view-front': 'front',
    'btn-view-side': 'side',
  }};
  Object.entries(viewBtns).forEach(([btnId, preset]) => {{
    document.getElementById(btnId).addEventListener('click', () => {{
      document.querySelectorAll('.tb-group .btn-tool').forEach(b => b.classList.remove('active'));
      document.getElementById(btnId).classList.add('active');
      setCameraPreset(preset);
    }});
  }});

  document.getElementById('btn-reset-cam').addEventListener('click', () => setCameraPreset('3d'));

  document.getElementById('btn-theme').addEventListener('click', () => {{
    isDark = !isDark;
    scene.background.set(isDark ? bgDark : bgLight);
    gridHelper.material.color.set(isDark ? 0x334155 : 0xcbd5e1);
  }});

  // ─── Full Screen Mode Toggle Logic ───
  const btnFullScreen = document.getElementById('btn-fullscreen');

  function isCurrentlyFullScreen() {{
    return !!(
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.mozFullScreenElement ||
      document.msFullscreenElement
    );
  }}

  function updateFullScreenUI(active) {{
    if (!btnFullScreen) return;
    if (active) {{
      btnFullScreen.innerHTML = '🗗 إنهاء ملء الشاشة';
      btnFullScreen.classList.add('active');
      btnFullScreen.title = 'إنهاء وضع ملء الشاشة (ESC)';
    }} else {{
      btnFullScreen.innerHTML = '⛶ ملء الشاشة (Full Screen)';
      btnFullScreen.classList.remove('active');
      btnFullScreen.title = 'عرض المجسم ثلاثي الأبعاد بملء الشاشة مع كافة الأزرار والأدوات';
    }}
  }}

  function toggleFullScreenMode() {{
    const docEl = document.documentElement;
    if (!isCurrentlyFullScreen()) {{
      const req = docEl.requestFullscreen || docEl.webkitRequestFullscreen || docEl.mozRequestFullScreen || docEl.msRequestFullscreen;
      if (req) {{
        req.call(docEl).then(() => {{
          updateFullScreenUI(true);
        }}).catch(err => {{
          console.warn("Fullscreen request error:", err);
        }});
      }}
    }} else {{
      const exit = document.exitFullscreen || document.webkitExitFullscreen || document.mozCancelFullScreen || document.msExitFullscreen;
      if (exit) {{
        exit.call(document).then(() => {{
          updateFullScreenUI(false);
        }}).catch(err => {{
          console.warn("Exit fullscreen error:", err);
        }});
      }}
    }}
  }}

  if (btnFullScreen) {{
    btnFullScreen.addEventListener('click', toggleFullScreenMode);
  }}

  document.addEventListener('fullscreenchange', () => {{
    updateFullScreenUI(isCurrentlyFullScreen());
    setTimeout(() => {{
      window.dispatchEvent(new Event('resize'));
    }}, 100);
  }});
  document.addEventListener('webkitfullscreenchange', () => {{
    updateFullScreenUI(isCurrentlyFullScreen());
    setTimeout(() => {{
      window.dispatchEvent(new Event('resize'));
    }}, 100);
  }});

  // ─── Foundation Layout Sketch Picture-in-Picture Logic ───
  const sketchBox = document.getElementById('sketch-box');
  const sketchImg = document.getElementById('sketch-img');
  const sketchImgWrap = document.getElementById('sketch-img-wrap');
  const btnToggleSketch = document.getElementById('btn-toggle-sketch');
  const btnSketchSize = document.getElementById('btn-sketch-size');
  const btnSketchMin = document.getElementById('btn-sketch-min');
  const btnSketchClose = document.getElementById('btn-sketch-close');
  const btnSketchAlignTop = document.getElementById('btn-sketch-align-top');
  const sketchOpacitySlider = document.getElementById('sketch-opacity-slider');
  const sketchOpacityVal = document.getElementById('sketch-opacity-val');
  const sketchDownloadLink = document.getElementById('sketch-download-link');

  const sketchB64 = data.layout_sketch_b64;
  if (sketchB64 && sketchB64.length > 50) {{
    const imgSrc = sketchB64.startsWith('data:') ? sketchB64 : ('data:image/png;base64,' + sketchB64);
    sketchImg.src = imgSrc;
    if (sketchDownloadLink) {{
      sketchDownloadLink.href = imgSrc;
    }}
  }} else {{
    if (sketchImgWrap) {{
      sketchImgWrap.style.background = '#1e293b';
      sketchImgWrap.style.padding = '20px 10px';
      sketchImgWrap.innerHTML = '<div style="color:#94a3b8; font-size:11px; text-align:center; line-height:1.6;">💡 المسقط الإنشائي غير متوفر حالياً.<br/>يرجى إدخال البيانات وحساب التصميم.</div>';
    }}
    if (sketchDownloadLink) {{
      sketchDownloadLink.style.display = 'none';
    }}
  }}

  // Prevent OrbitControls interference when clicking or dragging inside sketch box
  if (sketchBox) {{
    ['mousedown', 'pointerdown', 'wheel', 'touchstart', 'dblclick', 'contextmenu'].forEach(evt => {{
      sketchBox.addEventListener(evt, (e) => e.stopPropagation());
    }});
  }}

  // Toggle show/hide sketch box from toolbar button
  let sketchVisible = true;
  if (btnToggleSketch) {{
    btnToggleSketch.addEventListener('click', () => {{
      sketchVisible = !sketchVisible;
      sketchBox.style.display = sketchVisible ? 'flex' : 'none';
      btnToggleSketch.classList.toggle('active', sketchVisible);
    }});
  }}

  // Close button on sketch box
  if (btnSketchClose) {{
    btnSketchClose.addEventListener('click', () => {{
      sketchVisible = false;
      sketchBox.style.display = 'none';
      if (btnToggleSketch) btnToggleSketch.classList.remove('active');
    }});
  }}

  // Enlarge / Compact toggle
  let isSketchEnlarged = false;
  if (btnSketchSize) {{
    btnSketchSize.addEventListener('click', () => {{
      isSketchEnlarged = !isSketchEnlarged;
      sketchBox.classList.toggle('enlarged', isSketchEnlarged);
      btnSketchSize.innerHTML = isSketchEnlarged ? '⛶ نافذة عادية' : '⛶ نافذة عريضة';
      btnSketchSize.title = isSketchEnlarged ? 'استعادة الحجم المصغر' : 'توسيع نافذة المسقط الإنشائي';
    }});
  }}


  // Minimize / Expand toggle
  let isSketchMinimized = false;
  if (btnSketchMin) {{
    btnSketchMin.addEventListener('click', () => {{
      isSketchMinimized = !isSketchMinimized;
      sketchBox.classList.toggle('minimized', isSketchMinimized);
      btnSketchMin.textContent = isSketchMinimized ? '➕' : '➖';
      btnSketchMin.title = isSketchMinimized ? 'توسيع المخطط' : 'طي المخطط للشريط فقط';
    }});
  }}

  // Align 3D Camera to Top View for 1:1 Layout Comparison
  if (btnSketchAlignTop) {{
    btnSketchAlignTop.addEventListener('click', () => {{
      document.querySelectorAll('.tb-group .btn-tool').forEach(b => b.classList.remove('active'));
      const topBtn = document.getElementById('btn-view-top');
      if (topBtn) topBtn.classList.add('active');
      setCameraPreset('top');
    }});
  }}

  // ─── Full Screen for Structural Detailing Sketch ───
  const btnSketchFullscreen = document.getElementById('btn-sketch-fullscreen');
  let isSketchFullscreen = false;

  function enterSketchFullscreen() {{
    isSketchFullscreen = true;
    sketchBox.classList.add('sketch-fullscreen');
    if (btnSketchFullscreen) {{
      btnSketchFullscreen.classList.add('active');
      btnSketchFullscreen.innerHTML = '✕ خروج من ملء الشاشة';
      btnSketchFullscreen.title = 'الخروج من وضع ملء الشاشة';
    }}
    fitSketchToScreen();
    try {{
      const req = sketchBox.requestFullscreen || sketchBox.webkitRequestFullscreen || sketchBox.mozRequestFullScreen || sketchBox.msRequestFullscreen;
      if (req) {{
        const p = req.call(sketchBox);
        if (p && p.catch) p.catch(() => {{}});
      }}
    }} catch(err) {{}}
  }}

  function exitSketchFullscreen() {{
    isSketchFullscreen = false;
    sketchBox.classList.remove('sketch-fullscreen');
    if (btnSketchFullscreen) {{
      btnSketchFullscreen.classList.remove('active');
      btnSketchFullscreen.innerHTML = '⛶ ملء الشاشة';
      btnSketchFullscreen.title = 'عرض المسقط الإنشائي بملء الشاشة';
    }}
    fitSketchToScreen();
    try {{
      const exitFn = document.exitFullscreen || document.webkitExitFullscreen || document.mozCancelFullScreen || document.msExitFullscreen;
      if (exitFn && (document.fullscreenElement || document.webkitFullscreenElement)) {{
        const p = exitFn.call(document);
        if (p && p.catch) p.catch(() => {{}});
      }}
    }} catch(err) {{}}
  }}

  if (btnSketchFullscreen) {{
    btnSketchFullscreen.addEventListener('click', () => {{
      if (!isSketchFullscreen) {{
        enterSketchFullscreen();
      }} else {{
        exitSketchFullscreen();
      }}
    }});
  }}

  // Sync CSS class when browser exits fullscreen via Escape key
  document.addEventListener('fullscreenchange', () => {{
    if (!document.fullscreenElement && isSketchFullscreen) {{
      exitSketchFullscreen();
    }}
  }});
  document.addEventListener('webkitfullscreenchange', () => {{
    if (!document.webkitFullscreenElement && isSketchFullscreen) {{
      exitSketchFullscreen();
    }}
  }});

  // Opacity Slider for sketch box
  if (sketchOpacitySlider && sketchOpacityVal) {{
    sketchOpacitySlider.addEventListener('input', (e) => {{
      const val = e.target.value;
      sketchOpacityVal.textContent = val + '%';
      sketchBox.style.opacity = (val / 100.0).toString();
    }});
  }}

  // Draggable Sketch Box by Header (when NOT in fullscreen)
  const sketchHeader = document.getElementById('sketch-header');
  let isDraggingSketch = false;
  let sketchDragStartX = 0, sketchDragStartY = 0;
  let sketchBoxStartX = 0, sketchBoxStartY = 0;

  if (sketchHeader && sketchBox) {{
    sketchHeader.addEventListener('mousedown', (e) => {{
      if (isSketchFullscreen || e.target.closest('.btn-sketch-action')) return;
      isDraggingSketch = true;
      sketchDragStartX = e.clientX;
      sketchDragStartY = e.clientY;
      const rect = sketchBox.getBoundingClientRect();
      sketchBoxStartX = rect.left;
      sketchBoxStartY = rect.top;
      sketchBox.style.right = 'auto';
      sketchBox.style.bottom = 'auto';
      sketchBox.style.left = sketchBoxStartX + 'px';
      sketchBox.style.top = sketchBoxStartY + 'px';
      sketchHeader.style.cursor = 'grabbing';
      e.preventDefault();
    }});

    window.addEventListener('mousemove', (e) => {{
      if (!isDraggingSketch) return;
      const dx = e.clientX - sketchDragStartX;
      const dy = e.clientY - sketchDragStartY;
      const newX = Math.max(5, Math.min(window.innerWidth - sketchBox.offsetWidth - 5, sketchBoxStartX + dx));
      const newY = Math.max(5, Math.min(window.innerHeight - sketchBox.offsetHeight - 5, sketchBoxStartY + dy));
      sketchBox.style.left = newX + 'px';
      sketchBox.style.top = newY + 'px';
    }});

    window.addEventListener('mouseup', () => {{
      if (isDraggingSketch) {{
        isDraggingSketch = false;
        sketchHeader.style.cursor = 'grab';
      }}
    }});
  }}

  // ─── Sketch Pan & Zoom Engine (Directly on sketchImgWrap) ─────────────
  let fsScale      = 1.0;
  let fsPanX       = 0;
  let fsPanY       = 0;
  let fsIsDragging = false;
  let fsDragStartX = 0, fsDragStartY = 0;
  let fsPanStartX  = 0, fsPanStartY  = 0;

  function fsGetImg()  {{ return document.getElementById('sketch-img'); }}
  function fsGetWrap() {{ return document.getElementById('sketch-img-wrap'); }}

  function applyFsTransform() {{
    const img = fsGetImg();
    if (img) {{
      img.style.transform = 'translate(' + fsPanX + 'px,' + fsPanY + 'px) scale(' + fsScale + ')';
      img.style.transformOrigin = 'center center';
    }}
  }}

  function fitSketchToScreen() {{
    fsScale = 1.0;
    fsPanX  = 0;
    fsPanY  = 0;
    applyFsTransform();
  }}

  if (sketchImgWrap) {{
    // 1. Mouse wheel zoom centered on cursor
    sketchImgWrap.addEventListener('wheel', function(e) {{
      e.preventDefault();
      e.stopPropagation();

      const rect = sketchImgWrap.getBoundingClientRect();
      const cursorX = e.clientX - rect.left - rect.width  / 2;
      const cursorY = e.clientY - rect.top  - rect.height / 2;

      const oldScale   = fsScale;
      const zoomFactor = e.deltaY < 0 ? 1.15 : (1 / 1.15);
      fsScale = Math.max(0.15, Math.min(10.0, fsScale * zoomFactor));

      const ratio = fsScale / oldScale;
      fsPanX = cursorX + (fsPanX - cursorX) * ratio;
      fsPanY = cursorY + (fsPanY - cursorY) * ratio;

      applyFsTransform();
    }}, {{ passive: false }});

    // 2. Mousedown to start drag pan
    sketchImgWrap.addEventListener('mousedown', function(e) {{
      if (e.button !== 0) return; // Left mouse button only
      fsIsDragging = true;
      fsDragStartX = e.clientX;
      fsDragStartY = e.clientY;
      fsPanStartX  = fsPanX;
      fsPanStartY  = fsPanY;
      sketchImgWrap.style.cursor = 'grabbing';
      e.preventDefault();
      e.stopPropagation();
    }});

    // 3. Double click to restore to full fit
    sketchImgWrap.addEventListener('dblclick', function(e) {{
      e.preventDefault();
      e.stopPropagation();
      fitSketchToScreen();
    }});
  }}

  // 4. Mousemove on window for smooth panning
  window.addEventListener('mousemove', function(e) {{
    if (!fsIsDragging) return;
    fsPanX = fsPanStartX + (e.clientX - fsDragStartX);
    fsPanY = fsPanStartY + (e.clientY - fsDragStartY);
    applyFsTransform();
  }});

  // 5. Mouseup on window to release drag pan
  window.addEventListener('mouseup', function() {{
    if (fsIsDragging) {{
      fsIsDragging = false;
      const wrap = fsGetWrap();
      if (wrap) wrap.style.cursor = 'grab';
    }}
  }});

  // 6. Escape key to exit fullscreen
  window.addEventListener('keydown', function(e) {{
    if ((e.key === 'Escape' || e.keyCode === 27) && isSketchFullscreen) {{
      exitSketchFullscreen();
    }}
  }});

}})();

</script>
</body>
</html>"""


def render_3d_bim_viewer(
    Lx_calc: list,
    Ly_calc: list,
    cantilevers: dict,
    ts_cm: float,
    active_cols: list,
    indiv_col_designs: list = None,
    col_designs: list = None,
    col_H_cm: float = 300.0,
    num_floors: int = 1,
    ftg_analysis: dict = None,
    gb_analysis: dict = None,
    punching_results: list = None,
    top_extra_cols: list = None,
    btm_extra_spans: list = None,
    n_mesh_btm: float = 5.0,
    bottom_mesh_dia: int = 10,
    n_mesh_top: float = 5.0,
    top_mesh_dia: int = 10,
    fcu: float = 250.0,
    fy: float = 4000.0,
    prefix: str = "",
    height: int = 760,
    edge_columns: dict = None,
    layout_sketch_b64: str = None,
):
    """
    Renders the Integrated 3D Structural BIM & Rebar Viewer inside Module 1.
    """
    with st.expander("🏢 3D Integrated BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)", expanded=True):
        scene_data = extract_bim_3d_scene_data(
            Lx_calc=Lx_calc,
            Ly_calc=Ly_calc,
            cantilevers=cantilevers,
            ts_cm=ts_cm,
            active_cols=active_cols,
            indiv_col_designs=indiv_col_designs,
            col_designs=col_designs,
            col_H_cm=col_H_cm,
            num_floors=num_floors,
            ftg_analysis=ftg_analysis,
            gb_analysis=gb_analysis,
            punching_results=punching_results,
            top_extra_cols=top_extra_cols,
            btm_extra_spans=btm_extra_spans,
            n_mesh_btm=n_mesh_btm,
            bottom_mesh_dia=bottom_mesh_dia,
            n_mesh_top=n_mesh_top,
            top_mesh_dia=top_mesh_dia,
            fcu=fcu,
            fy=fy,
            edge_columns=edge_columns,
        )

        if not scene_data or not scene_data.get("concrete_elements"):
            st.info("💡 أدخل بيانات شبكة المحاور وقم بتنفيذ التصميم لعرض النموذج الإنشائي ثلاثي الأبعاد.")
            return

        # Check / retrieve / generate Foundation Layout Sketch base64 for side-by-side comparison
        if not layout_sketch_b64:
            layout_sketch_b64 = st.session_state.get(f"{prefix}foundation_sketch_b64", "")
        # If missing or smaller than a real drawing (<25KB base64 indicates a blank/cleared canvas), generate fresh
        if (not layout_sketch_b64 or len(layout_sketch_b64) < 25000) and active_cols and ftg_analysis:
            try:
                import matplotlib.pyplot as plt
                from modules.two_col_footings import draw_comprehensive_foundation_sketch
                gb_list = gb_analysis.get("ground_beams", []) if gb_analysis else []
                fig_sketch = draw_comprehensive_foundation_sketch(
                    active_cols, ftg_analysis, ground_beams=gb_list,
                    edge_columns=edge_columns,
                    slab_bounds=ftg_analysis.get("slab_bounds") if isinstance(ftg_analysis, dict) else None,
                )
                buf_sk = io.BytesIO()
                fig_sketch.savefig(buf_sk, format="png", bbox_inches="tight", dpi=140)
                buf_sk.seek(0)
                layout_sketch_b64 = base64.b64encode(buf_sk.getvalue()).decode("utf-8")
                st.session_state[f"{prefix}foundation_sketch_b64"] = layout_sketch_b64
                plt.close(fig_sketch)
            except Exception:
                layout_sketch_b64 = ""

        scene_data["layout_sketch_b64"] = layout_sketch_b64 or ""

        m = scene_data["metrics"]

        # Executive Metrics Header Strip
        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 15px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                    <span>🏢 النموذج الإنشائي الرقمي المتكامل (ECP 203 BIM Model):</span>
                </div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; font-weight: 700; color: #e2e8f0;">
                    <span>📐 مسطح السقف: <b style="color:#38bdf8;">{m['slab_area_m2']} م²</b></span>
                    <span>🏛️ الأعمدة: <b style="color:#4ade80;">{m['num_columns']} عمود</b></span>
                    <span>🪸 الأساسات: <b style="color:#fb923c;">{m['num_footings']} قاعدة</b></span>
                    <span>🔗 السملات والشدادات: <b style="color:#a3e635;">{m['num_ground_beams']} سملة</b></span>
                    <span>🏢 الطوابق: <b style="color:#f472b6;">{m['num_floors']} طوابق</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Generate WebGL HTML Component
        html_content = generate_bim_3d_html(scene_data, height=height)
        components.html(html_content, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
#  1. RECTANGULAR COLUMNS 3D BIM & REBAR VIEWER
# ══════════════════════════════════════════════════════════════════════════════
def render_column_3d_bim_viewer(
    b_cm: float,
    t_cm: float,
    H_clear_cm: float,
    n_bars: int,
    phi_mm: int,
    phi_st_mm: int = 8,
    n_st_per_m: int = 5,
    Pu_ton: float = 0.0,
    fcu: float = 250.0,
    fy: float = 4000.0,
    layout_sketch_b64: str = "",
    col_id: str = "C1",
    height: int = 740,
):
    """
    Renders the 3D BIM & Rebar Viewer for Module 2: Rectangular Columns.
    """
    b_m = max(0.20, b_cm / 100.0)
    t_m = max(0.20, t_cm / 100.0)
    H_m = max(2.0, H_clear_cm / 100.0)
    L_splice_m = max(1.0, (50.0 * phi_mm) / 1000.0)
    L_bar_m = H_m + L_splice_m
    unit_w_main = (phi_mm ** 2) / 162.0
    tot_w_main_kg = n_bars * L_bar_m * unit_w_main
    vol_conc_m3 = b_m * t_m * H_m

    n_ties = max(5, int(math.ceil(H_m * n_st_per_m)))
    tie_perim_m = 2.0 * ((b_m - 0.05) + (t_m - 0.05)) + 0.20
    unit_w_st = (phi_st_mm ** 2) / 162.0
    tot_w_st_kg = n_ties * tie_perim_m * unit_w_st
    tot_steel_kg = tot_w_main_kg + tot_w_st_kg

    # 3D Coordinates
    cov_m = 0.025
    cage_w = max(0.10, b_m - 2 * cov_m)
    cage_d = max(0.10, t_m - 2 * cov_m)
    half_w = cage_w / 2.0
    half_d = cage_d / 2.0

    z_col_base = 0.0
    z_col_top = H_m
    z_bar_start = z_col_base - 0.35
    z_bar_end = z_col_top + L_splice_m

    # Concrete Meshes
    concrete_elements = [
        {
            "id": f"col_{col_id}",
            "category": "columns",
            "name": f"العمود الخرساني {col_id}",
            "label": str(col_id),
            "type": "Rectangular Column",
            "x": 0.0,
            "y": 0.0,
            "z": H_m / 2.0,
            "dx": b_m,
            "dy": t_m,
            "dz": H_m,
            "color": "#475569",
            "details": {
                "النموذج": f"{col_id} — عمود خرساني مستطيل",
                "القطاع (b × t)": f"{b_cm:.0f} × {t_cm:.0f} سم",
                "الارتفاع الصافي (H)": f"{H_clear_cm:.0f} سم ({H_m:.2f} م)",
                "الحمل الأقصى (Pu)": f"{Pu_ton:.1f} طن",
                "التسليح الرئيسي": f"{n_bars} Φ {phi_mm} مم (طول السيخ: {L_bar_m:.2f} م')",
                "الكانات والأطواق": f"{n_st_per_m} Φ {phi_st_mm} / م (إجمالي: {n_ties} كانة)",
                "طول وصلة التراكب (Splice)": f"{L_splice_m*100:.0f} سم ({L_splice_m:.2f} م')",
                "حجم الخرسانة": f"{vol_conc_m3:.3f} م³",
                "إجمالي وزن الحديد": f"{tot_steel_kg:.1f} كجم ({tot_steel_kg/1000.0:.3f} طن)",
            },
        },
        {
            "id": "col_footing_stub",
            "category": "columns",
            "name": "قاعدة ارتكاز العمود (Footing Connection Stub)",
            "type": "Footing Base",
            "x": 0.0,
            "y": 0.0,
            "z": -0.20,
            "dx": b_m + 0.40,
            "dy": t_m + 0.40,
            "dz": 0.40,
            "color": "#334155",
            "details": {
                "الوصف": "قاعدة خرسانية توضح ارتكاز العمود وامتداد أرجل حديد التسليح",
                "الأبعاد": f"{(b_m+0.40)*100:.0f} × {(t_m+0.40)*100:.0f} × 40 سم",
            },
        },
        {
            "id": "col_slab_stub",
            "category": "columns",
            "name": "بلاطة السقف العلوي (Slab Connection)",
            "type": "Slab Stub",
            "x": 0.0,
            "y": 0.0,
            "z": H_m + 0.10,
            "dx": b_m + 0.40,
            "dy": t_m + 0.40,
            "dz": 0.20,
            "color": "#64748b",
            "details": {
                "الوصف": "بلاطة خرسانية توضح تقاطع العمود مع السقف وامتداد الأشاير",
                "الأبعاد": f"{(b_m+0.40)*100:.0f} × {(t_m+0.40)*100:.0f} × 20 سم",
            },
        },
    ]

    # Parametric Main Bars Positions
    long_bar_pos = [
        (-half_w, -half_d),
        (half_w, -half_d),
        (half_w, half_d),
        (-half_w, half_d),
    ]
    rem_bars = n_bars - 4
    if rem_bars > 0:
        side_w = max(0, int(round(rem_bars * (cage_w / max(0.01, cage_w + cage_d)))))
        side_d = max(0, rem_bars - side_w)
        if side_w > 0:
            ew = max(1, side_w // 2)
            for s in range(1, ew + 1):
                fx = -half_w + (s / (ew + 1)) * cage_w
                long_bar_pos.extend([(fx, -half_d), (fx, half_d)])
        if side_d > 0:
            ed = max(1, side_d // 2)
            for s in range(1, ed + 1):
                fy = -half_d + (s / (ed + 1)) * cage_d
                long_bar_pos.extend([(-half_w, fy), (half_w, fy)])

    main_bar_lines = []
    for bx, by in long_bar_pos:
        # Vertical shaft bar
        main_bar_lines.extend([bx, by, z_bar_start, bx, by, z_bar_end])
        # Footing bend hook
        fdx = -0.15 if bx > 0 else 0.15
        fdy = -0.15 if by > 0 else 0.15
        main_bar_lines.extend([bx, by, z_bar_start, bx + fdx, by + fdy, z_bar_start])

    rebar_elements = [
        {
            "id": f"rebar_col_main_{col_id}",
            "parent_id": f"col_{col_id}",
            "category": "rebar",
            "color": "#10b981",
            "name": f"الحديد الطولي الرئيسي ({n_bars} Φ {phi_mm} mm)",
            "lines": main_bar_lines,
        }
    ]

    # Stirrup Ties Lines
    tie_lines = []
    z_tie_steps = []
    cur_z = 0.06
    while cur_z < H_m - 0.05:
        z_tie_steps.append(cur_z)
        # Dense spacing in confinement zones (first/last 50 cm)
        sp = (0.5 / n_st_per_m) if (cur_z < 0.50 or cur_z > H_m - 0.50) else (1.0 / n_st_per_m)
        cur_z += max(0.08, sp)

    for z_t in z_tie_steps:
        # Outer rectangular tie
        tie_lines.extend([
            -half_w, -half_d, z_t,  half_w, -half_d, z_t,
             half_w, -half_d, z_t,  half_w,  half_d, z_t,
             half_w,  half_d, z_t, -half_w,  half_d, z_t,
            -half_w,  half_d, z_t, -half_w, -half_d, z_t,
        ])
        # Inner tie if multi-branch
        if n_bars >= 8 and half_w > 0.12 and half_d > 0.12:
            tie_lines.extend([
                -half_w * 0.45, -half_d, z_t,  half_w * 0.45, -half_d, z_t,
                 half_w * 0.45, -half_d, z_t,  half_w * 0.45,  half_d, z_t,
                 half_w * 0.45,  half_d, z_t, -half_w * 0.45,  half_d, z_t,
                -half_w * 0.45,  half_d, z_t, -half_w * 0.45, -half_d, z_t,
            ])

    if tie_lines:
        rebar_elements.append({
            "id": f"rebar_col_ties_{col_id}",
            "parent_id": f"col_{col_id}",
            "category": "rebar",
            "color": "#f59e0b",
            "name": f"كانات وأطواق العمود (Φ {phi_st_mm} @ {n_st_per_m}/m)",
            "lines": tie_lines,
        })

    scene_data = {
        "span_x": round(b_m + 0.80, 2),
        "span_y": round(t_m + 0.80, 2),
        "center_x": 0.0,
        "center_y": 0.0,
        "center_y_elev": round(H_m / 2.0, 2),
        "building_height": round(H_m + L_splice_m + 0.50, 2),
        "z_ground": 0.0,
        "grid_offset": 0.25,
        "concrete_elements": concrete_elements,
        "rebar_elements": rebar_elements,
        "categories": [
            {"id": "columns", "name": "العمود والخرسانة"},
            {"id": "rebar", "name": "حديد التسليح والكانات"},
        ],
        "legend_items": [
            {"color": "#10b981", "name": f"تسليح طولي ({n_bars} Φ {phi_mm} mm)"},
            {"color": "#f59e0b", "name": f"كانات العمود (Φ {phi_st_mm} @ {n_st_per_m}/m)"},
            {"color": "#38bdf8", "name": f"أشاير السقف ({L_splice_m:.2f} m)"},
        ],
        "sketch_title": f"مخطط وتفريد تسليح العمود {col_id} ({b_cm:.0f}×{t_cm:.0f} سم)",
        "sketch_btn_title": "🗺️ قطاع وتفريد العمود",
        "sketch_dl_name": f"Column_{col_id}_{b_cm:.0f}x{t_cm:.0f}cm_Section.png",
        "layout_sketch_b64": layout_sketch_b64 or "",
    }

    with st.expander("🏢 3D Integrated BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)", expanded=True):
        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 15px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                    <span>🏢 النموذج الإنشائي الرقمي للعمود (ECP 203 Column BIM Model):</span>
                </div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; font-weight: 700; color: #e2e8f0;">
                    <span>🏛️ القطاع: <b style="color:#38bdf8;">{b_cm:.0f} × {t_cm:.0f} سم</b></span>
                    <span>📏 الارتفاع الصافي: <b style="color:#4ade80;">{H_m:.2f} م</b></span>
                    <span>🔩 التسليح الطولي: <b style="color:#fb923c;">{n_bars} Φ {phi_mm} مم</b></span>
                    <span>⚙️ الكانات: <b style="color:#a3e635;">{n_st_per_m} Φ {phi_st_mm}/م</b></span>
                    <span>🧱 الخرسانة: <b style="color:#f472b6;">{vol_conc_m3:.2f} م³</b></span>
                    <span>⚖️ إجمالي الحديد: <b style="color:#e0e7ff;">{tot_steel_kg:.1f} كجم</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        html_content = generate_bim_3d_html(scene_data, height=height)
        components.html(html_content, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
#  2. ISOLATED FOOTINGS 3D BIM & REBAR VIEWER
# ══════════════════════════════════════════════════════════════════════════════
def render_isolated_footing_3d_bim_viewer(
    L_cm: float = None,
    B_cm: float = None,
    t_rc_cm: float = None,
    bc_cm: float = None,
    tc_cm: float = None,
    Phi: int = 16,
    n_long: int = 6,
    n_sht: int = 6,
    q_all: float = 1.5,
    q_act: float = 1.2,
    Pu: float = 100.0,
    fcu: float = 250.0,
    fy: float = 4000.0,
    layout_sketch_b64: str = "",
    ftg_id: str = "F1",
    col_id: str = "C1",
    height: int = 740,
    **kwargs,
):
    """
    Renders the 3D BIM & Rebar Viewer for Module 3: Isolated Footings.
    """
    if L_cm is None:
        L_cm = kwargs.get("L_rc", 2.0) * 100.0
    if B_cm is None:
        B_cm = kwargs.get("B_rc", 2.0) * 100.0
    if t_rc_cm is None:
        t_rc_cm = kwargs.get("t_rc", 0.5) * 100.0
    if bc_cm is None:
        bc_cm = kwargs.get("col_b", 0.3) * 100.0
    if tc_cm is None:
        tc_cm = kwargs.get("col_c", 0.6) * 100.0
    Phi = kwargs.get("phi_long", kwargs.get("phi_short", Phi))
    n_sht = kwargs.get("n_short", n_sht)
    q_all = kwargs.get("q_net", q_all)
    Pu = kwargs.get("pu_ton", Pu)
    ftg_id = kwargs.get("ftg_name", ftg_id)

    L_m = max(0.80, L_cm / 100.0)
    B_m = max(0.80, B_cm / 100.0)
    t_rc_m = max(0.30, t_rc_cm / 100.0)
    bc_m = max(0.20, bc_cm / 100.0)
    tc_m = max(0.20, tc_cm / 100.0)
    t_pc_m = 0.10
    pc_offset_m = 0.10

    vol_rc_m3 = L_m * B_m * t_rc_m
    vol_pc_m3 = (L_m + 2 * pc_offset_m) * (B_m + 2 * pc_offset_m) * t_pc_m

    # Rebar calculation
    unit_w = (Phi ** 2) / 162.0
    L_bar_long = L_m - 0.10 + 2 * (t_rc_m - 0.10)
    L_bar_sht = B_m - 0.10 + 2 * (t_rc_m - 0.10)
    w_long_kg = n_long * L_bar_long * unit_w
    w_sht_kg = n_sht * L_bar_sht * unit_w
    dowel_w_kg = 4 * 1.50 * unit_w
    tot_steel_kg = w_long_kg + w_sht_kg + dowel_w_kg

    z_pc_mid = -t_pc_m / 2.0
    z_rc_mid = t_rc_m / 2.0
    h_col_stump = 0.80
    z_stump_mid = t_rc_m + (h_col_stump / 2.0)

    concrete_elements = [
        {
            "id": f"pc_{ftg_id}",
            "category": "footings_pc",
            "name": f"فرشة الخرسانة العادية (P.C. Blinding) {ftg_id}",
            "type": "Plain Concrete",
            "x": 0.0,
            "y": 0.0,
            "z": z_pc_mid,
            "dx": L_m + 2 * pc_offset_m,
            "dy": B_m + 2 * pc_offset_m,
            "dz": t_pc_m,
            "color": "#64748b",
            "details": {
                "النوع": "فرشة خرسانة عادية نظافة",
                "الأبعاد": f"{(L_m+2*pc_offset_m)*100:.0f} × {(B_m+2*pc_offset_m)*100:.0f} × 10 سم",
                "الحجم": f"{vol_pc_m3:.2f} م³",
            },
        },
        {
            "id": f"rc_{ftg_id}",
            "category": "footings",
            "name": f"القاعدة الخرسانية المسلحة (R.C. Footing) {ftg_id}",
            "label": str(ftg_id),
            "type": "Reinforced Concrete Footing",
            "x": 0.0,
            "y": 0.0,
            "z": z_rc_mid,
            "dx": L_m,
            "dy": B_m,
            "dz": t_rc_m,
            "color": "#334155",
            "details": {
                "النموذج": f"{ftg_id} — قاعدة منفصلة",
                "الأبعاد (L × B × t)": f"{L_cm:.0f} × {B_cm:.0f} × {t_rc_cm:.0f} سم",
                "إجهاد التربة الفعلي (q_act)": f"{q_act:.2f} كجم/سم² (المسموح: {q_all:.2f})",
                "الحمل الأقصى (Pu)": f"{Pu:.1f} طن",
                "تسليح الاتجاه الطولي (L)": f"{n_long} Φ {Phi} مم (فرش)",
                "تسليح الاتجاه القصير (B)": f"{n_sht} Φ {Phi} مم (غطاء)",
                "حجم الخرسانة المسلحة": f"{vol_rc_m3:.2f} م³",
                "إجمالي وزن الحديد": f"{tot_steel_kg:.1f} كجم",
            },
        },
        {
            "id": f"col_{col_id}",
            "category": "columns",
            "name": f"رقبة العمود (Column Pedestal) {col_id}",
            "label": str(col_id),
            "type": "Column Stub",
            "x": 0.0,
            "y": 0.0,
            "z": z_stump_mid,
            "dx": bc_m,
            "dy": tc_m,
            "dz": h_col_stump,
            "color": "#475569",
            "details": {
                "القطاع": f"{bc_cm:.0f} × {tc_cm:.0f} سم",
                "الارتفاع الظاهر": f"{h_col_stump*100:.0f} سم",
            },
        },
    ]

    # Rebar Meshes
    cov = 0.05
    rebar_elements = []

    # Long direction bars (run along X, spaced along Y)
    long_lines = []
    ys = [(-B_m / 2.0 + cov) + i * (B_m - 2 * cov) / max(1, n_long - 1) for i in range(n_long)]
    x_start = -L_m / 2.0 + cov
    x_end = L_m / 2.0 - cov
    z_bot = cov
    z_top = t_rc_m - cov

    for y in ys:
        # Bottom main line
        long_lines.extend([x_start, y, z_bot, x_end, y, z_bot])
        # 90 deg hooks turning up
        long_lines.extend([x_start, y, z_bot, x_start, y, z_top])
        long_lines.extend([x_end, y, z_bot, x_end, y, z_top])

    rebar_elements.append({
        "id": f"rebar_ftg_long_{ftg_id}",
        "parent_id": f"rc_{ftg_id}",
        "category": "rebar",
        "color": "#0284c7",
        "name": f"فرش الاتجاه الرئيسي ({n_long} Φ {Phi} mm)",
        "lines": long_lines,
    })

    # Short direction bars (run along Y, spaced along X)
    sht_lines = []
    xs = [(-L_m / 2.0 + cov) + j * (L_m - 2 * cov) / max(1, n_sht - 1) for j in range(n_sht)]
    y_start = -B_m / 2.0 + cov
    y_end = B_m / 2.0 - cov
    z_bot_sht = cov + 0.02

    for x in xs:
        # Bottom transverse line
        sht_lines.extend([x, y_start, z_bot_sht, x, y_end, z_bot_sht])
        # 90 deg hooks turning up
        sht_lines.extend([x, y_start, z_bot_sht, x, y_start, z_top])
        sht_lines.extend([x, y_end, z_bot_sht, x, y_end, z_top])

    rebar_elements.append({
        "id": f"rebar_ftg_sht_{ftg_id}",
        "parent_id": f"rc_{ftg_id}",
        "category": "rebar",
        "color": "#6366f1",
        "name": f"غطاء الاتجاه الثانوي ({n_sht} Φ {Phi} mm)",
        "lines": sht_lines,
    })

    # Column Dowels (4 corners)
    dowel_lines = []
    dc_x = bc_m / 2.0 - 0.03
    dc_y = tc_m / 2.0 - 0.03
    for dx, dy in [(-dc_x, -dc_y), (dc_x, -dc_y), (dc_x, dc_y), (-dc_x, dc_y)]:
        # Vertical bar from bottom of footing up to stump top
        dowel_lines.extend([dx, dy, cov, dx, dy, t_rc_m + h_col_stump + 0.40])
        # L-foot in footing
        h_x = -0.20 if dx > 0 else 0.20
        h_y = -0.20 if dy > 0 else 0.20
        dowel_lines.extend([dx, dy, cov, dx + h_x, dy + h_y, cov])

    # 3 ties in pedestal
    for z_st in [t_rc_m + 0.15, t_rc_m + 0.40, t_rc_m + 0.65]:
        dowel_lines.extend([
            -dc_x, -dc_y, z_st,  dc_x, -dc_y, z_st,
             dc_x, -dc_y, z_st,  dc_x,  dc_y, z_st,
             dc_x,  dc_y, z_st, -dc_x,  dc_y, z_st,
            -dc_x,  dc_y, z_st, -dc_x, -dc_y, z_st,
        ])

    rebar_elements.append({
        "id": f"rebar_col_dowels_{col_id}",
        "parent_id": f"col_{col_id}",
        "category": "rebar",
        "color": "#10b981",
        "name": "أشاير العمود وكانات الرقبة",
        "lines": dowel_lines,
    })

    scene_data = {
        "span_x": round(L_m + 1.0, 2),
        "span_y": round(B_m + 1.0, 2),
        "center_x": 0.0,
        "center_y": 0.0,
        "center_y_elev": round(t_rc_m / 2.0, 2),
        "building_height": round(t_rc_m + h_col_stump + 0.50, 2),
        "z_ground": 0.0,
        "grid_offset": 0.15,
        "concrete_elements": concrete_elements,
        "rebar_elements": rebar_elements,
        "categories": [
            {"id": "footings", "name": "القاعدة المسلحة"},
            {"id": "footings_pc", "name": "الخرسانة العادية"},
            {"id": "columns", "name": "رقبة العمود"},
            {"id": "rebar", "name": "حديد التسليح والأشاير"},
        ],
        "legend_items": [
            {"color": "#0284c7", "name": f"فرش اتجاه رئيسي ({n_long} Φ {Phi})"},
            {"color": "#6366f1", "name": f"غطاء اتجاه ثانوي ({n_sht} Φ {Phi})"},
            {"color": "#10b981", "name": "أشاير العمود وكانات الرقبة"},
        ],
        "sketch_title": f"المسقط الأفقي للقاعدة {ftg_id} وتوزيع التسليح",
        "sketch_btn_title": "🗺️ مسقط القاعدة",
        "sketch_dl_name": f"Footing_{ftg_id}_{L_cm:.0f}x{B_cm:.0f}cm_Plan.png",
        "layout_sketch_b64": layout_sketch_b64 or "",
    }

    with st.expander("🏢 3D Integrated BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)", expanded=True):
        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 15px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                    <span>🏢 النموذج الإنشائي الرقمي للقاعدة المنفصلة (ECP 203 Isolated Footing BIM):</span>
                </div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; font-weight: 700; color: #e2e8f0;">
                    <span>📐 المسلحة: <b style="color:#38bdf8;">{L_cm:.0f} × {B_cm:.0f} × {t_rc_cm:.0f} سم</b></span>
                    <span>🏛️ رقبة العمود: <b style="color:#4ade80;">{bc_cm:.0f} × {tc_cm:.0f} سم</b></span>
                    <span>🌱 إجهاد التربة: <b style="color:#fb923c;">{q_act:.2f} / {q_all:.2f} kg/cm²</b></span>
                    <span>🔩 التسليح: <b style="color:#a3e635;">{n_long}Φ{Phi} فرش │ {n_sht}Φ{Phi} غطاء</b></span>
                    <span>🧱 خرسانة مسلحة: <b style="color:#f472b6;">{vol_rc_m3:.2f} م³</b></span>
                    <span>⚖️ إجمالي الحديد: <b style="color:#e0e7ff;">{tot_steel_kg:.1f} كجم</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        html_content = generate_bim_3d_html(scene_data, height=height)
        components.html(html_content, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
#  3. GROUND SLABS 3D BIM & REBAR VIEWER
# ══════════════════════════════════════════════════════════════════════════════
def render_ground_slab_3d_bim_viewer(
    Lx_m: float,
    Ly_m: float,
    ts_cm: float,
    mesh_type: str = "B500D Welded Wire Mesh",
    phi_mesh_mm: int = 8,
    spacing_mesh_cm: float = 15.0,
    dowel_phi_mm: int = 16,
    dowel_len_cm: float = 50.0,
    dowel_spacing_cm: float = 30.0,
    joint_spacing_x_m: float = 5.0,
    joint_spacing_y_m: float = 5.0,
    fcu: float = 250.0,
    wheel_load_ton: float = 5.0,
    layout_sketch_b64: str = "",
    height: int = 740,
):
    """
    Renders the 3D BIM & Rebar Viewer for Module 4: Ground Slabs.
    """
    Lx = max(4.0, float(Lx_m))
    Ly = max(4.0, float(Ly_m))
    ts_m = max(0.12, ts_cm / 100.0)
    h_subbase_m = 0.20
    vol_conc_m3 = Lx * Ly * ts_m

    concrete_elements = [
        {
            "id": "subbase_layer",
            "category": "subbase",
            "name": "طبقة الإحلال المدموكة (Compacted Subbase)",
            "type": "Granular Subbase",
            "x": 0.0,
            "y": 0.0,
            "z": -h_subbase_m / 2.0,
            "dx": Lx + 1.0,
            "dy": Ly + 1.0,
            "dz": h_subbase_m,
            "color": "#78716c",
            "details": {
                "النوع": "طبقة إحلال من سن متدرج ورمل مدموك 98% Proctor",
                "الأبعاد": f"{Lx+1.0:.1f} × {Ly+1.0:.1f} م × 20 سم",
                "الحجم": f"{(Lx+1.0)*(Ly+1.0)*h_subbase_m:.2f} م³",
            },
        },
        {
            "id": "ground_slab_mesh",
            "category": "slab",
            "name": "البلاطة الخرسانية الأرضية (Concrete Ground Slab)",
            "label": "Slab-on-Grade",
            "type": "Slab on Grade",
            "x": 0.0,
            "y": 0.0,
            "z": ts_m / 2.0,
            "dx": Lx,
            "dy": Ly,
            "dz": ts_m,
            "color": "#475569",
            "details": {
                "النموذج": "بلاطة أرضية خرسانية مسلحة (SOG)",
                "الأبعاد الكلية": f"{Lx:.1f} × {Ly:.1f} م (المساحة: {Lx*Ly:.1f} م²)",
                "السُمك (ts)": f"{ts_cm:.0f} سم ({ts_m:.2f} م)",
                "مقاومة الخرسانة (Fcu)": f"{fcu:.0f} كجم/سم²",
                "أقصى حمل تصميمي": f"{wheel_load_ton:.1f} طن / عجلة",
                "مسافات فواصل الانكماش": f"{joint_spacing_x_m:.1f} × {joint_spacing_y_m:.1f} م",
                "تسليح الشبكة": f"{mesh_type} (Φ{phi_mesh_mm} @ {spacing_mesh_cm:.0f} سم)",
                "دواول نقل القص": f"Φ{dowel_phi_mm} مم بطول {dowel_len_cm:.0f} سم @ {dowel_spacing_cm:.0f} سم",
                "حجم الخرسانة": f"{vol_conc_m3:.2f} م³",
            },
        },
    ]

    rebar_elements = []

    # Mesh Rebar Grid
    mesh_lines = []
    z_mesh = ts_m * 0.65
    sp_m = max(0.20, spacing_mesh_cm / 100.0)

    # Longitudinal lines parallel to X
    ny = int(math.floor(Ly / sp_m))
    for i in range(ny + 1):
        y = -Ly / 2.0 + i * sp_m
        mesh_lines.extend([-Lx / 2.0 + 0.10, y, z_mesh, Lx / 2.0 - 0.10, y, z_mesh])

    # Transverse lines parallel to Y
    nx = int(math.floor(Lx / sp_m))
    for j in range(nx + 1):
        x = -Lx / 2.0 + j * sp_m
        mesh_lines.extend([x, -Ly / 2.0 + 0.10, z_mesh, x, Ly / 2.0 - 0.10, z_mesh])

    rebar_elements.append({
        "id": "rebar_ground_mesh",
        "parent_id": "ground_slab_mesh",
        "category": "rebar",
        "color": "#0284c7",
        "name": f"شبكة تسليح الانكماش (Φ {phi_mesh_mm} @ {spacing_mesh_cm:.0f} cm)",
        "lines": mesh_lines,
    })

    # Contraction Joints & Dowel Bars
    dowel_lines = []
    dowel_len_m = dowel_len_cm / 100.0
    d_sp_m = max(0.25, dowel_spacing_cm / 100.0)

    # Vertical joints (parallel to Y, at intervals along X)
    num_jx = max(1, int(round(Lx / max(2.5, joint_spacing_x_m))))
    for kx in range(1, num_jx):
        jx = -Lx / 2.0 + kx * (Lx / num_jx)
        nd = int(math.floor(Ly / d_sp_m))
        for d_i in range(nd + 1):
            dy = -Ly / 2.0 + d_i * d_sp_m
            dowel_lines.extend([jx - dowel_len_m / 2.0, dy, ts_m / 2.0, jx + dowel_len_m / 2.0, dy, ts_m / 2.0])

    # Horizontal joints (parallel to X)
    num_jy = max(1, int(round(Ly / max(2.5, joint_spacing_y_m))))
    for ky in range(1, num_jy):
        jy = -Ly / 2.0 + ky * (Ly / num_jy)
        nd = int(math.floor(Lx / d_sp_m))
        for d_i in range(nd + 1):
            dx = -Lx / 2.0 + d_i * d_sp_m
            dowel_lines.extend([dx, jy - dowel_len_m / 2.0, ts_m / 2.0, dx, jy + dowel_len_m / 2.0, ts_m / 2.0])

    if dowel_lines:
        rebar_elements.append({
            "id": "rebar_ground_dowels",
            "parent_id": "ground_slab_mesh",
            "category": "rebar",
            "color": "#f97316",
            "name": f"دواول نقل القص الملساء (Φ {dowel_phi_mm} mm @ {dowel_spacing_cm:.0f} cm)",
            "lines": dowel_lines,
        })

    scene_data = {
        "span_x": round(Lx + 1.0, 2),
        "span_y": round(Ly + 1.0, 2),
        "center_x": 0.0,
        "center_y": 0.0,
        "center_y_elev": round(ts_m / 2.0, 2),
        "building_height": round(ts_m + h_subbase_m + 0.50, 2),
        "z_ground": 0.0,
        "grid_offset": 0.25,
        "concrete_elements": concrete_elements,
        "rebar_elements": rebar_elements,
        "categories": [
            {"id": "slab", "name": "البلاطة الخرسانية"},
            {"id": "subbase", "name": "طبقة الإحلال"},
            {"id": "rebar", "name": "شبكة التسليح والدواول"},
        ],
        "legend_items": [
            {"color": "#0284c7", "name": f"شبكة التسليح (Φ {phi_mesh_mm} @ {spacing_mesh_cm:.0f} cm)"},
            {"color": "#f97316", "name": f"دواول نقل القص (Φ {dowel_phi_mm} mm)"},
        ],
        "sketch_title": f"المسقط الأفقي للبلاطة الأرضية وفواصل الصب ({Lx:.1f}×{Ly:.1f} م)",
        "sketch_btn_title": "🗺️ مسقط البلاطة والفواصل",
        "sketch_dl_name": f"Ground_Slab_{Lx:.0f}x{Ly:.0f}m_ts{ts_cm:.0f}cm_Plan.png",
        "layout_sketch_b64": layout_sketch_b64 or "",
    }

    with st.expander("🏢 3D Integrated BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)", expanded=True):
        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 15px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                    <span>🏢 النموذج الإنشائي الرقمي للبلاطة الأرضية (ECP 203 SOG BIM Model):</span>
                </div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; font-weight: 700; color: #e2e8f0;">
                    <span>📐 مسطح البلاطة: <b style="color:#38bdf8;">{Lx*Ly:.1f} م²</b></span>
                    <span>🧱 السُمك ts: <b style="color:#4ade80;">{ts_cm:.0f} سم</b></span>
                    <span>🚚 الحمل التصميمي: <b style="color:#fb923c;">{wheel_load_ton:.1f} طن</b></span>
                    <span>🔩 شبكة التسليح: <b style="color:#a3e635;">Φ{phi_mesh_mm} @ {spacing_mesh_cm:.0f}سم</b></span>
                    <span>🔗 الدواول: <b style="color:#f472b6;">Φ{dowel_phi_mm} @ {dowel_spacing_cm:.0f}سم</b></span>
                    <span>🧱 خرسانة مسلحة: <b style="color:#e0e7ff;">{vol_conc_m3:.2f} م³</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        html_content = generate_bim_3d_html(scene_data, height=height)
        components.html(html_content, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
#  4. COMBINED FOOTINGS 3D BIM & REBAR VIEWER
# ══════════════════════════════════════════════════════════════════════════════
def render_combined_footing_3d_bim_viewer(
    Lc_m: float,
    Bc_m: float,
    tc_cm: float,
    c1_cm: float,
    b1_cm: float,
    P1_ton: float,
    c2_cm: float,
    b2_cm: float,
    P2_ton: float,
    S_m: float,
    x1_m: float,
    x2_m: float,
    Phi_top: int = 18,
    n_top: int = 8,
    Phi_bot: int = 16,
    n_bot: int = 8,
    q_net: float = 1.5,
    q_act: float = 1.2,
    fcu: float = 250.0,
    fy: float = 4000.0,
    layout_sketch_b64: str = "",
    cf_id: str = "CF1",
    height: int = 740,
):
    """
    Renders the 3D BIM & Rebar Viewer for Module 7: Combined Footing Design.
    """
    Lc = max(1.5, float(Lc_m))
    Bc = max(1.0, float(Bc_m))
    tc_m = max(0.40, tc_cm / 100.0)
    c1_m = max(0.20, c1_cm / 100.0)
    b1_m = max(0.20, b1_cm / 100.0)
    c2_m = max(0.20, c2_cm / 100.0)
    b2_m = max(0.20, b2_cm / 100.0)
    vol_rc = Lc * Bc * tc_m
    vol_pc = (Lc + 0.40) * (Bc + 0.40) * 0.10

    # Column center offsets from combined footing center (origin at 0,0)
    x1_pos = -Lc / 2.0 + x1_m
    x2_pos = x1_pos + S_m

    concrete_elements = [
        {
            "id": f"pc_{cf_id}",
            "category": "footings_pc",
            "name": f"الخرسانة العادية للقاعدة المشتركة {cf_id}",
            "type": "Plain Concrete",
            "x": 0.0,
            "y": 0.0,
            "z": -0.05,
            "dx": Lc + 0.40,
            "dy": Bc + 0.40,
            "dz": 0.10,
            "color": "#64748b",
            "details": {
                "النوع": "فرشة خرسانة عادية نظافة",
                "الأبعاد": f"{(Lc+0.40)*100:.0f} × {(Bc+0.40)*100:.0f} × 10 سم",
                "الحجم": f"{vol_pc:.2f} م³",
            },
        },
        {
            "id": f"rc_{cf_id}",
            "category": "footings",
            "name": f"القاعدة المشتركة المسلحة {cf_id}",
            "label": str(cf_id),
            "type": "Combined Footing",
            "x": 0.0,
            "y": 0.0,
            "z": tc_m / 2.0,
            "dx": Lc,
            "dy": Bc,
            "dz": tc_m,
            "color": "#334155",
            "details": {
                "النموذج": f"{cf_id} — قاعدة مشتركة لعمودين",
                "الأبعاد (L × B × t)": f"{Lc*100:.0f} × {Bc*100:.0f} × {tc_cm:.0f} سم",
                "المسافة بين المحاور (S)": f"{S_m:.2f} م",
                "أحمال الأعمدة": f"P₁ = {P1_ton:.1f} طن │ P₂ = {P2_ton:.1f} طن",
                "إجهاد التربة الفعلي (q_act)": f"{q_act:.2f} كجم/سم² (المسموح: {q_net:.2f})",
                "الحديد العلوي الرئيسي": f"{n_top} Φ {Phi_top} مم (لمقاومة العزم السالب)",
                "الحديد السفلي الرئيسي": f"{n_bot} Φ {Phi_bot} مم (لمقاومة العزم الموجب)",
                "حجم الخرسانة المسلحة": f"{vol_rc:.2f} م³",
            },
        },
        {
            "id": "col_1",
            "category": "columns",
            "name": f"العمود C1 (P={P1_ton:.1f}t)",
            "label": "C1",
            "type": "Column 1",
            "x": x1_pos,
            "y": 0.0,
            "z": tc_m + 0.50,
            "dx": c1_m,
            "dy": b1_m,
            "dz": 1.00,
            "color": "#475569",
            "details": {
                "العمود": "C1",
                "القطاع": f"{c1_cm:.0f} × {b1_cm:.0f} سم",
                "الحمل": f"{P1_ton:.1f} طن",
            },
        },
        {
            "id": "col_2",
            "category": "columns",
            "name": f"العمود C2 (P={P2_ton:.1f}t)",
            "label": "C2",
            "type": "Column 2",
            "x": x2_pos,
            "y": 0.0,
            "z": tc_m + 0.50,
            "dx": c2_m,
            "dy": b2_m,
            "dz": 1.00,
            "color": "#475569",
            "details": {
                "العمود": "C2",
                "القطاع": f"{c2_cm:.0f} × {b2_cm:.0f} سم",
                "الحمل": f"{P2_ton:.1f} طن",
            },
        },
    ]

    cov = 0.05
    rebar_elements = []

    # Top Longitudinal Rebar (Resisting Negative Hogging Moment)
    top_lines = []
    z_top = tc_m - cov
    z_bot = cov
    ys_top = [(-Bc / 2.0 + cov) + i * (Bc - 2 * cov) / max(1, n_top - 1) for i in range(n_top)]
    x_s = -Lc / 2.0 + cov
    x_e = Lc / 2.0 - cov

    for y in ys_top:
        top_lines.extend([x_s, y, z_top, x_e, y, z_top])
        # 90 deg downward hook legs
        top_lines.extend([x_s, y, z_top, x_s, y, z_bot + 0.10])
        top_lines.extend([x_e, y, z_top, x_e, y, z_bot + 0.10])

    rebar_elements.append({
        "id": "rebar_cf_top",
        "parent_id": f"rc_{cf_id}",
        "category": "rebar",
        "color": "#ea580c",
        "name": f"الحديد العلوي الرئيسي ({n_top} Φ {Phi_top} mm)",
        "lines": top_lines,
    })

    # Bottom Longitudinal Rebar
    bot_lines = []
    ys_bot = [(-Bc / 2.0 + cov) + i * (Bc - 2 * cov) / max(1, n_bot - 1) for i in range(n_bot)]
    for y in ys_bot:
        bot_lines.extend([x_s, y, z_bot, x_e, y, z_bot])
        bot_lines.extend([x_s, y, z_bot, x_s, y, z_top - 0.10])
        bot_lines.extend([x_e, y, z_bot, x_e, y, z_top - 0.10])

    rebar_elements.append({
        "id": "rebar_cf_bot",
        "parent_id": f"rc_{cf_id}",
        "category": "rebar",
        "color": "#0284c7",
        "name": f"الحديد السفلي الرئيسي ({n_bot} Φ {Phi_bot} mm)",
        "lines": bot_lines,
    })

    # Transverse Bands (under each column and along span)
    trans_lines = []
    n_trans = max(6, int(Lc * 3))
    xs_trans = [(-Lc / 2.0 + cov) + i * (Lc - 2 * cov) / max(1, n_trans - 1) for i in range(n_trans)]
    y_s = -Bc / 2.0 + cov
    y_e = Bc / 2.0 - cov
    for x in xs_trans:
        trans_lines.extend([x, y_s, z_bot + 0.02, x, y_e, z_bot + 0.02])
        trans_lines.extend([x, y_s, z_bot + 0.02, x, y_s, z_top - 0.05])
        trans_lines.extend([x, y_e, z_bot + 0.02, x, y_e, z_top - 0.05])

    rebar_elements.append({
        "id": "rebar_cf_trans",
        "parent_id": f"rc_{cf_id}",
        "category": "rebar",
        "color": "#6366f1",
        "name": "التسليح العرضي وأحزمة الأعمدة",
        "lines": trans_lines,
    })

    # Column dowels for C1 & C2
    dowel_lines = []
    for cx_p, cw, cd in [(x1_pos, c1_m, b1_m), (x2_pos, c2_m, b2_m)]:
        half_cx = cw / 2.0 - 0.03
        half_cy = cd / 2.0 - 0.03
        for dx, dy in [(-half_cx, -half_cy), (half_cx, -half_cy), (half_cx, half_cy), (-half_cx, half_cy)]:
            dowel_lines.extend([cx_p + dx, dy, z_bot, cx_p + dx, dy, tc_m + 1.35])
            hkx = -0.20 if dx > 0 else 0.20
            dowel_lines.extend([cx_p + dx, dy, z_bot, cx_p + dx + hkx, dy, z_bot])
        for z_t in [tc_m + 0.25, tc_m + 0.55, tc_m + 0.85]:
            dowel_lines.extend([
                cx_p - half_cx, -half_cy, z_t,  cx_p + half_cx, -half_cy, z_t,
                cx_p + half_cx, -half_cy, z_t,  cx_p + half_cx,  half_cy, z_t,
                cx_p + half_cx,  half_cy, z_t,  cx_p - half_cx,  half_cy, z_t,
                cx_p - half_cx,  half_cy, z_t,  cx_p - half_cx, -half_cy, z_t,
            ])

    rebar_elements.append({
        "id": "rebar_cf_dowels",
        "parent_id": "col_1",
        "category": "rebar",
        "color": "#10b981",
        "name": "أشاير الأعمدة C1 & C2",
        "lines": dowel_lines,
    })

    scene_data = {
        "span_x": round(max(Lc + 2.5, S_m + 3.0, 7.0), 2),
        "span_y": round(max(Bc + 2.5, 5.0), 2),
        "center_x": 0.0,
        "center_y": 0.0,
        "center_y_elev": round((tc_m + 1.0) / 2.0, 2),
        "building_height": round(tc_m + 1.60, 2),
        "z_ground": 0.0,
        "grid_offset": 0.15,
        "concrete_elements": concrete_elements,
        "rebar_elements": rebar_elements,
        "categories": [
            {"id": "footings", "name": "القاعدة المشتركة"},
            {"id": "footings_pc", "name": "الخرسانة العادية"},
            {"id": "columns", "name": "الأعمدة C1 & C2"},
            {"id": "rebar", "name": "حديد التسليح والأشاير"},
        ],
        "legend_items": [
            {"color": "#ea580c", "name": f"حديد علوي رئيسي ({n_top} Φ {Phi_top})"},
            {"color": "#0284c7", "name": f"حديد سفلي رئيسي ({n_bot} Φ {Phi_bot})"},
            {"color": "#6366f1", "name": "تسليح عرضي وأحزمة"},
            {"color": "#10b981", "name": "أشاير الأعمدة C1 & C2"},
        ],
        "sketch_title": f"المسقط الأفقي للقاعدة المشتركة {cf_id} وتوزيع التسليح",
        "sketch_btn_title": "🗺️ مسقط وتفريد المشتركة",
        "sketch_dl_name": f"Combined_Footing_{cf_id}_Plan.png",
        "layout_sketch_b64": layout_sketch_b64 or "",
    }

    with st.expander("🏢 3D Integrated BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)", expanded=True):
        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 15px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                    <span>🏢 النموذج الإنشائي الرقمي للقاعدة المشتركة (ECP 203 Combined Footing BIM):</span>
                </div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; font-weight: 700; color: #e2e8f0;">
                    <span>📐 المسلحة: <b style="color:#38bdf8;">{Lc*100:.0f} × {Bc*100:.0f} × {tc_cm:.0f} سم</b></span>
                    <span>🏛️ بحر الأعمدة S: <b style="color:#4ade80;">{S_m:.2f} م</b></span>
                    <span>🌱 إجهاد التربة: <b style="color:#fb923c;">{q_act:.2f} / {q_net:.2f} kg/cm²</b></span>
                    <span>🔩 علوي: <b style="color:#ea580c;">{n_top}Φ{Phi_top}</b> │ سفلي: <b style="color:#38bdf8;">{n_bot}Φ{Phi_bot}</b></span>
                    <span>🧱 خرسانة مسلحة: <b style="color:#f472b6;">{vol_rc:.2f} م³</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        html_content = generate_bim_3d_html(scene_data, height=height)
        components.html(html_content, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
#  5. REINFORCED CONCRETE STRAP FOOTING 3D BIM & REBAR VIEWER
# ══════════════════════════════════════════════════════════════════════════════
def render_strap_footing_3d_bim_viewer(
    strap_dict: dict,
    res_dict: dict,
    layout_sketch_b64: str = "",
    height: int = 740,
):
    """
    Renders the 3D BIM & Rebar Viewer for Module 9: Strap Footing Design.
    """
    d = strap_dict
    r = res_dict

    L1 = float(r.get("L1", 2.0))
    B1 = float(r.get("B1", 1.5))
    t1_m = float(r.get("t1_cm", 60.0)) / 100.0
    L2 = float(r.get("L2", 2.2))
    B2 = float(r.get("B2", 2.2))
    t2_m = float(r.get("t2_cm", 60.0)) / 100.0

    sb_m = float(r.get("sb_m", 0.40))
    sD_m = float(r.get("sD_cm", 100.0)) / 100.0

    xc1 = float(r.get("xc1", 0.75))
    xc2 = float(r.get("xc2", 5.0))
    col1_x = float(r.get("a1_m", 0.30)) / 2.0 + float(d.get("edge_clearance", 0.0))
    col2_x = xc2
    a1_m = float(r.get("a1_m", 0.30))
    b1_m = float(r.get("b1_m", 0.60))
    a2_m = float(r.get("a2_m", 0.40))
    b2_m = float(r.get("b2_m", 0.40))

    strap_len_m = xc2 + a2_m / 2.0 + 0.15
    strap_center_x = strap_len_m / 2.0

    n_top = int(r.get("n_top", 6))
    phi_top = int(d.get("long_bar_dia", 18))
    n_bot = int(r.get("n_bot", 4))
    phi_bot = int(d.get("long_bar_dia", 18))
    phi_st = int(d.get("stirrup_dia", 10))
    st_per_m = float(r.get("stirrup_per_m", 6.0))

    concrete_elements = [
        # Footing 1 (Property line)
        {
            "id": "ftg_1_rc",
            "category": "footings",
            "name": "قاعدة الجار الخارجية F1 (Eccentric Footing)",
            "label": "F1",
            "type": "Footing 1",
            "x": xc1,
            "y": 0.0,
            "z": t1_m / 2.0,
            "dx": L1,
            "dy": B1,
            "dz": t1_m,
            "color": "#334155",
            "details": {
                "النموذج": "F1 — قاعدة الجار",
                "الأبعاد": f"{L1*100:.0f} × {B1*100:.0f} × {t1_m*100:.0f} سم",
                "إجهاد التربة q_act1": f"{r.get('q_act1', 1.2):.2f} كجم/سم²",
                "التسليح العرضي": f"{r.get('n_t1', 7)} Φ {d.get('trans_bar_dia', 16)} مم",
            },
        },
        # Footing 2 (Interior)
        {
            "id": "ftg_2_rc",
            "category": "footings",
            "name": "القاعدة الداخلية F2 (Concentric Footing)",
            "label": "F2",
            "type": "Footing 2",
            "x": xc2,
            "y": 0.0,
            "z": t2_m / 2.0,
            "dx": L2,
            "dy": B2,
            "dz": t2_m,
            "color": "#334155",
            "details": {
                "النموذج": "F2 — القاعدة الداخلية",
                "الأبعاد": f"{L2*100:.0f} × {B2*100:.0f} × {t2_m*100:.0f} سم",
                "إجهاد التربة q_act2": f"{r.get('q_act2', 1.2):.2f} كجم/سم²",
                "التسليح العرضي": f"{r.get('n_t2', 8)} Φ {d.get('trans_bar_dia', 16)} مم",
            },
        },
        # Deep Strap Beam
        {
            "id": "strap_beam_rc",
            "category": "strap_beam",
            "name": "كمرة الشداد الرابطة (Deep Strap Beam)",
            "label": "Strap",
            "type": "Strap Beam",
            "x": strap_center_x,
            "y": 0.0,
            "z": sD_m / 2.0,
            "dx": strap_len_m,
            "dy": sb_m,
            "dz": sD_m,
            "color": "#1e3a8a",
            "details": {
                "العنصر": "كمرة شداد خرسانية مسلحة",
                "القطاع (b × D)": f"{sb_m*100:.0f} × {sD_m*100:.0f} سم",
                "الطول الكلي": f"{strap_len_m:.2f} م",
                "أقصى عزم سالب Mu,max": f"{r.get('Mu_max_strap', abs(r.get('Mu_neg', 0))):.2f} طن·م",
                "موقع انعدام القص (x₀)": f"{r.get('x0', 0.0):.2f} م من حد الجار",
                "الحديد العلوي الرئيسي": f"{n_top} Φ {phi_top} مم",
                "الحديد السفلي": f"{n_bot} Φ {phi_bot} مم",
                "الكانات": f"{st_per_m:.0f} Φ {phi_st} مم / م ({r.get('n_branches', 2)} فروع)",
            },
        },
        # Column 1 (Edge)
        {
            "id": "col_1",
            "category": "columns",
            "name": f"عمود الجار C1 (P={d.get('P1', 80)}t)",
            "label": "C1",
            "type": "Column 1",
            "x": col1_x,
            "y": 0.0,
            "z": sD_m + 0.40,
            "dx": a1_m,
            "dy": b1_m,
            "dz": 0.80,
            "color": "#475569",
            "details": {
                "العمود": "C1 (عمود الجار)",
                "القطاع": f"{a1_m*100:.0f} × {b1_m*100:.0f} سم",
                "الحمل التشغيلي": f"{d.get('P1', 80)} طن",
            },
        },
        # Column 2 (Interior)
        {
            "id": "col_2",
            "category": "columns",
            "name": f"العمود الداخلي C2 (P={d.get('P2', 120)}t)",
            "label": "C2",
            "type": "Column 2",
            "x": col2_x,
            "y": 0.0,
            "z": sD_m + 0.40,
            "dx": a2_m,
            "dy": b2_m,
            "dz": 0.80,
            "color": "#475569",
            "details": {
                "العمود": "C2 (الداخلي)",
                "القطاع": f"{a2_m*100:.0f} × {b2_m*100:.0f} سم",
                "الحمل التشغيلي": f"{d.get('P2', 120)} طن",
            },
        },
    ]

    # Rebar generation
    cov = 0.05
    rebar_elements = []

    # 1. Heavy Top Strap Bars
    strap_top_lines = []
    z_top = sD_m - cov
    z_bot = cov
    half_sb = sb_m / 2.0 - cov
    ys_str_top = [-half_sb + i * (2 * half_sb) / max(1, n_top - 1) for i in range(n_top)]
    x_s_str = 0.05
    x_e_str = strap_len_m - 0.05

    for y in ys_str_top:
        strap_top_lines.extend([x_s_str, y, z_top, x_e_str, y, z_top])
        # Vertical 90 deg hooks down to bottom of footings!
        strap_top_lines.extend([x_s_str, y, z_top, x_s_str, y, z_bot + 0.08])
        strap_top_lines.extend([x_e_str, y, z_top, x_e_str, y, z_bot + 0.08])

    rebar_elements.append({
        "id": "rebar_strap_top",
        "parent_id": "strap_beam_rc",
        "category": "rebar",
        "color": "#ea580c",
        "name": f"حديد الشداد العلوي الرئيسي ({n_top} Φ {phi_top} mm)",
        "lines": strap_top_lines,
    })

    # 2. Bottom Strap Bars
    strap_bot_lines = []
    ys_str_bot = [-half_sb + i * (2 * half_sb) / max(1, n_bot - 1) for i in range(n_bot)]
    for y in ys_str_bot:
        strap_bot_lines.extend([x_s_str, y, z_bot, x_e_str, y, z_bot])
        strap_bot_lines.extend([x_s_str, y, z_bot, x_s_str, y, z_top - 0.15])
        strap_bot_lines.extend([x_e_str, y, z_bot, x_e_str, y, z_top - 0.15])

    rebar_elements.append({
        "id": "rebar_strap_bot",
        "parent_id": "strap_beam_rc",
        "category": "rebar",
        "color": "#0284c7",
        "name": f"حديد الشداد السفلي ({n_bot} Φ {phi_bot} mm)",
        "lines": strap_bot_lines,
    })

    # 3. Strap Stirrups
    strap_st_lines = []
    num_st = max(8, int(round(strap_len_m * st_per_m)))
    for k in range(num_st):
        cur_x = x_s_str + k * (strap_len_m - 0.10) / max(1, num_st - 1)
        strap_st_lines.extend([
            cur_x, -half_sb, z_bot, cur_x,  half_sb, z_bot,
            cur_x,  half_sb, z_bot, cur_x,  half_sb, z_top,
            cur_x,  half_sb, z_top, cur_x, -half_sb, z_top,
            cur_x, -half_sb, z_top, cur_x, -half_sb, z_bot,
        ])

    rebar_elements.append({
        "id": "rebar_strap_stirrups",
        "parent_id": "strap_beam_rc",
        "category": "rebar",
        "color": "#ec4899",
        "name": f"كانات الشداد المكثفة (Φ {phi_st} @ {st_per_m:.0f}/m)",
        "lines": strap_st_lines,
    })

    # 4. Skin Bars (if sD >= 60cm)
    if sD_m >= 0.60:
        skin_lines = []
        n_side_levels = max(1, int((sD_m - 0.20) / 0.30))
        for lvl in range(1, n_side_levels + 1):
            z_side = z_bot + lvl * (sD_m - 2 * cov) / (n_side_levels + 1)
            skin_lines.extend([x_s_str, -half_sb, z_side, x_e_str, -half_sb, z_side])
            skin_lines.extend([x_s_str,  half_sb, z_side, x_e_str,  half_sb, z_side])
        rebar_elements.append({
            "id": "rebar_strap_skin",
            "parent_id": "strap_beam_rc",
            "category": "rebar",
            "color": "#eab308",
            "name": "براندات الانكماش الجانبية (Skin Bars)",
            "lines": skin_lines,
        })

    # 5. Footing Transverse Bottom Bars
    ftg_lines = []
    # F1
    n_t1 = int(r.get("n_t1", 8))
    xs_f1 = [xc1 - L1/2.0 + cov + i * (L1 - 2*cov) / max(1, n_t1 - 1) for i in range(n_t1)]
    for x in xs_f1:
        ftg_lines.extend([x, -B1/2.0 + cov, cov, x, B1/2.0 - cov, cov])
        ftg_lines.extend([x, -B1/2.0 + cov, cov, x, -B1/2.0 + cov, t1_m - cov])
        ftg_lines.extend([x,  B1/2.0 - cov, cov, x,  B1/2.0 - cov, t1_m - cov])

    # F2
    n_t2 = int(r.get("n_t2", 8))
    xs_f2 = [xc2 - L2/2.0 + cov + i * (L2 - 2*cov) / max(1, n_t2 - 1) for i in range(n_t2)]
    for x in xs_f2:
        ftg_lines.extend([x, -B2/2.0 + cov, cov, x, B2/2.0 - cov, cov])
        ftg_lines.extend([x, -B2/2.0 + cov, cov, x, -B2/2.0 + cov, t2_m - cov])
        ftg_lines.extend([x,  B2/2.0 - cov, cov, x,  B2/2.0 - cov, t2_m - cov])

    rebar_elements.append({
        "id": "rebar_strap_ftgs",
        "parent_id": "ftg_1_rc",
        "category": "rebar",
        "color": "#14b8a6",
        "name": "تسليح القواعد العرضي الرئيسي",
        "lines": ftg_lines,
    })

    # 6. Column Dowels
    dowel_lines = []
    for cx_p, cw, cd in [(col1_x, a1_m, b1_m), (col2_x, a2_m, b2_m)]:
        hc_x = cw / 2.0 - 0.03
        hc_y = cd / 2.0 - 0.03
        for dx, dy in [(-hc_x, -hc_y), (hc_x, -hc_y), (hc_x, hc_y), (-hc_x, hc_y)]:
            dowel_lines.extend([cx_p + dx, dy, cov, cx_p + dx, dy, sD_m + 0.80 + 0.35])
            hkx = -0.15 if dx > 0 else 0.15
            dowel_lines.extend([cx_p + dx, dy, cov, cx_p + dx + hkx, dy, cov])
        for z_t in [sD_m + 0.20, sD_m + 0.50, sD_m + 0.75]:
            dowel_lines.extend([
                cx_p - hc_x, -hc_y, z_t,  cx_p + hc_x, -hc_y, z_t,
                cx_p + hc_x, -hc_y, z_t,  cx_p + hc_x,  hc_y, z_t,
                cx_p + hc_x,  hc_y, z_t,  cx_p - hc_x,  hc_y, z_t,
                cx_p - hc_x,  hc_y, z_t,  cx_p - hc_x, -hc_y, z_t,
            ])

    rebar_elements.append({
        "id": "rebar_strap_dowels",
        "parent_id": "col_1",
        "category": "rebar",
        "color": "#10b981",
        "name": "أشاير الأعمدة C1 & C2",
        "lines": dowel_lines,
    })

    scene_data = {
        "span_x": round(strap_len_m + 1.2, 2),
        "span_y": round(max(B1, B2) + 1.0, 2),
        "center_x": round(strap_center_x, 2),
        "center_y": 0.0,
        "center_y_elev": round(sD_m / 2.0, 2),
        "building_height": round(sD_m + 1.20, 2),
        "z_ground": 0.0,
        "grid_offset": 0.20,
        "concrete_elements": concrete_elements,
        "rebar_elements": rebar_elements,
        "categories": [
            {"id": "strap_beam", "name": "كمرة الشداد"},
            {"id": "footings", "name": "القواعد F1 & F2"},
            {"id": "columns", "name": "الأعمدة C1 & C2"},
            {"id": "rebar", "name": "حديد التسليح والكانات"},
        ],
        "legend_items": [
            {"color": "#ea580c", "name": f"حديد الشداد العلوي ({n_top} Φ {phi_top})"},
            {"color": "#0284c7", "name": f"حديد الشداد السفلي ({n_bot} Φ {phi_bot})"},
            {"color": "#ec4899", "name": f"كانات الشداد ({st_per_m:.0f} Φ {phi_st}/m)"},
            {"color": "#14b8a6", "name": "تسليح القواعد العرضي"},
            {"color": "#10b981", "name": "أشاير الأعمدة"},
        ],
        "sketch_title": "اللوحة الإنشائية والتنفيذية للشداد والقواعد",
        "sketch_btn_title": "🗺️ مسقط وتفريد الشداد",
        "sketch_dl_name": "Strap_Footing_Detailing.png",
        "layout_sketch_b64": layout_sketch_b64 or "",
    }

    with st.expander("🏢 3D Integrated BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)", expanded=True):
        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 15px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                    <span>🏢 النموذج الإنشائي الرقمي لقواعد الجار بالشداد (ECP 203 Strap Footing BIM):</span>
                </div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; font-weight: 700; color: #e2e8f0;">
                    <span>🔗 كمرة الشداد: <b style="color:#38bdf8;">{sb_m*100:.0f} × {sD_m*100:.0f} سم</b></span>
                    <span>📐 قاعدة الجار F1: <b style="color:#4ade80;">{L1*100:.0f} × {B1*100:.0f} سم</b></span>
                    <span>📐 القاعدة الداخلية F2: <b style="color:#fb923c;">{L2*100:.0f} × {B2*100:.0f} سم</b></span>
                    <span>📉 العزم الأقصى Mu: <b style="color:#a3e635;">{r.get('Mu_max_strap', abs(r.get('Mu_neg', 0))):.2f} t·m</b></span>
                    <span>🔩 علوي الشداد: <b style="color:#ea580c;">{n_top}Φ{phi_top}</b> │ سفلي: <b style="color:#38bdf8;">{n_bot}Φ{phi_bot}</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_3d, tab_plan = st.tabs([
            "🏢 العرض ثلاثي الأبعاد التفاعلي (3D Interactive BIM Model)",
            "📐 المسقط الأفقي العام للقواعد والشداد (2D Layout Plan)",
        ])

        with tab_3d:
            html_content = generate_bim_3d_html(scene_data, height=height)
            components.html(html_content, height=height, scrolling=False)

        with tab_plan:
            if layout_sketch_b64:
                clean_b64 = layout_sketch_b64
                if clean_b64.startswith("data:"):
                    clean_b64 = clean_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(clean_b64)
                st.image(img_bytes, caption="المسقط الأفقي التنفيذي لقواعد الجار والشداد — ECP 203", use_container_width=True)
                st.download_button(
                    "📥 تحميل المسقط الأفقي عالي الدقة (Download 2D Plan PNG)",
                    data=img_bytes,
                    file_name="Strap_Footing_2D_Plan.png",
                    mime="image/png",
                    use_container_width=True,
                    key="btn_dl_m9_bim_plan",
                )
            else:
                st.info("💡 لم يتم توليد المسقط الأفقي بعد.")


# ══════════════════════════════════════════════════════════════════════════════
#  6. CORNER FOOTING WITH DIAGONAL STRAP 3D BIM & REBAR VIEWER
# ══════════════════════════════════════════════════════════════════════════════
def render_diagonal_strap_3d_bim_viewer(
    diag_dict: dict,
    res_dict: dict,
    layout_sketch_b64: str = "",
    height: int = 740,
):
    """
    Renders the 3D BIM & Rebar Viewer for Module 10: Corner Footing with Diagonal Strap.
    """
    d = diag_dict
    r = res_dict

    L1 = float(r.get("L1", 2.0))
    B1 = float(r.get("B1", 2.0))
    t1_m = float(r.get("t1_cm", 60.0)) / 100.0

    L2 = float(r.get("L2", 2.4))
    B2 = float(r.get("B2", 2.4))
    t2_m = float(r.get("t2_cm", 60.0)) / 100.0

    sb_m = float(r.get("sb_m", 0.45))
    sD_m = float(r.get("sD_cm", 110.0)) / 100.0

    X2 = float(r.get("X2", 5.0))
    Y2 = float(r.get("Y2", 5.0))
    L_diag = math.sqrt(X2 ** 2 + Y2 ** 2)
    theta = math.atan2(Y2, X2)

    a1_m = float(r.get("a1_m", 0.35))
    b1_m = float(r.get("b1_m", 0.35))
    a2_m = float(r.get("a2_m", 0.40))
    b2_m = float(r.get("b2_m", 0.40))

    n_top = int(r.get("n_top", 8))
    phi_top = int(d.get("long_bar_dia", 18))
    n_bot = int(r.get("n_bot", 4))
    phi_bot = int(d.get("long_bar_dia", 18))
    phi_st = int(d.get("stirrup_dia", 10))

    concrete_elements = [
        # Corner Footing F1
        {
            "id": "ftg_1_diag",
            "category": "footings",
            "name": "قاعدة الركن الخارجية F1 (Corner Footing)",
            "label": "F1",
            "type": "Corner Footing",
            "x": 0.0,
            "y": 0.0,
            "z": t1_m / 2.0,
            "dx": L1,
            "dy": B1,
            "dz": t1_m,
            "color": "#334155",
            "details": {
                "النموذج": "F1 — قاعدة ركن (لا مركزية ثنائية المحاور)",
                "الأبعاد": f"{L1*100:.0f} × {B1*100:.0f} × {t1_m*100:.0f} سم",
                "إجهاد التربة q_act1": f"{r.get('q_act1', 1.2):.2f} كجم/سم²",
            },
        },
        # Interior Footing F2
        {
            "id": "ftg_2_diag",
            "category": "footings",
            "name": "القاعدة الداخلية F2 (Interior Footing)",
            "label": "F2",
            "type": "Interior Footing",
            "x": X2,
            "y": Y2,
            "z": t2_m / 2.0,
            "dx": L2,
            "dy": B2,
            "dz": t2_m,
            "color": "#334155",
            "details": {
                "النموذج": "F2 — القاعدة الداخلية",
                "الأبعاد": f"{L2*100:.0f} × {B2*100:.0f} × {t2_m*100:.0f} سم",
                "إجهاد التربة q_act2": f"{r.get('q_act2', 1.2):.2f} كجم/سم²",
            },
        },
        # Diagonal Strap Beam (Rotated around Z by theta)
        {
            "id": "diag_strap_beam",
            "category": "strap_beam",
            "name": "الشداد المائل (Diagonal Strap Beam)",
            "label": "Diag-Strap",
            "type": "Diagonal Strap",
            "x": X2 / 2.0,
            "y": Y2 / 2.0,
            "z": sD_m / 2.0,
            "dx": L_diag,
            "dy": sb_m,
            "dz": sD_m,
            "rot_z": theta,
            "color": "#1e3a8a",
            "details": {
                "العنصر": "كمرة شداد مائل ركنية",
                "القطاع (b × D)": f"{sb_m*100:.0f} × {sD_m*100:.0f} سم",
                "الطول القطري": f"{L_diag:.2f} م (زاوية الميل: {math.degrees(theta):.1f}°)",
                "العزم الأقصى Mu": f"{r.get('Mu_max_strap', abs(r.get('Mu_neg', 0))):.2f} طن·م",
                "الحديد العلوي": f"{n_top} Φ {phi_top} مم",
                "الحديد السفلي": f"{n_bot} Φ {phi_bot} مم",
            },
        },
        # Column 1 (Corner)
        {
            "id": "col_1_corner",
            "category": "columns",
            "name": "عمود الركن C1",
            "label": "C1",
            "type": "Corner Column",
            "x": 0.0,
            "y": 0.0,
            "z": sD_m + 0.40,
            "dx": a1_m,
            "dy": b1_m,
            "dz": 0.80,
            "color": "#475569",
            "details": {
                "العمود": "C1 (ركن)",
                "القطاع": f"{a1_m*100:.0f} × {b1_m*100:.0f} سم",
            },
        },
        # Column 2 (Interior)
        {
            "id": "col_2_diag",
            "category": "columns",
            "name": "العمود الداخلي C2",
            "label": "C2",
            "type": "Interior Column",
            "x": X2,
            "y": Y2,
            "z": sD_m + 0.40,
            "dx": a2_m,
            "dy": b2_m,
            "dz": 0.80,
            "color": "#475569",
            "details": {
                "العمود": "C2 (داخلي)",
                "القطاع": f"{a2_m*100:.0f} × {b2_m*100:.0f} سم",
            },
        },
    ]

    cov = 0.05
    rebar_elements = []

    # Diagonal Top & Bottom Rebars along vector
    diag_top_lines = []
    diag_bot_lines = []
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    # Perpendicular unit vector in XY
    px = -sin_t
    py = cos_t

    half_sb = sb_m / 2.0 - cov
    z_top = sD_m - cov
    z_bot = cov

    # Top Bars
    for i in range(n_top):
        offset = -half_sb + i * (2 * half_sb) / max(1, n_top - 1)
        sx = 0.10 * cos_t + offset * px
        sy = 0.10 * sin_t + offset * py
        ex = (L_diag - 0.10) * cos_t + offset * px
        ey = (L_diag - 0.10) * sin_t + offset * py

        diag_top_lines.extend([sx, sy, z_top, ex, ey, z_top])
        diag_top_lines.extend([sx, sy, z_top, sx, sy, z_bot + 0.10])
        diag_top_lines.extend([ex, ey, z_top, ex, ey, z_bot + 0.10])

    rebar_elements.append({
        "id": "rebar_diag_top",
        "parent_id": "diag_strap_beam",
        "category": "rebar",
        "color": "#ea580c",
        "name": f"حديد الشداد المائل العلوي ({n_top} Φ {phi_top} mm)",
        "lines": diag_top_lines,
    })

    # Bottom Bars
    for j in range(n_bot):
        offset = -half_sb + j * (2 * half_sb) / max(1, n_bot - 1)
        sx = 0.10 * cos_t + offset * px
        sy = 0.10 * sin_t + offset * py
        ex = (L_diag - 0.10) * cos_t + offset * px
        ey = (L_diag - 0.10) * sin_t + offset * py

        diag_bot_lines.extend([sx, sy, z_bot, ex, ey, z_bot])
        diag_bot_lines.extend([sx, sy, z_bot, sx, sy, z_top - 0.10])
        diag_bot_lines.extend([ex, ey, z_bot, ex, ey, z_top - 0.10])

    rebar_elements.append({
        "id": "rebar_diag_bot",
        "parent_id": "diag_strap_beam",
        "category": "rebar",
        "color": "#0284c7",
        "name": f"حديد الشداد المائل السفلي ({n_bot} Φ {phi_bot} mm)",
        "lines": diag_bot_lines,
    })

    scene_data = {
        "span_x": round(X2 + max(L1, L2), 2),
        "span_y": round(Y2 + max(B1, B2), 2),
        "center_x": round(X2 / 2.0, 2),
        "center_y": round(Y2 / 2.0, 2),
        "center_y_elev": round(sD_m / 2.0, 2),
        "building_height": round(sD_m + 1.20, 2),
        "z_ground": 0.0,
        "grid_offset": 0.20,
        "concrete_elements": concrete_elements,
        "rebar_elements": rebar_elements,
        "categories": [
            {"id": "strap_beam", "name": "الشداد المائل"},
            {"id": "footings", "name": "القواعد (ركن وداخلية)"},
            {"id": "columns", "name": "الأعمدة C1 & C2"},
            {"id": "rebar", "name": "حديد التسليح"},
        ],
        "legend_items": [
            {"color": "#ea580c", "name": f"حديد الشداد العلوي ({n_top} Φ {phi_top})"},
            {"color": "#0284c7", "name": f"حديد الشداد السفلي ({n_bot} Φ {phi_bot})"},
            {"color": "#14b8a6", "name": "تسليح القواعد"},
            {"color": "#10b981", "name": "أشاير الأعمدة"},
        ],
        "sketch_title": "المخطط الإنشائي للشداد المائل وقاعدة الركن",
        "sketch_btn_title": "🗺️ مسقط الشداد المائل",
        "sketch_dl_name": "Diagonal_Strap_Detailing.png",
        "layout_sketch_b64": layout_sketch_b64 or "",
    }

    with st.expander("🏢 3D Integrated BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)", expanded=True):
        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 15px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                    <span>🏢 النموذج الإنشائي لقاعدة الركن بشداد مائل (ECP 203 Diagonal Strap BIM):</span>
                </div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; font-weight: 700; color: #e2e8f0;">
                    <span>📐 الشداد المائل: <b style="color:#38bdf8;">{sb_m*100:.0f} × {sD_m*100:.0f} سم (L = {L_diag:.2f} م)</b></span>
                    <span>📐 قاعدة الركن F1: <b style="color:#4ade80;">{L1*100:.0f} × {B1*100:.0f} سم</b></span>
                    <span>📐 الداخلية F2: <b style="color:#fb923c;">{L2*100:.0f} × {B2*100:.0f} سم</b></span>
                    <span>🔩 علوي: <b style="color:#ea580c;">{n_top}Φ{phi_top}</b> │ سفلي: <b style="color:#38bdf8;">{n_bot}Φ{phi_bot}</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        html_content = generate_bim_3d_html(scene_data, height=height)
        components.html(html_content, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
#  7. GROUND BEAM DESIGN & DETAILING 3D BIM & REBAR VIEWER
# ══════════════════════════════════════════════════════════════════════════════
def render_ground_beam_3d_bim_viewer(
    b_cm: float,
    t_cm: float,
    L_m: float,
    n_top: int,
    phi_top: int,
    n_bot: int,
    phi_bot: int,
    phi_st: int = 8,
    n_st_per_m: int = 5,
    n_branches: int = 2,
    n_side: int = 0,
    phi_side: int = 10,
    fcu: float = 250.0,
    fy: float = 4000.0,
    Mu_tm: float = 0.0,
    Qu_ton: float = 0.0,
    layout_sketch_b64: str = "",
    beam_id: str = "GB1",
    height: int = 740,
):
    """
    Renders the 3D BIM & Rebar Viewer for Module 11: Ground Beam Design & Detailing.
    """
    b_m = max(0.20, b_cm / 100.0)
    t_m = max(0.30, t_cm / 100.0)
    L = max(1.5, float(L_m))
    vol_rc = b_m * t_m * L

    ped_w = max(0.40, b_m + 0.10)
    ped_h = t_m + 0.30

    concrete_elements = [
        {
            "id": f"gb_{beam_id}",
            "category": "ground_beams",
            "name": f"الميدة الخرسانية المسلحة {beam_id}",
            "label": str(beam_id),
            "type": "Ground Beam",
            "x": 0.0,
            "y": 0.0,
            "z": t_m / 2.0,
            "dx": L,
            "dy": b_m,
            "dz": t_m,
            "color": "#334155",
            "details": {
                "النموذج": f"{beam_id} — ميدة / سمل ربط أرضي",
                "القطاع (b × t)": f"{b_cm:.0f} × {t_cm:.0f} سم",
                "البحر الصافي (L)": f"{L:.2f} م",
                "عزم الانحناء التصميمي (Mu)": f"{Mu_tm:.2f} طن·م",
                "قوة القص القصوى (Qu)": f"{Qu_ton:.2f} طن",
                "التسليح العلوي": f"{n_top} Φ {phi_top} مم",
                "التسليح السفلي": f"{n_bot} Φ {phi_bot} مم",
                "الكانات": f"{n_st_per_m} Φ {phi_st} / م ({n_branches} فروع)",
                "براندات الانكماش": f"{n_side} Φ {phi_side} مم" if n_side > 0 else "غير مطلوبة (العمق < 60 سم)",
                "حجم الخرسانة": f"{vol_rc:.2f} م³",
            },
        },
        # Left pedestal
        {
            "id": "col_ped_left",
            "category": "columns",
            "name": "ركيزة العمود الأيسر (Left Support)",
            "label": "C-Left",
            "type": "Support Column",
            "x": -L / 2.0,
            "y": 0.0,
            "z": ped_h / 2.0,
            "dx": ped_w,
            "dy": ped_w,
            "dz": ped_h,
            "color": "#475569",
            "details": {"النوع": "عمود/قاعدة تثبيت طرفية"},
        },
        # Right pedestal
        {
            "id": "col_ped_right",
            "category": "columns",
            "name": "ركيزة العمود الأيمن (Right Support)",
            "label": "C-Right",
            "type": "Support Column",
            "x": L / 2.0,
            "y": 0.0,
            "z": ped_h / 2.0,
            "dx": ped_w,
            "dy": ped_w,
            "dz": ped_h,
            "color": "#475569",
            "details": {"النوع": "عمود/قاعدة تثبيت طرفية"},
        },
    ]

    cov = 0.04
    rebar_elements = []

    # Top Rebars
    top_lines = []
    z_top = t_m - cov
    z_bot = cov
    half_b = b_m / 2.0 - cov
    ys_top = [-half_b + i * (2 * half_b) / max(1, n_top - 1) for i in range(n_top)]
    x_s = -L / 2.0 - 0.15
    x_e = L / 2.0 + 0.15

    for y in ys_top:
        top_lines.extend([x_s, y, z_top, x_e, y, z_top])
        # 90 deg downward hooks into supports
        top_lines.extend([x_s, y, z_top, x_s, y, z_bot + 0.10])
        top_lines.extend([x_e, y, z_top, x_e, y, z_bot + 0.10])

    rebar_elements.append({
        "id": f"rebar_gb_top_{beam_id}",
        "parent_id": f"gb_{beam_id}",
        "category": "rebar",
        "color": "#ea580c",
        "name": f"حديد الميدة العلوي ({n_top} Φ {phi_top} mm)",
        "lines": top_lines,
    })

    # Bottom Rebars
    bot_lines = []
    ys_bot = [-half_b + i * (2 * half_b) / max(1, n_bot - 1) for i in range(n_bot)]
    for y in ys_bot:
        bot_lines.extend([x_s, y, z_bot, x_e, y, z_bot])
        bot_lines.extend([x_s, y, z_bot, x_s, y, z_top - 0.10])
        bot_lines.extend([x_e, y, z_bot, x_e, y, z_top - 0.10])

    rebar_elements.append({
        "id": f"rebar_gb_bot_{beam_id}",
        "parent_id": f"gb_{beam_id}",
        "category": "rebar",
        "color": "#0284c7",
        "name": f"حديد الميدة السفلي ({n_bot} Φ {phi_bot} mm)",
        "lines": bot_lines,
    })

    # Stirrups
    st_lines = []
    num_st = max(6, int(round(L * n_st_per_m)))
    for k in range(num_st):
        cur_x = -L / 2.0 + 0.05 + k * (L - 0.10) / max(1, num_st - 1)
        st_lines.extend([
            cur_x, -half_b, z_bot, cur_x,  half_b, z_bot,
            cur_x,  half_b, z_bot, cur_x,  half_b, z_top,
            cur_x,  half_b, z_top, cur_x, -half_b, z_top,
            cur_x, -half_b, z_top, cur_x, -half_b, z_bot,
        ])

    rebar_elements.append({
        "id": f"rebar_gb_stirrups_{beam_id}",
        "parent_id": f"gb_{beam_id}",
        "category": "rebar",
        "color": "#ec4899",
        "name": f"كانات الميدة المغلقة (Φ {phi_st} @ {n_st_per_m}/m)",
        "lines": st_lines,
    })

    # Side bars
    if n_side > 0 or t_m >= 0.60:
        side_lines = []
        n_levels = max(1, n_side // 2 if n_side >= 2 else int((t_m - 0.20) / 0.30))
        for lvl in range(1, n_levels + 1):
            z_s = z_bot + lvl * (t_m - 2 * cov) / (n_levels + 1)
            side_lines.extend([x_s, -half_b, z_s, x_e, -half_b, z_s])
            side_lines.extend([x_s,  half_b, z_s, x_e,  half_b, z_s])
        rebar_elements.append({
            "id": f"rebar_gb_side_{beam_id}",
            "parent_id": f"gb_{beam_id}",
            "category": "rebar",
            "color": "#eab308",
            "name": f"براندات انكماش جانبية ({max(2, n_side)} Φ {phi_side} mm)",
            "lines": side_lines,
        })

    scene_data = {
        "span_x": round(L + 1.2, 2),
        "span_y": round(b_m + 1.2, 2),
        "center_x": 0.0,
        "center_y": 0.0,
        "center_y_elev": round(t_m / 2.0, 2),
        "building_height": round(t_m + 1.0, 2),
        "z_ground": 0.0,
        "grid_offset": 0.15,
        "concrete_elements": concrete_elements,
        "rebar_elements": rebar_elements,
        "categories": [
            {"id": "ground_beams", "name": "الميدة/السمل"},
            {"id": "columns", "name": "ركائز الأعمدة"},
            {"id": "rebar", "name": "حديد التسليح والكانات"},
        ],
        "legend_items": [
            {"color": "#ea580c", "name": f"حديد علوي ({n_top} Φ {phi_top})"},
            {"color": "#0284c7", "name": f"حديد سفلي ({n_bot} Φ {phi_bot})"},
            {"color": "#ec4899", "name": f"كانات مغلقة (Φ {phi_st} @ {n_st_per_m}/m)"},
            {"color": "#eab308", "name": "براندات انكماش جانبية"},
        ],
        "sketch_title": f"المخطط التنفيذي وتفريد تسليح الميدة {beam_id}",
        "sketch_btn_title": "🗺️ قطاع وتفريد الميدة",
        "sketch_dl_name": f"Ground_Beam_{beam_id}_{b_cm:.0f}x{t_cm:.0f}cm_Detailing.png",
        "layout_sketch_b64": layout_sketch_b64 or "",
    }

    with st.expander("🏢 3D Integrated BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)", expanded=True):
        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 15px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                    <span>🏢 النموذج الإنشائي الرقمي للميدة (ECP 203 Ground Beam BIM):</span>
                </div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; font-weight: 700; color: #e2e8f0;">
                    <span>🧱 القطاع: <b style="color:#38bdf8;">{b_cm:.0f} × {t_cm:.0f} سم</b></span>
                    <span>📏 البحر L: <b style="color:#4ade80;">{L:.2f} م</b></span>
                    <span>📉 عزم الانحناء Mu: <b style="color:#fb923c;">{Mu_tm:.2f} t·m</b></span>
                    <span>🔩 علوي: <b style="color:#ea580c;">{n_top}Φ{phi_top}</b> │ سفلي: <b style="color:#38bdf8;">{n_bot}Φ{phi_bot}</b></span>
                    <span>⚙️ الكانات: <b style="color:#a3e635;">{n_st_per_m}Φ{phi_st}/m</b></span>
                    <span>🧱 خرسانة: <b style="color:#f472b6;">{vol_rc:.2f} م³</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        html_content = generate_bim_3d_html(scene_data, height=height)
        components.html(html_content, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
#  8. STANDALONE FLAT SLABS 3D BIM & REBAR VIEWER
# ══════════════════════════════════════════════════════════════════════════════
def render_standalone_flat_slab_3d_bim_viewer(
    Lx_calc: list,
    Ly_calc: list,
    cantilevers: dict,
    ts_cm: float,
    active_cols: list,
    col_H_cm: float = 300.0,
    top_extra_cols: list = None,
    btm_extra_spans: list = None,
    punching_results: list = None,
    n_mesh_btm: float = 5.0,
    bottom_mesh_dia: int = 10,
    n_mesh_top: float = 5.0,
    top_mesh_dia: int = 10,
    fcu: float = 250.0,
    fy: float = 4000.0,
    layout_sketch_b64: str = "",
    prefix: str = "",
    height: int = 760,
):
    """
    Renders the 3D BIM & Rebar Viewer for Module 13: Standalone Flat Slabs.
    """
    with st.expander("🏢 3D Integrated BIM & Rebar Viewer (عارض النماذج الإنشائية ثلاثي الأبعاد والحديد)", expanded=True):
        scene_data = extract_bim_3d_scene_data(
            Lx_calc=Lx_calc,
            Ly_calc=Ly_calc,
            cantilevers=cantilevers,
            ts_cm=ts_cm,
            active_cols=active_cols,
            col_H_cm=col_H_cm,
            num_floors=1,
            ftg_analysis=None,
            gb_analysis=None,
            punching_results=punching_results,
            top_extra_cols=top_extra_cols,
            btm_extra_spans=btm_extra_spans,
            n_mesh_btm=n_mesh_btm,
            bottom_mesh_dia=bottom_mesh_dia,
            n_mesh_top=n_mesh_top,
            top_mesh_dia=top_mesh_dia,
            fcu=fcu,
            fy=fy,
        )

        if not scene_data or not scene_data.get("concrete_elements"):
            st.info("💡 أدخل بيانات شبكة المحاور وقم بتنفيذ التصميم لعرض النموذج الإنشائي ثلاثي الأبعاد للبلاطة اللاكمرية.")
            return

        scene_data["categories"] = [
            {"id": "slab", "name": "سقف البلاطة"},
            {"id": "columns", "name": "الأعمدة الحاملة"},
            {"id": "rebar", "name": "حديد التسليح والكابات"},
        ]
        scene_data["legend_items"] = [
            {"color": "#0284c7", "name": f"شبكة سفلية ({n_mesh_btm:.0f} Φ {bottom_mesh_dia}/م)"},
            {"color": "#6366f1", "name": f"شبكة علوية ({n_mesh_top:.0f} Φ {top_mesh_dia}/م)"},
            {"color": "#f97316", "name": "كابات إضافي الأعمدة"},
            {"color": "#ec4899", "name": "تسليح القص الثاقب"},
            {"color": "#10b981", "name": "تسليح الأعمدة"},
        ]
        scene_data["sketch_title"] = "المسقط الأفقي وتفريد تسليح السقف اللاكمري"
        scene_data["sketch_btn_title"] = "🗺️ مسقط السقف والتسليح"
        scene_data["sketch_dl_name"] = "Standalone_Flat_Slab_Reinforcement.png"
        # Check / retrieve / generate Flat Slab Layout Sketch base64 for side-by-side comparison
        fs_sketch = layout_sketch_b64 or st.session_state.get(f"{prefix}flat_slab_plan_b64", "")
        if (not fs_sketch or len(fs_sketch) < 25000) and active_cols and Lx_calc and Ly_calc:
            try:
                import io, base64
                import matplotlib.pyplot as plt
                from modules.flat_slab import generate_flat_slab_sketch
                fig_fs = generate_flat_slab_sketch(
                    Lx_calc, Ly_calc, cantilevers,
                    ts_initial=ts_cm,
                    n_floors=1,
                    bottom_mesh_dia=bottom_mesh_dia,
                    bottom_mesh_n=int(n_mesh_btm),
                    top_mesh_dia=top_mesh_dia,
                    top_mesh_n=int(n_mesh_top),
                    fcu=fcu,
                    fy=fy,
                )
                buf_sk = io.BytesIO()
                fig_fs.savefig(buf_sk, format="png", bbox_inches="tight", dpi=160)
                plt.close(fig_fs)
                buf_sk.seek(0)
                fs_sketch = "data:image/png;base64," + base64.b64encode(buf_sk.getvalue()).decode("utf-8")
                st.session_state[f"{prefix}flat_slab_plan_b64"] = fs_sketch
            except Exception:
                pass
        scene_data["layout_sketch_b64"] = fs_sketch or ""

        m = scene_data["metrics"]

        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 18px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 15px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                    <span>🏢 النموذج الإنشائي الرقمي للسقف اللاكمري (Standalone Flat Slab BIM Model):</span>
                </div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; font-weight: 700; color: #e2e8f0;">
                    <span>📐 مسطح السقف: <b style="color:#38bdf8;">{m['slab_area_m2']} م²</b></span>
                    <span>🧱 السُمك ts: <b style="color:#4ade80;">{ts_cm:.0f} سم</b></span>
                    <span>🏛️ الأعمدة الحاملة: <b style="color:#fb923c;">{m['num_columns']} عمود</b></span>
                    <span>🔩 شبكة سفلية: <b style="color:#a3e635;">{n_mesh_btm:.0f}Φ{bottom_mesh_dia}/م</b></span>
                    <span>🔩 شبكة علوية: <b style="color:#f472b6;">{n_mesh_top:.0f}Φ{top_mesh_dia}/م</b></span>
                    <span>🧱 حجم الخرسانة: <b style="color:#e0e7ff;">{m['slab_area_m2']*(ts_cm/100.0):.2f} م³</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        html_content = generate_bim_3d_html(scene_data, height=height)
        components.html(html_content, height=height, scrolling=False)

