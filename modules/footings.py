"""
Module 2 - Isolated Footing Design (ECP 203)
Units: ton, kg, cm, kg/cm²
Supports rectangular footing plan: Length L (long side) × Width B (short side)
"""
import math
import io
import base64
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Polygon
from modules import settings as S


def round_up_to_5(v):
    return int(math.ceil(v / 5.0) * 5)

def round_up_to_10(v):
    return int(math.ceil(v / 10.0) * 10)


def initial_LB(A_req, tc, bc):
    """
    Solve for L and B according to ECP 203 such that:
      1. Overhang in Long direction (c_L) == Overhang in Short direction (c_B):
         c_L = (L - tc)/2 == c_B = (B - bc)/2
      2. Footing Area L × B >= A_req = P_total / q_all
      3. Safety & Proportionality:
         L = B + (tc - bc)  →  Δ = tc - bc
         B² + Δ·B - A_req = 0  →  B_raw = (-Δ + √(Δ² + 4·A_req)) / 2
         L_raw = B_raw + Δ
         Both rounded up to the nearest 5 cm to guarantee equal overhangs.
    """
    delta = tc - bc
    discriminant = delta ** 2 + 4.0 * A_req
    B_raw = (-delta + math.sqrt(discriminant)) / 2.0
    L_raw = B_raw + delta

    return round_up_to_5(L_raw), round_up_to_5(B_raw)



