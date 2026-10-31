"""
modules/roof_beam_layout.py
================================================================================
Automated Roof Beams & Drop Beams (تصميم وتفريد ونماذج كمرات السقف والكوابيل)
Classification, Continuity Derivation, Structural Design, and 3-Model Grouping
Engine for Module 1 (ECP 203-2018).

Key Capabilities:
1. Coordinates & Connectivity Extraction:
   - Reads active columns and grid layout from Module 1.
   - Merges any existing custom drop beams from Drop Beams Engine.
   - Extracts orthogonal grid lines (X and Y directions) connecting columns.
   - Identifies cantilever zones (left, right, top, bottom) and generates
     cantilever beams (CB) extending to the slab edge.
2. Support Continuity Derivation (حالة الاستمرارية والدعم):
   - Simply Supported (حر من الطرفين) for 2-column line
   - Continuous from One End (مستمر من طرف واحد) for terminal spans of multi-column lines
   - Continuous from Both Ends (مستمر من الطرفين) for interior spans
   - Cantilever (كابولي) for cantilever beams with main top steel
3. Comprehensive Structural Design (per ECP 203):
   - Drop Beam Self-weight (stem below slab) + Tributary Slab Load (which already includes equivalent distributed wall load).
   - Bending moments (positive and negative), shear forces.
   - Recommended depth t_calc (deflection limit & flexure).
   - Bottom & top reinforcement, skin/shrinkage side bars (t >= 60 cm), stirrups.
4. Automatic Grouping into 3 Execution Models (B1, B2, B3) + Cantilevers (CB):
   - Sorts regular beams descending by structural demand.
   - Divides into B1 (Heavy), B2 (Medium), B3 (Light), plus CB (Cantilevers).
   - Applies Governing Envelope Rule (max t, max As_bot, max As_top, max stirrups).
   - Dynamic re-design when depth is modified by the user.
5. Bill of Quantities (BOQ):
   - Concrete volume, rebar weight by bar diameter, cement, sand, gravel.
================================================================================
"""

