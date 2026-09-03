"""
Module 7 – Combined Footing Design & Building Foundations
ECP 203 – Egyptian Code of Practice for RC Structures
═══════════════════════════════════════════════════════
Full Building Foundations System linked with Module 1 (Flat Slabs)
- Automated Data Pipeline from Module 1 (Pu total int / edge / corner)
- Typical Footings Unification (F1 Corner, F2 Edge, F3 Interior)
- Clearance & Overlap Engine (Clearance = S - (La/2 + Lb/2))
- Matplotlib Full Foundation Layout Plan with Red Warning Overlaps
- Dynamic Streamlit Tabs:
  Tab 1: Isolated Footings Schedule (9 columns)
  Tab 2: Combined Footings Schedule (8 columns) - Dynamic on overlap
Units strictly in Metric Engineering Units: ton · kg · cm · m · kg/cm² · ton·m · kN
"""
import math
import io
import base64
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from modules import settings as S
from modules.table_styler import render_styled_table


# ═══════════════════════════════════════════════════════════════════════════════
#  1. CORE UTILITY HELPERS (kg · cm · ton · m · kN)
# ═══════════════════════════════════════════════════════════════════════════════

def _r5(v_cm):
    """Round UP to nearest 5 cm."""
    return int(math.ceil(float(v_cm) / 5.0) * 5)


def _shear_allow_kgcm2(Fcu):
    """One-way shear allowable stress in kg/cm² (ECP 203: 0.16*sqrt(Fcu))."""
    return 0.16 * math.sqrt(Fcu)


def _punch_allow_kgcm2(Fcu, c_cm, b_cm, d_cm, bo_cm):
    """Punching shear allowable stress in kg/cm² (ECP 203 — min of 4 criteria)."""
    sq = math.sqrt(Fcu)
    a_col = min(c_cm, b_cm)
    b_col = max(c_cm, b_cm)
    ratio = a_col / b_col if b_col > 0 else 1.0

    q1 = 0.316 * (0.50 + ratio) * sq
    alpha = 4.0  # interior column
    q2 = 0.8 * (alpha * d_cm / bo_cm + 0.2) * sq if bo_cm > 0 else 999.0
    q3 = 0.316 * sq
    q4 = 17.0  # kg/cm² cap (1.7 MPa)

    return min(q1, q2, q3, q4)


def _As_design_cm2(Mu_kgcm, d_cm, b_cm, Fcu, Fy):
    """Required steel area (cm²) by Whitney stress block with 0.15% minimum."""
    if Mu_kgcm <= 0 or d_cm <= 0 or b_cm <= 0:
        return 0.0015 * b_cm * d_cm

    a = 0.10 * d_cm
    for _ in range(30):
        lever = d_cm - a / 2.0
        if lever <= 0:
            lever = 0.50 * d_cm
        As = Mu_kgcm / (0.9 * Fy * lever)
        a = (As * Fy) / (0.85 * Fcu * b_cm) if (Fcu * b_cm) > 0 else 0
    As_min = 0.0015 * b_cm * d_cm
    return max(As, As_min)


# ═══════════════════════════════════════════════════════════════════════════════
#  2. ISOLATED FOOTING MODEL DESIGN ENGINE (ECP 203)
# ═══════════════════════════════════════════════════════════════════════════════

