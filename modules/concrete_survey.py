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

import io
import base64
import wave
import struct
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from modules.settings import (
    load_settings,
    save_settings,
    cfg_val,
    cfg_set,
    text_input,
    get_safe_profile_filename_prefix,
)
from modules.report_generator import (
    generate_column_survey_report_html,
    html_to_pdf_bytes,
    fig_to_base64,
)
from modules.table_styler import render_styled_table, get_styled_table_html


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
    has_footing_dowels: bool = False,
    L_foot_cm: float = None,
    L_bar_custom_m: float = None,
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
    L_foot_val_cm = max(25.0, (12.0 * phi_mm) / 10.0) if L_foot_cm is None else L_foot_cm

    if not is_top_floor:
        L_calc_cm = H_col_cm + t_slab_cm + L_lap_cm + (L_foot_val_cm if has_footing_dowels else 0.0)
    else:
        L_calc_cm = H_col_cm + (t_slab_cm - cover) + L_hook_cm + (L_foot_val_cm if has_footing_dowels else 0.0)

    L_calc_m = L_calc_cm / 100.0

    if L_bar_custom_m is not None and L_bar_custom_m > 0:
        L_bar_m = float(L_bar_custom_m)
        L_bar_cm = L_bar_m * 100.0
    else:
        L_bar_cm = L_calc_cm
        L_bar_m = L_calc_m

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

    # Vertical bar main shafts
    ax_elev.plot([bx_left, bx_left], [y_bot, y_slab_top], color="#dc2626", lw=2.8, zorder=4)
    if has_footing_dowels:
        ax_elev.plot([bx_left, bx_left + 0.20], [y_bot, y_bot], color="#dc2626", lw=2.8, zorder=4)
    
    ax_elev.plot([bx_right, bx_right], [y_bot, y_slab_top], color="#dc2626", lw=2.8, zorder=4)
    if has_footing_dowels:
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
    if has_footing_dowels:
        ax_bbs.plot([rx, rx - 0.035], [y_m_bot, y_m_bot], color="#dc2626", lw=3.2, zorder=4)
        ax_bbs.text(rx - 0.040, y_m_bot - 0.022, f"Foot={L_foot_val_cm:.0f}cm", ha="right", va="center", fontsize=7.2, color="#b91c1c", weight="bold")

    if not is_top_floor:
        ax_bbs.plot([rx, rx + 0.018], [y_m_col, y_m_col + 0.018], color="#dc2626", lw=3.2, zorder=4)
        ax_bbs.plot([rx + 0.018, rx + 0.018], [y_m_col + 0.018, y_m_top], color="#dc2626", lw=3.2, zorder=4)
    else:
        ax_bbs.plot([rx, rx + 0.05], [y_m_col, y_m_col], color="#dc2626", lw=3.2, zorder=4)

    ax_bbs.text(rx - 0.045, (y_m_bot + y_m_col) / 2.0, f"H={H_col_cm:.0f} cm", ha="right", va="center", fontsize=8.0, color="#64748b", rotation=90)

    tx = 0.20
    ax_bbs.text(tx, 0.795, f"• Main Bars:  {n_bars} Φ {phi_mm} mm  [{n_rows} Rows]", fontsize=9.5, weight="bold", color="#1e293b", zorder=3)
    
    cut_txt = f"• Cut Length (L_bar):  {L_bar_m:.2f} m ({L_bar_cm:.0f} cm)"
    if abs(L_bar_m - L_calc_m) > 0.005:
        cut_txt += f" [Specified: {L_bar_m:.2f}m]"
    ax_bbs.text(tx, 0.720, cut_txt, fontsize=9.8, weight="bold", color="#b91c1c", zorder=3)

    splice_txt = f"L_lap = {L_lap_cm:.0f} cm [{lap_factor:.0f}Φ]" if not is_top_floor else f"Top Hook = {L_hook_cm:.0f} cm"
    ax_bbs.text(tx, 0.645, f"• Splice / Hook:  {splice_txt}", fontsize=8.8, color="#334155", zorder=3)

    foot_txt = f"Foot Leg = {L_foot_val_cm:.0f} cm [12Φ Leg]" if has_footing_dowels else "Straight Bottom (بدون أشاير قواعد)"
    ax_bbs.text(tx, 0.575, f"• Footing Dowel:  {foot_txt}", fontsize=8.6, color="#047857" if has_footing_dowels else "#64748b", zorder=3)

    calc_breakdown = f"L = H({H_col_cm:.0f}) + ts({t_slab_cm:.0f}) + Lap({L_lap_cm if not is_top_floor else L_hook_cm:.0f})"
    if has_footing_dowels:
        calc_breakdown += f" + Foot({L_foot_val_cm:.0f})"
    ax_bbs.text(tx, 0.510, f"• Formula:  {calc_breakdown} = {L_calc_m:.2f} m", fontsize=8.0, color="#64748b", zorder=3)

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
    has_footing_dowels: bool = False,
    L_foot_cm: float = None,
    L_bar_custom_m: float = None,
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
    L_foot_val_cm = max(25.0, (12.0 * phi_mm) / 10.0) if L_foot_cm is None else L_foot_cm

    if not is_top_floor:
        L_calc_cm = H_col_cm + t_slab_cm + L_lap_cm + (L_foot_val_cm if has_footing_dowels else 0.0)
    else:
        L_calc_cm = H_col_cm + (t_slab_cm - cover) + L_hook_cm + (L_foot_val_cm if has_footing_dowels else 0.0)

    L_calc_m = L_calc_cm / 100.0

    if L_bar_custom_m is not None and L_bar_custom_m > 0:
        L_bar_m = float(L_bar_custom_m)
        L_bar_cm = L_bar_m * 100.0
    else:
        L_bar_cm = L_calc_cm
        L_bar_m = L_calc_m

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
    if has_footing_dowels:
        ax.plot([bx_left, bx_left + 0.20], [y_bot, y_bot], color="#dc2626", lw=2.8, zorder=4)
    
    ax.plot([bx_right, bx_right], [y_bot, y_slab_top], color="#dc2626", lw=2.8, zorder=4)
    if has_footing_dowels:
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
    if has_footing_dowels:
        ax_bbs.plot([rx, rx - 0.035], [y_m_bot, y_m_bot], color="#dc2626", lw=3.2, zorder=4)
        ax_bbs.text(rx - 0.040, y_m_bot - 0.022, f"Foot={L_foot_val_cm:.0f}cm", ha="right", va="center", fontsize=7.2, color="#b91c1c", weight="bold")

    if not is_top_floor:
        ax_bbs.plot([rx, rx + 0.018], [y_m_col, y_m_col + 0.018], color="#dc2626", lw=3.2, zorder=4)
        ax_bbs.plot([rx + 0.018, rx + 0.018], [y_m_col + 0.018, y_m_top], color="#dc2626", lw=3.2, zorder=4)
    else:
        ax_bbs.plot([rx, rx + 0.05], [y_m_col, y_m_col], color="#dc2626", lw=3.2, zorder=4)

    # Dimension ticks on rebar
    ax_bbs.text(rx - 0.045, (y_m_bot + y_m_col) / 2.0, f"H={H_col_cm:.0f} cm", ha="right", va="center", fontsize=8.0, color="#64748b", rotation=90)

    # Structured Text Rows - Part A
    tx = 0.20
    ax_bbs.text(tx, 0.795, f"• Main Bars:  {n_bars} Φ {phi_mm} mm  [{n_rows} Rows]", fontsize=9.5, weight="bold", color="#1e293b", zorder=3)
    
    cut_txt = f"• Cut Length (L_bar):  {L_bar_m:.2f} m ({L_bar_cm:.0f} cm)"
    if abs(L_bar_m - L_calc_m) > 0.005:
        cut_txt += f" [Specified: {L_bar_m:.2f}m]"
    ax_bbs.text(tx, 0.720, cut_txt, fontsize=9.8, weight="bold", color="#b91c1c", zorder=3)

    splice_txt = f"L_lap = {L_lap_cm:.0f} cm [{lap_factor:.0f}Φ]" if not is_top_floor else f"Top Hook = {L_hook_cm:.0f} cm"
    ax_bbs.text(tx, 0.645, f"• Splice / Hook:  {splice_txt}", fontsize=8.8, color="#334155", zorder=3)

    foot_txt = f"Foot Leg = {L_foot_val_cm:.0f} cm [12Φ Leg]" if has_footing_dowels else "Straight Bottom (بدون أشاير قواعد)"
    ax_bbs.text(tx, 0.575, f"• Footing Dowel:  {foot_txt}", fontsize=8.6, color="#047857" if has_footing_dowels else "#64748b", zorder=3)

    calc_breakdown = f"L = H({H_col_cm:.0f}) + ts({t_slab_cm:.0f}) + Lap({L_lap_cm if not is_top_floor else L_hook_cm:.0f})"
    if has_footing_dowels:
        calc_breakdown += f" + Foot({L_foot_val_cm:.0f})"
    ax_bbs.text(tx, 0.510, f"• Formula:  {calc_breakdown} = {L_calc_m:.2f} m", fontsize=8.0, color="#64748b", zorder=3)

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
        ax_bbs.plot([sx + 0.02 + 0.022, sx + 0.02], [sy_in + sh_in - 0.02, sy_in + sh_in - 0.040], color="#059669", lw=1.8, zorder=6)

    # Stirrup dimension labels
    ax_bbs.text(sx + sw / 2, sy - 0.022, f"b' = {b_core:.0f} cm", ha="center", va="top", fontsize=8.2, weight="bold", color="#166534")
    ax_bbs.text(sx + sw + 0.015, sy + sh / 2, f"t' = {t_core:.0f} cm", ha="left", va="center", fontsize=8.2, weight="bold", color="#166534", rotation=90)

    st_tx = 0.36
    ax_bbs.text(st_tx, 0.385, f"• Tie Type:  {tie_title_str}", fontsize=9.2, weight="bold", color="#1e293b", zorder=3)
    ax_bbs.text(st_tx, 0.315, f"• Cut Length (L_tie):  {L_tie_m:.2f} m ({L_tie_cm:.0f} cm)", fontsize=9.8, weight="bold", color="#15803d", zorder=3)
    ax_bbs.text(st_tx, 0.245, f"• Size & Spacing:  Φ {phi_st_mm} mm @ {n_st_per_m} / m' (S={100.0/n_st_per_m:.0f} cm)", fontsize=8.8, color="#1e293b", zorder=3)
    ax_bbs.text(st_tx, 0.175, f"• Dimensions:  {b_core:.0f} × {t_core:.0f} cm  (Hook: {hook_len_cm:.0f} cm)", fontsize=8.5, color="#334155", zorder=3)
    ax_bbs.text(st_tx, 0.105, f"• Total Ties / Col:  {n_ties_per_col} Ties / Column", fontsize=9.0, weight="bold", color="#1e293b", zorder=3)
    ax_bbs.text(st_tx, 0.045, f"• Total Length:  {n_ties_per_col * L_tie_m:.1f} m' per column", fontsize=8.2, color="#64748b", zorder=3)

    fig.tight_layout()
    return fig


def draw_flat_slab_survey_sheet(
    lx_m: float,
    ly_m: float,
    ts_cm: float,
    phi_btm_x: int = 12,
    phi_btm_y: int = 12,
    phi_top_x: int = 10,
    phi_top_y: int = 10,
    nb_x: int = 6,
    nb_y: int = 6,
    nb_top_x: Optional[int] = None,
    nb_top_y: Optional[int] = None,
    name: str = "S1",
    n_rep: int = 1,
    add_top_lx: float = 0.0,
    add_top_ly: float = 0.0,
    n_top_add_x: int = 0,
    n_top_add_y: int = 0,
    phi_top_add: int = 12,
    add_btm_lx: float = 0.0,
    add_btm_ly: float = 0.0,
    n_btm_add_x: int = 0,
    n_btm_add_y: int = 0,
    phi_btm_add: int = 12,
    top_add_models: Optional[List[Dict]] = None,
    btm_add_models: Optional[List[Dict]] = None,
) -> plt.Figure:
    """
    Renders a unified, full-width 3-Panel CAD Drawing Sheet for the Flat Slab:
      1. Horizontal Plan View (المسقط الأفقي وتوزيع شبكتي التسليح السفلية والعلوية والحديد الإضافي)
      2. Cross Section Elevation (القطاع الرأسي وتفاصيل تخانة البلاطة والكراسي الحاملة)
      3. Bar Bending Schedule - BBS (جدول تفريد حديد التسليح والأطوال والأوزان وحجم الخرسانة)
    """
    nb_tx = nb_top_x if nb_top_x is not None else 6
    nb_ty = nb_top_y if nb_top_y is not None else 6
    nb_bx = nb_x
    nb_by = nb_y

    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"]
    fig = plt.figure(figsize=(19.0, 6.8), dpi=140, facecolor="#ffffff")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 0.95, 0.90], wspace=0.18)

    ax_plan = fig.add_subplot(gs[0, 0])
    ax_sec = fig.add_subplot(gs[0, 1])
    ax_bbs = fig.add_subplot(gs[0, 2])

    ax_plan.set_facecolor("#ffffff")
    ax_sec.set_facecolor("#ffffff")
    ax_bbs.set_facecolor("#ffffff")

    # Additional rebar processing for multi-model (per linear meter density)
    w_add_tot = 0.0
    top_add_lines = []
    btm_add_lines = []

    if top_add_models:
        for tm in top_add_models:
            t_name = tm.get("name", "T1")
            t_phi = int(tm.get("phi", 12))
            t_lx = float(tm.get("lx", 0.0))
            t_ly = float(tm.get("ly", 0.0))
            t_nx_m = float(tm.get("nx", 0))
            t_ny_m = float(tm.get("ny", 0))
            t_nz = int(tm.get("n_zones", 1))
            n_rx = int(math.ceil(t_ly * t_nx_m)) if (t_nx_m > 0 and t_ly > 0) else 0
            n_ry = int(math.ceil(t_lx * t_ny_m)) if (t_ny_m > 0 and t_lx > 0) else 0
            w_x = n_rx * t_nz * t_lx * ((t_phi ** 2) / 162.0) * n_rep if (n_rx > 0 and t_lx > 0) else 0.0
            w_y = n_ry * t_nz * t_ly * ((t_phi ** 2) / 162.0) * n_rep if (n_ry > 0 and t_ly > 0) else 0.0
            w_m = w_x + w_y
            w_add_tot += w_m
            if w_m > 0:
                top_add_lines.append(f"Top Add [{t_name}]: {n_rx*t_nz*n_rep}pcs ({t_nx_m:.0f}Φ{t_phi}/m') + {n_ry*t_nz*n_rep}pcs ({t_ny_m:.0f}Φ{t_phi}/m') = {w_m:.1f}kg")
    else:
        w_tax = n_top_add_x * add_top_lx * ((phi_top_add ** 2) / 162.0) * n_rep if (n_top_add_x > 0 and add_top_lx > 0) else 0.0
        w_tay = n_top_add_y * add_top_ly * ((phi_top_add ** 2) / 162.0) * n_rep if (n_top_add_y > 0 and add_top_ly > 0) else 0.0
        w_add_tot += (w_tax + w_tay)
        if (w_tax + w_tay) > 0:
            top_add_lines.append(f"Top Add: {n_top_add_x*n_rep}Φ{phi_top_add}(X) + {n_top_add_y*n_rep}Φ{phi_top_add}(Y) = {w_tax+w_tay:.1f}kg")

    if btm_add_models:
        for bm in btm_add_models:
            b_name = bm.get("name", "B1")
            b_phi = int(bm.get("phi", 12))
            b_lx = float(bm.get("lx", 0.0))
            b_ly = float(bm.get("ly", 0.0))
            b_nx_m = float(bm.get("nx", 0))
            b_ny_m = float(bm.get("ny", 0))
            b_nz = int(bm.get("n_zones", 1))
            n_rx = int(math.ceil(b_ly * b_nx_m)) if (b_nx_m > 0 and b_ly > 0) else 0
            n_ry = int(math.ceil(b_lx * b_ny_m)) if (b_ny_m > 0 and b_lx > 0) else 0
            w_x = n_rx * b_nz * b_lx * ((b_phi ** 2) / 162.0) * n_rep if (n_rx > 0 and b_lx > 0) else 0.0
            w_y = n_ry * b_nz * b_ly * ((b_phi ** 2) / 162.0) * n_rep if (n_ry > 0 and b_ly > 0) else 0.0
            w_m = w_x + w_y
            w_add_tot += w_m
            if w_m > 0:
                btm_add_lines.append(f"Btm Add [{b_name}]: {n_rx*b_nz*n_rep}pcs ({b_nx_m:.0f}Φ{b_phi}/m') + {n_ry*b_nz*n_rep}pcs ({b_ny_m:.0f}Φ{b_phi}/m') = {w_m:.1f}kg")
    else:
        w_bax = n_btm_add_x * add_btm_lx * ((phi_btm_add ** 2) / 162.0) * n_rep if (n_btm_add_x > 0 and add_btm_lx > 0) else 0.0
        w_bay = n_btm_add_y * add_btm_ly * ((phi_btm_add ** 2) / 162.0) * n_rep if (n_btm_add_y > 0 and add_btm_ly > 0) else 0.0
        w_add_tot += (w_bax + w_bay)
        if (w_bax + w_bay) > 0:
            btm_add_lines.append(f"Btm Add: {n_btm_add_x*n_rep}Φ{phi_btm_add}(X) + {n_btm_add_y*n_rep}Φ{phi_btm_add}(Y) = {w_bax+w_bay:.1f}kg")

    # 1. PLAN VIEW
    ax_plan.set_title(f"1. Plan View: Flat Slab [{name}] ({lx_m:.2f} × {ly_m:.2f} m — ts={ts_cm:.0f}cm)", fontsize=13, fontweight="bold", color="#1e3a8a", pad=12)
    rect = patches.Rectangle((0, 0), lx_m, ly_m, facecolor="#f8fafc", edgecolor="#1e3a8a", linewidth=2.5, zorder=1)
    ax_plan.add_patch(rect)

    # Grid rebar lines (Blue bottom, Green top)
    n_lines_y = min(12, max(4, int(ly_m * 1.5)))
    for y_pos in np.linspace(0.4, ly_m - 0.4, n_lines_y):
        ax_plan.plot([0.2, lx_m - 0.2], [y_pos, y_pos], color="#2563eb", linestyle="-", linewidth=1.2, alpha=0.70, zorder=2)
    
    n_lines_x = min(14, max(4, int(lx_m * 1.5)))
    for x_pos in np.linspace(0.4, lx_m - 0.4, n_lines_x):
        ax_plan.plot([x_pos, x_pos], [0.2, ly_m - 0.2], color="#1d4ed8", linestyle="-", linewidth=1.2, alpha=0.70, zorder=2)

    # Rebar callout text inside slab
    ax_plan.text(lx_m * 0.5, ly_m * 0.65, f"Bottom Mesh (B1, B2)\nB1: {nb_bx} Φ{phi_btm_x} mm/m' (Dir X)\nB2: {nb_by} Φ{phi_btm_y} mm/m' (Dir Y)",
                 ha="center", va="center", fontsize=10.0, fontweight="bold", color="#1e3a8a",
                 bbox=dict(boxstyle="round,pad=0.4", facecolor="#dbeafe", edgecolor="#3b82f6", linewidth=1.3, alpha=0.92), zorder=4)

    ax_plan.text(lx_m * 0.5, ly_m * 0.35, f"Top Mesh (T1, T2)\nT1: {nb_tx} Φ{phi_top_x} mm/m' (Dir X)\nT2: {nb_ty} Φ{phi_top_y} mm/m' (Dir Y)",
                 ha="center", va="center", fontsize=10.0, fontweight="bold", color="#15803d",
                 bbox=dict(boxstyle="round,pad=0.4", facecolor="#dcfce7", edgecolor="#22c55e", linewidth=1.3, alpha=0.92), zorder=4)

    # Additional rebar annotations if present
    add_notes = []
    if top_add_lines:
        add_notes.append(" | ".join(top_add_lines[:2]))
    if btm_add_lines:
        add_notes.append(" | ".join(btm_add_lines[:2]))
    if add_notes:
        ax_plan.text(lx_m * 0.5, ly_m * 0.12, "\n".join(add_notes),
                     ha="center", va="center", fontsize=8.5, fontweight="bold", color="#9a3412",
                     bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffedd5", edgecolor="#ea580c", linewidth=1.2, alpha=0.95), zorder=5)

    # Dimensions
    dim_off = max(0.5, ly_m * 0.08)
    ax_plan.annotate("", xy=(lx_m, -dim_off), xytext=(0, -dim_off),
                     arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.8))
    ax_plan.text(lx_m * 0.5, -dim_off * 1.4, f"Lx = {lx_m:.2f} m", ha="center", va="top", fontsize=11, fontweight="bold", color="#0f172a")

    dim_off_x = max(0.5, lx_m * 0.08)
    ax_plan.annotate("", xy=(-dim_off_x, ly_m), xytext=(-dim_off_x, 0),
                     arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.8))
    ax_plan.text(-dim_off_x * 1.4, ly_m * 0.5, f"Ly = {ly_m:.2f} m", ha="right", va="center", fontsize=11, fontweight="bold", color="#0f172a", rotation=90)

    ax_plan.set_xlim(-dim_off_x * 2.2, lx_m + dim_off_x * 0.8)
    ax_plan.set_ylim(-dim_off * 2.5, ly_m + dim_off * 0.8)
    ax_plan.set_aspect("equal", adjustable="datalim")
    ax_plan.axis("off")

    # 2. CROSS SECTION ELEVATION
    ax_sec.set_title(f"2. Cross Section (ts = {ts_cm:.0f} cm)", fontsize=13, fontweight="bold", color="#1e3a8a", pad=12)
    sec_w = 100.0
    sec_h = ts_cm
    cov_sec = 2.0

    # Concrete block
    sec_rect = patches.Rectangle((0, 0), sec_w, sec_h, facecolor="#f1f5f9", edgecolor="#334155", linewidth=2.0, zorder=1)
    ax_sec.add_patch(sec_rect)

    # Bottom rebar layer
    y_b1 = cov_sec + (phi_btm_x / 20.0)
    ax_sec.plot([2, sec_w - 2], [y_b1, y_b1], color="#2563eb", linewidth=2.5, zorder=2)
    y_b2 = y_b1 + (phi_btm_y / 10.0)
    for x_c in np.linspace(8, sec_w - 8, 8):
        c_b2 = patches.Circle((x_c, y_b2), (phi_btm_y / 20.0), facecolor="#1d4ed8", edgecolor="#0f172a", linewidth=1.0, zorder=3)
        ax_sec.add_patch(c_b2)

    # Top rebar layer
    y_t1 = sec_h - cov_sec - (phi_top_x / 20.0)
    ax_sec.plot([2, sec_w - 2], [y_t1, y_t1], color="#16a34a", linewidth=2.5, zorder=2)
    y_t2 = y_t1 - (phi_top_y / 10.0)
    for x_c in np.linspace(8, sec_w - 8, 8):
        c_t2 = patches.Circle((x_c, y_t2), (phi_top_y / 20.0), facecolor="#15803d", edgecolor="#0f172a", linewidth=1.0, zorder=3)
        ax_sec.add_patch(c_t2)

    # Rebar Chair sketch in the middle
    ch_x = sec_w * 0.5
    ch_top = y_t2 - (phi_top_y / 20.0)
    ch_btm = y_b1
    ax_sec.plot([ch_x - 12, ch_x - 6, ch_x + 6, ch_x + 12],
                [ch_btm, ch_top, ch_top, ch_btm],
                color="#ea580c", linewidth=2.0, linestyle="-", zorder=2)
    ax_sec.text(ch_x, (ch_top + ch_btm) * 0.5, f"Chair Φ10\n(كرسي حامل)", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#c2410c",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffedd5", edgecolor="#f97316", linewidth=1.0), zorder=4)

    # Annotations
    ax_sec.text(sec_w + 4, y_t1, f"Top Mesh: {nb_tx}Φ{phi_top_x} + {nb_ty}Φ{phi_top_y}", va="center", fontsize=9.5, fontweight="bold", color="#15803d")
    ax_sec.text(sec_w + 4, y_b1, f"Btm Mesh: {nb_bx}Φ{phi_btm_x} + {nb_by}Φ{phi_btm_y}", va="center", fontsize=9.5, fontweight="bold", color="#1d4ed8")
    ax_sec.text(sec_w + 4, sec_h * 0.5, f"Cover = 2.0 cm", va="center", fontsize=9.0, color="#64748b")

    # Thickness dimension
    ax_sec.annotate("", xy=(-6, sec_h), xytext=(-6, 0), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.5))
    ax_sec.text(-9, sec_h * 0.5, f"ts = {ts_cm:.0f} cm", ha="right", va="center", fontsize=10.5, fontweight="bold", color="#0f172a", rotation=90)

    ax_sec.set_xlim(-20, sec_w + 55)
    ax_sec.set_ylim(-8, sec_h + 8)
    ax_sec.set_aspect("auto")
    ax_sec.axis("off")

    # 3. BBS & QUANTITY SUMMARY
    ax_bbs.set_title(f"3. Bar Bending Schedule (BBS)", fontsize=13, fontweight="bold", color="#1e3a8a", pad=12)

    vol_m3 = lx_m * ly_m * (ts_cm / 100.0) * n_rep
    area_m2 = lx_m * ly_m * n_rep
    n_bx = int(math.ceil(ly_m * nb_bx))
    n_by = int(math.ceil(lx_m * nb_by))
    n_tx = int(math.ceil(ly_m * nb_tx))
    n_ty = int(math.ceil(lx_m * nb_ty))
    w_bx = n_bx * (lx_m + 0.20) * ((phi_btm_x ** 2) / 162.0) * n_rep
    w_by = n_by * (ly_m + 0.20) * ((phi_btm_y ** 2) / 162.0) * n_rep
    w_tx = n_tx * (lx_m + 0.20) * ((phi_top_x ** 2) / 162.0) * n_rep
    w_ty = n_ty * (ly_m + 0.20) * ((phi_top_y ** 2) / 162.0) * n_rep

    tot_st_kg = w_bx + w_by + w_tx + w_ty + w_add_tot
    tot_st_ton = tot_st_kg / 1000.0
    st_rate = (tot_st_kg / vol_m3) if vol_m3 > 0 else 0.0

    bbs_lines = [
        f"• Slab Name: {name} (Count = {n_rep})",
        f"• Dimensions: {lx_m:.2f} × {ly_m:.2f} m | Area = {area_m2:.1f} m²",
        f"• Concrete Vol: {vol_m3:.2f} m³ (ts = {ts_cm:.0f} cm)",
        "--------------------------------------------------",
        f"1. Btm Rebar X: {n_bx*n_rep} pcs Φ{phi_btm_x} (L={(lx_m+0.20):.2f}m) = {w_bx:.1f} kg",
        f"2. Btm Rebar Y: {n_by*n_rep} pcs Φ{phi_btm_y} (L={(ly_m+0.20):.2f}m) = {w_by:.1f} kg",
        f"3. Top Rebar X: {n_tx*n_rep} pcs Φ{phi_top_x} (L={(lx_m+0.20):.2f}m) = {w_tx:.1f} kg",
        f"4. Top Rebar Y: {n_ty*n_rep} pcs Φ{phi_top_y} (L={(ly_m+0.20):.2f}m) = {w_ty:.1f} kg",
    ]
    for tal in top_add_lines[:2]:
        bbs_lines.append(f"5. {tal}")
    for bal in btm_add_lines[:2]:
        bbs_lines.append(f"6. {bal}")

    bbs_lines.extend([
        "--------------------------------------------------",
        f"★ Total Steel: {tot_st_ton:.3f} Ton ({tot_st_kg:.1f} kg)",
        f"★ Steel Consumption: {st_rate:.1f} kg/m³",
    ])

    for idx, line in enumerate(bbs_lines):
        is_highlight = line.startswith("★")
        txt_color = "#1e3a8a" if is_highlight else ("#0f172a" if not line.startswith("•") else "#334155")
        weight = "bold" if (is_highlight or line.startswith("•") or "Total" in line) else "normal"
        size = 11.0 if is_highlight else 9.5
        ax_bbs.text(0.04, 0.94 - idx * 0.072, line, fontsize=size, fontweight=weight, color=txt_color, va="center", transform=ax_bbs.transAxes)

    ax_bbs.axis("off")
    fig.tight_layout()
    return fig





