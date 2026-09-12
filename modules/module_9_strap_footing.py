"""
Module 9 — Reinforced Concrete Strap Footing Design (ECP 203)
==============================================================
Standard Metric Units per ECP 203:
  • Loads & Reactions : ton · kg  (1 ton = 1,000 kg)
  • Moments           : ton·m     (1 ton·m = 100,000 kg·cm)
  • Stresses          : kg/cm²    (q_all,net, Fcu, Fy, tau)
  • Section Dims      : cm        (Columns, Beams, Footing Thickness, Cover)
  • Spans & Plan Dims : m         (S, edge_clearance, L1, B1, L2, B2)
  • Rebar Dims        : mm · cm   (Φ mm, spacing cm)
Run from app.py via:  render_strap_footing_module()
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
    """
    Required steel area (cm²) using Whitney stress block per ECP 203.
    """
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
_DEFAULTS = {
    "S": 5.0,              # m (المسافة المحورية بين الأعمدة)
    "edge_clearance": 0.0,  # m (المسافة لحد الجار)
    "a1": 30.0,            # cm (عمق عمود الجار)
    "b1": 60.0,            # cm (عرض عمود الجار)
    "a2": 40.0,            # cm (عمق العمود الداخلي)
    "b2": 50.0,            # cm (عرض العمود الداخلي)
    "P1_u": 120.0,         # ton (أقصى حمل لعمود الجار)
    "P2_u": 180.0,         # ton (أقصى حمل للعمود الداخلي)
    "col_weight_factor": 1.00,  # معامل وزن الأعمدة (افتراضي = 1.00)
    "P1_w": 80.0,          # ton (تلقائي = P1_u / 1.5)
    "P2_w": 120.0,         # ton (تلقائي = P2_u / 1.5)
    "q_all_net": 1.50,     # kg/cm² (إجهاد التربة الصافي المسموح به)
    "fcu": 250.0,          # kg/cm² (رتبة الخرسانة)
    "fy": 4000.0,          # kg/cm² (إجهاد خضوع حديد التسليح)
    "t_pc": 10.0,          # cm (سماكة الخرسانة العادية)
    "strap_b": 40.0,       # cm (عرض كمرة الشداد)
    "strap_D": 100.0,      # cm (عمق كمرة الشداد)
    "L1": 2.20,            # m (طول قاعدة الجار)
    "B1": 3.00,            # m (عرض قاعدة الجار)
    "t1": 55.0,            # cm (سماكة قاعدة الجار)
    "L2": 2.85,            # m (طول القاعدة الداخلية)
    "B2": 2.85,            # m (عرض القاعدة الداخلية)
    "t2": 50.0,            # cm (سماكة القاعدة الداخلية)
    "L1_override": 2.20,   # m (legacy)
    "L1_ov": 2.20,
    "B1_ov": 3.00,
    "t1_ov": 55.0,
    "L2_ov": 2.85,
    "B2_ov": 2.85,
    "t2_ov": 50.0,
    "long_bar_dia": 22,    # mm (قطر حديد طولي للشداد)
    "stirrup_dia": 10,     # mm (قطر الكانات)
    "stirrup_per_m": 5,    # كانات/م (عدد الكانات في المتر الطولي)
    "stirrup_spacing": 20, # cm (مسافة الكانات = 100 / عدد الكانات)
    "trans_bar_dia": 16,   # mm (قطر حديد القواعد العرضي)
    "final_B1": None,
    "final_L2": None,
    "final_B2": None,
    "is_calculated": False,
}


def _normalize_m9_dict(d: dict) -> dict:
    """Seamless migration from legacy SI units and support for single Ultimate load + col_weight_factor."""
    out = dict(d)
    # Col weight factor
    if "col_weight_factor" not in out:
        out["col_weight_factor"] = 1.00
    # Loads: kN -> ton
    if out.get("P1_w", 0) >= 300:
        out["P1_w"] = round(float(out["P1_w"]) / 10.0, 1)
        out["P1_u"] = round(float(out.get("P1_u", 1200.0)) / 10.0, 1)
        out["P2_w"] = round(float(out.get("P2_w", 1200.0)) / 10.0, 1)
        out["P2_u"] = round(float(out.get("P2_u", 1800.0)) / 10.0, 1)
    if "P1_u" not in out and "P1_w" in out:
        out["P1_u"] = round(float(out["P1_w"]) * 1.5, 1)
    if "P2_u" not in out and "P2_w" in out:
        out["P2_u"] = round(float(out["P2_w"]) * 1.5, 1)
    # Ensure P1_w & P2_w are consistent with P_u and factor
    cwf = float(out.get("col_weight_factor", 1.00))
    p1u = float(out.get("P1_u", 120.0))
    p2u = float(out.get("P2_u", 180.0))
    out["P1_w"] = round((p1u * cwf) / 1.5, 2)
    out["P2_w"] = round((p2u * cwf) / 1.5, 2)
    # Soil: kN/m² -> kg/cm²
    if out.get("q_all_net", 0) >= 20:
        out["q_all_net"] = round(float(out["q_all_net"]) / 100.0, 2)
    # Materials: MPa -> kg/cm²
    if 0 < out.get("fcu", 0) <= 100:
        out["fcu"] = round(float(out["fcu"]) * 10.0, 0)
    if 0 < out.get("fy", 0) <= 1000:
        out["fy"] = round(float(out["fy"]) * 10.0, 0)
    # Cross-sections: m -> cm
    if 0 < out.get("a1", 0) <= 2.0:
        out["a1"] = round(float(out["a1"]) * 100.0, 0)
    if 0 < out.get("b1", 0) <= 2.0:
        out["b1"] = round(float(out["b1"]) * 100.0, 0)
    if 0 < out.get("a2", 0) <= 2.0:
        out["a2"] = round(float(out["a2"]) * 100.0, 0)
    if 0 < out.get("b2", 0) <= 2.0:
        out["b2"] = round(float(out["b2"]) * 100.0, 0)
    if 0 < out.get("strap_b", 0) <= 2.0:
        out["strap_b"] = round(float(out["strap_b"]) * 100.0, 0)
    if 0 < out.get("strap_D", 0) <= 3.0:
        out["strap_D"] = round(float(out["strap_D"]) * 100.0, 0)
    if 0 < out.get("t_pc", 0) <= 1.0:
        out["t_pc"] = round(float(out["t_pc"]) * 100.0, 0)
    if 0 < out.get("t1_ov", 0) <= 2.0:
        out["t1_ov"] = round(float(out["t1_ov"]) * 100.0, 0)
    if 0 < out.get("t2_ov", 0) <= 2.0:
        out["t2_ov"] = round(float(out["t2_ov"]) * 100.0, 0)
    if out.get("stirrup_spacing", 0) > 50:
        out["stirrup_spacing"] = round(float(out["stirrup_spacing"]) / 10.0, 0)
    if "stirrup_per_m" not in out:
        old_s = float(out.get("stirrup_spacing", 20.0))
        out["stirrup_per_m"] = max(4, min(12, int(round(100.0 / old_s)))) if old_s > 0 else 5
    else:
        out["stirrup_per_m"] = max(4, min(12, int(round(float(out["stirrup_per_m"])))))
    out["stirrup_spacing"] = round(100.0 / float(out["stirrup_per_m"]), 2)
    return out


def _init_state():
    """Initialise and migrate session_state['module_9_data']."""
    if "module_9_data" in st.session_state and st.session_state["module_9_data"]:
        d = _normalize_m9_dict(st.session_state["module_9_data"])
        for k, v in _DEFAULTS.items():
            if k not in d:
                d[k] = v
        st.session_state["module_9_data"] = d
        return

    cfg = st.session_state.get("cfg", {})
    nested = cfg.get("module_9_strap_footing")
    if isinstance(nested, dict) and nested:
        d = dict(_DEFAULTS)
        d.update(_normalize_m9_dict(nested))
        d.setdefault("L1_override", d.get("L1_ov", 2.20))
        d.setdefault("L1_ov", d.get("L1_override", 2.20))
        st.session_state["module_9_data"] = d
    else:
        st.session_state["module_9_data"] = dict(_DEFAULTS)


def _calc_recommended_dimensions(d: dict) -> dict:
    """Compute structural engineering recommended dimensions for Strap Footing & Beam per ECP 203."""
    S = float(d.get("S", 5.0))
    ec = float(d.get("edge_clearance", 0.0))
    a1_m = float(d.get("a1", 30.0)) / 100.0
    b1_m = float(d.get("b1", 60.0)) / 100.0
    a2_m = float(d.get("a2", 40.0)) / 100.0
    b2_m = float(d.get("b2", 50.0)) / 100.0

    cwf = float(d.get("col_weight_factor", 1.00))
    P1u = float(d.get("P1_u", 120.0)) * cwf
    P2u = float(d.get("P2_u", 180.0)) * cwf
    P1w = P1u / 1.5
    P2w = P2u / 1.5

    q_ton_m2 = float(d.get("q_all_net", 1.50)) * 10.0
    fcu = float(d.get("fcu", 250.0))
    sb_cm = float(d.get("strap_b", 40.0))
    sb_m = sb_cm / 100.0

    # 1. Footing 1 (Edge) sizing
    Area1_approx = 1.15 * (P1w / q_ton_m2)
    # Target aspect ratio B1 / L1 ≈ 1.25 -> L1 ≈ sqrt(Area1 / 1.25)
    L1_calc = math.sqrt(max(Area1_approx / 1.25, 0.5))
    L1_min = 2.0 * (ec + a1_m / 2.0) + 0.30
    L1_rec = round(max(L1_calc, L1_min, 1.60) * 20.0) / 20.0

    e = (L1_rec / 2.0 - a1_m / 2.0) - ec
    X = max(S - e, 0.50)
    R1 = P1w * S / X
    Area1_actual = R1 / q_ton_m2
    B1_calc = Area1_actual / L1_rec
    B1_rec = math.ceil(max(B1_calc, b1_m + 0.40, sb_m + 0.40) * 20.0) / 20.0

    # 2. Footing 2 (Interior) sizing
    R2 = (P1w + P2w) - R1
    Area2 = max(R2, P2w) / q_ton_m2
    L2_calc = math.sqrt(max(Area2, 1.0))
    L2_rec = math.ceil(max(L2_calc, a2_m + 0.40, sb_m + 0.40) * 20.0) / 20.0
    B2_rec = math.ceil(max(Area2 / L2_rec, b2_m + 0.40, sb_m + 0.40) * 20.0) / 20.0

    # 3. Footing thicknesses (cm)
    cant1 = (B1_rec - sb_m) / 2.0
    cant2 = (B2_rec - sb_m) / 2.0
    t1_rec = float(math.ceil(max(50.0, cant1 * 100.0 / 2.5) / 5.0) * 5.0)
    t2_rec = float(math.ceil(max(50.0, cant2 * 100.0 / 2.5) / 5.0) * 5.0)

    # 4. Strap Beam Depth D_strap (cm)
    Ru1 = P1u * S / X
    wu1 = Ru1 / L1_rec
    col1_dist = ec + a1_m / 2.0
    x0_rec = min(L1_rec, max(col1_dist, P1u / wu1 if wu1 > 0 else col1_dist))
    Mu_neg = abs(P1u * (x0_rec - col1_dist) - wu1 * (x0_rec ** 2) / 2.0)
    # d from flexure (C1 ≈ 4.5)
    d_flex = 4.5 * math.sqrt(max(0.0, (Mu_neg * 1e5) / (fcu * sb_cm)))
    d_span = (S * 100.0) / 5.0
    d_approx = max(d_flex, d_span - 10.0, 70.0)
    Vu = abs(Ru1 - wu1 * (col1_dist + d_approx / 100.0))
    # ECP 203 max shear stress with stirrups: qu_max = 0.70 * sqrt(fcu/10/1.5)*10 ≈ 28.5 kg/cm2
    d_shear = (Vu * 1000.0) / (sb_cm * 22.0) if sb_cm > 0 else 60.0
    D_req = max(d_flex + 7.5, d_shear + 7.5, d_span, 70.0)
    strap_D_rec = float(math.ceil(D_req / 10.0) * 10.0)

    return {
        "L1": round(max(0.50, min(15.0, L1_rec)), 2),
        "B1": round(max(0.50, min(15.0, B1_rec)), 2),
        "t1": round(max(20.0, min(250.0, t1_rec)), 1),
        "L2": round(max(0.50, min(15.0, L2_rec)), 2),
        "B2": round(max(0.50, min(15.0, B2_rec)), 2),
        "t2": round(max(20.0, min(250.0, t2_rec)), 1),
        "strap_D": round(max(40.0, min(280.0, strap_D_rec)), 1),
    }


# ── Calculation Engine (ton · kg · cm · m · kg/cm² · ton·m) ───────────────────
def _calculate(d_in: dict) -> dict:
    d = _normalize_m9_dict(d_in)

    # Geometry in meters
    S = float(d["S"])
    ec = float(d["edge_clearance"])

    # Columns: cm -> m for layout geometry
    a1_m = float(d["a1"]) / 100.0
    b1_m = float(d["b1"]) / 100.0
    a2_m = float(d["a2"]) / 100.0
    b2_m = float(d["b2"]) / 100.0

    # Loads in ton (Solution B: Ultimate loads scaled by col_weight_factor, and Working = Pu / 1.5)
    cwf = float(d.get("col_weight_factor", 1.00))
    P1u = float(d.get("P1_u", 120.0)) * cwf
    P2u = float(d.get("P2_u", 180.0)) * cwf
    P1w = P1u / 1.5
    P2w = P2u / 1.5

    # Soil capacity: kg/cm² -> ton/m²
    q_kgcm2 = float(d["q_all_net"])
    q_ton_m2 = q_kgcm2 * 10.0  # 1 kg/cm² = 10 ton/m²

    # Material strengths in kg/cm²
    fcu_kgcm2 = float(d["fcu"])
    fy_kgcm2 = float(d["fy"])

    # Strap beam dimensions: cm and m
    sb_cm = float(d["strap_b"])
    sD_cm = float(d.get("strap_D", 100.0))
    sb_m = sb_cm / 100.0
    sD_m = sD_cm / 100.0

    # Footing thicknesses: cm and m
    t1_cm = float(d.get("t1", d.get("t1_ov", 55.0)))
    t2_cm = float(d.get("t2", d.get("t2_ov", 50.0)))
    t1_m = t1_cm / 100.0
    t2_m = t2_cm / 100.0

    # 1. Eccentricity & Lever arm
    L1_val = float(d.get("L1") or d.get("L1_override") or d.get("L1_ov", 2.20))
    if L1_val > 20.0:  # in case entered in cm
        L1_val = L1_val / 100.0
    L1 = L1_val if L1_val and L1_val > 0 else 2.20

    e = (L1 / 2.0 - a1_m / 2.0) - ec
    X = max(S - e, 0.01)

    # 2. Service soil reactions (ton)
    R1 = P1w * S / X
    R2 = (P1w + P2w) - R1

    # 3. Footing plan dimensions (m)
    Area1 = R1 / q_ton_m2
    B1_val = float(d.get("B1") or d.get("B1_ov", 0.0))
    if B1_val > 20.0:
        B1_val = B1_val / 100.0
    B1 = B1_val if B1_val > 0 else max(Area1 / L1, b1_m + 0.40)

    Area2 = max(R2, P2w) / q_ton_m2
    L2_val = float(d.get("L2") or d.get("L2_ov", 0.0))
    if L2_val > 20.0:
        L2_val = L2_val / 100.0
    L2 = L2_val if L2_val > 0 else max(math.sqrt(Area2), a2_m + 0.40)

    B2_val = float(d.get("B2") or d.get("B2_ov", 0.0))
    if B2_val > 20.0:
        B2_val = B2_val / 100.0
    B2 = B2_val if B2_val > 0 else max(Area2 / L2, b2_m + 0.40)

    # Actual contact pressures (kg/cm² and ton/m²)
    q_act1_tm2 = R1 / (L1 * B1)
    q_act1_kgcm2 = q_act1_tm2 / 10.0
    q_act2_tm2 = R2 / (L2 * B2)
    q_act2_kgcm2 = q_act2_tm2 / 10.0

    # Ultimate uniform upward pressure (ton/m²)
    qu1_tm2 = q_act1_tm2 * (P1u / P1w if P1w > 0 else 1.5)
    qu2_tm2 = q_act2_tm2 * (P2u / P2w if P2w > 0 else 1.5)

    # 4. Strap Beam Design (Ultimate)
    Ru1 = P1u * S / X  # ton
    wu1 = Ru1 / L1     # ton/m
    col1_from_f1 = ec + a1_m / 2.0  # m
    x0 = min(L1, max(col1_from_f1, P1u / wu1 if wu1 > 0 else col1_from_f1))
    Mu_neg_tm = -(P1u * (x0 - col1_from_f1) - wu1 * (x0 ** 2) / 2.0)  # ton·m
    Mu_pos_tm = abs(Mu_neg_tm) * 0.15  # ton·m
    Mu_col1_tm = -(wu1 * (col1_from_f1 ** 2) / 2.0)
    Mu_f1_edge_tm = -(P1u * (L1 - col1_from_f1) - wu1 * (L1 ** 2) / 2.0)

    long_dia_mm = float(d["long_bar_dia"])
    stirrup_dia_mm = float(d["stirrup_dia"])
    d_strap_cm = sD_cm - _COVER_CM - (stirrup_dia_mm / 10.0) - (long_dia_mm / 20.0)
    d_strap_m = d_strap_cm / 100.0

    # Required flexural steel (cm²) using Whitney stress block per ECP 203
    # 1 ton·m = 100,000 kg·cm
    As_top_cm2 = _as_design_cm2(abs(Mu_neg_tm) * 1e5, d_strap_cm, sb_cm, fcu_kgcm2, fy_kgcm2)
    As_bot_cm2 = _as_design_cm2(Mu_pos_tm * 1e5, d_strap_cm, sb_cm, fcu_kgcm2, fy_kgcm2)
    n_top = _bar_combo_cm2(As_top_cm2, int(long_dia_mm))
    n_bot = _bar_combo_cm2(As_bot_cm2, int(long_dia_mm))

    # Shear in Strap Beam
    Vu_ton = Ru1 - wu1 * (col1_from_f1 + d_strap_m)
    Vu_kg = abs(Vu_ton) * 1000.0
    tau_kgcm2 = Vu_kg / (sb_cm * d_strap_cm) if (sb_cm * d_strap_cm) > 0 else 0.0

    # Concrete shear capacity per ECP 203 in kg/cm²:
    # 0.24 * sqrt(fcu_MPa / 1.5) MPa -> in kg/cm² = 0.24 * sqrt((fcu_kgcm2/10)/1.5) * 10
    vc_kgcm2 = 0.24 * math.sqrt(max(0.0, (fcu_kgcm2 / 10.0) / 1.5)) * 10.0
    # ECP 203 maximum allowable shear capacity with shear reinforcement:
    # 0.70 * sqrt(fcu_MPa / 1.5) MPa -> in kg/cm²
    vc_max_kgcm2 = 0.70 * math.sqrt(max(0.0, (fcu_kgcm2 / 10.0) / 1.5)) * 10.0
    excess_kgcm2 = max(0.0, tau_kgcm2 - (vc_kgcm2 / 2.0))

    stirrup_dia_mm = float(d.get("stirrup_dia", 10.0))
    stirrup_per_m = float(d.get("stirrup_per_m", 5.0))
    if stirrup_per_m <= 0:
        stirrup_per_m = 5.0
    s_spacing_cm = 100.0 / stirrup_per_m

    # Number of branches: 4 branches if width b >= 40 cm, else 2 branches
    n_branches = 4 if sb_cm >= 40.0 else 2
    area_1bar_cm2 = math.pi * (stirrup_dia_mm / 10.0) ** 2 / 4.0
    # Provided stirrups area in cm²/m
    Asv_prov_cm2_m = stirrup_per_m * n_branches * area_1bar_cm2

    # Required stirrups area per meter per ECP 203:
    Asv_min_cm2_m = (0.40 * sb_cm * 100.0) / fy_kgcm2 if fy_kgcm2 > 0 else 0.0
    if excess_kgcm2 > 0 and fy_kgcm2 > 0:
        Asv_req_cm2_m = max((excess_kgcm2 * sb_cm * 100.0) / (fy_kgcm2 / 1.15), Asv_min_cm2_m)
    else:
        Asv_req_cm2_m = Asv_min_cm2_m

    Asv_req_cm2 = Asv_req_cm2_m * (s_spacing_cm / 100.0)

    # Provided shear strength from stirrups (kg/cm²):
    q_su_prov = (Asv_prov_cm2_m * (fy_kgcm2 / 1.15)) / (sb_cm * 100.0) if sb_cm > 0 else 0.0
    # Total shear resistance capacity:
    total_shear_cap_kgcm2 = min(vc_max_kgcm2, (vc_kgcm2 / 2.0) + q_su_prov if tau_kgcm2 > vc_kgcm2 else vc_kgcm2)

    concrete_shear_ok = tau_kgcm2 <= vc_kgcm2
    shear_max_ok = tau_kgcm2 <= vc_max_kgcm2
    stirrups_shear_ok = concrete_shear_ok or (shear_max_ok and Asv_prov_cm2_m >= (Asv_req_cm2_m - 1e-4))

    # 5. Transverse Footing Steel (تسليح القواعد العرضي)
    cantilever_f1_m = (B1 - sb_m) / 2.0  # m
    d_f1_cm = t1_cm - _COVER_CM - (float(d["trans_bar_dia"]) / 20.0)
    Mu_trans1_tm = qu1_tm2 * (cantilever_f1_m ** 2) / 2.0  # ton·m per meter strip
    As_trans1_cm2_m = _as_design_cm2(Mu_trans1_tm * 1e5, d_f1_cm, 100.0, fcu_kgcm2, fy_kgcm2)

    cantilever_f2_m = (B2 - sb_m) / 2.0  # m
    d_f2_cm = t2_cm - _COVER_CM - (float(d["trans_bar_dia"]) / 20.0)
    Mu_trans2_tm = qu2_tm2 * (cantilever_f2_m ** 2) / 2.0  # ton·m per meter strip
    As_trans2_cm2_m = _as_design_cm2(Mu_trans2_tm * 1e5, d_f2_cm, 100.0, fcu_kgcm2, fy_kgcm2)

    xc1 = ec + a1_m / 2.0
    xc2 = xc1 + S

    return {
        "L1": L1, "B1": B1, "t1_cm": t1_cm,
        "L2": L2, "B2": B2, "t2_cm": t2_cm,
        "e": e, "X": X,
        "R1": R1, "R2": R2,
        "q_act1": q_act1_kgcm2, "q_act1_tm2": q_act1_tm2,
        "q_act2": q_act2_kgcm2, "q_act2_tm2": q_act2_tm2,
        "qu1_tm2": qu1_tm2, "qu2_tm2": qu2_tm2,
        "Ru1": Ru1, "wu1": wu1,
        "Mu_neg": Mu_neg_tm, "Mu_pos": Mu_pos_tm,
        "As_top": As_top_cm2, "As_bot": As_bot_cm2,
        "n_top": n_top, "n_bot": n_bot,
        "d_strap_cm": d_strap_cm,
        "strap_D": sD_cm, "sD_cm": sD_cm,
        "strap_b": sb_cm, "sb_m": sb_m,
        "Vu_ton": Vu_ton,
        "tau_kgcm2": tau_kgcm2, "vc_kgcm2": vc_kgcm2,
        "vc_max_kgcm2": vc_max_kgcm2,
        "stirrup_per_m": stirrup_per_m,
        "n_branches": n_branches,
        "Asv_prov_cm2_m": Asv_prov_cm2_m,
        "Asv_req_cm2_m": Asv_req_cm2_m,
        "Asv_req_cm2": Asv_req_cm2,
        "q_su_prov": q_su_prov,
        "total_shear_cap_kgcm2": total_shear_cap_kgcm2,
        "concrete_shear_ok": concrete_shear_ok,
        "stirrups_shear_ok": stirrups_shear_ok,
        "shear_max_ok": shear_max_ok,
        "s_spacing_cm": s_spacing_cm,
        "As_trans1_per_m": As_trans1_cm2_m,
        "As_trans2_per_m": As_trans2_cm2_m,
        "cantilever_f1": cantilever_f1_m,
        "cantilever_f2": cantilever_f2_m,
        "xc1": xc1, "xc2": xc2,
        "sb_m": sb_m, "sD_cm": sD_cm,
        "a1_m": a1_m, "b1_m": b1_m,
        "a2_m": a2_m, "b2_m": b2_m,
        "P1u": P1u, "P2u": P2u,
        "P1w": P1w, "P2w": P2w,
        "col_weight_factor": cwf,
        "x0": x0,
        "Mu_max_strap": abs(Mu_neg_tm),
        "Mu_col1": Mu_col1_tm,
        "Mu_f1_edge": Mu_f1_edge_tm,
        "Mu_trans1": Mu_trans1_tm,
        "Mu_trans2": Mu_trans2_tm,
        "cantilever_f1_long": max(0.0, L1 - (ec + a1_m)),
        "cantilever_f2_long": max(0.0, (L2 - a2_m) / 2.0),
    }


# ── Drawing Engine ────────────────────────────────────────────────────────────
def _draw_plan(d: dict, r: dict):
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    L1, B1 = r["L1"], r["B1"]
    L2, B2 = r["L2"], r["B2"]
    xc1, xc2 = r["xc1"], r["xc2"]
    ec, sb_m = float(d["edge_clearance"]), r["sb_m"]
    a1_m, b1_m = r["a1_m"], r["b1_m"]
    a2_m, b2_m = r["a2_m"], r["b2_m"]

    # Footing 1 (Edge)
    ax.add_patch(patches.FancyBboxPatch(
        (0.0, -B1 / 2), L1, B1, boxstyle="round,pad=0.02",
        lw=1.8, edgecolor="#60a5fa", facecolor="#1d4ed8", alpha=0.35,
        label="Footing 1 (قاعدة الجار)",
    ))

    # Footing 2 (Interior)
    f2x = xc2 - L2 / 2
    ax.add_patch(patches.FancyBboxPatch(
        (f2x, -B2 / 2), L2, B2, boxstyle="round,pad=0.02",
        lw=1.8, edgecolor="#60a5fa", facecolor="#1d4ed8", alpha=0.35,
        label="Footing 2 (القاعدة الداخلية)",
    ))

    # Strap Beam
    strap_end = xc2 + a2_m / 2
    ax.add_patch(patches.Rectangle(
        (0, -sb_m / 2), strap_end, sb_m,
        lw=1.5, edgecolor="#4ade80", facecolor="#166534", alpha=0.65,
        label="Strap Beam (كمرة الشداد)",
    ))

    # Columns (Edge & Interior)
    c1_x = ec
    c1_y = -b1_m / 2
    ax.add_patch(patches.Rectangle(
        (c1_x, c1_y), a1_m, b1_m,
        lw=1.8, edgecolor="#f8fafc", facecolor="#334155",
        label="Col 1 (عمود الجار)",
    ))

    c2_x = xc2 - a2_m / 2
    c2_y = -b2_m / 2
    ax.add_patch(patches.Rectangle(
        (c2_x, c2_y), a2_m, b2_m,
        lw=1.8, edgecolor="#f8fafc", facecolor="#334155",
        label="Col 2 (العمود الداخلي)",
    ))

    # Property Line (حد الجار)
    y_top = max(B1, B2) / 2 + 0.70
    ax.plot([0, 0], [-y_top, y_top], color="#ef4444", lw=2.5, ls="--",
            label="حد الجار (Property Line)")
    ax.text(-0.06, y_top * 0.90, "حد الجار\nProperty Line", color="#ef4444",
            fontsize=8, ha="right", va="top", fontweight="bold")

    # Centrelines
    ax.plot([-0.2, strap_end + 0.3], [0, 0], color="#facc15", lw=0.9, ls="-.", alpha=0.7)
    ax.plot([xc1, xc1], [-b1_m / 2 - 0.25, b1_m / 2 + 0.25], color="#facc15", lw=0.8, ls="-.", alpha=0.6)
    ax.plot([xc2, xc2], [-b2_m / 2 - 0.25, b2_m / 2 + 0.25], color="#facc15", lw=0.8, ls="-.", alpha=0.6)

    # ── Dimension helper functions ───────────────────────────────────────────
    def dim_h(x1, x2, y, label, color="#38bdf8", offset=0.08, fontsize=8, tick=0.06):
        if abs(x2 - x1) < 1e-4:
            return
        ax.plot([x1, x1], [y - tick, y + tick], color=color, lw=0.9, alpha=0.85)
        ax.plot([x2, x2], [y - tick, y + tick], color=color, lw=0.9, alpha=0.85)
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.2, shrinkA=0, shrinkB=0))
        ax.text((x1 + x2) / 2, y + offset, label, ha="center", va="center",
                color=color, fontsize=fontsize, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="#0f172a", ec=color, lw=0.5, alpha=0.85))

    def dim_v(y1, y2, x, label, color="#38bdf8", offset=0.08, fontsize=8, tick=0.06, text_side="right"):
        if abs(y2 - y1) < 1e-4:
            return
        ax.plot([x - tick, x + tick], [y1, y1], color=color, lw=0.9, alpha=0.85)
        ax.plot([x - tick, x + tick], [y2, y2], color=color, lw=0.9, alpha=0.85)
        ax.annotate("", xy=(x, y2), xytext=(x, y1),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.2, shrinkA=0, shrinkB=0))
        ha = "left" if text_side == "right" else "right"
        ax.text(x + offset, (y1 + y2) / 2, label, ha=ha, va="center", rotation=90,
                color=color, fontsize=fontsize, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="#0f172a", ec=color, lw=0.5, alpha=0.85))

    # ── 1. Edge Clearance Dimension (المسافة لحد الجار) ────────────────────────
    if ec > 0.01:
        dim_h(0, ec, b1_m / 2 + 0.22, f"ec = {ec:.2f} m ({ec*100:.0f} cm)",
              color="#fb7185", offset=0.09, fontsize=7.5)
        ax.plot([ec, ec], [b1_m / 2, b1_m / 2 + 0.28], color="#fb7185", lw=0.7, ls=":", alpha=0.7)
    else:
        ax.annotate(
            "ec = 0.00 m\n(Flush ملاصق لحد الجار)",
            xy=(0, b1_m / 2 + 0.05), xytext=(0.28, b1_m / 2 + 0.32),
            arrowprops=dict(arrowstyle="->", color="#fb7185", lw=1.2),
            color="#fb7185", fontsize=7.5, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="#0f172a", ec="#fb7185", lw=0.7, alpha=0.9),
        )

    # ── 2. Footing Dimensions (L1, B1, L2, B2) ──────────────────────────────
    # Footing 1: L1 (top) & B1 (left)
    dim_y_top1 = B1 / 2 + 0.30
    dim_h(0, L1, dim_y_top1, f"L1 = {L1:.2f} m ({L1*100:.0f} cm)", color="#60a5fa", offset=0.09, fontsize=8)
    dim_v(-B1 / 2, B1 / 2, -0.42, f"B1 = {B1:.2f} m ({B1*100:.0f} cm)", color="#60a5fa", offset=-0.08, fontsize=8, text_side="left")

    # Footing 2: L2 (top) & B2 (right)
    dim_y_top2 = B2 / 2 + 0.30
    dim_h(f2x, f2x + L2, dim_y_top2, f"L2 = {L2:.2f} m ({L2*100:.0f} cm)", color="#60a5fa", offset=0.09, fontsize=8)
    dim_v(-B2 / 2, B2 / 2, f2x + L2 + 0.42, f"B2 = {B2:.2f} m ({B2*100:.0f} cm)", color="#60a5fa", offset=0.08, fontsize=8, text_side="right")

    # ── 3. Span S between column centers (bottom) ────────────────────────────
    y_span = -max(B1, B2) / 2 - 0.42
    ax.plot([xc1, xc1], [-b1_m / 2, y_span - 0.08], color="#facc15", lw=0.7, ls=":", alpha=0.6)
    ax.plot([xc2, xc2], [-b2_m / 2, y_span - 0.08], color="#facc15", lw=0.7, ls=":", alpha=0.6)
    dim_h(xc1, xc2, y_span, f"S = {d['S']:.2f} m (المسافة بين المحاور)", color="#facc15", offset=-0.10, fontsize=8.5)

    # ── 4. Column Dimensions (a1, b1, a2, b2) ────────────────────────────────
    # Col 1: a1 (below col), b1 (right of col)
    dim_h(c1_x, c1_x + a1_m, c1_y - 0.12, f"a1={d['a1']:.0f}cm", color="#f8fafc", offset=-0.06, fontsize=7, tick=0.04)
    dim_v(c1_y, c1_y + b1_m, c1_x + a1_m + 0.10, f"b1={d['b1']:.0f}cm", color="#f8fafc", offset=0.06, fontsize=7, tick=0.04, text_side="right")
    ax.text(xc1, 0, "C1", color="#ffffff", ha="center", va="center", fontsize=8, fontweight="bold")

    # Col 2: a2 (below col), b2 (right of col)
    dim_h(c2_x, c2_x + a2_m, c2_y - 0.12, f"a2={d['a2']:.0f}cm", color="#f8fafc", offset=-0.06, fontsize=7, tick=0.04)
    dim_v(c2_y, c2_y + b2_m, c2_x + a2_m + 0.10, f"b2={d['b2']:.0f}cm", color="#f8fafc", offset=0.06, fontsize=7, tick=0.04, text_side="right")
    ax.text(xc2, 0, "C2", color="#ffffff", ha="center", va="center", fontsize=8, fontweight="bold")

    # Footing & Beam Labels
    ax.text(L1 / 2, -B1 / 2 + 0.14, "Footing 1 (قاعدة الجار)", color="#93c5fd",
            ha="center", fontsize=8.5, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc="#0f172a", ec="none", alpha=0.7))
    ax.text(xc2, -B2 / 2 + 0.14, "Footing 2 (القاعدة الداخلية)", color="#93c5fd",
            ha="center", fontsize=8.5, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc="#0f172a", ec="none", alpha=0.7))
    ax.text((0 + strap_end) / 2, sb_m / 2 + 0.08, f"كمرة الشداد Strap Beam ({d['strap_b']:.0f} × {d['strap_D']:.0f} cm)", color="#86efac",
            ha="center", fontsize=8, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc="#0f172a", ec="none", alpha=0.7))

    x_min = -0.95
    x_max = f2x + L2 + 1.10
    y_max_view = max(B1, B2) / 2 + 0.95
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-y_max_view, y_max_view)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X (m)", color="#94a3b8", fontsize=9)
    ax.set_ylabel("Y (m)", color="#94a3b8", fontsize=9)
    ax.tick_params(colors="#94a3b8", labelsize=7.5)
    for spine in ax.spines.values():
        spine.set_edgecolor("#334155")
    ax.grid(True, ls=":", alpha=0.25, color="#475569")
    ax.legend(loc="upper right", fontsize=7.5, facecolor="#1e293b",
              edgecolor="#475569", labelcolor="#e2e8f0", framealpha=0.9)
    ax.set_title("Strap Footing — Plan View with Detailed Dimension Lines (ECP 203)",
                 color="#f1f5f9", fontsize=11, fontweight="bold", pad=10)
    fig.tight_layout()
    return fig


def _draw_detailing_elevation(d: dict, r: dict, n_t1: int, n_t2: int):
    fig, ax = plt.subplots(figsize=(14, 7.5))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    L1, t1 = r["L1"], r["t1_cm"] / 100.0
    L2, t2 = r["L2"], r["t2_cm"] / 100.0
    sD = r["sD_cm"] / 100.0
    sb_m = r["sb_m"]
    S = float(d["S"])
    ec = float(d["edge_clearance"])
    a1_m, b1_m = r["a1_m"], r["b1_m"]
    a2_m, b2_m = r["a2_m"], r["b2_m"]
    xc1, xc2 = r["xc1"], r["xc2"]
    f2x = xc2 - L2 / 2.0
    strap_end = xc2 + a2_m / 2.0 + 0.20
    tpc = float(d.get("t_pc", 0.0)) / 100.0

    # 1. Plain Concrete Layer (PC)
    if tpc > 0.04:
        ax.add_patch(patches.Rectangle((0, -tpc), L1 + tpc, tpc, facecolor="#334155", edgecolor="#64748b", lw=1.2, alpha=0.5, hatch="//", label="خرسانة عادية PC"))
        ax.add_patch(patches.Rectangle((f2x - tpc, -tpc), L2 + 2 * tpc, tpc, facecolor="#334155", edgecolor="#64748b", lw=1.2, alpha=0.5, hatch="//"))
        if f2x > (L1 + tpc):
            ax.add_patch(patches.Rectangle((L1 + tpc, -tpc), (f2x - tpc) - (L1 + tpc), tpc, facecolor="#1e293b", edgecolor="#475569", lw=1.0, ls=":"))

    # 2. Footing 1 RC
    ax.add_patch(patches.Rectangle((0, 0), L1, t1, facecolor="#1d4ed8", edgecolor="#60a5fa", lw=2.0, alpha=0.35, label="قاعدة الجار (Footing 1)"))
    # 3. Footing 2 RC
    ax.add_patch(patches.Rectangle((f2x, 0), L2, t2, facecolor="#1d4ed8", edgecolor="#60a5fa", lw=2.0, alpha=0.35, label="القاعدة الداخلية (Footing 2)"))
    # 4. Strap Beam RC
    ax.add_patch(patches.Rectangle((0, 0), strap_end, sD, facecolor="#166534", edgecolor="#4ade80", lw=2.2, alpha=0.50, label="كمرة الشداد (Strap Beam)"))

    # 5. Columns
    col_h = 0.85
    c1_x = ec
    c2_x = xc2 - a2_m / 2.0
    ax.add_patch(patches.Rectangle((c1_x, sD), a1_m, col_h, facecolor="#475569", edgecolor="#f8fafc", lw=1.8, label="الأعمدة (Columns)"))
    ax.add_patch(patches.Rectangle((c2_x, sD), a2_m, col_h, facecolor="#475569", edgecolor="#f8fafc", lw=1.8))
    ax.text(c1_x + a1_m / 2.0, sD + col_h / 2.0, f"C1\n{d['a1']:.0f}x{d['b1']:.0f}", color="#f8fafc", ha="center", va="center", fontsize=8, fontweight="bold")
    ax.text(c2_x + a2_m / 2.0, sD + col_h / 2.0, f"C2\n{d['a2']:.0f}x{d['b2']:.0f}", color="#f8fafc", ha="center", va="center", fontsize=8, fontweight="bold")

    # Column Starter Bars / Dowels
    dowel_cov = 0.04
    ax.plot([c1_x + dowel_cov, c1_x + dowel_cov], [0.08, sD + col_h * 0.85], color="#cbd5e1", lw=1.4, ls="--", alpha=0.75)
    ax.plot([c1_x + dowel_cov, c1_x + a1_m - dowel_cov], [0.08, 0.08], color="#cbd5e1", lw=1.4, ls="--", alpha=0.75)
    ax.plot([c1_x + a1_m - dowel_cov, c1_x + a1_m - dowel_cov], [0.08, sD + col_h * 0.85], color="#cbd5e1", lw=1.4, ls="--", alpha=0.75)

    ax.plot([c2_x + dowel_cov, c2_x + dowel_cov], [0.08, sD + col_h * 0.85], color="#cbd5e1", lw=1.4, ls="--", alpha=0.75)
    ax.plot([c2_x + dowel_cov, c2_x + a2_m - dowel_cov], [0.08, 0.08], color="#cbd5e1", lw=1.4, ls="--", alpha=0.75)
    ax.plot([c2_x + a2_m - dowel_cov, c2_x + a2_m - dowel_cov], [0.08, sD + col_h * 0.85], color="#cbd5e1", lw=1.4, ls="--", alpha=0.75)

    # 6. Rebar: Top Steel (الحديد العلوي الرئيسي)
    cov = 0.05
    top_y = sD - cov
    ax.plot([cov, strap_end - cov], [top_y, top_y], color="#f43f5e", lw=3.2, zorder=6, label=f"علوي: {r['n_top']}Φ{int(d['long_bar_dia'])}")
    ax.plot([cov, cov], [0.08, top_y], color="#f43f5e", lw=3.2, zorder=6)
    ax.plot([strap_end - cov, strap_end - cov], [0.08, top_y], color="#f43f5e", lw=3.2, zorder=6)

    # 7. Rebar: Bottom Steel (الحديد السفلي)
    bot_y = cov
    ax.plot([cov, strap_end - cov], [bot_y, bot_y], color="#38bdf8", lw=2.6, zorder=6, label=f"سفلي: {r['n_bot']}Φ{int(d['long_bar_dia'])}")
    ax.plot([cov, cov], [bot_y, bot_y + 0.18], color="#38bdf8", lw=2.6, zorder=6)
    ax.plot([strap_end - cov, strap_end - cov], [bot_y, bot_y + 0.18], color="#38bdf8", lw=2.6, zorder=6)

    # 8. Rebar: Side Bars (براندات الانكماش)
    if sD >= 0.60:
        n_side_pairs = max(1, int(sD / 0.30) - 1)
        step_y = (top_y - bot_y) / (n_side_pairs + 1)
        for sp_idx in range(1, n_side_pairs + 1):
            sy = bot_y + sp_idx * step_y
            ax.plot([cov + 0.02, strap_end - cov - 0.02], [sy, sy], color="#fb923c", lw=1.6, ls="--", zorder=5)

    # 9. Rebar: Stirrups (الكانات)
    spm = float(r.get("stirrup_per_m", 5.0))
    s_spacing_m = 1.0 / spm
    cur_x = cov + 0.08
    while cur_x <= (strap_end - cov - 0.04):
        ax.plot([cur_x, cur_x], [bot_y, top_y], color="#4ade80", lw=1.4, alpha=0.85, zorder=4)
        cur_x += s_spacing_m

    # 10. Footing Transverse Rebar Dots (دوائر الحديد العرضي للقواعد)
    dot_y = cov + 0.015
    f1_dots_x = [0.08 + i * (L1 - 0.16) / max(1, n_t1 - 1) for i in range(min(16, n_t1))]
    for dx_val in f1_dots_x:
        ax.plot(dx_val, dot_y, "o", color="#38bdf8", markersize=4.2, zorder=7)

    f2_dots_x = [f2x + 0.08 + i * (L2 - 0.16) / max(1, n_t2 - 1) for i in range(min(16, n_t2))]
    for dx_val in f2_dots_x:
        ax.plot(dx_val, dot_y, "o", color="#38bdf8", markersize=4.2, zorder=7)

    # Helper for dimension lines
    def edim_h(x1, x2, y, label, color="#38bdf8", offset=0.08, fontsize=8):
        ax.plot([x1, x1], [y - 0.04, y + 0.04], color=color, lw=0.9, alpha=0.85)
        ax.plot([x2, x2], [y - 0.04, y + 0.04], color=color, lw=0.9, alpha=0.85)
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.1, shrinkA=0, shrinkB=0))
        ax.text((x1 + x2) / 2, y + offset, label, ha="center", va="center",
                color=color, fontsize=fontsize, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="#0f172a", ec=color, lw=0.5, alpha=0.85))

    def edim_v(y1, y2, x, label, color="#38bdf8", offset=0.08, fontsize=8):
        ax.plot([x - 0.04, x + 0.04], [y1, y1], color=color, lw=0.9, alpha=0.85)
        ax.plot([x - 0.04, x + 0.04], [y2, y2], color=color, lw=0.9, alpha=0.85)
        ax.annotate("", xy=(x, y2), xytext=(x, y1),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.1, shrinkA=0, shrinkB=0))
        ax.text(x + offset, (y1 + y2) / 2, label, ha="left", va="center", rotation=90,
                color=color, fontsize=fontsize, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="#0f172a", ec=color, lw=0.5, alpha=0.85))

    # Dimensions on Elevation
    edim_v(0, sD, -0.38, f"D={r['sD_cm']:.0f}cm", color="#4ade80", offset=-0.08, fontsize=7.5)
    edim_v(0, t1, -0.62, f"t1={r['t1_cm']:.0f}cm", color="#60a5fa", offset=-0.08, fontsize=7.5)
    if tpc > 0.04:
        edim_v(-tpc, 0, -0.62, f"tpc={d['t_pc']:.0f}cm", color="#94a3b8", offset=-0.08, fontsize=7)

    edim_v(0, t2, strap_end + 0.35, f"t2={r['t2_cm']:.0f}cm", color="#60a5fa", offset=0.08, fontsize=7.5)

    y_dim_b = -0.35 if tpc <= 0 else -tpc - 0.30
    edim_h(0, L1, y_dim_b, f"L1={L1:.2f}m", color="#60a5fa", offset=-0.08, fontsize=8)
    edim_h(f2x, f2x + L2, y_dim_b, f"L2={L2:.2f}m", color="#60a5fa", offset=-0.08, fontsize=8)
    edim_h(xc1, xc2, y_dim_b - 0.28, f"S = {S:.2f} m (المسافة بين محاور الأعمدة)", color="#facc15", offset=-0.09, fontsize=8)

    # Callout Badges
    mid_x = (L1 + f2x) / 2.0
    ax.annotate(
        f"الحديد العلوي الرئيسي (Top Rebar):\n{r['n_top']} Φ {int(d['long_bar_dia'])} mm (عزم سالب Mu = {r['Mu_neg']:.1f} t.m)",
        xy=(mid_x, top_y), xytext=(mid_x, top_y + 0.46),
        arrowprops=dict(arrowstyle="->", color="#f43f5e", lw=1.5),
        color="#fecdd3", fontsize=8.5, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.25", fc="#1e293b", ec="#f43f5e", lw=1.2)
    )

    ax.annotate(
        f"الحديد السفلي (Bottom Rebar):\n{r['n_bot']} Φ {int(d['long_bar_dia'])} mm",
        xy=(mid_x, bot_y), xytext=(mid_x, y_dim_b + 0.08),
        arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.5),
        color="#bae6fd", fontsize=8.5, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.25", fc="#1e293b", ec="#38bdf8", lw=1.2)
    )

    st_call_x = (c1_x + a1_m + L1) / 2.0
    ax.annotate(
        f"كانات الشداد:\n{int(spm)} Φ {int(d['stirrup_dia'])} mm / م\n({r['n_branches']} فروع)",
        xy=(st_call_x, sD / 2.0), xytext=(st_call_x - 0.15, sD / 2.0 + 0.42),
        arrowprops=dict(arrowstyle="->", color="#4ade80", lw=1.4),
        color="#bbf7d0", fontsize=8, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="#1e293b", ec="#4ade80", lw=1.1)
    )

    # Property Line
    y_top_limit = sD + col_h + 0.35
    y_bot_limit = y_dim_b - 0.42
    ax.plot([0, 0], [y_bot_limit, y_top_limit], color="#ef4444", lw=2.2, ls="--")
    ax.text(-0.06, y_top_limit * 0.92, "حد الجار\nProperty Line", color="#ef4444", fontsize=7.5, ha="right", va="top", fontweight="bold")

    ax.set_xlim(-0.85, strap_end + 0.65)
    ax.set_ylim(y_bot_limit, y_top_limit)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X (m)", color="#94a3b8", fontsize=9)
    ax.set_ylabel("المنسوب / الارتفاع Y (m)", color="#94a3b8", fontsize=9)
    ax.tick_params(colors="#94a3b8", labelsize=7.5)
    for spine in ax.spines.values():
        spine.set_edgecolor("#334155")
    ax.grid(True, ls=":", alpha=0.25, color="#475569")
    ax.legend(loc="upper right", fontsize=7.5, facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0", framealpha=0.9)
    ax.set_title("Longitudinal Section & Rebar Detailing — القطاع الطولي وتفريد التسليح (ECP 203)",
                 color="#f1f5f9", fontsize=11, fontweight="bold", pad=10)
    fig.tight_layout()
    return fig


def _draw_detailing_plan(d: dict, r: dict, n_t1: int, n_t2: int):
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    L1, B1 = r["L1"], r["B1"]
    L2, B2 = r["L2"], r["B2"]
    xc1, xc2 = r["xc1"], r["xc2"]
    S = float(d["S"])
    ec, sb_m = float(d["edge_clearance"]), r["sb_m"]
    a1_m, b1_m = r["a1_m"], r["b1_m"]
    a2_m, b2_m = r["a2_m"], r["b2_m"]
    f2x = xc2 - L2 / 2.0
    strap_end = xc2 + a2_m / 2.0 + 0.15

    # Footing 1 (Edge)
    ax.add_patch(patches.FancyBboxPatch(
        (0.0, -B1 / 2), L1, B1, boxstyle="round,pad=0.02",
        lw=1.8, edgecolor="#60a5fa", facecolor="#1d4ed8", alpha=0.30,
        label="قاعدة الجار (Footing 1)",
    ))

    # Footing 2 (Interior)
    ax.add_patch(patches.FancyBboxPatch(
        (f2x, -B2 / 2), L2, B2, boxstyle="round,pad=0.02",
        lw=1.8, edgecolor="#60a5fa", facecolor="#1d4ed8", alpha=0.30,
        label="القاعدة الداخلية (Footing 2)",
    ))

    # Strap Beam
    ax.add_patch(patches.Rectangle(
        (0, -sb_m / 2), strap_end, sb_m,
        lw=1.8, edgecolor="#4ade80", facecolor="#166534", alpha=0.55,
        label="كمرة الشداد (Strap Beam)",
    ))

    # Transverse rebar lines in Footing 1 (الحديد العرضي الرئيسي)
    num_vis1 = min(12, max(5, int(n_t1)))
    f1_trans_xs = [0.08 + i * (L1 - 0.16) / max(1, num_vis1 - 1) for i in range(num_vis1)]
    for xb in f1_trans_xs:
        ax.plot([xb, xb], [-B1 / 2 + 0.05, B1 / 2 - 0.05], color="#38bdf8", lw=1.2, alpha=0.85)
        ax.plot([xb - 0.04, xb], [B1 / 2 - 0.05, B1 / 2 - 0.05], color="#38bdf8", lw=1.2)
        ax.plot([xb - 0.04, xb], [-B1 / 2 + 0.05, -B1 / 2 + 0.05], color="#38bdf8", lw=1.2)
    target_cyan_x1 = f1_trans_xs[len(f1_trans_xs) // 2]

    # Longitudinal distribution rebar lines in Footing 1 (الحديد الطولي الثانوي الموازي للشداد 5 فاي 12/م)
    n_long1 = max(4, int(round(B1 * 5.0)))
    num_vis_long1 = min(10, max(4, n_long1))
    for yb in [-B1 / 2 + 0.08 + i * (B1 - 0.16) / max(1, num_vis_long1 - 1) for i in range(num_vis_long1)]:
        if abs(yb) > (sb_m / 2.0 - 0.04):
            ax.plot([0.06, L1 - 0.06], [yb, yb], color="#c084fc", lw=1.1, alpha=0.85)
            ax.plot([0.06, 0.06], [yb - 0.04, yb], color="#c084fc", lw=1.1)
            ax.plot([L1 - 0.06, L1 - 0.06], [yb - 0.04, yb], color="#c084fc", lw=1.1)

    # Transverse rebar lines in Footing 2 (الحديد العرضي الرئيسي)
    num_vis2 = min(12, max(5, int(n_t2)))
    f2_trans_xs = [f2x + 0.08 + i * (L2 - 0.16) / max(1, num_vis2 - 1) for i in range(num_vis2)]
    for xb in f2_trans_xs:
        ax.plot([xb, xb], [-B2 / 2 + 0.05, B2 / 2 - 0.05], color="#38bdf8", lw=1.2, alpha=0.85)
        ax.plot([xb - 0.04, xb], [B2 / 2 - 0.05, B2 / 2 - 0.05], color="#38bdf8", lw=1.2)
        ax.plot([xb - 0.04, xb], [-B2 / 2 + 0.05, -B2 / 2 + 0.05], color="#38bdf8", lw=1.2)
    target_cyan_x2 = f2_trans_xs[len(f2_trans_xs) // 2]

    # Longitudinal distribution rebar lines in Footing 2 (الحديد الطولي الثانوي الموازي للشداد 5 فاي 12/م)
    n_long2 = max(4, int(round(B2 * 5.0)))
    num_vis_long2 = min(10, max(4, n_long2))
    for yb in [-B2 / 2 + 0.08 + i * (B2 - 0.16) / max(1, num_vis_long2 - 1) for i in range(num_vis_long2)]:
        if abs(yb) > (sb_m / 2.0 - 0.04):
            ax.plot([f2x + 0.06, f2x + L2 - 0.06], [yb, yb], color="#c084fc", lw=1.1, alpha=0.85)
            ax.plot([f2x + 0.06, f2x + 0.06], [yb - 0.04, yb], color="#c084fc", lw=1.1)
            ax.plot([f2x + L2 - 0.06, f2x + L2 - 0.06], [yb - 0.04, yb], color="#c084fc", lw=1.1)

    # Stirrup lines along Strap Beam in Plan
    spm = float(r.get("stirrup_per_m", 5.0))
    s_step = 1.0 / spm
    cur_x = 0.10
    while cur_x <= (strap_end - 0.05):
        ax.plot([cur_x, cur_x], [-sb_m / 2 + 0.03, sb_m / 2 - 0.03], color="#4ade80", lw=1.2, alpha=0.8)
        cur_x += s_step

    # Columns
    c1_x, c1_y = ec, -b1_m / 2
    c2_x, c2_y = xc2 - a2_m / 2, -b2_m / 2
    ax.add_patch(patches.Rectangle((c1_x, c1_y), a1_m, b1_m, lw=1.8, edgecolor="#f8fafc", facecolor="#334155", label="الأعمدة (Columns)"))
    ax.add_patch(patches.Rectangle((c2_x, c2_y), a2_m, b2_m, lw=1.8, edgecolor="#f8fafc", facecolor="#334155"))
    ax.text(xc1, 0, f"C1\n{d['a1']:.0f}×{d['b1']:.0f}", color="#ffffff", ha="center", va="center", fontsize=7.5, fontweight="bold")
    ax.text(xc2, 0, f"C2\n{d['a2']:.0f}×{d['b2']:.0f}", color="#ffffff", ha="center", va="center", fontsize=7.5, fontweight="bold")

    # Property Line
    y_top = max(B1, B2) / 2 + 0.75
    ax.plot([0, 0], [-y_top, y_top], color="#ef4444", lw=2.5, ls="--", label="حد الجار (Property Line)")
    ax.text(-0.06, y_top * 0.90, "حد الجار\nProperty Line", color="#ef4444", fontsize=8, ha="right", va="top", fontweight="bold")

    # Centrelines
    ax.plot([-0.2, strap_end + 0.3], [0, 0], color="#facc15", lw=0.9, ls="-.", alpha=0.7)
    ax.plot([xc1, xc1], [-b1_m / 2 - 0.25, b1_m / 2 + 0.25], color="#facc15", lw=0.8, ls="-.", alpha=0.6)
    ax.plot([xc2, xc2], [-b2_m / 2 - 0.25, b2_m / 2 + 0.25], color="#facc15", lw=0.8, ls="-.", alpha=0.6)

    # Dimension helper functions
    def pdim_h(x1, x2, y, label, color="#38bdf8", offset=0.06, fontsize=7.8):
        if abs(x2 - x1) < 1e-4:
            return
        ax.plot([x1, x1], [y - 0.04, y + 0.04], color=color, lw=0.9, alpha=0.85)
        ax.plot([x2, x2], [y - 0.04, y + 0.04], color=color, lw=0.9, alpha=0.85)
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.1, shrinkA=0, shrinkB=0))
        ax.text((x1 + x2) / 2, y + offset, label, ha="center", va="bottom",
                color=color, fontsize=fontsize, fontweight="bold")

    def pdim_v(y1, y2, x, label, color="#38bdf8", offset=0.06, fontsize=7.8, text_side="right"):
        if abs(y2 - y1) < 1e-4:
            return
        ax.plot([x - 0.04, x + 0.04], [y1, y1], color=color, lw=0.9, alpha=0.85)
        ax.plot([x - 0.04, x + 0.04], [y2, y2], color=color, lw=0.9, alpha=0.85)
        ax.annotate("", xy=(x, y2), xytext=(x, y1),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.1, shrinkA=0, shrinkB=0))
        ha = "left" if text_side == "right" else "right"
        ax.text(x + offset, (y1 + y2) / 2, label, ha=ha, va="center", rotation=90,
                color=color, fontsize=fontsize, fontweight="bold")

    # ── Dimensions & Cantilevers ──────────────────────────────────────────────
    cant1_long = max(0.0, L1 - (ec + a1_m))
    cant2_long = max(0.0, (L2 - a2_m) / 2.0)
    cant1_trans = r["cantilever_f1"]
    cant2_trans = r["cantilever_f2"]

    # Footing 1 Top Dimension Strings (Level 1: Cantilever & Column, Level 2: Total L1)
    dim_y_top1 = B1 / 2 + 0.28
    if ec > 0.03:
        pdim_h(0, ec, dim_y_top1, f"ec={ec:.2f}m", color="#f87171", offset=0.07, fontsize=7.2)
    pdim_h(ec, ec + a1_m, dim_y_top1, f"a1={d['a1']:.0f}cm", color="#e2e8f0", offset=0.07, fontsize=7.2)
    pdim_h(ec + a1_m, L1, dim_y_top1, f"رفرفة={cant1_long:.2f}m", color="#a78bfa", offset=0.07, fontsize=7.2)
    pdim_h(0, L1, dim_y_top1 + 0.32, f"L1 = {L1:.2f} m", color="#60a5fa", offset=0.08, fontsize=8)

    # Footing 2 Top Dimension Strings (Level 1: Cantilevers & Column, Level 2: Total L2)
    dim_y_top2 = B2 / 2 + 0.28
    pdim_h(f2x, xc2 - a2_m / 2, dim_y_top2, f"رفرفة={cant2_long:.2f}m", color="#a78bfa", offset=0.07, fontsize=7.2)
    pdim_h(xc2 - a2_m / 2, xc2 + a2_m / 2, dim_y_top2, f"a2={d['a2']:.0f}cm", color="#e2e8f0", offset=0.07, fontsize=7.2)
    pdim_h(xc2 + a2_m / 2, f2x + L2, dim_y_top2, f"رفرفة={cant2_long:.2f}m", color="#a78bfa", offset=0.07, fontsize=7.2)
    pdim_h(f2x, f2x + L2, dim_y_top2 + 0.32, f"L2 = {L2:.2f} m", color="#60a5fa", offset=0.08, fontsize=8)

    # Vertical Dimensions: Total Footing Widths
    pdim_v(-B1 / 2, B1 / 2, -0.45, f"B1 = {B1:.2f} m", color="#60a5fa", offset=-0.08, fontsize=8, text_side="left")
    pdim_v(-B2 / 2, B2 / 2, f2x + L2 + 0.45, f"B2 = {B2:.2f} m", color="#60a5fa", offset=0.08, fontsize=8, text_side="right")

    # Transverse Cantilevers Dimensions (رفرفة القواعد العرضية خارج الشداد)
    x_dim_trans1 = L1 + 0.16
    pdim_v(sb_m / 2, B1 / 2, x_dim_trans1, f"رفرفة={cant1_trans:.2f}m", color="#38bdf8", offset=0.07, fontsize=7.2, text_side="right")
    pdim_v(-B1 / 2, -sb_m / 2, x_dim_trans1, f"رفرفة={cant1_trans:.2f}m", color="#38bdf8", offset=0.07, fontsize=7.2, text_side="right")
    pdim_v(-sb_m / 2, sb_m / 2, x_dim_trans1, f"b={d['strap_b']:.0f}cm", color="#4ade80", offset=0.07, fontsize=7.2, text_side="right")

    x_dim_trans2 = f2x - 0.16
    pdim_v(sb_m / 2, B2 / 2, x_dim_trans2, f"رفرفة={cant2_trans:.2f}m", color="#38bdf8", offset=-0.07, fontsize=7.2, text_side="left")
    pdim_v(-B2 / 2, -sb_m / 2, x_dim_trans2, f"رفرفة={cant2_trans:.2f}m", color="#38bdf8", offset=-0.07, fontsize=7.2, text_side="left")
    pdim_v(-sb_m / 2, sb_m / 2, x_dim_trans2, f"b={d['strap_b']:.0f}cm", color="#4ade80", offset=-0.07, fontsize=7.2, text_side="left")

    y_span = -max(B1, B2) / 2 - 0.45
    pdim_h(xc1, xc2, y_span, f"S = {S:.2f} m", color="#facc15", offset=-0.10, fontsize=8.5)

    # Rebar Callouts on Plan
    # Footing 1 Transverse (Top) -> points directly to the cyan line!
    ax.annotate(
        f"تسليح عرضي رئيسي F1:\n{n_t1} Φ {int(d['trans_bar_dia'])} mm\n({r['As_trans1_per_m']:.2f} cm²/m)",
        xy=(target_cyan_x1, B1 / 2.0 - 0.12), xytext=(L1 / 2.0, B1 / 2.0 + 1.15),
        arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.6),
        color="#bae6fd", fontsize=8, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="#1e293b", ec="#38bdf8", lw=1.2)
    )
    ax.plot([target_cyan_x1], [B1 / 2.0 - 0.12], "o", color="#38bdf8", markersize=4.5, zorder=8)

    # Footing 1 Longitudinal Secondary (Bottom) -> moved down by 2 lines to avoid dimension line!
    y_call_bot1 = -max(B1, B2) / 2.0 - 1.45
    ax.annotate(
        f"تسليح طولي ثانوي F1 (موازي للشداد):\n5 Φ 12 mm / م (توزيع وانكماش)\n(إجمالي {n_long1} أسياخ على B1)",
        xy=(L1 * 0.45, -B1 / 4.0), xytext=(L1 / 2.0, y_call_bot1),
        arrowprops=dict(arrowstyle="->", color="#c084fc", lw=1.3),
        color="#f3e8ff", fontsize=7.8, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="#1e293b", ec="#c084fc", lw=1.1)
    )

    # Footing 2 Transverse (Top) -> points directly to the cyan line!
    ax.annotate(
        f"تسليح عرضي رئيسي F2:\n{n_t2} Φ {int(d['trans_bar_dia'])} mm\n({r['As_trans2_per_m']:.2f} cm²/m)",
        xy=(target_cyan_x2, B2 / 2.0 - 0.12), xytext=(xc2, B2 / 2.0 + 1.15),
        arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.6),
        color="#bae6fd", fontsize=8, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="#1e293b", ec="#38bdf8", lw=1.2)
    )
    ax.plot([target_cyan_x2], [B2 / 2.0 - 0.12], "o", color="#38bdf8", markersize=4.5, zorder=8)

    # Footing 2 Longitudinal Secondary (Bottom) -> moved down by 2 lines to avoid dimension line!
    y_call_bot2 = -max(B1, B2) / 2.0 - 1.45
    ax.annotate(
        f"تسليح طولي ثانوي F2 (موازي للشداد):\n5 Φ 12 mm / م (توزيع وانكماش)\n(إجمالي {n_long2} أسياخ على B2)",
        xy=(xc2, -B2 / 4.0), xytext=(xc2, y_call_bot2),
        arrowprops=dict(arrowstyle="->", color="#c084fc", lw=1.3),
        color="#f3e8ff", fontsize=7.8, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="#1e293b", ec="#c084fc", lw=1.1)
    )

    # Strap Beam Callout (Center between Footings) -> moved down by 2 lines to avoid dimension line!
    mid_strap = (L1 + f2x) / 2.0
    y_call_strap = -max(B1, B2) / 2.0 - 1.50
    ax.annotate(
        f"كمرة الشداد ({d['strap_b']:.0f}×{r['sD_cm']:.0f} cm):\nعلوي: {r['n_top']}Φ{int(d['long_bar_dia'])} | سفلي: {r['n_bot']}Φ{int(d['long_bar_dia'])}\nكانات: {int(spm)}Φ{int(d['stirrup_dia'])}/م ({r['n_branches']} فروع)",
        xy=(mid_strap, 0), xytext=(mid_strap, y_call_strap),
        arrowprops=dict(arrowstyle="->", color="#4ade80", lw=1.4),
        color="#bbf7d0", fontsize=8.5, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.25", fc="#1e293b", ec="#4ade80", lw=1.2)
    )

    x_min = -0.95
    x_max = f2x + L2 + 1.10
    y_top_view = max(B1, B2) / 2.0 + 2.05
    y_bot_view = -max(B1, B2) / 2.0 - 2.25
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_bot_view, y_top_view)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X (m)", color="#94a3b8", fontsize=9)
    ax.set_ylabel("Y (m)", color="#94a3b8", fontsize=9)
    ax.tick_params(colors="#94a3b8", labelsize=7.5)
    for spine in ax.spines.values():
        spine.set_edgecolor("#334155")
    ax.grid(True, ls=":", alpha=0.25, color="#475569")
    ax.legend(loc="upper right", fontsize=7.5, facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0", framealpha=0.9)
    ax.set_title("Structural Plan Detailing — المسقط الأفقي وتفريد التسليح (ECP 203)",
                 color="#f1f5f9", fontsize=11, fontweight="bold", pad=10)
    fig.tight_layout()
    return fig


def _draw_bending_moment_diagram(d: dict, r: dict):
    fig = plt.figure(figsize=(14, 9))
    fig.patch.set_facecolor("#0f172a")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.7, 1.0], hspace=0.38, wspace=0.25)
    ax_strap = fig.add_subplot(gs[0, :])
    ax_f1 = fig.add_subplot(gs[1, 0])
    ax_f2 = fig.add_subplot(gs[1, 1])

    for ax in (ax_strap, ax_f1, ax_f2):
        ax.set_facecolor("#1e293b")

    L1, B1 = r["L1"], r["B1"]
    L2, B2 = r["L2"], r["B2"]
    xc1, xc2 = r["xc1"], r["xc2"]
    S = float(d["S"])
    ec, sb_m = float(d["edge_clearance"]), r["sb_m"]
    a1_m, b1_m = r["a1_m"], r["b1_m"]
    a2_m, b2_m = r["a2_m"], r["b2_m"]
    f2x = xc2 - L2 / 2.0
    P1u, P2u = r["P1u"], r["P2u"]
    Ru1, wu1 = r["Ru1"], r["wu1"]
    x0 = r.get("x0", min(L1, max(xc1, P1u / wu1 if wu1 > 0 else xc1)))
    Mu_max = abs(r.get("Mu_max_strap", P1u * (x0 - xc1) - wu1 * (x0 ** 2) / 2.0))
    Mu_col1 = abs(r.get("Mu_col1", wu1 * (xc1 ** 2) / 2.0))
    Mu_L1 = abs(r.get("Mu_f1_edge", P1u * (L1 - xc1) - wu1 * (L1 ** 2) / 2.0))

    # --- 1. Strap Beam BMD ---
    # In RC drawings, negative / hogging moments are drawn UPWARD (tension at top)
    xs = np.linspace(0, xc2, 300)
    ms = []
    for x in xs:
        if x <= xc1:
            m = wu1 * (x ** 2) / 2.0
        elif x <= L1:
            m = P1u * (x - xc1) - wu1 * (x ** 2) / 2.0
        else:
            m = Mu_L1 * (xc2 - x) / max(0.01, (xc2 - L1))
        ms.append(m)
    ms = np.array(ms)

    ax_strap.plot(xs, ms, color="#f43f5e", lw=2.6, label="عزم الانحناء السالب Mu (ton·m)")
    ax_strap.fill_between(xs, 0, ms, color="#f43f5e", alpha=0.22)
    ax_strap.axhline(0, color="#94a3b8", lw=1.2, ls="--")

    # Mark Footing regions & Columns
    ax_strap.axvspan(0, L1, color="#1d4ed8", alpha=0.15, label="قاعدة الجار (Footing 1)")
    ax_strap.axvspan(f2x, f2x + L2, color="#1d4ed8", alpha=0.12, label="القاعدة الداخلية (Footing 2)")
    ax_strap.axvspan(ec, ec + a1_m, color="#334155", alpha=0.55)
    ax_strap.axvspan(xc2 - a2_m / 2, xc2 + a2_m / 2, color="#334155", alpha=0.55)

    # Vertical reference lines for critical sections
    ax_strap.plot([xc1, xc1], [0, Mu_col1], color="#facc15", ls=":", lw=1.2)
    ax_strap.plot([x0, x0], [0, Mu_max], color="#38bdf8", ls="--", lw=1.6)
    ax_strap.plot([L1, L1], [0, Mu_L1], color="#a78bfa", ls=":", lw=1.2)

    # Markers
    ax_strap.plot([x0], [Mu_max], "o", color="#38bdf8", markersize=7, zorder=6)
    ax_strap.plot([xc1], [Mu_col1], "s", color="#facc15", markersize=5.5, zorder=6)
    ax_strap.plot([L1], [Mu_L1], "^", color="#a78bfa", markersize=6, zorder=6)
    ax_strap.plot([xc2], [0], "d", color="#4ade80", markersize=6, zorder=6)

    # Value Callouts
    y_max_plot = max(Mu_max * 1.35, 10.0)
    ax_strap.annotate(
        f"أقصى عزم سالب (Zero Shear):\nMu,max = {Mu_max:.2f} t.m\nعند x0 = {x0:.2f} m",
        xy=(x0, Mu_max), xytext=(x0 + 0.35, Mu_max * 1.05),
        arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.5),
        color="#e0f2fe", fontsize=8.5, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.25", fc="#0f172a", ec="#38bdf8", lw=1.3)
    )

    ax_strap.annotate(
        f"عند وش F1 الداخلي:\nMu = {Mu_L1:.2f} t.m\n(x = {L1:.2f} m)",
        xy=(L1, Mu_L1), xytext=(min(xc2 - 0.5, L1 + 0.45), Mu_L1 * 0.90),
        arrowprops=dict(arrowstyle="->", color="#a78bfa", lw=1.3),
        color="#f3e8ff", fontsize=8, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.22", fc="#0f172a", ec="#a78bfa", lw=1.1)
    )

    ax_strap.annotate(
        f"محور عمود الجار C1:\nMu = {Mu_col1:.2f} t.m",
        xy=(xc1, Mu_col1), xytext=(xc1 + 0.15, max(1.0, Mu_col1 * 1.35)),
        arrowprops=dict(arrowstyle="->", color="#facc15", lw=1.2),
        color="#fef08a", fontsize=8, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.2", fc="#0f172a", ec="#facc15", lw=1.0)
    )

    ax_strap.annotate(
        f"محور C2 (عزم = صفر):\nMu = 0.00 t.m",
        xy=(xc2, 0), xytext=(xc2 - 0.85, y_max_plot * 0.25),
        arrowprops=dict(arrowstyle="->", color="#4ade80", lw=1.3),
        color="#bbf7d0", fontsize=8, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.22", fc="#0f172a", ec="#4ade80", lw=1.1)
    )

    ax_strap.set_title("مخطط عزم الانحناء لكمرة الشداد — Strap Beam Bending Moment Diagram (BMD)", color="#38bdf8", fontsize=11, fontweight="bold", pad=12)
    ax_strap.set_xlabel("المسافة من حد الجار x (m)", color="#94a3b8", fontsize=8.5)
    ax_strap.set_ylabel("العزم السالب Mu (ton·m)\n[الشد بالألياف العلوية]", color="#94a3b8", fontsize=8.5)
    ax_strap.set_xlim(-0.25, xc2 + 0.45)
    ax_strap.set_ylim(-y_max_plot * 0.08, y_max_plot)
    ax_strap.grid(True, color="#334155", ls=":", alpha=0.5)
    ax_strap.legend(loc="upper right", facecolor="#0f172a", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=8)

    # --- 2. Footing 1 Transverse Cantilever BMD ---
    c1 = r["cantilever_f1"]
    qu1 = r["qu1_tm2"]
    Mu_t1 = r.get("Mu_trans1", qu1 * (c1 ** 2) / 2.0)
    y_f1_pts = np.linspace(0, c1, 100)
    m_f1_pts = qu1 * (y_f1_pts ** 2) / 2.0

    ax_f1.plot(y_f1_pts, m_f1_pts, color="#38bdf8", lw=2.2)
    ax_f1.fill_between(y_f1_pts, 0, m_f1_pts, color="#38bdf8", alpha=0.25)
    ax_f1.plot([c1], [Mu_t1], "o", color="#38bdf8", markersize=6)
    ax_f1.annotate(
        f"Mu,trans1 = {Mu_t1:.2f} t.m/m\n(عند وش الشداد)",
        xy=(c1, Mu_t1), xytext=(c1 * 0.35, Mu_t1 * 0.75),
        arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.2),
        color="#bae6fd", fontsize=8, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.2", fc="#0f172a", ec="#38bdf8", lw=1.0)
    )
    ax_f1.set_title(f"عزم رفرفة قاعدة الجار F1 (عرضي):\nالرفرفة = {c1:.2f} m | qu1 = {qu1:.1f} t/m²", color="#e2e8f0", fontsize=9.5, fontweight="bold")
    ax_f1.set_xlabel("البعد من الحافة الحرة y (m)", color="#94a3b8", fontsize=8)
    ax_f1.set_ylabel("العزم Mu (ton·m/m)\n[الشد بالألياف السفلية]", color="#94a3b8", fontsize=8)
    ax_f1.set_xlim(-0.05, c1 + 0.10)
    ax_f1.set_ylim(-0.1, max(1.0, Mu_t1 * 1.30))
    ax_f1.grid(True, color="#334155", ls=":", alpha=0.5)

    # --- 3. Footing 2 Transverse Cantilever BMD ---
    c2 = r["cantilever_f2"]
    qu2 = r["qu2_tm2"]
    Mu_t2 = r.get("Mu_trans2", qu2 * (c2 ** 2) / 2.0)
    y_f2_pts = np.linspace(0, c2, 100)
    m_f2_pts = qu2 * (y_f2_pts ** 2) / 2.0

    ax_f2.plot(y_f2_pts, m_f2_pts, color="#4ade80", lw=2.2)
    ax_f2.fill_between(y_f2_pts, 0, m_f2_pts, color="#4ade80", alpha=0.25)
    ax_f2.plot([c2], [Mu_t2], "o", color="#4ade80", markersize=6)
    ax_f2.annotate(
        f"Mu,trans2 = {Mu_t2:.2f} t.m/m\n(عند وش الشداد)",
        xy=(c2, Mu_t2), xytext=(c2 * 0.35, Mu_t2 * 0.75),
        arrowprops=dict(arrowstyle="->", color="#4ade80", lw=1.2),
        color="#bbf7d0", fontsize=8, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.2", fc="#0f172a", ec="#4ade80", lw=1.0)
    )
    ax_f2.set_title(f"عزم رفرفة القاعدة الداخلية F2 (عرضي):\nالرفرفة = {c2:.2f} m | qu2 = {qu2:.1f} t/m²", color="#e2e8f0", fontsize=9.5, fontweight="bold")
    ax_f2.set_xlabel("البعد من الحافة الحرة y (m)", color="#94a3b8", fontsize=8)
    ax_f2.set_ylabel("العزم Mu (ton·m/m)\n[الشد بالألياف السفلية]", color="#94a3b8", fontsize=8)
    ax_f2.set_xlim(-0.05, c2 + 0.10)
    ax_f2.set_ylim(-0.1, max(1.0, Mu_t2 * 1.30))
    ax_f2.grid(True, color="#334155", ls=":", alpha=0.5)

    return fig


# ── Main Render (called from app.py) ─────────────────────────────────────────
def render_strap_footing_module():
    _init_state()
    d = st.session_state["module_9_data"]

    st.markdown(
        """
        <style>
        /* ── Module 9 Inputs Typography (75% Compact Scale) ── */
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
            font-size: 13px !important;
            font-weight: 700 !important;
            line-height: 1.15 !important;
            margin-bottom: 1px !important;
            padding-bottom: 0px !important;
            color: #facc15 !important; /* عناوين المدخلات باللون الأصفر */
            letter-spacing: 0.1px !important;
            white-space: nowrap !important;
        }

        /* Input boxes (number inputs, selectboxes) — 75% Compact Scale */
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] input,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] input[type="number"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="input"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="input"] input,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stNumberInput input,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="select"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="select"] *,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stSelectbox [data-baseweb="select"] *,
        div[data-testid="stExpander"] input,
        div[data-testid="stExpander"] div[data-baseweb="input"],
        div[data-testid="stExpander"] div[data-baseweb="input"] input,
        div[data-testid="stExpander"] div[data-baseweb="select"],
        div[data-testid="stExpander"] div[data-baseweb="select"] * {
            font-size: 13px !important;
            min-height: 28px !important;
            height: 28px !important;
            line-height: 28px !important;
        }

        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="input"] > div,
        div[data-testid="stExpander"] div[data-baseweb="input"] > div {
            min-height: 28px !important;
            height: 28px !important;
            padding: 0 6px !important;
        }

        /* Number input +/- step buttons */
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-testid="stNumberInput"] button,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] button[data-testid="stNumberInputStepUp"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] button[data-testid="stNumberInputStepDown"],
        div[data-testid="stExpander"] div[data-testid="stNumberInput"] button,
        div[data-testid="stNumberInput"] button {
            min-height: 14px !important;
            height: 14px !important;
            width: 20px !important;
            padding: 0px !important;
        }

        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-testid="stNumberInput"] button svg,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] button[data-testid="stNumberInputStepUp"] svg,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] button[data-testid="stNumberInputStepDown"] svg,
        div[data-testid="stExpander"] div[data-testid="stNumberInput"] button svg,
        div[data-testid="stNumberInput"] button svg {
            width: 10px !important;
            height: 10px !important;
        }

        /* Selectbox dropdown arrow icon */
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="select"] svg,
        div[data-testid="stExpander"] div[data-baseweb="select"] svg {
            width: 12px !important;
            height: 12px !important;
        }

        /* Subtle focus highlight with yellow accent */
        div[data-testid="stExpander"] div[data-baseweb="input"]:focus-within {
            border-color: #facc15 !important;
            box-shadow: 0 0 0 1px #facc15 !important;
        }

        /* Tight vertical spacing between lines/widgets */
        div[data-testid="stExpander"] div[data-testid="stVerticalBlock"] {
            gap: 0.15rem !important;
        }
        div[data-testid="stExpander"] div[data-testid="column"] {
            padding: 0 4px !important;
        }
        div[data-testid="stExpander"] details {
            padding: 5px 10px !important;
            margin-bottom: 5px !important;
            border-radius: 8px !important;
        }
        div[data-testid="stExpander"] summary {
            font-size: 12.5px !important;
            font-weight: 700 !important;
            padding: 3px 8px !important;
        }

        /* ── Clean Outlined White Line Borders (برواز خط أبيض أنيق بدون خلفية بطاقة) ── */
        div[data-testid="stExpander"] div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stExpander"] div[data-testid="stVerticalBlockBorderWrapper"] > div {
            border: 1.5px solid rgba(255, 255, 255, 0.55) !important;
            border-radius: 8px !important;
            background: transparent !important;
            background-color: transparent !important;
            padding: 8px 10px !important;
            margin-bottom: 4px !important;
            box-shadow: none !important;
        }

        div[data-testid="stExpander"] div[data-testid="stVerticalBlockBorderWrapper"]:hover,
        div[data-testid="stExpander"] div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
            border-color: #ffffff !important;
        }

        /* Section headers (Geometry, Loads, Soil, Footings) — 70% scaled */
        .m9-hdr {
            font-size: 17px !important;
            font-weight: 800 !important;
            color: #60a5fa !important;
            margin: 6px 0 4px 0 !important;
            padding-bottom: 3px !important;
            border-bottom: 1.5px solid rgba(96, 165, 250, 0.35) !important;
            line-height: 1.3 !important;
            display: block !important;
        }
        /* Subheaders (Column 1, Column 2, Strap Beam) */
        .m9-subhdr {
            font-size: 15px !important;
            font-weight: 700 !important;
            color: #f8fafc !important;
            background: rgba(51, 65, 85, 0.55) !important;
            border-right: 3px solid #38bdf8 !important;
            padding: 3px 8px !important;
            margin: 6px 0 4px 0 !important;
            border-radius: 4px !important;
            line-height: 1.3 !important;
            display: block !important;
        }
        .m9-auto-badge {
            font-size: 14px !important;
            font-weight: 700 !important;
            color: #38bdf8 !important;
            background: rgba(15, 23, 42, 0.75) !important;
            border: 1px solid rgba(56, 189, 248, 0.45) !important;
            border-radius: 6px !important;
            padding: 4px 8px !important;
            margin: 4px 0 6px 0 !important;
            line-height: 1.35 !important;
            display: block !important;
            text-align: center !important;
            direction: ltr !important;
            word-break: break-word !important;
            overflow-wrap: break-word !important;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2) !important;
        }

        hr {
            margin: 5px 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h2 style='color:#60a5fa; margin-bottom:2px;'>🔗 Module 9 — Strap Footing Design (ECP 203)</h2>"
        "<p style='color:#94a3b8; font-size:12px; margin-top:0;'>تصميم قاعدة الجار والشداد — الكود المصري للخرسانة المسلحة (الوحدات: ton · kg · cm · m · kg/cm² · ton·m)</p>",
        unsafe_allow_html=True,
    )

    # ── 1. Inputs (Design Inputs) ─────────────────────────────────────────────
    with st.expander("📐 Design Inputs (المدخلات التصميمية)", expanded=True):
        c_geo, c_load, c_mat = st.columns([1.4, 0.8, 0.8])

        with c_geo:
            with st.container(border=True):
                st.markdown("<div class='m9-hdr'>📐 الأبعاد الهندسية والأعمدة — Geometry</div>", unsafe_allow_html=True)
                d["S"] = st.number_input(
                    "S — المسافة المحورية بين الأعمدة (m)",
                    value=float(d["S"]), min_value=1.0, max_value=25.0, step=0.25, key="m9_S",
                )
                d["edge_clearance"] = st.number_input(
                    "edge_clearance — المسافة لحد الجار (m)",
                    value=float(d["edge_clearance"]), min_value=0.0, max_value=5.0, step=0.05,
                    help="0.00 = ملاصق لحد الجار (flush)", key="m9_ec",
                )
                st.markdown("<div class='m9-subhdr'>🔹 عمود الجار — Column 1 (Edge)</div>", unsafe_allow_html=True)
                ca, cb = st.columns(2)
                with ca:
                    d["a1"] = st.number_input("a1 موازي للشداد (cm)", value=float(d["a1"]),
                                              min_value=15.0, max_value=300.0, step=5.0, key="m9_a1")
                with cb:
                    d["b1"] = st.number_input("b1 عمودي على الشداد (cm)", value=float(d["b1"]),
                                              min_value=15.0, max_value=300.0, step=5.0, key="m9_b1")
                st.markdown("<div class='m9-subhdr'>🔹 العمود الداخلي — Column 2 (Interior)</div>", unsafe_allow_html=True)
                ca2, cb2 = st.columns(2)
                with ca2:
                    d["a2"] = st.number_input("a2 موازي للشداد (cm)", value=float(d["a2"]),
                                              min_value=15.0, max_value=300.0, step=5.0, key="m9_a2")
                with cb2:
                    d["b2"] = st.number_input("b2 عمودي على الشداد (cm)", value=float(d["b2"]),
                                              min_value=15.0, max_value=300.0, step=5.0, key="m9_b2")

        with c_load:
            with st.container(border=True):
                st.markdown("<div class='m9-hdr'>⚖️ الأحمال — Loads (ton)</div>", unsafe_allow_html=True)
                st.markdown("<div class='m9-subhdr'>🔹 عمود الجار — Column 1 (Edge)</div>", unsafe_allow_html=True)
                d["P1_u"] = st.number_input(
                    "Pu1 أقصى (ton) — الحمل الأقصى",
                    value=float(d.get("P1_u", 120.0)),
                    min_value=1.0, max_value=4500.0, step=5.0, key="m9_P1u",
                    help="الحمل الأقصى المستخرج مباشرة من مخرجات Module 1 أو برامج التحليل (Ultimate)",
                )

                st.markdown("<div class='m9-subhdr'>🔹 العمود الداخلي — Column 2 (Interior)</div>", unsafe_allow_html=True)
                d["P2_u"] = st.number_input(
                    "Pu2 أقصى (ton) — الحمل الأقصى",
                    value=float(d.get("P2_u", 180.0)),
                    min_value=1.0, max_value=4500.0, step=5.0, key="m9_P2u",
                    help="الحمل الأقصى المستخرج مباشرة من مخرجات Module 1 أو برامج التحليل (Ultimate)",
                )

                st.markdown("<div class='m9-subhdr'>🔹 وزن الأعمدة — Columns Weight</div>", unsafe_allow_html=True)
                d["col_weight_factor"] = st.number_input(
                    "Columns Own Weight Factor",
                    value=float(d.get("col_weight_factor", 1.00)),
                    min_value=1.00, max_value=1.50, step=0.01, format="%.2f", key="m9_col_factor",
                    help="1.00 = متضمن في أحمال Module 1 تلقائياً | 1.05~1.10 = إضافة نسبة لوزن الأعمدة",
                )

                # Auto-calculate working loads in session state for consistency
                d["P1_w"] = round((float(d["P1_u"]) * float(d["col_weight_factor"])) / 1.5, 2)
                d["P2_w"] = round((float(d["P2_u"]) * float(d["col_weight_factor"])) / 1.5, 2)

        with c_mat:
            with st.container(border=True):
                st.markdown("<div class='m9-hdr'>🧪 التربة والمواد — Soil & Materials</div>", unsafe_allow_html=True)
                d["q_all_net"] = st.number_input(
                    "q_all,net — إجهاد التربة (kg/cm²)",
                    value=float(d["q_all_net"]), min_value=0.5, max_value=10.0, step=0.10, key="m9_q",
                    help="1.50 kg/cm² = 15.0 ton/m²",
                )
                cm_m1, cm_m2 = st.columns(2)
                with cm_m1:
                    d["fcu"] = st.number_input("Fcu (kg/cm²)", value=float(d["fcu"]),
                                                min_value=150.0, max_value=600.0, step=25.0, key="m9_fcu")
                with cm_m2:
                    d["fy"] = st.number_input("Fy (kg/cm²)", value=float(d["fy"]),
                                               min_value=2000.0, max_value=6000.0, step=200.0, key="m9_fy")
                d["t_pc"] = st.number_input(
                    "t_pc — سماكة العادية (cm)",
                    value=float(d["t_pc"]), min_value=0.0, max_value=100.0, step=5.0, key="m9_tpc",
                )
                st.markdown("<div class='m9-subhdr'>🔹 كمرة الشداد — Strap Beam</div>", unsafe_allow_html=True)
                d["strap_b"] = st.number_input(
                    "B_strap العرض (cm)",
                    value=float(d["strap_b"]), min_value=20.0, max_value=200.0, step=5.0, key="m9_sb",
                    help="عرض كمرة الشداد — العمق D_strap يحسبه البرنامج تلقائياً بالأسفل",
                )

        # ── Explanation Note for Solution (B) ──
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.85); border: 1.5px solid rgba(56, 189, 248, 0.45); border-radius: 8px; padding: 12px 18px; margin-top: 10px; font-size: 22px !important; line-height: 1.65 !important; color: #f1f5f9; direction: rtl; text-align: right; box-shadow: 0 2px 8px rgba(0,0,0,0.25);">
                <div style="font-size: 24px !important; font-weight: 800; color: #38bdf8; margin-bottom: 6px;">💡 طريقة حساب وتوزيع الأحمال:</div>
                <div style="font-size: 22px !important; line-height: 1.65 !important; color: #e2e8f0;">
                    • الأحمال المدخلة هي <b>الأحمال القصوى (Pu1 & Pu2)</b> مباشرة كما تظهر في مخرجات <b>Module 1 (Flat Slab)</b> أو برامج التحليل الإنشائي.<br/>
                    • <b>وزن الأعمدة (Columns Own Weight Factor):</b> قيمته الافتراضية <b>1.00</b> (لأن أحمال Module 1 تتضمن وزن العمود مسبقاً)، ويمكن تعديله إذا رغبت بإضافة نسبة لوزن الأعمدة.<br/>
                    • <b>الأحمال التشغيلية (Working Loads):</b> يحسبها البرنامج تلقائياً في الخلفية بقسمة الحمل الأقصى على 1.5 <span style="color: #facc15; font-family: monospace; font-weight: 800;">(P_working = Pu / 1.5)</span> لتحديد مساحات وأبعاد القواعد وفق إجهاد التربة المسموح بالكود المصري ECP 203.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Recommended dimensions calculation based on inputs ───────────────────
    rec = _calc_recommended_dimensions(d)
    _upstream_sig = f"{d.get('S')}_{d.get('edge_clearance')}_{d.get('a1')}_{d.get('b1')}_{d.get('a2')}_{d.get('b2')}_{d.get('P1_u')}_{d.get('P2_u')}_{d.get('col_weight_factor')}_{d.get('q_all_net')}_{d.get('strap_b')}"

    # Handle reset action before widgets are instantiated to prevent StreamlitAPIException
    if st.session_state.get("_m9_action") == "reset":
        st.session_state["_m9_action"] = None
        d["L1"] = rec["L1"]
        d["B1"] = rec["B1"]
        d["t1"] = rec["t1"]
        d["L2"] = rec["L2"]
        d["B2"] = rec["B2"]
        d["t2"] = rec["t2"]
        d["strap_D"] = rec["strap_D"]
        for wk, k in [
            ("m9_L1", "L1"), ("m9_B1", "B1"), ("m9_t1", "t1"),
            ("m9_L2", "L2"), ("m9_B2", "B2"), ("m9_t2", "t2"),
            ("m9_sD", "strap_D"),
        ]:
            st.session_state[wk] = rec[k]

    # Auto-populate if first run or upstream design inputs modified
    if d.get("_last_upstream_sig") != _upstream_sig:
        d["_last_upstream_sig"] = _upstream_sig
        d["L1"] = rec["L1"]
        d["B1"] = rec["B1"]
        d["t1"] = rec["t1"]
        d["L2"] = rec["L2"]
        d["B2"] = rec["B2"]
        d["t2"] = rec["t2"]
        d["strap_D"] = rec["strap_D"]
        clamps = [
            ("m9_L1", 0.50, 20.0, rec["L1"]),
            ("m9_B1", 0.50, 20.0, rec["B1"]),
            ("m9_t1", 20.0, 250.0, rec["t1"]),
            ("m9_L2", 0.50, 20.0, rec["L2"]),
            ("m9_B2", 0.50, 20.0, rec["B2"]),
            ("m9_t2", 20.0, 250.0, rec["t2"]),
            ("m9_sD", 40.0, 300.0, rec["strap_D"]),
        ]
        for wk, c_min, c_max, val in clamps:
            if wk in st.session_state:
                st.session_state[wk] = max(c_min, min(c_max, float(val)))

    # ── 2. Executive Design Dimensions & Controls ──────────────────────────────
    with st.expander("📐 Design Dimensions & Overrides (نواتج التصميم والأبعاد التنفيذية)", expanded=True):
        st.caption("💡 نواتج التصميم الهندسية تظهر مباشرة في خانات الإدخال أدناه، ويمكنك تعديل أي قيمة وسيقوم البرنامج بإعادة الحساب والرسم فوراً.")
        col_footings, col_strap = st.columns([1.9, 1.1])

        with col_footings:
            with st.container(border=True):
                st.markdown("<div class='m9-hdr'>🟦 أبعاد وتسليح القواعد — Footings Design (F1 & F2)</div>", unsafe_allow_html=True)
                f1_col, f2_col = st.columns(2)

                with f1_col:
                    st.markdown("<div class='m9-subhdr'>🔹 Footing 1 (قاعدة الجار)</div>", unsafe_allow_html=True)
                    v_l1 = max(0.50, min(20.0, float(d.get("L1", rec["L1"]))))
                    d["L1"] = st.number_input(
                        "L1 — طول قاعدة الجار (m)",
                        value=v_l1, min_value=0.50, max_value=20.0, step=0.05, key="m9_L1",
                        help="البعد في اتجاه الشداد (محسوب لتأمين اللامركزية وإجهاد التربة)",
                    )
                    v_b1 = max(0.50, min(20.0, float(d.get("B1", rec["B1"]))))
                    d["B1"] = st.number_input(
                        "B1 — عرض قاعدة الجار (m)",
                        value=v_b1, min_value=0.50, max_value=20.0, step=0.05, key="m9_B1",
                        help="البعد في الاتجاه العمودي على الشداد",
                    )
                    v_t1 = max(20.0, min(250.0, float(d.get("t1", rec["t1"]))))
                    d["t1"] = st.number_input(
                        "t1 — عمق / سماكة القاعدة (cm)",
                        value=v_t1, min_value=20.0, max_value=250.0, step=5.0, key="m9_t1",
                    )
                    d["L1_override"] = d["L1"]
                    d["L1_ov"] = d["L1"]
                    d["B1_ov"] = d["B1"]
                    d["t1_ov"] = d["t1"]

                with f2_col:
                    st.markdown("<div class='m9-subhdr'>🔹 Footing 2 (القاعدة الداخلية)</div>", unsafe_allow_html=True)
                    v_l2 = max(0.50, min(20.0, float(d.get("L2", rec["L2"]))))
                    d["L2"] = st.number_input(
                        "L2 — طول القاعدة الداخلية (m)",
                        value=v_l2, min_value=0.50, max_value=20.0, step=0.05, key="m9_L2",
                        help="البعد في اتجاه الشداد",
                    )
                    v_b2 = max(0.50, min(20.0, float(d.get("B2", rec["B2"]))))
                    d["B2"] = st.number_input(
                        "B2 — عرض القاعدة الداخلية (m)",
                        value=v_b2, min_value=0.50, max_value=20.0, step=0.05, key="m9_B2",
                        help="البعد في الاتجاه العمودي على الشداد",
                    )
                    v_t2 = max(20.0, min(250.0, float(d.get("t2", rec["t2"]))))
                    d["t2"] = st.number_input(
                        "t2 — عمق / سماكة القاعدة (cm)",
                        value=v_t2, min_value=20.0, max_value=250.0, step=5.0, key="m9_t2",
                    )
                    d["L2_ov"] = d["L2"]
                    d["B2_ov"] = d["B2"]
                    d["t2_ov"] = d["t2"]

                # ── اسفل البانيل الخاص بالقواعد: حديد عرضي القواعد ──
                st.markdown("<hr style='margin: 6px 0 8px 0; border-color: rgba(96, 165, 250, 0.25);'>", unsafe_allow_html=True)
                cr1, cr2 = st.columns([1.0, 1.0])
                with cr1:
                    _td_opts = [12, 14, 16, 18, 20, 22]
                    d["trans_bar_dia"] = st.selectbox(
                        "حديد عرضي القواعد",
                        options=_td_opts,
                        index=_td_opts.index(d["trans_bar_dia"]) if d["trans_bar_dia"] in _td_opts else 2,
                        key="m9_tdia",
                        help="قطر أسياخ حديد التسليح العرضي الرئيسي لقاعدتي الجار والداخلية (mm)",
                    )
                with cr2:
                    st.markdown(
                        "<div style='font-size: 13.5px; color: #94a3b8; padding-top: 24px; font-weight: 600;'>💡 التسليح العرضي الرئيسي لمقاومة عزم الرفرفة لكلا القاعدتين (F1 & F2)</div>",
                        unsafe_allow_html=True,
                    )

        with col_strap:
            with st.container(border=True):
                st.markdown("<div class='m9-hdr'>🟩 كمرة الشداد والتسليح — Strap Beam & Rebar</div>", unsafe_allow_html=True)
                v_sd = max(40.0, min(300.0, float(d.get("strap_D", rec["strap_D"]))))
                d["strap_D"] = st.number_input(
                    "D_strap — عمق الشداد المحسوب (cm)",
                    value=v_sd, min_value=40.0, max_value=300.0, step=5.0, key="m9_sD",
                    help="عمق الشداد المحسوب تلقائياً لتلبية متطلبات العزم والقص والترخيم، ويمكنك تعديله",
                )
                sb_r1, sb_r2 = st.columns(2)
                with sb_r1:
                    _ld_opts = [16, 18, 20, 22, 25, 28, 32]
                    d["long_bar_dia"] = st.selectbox(
                        "قطر حديد طولي شدادات mm",
                        options=_ld_opts,
                        index=_ld_opts.index(d["long_bar_dia"]) if d["long_bar_dia"] in _ld_opts else 3,
                        key="m9_ldia",
                        help="قطر أسياخ الحديد الطولي الرئيسي لكمرة الشداد (علوي وسفلي)",
                    )
                with sb_r2:
                    _st_opts = [8, 10, 12, 14, 16]
                    d["stirrup_dia"] = st.selectbox(
                        "قطر الكانات (mm)",
                        options=_st_opts,
                        index=_st_opts.index(d["stirrup_dia"]) if d["stirrup_dia"] in _st_opts else 1,
                        key="m9_sdia",
                    )
                sb_r3, sb_r4 = st.columns(2)
                with sb_r3:
                    cur_spm = int(d.get("stirrup_per_m", round(100.0 / float(d.get("stirrup_spacing", 20.0)))))
                    cur_spm = max(4, min(12, cur_spm))
                    d["stirrup_per_m"] = st.number_input(
                        "عدد الكانات في المتر (كانات/م)",
                        value=cur_spm,
                        min_value=4,
                        max_value=12,
                        step=1,
                        key="m9_s_per_m",
                        help="العدد المعتاد للكانات في المتر الطولي للكمرة (5 إلى 10 كانات/م)",
                    )
                    d["stirrup_spacing"] = round(100.0 / float(d["stirrup_per_m"]), 2)
                with sb_r4:
                    st.markdown(
                        f"<div style='font-size: 13.5px; color: #94a3b8; padding-top: 24px; font-weight: 700;'>التباعد: <span style='color: #38bdf8; font-family: monospace; font-size: 15px;'>@ {d['stirrup_spacing']:.1f} cm</span></div>",
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 إعادة تعيين الأبعاد للقيم التصميمية المحسوبة تلقائياً (Reset to Auto-Design)", key="m9_btn_reset_dims"):
            st.session_state["_m9_action"] = "reset"
            st.rerun()

    r = _calculate(d)
    ok1 = r["q_act1"] <= float(d["q_all_net"])
    ok2 = r["q_act2"] <= float(d["q_all_net"])
    shear_ok = r["stirrups_shear_ok"]

    # ── 4. Dynamic Plan View (Immediately after Inputs & Overrides) ───────────
    st.divider()
    with st.expander("🗺️ Dynamic Plan View (المسقط الأفقي الديناميكي)", expanded=False, key="m9_plan_exp", on_change="rerun"):
        if st.session_state.get("m9_plan_exp", False):
            st.caption("يتحدث المسقط الأفقي تلقائياً ولحظياً لملاحظة تأثير التعديلات في الأبعاد والأحمال.")
            fig = _draw_plan(d, r)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.info("💡 انقر لتوسيع هذا القسم وتوليد المسقط الأفقي الديناميكي للشداد والقواعد (Lazy Loading).")

    # ── 5. Soil Stress Verification Result ───────────────────────────────────
    ok1 = r["q_act1"] <= float(d["q_all_net"])
    ok2 = r["q_act2"] <= float(d["q_all_net"])

    if ok1 and ok2:
        st.success(
            f"✅ **نتائج فحص إجهادات التربة (Soil Bearing Capacity — Safe):** "
            f"إجهاد التلامس الفعلي لقاعدة الجار F1 = {r['q_act1']:.2f} kg/cm²، "
            f"وللقاعدة الداخلية F2 = {r['q_act2']:.2f} kg/cm²، "
            f"وكلاهما أقل من إجهاد التأسيس الصافي المسموح به ({float(d['q_all_net']):.2f} kg/cm²)."
        )
    else:
        st.warning(
            f"⚠️ **نتائج فحص إجهادات التربة (Soil Bearing Capacity — Exceeded):** "
            f"تم تجاوز إجهاد التربة المسموح به ({float(d['q_all_net']):.2f} kg/cm²)! "
            f"قاعدة الجار: {r['q_act1']:.2f} kg/cm² | القاعدة الداخلية: {r['q_act2']:.2f} kg/cm²."
        )

    # ── 6. Unified Design, Dimensions, Reinforcement & Checks Summary ──────────
    st.divider()
    st.markdown("### 📋 ملخص التصميم والأبعاد والتسليح وفحص الإجهادات — Design & Reinforcement Summary")
    st.caption("ملخص تنفيذي موحد وشامل لنتائج تصميم قاعدة الجار والقاعدة الداخلية وكمرة الشداد، متضمناً فحص إجهادات القص، الأبعاد الخرسانية، وتفاصيل التسليح طبقاً للكود المصري ECP 203.")

    concrete_shear_ok = r["concrete_shear_ok"]
    stirrups_shear_ok = r["stirrups_shear_ok"]
    shear_max_ok = r["shear_max_ok"]
    shear_ok = stirrups_shear_ok

    if concrete_shear_ok:
        shear_status_text = "Safe (خرسانة بمفردها) ✅"
        shear_delta_color = "normal"
    elif stirrups_shear_ok:
        shear_status_text = f"Safe بالكانات ✅ ({r['Asv_prov_cm2_m']:.1f} ≥ {r['Asv_req_cm2_m']:.1f} cm²/m)"
        shear_delta_color = "normal"
    elif not shear_max_ok:
        shear_status_text = "حرج: τ > q_cu,max (كبر القطاع) 🚨"
        shear_delta_color = "inverse"
    else:
        shear_status_text = f"⚠️ كانات غير كافية ({r['Asv_prov_cm2_m']:.1f} < {r['Asv_req_cm2_m']:.1f})"
        shear_delta_color = "inverse"

    n_t1 = _bar_combo_cm2(r["As_trans1_per_m"] * r["L1"], int(d["trans_bar_dia"]))
    n_t2 = _bar_combo_cm2(r["As_trans2_per_m"] * r["L2"], int(d["trans_bar_dia"]))

    # Summary metric cards
    st.markdown("##### 🔩 مؤشرات التسليح وفحص القص الرئيسية:")

    def _metric_box(title, value, subtext, sub_color="#1d4ed8"):
        return f"""
        <div dir="ltr" style="background: #f0f4ff; border: 1px solid #c8d4f0; border-radius: 8px; padding: 10px 14px; box-sizing: border-box; text-align: left; min-height: 112px; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 8px;">
            <div style="color: #475569; font-weight: 600; font-size: 14px; line-height: 1.25; margin-bottom: 4px;">{title}</div>
            <div style="color: #1e3a8a; font-weight: 800; font-size: 22px; font-family: monospace, sans-serif; line-height: 1.2;">{value}</div>
            <div style="color: {sub_color}; font-weight: 800; font-size: 16px; line-height: 1.35; margin-top: 6px;">{subtext}</div>
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
                "كانات الشداد المنفذة (Stirrups)",
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
                "حديد قاعدة الجار العرضي (Footing 1 Transverse)",
                f"{n_t1} Φ {int(d['trans_bar_dia'])} mm",
                f"موزع على كامل الطول L1 = {r['L1']:.2f} m ({r['As_trans1_per_m']:.1f} cm²/m)",
                "#1d4ed8",
            ),
            unsafe_allow_html=True,
        )
    with tf2:
        st.markdown(
            _metric_box(
                "حديد القاعدة الداخلية العرضي (Footing 2 Transverse)",
                f"{n_t2} Φ {int(d['trans_bar_dia'])} mm",
                f"موزع على كامل الطول L2 = {r['L2']:.2f} m ({r['As_trans2_per_m']:.1f} cm²/m)",
                "#1d4ed8",
            ),
            unsafe_allow_html=True,
        )

    # ── Comprehensive Structural Verifications & Audio Siren Alert ───────────
    failed_checks = []
    if not ok1:
        failed_checks.append({
            "title": "إجهاد التربة أسفل قاعدة الجار (Footing 1) يتجاوز الإجهاد الصافي المسموح به!",
            "actual": f"q_act1 = {r['q_act1']:.2f} kg/cm²",
            "allowed": f"q_all,net = {float(d['q_all_net']):.2f} kg/cm²",
            "action": "يلزم زيادة طول قاعدة الجار L1 أو عرضها B1 لتكبير مساحة الارتكاز وخفض إجهاد التربة للحد الآمن.",
        })
    if not ok2:
        failed_checks.append({
            "title": "إجهاد التربة أسفل القاعدة الداخلية (Footing 2) يتجاوز الإجهاد الصافي المسموح به!",
            "actual": f"q_act2 = {r['q_act2']:.2f} kg/cm²",
            "allowed": f"q_all,net = {float(d['q_all_net']):.2f} kg/cm²",
            "action": "يلزم زيادة طول القاعدة الداخلية L2 أو عرضها B2 لتوزيع ردود الأفعال وخفض إجهاد التربة للحد الآمن.",
        })
    if not shear_max_ok:
        failed_checks.append({
            "title": "تحذير إنشائي حرج: إجهاد القص يتجاوز أقصى إجهاد مسموح به لقطاع الخرسانة (q_cu,max) بالكود المصري!",
            "actual": f"إجهاد القص الفعلي τ = {r['tau_kgcm2']:.2f} kg/cm²",
            "allowed": f"أقصى إجهاد قص مسموح q_cu,max = {r.get('vc_max_kgcm2', 0.0):.2f} kg/cm²",
            "action": "لا تكفي زيادة الكانات وحدها في هذه الحالة! يجب حتماً تكبير أبعاد قطاع الشداد بزيادة عمق الشداد D_strap أو عرضه B_strap لمنع انهيار الخرسانة بالضغط المائل.",
        })
    elif not stirrups_shear_ok:
        failed_checks.append({
            "title": "تحذير إنشائي: الكانات المنفذة غير كافية لمقاومة إجهاد القص الزائد!",
            "actual": f"الكانات المنفذة = {r['Asv_prov_cm2_m']:.2f} cm²/m ({int(r['stirrup_per_m'])} Φ {int(d['stirrup_dia'])} / م - {r['n_branches']} فروع)",
            "allowed": f"الحد الأدنى المطلوب لمقاومة القص = {r['Asv_req_cm2_m']:.2f} cm²/m",
            "action": f"يلزم زيادة قطر الكانات أو زيادة عدد الكانات في المتر لتأمين على الأقل {r['Asv_req_cm2_m']:.2f} cm²/m، أو زيادة عمق الشداد D_strap لخفض إجهاد القص الفعلي.",
        })

    if failed_checks:
        from modules.settings import play_warning_sound
        play_warning_sound()

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
                <div style="font-size: 19px; font-weight: 900; color: #fee2e2; display: flex; align-items: center; gap: 10px;">
                    🚨 تحذير إنشائي عاجل: تم رصد ({len(failed_checks)}) اختبار غير آمن في هذا التصميم!
                </div>
                {alert_items_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Design Summary Table ──────────────────────────────────────────────────
    st.markdown("##### 📊 جدول الأبعاد والتسليح والتحقق الإنشائي (Design & Verification Table):")

    status_badge_f1 = (
        '<span style="background: rgba(34, 197, 94, 0.20); color: #4ade80; border: 1.5px solid #22c55e; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px; display: inline-block;">آمن ✅</span>'
        if ok1 else
        '<span style="background: rgba(245, 158, 11, 0.20); color: #fbbf24; border: 1.5px solid #f59e0b; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px; display: inline-block;">تجاوز الإجهاد ⚠️</span>'
    )
    status_badge_f2 = (
        '<span style="background: rgba(34, 197, 94, 0.20); color: #4ade80; border: 1.5px solid #22c55e; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px; display: inline-block;">آمن ✅</span>'
        if ok2 else
        '<span style="background: rgba(245, 158, 11, 0.20); color: #fbbf24; border: 1.5px solid #f59e0b; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px; display: inline-block;">تجاوز الإجهاد ⚠️</span>'
    )
    if shear_ok:
        status_badge_strap = '<span style="background: rgba(34, 197, 94, 0.20); color: #4ade80; border: 1.5px solid #22c55e; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px; display: inline-block;">آمن ✅</span>'
    elif not shear_max_ok:
        status_badge_strap = '<span style="background: rgba(239, 68, 68, 0.20); color: #f87171; border: 1.5px solid #ef4444; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px; display: inline-block;">حرج τ > q_cu,max 🚨</span>'
    else:
        status_badge_strap = '<span style="background: rgba(245, 158, 11, 0.20); color: #fbbf24; border: 1.5px solid #f59e0b; border-radius: 6px; padding: 4px 10px; font-weight: 900; font-size: 15px; display: inline-block;">كانات غير كافية ⚠️</span>'

    table_html = f"""
    <style>
        .ecp-custom-table-container th span {{
            color: #67e8f9 !important;
        }}
        .ecp-custom-table-container td.row-header span {{
            color: #fb923c !important;
        }}
    </style>
    <div class="ecp-custom-table-container" style="overflow-x: auto; border: 2px solid #38bdf8; border-radius: 12px; box-shadow: 0 6px 25px rgba(0, 0, 0, 0.45); margin: 12px 0 20px 0;">
        <table class="ecp-styled-dark-table" style="width: 100% !important; border-collapse: collapse !important; background: #0b1329 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;">
            <thead>
                <tr style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important; border-bottom: 2.5px solid #38bdf8 !important;">
                    <th style="padding: 13px 16px !important; text-align: right !important; white-space: nowrap !important;"><span style="color: #67e8f9 !important; font-size: 17.5px !important; font-weight: 900 !important;">العنصر الإنشائي (Element)</span></th>
                    <th style="padding: 13px 14px !important; text-align: center !important; white-space: nowrap !important;"><span style="color: #67e8f9 !important; font-size: 17.5px !important; font-weight: 900 !important;">الطول L (m)</span></th>
                    <th style="padding: 13px 14px !important; text-align: center !important; white-space: nowrap !important;"><span style="color: #67e8f9 !important; font-size: 17.5px !important; font-weight: 900 !important;">العرض B</span></th>
                    <th style="padding: 13px 14px !important; text-align: center !important; white-space: nowrap !important;"><span style="color: #67e8f9 !important; font-size: 17.5px !important; font-weight: 900 !important;">السماكة / العمق (cm)</span></th>
                    <th style="padding: 13px 16px !important; text-align: right !important; white-space: nowrap !important;"><span style="color: #67e8f9 !important; font-size: 17.5px !important; font-weight: 900 !important;">التسليح المعتمد (Reinforcement)</span></th>
                    <th style="padding: 13px 14px !important; text-align: center !important; white-space: nowrap !important;"><span style="color: #67e8f9 !important; font-size: 17.5px !important; font-weight: 900 !important;">إجهاد التشغيل / القص الفعلي</span></th>
                    <th style="padding: 13px 14px !important; text-align: center !important; white-space: nowrap !important;"><span style="color: #67e8f9 !important; font-size: 17.5px !important; font-weight: 900 !important;">الحد المسموح به (Allowable)</span></th>
                    <th style="padding: 13px 14px !important; text-align: center !important; white-space: nowrap !important;"><span style="color: #67e8f9 !important; font-size: 17.5px !important; font-weight: 900 !important;">الحالة الإنشائية (Status)</span></th>
                </tr>
            </thead>
            <tbody>
                <!-- Row 1: Footing 1 -->
                <tr style="background: rgba(15, 23, 42, 0.85) !important; border-bottom: 1.5px solid rgba(148, 163, 184, 0.25) !important;">
                    <td class="row-header" style="padding: 12px 16px !important; text-align: right !important; white-space: nowrap !important;"><span style="color: #fb923c !important; font-size: 18px !important; font-weight: 900 !important;">قاعدة الجار (Footing 1)</span></td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">{r['L1']:.2f} m</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">{r['B1']:.2f} m</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">{r['t1_cm']:.0f} cm</td>
                    <td style="padding: 12px 16px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: right !important; white-space: nowrap !important;">عرضي: {n_t1} Φ {int(d['trans_bar_dia'])} mm | طولي: 5 Φ 12 / م</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #93c5fd !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">q_act = {r['q_act1']:.2f} kg/cm²</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #cbd5e1 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">q_all = {float(d['q_all_net']):.2f} kg/cm²</td>
                    <td style="padding: 12px 14px !important; text-align: center !important; vertical-align: middle !important; white-space: nowrap !important;">{status_badge_f1}</td>
                </tr>
                <!-- Row 2: Footing 2 -->
                <tr style="background: rgba(30, 41, 59, 0.85) !important; border-bottom: 1.5px solid rgba(148, 163, 184, 0.25) !important;">
                    <td class="row-header" style="padding: 12px 16px !important; text-align: right !important; white-space: nowrap !important;"><span style="color: #fb923c !important; font-size: 18px !important; font-weight: 900 !important;">القاعدة الداخلية (Footing 2)</span></td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">{r['L2']:.2f} m</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">{r['B2']:.2f} m</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">{r['t2_cm']:.0f} cm</td>
                    <td style="padding: 12px 16px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: right !important; white-space: nowrap !important;">عرضي: {n_t2} Φ {int(d['trans_bar_dia'])} mm | طولي: 5 Φ 12 / م</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #93c5fd !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">q_act = {r['q_act2']:.2f} kg/cm²</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #cbd5e1 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">q_all = {float(d['q_all_net']):.2f} kg/cm²</td>
                    <td style="padding: 12px 14px !important; text-align: center !important; vertical-align: middle !important; white-space: nowrap !important;">{status_badge_f2}</td>
                </tr>
                <!-- Row 3: Strap Beam -->
                <tr style="background: rgba(15, 23, 42, 0.85) !important;">
                    <td class="row-header" style="padding: 12px 16px !important; text-align: right !important; white-space: nowrap !important;"><span style="color: #fb923c !important; font-size: 18px !important; font-weight: 900 !important;">كمرة الشداد (Strap Beam)</span></td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">{d['S']:.2f} m (محاور S)</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">{d['strap_b']:.0f} cm</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">{r['sD_cm']:.0f} cm</td>
                    <td style="padding: 12px 16px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; text-align: right !important; white-space: nowrap !important;">علوي: {r['n_top']}Φ{int(d['long_bar_dia'])} | سفلي: {r['n_bot']}Φ{int(d['long_bar_dia'])} | كانات: {int(r['stirrup_per_m'])}Φ{int(d['stirrup_dia'])}/م</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #93c5fd !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">τ_act = {r['tau_kgcm2']:.2f} kg/cm²</td>
                    <td style="padding: 12px 14px !important; font-size: 16.5px !important; font-weight: 700 !important; color: #cbd5e1 !important; text-align: center !important; white-space: nowrap !important;" dir="ltr">q_cu = {r['vc_kgcm2']:.2f} kg/cm²</td>
                    <td style="padding: 12px 14px !important; text-align: center !important; vertical-align: middle !important; white-space: nowrap !important;">{status_badge_strap}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    if hasattr(st, "html"):
        st.html(table_html)
    else:
        st.markdown(table_html, unsafe_allow_html=True)

    # ── 7. Structural Detailing & Reinforcement Layout ─────────────────────────
    st.divider()
    st.markdown(
        """### <span style="color: #67e8f9 !important;">🏗️ المخطط الإنشائي وتفاصيل التسليح التنفيذية</span> <span style="color: #94a3b8 !important;">—</span> <span style="color: #fb923c !important;">Structural Detailing & Reinforcement Layout</span>""",
        unsafe_allow_html=True,
    )
    st.caption("لوحة إنشائية تنفيذية متكاملة توضح الأبعاد وتفريد حديد التسليح للقواعد والشداد طبقاً لمواصفات الكود المصري ECP 203.")

    # Tab bar glow styling
    st.markdown(
        """
        <style>
        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] p,
        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] span {
            color: #67e8f9 !important;
            font-weight: 800 !important;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"]:hover p,
        div[data-testid="stTabs"] button[data-baseweb="tab"]:hover span {
            color: #fb923c !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    det_tab1, det_tab2, det_tab3, det_tab4 = st.tabs([
        "🔍 Longitudinal Section (القطاع الطولي وتفريد التسليح)",
        "📐 Plan Detailing (المسقط الأفقي الإنشائي)",
        "📈 Bending Moment Diagram (مخطط العزوم الإنشائية)",
        "📊 Quantity Survey (جدول حصر الكميات والمواد)",
    ])

    with det_tab1:
        st.markdown(
            """#### <span style="color: #67e8f9 !important;">🔍 قطاع طولي تنفيذي في كمرة الشداد والقواعد</span> <span style="color: #94a3b8 !important;">—</span> <span style="color: #fb923c !important;">Longitudinal Detailing Section</span>""",
            unsafe_allow_html=True,
        )
        st.caption("يوضح القطاع: سمك القواعد $t_1, t_2$، وعمق الشداد $D_{strap}$، وتفريد الحديد العلوي والسفلي والكانات وبراندات الانكماش وأشاير الأعمدة والمناسيب.")
        with st.expander("🖼️ Longitudinal Detailing Section (استعراض القطاع الطولي وتفريد التسليح)", expanded=False, key="m9_elev_exp", on_change="rerun"):
            if st.session_state.get("m9_elev_exp", False):
                fig_elev = _draw_detailing_elevation(d, r, n_t1, n_t2)
                st.pyplot(fig_elev, use_container_width=True)
                plt.close(fig_elev)
            else:
                st.info("💡 انقر لتوسيع هذا القسم وتوليد القطاع الطولي التنفيذي وتفريد حديد الشداد والقواعد (Lazy Loading).")

        st.markdown(
            f"""
            <div dir="rtl" style="background: rgba(15, 23, 42, 0.65); border: 1px solid #334155; border-radius: 8px; padding: 16px 22px; margin-top: 8px; font-size: 19px; line-height: 1.85; color: #e2e8f0; text-align: right; direction: rtl;">
                <div style="font-weight: 800; font-size: 21px; margin-bottom: 10px; text-align: right;">
                    <span style="color: #67e8f9 !important;">📌 ملاحظات تنفيذية للقطاع الطولي لكمرة الشداد</span>
                    <span style="color: #fb923c !important;">(ECP 203):</span>
                </div>
                • <b>الحديد العلوي الرئيسي لكمرة الشداد (Strap Beam Top Rebar):</b> هذا الحديد مخصص لكمرة الشداد لمقاومة العزم السالب الناتج عن اللامركزية، ويمتد بكامل طول الشداد وينتهي بأرجل قياسية رأسية (Standard 90° Hooks) بطول تماسك لا يقل عن <code style="font-size: 18px;">55 Φ</code> أو حتى قاع القاعدة.<br/>
                • <b>الحديد السفلي لكمرة الشداد (Bottom Rebar):</b> حديد تعليق سفلي لمقاومة العزوم الموجبة وضمان تماسك القفص الحديدي واستمرار الكانات.<br/>
                • <b>تكثيف الكانات:</b> يتم تكثيف كانات الشداد بمعدل <b>{int(r['stirrup_per_m'])} كانات في المتر بقطر <span dir="ltr">Φ {int(d['stirrup_dia'])} mm</span> ({r['n_branches']} فروع)</b> على مسافة <code style="font-size: 18px;">1.5 d</code> من وش العمود/القاعدة حيث يكون إجهاد القص في أقصاه.<br/>
                • <b>براندات الانكماش:</b> عمق الشداد $D = {r['sD_cm']:.0f}\\text{{ cm}}$ {'يتطلب وضع براندات انكماش جانبية (Side Bars) بقطر 10 مم كل 30 سم لمقاومة شروخ الانكماش.' if r['sD_cm'] >= 60 else 'لا يتطلب براندات انكماش لأن العمق أقل من 60 سم.'}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with det_tab2:
        st.markdown(
            """#### <span style="color: #67e8f9 !important;">📐 المسقط الأفقي الإنشائي وتوزيع التسليح</span> <span style="color: #94a3b8 !important;">—</span> <span style="color: #fb923c !important;">Plan Detailing & Steel Layout</span>""",
            unsafe_allow_html=True,
        )
        st.caption("يوضح المسقط: حدود القواعد والشداد والأعمدة، وتوزيع أسياخ التسليح العرضي للقواعد، وكانات الشداد، وخطوط الأبعاد المحورية والنهائية.")
        with st.expander("🖼️ Plan Detailing & Steel Layout (استعراض المسقط الأفقي الإنشائي وتوزيع التسليح)", expanded=False, key="m9_det_plan_exp", on_change="rerun"):
            if st.session_state.get("m9_det_plan_exp", False):
                fig_det_plan = _draw_detailing_plan(d, r, n_t1, n_t2)
                st.pyplot(fig_det_plan, use_container_width=True)
                plt.close(fig_det_plan)
            else:
                st.info("💡 انقر لتوسيع هذا القسم وتوليد المسقط الأفقي الإنشائي وتوزيع التسليح (Lazy Loading).")

        st.markdown(
            f"""
            <div dir="rtl" style="background: rgba(15, 23, 42, 0.65); border: 1px solid #334155; border-radius: 8px; padding: 16px 22px; margin-top: 8px; font-size: 19px; line-height: 1.85; color: #e2e8f0; text-align: right; direction: rtl;">
                <div style="font-weight: 800; font-size: 21px; margin-bottom: 10px; text-align: right;">
                    <span style="color: #67e8f9 !important;">📌 ملاحظات تنفيذية لتسليح القواعد في الاتجاهين</span>
                    <span style="color: #fb923c !important;">(ECP 203):</span>
                </div>
                • <b>الاتجاه العرضي (العمودي على الشداد — الرئيسي):</b> هذا هو التسليح الإنشائي الأساسي المصمم على عزم الرفرفة الكابولية (Cantilever Moment)، بقيمة <b>{n_t1} أسياخ بقطر <span dir="ltr">Φ {int(d['trans_bar_dia'])} mm</span></b> لقاعدة الجار و <b>{n_t2} أسياخ بقطر <span dir="ltr">Φ {int(d['trans_bar_dia'])} mm</span></b> للقاعدة الداخلية.<br/>
                • <b>الاتجاه الطولي (الموازي للشداد — الثانوي / التوزيع):</b> الشداد هو الذي يحمل كامل العزوم وقوى القص في هذا الاتجاه، لذلك يوضع في بلاطة القواعد خارج الشداد <b>تسليح ثانوي كودي (Distribution Rebar) بمعدل 5 أسياخ في المتر بقطر <span dir="ltr">Φ 12 mm</span></b> (إجمالي <b>{max(4, int(round(r['B1'] * 5.0)))} أسياخ</b> لقاعدة الجار F1، و <b>{max(4, int(round(r['B2'] * 5.0)))} أسياخ</b> للقاعدة الداخلية F2) لتثبيت الشبكة السفلية ومقاومة انكماش الخرسانة.<br/>
                • <b>الحديد العلوي لبلاطة القواعد (Footings Top Mesh):</b> إنشائياً لا توجد عزوم سالبة على بلاطة القواعد لأن رد فعل ضغط التربة للأعلى يسبب شداً سفلياً فقط؛ لكن إذا زادت سماكة القاعدة عن <code style="font-size: 18px;">60 cm</code> (سماكة F1 = {r['t1_cm']:.0f} cm و F2 = {r['t2_cm']:.0f} cm) يوصي الكود بوضع <b>شبكة انكماش علوية خفيفة بمعدل 5 أسياخ في المتر بقطر <span dir="ltr">Φ 10 mm</span> أو <span dir="ltr">Φ 12 mm</span> في الاتجاهين (<span dir="ltr">5 Φ 10 mm/m</span> أو <span dir="ltr">5 Φ 12 mm/m</span>)</b> لمقاومة شروخ الانكماش السطحية الناتجة عن حرارة إماهة الأسمنت.<br/>
                • <b>خط الجار (Property Line):</b> تم الالتزام بمسافة الارتداد المحددة <code style="font-size: 18px;">ec = {float(d['edge_clearance']):.2f} m</code> بدقة هندسية تامة.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with det_tab3:
        st.markdown(
            """#### <span style="color: #67e8f9 !important;">📈 مخطط العزوم الإنشائية وتوزيع القوى</span> <span style="color: #94a3b8 !important;">—</span> <span style="color: #fb923c !important;">Bending Moment Diagram (BMD)</span>""",
            unsafe_allow_html=True,
        )
        st.caption("يوضح المخطط: منحنى عزوم الانحناء التصميمية لكمرة الشداد وقيمة وموقع أقصى عزم سالب عند نقطة انعدام القص (Zero Shear)، بالإضافة إلى عزوم الرفرفة العرضية للقواعد طبقاً للكود المصري ECP 203.")
        with st.expander("🖼️ Bending Moment Diagram (استعراض مخطط العزوم الإنشائية)", expanded=False, key="m9_bmd_exp", on_change="rerun"):
            if st.session_state.get("m9_bmd_exp", False):
                fig_bmd = _draw_bending_moment_diagram(d, r)
                st.pyplot(fig_bmd, use_container_width=True)
                plt.close(fig_bmd)
            else:
                st.info("💡 انقر لتوسيع هذا القسم وتوليد منحنى ومخطط العزوم الإنشائية (BMD).")

        # 4 Summary Metric Columns
        bmd_c1, bmd_c2, bmd_c3, bmd_c4 = st.columns(4)
        with bmd_c1:
            st.metric("أقصى عزم سالب للشداد Mu,max", f"{r.get('Mu_max_strap', abs(r['Mu_neg'])):.2f} t·m")
        with bmd_c2:
            st.metric("موقع Zero Shear (x₀ من الجار)", f"{r.get('x0', 0.0):.2f} m")
        with bmd_c3:
            st.metric("عزم رفرفة قاعدة الجار Mu,trans1", f"{r.get('Mu_trans1', 0.0):.2f} t·m/m")
        with bmd_c4:
            st.metric("عزم رفرفة القاعدة الداخلية Mu,trans2", f"{r.get('Mu_trans2', 0.0):.2f} t·m/m")

        st.markdown(
            f"""
            <div dir="rtl" style="background: rgba(15, 23, 42, 0.65); border: 1px solid #334155; border-radius: 8px; padding: 14px 18px; margin-top: 8px; font-size: 14.5px; line-height: 1.8; color: #e2e8f0; text-align: right; direction: rtl;">
                <div style="font-weight: 800; font-size: 16px; margin-bottom: 8px; text-align: right;">
                    <span style="color: #67e8f9 !important;">📌 القواعد الهندسية لتحليل وتوزيع العزوم</span>
                    <span style="color: #fb923c !important;">(ECP 203):</span>
                </div>
                • <b>أقصى عزم سالب للشداد ($M_{{u,\\max}}$):</b> يحدث دائماً عند نقطة انعدام القص (<b>Zero Shear</b>) الواقعة على مسافة <span dir="ltr"><b>x₀ = {r.get('x0', 0.0):.2f} m</b></span> من حد الجار، وتكون الألياف العلوية مشدودة بالكامل بقيمة <span dir="ltr"><b>{r.get('Mu_max_strap', abs(r['Mu_neg'])):.2f} ton·m</b></span>، ولذلك يتم تركيز الحديد الرئيسي المقاوم للعزم في أعلى كمرة الشداد (Top Rebar).<br/>
                • <b>اتزان العزوم عند القاعدة الداخلية C2:</b> نظراً لارتكاز الشداد على القاعدة الداخلية المتماثلة حول العمود، يتلاشى العزم تدريجياً وبشكل خطي حتى يصل إلى <span dir="ltr"><b>Mu = 0.00 ton·m</b></span> عند محور العمود الداخلي C2 محققاً الاتزان الاستاتيكي التام للمجموعة.<br/>
                • <b>عزم رفرفة بلاطة القواعد في الاتجاه العرضي:</b> تعمل بلاطة قاعدة الجار والقاعدة الداخلية ككابولي خرساني باتجاه عرضي يرتكز على كمرة الشداد، ويصل أقصى عزم موجب (شد سفلي) عند وش الشداد بقيمة <span dir="ltr"><b>{r.get('Mu_trans1', 0.0):.2f} ton·m/m</b></span> لقاعدة الجار و <span dir="ltr"><b>{r.get('Mu_trans2', 0.0):.2f} ton·m/m</b></span> للقاعدة الداخلية، وهو ما يصمم عليه حديد القواعد العرضي الأساسي.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with det_tab4:
        st.markdown(
            """#### <span style="color: #67e8f9 !important;">📊 جدول حصر الكميات والمواد الإنشائية</span> <span style="color: #94a3b8 !important;">—</span> <span style="color: #fb923c !important;">Quantity Survey (BOQ)</span>""",
            unsafe_allow_html=True,
        )
        st.caption("حصر هندسي متكامل ومفصل لكميات حديد التسليح لكل قطر، والأوزان الإجمالية، وأحجام الخرسانة، وكميات الأسمنت والزلط والرمل طبقاً للمواصفات القياسية المصرية ECP 203.")

        strap_len_m = r["xc2"] + r["a2_m"] / 2.0 + 0.20
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
        side_cut_m = strap_len_m
        side_bars_num = n_side_pairs * 2
        side_w_kg = side_bars_num * side_cut_m * (10.0 ** 2 / 162.0)

        f1_cut_m = r["B1"] - 0.10 + 2.0 * max(0.15, (r["t1_cm"] / 100.0 - 0.10))
        f1_w_kg = n_t1 * f1_cut_m * (float(d["trans_bar_dia"]) ** 2 / 162.0)

        f2_cut_m = r["B2"] - 0.10 + 2.0 * max(0.15, (r["t2_cm"] / 100.0 - 0.10))
        f2_w_kg = n_t2 * f2_cut_m * (float(d["trans_bar_dia"]) ** 2 / 162.0)

        n_long1 = max(4, int(round(r["B1"] * 5.0)))
        f1_long_cut_m = r["L1"] - 0.10 + 2.0 * max(0.15, (r["t1_cm"] / 100.0 - 0.10))
        f1_long_w_kg = n_long1 * f1_long_cut_m * (12.0 ** 2 / 162.0)

        n_long2 = max(4, int(round(r["B2"] * 5.0)))
        f2_long_cut_m = r["L2"] - 0.10 + 2.0 * max(0.15, (r["t2_cm"] / 100.0 - 0.10))
        f2_long_w_kg = n_long2 * f2_long_cut_m * (12.0 ** 2 / 162.0)

        # ── Grouping Rebar by Diameter ─────────────────────────────────────────
        rebar_items = [
            (int(d["long_bar_dia"]), r["n_top"], top_cut_m, top_w_kg, "الشداد — حديد علوي رئيسي"),
            (int(d["long_bar_dia"]), r["n_bot"], bot_cut_m, bot_w_kg, "الشداد — حديد سفلي"),
            (int(d["stirrup_dia"]), st_count, st_perim_m, st_w_kg, "الشداد — كانات القص"),
        ]
        if side_bars_num > 0:
            rebar_items.append((10, side_bars_num, side_cut_m, side_w_kg, "الشداد — براندات انكماش جانبية"))

        rebar_items.extend([
            (int(d["trans_bar_dia"]), n_t1, f1_cut_m, f1_w_kg, "قاعدة الجار F1 — تسليح عرضي رئيسي"),
            (12, n_long1, f1_long_cut_m, f1_long_w_kg, "قاعدة الجار F1 — تسليح طولي ثانوي"),
            (int(d["trans_bar_dia"]), n_t2, f2_cut_m, f2_w_kg, "القاعدة الداخلية F2 — تسليح عرضي رئيسي"),
            (12, n_long2, f2_long_cut_m, f2_long_w_kg, "القاعدة الداخلية F2 — تسليح طولي ثانوي"),
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

        # ── Concrete Volumes Takeoff ──────────────────────────────────────────
        L1, B1, t1 = r["L1"], r["B1"], r["t1_cm"] / 100.0
        L2, B2, t2 = r["L2"], r["B2"], r["t2_cm"] / 100.0
        sb = r["sb_m"]
        sD = r["sD_cm"] / 100.0
        f2x = r["xc2"] - L2 / 2.0
        strap_end = r["xc2"] + r["a2_m"] / 2.0 + 0.15

        # Net RC Volumes
        v_f1_rc = L1 * B1 * t1
        v_f2_rc = L2 * B2 * t2
        v_strap_above_f1 = L1 * sb * max(0.0, sD - t1)
        clear_span = max(0.0, f2x - L1)
        v_strap_clear = clear_span * sb * sD
        in_f2_len = min(L2, max(0.0, strap_end - f2x))
        v_strap_above_f2 = in_f2_len * sb * max(0.0, sD - t2)
        v_strap_net = v_strap_above_f1 + v_strap_clear + v_strap_above_f2
        v_rc_total = v_f1_rc + v_f2_rc + v_strap_net

        # Plain Concrete (PC) volumes
        tpc = float(d.get("t_pc", 10.0)) / 100.0
        if tpc > 0:
            v_pc1 = (L1 + tpc) * (B1 + 2 * tpc) * tpc
            v_pc2 = (L2 + 2 * tpc) * (B2 + 2 * tpc) * tpc
            v_pc_total = v_pc1 + v_pc2
        else:
            v_pc_total = 0.0

        v_concrete_total = v_rc_total + v_pc_total

        # ── Raw Materials Takeoff (Cement, Gravel, Sand) per ECP 203 ──────────
        # Cement: 350 kg/m³ for RC (7 bags), 250 kg/m³ for PC (5 bags)
        cement_rc_ton = v_rc_total * 0.350
        cement_pc_ton = v_pc_total * 0.250
        cement_total_ton = cement_rc_ton + cement_pc_ton
        cement_bags = cement_total_ton * 1000.0 / 50.0

        # Gravel (السن/الزلط): 0.80 m³ per 1 m³ of concrete
        gravel_total_m3 = v_concrete_total * 0.80

        # Sand (الرمل): 0.40 m³ per 1 m³ of concrete
        sand_total_m3 = v_concrete_total * 0.40

        # Steel consumption rate (kg steel per m³ RC)
        steel_rate_kg_m3 = total_steel_kg / v_rc_total if v_rc_total > 0 else 0.0

        # ── KPI Metrics Cards ──────────────────────────────────────────────────
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

        # ── Table 1: Rebar Quantity by Diameter ────────────────────────────────
        st.markdown(
            """##### <span style="color: #67e8f9 !important;">🔩 1. حصر كميات حديد التسليح لكل قطر</span> <span style="color: #fb923c !important;">(Rebar by Diameter)</span>""",
            unsafe_allow_html=True,
        )
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

        # ── Table 2: Detailed Bar Schedule (BBS) ──────────────────────────────
        st.markdown(
            """##### <span style="color: #67e8f9 !important;">📋 2. كشف تفريد أسياخ حديد التسليح التفصيلي</span> <span style="color: #fb923c !important;">(Bar Bending Schedule - BBS)</span>""",
            unsafe_allow_html=True,
        )
        bbs_data = {
            "العنصر الإنشائي (Element)": [
                "الشداد — حديد علوي رئيسي (Top Rebar)",
                "الشداد — حديد سفلي (Bottom Rebar)",
                "الشداد — كانات القص (Stirrups)",
                "الشداد — براندات جانبية (Side Bars)",
                "قاعدة الجار F1 — تسليح عرضي (رئيسي)",
                "قاعدة الجار F1 — تسليح طولي (توزيع ثانوي)",
                "القاعدة الداخلية F2 — تسليح عرضي (رئيسي)",
                "القاعدة الداخلية F2 — تسليح طولي (توزيع ثانوي)",
            ],
            "القطر Φ (mm)": [
                f"{int(d['long_bar_dia'])} mm",
                f"{int(d['long_bar_dia'])} mm",
                f"{int(d['stirrup_dia'])} mm",
                "10 mm" if side_bars_num > 0 else "—",
                f"{int(d['trans_bar_dia'])} mm",
                "12 mm",
                f"{int(d['trans_bar_dia'])} mm",
                "12 mm",
            ],
            "الشكل / التوصيف": [
                "سيخ مستقيم مع رجلين 90°",
                "سيخ مستقيم مع عكفتين",
                f"كانة مقفولة ({r['n_branches']} فروع)",
                "أسياخ أفقية مستقيمة" if side_bars_num > 0 else "غير مطلوبة (D < 60cm)",
                "أسياخ عرضية بأرجل U-Shape",
                "أسياخ طولية موازية للشداد",
                "أسياخ عرضية بأرجل U-Shape",
                "أسياخ طولية موازية للشداد",
            ],
            "العدد / التوزيع": [
                f"{r['n_top']} أسياخ",
                f"{r['n_bot']} أسياخ",
                f"{st_count} كانة ({int(r['stirrup_per_m'])} كانات/م)",
                f"{side_bars_num} أسياخ" if side_bars_num > 0 else "0",
                f"{n_t1} سيخ على L1",
                f"{n_long1} سيخ على B1 (5 Φ 12 / م)",
                f"{n_t2} سيخ على L2",
                f"{n_long2} سيخ على B2 (5 Φ 12 / م)",
            ],
            "طول القطع التقريبي (m)": [
                f"{top_cut_m:.2f} m",
                f"{bot_cut_m:.2f} m",
                f"{st_perim_m:.2f} m",
                f"{side_cut_m:.2f} m" if side_bars_num > 0 else "—",
                f"{f1_cut_m:.2f} m",
                f"{f1_long_cut_m:.2f} m",
                f"{f2_cut_m:.2f} m",
                f"{f2_long_cut_m:.2f} m",
            ],
            "الوزن التقريبي (kg)": [
                f"{top_w_kg:.1f} kg",
                f"{bot_w_kg:.1f} kg",
                f"{st_w_kg:.1f} kg",
                f"{side_w_kg:.1f} kg" if side_bars_num > 0 else "0.0 kg",
                f"{f1_w_kg:.1f} kg",
                f"{f1_long_w_kg:.1f} kg",
                f"{f2_w_kg:.1f} kg",
                f"{f2_long_w_kg:.1f} kg",
            ],
        }
        st.dataframe(pd.DataFrame(bbs_data).set_index("العنصر الإنشائي (Element)"), use_container_width=True)

        # ── Table 3: Concrete & Materials Takeoff ──────────────────────────────
        st.markdown(
            """##### <span style="color: #67e8f9 !important;">🧱 3. جدول حصر الخرسانات ومواد البناء الأساسية</span> <span style="color: #fb923c !important;">(Concrete & Materials BOQ)</span>""",
            unsafe_allow_html=True,
        )
        materials_data = {
            "البند / المادة (Item / Material)": [
                "خرسانة مسلحة — قاعدة الجار (Footing 1 RC)",
                "خرسانة مسلحة — القاعدة الداخلية (Footing 2 RC)",
                "خرسانة مسلحة — كمرة الشداد الصافية (Strap Beam RC)",
                "إجمالي الخرسانة المسلحة (Total Reinforced Concrete)",
                "خرسانة عادية فرشة نظافة (Plain Concrete PC)",
                "الأسمنت البورتلاندي للخرسانة المسلحة (RC Cement)",
                "الأسمنت البورتلاندي للخرسانة العادية (PC Cement)",
                "إجمالي الأسمنت المطلوب (Total Cement)",
                "الركام الكبير / الزلط أو السن (Coarse Aggregate / Gravel)",
                "الركام الصغير / الرمل النظيف (Fine Aggregate / Sand)",
                "مياه الخلط التقريبية (Mixing Water)",
            ],
            "الوحدة (Unit)": [
                "m³", "m³", "m³", "m³", "m³",
                "Ton", "Ton", "Ton",
                "m³", "m³", "لتر (Liter)",
            ],
            "الكمية المحسوبة (Quantity)": [
                f"{v_f1_rc:.2f} m³",
                f"{v_f2_rc:.2f} m³",
                f"{v_strap_net:.2f} m³",
                f"{v_rc_total:.2f} m³",
                f"{v_pc_total:.2f} m³" if v_pc_total > 0 else "—",
                f"{cement_rc_ton:.2f} Ton ({v_rc_total * 7:.0f} شكارة)",
                f"{cement_pc_ton:.2f} Ton ({v_pc_total * 5:.0f} شكارة)" if v_pc_total > 0 else "—",
                f"{cement_total_ton:.2f} Ton ({cement_bags:.0f} شكارة)",
                f"{gravel_total_m3:.2f} m³",
                f"{sand_total_m3:.2f} m³",
                f"{v_concrete_total * 175.0:.0f} L",
            ],
            "المعدل والمواصفات القياسية (ECP 203)": [
                f"L1 × B1 × t1 ({r['L1']:.2f} × {r['B1']:.2f} × {t1:.2f} m)",
                f"L2 × B2 × t2 ({r['L2']:.2f} × {r['B2']:.2f} × {t2:.2f} m)",
                "صافي حجم الشداد خارج تداخل بلاطات القواعد",
                f"معدل التسليح = {steel_rate_kg_m3:.1f} kg/m³ خرسانة مسلحة",
                f"سماكة {d.get('t_pc', 10.0):.0f} cm مع رفرفة عادية",
                "350 kg/m³ (7 شكائر في المتر المكعب)",
                "250 kg/m³ (5 شكائر في المتر المكعب)",
                "أسمنت بورتلاندي رتبة 42.5N معبأ 50 كجم",
                "0.80 m³ لكل 1 m³ خرسانة",
                "0.40 m³ لكل 1 m³ خرسانة",
                "بمعدل 175 لتر مياه صالحة للشرب لكل 1 m³ خرسانة",
            ],
        }
        st.dataframe(pd.DataFrame(materials_data).set_index("البند / المادة (Item / Material)"), use_container_width=True)

        st.markdown(
            f"""
            <div dir="rtl" style="background: rgba(15, 23, 42, 0.65); border: 1px solid #334155; border-radius: 8px; padding: 14px 18px; margin-top: 12px; font-size: 14px; line-height: 1.8; color: #e2e8f0; text-align: right; direction: rtl;">
                <div style="font-weight: 800; font-size: 16px; margin-bottom: 8px; text-align: right;">
                    <span style="color: #67e8f9 !important;">📌 ملاحظات هندسية لحصر المواد والتشوين</span>
                    <span style="color: #fb923c !important;">(ECP 203):</span>
                </div>
                • <b>نسبة الهالك في الموقع (Wastage Factor):</b> الكميات أعلاه هي كميات هندسية صافية طبقاً للأبعاد التنفيذية. يوصى بإضافة نسبة هالك <b>5% إلى 7%</b> لحديد التسليح (لتغطية وصلات التراكب والفضلات)، وإضافة <b>3% إلى 5%</b> للخرسانة والركام والأسمنت.<br/>
                • <b>معدل استهلاك الحديد (Steel Ratio):</b> يبلغ معدل التسليح الإجمالي <span dir="ltr"><b>{steel_rate_kg_m3:.1f} kg/m³</b></span> من الخرسانة المسلحة، وهو معدل اقتصادي ومتوازن متوافق تماماً مع نسب تسليح القواعد والشدادات بالكود المصري.<br/>
                • <b>نسب الخلط القياسية:</b> كل <b>1 م³</b> خرسانة مسلحة يتطلب: <span dir="ltr">0.80 m³</span> زلط/سن + <span dir="ltr">0.40 m³</span> رمل حرش + <span dir="ltr">350 kg</span> أسمنت (7 شكائر).
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Persist state
    d["final_B1"] = r["B1"]
    d["final_L2"] = r["L2"]
    d["final_B2"] = r["B2"]
    d["is_calculated"] = True
    st.session_state["module_9_data"] = d
