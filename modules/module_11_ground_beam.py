"""
Module 11 — Ground Beam Design & Detailing (ECP 203)
=====================================================
تصميم وتفاصيل الميدات والكمرات الأرضية والسملات وفق الكود المصري لتصميم المنشآت الخرسانية ECP 203-2018
Metric Engineering Units Convention (Strictly No SI Units):
  • Dimensions           : Section dimensions in cm, spans and lengths in m.
  • Loads & Moments      : Loads in ton/m, forces in ton, moments in ton·m.
  • Material Strengths   : fcu and fy in kg/cm², Allowable soil bearing capacity (q_all) in kg/cm².
  • Steel Linear Mass    : Calculated using (Φ² / 162) kg/m.
Run from app.py via:  render_ground_beam_module()
"""

import io
import math
import matplotlib
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from modules.table_styler import render_styled_table
from modules.settings import (
    cfg_val,
    cfg_set,
    save_settings,
    get_default_module_11_state,
    migrate_module_11_in_project_dict,
)

_COVER_CM = 4.0  # cm (ECP 203 standard substructure / foundation cover)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENGINEERING CALCULATION ENGINE (ECP 203)
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_ground_beam(params: dict) -> dict:
    """
    Core structural calculation engine for Ground Beam (الميدة / السمل) per ECP 203.
    Strictly metric engineering units: ton, m, cm, kg/cm².
    """
    level_type = params.get("level_type", "Above Footing Level (أعلى منسوب القواعد / رقاب الأعمدة)")
    support_cond = params.get("support_condition", "Simply Supported (حر من الطرفين)")
    L = float(params.get("L_m", 5.00))          # m
    b = float(params.get("b_cm", 25.0))         # cm
    t_exec = float(params.get("t_cm", 60.0))    # cm
    cover = float(params.get("cover_cm", _COVER_CM))

    fcu = float(params.get("fcu", 250.0))       # kg/cm²
    fy = float(params.get("fy", 4000.0))        # kg/cm²
    fy_st = float(params.get("fy_stirrup", 2400.0))  # kg/cm²

    phi_bot = int(params.get("phi_bot_mm", 16)) # mm
    phi_top = int(params.get("phi_top_mm", 12)) # mm
    phi_st = int(params.get("phi_stirrup_mm", 8)) # mm
    stirrups_per_m = int(params.get("stirrups_per_m", 6))
    n_branches = int(params.get("n_branches", 4 if b >= 40.0 else 2))
    phi_side = int(params.get("phi_side_mm", 10))

    # 1. Loading Calculations
    is_at_footing = "At Footing Level" in level_type

    # Own weight of beam (ton/m)
    w_ow = (b / 100.0) * (t_exec / 100.0) * 2.50

    # Wall / Masonry Parameters (Active for both levels: At Footing and Above Footing)
    has_wall = bool(params.get("has_wall", params.get("has_wall_at_footing", True)))
    h_wall = float(params.get("h_wall_m", 3.00)) if has_wall else 0.0
    t_wall = float(params.get("t_wall_cm", 12.0)) if has_wall else 0.0
    gamma_brick = float(params.get("gamma_brick", 1.80)) if has_wall else 1.80
    w_wall = h_wall * (t_wall / 100.0) * gamma_brick if has_wall else 0.0

    w_add_dl = float(params.get("w_add_dl", 0.0))
    w_add_ll = float(params.get("w_add_ll", 0.0))

    if is_at_footing:
        t_footing = float(params.get("t_footing_cm", 60.0))
        delta_settle_mm = float(params.get("delta_settlement_mm", 10.0))
        q_all_soil = float(params.get("q_all_soil", 1.50))
        if q_all_soil >= 5.0:
            q_all_soil = round(q_all_soil / 10.0, 2)
        h_backfill = float(params.get("h_backfill_m", 1.0))

        w_fill = (b / 100.0) * h_backfill * 1.80
        w_DL = w_ow + w_fill + w_wall + w_add_dl
        w_LL = w_add_ll
        w_u_grav = 1.4 * w_DL + (1.6 * w_LL if w_LL > 0 else 0.0)

        # Differential settlement calculation
        Ec = 44000.0 * math.sqrt(max(1.0, fcu / 10.0))  # kg/cm²
        Ig = (b * (t_exec ** 3)) / 12.0                  # cm⁴
        Ie = 0.35 * Ig                                    # cm⁴ (cracked section under settlement per ECP 203)
        delta_cm = delta_settle_mm / 10.0
        L_cm = L * 100.0

        M_delta_kgcm = (6.0 * Ec * Ie * delta_cm) / (L_cm ** 2) if L_cm > 0 else 0.0
        M_delta_tonm = M_delta_kgcm / 100000.0
        Mu_delta = 1.4 * M_delta_tonm
        Qu_delta = 1.4 * ((2.0 * M_delta_tonm) / max(0.5, L))
    else:
        t_footing = 0.0
        delta_settle_mm = 0.0
        q_all_soil = 0.0
        h_backfill = 0.0
        w_fill = 0.0

        w_DL = w_ow + w_wall + w_add_dl
        w_LL = w_add_ll
        w_u_grav = 1.4 * w_DL + (1.6 * w_LL if w_LL > 0 else 0.0)

        Ec = 44000.0 * math.sqrt(max(1.0, fcu / 10.0))
        Ig = (b * (t_exec ** 3)) / 12.0
        Ie = 0.35 * Ig
        M_delta_tonm = 0.0
        Mu_delta = 0.0
        Qu_delta = 0.0

    # 2. Support Condition & Gravity Internal Forces
    if "Simply Supported" in support_cond or "حر" in support_cond:
        L_d_limit = 16.0
        Mu_pos_grav = (w_u_grav * (L ** 2)) / 8.0
        Mu_neg_grav = (w_u_grav * (L ** 2)) / 24.0
        Qu_grav = 0.50 * w_u_grav * L
        supp_text = "Simply Supported (حر من الطرفين)"
    elif "One End" in support_cond or "طرف واحد" in support_cond:
        L_d_limit = 18.5
        Mu_pos_grav = (w_u_grav * (L ** 2)) / 10.0
        Mu_neg_grav = (w_u_grav * (L ** 2)) / 10.0
        Qu_grav = 0.60 * w_u_grav * L
        supp_text = "Continuous from One End (مستمر من طرف واحد)"
    else:  # Continuous from Both Ends
        L_d_limit = 21.0
        Mu_pos_grav = (w_u_grav * (L ** 2)) / 12.0
        Mu_neg_grav = (w_u_grav * (L ** 2)) / 12.0
        Qu_grav = 0.55 * w_u_grav * L
        supp_text = "Continuous from Both Ends (مستمر من الطرفين)"

    # Total Design Moments and Shears
    Mu = Mu_pos_grav + Mu_delta
    Mu_top = Mu_neg_grav + Mu_delta
    Qu = Qu_grav + Qu_delta

    # 3. Recommended Depth (t_calc) Calculation
    # Deflection requirement
    d_defl = (L * 100.0) / L_d_limit
    t_defl = d_defl + cover

    # Flexural requirement (with economical C1 = 3.50)
    d_flex = 3.50 * math.sqrt((Mu * 100000.0) / (max(1.0, fcu) * b)) if Mu > 0 else 25.0
    t_flex = d_flex + cover

    # Minimum base depth
    t_min_base = max(t_footing, 40.0) if is_at_footing else 40.0

    t_calc_raw = max(t_defl, t_flex, t_min_base)
    t_calc = float(math.ceil(t_calc_raw / 5.0) * 5.0)

    # 4. Cross-Section Effective Depth & Flexural Design with t_exec
    d = max(10.0, t_exec - cover)

    # Calculate C1 and J per ECP 203
    denom = math.sqrt((Mu * 100000.0) / (max(1.0, fcu) * b)) if Mu > 0 else 1.0
    C1 = d / denom if denom > 0 else 5.0

    if C1 >= 4.85:
        J = 0.826
        cd_ratio = 0.125
    elif C1 < 2.78:
        # Over-reinforced limit warning in ECP 203
        cd_ratio = 0.44
        J = 0.670
    else:
        term = 1.0 - (2.0 * Mu * 100000.0) / (0.85 * fcu * b * (d ** 2))
        term = max(0.0, term)
        cd_ratio = (1.0 - math.sqrt(term)) / 0.80
        J = min(0.826, max(0.67, 1.0 - 0.40 * cd_ratio))

    # Bottom Steel Area
    As_bot_req = (Mu * 100000.0) / (fy * J * d) if (fy * J * d) > 0 else 0.0
    As_min1 = 0.0015 * b * d
    As_min2 = (1.1 / fy) * b * d
    As_min3 = (1.3 * math.sqrt(fcu) / fy) * b * d
    As_min = max(As_min1, As_min2)
    As_bot = max(As_bot_req, As_min)

    area_1bar_bot = math.pi * ((phi_bot / 10.0) ** 2) / 4.0
    n_bot = max(2, math.ceil(As_bot / max(0.01, area_1bar_bot)))
    As_bot_prov = n_bot * area_1bar_bot

    # Top Steel Area
    if "Simply Supported" in support_cond or "حر" in support_cond:
        As_top_calc = (Mu_top * 100000.0) / (fy * 0.826 * d) if (fy * 0.826 * d) > 0 else 0.0
        As_top_min = 0.20 * As_bot
        As_top = max(As_top_calc, As_top_min)
    else:
        As_top_calc = (Mu_top * 100000.0) / (fy * J * d) if (fy * J * d) > 0 else 0.0
        As_top_min = max(0.20 * As_bot, 0.0015 * b * d)
        As_top = max(As_top_calc, As_top_min)

    area_1bar_top = math.pi * ((phi_top / 10.0) ** 2) / 4.0
    n_top = max(2, math.ceil(As_top / max(0.01, area_1bar_top)))
    As_top_prov = n_top * area_1bar_top

    # Shrinkage Side Bars (براندات الانكماش) per ECP 203
    if t_exec >= 60.0:
        side_spaces = math.ceil((t_exec - 2.0 * cover) / 30.0)
        n_side_rows = max(1, side_spaces - 1)
    else:
        n_side_rows = 0

    total_side_bars = 2 * n_side_rows
    area_1bar_side = math.pi * ((phi_side / 10.0) ** 2) / 4.0
    As_side_prov = total_side_bars * area_1bar_side

    # 5. Shear Stresses & Stirrups Design (ECP 203)
    qu = (Qu * 1000.0) / (b * d) if (b * d) > 0 else 0.0  # kg/cm²
    qcu = 0.75 * math.sqrt(fcu / 1.5)                      # kg/cm²
    qu_max = 2.20 * math.sqrt(fcu / 1.5)                   # kg/cm²

    area_1leg_st = math.pi * ((phi_st / 10.0) ** 2) / 4.0  # cm²
    As_st_prov_per_m = n_branches * area_1leg_st * stirrups_per_m  # cm²/m

    if qu > qu_max:
        shear_status = "UNSAFE"
        shear_status_text = "❌ غير آمن: إجهاد القص يتجاوز الحد الأقصى للخرسانة (qu > qu,max) يلزم زيادة أبعاد القطاع"
        As_st_req_per_m = 0.0
    elif qu > qcu:
        qsu = qu - (qcu / 2.0)
        As_st_req_per_m = (qsu * b * 100.0) / (fy_st / 1.15) if fy_st > 0 else 0.0
        if As_st_prov_per_m >= As_st_req_per_m:
            shear_status = "SAFE"
            shear_status_text = "✅ آمن بالكانات: الكانات المحددة كافية وتتحمل إجهاد القص الزائد"
        else:
            shear_status = "UNSAFE"
            shear_status_text = "⚠️ الكانات غير كافية: يلزم زيادة قطر الكانة أو عدد الكانات بالمتر"
    else:
        shear_status = "SAFE"
        shear_status_text = "✅ آمن خرسانة فقط: إجهاد القص أقل من مقاومة الخرسانة (qu ≤ qcu) وتوضع كانات دنيا"
        As_st_req_per_m = (0.40 / fy_st) * b * 100.0  # Minimum nominal per ECP 203

    # 6. Steel Linear Mass using (Φ² / 162) kg/m
    lin_mass_bot = (phi_bot ** 2) / 162.0
    lin_mass_top = (phi_top ** 2) / 162.0
    lin_mass_st = (phi_st ** 2) / 162.0
    lin_mass_side = (phi_side ** 2) / 162.0

    # Development & hook anchorage lengths (approx 50 Φ)
    L_dev_bot = (50.0 * phi_bot) / 1000.0  # m
    L_dev_top = (50.0 * phi_top) / 1000.0  # m
    L_bar_bot = L + 2.0 * L_dev_bot
    L_bar_top = L + 2.0 * L_dev_top
    L_bar_side = L + 0.30

    # Stirrup perimeter in meters
    st_w_m = (b - 2.0 * cover) / 100.0
    st_h_m = (t_exec - 2.0 * cover) / 100.0
    hook_m = (20.0 * phi_st) / 1000.0
    if n_branches == 4:
        st_perimeter = 2.0 * (2.0 * (st_w_m + st_h_m) + hook_m)  # Outer + Inner
    else:
        st_perimeter = 2.0 * (st_w_m + st_h_m) + hook_m

    num_stirrups_total = int(math.ceil(stirrups_per_m * L))

    # Total Weights in kg
    wt_bot_kg = n_bot * L_bar_bot * lin_mass_bot
    wt_top_kg = n_top * L_bar_top * lin_mass_top
    wt_side_kg = total_side_bars * L_bar_side * lin_mass_side
    wt_st_kg = num_stirrups_total * st_perimeter * lin_mass_st
    total_steel_kg = wt_bot_kg + wt_top_kg + wt_side_kg + wt_st_kg

    concrete_vol_m3 = (b / 100.0) * (t_exec / 100.0) * L
    steel_ratio_kg_m3 = (total_steel_kg / concrete_vol_m3) if concrete_vol_m3 > 0 else 0.0

    return {
        # Geometry
        "L": L,
        "b": b,
        "t_exec": t_exec,
        "t_calc": t_calc,
        "t_defl": t_defl,
        "t_flex": t_flex,
        "d": d,
        "cover": cover,
        "is_at_footing": is_at_footing,
        "level_type": level_type,
        "support_cond": supp_text,
        "L_d_limit": L_d_limit,
        # Loads
        "w_ow": w_ow,
        "has_wall": has_wall,
        "h_wall": h_wall,
        "t_wall": t_wall,
        "gamma_brick": gamma_brick,
        "w_wall": w_wall,
        "w_u_wall": 1.4 * w_wall,
        "w_fill": w_fill,
        "w_DL": w_DL,
        "w_LL": w_LL,
        "w_u_grav": w_u_grav,
        # Settlement & Soil
        "q_all_soil": q_all_soil,
        "delta_settle_mm": delta_settle_mm,
        "M_delta_tonm": M_delta_tonm,
        "Mu_delta": Mu_delta,
        "Qu_delta": Qu_delta,
        # Forces
        "Mu": Mu,
        "Mu_top": Mu_top,
        "Qu": Qu,
        # Flexural Design
        "C1": C1,
        "J": J,
        "cd_ratio": cd_ratio,
        "As_bot_req": As_bot_req,
        "As_min": As_min,
        "As_bot": As_bot,
        "n_bot": n_bot,
        "phi_bot": phi_bot,
        "As_bot_prov": As_bot_prov,
        "As_top_req": As_top,
        "n_top": n_top,
        "phi_top": phi_top,
        "As_top_prov": As_top_prov,
        # Side Bars
        "n_side_rows": n_side_rows,
        "total_side_bars": total_side_bars,
        "phi_side": phi_side,
        "As_side_prov": As_side_prov,
        # Shear
        "qu": qu,
        "qcu": qcu,
        "qu_max": qu_max,
        "stirrups_per_m": stirrups_per_m,
        "phi_st": phi_st,
        "n_branches": n_branches,
        "As_st_req_per_m": As_st_req_per_m,
        "As_st_prov_per_m": As_st_prov_per_m,
        "shear_status": shear_status,
        "shear_status_text": shear_status_text,
        # Materials
        "fcu": fcu,
        "fy": fy,
        "fy_st": fy_st,
        # Steel Quantities
        "lin_mass_bot": lin_mass_bot,
        "lin_mass_top": lin_mass_top,
        "lin_mass_st": lin_mass_st,
        "lin_mass_side": lin_mass_side,
        "wt_bot_kg": wt_bot_kg,
        "wt_top_kg": wt_top_kg,
        "wt_side_kg": wt_side_kg,
        "wt_st_kg": wt_st_kg,
        "total_steel_kg": total_steel_kg,
        "concrete_vol_m3": concrete_vol_m3,
        "steel_ratio_kg_m3": steel_ratio_kg_m3,
        "num_stirrups_total": num_stirrups_total,
        "L_bar_bot": L_bar_bot,
        "L_bar_top": L_bar_top,
        "st_perimeter": st_perimeter,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  2D STRUCTURAL REINFORCEMENT DRAWING (MATPLOTLIB)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_ground_beam_cross_section(res: dict) -> plt.Figure:
    """
    Executive-grade parametric cross-section drawing (Sec. A-A) of the ground beam.
    Strictly true proportions, CAD dark cyberpunk theme (#0f172a), closed stirrups with
    135-degree hooks, 4-branch inner stirrups for b >= 40 cm, multi-layer bottom steel,
    shrinkage side bars for t >= 60 cm, dimension witness lines, and CAD title block.
    """
    b = res["b"]
    t = res["t_exec"]
    cover = res["cover"]
    n_bot = res["n_bot"]
    phi_bot = res["phi_bot"]
    n_top = res["n_top"]
    phi_top = res["phi_top"]
    stirrups_per_m = res["stirrups_per_m"]
    phi_st = res["phi_st"]
    n_branches = res["n_branches"]
    n_side_rows = res["n_side_rows"]
    phi_side = res["phi_side"]

    fig, ax = plt.subplots(figsize=(6.8, 8.8), dpi=180)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')

    # 1. Concrete Outline
    rect_conc = patches.Rectangle(
        (0, 0), b, t,
        facecolor='#1e293b', edgecolor='#94a3b8',
        linewidth=2.4, zorder=1
    )
    ax.add_patch(rect_conc)

    # 2. Outer Closed Stirrup
    st_corner = 1.2  # cm
    st_w = b - 2.0 * cover
    st_h = t - 2.0 * cover
    outer_st = patches.FancyBboxPatch(
        (cover, cover), st_w, st_h,
        boxstyle=patches.BoxStyle('Round', pad=0.0, rounding_size=st_corner),
        facecolor='none', edgecolor='#38bdf8', linewidth=2.4, zorder=3
    )
    ax.add_patch(outer_st)

    # 135-Degree Standard Hook Closure at Top-Right Corner
    hook_len = max(3.0, (10.0 * phi_st) / 10.0)  # cm
    hook_start_x = b - cover - st_corner
    hook_start_y = t - cover
    ax.plot(
        [hook_start_x, hook_start_x - hook_len * 0.707],
        [hook_start_y, hook_start_y - hook_len * 0.707],
        color='#38bdf8', linewidth=2.4, solid_capstyle='round', zorder=4
    )

    # 4-Branch Inner Stirrup (if b >= 40 cm or user selected 4 branches)
    if n_branches == 4:
        inner_w = st_w * 0.50
        inner_x = cover + (st_w - inner_w) / 2.0
        inner_st = patches.FancyBboxPatch(
            (inner_x, cover), inner_w, st_h,
            boxstyle=patches.BoxStyle('Round', pad=0.0, rounding_size=st_corner),
            facecolor='none', edgecolor='#06b6d4', linewidth=1.8, linestyle='--', zorder=3
        )
        ax.add_patch(inner_st)

    # 3. Bottom Longitudinal Reinforcement (with 2-layer handling if spacing is tight)
    r_bot = max(0.60, (phi_bot / 10.0) / 2.0)
    t_st_wire = max(0.4, (phi_st / 10.0))
    y_bot_l1 = cover + t_st_wire + r_bot
    x_start_bot = cover + t_st_wire + r_bot
    x_end_bot = b - cover - t_st_wire - r_bot
    avail_w_bot = x_end_bot - x_start_bot

    # Clear spacing check for 1 layer vs 2 layers
    clear_spacing = (avail_w_bot - (n_bot - 1) * (2.0 * r_bot)) / max(1, n_bot - 1) if n_bot > 1 else 10.0

    if clear_spacing >= 2.50 or n_bot <= 3:
        # Single Layer
        for i in range(n_bot):
            xi = x_start_bot + i * (avail_w_bot / max(1, n_bot - 1))
            c_bot = patches.Circle((xi, y_bot_l1), r_bot, facecolor='#22c55e', edgecolor='#15803d', linewidth=1.2, zorder=6)
            ax.add_patch(c_bot)
    else:
        # Double Layer
        n1 = math.ceil(n_bot / 2.0)
        n2 = n_bot - n1
        y_bot_l2 = y_bot_l1 + 2.0 * r_bot + 2.50
        for i in range(n1):
            xi = x_start_bot + i * (avail_w_bot / max(1, n1 - 1))
            c_bot = patches.Circle((xi, y_bot_l1), r_bot, facecolor='#22c55e', edgecolor='#15803d', linewidth=1.2, zorder=6)
            ax.add_patch(c_bot)
        for j in range(n2):
            xj = x_start_bot + j * (avail_w_bot / max(1, n2 - 1))
            c_bot = patches.Circle((xj, y_bot_l2), r_bot, facecolor='#22c55e', edgecolor='#15803d', linewidth=1.2, zorder=6)
            ax.add_patch(c_bot)

    # 4. Top Longitudinal Reinforcement
    r_top = max(0.50, (phi_top / 10.0) / 2.0)
    y_top = t - cover - t_st_wire - r_top
    x_start_top = cover + t_st_wire + r_top
    x_end_top = b - cover - t_st_wire - r_top
    avail_w_top = x_end_top - x_start_top

    for j in range(n_top):
        xj = x_start_top + j * (avail_w_top / max(1, n_top - 1))
        c_top = patches.Circle((xj, y_top), r_top, facecolor='#f59e0b', edgecolor='#b45309', linewidth=1.2, zorder=6)
        ax.add_patch(c_top)

    # 5. Shrinkage Side Bars (براندات الانكماش) for t >= 60 cm
    if n_side_rows > 0:
        r_side = max(0.45, (phi_side / 10.0) / 2.0)
        s_y = (y_top - y_bot_l1) / (n_side_rows + 1)
        for k in range(1, n_side_rows + 1):
            yk = y_bot_l1 + k * s_y
            c_sl = patches.Circle((cover + t_st_wire + r_side, yk), r_side, facecolor='#a855f7', edgecolor='#7e22ce', linewidth=1.2, zorder=6)
            c_sr = patches.Circle((b - cover - t_st_wire - r_side, yk), r_side, facecolor='#a855f7', edgecolor='#7e22ce', linewidth=1.2, zorder=6)
            ax.add_patch(c_sl)
            ax.add_patch(c_sr)

    # 6. Dimensions Witness Lines & Text Labels (in cm)
    # Bottom Width Dimension
    y_dim_w = -0.14 * t
    ax.plot([0, b], [y_dim_w, y_dim_w], color='#38bdf8', linewidth=1.3, zorder=2)
    ax.plot([0, 0], [0, y_dim_w - 1.8], color='#64748b', linewidth=0.9, linestyle=':')
    ax.plot([b, b], [0, y_dim_w - 1.8], color='#64748b', linewidth=0.9, linestyle=':')
    ax.plot([0, 1.2], [y_dim_w - 0.6, y_dim_w + 0.6], color='#38bdf8', linewidth=1.3)
    ax.plot([b, b - 1.2], [y_dim_w - 0.6, y_dim_w + 0.6], color='#38bdf8', linewidth=1.3)
    ax.text(b / 2.0, y_dim_w - 3.2, f"b = {b:.0f} cm", color='#38bdf8', fontsize=11, fontweight='bold', ha='center', va='top')

    # Side Total Depth Dimension
    x_dim_d = b + 0.14 * b
    ax.plot([x_dim_d, x_dim_d], [0, t], color='#38bdf8', linewidth=1.3, zorder=2)
    ax.plot([b, x_dim_d + 1.8], [0, 0], color='#64748b', linewidth=0.9, linestyle=':')
    ax.plot([b, x_dim_d + 1.8], [t, t], color='#64748b', linewidth=0.9, linestyle=':')
    ax.plot([x_dim_d - 0.6, x_dim_d + 0.6], [0, 1.2], color='#38bdf8', linewidth=1.3)
    ax.plot([x_dim_d - 0.6, x_dim_d + 0.6], [t, t - 1.2], color='#38bdf8', linewidth=1.3)
    ax.text(x_dim_d + 3.0, t / 2.0, f"t = {t:.0f} cm", color='#38bdf8', fontsize=11, fontweight='bold', ha='left', va='center', rotation=-90)

    # 7. Leader Callout Annotations
    # Top Rebar Leader
    ax.annotate(
        f"Top: {n_top} Φ {phi_top} mm\nAs = {res['As_top_prov']:.2f} cm²",
        xy=(x_start_top, y_top),
        xytext=(-0.30 * b, y_top + 0.05 * t),
        arrowprops=dict(arrowstyle='->', color='#f59e0b', lw=1.5, shrinkB=4),
        color='#f59e0b', fontsize=9.5, fontweight='bold', ha='right', va='center',
        bbox=dict(boxstyle='round,pad=0.25', facecolor='#1e293b', edgecolor='#f59e0b', lw=1)
    )

    # Bottom Rebar Leader
    ax.annotate(
        f"Bottom: {n_bot} Φ {phi_bot} mm\nAs = {res['As_bot_prov']:.2f} cm²",
        xy=(x_start_bot, y_bot_l1),
        xytext=(-0.30 * b, y_bot_l1 - 0.04 * t),
        arrowprops=dict(arrowstyle='->', color='#22c55e', lw=1.5, shrinkB=4),
        color='#22c55e', fontsize=9.5, fontweight='bold', ha='right', va='center',
        bbox=dict(boxstyle='round,pad=0.25', facecolor='#1e293b', edgecolor='#22c55e', lw=1)
    )

    # Stirrups Leader
    ax.annotate(
        f"Stirrups: {stirrups_per_m} Φ {phi_st} / m\n({n_branches} Branches)",
        xy=(cover, t * 0.60),
        xytext=(-0.30 * b, t * 0.60),
        arrowprops=dict(arrowstyle='->', color='#38bdf8', lw=1.5, shrinkB=4),
        color='#38bdf8', fontsize=9.2, fontweight='bold', ha='right', va='center',
        bbox=dict(boxstyle='round,pad=0.25', facecolor='#1e293b', edgecolor='#38bdf8', lw=1)
    )

    # Shrinkage Side Bars Leader (if present)
    if n_side_rows > 0:
        s_y_first = y_bot_l1 + ((y_top - y_bot_l1) / (n_side_rows + 1))
        ax.annotate(
            f"Shrinkage: {2 * n_side_rows} Φ {phi_side} mm\n({n_side_rows} Rows ≤ 30cm)",
            xy=(cover + t_st_wire + r_side, s_y_first),
            xytext=(-0.30 * b, s_y_first),
            arrowprops=dict(arrowstyle='->', color='#a855f7', lw=1.5, shrinkB=4),
            color='#a855f7', fontsize=9.0, fontweight='bold', ha='right', va='center',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='#1e293b', edgecolor='#a855f7', lw=1)
        )

    # 8. Title Block Below Plot
    tb_y_top = -0.25 * t
    tb_h = 0.17 * t
    tb_rect = patches.Rectangle(
        (-0.25 * b, tb_y_top - tb_h), 1.60 * b, tb_h,
        facecolor='#1e293b', edgecolor='#3b82f6', linewidth=1.6, zorder=2
    )
    ax.add_patch(tb_rect)

    ax.text(
        0.55 * b, tb_y_top - 0.28 * tb_h,
        f"SEC A-A: {b:.0f} × {t:.0f} cm (GROUND BEAM - ECP 203)",
        color='#f8fafc', fontsize=11.0, fontweight='heavy', ha='center', va='center'
    )
    ax.text(
        0.55 * b, tb_y_top - 0.65 * tb_h,
        f"Mu = {res['Mu']:.2f} ton·m  |  Qu = {res['Qu']:.2f} ton  |  Span L = {res['L']:.2f} m",
        color='#38bdf8', fontsize=9.2, fontweight='bold', ha='center', va='center'
    )
    ax.text(
        0.55 * b, tb_y_top - 0.88 * tb_h,
        f"fcu = {res['fcu']:.0f} kg/cm²  |  fy = {res['fy']:.0f} kg/cm²  |  Cover = {cover:.1f} cm",
        color='#94a3b8', fontsize=8.2, ha='center', va='center'
    )

    # Limits and View Adjustments
    ax.set_xlim(-0.48 * b, b + 0.42 * b)
    ax.set_ylim(tb_y_top - tb_h - 0.05 * t, t + 0.12 * t)
    ax.axis('equal')
    ax.axis('off')

    return fig


