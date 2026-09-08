"""
Module 10 — Reinforced Concrete Corner Footing with Diagonal Strap Beam (ECP 203)
=================================================================================
تصميم قاعدة جار ركن (محصورة بين حدي جار متعامدين) ومتصلة بقاعدة داخلية بشداد على المائل
Standard Metric Units per ECP 203:
  • Loads & Reactions : ton · kg  (1 ton = 1,000 kg)
  • Moments           : ton·m     (1 ton·m = 100,000 kg·cm)
  • Stresses          : kg/cm²    (q_all,net, Fcu, Fy, tau)
  • Section Dims      : cm        (Columns, Beams, Footing Thickness, Cover)
  • Spans & Plan Dims : m         (X2, Y2, S, ec_x, ec_y, L1x, L1y, L2x, L2y)
  • Rebar Dims        : mm · cm   (Φ mm, spacing cm)
Run from app.py via:  render_diagonal_strap_module()
"""

import math
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

_COVER_CM = 7.0  # cm (ECP 203 substructure cover)


# ── Design Helpers (Metric: kg, cm, ton, ton·m) ──────────────────────────────
def _as_design_cm2(Mu_kgcm: float, d_cm: float, b_cm: float, Fcu: float, Fy: float) -> float:
    """Required steel area (cm²) using Whitney stress block per ECP 203."""
    if Mu_kgcm <= 0 or d_cm <= 0 or b_cm <= 0:
        return 0.0015 * b_cm * d_cm

    a = 0.10 * d_cm
    for _ in range(30):
        lever = d_cm - a / 2.0
        if lever <= 0.50 * d_cm:
            lever = 0.50 * d_cm
        As = Mu_kgcm / (0.9 * Fy * lever)
        a = (As * Fy) / (0.85 * Fcu * b_cm) if (Fcu * b_cm) > 0 else 0

    As_min = max(
        0.0015 * b_cm * d_cm,
        (0.225 * math.sqrt(max(0.0, Fcu)) / Fy) * b_cm * d_cm
    )
    return max(As, As_min)


def _bar_combo_cm2(As_cm2: float, bar_dia_mm: int) -> int:
    """Minimum number of bars of given diameter."""
    area_bar_cm2 = math.pi * (bar_dia_mm / 10.0) ** 2 / 4.0
    return max(2, math.ceil(As_cm2 / area_bar_cm2))


# ── Canonical defaults (Strictly in Metric Engineering Units) ────────────────
_DEFAULTS_M10 = {
    # ── Geometry & Coordinates ──
    "edge_clearance_x": 0.0,  # m (المسافة لحد الجار الرأسي X=0)
    "edge_clearance_y": 0.0,  # m (المسافة لحد الجار الأفقي Y=0)
    "a1": 30.0,               # cm (بعد عمود الركن في اتجاه X)
    "b1": 60.0,               # cm (بعد عمود الركن في اتجاه Y)
    "X2": 4.50,               # m (إحداثي X لمركز العمود الداخلي)
    "Y2": 3.80,               # m (إحداثي Y لمركز العمود الداخلي)
    "a2": 40.0,               # cm (بعد العمود الداخلي في اتجاه X)
    "b2": 50.0,               # cm (بعد العمود الداخلي في اتجاه Y)
    # ── Loads ──
    "P1_u": 120.0,            # ton (أقصى حمل لعمود الركن C1)
    "P2_u": 180.0,            # ton (أقصى حمل للعمود الداخلي C2)
    "col_weight_factor": 1.00,# معامل وزن الأعمدة
    "P1_w": 80.0,             # ton (P1_u / 1.5)
    "P2_w": 120.0,            # ton (P2_u / 1.5)
    # ── Soil & Materials ──
    "q_all_net": 1.50,        # kg/cm² (إجهاد التربة الصافي المسموح به)
    "fcu": 250.0,             # kg/cm² (رتبة الخرسانة)
    "fy": 4000.0,             # kg/cm² (إجهاد خضوع حديد التسليح)
    "t_pc": 10.0,             # cm (سماكة الخرسانة العادية)
    "strap_b": 40.0,          # cm (عرض كمرة الشداد المائل)
    "strap_D": 170.0,         # cm (عمق كمرة الشداد المائل)
    # ── Footing Dimensions ──
    "L1x": 2.95,              # m (بعد قاعدة الركن في اتجاه X)
    "L1y": 2.75,              # m (بعد قاعدة الركن في اتجاه Y)
    "t1": 80.0,               # cm (سماكة قاعدة الركن)
    "L2x": 2.85,              # m (بعد القاعدة الداخلية في اتجاه X)
    "L2y": 2.85,              # m (بعد القاعدة الداخلية في اتجاه Y)
    "t2": 60.0,               # cm (سماكة القاعدة الداخلية)
    # ── Rebar ──
    "long_bar_dia": 22,       # mm (قطر الحديد الطولي للشداد)
    "stirrup_dia": 10,        # mm (قطر الكانات)
    "stirrup_per_m": 5,       # كانات/م
    "stirrup_spacing": 20.0,  # cm
    "trans_bar_dia": 16,      # mm (قطر حديد القواعد)
    "is_calculated": False,
}


def _normalize_m10_dict(d: dict) -> dict:
    """Ensure all expected keys exist with valid types and default fallbacks."""
    out = dict(_DEFAULTS_M10)
    out.update(d)
    # Col weight factor
    cwf = float(out.get("col_weight_factor", 1.00))
    p1u = float(out.get("P1_u", 120.0))
    p2u = float(out.get("P2_u", 180.0))
    out["P1_w"] = round((p1u * cwf) / 1.5, 2)
    out["P2_w"] = round((p2u * cwf) / 1.5, 2)

    # Self-healing guard: if stored dimensions are corrupted (< 1.0m) recompute safe defaults
    if (
        float(out.get("L1x", 0)) < 1.0 or
        float(out.get("L1y", 0)) < 1.0 or
        float(out.get("L2x", 0)) < 1.0 or
        float(out.get("L2y", 0)) < 1.0 or
        float(out.get("strap_D", 0)) < 50.0
    ):
        rec_safe = _calc_recommended_dimensions(out)
        out["L1x"] = rec_safe["L1x"]
        out["L1y"] = rec_safe["L1y"]
        out["t1"] = rec_safe["t1"]
        out["L2x"] = rec_safe["L2x"]
        out["L2y"] = rec_safe["L2y"]
        out["t2"] = rec_safe["t2"]
        out["strap_D"] = rec_safe["strap_D"]
        out["is_manual_override"] = False

    return out


def _init_state_m10():
    """Ensure session_state['module_10_data'] exists and is properly initialized."""
    from modules.settings import cfg_val
    if "module_10_data" not in st.session_state:
        nested = cfg_val("module_10_diagonal_strap")
        if isinstance(nested, dict):
            d = _normalize_m10_dict(nested)
        else:
            d = dict(_DEFAULTS_M10)
        st.session_state["module_10_data"] = d
    else:
        st.session_state["module_10_data"] = _normalize_m10_dict(st.session_state["module_10_data"])


# ── Recommended Dimensions Calculation Engine ────────────────────────────────
def _calc_recommended_dimensions(d: dict) -> dict:
    """
    Compute structural engineering recommended dimensions for Corner Footing
    and Diagonal Strap Beam per ECP 203.
    Aligns eccentricity vector along the diagonal strap to prevent torsion.
    """
    ec_x = float(d.get("edge_clearance_x", 0.0))
    ec_y = float(d.get("edge_clearance_y", 0.0))
    a1_m = float(d.get("a1", 30.0)) / 100.0
    b1_m = float(d.get("b1", 60.0)) / 100.0
    a2_m = float(d.get("a2", 40.0)) / 100.0
    b2_m = float(d.get("b2", 50.0)) / 100.0

    X1 = ec_x + a1_m / 2.0
    Y1 = ec_y + b1_m / 2.0
    X2 = max(X1 + 1.0, float(d.get("X2", 4.50)))
    Y2 = max(Y1 + 1.0, float(d.get("Y2", 3.80)))

    dX = X2 - X1
    dY = Y2 - Y1
    S = math.sqrt(dX ** 2 + dY ** 2)
    theta = math.atan2(dY, dX) if dX > 0 else math.pi / 4.0
    tan_th = math.tan(theta) if abs(math.cos(theta)) > 1e-4 else 1.0
    cos_th = math.cos(theta)
    sin_th = math.sin(theta)

    cwf = float(d.get("col_weight_factor", 1.00))
    P1u = float(d.get("P1_u", 120.0)) * cwf
    P2u = float(d.get("P2_u", 180.0)) * cwf
    P1w = P1u / 1.5
    P2w = P2u / 1.5

    q_all_net_kgcm2 = float(d.get("q_all_net", 1.50))
    q_ton_m2 = q_all_net_kgcm2 * 10.0
    fcu = float(d.get("fcu", 250.0))
    sb_cm = float(d.get("strap_b", 40.0))
    sb_m = sb_cm / 100.0

    # 1. Footing 1 (Corner Footing) Sizing with Zero Torsion
    C_const = (b1_m + 2.0 * ec_y) - tan_th * (a1_m + 2.0 * ec_x)
    L1x_min = a1_m + 2.0 * ec_x + 0.50
    L1y_min = b1_m + 2.0 * ec_y + 0.50

    # Initial quadratic estimate for L1x
    Area1_approx = 1.30 * (P1w / q_ton_m2)
    A_q = max(0.05, tan_th)
    B_q = C_const
    C_q = -max(Area1_approx, 1.5)
    disc = max(0.0, B_q ** 2 - 4.0 * A_q * C_q)
    L1x = (-B_q + math.sqrt(disc)) / (2.0 * A_q)
    L1x = max(L1x, L1x_min, 1.60)

    # Iterative convergence to guarantee actual soil pressure q_act1 <= q_all_net
    for _ in range(60):
        L1y = tan_th * L1x + C_const
        if L1y < L1y_min:
            L1y = L1y_min
            L1x = (L1y - C_const) / tan_th
        ex = (L1x / 2.0) - X1
        ey = (L1y / 2.0) - Y1
        e_long = ex * cos_th + ey * sin_th
        X_arm = max(0.50, S - e_long)
        R1w = P1w * S / X_arm
        q_calc = (R1w / (L1x * L1y)) / 10.0
        if q_calc <= q_all_net_kgcm2 * 0.985:
            break
        ratio = math.sqrt(q_calc / (q_all_net_kgcm2 * 0.97))
        L1x = max(L1x * ratio, L1x + 0.05)

    # Round to standard 5 cm increments
    L1x_rec = math.ceil(L1x * 20.0) / 20.0
    L1y_rec = math.ceil((tan_th * L1x_rec + C_const) * 20.0) / 20.0

    # Final verification loop after rounding to strictly enforce q_act1 <= q_all_net
    for _ in range(25):
        ex = (L1x_rec / 2.0) - X1
        ey = (L1y_rec / 2.0) - Y1
        e_long = ex * cos_th + ey * sin_th
        X_arm = max(0.50, S - e_long)
        R1w = P1w * S / X_arm
        q_act1 = (R1w / (L1x_rec * L1y_rec)) / 10.0
        if q_act1 <= q_all_net_kgcm2:
            break
        L1x_rec += 0.05
        L1y_rec = math.ceil((tan_th * L1x_rec + C_const) * 20.0) / 20.0

    # 2. Footing 2 (Interior Footing) Sizing
    R2w = (P1w + P2w) - R1w
    P2_design = max(R2w, P2w)
    Area2_req = P2_design / q_ton_m2
    L2_side = math.sqrt(max(Area2_req, 1.5))
    L2x_rec = math.ceil(max(L2_side, a2_m + 0.50, sb_m + 0.50) * 20.0) / 20.0
    L2y_rec = math.ceil(max(Area2_req / L2x_rec, b2_m + 0.50, sb_m + 0.50) * 20.0) / 20.0
    while (P2_design / (L2x_rec * L2y_rec)) / 10.0 > q_all_net_kgcm2:
        L2x_rec += 0.05
        L2y_rec = math.ceil((Area2_req / L2x_rec) * 20.0) / 20.0

    # 3. Footing thicknesses (cm)
    corners = [(0, 0), (L1x_rec, 0), (L1x_rec, L1y_rec), (0, L1y_rec)]
    max_cant1 = max(max(0.20, abs(-(cx - X1) * sin_th + (cy - Y1) * cos_th) - sb_m / 2.0) for cx, cy in corners)
    cant2 = max(0.20, (L2x_rec - a2_m) / 2.0, (L2y_rec - b2_m) / 2.0)

    t1_rec = float(math.ceil(max(60.0, max_cant1 * 100.0 / 2.4) / 5.0) * 5.0)
    t2_rec = float(math.ceil(max(50.0, cant2 * 100.0 / 2.2) / 5.0) * 5.0)

    # 4. Diagonal Strap Beam Depth D_strap (cm)
    R1u = P1u * S / X_arm
    L_diag1 = min(L1x_rec / cos_th, L1y_rec / sin_th) if (cos_th > 0 and sin_th > 0) else math.sqrt(L1x_rec**2 + L1y_rec**2)
    L_diag1 = max(1.5, L_diag1)
    wu1 = R1u / L_diag1
    s_col1 = X1 * cos_th + Y1 * sin_th
    x0_rec = min(L_diag1, max(s_col1, P1u / wu1 if wu1 > 0 else s_col1))
    Mu_neg = abs(P1u * (x0_rec - s_col1) - wu1 * (x0_rec ** 2) / 2.0)

    d_flex = 4.5 * math.sqrt(max(0.0, (Mu_neg * 1e5) / (fcu * sb_cm)))
    d_span = (S * 100.0) / 5.0
    Vu = abs(R1u - P1u)
    d_shear = (Vu * 1000.0) / (sb_cm * 20.0) if sb_cm > 0 else 60.0
    D_req = max(d_flex + 7.5, d_shear + 7.5, d_span, 70.0)
    strap_D_rec = float(math.ceil(D_req / 10.0) * 10.0)

    return {
        "L1x": round(max(0.80, min(15.0, L1x_rec)), 2),
        "L1y": round(max(0.80, min(15.0, L1y_rec)), 2),
        "t1": round(max(30.0, min(250.0, t1_rec)), 1),
        "L2x": round(max(0.80, min(15.0, L2x_rec)), 2),
        "L2y": round(max(0.80, min(15.0, L2y_rec)), 2),
        "t2": round(max(30.0, min(250.0, t2_rec)), 1),
        "strap_D": round(max(40.0, min(300.0, strap_D_rec)), 1),
    }


