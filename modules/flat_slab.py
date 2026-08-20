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
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from modules import settings as S


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
    top_mesh_dia=10,
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
        ("Bottom Mesh (B1, B2)", f"Φ {bottom_mesh_dia} mm", "#1d4ed8"),
        ("Top Mesh (T1, T2)", f"Φ {top_mesh_dia} mm", "#1d4ed8"),
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
):
    """
    Generate the full-width engineering Bottom Reinforcement Drawing (المخطط الإنشائي للحديد السفلي).
    - Bottom Mesh (الشبكة السفلية الأساسية B1, B2).
    - Bottom Extra Steel in Enlarged / High-Moment Bays in Blue (🔵) with hatched zones & callouts.
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

    fig.suptitle(
        f"BOTTOM REINFORCEMENT & STRUCTURAL LAYOUT PLAN (المخطط الإنشائي للحديد السفلي والإضافي في الباكيات — ts = {ts_cm:.0f} cm)",
        fontsize=20, weight="bold", y=0.98, color="#0f172a"
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


def calculate_boq(Lx_spans, Ly_spans, cantilevers, ts_cm, mesh_btm_n, mesh_btm_dia, mesh_top_n, mesh_top_dia, col_extras, cant_rft_list, btm_extra_spans=None, void_panels=None):
    """
    Calculate comprehensive Bill of Quantities (BoQ) for Concrete and Steel,
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

    return {
        "slab_area_m2": slab_area,
        "concrete_vol_m3": concrete_vol,
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
        '<div class="section-header">🟦 Module 1 – Flat Slab Design '
        '(ECP 203 – Direct Design Method | Dynamic Multi-Span)</div>',
        unsafe_allow_html=True,
    )

    Lx_spans = []
    Ly_spans = []
    cantilevers = {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0}

    # ── ① GEOMETRY INPUTS ────────────────────────────────────────────────────
    with st.expander("📐 Step 1 — Grid Geometry & Cantilevers", expanded=True):
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
    with st.expander("🧱 Step 2 — Slab Thickness, Column Size, Loads & Rebar Diameters", expanded=True):
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
            top_mesh_dia    = S.selectbox("Top Mesh Φ",    "slab_top_mesh_dia_idx",    options=BAR_DIA)
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
    st.markdown(
        '<div class="section-header">🗺️ Structural Geometry Sketch – Verification</div>',
        unsafe_allow_html=True,
    )

    # ── ⑤  COLUMN & PANEL / VOID REMOVAL STATE MACHINE ───────────────────────
    # Keys used in session_state (NOT in cfg — state is session-local but
    # the confirmed removal lists ARE persisted to cfg / user_settings.json).
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

    # ── 5d. Draw Verification Sketch (always shown, reflects current state) ──
    col_w_for_sketch = _bc_col
    col_d_for_sketch = _tc_col
    fig_verif = generate_flat_slab_sketch(
        Lx_spans, Ly_spans, cantilevers,
        ts_initial=ts_initial if ts_initial is not None else 20,
        n_floors=num_floors,
        bottom_mesh_dia=bottom_mesh_dia if bottom_mesh_dia is not None else 12,
        top_mesh_dia=top_mesh_dia if top_mesh_dia is not None else 10,
        col_extra_dia=col_extra_dia if col_extra_dia is not None else 12,
        strip_top_extra_dia=strip_top_extra_dia if strip_top_extra_dia is not None else 12,
        strip_bottom_extra_dia=strip_bottom_extra_dia if strip_bottom_extra_dia is not None else 12,
        concrete_cover=cov if cov is not None else 1.5,
        fcu=Fcu if Fcu is not None else 250,
        fy=Fy if Fy is not None else 4000,
        live_load=LL if LL is not None else 0.25,
        flooring_load=SDL if SDL is not None else 0.15,
        wall_load=wall_load if wall_load is not None else 0.50,
        col_w_cm=col_w_for_sketch,
        col_d_cm=col_d_for_sketch,
        removed_col_ids=set(_confirmed_removals),
        pending_col_ids=set(st.session_state.get("_fs_pending_snapshot", [])
                            if st.session_state.get("_fs_show_confirm") else _pending_removals),
        void_panel_ids=set(_confirmed_voids),
        pending_void_ids=set(st.session_state.get("_fs_pending_void_snapshot", [])
                             if st.session_state.get("_fs_show_void_confirm") else _pending_voids),
    )
    st.pyplot(fig_verif, use_container_width=True)
    buf_v = io.BytesIO()
    fig_verif.savefig(buf_v, format="png", bbox_inches="tight", dpi=300)
    buf_v.seek(0)
    img_verif_b64 = "data:image/png;base64," + base64.b64encode(buf_v.getvalue()).decode("utf-8")
    buf_v.seek(0)
    st.download_button(
        label="📥 Download Structural Geometry Sketch (High-Res PNG)",
        data=buf_v,
        file_name="Flat_Slab_Geometry_Verification.png",
        mime="image/png",
        use_container_width=True,
    )
    plt.close(fig_verif)

    # ── Geometry summary pills (Unified 1.3x font size: 15px label / 19.5px value) ────
    n_total_cols  = (len(Lx_spans) + 1) * (len(Ly_spans) + 1)
    n_active_cols = len(_active_cols)
    tot_w_val = sum(Lx_spans) + cant_left + cant_right
    tot_h_val = sum(Ly_spans) + cant_bottom + cant_top

    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Total Width (X-dir)</div>
                <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{tot_w_val:.2f} m</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with g2:
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Total Height (Y-dir)</div>
                <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{tot_h_val:.2f} m</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with g3:
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">No. of Columns</div>
                <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{n_active_cols} active / {n_total_cols} total</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with g4:
        n_p_total = len(_all_panels)
        n_p_active = len(_active_panels)
        n_p_voids = len(_void_panels)
        p_val_str = f"{n_p_active} active / {n_p_total} total" if not n_p_voids else f"{n_p_active} act / {n_p_voids} voids"
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">No. of Panels</div>
                <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{p_val_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── 5e. Column Removal Panel ─────────────────────────────────────────────
    with st.expander(
        f"🗑️ Column Removal & Re-indexing (تعديل وحذف الأعمدة) "
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
        f"🏛️ Columns Labeling & Grid Registry "
        f"({len(_active_cols)} active columns — "
        f"{len(_confirmed_removals)} removed)",
        expanded=False,
    ):
        st.dataframe(_registry_df, use_container_width=True, hide_index=True)
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

    As_min_req_m = 0.0018 * 100.0 * ts
    n_mesh_btm = max(5, math.ceil(As_min_req_m / bar_area(bottom_mesh_dia)))
    prov_btm_mesh_cm2m = n_mesh_btm * bar_area(bottom_mesh_dia)
    mesh_btm_str = f"{n_mesh_btm} Φ{bottom_mesh_dia} / m'"

    n_mesh_top = 5
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

    # 3. Detect and calculate Enlarged Bays in X-direction
    for j, y in enumerate(y_coords):
        row_active = [c for c in _active_cols if c["j"] == j]
        row_active.sort(key=lambda c: c["x"])
        if len(row_active) >= 2:
            if j == 0:
                L_perp = cant_B + Ly_spans[0] / 2.0
            elif j == n_yj - 1:
                L_perp = Ly_spans[-1] / 2.0 + cant_T
            else:
                L_perp = (Ly_spans[j-1] + Ly_spans[j]) / 2.0

            for k in range(len(row_active) - 1):
                c_left = row_active[k]
                c_right = row_active[k+1]
                span_len = c_right["x"] - c_left["x"]
                Ln = span_len - bc_m
                all_Ln.append(Ln)
                is_enlarged = (c_right["i"] - c_left["i"]) > 1

                Mo = Wu * L_perp * (Ln ** 2) / 8.0
                M_pos = (0.50 if is_enlarged else 0.35) * Mo
                w_cs = min(span_len, L_perp) / 2.0
                M_cs_pos = 0.60 * M_pos
                As_cs_req = calc_As(M_cs_pos, w_cs, d, Fcu, Fy, ts)
                As_cs_m = As_cs_req / w_cs
                delta_As = max(0.0, As_cs_m - prov_btm_mesh_cm2m)

                if delta_As > 0.05 or is_enlarged:
                    a_bar = bar_area(strip_bottom_extra_dia)
                    n_b = max(2, math.ceil((delta_As * w_cs) / a_bar)) if delta_As > 0.05 else 0
                    L_ext = round(0.70 * span_len, 2)
                    mid_x = (c_left["x"] + c_right["x"]) / 2.0
                    mid_y = y
                    item = {
                        "bay_label": f"Bay {c_left['grid_x']}-{c_right['grid_x']} @ {c_left['grid_y']}",
                        "dir": "X",
                        "span_len": span_len,
                        "Ln": Ln,
                        "mid_x": mid_x,
                        "mid_y": mid_y,
                        "Mo": Mo,
                        "M_pos": M_pos,
                        "As_req_m": As_cs_m,
                        "delta_As": delta_As,
                        "n_extra": n_b,
                        "dia_extra": strip_bottom_extra_dia,
                        "L_extra": L_ext,
                        "is_enlarged": is_enlarged,
                        "callout": f"+{n_b} Φ{strip_bottom_extra_dia} (L={L_ext}m)" if n_b > 0 else "Base Mesh OK"
                    }
                    if n_b > 0:
                        btm_extra_spans.append(item)
                    if is_enlarged:
                        enlarged_bays_info.append(item)

    # 4. Detect and calculate Enlarged Bays in Y-direction
    for i, x in enumerate(x_coords):
        col_active = [c for c in _active_cols if c["i"] == i]
        col_active.sort(key=lambda c: c["y"])
        if len(col_active) >= 2:
            if i == 0:
                L_perp = cant_L + Lx_spans[0] / 2.0
            elif i == n_xi - 1:
                L_perp = Lx_spans[-1] / 2.0 + cant_R
            else:
                L_perp = (Lx_spans[i-1] + Lx_spans[i]) / 2.0

            for k in range(len(col_active) - 1):
                c_bot = col_active[k]
                c_top = col_active[k+1]
                span_len = c_top["y"] - c_bot["y"]
                Ln = span_len - tc_m
                all_Ln.append(Ln)
                is_enlarged = (c_top["j"] - c_bot["j"]) > 1

                Mo = Wu * L_perp * (Ln ** 2) / 8.0
                M_pos = (0.50 if is_enlarged else 0.35) * Mo
                w_cs = min(span_len, L_perp) / 2.0
                M_cs_pos = 0.60 * M_pos
                As_cs_req = calc_As(M_cs_pos, w_cs, d, Fcu, Fy, ts)
                As_cs_m = As_cs_req / w_cs
                delta_As = max(0.0, As_cs_m - prov_btm_mesh_cm2m)

                if delta_As > 0.05 or is_enlarged:
                    a_bar = bar_area(strip_bottom_extra_dia)
                    n_b = max(2, math.ceil((delta_As * w_cs) / a_bar)) if delta_As > 0.05 else 0
                    L_ext = round(0.70 * span_len, 2)
                    mid_x = x
                    mid_y = (c_bot["y"] + c_top["y"]) / 2.0
                    item = {
                        "bay_label": f"Bay {c_bot['grid_y']}-{c_top['grid_y']} @ {c_bot['grid_x']}",
                        "dir": "Y",
                        "span_len": span_len,
                        "Ln": Ln,
                        "mid_x": mid_x,
                        "mid_y": mid_y,
                        "Mo": Mo,
                        "M_pos": M_pos,
                        "As_req_m": As_cs_m,
                        "delta_As": delta_As,
                        "n_extra": n_b,
                        "dia_extra": strip_bottom_extra_dia,
                        "L_extra": L_ext,
                        "is_enlarged": is_enlarged,
                        "callout": f"+{n_b} Φ{strip_bottom_extra_dia} (L={L_ext}m)" if n_b > 0 else "Base Mesh OK"
                    }
                    if n_b > 0:
                        btm_extra_spans.append(item)
                    if is_enlarged:
                        enlarged_bays_info.append(item)

    # Global max clear span & code minimum thickness
    Ln_max = max(all_Ln) if all_Ln else max(max(Ln_x_all), max(Ln_y_all))
    ts_code_min = max(15.0, Ln_max * 100.0 / 32.0)

    # 5. Punching Shear Check
    punching_results = calculate_punching_shear(col_list, Lx_calc, Ly_calc, cantilevers, Wu, d, Fcu)

    # 6. Top Extra Steel at Columns (with enlarged bay influence)
    top_extra_cols = calculate_extra_top_steel_at_columns(
        col_list, rows_x, rows_y, Lx_calc, Ly_calc, d, Fcu, Fy, ts, prov_top_mesh_cm2m, col_extra_dia, enlarged_bays=enlarged_bays_info
    )

    # 7. Cantilever Reinforcement
    cant_rft_list = calculate_cantilever_reinforcement(cantilevers, Wu, d, Fcu, Fy, ts, bottom_mesh_dia)

    # 8. Bill of Quantities (BoQ)
    boq = calculate_boq(
        Lx_calc, Ly_calc, cantilevers, ts,
        n_mesh_btm, bottom_mesh_dia, n_mesh_top, top_mesh_dia,
        top_extra_cols, cant_rft_list, btm_extra_spans=btm_extra_spans,
        void_panels=_all_panels,
    )

    # ═════════════════════════════════════════════════════════════════════════
    #  OUTPUT DASHBOARD & RESULTS
    # ═════════════════════════════════════════════════════════════════════════

    st.markdown('<div class="section-header">📊 Design Results Summary & Structural Status</div>', unsafe_allow_html=True)

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
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Adopted ts</div>
                <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{ts:.0f} cm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Effective Depth d</div>
                <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{d:.1f} cm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Ultimate Load Wu</div>
                <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{Wu:.3f} t/m²</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Bottom Mesh (B1,B2)</div>
                <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{mesh_btm_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m5:
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Top Mesh (T1,T2)</div>
                <div style="font-size:19.5px; font-weight:700; color:#1e40af;">{mesh_top_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m6:
        st.markdown(
            f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px 14px; text-align:center;">
                <div style="font-size:15px; font-weight:600; color:#64748b; margin-bottom:4px;">Punching Check</div>
                <div style="font-size:19.5px; font-weight:700; color:{punching_color};">{punching_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if ts < ts_code_min:
        st.warning(f"⚠️ **ملاحظة إنشائية على السُمك بعد إزالة الأعمدة**: السُمك المحدد ({ts:.0f} cm) أقل من الحد الأدنى الموصى به لمقاومة الترخيم للبحر الأكبر ($L_n/32 = {ts_code_min:.1f}\\text{{ cm}}$). يرجى زيادة سُمك البلاطة أو فحص الترخيم (Long-Term Deflection).")

    st.markdown("---")

    # ── 📊 1. 2D BENDING MOMENT MATRIX & COLOR CONTOURS (M11 & M22) ─────────
    st.markdown(
        '<div class="section-header">📊 1. 2D Bending Moment Matrix & Color Contours (مصفوفة العزوم والمخطط اللوني M11 & M22)</div>',
        unsafe_allow_html=True,
    )

    moment_view_mode = S.radio(
        "👁️ Select Moment View Mode (اختر اتجاه عزم الانحناء للعرض):",
        "fs_moment_contour_view_mode_idx",
        options=[
            "↔️ M11 — X-Direction Moment (عزوم المحور الأفقي)",
            "↕️ M22 — Y-Direction Moment (عزوم المحور الرأسي)",
            "🔲 Dual View — Side-by-Side (مقارنة جانبية لكلا الاتجاهين M11 & M22)",
        ],
        index=0,
    )

    img_m11_b64 = None
    img_m22_b64 = None
    img_dual_moment_b64 = None

    if "M11" in moment_view_mode and "Dual" not in moment_view_mode:
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
            file_name=f"Flat_Slab_Moment_M11_Contour_Plan_ts{ts:.0f}cm.png",
            mime="image/png",
            use_container_width=True,
        )
        plt.close(fig_m11)

    elif "M22" in moment_view_mode and "Dual" not in moment_view_mode:
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
            file_name=f"Flat_Slab_Moment_M22_Contour_Plan_ts{ts:.0f}cm.png",
            mime="image/png",
            use_container_width=True,
        )
        plt.close(fig_m22)

    else:
        fig_dual = generate_flat_slab_dual_moment_contour(
            Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
            col_w_cm=bc_s, col_d_cm=tc_s,
            removed_cols=_removed_col_objs,
            void_panel_ids=set(_confirmed_voids),
        )
        st.pyplot(fig_dual, use_container_width=True)
        buf_dual = io.BytesIO()
        fig_dual.savefig(buf_dual, format="png", bbox_inches="tight", dpi=300)
        buf_dual.seek(0)
        img_dual_moment_b64 = "data:image/png;base64," + base64.b64encode(buf_dual.getvalue()).decode("utf-8")
        buf_dual.seek(0)
        st.download_button(
            label="📥 Download Dual Moments (M11 & M22) Plan (High-Res PNG)",
            data=buf_dual,
            file_name=f"Flat_Slab_Dual_Moments_M11_M22_ts{ts:.0f}cm.png",
            mime="image/png",
            use_container_width=True,
        )
        plt.close(fig_dual)

    st.markdown("---")

    # ── 🟢 2. TOP REINFORCEMENT PLAN ─────────────────────────────────────────
    st.markdown(
        '<div class="section-header">🟢 2. Top Reinforcement Plan (المخطط الإنشائي للحديد العلوي والإضافي فوق الأعمدة والكوابيل)</div>',
        unsafe_allow_html=True,
    )
    fig_top = generate_flat_slab_top_rft_sketch(
        Lx_calc, Ly_calc, cantilevers, ts,
        mesh_top_str, top_extra_cols, cant_rft_list,
        col_w_cm=bc_s, col_d_cm=tc_s,
        removed_cols=_removed_col_objs,
        void_panel_ids=set(_confirmed_voids),
    )
    st.pyplot(fig_top, use_container_width=True)
    buf_top = io.BytesIO()
    fig_top.savefig(buf_top, format="png", bbox_inches="tight", dpi=300)
    buf_top.seek(0)
    img_top_b64 = "data:image/png;base64," + base64.b64encode(buf_top.getvalue()).decode("utf-8")
    buf_top.seek(0)
    st.download_button(
        label="📥 Download Top Reinforcement Plan (High-Res PNG)",
        data=buf_top,
        file_name=f"Flat_Slab_Top_Reinforcement_Plan_ts{ts:.0f}cm.png",
        mime="image/png",
        use_container_width=True,
    )
    plt.close(fig_top)

    st.markdown("---")

    # ── 🔵 3. BOTTOM REINFORCEMENT PLAN ──────────────────────────────────────
    st.markdown(
        '<div class="section-header">🔵 3. Bottom Reinforcement Plan (المخطط الإنشائي للحديد السفلي الأساسي والإضافي في الباكيات)</div>',
        unsafe_allow_html=True,
    )

    active_btm_extras = [b for b in btm_extra_spans if isinstance(b, dict) and b.get("n_extra", 0) > 0]
    img_btm_b64 = None

    if active_btm_extras:
        fig_btm = generate_flat_slab_bottom_rft_sketch(
            Lx_calc, Ly_calc, cantilevers, ts,
            mesh_btm_str, btm_extra_spans,
            col_w_cm=bc_s, col_d_cm=tc_s,
            removed_cols=_removed_col_objs,
            void_panel_ids=set(_confirmed_voids),
        )
        st.pyplot(fig_btm, use_container_width=True)
        buf_btm = io.BytesIO()
        fig_btm.savefig(buf_btm, format="png", bbox_inches="tight", dpi=300)
        buf_btm.seek(0)
        img_btm_b64 = "data:image/png;base64," + base64.b64encode(buf_btm.getvalue()).decode("utf-8")
        buf_btm.seek(0)
        st.download_button(
            label="📥 Download Bottom Reinforcement Plan (High-Res PNG)",
            data=buf_btm,
            file_name=f"Flat_Slab_Bottom_Reinforcement_Plan_ts{ts:.0f}cm.png",
            mime="image/png",
            use_container_width=True,
        )
        plt.close(fig_btm)
    else:
        st.markdown(
            f"""
            <div style='background:#f0fdf4; border:3px solid #16a34a; border-radius:12px; padding:22px 26px; margin:16px 0; text-align:center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                <div style='color:#15803d; font-size:1.55rem; font-weight:800; margin-bottom:10px;'>
                    ✅ ملاحظة إنشائية: لا حاجة لحديد إضافي سفلي في أي باكية
                </div>
                <div style='color:#0f172a; font-size:1.2rem; font-weight:700; line-height:1.8;'>
                    الشبكة السفلية الأساسية المختارة <span style='color:#1d4ed8;'>({mesh_btm_str})</span> تغطي بالكامل جميع عزوم الانحناء الموجبة (+M) بكامل مسطح السقف.<br>
                    <span style='font-size:1.0rem; color:#475569; font-weight:600;'>مساحة الحديد المتوفرة ({prov_btm_mesh_cm2m:.2f} cm²/m) كافية وآمنة تماماً، ولذلك لا يتطلب المخطط أي تسليح سفلي إضافي.</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

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
        st.dataframe(pd.DataFrame(master_summary, columns=["Design Item", "Design Output / Value", "Engineering Notes & Code Reference"]), use_container_width=True, hide_index=True)

    # ── 🔩 TOP EXTRA REINFORCEMENT AT COLUMNS ─────────────────────────────────
    with st.expander("🔩 Top Extra Reinforcement @ Columns (حديد إضافي علوي فوق الأعمدة)", expanded=False):
        extra_df = pd.DataFrame([
            {
                "Column ID": c["id"],
                "Grid": c["grid"],
                "Type": c["type"],
                "Mu⁻ (ton.m)": f"{c['Mu_neg (t.m)']:.2f}",
                "As_req (cm²/m)": f"{c['As_req (cm²/m)']:.2f}",
                "Base Top Mesh (cm²/m)": f"{c['As_mesh (cm²/m)']:.2f}",
                "Extra Steel Required": c["callout"],
                "Length L_ext (m)": f"{c['L_extra']:.2f} m" if c["is_needed"] else "—",
            }
            for c in top_extra_cols
        ])
        st.dataframe(extra_df, use_container_width=True, hide_index=True)

    # ── 🏗️ BOTTOM EXTRA REINFORCEMENT IN ENLARGED BAYS ───────────────────────
    if btm_extra_spans:
        with st.expander("🏗️ Bottom Extra Reinforcement (حديد إضافي سفلي في الباكيات المكبرة)", expanded=False):
            btm_extra_df = pd.DataFrame([
                {
                    "Bay Location": b["bay_label"],
                    "Direction": b["dir"],
                    "Span Length (m)": f"{b['span_len']:.2f} m",
                    "Clear Span Ln (m)": f"{b['Ln']:.2f} m",
                    "Positive Moment M⁺ (t.m)": f"{b['M_pos']:.2f}",
                    "As_req (cm²/m)": f"{b['As_req_m']:.2f}",
                    "Base Mesh (cm²/m)": f"{prov_btm_mesh_cm2m:.2f}",
                    "Extra Bottom Steel": b["callout"],
                }
                for b in btm_extra_spans if isinstance(b, dict) and b.get("n_extra", 0) > 0
            ])
            st.dataframe(btm_extra_df, use_container_width=True, hide_index=True)


    # ── 🥊 PUNCHING SHEAR VERIFICATION ───────────────────────────────────────
    with st.expander("🥊 Punching Shear Check (فحص القص الثاقب لجميع الأعمدة)", expanded=False):
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
        st.dataframe(punch_df, use_container_width=True, hide_index=True)

        if not all_safe:
            st.warning("⚠️ **تنبيه إنشائي**: بعض الأعمدة غير آمنة في القص الثاقب. يُنصح بزيادة سُمك البلاطة $t_s$ أو إضافة سقوط عمود (Drop Panel) أو كانات قص (Studs).")

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
            st.dataframe(cant_df, use_container_width=True, hide_index=True)

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
        st.dataframe(pd.DataFrame(items_table_data), use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        # ── Table 2: Final Totals by Bar Diameter & Grand Total (جدول إجمالي الكمية لكل قطر والإجمالي العام) ──
        st.markdown("##### 📊 2. جدول إجمالي كميات الحديد لكل قطر والإجمالي الكلي (Total Quantities by Bar Diameter & Grand Total)")
        dia_table_data = []
        for d in boq.get("by_dia", []):
            dia_table_data.append({
                "قطر السيخ Φ (Bar Dia)": d["dia_str"],
                "وزن المتر الطولي (kg/m')": f"{d['unit_w_kg_m']:.3f}",
                "إجمالي الطول (m')": d["length_str"],
                "إجمالي الوزن (kg)": d["weight_kg_str"],
                "إجمالي الوزن (Ton)": d["weight_ton_str"],
                "النسبة المئوية (%)": d["percent_str"],
                "الاستخدام الإنشائي في السقف (Applications in Slab)": d["apps"],
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

        st.dataframe(pd.DataFrame(dia_table_data), use_container_width=True, hide_index=True)

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
        st.dataframe(ld_df, use_container_width=True, hide_index=True)

    # ── 📐 DETAILED DDM MOMENTS TABLES ───────────────────────────────────────
    def render_direction(rows, direction_label):
        with st.expander(f"📐 Bending Moments & Reinforcement — {direction_label}", expanded=False):
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

            st.dataframe(pd.DataFrame(moment_rows, columns=["Strip / Location", "Moment (ton·m)", "Strip Width (m)"]), use_container_width=True, hide_index=True)
            st.dataframe(pd.DataFrame(steel_rows, columns=["Zone", "Total As_req (cm²)", "As/m (cm²/m)", "Bars / meter", "Spacing", "As_prov/m (cm²/m)"]), use_container_width=True, hide_index=True)

    render_direction(rows_x, "X-Direction (spanning across Lx spans)")
    render_direction(rows_y, "Y-Direction (spanning across Ly spans)")

    # ── 🏛️ COLUMN REACTIONS & MULTI-STOREY LOADS (ردود أفعال وتوزيع أحمال الأعمدة) ────
    st.markdown(
        f'<div class="section-header">🏛️ Column Reactions & Vertical Loads (ردود أفعال وتوزيع أحمال الأعمدة — {num_floors} طوابق)</div>',
        unsafe_allow_html=True,
    )

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

    # ── Render Visual Column Reactions & Load Plan ───────────────────────────
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
        file_name=f"Flat_Slab_Column_Reactions_Plan_{num_floors}Floors.png",
        mime="image/png",
        use_container_width=True,
    )
    plt.close(fig_reac)

    st.markdown("---")

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
        st.dataframe(reactions_df, use_container_width=True, hide_index=True)

    # ── 📊 CLASSIFICATION INTO 3 GOVERNING COLUMN TYPES ──────────────────────
    with st.expander("📌 أقصى ردود أفعال وتصنيف نماذج الأعمدة (Governing Column Loads by Type)", expanded=False):
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
            st.dataframe(pd.DataFrame(summary_models), use_container_width=True, hide_index=True)

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
            file_name=f"ECP203_Flat_Slab_Calculation_Sheet_ts{ts:.0f}cm_{num_floors}Floors.html",
            mime="text/html",
            use_container_width=True,
        )
        if pdf_bytes:
            st.download_button(
                label="📕 Save as PDF (مباشر)",
                data=pdf_bytes,
                file_name=f"ECP203_Flat_Slab_Calculation_Sheet_ts{ts:.0f}cm_{num_floors}Floors.pdf",
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
