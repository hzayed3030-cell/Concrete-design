"""
Module 3 – Flat Slab Design (ECP 203 – Direct Design Method)
Dynamic Multi-Span System with Configurable Thickness & Rebar Diameters,
Punching Shear Check, Reinforcement Detailing Sketch, and BoQ Estimation.

Axis Conventions:
  Vertical   axes  → Y1, Y2, Y3, …  (left → right)
  Horizontal axes  → X1, X2, X3, …  (bottom → top)
  Lx_spans: horizontal distances between vertical axes  (direction X)
  Ly_spans: vertical   distances between horizontal axes (direction Y)

Units: ton, m, kg, cm, kg/cm²
"""

import io
import base64
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from modules import settings as S
from modules.table_styler import render_styled_table


# ── Constants ────────────────────────────────────────────────────────────────
BAR_DIA = [8, 10, 12, 14, 16, 18, 20, 22, 25]  # mm


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def bar_area(dia_mm):
    """Cross-sectional area of one bar in cm²."""
    return math.pi * (dia_mm / 10.0) ** 2 / 4.0


def bar_unit_weight(dia_mm):
    """Linear weight of rebar in kg/m (formula: dia² / 162)."""
    return (dia_mm ** 2) / 162.0


def round_up_5(v):
    """Round up to nearest 5 cm."""
    return int(math.ceil(v / 5.0) * 5)


def round_up_2(v):
    """Round up to nearest 2 cm."""
    return int(math.ceil(v / 2.0) * 2)


def fmt_steel(As_cm2_total, width_cm, phi_mm):
    """
    Return (n_bars/m, spacing_cm, As_prov_per_m, As_req_per_m) for a strip.
    """
    a_bar    = bar_area(phi_mm)
    As_m     = As_cm2_total / (width_cm / 100.0)   # cm²/m
    n_m      = max(4, math.ceil(As_m / a_bar))    # bars/m
    sp       = min(25.0, round(100.0 / n_m, 1))   # cm spacing
    n_m      = math.ceil(100.0 / sp)
    As_prov  = n_m * a_bar
    return n_m, sp, As_prov, As_m



def _geometry_key(Lx_spans, Ly_spans):
    """Return a hashable key representing the current span geometry, used to detect input changes."""
    return (tuple(round(x, 4) for x in Lx_spans), tuple(round(y, 4) for y in Ly_spans))


def _compute_effective_spans(Lx_spans, Ly_spans, removed_ij_set):
    """
    Given a set of (i, j) positions of removed columns, compute the effective
    Lx and Ly spans that remain active for DDM calculations.

    A Y-axis index i is considered 'inactive' (no support) only when ALL columns
    along that axis are removed. Similarly for X-axis index j.

    Returns (eff_Lx_spans, eff_Ly_spans, active_x_indices, active_y_indices,
             full_axis_x_removed, full_axis_y_removed, ddm_valid_warning).
    """
    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    n_xi = len(x_coords)   # number of Y-axis lines (i indices)
    n_yj = len(y_coords)   # number of X-axis lines (j indices)

    # Count remaining columns per axis line
    remaining_per_xi = {}   # i -> count of remaining cols at that Y-axis
    remaining_per_yj = {}   # j -> count of remaining cols at that X-axis
    for i in range(n_xi):
        remaining_per_xi[i] = n_yj - sum(1 for j in range(n_yj) if (i, j) in removed_ij_set)
    for j in range(n_yj):
        remaining_per_yj[j] = n_xi - sum(1 for i in range(n_xi) if (i, j) in removed_ij_set)

    # Active axis lines: those that still have at least one column
    active_xi = [i for i in range(n_xi) if remaining_per_xi[i] > 0]
    active_yj = [j for j in range(n_yj) if remaining_per_yj[j] > 0]

    # Compute effective spans between consecutive active axis lines
    eff_Lx = [x_coords[active_xi[k+1]] - x_coords[active_xi[k]] for k in range(len(active_xi)-1)]
    eff_Ly = [y_coords[active_yj[k+1]] - y_coords[active_yj[k]] for k in range(len(active_yj)-1)]

    # Detect fully-removed axis lines (for warning)
    full_x_removed = [i for i in range(n_xi) if remaining_per_xi[i] == 0]
    full_y_removed = [j for j in range(n_yj) if remaining_per_yj[j] == 0]

    # DDM validity check: adjacent effective spans ratio must be ≤ 1.33
    ddm_warning = None
    for spans, label in [(eff_Lx, "X"), (eff_Ly, "Y")]:
        for k in range(len(spans)-1):
            ratio = max(spans[k], spans[k+1]) / max(0.001, min(spans[k], spans[k+1]))
            if ratio > 1.33:
                ddm_warning = (
                    f"⚠️ **DDM Span Ratio Warning ({label}-direction):** "
                    f"Adjacent effective spans {spans[k]:.2f}m and {spans[k+1]:.2f}m have ratio "
                    f"{ratio:.2f} > 1.33 (ECP 203 DDM limit). "
                    f"Results are conservative approximations — use FEM for exact analysis."
                )
                break

    return eff_Lx, eff_Ly, active_xi, active_yj, full_x_removed, full_y_removed, ddm_warning


def get_flat_slab_columns(Lx_spans, Ly_spans, bc_cm=30, tc_cm=30, removed_ids=None):
    """
    Generate structured registry of columns C1, C2, ...
    Ordered: left to right (Y axes, i-direction), bottom to top (X axes, j-direction).

    Args:
        Lx_spans:    List of span lengths in X-direction (m).
        Ly_spans:    List of span lengths in Y-direction (m).
        bc_cm:       Column width (cm).
        tc_cm:       Column depth (cm).
        removed_ids: Optional set/list of column IDs to remove (e.g. {"C3", "C7"}).
                     IDs refer to the *original* numbering before any removal.

    Returns:
        active_columns:  List of dicts for remaining columns (re-indexed C1, C2, ...).
        all_columns:     Full list of dicts including removed ones (removed=True flag).
        eff_Lx_spans:    Effective Lx spans for DDM after axis merging.
        eff_Ly_spans:    Effective Ly spans for DDM after axis merging.
        ddm_warning:     String warning if DDM span ratio > 1.33, else None.
    """
    removed_set = set(removed_ids) if removed_ids else set()

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    n_xi = len(x_coords)
    n_yj = len(y_coords)

    # ── Build ALL columns with original IDs ──────────────────────────────────
    all_columns = []
    col_count = 1
    for j, y in enumerate(y_coords):
        for i, x in enumerate(x_coords):
            is_corner = (i in (0, n_xi-1)) and (j in (0, n_yj-1))
            is_edge   = (not is_corner) and (i in (0, n_xi-1) or j in (0, n_yj-1))
            col_type  = "Corner" if is_corner else ("Edge" if is_edge else "Interior")
            orig_id   = f"C{col_count}"
            all_columns.append({
                "id":      orig_id,
                "name":    orig_id,
                "orig_id": orig_id,
                "i": i, "j": j,
                "x": x, "y": y,
                "grid_x": f"Y{i+1}",
                "grid_y": f"X{j+1}",
                "type":   col_type,
                "bc": bc_cm, "tc": tc_cm,
                "removed": orig_id in removed_set,
            })
            col_count += 1

    # ── Build (i, j) removed set for axis analysis ───────────────────────────
    removed_ij = {(c["i"], c["j"]) for c in all_columns if c["removed"]}

    # ── Effective spans & DDM check ───────────────────────────────────────────
    if removed_ij:
        eff_Lx, eff_Ly, active_xi, active_yj, _, _, ddm_warning = _compute_effective_spans(
            Lx_spans, Ly_spans, removed_ij
        )
    else:
        eff_Lx, eff_Ly = list(Lx_spans), list(Ly_spans)
        active_xi = list(range(n_xi))
        active_yj = list(range(n_yj))
        ddm_warning = None

    # ── Re-index active columns and reclassify based on effective boundary ────
    active_columns = [c for c in all_columns if not c["removed"]]
    new_count = 1
    for col in active_columns:
        col["id"]   = f"C{new_count}"
        col["name"] = f"C{new_count}"
        col["i_eff"] = active_xi.index(col["i"]) if col["i"] in active_xi else min(col["i"], len(active_xi)-1)
        col["j_eff"] = active_yj.index(col["j"]) if col["j"] in active_yj else min(col["j"], len(active_yj)-1)
        # Reclassify based on effective grid boundaries
        is_corner_eff = (col["i"] in (active_xi[0], active_xi[-1])) and \
                        (col["j"] in (active_yj[0], active_yj[-1]))
        is_edge_eff   = (not is_corner_eff) and \
                        (col["i"] in (active_xi[0], active_xi[-1]) or
                         col["j"] in (active_yj[0], active_yj[-1]))
        col["type"] = "Corner" if is_corner_eff else ("Edge" if is_edge_eff else "Interior")
        new_count += 1

    return active_columns, all_columns, eff_Lx, eff_Ly, ddm_warning


def get_flat_slab_panels(Lx_spans, Ly_spans, void_ids=None):
    """
    Generate structured registry of panels/bays P(1,1), P(1,2), ...
    Ordered: left to right (i), bottom to top (j).

    Args:
        Lx_spans: List of span lengths in X-direction (m).
        Ly_spans: List of span lengths in Y-direction (m).
        void_ids: Optional set/list of panel IDs marked as voids/openings (e.g. {"P_1_1"}).

    Returns:
        panels: List of dicts representing all panels with bounding geometry and void status.
    """
    void_set = set(void_ids) if void_ids else set()

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    panels = []
    panel_count = 1
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            short_name = f"P({i+1},{j+1})"
            x1, x2 = x_coords[i], x_coords[i+1]
            y1, y2 = y_coords[j], y_coords[j+1]
            lx = Lx_spans[i]
            ly = Ly_spans[j]
            area = lx * ly
            grid_x = f"Y{i+1}-Y{i+2}"
            grid_y = f"X{j+1}-X{j+2}"
            is_void = pid in void_set

            panels.append({
                "id": pid,
                "name": short_name,
                "seq_id": f"P{panel_count}",
                "i": i,
                "j": j,
                "x1": x1, "x2": x2,
                "y1": y1, "y2": y2,
                "mid_x": (x1 + x2) / 2.0,
                "mid_y": (y1 + y2) / 2.0,
                "Lx": lx,
                "Ly": ly,
                "area": area,
                "grid_x": grid_x,
                "grid_y": grid_y,
                "is_void": is_void,
                "label": f"Panel P({i+1},{j+1}) [{grid_x} × {grid_y}] ({lx:.2f}m × {ly:.2f}m — {area:.1f} m²)",
            })
            panel_count += 1

    return panels





# ═══════════════════════════════════════════════════════════════════════════════
#  ① VERIFICATION SKETCH FUNCTION (Input Geometry & Data Card)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_flat_slab_sketch(
    Lx_spans,
    Ly_spans,
    cantilevers,
    ts_initial=20,
    n_floors=1,
    bottom_mesh_dia=12,
    bottom_mesh_n=5,
    top_mesh_dia=10,
    top_mesh_n=5,
    col_extra_dia=12,
    strip_top_extra_dia=12,
    strip_bottom_extra_dia=12,
    concrete_cover=1.5,
    fcu=250,
    fy=4000,
    live_load=0.25,
    flooring_load=0.15,
    wall_load=0.50,
    col_w_cm=30,
    col_d_cm=30,
    removed_col_ids=None,   # set of original col IDs confirmed as removed  e.g. {"C3","C7"}
    pending_col_ids=None,   # set of col IDs selected but not yet confirmed e.g. {"C5"}
    void_panel_ids=None,    # set of panel IDs confirmed as voids e.g. {"P_1_1"}
    pending_void_ids=None,  # set of panel IDs selected as voids for review
):
    """
    Generate the confirmatory geometric sketch for the flat slab with detailed Data Card.
    Dual subplot layout ensures crisp presentation, large bold fonts, and zero text/column overlap.

    removed_col_ids: columns drawn with red cross-out (confirmed deleted).
    pending_col_ids: columns drawn with orange dashed highlight (pending confirmation).
    void_panel_ids: panels drawn with grey fill and diagonal crossed lines (architectural voids/openings).
    """

    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)

    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    # Dual Subplot: Left (Structural Plan ~73%), Right (Data Card ~27%)
    fig = plt.figure(figsize=(16.5, 8.8), dpi=130, facecolor="#ffffff")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.82, 0.68], wspace=0.08, left=0.03, right=0.97, top=0.90, bottom=0.06)
    ax_plan = fig.add_subplot(gs[0, 0])
    ax_card = fig.add_subplot(gs[0, 1])

    # ── 1. STRUCTURAL GEOMETRY PLAN (ax_plan) ──
    ax_plan.set_facecolor("#ffffff")

    # Slab boundary
    slab_rect = patches.Rectangle(
        (x_slab_min, y_slab_min), slab_w, slab_h,
        linewidth=2.5, edgecolor="#0f172a", facecolor="#e8f0fe", zorder=1
    )
    ax_plan.add_patch(slab_rect)

    # Cantilever shading
    cant_color = "#c7dcfb"
    if cant_left > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_slab_min), cant_left, slab_h,
            linewidth=1.2, edgecolor="#1d4ed8", facecolor=cant_color, alpha=0.5, linestyle="--", zorder=2
        ))
    if cant_right > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_coords[-1], y_slab_min), cant_right, slab_h,
            linewidth=1.2, edgecolor="#1d4ed8", facecolor=cant_color, alpha=0.5, linestyle="--", zorder=2
        ))
    if cant_bottom > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_slab_min), slab_w, cant_bottom,
            linewidth=1.2, edgecolor="#1d4ed8", facecolor=cant_color, alpha=0.5, linestyle="--", zorder=2
        ))
    if cant_top > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_coords[-1]), slab_w, cant_top,
            linewidth=1.2, edgecolor="#1d4ed8", facecolor=cant_color, alpha=0.5, linestyle="--", zorder=2
        ))

    # Voids / Openings (المناور والفراغات المعمارية)
    _voids = set(void_panel_ids) if void_panel_ids else set()
    _pending_voids = set(pending_void_ids) if pending_void_ids else set()
    all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _voids)

    for p in all_panels:
        if p["is_void"]:
            # Confirmed Void (Grey with diagonal crossed X lines)
            v_rect = patches.Rectangle(
                (p["x1"], p["y1"]), p["Lx"], p["Ly"],
                linewidth=2.0, edgecolor="#64748b", facecolor="#cbd5e1", zorder=2
            )
            ax_plan.add_patch(v_rect)
            ax_plan.plot([p["x1"], p["x2"]], [p["y1"], p["y2"]], color="#64748b", linestyle="--", linewidth=1.8, zorder=2)
            ax_plan.plot([p["x1"], p["x2"]], [p["y2"], p["y1"]], color="#64748b", linestyle="--", linewidth=1.8, zorder=2)
            ax_plan.text(
                p["mid_x"], p["mid_y"], f"VOID (منور)\n{p['area']:.1f} m²",
                ha="center", va="center", fontsize=11.5, weight="bold", color="#0f172a",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#f1f5f9", edgecolor="#64748b", lw=1.5),
                zorder=3
            )
        elif p["id"] in _pending_voids:
            # Pending Void in review mode (Orange dashed border and cross)
            pv_rect = patches.Rectangle(
                (p["x1"], p["y1"]), p["Lx"], p["Ly"],
                linewidth=2.2, edgecolor="#ea580c", facecolor="#ffedd5", linestyle="--", alpha=0.85, zorder=2
            )
            ax_plan.add_patch(pv_rect)
            ax_plan.plot([p["x1"], p["x2"]], [p["y1"], p["y2"]], color="#ea580c", linestyle="--", linewidth=1.8, zorder=2)
            ax_plan.plot([p["x1"], p["x2"]], [p["y2"], p["y1"]], color="#ea580c", linestyle="--", linewidth=1.8, zorder=2)
            ax_plan.text(
                p["mid_x"], p["mid_y"], "PENDING VOID\n(قيد الحذف)",
                ha="center", va="center", fontsize=11.5, weight="bold", color="#c2410c",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff7ed", edgecolor="#ea580c", lw=1.5),
                zorder=3
            )

    # Grid bubble offsets
    bubble_radius = max(0.35, min(slab_w, slab_h) * 0.038)
    offset_grid_top = max(1.5, slab_h * 0.14)
    offset_grid_left = max(1.5, slab_w * 0.14)

    # Vertical Grid Axes (Y1, Y2, ...) with Top CAD Bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        y_bot_ext = y_slab_min - 0.4
        ax_plan.plot([x, x], [y_bot_ext, y_top_ext], color="#dc2626", linestyle="--", linewidth=1.2, alpha=0.8, zorder=2)
        bubble = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=1.6, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x, y_top_ext, f"Y{idx + 1}", color="#991b1b", fontsize=11.5, weight="bold", ha="center", va="center", zorder=7)

    # Horizontal Grid Axes (X1, X2, ...) with Left CAD Bubbles
    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        x_right_ext = x_slab_max + 0.4
        ax_plan.plot([x_left_ext, x_right_ext], [y, y], color="#dc2626", linestyle="--", linewidth=1.2, alpha=0.8, zorder=2)
        bubble = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=1.6, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x_left_ext, y, f"X{idx + 1}", color="#991b1b", fontsize=11.5, weight="bold", ha="center", va="center", zorder=7)

    # Columns at axis intersections — with removal state visualisation
    col_w_m = max(col_w_cm / 100.0, slab_w * 0.05)
    col_d_m = max(col_d_cm / 100.0, slab_h * 0.05)
    col_count = 1
    _removed = set(removed_col_ids) if removed_col_ids else set()
    _pending = set(pending_col_ids)  if pending_col_ids  else set()

    # Build re-indexed labels: skip removed columns, count only actives
    # First pass: assign original IDs and determine which are active
    orig_to_info = {}
    temp = 1
    for j_idx, y in enumerate(y_coords):
        for i_idx, x in enumerate(x_coords):
            orig_to_info[f"C{temp}"] = {"x": x, "y": y, "i": i_idx, "j": j_idx}
            temp += 1

    # Second pass: assign new labels to non-removed columns
    new_label = {}
    new_num = 1
    for orig_id in sorted(orig_to_info.keys(), key=lambda c: int(c[1:])):
        if orig_id not in _removed:
            new_label[orig_id] = f"C{new_num}"
            new_num += 1
        else:
            new_label[orig_id] = None  # removed

    # Draw columns
    for orig_id, info in orig_to_info.items():
        x, y = info["x"], info["y"]
        is_removed = orig_id in _removed
        is_pending = orig_id in _pending
        label = new_label.get(orig_id)

        if is_removed:
            # Completely omitted / removed from drawing after confirmation
            continue
        elif is_pending:
            # Orange dashed border — selected in review stage before confirmation
            col_rect = patches.Rectangle(
                (x - col_w_m / 2.0, y - col_d_m / 2.0),
                col_w_m, col_d_m,
                linewidth=2.5, edgecolor="#f97316", facecolor="#fed7aa",
                alpha=0.80, zorder=4, linestyle="--"
            )
            ax_plan.add_patch(col_rect)
            ax_plan.text(
                x, y, f"{orig_id}\n?",
                color="#c2410c", fontsize=9.5, weight="bold", ha="center", va="center", zorder=5
            )
        else:
            # Normal active column
            col_rect = patches.Rectangle(
                (x - col_w_m / 2.0, y - col_d_m / 2.0),
                col_w_m, col_d_m,
                linewidth=1.5, edgecolor="#0f172a", facecolor="#1e293b", zorder=4
            )
            ax_plan.add_patch(col_rect)
            display_id = label if label else orig_id
            ax_plan.text(
                x, y, display_id,
                color="#facc15", fontsize=11, weight="bold", ha="center", va="center", zorder=5
            )


    # Span Dimensions (Lx along Bottom)
    dim_offset_bot = max(1.0, slab_h * 0.10)
    y_dim_lx = y_slab_min - dim_offset_bot
    for i, lx in enumerate(Lx_spans):
        mid_x = (x_coords[i] + x_coords[i + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_coords[i + 1], y_dim_lx), xytext=(x_coords[i], y_dim_lx),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_coords[i], x_coords[i]], [y_dim_lx - 0.2, y_dim_lx + 0.2], color="#0f172a", lw=1.3)
        ax_plan.plot([x_coords[i+1], x_coords[i+1]], [y_dim_lx - 0.2, y_dim_lx + 0.2], color="#0f172a", lw=1.3)
        ax_plan.text(
            mid_x, y_dim_lx - 0.30, f"{lx:.2f} m",
            color="#0f172a", fontsize=12, weight="bold", ha="center", va="top"
        )

    # Span Dimensions (Ly along Right)
    dim_offset_right = max(1.0, slab_w * 0.10)
    x_dim_ly = x_slab_max + dim_offset_right
    for j, ly in enumerate(Ly_spans):
        mid_y = (y_coords[j] + y_coords[j + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_dim_ly, y_coords[j + 1]), xytext=(x_dim_ly, y_coords[j]),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_dim_ly - 0.2, x_dim_ly + 0.2], [y_coords[j], y_coords[j]], color="#0f172a", lw=1.3)
        ax_plan.plot([x_dim_ly - 0.2, x_dim_ly + 0.2], [y_coords[j+1], y_coords[j+1]], color="#0f172a", lw=1.3)
        ax_plan.text(
            x_dim_ly + 0.30, mid_y, f"{ly:.2f} m",
            color="#0f172a", fontsize=12, weight="bold", ha="left", va="center"
        )

    # Cantilever annotations
    cant_style = dict(color="#1d4ed8", fontsize=10.5, ha="center", va="center", weight="bold")
    if cant_left > 0:
        ax_plan.text(x_slab_min + cant_left / 2.0, (y_coords[0] + y_coords[-1]) / 2.0, f"Cant.\n{cant_left:.2f}m", **cant_style)
    if cant_right > 0:
        ax_plan.text(x_coords[-1] + cant_right / 2.0, (y_coords[0] + y_coords[-1]) / 2.0, f"Cant.\n{cant_right:.2f}m", **cant_style)
    if cant_bottom > 0:
        ax_plan.text((x_coords[0] + x_coords[-1]) / 2.0, y_slab_min + cant_bottom / 2.0, f"Cant. {cant_bottom:.2f}m", **cant_style)
    if cant_top > 0:
        ax_plan.text((x_coords[0] + x_coords[-1]) / 2.0, y_coords[-1] + cant_top / 2.0, f"Cant. {cant_top:.2f}m", **cant_style)

    # Bounds & Aspect
    margin_left = offset_grid_left + bubble_radius * 2 + 0.6
    margin_right = dim_offset_right + 1.4
    margin_top = offset_grid_top + bubble_radius * 2 + 0.6
    margin_bot = dim_offset_bot + 1.0
    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.axis("off")

    # ── 2. DATA CARD (ax_card) ──
    ax_card.set_facecolor("#ffffff")
    ax_card.axis("off")
    ax_card.set_xlim(0, 1)
    ax_card.set_ylim(0, 1)

    card_bg = FancyBboxPatch(
        (0.01, 0.01), 0.98, 0.98,
        boxstyle="round,pad=0.03,rounding_size=0.04",
        linewidth=2.0,
        edgecolor="#1e3a8a",
        facecolor="#f8fafc",
        zorder=1
    )
    ax_card.add_patch(card_bg)

    banner = FancyBboxPatch(
        (0.03, 0.88), 0.94, 0.09,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        linewidth=1.0,
        edgecolor="#1e3a8a",
        facecolor="#1e3a8a",
        zorder=2
    )
    ax_card.add_patch(banner)
    ax_card.text(
        0.50, 0.925, "DATA CARD & DESIGN PARAMETERS",
        ha="center", va="center",
        fontsize=14.0, weight="bold", color="#ffffff", zorder=3
    )

    fcu_kg = fcu if fcu > 100 else fcu * 10.0
    fy_kg = fy if fy > 100 else fy * 10.0
    avg_rebar_dia_cm = bottom_mesh_dia / 10.0
    d_eff_sketch = ts_initial - concrete_cover - (avg_rebar_dia_cm / 2.0)

    rows = [
        ("Slab Thickness (ts)", f"{ts_initial:.0f} cm  (d = {d_eff_sketch:.1f} cm)", "#0f172a"),
        ("No. of Floors", f"{n_floors} Floors (طوابق)", "#1e40af"),
        ("Concrete Cover", f"{concrete_cover:.1f} cm  (15 mm)", "#334155"),
        ("Bottom Mesh (B1, B2)", f"{bottom_mesh_n} Φ {bottom_mesh_dia} / m'", "#1d4ed8"),
        ("Top Mesh (T1, T2)", f"{top_mesh_n} Φ {top_mesh_dia} / m'", "#1d4ed8"),
        ("Col Extra Top Φ", f"Φ {col_extra_dia} mm", "#15803d"),
        ("Strip Extra Top / Btm", f"Φ {strip_top_extra_dia} / Φ {strip_bottom_extra_dia} mm", "#15803d"),
        ("Materials (fcu / fy)", f"{int(fcu_kg)} / {int(fy_kg)} kg/cm²", "#334155"),
        ("Superimposed DL (SDL)", f"{flooring_load:.2f} t/m²", "#b45309"),
        ("Wall Load (WL)", f"{wall_load:.2f} t/m²", "#b45309"),
        ("Live Load (LL)", f"{live_load:.2f} t/m²", "#b45309"),
        ("Column Size (bc × tc)", f"{col_w_cm:.0f} × {col_d_cm:.0f} cm", "#0f172a"),
    ]

    y_pos = 0.835
    y_step = 0.064

    for idx, (label, val, val_color) in enumerate(rows):
        if idx % 2 == 0:
            row_bg = patches.Rectangle(
                (0.03, y_pos - 0.020), 0.94, y_step * 0.88,
                facecolor="#edf2f7", edgecolor="none", zorder=2
            )
            ax_card.add_patch(row_bg)

        ax_card.text(
            0.04, y_pos + 0.005, label,
            ha="left", va="center",
            fontsize=10.2, weight="bold", color="#475569", zorder=3
        )
        ax_card.text(
            0.48, y_pos + 0.005, ":",
            ha="center", va="center",
            fontsize=10.2, weight="bold", color="#64748b", zorder=3
        )
        ax_card.text(
            0.96, y_pos + 0.005, val,
            ha="right", va="center",
            fontsize=10.5, weight="bold", color=val_color, zorder=3
        )
        y_pos -= y_step

    n_cols_total  = len(x_coords) * len(y_coords)
    n_removed_now = len(_removed)
    n_active      = n_cols_total - n_removed_now
    removal_note  = f" | {n_removed_now} Removed → {n_active} Active" if n_removed_now else ""
    n_voids_now   = len(_voids)
    void_note     = f" | {n_voids_now} Voids (مناور)" if n_voids_now else ""
    fig.suptitle(
        f"Flat Slab — Structural Geometry & Verification Sketch "
        f"({len(Lx_spans)}×{len(Ly_spans)} Spans | {n_cols_total} Cols{removal_note}{void_note} | {slab_w:.2f}×{slab_h:.2f} m)",
        fontsize=14, weight="bold", y=0.96, color="#0f172a"
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  ② TOP REINFORCEMENT & STRUCTURAL LAYOUT SKETCH (الحديد العلوي والإضافي)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_flat_slab_top_rft_sketch(
    Lx_spans,
    Ly_spans,
    cantilevers,
    ts_cm,
    mesh_top_str,
    top_extra_cols,
    cant_rft_list,
    col_w_cm=30,
    col_d_cm=30,
    removed_cols=None,
    void_panel_ids=None,
):
    """
    Generate the full-width engineering Top Reinforcement Drawing (المخطط الإنشائي للحديد العلوي).
    - Top Mesh (الشبكة العلوية الأساسية T1, T2).
    - Column Top Extra Steel (الحديد الإضافي العلوي فوق الأعمدة) in Green (🟢) with hatched zones & callouts.
    - Cantilever Shawka Reinforcement (تسليح الكوابيل والشوكة).
    - Dedicated CAD Title Block for Top Steel details.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)

    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    # Grid bubble offsets & margins
    bubble_radius = max(0.44, min(slab_w, slab_h) * 0.034)
    offset_grid_top = max(1.8, slab_h * 0.10)
    offset_grid_left = max(1.8, slab_w * 0.10)
    dim_offset_bot = max(1.6, slab_h * 0.10)
    dim_offset_right = max(1.5, slab_w * 0.08)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.6
    margin_right = dim_offset_right + 1.2
    margin_top = offset_grid_top + bubble_radius * 2 + 0.6
    margin_bot = dim_offset_bot + 1.2

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.5
    target_plan_w = target_plan_h * ar_plan
    legend_h = 4.2

    fig_w = max(24.0, min(36.0, target_plan_w + 1.6))
    fig_h = max(18.0, min(36.0, target_plan_h + legend_h + 1.2))

    plan_ratio = (fig_h - legend_h - 1.0) / fig_h
    legend_ratio = legend_h / fig_h

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=150, facecolor="#ffffff")
    gs = fig.add_gridspec(
        2, 1,
        height_ratios=[plan_ratio, legend_ratio],
        hspace=0.04,
        left=0.02, right=0.98, top=0.95, bottom=0.02
    )

    ax_plan = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])

    # ── 1. FULL WIDTH REINFORCEMENT PLAN (ax_plan) ───────────────────────────
    ax_plan.set_facecolor("#ffffff")

    # Slab boundary
    slab_rect = patches.Rectangle(
        (x_slab_min, y_slab_min), slab_w, slab_h,
        linewidth=4.0, edgecolor="#0f172a", facecolor="#f8fafc", zorder=1
    )
    ax_plan.add_patch(slab_rect)

    # Cantilever shading
    cant_color = "#e0e7ff"
    if cant_left > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_slab_min), cant_left, slab_h,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.45, linestyle="--", zorder=2
        ))
    if cant_right > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_coords[-1], y_slab_min), cant_right, slab_h,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.45, linestyle="--", zorder=2
        ))
    if cant_bottom > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_slab_min), slab_w, cant_bottom,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.45, linestyle="--", zorder=2
        ))
    if cant_top > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_coords[-1]), slab_w, cant_top,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.45, linestyle="--", zorder=2
        ))

    # Voids / Openings (المناور والفراغات المعمارية)
    _voids = set(void_panel_ids) if void_panel_ids else set()
    all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _voids)
    for p in all_panels:
        if p["is_void"]:
            v_rect = patches.Rectangle(
                (p["x1"], p["y1"]), p["Lx"], p["Ly"],
                linewidth=2.4, edgecolor="#64748b", facecolor="#cbd5e1", zorder=2
            )
            ax_plan.add_patch(v_rect)
            ax_plan.plot([p["x1"], p["x2"]], [p["y1"], p["y2"]], color="#64748b", linestyle="--", linewidth=2.0, zorder=2)
            ax_plan.plot([p["x1"], p["x2"]], [p["y2"], p["y1"]], color="#64748b", linestyle="--", linewidth=2.0, zorder=2)
            ax_plan.text(
                p["mid_x"], p["mid_y"], f"VOID (منور)\n{p['area']:.1f} m²",
                ha="center", va="center", fontsize=15.0, weight="bold", color="#0f172a",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#f1f5f9", edgecolor="#64748b", lw=1.8),
                zorder=4
            )

    # Vertical Grid Axes (Y1, Y2, ...) with Top CAD Bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        y_bot_ext = y_slab_min - 0.6
        ax_plan.plot([x, x], [y_bot_ext, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=2)
        bubble = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x, y_top_ext, f"Y{idx + 1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    # Horizontal Grid Axes (X1, X2, ...) with Left CAD Bubbles
    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        x_right_ext = x_slab_max + 0.6
        ax_plan.plot([x_left_ext, x_right_ext], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=2)
        bubble = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x_left_ext, y, f"X{idx + 1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    col_w_m = max(col_w_cm / 100.0, slab_w * 0.045)
    col_d_m = max(col_d_cm / 100.0, slab_h * 0.045)
    min_span_x = min(Lx_spans) if Lx_spans else 6.0
    min_span_y = min(Ly_spans) if Ly_spans else 6.0

    # 🟢 1. TOP EXTRA STEEL @ COLUMNS (GREEN)
    for col_data in top_extra_cols:
        x, y = col_data["x"], col_data["y"]
        cid = col_data["id"]
        n_ext = col_data["n_extra"]
        dia_ext = col_data["dia_extra"]
        l_ext = col_data["L_extra"]
        is_needed = col_data["is_needed"]
        i_idx = col_data.get("i", 0)
        j_idx = col_data.get("j", 0)

        # Top Extra Rebar Hatch Zone (Green //)
        patch_w = min(max(l_ext * 0.65, col_w_m + 0.9), min_span_x * 0.44)
        patch_h = min(max(l_ext * 0.50, col_d_m + 0.9), min_span_y * 0.44)

        if is_needed and n_ext > 0:
            extra_box = patches.Rectangle(
                (x - patch_w / 2.0, y - patch_h / 2.0),
                patch_w, patch_h,
                linewidth=1.8, edgecolor="#16a34a", facecolor="#dcfce7",
                linestyle="--", alpha=0.55, hatch="//", zorder=3
            )
            ax_plan.add_patch(extra_box)

            # Alternating (Staggered) badge placement: checkerboard parity (i + j) % 2
            parity = (i_idx + j_idx) % 2
            if parity == 0:
                tag_y = y + patch_h / 2.0 + 0.24
                va_mode = "bottom"
            else:
                tag_y = y - patch_h / 2.0 - 0.24
                va_mode = "top"

            ax_plan.text(
                x, tag_y,
                f"+{n_ext}Φ{dia_ext} Top (L={l_ext:.2f}m)",
                color="#14532d", fontsize=13.5, ha="center", va=va_mode,
                weight="bold",
                bbox=dict(boxstyle="round,pad=0.30", facecolor="#ffffff", edgecolor="#16a34a", lw=1.6, alpha=0.98),
                zorder=6
            )

        # Column Box
        col_box = patches.Rectangle(
            (x - col_w_m / 2.0, y - col_d_m / 2.0),
            col_w_m, col_d_m,
            linewidth=2.2, edgecolor="#0f172a", facecolor="#1e293b", zorder=4
        )
        ax_plan.add_patch(col_box)
        ax_plan.text(x, y, cid, color="#facc15", fontsize=16.0, ha="center", va="center", weight="bold", zorder=5)

    # Span Dimensions (Lx along Bottom)
    y_dim_lx = y_slab_min - dim_offset_bot
    for i, lx in enumerate(Lx_spans):
        mid_x = (x_coords[i] + x_coords[i + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_coords[i + 1], y_dim_lx), xytext=(x_coords[i], y_dim_lx),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_coords[i], x_coords[i]], [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.plot([x_coords[i+1], x_coords[i+1]], [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.text(
            mid_x, y_dim_lx - 0.45, f"{lx:.2f} m",
            color="#0f172a", fontsize=16.5, weight="bold", ha="center", va="top"
        )

    # Span Dimensions (Ly along Right)
    dim_offset_right = max(1.6, slab_w * 0.10)
    x_dim_ly = x_slab_max + dim_offset_right
    for j, ly in enumerate(Ly_spans):
        mid_y = (y_coords[j] + y_coords[j + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_dim_ly, y_coords[j + 1]), xytext=(x_dim_ly, y_coords[j]),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j], y_coords[j]], color="#0f172a", lw=1.8)
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j+1], y_coords[j+1]], color="#0f172a", lw=1.8)
        ax_plan.text(
            x_dim_ly + 0.45, mid_y, f"{ly:.2f} m",
            color="#0f172a", fontsize=16.5, weight="bold", ha="left", va="center"
        )

    # Cantilever Callouts (with clean non-overlapping leaders)
    for cant in cant_rft_list:
        side = cant["side"]
        lc = cant["length"]
        rft = cant["rft_callout"]
        ext_l = cant["ext_length"]
        if lc > 0:
            if side == "left":
                ax_plan.annotate(
                    f"Shawka: {rft}\n(Ext = {ext_l:.2f}m inside)",
                    xy=(x_slab_min + lc / 2.0, (y_slab_min + y_slab_max) / 2.0),
                    xytext=(x_slab_min - 3.0, (y_slab_min + y_slab_max) / 2.0),
                    arrowprops=dict(arrowstyle="->", color="#4338ca", lw=2.2),
                    fontsize=13.5, weight="bold", color="#4338ca", ha="right", va="center",
                    bbox=dict(boxstyle="round,pad=0.30", facecolor="#e0e7ff", edgecolor="#4f46e5", lw=1.6),
                    zorder=7
                )
            elif side == "top":
                ax_plan.annotate(
                    f"Shawka: {rft} (Ext={ext_l:.2f}m inside)",
                    xy=((x_slab_min + x_slab_max) / 2.0, y_coords[-1] + lc / 2.0),
                    xytext=((x_slab_min + x_slab_max) / 2.0, y_slab_max + 1.5),
                    arrowprops=dict(arrowstyle="->", color="#4338ca", lw=2.2),
                    fontsize=13.5, weight="bold", color="#4338ca", ha="center", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.30", facecolor="#e0e7ff", edgecolor="#4f46e5", lw=1.6),
                    zorder=7
                )
            elif side == "right":
                ax_plan.annotate(
                    f"Shawka: {rft} (Ext={ext_l:.2f}m)",
                    xy=(x_coords[-1] + lc / 2.0, (y_slab_min + y_slab_max) / 2.0),
                    xytext=(x_slab_max + 3.0, (y_slab_min + y_slab_max) / 2.0),
                    arrowprops=dict(arrowstyle="->", color="#4338ca", lw=2.2),
                    fontsize=13.5, weight="bold", color="#4338ca", ha="left", va="center",
                    bbox=dict(boxstyle="round,pad=0.30", facecolor="#e0e7ff", edgecolor="#4f46e5", lw=1.6),
                    zorder=7
                )
            elif side == "bottom":
                ax_plan.annotate(
                    f"Shawka: {rft} (Ext={ext_l:.2f}m)",
                    xy=((x_slab_min + x_slab_max) / 2.0, y_slab_min + lc / 2.0),
                    xytext=((x_slab_min + x_slab_max) / 2.0, y_slab_min - 1.8),
                    arrowprops=dict(arrowstyle="->", color="#4338ca", lw=2.2),
                    fontsize=13.5, weight="bold", color="#4338ca", ha="center", va="top",
                    bbox=dict(boxstyle="round,pad=0.30", facecolor="#e0e7ff", edgecolor="#4f46e5", lw=1.6),
                    zorder=7
                )

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.axis("off")

    # ── 2. ENGINEERING TITLE BLOCK & COLOR LEGEND (ax_legend) ────────────────
    ax_legend.set_facecolor("#ffffff")
    ax_legend.axis("off")
    ax_legend.set_xlim(0, 1)
    ax_legend.set_ylim(0, 1)

    legend_bg = FancyBboxPatch(
        (0.005, 0.02), 0.99, 0.96,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        linewidth=2.4, edgecolor="#0f172a", facecolor="#f8fafc", zorder=1
    )
    ax_legend.add_patch(legend_bg)

    cards_info = [
        ("TOP REINFORCEMENT\n(الحديد العلوي الأساسي)", f"Base Mesh: {mesh_top_str} (T1, T2)\nContinuous across full slab area", "#15803d", "#dcfce7", "#16a34a"),
        ("TOP EXTRA @ COLUMNS\n(إضافي الأعمدة)", "High-Yield Rebar over columns\nCut length L ≈ 0.30L from each side", "#15803d", "#dcfce7", "#16a34a"),
        ("CANTILEVERS\n(تسليح الكوابيل)", "Shawka RFT (الشوكة الرئيسية)\nExtends 1.5 L_cant inside slab", "#b45309", "#fef3c7", "#d97706"),
        ("CODE NOTES (ECP 203)\n(ملاحظات الكود)", "Perimeter: U-Pins Φ10@20cm + 2Φ12\nLap Splice >= 50Φ | Cover = 15mm", "#0f172a", "#f1f5f9", "#64748b"),
    ]

    x_box_w = 0.235
    x_box_gap = 0.012
    x_start = 0.015

    for k, (title, content, t_color, bg_color, border_color) in enumerate(cards_info):
        bx = x_start + k * (x_box_w + x_box_gap)
        ibox = FancyBboxPatch(
            (bx, 0.04), x_box_w, 0.92,
            boxstyle="round,pad=0.015,rounding_size=0.02",
            linewidth=1.6, edgecolor=border_color, facecolor=bg_color, zorder=2
        )
        ax_legend.add_patch(ibox)
        ax_legend.text(
            bx + x_box_w / 2.0, 0.74, title,
            ha="center", va="center", fontsize=16.5, weight="bold", color=t_color, linespacing=1.2, zorder=3
        )
        ax_legend.text(
            bx + x_box_w / 2.0, 0.28, content,
            ha="center", va="center", fontsize=19.6, color="#1e293b", weight="normal", linespacing=1.22, zorder=3
        )

    fig.suptitle(
        f"TOP REINFORCEMENT & STRUCTURAL LAYOUT PLAN (المخطط الإنشائي للحديد العلوي والإضافي فوق الأعمدة — ts = {ts_cm:.0f} cm)",
        fontsize=20, weight="bold", y=0.98, color="#0f172a"
    )

    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  ③ BOTTOM REINFORCEMENT & STRUCTURAL LAYOUT SKETCH (الحديد السفلي والإضافي)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_flat_slab_bottom_rft_sketch(
    Lx_spans,
    Ly_spans,
    cantilevers,
    ts_cm,
    mesh_btm_str,
    btm_extra_spans,
    col_w_cm=30,
    col_d_cm=30,
    removed_cols=None,
    void_panel_ids=None,
    direction="both",   # "X", "Y", or "both"
):
    """
    Generate the full-width engineering Bottom Reinforcement Drawing (المخطط الإنشائي للحديد السفلي).
    - Bottom Mesh (الشبكة السفلية الأساسية B1, B2).
    - Bottom Extra Steel in Enlarged / High-Moment Bays in Blue (🔵) with hatched zones & callouts.
    - `direction` filters which extra-steel items to draw: "X", "Y", or "both".
    - Dedicated CAD Title Block for Bottom Steel details.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)

    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    # Grid bubble offsets & margins
    bubble_radius = max(0.44, min(slab_w, slab_h) * 0.034)
    offset_grid_top = max(1.8, slab_h * 0.10)
    offset_grid_left = max(1.8, slab_w * 0.10)
    dim_offset_bot = max(1.6, slab_h * 0.10)
    dim_offset_right = max(1.5, slab_w * 0.08)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.6
    margin_right = dim_offset_right + 1.2
    margin_top = offset_grid_top + bubble_radius * 2 + 0.6
    margin_bot = dim_offset_bot + 1.2

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.5
    target_plan_w = target_plan_h * ar_plan
    legend_h = 4.2

    fig_w = max(24.0, min(36.0, target_plan_w + 1.6))
    fig_h = max(18.0, min(36.0, target_plan_h + legend_h + 1.2))

    plan_ratio = (fig_h - legend_h - 1.0) / fig_h
    legend_ratio = legend_h / fig_h

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=150, facecolor="#ffffff")
    gs = fig.add_gridspec(
        2, 1,
        height_ratios=[plan_ratio, legend_ratio],
        hspace=0.04,
        left=0.02, right=0.98, top=0.95, bottom=0.02
    )

    ax_plan = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])

    # ── 1. FULL WIDTH REINFORCEMENT PLAN (ax_plan) ───────────────────────────
    ax_plan.set_facecolor("#ffffff")

    # Slab boundary
    slab_rect = patches.Rectangle(
        (x_slab_min, y_slab_min), slab_w, slab_h,
        linewidth=4.0, edgecolor="#0f172a", facecolor="#f8fafc", zorder=1
    )
    ax_plan.add_patch(slab_rect)

    # Cantilever shading
    cant_color = "#e0e7ff"
    if cant_left > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_slab_min), cant_left, slab_h,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.45, linestyle="--", zorder=2
        ))
    if cant_right > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_coords[-1], y_slab_min), cant_right, slab_h,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.45, linestyle="--", zorder=2
        ))
    if cant_bottom > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_slab_min), slab_w, cant_bottom,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.45, linestyle="--", zorder=2
        ))
    if cant_top > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_coords[-1]), slab_w, cant_top,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.45, linestyle="--", zorder=2
        ))

    # Voids / Openings (المناور والفراغات المعمارية)
    _voids = set(void_panel_ids) if void_panel_ids else set()
    all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _voids)
    for p in all_panels:
        if p["is_void"]:
            v_rect = patches.Rectangle(
                (p["x1"], p["y1"]), p["Lx"], p["Ly"],
                linewidth=2.4, edgecolor="#64748b", facecolor="#cbd5e1", zorder=2
            )
            ax_plan.add_patch(v_rect)
            ax_plan.plot([p["x1"], p["x2"]], [p["y1"], p["y2"]], color="#64748b", linestyle="--", linewidth=2.0, zorder=2)
            ax_plan.plot([p["x1"], p["x2"]], [p["y2"], p["y1"]], color="#64748b", linestyle="--", linewidth=2.0, zorder=2)
            ax_plan.text(
                p["mid_x"], p["mid_y"], f"VOID (منور)\n{p['area']:.1f} m²",
                ha="center", va="center", fontsize=15.0, weight="bold", color="#0f172a",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#f1f5f9", edgecolor="#64748b", lw=1.8),
                zorder=4
            )

    # Vertical Grid Axes (Y1, Y2, ...) with Top CAD Bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        y_bot_ext = y_slab_min - 0.6
        ax_plan.plot([x, x], [y_bot_ext, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=2)
        bubble = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x, y_top_ext, f"Y{idx + 1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    # Horizontal Grid Axes (X1, X2, ...) with Left CAD Bubbles
    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        x_right_ext = x_slab_max + 0.6
        ax_plan.plot([x_left_ext, x_right_ext], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=2)
        bubble = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x_left_ext, y, f"X{idx + 1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    col_w_m = max(col_w_cm / 100.0, slab_w * 0.045)
    col_d_m = max(col_d_cm / 100.0, slab_h * 0.045)
    min_span_x = min(Lx_spans) if Lx_spans else 6.0
    min_span_y = min(Ly_spans) if Ly_spans else 6.0

    # Draw Columns
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()
    col_num = 1
    for y in y_coords:
        for x in x_coords:
            if (x, y) in rem_coords:
                continue
            cid = f"C{col_num}"
            col_box = patches.Rectangle(
                (x - col_w_m / 2.0, y - col_d_m / 2.0),
                col_w_m, col_d_m,
                linewidth=2.2, edgecolor="#0f172a", facecolor="#1e293b", zorder=4
            )
            ax_plan.add_patch(col_box)
            ax_plan.text(x, y, cid, color="#facc15", fontsize=16.0, ha="center", va="center", weight="bold", zorder=5)
            col_num += 1

    # 🔵 2. BOTTOM EXTRA REBAR IN ENLARGED BAYS (BLUE)
    if btm_extra_spans:
        # Filter by direction
        if direction in ("X", "Y"):
            active_btm_extras = [
                be for be in btm_extra_spans
                if isinstance(be, dict) and be.get("n_extra", 0) > 0 and be.get("dir", "X") == direction
            ]
        else:
            active_btm_extras = [be for be in btm_extra_spans if isinstance(be, dict) and be.get("n_extra", 0) > 0]
        has_both_dirs = len({be.get("dir", "X") for be in active_btm_extras}) > 1 and len(active_btm_extras) > 1

        for be in active_btm_extras:
            bx = be.get("mid_x", (x_coords[0] + x_coords[-1]) / 2.0)
            by = be.get("mid_y", (y_coords[0] + y_coords[-1]) / 2.0)
            n_b = be["n_extra"]
            dia_b = be["dia_extra"]
            l_b = be.get("L_extra", 4.0)
            dir_label = be.get("dir", "X")
            span_len = be.get("span_len", 6.0)

            if dir_label == "X":
                box_w = min(max(l_b * 0.55, 3.2), span_len * 0.55)
                box_h = min(max(slab_h * 0.12, 1.5), min_span_y * 0.35)
                draw_bx = bx
                draw_by = by - (1.1 if has_both_dirs else 0.0)

                ax_plan.add_patch(patches.Rectangle(
                    (draw_bx - box_w / 2.0, draw_by - box_h / 2.0), box_w, box_h,
                    linewidth=2.0, edgecolor="#2563eb", facecolor="#dbeafe",
                    linestyle="--", alpha=0.75, hatch="\\\\", zorder=3
                ))
                ax_plan.text(
                    draw_bx, draw_by,
                    f"+{n_b}Φ{dia_b} Btm Extra (X) — [→ X-Dir]\n(L={l_b:.2f}m)",
                    color="#1e40af", fontsize=13.5, weight="bold", ha="center", va="center",
                    rotation=0,
                    bbox=dict(boxstyle="round,pad=0.32", facecolor="#ffffff", edgecolor="#2563eb", lw=1.6, alpha=0.98),
                    zorder=6
                )
            else:
                box_w = min(max(slab_w * 0.12, 1.5), min_span_x * 0.35)
                box_h = min(max(l_b * 0.55, 3.2), span_len * 0.55)
                draw_bx = bx
                draw_by = by + (1.1 if has_both_dirs else 0.0)

                ax_plan.add_patch(patches.Rectangle(
                    (draw_bx - box_w / 2.0, draw_by - box_h / 2.0), box_w, box_h,
                    linewidth=2.0, edgecolor="#1d4ed8", facecolor="#dbeafe",
                    linestyle="--", alpha=0.75, hatch="//", zorder=3
                ))
                ax_plan.text(
                    draw_bx, draw_by,
                    f"+{n_b}Φ{dia_b} Btm Extra (Y) — [↑ Y-Dir]\n(L={l_b:.2f}m)",
                    color="#1d4ed8", fontsize=13.5, weight="bold", ha="center", va="center",
                    rotation=90,
                    bbox=dict(boxstyle="round,pad=0.32", facecolor="#ffffff", edgecolor="#1d4ed8", lw=1.6, alpha=0.98),
                    zorder=6
                )

    # Span Dimensions (Lx along Bottom)
    y_dim_lx = y_slab_min - dim_offset_bot
    for i, lx in enumerate(Lx_spans):
        mid_x = (x_coords[i] + x_coords[i + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_coords[i + 1], y_dim_lx), xytext=(x_coords[i], y_dim_lx),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_coords[i], x_coords[i]], [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.plot([x_coords[i+1], x_coords[i+1]], [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.text(
            mid_x, y_dim_lx - 0.45, f"{lx:.2f} m",
            color="#0f172a", fontsize=16.5, weight="bold", ha="center", va="top"
        )

    # Span Dimensions (Ly along Right)
    dim_offset_right = max(1.6, slab_w * 0.10)
    x_dim_ly = x_slab_max + dim_offset_right
    for j, ly in enumerate(Ly_spans):
        mid_y = (y_coords[j] + y_coords[j + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_dim_ly, y_coords[j + 1]), xytext=(x_dim_ly, y_coords[j]),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j], y_coords[j]], color="#0f172a", lw=1.8)
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j+1], y_coords[j+1]], color="#0f172a", lw=1.8)
        ax_plan.text(
            x_dim_ly + 0.45, mid_y, f"{ly:.2f} m",
            color="#0f172a", fontsize=16.5, weight="bold", ha="left", va="center"
        )

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.axis("off")

    # ── 2. ENGINEERING TITLE BLOCK & COLOR LEGEND (ax_legend) ────────────────
    ax_legend.set_facecolor("#ffffff")
    ax_legend.axis("off")
    ax_legend.set_xlim(0, 1)
    ax_legend.set_ylim(0, 1)

    legend_bg = FancyBboxPatch(
        (0.005, 0.02), 0.99, 0.96,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        linewidth=2.4, edgecolor="#0f172a", facecolor="#f8fafc", zorder=1
    )
    ax_legend.add_patch(legend_bg)

    cards_info = [
        ("BOTTOM REINFORCEMENT\n(الحديد السفلي الأساسي)", f"Base Mesh: {mesh_btm_str} (B1, B2)\nB1 (Main) in long dir, B2 in short dir", "#1e40af", "#dbeafe", "#2563eb"),
        ("BOTTOM EXTRA IN BAYS\n(إضافي الباكيات)", "Extra bottom bars in enlarged bays\nPlaced in mid-strip zones (L ≈ 0.70L)", "#1e40af", "#dbeafe", "#2563eb"),
        ("REBAR CONTINUITY\n(استمرارية التسليح)", "Bottom bars extend into supports >= 15cm\nContinuous through column/field strips", "#0f766e", "#ccfbf1", "#0d9488"),
        ("CODE NOTES (ECP 203)\n(ملاحظات الكود)", "Cover = 15mm | As,min = 0.18% b·ts\nStagger bottom splices at mid-spans", "#0f172a", "#f1f5f9", "#64748b"),
    ]

    x_box_w = 0.235
    x_box_gap = 0.012
    x_start = 0.015

    for k, (title, content, t_color, bg_color, border_color) in enumerate(cards_info):
        bx = x_start + k * (x_box_w + x_box_gap)
        ibox = FancyBboxPatch(
            (bx, 0.04), x_box_w, 0.92,
            boxstyle="round,pad=0.015,rounding_size=0.02",
            linewidth=1.6, edgecolor=border_color, facecolor=bg_color, zorder=2
        )
        ax_legend.add_patch(ibox)
        ax_legend.text(
            bx + x_box_w / 2.0, 0.74, title,
            ha="center", va="center", fontsize=16.5, weight="bold", color=t_color, linespacing=1.2, zorder=3
        )
        ax_legend.text(
            bx + x_box_w / 2.0, 0.28, content,
            ha="center", va="center", fontsize=19.6, color="#1e293b", weight="normal", linespacing=1.22, zorder=3
        )

    dir_label_en = {"X": "X-Direction (Horizontal Spans ↔)", "Y": "Y-Direction (Vertical Spans ↕)", "both": "Both Directions"}.get(direction, "")
    dir_label_ar = {"X": "الاتجاه الأفقي X", "Y": "الاتجاه الرأسي Y", "both": "كلا الاتجاهين"}.get(direction, "")
    fig.suptitle(
        f"BOTTOM EXTRA REINFORCEMENT PLAN — {dir_label_en}\n"
        f"(مخطط الحديد السفلي الإضافي — {dir_label_ar} — ts = {ts_cm:.0f} cm)",
        fontsize=19, weight="bold", y=0.98, color="#0f172a",
    )

    return fig



def generate_flat_slab_reactions_sketch(
    Lx_spans,
    Ly_spans,
    cantilevers,
    num_floors,
    Wu,
    col_reactions_data,
    col_w_cm=30,
    col_d_cm=50,
    removed_cols=None,
    void_panel_ids=None,
):
    """
    Renders an engineering layout plan showing column tributary areas,
    column locations, and explicit vertical reactions / axial loads (1 floor & Total for N floors)
    directly at each column position on the slab geometry.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)

    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    # Grid bubble offsets & margins
    bubble_radius = max(0.44, min(slab_w, slab_h) * 0.034)
    offset_grid_top = max(1.8, slab_h * 0.10)
    offset_grid_left = max(1.8, slab_w * 0.10)
    dim_offset_bot = max(1.6, slab_h * 0.10)
    dim_offset_right = max(1.5, slab_w * 0.08)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.6
    margin_right = dim_offset_right + 1.2
    margin_top = offset_grid_top + bubble_radius * 2 + 0.6
    margin_bot = dim_offset_bot + 1.2

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.5
    target_plan_w = target_plan_h * ar_plan
    legend_h = 4.2

    fig_w = max(24.0, min(36.0, target_plan_w + 1.6))
    fig_h = max(18.0, min(36.0, target_plan_h + legend_h + 1.2))

    plan_ratio = (fig_h - legend_h - 1.0) / fig_h
    legend_ratio = legend_h / fig_h

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=150, facecolor="#ffffff")
    gs = fig.add_gridspec(
        2, 1,
        height_ratios=[plan_ratio, legend_ratio],
        hspace=0.04,
        left=0.02, right=0.98, top=0.95, bottom=0.02
    )

    ax_plan = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])

    ax_plan.set_facecolor("#ffffff")

    # Slab boundary
    slab_rect = patches.Rectangle(
        (x_slab_min, y_slab_min), slab_w, slab_h,
        linewidth=3.5, edgecolor="#0f172a", facecolor="#f8fafc", zorder=1
    )
    ax_plan.add_patch(slab_rect)

    # Cantilever shading
    cant_color = "#e0e7ff"
    if cant_left > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_slab_min), cant_left, slab_h,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.40, linestyle="--", zorder=2
        ))
    if cant_right > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_coords[-1], y_slab_min), cant_right, slab_h,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.40, linestyle="--", zorder=2
        ))
    if cant_bottom > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_slab_min), slab_w, cant_bottom,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.40, linestyle="--", zorder=2
        ))
    if cant_top > 0:
        ax_plan.add_patch(patches.Rectangle(
            (x_slab_min, y_coords[-1]), slab_w, cant_top,
            linewidth=1.8, edgecolor="#4f46e5", facecolor=cant_color, alpha=0.40, linestyle="--", zorder=2
        ))

    # Voids / Openings (المناور والفراغات المعمارية)
    _voids = set(void_panel_ids) if void_panel_ids else set()
    all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _voids)
    for p in all_panels:
        if p["is_void"]:
            v_rect = patches.Rectangle(
                (p["x1"], p["y1"]), p["Lx"], p["Ly"],
                linewidth=2.4, edgecolor="#64748b", facecolor="#cbd5e1", zorder=2
            )
            ax_plan.add_patch(v_rect)
            ax_plan.plot([p["x1"], p["x2"]], [p["y1"], p["y2"]], color="#64748b", linestyle="--", linewidth=2.0, zorder=2)
            ax_plan.plot([p["x1"], p["x2"]], [p["y2"], p["y1"]], color="#64748b", linestyle="--", linewidth=2.0, zorder=2)
            ax_plan.text(
                p["mid_x"], p["mid_y"], f"VOID (منور)\n{p['area']:.1f} m²",
                ha="center", va="center", fontsize=15.0, weight="bold", color="#0f172a",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#f1f5f9", edgecolor="#64748b", lw=1.8),
                zorder=4
            )

    # Tributary area boundary dividers (mid-spans)
    for i in range(len(Lx_spans)):
        x_mid = (x_coords[i] + x_coords[i+1]) / 2.0
        ax_plan.plot([x_mid, x_mid], [y_slab_min, y_slab_max], color="#cbd5e1", linestyle="--", linewidth=1.5, zorder=2)
    for j in range(len(Ly_spans)):
        y_mid = (y_coords[j] + y_coords[j+1]) / 2.0
        ax_plan.plot([x_slab_min, x_slab_max], [y_mid, y_mid], color="#cbd5e1", linestyle="--", linewidth=1.5, zorder=2)

    # Vertical Grid Axes (Y1, Y2, ...) with Top CAD Bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        y_bot_ext = y_slab_min - 0.6
        ax_plan.plot([x, x], [y_bot_ext, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=2)
        bubble = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x, y_top_ext, f"Y{idx + 1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    # Horizontal Grid Axes (X1, X2, ...) with Left CAD Bubbles
    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        x_right_ext = x_slab_max + 0.6
        ax_plan.plot([x_left_ext, x_right_ext], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=2)
        bubble = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x_left_ext, y, f"X{idx + 1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    col_w_m = max(col_w_cm / 100.0, slab_w * 0.045)
    col_d_m = max(col_d_cm / 100.0, slab_h * 0.045)

    reac_map = {r["Column ID"]: r for r in col_reactions_data}
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()

    col_idx = 1
    for j_idx, y in enumerate(y_coords):
        for i_idx, x in enumerate(x_coords):
            if (x, y) in rem_coords:
                continue
            cid = f"C{col_idx}"
            r_info = reac_map.get(cid, None)

            raw_type = r_info.get("Raw Type", "Interior") if r_info else "Interior"
            if raw_type == "Corner":
                col_edge = "#ea580c"
                type_name = "Corner"
            elif raw_type == "Edge":
                col_edge = "#2563eb"
                type_name = "Edge"
            else:
                col_edge = "#16a34a"
                type_name = "Interior"

            col_box = patches.Rectangle(
                (x - col_w_m / 2.0, y - col_d_m / 2.0),
                col_w_m, col_d_m,
                linewidth=2.4, edgecolor="#0f172a", facecolor="#1e293b", zorder=4
            )
            ax_plan.add_patch(col_box)
            ax_plan.text(x, y, cid, color="#facc15", fontsize=15.0, ha="center", va="center", weight="bold", zorder=5)

            if r_info:
                pu1 = r_info.get("pu_1f_val", 0.0)
                pu_tot = r_info.get("pu_tot_val", 0.0)
                atrib = r_info.get("atrib_val", 0.0)

                card_dx = 0.0
                if j_idx == 0:
                    card_dy = col_d_m * 0.95 + max(0.5, slab_h * 0.05)
                elif j_idx == len(y_coords) - 1:
                    card_dy = -(col_d_m * 0.95 + max(0.5, slab_h * 0.05))
                else:
                    card_dy = col_d_m * 0.95 + max(0.4, slab_h * 0.04)

                card_x = x + card_dx
                card_y = y + card_dy

                text_content = (
                    f"[ {cid} — {type_name} ]\n"
                    f"• Atrib = {atrib:.2f} m²\n"
                    f"• Pu (1F) = {pu1:.2f} t\n"
                    f"★ Pu ({num_floors}F) = {pu_tot:.2f} t"
                )

                ax_plan.text(
                    card_x, card_y,
                    text_content,
                    color="#0f172a", fontsize=12.5, weight="bold", ha="center", va="center",
                    linespacing=1.35,
                    bbox=dict(
                        boxstyle="round,pad=0.38",
                        facecolor="#ffffff",
                        edgecolor=col_edge,
                        lw=2.0,
                        alpha=0.98
                    ),
                    zorder=6
                )

            col_idx += 1

    # Span Dimensions (Lx along Bottom)
    y_dim_lx = y_slab_min - dim_offset_bot
    for i, lx in enumerate(Lx_spans):
        mid_x = (x_coords[i] + x_coords[i + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_coords[i + 1], y_dim_lx), xytext=(x_coords[i], y_dim_lx),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_coords[i], x_coords[i]], [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.plot([x_coords[i+1], x_coords[i+1]], [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.text(
            mid_x, y_dim_lx - 0.45, f"{lx:.2f} m",
            color="#0f172a", fontsize=16.5, weight="bold", ha="center", va="top"
        )

    # Span Dimensions (Ly along Right)
    dim_offset_right = max(1.6, slab_w * 0.10)
    x_dim_ly = x_slab_max + dim_offset_right
    for j, ly in enumerate(Ly_spans):
        mid_y = (y_coords[j] + y_coords[j + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_dim_ly, y_coords[j + 1]), xytext=(x_dim_ly, y_coords[j]),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j], y_coords[j]], color="#0f172a", lw=1.8)
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j+1], y_coords[j+1]], color="#0f172a", lw=1.8)
        ax_plan.text(
            x_dim_ly + 0.45, mid_y, f"{ly:.2f} m",
            color="#0f172a", fontsize=16.5, weight="bold", ha="left", va="center"
        )

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.axis("off")

    # ── 2. BOTTOM LEGEND (ax_legend) ─────────────────────────────────────────
    ax_legend.set_facecolor("#ffffff")
    ax_legend.axis("off")
    ax_legend.set_xlim(0, 1)
    ax_legend.set_ylim(0, 1)

    legend_bg = FancyBboxPatch(
        (0.005, 0.02), 0.99, 0.96,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        linewidth=2.4, edgecolor="#0f172a", facecolor="#f8fafc", zorder=1
    )
    ax_legend.add_patch(legend_bg)

    cards_info = [
        ("INTERIOR COLUMNS\n(أعمدة داخلية)", "Full interior tributary area\nMaximum vertical load capacity", "#15803d", "#dcfce7", "#16a34a"),
        ("EDGE COLUMNS\n(أعمدة طرفية / وسط خارجي)", "Half-span spandrel tributary area\nSubject to edge unbalanced moment", "#1e40af", "#dbeafe", "#2563eb"),
        ("CORNER COLUMNS\n(أعمدة أركان)", "Quarter-span corner tributary area\nSubject to biaxial corner moments", "#c2410c", "#ffedd5", "#ea580c"),
        ("TRIBUTARY FORMULAS\n(معادلات توزيع الأحمال)", f"Total Pu = Pu(1 Floor) × {num_floors} Floors\nPu = Tributary Area × Wu ({Wu:.3f} t/m²)", "#0f172a", "#f1f5f9", "#64748b"),
    ]

    x_box_w = 0.235
    x_box_gap = 0.012
    x_start = 0.015

    for k, (title, content, t_color, bg_color, border_color) in enumerate(cards_info):
        bx = x_start + k * (x_box_w + x_box_gap)
        ibox = FancyBboxPatch(
            (bx, 0.04), x_box_w, 0.92,
            boxstyle="round,pad=0.015,rounding_size=0.02",
            linewidth=1.6, edgecolor=border_color, facecolor=bg_color, zorder=2
        )
        ax_legend.add_patch(ibox)
        ax_legend.text(
            bx + x_box_w / 2.0, 0.74, title,
            ha="center", va="center", fontsize=16.5, weight="bold", color=t_color, linespacing=1.2, zorder=3
        )
        ax_legend.text(
            bx + x_box_w / 2.0, 0.28, content,
            ha="center", va="center", fontsize=19.6, color="#1e293b", weight="normal", linespacing=1.22, zorder=3
        )

    fig.suptitle(
        f"COLUMN REACTIONS & VERTICAL LOADS DISTRIBUTION PLAN (مخطط ردود أفعال وأحمال الأعمدة — {num_floors} طوابق)",
        fontsize=20, weight="bold", y=0.98, color="#0f172a"
    )

    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  ④ 2D BENDING MOMENT MATRIX & COLOR CONTOUR VISUALIZATIONS (M11 & M22)
# ═══════════════════════════════════════════════════════════════════════════════

def build_slab_moment_field(
    Lx_spans,
    Ly_spans,
    cantilevers,
    rows_x,
    rows_y,
    Wu,
    void_panel_ids=None,
    grid_res=220,
):
    """
    Reconstructs continuous 2D moment fields M11(x, y) and M22(x, y)
    from DDM calculation values without altering any structural formulas.
    Returns (X, Y, M11, M22, M11_raw, M22_raw).
    """
    cant_L = cantilevers.get("left", 0.0)
    cant_R = cantilevers.get("right", 0.0)
    cant_B = cantilevers.get("bottom", 0.0)
    cant_T = cantilevers.get("top", 0.0)

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    x_min = x_coords[0] - cant_L
    x_max = x_coords[-1] + cant_R
    y_min = y_coords[0] - cant_B
    y_max = y_coords[-1] + cant_T

    # Generate fine 2D coordinate mesh
    slab_w = x_max - x_min
    slab_h = y_max - y_min
    nx_pts = max(grid_res, int(grid_res * slab_w / max(slab_h, 1.0)))
    ny_pts = max(grid_res, int(grid_res * slab_h / max(slab_w, 1.0)))
    x_vec = np.linspace(x_min, x_max, nx_pts)
    y_vec = np.linspace(y_min, y_max, ny_pts)
    X, Y = np.meshgrid(x_vec, y_vec)

    M11 = np.zeros_like(X)
    M22 = np.zeros_like(Y)

    Lx_avg = np.mean(Lx_spans) if Lx_spans else 6.0
    Ly_avg = np.mean(Ly_spans) if Ly_spans else 6.0
    h_cs_y = min(Lx_avg, Ly_avg) / 4.0
    h_cs_x = min(Lx_avg, Ly_avg) / 4.0

    # ── 1. Calculate M11(x, y) (Moments along X-direction) ───────────────────
    dist_to_y_axes = np.min(np.abs(Y[:, :, np.newaxis] - np.array(y_coords)), axis=2)
    w_cs_11 = np.cos(np.pi / 2.0 * np.clip(dist_to_y_axes / (h_cs_y * 1.35), 0.0, 1.0)) ** 2

    if cant_L > 0:
        mask_cL = (X < x_coords[0])
        M11[mask_cL] = -0.5 * Wu * np.maximum(0.0, X[mask_cL] - x_min) ** 2

    if cant_R > 0:
        mask_cR = (X > x_coords[-1])
        M11[mask_cR] = -0.5 * Wu * np.maximum(0.0, x_max - X[mask_cR]) ** 2

    for i, lx in enumerate(Lx_spans):
        x_left = x_coords[i]
        x_right = x_coords[i+1]
        mask_span = (X >= x_left) & (X <= x_right)
        if not np.any(mask_span):
            continue

        r_info = rows_x[min(i, len(rows_x)-1)] if rows_x else {}
        M_pos = r_info.get("M_pos", 0.35 * r_info.get("Mo", 10.0))

        if i == 0:
            M_neg_L = max(r_info.get("M_neg_ext", 0.0), 0.5 * Wu * (cant_L ** 2))
        else:
            M_neg_L = r_info.get("M_neg_int", 0.65 * r_info.get("Mo", 10.0))

        if i == len(Lx_spans) - 1:
            M_neg_R = max(r_info.get("M_neg_ext", 0.0), 0.5 * Wu * (cant_R ** 2))
        else:
            M_neg_R = r_info.get("M_neg_int", 0.65 * r_info.get("Mo", 10.0))

        M_cs_neg_L = 0.75 * M_neg_L
        M_cs_neg_R = 0.75 * M_neg_R
        M_cs_pos   = 0.60 * M_pos

        M_ms_neg_L = 0.25 * M_neg_L
        M_ms_neg_R = 0.25 * M_neg_R
        M_ms_pos   = 0.40 * M_pos

        xi = (X[mask_span] - x_left) / max(0.001, lx)
        M_cs = -M_cs_neg_L * (1.0 - xi) - M_cs_neg_R * xi + 4.0 * (M_cs_pos + (M_cs_neg_L + M_cs_neg_R) / 2.0) * xi * (1.0 - xi)
        M_ms = -M_ms_neg_L * (1.0 - xi) - M_ms_neg_R * xi + 4.0 * (M_ms_pos + (M_ms_neg_L + M_ms_neg_R) / 2.0) * xi * (1.0 - xi)

        w = w_cs_11[mask_span]
        M11[mask_span] = w * M_cs + (1.0 - w) * M_ms

    # ── 2. Calculate M22(x, y) (Moments along Y-direction) ───────────────────
    dist_to_x_axes = np.min(np.abs(X[:, :, np.newaxis] - np.array(x_coords)), axis=2)
    w_cs_22 = np.cos(np.pi / 2.0 * np.clip(dist_to_x_axes / (h_cs_x * 1.35), 0.0, 1.0)) ** 2

    if cant_B > 0:
        mask_cB = (Y < y_coords[0])
        M22[mask_cB] = -0.5 * Wu * np.maximum(0.0, Y[mask_cB] - y_min) ** 2

    if cant_T > 0:
        mask_cT = (Y > y_coords[-1])
        M22[mask_cT] = -0.5 * Wu * np.maximum(0.0, y_max - Y[mask_cT]) ** 2

    for j, ly in enumerate(Ly_spans):
        y_bot = y_coords[j]
        y_top = y_coords[j+1]
        mask_span = (Y >= y_bot) & (Y <= y_top)
        if not np.any(mask_span):
            continue

        r_info = rows_y[min(j, len(rows_y)-1)] if rows_y else {}
        M_pos = r_info.get("M_pos", 0.35 * r_info.get("Mo", 10.0))

        if j == 0:
            M_neg_B = max(r_info.get("M_neg_ext", 0.0), 0.5 * Wu * (cant_B ** 2))
        else:
            M_neg_B = r_info.get("M_neg_int", 0.65 * r_info.get("Mo", 10.0))

        if j == len(Ly_spans) - 1:
            M_neg_T = max(r_info.get("M_neg_ext", 0.0), 0.5 * Wu * (cant_T ** 2))
        else:
            M_neg_T = r_info.get("M_neg_int", 0.65 * r_info.get("Mo", 10.0))

        M_cs_neg_B = 0.75 * M_neg_B
        M_cs_neg_T = 0.75 * M_neg_T
        M_cs_pos   = 0.60 * M_pos

        M_ms_neg_B = 0.25 * M_neg_B
        M_ms_neg_T = 0.25 * M_neg_T
        M_ms_pos   = 0.40 * M_pos

        eta = (Y[mask_span] - y_bot) / max(0.001, ly)
        M_cs = -M_cs_neg_B * (1.0 - eta) - M_cs_neg_T * eta + 4.0 * (M_cs_pos + (M_cs_neg_B + M_cs_neg_T) / 2.0) * eta * (1.0 - eta)
        M_ms = -M_ms_neg_B * (1.0 - eta) - M_ms_neg_T * eta + 4.0 * (M_ms_pos + (M_ms_neg_B + M_ms_neg_T) / 2.0) * eta * (1.0 - eta)

        w = w_cs_22[mask_span]
        M22[mask_span] = w * M_cs + (1.0 - w) * M_ms

    # Keep unmasked copies for sampling support values
    M11_raw = np.copy(M11)
    M22_raw = np.copy(M22)

    # ── 3. Mask Void Openings ────────────────────────────────────────────────
    if void_panel_ids:
        void_set = set(void_panel_ids)
        for j in range(len(Ly_spans)):
            for i in range(len(Lx_spans)):
                pid = f"P_{i+1}_{j+1}"
                if pid in void_set:
                    x1, x2 = x_coords[i], x_coords[i+1]
                    y1, y2 = y_coords[j], y_coords[j+1]
                    v_mask = (X >= x1) & (X <= x2) & (Y >= y1) & (Y <= y2)
                    M11[v_mask] = np.nan
                    M22[v_mask] = np.nan

    return X, Y, M11, M22, M11_raw, M22_raw


def generate_flat_slab_moment_contour(
    Lx_spans,
    Ly_spans,
    cantilevers,
    rows_x,
    rows_y,
    Wu,
    mode="M11",                  # "M11" or "M22"
    col_w_cm=30,
    col_d_cm=30,
    removed_cols=None,
    void_panel_ids=None,
    top_extra_cols=None,
    btm_extra_spans=None,
):
    """
    Renders an engineering 2D Bending Moment Matrix & Color Contour Map (M11 or M22)
    using the exact DDM calculated values without modifying any structural equations.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)

    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    # Reconstruct 2D mesh and moment matrix
    X, Y, M11, M22, M11_raw, M22_raw = build_slab_moment_field(
        Lx_spans, Ly_spans, cantilevers, rows_x, rows_y, Wu, void_panel_ids=void_panel_ids
    )

    M_field = M11 if mode == "M11" else M22
    M_raw = M11_raw if mode == "M11" else M22_raw
    x_vec = X[0, :]
    y_vec = Y[:, 0]

    # Dynamic Figure Layout
    bubble_radius = max(0.44, min(slab_w, slab_h) * 0.034)
    offset_grid_top = max(1.8, slab_h * 0.10)
    offset_grid_left = max(1.8, slab_w * 0.10)
    dim_offset_bot = max(1.6, slab_h * 0.10)
    dim_offset_right = max(1.5, slab_w * 0.08)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.6
    margin_right = dim_offset_right + 1.2
    margin_top = offset_grid_top + bubble_radius * 2 + 0.6
    margin_bot = dim_offset_bot + 1.2

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.5
    target_plan_w = target_plan_h * ar_plan
    legend_h = 4.0

    fig_w = max(24.0, min(36.0, target_plan_w + 1.6))
    fig_h = max(18.0, min(36.0, target_plan_h + legend_h + 1.2))

    plan_ratio = (fig_h - legend_h - 1.0) / fig_h
    legend_ratio = legend_h / fig_h

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=150, facecolor="#ffffff")
    gs = fig.add_gridspec(
        2, 1,
        height_ratios=[plan_ratio, legend_ratio],
        hspace=0.05,
        left=0.02, right=0.96, top=0.94, bottom=0.02
    )

    ax_plan = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])

    ax_plan.set_facecolor("#ffffff")

    # Determine symmetric or optimal contour levels
    valid_m = M_field[~np.isnan(M_field)]
    m_min = float(np.min(valid_m)) if len(valid_m) > 0 else -10.0
    m_max = float(np.max(valid_m)) if len(valid_m) > 0 else 10.0

    levels = np.linspace(m_min, m_max, 36)

    # 1. Filled Contour Map
    cmap_chosen = "RdYlBu_r"   # Red: positive sagging (+M), Blue: negative hogging (-M)
    cs = ax_plan.contourf(X, Y, M_field, levels=levels, cmap=cmap_chosen, extend="both", zorder=1, alpha=0.92)

    # 2. Line Contours & Zero Inflection Line
    line_levels = np.linspace(m_min, m_max, 14)
    cs_lines = ax_plan.contour(X, Y, M_field, levels=line_levels, colors="#1e293b", linewidths=0.75, alpha=0.45, zorder=2)
    ax_plan.clabel(cs_lines, inline=True, fontsize=10.5, fmt="%.1f", colors="#0f172a")

    if m_min < 0 < m_max:
        # Bold dashed zero contour line
        ax_plan.contour(X, Y, M_field, levels=[0.0], colors="#000000", linewidths=2.2, linestyles="--", zorder=3)

    # Colorbar
    cbar_ax = fig.add_axes([0.965, 0.32, 0.015, 0.58])
    cbar = fig.colorbar(cs, cax=cbar_ax)
    dir_txt = "X-Direction (↔ M11)" if mode == "M11" else "Y-Direction (↕ M22)"
    cbar.set_label(f"Bending Moment {mode} (t·m/m) | عزم الانحناء [{dir_txt}]", fontsize=14, weight="bold", labelpad=12)
    cbar.ax.tick_params(labelsize=12)

    # Slab boundary outline
    slab_rect = patches.Rectangle(
        (x_slab_min, y_slab_min), slab_w, slab_h,
        linewidth=3.5, edgecolor="#0f172a", facecolor="none", zorder=4
    )
    ax_plan.add_patch(slab_rect)

    # Cantilever outlines
    cant_style = dict(linewidth=1.6, edgecolor="#1d4ed8", facecolor="none", linestyle="--", zorder=4)
    if cant_left > 0:
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), cant_left, slab_h, **cant_style))
    if cant_right > 0:
        ax_plan.add_patch(patches.Rectangle((x_coords[-1], y_slab_min), cant_right, slab_h, **cant_style))
    if cant_bottom > 0:
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, cant_bottom, **cant_style))
    if cant_top > 0:
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_coords[-1]), slab_w, cant_top, **cant_style))

    # Voids / Openings
    _voids = set(void_panel_ids) if void_panel_ids else set()
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                x1, x2 = x_coords[i], x_coords[i+1]
                y1, y2 = y_coords[j], y_coords[j+1]
                lx, ly = x2 - x1, y2 - y1
                v_rect = patches.Rectangle((x1, y1), lx, ly, linewidth=2.2, edgecolor="#475569", facecolor="#cbd5e1", zorder=4)
                ax_plan.add_patch(v_rect)
                ax_plan.plot([x1, x2], [y1, y2], color="#475569", linestyle="--", linewidth=1.8, zorder=4)
                ax_plan.plot([x1, x2], [y2, y1], color="#475569", linestyle="--", linewidth=1.8, zorder=4)
                ax_plan.text(
                    (x1 + x2) / 2.0, (y1 + y2) / 2.0, f"VOID (منور)\n{lx*ly:.1f} m²",
                    ha="center", va="center", fontsize=14.0, weight="bold", color="#0f172a",
                    bbox=dict(boxstyle="round,pad=0.32", facecolor="#f1f5f9", edgecolor="#64748b", lw=1.6),
                    zorder=5
                )

    # Vertical Grid Axes (Y1, Y2, ...) with Top CAD Bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        y_bot_ext = y_slab_min - 0.6
        ax_plan.plot([x, x], [y_bot_ext, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=3)
        bubble = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x, y_top_ext, f"Y{idx + 1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    # Horizontal Grid Axes (X1, X2, ...) with Left CAD Bubbles
    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        x_right_ext = x_slab_max + 0.6
        ax_plan.plot([x_left_ext, x_right_ext], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=3)
        bubble = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bubble)
        ax_plan.text(x_left_ext, y, f"X{idx + 1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    # Column Box & Peak Negative Moment Badges
    col_w_m = max(col_w_cm / 100.0, slab_w * 0.045)
    col_d_m = max(col_d_cm / 100.0, slab_h * 0.045)
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()

    col_idx = 1
    for j_idx, y in enumerate(y_coords):
        for i_idx, x in enumerate(x_coords):
            if (x, y) in rem_coords:
                continue
            cid = f"C{col_idx}"

            # Column rectangle
            col_box = patches.Rectangle(
                (x - col_w_m / 2.0, y - col_d_m / 2.0),
                col_w_m, col_d_m,
                linewidth=2.2, edgecolor="#0f172a", facecolor="#1e293b", zorder=6
            )
            ax_plan.add_patch(col_box)
            ax_plan.text(x, y, cid, color="#facc15", fontsize=14.5, ha="center", va="center", weight="bold", zorder=7)

            # Local peak negative moment value from raw unmasked matrix
            ix = np.argmin(np.abs(x_vec - x))
            iy = np.argmin(np.abs(y_vec - y))
            m_val = M_raw[iy, ix]

            # Badge offset
            if j_idx == 0:
                badge_y = y + col_d_m * 0.75 + 0.35
                va_pos = "bottom"
            else:
                badge_y = y - col_d_m * 0.75 - 0.35
                va_pos = "top"

            ax_plan.text(
                x, badge_y,
                f"M⁻ = {m_val:.2f} t.m",
                color="#1e3a8a", fontsize=12.0, weight="bold", ha="center", va=va_pos,
                bbox=dict(boxstyle="round,pad=0.28", facecolor="#ffffff", edgecolor="#3b82f6", lw=1.5, alpha=0.96),
                zorder=8
            )

            col_idx += 1

    # Peak Positive Moment Badges at Bay Midspans
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                continue
            mid_x = (x_coords[i] + x_coords[i+1]) / 2.0
            mid_y = (y_coords[j] + y_coords[j+1]) / 2.0
            ix = np.argmin(np.abs(x_vec - mid_x))
            iy = np.argmin(np.abs(y_vec - mid_y))
            m_pos_val = M_raw[iy, ix]

            ax_plan.text(
                mid_x, mid_y,
                f"M⁺ = +{m_pos_val:.2f}\nt.m/m",
                color="#991b1b", fontsize=12.5, weight="bold", ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.32", facecolor="#fff7ed", edgecolor="#ea580c", lw=1.6, alpha=0.96),
                zorder=7
            )

    # Span Dimensions (Lx along Bottom)
    y_dim_lx = y_slab_min - dim_offset_bot
    for i, lx in enumerate(Lx_spans):
        mid_x = (x_coords[i] + x_coords[i + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_coords[i + 1], y_dim_lx), xytext=(x_coords[i], y_dim_lx),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_coords[i], x_coords[i]], [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.plot([x_coords[i+1], x_coords[i+1]], [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.text(
            mid_x, y_dim_lx - 0.45, f"{lx:.2f} m",
            color="#0f172a", fontsize=16.5, weight="bold", ha="center", va="top"
        )

    # Span Dimensions (Ly along Right)
    dim_offset_right = max(1.6, slab_w * 0.10)
    x_dim_ly = x_slab_max + dim_offset_right
    for j, ly in enumerate(Ly_spans):
        mid_y = (y_coords[j] + y_coords[j + 1]) / 2.0
        ax_plan.annotate(
            "", xy=(x_dim_ly, y_coords[j + 1]), xytext=(x_dim_ly, y_coords[j]),
            arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0)
        )
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j], y_coords[j]], color="#0f172a", lw=1.8)
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j+1], y_coords[j+1]], color="#0f172a", lw=1.8)
        ax_plan.text(
            x_dim_ly + 0.45, mid_y, f"{ly:.2f} m",
            color="#0f172a", fontsize=16.5, weight="bold", ha="left", va="center"
        )

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.axis("off")

    # ── 2. ENGINEERING TITLE BLOCK & COLOR LEGEND (ax_legend) ────────────────
    ax_legend.set_facecolor("#ffffff")
    ax_legend.axis("off")
    ax_legend.set_xlim(0, 1)
    ax_legend.set_ylim(0, 1)

    legend_bg = FancyBboxPatch(
        (0.005, 0.02), 0.99, 0.96,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        linewidth=2.4, edgecolor="#0f172a", facecolor="#f8fafc", zorder=1
    )
    ax_legend.add_patch(legend_bg)

    cards_info = [
        (
            f"MOMENT FIELD ({mode})\n(مصفوفة العزوم الممثلة)",
            f"{'X-Direction (Horizontal Spans M11)' if mode=='M11' else 'Y-Direction (Vertical Spans M22)'}\nBased on ECP 203 Direct Design Method",
            "#1e40af", "#dbeafe", "#2563eb"
        ),
        (
            "SIGN CONVENTION\n(اصطلاح إشارات العزوم)",
            "(+) +M (Warm Colors): Sagging / Bottom Tension\n(-) -M (Cool Colors): Hogging / Top Tension @ Cols",
            "#b45309", "#fef3c7", "#d97706"
        ),
        (
            "STRIP DISTRIBUTION\n(توزيع شرائح الأعمدة والوسط)",
            "Column Strip: 75% Neg. / 60% Pos. Moments\nMiddle Strip: 25% Neg. / 40% Pos. Moments",
            "#15803d", "#dcfce7", "#16a34a"
        ),
        (
            "EXTREME DESIGN VALUES\n(القيم القصوى التصميمية)",
            f"Max Pos (+M): +{m_max:.2f} t.m/m\nMax Neg (-M): {m_min:.2f} t.m/m",
            "#0f172a", "#f1f5f9", "#64748b"
        ),
    ]

    x_box_w = 0.235
    x_box_gap = 0.012
    x_start = 0.015

    for k, (title, content, t_color, bg_color, border_color) in enumerate(cards_info):
        bx = x_start + k * (x_box_w + x_box_gap)
        ibox = FancyBboxPatch(
            (bx, 0.04), x_box_w, 0.92,
            boxstyle="round,pad=0.015,rounding_size=0.02",
            linewidth=1.6, edgecolor=border_color, facecolor=bg_color, zorder=2
        )
        ax_legend.add_patch(ibox)
        ax_legend.text(
            bx + x_box_w / 2.0, 0.74, title,
            ha="center", va="center", fontsize=15.0, weight="bold", color=t_color, linespacing=1.2, zorder=3
        )
        ax_legend.text(
            bx + x_box_w / 2.0, 0.28, content,
            ha="center", va="center", fontsize=14.0, color="#1e293b", weight="normal", linespacing=1.25, zorder=3
        )

    sub_title_ar = "اتجاه المحور الأفقي X" if mode == "M11" else "اتجاه المحور الرأسي Y"
    fig.suptitle(
        f"2D BENDING MOMENT CONTOUR MAP — {mode} (المخطط اللوني لمصفوفة عزوم الانحناء — {sub_title_ar})",
        fontsize=20, weight="bold", y=0.98, color="#0f172a"
    )

    return fig


def generate_flat_slab_dual_moment_contour(
    Lx_spans,
    Ly_spans,
    cantilevers,
    rows_x,
    rows_y,
    Wu,
    col_w_cm=30,
    col_d_cm=30,
    removed_cols=None,
    void_panel_ids=None,
):
    """
    Renders dual side-by-side engineering contour maps for both M11 and M22 on a unified canvas.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)

    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    X, Y, M11, M22, M11_raw, M22_raw = build_slab_moment_field(
        Lx_spans, Ly_spans, cantilevers, rows_x, rows_y, Wu, void_panel_ids=void_panel_ids
    )

    bubble_radius = max(0.40, min(slab_w, slab_h) * 0.030)
    offset_grid_top = max(1.5, slab_h * 0.09)
    offset_grid_left = max(1.5, slab_w * 0.09)
    dim_offset_bot = max(1.3, slab_h * 0.08)
    dim_offset_right = max(1.3, slab_w * 0.07)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.5
    margin_right = dim_offset_right + 1.0
    margin_top = offset_grid_top + bubble_radius * 2 + 0.5
    margin_bot = dim_offset_bot + 1.0

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot

    fig = plt.figure(figsize=(32.0, 16.0), dpi=140, facecolor="#ffffff")
    gs = fig.add_gridspec(1, 2, wspace=0.10, left=0.03, right=0.97, top=0.92, bottom=0.06)

    modes = [("M11", M11, "↔ X-Direction (Spans M11)", gs[0, 0]),
             ("M22", M22, "↕ Y-Direction (Spans M22)", gs[0, 1])]

    col_w_m = max(col_w_cm / 100.0, slab_w * 0.045)
    col_d_m = max(col_d_cm / 100.0, slab_h * 0.045)
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()
    _voids = set(void_panel_ids) if void_panel_ids else set()

    for mode_name, M_data, dir_label, g_slot in modes:
        ax = fig.add_subplot(g_slot)
        ax.set_facecolor("#ffffff")

        valid_m = M_data[~np.isnan(M_data)]
        m_min = float(np.min(valid_m)) if len(valid_m) > 0 else -10.0
        m_max = float(np.max(valid_m)) if len(valid_m) > 0 else 10.0
        levels = np.linspace(m_min, m_max, 32)

        cs = ax.contourf(X, Y, M_data, levels=levels, cmap="RdYlBu_r", extend="both", zorder=1, alpha=0.92)
        cs_lines = ax.contour(X, Y, M_data, levels=np.linspace(m_min, m_max, 12), colors="#1e293b", linewidths=0.7, alpha=0.4, zorder=2)
        ax.clabel(cs_lines, inline=True, fontsize=9.5, fmt="%.1f", colors="#0f172a")

        if m_min < 0 < m_max:
            ax.contour(X, Y, M_data, levels=[0.0], colors="#000000", linewidths=2.0, linestyles="--", zorder=3)

        cbar = fig.colorbar(cs, ax=ax, orientation="horizontal", pad=0.08, shrink=0.75)
        cbar.set_label(f"Bending Moment {mode_name} (t·m/m)", fontsize=13, weight="bold")
        cbar.ax.tick_params(labelsize=11)

        # Slab boundary
        ax.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, slab_h, linewidth=3.0, edgecolor="#0f172a", facecolor="none", zorder=4))

        # Voids
        for j in range(len(Ly_spans)):
            for i in range(len(Lx_spans)):
                pid = f"P_{i+1}_{j+1}"
                if pid in _voids:
                    x1, x2 = x_coords[i], x_coords[i+1]
                    y1, y2 = y_coords[j], y_coords[j+1]
                    lx, ly = x2 - x1, y2 - y1
                    v_rect = patches.Rectangle((x1, y1), lx, ly, linewidth=2.0, edgecolor="#475569", facecolor="#cbd5e1", zorder=4)
                    ax.add_patch(v_rect)
                    ax.plot([x1, x2], [y1, y2], color="#475569", linestyle="--", linewidth=1.6, zorder=4)
                    ax.plot([x1, x2], [y2, y1], color="#475569", linestyle="--", linewidth=1.6, zorder=4)
                    ax.text((x1 + x2)/2.0, (y1 + y2)/2.0, "VOID", ha="center", va="center", fontsize=12.0, weight="bold", color="#0f172a", zorder=5)

        # Grid lines & bubbles
        for idx, x in enumerate(x_coords):
            ax.plot([x, x], [y_slab_min - 0.4, y_slab_max + offset_grid_top], color="#dc2626", linestyle=":", linewidth=1.4, alpha=0.7, zorder=3)
            bubble = Circle((x, y_slab_max + offset_grid_top), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.0, zorder=6)
            ax.add_patch(bubble)
            ax.text(x, y_slab_max + offset_grid_top, f"Y{idx+1}", color="#991b1b", fontsize=13, weight="bold", ha="center", va="center", zorder=7)

        for idx, y in enumerate(y_coords):
            ax.plot([x_slab_min - offset_grid_left, x_slab_max + 0.4], [y, y], color="#dc2626", linestyle=":", linewidth=1.4, alpha=0.7, zorder=3)
            bubble = Circle((x_slab_min - offset_grid_left, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.0, zorder=6)
            ax.add_patch(bubble)
            ax.text(x_slab_min - offset_grid_left, y, f"X{idx+1}", color="#991b1b", fontsize=13, weight="bold", ha="center", va="center", zorder=7)

        # Columns
        col_c = 1
        for y in y_coords:
            for x in x_coords:
                if (x, y) in rem_coords:
                    continue
                ax.add_patch(patches.Rectangle((x - col_w_m/2.0, y - col_d_m/2.0), col_w_m, col_d_m, linewidth=1.8, edgecolor="#0f172a", facecolor="#1e293b", zorder=6))
                ax.text(x, y, f"C{col_c}", color="#facc15", fontsize=12, ha="center", va="center", weight="bold", zorder=7)
                col_c += 1

        ax.set_title(f"Moment {mode_name} — {dir_label}\n[Max +M: +{m_max:.2f} t.m/m | Max -M: {m_min:.2f} t.m/m]", fontsize=16, weight="bold", pad=12, color="#0f172a")
        ax.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
        ax.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

    fig.suptitle("DUAL BENDING MOMENT CONTOUR MAPS (M11 & M22) — ECP 203 DIRECT DESIGN METHOD", fontsize=22, weight="bold", y=0.98, color="#0f172a")
    return fig


def generate_moment_deficit_contour(
    Lx_spans,
    Ly_spans,
    cantilevers,
    rows_x,
    rows_y,
    Wu,
    prov_btm_mesh_cm2m,
    d_cm,
    Fcu,
    Fy,
    mode="M11",          # "M11" or "M22"
    col_w_cm=30,
    col_d_cm=30,
    removed_cols=None,
    void_panel_ids=None,
):
    """
    Generates a 2D colour-contour map of the MOMENT DEFICIT in the bottom steel.

    Deficit = max(0,  M_field  −  M_cap_btm)

    Green  → bottom mesh is sufficient (Deficit = 0).
    Yellow/Orange/Red → extra bottom steel is required (Deficit > 0).
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    # ── Grid coordinates ──────────────────────────────────────────────────────
    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)

    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    # ── Moment field from DDM ─────────────────────────────────────────────────
    X, Y, M11, M22, M11_raw, M22_raw = build_slab_moment_field(
        Lx_spans, Ly_spans, cantilevers, rows_x, rows_y, Wu,
        void_panel_ids=void_panel_ids
    )

    M_field = M11 if mode == "M11" else M22
    x_vec   = X[0, :]
    y_vec   = Y[:, 0]

    # ── Moment capacity of bottom mesh ────────────────────────────────────────
    M_cap = calc_moment_capacity_btm(prov_btm_mesh_cm2m, d_cm, Fcu, Fy)

    # ── Deficit matrix: only positive moments can be compared to bottom steel ─
    # Negative (hogging) moments are resisted by top steel — not bottom steel.
    # We take only the sagging (+M) part and subtract the capacity.
    M_sagging = np.where(M_field > 0, M_field, 0.0)
    M_deficit = np.where(~np.isnan(M_field), np.maximum(0.0, M_sagging - M_cap), np.nan)

    # ── Figure layout (mirrors existing contour function style) ───────────────
    bubble_radius    = max(0.44, min(slab_w, slab_h) * 0.034)
    offset_grid_top  = max(1.8, slab_h * 0.10)
    offset_grid_left = max(1.8, slab_w * 0.10)
    dim_offset_bot   = max(1.6, slab_h * 0.10)
    dim_offset_right = max(1.5, slab_w * 0.08)

    margin_left  = offset_grid_left + bubble_radius * 2 + 0.6
    margin_right = dim_offset_right + 1.2
    margin_top   = offset_grid_top  + bubble_radius * 2 + 0.6
    margin_bot   = dim_offset_bot   + 1.2

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top  + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.5
    target_plan_w = target_plan_h * ar_plan
    legend_h = 4.5

    fig_w = max(24.0, min(36.0, target_plan_w + 1.6))
    fig_h = max(18.0, min(36.0, target_plan_h + legend_h + 1.2))

    plan_ratio   = (fig_h - legend_h - 1.0) / fig_h
    legend_ratio = legend_h / fig_h

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=150, facecolor="#ffffff")
    gs  = fig.add_gridspec(
        2, 1,
        height_ratios=[plan_ratio, legend_ratio],
        hspace=0.05,
        left=0.02, right=0.96, top=0.94, bottom=0.02,
    )

    ax_plan   = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])

    # ── حساب هل يوجد عجز أم لا (قبل أي رسم) ────────────────────────────────
    valid_def   = M_deficit[~np.isnan(M_deficit) & (M_deficit > 0.001)]
    has_deficit = len(valid_def) > 0
    def_max     = float(np.max(valid_def)) if has_deficit else 1.0

    # ── خلفية بيضاء محايدة دائماً ───────────────────────────────────────────
    ax_plan.set_facecolor("#ffffff")

    if has_deficit:
        # ── pcolormesh بدلاً من contourf ─────────────────────────────────────
        # pcolormesh يرسم كل خلية مستقلة بدون أي interpolation بين الخلايا
        # → الخلية التي قيمتها صفر تبقى بيضاء تماماً حتى لو جارتها أحمر
        M_deficit_draw = np.ma.masked_where(
            (M_deficit <= 0.001) | np.isnan(M_deficit),
            M_deficit,
        )

        cmap_yr = plt.cm.YlOrRd.copy()
        cmap_yr.set_bad(color="none")   # الخلايا المخفية → شفافة تماماً

        norm = mcolors.Normalize(vmin=0.001, vmax=def_max)
        pc = ax_plan.pcolormesh(
            X, Y, M_deficit_draw,
            cmap=cmap_yr,
            norm=norm,
            shading="auto",
            zorder=2,
            alpha=0.93,
        )

        # خطوط iso-value فوق الـ pcolormesh للقراءة السريعة
        line_levels = np.linspace(0.001, def_max, 10)
        try:
            cs_lines = ax_plan.contour(
                X, Y, M_deficit_draw,
                levels=line_levels,
                colors="#7f1d1d",
                linewidths=0.9,
                alpha=0.5,
                zorder=3,
            )
            ax_plan.clabel(cs_lines, inline=True, fontsize=10.5, fmt="%.2f", colors="#7f1d1d")
        except Exception:
            pass   # إذا لم يكن هناك بيانات كافية للخطوط

        # شريط الألوان
        cbar_ax = fig.add_axes([0.965, 0.32, 0.015, 0.58])
        cbar = fig.colorbar(pc, cax=cbar_ax)
        dir_txt = "X-Direction (↔ M11)" if mode == "M11" else "Y-Direction (↕ M22)"
        cbar.set_label(
            f"Moment Deficit  [{mode}] (t·m/m) | فارق العزم السفلي [{dir_txt}]",
            fontsize=13, weight="bold", labelpad=12,
        )
        cbar.ax.tick_params(labelsize=11)

    else:
        # ── لا يوجد عجز — لا يُرسم أي كنتور إطلاقاً، فقط رسالة واضحة ────────
        ax_plan.text(
            (x_slab_min + x_slab_max) / 2.0,
            (y_slab_min + y_slab_max) / 2.0,
            (
                "✓  No Moment Deficit\n"
                "الشبكة السفلية كافية — لا يوجد عجز في العزوم\n\n"
                f"M_cap = {M_cap:.3f} t.m/m\n"
                f"(covers all positive sagging moments)"
            ),
            ha="center", va="center", fontsize=18, weight="bold", color="#15803d",
            linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.7", facecolor="#dcfce7", edgecolor="#16a34a", lw=2.5),
            zorder=10,
        )

    # ── Slab boundary ─────────────────────────────────────────────────────────
    ax_plan.add_patch(patches.Rectangle(
        (x_slab_min, y_slab_min), slab_w, slab_h,
        linewidth=3.5, edgecolor="#0f172a", facecolor="none", zorder=4,
    ))

    # ── Cantilever outlines ───────────────────────────────────────────────────
    cant_style = dict(linewidth=1.6, edgecolor="#1d4ed8", facecolor="none", linestyle="--", zorder=4)
    if cant_left   > 0: ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), cant_left,  slab_h,    **cant_style))
    if cant_right  > 0: ax_plan.add_patch(patches.Rectangle((x_coords[-1], y_slab_min), cant_right, slab_h,   **cant_style))
    if cant_bottom > 0: ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w,    cant_bottom, **cant_style))
    if cant_top    > 0: ax_plan.add_patch(patches.Rectangle((x_slab_min, y_coords[-1]), slab_w,  cant_top,    **cant_style))

    # ── Voids / Openings ─────────────────────────────────────────────────────
    _voids = set(void_panel_ids) if void_panel_ids else set()
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                x1, x2 = x_coords[i], x_coords[i+1]
                y1, y2 = y_coords[j], y_coords[j+1]
                lx, ly = x2 - x1, y2 - y1
                ax_plan.add_patch(patches.Rectangle(
                    (x1, y1), lx, ly,
                    linewidth=2.2, edgecolor="#475569", facecolor="#cbd5e1", zorder=5,
                ))
                ax_plan.plot([x1, x2], [y1, y2], color="#475569", linestyle="--", linewidth=1.8, zorder=5)
                ax_plan.plot([x1, x2], [y2, y1], color="#475569", linestyle="--", linewidth=1.8, zorder=5)
                ax_plan.text(
                    (x1 + x2) / 2.0, (y1 + y2) / 2.0, f"VOID\n{lx*ly:.1f} m²",
                    ha="center", va="center", fontsize=13, weight="bold", color="#0f172a",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#f1f5f9", edgecolor="#64748b", lw=1.5),
                    zorder=6,
                )

    # ── Grid axes & CAD bubbles ───────────────────────────────────────────────
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        ax_plan.plot([x, x], [y_slab_min - 0.6, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=3)
        bub = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x, y_top_ext, f"Y{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        ax_plan.plot([x_left_ext, x_slab_max + 0.6], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.75, zorder=3)
        bub = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x_left_ext, y, f"X{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    # ── Columns ───────────────────────────────────────────────────────────────
    col_w_m   = max(col_w_cm / 100.0, slab_w * 0.045)
    col_d_m   = max(col_d_cm / 100.0, slab_h * 0.045)
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()
    col_idx = 1
    for j_idx, y in enumerate(y_coords):
        for i_idx, x in enumerate(x_coords):
            if (x, y) in rem_coords:
                continue
            ax_plan.add_patch(patches.Rectangle(
                (x - col_w_m / 2.0, y - col_d_m / 2.0), col_w_m, col_d_m,
                linewidth=2.2, edgecolor="#0f172a", facecolor="#1e293b", zorder=6,
            ))
            ax_plan.text(x, y, f"C{col_idx}", color="#facc15", fontsize=13, ha="center", va="center", weight="bold", zorder=7)
            col_idx += 1

    # ── مربعات العجز على كل بلاطة ──────────────────────────────────────────────
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                continue

            mid_x = (x_coords[i] + x_coords[i+1]) / 2.0
            mid_y = (y_coords[j] + y_coords[j+1]) / 2.0

            # ── أقصى عجز داخل حدود البلاطة كاملة (وليس نقطة المنتصف فقط) ──
            ix_lo = np.searchsorted(x_vec, x_coords[i],   side="left")
            ix_hi = np.searchsorted(x_vec, x_coords[i+1], side="right")
            iy_lo = np.searchsorted(y_vec, y_coords[j],   side="left")
            iy_hi = np.searchsorted(y_vec, y_coords[j+1], side="right")

            panel_def = M_deficit[iy_lo:iy_hi+1, ix_lo:ix_hi+1]
            valid_cells = panel_def[~np.isnan(panel_def)]
            max_def = float(np.max(valid_cells)) if len(valid_cells) > 0 else 0.0

            if max_def > 0.01:
                # ── تحديد موقع أقصى عجز (شريط الأعمدة أم منتصف البلاطة) ──────
                flat_idx   = int(np.nanargmax(panel_def))
                local_iy, local_ix = np.unravel_index(flat_idx, panel_def.shape)

                # إحداثيات نقطة أقصى عجز
                max_xi = min(ix_lo + local_ix, len(x_vec) - 1)
                max_yi = min(iy_lo + local_iy, len(y_vec) - 1)
                max_x  = float(x_vec[max_xi])
                max_y  = float(y_vec[max_yi])

                Lx = x_coords[i+1] - x_coords[i]
                Ly = y_coords[j+1] - y_coords[j]

                # عرض شريط الأعمدة = min(Lx, Ly)/4 من كل جانب
                # (وفقاً لـ ECP 203: عرض شريط الأعمدة = نصف أصغر بحر)
                col_hw = min(Lx, Ly) / 4.0

                if mode == "M11":
                    # M11: عزوم أفقية — شريط الأعمدة على طول محاور Y
                    near_col = (
                        (max_y < y_coords[j]   + col_hw) or
                        (max_y > y_coords[j+1] - col_hw)
                    )
                else:
                    # M22: عزوم رأسية — شريط الأعمدة على طول محاور X
                    near_col = (
                        (max_x < x_coords[i]   + col_hw) or
                        (max_x > x_coords[i+1] - col_hw)
                    )

                location_txt = "📍 في شريط الأعمدة" if near_col else "📍 في منتصف البلاطة"

                badge_color  = "#fef3c7"
                border_color = "#d97706"
                txt_color    = "#92400e"
                label = (
                    f"أقصى عجز:\n"
                    f"Δ_max = +{max_def:.2f} t.m/m\n"
                    f"{location_txt}\n"
                    f"حديد سفلي إضافي مطلوب"
                )
            else:
                badge_color  = "#f0fdf4"
                border_color = "#16a34a"
                txt_color    = "#15803d"
                label = (
                    f"✓ الشبكة السفلية كافية\n"
                    f"لا يوجد عجز في أي نقطة\n"
                    f"M_cap = {M_cap:.2f} t.m/m"
                )

            ax_plan.text(
                mid_x, mid_y, label,
                ha="center", va="center", fontsize=11.5, weight="bold", color=txt_color,
                linespacing=1.4,
                bbox=dict(boxstyle="round,pad=0.35", facecolor=badge_color, edgecolor=border_color, lw=1.8),
                zorder=8,
            )

    # ── Span dimensions ───────────────────────────────────────────────────────
    y_dim_lx = y_slab_min - dim_offset_bot
    for i, lx in enumerate(Lx_spans):
        mid_x = (x_coords[i] + x_coords[i+1]) / 2.0
        ax_plan.annotate("", xy=(x_coords[i+1], y_dim_lx), xytext=(x_coords[i], y_dim_lx),
                         arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0))
        ax_plan.plot([x_coords[i], x_coords[i]],     [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.plot([x_coords[i+1], x_coords[i+1]], [y_dim_lx - 0.35, y_dim_lx + 0.35], color="#0f172a", lw=1.8)
        ax_plan.text(mid_x, y_dim_lx - 0.45, f"{lx:.2f} m", color="#0f172a", fontsize=16.5, weight="bold", ha="center", va="top")

    dim_offset_right_plot = max(1.6, slab_w * 0.10)
    x_dim_ly = x_slab_max + dim_offset_right_plot
    for j, ly in enumerate(Ly_spans):
        mid_y = (y_coords[j] + y_coords[j+1]) / 2.0
        ax_plan.annotate("", xy=(x_dim_ly, y_coords[j+1]), xytext=(x_dim_ly, y_coords[j]),
                         arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=2.4, shrinkA=0, shrinkB=0))
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j],   y_coords[j]],   color="#0f172a", lw=1.8)
        ax_plan.plot([x_dim_ly - 0.35, x_dim_ly + 0.35], [y_coords[j+1], y_coords[j+1]], color="#0f172a", lw=1.8)
        ax_plan.text(x_dim_ly + 0.45, mid_y, f"{ly:.2f} m", color="#0f172a", fontsize=16.5, weight="bold", ha="left", va="center")

    ax_plan.set_xlim(x_slab_min - margin_left,  x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot,   y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.axis("off")

    # ── Legend block ──────────────────────────────────────────────────────────
    ax_legend.set_facecolor("#ffffff")
    ax_legend.axis("off")
    ax_legend.set_xlim(0, 1)
    ax_legend.set_ylim(0, 1)

    ax_legend.add_patch(FancyBboxPatch(
        (0.005, 0.02), 0.99, 0.96,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        linewidth=2.4, edgecolor="#0f172a", facecolor="#f8fafc", zorder=1,
    ))

    dir_txt_ar = "اتجاه المحور الأفقي X" if mode == "M11" else "اتجاه المحور الرأسي Y"
    cards_info = [
        (
            f"BOTTOM MESH CAPACITY ({mode})\n(طاقة الشبكة السفلية)",
            f"M_cap = {M_cap:.3f} t.m/m\n(prov. = {prov_btm_mesh_cm2m:.2f} cm²/m, d = {d_cm:.1f} cm)",
            "#1e40af", "#dbeafe", "#2563eb",
        ),
        (
            "COLOUR CODE\n(دلالة الألوان)",
            (
                "⬜ White  → Deficit = 0  (Mesh Sufficient)\n🟡→🔴 Yellow-Red → Extra Bottom Steel Needed"
                if has_deficit else
                "⬜ All Zones: No Deficit\n✓ Base Mesh Covers Everything"
            ),
            "#b45309", "#fef3c7", "#d97706",
        ),
        (
            "DEFICIT DEFINITION\n(تعريف الفارق)",
            f"Δ = max(0,  M_{mode} − M_cap)\nOnly positive (sagging) moments compared",
            "#15803d", "#dcfce7", "#16a34a",
        ),
        (
            "EXTREME VALUES\n(القيم القصوى)",
            (f"Max Deficit: {float(np.nanmax(M_deficit)):.3f} t.m/m\nM_cap Provided: {M_cap:.3f} t.m/m"
             if has_deficit else
             "Max Deficit: 0.000 t.m/m\n✓ All zones covered by base mesh"),
            "#0f172a", "#f1f5f9", "#64748b",
        ),
    ]

    x_box_w   = 0.235
    x_box_gap = 0.012
    x_start   = 0.015
    for k, (title, content, t_color, bg_color, border_color) in enumerate(cards_info):
        bx = x_start + k * (x_box_w + x_box_gap)
        ax_legend.add_patch(FancyBboxPatch(
            (bx, 0.04), x_box_w, 0.92,
            boxstyle="round,pad=0.015,rounding_size=0.02",
            linewidth=1.6, edgecolor=border_color, facecolor=bg_color, zorder=2,
        ))
        ax_legend.text(bx + x_box_w / 2.0, 0.74, title,
                       ha="center", va="center", fontsize=14.5, weight="bold", color=t_color, linespacing=1.2, zorder=3)
        ax_legend.text(bx + x_box_w / 2.0, 0.28, content,
                       ha="center", va="center", fontsize=13.5, color="#1e293b", weight="normal", linespacing=1.25, zorder=3)

    if has_deficit:
        _main_title = (
            f"BOTTOM STEEL MOMENT DEFICIT CONTOUR — {mode}"
            f"  |  كونتور فارق العزوم السفلي — {dir_txt_ar}"
        )
        _title_color = "#7f1d1d"
    else:
        _main_title = (
            f"✓ BOTTOM MESH SUFFICIENT — NO DEFICIT ({mode})"
            f"  |  الشبكة السفلية كافية — لا يوجد عجز — {dir_txt_ar}"
        )
        _title_color = "#15803d"

    fig.suptitle(_main_title, fontsize=19, weight="bold", y=0.98, color=_title_color)

    return fig


def generate_flat_slab_rebar_bending_details(
    Lx_spans, Ly_spans, cantilevers, ts_cm,
    mesh_btm_n, mesh_btm_dia,
    mesh_top_n, mesh_top_dia,
    col_extras, cant_rft_list,
    btm_extra_spans=None,
    void_panels=None,
    bc_cm=30, tc_cm=30,
):
    """
    Generates a professional engineering BBS & Rebar Detailing sheet (اسكتش تفريد وتفاصيل الحديد)
    showing M11, M22, Column Caps, Additional Bottom Steel, Cantilevers, Edge U-Pins, and Chairs,
    complete with rebar shapes, cutting lengths, bar counts, covered areas, and weights.
    """
    cant_L = cantilevers.get("left", 0.0)
    cant_R = cantilevers.get("right", 0.0)
    cant_B = cantilevers.get("bottom", 0.0)
    cant_T = cantilevers.get("top", 0.0)

    total_w = sum(Lx_spans) + cant_L + cant_R
    total_h = sum(Ly_spans) + cant_B + cant_T
    gross_area = total_w * total_h
    void_area = sum(p["area"] for p in void_panels if p.get("is_void")) if void_panels else 0.0
    slab_area = max(0.1, gross_area - void_area)

    uw = lambda dia: (dia ** 2) / 162.0

    # 1. M11 Bottom Mesh (X-dir)
    n_runs_m11 = int(np.ceil(total_h * mesh_btm_n))
    L_bar_m11 = total_w + 0.30
    tot_len_m11_btm = n_runs_m11 * L_bar_m11
    wt_m11_btm = tot_len_m11_btm * uw(mesh_btm_dia)
    area_m11 = slab_area

    # 2. M22 Bottom Mesh (Y-dir)
    n_runs_m22 = int(np.ceil(total_w * mesh_btm_n))
    L_bar_m22 = total_h + 0.30
    tot_len_m22_btm = n_runs_m22 * L_bar_m22
    wt_m22_btm = tot_len_m22_btm * uw(mesh_btm_dia)
    area_m22 = slab_area

    # 3. Top Mesh (T1, T2 in X & Y)
    n_runs_top_x = int(np.ceil(total_h * mesh_top_n))
    n_runs_top_y = int(np.ceil(total_w * mesh_top_n))
    L_bar_top_x = total_w + 0.20
    L_bar_top_y = total_h + 0.20
    tot_len_top = (n_runs_top_x * L_bar_top_x) + (n_runs_top_y * L_bar_top_y)
    wt_top_mesh = tot_len_top * uw(mesh_top_dia)

    # 4. Column Caps Top Extra
    active_caps = [ce for ce in col_extras if ce.get("is_needed")]
    tot_cap_bars = sum(ce.get("n_extra", 0) for ce in active_caps)
    tot_cap_len = sum(ce.get("n_extra", 0) * ce.get("L_extra", 0) for ce in active_caps)
    cap_dia = active_caps[0].get("dia_extra", 12) if active_caps else 12
    wt_caps = tot_cap_len * uw(cap_dia)
    avg_Lx = float(np.mean(Lx_spans)) if Lx_spans else 5.0
    avg_Ly = float(np.mean(Ly_spans)) if Ly_spans else 5.0
    cap_cov_w = min(avg_Lx, avg_Ly) / 2.0
    cap_cov_area = len(active_caps) * (cap_cov_w ** 2)

    # 5. Additional Bottom Steel in Bays
    active_btm_extras = [be for be in (btm_extra_spans or []) if isinstance(be, dict) and be.get("n_extra", 0) > 0]
    tot_btm_ex_bars = sum(be.get("n_extra", 0) for be in active_btm_extras)
    tot_btm_ex_len = sum(be.get("n_extra", 0) * be.get("L_extra", 4.0) for be in active_btm_extras)
    btm_ex_dia = active_btm_extras[0].get("dia_extra", 12) if active_btm_extras else 12
    wt_btm_ex = tot_btm_ex_len * uw(btm_ex_dia)
    btm_ex_area = sum(be.get("span_len", 5.0) * avg_Ly for be in active_btm_extras)

    # 6. Cantilever Shawka
    tot_cant_bars = 0
    tot_cant_len = 0.0
    cant_area = 0.0
    for cr in cant_rft_list:
        s_len = total_w if cr["side"] in ["bottom", "top"] else total_h
        n_c = int(np.ceil(s_len * 6.0))
        tot_cant_bars += n_c
        tot_cant_len += n_c * cr["total_bar_length"]
        cant_area += s_len * cr["length"]
    wt_cant = tot_cant_len * uw(12)

    # 7. Edge U-Pins & Trim
    perim = 2.0 * (total_w + total_h)
    n_upins = int(np.ceil(perim / 0.20))
    l_upin_each = 2.0 * 0.35 + (ts_cm - 5.0) / 100.0
    tot_upins_len = n_upins * l_upin_each
    wt_upins = tot_upins_len * uw(10)

    # 8. Chairs & Spacers
    n_chairs = int(np.ceil(slab_area * 1.0))
    h_chair = max(0.08, (ts_cm - 5.0 - 4.0) / 100.0)
    l_chair_each = 2 * h_chair + 0.40
    tot_chair_len = n_chairs * l_chair_each
    wt_chairs = tot_chair_len * uw(12)

    # Create 8-panel grid figure (4 rows x 2 columns)
    fig, axes = plt.subplots(4, 2, figsize=(18, 20), dpi=140)
    fig.patch.set_facecolor("#ffffff")

    plt.subplots_adjust(left=0.04, right=0.96, top=0.945, bottom=0.025, hspace=0.36, wspace=0.20)

    fig.suptitle(
        "FLAT SLAB REINFORCEMENT BENDING SCHEDULE & CURTAILMENT DETAILS (ECP 203)",
        fontsize=16.5, fontweight="bold", color="#0f172a", y=0.985
    )

    panels = [
        {
            "ax": axes[0, 0],
            "title": "1. M11 — BOTTOM MESH (X-DIRECTION)",
            "bg": "#eff6ff", "border": "#3b82f6",
            "draw_func": "m11_btm",
            "dia": mesh_btm_dia, "count": n_runs_m11, "L_cut": L_bar_m11,
            "density": f"{mesh_btm_n} Φ{mesh_btm_dia}/m'",
            "cov_area": f"{area_m11:.1f} m² (Full Slab Width Wx={total_w:.2f}m)",
            "tot_len": f"{tot_len_m11_btm:,.1f} m'", "weight": f"{wt_m11_btm/1000.0:.3f} Ton ({wt_m11_btm:,.0f} kg)",
            "notes": "Straight continuous bottom bar extending 15 cm past exterior support centerline."
        },
        {
            "ax": axes[0, 1],
            "title": "2. M22 — BOTTOM MESH (Y-DIRECTION)",
            "bg": "#eff6ff", "border": "#3b82f6",
            "draw_func": "m22_btm",
            "dia": mesh_btm_dia, "count": n_runs_m22, "L_cut": L_bar_m22,
            "density": f"{mesh_btm_n} Φ{mesh_btm_dia}/m'",
            "cov_area": f"{area_m22:.1f} m² (Full Slab Height Wy={total_h:.2f}m)",
            "tot_len": f"{tot_len_m22_btm:,.1f} m'", "weight": f"{wt_m22_btm/1000.0:.3f} Ton ({wt_m22_btm:,.0f} kg)",
            "notes": "Straight continuous bottom bar spanning across Ly spans perpendicular to M11."
        },
        {
            "ax": axes[1, 0],
            "title": "3. TOP BASE MESH (T1 & T2 — X & Y)",
            "bg": "#f0fdf4", "border": "#22c55e",
            "draw_func": "top_mesh",
            "dia": mesh_top_dia, "count": n_runs_top_x + n_runs_top_y, "L_cut": (L_bar_top_x + L_bar_top_y)/2.0,
            "density": f"{mesh_top_n} Φ{mesh_top_dia}/m' (X & Y)",
            "cov_area": f"{slab_area:.1f} m² (Full Top Slab Surface)",
            "tot_len": f"{tot_len_top:,.1f} m'", "weight": f"{wt_top_mesh/1000.0:.3f} Ton ({wt_top_mesh:,.0f} kg)",
            "notes": "Top nominal crack-control mesh with 90° standard down-hooks at slab boundary edges."
        },
        {
            "ax": axes[1, 1],
            "title": "4. COLUMN CAPS / TOP EXTRA REINFORCEMENT",
            "bg": "#fef2f2", "border": "#ef4444",
            "draw_func": "col_caps",
            "dia": cap_dia, "count": tot_cap_bars if tot_cap_bars else "— (0)", "L_cut": active_caps[0]["L_extra"] if active_caps else 3.5,
            "density": f"Top Extra @ {len(active_caps)} Cols (Col Strip w={cap_cov_w:.2f}m)",
            "cov_area": f"{cap_cov_area:.1f} m² (Column Strips Negative Moment Zones)",
            "tot_len": f"{tot_cap_len:,.1f} m'" if tot_cap_len else "0.0 m'", "weight": f"{wt_caps/1000.0:.3f} Ton ({wt_caps:,.0f} kg)" if wt_caps else "0.00 Ton (Base Mesh Covers -M)",
            "notes": "Placed in Column Strip over columns. Length = 0.50 Ln + bc (0.25 Ln each side) with 90° hooks."
        },
        {
            "ax": axes[2, 0],
            "title": "5. ADDITIONAL BOTTOM STEEL (ENLARGED BAYS)",
            "bg": "#fffbeb", "border": "#f59e0b",
            "draw_func": "btm_extra",
            "dia": btm_ex_dia, "count": tot_btm_ex_bars if tot_btm_ex_bars else "— (0)", "L_cut": active_btm_extras[0]["L_extra"] if active_btm_extras else 4.0,
            "density": f"Bottom Extra @ {len(active_btm_extras)} Bay Zones",
            "cov_area": f"{btm_ex_area:.1f} m² (Middle Strips Positive Moment Zones)" if btm_ex_area else "0.0 m² (Base mesh is sufficient)",
            "tot_len": f"{tot_btm_ex_len:,.1f} m'" if tot_btm_ex_len else "0.0 m'", "weight": f"{wt_btm_ex/1000.0:.3f} Ton ({wt_btm_ex:,.0f} kg)" if wt_btm_ex else "0.00 Ton (Base Mesh Covers +M)",
            "notes": "Centered in enlarged bays to resist +M moments. Cut length ≈ 0.80 Ln."
        },
        {
            "ax": axes[2, 1],
            "title": "6. CANTILEVER SHAWKA & SECONDARY REBAR",
            "bg": "#faf5ff", "border": "#a855f7",
            "draw_func": "cantilever",
            "dia": 12, "count": tot_cant_bars if tot_cant_bars else "— (0)", "L_cut": cant_rft_list[0]["total_bar_length"] if cant_rft_list else 3.5,
            "density": "6 Φ12 / m' + Secondary 5Φ10/m'" if tot_cant_bars else "No cantilevers defined",
            "cov_area": f"{cant_area:.1f} m² (Cantilever Overhangs)" if cant_area else "0.0 m²",
            "tot_len": f"{tot_cant_len:,.1f} m'" if tot_cant_len else "0.0 m'", "weight": f"{wt_cant/1000.0:.3f} Ton ({wt_cant:,.0f} kg)" if wt_cant else "0.00 Ton",
            "notes": "Main top Shawka extends 1.5 L_cant into slab + edge loop + 0.5 L_cant bottom return leg."
        },
        {
            "ax": axes[3, 0],
            "title": "7. PERIMETER U-PINS & BOUNDARY EDGE REBAR",
            "bg": "#f8fafc", "border": "#64748b",
            "draw_func": "upins",
            "dia": 10, "count": n_upins, "L_cut": l_upin_each,
            "density": "U-Pins Φ10 @ 20 cm + 4Φ12 Edge Bars",
            "cov_area": f"Perimeter = {perim:.1f} m' (All Free Boundary Edges)",
            "tot_len": f"{tot_upins_len:,.1f} m'", "weight": f"{wt_upins/1000.0:.3f} Ton ({wt_upins:,.0f} kg)",
            "notes": "U-shaped hairpins enclosing slab edge depth ts with 2 top & 2 bottom longitudinal bars."
        },
        {
            "ax": axes[3, 1],
            "title": "8. REBAR CHAIRS & TOP MESH SUPPORTS",
            "bg": "#f1f5f9", "border": "#475569",
            "draw_func": "chairs",
            "dia": 12, "count": n_chairs, "L_cut": l_chair_each,
            "density": "1 Chair / m² (Spaced @ 1.0 m grid)",
            "cov_area": f"{slab_area:.1f} m² (Top Mesh Support Grid)",
            "tot_len": f"{tot_chair_len:,.1f} m'", "weight": f"{wt_chairs/1000.0:.3f} Ton ({wt_chairs:,.0f} kg)",
            "notes": "Chairs with height h = ts - 2*cov - 4*dia to rigidly support top rebar mesh during concreting."
        },
    ]

    for p in panels:
        ax = p["ax"]
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis("off")

        # Background card
        rect = patches.FancyBboxPatch(
            (1, 1), 98, 98,
            boxstyle="round,pad=1.5,rounding_size=4",
            facecolor=p["bg"],
            edgecolor=p["border"],
            linewidth=2.0,
        )
        ax.add_patch(rect)

        # Header Title Strip
        title_box = patches.FancyBboxPatch(
            (2, 82), 96, 15,
            boxstyle="round,pad=1.0,rounding_size=3",
            facecolor=p["border"],
            edgecolor="none",
        )
        ax.add_patch(title_box)
        ax.text(50, 89.5, p["title"], ha="center", va="center", fontsize=11.5, fontweight="bold", color="#ffffff")

        # Draw Sketch depending on item
        dfunc = p["draw_func"]
        if dfunc == "m11_btm":
            ax.plot([15, 85], [60, 60], color="#1e40af", lw=4.5, solid_capstyle="round")
            ax.plot([15, 15], [56, 64], color="#1e40af", lw=3.0)
            ax.plot([85, 85], [56, 64], color="#1e40af", lw=3.0)
            ax.annotate("", xy=(85, 52), xytext=(15, 52), arrowprops=dict(arrowstyle="<->", color="#1e40af", lw=1.8))
            ax.text(50, 48, f"Cutting Length L = {p['L_cut']:.2f} m'  (Total Width Wx = {total_w:.2f} m)", ha="center", va="center", fontsize=10.5, fontweight="bold", color="#1e40af")
            ax.text(50, 66, f"Straight Bottom Bar — Φ {p['dia']} mm", ha="center", va="center", fontsize=10.0, fontweight="bold", color="#0f172a")

        elif dfunc == "m22_btm":
            ax.plot([15, 85], [60, 60], color="#1e40af", lw=4.5, solid_capstyle="round")
            ax.plot([15, 15], [56, 64], color="#1e40af", lw=3.0)
            ax.plot([85, 85], [56, 64], color="#1e40af", lw=3.0)
            ax.annotate("", xy=(85, 52), xytext=(15, 52), arrowprops=dict(arrowstyle="<->", color="#1e40af", lw=1.8))
            ax.text(50, 48, f"Cutting Length L = {p['L_cut']:.2f} m'  (Total Height Wy = {total_h:.2f} m)", ha="center", va="center", fontsize=10.5, fontweight="bold", color="#1e40af")
            ax.text(50, 66, f"Straight Bottom Bar — Φ {p['dia']} mm", ha="center", va="center", fontsize=10.0, fontweight="bold", color="#0f172a")

        elif dfunc == "top_mesh":
            ax.plot([20, 80], [64, 64], color="#16a34a", lw=4.0)
            ax.plot([20, 20], [64, 52], color="#16a34a", lw=4.0)
            ax.plot([80, 80], [64, 52], color="#16a34a", lw=4.0)
            ax.text(14, 58, f"Hook {ts_cm-5:.0f}cm", ha="center", va="center", fontsize=8.5, color="#15803d")
            ax.text(86, 58, f"Hook {ts_cm-5:.0f}cm", ha="center", va="center", fontsize=8.5, color="#15803d")
            ax.annotate("", xy=(80, 47), xytext=(20, 47), arrowprops=dict(arrowstyle="<->", color="#16a34a", lw=1.8))
            ax.text(50, 43, f"Span Length L ≈ {p['L_cut']:.2f} m'", ha="center", va="center", fontsize=10.5, fontweight="bold", color="#15803d")
            ax.text(50, 70, f"Top Mesh Bar with 90° Down-Hooks — Φ {p['dia']} mm", ha="center", va="center", fontsize=10.0, fontweight="bold", color="#0f172a")

        elif dfunc == "col_caps":
            ax.plot([22, 78], [64, 64], color="#dc2626", lw=4.5)
            ax.plot([22, 22], [64, 54], color="#dc2626", lw=4.5)
            ax.plot([78, 78], [64, 54], color="#dc2626", lw=4.5)
            ax.plot([50, 50], [48, 74], color="#64748b", ls="--", lw=1.8)
            ax.text(50, 76, "CL Column", ha="center", va="center", fontsize=9.0, color="#475569", fontweight="bold")
            ax.annotate("", xy=(50, 50), xytext=(22, 50), arrowprops=dict(arrowstyle="<->", color="#dc2626", lw=1.5))
            ax.annotate("", xy=(78, 50), xytext=(50, 50), arrowprops=dict(arrowstyle="<->", color="#dc2626", lw=1.5))
            ax.text(36, 46, "0.25 Ln", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#dc2626")
            ax.text(64, 46, "0.25 Ln", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#dc2626")
            ax.text(50, 70, f"Top Extra Cap Bar — Φ {p['dia']} mm (L_ext = {p['L_cut']:.2f} m)", ha="center", va="center", fontsize=10.0, fontweight="bold", color="#991b1b")

        elif dfunc == "btm_extra":
            ax.plot([25, 75], [60, 60], color="#d97706", lw=5.0)
            ax.plot([25, 25], [56, 64], color="#d97706", lw=2.5)
            ax.plot([75, 75], [56, 64], color="#d97706", lw=2.5)
            ax.plot([12, 12], [48, 72], color="#94a3b8", ls=":", lw=1.8)
            ax.plot([88, 88], [48, 72], color="#94a3b8", ls=":", lw=1.8)
            ax.text(12, 75, "Col A", ha="center", va="center", fontsize=8.5, color="#64748b")
            ax.text(88, 75, "Col B", ha="center", va="center", fontsize=8.5, color="#64748b")
            ax.annotate("", xy=(75, 52), xytext=(25, 52), arrowprops=dict(arrowstyle="<->", color="#d97706", lw=1.8))
            ax.text(50, 48, f"Cut Length L_ext ≈ 0.80 Ln = {p['L_cut']:.2f} m'", ha="center", va="center", fontsize=10.0, fontweight="bold", color="#b45309")
            ax.text(50, 67, f"Bottom Extra Bar (Mid-Span) — Φ {p['dia']} mm", ha="center", va="center", fontsize=10.0, fontweight="bold", color="#0f172a")

        elif dfunc == "cantilever":
            ax.plot([15, 80], [66, 66], color="#9333ea", lw=4.0)
            ax.plot([80, 85, 85, 80], [66, 66, 56, 56], color="#9333ea", lw=4.0)
            ax.plot([80, 45], [56, 56], color="#9333ea", lw=4.0)
            ax.plot([45, 45], [56, 60], color="#9333ea", lw=3.0)
            ax.plot([15, 15], [66, 60], color="#9333ea", lw=3.0)
            ax.plot([50, 50], [48, 74], color="#64748b", ls="--", lw=1.8)
            ax.text(50, 76, "Slab Edge / Col", ha="center", va="center", fontsize=8.5, color="#475569", fontweight="bold")
            ax.text(32, 70, "1.5 L_cant", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#7e22ce")
            ax.text(68, 70, "L_cant", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#7e22ce")
            ax.text(50, 46, f"Total Cutting Length = {p['L_cut']:.2f} m'", ha="center", va="center", fontsize=10.0, fontweight="bold", color="#7e22ce")

        elif dfunc == "upins":
            ax.plot([25, 75], [66, 66], color="#475569", lw=4.0)
            ax.plot([75, 80, 80, 75], [66, 66, 54, 54], color="#475569", lw=4.0)
            ax.plot([75, 25], [54, 54], color="#475569", lw=4.0)
            for bx, by in [(35, 62), (65, 62), (35, 58), (65, 58)]:
                c_dot = patches.Circle((bx, by), 1.5, facecolor="#0284c7", edgecolor="none")
                ax.add_patch(c_dot)
            ax.text(50, 71, "Top Leg 35cm", ha="center", va="center", fontsize=8.5, color="#475569")
            ax.text(50, 49, "Bottom Leg 35cm", ha="center", va="center", fontsize=8.5, color="#475569")
            ax.text(86, 60, f"{ts_cm-5:.0f}cm", ha="left", va="center", fontsize=8.5, color="#475569")
            ax.text(50, 43, f"Cutting Length = {p['L_cut']:.2f} m' + 4Φ12 Edge Bars", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#1e293b")

        elif dfunc == "chairs":
            ax.plot([25, 35], [52, 52], color="#334155", lw=4.0)
            ax.plot([35, 42], [52, 66], color="#334155", lw=4.0)
            ax.plot([42, 58], [66, 66], color="#334155", lw=4.0)
            ax.plot([58, 65], [66, 52], color="#334155", lw=4.0)
            ax.plot([65, 75], [52, 52], color="#334155", lw=4.0)
            c_car = patches.Circle((50, 68), 2.0, facecolor="#dc2626", edgecolor="none")
            ax.add_patch(c_car)
            ax.text(50, 73, "Carrier Rebar", ha="center", va="center", fontsize=8.5, color="#b91c1c", fontweight="bold")
            ax.text(20, 60, f"h = {h_chair*100:.0f}cm", ha="center", va="center", fontsize=8.5, color="#334155")
            ax.text(50, 44, f"Chair Cut Length = {p['L_cut']:.2f} m' (Height = {h_chair*100:.0f} cm)", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#1e293b")

        # Metric & Info Strip below drawing
        info_box = patches.FancyBboxPatch(
            (3, 4), 94, 34,
            boxstyle="round,pad=0.8,rounding_size=3",
            facecolor="#ffffff",
            edgecolor="#cbd5e1",
            linewidth=1.2,
        )
        ax.add_patch(info_box)

        t_y = 33
        ax.text(6, t_y, "• Total Bar Count:", fontsize=10.0, fontweight="bold", color="#1e293b")
        ax.text(42, t_y, f"{p['count']} pcs", fontsize=10.0, fontweight="bold", color="#1e40af")
        ax.text(58, t_y, f"Density: {p['density']}", fontsize=9.5, color="#64748b")

        t_y -= 7.5
        ax.text(6, t_y, "• Covered Area / Strip:", fontsize=10.0, fontweight="bold", color="#1e293b")
        ax.text(42, t_y, f"{p['cov_area']}", fontsize=10.0, fontweight="bold", color="#047857")

        t_y -= 7.5
        ax.text(6, t_y, "• Length & Weight:", fontsize=10.0, fontweight="bold", color="#1e293b")
        ax.text(42, t_y, f"{p['tot_len']}  |  {p['weight']}", fontsize=10.0, fontweight="bold", color="#7e22ce")

        t_y -= 7.5
        ax.text(6, t_y, f"• Code Detailing: {p['notes']}", fontsize=8.8, color="#475569", style="italic")

    return fig


# ── 1. COLUMN CAPS (TOP EXTRA) ───────────────────────────────────────────────
def generate_flat_slab_column_caps_sketch(
    Lx_spans, Ly_spans, cantilevers, ts_cm,
    top_extra_cols,
    col_w_cm=30, col_d_cm=30,
    removed_cols=None, void_panel_ids=None,
):
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    bubble_radius = max(0.50, min(slab_w, slab_h) * 0.038)
    offset_grid_top = max(2.2, slab_h * 0.11)
    offset_grid_left = max(2.2, slab_w * 0.11)
    dim_offset_bot = max(2.0, slab_h * 0.11)
    dim_offset_right = max(1.8, slab_w * 0.09)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.8
    margin_right = dim_offset_right + 1.5
    margin_top = offset_grid_top + bubble_radius * 2 + 0.8
    margin_bot = dim_offset_bot + 1.5

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.0
    target_plan_w = target_plan_h * ar_plan
    legend_h = 5.2

    fig_w = max(22.0, min(34.0, target_plan_w + 1.6))
    fig_h = max(18.0, min(32.0, target_plan_h + legend_h + 1.0))

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=140)
    fig.patch.set_facecolor("#ffffff")

    plan_ratio = (fig_h - legend_h - 0.8) / fig_h
    legend_ratio = legend_h / fig_h

    gs = fig.add_gridspec(2, 1, height_ratios=[plan_ratio, legend_ratio], hspace=0.06, left=0.03, right=0.97, top=0.94, bottom=0.02)
    ax_plan = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])
    ax_plan.set_facecolor("#f8fafc")

    ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, slab_h, lw=3.2, edgecolor="#0f172a", facecolor="#ffffff", zorder=1))

    _voids = set(void_panel_ids) if void_panel_ids else set()
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                px0, px1 = x_coords[i], x_coords[i+1]
                py0, py1 = y_coords[j], y_coords[j+1]
                pw, ph = px1 - px0, py1 - py0
                v_rect = patches.Rectangle((px0, py0), pw, ph, facecolor="#f1f5f9", edgecolor="#ef4444", lw=2.2, hatch="//", zorder=2)
                ax_plan.add_patch(v_rect)
                ax_plan.text(px0 + pw/2, py0 + ph/2, "OPENING / VOID", ha="center", va="center", fontsize=13, fontweight="bold", color="#b91c1c", zorder=4, bbox=dict(boxstyle="round,pad=0.4", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.5))

    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        ax_plan.plot([x, x], [y_slab_min - 0.5, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=3)
        bub = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x, y_top_ext, f"Y{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        ax_plan.plot([x_left_ext, x_slab_max + 0.5], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=3)
        bub = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x_left_ext, y, f"X{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    col_w_m   = max(col_w_cm / 100.0, slab_w * 0.042)
    col_d_m   = max(col_d_cm / 100.0, slab_h * 0.042)
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()
    col_dict = {}
    col_idx = 1
    for j_idx, y in enumerate(y_coords):
        for i_idx, x in enumerate(x_coords):
            if (x, y) in rem_coords:
                continue
            cid = f"C{col_idx}"
            col_dict[cid] = (x, y, i_idx, j_idx)
            ax_plan.add_patch(patches.Rectangle((x - col_w_m / 2.0, y - col_d_m / 2.0), col_w_m, col_d_m, lw=2.2, edgecolor="#0f172a", facecolor="#1e293b", zorder=8))
            ax_plan.text(x, y, cid, color="#facc15", fontsize=13, ha="center", va="center", weight="bold", zorder=9)
            col_idx += 1

    active_caps_count = 0
    for c_info in (top_extra_cols or []):
        cid = c_info["id"]
        if cid not in col_dict:
            continue
        cx, cy, ci, cj = col_dict[cid]
        is_needed = c_info.get("is_needed", False)
        L_ext = c_info.get("L_extra", 3.0)
        n_ext = c_info.get("n_extra", 6)
        dia_ext = c_info.get("dia_extra", 12)
        callout = c_info.get("callout", f"{n_ext}Φ{dia_ext}")

        if is_needed:
            active_caps_count += 1
            cap_w = L_ext
            cap_h = min(Lx_spans[min(ci, len(Lx_spans)-1)], Ly_spans[min(cj, len(Ly_spans)-1)]) * 0.45
            cap_rect = patches.Rectangle(
                (cx - cap_w/2.0, cy - cap_h/2.0), cap_w, cap_h,
                lw=2.0, edgecolor="#dc2626", facecolor="#fee2e2", alpha=0.55, linestyle="--", zorder=4
            )
            ax_plan.add_patch(cap_rect)

            bar_y = cy + col_d_m/2.0 + 0.15
            ax_plan.plot([cx - cap_w/2.0, cx + cap_w/2.0], [bar_y, bar_y], color="#b91c1c", lw=4.0, zorder=6)
            ax_plan.plot([cx - cap_w/2.0, cx - cap_w/2.0], [bar_y, bar_y - 0.25], color="#b91c1c", lw=3.0, zorder=6)
            ax_plan.plot([cx + cap_w/2.0, cx + cap_w/2.0], [bar_y, bar_y - 0.25], color="#b91c1c", lw=3.0, zorder=6)

            bar_x = cx + col_w_m/2.0 + 0.15
            ax_plan.plot([bar_x, bar_x], [cy - cap_h/2.0, cy + cap_h/2.0], color="#b91c1c", lw=4.0, zorder=6)
            ax_plan.plot([bar_x, bar_x - 0.25], [cy - cap_h/2.0, cy - cap_h/2.0], color="#b91c1c", lw=3.0, zorder=6)
            ax_plan.plot([bar_x, bar_x - 0.25], [cy + cap_h/2.0, cy + cap_h/2.0], color="#b91c1c", lw=3.0, zorder=6)

            # Alternating Callout Placement (الكتابة بالتبادل لتجنب التداخل)
            is_above = ((ci + cj) % 2 == 0)
            if is_above:
                tag_y = cy + cap_h/2.0 + 0.35
                va_pos = "bottom"
            else:
                tag_y = cy - cap_h/2.0 - 0.35
                va_pos = "top"

            ax_plan.text(
                cx, tag_y,
                f"★ {cid} Top Cap: {n_ext}Φ{dia_ext}\n"
                f"Strip Dim: {cap_w:.2f}m (L) × {cap_h:.2f}m (W)",
                ha="center", va=va_pos, fontsize=12.0, fontweight="bold", color="#991b1b", zorder=8,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#ffffff", edgecolor="#dc2626", lw=1.8)
            )
        else:
            is_above = ((ci + cj) % 2 == 0)
            tag_y = (cy + col_d_m/2.0 + 0.25) if is_above else (cy - col_d_m/2.0 - 0.25)
            va_pos = "bottom" if is_above else "top"
            ax_plan.text(
                cx, tag_y, f"{cid}: Base Mesh OK",
                ha="center", va=va_pos, fontsize=11.0, fontweight="bold", color="#15803d", zorder=7,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#f0fdf4", edgecolor="#22c55e", lw=1.2)
            )

    dim_y = y_slab_min - dim_offset_bot
    if cant_left > 0:
        ax_plan.annotate("", xy=(x_coords[0], dim_y), xytext=(x_slab_min, dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text((x_slab_min + x_coords[0])/2.0, dim_y - 0.4, f"{cant_left:.2f}m", ha="center", va="top", fontsize=13, fontweight="bold", color="#0f172a")
    for i, lx in enumerate(Lx_spans):
        x0, x1 = x_coords[i], x_coords[i+1]
        ax_plan.annotate("", xy=(x1, dim_y), xytext=(x0, dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text((x0 + x1)/2.0, dim_y - 0.4, f"{lx:.2f}m", ha="center", va="top", fontsize=13, fontweight="bold", color="#0f172a")
    if cant_right > 0:
        ax_plan.annotate("", xy=(x_slab_max, dim_y), xytext=(x_coords[-1], dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text((x_coords[-1] + x_slab_max)/2.0, dim_y - 0.4, f"{cant_right:.2f}m", ha="center", va="top", fontsize=13, fontweight="bold", color="#0f172a")

    dim_x = x_slab_max + dim_offset_right
    if cant_bottom > 0:
        ax_plan.annotate("", xy=(dim_x, y_coords[0]), xytext=(dim_x, y_slab_min), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text(dim_x + 0.4, (y_slab_min + y_coords[0])/2.0, f"{cant_bottom:.2f}m", ha="left", va="center", fontsize=13, fontweight="bold", color="#0f172a")
    for j, ly in enumerate(Ly_spans):
        y0, y1 = y_coords[j], y_coords[j+1]
        ax_plan.annotate("", xy=(dim_x, y1), xytext=(dim_x, y0), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text(dim_x + 0.4, (y0 + y1)/2.0, f"{ly:.2f}m", ha="left", va="center", fontsize=13, fontweight="bold", color="#0f172a")
    if cant_top > 0:
        ax_plan.annotate("", xy=(dim_x, y_slab_max), xytext=(dim_x, y_coords[-1]), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text(dim_x + 0.4, (y_coords[-1] + y_slab_max)/2.0, f"{cant_top:.2f}m", ha="left", va="center", fontsize=13, fontweight="bold", color="#0f172a")

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="datalim")
    ax_plan.axis("off")

    ax_legend.set_facecolor("#ffffff")
    ax_legend.set_xlim(0, 100)
    ax_legend.set_ylim(0, 100)
    ax_legend.axis("off")

    c_box = FancyBboxPatch((1, 3), 98, 94, boxstyle="round,pad=1.0,rounding_size=3", facecolor="#fef2f2", edgecolor="#ef4444", lw=2.5)
    ax_legend.add_patch(c_box)
    ax_legend.text(2.5, 75, "COLUMN CAPS (TOP EXTRA REINFORCEMENT) SPECIFICATIONS (ECP 203)", fontsize=18.0, fontweight="bold", color="#991b1b")
    ax_legend.text(2.5, 38, f"• Columns Requiring Extra Top Steel: {active_caps_count} Columns  |  Coverage: Column Strips (شريحة الأعمدة w ≈ min(Lx,Ly)/2)\n"
                          f"• Bar Extension Rule: L_ext = 0.50 Ln + bc (Extends 0.25 Ln each side of internal columns, 0.30 Ln for exterior)\n"
                          f"• Strip Dimensions: Length (L) and Width (W) are indicated for each column cap zone on plan.",
                   fontsize=15.0, fontweight="bold", color="#1e293b", linespacing=1.6)

    fig.suptitle(
        f"COLUMN CAPS (TOP EXTRA REINFORCEMENT) LAYOUT — ts = {ts_cm:.0f} cm\n"
        f"مسقط كابات وحديد إضافي علوي فوق الأعمدة (أبعاد ومساحة الشرائح)",
        fontsize=17.0, fontweight="bold", color="#0f172a", y=0.985
    )
    return fig


# ── DEFLECTION CALCULATION (ECP 203) ──────────────────────────────────────
def calculate_flat_slab_deflections(
    Lx_spans,
    Ly_spans,
    cantilevers,
    ts_cm,
    d_cm,
    Fcu,
    DL_tot,
    LL,
    void_panel_ids=None,
    col_w_cm=30,
    col_d_cm=30,
):
    """
    Computes short-term and long-term (creep & shrinkage) deflections for all bays
    in accordance with ECP 203 Clause 4.3.1 (Branson effective inertia method).
    """
    panels_def = []
    _voids = set(void_panel_ids) if void_panel_ids else set()

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    n_x = len(Lx_spans)
    n_y = len(Ly_spans)

    fcu_mpa = Fcu * 0.0980665
    Ec_t_m2 = 4400.0 * math.sqrt(max(10.0, fcu_mpa)) * 100.0   # t/m2
    fctr_t_m2 = 0.60 * math.sqrt(max(10.0, fcu_mpa)) * 100.0   # t/m2

    ts_m = ts_cm / 100.0
    Ig_m4 = (1.0 * (ts_m ** 3)) / 12.0                         # m4/m
    yt_m = ts_m / 2.0
    Mcr = (fctr_t_m2 * Ig_m4) / yt_m                           # t.m/m

    Ws = DL_tot + LL                                           # Service load (t/m2)
    DL_ratio = min(1.0, max(0.4, DL_tot / max(0.1, Ws)))

    alpha_creep = 2.0
    lambda_long = 1.0 + alpha_creep * DL_ratio                 # Total multiplier for long-term deflection

    bc_m = col_w_cm / 100.0
    tc_m = col_d_cm / 100.0

    for j in range(n_y):
        for i in range(n_x):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                continue

            span_x = Lx_spans[i]
            span_y = Ly_spans[j]
            x_mid = (x_coords[i] + x_coords[i+1]) / 2.0
            y_mid = (y_coords[j] + y_coords[j+1]) / 2.0

            Ln_x = max(1.0, span_x - bc_m)
            Ln_y = max(1.0, span_y - tc_m)
            Ln_critical = max(Ln_x, Ln_y)

            is_edge_x = (i == 0 or i == n_x - 1)
            is_edge_y = (j == 0 or j == n_y - 1)

            if is_edge_x and is_edge_y:
                ptype = "Corner Panel (ركنية)"
                kd = 0.0105
                m_denom = 14.0
            elif is_edge_x or is_edge_y:
                ptype = "Edge Panel (طرفية)"
                kd = 0.0090
                m_denom = 15.0
            else:
                ptype = "Interior Panel (داخلية)"
                kd = 0.0075
                m_denom = 18.0

            Ms_pos = (Ws * (Ln_critical ** 2)) / m_denom       # t.m/m

            Icr = 0.35 * Ig_m4
            if Ms_pos <= Mcr:
                Ie = Ig_m4
                cracked = False
            else:
                cracked = True
                ratio_cr = (Mcr / max(0.01, Ms_pos)) ** 3
                Ie = max(Icr, min(Ig_m4, ratio_cr * Ig_m4 + (1.0 - ratio_cr) * Icr))

            delta_st_m = (kd * Ws * (Ln_critical ** 4)) / max(1.0, Ec_t_m2 * Ie)
            delta_st_mm = delta_st_m * 1000.0
            delta_long_mm = delta_st_mm * lambda_long

            delta_all_mm = (Ln_critical * 1000.0) / 250.0
            ratio = delta_long_mm / max(0.1, delta_all_mm)
            is_safe = ratio <= 1.0

            if not is_safe:
                ts_req_est = ts_cm * ((delta_long_mm / delta_all_mm) ** (1.0 / 3.0))
                ts_req_cm = max(ts_cm + 2.0, math.ceil(ts_req_est / 2.0) * 2.0)
                ts_inc_cm = ts_req_cm - ts_cm
            else:
                ts_req_cm = ts_cm
                ts_inc_cm = 0

            panels_def.append({
                "Panel ID": pid,
                "Bay Label": f"Bay ({i+1}, {j+1})",
                "Location Type": ptype,
                "x_mid": x_mid,
                "y_mid": y_mid,
                "x0": x_coords[i],
                "x1": x_coords[i+1],
                "y0": y_coords[j],
                "y1": y_coords[j+1],
                "span_x": span_x,
                "span_y": span_y,
                "Ln (m)": Ln_critical,
                "Ws (t/m²)": Ws,
                "Mcr (t.m/m)": Mcr,
                "Ms_pos (t.m/m)": Ms_pos,
                "Is_Cracked": cracked,
                "Ie/Ig": Ie / Ig_m4,
                "delta_st (mm)": delta_st_mm,
                "delta_long (mm)": delta_long_mm,
                "delta_all (mm)": delta_all_mm,
                "Ratio": ratio,
                "is_safe": is_safe,
                "ts_req_cm": int(ts_req_cm),
                "ts_inc_cm": int(ts_inc_cm),
                "Status": "✅ Safe (ضمن الحدود)" if is_safe else "🚨 Exceeds Limit (يتجاوز المسموح)",
            })

    return panels_def


# ── DEFLECTION 2D CONTOUR SKETCH ───────────────────────────────────────────
def generate_flat_slab_deflection_contour_sketch(
    Lx_spans,
    Ly_spans,
    cantilevers,
    ts_cm,
    d_cm,
    Fcu,
    DL_tot,
    LL,
    deflection_results,
    col_w_cm=30,
    col_d_cm=30,
    removed_cols=None,
    void_panel_ids=None,
):
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    bubble_radius = max(0.50, min(slab_w, slab_h) * 0.038)
    offset_grid_top = max(2.2, slab_h * 0.11)
    offset_grid_left = max(2.2, slab_w * 0.11)
    dim_offset_bot = max(2.0, slab_h * 0.11)
    dim_offset_right = max(1.8, slab_w * 0.09)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.8
    margin_right = dim_offset_right + 1.5
    margin_top = offset_grid_top + bubble_radius * 2 + 0.8
    margin_bot = dim_offset_bot + 1.5

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.0
    target_plan_w = target_plan_h * ar_plan
    legend_h = 5.2

    fig_w = max(24.0, min(36.0, target_plan_w + 1.8))
    fig_h = max(18.0, min(34.0, target_plan_h + legend_h + 1.0))

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=140)
    fig.patch.set_facecolor("#ffffff")

    plan_ratio = (fig_h - legend_h - 0.8) / fig_h
    legend_ratio = legend_h / fig_h

    gs = fig.add_gridspec(2, 1, height_ratios=[plan_ratio, legend_ratio], hspace=0.06, left=0.03, right=0.95, top=0.94, bottom=0.02)
    ax_plan = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])
    ax_plan.set_facecolor("#ffffff")

    # ── 1. GENERATE 2D DEFLECTION FIELD (Delta Field) ─────────────────────────
    nx_mesh = 240
    ny_mesh = 240
    x_grid = np.linspace(x_slab_min, x_slab_max, nx_mesh)
    y_grid = np.linspace(y_slab_min, y_slab_max, ny_mesh)
    X_m, Y_m = np.meshgrid(x_grid, y_grid)

    Delta_field = np.zeros_like(X_m)
    _voids = set(void_panel_ids) if void_panel_ids else set()

    for p in deflection_results:
        x0, x1 = p["x0"], p["x1"]
        y0, y1 = p["y0"], p["y1"]
        d_val = p["delta_long (mm)"]

        mask = (X_m >= x0) & (X_m <= x1) & (Y_m >= y0) & (Y_m <= y1)
        span_x = x1 - x0
        span_y = y1 - y0
        sin_x = np.sin(np.pi * np.clip((X_m - x0) / max(0.1, span_x), 0.0, 1.0))
        sin_y = np.sin(np.pi * np.clip((Y_m - y0) / max(0.1, span_y), 0.0, 1.0))
        Delta_field += mask * (d_val * sin_x * sin_y)

    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                px0, px1 = x_coords[i], x_coords[i+1]
                py0, py1 = y_coords[j], y_coords[j+1]
                v_mask = (X_m >= px0) & (X_m <= px1) & (Y_m >= py0) & (Y_m <= py1)
                Delta_field[v_mask] = np.nan

    # ── Check if any panel is unsafe ──
    has_unsafe = any(not p["is_safe"] for p in deflection_results)

    delta_all_sample = deflection_results[0].get("delta_all (mm)", 20.0) if deflection_results else 20.0
    delta_max = float(np.nanmax(Delta_field)) if np.any(~np.isnan(Delta_field)) else delta_all_sample
    delta_levels_max = max(delta_all_sample * 1.30, delta_max * 1.05)
    levels = np.linspace(0.0, max(5.0, delta_levels_max), 40)

    if has_unsafe:
        # ── UNSAFE CASE: Draw 2D Filled Deflection Contour Map & Colorbar ──
        cmap_def = "coolwarm"   # Blue (low deflection) -> Yellow/Orange -> Red (high deflection)
        cs = ax_plan.contourf(X_m, Y_m, Delta_field, levels=levels, cmap=cmap_def, extend="max", zorder=1, alpha=0.88)

        # Line Contours
        line_levels = np.linspace(0.0, delta_levels_max, 14)
        cs_lines = ax_plan.contour(X_m, Y_m, Delta_field, levels=line_levels, colors="#334155", linewidths=0.75, alpha=0.45, zorder=2)
        ax_plan.clabel(cs_lines, inline=True, fontsize=10.0, fmt="%.1f", colors="#0f172a")

        # Iso-contour for allowable limit
        if delta_all_sample < delta_levels_max:
            ax_plan.contour(X_m, Y_m, Delta_field, levels=[delta_all_sample], colors="#b91c1c", linewidths=2.6, linestyles="-.", zorder=3)

        # Colorbar
        cbar_ax = fig.add_axes([0.955, 0.32, 0.015, 0.56])
        cbar = fig.colorbar(cs, cax=cbar_ax)
        cbar.set_label("Total Long-Term Deflection Δ (mm) | الترخيم الكلي طويل المدى", fontsize=13.5, weight="bold", labelpad=12)
        cbar.ax.tick_params(labelsize=11.5)
    else:
        # ── SAFE CASE: Clean Plan (No Contours, No Colorbar) ──
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, slab_h, lw=0, facecolor="#f8fafc", zorder=1))

    # Slab boundary
    ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, slab_h, lw=3.2, edgecolor="#0f172a", facecolor="none", zorder=4))

    # Cantilevers
    if cant_left > 0:
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), cant_left, slab_h, lw=1.8, edgecolor="#4f46e5", facecolor="none", linestyle="--", zorder=4))
    if cant_right > 0:
        ax_plan.add_patch(patches.Rectangle((x_coords[-1], y_slab_min), cant_right, slab_h, lw=1.8, edgecolor="#4f46e5", facecolor="none", linestyle="--", zorder=4))
    if cant_bottom > 0:
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, cant_bottom, lw=1.8, edgecolor="#4f46e5", facecolor="none", linestyle="--", zorder=4))
    if cant_top > 0:
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_coords[-1]), slab_w, cant_top, lw=1.8, edgecolor="#4f46e5", facecolor="none", linestyle="--", zorder=4))

    # Voids
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                px0, px1 = x_coords[i], x_coords[i+1]
                py0, py1 = y_coords[j], y_coords[j+1]
                pw, ph = px1 - px0, py1 - py0
                v_rect = patches.Rectangle((px0, py0), pw, ph, facecolor="#f8fafc", edgecolor="#ef4444", lw=2.2, hatch="//", zorder=5)
                ax_plan.add_patch(v_rect)
                ax_plan.text(px0 + pw/2, py0 + ph/2, "OPENING / VOID", ha="center", va="center", fontsize=13, fontweight="bold", color="#b91c1c", zorder=6, bbox=dict(boxstyle="round,pad=0.4", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.5))

    # Grid lines & bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        ax_plan.plot([x, x], [y_slab_min - 0.5, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=5)
        bub = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=7)
        ax_plan.add_patch(bub)
        ax_plan.text(x, y_top_ext, f"Y{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=8)

    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        ax_plan.plot([x_left_ext, x_slab_max + 0.5], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=5)
        bub = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=7)
        ax_plan.add_patch(bub)
        ax_plan.text(x_left_ext, y, f"X{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=8)

    # Columns
    col_w_m = max(col_w_cm / 100.0, slab_w * 0.040)
    col_d_m = max(col_d_cm / 100.0, slab_h * 0.040)
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()
    col_k = 1
    for y in y_coords:
        for x in x_coords:
            if (x, y) in rem_coords:
                continue
            cid = f"C{col_k}"
            ax_plan.add_patch(patches.Rectangle((x - col_w_m / 2.0, y - col_d_m / 2.0), col_w_m, col_d_m, lw=2.2, edgecolor="#0f172a", facecolor="#1e293b", zorder=8))
            ax_plan.text(x, y, cid, color="#facc15", fontsize=13, ha="center", va="center", weight="bold", zorder=9)
            col_k += 1

    # Panel Deflection Callout Tags
    unsafe_count = 0
    safe_count = 0

    all_d_all = [p.get("delta_all (mm)", 20.0) for p in deflection_results]
    min_d_all = min(all_d_all) if all_d_all else 10.0
    max_d_all = max(all_d_all) if all_d_all else 25.0

    for p in deflection_results:
        xm = p["x_mid"]
        ym = p["y_mid"]
        pid = p["Panel ID"]
        lbl = p["Bay Label"]
        d_long = p["delta_long (mm)"]
        d_all = p["delta_all (mm)"]
        is_safe = p["is_safe"]
        ts_req = p["ts_req_cm"]
        ts_inc = p["ts_inc_cm"]

        if is_safe:
            safe_count += 1
            callout_str = (
                f"{pid} ({lbl})\n"
                f"Δact = {d_long:.1f} mm\n"
                f"Δall = {d_all:.1f} mm (Ln/250)\n"
                f"✅ SAFE (Δact ≤ Δall)"
            )
            ax_plan.text(
                xm, ym, callout_str,
                ha="center", va="center", fontsize=10.5, fontweight="bold",
                color="#15803d", zorder=10,
                bbox=dict(boxstyle="round,pad=0.45", facecolor="#ffffff", edgecolor="#16a34a", lw=2.0, alpha=0.98)
            )
        else:
            unsafe_count += 1
            ratio_pct = ((d_long / max(0.01, d_all)) - 1.0) * 100.0
            callout_str = (
                f"🚨 {pid} ({lbl}) — غير آمن (UNSAFE)\n"
                f"Δact = {d_long:.1f} mm > Δall = {d_all:.1f} mm\n"
                f"تجاوز الترخيم المسموح: +{ratio_pct:.1f}%\n"
                f"───────────────────────────────\n"
                f"💡 المعالجة المطلوبة (ECP 203):\n"
                f"• زيادة السُمك: ts ≥ {ts_req:.0f} cm (+{ts_inc:.0f}cm)\n"
                f"• أو إضافة سقوط عمود (Drop Panel)\n"
                f"• أو إضافة تسليح ضغط (As' Compression)"
            )
            ax_plan.text(
                xm, ym, callout_str,
                ha="center", va="center", fontsize=11.0, fontweight="bold",
                color="#7f1d1d", zorder=12,
                bbox=dict(boxstyle="round,pad=0.55", facecolor="#fee2e2", edgecolor="#dc2626", lw=3.0)
            )

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.axis("off")

    # Legend Panel
    ax_legend.set_xlim(0, 100)
    ax_legend.set_ylim(0, 100)
    ax_legend.axis("off")

    if has_unsafe:
        banner_color = "#fef2f2"
        banner_border = "#ef4444"
        title_color = "#991b1b"
        main_legend_title = "🚨 SLAB DEFLECTION 2D CONTOUR & SERVICEABILITY WARNING (ECP 203)"
        legend_text = (
            f"• Total Bays: {len(deflection_results)} Panels  |  ✅ Safe Panels: {safe_count}  |  🚨 Exceeds Limit: {unsafe_count}\n"
            f"• Design Parameters: fcu = {Fcu:.0f} kg/cm²  |  Slab ts = {ts_cm:.0f} cm  |  Service Load Ws = {DL_tot+LL:.2f} t/m² (DL = {DL_tot:.2f}, LL = {LL:.2f})\n"
            f"• معيار الأمان في الترخيم: الحد الأقصى المسموح يحسب لكل باكية بناءً على بحرها الصافي (Δall = Ln / 250).\n"
            f"• الباكيات المحددة بالمربع الأحمر (Δact > Δall): تتطلب زيادة سُمك البلاطة ts أو إضافة سقوط عمود (Drop Panel) أو تسليح ضغط."
        )
    else:
        banner_color = "#f0fdf4"
        banner_border = "#22c55e"
        title_color = "#15803d"
        main_legend_title = "✅ SLAB DEFLECTION VERIFICATION — ALL BAYS ARE SAFE (ECP 203)"
        legend_text = (
            f"• Total Bays: {len(deflection_results)} Panels  |  ✅ All Panels Safe (100% Safe)  |  🚨 Exceeds Limit: 0\n"
            f"• Design Parameters: fcu = {Fcu:.0f} kg/cm²  |  Slab ts = {ts_cm:.0f} cm  |  Service Load Ws = {DL_tot+LL:.2f} t/m² (DL = {DL_tot:.2f}, LL = {LL:.2f})\n"
            f"• معيار الأمان في الترخيم: الحد الأقصى المسموح يحسب لكل باكية بناءً على بحرها الصافي (Δall = Ln / 250).\n"
            f"• النتيجة: جميع باكيات السقف آمنة تماماً ولا تعاني من أي ترخيم حرج ولا تتطلب رسم كونتور تحذيري."
        )

    c_box = FancyBboxPatch((1, 3), 98, 94, boxstyle="round,pad=1.0,rounding_size=3", facecolor=banner_color, edgecolor=banner_border, lw=2.5)
    ax_legend.add_patch(c_box)
    ax_legend.text(2.5, 76, main_legend_title, fontsize=17.0, fontweight="bold", color=title_color)
    ax_legend.text(2.5, 22, legend_text, fontsize=12.5, fontweight="bold", color="#1e293b", linespacing=1.45)

    # ── LARGE BLACK BOX FOR ALLOWABLE DEFLECTION ──
    def_black_box = FancyBboxPatch((64, 8), 34, 84, boxstyle="round,pad=0.8,rounding_size=3", facecolor="#090d16", edgecolor="#334155", lw=3.0)
    ax_legend.add_patch(def_black_box)
    ax_legend.text(81.0, 78, "🛡️ أقصى ترخيم مسموح به (ECP 203)", fontsize=12.0, fontweight="bold", color="#94a3b8", ha="center")
    ax_legend.text(81.0, 54, "Δall = Ln / 250", fontsize=20.0, fontweight="black", color="#facc15", ha="center")
    if has_unsafe:
        ax_legend.text(81.0, 34, f"نطاق الحدود: {min_d_all:.1f} ~ {max_d_all:.1f} mm", fontsize=12.5, fontweight="bold", color="#f87171", ha="center")
        ax_legend.text(81.0, 16, "🚨 توجد باكيات تتجاوز الحد المسموح", fontsize=10.5, color="#ef4444", fontweight="bold", ha="center")
    else:
        ax_legend.text(81.0, 34, f"نطاق الحدود: {min_d_all:.1f} ~ {max_d_all:.1f} mm", fontsize=12.5, fontweight="bold", color="#4ade80", ha="center")
        ax_legend.text(81.0, 16, "✅ جميع الباكيات محققة لحدود الأمان", fontsize=10.5, color="#22c55e", fontweight="bold", ha="center")

    if has_unsafe:
        fig.suptitle(
            f"SLAB LONG-TERM DEFLECTION 2D CONTOUR MAP (Δact) — ts = {ts_cm:.0f} cm\n"
            f"مخطط كونتور ترخيم البلاطة اللاكمرية — الباكيات المحددة بالمربع الأحمر غير آمنة وتتجاوز الحد المسموح (Δact > Δall)",
            fontsize=16.5, fontweight="bold", color="#991b1b", y=0.985
        )
    else:
        fig.suptitle(
            f"SLAB DEFLECTION VERIFICATION (ALL BAYS SAFE) — ts = {ts_cm:.0f} cm\n"
            f"فحص سهم الانحناء — جميع الباكيات آمنة ومحققة لحدود الكود المصري ECP 203 (Δact ≤ Δall)",
            fontsize=16.5, fontweight="bold", color="#15803d", y=0.985
        )
    return fig


# ── PUNCHING SHEAR VERIFICATION 2D CONTOUR SKETCH ──────────────────────────
def generate_flat_slab_punching_shear_sketch(
    Lx_spans,
    Ly_spans,
    cantilevers,
    ts_cm,
    d_cm,
    Fcu,
    Wu,
    punching_results,
    col_w_cm=30,
    col_d_cm=30,
    removed_cols=None,
    void_panel_ids=None,
):
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    bubble_radius = max(0.50, min(slab_w, slab_h) * 0.038)
    offset_grid_top = max(2.2, slab_h * 0.11)
    offset_grid_left = max(2.2, slab_w * 0.11)
    dim_offset_bot = max(2.0, slab_h * 0.11)
    dim_offset_right = max(1.8, slab_w * 0.09)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.8
    margin_right = dim_offset_right + 1.5
    margin_top = offset_grid_top + bubble_radius * 2 + 0.8
    margin_bot = dim_offset_bot + 1.5

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.0
    target_plan_w = target_plan_h * ar_plan
    legend_h = 5.2

    fig_w = max(24.0, min(36.0, target_plan_w + 1.8))
    fig_h = max(18.0, min(34.0, target_plan_h + legend_h + 1.0))

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=140)
    fig.patch.set_facecolor("#ffffff")

    plan_ratio = (fig_h - legend_h - 0.8) / fig_h
    legend_ratio = legend_h / fig_h

    gs = fig.add_gridspec(2, 1, height_ratios=[plan_ratio, legend_ratio], hspace=0.06, left=0.03, right=0.95, top=0.94, bottom=0.02)
    ax_plan = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])
    ax_plan.set_facecolor("#ffffff")

    # ── 1. GENERATE 2D PUNCHING SHEAR STRESS FIELD (Qup Field) ───────────────
    nx_mesh = 240
    ny_mesh = 240
    x_grid = np.linspace(x_slab_min, x_slab_max, nx_mesh)
    y_grid = np.linspace(y_slab_min, y_slab_max, ny_mesh)
    X_m, Y_m = np.meshgrid(x_grid, y_grid)

    Qup_field = np.zeros_like(X_m)
    avg_span = (np.mean(Lx_spans) + np.mean(Ly_spans)) / 2.0 if len(Lx_spans) > 0 else 5.0
    sigma_punch = max(0.55, avg_span * 0.14)

    for p in punching_results:
        col_x = p.get("x", 0.0)
        col_y = p.get("y", 0.0)
        qup_val = p.get("qup (kg/cm²)", 0.0)
        dist_sq = (X_m - col_x) ** 2 + (Y_m - col_y) ** 2
        Qup_field += qup_val * np.exp(-dist_sq / (2.0 * (sigma_punch ** 2)))

    # Mask voids
    _voids = set(void_panel_ids) if void_panel_ids else set()
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                px0, px1 = x_coords[i], x_coords[i+1]
                py0, py1 = y_coords[j], y_coords[j+1]
                v_mask = (X_m >= px0) & (X_m <= px1) & (Y_m >= py0) & (Y_m <= py1)
                Qup_field[v_mask] = np.nan

    qcup_sample = punching_results[0].get("qcup (kg/cm²)", 10.5) if punching_results else 10.5
    qup_max = float(np.nanmax(Qup_field)) if np.any(~np.isnan(Qup_field)) else qcup_sample
    qup_levels_max = max(qcup_sample * 1.35, qup_max * 1.05)
    levels = np.linspace(0.0, qup_levels_max, 40)

    # 2. Filled 2D Contour Map
    cmap_punch = "YlOrRd"  # Yellow -> Orange -> Red (high shear stress concentration)
    cs = ax_plan.contourf(X_m, Y_m, Qup_field, levels=levels, cmap=cmap_punch, extend="max", zorder=1, alpha=0.88)

    # Line Contours
    line_levels = np.linspace(0.0, qup_levels_max, 14)
    cs_lines = ax_plan.contour(X_m, Y_m, Qup_field, levels=line_levels, colors="#334155", linewidths=0.75, alpha=0.45, zorder=2)
    ax_plan.clabel(cs_lines, inline=True, fontsize=10.0, fmt="%.1f", colors="#0f172a")

    # Iso-contour for Qcup threshold limit
    if qcup_sample < qup_levels_max:
        ax_plan.contour(X_m, Y_m, Qup_field, levels=[qcup_sample], colors="#b91c1c", linewidths=2.6, linestyles="-.", zorder=3)

    # Colorbar
    cbar_ax = fig.add_axes([0.955, 0.32, 0.015, 0.56])
    cbar = fig.colorbar(cs, cax=cbar_ax)
    cbar.set_label("Punching Shear Stress Qup (kg/cm²) | إجهاد القص الثاقب", fontsize=13.5, weight="bold", labelpad=12)
    cbar.ax.tick_params(labelsize=11.5)

    # Slab boundary
    ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, slab_h, lw=3.2, edgecolor="#0f172a", facecolor="none", zorder=4))

    # Cantilever shading
    if cant_left > 0:
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), cant_left, slab_h, lw=1.8, edgecolor="#4f46e5", facecolor="none", linestyle="--", zorder=4))
    if cant_right > 0:
        ax_plan.add_patch(patches.Rectangle((x_coords[-1], y_slab_min), cant_right, slab_h, lw=1.8, edgecolor="#4f46e5", facecolor="none", linestyle="--", zorder=4))
    if cant_bottom > 0:
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, cant_bottom, lw=1.8, edgecolor="#4f46e5", facecolor="none", linestyle="--", zorder=4))
    if cant_top > 0:
        ax_plan.add_patch(patches.Rectangle((x_slab_min, y_coords[-1]), slab_w, cant_top, lw=1.8, edgecolor="#4f46e5", facecolor="none", linestyle="--", zorder=4))

    # Voids
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                px0, px1 = x_coords[i], x_coords[i+1]
                py0, py1 = y_coords[j], y_coords[j+1]
                pw, ph = px1 - px0, py1 - py0
                v_rect = patches.Rectangle((px0, py0), pw, ph, facecolor="#f8fafc", edgecolor="#ef4444", lw=2.2, hatch="//", zorder=5)
                ax_plan.add_patch(v_rect)
                ax_plan.text(px0 + pw/2, py0 + ph/2, "OPENING / VOID", ha="center", va="center", fontsize=13, fontweight="bold", color="#b91c1c", zorder=6, bbox=dict(boxstyle="round,pad=0.4", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.5))

    # Grid lines & bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        ax_plan.plot([x, x], [y_slab_min - 0.5, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=5)
        bub = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=7)
        ax_plan.add_patch(bub)
        ax_plan.text(x, y_top_ext, f"Y{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=8)

    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        ax_plan.plot([x_left_ext, x_slab_max + 0.5], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=5)
        bub = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=7)
        ax_plan.add_patch(bub)
        ax_plan.text(x_left_ext, y, f"X{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=8)

    # Dimensions
    for i in range(len(Lx_spans)):
        x0, x1 = x_coords[i], x_coords[i+1]
        y_d = y_slab_min - dim_offset_bot
        ax_plan.annotate("", xy=(x0, y_d), xytext=(x1, y_d), arrowprops=dict(arrowstyle="<->", color="#1e293b", lw=2.2, shrinkA=0, shrinkB=0), zorder=6)
        ax_plan.text((x0 + x1)/2.0, y_d + 0.25, f"{Lx_spans[i]:.2f} m", color="#1e293b", fontsize=14, weight="bold", ha="center", va="bottom", zorder=7)

    for j in range(len(Ly_spans)):
        y0, y1 = y_coords[j], y_coords[j+1]
        x_d = x_slab_max + dim_offset_right
        ax_plan.annotate("", xy=(x_d, y0), xytext=(x_d, y1), arrowprops=dict(arrowstyle="<->", color="#1e293b", lw=2.2, shrinkA=0, shrinkB=0), zorder=6)
        ax_plan.text(x_d + 0.25, (y0 + y1)/2.0, f"{Ly_spans[j]:.2f} m", color="#1e293b", fontsize=14, weight="bold", ha="left", va="center", rotation=90, zorder=7)

    d_m = d_cm / 100.0
    col_w_m = max(col_w_cm / 100.0, slab_w * 0.040)
    col_d_m = max(col_d_cm / 100.0, slab_h * 0.040)

    unsafe_count = 0
    safe_count = 0

    for p in punching_results:
        cx = p.get("x", 0.0)
        cy = p.get("y", 0.0)
        cid = p.get("Column ID", "C")
        qup = p.get("qup (kg/cm²)", 0.0)
        qcup = p.get("qcup (kg/cm²)", qcup_sample)
        ratio = p.get("Ratio", 0.0)
        is_safe = p.get("is_safe", True)
        ctype = p.get("Location Type", "Interior")
        Pu_val = p.get("Pu (ton)", 40.0)
        bc_val = p.get("bc", col_w_cm)
        tc_val = p.get("tc", col_d_cm)

        crit_w = col_w_m + (d_m if ctype != "Corner" else d_m / 2.0)
        crit_h = col_d_m + (d_m if ctype != "Corner" else d_m / 2.0)
        crit_x = cx - crit_w / 2.0
        crit_y = cy - crit_h / 2.0

        if is_safe:
            safe_count += 1
            crit_edge = "#16a34a"
            col_face = "#1e293b"
            col_edge = "#0f172a"
            col_lw = 2.2
            tag_face = "#ffffff"
            tag_edge = "#16a34a"
            tag_txt_color = "#15803d"
        else:
            unsafe_count += 1
            crit_edge = "#dc2626"
            col_face = "#fee2e2"
            col_edge = "#b91c1c"
            col_lw = 3.6
            tag_face = "#fef2f2"
            tag_edge = "#ef4444"
            tag_txt_color = "#991b1b"

        # Draw critical shear perimeter d/2
        ax_plan.add_patch(patches.Rectangle(
            (crit_x, crit_y), crit_w, crit_h,
            lw=2.2, edgecolor=crit_edge, facecolor="none", linestyle="--", zorder=7
        ))

        # Draw column box
        ax_plan.add_patch(patches.Rectangle(
            (cx - col_w_m / 2.0, cy - col_d_m / 2.0), col_w_m, col_d_m,
            lw=col_lw, edgecolor=col_edge, facecolor=col_face, zorder=8
        ))

        # Column text inside box
        if is_safe:
            ax_plan.text(cx, cy + col_d_m * 0.15, cid, color="#facc15", fontsize=14, ha="center", va="center", weight="bold", zorder=9)
            ax_plan.text(cx, cy - col_d_m * 0.22, "SAFE", color="#4ade80", fontsize=10.5, ha="center", va="center", weight="bold", zorder=9)
        else:
            ax_plan.text(cx, cy + col_d_m * 0.16, cid, color="#7f1d1d", fontsize=15, ha="center", va="center", weight="bold", zorder=9)
            ax_plan.text(cx, cy - col_d_m * 0.22, "UNSAFE", color="#b91c1c", fontsize=11, ha="center", va="center", weight="bold", zorder=9)

        # Callout Text near the column showing Qup clearly
        offset_y = col_d_m / 2.0 + 0.55
        tag_x = cx
        tag_y = cy + offset_y

        if not is_safe:
            # Calculate design remediation according to ECP 203
            Pu_kg = Pu_val * 1000.0
            beta_val = 1.50 if ctype == "Corner" else (1.30 if ctype == "Edge" else 1.15)
            b0_const = (bc_val + tc_val) if ctype == "Corner" else (2.0 * bc_val + tc_val if ctype == "Edge" else 2.0 * bc_val + 2.0 * tc_val)
            b0_coeff = 1.0 if ctype == "Corner" else (2.0 if ctype == "Edge" else 4.0)
            target_area = (beta_val * Pu_kg) / max(0.1, qcup)
            A_q = b0_coeff
            B_q = b0_const
            C_q = -target_area
            disc = B_q**2 - 4 * A_q * C_q
            d_req = (-B_q + math.sqrt(disc)) / (2 * A_q) if disc > 0 else (d_cm * math.sqrt(qup / max(0.1, qcup)))
            ts_req = max(ts_cm + 2.0, math.ceil((d_req + 3.0) / 2.0) * 2.0)
            ts_inc = ts_req - ts_cm

            q_ss = max(0.0, qup - 0.5 * qcup)
            bo_curr = b0_const + b0_coeff * d_cm
            V_su_kg = q_ss * bo_curr * d_cm
            s_spacing = max(8.0, min(15.0, round(d_cm / 2.0)))
            Ast_req = (V_su_kg * s_spacing) / (3600.0 * max(1.0, d_cm))
            n_legs = math.ceil(Ast_req / 0.785)
            n_studs = max(8, int(math.ceil(n_legs / 4.0) * 4))

            callout_str = (
                f"🚨 {cid} — UNSAFE PUNCHING\n"
                f"Qup = {qup:.2f} kg/cm² (> Qcup)\n"
                f"────────────────────────\n"
                f"💡 المعالجة المطلوبة (ECP 203):\n"
                f"• كانات قص: + {n_studs} Φ10 / عمود\n"
                f"• أو زيادة السُمك: ts ≥ {ts_req:.0f} cm (+{ts_inc:.0f}cm)"
            )
            ax_plan.text(
                tag_x, tag_y, callout_str,
                ha="center", va="bottom", fontsize=11.5, fontweight="bold",
                color=tag_txt_color, zorder=11,
                bbox=dict(boxstyle="round,pad=0.45", facecolor=tag_face, edgecolor=tag_edge, lw=2.4)
            )
        else:
            callout_str = f"Qup = {qup:.2f} kg/cm²"
            ax_plan.text(
                tag_x, tag_y, callout_str,
                ha="center", va="bottom", fontsize=10.5, fontweight="bold",
                color=tag_txt_color, zorder=10,
                bbox=dict(boxstyle="round,pad=0.32", facecolor=tag_face, edgecolor=tag_edge, lw=1.6, alpha=0.96)
            )

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.axis("off")

    # Legend Panel
    ax_legend.set_xlim(0, 100)
    ax_legend.set_ylim(0, 100)
    ax_legend.axis("off")

    banner_color = "#fef2f2" if unsafe_count > 0 else "#f8fafc"
    banner_border = "#ef4444" if unsafe_count > 0 else "#cbd5e1"
    title_color = "#991b1b" if unsafe_count > 0 else "#1e3a8a"

    c_box = FancyBboxPatch((1, 3), 98, 94, boxstyle="round,pad=1.0,rounding_size=3", facecolor=banner_color, edgecolor=banner_border, lw=2.5)
    ax_legend.add_patch(c_box)
    ax_legend.text(2.5, 76, f"PUNCHING SHEAR 2D CONTOUR & STRESS VERIFICATION (ECP 203)", fontsize=17.5, fontweight="bold", color=title_color)

    legend_text = (
        f"• Total Columns: {len(punching_results)} Cols  |  ✅ Safe Columns: {safe_count}  |  🚨 Unsafe Columns: {unsafe_count}\n"
        f"• Design Parameters: fcu = {Fcu:.0f} kg/cm²  |  Slab ts = {ts_cm:.0f} cm  |  Effective Depth d = {d_cm:.1f} cm  |  Wu = {Wu:.2f} t/m²\n"
        f"• خريطة الكونتور توضح تركيز وتدرج إجهادات القص الثاقب Qup حول الأعمدة (تدرج من الأصفر إلى الأحمر الداكن).\n"
        f"• الأعمدة الحمراء (Qup > Qcup): غير آمنة وموضح أعلاها كانات القص المطلوبة (Shear Studs) أو سُمك الخرسانة البديل."
    )
    ax_legend.text(2.5, 22, legend_text, fontsize=12.5, fontweight="bold", color="#1e293b", linespacing=1.45)

    # ── LARGE BLACK BOX FOR QCUP (مربع كبير باللون الأسود مرة واحدة فقط) ───────
    qcup_black_box = FancyBboxPatch((64, 8), 34, 84, boxstyle="round,pad=0.8,rounding_size=3", facecolor="#090d16", edgecolor="#334155", lw=3.0)
    ax_legend.add_patch(qcup_black_box)
    ax_legend.text(81.0, 78, "🛡️ أقصى إجهاد خرسانة مسموح (ECP 203)", fontsize=12.0, fontweight="bold", color="#94a3b8", ha="center")
    ax_legend.text(81.0, 50, f"Qcup = {qcup_sample:.2f}", fontsize=22.0, fontweight="black", color="#facc15", ha="center")
    ax_legend.text(81.0, 24, f"kg/cm² ({qcup_sample*0.09807:.2f} MPa)", fontsize=13.0, fontweight="bold", color="#38bdf8", ha="center")

    fig.suptitle(
        f"PUNCHING SHEAR 2D CONTOUR MAP (Qup) — ts = {ts_cm:.0f} cm  |  ALLOWABLE LIMIT: Qcup = {qcup_sample:.2f} kg/cm²\n"
        f"مخطط كونتور إجهادات القص الثاقب Qup للأعمدة — أقصى إجهاد خرسانة مسموح به للتصميم Qcup = {qcup_sample:.2f} kg/cm²",
        fontsize=16.5, fontweight="bold", color="#0f172a", y=0.985
    )
    return fig


# ── 2. BOTTOM EXTRA & SHAWKA (WITH BASE MESHES BOX) ─────────────────────────
def generate_flat_slab_bottom_extra_shawka_sketch(
    Lx_spans, Ly_spans, cantilevers, ts_cm,
    btm_extra_spans, cant_rft_list,
    n_mesh_btm=6, bottom_mesh_dia=12,
    n_mesh_top=5, top_mesh_dia=10,
    col_w_cm=30, col_d_cm=30,
    removed_cols=None, void_panel_ids=None,
    direction="X",
):
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    bubble_radius = max(0.50, min(slab_w, slab_h) * 0.038)
    offset_grid_top = max(2.2, slab_h * 0.11)
    offset_grid_left = max(2.2, slab_w * 0.11)
    dim_offset_bot = max(2.0, slab_h * 0.11)
    dim_offset_right = max(1.8, slab_w * 0.09)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.8
    margin_right = dim_offset_right + 1.5
    margin_top = offset_grid_top + bubble_radius * 2 + 0.8
    margin_bot = dim_offset_bot + 1.5

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.0
    target_plan_w = target_plan_h * ar_plan
    legend_h = 5.2

    fig_w = max(22.0, min(34.0, target_plan_w + 1.6))
    fig_h = max(18.0, min(32.0, target_plan_h + legend_h + 1.0))

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=140)
    fig.patch.set_facecolor("#ffffff")

    plan_ratio = (fig_h - legend_h - 0.8) / fig_h
    legend_ratio = legend_h / fig_h

    gs = fig.add_gridspec(2, 1, height_ratios=[plan_ratio, legend_ratio], hspace=0.06, left=0.03, right=0.97, top=0.94, bottom=0.02)
    ax_plan = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])
    ax_plan.set_facecolor("#f8fafc")

    # Slab boundary
    ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, slab_h, lw=3.2, edgecolor="#0f172a", facecolor="#ffffff", zorder=1))

    # Voids
    _voids = set(void_panel_ids) if void_panel_ids else set()
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                px0, px1 = x_coords[i], x_coords[i+1]
                py0, py1 = y_coords[j], y_coords[j+1]
                pw, ph = px1 - px0, py1 - py0
                v_rect = patches.Rectangle((px0, py0), pw, ph, facecolor="#f1f5f9", edgecolor="#ef4444", lw=2.2, hatch="//", zorder=2)
                ax_plan.add_patch(v_rect)
                ax_plan.text(px0 + pw/2, py0 + ph/2, "OPENING / VOID", ha="center", va="center", fontsize=13, fontweight="bold", color="#b91c1c", zorder=4, bbox=dict(boxstyle="round,pad=0.4", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.5))

    # Grids & Bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        ax_plan.plot([x, x], [y_slab_min - 0.5, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=3)
        bub = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x, y_top_ext, f"Y{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        ax_plan.plot([x_left_ext, x_slab_max + 0.5], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=3)
        bub = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x_left_ext, y, f"X{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    # Columns
    col_w_m   = max(col_w_cm / 100.0, slab_w * 0.042)
    col_d_m   = max(col_d_cm / 100.0, slab_h * 0.042)
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()
    col_idx = 1
    for j_idx, y in enumerate(y_coords):
        for i_idx, x in enumerate(x_coords):
            if (x, y) in rem_coords:
                continue
            cid = f"C{col_idx}"
            ax_plan.add_patch(patches.Rectangle((x - col_w_m / 2.0, y - col_d_m / 2.0), col_w_m, col_d_m, lw=2.2, edgecolor="#0f172a", facecolor="#1e293b", zorder=8))
            ax_plan.text(x, y, cid, color="#facc15", fontsize=13, ha="center", va="center", weight="bold", zorder=9)
            col_idx += 1

    # Filter items by direction
    dir_req = (direction or "X").upper()
    filtered_bays = [
        b for b in (btm_extra_spans or [])
        if isinstance(b, dict) and b.get("n_extra", 0) > 0 and b.get("dir", "X").upper() == dir_req
    ]

    has_extra = len(filtered_bays) > 0

    if has_extra:
        for b_info in filtered_bays:
            pid = b_info.get("panel_id", "")
            if pid in _voids:
                continue

            L_ext = b_info.get("L_extra", 4.5)
            W_bay = b_info.get("W_bay", b_info.get("strip_w", 4.5))
            n_ext = b_info.get("n_extra", 6)
            dia_ext = b_info.get("dia_extra", 12)
            cx = b_info.get("cx", b_info.get("mid_x", 0.0))
            cy = b_info.get("cy", b_info.get("mid_y", 0.0))

            line_c = "#d97706"
            edge_c = "#d97706"
            face_c = "#fef3c7"

            if dir_req == "X":
                area_w = L_ext
                area_h = W_bay * 0.88
                area_rect = patches.Rectangle(
                    (cx - area_w/2.0, cy - area_h/2.0), area_w, area_h,
                    lw=2.2, edgecolor=edge_c, facecolor=face_c, alpha=0.60, linestyle="--", zorder=3
                )
                ax_plan.add_patch(area_rect)

                y_bar = cy + 0.35
                ax_plan.plot([cx - L_ext/2.0, cx + L_ext/2.0], [y_bar, y_bar], color=line_c, lw=4.5, solid_capstyle="round", zorder=6)
                ax_plan.plot([cx - L_ext/2.0, cx - L_ext/2.0], [y_bar - 0.25, y_bar + 0.25], color=line_c, lw=3.0, zorder=6)
                ax_plan.plot([cx + L_ext/2.0, cx + L_ext/2.0], [y_bar - 0.25, y_bar + 0.25], color=line_c, lw=3.0, zorder=6)

                ax_plan.text(
                    cx, cy - 0.45,
                    f"★ Bottom Extra (X-Dir / اتجاه X): {n_ext}Φ{dia_ext}\n"
                    f"Bay Dim: {area_w:.2f}m (L) × {W_bay:.2f}m (W)",
                    ha="center", va="center", fontsize=12.5, fontweight="bold", color="#b45309", zorder=8,
                    rotation=0,
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="#ffffff", edgecolor=edge_c, lw=1.8)
                )
            else:
                area_w = W_bay * 0.88
                area_h = L_ext
                area_rect = patches.Rectangle(
                    (cx - area_w/2.0, cy - area_h/2.0), area_w, area_h,
                    lw=2.2, edgecolor=edge_c, facecolor=face_c, alpha=0.60, linestyle="--", zorder=3
                )
                ax_plan.add_patch(area_rect)

                x_bar = cx + 0.35
                ax_plan.plot([x_bar, x_bar], [cy - L_ext/2.0, cy + L_ext/2.0], color=line_c, lw=4.5, solid_capstyle="round", zorder=6)
                ax_plan.plot([x_bar - 0.25, x_bar + 0.25], [cy - L_ext/2.0, cy - L_ext/2.0], color=line_c, lw=3.0, zorder=6)
                ax_plan.plot([x_bar - 0.25, x_bar + 0.25], [cy + L_ext/2.0, cy + L_ext/2.0], color=line_c, lw=3.0, zorder=6)

                ax_plan.text(
                    cx - 0.45, cy,
                    f"★ Bottom Extra (Y-Dir / اتجاه Y): {n_ext}Φ{dia_ext}\n"
                    f"Bay Dim: {W_bay:.2f}m (W) × {area_h:.2f}m (L)",
                    ha="center", va="center", fontsize=12.5, fontweight="bold", color="#b45309", zorder=8,
                    rotation=90,
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="#ffffff", edgecolor=edge_c, lw=1.8)
                )
    else:
        # Prominent banner when no extra bottom rebar needed in this direction
        mid_x_slab = (x_slab_min + x_slab_max) / 2.0
        mid_y_slab = (y_slab_min + y_slab_max) / 2.0
        banner_w = min(slab_w * 0.78, 14.0)
        banner_h = max(1.8, slab_h * 0.12)

        banner_box = FancyBboxPatch(
            (mid_x_slab - banner_w/2.0, mid_y_slab - banner_h/2.0), banner_w, banner_h,
            boxstyle="round,pad=0.5,rounding_size=0.6",
            facecolor="#f0fdf4", edgecolor="#16a34a", lw=2.6, zorder=10
        )
        ax_plan.add_patch(banner_box)

        dir_en = "X-DIRECTION" if dir_req == "X" else "Y-DIRECTION"
        ax_plan.text(
            mid_x_slab, mid_y_slab,
            f"[OK] NO BOTTOM EXTRA REQUIRED IN {dir_en} (كافية تماماً)",
            ha="center", va="center", fontsize=15.0, fontweight="bold", color="#15803d", zorder=11
        )

    # 2. Cantilever Shawka (filtered for relevant direction)
    for cr in (cant_rft_list or []):
        side = cr.get("side", "")
        L_c = cr.get("length", 0.0)
        tot_L = cr.get("total_bar_length", 3.0)
        callout = cr.get("rft_callout", "6Φ12/m'")

        if dir_req == "X":
            if side == "left" and cant_left > 0:
                cy_mid = (y_slab_min + y_slab_max) / 2.0
                cx_tip = x_slab_min
                cx_inner = x_coords[0] + 1.5 * L_c
                ax_plan.plot([cx_tip, cx_inner], [cy_mid, cy_mid], color="#9333ea", lw=4.2, zorder=6)
                ax_plan.plot([cx_tip, cx_tip + 0.5 * L_c], [cy_mid - 0.35, cy_mid - 0.35], color="#9333ea", lw=3.5, zorder=6)
                ax_plan.plot([cx_tip, cx_tip], [cy_mid - 0.35, cy_mid], color="#9333ea", lw=3.5, zorder=6)
                ax_plan.text(
                    cx_tip + L_c/2.0, cy_mid + 0.55, f"★ Shawka: {callout}\n(Total Cut L = {tot_L:.2f} m)",
                    ha="center", va="bottom", fontsize=13.0, fontweight="bold", color="#7e22ce", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="#faf5ff", edgecolor="#a855f7", lw=1.6)
                )
            elif side == "right" and cant_right > 0:
                cy_mid = (y_slab_min + y_slab_max) / 2.0
                cx_tip = x_slab_max
                cx_inner = x_coords[-1] - 1.5 * L_c
                ax_plan.plot([cx_tip, cx_inner], [cy_mid, cy_mid], color="#9333ea", lw=4.2, zorder=6)
                ax_plan.plot([cx_tip, cx_tip - 0.5 * L_c], [cy_mid - 0.35, cy_mid - 0.35], color="#9333ea", lw=3.5, zorder=6)
                ax_plan.plot([cx_tip, cx_tip], [cy_mid - 0.35, cy_mid], color="#9333ea", lw=3.5, zorder=6)
                ax_plan.text(
                    cx_tip - L_c/2.0, cy_mid + 0.55, f"★ Shawka: {callout}\n(Total Cut L = {tot_L:.2f} m)",
                    ha="center", va="bottom", fontsize=13.0, fontweight="bold", color="#7e22ce", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="#faf5ff", edgecolor="#a855f7", lw=1.6)
                )
        else: # Y
            if side == "top" and cant_top > 0:
                cx_mid = (x_slab_min + x_slab_max) / 2.0
                cy_tip = y_slab_max
                cy_inner = y_coords[-1] - 1.5 * L_c
                ax_plan.plot([cx_mid, cx_mid], [cy_tip, cy_inner], color="#9333ea", lw=4.2, zorder=6)
                ax_plan.plot([cx_mid + 0.35, cx_mid + 0.35], [cy_tip, cy_tip - 0.5 * L_c], color="#9333ea", lw=3.5, zorder=6)
                ax_plan.plot([cx_mid, cx_mid + 0.35], [cy_tip, cy_tip], color="#9333ea", lw=3.5, zorder=6)
                ax_plan.text(
                    cx_mid + 0.65, cy_tip - L_c/2.0, f"★ Shawka: {callout}\n(Total Cut L = {tot_L:.2f} m)",
                    ha="left", va="center", fontsize=13.0, fontweight="bold", color="#7e22ce", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="#faf5ff", edgecolor="#a855f7", lw=1.6)
                )
            elif side == "bottom" and cant_bottom > 0:
                cx_mid = (x_slab_min + x_slab_max) / 2.0
                cy_tip = y_slab_min
                cy_inner = y_coords[0] + 1.5 * L_c
                ax_plan.plot([cx_mid, cx_mid], [cy_tip, cy_inner], color="#9333ea", lw=4.2, zorder=6)
                ax_plan.plot([cx_mid + 0.35, cx_mid + 0.35], [cy_tip, cy_tip + 0.5 * L_c], color="#9333ea", lw=3.5, zorder=6)
                ax_plan.plot([cx_mid, cx_mid + 0.35], [cy_tip, cy_tip], color="#9333ea", lw=3.5, zorder=6)
                ax_plan.text(
                    cx_mid + 0.65, cy_tip + L_c/2.0, f"★ Shawka: {callout}\n(Total Cut L = {tot_L:.2f} m)",
                    ha="left", va="center", fontsize=13.0, fontweight="bold", color="#7e22ce", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="#faf5ff", edgecolor="#a855f7", lw=1.6)
                )

    # Dimensions
    dim_y = y_slab_min - dim_offset_bot
    if cant_left > 0:
        ax_plan.annotate("", xy=(x_coords[0], dim_y), xytext=(x_slab_min, dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text((x_slab_min + x_coords[0])/2.0, dim_y - 0.4, f"{cant_left:.2f}m", ha="center", va="top", fontsize=13, fontweight="bold", color="#0f172a")
    for i, lx in enumerate(Lx_spans):
        x0, x1 = x_coords[i], x_coords[i+1]
        ax_plan.annotate("", xy=(x1, dim_y), xytext=(x0, dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text((x0 + x1)/2.0, dim_y - 0.4, f"{lx:.2f}m", ha="center", va="top", fontsize=13, fontweight="bold", color="#0f172a")
    if cant_right > 0:
        ax_plan.annotate("", xy=(x_slab_max, dim_y), xytext=(x_coords[-1], dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text((x_coords[-1] + x_slab_max)/2.0, dim_y - 0.4, f"{cant_right:.2f}m", ha="center", va="top", fontsize=13, fontweight="bold", color="#0f172a")

    dim_x = x_slab_max + dim_offset_right
    if cant_bottom > 0:
        ax_plan.annotate("", xy=(dim_x, y_coords[0]), xytext=(dim_x, y_slab_min), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text(dim_x + 0.4, (y_slab_min + y_coords[0])/2.0, f"{cant_bottom:.2f}m", ha="left", va="center", fontsize=13, fontweight="bold", color="#0f172a")
    for j, ly in enumerate(Ly_spans):
        y0, y1 = y_coords[j], y_coords[j+1]
        ax_plan.annotate("", xy=(dim_x, y1), xytext=(dim_x, y0), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text(dim_x + 0.4, (y0 + y1)/2.0, f"{ly:.2f}m", ha="left", va="center", fontsize=13, fontweight="bold", color="#0f172a")
    if cant_top > 0:
        ax_plan.annotate("", xy=(dim_x, y_slab_max), xytext=(dim_x, y_coords[-1]), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text(dim_x + 0.4, (y_coords[-1] + y_slab_max)/2.0, f"{cant_top:.2f}m", ha="left", va="center", fontsize=13, fontweight="bold", color="#0f172a")

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="datalim")
    ax_plan.axis("off")

    # ── 🌟 DUAL HIGH-CONTRAST LEGEND STRIP WITH BIG FONT ─────────────────────
    ax_legend.set_facecolor("#ffffff")
    ax_legend.set_xlim(0, 100)
    ax_legend.set_ylim(0, 100)
    ax_legend.axis("off")

    # Card 1: Base Meshes Card (Left, 48% width)
    box_mesh = FancyBboxPatch((1, 3), 47.5, 94, boxstyle="round,pad=1.0,rounding_size=3", facecolor="#eff6ff", edgecolor="#2563eb", lw=2.5)
    ax_legend.add_patch(box_mesh)
    ax_legend.text(2.5, 75, "[1] BASE MESHES (شبكات التسليح الأساسية)", fontsize=16.5, fontweight="bold", color="#1e3a8a")
    txt_base = (
        f"• Bottom Mesh (الرقة السفلية): M11(X) & M22(Y) = {n_mesh_btm} Φ {bottom_mesh_dia} mm / m'\n"
        f"• Top Base Mesh (الرقة العلوية): T1(X) & T2(Y) = {n_mesh_top} Φ {top_mesh_dia} mm / m'\n"
        f"• Slab Thickness: ts = {ts_cm:.0f} cm  |  Cover = 25 mm (Spacers @ 1.0m)"
    )
    ax_legend.text(2.5, 38, txt_base, fontsize=14.0, fontweight="bold", color="#0f172a", linespacing=1.6)

    # Card 2: Extra Steel & Shawka Card (Right, 48% width)
    box_extra = FancyBboxPatch((50.5, 3), 48.5, 94, boxstyle="round,pad=1.0,rounding_size=3", facecolor="#fffbeb" if has_extra else "#f0fdf4", edgecolor="#f59e0b" if has_extra else "#16a34a", lw=2.5)
    ax_legend.add_patch(box_extra)
    dir_title = "X-DIR (اتجاه X)" if dir_req == "X" else "Y-DIR (اتجاه Y)"
    ax_legend.text(52.0, 75, f"[2] BOTTOM EXTRA & SHAWKA — {dir_title}", fontsize=16.5, fontweight="bold", color="#b45309" if has_extra else "#15803d")

    if dir_req == "X":
        txt_extra = "• Bottom Extra (X-Dir): Indicated in yellow shaded zones\n" if has_extra else "• Bottom Extra (X-Dir): 100% Sufficient (No extra steel)\n"
        txt_shawka = "• Cantilever Shawka: 6 Φ 12 / m' (Left / Right Cantilevers)\n"
    else:
        txt_extra = "• Bottom Extra (Y-Dir): Indicated in yellow shaded zones\n" if has_extra else "• Bottom Extra (Y-Dir): 100% Sufficient (No extra steel)\n"
        txt_shawka = "• Cantilever Shawka: 6 Φ 12 / m' (Bottom / Top Cantilevers)\n"

    txt_extra_card = (
        f"{txt_extra}"
        f"{txt_shawka}"
        f"• Perimeter Trim (حواف البلاطة): U-Pins Φ10@20cm + 4Φ12 Bars"
    )
    ax_legend.text(52.0, 38, txt_extra_card, fontsize=14.0, fontweight="bold", color="#1e293b" if has_extra else "#166534", linespacing=1.6)

    dir_main_title = f"BOTTOM EXTRA ({dir_req}-DIRECTION)"
    dir_main_title_ar = f"الإضافي السفلي (اتجاه {dir_req})"
    fig.suptitle(
        f"REINFORCEMENT LAYOUT: {dir_main_title}, SHAWKA & BASE MESHES — ts = {ts_cm:.0f} cm\n"
        f"مسقط تسليح البلاطة: {dir_main_title_ar} وشوك الكوابيل وبيان شبكات التسليح الأساسية",
        fontsize=16.5, fontweight="bold", color="#0f172a", y=0.985
    )
    return fig


# ── 3. TOP BASE MESH & EXTRA SLAB TOP MESH SKETCH ────────────────────────────
def generate_flat_slab_top_mesh_extra_sketch(
    Lx_spans, Ly_spans, cantilevers, ts_cm,
    top_extra_slab_bays=None,
    n_mesh_top=5, top_mesh_dia=10,
    n_mesh_btm=6, bottom_mesh_dia=12,
    col_w_cm=30, col_d_cm=30,
    removed_cols=None, void_panel_ids=None,
    direction="X",
):
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    bubble_radius = max(0.50, min(slab_w, slab_h) * 0.038)
    offset_grid_top = max(2.2, slab_h * 0.11)
    offset_grid_left = max(2.2, slab_w * 0.11)
    dim_offset_bot = max(2.0, slab_h * 0.11)
    dim_offset_right = max(1.8, slab_w * 0.09)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.8
    margin_right = dim_offset_right + 1.5
    margin_top = offset_grid_top + bubble_radius * 2 + 0.8
    margin_bot = dim_offset_bot + 1.5

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.0
    target_plan_w = target_plan_h * ar_plan
    legend_h = 5.2

    fig_w = max(22.0, min(34.0, target_plan_w + 1.6))
    fig_h = max(18.0, min(32.0, target_plan_h + legend_h + 1.0))

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=140)
    fig.patch.set_facecolor("#ffffff")

    plan_ratio = (fig_h - legend_h - 0.8) / fig_h
    legend_ratio = legend_h / fig_h

    gs = fig.add_gridspec(2, 1, height_ratios=[plan_ratio, legend_ratio], hspace=0.06, left=0.03, right=0.97, top=0.94, bottom=0.02)
    ax_plan = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])
    ax_plan.set_facecolor("#f8fafc")

    # Slab boundary
    ax_plan.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, slab_h, lw=3.2, edgecolor="#0f172a", facecolor="#ffffff", zorder=1))

    # Voids
    _voids = set(void_panel_ids) if void_panel_ids else set()
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                px0, px1 = x_coords[i], x_coords[i+1]
                py0, py1 = y_coords[j], y_coords[j+1]
                pw, ph = px1 - px0, py1 - py0
                v_rect = patches.Rectangle((px0, py0), pw, ph, facecolor="#f1f5f9", edgecolor="#ef4444", lw=2.2, hatch="//", zorder=2)
                ax_plan.add_patch(v_rect)
                ax_plan.text(px0 + pw/2, py0 + ph/2, "OPENING / VOID", ha="center", va="center", fontsize=13, fontweight="bold", color="#b91c1c", zorder=4, bbox=dict(boxstyle="round,pad=0.4", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.5))

    # Grids & Bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        ax_plan.plot([x, x], [y_slab_min - 0.5, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=3)
        bub = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x, y_top_ext, f"Y{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        ax_plan.plot([x_left_ext, x_slab_max + 0.5], [y, y], color="#dc2626", linestyle=":", linewidth=1.8, alpha=0.8, zorder=3)
        bub = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.4, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x_left_ext, y, f"X{idx+1}", color="#991b1b", fontsize=16, weight="bold", ha="center", va="center", zorder=7)

    # Columns
    col_w_m   = max(col_w_cm / 100.0, slab_w * 0.042)
    col_d_m   = max(col_d_cm / 100.0, slab_h * 0.042)
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()
    col_idx = 1
    for j_idx, y in enumerate(y_coords):
        for i_idx, x in enumerate(x_coords):
            if (x, y) in rem_coords:
                continue
            cid = f"C{col_idx}"
            ax_plan.add_patch(patches.Rectangle((x - col_w_m / 2.0, y - col_d_m / 2.0), col_w_m, col_d_m, lw=2.2, edgecolor="#0f172a", facecolor="#1e293b", zorder=8))
            ax_plan.text(x, y, cid, color="#facc15", fontsize=13, ha="center", va="center", weight="bold", zorder=9)
            col_idx += 1

    # ── Check Extra Top Slab Reinforcement by Direction ─────────────────────
    dir_req = (direction or "X").upper()
    filtered_bays = [
        b for b in (top_extra_slab_bays or [])
        if isinstance(b, dict) and b.get("n_extra", 0) > 0 and b.get("dir", "X").upper() == dir_req
    ]

    has_extra_top = len(filtered_bays) > 0

    if has_extra_top:
        for b_info in filtered_bays:
            pid = b_info.get("panel_id", "")
            if pid in _voids:
                continue

            L_ext = b_info.get("L_extra", 4.0)
            W_bay = b_info.get("W_bay", 4.0)
            n_ext = b_info.get("n_extra", 4)
            dia_ext = b_info.get("dia_extra", 10)
            cx = b_info.get("cx", (x_coords[0] + x_coords[-1])/2.0)
            cy = b_info.get("cy", (y_coords[0] + y_coords[-1])/2.0)

            line_c = "#2563eb"
            edge_c = "#2563eb"
            face_c = "#dbeafe"

            if dir_req == "X":
                area_w = L_ext
                area_h = W_bay * 0.88
                area_rect = patches.Rectangle(
                    (cx - area_w/2.0, cy - area_h/2.0), area_w, area_h,
                    lw=2.2, edgecolor=edge_c, facecolor=face_c, alpha=0.60, linestyle="--", zorder=3
                )
                ax_plan.add_patch(area_rect)

                y_bar = cy + 0.35
                ax_plan.plot([cx - L_ext/2.0, cx + L_ext/2.0], [y_bar, y_bar], color=line_c, lw=4.5, solid_capstyle="round", zorder=6)
                ax_plan.plot([cx - L_ext/2.0, cx - L_ext/2.0], [y_bar, y_bar - 0.35], color=line_c, lw=3.0, zorder=6)
                ax_plan.plot([cx + L_ext/2.0, cx + L_ext/2.0], [y_bar, y_bar - 0.35], color=line_c, lw=3.0, zorder=6)

                ax_plan.text(
                    cx, cy - 0.45,
                    f"★ Top Slab Extra (X-Dir / اتجاه X): {n_ext}Φ{dia_ext}\n"
                    f"Bay Dim: {area_w:.2f}m (L) × {W_bay:.2f}m (W)",
                    ha="center", va="center", fontsize=12.5, fontweight="bold", color="#1d4ed8", zorder=8,
                    rotation=0,
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="#ffffff", edgecolor=edge_c, lw=1.8)
                )
            else:
                area_w = W_bay * 0.88
                area_h = L_ext
                area_rect = patches.Rectangle(
                    (cx - area_w/2.0, cy - area_h/2.0), area_w, area_h,
                    lw=2.2, edgecolor=edge_c, facecolor=face_c, alpha=0.60, linestyle="--", zorder=3
                )
                ax_plan.add_patch(area_rect)

                x_bar = cx + 0.35
                ax_plan.plot([x_bar, x_bar], [cy - L_ext/2.0, cy + L_ext/2.0], color=line_c, lw=4.5, solid_capstyle="round", zorder=6)
                ax_plan.plot([x_bar - 0.35, x_bar], [cy - L_ext/2.0, cy - L_ext/2.0], color=line_c, lw=3.0, zorder=6)
                ax_plan.plot([x_bar - 0.35, x_bar], [cy + L_ext/2.0, cy + L_ext/2.0], color=line_c, lw=3.0, zorder=6)

                ax_plan.text(
                    cx - 0.45, cy,
                    f"★ Top Slab Extra (Y-Dir / اتجاه Y): {n_ext}Φ{dia_ext}\n"
                    f"Bay Dim: {W_bay:.2f}m (W) × {area_h:.2f}m (L)",
                    ha="center", va="center", fontsize=12.5, fontweight="bold", color="#1d4ed8", zorder=8,
                    rotation=90,
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="#ffffff", edgecolor=edge_c, lw=1.8)
                )
    else:
        # ── 🌟 PROMINENT LARGE BANNER WHEN NO EXTRA TOP SLAB REBAR REQUIRED ─────
        mid_x_slab = (x_slab_min + x_slab_max) / 2.0
        mid_y_slab = (y_slab_min + y_slab_max) / 2.0
        banner_w = min(slab_w * 0.78, 14.0)
        banner_h = max(1.8, slab_h * 0.12)

        banner_box = FancyBboxPatch(
            (mid_x_slab - banner_w/2.0, mid_y_slab - banner_h/2.0), banner_w, banner_h,
            boxstyle="round,pad=0.5,rounding_size=0.6",
            facecolor="#f0fdf4", edgecolor="#16a34a", lw=2.6, zorder=10
        )
        ax_plan.add_patch(banner_box)

        dir_en = "X-DIRECTION" if dir_req == "X" else "Y-DIRECTION"
        ax_plan.text(
            mid_x_slab, mid_y_slab,
            f"[OK] NO EXTRA TOP SLAB REBAR IN {dir_en} (كافية تماماً)",
            ha="center", va="center", fontsize=15.0, fontweight="bold", color="#15803d", zorder=11
        )

    # Dimensions
    dim_y = y_slab_min - dim_offset_bot
    if cant_left > 0:
        ax_plan.annotate("", xy=(x_coords[0], dim_y), xytext=(x_slab_min, dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text((x_slab_min + x_coords[0])/2.0, dim_y - 0.4, f"{cant_left:.2f}m", ha="center", va="top", fontsize=13, fontweight="bold", color="#0f172a")
    for i, lx in enumerate(Lx_spans):
        x0, x1 = x_coords[i], x_coords[i+1]
        ax_plan.annotate("", xy=(x1, dim_y), xytext=(x0, dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text((x0 + x1)/2.0, dim_y - 0.4, f"{lx:.2f}m", ha="center", va="top", fontsize=13, fontweight="bold", color="#0f172a")
    if cant_right > 0:
        ax_plan.annotate("", xy=(x_slab_max, dim_y), xytext=(x_coords[-1], dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text((x_coords[-1] + x_slab_max)/2.0, dim_y - 0.4, f"{cant_right:.2f}m", ha="center", va="top", fontsize=13, fontweight="bold", color="#0f172a")

    dim_x = x_slab_max + dim_offset_right
    if cant_bottom > 0:
        ax_plan.annotate("", xy=(dim_x, y_coords[0]), xytext=(dim_x, y_slab_min), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text(dim_x + 0.4, (y_slab_min + y_coords[0])/2.0, f"{cant_bottom:.2f}m", ha="left", va="center", fontsize=13, fontweight="bold", color="#0f172a")
    for j, ly in enumerate(Ly_spans):
        y0, y1 = y_coords[j], y_coords[j+1]
        ax_plan.annotate("", xy=(dim_x, y1), xytext=(dim_x, y0), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text(dim_x + 0.4, (y0 + y1)/2.0, f"{ly:.2f}m", ha="left", va="center", fontsize=13, fontweight="bold", color="#0f172a")
    if cant_top > 0:
        ax_plan.annotate("", xy=(dim_x, y_slab_max), xytext=(dim_x, y_coords[-1]), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6))
        ax_plan.text(dim_x + 0.4, (y_coords[-1] + y_slab_max)/2.0, f"{cant_top:.2f}m", ha="left", va="center", fontsize=13, fontweight="bold", color="#0f172a")

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="datalim")
    ax_plan.axis("off")

    # ── 🌟 DUAL HIGH-CONTRAST LEGEND STRIP WITH BIG FONT ─────────────────────
    ax_legend.set_facecolor("#ffffff")
    ax_legend.set_xlim(0, 100)
    ax_legend.set_ylim(0, 100)
    ax_legend.axis("off")

    # Card 1: Top Base Mesh Card (Left, 48% width)
    box_mesh = FancyBboxPatch((1, 3), 47.5, 94, boxstyle="round,pad=1.0,rounding_size=3", facecolor="#eff6ff", edgecolor="#2563eb", lw=2.5)
    ax_legend.add_patch(box_mesh)
    ax_legend.text(2.5, 75, "[1] TOP BASE MESH (الرقة العلوية الأساسية)", fontsize=16.5, fontweight="bold", color="#1e3a8a")
    txt_top_base = (
        f"• Top Base Mesh (الرقة العلوية): T1(X) & T2(Y) = {n_mesh_top} Φ {top_mesh_dia} mm / m'\n"
        f"• High Chairs (الكراسي الحاملة): Φ 10 mm @ 1.0 m spacing\n"
        f"• Slab Thickness: ts = {ts_cm:.0f} cm  |  Concrete Cover = 25 mm"
    )
    ax_legend.text(2.5, 38, txt_top_base, fontsize=14.0, fontweight="bold", color="#0f172a", linespacing=1.6)

    # Card 2: Top Extra Status Card (Right, 48% width)
    box_extra = FancyBboxPatch((50.5, 3), 48.5, 94, boxstyle="round,pad=1.0,rounding_size=3", facecolor="#eff6ff" if has_extra_top else "#f0fdf4", edgecolor="#2563eb" if has_extra_top else "#16a34a", lw=2.5)
    ax_legend.add_patch(box_extra)
    dir_title = "X-DIR (اتجاه X)" if dir_req == "X" else "Y-DIR (اتجاه Y)"
    ax_legend.text(52.0, 75, f"[2] SLAB TOP EXTRA — {dir_title}", fontsize=16.5, fontweight="bold", color="#1d4ed8" if has_extra_top else "#15803d")
    if not has_extra_top:
        txt_top_extra = (
            f"• Status: 100% Sufficient — No extra top slab rebar needed\n"
            f"• All middle strip negative moments resisted by Top Mesh\n"
            f"• For column caps top extra moments, refer to Tab 1"
        )
        ax_legend.text(52.0, 38, txt_top_extra, fontsize=14.0, fontweight="bold", color="#166534", linespacing=1.6)
    else:
        txt_top_extra = (
            f"• Top Extra ({dir_title}): Indicated in blue shaded bay zones\n"
            f"• Placement: Upper layer with downward end hooks\n"
            f"• For column caps top extra moments, refer to Tab 1"
        )
        ax_legend.text(52.0, 38, txt_top_extra, fontsize=14.0, fontweight="bold", color="#1e293b", linespacing=1.6)

    dir_main_title = f"EXTRA SLAB TOP STEEL ({dir_req}-DIRECTION)"
    dir_main_title_ar = f"الحديد الإضافي العلوي للبلاطة (اتجاه {dir_req})"
    fig.suptitle(
        f"REINFORCEMENT LAYOUT: TOP BASE MESH & {dir_main_title} — ts = {ts_cm:.0f} cm\n"
        f"مسقط تسليح البلاطة: الرقة العلوية الأساسية و{dir_main_title_ar}",
        fontsize=16.5, fontweight="bold", color="#0f172a", y=0.985
    )
    return fig


def generate_flat_slab_master_steel_layout_sketch(
    Lx_spans, Ly_spans, cantilevers, ts_cm,
    n_mesh_btm, bottom_mesh_dia,
    n_mesh_top, top_mesh_dia,
    top_extra_cols, cant_rft_list,
    btm_extra_spans=None,
    col_w_cm=30, col_d_cm=30,
    removed_cols=None,
    void_panel_ids=None,
):
    """
    Generates a master 2D structural floor plan (Steel Layout - مسقط أفقي لتسليح البلاطة)
    showing ALL reinforcement layers on one comprehensive CAD-style drawing:
    - Base Bottom Mesh (M11, M22)
    - Base Top Mesh (T1, T2)
    - Column Top Extra Caps (كابات الأعمدة) with exact counts, dia, and lengths
    - Additional Bottom Steel in enlarged bays (حديد إضافي سفلي) with lengths and counts
    - Cantilever Shawka Rebar (شوك الكوابيل)
    - Perimeter U-Pins & Edge Bars
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)

    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    cant_left   = cantilevers.get("left",   0.0)
    cant_right  = cantilevers.get("right",  0.0)
    cant_bottom = cantilevers.get("bottom", 0.0)
    cant_top    = cantilevers.get("top",    0.0)

    x_slab_min = x_coords[0]  - cant_left
    x_slab_max = x_coords[-1] + cant_right
    y_slab_min = y_coords[0]  - cant_bottom
    y_slab_max = y_coords[-1] + cant_top

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    # Grid bubble offsets & margins
    bubble_radius = max(0.44, min(slab_w, slab_h) * 0.034)
    offset_grid_top = max(1.8, slab_h * 0.10)
    offset_grid_left = max(1.8, slab_w * 0.10)
    dim_offset_bot = max(1.6, slab_h * 0.10)
    dim_offset_right = max(1.5, slab_w * 0.08)

    margin_left = offset_grid_left + bubble_radius * 2 + 0.6
    margin_right = dim_offset_right + 1.2
    margin_top = offset_grid_top + bubble_radius * 2 + 0.6
    margin_bot = dim_offset_bot + 1.2

    total_w = slab_w + margin_left + margin_right
    total_h = slab_h + margin_top + margin_bot
    ar_plan = total_w / total_h

    target_plan_h = 16.5
    target_plan_w = target_plan_h * ar_plan
    legend_h = 4.4

    fig_w = max(24.0, min(36.0, target_plan_w + 1.6))
    fig_h = max(18.0, min(36.0, target_plan_h + legend_h + 1.2))

    plan_ratio = (fig_h - legend_h - 1.0) / fig_h
    legend_ratio = legend_h / fig_h

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=140)
    fig.patch.set_facecolor("#ffffff")

    gs = gridspec.GridSpec(
        2, 1,
        height_ratios=[plan_ratio, legend_ratio],
        hspace=0.06,
        left=0.03, right=0.97, top=0.94, bottom=0.02,
    )

    ax_plan   = fig.add_subplot(gs[0, 0])
    ax_legend = fig.add_subplot(gs[1, 0])
    ax_plan.set_facecolor("#f8fafc")

    # 1. Slab Outer Boundary
    slab_rect = patches.Rectangle(
        (x_slab_min, y_slab_min), slab_w, slab_h,
        linewidth=3.0, edgecolor="#0f172a", facecolor="#ffffff", zorder=1,
    )
    ax_plan.add_patch(slab_rect)

    # 2. Voids / Openings
    _voids = set(void_panel_ids) if void_panel_ids else set()
    for j in range(len(Ly_spans)):
        for i in range(len(Lx_spans)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _voids:
                px0, px1 = x_coords[i], x_coords[i+1]
                py0, py1 = y_coords[j], y_coords[j+1]
                pw, ph = px1 - px0, py1 - py0
                v_rect = patches.Rectangle((px0, py0), pw, ph, facecolor="#f1f5f9", edgecolor="#ef4444", lw=2.0, hatch="//", zorder=2)
                ax_plan.add_patch(v_rect)
                ax_plan.plot([px0, px1], [py0, py1], color="#ef4444", lw=1.5, ls="--", zorder=3)
                ax_plan.plot([px0, px1], [py1, py0], color="#ef4444", lw=1.5, ls="--", zorder=3)
                ax_plan.text(px0 + pw/2, py0 + ph/2, "OPENING / VOID", ha="center", va="center", fontsize=11, fontweight="bold", color="#b91c1c", zorder=4, bbox=dict(boxstyle="round,pad=0.3", facecolor="#fee2e2", edgecolor="#ef4444", lw=1.2))

    # 3. Grid Lines & Bubbles
    for idx, x in enumerate(x_coords):
        y_top_ext = y_slab_max + offset_grid_top
        ax_plan.plot([x, x], [y_slab_min - 0.4, y_top_ext], color="#dc2626", linestyle=":", linewidth=1.6, alpha=0.75, zorder=3)
        bub = Circle((x, y_top_ext), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.2, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x, y_top_ext, f"Y{idx+1}", color="#991b1b", fontsize=14, weight="bold", ha="center", va="center", zorder=7)

    for idx, y in enumerate(y_coords):
        x_left_ext = x_slab_min - offset_grid_left
        ax_plan.plot([x_left_ext, x_slab_max + 0.4], [y, y], color="#dc2626", linestyle=":", linewidth=1.6, alpha=0.75, zorder=3)
        bub = Circle((x_left_ext, y), radius=bubble_radius, facecolor="#fee2e2", edgecolor="#dc2626", lw=2.2, zorder=6)
        ax_plan.add_patch(bub)
        ax_plan.text(x_left_ext, y, f"X{idx+1}", color="#991b1b", fontsize=14, weight="bold", ha="center", va="center", zorder=7)

    # 4. Columns & Labels
    col_w_m   = max(col_w_cm / 100.0, slab_w * 0.04)
    col_d_m   = max(col_d_cm / 100.0, slab_h * 0.04)
    rem_coords = {(c["x"], c["y"]) for c in removed_cols} if removed_cols else set()

    col_dict = {}
    col_idx = 1
    for j_idx, y in enumerate(y_coords):
        for i_idx, x in enumerate(x_coords):
            if (x, y) in rem_coords:
                continue
            cid = f"C{col_idx}"
            col_dict[cid] = (x, y, i_idx, j_idx)
            ax_plan.add_patch(patches.Rectangle(
                (x - col_w_m / 2.0, y - col_d_m / 2.0), col_w_m, col_d_m,
                linewidth=2.0, edgecolor="#0f172a", facecolor="#1e293b", zorder=8,
            ))
            ax_plan.text(x, y, cid, color="#facc15", fontsize=11, ha="center", va="center", weight="bold", zorder=9)
            col_idx += 1

    # 5. Base Mesh Indicators (Bottom & Top) in Central Bays
    mid_i = len(Lx_spans) // 2
    mid_j = len(Ly_spans) // 2
    bm_x0 = x_coords[mid_i] + 0.3 * Lx_spans[mid_i]
    bm_y0 = y_coords[mid_j] + 0.3 * Ly_spans[mid_j]

    # Bottom Mesh symbol
    ax_plan.annotate("", xy=(bm_x0 + 1.8, bm_y0), xytext=(bm_x0 - 0.2, bm_y0),
                    arrowprops=dict(arrowstyle="<->", color="#2563eb", lw=3.0), zorder=5)
    ax_plan.annotate("", xy=(bm_x0 + 0.8, bm_y0 + 1.8), xytext=(bm_x0 + 0.8, bm_y0 - 0.2),
                    arrowprops=dict(arrowstyle="<->", color="#2563eb", lw=3.0), zorder=5)
    ax_plan.text(bm_x0 + 0.8, bm_y0 - 0.55,
                f"BOTTOM MESH (BTM)\n"
                f"M11 (X): {n_mesh_btm} Φ{bottom_mesh_dia}/m'\n"
                f"M22 (Y): {n_mesh_btm} Φ{bottom_mesh_dia}/m'",
                ha="center", va="top", fontsize=10.0, fontweight="bold", color="#1e40af", zorder=7,
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#eff6ff", edgecolor="#3b82f6", lw=1.5))

    # Top Mesh symbol
    top_i = 0 if len(Lx_spans) > 1 else mid_i
    top_j = 0 if len(Ly_spans) > 1 else mid_j
    tm_x0 = x_coords[top_i] + 0.5 * Lx_spans[top_i]
    tm_y0 = y_coords[top_j] + 0.5 * Ly_spans[top_j]
    ax_plan.annotate("", xy=(tm_x0 + 1.5, tm_y0), xytext=(tm_x0 - 0.5, tm_y0),
                    arrowprops=dict(arrowstyle="<->", color="#16a34a", lw=2.5, ls="--"), zorder=5)
    ax_plan.annotate("", xy=(tm_x0 + 0.5, tm_y0 + 1.5), xytext=(tm_x0 + 0.5, tm_y0 - 0.5),
                    arrowprops=dict(arrowstyle="<->", color="#16a34a", lw=2.5, ls="--"), zorder=5)
    ax_plan.text(tm_x0 + 0.5, tm_y0 + 1.75,
                f"TOP BASE MESH (TOP)\n"
                f"T1 & T2: {n_mesh_top} Φ{top_mesh_dia}/m' (X & Y)",
                ha="center", va="bottom", fontsize=10.0, fontweight="bold", color="#15803d", zorder=7,
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#f0fdf4", edgecolor="#22c55e", lw=1.5))

    # 6. Column Caps (Top Extra Reinforcement over columns)
    for c_info in (top_extra_cols or []):
        if not c_info.get("is_needed"):
            continue
        cid = c_info["id"]
        if cid not in col_dict:
            continue
        cx, cy, ci, cj = col_dict[cid]
        L_ext = c_info.get("L_extra", 3.0)
        n_ext = c_info.get("n_extra", 6)
        dia_ext = c_info.get("dia_extra", 12)
        callout = c_info.get("callout", f"{n_ext}Φ{dia_ext}")

        cap_w = L_ext
        cap_h = min(Lx_spans[min(ci, len(Lx_spans)-1)], Ly_spans[min(cj, len(Ly_spans)-1)]) * 0.45
        cap_rect = patches.Rectangle(
            (cx - cap_w/2.0, cy - cap_h/2.0), cap_w, cap_h,
            linewidth=1.5, edgecolor="#dc2626", facecolor="#fee2e2", alpha=0.55, linestyle="--", zorder=4
        )
        ax_plan.add_patch(cap_rect)

        bar_y = cy + col_d_m/2.0 + 0.15
        ax_plan.plot([cx - cap_w/2.0, cx + cap_w/2.0], [bar_y, bar_y], color="#dc2626", lw=3.0, zorder=6)
        ax_plan.plot([cx - cap_w/2.0, cx - cap_w/2.0], [bar_y, bar_y - 0.25], color="#dc2626", lw=2.5, zorder=6)
        ax_plan.plot([cx + cap_w/2.0, cx + cap_w/2.0], [bar_y, bar_y - 0.25], color="#dc2626", lw=2.5, zorder=6)

        is_above = ((ci + cj) % 2 == 0)
        tag_y = (cy + cap_h/2.0 + 0.30) if is_above else (cy - cap_h/2.0 - 0.30)
        va_pos = "bottom" if is_above else "top"
        ax_plan.text(
            cx, tag_y, f"Top Cap: {callout} (L={L_ext:.2f}m)",
            ha="center", va=va_pos, fontsize=9.5, fontweight="bold", color="#991b1b", zorder=8,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#dc2626", lw=1.2)
        )

    # 7. Additional Bottom Steel in Bays
    for b_info in (btm_extra_spans or []):
        if not isinstance(b_info, dict) or b_info.get("n_extra", 0) <= 0:
            continue
        span_len = b_info.get("span_len", 5.0)
        Ln = b_info.get("Ln", span_len - 0.6)
        L_ext = b_info.get("L_extra", Ln * 0.8)
        n_ext = b_info.get("n_extra", 6)
        dia_ext = b_info.get("dia_extra", 12)
        callout = b_info.get("callout", f"{n_ext}Φ{dia_ext}")
        dir_b = b_info.get("dir", "X")
        bay_lbl = b_info.get("bay_label", "")

        bx_c = (x_coords[0] + x_coords[-1]) / 2.0
        by_c = (y_coords[0] + y_coords[-1]) / 2.0
        for i in range(len(Lx_spans)):
            for j in range(len(Ly_spans)):
                if f"X{i+1}" in bay_lbl and f"Y{j+1}" in bay_lbl:
                    bx_c = (x_coords[i] + x_coords[i+1]) / 2.0
                    by_c = (y_coords[j] + y_coords[j+1]) / 2.0

        if dir_b == "X":
            ax_plan.plot([bx_c - L_ext/2.0, bx_c + L_ext/2.0], [by_c, by_c], color="#d97706", lw=3.8, solid_capstyle="round", zorder=6)
            ax_plan.plot([bx_c - L_ext/2.0, bx_c - L_ext/2.0], [by_c - 0.2, by_c + 0.2], color="#d97706", lw=2.5, zorder=6)
            ax_plan.plot([bx_c + L_ext/2.0, bx_c + L_ext/2.0], [by_c - 0.2, by_c + 0.2], color="#d97706", lw=2.5, zorder=6)
            ax_plan.text(
                bx_c, by_c - 0.40, f"Btm Extra: {callout} (L={L_ext:.2f}m)",
                ha="center", va="top", fontsize=9.5, fontweight="bold", color="#b45309", zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.2)
            )
        else:
            ax_plan.plot([bx_c, bx_c], [by_c - L_ext/2.0, by_c + L_ext/2.0], color="#d97706", lw=3.8, solid_capstyle="round", zorder=6)
            ax_plan.plot([bx_c - 0.2, bx_c + 0.2], [by_c - L_ext/2.0, by_c - L_ext/2.0], color="#d97706", lw=2.5, zorder=6)
            ax_plan.plot([bx_c - 0.2, bx_c + 0.2], [by_c + L_ext/2.0, by_c + L_ext/2.0], color="#d97706", lw=2.5, zorder=6)
            ax_plan.text(
                bx_c + 0.40, by_c, f"Btm Extra: {callout}\n(L={L_ext:.2f}m)",
                ha="left", va="center", fontsize=9.5, fontweight="bold", color="#b45309", zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.2)
            )

    # 8. Cantilever Shawka Rebar (Overhang Zones)
    for cr in (cant_rft_list or []):
        side = cr.get("side", "")
        L_c = cr.get("length", 0.0)
        tot_L = cr.get("total_bar_length", 3.0)
        callout = cr.get("rft_callout", "6Φ12/m'")

        if side == "left" and cant_left > 0:
            cy_mid = (y_slab_min + y_slab_max) / 2.0
            cx_tip = x_slab_min
            cx_inner = x_coords[0] + 1.5 * L_c
            ax_plan.plot([cx_tip, cx_inner], [cy_mid, cy_mid], color="#9333ea", lw=3.5, zorder=6)
            ax_plan.plot([cx_tip, cx_tip + 0.5 * L_c], [cy_mid - 0.3, cy_mid - 0.3], color="#9333ea", lw=3.0, zorder=6)
            ax_plan.plot([cx_tip, cx_tip], [cy_mid - 0.3, cy_mid], color="#9333ea", lw=3.0, zorder=6)
            ax_plan.text(
                cx_tip + L_c/2.0, cy_mid + 0.45, f"Shawka: {callout}\n(Cut L={tot_L:.2f}m)",
                ha="center", va="bottom", fontsize=9.5, fontweight="bold", color="#7e22ce", zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#faf5ff", edgecolor="#a855f7", lw=1.2)
            )
        elif side == "top" and cant_top > 0:
            cx_mid = (x_slab_min + x_slab_max) / 2.0
            cy_tip = y_slab_max
            cy_inner = y_coords[-1] - 1.5 * L_c
            ax_plan.plot([cx_mid, cx_mid], [cy_tip, cy_inner], color="#9333ea", lw=3.5, zorder=6)
            ax_plan.plot([cx_mid + 0.3, cx_mid + 0.3], [cy_tip, cy_tip - 0.5 * L_c], color="#9333ea", lw=3.0, zorder=6)
            ax_plan.plot([cx_mid, cx_mid + 0.3], [cy_tip, cy_tip], color="#9333ea", lw=3.0, zorder=6)
            ax_plan.text(
                cx_mid + 0.55, cy_tip - L_c/2.0, f"Shawka: {callout}\n(Cut L={tot_L:.2f}m)",
                ha="left", va="center", fontsize=9.5, fontweight="bold", color="#7e22ce", zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#faf5ff", edgecolor="#a855f7", lw=1.2)
            )

    # 9. Perimeter Trim & U-Pins Callout
    perim_tag_x = x_slab_max - 0.4
    perim_tag_y = y_slab_min + 0.4
    ax_plan.text(
        perim_tag_x, perim_tag_y,
        "Perimeter Trim: U-Pins Φ10@20cm + 4Φ12 Edge Bars",
        ha="right", va="bottom", fontsize=9.5, fontweight="bold", color="#475569", zorder=8,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8fafc", edgecolor="#64748b", lw=1.2)
    )

    # 10. Dimension Lines
    dim_y = y_slab_min - dim_offset_bot
    if cant_left > 0:
        ax_plan.annotate("", xy=(x_coords[0], dim_y), xytext=(x_slab_min, dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
        ax_plan.text((x_slab_min + x_coords[0])/2.0, dim_y - 0.35, f"{cant_left:.2f}m", ha="center", va="top", fontsize=11, fontweight="bold", color="#0f172a")
    for i, lx in enumerate(Lx_spans):
        x0, x1 = x_coords[i], x_coords[i+1]
        ax_plan.annotate("", xy=(x1, dim_y), xytext=(x0, dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
        ax_plan.text((x0 + x1)/2.0, dim_y - 0.35, f"{lx:.2f}m", ha="center", va="top", fontsize=11, fontweight="bold", color="#0f172a")
    if cant_right > 0:
        ax_plan.annotate("", xy=(x_slab_max, dim_y), xytext=(x_coords[-1], dim_y), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
        ax_plan.text((x_coords[-1] + x_slab_max)/2.0, dim_y - 0.35, f"{cant_right:.2f}m", ha="center", va="top", fontsize=11, fontweight="bold", color="#0f172a")

    dim_x = x_slab_max + dim_offset_right
    if cant_bottom > 0:
        ax_plan.annotate("", xy=(dim_x, y_coords[0]), xytext=(dim_x, y_slab_min), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
        ax_plan.text(dim_x + 0.35, (y_slab_min + y_coords[0])/2.0, f"{cant_bottom:.2f}m", ha="left", va="center", fontsize=11, fontweight="bold", color="#0f172a")
    for j, ly in enumerate(Ly_spans):
        y0, y1 = y_coords[j], y_coords[j+1]
        ax_plan.annotate("", xy=(dim_x, y1), xytext=(dim_x, y0), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
        ax_plan.text(dim_x + 0.35, (y0 + y1)/2.0, f"{ly:.2f}m", ha="left", va="center", fontsize=11, fontweight="bold", color="#0f172a")
    if cant_top > 0:
        ax_plan.annotate("", xy=(dim_x, y_slab_max), xytext=(dim_x, y_coords[-1]), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.4))
        ax_plan.text(dim_x + 0.35, (y_coords[-1] + y_slab_max)/2.0, f"{cant_top:.2f}m", ha="left", va="center", fontsize=11, fontweight="bold", color="#0f172a")

    ax_plan.set_xlim(x_slab_min - margin_left, x_slab_max + margin_right)
    ax_plan.set_ylim(y_slab_min - margin_bot, y_slab_max + margin_top)
    ax_plan.set_aspect("equal", adjustable="datalim")
    ax_plan.axis("off")

    # 11. Engineering Legend Strip below Plan
    ax_legend.set_facecolor("#ffffff")
    ax_legend.set_xlim(0, 100)
    ax_legend.set_ylim(0, 100)
    ax_legend.axis("off")

    legend_cards = [
        {
            "title": "1. BOTTOM MESH (M11 & M22)",
            "content": f"• M11 (X-dir): {n_mesh_btm} Φ{bottom_mesh_dia}/m'\n• M22 (Y-dir): {n_mesh_btm} Φ{bottom_mesh_dia}/m'\n• Straight continuous bars (Cover=2.5cm)",
            "bg": "#eff6ff", "border": "#3b82f6",
        },
        {
            "title": "2. TOP BASE MESH (T1 & T2)",
            "content": f"• T1 & T2 (X & Y): {n_mesh_top} Φ{top_mesh_dia}/m'\n• Shrinkage & crack control mesh\n• Standard 90° down-hooks at slab edge",
            "bg": "#f0fdf4", "border": "#22c55e",
        },
        {
            "title": "3. COLUMN CAPS (TOP EXTRA)",
            "content": f"• Extra Top Rebar over high -M columns\n• Extends 0.25Ln each side into col strips\n• Cut Length = 0.50Ln + col width + hooks",
            "bg": "#fef2f2", "border": "#ef4444",
        },
        {
            "title": "4. BOTTOM EXTRA & SHAWKA",
            "content": f"• Btm Extra: Centered @ large bays (0.80Ln)\n• Shawka: Main 6Φ12/m' extends 1.5 L_cant\n• U-Pins: Φ10@20cm + 4Φ12 Edge perimeter",
            "bg": "#fffbeb", "border": "#f59e0b",
        },
    ]

    card_w = 23.5
    card_gap = 1.3
    card_start = 1.0

    for idx, card in enumerate(legend_cards):
        cx = card_start + idx * (card_w + card_gap)
        c_box = FancyBboxPatch(
            (cx, 4), card_w, 92,
            boxstyle="round,pad=1.0,rounding_size=3",
            facecolor=card["bg"], edgecolor=card["border"], lw=1.8,
        )
        ax_legend.add_patch(c_box)

        t_bar = FancyBboxPatch(
            (cx + 0.6, 70), card_w - 1.2, 22,
            boxstyle="round,pad=0.6,rounding_size=2",
            facecolor=card["border"], edgecolor="none"
        )
        ax_legend.add_patch(t_bar)
        ax_legend.text(cx + card_w/2.0, 81, card["title"], ha="center", va="center", fontsize=10.5, fontweight="bold", color="#ffffff")
        ax_legend.text(cx + 1.2, 45, card["content"], ha="left", va="center", fontsize=9.2, color="#1e293b", linespacing=1.35)

    fig.suptitle(
        f"FLAT SLAB MASTER REINFORCEMENT LAYOUT PLAN (ECP 203) — ts = {ts_cm:.0f} cm\n"
        f"المسقط الأفقي التنفيذي الشامل لتسليح البلاطة اللاكمرية ومواقع وتفاصيل الحديد",
        fontsize=16.0, fontweight="bold", color="#0f172a", y=0.985
    )

    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  DESIGN & CALCULATION ENGINES
# ═══════════════════════════════════════════════════════════════════════════════

def ddm_moments(Wu, L_perp, Ln, is_exterior):

    """
    Direct Design Method — total static moment and strip distribution (ECP 203).
    """
    Mo = Wu * L_perp * Ln**2 / 8.0

    if is_exterior:
        M_neg_ext = 0.00 * Mo
        M_pos     = 0.35 * Mo
        M_neg_int = 0.65 * Mo
    else:
        M_neg_ext = 0.65 * Mo
        M_pos     = 0.35 * Mo
        M_neg_int = 0.65 * Mo

    return dict(
        Mo        = Mo,
        M_neg_ext = M_neg_ext,
        M_pos     = M_pos,
        M_neg_int = M_neg_int,
        cs_neg_ext = 0.75 * M_neg_ext,
        ms_neg_ext = 0.25 * M_neg_ext,
        cs_pos     = 0.60 * M_pos,
        ms_pos     = 0.40 * M_pos,
        cs_neg_int = 0.75 * M_neg_int,
        ms_neg_int = 0.25 * M_neg_int,
    )


def calc_As(M_ton_m, width_m, d_cm, Fcu, Fy, ts):
    """
    Required steel area (cm²) for the full strip width.
    """
    width_m = max(0.10, float(width_m))
    if M_ton_m <= 0:
        M_ton_m = 0.001
    M_kg_cm  = M_ton_m * 100_000.0
    w_cm     = width_m * 100.0
    a_est    = 0.1 * d_cm
    denom_est = max(0.1, (d_cm - a_est / 2.0))
    As_est   = M_kg_cm / (0.9 * Fy * denom_est)
    a_ref    = (As_est * Fy) / (0.85 * Fcu * max(1.0, w_cm))
    denom_ref = max(0.1, (d_cm - a_ref / 2.0))
    As_ref   = M_kg_cm / (0.9 * Fy * denom_ref)
    As_min   = 0.0018 * w_cm * ts
    return max(As_ref, As_min)


def calc_moment_capacity_btm(As_cm2_per_m, d_cm, Fcu, Fy):
    """
    Moment capacity (t.m/m) of bottom mesh reinforcement per unit width (1 m strip).
    Uses ECP 203 rectangular stress block approach:
      a  = (As * Fy) / (0.85 * Fcu * b)   with b = 100 cm (per metre width)
      Mu = 0.9 * Fy * As * (d - a/2)
    Returns capacity in t.m/m.
    """
    As = max(As_cm2_per_m, 0.001)   # cm²/m  (already per-metre)
    a  = (As * Fy) / (0.85 * Fcu * 100.0)            # stress-block depth [cm], b=100 cm/m
    M_kg_cm = 0.9 * Fy * As * max(0.1, d_cm - a / 2.0)  # kg.cm per metre width
    return M_kg_cm / 100_000.0                           # → t.m/m


def calculate_punching_shear(columns, Lx_spans, Ly_spans, cantilevers, Wu, d_cm, Fcu):
    """
    Check punching shear capacity for every column (ECP 203).
    Returns list of detailed dicts.
    """
    results = []
    cant_L = cantilevers.get("left", 0.0)
    cant_R = cantilevers.get("right", 0.0)
    cant_B = cantilevers.get("bottom", 0.0)
    cant_T = cantilevers.get("top", 0.0)

    n_x = len(Lx_spans)
    n_y = len(Ly_spans)

    for col in columns:
        i = col.get("i_eff", col["i"])
        j = col.get("j_eff", col["j"])
        bc, tc = col["bc"], col["tc"]
        ctype = col["type"]

        if "Pu" in col and col["Pu"] is not None:
            Pu = col["Pu"]
        else:
            if i == 0:
                ltx = cant_L + Lx_spans[0] / 2.0
            elif i >= n_x:
                ltx = Lx_spans[-1] / 2.0 + cant_R
            else:
                ltx = (Lx_spans[min(max(0, i - 1), len(Lx_spans)-1)] + Lx_spans[min(i, len(Lx_spans)-1)]) / 2.0

            if j == 0:
                lty = cant_B + Ly_spans[0] / 2.0
            elif j >= n_y:
                lty = Ly_spans[-1] / 2.0 + cant_T
            else:
                lty = (Ly_spans[min(max(0, j - 1), len(Ly_spans)-1)] + Ly_spans[min(j, len(Ly_spans)-1)]) / 2.0

            Atrib = ltx * lty
            Pu = Wu * Atrib

        Pu_kg = Pu * 1000.0

        if ctype == "Corner":
            beta = 1.50
            bo = (bc + d_cm / 2.0) + (tc + d_cm / 2.0)
            alpha_s = 2.0
        elif ctype == "Edge":
            beta = 1.30
            if i == 0 or i >= n_x:
                bo = 2.0 * (bc + d_cm / 2.0) + (tc + d_cm)
            else:
                bo = (bc + d_cm) + 2.0 * (tc + d_cm / 2.0)
            alpha_s = 3.0
        else:
            beta = 1.15
            bo = 2.0 * (bc + d_cm) + 2.0 * (tc + d_cm)
            alpha_s = 4.0

        qup = (beta * Pu_kg) / (bo * d_cm)

        qcup1 = 0.815 * math.sqrt(Fcu / 1.5)
        qcup2 = 0.8 * (alpha_s * d_cm / bo + 0.2) * math.sqrt(Fcu / 1.5) * (math.sqrt(10) * 0.316)
        qcup3 = 0.316 * (0.5 + min(bc, tc) / max(bc, tc)) * math.sqrt(Fcu / 1.5) * math.sqrt(10)
        qcup = min(qcup1, qcup2, qcup3, 17.0)

        ratio = qup / qcup
        is_safe = ratio <= 1.0

        results.append({
            "Column ID": col["id"],
            "Grid": f"{col['grid_x']} - {col['grid_y']}",
            "Location Type": ctype,
            "Pu (ton)": Pu,
            "bo (cm)": bo,
            "qup (kg/cm²)": qup,
            "qcup (kg/cm²)": qcup,
            "Ratio": ratio,
            "Status": "✅ Safe" if is_safe else "⚠️ Unsafe (Needs Drop / Studs)",
            "is_safe": is_safe,
            "x": col.get("x", 0.0),
            "y": col.get("y", 0.0),
            "bc": bc,
            "tc": tc,
        })
    return results


def calculate_extra_top_steel_at_columns(
    columns,
    rows_x,
    rows_y,
    Lx_spans,
    Ly_spans,
    d_cm,
    Fcu,
    Fy,
    ts_cm,
    mesh_top_prov_cm2m,
    extra_dia_mm=12,
    enlarged_bays=None,
):
    """
    Determine required Top Extra Steel at each column (C1, C2, ...).
    """
    col_extras = []
    a_extra_bar = bar_area(extra_dia_mm)

    for col in columns:
        i = col.get("i_eff", col["i"])
        j = col.get("j_eff", col["j"])
        cid = col["id"]
        ctype = col["type"]

        # Adjacent spans
        lx_adj = Lx_spans[min(max(0, i), len(Lx_spans) - 1)]
        ly_adj = Ly_spans[min(max(0, j), len(Ly_spans) - 1)]
        w_cs = max(0.5, min(lx_adj, ly_adj) / 2.0)

        # Peak negative moment at this column
        mx_cand = rows_x[min(max(0, i), len(rows_x) - 1)]["cs_neg_int"] if rows_x else 1.0
        my_cand = rows_y[min(max(0, j), len(rows_y) - 1)]["cs_neg_int"] if rows_y else 1.0
        M_neg_col = max(mx_cand, my_cand)

        # If column is adjacent to an enlarged bay, adjust negative moment
        if enlarged_bays:
            for eb in enlarged_bays:
                # Check proximity
                if math.hypot(col["x"] - eb.get("mid_x", 0), col["y"] - eb.get("mid_y", 0)) <= eb.get("span_len", 6.0) * 0.75:
                    M_neg_from_enlarged = 0.65 * eb.get("Mo", 0.0)
                    if M_neg_from_enlarged > M_neg_col:
                        M_neg_col = M_neg_from_enlarged
                        span_gov_candidate = eb.get("span_len", lx_adj)
                        if span_gov_candidate > max(lx_adj, ly_adj):
                            lx_adj = span_gov_candidate

        if ctype == "Corner":
            M_neg_col = M_neg_col * 0.40
        elif ctype == "Edge":
            M_neg_col = M_neg_col * 0.70

        As_tot_req = calc_As(M_neg_col, w_cs, d_cm, Fcu, Fy, ts_cm)
        As_req_m = As_tot_req / w_cs

        # Extra steel required over base top mesh
        As_extra_m = max(0.0, As_req_m - mesh_top_prov_cm2m)
        As_extra_tot = As_extra_m * w_cs

        if As_extra_m > 0.05:
            n_extra = max(2, math.ceil(As_extra_tot / a_extra_bar))
            is_needed = True
        else:
            n_extra = 0
            is_needed = False

        # Development length
        span_gov = max(lx_adj, ly_adj)
        if ctype == "Corner":
            L_extra = round(0.30 * span_gov + col["bc"] / 100.0, 2)
        elif ctype == "Edge":
            L_extra = round(0.30 * span_gov * 2.0 * 0.75 + col["bc"] / 100.0, 2)
        else:
            L_extra = round(2.0 * 0.30 * span_gov + col["bc"] / 100.0, 2)

        col_extras.append({
            "id": cid,
            "x": col["x"],
            "y": col["y"],
            "i": col.get("i", i),
            "j": col.get("j", j),
            "grid": f"{col['grid_x']} - {col['grid_y']}",
            "type": ctype,
            "Mu_neg (t.m)": M_neg_col,
            "As_req (cm²/m)": As_req_m,
            "As_mesh (cm²/m)": mesh_top_prov_cm2m,
            "As_extra (cm²/m)": As_extra_m,
            "n_extra": n_extra,
            "dia_extra": extra_dia_mm,
            "L_extra": L_extra,
            "callout": f"+{n_extra} Φ{extra_dia_mm} (L={L_extra:.2f}m)" if is_needed else "Mesh is Sufficient (الشبكة تكفي)",
            "is_needed": is_needed,
        })
    return col_extras


def calculate_cantilever_reinforcement(cantilevers, Wu, d_cm, Fcu, Fy, ts_cm, bar_dia_mm=12):
    """
    Calculate Shawka top reinforcement for all cantilevers.
    """
    cant_rft = []
    a_bar = bar_area(bar_dia_mm)

    for side in ["left", "right", "bottom", "top"]:
        L_c = cantilevers.get(side, 0.0)
        if L_c > 0:
            M_u = Wu * (L_c ** 2) / 2.0  # ton.m/m
            As_req_m = calc_As(M_u, 1.0, d_cm, Fcu, Fy, ts_cm)
            n_bars = max(5, math.ceil(As_req_m / a_bar))
            sp = min(20.0, round(100.0 / n_bars, 1))
            ext_len = round(1.5 * L_c, 2)
            total_bar_l = round(L_c + ts_cm / 100.0 + ext_len, 2)

            cant_rft.append({
                "side": side,
                "side_ar": {"left": "اليسار", "right": "اليمين", "bottom": "الأسفل", "top": "الأعلى"}[side],
                "length": L_c,
                "Mu (t.m/m)": M_u,
                "As_req (cm²/m)": As_req_m,
                "rft_callout": f"{n_bars} Φ{bar_dia_mm} / m'",
                "ext_length": ext_len,
                "total_bar_length": total_bar_l,
                "secondary_rft": "5 Φ10 / m'",
            })
    return cant_rft


def calculate_boq(Lx_spans, Ly_spans, cantilevers, ts_cm, mesh_btm_n, mesh_btm_dia, mesh_top_n, mesh_top_dia, col_extras, cant_rft_list, btm_extra_spans=None, void_panels=None, fcu=250):
    """
    Calculate comprehensive Bill of Quantities (BoQ) for Concrete, Raw Materials, and Steel,
    including per-item details and diameter-based weight summaries.
    """
    cant_L = cantilevers.get("left", 0.0)
    cant_R = cantilevers.get("right", 0.0)
    cant_B = cantilevers.get("bottom", 0.0)
    cant_T = cantilevers.get("top", 0.0)

    total_w = sum(Lx_spans) + cant_L + cant_R
    total_h = sum(Ly_spans) + cant_B + cant_T
    gross_area = total_w * total_h
    void_area = sum(p["area"] for p in void_panels if p.get("is_void")) if void_panels else 0.0
    slab_area = max(0.1, gross_area - void_area)
    concrete_vol = slab_area * (ts_cm / 100.0)

    # Dictionary for accumulation by diameter
    dia_dict = {}

    def add_steel(dia_mm, length_m, app_label):
        if dia_mm not in dia_dict:
            dia_dict[dia_mm] = {"length_m": 0.0, "weight_kg": 0.0, "apps": set()}
        unit_w = bar_unit_weight(dia_mm)
        w_kg = length_m * unit_w
        dia_dict[dia_mm]["length_m"] += length_m
        dia_dict[dia_mm]["weight_kg"] += w_kg
        dia_dict[dia_mm]["apps"].add(app_label)
        return length_m, w_kg

    # 1. Bottom Base Mesh (B1, B2)
    len_btm_m = slab_area * (mesh_btm_n * 2.0) * 1.06
    _, steel_btm_kg = add_steel(mesh_btm_dia, len_btm_m, "الشبكة الأساسية السفلية (Bottom Mesh)")

    # 2. Top Base Mesh (T1, T2)
    len_top_m = slab_area * (mesh_top_n * 2.0) * 1.06
    _, steel_top_kg = add_steel(mesh_top_dia, len_top_m, "الشبكة الأساسية العلوية (Top Mesh)")

    # 3. Top Extra Caps at Columns
    len_col_extra_m = 0.0
    steel_col_extra_kg = 0.0
    col_extra_dia_used = None
    for ce in col_extras:
        if ce.get("is_needed"):
            dia = ce["dia_extra"]
            col_extra_dia_used = dia
            l_ext = ce["n_extra"] * ce["L_extra"] * 1.06
            len_col_extra_m += l_ext
            _, w_k = add_steel(dia, l_ext, "كابات حديد إضافي علوي (Top Caps @ Columns)")
            steel_col_extra_kg += w_k

    # 4. Bottom Extra Steel in Enlarged / High-Moment Bays
    len_btm_extra_m = 0.0
    steel_btm_extra_kg = 0.0
    btm_extra_dia_used = None
    if btm_extra_spans:
        for be in btm_extra_spans:
            if isinstance(be, dict) and be.get("n_extra", 0) > 0:
                dia = be.get("dia_extra", 12)
                btm_extra_dia_used = dia
                l_ext = be["n_extra"] * be.get("L_extra", 4.0) * 1.06
                len_btm_extra_m += l_ext
                _, w_k = add_steel(dia, l_ext, "حديد إضافي سفلي بالباكيات (Bottom Extra in Bays)")
                steel_btm_extra_kg += w_k

    # 5. Cantilever Shawka extra steel
    len_cant_m = 0.0
    steel_cant_kg = 0.0
    cant_dia_used = None
    for cr in cant_rft_list:
        side_len = total_w if cr["side"] in ["bottom", "top"] else total_h
        n_tot = math.ceil(side_len * 6.0)
        l_cant = n_tot * cr["total_bar_length"] * 1.06
        len_cant_m += l_cant
        cant_dia_used = 12
        _, w_k = add_steel(12, l_cant, "تسليح الكوابيل والشوكة (Cantilever Shawka)")
        steel_cant_kg += w_k

    # 6. Perimeter U-loops and edge steel
    perimeter = 2.0 * (total_w + total_h)
    l_upins = perimeter * 5.0 * 0.8 * 1.06
    _, w_upins = add_steel(10, l_upins, "أرجل غلق ودبابيس الأطراف (Perimeter U-Pins)")
    l_edge_long = perimeter * 4.0 * 1.06
    _, w_edge_long = add_steel(12, l_edge_long, "حديد كمرات مدفونة بالأطراف (Edge Rebar)")
    len_edge_m = l_upins + l_edge_long
    steel_edge_kg = w_upins + w_edge_long

    total_steel_kg = sum(v["weight_kg"] for v in dia_dict.values())
    total_steel_ton = total_steel_kg / 1000.0
    total_steel_len_m = sum(v["length_m"] for v in dia_dict.values())
    steel_ratio = total_steel_kg / concrete_vol if concrete_vol > 0 else 0.0

    # Build Items List for Table 1
    items = [
        {
            "item_name": "الشبكة الأساسية السفلية (Bottom Base Mesh B1, B2)",
            "dia_str": f"Φ {mesh_btm_dia} mm",
            "dia_mm": mesh_btm_dia,
            "length_m": len_btm_m,
            "weight_kg": steel_btm_kg,
            "weight_ton": steel_btm_kg / 1000.0,
            "qty_str": f"{steel_btm_kg / 1000.0:.2f} Ton ({steel_btm_kg:,.0f} kg)",
            "length_str": f"{len_btm_m:,.1f} m'",
            "spec": f"{mesh_btm_n} Φ{mesh_btm_dia} / m' في الاتجاهين X & Y (فرش وغطاء سفلي)",
        },
        {
            "item_name": "الشبكة الأساسية العلوية (Top Base Mesh T1, T2)",
            "dia_str": f"Φ {mesh_top_dia} mm",
            "dia_mm": mesh_top_dia,
            "length_m": len_top_m,
            "weight_kg": steel_top_kg,
            "weight_ton": steel_top_kg / 1000.0,
            "qty_str": f"{steel_top_kg / 1000.0:.2f} Ton ({steel_top_kg:,.0f} kg)",
            "length_str": f"{len_top_m:,.1f} m'",
            "spec": f"{mesh_top_n} Φ{mesh_top_dia} / m' في الاتجاهين X & Y بكامل المسطح",
        },
        {
            "item_name": "كابات حديد إضافي علوي فوق الأعمدة (Additional Top Caps)",
            "dia_str": f"Φ {col_extra_dia_used or 12} mm" if steel_col_extra_kg > 0 else "—",
            "dia_mm": col_extra_dia_used if steel_col_extra_kg > 0 else None,
            "length_m": len_col_extra_m,
            "weight_kg": steel_col_extra_kg,
            "weight_ton": steel_col_extra_kg / 1000.0,
            "qty_str": f"{steel_col_extra_kg / 1000.0:.2f} Ton ({steel_col_extra_kg:,.0f} kg)" if steel_col_extra_kg > 0 else "0.00 Ton (الشبكة تكفي)",
            "length_str": f"{len_col_extra_m:,.1f} m'" if steel_col_extra_kg > 0 else "—",
            "spec": "حديد إضافي عالي المقاومة فوق رؤوس الأعمدة الحاملة للعزوم السالبة (-M)" if steel_col_extra_kg > 0 else "عزوم الأعمدة مغطاة بالكامل بالشبكة العلوية",
        },
        {
            "item_name": "حديد إضافي سفلي بالباكيات (Additional Bottom Steel in Bays)",
            "dia_str": f"Φ {btm_extra_dia_used or 12} mm" if steel_btm_extra_kg > 0 else "—",
            "dia_mm": btm_extra_dia_used if steel_btm_extra_kg > 0 else None,
            "length_m": len_btm_extra_m,
            "weight_kg": steel_btm_extra_kg,
            "weight_ton": steel_btm_extra_kg / 1000.0,
            "qty_str": f"{steel_btm_extra_kg / 1000.0:.2f} Ton ({steel_btm_extra_kg:,.0f} kg)" if steel_btm_extra_kg > 0 else "0.00 Ton (الشبكة تكفي)",
            "length_str": f"{len_btm_extra_m:,.1f} m'" if steel_btm_extra_kg > 0 else "—",
            "spec": "حديد إضافي سفلي بمنتصف البحور والباكيات المكبرة لتغطية عزوم (+M)" if steel_btm_extra_kg > 0 else "عزوم البحور مغطاة بالكامل بالشبكة السفلية",
        },
    ]

    if steel_cant_kg > 0:
        items.append({
            "item_name": "تسليح الكوابيل والشوكة (Cantilever Shawka & Secondary)",
            "dia_str": f"Φ {cant_dia_used or 12} mm",
            "dia_mm": cant_dia_used or 12,
            "length_m": len_cant_m,
            "weight_kg": steel_cant_kg,
            "weight_ton": steel_cant_kg / 1000.0,
            "qty_str": f"{steel_cant_kg / 1000.0:.2f} Ton ({steel_cant_kg:,.0f} kg)",
            "length_str": f"{len_cant_m:,.1f} m'",
            "spec": "شوك علوية رئيسية تمتد 1.5 طول الكابولي داخل البلاطة + ثانوي 5Φ10/m'",
        })

    items.append({
        "item_name": "حديد رجل الغلق ودبابيس الأطراف (Perimeter U-Pins & Edge Bars)",
        "dia_str": "Φ 10 & Φ 12 mm",
        "dia_mm": 10,
        "length_m": len_edge_m,
        "weight_kg": steel_edge_kg,
        "weight_ton": steel_edge_kg / 1000.0,
        "qty_str": f"{steel_edge_kg / 1000.0:.2f} Ton ({steel_edge_kg:,.0f} kg)",
        "length_str": f"{len_edge_m:,.1f} m'",
        "spec": "دبابيس U-Pins Φ10 كل 20 سم + 2Φ12 سفلي و 2Φ12 علوي على كامل المحيط",
    })

    items.append({
        "item_name": "الخرسانة المسلحة (Reinforced Concrete Volume)",
        "dia_str": "—",
        "dia_mm": None,
        "length_m": 0.0,
        "weight_kg": 0.0,
        "weight_ton": 0.0,
        "qty_str": f"{concrete_vol:.2f} m³",
        "length_str": "—",
        "spec": f"رتبة الخرسانة المسلحة Fcu = {ts_cm:.0f}cm slab (مسطح السقف = {slab_area:.1f} m²)",
    })

    # Build Table 2 (By Diameter Summary)
    by_dia_rows = []
    for dia in sorted(dia_dict.keys()):
        d_data = dia_dict[dia]
        w_k = d_data["weight_kg"]
        l_m = d_data["length_m"]
        pct = (w_k / total_steel_kg * 100.0) if total_steel_kg > 0 else 0.0
        apps_str = " + ".join(sorted(d_data["apps"]))
        by_dia_rows.append({
            "dia_mm": dia,
            "dia_str": f"Φ {dia} mm",
            "unit_w_kg_m": bar_unit_weight(dia),
            "length_m": l_m,
            "length_str": f"{l_m:,.1f} m'",
            "weight_kg": w_k,
            "weight_kg_str": f"{w_k:,.1f} kg",
            "weight_ton": w_k / 1000.0,
            "weight_ton_str": f"{w_k / 1000.0:.3f} Ton",
            "percent": pct,
            "percent_str": f"{pct:.1f} %",
            "apps": apps_str,
        })

    # ── Concrete Raw Materials Calculation (حساب مكونات الخرسانة المسلحة) ─────
    # Standard ECP 203 proportions: 1 m³ concrete = 0.8 m³ gravel + 0.4 m³ sand + 350 kg cement (7 bags) + 175 L water
    cement_content_kg_m3 = 350.0 if (fcu is None or fcu <= 250) else (400.0 if fcu >= 300 else 350.0)
    cement_kg = concrete_vol * cement_content_kg_m3
    cement_ton = cement_kg / 1000.0
    cement_bags = int(round(cement_kg / 50.0))
    gravel_m3 = concrete_vol * 0.80
    sand_m3 = concrete_vol * 0.40
    water_liters = concrete_vol * 175.0

    return {
        "slab_area_m2": slab_area,
        "concrete_vol_m3": concrete_vol,
        "cement_kg": cement_kg,
        "cement_ton": cement_ton,
        "cement_bags": cement_bags,
        "cement_content_kg_m3": cement_content_kg_m3,
        "gravel_m3": gravel_m3,
        "sand_m3": sand_m3,
        "water_liters": water_liters,
        "steel_btm_kg": steel_btm_kg,
        "steel_top_kg": steel_top_kg,
        "steel_col_extra_kg": steel_col_extra_kg,
        "steel_btm_extra_kg": steel_btm_extra_kg,
        "steel_cant_kg": steel_cant_kg,
        "steel_edge_kg": steel_edge_kg,
        "total_steel_kg": total_steel_kg,
        "total_steel_ton": total_steel_ton,
        "total_steel_len_m": total_steel_len_m,
        "steel_ratio_kg_m3": steel_ratio,
        "items": items,
        "by_dia": by_dia_rows,
    }



# ═══════════════════════════════════════════════════════════════════════════════
#  STREAMLIT RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    st.markdown(
        """
        <style>
        /* ═══════════════════════════════════════════════════════════════════════
           EXPANDER HEADERS (عناوين الأقسام المطوية / Collapsed Sections) - 18px BOLD with Background
           ═══════════════════════════════════════════════════════════════════════ */
        div[data-testid="stExpander"] details summary,
        div[data-testid="stExpander"] summary,
        .stExpander details summary,
        .stExpander summary,
        details summary,
        .streamlit-expanderHeader {
            background: #f1f5f9 !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            padding: 9px 16px !important;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04) !important;
            transition: background-color 0.2s ease, border-color 0.2s ease !important;
        }

        div[data-testid="stExpander"] details summary:hover,
        div[data-testid="stExpander"] summary:hover,
        .stExpander summary:hover {
            background: #e2e8f0 !important;
            border-color: #94a3b8 !important;
        }

        div[data-testid="stExpander"] details[open] > summary,
        div[data-testid="stExpander"] details[open] > summary:hover {
            border-bottom-left-radius: 0px !important;
            border-bottom-right-radius: 0px !important;
            border-bottom: 1px solid #cbd5e1 !important;
        }

        div[data-testid="stExpander"] details summary p,
        div[data-testid="stExpander"] details summary span,
        div[data-testid="stExpander"] details summary div,
        div[data-testid="stExpander"] summary p,
        div[data-testid="stExpander"] summary span,
        div[data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p,
        .streamlit-expanderHeader p,
        .streamlit-expanderHeader span {
            font-size: 18px !important;
            font-weight: 800 !important;
            line-height: 1.4 !important;
            color: #0f172a !important;
        }

        div[data-testid="stExpander"] details summary svg,
        div[data-testid="stExpander"] summary svg,
        .stExpander summary svg,
        details summary svg {
            width: 17px !important;
            height: 17px !important;
            min-width: 17px !important;
            fill: currentColor !important;
            stroke: currentColor !important;
            color: #1e40af !important;
        }

        /* Dark Mode Theme Adaptive Rules */
        @media (prefers-color-scheme: dark) {
            div[data-testid="stExpander"] details summary,
            div[data-testid="stExpander"] summary,
            .stExpander summary {
                background: #1e293b !important;
                border-color: #334155 !important;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.25) !important;
            }
            div[data-testid="stExpander"] details summary:hover,
            div[data-testid="stExpander"] summary:hover,
            .stExpander summary:hover {
                background: #334155 !important;
                border-color: #475569 !important;
            }
            div[data-testid="stExpander"] details[open] > summary {
                border-bottom-color: #334155 !important;
            }
            div[data-testid="stExpander"] summary p,
            div[data-testid="stExpander"] summary span,
            div[data-testid="stExpander"] summary * {
                color: #f8fafc !important;
            }
            div[data-testid="stExpander"] summary svg {
                color: #60a5fa !important;
            }
        }
        [data-theme="dark"] div[data-testid="stExpander"] summary,
        .stApp[data-theme="dark"] div[data-testid="stExpander"] summary {
            background: #1e293b !important;
            border-color: #334155 !important;
        }
        [data-theme="dark"] div[data-testid="stExpander"] summary:hover,
        .stApp[data-theme="dark"] div[data-testid="stExpander"] summary:hover {
            background: #334155 !important;
            border-color: #475569 !important;
        }
        [data-theme="dark"] div[data-testid="stExpander"] summary *,
        .stApp[data-theme="dark"] div[data-testid="stExpander"] summary * {
            color: #f8fafc !important;
        }
        [data-theme="dark"] div[data-testid="stExpander"] summary svg,
        .stApp[data-theme="dark"] div[data-testid="stExpander"] summary svg {
            color: #60a5fa !important;
        }
        [data-theme="light"] div[data-testid="stExpander"] summary,
        .stApp[data-theme="light"] div[data-testid="stExpander"] summary {
            background: #f1f5f9 !important;
            border-color: #cbd5e1 !important;
        }
        [data-theme="light"] div[data-testid="stExpander"] summary *,
        .stApp[data-theme="light"] div[data-testid="stExpander"] summary * {
            color: #0f172a !important;
        }
        [data-theme="light"] div[data-testid="stExpander"] summary svg,
        .stApp[data-theme="light"] div[data-testid="stExpander"] summary svg {
            color: #1e40af !important;
        }
        /* ═══════════════════════════════════════════════════════════════════════
           COMPACT VERTICAL LINE SPACING FOR INPUTS (Step 1 & Step 2)
           ═══════════════════════════════════════════════════════════════════════ */
        /* Reduce spacing between vertical blocks inside inputs */
        div[data-testid="stExpander"] details > div {
            padding-top: 6px !important;
            padding-bottom: 8px !important;
            padding-left: 12px !important;
            padding-right: 12px !important;
        }
        div[data-testid="stExpander"] [data-testid="stVerticalBlock"] {
            gap: 0.35rem !important;
        }
        /* Widget labels - remove excess top/bottom margins */
        div[data-testid="stExpander"] [data-testid="stWidgetLabel"] {
            margin-bottom: 1px !important;
            min-height: 0px !important;
        }
        div[data-testid="stExpander"] [data-testid="stWidgetLabel"] p,
        div[data-testid="stExpander"] [data-testid="stWidgetLabel"] label {
            margin-bottom: 0px !important;
            margin-top: 0px !important;
            line-height: 1.2 !important;
        }
        /* Markdown subheaders inside Step 1 and Step 2 */
        div[data-testid="stExpander"] details > div [data-testid="stMarkdownContainer"] p {
            margin-top: 3px !important;
            margin-bottom: 2px !important;
            line-height: 1.25 !important;
        }
        /* Widget containers */
        div[data-testid="stExpander"] .stNumberInput,
        div[data-testid="stExpander"] .stSelectbox,
        div[data-testid="stExpander"] .stTextInput {
            margin-bottom: 2px !important;
            margin-top: 0px !important;
        }
        /* Inputs and dropdowns compact height without changing font size */
        div[data-testid="stExpander"] div[data-baseweb="input"] input {
            min-height: 32px !important;
            padding-top: 3px !important;
            padding-bottom: 3px !important;
        }
        div[data-testid="stExpander"] div[data-baseweb="select"] {
            min-height: 32px !important;
        }
        div[data-testid="stExpander"] div[data-baseweb="select"] > div {
            min-height: 32px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
        }
        /* Stepper buttons */
        div[data-testid="stExpander"] button[data-testid="stNumberInputStepUp"],
        div[data-testid="stExpander"] button[data-testid="stNumberInputStepDown"] {
            min-height: 15px !important;
            height: 15px !important;
        }
        /* Section Header compact margin */
        .section-header {
            margin: 8px 0 6px 0 !important;
            padding: 6px 14px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-header">🟦 Module 1 – Flat Slab Design (ECP 203) (تصميم البلاطات اللاكمرية)</div>',
        unsafe_allow_html=True,
    )

    active_profile_name = S.get_active_profile_name()
    prefix = S.get_safe_profile_filename_prefix()

    Lx_spans = []
    Ly_spans = []
    cantilevers = {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0}

    # ── ① INPUTS MAIN HEADER & GEOMETRY INPUTS ───────────────────────────────
    st.markdown(
        """
        <div class="input-section-header">
            <span style="font-size: 26px;">📥</span>
            <span>مدخلات وأبعاد ومواصفات السقف والأحمال (Flat Slab Design & Geometry Inputs)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(f"📐 Step 1 — Grid Geometry & Cantilevers (اسم المشروع والمحاور والكوابيل) — [ {active_profile_name} ]", expanded=True):
        col_fs_pad1, col_fs_center, col_fs_pad2 = st.columns([0.6, 6.8, 0.6])
        with col_fs_center:
            cur_p_name = S.text_input(
                "اسم المشروع (Project Name)",
                "cs_project_name",
                help="يمكنك تعديل اسم المشروع وتغييره مباشرة لهذا المشروع المحفوظ.",
            )
            if cur_p_name and cur_p_name.strip() and cur_p_name.strip() != active_profile_name:
                if S.rename_project(active_profile_name, cur_p_name.strip()):
                    st.rerun()

        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            n_lx = S.integer_input(
                "Number of Lx spans (horizontal — between vertical axes)",
                "fs_n_lx",
                min_value=1, max_value=10,
            )
        with col_b:
            n_ly = S.integer_input(
                "Number of Ly spans (vertical — between horizontal axes)",
                "fs_n_ly",
                min_value=1, max_value=10,
            )

        st.markdown("**Lx spans — between vertical axes Y (m)**")
        lx_cols = st.columns(int(n_lx))
        Lx_spans = []
        for i, c in enumerate(lx_cols):
            with c:
                val = S.number_input(
                    f"Lx{i+1}",
                    f"fs_lx_{i}",
                    min_value=1.0, max_value=20.0, step=0.5,
                )
                Lx_spans.append(val)

        st.markdown("**Ly spans — between horizontal axes X (m)**")
        ly_cols = st.columns(int(n_ly))
        Ly_spans = []
        for j, c in enumerate(ly_cols):
            with c:
                val = S.number_input(
                    f"Ly{j+1}",
                    f"fs_ly_{j}",
                    min_value=1.0, max_value=20.0, step=0.5,
                )
                Ly_spans.append(val)

        st.markdown("**Cantilevers (m) — enter 0 if none**")
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            cant_left = S.number_input("Left", "fs_cant_left", min_value=0.0, max_value=5.0, step=0.25)
        with cc2:
            cant_right = S.number_input("Right", "fs_cant_right", min_value=0.0, max_value=5.0, step=0.25)
        with cc3:
            cant_bottom = S.number_input("Bottom", "fs_cant_bottom", min_value=0.0, max_value=5.0, step=0.25)
        with cc4:
            cant_top = S.number_input("Top", "fs_cant_top", min_value=0.0, max_value=5.0, step=0.25)

        cantilevers = dict(
            left=cant_left, right=cant_right,
            bottom=cant_bottom, top=cant_top,
        )

    # ── ② COLUMN, THICKNESS, LOADS, MATERIALS & REBAR OPTIONS ────────────────
    with st.expander("🧱 Step 2 — Slab Thickness, Column Size, Loads & Rebar (السُمك والأعمدة والأحمال والتسليح)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown("**🏛️ Column, Thickness & Floors**")
            bc_s = S.number_input("Col. Width bc (cm)", "slab_bc", min_value=None, step=5)
            tc_s = S.number_input("Col. Depth tc (cm)", "slab_tc", min_value=None, step=5)
            ts_initial = S.number_input("Initial Slab ts (cm)", "slab_ts_initial", min_value=12, max_value=80, step=1)
            n_floors = S.integer_input("No. of Floors (عدد الأدوار)", "slab_n_floors", min_value=1, max_value=100)

        with c2:
            st.markdown("**⚖️ Surface Loads (ton/m²)**")
            SDL       = S.number_input("Flooring / SDL", "slab_SDL", min_value=None, step=0.05)
            wall_load = S.number_input("Wall Load (WL)", "slab_wall_load", min_value=None, step=0.05)
            LL        = S.number_input("Live Load (LL)", "slab_LL", min_value=None, step=0.05)
            gamma_c   = S.number_input("γ_concrete (t/m³)", "slab_gamma_c", min_value=None, step=0.1)

        with c3:
            st.markdown("**🧪 Materials & Cover**")
            Fcu = S.number_input("Concrete Fcu (kg/cm²)", "slab_Fcu", min_value=None, step=25)
            Fy  = S.number_input("Steel Fy (kg/cm²)", "slab_Fy", min_value=None, step=200)
            cov = S.number_input("Concrete Cover (cm)", "slab_cover", min_value=0.5, max_value=5.0, step=0.5)

        with c4:
            st.markdown("**🔩 Rebar Diameters (Φ mm)**")
            bottom_mesh_dia = S.selectbox("Bottom Mesh Φ", "slab_bottom_mesh_dia_idx", options=BAR_DIA)
            n_btm_mesh_usr  = S.number_input(
                "عدد أسياخ الشبكة السفلية / م'  (Bottom Mesh n)",
                "slab_n_btm_mesh",
                min_value=4, max_value=30, step=1,
                help="عدد الأسياخ لكل متر طولي للشبكة الأساسية السفلية (B1, B2). الحد الأدنى الكودي يُحسب تلقائياً ويُطبَّق إذا كانت القيمة المدخلة أقل منه.",
            )
            top_mesh_dia    = S.selectbox("Top Mesh Φ",    "slab_top_mesh_dia_idx",    options=BAR_DIA)
            n_top_mesh_usr  = S.number_input(
                "عدد أسياخ الشبكة العلوية / م'  (Top Mesh n)",
                "slab_n_top_mesh",
                min_value=4, max_value=30, step=1,
                help="عدد الأسياخ لكل متر طولي للشبكة الأساسية العلوية (T1, T2).",
            )
            col_extra_dia   = S.selectbox("Col Extra Top Φ","slab_col_extra_dia_idx",  options=BAR_DIA)
            strip_top_extra_dia = S.selectbox("Strip Top Extra Φ", "slab_strip_top_extra_dia_idx", options=BAR_DIA)
            strip_bottom_extra_dia = S.selectbox("Strip Btm Extra Φ", "slab_strip_bottom_extra_dia_idx", options=BAR_DIA)

    # ── ③ INPUT VALIDATION ───────────────────────────────────────────────────
    errs = []
    if bc_s is None or bc_s <= 0:         errs.append(f"Column Width bc must be > 0 (got {bc_s}).")
    if tc_s is None or tc_s <= 0:         errs.append(f"Column Depth tc must be > 0 (got {tc_s}).")
    if ts_initial is None or ts_initial <= 0: errs.append(f"Initial Slab Thickness must be > 0 (got {ts_initial}).")
    if n_floors is None or n_floors < 1:  errs.append(f"Number of Floors must be ≥ 1 (got {n_floors}).")
    if SDL  is None or SDL  < 0:          errs.append(f"Super-Imposed DL must be ≥ 0 (got {SDL}).")
    if wall_load is None or wall_load < 0: errs.append(f"Wall Load must be ≥ 0 (got {wall_load}).")
    if LL   is None or LL   < 0:          errs.append(f"Live Load must be ≥ 0 (got {LL}).")
    if gamma_c is None or gamma_c <= 0:   errs.append(f"γ_concrete must be > 0 (got {gamma_c}).")
    if Fcu  is None or Fcu  <= 0:         errs.append(f"Fcu must be > 0 (got {Fcu}).")
    if Fy   is None or Fy   <= 0:         errs.append(f"Fy must be > 0 (got {Fy}).")
    if cov  is None or cov  <= 0:         errs.append(f"Cover must be > 0 (got {cov}).")
    if Fy is not None and Fcu is not None and Fy <= Fcu:
        errs.append(f"Fy ({Fy} kg/cm²) must be > Fcu ({Fcu} kg/cm²).")
    if any(lx <= 0 for lx in Lx_spans):   errs.append("All Lx spans must be > 0.")
    if any(ly <= 0 for ly in Ly_spans):   errs.append("All Ly spans must be > 0.")

    num_floors = int(n_floors) if n_floors and n_floors >= 1 else 1

    # ── ④ VERIFICATION SKETCH ────────────────────────────────────────────────
    # الحسابات دائماً تُنفَّذ (خارج الـ expander) لأن img_verif_b64 مطلوب لاحقاً
    _bc_col = bc_s if bc_s else 30
    _tc_col = tc_s if tc_s else 30



    # ── 5a. Geometry-change guard ────────────────────────────────────────────
    # If the user edits spans, the column & panel numbering changes → auto-reset pending.
    _geom_key = _geometry_key(Lx_spans, Ly_spans)
    if st.session_state.get("_fs_last_geom_key") != _geom_key:
        st.session_state["_fs_last_geom_key"]        = _geom_key
        st.session_state["_fs_pending_removals"]     = []
        st.session_state["_fs_pending_voids"]        = []
        st.session_state["_fs_show_confirm"]         = False
        st.session_state["_fs_show_void_confirm"]    = False
        st.session_state["_fs_pending_snapshot"]     = []
        st.session_state["_fs_pending_void_snapshot"] = []

    # ── 5b. Load confirmed column & void removals from persistent cfg ────────
    _confirmed_raw = S.cfg_val("fs_removed_cols", [])
    _confirmed_raw = _confirmed_raw if isinstance(_confirmed_raw, list) else []

    _confirmed_voids_raw = S.cfg_val("fs_void_panels", [])
    _confirmed_voids_raw = _confirmed_voids_raw if isinstance(_confirmed_voids_raw, list) else []

    # Generate all columns (original numbering) to validate persisted IDs
    _all_cols_ref, _, _, _, _ = get_flat_slab_columns(
        Lx_spans, Ly_spans, bc_cm=_bc_col, tc_cm=_tc_col
    )
    _valid_orig_ids = {c["orig_id"] for c in _all_cols_ref}
    _confirmed_removals = [cid for cid in _confirmed_raw if cid in _valid_orig_ids]
    if _confirmed_removals != _confirmed_raw:          # geometry changed → prune stale IDs
        S.cfg_set("fs_removed_cols", _confirmed_removals)

    # Generate all panels to validate persisted void IDs
    _all_panels_ref = get_flat_slab_panels(Lx_spans, Ly_spans)
    _valid_panel_ids = {p["id"] for p in _all_panels_ref}
    _confirmed_voids = [pid for pid in _confirmed_voids_raw if pid in _valid_panel_ids]
    if _confirmed_voids != _confirmed_voids_raw:        # geometry changed → prune stale IDs
        S.cfg_set("fs_void_panels", _confirmed_voids)

    _pending_removals = st.session_state.get("_fs_pending_removals", [])
    _pending_voids = st.session_state.get("_fs_pending_voids", [])

    # Panels registry with voids marked
    _all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _confirmed_voids)
    _active_panels = [p for p in _all_panels if not p["is_void"]]
    _void_panels = [p for p in _all_panels if p["is_void"]]

    # ── 5c. Build active columns with confirmed removals applied ─────────────
    _active_cols, _all_cols, _eff_Lx, _eff_Ly, _ddm_warn = get_flat_slab_columns(
        Lx_spans, Ly_spans, bc_cm=_bc_col, tc_cm=_tc_col,
        removed_ids=set(_confirmed_removals),
    )
    _active_orig_ids = {c["orig_id"] for c in _active_cols}  # IDs available for further removal

    # ── 5d. رسم مخطط التحقق الهندسي (مغلق بشكل افتراضي) ─────────────────────
    # حساب الصورة دائماً لأن img_verif_b64 مطلوب في التقرير لاحقاً
    _col_w_sk = _bc_col
    _col_d_sk = _tc_col
    _removed_col_objs_sk = [c for c in _all_cols if c["orig_id"] in set(_confirmed_removals)]

    fig_verif = generate_flat_slab_sketch(
        Lx_spans, Ly_spans, cantilevers,
        ts_initial=ts_initial if ts_initial is not None else 20,
        n_floors=num_floors,
        bottom_mesh_dia=bottom_mesh_dia if bottom_mesh_dia is not None else 12,
        bottom_mesh_n=int(n_btm_mesh_usr) if n_btm_mesh_usr else 5,
        top_mesh_dia=top_mesh_dia if top_mesh_dia is not None else 10,
        top_mesh_n=int(n_top_mesh_usr) if n_top_mesh_usr else 5,
        col_extra_dia=col_extra_dia if col_extra_dia is not None else 12,
        strip_top_extra_dia=strip_top_extra_dia if strip_top_extra_dia is not None else 12,
        strip_bottom_extra_dia=strip_bottom_extra_dia if strip_bottom_extra_dia is not None else 12,
        concrete_cover=cov if cov is not None else 1.5,
        fcu=Fcu if Fcu is not None else 250,
        fy=Fy if Fy is not None else 4000,
        live_load=LL if LL is not None else 0.25,
        flooring_load=SDL if SDL is not None else 0.15,
        wall_load=wall_load if wall_load is not None else 0.50,
        col_w_cm=_col_w_sk,
        col_d_cm=_col_d_sk,
        removed_col_ids=set(_confirmed_removals),
        pending_col_ids=set(st.session_state.get("_fs_pending_snapshot", [])
                            if st.session_state.get("_fs_show_confirm") else _pending_removals),
        void_panel_ids=set(_confirmed_voids),
        pending_void_ids=set(st.session_state.get("_fs_pending_void_snapshot", [])
                             if st.session_state.get("_fs_show_void_confirm") else _pending_voids),
    )
    buf_v = io.BytesIO()
    fig_verif.savefig(buf_v, format="png", bbox_inches="tight", dpi=300)
    buf_v.seek(0)
    img_verif_b64 = "data:image/png;base64," + base64.b64encode(buf_v.getvalue()).decode("utf-8")
    buf_v.seek(0)

    with st.expander(
        "🗺️ Structural Geometry Sketch & Verification (مخطط التحقق الهندسي وتوزيع المحاور والأعمدة)",
        expanded=True,
    ):
        st.markdown(
            '<div class="section-header">🗺️ Structural Geometry Sketch & Verification (مخطط التحقق الهندسي وتوزيع المحاور والأعمدة)</div>',
            unsafe_allow_html=True,
        )
        st.pyplot(fig_verif, use_container_width=True)
        st.download_button(
            label="📥 Download Structural Geometry Sketch (High-Res PNG)",
            data=buf_v,
            file_name=f"{prefix}Flat_Slab_Geometry_Verification.png",
            mime="image/png",
            use_container_width=True,
        )

        # ── ملخص الأبعاد ─────────────────────────────────────────────────────
        n_total_cols  = (len(Lx_spans) + 1) * (len(Ly_spans) + 1)
        n_active_cols = len(_active_cols)
        tot_w_val = sum(Lx_spans) + cant_left + cant_right
        tot_h_val = sum(Ly_spans) + cant_bottom + cant_top
        n_p_total  = len(_all_panels)
        n_p_active = len(_active_panels)
        n_p_voids  = len(_void_panels)
        p_val_str  = f"{n_p_active} active / {n_p_total} total" if not n_p_voids else f"{n_p_active} act / {n_p_voids} voids"

        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.markdown(f"""<div class="ecp-metric-box">
                <div class="ecp-metric-lbl">Total Width (X-dir)</div>
                <div class="ecp-metric-val">{tot_w_val:.2f} m</div></div>""",
                unsafe_allow_html=True)
        with g2:
            st.markdown(f"""<div class="ecp-metric-box">
                <div class="ecp-metric-lbl">Total Height (Y-dir)</div>
                <div class="ecp-metric-val">{tot_h_val:.2f} m</div></div>""",
                unsafe_allow_html=True)
        with g3:
            st.markdown(f"""<div class="ecp-metric-box">
                <div class="ecp-metric-lbl">No. of Columns</div>
                <div class="ecp-metric-val">{n_active_cols} active / {n_total_cols} total</div></div>""",
                unsafe_allow_html=True)
        with g4:
            st.markdown(f"""<div class="ecp-metric-box">
                <div class="ecp-metric-lbl">No. of Panels</div>
                <div class="ecp-metric-val">{p_val_str}</div></div>""",
                unsafe_allow_html=True)

    plt.close(fig_verif)

    # ── 5e. Column Removal Panel ─────────────────────────────────────────────

    with st.expander(
        f"🗑️ Column Removal & Re-indexing (تعديل وحذف الأعمدة وتحديث الترقيم) "
        f"{'— ' + str(len(_confirmed_removals)) + ' columns removed' if _confirmed_removals else ''}",
        expanded=bool(st.session_state.get("_fs_show_confirm", False)),
    ):
        st.markdown(
            """
            <div style='background:#fffbeb;border-left:4px solid #f59e0b;padding:10px 14px;
                        border-radius:6px;margin-bottom:10px;'>
            <b>📋 يرجى مراجعة مخطط الأعمدة أعلاه.</b><br>
            حدّد الأعمدة التي تريد حذفها من الشبكة الإنشائية (بأرقامها الأصلية).<br>
            بعد التأكيد: سيُعاد رسم المخطط وترقيم الأعمدة وإعادة جميع حسابات التصميم تلقائياً.
            </div>
            """,
            unsafe_allow_html=True,
        )

        _all_orig_sorted = sorted(_valid_orig_ids, key=lambda c: int(c[1:]))
        _options_for_removal = [
            cid for cid in _all_orig_sorted if cid not in _confirmed_removals
        ]
        _options_labels = {
            cid: f"{cid} ({next((c['type'] for c in _all_cols if c['orig_id']==cid), '?')})"
            for cid in _options_for_removal
        }

        # ── Persistent confirm-mode flag ──────────────────────────────────────
        _show_confirm = st.session_state.get("_fs_show_confirm", False)

        if not _show_confirm:
            # ── Selection mode ────────────────────────────────────────────────
            _selected = st.multiselect(
                "🔍 Select columns to remove (اختر الأعمدة للحذف):",
                options=_options_for_removal,
                default=[p for p in _pending_removals if p in _options_for_removal],
                format_func=lambda cid: _options_labels.get(cid, cid),
                key="_fs_col_select_widget",
                help="يمكنك اختيار أي عمود بغض النظر عن موقعه (داخلي، حافّي، زاوية).",
            )
            st.session_state["_fs_pending_removals"] = _selected

            _btn_col, _ = st.columns([1, 2])
            with _btn_col:
                if st.button(
                    "🔍 Review & Confirm Removal",
                    key="_fs_btn_review",
                    use_container_width=True,
                    disabled=not _selected,
                ):
                    st.session_state["_fs_show_confirm"]     = True
                    st.session_state["_fs_pending_snapshot"] = list(_selected)
                    st.rerun()

        else:
            # ── Confirmation gate (persistent across re-renders) ──────────────
            _snapshot = st.session_state.get("_fs_pending_snapshot", [])

            st.warning(
                "⚠️ **Pending Removal Confirmation**\n\n"
                "سيتم حذف الأعمدة التالية نهائياً من النموذج الإنشائي:\n\n"
                + "\n".join(
                    f"- **{cid}** ({next((c['type'] for c in _all_cols if c['orig_id']==cid), '?')})"
                    for cid in sorted(_snapshot, key=lambda c: int(c[1:]))
                )
            )

            if _snapshot:
                _trial_removed = set(_confirmed_removals) | set(_snapshot)
                _, _, _trial_Lx, _trial_Ly, _trial_warn = get_flat_slab_columns(
                    Lx_spans, Ly_spans, bc_cm=_bc_col, tc_cm=_tc_col,
                    removed_ids=_trial_removed,
                )
                if _trial_Lx and _trial_Ly:
                    st.info(
                        f"📐 **Effective spans after removal:**  "
                        f"Lx = [{', '.join(f'{v:.2f}m' for v in _trial_Lx)}]  |  "
                        f"Ly = [{', '.join(f'{v:.2f}m' for v in _trial_Ly)}]"
                    )
                if _trial_warn:
                    st.warning(_trial_warn)

            _conf_a, _conf_b, _ = st.columns([1, 1, 2])
            with _conf_a:
                if st.button("✅ Yes — Confirm & Redesign",
                             key="_fs_btn_yes", use_container_width=True):
                    _new_confirmed = list(set(_confirmed_removals) | set(_snapshot))
                    st.session_state.setdefault("cfg", {})["fs_removed_cols"] = _new_confirmed
                    S.save_settings()
                    st.session_state["_fs_pending_removals"] = []
                    st.session_state["_fs_pending_snapshot"] = []
                    st.session_state["_fs_show_confirm"]     = False
                    st.rerun()
            with _conf_b:
                if st.button("↩️ Cancel", key="_fs_btn_cancel", use_container_width=True):
                    st.session_state["_fs_pending_removals"] = []
                    st.session_state["_fs_pending_snapshot"] = []
                    st.session_state["_fs_show_confirm"]     = False
                    st.rerun()

        # ── Restore section ───────────────────────────────────────────────────
        if _confirmed_removals:
            st.markdown("---")
            st.markdown("**🔄 Restore Removed Columns (استعادة أعمدة محذوفة):**")
            _removed_labels = {
                cid: f"{cid} (originally {next((c['type'] for c in _all_cols if c['orig_id']==cid), '?')})"
                for cid in sorted(_confirmed_removals, key=lambda c: int(c[1:]))
            }
            _to_restore = st.multiselect(
                "Choose columns to restore (اختر الأعمدة لاستعادتها):",
                options=sorted(_confirmed_removals, key=lambda c: int(c[1:])),
                format_func=lambda cid: _removed_labels.get(cid, cid),
                key="_fs_restore_widget",
            )
            _rst_a, _ = st.columns([1, 3])
            with _rst_a:
                if st.button("♻️ Restore Selected", key="_fs_btn_restore",
                             use_container_width=True, disabled=not _to_restore):
                    _new_confirmed = [c for c in _confirmed_removals if c not in _to_restore]
                    st.session_state.setdefault("cfg", {})["fs_removed_cols"] = _new_confirmed
                    S.save_settings()
                    st.session_state["_fs_pending_removals"] = []
                    st.session_state["_fs_show_confirm"]     = False
                    st.rerun()

            st.markdown("---")
            _del_a, _ = st.columns([1, 3])
            with _del_a:
                if st.button(
                    "🗑️ Reset — Restore ALL Columns",
                    key="_fs_btn_clear_all", use_container_width=True,
                    help="Restore all removed columns and return to full grid.",
                ):
                    st.session_state.setdefault("cfg", {})["fs_removed_cols"] = []
                    S.save_settings()
                    st.session_state["_fs_pending_removals"] = []
                    st.session_state["_fs_show_confirm"]     = False
                    st.rerun()

    # ── 5f. Panel / Void Removal Expander ─────────────────────────────────────
    with st.expander(
        f"🕳️ Panel Removal & Openings (تعديل وحذف البلاطات — إنشاء مناور وفراغات معمارية / Voids) "
        f"{'— ' + str(len(_confirmed_voids)) + ' voids created' if _confirmed_voids else ''}",
        expanded=bool(st.session_state.get("_fs_show_void_confirm", False)),
    ):
        st.markdown(
            """
            <div style='background:#fffbeb;border-left:4px solid #f59e0b;padding:10px 14px;
                        border-radius:6px;margin-bottom:10px;'>
            <b>📋 يرجى مراجعة مخطط البلاطات أعلاه.</b><br>
            حدّد البلاطات المحصورة بين المحاور التي تريد حذفها لإنشاء مناور وفراغات معمارية (Voids).<br>
            بعد التأكيد: سيتم تلوين البلاطات باللون الرصاصي وعمل علامة X وحذف كمياتها وتعديل أحمال الأعمدة المحيطة بها تلقائياً.
            </div>
            """,
            unsafe_allow_html=True,
        )

        _options_for_voids = [p["id"] for p in _all_panels if p["id"] not in _confirmed_voids]
        _void_labels = {
            p["id"]: f"{p['name']} [{p['grid_x']} × {p['grid_y']}] ({p['Lx']:.2f}m × {p['Ly']:.2f}m — {p['area']:.1f} m²)"
            for p in _all_panels
        }

        _show_void_confirm = st.session_state.get("_fs_show_void_confirm", False)

        if not _show_void_confirm:
            _selected_voids = st.multiselect(
                "🔍 Select panels to remove / make into voids (اختر البلاطات لإنشاء مناور):",
                options=_options_for_voids,
                default=[p for p in _pending_voids if p in _options_for_voids],
                format_func=lambda pid: _void_labels.get(pid, pid),
                key="_fs_void_select_widget",
                help="اختر البلاطة المحددة بمحاورها لتحويلها إلى منور.",
            )
            st.session_state["_fs_pending_voids"] = _selected_voids

            _btn_v_col, _ = st.columns([1, 2])
            with _btn_v_col:
                if st.button(
                    "🔍 Review & Confirm Void Removal",
                    key="_fs_btn_void_review",
                    use_container_width=True,
                    disabled=not _selected_voids,
                ):
                    st.session_state["_fs_show_void_confirm"]     = True
                    st.session_state["_fs_pending_void_snapshot"] = list(_selected_voids)
                    st.rerun()

        else:
            _void_snapshot = st.session_state.get("_fs_pending_void_snapshot", [])
            _snap_panels = [p for p in _all_panels if p["id"] in _void_snapshot]
            _tot_vd_area = sum(p["area"] for p in _snap_panels)

            st.warning(
                "⚠️ **Pending Void Creation Confirmation**\n\n"
                f"سيتم تفريغ البلاطات التالية كـ **مناور معمارية (Voids)** بمساحة إجمالية **{_tot_vd_area:.2f} m²**:\n\n"
                + "\n".join(
                    f"- **{_void_labels.get(pid, pid)}**"
                    for pid in _void_snapshot
                )
            )

            _conf_v_a, _conf_v_b, _ = st.columns([1, 1, 2])
            with _conf_v_a:
                if st.button("✅ Yes — Confirm Voids & Redesign",
                             key="_fs_btn_void_yes", use_container_width=True):
                    _new_confirmed_voids = list(set(_confirmed_voids) | set(_void_snapshot))
                    st.session_state.setdefault("cfg", {})["fs_void_panels"] = _new_confirmed_voids
                    S.save_settings()
                    st.session_state["_fs_pending_voids"] = []
                    st.session_state["_fs_pending_void_snapshot"] = []
                    st.session_state["_fs_show_void_confirm"] = False
                    st.rerun()
            with _conf_v_b:
                if st.button("↩️ Cancel", key="_fs_btn_void_cancel", use_container_width=True):
                    st.session_state["_fs_pending_voids"] = []
                    st.session_state["_fs_pending_void_snapshot"] = []
                    st.session_state["_fs_show_void_confirm"] = False
                    st.rerun()

        # ── Restore Voids Section ─────────────────────────────────────────────
        if _confirmed_voids:
            st.markdown("---")
            st.markdown("**🔄 Restore Removed Panels (استعادة البلاطات وإلغاء المناور):**")
            _to_restore_voids = st.multiselect(
                "Choose panels to restore (اختر البلاطات لاستعادتها كخرسانة مسلحة):",
                options=_confirmed_voids,
                format_func=lambda pid: _void_labels.get(pid, pid),
                key="_fs_restore_void_widget",
            )
            _rst_v_a, _ = st.columns([1, 3])
            with _rst_v_a:
                if st.button("♻️ Restore Selected Panels", key="_fs_btn_restore_voids",
                             use_container_width=True, disabled=not _to_restore_voids):
                    _new_confirmed_voids = [p for p in _confirmed_voids if p not in _to_restore_voids]
                    st.session_state.setdefault("cfg", {})["fs_void_panels"] = _new_confirmed_voids
                    S.save_settings()
                    st.session_state["_fs_pending_voids"] = []
                    st.session_state["_fs_show_void_confirm"] = False
                    st.rerun()

            st.markdown("---")
            _del_v_a, _ = st.columns([1, 3])
            with _del_v_a:
                if st.button(
                    "🗑️ Reset — Restore ALL Panels (إلغاء جميع المناور)",
                    key="_fs_btn_clear_all_voids", use_container_width=True,
                    help="Restore all removed panels and return to full solid slab.",
                ):
                    st.session_state.setdefault("cfg", {})["fs_void_panels"] = []
                    S.save_settings()
                    st.session_state["_fs_pending_voids"] = []
                    st.session_state["_fs_show_void_confirm"] = False
                    st.rerun()

    # ── Columns Registry Table (reflects active columns after removal) ────────
    _registry_df = pd.DataFrame([
        {
            "New ID": c["id"],
            "Orig ID": c["orig_id"],
            "Grid": f"{c['grid_x']} - {c['grid_y']}",
            "Type": c["type"],
            "x (m)": round(c["x"], 3),
            "y (m)": round(c["y"], 3),
        }
        for c in _active_cols
    ])
    with st.expander(
        f"🏛️ Columns Labeling & Grid Registry (سجل وجدول إحداثيات ونماذج الأعمدة) "
        f"({len(_active_cols)} active columns — "
        f"{len(_confirmed_removals)} removed)",
        expanded=False,
    ):
        render_styled_table(_registry_df)
        if _confirmed_removals:
            st.info(
                f"🔴 **Removed columns (original IDs):** "
                + ", ".join(sorted(_confirmed_removals, key=lambda c: int(c[1:])))
            )
        st.caption("ℹ️ New IDs reflect re-indexing after removal. Ordered left→right (Y axes), bottom→top (X axes).")

    if errs:
        st.error("⚠️ **Illogical Input Detected — Calculation Stopped.**")
        for e in errs:
            st.warning(f"• {e}")
        return

    if not _active_cols:
        st.error("❌ No active columns remain — please restore at least one column to proceed with design.")
        return

    # ═════════════════════════════════════════════════════════════════════════
    #  DESIGN CALCULATIONS (accounting for column & void removals)
    # ═════════════════════════════════════════════════════════════════════════

    # Effective spans (merged where full axis was removed)
    Lx_calc = _eff_Lx if _eff_Lx else list(Lx_spans)
    Ly_calc = _eff_Ly if _eff_Ly else list(Ly_spans)
    col_list = _active_cols   # active re-indexed columns

    # DDM warning (span ratio > 1.33)
    if _ddm_warn:
        st.warning(_ddm_warn)

    bc_m = bc_s / 100.0
    tc_m = tc_s / 100.0

    ts = float(ts_initial) if ts_initial is not None else 20.0
    WL      = wall_load if wall_load is not None else 0.0
    SW      = gamma_c * (ts / 100.0)
    DL_tot  = SW + SDL + WL
    Wu      = 1.4 * DL_tot + 1.6 * LL

    avg_rebar_dia = (bottom_mesh_dia / 10.0)
    d = ts - cov - (avg_rebar_dia / 2.0)

    As_min_req_m   = 0.0018 * 100.0 * ts
    n_mesh_btm_min = max(5, math.ceil(As_min_req_m / bar_area(bottom_mesh_dia)))

    # ── الشبكة السفلية: أخذ قيمة المستخدم مع تطبيق الحد الأدنى الكودي ─────────
    _n_btm_usr = int(n_btm_mesh_usr) if n_btm_mesh_usr else n_mesh_btm_min
    if _n_btm_usr < n_mesh_btm_min:
        st.warning(
            f"⚠️ عدد أسياخ الشبكة السفلية المدخل ({_n_btm_usr} Φ{bottom_mesh_dia}) "
            f"أقل من الحد الأدنى الكودي (ECP 203: ρ_min = 0.18%) "
            f"— سيُطبَّق الحد الأدنى تلقائياً: **{n_mesh_btm_min} Φ{bottom_mesh_dia} / m'**"
        )
    n_mesh_btm = max(_n_btm_usr, n_mesh_btm_min)

    prov_btm_mesh_cm2m = n_mesh_btm * bar_area(bottom_mesh_dia)
    mesh_btm_str = f"{n_mesh_btm} Φ{bottom_mesh_dia} / m'"

    # ── الشبكة العلوية: قيمة المستخدم مباشرة ────────────────────────────────────
    n_mesh_top = int(n_top_mesh_usr) if n_top_mesh_usr else 5
    prov_top_mesh_cm2m = n_mesh_top * bar_area(top_mesh_dia)
    mesh_top_str = f"{n_mesh_top} Φ{top_mesh_dia} / m'"

    # ── Load Redistribution & Tributary Calculation (with Void Deductions) ───
    cant_L = cantilevers.get("left", 0.0)
    cant_R = cantilevers.get("right", 0.0)
    cant_B = cantilevers.get("bottom", 0.0)
    cant_T = cantilevers.get("top", 0.0)

    nx_sp = len(Lx_spans)
    ny_sp = len(Ly_spans)
    void_set = set(_confirmed_voids)

    # Calculate exact tributary area for each column by summing its 4 surrounding quadrants (excluding void openings)
    for c in _all_cols:
        i, j = c["i"], c["j"]
        col_atrib = 0.0

        # Quadrant 1: Bottom-Left (panel i-1, j-1)
        if i > 0 and j > 0:
            if f"P_{i}_{j}" not in void_set:
                col_atrib += (Lx_spans[i-1] / 2.0) * (Ly_spans[j-1] / 2.0)
        elif i == 0 and j > 0:
            col_atrib += cant_L * (Ly_spans[j-1] / 2.0)
        elif i > 0 and j == 0:
            col_atrib += (Lx_spans[i-1] / 2.0) * cant_B
        elif i == 0 and j == 0:
            col_atrib += cant_L * cant_B

        # Quadrant 2: Bottom-Right (panel i, j-1)
        if i < nx_sp and j > 0:
            if f"P_{i+1}_{j}" not in void_set:
                col_atrib += (Lx_spans[i] / 2.0) * (Ly_spans[j-1] / 2.0)
        elif i == nx_sp and j > 0:
            col_atrib += cant_R * (Ly_spans[j-1] / 2.0)
        elif i < nx_sp and j == 0:
            col_atrib += (Lx_spans[i] / 2.0) * cant_B
        elif i == nx_sp and j == 0:
            col_atrib += cant_R * cant_B

        # Quadrant 3: Top-Left (panel i-1, j)
        if i > 0 and j < ny_sp:
            if f"P_{i}_{j+1}" not in void_set:
                col_atrib += (Lx_spans[i-1] / 2.0) * (Ly_spans[j] / 2.0)
        elif i == 0 and j < ny_sp:
            col_atrib += cant_L * (Ly_spans[j] / 2.0)
        elif i > 0 and j == ny_sp:
            col_atrib += (Lx_spans[i-1] / 2.0) * cant_T
        elif i == 0 and j == ny_sp:
            col_atrib += cant_L * cant_T

        # Quadrant 4: Top-Right (panel i, j)
        if i < nx_sp and j < ny_sp:
            if f"P_{i+1}_{j+1}" not in void_set:
                col_atrib += (Lx_spans[i] / 2.0) * (Ly_spans[j] / 2.0)
        elif i == nx_sp and j < ny_sp:
            col_atrib += cant_R * (Ly_spans[j] / 2.0)
        elif i < nx_sp and j == ny_sp:
            col_atrib += (Lx_spans[i] / 2.0) * cant_T
        elif i == nx_sp and j == ny_sp:
            col_atrib += cant_R * cant_T

        c["Atrib_0"] = max(0.0, col_atrib)
        c["Pu_0"] = Wu * c["Atrib_0"]
        c["Pu"] = c["Pu_0"]

    # If columns were removed, transfer their load to surviving active columns
    _removed_col_objs = [c for c in _all_cols if c.get("removed")]
    if _removed_col_objs and _active_cols:
        for rcol in _removed_col_objs:
            rx, ry = rcol["x"], rcol["y"]
            r_load = rcol["Pu_0"]
            if r_load > 0:
                dists = [math.hypot(c["x"] - rx, c["y"] - ry) for c in _active_cols]
                weights = [1.0 / (dist + 0.1) for dist in dists]
                tot_w = sum(weights)
                for idx, c in enumerate(_active_cols):
                    c["Pu"] += (weights[idx] / tot_w) * r_load

    # ── Multi-Bay & Merged-Bay Moments Analysis (X & Y) ──────────────────────
    btm_extra_spans = []
    enlarged_bays_info = []
    all_Ln = []

    x_coords = [0.0]
    for lx in Lx_spans:
        x_coords.append(x_coords[-1] + lx)
    y_coords = [0.0]
    for ly in Ly_spans:
        y_coords.append(y_coords[-1] + ly)

    n_xi = len(x_coords)
    n_yj = len(y_coords)

    # 1. Standard DDM span rows for X direction
    Ly_avg = sum(Ly_calc) / len(Ly_calc)
    Lx_avg = sum(Lx_calc) / len(Lx_calc)
    Ln_x_all = [lx - bc_m for lx in Lx_calc]
    Ln_y_all = [ly - tc_m for ly in Ly_calc]

    rows_x = []
    for i, lx in enumerate(Lx_calc):
        is_ext = (i == 0) or (i == len(Lx_calc) - 1)
        L_perp = Ly_avg
        Ln     = Ln_x_all[i]
        all_Ln.append(Ln)
        m      = ddm_moments(Wu, L_perp, Ln, is_ext)
        cs_w   = min(lx, L_perp) / 2.0
        ms_w   = max(0.1, L_perp - cs_w)

        rows_x.append(dict(
            span_label = f"Lx{i+1} = {lx:.2f} m",
            span_type  = "Exterior" if is_ext else "Interior",
            Ln         = Ln,
            Mo         = m["Mo"],
            M_neg_ext  = m["M_neg_ext"],
            M_pos      = m["M_pos"],
            M_neg_int  = m["M_neg_int"],
            cs_w       = cs_w,
            ms_w       = ms_w,
            cs_neg_ext = m["cs_neg_ext"],
            cs_pos     = m["cs_pos"],
            cs_neg_int = m["cs_neg_int"],
            ms_neg_ext = m["ms_neg_ext"],
            ms_pos     = m["ms_pos"],
            ms_neg_int = m["ms_neg_int"],
            As_cs_neg_ext = calc_As(m["cs_neg_ext"], cs_w, d, Fcu, Fy, ts),
            As_cs_pos     = calc_As(m["cs_pos"],     cs_w, d, Fcu, Fy, ts),
            As_cs_neg_int = calc_As(m["cs_neg_int"], cs_w, d, Fcu, Fy, ts),
            As_ms_neg_ext = calc_As(m["ms_neg_ext"], ms_w, d, Fcu, Fy, ts),
            As_ms_pos     = calc_As(m["ms_pos"],     ms_w, d, Fcu, Fy, ts),
            As_ms_neg_int = calc_As(m["ms_neg_int"], ms_w, d, Fcu, Fy, ts),
        ))

    # 2. Standard DDM span rows for Y direction
    rows_y = []
    for j, ly in enumerate(Ly_calc):
        is_ext = (j == 0) or (j == len(Ly_calc) - 1)
        L_perp = Lx_avg
        Ln     = Ln_y_all[j]
        all_Ln.append(Ln)
        m      = ddm_moments(Wu, L_perp, Ln, is_ext)
        cs_w   = min(ly, L_perp) / 2.0
        ms_w   = max(0.1, L_perp - cs_w)

        rows_y.append(dict(
            span_label = f"Ly{j+1} = {ly:.2f} m",
            span_type  = "Exterior" if is_ext else "Interior",
            Ln         = Ln,
            Mo         = m["Mo"],
            M_neg_ext  = m["M_neg_ext"],
            M_pos      = m["M_pos"],
            M_neg_int  = m["M_neg_int"],
            cs_w       = cs_w,
            ms_w       = ms_w,
            cs_neg_ext = m["cs_neg_ext"],
            cs_pos     = m["cs_pos"],
            cs_neg_int = m["cs_neg_int"],
            ms_neg_ext = m["ms_neg_ext"],
            ms_pos     = m["ms_pos"],
            ms_neg_int = m["ms_neg_int"],
            As_cs_neg_ext = calc_As(m["cs_neg_ext"], cs_w, d, Fcu, Fy, ts),
            As_cs_pos     = calc_As(m["cs_pos"],     cs_w, d, Fcu, Fy, ts),
            As_cs_neg_int = calc_As(m["cs_neg_int"], cs_w, d, Fcu, Fy, ts),
            As_ms_neg_ext = calc_As(m["ms_neg_ext"], ms_w, d, Fcu, Fy, ts),
            As_ms_pos     = calc_As(m["ms_pos"],     ms_w, d, Fcu, Fy, ts),
            As_ms_neg_int = calc_As(m["ms_neg_int"], ms_w, d, Fcu, Fy, ts),
        ))

    # 3. Detect and calculate Bottom Extra Steel per Panel Bay (بين المحاور داخل كل باكية)
    rem_coords_set = {(c["x"], c["y"]) for c in (_removed_col_objs or [])}
    all_panels_x_design = []
    all_panels_y_design = []

    for j in range(len(Ly_calc)):
        for i in range(len(Lx_calc)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _confirmed_voids:
                continue

            x_l, x_r = x_coords[i], x_coords[i+1]
            y_b, y_t = y_coords[j], y_coords[j+1]
            span_lx = Lx_calc[i]
            span_ly = Ly_calc[j]
            cx = (x_l + x_r) / 2.0
            cy = (y_b + y_t) / 2.0

            Ln_x = max(0.5, span_lx - bc_m)
            Ln_y = max(0.5, span_ly - tc_m)
            all_Ln.extend([Ln_x, Ln_y])

            # Check if this panel borders any removed column (enlarged bay)
            is_enlarged = bool(rem_coords_set.intersection({(x_l, y_b), (x_r, y_b), (x_l, y_t), (x_r, y_t)}))

            # X-direction Bending
            Mo_x = Wu * span_ly * (Ln_x ** 2) / 8.0
            M_pos_x = (0.50 if is_enlarged else 0.35) * Mo_x
            w_cs_x = min(span_lx, span_ly) / 2.0
            M_cs_x = 0.60 * M_pos_x
            As_cs_req_x = calc_As(M_cs_x, w_cs_x, d, Fcu, Fy, ts)
            As_cs_m_x = As_cs_req_x / w_cs_x
            delta_As_cs_x = max(0.0, As_cs_m_x - prov_btm_mesh_cm2m)

            ms_w_x = max(0.1, span_ly - w_cs_x)
            M_ms_x = 0.40 * M_pos_x
            As_ms_req_x = calc_As(M_ms_x, ms_w_x, d, Fcu, Fy, ts)
            As_ms_m_x = As_ms_req_x / ms_w_x
            delta_As_ms_x = max(0.0, As_ms_m_x - prov_btm_mesh_cm2m)
            delta_As_x = max(delta_As_cs_x, delta_As_ms_x)

            # Y-direction Bending
            Mo_y = Wu * span_lx * (Ln_y ** 2) / 8.0
            M_pos_y = (0.50 if is_enlarged else 0.35) * Mo_y
            w_cs_y = min(span_lx, span_ly) / 2.0
            M_cs_y = 0.60 * M_pos_y
            As_cs_req_y = calc_As(M_cs_y, w_cs_y, d, Fcu, Fy, ts)
            As_cs_m_y = As_cs_req_y / w_cs_y
            delta_As_cs_y = max(0.0, As_cs_m_y - prov_btm_mesh_cm2m)

            ms_w_y = max(0.1, span_lx - w_cs_y)
            M_ms_y = 0.40 * M_pos_y
            As_ms_req_y = calc_As(M_ms_y, ms_w_y, d, Fcu, Fy, ts)
            As_ms_m_y = As_ms_req_y / ms_w_y
            delta_As_ms_y = max(0.0, As_ms_m_y - prov_btm_mesh_cm2m)
            delta_As_y = max(delta_As_cs_y, delta_As_ms_y)

            # X-direction Bottom Extra Check & Record
            a_bar = bar_area(strip_bottom_extra_dia)
            n_b_x = max(2, math.ceil((delta_As_x * span_ly) / a_bar))
            L_ext_x = round(0.70 * span_lx, 2)
            req_extra_x = (delta_As_x > 0.05 or (is_enlarged and span_lx >= span_ly))
            is_ext_x = (i == 0) or (i == len(Lx_calc) - 1)
            span_type_x = "باكية مكبرة (Enlarged)" if is_enlarged else ("بحر طرفي (Exterior)" if is_ext_x else "بحر داخلي (Interior)")

            item_x = {
                "panel_id": pid,
                "bay_label": f"Bay X{i+1}-X{i+2} / Y{j+1}-Y{j+2}",
                "span_type": span_type_x,
                "dir": "X",
                "span_len": span_lx,
                "Ln": Ln_x,
                "W_bay": span_ly,
                "cx": cx,
                "cy": cy,
                "Mo": Mo_x,
                "M_pos": M_pos_x,
                "As_req_m": max(As_cs_m_x, As_ms_m_x),
                "As_prov_m": prov_btm_mesh_cm2m,
                "delta_As": delta_As_x,
                "n_extra": n_b_x if req_extra_x else 0,
                "dia_extra": strip_bottom_extra_dia,
                "L_extra": L_ext_x if req_extra_x else 0.0,
                "is_enlarged": is_enlarged,
                "is_needed": req_extra_x,
                "callout": f"+{n_b_x} Φ{strip_bottom_extra_dia} (X-Dir, L={L_ext_x}m)" if req_extra_x else f"الشبكة الأساسية ({mesh_btm_str}) كافية ومغطية بالكامل ✅",
                "L_cut": f"{L_ext_x:.2f} m" if req_extra_x else "—",
            }
            all_panels_x_design.append(item_x)
            if req_extra_x:
                btm_extra_spans.append(item_x)
                if is_enlarged:
                    enlarged_bays_info.append(item_x)

            # Y-direction Bottom Extra Check & Record
            n_b_y = max(2, math.ceil((delta_As_y * span_lx) / a_bar))
            L_ext_y = round(0.70 * span_ly, 2)
            req_extra_y = (delta_As_y > 0.05 or (is_enlarged and span_ly > span_lx))
            is_ext_y = (j == 0) or (j == len(Ly_calc) - 1)
            span_type_y = "باكية مكبرة (Enlarged)" if is_enlarged else ("بحر طرفي (Exterior)" if is_ext_y else "بحر داخلي (Interior)")

            item_y = {
                "panel_id": pid,
                "bay_label": f"Bay Y{j+1}-Y{j+2} / X{i+1}-X{i+2}",
                "span_type": span_type_y,
                "dir": "Y",
                "span_len": span_ly,
                "Ln": Ln_y,
                "W_bay": span_lx,
                "cx": cx,
                "cy": cy,
                "Mo": Mo_y,
                "M_pos": M_pos_y,
                "As_req_m": max(As_cs_m_y, As_ms_m_y),
                "As_prov_m": prov_btm_mesh_cm2m,
                "delta_As": delta_As_y,
                "n_extra": n_b_y if req_extra_y else 0,
                "dia_extra": strip_bottom_extra_dia,
                "L_extra": L_ext_y if req_extra_y else 0.0,
                "is_enlarged": is_enlarged,
                "is_needed": req_extra_y,
                "callout": f"+{n_b_y} Φ{strip_bottom_extra_dia} (Y-Dir, L={L_ext_y}m)" if req_extra_y else f"الشبكة الأساسية ({mesh_btm_str}) كافية ومغطية بالكامل ✅",
                "L_cut": f"{L_ext_y:.2f} m" if req_extra_y else "—",
            }
            all_panels_y_design.append(item_y)
            if req_extra_y:
                btm_extra_spans.append(item_y)
                if is_enlarged and (not req_extra_x):
                    enlarged_bays_info.append(item_y)


    # Global max clear span & code minimum thickness
    Ln_max = max(all_Ln) if all_Ln else max(max(Ln_x_all), max(Ln_y_all))
    ts_code_min = max(15.0, Ln_max * 100.0 / 32.0)

    # 4b. Long-term Deflection Calculation (ECP 203)
    deflection_results = calculate_flat_slab_deflections(
        Lx_calc, Ly_calc, cantilevers, ts, d, Fcu, DL_tot, LL,
        void_panel_ids=set(_confirmed_voids),
        col_w_cm=bc_s, col_d_cm=tc_s,
    )
    all_deflection_safe = all(p["is_safe"] for p in deflection_results)

    # 5. Punching Shear Check
    punching_results = calculate_punching_shear(col_list, Lx_calc, Ly_calc, cantilevers, Wu, d, Fcu)

    # 6. Top Extra Steel at Columns (with enlarged bay influence)
    top_extra_cols = calculate_extra_top_steel_at_columns(
        col_list, rows_x, rows_y, Lx_calc, Ly_calc, d, Fcu, Fy, ts, prov_top_mesh_cm2m, col_extra_dia, enlarged_bays=enlarged_bays_info
    )

    # 6b. Extra Slab Top Steel in Middle Strips / Panels (الحديد الإضافي العلوي للبلاطة)
    top_extra_slab_bays = []
    for j in range(len(Ly_calc)):
        for i in range(len(Lx_calc)):
            pid = f"P_{i+1}_{j+1}"
            if pid in _confirmed_voids:
                continue
            x_l, x_r = x_coords[i], x_coords[i+1]
            y_b, y_t = y_coords[j], y_coords[j+1]
            span_lx = Lx_calc[i]
            span_ly = Ly_calc[j]
            cx = (x_l + x_r) / 2.0
            cy = (y_b + y_t) / 2.0

            Ln_x = max(0.5, span_lx - bc_m)
            Ln_y = max(0.5, span_ly - tc_m)

            Mo_x = Wu * span_ly * (Ln_x ** 2) / 8.0
            M_neg_ms_x = 0.25 * Mo_x
            w_ms_x = max(0.1, span_ly - min(span_lx, span_ly) / 2.0)
            As_req_ms_x = calc_As(M_neg_ms_x, w_ms_x, d, Fcu, Fy, ts)
            As_m_ms_x = As_req_ms_x / w_ms_x
            delta_As_x = max(0.0, As_m_ms_x - prov_top_mesh_cm2m)

            Mo_y = Wu * span_lx * (Ln_y ** 2) / 8.0
            M_neg_ms_y = 0.25 * Mo_y
            w_ms_y = max(0.1, span_lx - min(span_lx, span_ly) / 2.0)
            As_req_ms_y = calc_As(M_neg_ms_y, w_ms_y, d, Fcu, Fy, ts)
            As_m_ms_y = As_req_ms_y / w_ms_y
            delta_As_y = max(0.0, As_m_ms_y - prov_top_mesh_cm2m)

            # X-direction Top Slab Extra Check
            if delta_As_x > 0.05:
                a_bar = bar_area(col_extra_dia)
                n_b_x = max(2, math.ceil((delta_As_x * span_ly) / a_bar))
                L_ext_x = round(0.60 * span_lx, 2)
                top_extra_slab_bays.append({
                    "panel_id": pid,
                    "bay_label": f"Bay X{i+1}-X{i+2} / Y{j+1}-Y{j+2} (X-Dir)",
                    "dir": "X",
                    "span_len": span_lx,
                    "W_bay": span_ly,
                    "cx": cx,
                    "cy": cy,
                    "n_extra": n_b_x,
                    "dia_extra": col_extra_dia,
                    "L_extra": L_ext_x,
                    "callout": f"+{n_b_x} Φ{col_extra_dia} (X-Dir, L={L_ext_x}m)"
                })

            # Y-direction Top Slab Extra Check
            if delta_As_y > 0.05:
                a_bar = bar_area(col_extra_dia)
                n_b_y = max(2, math.ceil((delta_As_y * span_lx) / a_bar))
                L_ext_y = round(0.60 * span_ly, 2)
                top_extra_slab_bays.append({
                    "panel_id": pid,
                    "bay_label": f"Bay X{i+1}-X{i+2} / Y{j+1}-Y{j+2} (Y-Dir)",
                    "dir": "Y",
                    "span_len": span_ly,
                    "W_bay": span_lx,
                    "cx": cx,
                    "cy": cy,
                    "n_extra": n_b_y,
                    "dia_extra": col_extra_dia,
                    "L_extra": L_ext_y,
                    "callout": f"+{n_b_y} Φ{col_extra_dia} (Y-Dir, L={L_ext_y}m)"
                })

    # 7. Cantilever Reinforcement
    cant_rft_list = calculate_cantilever_reinforcement(cantilevers, Wu, d, Fcu, Fy, ts, bottom_mesh_dia)

    # 8. Bill of Quantities (BoQ)
    boq = calculate_boq(
        Lx_calc, Ly_calc, cantilevers, ts,
        n_mesh_btm, bottom_mesh_dia, n_mesh_top, top_mesh_dia,
        top_extra_cols, cant_rft_list, btm_extra_spans=btm_extra_spans,
        void_panels=_all_panels,
        fcu=Fcu,
    )

    # ═════════════════════════════════════════════════════════════════════════
    #  OUTPUT DASHBOARD & RESULTS
    # ═════════════════════════════════════════════════════════════════════════

    st.markdown('<div class="section-header">📊 Design Results Summary & Structural Status (ملخص نتائج التصميم والحالة الإنشائية)</div>', unsafe_allow_html=True)

    # Structural Redesign Summary Banner if columns were removed
    if _confirmed_removals:
        st.markdown(
            f"""
            <div style='background:#f0fdf4;border:2px solid #22c55e;padding:12px 18px;border-radius:8px;margin-bottom:14px;'>
            <h4 style='color:#15803d;margin:0 0 6px 0;'>🔄 تم إعادة التصميم الإنشائي وتحديث التسليح بعد إزالة الأعمدة</h4>
            <b>الأعمدة المحذوفة:</b> {', '.join(sorted(_confirmed_removals, key=lambda c: int(c[1:])))}<br>
            • <b>أقصى بحر خالص (Ln,max):</b> {Ln_max:.2f} m (الحد الأدنى لسمك البلاطة: {ts_code_min:.1f} cm).<br>
            • <b>إعادة توزيع الأحمال:</b> تم ترحيل أحمال الأعمدة المحذوفة إلى الأعمدة المجاورة المحيطة وتحديث فحص القص الثاقب (Punching Shear).<br>
            • <b>الحديد الإضافي السفلي (Bottom Extra):</b> تم توليد وحساب التسليح الإضافي السفلي للباكيات المكبرة لتغطية عزوم الانحناء الموجبة (+M).<br>
            • <b>الحديد الإضافي العلوي (Top Extra):</b> تم زيادة التسليح الإضافي العلوي فوق الأعمدة الحاملة للباكيات المكبرة.
            </div>
            """,
            unsafe_allow_html=True
        )

    all_safe = all(p["is_safe"] for p in punching_results)
    punching_str = "✅ All Safe" if all_safe else "⚠️ Unsafe Columns"
    punching_color = "#16a34a" if all_safe else "#dc2626"

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.markdown(
            f"""
            <div class="ecp-metric-box">
                <div class="ecp-metric-lbl">Adopted ts</div>
                <div class="ecp-metric-val">{ts:.0f} cm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"""
            <div class="ecp-metric-box">
                <div class="ecp-metric-lbl">Effective Depth d</div>
                <div class="ecp-metric-val">{d:.1f} cm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"""
            <div class="ecp-metric-box">
                <div class="ecp-metric-lbl">Ultimate Load Wu</div>
                <div class="ecp-metric-val">{Wu:.3f} t/m²</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f"""
            <div class="ecp-metric-box">
                <div class="ecp-metric-lbl">Bottom Mesh (B1,B2)</div>
                <div class="ecp-metric-val">{mesh_btm_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m5:
        st.markdown(
            f"""
            <div class="ecp-metric-box">
                <div class="ecp-metric-lbl">Top Mesh (T1,T2)</div>
                <div class="ecp-metric-val">{mesh_top_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m6:
        st.markdown(
            f"""
            <div class="ecp-metric-box">
                <div class="ecp-metric-lbl">Punching Check</div>
                <div class="ecp-metric-val" style="color:{punching_color};">{punching_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if ts < ts_code_min:
        st.warning(f"⚠️ **ملاحظة إنشائية على السُمك بعد إزالة الأعمدة**: السُمك المحدد ({ts:.0f} cm) أقل من الحد الأدنى الموصى به لمقاومة الترخيم للبحر الأكبر ($L_n/32 = {ts_code_min:.1f}\\text{{ cm}}$). يرجى زيادة سُمك البلاطة أو فحص الترخيم (Long-Term Deflection).")

    st.markdown("---")

    # ── 📊 1. 2D BENDING MOMENT MATRIX & COLOR CONTOURS (M11 & M22) ─────────
    img_m11_b64 = None
    img_m22_b64 = None
    img_dual_moment_b64 = None

    with st.expander(
        "📊 1. 2D Bending Moment Matrix & Color Contours (مصفوفة العزوم والمخطط اللوني M11 & M22)",
        expanded=False,
    ):
        moment_view_mode = S.radio(
            "👁️ Select Moment View Mode (اختر اتجاه عزم الانحناء للعرض):",
            "fs_moment_contour_view_mode_idx",
            options=[
                "↔️ M11 — X-Direction Moment (عزوم المحور الأفقي)",
                "↕️ M22 — Y-Direction Moment (عزوم المحور الرأسي)",
            ],
            index=0,
        )

        if "M11" in moment_view_mode:
            fig_m11 = generate_flat_slab_moment_contour(
                Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
                mode="M11",
                col_w_cm=bc_s, col_d_cm=tc_s,
                removed_cols=_removed_col_objs,
                void_panel_ids=set(_confirmed_voids),
                top_extra_cols=top_extra_cols,
                btm_extra_spans=btm_extra_spans,
            )
            st.pyplot(fig_m11, use_container_width=True)
            buf_m11 = io.BytesIO()
            fig_m11.savefig(buf_m11, format="png", bbox_inches="tight", dpi=300)
            buf_m11.seek(0)
            img_m11_b64 = "data:image/png;base64," + base64.b64encode(buf_m11.getvalue()).decode("utf-8")
            buf_m11.seek(0)
            st.download_button(
                label="📥 Download M11 Moment Contour Plan (High-Res PNG)",
                data=buf_m11,
                file_name=f"{prefix}Flat_Slab_Moment_M11_Contour_Plan_ts{ts:.0f}cm.png",
                mime="image/png",
                use_container_width=True,
            )
            plt.close(fig_m11)

        else:
            fig_m22 = generate_flat_slab_moment_contour(
                Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
                mode="M22",
                col_w_cm=bc_s, col_d_cm=tc_s,
                removed_cols=_removed_col_objs,
                void_panel_ids=set(_confirmed_voids),
                top_extra_cols=top_extra_cols,
                btm_extra_spans=btm_extra_spans,
            )
            st.pyplot(fig_m22, use_container_width=True)
            buf_m22 = io.BytesIO()
            fig_m22.savefig(buf_m22, format="png", bbox_inches="tight", dpi=300)
            buf_m22.seek(0)
            img_m22_b64 = "data:image/png;base64," + base64.b64encode(buf_m22.getvalue()).decode("utf-8")
            buf_m22.seek(0)
            st.download_button(
                label="📥 Download M22 Moment Contour Plan (High-Res PNG)",
                data=buf_m22,
                file_name=f"{prefix}Flat_Slab_Moment_M22_Contour_Plan_ts{ts:.0f}cm.png",
                mime="image/png",
                use_container_width=True,
            )
            plt.close(fig_m22)

    # ── 📊 1b. MOMENT DEFICIT CONTOUR (فارق العزوم السفلي) ──────────────────
    with st.expander(
        "📊 1b. Moment Deficit Contour — Bottom Steel Coverage (كونتور فارق العزوم: ما يغطيه الحديد السفلي وما يحتاج إضافي)",
        expanded=False,
    ):
        # Info card: show M_cap of the base mesh
        M_cap_display = calc_moment_capacity_btm(prov_btm_mesh_cm2m, d, Fcu, Fy)
        st.markdown(
            f"""
            <div style="background:#eff6ff; border:2px solid #3b82f6; border-radius:10px;
                        padding:14px 20px; margin:10px 0 16px 0; display:flex; gap:32px; flex-wrap:wrap;">
                <div>
                    <span style="font-size:13px; font-weight:600; color:#64748b;">Bottom Mesh Provided</span><br>
                    <span style="font-size:17px; font-weight:700; color:#1e40af;">{mesh_btm_str}</span>
                </div>
                <div>
                    <span style="font-size:13px; font-weight:600; color:#64748b;">Steel Area (As)</span><br>
                    <span style="font-size:17px; font-weight:700; color:#1e40af;">{prov_btm_mesh_cm2m:.2f} cm²/m</span>
                </div>
                <div>
                    <span style="font-size:13px; font-weight:600; color:#64748b;">Moment Capacity (M_cap)</span><br>
                    <span style="font-size:17px; font-weight:700; color:#15803d;">{M_cap_display:.3f} t.m/m</span>
                </div>
                <div style="border-left:2px solid #cbd5e1; padding-left:20px;">
                    <span style="font-size:13px; font-weight:600; color:#64748b;">Deficit = max(0, M_applied − M_cap)</span><br>
                    <span style="font-size:13px; color:#475569; font-weight:500;">
                        🟢 Green = No extra steel needed &nbsp;|&nbsp; 🟡→🔴 Coloured = Extra bottom steel required
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        deficit_view_mode = S.radio(
            "👁️ Select Deficit View (اختر اتجاه عرض فارق العزوم):",
            "fs_deficit_contour_view_mode_idx",
            options=[
                "↔️ M11 Deficit — X-Direction (فارق عزوم M11 الأفقي)",
                "↕️ M22 Deficit — Y-Direction (فارق عزوم M22 الرأسي)",
            ],
            index=0,
        )

        if "M11" in deficit_view_mode:
            _def_mode = "M11"
        else:
            _def_mode = "M22"

        fig_deficit = generate_moment_deficit_contour(
            Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
            prov_btm_mesh_cm2m=prov_btm_mesh_cm2m,
            d_cm=d,
            Fcu=Fcu,
            Fy=Fy,
            mode=_def_mode,
            col_w_cm=bc_s,
            col_d_cm=tc_s,
            removed_cols=_removed_col_objs,
            void_panel_ids=set(_confirmed_voids),
        )
        st.pyplot(fig_deficit, use_container_width=True)
        buf_deficit = io.BytesIO()
        fig_deficit.savefig(buf_deficit, format="png", bbox_inches="tight", dpi=300)
        buf_deficit.seek(0)
        st.download_button(
            label=f"📥 Download Moment Deficit Contour ({_def_mode}) Plan (High-Res PNG)",
            data=buf_deficit,
            file_name=f"{prefix}Flat_Slab_Moment_Deficit_{_def_mode}_ts{ts:.0f}cm.png",
            mime="image/png",
            use_container_width=True,
        )
        plt.close(fig_deficit)

    # ── 🟢 2. TOP REINFORCEMENT PLAN (Initialized for exports) ────────────────
    img_top_b64 = None

    # ── 🔵 3. BOTTOM REINFORCEMENT PLAN (Initialized for exports) ────────────
    active_btm_extras   = [b for b in btm_extra_spans if isinstance(b, dict) and b.get("n_extra", 0) > 0]
    active_btm_extras_x = [b for b in active_btm_extras if b.get("dir", "X") == "X"]
    active_btm_extras_y = [b for b in active_btm_extras if b.get("dir", "X") == "Y"]
    img_btm_b64 = None   # kept for report generator compatibility

    # ── 📋 MASTER DESIGN OUTPUT TABLE ────────────────────────────────────────


    with st.expander("📋 Master Design Output Table (الجدول الملخص الشامل لمخرجات التصميم)", expanded=False):
        btm_extra_labels = [b["bay_label"] + ": " + b["callout"] for b in btm_extra_spans if isinstance(b, dict) and b.get("n_extra", 0) > 0]

        master_summary = [
            ["1. Slab Thickness (ts)", f"{ts:.0f} cm", f"User input ts={ts:.0f} cm (Code limit Ln_max/32 = {ts_code_min:.1f} cm)"],
            ["2. Effective Depth (d)", f"{d:.2f} cm", f"ts ({ts:.0f}cm) − Cover ({cov:.1f}cm) − Φ/2 ({avg_rebar_dia/2.0:.2f}cm) = {d:.2f} cm (Maximized)"],
            ["3. Bottom Mesh RFT (Mesh B1, B2)", f"{mesh_btm_str} (X & Y)", f"Prov: {prov_btm_mesh_cm2m:.2f} cm²/m (Min req: {As_min_req_m:.2f} cm²/m)"],
            ["4. Top Nominal Mesh RFT (Mesh T1, T2)", f"{mesh_top_str} (X & Y)", f"Prov: {prov_top_mesh_cm2m:.2f} cm²/m across full slab (Φ={top_mesh_dia}mm)"],
            ["5. Top Extra @ Columns", f"{sum(1 for c in top_extra_cols if c['is_needed'])} columns require extra top bars", f"Calculated using selected Col Extra Φ{col_extra_dia} mm"],
            ["6. Bottom Extra @ Strips / Enlarged Bays", f"{len(btm_extra_labels)} zones require extra bottom steel", " | ".join(btm_extra_labels) if btm_extra_labels else f"Base Bottom Mesh (Φ{bottom_mesh_dia}) is sufficient"],
            ["7. Cantilever Shawka RFT", f"{len(cant_rft_list)} cantilevers active", "Detailed in Cantilevers section (Ext = 1.5 L_cant)"],
            ["8. Perimeter & Edge RFT", "U-Loops Φ10 @ 20 cm + 2Φ12 Top/Btm", "Placed along all free slab perimeter boundaries"],
            ["9. Estimated Steel Weight", f"{boq['total_steel_ton']:.2f} Ton", f"Reinforcement Ratio: {boq['steel_ratio_kg_m3']:.1f} kg/m³"],
        ]
        render_styled_table(master_summary, headers=["Design Item", "Design Output / Value", "Engineering Notes & Code Reference"])

    # ── 📊 BENDING MOMENTS & REINFORCEMENT SCHEDULES (Collapsed Section) ─────
    with st.expander("📊 جداول حصر وتوزيع العزوم وحديد التسليح (Bending Moments & Steel Design Schedules)", expanded=False):
        st.markdown(
            """
            <div style="background:#f8fafc; border:1.5px solid #cbd5e1; border-radius:8px; padding:10px 16px; margin-bottom:14px;">
                <div style="font-size:0.95rem; font-weight:800; color:#1e3a8a; display:flex; align-items:center; gap:8px;">
                    <span>📋</span>
                    <span>جداول تفصيلية شاملة لمواضع وقيم عزوم الانحناء التصميمية وحديد التسليح المطلوب لتغطيتها طبقاً للكود المصري ECP 203</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        active_top_extra = [c for c in top_extra_cols if c.get("is_needed", False)]
        active_btm_x = [bx for bx in all_panels_x_design if bx.get("is_needed", False)]
        active_btm_y = [by for by in all_panels_y_design if by.get("is_needed", False)]

        tab_tbl_top, tab_tbl_btm_x, tab_tbl_btm_y = st.tabs([
            f"🔴 1. الحديد العلوي الإضافي فوق الأعمدة ({len(active_top_extra)} عمود)",
            f"↔️ 2. الحديد السفلي الإضافي — اتجاه X ({len(active_btm_x)} باكية)",
            f"↕️ 3. الحديد السفلي الإضافي — اتجاه Y ({len(active_btm_y)} باكية)",
        ])

        with tab_tbl_top:
            if active_top_extra:
                st.markdown(f"##### 🔴 جدول الأعمدة التي تحتاج إلى حديد إضافي علوي ({len(active_top_extra)} أعمدة):")
                top_table_rows = []
                for c in active_top_extra:
                    as_req_val = float(c["As_req (cm²/m)"])
                    as_mesh_val = float(c["As_mesh (cm²/m)"])
                    delta_as_val = max(0.0, as_req_val - as_mesh_val)
                    top_table_rows.append({
                        "موضع ورقم العمود (Location / ID)": f"{c['id']} — Grid ({c['grid']})",
                        "نوع وموضع الركيزة (Support Type)": c["type"],
                        "العزم السالب التصميمي Mu⁻ (ton·m/m)": f"{c['Mu_neg (t.m)']:.2f}",
                        "التسليح المطلوب كلياً As_req (cm²/m)": f"{as_req_val:.2f}",
                        "مقاومة الشبكة العلوية As_mesh (cm²/m)": f"{as_mesh_val:.2f}",
                        "فرق التسليح الإضافي ΔAs (cm²/m)": f"{delta_as_val:.2f}",
                        "الحديد المطلوب لتغطية العزم (Rebar Selection)": c["callout"],
                        "طول الامتداد والتفريد L_ext (m)": f"{c['L_extra']:.2f} m",
                        "حالة التسليح": "🚨 يتطلب حديد إضافي علوي",
                    })
                render_styled_table(top_table_rows)
            else:
                st.markdown(
                    f"""
                    <div style="background:#f0fdf4; border:2px solid #16a34a; border-radius:8px; padding:16px 20px; text-align:center; margin:8px 0;">
                        <div style="color:#15803d; font-size:1.15rem; font-weight:800; margin-bottom:4px;">✅ لا توجد أعمدة تحتاج إلى حديد إضافي علوي</div>
                        <div style="color:#334155; font-size:0.95rem;">الشبكة العلوية الأساسية ({mesh_top_str}) تغطي بالكامل كافة العزوم السالبة (-M) فوق جميع أعمدة السقف.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with tab_tbl_btm_x:
            if active_btm_x:
                st.markdown(f"##### ↔️ جدول الباكيات التي تحتاج إلى حديد إضافي سفلي في الاتجاه الأفقي X ({len(active_btm_x)} باكية):")
                btm_x_table_rows = []
                for bx in active_btm_x:
                    btm_x_table_rows.append({
                        "مكان وموضع الباكية (Bay Location)": bx["bay_label"],
                        "نوع البحر (Span Classification)": bx["span_type"],
                        "طول البحر L (m)": f"{bx['span_len']:.2f} m",
                        "البحر الصافي Ln (m)": f"{bx['Ln']:.2f} m",
                        "العزم الموجب التصميمي Mu⁺ (ton·m/m)": f"{bx['M_pos']:.2f}",
                        "التسليح السفلي المطلوب As_req (cm²/m)": f"{bx['As_req_m']:.2f}",
                        "تسليح الشبكة السفلية As_prov (cm²/m)": f"{bx['As_prov_m']:.2f}",
                        "فارق التسليح ΔAs (cm²/m)": f"{bx['delta_As']:.2f}",
                        "الحديد الإضافي المطلوب (Bottom Rebar)": bx["callout"],
                        "طول التقطيع والتفريد L_cut (m)": bx["L_cut"],
                        "حالة التسليح": "🚨 يتطلب حديد إضافي سفلي",
                    })
                render_styled_table(btm_x_table_rows)
            else:
                st.markdown(
                    f"""
                    <div style="background:#f0fdf4; border:2px solid #16a34a; border-radius:8px; padding:16px 20px; text-align:center; margin:8px 0;">
                        <div style="color:#15803d; font-size:1.15rem; font-weight:800; margin-bottom:4px;">✅ لا توجد باكيات تحتاج إلى حديد إضافي سفلي في الاتجاه الأفقي X</div>
                        <div style="color:#334155; font-size:0.95rem;">الشبكة السفلية الأساسية ({mesh_btm_str}) تغطي بالكامل كافة العزوم الموجبة (+M) لجميع بحور الاتجاه الأفقي X.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with tab_tbl_btm_y:
            if active_btm_y:
                st.markdown(f"##### ↕️ جدول الباكيات التي تحتاج إلى حديد إضافي سفلي في الاتجاه الرأسي Y ({len(active_btm_y)} باكية):")
                btm_y_table_rows = []
                for by in active_btm_y:
                    btm_y_table_rows.append({
                        "مكان وموضع الباكية (Bay Location)": by["bay_label"],
                        "نوع البحر (Span Classification)": by["span_type"],
                        "طول البحر L (m)": f"{by['span_len']:.2f} m",
                        "البحر الصافي Ln (m)": f"{by['Ln']:.2f} m",
                        "العزم الموجب التصميمي Mu⁺ (ton·m/m)": f"{by['M_pos']:.2f}",
                        "التسليح السفلي المطلوب As_req (cm²/m)": f"{by['As_req_m']:.2f}",
                        "تسليح الشبكة السفلية As_prov (cm²/m)": f"{by['As_prov_m']:.2f}",
                        "فارق التسليح ΔAs (cm²/m)": f"{by['delta_As']:.2f}",
                        "الحديد الإضافي المطلوب (Bottom Rebar)": by["callout"],
                        "طول التقطيع والتفريد L_cut (m)": by["L_cut"],
                        "حالة التسليح": "🚨 يتطلب حديد إضافي سفلي",
                    })
                render_styled_table(btm_y_table_rows)
            else:
                st.markdown(
                    f"""
                    <div style="background:#f0fdf4; border:2px solid #16a34a; border-radius:8px; padding:16px 20px; text-align:center; margin:8px 0;">
                        <div style="color:#15803d; font-size:1.15rem; font-weight:800; margin-bottom:4px;">✅ لا توجد باكيات تحتاج إلى حديد إضافي سفلي في الاتجاه الرأسي Y</div>
                        <div style="color:#334155; font-size:0.95rem;">الشبكة السفلية الأساسية ({mesh_btm_str}) تغطي بالكامل كافة العزوم الموجبة (+M) لجميع بحور الاتجاه الرأسي Y.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── 🗺️ STEEL LAYOUT MASTER FLOOR PLAN ─────────────────────────────────────
    with st.expander("🗺️ Steel Layout (مسقط أفقي لتسليح البلاطة)", expanded=True):
        st.markdown(
            """
            <style>
            /* Allow tabs in Steel Layout to wrap titles cleanly and display side-by-side */
            div[data-testid="stTabs"] button[role="tab"],
            div[data-baseweb="tab-list"] button {
                white-space: normal !important;
                text-align: center !important;
                height: auto !important;
                min-height: 48px !important;
                padding: 6px 12px !important;
                font-weight: 600 !important;
                line-height: 1.25 !important;
                font-size: 0.88rem !important;
            }
            div[data-testid="stTabs"] div[role="tablist"],
            div[data-baseweb="tab-list"] {
                display: flex !important;
                flex-wrap: wrap !important;
                gap: 4px !important;
            }
            </style>
            <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 14px 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #3b82f6;">
                <div style="color: #60a5fa; font-weight: bold; font-size: 1.15rem;">📐 المخططات التنفيذية لتسليح البلاطة (Executive Rebar Plans)</div>
                <div style="color: #cbd5e1; font-size: 0.92rem; margin-top: 4px;">
                    تم فصل كل طبقة ونوع تسليح في رسم هندسي مستقل عالي الدقة بخط كبير وواضح مع كود الألوان والمواصفات وحصر الأطوال والأوزان في تبويبات متجاورة.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_m1, tab_m2a, tab_m2b, tab_m3a, tab_m3b = st.tabs([
            "🔴 1. Column Caps (Top Extra)\nكابات وتفريد الإضافي العلوي للأعمدة",
            "🔶 2A. Bottom Extra (X-Dir)\nالإضافي السفلي وشوك الكوابيل (اتجاه X)",
            "🔶 2B. Bottom Extra (Y-Dir)\nالإضافي السفلي وشوك الكوابيل (اتجاه Y)",
            "🔵 3A. Top Slab Extra (X-Dir)\nالرقة العلوية والإضافي العلوي (اتجاه X)",
            "🔵 3B. Top Slab Extra (Y-Dir)\nالرقة العلوية والإضافي العلوي (اتجاه Y)",
        ])

        # ── Tab 1: Column Caps
        with tab_m1:
            st.markdown("#### 🔴 1. Column Caps Layout (Top Extra) — كابات الحديد الإضافي العلوي فوق الأعمدة (أبعاد ومساحة الشرائح)")
            fig_cc = generate_flat_slab_column_caps_sketch(
                Lx_calc, Ly_calc, cantilevers, ts,
                top_extra_cols=top_extra_cols,
                col_w_cm=bc_s, col_d_cm=tc_s,
                removed_cols=_confirmed_removals,
                void_panel_ids=_confirmed_voids,
            )
            st.pyplot(fig_cc, use_container_width=True)
            buf_cc = io.BytesIO()
            fig_cc.savefig(buf_cc, format="png", bbox_inches="tight", dpi=300)
            buf_cc.seek(0)
            st.download_button(
                label="📥 Download 1. Column Caps Layout (High-Res PNG)",
                data=buf_cc,
                file_name=f"{prefix}1_Column_Caps_Top_Extra_ts{ts:.0f}cm.png",
                mime="image/png",
                use_container_width=True,
                key="btn_dl_col_caps",
            )
            plt.close(fig_cc)

        # ── Tab 2A: Bottom Extra (X-Direction) & Shawka
        with tab_m2a:
            st.markdown("#### 🔶 2A. Bottom Extra (X-Direction) & Base Meshes — الحديد الإضافي السفلي وشوك الكوابيل في اتجاه X وشبكات التسليح")
            fig_bes_x = generate_flat_slab_bottom_extra_shawka_sketch(
                Lx_calc, Ly_calc, cantilevers, ts,
                btm_extra_spans=btm_extra_spans,
                cant_rft_list=cant_rft_list,
                n_mesh_btm=n_mesh_btm,
                bottom_mesh_dia=bottom_mesh_dia,
                n_mesh_top=n_mesh_top,
                top_mesh_dia=top_mesh_dia,
                col_w_cm=bc_s, col_d_cm=tc_s,
                removed_cols=_confirmed_removals,
                void_panel_ids=_confirmed_voids,
                direction="X",
            )
            st.pyplot(fig_bes_x, use_container_width=True)
            buf_bes_x = io.BytesIO()
            fig_bes_x.savefig(buf_bes_x, format="png", bbox_inches="tight", dpi=300)
            buf_bes_x.seek(0)
            st.download_button(
                label="📥 Download 2A. Bottom Extra (X-Direction) Layout (High-Res PNG)",
                data=buf_bes_x,
                file_name=f"{prefix}2A_Bottom_Extra_X_ts{ts:.0f}cm.png",
                mime="image/png",
                use_container_width=True,
                key="btn_dl_btm_extra_x",
            )
            plt.close(fig_bes_x)

        # ── Tab 2B: Bottom Extra (Y-Direction) & Shawka
        with tab_m2b:
            st.markdown("#### 🔶 2B. Bottom Extra (Y-Direction) & Base Meshes — الحديد الإضافي السفلي وشوك الكوابيل في اتجاه Y وشبكات التسليح")
            fig_bes_y = generate_flat_slab_bottom_extra_shawka_sketch(
                Lx_calc, Ly_calc, cantilevers, ts,
                btm_extra_spans=btm_extra_spans,
                cant_rft_list=cant_rft_list,
                n_mesh_btm=n_mesh_btm,
                bottom_mesh_dia=bottom_mesh_dia,
                n_mesh_top=n_mesh_top,
                top_mesh_dia=top_mesh_dia,
                col_w_cm=bc_s, col_d_cm=tc_s,
                removed_cols=_confirmed_removals,
                void_panel_ids=_confirmed_voids,
                direction="Y",
            )
            st.pyplot(fig_bes_y, use_container_width=True)
            buf_bes_y = io.BytesIO()
            fig_bes_y.savefig(buf_bes_y, format="png", bbox_inches="tight", dpi=300)
            buf_bes_y.seek(0)
            st.download_button(
                label="📥 Download 2B. Bottom Extra (Y-Direction) Layout (High-Res PNG)",
                data=buf_bes_y,
                file_name=f"{prefix}2B_Bottom_Extra_Y_ts{ts:.0f}cm.png",
                mime="image/png",
                use_container_width=True,
                key="btn_dl_btm_extra_y",
            )
            plt.close(fig_bes_y)

        # ── Tab 3A: Top Base Mesh & Extra Slab Top Mesh (X-Direction)
        with tab_m3a:
            st.markdown("#### 🔵 3A. Top Base Mesh & Extra Slab Top Mesh (X-Direction) — الرقة العلوية الأساسية والحديد الإضافي العلوي (اتجاه X)")
            fig_tmes_x = generate_flat_slab_top_mesh_extra_sketch(
                Lx_calc, Ly_calc, cantilevers, ts,
                top_extra_slab_bays=top_extra_slab_bays,
                n_mesh_top=n_mesh_top,
                top_mesh_dia=top_mesh_dia,
                n_mesh_btm=n_mesh_btm,
                bottom_mesh_dia=bottom_mesh_dia,
                col_w_cm=bc_s, col_d_cm=tc_s,
                removed_cols=_confirmed_removals,
                void_panel_ids=_confirmed_voids,
                direction="X",
            )
            st.pyplot(fig_tmes_x, use_container_width=True)
            buf_tmes_x = io.BytesIO()
            fig_tmes_x.savefig(buf_tmes_x, format="png", bbox_inches="tight", dpi=300)
            buf_tmes_x.seek(0)
            st.download_button(
                label="📥 Download 3A. Top Slab Extra (X-Direction) Layout (High-Res PNG)",
                data=buf_tmes_x,
                file_name=f"{prefix}3A_Top_Base_Mesh_Extra_Slab_X_ts{ts:.0f}cm.png",
                mime="image/png",
                use_container_width=True,
                key="btn_dl_top_mesh_extra_x",
            )
            plt.close(fig_tmes_x)

        # ── Tab 3B: Top Base Mesh & Extra Slab Top Mesh (Y-Direction)
        with tab_m3b:
            st.markdown("#### 🔵 3B. Top Base Mesh & Extra Slab Top Mesh (Y-Direction) — الرقة العلوية الأساسية والحديد الإضافي العلوي (اتجاه Y)")
            fig_tmes_y = generate_flat_slab_top_mesh_extra_sketch(
                Lx_calc, Ly_calc, cantilevers, ts,
                top_extra_slab_bays=top_extra_slab_bays,
                n_mesh_top=n_mesh_top,
                top_mesh_dia=top_mesh_dia,
                n_mesh_btm=n_mesh_btm,
                bottom_mesh_dia=bottom_mesh_dia,
                col_w_cm=bc_s, col_d_cm=tc_s,
                removed_cols=_confirmed_removals,
                void_panel_ids=_confirmed_voids,
                direction="Y",
            )
            st.pyplot(fig_tmes_y, use_container_width=True)
            buf_tmes_y = io.BytesIO()
            fig_tmes_y.savefig(buf_tmes_y, format="png", bbox_inches="tight", dpi=300)
            buf_tmes_y.seek(0)
            st.download_button(
                label="📥 Download 3B. Top Slab Extra (Y-Direction) Layout (High-Res PNG)",
                data=buf_tmes_y,
                file_name=f"{prefix}3B_Top_Base_Mesh_Extra_Slab_Y_ts{ts:.0f}cm.png",
                mime="image/png",
                use_container_width=True,
                key="btn_dl_top_mesh_extra_y",
            )
            plt.close(fig_tmes_y)

    # ── 📉 DEFLECTION & SERVICEABILITY VERIFICATION ──────────────────────────
    with st.expander("📉 Deflection Check (فحص سهم الانحناء والترخيم طويل المدى)", expanded=False):
        fig_def = generate_flat_slab_deflection_contour_sketch(
            Lx_calc, Ly_calc, cantilevers, ts, d, Fcu, DL_tot, LL,
            deflection_results,
            col_w_cm=bc_s, col_d_cm=tc_s,
            removed_cols=_removed_col_objs,
            void_panel_ids=set(_confirmed_voids),
        )
        st.pyplot(fig_def, use_container_width=True)

        buf_def = io.BytesIO()
        fig_def.savefig(buf_def, format="png", bbox_inches="tight", dpi=300)
        buf_def.seek(0)
        def_dl_label = "📥 Download Deflection Warning 2D Contour Plan (High-Res PNG)" if not all_deflection_safe else "📥 Download Deflection Verification 2D Plan (High-Res PNG)"
        st.download_button(
            label=def_dl_label,
            data=buf_def,
            file_name=f"{prefix}Flat_Slab_Deflection_Check_ts{ts:.0f}cm.png",
            mime="image/png",
            use_container_width=True,
            key="btn_dl_deflection_contour",
        )
        plt.close(fig_def)

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        def_df = pd.DataFrame([
            {
                "Panel ID": p["Panel ID"],
                "Bay Location": p["Bay Label"],
                "Type": p["Location Type"],
                "Span Ln (m)": f"{p['Ln (m)']:.2f} m",
                "Service Load Ws (t/m²)": f"{p['Ws (t/m²)']:.2f}",
                "Ms (t·m/m)": f"{p['Ms_pos (t.m/m)']:.2f}",
                "Mcr (t·m/m)": f"{p['Mcr (t.m/m)']:.2f}",
                "Section State": "تشريخ (Cracked)" if p["Is_Cracked"] else "غير مشرخ (Uncracked)",
                "Short-Term δst (mm)": f"{p['delta_st (mm)']:.2f} mm",
                "Long-Term Δtotal (mm)": f"{p['delta_long (mm)']:.2f} mm",
                "Allowable Limit Δall (mm)": f"{p['delta_all (mm)']:.2f} mm (Ln/250)",
                "Ratio (Δ/Δall)": f"{p['Ratio']:.2f}",
                "Status": p["Status"],
            }
            for p in deflection_results
        ])
        render_styled_table(def_df)

        if not all_deflection_safe:
            st.warning("⚠️ **تنبيه إنشائي (Deflection Warning)**: بعض بحور وباكيات السقف تتجاوز سهم الانحناء المسموح كودياً (Δact > Δall). يُنصح بزيادة سُمك البلاطة $t_s$ أو إضافة سقوط عمود (Drop Panel) أو إضافة تسليح ضغط.")

    # ── 🥊 PUNCHING SHEAR VERIFICATION ───────────────────────────────────────
    with st.expander("🥊 Punching Shear Check (فحص القص الثاقب لجميع الأعمدة)", expanded=False):
        fig_punch = generate_flat_slab_punching_shear_sketch(
            Lx_calc, Ly_calc, cantilevers, ts, d, Fcu, Wu,
            punching_results,
            col_w_cm=bc_s, col_d_cm=tc_s,
            removed_cols=_removed_col_objs,
            void_panel_ids=set(_confirmed_voids),
        )
        st.pyplot(fig_punch, use_container_width=True)

        buf_punch = io.BytesIO()
        fig_punch.savefig(buf_punch, format="png", bbox_inches="tight", dpi=300)
        buf_punch.seek(0)
        st.download_button(
            label="📥 Download Punching Shear Verification Plan (High-Res PNG)",
            data=buf_punch,
            file_name=f"{prefix}Flat_Slab_Punching_Shear_Check_ts{ts:.0f}cm.png",
            mime="image/png",
            use_container_width=True,
        )
        plt.close(fig_punch)

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        punch_df = pd.DataFrame([
            {
                "Column ID": p["Column ID"],
                "Grid": p["Grid"],
                "Type": p["Location Type"],
                "Pu (ton)": f"{p['Pu (ton)']:.2f}",
                "bo (cm)": f"{p['bo (cm)']:.1f}",
                "qup (kg/cm²)": f"{p['qup (kg/cm²)']:.2f}",
                "qcup (kg/cm²)": f"{p['qcup (kg/cm²)']:.2f}",
                "Stress Ratio (qup/qcup)": f"{p['Ratio']:.2f}",
                "Status": p["Status"],
            }
            for p in punching_results
        ])
        render_styled_table(punch_df)

        if not all_safe:
            st.warning("⚠️ **تنبيه إنشائي**: بعض الأعمدة غير آمنة في القص الثاقب (qup > qcup). يُنصح بزيادة سُمك البلاطة $t_s$ أو إضافة سقوط عمود (Drop Panel) أو كانات قص (Studs).")

    # ── 🦅 CANTILEVER REINFORCEMENT ──────────────────────────────────────────
    if cant_rft_list:
        with st.expander("🦅 Cantilever Reinforcement Details (تسليح الكوابيل والشوكة)", expanded=False):
            cant_df = pd.DataFrame([
                {
                    "Cantilever Side": f"{c['side_ar']} ({c['side']})",
                    "Length (m)": f"{c['length']:.2f} m",
                    "Cantilever Mu (ton.m/m)": f"{c['Mu (t.m/m)']:.2f}",
                    "Main Top Shawka": c["rft_callout"],
                    "Extension into Slab": f"{c['ext_length']:.2f} m (1.5 L_cant)",
                    "Total Cut Length": f"{c['total_bar_length']:.2f} m",
                    "Secondary Bottom RFT": c["secondary_rft"],
                }
                for c in cant_rft_list
            ])
            render_styled_table(cant_df)

    # ── ⚖️ LOAD SUMMARY ──────────────────────────────────────────────────────
    with st.expander("⚖️ Load Breakdown (ملخص توزيع وتراكب الأحمال)", expanded=False):
        ld_df = pd.DataFrame({
            "Load Component": [
                "Slab Self-Weight  OW = γc × ts",
                "Super-Imposed Dead Load  SDL",
                "Wall Load  WL  (equivalent distributed)",
                "Total Dead Load  DL = OW + SDL + WL",
                "Live Load  LL",
                "Ultimate  Wu = 1.4 DL + 1.6 LL",
            ],
            "Value (ton/m²)": [
                f"{SW:.4f}", f"{SDL:.4f}", f"{WL:.4f}",
                f"{DL_tot:.4f}", f"{LL:.4f}", f"{Wu:.4f}",
            ],
            "Note": [
                f"Auto: {ts:.0f}cm × {gamma_c} t/m³", "User input", "User input",
                "OW + SDL + WL", "User input", "ECP 203 Ultimate load combination",
            ],
        })
        render_styled_table(ld_df)

    # ── 📐 DETAILED DDM MOMENTS TABLES ───────────────────────────────────────
    def render_direction(rows, direction_label):
        with st.expander(f"📐 Bending Moments & Reinforcement — {direction_label} (عزوم الانحناء والتسليح)", expanded=False):
            moment_rows = []
            steel_rows  = []

            for r in rows:
                sl  = r["span_label"]
                st_ = r["span_type"]
                moment_rows += [
                    [f"{sl}  [{st_}]  Total Static Mo", f"{r['Mo']:.3f}", "—"],
                    [f"  ↳ Neg. Ext.  (M_neg_ext)", f"{r['M_neg_ext']:.3f}", "—"],
                    [f"  ↳ Positive   (M_pos)",     f"{r['M_pos']:.3f}",     "—"],
                    [f"  ↳ Neg. Int.  (M_neg_int)", f"{r['M_neg_int']:.3f}", "—"],
                    [f"    ↳ Col.Strip neg.ext",  f"{r['cs_neg_ext']:.3f}", f"{r['cs_w']:.2f}"],
                    [f"    ↳ Mid.Strip neg.ext",  f"{r['ms_neg_ext']:.3f}", f"{r['ms_w']:.2f}"],
                    [f"    ↳ Col.Strip pos",      f"{r['cs_pos']:.3f}",     f"{r['cs_w']:.2f}"],
                    [f"    ↳ Mid.Strip pos",      f"{r['ms_pos']:.3f}",     f"{r['ms_w']:.2f}"],
                    [f"    ↳ Col.Strip neg.int",  f"{r['cs_neg_int']:.3f}", f"{r['cs_w']:.2f}"],
                    [f"    ↳ Mid.Strip neg.int",  f"{r['ms_neg_int']:.3f}", f"{r['ms_w']:.2f}"],
                ]

                def steel_entry(label, As_req, w_m):
                    n, sp, prov, as_m = fmt_steel(As_req, w_m * 100.0, bottom_mesh_dia)
                    return [
                        f"{sl} | {label}",
                        f"{As_req:.2f}",
                        f"{as_m:.2f}",
                        f"{n} Φ{bottom_mesh_dia} / m",
                        f"@ {sp} cm",
                        f"{prov:.3f}",
                    ]

                steel_rows += [
                    steel_entry(f"Col.Strip TOP (neg.ext)  w={r['cs_w']:.1f}m", r["As_cs_neg_ext"], r["cs_w"]),
                    steel_entry(f"Col.Strip BTM (pos)      w={r['cs_w']:.1f}m", r["As_cs_pos"],     r["cs_w"]),
                    steel_entry(f"Col.Strip TOP (neg.int)  w={r['cs_w']:.1f}m", r["As_cs_neg_int"], r["cs_w"]),
                    steel_entry(f"Mid.Strip TOP (neg.ext)  w={r['ms_w']:.1f}m", r["As_ms_neg_ext"], r["ms_w"]),
                    steel_entry(f"Mid.Strip BTM (pos)      w={r['ms_w']:.1f}m", r["As_ms_pos"],     r["ms_w"]),
                    steel_entry(f"Mid.Strip TOP (neg.int)  w={r['ms_w']:.1f}m", r["As_ms_neg_int"], r["ms_w"]),
                ]

            render_styled_table(moment_rows, headers=["Strip / Location", "Moment (ton·m)", "Strip Width (m)"])
            render_styled_table(steel_rows, headers=["Zone", "Total As_req (cm²)", "As/m (cm²/m)", "Bars / meter", "Spacing", "As_prov/m (cm²/m)"])

    render_direction(rows_x, "X-Direction (spanning across Lx spans)")
    render_direction(rows_y, "Y-Direction (spanning across Ly spans)")

    # ── 🏛️ COLUMN REACTIONS & MULTI-STOREY LOADS (ردود أفعال وتوزيع أحمال الأعمدة) ────
    col_reactions_data = []
    for c in _active_cols:
        pu_1f = c.get("Pu", 0.0)
        pu_tot = pu_1f * num_floors
        atrib = c.get("Atrib_0", 0.0)
        raw_type = c.get("type", "Interior")
        col_reactions_data.append({
            "Column ID": c["id"],
            "Orig ID": c.get("orig_id", c["id"]),
            "Grid": f"{c['grid_x']} - {c['grid_y']}",
            "Location Type": {"Interior": "داخلي (Interior)", "Edge": "طرفي / وسط خارجي (Edge)", "Corner": "ركن (Corner)"}.get(raw_type, raw_type),
            "Raw Type": raw_type,
            "Tributary Area (m²)": f"{atrib:.2f}",
            "Pu (1 Floor) [ton]": f"{pu_1f:.2f}",
            f"Total Pu ({num_floors} Floors) [ton]": f"{pu_tot:.2f}",
            "pu_1f_val": pu_1f,
            "pu_tot_val": pu_tot,
            "atrib_val": atrib,
        })

    img_reactions_b64 = None
    with st.expander(
        f"🏛️ Column Reactions & Vertical Loads — {num_floors} Floors (ردود أفعال وتوزيع أحمال الأعمدة)",
        expanded=False,
    ):
        fig_reac = generate_flat_slab_reactions_sketch(
            Lx_calc, Ly_calc, cantilevers, num_floors, Wu,
            col_reactions_data,
            col_w_cm=bc_s, col_d_cm=tc_s,
            removed_cols=_removed_col_objs,
            void_panel_ids=set(_confirmed_voids),
        )
        st.pyplot(fig_reac, use_container_width=True)
        buf_reac = io.BytesIO()
        fig_reac.savefig(buf_reac, format="png", bbox_inches="tight", dpi=300)
        buf_reac.seek(0)
        img_reactions_b64 = "data:image/png;base64," + base64.b64encode(buf_reac.getvalue()).decode("utf-8")
        buf_reac.seek(0)
        st.download_button(
            label="📥 Download Column Reactions Plan (High-Res PNG)",
            data=buf_reac,
            file_name=f"{prefix}Flat_Slab_Column_Reactions_Plan_{num_floors}Floors.png",
            mime="image/png",
            use_container_width=True,
        )
        plt.close(fig_reac)

    with st.expander(f"📊 Column Reactions Table — {num_floors} Floors (جدول ردود أفعال وتوزيع أحمال الأعمدة)", expanded=False):
        reactions_df = pd.DataFrame([
            {
                "Column ID": r["Column ID"],
                "Grid": r["Grid"],
                "Location Type": r["Location Type"],
                "Tributary Area (m²)": r["Tributary Area (m²)"],
                "Pu (1 Floor) [ton]": r["Pu (1 Floor) [ton]"],
                f"Total Pu ({num_floors} Floors) [ton]": r[f"Total Pu ({num_floors} Floors) [ton]"],
            }
            for r in col_reactions_data
        ])
        render_styled_table(reactions_df)

    # ── 📊 CLASSIFICATION INTO 3 GOVERNING COLUMN TYPES ──────────────────────
    with st.expander("📌 Governing Column Loads by Type (أقصى ردود أفعال وتصنيف نماذج الأعمدة)", expanded=False):
        int_cols = [r for r in col_reactions_data if r["Raw Type"] == "Interior"]
        edge_cols = [r for r in col_reactions_data if r["Raw Type"] == "Edge"]
        corner_cols = [r for r in col_reactions_data if r["Raw Type"] == "Corner"]

        max_int = max(int_cols, key=lambda x: x["pu_1f_val"]) if int_cols else None
        max_edge = max(edge_cols, key=lambda x: x["pu_1f_val"]) if edge_cols else None
        max_corner = max(corner_cols, key=lambda x: x["pu_1f_val"]) if corner_cols else None

        # Governing summary model table
        summary_models = []
        if max_int:
            summary_models.append({
                "Column Model (نموذج التصميم)": "C_int (أقصى عمود داخلي)",
                "Governing Column": f"{max_int['Column ID']} ({max_int['Grid']})",
                "Location Type": "داخلي (Interior)",
                "Tributary Area (m²)": f"{max_int['atrib_val']:.2f}",
                "Pu (1 Floor) [ton]": f"{max_int['pu_1f_val']:.2f}",
                f"Total Pu ({num_floors} Floors) [ton]": f"{max_int['pu_tot_val']:.2f}",
            })
        if max_edge:
            summary_models.append({
                "Column Model (نموذج التصميم)": "C_edge (أقصى عمود طرفي)",
                "Governing Column": f"{max_edge['Column ID']} ({max_edge['Grid']})",
                "Location Type": "طرفي / وسط خارجي (Edge)",
                "Tributary Area (m²)": f"{max_edge['atrib_val']:.2f}",
                "Pu (1 Floor) [ton]": f"{max_edge['pu_1f_val']:.2f}",
                f"Total Pu ({num_floors} Floors) [ton]": f"{max_edge['pu_tot_val']:.2f}",
            })
        if max_corner:
            summary_models.append({
                "Column Model (نموذج التصميم)": "C_corner (أقصى عمود ركن)",
                "Governing Column": f"{max_corner['Column ID']} ({max_corner['Grid']})",
                "Location Type": "ركن (Corner)",
                "Tributary Area (m²)": f"{max_corner['atrib_val']:.2f}",
                "Pu (1 Floor) [ton]": f"{max_corner['pu_1f_val']:.2f}",
                f"Total Pu ({num_floors} Floors) [ton]": f"{max_corner['pu_tot_val']:.2f}",
            })

        if summary_models:
            render_styled_table(summary_models)

    # ── 💾 PERSIST GOVERNING COLUMN LOADS FOR MODULE 2 ─────────────────────────
    if max_int and max_int.get("pu_1f_val", 0) > 0:
        S.cfg_set("fs_col_pu_int", float(max_int["pu_1f_val"]))
    if max_edge and max_edge.get("pu_1f_val", 0) > 0:
        S.cfg_set("fs_col_pu_edge", float(max_edge["pu_1f_val"]))
    if max_corner and max_corner.get("pu_1f_val", 0) > 0:
        S.cfg_set("fs_col_pu_corner", float(max_corner["pu_1f_val"]))

    # ── 🏛️ RECTANGULAR COLUMNS DESIGN FROM FLAT SLAB LOADS ─────────────────────
    from modules.columns import design_rectangular_column

    col_sf = S.cfg_val("col_Safety_Factor", 1.20)
    col_b_val = S.cfg_val("col_b", bc_s if bc_s else 30)
    col_H = S.cfg_val("col_H_clear", 300)
    col_K_idx = S.cfg_val("col_K_index", 1)
    K_opts = [0.50, 0.70, 1.00, 1.20, 2.00]
    col_K = K_opts[col_K_idx] if 0 <= col_K_idx < len(K_opts) else 0.70
    col_Fcu = S.cfg_val("col_Fcu", Fcu if Fcu else 250)
    col_Fy = S.cfg_val("col_Fy", Fy if Fy else 4000)
    col_Fyk = S.cfg_val("col_Fyk", 2400)
    col_mu = S.cfg_val("col_mu_target", 1.0)
    phi_opts = [12, 16, 18, 20, 25]
    col_phi_idx = S.cfg_val("col_Phi_index", 1)
    col_phi = phi_opts[col_phi_idx] if 0 <= col_phi_idx < len(phi_opts) else 16
    phi_st_opts = [6, 8, 10]
    col_phist_idx = S.cfg_val("col_Phi_st_index", 1)
    col_phi_st = phi_st_opts[col_phist_idx] if 0 <= col_phist_idx < len(phi_st_opts) else 8

    cnt_int = sum(1 for c in _active_cols if c.get("type") == "Interior")
    cnt_edge = sum(1 for c in _active_cols if c.get("type") == "Edge")
    cnt_corner = sum(1 for c in _active_cols if c.get("type") == "Corner")
    tot_active_cols = len(_active_cols)
    tot_conc_vol_1f = 0.0
    tot_main_steel_kg_1f = 0.0
    tot_stirrup_steel_kg_1f = 0.0
    tot_steel_kg_1f = 0.0
    tot_ratio_1f = 0.0
    tot_conc_vol_bld = 0.0
    tot_steel_ton_bld = 0.0
    tot_steel_kg_bld = 0.0
    cement_ton_cols = 0.0
    cement_bags_cols = 0
    gravel_m3_cols = 0.0
    sand_m3_cols = 0.0

    col_designs = []
    for model_label, col_obj, model_key in [
        ("C_int (أقصى عمود داخلي)", max_int, "C_int"),
        ("C_edge (أقصى عمود طرفي)", max_edge, "C_edge"),
        ("C_corner (أقصى عمود ركن)", max_corner, "C_corner"),
    ]:
        if col_obj and col_obj.get("pu_1f_val", 0) > 0:
            pu_1f = float(col_obj["pu_1f_val"])
            des = design_rectangular_column(
                Pu_input=pu_1f,
                Safety_Factor=col_sf,
                b=col_b_val,
                H_clear=col_H,
                K=col_K,
                Fcu=col_Fcu,
                Fy=col_Fy,
                Fyk=col_Fyk,
                mu_target=col_mu,
                Phi=col_phi,
                Phi_st=col_phi_st,
            )
            des["model_label"] = model_label
            des["model_key"] = model_key
            des["gov_col"] = f"{col_obj['Column ID']} ({col_obj['Grid']})"
            des["loc_type"] = col_obj["Location Type"]
            des["atrib"] = col_obj["atrib_val"]
            col_designs.append(des)

    if col_designs:
        with st.expander("🏛️ Rectangular Columns Design (التصميم الإنشائي لنماذج الأعمدة المستطيلة طبقاً لأحمال السقف)", expanded=False):
            st.markdown(
                """
                <div style='background:#f8fafc;border-left:4px solid #1e40af;padding:10px 14px;border-radius:6px;margin-bottom:12px;'>
                <b>📋 تصميم قطاعات وتسليح نماذج الأعمدة (ECP 203):</b><br>
                تم أخذ أقصى أحمال رأسية للدور الواحد <code>Pu (1 Floor)</code> لكل نموذج عمود (داخلي C_int، طرفي C_edge، ركن C_corner)
                وتطبيق معادلات تصميم الأعمدة المستطيلة المعرضة لقوى ضغط محورية ومطابقتها مع اشتراطات الكود المصري.
                </div>
                """,
                unsafe_allow_html=True
            )

            col_designs_table = []
            for des in col_designs:
                col_designs_table.append({
                    "نموذج العمود (Model)": des["model_label"],
                    "العمود الحاكم (Gov Col)": des["gov_col"],
                    "حمل الدور Pu_1F (t)": f"{des['Pu_input']:.2f}",
                    "حمل التصميم Pu_des (t)": f"{des['Pu_ton']:.2f}",
                    "القطاع المصمم b × t (cm)": f"{des['b']:.0f} × {des['t']:.0f}",
                    "التسليح الطولي (Main RFT)": f"{des['main_steel_str']} (μ={des['mu_provided']:.2f}%)",
                    "الكانات (Stirrups / Ties)": des["stirrups_str"],
                    "سعة التحمل Pu,cap (t)": f"{des['Pu_cap_t']:.2f}",
                    "نسبة الاستخدام (Util %)": f"{des['util_percent']:.1f} %",
                    "فحص النحافة والأمان": "✅ Safe" if des["is_safe"] else "⚠️ Review",
                })

            render_styled_table(col_designs_table)

            st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

            # 3 Detailed Cards for the 3 Column Models
            d_c1, d_c2, d_c3 = st.columns(3)
            for des, container, color_border, color_hdr in zip(
                col_designs,
                [d_c1, d_c2, d_c3],
                ["#93c5fd", "#fde68a", "#fecaca"],
                ["#1e40af", "#b45309", "#b91c1c"]
            ):
                with container:
                    st.markdown(
                        f"""
                        <div style="background:#ffffff; border:2px solid {color_border}; border-radius:10px; padding:12px 14px; text-align:center;">
                            <div style="font-size:15px; font-weight:700; color:{color_hdr}; margin-bottom:6px;">{des['model_label']}</div>
                            <div style="font-size:13px; color:#475569;">العمود: <b>{des['gov_col']}</b></div>
                            <div style="font-size:13px; color:#475569;">Pu_1F = <b>{des['Pu_input']:.1f} t</b> (Design = <b>{des['Pu_ton']:.1f} t</b>)</div>
                            <hr style="margin:8px 0; border:0; border-top:1px solid #e2e8f0;">
                            <div style="font-size:17px; font-weight:800; color:#0f172a;">{des['b']:.0f} × {des['t']:.0f} cm</div>
                            <div style="font-size:14px; font-weight:700; color:#991b1b; margin-top:2px;">{des['main_steel_str']} (μ={des['mu_provided']:.2f}%)</div>
                            <div style="font-size:13px; font-weight:600; color:#166534; margin-top:2px;">{des['stirrups_str']}</div>
                            <div style="font-size:12px; color:#64748b; margin-top:4px;">Pu,cap = {des['Pu_cap_t']:.1f} t (كفاءة {des['util_percent']:.1f}%)</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.markdown("<div style='margin-bottom:14px;'></div>", unsafe_allow_html=True)
            st.markdown("---")

            # ── 📊 حصر كميات الخرسانة والحديد لجميع أعمدة المسقط الإنشائي (Columns BOQ) ──
            cnt_int = sum(1 for c in _active_cols if c.get("type") == "Interior")
            cnt_edge = sum(1 for c in _active_cols if c.get("type") == "Edge")
            cnt_corner = sum(1 for c in _active_cols if c.get("type") == "Corner")
            tot_active_cols = len(_active_cols)

            st.markdown(
                f"##### 📊 حصر كميات الخرسانة والحديد لجميع الأعمدة في المسقط الإنشائي "
                f"({tot_active_cols} عمود: {cnt_int} داخلي + {cnt_edge} طرفي + {cnt_corner} ركن)"
            )

            des_map = {d["model_key"]: d for d in col_designs}
            col_boq_rows = []
            tot_conc_vol_1f = 0.0
            tot_main_steel_kg_1f = 0.0
            tot_stirrup_steel_kg_1f = 0.0
            tot_steel_kg_1f = 0.0

            H_m = col_H / 100.0  # column height in meters

            for m_key, m_label, count in [
                ("C_int", "C_int (أعمدة داخلية)", cnt_int),
                ("C_edge", "C_edge (أعمدة طرفية)", cnt_edge),
                ("C_corner", "C_corner (أعمدة ركن)", cnt_corner),
            ]:
                if count > 0 and m_key in des_map:
                    des = des_map[m_key]
                    b_cm = des["b"]
                    t_cm = des["t"]
                    phi_m = des["Phi"]
                    n_b = des["n_bars"]
                    phi_st = des["Phi_st"]
                    n_st_m = des["n_st_per_m"]

                    # Concrete volume for 1 column and all columns of this type (m³)
                    vol_1col = (b_cm / 100.0) * (t_cm / 100.0) * H_m
                    vol_total = vol_1col * count

                    # Main longitudinal rebar: L = H + splice (m)
                    L_bar = H_m + max(1.0, (50.0 * phi_m) / 1000.0)
                    unit_w_main = (phi_m ** 2) / 162.0
                    tot_len_main_1col = n_b * L_bar
                    w_main_1col = tot_len_main_1col * unit_w_main
                    tot_w_main = w_main_1col * count

                    # Stirrups / Ties
                    n_ties_1col = max(5, int(math.ceil(H_m * n_st_m)))
                    cov_cm = 2.5
                    tie_perim = 2.0 * (((b_cm - 2.0 * cov_cm) + (t_cm - 2.0 * cov_cm)) / 100.0) + 0.20
                    unit_w_st = (phi_st ** 2) / 162.0
                    tot_len_st_1col = n_ties_1col * tie_perim
                    w_st_1col = tot_len_st_1col * unit_w_st
                    tot_w_st = w_st_1col * count

                    # Total steel weight & ratio
                    tot_w_steel = tot_w_main + tot_w_st
                    ratio_kg_m3 = (tot_w_steel / vol_total) if vol_total > 0 else 0.0

                    tot_conc_vol_1f += vol_total
                    tot_main_steel_kg_1f += tot_w_main
                    tot_stirrup_steel_kg_1f += tot_w_st
                    tot_steel_kg_1f += tot_w_steel

                    col_boq_rows.append({
                        "نموذج العمود (Model)": m_label,
                        "العدد في المسقط (Count)": f"{count} عمود",
                        "القطاع b × t (cm)": f"{b_cm:.0f} × {t_cm:.0f}",
                        "حجم الخرسانة (m³)": f"{vol_total:.2f} m³",
                        "التسليح الرئيسي (Main Steel)": f"{n_b}Φ{phi_m} ({tot_w_main:,.1f} kg)",
                        "الكانات (Stirrups)": f"{n_st_m}Φ{phi_st}/m' ({tot_w_st:,.1f} kg)",
                        "إجمالي وزن الحديد (Ton)": f"{tot_w_steel/1000.0:.3f} Ton",
                        "معدل التسليح (kg/m³)": f"{ratio_kg_m3:.1f} kg/m³",
                    })

            # Total row
            tot_ratio_1f = (tot_steel_kg_1f / tot_conc_vol_1f) if tot_conc_vol_1f > 0 else 0.0
            col_boq_rows.append({
                "نموذج العمود (Model)": "📌 الإجمالي الكلي للأعمدة (1 Floor)",
                "العدد في المسقط (Count)": f"{tot_active_cols} عمود",
                "القطاع b × t (cm)": f"ارتفاع H = {H_m:.2f} m",
                "حجم الخرسانة (m³)": f"{tot_conc_vol_1f:.2f} m³",
                "التسليح الرئيسي (Main Steel)": f"{tot_main_steel_kg_1f:,.1f} kg ({tot_main_steel_kg_1f/1000.0:.3f} Ton)",
                "الكانات (Stirrups)": f"{tot_stirrup_steel_kg_1f:,.1f} kg ({tot_stirrup_steel_kg_1f/1000.0:.3f} Ton)",
                "إجمالي وزن الحديد (Ton)": f"{tot_steel_kg_1f/1000.0:.3f} Ton",
                "معدل التسليح (kg/m³)": f"{tot_ratio_1f:.1f} kg/m³",
            })

            # Multi-storey figures
            tot_conc_vol_bld = tot_conc_vol_1f * num_floors
            tot_steel_ton_bld = (tot_steel_kg_1f / 1000.0) * num_floors
            tot_steel_kg_bld = tot_steel_kg_1f * num_floors
            cement_ton_cols = tot_conc_vol_1f * 0.350
            cement_bags_cols = int(round(tot_conc_vol_1f * 7.0))
            gravel_m3_cols = tot_conc_vol_1f * 0.80
            sand_m3_cols = tot_conc_vol_1f * 0.40

            # ── Summary Metric Panels for Columns BOQ ──
            cb1, cb2, cb3, cb4 = st.columns(4)
            with cb1:
                st.markdown(
                    f"""
                    <div style="background:#f8fafc; border:1.5px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                        <div style="font-size:14px; font-weight:600; color:#475569; margin-bottom:4px;">إجمالي عدد الأعمدة (Columns Count)</div>
                        <div style="font-size:20px; font-weight:700; color:#1e40af;">{tot_active_cols} عمود</div>
                        <div style="font-size:12px; color:#64748b; margin-top:2px;">{cnt_int} داخلي + {cnt_edge} طرفي + {cnt_corner} ركن</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with cb2:
                st.markdown(
                    f"""
                    <div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:8px; padding:10px 14px; text-align:center;">
                        <div style="font-size:14px; font-weight:600; color:#15803d; margin-bottom:4px;">حجم خرسانة الأعمدة (Concrete Vol)</div>
                        <div style="font-size:20px; font-weight:700; color:#166534;">{tot_conc_vol_1f:.2f} m³</div>
                        <div style="font-size:12px; color:#64748b; margin-top:2px;">ولـ {num_floors} طابق: {tot_conc_vol_bld:.2f} m³</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with cb3:
                st.markdown(
                    f"""
                    <div style="background:#f5f3ff; border:1.5px solid #c4b5fd; border-radius:8px; padding:10px 14px; text-align:center;">
                        <div style="font-size:14px; font-weight:600; color:#6d28d9; margin-bottom:4px;">إجمالي وزن حديد الأعمدة (Steel Weight)</div>
                        <div style="font-size:20px; font-weight:700; color:#5b21b6;">{tot_steel_kg_1f/1000.0:.3f} Ton</div>
                        <div style="font-size:12px; color:#64748b; margin-top:2px;">{tot_steel_kg_1f:,.1f} kg (ولـ {num_floors} طابق: {tot_steel_ton_bld:.3f} Ton)</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with cb4:
                st.markdown(
                    f"""
                    <div style="background:#eff6ff; border:1.5px solid #93c5fd; border-radius:8px; padding:10px 14px; text-align:center;">
                        <div style="font-size:14px; font-weight:600; color:#1e40af; margin-bottom:4px;">معدل التسليح للأعمدة (Steel Ratio)</div>
                        <div style="font-size:20px; font-weight:700; color:#1e3a8a;">{tot_ratio_1f:.1f} kg/m³</div>
                        <div style="font-size:12px; color:#64748b; margin-top:2px;">متوسط نسبة التسليح لخرسانة الأعمدة</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
            render_styled_table(col_boq_rows)

            st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

            # ── Concrete Raw Materials Panels for Columns ──
            st.markdown("###### 🧱 المواد الأولية المطلوبة لصب خرسانة الأعمدة (Concrete Materials for Columns):")
            cm1, cm2, cm3, cm4 = st.columns(4)
            with cm1:
                st.markdown(
                    f"""
                    <div style="background:#eff6ff; border:1.5px solid #93c5fd; border-radius:8px; padding:8px 12px; text-align:center;">
                        <div style="font-size:13px; font-weight:600; color:#1e40af;">كمية الأسمنت للأعمدة</div>
                        <div style="font-size:18px; font-weight:700; color:#1e3a8a;">{cement_ton_cols:.2f} Ton</div>
                        <div style="font-size:11.5px; color:#64748b;">{cement_bags_cols} شكارة (بمعدل 350 kg/m³)</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with cm2:
                st.markdown(
                    f"""
                    <div style="background:#fffbeb; border:1.5px solid #fde68a; border-radius:8px; padding:8px 12px; text-align:center;">
                        <div style="font-size:13px; font-weight:600; color:#b45309;">كمية الزلط للأعمدة</div>
                        <div style="font-size:18px; font-weight:700; color:#92400e;">{gravel_m3_cols:.2f} m³</div>
                        <div style="font-size:11.5px; color:#64748b;">بمعدل 0.80 m³ لكل م³ خرسانة</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with cm3:
                st.markdown(
                    f"""
                    <div style="background:#fef2f2; border:1.5px solid #fecaca; border-radius:8px; padding:8px 12px; text-align:center;">
                        <div style="font-size:13px; font-weight:600; color:#b91c1c;">كمية الرمل للأعمدة</div>
                        <div style="font-size:18px; font-weight:700; color:#991b1b;">{sand_m3_cols:.2f} m³</div>
                        <div style="font-size:11.5px; color:#64748b;">بمعدل 0.40 m³ لكل م³ خرسانة</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with cm4:
                st.markdown(
                    f"""
                    <div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:8px; padding:8px 12px; text-align:center;">
                        <div style="font-size:13px; font-weight:600; color:#15803d;">إجمالي وزن الحديد الكامل</div>
                        <div style="font-size:18px; font-weight:700; color:#166534;">{tot_steel_kg_1f/1000.0:.3f} Ton</div>
                        <div style="font-size:11.5px; color:#64748b;">رئيسي: {tot_main_steel_kg_1f/1000.0:.2f}t | كانات: {tot_stirrup_steel_kg_1f/1000.0:.2f}t</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── 💰 BILL OF QUANTITIES (BOQ) ESTIMATE ─────────────────────────────────
    with st.expander("💰 Material Take-off & BoQ Estimate (جدول حصر الكميات المبدئي)", expanded=False):
        bq1, bq2, bq3, bq4 = st.columns(4)
        with bq1:
            st.markdown(
                f"""
                <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Total Slab Area</div>
                    <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{boq['slab_area_m2']:.1f} m²</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with bq2:
            st.markdown(
                f"""
                <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Concrete Volume</div>
                    <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{boq['concrete_vol_m3']:.2f} m³</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with bq3:
            st.markdown(
                f"""
                <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Total Steel Weight</div>
                    <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{boq['total_steel_ton']:.2f} Ton</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with bq4:
            st.markdown(
                f"""
                <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Steel Ratio</div>
                    <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{boq['steel_ratio_kg_m3']:.1f} kg/m³</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

        # ── Table 1: Detailed Items Breakdown (جدول حصر بنود حديد التسليح والمواد) ──
        st.markdown("##### 📋 1. جدول حصر بنود حديد التسليح والمواد (Reinforcement & Material Breakdown)")
        items_table_data = []
        for item in boq.get("items", []):
            items_table_data.append({
                "بند حديد التسليح / المادة (Material Component)": item["item_name"],
                "قطر الحديد Φ (Bar Dia)": item["dia_str"],
                "الكمية (Quantity)": item["qty_str"],
                "إجمالي الطول (Total Length)": item["length_str"],
                "المواصفات والملاحظات الإنشائية (Specification / Detailing Notes)": item["spec"],
            })
        render_styled_table(items_table_data)

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        # ── Table 2: Final Totals by Bar Diameter & Grand Total (جدول إجمالي الكمية لكل قطر والإجمالي العام) ──
        st.markdown("##### 📊 2. جدول إجمالي كميات الحديد لكل قطر والإجمالي الكلي (Total Quantities by Bar Diameter & Grand Total)")
        dia_table_data = []
        for dia_row in boq.get("by_dia", []):
            dia_table_data.append({
                "قطر السيخ Φ (Bar Dia)": dia_row["dia_str"],
                "وزن المتر الطولي (kg/m')": f"{dia_row['unit_w_kg_m']:.3f}",
                "إجمالي الطول (m')": dia_row["length_str"],
                "إجمالي الوزن (kg)": dia_row["weight_kg_str"],
                "إجمالي الوزن (Ton)": dia_row["weight_ton_str"],
                "النسبة المئوية (%)": dia_row.get("percent_str", ""),
                "الاستخدام الإنشائي في السقف (Applications in Slab)": dia_row.get("apps", "—"),
            })

        # Add prominent Grand Total Row
        dia_table_data.append({
            "قطر السيخ Φ (Bar Dia)": "📌 الإجمالي الكلي لحديد التسليح (Grand Total Rebar)",
            "وزن المتر الطولي (kg/m')": "—",
            "إجمالي الطول (m')": f"{boq.get('total_steel_len_m', 0.0):,.1f} m'",
            "إجمالي الوزن (kg)": f"{boq.get('total_steel_kg', 0.0):,.1f} kg",
            "إجمالي الوزن (Ton)": f"{boq.get('total_steel_ton', 0.0):.3f} Ton",
            "النسبة المئوية (%)": "100.0 %",
            "الاستخدام الإنشائي في السقف (Applications in Slab)": f"معدل الاستهلاك: {boq.get('steel_ratio_kg_m3', 0.0):.1f} kg/m³ خرسانة",
        })

        render_styled_table(dia_table_data)

        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

        # ── Grand Total Rebar Metric Panels (بانيل الإجمالي الكلي لحديد التسليح) ──
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1:
            st.markdown(
                f"""
                <div style="background:#f5f3ff; border:1.5px solid #c4b5fd; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:14px; font-weight:600; color:#6d28d9; margin-bottom:4px;">إجمالي وزن الحديد (Total Steel)</div>
                    <div style="font-size:20px; font-weight:700; color:#5b21b6;">{boq.get('total_steel_ton', 0.0):.3f} Ton</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">{boq.get('total_steel_kg', 0.0):,.1f} kg</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with rc2:
            st.markdown(
                f"""
                <div style="background:#eff6ff; border:1.5px solid #93c5fd; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:14px; font-weight:600; color:#1e40af; margin-bottom:4px;">إجمالي أطوال الأسياخ (Total Length)</div>
                    <div style="font-size:20px; font-weight:700; color:#1e3a8a;">{boq.get('total_steel_len_m', 0.0):,.1f} m'</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">مجموع أطوال كافة الأقطار</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with rc3:
            st.markdown(
                f"""
                <div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:14px; font-weight:600; color:#15803d; margin-bottom:4px;">معدل التسليح للخرسانة (Steel Ratio)</div>
                    <div style="font-size:20px; font-weight:700; color:#166534;">{boq.get('steel_ratio_kg_m3', 0.0):.1f} kg/m³</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">نسبة الحديد لحجم الخرسانة</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with rc4:
            st.markdown(
                f"""
                <div style="background:#fffbeb; border:1.5px solid #fde68a; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:14px; font-weight:600; color:#b45309; margin-bottom:4px;">معدل التسليح للمسطح (Per Area)</div>
                    <div style="font-size:20px; font-weight:700; color:#92400e;">{(boq.get('total_steel_kg', 0.0)/boq['slab_area_m2']) if boq.get('slab_area_m2') else 0:.1f} kg/m²</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">لكل م² من مسطح السقف</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom:14px;'></div>", unsafe_allow_html=True)

        # ── 🧱 3. جدول حصر كميات الخرسانة والمواد الأولية (Concrete & Raw Materials) ──
        st.markdown("##### 🧱 3. جدول حصر كميات الخرسانة والمواد الأولية (Concrete & Raw Materials Estimate)")

        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.markdown(
                f"""
                <div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:14px; font-weight:600; color:#15803d; margin-bottom:4px;">حجم الخرسانة المسلحة (Concrete)</div>
                    <div style="font-size:20px; font-weight:700; color:#166534;">{boq['concrete_vol_m3']:.2f} m³</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">مسطح {boq['slab_area_m2']:.1f} m² × سمك {ts:.0f} cm</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with mc2:
            st.markdown(
                f"""
                <div style="background:#eff6ff; border:1.5px solid #93c5fd; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:14px; font-weight:600; color:#1e40af; margin-bottom:4px;">كمية الأسمنت (Cement)</div>
                    <div style="font-size:20px; font-weight:700; color:#1e3a8a;">{boq['cement_ton']:.2f} Ton</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">{boq['cement_bags']} شكارة ({boq['cement_content_kg_m3']:.0f} kg/m³)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with mc3:
            st.markdown(
                f"""
                <div style="background:#fffbeb; border:1.5px solid #fde68a; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:14px; font-weight:600; color:#b45309;">كمية الزلط (Gravel)</div>
                    <div style="font-size:20px; font-weight:700; color:#92400e;">{boq['gravel_m3']:.2f} m³</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">بمعدل 0.80 m³ لكل 1 m³ خرسانة</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with mc4:
            st.markdown(
                f"""
                <div style="background:#fef2f2; border:1.5px solid #fecaca; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:14px; font-weight:600; color:#b91c1c;">كمية الرمل (Sand)</div>
                    <div style="font-size:20px; font-weight:700; color:#991b1b;">{boq['sand_m3']:.2f} m³</div>
                    <div style="font-size:12px; color:#475569; margin-top:2px;">بمعدل 0.40 m³ لكل 1 m³ خرسانة</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

        concrete_mat_df = pd.DataFrame([
            {
                "المادة / المكون الإنشائي (Material Component)": "1. الخرسانة المسلحة الجاهزة (Reinforced Concrete Volume)",
                "الكمية المحسوبة (Quantity)": f"{boq['concrete_vol_m3']:.2f} m³",
                "الوحدة (Unit)": "متر مكعب (m³)",
                "معدل الخلط / النسب المعيارية (Mix Proportion / Standard)": f"مسطح البلاطة الصافي: {boq['slab_area_m2']:.1f} m² × سمك {ts:.0f} cm",
                "ملاحظات التنفيذ والتوريد (Procurement & Site Notes)": f"رتبة الخرسانة المطلوبة Fcu = {Fcu:.0f} kg/cm² (صب بالمضخة Pump)",
            },
            {
                "المادة / المكون الإنشائي (Material Component)": "2. الأسمنت البورتلاندي العادي (Ordinary Portland Cement)",
                "الكمية المحسوبة (Quantity)": f"{boq['cement_ton']:.2f} Ton ({boq['cement_kg']:,.0f} kg)",
                "الوحدة (Unit)": "طن (Ton) / شكارة (Bag)",
                "معدل الخلط / النسب المعيارية (Mix Proportion / Standard)": f"{boq['cement_content_kg_m3']:.0f} kg/m³ ({boq['cement_content_kg_m3']/50:.0f} شكاير / م³ خرسانة)",
                "ملاحظات التنفيذ والتوريد (Procurement & Site Notes)": f"إجمالي عدد الشكائر: {boq['cement_bags']:,} شكارة (وزن الشكارة 50 كجم)",
            },
            {
                "المادة / المكون الإنشائي (Material Component)": "3. الزلط / الركام الكبير (Gravel / Coarse Aggregate)",
                "الكمية المحسوبة (Quantity)": f"{boq['gravel_m3']:.2f} m³",
                "الوحدة (Unit)": "متر مكعب (m³)",
                "معدل الخلط / النسب المعيارية (Mix Proportion / Standard)": "0.80 m³ زلط لكل 1.0 m³ خرسانة مسلحة",
                "ملاحظات التنفيذ والتوريد (Procurement & Site Notes)": "زلط نظيف متدرج الحبيبات خالٍ من الشوائب والمواد العضوية",
            },
            {
                "المادة / المكون الإنشائي (Material Component)": "4. الرمل الحرش / الركام الصغير (Clean Coarse Sand)",
                "الكمية المحسوبة (Quantity)": f"{boq['sand_m3']:.2f} m³",
                "الوحدة (Unit)": "متر مكعب (m³)",
                "معدل الخلط / النسب المعيارية (Mix Proportion / Standard)": "0.40 m³ رمل لكل 1.0 m³ خرسانة مسلحة (نصف حجم الزلط)",
                "ملاحظات التنفيذ والتوريد (Procurement & Site Notes)": "رمل حرش نظيف متدرج خالٍ من الطفلة والأملاح الضارة",
            },
            {
                "المادة / المكون الإنشائي (Material Component)": "5. مياه الخلط التقريبية (Mixing Water)",
                "الكمية المحسوبة (Quantity)": f"{boq['water_liters']:,.0f} لتر ({boq['water_liters']/1000:.2f} m³)",
                "الوحدة (Unit)": "لتر (Liters) / متر مكعب (m³)",
                "معدل الخلط / النسب المعيارية (Mix Proportion / Standard)": f"175 لتر / م³ (نسبة مياه/أسمنت w/c ≈ 0.50)",
                "ملاحظات التنفيذ والتوريد (Procurement & Site Notes)": "مياه صالحة للشرب وخالية من الشوائب والزيوت",
            },
        ])
        render_styled_table(concrete_mat_df)

    # ── 🏆 FINAL SURVEY FOR COLUMNS & ROOF (الحصر النهائي للسقف والأعمدة) ───────────
    slab_conc_1f = boq.get("concrete_vol_m3", 0.0)
    slab_steel_kg_1f = boq.get("total_steel_kg", 0.0)
    slab_steel_ton_1f = boq.get("total_steel_ton", 0.0)
    slab_cement_ton_1f = boq.get("cement_ton", 0.0)
    slab_cement_bags_1f = boq.get("cement_bags", 0)
    slab_gravel_1f = boq.get("gravel_m3", 0.0)
    slab_sand_1f = boq.get("sand_m3", 0.0)
    slab_ratio_1f = boq.get("steel_ratio_kg_m3", 0.0)

    cols_conc_1f = tot_conc_vol_1f
    cols_steel_kg_1f = tot_steel_kg_1f
    cols_steel_ton_1f = tot_steel_kg_1f / 1000.0
    cols_cement_ton_1f = cement_ton_cols
    cols_cement_bags_1f = cement_bags_cols
    cols_gravel_1f = gravel_m3_cols
    cols_sand_1f = sand_m3_cols
    cols_ratio_1f = tot_ratio_1f

    comb_conc_1f = slab_conc_1f + cols_conc_1f
    comb_steel_kg_1f = slab_steel_kg_1f + cols_steel_kg_1f
    comb_steel_ton_1f = slab_steel_ton_1f + cols_steel_ton_1f
    comb_cement_ton_1f = slab_cement_ton_1f + cols_cement_ton_1f
    comb_cement_bags_1f = slab_cement_bags_1f + cols_cement_bags_1f
    comb_gravel_1f = slab_gravel_1f + cols_gravel_1f
    comb_sand_1f = slab_sand_1f + cols_sand_1f
    comb_ratio_1f = (comb_steel_kg_1f / comb_conc_1f) if comb_conc_1f > 0 else 0.0

    # Multi-storey figures
    comb_conc_bld = comb_conc_1f * num_floors
    comb_steel_ton_bld = comb_steel_ton_1f * num_floors
    comb_steel_kg_bld = comb_steel_kg_1f * num_floors
    comb_cement_ton_bld = comb_cement_ton_1f * num_floors
    comb_cement_bags_bld = comb_cement_bags_1f * num_floors
    comb_gravel_bld = comb_gravel_1f * num_floors
    comb_sand_bld = comb_sand_1f * num_floors

    with st.expander("🏆 Final Survey for Columns & Roof (الحصر النهائي للسقف والأعمدة)", expanded=False):
        st.markdown(
            f"""
            <div style='background:#f8fafc; border-left:4px solid #0284c7; padding:10px 14px; border-radius:6px; margin-bottom:12px;'>
                <b>📊 الحصر الشامل والنهائي لجميع المواد الإنشائية (Total Material Take-off & Survey):</b><br>
                يجمع هذا القسم كافة الكميات والمواد المستهلكة في <b>البلاطة اللاكمرية (السقف)</b> بالإضافة إلى <b>كامل الأعمدة الخرسانية ({tot_active_cols} عمود)</b> للدور الواحد ولإجمالي كامل المبنى (<b>{num_floors} طوابق</b>).
            </div>
            """,
            unsafe_allow_html=True
        )

        # ── KPI Summary Cards ──
        fs_c1, fs_c2, fs_c3, fs_c4 = st.columns(4)
        with fs_c1:
            st.markdown(
                f"""
                <div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:13px; font-weight:600; color:#15803d; margin-bottom:4px;">إجمالي حجم الخرسانة المسلحة</div>
                    <div style="font-size:19.5px; font-weight:700; color:#166534;">{comb_conc_1f:.2f} m³</div>
                    <div style="font-size:11.5px; color:#475569; margin-top:2px;">ولـ {num_floors} طابق: <b>{comb_conc_bld:.2f} m³</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with fs_c2:
            st.markdown(
                f"""
                <div style="background:#f5f3ff; border:1.5px solid #c4b5fd; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:13px; font-weight:600; color:#6d28d9; margin-bottom:4px;">إجمالي وزن حديد التسليح</div>
                    <div style="font-size:19.5px; font-weight:700; color:#5b21b6;">{comb_steel_ton_1f:.3f} Ton</div>
                    <div style="font-size:11.5px; color:#475569; margin-top:2px;">ولـ {num_floors} طابق: <b>{comb_steel_ton_bld:.3f} Ton</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with fs_c3:
            st.markdown(
                f"""
                <div style="background:#eff6ff; border:1.5px solid #93c5fd; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:13px; font-weight:600; color:#1e40af; margin-bottom:4px;">إجمالي كمية الأسمنت</div>
                    <div style="font-size:19.5px; font-weight:700; color:#1e3a8a;">{comb_cement_ton_1f:.2f} Ton</div>
                    <div style="font-size:11.5px; color:#475569; margin-top:2px;">{comb_cement_bags_1f:,} شكارة (ولـ {num_floors} طابق: <b>{comb_cement_ton_bld:.2f} t</b>)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with fs_c4:
            st.markdown(
                f"""
                <div style="background:#fffbeb; border:1.5px solid #fde68a; border-radius:8px; padding:10px 14px; text-align:center;">
                    <div style="font-size:13px; font-weight:600; color:#b45309; margin-bottom:4px;">متوسط معدل التسليح الإجمالي</div>
                    <div style="font-size:19.5px; font-weight:700; color:#92400e;">{comb_ratio_1f:.1f} kg/m³</div>
                    <div style="font-size:11.5px; color:#475569; margin-top:2px;">زلط: {comb_gravel_1f:.1f} m³ | رمل: {comb_sand_1f:.1f} m³</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        # ── Table: إجماليات وتفصيل مواد البلاطات والأعمدة والإجمالي الموحد ──
        st.markdown("##### 📋 جدول تفصيل وإجماليات المواد لكل عنصر إنشائي (Slab & Columns Materials Breakdown):")
        elements_breakdown_data = [
            {
                "العنصر الإنشائي (Structural Element)": f"1. سقف البلاطة اللاكمرية (Flat Slab ts={ts:.0f}cm)",
                "حجم الخرسانة (m³)": f"{slab_conc_1f:.2f} m³",
                "وزن الحديد (Ton)": f"{slab_steel_ton_1f:.3f} Ton",
                "وزن الحديد (kg)": f"{slab_steel_kg_1f:,.1f} kg",
                "الأسمنت (Ton)": f"{slab_cement_ton_1f:.2f} Ton",
                "الأسمنت (شكارة 50kg)": f"{slab_cement_bags_1f:,} شكارة",
                "الزلط (m³)": f"{slab_gravel_1f:.2f} m³",
                "الرمل (m³)": f"{slab_sand_1f:.2f} m³",
                "معدل التسليح (kg/m³)": f"{slab_ratio_1f:.1f} kg/m³",
            },
            {
                "العنصر الإنشائي (Structural Element)": f"2. أعمدة المسقط الإنشائي ({tot_active_cols} عمود)",
                "حجم الخرسانة (m³)": f"{cols_conc_1f:.2f} m³",
                "وزن الحديد (Ton)": f"{cols_steel_ton_1f:.3f} Ton",
                "وزن الحديد (kg)": f"{cols_steel_kg_1f:,.1f} kg",
                "الأسمنت (Ton)": f"{cols_cement_ton_1f:.2f} Ton",
                "الأسمنت (شكارة 50kg)": f"{cols_cement_bags_1f:,} شكارة",
                "الزلط (m³)": f"{cols_gravel_1f:.2f} m³",
                "الرمل (m³)": f"{cols_sand_1f:.2f} m³",
                "معدل التسليح (kg/m³)": f"{cols_ratio_1f:.1f} kg/m³",
            },
            {
                "العنصر الإنشائي (Structural Element)": "📌 الإجمالي الموحد للدور الواحد (Total 1 Floor)",
                "حجم الخرسانة (m³)": f"{comb_conc_1f:.2f} m³",
                "وزن الحديد (Ton)": f"{comb_steel_ton_1f:.3f} Ton",
                "وزن الحديد (kg)": f"{comb_steel_kg_1f:,.1f} kg",
                "الأسمنت (Ton)": f"{comb_cement_ton_1f:.2f} Ton",
                "الأسمنت (شكارة 50kg)": f"{comb_cement_bags_1f:,} شكارة",
                "الزلط (m³)": f"{comb_gravel_1f:.2f} m³",
                "الرمل (m³)": f"{comb_sand_1f:.2f} m³",
                "معدل التسليح (kg/m³)": f"{comb_ratio_1f:.1f} kg/m³",
            },
            {
                "العنصر الإنشائي (Structural Element)": f"🏢 الإجمالي لكامل المبنى ({num_floors} طوابق)",
                "حجم الخرسانة (m³)": f"{comb_conc_bld:.2f} m³",
                "وزن الحديد (Ton)": f"{comb_steel_ton_bld:.3f} Ton",
                "وزن الحديد (kg)": f"{comb_steel_kg_bld:,.1f} kg",
                "الأسمنت (Ton)": f"{comb_cement_ton_bld:.2f} Ton",
                "الأسمنت (شكارة 50kg)": f"{comb_cement_bags_bld:,} شكارة",
                "الزلط (m³)": f"{comb_gravel_bld:.2f} m³",
                "الرمل (m³)": f"{comb_sand_bld:.2f} m³",
                "معدل التسليح (kg/m³)": f"{comb_ratio_1f:.1f} kg/m³",
            },
        ]
        render_styled_table(elements_breakdown_data)

    st.markdown("---")

    # ── 💾 SAVE & EXPORT COMPLETE CALCULATION SHEET ────────────────────────────
    st.markdown(
        '<div class="section-header">💾 Save & Export Design Calculation Sheet (حفظ وتصدير المذكرة الحسابية الكاملة)</div>',
        unsafe_allow_html=True,
    )

    from modules.report_generator import generate_flat_slab_report_html, html_to_pdf_bytes

    # Ensure moment contour images are generated for the comprehensive report
    if img_m11_b64 is None and img_dual_moment_b64 is None:
        _fig_m11_rep = generate_flat_slab_moment_contour(
            Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
            mode="M11", col_w_cm=bc_s, col_d_cm=tc_s,
            removed_cols=_removed_col_objs, void_panel_ids=set(_confirmed_voids),
            top_extra_cols=top_extra_cols, btm_extra_spans=btm_extra_spans,
        )
        _buf = io.BytesIO()
        _fig_m11_rep.savefig(_buf, format="png", bbox_inches="tight", dpi=180)
        _buf.seek(0)
        img_m11_b64 = "data:image/png;base64," + base64.b64encode(_buf.getvalue()).decode("utf-8")
        plt.close(_fig_m11_rep)

    if img_m22_b64 is None and img_dual_moment_b64 is None:
        _fig_m22_rep = generate_flat_slab_moment_contour(
            Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
            mode="M22", col_w_cm=bc_s, col_d_cm=tc_s,
            removed_cols=_removed_col_objs, void_panel_ids=set(_confirmed_voids),
            top_extra_cols=top_extra_cols, btm_extra_spans=btm_extra_spans,
        )
        _buf = io.BytesIO()
        _fig_m22_rep.savefig(_buf, format="png", bbox_inches="tight", dpi=180)
        _buf.seek(0)
        img_m22_b64 = "data:image/png;base64," + base64.b64encode(_buf.getvalue()).decode("utf-8")
        plt.close(_fig_m22_rep)

    report_html = generate_flat_slab_report_html(
        project_name="Flat Slab Reinforced Concrete Design (ECP 203)",
        ts=ts,
        d=d,
        num_floors=num_floors,
        Wu=Wu,
        Lx_spans=Lx_calc,
        Ly_spans=Ly_calc,
        cantilevers=cantilevers,
        mesh_btm_str=mesh_btm_str,
        mesh_top_str=mesh_top_str,
        prov_btm_mesh_cm2m=prov_btm_mesh_cm2m,
        prov_top_mesh_cm2m=prov_top_mesh_cm2m,
        Fcu=Fcu,
        Fy=Fy,
        SDL=SDL,
        wall_load=wall_load,
        LL=LL,
        bc=bc_s,
        tc=tc_s,
        boq=boq,
        top_extra_cols=top_extra_cols,
        btm_extra_spans=btm_extra_spans,
        punching_results=punching_results,
        all_punching_safe=all_safe,
        col_reactions_data=col_reactions_data,
        summary_models=summary_models,
        img_verif_b64=img_verif_b64,
        img_top_rft_b64=img_top_b64,
        img_btm_rft_b64=img_btm_b64,
        img_reactions_b64=img_reactions_b64,
        img_m11_b64=img_m11_b64,
        img_m22_b64=img_m22_b64,
        img_dual_moment_b64=img_dual_moment_b64,
    )

    pdf_bytes = html_to_pdf_bytes(report_html)

    c_save1, c_save2 = st.columns([3, 1])
    with c_save1:
        st.markdown(
            f"""
            <div style='background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:14px 16px;'>
                <div style='font-weight:700; color:#1e293b; font-size:1.0rem;'>
                    📄 ملف المذكرة الحسابية الهندسية الشاملة (ECP 203 Calculation Sheet)
                </div>
                <div style='font-size:0.88rem; color:#64748b; margin-top:2px;'>
                    يتضمن جميع المدخلات، والمخططات الهندسية عالية الدقة، وفحوصات القص الثاقب، وردود أفعال وتصنيفات الأعمدة لـ <b>{num_floors} طوابق</b>، وحصر الكميات.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c_save2:
        st.download_button(
            label="🌐 Save Calculation Sheet (HTML)",
            data=report_html,
            file_name=f"{prefix}ECP203_Flat_Slab_Calculation_Sheet_ts{ts:.0f}cm_{num_floors}Floors.html",
            mime="text/html",
            use_container_width=True,
        )
        if pdf_bytes:
            st.download_button(
                label="📕 Save as PDF (مباشر)",
                data=pdf_bytes,
                file_name=f"{prefix}ECP203_Flat_Slab_Calculation_Sheet_ts{ts:.0f}cm_{num_floors}Floors.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    st.markdown("---")

    # ── Final Info Summary ────────────────────────────────────────────────────
    st.info(
        f"📐 **Design Complete:** Flat Slab ts = {ts:.0f} cm  │  Floors: {num_floors}  │  Bottom Mesh: {mesh_btm_str}  │  "
        f"Top Mesh: {mesh_top_str}  │  Wu = {Wu:.3f} t/m²  │  "
        f"Concrete: {boq['concrete_vol_m3']:.1f} m³  │  Steel: {boq['total_steel_ton']:.2f} Ton ({boq['steel_ratio_kg_m3']:.0f} kg/m³)"
    )