# ── Full Structural Calculation Engine ───────────────────────────────────────
def _calculate(d_in: dict) -> dict:
    d = _normalize_m10_dict(d_in)

    # Clearances and Column 1 (Corner)
    ec_x = float(d["edge_clearance_x"])
    ec_y = float(d["edge_clearance_y"])
    a1_m = float(d["a1"]) / 100.0
    b1_m = float(d["b1"]) / 100.0
    a2_m = float(d["a2"]) / 100.0
    b2_m = float(d["b2"]) / 100.0

    X1 = ec_x + a1_m / 2.0
    Y1 = ec_y + b1_m / 2.0

    # Column 2 Center Coordinates
    X2 = float(d["X2"])
    Y2 = float(d["Y2"])

    # Geometry & Angle
    dX = X2 - X1
    dY = Y2 - Y1
    S = math.sqrt(dX ** 2 + dY ** 2)
    theta = math.atan2(dY, dX)
    theta_deg = theta * 180.0 / math.pi
    cos_th = math.cos(theta)
    sin_th = math.sin(theta)

    # Loads in ton
    cwf = float(d.get("col_weight_factor", 1.00))
    P1u = float(d.get("P1_u", 120.0)) * cwf
    P2u = float(d.get("P2_u", 180.0)) * cwf
    P1w = P1u / 1.5
    P2w = P2u / 1.5

    # Soil & Materials
    q_all_net_kgcm2 = float(d["q_all_net"])
    q_ton_m2 = q_all_net_kgcm2 * 10.0
    fcu_kgcm2 = float(d["fcu"])
    fy_kgcm2 = float(d["fy"])

    # Strap Beam Dimensions
    sb_cm = float(d["strap_b"])
    sD_cm = float(d["strap_D"])
    sb_m = sb_cm / 100.0
    sD_m = sD_cm / 100.0

    # Footing Dimensions
    L1x = float(d.get("L1x", 2.20))
    L1y = float(d.get("L1y", 2.60))
    t1_cm = float(d.get("t1", 60.0))
    t1_m = t1_cm / 100.0

    L2x = float(d.get("L2x", 2.80))
    L2y = float(d.get("L2y", 2.80))
    t2_cm = float(d.get("t2", 55.0))
    t2_m = t2_cm / 100.0

    # 1. Eccentricity analysis
    X_f1 = L1x / 2.0
    Y_f1 = L1y / 2.0
    ex = X_f1 - X1
    ey = Y_f1 - Y1
    e_res = math.sqrt(ex ** 2 + ey ** 2)
    theta_e_deg = math.atan2(ey, ex) * 180.0 / math.pi if (abs(ex) > 1e-4 or abs(ey) > 1e-4) else 0.0

    # Decompose eccentricity into longitudinal (along strap) and transverse
    e_long = ex * cos_th + ey * sin_th
    e_trans = -ex * sin_th + ey * cos_th
    torsion_Mtu = abs(P1u * e_trans)  # ton·m

    # Lever Arm
    X_arm = max(0.50, S - e_long)

    # 2. Service Reactions
    R1w = P1w * S / X_arm
    R2w = (P1w + P2w) - R1w
    P2_serv_design = max(R2w, P2w)

    # 3. Ultimate Reactions
    R1u = P1u * S / X_arm
    R2u = (P1u + P2u) - R1u
    P2_ult_design = max(R2u, P2u)

    # 4. Actual Contact Soil Pressures
    Area1 = L1x * L1y
    Area2 = L2x * L2y
    q_act1_tm2 = R1w / Area1 if Area1 > 0 else 999.0
    q_act1 = q_act1_tm2 / 10.0  # kg/cm²

    q_act2_tm2 = P2_serv_design / Area2 if Area2 > 0 else 999.0
    q_act2 = q_act2_tm2 / 10.0  # kg/cm²

    qu1_tm2 = R1u / Area1 if Area1 > 0 else 999.0
    qu2_tm2 = P2_ult_design / Area2 if Area2 > 0 else 999.0

    # 5. Diagonal Strap Beam Analysis
    if cos_th > 0.05 and sin_th > 0.05:
        L_diag1 = min(L1x / cos_th, L1y / sin_th)
    else:
        L_diag1 = math.sqrt(L1x**2 + L1y**2)
    L_diag1 = max(1.0, L_diag1)

    wu1 = R1u / L_diag1
    s_col1 = X1 * cos_th + Y1 * sin_th
    x0 = min(L_diag1, max(s_col1, P1u / wu1 if wu1 > 0 else s_col1))

    Mu_neg_tm = -(P1u * (x0 - s_col1) - wu1 * (x0 ** 2) / 2.0)
    Mu_max_strap = abs(Mu_neg_tm)
    Mu_pos_tm = Mu_max_strap * 0.20

    long_dia_mm = float(d["long_bar_dia"])
    stirrup_dia_mm = float(d["stirrup_dia"])
    d_strap_cm = sD_cm - _COVER_CM - (stirrup_dia_mm / 10.0) - (long_dia_mm / 20.0)
    d_strap_m = d_strap_cm / 100.0

    As_top_cm2 = _as_design_cm2(Mu_max_strap * 1e5, d_strap_cm, sb_cm, fcu_kgcm2, fy_kgcm2)
    As_bot_cm2 = _as_design_cm2(Mu_pos_tm * 1e5, d_strap_cm, sb_cm, fcu_kgcm2, fy_kgcm2)
    n_top = _bar_combo_cm2(As_top_cm2, int(long_dia_mm))
    n_bot = _bar_combo_cm2(As_bot_cm2, int(long_dia_mm))

    # Shear in Strap Beam
    Vu_ton = abs(R1u - P1u)
    Vu_kg = Vu_ton * 1000.0
    tau_kgcm2 = Vu_kg / (sb_cm * d_strap_cm) if (sb_cm * d_strap_cm) > 0 else 0.0

    vc_kgcm2 = 0.24 * math.sqrt(max(0.0, (fcu_kgcm2 / 10.0) / 1.5)) * 10.0
    vc_max_kgcm2 = 0.70 * math.sqrt(max(0.0, (fcu_kgcm2 / 10.0) / 1.5)) * 10.0

    concrete_shear_ok = tau_kgcm2 <= vc_kgcm2
    shear_max_ok = tau_kgcm2 <= vc_max_kgcm2

    excess_kgcm2 = max(0.0, tau_kgcm2 - (vc_kgcm2 / 2.0))
    fy_stirrup = 2400.0 if fy_kgcm2 <= 2800 else 4000.0
    n_branches = 4 if sb_cm >= 50.0 else 2
    As_one_branch_cm2 = math.pi * (stirrup_dia_mm / 10.0) ** 2 / 4.0
    Asv_one_stirrup_cm2 = n_branches * As_one_branch_cm2

    if excess_kgcm2 > 0:
        s_calc_cm = (Asv_one_stirrup_cm2 * (fy_stirrup / 1.15)) / (excess_kgcm2 * sb_cm) if (excess_kgcm2 * sb_cm) > 0 else 20.0
        s_calc_cm = max(8.0, min(20.0, s_calc_cm))
        Asv_req_cm2_m = (Asv_one_stirrup_cm2 / s_calc_cm) * 100.0
    else:
        Asv_req_cm2_m = max(3.5, (0.40 * sb_cm * 100.0) / (fy_stirrup / 1.15))

    stirrup_per_m = float(d.get("stirrup_per_m", 5.0))
    Asv_prov_cm2_m = stirrup_per_m * Asv_one_stirrup_cm2
    stirrups_shear_ok = (concrete_shear_ok or (Asv_prov_cm2_m >= Asv_req_cm2_m)) and shear_max_ok

    # 6. Footing Cantilever Moments & Transverse Reinforcement
    cant1_x = max(0.20, L1x - X1 - a1_m / 2.0)
    cant1_y = max(0.20, L1y - Y1 - b1_m / 2.0)
    Mu_trans1_x = qu1_tm2 * (cant1_x ** 2) / 2.0
    Mu_trans1_y = qu1_tm2 * (cant1_y ** 2) / 2.0
    Mu_trans1 = max(Mu_trans1_x, Mu_trans1_y)

    d1_cm = t1_cm - _COVER_CM - 1.0
    trans_dia_mm = float(d["trans_bar_dia"])
    As_trans1_per_m = _as_design_cm2(Mu_trans1 * 1e5, d1_cm, 100.0, fcu_kgcm2, fy_kgcm2)

    cant2_x = max(0.20, (L2x - a2_m) / 2.0)
    cant2_y = max(0.20, (L2y - b2_m) / 2.0)
    Mu_trans2_x = qu2_tm2 * (cant2_x ** 2) / 2.0
    Mu_trans2_y = qu2_tm2 * (cant2_y ** 2) / 2.0
    Mu_trans2 = max(Mu_trans2_x, Mu_trans2_y)

    d2_cm = t2_cm - _COVER_CM - 1.0
    As_trans2_per_m = _as_design_cm2(Mu_trans2 * 1e5, d2_cm, 100.0, fcu_kgcm2, fy_kgcm2)

    return {
        "X1": X1, "Y1": Y1, "X2": X2, "Y2": Y2,
        "dX": dX, "dY": dY, "S": S,
        "theta": theta, "theta_deg": theta_deg,
        "cos_th": cos_th, "sin_th": sin_th,
        "ec_x": ec_x, "ec_y": ec_y,
        "a1_m": a1_m, "b1_m": b1_m, "a2_m": a2_m, "b2_m": b2_m,
        "sb_m": sb_m, "sD_cm": sD_cm, "d_strap_cm": d_strap_cm,
        "L1x": L1x, "L1y": L1y, "t1_cm": t1_cm,
        "L2x": L2x, "L2y": L2y, "t2_cm": t2_cm,
        "ex": ex, "ey": ey, "e_res": e_res,
        "theta_e_deg": theta_e_deg,
        "e_long": e_long, "e_trans": e_trans,
        "torsion_Mtu": torsion_Mtu,
        "X_arm": X_arm,
        "P1w": P1w, "P2w": P2w, "P1u": P1u, "P2u": P2u,
        "R1w": R1w, "R2w": R2w, "R1u": R1u, "R2u": R2u,
        "q_act1": q_act1, "q_act2": q_act2,
        "qu1_tm2": qu1_tm2, "qu2_tm2": qu2_tm2,
        "L_diag1": L_diag1, "wu1": wu1,
        "s_col1": s_col1, "x0": x0,
        "Mu_max_strap": Mu_max_strap, "Mu_neg_tm": Mu_neg_tm, "Mu_pos_tm": Mu_pos_tm,
        "As_top_cm2": As_top_cm2, "n_top": n_top,
        "As_bot_cm2": As_bot_cm2, "n_bot": n_bot,
        "Vu_ton": Vu_ton, "tau_kgcm2": tau_kgcm2,
        "vc_kgcm2": vc_kgcm2, "vc_max_kgcm2": vc_max_kgcm2,
        "concrete_shear_ok": concrete_shear_ok,
        "shear_max_ok": shear_max_ok,
        "stirrups_shear_ok": stirrups_shear_ok,
        "n_branches": n_branches,
        "Asv_req_cm2_m": Asv_req_cm2_m,
        "Asv_prov_cm2_m": Asv_prov_cm2_m,
        "stirrup_per_m": stirrup_per_m,
        "Mu_trans1": Mu_trans1, "As_trans1_per_m": As_trans1_per_m,
        "Mu_trans2": Mu_trans2, "As_trans2_per_m": As_trans2_per_m,
    }


