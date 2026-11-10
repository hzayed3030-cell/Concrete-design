"""
Module 10 — Equipment & Liquid Storage Tank Foundations
(تصميم القواعد الإنشائية للمعدات الميكانيكية وخزانات السوائل)
================================================================
ECP 203 - Egyptian Code of Practice / ACI 351.3R / ACI 350 / ACI 318
Comprehensive Structural & Geotechnical Design Module for:
1. Mechanical Equipment Foundations (Static & Dynamic / Vibrating Machinery)
2. Liquid Storage Tank Foundations (Circular & Rectangular, Steel & Plastic)
"""

import io
import math
import base64
import datetime
import numpy as np
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon

from modules import settings as S
from modules.steel_bars import BARS
from modules.report_generator import html_to_pdf_bytes

BAR_WEIGHTS = {b["dia_mm"]: b["weight_kgm"] for b in BARS}
BAR_AREAS = {b["dia_mm"]: b["area_cm2"] for b in BARS}
ECP_DIAMETERS = [10, 12, 16, 18, 20, 22, 25, 28, 32]


# ===============================================================================
#  1. ENGINEERING COMPUTATION ENGINE — EQUIPMENT FOUNDATIONS (STATIC & DYNAMIC)
# ===============================================================================

def compute_equipment_foundation_design(
    eq_weight_ton: float = 15.0,
    eq_shape: str = "مستطيلة (Rectangular)",
    eq_length_m: float = 2.50,
    eq_width_m: float = 1.50,
    eq_dia_m: float = 2.00,
    isolation_type: str = "وجود نظام عزل اهتزازات (Springs & Isolators)",
    operating_rpm: float = 1500.0,
    ks_kg_cm3: float = 4.0,
    fc_kg_cm2: float = 300.0,
    fy_kg_cm2: float = 3600.0,
    q_all_kg_cm2: float = 1.50,
    sizing_mode: str = "حساب أوتوماتيكي للأبعاد (Auto-Sizing)",
    manual_Lf_m: float = 3.50,
    manual_Bf_m: float = 2.50,
    manual_tf_m: float = 0.80,
    target_mass_ratio: float = 2.50,
    cover_cm: float = 7.5,
    phi_bot_mm: int = 16,
    phi_top_mm: int = 12,
) -> dict:
    """
    Executes full structural, geotechnical, and dynamic vibration design for
    Mechanical Equipment Foundations according to ECP 203 & ACI 351.3R.
    """
    gamma_c = 2.50  # ton/m³ (Reinforced Concrete Density)
    q_all_ton_m2 = q_all_kg_cm2 * 10.0  # 1 kg/cm² = 10 ton/m²

    is_circular_eq = "دائرية" in eq_shape or "Circular" in eq_shape
    is_fixed_base = "عدم وجود" in isolation_type or "Fixed Base" in isolation_type
    is_isolated = not is_fixed_base

    if is_circular_eq:
        Lm_m = max(eq_dia_m, 0.20)
        Bm_m = max(eq_dia_m, 0.20)
    else:
        Lm_m = max(eq_length_m, 0.20)
        Bm_m = max(eq_width_m, 0.20)

    # Clearance around equipment footprint (min 0.30m to 0.50m per side)
    min_clearance_m = 0.40
    min_Lf = round(Lm_m + 2.0 * min_clearance_m, 2)
    min_Bf = round(Bm_m + 2.0 * min_clearance_m, 2)

    # Dynamic Factor & Target Mass Ratio Logic
    if is_isolated:
        dyn_factor = 1.20
        P_eq_design_ton = eq_weight_ton * dyn_factor
        req_min_wf_ton = 0.0  # Governed by geometry, soil & punching
    else:
        # Fixed Base (No isolation): Concrete weight must be 2.0 to 3.0 times equipment weight
        dyn_factor = 1.50  # Dynamic impact amplification for non-isolated strength check
        P_eq_design_ton = eq_weight_ton * dyn_factor
        clamped_ratio = max(2.0, min(3.0, target_mass_ratio))
        req_min_wf_ton = eq_weight_ton * clamped_ratio

    # Determine Foundation Dimensions (Lf, Bf, tf)
    if "Auto" in sizing_mode or "أوتوماتيكي" in sizing_mode:
        # Start with minimum plan dimensions
        Lf_m = max(min_Lf, 1.20)
        Bf_m = max(min_Bf, 1.20)
        tf_m = 0.50 if is_isolated else 0.70

        # If Fixed Base, ensure volume satisfies W_f >= target_mass_ratio * W_eq
        if not is_isolated:
            req_vol_m3 = req_min_wf_ton / gamma_c
            current_vol = Lf_m * Bf_m * tf_m
            if current_vol < req_vol_m3:
                # Scale plan & thickness proportionally
                scale_3d = (req_vol_m3 / max(current_vol, 0.01)) ** (1.0 / 3.0)
                Lf_m = math.ceil((Lf_m * scale_3d) * 20.0) / 20.0
                Bf_m = math.ceil((Bf_m * scale_3d) * 20.0) / 20.0
                tf_m = math.ceil((req_vol_m3 / (Lf_m * Bf_m)) * 20.0) / 20.0
                tf_m = max(tf_m, 0.60)

        # Iterative Soil Bearing & Punching Convergence Loop
        for _ in range(40):
            vol_f = Lf_m * Bf_m * tf_m
            Wf_ton = vol_f * gamma_c
            P_total_working = P_eq_design_ton + Wf_ton
            Af_m2 = Lf_m * Bf_m
            q_act_ton_m2 = P_total_working / Af_m2

            # Check soil pressure
            if q_act_ton_m2 > q_all_ton_m2:
                # Expand plan area
                Lf_m = round(Lf_m + 0.15, 2)
                Bf_m = round(Bf_m + 0.15, 2)
                continue

            # Check punching shear
            d_cm = max(tf_m * 100.0 - cover_cm, 15.0)
            d_m = d_cm / 100.0
            if is_circular_eq:
                bo_m = math.pi * (Lm_m + d_m)
                area_punch_m2 = (math.pi / 4.0) * ((Lm_m + d_m) ** 2)
            else:
                bo_m = 2.0 * ((Lm_m + d_m) + (Bm_m + d_m))
                area_punch_m2 = (Lm_m + d_m) * (Bm_m + d_m)

            Pu_eq_ton = 1.50 * P_eq_design_ton
            qu_net_ton_m2 = Pu_eq_ton / Af_m2
            Q_up_ton = max(0.0, Pu_eq_ton - qu_net_ton_m2 * min(area_punch_m2, Af_m2))
            q_up_kg_cm2 = (Q_up_ton * 1000.0) / (bo_m * 100.0 * d_cm)

            fcu_mpa = fc_kg_cm2 / 10.0
            q_cup_kg_cm2 = min(0.316 * math.sqrt(fcu_mpa / 1.50) * 10.0, 16.0)

            if q_up_kg_cm2 > q_cup_kg_cm2:
                tf_m = round(tf_m + 0.05, 2)
                continue

            break
    else:
        Lf_m = max(manual_Lf_m, 0.50)
        Bf_m = max(manual_Bf_m, 0.50)
        tf_m = max(manual_tf_m, 0.25)

    # Final Geometry & Self-Weight Automatic Calculation
    Af_m2 = Lf_m * Bf_m
    vol_f_m3 = Af_m2 * tf_m
    Wf_ton = vol_f_m3 * gamma_c  # Automatic Self-Weight (2.5 t/m³)
    actual_mass_ratio = Wf_ton / max(eq_weight_ton, 0.01)

    if is_isolated:
        is_mass_ratio_safe = True
        req_mass_ratio_min = 0.0
    else:
        req_mass_ratio_min = 2.0
        is_mass_ratio_safe = actual_mass_ratio >= 1.999

    # Total Working & Ultimate Loads
    P_total_working_ton = P_eq_design_ton + Wf_ton
    Pu_total_ton = 1.40 * Wf_ton + 1.50 * P_eq_design_ton
    Pu_net_ton = 1.50 * P_eq_design_ton  # Net upward pressure causing bending/shear

    # 1. Soil Bearing Check
    q_act_ton_m2 = P_total_working_ton / Af_m2
    q_act_kg_cm2 = q_act_ton_m2 / 10.0
    ratio_soil = q_act_kg_cm2 / max(q_all_kg_cm2, 0.01)
    is_soil_safe = ratio_soil <= 1.0001

    # 2. Natural Frequency & Resonance Check (ACI 351.3R / Richart-Whitman)
    # Spring constant of soil Kz = ks * Af
    # ks in kg/cm³ -> 1 kg/cm³ = 1000 ton/m³
    ks_ton_m3 = ks_kg_cm3 * 1000.0
    Kz_ton_m = ks_ton_m3 * Af_m2
    Kz_N_m = Kz_ton_m * 9806.65
    total_mass_kg = ((eq_weight_ton + Wf_ton) * 1000.0)
    omega_n_rad_s = math.sqrt(Kz_N_m / max(total_mass_kg, 1.0))
    fn_hz = omega_n_rad_s / (2.0 * math.pi)
    f_op_hz = operating_rpm / 60.0
    freq_ratio = f_op_hz / max(fn_hz, 0.01)

    # Resonance band is 0.70 <= f_op / fn <= 1.30 for fixed-base foundations
    if is_isolated:
        # With springs & isolators (tuned low natural frequency), isolation efficiency > 85%
        is_resonance_safe = True
        resonance_status_ar = "آمن (معزول بديناميكية نوابض وعوازل)"
    else:
        is_resonance_safe = (freq_ratio < 0.70) or (freq_ratio > 1.30)
        if is_resonance_safe:
            resonance_status_ar = f"آمن ضد الرنين (r = {freq_ratio:.2f} خارج نطاق 0.7–1.3)"
        else:
            resonance_status_ar = f"⚠️ خطر رنين ديناميكي (r = {freq_ratio:.2f} ضمن النطاق الحرج 0.7–1.3)"

    # 3. Punching Shear & One-Way Shear Checks (ECP 203)
    d_cm = max(tf_m * 100.0 - cover_cm, 10.0)
    d_m = d_cm / 100.0
    fcu_mpa = fc_kg_cm2 / 10.0
    gamma_c_mat = 1.50
    gamma_s_mat = 1.15

    if is_circular_eq:
        bo_m = math.pi * (Lm_m + d_m)
        area_punch_m2 = (math.pi / 4.0) * ((Lm_m + d_m) ** 2)
    else:
        bo_m = 2.0 * ((Lm_m + d_m) + (Bm_m + d_m))
        area_punch_m2 = (Lm_m + d_m) * (Bm_m + d_m)

    qu_net_ton_m2 = Pu_net_ton / Af_m2
    Q_up_ton = max(0.0, Pu_net_ton - qu_net_ton_m2 * min(area_punch_m2, Af_m2))
    q_up_kg_cm2 = (Q_up_ton * 1000.0) / (bo_m * 100.0 * d_cm)

    # ECP 203 Allowable Concrete Punching Shear Stress
    alpha_col = 4.0
    q_cup_1 = 0.80 * ((alpha_col * d_cm / (bo_m * 100.0)) + 0.20) * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    if is_circular_eq:
        q_cup_2 = 0.316 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    else:
        beta_c = min(Lm_m, Bm_m) / max(Lm_m, Bm_m)
        q_cup_2 = 0.316 * (0.50 + beta_c) * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    q_cup_3 = 0.316 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    q_cup_all_kg_cm2 = min(q_cup_1, q_cup_2, q_cup_3, 16.0)

    ratio_punching = q_up_kg_cm2 / max(q_cup_all_kg_cm2, 0.01)
    is_punching_safe = ratio_punching <= 1.0001

    # One-Way Shear Check
    cant_L_m = max(0.0, (Lf_m - Lm_m) / 2.0)
    cant_B_m = max(0.0, (Bf_m - Bm_m) / 2.0)
    crit_shear_arm_m = max(0.0, max(cant_L_m, cant_B_m) - d_m)
    Qu_1way_ton_m = qu_net_ton_m2 * crit_shear_arm_m
    qu_1way_kg_cm2 = (Qu_1way_ton_m * 1000.0) / (100.0 * d_cm)
    qcu_1way_kg_cm2 = 0.16 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    ratio_1way_shear = qu_1way_kg_cm2 / max(qcu_1way_kg_cm2, 0.01)
    is_1way_shear_safe = ratio_1way_shear <= 1.0001

    # 4. Flexural Design & Reinforcement (Bottom & Top Meshes per ECP 203 / ACI)
    # Bottom reinforcement: Cantilever moment under net upward soil reaction
    Mu_bot_L_tm = qu_net_ton_m2 * (cant_L_m ** 2) / 2.0
    Mu_bot_B_tm = qu_net_ton_m2 * (cant_B_m ** 2) / 2.0
    Mu_bot_max_tm = max(Mu_bot_L_tm, Mu_bot_B_tm, 1.50)

    # Top reinforcement: Dynamic reversal / shrinkage / thermal / uplift moment (min 50% of bottom or shrinkage)
    Mu_top_max_tm = max(0.50 * Mu_bot_max_tm, 1.0)

    j_factor = 0.826
    fy_design = fy_kg_cm2 / gamma_s_mat

    As_bot_flex_cm2_m = (Mu_bot_max_tm * 1e5) / (fy_design * j_factor * d_cm)
    As_top_flex_cm2_m = (Mu_top_max_tm * 1e5) / (fy_design * j_factor * d_cm)

    # Minimum Reinforcement per ECP 203 (0.15% of d or 1.5/fy * b * d, min 5Φ12/m)
    As_min_ecp_cm2_m = max(0.0015 * 100.0 * d_cm, (0.60 / (fy_kg_cm2 / 10.0)) * 100.0 * d_cm, 5.65)
    # Top mesh minimum for dynamic/massive equipment foundations (shrinkage & vibration crack control)
    As_min_top_cm2_m = max(0.0012 * 100.0 * d_cm, 5.65)

    As_bot_req_cm2_m = max(As_bot_flex_cm2_m, As_min_ecp_cm2_m)
    As_top_req_cm2_m = max(As_top_flex_cm2_m, As_min_top_cm2_m)

    area_bar_bot = BAR_AREAS.get(phi_bot_mm, (math.pi * (phi_bot_mm / 10.0) ** 2) / 4.0)
    area_bar_top = BAR_AREAS.get(phi_top_mm, (math.pi * (phi_top_mm / 10.0) ** 2) / 4.0)

    n_bars_bot_m = max(5, math.ceil(As_bot_req_cm2_m / area_bar_bot))
    n_bars_top_m = max(5, math.ceil(As_top_req_cm2_m / area_bar_top))

    spacing_bot_cm = round(100.0 / n_bars_bot_m, 1)
    spacing_top_cm = round(100.0 / n_bars_top_m, 1)

    As_bot_prov_cm2_m = n_bars_bot_m * area_bar_bot
    As_top_prov_cm2_m = n_bars_top_m * area_bar_top

    # Total Steel Quantities (Bottom X+Y + Top X+Y + Side Dowels/Stirrups)
    wt_bar_bot_kg_m = BAR_WEIGHTS.get(phi_bot_mm, (phi_bot_mm ** 2) / 162.0)
    wt_bar_top_kg_m = BAR_WEIGHTS.get(phi_top_mm, (phi_top_mm ** 2) / 162.0)

    # Length of bars including U-legs (2 * (tf - 2*cover))
    u_leg_m = max(0.20, tf_m - 2.0 * (cover_cm / 100.0))
    len_bar_L_m = Lf_m - 2.0 * (cover_cm / 100.0) + 2.0 * u_leg_m
    len_bar_B_m = Bf_m - 2.0 * (cover_cm / 100.0) + 2.0 * u_leg_m

    total_bars_bot_L = math.ceil(n_bars_bot_m * Bf_m) + 1
    total_bars_bot_B = math.ceil(n_bars_bot_m * Lf_m) + 1
    weight_bot_kg = (total_bars_bot_L * len_bar_L_m + total_bars_bot_B * len_bar_B_m) * wt_bar_bot_kg_m

    total_bars_top_L = math.ceil(n_bars_top_m * Bf_m) + 1
    total_bars_top_B = math.ceil(n_bars_top_m * Lf_m) + 1
    weight_top_kg = (total_bars_top_L * len_bar_L_m + total_bars_top_B * len_bar_B_m) * wt_bar_top_kg_m

    total_rebar_weight_kg = (weight_bot_kg + weight_top_kg) * 1.05  # +5% side shrinkage bars & chairs
    total_rebar_weight_ton = total_rebar_weight_kg / 1000.0
    steel_rate_kg_m3 = total_rebar_weight_kg / max(vol_f_m3, 0.01)

    is_all_safe = is_soil_safe and is_punching_safe and is_1way_shear_safe and is_mass_ratio_safe and is_resonance_safe

    return {
        "eq_weight_ton": eq_weight_ton,
        "eq_shape": eq_shape,
        "is_circular_eq": is_circular_eq,
        "Lm_m": Lm_m,
        "Bm_m": Bm_m,
        "isolation_type": isolation_type,
        "is_isolated": is_isolated,
        "operating_rpm": operating_rpm,
        "ks_kg_cm3": ks_kg_cm3,
        "fc_kg_cm2": fc_kg_cm2,
        "fy_kg_cm2": fy_kg_cm2,
        "q_all_kg_cm2": q_all_kg_cm2,
        "q_all_ton_m2": q_all_ton_m2,
        "sizing_mode": sizing_mode,
        "Lf_m": Lf_m,
        "Bf_m": Bf_m,
        "tf_m": tf_m,
        "tf_cm": tf_m * 100.0,
        "d_cm": d_cm,
        "cover_cm": cover_cm,
        "Af_m2": Af_m2,
        "vol_f_m3": vol_f_m3,
        "Wf_ton": Wf_ton,
        "dyn_factor": dyn_factor,
        "P_eq_design_ton": P_eq_design_ton,
        "P_total_working_ton": P_total_working_ton,
        "Pu_total_ton": Pu_total_ton,
        "Pu_net_ton": Pu_net_ton,
        "actual_mass_ratio": actual_mass_ratio,
        "req_mass_ratio_min": req_mass_ratio_min,
        "req_min_wf_ton": req_min_wf_ton,
        "is_mass_ratio_safe": is_mass_ratio_safe,
        "q_act_ton_m2": q_act_ton_m2,
        "q_act_kg_cm2": q_act_kg_cm2,
        "ratio_soil": ratio_soil,
        "is_soil_safe": is_soil_safe,
        "fn_hz": fn_hz,
        "f_op_hz": f_op_hz,
        "freq_ratio": freq_ratio,
        "is_resonance_safe": is_resonance_safe,
        "resonance_status_ar": resonance_status_ar,
        "bo_m": bo_m,
        "Q_up_ton": Q_up_ton,
        "q_up_kg_cm2": q_up_kg_cm2,
        "q_cup_all_kg_cm2": q_cup_all_kg_cm2,
        "ratio_punching": ratio_punching,
        "is_punching_safe": is_punching_safe,
        "Qu_1way_ton_m": Qu_1way_ton_m,
        "qu_1way_kg_cm2": qu_1way_kg_cm2,
        "qcu_1way_kg_cm2": qcu_1way_kg_cm2,
        "ratio_1way_shear": ratio_1way_shear,
        "is_1way_shear_safe": is_1way_shear_safe,
        "Mu_bot_max_tm": Mu_bot_max_tm,
        "Mu_top_max_tm": Mu_top_max_tm,
        "As_bot_req_cm2_m": As_bot_req_cm2_m,
        "As_top_req_cm2_m": As_top_req_cm2_m,
        "phi_bot_mm": phi_bot_mm,
        "phi_top_mm": phi_top_mm,
        "n_bars_bot_m": n_bars_bot_m,
        "n_bars_top_m": n_bars_top_m,
        "spacing_bot_cm": spacing_bot_cm,
        "spacing_top_cm": spacing_top_cm,
        "As_bot_prov_cm2_m": As_bot_prov_cm2_m,
        "As_top_prov_cm2_m": As_top_prov_cm2_m,
        "weight_bot_kg": weight_bot_kg,
        "weight_top_kg": weight_top_kg,
        "total_rebar_weight_kg": total_rebar_weight_kg,
        "total_rebar_weight_ton": total_rebar_weight_ton,
        "steel_rate_kg_m3": steel_rate_kg_m3,
        "is_all_safe": is_all_safe,
    }