# ═══════════════════════════════════════════════════════════════════════════
# 2. MAIN RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def _generate_alarm_wav_b64() -> str:
    """Generates a multi-tone engineering warning alarm sound as base64 WAV."""
    sample_rate = 22050
    beeps = [(920, 0.14), (0, 0.06), (920, 0.14), (0, 0.06), (1200, 0.24)]
    samples = []
    for freq, dur in beeps:
        n_samples = int(sample_rate * dur)
        for i in range(n_samples):
            if freq == 0:
                samples.append(0.0)
            else:
                t = float(i) / sample_rate
                env = math.sin(math.pi * (i / n_samples))
                samples.append(env * math.sin(2.0 * math.pi * freq * t))
    wav_io = io.BytesIO()
    with wave.open(wav_io, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        int_s = [int(s * 32767 * 0.85) for s in samples]
        f.writeframes(struct.pack("<" + "h" * len(int_s), *int_s))
    return base64.b64encode(wav_io.getvalue()).decode("ascii")


if hasattr(st, "dialog"):
    @st.dialog("⚠️ تحذير هندسي: طول القطع أقل من الكود المصري (ECP 203)")
    def _warn_short_cut_dialog(short_models: list, total_types: int = 4):
        # Audible Alarm: Web Audio API Oscillator + HTML5 Audio Autoplay
        try:
            alarm_b64 = _generate_alarm_wav_b64()
            audio_html = (
                '<audio autoplay style="display:none;">'
                + f'<source src="data:audio/wav;base64,{alarm_b64}" type="audio/wav">'
                + '</audio>'
                + """
                <script>
                (function() {
                    try {
                        var AudioCtx = window.AudioContext || window.webkitAudioContext || (window.parent && (window.parent.AudioContext || window.parent.webkitAudioContext));
                        if (AudioCtx) {
                            var ctx = new AudioCtx();
                            if (ctx.state === 'suspended') ctx.resume();
                            function playTone(freq, start, duration, type) {
                                var osc = ctx.createOscillator();
                                var gain = ctx.createGain();
                                osc.type = type || 'sawtooth';
                                osc.frequency.setValueAtTime(freq, start);
                                gain.gain.setValueAtTime(0.001, start);
                                gain.gain.linearRampToValueAtTime(0.35, start + 0.02);
                                gain.gain.exponentialRampToValueAtTime(0.001, start + duration);
                                osc.connect(gain);
                                gain.connect(ctx.destination);
                                osc.start(start);
                                osc.stop(start + duration);
                            }
                            var now = ctx.currentTime;
                            playTone(920, now, 0.15, 'sawtooth');
                            playTone(920, now + 0.20, 0.15, 'sawtooth');
                            playTone(1200, now + 0.40, 0.28, 'triangle');
                        }
                    } catch(e) {
                        console.log("Audio alarm notice:", e);
                    }
                })();
                </script>
                """
            )
            components.html(audio_html, height=0, width=0)
        except Exception:
            pass

        # Build table rows for all affected models
        warning_rows = []
        user_val = short_models[0]["user_cut_m"] if short_models else 0.0
        for m in short_models:
            warning_rows.append({
                "نموذج العمود": f"🏛️ نموذج ({m['name']})",
                "القطر": f"Φ{m.get('phi', 16)} mm",
                "طول القطع المدخل": f"{m['user_cut_m']:.2f} m'",
                "المطلوب بالكود": f"{m['calc_cut_m']:.2f} m'",
                "مقدار النقص والعجز": f"-{m['diff_cm']:.0f} cm (عجز {m['diff_cm']/100:.2f}م)",
            })

        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg, #450a0a 0%, #1e1b4b 100%); border:2px solid #ef4444; border-right:8px solid #dc2626; padding:16px 20px; border-radius:12px; margin-bottom:14px; box-shadow:0 6px 25px rgba(220,38,38,0.30);">
                <div style="font-size:21px; font-weight:900; color:#fca5a5; margin-bottom:6px; display:flex; align-items:center; gap:10px;">
                    <span style="font-size:26px;">🚨</span>
                    <span>صفارة إنذار: طول السيخ المختار أقل من الكود لـ ({len(short_models)}) نماذج أعمدة!</span>
                </div>
                <div style="font-size:16px; color:#fecaca; line-height:1.6;">
                    لقد قمت باختيار طول تقطيع موحد <b style="color:#ffffff; font-size:18px;" dir="ltr">{user_val:.2f} m'</b>، وهو <b style="color:#f87171;">أقل من الحد الأدنى المطلوب هندسياً</b> طبقاً للكود المصري (ECP 203) في النماذج الموضحة بالجدول أدناه:
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_styled_table(
            warning_rows,
            accent_border_color="#ef4444",
            col_colors=["#ffffff", "#38bdf8", "#f87171", "#4ade80", "#f87171"],
        )
        st.warning("⚠️ تنبيه هندسي: تقليل طول السيخ عن الحد المحسوب سيؤدي إلى نقص مباشر في طول وصلة التراكب (L_lap) أو الأشاير طبقاً لـ ECP 203.")
        st.markdown("<div style='font-size:15.5px; font-weight:700; color:#1e293b; margin-bottom:12px;'>هل ترغب في الاستمرار واعتماد هذا الطول المخصص لكافة النماذج على مسؤوليتك؟</div>", unsafe_allow_html=True)
        
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("✅ موافق (OK — استمرار بالتصميم لكافة النماذج)", type="primary", use_container_width=True, key="dlg_ok_cut_all"):
                for k in range(total_types):
                    st.session_state[f"cs_cut_length_{k}"] = float(user_val)
                    st.session_state[f"cs_cut_confirmed_{k}"] = float(user_val)
                st.rerun()
        with btn_c2:
            if st.button("❌ تراجع واستعادة الطول المحسوب لكل نموذج", use_container_width=True, key="dlg_cancel_cut_all"):
                for k in range(total_types):
                    st.session_state.pop(f"cs_cut_length_{k}", None)
                    st.session_state.pop(f"cs_cut_confirmed_{k}", None)
                    st.session_state.pop(f"_last_cut_calc_key_{k}", None)
                st.rerun()


if hasattr(st, "dialog"):
    @st.dialog("⚠️ تحذير هندسي: إجهاد الخرسانة أقل من الحد القياسي (350 kg/cm²)")
    def _warn_low_fcu_dialog(fcu_val: float):
        # Audible Alarm: Web Audio API Oscillator + HTML5 Audio Autoplay
        try:
            alarm_b64 = _generate_alarm_wav_b64()
            audio_html = (
                '<audio autoplay style="display:none;">'
                + f'<source src="data:audio/wav;base64,{alarm_b64}" type="audio/wav">'
                + '</audio>'
                + """
                <script>
                (function() {
                    try {
                        var AudioCtx = window.AudioContext || window.webkitAudioContext || (window.parent && (window.parent.AudioContext || window.parent.webkitAudioContext));
                        if (AudioCtx) {
                            var ctx = new AudioCtx();
                            if (ctx.state === 'suspended') ctx.resume();
                            function playTone(freq, start, duration, type) {
                                var osc = ctx.createOscillator();
                                var gain = ctx.createGain();
                                osc.type = type || 'sawtooth';
                                osc.frequency.setValueAtTime(freq, start);
                                gain.gain.setValueAtTime(0.001, start);
                                gain.gain.linearRampToValueAtTime(0.35, start + 0.02);
                                gain.gain.exponentialRampToValueAtTime(0.001, start + duration);
                                osc.connect(gain);
                                gain.connect(ctx.destination);
                                osc.start(start);
                                osc.stop(start + duration);
                            }
                            var now = ctx.currentTime;
                            playTone(920, now, 0.15, 'sawtooth');
                            playTone(920, now + 0.20, 0.15, 'sawtooth');
                            playTone(1200, now + 0.40, 0.28, 'triangle');
                        }
                    } catch(e) {
                        console.log("Audio alarm notice:", e);
                    }
                })();
                </script>
                """
            )
            components.html(audio_html, height=0, width=0)
        except Exception:
            pass

        st.markdown(
            f"""
            <div style="background:#fef2f2; border:2px solid #ef4444; border-right:8px solid #dc2626; padding:16px 18px; border-radius:10px; margin-bottom:14px; box-shadow:0 4px 14px rgba(220,38,38,0.15);">
                <div style="font-size:19px; font-weight:800; color:#991b1b; margin-bottom:8px; display:flex; align-items:center; gap:10px;">
                    <span style="font-size:26px;">🚨</span>
                    <span>صفارة إنذار: إجهاد الخرسانة المدخل أقل من الحد القياسي ({fcu_val:.0f} kg/cm²)!</span>
                </div>
                <div style="font-size:15.5px; color:#7f1d1d; line-height:1.7;">
                    لقد قمت بإدخال إجهاد خرسانة <b style="color:#b91c1c; font-size:18px;" dir="ltr">{fcu_val:.0f} kg/cm²</b>، وهو <b>أقل من الإجهاد القياسي للخرسانة المسلحة</b> <b style="color:#15803d; font-size:18px;" dir="ltr">(350 kg/cm²)</b>.<br>
                    <span style="color:#991b1b; font-weight:700;">💡 تنبيه: تقليل رتبة الخرسانة يقلل من مقاومة الضغط للأعمدة الخرسانية ويتطلب زيادة قطاعات الأعمدة أو زيادة نسبة حديد التسليح لتعويض نقص المقاومة طبقاً لـ ECP 203.</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.warning("⚠️ هل ترغب في الاستمرار واعتماد إجهاد الخرسانة المخفض على مسؤوليتك الإنشائية؟")
        
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("✅ موافق (OK — استمرار بالتصميم على هذا الإجهاد)", type="primary", use_container_width=True, key="dlg_ok_fcu"):
                st.session_state["cs_fcu_confirmed"] = float(fcu_val)
                st.session_state["cs_fcu"] = float(fcu_val)
                st.rerun()
        with btn_c2:
            if st.button("❌ تراجع واستعادة الإجهاد القياسي (350 kg/cm²)", use_container_width=True, key="dlg_cancel_fcu"):
                st.session_state["cs_fcu"] = 350.0
                st.session_state["cs_fcu_confirmed"] = 350.0
                st.rerun()


def render() -> None:
    st.markdown(
        '<div class="section-header">📊 Module 6 – Concrete Quantity Survey & Take-off (ECP 203)</div>',
        unsafe_allow_html=True,
    )

    # ── Project Info Panel (اسم المشروع في بانيل مميز بالمنتصف) ─────────────
    col_p_pad1, col_p_center, col_p_pad2 = st.columns([0.6, 6.8, 0.6])
    with col_p_center:
        project_name_in = text_input(
            "اسم المشروع (Project Name)",
            cfg_key="cs_project_name",
            help="اسم المشروع الذي سيظهر في ترويسة تقارير الطباعة وملفات الـ PDF وبطاقة المشروع",
        )

    # Global Styling for ALL tabs across the module
    st.markdown(
        """
        <style>
        /* Enlarged typography for ALL Tabs across Concrete Survey module */
        div[data-testid="stTabs"] button[data-testid="stTab"] {
            font-size: 1.30rem !important;
            font-weight: 800 !important;
            padding: 10px 22px !important;
            border-radius: 8px 8px 0 0 !important;
        }
        div[data-testid="stTabs"] button[data-testid="stTab"] p {
            font-size: 1.30rem !important;
            font-weight: 800 !important;
            line-height: 1.4 !important;
        }
        div[data-testid="stTabs"] button[data-testid="stTab"][aria-selected="true"] {
            color: #1e3a8a !important;
            border-bottom: 4px solid #2563eb !important;
            background: rgba(37, 99, 235, 0.08) !important;
        }
        div[data-testid="stTabs"] button[data-testid="stTab"][aria-selected="true"] p {
            color: #1e3a8a !important;
            font-weight: 900 !important;
        }
        div[data-testid="stTabs"] button[data-testid="stTab"]:hover {
            color: #2563eb !important;
            background: rgba(37, 99, 235, 0.04) !important;
        }
        </style>
        """,
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
        cover_cm = 2.5

        # Framed Inputs Container (برواز بلون هندسي مميز ومتقن للمدخلات)
        with st.container(border=True):

            st.markdown(
                """
                <style>
                /* Distinctive Custom Colored Frame for Inputs */
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge) {
                    border: 2px solid #38bdf8 !important;
                    border-radius: 10px !important;
                    background: linear-gradient(180deg, #0b1329 0%, #1e293b 100%) !important;
                    padding: 10px 14px !important;
                    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.40) !important;
                }
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge):hover {
                    border-color: #60a5fa !important;
                    box-shadow: 0 6px 18px rgba(56, 189, 248, 0.25) !important;
                }
                /* Increase label font size by 1.25x (عناوين المدخلات) */
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge) label p {
                    font-size: 1.15rem !important;
                    font-weight: 700 !important;
                    color: #fde047 !important;
                    line-height: 1.30 !important;
                }
                /* Increase input values/numbers font size by 1.25x (قيم المدخلات) */
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.cs-inputs-header-badge) input {
                    font-size: 1.22rem !important;
                    font-weight: 800 !important;
                    padding: 6px 10px !important;
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
                <div class="cs-inputs-header-badge input-section-header" style="margin-bottom: 12px;">
                    <span style="font-size:24px;">📥</span>
                    <span>مدخلات قطاعات وتسليح نماذج الأعمدة (Multi-Column Types Survey Inputs)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ── SECTION A: COMMON PROJECT / FLOOR PARAMETERS ──
            st.markdown("<div style='font-size:14.5px; font-weight:800; color:#1e3a8a; margin-bottom:4px;'>📌 1. المدخلات العامة المشتركة لسقف/دور المشروع (Shared Floor & Project Specs)</div>", unsafe_allow_html=True)

            # Persistent Defaults from user_settings.json
            def_n_types = int(cfg_val("cs_n_types", 2))
            def_col_h = float(cfg_val("cs_col_h", 300.0))
            def_t_slab = float(cfg_val("cs_t_slab", 20.0))
            def_fcu = float(cfg_val("cs_fcu", 350.0))
            def_is_top_floor_idx = int(cfg_val("cs_is_top_floor_idx", 0))
            def_has_footing_dowels_idx = int(cfg_val("cs_has_footing_dowels_idx", 0))
            def_lap_factor_idx = int(cfg_val("cs_lap_factor_idx", 2))
            def_n_st_m = int(cfg_val("cs_n_st_m", 6))
            def_phi_st_idx = int(cfg_val("cs_phi_st_idx", 1))

            col_g1, col_g2, col_g3, col_g4 = st.columns(4)
            with col_g1:
                n_types_in = st.number_input(
                    "عدد أنواع / نماذج الأعمدة بالمشروع",
                    min_value=1, max_value=15, value=def_n_types, step=1,
                    help="إجمالي عدد النماذج المختلفة للأعمدة بالمشروع (مثل: C1، C2، C3...)",
                    key="cs_n_types",
                )
            with col_g2:
                col_h_in = st.number_input(
                    "ارتفاع العمود الصافي H (cm)",
                    min_value=50.0, max_value=2000.0, value=def_col_h, step=10.0,
                    help="ارتفاع العمود الخالص الصافي من وش الخرسانة لبطنية السقف (Default 300 cm)",
                    key="cs_col_h",
                )
            with col_g3:
                t_slab_in = st.number_input(
                    "تخانة البلاطة والكمرات (cm)",
                    min_value=5.0, max_value=200.0, value=def_t_slab, step=1.0,
                    help="تخانة البلاطة أو سقوط الكمرة أعلى العمود الخرساني (Default 20 cm)",
                    key="cs_t_slab",
                )
            with col_g4:
                fcu_in = st.number_input(
                    "إجهاد الخرسانة fcu (kg/cm²)",
                    min_value=150.0, max_value=800.0, value=def_fcu, step=25.0,
                    help="إجهاد الخرسانة المميز للضغط بعد 28 يوماً (الافتراضي 350 kg/cm² للخرسانة المسلحة)",
                    key="cs_fcu",
                )

            # Pop-up check if user enters fcu < 350 kg/cm²
            is_low_fcu = (fcu_in < 350.0 - 0.1)
            confirmed_fcu_val = st.session_state.get("cs_fcu_confirmed")
            if is_low_fcu and (confirmed_fcu_val != fcu_in):
                if hasattr(st, "dialog"):
                    _warn_low_fcu_dialog(fcu_in)
            elif not is_low_fcu:
                st.session_state["cs_fcu_confirmed"] = fcu_in

            col_g5, col_g6, col_g7, col_g8 = st.columns(4)
            with col_g5:
                is_top_floor_sel = st.radio(
                    "عمود دور أخير؟ (Top Floor)",
                    options=["No (متكرر / وصلة Llap)", "Yes (دور أخير / جنش Lhook)"],
                    index=max(0, min(def_is_top_floor_idx, 1)),
                    horizontal=True,
                    help="إذا كانت No يتم حساب وصلة Llap أعلى البلاطة، وإذا كانت Yes يتم حساب جنش/رجل أعلى البلاطة",
                    key="cs_is_top_floor",
                )
            with col_g6:
                has_footing_dowels_sel = st.radio(
                    "هل توجد أشاير للقواعد؟",
                    options=["No (لا توجد / سيخ مستقيم)", "Yes (أشاير قواعد / رجل أفقية)"],
                    index=max(0, min(def_has_footing_dowels_idx, 1)),
                    horizontal=True,
                    help="إذا كان No يكون السيخ مستقيماً من الأسفل ولا تُرسم الرجل الأفقية، وإذا كان Yes يتم رسم وحساب الرجل الأفقية",
                    key="cs_has_footing_dowels",
                )
            with col_g7:
                lap_factor_sel = st.selectbox(
                    "معامل طول الوصلة / الجنش (Llap)",
                    options=[40, 45, 50, 60],
                    index=max(0, min(def_lap_factor_idx, 3)),
                    format_func=lambda x: f"{x} Φ",
                    help="طول الوصلة طبقا للكود المصري من 40 إلى 50 مرة القطر (Default 50Φ)",
                    key="cs_lap_factor",
                )
            with col_g8:
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    n_st_m = st.number_input(
                        "كانات/م'",
                        min_value=4, max_value=15, value=def_n_st_m, step=1,
                        help="عدد الكانات بالمتر الطولي لارتفاع العمود (Default 6/m')",
                        key="cs_n_st_m",
                    )
                with col_sub2:
                    phi_st = st.selectbox(
                        "قطر الكانة",
                        options=[6, 8, 10, 12],
                        index=max(0, min(def_phi_st_idx, 3)),
                        format_func=lambda d: f"Φ{d} mm",
                        help="قطر أسياخ الكانات (Default 8 mm)",
                        key="cs_phi_st",
                    )

            st.markdown("<hr style='margin:10px 0 8px 0; border:none; border-top:1px dashed #cbd5e1;'>", unsafe_allow_html=True)

            # ── ECP 203 Column Rebar Grid & Rows Calculation Helper ──
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

            # ── SECTION B: PER-COLUMN TYPE SPECIFIC INPUTS ──
            st.markdown("<div style='font-size:14.5px; font-weight:800; color:#1e3a8a; margin-bottom:6px;'>🏛️ 2. مدخلات وتفاصيل نماذج الأعمدة (Per-Column Model Details)</div>", unsafe_allow_html=True)

            type_tabs = st.tabs([f"🏛️ نموذج C{i+1}" for i in range(int(n_types_in))])
            col_inputs = []
            short_models_list = []

            is_top_flag = "yes" in is_top_floor_sel.lower()
            has_footing_flag = "yes" in has_footing_dowels_sel.lower()

            for idx in range(int(n_types_in)):
                with type_tabs[idx]:
                    # Persistent defaults per column type from user_settings.json
                    def_fallback_name = f"C{idx+1}"
                    def_fallback_b = 30.0
                    def_fallback_t = 60.0 if idx == 0 else (50.0 if idx == 1 else (70.0 if idx == 2 else 60.0 + (idx - 3) * 10.0))
                    def_fallback_ncols = 10 if idx == 0 else (8 if idx == 1 else (6 if idx == 2 else 5))
                    def_fallback_nb = 8 if idx == 0 else (6 if idx == 1 else (10 if idx == 2 else 8))
                    def_fallback_phi_idx = 3  # 16 mm

                    def_name = str(cfg_val(f"cs_name_{idx}", def_fallback_name))
                    def_b = float(cfg_val(f"cs_b_{idx}", def_fallback_b))
                    def_t = float(cfg_val(f"cs_t_{idx}", def_fallback_t))
                    def_ncols = int(cfg_val(f"cs_ncols_{idx}", def_fallback_ncols))
                    def_nb = int(cfg_val(f"cs_nb_{idx}", def_fallback_nb))
                    def_phi_idx = int(cfg_val(f"cs_phi_idx_{idx}", def_fallback_phi_idx))

                    r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
                    with r1_c1:
                        c_name_in = st.text_input(
                            "اسم / رمز النموذج",
                            value=def_name,
                            key=f"cs_name_{idx}",
                            help="اسم نموذج العمود مثل: C1, C2, ع1, ع2...",
                        )
                    with r1_c2:
                        c_b_in = st.number_input(
                            "عرض العمود b (cm)",
                            min_value=15.0, max_value=300.0,
                            value=def_b,
                            step=5.0,
                            key=f"cs_b_{idx}",
                        )
                    with r1_c3:
                        c_t_in = st.number_input(
                            "طول العمود t (cm)",
                            min_value=20.0, max_value=500.0,
                            value=def_t,
                            step=5.0,
                            key=f"cs_t_{idx}",
                        )
                    with r1_c4:
                        c_ncols_in = st.number_input(
                            "عدد الأعمدة من هذا النموذج (N)",
                            min_value=1, max_value=10000,
                            value=def_ncols,
                            step=1,
                            key=f"cs_ncols_{idx}",
                        )

                    # Dynamic ECP rows and tie-type rules
                    cur_nb = st.session_state.get(f"cs_nb_{idx}", def_nb)
                    cur_phi = st.session_state.get(f"cs_phi_{idx}", 16)
                    ny_d, nx_d, sy_d, sx_d = _calc_ecp_rows(c_b_in, c_t_in, cur_nb, cur_phi, cover_cm)

                    def_nrows = int(cfg_val(f"cs_nrows_{idx}", ny_d))
                    def_tietype_idx = int(cfg_val(f"cs_tietype_idx_{idx}", 0 if cur_nb < 8 else (1 if ny_d > 3 else 0)))

                    design_key_i = (c_b_in, c_t_in, cur_nb, cur_phi)
                    if st.session_state.get(f"_last_key_{idx}") != design_key_i:
                        st.session_state[f"_last_key_{idx}"] = design_key_i
                        if cur_nb < 8:
                            st.session_state[f"cs_nrows_{idx}"] = 3 if cur_nb == 6 else (2 if cur_nb <= 4 else min(3, ny_d))
                            st.session_state[f"cs_tietype_{idx}"] = "Box (كانة صندوقية)"
                        else:
                            st.session_state[f"cs_nrows_{idx}"] = ny_d
                            if ny_d > 3:
                                st.session_state[f"cs_tietype_{idx}"] = "Automatic (كانة أوتوماتيك)"
                            else:
                                st.session_state[f"cs_tietype_{idx}"] = "Box (كانة صندوقية)"

                    r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
                    with r2_c1:
                        c_nb_in = st.number_input(
                            "عدد أسياخ الحديد الرئيسي",
                            min_value=4, max_value=100,
                            value=def_nb,
                            step=2,
                            key=f"cs_nb_{idx}",
                            help="إذا كان أقل من 8 أسياخ يتم تعيين الكانات إلى Box وتحديد 3/2 صفوف تلقائياً",
                        )
                    with r2_c2:
                        phi_opts_list = [10, 12, 14, 16, 18, 20, 22, 25, 28, 32]
                        c_phi_in = st.selectbox(
                            "قطر الحديد الرئيسي (mm)",
                            options=phi_opts_list,
                            index=max(0, min(def_phi_idx, len(phi_opts_list) - 1)),
                            format_func=lambda d: f"Φ{d} mm",
                            key=f"cs_phi_{idx}",
                        )
                    with r2_c3:
                        c_nrows_in = st.number_input(
                            f"عدد صفوف الحديد (تصميم: {ny_d} صفوف)",
                            min_value=2, max_value=20,
                            value=st.session_state.get(f"cs_nrows_{idx}", def_nrows),
                            step=1,
                            key=f"cs_nrows_{idx}",
                            help=f"محسوب تلقائياً (ECP 203): {ny_d} صفوف × {nx_d} أعمدة (S = {sy_d:.1f} cm ≤ 25 cm)",
                        )
                    with r2_c4:
                        tie_opts_list = ["Box (كانة صندوقية)", "Automatic (كانة أوتوماتيك)"]
                        if f"cs_tietype_{idx}" not in st.session_state:
                            st.session_state[f"cs_tietype_{idx}"] = tie_opts_list[max(0, min(def_tietype_idx, 1))]

                        c_tietype_in = st.selectbox(
                            "نوع الكانات",
                            options=tie_opts_list,
                            index=max(0, min(def_tietype_idx, 1)),
                            key=f"cs_tietype_{idx}",
                            help="إذا كان أقل من 8 أسياخ يتغير تلقائياً إلى Box، وإذا زاد عدد الصفوف عن 3 يتغير تلقائياً إلى Automatic",
                        )

                    # ── DYNAMIC THEORETICAL CUTTING LENGTH & EDITABLE USER OVERRIDE ──
                    c_L_lap_calc_cm = (lap_factor_sel * c_phi_in) / 10.0
                    c_L_hook_calc_cm = max(25.0, (lap_factor_sel * c_phi_in) / 10.0)
                    c_L_foot_calc_cm = max(25.0, (12.0 * c_phi_in) / 10.0) if has_footing_flag else 0.0

                    if not is_top_flag:
                        c_L_calc_cm = col_h_in + t_slab_in + c_L_lap_calc_cm + c_L_foot_calc_cm
                    else:
                        c_L_calc_cm = col_h_in + (t_slab_in - cover_cm) + c_L_hook_calc_cm + c_L_foot_calc_cm

                    c_L_calc_m = round(c_L_calc_cm / 100.0, 2)

                    # Dynamic update of cut length when design parameters change
                    cut_calc_trigger_key = (col_h_in, t_slab_in, is_top_flag, lap_factor_sel, has_footing_flag, c_phi_in)
                    if st.session_state.get(f"_last_cut_calc_key_{idx}") != cut_calc_trigger_key:
                        st.session_state[f"_last_cut_calc_key_{idx}"] = cut_calc_trigger_key
                        st.session_state[f"cs_cut_length_{idx}"] = float(c_L_calc_m)

                    def_cut_length = float(cfg_val(f"cs_cut_length_{idx}", c_L_calc_m))
                    if f"cs_cut_length_{idx}" not in st.session_state:
                        st.session_state[f"cs_cut_length_{idx}"] = def_cut_length

                    def _sync_cut_length_to_all(src_idx: int):
                        new_val = st.session_state.get(f"cs_cut_length_{src_idx}")
                        if new_val is not None:
                            for k in range(20):
                                st.session_state[f"cs_cut_length_{k}"] = float(new_val)

                    r3_c1, r3_c2 = st.columns([1.5, 2.5])
                    with r3_c1:
                        c_cut_length_in = st.number_input(
                            "📐 أختر طول القطع Total cut length of main steel (m')",
                            min_value=0.50, max_value=12.00,
                            value=float(st.session_state.get(f"cs_cut_length_{idx}", c_L_calc_m)),
                            step=0.05,
                            format="%.2f",
                            key=f"cs_cut_length_{idx}",
                            on_change=_sync_cut_length_to_all,
                            args=(idx,),
                            help=f"طول القطع المحسوب هندسياً طبقاً للمدخلات = {c_L_calc_m:.2f} م ({c_L_calc_cm:.0f} سم). عند تعديل هذا الطول في أي نموذج يتم تطبيقه تلقائياً وموحداً على كافة نماذج الأعمدة الأخرى ({n_types_in} نماذج) لتوحيد أطوال التقطيع والطلبيات.",
                        )

                    # Pop-up check if user enters length less than calculated
                    is_shorter_than_code = (c_cut_length_in < c_L_calc_m - 0.005)
                    confirmed_cut_val = st.session_state.get(f"cs_cut_confirmed_{idx}")

                    if is_shorter_than_code and (confirmed_cut_val != c_cut_length_in):
                        diff_cm = (c_L_calc_m - c_cut_length_in) * 100.0
                        short_models_list.append({
                            "idx": idx,
                            "name": c_name_in or f"C{idx+1}",
                            "phi": int(c_phi_in),
                            "user_cut_m": float(c_cut_length_in),
                            "calc_cut_m": float(c_L_calc_m),
                            "diff_cm": float(diff_cm),
                        })
                    elif not is_shorter_than_code:
                        st.session_state[f"cs_cut_confirmed_{idx}"] = c_cut_length_in

                    with r3_c2:
                        is_custom_cut = abs(c_cut_length_in - c_L_calc_m) > 0.005
                        is_shorter = c_cut_length_in < (c_L_calc_m - 0.005)
                        foot_note = f" + رجل {c_L_foot_calc_cm:.0f}سم" if has_footing_flag else ""
                        top_lap_note = f"جنش {c_L_hook_calc_cm:.0f}سم" if is_top_flag else f"وصلة {c_L_lap_calc_cm:.0f}سم ({lap_factor_sel:.0f}Φ)"
                        calc_summary_str = f"H ({col_h_in:.0f}) + ts ({t_slab_in:.0f}) + {top_lap_note}{foot_note}"
                        
                        if is_shorter:
                            badge_bg = "linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)"
                            badge_border = "#ef4444"
                            badge_accent = "#dc2626"
                            badge_shadow = "rgba(220, 38, 38, 0.22)"
                            badge_title_color = "#991b1b"
                            badge_text_color = "#7f1d1d"
                            badge_icon = "🚨"
                            diff_short_cm = (c_L_calc_m - c_cut_length_in) * 100.0
                            status_label = f"⚠️ تحذير: طول القطع المخصص (<span style='font-size:1.50rem; font-weight:900; color:#dc2626;' dir='ltr'>{c_cut_length_in:.2f} m'</span>) أقل من المطلوب هندسياً (<span style='font-size:1.20rem; font-weight:800; color:#15803d;' dir='ltr'>{c_L_calc_m:.2f} m'</span>) بنقص {diff_short_cm:.0f} سم!"
                        elif is_custom_cut:
                            badge_bg = "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)"
                            badge_border = "#f59e0b"
                            badge_accent = "#d97706"
                            badge_shadow = "rgba(217, 119, 6, 0.22)"
                            badge_title_color = "#92400e"
                            badge_text_color = "#78350f"
                            badge_icon = "⚠️"
                            status_label = f"تم تخصيص طول القطع يدوياً إلى: <span style='font-size:1.50rem; font-weight:900; color:#b45309;' dir='ltr'>{c_cut_length_in:.2f} m'</span> <span style='font-size:1.10rem; opacity:0.95;'>({c_cut_length_in*100:.0f} cm — المحسوب: {c_L_calc_m:.2f} m')</span>"
                        else:
                            badge_bg = "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)"
                            badge_border = "#16a34a"
                            badge_accent = "#15803d"
                            badge_shadow = "rgba(22, 163, 74, 0.22)"
                            badge_title_color = "#14532d"
                            badge_text_color = "#166534"
                            badge_icon = "✅"
                            status_label = f"طول القطع مطابق للحسابات الهندسية: <span style='font-size:1.50rem; font-weight:900; color:#15803d;' dir='ltr'>{c_L_calc_m:.2f} m'</span> <span style='font-size:1.10rem; opacity:0.95;'>({c_L_calc_cm:.0f} cm)</span>"

                        st.markdown(
                            f"""
                            <div style="
                                margin-top: 14px;
                                padding: 14px 20px;
                                background: {badge_bg};
                                border: 2.5px solid {badge_border};
                                border-right: 10px solid {badge_accent};
                                border-radius: 10px;
                                box-shadow: 0 6px 18px {badge_shadow};
                            ">
                                <div style="font-size: 1.35rem; font-weight: 900; color: {badge_title_color}; display: flex; align-items: center; gap: 10px;">
                                    <span style="font-size: 1.60rem;">{badge_icon}</span>
                                    <span>{status_label}</span>
                                </div>
                                <div style="font-size: 1.20rem; font-weight: 800; color: {badge_text_color}; margin-top: 8px; line-height: 1.5;" dir="rtl">
                                    📌 <b>تفصيل الحساب الهندسي:</b> <span dir="ltr" style="background:rgba(255,255,255,0.88); border:1.5px solid rgba(0,0,0,0.18); padding:4px 14px; border-radius:6px; font-weight:900; font-size:1.22rem; color:#0f172a;">{calc_summary_str} = {c_L_calc_cm:.0f} cm ({c_L_calc_m:.2f} m')</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    col_inputs.append({
                        "index": idx,
                        "name": c_name_in or f"C{idx+1}",
                        "b": c_b_in,
                        "t": c_t_in,
                        "n_cols": int(c_ncols_in),
                        "n_bars": int(c_nb_in),
                        "phi_main": int(c_phi_in),
                        "n_rows": int(c_nrows_in),
                        "tie_type": c_tietype_in,
                        "cut_length_m": float(c_cut_length_in),
                        "calc_length_m": float(c_L_calc_m),
                        "L_foot_cm": float(c_L_foot_calc_cm),
                    })

            # Trigger warning dialog ONCE if any model requires confirmation for shorter cut length
            if len(short_models_list) > 0 and hasattr(st, "dialog"):
                _warn_short_cut_dialog(
                    short_models=short_models_list,
                    total_types=int(n_types_in),
                )

        # ════════════════════════════════════════════════════════════════════
        # SECTION 2: FLAT SLAB QUANTITY SURVEY INPUTS (حصر البلاطات المسطة flat slab)
        # ════════════════════════════════════════════════════════════════════
        with st.container(border=True):
            st.markdown(
                """
                <div class="cs-inputs-header-badge" style="
                    background: linear-gradient(135deg, #065f46 0%, #059669 100%);
                    color: #ffffff !important;
                    padding: 4px 12px;
                    border-radius: 6px;
                    font-weight: 800;
                    font-size: 15px;
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    border-left: 4px solid #34d399;
                ">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:16px;">🟦</span>
                        <span style="color:#ffffff !important;">حصر البلاطات المسطة flat slab</span>
                    </div>
                    <span style="background: rgba(255,255,255,0.22); color:#ffffff !important; padding: 1px 8px; border-radius: 12px; font-size: 11.5px; font-weight: 700;">
                        Flat Slab Survey
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Common Flat Slab Inputs & Unified Meshes
            def_fs_n_slabs = int(cfg_val("cs_fs_n_slabs", 1))
            def_fs_ts = float(cfg_val("cs_fs_ts", 20.0))
            def_fs_fcu = float(cfg_val("cs_fs_fcu", 350.0))
            def_fs_phi_btm = int(cfg_val("cs_fs_phi_btm", 12))
            def_fs_nb_btm = int(cfg_val("cs_fs_nb_btm", 6))
            def_fs_phi_top = int(cfg_val("cs_fs_phi_top", 10))
            def_fs_nb_top = int(cfg_val("cs_fs_nb_top", 6))

            mesh_dia_opts = [10, 12, 14, 16, 18, 20]

            fs_cg1, fs_cg2, fs_cg3 = st.columns([1.2, 1.4, 1.4])
            with fs_cg1:
                n_slabs_fs_in = st.number_input(
                    "عدد نماذج البلاطات المسطحة (S1, S2...)",
                    min_value=1, max_value=20, value=def_fs_n_slabs, step=1,
                    help="إجمالي عدد نماذج البلاطات المسطحة المطلوب حصر خرسانتها وحديدها ومواد بنائها",
                    key="cs_fs_n_slabs",
                )
            with fs_cg2:
                ts_fs_in = st.number_input(
                    "تخانة البلاطة ts (cm) — موحدة لجميع البلاطات",
                    min_value=10.0, max_value=60.0, value=def_fs_ts, step=1.0,
                    help="تخانة وسماكة البلاطة المسطحة الخرسانية الموحدة لجميع البلاطات (Default 20 cm)",
                    key="cs_fs_ts",
                )
            with fs_cg3:
                fcu_fs_in = st.number_input(
                    "رتبة الخرسانة / محتوى الأسمنت (kg/m³)",
                    min_value=150.0, max_value=600.0, value=def_fs_fcu, step=25.0,
                    help="محتوى الأسمنت للبلاطات المسطحة لحساب كميات الأسمنت والمياه (Default 350 kg/m³)",
                    key="cs_fs_fcu",
                )

            fs_m1, fs_m2, fs_m3, fs_m4 = st.columns(4)
            with fs_m1:
                idx_b = mesh_dia_opts.index(def_fs_phi_btm) if def_fs_phi_btm in mesh_dia_opts else 1
                phi_btm_mesh_in = st.selectbox(
                    "قطر شبكة الحديد السفلية",
                    options=mesh_dia_opts,
                    index=idx_b,
                    format_func=lambda d: f"Φ{d} mm",
                    help="قطر شبكة التسليح السفلية الموحدة في الاتجاهين X و Y (Default Φ12 mm)",
                    key="cs_fs_phi_btm",
                )
            with fs_m2:
                nb_btm_mesh_in = st.number_input(
                    "عدد اسياخ شبكة الحديد السفلية (أسياخ/م')",
                    min_value=3, max_value=15, value=def_fs_nb_btm, step=1,
                    help="كثافة التسليح بالمتر الطولي للشبكة السفلية في الاتجاهين X و Y (Default 6 أسياخ/متر)",
                    key="cs_fs_nb_btm",
                )
            with fs_m3:
                idx_t = mesh_dia_opts.index(def_fs_phi_top) if def_fs_phi_top in mesh_dia_opts else 0
                phi_top_mesh_in = st.selectbox(
                    "قطر شبكة الحديد العلوية",
                    options=mesh_dia_opts,
                    index=idx_t,
                    format_func=lambda d: f"Φ{d} mm",
                    help="قطر شبكة التسليح العلوية الموحدة في الاتجاهين X و Y (Default Φ10 mm)",
                    key="cs_fs_phi_top",
                )
            with fs_m4:
                nb_top_mesh_in = st.number_input(
                    "عدد اسياخ شبكة الحديد العلوية (أسياخ/م')",
                    min_value=3, max_value=15, value=def_fs_nb_top, step=1,
                    help="كثافة التسليح بالمتر الطولي للشبكة العلوية في الاتجاهين X و Y (Default 6 أسياخ/متر)",
                    key="cs_fs_nb_top",
                )

            st.markdown("<hr style='margin:8px 0 8px 0; border:none; border-top:1px dashed #cbd5e1;'>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #065f46 0%, #047857 100%); padding: 12px 18px; border-radius: 8px; border-left: 6px solid #34d399; margin: 12px 0 10px 0; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 12px rgba(6, 95, 70, 0.20);">
                    <span style="color: #ffffff !important; font-size: 24px; font-weight: 900;">📐 أبعاد وتكرار نماذج البلاطات المسطحة (Slab Panels Dimensions & Counts)</span>
                    <span style="font-size: 15px; font-weight: 700; color: #ffffff !important; background: rgba(255,255,255,0.20); padding: 4px 14px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.35);">
                        تخانة موحدة: {ts_fs_in:.0f}cm │ سفلي: {nb_btm_mesh_in}Φ{phi_btm_mesh_in}/م' │ علوي: {nb_top_mesh_in}Φ{phi_top_mesh_in}/م' │ رتبة: {fcu_fs_in:.0f}kg/m³
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            slab_tabs = st.tabs([f"🟦 نموذج بلاطة S{i+1}" for i in range(int(n_slabs_fs_in))])
            slab_inputs = []

            for s_idx in range(int(n_slabs_fs_in)):
                with slab_tabs[s_idx]:
                    def_s_name = str(cfg_val(f"cs_fs_name_{s_idx}", f"S{s_idx+1}"))
                    def_s_lx = float(cfg_val(f"cs_fs_lx_{s_idx}", 10.0 if s_idx == 0 else (8.0 if s_idx == 1 else 12.0)))
                    def_s_ly = float(cfg_val(f"cs_fs_ly_{s_idx}", 8.0 if s_idx == 0 else (6.0 if s_idx == 1 else 10.0)))
                    def_s_n_rep = int(cfg_val(f"cs_fs_n_rep_{s_idx}", 1))

                    sr1_1, sr1_2, sr1_3, sr1_4 = st.columns(4)
                    with sr1_1:
                        s_name_in = st.text_input(
                            "اسم / رمز البلاطة",
                            value=def_s_name,
                            key=f"cs_fs_name_{s_idx}",
                            help="اسم نموذج البلاطة مثل: S1, S2, سقف1...",
                        )
                    with sr1_2:
                        s_lx_in = st.number_input(
                            "طول البلاطة اتجاه x (m)",
                            min_value=1.0, max_value=200.0, value=def_s_lx, step=0.5,
                            help="البعد الأفقي للبلاطة في اتجاه محور X بالمتر",
                            key=f"cs_fs_lx_{s_idx}",
                        )
                    with sr1_3:
                        s_ly_in = st.number_input(
                            "عرض البلاطة اتجاه y (m)",
                            min_value=1.0, max_value=200.0, value=def_s_ly, step=0.5,
                            help="البعد الرأسي للبلاطة في اتجاه محور Y بالمتر",
                            key=f"cs_fs_ly_{s_idx}",
                        )
                    with sr1_4:
                        s_n_rep_in = st.number_input(
                            "عدد البلاطات المتطابقة (N)",
                            min_value=1, max_value=1000, value=def_s_n_rep, step=1,
                            help="عدد مرات تكرار هذه البلاطة بالمشروع",
                            key=f"cs_fs_n_rep_{s_idx}",
                        )

                    # ── 1. قسم مدخلات الحديد الإضافي العلوي (Top Additional Reinforcement /m') ──
                    st.markdown(
                        """
                        <div style='background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); color:#166534; font-size:13.5px; font-weight:800; padding:7px 14px; border-radius:6px; border-left:4px solid #16a34a; margin:12px 0 6px 0; display:flex; justify-content:space-between; align-items:center; border:1px solid #bbf7d0;'>
                            <span>🔼 مدخلات نماذج الحديد الإضافي العلوي — (بالمتر الطولي /م') (Top Additional Rebar /m')</span>
                            <span style='font-size:11.5px; color:#15803d; font-weight:700;'>المدخلات بالمتر الطولي (أسياخ / م') لشريحة أبعادها (Lx × Ly) — ضع 0 في حال عدم الحاجة</span>
                        </div>
                        <div style='background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%); border: 2.5px solid #eab308; border-radius: 8px; padding: 10px 16px; margin: 6px 0 10px 0; display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(234, 179, 8, 0.18);'>
                            <span style='font-size: 24px;'>💡</span>
                            <div>
                                <span style='color: #854d0e; font-size: 17px; font-weight: 900;'>ملاحظة هامة (NOTE):</span>
                                <span style='color: #713f12; font-size: 17px; font-weight: 800; margin-right: 6px;'>يتم ادخال جميع المساحات التي تحتاج الي حديد علوي اضافي بالتتابع</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    def_n_top_m = int(cfg_val(f"cs_fs_n_top_models_{s_idx}", 1))
                    n_top_models_in = st.number_input(
                        f"عدد نماذج الحديد الإضافي العلوي للبلاطة {def_s_name}",
                        min_value=1, max_value=10, value=def_n_top_m, step=1,
                        key=f"cs_fs_n_top_models_{s_idx}",
                        help="عدد نماذج أو مناطق الحديد الإضافي العلوي في هذه البلاطة (مثلاً T1 فوق عمود C1، T2 فوق عمود C2...)",
                    )

                    top_add_models = []
                    top_tabs = st.tabs([f"🔹 نموذج علوي T{k+1}" for k in range(int(n_top_models_in))])
                    for k in range(int(n_top_models_in)):
                        with top_tabs[k]:
                            t_c0, t_c1, t_c2, t_c3, t_c4, t_c5, t_c6 = st.columns([1.2, 1.1, 1.1, 1.1, 1.0, 1.0, 1.0])
                            with t_c0:
                                def_t_name = str(cfg_val(f"cs_fs_top_add_name_{s_idx}_{k}", f"T{k+1}"))
                                t_name_in = st.text_input("اسم النموذج", value=def_t_name, key=f"cs_fs_top_add_name_{s_idx}_{k}", help="رمز أو اسم النموذج مثل T1, T2")
                            with t_c1:
                                def_phi_t = int(cfg_val(f"cs_fs_top_add_phi_{s_idx}_{k}", 12))
                                idx_phi_t = mesh_dia_opts.index(def_phi_t) if def_phi_t in mesh_dia_opts else 1
                                t_phi_in = st.selectbox("القطر", options=mesh_dia_opts, index=idx_phi_t, format_func=lambda d: f"Φ{d} mm", key=f"cs_fs_top_add_phi_{s_idx}_{k}", help="قطر أسياخ هذا النموذج")
                            with t_c2:
                                def_t_lx = float(cfg_val(f"cs_fs_top_add_lx_{s_idx}_{k}", round(def_s_lx * 0.30, 2)))
                                t_lx_in = st.number_input("طول X (m)", min_value=0.1, max_value=200.0, value=def_t_lx, step=0.25, key=f"cs_fs_top_add_lx_{s_idx}_{k}", help="طول السيخ في اتجاه X")
                            with t_c3:
                                def_t_ly = float(cfg_val(f"cs_fs_top_add_ly_{s_idx}_{k}", round(def_s_ly * 0.30, 2)))
                                t_ly_in = st.number_input("عرض Y (m)", min_value=0.1, max_value=200.0, value=def_t_ly, step=0.25, key=f"cs_fs_top_add_ly_{s_idx}_{k}", help="عرض الشريحة في اتجاه Y")
                            with t_c4:
                                def_t_nx = int(cfg_val(f"cs_fs_top_add_nx_{s_idx}_{k}", 0))
                                t_nx_in = st.number_input("عدد أسياخ X (سيخ/م')", min_value=0, max_value=50, value=def_t_nx, step=1, key=f"cs_fs_top_add_nx_{s_idx}_{k}", help="عدد الأسياخ في المتر الطولي في اتجاه X، وتوزع على عرض الشريحة Ly")
                            with t_c5:
                                def_t_ny = int(cfg_val(f"cs_fs_top_add_ny_{s_idx}_{k}", 0))
                                t_ny_in = st.number_input("عدد أسياخ Y (سيخ/م')", min_value=0, max_value=50, value=def_t_ny, step=1, key=f"cs_fs_top_add_ny_{s_idx}_{k}", help="عدد الأسياخ في المتر الطولي في اتجاه Y، وتوزع على طول الشريحة Lx")
                            with t_c6:
                                def_t_nz = int(cfg_val(f"cs_fs_top_add_nz_{s_idx}_{k}", 1))
                                t_nz_in = st.number_input("تكرار المنطقة", min_value=1, max_value=100, value=def_t_nz, step=1, key=f"cs_fs_top_add_nz_{s_idx}_{k}", help="عدد مرات تكرار هذه المنطقة بالبلاطة")

                            top_add_models.append({
                                "index": k,
                                "name": t_name_in or f"T{k+1}",
                                "phi": int(t_phi_in),
                                "lx": float(t_lx_in),
                                "ly": float(t_ly_in),
                                "nx": int(t_nx_in),
                                "ny": int(t_ny_in),
                                "n_zones": int(t_nz_in),
                            })

                    # ── 2. قسم مدخلات الحديد الإضافي السفلي (Bottom Additional Reinforcement /m') ──
                    st.markdown(
                        """
                        <div style='background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); color:#1e40af; font-size:13.5px; font-weight:800; padding:7px 14px; border-radius:6px; border-left:4px solid #2563eb; margin:14px 0 6px 0; display:flex; justify-content:space-between; align-items:center; border:1px solid #bfdbfe;'>
                            <span>🔽 مدخلات نماذج الحديد الإضافي السفلي — (بالمتر الطولي /م') (Bottom Additional Rebar /m')</span>
                            <span style='font-size:11.5px; color:#1d4ed8; font-weight:700;'>المدخلات بالمتر الطولي (أسياخ / م') لشريحة أبعادها (Lx × Ly) — ضع 0 في حال عدم الحاجة</span>
                        </div>
                        <div style='background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%); border: 2.5px solid #eab308; border-radius: 8px; padding: 10px 16px; margin: 6px 0 10px 0; display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(234, 179, 8, 0.18);'>
                            <span style='font-size: 24px;'>💡</span>
                            <div>
                                <span style='color: #854d0e; font-size: 17px; font-weight: 900;'>ملاحظة هامة (NOTE):</span>
                                <span style='color: #713f12; font-size: 17px; font-weight: 800; margin-right: 6px;'>يتم ادخال جميع المساحات التي تحتاج الي حديد سفلي اضافي بالتتابع</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    def_n_btm_m = int(cfg_val(f"cs_fs_n_btm_models_{s_idx}", 1))
                    n_btm_models_in = st.number_input(
                        f"عدد نماذج الحديد الإضافي السفلي للبلاطة {def_s_name}",
                        min_value=1, max_value=10, value=def_n_btm_m, step=1,
                        key=f"cs_fs_n_btm_models_{s_idx}",
                        help="عدد نماذج أو مناطق الحديد الإضافي السفلي في هذه البلاطة (مثلاً B1 في منتصف البحر 1، B2 في منتصف البحر 2...)",
                    )

                    btm_add_models = []
                    btm_tabs = st.tabs([f"🔹 نموذج سفلي B{k+1}" for k in range(int(n_btm_models_in))])
                    for k in range(int(n_btm_models_in)):
                        with btm_tabs[k]:
                            b_c0, b_c1, b_c2, b_c3, b_c4, b_c5, b_c6 = st.columns([1.2, 1.1, 1.1, 1.1, 1.0, 1.0, 1.0])
                            with b_c0:
                                def_b_name = str(cfg_val(f"cs_fs_btm_add_name_{s_idx}_{k}", f"B{k+1}"))
                                b_name_in = st.text_input("اسم النموذج", value=def_b_name, key=f"cs_fs_btm_add_name_{s_idx}_{k}", help="رمز أو اسم النموذج مثل B1, B2")
                            with b_c1:
                                def_phi_b = int(cfg_val(f"cs_fs_btm_add_phi_{s_idx}_{k}", 12))
                                idx_phi_b = mesh_dia_opts.index(def_phi_b) if def_phi_b in mesh_dia_opts else 1
                                b_phi_in = st.selectbox("القطر", options=mesh_dia_opts, index=idx_phi_b, format_func=lambda d: f"Φ{d} mm", key=f"cs_fs_btm_add_phi_{s_idx}_{k}", help="قطر أسياخ هذا النموذج")
                            with b_c2:
                                def_b_lx = float(cfg_val(f"cs_fs_btm_add_lx_{s_idx}_{k}", round(def_s_lx * 0.50, 2)))
                                b_lx_in = st.number_input("طول X (m)", min_value=0.1, max_value=200.0, value=def_b_lx, step=0.25, key=f"cs_fs_btm_add_lx_{s_idx}_{k}", help="طول السيخ في اتجاه X")
                            with b_c3:
                                def_b_ly = float(cfg_val(f"cs_fs_btm_add_ly_{s_idx}_{k}", round(def_s_ly * 0.50, 2)))
                                b_ly_in = st.number_input("عرض Y (m)", min_value=0.1, max_value=200.0, value=def_b_ly, step=0.25, key=f"cs_fs_btm_add_ly_{s_idx}_{k}", help="عرض الشريحة في اتجاه Y")
                            with b_c4:
                                def_b_nx = int(cfg_val(f"cs_fs_btm_add_nx_{s_idx}_{k}", 0))
                                b_nx_in = st.number_input("عدد أسياخ X (سيخ/م')", min_value=0, max_value=50, value=def_b_nx, step=1, key=f"cs_fs_btm_add_nx_{s_idx}_{k}", help="عدد الأسياخ في المتر الطولي في اتجاه X، وتوزع على عرض الشريحة Ly")
                            with b_c5:
                                def_b_ny = int(cfg_val(f"cs_fs_btm_add_ny_{s_idx}_{k}", 0))
                                b_ny_in = st.number_input("عدد أسياخ Y (سيخ/م')", min_value=0, max_value=50, value=def_b_ny, step=1, key=f"cs_fs_btm_add_ny_{s_idx}_{k}", help="عدد الأسياخ في المتر الطولي في اتجاه Y، وتوزع على طول الشريحة Lx")
                            with b_c6:
                                def_b_nz = int(cfg_val(f"cs_fs_btm_add_nz_{s_idx}_{k}", 1))
                                b_nz_in = st.number_input("تكرار المنطقة", min_value=1, max_value=100, value=def_b_nz, step=1, key=f"cs_fs_btm_add_nz_{s_idx}_{k}", help="عدد مرات تكرار هذه المنطقة بالبلاطة")

                            btm_add_models.append({
                                "index": k,
                                "name": b_name_in or f"B{k+1}",
                                "phi": int(b_phi_in),
                                "lx": float(b_lx_in),
                                "ly": float(b_ly_in),
                                "nx": int(b_nx_in),
                                "ny": int(b_ny_in),
                                "n_zones": int(b_nz_in),
                            })

                    # Info Card with inherited & additional details
                    add_summary_badges = []
                    for tm in top_add_models:
                        if tm["nx"] > 0 or tm["ny"] > 0:
                            n_rx_disp = int(math.ceil(tm["ly"] * tm["nx"])) if (tm["nx"] > 0 and tm["ly"] > 0) else 0
                            n_ry_disp = int(math.ceil(tm["lx"] * tm["ny"])) if (tm["ny"] > 0 and tm["lx"] > 0) else 0
                            add_summary_badges.append(f"🔼 علوي [{tm['name']}]: X={n_rx_disp} سيخ ({tm['nx']}Φ{tm['phi']}/م' بطول {tm['lx']:.1f}m), Y={n_ry_disp} سيخ ({tm['ny']}Φ{tm['phi']}/م' بطول {tm['ly']:.1f}m) ×{tm['n_zones']}")
                    for bm in btm_add_models:
                        if bm["nx"] > 0 or bm["ny"] > 0:
                            n_rx_disp = int(math.ceil(bm["ly"] * bm["nx"])) if (bm["nx"] > 0 and bm["ly"] > 0) else 0
                            n_ry_disp = int(math.ceil(bm["lx"] * bm["ny"])) if (bm["ny"] > 0 and bm["lx"] > 0) else 0
                            add_summary_badges.append(f"🔽 سفلي [{bm['name']}]: X={n_rx_disp} سيخ ({bm['nx']}Φ{bm['phi']}/م' بطول {bm['lx']:.1f}m), Y={n_ry_disp} سيخ ({bm['ny']}Φ{bm['phi']}/م' بطول {bm['ly']:.1f}m) ×{bm['n_zones']}")

                    st.markdown(
                        f"""
                        <div style='background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:6px 14px; font-size:13px; color:#475569; display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin-top:6px;'>
                            <span>📐 <b>تخانة البلاطة:</b> {ts_fs_in:.0f} cm</span>
                            <span>🔹 <b>الشبكة السفلية:</b> {nb_btm_mesh_in} Φ{phi_btm_mesh_in} mm / م'</span>
                            <span>🔸 <b>الشبكة العلوية:</b> {nb_top_mesh_in} Φ{phi_top_mesh_in} mm / م'</span>
                            <span>🧪 <b>رتبة الخرسانة:</b> {fcu_fs_in:.0f} kg/m³</span>
                            {"".join([f"<span style='background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:4px; font-weight:700;'>{badge}</span>" for badge in add_summary_badges])}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    slab_inputs.append({
                        "index": s_idx,
                        "name": s_name_in or f"S{s_idx+1}",
                        "lx": float(s_lx_in),
                        "ly": float(s_ly_in),
                        "ts": float(ts_fs_in),
                        "fcu": float(fcu_fs_in),
                        "n_rep": int(s_n_rep_in),
                        "phi_btm_x": int(phi_btm_mesh_in),
                        "phi_btm_y": int(phi_btm_mesh_in),
                        "nb_btm_x": int(nb_btm_mesh_in),
                        "nb_btm_y": int(nb_btm_mesh_in),
                        "phi_top_x": int(phi_top_mesh_in),
                        "phi_top_y": int(phi_top_mesh_in),
                        "nb_top_x": int(nb_top_mesh_in),
                        "nb_top_y": int(nb_top_mesh_in),
                        "nb_x": int(nb_btm_mesh_in),
                        "nb_y": int(nb_btm_mesh_in),
                        # Multi-model Additional Rebar
                        "top_add_models": top_add_models,
                        "btm_add_models": btm_add_models,
                        # Single model fallback references
                        "phi_top_add": top_add_models[0]["phi"] if top_add_models else 12,
                        "add_top_lx": top_add_models[0]["lx"] if top_add_models else 0.0,
                        "add_top_ly": top_add_models[0]["ly"] if top_add_models else 0.0,
                        "n_top_add_x": top_add_models[0]["nx"] if top_add_models else 0,
                        "n_top_add_y": top_add_models[0]["ny"] if top_add_models else 0,
                        "phi_btm_add": btm_add_models[0]["phi"] if btm_add_models else 12,
                        "add_btm_lx": btm_add_models[0]["lx"] if btm_add_models else 0.0,
                        "add_btm_ly": btm_add_models[0]["ly"] if btm_add_models else 0.0,
                        "n_btm_add_x": btm_add_models[0]["nx"] if btm_add_models else 0,
                        "n_btm_add_y": btm_add_models[0]["ny"] if btm_add_models else 0,
                    })

        # ════════════════════════════════════════════════════════════════════
        # SECTION 3: MATERIAL PRICES INPUTS (اسعار المواد الخام material prices)
        # ════════════════════════════════════════════════════════════════════
        with st.container(border=True):
            st.markdown(
                """
                <div class="cs-inputs-header-badge" style="
                    background: linear-gradient(135deg, #b45309 0%, #d97706 100%);
                    color: #ffffff !important;
                    padding: 4px 12px;
                    border-radius: 6px;
                    font-weight: 800;
                    font-size: 15px;
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    border-left: 4px solid #fde047;
                ">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:16px;">💰</span>
                        <span style="color:#ffffff !important;">اسعار المواد الخام material prices</span>
                    </div>
                    <span style="background: rgba(255,255,255,0.22); color:#ffffff !important; padding: 1px 8px; border-radius: 12px; font-size: 11.5px; font-weight: 700;">
                        Unit Prices & Rates
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            def_p_steel = float(cfg_val("cs_price_steel", 40000.0))
            def_p_cement = float(cfg_val("cs_price_cement", 4000.0))
            def_p_gravel = float(cfg_val("cs_price_gravel", 600.0))
            def_p_sand = float(cfg_val("cs_price_sand", 200.0))
            def_p_labor = float(cfg_val("cs_price_labor", 2000.0))

            pr_c1, pr_c2, pr_c3, pr_c4, pr_c5 = st.columns(5)
            with pr_c1:
                price_steel_in = st.number_input(
                    "سعر طن الحديد (EGP) — Default 40000",
                    min_value=0.0, max_value=500000.0, value=def_p_steel, step=500.0,
                    help="سعر توريد طن حديد التسليح تسليم الموقع (Default 40,000 ج.م)",
                    key="cs_price_steel",
                )
            with pr_c2:
                price_cement_in = st.number_input(
                    "سعر طن الاسمنت (EGP) — Default 4000",
                    min_value=0.0, max_value=50000.0, value=def_p_cement, step=100.0,
                    help="سعر توريد طن الأسمنت البورتلاندي تسليم الموقع (Default 4,000 ج.م)",
                    key="cs_price_cement",
                )
            with pr_c3:
                price_gravel_in = st.number_input(
                    "سعر متر مكعب زلط (EGP) — Default 600",
                    min_value=0.0, max_value=10000.0, value=def_p_gravel, step=25.0,
                    help="سعر المتر المكعب من السن / الزلط المتدرج (Default 600 ج.م)",
                    key="cs_price_gravel",
                )
            with pr_c4:
                price_sand_in = st.number_input(
                    "سعر متر مكعب رمل (EGP) — Default 200",
                    min_value=0.0, max_value=5000.0, value=def_p_sand, step=10.0,
                    help="سعر المتر المكعب من الرمل الحرش النظيف (Default 200 ج.م)",
                    key="cs_price_sand",
                )
            with pr_c5:
                price_labor_in = st.number_input(
                    "مصنعية المتر المكعب (EGP) — Default 2000",
                    min_value=0.0, max_value=20000.0, value=def_p_labor, step=50.0,
                    help="مصنعية المتر المكعب خرسانة مسلحة نجارة وحدادة وصب وتشغيل (Default 2,000 ج.م)",
                    key="cs_price_labor",
                )

        st.markdown("---")

        # ── Auto-persist all current inputs to user_settings.json on change ──
        lap_opts_list = [40, 45, 50, 60]
        st_dia_opts_list = [6, 8, 10, 12]
        phi_main_opts_list = [10, 12, 14, 16, 18, 20, 22, 25, 28, 32]
        tie_opts_list = ["Box (كانة صندوقية)", "Automatic (كانة أوتوماتيك)"]

        cfg_updates = {
            "cs_n_types": int(n_types_in),
            "cs_col_h": float(col_h_in),
            "cs_t_slab": float(t_slab_in),
            "cs_fcu": float(fcu_in),
            "cs_is_top_floor_idx": 1 if "yes" in is_top_floor_sel.lower() else 0,
            "cs_has_footing_dowels_idx": 1 if "yes" in has_footing_dowels_sel.lower() else 0,
            "cs_lap_factor_idx": lap_opts_list.index(lap_factor_sel) if lap_factor_sel in lap_opts_list else 2,
            "cs_n_st_m": int(n_st_m),
            "cs_phi_st_idx": st_dia_opts_list.index(phi_st) if phi_st in st_dia_opts_list else 1,
            "cs_fs_n_slabs": int(n_slabs_fs_in),
            "cs_fs_ts": float(ts_fs_in),
            "cs_fs_fcu": float(fcu_fs_in),
            "cs_fs_phi_btm": int(phi_btm_mesh_in),
            "cs_fs_nb_btm": int(nb_btm_mesh_in),
            "cs_fs_phi_top": int(phi_top_mesh_in),
            "cs_fs_nb_top": int(nb_top_mesh_in),
            "cs_price_steel": float(price_steel_in),
            "cs_price_cement": float(price_cement_in),
            "cs_price_gravel": float(price_gravel_in),
            "cs_price_sand": float(price_sand_in),
            "cs_price_labor": float(price_labor_in),
        }
        for idx, c in enumerate(col_inputs):
            cfg_updates[f"cs_name_{idx}"] = str(c["name"])
            cfg_updates[f"cs_b_{idx}"] = float(c["b"])
            cfg_updates[f"cs_t_{idx}"] = float(c["t"])
            cfg_updates[f"cs_ncols_{idx}"] = int(c["n_cols"])
            cfg_updates[f"cs_nb_{idx}"] = int(c["n_bars"])
            cfg_updates[f"cs_phi_idx_{idx}"] = phi_main_opts_list.index(c["phi_main"]) if c["phi_main"] in phi_main_opts_list else 3
            cfg_updates[f"cs_nrows_{idx}"] = int(c["n_rows"])
            cfg_updates[f"cs_tietype_idx_{idx}"] = tie_opts_list.index(c["tie_type"]) if c["tie_type"] in tie_opts_list else 0
            cfg_updates[f"cs_cut_length_{idx}"] = float(c["cut_length_m"])

        for s_idx, s in enumerate(slab_inputs):
            cfg_updates[f"cs_fs_name_{s_idx}"] = str(s["name"])
            cfg_updates[f"cs_fs_lx_{s_idx}"] = float(s["lx"])
            cfg_updates[f"cs_fs_ly_{s_idx}"] = float(s["ly"])
            cfg_updates[f"cs_fs_n_rep_{s_idx}"] = int(s["n_rep"])
            cfg_updates[f"cs_fs_n_top_models_{s_idx}"] = len(s.get("top_add_models", []))
            for k, tm in enumerate(s.get("top_add_models", [])):
                cfg_updates[f"cs_fs_top_add_name_{s_idx}_{k}"] = str(tm["name"])
                cfg_updates[f"cs_fs_top_add_phi_{s_idx}_{k}"] = int(tm["phi"])
                cfg_updates[f"cs_fs_top_add_lx_{s_idx}_{k}"] = float(tm["lx"])
                cfg_updates[f"cs_fs_top_add_ly_{s_idx}_{k}"] = float(tm["ly"])
                cfg_updates[f"cs_fs_top_add_nx_{s_idx}_{k}"] = int(tm["nx"])
                cfg_updates[f"cs_fs_top_add_ny_{s_idx}_{k}"] = int(tm["ny"])
                cfg_updates[f"cs_fs_top_add_nz_{s_idx}_{k}"] = int(tm["n_zones"])
            cfg_updates[f"cs_fs_n_btm_models_{s_idx}"] = len(s.get("btm_add_models", []))
            for k, bm in enumerate(s.get("btm_add_models", [])):
                cfg_updates[f"cs_fs_btm_add_name_{s_idx}_{k}"] = str(bm["name"])
                cfg_updates[f"cs_fs_btm_add_phi_{s_idx}_{k}"] = int(bm["phi"])
                cfg_updates[f"cs_fs_btm_add_lx_{s_idx}_{k}"] = float(bm["lx"])
                cfg_updates[f"cs_fs_btm_add_ly_{s_idx}_{k}"] = float(bm["ly"])
                cfg_updates[f"cs_fs_btm_add_nx_{s_idx}_{k}"] = int(bm["nx"])
                cfg_updates[f"cs_fs_btm_add_ny_{s_idx}_{k}"] = int(bm["ny"])
                cfg_updates[f"cs_fs_btm_add_nz_{s_idx}_{k}"] = int(bm["n_zones"])

        if "cfg" not in st.session_state:
            load_settings()
        has_cfg_changes = False
        for k, v in cfg_updates.items():
            if st.session_state["cfg"].get(k) != v:
                st.session_state["cfg"][k] = v
                has_cfg_changes = True
        if has_cfg_changes:
            save_settings()

        # ────────────────────────────────────────────────────────────────────
        # COMPUTATIONS & MULTI-MODEL SURVEY ENGINE
        # ────────────────────────────────────────────────────────────────────
        is_top = "yes" in is_top_floor_sel.lower()
        has_footing = "yes" in has_footing_dowels_sel.lower()
        cover_cm = 2.5

        # 1. COLUMNS COMPUTATIONS
        col_results = []
        for c in col_inputs:
            c_b = c["b"]
            c_t = c["t"]
            c_nc = c["n_cols"]
            c_nb = c["n_bars"]
            c_phi = c["phi_main"]
            c_nr = c["n_rows"]
            c_tie = c["tie_type"]
            c_name = c["name"]
            c_L_bar_single_m = c["cut_length_m"]
            c_L_bar_single_cm = c_L_bar_single_m * 100.0
            c_calc_length_m = c["calc_length_m"]
            c_L_foot_cm = c["L_foot_cm"]

            # Main Rebar Length & Weight
            c_w_main_unit = (c_phi ** 2) / 162.0
            c_w_main_single_kg = c_nb * c_L_bar_single_m * c_w_main_unit
            c_w_main_total_kg = c_w_main_single_kg * c_nc
            c_w_main_total_ton = c_w_main_total_kg / 1000.0

            # Stirrups Length & Weight
            c_b_core = max(c_b - 2.0 * cover_cm, 1.0)
            c_t_core = max(c_t - 2.0 * cover_cm, 1.0)
            c_hook_len = max(8.0, 10.0 * (phi_st / 10.0))

            is_auto_tie = "auto" in c_tie.lower() or "أوتوماتيك" in c_tie
            if is_auto_tie:
                c_t_core_in = max(c_t_core * 0.5, 5.0)
                c_b_core_in = c_b_core
                c_L_tie_single_cm = 2.0 * (c_b_core + c_t_core) + 2.0 * (c_b_core_in + c_t_core_in) + 4.0 * c_hook_len
            else:
                c_L_tie_single_cm = 2.0 * (c_b_core + c_t_core) + 2.0 * c_hook_len

            c_L_tie_single_m = c_L_tie_single_cm / 100.0
            c_n_ties_per_col = max(3, int(math.ceil((col_h_in / 100.0) * n_st_m)))
            c_w_st_unit = (phi_st ** 2) / 162.0
            c_w_st_single_kg = c_n_ties_per_col * c_L_tie_single_m * c_w_st_unit
            c_w_st_total_kg = c_w_st_single_kg * c_nc
            c_w_st_total_ton = c_w_st_total_kg / 1000.0

            # Concrete Volume & Combined Steel Weight
            c_vol_single_m3 = (c_b / 100.0) * (c_t / 100.0) * (col_h_in / 100.0)
            c_vol_total_m3 = c_vol_single_m3 * c_nc
            c_w_steel_total_kg = c_w_main_total_kg + c_w_st_total_kg
            c_w_steel_total_ton = c_w_steel_total_kg / 1000.0
            c_steel_rate = (c_w_steel_total_kg / c_vol_total_m3) if c_vol_total_m3 > 0 else 0.0

            col_results.append({
                "index": c["index"],
                "name": c_name,
                "b": c_b,
                "t": c_t,
                "n_cols": c_nc,
                "n_bars": c_nb,
                "phi_main": c_phi,
                "n_rows": c_nr,
                "tie_type": c_tie,
                "L_bar_cm": c_L_bar_single_cm,
                "L_bar_m": c_L_bar_single_m,
                "calc_length_m": c_calc_length_m,
                "L_foot_cm": c_L_foot_cm,
                "w_main_total_kg": c_w_main_total_kg,
                "w_main_total_ton": c_w_main_total_ton,
                "n_ties_per_col": c_n_ties_per_col,
                "L_tie_cm": c_L_tie_single_cm,
                "L_tie_m": c_L_tie_single_m,
                "w_st_total_kg": c_w_st_total_kg,
                "w_st_total_ton": c_w_st_total_ton,
                "vol_col_single_m3": c_vol_single_m3,
                "vol_col_total_m3": c_vol_total_m3,
                "w_steel_total_kg": c_w_steel_total_kg,
                "w_steel_total_ton": c_w_steel_total_ton,
                "steel_rate_kg_m3": c_steel_rate,
            })

        # Columns Totals
        total_cols_all = sum(r["n_cols"] for r in col_results)
        total_vol_all = sum(r["vol_col_total_m3"] for r in col_results)
        total_w_main_kg_all = sum(r["w_main_total_kg"] for r in col_results)
        total_w_main_ton_all = total_w_main_kg_all / 1000.0
        total_w_st_kg_all = sum(r["w_st_total_kg"] for r in col_results)
        total_w_st_ton_all = total_w_st_kg_all / 1000.0
        total_w_steel_kg_all = total_w_main_kg_all + total_w_st_kg_all
        total_w_steel_ton_all = total_w_steel_kg_all / 1000.0
        overall_steel_rate = (total_w_steel_kg_all / total_vol_all) if total_vol_all > 0 else 0.0

        # 2. FLAT SLABS COMPUTATIONS
        slab_results = []
        for s in slab_inputs:
            s_name = s["name"]
            s_lx = s["lx"]
            s_ly = s["ly"]
            s_ts = s["ts"]
            s_n_rep = s["n_rep"]
            s_phi_bx = s["phi_btm_x"]
            s_phi_by = s["phi_btm_y"]
            s_nb_bx = s["nb_btm_x"]
            s_nb_by = s["nb_btm_y"]
            s_phi_tx = s["phi_top_x"]
            s_phi_ty = s["phi_top_y"]
            s_nb_tx = s["nb_top_x"]
            s_nb_ty = s["nb_top_y"]

            s_area_single = s_lx * s_ly
            s_area_total = s_area_single * s_n_rep
            s_vol_single = s_lx * s_ly * (s_ts / 100.0)
            s_vol_total = s_vol_single * s_n_rep

            # Bottom Mesh: X runs along Y, Y runs along X
            s_n_runs_bx = int(math.ceil(s_ly * s_nb_bx))
            s_L_cut_bx = s_lx + 0.20
            s_w_bx_kg = s_n_runs_bx * s_L_cut_bx * ((s_phi_bx ** 2) / 162.0) * s_n_rep
            s_w_bx_ton = s_w_bx_kg / 1000.0

            s_n_runs_by = int(math.ceil(s_lx * s_nb_by))
            s_L_cut_by = s_ly + 0.20
            s_w_by_kg = s_n_runs_by * s_L_cut_by * ((s_phi_by ** 2) / 162.0) * s_n_rep
            s_w_by_ton = s_w_by_kg / 1000.0

            # Top Mesh: X runs along Y, Y runs along X
            s_n_runs_tx = int(math.ceil(s_ly * s_nb_tx))
            s_L_cut_tx = s_lx + 0.20
            s_w_tx_kg = s_n_runs_tx * s_L_cut_tx * ((s_phi_tx ** 2) / 162.0) * s_n_rep
            s_w_tx_ton = s_w_tx_kg / 1000.0

            s_n_runs_ty = int(math.ceil(s_lx * s_nb_ty))
            s_L_cut_ty = s_ly + 0.20
            s_w_ty_kg = s_n_runs_ty * s_L_cut_ty * ((s_phi_ty ** 2) / 162.0) * s_n_rep
            s_w_ty_ton = s_w_ty_kg / 1000.0

            # Chairs supporting top mesh (1 chair / m2, phi=10mm)
            s_n_chairs = int(math.ceil(s_area_single * 1.0)) * s_n_rep
            s_L_chair_m = (2.0 * max(s_ts - 5.0, 5.0) + 40.0) / 100.0
            s_w_chairs_kg = s_n_chairs * s_L_chair_m * (100.0 / 162.0)
            s_w_chairs_ton = s_w_chairs_kg / 1000.0

            # Multi-model Additional Top Reinforcement (Density in bars / linear meter)
            top_add_models_res = []
            s_w_top_add_total_kg = 0.0
            for tm in s.get("top_add_models", []):
                tm_name = tm.get("name", "T1")
                tm_phi = int(tm.get("phi", 12))
                tm_lx = float(tm.get("lx", 0.0))
                tm_ly = float(tm.get("ly", 0.0))
                tm_nx_m = float(tm.get("nx", 0)) # bars/m' in X (runs along width Ly)
                tm_ny_m = float(tm.get("ny", 0)) # bars/m' in Y (runs along length Lx)
                tm_nz = int(tm.get("n_zones", 1))

                tm_n_rx = int(math.ceil(tm_ly * tm_nx_m)) if (tm_nx_m > 0 and tm_ly > 0) else 0
                tm_lin_x = tm_lx * tm_n_rx * tm_nz * s_n_rep if (tm_n_rx > 0 and tm_lx > 0) else 0.0
                tm_w_x_kg = tm_lin_x * ((tm_phi ** 2) / 162.0)

                tm_n_ry = int(math.ceil(tm_lx * tm_ny_m)) if (tm_ny_m > 0 and tm_lx > 0) else 0
                tm_lin_y = tm_ly * tm_n_ry * tm_nz * s_n_rep if (tm_n_ry > 0 and tm_ly > 0) else 0.0
                tm_w_y_kg = tm_lin_y * ((tm_phi ** 2) / 162.0)

                tm_w_tot_kg = tm_w_x_kg + tm_w_y_kg
                s_w_top_add_total_kg += tm_w_tot_kg

                top_add_models_res.append({
                    "name": tm_name,
                    "phi": tm_phi,
                    "lx": tm_lx,
                    "ly": tm_ly,
                    "nx": tm_nx_m,
                    "ny": tm_ny_m,
                    "n_runs_x": tm_n_rx,
                    "n_runs_y": tm_n_ry,
                    "n_zones": tm_nz,
                    "lin_x": tm_lin_x,
                    "lin_y": tm_lin_y,
                    "w_x_kg": tm_w_x_kg,
                    "w_y_kg": tm_w_y_kg,
                    "w_total_kg": tm_w_tot_kg,
                })

            # Fallback if top_add_models empty
            if not top_add_models_res and (s.get("n_top_add_x", 0) > 0 or s.get("n_top_add_y", 0) > 0):
                tm_phi = int(s.get("phi_top_add", 12))
                tm_lx = float(s.get("add_top_lx", 0.0))
                tm_ly = float(s.get("add_top_ly", 0.0))
                tm_nx_m = float(s.get("n_top_add_x", 0))
                tm_ny_m = float(s.get("n_top_add_y", 0))
                tm_n_rx = int(math.ceil(tm_ly * tm_nx_m)) if (tm_nx_m > 0 and tm_ly > 0) else int(tm_nx_m)
                tm_n_ry = int(math.ceil(tm_lx * tm_ny_m)) if (tm_ny_m > 0 and tm_lx > 0) else int(tm_ny_m)
                tm_lin_x = tm_lx * tm_n_rx * s_n_rep if (tm_n_rx > 0 and tm_lx > 0) else 0.0
                tm_w_x_kg = tm_lin_x * ((tm_phi ** 2) / 162.0)
                tm_lin_y = tm_ly * tm_n_ry * s_n_rep if (tm_ny > 0 and tm_ly > 0) else 0.0
                tm_w_y_kg = tm_lin_y * ((tm_phi ** 2) / 162.0)
                s_w_top_add_total_kg = tm_w_x_kg + tm_w_y_kg
                top_add_models_res.append({
                    "name": "T1", "phi": tm_phi, "lx": tm_lx, "ly": tm_ly,
                    "nx": tm_nx_m, "ny": tm_ny_m, "n_runs_x": tm_n_rx, "n_runs_y": tm_n_ry, "n_zones": 1,
                    "lin_x": tm_lin_x, "lin_y": tm_lin_y,
                    "w_x_kg": tm_w_x_kg, "w_y_kg": tm_w_y_kg, "w_total_kg": s_w_top_add_total_kg,
                })

            # Multi-model Additional Bottom Reinforcement (Density in bars / linear meter)
            btm_add_models_res = []
            s_w_btm_add_total_kg = 0.0
            for bm in s.get("btm_add_models", []):
                bm_name = bm.get("name", "B1")
                bm_phi = int(bm.get("phi", 12))
                bm_lx = float(bm.get("lx", 0.0))
                bm_ly = float(bm.get("ly", 0.0))
                bm_nx_m = float(bm.get("nx", 0)) # bars/m' in X (runs along width Ly)
                bm_ny_m = float(bm.get("ny", 0)) # bars/m' in Y (runs along length Lx)
                bm_nz = int(bm.get("n_zones", 1))

                bm_n_rx = int(math.ceil(bm_ly * bm_nx_m)) if (bm_nx_m > 0 and bm_ly > 0) else 0
                bm_lin_x = bm_lx * bm_n_rx * bm_nz * s_n_rep if (bm_n_rx > 0 and bm_lx > 0) else 0.0
                bm_w_x_kg = bm_lin_x * ((bm_phi ** 2) / 162.0)

                bm_n_ry = int(math.ceil(bm_lx * bm_ny_m)) if (bm_ny_m > 0 and bm_lx > 0) else 0
                bm_lin_y = bm_ly * bm_n_ry * bm_nz * s_n_rep if (bm_n_ry > 0 and bm_ly > 0) else 0.0
                bm_w_y_kg = bm_lin_y * ((bm_phi ** 2) / 162.0)

                bm_w_tot_kg = bm_w_x_kg + bm_w_y_kg
                s_w_btm_add_total_kg += bm_w_tot_kg

                btm_add_models_res.append({
                    "name": bm_name,
                    "phi": bm_phi,
                    "lx": bm_lx,
                    "ly": bm_ly,
                    "nx": bm_nx_m,
                    "ny": bm_ny_m,
                    "n_runs_x": bm_n_rx,
                    "n_runs_y": bm_n_ry,
                    "n_zones": bm_nz,
                    "lin_x": bm_lin_x,
                    "lin_y": bm_lin_y,
                    "w_x_kg": bm_w_x_kg,
                    "w_y_kg": bm_w_y_kg,
                    "w_total_kg": bm_w_tot_kg,
                })

            # Fallback if btm_add_models empty
            if not btm_add_models_res and (s.get("n_btm_add_x", 0) > 0 or s.get("n_btm_add_y", 0) > 0):
                bm_phi = int(s.get("phi_btm_add", 12))
                bm_lx = float(s.get("add_btm_lx", 0.0))
                bm_ly = float(s.get("add_btm_ly", 0.0))
                bm_nx_m = float(s.get("n_btm_add_x", 0))
                bm_ny_m = float(s.get("n_btm_add_y", 0))
                bm_n_rx = int(math.ceil(bm_ly * bm_nx_m)) if (bm_nx_m > 0 and bm_ly > 0) else int(bm_nx_m)
                bm_n_ry = int(math.ceil(bm_lx * bm_ny_m)) if (bm_ny_m > 0 and bm_lx > 0) else int(bm_ny_m)
                bm_lin_x = bm_lx * bm_n_rx * s_n_rep if (bm_n_rx > 0 and bm_lx > 0) else 0.0
                bm_w_x_kg = bm_lin_x * ((bm_phi ** 2) / 162.0)
                bm_lin_y = bm_ly * bm_n_ry * s_n_rep if (bm_ny > 0 and bm_ly > 0) else 0.0
                bm_w_y_kg = bm_lin_y * ((bm_phi ** 2) / 162.0)
                s_w_btm_add_total_kg = bm_w_x_kg + bm_w_y_kg
                btm_add_models_res.append({
                    "name": "B1", "phi": bm_phi, "lx": bm_lx, "ly": bm_ly,
                    "nx": bm_nx_m, "ny": bm_ny_m, "n_runs_x": bm_n_rx, "n_runs_y": bm_n_ry, "n_zones": 1,
                    "lin_x": bm_lin_x, "lin_y": bm_lin_y,
                    "w_x_kg": bm_w_x_kg, "w_y_kg": bm_w_y_kg, "w_total_kg": s_w_btm_add_total_kg,
                })

            s_w_add_total_kg = s_w_top_add_total_kg + s_w_btm_add_total_kg

            s_w_steel_slab_kg = s_w_bx_kg + s_w_by_kg + s_w_tx_kg + s_w_ty_kg + s_w_chairs_kg + s_w_add_total_kg
            s_w_steel_slab_ton = s_w_steel_slab_kg / 1000.0
            s_steel_rate = (s_w_steel_slab_kg / s_vol_total) if s_vol_total > 0 else 0.0

            slab_results.append({
                "index": s["index"],
                "name": s_name,
                "lx": s_lx,
                "ly": s_ly,
                "ts": s_ts,
                "fcu": s.get("fcu", 350.0),
                "n_rep": s_n_rep,
                "area_total_m2": s_area_total,
                "vol_total_m3": s_vol_total,
                "vol_single_m3": s_vol_single,
                "phi_bx": s_phi_bx,
                "phi_by": s_phi_by,
                "nb_bx": s_nb_bx,
                "nb_by": s_nb_by,
                "phi_tx": s_phi_tx,
                "phi_ty": s_phi_ty,
                "nb_tx": s_nb_tx,
                "nb_ty": s_nb_ty,
                "nb_x": s_nb_bx,
                "nb_y": s_nb_by,
                "n_runs_bx": s_n_runs_bx,
                "n_runs_by": s_n_runs_by,
                "n_runs_tx": s_n_runs_tx,
                "n_runs_ty": s_n_runs_ty,
                "L_cut_bx": s_L_cut_bx,
                "L_cut_by": s_L_cut_by,
                "L_cut_tx": s_L_cut_tx,
                "L_cut_ty": s_L_cut_ty,
                "w_bx_kg": s_w_bx_kg,
                "w_bx_ton": s_w_bx_ton,
                "w_by_kg": s_w_by_kg,
                "w_by_ton": s_w_by_ton,
                "w_tx_kg": s_w_tx_kg,
                "w_tx_ton": s_w_tx_ton,
                "w_ty_kg": s_w_ty_kg,
                "w_ty_ton": s_w_ty_ton,
                "n_chairs": s_n_chairs,
                "L_chair_m": s_L_chair_m,
                "w_chairs_kg": s_w_chairs_kg,
                # Multi-model additional rebar lists
                "top_add_models": s.get("top_add_models", []),
                "btm_add_models": s.get("btm_add_models", []),
                "top_add_models_res": top_add_models_res,
                "btm_add_models_res": btm_add_models_res,
                "w_top_add_kg": s_w_top_add_total_kg,
                "w_btm_add_kg": s_w_btm_add_total_kg,
                "w_add_total_kg": s_w_add_total_kg,
                "w_steel_total_kg": s_w_steel_slab_kg,
                "w_steel_total_ton": s_w_steel_slab_ton,
                "steel_rate_kg_m3": s_steel_rate,
                # Backwards compatible single-model fields
                "add_top_lx": s.get("add_top_lx", 0.0),
                "add_top_ly": s.get("add_top_ly", 0.0),
                "n_top_add_x": s.get("n_top_add_x", 0),
                "n_top_add_y": s.get("n_top_add_y", 0),
                "phi_top_add": s.get("phi_top_add", 12),
                "add_btm_lx": s.get("add_btm_lx", 0.0),
                "add_btm_ly": s.get("add_btm_ly", 0.0),
                "n_btm_add_x": s.get("n_btm_add_x", 0),
                "n_btm_add_y": s.get("n_btm_add_y", 0),
                "phi_btm_add": s.get("phi_btm_add", 12),
            })

        total_slabs_count = sum(s["n_rep"] for s in slab_results)
        total_vol_slabs_all = sum(s["vol_total_m3"] for s in slab_results)
        total_area_slabs_all = sum(s.get("area_total_m2", 0.0) for s in slab_results)
        total_w_slabs_steel_kg = sum(s["w_steel_total_kg"] for s in slab_results)
        total_w_slabs_steel_ton = total_w_slabs_steel_kg / 1000.0

        # GRAND COMBINED TOTALS (Columns + Flat Slabs)
        grand_vol_concrete_all = total_vol_all + total_vol_slabs_all
        grand_w_steel_kg_all = total_w_steel_kg_all + total_w_slabs_steel_kg
        grand_w_steel_ton_all = grand_w_steel_kg_all / 1000.0
        grand_overall_steel_rate = (grand_w_steel_kg_all / grand_vol_concrete_all) if grand_vol_concrete_all > 0 else 0.0

        # MATERIALS QUANTITIES
        cement_cols_tons = (total_vol_all * float(fcu_in)) / 1000.0
        cement_slabs_tons = (total_vol_slabs_all * float(fcu_fs_in)) / 1000.0
        grand_cement_tons = cement_cols_tons + cement_slabs_tons
        grand_cement_bags = int(round(grand_cement_tons * 20.0))
        grand_sand_m3 = grand_vol_concrete_all * 0.40
        grand_gravel_m3 = grand_vol_concrete_all * 0.80
        water_cols_liters = total_vol_all * float(fcu_in) * 0.50
        water_slabs_liters = total_vol_slabs_all * float(fcu_fs_in) * 0.50
        grand_water_liters = water_cols_liters + water_slabs_liters

        # FINANCIAL PRICING CALCULATIONS (EGP / ج.م)
        cost_steel_total = grand_w_steel_ton_all * float(price_steel_in)
        cost_cement_total = grand_cement_tons * float(price_cement_in)
        cost_gravel_total = grand_gravel_m3 * float(price_gravel_in)
        cost_sand_total = grand_sand_m3 * float(price_sand_in)
        cost_labor_total = grand_vol_concrete_all * float(price_labor_in)
        cost_materials_total = cost_steel_total + cost_cement_total + cost_gravel_total + cost_sand_total
        cost_grand_total = cost_materials_total + cost_labor_total
        cost_per_m3_all_inclusive = (cost_grand_total / grand_vol_concrete_all) if grand_vol_concrete_all > 0 else 0.0
        cost_per_m2_slab = (cost_grand_total / total_area_slabs_all) if total_area_slabs_all > 0 else 0.0

        # Cost breakdown per element type (Columns & Flat Slabs)
        cost_steel_cols = total_w_steel_ton_all * float(price_steel_in)
        cost_cement_cols = cement_cols_tons * float(price_cement_in)
        cost_gravel_cols = (total_vol_all * 0.80) * float(price_gravel_in)
        cost_sand_cols = (total_vol_all * 0.40) * float(price_sand_in)
        cost_labor_cols = total_vol_all * float(price_labor_in)
        cost_cols_total = cost_steel_cols + cost_cement_cols + cost_gravel_cols + cost_sand_cols + cost_labor_cols
        rate_cols_per_m3 = (cost_cols_total / total_vol_all) if total_vol_all > 0 else 0.0

        cost_steel_cols_m3 = (cost_steel_cols / total_vol_all) if total_vol_all > 0 else 0.0
        cost_cement_cols_m3 = (cost_cement_cols / total_vol_all) if total_vol_all > 0 else 0.0
        cost_gravel_cols_m3 = (cost_gravel_cols / total_vol_all) if total_vol_all > 0 else 0.0
        cost_sand_cols_m3 = (cost_sand_cols / total_vol_all) if total_vol_all > 0 else 0.0

        cost_steel_slabs = total_w_slabs_steel_ton * float(price_steel_in)
        cost_cement_slabs = cement_slabs_tons * float(price_cement_in)
        cost_gravel_slabs = (total_vol_slabs_all * 0.80) * float(price_gravel_in)
        cost_sand_slabs = (total_vol_slabs_all * 0.40) * float(price_sand_in)
        cost_labor_slabs = total_vol_slabs_all * float(price_labor_in)
        cost_slabs_total = cost_steel_slabs + cost_cement_slabs + cost_gravel_slabs + cost_sand_slabs + cost_labor_slabs
        rate_slabs_per_m3 = (cost_slabs_total / total_vol_slabs_all) if total_vol_slabs_all > 0 else 0.0

        cost_steel_slabs_m3 = (cost_steel_slabs / total_vol_slabs_all) if total_vol_slabs_all > 0 else 0.0
        cost_cement_slabs_m3 = (cost_cement_slabs / total_vol_slabs_all) if total_vol_slabs_all > 0 else 0.0
        cost_gravel_slabs_m3 = (cost_gravel_slabs / total_vol_slabs_all) if total_vol_slabs_all > 0 else 0.0
        cost_sand_slabs_m3 = (cost_sand_slabs / total_vol_slabs_all) if total_vol_slabs_all > 0 else 0.0

        # ────────────────────────────────────────────────────────────────────
        # INTEGRATED CAD DRAWINGS & BBS VISUALIZER (Columns + Flat Slabs)
        # ────────────────────────────────────────────────────────────────────
        with st.expander(
            f"📐 المخططات الإنشائية وتفريد التسليح للعناصر ({len(col_results)} نماذج أعمدة + {len(slab_results)} نماذج بلاطات)",
            expanded=False,
            key="cs_draw_exp",
            on_change="rerun",
        ):
            if st.session_state.get("cs_draw_exp", False):
                all_drawings = []
                for idx, r in enumerate(col_results):
                    fig_i = draw_column_unified_sheet(
                        b_cm=r["b"],
                        t_cm=r["t"],
                        H_col_cm=col_h_in,
                        t_slab_cm=t_slab_in,
                        n_bars=r["n_bars"],
                        phi_mm=r["phi_main"],
                        phi_st_mm=phi_st,
                        n_st_per_m=n_st_m,
                        is_top_floor=is_top,
                        lap_factor=lap_factor_sel,
                        tie_type=r["tie_type"],
                        n_rows=r["n_rows"],
                        cover=cover_cm,
                        has_footing_dowels=has_footing,
                        L_foot_cm=r.get("L_foot_cm", 25.0 if has_footing else 0.0),
                        L_bar_custom_m=r["L_bar_m"],
                    )
                    b64_i = fig_to_base64(fig_i)
                    all_drawings.append({
                        "type": "column",
                        "fig": fig_i,
                        "img_b64": b64_i,
                        "name": r["name"],
                        "b": r["b"],
                        "t": r["t"],
                        "n_bars": r["n_bars"],
                        "phi_main": r["phi_main"],
                    })

                slab_drawings = []
                for s_idx, s in enumerate(slab_results):
                    fig_s = draw_flat_slab_survey_sheet(
                        lx_m=s["lx"],
                        ly_m=s["ly"],
                        ts_cm=s["ts"],
                        phi_btm_x=s["phi_bx"],
                        phi_btm_y=s["phi_by"],
                        phi_top_x=s["phi_tx"],
                        phi_top_y=s["phi_ty"],
                        nb_x=s["nb_bx"],
                        nb_y=s["nb_by"],
                        nb_top_x=s["nb_tx"],
                        nb_top_y=s["nb_ty"],
                        name=s["name"],
                        n_rep=s["n_rep"],
                        add_top_lx=s.get("add_top_lx", 0.0),
                        add_top_ly=s.get("add_top_ly", 0.0),
                        n_top_add_x=s.get("n_top_add_x", 0),
                        n_top_add_y=s.get("n_top_add_y", 0),
                        phi_top_add=s.get("phi_top_add", 12),
                        add_btm_lx=s.get("add_btm_lx", 0.0),
                        add_btm_ly=s.get("add_btm_ly", 0.0),
                        n_btm_add_x=s.get("n_btm_add_x", 0),
                        n_btm_add_y=s.get("n_btm_add_y", 0),
                        phi_btm_add=s.get("phi_btm_add", 12),
                        top_add_models=s.get("top_add_models", []),
                        btm_add_models=s.get("btm_add_models", []),
                    )
                    b64_s = fig_to_base64(fig_s)
                    slab_drawings.append({
                        "type": "slab",
                        "fig": fig_s,
                        "img_b64": b64_s,
                        "name": s["name"],
                        "lx": s["lx"],
                        "ly": s["ly"],
                        "ts": s["ts"],
                        "n_rep": s["n_rep"],
                    })

                combined_all_drawings = all_drawings + slab_drawings
                view_mode_col1, view_mode_col2 = st.columns([2, 1])
                with view_mode_col1:
                    draw_view_mode = st.radio(
                        "طريقة استعراض الرسومات الهندسية:",
                        options=["📑 استعراض بنظام التبويبات (Tabs لكل عنصر)", "📜 عرض كافة الرسومات معاً"],
                        index=0,
                        horizontal=True,
                        key="cs_draw_view_mode",
                    )
                with view_mode_col2:
                    st.caption(f"يتوفر رسم تنفيذي وتفريد تسليح مستقل لـ {len(col_results)} نماذج أعمدة و {len(slab_results)} نماذج بلاطات.")

                if "تبويبات" in draw_view_mode:
                    tab_labels = []
                    for d in combined_all_drawings:
                        if d.get("type") == "column":
                            tab_labels.append(f"🏛️ عمود {d['name']} ({d['b']:.0f}×{d['t']:.0f} cm)")
                        else:
                            tab_labels.append(f"🟦 بلاطة {d['name']} ({d['lx']:.1f}×{d['ly']:.1f} m)")

                    draw_tabs = st.tabs(tab_labels)
                    for i, d in enumerate(combined_all_drawings):
                        with draw_tabs[i]:
                            if d.get("type") == "column":
                                header_bg = "linear-gradient(135deg, #1e3a8a 0%, #1e40af 50%, #2563eb 100%)"
                                border_col = "#60a5fa"
                                icon_str = "🏛️"
                                tag_str = f"{d['b']:.0f} × {d['t']:.0f} cm &nbsp;|&nbsp; {d['n_bars']} Φ {d['phi_main']} mm"
                                title_str = f"المخطط الإنشائي وتفريد التسليح لنموذج عمود: <b style='color:#93c5fd; font-size:28px;'>{d['name']}</b>"
                            else:
                                header_bg = "linear-gradient(135deg, #065f46 0%, #047857 50%, #059669 100%)"
                                border_col = "#34d399"
                                icon_str = "🟦"
                                tag_str = f"{d['lx']:.1f} × {d['ly']:.1f} m &nbsp;|&nbsp; ts = {d['ts']:.0f} cm"
                                title_str = f"المخطط الإنشائي وتفريد التسليح لنموذج بلاطة مسطحة: <b style='color:#a7f3d0; font-size:28px;'>{d['name']}</b>"

                            st.markdown(
                                f"""
                                <div style="
                                    background: {header_bg};
                                    color: #ffffff !important;
                                    padding: 15px 24px;
                                    border-radius: 10px;
                                    font-size: 26px;
                                    font-weight: 900;
                                    margin: 8px 0 16px 0;
                                    display: flex;
                                    justify-content: space-between;
                                    align-items: center;
                                    box-shadow: 0 5px 18px rgba(30, 58, 138, 0.28);
                                    border-right: 8px solid {border_col};
                                ">
                                    <div style="display:flex; align-items:center; gap:12px;">
                                        <span style="font-size:28px;">{icon_str}</span>
                                        <span style="color:#ffffff !important;">{title_str}</span>
                                    </div>
                                    <span dir="ltr" style="background:rgba(255,255,255,0.22); color:#ffffff !important; padding:6px 18px; border-radius:16px; font-size:20px; font-weight:900; border:1.5px solid rgba(255,255,255,0.40);">
                                        {tag_str}
                                    </span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            st.pyplot(d["fig"], use_container_width=True)

                            # High-Res PNG Download Button per Drawing (as in Flat Slab module)
                            buf_draw_tab = io.BytesIO()
                            d["fig"].savefig(buf_draw_tab, format="png", bbox_inches="tight", dpi=300)
                            buf_draw_tab.seek(0)
                            prefix = get_safe_profile_filename_prefix()
                            st.download_button(
                                label=f"📥 Download Drawing {d['name']} (High-Res PNG)",
                                data=buf_draw_tab,
                                file_name=f"{prefix}ECP203_CAD_Drawing_{d['name']}.png",
                                mime="image/png",
                                use_container_width=True,
                                key=f"cs_btn_dl_tab_{i}_{d['name']}",
                            )
                else:
                    for i, d in enumerate(combined_all_drawings):
                        if d.get("type") == "column":
                            header_bg = "linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%)"
                            border_col = "#38bdf8"
                            icon_str = "🏛️"
                            tag_str = f"{d['b']:.0f} × {d['t']:.0f} cm &nbsp;|&nbsp; {d['n_bars']} Φ {d['phi_main']} mm"
                            title_str = f"المخطط الإنشائي وتفريد التسليح لنموذج عمود: <b style='color:#67e8f9; font-size:28px;'>{d['name']}</b>"
                        else:
                            header_bg = "linear-gradient(135deg, #064e3b 0%, #047857 100%)"
                            border_col = "#34d399"
                            icon_str = "🟦"
                            tag_str = f"{d['lx']:.1f} × {d['ly']:.1f} m &nbsp;|&nbsp; ts = {d['ts']:.0f} cm"
                            title_str = f"المخطط الإنشائي وتفريد التسليح لنموذج بلاطة مسطحة: <b style='color:#6ee7b7; font-size:28px;'>{d['name']}</b>"

                        st.markdown(
                            f"""
                            <div style="
                                background: {header_bg};
                                color: #ffffff !important;
                                padding: 16px 24px;
                                margin: 22px 0 14px 0;
                                border-radius: 10px;
                                font-size: 26px;
                                font-weight: 900;
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                box-shadow: 0 5px 18px rgba(15, 23, 42, 0.30);
                                border-right: 8px solid {border_col};
                            ">
                                <div style="display:flex; align-items:center; gap:12px;">
                                    <span style="font-size:28px;">{icon_str}</span>
                                    <span style="color:#ffffff !important;">{title_str}</span>
                                </div>
                                <span dir="ltr" style="background:rgba(255,255,255,0.20); color:#ffffff !important; padding:6px 18px; border-radius:16px; font-size:20px; font-weight:900; border:1.5px solid rgba(255,255,255,0.35);">
                                    {tag_str}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.pyplot(d["fig"], use_container_width=True)

                        # High-Res PNG Download Button per Drawing (as in Flat Slab module)
                        buf_draw_list = io.BytesIO()
                        d["fig"].savefig(buf_draw_list, format="png", bbox_inches="tight", dpi=300)
                        buf_draw_list.seek(0)
                        prefix = get_safe_profile_filename_prefix()
                        st.download_button(
                            label=f"📥 Download Drawing {d['name']} (High-Res PNG)",
                            data=buf_draw_list,
                            file_name=f"{prefix}ECP203_CAD_Drawing_{d['name']}.png",
                            mime="image/png",
                            use_container_width=True,
                            key=f"cs_btn_dl_list_{i}_{d['name']}",
                        )
            else:
                st.info("💡 انقر لتوسيع هذا القسم وتوليد المخططات الهندسية وتفريد التسليح لكافة نماذج الأعمدة والأسقف (Lazy Loading).")

        # ────────────────────────────────────────────────────────────────────
        # BOTTOM PANEL: SUMMARY METRICS & DETAILED QUANTITY TAKEOFF RESULTS
        # ────────────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 لوحة نتائج حصر الخرسانات والحديد والمقايسة المالية (Quantity Takeoff & BOQ Panel)")

        # Summary Metric Cards
        p_m1, p_m2, p_m3, p_m4, p_m5 = st.columns(5)
        p_m1.metric("إجمالي حجم الخرسانة المسلحة", f"{grand_vol_concrete_all:.2f} m³", f"أعمدة: {total_vol_all:.1f}m³ | بلاطات: {total_vol_slabs_all:.1f}m³")
        p_m2.metric("إجمالي وزن حديد التسليح", f"{grand_w_steel_ton_all:.3f} Ton", f"{grand_w_steel_kg_all:,.1f} kg")
        p_m3.metric("معدل استهلاك الحديد الكلي", f"{grand_overall_steel_rate:.1f} kg/m³")
        p_m4.metric("إجمالي التكلفة التقديرية", f"{cost_grand_total:,.0f} EGP", "شامل المواد والمصنعيات")
        p_m5.metric("متوسط تكلفة المتر المكعب", f"{cost_per_m3_all_inclusive:,.0f} EGP/m³", "تكلفة شاملة بالمتر المكعب")

        # ── 1. DETAILED QUANTITY TAKEOFF TABLE (الأعمدة + البلاطات المسطحة) ──
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: #ffffff !important; padding: 14px 22px; border-radius: 10px; font-size: 24px; font-weight: 800; margin: 20px 0 14px 0; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.22); border-left: 6px solid #60a5fa;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 26px;">📋</span>
                    <span style="color: #ffffff !important; font-weight: 800;">جدول تفصيلي بحصر الكميات والحديد لجميع عناصر المشروع ({len(col_results)} نماذج أعمدة + {len(slab_results)} نماذج بلاطات)</span>
                </div>
                <span style="background: rgba(255,255,255,0.22); color: #ffffff !important; padding: 5px 14px; border-radius: 20px; font-size: 15px; font-weight: 700; border: 1px solid rgba(255,255,255,0.35);">
                    إجمالي خرسانة: {grand_vol_concrete_all:.2f} m³
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        takeoff_rows_html = ""
        total_steel_linear_all = 0.0
        rebar_by_dia = {}

        # A. Columns Rows
        for m_idx, r in enumerate(col_results, 1):
            c_name = r["name"]
            c_b = r["b"]
            c_t = r["t"]
            c_nc = r["n_cols"]
            c_nb = r["n_bars"]
            c_phi = r["phi_main"]
            c_nr = r["n_rows"]
            c_tie = r["tie_type"].split(' ')[0]
            c_L_bar_m = r["L_bar_m"]
            c_L_bar_cm = r["L_bar_cm"]
            c_w_main_kg = r["w_main_total_kg"]
            c_w_main_ton = r["w_main_total_ton"]
            c_n_ties = r["n_ties_per_col"]
            c_L_tie_m = r["L_tie_m"]
            c_L_tie_cm = r["L_tie_cm"]
            c_w_st_kg = r["w_st_total_kg"]
            c_w_st_ton = r["w_st_total_ton"]
            c_vol_single = r["vol_col_single_m3"]
            c_vol_total = r["vol_col_total_m3"]

            c_main_lin = c_nc * c_nb * c_L_bar_m
            c_st_lin = c_nc * c_n_ties * c_L_tie_m
            total_steel_linear_all += (c_main_lin + c_st_lin)

            # Aggregate by diameter
            if c_phi not in rebar_by_dia:
                rebar_by_dia[c_phi] = {"phi": c_phi, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
            rebar_by_dia[c_phi]["total_len_m"] += c_main_lin
            rebar_by_dia[c_phi]["total_w_kg"] += c_w_main_kg
            rebar_by_dia[c_phi]["main_pieces"] += (c_nc * c_nb)
            rebar_by_dia[c_phi]["desc"].append(f"أعمدة {c_name} ({c_nc * c_nb} سيخ)")

            if phi_st not in rebar_by_dia:
                rebar_by_dia[phi_st] = {"phi": phi_st, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
            rebar_by_dia[phi_st]["total_len_m"] += c_st_lin
            rebar_by_dia[phi_st]["total_w_kg"] += c_w_st_kg
            rebar_by_dia[phi_st]["tie_pieces"] += (c_nc * c_n_ties)
            rebar_by_dia[phi_st]["desc"].append(f"كانات {c_name} ({c_nc * c_n_ties} كانة)")

            foot_tag = f" + رجل <span dir='ltr'>{r.get('L_foot_cm', 0):.0f}cm</span>" if has_footing else ""
            top_tag = f"جنش <span dir='ltr'>{((lap_factor_sel * c_phi) / 10.0):.0f}cm</span>" if is_top else f"وصلة <span dir='ltr'>{lap_factor_sel:.0f}Φ</span>"

            takeoff_rows_html += f"""
            <tr style="background:#f8fafc; font-size:24px; text-align:center;">
                <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#1e3a8a;">{m_idx}.1. خرسانة مسلحة ({c_name})</td>
                <td style="padding:14px 12px; border:1px solid #cbd5e1; font-weight:800; color:#1e3a8a; font-size:24px;"><span dir="ltr">{c_b:.0f} × {c_t:.0f} cm</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#1e3a8a;"><span dir="ltr">{c_nc}</span> عمود</td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#1e3a8a; background:#f1f5f9;"><span dir="ltr">{c_nc}</span> قطعة</td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#1e3a8a;"><span dir="ltr">H = {col_h_in/100:.2f} m</span></td>
                <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:800; color:#1e3a8a; background:#eff6ff; font-size:25px;"><span dir="ltr">{c_vol_total:.2f} m³</span></td>
                <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:20px; color:#475569;">حجم العمود = <span dir="ltr">{c_vol_single:.3f} m³</span> (صافي <span dir="ltr">H={col_h_in/100:.2f}m</span>)</td>
            </tr>
            <tr style="background:#ffffff; font-size:24px; text-align:center;">
                <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#b91c1c;">{m_idx}.2. تسليح رئيسي ({c_name})</td>
                <td style="padding:14px 12px; border:1px solid #cbd5e1; color:#b91c1c; font-weight:800; font-size:24px;"><span dir="ltr">{c_nb} Φ{c_phi} mm [{c_nr} Rows]</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#475569;"><span dir="ltr">{c_nc}</span> عمود</td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b91c1c; background:#fef2f2; font-size:25px;"><span dir="ltr">{c_nc * c_nb}</span> قطعة<br><span style="font-size:18px; font-weight:700; color:#991b1b;" dir="ltr">({c_nb} قطعة/عمود)</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#15803d; background:#f0fdf4; font-size:25px;"><span dir="ltr">{c_L_bar_m:.2f} m'</span></td>
                <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:800; color:#991b1b; background:#fef2f2; font-size:25px;"><span dir="ltr">{c_w_main_kg:.1f} kg</span><br><span style="font-size:21px; color:#b91c1c;" dir="ltr">({c_w_main_ton:.3f} Ton)</span></td>
                <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:20px; color:#475569;">طول القطع = <span dir="ltr">{c_L_bar_m:.2f}m</span> (ارتفاع <span dir="ltr">{col_h_in:.0f}</span> + سقف <span dir="ltr">{t_slab_in:.0f}</span> + {top_tag}{foot_tag})</td>
            </tr>
            <tr style="background:#f8fafc; font-size:24px; text-align:center;">
                <td style="padding:14px 16px; border:1px solid #cbd5e1; border-bottom:3px solid #334155 !important; font-weight:800; text-align:right; color:#15803d;">{m_idx}.3. حديد الكانات ({c_name})</td>
                <td style="padding:14px 12px; border:1px solid #cbd5e1; border-bottom:3px solid #334155 !important; color:#15803d; font-weight:800; font-size:24px;"><span dir="ltr">{c_tie} - Φ{phi_st} mm</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; border-bottom:3px solid #334155 !important; font-weight:800; color:#475569;"><span dir="ltr">{c_nc}</span> عمود</td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; border-bottom:3px solid #334155 !important; font-weight:900; color:#15803d; background:#f0fdf4; font-size:25px;"><span dir="ltr">{c_nc * c_n_ties}</span> قطعة<br><span style="font-size:18px; font-weight:700; color:#166534;" dir="ltr">({c_n_ties} كانة/عمود)</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; border-bottom:3px solid #334155 !important; font-weight:900; color:#15803d; background:#f0fdf4; font-size:25px;"><span dir="ltr">{c_L_tie_m:.2f} m'</span></td>
                <td style="padding:14px 14px; border:1px solid #cbd5e1; border-bottom:3px solid #334155 !important; font-weight:800; color:#15803d; background:#f0fdf4; font-size:25px;"><span dir="ltr">{c_w_st_kg:.1f} kg</span><br><span style="font-size:21px; color:#15803d;" dir="ltr">({c_w_st_ton:.3f} Ton)</span></td>
                <td style="padding:14px 16px; border:1px solid #cbd5e1; border-bottom:3px solid #334155 !important; font-size:20px; color:#475569;">طول الكانة = <span dir="ltr">{c_L_tie_m:.2f}m</span> (كثافة <span dir="ltr">{n_st_m} Φ{phi_st}/m'</span> | كانة <span dir="ltr">{c_b-2*cover_cm:.0f}×{c_t-2*cover_cm:.0f} cm</span>)</td>
            </tr>
            """

        # B. Flat Slabs Rows
        for s_idx, s in enumerate(slab_results, 1):
            s_name = s["name"]
            s_lx = s["lx"]
            s_ly = s["ly"]
            s_ts = s["ts"]
            s_n_rep = s["n_rep"]
            s_vol = s["vol_total_m3"]
            s_w_st_kg = s["w_steel_total_kg"]
            s_w_st_ton = s["w_steel_total_ton"]

            # Linear meters for slab
            s_lin_bx = s["n_runs_bx"] * s["L_cut_bx"] * s_n_rep
            s_lin_by = s["n_runs_by"] * s["L_cut_by"] * s_n_rep
            s_lin_tx = s["n_runs_tx"] * s["L_cut_tx"] * s_n_rep
            s_lin_ty = s["n_runs_ty"] * s["L_cut_ty"] * s_n_rep
            s_lin_chairs = s["n_chairs"] * s["L_chair_m"]
            total_steel_linear_all += (s_lin_bx + s_lin_by + s_lin_tx + s_lin_ty + s_lin_chairs)

            # Aggregate by diameter
            # Bottom X
            d_bx = s["phi_bx"]
            if d_bx not in rebar_by_dia:
                rebar_by_dia[d_bx] = {"phi": d_bx, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
            rebar_by_dia[d_bx]["total_len_m"] += s_lin_bx
            rebar_by_dia[d_bx]["total_w_kg"] += s["w_bx_kg"]
            rebar_by_dia[d_bx]["main_pieces"] += (s["n_runs_bx"] * s_n_rep)
            rebar_by_dia[d_bx]["desc"].append(f"بلاطة {s_name} سفلي X ({s['n_runs_bx']*s_n_rep} سيخ)")

            # Bottom Y
            d_by = s["phi_by"]
            if d_by not in rebar_by_dia:
                rebar_by_dia[d_by] = {"phi": d_by, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
            rebar_by_dia[d_by]["total_len_m"] += s_lin_by
            rebar_by_dia[d_by]["total_w_kg"] += s["w_by_kg"]
            rebar_by_dia[d_by]["main_pieces"] += (s["n_runs_by"] * s_n_rep)
            rebar_by_dia[d_by]["desc"].append(f"بلاطة {s_name} سفلي Y ({s['n_runs_by']*s_n_rep} سيخ)")

            # Top X
            d_tx = s["phi_tx"]
            if d_tx not in rebar_by_dia:
                rebar_by_dia[d_tx] = {"phi": d_tx, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
            rebar_by_dia[d_tx]["total_len_m"] += s_lin_tx
            rebar_by_dia[d_tx]["total_w_kg"] += s["w_tx_kg"]
            rebar_by_dia[d_tx]["main_pieces"] += (s["n_runs_tx"] * s_n_rep)
            rebar_by_dia[d_tx]["desc"].append(f"بلاطة {s_name} علوي X ({s['n_runs_tx']*s_n_rep} سيخ)")

            # Top Y
            d_ty = s["phi_ty"]
            if d_ty not in rebar_by_dia:
                rebar_by_dia[d_ty] = {"phi": d_ty, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
            rebar_by_dia[d_ty]["total_len_m"] += s_lin_ty
            rebar_by_dia[d_ty]["total_w_kg"] += s["w_ty_kg"]
            rebar_by_dia[d_ty]["main_pieces"] += (s["n_runs_ty"] * s_n_rep)
            rebar_by_dia[d_ty]["desc"].append(f"بلاطة {s_name} علوي Y ({s['n_runs_ty']*s_n_rep} سيخ)")

            # Multi-model Additional Top Reinforcement
            if s.get("top_add_models_res"):
                for tm in s.get("top_add_models_res", []):
                    tm_phi = tm["phi"]
                    tm_name = tm["name"]
                    tot_pcs_x = tm["n_runs_x"] * tm["n_zones"] * s_n_rep
                    if tot_pcs_x > 0 and tm["lx"] > 0:
                        total_steel_linear_all += tm["lin_x"]
                        if tm_phi not in rebar_by_dia:
                            rebar_by_dia[tm_phi] = {"phi": tm_phi, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
                        rebar_by_dia[tm_phi]["total_len_m"] += tm["lin_x"]
                        rebar_by_dia[tm_phi]["total_w_kg"] += tm["w_x_kg"]
                        rebar_by_dia[tm_phi]["main_pieces"] += tot_pcs_x
                        rebar_by_dia[tm_phi]["desc"].append(f"إضافي علوي [{tm_name}] X بلاطة {s_name} ({tot_pcs_x} سيخ Φ{tm_phi} بمعدل {tm['nx']:.0f}/م')")

                    tot_pcs_y = tm["n_runs_y"] * tm["n_zones"] * s_n_rep
                    if tot_pcs_y > 0 and tm["ly"] > 0:
                        total_steel_linear_all += tm["lin_y"]
                        if tm_phi not in rebar_by_dia:
                            rebar_by_dia[tm_phi] = {"phi": tm_phi, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
                        rebar_by_dia[tm_phi]["total_len_m"] += tm["lin_y"]
                        rebar_by_dia[tm_phi]["total_w_kg"] += tm["w_y_kg"]
                        rebar_by_dia[tm_phi]["main_pieces"] += tot_pcs_y
                        rebar_by_dia[tm_phi]["desc"].append(f"إضافي علوي [{tm_name}] Y بلاطة {s_name} ({tot_pcs_y} سيخ Φ{tm_phi} بمعدل {tm['ny']:.0f}/م')")
            elif s.get("n_top_add_x", 0) > 0 or s.get("n_top_add_y", 0) > 0:
                d_tax = int(s.get("phi_top_add", 12))
                lin_tax = s.get("lin_top_add_x", 0.0) + s.get("lin_top_add_y", 0.0)
                w_tax = s.get("w_top_add_kg", 0.0)
                total_steel_linear_all += lin_tax
                if d_tax not in rebar_by_dia:
                    rebar_by_dia[d_tax] = {"phi": d_tax, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
                rebar_by_dia[d_tax]["total_len_m"] += lin_tax
                rebar_by_dia[d_tax]["total_w_kg"] += w_tax
                tot_p = (s.get("n_runs_x", 0) + s.get("n_runs_y", 0)) * s_n_rep
                rebar_by_dia[d_tax]["main_pieces"] += tot_p
                rebar_by_dia[d_tax]["desc"].append(f"إضافي علوي بلاطة {s_name} ({tot_p} سيخ Φ{d_tax})")

            # Multi-model Additional Bottom Reinforcement
            if s.get("btm_add_models_res"):
                for bm in s.get("btm_add_models_res", []):
                    bm_phi = bm["phi"]
                    bm_name = bm["name"]
                    tot_pcs_x = bm["n_runs_x"] * bm["n_zones"] * s_n_rep
                    if tot_pcs_x > 0 and bm["lx"] > 0:
                        total_steel_linear_all += bm["lin_x"]
                        if bm_phi not in rebar_by_dia:
                            rebar_by_dia[bm_phi] = {"phi": bm_phi, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
                        rebar_by_dia[bm_phi]["total_len_m"] += bm["lin_x"]
                        rebar_by_dia[bm_phi]["total_w_kg"] += bm["w_x_kg"]
                        rebar_by_dia[bm_phi]["main_pieces"] += tot_pcs_x
                        rebar_by_dia[bm_phi]["desc"].append(f"إضافي سفلي [{bm_name}] X بلاطة {s_name} ({tot_pcs_x} سيخ Φ{bm_phi} بمعدل {bm['nx']:.0f}/م')")

                    tot_pcs_y = bm["n_runs_y"] * bm["n_zones"] * s_n_rep
                    if tot_pcs_y > 0 and bm["ly"] > 0:
                        total_steel_linear_all += bm["lin_y"]
                        if bm_phi not in rebar_by_dia:
                            rebar_by_dia[bm_phi] = {"phi": bm_phi, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
                        rebar_by_dia[bm_phi]["total_len_m"] += bm["lin_y"]
                        rebar_by_dia[bm_phi]["total_w_kg"] += bm["w_y_kg"]
                        rebar_by_dia[bm_phi]["main_pieces"] += tot_pcs_y
                        rebar_by_dia[bm_phi]["desc"].append(f"إضافي سفلي [{bm_name}] Y بلاطة {s_name} ({tot_pcs_y} سيخ Φ{bm_phi} بمعدل {bm['ny']:.0f}/م')")
            elif s.get("n_btm_add_x", 0) > 0 or s.get("n_btm_add_y", 0) > 0:
                d_bax = int(s.get("phi_btm_add", 12))
                lin_bax = s.get("lin_btm_add_x", 0.0) + s.get("lin_btm_add_y", 0.0)
                w_bax = s.get("w_btm_add_kg", 0.0)
                total_steel_linear_all += lin_bax
                if d_bax not in rebar_by_dia:
                    rebar_by_dia[d_bax] = {"phi": d_bax, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
                rebar_by_dia[d_bax]["total_len_m"] += lin_bax
                rebar_by_dia[d_bax]["total_w_kg"] += w_bax
                tot_p = (s.get("n_runs_x", 0) + s.get("n_runs_y", 0)) * s_n_rep
                rebar_by_dia[d_bax]["main_pieces"] += tot_p
                rebar_by_dia[d_bax]["desc"].append(f"إضافي سفلي بلاطة {s_name} ({tot_p} سيخ Φ{d_bax})")

            # Chairs (Phi 10)
            if 10 not in rebar_by_dia:
                rebar_by_dia[10] = {"phi": 10, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
            rebar_by_dia[10]["total_len_m"] += s_lin_chairs
            rebar_by_dia[10]["total_w_kg"] += s["w_chairs_kg"]
            rebar_by_dia[10]["tie_pieces"] += s["n_chairs"]
            rebar_by_dia[10]["desc"].append(f"كراسي بلاطة {s_name} ({s['n_chairs']} كرسي)")

            takeoff_rows_html += f"""
            <tr style="background:#f0fdf4; font-size:24px; text-align:center;">
                <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#065f46;">FS.{s_idx}.1. خرسانة مسلحة ({s_name})</td>
                <td style="padding:14px 12px; border:1px solid #cbd5e1; font-weight:800; color:#065f46; font-size:24px;"><span dir="ltr">{s_lx:.2f} × {s_ly:.2f} m (ts={s_ts:.0f}cm)</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#065f46;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#065f46; background:#dcfce7;"><span dir="ltr">{s_n_rep}</span> مسطح</td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#065f46;"><span dir="ltr">ts = {s_ts:.0f} cm</span></td>
                <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:800; color:#065f46; background:#dcfce7; font-size:25px;"><span dir="ltr">{s_vol:.2f} m³</span></td>
                <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:20px; color:#475569;">مسطح البلاطة = <span dir="ltr">{s['area_total_m2']:.1f} m²</span> (إجمالي <span dir="ltr">{s_n_rep}</span> تكرار)</td>
            </tr>
            <tr style="background:#ffffff; font-size:24px; text-align:center;">
                <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#1d4ed8;">FS.{s_idx}.2. شبكة سفلية ({s_name})</td>
                <td style="padding:14px 12px; border:1px solid #cbd5e1; color:#1d4ed8; font-weight:800; font-size:24px;"><span dir="ltr">{s['nb_bx']}Φ{s['phi_bx']} (X) + {s['nb_by']}Φ{s['phi_by']} (Y)</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#475569;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#1d4ed8; background:#eff6ff; font-size:25px;"><span dir="ltr">{(s['n_runs_bx'] + s['n_runs_by'])*s_n_rep}</span> قطعة<br><span style="font-size:19px; font-weight:700; color:#1e40af;" dir="ltr">(X={s['n_runs_bx']*s_n_rep}, Y={s['n_runs_by']*s_n_rep})</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#15803d; background:#f0fdf4; font-size:25px;"><span dir="ltr">X={s['L_cut_bx']:.2f}m, Y={s['L_cut_by']:.2f}m</span></td>
                <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:800; color:#1d4ed8; background:#eff6ff; font-size:25px;"><span dir="ltr">{s['w_bx_kg']+s['w_by_kg']:.1f} kg</span><br><span style="font-size:21px;" dir="ltr">({(s['w_bx_kg']+s['w_by_kg'])/1000:.3f} Ton)</span></td>
                <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:20px; color:#475569;">سفلي X: <span dir="ltr">{s['w_bx_kg']:.1f}kg</span> + سفلي Y: <span dir="ltr">{s['w_by_kg']:.1f}kg</span></td>
            </tr>
            <tr style="background:#f0fdf4; font-size:24px; text-align:center;">
                <td style="padding:14px 16px; border:1px solid #cbd5e1; border-bottom:3px solid #065f46 !important; font-weight:800; text-align:right; color:#15803d;">FS.{s_idx}.3. شبكة علوية وكراسي ({s_name})</td>
                <td style="padding:14px 12px; border:1px solid #cbd5e1; border-bottom:3px solid #065f46 !important; color:#15803d; font-weight:800; font-size:24px;"><span dir="ltr">{s['nb_tx']}Φ{s['phi_tx']} (X) + {s['nb_ty']}Φ{s['phi_ty']} (Y)</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; border-bottom:3px solid #065f46 !important; font-weight:800; color:#475569;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; border-bottom:3px solid #065f46 !important; font-weight:900; color:#15803d; background:#dcfce7; font-size:25px;"><span dir="ltr">{(s['n_runs_tx'] + s['n_runs_ty'])*s_n_rep + s['n_chairs']}</span> قطعة<br><span style="font-size:19px; font-weight:700; color:#166534;" dir="ltr">(X={s['n_runs_tx']*s_n_rep}, Y={s['n_runs_ty']*s_n_rep} + {s['n_chairs']} كرسي)</span></td>
                <td style="padding:14px 10px; border:1px solid #cbd5e1; border-bottom:3px solid #065f46 !important; font-weight:900; color:#15803d; background:#dcfce7; font-size:25px;"><span dir="ltr">X={s['L_cut_tx']:.2f}m, Y={s['L_cut_ty']:.2f}m</span></td>
                <td style="padding:14px 14px; border:1px solid #cbd5e1; border-bottom:3px solid #065f46 !important; font-weight:800; color:#15803d; background:#dcfce7; font-size:25px;"><span dir="ltr">{s['w_tx_kg']+s['w_ty_kg']+s['w_chairs_kg']:.1f} kg</span><br><span style="font-size:21px;" dir="ltr">({(s['w_tx_kg']+s['w_ty_kg']+s['w_chairs_kg'])/1000:.3f} Ton)</span></td>
                <td style="padding:14px 16px; border:1px solid #cbd5e1; border-bottom:3px solid #065f46 !important; font-size:20px; color:#475569;">علوي: <span dir="ltr">{s['w_tx_kg']+s['w_ty_kg']:.1f}kg</span> + كراسي Φ10: <span dir="ltr">{s['w_chairs_kg']:.1f}kg</span> ({s['n_chairs']} كرسي)</td>
            </tr>
            """

            if s.get("top_add_models_res"):
                for m_i, tm in enumerate(s.get("top_add_models_res", []), 1):
                    if tm["w_total_kg"] > 0:
                        tot_pcs_x = tm["n_runs_x"] * tm["n_zones"] * s_n_rep
                        tot_pcs_y = tm["n_runs_y"] * tm["n_zones"] * s_n_rep
                        tot_pcs = tot_pcs_x + tot_pcs_y
                        w_ton = tm["w_total_kg"] / 1000.0
                        takeoff_rows_html += f"""
                        <tr style="background:#fffbeb; font-size:24px; text-align:center;">
                            <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#b45309;">FS.{s_idx}.4.{m_i}. إضافي علوي [{tm['name']}] ({s_name})</td>
                            <td style="padding:14px 12px; border:1px solid #cbd5e1; color:#b45309; font-weight:800; font-size:24px;"><span dir="ltr">X={tm['nx']:.0f}Φ{tm['phi']}/م' + Y={tm['ny']:.0f}Φ{tm['phi']}/م' ({tm['n_zones']} مناطق)</span></td>
                            <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#475569;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                            <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">{tot_pcs}</span> قطعة<br><span style="font-size:19px; font-weight:700; color:#92400e;" dir="ltr">(X={tot_pcs_x}, Y={tot_pcs_y})</span></td>
                            <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">Lx={tm['lx']:.2f}m, Ly={tm['ly']:.2f}m</span></td>
                            <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:800; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">{tm['w_total_kg']:.1f} kg</span><br><span style="font-size:21px;" dir="ltr">({w_ton:.3f} Ton)</span></td>
                            <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:20px; color:#475569;">علوي X: <span dir="ltr">{tot_pcs_x} قطعة ({tm['w_x_kg']:.1f}kg)</span> + علوي Y: <span dir="ltr">{tot_pcs_y} قطعة ({tm['w_y_kg']:.1f}kg)</span></td>
                        </tr>
                        """
            elif s.get("w_top_add_kg", 0.0) > 0:
                n_tax_x = s.get('n_runs_x', 0) * s_n_rep
                n_tax_y = s.get('n_runs_y', 0) * s_n_rep
                n_tax_tot = n_tax_x + n_tax_y
                w_tax_tot = s.get("w_top_add_kg", 0.0)
                takeoff_rows_html += f"""
                <tr style="background:#fffbeb; font-size:24px; text-align:center;">
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#b45309;">FS.{s_idx}.4. حديد إضافي علوي ({s_name})</td>
                    <td style="padding:14px 12px; border:1px solid #cbd5e1; color:#b45309; font-weight:800; font-size:24px;"><span dir="ltr">X={s.get('nx',0):.0f}Φ{s.get('phi_top_add',12)}/م' + Y={s.get('ny',0):.0f}Φ{s.get('phi_top_add',12)}/م'</span></td>
                    <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#475569;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                    <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">{n_tax_tot}</span> قطعة<br><span style="font-size:19px; font-weight:700; color:#92400e;" dir="ltr">(X={n_tax_x}, Y={n_tax_y})</span></td>
                    <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">Lx={s.get('add_top_lx',0):.2f}m, Ly={s.get('add_top_ly',0):.2f}m</span></td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:800; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">{w_tax_tot:.1f} kg</span><br><span style="font-size:21px;" dir="ltr">({w_tax_tot/1000:.3f} Ton)</span></td>
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:20px; color:#475569;">إضافي علوي X: <span dir="ltr">{s.get('w_top_add_x_kg',0):.1f}kg</span> + إضافي علوي Y: <span dir="ltr">{s.get('w_top_add_y_kg',0):.1f}kg</span></td>
                </tr>
                """

            if s.get("btm_add_models_res"):
                for m_i, bm in enumerate(s.get("btm_add_models_res", []), 1):
                    if bm["w_total_kg"] > 0:
                        tot_pcs_x = bm["n_runs_x"] * bm["n_zones"] * s_n_rep
                        tot_pcs_y = bm["n_runs_y"] * bm["n_zones"] * s_n_rep
                        tot_pcs = tot_pcs_x + tot_pcs_y
                        w_ton = bm["w_total_kg"] / 1000.0
                        takeoff_rows_html += f"""
                        <tr style="background:#fffbeb; font-size:24px; text-align:center;">
                            <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#b45309;">FS.{s_idx}.5.{m_i}. إضافي سفلي [{bm['name']}] ({s_name})</td>
                            <td style="padding:14px 12px; border:1px solid #cbd5e1; color:#b45309; font-weight:800; font-size:24px;"><span dir="ltr">X={bm['nx']:.0f}Φ{bm['phi']}/م' + Y={bm['ny']:.0f}Φ{bm['phi']}/م' ({bm['n_zones']} مناطق)</span></td>
                            <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#475569;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                            <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">{tot_pcs}</span> قطعة<br><span style="font-size:19px; font-weight:700; color:#92400e;" dir="ltr">(X={tot_pcs_x}, Y={tot_pcs_y})</span></td>
                            <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">Lx={bm['lx']:.2f}m, Ly={bm['ly']:.2f}m</span></td>
                            <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:800; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">{bm['w_total_kg']:.1f} kg</span><br><span style="font-size:21px;" dir="ltr">({w_ton:.3f} Ton)</span></td>
                            <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:20px; color:#475569;">سفلي X: <span dir="ltr">{tot_pcs_x} قطعة ({bm['w_x_kg']:.1f}kg)</span> + سفلي Y: <span dir="ltr">{tot_pcs_y} قطعة ({bm['w_y_kg']:.1f}kg)</span></td>
                        </tr>
                        """
            elif s.get("w_btm_add_kg", 0.0) > 0:
                n_bax_x = s.get('n_runs_x', 0) * s_n_rep
                n_bax_y = s.get('n_runs_y', 0) * s_n_rep
                n_bax_tot = n_bax_x + n_bax_y
                w_bax_tot = s.get("w_btm_add_kg", 0.0)
                takeoff_rows_html += f"""
                <tr style="background:#fffbeb; font-size:24px; text-align:center;">
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#b45309;">FS.{s_idx}.5. حديد إضافي سفلي ({s_name})</td>
                    <td style="padding:14px 12px; border:1px solid #cbd5e1; color:#b45309; font-weight:800; font-size:24px;"><span dir="ltr">X={s.get('nx',0):.0f}Φ{s.get('phi_btm_add',12)}/م' + Y={s.get('ny',0):.0f}Φ{s.get('phi_btm_add',12)}/م'</span></td>
                    <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:800; color:#475569;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                    <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">{n_bax_tot}</span> قطعة<br><span style="font-size:19px; font-weight:700; color:#92400e;" dir="ltr">(X={n_bax_x}, Y={n_bax_y})</span></td>
                    <td style="padding:14px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">Lx={s.get('add_btm_lx',0):.2f}m, Ly={s.get('add_btm_ly',0):.2f}m</span></td>
                    <td style="padding:14px 14px; border:1px solid #cbd5e1; font-weight:800; color:#b45309; background:#fef3c7; font-size:25px;"><span dir="ltr">{w_bax_tot:.1f} kg</span><br><span style="font-size:21px;" dir="ltr">({w_bax_tot/1000:.3f} Ton)</span></td>
                    <td style="padding:14px 16px; border:1px solid #cbd5e1; font-size:20px; color:#475569;">إضافي سفلي X: <span dir="ltr">{s.get('w_btm_add_x_kg',0):.1f}kg</span> + إضافي سفلي Y: <span dir="ltr">{s.get('w_btm_add_y_kg',0):.1f}kg</span></td>
                </tr>
                """

        # Generate rows for each diameter breakdown
        dia_rows_html = ""
        total_pieces_all = 0
        for phi_key in sorted(rebar_by_dia.keys()):
            d_info = rebar_by_dia[phi_key]
            d_phi = d_info["phi"]
            d_len_m = d_info["total_len_m"]
            d_w_kg = d_info["total_w_kg"]
            d_w_ton = d_w_kg / 1000.0
            d_w_per_m = (d_phi**2) / 162.0
            
            tot_p = d_info["main_pieces"] + d_info["tie_pieces"]
            total_pieces_all += tot_p
            
            role_label = "رئيسي / شبكات + كانات/كراسي" if (d_info["main_pieces"] > 0 and d_info["tie_pieces"] > 0) else ("تسليح رئيسي / شبكات" if d_info["main_pieces"] > 0 else "كانات وكراسي")
            pieces_str = f"{tot_p} قطعة"
            desc_str = " | ".join(d_info["desc"][:4]) + ("..." if len(d_info["desc"]) > 4 else "")

            dia_rows_html += f"""
            <tr style="background:#fffbeb; font-size:24px; text-align:center;">
                <td style="padding:13px 16px; border:1px solid #cbd5e1; font-weight:800; text-align:right; color:#b45309;">🔹 حديد تسليح <span dir="ltr">Φ{d_phi} mm</span> ({role_label})</td>
                <td style="padding:13px 12px; border:1px solid #cbd5e1; font-weight:800; color:#b45309; font-size:22px;"><span dir="ltr">{d_w_per_m:.3f} kg/m'</span> (وزن المتر)</td>
                <td style="padding:13px 10px; border:1px solid #cbd5e1; color:#b45309;">-</td>
                <td style="padding:13px 10px; border:1px solid #cbd5e1; font-weight:900; color:#b45309; font-size:24px;"><span dir="ltr">{pieces_str}</span></td>
                <td style="padding:13px 10px; border:1px solid #cbd5e1; font-weight:800; color:#b45309;"><span dir="ltr">{d_len_m:.1f} m'</span> (طول إجمالي)</td>
                <td style="padding:13px 14px; border:1px solid #cbd5e1; font-weight:800; color:#92400e; background:#fef3c7; font-size:25px;"><span dir="ltr">{d_w_kg:.1f} kg</span><br><span style="font-size:20px; color:#b45309;" dir="ltr">({d_w_ton:.3f} Ton)</span></td>
                <td style="padding:13px 16px; border:1px solid #cbd5e1; font-size:19px; color:#475569;">{desc_str}</td>
            </tr>
            """

        takeoff_html = f"""
<div style="overflow-x:auto; border:2px solid rgba(56, 189, 248, 0.45); border-radius:12px; box-shadow:0 6px 25px rgba(0,0,0,0.50); margin:12px 0 24px 0;">
<table style="width:100%; border-collapse:collapse; background:#0b1329; font-family:'Segoe UI', Tahoma, sans-serif;">
<thead>
<tr style="background:linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom:2.5px solid #38bdf8; text-align:center;">
<th style="padding:15px 16px; color:#38bdf8; font-weight:900; font-size:18px; text-align:right;">البند / Component</th>
<th style="padding:15px 12px; color:#38bdf8; font-weight:900; font-size:18px;">القطاع / المواصفة</th>
<th style="padding:15px 10px; color:#38bdf8; font-weight:900; font-size:18px;">عدد العناصر</th>
<th style="padding:15px 10px; color:#38bdf8; font-weight:900; font-size:18px;">عدد القطع (Pieces)</th>
<th style="padding:15px 10px; color:#38bdf8; font-weight:900; font-size:18px;">طول القطع (Cut Length)</th>
<th style="padding:15px 14px; color:#fbbf24; font-weight:900; font-size:18px;">الوزن / الحجم الإجمالي</th>
<th style="padding:15px 16px; color:#cbd5e1; font-weight:900; font-size:18px;">ملاحظات الحصر والتفريد</th>
</tr>
</thead>
<tbody>
{takeoff_rows_html}
<tr style="background:linear-gradient(90deg, rgba(30, 58, 138, 0.45) 0%, rgba(15, 23, 42, 0.75) 100%); border-top:2.5px solid #38bdf8; border-bottom:2.5px solid #38bdf8; font-size:18px; font-weight:800; text-align:center;">
<td style="padding:15px 16px; color:#38bdf8; text-align:right; font-weight:900;">🔷 إجمالي الخرسانة المسلحة الكلية (أعمدة + بلاطات)</td>
<td style="padding:15px 12px; color:#ffffff;">كافة قطاعات الأعمدة والأسقف</td>
<td style="padding:15px 10px; color:#38bdf8; font-weight:800;"><span dir="ltr">{total_cols_all} عمود + {total_slabs_count} بلاطة</span></td>
<td style="padding:15px 10px; color:#cbd5e1;">-</td>
<td style="padding:15px 10px; color:#cbd5e1;">-</td>
<td style="padding:15px 14px; color:#38bdf8; font-size:20px; font-weight:900;"><span dir="ltr">{grand_vol_concrete_all:.2f} m³</span></td>
<td style="padding:15px 16px; color:#cbd5e1; font-size:16px;">أعمدة: <span dir="ltr">{total_vol_all:.2f} m³</span> | بلاطات: <span dir="ltr">{total_vol_slabs_all:.2f} m³</span></td>
</tr>
{dia_rows_html}
<tr style="background:linear-gradient(90deg, rgba(161, 98, 7, 0.35) 0%, rgba(15, 23, 42, 0.85) 100%); border-top:2.5px solid #ca8a04; border-bottom:2.5px solid #ca8a04; font-size:18px; font-weight:900; text-align:center;">
<td style="padding:16px 16px; color:#fbbf24; text-align:right; font-weight:900;">✅ الإجمالي العام لحديد التسليح بالمشروع (أعمدة + بلاطات)</td>
<td style="padding:16px 12px; color:#ffffff;">رئيسي + كانات + شبكات سفلية وعلوية</td>
<td style="padding:16px 10px; color:#fbbf24; font-weight:800;">كافة العناصر</td>
<td style="padding:16px 10px; color:#fbbf24; font-weight:900; font-size:19px;"><span dir="ltr">{total_pieces_all}</span> قطعة</td>
<td style="padding:16px 10px; color:#38bdf8; font-weight:800;"><span dir="ltr">{total_steel_linear_all:.1f} m'</span></td>
<td style="padding:16px 14px; color:#fbbf24; font-size:20px; font-weight:900;"><span dir="ltr">{grand_w_steel_kg_all:,.1f} kg</span><br><span style="font-size:17px; color:#fde047;" dir="ltr">({grand_w_steel_ton_all:.3f} Ton)</span></td>
<td style="padding:16px 16px; color:#38bdf8; font-size:17px; font-weight:800;">معدل الحديد الكلي = <span dir="ltr">{grand_overall_steel_rate:.1f} kg/m³</span></td>
</tr>
</tbody>
</table>
</div>
"""
        clean_takeoff_html = "\n".join(line.strip() for line in takeoff_html.splitlines() if line.strip())
        if hasattr(st, "html"):
            st.html(clean_takeoff_html)
        else:
            st.markdown(clean_takeoff_html, unsafe_allow_html=True)

        # ── 2. COMPREHENSIVE BILL OF QUANTITIES & MATERIAL PRICES TABLE ──
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #78350f 0%, #1e1b4b 100%); color: #ffffff !important; padding: 14px 22px; border-radius: 12px; font-size: 22px; font-weight: 800; margin: 26px 0 14px 0; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 6px 25px rgba(217, 119, 6, 0.25); border: 2px solid rgba(245, 158, 11, 0.45); border-left: 6px solid #fbbf24;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 26px;">💰</span>
                    <span style="color: #ffffff !important; font-weight: 800;">جدول مقايسة الأسعار وحصر تكاليف المواد والمصنعيات (Bill of Quantities & Pricing Table)</span>
                </div>
                <span style="background: rgba(251, 191, 36, 0.20); color: #fbbf24 !important; padding: 6px 16px; border-radius: 20px; font-size: 16px; font-weight: 800; border: 1.5px solid #fbbf24;">
                    إجمالي التكلفة: {cost_grand_total:,.2f} EGP
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        pricing_html = f"""
<div style="overflow-x:auto; border:2px solid rgba(245, 158, 11, 0.45); border-radius:12px; box-shadow:0 6px 25px rgba(0,0,0,0.50); margin:12px 0 24px 0;">
<table style="width:100%; border-collapse:collapse; background:#0b1329; font-family:'Segoe UI', Tahoma, sans-serif;">
<thead>
<tr style="background:linear-gradient(135deg, #451a03 0%, #0f172a 100%); border-bottom:2.5px solid #f59e0b; text-align:center;">
<th style="padding:15px 12px; color:#fbbf24; font-weight:900; font-size:18px; width:50px;">م</th>
<th style="padding:15px 16px; color:#38bdf8; font-weight:900; font-size:18px; text-align:right;">البند بمواصفاته الفنية</th>
<th style="padding:15px 12px; color:#38bdf8; font-weight:900; font-size:18px;">الوحدة</th>
<th style="padding:15px 14px; color:#38bdf8; font-weight:900; font-size:18px;">الكمية المحصورة</th>
<th style="padding:15px 14px; color:#fbbf24; font-weight:900; font-size:18px;">سعر البند (ج.م)</th>
<th style="padding:15px 16px; color:#fbbf24; font-weight:900; font-size:18px;">إجمالي السعر (ج.م)</th>
<th style="padding:15px 16px; color:#cbd5e1; font-weight:900; font-size:18px;">ملاحظات وتفاصيل الحساب</th>
</tr>
</thead>
<tbody>
<tr style="background:rgba(15, 23, 42, 0.75); border-bottom:1.5px solid rgba(148, 163, 184, 0.25); font-size:17px; text-align:center;">
<td style="padding:14px 10px; font-weight:800; color:#fbbf24;">1</td>
<td style="padding:14px 16px; font-weight:800; text-align:right; color:#ffffff;">خرسانة مسلحة للأعمدة الخرسانية (شاملة المواد والمصنعيات)</td>
<td style="padding:14px 12px; font-weight:700; color:#a5f3fc;">متر مكعب (m³)</td>
<td style="padding:14px 12px; font-weight:900; color:#38bdf8;"><span dir="ltr">{total_vol_all:.2f} m³</span></td>
<td style="padding:14px 12px; font-weight:900; color:#fbbf24;"><span dir="ltr">{rate_cols_per_m3:,.2f}</span></td>
<td style="padding:14px 16px; font-weight:900; color:#fbbf24; font-size:19px;"><span dir="ltr">{cost_cols_total:,.2f} ج.م</span></td>
<td style="padding:14px 16px; font-size:15px; color:#cbd5e1;">حديد: <span dir="ltr">{cost_steel_cols_m3:,.0f}</span> + أسمنت: <span dir="ltr">{cost_cement_cols_m3:,.0f}</span> + سن: <span dir="ltr">{cost_gravel_cols_m3:,.0f}</span> + رمل: <span dir="ltr">{cost_sand_cols_m3:,.0f}</span> + مصنعية: <span dir="ltr">{price_labor_in:,.0f}</span> ج.م/م³</td>
</tr>
<tr style="background:rgba(30, 41, 59, 0.75); border-bottom:1.5px solid rgba(148, 163, 184, 0.25); font-size:17px; text-align:center;">
<td style="padding:14px 10px; font-weight:800; color:#fbbf24;">2</td>
<td style="padding:14px 16px; font-weight:800; text-align:right; color:#ffffff;">خرسانة مسلحة للبلاطات المسطحة Flat Slabs (شاملة المواد والمصنعيات)</td>
<td style="padding:14px 12px; font-weight:700; color:#a5f3fc;">متر مكعب (m³)</td>
<td style="padding:14px 12px; font-weight:900; color:#38bdf8;"><span dir="ltr">{total_vol_slabs_all:.2f} m³</span></td>
<td style="padding:14px 12px; font-weight:900; color:#fbbf24;"><span dir="ltr">{rate_slabs_per_m3:,.2f}</span></td>
<td style="padding:14px 16px; font-weight:900; color:#fbbf24; font-size:19px;"><span dir="ltr">{cost_slabs_total:,.2f} ج.م</span></td>
<td style="padding:14px 16px; font-size:15px; color:#cbd5e1;">حديد: <span dir="ltr">{cost_steel_slabs_m3:,.0f}</span> + أسمنت: <span dir="ltr">{cost_cement_slabs_m3:,.0f}</span> + سن: <span dir="ltr">{cost_gravel_slabs_m3:,.0f}</span> + رمل: <span dir="ltr">{cost_sand_slabs_m3:,.0f}</span> + مصنعية: <span dir="ltr">{price_labor_in:,.0f}</span> ج.م/م³</td>
</tr>
<tr style="background:rgba(15, 23, 42, 0.75); border-bottom:1.5px solid rgba(148, 163, 184, 0.25); font-size:17px; text-align:center;">
<td style="padding:14px 10px; font-weight:800; color:#fbbf24;">3</td>
<td style="padding:14px 16px; font-weight:800; text-align:right; color:#ffffff;">إجمالي توريد حديد التسليح للمشروع (أعمدة + بلاطات)</td>
<td style="padding:14px 12px; color:#a5f3fc; font-weight:700;">طن (Ton)</td>
<td style="padding:14px 12px; color:#38bdf8; font-weight:900;"><span dir="ltr">{grand_w_steel_ton_all:.3f} Ton</span></td>
<td style="padding:14px 12px; font-weight:900; color:#fbbf24;"><span dir="ltr">{price_steel_in:,.2f}</span></td>
<td style="padding:14px 16px; font-weight:900; color:#fbbf24; font-size:19px;"><span dir="ltr">{cost_steel_total:,.2f} ج.م</span></td>
<td style="padding:14px 16px; font-size:15px; color:#cbd5e1;">إجمالي {grand_w_steel_kg_all:,.1f} kg (أعمدة <span dir="ltr">{total_w_steel_ton_all:.3f}T</span> + بلاطات <span dir="ltr">{total_w_slabs_steel_ton:.3f}T</span>)</td>
</tr>
<tr style="background:rgba(30, 41, 59, 0.75); border-bottom:1.5px solid rgba(148, 163, 184, 0.25); font-size:17px; text-align:center;">
<td style="padding:14px 10px; font-weight:800; color:#fbbf24;">4</td>
<td style="padding:14px 16px; font-weight:800; text-align:right; color:#ffffff;">إجمالي توريد الأسمنت البورتلاندي العادي للمشروع</td>
<td style="padding:14px 12px; font-weight:700; color:#a5f3fc;">طن (Ton)</td>
<td style="padding:14px 12px; font-weight:900; color:#38bdf8;"><span dir="ltr">{grand_cement_tons:.2f} Ton</span></td>
<td style="padding:14px 12px; font-weight:900; color:#fbbf24;"><span dir="ltr">{price_cement_in:,.2f}</span></td>
<td style="padding:14px 16px; font-weight:900; color:#fbbf24; font-size:19px;"><span dir="ltr">{cost_cement_total:,.2f} ج.م</span></td>
<td style="padding:14px 16px; font-size:15px; color:#cbd5e1;">إجمالي <span dir="ltr">{grand_cement_bags}</span> شكارة 50kg (أعمدة <span dir="ltr">{cement_cols_tons:.2f}T</span> + بلاطات <span dir="ltr">{cement_slabs_tons:.2f}T</span>)</td>
</tr>
<tr style="background:rgba(15, 23, 42, 0.75); border-bottom:1.5px solid rgba(148, 163, 184, 0.25); font-size:17px; text-align:center;">
<td style="padding:14px 10px; font-weight:800; color:#fbbf24;">5</td>
<td style="padding:14px 16px; font-weight:800; text-align:right; color:#ffffff;">إجمالي توريد السن / الزلط المتدرج النظيف للخرسانة</td>
<td style="padding:14px 12px; font-weight:700; color:#a5f3fc;">متر مكعب (m³)</td>
<td style="padding:14px 12px; font-weight:900; color:#38bdf8;"><span dir="ltr">{grand_gravel_m3:.2f} m³</span></td>
<td style="padding:14px 12px; font-weight:900; color:#fbbf24;"><span dir="ltr">{price_gravel_in:,.2f}</span></td>
<td style="padding:14px 16px; font-weight:900; color:#fbbf24; font-size:19px;"><span dir="ltr">{cost_gravel_total:,.2f} ج.م</span></td>
<td style="padding:14px 16px; font-size:15px; color:#cbd5e1;">نسبة زلط <span dir="ltr">0.80 m³/m³</span> خرسانة مسلحة</td>
</tr>
<tr style="background:rgba(30, 41, 59, 0.75); border-bottom:1.5px solid rgba(148, 163, 184, 0.25); font-size:17px; text-align:center;">
<td style="padding:14px 10px; font-weight:800; color:#fbbf24;">6</td>
<td style="padding:14px 16px; font-weight:800; text-align:right; color:#ffffff;">إجمالي توريد الرمل الحرش النظيف للخرسانة</td>
<td style="padding:14px 12px; font-weight:700; color:#a5f3fc;">متر مكعب (m³)</td>
<td style="padding:14px 12px; font-weight:900; color:#38bdf8;"><span dir="ltr">{grand_sand_m3:.2f} m³</span></td>
<td style="padding:14px 12px; font-weight:900; color:#fbbf24;"><span dir="ltr">{price_sand_in:,.2f}</span></td>
<td style="padding:14px 16px; font-weight:900; color:#fbbf24; font-size:19px;"><span dir="ltr">{cost_sand_total:,.2f} ج.م</span></td>
<td style="padding:14px 16px; font-size:15px; color:#cbd5e1;">نسبة رمل <span dir="ltr">0.40 m³/m³</span> خرسانة مسلحة</td>
</tr>
<tr style="background:rgba(15, 23, 42, 0.75); border-bottom:1.5px solid rgba(148, 163, 184, 0.25); font-size:17px; text-align:center;">
<td style="padding:14px 10px; font-weight:800; color:#fbbf24;">7</td>
<td style="padding:14px 16px; font-weight:800; text-align:right; color:#ffffff;">إجمالي مصنعيات الصب والحدادة والنجارة والتشغيل</td>
<td style="padding:14px 12px; font-weight:700; color:#a5f3fc;">متر مكعب (m³)</td>
<td style="padding:14px 12px; font-weight:900; color:#38bdf8;"><span dir="ltr">{grand_vol_concrete_all:.2f} m³</span></td>
<td style="padding:14px 12px; font-weight:900; color:#fbbf24;"><span dir="ltr">{price_labor_in:,.2f}</span></td>
<td style="padding:14px 16px; font-weight:900; color:#fbbf24; font-size:19px;"><span dir="ltr">{cost_labor_total:,.2f} ج.م</span></td>
<td style="padding:14px 16px; font-size:15px; color:#cbd5e1;">تنفيذ وتشغيل متكامل لكافة الأعمدة والبلاطات</td>
</tr>
<tr style="background:linear-gradient(90deg, rgba(161, 98, 7, 0.40) 0%, rgba(15, 23, 42, 0.85) 100%); border-top:2.5px solid #ca8a04; border-bottom:2.5px solid #ca8a04; font-size:19px; font-weight:900; text-align:center;">
<td colspan="2" style="padding:16px 16px; color:#fbbf24; text-align:right; font-size:20px;">★ الإجمالي المالي العام الشامل للمشروع (Grand Total Estimated Budget)</td>
<td style="padding:16px 12px; color:#a5f3fc; font-weight:800;">مشروع شامل (L.S)</td>
<td style="padding:16px 14px; color:#38bdf8;"><span dir="ltr">{grand_vol_concrete_all:.2f} m³ خرسانة</span></td>
<td style="padding:16px 14px; color:#cbd5e1; font-weight:900;">-</td>
<td style="padding:16px 16px; color:#fde047; font-size:22px; font-weight:900;"><span dir="ltr">{cost_grand_total:,.2f} EGP</span></td>
<td style="padding:16px 16px; color:#38bdf8; font-size:16px; font-weight:800;">شامل كافة المواد والمصنعيات بالكامل (متوسط <span dir="ltr">{cost_per_m3_all_inclusive:,.1f} ج.م/م³</span>)</td>
</tr>
</tbody>
</table>
</div>
"""
        clean_pricing_html = "\n".join(line.strip() for line in pricing_html.splitlines() if line.strip())
        if hasattr(st, "html"):
            st.html(clean_pricing_html)
        else:
            st.markdown(clean_pricing_html, unsafe_allow_html=True)

        # Materials estimation for all elements (Columns + Flat Slabs)
        with st.expander(f"🧪 تقدير مواد الخلطة الخرسانية الإجمالية للمشروع ({grand_vol_concrete_all:.2f} m³ لكافة الأعمدة والأسقف)"):
            mat_c1, mat_c2, mat_c3, mat_c4 = st.columns(4)
            mat_c1.metric(f"أسمنت ({fcu_in:.0f} kg/m³)", f"{grand_cement_tons:.2f} طن", f"{grand_cement_bags} شكارة")
            mat_c2.metric("رمل (0.40 m³/m³)", f"{grand_sand_m3:.2f} m³")
            mat_c3.metric("سن / زلط (0.80 m³/m³)", f"{grand_gravel_m3:.2f} m³")
            mat_c4.metric("مياه صالحة (W/C=0.50)", f"{grand_water_liters:.0f} لتر")

        # ────────────────────────────────────────────────────────────────────
        # BOLD FINANCIAL NOTE: GRAND TOTAL, TOTAL SLABS AREA & COST PER M2
        # ────────────────────────────────────────────────────────────────────
        if slab_results and len(slab_results) > 0 and total_area_slabs_all > 0:
            slabs_names_str = " + ".join(f"{s['name']}" for s in slab_results)
            slabs_areas_str = " + ".join(f"{s['name']} ({s['area_total_m2']:.1f} m²)" for s in slab_results)
            cost_per_m2_note_html = f"""
            <div style="
                background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #1e293b 100%);
                border: 3px solid #6366f1;
                border-radius: 12px;
                padding: 22px 26px;
                margin: 20px 0 24px 0;
                box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25);
            ">
                <div style="font-size: 24px; font-weight: 900; color: #a5b4fc; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid rgba(165, 180, 252, 0.35); padding-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 28px;">📌</span>
                        <span style="color: #ffffff !important; font-size: 24px; font-weight: 900;">ملاحظة مالية هامة وحساب متوسط تكلفة المتر المسطح (Cost per Square Meter Note)</span>
                    </div>
                    <span style="font-size: 16px; font-weight: 800; color: #ffffff !important; background: rgba(99, 102, 241, 0.35); padding: 5px 16px; border-radius: 14px; border: 1.5px solid rgba(165, 180, 252, 0.45);">
                        {len(slab_results)} نماذج بلاطات ({slabs_names_str})
                    </span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; margin-bottom: 8px;">
                    <div style="background: rgba(255, 255, 255, 0.05); padding: 16px 20px; border-radius: 10px; border-right: 5px solid #f59e0b;">
                        <div style="font-size: 17px; color: #e2e8f0; font-weight: 800; margin-bottom: 6px;">★ الإجمالي المالي العام الشامل للمشروع:</div>
                        <div style="font-size: 28px; font-weight: 900; color: #fbbf24;" dir="ltr">{cost_grand_total:,.2f} EGP</div>
                        <div style="font-size: 14.5px; color: #94a3b8; font-weight: 700; margin-top: 4px;">Grand Total Estimated Budget (شامل كافة المواد والمصنعيات)</div>
                    </div>
                    <div style="background: rgba(255, 255, 255, 0.05); padding: 16px 20px; border-radius: 10px; border-right: 5px solid #10b981;">
                        <div style="font-size: 17px; color: #e2e8f0; font-weight: 800; margin-bottom: 6px;">📐 إجمالي مساحة نماذج البلاطات ({slabs_names_str}):</div>
                        <div style="font-size: 28px; font-weight: 900; color: #34d399;" dir="ltr">{total_area_slabs_all:,.2f} m²</div>
                        <div style="font-size: 14.5px; color: #a7f3d0; font-weight: 700; margin-top: 4px;">{slabs_areas_str}</div>
                    </div>
                    <div style="background: linear-gradient(135deg, rgba(56, 189, 248, 0.20) 0%, rgba(99, 102, 241, 0.25) 100%); padding: 16px 20px; border-radius: 10px; border-right: 5px solid #38bdf8; border: 2px solid rgba(56, 189, 248, 0.40);">
                        <div style="font-size: 17px; color: #ffffff; font-weight: 900; margin-bottom: 6px;">💰 تكلفة المتر المسطح بالجنيه (Cost / m²):</div>
                        <div style="font-size: 32px; font-weight: 900; color: #38bdf8;" dir="ltr">{cost_per_m2_slab:,.2f} ج.م / م²</div>
                        <div style="font-size: 15px; color: #e0f2fe; font-weight: 800; margin-top: 4px;">= ({cost_grand_total:,.0f} ج.م ÷ {total_area_slabs_all:,.1f} م²)</div>
                    </div>
                </div>
            </div>
            """
            clean_note_html = "\n".join(line.strip() for line in cost_per_m2_note_html.splitlines() if line.strip())
            if hasattr(st, "html"):
                st.html(clean_note_html)
            else:
                st.markdown(clean_note_html, unsafe_allow_html=True)

        # ────────────────────────────────────────────────────────────────────
        # SAVE & PRINT ACTIONS SECTION (حفظ وطباعة النتائج لجميع النماذج)
        # ────────────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🖨️ حفظ وطباعة نتائج الحصر والمقايسة المالية (Save & Print Reports)")

        pricing_dict = {
            "price_steel": float(price_steel_in),
            "price_cement": float(price_cement_in),
            "price_gravel": float(price_gravel_in),
            "price_sand": float(price_sand_in),
            "price_labor": float(price_labor_in),
        }

        first_draw_b64 = all_drawings[0]["img_b64"] if all_drawings else (slab_drawings[0]["img_b64"] if slab_drawings else None)

        col_survey_html = generate_column_survey_report_html(
            project_name=project_name_in,
            b=col_results[0]["b"],
            t=col_results[0]["t"],
            H=col_h_in,
            t_slab=t_slab_in,
            fcu=fcu_in,
            n_cols=total_cols_all,
            n_bars=col_results[0]["n_bars"],
            phi_main=col_results[0]["phi_main"],
            n_rows=col_results[0]["n_rows"],
            tie_type=col_results[0]["tie_type"],
            n_st_m=n_st_m,
            phi_st=phi_st,
            is_top_floor=is_top,
            lap_factor=lap_factor_sel,
            L_bar_m=col_results[0]["L_bar_m"],
            L_bar_cm=col_results[0]["L_bar_cm"],
            w_main_total_kg=total_w_main_kg_all,
            w_main_total_ton=total_w_main_ton_all,
            L_tie_m=col_results[0]["L_tie_m"],
            L_tie_cm=col_results[0]["L_tie_cm"],
            n_ties_per_col=col_results[0]["n_ties_per_col"],
            w_st_total_kg=total_w_st_kg_all,
            w_st_total_ton=total_w_st_ton_all,
            vol_col_single_m3=col_results[0]["vol_col_single_m3"],
            vol_col_total_m3=total_vol_all,
            w_steel_total_kg=grand_w_steel_kg_all,
            w_steel_total_ton=grand_w_steel_ton_all,
            steel_rate_kg_m3=grand_overall_steel_rate,
            cement_tons=grand_cement_tons,
            cement_bags=grand_cement_bags,
            sand_m3=grand_sand_m3,
            gravel_m3=grand_gravel_m3,
            water_liters=grand_water_liters,
            img_plan_b64=first_draw_b64,
            img_elev_b64=None,
            col_results=col_results,
            drawings_list=all_drawings,
            slab_results=slab_results,
            slab_drawings_list=slab_drawings,
            pricing_data=pricing_dict,
        )

        pdf_bytes = html_to_pdf_bytes(col_survey_html)

        # CSV export data for all items and pricing
        export_rows = []
        for r in col_results:
            c_name = r["name"]
            export_rows.append({"العنصر": "أعمدة", "النموذج": c_name, "البند": f"خرسانة مسلحة شاملة ({c_name})", "المواصفة": f"{r['b']:.0f}×{r['t']:.0f} cm", "العدد": r['n_cols'], "الكمية": f"{r['vol_col_total_m3']:.2f}", "الوحدة": "متر مكعب m³", "سعر الوحدة (ج.م)": f"{rate_cols_per_m3:.2f}", "إجمالي السعر (ج.م)": f"{r['vol_col_total_m3'] * rate_cols_per_m3:.2f}"})
            export_rows.append({"العنصر": "أعمدة", "النموذج": c_name, "البند": f"حديد رئيسي ({c_name})", "المواصفة": f"{r['n_bars']} Φ{r['phi_main']} mm", "العدد": r['n_cols'], "الكمية": f"{r['w_main_total_ton']:.3f}", "الوحدة": "طن Ton", "سعر الوحدة (ج.م)": f"{price_steel_in:.2f}", "إجمالي السعر (ج.م)": f"{r['w_main_total_ton'] * price_steel_in:.2f}"})
            export_rows.append({"العنصر": "أعمدة", "النموذج": c_name, "البند": f"حديد كانات ({c_name})", "المواصفة": f"{r['tie_type'].split(' ')[0]} Φ{phi_st} mm", "العدد": r['n_cols'], "الكمية": f"{r['w_st_total_ton']:.3f}", "الوحدة": "طن Ton", "سعر الوحدة (ج.م)": f"{price_steel_in:.2f}", "إجمالي السعر (ج.م)": f"{r['w_st_total_ton'] * price_steel_in:.2f}"})

        for s in slab_results:
            s_name = s["name"]
            export_rows.append({"العنصر": "بلاطات مسطحة", "النموذج": s_name, "البند": f"خرسانة مسلحة شاملة ({s_name})", "المواصفة": f"{s['lx']:.1f}×{s['ly']:.1f} m (ts={s['ts']:.0f}cm)", "العدد": s['n_rep'], "الكمية": f"{s['vol_total_m3']:.2f}", "الوحدة": "متر مكعب m³", "سعر الوحدة (ج.م)": f"{rate_slabs_per_m3:.2f}", "إجمالي السعر (ج.م)": f"{s['vol_total_m3'] * rate_slabs_per_m3:.2f}"})
            
            top_add_desc = []
            for tm in s.get("top_add_models_res", []):
                if tm["w_total_kg"] > 0:
                    top_add_desc.append(f"علوي [{tm['name']}]: {tm['nx']:.0f}Φ{tm['phi']}/م'(X)+{tm['ny']:.0f}Φ{tm['phi']}/م'(Y)×{tm['n_zones']}")
            btm_add_desc = []
            for bm in s.get("btm_add_models_res", []):
                if bm["w_total_kg"] > 0:
                    btm_add_desc.append(f"سفلي [{bm['name']}]: {bm['nx']:.0f}Φ{bm['phi']}/م'(X)+{bm['ny']:.0f}Φ{bm['phi']}/م'(Y)×{bm['n_zones']}")

            rebar_desc_str = f"سفلي ({s['nb_bx']}Φ{s['phi_bx']}+{s['nb_by']}Φ{s['phi_by']}) علوي ({s['nb_tx']}Φ{s['phi_tx']}+{s['nb_ty']}Φ{s['phi_ty']})"
            if top_add_desc:
                rebar_desc_str += " + " + " + ".join(top_add_desc)
            elif s.get("w_top_add_kg", 0.0) > 0:
                rebar_desc_str += f" + إضافي علوي ({s.get('n_top_add_x',0)}Φ{s.get('phi_top_add',12)}+{s.get('n_top_add_y',0)}Φ{s.get('phi_top_add',12)})"

            if btm_add_desc:
                rebar_desc_str += " + " + " + ".join(btm_add_desc)
            elif s.get("w_btm_add_kg", 0.0) > 0:
                rebar_desc_str += f" + إضافي سفلي ({s.get('n_btm_add_x',0)}Φ{s.get('phi_btm_add',12)}+{s.get('n_btm_add_y',0)}Φ{s.get('phi_btm_add',12)})"
            
            export_rows.append({"العنصر": "بلاطات مسطحة", "النموذج": s_name, "البند": f"حديد تسليح شبكات وإضافي ({s_name})", "المواصفة": rebar_desc_str, "العدد": s['n_rep'], "الكمية": f"{s['w_steel_total_ton']:.3f}", "الوحدة": "طن Ton", "سعر الوحدة (ج.م)": f"{price_steel_in:.2f}", "إجمالي السعر (ج.م)": f"{s['w_steel_total_ton'] * price_steel_in:.2f}"})

        export_rows.append({"العنصر": "مقايسة إجمالية", "النموذج": "المشروع", "البند": "إجمالي توريد حديد التسليح", "المواصفة": "كافة الأقطار", "العدد": "-", "الكمية": f"{grand_w_steel_ton_all:.3f}", "الوحدة": "طن Ton", "سعر الوحدة (ج.م)": f"{price_steel_in:.2f}", "إجمالي السعر (ج.م)": f"{cost_steel_total:.2f}"})
        cement_spec_str = f"{fcu_in:.0f} kg/m³" if fcu_in == fcu_fs_in else f"أعمدة {fcu_in:.0f} + بلاطات {fcu_fs_in:.0f} kg/m³"
        export_rows.append({"العنصر": "مقايسة إجمالية", "النموذج": "المشروع", "البند": "إجمالي توريد الأسمنت البورتلاندي", "المواصفة": cement_spec_str, "العدد": "-", "الكمية": f"{grand_cement_tons:.2f}", "الوحدة": "طن Ton", "سعر الوحدة (ج.م)": f"{price_cement_in:.2f}", "إجمالي السعر (ج.م)": f"{cost_cement_total:.2f}"})
        export_rows.append({"العنصر": "مقايسة إجمالية", "النموذج": "المشروع", "البند": "إجمالي توريد السن / الزلط", "المواصفة": "متدرج 0.80 m³/m³", "العدد": "-", "الكمية": f"{grand_gravel_m3:.2f}", "الوحدة": "متر مكعب m³", "سعر الوحدة (ج.م)": f"{price_gravel_in:.2f}", "إجمالي السعر (ج.م)": f"{cost_gravel_total:.2f}"})
        export_rows.append({"العنصر": "مقايسة إجمالية", "النموذج": "المشروع", "البند": "إجمالي توريد الرمل النظيف", "المواصفة": "حرش 0.40 m³/m³", "العدد": "-", "الكمية": f"{grand_sand_m3:.2f}", "الوحدة": "متر مكعب m³", "سعر الوحدة (ج.م)": f"{price_sand_in:.2f}", "إجمالي السعر (ج.م)": f"{cost_sand_total:.2f}"})
        export_rows.append({"العنصر": "مقايسة إجمالية", "النموذج": "المشروع", "البند": "إجمالي مصنعيات الصب والتنفيذ", "المواصفة": "كامل المسطحات", "العدد": "-", "الكمية": f"{grand_vol_concrete_all:.2f}", "الوحدة": "متر مكعب m³", "سعر الوحدة (ج.م)": f"{price_labor_in:.2f}", "إجمالي السعر (ج.م)": f"{cost_labor_total:.2f}"})
        export_rows.append({"العنصر": "الإجمالي العام", "النموذج": "المشروع بالكامل", "البند": "★ الإجمالي المالي العام الشامل للمشروع", "المواصفة": "شامل كافة المواد والمصنعيات", "العدد": "-", "الكمية": f"{grand_vol_concrete_all:.2f} m³ خرسانة | {grand_w_steel_ton_all:.3f} Ton حديد", "الوحدة": "مشروع شامل (L.S)", "سعر الوحدة (ج.م)": "-", "إجمالي السعر (ج.م)": f"{cost_grand_total:.2f}"})

        export_df = pd.DataFrame(export_rows)
        csv_data = export_df.to_csv(index=False).encode('utf-8-sig')

        c_save1, c_save2 = st.columns([3, 1])
        with c_save1:
            st.markdown(
                f"""
                <div style='background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:14px 16px;'>
                    <div style='font-weight:700; color:#1e293b; font-size:1.0rem;'>
                        📄 ملف المذكرة الحسابية والمقايسة الهندسية الشاملة (ECP 203 Quantity Survey & BOQ Sheet)
                    </div>
                    <div style='font-size:0.88rem; color:#64748b; margin-top:2px;'>
                        يتضمن جميع المدخلات، والمخططات الهندسية وتفريد التسليح (BBS)، وجداول حصر الكميات لـ <b>{len(col_results)} نماذج أعمدة ({total_cols_all} عمود)</b> و <b>{len(slab_results)} نماذج بلاطات ({total_slabs_count} مسطح)</b>، وجدول المقايسة وحصر الأسعار الشامل (إجمالي خرسانة: <b>{grand_vol_concrete_all:.2f} m³</b>، حديد: <b>{grand_w_steel_ton_all:.3f} Ton</b>، تكلفة: <b>{cost_grand_total:,.0f} EGP</b>).
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_save2:
            prefix = get_safe_profile_filename_prefix()
            st.download_button(
                label="🌐 Save Calculation Sheet (HTML)",
                data=col_survey_html,
                file_name=f"{prefix}ECP203_Concrete_Survey_Takeoff_BOQ_{len(col_results)}Cols_{len(slab_results)}Slabs.html",
                mime="text/html",
                use_container_width=True,
                key="cs_btn_save_html",
            )
            if pdf_bytes:
                st.download_button(
                    label="📕 Save as PDF (مباشر)",
                    data=pdf_bytes,
                    file_name=f"{prefix}ECP203_Concrete_Survey_Takeoff_BOQ_{len(col_results)}Cols_{len(slab_results)}Slabs.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="cs_btn_save_pdf",
                )
            else:
                st.download_button(
                    label="🌐 فتح للطباعة وحفظ PDF",
                    data=col_survey_html,
                    file_name=f"{prefix}ECP203_Concrete_Survey_Takeoff_BOQ_{len(col_results)}Cols_{len(slab_results)}Slabs.html",
                    mime="text/html",
                    use_container_width=True,
                    key="cs_btn_save_html_print",
                )
            st.download_button(
                label="📊 Export Data to Excel / CSV",
                data=csv_data,
                file_name=f"{prefix}ECP203_Concrete_Survey_Takeoff_BOQ_{len(col_results)}Cols_{len(slab_results)}Slabs.csv",
                mime="text/csv",
                use_container_width=True,
                key="cs_btn_save_csv",
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
                pc_l = st.number_input("متوسط الطول L (m)", min_value=0.0, value=float(cfg_val("surv_pc_l", 2.20)), step=0.10, key="surv_pc_l")
                pc_b = st.number_input("متوسط العرض B (m)", min_value=0.0, value=float(cfg_val("surv_pc_b", 2.00)), step=0.10, key="surv_pc_b")
                pc_t = st.number_input("السماكة t (m)", min_value=0.0, value=float(cfg_val("surv_pc_t", 0.30)), step=0.05, key="surv_pc_t")
                pc_n = st.number_input("عدد القواعد العادية", min_value=0, value=int(cfg_val("surv_pc_n", 12)), step=1, key="surv_pc_n")
                pc_vol = pc_l * pc_b * pc_t * pc_n
                st.markdown(f"**حجم خرسانة عادية:** `{pc_vol:.2f} m³`")

            with f_col2:
                st.markdown("**القواعد المسلحة (Reinforced Concrete - RC)**")
                rc_l = st.number_input("متوسط الطول L (m)", min_value=0.0, value=float(cfg_val("surv_rc_l", 1.80)), step=0.10, key="surv_rc_l")
                rc_b = st.number_input("متوسط العرض B (m)", min_value=0.0, value=float(cfg_val("surv_rc_b", 1.60)), step=0.10, key="surv_rc_b")
                rc_t = st.number_input("السماكة t (m)", min_value=0.0, value=float(cfg_val("surv_rc_t", 0.60)), step=0.05, key="surv_rc_t")
                rc_n = st.number_input("عدد القواعد المسلحة", min_value=0, value=int(cfg_val("surv_rc_n", 12)), step=1, key="surv_rc_n")
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
        render_styled_table(breakdown_df)

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

            render_styled_table(table_summary)

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
            def_mix_cement = float(st.session_state.get("cs_fcu", 350.0))
            cement_content = st.number_input(
                f"محتوى الأسمنت (kg/m³) — إجهاد المشروع fcu = {def_mix_cement:.0f}",
                min_value=150.0,
                max_value=800.0,
                value=float(st.session_state.get("mix_cement_content", def_mix_cement)),
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
        render_styled_table(mat_summary)

        res1, res2, res3, res4 = st.columns(4)
        res1.metric("إجمالي الأسمنت", f"{tot_cement_tons:.2f} Ton", f"{tot_cement_bags:.0f} شكارة")
        res2.metric("إجمالي الرمل", f"{tot_sand_m3:.2f} m³")
        res3.metric("إجمالي السن/الزلط", f"{tot_gravel_m3:.2f} m³")
        res4.metric("إجمالي المياه", f"{tot_water_liters:.0f} L")