# ── Dynamic Interactive Plan View Drawing ────────────────────────────────────
def _draw_plan(d: dict, r: dict):
    fig, ax = plt.subplots(figsize=(13, 7.5))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    L1x, L1y = r["L1x"], r["L1y"]
    L2x, L2y = r["L2x"], r["L2y"]
    X1, Y1 = r["X1"], r["Y1"]
    X2, Y2 = r["X2"], r["Y2"]
    a1_m, b1_m = r["a1_m"], r["b1_m"]
    a2_m, b2_m = r["a2_m"], r["b2_m"]
    sb_m = r["sb_m"]
    theta = r["theta"]
    cos_th, sin_th = r["cos_th"], r["sin_th"]
    tpc = float(d.get("t_pc", 10.0)) / 100.0

    # 1. Plain Concrete (PC) for Footing 1 & 2
    if tpc > 0:
        ax.add_patch(patches.Rectangle(
            (0.0, 0.0), L1x + tpc, L1y + tpc,
            lw=1.0, edgecolor="#94a3b8", facecolor="#334155", alpha=0.35, ls="--",
            label="Plain Concrete (خرسانة عادية)",
        ))
        f2_pc_x = X2 - L2x / 2.0 - tpc
        f2_pc_y = Y2 - L2y / 2.0 - tpc
        ax.add_patch(patches.Rectangle(
            (f2_pc_x, f2_pc_y), L2x + 2 * tpc, L2y + 2 * tpc,
            lw=1.0, edgecolor="#94a3b8", facecolor="#334155", alpha=0.35, ls="--",
        ))

    # 2. Footing 1 (Corner Footing RC)
    ax.add_patch(patches.FancyBboxPatch(
        (0.0, 0.0), L1x, L1y, boxstyle="round,pad=0.015",
        lw=2.0, edgecolor="#38bdf8", facecolor="#1d4ed8", alpha=0.38,
        label="Footing 1 — قاعدة الجار الركن",
    ))

    # 3. Footing 2 (Interior Footing RC)
    f2_x = X2 - L2x / 2.0
    f2_y = Y2 - L2y / 2.0
    ax.add_patch(patches.FancyBboxPatch(
        (f2_x, f2_y), L2x, L2y, boxstyle="round,pad=0.015",
        lw=2.0, edgecolor="#38bdf8", facecolor="#1d4ed8", alpha=0.38,
        label="Footing 2 — القاعدة الداخلية",
    ))

    # 4. Diagonal Strap Beam (Rotated Polygon)
    u_vec = np.array([cos_th, sin_th])
    n_vec = np.array([-sin_th, cos_th])
    strap_start = np.array([X1, Y1]) - 0.20 * u_vec
    strap_end = np.array([X2, Y2]) + (a2_m / 2.0 + 0.15) * u_vec
    p1 = strap_start + (sb_m / 2.0) * n_vec
    p2 = strap_end + (sb_m / 2.0) * n_vec
    p3 = strap_end - (sb_m / 2.0) * n_vec
    p4 = strap_start - (sb_m / 2.0) * n_vec
    strap_poly = patches.Polygon(
        [p1, p2, p3, p4], closed=True,
        lw=1.6, edgecolor="#4ade80", facecolor="#166534", alpha=0.65,
        label="Diagonal Strap Beam (كمرة الشداد المائل)",
    )
    ax.add_patch(strap_poly)

    # 5. Columns
    c1_x0 = X1 - a1_m / 2.0
    c1_y0 = Y1 - b1_m / 2.0
    ax.add_patch(patches.Rectangle(
        (c1_x0, c1_y0), a1_m, b1_m,
        lw=1.8, edgecolor="#ffffff", facecolor="#475569", hatch="//",
        label="Col 1 — عمود الركن C1",
    ))

    c2_x0 = X2 - a2_m / 2.0
    c2_y0 = Y2 - b2_m / 2.0
    ax.add_patch(patches.Rectangle(
        (c2_x0, c2_y0), a2_m, b2_m,
        lw=1.8, edgecolor="#ffffff", facecolor="#475569", hatch="//",
        label="Col 2 — العمود الداخلي C2",
    ))

    # 6. Property Lines
    x_max = max(X2 + L2x / 2.0 + 1.2, L1x + 2.0)
    y_max = max(Y2 + L2y / 2.0 + 1.2, L1y + 2.0)

    # Vertical Property Line 1 (X = 0)
    ax.plot([0, 0], [-0.5, y_max], color="#ef4444", lw=2.5, ls="--")
    ax.text(-0.08, y_max * 0.95, "حد الجار 1 (X = 0)\nProperty Line 1",
            color="#ef4444", fontsize=8.5, ha="right", va="top", fontweight="bold")

    # Horizontal Property Line 2 (Y = 0)
    ax.plot([-0.5, x_max], [0, 0], color="#ef4444", lw=2.5, ls="--")
    ax.text(x_max * 0.95, -0.08, "حد الجار 2 (Y = 0) — Property Line 2",
            color="#ef4444", fontsize=8.5, ha="right", va="top", fontweight="bold")

    # Corner (0,0) marker
    ax.plot([0], [0], marker="o", markersize=6, color="#ef4444")
    ax.text(-0.10, -0.10, "Corner (0,0)", color="#ef4444", fontsize=8, ha="right", va="top", fontweight="bold")

    # 7. Strap Beam Centerline & Column Centers
    ax.plot([X1, X2], [Y1, Y2], color="#facc15", lw=1.2, ls="-.", alpha=0.85)
    ax.plot([X1], [Y1], marker="x", markersize=8, color="#facc15", markeredgewidth=2)
    ax.plot([X2], [Y2], marker="x", markersize=8, color="#facc15", markeredgewidth=2)
    ax.text(X1, Y1, "C1", color="#ffffff", ha="center", va="center", fontsize=8, fontweight="bold")
    ax.text(X1, Y1 + b1_m / 2.0 + 0.12, f"C1 ({X1:.2f}, {Y1:.2f})", color="#facc15",
            fontsize=8, ha="center", fontweight="bold")
    ax.text(X2, Y2, "C2", color="#ffffff", ha="center", va="center", fontsize=8.5, fontweight="bold")
    ax.text(X2, Y2 + b2_m / 2.0 + 0.15, f"C2 ({X2:.2f}, {Y2:.2f})", color="#facc15",
            fontsize=8.5, ha="center", fontweight="bold")

    # Footing 1 Centroid & Eccentricity Vector
    X_f1, Y_f1 = L1x / 2.0, L1y / 2.0
    ax.plot([X_f1], [Y_f1], marker="o", markersize=5, color="#f43f5e")
    ax.annotate(
        "", xy=(X_f1, Y_f1), xytext=(X1, Y1),
        arrowprops=dict(arrowstyle="->", color="#f43f5e", lw=1.4, ls=":")
    )
    ax.text(X_f1 + 0.05, Y_f1 - 0.15, f"F1 C.G. (e={r['e_res']:.2f}m)", color="#f43f5e",
            fontsize=7.5, fontweight="bold")

    # 8. Angle Arc at C1
    arc_radius = 0.90
    arc = patches.Arc(
        (X1, Y1), 2 * arc_radius, 2 * arc_radius,
        angle=0, theta1=0, theta2=r["theta_deg"],
        color="#fb923c", lw=1.5, ls="-"
    )
    ax.add_patch(arc)
    ang_text_r = arc_radius + 0.25
    mid_ang = math.radians(r["theta_deg"] / 2.0)
    ax.text(
        X1 + ang_text_r * math.cos(mid_ang),
        Y1 + ang_text_r * math.sin(mid_ang),
        f"θ = {r['theta_deg']:.1f}°",
        color="#fb923c", fontsize=8.5, fontweight="bold", ha="center"
    )

    def dim_h(x1, x2, y, label, color="#38bdf8", offset=0.08, fontsize=8, tick=0.05):
        if abs(x2 - x1) < 0.02:
            return
        ax.plot([x1, x1], [y - tick, y + tick], color=color, lw=0.9, alpha=0.85)
        ax.plot([x2, x2], [y - tick, y + tick], color=color, lw=0.9, alpha=0.85)
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.1, shrinkA=0, shrinkB=0))
        ax.text((x1 + x2) / 2, y + offset, label, ha="center", va="center",
                color=color, fontsize=fontsize, fontweight="bold")

    def dim_v(y1, y2, x, label, color="#38bdf8", offset=0.08, fontsize=8, tick=0.05, text_side="right", rotation=0):
        if abs(y2 - y1) < 0.02:
            return
        ax.plot([x - tick, x + tick], [y1, y1], color=color, lw=0.9, alpha=0.85)
        ax.plot([x - tick, x + tick], [y2, y2], color=color, lw=0.9, alpha=0.85)
        ax.annotate("", xy=(x, y2), xytext=(x, y1),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.1, shrinkA=0, shrinkB=0))
        ha = "left" if text_side == "right" else "right"
        ax.text(x + offset, (y1 + y2) / 2, label, ha=ha, va="center",
                rotation=rotation, color=color, fontsize=fontsize, fontweight="bold")

    # Column 1 Dimensions — أبعاد عمود الجار الركن C1 بخطوط أبعاد مباشرة وبدون بانيل
    c1_x1 = c1_x0 + a1_m
    c1_y1 = c1_y0 + b1_m
    ax.plot([c1_x0, c1_x0], [c1_y0, c1_y0 - 0.16], color="#94a3b8", lw=0.7, ls=":")
    ax.plot([c1_x1, c1_x1], [c1_y0, c1_y0 - 0.16], color="#94a3b8", lw=0.7, ls=":")
    dim_h(c1_x0, c1_x1, c1_y0 - 0.12, f"a1 = {d['a1']:.0f} cm", color="#f8fafc", offset=-0.07, fontsize=7.5, tick=0.03)

    ax.plot([c1_x1, c1_x1 + 0.16], [c1_y0, c1_y0], color="#94a3b8", lw=0.7, ls=":")
    ax.plot([c1_x1, c1_x1 + 0.16], [c1_y1, c1_y1], color="#94a3b8", lw=0.7, ls=":")
    dim_v(c1_y0, c1_y1, c1_x1 + 0.12, f"b1 = {d['b1']:.0f} cm", color="#f8fafc", offset=0.06, fontsize=7.5, tick=0.03)

    # Column 2 Dimensions — أبعاد العمود الداخلي C2 بخطوط أبعاد مباشرة وبدون بانيل
    c2_x1 = c2_x0 + a2_m
    c2_y1 = c2_y0 + b2_m
    ax.plot([c2_x0, c2_x0], [c2_y0, c2_y0 - 0.18], color="#94a3b8", lw=0.7, ls=":")
    ax.plot([c2_x1, c2_x1], [c2_y0, c2_y0 - 0.18], color="#94a3b8", lw=0.7, ls=":")
    dim_h(c2_x0, c2_x1, c2_y0 - 0.14, f"a2 = {d['a2']:.0f} cm", color="#f8fafc", offset=-0.07, fontsize=7.5, tick=0.03)

    ax.plot([c2_x1, c2_x1 + 0.18], [c2_y0, c2_y0], color="#94a3b8", lw=0.7, ls=":")
    ax.plot([c2_x1, c2_x1 + 0.18], [c2_y1, c2_y1], color="#94a3b8", lw=0.7, ls=":")
    dim_v(c2_y0, c2_y1, c2_x1 + 0.14, f"b2 = {d['b2']:.0f} cm", color="#f8fafc", offset=0.06, fontsize=7.5, tick=0.03)

    # Footing Dimensions — أبعاد القواعد بدون أي بانيل أو صندوق
    dim_h(0.0, L1x, L1y + 0.25, f"L1x = {L1x:.2f} m", color="#38bdf8", offset=0.08)
    dim_v(0.0, L1y, L1x + 0.25, f"L1y = {L1y:.2f} m", color="#38bdf8", offset=0.08)
    dim_h(f2_x, f2_x + L2x, f2_y - 0.40, f"L2x = {L2x:.2f} m", color="#38bdf8", offset=-0.09)
    dim_v(f2_y, f2_y + L2y, f2_x + L2x + 0.35, f"L2y = {L2y:.2f} m", color="#38bdf8", offset=0.08)

    # Span S — المسافة المحورية للشداد المائل بمحاذاة المحور بدون بانيل
    mid_s = (np.array([X1, Y1]) + np.array([X2, Y2])) / 2.0
    ax.text(
        mid_s[0] - (sb_m / 2.0 + 0.18) * sin_th,
        mid_s[1] + (sb_m / 2.0 + 0.18) * cos_th,
        f"Span S = {r['S']:.2f} m", color="#4ade80",
        fontsize=9, fontweight="bold", ha="center", va="center",
        rotation=r["theta_deg"]
    )

    # Offsets ΔX & ΔY — الفروق الإحداثية بدون أي بانيل وبتنظيم هندسي متقن
    dim_h(X1, X2, Y1 - 0.60, f"ΔX = {r['dX']:.2f} m", color="#94a3b8", offset=-0.10, fontsize=7.5)
    ax.plot([X1, X1], [c1_y0 - 0.16, Y1 - 0.65], color="#94a3b8", lw=0.6, ls=":")
    ax.plot([X2, X2], [c2_y0 - 0.18, Y1 - 0.65], color="#94a3b8", lw=0.6, ls=":")

    dy_x = f2_x + L2x + 0.95
    dim_v(Y1, Y2, dy_x, f"ΔY = {r['dY']:.2f} m", color="#94a3b8", offset=0.10, fontsize=7.5)
    ax.plot([f2_x + L2x + 0.40, dy_x + 0.05], [Y1, Y1], color="#94a3b8", lw=0.6, ls=":")
    ax.plot([f2_x + L2x + 0.40, dy_x + 0.05], [Y2, Y2], color="#94a3b8", lw=0.6, ls=":")

    ax.set_xlim(-0.80, dy_x + 0.80)
    ax.set_ylim(-0.85, y_max + 0.30)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, color="#334155", lw=0.5, ls="--", alpha=0.5)

    info_txt = (
        f"Corner Strap: S = {r['S']:.2f} m | θ = {r['theta_deg']:.1f}° | "
        f"Pu1 = {r['P1u']:.1f}t, Pu2 = {r['P2u']:.1f}t | q_act1 = {r['q_act1']:.2f}, q_act2 = {r['q_act2']:.2f} kg/cm²"
    )
    ax.text(
        0.02, 0.97, info_txt, transform=ax.transAxes,
        color="#f1f5f9", fontsize=8.5, fontweight="bold", va="top",
        bbox=dict(boxstyle="round,pad=0.3", fc="#0f172a", ec="#38bdf8", lw=1.0, alpha=0.9)
    )

    ax.set_xlabel("X (m) — المحور الأفقي", color="#94a3b8", fontsize=9)
    ax.set_ylabel("Y (m) — المحور الرأسي", color="#94a3b8", fontsize=9)
    ax.tick_params(colors="#94a3b8", labelsize=8)

    plt.tight_layout()
    return fig


# ── Structural Detailing: Longitudinal Section ──────────────────────────────
def _draw_detailing_elevation(d: dict, r: dict, n_t1: int, n_t2: int):
    fig, ax = plt.subplots(figsize=(14, 6.5))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    S = r["S"]
    t1 = r["t1_cm"] / 100.0
    t2 = r["t2_cm"] / 100.0
    sD = r["sD_cm"] / 100.0
    s_col1 = r["s_col1"]
    L_diag1 = r["L_diag1"]
    a1_m, a2_m = r["a1_m"], r["a2_m"]

    f2_diag_start = S - 0.50 * math.sqrt(r["L2x"]**2 + r["L2y"]**2) / 2.0
    f2_diag_end = S + 0.50 * math.sqrt(r["L2x"]**2 + r["L2y"]**2) / 2.0

    tpc = float(d.get("t_pc", 10.0)) / 100.0
    if tpc > 0:
        ax.add_patch(patches.Rectangle(
            (-0.15, -tpc), L_diag1 + 0.30, tpc,
            lw=1.0, edgecolor="#94a3b8", facecolor="#334155", alpha=0.5, hatch=".."
        ))
        ax.add_patch(patches.Rectangle(
            (f2_diag_start - 0.15, -tpc), (f2_diag_end - f2_diag_start) + 0.30, tpc,
            lw=1.0, edgecolor="#94a3b8", facecolor="#334155", alpha=0.5, hatch=".."
        ))

    ax.add_patch(patches.Rectangle(
        (0.0, 0.0), L_diag1, t1,
        lw=1.8, edgecolor="#38bdf8", facecolor="#1d4ed8", alpha=0.35,
    ))

    ax.add_patch(patches.Rectangle(
        (f2_diag_start, 0.0), f2_diag_end - f2_diag_start, t2,
        lw=1.8, edgecolor="#38bdf8", facecolor="#1d4ed8", alpha=0.35,
    ))

    strap_total_len = S + a2_m / 2.0 + 0.20
    ax.add_patch(patches.Rectangle(
        (0.0, 0.0), strap_total_len, sD,
        lw=2.0, edgecolor="#4ade80", facecolor="#166534", alpha=0.35,
    ))

    col_h = 1.0
    ax.add_patch(patches.Rectangle(
        (s_col1 - a1_m / 2.0, sD), a1_m, col_h,
        lw=1.8, edgecolor="#ffffff", facecolor="#475569", hatch="//",
    ))
    ax.text(s_col1, sD + col_h + 0.08, "C1 (Corner)", color="#facc15",
            fontsize=8.5, ha="center", fontweight="bold")

    ax.add_patch(patches.Rectangle(
        (S - a2_m / 2.0, sD), a2_m, col_h,
        lw=1.8, edgecolor="#ffffff", facecolor="#475569", hatch="//",
    ))
    ax.text(S, sD + col_h + 0.08, "C2 (Interior)", color="#facc15",
            fontsize=8.5, ha="center", fontweight="bold")

    cov = _COVER_CM / 100.0
    y_top = sD - cov
    ax.plot([cov, strap_total_len - cov], [y_top, y_top], color="#ef4444", lw=2.8)
    ax.plot([cov, cov], [y_top, cov + 0.10], color="#ef4444", lw=2.8)
    ax.plot([strap_total_len - cov, strap_total_len - cov], [y_top, cov + 0.10], color="#ef4444", lw=2.8)
    ax.text(
        (s_col1 + S) / 2.0, y_top + 0.06,
        f"حديد علوي رئيسي: {r['n_top']} Φ {int(d['long_bar_dia'])} mm",
        color="#ef4444", fontsize=8.5, ha="center", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.15", fc="#0b1329", ec="#ef4444", lw=0.6)
    )

    y_bot = cov
    ax.plot([cov + 0.05, strap_total_len - cov - 0.05], [y_bot, y_bot], color="#38bdf8", lw=2.4)
    ax.plot([cov + 0.05, cov + 0.05], [y_bot, y_bot + 0.15], color="#38bdf8", lw=2.4)
    ax.plot([strap_total_len - cov - 0.05, strap_total_len - cov - 0.05], [y_bot, y_bot + 0.15], color="#38bdf8", lw=2.4)
    ax.text(
        (s_col1 + S) / 2.0, y_bot - 0.12,
        f"حديد سفلي: {r['n_bot']} Φ {int(d['long_bar_dia'])} mm",
        color="#38bdf8", fontsize=8.5, ha="center", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.15", fc="#0b1329", ec="#38bdf8", lw=0.6)
    )

    st_sp = float(d.get("stirrup_spacing", 20.0)) / 100.0
    st_x = cov + 0.15
    while st_x <= strap_total_len - cov - 0.10:
        ax.plot([st_x, st_x], [y_bot, y_top], color="#facc15", lw=1.0, ls="-", alpha=0.75)
        st_x += st_sp
    ax.text(
        s_col1 + 0.80, sD / 2.0,
        f"كانات: {int(r['stirrup_per_m'])} Φ {int(d['stirrup_dia'])} / m",
        color="#facc15", fontsize=8, ha="left", fontweight="bold", rotation=90,
        bbox=dict(boxstyle="round,pad=0.15", fc="#0b1329", ec="#facc15", lw=0.5)
    )

    if r["sD_cm"] >= 60:
        n_side = max(1, int(r["sD_cm"] / 30.0) - 1)
        for i in range(1, n_side + 1):
            y_side = y_bot + (y_top - y_bot) * (i / (n_side + 1))
            ax.plot([cov + 0.10, strap_total_len - cov - 0.10], [y_side, y_side],
                    color="#a78bfa", lw=1.2, ls="--")
        ax.text(
            strap_total_len - 0.20, (y_top + y_bot) / 2.0,
            f"براندات انكماش: 2×{n_side} Φ 10", color="#a78bfa",
            fontsize=7.5, ha="right", fontweight="bold"
        )

    for cx in [s_col1, S]:
        ax.plot([cx - 0.10, cx - 0.10], [cov, sD + col_h * 0.90], color="#fb923c", lw=1.8)
        ax.plot([cx - 0.10, cx - 0.25], [cov, cov], color="#fb923c", lw=1.8)
        ax.plot([cx + 0.10, cx + 0.10], [cov, sD + col_h * 0.90], color="#fb923c", lw=1.8)
        ax.plot([cx + 0.10, cx + 0.25], [cov, cov], color="#fb923c", lw=1.8)

    def edim_h(x1, x2, y, label, color="#38bdf8", offset=0.08, fontsize=8):
        ax.plot([x1, x1], [y - 0.04, y + 0.04], color=color, lw=0.9)
        ax.plot([x2, x2], [y - 0.04, y + 0.04], color=color, lw=0.9)
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.0, shrinkA=0, shrinkB=0))
        ax.text((x1 + x2) / 2, y + offset, label, ha="center", va="center",
                color=color, fontsize=fontsize, fontweight="bold")

    def edim_v(y1, y2, x, label, color="#38bdf8", offset=0.08, fontsize=8):
        ax.plot([x - 0.04, x + 0.04], [y1, y1], color=color, lw=0.9)
        ax.plot([x - 0.04, x + 0.04], [y2, y2], color=color, lw=0.9)
        ax.annotate("", xy=(x, y2), xytext=(x, y1),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.0, shrinkA=0, shrinkB=0))
        ax.text(x + offset, (y1 + y2) / 2, label, ha="left", va="center",
                color=color, fontsize=fontsize, fontweight="bold")

    edim_v(0.0, sD, -0.25, f"D = {r['sD_cm']:.0f} cm")
    edim_v(0.0, t1, L_diag1 + 0.15, f"t1 = {r['t1_cm']:.0f} cm")
    edim_v(0.0, t2, f2_diag_end + 0.15, f"t2 = {r['t2_cm']:.0f} cm")
    edim_h(s_col1, S, sD + col_h + 0.35, f"المسافة المحورية S = {S:.2f} m", color="#4ade80")

    ax.set_xlim(-0.70, strap_total_len + 0.80)
    ax.set_ylim(-tpc - 0.35, sD + col_h + 0.60)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, color="#334155", lw=0.5, ls="--", alpha=0.4)
    ax.set_xlabel("المسافة على امتداد محور الشداد المائل (m)", color="#94a3b8", fontsize=9)
    ax.set_ylabel("الارتفاع والمناسيب (m)", color="#94a3b8", fontsize=9)
    ax.tick_params(colors="#94a3b8", labelsize=8)

    plt.tight_layout()
    return fig


