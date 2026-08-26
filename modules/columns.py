"""
Module 1 - Rectangular Column Design (ECP 203)
Units: ton, kg, cm, kg/cm²
"""
import io
import base64
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
import streamlit as st
import pandas as pd
from modules import settings as S


# ---------------------------------------------------------------------------
# Drawing function: Rectangular Column Structural Output Sheet
# ---------------------------------------------------------------------------

def draw_rectangular_column_output(
    b: float,
    t: float,
    main_steel_str: str,
    stirrups_str: str,
    Pu: float,
    fcu: float = 250,
    fy: float = 4000,
    mu_percent: float = 1.0,
    n_bars: int = None,
    phi_mm: int = None,
    phi_st_mm: int = 8,
    n_st_per_m: int = 5,
    s_calc: float = 20.0,
    pu_cap: float = None,
    cover: float = 2.5,
    slender_str: str = "Short Column (λb ≤ 10)",
    H_clear: float = 300.0,
    save_path: str = None,
):
    """
    Renders an engineering design output sheet for a rectangular reinforced concrete column (ECP 203).
    Creates a structural CAD-like cross-section alongside a detailed Rebar Bending / Detailing sketch
    and a comprehensive Design & Quantities Take-off Summary Card.
    Units strictly in: kg, cm, ton, kg/cm² (No Newton / MPa units).
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"]

    # Ensure material strength units are in kg/cm²
    fcu_kg = fcu if fcu > 100 else fcu * 10.0
    fy_kg = fy if fy > 100 else fy * 10.0

    b_val = float(b)
    t_val = float(t)
    b_disp = f"{int(b_val)}" if b_val == int(b_val) else f"{b_val:.1f}"
    t_disp = f"{int(t_val)}" if t_val == int(t_val) else f"{t_val:.1f}"

    # Extract bar count and diameter if not explicitly provided
    if n_bars is None or phi_mm is None:
        try:
            cleaned = str(main_steel_str).replace("Φ", " ").replace("mm", " ").split()
            if len(cleaned) >= 2:
                n_bars = int(cleaned[0]) if n_bars is None else n_bars
                phi_mm = int(cleaned[1]) if phi_mm is None else phi_mm
        except Exception:
            pass
    n_bars = n_bars or 4
    phi_mm = phi_mm or 16

    # ── Detailed Rebar & Quantities Calculations for Detailing ──
    H_m = float(H_clear) / 100.0
    L_splice_m = max(1.0, (50.0 * phi_mm) / 1000.0)
    L_splice_cm = L_splice_m * 100.0
    L_bar_m = H_m + L_splice_m
    L_bar_cm = float(H_clear) + L_splice_cm
    unit_w_main = (phi_mm ** 2) / 162.0
    tot_len_main_m = n_bars * L_bar_m
    tot_w_main_kg = tot_len_main_m * unit_w_main

    b_core = max(b_val - 2 * cover, 1.0)
    t_core = max(t_val - 2 * cover, 1.0)
    hook_len_cm = max(8.0, 10.0 * (phi_st_mm / 10.0))

    # Rebar grid geometry calculation
    offset_x = cover + (phi_mm / 10.0) / 2.0
    offset_y = cover + (phi_mm / 10.0) / 2.0
    w_rebar = max(b_val - 2 * offset_x, 1.0)
    h_rebar = max(t_val - 2 * offset_y, 1.0)

    if n_bars <= 4:
        nx, ny = 2, 2
    else:
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

    # Check if Automatic Stirrup (كانة أوتوماتيك) is required (more than 3 rows in depth: ny > 3 or nx > 3)
    is_auto_tie = (ny > 3) or (nx > 3)

    if is_auto_tie:
        # Inner loop geometry
        if ny >= 4 and nx == 2:
            t_core_in = max(float(ys_d[-2] - ys_d[1]) + (phi_mm / 10.0), 5.0)
            b_core_in = b_core
            L_tie_cm = 2.0 * (b_core + t_core) + 2.0 * (b_core_in + t_core_in) + 4.0 * hook_len_cm
            tie_type_str = "Automatic 4-Branch Tie (كانة أوتوماتيك)"
        elif nx >= 3 and ny >= 3:
            b_core_in = max(float(xs_b[-2] - xs_b[1]) + (phi_mm / 10.0), 5.0)
            t_core_in = max(float(ys_d[-2] - ys_d[1]) + (phi_mm / 10.0), 5.0)
            L_tie_cm = 2.0 * (b_core + t_core) + 2.0 * (b_core_in + t_core_in) + 4.0 * hook_len_cm
            tie_type_str = "Automatic Multi-Branch Tie (كانة أوتوماتيك)"
        else:
            t_core_in = t_core * 0.5
            b_core_in = b_core
            L_tie_cm = 2.0 * (b_core + t_core) + 2.0 * (b_core_in + t_core_in) + 4.0 * hook_len_cm
            tie_type_str = "Automatic 4-Branch Tie (كانة أوتوماتيك)"
    else:
        t_core_in = 0.0
        b_core_in = 0.0
        L_tie_cm = 2.0 * (b_core + t_core) + 2.0 * hook_len_cm
        tie_type_str = "Closed Box Tie (كانة صندوقية)"

    L_tie_m = L_tie_cm / 100.0
    n_ties = max(5, int(math.ceil(H_m * n_st_per_m)))
    unit_w_st = (phi_st_mm ** 2) / 162.0
    tot_len_st_m = n_ties * L_tie_m
    tot_w_st_kg = tot_len_st_m * unit_w_st

    tot_steel_kg = tot_w_main_kg + tot_w_st_kg
    vol_conc_m3 = (b_val / 100.0) * (t_val / 100.0) * H_m
    steel_ratio = (tot_steel_kg / vol_conc_m3) if vol_conc_m3 > 0 else 0.0

    cement_kg = vol_conc_m3 * 350.0
    cement_bags = int(round(cement_kg / 50.0))
    gravel_m3 = vol_conc_m3 * 0.80
    sand_m3 = vol_conc_m3 * 0.40

    # Create figure: Row 0 has 2 drawings side-by-side across full width, Row 1 has horizontal summary strip
    fig = plt.figure(figsize=(17.5, 10.0), dpi=140, facecolor="#ffffff")
    gs = fig.add_gridspec(
        2, 2, height_ratios=[3.6, 1.55], width_ratios=[1.0, 1.25],
        wspace=0.10, hspace=0.20, left=0.03, right=0.97, top=0.92, bottom=0.035
    )
    ax_sec = fig.add_subplot(gs[0, 0])
    ax_det = fig.add_subplot(gs[0, 1])
    ax_strip = fig.add_subplot(gs[1, :])

    # ═══════════════════════════════════════════════════════════════════════
    # 1. LEFT SUBPLOT: COLUMN CROSS-SECTION & AUTOMATIC TIES
    # ═══════════════════════════════════════════════════════════════════════
    ax_sec.set_facecolor("#ffffff")

    # Concrete outer rectangle
    col_rect = patches.Rectangle(
        (0, 0), b_val, t_val,
        linewidth=3.0, edgecolor="#0f172a", facecolor="#e6ecf5", zorder=1,
    )
    ax_sec.add_patch(col_rect)

    st_x = cover
    st_y = cover
    st_w = b_core
    st_h = t_core

    core_rect = patches.Rectangle(
        (st_x, st_y), st_w, st_h,
        facecolor="#f1f5f9", edgecolor="none", zorder=2,
    )
    ax_sec.add_patch(core_rect)

    # Outer perimeter tie
    rounding = min(1.5, cover * 0.6)
    stirrup_patch = FancyBboxPatch(
        (st_x, st_y), st_w, st_h,
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        linewidth=2.6, edgecolor="#16a34a", facecolor="none", zorder=4,
    )
    ax_sec.add_patch(stirrup_patch)

    hook_sz = min(3.5, max(2.2, st_w * 0.15))
    ax_sec.plot([st_x, st_x + hook_sz * 0.707], [st_y + st_h, st_y + st_h - hook_sz * 0.707], color="#16a34a", lw=2.6, zorder=5)
    ax_sec.plot([st_x + hook_sz * 0.707, st_x], [st_y + st_h - hook_sz * 0.707, st_y + st_h - hook_sz * 1.15], color="#16a34a", lw=2.6, zorder=5)

    bar_radius = max(1.15, min(2.2, (phi_mm / 10.0) * 0.90))

    rebar_coords = []
    for x in xs_b:
        rebar_coords.append((x, offset_y))
    for x in xs_b:
        rebar_coords.append((x, t_val - offset_y))
    for y in ys_d[1:-1]:
        rebar_coords.append((offset_x, y))
        rebar_coords.append((b_val - offset_x, y))

    unique_rebars = []
    for pt in rebar_coords:
        if not any(np.isclose(pt[0], u[0], atol=1e-2) and np.isclose(pt[1], u[1], atol=1e-2) for u in unique_rebars):
            unique_rebars.append(pt)

    # Inner Automatic Stirrup loop (drawn when ny > 3 or nx > 3)
    if is_auto_tie:
        if ny >= 4 and nx == 2:
            in_y_min = ys_d[1] - (phi_mm / 10.0) / 2.0 - 0.4
            in_y_max = ys_d[-2] + (phi_mm / 10.0) / 2.0 + 0.4
            in_h = in_y_max - in_y_min
            inner_stirrup = FancyBboxPatch(
                (st_x + 0.5, in_y_min), st_w - 1.0, in_h,
                boxstyle=f"round,pad=0,rounding_size={rounding}",
                linewidth=2.2, edgecolor="#059669", facecolor="#ecfdf5", linestyle="-", zorder=3,
            )
            ax_sec.add_patch(inner_stirrup)
            # Inner tie hooks
            ax_sec.plot([st_x + 0.5, st_x + 0.5 + hook_sz * 0.6], [in_y_min + in_h, in_y_min + in_h - hook_sz * 0.6], color="#059669", lw=2.2, zorder=5)
            ax_sec.plot([st_x + 0.5 + hook_sz * 0.6, st_x + 0.5], [in_y_min + in_h - hook_sz * 0.6, in_y_min + in_h - hook_sz * 0.9], color="#059669", lw=2.2, zorder=5)

        elif nx >= 3 and ny >= 3:
            in_x_min = xs_b[1] - (phi_mm / 10.0) / 2.0 - 0.4
            in_x_max = xs_b[-2] + (phi_mm / 10.0) / 2.0 + 0.4
            in_y_min = ys_d[1] - (phi_mm / 10.0) / 2.0 - 0.4
            in_y_max = ys_d[-2] + (phi_mm / 10.0) / 2.0 + 0.4
            inner_stirrup = FancyBboxPatch(
                (in_x_min, in_y_min), in_x_max - in_x_min, in_y_max - in_y_min,
                boxstyle=f"round,pad=0,rounding_size={rounding}",
                linewidth=2.2, edgecolor="#059669", facecolor="#ecfdf5", linestyle="-", zorder=3,
            )
            ax_sec.add_patch(inner_stirrup)

    for rx, ry in unique_rebars:
        rebar_circle = Circle((rx, ry), radius=bar_radius, facecolor="#dc2626", edgecolor="#1e293b", linewidth=1.5, zorder=6)
        ax_sec.add_patch(rebar_circle)

    dim_offset = max(7.0, min(b_val, t_val) * 0.18)
    y_dim = -dim_offset
    ax_sec.plot([0, 0], [0, y_dim - 1.2], color="#94a3b8", lw=1.2, linestyle=":", zorder=2)
    ax_sec.plot([b_val, b_val], [0, y_dim - 1.2], color="#94a3b8", lw=1.2, linestyle=":", zorder=2)
    ax_sec.annotate("", xy=(b_val, y_dim), xytext=(0, y_dim), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.8, shrinkA=0, shrinkB=0))
    ax_sec.text(b_val / 2.0, y_dim - 1.6, f"b = {b_disp} cm", ha="center", va="top", fontsize=13.5, weight="bold", color="#0f172a")

    x_dim = -dim_offset
    ax_sec.plot([0, x_dim - 1.2], [0, 0], color="#94a3b8", lw=1.2, linestyle=":", zorder=2)
    ax_sec.plot([0, x_dim - 1.2], [t_val, t_val], color="#94a3b8", lw=1.2, linestyle=":", zorder=2)
    ax_sec.annotate("", xy=(x_dim, t_val), xytext=(x_dim, 0), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.8, shrinkA=0, shrinkB=0))
    ax_sec.text(x_dim - 1.6, t_val / 2.0, f"t = {t_disp} cm", ha="right", va="center", rotation=90, fontsize=13.5, weight="bold", color="#0f172a")

    top_right_bar = (b_val - offset_x, t_val - offset_y)
    ax_sec.annotate(
        f"Main: {main_steel_str} ({ny} Rows)", xy=top_right_bar, xytext=(b_val * 0.30, t_val + dim_offset * 1.10),
        arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.8, connectionstyle="arc3,rad=-0.15"),
        fontsize=13, weight="bold", color="#991b1b", ha="left", va="bottom",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.4),
    )

    stirrup_label = f"Auto Ties: {n_st_per_m}Φ{phi_st_mm}/m'" if is_auto_tie else f"Ties: {stirrups_str}"
    top_left_stirrup = (st_x + st_w * 0.25, st_y + st_h)
    ax_sec.annotate(
        stirrup_label, xy=top_left_stirrup, xytext=(b_val * 0.10, t_val + dim_offset * 1.10),
        arrowprops=dict(arrowstyle="->", color="#16a34a", lw=1.8, connectionstyle="arc3,rad=0.15"),
        fontsize=13, weight="bold", color="#15803d", ha="right", va="bottom",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#dcfce7", edgecolor="#22c55e", lw=1.4),
    )

    pad_left = dim_offset + 10
    pad_right = max(dim_offset + 14, b_val * 0.4 + 16)
    pad_y_top = dim_offset * 1.10 + 16
    pad_y_bot = dim_offset + 12
    ax_sec.set_xlim(-pad_left, b_val + pad_right)
    ax_sec.set_ylim(-pad_y_bot, t_val + pad_y_top)
    ax_sec.set_aspect("equal", adjustable="box")
    ax_sec.axis("off")
    sec_title = f"1. COLUMN CROSS-SECTION ({b_disp}×{t_disp} cm — {ny} REBAR ROWS)"
    ax_sec.text((b_val) / 2.0, -pad_y_bot + 1.2, sec_title, ha="center", va="bottom", fontsize=13.5, weight="bold", color="#0f172a")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. RIGHT SUBPLOT: REBAR BENDING & AUTOMATIC TIES BBS
    # ═══════════════════════════════════════════════════════════════════════
    ax_det.set_facecolor("#ffffff")
    ax_det.axis("off")
    ax_det.set_xlim(0, 1)
    ax_det.set_ylim(0, 1)

    det_bg = FancyBboxPatch((0.01, 0.01), 0.98, 0.98, boxstyle="round,pad=0.02,rounding_size=0.03", linewidth=2.0, edgecolor="#94a3b8", facecolor="#f8fafc", zorder=1)
    ax_det.add_patch(det_bg)

    ax_det.text(0.50, 0.945, "2. REBAR BENDING & DETAILING DIAGRAM (BBS)", ha="center", va="center", fontsize=14, weight="bold", color="#0f172a", zorder=3)

    # Sub-section A: Main Rebar
    rx = 0.14
    y_bot = 0.56
    y_col_top = 0.81
    y_splice_top = 0.90

    ax_det.plot([rx, rx], [y_bot, y_col_top], color="#dc2626", lw=3.4, zorder=4)
    ax_det.plot([rx, rx + 0.022], [y_col_top, y_col_top + 0.02], color="#dc2626", lw=3.4, zorder=4)
    ax_det.plot([rx + 0.022, rx + 0.022], [y_col_top + 0.02, y_splice_top], color="#dc2626", lw=3.4, zorder=4)
    ax_det.plot([rx, rx - 0.045], [y_bot, y_bot], color="#dc2626", lw=3.4, zorder=4)

    ax_det.annotate("", xy=(0.055, y_col_top), xytext=(0.055, y_bot), arrowprops=dict(arrowstyle="<->", color="#475569", lw=1.4))
    ax_det.text(0.04, (y_bot + y_col_top) / 2, f"H = {H_clear:.0f} cm", ha="right", va="center", fontsize=11, weight="bold", color="#334155", rotation=90)

    ax_det.annotate("", xy=(0.055, y_splice_top), xytext=(0.055, y_col_top), arrowprops=dict(arrowstyle="<->", color="#b91c1c", lw=1.4))
    ax_det.text(0.04, (y_col_top + y_splice_top) / 2, f"Ld={L_splice_cm:.0f}cm", ha="right", va="center", fontsize=10.5, weight="bold", color="#b91c1c", rotation=90)

    ax_det.text(0.24, 0.86, f"• Main Bar Diameter:  Φ {phi_mm} mm", fontsize=12.5, weight="bold", color="#1e293b", zorder=3)
    ax_det.text(0.24, 0.79, f"• Total Bars Count:  {n_bars} Bars ({ny} Rows × {nx} Cols)", fontsize=12.5, weight="bold", color="#1e293b", zorder=3)
    ax_det.text(0.24, 0.72, f"• Cut Length / Bar:  {L_bar_m:.2f} m' ({L_bar_cm:.0f} cm)", fontsize=12.5, weight="bold", color="#991b1b", zorder=3)
    ax_det.text(0.24, 0.65, f"• Total Steel Length:  {tot_len_main_m:,.1f} m'", fontsize=12, color="#475569", zorder=3)
    ax_det.text(0.24, 0.58, f"• Total Main Weight:  {tot_w_main_kg:.1f} kg ({tot_w_main_kg/1000.0:.3f} Ton)", fontsize=13, weight="bold", color="#047857", zorder=3)

    ax_det.plot([0.03, 0.97], [0.51, 0.51], color="#cbd5e1", lw=1.4, linestyle="--", zorder=3)

    # Sub-section B: Stirrups (Automatic vs Closed)
    tie_header = "B. AUTOMATIC 4-BRANCH TIE (ECP 203)" if is_auto_tie else "B. CLOSED STIRRUP TIE"
    ax_det.text(0.50, 0.47, tie_header, ha="center", va="center", fontsize=13, weight="bold", color="#15803d", zorder=3)

    sx = 0.06
    sy = 0.08
    sw = 0.16
    sh = 0.32

    # Outer tie
    st_outer = FancyBboxPatch(
        (sx, sy), sw, sh,
        boxstyle="round,pad=0,rounding_size=0.015",
        linewidth=2.6, edgecolor="#16a34a", facecolor="#f0fdf4", zorder=4,
    )
    ax_det.add_patch(st_outer)

    # Outer tie hooks
    ax_det.plot([sx, sx + 0.03], [sy + sh, sy + sh - 0.03], color="#15803d", lw=2.6, zorder=5)
    ax_det.plot([sx + 0.03, sx], [sy + sh - 0.03, sy + sh - 0.055], color="#15803d", lw=2.6, zorder=5)

    if is_auto_tie:
        # Inner automatic loop
        sh_in = sh * 0.50
        sy_in = sy + (sh - sh_in) / 2.0
        st_inner = FancyBboxPatch(
            (sx + 0.015, sy_in), sw - 0.03, sh_in,
            boxstyle="round,pad=0,rounding_size=0.012",
            linewidth=2.2, edgecolor="#059669", facecolor="#dcfce7", zorder=5,
        )
        ax_det.add_patch(st_inner)
        # Inner tie hooks
        ax_det.plot([sx + 0.015, sx + 0.015 + 0.025], [sy_in + sh_in, sy_in + sh_in - 0.025], color="#059669", lw=2.2, zorder=6)
        ax_det.plot([sx + 0.015 + 0.025, sx + 0.015], [sy_in + sh_in - 0.025, sy_in + sh_in - 0.045], color="#059669", lw=2.2, zorder=6)

        ax_det.text(sx + sw / 2, sy - 0.025, f"b'={b_core:.0f}cm", ha="center", va="top", fontsize=11, weight="bold", color="#166534")
        ax_det.text(sx + sw + 0.012, sy + sh / 2, f"t'={t_core:.0f}cm (In={t_core_in:.0f})", ha="left", va="center", fontsize=10.5, weight="bold", color="#166534", rotation=90)
    else:
        ax_det.text(sx + sw / 2, sy - 0.025, f"b' = {b_core:.0f} cm", ha="center", va="top", fontsize=11, weight="bold", color="#166534")
        ax_det.text(sx + sw + 0.015, sy + sh / 2, f"t' = {t_core:.0f} cm", ha="left", va="center", fontsize=11, weight="bold", color="#166534", rotation=90)

    ax_det.text(0.30, 0.40, f"• Tie Type:  {tie_type_str}", fontsize=12.5, weight="bold", color="#166534", zorder=3)
    if is_auto_tie:
        ax_det.text(0.30, 0.33, f"• Tie Dimensions:  Outer {b_core:.0f}×{t_core:.0f} cm | Inner {b_core_in:.0f}×{t_core_in:.0f} cm", fontsize=11.5, color="#334155", zorder=3)
    else:
        ax_det.text(0.30, 0.33, f"• Tie Outer Dimensions:  {b_core:.0f} × {t_core:.0f} cm", fontsize=12, color="#475569", zorder=3)
    ax_det.text(0.30, 0.26, f"• Cut Length / Tie:  {L_tie_cm:.1f} cm ({L_tie_m:.2f} m')", fontsize=12.5, weight="bold", color="#15803d", zorder=3)
    ax_det.text(0.30, 0.19, f"• Total Ties / Column:  {n_ties} Ties ({n_st_per_m} Φ{phi_st_mm}/m')", fontsize=12, color="#1e293b", zorder=3)
    ax_det.text(0.30, 0.12, f"• Total Ties Weight:  {tot_w_st_kg:.1f} kg ({tot_w_st_kg/1000.0:.3f} Ton)", fontsize=13, weight="bold", color="#047857", zorder=3)

    # ═══════════════════════════════════════════════════════════════════════
    # 3. BOTTOM SUBPLOT: DESIGN & TAKEOFF SUMMARY STRIP (FULL WIDTH)
    # ═══════════════════════════════════════════════════════════════════════
    ax_strip.set_facecolor("#ffffff")
    ax_strip.axis("off")
    ax_strip.set_xlim(0, 1)
    ax_strip.set_ylim(0, 1)

    strip_bg = FancyBboxPatch((0.005, 0.02), 0.99, 0.96, boxstyle="round,pad=0.015,rounding_size=0.025", linewidth=2.0, edgecolor="#1e3a8a", facecolor="#fffdf5", zorder=1)
    ax_strip.add_patch(strip_bg)

    ribbon = FancyBboxPatch((0.015, 0.77), 0.97, 0.19, boxstyle="round,pad=0.01,rounding_size=0.015", linewidth=1.2, edgecolor="#1e3a8a", facecolor="#1e3a8a", zorder=2)
    ax_strip.add_patch(ribbon)
    ax_strip.text(0.50, 0.865, "DESIGN & QUANTITIES TAKE-OFF SUMMARY STRIP", ha="center", va="center", fontsize=13.5, weight="bold", color="#ffffff", zorder=3)

    cols_data = [
        {
            "title": "1. Section & Geometry",
            "bg": "#f8fafc",
            "border": "#cbd5e1",
            "tcolor": "#0f172a",
            "lines": [
                f"Section: {b_disp} × {t_disp} cm",
                f"Height: H = {int(H_clear)} cm",
                f"Status: {slender_str.split('(')[0].strip()}",
            ]
        },
        {
            "title": "2. Concrete & Materials",
            "bg": "#f0fdf4",
            "border": "#86efac",
            "tcolor": "#15803d",
            "lines": [
                f"Concrete: {vol_conc_m3:.2f} m³",
                f"Cement: {cement_kg/1000.0:.2f} t ({cement_bags} bags)",
                f"Gravel: {gravel_m3:.2f}m³ | Sand: {sand_m3:.2f}m³",
            ]
        },
        {
            "title": "3. Main Rebar (BBS)",
            "bg": "#fee2e2",
            "border": "#fca5a5",
            "tcolor": "#991b1b",
            "lines": [
                f"Pattern: {n_bars} Φ {phi_mm} ({ny} rows)",
                f"Cut: {L_bar_m:.2f} m' (Ld={L_splice_cm:.0f}cm)",
                f"Weight: {tot_w_main_kg:.1f} kg ({tot_w_main_kg/1000.0:.3f}t)",
            ]
        },
        {
            "title": "4. Stirrup Ties (BBS)",
            "bg": "#dcfce7",
            "border": "#86efac",
            "tcolor": "#166534",
            "lines": [
                f"Type: {'Auto 4-Branch' if is_auto_tie else 'Closed Tie'}",
                f"Cut: {L_tie_cm:.1f} cm ({n_ties} ties)",
                f"Weight: {tot_w_st_kg:.1f} kg ({tot_w_st_kg/1000.0:.3f}t)",
            ]
        },
        {
            "title": "5. Total Steel & Capacity",
            "bg": "#f5f3ff",
            "border": "#c4b5fd",
            "tcolor": "#6d28d9",
            "lines": [
                f"Grand Steel: {tot_steel_kg:.1f} kg ({tot_steel_kg/1000.0:.3f}t)",
                f"Steel Ratio: {steel_ratio:.1f} kg/m³",
                f"Pu: {Pu:.1f}t / Cap: {pu_cap:.1f}t ({Pu/pu_cap*100:.1f}%)" if pu_cap else f"Pu = {Pu:.1f} t",
            ]
        }
    ]

    col_w = 0.186
    col_gap = 0.009
    start_x = 0.015
    box_h = 0.68
    box_y = 0.05

    for i, c in enumerate(cols_data):
        cx = start_x + i * (col_w + col_gap)
        c_box = FancyBboxPatch(
            (cx, box_y), col_w, box_h,
            boxstyle="round,pad=0.01,rounding_size=0.015",
            linewidth=1.4, edgecolor=c["border"], facecolor=c["bg"], zorder=2,
        )
        ax_strip.add_patch(c_box)

        # Title
        ax_strip.text(
            cx + col_w / 2.0, box_y + box_h - 0.12,
            c["title"], ha="center", va="center",
            fontsize=11.5, weight="bold", color=c["tcolor"], zorder=3
        )
        # Line divider inside box
        ax_strip.plot([cx + 0.01, cx + col_w - 0.01], [box_y + box_h - 0.22, box_y + box_h - 0.22], color=c["border"], lw=1.2, zorder=3)

        # Lines
        y_text = box_y + box_h - 0.35
        for line in c["lines"]:
            ax_strip.text(
                cx + col_w / 2.0, y_text,
                line, ha="center", va="center",
                fontsize=10.5, weight="bold", color="#1e293b", zorder=3
            )
            y_text -= 0.16

    fig.suptitle(
        f"Structural Column Design, Rebar Detailing & Take-off Sheet (b = {b_disp} cm × t = {t_disp} cm — H = {H_m:.2f} m)",
        fontsize=16.5, weight="bold", y=0.97, color="#0f172a",
    )

    if save_path:
        plt.savefig(save_path, bbox_inches="tight", dpi=150)
    return fig


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def round_up_to_5(value: float) -> int:
    """Round up to the nearest multiple of 5 cm."""
    return int(math.ceil(value / 5.0) * 5)


def bar_area_cm2(dia_mm: int) -> float:
    """Cross-sectional area of one rebar in cm²."""
    return math.pi * (dia_mm / 10) ** 2 / 4  # mm -> cm


def design_rectangular_column(
    Pu_input: float,
    Safety_Factor: float = 1.20,
    b: float = 30.0,
    H_clear: float = 300.0,
    K: float = 0.70,
    Fcu: float = 250.0,
    Fy: float = 4000.0,
    Fyk: float = 2400.0,
    mu_target: float = 1.0,
    Phi: int = 16,
    Phi_st: int = 8,
) -> dict:
    """
    Core design engine for a rectangular reinforced concrete column under axial load (ECP 203).
    Returns a dictionary of all design parameters, reinforcement detailing, and safety checks.
    """
    mu = mu_target / 100.0

    # Design load
    Pu_ton = Pu_input * Safety_Factor
    Pu_design = Pu_ton * 1000.0  # kg

    # Slenderness check (about shorter axis b)
    Le = K * H_clear  # cm (effective length)
    lambda_b = Le / b if b > 0 else 0.0

    if lambda_b <= 10:
        slender_class = "Short Column  (λb ≤ 10)"
        slender_ok = True
    elif lambda_b <= 15:
        slender_class = "Short Column  (10 < λb ≤ 15)"
        slender_ok = True
    else:
        slender_class = "⚠️  Long (Slender) Column  (λb > 15) – Magnification required"
        slender_ok = False

    # Required gross area (ECP 203 Eq.)
    coeff = 0.35 * Fcu * (1.0 - mu) + 0.67 * Fy * mu
    Ag_req = Pu_design / coeff if coeff > 0 else 0.0  # cm²

    # Required depth t and Column Depth Constraint (t >= b)
    t_req = Ag_req / b if b > 0 else 0.0
    t_override_applied = False

    if t_req < b:
        t_calc = float(b)
        t_override_applied = True
    else:
        t_calc = t_req

    t_design = round_up_to_5(t_calc)
    if t_design < b:
        t_design = round_up_to_5(b)
        t_override_applied = True

    # Actual gross area
    Ag = b * t_design  # cm²

    # Slenderness about longer axis t
    lambda_t = Le / t_design if t_design > 0 else 0.0

    # Actual concrete & steel areas
    Asc_min = max(0.008 * Ag, 4.0 * bar_area_cm2(Phi))  # ECP min 0.8%
    Asc_max = 0.06 * Ag                                  # ECP max 6%
    Asc_req = mu * Ag                                    # from target ratio

    Asc_use = max(Asc_req, Asc_min)

    # Number of bars (symmetric, min 4, even)
    n_bars_raw = Asc_use / bar_area_cm2(Phi) if bar_area_cm2(Phi) > 0 else 4
    n_bars = max(4, int(math.ceil(n_bars_raw)))
    if n_bars % 2 != 0:
        n_bars += 1

    Asc_provided = n_bars * bar_area_cm2(Phi)
    mu_provided = (Asc_provided / Ag) * 100.0 if Ag > 0 else 0.0  # %

    # Axial capacity check
    Ac = Ag - Asc_provided
    Pu_cap = 0.35 * Fcu * Ac + 0.67 * Fy * Asc_provided  # kg
    Pu_cap_t = Pu_cap / 1000.0                           # ton

    # Stirrup spacing (ECP 203)
    S_calc = min(15.0 * Phi / 10.0, b, t_design, 20.0)   # cm
    n_st_per_m = max(5, math.ceil(100.0 / S_calc)) if S_calc > 0 else 5

    util = (Pu_design / Pu_cap * 100.0) if Pu_cap > 0 else 0.0
    is_safe = util <= 100.0 and slender_ok

    return {
        "Pu_input": Pu_input,
        "Safety_Factor": Safety_Factor,
        "Pu_ton": Pu_ton,
        "Pu_design_kg": Pu_design,
        "b": b,
        "t": t_design,
        "t_req": t_req,
        "t_override_applied": t_override_applied,
        "Ag": Ag,
        "Ag_req": Ag_req,
        "Asc_req": Asc_req,
        "Asc_min": Asc_min,
        "Asc_use": Asc_use,
        "mu": mu,
        "Le": Le,
        "lambda_b": lambda_b,
        "lambda_t": lambda_t,
        "slender_class": slender_class,
        "slender_ok": slender_ok,
        "Phi": Phi,
        "n_bars": n_bars,
        "main_steel_str": f"{n_bars} Φ {Phi}",
        "Asc_provided": Asc_provided,
        "mu_provided": mu_provided,
        "Phi_st": Phi_st,
        "n_st_per_m": n_st_per_m,
        "stirrups_str": f"{n_st_per_m} Φ {Phi_st} / m'",
        "S_calc": S_calc,
        "Pu_cap_t": Pu_cap_t,
        "util_percent": util,
        "is_safe": is_safe,
    }


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render():
    st.markdown('<div class="section-header">🏛️ Module 2 – Rectangular Column Design (ECP 203) (تصميم الأعمدة المستطيلة)</div>',
                unsafe_allow_html=True)

    # ── INPUT FORM ──────────────────────────────────────────────────────────
    with st.expander("📝 Design Inputs (مدخلات التصميم والأبعاد والأحمال)", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**🔩 Loads & Safety**")
            Pu_input      = S.number_input("Axial Load  Pu  (ton)",       "col_Pu_input",      min_value=None, step=5.0)
            Safety_Factor = S.number_input("Safety Factor",                "col_Safety_Factor", min_value=None, step=0.05)
            if Pu_input is not None and Safety_Factor is not None and Pu_input > 0 and Safety_Factor > 0:
                st.caption(f"Design Load = {Pu_input:.1f} × {Safety_Factor:.2f} = **{Pu_input*Safety_Factor:.2f} ton**")

        with col2:
            st.markdown("**📐 Section Geometry**")
            b       = S.number_input("Column Width  b  (cm)",        "col_b",       min_value=None, step=5)
            H_clear = S.number_input("Clear Height  H_clear  (cm)",  "col_H_clear", min_value=None, step=10)
            K_opts  = [0.50, 0.70, 1.00, 1.20, 2.00]
            K       = S.selectbox(
                "Fixity Condition  K",
                "col_K_index",
                options=K_opts,
                format_func=lambda x: {
                    0.50: "0.50 – Fixed-Fixed (theoretical)",
                    0.70: "0.70 – Fixed-Fixed (practical)",
                    1.00: "1.00 – Pin-Fixed",
                    1.20: "1.20 – Pin-Pin (ECP practical)",
                    2.00: "2.00 – Cantilever",
                }.get(x, str(x)),
            )

        with col3:
            st.markdown("**🧱 Material Properties**")
            Fcu       = S.number_input("Concrete Strength  Fcu  (kg/cm²)",       "col_Fcu",       min_value=None, step=25)
            Fy        = S.number_input("Main Steel  Fy  (kg/cm²)",               "col_Fy",        min_value=None, step=200)
            Fyk       = S.number_input("Stirrup Steel  Fyk  (kg/cm²)",           "col_Fyk",       min_value=None, step=200)
            mu_target = S.number_input("Target Steel Ratio  μ  (%)",             "col_mu_target", min_value=None, step=0.1)
            Phi       = S.selectbox("Main Bar Diameter  Φ  (mm)",    "col_Phi_index",    options=[12, 16, 18, 20, 25])
            Phi_st    = S.selectbox("Stirrup Diameter  Φst  (mm)",   "col_Phi_st_index", options=[6, 8, 10])

    # ── ILLOGICAL INPUT SCREENING & WARNING ALERTS ───────────────────────────
    invalid_inputs = []

    if Pu_input is None or Pu_input <= 0:
        invalid_inputs.append(f"Axial Load Pu must be greater than zero (got {Pu_input}).")
    if Safety_Factor is None or Safety_Factor <= 0:
        invalid_inputs.append(f"Safety Factor must be greater than zero (got {Safety_Factor}).")
    if b is None or b <= 0:
        invalid_inputs.append(f"Column Width b must be greater than zero (got {b}).")
    if H_clear is None or H_clear <= 0:
        invalid_inputs.append(f"Clear Height H_clear must be greater than zero (got {H_clear}).")
    if Fcu is None or Fcu <= 0:
        invalid_inputs.append(f"Concrete Strength Fcu must be greater than zero (got {Fcu}).")
    if Fy is None or Fy <= 0:
        invalid_inputs.append(f"Main Steel Fy must be greater than zero (got {Fy}).")
    if Fyk is None or Fyk <= 0:
        invalid_inputs.append(f"Stirrup Steel Fyk must be greater than zero (got {Fyk}).")
    if mu_target is None or mu_target <= 0:
        invalid_inputs.append(f"Target Steel Ratio μ must be greater than zero (got {mu_target}).")

    if Fy is not None and Fcu is not None and Fy <= Fcu:
        invalid_inputs.append(
            f"Unrealistic material strength ratio: Main steel yield strength Fy ({Fy} kg/cm²) must be greater than concrete compressive strength Fcu ({Fcu} kg/cm²)."
        )

    if invalid_inputs:
        st.error("⚠️ **Illogical Input Detected! Calculation Stopped.**")
        for err in invalid_inputs:
            st.warning(f"• {err}")
        return

    # ── CALCULATION ENGINE ──────────────────────────────────────────────────
    res = design_rectangular_column(
        Pu_input=Pu_input,
        Safety_Factor=Safety_Factor,
        b=b,
        H_clear=H_clear,
        K=K,
        Fcu=Fcu,
        Fy=Fy,
        Fyk=Fyk,
        mu_target=mu_target,
        Phi=Phi,
        Phi_st=Phi_st,
    )

    Pu_ton = res["Pu_ton"]
    Pu_design = res["Pu_design_kg"]
    t_design = res["t"]
    t_req = res["t_req"]
    t_override_applied = res["t_override_applied"]
    Ag = res["Ag"]
    Ag_req = res.get("Ag_req", Ag)
    Le = res["Le"]
    lambda_b = res["lambda_b"]
    slender_class = res["slender_class"]
    slender_ok = res["slender_ok"]
    Asc_req = res.get("Asc_req", 0.0)
    Asc_min = res.get("Asc_min", 0.0)
    Asc_use = res.get("Asc_use", 0.0)
    Asc_provided = res["Asc_provided"]
    n_bars = res["n_bars"]
    mu_provided = res["mu_provided"]
    mu = res.get("mu", (mu_target / 100.0) if mu_target else 0.01)
    n_st_per_m = res["n_st_per_m"]
    S_calc = res["S_calc"]
    Pu_cap_t = res["Pu_cap_t"]
    util = res["util_percent"]

    # ── OUTPUTS ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Design Results & Structural Checks (نتائج التصميم والفحص الإنشائي)</div>', unsafe_allow_html=True)

    if t_override_applied:
        st.info(
            f"ℹ️ **Column Depth Constraint Applied (t ≥ b):** Calculated required depth t_req ({t_req:.2f} cm) was less than input width b ({b} cm). "
            f"Depth automatically overridden to t = {t_design} cm (rounded to nearest 5 cm increment)."
        )

    # Slenderness banner
    banner_cls = "result-ok" if slender_ok else "result-warn"
    st.markdown(
        f'<div class="{banner_cls}">Slenderness Check: λb = {lambda_b:.2f} → {slender_class}</div>',
        unsafe_allow_html=True,
    )

    # Capacity banner
    cap_cls = "result-ok" if util <= 100 else "result-fail"
    st.markdown(
        f'<div class="{cap_cls}">Capacity Check: Pu_design = {Pu_ton:.1f} ton | Pu_capacity = {Pu_cap_t:.1f} ton | Utilisation = {util:.1f}%</div>',
        unsafe_allow_html=True,
    )

    # Summary metric cards
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Design Load",        f"{Pu_ton:.1f} ton")
    c2.metric("Section (b × t)",    f"{b} × {t_design} cm")
    c3.metric("Main Steel",         f"{n_bars} Φ {Phi} mm")
    c4.metric("Steel Ratio μ",      f"{mu_provided:.2f} %")
    c5.metric("Stirrups",           f"{n_st_per_m} Φ {Phi_st}/m")

    st.markdown("---")

    # ── STRUCTURAL DRAWING & REINFORCEMENT DETAILING ────────────────────────
    st.markdown('<div class="section-header">🏛️ Column Section Design Sheet (لوحة قطاع وتسليح العمود)</div>', unsafe_allow_html=True)

    main_steel_str = f"{n_bars} Φ {Phi}"
    stirrups_str   = f"{n_st_per_m} Φ {Phi_st} / m'"

    fig = draw_rectangular_column_output(
        b=b,
        t=t_design,
        main_steel_str=main_steel_str,
        stirrups_str=stirrups_str,
        Pu=Pu_ton,
        fcu=Fcu,
        fy=Fy,
        mu_percent=mu_provided,
        n_bars=n_bars,
        phi_mm=Phi,
        phi_st_mm=Phi_st,
        n_st_per_m=n_st_per_m,
        s_calc=S_calc,
        pu_cap=Pu_cap_t,
        cover=2.5,
        slender_str=slender_class,
        H_clear=H_clear,
    )
    st.pyplot(fig, use_container_width=True)

    # Download button for high-res drawing sheet
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=300)
    buf.seek(0)
    img_col_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    buf.seek(0)
    prefix = S.get_safe_profile_filename_prefix()
    st.download_button(
        label="📥 Download Column Structural Drawing Sheet (High-Res PNG)",
        data=buf,
        file_name=f"{prefix}Column_Section_{b}x{t_design}cm.png",
        mime="image/png",
        use_container_width=True,
    )
    plt.close(fig)

    # ── 📊 BAR BENDING SCHEDULE & QUANTITIES TAKE-OFF (حصر وتفريد حديد ومواد العمود) ──
    H_m_col = H_clear / 100.0
    L_splice_m_col = max(1.0, (50.0 * Phi) / 1000.0)
    L_splice_cm_col = L_splice_m_col * 100.0
    L_bar_m_col = H_m_col + L_splice_m_col
    unit_w_main_col = (Phi ** 2) / 162.0
    tot_len_main_m_col = n_bars * L_bar_m_col
    tot_w_main_kg_col = tot_len_main_m_col * unit_w_main_col

    # Rebar grid calculation
    offset_x_col = 2.5 + (Phi / 10.0) / 2.0
    offset_y_col = 2.5 + (Phi / 10.0) / 2.0
    w_rebar_col = max(b - 2 * offset_x_col, 1.0)
    h_rebar_col = max(t_design - 2 * offset_y_col, 1.0)
    if n_bars <= 4:
        nx_col, ny_col = 2, 2
    else:
        perimeter_rebar_col = 2 * (w_rebar_col + h_rebar_col)
        s_target_col = perimeter_rebar_col / n_bars
        nx_est_col = int(round(w_rebar_col / s_target_col)) + 1
        nx_col = max(2, min(nx_est_col, n_bars // 2))
        ny_col = (n_bars // 2 + 2) - nx_col
        if ny_col < 2:
            ny_col = 2
            nx_col = (n_bars // 2 + 2) - ny_col

    xs_b_col = np.linspace(offset_x_col, b - offset_x_col, nx_col)
    ys_d_col = np.linspace(offset_y_col, t_design - offset_y_col, ny_col)

    is_auto_tie_col = (ny_col > 3) or (nx_col > 3)

    b_core_col = max(b - 2 * 2.5, 1.0)
    t_core_col = max(t_design - 2 * 2.5, 1.0)
    hook_len_cm_col = max(8.0, 10.0 * (Phi_st / 10.0))

    if is_auto_tie_col:
        if ny_col >= 4 and nx_col == 2:
            t_core_in_col = max(float(ys_d_col[-2] - ys_d_col[1]) + (Phi / 10.0), 5.0)
            b_core_in_col = b_core_col
            L_tie_cm_col = 2.0 * (b_core_col + t_core_col) + 2.0 * (b_core_in_col + t_core_in_col) + 4.0 * hook_len_cm_col
            tie_item_name = "2. كانات العمود الأوتوماتيك (Automatic 4-Branch Ties)"
            tie_desc_str = f"{L_tie_cm_col/100.0:.2f} m' (كانة خارجية {2*(b_core_col+t_core_col):.0f}cm + داخلية {2*(b_core_in_col+t_core_in_col):.0f}cm + 4 أقفال {4*hook_len_cm_col:.0f}cm)"
        elif nx_col >= 3 and ny_col >= 3:
            b_core_in_col = max(float(xs_b_col[-2] - xs_b_col[1]) + (Phi / 10.0), 5.0)
            t_core_in_col = max(float(ys_d_col[-2] - ys_d_col[1]) + (Phi / 10.0), 5.0)
            L_tie_cm_col = 2.0 * (b_core_col + t_core_col) + 2.0 * (b_core_in_col + t_core_in_col) + 4.0 * hook_len_cm_col
            tie_item_name = "2. كانات العمود الأوتوماتيك (Automatic Multi-Branch Ties)"
            tie_desc_str = f"{L_tie_cm_col/100.0:.2f} m' (خارجية {2*(b_core_col+t_core_col):.0f}cm + داخلية {2*(b_core_in_col+t_core_in_col):.0f}cm + 4 أقفال {4*hook_len_cm_col:.0f}cm)"
        else:
            t_core_in_col = t_core_col * 0.5
            b_core_in_col = b_core_col
            L_tie_cm_col = 2.0 * (b_core_col + t_core_col) + 2.0 * (b_core_in_col + t_core_in_col) + 4.0 * hook_len_cm_col
            tie_item_name = "2. كانات العمود الأوتوماتيك (Automatic 4-Branch Ties)"
            tie_desc_str = f"{L_tie_cm_col/100.0:.2f} m' (خارجية وداخلية + 4 أقفال {4*hook_len_cm_col:.0f}cm)"
    else:
        L_tie_cm_col = 2.0 * (b_core_col + t_core_col) + 2.0 * hook_len_cm_col
        tie_item_name = "2. كانات العمود المستطيلة (Closed Box Ties)"
        tie_desc_str = f"{L_tie_cm_col/100.0:.2f} m' (محيط {2*(b_core_col+t_core_col):.0f}cm + قفلين {2*hook_len_cm_col:.0f}cm)"

    L_tie_m_col = L_tie_cm_col / 100.0
    n_ties_col = max(5, int(math.ceil(H_m_col * n_st_per_m)))
    unit_w_st_col = (Phi_st ** 2) / 162.0
    tot_len_st_m_col = n_ties_col * L_tie_m_col
    tot_w_st_kg_col = tot_len_st_m_col * unit_w_st_col

    tot_steel_kg_col = tot_w_main_kg_col + tot_w_st_kg_col
    vol_conc_m3_col = (b / 100.0) * (t_design / 100.0) * H_m_col
    steel_ratio_col = (tot_steel_kg_col / vol_conc_m3_col) if vol_conc_m3_col > 0 else 0.0

    cement_ton_col = vol_conc_m3_col * 0.350
    cement_bags_col = int(round(vol_conc_m3_col * 7.0))
    gravel_m3_col = vol_conc_m3_col * 0.80
    sand_m3_col = vol_conc_m3_col * 0.40

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)
    with st.expander("📊 Bar Bending Schedule & BOQ Take-off (جدول حصر وتفريد حديد ومواد العمود)", expanded=True):
        bbs_rows = [
            {
                "بند التسليح (Item)": "1. حديد التسليح الطولي الرئيسي (Main Rebar)",
                "القطر Φ": f"Φ {Phi} mm",
                "العدد (Count)": f"{n_bars} أسياخ ({ny_col} صفوف)",
                "طول القطع للسيخ (m)": f"{L_bar_m_col:.2f} m' (ارتفاع {H_clear:.0f}cm + إشارة {L_splice_cm_col:.0f}cm)",
                "إجمالي الأطوال (m')": f"{tot_len_main_m_col:,.1f} m'",
                "وزن المتر (kg/m')": f"{unit_w_main_col:.3f}",
                "إجمالي الوزن (kg)": f"{tot_w_main_kg_col:,.1f} kg",
                "إجمالي الوزن (Ton)": f"{tot_w_main_kg_col/1000.0:.3f} Ton",
            },
            {
                "بند التسليح (Item)": tie_item_name,
                "القطر Φ": f"Φ {Phi_st} mm",
                "العدد (Count)": f"{n_ties_col} كانة ({n_st_per_m}/m')",
                "طول القطع للسيخ (m)": tie_desc_str,
                "إجمالي الأطوال (m')": f"{tot_len_st_m_col:,.1f} m'",
                "وزن المتر (kg/m')": f"{unit_w_st_col:.3f}",
                "إجمالي الوزن (kg)": f"{tot_w_st_kg_col:,.1f} kg",
                "إجمالي الوزن (Ton)": f"{tot_w_st_kg_col/1000.0:.3f} Ton",
            },
            {
                "بند التسليح (Item)": "📌 الإجمالي الكلي لحديد تسليح العمود (Grand Total Steel)",
                "القطر Φ": "—",
                "العدد (Count)": f"{n_bars} أسياخ + {n_ties_col} كانة",
                "طول القطع للسيخ (m)": f"معدل الاستهلاك: {steel_ratio_col:.1f} kg/m³",
                "إجمالي الأطوال (m')": f"{tot_len_main_m_col + tot_len_st_m_col:,.1f} m'",
                "وزن المتر (kg/m')": "—",
                "إجمالي الوزن (kg)": f"{tot_steel_kg_col:,.1f} kg",
                "إجمالي الوزن (Ton)": f"{tot_steel_kg_col/1000.0:.3f} Ton",
            },
        ]
        st.dataframe(pd.DataFrame(bbs_rows), use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
        cm1, cm2, cm3, cm4 = st.columns(4)
        with cm1:
            st.markdown(
                f"""
                <div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:8px; padding:8px 12px; text-align:center;">
                    <div style="font-size:13px; font-weight:600; color:#15803d;">حجم خرسانة العمود</div>
                    <div style="font-size:18px; font-weight:700; color:#166534;">{vol_conc_m3_col:.2f} m³</div>
                    <div style="font-size:11.5px; color:#64748b;">{b:.0f}×{t_design:.0f} cm × H {H_clear:.0f} cm</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cm2:
            st.markdown(
                f"""
                <div style="background:#eff6ff; border:1.5px solid #93c5fd; border-radius:8px; padding:8px 12px; text-align:center;">
                    <div style="font-size:13px; font-weight:600; color:#1e40af;">كمية الأسمنت للعمود</div>
                    <div style="font-size:18px; font-weight:700; color:#1e3a8a;">{cement_ton_col:.2f} Ton</div>
                    <div style="font-size:11.5px; color:#64748b;">{cement_bags_col} شكارة (350 kg/m³)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cm3:
            st.markdown(
                f"""
                <div style="background:#fffbeb; border:1.5px solid #fde68a; border-radius:8px; padding:8px 12px; text-align:center;">
                    <div style="font-size:13px; font-weight:600; color:#b45309;">حجم الزلط والرمل</div>
                    <div style="font-size:18px; font-weight:700; color:#92400e;">{gravel_m3_col:.2f} m³ | {sand_m3_col:.2f} m³</div>
                    <div style="font-size:11.5px; color:#64748b;">زلط (0.80) / رمل (0.40) لكل م³</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cm4:
            st.markdown(
                f"""
                <div style="background:#f5f3ff; border:1.5px solid #c4b5fd; border-radius:8px; padding:8px 12px; text-align:center;">
                    <div style="font-size:13px; font-weight:600; color:#6d28d9;">معدل التسليح للعمود</div>
                    <div style="font-size:18px; font-weight:700; color:#5b21b6;">{steel_ratio_col:.1f} kg/m³</div>
                    <div style="font-size:11.5px; color:#64748b;">إجمالي الحديد: {tot_steel_kg_col:.1f} kg</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # Full calculation table
    st.markdown('<div class="section-header">📋 Detailed Calculation Sheet (جدول الحسابات التفصيلية الكاملة)</div>', unsafe_allow_html=True)

    table_data = {
        "Parameter": [
            "Input Load  Pu_input",
            "Safety Factor",
            "Design Load  Pu_design",
            "Column Width  b",
            "Effective Length  Le = K × H",
            "Slenderness Ratio  λb = Le / b",
            "Slenderness Class",
            "Concrete  Fcu",
            "Main Steel  Fy",
            "Stirrup Steel  Fyk",
            "Target Steel Ratio  μ",
            "Required Gross Area  Ag_req",
            "Required Depth  t_req",
            "Adopted Depth  t_design",
            "Actual Gross Area  Ag",
            "Required Steel Area  Asc_req",
            "Min. Steel Area  Asc_min (0.8%)",
            "Design Steel Area  Asc_use",
            "Main Bar Diameter  Φ",
            "No. of Bars  n",
            "Provided Steel Area  Asc",
            "Provided Steel Ratio  μ_provided",
            "Axial Capacity  Pu_cap",
            "Utilisation Ratio",
            "Stirrup Spacing  S",
            "Stirrups per Meter",
        ],
        "Value": [
            f"{Pu_input:.1f} ton",
            f"{Safety_Factor:.2f}",
            f"{Pu_ton:.2f} ton  ({Pu_design:,.0f} kg)",
            f"{b} cm",
            f"{Le:.1f} cm",
            f"{lambda_b:.2f}",
            slender_class,
            f"{Fcu} kg/cm²",
            f"{Fy} kg/cm²",
            f"{Fyk} kg/cm²",
            f"{mu*100:.2f} %",
            f"{Ag_req:.2f} cm²",
            f"{t_req:.2f} cm" + (" (Overridden: t_req < b)" if t_req < b else ""),
            f"{t_design} cm",
            f"{Ag:.2f} cm²",
            f"{Asc_req:.2f} cm²",
            f"{Asc_min:.2f} cm²",
            f"{Asc_use:.2f} cm²",
            f"Φ {Phi} mm  (area = {bar_area_cm2(Phi):.3f} cm²/bar)",
            f"{n_bars} bars (symmetric)",
            f"{Asc_provided:.3f} cm²",
            f"{mu_provided:.3f} %",
            f"{Pu_cap_t:.2f} ton",
            f"{util:.2f} %",
            f"{S_calc:.1f} cm",
            f"{n_st_per_m} Φ {Phi_st}/m",
        ],
        "Reference": [
            "User input",
            "User input",
            "Pu_input × SF",
            "User input",
            "ECP 6.7.1",
            "ECP 6.7.1",
            "ECP 6.7.1",
            "Material",
            "Material",
            "Material",
            "User input",
            "ECP 6.3.1",
            "Ag_req / b",
            "Constraint: t ≥ b, step 5cm",
            "b × t_design",
            "μ × Ag",
            "ECP 6.5.1 (min 0.8%)",
            "max(Asc_req, Asc_min)",
            "User selection",
            "ceil, min 4, even",
            "n × A_bar",
            "Asc/Ag",
            "ECP 6.3.1",
            "Pu_design/Pu_cap",
            "ECP 6.7.4",
            "min 5/m",
        ],
    }

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── 💾 SAVE & EXPORT COMPLETE CALCULATION SHEET ────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div class="section-header">💾 Save & Export Design Calculation Sheet (حفظ وتصدير المذكرة الحسابية الكاملة)</div>',
        unsafe_allow_html=True,
    )

    from modules.report_generator import generate_column_report_html, html_to_pdf_bytes

    col_report_html = generate_column_report_html(
        project_name="Rectangular Column Design (ECP 203)",
        b=b,
        t=t_design,
        H=H_clear,
        Pu=Pu_ton,
        fcu=Fcu,
        fy=Fy,
        main_steel_str=f"{n_bars} Φ {Phi} mm ({Asc_provided:.2f} cm²)",
        stirrups_str=f"Φ {Phi_st} mm @ {S_calc:.0f} cm ({n_st_per_m}/m)",
        pu_cap=Pu_cap_t,
        slender_str=slender_class,
        img_col_b64=img_col_b64,
    )

    pdf_bytes = html_to_pdf_bytes(col_report_html)

    c_save1, c_save2 = st.columns([3, 1])
    with c_save1:
        st.markdown(
            f"""
            <div style='background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:14px 16px;'>
                <div style='font-weight:700; color:#1e293b; font-size:1.0rem;'>
                    📄 مذكرة الحسابات الإنشائية للعمود (Column Calculation Sheet)
                </div>
                <div style='font-size:0.88rem; color:#64748b; margin-top:2px;'>
                    تتضمن جميع المدخلات، ومخطط تفاصيل القطاع والتسليح، وجدول الفحص وسعة التحمل.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c_save2:
        prefix = S.get_safe_profile_filename_prefix()
        st.download_button(
            label="🌐 Save Calculation Sheet (HTML)",
            data=col_report_html,
            file_name=f"{prefix}ECP203_Column_Calculation_Sheet_{b}x{t_design}cm.html",
            mime="text/html",
            use_container_width=True,
        )
        if pdf_bytes:
            st.download_button(
                label="📕 Save as PDF (مباشر)",
                data=pdf_bytes,
                file_name=f"{prefix}ECP203_Column_Calculation_Sheet_{b}x{t_design}cm.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    # Design sketch note
    st.markdown("---")
    st.info(
        f"📐 **Design Summary:**  "
        f"Column {b} × {t_design} cm  |  "
        f"{n_bars} Φ {Phi} main bars  |  "
        f"Φ {Phi_st} stirrups @ {S_calc:.0f} cm spacing ({n_st_per_m} per meter)  |  "
        f"μ = {mu_provided:.2f}%"
    )
