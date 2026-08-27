"""
modules/ground_slab.py
----------------------
Comprehensive Engineering Design & Detailing Module for Ground Slabs / Slab on Grade (SOG)
According to Egyptian Code of Practice ECP 203-2018, ECP Soil Mechanics & Foundations, and ACI 360R / PCA Standards.
"""

import os
import io
import math
import base64
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon, Arc

from modules import settings as S
from modules.steel_bars import BAR_MAP, DIAMETERS, BARS

BAR_WEIGHTS = {b["dia_mm"]: b["weight_kgm"] for b in BARS}
BAR_AREAS = {b["dia_mm"]: b["area_cm2"] for b in BARS}


# ===============================================================================
#  ENGINEERING COMPUTATION ENGINE FOR SLAB ON GRADE (SOG)
# ===============================================================================

def compute_ground_slab_design(
    Lx_m: float = 30.0,
    Ly_m: float = 20.0,
    ts_cm: float = 20.0,
    cover_cm: float = 4.0,
    fcu_kg_cm2: float = 300.0,
    fy_kg_cm2: float = 4200.0,
    ks_kg_cm3: float = 5.0,
    q_all_kg_cm2: float = 1.5,
    h_base_cm: float = 20.0,
    w_ll_ton_m2: float = 2.5,
    p_wheel_ton: float = 4.0,
    wheel_b_cm: float = 20.0,
    wheel_l_cm: float = 25.0,
    p_post_ton: float = 3.5,
    post_bp_cm: float = 15.0,
    post_tp_cm: float = 15.0,
    mesh_type: str = "شبكة علوية وسفلية (Double Mesh)",
    phi_mesh_mm: int = 10,
    spacing_mesh_cm: float = 20.0,
    joint_spacing_x_m: float = 4.5,
    joint_spacing_y_m: float = 4.5,
    dowel_phi_mm: int = 20,
    dowel_len_cm: float = 45.0,
    dowel_spacing_cm: float = 30.0,
) -> dict:
    """
    Executes full structural, geotechnical, flexural, punching shear,
    and contraction joints analysis for Ground Slab according to ECP 203 / ACI 360R.
    """
    Ec = 14000.0 * math.sqrt(fcu_kg_cm2)  # kg/cm²
    nu = 0.15
    d_eff = max(ts_cm - cover_cm, 5.0)
    gamma_c = 2.5  # ton/m³

    fcu_mpa = fcu_kg_cm2 / 10.0
    fctr_mpa = 0.6 * math.sqrt(fcu_mpa)
    fctr_kg_cm2 = fctr_mpa * 10.0

    safety_factor_flexure = 1.70
    sigma_all_flexure = fctr_kg_cm2 / safety_factor_flexure

    num_stiff = Ec * (ts_cm ** 3)
    den_stiff = 12.0 * (1.0 - nu ** 2) * ks_kg_cm3
    radius_rel_stiffness_cm = (num_stiff / den_stiff) ** 0.25

    area_contact_wheel = wheel_b_cm * wheel_l_cm
    a_wheel = math.sqrt(area_contact_wheel / math.pi)
    if a_wheel < 1.724 * ts_cm:
        b_prime_wheel = math.sqrt(1.6 * (a_wheel ** 2) + (ts_cm ** 2)) - 0.675 * ts_cm
    else:
        b_prime_wheel = a_wheel

    P_wheel_kg = p_wheel_ton * 1000.0
    sigma_i_wheel = (3.0 * P_wheel_kg * (1.0 + nu) / (2.0 * math.pi * (ts_cm ** 2))) * (
        math.log(radius_rel_stiffness_cm / max(b_prime_wheel, 0.1)) + 0.6159
    )
    sigma_e_wheel = (3.0 * (1.0 + nu) * P_wheel_kg / (math.pi * (3.0 + nu) * (ts_cm ** 2))) * (
        math.log(Ec * (ts_cm ** 3) / (100.0 * ks_kg_cm3 * (a_wheel ** 4))) + 3.84 - (4.0 * nu / 3.0)
    )
    term_corner = (a_wheel * math.sqrt(2.0) / radius_rel_stiffness_cm) ** 0.6
    sigma_c_wheel = (3.0 * P_wheel_kg / (ts_cm ** 2)) * (1.0 - term_corner)
    max_wheel_stress = max(sigma_i_wheel, sigma_e_wheel, sigma_c_wheel)

    area_contact_post = post_bp_cm * post_tp_cm
    a_post = math.sqrt(area_contact_post / math.pi)
    if a_post < 1.724 * ts_cm:
        b_prime_post = math.sqrt(1.6 * (a_post ** 2) + (ts_cm ** 2)) - 0.675 * ts_cm
    else:
        b_prime_post = a_post

    P_post_kg = p_post_ton * 1000.0
    sigma_i_post = (3.0 * P_post_kg * (1.0 + nu) / (2.0 * math.pi * (ts_cm ** 2))) * (
        math.log(radius_rel_stiffness_cm / max(b_prime_post, 0.1)) + 0.6159
    )
    sigma_e_post = (3.0 * (1.0 + nu) * P_post_kg / (math.pi * (3.0 + nu) * (ts_cm ** 2))) * (
        math.log(Ec * (ts_cm ** 3) / (100.0 * ks_kg_cm3 * (a_post ** 4))) + 3.84 - (4.0 * nu / 3.0)
    )
    term_corner_post = (a_post * math.sqrt(2.0) / radius_rel_stiffness_cm) ** 0.6
    sigma_c_post = (3.0 * P_post_kg / (ts_cm ** 2)) * (1.0 - term_corner_post)
    max_post_stress = max(sigma_i_post, sigma_e_post, sigma_c_post)

    sigma_act_flexure = max(max_wheel_stress, max_post_stress)
    ratio_flexure = sigma_act_flexure / sigma_all_flexure
    is_flexure_safe = ratio_flexure <= 1.0

    bo_post = 2.0 * (post_bp_cm + d_eff) + 2.0 * (post_tp_cm + d_eff)
    Pu_post_kg = 1.5 * P_post_kg
    qup_post = Pu_post_kg / (bo_post * d_eff)

    qcu_punching_kg_cm2 = 0.316 * math.sqrt(fcu_mpa / 1.5) * 10.0
    ratio_punching = qup_post / qcu_punching_kg_cm2
    is_punching_safe = ratio_punching <= 1.0

    q_dead_kg_cm2 = (ts_cm * gamma_c * 1000.0 / 10000.0) / 1000.0 * 10.0
    q_live_kg_cm2 = (w_ll_ton_m2 * 1000.0) / 10000.0
    q_total_act_kg_cm2 = q_dead_kg_cm2 + q_live_kg_cm2
    ratio_soil = q_total_act_kg_cm2 / q_all_kg_cm2
    is_soil_safe = ratio_soil <= 1.0

    delta_subgrade_mm = (q_live_kg_cm2 / ks_kg_cm3) * 10.0
    delta_all_mm = 3.0
    is_deflection_safe = delta_subgrade_mm <= delta_all_mm

    mu_friction = 1.5
    L_joint_max_m = max(joint_spacing_x_m, joint_spacing_y_m)
    W_slab_kg_m2 = (ts_cm / 100.0) * 2500.0
    fs_allowable = 0.60 * (fy_kg_cm2)

    As_drag_cm2_m = (mu_friction * W_slab_kg_m2 * L_joint_max_m) / (2.0 * fs_allowable)
    As_min_ecp_cm2_m = 0.0015 * 100.0 * ts_cm
    As_required_cm2_m = max(As_drag_cm2_m, As_min_ecp_cm2_m)

    area_bar_cm2 = (math.pi * ((phi_mesh_mm / 10.0) ** 2)) / 4.0
    bars_per_meter = 100.0 / spacing_mesh_cm
    n_mesh_layers = 2 if ("Double" in mesh_type or "علوية وسفلية" in mesh_type) else 1
    As_provided_cm2_m = n_mesh_layers * bars_per_meter * area_bar_cm2

    ratio_rebar = As_required_cm2_m / As_provided_cm2_m
    is_rebar_safe = As_provided_cm2_m >= As_required_cm2_m

    max_rec_joint_spacing_m = min((25.0 * ts_cm) / 100.0, 5.5)
    saw_cut_depth_cm = ts_cm / 4.0

    num_bays_x = max(int(math.ceil(Lx_m / joint_spacing_x_m)), 1)
    num_bays_y = max(int(math.ceil(Ly_m / joint_spacing_y_m)), 1)
    actual_bay_lx = Lx_m / num_bays_x
    actual_bay_ly = Ly_m / num_bays_y
    aspect_ratio_bay = max(actual_bay_lx, actual_bay_ly) / min(actual_bay_lx, actual_bay_ly)
    is_aspect_ratio_safe = aspect_ratio_bay <= 1.25

    total_area_m2 = Lx_m * Ly_m
    concrete_vol_m3 = total_area_m2 * (ts_cm / 100.0)
    subbase_vol_m3 = total_area_m2 * (h_base_cm / 100.0)
    vapor_barrier_m2 = total_area_m2 * 1.10

    joint_length_y_lines = (num_bays_x - 1) * Ly_m
    joint_length_x_lines = (num_bays_y - 1) * Lx_m
    total_joint_length_m = joint_length_y_lines + joint_length_x_lines

    total_dowels_count = int(math.ceil((total_joint_length_m * 100.0) / dowel_spacing_cm))
    dowel_weight_per_m = BAR_WEIGHTS.get(dowel_phi_mm, 2.47)
    total_dowel_weight_kg = total_dowels_count * (dowel_len_cm / 100.0) * dowel_weight_per_m
    total_dowel_weight_ton = total_dowel_weight_kg / 1000.0

    mesh_weight_per_m = BAR_WEIGHTS.get(phi_mesh_mm, 0.617)
    total_rebar_lin_m = n_mesh_layers * (
        (Lx_m * (Ly_m / (spacing_mesh_cm / 100.0))) +
        (Ly_m * (Lx_m / (spacing_mesh_cm / 100.0)))
    )
    total_mesh_weight_kg = total_rebar_lin_m * mesh_weight_per_m
    total_mesh_weight_ton = total_mesh_weight_kg / 1000.0

    total_steel_weight_ton = total_mesh_weight_ton + total_dowel_weight_ton
    steel_rate_kg_m3 = (total_steel_weight_ton * 1000.0) / concrete_vol_m3 if concrete_vol_m3 > 0 else 0.0

    all_checks_safe = (
        is_flexure_safe and
        is_punching_safe and
        is_soil_safe and
        is_rebar_safe and
        is_aspect_ratio_safe
    )

    return {
        "Lx_m": Lx_m,
        "Ly_m": Ly_m,
        "ts_cm": ts_cm,
        "cover_cm": cover_cm,
        "d_eff_cm": d_eff,
        "fcu_kg_cm2": fcu_kg_cm2,
        "fy_kg_cm2": fy_kg_cm2,
        "fctr_kg_cm2": fctr_kg_cm2,
        "sigma_all_flexure": sigma_all_flexure,
        "ks_kg_cm3": ks_kg_cm3,
        "q_all_kg_cm2": q_all_kg_cm2,
        "radius_rel_stiffness_cm": radius_rel_stiffness_cm,
        "w_ll_ton_m2": w_ll_ton_m2,
        "p_wheel_ton": p_wheel_ton,
        "p_post_ton": p_post_ton,
        "sigma_act_flexure": sigma_act_flexure,
        "ratio_flexure": ratio_flexure,
        "is_flexure_safe": is_flexure_safe,
        "qup_post_kg_cm2": qup_post,
        "qcu_punching_kg_cm2": qcu_punching_kg_cm2,
        "ratio_punching": ratio_punching,
        "is_punching_safe": is_punching_safe,
        "q_total_act_kg_cm2": q_total_act_kg_cm2,
        "ratio_soil": ratio_soil,
        "is_soil_safe": is_soil_safe,
        "delta_subgrade_mm": delta_subgrade_mm,
        "delta_all_mm": delta_all_mm,
        "is_deflection_safe": is_deflection_safe,
        "As_drag_cm2_m": As_drag_cm2_m,
        "As_min_ecp_cm2_m": As_min_ecp_cm2_m,
        "As_required_cm2_m": As_required_cm2_m,
        "As_provided_cm2_m": As_provided_cm2_m,
        "ratio_rebar": ratio_rebar,
        "is_rebar_safe": is_rebar_safe,
        "mesh_type": mesh_type,
        "phi_mesh_mm": phi_mesh_mm,
        "spacing_mesh_cm": spacing_mesh_cm,
        "n_mesh_layers": n_mesh_layers,
        "max_rec_joint_spacing_m": max_rec_joint_spacing_m,
        "saw_cut_depth_cm": saw_cut_depth_cm,
        "num_bays_x": num_bays_x,
        "num_bays_y": num_bays_y,
        "actual_bay_lx": actual_bay_lx,
        "actual_bay_ly": actual_bay_ly,
        "aspect_ratio_bay": aspect_ratio_bay,
        "is_aspect_ratio_safe": is_aspect_ratio_safe,
        "dowel_phi_mm": dowel_phi_mm,
        "dowel_len_cm": dowel_len_cm,
        "dowel_spacing_cm": dowel_spacing_cm,
        "total_dowels_count": total_dowels_count,
        "total_dowel_weight_ton": total_dowel_weight_ton,
        "total_area_m2": total_area_m2,
        "concrete_vol_m3": concrete_vol_m3,
        "subbase_vol_m3": subbase_vol_m3,
        "vapor_barrier_m2": vapor_barrier_m2,
        "total_joint_length_m": total_joint_length_m,
        "total_mesh_weight_ton": total_mesh_weight_ton,
        "total_steel_weight_ton": total_steel_weight_ton,
        "steel_rate_kg_m3": steel_rate_kg_m3,
        "all_checks_safe": all_checks_safe,
    }


