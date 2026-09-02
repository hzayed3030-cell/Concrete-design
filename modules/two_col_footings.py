"""
Module 7 – Combined Footing Design (Isolated or Combined)
ECP 203 – Egyptian Code of Practice for RC Structures
═══════════════════════════════════════════════════════
Units strictly in standard Metric Engineering Units:
ton · kg · cm · m · kg/cm² · ton·m
(No Newton / kN / MPa units in UI or outputs)
"""
import math
import io
import base64
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from modules import settings as S
from modules.table_styler import render_styled_table


# ═══════════════════════════════════════════════════════════════════════════════
#  UTILITY HELPERS (kg · cm · ton · m)
# ═══════════════════════════════════════════════════════════════════════════════

def _r5(v_cm):
    """Round UP to nearest 5 cm."""
    return int(math.ceil(v_cm / 5.0) * 5)


def _iso_dims(P_ton, c_cm, b_cm, q_net_kgcm2):
    """
    Initial isolated-footing dimensions (equal overhangs).
    P_ton in ton, c,b in cm, q_net in kg/cm².
    Returns (L_cm, B_cm) rounded to 5 cm.
    """
    P_kg  = P_ton * 1000.0
    A_req = 1.05 * P_kg / q_net_kgcm2           # cm²
    delta = c_cm - b_cm
    disc  = delta ** 2 + 4.0 * A_req
    B_raw = (-delta + math.sqrt(max(disc, 1))) / 2.0
    L_raw = B_raw + delta
    return _r5(max(L_raw, c_cm + 20)), _r5(max(B_raw, b_cm + 20))


def _combined_dims(P1_ton, P2_ton, c1_cm, b1_cm, c2_cm, b2_cm, S_m, q_net_kgcm2):
    """
    Initial combined-footing dimensions.
    Returns (L_cm, B_cm, x1_cm, x2_cm).
    """
    R_ton = P1_ton + P2_ton
    if R_ton <= 0:
        return 100, 100, 20, 20
    R_kg  = R_ton * 1000.0
    x_R_m = P2_ton * S_m / R_ton                # resultant distance from C1 center (m)
    A_req_cm2 = 1.05 * R_kg / q_net_kgcm2       # cm²

    ov_min_m = 0.20                             # 20 cm min overhang beyond col face
    x1_min_m = (c1_cm / 100.0) / 2.0 + ov_min_m

    L_trial_m = 2.0 * (x1_min_m + x_R_m)
    x2_trial_m = L_trial_m - x1_min_m - S_m

    if x2_trial_m < (c2_cm / 100.0) / 2.0 + ov_min_m:
        x1_min_m = max(x1_min_m, (c2_cm / 100.0) / 2.0 + ov_min_m + S_m - 2.0 * x_R_m)
        L_trial_m = 2.0 * (x1_min_m + x_R_m)

    L_cm  = _r5(L_trial_m * 100.0)
    L_m   = L_cm / 100.0
    x1_m  = L_m / 2.0 - x_R_m
    x2_m  = L_m - x1_m - S_m

    if x1_m < 0:
        x1_m = (c1_cm / 100.0) / 2.0 + 0.10
        L_cm = _r5((x1_m + S_m + (c2_cm / 100.0) / 2.0 + 0.10) * 100.0)
        L_m  = L_cm / 100.0
        x2_m = L_m - x1_m - S_m

    B_raw_cm = A_req_cm2 / L_cm
    B_cm  = _r5(max(B_raw_cm, max(b1_cm, b2_cm) + 20))
    return L_cm, B_cm, round(x1_m * 100, 1), round(x2_m * 100, 1)


def _shear_allow_kgcm2(Fcu):
    """One-way shear allowable stress in kg/cm² (ECP 203)."""
    return 0.16 * math.sqrt(Fcu)


def _punch_allow_kgcm2(Fcu, c_cm, b_cm, d_cm, bo_cm):
    """Punching shear allowable stress in kg/cm² (ECP 203 — min of 4 criteria)."""
    sq = math.sqrt(Fcu)
    a_col = min(c_cm, b_cm)
    b_col = max(c_cm, b_cm)
    ratio = a_col / b_col if b_col > 0 else 1.0

    q1 = 0.316 * (0.50 + ratio) * sq
    alpha = 4.0                                 # interior column
    q2 = 0.8 * (alpha * d_cm / bo_cm + 0.2) * sq if bo_cm > 0 else 999.0
    q3 = 0.316 * sq
    q4 = 17.0                                   # kg/cm² hard cap (1.7 MPa)

    return min(q1, q2, q3, q4)


def _As_design_cm2(Mu_kgcm, d_cm, b_cm, Fcu, Fy):
    """
    Required steel area (cm²) by Whitney stress block.
    Mu in kg·cm, d in cm, b in cm, Fcu in kg/cm², Fy in kg/cm².
    """
    if Mu_kgcm <= 0 or d_cm <= 0 or b_cm <= 0:
        return 0.0015 * b_cm * d_cm             # minimum 0.15%

    a = 0.10 * d_cm
    for _ in range(30):
        lever = d_cm - a / 2.0
        if lever <= 0:
            lever = 0.50 * d_cm
        As = Mu_kgcm / (0.9 * Fy * lever)
        a  = (As * Fy) / (0.85 * Fcu * b_cm) if (Fcu * b_cm) > 0 else 0
    As_min = 0.0015 * b_cm * d_cm
    return max(As, As_min)


# ═══════════════════════════════════════════════════════════════════════════════
#  DIMENSION-LINE HELPERS (matplotlib)
# ═══════════════════════════════════════════════════════════════════════════════

_DIM_COLOR   = "#334155"
_DIM_FS      = 13
_ARROW_STYLE = dict(arrowstyle="<->", color="#334155", lw=1.8)


