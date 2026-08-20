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
    save_path: str = None,
):
    """
    Renders an engineering design output sheet for a rectangular reinforced concrete column (ECP 203).
    Creates a structural CAD-like cross-section with rebar & stirrup detailing alongside
    a comprehensive, high-contrast Design Output Summary Card.
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

    # Create Figure with 2 Subplots (Left: Cross-Section, Right: Summary Card)
    fig = plt.figure(figsize=(12, 7.2), dpi=130, facecolor="#ffffff")
    gs = fig.add_gridspec(
        1, 2, width_ratios=[1.05, 1.15], wspace=0.10, left=0.04, right=0.96, top=0.88, bottom=0.07
    )
    ax_sec = fig.add_subplot(gs[0, 0])
    ax_card = fig.add_subplot(gs[0, 1])

    # ═══════════════════════════════════════════════════════════════════════
    # 1. LEFT SUBPLOT: COLUMN CROSS-SECTION & DETAILING
    # ═══════════════════════════════════════════════════════════════════════
    ax_sec.set_facecolor("#ffffff")

    # Concrete outer rectangle
    col_rect = patches.Rectangle(
        (0, 0),
        b_val,
        t_val,
        linewidth=2.8,
        edgecolor="#0f172a",
        facecolor="#e6ecf5",
        zorder=1,
    )
    ax_sec.add_patch(col_rect)

    # Core concrete inside ties
    st_x = cover
    st_y = cover
    st_w = max(b_val - 2 * cover, 1.0)
    st_h = max(t_val - 2 * cover, 1.0)

    core_rect = patches.Rectangle(
        (st_x, st_y),
        st_w,
        st_h,
        facecolor="#f1f5f9",
        edgecolor="none",
        zorder=2,
    )
    ax_sec.add_patch(core_rect)

    # Perimeter Stirrup / Ties
    rounding = min(1.5, cover * 0.6)
    stirrup_patch = FancyBboxPatch(
        (st_x, st_y),
        st_w,
        st_h,
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        linewidth=2.4,
        edgecolor="#16a34a",  # Vivid Green
        facecolor="none",
        zorder=4,
    )
    ax_sec.add_patch(stirrup_patch)

    # Stirrup standard 135-degree corner hook (top-left)
    hook_sz = min(3.5, max(2.2, st_w * 0.15))
    ax_sec.plot(
        [st_x, st_x + hook_sz * 0.707],
        [st_y + st_h, st_y + st_h - hook_sz * 0.707],
        color="#16a34a",
        lw=2.4,
        zorder=5,
    )
    ax_sec.plot(
        [st_x + hook_sz * 0.707, st_x],
        [st_y + st_h - hook_sz * 0.707, st_y + st_h - hook_sz * 1.15],
        color="#16a34a",
        lw=2.4,
        zorder=5,
    )

    # Rebar layout calculation
    bar_radius = max(1.1, min(2.1, (phi_mm / 10.0) * 0.85))
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
        if not any(
            np.isclose(pt[0], u[0], atol=1e-2) and np.isclose(pt[1], u[1], atol=1e-2)
            for u in unique_rebars
        ):
            unique_rebars.append(pt)

    # Intermediate ties (internal ties / branch ties)
    if ny >= 4 and nx == 2:
        for y in ys_d[1:-1]:
            ax_sec.plot(
                [st_x, b_val - st_x], [y, y], color="#16a34a", lw=1.8, linestyle="--", zorder=3
            )
            ax_sec.plot([st_x, st_x + 1.2], [y, y + 0.8], color="#16a34a", lw=1.8, zorder=3)
            ax_sec.plot([b_val - st_x, b_val - st_x - 1.2], [y, y - 0.8], color="#16a34a", lw=1.8, zorder=3)
    elif nx >= 3 and ny >= 3:
        mid_x = b_val / 2.0
        mid_y = t_val / 2.0
        if len(unique_rebars) == 8:
            d_pts = [
                (mid_x, offset_y),
                (b_val - offset_x, mid_y),
                (mid_x, t_val - offset_y),
                (offset_x, mid_y),
                (mid_x, offset_y),
            ]
            dx, dy = zip(*d_pts)
            ax_sec.plot(dx, dy, color="#16a34a", lw=1.8, linestyle="--", zorder=3)

    # Draw Rebars
    for rx, ry in unique_rebars:
        rebar_circle = Circle(
            (rx, ry),
            radius=bar_radius,
            facecolor="#dc2626",  # Crimson Red
            edgecolor="#1e293b",
            linewidth=1.4,
            zorder=6,
        )
        ax_sec.add_patch(rebar_circle)

    # Dimension Lines
    dim_offset = max(6.0, min(b_val, t_val) * 0.16)

    # Width dimension (b) - Bottom
    y_dim = -dim_offset
    ax_sec.plot([0, 0], [0, y_dim - 1.2], color="#94a3b8", lw=1.1, linestyle=":", zorder=2)
    ax_sec.plot([b_val, b_val], [0, y_dim - 1.2], color="#94a3b8", lw=1.1, linestyle=":", zorder=2)
    ax_sec.annotate(
        "",
        xy=(b_val, y_dim),
        xytext=(0, y_dim),
        arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6, shrinkA=0, shrinkB=0),
    )
    ax_sec.text(
        b_val / 2.0,
        y_dim - 1.4,
        f"b = {b_disp} cm",
        ha="center",
        va="top",
        fontsize=13,
        weight="bold",
        color="#0f172a",
    )

    # Depth dimension (t) - Left
    x_dim = -dim_offset
    ax_sec.plot([0, x_dim - 1.2], [0, 0], color="#94a3b8", lw=1.1, linestyle=":", zorder=2)
    ax_sec.plot([0, x_dim - 1.2], [t_val, t_val], color="#94a3b8", lw=1.1, linestyle=":", zorder=2)
    ax_sec.annotate(
        "",
        xy=(x_dim, t_val),
        xytext=(x_dim, 0),
        arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6, shrinkA=0, shrinkB=0),
    )
    ax_sec.text(
        x_dim - 1.4,
        t_val / 2.0,
        f"t = {t_disp} cm",
        ha="right",
        va="center",
        rotation=90,
        fontsize=13,
        weight="bold",
        color="#0f172a",
    )

    # Leader Callout for Main Steel (Top Right)
    top_right_bar = (b_val - offset_x, t_val - offset_y)
    ax_sec.annotate(
        f"Main RFT: {main_steel_str}",
        xy=top_right_bar,
        xytext=(b_val * 0.45, t_val + dim_offset * 1.05),
        arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.8, connectionstyle="arc3,rad=-0.15"),
        fontsize=12,
        weight="bold",
        color="#991b1b",
        ha="left",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.38", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.4),
    )

    # Leader Callout for Stirrups (Top Left)
    top_left_stirrup = (st_x + st_w * 0.25, st_y + st_h)
    ax_sec.annotate(
        f"Stirrups: {stirrups_str}",
        xy=top_left_stirrup,
        xytext=(b_val * 0.10, t_val + dim_offset * 1.05),
        arrowprops=dict(arrowstyle="->", color="#16a34a", lw=1.8, connectionstyle="arc3,rad=0.15"),
        fontsize=11.5,
        weight="bold",
        color="#15803d",
        ha="right",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.38", facecolor="#dcfce7", edgecolor="#22c55e", lw=1.4),
    )

    # Section bounds & aspect
    pad_left = dim_offset + 12
    pad_right = max(dim_offset + 16, b_val * 0.5 + 20)
    pad_y_top = dim_offset * 1.05 + 16
    pad_y_bot = dim_offset + 8
    ax_sec.set_xlim(-pad_left, b_val + pad_right)
    ax_sec.set_ylim(-pad_y_bot, t_val + pad_y_top)
    ax_sec.set_aspect("equal", adjustable="box")
    ax_sec.axis("off")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. RIGHT SUBPLOT: DESIGN OUTPUT SUMMARY CARD
    # ═══════════════════════════════════════════════════════════════════════
    ax_card.set_facecolor("#ffffff")
    ax_card.axis("off")
    ax_card.set_xlim(0, 1)
    ax_card.set_ylim(0, 1)

    # Outer Card Box
    card_bg = FancyBboxPatch(
        (0.01, 0.01),
        0.98,
        0.98,
        boxstyle="round,pad=0.03,rounding_size=0.04",
        linewidth=2.2,
        edgecolor="#831843",  # Dark Crimson/Maroon border
        facecolor="#fffdf5",  # Warm ivory/parchment background
        zorder=1,
    )
    ax_card.add_patch(card_bg)

    # Card Title Banner
    banner = FancyBboxPatch(
        (0.03, 0.88),
        0.94,
        0.09,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=1.2,
        edgecolor="#831843",
        facecolor="#831843",
        zorder=2,
    )
    ax_card.add_patch(banner)
    ax_card.text(
        0.50,
        0.925,
        "DESIGN OUTPUTS & CAPACITY",
        ha="center",
        va="center",
        fontsize=13.5,
        weight="bold",
        color="#ffffff",
        zorder=3,
    )

    pu_cap_disp = f"{pu_cap:.1f} Tons" if pu_cap is not None else f"{Pu:.1f} Tons"
    fcu_fy_disp = f"{int(fcu_kg)} / {int(fy_kg)} kg/cm²"

    rows = [
        ("Section (b × t)", f"{b_disp} × {t_disp} cm", "#0f172a"),
        ("Main Steel (RFT)", f"{main_steel_str}", "#991b1b"),
        ("Stirrups (Ties)", f"{stirrups_str}", "#166534"),
        ("Design Load (Pu)", f"{Pu:.1f} Tons", "#b45309"),
        ("Capacity (Pu,cap)", f"{pu_cap_disp}", "#047857"),
        ("Rebar Ratio (μ)", f"{mu_percent:.2f} %", "#1d4ed8"),
        ("fcu / fy", f"{fcu_fy_disp}", "#334155"),
        ("Concrete Cover", f"{cover:.1f} cm", "#334155"),
        ("Slenderness Check", f"{slender_str.split('–')[0].strip()}", "#1e293b"),
    ]

    y_pos = 0.82
    y_step = 0.082

    for idx, (label, val, val_color) in enumerate(rows):
        if idx % 2 == 0:
            row_bg = patches.Rectangle(
                (0.035, y_pos - 0.026),
                0.93,
                y_step * 0.90,
                facecolor="#fef2f2" if idx == 1 else "#f8f9fa",
                edgecolor="none",
                zorder=2,
            )
            ax_card.add_patch(row_bg)

        # Label (Left)
        ax_card.text(
            0.06,
            y_pos + 0.010,
            label,
            ha="left",
            va="center",
            fontsize=12,
            weight="bold",
            color="#475569",
            zorder=3,
        )
        # Colon separator
        ax_card.text(
            0.48,
            y_pos + 0.010,
            ":",
            ha="center",
            va="center",
            fontsize=12,
            weight="bold",
            color="#64748b",
            zorder=3,
        )
        # Value (Right)
        ax_card.text(
            0.94,
            y_pos + 0.010,
            val,
            ha="right",
            va="center",
            fontsize=12.5,
            weight="bold",
            color=val_color,
            zorder=3,
        )
        y_pos -= y_step

    # Global Figure Title
    fig.suptitle(
        f"Column Section Design & Reinforcement Details ({b_disp} × {t_disp} cm)",
        fontsize=15,
        weight="bold",
        y=0.96,
        color="#0f172a",
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


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render():
    st.markdown('<div class="section-header">🏛️ Module 2 – Rectangular Column Design (ECP 203)</div>',
                unsafe_allow_html=True)

    # ── INPUT FORM ──────────────────────────────────────────────────────────
    with st.expander("📝 Design Inputs", expanded=True):
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
    mu = mu_target / 100.0

    # Design load
    Pu_ton    = Pu_input * Safety_Factor        # ton
    Pu_design = Pu_ton * 1000                   # kg

    # Slenderness check (about shorter axis b)
    Le       = K * H_clear                      # cm  (effective length)
    lambda_b = Le / b

    if lambda_b <= 10:
        slender_class = "Short Column  (λb ≤ 10)"
        slender_ok    = True
    elif lambda_b <= 15:
        slender_class = "Short Column  (10 < λb ≤ 15)"
        slender_ok    = True
    else:
        slender_class = "⚠️  Long (Slender) Column  (λb > 15) – Magnification required"
        slender_ok    = False

    # Required gross area (ECP 203 Eq.)
    coeff  = 0.35 * Fcu * (1 - mu) + 0.67 * Fy * mu
    Ag_req = Pu_design / coeff                  # cm²

    # Required depth t and Column Depth Constraint (t >= b)
    t_req = Ag_req / b
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
    Ag = b * t_design                           # cm²

    # Slenderness about longer axis t
    lambda_t = Le / t_design

    # Actual concrete & steel areas
    Asc_min  = max(0.008 * Ag, 4 * bar_area_cm2(Phi))   # ECP min 0.8%
    Asc_max  = 0.06 * Ag                                  # ECP max 6%
    Asc_req  = mu * Ag                                    # from target ratio

    Asc_use  = max(Asc_req, Asc_min)

    # Number of bars (symmetric, min 4, even)
    n_bars_raw = Asc_use / bar_area_cm2(Phi)
    n_bars     = max(4, int(math.ceil(n_bars_raw)))
    if n_bars % 2 != 0:
        n_bars += 1

    Asc_provided = n_bars * bar_area_cm2(Phi)
    mu_provided  = Asc_provided / Ag * 100     # %

    # Axial capacity check
    Ac        = Ag - Asc_provided
    Pu_cap    = 0.35 * Fcu * Ac + 0.67 * Fy * Asc_provided   # kg
    Pu_cap_t  = Pu_cap / 1000                                  # ton

    # Stirrup spacing (ECP 203)
    S_calc     = min(15 * Phi / 10, b, t_design, 20)   # cm
    n_st_per_m = max(5, math.ceil(100 / S_calc))

    # ── OUTPUTS ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Design Results</div>', unsafe_allow_html=True)

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
    util = Pu_design / Pu_cap * 100
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
    )
    st.pyplot(fig, use_container_width=True)

    # Download button for high-res drawing sheet
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=300)
    buf.seek(0)
    img_col_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    buf.seek(0)
    st.download_button(
        label="📥 Download Column Structural Drawing Sheet (High-Res PNG)",
        data=buf,
        file_name=f"Column_Section_{b}x{t_design}cm.png",
        mime="image/png",
        use_container_width=True,
    )
    plt.close(fig)

    st.markdown("---")

    # Full calculation table
    st.markdown('<div class="section-header">📋 Detailed Calculation Sheet</div>', unsafe_allow_html=True)

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
        st.download_button(
            label="🌐 Save Calculation Sheet (HTML)",
            data=col_report_html,
            file_name=f"ECP203_Column_Calculation_Sheet_{b}x{t_design}cm.html",
            mime="text/html",
            use_container_width=True,
        )
        if pdf_bytes:
            st.download_button(
                label="📕 Save as PDF (مباشر)",
                data=pdf_bytes,
                file_name=f"ECP203_Column_Calculation_Sheet_{b}x{t_design}cm.pdf",
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