# ── Structural Detailing: Plan Reinforcement Layout ──────────────────────────
def _draw_detailing_plan(d: dict, r: dict, n_t1: int, n_t2: int):
    fig, ax = plt.subplots(figsize=(13, 7.5))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    L1x, L1y = r["L1x"], r["L1y"]
    L2x, L2y = r["L2x"], r["L2y"]
    X1, Y1 = r["X1"], r["Y1"]
    X2, Y2 = r["X2"], r["Y2"]
    sb_m = r["sb_m"]
    cos_th, sin_th = r["cos_th"], r["sin_th"]
    u_vec = np.array([cos_th, sin_th])
    n_vec = np.array([-sin_th, cos_th])

    # 1. Concrete Outlines
    ax.add_patch(patches.Rectangle((0, 0), L1x, L1y, lw=2.0, edgecolor="#38bdf8", facecolor="#1e293b", alpha=0.9))
    f2_x = X2 - L2x / 2.0
    f2_y = Y2 - L2y / 2.0
    ax.add_patch(patches.Rectangle((f2_x, f2_y), L2x, L2y, lw=2.0, edgecolor="#38bdf8", facecolor="#1e293b", alpha=0.9))

    strap_start = np.array([X1, Y1]) - 0.20 * u_vec
    strap_end = np.array([X2, Y2]) + (r["a2_m"] / 2.0 + 0.15) * u_vec
    p1 = strap_start + (sb_m / 2.0) * n_vec
    p2 = strap_end + (sb_m / 2.0) * n_vec
    p3 = strap_end - (sb_m / 2.0) * n_vec
    p4 = strap_start - (sb_m / 2.0) * n_vec
    ax.add_patch(patches.Polygon([p1, p2, p3, p4], closed=True, lw=1.8, edgecolor="#4ade80", facecolor="#0f172a", alpha=0.85))

    ax.add_patch(patches.Rectangle((X1 - r["a1_m"]/2, Y1 - r["b1_m"]/2), r["a1_m"], r["b1_m"], lw=1.5, edgecolor="#ffffff", facecolor="#475569"))
    ax.add_patch(patches.Rectangle((X2 - r["a2_m"]/2, Y2 - r["b2_m"]/2), r["a2_m"], r["b2_m"], lw=1.5, edgecolor="#ffffff", facecolor="#475569"))

    ax.plot([0, 0], [-0.5, max(Y2 + L2y/2, L1y) + 1.0], color="#ef4444", lw=2.2, ls="--")
    ax.plot([-0.5, max(X2 + L2x/2, L1x) + 1.0], [0, 0], color="#ef4444", lw=2.2, ls="--")

    # 2. Rebar in Footing 1 (Orthogonal mesh)
    nx_bars = max(4, int(L1y / 0.20))
    for i in range(nx_bars):
        yb = 0.10 + i * (L1y - 0.20) / max(1, nx_bars - 1)
        ax.plot([0.08, L1x - 0.08], [yb, yb], color="#38bdf8", lw=1.2, ls="-", alpha=0.7)
    ny_bars = max(4, int(L1x / 0.20))
    for i in range(ny_bars):
        xb = 0.10 + i * (L1x - 0.20) / max(1, ny_bars - 1)
        ax.plot([xb, xb], [0.08, L1y - 0.08], color="#38bdf8", lw=1.2, ls="-", alpha=0.7)

    # 3. Rebar in Footing 2 (Mesh)
    f2_nb_x = max(5, int(L2y / 0.20))
    for i in range(f2_nb_x):
        yb = f2_y + 0.10 + i * (L2y - 0.20) / max(1, f2_nb_x - 1)
        ax.plot([f2_x + 0.08, f2_x + L2x - 0.08], [yb, yb], color="#38bdf8", lw=1.2, ls="-", alpha=0.7)
    f2_nb_y = max(5, int(L2x / 0.20))
    for i in range(f2_nb_y):
        xb = f2_x + 0.10 + i * (L2x - 0.20) / max(1, f2_nb_y - 1)
        ax.plot([xb, xb], [f2_y + 0.08, f2_y + L2y - 0.08], color="#38bdf8", lw=1.2, ls="-", alpha=0.7)

    mid_s = (np.array([X1, Y1]) + np.array([X2, Y2])) / 2.0
    ax.annotate(
        f"تسليح الشداد:\n• علوي: {r['n_top']} Φ {int(d['long_bar_dia'])}\n• سفلي: {r['n_bot']} Φ {int(d['long_bar_dia'])}\n• كانات: {int(r['stirrup_per_m'])} Φ {int(d['stirrup_dia'])}/م",
        xy=(mid_s[0], mid_s[1]),
        xytext=(mid_s[0] - 1.2 * sin_th, mid_s[1] + 1.2 * cos_th),
        arrowprops=dict(arrowstyle="->", color="#4ade80", lw=1.2),
        color="#4ade80", fontsize=8.5, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="#0b1329", ec="#4ade80", lw=0.9)
    )

    ax.annotate(
        f"تسليح قاعدة الجار F1:\n{n_t1} Φ {int(d['trans_bar_dia'])} mm في الاتجاهين\n(شبكة سفلية رئيسية)",
        xy=(L1x * 0.35, L1y * 0.35),
        xytext=(L1x + 0.35, L1y + 0.35),
        arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.2),
        color="#38bdf8", fontsize=8.5, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="#0b1329", ec="#38bdf8", lw=0.9)
    )

    ax.annotate(
        f"تسليح القاعدة الداخلية F2:\n{n_t2} Φ {int(d['trans_bar_dia'])} mm في الاتجاهين\n(شبكة سفلية رئيسية)",
        xy=(X2, Y2 - L2y * 0.35),
        xytext=(X2, Y2 - L2y * 0.50 - 0.65),
        arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.2),
        color="#38bdf8", fontsize=8.5, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.3", fc="#0b1329", ec="#38bdf8", lw=0.9)
    )

    ax.set_xlim(-0.60, max(X2 + L2x/2, L1x) + 1.2)
    ax.set_ylim(-0.60, max(Y2 + L2y/2, L1y) + 1.2)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, color="#334155", lw=0.5, ls="--", alpha=0.4)
    ax.set_xlabel("X (m)", color="#94a3b8", fontsize=9)
    ax.set_ylabel("Y (m)", color="#94a3b8", fontsize=9)
    ax.tick_params(colors="#94a3b8", labelsize=8)

    plt.tight_layout()
    return fig


# ── Structural Detailing: Bending Moment & Shear Diagram ─────────────────────
def _draw_bending_moment_diagram(d: dict, r: dict):
    fig, (ax_sfd, ax_bmd) = plt.subplots(2, 1, figsize=(13, 8.5), sharex=True)
    fig.patch.set_facecolor("#0f172a")
    for ax in [ax_sfd, ax_bmd]:
        ax.set_facecolor("#1e293b")
        ax.grid(True, color="#334155", lw=0.5, ls="--", alpha=0.5)
        ax.tick_params(colors="#94a3b8", labelsize=8.5)

    S = r["S"]
    s_col1 = r["s_col1"]
    L_diag1 = r["L_diag1"]
    P1u = r["P1u"]
    R1u = r["R1u"]
    wu1 = r["wu1"]
    x0 = r["x0"]
    Mu_max = r["Mu_max_strap"]

    s_pts = np.linspace(0.0, S, 400)
    V_vals = []
    M_vals = []

    for s in s_pts:
        if s <= L_diag1:
            V_up = wu1 * s
        else:
            V_up = R1u

        V_down = P1u if s >= s_col1 else 0.0
        V = V_up - V_down
        V_vals.append(V)

        if s <= s_col1:
            M = (wu1 * s ** 2) / 2.0
        elif s <= L_diag1:
            M = (wu1 * s ** 2) / 2.0 - P1u * (s - s_col1)
        else:
            M_at_L1 = (wu1 * L_diag1 ** 2) / 2.0 - P1u * (L_diag1 - s_col1)
            frac = (S - s) / max(1e-4, S - L_diag1)
            M = M_at_L1 * frac
        M_vals.append(M)

    V_vals = np.array(V_vals)
    M_vals = np.array(M_vals)

    ax_sfd.plot(s_pts, V_vals, color="#38bdf8", lw=2.0, label="Shear Force V_u (ton)")
    ax_sfd.fill_between(s_pts, 0, V_vals, where=(V_vals >= 0), color="#38bdf8", alpha=0.25)
    ax_sfd.fill_between(s_pts, 0, V_vals, where=(V_vals < 0), color="#f87171", alpha=0.25)
    ax_sfd.axhline(0, color="#ffffff", lw=1.0, alpha=0.6)
    ax_sfd.axvline(x0, color="#facc15", lw=1.4, ls=":", label=f"Zero Shear (x0={x0:.2f}m)")
    ax_sfd.plot([x0], [0], marker="o", markersize=6, color="#facc15")
    ax_sfd.set_ylabel("قوى القص Vu (ton)", color="#38bdf8", fontsize=10, fontweight="bold")
    ax_sfd.legend(loc="upper right", facecolor="#0f172a", edgecolor="#38bdf8", fontsize=8.5, labelcolor="#f1f5f9")
    ax_sfd.set_title("مخطط قوى القص للشداد المائل — Shear Force Diagram (SFD)", color="#38bdf8", fontsize=11, fontweight="bold")

    ax_bmd.plot(s_pts, M_vals, color="#f43f5e", lw=2.2, label="Bending Moment M_u (ton·m)")
    ax_bmd.fill_between(s_pts, 0, M_vals, color="#f43f5e", alpha=0.25)
    ax_bmd.axhline(0, color="#ffffff", lw=1.0, alpha=0.6)
    ax_bmd.axvline(x0, color="#facc15", lw=1.4, ls=":")

    M_at_x0 = np.interp(x0, s_pts, M_vals)
    ax_bmd.plot([x0], [M_at_x0], marker="s", markersize=7, color="#facc15")
    ax_bmd.annotate(
        f"أقصى عزم سالب Mu,max = {Mu_max:.2f} ton·m\nعند نقطة انعدام القص x0 = {x0:.2f} m",
        xy=(x0, M_at_x0),
        xytext=(x0 + 0.40, M_at_x0 - 15.0 if M_at_x0 < 0 else M_at_x0 + 15.0),
        arrowprops=dict(arrowstyle="->", color="#facc15", lw=1.4),
        color="#facc15", fontsize=9, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="#0b1329", ec="#facc15", lw=0.9)
    )

    ax_bmd.set_ylabel("عزم الانحناء Mu (ton·m)", color="#f43f5e", fontsize=10, fontweight="bold")
    ax_bmd.set_xlabel("المسافة على امتداد محور الشداد المائل (m)", color="#94a3b8", fontsize=10)
    ax_bmd.legend(loc="lower right", facecolor="#0f172a", edgecolor="#f43f5e", fontsize=8.5, labelcolor="#f1f5f9")
    ax_bmd.set_title("مخطط عزوم الانحناء للشداد المائل — Bending Moment Diagram (BMD)", color="#f43f5e", fontsize=11, fontweight="bold")

    plt.tight_layout()
    return fig