def generate_footing_plan_sketch(
    L_cm=260,
    B_cm=210,
    t_rc_cm=60,
    bc_cm=30,
    tc_cm=80,
    Phi=16,
    n_long=16,
    n_m_long=8,
    sp_long=13.3,
    n_sht=18,
    n_m_sht=7,
    sp_sht=14.7,
    cover_cm=5,
    t_pc_cm=10,
    pc_offset_cm=10,
):
    """
    Renders a standalone Plan View (المسقط الأفقي) sketch for Isolated Footing (ECP 203)
    with maximized font sizes, clear dimension chains, rebar callouts, and axes.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    fig, ax = plt.subplots(figsize=(19, 14.5), dpi=150, facecolor="#ffffff")
    ax.set_facecolor("#ffffff")

    # Dimensions in meters for plotting
    L_m = L_cm / 100.0
    B_m = B_cm / 100.0
    tc_m = tc_cm / 100.0
    bc_m = bc_cm / 100.0
    pc_off_m = pc_offset_cm / 100.0

    L_pc_m = L_m + 2 * pc_off_m
    B_pc_m = B_m + 2 * pc_off_m

    cL_m = (L_m - tc_m) / 2.0
    cB_m = (B_m - bc_m) / 2.0
    cov_m = cover_cm / 100.0

    # 1. Plain Concrete (P.C.) Base
    pc_rect = patches.Rectangle(
        (-L_pc_m / 2.0, -B_pc_m / 2.0), L_pc_m, B_pc_m,
        linewidth=2.8, edgecolor="#64748b", facecolor="#f8fafc", linestyle="--", zorder=1
    )
    ax.add_patch(pc_rect)

    # 2. Reinforced Concrete (R.C.) Footing
    rc_rect = patches.Rectangle(
        (-L_m / 2.0, -B_m / 2.0), L_m, B_m,
        linewidth=4.2, edgecolor="#0f172a", facecolor="#e0f2fe", alpha=0.92, zorder=2
    )
    ax.add_patch(rc_rect)

    # 3. Column Rectangle
    col_rect = patches.Rectangle(
        (-tc_m / 2.0, -bc_m / 2.0), tc_m, bc_m,
        linewidth=3.2, edgecolor="#0f172a", facecolor="#1e293b", hatch="//", zorder=5
    )
    ax.add_patch(col_rect)
    ax.text(
        0, 0, f"COLUMN\n{tc_cm} × {bc_cm} cm",
        ha="center", va="center", color="#facc15", fontsize=15.5, weight="bold", zorder=6
    )

    # 4. Center Grid Axes (X and Y)
    axis_ext_x = L_pc_m / 2.0 + 0.35
    axis_ext_y = B_pc_m / 2.0 + 0.58
    ax.plot([-axis_ext_x - 0.15, axis_ext_x], [0, 0], color="#dc2626", linestyle="-.", linewidth=1.8, alpha=0.75, zorder=2)
    ax.plot([0, 0], [-axis_ext_y, axis_ext_y + 0.10], color="#dc2626", linestyle="-.", linewidth=1.8, alpha=0.75, zorder=2)
    ax.text(-axis_ext_x - 0.18, 0, "CL", color="#dc2626", fontsize=16, weight="bold", va="center", ha="right", zorder=10)
    ax.text(0, axis_ext_y + 0.12, "CL", color="#dc2626", fontsize=16, weight="bold", ha="center", va="bottom", zorder=10)

    # 5. Section Cut Line A - A
    sec_cut_y = -B_m / 2.0 - 0.12
    ax.plot([-L_pc_m * 0.58, L_pc_m * 0.58], [sec_cut_y, sec_cut_y], color="#b91c1c", linestyle="--", linewidth=2.6, zorder=7)
    ax.annotate("A", xy=(-L_pc_m * 0.54, sec_cut_y), xytext=(-L_pc_m * 0.54, sec_cut_y + 0.25),
                arrowprops=dict(facecolor="#b91c1c", edgecolor="#b91c1c", width=3.0, headwidth=11),
                fontsize=18, weight="bold", color="#b91c1c", ha="center", va="bottom", zorder=8)
    ax.annotate("A", xy=(L_pc_m * 0.54, sec_cut_y), xytext=(L_pc_m * 0.54, sec_cut_y + 0.25),
                arrowprops=dict(facecolor="#b91c1c", edgecolor="#b91c1c", width=3.0, headwidth=11),
                fontsize=18, weight="bold", color="#b91c1c", ha="center", va="bottom", zorder=8)

    # 6. Reinforcement Mesh Lines in Plan
    r_x1 = -L_m / 2.0 + cov_m
    r_x2 = L_m / 2.0 - cov_m
    r_y1 = -B_m / 2.0 + cov_m
    r_y2 = B_m / 2.0 - cov_m

    for yl in np.linspace(r_y1 + 0.08, r_y2 - 0.08, 6):
        ax.plot([r_x1, r_x2], [yl, yl], color="#2563eb", linewidth=1.6, linestyle="-", alpha=0.45, zorder=3)

    for xl in np.linspace(r_x1 + 0.08, r_x2 - 0.08, 7):
        ax.plot([xl, xl], [r_y1, r_y2], color="#16a34a", linewidth=1.6, linestyle="-", alpha=0.45, zorder=3)

    # 7. Dimension Lines with MAXIMIZED fonts
    dim_off_b1 = B_pc_m / 2.0 + 0.34
    dim_off_b2 = dim_off_b1 + 0.42
    dim_off_r1 = L_pc_m / 2.0 + 0.45
    dim_off_r2 = dim_off_r1 + 0.48

    # Bottom Dimension 1: Cantilevers & Column tc
    ax.annotate("", xy=(-tc_m/2.0, -dim_off_b1), xytext=(-L_m/2.0, -dim_off_b1),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.2))
    ax.text((-L_m/2.0 - tc_m/2.0)/2.0, -dim_off_b1 - 0.08, f"cL = {cL_m*100:.0f} cm", ha="center", va="top", fontsize=14.0, weight="bold", zorder=10)

    ax.annotate("", xy=(tc_m/2.0, -dim_off_b1), xytext=(-tc_m/2.0, -dim_off_b1),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.2))
    ax.text(0, -dim_off_b1 - 0.08, f"tc = {tc_cm} cm", ha="center", va="top", fontsize=14.5, weight="bold", zorder=10,
            bbox=dict(boxstyle="square,pad=0.20", facecolor="#ffffff", edgecolor="none"))

    ax.annotate("", xy=(L_m/2.0, -dim_off_b1), xytext=(tc_m/2.0, -dim_off_b1),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.2))
    ax.text((L_m/2.0 + tc_m/2.0)/2.0, -dim_off_b1 - 0.08, f"cL = {cL_m*100:.0f} cm", ha="center", va="top", fontsize=14.0, weight="bold", zorder=10)

    # Bottom Dimension 2: Overall RC Footing Length L
    ax.annotate("", xy=(L_m/2.0, -dim_off_b2), xytext=(-L_m/2.0, -dim_off_b2),
                arrowprops=dict(arrowstyle="<->", color="#1e40af", lw=3.0))
    ax.text(0, -dim_off_b2 - 0.10, f"R.C. Footing Length  L = {L_cm} cm  ({L_m:.2f} m)", ha="center", va="top", fontsize=16.5, weight="bold", color="#1e40af", zorder=10,
            bbox=dict(boxstyle="square,pad=0.25", facecolor="#ffffff", edgecolor="none"))

    # Right Dimension 1: Cantilevers & Column bc
    ax.annotate("", xy=(dim_off_r1, bc_m/2.0), xytext=(dim_off_r1, -bc_m/2.0),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.2))
    ax.text(dim_off_r1 + 0.08, 0, f"bc = {bc_cm} cm", ha="left", va="center", fontsize=14.0, weight="bold", zorder=10,
            bbox=dict(boxstyle="square,pad=0.20", facecolor="#ffffff", edgecolor="none"))

    ax.annotate("", xy=(dim_off_r1, B_m/2.0), xytext=(dim_off_r1, bc_m/2.0),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.2))
    ax.text(dim_off_r1 + 0.08, (B_m/2.0 + bc_m/2.0)/2.0, f"cB = {cB_m*100:.0f} cm", ha="left", va="center", fontsize=13.5, weight="bold", zorder=10)

    ax.annotate("", xy=(dim_off_r1, -bc_m/2.0), xytext=(dim_off_r1, -B_m/2.0),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.2))
    ax.text(dim_off_r1 + 0.08, (-B_m/2.0 - bc_m/2.0)/2.0, f"cB = {cB_m*100:.0f} cm", ha="left", va="center", fontsize=13.5, weight="bold", zorder=10)

    # Right Dimension 2: Overall RC Footing Width B
    ax.annotate("", xy=(dim_off_r2, B_m/2.0), xytext=(dim_off_r2, -B_m/2.0),
                arrowprops=dict(arrowstyle="<->", color="#1e40af", lw=3.0))
    ax.text(dim_off_r2 + 0.10, 0, f"R.C. Footing Width\nB = {B_cm} cm  ({B_m:.2f} m)", ha="left", va="center", fontsize=16.5, weight="bold", color="#1e40af", zorder=10,
            bbox=dict(boxstyle="square,pad=0.25", facecolor="#ffffff", edgecolor="none"))

    # Top Dimension: P.C. Dimension
    dim_off_t = B_pc_m / 2.0 + 0.30
    ax.annotate("", xy=(L_pc_m/2.0, dim_off_t), xytext=(-L_pc_m/2.0, dim_off_t),
                arrowprops=dict(arrowstyle="<->", color="#64748b", lw=2.6))
    ax.text(0, dim_off_t + 0.08, f"P.C. Blinding: {L_pc_m*100:.0f} × {B_pc_m*100:.0f} cm   (t_pc = {t_pc_cm} cm)",
            ha="center", va="bottom", fontsize=15.5, weight="bold", color="#334155", zorder=10,
            bbox=dict(boxstyle="square,pad=0.25", facecolor="#ffffff", edgecolor="none"))

    # Reinforcement Callout Badges with MAXIMIZED font
    ax.text(
        0, B_m / 2.0 - 0.24,
        f"↔ Main Long Steel [L-dir] — فرش الاتجاه الطويل:\n{n_long} Φ{Phi}   ({n_m_long} Φ{Phi}/m)  @  {sp_long:.1f} cm",
        ha="center", va="center", fontsize=14.5, weight="bold", color="#1e40af", linespacing=1.3, zorder=10,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#eff6ff", edgecolor="#3b82f6", lw=2.0)
    )
    ax.text(
        0, -B_m / 2.0 + 0.24,
        f"↕ Secondary Short Steel [B-dir] — غطاء الاتجاه القصير:\n{n_sht} Φ{Phi}   ({n_m_sht} Φ{Phi}/m)  @  {sp_sht:.1f} cm",
        ha="center", va="center", fontsize=14.5, weight="bold", color="#15803d", linespacing=1.3, zorder=10,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#f0fdf4", edgecolor="#22c55e", lw=2.0)
    )

    ax.set_title("ISOLATED FOOTING — PLAN VIEW (المسقط الأفقي للقاعدة الخرسانية المسلحة والعادية)",
                 fontsize=19.5, weight="bold", pad=20, color="#0f172a")

    margin_p = max(L_pc_m, B_pc_m) * 0.44
    ax.set_xlim(-L_pc_m/2.0 - margin_p, L_pc_m/2.0 + margin_p + 0.5)
    ax.set_ylim(-B_pc_m/2.0 - margin_p - 0.25, B_pc_m/2.0 + margin_p * 0.65)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    fig.tight_layout()
    return fig


def generate_footing_section_sketch(
    L_cm=260,
    B_cm=210,
    t_rc_cm=60,
    bc_cm=30,
    tc_cm=80,
    Phi=16,
    n_long=16,
    n_m_long=8,
    sp_long=13.3,
    n_sht=18,
    n_m_sht=7,
    sp_sht=14.7,
    cover_cm=5,
    Df_m=1.8,
    t_pc_cm=10,
    pc_offset_cm=10,
):
    """
    Renders a standalone Cross-Section Elevation (القطاع الرأسي وتفاصيل التسليح A-A) sketch
    for Isolated Footing (ECP 203) with maximized font sizes and complete rebar detailing.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    fig, ax = plt.subplots(figsize=(20, 13.5), dpi=150, facecolor="#ffffff")
    ax.set_facecolor("#ffffff")

    # Dimensions in meters for plotting
    L_m = L_cm / 100.0
    B_m = B_cm / 100.0
    tc_m = tc_cm / 100.0
    bc_m = bc_cm / 100.0
    trc_m = t_rc_cm / 100.0
    tpc_m = t_pc_cm / 100.0
    pc_off_m = pc_offset_cm / 100.0

    L_pc_m = L_m + 2 * pc_off_m
    cL_m = (L_m - tc_m) / 2.0
    cov_m = cover_cm / 100.0

    y_base = 0.0
    y_rc_bot = y_base + tpc_m
    y_rc_top = y_rc_bot + trc_m
    col_neck_h = max(1.0, Df_m - trc_m - tpc_m + 0.40)
    y_col_top = y_rc_top + col_neck_h
    y_gl = y_base + Df_m  # Ground Level

    # 1. Soil Hatching / Background
    ax.fill_between(
        [-L_pc_m * 0.72, L_pc_m * 0.72],
        [y_base, y_base], [y_gl, y_gl],
        color="#fef3c7", alpha=0.32, zorder=0
    )

    # Ground Level Line (G.L.)
    ax.plot([-L_pc_m * 0.76, L_pc_m * 0.76], [y_gl, y_gl], color="#78350f", linewidth=3.0, linestyle="-", zorder=2)
    for gx in np.linspace(-L_pc_m * 0.72, L_pc_m * 0.72, 12):
        ax.plot([gx - 0.09, gx, gx + 0.09], [y_gl - 0.06, y_gl, y_gl - 0.06], color="#78350f", lw=1.8, zorder=2)
    ax.text(L_pc_m * 0.74, y_gl + 0.06, f"G.L. ±0.00\n(Df = {Df_m:.2f} m)", color="#78350f", fontsize=15.5, weight="bold", va="bottom", ha="left")

    # 2. Plain Concrete (P.C.) Blinding Layer
    pc_sec = patches.Rectangle(
        (-L_pc_m / 2.0, y_base), L_pc_m, tpc_m,
        linewidth=2.6, edgecolor="#64748b", facecolor="#e2e8f0", hatch="..", zorder=1
    )
    ax.add_patch(pc_sec)
    ax.text(-L_pc_m / 2.0 + 0.15, y_base + tpc_m / 2.0, f"P.C. Blinding ({t_pc_cm} cm)", color="#334155", fontsize=14.0, weight="bold", va="center")

    # 3. Reinforced Concrete (R.C.) Footing Block
    rc_sec = patches.Rectangle(
        (-L_m / 2.0, y_rc_bot), L_m, trc_m,
        linewidth=3.8, edgecolor="#0f172a", facecolor="#e0f2fe", alpha=0.88, zorder=2
    )
    ax.add_patch(rc_sec)

    # 4. Column Neck / Starter
    col_sec = patches.Rectangle(
        (-tc_m / 2.0, y_rc_top), tc_m, col_neck_h,
        linewidth=3.0, edgecolor="#0f172a", facecolor="#f8fafc", zorder=2
    )
    ax.add_patch(col_sec)
    ax.plot([-tc_m/2.0, tc_m/2.0], [y_rc_top, y_rc_top], color="#0f172a", linewidth=2.2, linestyle=":", zorder=3)
    ax.text(0, y_rc_top + col_neck_h * 0.55, f"COLUMN\n{tc_cm} × {bc_cm} cm", ha="center", va="center", fontsize=14.5, weight="bold", color="#1e293b", zorder=6)

    # 5. Reinforcement Detailing in Elevation
    # (a) Main Bottom Long Bars (فرش مع زوايا قائمة U-hooks)
    r_y_main = y_rc_bot + cov_m
    hook_h = trc_m - 2 * cov_m
    r_x_start = -L_m / 2.0 + cov_m
    r_x_end = L_m / 2.0 - cov_m

    hook_pts = [
        [r_x_start, r_y_main + hook_h],
        [r_x_start, r_y_main],
        [r_x_end, r_y_main],
        [r_x_end, r_y_main + hook_h]
    ]
    hook_arr = np.array(hook_pts)
    ax.plot(hook_arr[:, 0], hook_arr[:, 1], color="#1d4ed8", linewidth=4.2, zorder=5)

    # (b) Cross Secondary Bars (غطاء - كرات/دوائر عمودية)
    n_cross_dots = 12
    x_cross_dots = np.linspace(r_x_start + 0.09, r_x_end - 0.09, n_cross_dots)
    y_dot = r_y_main + 0.045
    for xd in x_cross_dots:
        dot = Circle((xd, y_dot), radius=0.020, facecolor="#16a34a", edgecolor="#14532d", lw=1.5, zorder=6)
        ax.add_patch(dot)

    # (c) Column Starter Bars (أشاير العمود مع رجل تثبيت 90 درجة)
    col_rebar_off = 0.05
    col_bar_L = -tc_m / 2.0 + col_rebar_off
    col_bar_R = tc_m / 2.0 - col_rebar_off
    leg_len = min(0.45, cL_m * 0.72)

    # Left Starter Bar
    bar_L_pts = [
        [col_bar_L, y_col_top + 0.20],
        [col_bar_L, r_y_main + 0.08],
        [col_bar_L - leg_len, r_y_main + 0.08]
    ]
    arr_bL = np.array(bar_L_pts)
    ax.plot(arr_bL[:, 0], arr_bL[:, 1], color="#dc2626", linewidth=3.4, zorder=4)

    # Right Starter Bar
    bar_R_pts = [
        [col_bar_R, y_col_top + 0.20],
        [col_bar_R, r_y_main + 0.08],
        [col_bar_R + leg_len, r_y_main + 0.08]
    ]
    arr_bR = np.array(bar_R_pts)
    ax.plot(arr_bR[:, 0], arr_bR[:, 1], color="#dc2626", linewidth=3.4, zorder=4)

    # Column Stirrups / Ties
    for y_tie in np.linspace(y_rc_top + 0.10, y_col_top - 0.10, 5):
        ax.plot([col_bar_L, col_bar_R], [y_tie, y_tie], color="#b91c1c", linewidth=2.4, linestyle="-", zorder=3)

    # 6. MAXIMIZED Elevation Callout Annotations
    # Main Bottom Steel Leader
    ax.annotate(
        f"Main Bottom Steel [L-dir] — فرش الاتجاه الطويل:\n{n_long} Φ{Phi}   ({n_m_long} Φ{Phi}/m)  @  {sp_long:.1f} cm",
        xy=(0, r_y_main), xytext=(0.10, y_rc_bot - 0.32),
        arrowprops=dict(arrowstyle="->", color="#1d4ed8", lw=2.4),
        fontsize=14.5, weight="bold", color="#1d4ed8", ha="left", linespacing=1.3,
        bbox=dict(boxstyle="round,pad=0.40", facecolor="#eff6ff", edgecolor="#3b82f6", lw=2.0),
        zorder=9
    )

    # Cross Secondary Steel Leader
    ax.annotate(
        f"Cross Secondary Steel [B-dir] — غطاء الاتجاه القصير:\n{n_sht} Φ{Phi}   ({n_m_sht} Φ{Phi}/m)  @  {sp_sht:.1f} cm",
        xy=(x_cross_dots[8], y_dot), xytext=(L_m * 0.38, y_rc_bot + trc_m * 0.45),
        arrowprops=dict(arrowstyle="->", color="#15803d", lw=2.4),
        fontsize=14.5, weight="bold", color="#15803d", ha="left", linespacing=1.3,
        bbox=dict(boxstyle="round,pad=0.40", facecolor="#f0fdf4", edgecolor="#22c55e", lw=2.0),
        zorder=9
    )

    # Column Starter Bars Leader
    ax.annotate(
        f"Column Starter Dowels — أشاير كانات رقبة العمود:\n4Φ16 Starter Dowels + Leg ≥ {leg_len*100:.0f} cm\nTies: 5 Φ8/m (كانات رقبة العمود)",
        xy=(col_bar_L, y_col_top - 0.25), xytext=(-L_m * 0.56, y_col_top - 0.15),
        arrowprops=dict(arrowstyle="->", color="#dc2626", lw=2.4),
        fontsize=14.5, weight="bold", color="#991b1b", ha="right", linespacing=1.3,
        bbox=dict(boxstyle="round,pad=0.40", facecolor="#fee2e2", edgecolor="#ef4444", lw=2.0),
        zorder=9
    )

    # 7. MAXIMIZED Elevation Dimensions Chains
    dim_x_l1 = -L_pc_m / 2.0 - 0.34
    dim_x_l2 = dim_x_l1 - 0.38

    # Thickness t_rc & t_pc dimensions
    ax.annotate("", xy=(dim_x_l1, y_rc_top), xytext=(dim_x_l1, y_rc_bot),
                arrowprops=dict(arrowstyle="<->", color="#1e40af", lw=2.8))
    ax.text(dim_x_l1 - 0.08, y_rc_bot + trc_m/2.0, f"t_rc = {t_rc_cm} cm\n(d = {t_rc_cm-cover_cm:.0f} cm)", ha="right", va="center", fontsize=15.5, weight="bold", color="#1e40af")

    ax.annotate("", xy=(dim_x_l1, y_rc_bot), xytext=(dim_x_l1, y_base),
                arrowprops=dict(arrowstyle="<->", color="#475569", lw=2.4))
    ax.text(dim_x_l1 - 0.08, y_base + tpc_m/2.0, f"t_pc = {t_pc_cm} cm", ha="right", va="center", fontsize=14.5, weight="bold", color="#475569")

    # Foundation Depth Df dimension
    ax.annotate("", xy=(dim_x_l2, y_gl), xytext=(dim_x_l2, y_base),
                arrowprops=dict(arrowstyle="<->", color="#78350f", lw=3.0))
    ax.text(dim_x_l2 - 0.08, (y_gl + y_base)/2.0, f"Df = {Df_m:.2f} m\n(عمق التأسيس)", ha="right", va="center", fontsize=16.0, weight="bold", color="#78350f")

    # Horizontal Elevation Span Dimension
    dim_y_bot = y_base - 0.20
    ax.annotate("", xy=(L_m/2.0, dim_y_bot), xytext=(-L_m/2.0, dim_y_bot),
                arrowprops=dict(arrowstyle="<->", color="#1e40af", lw=3.0))
    ax.text(0, dim_y_bot - 0.10, f"R.C. Footing Length  L = {L_cm} cm  ({L_m:.2f} m)", ha="center", va="top", fontsize=16.5, weight="bold", color="#1e40af")

    ax.set_title("ISOLATED FOOTING — SECTION ELEVATION A-A (القطاع الرأسي وتفاصيل التسليح الإنشائي)",
                 fontsize=19.5, weight="bold", pad=20, color="#0f172a")

    margin_s = max(L_pc_m, L_m) * 0.44
    ax.set_xlim(-L_pc_m/2.0 - margin_s - 0.35, L_pc_m/2.0 + margin_s + 0.45)
    ax.set_ylim(y_base - 0.55, max(y_gl, y_col_top) + 0.45)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    fig.tight_layout()
    return fig