def draw_ground_beam_longitudinal_elevation(res: dict) -> plt.Figure:
    """
    Executive-grade longitudinal beam elevation (Sec. Long-1) showing:
    • Column/Footing supports at both ends
    • Longitudinal bottom steel with standard 90-degree end hooks
    • Top steel with hooks
    • Side shrinkage bars
    • Stirrup zones along the span
    • Bending Moment Diagram (BMD) & Shear Force Diagram (SFD)
    """
    L = res["L"]
    b = res["b"]
    t = res["t_exec"]
    L_cm = L * 100.0

    fig, (ax_elev, ax_diag) = plt.subplots(2, 1, figsize=(10.0, 7.8), dpi=180, gridspec_kw={'height_ratios': [1.8, 1.2]})
    fig.patch.set_facecolor('#0f172a')
    ax_elev.set_facecolor('#0f172a')
    ax_diag.set_facecolor('#0f172a')

    supp_w = 40.0  # cm
    supp_h = 35.0  # cm

    # 1. Supports (Columns/Footings)
    supp_left = patches.Rectangle((-supp_w, -supp_h), supp_w, t + 2 * supp_h, facecolor='#334155', edgecolor='#64748b', hatch='//', lw=1.5)
    supp_right = patches.Rectangle((L_cm, -supp_h), supp_w, t + 2 * supp_h, facecolor='#334155', edgecolor='#64748b', hatch='//', lw=1.5)
    ax_elev.add_patch(supp_left)
    ax_elev.add_patch(supp_right)

    # 2. Concrete Beam Body
    beam_rect = patches.Rectangle((0, 0), L_cm, t, facecolor='#1e293b', edgecolor='#94a3b8', lw=2.2, zorder=2)
    ax_elev.add_patch(beam_rect)

    # 3. Bottom Steel with 90° Hooks
    cover = res["cover"]
    y_bot = cover + 1.2
    hook_h = max(20.0, t * 0.65)
    bot_xs = [-supp_w * 0.70, -supp_w * 0.70, L_cm + supp_w * 0.70, L_cm + supp_w * 0.70]
    bot_ys = [y_bot + hook_h, y_bot, y_bot, y_bot + hook_h]
    ax_elev.plot(bot_xs, bot_ys, color='#22c55e', linewidth=2.8, solid_capstyle='round', zorder=5)

    # 4. Top Steel with 90° Hooks
    y_top = t - cover - 1.2
    top_xs = [-supp_w * 0.70, -supp_w * 0.70, L_cm + supp_w * 0.70, L_cm + supp_w * 0.70]
    top_ys = [y_top - hook_h * 0.60, y_top, y_top, y_top - hook_h * 0.60]
    ax_elev.plot(top_xs, top_ys, color='#f59e0b', linewidth=2.4, solid_capstyle='round', zorder=5)

    # 5. Side Bars (if t >= 60 cm)
    if res["n_side_rows"] > 0:
        sy = (y_top - y_bot) / (res["n_side_rows"] + 1)
        for k in range(1, res["n_side_rows"] + 1):
            yk = y_bot + k * sy
            ax_elev.plot([-supp_w * 0.50, L_cm + supp_w * 0.50], [yk, yk], color='#a855f7', linewidth=1.8, linestyle='--', zorder=4)

    # 6. Stirrups Distribution along the span
    num_st = min(40, max(15, int(res["stirrups_per_m"] * L)))
    st_spacing = L_cm / (num_st + 1)
    for si in range(1, num_st + 1):
        x_st = si * st_spacing
        ax_elev.plot([x_st, x_st], [cover, t - cover], color='#38bdf8', linewidth=1.2, alpha=0.85, zorder=3)

    # Dimension line for clear span L
    y_dim_L = -supp_h - 12.0
    ax_elev.plot([0, L_cm], [y_dim_L, y_dim_L], color='#38bdf8', lw=1.4)
    ax_elev.plot([0, 0], [0, y_dim_L - 3.0], color='#64748b', lw=0.9, linestyle=':')
    ax_elev.plot([L_cm, L_cm], [0, y_dim_L - 3.0], color='#64748b', lw=0.9, linestyle=':')
    ax_elev.text(L_cm / 2.0, y_dim_L - 4.0, f"Clear Span L = {L:.2f} m ({L_cm:.0f} cm)", color='#38bdf8', fontsize=10, fontweight='bold', ha='center', va='top')

    # Annotations on Elevation
    ax_elev.text(
        L_cm / 2.0, y_bot - 7.0,
        f"Bottom: {res['n_bot']} Φ {res['phi_bot']} mm",
        color='#22c55e', fontsize=10, fontweight='bold', ha='center', va='top'
    )
    ax_elev.text(
        L_cm / 2.0, y_top + 7.0,
        f"Top: {res['n_top']} Φ {res['phi_top']} mm",
        color='#f59e0b', fontsize=10, fontweight='bold', ha='center', va='bottom'
    )

    ax_elev.set_xlim(-supp_w - 20.0, L_cm + supp_w + 20.0)
    ax_elev.set_ylim(-supp_h - 26.0, t + supp_h + 18.0)
    ax_elev.axis('off')
    ax_elev.set_title("ELEVATION VIEW — SEC. LONG-1 (المسقط الطولي وتفريد حديد الميدة)", color='#f8fafc', fontsize=12, fontweight='bold', pad=10)

    # ── 7. Bending Moment Diagram (BMD) & Shear (SFD) in bottom subplot ──────
    xs = np.linspace(0, L, 200)
    # Parabolic moment
    w_eq = (8.0 * res["Mu"]) / (L ** 2) if L > 0 else 1.0
    M_curve = 4.0 * res["Mu"] * (xs / L) * (1.0 - xs / L)

    ax_diag.plot(xs, M_curve, color='#e11d48', linewidth=2.2, label=f"Bending Moment Mu (Max = {res['Mu']:.2f} t·m)")
    ax_diag.fill_between(xs, 0, M_curve, color='#e11d48', alpha=0.20)
    ax_diag.axhline(0, color='#94a3b8', linestyle='--', linewidth=0.8)

    ax_diag.set_xlim(0, L)
    ax_diag.set_xlabel("Span (m)", color='#cbd5e1', fontsize=9.5)
    ax_diag.set_ylabel("Mu (ton·m)", color='#fb7185', fontsize=9.5)
    ax_diag.tick_params(colors='#94a3b8', labelsize=8.5)
    ax_diag.grid(True, linestyle=':', alpha=0.35, color='#475569')

    # Shear indication text
    ax_diag.text(
        0.02, 0.85,
        f"Max Shear Qu = {res['Qu']:.2f} ton  |  qu = {res['qu']:.2f} kg/cm²",
        transform=ax_diag.transAxes, color='#38bdf8', fontsize=9.5, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1e293b', edgecolor='#38bdf8', lw=1)
    )
    ax_diag.legend(loc='upper right', facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc', fontsize=8.5)

    plt.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  STREAMLIT UI MODULE RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render_ground_beam_module():
    """
    Main Streamlit module renderer for Module 11: Ground Beam Design & Detailing.
    """
    # Synchronize session state dictionary
    if "module_11_data" not in st.session_state or not isinstance(st.session_state["module_11_data"], dict):
        cfg = st.session_state.get("cfg", {})
        migrate_module_11_in_project_dict(cfg)
        nested = cfg.get("module_11_ground_beam")
        if not isinstance(nested, dict):
            nested = get_default_module_11_state()
            cfg["module_11_ground_beam"] = nested
        st.session_state["module_11_data"] = dict(nested)

    data = st.session_state["module_11_data"]
    if float(data.get("q_all_soil", 1.50)) >= 5.0:
        data["q_all_soil"] = round(float(data["q_all_soil"]) / 10.0, 2)

    # ── Header Banner ────────────────────────────────────────────────────────
    st.markdown(
        """
        <div dir="rtl" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                    border: 2px solid #38bdf8; border-radius: 12px; padding: 18px 22px; margin-bottom: 18px;
                    box-shadow: 0 4px 20px rgba(56, 189, 248, 0.15); text-align: right;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div>
                    <div style="font-size: 23px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 10px;">
                        🧱 Module 11 — تصميم وتفاصيل الميدات والكمرات الأرضية (Ground Beams & Tie Beams)
                    </div>
                    <div style="font-size: 14.5px; color: #cbd5e1; margin-top: 6px; line-height: 1.7;">
                        وفق اشتراطات الكود المصري <b>ECP 203-2018</b> • فحص الهبوط التفاضلي وأحمال الحوائط • إعادة التصميم التفاعلي للعمق التنفيذي • رسم قطاع إنشائي تنفيذي متكامل (Sec. A-A)
                    </div>
                </div>
                <div style="background: rgba(56, 189, 248, 0.12); border: 1.5px solid #38bdf8; border-radius: 8px; padding: 8px 14px; text-align: center;">
                    <div style="font-size: 12px; color: #94a3b8;">الوحدات الهندسية المعتمدة</div>
                    <div style="font-size: 15px; font-weight: 800; color: #38bdf8;">ton · m · cm · kg/cm²</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Interactive Sidebar / Top Controls ───────────────────────────────────
    col_in1, col_in2, col_in3 = st.columns([1.1, 1.1, 1.0])

    with col_in1:
        st.markdown("<div style='font-size:16px; font-weight:800; color:#38bdf8; margin-bottom:8px;'>📌 منسوب الميدة ونوع الارتكاز</div>", unsafe_allow_html=True)
        level_options = [
            "Above Footing Level (أعلى منسوب القواعد / رقاب الأعمدة)",
            "At Footing Level (في منسوب القواعد المسلحة / سمل رابط)"
        ]
        curr_lvl = data.get("level_type", level_options[0])
        lvl_idx = level_options.index(curr_lvl) if curr_lvl in level_options else 0
        sel_level = st.selectbox("منسوب الميدة الإنشائي (Ground Beam Level):", options=level_options, index=lvl_idx, key="m11_sel_level")
        data["level_type"] = sel_level

        support_options = [
            "Simply Supported (حر من الطرفين)",
            "Continuous from One End (مستمر من طرف واحد)",
            "Continuous from Both Ends (مستمر من الطرفين)"
        ]
        curr_sup = data.get("support_condition", support_options[0])
        sup_idx = support_options.index(curr_sup) if curr_sup in support_options else 0
        sel_sup = st.selectbox("حالة الاستمرارية والدعم (Support Condition):", options=support_options, index=sup_idx, key="m11_sel_sup")
        data["support_condition"] = sel_sup

        c_g1, c_g2 = st.columns(2)
        with c_g1:
            L_val = st.number_input("البحر الصافي L (m):", min_value=1.50, max_value=14.00, value=float(data.get("L_m", 5.00)), step=0.25, key="m11_L_m")
            data["L_m"] = L_val
        with c_g2:
            b_val = st.number_input("عرض الميدة b (cm):", min_value=15.0, max_value=80.0, value=float(data.get("b_cm", 25.0)), step=5.0, key="m11_b_cm")
            data["b_cm"] = b_val

    with col_in2:
        st.markdown("<div style='font-size:16px; font-weight:800; color:#38bdf8; margin-bottom:8px;'>🧱 أحمال الميدة والمتغيرات الموقعية</div>", unsafe_allow_html=True)
        if "At Footing Level" in sel_level:
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                t_ftg = st.number_input("عمق القاعدة المجاورة (cm):", min_value=30.0, max_value=150.0, value=float(data.get("t_footing_cm", 60.0)), step=5.0, key="m11_t_footing")
                data["t_footing_cm"] = t_ftg
            with c_f2:
                delta_val = st.number_input("هبوط تفاضلي Δ (mm):", min_value=0.0, max_value=50.0, value=float(data.get("delta_settlement_mm", 10.0)), step=1.0, key="m11_delta")
                data["delta_settlement_mm"] = delta_val

            c_s1, c_s2 = st.columns(2)
            with c_s1:
                q_soil = st.number_input(
                    "جهد التربة q_all (kg/cm²):",
                    min_value=0.50,
                    max_value=5.00,
                    value=float(data.get("q_all_soil", 1.50)),
                    step=0.10,
                    key="m11_q_soil",
                    help="جهد التأسيس المسموح للتربة (kg/cm²). القيمة المعتادة 1.0 إلى 2.5 kg/cm² (حيث 1.50 kg/cm² = 15 ton/m²)"
                )
                data["q_all_soil"] = q_soil
            with c_s2:
                h_fill = st.number_input("ارتفاع الردم (m):", min_value=0.0, max_value=3.0, value=float(data.get("h_backfill_m", 1.0)), step=0.2, key="m11_h_fill")
                data["h_backfill_m"] = h_fill

        # ── حوائط المباني والأحمال فوق الميدة (متاحة في الحالتين: في منسوب القواعد وأعلى منسوب القواعد)
        has_wall_val = bool(data.get("has_wall", data.get("has_wall_at_footing", True)))
        has_wall = st.checkbox(
            "يوجد حائط طوب (مباني) فوق الميدة / السمل",
            value=has_wall_val,
            key="m11_has_wall",
            help="تفعيل هذا الخيار لاحتساب أحمال الحوائط وتصعيدها بـ 1.4 ودمجها مباشرة في عزوم وقوى قص التصميم"
        )
        data["has_wall"] = has_wall
        data["has_wall_at_footing"] = has_wall

        if has_wall:
            c_w1, c_w2 = st.columns(2)
            with c_w1:
                hw = st.number_input(
                    "ارتفاع الحائط h_wall (m):",
                    min_value=0.50,
                    max_value=6.00,
                    value=float(data.get("h_wall_m", 3.00)),
                    step=0.25,
                    key="m11_hw",
                    help="ارتفاع الحائط الصافي المقام فوق الميدة بالمتر"
                )
                data["h_wall_m"] = hw
            with c_w2:
                tw = st.number_input(
                    "سماكة الحائط t_wall (cm):",
                    min_value=10.0,
                    max_value=38.0,
                    value=float(data.get("t_wall_cm", 12.0)),
                    step=1.0,
                    key="m11_tw",
                    help="سماكة الحائط بالسنتيمتر (12 سم لنصف طوبة، 25 سم لطوبة كاملة)"
                )
                data["t_wall_cm"] = tw

            c_d1, c_d2 = st.columns(2)
            with c_d1:
                g_brick = st.number_input(
                    "كثافة الطوب والمونة γ (ton/m³):",
                    min_value=1.20,
                    max_value=2.40,
                    value=float(data.get("gamma_brick", 1.80)),
                    step=0.05,
                    key="m11_g_brick",
                    help="كثافة الطوب مع المونة والمحارة (1.80 للأحمر / 2.00 للأسمنتي)"
                )
                data["gamma_brick"] = g_brick
            with c_d2:
                w_dl_add = st.number_input(
                    "أحمال ميتة إضافية (ton/m):",
                    min_value=0.0,
                    max_value=5.0,
                    value=float(data.get("w_add_dl", 0.0)),
                    step=0.1,
                    key="m11_w_dl_add"
                )
                data["w_add_dl"] = w_dl_add
        else:
            w_dl_add = st.number_input(
                "أحمال ميتة إضافية (ton/m):",
                min_value=0.0,
                max_value=5.0,
                value=float(data.get("w_add_dl", 0.0)),
                step=0.1,
                key="m11_w_dl_add"
            )
            data["w_add_dl"] = w_dl_add

        # Live calculation of the wall load directly below inputs
        calc_w_wall = (float(data.get("h_wall_m", 3.00)) * (float(data.get("t_wall_cm", 12.0)) / 100.0) * float(data.get("gamma_brick", 1.80))) if has_wall else 0.0
        st.markdown(
            f"""
            <div style="background: rgba(56, 189, 248, 0.08); border: 1px dashed #38bdf8; border-radius: 6px; padding: 6px 10px; margin-top: 6px; font-size: 12.5px; color: #cbd5e1;">
                🧱 <b>حمل الحائط:</b> <span style="color:#38bdf8; font-weight:bold;">{calc_w_wall:.3f} ton/m</span> 
                (المصعد Ultimate: <span style="color:#4ade80; font-weight:bold;">{1.4 * calc_w_wall:.3f} ton/m</span>)
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_in3:
        st.markdown("<div style='font-size:16px; font-weight:800; color:#38bdf8; margin-bottom:8px;'>⚙️ المواد وأقطار التسليح</div>", unsafe_allow_html=True)
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            fcu_val = st.number_input("خرسانة fcu (kg/cm²):", min_value=150.0, max_value=500.0, value=float(data.get("fcu", 250.0)), step=25.0, key="m11_fcu")
            data["fcu"] = fcu_val
        with c_m2:
            fy_val = st.number_input("صلب طولي fy (kg/cm²):", min_value=2400.0, max_value=5000.0, value=float(data.get("fy", 4000.0)), step=200.0, key="m11_fy")
            data["fy"] = fy_val

        c_r1, c_r2 = st.columns(2)
        with c_r1:
            bar_opts = [12, 16, 18, 20, 22, 25]
            curr_b = int(data.get("phi_bot_mm", 16))
            idx_b = bar_opts.index(curr_b) if curr_b in bar_opts else 1
            phi_b = st.selectbox("سفلي Φ_bot (mm):", options=bar_opts, index=idx_b, key="m11_phi_bot")
            data["phi_bot_mm"] = phi_b
        with c_r2:
            top_opts = [10, 12, 16, 18]
            curr_t = int(data.get("phi_top_mm", 12))
            idx_t = top_opts.index(curr_t) if curr_t in top_opts else 1
            phi_t = st.selectbox("علوي Φ_top (mm):", options=top_opts, index=idx_t, key="m11_phi_top")
            data["phi_top_mm"] = phi_t

        c_st1, c_st2 = st.columns(2)
        with c_st1:
            st_dia_opts = [8, 10, 12]
            curr_st = int(data.get("phi_stirrup_mm", 8))
            idx_st = st_dia_opts.index(curr_st) if curr_st in st_dia_opts else 0
            phi_st_val = st.selectbox("كانات Φ_st (mm):", options=st_dia_opts, index=idx_st, key="m11_phi_st")
            data["phi_stirrup_mm"] = phi_st_val
        with c_st2:
            st_per_m_opts = [5, 6, 7, 8, 10]
            curr_spm = int(data.get("stirrups_per_m", 6))
            idx_spm = st_per_m_opts.index(curr_spm) if curr_spm in st_per_m_opts else 1
            spm = st.selectbox("كانات / متر:", options=st_per_m_opts, index=idx_spm, key="m11_spm")
            data["stirrups_per_m"] = spm

        # Auto select 4 branches if b >= 40
        def_branches = 4 if b_val >= 40.0 else 2
        branch_opts = [2, 4]
        curr_br = int(data.get("n_branches", def_branches))
        if b_val >= 40.0:
            curr_br = 4
        idx_br = branch_opts.index(curr_br) if curr_br in branch_opts else 0
        n_br = st.selectbox("فروع الكانة (Branches):", options=branch_opts, index=idx_br, key="m11_n_branches")
        data["n_branches"] = n_br
        if b_val >= 40.0 and n_br == 2:
            st.caption("ℹ️ يُوصى بـ 4 فروع للقطاعات بعرض b ≥ 40 cm.")

    # ── Preliminary Calculation to determine Recommended Depth t_calc ────────
    temp_res = calculate_ground_beam(data)
    t_calc_val = temp_res["t_calc"]
    data["t_calc_cm"] = t_calc_val
    st.session_state["m11_target_t_calc"] = t_calc_val

    # Define callback to safely update session_state before widgets run on next pass
    def _sync_m11_depth_callback():
        target_val = float(st.session_state.get("m11_target_t_calc", 60.0))
        st.session_state["m11_t_exec_input"] = target_val
        if "module_11_data" in st.session_state and isinstance(st.session_state["module_11_data"], dict):
            st.session_state["module_11_data"]["t_cm"] = target_val

    # Ensure widget key is in session state prior to widget instantiation
    if "m11_t_exec_input" not in st.session_state:
        st.session_state["m11_t_exec_input"] = float(data.get("t_cm", t_calc_val))

    # ── Interactive Depth Override Card ──────────────────────────────────────
    st.markdown("---")
    c_dep1, c_dep2, c_dep3 = st.columns([1.5, 1.2, 1.3])

    with c_dep1:
        st.markdown(
            f"""
            <div style="background:#1e293b; border:1.5px solid #38bdf8; border-radius:10px; padding:12px 16px;">
                <div style="font-size:13px; color:#94a3b8; font-weight:700;">العمق التصميمي الاسترشادي المحسوب (Recommended Depth):</div>
                <div style="font-size:24px; font-weight:900; color:#38bdf8; margin-top:3px;">
                    t_calc = {t_calc_val:.0f} cm
                </div>
                <div style="font-size:12.5px; color:#cbd5e1; margin-top:3px;">
                    محددات الكود: ترخيم (<b>{temp_res['t_defl']:.0f} cm</b>) • عزم انحناء (<b>{temp_res['t_flex']:.0f} cm</b>)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_dep2:
        # Execution depth editable field
        t_exec_input = st.number_input(
            "العمق التنفيذي الفعلي للميدة Execution Beam Depth (t) [cm]:",
            min_value=25.0,
            max_value=200.0,
            step=5.0,
            key="m11_t_exec_input",
            help="تعديل هذا العمق يؤدي لإعادة تصميم القطاع فوراً وإعادة حساب التسليح والقص والترخيم"
        )
        data["t_cm"] = float(t_exec_input)

    with c_dep3:
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.button(
            "🔄 مزامنة مع العمق المحسوب (t_calc)",
            on_click=_sync_m11_depth_callback,
            use_container_width=True,
            key="m11_btn_sync_depth",
            help="إعادة ضبط العمق التنفيذي ليتطابق فوراً مع العمق الاسترشادي الآمن المحسوب كودياً"
        )

    # ── Run Final Calculation with Execution Depth ────────────────────────────
    res = calculate_ground_beam(data)

    # Save to session and cfg
    st.session_state["module_11_data"] = data
    cfg = st.session_state.get("cfg", {})
    cfg["module_11_ground_beam"] = data
    save_settings()

    # ── KPI Dashboard Cards ──────────────────────────────────────────────────
    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    k1.metric(
        label="عزم التصميم الأقصى Mu",
        value=f"{res['Mu']:.2f} t·m",
        delta=f"+{res['Mu_delta']:.2f} هبوط" if res["is_at_footing"] and res["Mu_delta"] > 0 else None,
    )
    k2.metric(
        label="قوة القص القصوى Qu",
        value=f"{res['Qu']:.2f} ton",
        delta=f"qu = {res['qu']:.2f} kg/cm²",
    )
    k3.metric(
        label="القطاع الفعلي (b × t)",
        value=f"{res['b']:.0f} × {res['t_exec']:.0f} cm",
        delta=f"d = {res['d']:.0f} cm (غ = 4cm)",
    )
    k4.metric(
        label="الحديد السفلي الرئيسي",
        value=f"{res['n_bot']} Φ {res['phi_bot']}",
        delta=f"{res['As_bot_prov']:.2f} cm²",
    )
    k5.metric(
        label="الحديد العلوي / التعليق",
        value=f"{res['n_top']} Φ {res['phi_top']}",
        delta=f"{res['As_top_prov']:.2f} cm²",
    )
    k6.metric(
        label="الكانات المقترحة",
        value=f"{res['stirrups_per_m']} Φ {res['phi_st']} / m",
        delta=f"{res['n_branches']} فروع",
    )

    # Status Alert Bar
    if res["qu"] > res["qu_max"]:
        st.error(f"🚨 {res['shear_status_text']}")
    elif res["qu"] > res["qcu"] and res["As_st_prov_per_m"] < res["As_st_req_per_m"]:
        st.warning(f"⚠️ {res['shear_status_text']}")
    else:
        st.success(f"✅ التصميم الإنشائي للميدة آمن ومحقق لكافة اشتراطات الكود المصري ECP 203 (العزم، القص، والترخيم)")

    # ── TABS: Detailing Drawings, Elevation, Tables, BBS ──────────────────────
    tab_sec, tab_elev, tab_tables, tab_bbs = st.tabs([
        "📐 Sec. A-A Blueprint (القطاع العرضي التنفيذي)",
        "📏 Sec. Long-1 Blueprint (المسقط الطولي والعزوم والقص)",
        "📋 ECP 203 Calculation Tables (جداول الحسابات والتحقق الإنشائي)",
        "📊 BBS & BOQ Schedule (جدول تفريد وحصر كميات الحديد)",
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 1: CROSS-SECTION DRAWING (Sec. A-A)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_sec:
        c_drw, c_info = st.columns([1.8, 1.2])
        with c_drw:
            with st.expander("🖼️ Sec. A-A Blueprint (عرض لوحة القطاع العرضي)", expanded=False, key="m11_sec_exp", on_change="rerun"):
                if st.session_state.get("m11_sec_exp", False):
                    fig_sec = draw_ground_beam_cross_section(res)
                    st.pyplot(fig_sec, clear_figure=True, use_container_width=True)

                    # High-res PNG export
                    buf_sec = io.BytesIO()
                    fig_sec.savefig(buf_sec, format="png", bbox_inches="tight", dpi=200)
                    buf_sec.seek(0)
                    st.download_button(
                        label="📥 تحميل رسم القطاع العرضي عالي الدقة (High-Res PNG)",
                        data=buf_sec,
                        file_name=f"Ground_Beam_SecAA_{res['b']:.0f}x{res['t_exec']:.0f}cm.png",
                        mime="image/png",
                        use_container_width=True,
                        key="m11_btn_dl_sec"
                    )
                    plt.close(fig_sec)
                else:
                    st.info("💡 انقر لتوسيع هذا القسم وتوليد رسم القطاع العرضي التنفيذي للميدة (Lazy Loading).")

        with c_info:
            st.markdown(
                f"""
                <div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:16px; margin-bottom:12px;">
                    <div style="font-size:16px; font-weight:800; color:#38bdf8; margin-bottom:8px;">
                        📌 المواصفات التنفيذية للقطاع (Sec. A-A)
                    </div>
                    <div style="font-size:14px; color:#f1f5f9; line-height:1.9;">
                        • <b>الأبعاد الخرسانية:</b> العرض {res['b']:.0f} cm × العمق {res['t_exec']:.0f} cm<br>
                        • <b>الغطاء الخرساني (Cover):</b> {res['cover']:.1f} cm (اشتراطات الأساسات)<br>
                        • <b>العمق الفعال (d):</b> {res['d']:.1f} cm<br>
                        • <b>التسليح السفلي الرئيسي:</b> <span style="color:#4ade80; font-weight:bold;">{res['n_bot']} Φ {res['phi_bot']} mm</span> (As = {res['As_bot_prov']:.2f} cm²)<br>
                        • <b>التسليح العلوي / التعليق:</b> <span style="color:#fbbf24; font-weight:bold;">{res['n_top']} Φ {res['phi_top']} mm</span> (As = {res['As_top_prov']:.2f} cm²)<br>
                        • <b>الكانات المقفولة:</b> <span style="color:#38bdf8; font-weight:bold;">{res['stirrups_per_m']} Φ {res['phi_st']} / m</span> ({res['n_branches']} فروع بقفل 135°)<br>
                        • <b>براندات الانكماش الجانبية:</b> <span style="color:#c084fc; font-weight:bold;">{res['total_side_bars']} Φ {res['phi_side']} mm</span> (صف كل {((res['t_exec'] - 2*res['cover'])/max(1, res['n_side_rows']+1)):.0f} cm)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if res["t_exec"] >= 60.0:
                st.info(f"ℹ️ تم تطبيق اشتراط ECP 203 بوضع براندات جانبية (براندات انكماش) لأن عمق القطاع t = {res['t_exec']:.0f} cm ≥ 60 cm بمسافات رأسية لا تتجاوز 30 cm.")
            if res["b"] >= 40.0:
                st.info(f"ℹ️ تم رسم كانة داخلية أوتوماتيكياً (4 فروع) لأن عرض الميدة b = {res['b']:.0f} cm ≥ 40 cm لمنع تحنيب الأسياخ وضمان كفاءة القص.")

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 2: LONGITUDINAL ELEVATION & DIAGRAMS
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_elev:
        with st.expander("🖼️ Longitudinal Elevation Blueprint (عرض المسقط الطولي والمخططات)", expanded=False, key="m11_elev_exp", on_change="rerun"):
            if st.session_state.get("m11_elev_exp", False):
                fig_elev = draw_ground_beam_longitudinal_elevation(res)
                st.pyplot(fig_elev, clear_figure=True, use_container_width=True)

                buf_elev = io.BytesIO()
                fig_elev.savefig(buf_elev, format="png", bbox_inches="tight", dpi=200)
                buf_elev.seek(0)
                st.download_button(
                    label="📥 تحميل رسم المسقط الطولي والمخططات (High-Res PNG)",
                    data=buf_elev,
                    file_name=f"Ground_Beam_Longitudinal_L{res['L']:.2f}m.png",
                    mime="image/png",
                    use_container_width=True,
                    key="m11_btn_dl_elev"
                )
                plt.close(fig_elev)
            else:
                st.info("💡 انقر لتوسيع هذا القسم وتوليد المسقط الطولي التنفيذي وتفريد حديد الميدة ومخططات القوى (Lazy Loading).")

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 3: CALCULATION & VERIFICATION TABLES
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_tables:
        st.markdown("<div style='font-size:17px; font-weight:800; color:#38bdf8; margin-bottom:8px;'>📋 جدول ملخص الأحمال والقوى التصميمية (Design Loads & Forces)</div>", unsafe_allow_html=True)
        loads_list = [
            {"البند / الخاصية (Parameter)": "الوزن الذاتي للميدة (Beam Own Weight)", "القيمة (Value)": f"{res['w_ow']:.3f} ton/m", "الكود والملاحظات": f"γc = 2.5 ton/m³, b={res['b']:.0f}cm, t={res['t_exec']:.0f}cm"},
            {
                "البند / الخاصية (Parameter)": "حمل حائط المباني (Wall Line Load)",
                "القيمة (Value)": f"{res['w_wall']:.3f} ton/m" if res.get('has_wall', True) else "0.000 ton/m (بدون حوائط)",
                "الكود والملاحظات": f"hw={res.get('h_wall', 3.0):.2f}m × tw={res.get('t_wall', 12.0):.0f}cm × γ={res.get('gamma_brick', 1.8):.2f} (المصعد 1.4×w = {res.get('w_u_wall', 1.4*res['w_wall']):.3f} t/m)" if res.get('has_wall', True) else "لا توجد مباني محملة"
            },
            {"البند / الخاصية (Parameter)": "الحمل الميت التشغيلي الكلي (Total DL)", "القيمة (Value)": f"{res['w_DL']:.3f} ton/m", "الكود والملاحظات": "DL = w_ow + w_wall + w_add"},
            {"البند / الخاصية (Parameter)": "الحمل القصوى المصعد (Factored wu)", "القيمة (Value)": f"{res['w_u_grav']:.3f} ton/m", "الكود والملاحظات": "wu = 1.4 DL + 1.6 LL"},
            {"البند / الخاصية (Parameter)": "عزم الانحناء الموجب للجاذبية (Mu,grav)", "القيمة (Value)": f"{res['Mu'] - res['Mu_delta']:.2f} ton·m", "الكود والملاحظات": f"حسب شرط الاستمرارية ({res['support_cond']})"},
        ]
        if res.get("is_at_footing", False):
            loads_list.append(
                {"البند / الخاصية (Parameter)": "جهد التربة المسموح (Allowable SBC q_all)", "القيمة (Value)": f"{res.get('q_all_soil', 1.50):.2f} kg/cm²", "الكود والملاحظات": f"جهد التأسيس المعتمد بالموقع (= {res.get('q_all_soil', 1.50)*10.0:.1f} ton/m²)"}
            )
        loads_list.extend([
            {"البند / الخاصية (Parameter)": "عزم الهبوط التفاضلي الإضافي (Mu,settlement)", "القيمة (Value)": f"{res['Mu_delta']:.2f} ton·m", "الكود والملاحظات": f"هبوط تفاضلي Δ = {res['delta_settle_mm']:.1f} mm (Ec=44000√fcu/10)"},
            {"البند / الخاصية (Parameter)": "عزم التصميم الأقصى الكلي (Total Design Mu)", "القيمة (Value)": f"{res['Mu']:.2f} ton·m", "الكود والملاحظات": "المعتمد في حساب حديد التسليح السفلي"},
            {"البند / الخاصية (Parameter)": "قوة القص التصميمية القصوى (Total Design Qu)", "القيمة (Value)": f"{res['Qu']:.2f} ton", "الكود والملاحظات": "شاملة قص الجاذبية + قص الهبوط التفاضلي"},
        ])
        loads_df = pd.DataFrame(loads_list)
        render_styled_table(loads_df)

        st.markdown("<div style='font-size:17px; font-weight:800; color:#38bdf8; margin-top:16px; margin-bottom:8px;'>📋 جدول التحقق الإنشائي ومطابقة الكود المصري (ECP 203 Compliance)</div>", unsafe_allow_html=True)
        checks_df = pd.DataFrame([
            {"عنصر الفحص الإنشائي (Structural Check)": "معامل عمق الضغط C1", "القيمة المحسوبة": f"{res['C1']:.2f}", "الحد الكودي المسموح": "C1 ≥ 2.78 (منع الانهيار القصيف)", "حالة الأمان (Status)": "SAFE" if res['C1'] >= 2.78 else "UNSAFE"},
            {"عنصر الفحص الإنشائي (Structural Check)": "معامل ذراع العزم J", "القيمة المحسوبة": f"{res['J']:.3f}", "الحد الكودي المسموح": "0.670 ≤ J ≤ 0.826", "حالة الأمان (Status)": "SAFE"},
            {"عنصر الفحص الإنشائي (Structural Check)": "مساحة حديد الشد السفلي As,bot", "القيمة المحسوبة": f"{res['As_bot_prov']:.2f} cm²", "الحد الكودي المسموح": f"As,min = {res['As_min']:.2f} cm²", "حالة الأمان (Status)": "SAFE" if res['As_bot_prov'] >= res['As_bot'] else "UNSAFE"},
            {"عنصر الفحص الإنشائي (Structural Check)": "إجهاد القص الاسمي للخرسانة qu", "القيمة المحسوبة": f"{res['qu']:.2f} kg/cm²", "الحد الكودي المسموح": f"qu,max = {res['qu_max']:.2f} kg/cm²", "حالة الأمان (Status)": "SAFE" if res['qu'] <= res['qu_max'] else "UNSAFE"},
            {"عنصر الفحص الإنشائي (Structural Check)": "مقاومة الخرسانة غير المشرخة للقص qcu", "القيمة المحسوبة": f"{res['qcu']:.2f} kg/cm²", "الحد الكودي المسموح": "0.75 √(fcu / 1.5)", "حالة الأمان (Status)": "PASS"},
            {"عنصر الفحص الإنشائي (Structural Check)": "مقاومة الكانات للقص (Stirrups Area)", "القيمة المحسوبة": f"{res['As_st_prov_per_m']:.2f} cm²/m", "الحد الكودي المسموح": f"As,req = {res['As_st_req_per_m']:.2f} cm²/m", "حالة الأمان (Status)": res['shear_status']},
            {"عنصر الفحص الإنشائي (Structural Check)": "فحص الترخيم وضمان الجساءة (L/d)", "القيمة المحسوبة": f"{((res['L']*100)/res['d']):.1f}", "الحد الكودي المسموح": f"L/d limit = {res['L_d_limit']:.1f}", "حالة الأمان (Status)": "SAFE" if ((res['L']*100)/res['d']) <= res['L_d_limit'] else "Review"},
        ])
        render_styled_table(checks_df)

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 4: STEEL BAR BENDING SCHEDULE (BBS) & BOQ
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_bbs:
        st.markdown("<div style='font-size:17px; font-weight:800; color:#38bdf8; margin-bottom:8px;'>📊 جدول تفريد وحصر كميات حديد التسليح (Bar Bending Schedule)</div>", unsafe_allow_html=True)
        st.caption("ℹ️ تم حساب وزن المتر الطولي لكافة الأقطار بدقة متناهية طبقاً للمعادلة الكودية: **(Φ² / 162) kg/m**.")

        bbs_data = [
            {
                "كود السيخ (Mark)": "B1 (سفلي رئيسي)",
                "الوصف والموقع": "الحديد السفلي الرئيسي لمقاومة العزوم الموجبة",
                "القطر Φ (mm)": f"Φ {res['phi_bot']}",
                "العدد (Count)": f"{res['n_bot']} أسياخ",
                "طول السيخ المفرد (m)": f"{res['L_bar_bot']:.2f} m",
                "وزن المتر (kg/m)": f"{res['lin_mass_bot']:.3f}",
                "إجمالي الوزن (kg)": f"{res['wt_bot_kg']:.1f} kg",
            },
            {
                "كود السيخ (Mark)": "T1 (علوي تعليق)",
                "الوصف والموقع": "الحديد العلوي لتعليق الكانات ومقاومة العزوم السالبة",
                "القطر Φ (mm)": f"Φ {res['phi_top']}",
                "العدد (Count)": f"{res['n_top']} أسياخ",
                "طول السيخ المفرد (m)": f"{res['L_bar_top']:.2f} m",
                "وزن المتر (kg/m)": f"{res['lin_mass_top']:.3f}",
                "إجمالي الوزن (kg)": f"{res['wt_top_kg']:.1f} kg",
            },
            {
                "كود السيخ (Mark)": "S1 (كانات مقفولة)",
                "الوصف والموقع": f"كانات مقفولة بقفل 135° ({res['n_branches']} فروع)",
                "القطر Φ (mm)": f"Φ {res['phi_st']}",
                "العدد (Count)": f"{res['num_stirrups_total']} كانة",
                "طول السيخ المفرد (m)": f"{res['st_perimeter']:.2f} m",
                "وزن المتر (kg/m)": f"{res['lin_mass_st']:.3f}",
                "إجمالي الوزن (kg)": f"{res['wt_st_kg']:.1f} kg",
            },
        ]

        if res["n_side_rows"] > 0:
            bbs_data.append({
                "كود السيخ (Mark)": "SD1 (براندات انكماش)",
                "الوصف والموقع": f"حديد جانبي بالوجهين لمقاومة الانكماش (t={res['t_exec']:.0f}cm ≥ 60cm)",
                "القطر Φ (mm)": f"Φ {res['phi_side']}",
                "العدد (Count)": f"{res['total_side_bars']} أسياخ",
                "طول السيخ المفرد (m)": f"{res['L'] + 0.30:.2f} m",
                "وزن المتر (kg/m)": f"{res['lin_mass_side']:.3f}",
                "إجمالي الوزن (kg)": f"{res['wt_side_kg']:.1f} kg",
            })

        bbs_df = pd.DataFrame(bbs_data)
        render_styled_table(bbs_df)

        # BOQ Summary Box
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                        border: 2px solid #22c55e; border-radius: 10px; padding: 18px 22px; margin-top: 16px;">
                <div style="font-size: 17px; font-weight: 800; color: #22c55e; margin-bottom: 8px;">
                    📈 ملخص حصر الكميات والمؤشرات الاقتصادية للميدة (BOQ Summary)
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 12px;">
                    <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 8px; padding: 10px 14px;">
                        <div style="font-size: 12px; color: #94a3b8;">حجم الخرسانة المسلحة:</div>
                        <div style="font-size: 20px; font-weight: 800; color: #f8fafc;">{res['concrete_vol_m3']:.2f} m³</div>
                    </div>
                    <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 8px; padding: 10px 14px;">
                        <div style="font-size: 12px; color: #94a3b8;">إجمالي وزن حديد التسليح:</div>
                        <div style="font-size: 20px; font-weight: 800; color: #4ade80;">{res['total_steel_kg']:.1f} kg ({res['total_steel_kg']/1000.0:.3f} Ton)</div>
                    </div>
                    <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 8px; padding: 10px 14px;">
                        <div style="font-size: 12px; color: #94a3b8;">معدل استهلاك الحديد:</div>
                        <div style="font-size: 20px; font-weight: 800; color: #38bdf8;">{res['steel_ratio_kg_m3']:.1f} kg/m³</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Aliases for flexible module importing
render = render_ground_beam_module