# ===============================================================================
#  2. ENGINEERING COMPUTATION ENGINE — LIQUID STORAGE TANK FOUNDATIONS
# ===============================================================================

def compute_liquid_tank_foundation_design(
    tank_shape: str = "دائري (Circular)",
    tank_dia_m: float = 6.00,
    tank_length_m: float = 6.00,
    tank_width_m: float = 4.00,
    tank_material: str = "صاج صلب (Steel Sheet)",
    sheet_thk_mm: float = 8.0,
    capacity_barrels: float = 1000.0,
    specific_gravity: float = 0.85,
    fc_kg_cm2: float = 300.0,
    fy_kg_cm2: float = 3600.0,
    q_all_kg_cm2: float = 1.50,
    sizing_mode: str = "حساب أوتوماتيكي للأبعاد (Auto-Sizing)",
    manual_overhang_m: float = 0.60,
    manual_tf_m: float = 0.60,
    gwt_depth_m: float = 1.00,
    wind_seismic_coeff: float = 0.08,
    cover_cm: float = 7.5,
    phi_bot_mm: int = 16,
    phi_top_mm: int = 12,
) -> dict:
    """
    Executes full structural, hydrostatic, buoyancy, overturning, punching shear,
    and reinforcement design for Liquid Storage Tank Foundations per ECP 203 / ACI 350.
    """
    gamma_c = 2.50  # ton/m³ (Reinforced Concrete Density - Mandatory)
    gamma_water = 1.00  # ton/m³
    q_all_ton_m2 = q_all_kg_cm2 * 10.0

    is_circular = "دائري" in tank_shape or "Circular" in tank_shape
    is_steel = "صاج" in tank_material or "Steel" in tank_material

    # 1 Barrel (US Oil Barrel) = 42 US Gallons = 158.9873 Liters = 0.1589873 m³
    BBL_TO_M3 = 0.1589873
    vol_liquid_m3 = capacity_barrels * BBL_TO_M3
    gamma_liquid_ton_m3 = specific_gravity * gamma_water
    W_liquid_ton = vol_liquid_m3 * gamma_liquid_ton_m3

    # Tank Plan Area & Effective Liquid Height
    if is_circular:
        D_tank_m = max(tank_dia_m, 0.50)
        L_tank_m = D_tank_m
        B_tank_m = D_tank_m
        A_tank_m2 = (math.pi / 4.0) * (D_tank_m ** 2)
        perimeter_tank_m = math.pi * D_tank_m
    else:
        L_tank_m = max(tank_length_m, 0.50)
        B_tank_m = max(tank_width_m, 0.50)
        D_tank_m = max(L_tank_m, B_tank_m)
        A_tank_m2 = L_tank_m * B_tank_m
        perimeter_tank_m = 2.0 * (L_tank_m + B_tank_m)

    H_liquid_m = vol_liquid_m3 / max(A_tank_m2, 0.01)
    freeboard_m = max(0.30, 0.10 * H_liquid_m)
    H_tank_total_m = H_liquid_m + freeboard_m

    # Tank Structure Empty Self-Weight Calculation (Automatic based on Material, Dimensions & Thickness)
    # Total Surface Area = Bottom Floor + Side Shell Wall + Roof Cover (with 15% stiffeners/nozzles allowance)
    area_shell_m2 = perimeter_tank_m * H_tank_total_m
    area_total_plates_m2 = (2.0 * A_tank_m2 + area_shell_m2) * 1.15
    thk_m = max(sheet_thk_mm, 1.0) / 1000.0
    if is_steel:
        gamma_mat_ton_m3 = 7.85  # Steel density = 7.85 ton/m³
    else:
        gamma_mat_ton_m3 = 1.40  # High-density Polyethylene / GRP Plastic = 1.40 ton/m³

    W_tank_empty_ton = area_total_plates_m2 * thk_m * gamma_mat_ton_m3

    # Hydrostatic Pressure on Tank Base
    p_hydrostatic_ton_m2 = gamma_liquid_ton_m3 * H_liquid_m
    p_hydrostatic_kg_cm2 = p_hydrostatic_ton_m2 / 10.0

    # Auto-Sizing or Manual Foundation Dimensions
    if "Auto" in sizing_mode or "أوتوماتيكي" in sizing_mode:
        overhang_m = 0.50
        tf_m = 0.50

        for _ in range(45):
            if is_circular:
                Df_m = D_tank_m + 2.0 * overhang_m
                Lf_m = Df_m
                Bf_m = Df_m
                Af_m2 = (math.pi / 4.0) * (Df_m ** 2)
            else:
                Lf_m = L_tank_m + 2.0 * overhang_m
                Bf_m = B_tank_m + 2.0 * overhang_m
                Df_m = Lf_m
                Af_m2 = Lf_m * Bf_m

            vol_f_m3 = Af_m2 * tf_m
            Wf_ton = vol_f_m3 * gamma_c  # Mandatory Self-Weight (2.5 t/m³)
            P_total_working = W_tank_empty_ton + W_liquid_ton + Wf_ton
            q_act_ton_m2 = P_total_working / Af_m2

            # 1. Check Soil Bearing
            if q_act_ton_m2 > q_all_ton_m2:
                overhang_m = round(overhang_m + 0.10, 2)
                continue

            # 2. Check Buoyancy (Uplift when Tank is Empty & submerged by gwt_depth_m)
            U_buoyancy_ton = Af_m2 * max(0.0, gwt_depth_m) * gamma_water
            W_resisting_uplift = W_tank_empty_ton + Wf_ton
            fos_buoyancy = W_resisting_uplift / max(U_buoyancy_ton, 0.01) if U_buoyancy_ton > 0 else 99.9
            if U_buoyancy_ton > 0 and fos_buoyancy < 1.25:
                tf_m = round(tf_m + 0.05, 2)
                continue

            # 3. Check Punching Shear under Shell / Tank Footprint
            d_cm = max(tf_m * 100.0 - cover_cm, 15.0)
            d_m = d_cm / 100.0
            if is_circular:
                bo_m = math.pi * (D_tank_m + d_m)
                area_punch_m2 = (math.pi / 4.0) * ((D_tank_m + d_m) ** 2)
            else:
                bo_m = 2.0 * ((L_tank_m + d_m) + (B_tank_m + d_m))
                area_punch_m2 = (L_tank_m + d_m) * (B_tank_m + d_m)

            Pu_tank_liq_ton = 1.40 * W_tank_empty_ton + 1.50 * W_liquid_ton
            qu_net_ton_m2 = Pu_tank_liq_ton / Af_m2
            Q_up_ton = max(0.0, Pu_tank_liq_ton - qu_net_ton_m2 * min(area_punch_m2, Af_m2))
            q_up_kg_cm2 = (Q_up_ton * 1000.0) / (bo_m * 100.0 * d_cm)

            fcu_mpa = fc_kg_cm2 / 10.0
            q_cup_all_kg_cm2 = min(0.316 * math.sqrt(fcu_mpa / 1.50) * 10.0, 16.0)
            if q_up_kg_cm2 > q_cup_all_kg_cm2:
                tf_m = round(tf_m + 0.05, 2)
                continue

            break
    else:
        overhang_m = max(manual_overhang_m, 0.15)
        tf_m = max(manual_tf_m, 0.25)

    # Final Geometry & Mandatory Foundation Self-Weight Calculation
    if is_circular:
        Df_m = round(D_tank_m + 2.0 * overhang_m, 2)
        Lf_m = Df_m
        Bf_m = Df_m
        Af_m2 = (math.pi / 4.0) * (Df_m ** 2)
        If_m4 = (math.pi / 64.0) * (Df_m ** 4)
        c_edge_m = Df_m / 2.0
    else:
        Lf_m = round(L_tank_m + 2.0 * overhang_m, 2)
        Bf_m = round(B_tank_m + 2.0 * overhang_m, 2)
        Df_m = Lf_m
        Af_m2 = Lf_m * Bf_m
        # Bending about shorter axis Bf_m for conservative overturning check
        B_gov_m = min(Lf_m, Bf_m)
        L_gov_m = max(Lf_m, Bf_m)
        If_m4 = (L_gov_m * (B_gov_m ** 3)) / 12.0
        c_edge_m = B_gov_m / 2.0

    vol_f_m3 = Af_m2 * tf_m
    Wf_ton = vol_f_m3 * gamma_c  # Mandatory Self-Weight = V_f * 2.5 ton/m³

    # Total Working & Ultimate Loads (Tank + Liquid + Foundation Self-Weight)
    P_total_working_ton = W_tank_empty_ton + W_liquid_ton + Wf_ton
    Pu_total_ton = 1.40 * (W_tank_empty_ton + Wf_ton) + 1.50 * W_liquid_ton
    Pu_net_ton = 1.40 * W_tank_empty_ton + 1.50 * W_liquid_ton

    # Stability against Overturning (Wind / Seismic Lateral Force)
    V_lateral_ton = wind_seismic_coeff * (W_tank_empty_ton + W_liquid_ton)
    lever_arm_m = 0.50 * H_liquid_m + tf_m
    M_overturning_tm = V_lateral_ton * lever_arm_m

    # Resisting Moment about toe
    M_resisting_full_tm = P_total_working_ton * c_edge_m
    fos_overturning = M_resisting_full_tm / max(M_overturning_tm, 0.01)
    is_overturning_safe = fos_overturning >= 1.50

    # Stability against Buoyancy / Uplift (Empty Tank + Groundwater Head)
    U_buoyancy_ton = Af_m2 * max(0.0, gwt_depth_m) * gamma_water
    W_empty_total_ton = W_tank_empty_ton + Wf_ton
    fos_buoyancy = W_empty_total_ton / max(U_buoyancy_ton, 0.01) if U_buoyancy_ton > 0 else 99.9
    is_buoyancy_safe = fos_buoyancy >= 1.25

    # Soil Bearing Stress Check (Direct + Eccentricity from Overturning Moment)
    q_avg_ton_m2 = P_total_working_ton / Af_m2
    q_moment_ton_m2 = (M_overturning_tm * c_edge_m) / max(If_m4, 0.01)
    q_max_ton_m2 = q_avg_ton_m2 + q_moment_ton_m2
    q_min_ton_m2 = q_avg_ton_m2 - q_moment_ton_m2

    q_max_kg_cm2 = q_max_ton_m2 / 10.0
    q_min_kg_cm2 = q_min_ton_m2 / 10.0
    ratio_soil = q_max_kg_cm2 / max(q_all_kg_cm2, 0.01)
    is_soil_safe = (ratio_soil <= 1.0001) and (q_min_kg_cm2 >= 0.0)

    # Punching Shear & One-Way Shear Checks (ECP 203)
    d_cm = max(tf_m * 100.0 - cover_cm, 10.0)
    d_m = d_cm / 100.0
    fcu_mpa = fc_kg_cm2 / 10.0
    gamma_c_mat = 1.50
    gamma_s_mat = 1.15

    if is_circular:
        bo_m = math.pi * (D_tank_m + d_m)
        area_punch_m2 = (math.pi / 4.0) * ((D_tank_m + d_m) ** 2)
    else:
        bo_m = 2.0 * ((L_tank_m + d_m) + (B_tank_m + d_m))
        area_punch_m2 = (L_tank_m + d_m) * (B_tank_m + d_m)

    qu_net_ton_m2 = Pu_net_ton / Af_m2
    # Shell wall reaction + overhang net upward soil shear
    W_shell_ult_ton = 1.40 * W_tank_empty_ton + 0.15 * (1.50 * W_liquid_ton)
    Q_up_overhang_ton = max(0.0, Pu_net_ton - qu_net_ton_m2 * min(area_punch_m2, Af_m2))
    Q_up_ton = max(W_shell_ult_ton, Q_up_overhang_ton)

    q_up_kg_cm2 = (Q_up_ton * 1000.0) / (bo_m * 100.0 * d_cm)
    q_cup_all_kg_cm2 = min(0.316 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0, 16.0)
    ratio_punching = q_up_kg_cm2 / max(q_cup_all_kg_cm2, 0.01)
    is_punching_safe = ratio_punching <= 1.0001

    # One-Way Shear Check at d from Tank Wall
    shear_span_m = max(overhang_m - d_m, 0.15 * min(L_tank_m, B_tank_m))
    Qu_1way_ton_m = qu_net_ton_m2 * shear_span_m * 0.35
    qu_1way_kg_cm2 = (Qu_1way_ton_m * 1000.0) / (100.0 * d_cm)
    qcu_1way_kg_cm2 = 0.16 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    ratio_1way_shear = qu_1way_kg_cm2 / max(qcu_1way_kg_cm2, 0.01)
    is_1way_shear_safe = ratio_1way_shear <= 1.0001

    # Flexural Design (Hydrostatic + Overhang + Edge Shell Wall Effect + Uplift)
    # 1. Cantilever moment at tank wall edge:
    Mu_cant_tm = qu_net_ton_m2 * (overhang_m ** 2) / 2.0 + (W_shell_ult_ton / perimeter_tank_m) * (overhang_m * 0.50)
    # 2. Interior slab radial/longitudinal moment under hydrostatic pressure & soil subgrade interaction:
    span_ref_m = D_tank_m if is_circular else min(L_tank_m, B_tank_m)
    Mu_interior_pos_tm = max(Mu_cant_tm, 0.035 * (1.50 * p_hydrostatic_ton_m2) * (span_ref_m ** 2))
    # 3. Top Moment (Negative moment from shell fixity / groundwater uplift when empty):
    q_uplift_ult_ton_m2 = 1.40 * max(0.0, gwt_depth_m * gamma_water)
    Mu_top_neg_tm = max(0.65 * Mu_interior_pos_tm, 0.045 * q_uplift_ult_ton_m2 * (span_ref_m ** 2), 1.50)

    # Water-tightness / Crack Control factor per ECP 203 Liquid Structures (reduce fs or multiply moment by 1.25)
    crack_control_factor = 1.20
    j_factor = 0.826
    fy_design = fy_kg_cm2 / gamma_s_mat

    As_bot_flex_cm2_m = (Mu_interior_pos_tm * crack_control_factor * 1e5) / (fy_design * j_factor * d_cm)
    As_top_flex_cm2_m = (Mu_top_neg_tm * crack_control_factor * 1e5) / (fy_design * j_factor * d_cm)

    # ECP 203 Minimum Rebar for Liquid Retaining Foundations (0.20% for crack control or min 6Φ12/m)
    As_min_bot_cm2_m = max(0.0018 * 100.0 * d_cm, 6.78)
    As_min_top_cm2_m = max(0.0015 * 100.0 * d_cm, 5.65)

    As_bot_req_cm2_m = max(As_bot_flex_cm2_m, As_min_bot_cm2_m)
    As_top_req_cm2_m = max(As_top_flex_cm2_m, As_min_top_cm2_m)

    area_bar_bot = BAR_AREAS.get(phi_bot_mm, (math.pi * (phi_bot_mm / 10.0) ** 2) / 4.0)
    area_bar_top = BAR_AREAS.get(phi_top_mm, (math.pi * (phi_top_mm / 10.0) ** 2) / 4.0)

    n_bars_bot_m = max(5, math.ceil(As_bot_req_cm2_m / area_bar_bot))
    n_bars_top_m = max(5, math.ceil(As_top_req_cm2_m / area_bar_top))

    spacing_bot_cm = round(100.0 / n_bars_bot_m, 1)
    spacing_top_cm = round(100.0 / n_bars_top_m, 1)

    As_bot_prov_cm2_m = n_bars_bot_m * area_bar_bot
    As_top_prov_cm2_m = n_bars_top_m * area_bar_top

    # Total Steel Weight in Tank Foundation
    wt_bar_bot_kg_m = BAR_WEIGHTS.get(phi_bot_mm, (phi_bot_mm ** 2) / 162.0)
    wt_bar_top_kg_m = BAR_WEIGHTS.get(phi_top_mm, (phi_top_mm ** 2) / 162.0)

    # Equivalent weight per m² for orthogonal/radial-tangential 2-directional mesh
    wt_bot_per_m2 = 2.0 * n_bars_bot_m * wt_bar_bot_kg_m
    wt_top_per_m2 = 2.0 * n_bars_top_m * wt_bar_top_kg_m

    weight_bot_kg = wt_bot_per_m2 * Af_m2 * 1.08  # +8% hooks & laps
    weight_top_kg = wt_top_per_m2 * Af_m2 * 1.08

    total_rebar_weight_kg = weight_bot_kg + weight_top_kg
    total_rebar_weight_ton = total_rebar_weight_kg / 1000.0
    steel_rate_kg_m3 = total_rebar_weight_kg / max(vol_f_m3, 0.01)

    is_all_safe = (
        is_soil_safe
        and is_punching_safe
        and is_1way_shear_safe
        and is_overturning_safe
        and is_buoyancy_safe
    )

    return {
        "tank_shape": tank_shape,
        "is_circular": is_circular,
        "D_tank_m": D_tank_m,
        "L_tank_m": L_tank_m,
        "B_tank_m": B_tank_m,
        "A_tank_m2": A_tank_m2,
        "H_liquid_m": H_liquid_m,
        "H_tank_total_m": H_tank_total_m,
        "tank_material": tank_material,
        "is_steel": is_steel,
        "sheet_thk_mm": sheet_thk_mm,
        "capacity_barrels": capacity_barrels,
        "vol_liquid_m3": vol_liquid_m3,
        "specific_gravity": specific_gravity,
        "gamma_liquid_ton_m3": gamma_liquid_ton_m3,
        "W_tank_empty_ton": W_tank_empty_ton,
        "W_liquid_ton": W_liquid_ton,
        "p_hydrostatic_ton_m2": p_hydrostatic_ton_m2,
        "p_hydrostatic_kg_cm2": p_hydrostatic_kg_cm2,
        "fc_kg_cm2": fc_kg_cm2,
        "fy_kg_cm2": fy_kg_cm2,
        "q_all_kg_cm2": q_all_kg_cm2,
        "q_all_ton_m2": q_all_ton_m2,
        "sizing_mode": sizing_mode,
        "overhang_m": overhang_m,
        "Df_m": Df_m,
        "Lf_m": Lf_m,
        "Bf_m": Bf_m,
        "tf_m": tf_m,
        "tf_cm": tf_m * 100.0,
        "d_cm": d_cm,
        "cover_cm": cover_cm,
        "Af_m2": Af_m2,
        "vol_f_m3": vol_f_m3,
        "Wf_ton": Wf_ton,
        "P_total_working_ton": P_total_working_ton,
        "Pu_total_ton": Pu_total_ton,
        "Pu_net_ton": Pu_net_ton,
        "gwt_depth_m": gwt_depth_m,
        "wind_seismic_coeff": wind_seismic_coeff,
        "V_lateral_ton": V_lateral_ton,
        "M_overturning_tm": M_overturning_tm,
        "M_resisting_full_tm": M_resisting_full_tm,
        "fos_overturning": fos_overturning,
        "is_overturning_safe": is_overturning_safe,
        "U_buoyancy_ton": U_buoyancy_ton,
        "W_empty_total_ton": W_empty_total_ton,
        "fos_buoyancy": fos_buoyancy,
        "is_buoyancy_safe": is_buoyancy_safe,
        "q_avg_ton_m2": q_avg_ton_m2,
        "q_max_ton_m2": q_max_ton_m2,
        "q_min_ton_m2": q_min_ton_m2,
        "q_max_kg_cm2": q_max_kg_cm2,
        "q_min_kg_cm2": q_min_kg_cm2,
        "ratio_soil": ratio_soil,
        "is_soil_safe": is_soil_safe,
        "bo_m": bo_m,
        "Q_up_ton": Q_up_ton,
        "q_up_kg_cm2": q_up_kg_cm2,
        "q_cup_all_kg_cm2": q_cup_all_kg_cm2,
        "ratio_punching": ratio_punching,
        "is_punching_safe": is_punching_safe,
        "Qu_1way_ton_m": Qu_1way_ton_m,
        "qu_1way_kg_cm2": qu_1way_kg_cm2,
        "qcu_1way_kg_cm2": qcu_1way_kg_cm2,
        "ratio_1way_shear": ratio_1way_shear,
        "is_1way_shear_safe": is_1way_shear_safe,
        "Mu_interior_pos_tm": Mu_interior_pos_tm,
        "Mu_top_neg_tm": Mu_top_neg_tm,
        "As_bot_req_cm2_m": As_bot_req_cm2_m,
        "As_top_req_cm2_m": As_top_req_cm2_m,
        "phi_bot_mm": phi_bot_mm,
        "phi_top_mm": phi_top_mm,
        "n_bars_bot_m": n_bars_bot_m,
        "n_bars_top_m": n_bars_top_m,
        "spacing_bot_cm": spacing_bot_cm,
        "spacing_top_cm": spacing_top_cm,
        "As_bot_prov_cm2_m": As_bot_prov_cm2_m,
        "As_top_prov_cm2_m": As_top_prov_cm2_m,
        "weight_bot_kg": weight_bot_kg,
        "weight_top_kg": weight_top_kg,
        "total_rebar_weight_kg": total_rebar_weight_kg,
        "total_rebar_weight_ton": total_rebar_weight_ton,
        "steel_rate_kg_m3": steel_rate_kg_m3,
        "is_all_safe": is_all_safe,
    }