def _hdim(ax, y, x1, x2, label, side="top", fs=_DIM_FS, offset=0.12):
    """Horizontal dimension line with ticks."""
    ym = y + offset if side == "top" else y - offset
    ax.annotate("", xy=(x1, ym), xytext=(x2, ym), arrowprops=_ARROW_STYLE)
    ax.plot([x1, x1], [y, ym], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.plot([x2, x2], [y, ym], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.text((x1 + x2) / 2, ym + 0.06 * (1 if side == "top" else -1),
            label, ha="center", va="bottom" if side == "top" else "top",
            fontsize=fs, fontweight="bold", color=_DIM_COLOR)


def _vdim(ax, x, y1, y2, label, side="right", fs=_DIM_FS, offset=0.12):
    """Vertical dimension line with ticks."""
    xm = x + offset if side == "right" else x - offset
    ax.annotate("", xy=(xm, y1), xytext=(xm, y2), arrowprops=_ARROW_STYLE)
    ax.plot([x, xm], [y1, y1], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.plot([x, xm], [y2, y2], color=_DIM_COLOR, lw=1.0, ls="--", alpha=0.6)
    ax.text(xm + 0.06 * (1 if side == "right" else -1), (y1 + y2) / 2,
            label, ha="left" if side == "right" else "right",
            va="center", fontsize=fs, fontweight="bold", color=_DIM_COLOR,
            rotation=90)


# ═══════════════════════════════════════════════════════════════════════════════
#  PLAN SKETCH (Geometry-only or with Reinforcement callouts)
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_plan(mode, *,
               S_m, c1_cm, b1_cm, c2_cm, b2_cm,
               L1_cm=0, B1_cm=0, L2_cm=0, B2_cm=0,
               Lc_cm=0, Bc_cm=0, x1_cm=0, x2_cm=0,
               rft=None):
    """
    Render plan-view sketch.
    mode: 'isolated' or 'combined'
    rft: dict with reinforcement callout strings (if any).
    Returns matplotlib Figure.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]

    fig, ax = plt.subplots(figsize=(20, 13), dpi=150, facecolor="#ffffff")
    ax.set_facecolor("#ffffff")

    c1_m = c1_cm / 100.0;  b1_m = b1_cm / 100.0
    c2_m = c2_cm / 100.0;  b2_m = b2_cm / 100.0

    if mode == "isolated":
        L1_m = L1_cm / 100.0; B1_m = B1_cm / 100.0
        L2_m = L2_cm / 100.0; B2_m = B2_cm / 100.0

        # Footing 1 centred on C1 at origin
        f1_x = -L1_m / 2.0; f1_y = -B1_m / 2.0
        # Footing 2 centred on C2 at (S_m, 0)
        f2_x = S_m - L2_m / 2.0; f2_y = -B2_m / 2.0

        # ── Draw footings ──
        ax.add_patch(patches.Rectangle((f1_x, f1_y), L1_m, B1_m, lw=3.5,
                     ec="#0f172a", fc="#e0f2fe", alpha=0.88, zorder=2))
        ax.add_patch(patches.Rectangle((f2_x, f2_y), L2_m, B2_m, lw=3.5,
                     ec="#0f172a", fc="#e0f2fe", alpha=0.88, zorder=2))

        # ── Draw columns ──
        ax.add_patch(patches.Rectangle((-c1_m/2, -b1_m/2), c1_m, b1_m, lw=2.8,
                     ec="#0f172a", fc="#1e293b", hatch="//", zorder=5))
        ax.text(0, 0, f"C₁\n{c1_cm}×{b1_cm} cm", ha="center", va="center",
                color="#facc15", fontsize=12, weight="bold", zorder=6)

        ax.add_patch(patches.Rectangle((S_m-c2_m/2, -b2_m/2), c2_m, b2_m, lw=2.8,
                     ec="#0f172a", fc="#1e293b", hatch="//", zorder=5))
        ax.text(S_m, 0, f"C₂\n{c2_cm}×{b2_cm} cm", ha="center", va="center",
                color="#facc15", fontsize=12, weight="bold", zorder=6)

        # ── Center axes ──
        ext = max(L1_m/2, L2_m/2, B1_m/2, B2_m/2) + 0.5
        for cx in [0, S_m]:
            ax.plot([cx, cx], [-ext, ext], color="#dc2626", ls="-.", lw=1.4, alpha=0.6, zorder=1)
        ax.plot([-ext, S_m + ext], [0, 0], color="#dc2626", ls="-.", lw=1.4, alpha=0.6, zorder=1)

        # ── Dimensions – Footing 1 ──
        top1 = B1_m / 2.0
        _hdim(ax, top1, f1_x, f1_x + L1_m, f"L₁ = {L1_cm} cm", offset=0.35)
        _vdim(ax, f1_x, f1_y, f1_y + B1_m, f"B₁ = {B1_cm} cm", side="left", offset=0.35)

        # ── Dimensions – Footing 2 ──
        top2 = B2_m / 2.0
        _hdim(ax, top2, f2_x, f2_x + L2_m, f"L₂ = {L2_cm} cm", offset=0.60)
        _vdim(ax, f2_x + L2_m, f2_y, f2_y + B2_m, f"B₂ = {B2_cm} cm", side="right", offset=0.35)

        # ── S dimension ──
        _hdim(ax, -max(B1_m, B2_m) / 2.0, 0, S_m, f"S = {S_m:.2f} m", side="bottom", offset=0.45)

        # ── Clearance annotation ──
        gap_left  = S_m - L1_m / 2.0 - L2_m / 2.0
        clr_x1    = L1_m / 2.0
        clr_x2    = S_m - L2_m / 2.0
        if gap_left > 0.01:
            _hdim(ax, 0, clr_x1, clr_x2, f"Clr = {gap_left*100:.0f} cm", offset=0.20, fs=12)

        # ── Reinforcement Representation & Callouts (2 X-lines & 2 Y-lines) ──
        if rft:
            for tag, cx, LL_m, BB_m in [("1", 0, L1_m, B1_m), ("2", S_m, L2_m, B2_m)]:
                txt_x = rft.get(f"ftg_{tag}_x", "")
                txt_y = rft.get(f"ftg_{tag}_y", "")

                cov = 0.08
                hk = min(0.16, BB_m * 0.12)

                # 1) Draw 2 horizontal lines in X direction (inside footing)
                y_x1 = -BB_m / 3.2
                y_x2 = +BB_m / 3.2
                for y_pos in [y_x1, y_x2]:
                    # Main horizontal bar
                    ax.plot([cx - LL_m / 2 + cov, cx + LL_m / 2 - cov], [y_pos, y_pos],
                            color="#1d4ed8", lw=3.0, zorder=7)
                    # End hooks pointing UP
                    ax.plot([cx - LL_m / 2 + cov, cx - LL_m / 2 + cov], [y_pos, y_pos + hk],
                            color="#1d4ed8", lw=3.0, zorder=7)
                    ax.plot([cx + LL_m / 2 - cov, cx + LL_m / 2 - cov], [y_pos, y_pos + hk],
                            color="#1d4ed8", lw=3.0, zorder=7)

                # Write X reinforcement text HORIZONTALLY above the top X bar
                if txt_x:
                    ax.text(cx, y_x2 + 0.08, f"X-dir (فرش طولي): {txt_x}",
                            ha="center", va="bottom", fontsize=13.5, fontweight="bold",
                            color="#1e3a8a", zorder=12,
                            bbox=dict(boxstyle="round,pad=0.35", fc="#eff6ff", ec="#3b82f6", lw=1.8))

                # 2) Draw 2 vertical lines in Y direction (inside footing)
                x_y1 = cx - LL_m / 3.2
                x_y2 = cx + LL_m / 3.2
                for x_pos in [x_y1, x_y2]:
                    # Main vertical bar
                    ax.plot([x_pos, x_pos], [-BB_m / 2 + cov, +BB_m / 2 - cov],
                            color="#047857", lw=3.0, zorder=7)
                    # End hooks pointing RIGHT
                    ax.plot([x_pos, x_pos + hk], [-BB_m / 2 + cov, -BB_m / 2 + cov],
                            color="#047857", lw=3.0, zorder=7)
                    ax.plot([x_pos, x_pos + hk], [+BB_m / 2 - cov, +BB_m / 2 - cov],
                            color="#047857", lw=3.0, zorder=7)

                # Write Y reinforcement text VERTICALLY (top to bottom) along the left Y bar
                if txt_y:
                    ax.text(x_y1 - 0.08, 0, f"Y-dir (غطاء عرضي): {txt_y}",
                            ha="right", va="center", rotation=90, fontsize=13.5, fontweight="bold",
                            color="#065f46", zorder=12,
                            bbox=dict(boxstyle="round,pad=0.35", fc="#f0fdf4", ec="#10b981", lw=1.8))

        pad = 1.3
        ax.set_xlim(f1_x - pad, f2_x + L2_m + pad)
        ax.set_ylim(-max(B1_m, B2_m)/2 - pad, max(B1_m, B2_m)/2 + pad)

    else:  # combined
        Lc_m = Lc_cm / 100.0; Bc_m = Bc_cm / 100.0
        x1_m = x1_cm / 100.0; x2_m = x2_cm / 100.0

        # Footing origin at left edge: (0, -Bc_m/2)
        fx = 0; fy = -Bc_m / 2.0

        ax.add_patch(patches.Rectangle((fx, fy), Lc_m, Bc_m, lw=3.5,
                     ec="#0f172a", fc="#e0f2fe", alpha=0.88, zorder=2))

        # Columns
        cx1 = x1_m; cx2 = x1_m + S_m
        ax.add_patch(patches.Rectangle((cx1 - c1_m/2, -b1_m/2), c1_m, b1_m, lw=2.8,
                     ec="#0f172a", fc="#1e293b", hatch="//", zorder=5))
        ax.text(cx1, 0, f"C₁\n{c1_cm}×{b1_cm} cm", ha="center", va="center",
                color="#facc15", fontsize=12, weight="bold", zorder=6)

        ax.add_patch(patches.Rectangle((cx2 - c2_m/2, -b2_m/2), c2_m, b2_m, lw=2.8,
                     ec="#0f172a", fc="#1e293b", hatch="//", zorder=5))
        ax.text(cx2, 0, f"C₂\n{c2_cm}×{b2_cm} cm", ha="center", va="center",
                color="#facc15", fontsize=12, weight="bold", zorder=6)

        # Center axes
        ext_y = Bc_m / 2.0 + 0.6
        for cx in [cx1, cx2]:
            ax.plot([cx, cx], [-ext_y, ext_y], color="#dc2626", ls="-.", lw=1.4, alpha=0.6, zorder=1)
        ax.plot([-0.3, Lc_m + 0.3], [0, 0], color="#dc2626", ls="-.", lw=1.4, alpha=0.6, zorder=1)

        # Dimensions
        top = Bc_m / 2.0
        _hdim(ax, top, 0, Lc_m, f"L = {Lc_cm} cm", offset=0.65)
        # Sub-dims
        _hdim(ax, top, 0, cx1, f"x₁ = {x1_cm:.0f} cm", offset=0.30)
        _hdim(ax, top, cx1, cx2, f"S = {S_m:.2f} m", offset=0.30)
        _hdim(ax, top, cx2, Lc_m, f"x₂ = {x2_cm:.0f} cm", offset=0.30)
        # Width
        _vdim(ax, Lc_m, fy, fy + Bc_m, f"B = {Bc_cm} cm", side="right", offset=0.35)

        # ── Reinforcement Representation & Callouts (2 X-lines & 2 Y-lines) ──
        if rft:
            txt_bot_x = rft.get("bot_x", "")
            txt_top_x = rft.get("top_x", "")
            txt_trans_y = rft.get("trans_y", "")

            cov = 0.08
            hk = min(0.18, Bc_m * 0.14)

            # 1) Draw 2 horizontal lines in X direction
            # Line 1: Bottom Main Rebar at -Bc_m/3.2
            y_bot = -Bc_m / 3.2
            ax.plot([0 + cov, Lc_m - cov], [y_bot, y_bot], color="#1d4ed8", lw=3.2, zorder=7)
            # Upward end hooks
            ax.plot([0 + cov, 0 + cov], [y_bot, y_bot + hk], color="#1d4ed8", lw=3.2, zorder=7)
            ax.plot([Lc_m - cov, Lc_m - cov], [y_bot, y_bot + hk], color="#1d4ed8", lw=3.2, zorder=7)

            if txt_bot_x:
                ax.text(Lc_m / 2, y_bot + 0.08, f"X-Bottom (فرش سفلي طولي): {txt_bot_x}",
                        ha="center", va="bottom", fontsize=13.5, fontweight="bold",
                        color="#1e3a8a", zorder=12,
                        bbox=dict(boxstyle="round,pad=0.35", fc="#eff6ff", ec="#3b82f6", lw=1.8))

            # Line 2: Top Main Rebar at +Bc_m/3.2
            y_top = +Bc_m / 3.2
            ax.plot([0 + cov, Lc_m - cov], [y_top, y_top], color="#dc2626", lw=3.2, zorder=7)
            # Downward end hooks
            ax.plot([0 + cov, 0 + cov], [y_top, y_top - hk], color="#dc2626", lw=3.2, zorder=7)
            ax.plot([Lc_m - cov, Lc_m - cov], [y_top, y_top - hk], color="#dc2626", lw=3.2, zorder=7)

            if txt_top_x:
                ax.text(Lc_m / 2, y_top + 0.08, f"X-Top (تسليح علوي طولي): {txt_top_x}",
                        ha="center", va="bottom", fontsize=13.5, fontweight="bold",
                        color="#991b1b", zorder=12,
                        bbox=dict(boxstyle="round,pad=0.35", fc="#fef2f2", ec="#ef4444", lw=1.8))

            # 2) Draw vertical lines in Y direction
            # Transverse Bottom Main Steel (GREEN) under C1 & C2
            x_trn1 = cx1 - c1_m / 2.0 - 0.20
            x_trn2 = cx2 + c2_m / 2.0 + 0.20
            for x_pos in [x_trn1, x_trn2]:
                ax.plot([x_pos, x_pos], [-Bc_m / 2 + cov, +Bc_m / 2 - cov],
                        color="#047857", lw=3.2, zorder=7)
                # Inward hooks
                ax.plot([x_pos, x_pos + hk], [-Bc_m / 2 + cov, -Bc_m / 2 + cov],
                        color="#047857", lw=3.2, zorder=7)
                ax.plot([x_pos, x_pos + hk], [+Bc_m / 2 - cov, +Bc_m / 2 - cov],
                        color="#047857", lw=3.2, zorder=7)

            if txt_trans_y:
                ax.text(x_trn1 - 0.08, 0, f"Y-Bottom (سفلي عرضي رئيسي): {txt_trans_y}",
                        ha="right", va="center", rotation=90, fontsize=13.0, fontweight="bold",
                        color="#065f46", zorder=12,
                        bbox=dict(boxstyle="round,pad=0.35", fc="#f0fdf4", ec="#10b981", lw=1.8))

            # Transverse Top Secondary / Shrinkage Steel (PURPLE) between columns
            txt_trans_top_y = rft.get("trans_top_y", "")
            if txt_trans_top_y:
                x_sec1 = cx1 + (cx2 - cx1) * 0.38
                x_sec2 = cx1 + (cx2 - cx1) * 0.62
                for x_pos in [x_sec1, x_sec2]:
                    ax.plot([x_pos, x_pos], [-Bc_m / 2 + cov, +Bc_m / 2 - cov],
                            color="#9333ea", lw=3.0, ls="-", zorder=7)
                    ax.plot([x_pos, x_pos + hk], [-Bc_m / 2 + cov, -Bc_m / 2 + cov],
                            color="#9333ea", lw=3.0, zorder=7)
                    ax.plot([x_pos, x_pos + hk], [+Bc_m / 2 - cov, +Bc_m / 2 - cov],
                            color="#9333ea", lw=3.0, zorder=7)

                purple_label = f"Y-Top Secondary (علوي عرضي)\n{txt_trans_top_y} (تربيط وانكماش)"
                ax.text((x_sec1 + x_sec2) / 2.0, 0, purple_label,
                        ha="center", va="center", rotation=90, fontsize=13.5, fontweight="bold",
                        color="#6b21a8", zorder=12,
                        bbox=dict(boxstyle="round,pad=0.25", fc="#faf5ff", ec="#c084fc", lw=1.5))

        pad = 1.3
        ax.set_xlim(-pad, Lc_m + pad + 0.8)
        ax.set_ylim(-Bc_m / 2 - pad, Bc_m / 2 + pad)

    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  STRUCTURAL TUTORIAL DRAWINGS
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_tutorial_bmd():
    """Generate the Bending Moment & Structural Behavior tutorial figure."""
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, axes = plt.subplots(2, 1, figsize=(16, 11), dpi=150, facecolor="#ffffff")
    plt.subplots_adjust(hspace=0.38)

    # 1. Longitudinal BMD
    ax1 = axes[0]
    ax1.set_facecolor("#f8fafc")
    ax1.set_title("1. Longitudinal Direction (X-Axis): Inverted Beam Model & Bending Moments (BMD)",
                  fontsize=13.5, fontweight="bold", pad=12, color="#0f172a")

    ax1.add_patch(patches.Rectangle((1.0, 1.8), 8.0, 1.0, fc="#e2e8f0", ec="#0f172a", lw=2.5, zorder=2))
    ax1.add_patch(patches.Rectangle((2.6, 2.8), 0.8, 0.8, fc="#334155", ec="#0f172a", hatch="//", lw=2, zorder=3))
    ax1.text(3.0, 3.2, "C1\n(P1)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)
    ax1.annotate("", xy=(3.0, 2.8), xytext=(3.0, 3.9), arrowprops=dict(arrowstyle="->", color="#dc2626", lw=2.8))

    ax1.add_patch(patches.Rectangle((6.6, 2.8), 0.8, 0.8, fc="#334155", ec="#0f172a", hatch="//", lw=2, zorder=3))
    ax1.text(7.0, 3.2, "C2\n(P2)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)
    ax1.annotate("", xy=(7.0, 2.8), xytext=(7.0, 3.9), arrowprops=dict(arrowstyle="->", color="#dc2626", lw=2.8))

    for x in [1.5, 2.3, 3.1, 3.9, 4.7, 5.5, 6.3, 7.1, 7.9, 8.5]:
        ax1.annotate("", xy=(x, 1.8), xytext=(x, 1.0), arrowprops=dict(arrowstyle="->", color="#2563eb", lw=1.8))
    ax1.text(5.0, 0.65, "Upward Uniform Net Soil Reaction (qu)", ha="center", color="#1d4ed8", fontweight="bold", fontsize=11)

    # Rebar & Moments
    ax1.plot([1.2, 8.8], [2.6, 2.6], color="#dc2626", lw=3.2, zorder=5)
    ax1.plot([1.2, 1.2], [2.6, 2.3], color="#dc2626", lw=3.2, zorder=5)
    ax1.plot([8.8, 8.8], [2.6, 2.3], color="#dc2626", lw=3.2, zorder=5)
    ax1.text(5.0, 2.75, "TOP REBAR: Resists Negative Hogging Moment (-M_top) between columns",
             ha="center", va="bottom", color="#b91c1c", fontweight="bold", fontsize=10.5,
             bbox=dict(boxstyle="round,pad=0.22", fc="#fee2e2", ec="#ef4444"))

    ax1.plot([1.2, 8.8], [2.0, 2.0], color="#1d4ed8", lw=3.2, zorder=5)
    ax1.plot([1.2, 1.2], [2.0, 2.3], color="#1d4ed8", lw=3.2, zorder=5)
    ax1.plot([8.8, 8.8], [2.0, 2.3], color="#1d4ed8", lw=3.2, zorder=5)
    ax1.text(5.0, 2.18, "BOTTOM REBAR: Resists Positive Moments (+M_bot) under cantilevers",
             ha="center", va="bottom", color="#1e40af", fontweight="bold", fontsize=10.5,
             bbox=dict(boxstyle="round,pad=0.22", fc="#eff6ff", ec="#3b82f6"))

    ax1.set_xlim(0, 10)
    ax1.set_ylim(0.3, 4.2)
    ax1.axis("off")

    # 2. Transverse Cantilever
    ax2 = axes[1]
    ax2.set_facecolor("#f8fafc")
    ax2.set_title("2. Transverse Direction (Y-Axis): Lateral Cantilever Action & Bottom Tension Only",
                  fontsize=13.5, fontweight="bold", pad=12, color="#0f172a")

    ax2.add_patch(patches.Rectangle((2.5, 1.8), 5.0, 1.0, fc="#e2e8f0", ec="#0f172a", lw=2.5, zorder=2))
    ax2.add_patch(patches.Rectangle((4.5, 2.8), 1.0, 0.8, fc="#334155", ec="#0f172a", hatch="//", lw=2, zorder=3))
    ax2.text(5.0, 3.2, "Column\n(Pu)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=11)
    ax2.annotate("", xy=(5.0, 2.8), xytext=(5.0, 3.9), arrowprops=dict(arrowstyle="->", color="#dc2626", lw=2.8))

    for x in [2.8, 3.5, 4.2, 5.0, 5.8, 6.5, 7.2]:
        ax2.annotate("", xy=(x, 1.8), xytext=(x, 1.0), arrowprops=dict(arrowstyle="->", color="#059669", lw=1.8))
    ax2.text(5.0, 0.65, "Soil Pressure bends lateral cantilevers upward -> BOTTOM TENSION ONLY",
             ha="center", color="#047857", fontweight="bold", fontsize=11)

    ax2.plot([2.7, 7.3], [2.0, 2.0], color="#047857", lw=3.5, zorder=5)
    ax2.plot([2.7, 2.7], [2.0, 2.3], color="#047857", lw=3.5, zorder=5)
    ax2.plot([7.3, 7.3], [2.0, 2.3], color="#047857", lw=3.5, zorder=5)
    ax2.text(5.0, 2.15, "MAIN TRANSVERSE BOTTOM REBAR: Resists Cantilever Sagging Moments",
             ha="center", color="#065f46", fontweight="bold", fontsize=10.5,
             bbox=dict(boxstyle="round,pad=0.2", fc="#d1fae5", ec="#10b981"))

    ax2.plot([2.7, 7.3], [2.6, 2.6], color="#9333ea", lw=2.2, ls="--", zorder=5)
    ax2.text(5.0, 2.75, "Top Secondary Rebar (5Φ10/m) - For Shrinkage & Rebar Carrier Only (No Design Moment)",
             ha="center", color="#6b21a8", fontsize=9.0, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.15", fc="#faf5ff", ec="#c084fc"))

    ax2.set_xlim(0, 10)
    ax2.set_ylim(0.3, 4.2)
    ax2.axis("off")

    fig.tight_layout()
    return fig


def _draw_tutorial_sections():
    """Generate the complete 4-layer executive blueprint figure."""
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, (ax_plan, ax_sec) = plt.subplots(2, 1, figsize=(18, 17), dpi=150, facecolor="#ffffff")
    plt.subplots_adjust(hspace=0.36)

    # 1. Plan View
    ax_plan.set_facecolor("#f8fafc")
    ax_plan.set_title("1. Plan View: Full 4-Layer Executive Reinforcement Blueprint (المسقط الأفقي التنفيذي المتكامل للـ 4 طبقات)", 
                      fontsize=14, fontweight="bold", pad=14, color="#0f172a")

    ax_plan.add_patch(patches.Rectangle((1.0, 1.0), 12.0, 5.2, fc="#ffffff", ec="#0f172a", lw=3.5, zorder=2))
    ax_plan.annotate("", xy=(1.0, 6.5), xytext=(13.0, 6.5), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.8))
    ax_plan.text(7.0, 6.65, "Footing Length (L)", ha="center", va="bottom", fontsize=12, fontweight="bold", color="#1e293b")

    ax_plan.annotate("", xy=(13.3, 1.0), xytext=(13.3, 6.2), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.8))
    ax_plan.text(13.5, 3.6, "Footing Width (B)", ha="left", va="center", rotation=-90, fontsize=12, fontweight="bold", color="#1e293b")

    # Column 1
    ax_plan.add_patch(patches.Rectangle((3.0, 2.9), 1.2, 1.4, fc="#1e293b", ec="#0f172a", hatch="//", lw=2, zorder=5))
    ax_plan.text(3.6, 3.6, "C1\n(Col 1)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=12, zorder=6)

    # Column 2
    ax_plan.add_patch(patches.Rectangle((9.5, 2.9), 1.4, 1.4, fc="#1e293b", ec="#0f172a", hatch="//", lw=2, zorder=5))
    ax_plan.text(10.2, 3.6, "C2\n(Col 2)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=12, zorder=6)

    ax_plan.plot([3.6, 3.6], [0.5, 6.8], color="#dc2626", ls="-.", lw=1.4, alpha=0.6)
    ax_plan.plot([10.2, 10.2], [0.5, 6.8], color="#dc2626", ls="-.", lw=1.4, alpha=0.6)
    ax_plan.plot([0.5, 13.5], [3.6, 3.6], color="#dc2626", ls="-.", lw=1.4, alpha=0.6)

    # Layer 1: X-Top Main
    ax_plan.plot([1.3, 12.7], [5.2, 5.2], color="#dc2626", lw=3.8, zorder=8)
    ax_plan.plot([1.3, 1.3], [5.2, 4.8], color="#dc2626", lw=3.8, zorder=8)
    ax_plan.plot([12.7, 12.7], [5.2, 4.8], color="#dc2626", lw=3.8, zorder=8)
    ax_plan.text(7.0, 5.35, "[RED] Layer 1: X-Top Main Rebar (تسليح طولي علوي رئيسي لمقاومة العزم السالب بين العمودين)", 
                 ha="center", va="bottom", fontsize=11.5, fontweight="bold", color="#991b1b", 
                 bbox=dict(boxstyle="round,pad=0.28", fc="#fef2f2", ec="#ef4444", lw=1.6), zorder=12)

    # Layer 2: X-Bottom Main
    ax_plan.plot([1.3, 12.7], [2.0, 2.0], color="#1d4ed8", lw=3.8, zorder=8)
    ax_plan.plot([1.3, 1.3], [2.0, 2.4], color="#1d4ed8", lw=3.8, zorder=8)
    ax_plan.plot([12.7, 12.7], [2.0, 2.4], color="#1d4ed8", lw=3.8, zorder=8)
    ax_plan.text(7.0, 1.50, "[BLUE] Layer 2: X-Bottom Main Rebar (تسليح طولي سفلي رئيسي لمقاومة عزم الكوابيل الموجب)", 
                 ha="center", va="top", fontsize=11.5, fontweight="bold", color="#1e40af", 
                 bbox=dict(boxstyle="round,pad=0.28", fc="#eff6ff", ec="#3b82f6", lw=1.6), zorder=12)

    # Layer 3: Y-Transverse Bottom Main (Under C1 & C2)
    ax_plan.plot([2.2, 2.2], [1.3, 5.9], color="#047857", lw=3.2, zorder=7)
    ax_plan.plot([2.2, 2.5], [1.3, 1.3], color="#047857", lw=3.2, zorder=7)
    ax_plan.plot([2.2, 2.5], [5.9, 5.9], color="#047857", lw=3.2, zorder=7)

    ax_plan.plot([4.8, 4.8], [1.3, 5.9], color="#047857", lw=3.2, zorder=7)
    ax_plan.plot([4.8, 4.5], [1.3, 1.3], color="#047857", lw=3.2, zorder=7)
    ax_plan.plot([4.8, 4.5], [5.9, 5.9], color="#047857", lw=3.2, zorder=7)

    ax_plan.text(1.8, 3.6, "[GREEN] Layer 3: Y-Transverse Bottom Main\n(تسليح عرضي سفلي رئيسي أسفل العمود C1)", 
                 ha="right", va="center", rotation=90, fontsize=11, fontweight="bold", color="#065f46",
                 bbox=dict(boxstyle="round,pad=0.25", fc="#f0fdf4", ec="#10b981", lw=1.5), zorder=12)

    ax_plan.plot([8.6, 8.6], [1.3, 5.9], color="#047857", lw=3.2, zorder=7)
    ax_plan.plot([8.6, 8.9], [1.3, 1.3], color="#047857", lw=3.2, zorder=7)
    ax_plan.plot([8.6, 8.9], [5.9, 5.9], color="#047857", lw=3.2, zorder=7)

    ax_plan.plot([11.7, 11.7], [1.3, 5.9], color="#047857", lw=3.2, zorder=7)
    ax_plan.plot([11.7, 11.4], [1.3, 1.3], color="#047857", lw=3.2, zorder=7)
    ax_plan.plot([11.7, 11.4], [5.9, 5.9], color="#047857", lw=3.2, zorder=7)

    ax_plan.text(12.1, 3.6, "[GREEN] Layer 3: Y-Transverse Bottom Main\n(تسليح عرضي سفلي رئيسي أسفل العمود C2)", 
                 ha="left", va="center", rotation=-90, fontsize=11, fontweight="bold", color="#065f46",
                 bbox=dict(boxstyle="round,pad=0.25", fc="#f0fdf4", ec="#10b981", lw=1.5), zorder=12)

    # Layer 4: Y-Top Secondary Shrinkage Rebar (80% scaled font)
    for x_pos in [6.1, 7.7]:
        ax_plan.plot([x_pos, x_pos], [1.3, 5.9], color="#9333ea", lw=2.8, ls="-", zorder=7)
        ax_plan.plot([x_pos, x_pos + 0.3], [1.3, 1.3], color="#9333ea", lw=2.8, zorder=7)
        ax_plan.plot([x_pos, x_pos + 0.3], [5.9, 5.9], color="#9333ea", lw=2.8, zorder=7)

    ax_plan.text(6.9, 3.6, "[PURPLE] Layer 4: Y-Top Secondary Rebar (5Φ10/m)\n(تسليح عرضي علوي ثانوي للتربيط والانكماش وحمل الأسياخ العلوية)", 
                 ha="center", va="center", rotation=90, fontsize=8.8, fontweight="bold", color="#6b21a8",
                 bbox=dict(boxstyle="round,pad=0.18", fc="#faf5ff", ec="#c084fc", lw=1.2), zorder=12)

    ax_plan.set_xlim(0, 14.5)
    ax_plan.set_ylim(0.4, 7.3)
    ax_plan.axis("off")

    # 2. Longitudinal Section
    ax_sec.set_facecolor("#f8fafc")
    ax_sec.set_title("2. Longitudinal Cross-Section: Full 4-Layer Stacking & Detailing (القطاع الإنشائي الطولي التفصيلي للطبقات الأربع)", 
                     fontsize=14, fontweight="bold", pad=14, color="#0f172a")

    ax_sec.add_patch(patches.Rectangle((0.8, 0.4), 12.4, 0.5, fc="#e2e8f0", ec="#94a3b8", lw=1.5, hatch="..", zorder=1))
    ax_sec.text(1.0, 0.65, "Plain Concrete Blinding (P.C فرشة نظافة)", ha="left", va="center", fontsize=10.5, fontweight="bold", color="#64748b")

    ax_sec.add_patch(patches.Rectangle((1.0, 0.9), 12.0, 2.4, fc="#ffffff", ec="#0f172a", lw=3.5, zorder=2))

    # Columns
    ax_sec.add_patch(patches.Rectangle((3.0, 3.3), 1.2, 2.2, fc="#334155", ec="#0f172a", lw=2.5, zorder=4))
    ax_sec.text(3.6, 4.4, "C1\n(Col 1)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=12)

    ax_sec.add_patch(patches.Rectangle((9.5, 3.3), 1.4, 2.2, fc="#334155", ec="#0f172a", lw=2.5, zorder=4))
    ax_sec.text(10.2, 4.4, "C2\n(Col 2)", ha="center", va="center", color="#facc15", fontweight="bold", fontsize=12)

    # Column Dowels
    ax_sec.plot([3.15, 3.15, 2.4], [5.2, 1.15, 1.15], color="#eab308", lw=3.0, zorder=6)
    ax_sec.plot([4.05, 4.05, 4.8], [5.2, 1.15, 1.15], color="#eab308", lw=3.0, zorder=6)
    ax_sec.plot([9.65, 9.65, 8.9], [5.2, 1.15, 1.15], color="#eab308", lw=3.0, zorder=6)
    ax_sec.plot([10.75, 10.75, 11.5], [5.2, 1.15, 1.15], color="#eab308", lw=3.0, zorder=6)
    ax_sec.text(3.6, 5.4, "Column Dowels (أشاير الأعمدة Ld)", ha="center", va="bottom", fontsize=11, fontweight="bold", color="#ca8a04")

    # Layer 1: X-Top Main
    ax_sec.plot([1.2, 12.8], [3.05, 3.05], color="#dc2626", lw=3.8, zorder=8)
    ax_sec.plot([1.2, 1.2], [3.05, 1.5], color="#dc2626", lw=3.8, zorder=8)
    ax_sec.plot([12.8, 12.8], [3.05, 1.5], color="#dc2626", lw=3.8, zorder=8)
    ax_sec.text(7.0, 3.16, "[RED] Layer 1: X-Top Main Rebar (تسليح طولي علوي رئيسي)", 
                ha="center", va="bottom", fontsize=11.5, fontweight="bold", color="#991b1b",
                bbox=dict(boxstyle="round,pad=0.22", fc="#fef2f2", ec="#ef4444", lw=1.5), zorder=12)

    # Layer 4: Y-Top Secondary Dots (80% scaled font)
    for x in [1.5, 2.1, 2.7, 3.3, 3.9, 4.5, 5.1, 5.7, 6.3, 6.9, 7.5, 8.1, 8.7, 9.3, 9.9, 10.5, 11.1, 11.7, 12.3]:
        ax_sec.scatter(x, 2.92, s=50, color="#9333ea", edgecolors="#581c87", lw=1.0, zorder=9)
    ax_sec.text(12.9, 2.92, "Layer 4: Y-Top Secondary Dots (5Φ10/m) [PURPLE]", ha="left", va="center", fontsize=8.0, fontweight="bold", color="#7e22ce")

    # Layer 2: X-Bottom Main
    ax_sec.plot([1.2, 12.8], [1.15, 1.15], color="#1d4ed8", lw=3.8, zorder=8)
    ax_sec.plot([1.2, 1.2], [1.15, 2.7], color="#1d4ed8", lw=3.8, zorder=8)
    ax_sec.plot([12.8, 12.8], [1.15, 2.7], color="#1d4ed8", lw=3.8, zorder=8)
    ax_sec.text(7.0, 0.94, "[BLUE] Layer 2: X-Bottom Main Rebar (تسليح طولي سفلي رئيسي)", 
                ha="center", va="top", fontsize=11.5, fontweight="bold", color="#1e40af",
                bbox=dict(boxstyle="round,pad=0.22", fc="#eff6ff", ec="#3b82f6", lw=1.5), zorder=12)

    # Layer 3: Y-Bottom Transverse Dots
    for x in [1.4, 1.8, 2.2, 2.6, 3.0, 3.4, 3.8, 4.2, 4.6, 5.0, 5.4, 5.8, 6.2, 6.6, 7.0, 7.4, 7.8, 8.2, 8.6, 9.0, 9.4, 9.8, 10.2, 10.6, 11.0, 11.4, 11.8, 12.2, 12.6]:
        ax_sec.scatter(x, 1.28, s=65, color="#047857", edgecolors="#064e3b", lw=1.2, zorder=9)
    ax_sec.text(12.9, 1.28, "Layer 3: Y-Bottom Transverse Dots [GREEN]", ha="left", va="center", fontsize=10, fontweight="bold", color="#065f46")

    # Steel Chairs
    for cx in [4.8, 7.8]:
        ax_sec.plot([cx-0.2, cx-0.2, cx+0.2, cx+0.2], [1.15, 2.92, 2.92, 1.15], color="#475569", lw=2.2, zorder=5)
        ax_sec.text(cx, 2.05, "Chair\n(كرسي)", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#475569")

    # Thickness dimension
    ax_sec.annotate("", xy=(0.5, 0.9), xytext=(0.5, 3.3), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.8))
    ax_sec.text(0.3, 2.1, "Thickness (t)", ha="right", va="center", rotation=90, fontsize=12, fontweight="bold", color="#1e293b")

    ax_sec.set_xlim(0, 15.5)
    ax_sec.set_ylim(0.1, 5.8)
    ax_sec.axis("off")

    fig.tight_layout()
    return fig


def _render_structural_tutorial():
    """Render the interactive Combined Footing Structural Tutorial with sub-tabs."""
    st.markdown("---")
    with st.expander("📚 Combined Footing Structural Tutorial (الدليل الإنشائي والتعليمي للقواعد المشتركة)", expanded=False):
        t1, t2 = st.tabs([
            "📈 مخططات العزوم والسلوك الإنشائي (BMD & Structural Behavior)",
            "🧱 قطاعات وتفاصيل التسليح الكاملة (Full 4-Layer Detailing)",
        ])

        with t1:
            st.markdown("#### 🔍 السلوك الإنشائي ومخططات العزوم (Bending Moments & Mechanics)")
            fig_bmd = _draw_tutorial_bmd()
            st.pyplot(fig_bmd, use_container_width=True)
            plt.close(fig_bmd)

            st.markdown(
                """
                <div dir="rtl" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:16px; font-size:14px; line-height:1.8;">
                <b>📌 تحليل السلوك الإنشائي للقاعدة المشتركة:</b><br>
                1. <b>الاتجاه الطولي (X-Axis):</b> تعمل ككمرة مقلوبة مستمرة مرتكزة على العمودين ومحملة بضغط التربة الموزع لأعلى.
                   - ينتج عن ذلك <b>عزم سالب كبير جداً (Hogging)</b> في منتصف البحر بين العمودين يستدعي تسليحاً علوياً رئيسياً وقوياً.
                   - وعزم موجب سفلي عند الكوابيل وأسفل الأعمدة يستدعي تسليحاً سفلياً.
                <br>
                2. <b>الاتجاه العرضي (Y-Axis):</b> تعمل ككابوليين جانبيين بسيطين يبرزان يمين ويسار كل عمود بمسافة <code>(B - bc) / 2</code>.
                   - ضغط التربة الصاعد لأعلى يثني طرفي الكابولي للأعلى، مما يسبب شداً في <b>السطح السفلي فقط</b>.
                   - لا يتولد أي عزم علوي في الاتجاه العرضي، ويكتفى بوضع حديد علوي خفيف <code>5Φ10/m</code> للتربيط والانكماش.
                </div>
                """,
                unsafe_allow_html=True,
            )

        with t2:
            st.markdown("#### 🧱 المخطط التنفيذي الشامل للطبقات الأربع للتسليح (4-Layer Executive Blueprint)")
            fig_sec = _draw_tutorial_sections()
            st.pyplot(fig_sec, use_container_width=True)
            plt.close(fig_sec)

            st.markdown(
                """
                <div dir="rtl" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:16px; font-size:14px; line-height:1.8;">
                <b>📋 تفصيل الطبقات الأربع لحديد التسليح:</b><br>
                • 🔴 <b>Layer 1 (X-Top Main):</b> تسليح علوي طولي رئيسي لمقاومة العزم السالب بين العمودين.<br>
                • 🔵 <b>Layer 2 (X-Bottom Main):</b> تسليح سفلي طولي رئيسي لمقاومة عزم الكوابيل الموجب.<br>
                • 🟢 <b>Layer 3 (Y-Transverse Bottom Main):</b> تسليح عرضي سفلي رئيسي أسفل الأعمدة لمقاومة عزم الكابولي العرضي.<br>
                • 🟣 <b>Layer 4 (Y-Top Secondary):</b> تسليح عرضي علوي ثانوي (5Φ10/m) للتربيط والانكماش واستكمال الشبكة العلوية وحمل الأسياخ.<br>
                • 🟨 <b>أشاير الأعمدة (Dowels):</b> تمتد برجل 90° داخل القاعدة بطول الرباط الكودي $L_d$.<br>
                • 🪑 <b>كراسي الحديد (Steel Chairs):</b> لحمل وضبط منسوب الشبكة العلوية.
                </div>
                """,
                unsafe_allow_html=True,
            )



# ═══════════════════════════════════════════════════════════════════════════════
#  AUTO-SUGGESTED MINIMUM THICKNESS
# ═══════════════════════════════════════════════════════════════════════════════

def _suggest_t_iso(P_ton, c_cm, b_cm, L_cm, B_cm, Fcu, Fy, cover_cm, Phi_mm, q_net_kgcm2):
    """Iterate d to satisfy one-way + punching for one isolated footing. Returns t_cm."""
    phi_cm = Phi_mm / 10.0
    P_u_kg = 1.5 * P_ton * 1000.0               # kg
    A_cm2  = L_cm * B_cm
    q_u    = P_u_kg / A_cm2 if A_cm2 > 0 else 0 # kg/cm²

    cant_L = (L_cm - c_cm) / 2.0                 # cm
    cant_B = (B_cm - b_cm) / 2.0                 # cm

    tau_s_allow = _shear_allow_kgcm2(Fcu)       # kg/cm²

    for d_cm in range(15, 250):
        # One-way shear (critical at d/2 from face)
        a_L = max(cant_L - d_cm / 2.0, 0)
        a_B = max(cant_B - d_cm / 2.0, 0)
        V_L = q_u * B_cm * a_L
        V_B = q_u * L_cm * a_B
        tau_L = V_L / (B_cm * d_cm) if d_cm > 0 else 999
        tau_B = V_B / (L_cm * d_cm) if d_cm > 0 else 999
        if max(tau_L, tau_B) > tau_s_allow:
            continue

        # Punching shear (perimeter at d/2 from face)
        ap = c_cm + d_cm; bp = b_cm + d_cm       # cm
        bo = 2.0 * (ap + bp)                      # cm
        A_punch = ap * bp                         # cm²
        Q_p = P_u_kg - q_u * A_punch             # kg
        tau_p = Q_p / (bo * d_cm) if (bo * d_cm) > 0 else 999
        tau_p_allow = _punch_allow_kgcm2(Fcu, c_cm, b_cm, d_cm, bo)
        if tau_p > tau_p_allow:
            continue

        break
    t_raw = d_cm + cover_cm + phi_cm / 2.0
    return max(40, _r5(t_raw))


def _suggest_t_combined(P1_ton, P2_ton, c1_cm, b1_cm, c2_cm, b2_cm, S_m, L_cm, B_cm, x1_cm,
                        Fcu, Fy, cover_cm, Phi_mm, q_net_kgcm2):
    """Iterate d for combined footing. Returns t_cm."""
    phi_cm = Phi_mm / 10.0
    Pu1_kg = 1.5 * P1_ton * 1000.0; Pu2_kg = 1.5 * P2_ton * 1000.0; Ru_kg = Pu1_kg + Pu2_kg
    L_m = L_cm / 100.0; B_m = B_cm / 100.0
    x1_m = x1_cm / 100.0; x2_m = L_m - x1_m - S_m
    c1_m = c1_cm / 100.0; c2_m = c2_cm / 100.0

    A_cm2 = L_cm * B_cm
    if A_cm2 <= 0:
        return 50
    q_u_kgcm2 = Ru_kg / A_cm2                    # kg/cm²
    w_kgcm    = Ru_kg / L_cm                     # kg/cm

    tau_s_allow = _shear_allow_kgcm2(Fcu)

    for d_cm in range(15, 250):
        # ── One-way shear at 4 critical sections ──
        # 1) left cantilever
        xs1 = max((x1_m - c1_m / 2.0) * 100.0 - d_cm / 2.0, 0)
        V1  = w_kgcm * xs1
        # 2) right cantilever
        xs2 = max((x2_m - c2_m / 2.0) * 100.0 - d_cm / 2.0, 0)
        V2  = w_kgcm * xs2
        # 3) d/2 right of C1 (between cols)
        xm1 = (x1_m + c1_m / 2.0) * 100.0 + d_cm / 2.0
        V3  = abs(w_kgcm * xm1 - Pu1_kg)
        # 4) d/2 left of C2 (between cols)
        xm2 = (x1_m + S_m - c2_m / 2.0) * 100.0 - d_cm / 2.0
        V4  = abs(w_kgcm * xm2 - Pu1_kg)

        V_gov = max(V1, V2, V3, V4)
        tau_s = V_gov / (B_cm * d_cm) if (B_cm * d_cm) > 0 else 999
        if tau_s > tau_s_allow:
            continue

        # ── Punching at both columns ──
        ok = True
        for (Pu_k, cc, bb) in [(Pu1_kg, c1_cm, b1_cm), (Pu2_kg, c2_cm, b2_cm)]:
            ap = cc + d_cm; bp = bb + d_cm
            bo = 2.0 * (ap + bp)
            A_punch = ap * bp
            Q_p = Pu_k - q_u_kgcm2 * A_punch
            tau_p = Q_p / (bo * d_cm) if (bo * d_cm) > 0 else 999
            tau_p_a = _punch_allow_kgcm2(Fcu, cc, bb, d_cm, bo)
            if tau_p > tau_p_a:
                ok = False
                break
        if not ok:
            continue
        break

    t_raw = d_cm + cover_cm + phi_cm / 2.0
    return max(50, _r5(t_raw))


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    """Entry point — Combined Footing Design (ECP 203) in Standard Metric Units."""

    # ── HEADER ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="input-section-header">
            <span style="font-size:26px;">🏗️</span>
            <span>Module 7 — Combined Footing Design — ECP 203</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── DESIGN NOTE ───────────────────────────────────────────────────────────
    st.warning(
        "⚠️ **ملاحظة تصميمية:** تُعتبر الخرسانة العادية (P.C) فرشة نظافة بسمك أقل من 20 سم، "
        "ولا يتم أخذها في الاعتبار في توزيع الإجهادات أو تقليل أبعاد القواعد المسلحة؛ "
        "ويتم تصميم الخرسانة المسلحة (R.C) مباشرة على إجهاد التربة الصافي المسموح به "
        "(**q_all,net**)."
    )

    # ── COMPACT CSS STYLING (Minimize vertical gaps between inputs) ────────────
    st.markdown(
        """
        <style>
        /* Compact, comfortable input styling for Module 7 */
        div[data-testid="stExpander"] details {
            padding: 8px 14px !important;
            margin-bottom: 8px !important;
        }
        div[data-testid="stExpander"] details summary {
            padding: 6px 10px !important;
        }
        div[data-testid="stExpander"] div[data-testid="stVerticalBlock"] {
            gap: 0.45rem !important;
        }
        div[data-testid="stNumberInput"],
        div[data-testid="stSelectbox"] {
            margin-top: 2px !important;
            margin-bottom: 6px !important;
        }
        div[data-testid="stNumberInput"] label,
        div[data-testid="stSelectbox"] label {
            margin-bottom: 2px !important;
            padding-bottom: 1px !important;
            min-height: 0px !important;
        }
        div[data-testid="stNumberInput"] label p,
        div[data-testid="stSelectbox"] label p {
            font-size: 13.5px !important;
            font-weight: 700 !important;
            line-height: 1.3 !important;
            margin-bottom: 2px !important;
        }
        div[data-testid="stNumberInputContainer"],
        div[data-baseweb="select"] {
            min-height: 36px !important;
            height: 36px !important;
        }
        div[data-testid="stNumberInputContainer"] input {
            height: 32px !important;
            padding-top: 3px !important;
            padding-bottom: 3px !important;
            font-size: 14px !important;
        }
        div[data-testid="stNumberInputContainer"] button {
            height: 32px !important;
            min-height: 32px !important;
        }
        .stCaption {
            margin-top: 1px !important;
            margin-bottom: 4px !important;
            font-size: 11.5px !important;
            line-height: 1.25 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════════════════════════
    #  1.  INPUTS (ton · cm · m · kg/cm²)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        """
        <div class="input-section-header">
            <span style="font-size:26px;">📥</span>
            <span>مدخلات التصميم (Design Inputs — ton · cm · m · kg/cm²)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📝 Column & Soil Data (بيانات الأعمدة والتربة والمواد)", expanded=True):
        ic1, ic2, ic3 = st.columns(3)

        with ic1:
            st.markdown("**🔩 Column 1 (C₁)**")
            P1 = S.number_input("Service Load P₁ (ton)", "tcf_P1", min_value=1.0, max_value=3000.0, step=5.0)
            c1 = S.number_input("c₁ — parallel to link (cm)", "tcf_c1", min_value=15, max_value=300, step=5)
            b1 = S.number_input("b₁ — perpendicular (cm)", "tcf_b1", min_value=15, max_value=300, step=5)

        with ic2:
            st.markdown("**🔩 Column 2 (C₂)**")
            P2 = S.number_input("Service Load P₂ (ton)", "tcf_P2", min_value=1.0, max_value=3000.0, step=5.0)
            c2 = S.number_input("c₂ — parallel to link (cm)", "tcf_c2", min_value=15, max_value=300, step=5)
            b2 = S.number_input("b₂ — perpendicular (cm)", "tcf_b2", min_value=15, max_value=300, step=5)

        with ic3:
            st.markdown("**🌱 Soil & Materials**")
            S_dist = S.number_input("Spacing S (m) — centre-to-centre", "tcf_S", min_value=0.5, max_value=30.0, step=0.25)
            q_net  = S.number_input("q_all,net (kg/cm²)", "tcf_q_net", min_value=0.5, max_value=5.0, step=0.1,
                                    help="Net allowable soil bearing capacity (realistic range: 0.5 – 5.0 kg/cm² | 1.5 kg/cm² = 15 ton/m²)")
            Fcu    = S.number_input("Fcu (kg/cm²)", "tcf_Fcu", min_value=150, max_value=600, step=25)
            Fy     = S.number_input("Fy  (kg/cm²)", "tcf_Fy",  min_value=2000, max_value=6000, step=200)
            cover  = S.number_input("Cover (cm)", "tcf_cover", min_value=3, max_value=15, step=1)
            Phi    = S.selectbox("Main Bar Φ (mm)", "tcf_Phi_index",
                                options=[12, 16, 18, 22, 25])

    # ══════════════════════════════════════════════════════════════════════════
    #  2.  INPUT VALIDATION
    # ══════════════════════════════════════════════════════════════════════════
    errs = []
    if P1 is None or P1 <= 0: errs.append(f"Column 1 Load P₁ must be > 0 ton (got {P1}).")
    if P2 is None or P2 <= 0: errs.append(f"Column 2 Load P₂ must be > 0 ton (got {P2}).")
    for lbl, val in [("c₁", c1), ("b₁", b1), ("c₂", c2), ("b₂", b2)]:
        if val is None or val < 15: errs.append(f"Column dimension {lbl} must be ≥ 15 cm (got {val}).")
    if S_dist is None or S_dist <= 0: errs.append(f"Column spacing S must be > 0 m (got {S_dist}).")
    if q_net is None or q_net < 0.5 or q_net > 5.0:
        errs.append(f"Soil bearing capacity (q_all,net = {q_net} kg/cm²) is outside the realistic engineering range of 0.5 to 5.0 kg/cm².")
    if Fcu is None or Fcu < 150: errs.append(f"Concrete strength Fcu must be ≥ 150 kg/cm² (got {Fcu}).")
    if Fy is None or Fy < 2000:  errs.append(f"Steel yield strength Fy must be ≥ 2000 kg/cm² (got {Fy}).")
    if Fy is not None and Fcu is not None and Fy <= Fcu:
        errs.append(f"Unrealistic material strength: Steel Fy ({Fy} kg/cm²) must be greater than concrete Fcu ({Fcu} kg/cm²).")
    if cover is None or cover < 3 or cover > 15:
        errs.append(f"Concrete Cover must be between 3 and 15 cm (got {cover}).")
    if errs:
        st.error("⚠️ **Illogical Input Detected! Calculation Stopped.**")
        for e in errs:
            st.warning(f"• {e}")
        return

    cover_cm = float(cover)
    phi_cm   = float(Phi) / 10.0

    # ══════════════════════════════════════════════════════════════════════════
    #  3.  INITIAL SIZING & OVERLAP CHECK
    # ══════════════════════════════════════════════════════════════════════════
    L1_auto, B1_auto = _iso_dims(P1, c1, b1, q_net)
    L2_auto, B2_auto = _iso_dims(P2, c2, b2, q_net)

    clearance_m = S_dist - (L1_auto / 200.0 + L2_auto / 200.0)

    if clearance_m >= 0.15:
        mode = "isolated"
    else:
        mode = "combined"

    # Combined auto dims
    Lc_auto, Bc_auto, x1_auto, x2_auto = _combined_dims(
        P1, P2, c1, b1, c2, b2, S_dist, q_net)

    # Auto thickness
    t1_auto = _suggest_t_iso(P1, c1, b1, L1_auto, B1_auto, Fcu, Fy, cover_cm, Phi, q_net)
    t2_auto = _suggest_t_iso(P2, c2, b2, L2_auto, B2_auto, Fcu, Fy, cover_cm, Phi, q_net)
    tc_auto = _suggest_t_combined(P1, P2, c1, b1, c2, b2, S_dist,
                                  Lc_auto, Bc_auto, x1_auto, Fcu, Fy, cover_cm, Phi, q_net)

    # ══════════════════════════════════════════════════════════════════════════
    #  4.  TYPE BANNER
    # ══════════════════════════════════════════════════════════════════════════
    if mode == "isolated":
        st.markdown(
            """<div style="background:#dcfce7;border:2px solid #22c55e;border-radius:12px;
            padding:16px 20px;text-align:center;margin:10px 0 18px;">
            <span style="font-size:28px;">🟢</span>
            <span style="font-size:22px;font-weight:800;color:#166534;">
            النوع المحدد: قواعد منفصلة (ISOLATED FOOTINGS)</span><br>
            <span style="font-size:14px;color:#15803d;">
            Clearance = """ + f"{clearance_m*100:.0f} cm ≥ 15 cm ✅" + """</span>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div style="background:#fff7ed;border:2px solid #f97316;border-radius:12px;
            padding:16px 20px;text-align:center;margin:10px 0 18px;">
            <span style="font-size:28px;">🟠</span>
            <span style="font-size:22px;font-weight:800;color:#9a3412;">
            النوع المحدد: قاعدة مشتركة (COMBINED FOOTING)</span><br>
            <span style="font-size:14px;color:#c2410c;">
            Clearance = """ + f"{clearance_m*100:.0f} cm < 15 cm ⚠️" + """</span>
            </div>""",
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  5.  INTERACTIVE DIMENSION CONTROLS (Moved BEFORE Geometric Sketch)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="section-header">📊 التحكم التفاعلي في الأبعاد '
        '(Interactive Dimension Controls)</div>',
        unsafe_allow_html=True)

    # ── detect input changes → auto-recalculate sizing within active project ──
    active_pname = S.get_active_project_name()
    sig_key = f"_tcf_sig_{active_pname}"
    curr_sig = (float(P1), float(P2), int(c1), int(b1), int(c2), int(b2),
                float(S_dist), float(q_net), float(Fcu), float(Fy), int(cover), int(Phi))
    prev_sig = st.session_state.get(sig_key)

    if prev_sig is None:
        # Initializing project session without clobbering existing saved overrides
        st.session_state[sig_key] = curr_sig
    elif prev_sig != curr_sig:
        # User interactively changed primary input parameters during this project session
        st.session_state[sig_key] = curr_sig
        st.session_state["w_tcf_L1_ov"] = int(L1_auto)
        st.session_state["w_tcf_B1_ov"] = int(B1_auto)
        st.session_state["w_tcf_t1_ov"] = int(t1_auto)
        st.session_state["w_tcf_L2_ov"] = int(L2_auto)
        st.session_state["w_tcf_B2_ov"] = int(B2_auto)
        st.session_state["w_tcf_t2_ov"] = int(t2_auto)
        st.session_state["w_tcf_Lc_ov"] = int(Lc_auto)
        st.session_state["w_tcf_Bc_ov"] = int(Bc_auto)
        st.session_state["w_tcf_tc_ov"] = int(tc_auto)
        S.cfg_set("tcf_L1_ov", int(L1_auto))
        S.cfg_set("tcf_B1_ov", int(B1_auto))
        S.cfg_set("tcf_t1_ov", int(t1_auto))
        S.cfg_set("tcf_L2_ov", int(L2_auto))
        S.cfg_set("tcf_B2_ov", int(B2_auto))
        S.cfg_set("tcf_t2_ov", int(t2_auto))
        S.cfg_set("tcf_Lc_ov", int(Lc_auto))
        S.cfg_set("tcf_Bc_ov", int(Bc_auto))
        S.cfg_set("tcf_tc_ov", int(tc_auto))

    def _save_ov(cfg_k, w_k, default_v):
        val = st.session_state.get(w_k, default_v)
        if val is not None:
            S.cfg_set(cfg_k, int(val))

    with st.expander("📐 Adjust Footing Dimensions (تعديل أبعاد القواعد)", expanded=True):
        if mode == "isolated":
            st.markdown("##### Footing 1 (under C₁)")
            cL1, cB1, ct1 = st.columns(3)

            saved_L1 = S.cfg_val("tcf_L1_ov")
            saved_B1 = S.cfg_val("tcf_B1_ov")
            saved_t1 = S.cfg_val("tcf_t1_ov")
            def_L1 = int(saved_L1) if saved_L1 is not None else int(L1_auto)
            def_B1 = int(saved_B1) if saved_B1 is not None else int(B1_auto)
            def_t1 = int(saved_t1) if saved_t1 is not None else int(t1_auto)

            with cL1:
                L1 = st.number_input("L₁ (cm)", min_value=30, max_value=3000,
                    value=def_L1, step=5, key="w_tcf_L1_ov",
                    on_change=_save_ov, args=("tcf_L1_ov", "w_tcf_L1_ov", L1_auto))
                st.caption(f"💡 Suggested: {L1_auto} cm")
            with cB1:
                B1 = st.number_input("B₁ (cm)", min_value=30, max_value=3000,
                    value=def_B1, step=5, key="w_tcf_B1_ov",
                    on_change=_save_ov, args=("tcf_B1_ov", "w_tcf_B1_ov", B1_auto))
                st.caption(f"💡 Suggested: {B1_auto} cm")
            with ct1:
                t1 = st.number_input("t₁ (cm)", min_value=20, max_value=300,
                    value=def_t1, step=5, key="w_tcf_t1_ov",
                    on_change=_save_ov, args=("tcf_t1_ov", "w_tcf_t1_ov", t1_auto))
                st.caption(f"💡 Suggested: {t1_auto} cm")

            st.markdown("##### Footing 2 (under C₂)")
            cL2, cB2, ct2 = st.columns(3)

            saved_L2 = S.cfg_val("tcf_L2_ov")
            saved_B2 = S.cfg_val("tcf_B2_ov")
            saved_t2 = S.cfg_val("tcf_t2_ov")
            def_L2 = int(saved_L2) if saved_L2 is not None else int(L2_auto)
            def_B2 = int(saved_B2) if saved_B2 is not None else int(B2_auto)
            def_t2 = int(saved_t2) if saved_t2 is not None else int(t2_auto)

            with cL2:
                L2 = st.number_input("L₂ (cm)", min_value=30, max_value=3000,
                    value=def_L2, step=5, key="w_tcf_L2_ov",
                    on_change=_save_ov, args=("tcf_L2_ov", "w_tcf_L2_ov", L2_auto))
                st.caption(f"💡 Suggested: {L2_auto} cm")
            with cB2:
                B2 = st.number_input("B₂ (cm)", min_value=30, max_value=3000,
                    value=def_B2, step=5, key="w_tcf_B2_ov",
                    on_change=_save_ov, args=("tcf_B2_ov", "w_tcf_B2_ov", B2_auto))
                st.caption(f"💡 Suggested: {B2_auto} cm")
            with ct2:
                t2 = st.number_input("t₂ (cm)", min_value=20, max_value=300,
                    value=def_t2, step=5, key="w_tcf_t2_ov",
                    on_change=_save_ov, args=("tcf_t2_ov", "w_tcf_t2_ov", t2_auto))
                st.caption(f"💡 Suggested: {t2_auto} cm")

        else:  # combined
            cL, cB, ct = st.columns(3)

            saved_Lc = S.cfg_val("tcf_Lc_ov")
            saved_Bc = S.cfg_val("tcf_Bc_ov")
            saved_tc = S.cfg_val("tcf_tc_ov")
            def_Lc = int(saved_Lc) if saved_Lc is not None else int(Lc_auto)
            def_Bc = int(saved_Bc) if saved_Bc is not None else int(Bc_auto)
            def_tc = int(saved_tc) if saved_tc is not None else int(tc_auto)

            with cL:
                Lc = st.number_input("L (cm)", min_value=50, max_value=5000,
                    value=def_Lc, step=5, key="w_tcf_Lc_ov",
                    on_change=_save_ov, args=("tcf_Lc_ov", "w_tcf_Lc_ov", Lc_auto))
                st.caption(f"💡 Suggested: {Lc_auto} cm")
            with cB:
                Bc = st.number_input("B (cm)", min_value=30, max_value=3000,
                    value=def_Bc, step=5, key="w_tcf_Bc_ov",
                    on_change=_save_ov, args=("tcf_Bc_ov", "w_tcf_Bc_ov", Bc_auto))
                st.caption(f"💡 Suggested: {Bc_auto} cm")
            with ct:
                tc = st.number_input("t (cm)", min_value=20, max_value=400,
                    value=def_tc, step=5, key="w_tcf_tc_ov",
                    on_change=_save_ov, args=("tcf_tc_ov", "w_tcf_tc_ov", tc_auto))
                st.caption(f"💡 Suggested: {tc_auto} cm")

        if st.button("↺ Reset to Auto-Calculated (العودة للأبعاد المحسوبة تلقائياً)",
                     use_container_width=True, key="tcf_reset_dims"):
            st.session_state["w_tcf_L1_ov"] = int(L1_auto)
            st.session_state["w_tcf_B1_ov"] = int(B1_auto)
            st.session_state["w_tcf_t1_ov"] = int(t1_auto)
            st.session_state["w_tcf_L2_ov"] = int(L2_auto)
            st.session_state["w_tcf_B2_ov"] = int(B2_auto)
            st.session_state["w_tcf_t2_ov"] = int(t2_auto)
            st.session_state["w_tcf_Lc_ov"] = int(Lc_auto)
            st.session_state["w_tcf_Bc_ov"] = int(Bc_auto)
            st.session_state["w_tcf_tc_ov"] = int(tc_auto)
            S.cfg_set("tcf_L1_ov", int(L1_auto))
            S.cfg_set("tcf_B1_ov", int(B1_auto))
            S.cfg_set("tcf_t1_ov", int(t1_auto))
            S.cfg_set("tcf_L2_ov", int(L2_auto))
            S.cfg_set("tcf_B2_ov", int(B2_auto))
            S.cfg_set("tcf_t2_ov", int(t2_auto))
            S.cfg_set("tcf_Lc_ov", int(Lc_auto))
            S.cfg_set("tcf_Bc_ov", int(Bc_auto))
            S.cfg_set("tcf_tc_ov", int(tc_auto))
            st.rerun()

    # ── Re-check overlap after manual edits ──
    if mode == "isolated":
        clr_now = S_dist - (L1 / 200.0 + L2 / 200.0)
        if clr_now < 0.15:
            st.warning(
                f"⚠️ **تداخل بعد التعديل اليدوي:** الخلوص الحالي = {clr_now*100:.0f} cm "
                f"< 15 cm — يُنصح بالتحول لقاعدة مشتركة أو تقليل الأبعاد."
            )
    else:
        # Recalculate combined overhangs based on current Lc
        R_serv_ton = P1 + P2
        x_R_m      = P2 * S_dist / R_serv_ton if R_serv_ton > 0 else S_dist / 2.0
        L_m        = Lc / 100.0
        x1_m       = L_m / 2.0 - x_R_m
        x2_m       = L_m - x1_m - S_dist
        x1_cm      = round(x1_m * 100, 1)
        x2_cm      = round(x2_m * 100, 1)

    # ══════════════════════════════════════════════════════════════════════════
    #  6.  GEOMETRIC SKETCH (Drawn with active updated dimensions)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="section-header">📐 المسقط الهندسي (Geometric Sketch)</div>',
        unsafe_allow_html=True)

    if mode == "isolated":
        fig_pre = _draw_plan("isolated", S_m=S_dist,
                             c1_cm=c1, b1_cm=b1, c2_cm=c2, b2_cm=b2,
                             L1_cm=L1, B1_cm=B1,
                             L2_cm=L2, B2_cm=B2)
    else:
        fig_pre = _draw_plan("combined", S_m=S_dist,
                             c1_cm=c1, b1_cm=b1, c2_cm=c2, b2_cm=b2,
                             Lc_cm=Lc, Bc_cm=Bc,
                             x1_cm=x1_cm, x2_cm=x2_cm)
    st.pyplot(fig_pre, use_container_width=True)
    plt.close(fig_pre)

    # ══════════════════════════════════════════════════════════════════════════
    #  7.  STRUCTURAL ANALYSIS (ECP 203)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="section-header">📊 نتائج التحقق الإنشائي '
        '(Structural Verification — ECP 203)</div>',
        unsafe_allow_html=True)

    Pu1_ton = 1.5 * P1;  Pu2_ton = 1.5 * P2;  Ru_ton = Pu1_ton + Pu2_ton
    tau_s_allow = _shear_allow_kgcm2(Fcu)       # kg/cm²

    # ──────────────────────────────────────────────────────────────────────────
    #  ISOLATED FOOTINGS ANALYSIS
    # ──────────────────────────────────────────────────────────────────────────
    if mode == "isolated":
        results = []
        rft_callouts = {}

        for tag, (P_t, Pu_t, cc, bb, LL, BB, tt) in enumerate([
            (P1, Pu1_ton, c1, b1, L1, B1, t1),
            (P2, Pu2_ton, c2, b2, L2, B2, t2),
        ], start=1):
            A_cm2 = LL * BB
            d_cm  = tt - cover_cm - phi_cm / 2.0

            if d_cm <= 0:
                st.error(f"Footing {tag}: thickness too small (d ≤ 0 cm).")
                return

            P_kg  = P_t * 1000.0
            Pu_kg = Pu_t * 1000.0

            # ── Soil bearing ──
            q_act = 1.05 * P_kg / A_cm2 if A_cm2 > 0 else 999.0  # kg/cm²
            q_ok  = q_act <= q_net
            util_q = q_act / q_net * 100.0

            # ── Ultimate pressure ──
            q_u = Pu_kg / A_cm2 if A_cm2 > 0 else 0.0            # kg/cm²

            # ── One-way shear ──
            cant_L = (LL - cc) / 2.0                             # cm
            cant_B = (BB - bb) / 2.0                             # cm
            a_L = max(cant_L - d_cm / 2.0, 0)
            a_B = max(cant_B - d_cm / 2.0, 0)
            V_L = q_u * BB * a_L                                 # kg
            V_B = q_u * LL * a_B                                 # kg
            V_gov = max(V_L, V_B)
            tau_s = V_gov / (max(BB, LL) * d_cm) if d_cm > 0 else 999.0  # kg/cm²
            s_ok  = tau_s <= tau_s_allow

            # ── Punching shear ──
            ap = cc + d_cm;  bp = bb + d_cm                      # cm
            bo_cm = 2.0 * (ap + bp)
            A_punch = ap * bp                                     # cm²
            Q_p = Pu_kg - q_u * A_punch                          # kg
            tau_p = Q_p / (bo_cm * d_cm) if (bo_cm * d_cm) > 0 else 999.0 # kg/cm²
            tau_p_allow = _punch_allow_kgcm2(Fcu, cc, bb, d_cm, bo_cm)
            p_ok = tau_p <= tau_p_allow

            # ── Bending & reinforcement (both directions) ──
            M_L_kgcm = q_u * BB * (cant_L ** 2) / 2.0            # kg·cm
            M_B_kgcm = q_u * LL * (cant_B ** 2) / 2.0            # kg·cm
            M_L_tm   = M_L_kgcm / 100000.0                       # ton·m
            M_B_tm   = M_B_kgcm / 100000.0                       # ton·m

            As_L = _As_design_cm2(M_L_kgcm, d_cm, BB, Fcu, Fy)   # cm²
            As_B = _As_design_cm2(M_B_kgcm, d_cm, LL, Fcu, Fy)   # cm²
            a_bar_cm2 = math.pi * ((Phi / 10.0) ** 2) / 4.0      # cm²

            B_m = BB / 100.0
            L_m = LL / 100.0
            n_m_L = max(5.0, (As_L / B_m) / a_bar_cm2)           # bars/m
            n_m_B = max(5.0, (As_B / L_m) / a_bar_cm2)           # bars/m

            nL = math.ceil(n_m_L * B_m)
            nB = math.ceil(n_m_B * L_m)
            n_m_L_int = math.ceil(n_m_L)
            n_m_B_int = math.ceil(n_m_B)

            rebar_ok = max(n_m_L_int, n_m_B_int) <= 10

            # ── Collect results ──
            res = dict(
                tag=tag, q_act=q_act, q_ok=q_ok, util_q=util_q,
                tau_s=tau_s, s_ok=s_ok,
                tau_p=tau_p, tau_p_allow=tau_p_allow, p_ok=p_ok,
                M_L_tm=M_L_tm, M_B_tm=M_B_tm,
                M_L_kgcm=M_L_kgcm, M_B_kgcm=M_B_kgcm,
                nL=nL, nB=nB, n_m_L=n_m_L_int, n_m_B=n_m_B_int,
                rebar_ok=rebar_ok,
                d_cm=d_cm, tt=tt, LL=LL, BB=BB, cc=cc, bb=bb,
                As_L_cm2=As_L, As_B_cm2=As_B,
            )
            results.append(res)

            rft_callouts[f"ftg_{tag}_x"] = f"{nL} Φ {Phi} ({n_m_L_int}Φ{Phi}/m)"
            rft_callouts[f"ftg_{tag}_y"] = f"{nB} Φ {Phi} ({n_m_B_int}Φ{Phi}/m)"

        # ── Safety gate ──
        all_safe = True
        for r in results:
            fail_msgs = []
            if not r["q_ok"]:
                fail_msgs.append(f"Footing {r['tag']}: Soil bearing exceeded "
                                 f"(q_act={r['q_act']:.2f} > q_net={q_net:.2f} kg/cm²)")
            if not r["s_ok"]:
                fail_msgs.append(f"Footing {r['tag']}: One-way shear exceeded "
                                 f"(τ={r['tau_s']:.2f} > τ_allow={tau_s_allow:.2f} kg/cm²)")
            if not r["p_ok"]:
                fail_msgs.append(f"Footing {r['tag']}: Punching shear exceeded "
                                 f"(τ_p={r['tau_p']:.2f} > τ_p,allow={r['tau_p_allow']:.2f} kg/cm²)")
            if not r["rebar_ok"]:
                fail_msgs.append(f"Footing {r['tag']}: Rebar congestion > 10 Φ/m")
            if fail_msgs:
                all_safe = False
                st.error("⚠️ **ECP 203 CHECK FAILED:**\n\n" +
                         "\n\n".join(f"• {m}" for m in fail_msgs))

        if not all_safe:
            st.info("💡 قم بزيادة الأبعاد (L, B) أو السمك (t) لتحقيق الأمان الإنشائي.")
            return

        # ── ALL SAFE ──
        st.markdown(
            '<div class="result-ok" style="font-size:0.95rem;text-align:center;">'
            '✅ SAFE DESIGN — ALL ECP 203 CHECKS SATISFIED (Both Footings)</div>',
            unsafe_allow_html=True)

        # ── Design metrics grid ──
        for r in results:
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            _card = lambda col, title, val: col.markdown(
                f"""<div style="background:#f0f4ff;border:1px solid #c8d4f0;border-radius:8px;
                padding:8px 10px;text-align:center;min-height:64px;display:flex;
                flex-direction:column;justify-content:center;">
                <div style="color:#3a4a6b;font-size:0.68rem;font-weight:600;
                text-transform:uppercase;letter-spacing:0.4px;margin-bottom:2px;">{title}</div>
                <div style="color:#1a2340;font-size:0.82rem;font-weight:700;">{val}</div>
                </div>""", unsafe_allow_html=True)
            _card(mc1, f"Footing {r['tag']} Plan", f"{r['LL']}×{r['BB']} cm")
            _card(mc2, "RC Thickness", f"{r['tt']} cm")
            _card(mc3, f"d_eff", f"{r['d_cm']:.1f} cm")
            _card(mc4, "Long Steel", f"{r['nL']}Φ{Phi} ({r['n_m_L']}Φ{Phi}/m)")
            _card(mc5, "Short Steel", f"{r['nB']}Φ{Phi} ({r['n_m_B']}Φ{Phi}/m)")

        # ── Final reinforcement plan ──
        st.markdown("---")
        st.markdown(
            '<div class="section-header">📐 المسقط الإنشائي النهائي مع التسليح '
            '(Final Reinforcement Plan)</div>',
            unsafe_allow_html=True)

        fig_rft = _draw_plan("isolated", S_m=S_dist,
                             c1_cm=c1, b1_cm=b1, c2_cm=c2, b2_cm=b2,
                             L1_cm=L1, B1_cm=B1, L2_cm=L2, B2_cm=B2,
                             rft=rft_callouts)
        st.pyplot(fig_rft, use_container_width=True)

        buf = io.BytesIO()
        fig_rft.savefig(buf, format="png", bbox_inches="tight", dpi=300)
        buf.seek(0)
        st.download_button("📥 Download Plan (PNG)", buf.getvalue(),
                           file_name="ECP203_TwoCol_Isolated_Plan.png",
                           mime="image/png", use_container_width=True, key="dl_iso_plan")
        plt.close(fig_rft)

        # ── Summary table ──
        st.markdown("---")
        st.markdown(
            '<div class="section-header">📋 ملخص التحققات الإنشائية '
            '(Structural Verification Summary)</div>',
            unsafe_allow_html=True)

        rows = []
        for r in results:
            rows.append({
                "Check": f"Ftg {r['tag']} — Soil Bearing (q_act ≤ q_net)",
                "Actual": f"{r['q_act']:.2f} kg/cm²",
                "Allowable": f"{q_net:.2f} kg/cm²",
                "Util (%)": f"{r['util_q']:.1f}%",
                "Status": "✅ Safe" if r['q_ok'] else "❌ Unsafe",
            })
            rows.append({
                "Check": f"Ftg {r['tag']} — One-Way Shear (τ ≤ τ_cu)",
                "Actual": f"{r['tau_s']:.2f} kg/cm²",
                "Allowable": f"{tau_s_allow:.2f} kg/cm²",
                "Util (%)": f"{r['tau_s']/tau_s_allow*100:.1f}%",
                "Status": "✅ Safe" if r['s_ok'] else "❌ Unsafe",
            })
            rows.append({
                "Check": f"Ftg {r['tag']} — Punching Shear (τ_p ≤ τ_cup)",
                "Actual": f"{r['tau_p']:.2f} kg/cm²",
                "Allowable": f"{r['tau_p_allow']:.2f} kg/cm²",
                "Util (%)": f"{r['tau_p']/r['tau_p_allow']*100:.1f}%",
                "Status": "✅ Safe" if r['p_ok'] else "❌ Unsafe",
            })
        render_styled_table(pd.DataFrame(rows))

    # ──────────────────────────────────────────────────────────────────────────
    #  COMBINED FOOTING ANALYSIS
    # ──────────────────────────────────────────────────────────────────────────
    else:
        A_cm2 = Lc * Bc
        d_cm  = tc - cover_cm - phi_cm / 2.0

        if d_cm <= 0:
            st.error("Combined footing thickness too small (d ≤ 0 cm).")
            return

        # Recalculate x1, x2 from CG constraint
        R_serv_ton = P1 + P2
        R_serv_kg  = R_serv_ton * 1000.0
        x_R_m      = P2 * S_dist / R_serv_ton if R_serv_ton > 0 else S_dist / 2.0
        L_m        = Lc / 100.0
        B_m        = Bc / 100.0
        x1_m       = L_m / 2.0 - x_R_m
        x2_m       = L_m - x1_m - S_dist
        x1_cm      = round(x1_m * 100, 1)
        x2_cm      = round(x2_m * 100, 1)

        c1_m = c1 / 100.0; c2_m = c2 / 100.0
        b1_m = b1 / 100.0; b2_m = b2 / 100.0

        # ── Soil bearing ──
        q_act = 1.05 * R_serv_kg / A_cm2 if A_cm2 > 0 else 999.0 # kg/cm²
        q_ok  = q_act <= q_net
        util_q = q_act / q_net * 100.0

        # ── Ultimate loads ──
        Pu1_kg = Pu1_ton * 1000.0
        Pu2_kg = Pu2_ton * 1000.0
        Ru_kg  = Ru_ton  * 1000.0

        q_u    = Ru_kg / A_cm2 if A_cm2 > 0 else 0.0             # kg/cm²
        w_kgcm = Ru_kg / Lc if Lc > 0 else 0.0                   # kg/cm
        w_tonm = Ru_ton / L_m if L_m > 0 else 0.0                # ton/m

        # ── One-way shear at 4 critical sections ──
        xs1 = max((x1_m - c1_m / 2.0) * 100.0 - d_cm / 2.0, 0)
        V1  = w_kgcm * xs1                                       # kg (left cantilever)
        xs2 = max((x2_m - c2_m / 2.0) * 100.0 - d_cm / 2.0, 0)
        V2  = w_kgcm * xs2                                       # kg (right cantilever)
        xm1 = (x1_m + c1_m / 2.0) * 100.0 + d_cm / 2.0
        V3  = abs(w_kgcm * xm1 - Pu1_kg)                         # kg (between cols near C1)
        xm2 = (x1_m + S_dist - c2_m / 2.0) * 100.0 - d_cm / 2.0
        V4  = abs(w_kgcm * xm2 - Pu1_kg)                         # kg (between cols near C2)

        V_gov = max(V1, V2, V3, V4)
        tau_s = V_gov / (Bc * d_cm) if (Bc * d_cm) > 0 else 999.0 # kg/cm²
        s_ok  = tau_s <= tau_s_allow

        # ── Punching shear at both columns ──
        punch_data = []
        for (Pu_k, cc, bb, lbl) in [(Pu1_kg, c1, b1, "C₁"), (Pu2_kg, c2, b2, "C₂")]:
            ap = cc + d_cm; bp = bb + d_cm
            bo_cm = 2.0 * (ap + bp)
            A_punch = ap * bp
            Q_p = Pu_k - q_u * A_punch
            tau_p = Q_p / (bo_cm * d_cm) if (bo_cm * d_cm) > 0 else 999.0
            tau_p_a = _punch_allow_kgcm2(Fcu, cc, bb, d_cm, bo_cm)
            punch_data.append(dict(label=lbl, tau_p=tau_p, tau_p_a=tau_p_a,
                                   p_ok=tau_p <= tau_p_a))

        # ── Bending moments (longitudinal) ──
        # M at face of C1 (left cantilever)
        cant_L1_cm = max((x1_m - c1_m / 2.0) * 100.0, 0)
        M_cant1_kgcm = w_kgcm * (cant_L1_cm ** 2) / 2.0          # kg·cm (sagging → bottom)
        M_cant1_tm   = M_cant1_kgcm / 100000.0                   # ton·m

        # M at face of C2 (right cantilever)
        cant_R2_cm = max((x2_m - c2_m / 2.0) * 100.0, 0)
        M_cant2_kgcm = w_kgcm * (cant_R2_cm ** 2) / 2.0          # kg·cm (sagging → bottom)
        M_cant2_tm   = M_cant2_kgcm / 100000.0                   # ton·m

        # Max moment between columns (at zero-shear point)
        x_zero_cm = Pu1_kg / w_kgcm if w_kgcm > 0 else x1_cm     # from left edge (cm)
        M_mid_kgcm = (w_kgcm * (x_zero_cm ** 2) / 2.0) - Pu1_kg * (x_zero_cm - x1_cm) # kg·cm
        M_mid_tm   = M_mid_kgcm / 100000.0                       # ton·m

        M_bot_max_kgcm = max(M_cant1_kgcm, M_cant2_kgcm, max(M_mid_kgcm, 0))
        M_top_max_kgcm = abs(min(M_mid_kgcm, 0))

        M_bot_max_tm = M_bot_max_kgcm / 100000.0
        M_top_max_tm = M_top_max_kgcm / 100000.0

        # ── Transverse bending ──
        cant_B1_cm = max((Bc - b1) / 2.0, 0)
        cant_B2_cm = max((Bc - b2) / 2.0, 0)
        cant_B_max = max(cant_B1_cm, cant_B2_cm)
        M_trans_kgcm = q_u * 100.0 * (cant_B_max ** 2) / 2.0     # kg·cm per meter strip
        M_trans_tm   = M_trans_kgcm / 100000.0                   # ton·m per meter strip

        # ── Reinforcement ──
        # Longitudinal bottom
        As_bot = _As_design_cm2(M_bot_max_kgcm, d_cm, Bc, Fcu, Fy)
        a_bar_cm2 = math.pi * ((Phi / 10.0) ** 2) / 4.0
        n_m_bot = max(5.0, (As_bot / B_m) / a_bar_cm2)
        n_bot   = math.ceil(n_m_bot * B_m)
        n_m_bot_int = math.ceil(n_m_bot)

        # Longitudinal top (if hogging exists)
        if M_top_max_kgcm > 0:
            As_top = _As_design_cm2(M_top_max_kgcm, d_cm, Bc, Fcu, Fy)
            n_m_top = max(5.0, (As_top / B_m) / a_bar_cm2)
            n_top   = math.ceil(n_m_top * B_m)
            n_m_top_int = math.ceil(n_m_top)
        else:
            As_top = 0.0; n_m_top = 5.0; n_top = math.ceil(5.0 * B_m); n_m_top_int = 5

        # Transverse bottom (per meter and total across L)
        As_trans = _As_design_cm2(M_trans_kgcm, d_cm, 100.0, Fcu, Fy)
        n_m_trans = max(5.0, As_trans / a_bar_cm2)
        n_m_trans_int = math.ceil(n_m_trans)
        n_trans = math.ceil(n_m_trans * L_m)
        As_trans_total = As_trans * L_m

        rebar_ok = max(n_m_bot_int, n_m_top_int, n_m_trans_int) <= 10

        # ── Safety gate ──
        fail_msgs = []
        if not q_ok:
            fail_msgs.append(f"Soil bearing exceeded: q_act={q_act:.2f} > q_net={q_net:.2f} kg/cm²")
        if not s_ok:
            fail_msgs.append(f"One-way shear exceeded: τ={tau_s:.2f} > τ_allow={tau_s_allow:.2f} kg/cm²")
        for pd_ in punch_data:
            if not pd_["p_ok"]:
                fail_msgs.append(f"Punching ({pd_['label']}): τ_p={pd_['tau_p']:.2f} > "
                                 f"τ_p,allow={pd_['tau_p_a']:.2f} kg/cm²")
        if not rebar_ok:
            fail_msgs.append("Rebar congestion > 10 Φ/m — increase thickness.")

        if fail_msgs:
            st.error("⚠️ **ECP 203 CHECK FAILED:**\n\n" +
                     "\n\n".join(f"• {m}" for m in fail_msgs))
            st.info("💡 قم بزيادة الأبعاد (L, B) أو السمك (t) لتحقيق الأمان الإنشائي.")
            return

        # ── ALL SAFE ──
        st.markdown(
            '<div class="result-ok" style="font-size:0.95rem;text-align:center;">'
            '✅ SAFE DESIGN — ALL ECP 203 CHECKS SATISFIED (Combined Footing)</div>',
            unsafe_allow_html=True)

        # ── Design metrics ──
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        _card = lambda col, title, val: col.markdown(
            f"""<div style="background:#f0f4ff;border:1px solid #c8d4f0;border-radius:8px;
            padding:8px 10px;text-align:center;min-height:64px;display:flex;
            flex-direction:column;justify-content:center;">
            <div style="color:#3a4a6b;font-size:0.68rem;font-weight:600;
            text-transform:uppercase;letter-spacing:0.4px;margin-bottom:2px;">{title}</div>
            <div style="color:#1a2340;font-size:0.82rem;font-weight:700;">{val}</div>
            </div>""", unsafe_allow_html=True)
        _card(mc1, "Combined Plan", f"{Lc}×{Bc} cm")
        _card(mc2, "RC Thickness", f"{tc} cm (d={d_cm:.1f} cm)")
        _card(mc3, "Bot. Long. Rft", f"{n_bot}Φ{Phi} ({n_m_bot_int}Φ{Phi}/m)")
        _card(mc4, "Top Long. Rft", f"{n_top}Φ{Phi} ({n_m_top_int}Φ{Phi}/m)")
        _card(mc5, "Trans. Rft", f"{n_trans}Φ{Phi} ({n_m_trans_int}Φ{Phi}/m)")

        # ── Final reinforcement plan ──
        st.markdown("---")
        st.markdown(
            '<div class="section-header">📐 المسقط الإنشائي النهائي مع التسليح '
            '(Final Reinforcement Plan)</div>',
            unsafe_allow_html=True)

        rft_comb = {
            "bot_x": f"{n_bot} Φ {Phi} ({n_m_bot_int}Φ{Phi}/m — {As_bot:.1f} cm²)",
            "top_x": f"{n_top} Φ {Phi} ({n_m_top_int}Φ{Phi}/m — {As_top:.1f} cm²)",
            "trans_y": f"{n_trans} Φ {Phi} ({n_m_trans_int}Φ{Phi}/m — {As_trans_total:.1f} cm²)",
            "trans_top_y": "5Φ10/m",
        }
        fig_rft = _draw_plan("combined", S_m=S_dist,
                             c1_cm=c1, b1_cm=b1, c2_cm=c2, b2_cm=b2,
                             Lc_cm=Lc, Bc_cm=Bc, x1_cm=x1_cm, x2_cm=x2_cm,
                             rft=rft_comb)
        st.pyplot(fig_rft, use_container_width=True)

        buf = io.BytesIO()
        fig_rft.savefig(buf, format="png", bbox_inches="tight", dpi=300)
        buf.seek(0)
        st.download_button("📥 Download Plan (PNG)", buf.getvalue(),
                           file_name="ECP203_TwoCol_Combined_Plan.png",
                           mime="image/png", use_container_width=True, key="dl_comb_plan")
        plt.close(fig_rft)

        # ── Summary table ──
        st.markdown("---")
        st.markdown(
            '<div class="section-header">📋 ملخص التحققات الإنشائية '
            '(Structural Verification Summary)</div>',
            unsafe_allow_html=True)

        rows = [
            {
                "Check": "Soil Bearing (q_act ≤ q_net)",
                "Actual": f"{q_act:.2f} kg/cm²",
                "Allowable": f"{q_net:.2f} kg/cm²",
                "Util (%)": f"{util_q:.1f}%",
                "Status": "✅ Safe" if q_ok else "❌ Unsafe",
            },
            {
                "Check": "One-Way Shear (τ ≤ τ_cu)",
                "Actual": f"{tau_s:.2f} kg/cm²",
                "Allowable": f"{tau_s_allow:.2f} kg/cm²",
                "Util (%)": f"{tau_s/tau_s_allow*100:.1f}%",
                "Status": "✅ Safe" if s_ok else "❌ Unsafe",
            },
        ]
        for pd_ in punch_data:
            rows.append({
                "Check": f"Punching Shear — {pd_['label']} (τ_p ≤ τ_cup)",
                "Actual": f"{pd_['tau_p']:.2f} kg/cm²",
                "Allowable": f"{pd_['tau_p_a']:.2f} kg/cm²",
                "Util (%)": f"{pd_['tau_p']/pd_['tau_p_a']*100:.1f}%",
                "Status": "✅ Safe" if pd_['p_ok'] else "❌ Unsafe",
            })
        render_styled_table(pd.DataFrame(rows))

        # ── Detailed bending moments card ──
        with st.expander("📋 Bending Moments & Reinforcement Details (تفاصيل العزوم والتسليح)", expanded=False):
            df_mom = pd.DataFrame({
                "Parameter": [
                    "Left Cantilever Moment (M_cant1)",
                    "Right Cantilever Moment (M_cant2)",
                    "Mid-span Moment (M_mid) — at zero-shear",
                    "Max Bottom Moment (M_bot_max)",
                    "Max Top Moment (M_top_max)",
                    "Transverse Moment (M_trans) per m",
                    "Bottom Long. Steel (As_bot)",
                    "Top Long. Steel (As_top)",
                    "Transverse Steel per m (As_trans)",
                    "Zero-Shear Point from Left Edge",
                    "x₁ (left overhang)",
                    "x₂ (right overhang)",
                ],
                "Value": [
                    f"{M_cant1_tm:.2f} ton·m ({M_cant1_kgcm:,.0f} kg·cm) [Sagging → Bottom]",
                    f"{M_cant2_tm:.2f} ton·m ({M_cant2_kgcm:,.0f} kg·cm) [Sagging → Bottom]",
                    f"{M_mid_tm:.2f} ton·m ({M_mid_kgcm:,.0f} kg·cm) [{'Hogging → Top' if M_mid_kgcm < 0 else 'Sagging → Bottom'}]",
                    f"{M_bot_max_tm:.2f} ton·m ({M_bot_max_kgcm:,.0f} kg·cm)",
                    f"{M_top_max_tm:.2f} ton·m ({M_top_max_kgcm:,.0f} kg·cm)",
                    f"{M_trans_tm:.2f} ton·m/m ({M_trans_kgcm:,.0f} kg·cm/m)",
                    f"{As_bot:.2f} cm² → {n_bot}Φ{Phi} ({n_m_bot_int}Φ{Phi}/m)",
                    f"{As_top:.2f} cm² → {n_top}Φ{Phi} ({n_m_top_int}Φ{Phi}/m)",
                    f"{As_trans:.2f} cm²/m ({As_trans_total:.2f} cm² total) → {n_trans}Φ{Phi} ({n_m_trans_int}Φ{Phi}/m)",
                    f"{x_zero_cm/100.0:.3f} m ({x_zero_cm:.1f} cm) from left edge",
                    f"{x1_cm:.0f} cm",
                    f"{x2_cm:.0f} cm",
                ],
            })
            render_styled_table(df_mom)

    # ── Design summary ──
    st.markdown("---")
    if mode == "isolated":
        st.info(
            f"📐 **Design Summary:** Two Isolated Footings | "
            f"Ftg 1: **{L1}×{B1} cm** (t={t1} cm) | "
            f"Ftg 2: **{L2}×{B2} cm** (t={t2} cm) | "
            f"Spacing S = {S_dist} m | "
            f"Clearance = {(S_dist - L1/200.0 - L2/200.0)*100:.0f} cm"
        )
    else:
        st.info(
            f"📐 **Design Summary:** Combined Footing **{Lc}×{Bc} cm** (t={tc} cm) | "
            f"x₁={x1_cm:.0f} cm, S={S_dist} m, x₂={x2_cm:.0f} cm | "
            f"Bot: {n_bot}Φ{Phi} | Top: {n_top}Φ{Phi} | Trans: {n_trans}Φ{Phi} ({n_m_trans_int}Φ{Phi}/m)"
        )

    # ── Combined Footing Structural Tutorial Section ──
    _render_structural_tutorial()

