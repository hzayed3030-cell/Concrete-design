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


# ═══════════════════════════════════════════════════════════════════════════════
# 1. NETWORK CONNECTIVITY & BEAM SEGMENT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

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
                "rft_top_str": f"{n_top} Φ 22",
                "rft_bot_str": f"{n_bot} Φ 16",
                "stirrups_str": f"{st_per_m} Φ 10 / m ({n_br} فروع)",
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
                "rft_top_str": f"{n_top} Φ 22",
                "rft_bot_str": f"{n_bot} Φ 16",
                "stirrups_str": f"{st_per_m} Φ 10 / m ({n_br} فروع)",
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
        })

    # ── Step D: AUTOMATIC GROUPING INTO 3 TYPES (B1, B2, B3) ───────────────────
    # Sort all analyzed beams in descending order based on structural demand
    analyzed_ground_beams.sort(key=lambda b: b["demand_score"], reverse=True)

    n_tot_gb = len(analyzed_ground_beams)
    group_assignments = {}  # elem_id -> "B1", "B2", or "B3"

    if n_tot_gb == 0:
        pass
    elif n_tot_gb == 1:
        group_assignments[analyzed_ground_beams[0]["elem_id"]] = "B1"
    elif n_tot_gb == 2:
        group_assignments[analyzed_ground_beams[0]["elem_id"]] = "B1"
        group_assignments[analyzed_ground_beams[1]["elem_id"]] = "B2"
    else:
        cut1 = int(math.ceil(n_tot_gb / 3.0))
        cut2 = int(math.ceil(2.0 * n_tot_gb / 3.0))
        for i, b in enumerate(analyzed_ground_beams):
            if i < cut1:
                group_assignments[b["elem_id"]] = "B1"
            elif i < cut2:
                group_assignments[b["elem_id"]] = "B2"
            else:
                group_assignments[b["elem_id"]] = "B3"

    # Compute Governing Envelope for each group
    models_dict = {}
    overrides = user_overrides or {}

    for mark, label in [
        ("B1", "B1 (Heavy — قطاع ثقيل لأعلى عزوم وبحور)"),
        ("B2", "B2 (Medium — قطاع متوسط للمتطلبات الإنشائية الوسطى)"),
        ("B3", "B3 (Light — قطاع خفيف للبحور القصيرة وقواطيع الحوائط)"),
    ]:
        grp_beams = [b for b in analyzed_ground_beams if group_assignments.get(b["elem_id"]) == mark]
        if not grp_beams:
            continue

        env_t = max(b["t_calc"] for b in grp_beams)
        env_t = float(math.ceil(env_t / 5.0) * 5.0)
        env_As_bot = max(b["As_bot_req"] for b in grp_beams)
        env_As_top = max(b["As_top_req"] for b in grp_beams)
        env_st_m = max(b["stirrups_per_m"] for b in grp_beams)
        env_branches = 4 if b_unified >= 40.0 else 2

        area_1bot = math.pi * ((phi_bot / 10.0) ** 2) / 4.0
        env_nbot = max(2, int(math.ceil(env_As_bot / max(0.01, area_1bot))))
        area_1top = math.pi * ((phi_top / 10.0) ** 2) / 4.0
        env_ntop = max(2, int(math.ceil(env_As_top / max(0.01, area_1top))))

        # Apply User Interactive Overrides if provided
        ov_t = float(overrides.get(f"{mark}_t", env_t))
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
            "n_branches": env_branches,
            "rft_bot_str": f"{ov_nbot} Φ {phi_bot}",
            "rft_top_str": f"{ov_ntop} Φ {phi_top}",
            "rft_side_str": f"{env_side_bars} Φ {phi_side} (براندات)" if env_side_bars > 0 else "—",
            "stirrups_str": f"{ov_st} Φ {phi_st} / m ({env_branches} فروع)",
            "dimensions_str": f"{int(b_unified)} × {int(ov_t)}",
        }

    # Assign Model Tag to Each Ground Beam
    for b in analyzed_ground_beams:
        b["model_mark"] = group_assignments.get(b["elem_id"], "B1")
        b["tag"] = b["model_mark"]
        m_info = models_dict.get(b["model_mark"], {})
        b["exec_t_cm"] = m_info.get("t_cm", b["t_calc"])
        b["exec_n_bot"] = m_info.get("n_bot", b["n_bot"])
        b["exec_n_top"] = m_info.get("n_top", b["n_top"])
        b["exec_stirrups_per_m"] = m_info.get("stirrups_per_m", b["stirrups_per_m"])
        b["exec_side_bars"] = m_info.get("total_side_bars", b["total_side_bars"])

    # ── Step E: Master Ground Beams Schedule Table ─────────────────────────────
    models_schedule = []
    for mark in ["B1", "B2", "B3"]:
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
            "Reinforcement Summary": f"سفلي: {gb['exec_n_bot']} Φ {gb['phi_bot']} | علوي: {gb['exec_n_top']} Φ {gb['phi_top']} | كانات: {gb['exec_stirrups_per_m']} Φ {gb['phi_st']}/m",
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
            "التسليح السفلي (Bottom Steel)": f"{gb['exec_n_bot']} Φ {gb['phi_bot']}",
            "التسليح العلوي (Top Steel)": f"{gb['exec_n_top']} Φ {gb['phi_top']}",
            "براندات الجوانب (Side Bars)": f"{gb['exec_side_bars']} Φ {gb['phi_side']}" if gb['exec_side_bars'] > 0 else "—",
            "الكانات (Stirrups)": f"{gb['exec_stirrups_per_m']} Φ {gb['phi_st']} / m",
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