# ===============================================================================
#  3. 2D CAD ENGINEERING SKETCH GENERATORS (EQUIPMENT & LIQUID TANK)
# ===============================================================================

def generate_equipment_foundation_sketches(res: dict) -> str:
    """Generates a high-resolution 2-panel CAD blueprint (Plan + Section) for Equipment Foundation."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.8), dpi=130)
    fig.patch.set_facecolor("#0b1329")

    for ax in (ax1, ax2):
        ax.set_facecolor("#0f172a")
        for spine in ax.spines.values():
            spine.set_color("#334155")
            spine.set_linewidth(1.5)

    Lf = res["Lf_m"]
    Bf = res["Bf_m"]
    tf = res["tf_m"]
    Lm = res["Lm_m"]
    Bm = res["Bm_m"]
    d_m = res["d_cm"] / 100.0

    # --- Panel 1: Top Plan View ---
    ax1.set_title("1. Top Plan View & Critical Punching Perimeter", color="#38bdf8", fontsize=13, fontweight="bold", pad=12)
    rect_f = Rectangle((-Lf / 2, -Bf / 2), Lf, Bf, facecolor="#1e293b", edgecolor="#38bdf8", linewidth=2.5, label="RC Foundation")
    ax1.add_patch(rect_f)

    # Rebar grid lines in Plan
    nx_lines = np.linspace(-Lf / 2 + 0.15, Lf / 2 - 0.15, 9)
    ny_lines = np.linspace(-Bf / 2 + 0.15, Bf / 2 - 0.15, 7)
    for xl in nx_lines:
        ax1.plot([xl, xl], [-Bf / 2 + 0.08, Bf / 2 - 0.08], color="#22c55e", alpha=0.30, linewidth=1.0, linestyle="--")
    for yl in ny_lines:
        ax1.plot([-Lf / 2 + 0.08, Lf / 2 - 0.08], [yl, yl], color="#22c55e", alpha=0.30, linewidth=1.0, linestyle="--")

    # Punching perimeter at d/2
    if res["is_circular_eq"]:
        cir_p = Circle((0, 0), radius=(Lm + d_m) / 2, facecolor="none", edgecolor="#f59e0b", linewidth=2.0, linestyle="-.")
        cir_m = Circle((0, 0), radius=Lm / 2, facecolor="#334155", edgecolor="#f87171", linewidth=2.2)
        ax1.add_patch(cir_p)
        ax1.add_patch(cir_m)
    else:
        Lp = min(Lm + d_m, Lf - 0.05)
        Bp = min(Bm + d_m, Bf - 0.05)
        rect_p = Rectangle((-Lp / 2, -Bp / 2), Lp, Bp, facecolor="none", edgecolor="#f59e0b", linewidth=2.0, linestyle="-.")
        rect_m = Rectangle((-Lm / 2, -Bm / 2), Lm, Bm, facecolor="#334155", edgecolor="#f87171", linewidth=2.2)
        ax1.add_patch(rect_p)
        ax1.add_patch(rect_m)

    # Dimension annotations (separated cleanly from dimension line & arrows)
    dim_offset_y = max(0.32, Bf * 0.14)
    text_offset_y = dim_offset_y + max(0.24, Bf * 0.11)
    ax1.annotate("", xy=(-Lf / 2, -Bf / 2 - dim_offset_y), xytext=(Lf / 2, -Bf / 2 - dim_offset_y),
                 arrowprops=dict(arrowstyle="<->", color="#e2e8f0", lw=1.8))
    ax1.text(0, -Bf / 2 - text_offset_y, f"Lf = {Lf:.2f} m", color="#ffffff", fontsize=11, fontweight="bold",
             ha="center", va="top", bbox=dict(boxstyle="round,pad=0.25", facecolor="#0f172a", edgecolor="#38bdf8", lw=1.0))

    dim_offset_x = max(0.32, Lf * 0.14)
    text_offset_x = dim_offset_x + max(0.26, Lf * 0.11)
    ax1.annotate("", xy=(-Lf / 2 - dim_offset_x, -Bf / 2), xytext=(-Lf / 2 - dim_offset_x, Bf / 2),
                 arrowprops=dict(arrowstyle="<->", color="#e2e8f0", lw=1.8))
    ax1.text(-Lf / 2 - text_offset_x, 0, f"Bf = {Bf:.2f} m", color="#ffffff", fontsize=11, fontweight="bold",
             ha="right", va="center", rotation=90, bbox=dict(boxstyle="round,pad=0.25", facecolor="#0f172a", edgecolor="#38bdf8", lw=1.0))

    ax1.text(0, 0, f"Equipment\n{Lm:.2f}×{Bm:.2f} m\nW = {res['eq_weight_ton']:.1f} t",
             color="#fde047", fontsize=10, fontweight="bold", ha="center", va="center")

    margin_x = text_offset_x + max(0.45, Lf * 0.16)
    margin_y = text_offset_y + max(0.45, Bf * 0.16)
    ax1.set_xlim(-Lf / 2 - margin_x, Lf / 2 + max(0.40, Lf * 0.18))
    ax1.set_ylim(-Bf / 2 - margin_y, Bf / 2 + max(0.40, Bf * 0.18))
    ax1.set_aspect("equal", "box")
    ax1.axis("off")

    # --- Panel 2: Structural Cross-Section & Rebar Cage ---
    ax2.set_title("2. Cross-Section & Top/Bottom Rebar Detailing", color="#38bdf8", fontsize=13, fontweight="bold", pad=12)

    # Soil Subgrade Hatch
    soil_rect = Rectangle((-Lf / 2 - 0.4, -0.35), Lf + 0.8, 0.35, facecolor="#422006", edgecolor="#ca8a04", hatch="//", alpha=0.6)
    ax2.add_patch(soil_rect)

    # Concrete Foundation Block
    conc_rect = Rectangle((-Lf / 2, 0), Lf, tf, facecolor="#334155", edgecolor="#94a3b8", linewidth=2.5)
    ax2.add_patch(conc_rect)

    # Rebar Cage (Bottom & Top U-Bars)
    cov_m = res["cover_cm"] / 100.0
    ax2.plot([-Lf / 2 + cov_m, Lf / 2 - cov_m], [cov_m, cov_m], color="#4ade80", linewidth=3.2, label="Bottom Mesh")
    ax2.plot([-Lf / 2 + cov_m, Lf / 2 - cov_m], [tf - cov_m, tf - cov_m], color="#38bdf8", linewidth=2.8, label="Top Mesh")
    ax2.plot([-Lf / 2 + cov_m, -Lf / 2 + cov_m], [cov_m, tf - cov_m], color="#4ade80", linewidth=2.5)
    ax2.plot([Lf / 2 - cov_m, Lf / 2 - cov_m], [cov_m, tf - cov_m], color="#4ade80", linewidth=2.5)

    # Isolators / Springs or Anchor Bolts
    eq_base_y = tf + (0.18 if res["is_isolated"] else 0.04)
    if res["is_isolated"]:
        n_sp = 4
        sp_xs = np.linspace(-Lm / 2 + 0.15, Lm / 2 - 0.15, n_sp)
        for sx in sp_xs:
            ax2.plot([sx, sx], [tf, eq_base_y], color="#facc15", linewidth=3.5, linestyle=":")
            ax2.add_patch(Rectangle((sx - 0.08, tf), 0.16, 0.04, facecolor="#eab308"))
    else:
        for ax_x in (-Lm / 2 + 0.15, Lm / 2 - 0.15):
            ax2.plot([ax_x, ax_x], [tf - 0.50 * tf, tf + 0.12], color="#f87171", linewidth=2.5)

    # Equipment Body
    eq_h = max(0.55, 0.45 * tf)
    eq_rect = FancyBboxPatch((-Lm / 2, eq_base_y), Lm, eq_h, boxstyle="round,pad=0.02", facecolor="#1e3a8a", edgecolor="#60a5fa", linewidth=2.2)
    ax2.add_patch(eq_rect)
    ax2.text(0, eq_base_y + eq_h / 2, f"Mechanical Equipment\nP_op = {res['eq_weight_ton']:.1f} ton (DF = {res['dyn_factor']:.2f})",
             color="#ffffff", fontsize=10, fontweight="bold", ha="center", va="center")

    # Rebar & Thickness Callouts
    ax2.text(0, cov_m + 0.06 * tf, f"Bottom: {res['n_bars_bot_m']} Φ {res['phi_bot_mm']}/m' (As = {res['As_bot_prov_cm2_m']:.2f} cm²/m')",
             color="#4ade80", fontsize=10, fontweight="bold", ha="center")
    ax2.text(0, tf - cov_m - 0.10 * tf, f"Top: {res['n_bars_top_m']} Φ {res['phi_top_mm']}/m' (As = {res['As_top_prov_cm2_m']:.2f} cm²/m')",
             color="#38bdf8", fontsize=10, fontweight="bold", ha="center")
    ax2.text(0, -0.22, f"q_act = {res['q_act_kg_cm2']:.2f} kg/cm² ≤ q_all = {res['q_all_kg_cm2']:.2f} kg/cm² | W_f (Self) = {res['Wf_ton']:.2f} ton",
             color="#fde047", fontsize=10, fontweight="bold", ha="center")

    tf_dim_x = Lf / 2 + max(0.28, Lf * 0.08)
    tf_txt_x = tf_dim_x + max(0.22, Lf * 0.07)
    ax2.annotate("", xy=(tf_dim_x, 0), xytext=(tf_dim_x, tf),
                 arrowprops=dict(arrowstyle="<->", color="#f87171", lw=2.0))
    ax2.text(tf_txt_x, tf / 2, f"tf = {tf:.2f} m", color="#f87171", fontsize=11, fontweight="bold",
             ha="left", va="center", rotation=90, bbox=dict(boxstyle="round,pad=0.2", facecolor="#0f172a", edgecolor="#f87171", lw=1.0))

    ax2.set_xlim(-Lf / 2 - max(0.85, Lf * 0.20), tf_txt_x + max(0.55, Lf * 0.14))
    ax2.set_ylim(-0.55, eq_base_y + eq_h + 0.35)
    ax2.axis("off")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_liquid_tank_foundation_sketches(res: dict) -> str:
    """Generates a high-resolution 2-panel CAD blueprint (Plan + Section) for Liquid Storage Tank Foundation."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.8), dpi=130)
    fig.patch.set_facecolor("#0b1329")

    for ax in (ax1, ax2):
        ax.set_facecolor("#0f172a")
        for spine in ax.spines.values():
            spine.set_color("#334155")
            spine.set_linewidth(1.5)

    Lf = res["Lf_m"]
    Bf = res["Bf_m"]
    tf = res["tf_m"]
    Lt = res["L_tank_m"]
    Bt = res["B_tank_m"]

    # --- Panel 1: Foundation & Tank Plan View ---
    ax1.set_title("1. Tank & Foundation Plan View (ECP 203 / ACI 350)", color="#38bdf8", fontsize=13, fontweight="bold", pad=12)

    if res["is_circular"]:
        cir_f = Circle((0, 0), radius=Lf / 2, facecolor="#1e293b", edgecolor="#38bdf8", linewidth=2.5)
        cir_t = Circle((0, 0), radius=Lt / 2, facecolor="#0284c7", alpha=0.35, edgecolor="#fde047", linewidth=2.5)
        ax1.add_patch(cir_f)
        ax1.add_patch(cir_t)
        # Radial & Tangential Rebar schematic lines
        for r_rad in np.linspace(0.25 * Lf / 2, 0.90 * Lf / 2, 4):
            ax1.add_patch(Circle((0, 0), radius=r_rad, facecolor="none", edgecolor="#4ade80", alpha=0.30, linestyle="--"))
        for ang in np.linspace(0, np.pi, 6, endpoint=False):
            x_r = (Lf / 2 - 0.1) * np.cos(ang)
            y_r = (Lf / 2 - 0.1) * np.sin(ang)
            ax1.plot([-x_r, x_r], [-y_r, y_r], color="#4ade80", alpha=0.25, linewidth=1.0)
        dim_lbl = f"Df = {Lf:.2f} m (D_tank = {Lt:.2f} m)"
    else:
        rect_f = Rectangle((-Lf / 2, -Bf / 2), Lf, Bf, facecolor="#1e293b", edgecolor="#38bdf8", linewidth=2.5)
        rect_t = Rectangle((-Lt / 2, -Bt / 2), Lt, Bt, facecolor="#0284c7", alpha=0.35, edgecolor="#fde047", linewidth=2.5)
        ax1.add_patch(rect_f)
        ax1.add_patch(rect_t)
        for xl in np.linspace(-Lf / 2 + 0.2, Lf / 2 - 0.2, 8):
            ax1.plot([xl, xl], [-Bf / 2 + 0.1, Bf / 2 - 0.1], color="#4ade80", alpha=0.28, linestyle="--")
        for yl in np.linspace(-Bf / 2 + 0.2, Bf / 2 - 0.2, 6):
            ax1.plot([-Lf / 2 + 0.1, Lf / 2 - 0.1], [yl, yl], color="#4ade80", alpha=0.28, linestyle="--")
        dim_lbl = f"Lf × Bf = {Lf:.2f} × {Bf:.2f} m"

    ax1.text(0, 0, f"Liquid Storage Tank\n{res['capacity_barrels']:.0f} BBL ({res['vol_liquid_m3']:.1f} m³)\nW_liq = {res['W_liquid_ton']:.1f} t",
             color="#ffffff", fontsize=10, fontweight="bold", ha="center", va="center")

    dim_offset_y = max(0.35, Bf * 0.12)
    text_offset_y = dim_offset_y + max(0.26, Bf * 0.09)
    ax1.annotate("", xy=(-Lf / 2, -Bf / 2 - dim_offset_y), xytext=(Lf / 2, -Bf / 2 - dim_offset_y),
                 arrowprops=dict(arrowstyle="<->", color="#e2e8f0", lw=1.8))
    ax1.text(0, -Bf / 2 - text_offset_y, dim_lbl, color="#fde047", fontsize=11, fontweight="bold",
             ha="center", va="top", bbox=dict(boxstyle="round,pad=0.25", facecolor="#0f172a", edgecolor="#38bdf8", lw=1.0))

    if not res["is_circular"]:
        dim_offset_x = max(0.35, Lf * 0.12)
        text_offset_x = dim_offset_x + max(0.28, Lf * 0.09)
        ax1.annotate("", xy=(-Lf / 2 - dim_offset_x, -Bf / 2), xytext=(-Lf / 2 - dim_offset_x, Bf / 2),
                     arrowprops=dict(arrowstyle="<->", color="#e2e8f0", lw=1.8))
        ax1.text(-Lf / 2 - text_offset_x, 0, f"Bf = {Bf:.2f} m", color="#fde047", fontsize=11, fontweight="bold",
                 ha="right", va="center", rotation=90, bbox=dict(boxstyle="round,pad=0.25", facecolor="#0f172a", edgecolor="#38bdf8", lw=1.0))
        margin_x = text_offset_x + max(0.45, Lf * 0.14)
    else:
        margin_x = max(Lf, Bf) * 0.30

    margin_y = text_offset_y + max(0.45, Bf * 0.14)
    ax1.set_xlim(-Lf / 2 - margin_x, Lf / 2 + max(0.40, Lf * 0.18))
    ax1.set_ylim(-Bf / 2 - margin_y, Bf / 2 + max(0.40, Bf * 0.18))
    ax1.set_aspect("equal", "box")
    ax1.axis("off")

    # --- Panel 2: Elevation Section (Tank + Liquid + RC Foundation) ---
    ax2.set_title("2. Structural Elevation, Hydrostatic Load & Rebar Mesh", color="#38bdf8", fontsize=13, fontweight="bold", pad=12)

    H_draw_tank = min(max(res["H_tank_total_m"] * 0.35, 1.20), 2.60)
    H_draw_liq = H_draw_tank * (res["H_liquid_m"] / max(res["H_tank_total_m"], 0.1))

    # Subgrade
    ax2.add_patch(Rectangle((-Lf / 2 - 0.5, -0.35), Lf + 1.0, 0.35, facecolor="#422006", edgecolor="#ca8a04", hatch="//", alpha=0.6))

    # RC Foundation Slab
    ax2.add_patch(Rectangle((-Lf / 2, 0), Lf, tf, facecolor="#334155", edgecolor="#94a3b8", linewidth=2.5))

    # Rebar Top & Bottom
    cov_m = min(res["cover_cm"] / 100.0, tf * 0.2)
    ax2.plot([-Lf / 2 + cov_m, Lf / 2 - cov_m], [cov_m, cov_m], color="#4ade80", linewidth=3.0)
    ax2.plot([-Lf / 2 + cov_m, Lf / 2 - cov_m], [tf - cov_m, tf - cov_m], color="#38bdf8", linewidth=2.8)

    # Tank Shell & Liquid Fill
    ax2.add_patch(Rectangle((-Lt / 2, tf), Lt, H_draw_liq, facecolor="#0284c7", alpha=0.55, edgecolor="none"))
    ax2.add_patch(Rectangle((-Lt / 2, tf), Lt, H_draw_tank, facecolor="none", edgecolor="#fde047", linewidth=2.8))

    # Labels
    ax2.text(0, tf + H_draw_liq / 2,
             f"Stored Liquid (SG = {res['specific_gravity']:.2f})\nH_liq = {res['H_liquid_m']:.2f} m | p_hyd = {res['p_hydrostatic_ton_m2']:.2f} t/m²\nW_liquid = {res['W_liquid_ton']:.2f} ton",
             color="#ffffff", fontsize=9.5, fontweight="bold", ha="center", va="center")
    ax2.text(0, tf / 2,
             f"RC Foundation (tf = {tf:.2f} m, W_f = {res['Wf_ton']:.2f} ton)\nBot: {res['n_bars_bot_m']}Φ{res['phi_bot_mm']}/m' | Top: {res['n_bars_top_m']}Φ{res['phi_top_mm']}/m'",
             color="#4ade80", fontsize=9.5, fontweight="bold", ha="center", va="center")
    ax2.text(0, -0.22,
             f"q_max = {res['q_max_kg_cm2']:.2f} kg/cm² ≤ {res['q_all_kg_cm2']:.2f} kg/cm² | FOS_overturn = {res['fos_overturning']:.2f} | FOS_uplift = {res['fos_buoyancy']:.2f}",
             color="#fde047", fontsize=9.5, fontweight="bold", ha="center")

    ax2.set_xlim(-Lf / 2 - 0.9, Lf / 2 + 0.9)
    ax2.set_ylim(-0.55, tf + H_draw_tank + 0.45)
    ax2.axis("off")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ===============================================================================