import math
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def extract_roof_beams_and_models(
    active_columns: list,
    drop_beams: list = None,
    cantilevers: dict = None,
    Lx_spans: list = None,
    Ly_spans: list = None,
    ts_cm: float = 20.0,
    Wu_slab: float = 1.45,
    Fcu: float = 250.0,
    Fy: float = 4000.0,
    b_unified: float = 25.0,
    has_wall: bool = False,
    h_wall: float = 0.0,
    t_wall: float = 0.0,
    gamma_brick: float = 1.80,
    phi_bot: int = 16,
    phi_top: int = 12,
    phi_st: int = 8,
    phi_side: int = 10,
    stirrups_per_m: int = 6,
    user_overrides: dict = None,
) -> dict:
    """
    Extracts, designs, and groups all roof beams and cantilevers in the building slab.
    """
    if not active_columns:
        return {
            "all_links": [],
            "roof_beams": [],
            "cantilever_beams": [],
            "models_schedule": [],
            "models_dict": {},
            "boq": {
                "conc_vol_rc": 0.0, "steel_kg_tot": 0.0, "steel_ton_tot": 0.0,
                "cement_ton": 0.0, "cement_bags": 0, "sand_m3": 0.0,
                "gravel_m3": 0.0, "dia_map": {}, "steel_ratio_kg_m3": 0.0,
            },
            "classification_rows": [],
            "detailed_schedule_rows": [],
        }

    cover_cm = 4.0
    fy_st = 2400.0 if phi_st <= 8 else 4000.0
    qcu = 0.75 * math.sqrt(max(1.0, Fcu) / 1.5)
    qu_max = 2.20 * math.sqrt(max(1.0, Fcu) / 1.5)
    area_1bot = math.pi * ((phi_bot / 10.0) ** 2) / 4.0
    area_1top = math.pi * ((phi_top / 10.0) ** 2) / 4.0
    area_1st = math.pi * ((phi_st / 10.0) ** 2) / 4.0
    n_branches = 4 if b_unified >= 40.0 else 2

    # ── Step A: Cluster Columns by Axes ──────────────────────────────────────
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

    raw_spans = []
    connected_pairs = set()

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
            if pair_key in connected_pairs:
                continue
            connected_pairs.add(pair_key)

            if m == 2:
                supp_cond = "Simply Supported (حر من الطرفين)"
            elif k == 0 or k == m - 2:
                supp_cond = "Continuous from One End (مستمر من طرف واحد)"
            else:
                supp_cond = "Continuous from Both Ends (مستمر من الطرفين)"

            S_m = math.dist((cA["x"], cA["y"]), (cB["x"], cB["y"]))
            if S_m > 9.0:
                continue

            colA_w = float(cA.get("width_m", cA.get("tc", 50.0) / 100.0))
            colB_w = float(cB.get("width_m", cB.get("tc", 50.0) / 100.0))
            Ln_m = max(0.40, S_m - (colA_w / 2.0 + colB_w / 2.0))
            axis_name = cA.get("grid_y", f"X-Line @ y={cA['y']:.2f}")

            raw_spans.append({
                "dir": "X",
                "col1": cA, "col2": cB,
                "col1_id": cA["id"], "col2_id": cB["id"],
                "axis_name": axis_name,
                "S_m": S_m, "Ln_m": Ln_m,
                "supp_cond": supp_cond,
                "is_cantilever": False,
                "p1": [cA["x"], cA["y"]],
                "p2": [cB["x"], cB["y"]],
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
            if pair_key in connected_pairs:
                continue
            connected_pairs.add(pair_key)

            if n == 2:
                supp_cond = "Simply Supported (حر من الطرفين)"
            elif k == 0 or k == n - 2:
                supp_cond = "Continuous from One End (مستمر من طرف واحد)"
            else:
                supp_cond = "Continuous from Both Ends (مستمر من الطرفين)"

            S_m = math.dist((cA["x"], cA["y"]), (cB["x"], cB["y"]))
            if S_m > 9.0:
                continue

            colA_h = float(cA.get("height_m", cA.get("bc", 30.0) / 100.0))
            colB_h = float(cB.get("height_m", cB.get("bc", 30.0) / 100.0))
            Ln_m = max(0.40, S_m - (colA_h / 2.0 + colB_h / 2.0))
            axis_name = cA.get("grid_x", f"Y-Line @ x={cA['x']:.2f}")

            raw_spans.append({
                "dir": "Y",
                "col1": cA, "col2": cB,
                "col1_id": cA["id"], "col2_id": cB["id"],
                "axis_name": axis_name,
                "S_m": S_m, "Ln_m": Ln_m,
                "supp_cond": supp_cond,
                "is_cantilever": False,
                "p1": [cA["x"], cA["y"]],
                "p2": [cB["x"], cB["y"]],
            })

    # 3. Add Cantilever Beams (كوابيل السقف) if cantilevers exist
    cant_dict = cantilevers or {}
    c_left = float(cant_dict.get("left", 0.0) or 0.0)
    c_right = float(cant_dict.get("right", 0.0) or 0.0)
    c_top = float(cant_dict.get("top", 0.0) or 0.0)
    c_bot = float(cant_dict.get("bottom", 0.0) or 0.0)

    xs_all = [c["x"] for c in active_columns]
    ys_all = [c["y"] for c in active_columns]
    min_x, max_x = min(xs_all), max(xs_all)
    min_y, max_y = min(ys_all), max(ys_all)

    # Cantilevers on Left
    if c_left > 0.25 and v_lines:
        left_cols = sorted(v_lines[0], key=lambda c: c["y"])
        for idx_cb, cA in enumerate(left_cols):
            raw_spans.append({
                "dir": "X-Cantilever",
                "col1": cA, "col2": {"id": f"Edge-L{idx_cb+1}", "x": cA["x"] - c_left, "y": cA["y"]},
                "col1_id": cA["id"], "col2_id": f"Edge-L{idx_cb+1}",
                "axis_name": f"كابولي أيسر ({cA.get('grid_y', '')})",
                "S_m": c_left, "Ln_m": max(0.30, c_left - 0.20),
                "supp_cond": "Cantilever (كابولي طرفي)",
                "is_cantilever": True,
                "p1": [cA["x"], cA["y"]],
                "p2": [cA["x"] - c_left, cA["y"]],
            })

    # Cantilevers on Right
    if c_right > 0.25 and v_lines:
        right_cols = sorted(v_lines[-1], key=lambda c: c["y"])
        for idx_cb, cA in enumerate(right_cols):
            raw_spans.append({
                "dir": "X-Cantilever",
                "col1": cA, "col2": {"id": f"Edge-R{idx_cb+1}", "x": cA["x"] + c_right, "y": cA["y"]},
                "col1_id": cA["id"], "col2_id": f"Edge-R{idx_cb+1}",
                "axis_name": f"كابولي أيمن ({cA.get('grid_y', '')})",
                "S_m": c_right, "Ln_m": max(0.30, c_right - 0.20),
                "supp_cond": "Cantilever (كابولي طرفي)",
                "is_cantilever": True,
                "p1": [cA["x"], cA["y"]],
                "p2": [cA["x"] + c_right, cA["y"]],
            })

    # Cantilevers on Top
    if c_top > 0.25 and h_lines:
        top_cols = sorted(h_lines[-1], key=lambda c: c["x"])
        for idx_cb, cA in enumerate(top_cols):
            raw_spans.append({
                "dir": "Y-Cantilever",
                "col1": cA, "col2": {"id": f"Edge-T{idx_cb+1}", "x": cA["x"], "y": cA["y"] + c_top},
                "col1_id": cA["id"], "col2_id": f"Edge-T{idx_cb+1}",
                "axis_name": f"كابولي علوي ({cA.get('grid_x', '')})",
                "S_m": c_top, "Ln_m": max(0.30, c_top - 0.20),
                "supp_cond": "Cantilever (كابولي طرفي)",
                "is_cantilever": True,
                "p1": [cA["x"], cA["y"]],
                "p2": [cA["x"], cA["y"] + c_top],
            })

    # Cantilevers on Bottom
    if c_bot > 0.25 and h_lines:
        bot_cols = sorted(h_lines[0], key=lambda c: c["x"])
        for idx_cb, cA in enumerate(bot_cols):
            raw_spans.append({
                "dir": "Y-Cantilever",
                "col1": cA, "col2": {"id": f"Edge-B{idx_cb+1}", "x": cA["x"], "y": cA["y"] - c_bot},
                "col1_id": cA["id"], "col2_id": f"Edge-B{idx_cb+1}",
                "axis_name": f"كابولي سفلي ({cA.get('grid_x', '')})",
                "S_m": c_bot, "Ln_m": max(0.30, c_bot - 0.20),
                "supp_cond": "Cantilever (كابولي طرفي)",
                "is_cantilever": True,
                "p1": [cA["x"], cA["y"]],
                "p2": [cA["x"], cA["y"] - c_bot],
            })

    # ── Step B: Structural Design of Each Beam ───────────────────────────────
    # Note: Flat slab Wu_slab already includes equivalent distributed wall load (1.4*WL).
    # Only drop beam stem self-weight below slab: (t - ts) * b * gamma_c is added.
    w_wall = 0.0

    analyzed_roof_beams = []
    for idx, sp in enumerate(raw_spans, start=1):
        cA = sp["col1"]
        cB = sp["col2"]
        S_m = sp["S_m"]
        Ln_m = sp["Ln_m"]
        supp_cond = sp["supp_cond"]
        is_cant = sp["is_cantilever"]

        # Tributary slab load width:
        # Cantilevers take average spacing of perimeter columns
        # Regular beams take tributary band (approx 1.5 - 2.5 m)
        if is_cant:
            w_trib = 2.0
            L_d_limit = 8.0
            coeff_pos = 0.0
            coeff_neg = 0.50
            coeff_V = 1.00
        elif "Simply Supported" in supp_cond or "حر" in supp_cond:
            w_trib = 2.0
            L_d_limit = 16.0
            coeff_pos = 1.0 / 8.0
            coeff_neg = 1.0 / 24.0
            coeff_V = 0.50
        elif "One End" in supp_cond or "طرف واحد" in supp_cond:
            w_trib = 2.2
            L_d_limit = 18.5
            coeff_pos = 1.0 / 10.0
            coeff_neg = 1.0 / 10.0
            coeff_V = 0.60
        else:
            w_trib = 2.5
            L_d_limit = 21.0
            coeff_pos = 1.0 / 12.0
            coeff_neg = 1.0 / 12.0
            coeff_V = 0.55

        d_trial_m = (S_m * 100.0 / L_d_limit - cover_cm) / 100.0
        L_des = min(S_m, Ln_m + max(0.20, d_trial_m)) if not is_cant else S_m

        t_trial = max(40.0, math.ceil((L_des * 100.0 / L_d_limit + cover_cm) / 5.0) * 5.0)
        t_drop_cm = max(0.0, t_trial - ts_cm)
        w_ow = (b_unified / 100.0) * (t_drop_cm / 100.0) * 2.50
        w_slab_load = Wu_slab * w_trib
        w_u = 1.4 * w_ow + w_slab_load

        P_parapet = (1.4 * 0.25) if is_cant else 0.0
        Mu_pos = coeff_pos * w_u * (L_des ** 2)
        Mu_neg = coeff_neg * w_u * (L_des ** 2) + P_parapet * L_des
        Qu = coeff_V * w_u * L_des + P_parapet

        # Required depth t_calc
        d_defl = (L_des * 100.0) / L_d_limit
        d_flex = 3.50 * math.sqrt((max(Mu_pos, Mu_neg) * 100000.0) / (max(1.0, Fcu) * b_unified)) if max(Mu_pos, Mu_neg) > 0 else 25.0
        t_calc = float(math.ceil(max(d_defl + cover_cm, d_flex + cover_cm, 40.0) / 5.0) * 5.0)

        # Preliminary rebar design
        d_exec = max(10.0, t_calc - cover_cm)
        M_gov = Mu_neg if is_cant else Mu_pos
        denom = math.sqrt((M_gov * 100000.0) / (max(1.0, Fcu) * b_unified)) if M_gov > 0 else 1.0
        C1 = d_exec / denom if denom > 0 else 5.0
        if C1 >= 4.85:
            J = 0.826
        elif C1 < 2.78:
            J = 0.670
        else:
            term = max(0.0, 1.0 - (2.0 * M_gov * 100000.0) / (0.85 * Fcu * b_unified * (d_exec ** 2)))
            cd_ratio = (1.0 - math.sqrt(term)) / 0.80
            J = min(0.826, max(0.67, 1.0 - 0.40 * cd_ratio))

        As_min = max(0.0015 * b_unified * d_exec, (1.1 / Fy) * b_unified * d_exec)

        if is_cant:
            As_top_flex = (Mu_neg * 100000.0) / (Fy * J * d_exec) if (Fy * J * d_exec) > 0 else 0.0
            As_top_req = max(As_top_flex, As_min)
            As_bot_req = max(0.20 * As_top_req, 0.0015 * b_unified * d_exec)
        else:
            As_bot_flex = (Mu_pos * 100000.0) / (Fy * J * d_exec) if (Fy * J * d_exec) > 0 else 0.0
            As_bot_req = max(As_bot_flex, As_min)
            As_top_flex = (Mu_neg * 100000.0) / (Fy * 0.826 * d_exec) if (Fy * 0.826 * d_exec) > 0 else 0.0
            As_top_req = max(As_top_flex, max(0.20 * As_bot_req, 0.0015 * b_unified * d_exec))

        n_bot = max(2, int(math.ceil(As_bot_req / max(0.01, area_1bot))))
        n_top = max(2, int(math.ceil(As_top_req / max(0.01, area_1top))))

        if t_calc >= 60.0:
            side_spaces = math.ceil((t_calc - 2.0 * cover_cm) / 30.0)
            n_side_rows = max(1, side_spaces - 1)
        else:
            n_side_rows = 0
        total_side_bars = 2 * n_side_rows

        qu = (Qu * 1000.0) / (b_unified * d_exec) if (b_unified * d_exec) > 0 else 0.0
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

        demand_score = round(max(Mu_pos, Mu_neg) * 10.0 + max(As_bot_req, As_top_req) * (t_calc / 10.0), 2)

        elem_prefix = "CB" if is_cant else "RB"
        col1_id_str = str(cA.get("id", ""))
        col2_id_str = str(cB.get("id", ""))
        col_str = f"{col1_id_str} ⟷ {col2_id_str}"

        analyzed_roof_beams.append({
            "elem_id": f"{elem_prefix}-{idx}",
            "beam_id": f"{elem_prefix}-{idx}",
            "dir": sp["dir"],
            "col1_id": col1_id_str, "col2_id": col2_id_str,
            "col1": cA, "col2": cB,
            "axis_name": sp["axis_name"],
            "col_str": col_str,
            "span_m": S_m, "clear_span_m": Ln_m,
            "L_des": L_des, "supp_cond": supp_cond,
            "is_cantilever": is_cant,
            "w_trib": w_trib, "w_wall": w_wall,
            "coeff_pos": coeff_pos, "coeff_neg": coeff_neg, "coeff_V": coeff_V,
            "P_parapet": P_parapet,
            "b_cm": b_unified, "t_calc": t_calc,
            "Mu_pos": Mu_pos, "Mu_neg": Mu_neg, "Qu": Qu,
            "As_bot_req": As_bot_req, "As_top_req": As_top_req,
            "n_bot": n_bot, "phi_bot": phi_bot,
            "n_top": n_top, "phi_top": phi_top,
            "total_side_bars": total_side_bars, "phi_side": phi_side,
            "stirrups_per_m": st_req_per_m, "phi_st": phi_st,
            "n_branches": n_branches,
            "demand_score": demand_score,
            "shear_status": shear_status,
            "p1": sp["p1"], "p2": sp["p2"],
        })

    # ── Step C: Grouping into 3 Models (B1, B2, B3) + Cantilevers (CB1) ─────
    reg_beams = [b for b in analyzed_roof_beams if not b["is_cantilever"]]
    cant_beams = [b for b in analyzed_roof_beams if b["is_cantilever"]]

    # Sort regular beams by structural demand
    reg_beams.sort(key=lambda b: b["demand_score"], reverse=True)
    n_reg = len(reg_beams)
    group_assignments = {}

    if n_reg == 0:
        pass
    elif n_reg == 1:
        group_assignments[reg_beams[0]["elem_id"]] = "B1"
    elif n_reg == 2:
        group_assignments[reg_beams[0]["elem_id"]] = "B1"
        group_assignments[reg_beams[1]["elem_id"]] = "B2"
    else:
        cut1 = int(math.ceil(n_reg / 3.0))
        cut2 = int(math.ceil(2.0 * n_reg / 3.0))
        for i, b in enumerate(reg_beams):
            if i < cut1:
                group_assignments[b["elem_id"]] = "B1"
            elif i < cut2:
                group_assignments[b["elem_id"]] = "B2"
            else:
                group_assignments[b["elem_id"]] = "B3"

    for cb in cant_beams:
        group_assignments[cb["elem_id"]] = "CB1"

    # Compute Governing Envelopes & Apply Dynamic Overrides
    models_dict = {}
    overrides = user_overrides or {}

    model_categories = [
        ("B1", "B1 (Heavy — قطاع ثقيل لأعلى عزوم وبحور سقف)"),
        ("B2", "B2 (Medium — قطاع متوسط للبحور المعتدلة بالسقف)"),
        ("B3", "B3 (Light — قطاع خفيف للبحور القصيرة وقواطيع المباني)"),
    ]
    if cant_beams:
        model_categories.append(("CB1", "CB1 (Cantilever — كمرات كابولية بأعلى عزوم سالبة وشوك علوية)"))

    for mark, label in model_categories:
        grp_beams = [b for b in analyzed_roof_beams if group_assignments.get(b["elem_id"]) == mark]
        if not grp_beams:
            continue

        env_t = max(b["t_calc"] for b in grp_beams)
        env_t = float(math.ceil(env_t / 5.0) * 5.0)
        ov_t = float(overrides.get(f"{mark}_t", env_t))

        # Dynamic Recalculation for each beam with depth ov_t
        for b in grp_beams:
            d_exec = max(10.0, ov_t - cover_cm)
            t_drop_exec_cm = max(0.0, ov_t - ts_cm)
            w_ow = (b_unified / 100.0) * (t_drop_exec_cm / 100.0) * 2.50
            w_u_recalc = 1.4 * w_ow + (Wu_slab * b["w_trib"])
            L_des = b["L_des"]

            Mu_pos = b["coeff_pos"] * w_u_recalc * (L_des ** 2)
            Mu_neg = b["coeff_neg"] * w_u_recalc * (L_des ** 2) + b["P_parapet"] * L_des
            Qu = b["coeff_V"] * w_u_recalc * L_des + b["P_parapet"]

            M_gov = Mu_neg if b["is_cantilever"] else Mu_pos
            denom = math.sqrt((M_gov * 100000.0) / (max(1.0, Fcu) * b_unified)) if M_gov > 0 else 1.0
            C1 = d_exec / denom if denom > 0 else 5.0
            if C1 >= 4.85:
                J = 0.826
            elif C1 < 2.78:
                J = 0.670
            else:
                term = max(0.0, 1.0 - (2.0 * M_gov * 100000.0) / (0.85 * Fcu * b_unified * (d_exec ** 2)))
                cd_ratio = (1.0 - math.sqrt(term)) / 0.80
                J = min(0.826, max(0.67, 1.0 - 0.40 * cd_ratio))

            As_min = max(0.0015 * b_unified * d_exec, (1.1 / Fy) * b_unified * d_exec)

            if b["is_cantilever"]:
                As_top_flex = (Mu_neg * 100000.0) / (Fy * J * d_exec) if (Fy * J * d_exec) > 0 else 0.0
                As_top_req = max(As_top_flex, As_min)
                As_bot_req = max(0.20 * As_top_req, 0.0015 * b_unified * d_exec)
            else:
                As_bot_flex = (Mu_pos * 100000.0) / (Fy * J * d_exec) if (Fy * J * d_exec) > 0 else 0.0
                As_bot_req = max(As_bot_flex, As_min)
                As_top_flex = (Mu_neg * 100000.0) / (Fy * 0.826 * d_exec) if (Fy * 0.826 * d_exec) > 0 else 0.0
                As_top_req = max(As_top_flex, max(0.20 * As_bot_req, 0.0015 * b_unified * d_exec))

            qu = (Qu * 1000.0) / (b_unified * d_exec) if (b_unified * d_exec) > 0 else 0.0
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

            n_bot_beam = max(2, int(math.ceil(As_bot_req / max(0.01, area_1bot))))
            n_top_beam = max(2, int(math.ceil(As_top_req / max(0.01, area_1top))))

            b["Mu_pos"] = Mu_pos
            b["Mu_neg"] = Mu_neg
            b["Qu"] = Qu
            b["As_bot_req"] = As_bot_req
            b["As_top_req"] = As_top_req
            b["n_bot"] = n_bot_beam
            b["n_top"] = n_top_beam
            b["stirrups_per_m"] = st_req_per_m
            b["shear_status"] = shear_status

        # Governing Envelope
        env_As_bot = max(b["As_bot_req"] for b in grp_beams)
        env_As_top = max(b["As_top_req"] for b in grp_beams)
        env_st_m = max(b["stirrups_per_m"] for b in grp_beams)

        env_nbot = max(2, int(math.ceil(env_As_bot / max(0.01, area_1bot))))
        env_ntop = max(2, int(math.ceil(env_As_top / max(0.01, area_1top))))

        ov_nbot = int(overrides.get(f"{mark}_nbot", env_nbot))
        ov_ntop = int(overrides.get(f"{mark}_ntop", env_ntop))
        ov_st = int(overrides.get(f"{mark}_stirrups", env_st_m))

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
            "phi_bot": phi_bot,
            "n_top": ov_ntop,
            "phi_top": phi_top,
            "total_side_bars": env_side_bars,
            "phi_side": phi_side,
            "stirrups_per_m": ov_st,
            "phi_st": phi_st,
            "n_branches": n_branches,
            "rft_bot_str": f"{ov_nbot}Ø{phi_bot}",
            "rft_top_str": f"{ov_ntop}Ø{phi_top}",
            "rft_side_str": f"{env_side_bars}Ø{phi_side} (براندات)" if env_side_bars > 0 else "—",
            "stirrups_str": f"{ov_st}Ø{phi_st}/m ({n_branches} فروع)",
            "dimensions_str": f"{int(b_unified)} × {int(ov_t)}",
            "is_cantilever": (mark == "CB1"),
        }

    # Assign Model Tag to Each Beam
    for b in analyzed_roof_beams:
        b["model_mark"] = group_assignments.get(b["elem_id"], "B1")
        b["tag"] = b["model_mark"]
        m_info = models_dict.get(b["model_mark"], {})
        b["exec_t_cm"] = m_info.get("t_cm", b["t_calc"])
        b["exec_n_bot"] = m_info.get("n_bot", b["n_bot"])
        b["exec_n_top"] = m_info.get("n_top", b["n_top"])
        b["exec_stirrups_per_m"] = m_info.get("stirrups_per_m", b["stirrups_per_m"])
        b["exec_side_bars"] = m_info.get("total_side_bars", 0)

    # ── Step D: Master Roof Beams Schedule ────────────────────────────────────
    models_schedule = []
    for mark in ["B1", "B2", "B3", "CB1"]:
        if mark in models_dict:
            m = models_dict[mark]
            models_schedule.append({
                "النموذج (Mark)": m["mark"],
                "التصنيف والأهمية الإنشائية": m["label"].split("—")[1].strip(" )") if "—" in m["label"] else m["label"],
                "الأبعاد b × t (cm)": m["dimensions_str"],
                "التسليح السفلي (Bottom Rft)": m["rft_bot_str"],
                "التسليح العلوي / الشوك (Top Rft)": m["rft_top_str"],
                "براندات الانكماش (Side Bars)": m["rft_side_str"],
                "الكانات (Stirrups)": m["stirrups_str"],
                "العدد بالمشروع (Count)": f"{m['count']} كمرة",
                "إجمالي الأطوال (Total Length)": f"{m['total_len_m']:.2f} m",
            })

    # ── Step E: Classification Table ──────────────────────────────────────────
    classification_rows = []
    for rb in analyzed_roof_beams:
        rft_str = f"سفلي: {rb['exec_n_bot']}Ø{rb['phi_bot']} | علوي: {rb['exec_n_top']}Ø{rb['phi_top']} | كانات: {rb['exec_stirrups_per_m']}Ø{rb['phi_st']}/m"
        if rb.get("exec_side_bars", 0) > 0:
            rft_str += f" | براندات: {rb['exec_side_bars']}Ø{rb['phi_side']}"

        forces_str = f"Mu- = {rb['Mu_neg']:.2f} t.m | Qu = {rb['Qu']:.2f} t" if rb["is_cantilever"] else f"Mu+ = {rb['Mu_pos']:.2f} t.m | Qu = {rb['Qu']:.2f} t"
        type_str = "Cantilever Beam (كمرة كابولية — نموذج CB1)" if rb["is_cantilever"] else f"Roof Drop Beam (كمرة سقف ساقطة — نموذج {rb['tag']})"

        classification_rows.append({
            "Element ID": rb["elem_id"],
            "Tag / Mark": rb["tag"],
            "Type (التصنيف الإنشائي)": type_str,
            "From Column — To Column": rb["col_str"],
            "Axis / Location": rb["axis_name"],
            "Span L (m)": f"{rb['span_m']:.2f} m (صافي {rb['clear_span_m']:.2f}m)",
            "Cross-Section (b × t)": f"{int(rb['b_cm'])} × {int(rb['exec_t_cm'])}",
            "Structural Behavior / Notes": rb["supp_cond"],
            "Design Capacity / Forces": forces_str,
            "Reinforcement Summary": rft_str,
        })

    # ── Step F: Detailed Bar Bending Schedule ─────────────────────────────────
    detailed_schedule_rows = []
    for rb in analyzed_roof_beams:
        forces_str = f"Mu- = {rb['Mu_neg']:.2f}" if rb["is_cantilever"] else f"Mu+ = {rb['Mu_pos']:.2f}"
        detailed_schedule_rows.append({
            "الكمرة (ID)": rb["elem_id"],
            "النموذج (Mark)": rb["tag"],
            "المحور / الموقع": rb["axis_name"],
            "الأعمدة / الركائز": rb["col_str"],
            "البحر S (m)": f"{rb['span_m']:.2f}",
            "البحر الصافي Ln (m)": f"{rb['clear_span_m']:.2f}",
            "القطاع b × t (cm)": f"{int(rb['b_cm'])} × {int(rb['exec_t_cm'])}",
            "حالة الاستمرارية": rb["supp_cond"].split("(")[0].strip(),
            "عزم التصميم Mu (t.m)": forces_str,
            "قوة القص Qu (ton)": f"{rb['Qu']:.2f}",
            "التسليح السفلي (Bottom Steel)": f"{rb['exec_n_bot']}Ø{rb['phi_bot']}",
            "التسليح العلوي (Top Steel)": f"{rb['exec_n_top']}Ø{rb['phi_top']}",
            "براندات الجوانب (Side Bars)": f"{rb['exec_side_bars']}Ø{rb['phi_side']}" if rb.get('exec_side_bars', 0) > 0 else "—",
            "الكانات (Stirrups)": f"{rb['exec_stirrups_per_m']}Ø{rb['phi_st']}/m",
            "حالة التحقق (Status)": rb["shear_status"],
        })

    # ── Step G: BOQ for Roof Beams ───────────────────────────────────────────
    conc_vol_rc = 0.0
    steel_kg_tot = 0.0
    dia_map = {}

    def _add_dia_wt(d_mm, wt_kg, app_desc):
        if wt_kg <= 0:
            return
        if d_mm not in dia_map:
            dia_map[d_mm] = {"weight_kg": 0.0, "apps": app_desc}
        dia_map[d_mm]["weight_kg"] += wt_kg

    for rb in analyzed_roof_beams:
        b_m = rb["b_cm"] / 100.0
        t_m = rb["exec_t_cm"] / 100.0
        L_m = rb["span_m"]
        v_b = b_m * t_m * L_m
        conc_vol_rc += v_b

        # Steel weights
        L_bar_bot = L_m + 2.0 * max(0.40, (50.0 * rb["phi_bot"]) / 1000.0)
        wt_bot = rb["exec_n_bot"] * L_bar_bot * ((rb["phi_bot"] ** 2) / 162.0)

        # Cantilevers top steel extends into backspan (1.5 times cantilever span)
        L_bar_top = (2.5 * L_m + 0.50) if rb["is_cantilever"] else (L_m + 2.0 * max(0.40, (50.0 * rb["phi_top"]) / 1000.0))
        wt_top = rb["exec_n_top"] * L_bar_top * ((rb["phi_top"] ** 2) / 162.0)

        wt_side = 0.0
        if rb["exec_side_bars"] > 0:
            L_bar_side = L_m + 0.30
            wt_side = rb["exec_side_bars"] * L_bar_side * ((rb["phi_side"] ** 2) / 162.0)

        st_w_m = (rb["b_cm"] - 2.0 * cover_cm) / 100.0
        st_h_m = (rb["exec_t_cm"] - 2.0 * cover_cm) / 100.0
        st_perim = 2.0 * (st_w_m + st_h_m) + 0.15
        if rb["n_branches"] == 4:
            st_perim *= 2.0
        n_st = max(5, int(math.ceil(rb["exec_stirrups_per_m"] * L_m)))
        wt_st = n_st * st_perim * ((rb["phi_st"] ** 2) / 162.0)

        wt_b_tot = wt_bot + wt_top + wt_side + wt_st
        steel_kg_tot += wt_b_tot

        _add_dia_wt(rb["phi_bot"], wt_bot, "تسليح سفلي رئيسي لكمرات السقف (Roof Beams Bottom Rebar)")
        _add_dia_wt(rb["phi_top"], wt_top, "تسليح علوي وشوك كمرات السقف (Roof Beams Top Rebar / Cantilever Shok)")
        if wt_side > 0:
            _add_dia_wt(rb["phi_side"], wt_side, "براندات انكماش جانبية لكمرات السقف (Roof Beams Side Shrinkage)")
        _add_dia_wt(rb["phi_st"], wt_st, "كانات كمرات السقف (Roof Beams Stirrups)")

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
        "roof_beams": [b for b in analyzed_roof_beams if not b["is_cantilever"]],
        "cantilever_beams": [b for b in analyzed_roof_beams if b["is_cantilever"]],
        "all_roof_beams": analyzed_roof_beams,
        "models_schedule": models_schedule,
        "models_dict": models_dict,
        "boq": boq,
        "classification_rows": classification_rows,
        "detailed_schedule_rows": detailed_schedule_rows,
    }