# ── Main Module 10 UI Renderer Function ──────────────────────────────────────
def render_diagonal_strap_module():
    _init_state_m10()
    d = st.session_state["module_10_data"]

    st.markdown(
        """
        <style>
        /* ── Module 10 Inputs Typography ── */
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stWidgetLabel"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stWidgetLabel"] *,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stWidgetLabel"] label,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stWidgetLabel"] p,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stWidgetLabel"] span,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stNumberInput label,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stNumberInput label *,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stSelectbox label,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stSelectbox label *,
        div[data-testid="stExpander"] label,
        div[data-testid="stExpander"] label *,
        div[data-testid="stExpander"] div[data-testid="stWidgetLabel"] label,
        div[data-testid="stExpander"] div[data-testid="stWidgetLabel"] p,
        div[data-testid="stExpander"] div[data-testid="stWidgetLabel"] span,
        div[data-testid="stWidgetLabel"] label,
        div[data-testid="stWidgetLabel"] label p,
        div[data-testid="stWidgetLabel"] label span {
            font-size: 17px !important;
            font-weight: 700 !important;
            line-height: 1.25 !important;
            margin-bottom: 2px !important;
            padding-bottom: 0px !important;
            color: #facc15 !important;
            letter-spacing: 0.1px !important;
            white-space: nowrap !important;
        }

        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] input,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] input[type="number"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="input"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="input"] input,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stNumberInput input,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="select"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="select"] *,
        div[data-testid="stExpander"] input,
        div[data-testid="stExpander"] div[data-baseweb="input"] input {
            font-size: 17px !important;
            min-height: 35px !important;
            height: 35px !important;
            line-height: 35px !important;
        }

        div[data-testid="stExpander"] div[data-baseweb="input"]:focus-within {
            border-color: #facc15 !important;
            box-shadow: 0 0 0 1px #facc15 !important;
        }

        div[data-testid="stExpander"] div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stExpander"] div[data-testid="stVerticalBlockBorderWrapper"] > div {
            border: 1.5px solid rgba(255, 255, 255, 0.55) !important;
            border-radius: 8px !important;
        }

        .m10-hdr {
            font-size: 19px !important;
            font-weight: 900 !important;
            color: #38bdf8 !important;
            margin-bottom: 8px !important;
            border-bottom: 1.5px solid rgba(56, 189, 248, 0.4) !important;
            padding-bottom: 4px !important;
        }
        .m10-subhdr {
            font-size: 16px !important;
            font-weight: 800 !important;
            color: #a78bfa !important;
            margin-top: 6px !important;
            margin-bottom: 3px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h2 style='color:#38bdf8; margin-bottom:2px;'>📐 Module 10 — Corner Footing with Diagonal Strap Beam (ECP 203)</h2>"
        "<p style='color:#94a3b8; font-size:13px; margin-top:0;'>تصميم قاعدة جار ركن (محصورة بين حدي جار متعامدين) ومتصلة بقاعدة داخلية بشداد على المائل — الكود المصري (الوحدات: ton · kg · cm · m · kg/cm² · ton·m)</p>",
        unsafe_allow_html=True,
    )

    # ── 1. Inputs (Design Inputs) ─────────────────────────────────────────────
    with st.expander("📐 المدخلات التصميمية والإحداثيات — Design Inputs & Coordinates", expanded=True):
        c_geo, c_load, c_mat = st.columns([1.4, 0.8, 0.8])

        with c_geo:
            with st.container(border=True):
                st.markdown("<div class='m10-hdr'>📐 الإحداثيات والأبعاد الهندسية — Geometry</div>", unsafe_allow_html=True)
                st.markdown("<div class='m10-subhdr'>🔹 عمود الركن C1 (Corner Column)</div>", unsafe_allow_html=True)
                ca_ec1, ca_ec2 = st.columns(2)
                with ca_ec1:
                    d["edge_clearance_x"] = st.number_input(
                        "خلوص حد الجار X (m)",
                        value=float(d.get("edge_clearance_x", 0.0)),
                        min_value=0.0, max_value=5.0, step=0.05, key="m10_ecx",
                        help="المسافة من حد الجار الرأسي X=0 إلى وجه العمود (0.00 = ملاصق للجار)",
                    )
                with ca_ec2:
                    d["edge_clearance_y"] = st.number_input(
                        "خلوص حد الجار Y (m)",
                        value=float(d.get("edge_clearance_y", 0.0)),
                        min_value=0.0, max_value=5.0, step=0.05, key="m10_ecy",
                        help="المسافة من حد الجار الأفقي Y=0 إلى وجه العمود (0.00 = ملاصق للجار)",
                    )

                ca1, cb1 = st.columns(2)
                with ca1:
                    d["a1"] = st.number_input("a1 في اتجاه X (cm)", value=float(d["a1"]),
                                              min_value=15.0, max_value=300.0, step=5.0, key="m10_a1")
                with cb1:
                    d["b1"] = st.number_input("b1 في اتجاه Y (cm)", value=float(d["b1"]),
                                              min_value=15.0, max_value=300.0, step=5.0, key="m10_b1")

                c1_xc = d["edge_clearance_x"] + (d["a1"] / 200.0)
                c1_yc = d["edge_clearance_y"] + (d["b1"] / 200.0)
                st.caption(f"📍 إحداثيات مركز عمود الركن: C1 = ({c1_xc:.2f}, {c1_yc:.2f}) m")

                st.markdown("<div class='m10-subhdr'>🔹 العمود الداخلي C2 (Interior Column Coordinates)</div>", unsafe_allow_html=True)
                ca2_c1, ca2_c2 = st.columns(2)
                with ca2_c1:
                    d["X2"] = st.number_input(
                        "إحداثي X لمركز C2 (m)",
                        value=float(d.get("X2", 4.50)),
                        min_value=c1_xc + 0.50, max_value=30.0, step=0.25, key="m10_x2",
                        help="إحداثي مركز العمود الداخلي في اتجاه X بالنسبة لنقطة أصل الركن",
                    )
                with ca2_c2:
                    d["Y2"] = st.number_input(
                        "إحداثي Y لمركز C2 (m)",
                        value=float(d.get("Y2", 3.80)),
                        min_value=c1_yc + 0.50, max_value=30.0, step=0.25, key="m10_y2",
                        help="إحداثي مركز العمود الداخلي في اتجاه Y بالنسبة لنقطة أصل الركن",
                    )

                ca2_d1, ca2_d2 = st.columns(2)
                with ca2_d1:
                    d["a2"] = st.number_input("a2 في اتجاه X (cm)", value=float(d["a2"]),
                                              min_value=15.0, max_value=300.0, step=5.0, key="m10_a2")
                with ca2_d2:
                    d["b2"] = st.number_input("b2 في اتجاه Y (cm)", value=float(d["b2"]),
                                              min_value=15.0, max_value=300.0, step=5.0, key="m10_b2")

                _dx = float(d["X2"]) - c1_xc
                _dy = float(d["Y2"]) - c1_yc
                _diag_s = math.sqrt(_dx**2 + _dy**2)
                _diag_ang = math.degrees(math.atan2(_dy, _dx))
                st.markdown(
                    f"<div style='background: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; border-radius: 6px; padding: 6px 12px; margin-top: 4px; font-size: 14.5px; color: #f1f5f9;'>"
                    f"🔗 <b>البحر المحوري على المائل S:</b> <span style='color: #4ade80; font-family: monospace; font-weight: 800;'>{_diag_s:.2f} m</span> | "
                    f"📐 <b>زاوية الميل θ:</b> <span style='color: #facc15; font-family: monospace; font-weight: 800;'>{_diag_ang:.1f}°</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        with c_load:
            with st.container(border=True):
                st.markdown("<div class='m10-hdr'>⚖️ الأحمال — Loads (ton)</div>", unsafe_allow_html=True)
                st.markdown("<div class='m10-subhdr'>🔹 عمود الركن C1</div>", unsafe_allow_html=True)
                d["P1_u"] = st.number_input(
                    "Pu1 أقصى (ton) — عمود الركن",
                    value=float(d.get("P1_u", 120.0)),
                    min_value=1.0, max_value=4500.0, step=5.0, key="m10_P1u",
                    help="الحمل الأقصى المستخرج من مخرجات Module 1 أو برامج التحليل الإنشائي",
                )

                st.markdown("<div class='m10-subhdr'>🔹 العمود الداخلي C2</div>", unsafe_allow_html=True)
                d["P2_u"] = st.number_input(
                    "Pu2 أقصى (ton) — العمود الداخلي",
                    value=float(d.get("P2_u", 180.0)),
                    min_value=1.0, max_value=4500.0, step=5.0, key="m10_P2u",
                    help="الحمل الأقصى للعمود الداخلي C2",
                )

                st.markdown("<div class='m10-subhdr'>🔹 معامل وزن الأعمدة</div>", unsafe_allow_html=True)
                d["col_weight_factor"] = st.number_input(
                    "Columns Weight Factor",
                    value=float(d.get("col_weight_factor", 1.00)),
                    min_value=1.00, max_value=1.50, step=0.01, format="%.2f", key="m10_col_factor",
                    help="1.00 = متضمن في أحمال Module 1 تلقائياً | 1.05~1.10 = نسبة إضافية لوزن الأعمدة",
                )

                d["P1_w"] = round((float(d["P1_u"]) * float(d["col_weight_factor"])) / 1.5, 2)
                d["P2_w"] = round((float(d["P2_u"]) * float(d["col_weight_factor"])) / 1.5, 2)

        with c_mat:
            with st.container(border=True):
                st.markdown("<div class='m10-hdr'>🧪 التربة والمواد — Soil & Materials</div>", unsafe_allow_html=True)
                d["q_all_net"] = st.number_input(
                    "q_all,net — إجهاد التربة (kg/cm²)",
                    value=float(d["q_all_net"]), min_value=0.5, max_value=10.0, step=0.10, key="m10_q",
                    help="1.50 kg/cm² = 15.0 ton/m²",
                )
                cm_m1, cm_m2 = st.columns(2)
                with cm_m1:
                    d["fcu"] = st.number_input("Fcu (kg/cm²)", value=float(d["fcu"]),
                                                min_value=150.0, max_value=600.0, step=25.0, key="m10_fcu")
                with cm_m2:
                    d["fy"] = st.number_input("Fy (kg/cm²)", value=float(d["fy"]),
                                               min_value=2000.0, max_value=6000.0, step=200.0, key="m10_fy")
                d["t_pc"] = st.number_input(
                    "t_pc — سماكة العادية (cm)",
                    value=float(d["t_pc"]), min_value=0.0, max_value=100.0, step=5.0, key="m10_tpc",
                )
                st.markdown("<div class='m10-subhdr'>🔹 كمرة الشداد المائل</div>", unsafe_allow_html=True)
                d["strap_b"] = st.number_input(
                    "B_strap العرض (cm)",
                    value=float(d["strap_b"]), min_value=20.0, max_value=200.0, step=5.0, key="m10_sb",
                    help="عرض كمرة الشداد — العمق D_strap يحسبه البرنامج تلقائياً بالأسفل",
                )

        st.markdown("<hr style='margin: 8px 0 12px 0; border-color: rgba(56, 189, 248, 0.25);'>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<div class='m10-hdr'>🔩 مواصفات وأقطار حديد التسليح والكانات — Reinforcement & Stirrups Specifications</div>", unsafe_allow_html=True)
            r_c1, r_c2, r_c3, r_c4 = st.columns(4)
            with r_c1:
                _td_opts = [12, 14, 16, 18, 20, 22]
                d["trans_bar_dia"] = st.selectbox(
                    "قطر حديد تسليح القواعد (mm)",
                    options=_td_opts,
                    index=_td_opts.index(d["trans_bar_dia"]) if d["trans_bar_dia"] in _td_opts else 2,
                    key="m10_tdia",
                    help="قطر أسياخ حديد التسليح الرئيسي لشبكة القواعد (mm)",
                )
            with r_c2:
                _ld_opts = [16, 18, 20, 22, 25, 28, 32]
                d["long_bar_dia"] = st.selectbox(
                    "قطر حديد طولي الشداد (mm)",
                    options=_ld_opts,
                    index=_ld_opts.index(d["long_bar_dia"]) if d["long_bar_dia"] in _ld_opts else 3,
                    key="m10_ldia",
                    help="قطر أسياخ الحديد الطولي الرئيسي لكمرة الشداد (علوي وسفلي)",
                )
            with r_c3:
                _st_opts = [8, 10, 12, 14, 16]
                d["stirrup_dia"] = st.selectbox(
                    "قطر الكانات (mm)",
                    options=_st_opts,
                    index=_st_opts.index(d["stirrup_dia"]) if d["stirrup_dia"] in _st_opts else 1,
                    key="m10_sdia",
                    help="قطر أسياخ كانات الشداد المائل لمقاومة قوى القص",
                )
            with r_c4:
                cur_spm = int(d.get("stirrup_per_m", round(100.0 / float(d.get("stirrup_spacing", 20.0)))))
                cur_spm = max(4, min(12, cur_spm))
                d["stirrup_per_m"] = st.number_input(
                    "عدد الكانات في المتر (كانات/م)",
                    value=cur_spm, min_value=4, max_value=12, step=1, key="m10_s_per_m",
                    help="عدد الكانات في المتر الطولي للكمرة (4 إلى 12 كانة/م)",
                )
                d["stirrup_spacing"] = round(100.0 / float(d["stirrup_per_m"]), 2)
                st.markdown(
                    f"<div style='font-size: 13.5px; color: #94a3b8; font-weight: 700; padding-top: 4px;'>التباعد: <span style='color: #38bdf8; font-family: monospace; font-size: 15px;'>@ {d['stirrup_spacing']:.1f} cm</span></div>",
                    unsafe_allow_html=True,
                )

        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.85); border: 1.5px solid rgba(56, 189, 248, 0.45); border-radius: 8px; padding: 12px 18px; margin-top: 10px; font-size: 15px !important; line-height: 1.65 !important; color: #f1f5f9; direction: rtl; text-align: right;">
                <div style="font-size: 16px !important; font-weight: 800; color: #38bdf8; margin-bottom: 4px;">💡 هندسة الشداد المائل وقاعدة الركن (ECP 203):</div>
                • يتم تحديد موضع عمود الركن عبر خلوصات حدي الجار <span dir="ltr" style="color:#facc15; font-weight:bold;">(edge_clearance_x, edge_clearance_y)</span>، ويتم إدخال إحداثيات مركز العمود الداخلي <span dir="ltr" style="color:#facc15; font-weight:bold;">(X2, Y2)</span> مباشرة.<br/>
                • يحسب الكود تلقائياً المسافة المحورية على المائل <span dir="ltr" style="color:#4ade80; font-weight:bold;">S</span> وزاوية ميل الشداد <span dir="ltr" style="color:#4ade80; font-weight:bold;">θ</span>.<br/>
                • تُحسب الأبعاد التلقائية لقاعدة الركن <span dir="ltr" style="color:#38bdf8; font-weight:bold;">(L1x, L1y)</span> بحيث يقع مركز ثقل القاعدة تماماً على امتداد محور الشداد المائل <span dir="ltr" style="color:#facc15; font-weight:bold;">(ey/ex = tan θ)</span> لتصفير عزم الالتواء (Zero Torsion) تماماً.
            </div>
            """,
            unsafe_allow_html=True,
        )

    rec = _calc_recommended_dimensions(d)
    _upstream_sig = (
        f"{d.get('edge_clearance_x')}_{d.get('edge_clearance_y')}_{d.get('a1')}_{d.get('b1')}_"
        f"{d.get('X2')}_{d.get('Y2')}_{d.get('a2')}_{d.get('b2')}_"
        f"{d.get('P1_u')}_{d.get('P2_u')}_{d.get('col_weight_factor')}_{d.get('q_all_net')}_"
        f"{d.get('fcu')}_{d.get('fy')}_{d.get('t_pc')}_{d.get('strap_b')}"
    )

    is_sig_changed = d.get("_last_upstream_sig") != _upstream_sig

    dim_keys = [
        ("m10_L1x", "L1x"), ("m10_L1y", "L1y"), ("m10_t1", "t1"),
        ("m10_L2x", "L2x"), ("m10_L2y", "L2y"), ("m10_t2", "t2"),
        ("m10_sD", "strap_D"),
    ]

    # Handle pending button actions BEFORE any dimension widgets are instantiated
    pending_action = st.session_state.pop("_m10_action", None)
    if pending_action == "reset":
        d["is_manual_override"] = False
        for wk, k in dim_keys:
            st.session_state[wk] = rec[k]
            d[k] = rec[k]
        st.toast("تمت إعادة تعيين كافة الأبعاد للتصميم التلقائي الآمن! 🔄")
    elif pending_action == "align":
        st.session_state["m10_L1x"] = rec["L1x"]
        st.session_state["m10_L1y"] = rec["L1y"]
        d["L1x"] = rec["L1x"]
        d["L1y"] = rec["L1y"]
        st.toast("تمت محاذاة أبعاد قاعدة الركن بنجاح وتصفير عزم الالتواء! 🎯")

    has_session_override = any(
        wk in st.session_state and abs(float(st.session_state[wk]) - rec[k]) > 1e-3
        for wk, k in dim_keys
    )
    is_override = (d.get("is_manual_override", False) or has_session_override) and not is_sig_changed

    if is_sig_changed:
        d["_last_upstream_sig"] = _upstream_sig
        d["is_manual_override"] = False
        d["L1x"] = rec["L1x"]
        d["L1y"] = rec["L1y"]
        d["t1"] = rec["t1"]
        d["L2x"] = rec["L2x"]
        d["L2y"] = rec["L2y"]
        d["t2"] = rec["t2"]
        d["strap_D"] = rec["strap_D"]
        for wk, k in dim_keys:
            st.session_state[wk] = rec[k]
    elif not is_override:
        d["_last_upstream_sig"] = _upstream_sig
        d["L1x"] = rec["L1x"]
        d["L1y"] = rec["L1y"]
        d["t1"] = rec["t1"]
        d["L2x"] = rec["L2x"]
        d["L2y"] = rec["L2y"]
        d["t2"] = rec["t2"]
        d["strap_D"] = rec["strap_D"]
        for wk, k in dim_keys:
            if wk not in st.session_state:
                st.session_state[wk] = rec[k]

    # ── 2. Executive Design Dimensions & Controls ──────────────────────────────
    with st.expander("📐 نواتج التصميم والأبعاد التنفيذية — Design Dimensions & Overrides", expanded=True):
        st.caption("💡 نواتج التصميم الهندسية الآمنة تظهر مباشرة في خانات الإدخال أدناه، وعند قيامك بأي تعديل يدوي يتم فوراً ولحظياً إعادة الحساب وإجراء كافة الفحوصات الإنشائية والإفادة بحالة الأمان.")
        if is_override:
            st.info("✏️ **وضع التعديل اليدوي للأبعاد (Manual Override Mode):** يتم الآن استخدام الأبعاد المخصصة يدوياً، ويقوم الموديول بإعادة الحساب اللحظي وإجراء كافة الاختبارات الإنشائية فوراً للتأكد من أمان التصميم.")
        else:
            st.success("✨ **أبعاد آمنة ومصممة تلقائياً (Auto-Designed & Safe):** قام الكود بحساب وتصميم الأبعاد الآمنة للقواعد والشداد تلقائياً بناءً على المدخلات، وتم وضعها في خانات الإدخال أدناه مع إمكانية تعديلها حسب رغبتك.")

        col_footings, col_strap = st.columns([1.85, 1.15])

        with col_footings:
            with st.container(border=True):
                st.markdown("<div class='m10-hdr'>🟦 أبعاد القواعد الخرسانية — Footings Dimensions (F1 & F2)</div>", unsafe_allow_html=True)
                f1_col, f2_col = st.columns(2)

                with f1_col:
                    st.markdown("<div class='m10-subhdr'>🔹 Footing 1 (قاعدة الجار الركن)</div>", unsafe_allow_html=True)
                    v_l1x = max(0.50, min(20.0, float(d.get("L1x", rec["L1x"]))))
                    if v_l1x < 1.0:
                        v_l1x = rec["L1x"]
                    d["L1x"] = st.number_input(
                        "L1x — البعد في اتجاه X (m)",
                        value=v_l1x, min_value=0.50, max_value=20.0, step=0.05, key="m10_L1x",
                    )
                    v_l1y = max(0.50, min(20.0, float(d.get("L1y", rec["L1y"]))))
                    if v_l1y < 1.0:
                        v_l1y = rec["L1y"]
                    d["L1y"] = st.number_input(
                        "L1y — البعد في اتجاه Y (m)",
                        value=v_l1y, min_value=0.50, max_value=20.0, step=0.05, key="m10_L1y",
                    )
                    v_t1 = max(20.0, min(250.0, float(d.get("t1", rec["t1"]))))
                    if v_t1 < 30.0:
                        v_t1 = rec["t1"]
                    d["t1"] = st.number_input(
                        "t1 — عمق / سماكة قاعدة الركن (cm)",
                        value=v_t1, min_value=20.0, max_value=250.0, step=5.0, key="m10_t1",
                    )

                with f2_col:
                    st.markdown("<div class='m10-subhdr'>🔹 Footing 2 (القاعدة الداخلية)</div>", unsafe_allow_html=True)
                    v_l2x = max(0.50, min(20.0, float(d.get("L2x", rec["L2x"]))))
                    if v_l2x < 1.0:
                        v_l2x = rec["L2x"]
                    d["L2x"] = st.number_input(
                        "L2x — البعد في اتجاه X (m)",
                        value=v_l2x, min_value=0.50, max_value=20.0, step=0.05, key="m10_L2x",
                    )
                    v_l2y = max(0.50, min(20.0, float(d.get("L2y", rec["L2y"]))))
                    if v_l2y < 1.0:
                        v_l2y = rec["L2y"]
                    d["L2y"] = st.number_input(
                        "L2y — البعد في اتجاه Y (m)",
                        value=v_l2y, min_value=0.50, max_value=20.0, step=0.05, key="m10_L2y",
                    )
                    v_t2 = max(20.0, min(250.0, float(d.get("t2", rec["t2"]))))
                    if v_t2 < 30.0:
                        v_t2 = rec["t2"]
                    d["t2"] = st.number_input(
                        "t2 — عمق / سماكة القاعدة (cm)",
                        value=v_t2, min_value=20.0, max_value=250.0, step=5.0, key="m10_t2",
                    )

        with col_strap:
            with st.container(border=True):
                st.markdown("<div class='m10-hdr'>🟩 كمرة الشداد المائل — Diagonal Strap Beam</div>", unsafe_allow_html=True)
                v_sd = max(40.0, min(300.0, float(d.get("strap_D", rec["strap_D"]))))
                if v_sd < 50.0:
                    v_sd = rec["strap_D"]
                d["strap_D"] = st.number_input(
                    "D_strap — عمق الشداد المحسوب (cm)",
                    value=v_sd, min_value=40.0, max_value=300.0, step=5.0, key="m10_sD",
                    help="عمق كمرة الشداد لتأمين جساءة منع الدوران ومقاومة العزم والقص",
                )
                st.markdown(
                    "<div style='font-size: 13.5px; color: #94a3b8; padding-top: 14px; line-height: 1.55;'>"
                    "💡 يُحسب عمق الشداد $D$ تلقائياً لتأمين عدم دوران قاعدة الركن وضمان جساءة كافية لمقاومة عزم اللامركزية وقوى القص."
                    "</div>",
                    unsafe_allow_html=True,
                )

        # Check if user made a manual edit away from auto-design
        is_manual = (
            abs(d["L1x"] - rec["L1x"]) > 1e-3 or
            abs(d["L1y"] - rec["L1y"]) > 1e-3 or
            abs(d["t1"] - rec["t1"]) > 1e-3 or
            abs(d["L2x"] - rec["L2x"]) > 1e-3 or
            abs(d["L2y"] - rec["L2y"]) > 1e-3 or
            abs(d["t2"] - rec["t2"]) > 1e-3 or
            abs(d["strap_D"] - rec["strap_D"]) > 1e-3
        )
        d["is_manual_override"] = is_manual

        # Run real-time structural analysis and verifications for current dimensions
        r = _calculate(d)
        ok1 = r["q_act1"] <= float(d["q_all_net"])
        ok2 = r["q_act2"] <= float(d["q_all_net"])
        shear_ok = r["stirrups_shear_ok"]
        shear_max_ok = r["shear_max_ok"]
        torsion_ok = r["e_trans"] <= 0.10
        overall_safe = ok1 and ok2 and shear_ok and torsion_ok

        # Render Real-time Safety Diagnostic Banner inside Design Dimensions & Overrides
        if overall_safe:
            mode_badge = "تعديل يدوي آمن (Manual Override — Safe)" if is_manual else "تصميم آمن تلقائياً (Auto-Design — Safe)"
            st.markdown(
                f"""
                <div dir="rtl" style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.16) 0%, rgba(21, 128, 61, 0.28) 100%); border: 2px solid #22c55e; border-radius: 10px; padding: 14px 18px; margin: 12px 0 16px 0; box-shadow: 0 4px 14px rgba(34, 197, 94, 0.20);">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                        <div style="font-size: 17.5px; font-weight: 800; color: #4ade80;">
                            ✅ نتائج الفحص الإنشائي اللحظي: التصميم آمن ومحقق لكافة اشتراطات الكود (Design is Safe & Verified)
                        </div>
                        <div style="font-size: 13px; background: #166534; color: #bbf7d0; padding: 3px 10px; border-radius: 6px; font-weight: 700;">
                            {mode_badge}
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; margin-top: 12px; font-size: 13.5px;">
                        <div style="background: rgba(0,0,0,0.32); padding: 9px 12px; border-radius: 6px; border-right: 3.5px solid #22c55e;">
                            <span style="color: #cbd5e1;">إجهاد تربة الركن F1:</span><br/>
                            <span dir="ltr" style="font-family: monospace; color: #86efac; font-weight: 800; font-size: 15px;">q_act1 = {r['q_act1']:.2f} ≤ {float(d['q_all_net']):.2f} kg/cm²</span> ✅
                        </div>
                        <div style="background: rgba(0,0,0,0.32); padding: 9px 12px; border-radius: 6px; border-right: 3.5px solid #22c55e;">
                            <span style="color: #cbd5e1;">إجهاد تربة الداخلية F2:</span><br/>
                            <span dir="ltr" style="font-family: monospace; color: #86efac; font-weight: 800; font-size: 15px;">q_act2 = {r['q_act2']:.2f} ≤ {float(d['q_all_net']):.2f} kg/cm²</span> ✅
                        </div>
                        <div style="background: rgba(0,0,0,0.32); padding: 9px 12px; border-radius: 6px; border-right: 3.5px solid #22c55e;">
                            <span style="color: #cbd5e1;">فحص قص الشداد τ:</span><br/>
                            <span dir="ltr" style="font-family: monospace; color: #86efac; font-weight: 800; font-size: 15px;">τ = {r['tau_kgcm2']:.2f} ≤ {r['vc_kgcm2']:.2f} kg/cm²</span> ✅
                        </div>
                        <div style="background: rgba(0,0,0,0.32); padding: 9px 12px; border-radius: 6px; border-right: 3.5px solid #22c55e;">
                            <span style="color: #cbd5e1;">محاذاة الشداد وتصفير الالتواء:</span><br/>
                            <span dir="ltr" style="font-family: monospace; color: #86efac; font-weight: 800; font-size: 15px;">e_trans = {r['e_trans']:.2f} m | Mtu = {r['torsion_Mtu']:.2f} t·m</span> ✅
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            override_issues = []
            if not ok1:
                override_issues.append(
                    f"• <b>إجهاد التربة أسفل قاعدة الركن F1 تجاوز الإجهاد الصافي المسموح به:</b> "
                    f"<span dir='ltr' style='font-family: monospace; color: #fca5a5; font-weight: bold;'>q_act1 = {r['q_act1']:.2f} kg/cm² > {float(d['q_all_net']):.2f} kg/cm²</span> "
                    f"— <span style='color: #fef08a;'>الإجراء: يلزم زيادة بعدي قاعدة الركن L1x أو L1y لتكبير مساحة الارتكاز.</span>"
                )
            if not ok2:
                override_issues.append(
                    f"• <b>إجهاد التربة أسفل القاعدة الداخلية F2 تجاوز الإجهاد الصافي المسموح به:</b> "
                    f"<span dir='ltr' style='font-family: monospace; color: #fca5a5; font-weight: bold;'>q_act2 = {r['q_act2']:.2f} kg/cm² > {float(d['q_all_net']):.2f} kg/cm²</span> "
                    f"— <span style='color: #fef08a;'>الإجراء: يلزم زيادة بعدي القاعدة الداخلية L2x أو L2y.</span>"
                )
            if not shear_max_ok:
                override_issues.append(
                    f"• <b>تحذير إنشائي حرج: إجهاد القص في الشداد تجاوز أقصى إجهاد مسموح للخرسانة (q_cu,max):</b> "
                    f"<span dir='ltr' style='font-family: monospace; color: #fca5a5; font-weight: bold;'>τ = {r['tau_kgcm2']:.2f} kg/cm² > {r.get('vc_max_kgcm2', 0.0):.2f} kg/cm²</span> "
                    f"— <span style='color: #fef08a;'>الإجراء: يلزم تكبير أبعاد قطاع الشداد بزيادة العمق D_strap أو العرض b.</span>"
                )
            elif not shear_ok:
                override_issues.append(
                    f"• <b>كانات الشداد المائل غير كافية لمقاومة إجهاد القص:</b> "
                    f"<span dir='ltr' style='font-family: monospace; color: #fca5a5; font-weight: bold;'>المنفذ = {r['Asv_prov_cm2_m']:.2f} cm²/m < المطلوب = {r['Asv_req_cm2_m']:.2f} cm²/m</span> "
                    f"— <span style='color: #fef08a;'>الإجراء: يلزم زيادة قطر أو عدد الكانات في المتر في قسم المدخلات بالأعلى، أو زيادة عمق الشداد.</span>"
                )
            if not torsion_ok:
                override_issues.append(
                    f"• <b>يوجد عزم التواء (Torsion) إضافي على الشداد المائل نتيجة عدم محاذاة مركز قاعدة الركن:</b> "
                    f"<span dir='ltr' style='font-family: monospace; color: #fca5a5; font-weight: bold;'>e_trans = {r['e_trans']:.2f} m | Mtu = {r['torsion_Mtu']:.2f} t·m</span> "
                    f"— <span style='color: #fef08a;'>الإجراء: اضغط على زر «محاذاة أبعاد قاعدة الركن لتصفير الالتواء» بالأدنى لتصفير عزم الالتواء تلقائياً.</span>"
                )

            issues_html = "<br/>".join(override_issues)
            st.markdown(
                f"""
                <div dir="rtl" style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.22) 0%, rgba(185, 28, 28, 0.40) 100%); border: 2px solid #ef4444; border-radius: 10px; padding: 14px 18px; margin: 12px 0 16px 0; box-shadow: 0 4px 16px rgba(239, 68, 68, 0.25);">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                        <div style="font-size: 17.5px; font-weight: 900; color: #fee2e2;">
                            🚨 نتائج الفحص الإنشائي اللحظي: الأبعاد المدخلة غير آمنة هندسياً (Design is Unsafe — Review Required)
                        </div>
                        <div style="font-size: 13px; background: #991b1b; color: #fecaca; padding: 3px 10px; border-radius: 6px; font-weight: 700;">
                            تعديل يدوي يتطلب المراجعة ({len(override_issues)} ملاحظات)
                        </div>
                    </div>
                    <div style="margin-top: 10px; font-size: 14px; color: #ffffff; line-height: 1.7; background: rgba(0,0,0,0.32); padding: 10px 14px; border-radius: 6px; border-right: 4px solid #ef4444;">
                        {issues_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        b_c1, b_c2 = st.columns(2)
        with b_c1:
            if st.button("🔄 إعادة تعيين الأبعاد للقيم المحسوبة تلقائياً (Reset to Auto-Design)", key="m10_btn_reset"):
                st.session_state["_m10_action"] = "reset"
                st.rerun()

        with b_c2:
            if st.button("🎯 محاذاة أبعاد قاعدة الركن لتصفير الالتواء (Align Eccentricity with Strap)", key="m10_btn_align"):
                st.session_state["_m10_action"] = "align"
                st.rerun()

    # ── 3. Dynamic Interactive Plan View ──────────────────────────────────────
    st.divider()
    with st.expander("🗺️ المسقط الأفقي الديناميكي اللحظي — Dynamic Plan View", expanded=False, key="m10_plan_exp", on_change="rerun"):
        if st.session_state.get("m10_plan_exp", False):
            st.caption("يتحدث المسقط الأفقي لحظياً وفورياً مع أي تعديل في الإحداثيات أو الأبعاد أو الأحمال لمتابعة التموضع الهندسي الدقيق.")
            fig = _draw_plan(d, r)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.info("💡 انقر لتوسيع هذا القسم وتوليد المسقط الأفقي الديناميكي لقاعدة الركن والشداد المائل (Lazy Loading).")

    # ── 4. Soil Stress Verification Result ───────────────────────────────────
    if ok1 and ok2:
        st.success(
            f"✅ **نتائج فحص إجهادات التربة (Soil Bearing Capacity — Safe):** "
            f"إجهاد التلامس الفعلي لقاعدة الجار الركن F1 = {r['q_act1']:.2f} kg/cm²، "
            f"وللقاعدة الداخلية F2 = {r['q_act2']:.2f} kg/cm²، "
            f"وكلاهما آمن وأقل من إجهاد التأسيس الصافي المسموح به ({float(d['q_all_net']):.2f} kg/cm²)."
        )
    else:
        st.warning(
            f"⚠️ **نتائج فحص إجهادات التربة (Soil Bearing Capacity — Exceeded):** "
            f"تم تجاوز إجهاد التربة المسموح به ({float(d['q_all_net']):.2f} kg/cm²)! "
            f"قاعدة الركن F1: {r['q_act1']:.2f} kg/cm² | القاعدة الداخلية F2: {r['q_act2']:.2f} kg/cm²."
        )

    # ── 5. Metric Cards ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📋 ملخص التصميم والأبعاد والتسليح وفحص الإجهادات — Design & Verification Summary")

    concrete_shear_ok = r["concrete_shear_ok"]
    stirrups_shear_ok = r["stirrups_shear_ok"]
    shear_max_ok = r["shear_max_ok"]

    if concrete_shear_ok:
        shear_status_text = "Safe (خرسانة بمفردها) ✅"
    elif stirrups_shear_ok:
        shear_status_text = f"Safe بالكانات ✅ ({r['Asv_prov_cm2_m']:.1f} ≥ {r['Asv_req_cm2_m']:.1f} cm²/m)"
    elif not shear_max_ok:
        shear_status_text = "حرج: τ > q_cu,max (كبر القطاع) 🚨"
    else:
        shear_status_text = f"⚠️ كانات غير كافية ({r['Asv_prov_cm2_m']:.1f} < {r['Asv_req_cm2_m']:.1f})"

    n_t1_x = _bar_combo_cm2(r["As_trans1_per_m"] * r["L1y"], int(d["trans_bar_dia"]))
    n_t2_x = _bar_combo_cm2(r["As_trans2_per_m"] * r["L2y"], int(d["trans_bar_dia"]))

    def _metric_box(title, value, subtext, sub_color="#1d4ed8"):
        return f"""
        <div dir="ltr" style="background: #f0f4ff; border: 1px solid #c8d4f0; border-radius: 8px; padding: 10px 14px; box-sizing: border-box; text-align: left; min-height: 112px; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 8px;">
            <div style="color: #475569; font-weight: 600; font-size: 14px; line-height: 1.25; margin-bottom: 4px;">{title}</div>
            <div style="color: #1e3a8a; font-weight: 800; font-size: 22px; font-family: monospace, sans-serif; line-height: 1.2;">{value}</div>
            <div style="color: {sub_color}; font-weight: 800; font-size: 15px; line-height: 1.35; margin-top: 6px;">{subtext}</div>
        </div>
        """

    sb_top, sb_bot, sb_stirrup, sb_shear = st.columns(4)
    with sb_top:
        st.markdown(
            _metric_box(
                "حديد الشداد العلوي (Top Steel)",
                f"{r['n_top']} Φ {int(d['long_bar_dia'])} mm",
                "رئيسي لمقاومة عزم اللامركزية",
                "#1d4ed8",
            ),
            unsafe_allow_html=True,
        )
    with sb_bot:
        st.markdown(
            _metric_box(
                "حديد الشداد السفلي (Bottom Steel)",
                f"{r['n_bot']} Φ {int(d['long_bar_dia'])} mm",
                "تعليق وتماسك القفص",
                "#1d4ed8",
            ),
            unsafe_allow_html=True,
        )
    with sb_stirrup:
        st.markdown(
            _metric_box(
                "كانات الشداد المائل (Stirrups)",
                f"{int(r['stirrup_per_m'])} Φ {int(d['stirrup_dia'])} mm / m",
                f"المنفذ: {r['Asv_prov_cm2_m']:.2f} cm²/m ({r['n_branches']} فروع)",
                "#1d4ed8",
            ),
            unsafe_allow_html=True,
        )
    with sb_shear:
        shear_card_color = "#15803d" if stirrups_shear_ok else "#b91c1c"
        st.markdown(
            _metric_box(
                f"{'✅' if stirrups_shear_ok else '⚠️'} فحص القص τ / q_cu",
                f"{r['tau_kgcm2']:.2f} / {r['vc_kgcm2']:.2f} kg/cm²",
                shear_status_text,
                shear_card_color,
            ),
            unsafe_allow_html=True,
        )

    tf1, tf2 = st.columns(2)
    with tf1:
        st.markdown(
            _metric_box(
                "تسليح قاعدة الجار الركن (Footing 1 Rebar)",
                f"{n_t1_x} Φ {int(d['trans_bar_dia'])} mm",
                f"شبكة سفلية في الاتجاهين ({r['As_trans1_per_m']:.1f} cm²/m)",
                "#1d4ed8",
            ),
            unsafe_allow_html=True,
        )
    with tf2:
        st.markdown(
            _metric_box(
                "تسليح القاعدة الداخلية (Footing 2 Rebar)",
                f"{n_t2_x} Φ {int(d['trans_bar_dia'])} mm",
                f"شبكة سفلية في الاتجاهين ({r['As_trans2_per_m']:.1f} cm²/m)",
                "#1d4ed8",
            ),
            unsafe_allow_html=True,
        )

    # ── Failed Checks & Siren ────────────────────────────────────────────────
    failed_checks = []
    if not ok1:
        failed_checks.append({
            "title": "إجهاد التربة أسفل قاعدة الجار الركن (Footing 1) يتجاوز الإجهاد الصافي المسموح به!",
            "actual": f"q_act1 = {r['q_act1']:.2f} kg/cm²",
            "allowed": f"q_all,net = {float(d['q_all_net']):.2f} kg/cm²",
            "action": "يلزم زيادة بعدي قاعدة الركن L1x أو L1y لتكبير مساحة الارتكاز وخفض إجهاد التربة للحد الآمن.",
        })
    if not ok2:
        failed_checks.append({
            "title": "إجهاد التربة أسفل القاعدة الداخلية (Footing 2) يتجاوز الإجهاد الصافي المسموح به!",
            "actual": f"q_act2 = {r['q_act2']:.2f} kg/cm²",
            "allowed": f"q_all,net = {float(d['q_all_net']):.2f} kg/cm²",
            "action": "يلزم زيادة بعدي القاعدة الداخلية L2x أو L2y لخفض إجهاد التربة للحد الآمن.",
        })
    if not shear_max_ok:
        failed_checks.append({
            "title": "تحذير إنشائي حرج: إجهاد القص يتجاوز أقصى إجهاد مسموح به لقطاع الخرسانة (q_cu,max) بالكود المصري!",
            "actual": f"إجهاد القص الفعلي τ = {r['tau_kgcm2']:.2f} kg/cm²",
            "allowed": f"أقصى إجهاد قص مسموح q_cu,max = {r.get('vc_max_kgcm2', 0.0):.2f} kg/cm²",
            "action": "يجب تكبير أبعاد قطاع الشداد بزيادة العمق D_strap أو العرض B_strap لمنع انهيار الخرسانة بالضغط المائل.",
        })
    elif not stirrups_shear_ok:
        failed_checks.append({
            "title": "تحذير إنشائي: الكانات المنفذة غير كافية لمقاومة إجهاد القص الزائد!",
            "actual": f"المنفذ = {r['Asv_prov_cm2_m']:.2f} cm²/m",
            "allowed": f"المطلوب = {r['Asv_req_cm2_m']:.2f} cm²/m",
            "action": f"يلزم زيادة قطر الكانات أو عددها في المتر لتأمين {r['Asv_req_cm2_m']:.2f} cm²/m أو زيادة عمق الشداد.",
        })
    if r["e_trans"] > 0.15:
        failed_checks.append({
            "title": "تنبيه هندسي: يوجد عزم التواء (Torsion) إضافي على الشداد المائل نتيجة عدم محاذاة مركز قاعدة الركن!",
            "actual": f"اللامركزية العمودية e_trans = {r['e_trans']:.2f} m | Mtu = {r['torsion_Mtu']:.2f} t·m",
            "allowed": "الأفضل هندسياً: e_trans ≈ 0.00 m",
            "action": "اضغط على زر «محاذاة أبعاد قاعدة الركن لتصفير الالتواء» بالأعلى لمحاذاة مركز القاعدة تلقائياً مع محور الشداد.",
        })

    if failed_checks:
        audio_buzzer_html = """
        <script>
        (function() {
            try {
                var AudioCtx = window.AudioContext || window.webkitAudioContext || (window.parent && (window.parent.AudioContext || window.parent.webkitAudioContext));
                if (!AudioCtx) return;
                var ctx = new AudioCtx();
                if (ctx.state === 'suspended') { ctx.resume(); }
                function beep(freq, start, duration, type) {
                    var osc = ctx.createOscillator();
                    var gain = ctx.createGain();
                    osc.type = type || 'sawtooth';
                    osc.frequency.setValueAtTime(freq, ctx.currentTime + start);
                    gain.gain.setValueAtTime(0.25, ctx.currentTime + start);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start(ctx.currentTime + start);
                    osc.stop(ctx.currentTime + start + duration);
                }
                beep(880, 0.05, 0.22, 'sawtooth');
                beep(1175, 0.35, 0.35, 'square');
            } catch(e) {}
        })();
        </script>
        """
        st.components.v1.html(audio_buzzer_html, height=0)

        alert_items_html = "".join([
            f"""
            <div style="margin-top: 8px; padding: 10px 14px; background: rgba(0,0,0,0.30); border-radius: 8px; border-right: 4px solid #f87171;">
                <div style="font-weight: 800; font-size: 16px; color: #fecaca;">⚠️ {fc['title']}</div>
                <div style="font-size: 14.5px; color: #ffffff; margin-top: 4px; line-height: 1.55;">
                    • <b>القيم المحسوبة:</b> <span dir="ltr" style="font-family: monospace; color: #fca5a5; font-weight: 700;">{fc['actual']}</span> | <b>الحد المسموح:</b> <span dir="ltr" style="font-family: monospace; color: #fef08a; font-weight: 700;">{fc['allowed']}</span><br/>
                    • <b>الإجراء الهندسي الواجب:</b> {fc['action']}
                </div>
            </div>
            """
            for fc in failed_checks
        ])

        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.25) 0%, rgba(185, 28, 28, 0.42) 100%); border: 2px solid #ef4444; border-radius: 12px; padding: 16px 20px; margin-top: 12px; margin-bottom: 12px; text-align: right; box-shadow: 0 4px 18px rgba(239, 68, 68, 0.30);">
                <div style="font-size: 19px; font-weight: 900; color: #fee2e2;">
                    🚨 تحذير إنشائي عاجل: تم رصد ({len(failed_checks)}) ملاحظة غير آمنة في هذا التصميم!
                </div>
                {alert_items_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── 6. Design Summary Table ───────────────────────────────────────────────
    st.markdown("##### 📊 جدول الأبعاد والتسليح والتحقق الإنشائي (Design & Verification Table):")

    status_badge_f1 = (
        '<span style="background: rgba(34, 197, 94, 0.20); color: #4ade80; border: 1.5px solid #22c55e; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px;">آمن ✅</span>'
        if ok1 else
        '<span style="background: rgba(245, 158, 11, 0.20); color: #fbbf24; border: 1.5px solid #f59e0b; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px;">تجاوز الإجهاد ⚠️</span>'
    )
    status_badge_f2 = (
        '<span style="background: rgba(34, 197, 94, 0.20); color: #4ade80; border: 1.5px solid #22c55e; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px;">آمن ✅</span>'
        if ok2 else
        '<span style="background: rgba(245, 158, 11, 0.20); color: #fbbf24; border: 1.5px solid #f59e0b; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px;">تجاوز الإجهاد ⚠️</span>'
    )
    if shear_ok:
        status_badge_strap = '<span style="background: rgba(34, 197, 94, 0.20); color: #4ade80; border: 1.5px solid #22c55e; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px;">آمن ✅</span>'
    elif not shear_max_ok:
        status_badge_strap = '<span style="background: rgba(239, 68, 68, 0.20); color: #f87171; border: 1.5px solid #ef4444; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px;">حرج τ > q_cu,max 🚨</span>'
    else:
        status_badge_strap = '<span style="background: rgba(245, 158, 11, 0.20); color: #fbbf24; border: 1.5px solid #f59e0b; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px;">كانات غير كافية ⚠️</span>'

    table_html = f"""
    <div style="overflow-x: auto; border: 2px solid #38bdf8; border-radius: 12px; box-shadow: 0 6px 25px rgba(0, 0, 0, 0.45); margin: 12px 0 20px 0;">
        <table style="width: 100% !important; border-collapse: collapse !important; background: #0b1329 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;">
            <thead>
                <tr style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important; border-bottom: 2.5px solid #38bdf8 !important;">
                    <th style="padding: 13px 16px; text-align: right;"><span style="color: #67e8f9; font-size: 17.5px; font-weight: 900;">العنصر الإنشائي</span></th>
                    <th style="padding: 13px 14px; text-align: center;"><span style="color: #67e8f9; font-size: 17.5px; font-weight: 900;">البعد X (m)</span></th>
                    <th style="padding: 13px 14px; text-align: center;"><span style="color: #67e8f9; font-size: 17.5px; font-weight: 900;">البعد Y (m)</span></th>
                    <th style="padding: 13px 14px; text-align: center;"><span style="color: #67e8f9; font-size: 17.5px; font-weight: 900;">السماكة / العمق (cm)</span></th>
                    <th style="padding: 13px 16px; text-align: right;"><span style="color: #67e8f9; font-size: 17.5px; font-weight: 900;">التسليح المعتمد</span></th>
                    <th style="padding: 13px 14px; text-align: center;"><span style="color: #67e8f9; font-size: 17.5px; font-weight: 900;">إجهاد التشغيل / القص</span></th>
                    <th style="padding: 13px 14px; text-align: center;"><span style="color: #67e8f9; font-size: 17.5px; font-weight: 900;">المسموح به</span></th>
                    <th style="padding: 13px 14px; text-align: center;"><span style="color: #67e8f9; font-size: 17.5px; font-weight: 900;">الحالة</span></th>
                </tr>
            </thead>
            <tbody>
                <!-- Row 1: Footing 1 -->
                <tr style="background: rgba(15, 23, 42, 0.85); border-bottom: 1.5px solid rgba(148, 163, 184, 0.25);">
                    <td style="padding: 12px 16px; text-align: right;"><span style="color: #fb923c; font-size: 18px; font-weight: 900;">قاعدة الجار الركن (F1)</span></td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: center;" dir="ltr">{r['L1x']:.2f} m</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: center;" dir="ltr">{r['L1y']:.2f} m</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: center;" dir="ltr">{r['t1_cm']:.0f} cm</td>
                    <td style="padding: 12px 16px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: right;">{n_t1_x} Φ {int(d['trans_bar_dia'])} mm في الاتجاهين</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #93c5fd; text-align: center;" dir="ltr">q_act = {r['q_act1']:.2f} kg/cm²</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #cbd5e1; text-align: center;" dir="ltr">q_all = {float(d['q_all_net']):.2f} kg/cm²</td>
                    <td style="padding: 12px 14px; text-align: center;">{status_badge_f1}</td>
                </tr>
                <!-- Row 2: Footing 2 -->
                <tr style="background: rgba(30, 41, 59, 0.85); border-bottom: 1.5px solid rgba(148, 163, 184, 0.25);">
                    <td style="padding: 12px 16px; text-align: right;"><span style="color: #fb923c; font-size: 18px; font-weight: 900;">القاعدة الداخلية (F2)</span></td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: center;" dir="ltr">{r['L2x']:.2f} m</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: center;" dir="ltr">{r['L2y']:.2f} m</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: center;" dir="ltr">{r['t2_cm']:.0f} cm</td>
                    <td style="padding: 12px 16px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: right;">{n_t2_x} Φ {int(d['trans_bar_dia'])} mm في الاتجاهين</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #93c5fd; text-align: center;" dir="ltr">q_act = {r['q_act2']:.2f} kg/cm²</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #cbd5e1; text-align: center;" dir="ltr">q_all = {float(d['q_all_net']):.2f} kg/cm²</td>
                    <td style="padding: 12px 14px; text-align: center;">{status_badge_f2}</td>
                </tr>
                <!-- Row 3: Diagonal Strap -->
                <tr style="background: rgba(15, 23, 42, 0.85);">
                    <td style="padding: 12px 16px; text-align: right;"><span style="color: #fb923c; font-size: 18px; font-weight: 900;">الشداد المائل (Strap Beam)</span></td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: center;" dir="ltr">S = {r['S']:.2f} m (مائل)</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: center;" dir="ltr">عرض {d['strap_b']:.0f} cm</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: center;" dir="ltr">{r['sD_cm']:.0f} cm</td>
                    <td style="padding: 12px 16px; font-size: 16.5px; font-weight: 700; color: #f1f5f9; text-align: right;">علوي: {r['n_top']}Φ{int(d['long_bar_dia'])} | سفلي: {r['n_bot']}Φ{int(d['long_bar_dia'])} | كانات: {int(r['stirrup_per_m'])}Φ{int(d['stirrup_dia'])}/م</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #93c5fd; text-align: center;" dir="ltr">τ = {r['tau_kgcm2']:.2f} kg/cm²</td>
                    <td style="padding: 12px 14px; font-size: 16.5px; font-weight: 700; color: #cbd5e1; text-align: center;" dir="ltr">q_cu = {r['vc_kgcm2']:.2f} kg/cm²</td>
                    <td style="padding: 12px 14px; text-align: center;">{status_badge_strap}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

    # ── 7. Detailed Tabs ──────────────────────────────────────────────────────
    st.divider()
    st.markdown(
        """### <span style="color: #67e8f9 !important;">🏗️ المخطط الإنشائي وتفاصيل التسليح التنفيذية</span> <span style="color: #94a3b8 !important;">—</span> <span style="color: #fb923c !important;">Structural Detailing & Layout</span>""",
        unsafe_allow_html=True,
    )

    det_tab1, det_tab2, det_tab3, det_tab4 = st.tabs([
        "🔍 القطاع الطولي وتفريد التسليح (Longitudinal Section)",
        "📐 المسقط الأفقي الإنشائي (Plan Detailing)",
        "📈 مخطط العزوم الإنشائية (Bending Moment Diagram)",
        "📊 جدول حصر الكميات والمواد (Quantity Survey)",
    ])

    with det_tab1:
        st.markdown(
            """#### <span style="color: #67e8f9 !important;">🔍 قطاع طولي تنفيذي على امتداد محور الشداد المائل</span>""",
            unsafe_allow_html=True,
        )
        st.caption("يوضح القطاع: سمك القواعد $t_1, t_2$ وعمق الشداد $D_{strap}$ وتفريد الحديد العلوي والسفلي والكانات والبراندات وأشاير الأعمدة.")
        with st.expander("🖼️ استعراض القطاع الطولي وتفريد التسليح (Longitudinal Detailing Section)", expanded=False, key="m10_elev_exp", on_change="rerun"):
            if st.session_state.get("m10_elev_exp", False):
                fig_elev = _draw_detailing_elevation(d, r, n_t1_x, n_t2_x)
                st.pyplot(fig_elev, use_container_width=True)
                plt.close(fig_elev)
            else:
                st.info("💡 انقر لتوسيع هذا القسم وتوليد القطاع الطولي للشداد المائل وقاعدة الركن (Lazy Loading).")

        st.markdown(
            f"""
            <div dir="rtl" style="background: rgba(15, 23, 42, 0.65); border: 1px solid #334155; border-radius: 8px; padding: 16px 22px; margin-top: 8px; font-size: 15px; line-height: 1.8; color: #e2e8f0; text-align: right;">
                <div style="font-weight: 800; font-size: 17px; margin-bottom: 8px;">
                    <span style="color: #67e8f9;">📌 ملاحظات تنفيذية للقطاع الطولي للشداد المائل</span>
                    <span style="color: #fb923c;">(ECP 203):</span>
                </div>
                • <b>الحديد العلوي الرئيسي (Strap Top Rebar):</b> مصمم لمقاومة أقصى عزم سالب ناتج عن اللامركزية، ويمتد بكامل طول الشداد وينتهي بأرجل رأسية قياسية 90° بطول تماسك <code style="font-size: 15px;">55 Φ</code>.<br/>
                • <b>الحديد السفلي (Bottom Rebar):</b> حديد تعليق وضمان تماسك قفص الشداد لمقاومة العزوم الموجبة العرضية.<br/>
                • <b>تكثيف الكانات:</b> يتم تكثيف كانات الشداد بمعدل <b>{int(r['stirrup_per_m'])} كانات/م بقطر <span dir="ltr">Φ {int(d['stirrup_dia'])} mm</span> ({r['n_branches']} فروع)</b> قرب وش الأعمدة والقواعد.<br/>
                • <b>براندات الانكماش:</b> عمق الشداد $D = {r['sD_cm']:.0f}\\text{{ cm}}$ {'يتطلب وضع براندات انكماش جانبية (Side Bars) بقطر 10 مم كل 30 سم.' if r['sD_cm'] >= 60 else 'لا يتطلب براندات انكماش لأن العمق أقل من 60 سم.'}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with det_tab2:
        st.markdown(
            """#### <span style="color: #67e8f9 !important;">📐 المسقط الأفقي الإنشائي وتوزيع التسليح</span>""",
            unsafe_allow_html=True,
        )
        st.caption("يوضح المسقط: حدود قاعدتي الركن والداخلية، والشداد المائل، وشبكات التسليح في الاتجاهين وكانات الشداد.")
        with st.expander("🖼️ استعراض المسقط الأفقي الإنشائي وتوزيع التسليح (Plan Detailing & Steel Layout)", expanded=False, key="m10_det_plan_exp", on_change="rerun"):
            if st.session_state.get("m10_det_plan_exp", False):
                fig_plan = _draw_detailing_plan(d, r, n_t1_x, n_t2_x)
                st.pyplot(fig_plan, use_container_width=True)
                plt.close(fig_plan)
            else:
                st.info("💡 انقر لتوسيع هذا القسم وتوليد المسقط الأفقي الإنشائي وتوزيع التسليح (Lazy Loading).")

        st.markdown(
            f"""
            <div dir="rtl" style="background: rgba(15, 23, 42, 0.65); border: 1px solid #334155; border-radius: 8px; padding: 16px 22px; margin-top: 8px; font-size: 15px; line-height: 1.8; color: #e2e8f0; text-align: right;">
                <div style="font-weight: 800; font-size: 17px; margin-bottom: 8px;">
                    <span style="color: #67e8f9;">📌 القواعد الهندسية لتسليح قاعدة الركن</span>
                    <span style="color: #fb923c;">(ECP 203):</span>
                </div>
                • <b>شبكة تسليح قاعدة الجار الركن:</b> تعمل بلاطة قاعدة الركن ككابولي خرساني يرتكز على كمرة الشداد المائل، ويتم تنفيذ شبكة تسليح سفلية قوية في الاتجاهين X و Y بمعدل <b>{n_t1_x} أسياخ بقطر <span dir="ltr">Φ {int(d['trans_bar_dia'])} mm</span></b> لمقاومة العزوم الناتجة عن ضغط التربة للأعلى.<br/>
                • <b>شبكة التسليح العلوية:</b> إذا زادت سماكة القاعدة عن 60 سم يوصى بوضع شبكة انكماش علوية خفيفة بمعدل 5 أسياخ في المتر بقطر 10 مم أو 12 مم.<br/>
                • <b>حدود الجار:</b> تم التقيد بحدي الجار المتعامدين $X = 0$ و $Y = 0$ دون أي تجاوز خارج حدود الملكية.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with det_tab3:
        st.markdown(
            """#### <span style="color: #67e8f9 !important;">📈 مخطط العزوم وقوى القص الإنشائية</span>""",
            unsafe_allow_html=True,
        )
        st.caption("يوضح المخطط: منحنى عزوم الانحناء التصميمية وقوى القص وموقع أقصى عزم سالب عند نقطة انعدام القص (Zero Shear).")
        with st.expander("🖼️ استعراض مخطط العزوم الإنشائية (Bending Moment Diagram)", expanded=False, key="m10_bmd_exp", on_change="rerun"):
            if st.session_state.get("m10_bmd_exp", False):
                fig_bmd = _draw_bending_moment_diagram(d, r)
                st.pyplot(fig_bmd, use_container_width=True)
                plt.close(fig_bmd)
            else:
                st.info("💡 انقر لتوسيع هذا القسم وتوليد منحنى ومخطط العزوم وقوى القص الإنشائية (BMD).")

        bmd_c1, bmd_c2, bmd_c3, bmd_c4 = st.columns(4)
        with bmd_c1:
            st.metric("أقصى عزم سالب Mu,max", f"{r['Mu_max_strap']:.2f} t·m")
        with bmd_c2:
            st.metric("موقع Zero Shear (x0 من الركن)", f"{r['x0']:.2f} m")
        with bmd_c3:
            st.metric("عزم رفرفة قاعدة الركن Mu,trans1", f"{r['Mu_trans1']:.2f} t·m/m")
        with bmd_c4:
            st.metric("عزم رفرفة القاعدة الداخلية Mu,trans2", f"{r['Mu_trans2']:.2f} t·m/m")

    with det_tab4:
        st.markdown(
            """#### <span style="color: #67e8f9 !important;">📊 جدول حصر الكميات والمواد الإنشائية</span> <span style="color: #fb923c !important;">(BOQ)</span>""",
            unsafe_allow_html=True,
        )
        st.caption("حصر شامل ومفصل لأوزان حديد التسليح لكل قطر، وأحجام الخرسانات، وكميات الأسمنت والرمل والزلط طبقا للكود المصري ECP 203.")

        strap_len_m = r["S"] + r["a2_m"] / 2.0 + 0.20
        top_cut_m = strap_len_m + 2.0 * max(0.25, (r["sD_cm"] / 100.0 - 0.10))
        bot_cut_m = strap_len_m + 2.0 * 0.25
        top_w_kg = r["n_top"] * top_cut_m * (float(d["long_bar_dia"]) ** 2 / 162.0)
        bot_w_kg = r["n_bot"] * bot_cut_m * (float(d["long_bar_dia"]) ** 2 / 162.0)

        st_perim_m = 2.0 * (r["sb_m"] - 0.10) + 2.0 * (r["sD_cm"] / 100.0 - 0.10) + 0.20
        if r["n_branches"] == 4:
            st_perim_m += (r["sb_m"] - 0.10) + 2.0 * (r["sD_cm"] / 100.0 - 0.10)
        st_count = int(round(strap_len_m * float(r.get("stirrup_per_m", 5.0))))
        st_w_kg = st_count * st_perim_m * (float(d["stirrup_dia"]) ** 2 / 162.0)

        n_side_pairs = max(1, int(r["sD_cm"] / 30.0) - 1) if r["sD_cm"] >= 60.0 else 0
        side_bars_num = n_side_pairs * 2
        side_w_kg = side_bars_num * strap_len_m * (10.0 ** 2 / 162.0)

        f1_cut_x = r["L1x"] - 0.10 + 2.0 * max(0.15, (r["t1_cm"] / 100.0 - 0.10))
        f1_cut_y = r["L1y"] - 0.10 + 2.0 * max(0.15, (r["t1_cm"] / 100.0 - 0.10))
        f1_wx = n_t1_x * f1_cut_x * (float(d["trans_bar_dia"]) ** 2 / 162.0)
        f1_wy = n_t1_x * f1_cut_y * (float(d["trans_bar_dia"]) ** 2 / 162.0)

        f2_cut_x = r["L2x"] - 0.10 + 2.0 * max(0.15, (r["t2_cm"] / 100.0 - 0.10))
        f2_cut_y = r["L2y"] - 0.10 + 2.0 * max(0.15, (r["t2_cm"] / 100.0 - 0.10))
        f2_wx = n_t2_x * f2_cut_x * (float(d["trans_bar_dia"]) ** 2 / 162.0)
        f2_wy = n_t2_x * f2_cut_y * (float(d["trans_bar_dia"]) ** 2 / 162.0)

        rebar_items = [
            (int(d["long_bar_dia"]), r["n_top"], top_cut_m, top_w_kg, "الشداد المائل — حديد علوي رئيسي"),
            (int(d["long_bar_dia"]), r["n_bot"], bot_cut_m, bot_w_kg, "الشداد المائل — حديد سفلي"),
            (int(d["stirrup_dia"]), st_count, st_perim_m, st_w_kg, "الشداد المائل — كانات القص"),
        ]
        if side_bars_num > 0:
            rebar_items.append((10, side_bars_num, strap_len_m, side_w_kg, "الشداد المائل — براندات انكماش جانبية"))

        rebar_items.extend([
            (int(d["trans_bar_dia"]), n_t1_x, f1_cut_x, f1_wx, "قاعدة الجار الركن F1 — تسليح في اتجاه X"),
            (int(d["trans_bar_dia"]), n_t1_x, f1_cut_y, f1_wy, "قاعدة الجار الركن F1 — تسليح في اتجاه Y"),
            (int(d["trans_bar_dia"]), n_t2_x, f2_cut_x, f2_wx, "القاعدة الداخلية F2 — تسليح في اتجاه X"),
            (int(d["trans_bar_dia"]), n_t2_x, f2_cut_y, f2_wy, "القاعدة الداخلية F2 — تسليح في اتجاه Y"),
        ])

        dia_summary = {}
        for dia, count, cut_len, weight, desc in rebar_items:
            if dia not in dia_summary:
                dia_summary[dia] = {"dia": dia, "total_len_m": 0.0, "total_weight_kg": 0.0, "elements": []}
            dia_summary[dia]["total_len_m"] += count * cut_len
            dia_summary[dia]["total_weight_kg"] += weight
            dia_summary[dia]["elements"].append(desc)

        total_steel_kg = sum(x["total_weight_kg"] for x in dia_summary.values())
        total_steel_ton = total_steel_kg / 1000.0

        L1x, L1y, t1 = r["L1x"], r["L1y"], r["t1_cm"] / 100.0
        L2x, L2y, t2 = r["L2x"], r["L2y"], r["t2_cm"] / 100.0
        sb = r["sb_m"]
        sD = r["sD_cm"] / 100.0

        v_f1_rc = L1x * L1y * t1
        v_f2_rc = L2x * L2y * t2
        clear_span = max(0.0, r["S"] - r["L_diag1"] / 2.0 - math.sqrt(L2x**2 + L2y**2) / 4.0)
        v_strap_net = clear_span * sb * sD + (r["L_diag1"] * sb * max(0.0, sD - t1))
        v_rc_total = v_f1_rc + v_f2_rc + v_strap_net

        tpc = float(d.get("t_pc", 10.0)) / 100.0
        if tpc > 0:
            v_pc1 = (L1x + tpc) * (L1y + tpc) * tpc
            v_pc2 = (L2x + 2 * tpc) * (L2y + 2 * tpc) * tpc
            v_pc_total = v_pc1 + v_pc2
        else:
            v_pc_total = 0.0
        v_concrete_total = v_rc_total + v_pc_total

        cement_rc_ton = v_rc_total * 0.350
        cement_pc_ton = v_pc_total * 0.250
        cement_total_ton = cement_rc_ton + cement_pc_ton
        cement_bags = cement_total_ton * 1000.0 / 50.0
        gravel_total_m3 = v_concrete_total * 0.80
        sand_total_m3 = v_concrete_total * 0.40

        qs_col1, qs_col2, qs_col3, qs_col4, qs_col5 = st.columns(5)
        with qs_col1:
            st.metric("الوزن الإجمالي للحديد", f"{total_steel_ton:.2f} Ton", f"{total_steel_kg:.0f} kg")
        with qs_col2:
            st.metric("كمية الأسمنت بالطن", f"{cement_total_ton:.2f} Ton", f"{cement_bags:.0f} شكارة")
        with qs_col3:
            st.metric("كمية الزلط (السن)", f"{gravel_total_m3:.2f} m³", "0.80 م³/م³")
        with qs_col4:
            st.metric("كمية الرمل", f"{sand_total_m3:.2f} m³", "0.40 م³/م³")
        with qs_col5:
            st.metric("إجمالي الخرسانة", f"{v_concrete_total:.2f} m³", f"{v_rc_total:.2f} m³ مسلحة")

        st.markdown("##### 🔩 1. حصر كميات حديد التسليح لكل قطر:")
        rebar_dia_rows = []
        for dia in sorted(dia_summary.keys()):
            info = dia_summary[dia]
            pct = (info["total_weight_kg"] / total_steel_kg) * 100.0 if total_steel_kg > 0 else 0.0
            rebar_dia_rows.append({
                "قطر السيخ Φ": f"Φ {dia} mm",
                "الاستخدام والعناصر في المشروع": " + ".join(dict.fromkeys(info["elements"])),
                "إجمالي الطول (m)": f"{info['total_len_m']:.1f} m",
                "الوزن بالكجم (kg)": f"{info['total_weight_kg']:.1f} kg",
                "الوزن بالطن (Ton)": f"{info['total_weight_kg'] / 1000.0:.3f} Ton",
                "النسبة من إجمالي الحديد": f"{pct:.1f} %",
            })
        st.dataframe(pd.DataFrame(rebar_dia_rows).set_index("قطر السيخ Φ"), use_container_width=True)

        st.markdown("##### 🧱 2. جدول حصر الخرسانات ومواد البناء الأساسية:")
        materials_data = {
            "البند / المادة (Item / Material)": [
                "خرسانة مسلحة — قاعدة الجار الركن (Footing 1 RC)",
                "خرسانة مسلحة — القاعدة الداخلية (Footing 2 RC)",
                "خرسانة مسلحة — كمرة الشداد المائل (Strap Beam RC)",
                "إجمالي الخرسانة المسلحة (Total Reinforced Concrete)",
                "خرسانة عادية فرشة نظافة (Plain Concrete PC)",
                "إجمالي الأسمنت المطلوب (Total Cement)",
                "الركام الكبير / الزلط أو السن (Gravel)",
                "الركام الصغير / الرمل النظيف (Sand)",
            ],
            "الوحدة (Unit)": ["m³", "m³", "m³", "m³", "m³", "Ton", "m³", "m³"],
            "الكمية المحسوبة": [
                f"{v_f1_rc:.2f} m³", f"{v_f2_rc:.2f} m³", f"{v_strap_net:.2f} m³",
                f"{v_rc_total:.2f} m³", f"{v_pc_total:.2f} m³" if v_pc_total > 0 else "—",
                f"{cement_total_ton:.2f} Ton ({cement_bags:.0f} شكارة)",
                f"{gravel_total_m3:.2f} m³", f"{sand_total_m3:.2f} m³",
            ],
        }
        st.dataframe(pd.DataFrame(materials_data).set_index("البند / المادة (Item / Material)"), use_container_width=True)

    # Persist state
    d["is_calculated"] = True
    st.session_state["module_10_data"] = d
    if "cfg" in st.session_state and isinstance(st.session_state["cfg"], dict):
        st.session_state["cfg"]["module_10_diagonal_strap"] = {k: v for k, v in d.items()}
    from modules.settings import save_settings
    save_settings()