#  4. STANDALONE HTML/PDF CALCULATION SHEET GENERATOR
# ===============================================================================

def generate_m10_calculation_sheet_html(title_ar: str, subtitle_en: str, rows_summary: list, checks_list: list, sketch_b64: str) -> str:
    """Generates a clean, print-ready Arabic RTL HTML calculation report for Module 10."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    summary_trs = "".join(
        f"<tr><td style='padding:8px 12px; font-weight:700; border:1px solid #cbd5e1;'>{k}</td>"
        f"<td style='padding:8px 12px; font-weight:800; color:#1e40af; border:1px solid #cbd5e1;' dir='ltr'>{v}</td></tr>"
        for k, v in rows_summary
    )
    checks_trs = "".join(
        f"<tr>"
        f"<td style='padding:8px 12px; font-weight:700; border:1px solid #cbd5e1;'>{item}</td>"
        f"<td style='padding:8px 12px; text-align:center; border:1px solid #cbd5e1;' dir='ltr'>{act}</td>"
        f"<td style='padding:8px 12px; text-align:center; border:1px solid #cbd5e1;' dir='ltr'>{lim}</td>"
        f"<td style='padding:8px 12px; text-align:center; font-weight:800; color:{'#15803d' if ok else '#b91c1c'}; border:1px solid #cbd5e1;'>{'✅ SAFE' if ok else '⚠️ UNSAFE'}</td>"
        f"</tr>"
        for item, act, lim, ok in checks_list
    )
    img_block = f'<div style="text-align:center; margin:18px 0;"><img src="data:image/png;base64,{sketch_b64}" style="max-width:100%; border:1.5px solid #1e3a8a; border-radius:8px;"/><div class="drawing-caption">{title_ar} — {subtitle_en}</div></div>' if sketch_b64 else ""

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<title>{title_ar}</title>
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; margin: 24px; color: #0f172a; background: #ffffff; direction: rtl; }}
    .hdr {{ background: linear-gradient(135deg, #0f172a, #1e3a8a); color: #fff; padding: 18px 24px; border-radius: 10px; margin-bottom: 20px; }}
    .hdr h1 {{ margin: 0 0 6px 0; font-size: 22px; color: #fde047; }}
    .hdr p {{ margin: 0; font-size: 13px; color: #e2e8f0; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; }}
    th {{ background: #1e293b; color: #ffffff; padding: 10px 12px; border: 1px solid #cbd5e1; text-align: right; }}
    .drawing-caption {{ font-size: 12px; color: #475569; margin-top: 6px; font-weight: bold; }}
</style>
</head>
<body>
    <div class="hdr">
        <h1>{title_ar}</h1>
        <p>{subtitle_en} | الكود المصري ECP 203 & ACI | تاريخ التقرير: {now_str}</p>
    </div>
    <h3>1. ملخص البيانات الهندسية والأوزان والأبعاد والتسليح (Design Summary)</h3>
    <table>
        <thead><tr><th>البند الهندسي (Parameter)</th><th>القيمة المعتمدة (Design Value)</th></tr></thead>
        <tbody>{summary_trs}</tbody>
    </table>
    <h3>2. جدول التحققات الكودية والاتزان (Code Verification Checks)</h3>
    <table>
        <thead><tr><th>بند التحقق (Check)</th><th>القيمة الفعلية (Actual)</th><th>الحد الكودي (Allowable)</th><th>الحالة (Status)</th></tr></thead>
        <tbody>{checks_trs}</tbody>
    </table>
    {img_block}
</body>
</html>"""