def render():
    st.markdown(
        '<div class="section-header">🪨 Module 3 – Isolated Footing Design (ECP 203) (تصميم القواعد المنفصلة)</div>',
        unsafe_allow_html=True,
    )

    # ── INPUTS ──────────────────────────────────────────────────────────────
    with st.expander("📝 Design Inputs (مدخلات التصميم والأبعاد والأحمال)", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**🔩 Column & Loads**")
            bc     = S.number_input("Column Width  bc  (cm)",            "ftg_bc",         min_value=None, step=5)
            tc     = S.number_input("Column Depth  tc  (cm)",            "ftg_tc",         min_value=None, step=5)
            Pu     = S.number_input("Column Load  Pu  (ton)",            "ftg_Pu",         min_value=None, step=10.0)
            Wf_est = S.number_input("Est. Footing Self-Wt (%Pu)",        "ftg_Wf_est",     min_value=None, step=5.0)

        with c2:
            st.markdown("**🌱 Soil Parameters**")
            q_all  = S.number_input("Allowable SBC  q_all  (kg/cm²)",   "ftg_q_all",      min_value=None, step=0.1,
                                    help="Gross allowable bearing capacity at foundation level (realistic range: 0.5 - 5.0 kg/cm²)")
            Df     = S.number_input("Depth of Footing  Df  (m)",         "ftg_Df",         min_value=None, step=0.1)
            gamma_soil = S.number_input("Soil Unit Weight  γ  (ton/m³)", "ftg_gamma_soil", min_value=None, step=0.1)

        with c3:
            st.markdown("**🧱 Materials**")
            Fcu    = S.number_input("Concrete  Fcu  (kg/cm²)",           "ftg_Fcu",        min_value=None, step=25)
            Fy     = S.number_input("Steel  Fy  (kg/cm²)",               "ftg_Fy",         min_value=None, step=200)
            cover  = S.number_input("Concrete Cover  (cm)",              "ftg_cover",      min_value=None, step=1)
            Phi    = S.selectbox("Main Bar Dia  Φ  (mm)", "ftg_Phi_index", options=[12, 16, 18, 22, 25])

    # ── ILLOGICAL INPUT SCREENING & WARNING ALERTS ───────────────────────────
    invalid_inputs = []

    if bc is None or bc <= 0:
        invalid_inputs.append(f"Column Width bc must be greater than zero (got {bc}).")
    if tc is None or tc <= 0:
        invalid_inputs.append(f"Column Depth tc must be greater than zero (got {tc}).")
    if Pu is None or Pu <= 0:
        invalid_inputs.append(f"Column Load Pu must be greater than zero (got {Pu}).")
    if Wf_est is None or Wf_est <= 0:
        invalid_inputs.append(f"Footing Self-Weight estimate must be greater than zero (got {Wf_est}).")
    if Df is None or Df <= 0:
        invalid_inputs.append(f"Footing Depth Df must be greater than zero (got {Df}).")
    if gamma_soil is None or gamma_soil <= 0:
        invalid_inputs.append(f"Soil Unit Weight γ must be greater than zero (got {gamma_soil}).")
    if Fcu is None or Fcu <= 0:
        invalid_inputs.append(f"Concrete Strength Fcu must be greater than zero (got {Fcu}).")
    if Fy is None or Fy <= 0:
        invalid_inputs.append(f"Steel Yield Strength Fy must be greater than zero (got {Fy}).")
    if cover is None or cover <= 0:
        invalid_inputs.append(f"Concrete Cover must be greater than zero (got {cover}).")

    if q_all is None or q_all < 0.5 or q_all > 5.0:
        invalid_inputs.append(
            f"Soil bearing capacity (q_all = {q_all} kg/cm²) is outside the realistic engineering range of 0.5 to 5.0 kg/cm²."
        )

    if Fy is not None and Fcu is not None and Fy <= Fcu:
        invalid_inputs.append(
            f"Unrealistic material strength ratio: Steel yield strength Fy ({Fy} kg/cm²) must be greater than concrete compressive strength Fcu ({Fcu} kg/cm²)."
        )

    if invalid_inputs:
        st.error("⚠️ **Illogical Input Detected! Calculation Stopped.**")
        for err in invalid_inputs:
            st.warning(f"• {err}")
        return

    # ── PRELIMINARY CALCULATIONS ─────────────────────────────────────────────

    gamma_soil_kgcm3 = gamma_soil * 1000 / (100**3)
    Df_cm            = Df * 100
    q_surcharge      = gamma_soil_kgcm3 * Df_cm
    q_net            = q_all - q_surcharge
    if q_net <= 0:
        st.error("Net bearing capacity is zero or negative. Increase q_all or reduce Df.")
        return

    Pu_kg      = Pu * 1000.0
    P_serv_kg  = Pu_kg / 1.5
    Ptotal_kg  = P_serv_kg * (1.0 + Wf_est / 100.0)

    # ── INITIAL RECTANGULAR SIZING (Equal-Overhang Method) ──────────────────
    A_req_cm2        = Ptotal_kg / q_all
    L_req, B_req     = initial_LB(A_req_cm2, tc, bc)

    # Allowable shear stresses
    tau_p_allow = 0.316 * math.sqrt(Fcu)
    tau_1_allow = 0.16  * math.sqrt(Fcu)

    # ── AUTO-SUGGESTED THICKNESS ─────────────────────────────────────────────
    L_temp = L_req
    B_temp = B_req
    A_f_temp   = L_temp * B_temp
    q_u_temp   = Pu_kg  / A_f_temp
    cant_long_temp = (L_temp - tc) / 2.0
    cant_sht_temp  = (B_temp - bc) / 2.0

    def calc_punching_d(A_f_val, q_u_val):
        d_p = 20
        for _ in range(300):
            b0      = 2 * ((bc + d_p) + (tc + d_p))
            A_out   = (bc + d_p) * (tc + d_p)
            Vp      = q_u_val * (A_f_val - A_out)
            tau     = Vp / (b0 * d_p) if d_p > 0 else 999
            if tau <= tau_p_allow:
                break
            d_p += 1
        return d_p

    def calc_oneway_d(B_val, L_val, q_u_val, c_long, c_sht):
        d_1 = 20
        for _ in range(300):
            a_long  = max(c_long - d_1, 0)
            V_long  = q_u_val * B_val * a_long
            tau_l   = V_long / (B_val * d_1) if d_1 > 0 else 999
            a_sht   = max(c_sht - d_1, 0)
            V_sht   = q_u_val * L_val * a_sht
            tau_s   = V_sht / (L_val * d_1) if d_1 > 0 else 999
            if max(tau_l, tau_s) <= tau_1_allow:
                break
            d_1 += 1
        return d_1

    a_bar = math.pi * (Phi / 10.0)**2 / 4.0
    d_punch_min  = calc_punching_d(A_f_temp, q_u_temp)
    d_oneway_min = calc_oneway_d(B_temp, L_temp, q_u_temp, cant_long_temp, cant_sht_temp)

    M_long_temp = q_u_temp * B_temp * cant_long_temp**2 / 2.0
    M_sht_temp  = q_u_temp * L_temp * cant_sht_temp**2  / 2.0

    As_max_10_long_temp = 10.0 * a_bar * (B_temp / 100.0)
    As_max_10_sht_temp  = 10.0 * a_bar * (L_temp / 100.0)
    a_block_long = (As_max_10_long_temp * Fy) / (0.85 * Fcu * B_temp)
    a_block_sht  = (As_max_10_sht_temp  * Fy) / (0.85 * Fcu * L_temp)

    d_rebar_long = (M_long_temp / (0.9 * Fy * As_max_10_long_temp)) + (a_block_long / 2.0)
    d_rebar_sht  = (M_sht_temp  / (0.9 * Fy * As_max_10_sht_temp))  + (a_block_sht  / 2.0)
    d_rebar_limit_temp = max(d_rebar_long, d_rebar_sht)

    d_min_suggested    = max(d_punch_min, d_oneway_min, d_rebar_limit_temp)
    t_rc_raw_suggested = d_min_suggested + cover + (Phi / 10.0 / 2.0)
    t_rc_min_suggested = max(40, round_up_to_5(t_rc_raw_suggested))

    # ── DETECT INPUT CHANGES & AUTO-RECALCULATE SIZING ───────────────────────
    curr_inputs_sig = (
        float(bc), float(tc), float(Pu), float(Wf_est), float(q_all),
        float(Df), float(gamma_soil), float(Fcu), float(Fy), float(cover), int(Phi)
    )
    prev_inputs_sig = st.session_state.get("_ftg_inputs_sig")

    if prev_inputs_sig is None or prev_inputs_sig != curr_inputs_sig:
        st.session_state["_ftg_inputs_sig"] = curr_inputs_sig
        st.session_state["w_ftg_L_override"] = int(L_req)
        st.session_state["w_ftg_B_override"] = int(B_req)
        st.session_state["w_ftg_trc_override"] = int(t_rc_min_suggested)
        S.cfg_set("ftg_L_override", int(L_req))
        S.cfg_set("ftg_B_override", int(B_req))
        S.cfg_set("ftg_trc_override", int(t_rc_min_suggested))

    # ── SECTION HEADER ───────────────────────────────────────────────────────
    st.markdown(
        '<div class="section-header">📊 Design Results & Structural Verification (نتائج التصميم والتحقق الإنشائي)</div>',
        unsafe_allow_html=True,
    )

    # ── INTERACTIVE SIZING CONTROLS ──────────────────────────────────────────
    saved_L   = S.cfg_val("ftg_L_override")
    saved_B   = S.cfg_val("ftg_B_override")
    saved_trc = S.cfg_val("ftg_trc_override")

    default_L   = int(saved_L)   if saved_L   is not None else int(L_req)
    default_B   = int(saved_B)   if saved_B   is not None else int(B_req)
    default_trc = int(saved_trc) if saved_trc is not None else int(t_rc_min_suggested)

    with st.expander("📐 Interactive Footing Sizing Controls (Dynamic Dimensioning) (التحكم التفاعلي في أبعاد القاعدة)", expanded=True):
        col_L, col_B, col_t = st.columns(3)

        with col_L:
            L_user = st.number_input(
                "Footing Length  L  (cm)",
                min_value=50, max_value=2000,
                value=default_L, step=5,
                key="w_ftg_L_override",
                help=f"Step 5 cm. Default = auto-suggested minimum for equal overhangs ({L_req} cm).",
                on_change=lambda: S.cfg_set("ftg_L_override", st.session_state["w_ftg_L_override"]),
            )
            st.caption(
                f"💡 **Suggested Min.:** `{L_req} cm` "
                f"*(Long side — col. depth tc = {tc} cm, overhang = {(L_req - tc)/2:.0f} cm)*"
            )

        with col_B:
            B_user = st.number_input(
                "Footing Width  B  (cm)",
                min_value=50, max_value=2000,
                value=default_B, step=5,
                key="w_ftg_B_override",
                help=f"Step 5 cm. Default = auto-suggested minimum for equal overhangs ({B_req} cm).",
                on_change=lambda: S.cfg_set("ftg_B_override", st.session_state["w_ftg_B_override"]),
            )
            st.caption(
                f"💡 **Suggested Min.:** `{B_req} cm` "
                f"*(Short side — col. width bc = {bc} cm, overhang = {(B_req - bc)/2:.0f} cm)*"
            )

        with col_t:
            t_rc_user = st.number_input(
                "R.C. Footing Thickness  t_rc  (cm)",
                min_value=20, max_value=300,
                value=default_trc, step=5,
                key="w_ftg_trc_override",
                help=f"Step 5 cm. Default matches auto-suggested minimum thickness ({t_rc_min_suggested} cm).",
                on_change=lambda: S.cfg_set("ftg_trc_override", st.session_state["w_ftg_trc_override"]),
            )
            st.caption(
                f"💡 **Suggested Min.:** `{t_rc_min_suggested} cm` "
                f"*(Rounded up to nearest 5 cm per ECP 203)*"
            )

        if st.button("↺ Reset Dimensions to Auto-Calculated (العودة للأبعاد المحسوبة تلقائياً)", use_container_width=True):
            st.session_state["w_ftg_L_override"] = int(L_req)
            st.session_state["w_ftg_B_override"] = int(B_req)
            st.session_state["w_ftg_trc_override"] = int(t_rc_min_suggested)
            S.cfg_set("ftg_L_override", int(L_req))
            S.cfg_set("ftg_B_override", int(B_req))
            S.cfg_set("ftg_trc_override", int(t_rc_min_suggested))
            st.rerun()

    # ── ACTIVE DYNAMIC RE-CALCULATIONS ───────────────────────────────────────
    L    = L_user
    B    = B_user
    t_rc = t_rc_user
    A_f  = L * B
    q_u  = Pu_kg / A_f
    t_pc = 10

    # 1) Soil Bearing Capacity Check
    q_act  = Ptotal_kg / A_f
    q_ok   = q_act <= q_all
    util_q = (q_act / q_all) * 100.0

    if not q_ok:
        st.warning(
            f"⚠️ **Soil Bearing Capacity Exceeded:** Actual q_act = **{q_act:.3f} kg/cm²** "
            f"> Allowable q_all = **{q_all:.2f} kg/cm²** (Utilisation: {util_q:.1f}%). "
            f"Increase L × B area — suggested minimum plan: **{L_req} × {B_req} cm** "
            f"(area = {L_req * B_req:,} cm²)."
        )

    cantilever_long = (L - tc) / 2.0
    cantilever_sht  = (B - bc) / 2.0

    if cantilever_long <= 0 or cantilever_sht <= 0:
        st.error(
            "Footing dimensions are smaller than the column! "
            "Please increase L and B so the footing projects beyond the column on all sides."
        )
        return

    d_actual = t_rc - cover - (Phi / 10.0 / 2.0)
    if d_actual <= 0:
        st.error("Selected footing thickness is smaller than concrete cover!")
        return

    # 2) Punching Shear Check
    b0          = 2 * ((bc + d_actual) + (tc + d_actual))
    A_punch_out = (bc + d_actual) * (tc + d_actual)
    Vp          = q_u * (A_f - A_punch_out)
    tau_p_act   = Vp / (b0 * d_actual) if d_actual > 0 else 999
    p_ok        = tau_p_act <= tau_p_allow

    # 3) One-Way Shear Checks (both directions independently)
    a_strip_long  = max(cantilever_long - d_actual, 0)
    V1_long       = q_u * B * a_strip_long
    tau_1_long    = V1_long / (B * d_actual) if d_actual > 0 else 999

    a_strip_sht   = max(cantilever_sht - d_actual, 0)
    V1_sht        = q_u * L * a_strip_sht
    tau_1_sht     = V1_sht / (L * d_actual) if d_actual > 0 else 999

    tau_1_act     = max(tau_1_long, tau_1_sht)
    s_ok          = tau_1_act <= tau_1_allow

    # 4) Bending Moments & Reinforcement
    M_long = q_u * B * cantilever_long**2 / 2.0
    M_sht  = q_u * L * cantilever_sht**2  / 2.0

    def As_required(M_kgcm, d_cm, b_cm, t_ref):
        a_est  = 0.1 * d_cm
        As_est = M_kgcm / (0.9 * Fy * (d_cm - a_est / 2.0))
        a_ref  = (As_est * Fy) / (0.85 * Fcu * b_cm)
        As_ref = M_kgcm / (0.9 * Fy * (d_cm - a_ref / 2.0))
        As_min = 0.0025 * b_cm * t_ref
        return max(As_ref, As_min)

    As_long = As_required(M_long, d_actual, B, t_rc)
    As_sht  = As_required(M_sht,  d_actual, L, t_rc)

    B_m = B / 100.0
    L_m = L / 100.0

    As_per_m_long = As_long / B_m
    As_per_m_sht  = As_sht  / L_m

    raw_n_m_long = As_per_m_long / a_bar
    raw_n_m_sht  = As_per_m_sht  / a_bar

    n_bars_m_long = math.ceil(raw_n_m_long)
    n_bars_m_sht  = math.ceil(raw_n_m_sht)
    n_bars_m_max  = max(n_bars_m_long, n_bars_m_sht)
    rebar_ok      = n_bars_m_max <= 10

    # ── SAFETY CHECKS – HARD STOP ON STRUCTURAL FAILURE ─────────────────────
    if not q_ok or not (p_ok and s_ok and rebar_ok):
        err_msgs = []
        if not q_ok:
            err_msgs.append(
                f"**Soil Bearing Capacity Exceeded:** q_act = **{q_act:.3f} kg/cm²** "
                f"> q_all = **{q_all:.2f} kg/cm²** (Util: {util_q:.1f}%). "
                f"→ *Increase L × B to at least* **{L_req} × {B_req} cm**."
            )
        if not p_ok:
            err_msgs.append(
                f"**Punching Shear Exceeded:** τ_p = **{tau_p_act:.3f} kg/cm²** "
                f"> τ_p,allow = **{tau_p_allow:.3f} kg/cm²**. "
                f"→ *Increase R.C. Thickness t_rc.*"
            )
        if not s_ok:
            dir_label = "Long" if tau_1_long >= tau_1_sht else "Short"
            err_msgs.append(
                f"**One-Way Shear Exceeded ({dir_label} dir.):** τ_1 = **{tau_1_act:.3f} kg/cm²** "
                f"> τ_1,allow = **{tau_1_allow:.3f} kg/cm²**. "
                f"→ *Increase R.C. Thickness t_rc.*"
            )
        if not rebar_ok:
            err_msgs.append(
                f"**Rebar Congestion Limit Exceeded (ECP 203):** Required = **{n_bars_m_max} Φ{Phi}/m** "
                f"(> 10 Φ/m limit). "
                f"→ *Increase t_rc (min {t_rc_min_suggested} cm) or select a larger bar diameter.*"
            )

        st.error(
            "⚠️ **DESIGN NOT SAFE / ECP 203 CHECK FAILED:**\n\n"
            + "\n\n".join(f"• {msg}" for msg in err_msgs)
        )
        return

    # ── MINIMUM REINFORCEMENT ENFORCEMENT (<5 bars/m) ─────────────────────────
    min_enforced = raw_n_m_long < 5.0 or raw_n_m_sht < 5.0
    density_long_use = max(5.0, raw_n_m_long)
    density_sht_use  = max(5.0, raw_n_m_sht)
    n_m_long = math.ceil(density_long_use)
    n_m_sht  = math.ceil(density_sht_use)

    n_long = math.ceil(n_m_long * B_m)
    n_sht  = math.ceil(n_m_sht  * L_m)

    As_long_prov = n_long * a_bar
    As_sht_prov  = n_sht  * a_bar

    sp_long = (B - 2.0 * cover) / (n_long - 1.0) if n_long > 1 else (B - 2.0 * cover)
    sp_sht  = (L - 2.0 * cover) / (n_sht  - 1.0) if n_sht  > 1 else (L - 2.0 * cover)

    # ── OUTPUTS ──────────────────────────────────────────────────────────────

    if min_enforced:
        st.info(
            f"ℹ️ **Minimum Code Reinforcement Enforced:** Steel area < 5 bars/m. "
            f"Enforced ECP 203 minimum of 5 Φ{Phi}/m."
        )

    st.markdown(
        '<div class="result-ok" style="font-size: 0.95rem; text-align: center;">'
        '✅ SAFE DESIGN – ALL ECP 203 CHECKS SATISFIED</div>',
        unsafe_allow_html=True,
    )

    # ── KEY DESIGN METRICS GRID ──────────────────────────────────────────────
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

    with m_col1:
        st.markdown(
            f"""
            <div style="background: #f0f4ff; border: 1px solid #c8d4f0; border-radius: 8px; padding: 8px 10px; text-align: center; min-height: 64px; display: flex; flex-direction: column; justify-content: center;">
                <div style="color: #3a4a6b; font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 2px;">Footing Plan</div>
                <div style="color: #1a2340; font-size: 0.82rem; font-weight: 700; white-space: normal; word-break: break-word;">{L} × {B} cm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m_col2:
        st.markdown(
            f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; text-align: center; min-height: 64px; display: flex; flex-direction: column; justify-content: center;">
                <div style="color: #64748b; font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 2px;">P.C. Blinding</div>
                <div style="color: #64748b; font-size: 0.78rem; font-weight: 600; white-space: normal; word-break: break-word;">10 cm (Non-structural)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m_col3:
        st.markdown(
            f"""
            <div style="background: #f0f4ff; border: 1px solid #c8d4f0; border-radius: 8px; padding: 8px 10px; text-align: center; min-height: 64px; display: flex; flex-direction: column; justify-content: center;">
                <div style="color: #3a4a6b; font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 2px;">RC Thickness</div>
                <div style="color: #1a2340; font-size: 0.82rem; font-weight: 700; white-space: normal; word-break: break-word;">{t_rc} cm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m_col4:
        st.markdown(
            f"""
            <div style="background: #f0f4ff; border: 1px solid #c8d4f0; border-radius: 8px; padding: 8px 10px; text-align: center; min-height: 64px; display: flex; flex-direction: column; justify-content: center;">
                <div style="color: #3a4a6b; font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 2px;">Long Steel (L-dir)</div>
                <div style="color: #1a2340; font-size: 0.82rem; font-weight: 700; white-space: normal; word-break: break-word;">{n_long} Φ{Phi} ({n_m_long} Φ{Phi}/m)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m_col5:
        st.markdown(
            f"""
            <div style="background: #f0f4ff; border: 1px solid #c8d4f0; border-radius: 8px; padding: 8px 10px; text-align: center; min-height: 64px; display: flex; flex-direction: column; justify-content: center;">
                <div style="color: #3a4a6b; font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 2px;">Short Steel (B-dir)</div>
                <div style="color: #1a2340; font-size: 0.82rem; font-weight: 700; white-space: normal; word-break: break-word;">{n_sht} Φ{Phi} ({n_m_sht} Φ{Phi}/m)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── 📐 CAD DRAWINGS & REINFORCEMENT SKETCHES ────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div class="section-header">📐 Structural Detailing Sketches (المخططات الإنشائية وتفاصيل التسليح)</div>',
        unsafe_allow_html=True,
    )

    # 1. Plan View Sketch (المسقط الأفقي)
    st.markdown("#### 1️⃣ المسقط الأفقي للقاعدة الخرسانية المسلحة والعادية (Plan View)")
    fig_plan = generate_footing_plan_sketch(
        L_cm=L,
        B_cm=B,
        t_rc_cm=t_rc,
        bc_cm=bc,
        tc_cm=tc,
        Phi=Phi,
        n_long=n_long,
        n_m_long=n_m_long,
        sp_long=sp_long,
        n_sht=n_sht,
        n_m_sht=n_m_sht,
        sp_sht=sp_sht,
        cover_cm=cover,
        t_pc_cm=10,
        pc_offset_cm=10,
    )
    st.pyplot(fig_plan, use_container_width=True)

    buf_plan = io.BytesIO()
    fig_plan.savefig(buf_plan, format="png", bbox_inches="tight", dpi=300)
    buf_plan.seek(0)
    img_plan_bytes = buf_plan.getvalue()
    img_plan_b64 = f"data:image/png;base64,{base64.b64encode(img_plan_bytes).decode('utf-8')}"
    plt.close(fig_plan)

    c_p1, c_p2 = st.columns([3, 1])
    with c_p1:
        st.caption("📐 **المسقط الأفقي:** يوضح أبعاد القاعدة المسلحة (L × B)، ورفرفة العادية، ومحاور الأعمدة، وتوزيع حديد الفرش والغطاء والمسافات البينية بدقة عالية وخطوط واضحة.")
    prefix = S.get_safe_profile_filename_prefix()
    with c_p2:
        st.download_button(
            label="📥 Download Plan View (PNG)",
            data=img_plan_bytes,
            file_name=f"{prefix}ECP203_Footing_Plan_{L}x{B}cm.png",
            mime="image/png",
            use_container_width=True,
            key="dl_plan_sketch",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Section Elevation View Sketch (القطاع الرأسي والتسليح)
    st.markdown("#### 2️⃣ القطاع الرأسي وتفاصيل التسليح الإنشائي (Section Elevation A-A)")
    fig_sec = generate_footing_section_sketch(
        L_cm=L,
        B_cm=B,
        t_rc_cm=t_rc,
        bc_cm=bc,
        tc_cm=tc,
        Phi=Phi,
        n_long=n_long,
        n_m_long=n_m_long,
        sp_long=sp_long,
        n_sht=n_sht,
        n_m_sht=n_m_sht,
        sp_sht=sp_sht,
        cover_cm=cover,
        Df_m=Df,
        t_pc_cm=10,
        pc_offset_cm=10,
    )
    st.pyplot(fig_sec, use_container_width=True)

    buf_sec = io.BytesIO()
    fig_sec.savefig(buf_sec, format="png", bbox_inches="tight", dpi=300)
    buf_sec.seek(0)
    img_sec_bytes = buf_sec.getvalue()
    img_sec_b64 = f"data:image/png;base64,{base64.b64encode(img_sec_bytes).decode('utf-8')}"
    plt.close(fig_sec)

    c_s1, c_s2 = st.columns([3, 1])
    with c_s1:
        st.caption("📐 **القطاع الرأسي (A-A):** يوضح سمك المسلحة (t_rc) والعمق الفعال (d)، وسمك العادية وعمق التأسيس (Df)، مع تفاصيل تفريد حديد الفرش (U-Hooks) والغطاء وأشاير ورقبة العمود وكاناتها.")
    with c_s2:
        st.download_button(
            label="📥 Download Section Elevation (PNG)",
            data=img_sec_bytes,
            file_name=f"{prefix}ECP203_Footing_Section_{L}x{B}cm.png",
            mime="image/png",
            use_container_width=True,
            key="dl_sec_sketch",
        )

    # ── REINFORCEMENT LAYOUT CARDS ───────────────────────────────────────────
    with st.expander("🔩 Reinforcement Layout (ECP 203) (مخطط وتفاصيل حديد التسليح)", expanded=False):
        c_long, c_sht = st.columns(2)
        with c_long:
            st.markdown(
                f"""
                <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 14px;">
                    <div style="font-weight: 700; font-size: 0.85rem; color: #1e293b; margin-bottom: 6px;">
                        ↔️ Long Direction – L = {L} cm (Cantilever c<sub>L</sub> = {cantilever_long:.1f} cm)
                    </div>
                    <ul style="font-size: 0.8rem; color: #334155; margin: 0; padding-left: 18px; line-height: 1.5;">
                        <li><b>Bars run parallel to L, spaced over B = {B} cm</b></li>
                        <li><b>Total Bars:</b> {n_long} Φ{Phi} mm ({As_long_prov:.2f} cm²)</li>
                        <li><b>Reinforcement Density:</b> {n_m_long} Φ{Phi} / meter</li>
                        <li><b>Required Area:</b> {As_long:.2f} cm² ({As_per_m_long:.2f} cm²/m)</li>
                        <li><b>Center-to-Center Spacing:</b> @ {sp_long:.1f} cm</li>
                        <li><b>Bending Moment M<sub>L</sub>:</b> {M_long/100000:.3f} t·m ({M_long:,.0f} kg·cm)</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_sht:
            st.markdown(
                f"""
                <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 14px;">
                    <div style="font-weight: 700; font-size: 0.85rem; color: #1e293b; margin-bottom: 6px;">
                        ↕️ Short Direction – B = {B} cm (Cantilever c<sub>B</sub> = {cantilever_sht:.1f} cm)
                    </div>
                    <ul style="font-size: 0.8rem; color: #334155; margin: 0; padding-left: 18px; line-height: 1.5;">
                        <li><b>Bars run parallel to B, spaced over L = {L} cm</b></li>
                        <li><b>Total Bars:</b> {n_sht} Φ{Phi} mm ({As_sht_prov:.2f} cm²)</li>
                        <li><b>Reinforcement Density:</b> {n_m_sht} Φ{Phi} / meter</li>
                        <li><b>Required Area:</b> {As_sht:.2f} cm² ({As_per_m_sht:.2f} cm²/m)</li>
                        <li><b>Center-to-Center Spacing:</b> @ {sp_sht:.1f} cm</li>
                        <li><b>Bending Moment M<sub>B</sub>:</b> {M_sht/100000:.3f} t·m ({M_sht:,.0f} kg·cm)</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── DETAILED CALCULATION SHEET (TABS) ────────────────────────────────────
    with st.expander("📋 Detailed Calculation Sheet (جدول الحسابات التفصيلية الكاملة)", expanded=False):
        tab_geom, tab_conc, tab_rebar = st.tabs([
            "📐 Geometry & Soil Pressures",
            "🧱 Concrete & Shear Checks",
            "🔩 Bending & Reinforcement",
        ])

        with tab_geom:
            df_geom = pd.DataFrame({
                "Parameter": [
                    "Column Size (bc × tc)",
                    "Column Ultimate Load (Pu)",
                    "Total Service Load for Area (1.15 × Pu)",
                    "Gross Allowable SBC (q_all)",
                    "Net Allowable SBC (q_net)",
                    "Auto-Suggested Min. Footing Area",
                    "Auto-Suggested Min. Footing Length (L_req)",
                    "Auto-Suggested Min. Footing Width (B_req)",
                    "Initial Overhang per Side (equal)",
                    "Adopted Footing Length (L)",
                    "Adopted Footing Width (B)",
                    "Adopted Footing Plan (L × B)",
                    "Actual Footing Area (A_f)",
                    "Actual Soil Bearing Stress (q_act)",
                    "Net Ultimate Soil Pressure (q_u)",
                    "P.C. Layer Thickness (t_pc)",
                    "Long-Direction Cantilever (c_L)",
                    "Short-Direction Cantilever (c_B)",
                ],
                "Value": [
                    f"{bc} × {tc} cm",
                    f"{Pu:.1f} ton",
                    f"{Ptotal_kg/1000:.2f} ton  ({Ptotal_kg:,.0f} kg)",
                    f"{q_all:.2f} kg/cm²",
                    f"{q_net:.3f} kg/cm²",
                    f"{A_req_cm2:.1f} cm²",
                    f"{L_req} cm",
                    f"{B_req} cm",
                    f"{(L_req - tc)/2:.1f} cm  [= (L_req − tc)/2 = (B_req − bc)/2]",
                    f"{L} cm",
                    f"{B} cm",
                    f"{L} × {B} cm",
                    f"{A_f:,} cm²",
                    f"{q_act:.3f} kg/cm² (util = {util_q:.1f}%) {'✅' if q_ok else '⚠️'}",
                    f"{q_u:.4f} kg/cm²",
                    "10 cm (Blinding – Non-structural)",
                    f"{cantilever_long:.1f} cm",
                    f"{cantilever_sht:.1f} cm",
                ],
                "Reference": [
                    "User input",
                    "User input",
                    "1.15 × Pu (Self-weight allowance)",
                    "User input",
                    "q_all − γ_soil × Df",
                    "(Pu × 1.15) / q_all",
                    "Equal-overhang quadratic sizing",
                    "Equal-overhang quadratic sizing",
                    "(L_req − tc)/2 = (B_req − bc)/2",
                    "Interactive user input",
                    "Interactive user input",
                    "L × B",
                    "L × B",
                    "Ptotal / A_f",
                    "Pu / A_f",
                    "Blinding layer under R.C.",
                    "(L − tc) / 2",
                    "(B − bc) / 2",
                ],
            })
            st.dataframe(df_geom, use_container_width=True, hide_index=True)

        with tab_conc:
            df_conc = pd.DataFrame({
                "Parameter": [
                    "P.C. Structural Contribution",
                    "P.C. Blinding Layer Thickness",
                    "Allowable Punching Shear (τ_p,allow)",
                    "Punching Perimeter (b₀)",
                    "Actual Punching Shear (τ_p,act)",
                    "Allowable One-Way Shear (τ_1,allow)",
                    "Actual One-Way Shear – Long Dir. (τ_1,L)",
                    "Actual One-Way Shear – Short Dir. (τ_1,B)",
                    "Governing One-Way Shear (τ_1,act)",
                    "Governing Min. Effective Depth (d_min)",
                    "Auto-Suggested Min. Thickness (t_rc,min)",
                    "Adopted R.C. Thickness (t_rc)",
                    "Actual Effective Depth (d_actual)",
                ],
                "Value": [
                    "Ignored (R.C. directly on soil)",
                    "10 cm (Non-structural)",
                    f"{tau_p_allow:.3f} kg/cm²",
                    f"{b0:.1f} cm",
                    f"{tau_p_act:.3f} kg/cm² (util = {(tau_p_act/tau_p_allow)*100:.1f}%) {'✅' if p_ok else '❌'}",
                    f"{tau_1_allow:.3f} kg/cm²",
                    f"{tau_1_long:.3f} kg/cm² (util = {(tau_1_long/tau_1_allow)*100:.1f}%) {'✅' if tau_1_long <= tau_1_allow else '❌'}",
                    f"{tau_1_sht:.3f} kg/cm²  (util = {(tau_1_sht/tau_1_allow)*100:.1f}%) {'✅' if tau_1_sht <= tau_1_allow else '❌'}",
                    f"{tau_1_act:.3f} kg/cm² {'✅' if s_ok else '❌'}",
                    f"{d_min_suggested:.1f} cm",
                    f"{t_rc_min_suggested} cm (rounded up 5 cm)",
                    f"{t_rc} cm",
                    f"{d_actual:.1f} cm",
                ],
                "Reference": [
                    "Direct R.C. Design",
                    "Blinding layer",
                    "0.316 × √Fcu",
                    "2×[(bc+d) + (tc+d)]",
                    "Vp / (b₀ × d)",
                    "0.16 × √Fcu",
                    "q_u × B × (c_L − d) / (B × d)",
                    "q_u × L × (c_B − d) / (L × d)",
                    "max(τ_1,L , τ_1,B)",
                    "max(d_punch, d_oneway, d_rebar_limit)",
                    "d_min + cover + Φ/2 (step 5, min 40)",
                    "Interactive user input",
                    "t_rc − cover − Φ/2",
                ],
            })
            st.dataframe(df_conc, use_container_width=True, hide_index=True)

        with tab_rebar:
            df_rebar = pd.DataFrame({
                "Parameter": [
                    "Bending Moment – Long Dir. (M_L)",
                    "Bending Moment – Short Dir. (M_B)",
                    "Req. Steel Area – Long Dir. (As_long)",
                    "Req. Steel Area – Short Dir. (As_sht)",
                    "Raw Steel Density – Long Dir.",
                    "Raw Steel Density – Short Dir.",
                    "Provided Long Steel Layout",
                    "Provided Short Steel Layout",
                    "Long Bar Center Spacing",
                    "Short Bar Center Spacing",
                ],
                "Value": [
                    f"{M_long/100000:.3f} t·m ({M_long:,.0f} kg·cm)",
                    f"{M_sht/100000:.3f} t·m ({M_sht:,.0f} kg·cm)",
                    f"{As_long:.2f} cm² ({As_per_m_long:.2f} cm²/m)",
                    f"{As_sht:.2f} cm² ({As_per_m_sht:.2f} cm²/m)",
                    f"{raw_n_m_long:.2f} bars/m" + (" (min 5 enforced)" if raw_n_m_long < 5 else ""),
                    f"{raw_n_m_sht:.2f} bars/m"  + (" (min 5 enforced)" if raw_n_m_sht  < 5 else ""),
                    f"{n_long} Φ{Phi} total ({n_m_long} Φ{Phi}/m) – {As_long_prov:.2f} cm²",
                    f"{n_sht} Φ{Phi} total ({n_m_sht} Φ{Phi}/m) – {As_sht_prov:.2f} cm²",
                    f"{sp_long:.1f} cm  (over B = {B} cm)",
                    f"{sp_sht:.1f} cm  (over L = {L} cm)",
                ],
                "Reference": [
                    "q_u × B × c_L² / 2",
                    "q_u × L × c_B² / 2",
                    "M / (0.9 × Fy × d); As_min = 0.0025 × b × t",
                    "M / (0.9 × Fy × d); As_min = 0.0025 × b × t",
                    "As_per_m / A_bar",
                    "As_per_m / A_bar",
                    "n_long × A_bar",
                    "n_sht × A_bar",
                    "(B − 2×cover) / (n_long − 1)",
                    "(L − 2×cover) / (n_sht − 1)",
                ],
            })
            st.dataframe(df_rebar, use_container_width=True, hide_index=True)

    # ── 💾 SAVE & EXPORT COMPLETE CALCULATION SHEET ────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div class="section-header">💾 Save & Export Design Calculation Sheet (حفظ وتصدير المذكرة الحسابية الكاملة)</div>',
        unsafe_allow_html=True,
    )

    from modules.report_generator import generate_footing_report_html, html_to_pdf_bytes

    footing_report_html = generate_footing_report_html(
        project_name="Isolated Footing Design (ECP 203)",
        col_bc=bc,
        col_tc=tc,
        P_serv=Ptotal_kg / 1000.0,
        Pu=Pu,
        q_all=q_all,
        L_rc=L / 100.0,
        B_rc=B / 100.0,
        d_rc=d_actual,
        rebar_L_str=f"{n_long} Φ{Phi} total ({n_m_long} Φ{Phi}/m) @ {sp_long:.1f} cm",
        rebar_B_str=f"{n_sht} Φ{Phi} total ({n_m_sht} Φ{Phi}/m) @ {sp_sht:.1f} cm",
        img_plan_b64=img_plan_b64,
        img_sec_b64=img_sec_b64,
    )

    pdf_bytes = html_to_pdf_bytes(footing_report_html)

    c_save1, c_save2 = st.columns([3, 1])
    with c_save1:
        st.markdown(
            f"""
            <div style='background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:14px 16px;'>
                <div style='font-weight:700; color:#1e293b; font-size:1.0rem;'>
                    📄 مذكرة الحسابات الإنشائية للقاعدة (Isolated Footing Calculation Sheet)
                </div>
                <div style='font-size:0.88rem; color:#64748b; margin-top:2px;'>
                    تتضمن جميع المدخلات، وأبعاد الخرسانة المسلحة والعادية، وفحوصات القص والثقب وإجهاد التربة والتسليح.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c_save2:
        prefix = S.get_safe_profile_filename_prefix()
        st.download_button(
            label="🌐 Save Calculation Sheet (HTML)",
            data=footing_report_html,
            file_name=f"{prefix}ECP203_Footing_Calculation_Sheet_{L}x{B}cm.html",
            mime="text/html",
            use_container_width=True,
        )
        if pdf_bytes:
            st.download_button(
                label="📕 Save as PDF (مباشر)",
                data=pdf_bytes,
                file_name=f"{prefix}ECP203_Footing_Calculation_Sheet_{L}x{B}cm.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    # ── EXECUTIVE DESIGN SUMMARY ─────────────────────────────────────────────
    st.markdown("---")
    st.info(
        f"📐 **Design Summary:** R.C. Footing **{L} × {B} cm** (L × B) directly on soil | "
        f"P.C. **10 cm Blinding (Non-structural)** | R.C. **t = {t_rc} cm** (d = {d_actual:.1f} cm) | "
        f"Long Steel: **{n_long} Φ{Phi}** @ {sp_long:.1f} cm ({n_m_long} Φ{Phi}/m over B) | "
        f"Short Steel: **{n_sht} Φ{Phi}** @ {sp_sht:.1f} cm ({n_m_sht} Φ{Phi}/m over L)."
    )