def draw_roof_beams_layout_sketch(
    active_columns: list,
    roof_beams_analysis: dict,
    slab_bounds: dict = None,
    title: str = "ECP 203 — Roof Drop Beams & Cantilevers Layout Plan Sketch",
):
    """
    Renders comprehensive 2D roof beams and cantilevers plan sketch:
    - Soft Emerald Green (#15803d): B1 Heavy Roof Beams
    - Light Sky Blue (#0284c7): B2 Medium Roof Beams
    - Soft Indigo/Purple (#7e22ce): B3 Light Roof Beams
    - Warm Coral/Orange (#ea580c): CB1 Cantilever Beams with top shok rebar
    - Slab boundary and grid lines with dimension bubbles.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, ax = plt.subplots(figsize=(15, 12), dpi=160, facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")

    if not active_columns:
        ax.text(0.5, 0.5, "No Active Columns Found", ha="center", va="center", fontsize=14)
        return fig

    xs = sorted(list(set(round(c["x"], 2) for c in active_columns)))
    ys = sorted(list(set(round(c["y"], 2) for c in active_columns)))

    unique_xs = []
    for x in xs:
        if not unique_xs or abs(x - unique_xs[-1]) > 0.35:
            unique_xs.append(x)
    unique_ys = []
    for y in ys:
        if not unique_ys or abs(y - unique_ys[-1]) > 0.35:
            unique_ys.append(y)

    min_x = min(c["x"] for c in active_columns) - 1.5
    max_x = max(c["x"] for c in active_columns) + 1.5
    min_y = min(c["y"] for c in active_columns) - 1.5
    max_y = max(c["y"] for c in active_columns) + 1.5

    if slab_bounds:
        min_x = min(min_x, float(slab_bounds.get("min_x", min_x)) - float(slab_bounds.get("cant_left", 0.0) or 0.0) - 1.0)
        max_x = max(max_x, float(slab_bounds.get("max_x", max_x)) + float(slab_bounds.get("cant_right", 0.0) or 0.0) + 1.0)
        min_y = min(min_y, float(slab_bounds.get("min_y", min_y)) - float(slab_bounds.get("cant_bottom", 0.0) or 0.0) - 1.0)
        max_y = max(max_y, float(slab_bounds.get("max_y", max_y)) + float(slab_bounds.get("cant_top", 0.0) or 0.0) + 1.0)

    # 1. Draw Slab Boundary Outline
    if slab_bounds:
        sb_x0 = float(slab_bounds.get("min_x", 0.0)) - float(slab_bounds.get("cant_left", 0.0) or 0.0)
        sb_x1 = float(slab_bounds.get("max_x", 0.0)) + float(slab_bounds.get("cant_right", 0.0) or 0.0)
        sb_y0 = float(slab_bounds.get("min_y", 0.0)) - float(slab_bounds.get("cant_bottom", 0.0) or 0.0)
        sb_y1 = float(slab_bounds.get("max_y", 0.0)) + float(slab_bounds.get("cant_top", 0.0) or 0.0)
        sb_w = sb_x1 - sb_x0
        sb_h = sb_y1 - sb_y0
        if sb_w > 0 and sb_h > 0:
            slab_rect = patches.Rectangle(
                (sb_x0, sb_y0), sb_w, sb_h,
                facecolor="#f1f5f9", edgecolor="#64748b", lw=1.8, ls="--", alpha=0.55, zorder=1
            )
            ax.add_patch(slab_rect)
            ax.text(
                sb_x0 + 0.3, sb_y1 - 0.4, "Slab Boundary / محيط البلاطة والكوابيل",
                fontsize=8.5, color="#64748b", fontweight="bold", zorder=2
            )

    # 2. Draw Grid lines & Bubbles
    y_bubble = max_y + 1.3
    x_bubble = min_x - 1.3
    for idx, gx in enumerate(unique_xs, 1):
        ax.plot([gx, gx], [min_y - 0.5, y_bubble], color="#94a3b8", ls="--", lw=1.1, zorder=1)
        ax.text(gx, y_bubble, f"Y{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=10,
                bbox=dict(boxstyle="circle,pad=0.28", fc="#f8fafc", ec="#334155", lw=1.4), zorder=8)

    for idx, gy in enumerate(unique_ys, 1):
        ax.plot([x_bubble, max_x + 0.5], [gy, gy], color="#94a3b8", ls="--", lw=1.1, zorder=1)
        ax.text(x_bubble, gy, f"X{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=10,
                bbox=dict(boxstyle="circle,pad=0.28", fc="#f8fafc", ec="#334155", lw=1.4), zorder=8)

    # 3. Draw Beams
    color_map = {
        "B1": {"fc": "#dcfce7", "ec": "#15803d", "tc": "#14532d", "hatch": None},
        "B2": {"fc": "#e0f2fe", "ec": "#0284c7", "tc": "#0369a1", "hatch": None},
        "B3": {"fc": "#f3e8ff", "ec": "#7e22ce", "tc": "#581c87", "hatch": None},
        "CB1": {"fc": "#ffedd5", "ec": "#ea580c", "tc": "#9a3412", "hatch": "///"},
    }

    all_beams = roof_beams_analysis.get("all_roof_beams", [])
    for b in all_beams:
        p1 = b["p1"]
        p2 = b["p2"]
        bw_m = float(b.get("b_cm", 25.0)) / 100.0
        t_cm = int(b.get("exec_t_cm", b.get("t_calc", 50.0)))
        b_cm = int(b.get("b_cm", 25.0))
        tag = b.get("tag", "B1")
        cfg = color_map.get(tag, color_map["B1"])

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        if abs(dx) >= abs(dy):
            bx0 = min(p1[0], p2[0])
            bw = abs(dx)
            by0 = p1[1] - bw_m / 2.0
            rect = patches.Rectangle(
                (bx0, by0), bw, bw_m,
                facecolor=cfg["fc"], edgecolor=cfg["ec"], hatch=cfg["hatch"], lw=1.8, alpha=0.92, zorder=3
            )
            ax.add_patch(rect)
            mid_x = bx0 + bw / 2.0
            mid_y = by0 + bw_m / 2.0
            rot = 0
        else:
            by0 = min(p1[1], p2[1])
            bh = abs(dy)
            bx0 = p1[0] - bw_m / 2.0
            rect = patches.Rectangle(
                (bx0, by0), bw_m, bh,
                facecolor=cfg["fc"], edgecolor=cfg["ec"], hatch=cfg["hatch"], lw=1.8, alpha=0.92, zorder=3
            )
            ax.add_patch(rect)
            mid_x = bx0 + bw_m / 2.0
            mid_y = by0 + bh / 2.0
            rot = 90

        if b.get("is_cantilever"):
            lbl = f"{tag} ({b_cm}×{t_cm})\n{b.get('exec_n_top', 2)}Ø{b.get('phi_top', 12)} شوك"
        else:
            lbl = f"{tag} ({b_cm}×{t_cm})\n{b.get('exec_n_bot', 2)}Ø{b.get('phi_bot', 16)} / {b.get('exec_n_top', 2)}Ø{b.get('phi_top', 12)}"
            if b.get("exec_side_bars", 0) > 0:
                lbl += f"\n+{b['exec_side_bars']}Ø{b.get('phi_side', 10)}"

        ax.text(
            mid_x, mid_y, lbl,
            ha="center", va="center", rotation=rot, fontsize=7.2, fontweight="bold", color=cfg["tc"],
            bbox=dict(boxstyle="round,pad=0.10", fc="#ffffff", ec=cfg["ec"], lw=0.8, alpha=0.88),
            zorder=6
        )

    # 4. Draw Columns
    for c in active_columns:
        w_m = float(c.get("width_m", 0.30))
        h_m = float(c.get("height_m", 0.60))
        cx = float(c["x"])
        cy = float(c["y"])
        col_r = patches.Rectangle(
            (cx - w_m / 2.0, cy - h_m / 2.0), w_m, h_m,
            facecolor="#1e293b", edgecolor="#0f172a", lw=1.5, zorder=5
        )
        ax.add_patch(col_r)
        ax.text(
            cx, cy, c.get("orig_id", c.get("id", "C")),
            ha="center", va="center", color="#ffffff", fontweight="bold", fontsize=8, zorder=7
        )

    # 5. Legend Box
    models_dict = roof_beams_analysis.get("models_dict", {})
    leg_lines = ["دليل نماذج كمرات السقف (Models Legend):"]
    for mk in ["B1", "B2", "B3", "CB1"]:
        if mk in models_dict:
            m = models_dict[mk]
            leg_lines.append(f"• {mk}: {m['dimensions_str']} cm | {m['rft_bot_str']} / {m['rft_top_str']} ({m['count']} كمرة)")
    leg_text = "\n".join(leg_lines)
    ax.text(
        0.02, 0.02, leg_text, transform=ax.transAxes,
        fontsize=8.5, fontweight="bold", color="#1e293b", va="bottom", ha="left",
        bbox=dict(boxstyle="round,pad=0.4", fc="#ffffff", ec="#cbd5e1", lw=1.2, alpha=0.92),
        zorder=9
    )

    ax.set_xlim(min_x - 1.8, max_x + 1.8)
    ax.set_ylim(min_y - 1.2, max_y + 2.0)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(title, fontsize=13, fontweight="bold", color="#0f172a", pad=20)
    return fig