# ===============================================================================
#  2D MATPLOTLIB PROFESSIONAL CAD DRAWINGS GENERATOR
# ===============================================================================

def generate_ground_slab_plan_and_detail_sketches(res: dict) -> tuple:
    """
    Renders two high-res 2D engineering blueprints:
    1. Full 2D Floor Plan with Joints Grid, Dowels, and Loads Footprint.
    2. Detailed Cross-Section in Contraction / Saw-Cut Joint with Dowel & Sealant.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    Lx = res["Lx_m"]
    Ly = res["Ly_m"]
    nb_x = res["num_bays_x"]
    nb_y = res["num_bays_y"]
    bay_lx = res["actual_bay_lx"]
    bay_ly = res["actual_bay_ly"]
    ts = res["ts_cm"]

    # FIG 1: 2D Floor Plan
    fig1, ax1 = plt.subplots(figsize=(16, 11), dpi=140, facecolor="#ffffff")
    ax1.set_facecolor("#f8fafc")

    slab_rect = Rectangle((0, 0), Lx, Ly, linewidth=3.0, edgecolor="#0f172a", facecolor="#f1f5f9", zorder=2)
    ax1.add_patch(slab_rect)

    for i in range(1, nb_x):
        x_pos = i * bay_lx
        ax1.plot([x_pos, x_pos], [0, Ly], color="#dc2626", linestyle="--", linewidth=2.0, zorder=3)
        for y_d in np.linspace(1.0, Ly - 1.0, min(int(Ly / 1.2), 12)):
            ax1.plot([x_pos - 0.25, x_pos + 0.25], [y_d, y_d], color="#2563eb", linewidth=3.5, zorder=4)

    for j in range(1, nb_y):
        y_pos = j * bay_ly
        ax1.plot([0, Lx], [y_pos, y_pos], color="#dc2626", linestyle="--", linewidth=2.0, zorder=3)
        for x_d in np.linspace(1.0, Lx - 1.0, min(int(Lx / 1.2), 16)):
            ax1.plot([x_d, x_d], [y_pos - 0.25, y_pos + 0.25], color="#2563eb", linewidth=3.5, zorder=4)

    cx = Lx / 2.0
    cy = Ly / 2.0
    for ox in [-1.5, 1.5]:
        for oy in [-1.5, 1.5]:
            post_p = Rectangle((cx + ox - 0.2, cy + oy - 0.2), 0.4, 0.4, facecolor="#f59e0b", edgecolor="#b45309", linewidth=2.0, zorder=5)
            ax1.add_patch(post_p)
            ax1.text(cx + ox, cy + oy + 0.35, f"Post P={res['p_post_ton']:.1f}t", color="#92400e", fontsize=10, fontweight="bold", ha="center", zorder=6)

    ax1.annotate(
        f"Forklift Axle P={res['p_wheel_ton']:.1f} Ton",
        xy=(bay_lx * 0.5, bay_ly * 0.5),
        xytext=(bay_lx * 0.5, bay_ly * 0.85),
        arrowprops=dict(facecolor="#10b981", edgecolor="#065f46", shrink=0.08, width=2.5, headwidth=8),
        fontsize=11,
        fontweight="bold",
        color="#065f46",
        ha="center",
        zorder=6,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#ecfdf5", edgecolor="#10b981", alpha=0.95),
    )

    for i in range(nb_x):
        for j in range(nb_y):
            bx_center = (i + 0.5) * bay_lx
            by_center = (j + 0.5) * bay_ly
            ax1.text(
                bx_center, by_center - 0.2,
                f"Bay {i+1}-{j+1}\n{bay_lx:.2f}m × {bay_ly:.2f}m",
                fontsize=11, color="#64748b", ha="center", va="center", fontweight="bold", alpha=0.7, zorder=3
            )

    pad_dim = max(Lx, Ly) * 0.08
    ax1.annotate("", xy=(0, -pad_dim*0.6), xytext=(Lx, -pad_dim*0.6), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.0))
    ax1.text(Lx / 2.0, -pad_dim*0.9, f"Total Length Lx = {Lx:.2f} m", fontsize=14, fontweight="900", color="#0f172a", ha="center")

    ax1.annotate("", xy=(-pad_dim*0.6, 0), xytext=(-pad_dim*0.6, Ly), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.0))
    ax1.text(-pad_dim*0.9, Ly / 2.0, f"Total Width Ly = {Ly:.2f} m", fontsize=14, fontweight="900", color="#0f172a", va="center", rotation=90)

    ax1.set_title(
        f"ECP 203 / ACI 360R — Ground Slab Layout Plan (ts = {ts:.0f} cm)\n"
        f"Reinforcement: {res['mesh_type']} Φ{res['phi_mesh_mm']} @ {res['spacing_mesh_cm']:.0f} cm | Dowels: Φ{res['dowel_phi_mm']} L={res['dowel_len_cm']:.0f}cm @ {res['dowel_spacing_cm']:.0f}cm",
        fontsize=14, fontweight="900", color="#1e3a8a", pad=16
    )

    ax1.set_xlim(-pad_dim*1.4, Lx + pad_dim*0.8)
    ax1.set_ylim(-pad_dim*1.4, Ly + pad_dim*0.8)
    ax1.set_aspect("equal", "box")
    ax1.axis("off")

    buf1 = io.BytesIO()
    fig1.savefig(buf1, format="png", bbox_inches="tight", dpi=140)
    plt.close(fig1)
    buf1.seek(0)
    b64_plan = base64.b64encode(buf1.getvalue()).decode("utf-8")

    # FIG 2: Cross Section Detail
    fig2, ax2 = plt.subplots(figsize=(15, 8.5), dpi=140, facecolor="#ffffff")
    ax2.set_facecolor("#ffffff")

    W_det = 120.0
    ts_det = ts
    cut_d = res["saw_cut_depth_cm"]

    ax2.add_patch(Rectangle((-W_det/2, -35), W_det, 35, facecolor="#e2e8f0", edgecolor="#94a3b8", hatch="//", alpha=0.7))
    ax2.text(0, -22, "Subbase Course / Well-compacted Granular Layer (20 cm)", color="#475569", fontsize=12, fontweight="bold", ha="center")

    ax2.plot([-W_det/2, W_det/2], [0, 0], color="#0284c7", linewidth=3.0, linestyle=":")
    ax2.text(W_det/2 - 18, 2.5, "Vapor Barrier (PE Sheet)", color="#0284c7", fontsize=11, fontweight="bold")

    cut_w = 0.6  # cm saw-cut slot width
    # Left Concrete Slab Body
    poly_left = Polygon([
        [-W_det/2, 0],
        [0, 0],
        [0, ts_det - cut_d],
        [-cut_w/2, ts_det - cut_d],
        [-cut_w/2, ts_det],
        [-W_det/2, ts_det]
    ], facecolor="#cbd5e1", edgecolor="#1e293b", linewidth=2.5)
    ax2.add_patch(poly_left)

    # Right Concrete Slab Body
    poly_right = Polygon([
        [0, 0],
        [W_det/2, 0],
        [W_det/2, ts_det],
        [cut_w/2, ts_det],
        [cut_w/2, ts_det - cut_d],
        [0, ts_det - cut_d]
    ], facecolor="#cbd5e1", edgecolor="#1e293b", linewidth=2.5)
    ax2.add_patch(poly_right)

    # Natural Jagged Induced Crack Line (Aggregate Interlock) below saw-cut
    crack_y = np.linspace(0, ts_det - cut_d, 20)
    crack_x = np.sin(crack_y * 1.5) * 0.25
    ax2.plot(crack_x, crack_y, color="#b91c1c", linestyle="-.", linewidth=2.0, zorder=5)

    # Joint Sealant & Backer Rod inside the Saw-cut slot
    ax2.add_patch(Rectangle((-cut_w/2, ts_det - cut_d), cut_w, cut_d, facecolor="#0f172a", edgecolor="#0f172a", zorder=4))
    ax2.add_patch(Circle((0, ts_det - cut_d + 0.4), radius=0.3, facecolor="#f59e0b", edgecolor="#d97706", zorder=5))

    # Rebar Mesh (Top & Bottom or Single)
    rebar_y_btm = res["cover_cm"]
    rebar_y_top = ts_det - res["cover_cm"]

    ax2.plot([-W_det/2 + 6, -3], [rebar_y_btm, rebar_y_btm], color="#15803d", linewidth=3.0)
    ax2.plot([3, W_det/2 - 6], [rebar_y_btm, rebar_y_btm], color="#15803d", linewidth=3.0)

    if res["n_mesh_layers"] == 2:
        ax2.plot([-W_det/2 + 6, -3], [rebar_y_top, rebar_y_top], color="#15803d", linewidth=3.0)
        ax2.plot([3, W_det/2 - 6], [rebar_y_top, rebar_y_top], color="#15803d", linewidth=3.0)

    # Smooth Dowel Bar with Debonding Sleeve / Greased Half
    dowel_len = res["dowel_len_cm"]
    dowel_y = ts_det / 2.0
    d_phi_cm = res["dowel_phi_mm"] / 10.0

    # Embedded Half (Left)
    ax2.add_patch(FancyBboxPatch((-dowel_len/2, dowel_y - d_phi_cm/2), dowel_len/2, d_phi_cm, boxstyle="square", facecolor="#2563eb", edgecolor="#1d4ed8", linewidth=2.0, zorder=6))
    # Greased / Sleeved Half (Right)
    ax2.add_patch(FancyBboxPatch((0, dowel_y - d_phi_cm/2), dowel_len/2, d_phi_cm, boxstyle="square", facecolor="#38bdf8", edgecolor="#0284c7", linewidth=2.0, zorder=6))
    # Expansion Cap on Right Tip
    ax2.add_patch(Rectangle((dowel_len/2 - 2.5, dowel_y - d_phi_cm/2 - 0.15), 2.5, d_phi_cm + 0.3, facecolor="#ef4444", edgecolor="#b91c1c", linewidth=1.5, zorder=7))

    # Annotations
    ax2.annotate(
        f"Saw-Cut Slot (Depth = ts/4 = {cut_d:.1f} cm)\nwith Polyurethane Sealant & Backer Rod",
        xy=(0, ts_det),
        xytext=(0, ts_det + 12),
        arrowprops=dict(arrowstyle="->", color="#0f172a", lw=2.0),
        fontsize=12, fontweight="bold", color="#0f172a", ha="center"
    )

    ax2.annotate(
        f"Controlled Induced Crack (شرخ انكماش موجه)\nwith Aggregate Interlock (تعشيق الركام)",
        xy=(0, (ts_det - cut_d) * 0.35),
        xytext=(28, (ts_det - cut_d) * 0.35 - 8),
        arrowprops=dict(arrowstyle="->", color="#b91c1c", lw=2.0),
        fontsize=11, fontweight="bold", color="#b91c1c", ha="left"
    )

    ax2.annotate(
        f"Smooth Dowel Bar Φ{res['dowel_phi_mm']} mm (L={dowel_len:.0f} cm @ {res['dowel_spacing_cm']:.0f} cm c/c)\n[Greased / Sleeved on Free Side]",
        xy=(dowel_len/4, dowel_y),
        xytext=(dowel_len/4, dowel_y + 10),
        arrowprops=dict(arrowstyle="->", color="#0284c7", lw=2.0),
        fontsize=12, fontweight="bold", color="#0284c7", ha="center"
    )

    ax2.annotate(
        f"Reinforcement: {res['mesh_type']}\nΦ{res['phi_mesh_mm']} @ {res['spacing_mesh_cm']:.0f} cm (Both Directions)",
        xy=(-W_det/3, rebar_y_btm),
        xytext=(-W_det/3, rebar_y_btm - 12),
        arrowprops=dict(arrowstyle="->", color="#15803d", lw=2.0),
        fontsize=12, fontweight="bold", color="#15803d", ha="center"
    )

    ax2.annotate("", xy=(-W_det/2 + 2, 0), xytext=(-W_det/2 + 2, ts_det), arrowprops=dict(arrowstyle="<->", color="#b91c1c", lw=2.5))
    ax2.text(-W_det/2 - 6, ts_det / 2.0, f"ts = {ts:.0f} cm", fontsize=14, fontweight="900", color="#b91c1c", va="center", rotation=90)

    ax2.set_title(f"ECP 203 / ACI 360R — Saw-Cut Contraction Joint & Dowel Bar Cross-Section Detail", fontsize=14, fontweight="900", color="#1e3a8a", pad=18)
    ax2.set_xlim(-W_det/2 - 14, W_det/2 + 14)
    ax2.set_ylim(-40, ts_det + 22)
    ax2.set_aspect("equal", "box")
    ax2.axis("off")

    buf2 = io.BytesIO()
    fig2.savefig(buf2, format="png", bbox_inches="tight", dpi=140)
    plt.close(fig2)
    buf2.seek(0)
    b64_detail = base64.b64encode(buf2.getvalue()).decode("utf-8")

    return b64_plan, b64_detail


# ===============================================================================
#  STREAMLIT UI RENDERER FOR GROUND SLAB
# ===============================================================================

def render():
    """Renders the complete luxury Ground Slab (Slab on Grade) Design Suite."""
    col_hdr_main, col_hdr_actions = st.columns([3.6, 1.4])
    with col_hdr_main:
        st.markdown(
            """
            <div dir="rtl" style="
                background: linear-gradient(135deg, #0b1329 0%, #1e293b 50%, #0b1329 100%);
                padding: 12px 20px;
                border-radius: 12px;
                border: 1.5px solid rgba(56, 189, 248, 0.4);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                min-height: 82px;
            ">
                <div style="display: flex; justify-content: center; align-items: center; gap: 12px; flex-wrap: wrap;">
                    <span style="font-size: 30px;">🏗️</span>
                    <span style="font-size: 26px; font-weight: 900; color: #ffffff; letter-spacing: 0.5px;">
                        تصميم البلاطات الأرضية الخرسانية (Slab on Grade / Ground Slab)
                    </span>
                    <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1.5px solid #38bdf8; padding: 4px 14px; border-radius: 12px; font-size: 14px; font-weight: 800;">
                        ECP 203 · ACI 360R
                    </span>
                </div>
                <div style="color: #cbd5e1; font-size: 15px; font-weight: 700; margin-top: 5px; text-align: center;">
                    إجهادات ويسترجارد (Westergaard) · فحص القص الثاقب للأرفف والمعدات · تسليح الفواصل والدواول
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_hdr_actions:
        with st.container(border=True):
            c_b1, c_b2 = st.columns([1.2, 0.9])
            with c_b1:
                is_help_open = st.session_state.get("_show_gs_help_panel", False)
                btn_txt = "Close Help" if is_help_open else "💡 Help"
                if st.button(btn_txt, key="btn_help_ground_slab", use_container_width=True, type="primary" if not is_help_open else "secondary"):
                    st.session_state["_show_gs_help_panel"] = not is_help_open
                    st.rerun()
            with c_b2:
                word_doc_path = r"e:\Concrete design\دليل_تصميم_ومدخلات_البلاطات_الأرضية_ECP203_ACI360R.docx"
                if os.path.exists(word_doc_path):
                    with open(word_doc_path, "rb") as f_word:
                        word_bytes = f_word.read()
                    st.download_button(
                        "📥 Word",
                        data=word_bytes,
                        file_name="Ground_Slab_Design_Manual_ECP203.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "📐 1. المدخلات والأحمال والتربة (Inputs & Soil)",
        "⚙️ 2. فحص الإجهادات والقص (Analysis & Checks)",
        "🔗 3. تصميم الفواصل والدواول (Joints & Dowels)",
        "📊 4. المخططات والكميات (CAD Drawings & BOQ)",
    ])

    with tab1:
        st.markdown(
            """
            <div class="input-section-header">
                <span style="font-size: 26px;">📥</span>
                <span>مدخلات ومواصفات البلاطة الأرضية والتربة والأحمال (Ground Slab Design Inputs)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.get("_show_gs_help_panel", False):
            st.markdown(
                """
                <style>
                [data-testid="stExpander"] details summary p {
                    font-size: 20px !important;
                    font-weight: 900 !important;
                    color: #38bdf8 !important;
                    line-height: 1.5 !important;
                }
                [data-testid="stExpander"] details summary svg {
                    width: 20px !important;
                    height: 20px !important;
                }
                </style>
                <div style='margin-top: 10px;'></div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("🌍 1. خواص التربة وطبقة الإحلال (Subgrade & Base Properties) — [اضغط للتفاصيل]", expanded=True):
                st.markdown(
                    """
                    <div dir="rtl" style="text-align: right; font-size: 18px; line-height: 2.1; color: #ffffff; padding: 8px 12px;">
                    <ul style="padding-right: 22px; list-style-type: square;">
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">معامل رد فعل التربة ks (القيمة الافتراضية = 5.0 kg/cm³):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">المدلول الفيزيائي والهندسي:</b> <span style="font-size: 18px; color: #ffffff;">يمثل الصلابة الزنبركية لفرشة التأسيس (Spring Stiffness = ΔP / Δδ) ويقاس باختبار التحميل باللوح (Plate Load Test بقطر 75 سم).</span>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">لماذا تم اختيار 5.0 kg/cm³ تحديداً؟</b> <span style="font-size: 18px; color: #ffffff;">هي القيمة الوسطية الآمنة والشائعة لمعظم المواقع التي تم تسويتها مع فرش طبقة إحلال مدموكة.</span>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">القيم الحقلية المرجعية حسب نوع التربة:</b>
                            <br>&nbsp;&nbsp;&nbsp;&nbsp;▫️ <span style="font-size: 18px; color: #cbd5e1;">تربة طينية رخوة:</span> <b style="font-size: 18px; color: #f87171;">1.5 – 3.0 kg/cm³</b>
                            <br>&nbsp;&nbsp;&nbsp;&nbsp;▫️ <span style="font-size: 18px; color: #cbd5e1;">تربة رملية مدموكة / طمي:</span> <b style="font-size: 18px; color: #fbbf24;">3.5 – 5.5 kg/cm³</b>
                            <br>&nbsp;&nbsp;&nbsp;&nbsp;▫️ <span style="font-size: 18px; color: #cbd5e1;">طبقة إحلال من كسر الحصى والسن المدموك ≥ 98%:</span> <b style="font-size: 18px; color: #4ade80;">6.0 – 10.0 kg/cm³</b>
                        </li>
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">إجهاد التأسيس المسموح للتربة q_all (القيمة الافتراضية = 1.50 kg/cm² = 15 ton/m²):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">المدلول الهندسي والتطبيقي:</b> <span style="font-size: 18px; color: #ffffff;">قدرة التحمل الآمنة السائدة في تقارير أبحاث التربة للأراضي الصناعية لضمان عدم حدوث قص أو هبوط زائد تحت الأحمال الكلية.</span>
                        </li>
                        <li>
                            <b style="color: #38bdf8; font-size: 24px;">سمك طبقة الإحلال / الأساس الحصوي h_base (القيمة الافتراضية = 20.0 cm):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">الوظيفة الإنشائية:</b> <span style="font-size: 18px; color: #ffffff;">طبقة سن متدرجة مدموكة جيداً لتسوية الموقع، وقطع صعود الرطوبة والمياه الجوفية، ورفع قيمة ks الفعالة وتوزيع الإجهادات المركزة.</span>
                        </li>
                    </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("📐 2. أبعاد البلاطة والمواد الإنشائية (Geometry & Materials) — [اضغط للتفاصيل]", expanded=False):
                st.markdown(
                    """
                    <div dir="rtl" style="text-align: right; font-size: 18px; line-height: 2.1; color: #ffffff; padding: 8px 12px;">
                    <ul style="padding-right: 22px; list-style-type: square;">
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">أبعاد الصالة Lx × Ly (القيمة الافتراضية = 30 × 20 م):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">الهدف التخطيطي:</b> <span style="font-size: 18px; color: #ffffff;">المساحة النمطية للجمالونات والمستودعات المتوسطة (600 م²)، وتستخدم لتقسيم الباكيات وحساب كميات الخرسانة والحديد.</span>
                        </li>
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">سمك البلاطة الخرسانية ts (القيمة الافتراضية = 20.0 cm):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">الكفاءة الإنشائية:</b> <span style="font-size: 18px; color: #ffffff;">السمك القياسي للأرضيات الصناعية (15 – 25 سم). يوفر عزم عطالة ممتاز (ts³ في معادلة ويسترجارد) لمنع الشروخ وضمان أمان القص الثاقب.</span>
                        </li>
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">الغطاء الخرساني الصافي Cover (القيمة الافتراضية = 4.0 cm):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">اشتراطات الكود المصري ECP 203:</b> <span style="font-size: 18px; color: #ffffff;">العناصر الملامسة للتربة وعوازل الرطوبة تتطلب غطاءً صافياً لا يقل عن 4.0 سم لحماية التسليح من التآكل والأملاح الأرضية.</span>
                        </li>
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">رتبة الخرسانة fcu (القيمة الافتراضية = 300 kg/cm² = 30 MPa):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">مقاومة البري والشد:</b> <span style="font-size: 18px; color: #ffffff;">الموصى به للأرضيات الصناعية (300 – 350 كجم/سم²) لضمان مقاومة عالية للبري والاحتكاك السطحي (Abrasion) وتحقيق إجهاد شد انحناء عالي fctr = 0.6√fcu.</span>
                        </li>
                        <li>
                            <b style="color: #38bdf8; font-size: 24px;">إجهاد خضوع الحديد fy (القيمة الافتراضية = 4200 kg/cm²):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">نوعية الصلب:</b> <span style="font-size: 18px; color: #ffffff;">الرتبة القياسية عالية المقاومة (St 420/500) لتحمل قوى الشد الناتجة عن سحب التربة أثناء الانكماش بأعلى كفاءة اقتصادية.</span>
                        </li>
                    </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("🚛 3. الأحمال التشغيلية وحمولات المعدات (Design Loads) — [اضغط للتفاصيل]", expanded=False):
                st.markdown(
                    """
                    <div dir="rtl" style="text-align: right; font-size: 18px; line-height: 2.1; color: #ffffff; padding: 8px 12px;">
                    <ul style="padding-right: 22px; list-style-type: square;">
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">الحمل الحي الموزع بانتظام w_LL (القيمة الافتراضية = 2.5 ton/m²):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">نطاق التغطية:</b> <span style="font-size: 18px; color: #ffffff;">يغطي حمولات التخزين العام، الممرات، وتوزيع البضائع في المصانع والمستودعات المتوسطة.</span>
                        </li>
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">حمولة عجلة الرافعة الشوكية P_wheel (القيمة الافتراضية = 4.0 ton):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">تحليل أوزان المعدات:</b> <span style="font-size: 18px; color: #ffffff;">الرافعة الشوكية القياسية (حمولة 2.5 – 3.0 طن) تنقل حوالي 80% إلى 85% من وزنها الإجمالي مع الحمولة إلى المحور الأمامي، فيكون نصيب العجلة الواحدة 3.5 – 4.5 طن كحمل نقطي ديناميكي.</span>
                        </li>
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">بصمة تلامس إطار العجلة bw × lw (القيمة الافتراضية = 20 × 25 cm):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">المساحة التلامسية:</b> <span style="font-size: 18px; color: #ffffff;">المساحة الواقعية لبصمة الإطار المطاطي (500 سم²) وتستخدم لحساب نصف القطر المكافئ a في معادلات ويسترجارد.</span>
                        </li>
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">حمولة رجل أرفف التخزين P_post (القيمة الافتراضية = 3.5 ton):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">التركيز النقطي والقص:</b> <span style="font-size: 18px; color: #ffffff;">الحمل النقطي المركز النازل من أرجل أرفف التخزين المرتفعة (Pallet Racking بارتفاع 4 – 6 م)، وهو المسبب الرئيسي للقص الثاقب (Punching).</span>
                        </li>
                        <li>
                            <b style="color: #38bdf8; font-size: 24px;">أبعاد لوح التثبيت bp × tp (القيمة الافتراضية = 15 × 15 cm):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">تفصيلة القاعدة:</b> <span style="font-size: 18px; color: #ffffff;">أبعاد اللوح الفولاذي السفلي (Base Plate) لرجل الرف المثبت بمسامير في الخرسانة.</span>
                        </li>
                    </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("🔗 4. فواصل الانكماش والدواول والتسليح (Joints & Reinforcement) — [اضغط للتفاصيل]", expanded=False):
                st.markdown(
                    """
                    <div dir="rtl" style="text-align: right; font-size: 18px; line-height: 2.1; color: #ffffff; padding: 8px 12px;">
                    <ul style="padding-right: 22px; list-style-type: square;">
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">مسافات الفواصل Ljx × Ljy (القيمة الافتراضية = 4.5 × 4.5 م):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">القاعدة الكودية الذهبية:</b> <span style="font-size: 18px; color: #ffffff;">المسافة بين الفواصل لا تزيد عن 24 إلى 30 ضعف السمك (24 × 0.20 = 4.80 م). اختيار 4.5 م يضمن منع الشروخ العشوائية مع نسبة طول لعرض ≤ 1.25.</span>
                        </li>
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">عمق قطع الفاصل بالمنشار (Saw-Cut Depth = ts / 4 = 5.0 cm):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">آلية العمل:</b> <span style="font-size: 18px; color: #ffffff;">لعمل مستوى ضعف متعمد (Weakened Plane) يشرخ تحته خط مستقيم ذاتياً مع بقاء التعشيق الركامي في الأسفل.</span>
                        </li>
                        <li style="margin-bottom: 18px;">
                            <b style="color: #38bdf8; font-size: 24px;">شبك التسليح (Double Mesh Φ 10 mm @ 20 cm):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">مقاومة الانكماش:</b> <span style="font-size: 18px; color: #ffffff;">يعطي مساحة مقطع As = 3.93 سم²/م' يفوق الحد الأدنى للكود المصري (0.15% b ts) ويقاوم قوى سحب التربة (Subgrade Drag).</span>
                        </li>
                        <li>
                            <b style="color: #38bdf8; font-size: 24px;">أسياخ الدواول (Smooth Dowels Φ 20 mm @ 30 cm c/c, L = 45 cm):</b>
                            <br>• <b style="color: #fbbf24; font-size: 22px;">نقل القص الرأسي:</b> <span style="font-size: 18px; color: #ffffff;">أسياخ ملساء تنقل القص رأسياً وتمنع فرق الهبوط (Faulting) مع السماح بالحركة الأفقية بفضل جراب التمدد البلاستيكي أو دهان الشحم.</span>
                        </li>
                    </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════════════
        # 📐 DESIGN INPUTS SECTION (SEPARATE BELOW HELP)
        # ══════════════════════════════════════════════════════════════════════
        st.markdown("### 📝 حقول إدخال بيانات المشروع والأبعاد والتربة والأحمال")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📐 أبعاد البلاطة والمواد (Geometry & Materials)")
            Lx_in = S.number_input("طول الصالة / البلاطة Lx (m):", "gs_lx", min_value=3.0, max_value=200.0, step=1.0)
            Ly_in = S.number_input("عرض الصالة / البلاطة Ly (m):", "gs_ly", min_value=3.0, max_value=200.0, step=1.0)
            ts_in = S.number_input("سمك البلاطة الخرسانية ts (cm):", "gs_ts", min_value=10.0, max_value=60.0, step=1.0)
            cover_in = S.number_input("الغطاء الخرساني الصافي Cover (cm):", "gs_cover", min_value=2.0, max_value=10.0, step=0.5)
            fcu_in = S.number_input("إجهاد كسر الخرسانة fcu (kg/cm²):", "gs_fcu", min_value=200.0, max_value=600.0, step=25.0)
            fy_in = S.number_input("إجهاد خضوع حديد التسليح fy (kg/cm²):", "gs_fy", min_value=2400.0, max_value=6000.0, step=200.0)

        with c2:
            st.markdown("#### 🌍 خواص التربة وطبقة الإحلال (Subgrade & Base)")
            ks_in = S.number_input("معامل رد فعل التربة ks (kg/cm³):", "gs_ks", min_value=1.0, max_value=25.0, step=0.5, help="Modulus of Subgrade Reaction (3-5 لتربة طينية/رملية متوسطة، 6-10 لطبقة إحلال مدموكة)")
            q_all_in = S.number_input("إجهاد التأسيس المسموح للتربة q_all (kg/cm²):", "gs_q_all", min_value=0.5, max_value=5.0, step=0.1)
            h_base_in = S.number_input("سمك طبقة الإحلال / الدبش المدموك (cm):", "gs_h_base", min_value=0.0, max_value=60.0, step=5.0)

            st.markdown("#### 🚛 الأحمال التشغيلية (Design Loads)")
            w_ll_in = S.number_input("الحمل الحي الموزع بانتظام (ton/m²):", "gs_w_ll", min_value=0.5, max_value=20.0, step=0.5)
            p_wheel_in = S.number_input("حمولة عجلة الرافعة الشوكية (ton):", "gs_p_wheel", min_value=0.5, max_value=20.0, step=0.5)
            col_wh1, col_wh2 = st.columns(2)
            with col_wh1:
                wh_b_in = S.number_input("عرض تلامس العجلة (cm):", "gs_wheel_b", min_value=5.0, max_value=50.0, step=1.0)
            with col_wh2:
                wh_l_in = S.number_input("طول تلامس العجلة (cm):", "gs_wheel_l", min_value=5.0, max_value=50.0, step=1.0)

            p_post_in = S.number_input("حمولة رجل أرفف التخزين (ton):", "gs_p_post", min_value=0.5, max_value=25.0, step=0.5)
            col_ps1, col_ps2 = st.columns(2)
            with col_ps1:
                post_bp_in = S.number_input("عرض بليت الركيزة (cm):", "gs_post_bp", min_value=5.0, max_value=50.0, step=1.0)
            with col_ps2:
                post_tp_in = S.number_input("طول بليت الركيزة (cm):", "gs_post_tp", min_value=5.0, max_value=50.0, step=1.0)

    with tab3:
        cj1, cj2 = st.columns(2)
        with cj1:
            st.markdown("#### 🔗 فواصل الانكماش والتحكم (Contraction Joints)")
            joint_sx_in = S.number_input("المسافة بين الفواصل في اتجاه X (m):", "gs_joint_spacing_x", min_value=2.0, max_value=10.0, step=0.25)
            joint_sy_in = S.number_input("المسافة بين الفواصل في اتجاه Y (m):", "gs_joint_spacing_y", min_value=2.0, max_value=10.0, step=0.25)

            st.markdown("#### 🔩 أسياخ الدواول الناقلة للقص (Smooth Dowel Bars)")
            dowel_phi_in = S.selectbox("قطر سيخ الدواول (mm):", "gs_dowel_phi", [16, 20, 22, 25, 28, 32])
            dowel_len_in = S.number_input("طول سيخ الدواول (cm):", "gs_dowel_len", min_value=30.0, max_value=80.0, step=5.0)
            dowel_sp_in = S.number_input("المسافة بين أسياخ الدواول (cm c/c):", "gs_dowel_spacing", min_value=15.0, max_value=50.0, step=5.0)

        with cj2:
            st.markdown("#### 🕸️ شبكات حديد التسليح (Reinforcement Mesh)")
            mesh_type_in = S.selectbox(
                "نوع التسليح المقترح:",
                "gs_rebar_mesh_type",
                ["شبكة علوية وسفلية (Double Mesh)", "شبكة واحدة بموضع علوي (Single Top Mesh)", "شبكة واحدة بموضع سفلي (Single Bottom Mesh)"],
            )
            phi_mesh_in = S.selectbox("قطر أسياخ شبك التسليح (mm):", "gs_phi_mesh", [8, 10, 12, 14, 16])
            mesh_spacing_in = S.number_input("المسافة بين الأسياخ (cm c/c):", "gs_mesh_spacing", min_value=10.0, max_value=30.0, step=2.5)

    res = compute_ground_slab_design(
        Lx_m=float(Lx_in),
        Ly_m=float(Ly_in),
        ts_cm=float(ts_in),
        cover_cm=float(cover_in),
        fcu_kg_cm2=float(fcu_in),
        fy_kg_cm2=float(fy_in),
        ks_kg_cm3=float(ks_in),
        q_all_kg_cm2=float(q_all_in),
        h_base_cm=float(h_base_in),
        w_ll_ton_m2=float(w_ll_in),
        p_wheel_ton=float(p_wheel_in),
        wheel_b_cm=float(wh_b_in),
        wheel_l_cm=float(wh_l_in),
        p_post_ton=float(p_post_in),
        post_bp_cm=float(post_bp_in),
        post_tp_cm=float(post_tp_in),
        mesh_type=mesh_type_in,
        phi_mesh_mm=int(phi_mesh_in),
        spacing_mesh_cm=float(mesh_spacing_in),
        joint_spacing_x_m=float(joint_sx_in),
        joint_spacing_y_m=float(joint_sy_in),
        dowel_phi_mm=int(dowel_phi_in),
        dowel_len_cm=float(dowel_len_in),
        dowel_spacing_cm=float(dowel_sp_in),
    )

    with tab2:
        st.markdown("### 📊 نتائج الفحوصات الإنشائية والجيوتقنية (Structural & Soil Verification)")

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            bg_k1 = "#064e3b" if res["is_flexure_safe"] else "#7f1d1d"
            bd_k1 = "#22c55e" if res["is_flexure_safe"] else "#ef4444"
            st.markdown(
                f"""<div style="background:{bg_k1}; border:2px solid {bd_k1}; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:18px; color:#cbd5e1; font-weight:800;">فحص إجهادات الانحناء (Flexure)</div>
                    <div style="font-size:30px; font-weight:900; color:#ffffff; margin:6px 0;">{'✅ SAFE' if res['is_flexure_safe'] else '⚠️ UNSAFE'}</div>
                    <div style="font-size:17px; color:#f1f5f9; font-weight:700;">{res['sigma_act_flexure']:.2f} / {res['sigma_all_flexure']:.2f} kg/cm² ({res['ratio_flexure']*100:.1f}%)</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with k2:
            bg_k2 = "#064e3b" if res["is_punching_safe"] else "#7f1d1d"
            bd_k2 = "#22c55e" if res["is_punching_safe"] else "#ef4444"
            st.markdown(
                f"""<div style="background:{bg_k2}; border:2px solid {bd_k2}; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:18px; color:#cbd5e1; font-weight:800;">فحص القص الثاقب (Punching)</div>
                    <div style="font-size:30px; font-weight:900; color:#ffffff; margin:6px 0;">{'✅ SAFE' if res['is_punching_safe'] else '⚠️ UNSAFE'}</div>
                    <div style="font-size:17px; color:#f1f5f9; font-weight:700;">{res['qup_post_kg_cm2']:.2f} / {res['qcu_punching_kg_cm2']:.2f} kg/cm² ({res['ratio_punching']*100:.1f}%)</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with k3:
            bg_k3 = "#064e3b" if res["is_soil_safe"] else "#7f1d1d"
            bd_k3 = "#22c55e" if res["is_soil_safe"] else "#ef4444"
            st.markdown(
                f"""<div style="background:{bg_k3}; border:2px solid {bd_k3}; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:18px; color:#cbd5e1; font-weight:800;">إجهاد التربة (Soil Pressure)</div>
                    <div style="font-size:30px; font-weight:900; color:#ffffff; margin:6px 0;">{'✅ SAFE' if res['is_soil_safe'] else '⚠️ UNSAFE'}</div>
                    <div style="font-size:17px; color:#f1f5f9; font-weight:700;">{res['q_total_act_kg_cm2']:.2f} / {res['q_all_kg_cm2']:.2f} kg/cm² ({res['ratio_soil']*100:.1f}%)</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with k4:
            bg_k4 = "#064e3b" if res["is_rebar_safe"] else "#7f1d1d"
            bd_k4 = "#22c55e" if res["is_rebar_safe"] else "#ef4444"
            st.markdown(
                f"""<div style="background:{bg_k4}; border:2px solid {bd_k4}; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:18px; color:#cbd5e1; font-weight:800;">حديد الانكماش (Rebar Mesh)</div>
                    <div style="font-size:30px; font-weight:900; color:#ffffff; margin:6px 0;">{'✅ SAFE' if res['is_rebar_safe'] else '⚠️ UNSAFE'}</div>
                    <div style="font-size:17px; color:#f1f5f9; font-weight:700;">{res['As_provided_cm2_m']:.2f} / {res['As_required_cm2_m']:.2f} cm²/m'</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

        checks_rows = [
            (
                "1. إجهاد الانحناء تحت أقصى حمل مركز (Westergaard Stress)",
                f"{res['sigma_act_flexure']:.2f} kg/cm²",
                f"{res['sigma_all_flexure']:.2f} kg/cm² (fctr/1.7)",
                f"{res['ratio_flexure']*100:.1f}%",
                res['is_flexure_safe'],
                "آمن ومطابق" if res['is_flexure_safe'] else "غير آمن (زيادة السمك ts مطلوبة)",
            ),
            (
                "2. إجهاد القص الثاقب تحت أقدام الأرفف (Punching Shear)",
                f"{res['qup_post_kg_cm2']:.2f} kg/cm²",
                f"{res['qcu_punching_kg_cm2']:.2f} kg/cm²",
                f"{res['ratio_punching']*100:.1f}%",
                res['is_punching_safe'],
                "آمن ومطابق" if res['is_punching_safe'] else "غير آمن (تكبير لوح التثبيت أو زيادة ts)",
            ),
            (
                "3. ضغط التربة الإجمالي المباشر (Subgrade Contact Pressure)",
                f"{res['q_total_act_kg_cm2']:.2f} kg/cm²",
                f"{res['q_all_kg_cm2']:.2f} kg/cm²",
                f"{res['ratio_soil']*100:.1f}%",
                res['is_soil_safe'],
                "آمن ومطابق" if res['is_soil_safe'] else "تجاوز قدرة تحمل التربة",
            ),
            (
                "4. هبوط التربة المرن (Subgrade Deflection under LL)",
                f"{res['delta_subgrade_mm']:.2f} mm",
                f"{res['delta_all_mm']:.2f} mm",
                f"{(res['delta_subgrade_mm']/res['delta_all_mm'])*100:.1f}%",
                res['is_deflection_safe'],
                "آمن ومطابق" if res['is_deflection_safe'] else "هبوط زائد (زيادة دمك الإحلال)",
            ),
            (
                "5. مساحة حديد تسليح الانكماش (Shrinkage Mesh Area)",
                f"{res['As_provided_cm2_m']:.2f} cm²/m'",
                f"Min {res['As_required_cm2_m']:.2f} cm²/m'",
                f"{(res['As_required_cm2_m']/res['As_provided_cm2_m'])*100:.1f}%",
                res['is_rebar_safe'],
                "آمن ومطابق" if res['is_rebar_safe'] else "مطلوب تقليل مسافات الشبك أو زيادة القطر",
            ),
            (
                "6. المسافة بين فواصل الانكماش (Joint Spacing Ratio)",
                f"L_bay = {max(res['actual_bay_lx'], res['actual_bay_ly']):.2f} m",
                f"Max {res['max_rec_joint_spacing_m']:.2f} m (25 ts)",
                f"{(max(res['actual_bay_lx'], res['actual_bay_ly'])/res['max_rec_joint_spacing_m'])*100:.1f}%",
                (max(res['actual_bay_lx'], res['actual_bay_ly']) <= res['max_rec_joint_spacing_m']),
                "آمن ومطابق" if (max(res['actual_bay_lx'], res['actual_bay_ly']) <= res['max_rec_joint_spacing_m']) else "تباعد زائد (مطلوب تقريب الفواصل)",
            ),
        ]

        table_checks_body = []
        for idx, (item, actual, allowable, ratio, is_safe, comment) in enumerate(checks_rows):
            bg_row = "rgba(15, 23, 42, 0.75)" if idx % 2 == 0 else "rgba(30, 41, 59, 0.75)"
            status_badge = (
                f'<span style="background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 2px solid #22c55e; padding: 6px 16px; border-radius: 10px; font-size: 22px; font-weight: 900; display: inline-block;">✅ {comment}</span>'
                if is_safe else
                f'<span style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 2px solid #ef4444; padding: 6px 16px; border-radius: 10px; font-size: 22px; font-weight: 900; display: inline-block;">⚠️ {comment}</span>'
            )
            table_checks_body.append(
                f'<tr style="background: {bg_row}; border-bottom: 1.5px solid rgba(148, 163, 184, 0.25);">'
                f'<td style="padding: 16px 18px; font-size: 22px; font-weight: 800; color: #ffffff; text-align: right;">{item}</td>'
                f'<td style="padding: 16px 18px; font-size: 24px; font-weight: 900; color: #38bdf8; text-align: center;" dir="ltr">{actual}</td>'
                f'<td style="padding: 16px 18px; font-size: 22px; font-weight: 800; color: #fbbf24; text-align: center;" dir="ltr">{allowable}</td>'
                f'<td style="padding: 16px 18px; font-size: 24px; font-weight: 900; color: #f1f5f9; text-align: center;" dir="ltr">{ratio}</td>'
                f'<td style="padding: 16px 18px; text-align: center;">{status_badge}</td>'
                f'</tr>'
            )

        checks_html_table = (
            '<div style="overflow-x: auto; border: 2px solid rgba(56, 189, 248, 0.45); border-radius: 12px; box-shadow: 0 6px 25px rgba(0,0,0,0.5); margin: 12px 0 24px 0;">'
            '<table style="width: 100%; border-collapse: collapse; background: #0b1329; font-family: inherit;">'
            '<thead>'
            '<tr style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom: 2.5px solid #38bdf8;">'
            '<th style="padding: 18px 20px; font-size: 24px; font-weight: 900; color: #38bdf8; text-align: right;">بند التحقق الهندسي (Verification Item)</th>'
            '<th style="padding: 18px 20px; font-size: 24px; font-weight: 900; color: #38bdf8; text-align: center;">القيمة المحسوبة (Actual)</th>'
            '<th style="padding: 18px 20px; font-size: 24px; font-weight: 900; color: #fbbf24; text-align: center;">القيمة المسموحة (Allowable)</th>'
            '<th style="padding: 18px 20px; font-size: 24px; font-weight: 900; color: #38bdf8; text-align: center;">نسبة الاستخدام (Ratio)</th>'
            '<th style="padding: 18px 20px; font-size: 24px; font-weight: 900; color: #4ade80; text-align: center;">الحالة والنتيجة (Status)</th>'
            '</tr>'
            '</thead>'
            '<tbody>'
            + "".join(table_checks_body) +
            '</tbody>'
            '</table>'
            '</div>'
        )
        st.markdown(checks_html_table, unsafe_allow_html=True)

    with tab4:
        st.markdown("### 📐 المخططات الهندسية وجدول حصر الكميات (CAD Drawings & BOQ)")

        b64_plan, b64_detail = generate_ground_slab_plan_and_detail_sketches(res)

        st.markdown("#### 1. المسقط الأفقي العام للبلاطة والفواصل وتمركز الأحمال (2D Floor Plan)")
        st.image(f"data:image/png;base64,{b64_plan}", use_container_width=True)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "📥 تحميل المسقط الأفقي (Download 2D Plan PNG)",
                data=base64.b64decode(b64_plan),
                file_name=f"Ground_Slab_2D_Plan_{res['Lx_m']:.0f}x{res['Ly_m']:.0f}m_ts{res['ts_cm']:.0f}cm.png",
                mime="image/png",
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("#### 2. قطاع تفصيلي في فاصل الانكماش والدواول (Contraction Joint & Dowel Detail)")
        st.image(f"data:image/png;base64,{b64_detail}", use_container_width=True)

        with col_d2:
            st.download_button(
                "📥 تحميل تفصيلة الفاصل (Download Joint Detail PNG)",
                data=base64.b64decode(b64_detail),
                file_name=f"Ground_Slab_Joint_Detail_ts{res['ts_cm']:.0f}cm.png",
                mime="image/png",
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("### 📋 جدول حصر الكميات والمقايسة المادية (Takeoff & BOQ Breakdown)")

        boq_data_list = [
            ("1", "خرسانة مسلحة للبلاطة الأرضية", f"fcu={res['fcu_kg_cm2']:.0f} kg/cm² (ts={res['ts_cm']:.0f} cm)", f"{res['concrete_vol_m3']:.2f}", "متر مكعب m³"),
            ("2", "حديد تسليح شبكات الانكماش", f"{res['mesh_type']} (Φ{res['phi_mesh_mm']} @ {res['spacing_mesh_cm']:.0f} cm)", f"{res['total_mesh_weight_ton']:.3f}", "طن Ton"),
            ("3", "أسياخ دواول نقل القص الملساء", f"Φ{res['dowel_phi_mm']} mm (L={res['dowel_len_cm']:.0f} cm @ {res['dowel_spacing_cm']:.0f} cm)", f"{res['total_dowel_weight_ton']:.3f} ({res['total_dowels_count']} سيخ)", "طن Ton"),
            ("4", "إجمالي حديد التسليح والدواول", f"معدل التسليح = {res['steel_rate_kg_m3']:.1f} kg/m³", f"{res['total_steel_weight_ton']:.3f}", "طن Ton"),
            ("5", "قطع فواصل الانكماش بالمنشار", f"عمق القطع = {res['saw_cut_depth_cm']:.1f} cm", f"{res['total_joint_length_m']:.1f}", "متر طولي m'"),
            ("6", "مادة ملء وحقن الفواصل المرنة", "Polyurethane Elastomeric Sealant", f"{res['total_joint_length_m']:.1f}", "متر طولي m'"),
            ("7", "عازل رطوبة بولي إيثيلين (PE)", "Heavy-duty 500 Micron Polyethylene Sheet", f"{res['vapor_barrier_m2']:.1f}", "متر مربع m²"),
            ("8", "طبقة إحلال من الحصى المتدرج المدموك", f"سمك الطبقة = {h_base_in:.0f} cm (Compaction >= 98% Proctor)", f"{res['subbase_vol_m3']:.2f}", "متر مكعب m³"),
        ]

        table_boq_body = []
        for idx_b, (num, item_b, spec_b, qty_b, unit_b) in enumerate(boq_data_list):
            bg_row_b = "rgba(15, 23, 42, 0.75)" if idx_b % 2 == 0 else "rgba(30, 41, 59, 0.75)"
            table_boq_body.append(
                f'<tr style="background: {bg_row_b}; border-bottom: 1.5px solid rgba(148, 163, 184, 0.25);">'
                f'<td style="padding: 16px 14px; font-size: 23px; font-weight: 900; color: #fbbf24; text-align: center;">{num}</td>'
                f'<td style="padding: 16px 18px; font-size: 23px; font-weight: 800; color: #ffffff; text-align: right;">{item_b}</td>'
                f'<td style="padding: 16px 18px; font-size: 21px; font-weight: 700; color: #cbd5e1; text-align: center;" dir="ltr">{spec_b}</td>'
                f'<td style="padding: 16px 18px; font-size: 25px; font-weight: 900; color: #38bdf8; text-align: center;" dir="ltr">{qty_b}</td>'
                f'<td style="padding: 16px 18px; font-size: 22px; font-weight: 800; color: #a5f3fc; text-align: center;">{unit_b}</td>'
                f'</tr>'
            )

        boq_html_table = (
            '<div style="overflow-x: auto; border: 2px solid rgba(56, 189, 248, 0.45); border-radius: 12px; box-shadow: 0 6px 25px rgba(0,0,0,0.5); margin: 12px 0 24px 0;">'
            '<table style="width: 100%; border-collapse: collapse; background: #0b1329; font-family: inherit;">'
            '<thead>'
            '<tr style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom: 2.5px solid #38bdf8;">'
            '<th style="padding: 18px 14px; font-size: 24px; font-weight: 900; color: #fbbf24; text-align: center; width: 60px;">م</th>'
            '<th style="padding: 18px 20px; font-size: 24px; font-weight: 900; color: #38bdf8; text-align: right;">بند الأعمال (Item)</th>'
            '<th style="padding: 18px 20px; font-size: 24px; font-weight: 900; color: #38bdf8; text-align: center;">المواصفة الفنية (Specifications)</th>'
            '<th style="padding: 18px 20px; font-size: 24px; font-weight: 900; color: #38bdf8; text-align: center;">الكمية (Qty)</th>'
            '<th style="padding: 18px 20px; font-size: 24px; font-weight: 900; color: #38bdf8; text-align: center;">الوحدة (Unit)</th>'
            '</tr>'
            '</thead>'
            '<tbody>'
            + "".join(table_boq_body) +
            '</tbody>'
            '</table>'
            '</div>'
        )
        st.markdown(boq_html_table, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📄 حفظ وتصدير المذكرة الحسابية الكاملة (Save & Export Calculation Sheet)")

        from modules.report_generator import generate_ground_slab_report_html, html_to_pdf_bytes

        active_proj = S.get_active_profile_name() if hasattr(S, "get_active_profile_name") else "Ground Slab Design"
        prefix = S.get_safe_profile_filename_prefix()

        img_plan_url = f"data:image/png;base64,{b64_plan}"
        img_detail_url = f"data:image/png;base64,{b64_detail}"

        sog_html = generate_ground_slab_report_html(
            res=res,
            project_name=active_proj,
            img_plan_b64=img_plan_url,
            img_detail_b64=img_detail_url,
        )
        pdf_bytes = html_to_pdf_bytes(sog_html)

        cs1, cs2 = st.columns([3, 1])
        with cs1:
            st.markdown(
                f"""<div style='background:rgba(30, 41, 59, 0.7); border:1.5px solid #38bdf8; border-radius:10px; padding:12px 16px;'>
                    <div style='font-weight:800; color:#38bdf8; font-size:16px;'>
                        📋 مذكرة الحسابات الإنشائية والجيوتقنية للبلاطة الأرضية
                    </div>
                    <div style='font-size:13px; color:#cbd5e1; margin-top:3px;'>
                        تتضمن كامل المدخلات، وفحوصات ويسترجارد للانحناء، والقص الثاقب، وإجهاد التربة، وتفاصيل الفواصل والدواول، وحصر الكميات.
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
        with cs2:
            st.download_button(
                "🌐 Save Calculation Sheet (HTML)",
                data=sog_html,
                file_name=f"{prefix}Ground_Slab_Report_{res['Lx_m']:.0f}x{res['Ly_m']:.0f}m_ts{res['ts_cm']:.0f}cm.html",
                mime="text/html",
                use_container_width=True,
            )
            if pdf_bytes:
                st.download_button(
                    "📕 Save as PDF (مباشر)",
                    data=pdf_bytes,
                    file_name=f"{prefix}Ground_Slab_Report_{res['Lx_m']:.0f}x{res['Ly_m']:.0f}m_ts{res['ts_cm']:.0f}cm.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

