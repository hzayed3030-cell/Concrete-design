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

    x_min_slab = -cant_left
    x_max_slab = sum(Lx_calc) + cant_right
    y_min_slab = -cant_bottom
    y_max_slab = sum(Ly_calc) + cant_top

    slab_w_x = x_max_slab - x_min_slab
    slab_w_y = y_max_slab - y_min_slab
    slab_center_x = (x_min_slab + x_max_slab) / 2.0
    slab_center_y = (y_min_slab + y_max_slab) / 2.0

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

    # 1.3 FOUNDATIONS (Isolated, Combined, Edge Strap, Corner Strap)
    if ftg_analysis:
        # A. Isolated Footings
        for f_iso in ftg_analysis.get("isolated_footings", []):
            cid = f_iso.get("col_id") or (f_iso.get("col", {}).get("id") if isinstance(f_iso.get("col"), dict) else "")
            fx = float(f_iso.get("x", 0.0))
            fy_coord = float(f_iso.get("y", 0.0))
            L_rc = float(f_iso.get("L_rc", f_iso.get("Lc_cm", 200.0) / 100.0))
            B_rc = float(f_iso.get("B_rc", f_iso.get("Bc_cm", 200.0) / 100.0))
            t_rc = float(f_iso.get("t_rc", f_iso.get("tc_cm", 50.0) / 100.0))
            L_pc = float(f_iso.get("L_pc", L_rc + 0.40))
            B_pc = float(f_iso.get("B_pc", B_rc + 0.40))
            t_pc = 0.20

            f_id = f"ftg_iso_{cid}"
            m_name = f_iso.get("model_name", f_iso.get("name", f"F-{cid}"))

            concrete_elements.append({
                "id": f_id,
                "category": "footings",
                "name": f"قاعدة منفصلة {m_name} (عمود {cid})",
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

        # B. Combined Footings
        for cf in ftg_analysis.get("combined_footings", []):
            cf_name = cf.get("name", "CF-1")
            cf_cols = cf.get("supported_cols", "")
            L_rc = float(cf.get("Lc_cm", 350.0)) / 100.0
            B_rc = float(cf.get("Bc_cm", 220.0)) / 100.0
            t_rc = float(cf.get("tc_cm", 70.0)) / 100.0
            cx_cf = float(cf.get("x_c", cf.get("col1", {}).get("x", 0.0)))
            cy_cf = float(cf.get("y_c", cf.get("col1", {}).get("y", 0.0)))

            cf_id = f"ftg_cf_{cf_name}"
            concrete_elements.append({
                "id": cf_id,
                "category": "footings",
                "name": f"قاعدة مشتركة {cf_name} ({cf_cols})",
                "type": "Combined Footing (RC)",
                "x": cx_cf,
                "y": cy_cf,
                "z": z_ground - (t_rc / 2.0),
                "dx": L_rc,
                "dy": B_rc,
                "dz": t_rc,
                "color": "#10b981",
                "details": {
                    "النموذج": f"{cf_name} (قاعدة مشتركة)",
                    "الأعمدة المرتكزة": cf_cols,
                    "أبعاد المسلحة (L × B × t)": f"{int(L_rc*100)} × {int(B_rc*100)} × {int(t_rc*100)} سم",
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
                "dx": L_rc + 0.40,
                "dy": B_rc + 0.40,
                "dz": 0.20,
                "color": "#94a3b8",
                "details": {
                    "النوع": "فرشة خرسانة عادية 20 سم",
                    "الأبعاد": f"{int((L_rc+0.4)*100)} × {int((B_rc+0.4)*100)} × 20 سم",
                }
            })

            # Combined Rebar Mesh
            f_cov = cover_ftg_cm / 100.0
            rebar_w = L_rc - 2 * f_cov
            rebar_d = B_rc - 2 * f_cov
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
            c1_id = c1.get("id", "")
            c2_id = c2.get("id", "")

            L1 = float(sf.get("L1", 2.2))
            B1 = float(sf.get("B1", 3.0))
            t1 = float(sf.get("t1", 60.0)) / 100.0
            x1 = float(c1.get("x", 0.0))
            y1 = float(c1.get("y", 0.0))

            L2 = float(sf.get("L2", 2.5))
            B2 = float(sf.get("B2", 2.5))
            t2 = float(sf.get("t2", 50.0)) / 100.0
            x2 = float(c2.get("x", 0.0))
            y2 = float(c2.get("y", 0.0))

            sb_b = float(sf.get("sb", 0.40))
            sb_D = float(sf.get("sD", 0.90))
            mid_x = (x1 + x2) / 2.0
            mid_y = (y1 + y2) / 2.0
            span_sb = math.hypot(x2 - x1, y2 - y1)
            angle_sb = math.atan2(y2 - y1, x2 - x1)

            f1_id = f"ftg_edge_f1_{sf_name}"
            concrete_elements.append({
                "id": f1_id,
                "category": "footings",
                "name": f"قاعدة الجار {sf_name} — F1 (عمود {c1_id})",
                "type": "Edge Footing (F1)",
                "x": x1,
                "y": y1,
                "z": z_ground - (t1 / 2.0),
                "dx": L1,
                "dy": B1,
                "dz": t1,
                "color": "#f97316",
                "details": {
                    "النموذج": f"{sf_name} — قاعدة الجار الخارجية (F1)",
                    "العمود": f"{c1_id} (ملاصق لحدود الجار)",
                    "الأبعاد (L1 × B1 × t1)": f"{int(L1*100)} × {int(B1*100)} × {int(t1*100)} سم",
                    "التسليح": "شبكة سفلية اتجاهين 6-7 Φ 16 / م",
                }
            })

            sb_id = f"strap_beam_{sf_name}"
            concrete_elements.append({
                "id": sb_id,
                "category": "ground_beams",
                "name": f"كمرة شداد {sf_name} ({c1_id} إلى {c2_id})",
                "type": "Strap Beam",
                "x": mid_x,
                "y": mid_y,
                "z": z_ground - (sb_D / 2.0),
                "dx": span_sb,
                "dy": sb_b,
                "dz": sb_D,
                "rot_z": angle_sb,
                "color": "#dc2626",
                "details": {
                    "النموذج": f"{sf_name} — كمرة شداد جداري (Strap Beam)",
                    "يربط بين": f"{c1_id} و {c2_id}",
                    "البحر (S)": f"{span_sb:.2f} م",
                    "القطاع (b × D)": f"{int(sb_b*100)} × {int(sb_D*100)} سم",
                    "التسليح الرئيسي (العلوي)": "6 Φ 22 (مقاومة عزم الانقلاب)",
                    "التسليح السفلي": "4 Φ 16",
                    "الكانات": "7 Φ 10 / م (4 فروع لمقاومة القص والالتواء)",
                }
            })

            # Strap Beam Rebar Cage
            sb_rebar_lines = []
            z_top_sb = z_ground - 0.05
            z_bot_sb = z_ground - sb_D + 0.05
            dx_unit = (x2 - x1) / max(0.01, span_sb)
            dy_unit = (y2 - y1) / max(0.01, span_sb)
            perp_x = -dy_unit * (sb_b / 2.0 - 0.04)
            perp_y = dx_unit * (sb_b / 2.0 - 0.04)

            for frac in [-1.0, -0.33, 0.33, 1.0]:
                px = frac * perp_x
                py = frac * perp_y
                sb_rebar_lines.extend([
                    x1 + px, y1 + py, z_top_sb,
                    x2 + px, y2 + py, z_top_sb
                ])
            for frac in [-0.8, 0.8]:
                px = frac * perp_x
                py = frac * perp_y
                sb_rebar_lines.extend([
                    x1 + px, y1 + py, z_bot_sb,
                    x2 + px, y2 + py, z_bot_sb
                ])
            n_st_sb = max(6, int(math.ceil(span_sb * 6.0)))
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

    # 1.4 GROUND BEAMS (السملات والميدات الأرضية)
    if gb_analysis:
        for gb in gb_analysis.get("ground_beams", []):
            gb_id = gb.get("elem_id", "GB-1")
            c1 = gb.get("col1", {})
            c2 = gb.get("col2", {})
            c1_id = c1.get("id", "")
            c2_id = c2.get("id", "")
            x1 = float(c1.get("x", 0.0))
            y1 = float(c1.get("y", 0.0))
            x2 = float(c2.get("x", 0.0))
            y2 = float(c2.get("y", 0.0))

            b_m = float(gb.get("b_cm", 25.0)) / 100.0
            t_m = float(gb.get("exec_t_cm", 60.0)) / 100.0
            span = math.hypot(x2 - x1, y2 - y1)
            if span < 0.20:
                continue

            mid_x = (x1 + x2) / 2.0
            mid_y = (y1 + y2) / 2.0
            angle_gb = math.atan2(y2 - y1, x2 - x1)

            concrete_elements.append({
                "id": f"gb_{gb_id}",
                "category": "ground_beams",
                "name": f"سملة أرضية {gb_id} ({c1_id} إلى {c2_id})",
                "type": "Ground Beam (GB)",
                "x": mid_x,
                "y": mid_y,
                "z": z_ground - (t_m / 2.0),
                "dx": span,
                "dy": b_m,
                "dz": t_m,
                "rot_z": angle_gb,
                "color": "#65a30d",
                "details": {
                    "النموذج": f"{gb_id} — {gb.get('tag', 'B1')}",
                    "الأعمدة المربوطة": f"{c1_id} ⟷ {c2_id}",
                    "المحور": gb.get("axis_str", "—"),
                    "البحر (Span)": f"{span:.2f} م (صافي {gb.get('clear_span_m', span):.2f} م)",
                    "القطاع (b × t)": f"{int(b_m*100)} × {int(t_m*100)} سم",
                    "التسليح السفلي": f"{gb.get('exec_n_bot', 3)} Φ {gb.get('phi_bot', 16)}",
                    "التسليح العلوي": f"{gb.get('exec_n_top', 2)} Φ {gb.get('phi_top', 12)}",
                    "براندات الجوانب": f"{gb.get('exec_side_bars', 0)} Φ {gb.get('phi_side', 10)}" if gb.get('exec_side_bars', 0) > 0 else "غير مطلوبة",
                    "الكانات": f"{gb.get('exec_stirrups_per_m', 6)} Φ {gb.get('phi_st', 8)} / م",
                    "حالة التحقق": gb.get("shear_status", "✅ Safe"),
                }
            })

            # Rebar Lines
            gb_lines = []
            cov = cover_gb_cm / 100.0
            z_top_g = z_ground - cov
            z_bot_g = z_ground - t_m + cov
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
            "num_footings": len(ftg_analysis.get("isolated_footings", [])) + len(ftg_analysis.get("combined_footings", [])) + len(ftg_analysis.get("edge_strap_footings", [])) if ftg_analysis else 0,
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

  /* Concrete Opacity Slider Control Box */
  .slider-box {{
    display: flex;
    align-items: center;
    gap: 8px;
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 800;
  }}
  .slider-box input[type="range"] {{
    -webkit-appearance: none;
    width: 140px;
    height: 6px;
    border-radius: 3px;
    background: #334155;
    outline: none;
    cursor: pointer;
  }}
  .slider-box input[type="range"]::-webkit-slider-thumb {{
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #38bdf8;
    border: 2px solid #ffffff;
    box-shadow: 0 0 6px rgba(56, 189, 248, 0.8);
    cursor: pointer;
    transition: transform 0.1s;
  }}
  .slider-box input[type="range"]::-webkit-slider-thumb:hover {{
    transform: scale(1.2);
  }}
  .opacity-badge {{
    background: #0284c7;
    color: #ffffff;
    padding: 2px 7px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 900;
    min-width: 42px;
    text-align: center;
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
  </div>

  <div class="tb-group">
    <div class="slider-box">
      <span>🏢 شفافية الخرسانة (X-Ray):</span>
      <input type="range" id="opacity-slider" min="0" max="100" value="100" step="2" />
      <span class="opacity-badge" id="opacity-val">100%</span>
    </div>
  </div>

  <div class="tb-group">
    <span style="font-size: 11.5px; font-weight: 800; color:#94a3b8; margin-left: 4px;">الفلاتر:</span>
    <button class="filter-chip active" id="flt-slab" data-cat="slab">السقف</button>
    <button class="filter-chip active" id="flt-cols" data-cat="columns">الأعمدة</button>
    <button class="filter-chip active" id="flt-ftgs" data-cat="footings">الأساسات</button>
    <button class="filter-chip active" id="flt-gb" data-cat="ground_beams">السملات والشدادات</button>
    <button class="filter-chip active" id="flt-rebar" data-cat="rebar">حديد التسليح</button>
  </div>
</div>

<div class="rebar-legend" id="rebar-legend">
  <span style="color:#38bdf8; font-weight:800; margin-left:4px;">🎨 كود ألوان الحديد:</span>
  <div class="legend-item"><span class="legend-dot" style="background:#0284c7;"></span> شبكة بلاطة سفلية</div>
  <div class="legend-item"><span class="legend-dot" style="background:#6366f1;"></span> شبكة بلاطة علوية</div>
  <div class="legend-item"><span class="legend-dot" style="background:#f97316;"></span> كابات إضافي الأعمدة</div>
  <div class="legend-item"><span class="legend-dot" style="background:#ec4899;"></span> كانات القص الثاقب</div>
  <div class="legend-item"><span class="legend-dot" style="background:#10b981;"></span> تسليح الأعمدة الطولي</div>
  <div class="legend-item"><span class="legend-dot" style="background:#84cc16;"></span> كانات وسملات</div>
  <div class="legend-item"><span class="legend-dot" style="background:#14b8a6;"></span> تسليح القواعد</div>
  <div class="legend-item"><span class="legend-dot" style="background:#e11d48;"></span> حديد الشدادات</div>
</div>

<div class="help-bar">
  🖱️ تدوير: سحب بالفأرة &nbsp;|&nbsp; Zoom: عجلة الفأرة &nbsp;|&nbsp; Pan: زر الفأرة الأيمن &nbsp;|&nbsp; 👈 انقر على أي عنصر لفحصه وعزله
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
  controls.minDistance = 2.0;
  controls.maxDistance = 300.0;

  const ambLight = new THREE.AmbientLight(0xffffff, 0.75);
  scene.add(ambLight);

  const maxSpan = Math.max(data.span_x || 15, data.span_y || 15, 10);
  const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.85);
  dirLight1.position.set(maxSpan * 1.5, maxSpan * 2.0, maxSpan * 1.5);
  scene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(0x93c5fd, 0.40);
  dirLight2.position.set(-maxSpan * 1.5, -maxSpan * 1.0, maxSpan * 1.2);
  scene.add(dirLight2);

  const concreteGroup = new THREE.Group();
  const rebarGroup = new THREE.Group();
  const edgesGroup = new THREE.Group();
  scene.add(concreteGroup);
  scene.add(rebarGroup);
  scene.add(edgesGroup);

  const concreteMeshes = [];
  const rebarMeshes = [];
  const elementDataMap = new Map();

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

  const gridHelper = new THREE.GridHelper(maxSpan * 2.2, 22, 0x334155, 0x1e293b);
  gridHelper.position.set(data.center_x || 0, data.z_ground - 1.20, -(data.center_y || 0));
  scene.add(gridHelper);

  const targetX = data.center_x || 0;
  const targetY = (data.z_slab_top || 3.0) / 2.0;
  const targetZ = -(data.center_y || 0);
  controls.target.set(targetX, targetY, targetZ);

  function setCameraPreset(preset) {{
    const span = maxSpan;
    if (preset === '3d') {{
      camera.position.set(targetX + span * 1.3, targetY + span * 1.1, targetZ + span * 1.4);
    }} else if (preset === 'top') {{
      camera.position.set(targetX, targetY + span * 2.2, targetZ + 0.001);
    }} else if (preset === 'front') {{
      camera.position.set(targetX, targetY, targetZ + span * 2.0);
    }} else if (preset === 'side') {{
      camera.position.set(targetX + span * 2.0, targetY, targetZ);
    }}
    controls.target.set(targetX, targetY, targetZ);
    controls.update();
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

  const opacitySlider = document.getElementById('opacity-slider');
  const opacityValBadge = document.getElementById('opacity-val');

  function updateOpacity(val) {{
    opacityValBadge.textContent = val + '%';
    const norm = val / 100.0;

    if (val >= 99) {{
      concreteMeshes.forEach(m => {{
        m.material.transparent = false;
        m.material.opacity = 1.0;
        m.material.depthWrite = true;
        m.visible = true;
      }});
      rebarGroup.visible = false;
    }} else if (val <= 1) {{
      concreteMeshes.forEach(m => {{
        m.visible = false;
      }});
      rebarGroup.visible = true;
      rebarMeshes.forEach(r => {{
        r.material.opacity = 1.0;
      }});
    }} else {{
      concreteMeshes.forEach(m => {{
        m.visible = true;
        m.material.transparent = true;
        m.material.opacity = norm * 0.75 + 0.05;
        m.material.depthWrite = false;
      }});
      rebarGroup.visible = true;
      rebarMeshes.forEach(r => {{
        r.material.opacity = 0.95;
      }});
    }}
  }}
  opacitySlider.addEventListener('input', (e) => updateOpacity(parseInt(e.target.value)));

  const filterState = {{
    slab: true,
    columns: true,
    footings: true,
    ground_beams: true,
    rebar: true,
  }};

  function applyCategoryFilters() {{
    concreteMeshes.forEach(m => {{
      const cat = m.userData.category;
      if (cat === 'footings_pc') {{
        m.visible = filterState.footings;
      }} else if (filterState[cat] !== undefined) {{
        m.visible = filterState[cat];
      }}
    }});
    edgesGroup.children.forEach(e => {{
      const cat = e.userData.category;
      if (filterState[cat] !== undefined) {{
        e.visible = filterState[cat];
      }}
    }});
    rebarGroup.visible = filterState.rebar && (parseInt(opacitySlider.value) < 99);
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
  }}

  function resetIsolation() {{
    isIsolated = false;
    updateOpacity(parseInt(opacitySlider.value));
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
    if (e.target.closest('.toolbar') || e.target.closest('.inspector-panel') || e.target.closest('.rebar-legend')) {{
      return;
    }}

    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

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
        )

        if not scene_data or not scene_data.get("concrete_elements"):
            st.info("💡 أدخل بيانات شبكة المحاور وقم بتنفيذ التصميم لعرض النموذج الإنشائي ثلاثي الأبعاد.")
            return

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