def design_isolated_footing_model(
    model_id: str,
    model_label: str,
    col_code: str,
    Pu_ton: float,
    c_cm: float,
    b_cm: float,
    q_net_kgcm2: float,
    Fcu: float = 250.0,
    Fy: float = 4000.0,
    cover_cm: float = 7.0,
    Phi_mm: int = 16,
    Phi_col_mm: int = 16,
):
    """
    Design unified isolated footing model (F1, F2, F3) according to ECP 203.
    Returns complete dictionary with all 9 schedule columns and verification metrics.
    """
    if Pu_ton <= 0:
        Pu_ton = 10.0

    # 1. Working load & required area
    P_working_ton = Pu_ton / 1.5
    P_working_kg = P_working_ton * 1000.0
    A_req_cm2 = 1.05 * P_working_kg / q_net_kgcm2

    # 2. Equal overhangs (c_L = c_B) -> L = B + (c - b)
    delta = float(c_cm - b_cm)
    disc = delta**2 + 4.0 * A_req_cm2
    B_raw = (-delta + math.sqrt(max(disc, 1.0))) / 2.0
    L_raw = B_raw + delta

    L_cm = _r5(max(L_raw, c_cm + 30))
    B_cm = _r5(max(B_raw, b_cm + 30))

    # Actual contact pressure at working load
    A_cm2 = L_cm * B_cm
    q_act = 1.05 * P_working_kg / A_cm2
    q_ok = q_act <= q_net_kgcm2
    util_q = (q_act / q_net_kgcm2) * 100.0

    # Ultimate uniform soil reaction
    Pu_kg = Pu_ton * 1000.0
    q_u = Pu_kg / A_cm2

    cant_L = (L_cm - c_cm) / 2.0
    cant_B = (B_cm - b_cm) / 2.0

    # Thickness check (governed by shear, punching, and minimum 40 cm)
    q_cu = _shear_allow_kgcm2(Fcu)
    d_shear = (q_u * cant_L) / (q_cu + 0.5 * q_u) if (q_cu + 0.5 * q_u) > 0 else 30.0

    d_punch = 35.0
    for _ in range(5):
        bo = 2.0 * ((c_cm + d_punch) + (b_cm + d_punch))
        Ap = (c_cm + d_punch) * (b_cm + d_punch)
        Qp = Pu_kg - q_u * Ap
        tau_p_allow = _punch_allow_kgcm2(Fcu, c_cm, b_cm, d_punch, bo)
        d_req = Qp / (bo * tau_p_allow) if (bo * tau_p_allow) > 0 else 30.0
        d_punch = max(d_punch, d_req)

    d_cm = _r5(max(d_shear, d_punch, 35.0))
    t_cm = _r5(d_cm + cover_cm + (Phi_mm / 20.0))
    if t_cm < 40:
        t_cm = 40
        d_cm = t_cm - cover_cm - (Phi_mm / 20.0)

    # Re-verify shear and punching stresses
    a_L = max(cant_L - d_cm / 2.0, 0)
    V_L = q_u * B_cm * a_L
    tau_s = V_L / (B_cm * d_cm) if (B_cm * d_cm) > 0 else 0.0
    s_ok = tau_s <= q_cu

    bo_final = 2.0 * ((c_cm + d_cm) + (b_cm + d_cm))
    Ap_final = (c_cm + d_cm) * (b_cm + d_cm)
    Qp_final = Pu_kg - q_u * Ap_final
    tau_p = Qp_final / (bo_final * d_cm) if (bo_final * d_cm) > 0 else 0.0
    tau_p_allow = _punch_allow_kgcm2(Fcu, c_cm, b_cm, d_cm, bo_final)
    p_ok = tau_p <= tau_p_allow

    # Flexure & Reinforcement
    M_L_kgcm = q_u * B_cm * (cant_L**2) / 2.0
    M_B_kgcm = q_u * L_cm * (cant_B**2) / 2.0

    As_L = _As_design_cm2(M_L_kgcm, d_cm, B_cm, Fcu, Fy)
    As_B = _As_design_cm2(M_B_kgcm, d_cm, L_cm, Fcu, Fy)

    a_bar_cm2 = math.pi * ((Phi_mm / 10.0)**2) / 4.0
    n_m_L = max(5, math.ceil((As_L / (B_cm / 100.0)) / a_bar_cm2))
    n_m_B = max(5, math.ceil((As_B / (L_cm / 100.0)) / a_bar_cm2))

    total_bars_L = math.ceil(n_m_L * (B_cm / 100.0))
    total_bars_B = math.ceil(n_m_B * (L_cm / 100.0))

    # Top reinforcement (shrinkage if t >= 80 cm)
    if t_cm >= 80:
        top_rft_str = "5 Φ 12 / m (انكماش علوي)"
    else:
        top_rft_str = "None"

    # Column dowel length Ld (60 Phi)
    Ld_cm = int(math.ceil(60.0 * (Phi_col_mm / 10.0)))

    is_safe = q_ok and s_ok and p_ok

    Pu_kN = Pu_ton * 9.80665

    return {
        "model_id": model_id,
        "model_label": model_label,
        "model_name": f"{model_id} ({model_label})",
        "col_code": col_code,
        "col_dims_str": f"{c_cm:.0f} × {b_cm:.0f} cm",
        "supported_col_str": f"{col_code} ({c_cm:.0f}×{b_cm:.0f} cm)",
        "Pu_ton": Pu_ton,
        "Pu_kN": Pu_kN,
        "Pu_str": f"{Pu_ton:.2f} ton",
        "P_working_ton": P_working_ton,
        "L_cm": L_cm,
        "B_cm": B_cm,
        "t_cm": t_cm,
        "d_cm": d_cm,
        "dims_str": f"{L_cm} × {B_cm} × {t_cm} cm",
        "rft_long_str": f"{n_m_L} Φ {Phi_mm} / m ({total_bars_L} Φ {Phi_mm})",
        "rft_short_str": f"{n_m_B} Φ {Phi_mm} / m ({total_bars_B} Φ {Phi_mm})",
        "top_rft_str": top_rft_str,
        "Ld_str": f"{Ld_cm} cm (60Φ)",
        "status_str": "Safe ✅" if is_safe else "Review ⚠️",
        "is_safe": is_safe,
        "q_act": q_act,
        "q_net": q_net_kgcm2,
        "util_q": util_q,
        "tau_s": tau_s,
        "tau_s_allow": q_cu,
        "tau_p": tau_p,
        "tau_p_allow": tau_p_allow,
        "M_L_tm": M_L_kgcm / 100000.0,
        "M_B_tm": M_B_kgcm / 100000.0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  3. COMBINED FOOTING MODEL DESIGN ENGINE (ECP 203)
# ═══════════════════════════════════════════════════════════════════════════════

def design_combined_footing_model(
    cf_id: str,
    col_a_info: dict,
    col_b_info: dict,
    S_m: float,
    q_net_kgcm2: float,
    Fcu: float = 250.0,
    Fy: float = 4000.0,
    cover_cm: float = 7.0,
    Phi_mm: int = 18,
):
    """
    Design combined footing model according to ECP 203 for two overlapping columns.
    Returns complete dictionary with all 8 schedule columns and verification metrics.
    """
    P1_ton = float(col_a_info.get("pu_tot", 50.0))
    P2_ton = float(col_b_info.get("pu_tot", 75.0))
    c1_cm = float(col_a_info.get("tc", 50.0))
    b1_cm = float(col_a_info.get("bc", 30.0))
    c2_cm = float(col_b_info.get("tc", 50.0))
    b2_cm = float(col_b_info.get("bc", 30.0))

    Ru_ton = P1_ton + P2_ton
    R_work_ton = Ru_ton / 1.5
    R_work_kg = R_work_ton * 1000.0
    Ru_kg = Ru_ton * 1000.0

    # Center of gravity of loads from C1 center
    x_R_m = (P2_ton * S_m) / Ru_ton if Ru_ton > 0 else S_m / 2.0
    A_req_cm2 = 1.05 * R_work_kg / q_net_kgcm2

    ov_min_m = 0.25  # minimum 25 cm overhang beyond col face
    x1_min_m = (c1_cm / 200.0) + ov_min_m

    L_trial_m = 2.0 * (x1_min_m + x_R_m)
    x2_trial_m = L_trial_m - x1_min_m - S_m

    if x2_trial_m < (c2_cm / 200.0) + ov_min_m:
        x1_min_m = max(x1_min_m, (c2_cm / 200.0) + ov_min_m + S_m - 2.0 * x_R_m)
        L_trial_m = 2.0 * (x1_min_m + x_R_m)

    Lc_cm = _r5(L_trial_m * 100.0)
    Lc_m = Lc_cm / 100.0
    x1_m = (Lc_m / 2.0) - x_R_m
    x2_m = Lc_m - x1_m - S_m

    if x1_m < (c1_cm / 200.0) + 0.10:
        x1_m = (c1_cm / 200.0) + 0.20
        Lc_cm = _r5((x1_m + S_m + (c2_cm / 200.0) + 0.20) * 100.0)
        Lc_m = Lc_cm / 100.0
        x2_m = Lc_m - x1_m - S_m

    # Practical minimum width for combined footing:
    # 1. Must be at least the width of the individual isolated footings being combined
    iso_B1 = float(col_a_info.get("iso_B_cm", 140.0))
    iso_B2 = float(col_b_info.get("iso_B_cm", 140.0))
    min_iso_B = max(iso_B1, iso_B2)

    # 2. Transverse cantilever of at least 50 cm on each side of column
    min_cant_B = max(b1_cm, b2_cm) + 2.0 * 50.0  # e.g. 30 + 100 = 130 cm

    # 3. Standard minimum combined footing width in engineering practice (at least 140 cm)
    min_required_B = max(min_iso_B, min_cant_B, 140.0)

    Bc_raw_cm = A_req_cm2 / Lc_cm
    Bc_cm = _r5(max(Bc_raw_cm, min_required_B))
    Bc_m = Bc_cm / 100.0

    # Auto-thickness for combined footing (approx S / 4.5, min 60 cm)
    tc_cm = _r5(max(S_m / 4.5 * 100.0, 60.0))
    dc_cm = tc_cm - cover_cm - (Phi_mm / 20.0)

    # Actual working soil pressure
    Ac_cm2 = Lc_cm * Bc_cm
    q_act = 1.05 * R_work_kg / Ac_cm2
    q_ok = q_act <= q_net_kgcm2

    # Moments: Inverted beam upward load
    w_u_tonm = Ru_ton / Lc_m if Lc_m > 0 else 0.0
    w_u_kgcm = (Ru_kg / Lc_cm) if Lc_cm > 0 else 0.0

    # Left & right cantilevers positive moments (sagging -> bottom steel)
    cant1_m = max(x1_m - (c1_cm / 200.0), 0.0)
    cant2_m = max(x2_m - (c2_cm / 200.0), 0.0)
    M_cant1_tm = w_u_tonm * (cant1_m**2) / 2.0
    M_cant2_tm = w_u_tonm * (cant2_m**2) / 2.0

    # Maximum negative moment between columns at zero-shear section
    x_zero_m = (P1_ton / w_u_tonm) if w_u_tonm > 0 else x1_m
    M_top_tm = abs((w_u_tonm * (x_zero_m**2) / 2.0) - P1_ton * (x_zero_m - x1_m))
    M_bot_max_tm = max(M_cant1_tm, M_cant2_tm)

    # Transverse bending under columns (cantilever of width (Bc - b) / 2)
    cant_trans_m = max((Bc_m - (max(b1_cm, b2_cm) / 100.0)) / 2.0, 0.0)
    q_u_kgcm2 = Ru_kg / Ac_cm2
    M_trans_kgcm = q_u_kgcm2 * 100.0 * ((cant_trans_m * 100.0)**2) / 2.0

    # Reinforcement calculation
    As_top_cm2 = _As_design_cm2(M_top_tm * 100000.0, dc_cm, Bc_cm, Fcu, Fy)
    As_bot_cm2 = _As_design_cm2(M_bot_max_tm * 100000.0, dc_cm, Bc_cm, Fcu, Fy)
    As_trans_cm2 = _As_design_cm2(M_trans_kgcm, dc_cm, 100.0, Fcu, Fy)

    a_bar_cm2 = math.pi * ((Phi_mm / 10.0)**2) / 4.0
    n_top_total = max(math.ceil(As_top_cm2 / a_bar_cm2), math.ceil(5 * Bc_m))
    n_bot_total = max(math.ceil(As_bot_cm2 / a_bar_cm2), math.ceil(5 * Bc_m))
    n_trans_m = max(5, math.ceil(As_trans_cm2 / a_bar_cm2))

    # Shear & Punching check
    tau_s_allow = _shear_allow_kgcm2(Fcu)
    V_crit_kg = abs(P1_ton * 1000.0 - w_u_kgcm * ((x1_m + c1_cm / 200.0) * 100.0 + dc_cm / 2.0))
    tau_s = V_crit_kg / (Bc_cm * dc_cm) if (Bc_cm * dc_cm) > 0 else 0.0
    s_ok = tau_s <= tau_s_allow

    is_safe = q_ok and s_ok

    col_a_name = col_a_info.get("id", "C_A")
    col_b_name = col_b_info.get("id", "C_B")

    return {
        "cf_id": cf_id,
        "name": cf_id,
        "supported_cols": f"{col_a_name} + {col_b_name}",
        "col_a_id": col_a_name,
        "col_b_id": col_b_name,
        "col_a_info": col_a_info,
        "col_b_info": col_b_info,
        "P1_ton": P1_ton,
        "P2_ton": P2_ton,
        "Ru_ton": Ru_ton,
        "S_m": S_m,
        "Lc_cm": Lc_cm,
        "Bc_cm": Bc_cm,
        "tc_cm": tc_cm,
        "dc_cm": dc_cm,
        "dims_str": f"{Lc_cm} × {Bc_cm} × {tc_cm} cm",
        "rft_bot_str": f"{n_bot_total} Φ {Phi_mm} ({n_bot_total/Bc_m:.0f}Φ/m)",
        "rft_top_str": f"{n_top_total} Φ {Phi_mm} ({n_top_total/Bc_m:.0f}Φ/m)",
        "rft_trans_str": f"{n_trans_m} Φ {Phi_mm} / m'",
        "x1_cm": round(x1_m * 100.0, 1),
        "x2_cm": round(x2_m * 100.0, 1),
        "overhangs_str": f"x₁ = {x1_m*100:.0f} cm, x₂ = {x2_m*100:.0f} cm",
        "status_str": "Safe ✅" if is_safe else "Review ⚠️",
        "is_safe": is_safe,
        "M_top_tm": M_top_tm,
        "M_bot_max_tm": M_bot_max_tm,
        "q_act": q_act,
        "q_net": q_net_kgcm2,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  4. BUILDING COLUMNS PIPELINE & CLEARANCE / OVERLAP ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def get_building_columns_data():
    """
    Retrieve building columns data from session state or settings (exported from Module 1).
    If not available, generates a realistic standard 3x3 building layout.
    """
    pu_c = (
        st.session_state.get("pu_tot_corner")
        or S.cfg_val("fs_col_tot_pu_corner")
        or (float(S.cfg_val("fs_col_pu_corner", 14.5)) * float(S.cfg_val("slab_n_floors", 3)))
    )
    pu_e = (
        st.session_state.get("pu_tot_edge")
        or st.session_state.get("pu_tot_side")
        or S.cfg_val("fs_col_tot_pu_edge")
        or (float(S.cfg_val("fs_col_pu_edge", 28.5)) * float(S.cfg_val("slab_n_floors", 3)))
    )
    pu_i = (
        st.session_state.get("pu_tot_int")
        or S.cfg_val("fs_col_tot_pu_int")
        or (float(S.cfg_val("fs_col_pu_int", 45.0)) * float(S.cfg_val("slab_n_floors", 3)))
    )

    bc = float(st.session_state.get("fs_col_b") or S.cfg_val("fs_col_b", S.cfg_val("slab_bc", 30)))
    tc = float(st.session_state.get("fs_col_c") or S.cfg_val("fs_col_c", S.cfg_val("slab_tc", 50)))

    saved_cols = st.session_state.get("fs_building_columns") or S.cfg_val("fs_building_columns")

    if saved_cols and isinstance(saved_cols, list) and len(saved_cols) >= 4:
        columns = []
        for c in saved_cols:
            c_type = c.get("type", "Interior")
            pu_val = float(c.get("pu_tot", 0.0))
            if pu_val <= 0:
                pu_val = pu_c if c_type == "Corner" else (pu_e if c_type == "Edge" else pu_i)
            columns.append({
                "id": c.get("id", "C"),
                "orig_id": c.get("orig_id", c.get("id", "C")),
                "type": c_type,
                "x": float(c.get("x", 0.0)),
                "y": float(c.get("y", 0.0)),
                "bc": float(c.get("bc", bc)),
                "tc": float(c.get("tc", tc)),
                "pu_tot": pu_val,
                "grid_x": c.get("grid_x", ""),
                "grid_y": c.get("grid_y", ""),
            })
        has_imported = True
    else:
        has_imported = False
        columns = []
        x_coords = [0.0, 4.5, 9.0]
        y_coords = [0.0, 4.5, 9.0]
        c_count = 1
        for j, y in enumerate(y_coords):
            for i, x in enumerate(x_coords):
                is_c = (i in (0, 2)) and (j in (0, 2))
                is_e = (not is_c) and (i in (0, 2) or j in (0, 2))
                ctype = "Corner" if is_c else ("Edge" if is_e else "Interior")
                pu = pu_c if is_c else (pu_e if is_e else pu_i)
                columns.append({
                    "id": f"C{c_count}",
                    "orig_id": f"C{c_count}",
                    "type": ctype,
                    "x": x,
                    "y": y,
                    "bc": bc,
                    "tc": tc,
                    "pu_tot": pu,
                    "grid_x": f"Y{i+1}",
                    "grid_y": f"X{j+1}",
                })
                c_count += 1

    return {
        "columns": columns,
        "pu_corner": float(pu_c),
        "pu_edge": float(pu_e),
        "pu_int": float(pu_i),
        "bc": bc,
        "tc": tc,
        "has_imported": has_imported,
    }


def check_building_clearances_and_overlaps(columns_list: list, footings_map: dict):
    """
    Check horizontal and vertical clearances between all adjacent footings.
    Clearance = Distance between Column Centers - (L_A/2 + L_B/2)
    Condition 1: Clearance >= 0.15 m -> Stable isolated footing.
    Condition 2: Clearance < 0.15 m  -> Overlap detected -> Combined Footing required.
    """
    overlapping_pairs = []
    all_clearances = []
    overlapping_col_ids = set()

    y_tol = 0.10
    rows = {}
    for c in columns_list:
        matched_y = None
        for y_key in rows.keys():
            if abs(c["y"] - y_key) < y_tol:
                matched_y = y_key
                break
        if matched_y is None:
            matched_y = c["y"]
            rows[matched_y] = []
        rows[matched_y].append(c)

    for y_val, row_cols in rows.items():
        row_cols.sort(key=lambda c: c["x"])
        for i in range(len(row_cols) - 1):
            cA = row_cols[i]
            cB = row_cols[i + 1]
            S_x = cB["x"] - cA["x"]

            fA = footings_map.get(cA["type"])
            fB = footings_map.get(cB["type"])
            dimA_x = (fA["L_cm"] / 100.0) if fA else 2.0
            dimB_x = (fB["L_cm"] / 100.0) if fB else 2.0

            clearance = S_x - (dimA_x / 2.0 + dimB_x / 2.0)
            cA["iso_B_cm"] = fA["B_cm"] if fA else 140.0
            cB["iso_B_cm"] = fB["B_cm"] if fB else 140.0
            cA["iso_L_cm"] = fA["L_cm"] if fA else 140.0
            cB["iso_L_cm"] = fB["L_cm"] if fB else 140.0
            pair_rec = {
                "col_A": cA,
                "col_B": cB,
                "dir": "X",
                "spacing_m": S_x,
                "clearance_m": clearance,
                "clearance_cm": clearance * 100.0,
                "is_overlap": clearance < 0.15,
            }
            all_clearances.append(pair_rec)
            if clearance < 0.15:
                overlapping_pairs.append(pair_rec)
                overlapping_col_ids.add(cA["id"])
                overlapping_col_ids.add(cB["id"])

    x_tol = 0.10
    cols = {}
    for c in columns_list:
        matched_x = None
        for x_key in cols.keys():
            if abs(c["x"] - x_key) < x_tol:
                matched_x = x_key
                break
        if matched_x is None:
            matched_x = c["x"]
            cols[matched_x] = []
        cols[matched_x].append(c)

    for x_val, col_cols in cols.items():
        col_cols.sort(key=lambda c: c["y"])
        for j in range(len(col_cols) - 1):
            cA = col_cols[j]
            cB = col_cols[j + 1]
            S_y = cB["y"] - cA["y"]

            fA = footings_map.get(cA["type"])
            fB = footings_map.get(cB["type"])
            dimA_y = (fA["B_cm"] / 100.0) if fA else 2.0
            dimB_y = (fB["B_cm"] / 100.0) if fB else 2.0

            clearance = S_y - (dimA_y / 2.0 + dimB_y / 2.0)
            cA["iso_B_cm"] = fA["B_cm"] if fA else 140.0
            cB["iso_B_cm"] = fB["B_cm"] if fB else 140.0
            cA["iso_L_cm"] = fA["L_cm"] if fA else 140.0
            cB["iso_L_cm"] = fB["L_cm"] if fB else 140.0
            pair_rec = {
                "col_A": cA,
                "col_B": cB,
                "dir": "Y",
                "spacing_m": S_y,
                "clearance_m": clearance,
                "clearance_cm": clearance * 100.0,
                "is_overlap": clearance < 0.15,
            }
            all_clearances.append(pair_rec)
            if clearance < 0.15:
                overlapping_pairs.append(pair_rec)
                overlapping_col_ids.add(cA["id"])
                overlapping_col_ids.add(cB["id"])

    has_overlap = len(overlapping_pairs) > 0
    return {
        "has_overlap": has_overlap,
        "overlapping_pairs": overlapping_pairs,
        "all_clearances": all_clearances,
        "overlapping_col_ids": overlapping_col_ids,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  5. MATPLOTLIB FOUNDATION GENERAL LAYOUT PLAN
# ═══════════════════════════════════════════════════════════════════════════════

_DIM_COLOR = "#334155"
_DIM_FS = 10.0
_ARROW_STYLE = dict(arrowstyle="<->", color="#334155", lw=1.5)

def _hdim(ax, y, x1, x2, label, side="top", fs=_DIM_FS, offset=0.18):
    ym = y + offset if side == "top" else y - offset
    ax.annotate("", xy=(x1, ym), xytext=(x2, ym), arrowprops=_ARROW_STYLE)
    ax.plot([x1, x1], [y, ym], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.plot([x2, x2], [y, ym], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.text((x1 + x2) / 2, ym + 0.08 * (1 if side == "top" else -1),
            label, ha="center", va="bottom" if side == "top" else "top",
            fontsize=fs, fontweight="bold", color=_DIM_COLOR)

def _vdim(ax, x, y1, y2, label, side="right", fs=_DIM_FS, offset=0.18):
    xm = x + offset if side == "right" else x - offset
    ax.annotate("", xy=(xm, y1), xytext=(xm, y2), arrowprops=_ARROW_STYLE)
    ax.plot([x, xm], [y1, y1], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.plot([x, xm], [y2, y2], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.text(xm + 0.08 * (1 if side == "right" else -1), (y1 + y2) / 2,
            label, ha="left" if side == "right" else "right", va="center",
            rotation=90, fontsize=fs, fontweight="bold", color=_DIM_COLOR)

def draw_foundation_layout_plan(
    columns_list: list,
    footings_map: dict,
    overlap_info: dict,
    combined_footings_list: list = None,
):
    """
    Generate comprehensive Foundation General Layout Plan:
    - R.C. boundaries at exact positions
    - Intermediate bay dimensions between consecutive grid axes (X & Y)
    - Total dimensions between first and last axis in both directions
    - Column labels simplified to C1, C2, C3 beside columns in black text
    - Representative footing for each type has clean dimension lines (L & B)
    - Footing dimension and thickness boxes placed cleanly at the bottom of the drawing
    - Clean layout without cluttering Clr lines
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, ax = plt.subplots(figsize=(16, 13), dpi=160, facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")

    overlapping_ids = overlap_info["overlapping_col_ids"]

    xs = [c["x"] for c in columns_list]
    ys = [c["y"] for c in columns_list]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    unique_xs = sorted(list(set(round(x, 2) for x in xs)))
    unique_ys = sorted(list(set(round(y, 2) for y in ys)))

    max_ftg_y = max(c["y"] + ((footings_map.get(c["type"], {}).get("B_cm", 200.0) / 200.0)) for c in columns_list)
    min_ftg_y = min(c["y"] - ((footings_map.get(c["type"], {}).get("B_cm", 200.0) / 200.0)) for c in columns_list)
    min_ftg_x = min(c["x"] - ((footings_map.get(c["type"], {}).get("L_cm", 200.0) / 200.0)) for c in columns_list)
    max_ftg_x = max(c["x"] + ((footings_map.get(c["type"], {}).get("L_cm", 200.0) / 200.0)) for c in columns_list)

    y_top_base = max_ftg_y + 0.6
    x_left_base = min_ftg_x - 0.6
    y_bottom_base = min_ftg_y - 0.6
    x_right_base = max_ftg_x + 0.6

    y_dim1 = y_top_base + 0.6
    y_dim2 = y_top_base + 1.4
    y_bubble = y_top_base + 2.2

    x_dim1 = x_left_base - 0.6
    x_dim2 = x_left_base - 1.4
    x_bubble = x_left_base - 2.2

    # 1. Draw Grid lines & Axis bubbles
    for idx, gx in enumerate(unique_xs, start=1):
        ax.plot([gx, gx], [y_bottom_base + 0.3, y_bubble], color="#cbd5e1", ls="--", lw=1.2, zorder=1)
        ax.text(gx, y_bubble + 0.35, f"Y{idx}", ha="center", va="center", color="#1e293b",
                fontweight="bold", fontsize=11.0, bbox=dict(boxstyle="circle,pad=0.28", fc="#f8fafc", ec="#475569", lw=1.5))

    for idx, gy in enumerate(unique_ys, start=1):
        ax.plot([x_bubble, x_right_base], [gy, gy], color="#cbd5e1", ls="--", lw=1.2, zorder=1)
        ax.text(x_bubble - 0.35, gy, f"X{idx}", ha="center", va="center", color="#1e293b",
                fontweight="bold", fontsize=11.0, bbox=dict(boxstyle="circle,pad=0.28", fc="#f8fafc", ec="#475569", lw=1.5))

    # 2. Dimensions between vertical grid lines (along X at the top)
    if len(unique_xs) > 1:
        # Intermediate bay spans
        for i in range(len(unique_xs) - 1):
            xa = unique_xs[i]
            xb = unique_xs[i + 1]
            dx = xb - xa
            _hdim(ax, y_top_base, xa, xb, f"{dx:.2f} m", side="top", fs=9.5, offset=0.6)

        # Total span between first and last vertical axis
        tot_dx = unique_xs[-1] - unique_xs[0]
        _hdim(ax, y_top_base, unique_xs[0], unique_xs[-1], f"Total L = {tot_dx:.2f} m", side="top", fs=10.5, offset=1.4)

    # 3. Dimensions between horizontal grid lines (along Y at the left)
    if len(unique_ys) > 1:
        # Intermediate bay spans
        for j in range(len(unique_ys) - 1):
            ya = unique_ys[j]
            yb = unique_ys[j + 1]
            dy = yb - ya
            _vdim(ax, x_left_base, ya, yb, f"{dy:.2f} m", side="left", fs=9.5, offset=0.6)

        # Total span between first and last horizontal axis
        tot_dy = unique_ys[-1] - unique_ys[0]
        _vdim(ax, x_left_base, unique_ys[0], unique_ys[-1], f"Total B = {tot_dy:.2f} m", side="left", fs=10.5, offset=1.4)

    # Pick exactly one representative column for each footing type (Corner F1, Edge F2, Interior F3)
    rep_types = {"Corner": None, "Edge": None, "Interior": None}
    for c in columns_list:
        ct = c["type"]
        if ct in rep_types and rep_types[ct] is None and c["id"] not in overlapping_ids:
            rep_types[ct] = c["id"]
    for c in columns_list:
        ct = c["type"]
        if ct in rep_types and rep_types[ct] is None:
            rep_types[ct] = c["id"]

    # 4. Draw footings for NON-OVERLAPPING columns ONLY
    for c in columns_list:
        cid = c["id"]
        if cid in overlapping_ids:
            # Overlapping columns are enclosed by the single combined footing outline below!
            continue

        cx = c["x"]
        cy = c["y"]
        ctype = c["type"]
        ftg = footings_map.get(ctype)

        L_m = (ftg["L_cm"] / 100.0) if ftg else 2.0
        B_m = (ftg["B_cm"] / 100.0) if ftg else 2.0

        is_rep = (cid in rep_types.values())

        x0 = cx - L_m / 2.0
        y0 = cy - B_m / 2.0

        rect = patches.Rectangle(
            (x0, y0), L_m, B_m,
            linewidth=1.8, edgecolor="#1e40af", facecolor="#e2e8f0",
            alpha=0.85, zorder=2
        )
        ax.add_patch(rect)
        ax.text(x0 + 0.12, y0 + 0.12, f"{ftg['model_id']}", ha="left", va="bottom",
                fontsize=10, fontweight="bold", color="#1e3a8a", zorder=4)

        if is_rep:
            _hdim(ax, y0, x0, x0 + L_m, f"L = {ftg['L_cm']} cm", side="bottom", fs=9.0, offset=0.25)
            _vdim(ax, x0 + L_m, y0, y0 + B_m, f"B = {ftg['B_cm']} cm", side="right", fs=9.0, offset=0.25)

    # 5. Draw Combined Footings (Dimensions only using dimension lines + clean label, no bulky badge box)
    if combined_footings_list:
        for cf in combined_footings_list:
            cA = cf["col_a_info"]
            cB = cf["col_b_info"]
            Lc_m = cf["Lc_cm"] / 100.0
            Bc_m = cf["Bc_cm"] / 100.0
            x1_m = cf["x1_cm"] / 100.0
            ov_dir = cf.get("overlap_dir", "X")
            if abs(cB["x"] - cA["x"]) < 0.1 and abs(cB["y"] - cA["y"]) > 0.1:
                ov_dir = "Y"

            if ov_dir == "X":
                cf_x0 = cA["x"] - x1_m
                cf_y0 = cA["y"] - Bc_m / 2.0
                cf_w, cf_h = Lc_m, Bc_m
                dim_L = f"L = {cf['Lc_cm']} cm"
                dim_B = f"B = {cf['Bc_cm']} cm"
            else:
                cf_x0 = cA["x"] - Bc_m / 2.0
                cf_y0 = cA["y"] - x1_m
                cf_w, cf_h = Bc_m, Lc_m
                dim_L = f"L = {cf['Lc_cm']} cm"
                dim_B = f"B = {cf['Bc_cm']} cm"

            cf_rect = patches.Rectangle(
                (cf_x0, cf_y0), cf_w, cf_h,
                linewidth=2.8, edgecolor="green", facecolor="#dcfce7",
                linestyle="--", alpha=0.55, zorder=3
            )
            ax.add_patch(cf_rect)

            # Clean name label in green inside the footing without bulky card box
            ax.text(
                cf_x0 + 0.12, cf_y0 + cf_h - 0.15,
                f"{cf['name']}",
                ha="left", va="top", color="#15803d", fontweight="bold", fontsize=10.5,
                zorder=6,
            )

            # Draw outer dimension lines on the combined footing exactly like isolated footings
            if ov_dir == "X":
                _hdim(ax, cf_y0, cf_x0, cf_x0 + cf_w, dim_L, side="bottom", fs=8.5, offset=0.25)
                _vdim(ax, cf_x0 + cf_w, cf_y0, cf_y0 + cf_h, dim_B, side="right", fs=8.5, offset=0.25)
            else:
                _vdim(ax, cf_x0 + cf_w, cf_y0, cf_y0 + cf_h, dim_L, side="right", fs=8.5, offset=0.25)
                _hdim(ax, cf_y0, cf_x0, cf_x0 + cf_w, dim_B, side="bottom", fs=8.5, offset=0.25)

    # 6. Draw column sections and place ONLY C1, C2, C3 beside columns in BLACK text
    for c in columns_list:
        cx = c["x"]
        cy = c["y"]
        col_w_m = c["tc"] / 100.0
        col_h_m = c["bc"] / 100.0

        col_rect = patches.Rectangle(
            (cx - col_w_m / 2.0, cy - col_h_m / 2.0),
            col_w_m, col_h_m,
            linewidth=1.5, edgecolor="#0f172a", facecolor="#64748b",
            hatch="//", zorder=6
        )
        ax.add_patch(col_rect)

        # Show only C1, C2, C3 without column index
        c_tag = "C1" if c["type"] == "Corner" else ("C2" if c["type"] == "Edge" else "C3")
        ax.text(
            cx + col_w_m / 2.0 + 0.12,
            cy + col_h_m / 2.0 + 0.05,
            f"{c_tag}",
            ha="left",
            va="center",
            color="#000000",
            fontweight="bold",
            fontsize=10.0,
            zorder=8,
            bbox=dict(boxstyle="round,pad=0.15", fc="#ffffff", ec="#94a3b8", alpha=0.9),
        )

    # 7. INTEGRATED FOOTINGS SCHEDULE TABLE AT THE BOTTOM (NO CARDS)
    f1 = footings_map.get("Corner")
    f2 = footings_map.get("Edge")
    f3 = footings_map.get("Interior")

    headers = ["Footing Model", "Type", "Supported Columns", "R.C. Dims (L × B × t cm)", "P.C. Dims (L × B × t cm)"]
    col_widths = [0.18, 0.16, 0.24, 0.21, 0.21]

    cell_text = []
    row_colors = []

    if f1:
        cell_text.append([f1["model_name"], "Isolated", f1["supported_col_str"], f"{f1['L_cm']} × {f1['B_cm']} × {f1['t_cm']}", f"{f1['L_cm'] + 40} × {f1['B_cm'] + 40} × 20"])
        row_colors.append("#eff6ff")
    if f2:
        cell_text.append([f2["model_name"], "Isolated", f2["supported_col_str"], f"{f2['L_cm']} × {f2['B_cm']} × {f2['t_cm']}", f"{f2['L_cm'] + 40} × {f2['B_cm'] + 40} × 20"])
        row_colors.append("#eff6ff")
    if f3:
        cell_text.append([f3["model_name"], "Isolated", f3["supported_col_str"], f"{f3['L_cm']} × {f3['B_cm']} × {f3['t_cm']}", f"{f3['L_cm'] + 40} × {f3['B_cm'] + 40} × 20"])
        row_colors.append("#eff6ff")

    if combined_footings_list:
        for cf in combined_footings_list:
            cell_text.append([
                cf["name"],
                "Combined",
                cf["supported_cols"],
                f"{cf['Lc_cm']} × {cf['Bc_cm']} × {cf['tc_cm']}",
                f"{cf['Lc_cm'] + 40} × {cf['Bc_cm'] + 40} × 20"
            ])
            row_colors.append("#f0fdf4")

    # Table layout matching grid width
    x_start = x_bubble
    total_w = x_right_base - x_bubble
    cum_w = [0.0]
    for w in col_widths:
        cum_w.append(cum_w[-1] + w * total_w)

    table_y = y_bottom_base - 0.95
    row_h = 0.52

    # Draw Header
    cur_y = table_y
    for i in range(len(headers)):
        rect = patches.Rectangle(
            (x_start + cum_w[i], cur_y - row_h), cum_w[i+1] - cum_w[i], row_h,
            facecolor="#1e3a8a", edgecolor="#94a3b8", lw=1.2, zorder=5
        )
        ax.add_patch(rect)
        ax.text(
            x_start + (cum_w[i] + cum_w[i+1]) / 2.0, cur_y - row_h / 2.0, headers[i],
            ha="center", va="center", color="#ffffff", fontweight="bold", fontsize=9.2, zorder=6
        )

    # Draw Rows
    cur_y -= row_h
    for r_idx, row in enumerate(cell_text):
        bg_color = row_colors[r_idx]
        for c_idx, val in enumerate(row):
            rect = patches.Rectangle(
                (x_start + cum_w[c_idx], cur_y - row_h), cum_w[c_idx+1] - cum_w[c_idx], row_h,
                facecolor=bg_color, edgecolor="#cbd5e1", lw=0.9, zorder=5
            )
            ax.add_patch(rect)
            text_color = "#1e40af" if "F" in row[0] else ("#15803d" if c_idx == 0 else "#1e293b")
            is_bold = "bold" if (c_idx == 0 or c_idx == 1) else "normal"
            ax.text(
                x_start + (cum_w[c_idx] + cum_w[c_idx+1]) / 2.0, cur_y - row_h / 2.0, val,
                ha="center", va="center", color=text_color, fontweight=is_bold, fontsize=8.8, zorder=6
            )
        cur_y -= row_h

    bottom_limit = cur_y - 1.25

    title_text = "ECP 203 — Foundation General Layout Plan & Overlap Verification"
    ax.set_title(title_text, fontsize=13.5, fontweight="bold", color="#0f172a", pad=25)

    leg_handles = [
        patches.Patch(facecolor="#e2e8f0", edgecolor="#1e40af", lw=1.8, label="Isolated Footing (قاعدة منفصلة آمنة)"),
        patches.Patch(facecolor="#dcfce7", edgecolor="green", linestyle="--", lw=2.2, label="Combined Footing (برواز القاعدة المشتركة بالكامل)"),
        patches.Patch(facecolor="#64748b", edgecolor="#0f172a", hatch="//", label="Column Section (C1: Corner, C2: Edge, C3: Interior)"),
    ]

    ax.legend(handles=leg_handles, loc="upper center", bbox_to_anchor=(0.5, -0.04),
              ncol=3, fontsize=9.2, frameon=True, facecolor="#ffffff")

    ax.set_xlim(x_bubble - 1.2, x_right_base + 1.2)
    ax.set_ylim(bottom_limit, y_bubble + 1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    return fig


#  6. QUICK 2-COLUMN MODE FUNCTIONS (Backward Compatible)
# ═══════════════════════════════════════════════════════════════════════════════

_DIM_COLOR = "#334155"
_DIM_FS = 13
_ARROW_STYLE = dict(arrowstyle="<->", color="#334155", lw=1.8)

def _hdim(ax, y, x1, x2, label, side="top", fs=_DIM_FS, offset=0.12):
    ym = y + offset if side == "top" else y - offset
    ax.annotate("", xy=(x1, ym), xytext=(x2, ym), arrowprops=_ARROW_STYLE)
    ax.plot([x1, x1], [y, ym], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.plot([x2, x2], [y, ym], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.text((x1 + x2) / 2, ym + 0.06 * (1 if side == "top" else -1),
            label, ha="center", va="bottom" if side == "top" else "top",
            fontsize=fs, fontweight="bold", color=_DIM_COLOR)

def _vdim(ax, x, y1, y2, label, side="right", fs=_DIM_FS, offset=0.12):
    xm = x + offset if side == "right" else x - offset
    ax.annotate("", xy=(xm, y1), xytext=(xm, y2), arrowprops=_ARROW_STYLE)
    ax.plot([x, xm], [y1, y1], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.plot([x, xm], [y2, y2], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.text(xm + 0.06 * (1 if side == "right" else -1), (y1 + y2) / 2,
            label, ha="left" if side == "right" else "right", va="center",
            rotation=90, fontsize=fs, fontweight="bold", color=_DIM_COLOR)

def _draw_plan(mode, *, S_m, c1_cm, b1_cm, c2_cm, b2_cm,
               L1_cm=None, B1_cm=None, L2_cm=None, B2_cm=None,
               Lc_cm=None, Bc_cm=None, x1_cm=None, x2_cm=None,
               rft=None):
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, ax = plt.subplots(figsize=(13, 7.5), dpi=150, facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")
    c1_m = c1_cm / 100.0; b1_m = b1_cm / 100.0
    c2_m = c2_cm / 100.0; b2_m = b2_cm / 100.0

    if mode == "isolated":
        L1_m = L1_cm / 100.0; B1_m = B1_cm / 100.0
        L2_m = L2_cm / 100.0; B2_m = B2_cm / 100.0
        x_c1 = 0.0; x_c2 = S_m
        y_c = 0.0
        ax.add_patch(patches.Rectangle((x_c1 - L1_m / 2, y_c - B1_m / 2), L1_m, B1_m, fc="#e2e8f0", ec="#0f172a", lw=2.5))
        ax.add_patch(patches.Rectangle((x_c2 - L2_m / 2, y_c - B2_m / 2), L2_m, B2_m, fc="#e2e8f0", ec="#0f172a", lw=2.5))
        ax.add_patch(patches.Rectangle((x_c1 - c1_m / 2, y_c - b1_m / 2), c1_m, b1_m, fc="#1e293b", ec="#0f172a", lw=2))
        ax.add_patch(patches.Rectangle((x_c2 - c2_m / 2, y_c - b2_m / 2), c2_m, b2_m, fc="#1e293b", ec="#0f172a", lw=2))
        ax.text(x_c1, y_c, "C1", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)
        ax.text(x_c2, y_c, "C2", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)
    else:
        Lc_m = Lc_cm / 100.0; Bc_m = Bc_cm / 100.0
        x1_m = x1_cm / 100.0
        x_c1 = 0.0; x_c2 = S_m; y_c = 0.0
        x0 = x_c1 - x1_m
        ax.add_patch(patches.Rectangle((x0, y_c - Bc_m / 2), Lc_m, Bc_m, fc="#e2e8f0", ec="#0f172a", lw=2.5))
        ax.add_patch(patches.Rectangle((x_c1 - c1_m / 2, y_c - b1_m / 2), c1_m, b1_m, fc="#1e293b", ec="#0f172a", lw=2))
        ax.add_patch(patches.Rectangle((x_c2 - c2_m / 2, y_c - b2_m / 2), c2_m, b2_m, fc="#1e293b", ec="#0f172a", lw=2))
        ax.text(x_c1, y_c, "C1", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)
        ax.text(x_c2, y_c, "C2", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)

    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  7. MAIN RENDER FUNCTION & STREAMLIT UI
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
#  7. STRUCTURAL TUTORIAL DRAWINGS & RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_tutorial_bmd():
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, axes = plt.subplots(2, 1, figsize=(16, 11), dpi=150, facecolor="#ffffff")
    plt.subplots_adjust(hspace=0.38)

    ax1 = axes[0]
    ax1.set_facecolor("#f8fafc")
    ax1.set_title("1. Longitudinal Direction (X-Axis): Inverted Beam Model & Bending Moments (BMD)",
                  fontsize=13.5, fontweight="bold", pad=12, color="#0f172a")

    ax1.add_patch(patches.Rectangle((1.0, 1.8), 8.0, 1.0, fc="#e2e8f0", ec="#0f172a", lw=2.5, zorder=2))
    ax1.add_patch(patches.Rectangle((2.6, 2.8), 0.8, 0.8, fc="#334155", ec="#0f172a", hatch="//", lw=2, zorder=3))
    ax1.text(3.0, 3.2, "C1\n(P1)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)
    ax1.annotate("", xy=(3.0, 2.8), xytext=(3.0, 3.9), arrowprops=dict(arrowstyle="->", color="#dc2626", lw=2.8))

    ax1.add_patch(patches.Rectangle((6.6, 2.8), 0.8, 0.8, fc="#334155", ec="#0f172a", hatch="//", lw=2, zorder=3))
    ax1.text(7.0, 3.2, "C2\n(P2)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)
    ax1.annotate("", xy=(7.0, 2.8), xytext=(7.0, 3.9), arrowprops=dict(arrowstyle="->", color="#dc2626", lw=2.8))

    for x in [1.5, 2.3, 3.1, 3.9, 4.7, 5.5, 6.3, 7.1, 7.9, 8.5]:
        ax1.annotate("", xy=(x, 1.8), xytext=(x, 1.0), arrowprops=dict(arrowstyle="->", color="#2563eb", lw=1.8))
    ax1.text(5.0, 0.65, "Upward Uniform Net Soil Reaction (qu)", ha="center", color="#1d4ed8", fontweight="bold", fontsize=11)

    ax1.plot([1.2, 8.8], [2.6, 2.6], color="#dc2626", lw=3.2, zorder=5)
    ax1.plot([1.2, 1.2], [2.6, 2.3], color="#dc2626", lw=3.2, zorder=5)
    ax1.plot([8.8, 8.8], [2.6, 2.3], color="#dc2626", lw=3.2, zorder=5)
    ax1.text(5.0, 2.75, "TOP REBAR: Resists Negative Hogging Moment (-M_top) between columns",
             ha="center", va="bottom", color="#b91c1c", fontweight="bold", fontsize=10.5,
             bbox=dict(boxstyle="round,pad=0.22", fc="#fee2e2", ec="#ef4444"))

    ax1.plot([1.2, 8.8], [2.0, 2.0], color="#1d4ed8", lw=3.2, zorder=5)
    ax1.plot([1.2, 1.2], [2.0, 2.3], color="#1d4ed8", lw=3.2, zorder=5)
    ax1.plot([8.8, 8.8], [2.0, 2.3], color="#1d4ed8", lw=3.2, zorder=5)
    ax1.text(5.0, 2.18, "BOTTOM REBAR: Resists Positive Moments (+M_bot) under cantilevers",
             ha="center", va="bottom", color="#1e40af", fontweight="bold", fontsize=10.5,
             bbox=dict(boxstyle="round,pad=0.22", fc="#eff6ff", ec="#3b82f6"))

    ax1.set_xlim(0, 10)
    ax1.set_ylim(0.3, 4.2)
    ax1.axis("off")

    ax2 = axes[1]
    ax2.set_facecolor("#f8fafc")
    ax2.set_title("2. Transverse Direction (Y-Axis): Lateral Cantilever Action & Bottom Tension Only",
                  fontsize=13.5, fontweight="bold", pad=12, color="#0f172a")

    ax2.add_patch(patches.Rectangle((2.5, 1.8), 5.0, 1.0, fc="#e2e8f0", ec="#0f172a", lw=2.5, zorder=2))
    ax2.add_patch(patches.Rectangle((4.5, 2.8), 1.0, 0.8, fc="#334155", ec="#0f172a", hatch="//", lw=2, zorder=3))
    ax2.text(5.0, 3.2, "Column\n(Pu)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)
    ax2.annotate("", xy=(5.0, 2.8), xytext=(5.0, 3.9), arrowprops=dict(arrowstyle="->", color="#dc2626", lw=2.8))

    for x in [2.8, 3.5, 4.2, 5.0, 5.8, 6.5, 7.2]:
        ax2.annotate("", xy=(x, 1.8), xytext=(x, 1.0), arrowprops=dict(arrowstyle="->", color="#059669", lw=1.8))
    ax2.text(5.0, 0.65, "Soil Pressure bends lateral cantilevers upward -> BOTTOM TENSION ONLY",
             ha="center", color="#047857", fontweight="bold", fontsize=11)

    ax2.plot([2.7, 7.3], [2.0, 2.0], color="#047857", lw=3.5, zorder=5)
    ax2.plot([2.7, 2.7], [2.0, 2.3], color="#047857", lw=3.5, zorder=5)
    ax2.plot([7.3, 7.3], [2.0, 2.3], color="#047857", lw=3.5, zorder=5)
    ax2.text(5.0, 2.15, "MAIN TRANSVERSE BOTTOM REBAR: Resists Cantilever Sagging Moments",
             ha="center", color="#065f46", fontweight="bold", fontsize=10.5,
             bbox=dict(boxstyle="round,pad=0.2", fc="#d1fae5", ec="#10b981"))

    ax2.plot([2.7, 7.3], [2.6, 2.6], color="#9333ea", lw=2.2, ls="--", zorder=5)
    ax2.text(5.0, 2.75, "Top Secondary Rebar (5Φ10/m) - For Shrinkage & Rebar Carrier Only (No Design Moment)",
             ha="center", color="#6b21a8", fontsize=9.0, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.15", fc="#faf5ff", ec="#c084fc"))

    ax2.set_xlim(0, 10)
    ax2.set_ylim(0.3, 4.2)
    ax2.axis("off")

    fig.tight_layout()
    return fig

def _draw_tutorial_sections():
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, (ax_plan, ax_sec) = plt.subplots(2, 1, figsize=(18, 17), dpi=150, facecolor="#ffffff")
    plt.subplots_adjust(hspace=0.36)

    ax_plan.set_facecolor("#f8fafc")
    ax_plan.set_title("1. Plan View: Full 4-Layer Executive Reinforcement Blueprint",
                      fontsize=14, fontweight="bold", pad=14, color="#0f172a")

    ax_plan.add_patch(patches.Rectangle((1.0, 1.0), 12.0, 5.2, fc="#ffffff", ec="#0f172a", lw=3.5, zorder=2))
    ax_plan.annotate("", xy=(1.0, 6.5), xytext=(13.0, 6.5), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.8))
    ax_plan.text(7.0, 6.65, "Footing Length (L)", ha="center", va="bottom", fontsize=12, fontweight="bold", color="#1e293b")

    ax_plan.annotate("", xy=(13.3, 1.0), xytext=(13.3, 6.2), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.8))
    ax_plan.text(13.5, 3.6, "Footing Width (B)", ha="left", va="center", rotation=-90, fontsize=12, fontweight="bold", color="#1e293b")

    ax_plan.add_patch(patches.Rectangle((3.0, 2.9), 1.2, 1.4, fc="#1e293b", ec="#0f172a", hatch="//", lw=2, zorder=5))
    ax_plan.text(3.6, 3.6, "C1\n(Col 1)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=12, zorder=6)

    ax_plan.add_patch(patches.Rectangle((9.5, 2.9), 1.4, 1.4, fc="#1e293b", ec="#0f172a", hatch="//", lw=2, zorder=5))
    ax_plan.text(10.2, 3.6, "C2\n(Col 2)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=12, zorder=6)

    ax_plan.plot([1.3, 12.7], [5.2, 5.2], color="#dc2626", lw=3.8, zorder=8)
    ax_plan.text(7.0, 5.35, "Layer 1: X-Top Main Rebar (العزم السالب بين العمودين)",
                 ha="center", va="bottom", fontsize=11.5, fontweight="bold", color="#991b1b",
                 bbox=dict(boxstyle="round,pad=0.28", fc="#fef2f2", ec="#ef4444", lw=1.6), zorder=12)

    ax_plan.plot([1.3, 12.7], [2.0, 2.0], color="#1d4ed8", lw=3.8, zorder=8)
    ax_plan.text(7.0, 1.50, "Layer 2: X-Bottom Main Rebar (عزم الكوابيل الموجب)",
                 ha="center", va="top", fontsize=11.5, fontweight="bold", color="#1e40af",
                 bbox=dict(boxstyle="round,pad=0.28", fc="#eff6ff", ec="#3b82f6", lw=1.6), zorder=12)

    ax_plan.set_xlim(0, 14.5)
    ax_plan.set_ylim(0.4, 7.3)
    ax_plan.axis("off")

    ax_sec.set_facecolor("#f8fafc")
    ax_sec.set_title("2. Longitudinal Cross-Section: Full 4-Layer Stacking & Detailing",
                     fontsize=14, fontweight="bold", pad=14, color="#0f172a")

    ax_sec.add_patch(patches.Rectangle((0.8, 0.4), 12.4, 0.5, fc="#e2e8f0", ec="#94a3b8", lw=1.5, hatch="..", zorder=1))
    ax_sec.text(1.0, 0.65, "Plain Concrete Blinding (P.C فرشة نظافة)", ha="left", va="center", fontsize=10.5, fontweight="bold", color="#64748b")

    ax_sec.add_patch(patches.Rectangle((1.0, 0.9), 12.0, 2.4, fc="#ffffff", ec="#0f172a", lw=3.5, zorder=2))
    ax_sec.add_patch(patches.Rectangle((3.0, 3.3), 1.2, 2.2, fc="#334155", ec="#0f172a", lw=2.5, zorder=4))
    ax_sec.text(3.6, 4.4, "C1\n(Col 1)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=12)
    ax_sec.add_patch(patches.Rectangle((9.5, 3.3), 1.4, 2.2, fc="#334155", ec="#0f172a", lw=2.5, zorder=4))
    ax_sec.text(10.2, 4.4, "C2\n(Col 2)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=12)

    ax_sec.set_xlim(0, 15.5)
    ax_sec.set_ylim(0.1, 5.8)
    ax_sec.axis("off")

    fig.tight_layout()
    return fig

def _render_structural_tutorial():
    st.markdown("---")
    with st.expander("📚 Combined Footing Structural Tutorial (الدليل الإنشائي والتعليمي للقواعد المشتركة)", expanded=False):
        t1, t2 = st.tabs([
            "📈 مخططات العزوم والسلوك الإنشائي (BMD & Structural Behavior)",
            "🧱 قطاعات وتفاصيل التسليح الكاملة (Full 4-Layer Detailing)",
        ])
        with t1:
            st.markdown("#### 🔍 السلوك الإنشائي ومخططات العزوم (Bending Moments & Mechanics)")
            fig_bmd = _draw_tutorial_bmd()
            st.pyplot(fig_bmd, use_container_width=True)
            plt.close(fig_bmd)

        with t2:
            st.markdown("#### 🧱 المخطط التنفيذي الشامل للطبقات الأربع للتسليح (4-Layer Executive Blueprint)")
            fig_sec = _draw_tutorial_sections()
            st.pyplot(fig_sec, use_container_width=True)
            plt.close(fig_sec)



def render():
    """Entry point — Module 7: Building Foundations & Combined Footings (ECP 203)."""

    # ── HEADER ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="input-section-header">
            <span style="font-size:26px;">🏗️</span>
            <span>Module 7 — تصميم أساسات المبنى والقواعد المشتركة (Building Foundations — ECP 203)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Design Note
    st.warning(
        "⚠️ **ملاحظة تصميمية واشتراطات الكود المصري (ECP 203):**\n\n"
        "تُعتبر الخرسانة العادية (P.C) فرشة نظافة بسمك أقل من 20 سم، ولا يتم أخذها في الاعتبار في توزيع الإجهادات أو تقليل أبعاد القواعد المسلحة؛ "
        "ويتم تصميم الخرسانة المسلحة (R.C) مباشرة على إجهاد التربة الصافي المسموح به (**q_all,net**). "
        "وعندما يقل الخلوص الصافي بين القواعد المتجاورة عن **0.15 م (15 سم)**، يلزم الكود التحول الفوري لنظام القواعد المشتركة (Combined Footings)."
    )

    # Compact Styling
    st.markdown(
        """
        <style>
        div[data-testid="stExpander"] details { padding: 8px 14px !important; margin-bottom: 8px !important; }
        div[data-testid="stExpander"] details summary { padding: 6px 10px !important; }
        div[data-testid="stExpander"] div[data-testid="stVerticalBlock"] { gap: 0.45rem !important; }
        .stCaption { font-size: 11.5px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── MODE SELECTOR ─────────────────────────────────────────────────────────
    m_choice = st.radio(
        "اختر نظام العمل المطلوب:",
        [
            "🏢 تصميم أساسات المبنى بالكامل (ربط تلقائي مع Module 1 — مسقط عام وفحص التداخل)",
            "📐 وضع التصميم السريع لقاعدتين (Manual Two-Column Mode)",
        ],
        index=0,
        horizontal=True,
        key="tcf_main_work_mode",
    )

    # ══════════════════════════════════════════════════════════════════════════
    #  A. FULL BUILDING FOUNDATIONS SYSTEM (LINKED WITH MODULE 1)
    # ══════════════════════════════════════════════════════════════════════════
    if "المبنى بالكامل" in m_choice:
        b_data = get_building_columns_data()
        cols_list = b_data["columns"]

        # 1. Sync & Data Pipeline Status
        st.markdown(
            """
            <div class="section-header">📥 1. نقل البيانات وتوحيد نماذج القواعد (Data Pipeline & Grouping)</div>
            """,
            unsafe_allow_html=True,
        )

        stat_col1, stat_col2 = st.columns([3, 1])
        with stat_col1:
            if b_data["has_imported"]:
                st.success(
                    f"✅ **تم استيراد ردود الأفعال القصوى وأبعاد ومواقع الأعمدة بنجاح من Module 1 (Flat Slabs)!**\n\n"
                    f"إجمالي عدد الأعمدة في المسقط العام: **{len(cols_list)} عمود**."
                )
            else:
                st.info(
                    f"ℹ️ **المسقط الافتراضي:** لم يتم تشغيل Module 1 في الجلسة الحالية، تم تحميل نموذج مسقط قياسي للمبنى ({len(cols_list)} عمود).\n"
                    f"يمكنك تشغيل Module 1 لحساب كامل الأحمال بدقة، أو إدخال/تعديل الأحمال أدناه مباشرة."
                )

        with stat_col2:
            if st.button("🔄 مزامنة واستيراد من Module 1", use_container_width=True, key="btn_resync_mod1"):
                st.rerun()

        # 2. Material & Soil Properties Expander
        with st.expander("🌱 مدخلات التربة وخواص المواد والخرسانة (Soil & Material Properties)", expanded=True):
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            with mc1:
                q_net = S.number_input("q_all,net (kg/cm²)", "tcf_q_net", min_value=0.5, max_value=5.0, step=0.1)
                st.caption("1.5 kg/cm² = 15 t/m²")
            with mc2:
                Fcu = S.number_input("Fcu (kg/cm²)", "tcf_Fcu", min_value=150, max_value=600, step=25)
            with mc3:
                Fy = S.number_input("Fy (kg/cm²)", "tcf_Fy", min_value=2000, max_value=6000, step=200)
            with mc4:
                cover = S.number_input("Cover (cm)", "tcf_cover", min_value=3, max_value=15, step=1)
            with mc5:
                Phi = S.selectbox("Main Rebar Φ (mm)", "tcf_Phi_index", options=[12, 16, 18, 22, 25])

        # 3. Governing Loads by Type Expander (Pu total int / edge / corner)
        with st.expander("🔩 ردود الأفعال القصوى للأعمدة (Governing Column Loads from Module 1)", expanded=True):
            gc1, gc2, gc3, gc4 = st.columns(4)
            with gc1:
                st.markdown("**🔹 عمود الركن (C₁)**")
                Pu1_val = st.number_input("P_u1 Total (ton)", min_value=1.0, max_value=3000.0,
                                          value=float(b_data["pu_corner"]), step=2.5, key="inp_pu_corner")
                st.caption(f"= {Pu1_val*9.80665:.1f} kN")
            with gc2:
                st.markdown("**🔹 العمود الجانبي (C₂)**")
                Pu2_val = st.number_input("P_u2 Total (ton)", min_value=1.0, max_value=3000.0,
                                          value=float(b_data["pu_edge"]), step=2.5, key="inp_pu_edge")
                st.caption(f"= {Pu2_val*9.80665:.1f} kN")
            with gc3:
                st.markdown("**🔹 العمود الداخلي (C₃)**")
                Pu3_val = st.number_input("P_u3 Total (ton)", min_value=1.0, max_value=3000.0,
                                          value=float(b_data["pu_int"]), step=2.5, key="inp_pu_int")
                st.caption(f"= {Pu3_val*9.80665:.1f} kN")
            with gc4:
                st.markdown("**📐 أبعاد الأعمدة (c × b)**")
                col_c = st.number_input("عمق العمود c (cm)", min_value=20, max_value=300, value=int(b_data["tc"]), step=5, key="inp_col_c")
                col_b = st.number_input("عرض العمود b (cm)", min_value=20, max_value=300, value=int(b_data["bc"]), step=5, key="inp_col_b")

        # Design the 3 Typical Isolated Footing Models: F1, F2, F3
        F1 = design_isolated_footing_model("F1", "قاعدة ركن", "C1", Pu1_val, col_c, col_b, q_net, Fcu, Fy, cover, Phi)
        F2 = design_isolated_footing_model("F2", "قاعدة جانبية", "C2", Pu2_val, col_c, col_b, q_net, Fcu, Fy, cover, Phi)
        F3 = design_isolated_footing_model("F3", "قاعدة داخلية", "C3", Pu3_val, col_c, col_b, q_net, Fcu, Fy, cover, Phi)

        footings_map = {
            "Corner": F1,
            "Edge": F2,
            "Interior": F3,
        }

        # 4. Clearance & Overlap Engine Execution
        overlap_res = check_building_clearances_and_overlaps(cols_list, footings_map)
        has_overlap = overlap_res["has_overlap"]

        combined_models = []
        if has_overlap:
            cf_counter = 1
            for p in overlap_res["overlapping_pairs"]:
                cf_obj = design_combined_footing_model(
                    f"comb-{cf_counter}",
                    p["col_A"],
                    p["col_B"],
                    p["spacing_m"],
                    q_net,
                    Fcu,
                    Fy,
                    cover,
                    Phi,
                )
                combined_models.append(cf_obj)
                cf_counter += 1

        # ── 5. ALERT BANNER ───────────────────────────────────────────────────
        if has_overlap:
            st.markdown(
                """
                <div style="background:#fee2e2; border:2px solid #ef4444; border-radius:12px; padding:18px 24px; margin: 16px 0 20px 0;">
                    <span style="font-size:26px;">🚨</span>
                    <b style="font-size:20px; color:#991b1b;">تنبيه إنشائي:</b>
                    <span style="font-size:18px; color:#7f1d1d; font-weight:700;">
                    القواعد المحددة بالخط الأخضر المتقطع هي قواعد متداخلة (المسافة الصافية Clearance &lt; 0.15 م)،
                    وسيتم تصميمها تلقائياً بنظام القواعد المشتركة (Combined Footings).
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background:#dcfce7; border:2px solid #22c55e; border-radius:12px; padding:18px 24px; margin: 16px 0 20px 0;">
                    <span style="font-size:26px;">✅</span>
                    <b style="font-size:20px; color:#166534;">النظام الإنشائي مستقر:</b>
                    <span style="font-size:18px; color:#14532d; font-weight:700;">
                    كامل النظام الإنشائي للأساسات مستقر كقواعد منفصلة ولا يوجد أي تداخل خرساني
                    (جميع المسافات الصافية Clearance &ge; 0.15 م).
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── 6. FOUNDATION GENERAL LAYOUT PLAN ─────────────────────────────────
        st.markdown(
            """
            <div class="section-header">📐 المسقط الأفقي العام للقواعد وفحص التداخل (Foundation General Layout Plan)</div>
            """,
            unsafe_allow_html=True,
        )

        fig_plan = draw_foundation_layout_plan(cols_list, footings_map, overlap_res, combined_models)
        st.pyplot(fig_plan, use_container_width=True)

        buf_p = io.BytesIO()
        fig_plan.savefig(buf_p, format="png", bbox_inches="tight", dpi=300)
        buf_p.seek(0)
        st.download_button(
            "📥 Download Foundation General Layout Plan (High-Res PNG)",
            buf_p.getvalue(),
            file_name="ECP203_Building_Foundations_Plan.png",
            mime="image/png",
            use_container_width=True,
            key="btn_dl_bld_plan",
        )
        plt.close(fig_plan)

        # ── 7. DYNAMIC STREAMLIT TABS ─────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            """
            <div class="section-header">📋 جداول التصميم والمخرجات الإنشائية (Foundation Schedules & Design Outputs)</div>
            """,
            unsafe_allow_html=True,
        )

        if has_overlap:
            tab_iso, tab_comb = st.tabs([
                "🔹 تصميم القواعد المنفصلة (Isolated Footings)",
                "🔸 تصميم القواعد المشتركة (Combined Footings)",
            ])
        else:
            tab_iso, = st.tabs([
                "🔹 تصميم القواعد المنفصلة (Isolated Footings)",
            ])

        # ── TAB 1: UNIFIED FOOTINGS SCHEDULE (ISOLATED + COMBINED) ───────────
        with tab_iso:
            st.markdown("#### 📋 جدول نماذج القواعد الموحد لأساسات المبنى (Unified Footings Schedule — ECP 203)")

            unified_schedule_data = []
            for f in [F1, F2, F3]:
                pc_L = f["L_cm"] + 40
                pc_B = f["B_cm"] + 40
                unified_schedule_data.append({
                    "نموذج القاعدة (Model)": f["model_name"],
                    "الأعمدة المرتكزة (Columns)": f["supported_col_str"],
                    "أقصى حمل تصميمي Pu (ton)": f"{f['Pu_ton']:.2f} ton",
                    "أبعاد المسلحة R.C. (cm)": f"{f['L_cm']} × {f['B_cm']} × {f['t_cm']}",
                    "أبعاد العادية P.C. (cm)": f"{pc_L} × {pc_B} × 20 (نظافة)",
                    "التسليح السفلي (Bottom RFT)": f"فرش: {f['rft_long_str']} | غطاء: {f['rft_short_str']}",
                    "التسليح العلوي الرئيسي (Top RFT)": "-" if f["t_cm"] < 80 else f["top_rft_str"],
                    "طول التماسك / الرفارف (Details)": f"Ld = {f['Ld_str']}",
                    "حالة التحقق الإنشائي (Status)": f["status_str"],
                })

            if has_overlap:
                for cf in combined_models:
                    cf_pc_L = cf["Lc_cm"] + 40
                    cf_pc_B = cf["Bc_cm"] + 40
                    unified_schedule_data.append({
                        "نموذج القاعدة (Model)": f"{cf['name']} (مشتركة)",
                        "الأعمدة المرتكزة (Columns)": cf["supported_cols"],
                        "أقصى حمل تصميمي Pu (ton)": f"Ru = {cf['Ru_ton']:.2f} ton",
                        "أبعاد المسلحة R.C. (cm)": f"{cf['Lc_cm']} × {cf['Bc_cm']} × {cf['tc_cm']}",
                        "أبعاد العادية P.C. (cm)": f"{cf_pc_L} × {cf_pc_B} × 20 (نظافة)",
                        "التسليح السفلي (Bottom RFT)": f"طولي: {cf['rft_bot_str']} | عرضي: {cf['rft_trans_str']}",
                        "التسليح العلوي الرئيسي (Top RFT)": f"علوي رئيسي: {cf['rft_top_str']} (-M={cf['M_top_tm']:.2f} t·m)",
                        "طول التماسك / الرفارف (Details)": f"رفارف: {cf['overhangs_str']}",
                        "حالة التحقق الإنشائي (Status)": cf["status_str"],
                    })

            unified_df = pd.DataFrame(unified_schedule_data)
            render_styled_table(unified_df)

            # Export Excel & CSV
            csv_tcf_data = unified_df.to_csv(index=False).encode('utf-8-sig')
            buf_tcf_xl = io.BytesIO()
            with pd.ExcelWriter(buf_tcf_xl, engine='openpyxl') as writer:
                unified_df.to_excel(writer, index=False, sheet_name='Footings_Schedule')
            excel_tcf_bytes = buf_tcf_xl.getvalue()

            tcf_c1, tcf_c2 = st.columns(2)
            with tcf_c1:
                st.download_button(
                    label="📊 تصدير جدول نماذج القواعد الموحد (Excel .xlsx)",
                    data=excel_tcf_bytes,
                    file_name="Unified_Building_Footings_Schedule.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="btn_dl_unified_excel_tcf",
                )
            with tcf_c2:
                st.download_button(
                    label="📥 تصدير جدول نماذج القواعد الموحد (CSV)",
                    data=csv_tcf_data,
                    file_name="Unified_Building_Footings_Schedule.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_dl_unified_csv_tcf",
                )

            with st.expander("🔍 تفاصيل التحققات الإنشائية والإجهادات (Detailed Stresses & Checks)", expanded=False):
                for f in [F1, F2, F3]:
                    st.markdown(f"##### 📌 نموذج {f['model_name']} — {f['dims_str']}")
                    c_det1, c_det2, c_det3, c_det4 = st.columns(4)
                    c_det1.metric("إجهاد التلامس (q_act)", f"{f['q_act']:.2f} kg/cm²", f"المسموح: {f['q_net']:.2f}")
                    c_det2.metric("إجهاد القص (One-Way Shear)", f"{f['tau_s']:.2f} kg/cm²", f"المسموح: {f['tau_s_allow']:.2f}")
                    c_det3.metric("إجهاد الثقب (Punching)", f"{f['tau_p']:.2f} kg/cm²", f"المسموح: {f['tau_p_allow']:.2f}")
                    c_det4.metric("أقصى عزم انحناء (Mu)", f"{f['M_L_tm']:.2f} t·m", f"d = {f['d_cm']:.1f} cm")
                    st.markdown("---")

        # ── TAB 2: COMBINED FOOTINGS STRUCTURAL DETAILS ──────────────────────
        if has_overlap:
            with tab_comb:
                st.markdown("#### 🧱 تفاصيل وحسابات القواعد المشتركة الناتجة عن التداخل (Combined Footings Analysis)")

                with st.expander("🔍 تفاصيل العزوم والتصميم الإنشائي للقواعد المشتركة (Bending & Details)", expanded=False):
                    for cf in combined_models:
                        st.markdown(f"##### 🧱 نموذج {cf['name']} ({cf['supported_cols']}) — البحر S = {cf['S_m']} m")
                        cc1, cc2, cc3, cc4 = st.columns(4)
                        cc1.metric("الحمل الإجمالي Ru", f"{cf['Ru_ton']:.1f} ton", f"P1={cf['P1_ton']:.1f}, P2={cf['P2_ton']:.1f}")
                        cc2.metric("عزم علوي سالب (-M_top)", f"{cf['M_top_tm']:.2f} t·m", "تسليح علوي رئيسي")
                        cc3.metric("عزم كابولي سفلي (+M_bot)", f"{cf['M_bot_max_tm']:.2f} t·m", "تسليح سفلي رئيسي")
                        cc4.metric("إجهاد التربة الفعلي q_act", f"{cf['q_act']:.2f} kg/cm²", f"المسموح: {cf['q_net']:.2f}")
                        st.markdown("---")

        _render_structural_tutorial()

    # ══════════════════════════════════════════════════════════════════════════
    #  B. MANUAL QUICK TWO-COLUMN MODE (PRESERVED)
    # ══════════════════════════════════════════════════════════════════════════
    else:
        st.markdown(
            """
            <div class="section-header">📥 مدخلات التصميم اليدوي السريع لقاعدتين (Manual Two-Column Inputs)</div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("📝 Column & Soil Data (بيانات الأعمدة والتربة)", expanded=True):
            ic1, ic2, ic3 = st.columns(3)
            with ic1:
                st.markdown("**🔩 Column 1 (C₁)**")
                P1 = S.number_input("Service Load P₁ (ton)", "tcf_P1", min_value=1.0, max_value=3000.0, step=5.0)
                c1 = S.number_input("c₁ — parallel (cm)", "tcf_c1", min_value=15, max_value=300, step=5)
                b1 = S.number_input("b₁ — perpendicular (cm)", "tcf_b1", min_value=15, max_value=300, step=5)

            with ic2:
                st.markdown("**🔩 Column 2 (C₂)**")
                P2 = S.number_input("Service Load P₂ (ton)", "tcf_P2", min_value=1.0, max_value=3000.0, step=5.0)
                c2 = S.number_input("c₂ — parallel (cm)", "tcf_c2", min_value=15, max_value=300, step=5)
                b2 = S.number_input("b₂ — perpendicular (cm)", "tcf_b2", min_value=15, max_value=300, step=5)

            with ic3:
                st.markdown("**🌱 Soil & Materials**")
                S_dist = S.number_input("Spacing S (m)", "tcf_S", min_value=0.5, max_value=30.0, step=0.25)
                q_net = S.number_input("q_all,net (kg/cm²)", "tcf_q_net", min_value=0.5, max_value=5.0, step=0.1)
                Fcu = S.number_input("Fcu (kg/cm²)", "tcf_Fcu", min_value=150, max_value=600, step=25)
                Fy = S.number_input("Fy (kg/cm²)", "tcf_Fy", min_value=2000, max_value=6000, step=200)
                cover = S.number_input("Cover (cm)", "tcf_cover", min_value=3, max_value=15, step=1)
                Phi = S.selectbox("Main Bar Φ (mm)", "tcf_Phi_index", options=[12, 16, 18, 22, 25])

        f1_quick = design_isolated_footing_model("F1", "C1", "C1", P1 * 1.5, c1, b1, q_net, Fcu, Fy, cover, Phi)
        f2_quick = design_isolated_footing_model("F2", "C2", "C2", P2 * 1.5, c2, b2, q_net, Fcu, Fy, cover, Phi)

        clr_quick = S_dist - (f1_quick["L_cm"] / 200.0 + f2_quick["L_cm"] / 200.0)
        mode_q = "isolated" if clr_quick >= 0.15 else "combined"

        if mode_q == "isolated":
            st.success(f"🟢 **النوع المحدد: قواعد منفصلة (ISOLATED FOOTINGS) — Clearance = {clr_quick*100:.0f} cm ≥ 15 cm ✅**")
        else:
            st.warning(f"🟠 **النوع المحدد: قاعدة مشتركة (COMBINED FOOTING) — Clearance = {clr_quick*100:.0f} cm < 15 cm ⚠️**")

        colA_dict = {"id": "C1", "tc": c1, "bc": b1, "pu_tot": P1 * 1.5}
        colB_dict = {"id": "C2", "tc": c2, "bc": b2, "pu_tot": P2 * 1.5}

        if mode_q == "combined":
            cf_quick = design_combined_footing_model("comb-1", colA_dict, colB_dict, S_dist, q_net, Fcu, Fy, cover, Phi)
            fig_q = _draw_plan("combined", S_m=S_dist, c1_cm=c1, b1_cm=b1, c2_cm=c2, b2_cm=b2,
                               Lc_cm=cf_quick["Lc_cm"], Bc_cm=cf_quick["Bc_cm"],
                               x1_cm=cf_quick["x1_cm"], x2_cm=cf_quick["x2_cm"])
        else:
            fig_q = _draw_plan("isolated", S_m=S_dist, c1_cm=c1, b1_cm=b1, c2_cm=c2, b2_cm=b2,
                               L1_cm=f1_quick["L_cm"], B1_cm=f1_quick["B_cm"],
                               L2_cm=f2_quick["L_cm"], B2_cm=f2_quick["B_cm"])

        st.pyplot(fig_q, use_container_width=True)
        plt.close(fig_q)

        _render_structural_tutorial()