# ===============================================================================
#  5. STREAMLIT UI RENDERER — SECTION 1: EQUIPMENT FOUNDATIONS
# ===============================================================================

def _render_equipment_foundations_tab():
    st.markdown(
        """
        <div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #0f172a 100%); border: 2px solid #38bdf8; border-radius: 12px; padding: 16px 22px; margin-bottom: 18px; box-shadow: 0 4px 18px rgba(56, 189, 248, 0.2);">
            <div style="font-size: 20px; font-weight: 900; color: #fde047; margin-bottom: 6px; direction: rtl !important; text-align: right !important;">
                ⚙️ أولاً: تصميم القواعد الإنشائية للمعدات الميكانيكية الثابتة والديناميكية (Equipment Foundation Design)
            </div>
            <div style="font-size: 14.5px; color: #e2e8f0; line-height: 1.75; font-weight: 600; direction: rtl !important; text-align: right !important;">
                تصميم متكامل لقواعد الماكينات والمضخات والضواغط والمولدات وفقاً للكود المصري <span dir="ltr">ECP 203</span> و <span dir="ltr">ACI 351.3R</span>، مع الحساب التلقائي للوزن الذاتي للقاعدة (<span dir="ltr">γc = 2.5 t/m³</span>) ومعالجة الأحمال الاهتزازية في حالتي وجود نظام عزل (<span dir="ltr">Springs & Isolators</span>) أو القاعدة الثابتة (<span dir="ltr">Fixed Base</span>).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📥 1. مدخلات المعدة والتربة والمواد ونظام العزل (Equipment, Materials & Soil Inputs)", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#38bdf8; margin-bottom:10px;'>⚙️ 1. بيانات المعدة (Equipment Data)</div>", unsafe_allow_html=True)
            eq_weight = S.number_input(
                "الوزن التشغيلي للمعدة (Operating Weight) [ton]:",
                "m10_eq_weight_ton",
                value=15.0,
                min_value=0.5,
                max_value=500.0,
                step=0.5,
            )
            eq_shape = S.selectbox(
                "الشكل الهندسي لبصمة المعدة (Footprint Shape):",
                "m10_eq_shape",
                ["مستطيلة (Rectangular)", "دائرية (Circular)"],
            )
            if "دائرية" in eq_shape:
                eq_dia = S.number_input(
                    "قطر قاعدة المعدة D_eq [m]:",
                    "m10_eq_dia_m",
                    value=2.00,
                    min_value=0.30,
                    max_value=20.0,
                    step=0.10,
                )
                eq_len, eq_wid = eq_dia, eq_dia
            else:
                col_l, col_b = st.columns(2)
                with col_l:
                    eq_len = S.number_input(
                        "طول المعدة L_eq [m]:",
                        "m10_eq_len_m",
                        value=2.50,
                        min_value=0.30,
                        max_value=25.0,
                        step=0.10,
                    )
                with col_b:
                    eq_wid = S.number_input(
                        "عرض المعدة B_eq [m]:",
                        "m10_eq_wid_m",
                        value=1.50,
                        min_value=0.30,
                        max_value=25.0,
                        step=0.10,
                    )
                eq_dia = eq_len

        with c2:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#38bdf8; margin-bottom:10px;'>🧱 2. خواص المواد والتربة (Materials & Soil)</div>", unsafe_allow_html=True)
            fc_eq = S.number_input(
                "إجهاد الخرسانة fc' / fcu [kg/cm²]:",
                "m10_eq_fc",
                value=300.0,
                min_value=200.0,
                max_value=600.0,
                step=25.0,
            )
            fy_eq = S.number_input(
                "إجهاد حديد التسليح fy [kg/cm²]:",
                "m10_eq_fy",
                value=3600.0,
                min_value=2400.0,
                max_value=5000.0,
                step=200.0,
            )
            q_all_eq = S.number_input(
                "إجهاد التحمل المسموح للتربة q_all [kg/cm²]:",
                "m10_eq_q_all",
                value=1.50,
                min_value=0.40,
                max_value=6.00,
                step=0.10,
                help="1.0 kg/cm² = 10 ton/m²",
            )
            ks_eq = S.number_input(
                "معامل رد فعل التربة الديناميكي ks [kg/cm³]:",
                "m10_eq_ks",
                value=4.0,
                min_value=1.0,
                max_value=20.0,
                step=0.5,
            )

        with c3:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#38bdf8; margin-bottom:10px;'>📳 3. نظام العزل الاهتزازي والأبعاد</div>", unsafe_allow_html=True)
            iso_type = S.selectbox(
                "حالة العزل الديناميكي (Vibration Isolation):",
                "m10_eq_iso_type",
                [
                    "وجود نظام عزل اهتزازات (Springs & Isolators)",
                    "عدم وجود نظام عزل - قاعدة ثابتة (Fixed Base)",
                ],
            )
            op_rpm = S.number_input(
                "سرعة دوران التشغيل (Operating Speed) [RPM]:",
                "m10_eq_rpm",
                value=1500.0,
                min_value=100.0,
                max_value=10000.0,
                step=100.0,
            )
            if "Fixed Base" in iso_type or "عدم وجود" in iso_type:
                mass_ratio_target = S.number_input(
                    "نسبة وزن القاعدة لوزن المعدة (2.0 إلى 3.0 أضعاف):",
                    "m10_eq_mass_ratio",
                    value=2.50,
                    min_value=2.00,
                    max_value=3.00,
                    step=0.10,
                )
            else:
                mass_ratio_target = 2.50

            sizing_mode_eq = S.selectbox(
                "نظام تحديد أبعاد القاعدة الخرسانية:",
                "m10_eq_sizing_mode",
                ["حساب أوتوماتيكي للأبعاد (Auto-Sizing)", "إدخال يدوي للأبعاد (Manual Override)"],
            )

        st.markdown("---")
        c_reb1, c_reb2, c_reb3, c_reb4 = st.columns(4)
        with c_reb1:
            phi_bot_eq = S.selectbox("قطر التسليح السفلي Φ_bot [mm]:", "m10_eq_phi_bot", ECP_DIAMETERS, index=2)
        with c_reb2:
            phi_top_eq = S.selectbox("قطر التسليح العلوي Φ_top [mm]:", "m10_eq_phi_top", ECP_DIAMETERS, index=1)
        with c_reb3:
            cover_eq = S.number_input("الغطاء الخرساني Cover [cm]:", "m10_eq_cover", value=7.5, min_value=5.0, max_value=12.0, step=0.5)
        with c_reb4:
            if "Manual" in sizing_mode_eq or "يدوي" in sizing_mode_eq:
                m_c1, m_c2, m_c3 = st.columns(3)
                with m_c1:
                    man_Lf = S.number_input("الطول Lf [m]:", "m10_eq_man_Lf", value=3.50, min_value=1.0, max_value=30.0, step=0.10)
                with m_c2:
                    man_Bf = S.number_input("العرض Bf [m]:", "m10_eq_man_Bf", value=2.50, min_value=1.0, max_value=30.0, step=0.10)
                with m_c3:
                    man_tf = S.number_input("السمك tf [m]:", "m10_eq_man_tf", value=0.80, min_value=0.30, max_value=5.0, step=0.05)
            else:
                man_Lf, man_Bf, man_tf = 3.50, 2.50, 0.80
                st.markdown(
                    "<div dir='rtl' style='direction:rtl !important; background:rgba(16,185,129,0.15); border:1.5px solid #10b981; border-radius:8px; padding:10px; text-align:center; color:#a7f3d0; font-weight:800; margin-top:6px;'>✨ الأبعاد تحسب أوتوماتيكياً لتحقيق الأمان الكامل</div>",
                    unsafe_allow_html=True,
                )

    res_eq = compute_equipment_foundation_design(
        eq_weight_ton=float(eq_weight),
        eq_shape=eq_shape,
        eq_length_m=float(eq_len),
        eq_width_m=float(eq_wid),
        eq_dia_m=float(eq_dia),
        isolation_type=iso_type,
        operating_rpm=float(op_rpm),
        ks_kg_cm3=float(ks_eq),
        fc_kg_cm2=float(fc_eq),
        fy_kg_cm2=float(fy_eq),
        q_all_kg_cm2=float(q_all_eq),
        sizing_mode=sizing_mode_eq,
        manual_Lf_m=float(man_Lf),
        manual_Bf_m=float(man_Bf),
        manual_tf_m=float(man_tf),
        target_mass_ratio=float(mass_ratio_target),
        cover_cm=float(cover_eq),
        phi_bot_mm=int(phi_bot_eq),
        phi_top_mm=int(phi_top_eq),
    )

    # ── OUTPUT KPI CARDS ──
    with st.expander("📊 2. المخرجات النهائية والتحققات الهندسية والتسليح (Final Outputs & Code Verification)", expanded=True):
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#0f172a; border:2px solid #38bdf8; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#93c5fd; font-weight:800;">الأبعاد النهائية للقاعدة (Lf × Bf × tf)</div>
                    <div style="font-size:25px; font-weight:900; color:#ffffff; margin:6px 0;" dir="ltr">{res_eq['Lf_m']:.2f} × {res_eq['Bf_m']:.2f} × {res_eq['tf_m']:.2f} m</div>
                    <div style="font-size:14px; color:#cbd5e1; font-weight:700;">الحجم الخرساني = <span dir="ltr">{res_eq['vol_f_m3']:.2f} m³</span></div>
                </div>""",
                unsafe_allow_html=True,
            )
        with k2:
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#0f172a; border:2px solid #f59e0b; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#fde047; font-weight:800;">الوزن الذاتي المحسوب تلقائياً (W_f)</div>
                    <div style="font-size:26px; font-weight:900; color:#fde047; margin:6px 0;" dir="ltr">{res_eq['Wf_ton']:.2f} ton</div>
                    <div style="font-size:14px; color:#cbd5e1; font-weight:700;">نسبة الكتلة <span dir="ltr">W_f / W_eq = {res_eq['actual_mass_ratio']:.2f}x</span></div>
                </div>""",
                unsafe_allow_html=True,
            )
        with k3:
            bg_s = "#064e3b" if res_eq["is_soil_safe"] else "#7f1d1d"
            bd_s = "#22c55e" if res_eq["is_soil_safe"] else "#ef4444"
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:{bg_s}; border:2px solid {bd_s}; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#e2e8f0; font-weight:800;">إجهاد التربة الفعلي / المسموح</div>
                    <div style="font-size:25px; font-weight:900; color:#ffffff; margin:6px 0;" dir="ltr">{res_eq['q_act_kg_cm2']:.2f} / {res_eq['q_all_kg_cm2']:.2f} kg/cm²</div>
                    <div style="font-size:14px; color:#a7f3d0; font-weight:700;">{'✅ آمن (SAFE)' if res_eq['is_soil_safe'] else '⚠️ غير آمن (UNSAFE)'} (<span dir="ltr">{res_eq['ratio_soil']*100:.1f}%</span>)</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with k4:
            bg_p = "#064e3b" if res_eq["is_punching_safe"] else "#7f1d1d"
            bd_p = "#22c55e" if res_eq["is_punching_safe"] else "#ef4444"
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:{bg_p}; border:2px solid {bd_p}; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#e2e8f0; font-weight:800;">فحص الاختراق (Punching Shear)</div>
                    <div style="font-size:25px; font-weight:900; color:#ffffff; margin:6px 0;" dir="ltr">{res_eq['q_up_kg_cm2']:.2f} / {res_eq['q_cup_all_kg_cm2']:.2f} kg/cm²</div>
                    <div style="font-size:14px; color:#a7f3d0; font-weight:700;">{'✅ آمن (SAFE)' if res_eq['is_punching_safe'] else '⚠️ غير آمن (UNSAFE)'} (<span dir="ltr">{res_eq['ratio_punching']*100:.1f}%</span>)</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        # Reinforcement & Dynamic Summary Banner
        r_c1, r_c2 = st.columns(2)
        with r_c1:
            st.markdown(
                f"""<div class="m10-rtl-panel" dir="rtl" style="direction:rtl !important; text-align:right !important; background:rgba(15,23,42,0.85); border:2px solid #22c55e; border-radius:12px; padding:16px 20px; unicode-bidi:isolate;">
                    <div dir="rtl" style="font-size:18px; font-weight:900; color:#4ade80; margin-bottom:10px; direction:rtl !important; text-align:right !important; width:100%;">🔩 تسليح القاعدة السفلي والعلوي والكميات (Reinforcement Summary)</div>
                    <div dir="rtl" style="font-size:15.5px; color:#f1f5f9; line-height:1.95; font-weight:700; direction:rtl !important; text-align:right !important; width:100%;">
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>شبكة التسليح السفلية (Bottom Mesh):</b> <span dir="ltr" style="color:#fde047; font-size:18px; font-weight:900; unicode-bidi:isolate;">{res_eq['n_bars_bot_m']} Φ {res_eq['phi_bot_mm']} / m'</span> في الاتجاهين (المسافة = <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['spacing_bot_cm']} cm</span>)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important; padding-right:16px;">▫️ المساحة المطلوبة = <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['As_bot_req_cm2_m']:.2f} cm²/m'</span> | المساحة المتوفرة = <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_eq['As_bot_prov_cm2_m']:.2f} cm²/m'</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>شبكة التسليح العلوية (Top Mesh):</b> <span dir="ltr" style="color:#38bdf8; font-size:18px; font-weight:900; unicode-bidi:isolate;">{res_eq['n_bars_top_m']} Φ {res_eq['phi_top_mm']} / m'</span> في الاتجاهين (المسافة = <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['spacing_top_cm']} cm</span>)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important; padding-right:16px;">▫️ المساحة المطلوبة = <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['As_top_req_cm2_m']:.2f} cm²/m'</span> | المساحة المتوفرة = <span dir="ltr" style="color:#38bdf8; unicode-bidi:isolate;">{res_eq['As_top_prov_cm2_m']:.2f} cm²/m'</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>إجمالي وزن حديد التسليح للقاعدة:</b> <span dir="ltr" style="color:#f472b6; font-size:17px; font-weight:900; unicode-bidi:isolate;">{res_eq['total_rebar_weight_kg']:.1f} kg ({res_eq['total_rebar_weight_ton']:.3f} ton)</span> — بمعدل <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['steel_rate_kg_m3']:.1f} kg/m³</span></div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        with r_c2:
            st.markdown(
                f"""<div class="m10-rtl-panel" dir="rtl" style="direction:rtl !important; text-align:right !important; background:rgba(15,23,42,0.85); border:2px solid #38bdf8; border-radius:12px; padding:16px 20px; unicode-bidi:isolate;">
                    <div dir="rtl" style="font-size:18px; font-weight:900; color:#38bdf8; margin-bottom:10px; direction:rtl !important; text-align:right !important; width:100%;">📳 تحليل الأحمال الاهتزازية والرنين (Dynamic & Vibration Analysis)</div>
                    <div dir="rtl" style="font-size:15.5px; color:#f1f5f9; line-height:1.95; font-weight:700; direction:rtl !important; text-align:right !important; width:100%;">
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>حالة الارتكاز والعزل:</b> {res_eq['isolation_type']}</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>حمل المعدة التصميمي بالمضاعف الديناميكي (<span dir="ltr" style="unicode-bidi:isolate;">DF = {res_eq['dyn_factor']:.2f}</span>):</b> <span dir="ltr" style="color:#fde047; unicode-bidi:isolate;">{res_eq['P_eq_design_ton']:.2f} ton</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>الوزن الذاتي للقاعدة (<span dir="ltr" style="unicode-bidi:isolate;">V × 2.5 t/m³</span>):</b> <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_eq['Wf_ton']:.2f} ton</span> | <b>الحمل الكلي:</b> <span dir="ltr" style="color:#38bdf8; unicode-bidi:isolate;">{res_eq['P_total_working_ton']:.2f} ton</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>التردد الطبيعي للقاعدة والتربة (<span dir="ltr" style="unicode-bidi:isolate;">fn</span>):</b> <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['fn_hz']:.2f} Hz</span> | <b>تردد التشغيل (<span dir="ltr" style="unicode-bidi:isolate;">f_op</span>):</b> <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['f_op_hz']:.2f} Hz</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>حالة الرنين الديناميكي:</b> <span style="color:{'#4ade80' if res_eq['is_resonance_safe'] else '#f87171'};">{res_eq['resonance_status_ar']}</span></div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        # Detailed Verification Table
        eq_checks = [
            (
                "1. الوزن الذاتي للقاعدة ونسبة القصور الذاتي (Foundation Self-Weight Ratio)",
                f"W_f = {res_eq['Wf_ton']:.2f} t ({res_eq['actual_mass_ratio']:.2f} W_eq)",
                "محسوب تلقائياً (DF = 1.2)" if res_eq["is_isolated"] else f"≥ {res_eq['req_mass_ratio_min']:.1f}×W_eq ({res_eq['req_min_wf_ton']:.1f} t)",
                res_eq["is_mass_ratio_safe"],
            ),
            (
                "2. فحص إجهاد التربة تحت الأحمال الكلية (Soil Bearing Capacity Check)",
                f"q_act = {res_eq['q_act_kg_cm2']:.2f} kg/cm² ({res_eq['q_act_ton_m2']:.1f} t/m²)",
                f"q_all = {res_eq['q_all_kg_cm2']:.2f} kg/cm² ({res_eq['q_all_ton_m2']:.1f} t/m²)",
                res_eq["is_soil_safe"],
            ),
            (
                "3. فحص القص الثاقب / الاختراق (Punching Shear Check - ECP 203)",
                f"q_up = {res_eq['q_up_kg_cm2']:.2f} kg/cm²",
                f"q_cup = {res_eq['q_cup_all_kg_cm2']:.2f} kg/cm²",
                res_eq["is_punching_safe"],
            ),
            (
                "4. فحص القص الحرج ذو الاتجاه الواحد (One-Way Beam Shear Check)",
                f"q_u = {res_eq['qu_1way_kg_cm2']:.2f} kg/cm²",
                f"q_cu = {res_eq['qcu_1way_kg_cm2']:.2f} kg/cm²",
                res_eq["is_1way_shear_safe"],
            ),
            (
                "5. التحقق من التردد الطبيعي وتجنب الرنين (Resonance Check)",
                f"f_op / f_n = {res_eq['freq_ratio']:.2f} ({res_eq['f_op_hz']:.1f} / {res_eq['fn_hz']:.1f} Hz)",
                "خارج نطاق الرنين [0.70 – 1.30]",
                res_eq["is_resonance_safe"],
            ),
        ]

        rows_html = []
        for idx, (c_name, c_act, c_lim, c_ok) in enumerate(eq_checks):
            bg_r = "rgba(15, 23, 42, 0.75)" if idx % 2 == 0 else "rgba(30, 41, 59, 0.75)"
            badge = (
                '<span style="background:rgba(34,197,94,0.2); color:#4ade80; border:1.5px solid #22c55e; padding:4px 12px; border-radius:8px; font-weight:900;">✅ آمن ومطابق (SAFE)</span>'
                if c_ok else
                '<span style="background:rgba(239,68,68,0.2); color:#f87171; border:1.5px solid #ef4444; padding:4px 12px; border-radius:8px; font-weight:900;">⚠️ غير آمن (UNSAFE)</span>'
            )
            rows_html.append(
                f'<tr style="background:{bg_r}; border-bottom:1px solid #334155;">'
                f'<td style="padding:12px 16px; font-size:17px; font-weight:800; color:#ffffff; text-align:right; direction:rtl;">{c_name}</td>'
                f'<td style="padding:12px 16px; font-size:18px; font-weight:900; color:#38bdf8; text-align:center;" dir="ltr">{c_act}</td>'
                f'<td style="padding:12px 16px; font-size:17px; font-weight:800; color:#fbbf24; text-align:center;" dir="ltr">{c_lim}</td>'
                f'<td style="padding:12px 16px; text-align:center;">{badge}</td>'
                f'</tr>'
            )

        st.markdown(
            '<div dir="rtl" style="direction:rtl !important; overflow-x:auto; border:2px solid #38bdf8; border-radius:12px; margin-top:16px;">'
            '<table dir="rtl" style="direction:rtl !important; width:100%; border-collapse:collapse; background:#0b1329;">'
            '<thead><tr style="background:#1e293b; border-bottom:2px solid #38bdf8;">'
            '<th style="padding:14px 16px; font-size:18px; color:#38bdf8; text-align:right;">بند التحقق الكودي (Verification Item)</th>'
            '<th style="padding:14px 16px; font-size:18px; color:#38bdf8; text-align:center;">القيمة المحسوبة (Actual)</th>'
            '<th style="padding:14px 16px; font-size:18px; color:#fbbf24; text-align:center;">الحد المسموح (Allowable)</th>'
            '<th style="padding:14px 16px; font-size:18px; color:#4ade80; text-align:center;">الحالة (Status)</th>'
            '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>',
            unsafe_allow_html=True,
        )

    # ── CAD SKETCH & REPORT EXPORT ──
    with st.expander("📐 3. المخططات الهندسية وتصدير المذكرة الحسابية (2D CAD Blueprints & Report Export)", expanded=True):
        sketch_eq_b64 = generate_equipment_foundation_sketches(res_eq)
        st.image(f"data:image/png;base64,{sketch_eq_b64}", use_container_width=True)

        summary_eq_rows = [
            ("الوزن التشغيلي للمعدة (Operating Weight)", f"{res_eq['eq_weight_ton']:.2f} ton"),
            ("حالة العزل الاهتزازي (Isolation Mode)", res_eq["isolation_type"]),
            ("الأبعاد النهائية للقاعدة (Lf × Bf × tf)", f"{res_eq['Lf_m']:.2f} m × {res_eq['Bf_m']:.2f} m × {res_eq['tf_m']:.2f} m"),
            ("حجم الخرسانة والوزن الذاتي للقاعدة (W_f @ 2.5 t/m³)", f"V = {res_eq['vol_f_m3']:.2f} m³ | W_f = {res_eq['Wf_ton']:.2f} ton"),
            ("إجمالي الحمل التصميمي التشغيلي (Total Working Load)", f"{res_eq['P_total_working_ton']:.2f} ton"),
            ("إجهاد التربة الفعلي / المسموح به", f"{res_eq['q_act_kg_cm2']:.2f} / {res_eq['q_all_kg_cm2']:.2f} kg/cm²"),
            ("إجهاد الاختراق الفعلي / المسموح (Punching Shear)", f"{res_eq['q_up_kg_cm2']:.2f} / {res_eq['q_cup_all_kg_cm2']:.2f} kg/cm²"),
            ("التسليح السفلي في الاتجاهين (Bottom Reinforcement)", f"{res_eq['n_bars_bot_m']} Φ {res_eq['phi_bot_mm']} / m' (As = {res_eq['As_bot_prov_cm2_m']:.2f} cm²/m')"),
            ("التسليح العلوي في الاتجاهين (Top Reinforcement)", f"{res_eq['n_bars_top_m']} Φ {res_eq['phi_top_mm']} / m' (As = {res_eq['As_top_prov_cm2_m']:.2f} cm²/m')"),
            ("إجمالي كمية حديد التسليح للقاعدة", f"{res_eq['total_rebar_weight_kg']:.1f} kg ({res_eq['total_rebar_weight_ton']:.3f} ton)"),
        ]
        html_eq_report = generate_m10_calculation_sheet_html(
            title_ar="مذكرة الحسابات الإنشائية لقاعدة المعدة الميكانيكية",
            subtitle_en="Equipment Foundation Structural & Dynamic Calculation Sheet (ECP 203 / ACI 351.3R)",
            rows_summary=summary_eq_rows,
            checks_list=eq_checks,
            sketch_b64=sketch_eq_b64,
        )

        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            st.download_button(
                "📥 تحميل المخطط الهندسي (PNG)",
                data=base64.b64decode(sketch_eq_b64),
                file_name=f"Equipment_Foundation_{res_eq['Lf_m']:.1f}x{res_eq['Bf_m']:.1f}m.png",
                mime="image/png",
                use_container_width=True,
            )
        with dl2:
            st.download_button(
                "🌐 تحميل المذكرة الحسابية (HTML)",
                data=html_eq_report,
                file_name=f"Equipment_Foundation_Report_{res_eq['Lf_m']:.1f}x{res_eq['Bf_m']:.1f}m.html",
                mime="text/html",
                use_container_width=True,
            )
        with dl3:
            if st.button("📕 توليد وتحميل ملف PDF", key="btn_m10_eq_pdf", use_container_width=True):
                with st.spinner("جاري تجهيز ملف PDF..."):
                    pdf_b = html_to_pdf_bytes(html_eq_report)
                    if pdf_b:
                        st.download_button(
                            "📥 اضغط لحفظ التقرير PDF",
                            data=pdf_b,
                            file_name="Equipment_Foundation_Report.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )


# ===============================================================================
#  6. STREAMLIT UI RENDERER — SECTION 2: LIQUID STORAGE TANK FOUNDATIONS
# ===============================================================================

def _render_liquid_storage_tanks_tab():
    st.markdown(
        """
        <div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #0f172a 0%, #064e3b 60%, #0f172a 100%); border: 2px solid #10b981; border-radius: 12px; padding: 16px 22px; margin-bottom: 18px; box-shadow: 0 4px 18px rgba(16, 185, 129, 0.25);">
            <div style="font-size: 20px; font-weight: 900; color: #fde047; margin-bottom: 6px; direction: rtl !important; text-align: right !important;">
                🛢️ ثانياً: قسم تصميم قواعد الخزانات السائلة (Liquid Storage Tank Foundations)
            </div>
            <div style="font-size: 14.5px; color: #e2e8f0; line-height: 1.75; font-weight: 600; direction: rtl !important; text-align: right !important;">
                قسم مستقل ومتكامل لتصميم القواعد الخرسانية المسلحة للخزانات الدائرية (<span dir="ltr">Circular</span>) والمستطيلة (<span dir="ltr">Rectangular</span>) المصنوعة من الصاج (<span dir="ltr">Steel Sheet</span>) أو البلاستيك (<span dir="ltr">Plastic</span>)، مع الحساب التلقائي لوزن الخزان ووزن السائل من السعة بالبراميل (<span dir="ltr">Barrels</span>) والوزن الذاتي الإجباري للقاعدة (<span dir="ltr">2.5 t/m³</span>) وفقاً للكود المصري <span dir="ltr">ECP 203</span> و <span dir="ltr">ACI 350</span>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📥 1. مدخلات الخزان الهندسية وسعة التخزين والمواد والتربة (Tank, Capacity & Soil Inputs)", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#34d399; margin-bottom:10px;'>🛢️ 1. بيانات هندسية ومادية للخزان</div>", unsafe_allow_html=True)
            tank_shape = S.selectbox(
                "الشكل الهندسي للخزان (Tank Shape):",
                "m10_tk_shape",
                ["دائري (Circular)", "مستطيل (Rectangular)"],
            )
            if "دائري" in tank_shape or "Circular" in tank_shape:
                tank_dia = S.number_input(
                    "قطر الخزان الدائري D_tank [m]:",
                    "m10_tk_dia_m",
                    value=6.00,
                    min_value=1.00,
                    max_value=60.0,
                    step=0.25,
                )
                tank_len, tank_wid = tank_dia, tank_dia
            else:
                tc1, tc2 = st.columns(2)
                with tc1:
                    tank_len = S.number_input(
                        "طول الخزان L_tank [m]:",
                        "m10_tk_len_m",
                        value=6.00,
                        min_value=1.00,
                        max_value=60.0,
                        step=0.25,
                    )
                with tc2:
                    tank_wid = S.number_input(
                        "عرض الخزان B_tank [m]:",
                        "m10_tk_wid_m",
                        value=4.00,
                        min_value=1.00,
                        max_value=60.0,
                        step=0.25,
                    )
                tank_dia = tank_len

            tank_mat = S.selectbox(
                "نوع مادة جسم الخزان (Tank Material):",
                "m10_tk_material",
                ["صاج صلب (Steel Sheet)", "بلاستيك مقوى / بولي إيثيلين (Plastic)"],
            )
            sheet_thk = S.number_input(
                "تخانة الصاج / الجدار (Sheet Thickness) [mm]:",
                "m10_tk_sheet_thk_mm",
                value=8.0,
                min_value=2.0,
                max_value=40.0,
                step=0.5,
            )

        with c2:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#34d399; margin-bottom:10px;'>🛢️ 2. سعة التخزين وخصائص السائل</div>", unsafe_allow_html=True)
            cap_bbl = S.number_input(
                "سعة الخزان بالبراميل (Storage Capacity) [Barrels]:",
                "m10_tk_cap_bbl",
                value=1000.0,
                min_value=10.0,
                max_value=200000.0,
                step=50.0,
                help="1 برميل قياسي = 158.987 لتر = 0.158987 م³",
            )
            sg_liq = S.number_input(
                "الكثافة النوعية للسائل / البترول (Specific Gravity):",
                "m10_tk_sg",
                value=0.85,
                min_value=0.60,
                max_value=1.50,
                step=0.05,
                help="الكثافة النوعية للبترول الخام والوقود تتراوح عادة بين 0.80 و 0.90 (الماء = 1.00)",
            )
            gwt_head = S.number_input(
                "عمق الغمر بالمياه الجوفية لفحص الطفو [m]:",
                "m10_tk_gwt_m",
                value=0.50,
                min_value=0.0,
                max_value=5.0,
                step=0.10,
            )
            lat_coeff = S.number_input(
                "معامل القوة الأفقية للرياح/الزلازل (Lateral Coeff):",
                "m10_tk_lat_coeff",
                value=0.08,
                min_value=0.02,
                max_value=0.30,
                step=0.01,
            )

        with c3:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#34d399; margin-bottom:10px;'>🧱 3. خواص المواد والتربة وأبعاد القاعدة</div>", unsafe_allow_html=True)
            fc_tk = S.number_input(
                "إجهاد الخرسانة fc' / fcu [kg/cm²]:",
                "m10_tk_fc",
                value=300.0,
                min_value=200.0,
                max_value=600.0,
                step=25.0,
            )
            fy_tk = S.number_input(
                "إجهاد حديد التسليح fy [kg/cm²]:",
                "m10_tk_fy",
                value=3600.0,
                min_value=2400.0,
                max_value=5000.0,
                step=200.0,
            )
            q_all_tk = S.number_input(
                "إجهاد التربة المسموح به q_all [kg/cm²]:",
                "m10_tk_q_all",
                value=1.50,
                min_value=0.40,
                max_value=6.00,
                step=0.10,
            )
            sizing_mode_tk = S.selectbox(
                "نظام تحديد أبعاد القاعدة الخرسانية:",
                "m10_tk_sizing_mode",
                ["حساب أوتوماتيكي للأبعاد (Auto-Sizing)", "إدخال يدوي للأبعاد (Manual Override)"],
            )

        st.markdown("---")
        t_reb1, t_reb2, t_reb3, t_reb4 = st.columns(4)
        with t_reb1:
            phi_bot_tk = S.selectbox("قطر التسليح السفلي Φ_bot [mm]:", "m10_tk_phi_bot", ECP_DIAMETERS, index=2)
        with t_reb2:
            phi_top_tk = S.selectbox("قطر التسليح العلوي Φ_top [mm]:", "m10_tk_phi_top", ECP_DIAMETERS, index=1)
        with t_reb3:
            cover_tk = S.number_input("الغطاء الخرساني Cover [cm]:", "m10_tk_cover", value=7.5, min_value=5.0, max_value=12.0, step=0.5)
        with t_reb4:
            if "Manual" in sizing_mode_tk or "يدوي" in sizing_mode_tk:
                mc1, mc2 = st.columns(2)
                with mc1:
                    man_ov_tk = S.number_input("رفرفة القاعدة c [m]:", "m10_tk_man_ov", value=0.60, min_value=0.20, max_value=5.0, step=0.10)
                with mc2:
                    man_tf_tk = S.number_input("سمك القاعدة tf [m]:", "m10_tk_man_tf", value=0.60, min_value=0.30, max_value=4.0, step=0.05)
            else:
                man_ov_tk, man_tf_tk = 0.60, 0.60
                st.markdown(
                    "<div dir='rtl' style='direction:rtl !important; background:rgba(16,185,129,0.15); border:1.5px solid #10b981; border-radius:8px; padding:10px; text-align:center; color:#a7f3d0; font-weight:800; margin-top:6px;'>✨ الأبعاد والرفرفة والسمك تحسب تلقائياً</div>",
                    unsafe_allow_html=True,
                )

    res_tk = compute_liquid_tank_foundation_design(
        tank_shape=tank_shape,
        tank_dia_m=float(tank_dia),
        tank_length_m=float(tank_len),
        tank_width_m=float(tank_wid),
        tank_material=tank_mat,
        sheet_thk_mm=float(sheet_thk),
        capacity_barrels=float(cap_bbl),
        specific_gravity=float(sg_liq),
        fc_kg_cm2=float(fc_tk),
        fy_kg_cm2=float(fy_tk),
        q_all_kg_cm2=float(q_all_tk),
        sizing_mode=sizing_mode_tk,
        manual_overhang_m=float(man_ov_tk),
        manual_tf_m=float(man_tf_tk),
        gwt_depth_m=float(gwt_head),
        wind_seismic_coeff=float(lat_coeff),
        cover_cm=float(cover_tk),
        phi_bot_mm=int(phi_bot_tk),
        phi_top_mm=int(phi_top_tk),
    )

    # ── DETAILED WEIGHTS & OUTPUTS ──
    with st.expander("📊 2. التقرير الحسابي التفصيلي للأوزان والأبعاد والتحققات والتسليح (Detailed Calculation Report)", expanded=True):
        # 4 Weight & Dimension Highlight Cards
        w1, w2, w3, w4 = st.columns(4)
        with w1:
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#0f172a; border:2px solid #38bdf8; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#93c5fd; font-weight:800;">وزن هيكل الخزان الفارغ (W_tank)</div>
                    <div style="font-size:26px; font-weight:900; color:#ffffff; margin:6px 0;" dir="ltr">{res_tk['W_tank_empty_ton']:.2f} ton</div>
                    <div style="font-size:13.5px; color:#cbd5e1; font-weight:700;">{res_tk['tank_material']} (تخانة <span dir="ltr">{res_tk['sheet_thk_mm']:.1f} mm</span>)</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with w2:
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#0f172a; border:2px solid #0ea5e9; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#7dd3fc; font-weight:800;">وزن السائل الإجمالي (W_liquid)</div>
                    <div style="font-size:26px; font-weight:900; color:#38bdf8; margin:6px 0;" dir="ltr">{res_tk['W_liquid_ton']:.2f} ton</div>
                    <div style="font-size:13.5px; color:#cbd5e1; font-weight:700;" dir="ltr">{res_tk['capacity_barrels']:.0f} BBL = {res_tk['vol_liquid_m3']:.1f} m³ (SG={res_tk['specific_gravity']:.2f})</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with w3:
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#0f172a; border:2px solid #f59e0b; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#fde047; font-weight:800;">الوزن الذاتي للقاعدة (W_foundation)</div>
                    <div style="font-size:26px; font-weight:900; color:#fde047; margin:6px 0;" dir="ltr">{res_tk['Wf_ton']:.2f} ton</div>
                    <div style="font-size:13.5px; color:#cbd5e1; font-weight:700;">الحجم = <span dir="ltr">{res_tk['vol_f_m3']:.2f} m³ × 2.5 t/m³</span></div>
                </div>""",
                unsafe_allow_html=True,
            )
        with w4:
            dim_str = (
                f"D_f = {res_tk['Df_m']:.2f} m × tf = {res_tk['tf_m']:.2f} m"
                if res_tk["is_circular"]
                else f"{res_tk['Lf_m']:.2f} × {res_tk['Bf_m']:.2f} × {res_tk['tf_m']:.2f} m"
            )
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#064e3b; border:2px solid #10b981; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#a7f3d0; font-weight:800;">الأبعاد الهندسية النهائية للقاعدة</div>
                    <div style="font-size:22px; font-weight:900; color:#ffffff; margin:8px 0;" dir="ltr">{dim_str}</div>
                    <div style="font-size:13.5px; color:#fde047; font-weight:700;">الحمل الكلي = <span dir="ltr">{res_tk['P_total_working_ton']:.2f} ton</span></div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        tk_c1, tk_c2 = st.columns(2)
        with tk_c1:
            st.markdown(
                f"""<div class="m10-rtl-panel" dir="rtl" style="direction:rtl !important; text-align:right !important; background:rgba(15,23,42,0.85); border:2px solid #22c55e; border-radius:12px; padding:16px 20px; unicode-bidi:isolate;">
                    <div dir="rtl" style="font-size:18px; font-weight:900; color:#4ade80; margin-bottom:10px; direction:rtl !important; text-align:right !important; width:100%;">🔩 تسليح قاعدة الخزان السفلي والعلوي طبقاً للكود (Reinforcement)</div>
                    <div dir="rtl" style="font-size:15.5px; color:#f1f5f9; line-height:1.95; font-weight:700; direction:rtl !important; text-align:right !important; width:100%;">
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>شبكة التسليح السفلية (Bottom Mesh):</b> <span dir="ltr" style="color:#fde047; font-size:18px; font-weight:900; unicode-bidi:isolate;">{res_tk['n_bars_bot_m']} Φ {res_tk['phi_bot_mm']} / m'</span> في الاتجاهين (المسافة = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['spacing_bot_cm']} cm</span>)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important; padding-right:16px;">▫️ المساحة المطلوبة = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['As_bot_req_cm2_m']:.2f} cm²/m'</span> | المساحة المتوفرة = <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_tk['As_bot_prov_cm2_m']:.2f} cm²/m'</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>شبكة التسليح العلوية (Top Mesh):</b> <span dir="ltr" style="color:#38bdf8; font-size:18px; font-weight:900; unicode-bidi:isolate;">{res_tk['n_bars_top_m']} Φ {res_tk['phi_top_mm']} / m'</span> في الاتجاهين (المسافة = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['spacing_top_cm']} cm</span>)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important; padding-right:16px;">▫️ المساحة المطلوبة = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['As_top_req_cm2_m']:.2f} cm²/m'</span> | المساحة المتوفرة = <span dir="ltr" style="color:#38bdf8; unicode-bidi:isolate;">{res_tk['As_top_prov_cm2_m']:.2f} cm²/m'</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>إجمالي وزن حديد التسليح للقاعدة:</b> <span dir="ltr" style="color:#f472b6; font-size:17px; font-weight:900; unicode-bidi:isolate;">{res_tk['total_rebar_weight_kg']:.1f} kg ({res_tk['total_rebar_weight_ton']:.3f} ton)</span> — بمعدل <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['steel_rate_kg_m3']:.1f} kg/m³</span></div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        with tk_c2:
            st.markdown(
                f"""<div class="m10-rtl-panel" dir="rtl" style="direction:rtl !important; text-align:right !important; background:rgba(15,23,42,0.85); border:2px solid #38bdf8; border-radius:12px; padding:16px 20px; unicode-bidi:isolate;">
                    <div dir="rtl" style="font-size:18px; font-weight:900; color:#38bdf8; margin-bottom:10px; direction:rtl !important; text-align:right !important; width:100%;">🌊 الضغط الهيدروستاتيكي والاتزان ضد الانقلاب والطفو</div>
                    <div dir="rtl" style="font-size:15.5px; color:#f1f5f9; line-height:1.95; font-weight:700; direction:rtl !important; text-align:right !important; width:100%;">
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>ارتفاع السائل داخل الخزان (<span dir="ltr" style="unicode-bidi:isolate;">H_liquid</span>):</b> <span dir="ltr" style="color:#fde047; unicode-bidi:isolate;">{res_tk['H_liquid_m']:.2f} m</span> (الارتفاع الكلي = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['H_tank_total_m']:.2f} m</span>)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>الضغط الهيدروستاتيكي على القاع (<span dir="ltr" style="unicode-bidi:isolate;">p = γ_liq × H</span>):</b> <span dir="ltr" style="color:#38bdf8; unicode-bidi:isolate;">{res_tk['p_hydrostatic_ton_m2']:.2f} ton/m² ({res_tk['p_hydrostatic_kg_cm2']:.2f} kg/cm²)</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>معامل الأمان ضد الانقلاب (<span dir="ltr" style="unicode-bidi:isolate;">FOS_overturning</span>):</b> <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_tk['fos_overturning']:.2f}</span> (المطلوب ≥ 1.50)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>معامل الأمان ضد الطفو (<span dir="ltr" style="unicode-bidi:isolate;">FOS_buoyancy</span>):</b> <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_tk['fos_buoyancy']:.2f}</span> (المطلوب ≥ 1.25)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>أقصى إجهاد تربة فعلي (<span dir="ltr" style="unicode-bidi:isolate;">q_max</span>):</b> <span dir="ltr" style="color:#fde047; unicode-bidi:isolate;">{res_tk['q_max_kg_cm2']:.2f} kg/cm²</span> ≤ المسموح <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['q_all_kg_cm2']:.2f} kg/cm²</span></div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        tk_checks = [
            (
                "1. التحقق من عدم تجاوز إجهاد التربة المسموح به (Soil Bearing Pressure)",
                f"q_max = {res_tk['q_max_kg_cm2']:.2f} kg/cm² ({res_tk['q_max_ton_m2']:.1f} t/m²)",
                f"q_all = {res_tk['q_all_kg_cm2']:.2f} kg/cm² ({res_tk['q_all_ton_m2']:.1f} t/m²)",
                res_tk["is_soil_safe"],
            ),
            (
                "2. فحص مقاومة الاختراق تحت جدار وحمل الخزان (Punching Shear - ECP 203)",
                f"q_up = {res_tk['q_up_kg_cm2']:.2f} kg/cm²",
                f"q_cup = {res_tk['q_cup_all_kg_cm2']:.2f} kg/cm²",
                res_tk["is_punching_safe"],
            ),
            (
                "3. فحص مقاومة القص ذو الاتجاه الواحد (One-Way Shear Strength)",
                f"q_u = {res_tk['qu_1way_kg_cm2']:.2f} kg/cm²",
                f"q_cu = {res_tk['qcu_1way_kg_cm2']:.2f} kg/cm²",
                res_tk["is_1way_shear_safe"],
            ),
            (
                "4. التحقق من الاستقرار ضد الانقلاب (Overturning Stability)",
                f"FOS = {res_tk['fos_overturning']:.2f} (M_res={res_tk['M_resisting_full_tm']:.1f} / M_ot={res_tk['M_overturning_tm']:.1f})",
                "FOS ≥ 1.50",
                res_tk["is_overturning_safe"],
            ),
            (
                "5. التحقق من مقاومة قوى الطفو (Buoyancy / Uplift Stability)",
                f"FOS = {res_tk['fos_buoyancy']:.2f} (W_empty={res_tk['W_empty_total_ton']:.1f} t / U={res_tk['U_buoyancy_ton']:.1f} t)",
                "FOS ≥ 1.25",
                res_tk["is_buoyancy_safe"],
            ),
        ]

        rows_tk_html = []
        for idx, (c_name, c_act, c_lim, c_ok) in enumerate(tk_checks):
            bg_r = "rgba(15, 23, 42, 0.75)" if idx % 2 == 0 else "rgba(30, 41, 59, 0.75)"
            badge = (
                '<span style="background:rgba(34,197,94,0.2); color:#4ade80; border:1.5px solid #22c55e; padding:4px 12px; border-radius:8px; font-weight:900;">✅ آمن ومطابق (SAFE)</span>'
                if c_ok else
                '<span style="background:rgba(239,68,68,0.2); color:#f87171; border:1.5px solid #ef4444; padding:4px 12px; border-radius:8px; font-weight:900;">⚠️ غير آمن (UNSAFE)</span>'
            )
            rows_tk_html.append(
                f'<tr style="background:{bg_r}; border-bottom:1px solid #334155;">'
                f'<td style="padding:12px 16px; font-size:17px; font-weight:800; color:#ffffff; text-align:right; direction:rtl;">{c_name}</td>'
                f'<td style="padding:12px 16px; font-size:18px; font-weight:900; color:#38bdf8; text-align:center;" dir="ltr">{c_act}</td>'
                f'<td style="padding:12px 16px; font-size:17px; font-weight:800; color:#fbbf24; text-align:center;" dir="ltr">{c_lim}</td>'
                f'<td style="padding:12px 16px; text-align:center;">{badge}</td>'
                f'</tr>'
            )

        st.markdown(
            '<div dir="rtl" style="direction:rtl !important; overflow-x:auto; border:2px solid #10b981; border-radius:12px; margin-top:16px;">'
            '<table dir="rtl" style="direction:rtl !important; width:100%; border-collapse:collapse; background:#0b1329;">'
            '<thead><tr style="background:#1e293b; border-bottom:2px solid #10b981;">'
            '<th style="padding:14px 16px; font-size:18px; color:#34d399; text-align:right;">بند التحقق الكودي للخزان (Verification Item)</th>'
            '<th style="padding:14px 16px; font-size:18px; color:#38bdf8; text-align:center;">القيمة المحسوبة (Actual)</th>'
            '<th style="padding:14px 16px; font-size:18px; color:#fbbf24; text-align:center;">الحد المسموح (Allowable)</th>'
            '<th style="padding:14px 16px; font-size:18px; color:#4ade80; text-align:center;">الحالة (Status)</th>'
            '</tr></thead><tbody>' + "".join(rows_tk_html) + '</tbody></table></div>',
            unsafe_allow_html=True,
        )

    # ── CAD SKETCH & REPORT EXPORT ──
    with st.expander("📐 3. المخططات الهندسية وتصدير التقرير الحسابي للخزان (2D Tank Blueprints & Report)", expanded=True):
        sketch_tk_b64 = generate_liquid_tank_foundation_sketches(res_tk)
        st.image(f"data:image/png;base64,{sketch_tk_b64}", use_container_width=True)

        summary_tk_rows = [
            ("الشكل الهندسي ومادة الخزان", f"{res_tk['tank_shape']} — {res_tk['tank_material']} (تخانة {res_tk['sheet_thk_mm']:.1f} mm)"),
            ("سعة وحجم التخزين", f"{res_tk['capacity_barrels']:.0f} Barrels ({res_tk['vol_liquid_m3']:.2f} m³) — الكثافة النوعية = {res_tk['specific_gravity']:.2f}"),
            ("وزن الخزان الفارغ المحسوب تلقائياً (W_tank)", f"{res_tk['W_tank_empty_ton']:.2f} ton"),
            ("وزن السائل الإجمالي المحسوب تلقائياً (W_liquid)", f"{res_tk['W_liquid_ton']:.2f} ton"),
            ("الوزن الذاتي للقاعدة الخرسانية (W_foundation @ 2.5 t/m³)", f"V = {res_tk['vol_f_m3']:.2f} m³ | W_f = {res_tk['Wf_ton']:.2f} ton"),
            ("إجمالي الأحمال الكلية (المعدة + السائل + القاعدة)", f"{res_tk['P_total_working_ton']:.2f} ton"),
            ("الأبعاد الهندسية النهائية للقاعدة (Lf × Bf × tf)", f"{res_tk['Lf_m']:.2f} m × {res_tk['Bf_m']:.2f} m × {res_tk['tf_m']:.2f} m"),
            ("إجهاد التربة الأقصى الفعلي / المسموح به", f"{res_tk['q_max_kg_cm2']:.2f} / {res_tk['q_all_kg_cm2']:.2f} kg/cm²"),
            ("تسليح القاعدة السفلي (Bottom Mesh)", f"{res_tk['n_bars_bot_m']} Φ {res_tk['phi_bot_mm']} / m' (As = {res_tk['As_bot_prov_cm2_m']:.2f} cm²/m')"),
            ("تسليح القاعدة العلوي (Top Mesh)", f"{res_tk['n_bars_top_m']} Φ {res_tk['phi_top_mm']} / m' (As = {res_tk['As_top_prov_cm2_m']:.2f} cm²/m')"),
            ("إجمالي وزن حديد التسليح للقاعدة", f"{res_tk['total_rebar_weight_kg']:.1f} kg ({res_tk['total_rebar_weight_ton']:.3f} ton)"),
        ]
        html_tk_report = generate_m10_calculation_sheet_html(
            title_ar="التقرير الحسابي التفصيلي لقاعدة خزان السوائل",
            subtitle_en="Liquid Storage Tank Foundation Calculation Sheet (ECP 203 / ACI 350)",
            rows_summary=summary_tk_rows,
            checks_list=tk_checks,
            sketch_b64=sketch_tk_b64,
        )

        td1, td2, td3 = st.columns(3)
        with td1:
            st.download_button(
                "📥 تحميل مخطط قاعدة الخزان (PNG)",
                data=base64.b64decode(sketch_tk_b64),
                file_name=f"Liquid_Tank_Foundation_{res_tk['Lf_m']:.1f}x{res_tk['Bf_m']:.1f}m.png",
                mime="image/png",
                use_container_width=True,
            )
        with td2:
            st.download_button(
                "🌐 تحميل التقرير الحسابي للخزان (HTML)",
                data=html_tk_report,
                file_name=f"Liquid_Tank_Foundation_Report_{res_tk['capacity_barrels']:.0f}BBL.html",
                mime="text/html",
                use_container_width=True,
            )
        with td3:
            if st.button("📕 توليد وتحميل ملف PDF للخزان", key="btn_m10_tk_pdf", use_container_width=True):
                with st.spinner("جاري تجهيز ملف PDF..."):
                    pdf_b2 = html_to_pdf_bytes(html_tk_report)
                    if pdf_b2:
                        st.download_button(
                            "📥 اضغط لحفظ التقرير PDF",
                            data=pdf_b2,
                            file_name="Liquid_Tank_Foundation_Report.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )


# ===============================================================================
#  7. MAIN MODULE 10 ENTRY POINT
# ===============================================================================

def render_circular_tank_foundations_module():
    """
    Main Streamlit renderer for Module 10:
    1. Equipment Foundation Design (Static & Dynamic Mechanical Equipment)
    2. Liquid Storage Tank Foundations (Circular & Rectangular Liquid Tanks)
    """
    st.markdown(
        """
        <style>
        /* Keep Expander Section Headers LTR (Left-to-Right) just like all other modules */
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] summary,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] summary * {
            direction: ltr !important;
            text-align: left !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stTabs"] button[data-baseweb="tab"] {
            font-size: 18px !important;
            font-weight: 900 !important;
            padding: 12px 24px !important;
        }
        /* Ensure RTL inside custom Arabic panels & widget labels */
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stWidgetLabel"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stWidgetLabel"] * {
            direction: rtl !important;
            text-align: right !important;
            width: 100% !important;
            justify-content: flex-start !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="select"] {
            direction: rtl !important;
            text-align: right !important;
        }
        [data-testid="stMainBlockContainer"] .m10-rtl-panel,
        [data-testid="stMainBlockContainer"] .m10-rtl-panel > div,
        [data-testid="stMainBlockContainer"] .m10-rtl-panel div {
            direction: rtl !important;
            text-align: right !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    tab_eq, tab_tank = st.tabs([
        "⚙️ أولاً: تصميم قواعد المعدات الميكانيكية (Equipment Foundations)",
        "🛢️ ثانياً: تصميم قواعد الخزانات السائلة (Liquid Storage Tank Foundations)",
    ])

    with tab_eq:
        _render_equipment_foundations_tab()

    with tab_tank:
        _render_liquid_storage_tanks_tab()
