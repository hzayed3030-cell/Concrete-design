"""
modules/concrete_survey.py
--------------------------
المساعد — حصر الخرسانات (Concrete Quantity Survey)

Comprehensive concrete volume & material quantity takeoff tool:
  • Customs Tab: Concrete columns quantity survey with 2D horizontal plan & vertical elevation rebar detailing
  • Interactive structural elements quantity survey (Footings, Columns, Beams, Slabs, Walls)
  • Dynamic custom items table
  • Mix Materials Estimator (Cement, Sand, Gravel, Water)
"""

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
import streamlit as st
import pandas as pd
from modules.report_generator import (
    generate_column_survey_report_html,
    html_to_pdf_bytes,
    fig_to_base64,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. DRAWING FUNCTIONS FOR CUSTOMS TAB (COLUMN HORIZONTAL & VERTICAL SECTIONS)
# ═══════════════════════════════════════════════════════════════════════════

def draw_column_horizontal_section(
    b_cm: float,
    t_cm: float,
    n_bars: int,
    phi_mm: int,
    phi_st_mm: int,
    n_rows: int,
    tie_type: str,
    cover: float = 2.5,
) -> plt.Figure:
    """
    Renders the horizontal cross-section / plan of the column showing:
    - Concrete outline (b × t)
    - Perimeter and internal stirrups (Box or Automatic)
    - Longitudinal rebar distribution with coordinate mapping
    - Dimensions and callouts
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"]

    b_val = float(b_cm)
    t_val = float(t_cm)

    # Effective core dimensions
    b_core = max(b_val - 2.0 * cover, 1.0)
    t_core = max(t_val - 2.0 * cover, 1.0)
    hook_sz = min(3.5, max(2.2, b_core * 0.15))

    # Grid rebar coordinates
    offset_x = cover + (phi_mm / 10.0) / 2.0
    offset_y = cover + (phi_mm / 10.0) / 2.0
    w_rebar = max(b_val - 2.0 * offset_x, 1.0)
    h_rebar = max(t_val - 2.0 * offset_y, 1.0)

    ny = max(2, int(n_rows))
    # Estimate columns of bars along width b
    nx = max(2, int(math.ceil((n_bars - 2 * ny + 4) / 2))) if n_bars > 2 * ny else 2

    xs_b = np.linspace(offset_x, b_val - offset_x, nx)
    ys_d = np.linspace(offset_y, t_val - offset_y, ny)

    # Collect perimeter bars
    rebar_coords = []
    for x in xs_b:
        rebar_coords.append((x, offset_y))
        rebar_coords.append((x, t_val - offset_y))
    for y in ys_d[1:-1]:
        rebar_coords.append((offset_x, y))
        rebar_coords.append((b_val - offset_x, y))

    unique_rebars = []
    for pt in rebar_coords:
        if not any(np.isclose(pt[0], u[0], atol=1e-2) and np.isclose(pt[1], u[1], atol=1e-2) for u in unique_rebars):
            unique_rebars.append(pt)

    # If count doesn't match exactly, distribute along perimeter
    if len(unique_rebars) != n_bars and n_bars >= 4:
        # Fallback perimeter distribution
        unique_rebars = []
        unique_rebars.append((offset_x, offset_y))
        unique_rebars.append((b_val - offset_x, offset_y))
        unique_rebars.append((b_val - offset_x, t_val - offset_y))
        unique_rebars.append((offset_x, t_val - offset_y))
        rem = n_bars - 4
        if rem > 0:
            rem_y = min(rem, (ny - 2) * 2)
            rem_x = rem - rem_y
            if rem_y > 0 and ny > 2:
                for y in np.linspace(offset_y, t_val - offset_y, (rem_y // 2) + 2)[1:-1]:
                    unique_rebars.append((offset_x, y))
                    unique_rebars.append((b_val - offset_x, y))
            if rem_x > 0:
                for x in np.linspace(offset_x, b_val - offset_x, (rem_x // 2) + 2)[1:-1]:
                    unique_rebars.append((x, offset_y))
                    unique_rebars.append((x, t_val - offset_y))

    is_auto = "auto" in tie_type.lower() or "أوتوماتيك" in tie_type

    fig, ax = plt.subplots(figsize=(6.8, 6.8), dpi=140, facecolor="#ffffff")
    ax.set_facecolor("#ffffff")


    # 1. Concrete outer section
    col_rect = patches.Rectangle(
        (0, 0), b_val, t_val,
        linewidth=2.8, edgecolor="#0f172a", facecolor="#f1f5f9", zorder=1,
    )
    ax.add_patch(col_rect)

    # 2. Outer stirrup
    st_x, st_y, st_w, st_h = cover, cover, b_core, t_core
    rounding = min(1.5, cover * 0.6)
    stirrup_outer = FancyBboxPatch(
        (st_x, st_y), st_w, st_h,
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        linewidth=2.4, edgecolor="#16a34a", facecolor="none", zorder=3,
    )
    ax.add_patch(stirrup_outer)

    # Outer hook
    ax.plot([st_x, st_x + hook_sz * 0.707], [st_y + st_h, st_y + st_h - hook_sz * 0.707], color="#16a34a", lw=2.4, zorder=4)
    ax.plot([st_x + hook_sz * 0.707, st_x], [st_y + st_h - hook_sz * 0.707, st_y + st_h - hook_sz * 1.15], color="#16a34a", lw=2.4, zorder=4)

    # 3. Inner Stirrup (if Automatic or Multi-Row)
    if is_auto and ny >= 3:
        if ny >= 4 and nx == 2:
            in_y_min = ys_d[1] - (phi_mm / 10.0) / 2.0 - 0.3
            in_y_max = ys_d[-2] + (phi_mm / 10.0) / 2.0 + 0.3
            in_h = max(5.0, in_y_max - in_y_min)
            inner_st = FancyBboxPatch(
                (st_x + 0.5, in_y_min), st_w - 1.0, in_h,
                boxstyle=f"round,pad=0,rounding_size={rounding}",
                linewidth=2.0, edgecolor="#059669", facecolor="#ecfdf5", zorder=3,
            )
            ax.add_patch(inner_st)
            ax.plot([st_x + 0.5, st_x + 0.5 + hook_sz * 0.6], [in_y_min + in_h, in_y_min + in_h - hook_sz * 0.6], color="#059669", lw=2.0, zorder=4)
        elif nx >= 3 and ny >= 3:
            in_x_min = xs_b[1] - (phi_mm / 10.0) / 2.0 - 0.3
            in_x_max = xs_b[-2] + (phi_mm / 10.0) / 2.0 + 0.3
            in_y_min = ys_d[1] - (phi_mm / 10.0) / 2.0 - 0.3
            in_y_max = ys_d[-2] + (phi_mm / 10.0) / 2.0 + 0.3
            inner_st = FancyBboxPatch(
                (in_x_min, in_y_min), max(5.0, in_x_max - in_x_min), max(5.0, in_y_max - in_y_min),
                boxstyle=f"round,pad=0,rounding_size={rounding}",
                linewidth=2.0, edgecolor="#059669", facecolor="#ecfdf5", zorder=3,
            )
            ax.add_patch(inner_st)
        else:
            in_h = st_h * 0.5
            in_y_min = st_y + (st_h - in_h) / 2.0
            inner_st = FancyBboxPatch(
                (st_x + 0.5, in_y_min), st_w - 1.0, in_h,
                boxstyle=f"round,pad=0,rounding_size={rounding}",
                linewidth=2.0, edgecolor="#059669", facecolor="#ecfdf5", zorder=3,
            )
            ax.add_patch(inner_st)

    # 4. Longitudinal rebar circles
    bar_radius = max(1.15, min(2.4, (phi_mm / 10.0) * 0.90))
    for rx, ry in unique_rebars:
        rebar_circle = Circle((rx, ry), radius=bar_radius, facecolor="#dc2626", edgecolor="#7f1d1d", linewidth=1.4, zorder=6)
        ax.add_patch(rebar_circle)

    # 5. Dimensions
    dim_offset = max(6.0, min(b_val, t_val) * 0.16)
    y_dim = -dim_offset
    ax.plot([0, 0], [0, y_dim - 1.0], color="#94a3b8", lw=1.0, linestyle=":")
    ax.plot([b_val, b_val], [0, y_dim - 1.0], color="#94a3b8", lw=1.0, linestyle=":")
    ax.annotate("", xy=(b_val, y_dim), xytext=(0, y_dim), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.5))
    ax.text(b_val / 2.0, y_dim - 1.2, f"b = {b_val:.0f} cm", ha="center", va="top", fontsize=11, weight="bold", color="#0f172a")

    x_dim = -dim_offset
    ax.plot([0, x_dim - 1.0], [0, 0], color="#94a3b8", lw=1.0, linestyle=":")
    ax.plot([0, x_dim - 1.0], [t_val, t_val], color="#94a3b8", lw=1.0, linestyle=":")
    ax.annotate("", xy=(x_dim, t_val), xytext=(x_dim, 0), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.5))
    ax.text(x_dim - 1.2, t_val / 2.0, f"t = {t_val:.0f} cm", ha="right", va="center", rotation=90, fontsize=11, weight="bold", color="#0f172a")

    # Titles & callouts
    top_bar = (b_val - offset_x, t_val - offset_y)
    ax.annotate(
        f"{n_bars} Φ{phi_mm} ({ny} Rows)", xy=top_bar, xytext=(b_val * 0.25, t_val + dim_offset * 1.15),
        arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.5, connectionstyle="arc3,rad=-0.12"),
        fontsize=10.5, weight="bold", color="#991b1b", ha="left", va="bottom",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.2),
    )

    pad_left = dim_offset + 8
    pad_right = max(dim_offset + 12, b_val * 0.35 + 10)
    pad_y_top = dim_offset * 1.15 + 14
    pad_y_bot = dim_offset + 10
    ax.set_xlim(-pad_left, b_val + pad_right)
    ax.set_ylim(-pad_y_bot, t_val + pad_y_top)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(f"1. مسقط أفقي للعمود  |  Cross-Section ({b_val:.0f}×{t_val:.0f} cm)", fontsize=12, weight="bold", pad=8, color="#1e3a8a")

    fig.tight_layout()
    return fig


def draw_column_unified_sheet(
    b_cm: float,
    t_cm: float,
    H_col_cm: float,
    t_slab_cm: float,
    n_bars: int,
    phi_mm: int,
    phi_st_mm: int,
    n_st_per_m: int,
    is_top_floor: bool,
    lap_factor: float = 50.0,
    tie_type: str = "Automatic",
    n_rows: int = 2,
    cover: float = 2.5,
) -> plt.Figure:
    """
    Renders a unified, full-width 3-Panel CAD Drawing Sheet:
      1. Horizontal Cross-Section Plan (المسقط الأفقي وتوزيع الكانات والأسياخ)
      2. Vertical Elevation (القطاع الرأسي وتوزيع الكانات وارتفاع العمود والسقف والوصلات)
      3. Bar Bending Schedule - BBS (تفريد حديد التسليح والكانات بالتفصيل والأطوال والأوزان)
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"]

    b_val = float(b_cm)
    t_val = float(t_cm)
    b_core = max(b_val - 2.0 * cover, 1.0)
    t_core = max(t_val - 2.0 * cover, 1.0)
    hook_len_cm = max(8.0, 10.0 * (phi_st_mm / 10.0))
    is_auto = "auto" in tie_type.lower() or "أوتوماتيك" in tie_type

    if is_auto:
        t_core_in = max(t_core * 0.5, 5.0)
        b_core_in = b_core
        L_tie_cm = 2.0 * (b_core + t_core) + 2.0 * (b_core_in + t_core_in) + 4.0 * hook_len_cm
        tie_title_str = "Automatic Multi-Branch"
    else:
        t_core_in = 0.0
        b_core_in = 0.0
        L_tie_cm = 2.0 * (b_core + t_core) + 2.0 * hook_len_cm
        tie_title_str = "Closed Box Tie"

    L_tie_m = L_tie_cm / 100.0
    n_ties_per_col = max(3, int(math.ceil((H_col_cm / 100.0) * n_st_per_m)))

    L_lap_cm = (lap_factor * phi_mm) / 10.0
    L_hook_cm = max(25.0, (lap_factor * phi_mm) / 10.0)

    if not is_top_floor:
        L_bar_cm = H_col_cm + t_slab_cm + L_lap_cm
    else:
        L_bar_cm = H_col_cm + (t_slab_cm - cover) + L_hook_cm

    L_bar_m = L_bar_cm / 100.0

    # 3-Panel Unified Figure: Plan (left), Elevation (middle), BBS (right)
    fig = plt.figure(figsize=(15.2, 6.2), dpi=140, facecolor="#ffffff")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 1.35], wspace=0.18)

    ax_plan = fig.add_subplot(gs[0, 0])
    ax_elev = fig.add_subplot(gs[0, 1])
    ax_bbs = fig.add_subplot(gs[0, 2])

    # ── PANEL 1: HORIZONTAL CROSS-SECTION PLAN ──
    ax_plan.set_facecolor("#ffffff")
    offset_x = cover + (phi_mm / 10.0) / 2.0
    offset_y = cover + (phi_mm / 10.0) / 2.0
    w_rebar = max(b_val - 2 * offset_x, 1.0)
    h_rebar = max(t_val - 2 * offset_y, 1.0)
    perimeter_rebar = 2 * (w_rebar + h_rebar)
    s_target = perimeter_rebar / n_bars
    nx_est = int(round(w_rebar / s_target)) + 1
    nx = max(2, min(nx_est, n_bars // 2))
    ny = (n_bars // 2 + 2) - nx
    if ny < 2:
        ny = 2
        nx = (n_bars // 2 + 2) - ny

    xs_b = np.linspace(offset_x, b_val - offset_x, nx)
    ys_d = np.linspace(offset_y, t_val - offset_y, ny)

    rebar_coords = []
    for x in xs_b:
        rebar_coords.append((x, offset_y))
        rebar_coords.append((x, t_val - offset_y))
    for y in ys_d[1:-1]:
        rebar_coords.append((offset_x, y))
        rebar_coords.append((b_val - offset_x, y))

    unique_rebars = []
    for pt in rebar_coords:
        if not any(np.isclose(pt[0], u[0], atol=1e-2) and np.isclose(pt[1], u[1], atol=1e-2) for u in unique_rebars):
            unique_rebars.append(pt)

    col_rect = patches.Rectangle((0, 0), b_val, t_val, linewidth=2.4, edgecolor="#0f172a", facecolor="#f1f5f9", zorder=1)
    ax_plan.add_patch(col_rect)

    rounding = min(1.5, cover * 0.6)
    hook_sz = max(4.0, (phi_st_mm / 10.0) * 8.0)
    stirrup_outer = FancyBboxPatch((cover, cover), b_core, t_core, boxstyle=f"round,pad=0,rounding_size={rounding}", linewidth=2.2, edgecolor="#16a34a", facecolor="none", zorder=3)
    ax_plan.add_patch(stirrup_outer)
    ax_plan.plot([cover, cover + hook_sz * 0.707], [cover + t_core, cover + t_core - hook_sz * 0.707], color="#16a34a", lw=2.2, zorder=4)
    ax_plan.plot([cover + hook_sz * 0.707, cover], [cover + t_core - hook_sz * 0.707, cover + t_core - hook_sz * 1.15], color="#16a34a", lw=2.2, zorder=4)

    if is_auto and ny >= 3:
        in_y_min = ys_d[1] - (phi_mm / 10.0) / 2.0 - 0.3
        in_y_max = ys_d[-2] + (phi_mm / 10.0) / 2.0 + 0.3
        in_h = max(5.0, in_y_max - in_y_min)
        inner_st = FancyBboxPatch((cover + 0.5, in_y_min), b_core - 1.0, in_h, boxstyle=f"round,pad=0,rounding_size={rounding}", linewidth=1.8, edgecolor="#059669", facecolor="#ecfdf5", zorder=3)
        ax_plan.add_patch(inner_st)
        ax_plan.plot([cover + 0.5, cover + 0.5 + hook_sz * 0.6], [in_y_min + in_h, in_y_min + in_h - hook_sz * 0.6], color="#059669", lw=1.8, zorder=4)

    bar_radius = max(1.15, min(2.4, (phi_mm / 10.0) * 0.90))
    for rx, ry in unique_rebars:
        rebar_circle = Circle((rx, ry), radius=bar_radius, facecolor="#dc2626", edgecolor="#7f1d1d", linewidth=1.4, zorder=6)
        ax_plan.add_patch(rebar_circle)

    dim_off = 6.5
    ax_plan.plot([0, 0], [0, -dim_off], color="#94a3b8", lw=1.0, linestyle=":")
    ax_plan.plot([b_val, b_val], [0, -dim_off], color="#94a3b8", lw=1.0, linestyle=":")
    ax_plan.annotate("", xy=(b_val, -dim_off), xytext=(0, -dim_off), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
    ax_plan.text(b_val / 2.0, -dim_off - 1.2, f"b = {b_val:.0f} cm", ha="center", va="top", fontsize=10.5, weight="bold", color="#0f172a")

    ax_plan.plot([0, -dim_off], [0, 0], color="#94a3b8", lw=1.0, linestyle=":")
    ax_plan.plot([0, -dim_off], [t_val, t_val], color="#94a3b8", lw=1.0, linestyle=":")
    ax_plan.annotate("", xy=(-dim_off, t_val), xytext=(-dim_off, 0), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
    ax_plan.text(-dim_off - 1.2, t_val / 2.0, f"t = {t_val:.0f} cm", ha="right", va="center", rotation=90, fontsize=10.5, weight="bold", color="#0f172a")

    top_bar = (b_val - offset_x, t_val - offset_y)
    ax_plan.annotate(
        f"{n_bars} Φ{phi_mm} ({ny} Rows)", xy=top_bar, xytext=(b_val * 0.15, t_val + dim_off * 1.1),
        arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.4, connectionstyle="arc3,rad=-0.1"),
        fontsize=9.5, weight="bold", color="#991b1b", ha="left", va="bottom",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.0),
    )

    ax_plan.set_xlim(-dim_off - 8, b_val + dim_off + 10)
    ax_plan.set_ylim(-dim_off - 8, t_val + dim_off + 12)
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.axis("off")
    ax_plan.set_title("1. مسقط أفقي للعمود  |  Cross-Section", fontsize=11.0, weight="bold", color="#1e3a8a", pad=8)

    # ── PANEL 2: VERTICAL ELEVATION ──
    ax_elev.set_facecolor("#ffffff")
    y_bot = 0.4
    y_col_top = 2.8
    y_slab_top = 3.35
    y_lap_top = 4.15 if not is_top_floor else 3.35

    x_left = 0.95
    x_right = 2.15
    col_w_draw = x_right - x_left

    ax_elev.plot([0.2, 2.9], [y_bot, y_bot], color="#334155", lw=2.4, linestyle="-")
    ax_elev.fill_between([0.2, 2.9], [y_bot - 0.22, y_bot - 0.22], [y_bot, y_bot], color="#e2e8f0", hatch="//")

    col_rect_elev = patches.Rectangle((x_left, y_bot), col_w_draw, y_col_top - y_bot, facecolor="#f8fafc", edgecolor="#0f172a", linewidth=2.4, zorder=2)
    ax_elev.add_patch(col_rect_elev)

    slab_rect = patches.Rectangle((0.2, y_col_top), 2.7, y_slab_top - y_col_top, facecolor="#e2e8f0", edgecolor="#334155", linewidth=2.0, zorder=2)
    ax_elev.add_patch(slab_rect)
    ax_elev.text(2.25, (y_col_top + y_slab_top) / 2.0, f"ts = {t_slab_cm:.0f} cm", ha="left", va="center", fontsize=9.0, weight="bold", color="#1e293b")

    bar_off = 0.16
    bx_left = x_left + bar_off
    bx_right = x_right - bar_off

    ax_elev.plot([bx_left, bx_left], [y_bot, y_slab_top], color="#dc2626", lw=2.8, zorder=4)
    ax_elev.plot([bx_left, bx_left + 0.20], [y_bot, y_bot], color="#dc2626", lw=2.8, zorder=4)
    ax_elev.plot([bx_right, bx_right], [y_bot, y_slab_top], color="#dc2626", lw=2.8, zorder=4)
    ax_elev.plot([bx_right, bx_right - 0.20], [y_bot, y_bot], color="#dc2626", lw=2.8, zorder=4)

    if not is_top_floor:
        ax_elev.plot([bx_left, bx_left + 0.06], [y_slab_top, y_slab_top + 0.08], color="#dc2626", lw=2.8, zorder=4)
        ax_elev.plot([bx_left + 0.06, bx_left + 0.06], [y_slab_top + 0.08, y_lap_top], color="#dc2626", lw=2.8, zorder=4)
        ax_elev.plot([bx_right, bx_right - 0.06], [y_slab_top, y_slab_top + 0.08], color="#dc2626", lw=2.8, zorder=4)
        ax_elev.plot([bx_right - 0.06, bx_right - 0.06], [y_slab_top + 0.08, y_lap_top], color="#dc2626", lw=2.8, zorder=4)

        ax_elev.annotate("", xy=(2.45, y_lap_top), xytext=(2.45, y_slab_top), arrowprops=dict(arrowstyle="<->", color="#b91c1c", lw=1.4))
        ax_elev.text(2.52, (y_slab_top + y_lap_top) / 2.0, f"L_lap = {L_lap_cm:.0f} cm\n({lap_factor:.0f}Φ)", ha="left", va="center", fontsize=8.5, weight="bold", color="#b91c1c")
    else:
        hook_len_draw = 0.45
        ax_elev.plot([bx_left, bx_left + hook_len_draw], [y_slab_top - 0.06, y_slab_top - 0.06], color="#dc2626", lw=2.8, zorder=4)
        ax_elev.plot([bx_right, bx_right - hook_len_draw], [y_slab_top - 0.06, y_slab_top - 0.06], color="#dc2626", lw=2.8, zorder=4)
        ax_elev.text(bx_left + 0.22, y_slab_top - 0.15, f"Top Hook\n{L_hook_cm:.0f} cm", ha="center", va="top", fontsize=8.0, weight="bold", color="#b91c1c")

    tie_ys = np.linspace(y_bot + 0.16, y_col_top - 0.10, 8)
    for ty in tie_ys:
        ax_elev.plot([bx_left, bx_right], [ty, ty], color="#16a34a", lw=1.8, zorder=3)

    mid_tie_y = tie_ys[4]
    ax_elev.annotate(
        f"{n_st_per_m}Φ{phi_st_mm}/m'", xy=(bx_right, mid_tie_y), xytext=(2.30, mid_tie_y),
        arrowprops=dict(arrowstyle="->", color="#16a34a", lw=1.2),
        fontsize=9.0, weight="bold", color="#15803d", ha="left", va="center",
    )

    dim_x = 0.55
    ax_elev.annotate("", xy=(dim_x, y_col_top), xytext=(dim_x, y_bot), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
    ax_elev.text(dim_x - 0.08, (y_bot + y_col_top) / 2.0, f"H = {H_col_cm:.0f} cm", ha="right", va="center", rotation=90, fontsize=10.5, weight="bold", color="#0f172a")

    ax_elev.set_xlim(0.0, 3.6)
    ax_elev.set_ylim(0.0, 4.45)
    ax_elev.axis("off")
    ax_elev.set_title("2. قطاع رأسي للعمود  |  Vertical Elevation", fontsize=11.0, weight="bold", color="#1e3a8a", pad=8)

    # ── PANEL 3: REBAR & STIRRUPS BBS DETAILING ──
    ax_bbs.set_facecolor("#ffffff")
    ax_bbs.set_xlim(0, 1)
    ax_bbs.set_ylim(0, 1)
    ax_bbs.axis("off")

    bbs_bg = FancyBboxPatch((0.01, 0.01), 0.98, 0.98, boxstyle="round,pad=0.015,rounding_size=0.03", linewidth=1.5, edgecolor="#cbd5e1", facecolor="#f8fafc", zorder=1)
    ax_bbs.add_patch(bbs_bg)

    # Header Ribbon
    header_box = FancyBboxPatch((0.03, 0.915), 0.94, 0.065, boxstyle="round,pad=0.01,rounding_size=0.02", linewidth=1.0, edgecolor="#bfdbfe", facecolor="#eff6ff", zorder=2)
    ax_bbs.add_patch(header_box)
    ax_bbs.text(0.50, 0.947, "Rebar Detailing & BBS  |  تفريد حديد التسليح", ha="center", va="center", fontsize=11.0, weight="bold", color="#1e3a8a", zorder=3)

    # Part A: Main Rebar
    sub_bg1 = FancyBboxPatch((0.02, 0.51), 0.96, 0.395, boxstyle="round,pad=0.012,rounding_size=0.02", linewidth=1.2, edgecolor="#fecaca", facecolor="#ffffff", zorder=2)
    ax_bbs.add_patch(sub_bg1)
    ax_bbs.text(0.05, 0.865, "A. Main Rebar Detailing  |  تفريد الحديد الرئيسي", fontsize=10.2, weight="bold", color="#991b1b", zorder=3)

    rx = 0.10
    y_m_bot = 0.55
    y_m_col = 0.71
    y_m_top = 0.81
    ax_bbs.plot([rx, rx], [y_m_bot, y_m_col], color="#dc2626", lw=3.2, zorder=4)
    ax_bbs.plot([rx, rx - 0.035], [y_m_bot, y_m_bot], color="#dc2626", lw=3.2, zorder=4)
    if not is_top_floor:
        ax_bbs.plot([rx, rx + 0.018], [y_m_col, y_m_col + 0.018], color="#dc2626", lw=3.2, zorder=4)
        ax_bbs.plot([rx + 0.018, rx + 0.018], [y_m_col + 0.018, y_m_top], color="#dc2626", lw=3.2, zorder=4)
    else:
        ax_bbs.plot([rx, rx + 0.05], [y_m_col, y_m_col], color="#dc2626", lw=3.2, zorder=4)

    ax_bbs.text(rx - 0.045, (y_m_bot + y_m_col) / 2.0, f"H={H_col_cm:.0f} cm", ha="right", va="center", fontsize=8.0, color="#64748b", rotation=90)

    tx = 0.20
    ax_bbs.text(tx, 0.79, f"• Main Bars:  {n_bars} Φ {phi_mm} mm  [{n_rows} Rows]", fontsize=9.5, weight="bold", color="#1e293b", zorder=3)
    ax_bbs.text(tx, 0.71, f"• Cut Length (L_bar):  {L_bar_m:.2f} m ({L_bar_cm:.0f} cm)", fontsize=9.8, weight="bold", color="#b91c1c", zorder=3)
    splice_txt = f"L_lap = {L_lap_cm:.0f} cm [{lap_factor:.0f}Φ]" if not is_top_floor else f"Top Hook = {L_hook_cm:.0f} cm"
    ax_bbs.text(tx, 0.63, f"• Splice / Hook:  {splice_txt}", fontsize=8.8, color="#334155", zorder=3)
    ax_bbs.text(tx, 0.55, f"• Formula:  L = H ({H_col_cm:.0f}) + ts ({t_slab_cm:.0f}) + Lap ({L_lap_cm if not is_top_floor else L_hook_cm:.0f} cm)", fontsize=8.2, color="#64748b", zorder=3)

    # Part B: Stirrup Tie
    sub_bg2 = FancyBboxPatch((0.02, 0.025), 0.96, 0.465, boxstyle="round,pad=0.012,rounding_size=0.02", linewidth=1.2, edgecolor="#bbf7d0", facecolor="#ffffff", zorder=2)
    ax_bbs.add_patch(sub_bg2)
    ax_bbs.text(0.05, 0.450, "B. Stirrup Detailing  |  تفريد الكانات", fontsize=10.2, weight="bold", color="#15803d", zorder=3)

    sx, sy, sw, sh = 0.07, 0.08, 0.22, 0.32
    st_outer = FancyBboxPatch((sx, sy), sw, sh, boxstyle="round,pad=0,rounding_size=0.015", linewidth=2.2, edgecolor="#16a34a", facecolor="#f0fdf4", zorder=4)
    ax_bbs.add_patch(st_outer)
    ax_bbs.plot([sx, sx + 0.028], [sy + sh, sy + sh - 0.028], color="#15803d", lw=2.2, zorder=5)
    ax_bbs.plot([sx + 0.028, sx], [sy + sh - 0.028, sy + sh - 0.048], color="#15803d", lw=2.2, zorder=5)

    if is_auto:
        sh_in = sh * 0.52
        sy_in = sy + (sh - sh_in) / 2.0
        st_inner = FancyBboxPatch((sx + 0.02, sy_in), sw - 0.04, sh_in, boxstyle="round,pad=0,rounding_size=0.012", linewidth=1.8, edgecolor="#059669", facecolor="#dcfce7", zorder=5)
        ax_bbs.add_patch(st_inner)
        ax_bbs.plot([sx + 0.02, sx + 0.02 + 0.022], [sy_in + sh_in, sy_in + sh_in - 0.022], color="#059669", lw=1.8, zorder=6)
        ax_bbs.plot([sx + 0.02 + 0.022, sx + 0.02], [sy_in + sh_in - 0.02, sy_in + sh_in - 0.040], color="#059669", lw=1.8, zorder=6)

    ax_bbs.text(sx + sw / 2, sy - 0.022, f"b' = {b_core:.0f} cm", ha="center", va="top", fontsize=8.2, weight="bold", color="#166534")
    ax_bbs.text(sx + sw + 0.015, sy + sh / 2, f"t' = {t_core:.0f} cm", ha="left", va="center", fontsize=8.2, weight="bold", color="#166534", rotation=90)

    st_tx = 0.36
    ax_bbs.text(st_tx, 0.385, f"• Tie Type:  {tie_title_str}", fontsize=9.2, weight="bold", color="#1e293b", zorder=3)
    ax_bbs.text(st_tx, 0.315, f"• Cut Length (L_tie):  {L_tie_m:.2f} m ({L_tie_cm:.0f} cm)", fontsize=9.8, weight="bold", color="#15803d", zorder=3)
    ax_bbs.text(st_tx, 0.245, f"• Size & Spacing:  Φ {phi_st_mm} mm @ {n_st_per_m} / m' (S={100.0/n_st_per_m:.0f} cm)", fontsize=8.8, color="#1e293b", zorder=3)
    ax_bbs.text(st_tx, 0.175, f"• Dimensions:  {b_core:.0f} × {t_core:.0f} cm  (Hook: {hook_len_cm:.0f} cm)", fontsize=8.5, color="#334155", zorder=3)
    ax_bbs.text(st_tx, 0.105, f"• Total Ties / Col:  {n_ties_per_col} Ties / Column", fontsize=9.0, weight="bold", color="#1e293b", zorder=3)
    ax_bbs.text(st_tx, 0.045, f"• Total Length:  {n_ties_per_col * L_tie_m:.1f} m' per column", fontsize=8.2, color="#64748b", zorder=3)

    return fig


def draw_column_vertical_elevation(
    H_col_cm: float,
    t_slab_cm: float,
    b_cm: float,
    t_cm: float,
    n_bars: int,
    phi_mm: int,
    phi_st_mm: int,
    n_st_per_m: int,
    is_top_floor: bool,
    lap_factor: float = 50.0,
    tie_type: str = "Automatic",
    n_rows: int = 2,
    cover: float = 2.5,
) -> plt.Figure:

    """
    Renders the vertical cross-section / elevation of the column along with
    complete Rebar Detailing (BBS) for BOTH Main Rebar and Stirrups:
    - Clear column height (H_col)
    - Top slab/beam zone (t_slab)
    - Main longitudinal bars (with Lap length Llap or Top Hook Lhook)
    - Stirrup distribution along height
    - Detailed Stirrup Detailing (تفريد حديد الكانة: Outer + Inner loops & hooks)
    - Detailed Main Rebar Detailing (تفريد الحديد الرئيسي)
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"]

    b_val = float(b_cm)
    t_val = float(t_cm)
    b_core = max(b_val - 2.0 * cover, 1.0)
    t_core = max(t_val - 2.0 * cover, 1.0)
    hook_len_cm = max(8.0, 10.0 * (phi_st_mm / 10.0))

    is_auto = "auto" in tie_type.lower() or "أوتوماتيك" in tie_type

    if is_auto:
        t_core_in = max(t_core * 0.5, 5.0)
        b_core_in = b_core
        L_tie_cm = 2.0 * (b_core + t_core) + 2.0 * (b_core_in + t_core_in) + 4.0 * hook_len_cm
        tie_title_str = "Automatic Multi-Branch (كانة أوتوماتيك)"
    else:
        t_core_in = 0.0
        b_core_in = 0.0
        L_tie_cm = 2.0 * (b_core + t_core) + 2.0 * hook_len_cm
        tie_title_str = "Closed Box Tie (كانة صندوقية)"

    L_tie_m = L_tie_cm / 100.0
    n_ties_per_col = max(3, int(math.ceil((H_col_cm / 100.0) * n_st_per_m)))

    L_lap_cm = (lap_factor * phi_mm) / 10.0
    L_hook_cm = max(25.0, (lap_factor * phi_mm) / 10.0)

    if not is_top_floor:
        L_bar_cm = H_col_cm + t_slab_cm + L_lap_cm
    else:
        L_bar_cm = H_col_cm + (t_slab_cm - cover) + L_hook_cm

    L_bar_m = L_bar_cm / 100.0

    fig, (ax, ax_bbs) = plt.subplots(
        1, 2, figsize=(9.6, 6.8), dpi=140,
        gridspec_kw={"width_ratios": [1.0, 1.35]}, facecolor="#ffffff"
    )

    # ═══════════════════════════════════════════════════════════════════════
    # 1. LEFT SUBPLOT: COLUMN ELEVATION
    # ═══════════════════════════════════════════════════════════════════════
    ax.set_facecolor("#ffffff")
    y_bot = 0.4
    y_col_top = 2.8
    y_slab_top = 3.35
    y_lap_top = 4.15 if not is_top_floor else 3.35

    x_left = 0.95
    x_right = 2.15
    col_w_draw = x_right - x_left

    # Foundation / lower floor level
    ax.plot([0.2, 2.9], [y_bot, y_bot], color="#334155", lw=2.4, linestyle="-")
    ax.fill_between([0.2, 2.9], [y_bot - 0.22, y_bot - 0.22], [y_bot, y_bot], color="#e2e8f0", hatch="//")

    # Column concrete body
    col_rect = patches.Rectangle(
        (x_left, y_bot), col_w_draw, y_col_top - y_bot,
        facecolor="#f8fafc", edgecolor="#0f172a", linewidth=2.4, zorder=2,
    )
    ax.add_patch(col_rect)

    # Upper Slab / Beam zone
    slab_rect = patches.Rectangle(
        (0.2, y_col_top), 2.7, y_slab_top - y_col_top,
        facecolor="#e2e8f0", edgecolor="#334155", linewidth=2.0, zorder=2,
    )
    ax.add_patch(slab_rect)
    ax.text(2.25, (y_col_top + y_slab_top) / 2.0, f"ts = {t_slab_cm:.0f} cm", ha="left", va="center", fontsize=9.0, weight="bold", color="#1e293b")

    # Main Rebars
    bar_off = 0.16
    bx_left = x_left + bar_off
    bx_right = x_right - bar_off

    ax.plot([bx_left, bx_left], [y_bot, y_slab_top], color="#dc2626", lw=2.8, zorder=4)
    ax.plot([bx_left, bx_left + 0.20], [y_bot, y_bot], color="#dc2626", lw=2.8, zorder=4)
    ax.plot([bx_right, bx_right], [y_bot, y_slab_top], color="#dc2626", lw=2.8, zorder=4)
    ax.plot([bx_right, bx_right - 0.20], [y_bot, y_bot], color="#dc2626", lw=2.8, zorder=4)

    if not is_top_floor:
        ax.plot([bx_left, bx_left + 0.06], [y_slab_top, y_slab_top + 0.08], color="#dc2626", lw=2.8, zorder=4)
        ax.plot([bx_left + 0.06, bx_left + 0.06], [y_slab_top + 0.08, y_lap_top], color="#dc2626", lw=2.8, zorder=4)
        ax.plot([bx_right, bx_right - 0.06], [y_slab_top, y_slab_top + 0.08], color="#dc2626", lw=2.8, zorder=4)
        ax.plot([bx_right - 0.06, bx_right - 0.06], [y_slab_top + 0.08, y_lap_top], color="#dc2626", lw=2.8, zorder=4)

        ax.annotate("", xy=(2.45, y_lap_top), xytext=(2.45, y_slab_top), arrowprops=dict(arrowstyle="<->", color="#b91c1c", lw=1.4))
        ax.text(2.52, (y_slab_top + y_lap_top) / 2.0, f"L_lap = {L_lap_cm:.0f} cm\n({lap_factor:.0f}Φ)", ha="left", va="center", fontsize=8.5, weight="bold", color="#b91c1c")
    else:
        hook_len_draw = 0.45
        ax.plot([bx_left, bx_left + hook_len_draw], [y_slab_top - 0.06, y_slab_top - 0.06], color="#dc2626", lw=2.8, zorder=4)
        ax.plot([bx_right, bx_right - hook_len_draw], [y_slab_top - 0.06, y_slab_top - 0.06], color="#dc2626", lw=2.8, zorder=4)
        ax.text(bx_left + 0.22, y_slab_top - 0.15, f"Top Hook\n{L_hook_cm:.0f} cm", ha="center", va="top", fontsize=8.0, weight="bold", color="#b91c1c")

    # Stirrups distribution
    n_ties_draw = 8
    tie_ys = np.linspace(y_bot + 0.16, y_col_top - 0.10, n_ties_draw)
    for ty in tie_ys:
        ax.plot([bx_left, bx_right], [ty, ty], color="#16a34a", lw=1.8, zorder=3)

    mid_tie_y = tie_ys[n_ties_draw // 2]
    ax.annotate(
        f"{n_st_per_m}Φ{phi_st_mm}/m'", xy=(bx_right, mid_tie_y), xytext=(2.30, mid_tie_y),
        arrowprops=dict(arrowstyle="->", color="#16a34a", lw=1.2),
        fontsize=9.0, weight="bold", color="#15803d", ha="left", va="center",
    )

    # Column height dimension arrow
    dim_x = 0.55
    ax.annotate("", xy=(dim_x, y_col_top), xytext=(dim_x, y_bot), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
    ax.text(dim_x - 0.08, (y_bot + y_col_top) / 2.0, f"H = {H_col_cm:.0f} cm", ha="right", va="center", rotation=90, fontsize=10.5, weight="bold", color="#0f172a")

    ax.set_xlim(0.0, 3.6)
    ax.set_ylim(0.0, 4.45)
    ax.axis("off")
    ax.set_title("2. قطاع رأسي للعمود  |  Vertical Elevation", fontsize=11.0, weight="bold", color="#1e3a8a", pad=8)

    # ═══════════════════════════════════════════════════════════════════════
    # 2. RIGHT SUBPLOT: STRUCTURED CAD REBAR & STIRRUP BBS DETAILING
    # ═══════════════════════════════════════════════════════════════════════
    ax_bbs.set_facecolor("#ffffff")
    ax_bbs.set_xlim(0, 1)
    ax_bbs.set_ylim(0, 1)
    ax_bbs.axis("off")

    # Outer Card
    bbs_bg = FancyBboxPatch((0.01, 0.01), 0.98, 0.98, boxstyle="round,pad=0.015,rounding_size=0.03", linewidth=1.5, edgecolor="#cbd5e1", facecolor="#f8fafc", zorder=1)
    ax_bbs.add_patch(bbs_bg)

    # Header Ribbon
    header_box = FancyBboxPatch((0.03, 0.915), 0.94, 0.065, boxstyle="round,pad=0.01,rounding_size=0.02", linewidth=1.0, edgecolor="#bfdbfe", facecolor="#eff6ff", zorder=2)
    ax_bbs.add_patch(header_box)
    ax_bbs.text(0.50, 0.947, "Rebar Detailing & BBS  |  تفريد حديد التسليح", ha="center", va="center", fontsize=11.0, weight="bold", color="#1e3a8a", zorder=3)

    # ── PART A: MAIN REBAR BBS CARD ──
    sub_bg1 = FancyBboxPatch((0.02, 0.51), 0.96, 0.395, boxstyle="round,pad=0.012,rounding_size=0.02", linewidth=1.2, edgecolor="#fecaca", facecolor="#ffffff", zorder=2)
    ax_bbs.add_patch(sub_bg1)
    ax_bbs.text(0.05, 0.865, "A. Main Rebar Detailing  |  تفريد الحديد الرئيسي", fontsize=10.2, weight="bold", color="#991b1b", zorder=3)

    # Sketch Main Bar
    rx = 0.10
    y_m_bot = 0.55
    y_m_col = 0.71
    y_m_top = 0.81
    ax_bbs.plot([rx, rx], [y_m_bot, y_m_col], color="#dc2626", lw=3.2, zorder=4)
    ax_bbs.plot([rx, rx - 0.035], [y_m_bot, y_m_bot], color="#dc2626", lw=3.2, zorder=4)
    if not is_top_floor:
        ax_bbs.plot([rx, rx + 0.018], [y_m_col, y_m_col + 0.018], color="#dc2626", lw=3.2, zorder=4)
        ax_bbs.plot([rx + 0.018, rx + 0.018], [y_m_col + 0.018, y_m_top], color="#dc2626", lw=3.2, zorder=4)
    else:
        ax_bbs.plot([rx, rx + 0.05], [y_m_col, y_m_col], color="#dc2626", lw=3.2, zorder=4)

    # Dimension ticks on rebar
    ax_bbs.text(rx - 0.045, (y_m_bot + y_m_col) / 2.0, f"H={H_col_cm:.0f} cm", ha="right", va="center", fontsize=8.0, color="#64748b", rotation=90)

    # Structured Text Rows - Part A
    tx = 0.20
    ax_bbs.text(tx, 0.79, f"• Main Bars:  {n_bars} Φ {phi_mm} mm  [{n_rows} Rows]", fontsize=9.5, weight="bold", color="#1e293b", zorder=3)
    ax_bbs.text(tx, 0.71, f"• Cut Length (L_bar):  {L_bar_m:.2f} m ({L_bar_cm:.0f} cm)", fontsize=9.8, weight="bold", color="#b91c1c", zorder=3)
    splice_txt = f"L_lap = {L_lap_cm:.0f} cm [{lap_factor:.0f}Φ]" if not is_top_floor else f"Top Hook = {L_hook_cm:.0f} cm"
    ax_bbs.text(tx, 0.63, f"• Splice / Hook:  {splice_txt}", fontsize=8.8, color="#334155", zorder=3)
    ax_bbs.text(tx, 0.55, f"• Formula:  L = H ({H_col_cm:.0f}) + ts ({t_slab_cm:.0f}) + Lap ({L_lap_cm if not is_top_floor else L_hook_cm:.0f} cm)", fontsize=8.2, color="#64748b", zorder=3)

    # ── PART B: STIRRUP TIE BBS CARD ──
    sub_bg2 = FancyBboxPatch((0.02, 0.025), 0.96, 0.465, boxstyle="round,pad=0.012,rounding_size=0.02", linewidth=1.2, edgecolor="#bbf7d0", facecolor="#ffffff", zorder=2)
    ax_bbs.add_patch(sub_bg2)
    ax_bbs.text(0.05, 0.450, "B. Stirrup Detailing  |  تفريد الكانات", fontsize=10.2, weight="bold", color="#15803d", zorder=3)

    # Draw Stirrup Loop (Left side of Part B)
    sx, sy, sw, sh = 0.07, 0.08, 0.22, 0.32
    st_outer = FancyBboxPatch((sx, sy), sw, sh, boxstyle="round,pad=0,rounding_size=0.015", linewidth=2.2, edgecolor="#16a34a", facecolor="#f0fdf4", zorder=4)
    ax_bbs.add_patch(st_outer)
    ax_bbs.plot([sx, sx + 0.028], [sy + sh, sy + sh - 0.028], color="#15803d", lw=2.2, zorder=5)
    ax_bbs.plot([sx + 0.028, sx], [sy + sh - 0.028, sy + sh - 0.048], color="#15803d", lw=2.2, zorder=5)

    if is_auto:
        sh_in = sh * 0.52
        sy_in = sy + (sh - sh_in) / 2.0
        st_inner = FancyBboxPatch((sx + 0.02, sy_in), sw - 0.04, sh_in, boxstyle="round,pad=0,rounding_size=0.012", linewidth=1.8, edgecolor="#059669", facecolor="#dcfce7", zorder=5)
        ax_bbs.add_patch(st_inner)
        ax_bbs.plot([sx + 0.02, sx + 0.02 + 0.022], [sy_in + sh_in, sy_in + sh_in - 0.022], color="#059669", lw=1.8, zorder=6)
        ax_bbs.plot([sx + 0.02 + 0.022, sx + 0.02], [sy_in + sh_in - 0.022, sy_in + sh_in - 0.040], color="#059669", lw=1.8, zorder=6)

    # Stirrup dimension labels
    ax_bbs.text(sx + sw / 2, sy - 0.022, f"b' = {b_core:.0f} cm", ha="center", va="top", fontsize=8.2, weight="bold", color="#166534")
    ax_bbs.text(sx + sw + 0.015, sy + sh / 2, f"t' = {t_core:.0f} cm", ha="left", va="center", fontsize=8.2, weight="bold", color="#166534", rotation=90)

    # Stirrup Text Block (Fills Middle and Right Side to Bottom-Right Corner)
    st_tx = 0.36
    ax_bbs.text(st_tx, 0.385, f"• Tie Type:  {tie_title_str}", fontsize=9.2, weight="bold", color="#1e293b", zorder=3)
    ax_bbs.text(st_tx, 0.315, f"• Cut Length (L_tie):  {L_tie_m:.2f} m ({L_tie_cm:.0f} cm)", fontsize=9.8, weight="bold", color="#15803d", zorder=3)
    ax_bbs.text(st_tx, 0.245, f"• Size & Spacing:  Φ {phi_st_mm} mm @ {n_st_per_m} / m' (S={100.0/n_st_per_m:.0f} cm)", fontsize=8.8, color="#1e293b", zorder=3)
    ax_bbs.text(st_tx, 0.175, f"• Dimensions:  {b_core:.0f} × {t_core:.0f} cm  (Hook: {hook_len_cm:.0f} cm)", fontsize=8.5, color="#334155", zorder=3)
    ax_bbs.text(st_tx, 0.105, f"• Total Ties / Col:  {n_ties_per_col} Ties / Column", fontsize=9.0, weight="bold", color="#1e293b", zorder=3)
    ax_bbs.text(st_tx, 0.045, f"• Total Length:  {n_ties_per_col * L_tie_m:.1f} m' per column", fontsize=8.2, color="#64748b", zorder=3)

    fig.tight_layout()
    return fig





# ═══════════════════════════════════════════════════════════════════════════
# 2. MAIN RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def render() -> None:
    st.markdown(
        "<h2 style='color:#1e3a8a; margin-bottom:4px;'>"
        "📊 حصر الخرسانات — Concrete Qty. Survey"
        "</h2>"
        "<p style='color:#64748b; font-size:13px; margin-top:0;'>"
        "حساب حجوم العناصر الخرسانية وتقدير كميات مواد الخلطة وحديد التسليح (ECP 203)"
        "</p>",
        unsafe_allow_html=True,
    )

    tab_customs, tab_quick, tab_table, tab_materials = st.tabs([
        "🏛️ Customs — Concrete Columns Survey",
        "🧱 حصر العناصر الإنشائية  |  Elements Survey",
        "📋 جدول حصر مخصص  |  Custom Takeoff Table",
        "🧪 تقدير مواد الخلطة  |  Mix Materials Estimator",
    ])

    # ────────────────────────────────────────────────────────────────────────
    # TAB 1 — CUSTOMS: CONCRETE COLUMNS QUANTITY SURVEY
    # ────────────────────────────────────────────────────────────────────────
    with tab_customs:
        st.markdown("## 🏛️ Concrete columns quantity survey (حصر أعمدة خرسانية)")
        st.caption("أدخل بيانات قطاع العمود وارتفاعه وتخانة البلاطة لحساب أطوال الأسياخ وأوزان الحديد وحجم الخرسانة مع المساقط الهندسية.")

        cover_cm = 2.5

        # Framed Inputs Container (برواز بلون هندسي مميز ومتقن للمدخلات)
        with st.container(border=True):
            st.markdown(
                """
                <style>
                /* Distinctive Custom Colored Frame for Inputs */
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge) {
                    border: 2.5px solid #2563eb !important;
                    border-radius: 14px !important;
                    background: linear-gradient(180deg, #ffffff 0%, #f8faff 100%) !important;
                    padding: 20px 22px !important;
                    box-shadow: 0 6px 20px rgba(37, 99, 235, 0.12) !important;
                }
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge):hover {
                    border-color: #1d4ed8 !important;
                    box-shadow: 0 8px 26px rgba(37, 99, 235, 0.18) !important;
                }
                /* Increase label font size by 1.25x (عناوين المدخلات) */
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge) label p {
                    font-size: 1.15rem !important;
                    font-weight: 700 !important;
                    color: #0f172a !important;
                    line-height: 1.35 !important;
                }
                /* Increase input values/numbers font size by 1.25x (قيم المدخلات) */
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge) input {
                    font-size: 1.22rem !important;
                    font-weight: 800 !important;
                    color: #1e3a8a !important;
                    padding: 8px 12px !important;
                }
                /* Increase selectbox and radio text font size by 1.25x */
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge) div[data-baseweb="select"] span {
                    font-size: 1.18rem !important;
                    font-weight: 700 !important;
                }
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge) div[data-testid="stRadio"] label p {
                    font-size: 1.15rem !important;
                    font-weight: 700 !important;
                }
                </style>
                <div class="cs-inputs-header-badge" style="
                    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
                    color: #ffffff;
                    padding: 14px 22px;
                    border-radius: 10px;
                    font-weight: 800;
                    font-size: 22px;
                    margin-bottom: 18px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.22);
                    border-left: 6px solid #60a5fa;
                ">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span style="font-size:26px;">📥</span>
                        <span>مدخلات قطاع وتسليح العمود الخرساني (Column Geometry & Reinforcement Inputs)</span>
                    </div>
                    <span style="background: rgba(255,255,255,0.22); color:#ffffff; padding: 5px 14px; border-radius: 20px; font-size: 15px; font-weight: 700; border: 1px solid rgba(255,255,255,0.35);">
                        الكود المصري ECP 203
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Row 1: Dimensions & Count
            col_in1, col_in2, col_in3, col_in4, col_in5 = st.columns(5)



            with col_in1:
                t_slab_in = st.number_input(
                    "تخانة البلاطة والكمرات (cm)",
                    min_value=5.0, max_value=200.0, value=20.0, step=1.0,
                    help="تخانة البلاطة أو سقوط الكمرة أعلى العمود الخرساني (Default 20 cm)",
                    key="cs_t_slab",
                )
            with col_in2:
                col_b_in = st.number_input(
                    "عرض العمود b (cm)",
                    min_value=15.0, max_value=300.0, value=30.0, step=5.0,
                    help="عرض قطاع العمود الخرساني (Default 30 cm)",
                    key="cs_col_b",
                )
            with col_in3:
                col_t_in = st.number_input(
                    "طول العمود t (cm)",
                    min_value=20.0, max_value=500.0, value=60.0, step=5.0,
                    help="طول أو عمق قطاع العمود الخرساني (Default 60 cm)",
                    key="cs_col_t",
                )
            with col_in4:
                col_h_in = st.number_input(
                    "ارتفاع العمود H (cm)",
                    min_value=50.0, max_value=2000.0, value=300.0, step=10.0,
                    help="ارتفاع العمود الخالص الصافي من وش الخرسانة لبطنية السقف (Default 300 cm)",
                    key="cs_col_h",
                )
            with col_in5:
                n_cols_in = st.number_input(
                    "عدد الأعمدة (N)",
                    min_value=1, max_value=10000, value=15, step=1,
                    help="إجمالي عدد الأعمدة المراد حصرها بنفس القطاع (Default 15)",
                    key="cs_n_cols",
                )

            # ── ECP 203 Column Rebar Grid & Rows Calculation ──
            def _calc_ecp_rows(b_val, t_val, nb, phi, cov=2.5):
                off_x = cov + (phi / 10.0) / 2.0
                off_y = cov + (phi / 10.0) / 2.0
                w_reb = max(b_val - 2.0 * off_x, 1.0)
                h_reb = max(t_val - 2.0 * off_y, 1.0)
                if nb <= 4:
                    nx_d, ny_d = 2, 2
                elif nb == 6:
                    nx_d, ny_d = 2, 3
                else:
                    perim = 2.0 * (w_reb + h_reb)
                    s_tgt = perim / nb
                    nx_e = int(round(w_reb / s_tgt)) + 1
                    nx_d = max(2, min(nx_e, nb // 2))
                    ny_d = (nb // 2 + 2) - nx_d
                    if ny_d < 2:
                        ny_d = 2
                        nx_d = (nb // 2 + 2) - ny_d
                sy_d = h_reb / max(ny_d - 1, 1)
                sx_d = w_reb / max(nx_d - 1, 1)
                return ny_d, nx_d, sy_d, sx_d

            # Pre-calculate or fetch current main bars
            current_nb_val = st.session_state.get("cs_n_bars", 8)
            current_b_val = st.session_state.get("cs_col_b", 30.0)
            current_t_val = st.session_state.get("cs_col_t", 60.0)
            current_phi_val = st.session_state.get("cs_phi_main", 16)

            designed_ny, designed_nx, designed_sy, designed_sx = _calc_ecp_rows(
                current_b_val, current_t_val, current_nb_val, current_phi_val, cover_cm
            )

            # Auto-update session state for n_rows & tie_type if parameters change
            design_key_tuple = (current_b_val, current_t_val, current_nb_val, current_phi_val)
            if st.session_state.get("_last_design_key") != design_key_tuple:
                st.session_state["_last_design_key"] = design_key_tuple
                if current_nb_val < 8:
                    st.session_state["cs_n_rows"] = 3 if current_nb_val == 6 else (2 if current_nb_val <= 4 else min(3, designed_ny))
                    st.session_state["cs_tie_type"] = "Box (كانة صندوقية)"
                else:
                    st.session_state["cs_n_rows"] = designed_ny
                    if designed_ny > 3:
                        st.session_state["cs_tie_type"] = "Automatic (كانة أوتوماتيك)"
                    else:
                        st.session_state["cs_tie_type"] = "Box (كانة صندوقية)"

            def _on_n_bars_change():
                nb = st.session_state.get("cs_n_bars", 8)
                if nb < 8:
                    st.session_state["cs_n_rows"] = 3 if nb == 6 else (2 if nb <= 4 else 3)
                    st.session_state["cs_tie_type"] = "Box (كانة صندوقية)"
                else:
                    ny_calc, _, _, _ = _calc_ecp_rows(
                        st.session_state.get("cs_col_b", 30.0),
                        st.session_state.get("cs_col_t", 60.0),
                        nb,
                        st.session_state.get("cs_phi_main", 16),
                        cover_cm,
                    )
                    st.session_state["cs_n_rows"] = ny_calc
                    if ny_calc > 3:
                        st.session_state["cs_tie_type"] = "Automatic (كانة أوتوماتيك)"
                    else:
                        st.session_state["cs_tie_type"] = "Box (كانة صندوقية)"

            def _on_n_rows_change():
                current_rows = st.session_state.get("cs_n_rows", 2)
                nb = st.session_state.get("cs_n_bars", 8)
                if nb < 8:
                    st.session_state["cs_tie_type"] = "Box (كانة صندوقية)"
                elif current_rows > 3:
                    st.session_state["cs_tie_type"] = "Automatic (كانة أوتوماتيك)"
                else:
                    st.session_state["cs_tie_type"] = "Box (كانة صندوقية)"

            # Row 2: Main Rebar & Rows
            col_in6, col_in7, col_in8, col_in9 = st.columns(4)
            with col_in6:
                n_main_bars = st.number_input(
                    "عدد أسياخ الحديد الرئيسي",
                    min_value=4, max_value=100, value=8, step=2,
                    help="إجمالي عدد أسياخ التسليح الطولي للعمود (إذا كان أقل من 8 أسياخ يتم تعيين الكانات إلى Box وتحديد 3 صفوف تلقائياً)",
                    key="cs_n_bars",
                    on_change=_on_n_bars_change,
                )
            with col_in7:
                phi_main_bars = st.selectbox(
                    "قطر الحديد الرئيسي (mm)",
                    options=[10, 12, 14, 16, 18, 20, 22, 25, 28, 32],
                    index=3,  # 16 mm default
                    format_func=lambda d: f"Φ{d} mm",
                    help="قطر أسياخ التسليح الطولي (Default 16 mm)",
                    key="cs_phi_main",
                )

            with col_in8:
                n_rows_in = st.number_input(
                    f"عدد صفوف الحديد (تصميم: {designed_ny} صفوف)",
                    min_value=2, max_value=20, value=st.session_state.get("cs_n_rows", designed_ny), step=1,
                    help=f"محسوب تلقائياً طبقاً لتصميم العمود (ECP 203): {designed_ny} صفوف × {designed_nx} أعمدة أسياخ (المسافة S = {designed_sy:.1f} cm ≤ 25 cm)",
                    key="cs_n_rows",
                    on_change=_on_n_rows_change,
                )
            with col_in9:
                if "cs_tie_type" not in st.session_state:
                    st.session_state["cs_tie_type"] = "Box (كانة صندوقية)" if n_main_bars < 8 or n_rows_in <= 3 else "Automatic (كانة أوتوماتيك)"

                tie_type_choice = st.selectbox(
                    "نوع الكانات",
                    options=["Box (كانة صندوقية)", "Automatic (كانة أوتوماتيك)"],
                    help="نوع الكانات: إذا كان عدد الأسياخ أقل من 8 يتغير تلقائياً إلى Box، وإذا زاد عدد الصفوف عن 3 يتغير تلقائياً إلى Automatic مع إمكانية التعديل اليدوي",
                    key="cs_tie_type",
                )




            # Row 3: Stirrup details & Top floor check
            col_in10, col_in11, col_in12, col_in13 = st.columns(4)
            with col_in10:
                n_st_m = st.number_input(
                    "عدد الكانات في المتر",
                    min_value=4, max_value=15, value=6, step=1,
                    help="عدد الكانات بالمتر الطولي لارتفاع العمود (Default 6/m')",
                    key="cs_n_st_m",
                )
            with col_in11:
                phi_st = st.selectbox(
                    "قطر حديد الكانات (mm)",
                    options=[6, 8, 10, 12],
                    index=1,  # 8 mm default
                    format_func=lambda d: f"Φ{d} mm",
                    help="قطر أسياخ الكانات (Default 8 mm)",
                    key="cs_phi_st",
                )
            with col_in12:
                is_top_floor_sel = st.radio(
                    "عمود دور أخير؟ (Top Floor)",
                    options=["No (متكرر / ليس دور أخير)", "Yes (دور أخير)"],
                    index=0,
                    horizontal=True,
                    help="إذا كانت No يتم حساب وصلة Llap أعلى البلاطة، وإذا كانت Yes يتم حساب جنش/رجل أعلى البلاطة",
                    key="cs_is_top_floor",
                )
            with col_in13:
                lap_factor_sel = st.selectbox(
                    "معامل طول الوصلة / الجنش (Llap)",
                    options=[40, 45, 50, 60],
                    index=2,  # 50 default
                    format_func=lambda x: f"{x} Φ ({lap_factor_sel_cm:.0f} cm)" if 'lap_factor_sel_cm' in locals() else f"{x} Φ",
                    help="طول الوصلة طبقا للكود المصري من 40 إلى 50 مرة القطر (Default 50Φ)",
                    key="cs_lap_factor",
                )

        st.markdown("---")

        # ────────────────────────────────────────────────────────────────────
        # COMPUTATIONS & CALCULATIONS
        # ────────────────────────────────────────────────────────────────────
        is_top = "yes" in is_top_floor_sel.lower()
        cover_cm = 2.5
        L_lap_calc_cm = (lap_factor_sel * phi_main_bars) / 10.0
        L_hook_calc_cm = max(25.0, (lap_factor_sel * phi_main_bars) / 10.0)

        # 1. Main Rebar Length & Weight
        if not is_top:
            # H_col + t_slab + Llap
            L_bar_single_cm = col_h_in + t_slab_in + L_lap_calc_cm
        else:
            # H_col + (t_slab - cover) + Lhook
            L_bar_single_cm = col_h_in + (t_slab_in - cover_cm) + L_hook_calc_cm

        L_bar_single_m = L_bar_single_cm / 100.0
        w_main_unit_kgm = (phi_main_bars ** 2) / 162.0
        w_main_per_col_kg = n_main_bars * L_bar_single_m * w_main_unit_kgm
        w_main_total_kg = w_main_per_col_kg * n_cols_in
        w_main_total_ton = w_main_total_kg / 1000.0

        # 2. Stirrups Length & Weight
        b_core_calc = max(col_b_in - 2.0 * cover_cm, 1.0)
        t_core_calc = max(col_t_in - 2.0 * cover_cm, 1.0)
        hook_len_tie_cm = max(8.0, 10.0 * (phi_st / 10.0))

        is_auto_tie_calc = "auto" in tie_type_choice.lower() or "أوتوماتيك" in tie_type_choice

        if is_auto_tie_calc:
            # Inner tie addition
            t_core_in_calc = max(t_core_calc * 0.5, 5.0)
            b_core_in_calc = b_core_calc
            L_tie_single_cm = 2.0 * (b_core_calc + t_core_calc) + 2.0 * (b_core_in_calc + t_core_in_calc) + 4.0 * hook_len_tie_cm
        else:
            L_tie_single_cm = 2.0 * (b_core_calc + t_core_calc) + 2.0 * hook_len_tie_cm

        L_tie_single_m = L_tie_single_cm / 100.0
        n_ties_per_col = max(3, int(math.ceil((col_h_in / 100.0) * n_st_m)))
        w_st_unit_kgm = (phi_st ** 2) / 162.0
        w_st_per_col_kg = n_ties_per_col * L_tie_single_m * w_st_unit_kgm
        w_st_total_kg = w_st_per_col_kg * n_cols_in
        w_st_total_ton = w_st_total_kg / 1000.0

        # 3. Concrete Volume & Grand Totals
        vol_col_single_m3 = (col_b_in / 100.0) * (col_t_in / 100.0) * (col_h_in / 100.0)
        vol_col_total_m3 = vol_col_single_m3 * n_cols_in

        w_steel_total_kg = w_main_total_kg + w_st_total_kg
        w_steel_total_ton = w_steel_total_kg / 1000.0
        steel_rate_kg_m3 = (w_steel_total_kg / vol_col_total_m3) if vol_col_total_m3 > 0 else 0.0

        st.markdown("#### 📐 المخطط الإنشائي المتكامل وتفريد التسليح (Structural Drawings & BBS Detailing)")

        fig_unified = draw_column_unified_sheet(
            b_cm=col_b_in,
            t_cm=col_t_in,
            H_col_cm=col_h_in,
            t_slab_cm=t_slab_in,
            n_bars=n_main_bars,
            phi_mm=phi_main_bars,
            phi_st_mm=phi_st,
            n_st_per_m=n_st_m,
            is_top_floor=is_top,
            lap_factor=lap_factor_sel,
            tie_type=tie_type_choice,
            n_rows=n_rows_in,
            cover=cover_cm,
        )
        st.pyplot(fig_unified, use_container_width=True)


        # ────────────────────────────────────────────────────────────────────
        # BOTTOM PANEL: DETAILED QUANTITY TAKEOFF RESULTS
        # ────────────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 لوحة نتائج حصر الخرسانات والحديد (Quantity Takeoff Panel)")

        # Summary Metric Cards
        p_m1, p_m2, p_m3, p_m4, p_m5 = st.columns(5)
        p_m1.metric("إجمالي حجم الخرسانة", f"{vol_col_total_m3:.2f} m³", f"للعمود: {vol_col_single_m3:.3f} m³")
        p_m2.metric("إجمالي الحديد الرئيسي", f"{w_main_total_ton:.3f} Ton", f"{w_main_total_kg:.1f} kg")
        p_m3.metric("إجمالي حديد الكانات", f"{w_st_total_ton:.3f} Ton", f"{w_st_total_kg:.1f} kg")
        p_m4.metric("إجمالي وزن الحديد الكلي", f"{w_steel_total_ton:.3f} Ton", f"{w_steel_total_kg:.1f} kg")
        p_m5.metric("معدل استهلاك الحديد", f"{steel_rate_kg_m3:.1f} kg/m³")

        # Detailed Breakdown Table with High-Visibility Large Typography (1.25x Enlarged)
        st.markdown(
            """
            <div style="font-size: 24px; font-weight: 800; color: #1e3a8a; margin: 20px 0 12px 0; display: flex; align-items: center; gap: 10px;">
                <span>📋 جدول تفصيلي بحصر الكميات والحديد (Takeoff Breakdown)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        takeoff_html = f"""
        <div style="overflow-x:auto; margin-top:10px; margin-bottom:20px;">
        <table style="width:100%; border-collapse:collapse; font-size:25px; font-family:'Segoe UI', Tahoma, sans-serif; background:#ffffff; border:2.5px solid #94a3b8; border-radius:10px; box-shadow:0 3px 8px rgba(0,0,0,0.08);">
            <thead>
                <tr style="background:#1e3a8a; color:#ffffff; font-size:26px; font-weight:800; text-align:center;">
                    <th style="padding:16px 16px; border:1px solid #3b82f6; text-align:right;">البند / Component</th>
                    <th style="padding:16px 14px; border:1px solid #3b82f6;">القطاع / المواصفة</th>
                    <th style="padding:16px 12px; border:1px solid #3b82f6;">العدد</th>
                    <th style="padding:16px 14px; border:1px solid #3b82f6;">طول الإفراد</th>
                    <th style="padding:16px 14px; border:1px solid #3b82f6;">إجمالي الطول</th>
                    <th style="padding:16px 16px; border:1px solid #3b82f6; background:#1d4ed8;">الوزن / الحجم الإجمالي</th>
                    <th style="padding:16px 16px; border:1px solid #3b82f6;">ملاحظات</th>
                </tr>
            </thead>
            <tbody>
                <tr style="background:#f8fafc; font-size:24px; text-align:center;">
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#0f172a;">1. الخرسانة المسلحة للأعمدة</td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:700;"><span dir="ltr">{col_b_in:.0f}×{col_t_in:.0f}×{col_h_in:.0f} cm</span></td>
                    <td style="padding:14px 12px; border:1px solid #cbd5e1; font-weight:800; color:#1e3a8a;">{n_cols_in} عمود</td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1;"><span dir="ltr">H = {col_h_in/100:.2f} m</span></td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:700;"><span dir="ltr">{n_cols_in * (col_h_in/100):.1f} m'</span></td>
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; color:#1e3a8a; background:#eff6ff; font-size:26px;"><span dir="ltr">{vol_col_total_m3:.2f} m³</span></td>
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:21px; color:#475569;">حجم العمود = <span dir="ltr">{vol_col_single_m3:.3f} m³</span></td>
                </tr>
                <tr style="background:#ffffff; font-size:24px; text-align:center;">
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#0f172a;">2. حديد التسليح الرئيسي</td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; color:#b91c1c; font-weight:800; font-size:25px;"><span dir="ltr">{n_main_bars} Φ{phi_main_bars} mm [{n_rows_in} Rows]</span></td>
                    <td style="padding:14px 12px; border:1px solid #cbd5e1; font-weight:800; color:#b91c1c;">{n_cols_in * n_main_bars} سيخ</td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:700;"><span dir="ltr">{L_bar_single_m:.2f} m ({L_bar_single_cm:.0f} cm)</span></td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:700;"><span dir="ltr">{n_cols_in * n_main_bars * L_bar_single_m:.1f} m'</span></td>
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; color:#991b1b; background:#fef2f2; font-size:26px;"><span dir="ltr">{w_main_total_kg:.1f} kg</span><br><span style="font-size:22px; color:#b91c1c;" dir="ltr">({w_main_total_ton:.3f} Ton)</span></td>
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:21px; color:#475569;">ارتفاع <span dir="ltr">{col_h_in:.0f}cm</span> + سقف <span dir="ltr">{t_slab_in:.0f}cm</span> + وصلة <span dir="ltr">({lap_factor_sel:.0f}Φ)</span></td>
                </tr>
                <tr style="background:#f8fafc; font-size:24px; text-align:center;">
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#0f172a;">3. حديد الكانات</td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; color:#15803d; font-weight:800; font-size:25px;"><span dir="ltr">{tie_type_choice.split(' ')[0]} - Φ{phi_st} mm</span></td>
                    <td style="padding:14px 12px; border:1px solid #cbd5e1; font-weight:800; color:#15803d;">{n_cols_in * n_ties_per_col} كانة <br><span style="font-size:20px;">({n_ties_per_col}/عمود)</span></td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:700;"><span dir="ltr">{L_tie_single_m:.2f} m ({L_tie_single_cm:.0f} cm)</span></td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:700;"><span dir="ltr">{n_cols_in * n_ties_per_col * L_tie_single_m:.1f} m'</span></td>
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; color:#15803d; background:#f0fdf4; font-size:26px;"><span dir="ltr">{w_st_total_kg:.1f} kg</span><br><span style="font-size:22px; color:#15803d;" dir="ltr">({w_st_total_ton:.3f} Ton)</span></td>
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:21px; color:#475569;">كثافة <span dir="ltr">{n_st_m} Φ{phi_st}/m'</span> (أبعاد <span dir="ltr">{col_b_in-2*cover_cm:.0f}×{col_t_in-2*cover_cm:.0f} cm</span>)</td>
                </tr>
                <tr style="background:#fefce8; font-size:25px; font-weight:800; text-align:center; border-top:3px solid #ca8a04;">
                    <td style="padding:16px 16px; border:1px solid #cbd5e1; color:#854d0e; text-align:right; font-size:26px;">✅ الإجمالي العام لحديد التسليح</td>
                    <td style="padding:16px 14px; border:1px solid #cbd5e1; color:#854d0e;"><span dir="ltr">Φ{phi_main_bars} + Φ{phi_st}</span></td>
                    <td style="padding:16px 12px; border:1px solid #cbd5e1; color:#854d0e;">—</td>
                    <td style="padding:16px 14px; border:1px solid #cbd5e1; color:#854d0e;">—</td>
                    <td style="padding:16px 14px; border:1px solid #cbd5e1; color:#854d0e; font-weight:800;"><span dir="ltr">{n_cols_in * n_main_bars * L_bar_single_m + n_cols_in * n_ties_per_col * L_tie_single_m:.1f} m'</span></td>
                    <td style="padding:16px 16px; border:1px solid #cbd5e1; color:#854d0e; background:#fef08a; font-size:28px; font-weight:800;"><span dir="ltr">{w_steel_total_kg:.1f} kg</span><br><span style="font-size:24px;" dir="ltr">({w_steel_total_ton:.3f} Ton)</span></td>
                    <td style="padding:16px 16px; border:1px solid #cbd5e1; color:#854d0e; font-size:24px; font-weight:800;">معدل الحديد = <span dir="ltr">{steel_rate_kg_m3:.1f} kg/m³</span></td>
                </tr>
            </tbody>
        </table>
        </div>
        """
        st.markdown(takeoff_html, unsafe_allow_html=True)



        # Materials estimation for columns
        with st.expander("🧪 تقدير مواد الخلطة لخرسانة الأعمدة (أسمنت، رمل، سن، ماء)"):
            c_cement_tons = (vol_col_total_m3 * 350.0) / 1000.0
            c_cement_bags = int(round((vol_col_total_m3 * 350.0) / 50.0))
            c_sand_m3 = vol_col_total_m3 * 0.40
            c_gravel_m3 = vol_col_total_m3 * 0.80
            c_water_liters = vol_col_total_m3 * 350.0 * 0.50

            mat_c1, mat_c2, mat_c3, mat_c4 = st.columns(4)
            mat_c1.metric("أسمنت (350 kg/m³)", f"{c_cement_tons:.2f} طن", f"{c_cement_bags} شكارة")
            mat_c2.metric("رمل (0.40 m³/m³)", f"{c_sand_m3:.2f} m³")
            mat_c3.metric("سن / زلط (0.80 m³/m³)", f"{c_gravel_m3:.2f} m³")
            mat_c4.metric("مياه صالحة (W/C=0.50)", f"{c_water_liters:.0f} لتر")

        # ────────────────────────────────────────────────────────────────────
        # SAVE & PRINT ACTIONS SECTION (حفظ وطباعة النتائج)
        # ────────────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🖨️ حفظ وطباعة نتائج الحصر (Save & Print Reports)")

        img_unified_b64 = fig_to_base64(fig_unified)

        col_survey_html = generate_column_survey_report_html(
            project_name="حصر أعمدة خرسانية (Column Takeoff)",
            b=col_b_in,
            t=col_t_in,
            H=col_h_in,
            t_slab=t_slab_in,
            n_cols=n_cols_in,
            n_bars=n_main_bars,
            phi_main=phi_main_bars,
            n_rows=n_rows_in,
            tie_type=tie_type_choice,
            n_st_m=n_st_m,
            phi_st=phi_st,
            is_top_floor=is_top,
            lap_factor=lap_factor_sel,
            L_bar_m=L_bar_single_m,
            L_bar_cm=L_bar_single_cm,
            w_main_total_kg=w_main_total_kg,
            w_main_total_ton=w_main_total_ton,
            L_tie_m=L_tie_single_m,
            L_tie_cm=L_tie_single_cm,
            n_ties_per_col=n_ties_per_col,
            w_st_total_kg=w_st_total_kg,
            w_st_total_ton=w_st_total_ton,
            vol_col_single_m3=vol_col_single_m3,
            vol_col_total_m3=vol_col_total_m3,
            w_steel_total_kg=w_steel_total_kg,
            w_steel_total_ton=w_steel_total_ton,
            steel_rate_kg_m3=steel_rate_kg_m3,
            cement_tons=c_cement_tons,
            cement_bags=c_cement_bags,
            sand_m3=c_sand_m3,
            gravel_m3=c_gravel_m3,
            water_liters=c_water_liters,
            img_plan_b64=img_unified_b64,
            img_elev_b64=None,
        )

        pdf_bytes = html_to_pdf_bytes(col_survey_html)

        # CSV export data
        export_df = pd.DataFrame([
            {"البند": "الخرسانة المسلحة للأعمدة", "القطاع": f"{col_b_in:.0f}×{col_t_in:.0f}×{col_h_in:.0f} cm", "العدد": n_cols_in, "طول الإفراد (m)": f"{col_h_in/100:.2f}", "إجمالي الطول (m')": f"{n_cols_in * (col_h_in/100):.1f}", "الحجم/الوزن": f"{vol_col_total_m3:.2f} m³", "الوحدة": "متر مكعب m³"},
            {"البند": "حديد التسليح الرئيسي", "القطاع": f"{n_main_bars} Φ{phi_main_bars} mm", "العدد": n_cols_in * n_main_bars, "طول الإفراد (m)": f"{L_bar_single_m:.2f}", "إجمالي الطول (m')": f"{n_cols_in * n_main_bars * L_bar_single_m:.1f}", "الحجم/الوزن": f"{w_main_total_kg:.1f} kg ({w_main_total_ton:.3f} Ton)", "الوحدة": "كجم / طن"},
            {"البند": "حديد الكانات", "القطاع": f"{tie_type_choice.split(' ')[0]} Φ{phi_st} mm", "العدد": n_cols_in * n_ties_per_col, "طول الإفراد (m)": f"{L_tie_single_m:.2f}", "إجمالي الطول (m')": f"{n_cols_in * n_ties_per_col * L_tie_single_m:.1f}", "الحجم/الوزن": f"{w_st_total_kg:.1f} kg ({w_st_total_ton:.3f} Ton)", "الوحدة": "كجم / طن"},
            {"البند": "الإجمالي العام للحديد", "القطاع": f"رئيسي Φ{phi_main_bars} + كانات Φ{phi_st}", "العدد": "-", "طول الإفراد (m)": "-", "إجمالي الطول (m')": f"{n_cols_in * n_main_bars * L_bar_single_m + n_cols_in * n_ties_per_col * L_tie_single_m:.1f}", "الحجم/الوزن": f"{w_steel_total_kg:.1f} kg ({w_steel_total_ton:.3f} Ton)", "الوحدة": "كجم / طن"},
        ])
        csv_data = export_df.to_csv(index=False).encode('utf-8-sig')

        b_c1, b_c2, b_c3 = st.columns(3)
        with b_c1:
            st.download_button(
                label="🌐 حفظ وطباعة التقرير (HTML / Print)",
                data=col_survey_html,
                file_name=f"Concrete_Columns_Takeoff_{col_b_in:.0f}x{col_t_in:.0f}cm.html",
                mime="text/html",
                use_container_width=True,
                help="حفظ تقرير الحصر كملف ويب جاهز للطباعة الفورية بضغطة زر واحدة",
            )
        with b_c2:
            if pdf_bytes:
                st.download_button(
                    label="📕 حفظ التقرير كـ PDF (مباشر)",
                    data=pdf_bytes,
                    file_name=f"Concrete_Columns_Takeoff_{col_b_in:.0f}x{col_t_in:.0f}cm.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    help="تصدير مذكرة الحصر بصيغة PDF الرسمية للطباعة والأرشفة",
                )
            else:
                st.download_button(
                    label="📕 حفظ كـ PDF (عبر المتصفح)",
                    data=col_survey_html,
                    file_name=f"Concrete_Columns_Takeoff_{col_b_in:.0f}x{col_t_in:.0f}cm.html",
                    mime="text/html",
                    use_container_width=True,
                )
        with b_c3:
            st.download_button(
                label="📊 تصدير جدول الحصر (Excel / CSV)",
                data=csv_data,
                file_name=f"Concrete_Columns_Takeoff_{col_b_in:.0f}x{col_t_in:.0f}cm.csv",
                mime="text/csv",
                use_container_width=True,
                help="تصدير جدول الكميات إلى ملف CSV متوافق مع Excel",
            )


    # ────────────────────────────────────────────────────────────────────────
    # TAB 2 — Elements Survey (Categorized by Element Type)
    # ────────────────────────────────────────────────────────────────────────
    with tab_quick:
        st.markdown("#### حصر العناصر الإنشائية الرئيسية")
        
        # 1. Footings
        with st.expander("🪨 1. القواعد (Footings - PC & RC)", expanded=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                st.markdown("**القواعد العادية (Plain Concrete - PC)**")
                pc_l = st.number_input("متوسط الطول L (m)", min_value=0.0, value=2.20, step=0.10, key="surv_pc_l")
                pc_b = st.number_input("متوسط العرض B (m)", min_value=0.0, value=2.00, step=0.10, key="surv_pc_b")
                pc_t = st.number_input("السماكة t (m)", min_value=0.0, value=0.30, step=0.05, key="surv_pc_t")
                pc_n = st.number_input("عدد القواعد العادية", min_value=0, value=12, step=1, key="surv_pc_n")
                pc_vol = pc_l * pc_b * pc_t * pc_n
                st.markdown(f"**حجم خرسانة عادية:** `{pc_vol:.2f} m³`")

            with f_col2:
                st.markdown("**القواعد المسلحة (Reinforced Concrete - RC)**")
                rc_l = st.number_input("متوسط الطول L (m)", min_value=0.0, value=1.80, step=0.10, key="surv_rc_l")
                rc_b = st.number_input("متوسط العرض B (m)", min_value=0.0, value=1.60, step=0.10, key="surv_rc_b")
                rc_t = st.number_input("السماكة t (m)", min_value=0.0, value=0.60, step=0.05, key="surv_rc_t")
                rc_n = st.number_input("عدد القواعد المسلحة", min_value=0, value=12, step=1, key="surv_rc_n")
                rc_vol = rc_l * rc_b * rc_t * rc_n
                st.markdown(f"**حجم خرسانة مسلحة:** `{rc_vol:.2f} m³`")

        # 2. Columns & Necks
        with st.expander("🏛️ 2. الأعمدة ورقاب الأعمدة (Columns & Necks)", expanded=True):
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                st.markdown("**رقاب الأعمدة (Neck Columns)**")
                cn_b = st.number_input("عرض العمود b (m)", min_value=0.0, value=0.30, step=0.05, key="surv_cn_b")
                cn_t = st.number_input("طول قطاع العمود t (m)", min_value=0.0, value=0.60, step=0.05, key="surv_cn_t")
                cn_h = st.number_input("ارتفاع رقبة العمود H (m)", min_value=0.0, value=1.20, step=0.10, key="surv_cn_h")
                cn_n = st.number_input("عدد الرقاب", min_value=0, value=12, step=1, key="surv_cn_n")
                cn_vol = cn_b * cn_t * cn_h * cn_n
                st.markdown(f"**حجم رقاب الأعمدة:** `{cn_vol:.2f} m³`")

            with c_col2:
                st.markdown("**أعمدة الأدوار المتكررة (Columns)**")
                col_b = st.number_input("عرض العمود b (m)", min_value=0.0, value=0.30, step=0.05, key="surv_col_b")
                col_t = st.number_input("طول قطاع العمود t (m)", min_value=0.0, value=0.60, step=0.05, key="surv_col_t")
                col_h = st.number_input("ارتفاع العمود الصافي H (m)", min_value=0.0, value=2.80, step=0.10, key="surv_col_h")
                col_n = st.number_input("عدد الأعمدة بالدور", min_value=0, value=12, step=1, key="surv_col_n")
                col_floors = st.number_input("عدد الأدوار", min_value=1, value=1, step=1, key="surv_col_floors")
                col_vol = col_b * col_t * col_h * col_n * col_floors
                st.markdown(f"**حجم الأعمدة الكلي:** `{col_vol:.2f} m³`")

        # 3. Ground Beams & Tie Beams (السملات والشدادات)
        with st.expander("🔗 3. السملات والشدادات (Ground Beams & Straps)", expanded=False):
            gb_col1, gb_col2 = st.columns(2)
            with gb_col1:
                gb_l = st.number_input("إجمالي أطوال السملات L (m)", min_value=0.0, value=85.0, step=1.0, key="surv_gb_l")
                gb_b = st.number_input("عرض السمل b (m)", min_value=0.0, value=0.30, step=0.05, key="surv_gb_b")
            with gb_col2:
                gb_t = st.number_input("ارتفاع السمل t (m)", min_value=0.0, value=0.60, step=0.05, key="surv_gb_t")
                gb_n = st.number_input("المعامل / التكرار", min_value=1, value=1, step=1, key="surv_gb_n")
            gb_vol = gb_l * gb_b * gb_t * gb_n
            st.markdown(f"**حجم السملات والشدادات:** `{gb_vol:.2f} m³`")

        # 4. Slabs & Beams (الأسقف والكمرات)
        with st.expander("🟦 4. الأسقف والكمرات (Slabs & Beams)", expanded=True):
            slab_type = st.radio(
                "نوع البلاطة / Slab Type",
                ["Flat Slab (بلاطة لاكمرية)", "Solid Slab (بلاطة كمرية)"],
                horizontal=True,
                key="surv_slab_type"
            )
            
            if "Flat" in slab_type:
                sl_c1, sl_c2 = st.columns(2)
                with sl_c1:
                    sl_area = st.number_input("مساحة المسطح (m²)", min_value=0.0, value=200.0, step=10.0, key="surv_fs_area")
                    sl_ts = st.number_input("سماكة البلاطة ts (m)", min_value=0.0, value=0.20, step=0.02, key="surv_fs_ts")
                with sl_c2:
                    sl_drop_vol = st.number_input("حجم السقوط والكمرات الطرفية (m³)", min_value=0.0, value=3.5, step=0.5, key="surv_fs_drop")
                    sl_floors = st.number_input("عدد الأسقف", min_value=1, value=1, step=1, key="surv_fs_floors")
                slab_vol = (sl_area * sl_ts + sl_drop_vol) * sl_floors
            else:
                sl_c1, sl_c2 = st.columns(2)
                with sl_c1:
                    sl_area = st.number_input("مساحة السقف (m²)", min_value=0.0, value=200.0, step=10.0, key="surv_ss_area")
                    sl_ts = st.number_input("متوسط سماكة البلاطة ts (m)", min_value=0.0, value=0.14, step=0.01, key="surv_ss_ts")
                with sl_c2:
                    beam_vol = st.number_input("حجم سقوط الكمرات الكلي (m³)", min_value=0.0, value=12.0, step=0.5, key="surv_ss_beams")
                    sl_floors = st.number_input("عدد الأسقف", min_value=1, value=1, step=1, key="surv_ss_floors")
                slab_vol = (sl_area * sl_ts + beam_vol) * sl_floors

            st.markdown(f"**حجم خرسانة الأسقف:** `{slab_vol:.2f} m³`")

        # 5. Summary Cards
        st.markdown("---")
        st.markdown("#### 📊 ملخص الحجوم الإجمالية")
        
        total_rc_elements = rc_vol + cn_vol + col_vol + gb_vol + slab_vol
        total_all = pc_vol + total_rc_elements

        s1, s2, s3 = st.columns(3)
        s1.metric("خرسانة عادية (PC)", f"{pc_vol:.2f} m³")
        s2.metric("خرسانة مسلحة (RC)", f"{total_rc_elements:.2f} m³")
        s3.metric("إجمالي الخرسانات الكلي", f"{total_all:.2f} m³")

        # Breakdown summary dataframe
        breakdown_df = pd.DataFrame([
            {"البند / Element": "1. خرسانة عادية للقواعد (PC Footings)", "النوع": "عادية (PC)", "الحجم (m³)": f"{pc_vol:.2f}"},
            {"البند / Element": "2. خرسانة مسلحة للقواعد (RC Footings)", "النوع": "مسلحة (RC)", "الحجم (m³)": f"{rc_vol:.2f}"},
            {"البند / Element": "3. رقاب الأعمدة (Column Necks)", "النوع": "مسلحة (RC)", "الحجم (m³)": f"{cn_vol:.2f}"},
            {"البند / Element": "4. الأعمدة المتكررة (Columns)", "النوع": "مسلحة (RC)", "الحجم (m³)": f"{col_vol:.2f}"},
            {"البند / Element": "5. السملات والشدادات (Ground Beams)", "النوع": "مسلحة (RC)", "الحجم (m³)": f"{gb_vol:.2f}"},
            {"البند / Element": "6. الأسقف والكمرات (Slabs & Beams)", "النوع": "مسلحة (RC)", "الحجم (m³)": f"{slab_vol:.2f}"},
            {"البند / Element": "المجموع الكلي للخرسانة المسلحة (Total RC)", "النوع": "مسلحة (RC)", "الحجم (m³)": f"{total_rc_elements:.2f}"},
            {"البند / Element": "الإجمالي العام لكافة الخرسانات (Grand Total)", "النوع": "الكل (All)", "الحجم (m³)": f"{total_all:.2f}"},
        ])
        st.dataframe(breakdown_df, use_container_width=True, hide_index=True)

    # ────────────────────────────────────────────────────────────────────────
    # TAB 3 — Custom Takeoff Table (Dynamic Rows)
    # ────────────────────────────────────────────────────────────────────────
    with tab_table:
        st.markdown("#### جدول حصر كميات تفصيلي (Dynamic Takeoff Table)")
        st.caption("أضف بنود الحصر بالأبعاد المباشرة (طول × عرض × ارتفاع × عدد) لحساب الحجم لكل بند.")

        if "custom_takeoff_rows" not in st.session_state:
            st.session_state["custom_takeoff_rows"] = [
                {"name": "قواعد مسلحة ق1", "type": "RC", "n": 6, "l": 2.0, "w": 1.8, "h": 0.60, "deduct": 0.0},
                {"name": "أعمدة ع1 دور أرضي", "type": "RC", "n": 10, "l": 0.30, "w": 0.60, "h": 3.00, "deduct": 0.0},
                {"name": "سقف الدور الأرضي", "type": "RC", "n": 1, "l": 15.0, "w": 12.0, "h": 0.20, "deduct": 4.5},
            ]

        def _add_takeoff_row():
            st.session_state["custom_takeoff_rows"].append(
                {"name": f"بند جديد #{len(st.session_state['custom_takeoff_rows'])+1}", "type": "RC", "n": 1, "l": 1.0, "w": 1.0, "h": 1.0, "deduct": 0.0}
            )

        def _clear_takeoff_rows():
            st.session_state["custom_takeoff_rows"] = []

        b_c1, b_c2, _ = st.columns([1.2, 1.2, 3.6])
        b_c1.button("➕ إضافة بند حصر", on_click=_add_takeoff_row, use_container_width=True)
        b_c2.button("🗑️ مسح الجدول", on_click=_clear_takeoff_rows, use_container_width=True)

        rows_to_del = []
        rows = st.session_state["custom_takeoff_rows"]

        if rows:
            st.markdown("")
            # Header
            h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([2.5, 1, 1, 1, 1, 1, 1.2, 0.5])
            h1.caption("**اسم البند**")
            h2.caption("**النوع**")
            h3.caption("**العدد**")
            h4.caption("**الطول L (m)**")
            h5.caption("**العرض B (m)**")
            h6.caption("**الارتفاع H (m)**")
            h7.caption("**الخصم (m³)**")
            h8.caption("")

            for idx, r in enumerate(rows):
                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.5, 1, 1, 1, 1, 1, 1.2, 0.5])
                with c1:
                    r["name"] = st.text_input(f"name_{idx}", value=r["name"], key=f"tk_name_{idx}", label_visibility="collapsed")
                with c2:
                    r["type"] = st.selectbox(f"type_{idx}", ["RC", "PC"], index=0 if r["type"] == "RC" else 1, key=f"tk_type_{idx}", label_visibility="collapsed")
                with c3:
                    r["n"] = st.number_input(f"n_{idx}", min_value=1, value=int(r["n"]), step=1, key=f"tk_n_{idx}", label_visibility="collapsed")
                with c4:
                    r["l"] = st.number_input(f"l_{idx}", min_value=0.0, value=float(r["l"]), step=0.1, key=f"tk_l_{idx}", label_visibility="collapsed")
                with c5:
                    r["w"] = st.number_input(f"w_{idx}", min_value=0.0, value=float(r["w"]), step=0.1, key=f"tk_w_{idx}", label_visibility="collapsed")
                with c6:
                    r["h"] = st.number_input(f"h_{idx}", min_value=0.0, value=float(r["h"]), step=0.05, key=f"tk_h_{idx}", label_visibility="collapsed")
                with c7:
                    r["deduct"] = st.number_input(f"ded_{idx}", min_value=0.0, value=float(r.get("deduct", 0.0)), step=0.1, key=f"tk_ded_{idx}", label_visibility="collapsed")
                with c8:
                    if st.button("✕", key=f"tk_del_{idx}", help="حذف البند"):
                        rows_to_del.append(idx)

            for d_idx in reversed(rows_to_del):
                st.session_state["custom_takeoff_rows"].pop(d_idx)
            if rows_to_del:
                st.rerun()

            # Process summary table
            st.markdown("---")
            table_summary = []
            tot_rc_custom = 0.0
            tot_pc_custom = 0.0

            for r in rows:
                gross_v = r["n"] * r["l"] * r["w"] * r["h"]
                net_v = max(0.0, gross_v - r.get("deduct", 0.0))
                if r["type"] == "RC":
                    tot_rc_custom += net_v
                else:
                    tot_pc_custom += net_v

                table_summary.append({
                    "البند": r["name"],
                    "النوع": "خرسانة مسلحة (RC)" if r["type"] == "RC" else "خرسانة عادية (PC)",
                    "العدد": r["n"],
                    "الطول (m)": f"{r['l']:.2f}",
                    "العرض (m)": f"{r['w']:.2f}",
                    "الارتفاع (m)": f"{r['h']:.2f}",
                    "الخصم (m³)": f"{r.get('deduct', 0.0):.2f}",
                    "صافي الحجم (m³)": f"{net_v:.2f}",
                })

            st.dataframe(pd.DataFrame(table_summary), use_container_width=True, hide_index=True)

            k1, k2, k3 = st.columns(3)
            k1.metric("إجمالي خرسانة عادية (PC)", f"{tot_pc_custom:.2f} m³")
            k2.metric("إجمالي خرسانة مسلحة (RC)", f"{tot_rc_custom:.2f} m³")
            k3.metric("الإجمالي الكلي", f"{tot_pc_custom + tot_rc_custom:.2f} m³")
        else:
            st.info("لا توجد بنود حالياً. اضغط على **➕ إضافة بند حصر** للبدء.")

    # ────────────────────────────────────────────────────────────────────────
    # TAB 4 — Mix Materials Estimator (حساب كميات المواد)
    # ────────────────────────────────────────────────────────────────────────
    with tab_materials:
        st.markdown("#### 🧪 تقدير كميات مواد الخلطة الخرسانية")
        st.caption("تقدير كميات الأسمنت والرمل والسن والمياه بناءً على حجم الخرسانة ونسب الخلطة المحددة.")

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.markdown("**بيانات الحجم والهالك**")
            vol_input = st.number_input(
                "حجم الخرسانة المطلوب تقديره (m³)",
                min_value=0.1,
                value=float(round(total_all if 'total_all' in locals() and total_all > 0 else 50.0, 2)),
                step=5.0,
                key="mix_vol_input"
            )
            waste_pct = st.number_input(
                "نسبة الهالك والفاقد المضافة (%)",
                min_value=0.0,
                max_value=30.0,
                value=5.0,
                step=1.0,
                key="mix_waste_pct"
            )
            total_vol_with_waste = vol_input * (1.0 + waste_pct / 100.0)

        with m_col2:
            st.markdown("**مواصفات الخلطة الخرسانية (Mix Proportions)**")
            cement_content = st.number_input(
                "محتوى الأسمنت (kg/m³) — عادة 250 للعادية و 350 للمسلحة",
                min_value=150.0,
                max_value=600.0,
                value=350.0,
                step=25.0,
                key="mix_cement_content"
            )
            sand_ratio = st.number_input(
                "نسبة الرمل (m³/m³) — عادة 0.40",
                min_value=0.1,
                max_value=1.0,
                value=0.40,
                step=0.05,
                key="mix_sand_ratio"
            )
            gravel_ratio = st.number_input(
                "نسبة السن / الزلط (m³/m³) — عادة 0.80",
                min_value=0.1,
                max_value=1.5,
                value=0.80,
                step=0.05,
                key="mix_gravel_ratio"
            )
            water_ratio = st.number_input(
                "نسبة مياه الخلط (W/C Ratio) — عادة 0.45 إلى 0.50",
                min_value=0.30,
                max_value=0.70,
                value=0.50,
                step=0.05,
                key="mix_water_ratio"
            )

        # Computations
        tot_cement_kg = total_vol_with_waste * cement_content
        tot_cement_tons = tot_cement_kg / 1000.0
        tot_cement_bags = tot_cement_kg / 50.0  # 50kg bag
        tot_sand_m3 = total_vol_with_waste * sand_ratio
        tot_gravel_m3 = total_vol_with_waste * gravel_ratio
        tot_water_liters = tot_cement_kg * water_ratio

        st.markdown("---")
        st.markdown("#### 📦 جدول الكميات التقديرية للمواد (Bill of Materials)")

        mat_summary = [
            {"المادة": "🧱 الأسمنت (Cement)", "الكمية": f"{tot_cement_tons:.2f} طن ({tot_cement_bags:.0f} شيكارة)", "الوحدة": "طن / شكارة 50kg", "ملاحظات": f"{cement_content:.0f} kg/m³ + {waste_pct}% هالك"},
            {"المادة": "🏖️ الرمل النظيف (Sand)", "الكمية": f"{tot_sand_m3:.2f}", "الوحدة": "متر مكعب (m³)", "ملاحظات": f"{sand_ratio:.2f} m³/m³"},
            {"المادة": "🪨 السن / الزلط (Gravel/Coarse Agg.)", "الكمية": f"{tot_gravel_m3:.2f}", "الوحدة": "متر مكعب (m³)", "ملاحظات": f"{gravel_ratio:.2f} m³/m³"},
            {"المادة": "💧 مياه الخلط الصالحة (Water)", "الكمية": f"{tot_water_liters:.0f} لتر ({tot_water_liters/1000:.2f} m³)", "الوحدة": "لتر / m³", "ملاحظات": f"W/C = {water_ratio:.2f}"},
        ]
        st.dataframe(pd.DataFrame(mat_summary), use_container_width=True, hide_index=True)

        res1, res2, res3, res4 = st.columns(4)
        res1.metric("إجمالي الأسمنت", f"{tot_cement_tons:.2f} Ton", f"{tot_cement_bags:.0f} شكارة")
        res2.metric("إجمالي الرمل", f"{tot_sand_m3:.2f} m³")
        res3.metric("إجمالي السن/الزلط", f"{tot_gravel_m3:.2f} m³")
        res4.metric("إجمالي المياه", f"{tot_water_liters:.0f} L")
