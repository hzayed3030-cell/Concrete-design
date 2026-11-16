"""
modules/concise_report_generator.py
================================================================================
Concise Design Outputs Report Generator (تصدير مخرجات التصميم المختصرة - 8 صفحات)
Engine for Module 1: Integrated Structure Design (ECP 203-2018).

Generates an exact 8-page consulting-grade engineering PDF calculation sheet:
Page 1: Inputs Plan View (مسقط أفقي للمدخلات الإنشائية - صامت بالأبعاد فقط دون مسميات أو قطاعات)
Page 2: Columns Design (ملخص تصميم الأعمدة بعد النمذجة - مسقط برموز C1, C2, C3 فقط + جدول التصميم)
Page 3: Footings Design (ملخص تصميم القواعد المسلحة بعد النمذجة - مسقط برموز F1, F2, F3 فقط + جدول التصميم)
Page 4: Ground Beams Design (ملخص تصميم السملات الأرضية - مسقط برموز B1, B2, B3 فقط + جدول التصميم)
Page 5: Slab Beams & Cantilevers Design (ملخص كمرات السقف والكوابيل بعد النمذجة - مسقط بأسماء النماذج + جدول التصميم)
Page 6: Slab Bottom Reinforcement (مسقط تسليح الرقة السفلية - الشبكة الرئيسية + الإضافي بالاتجاهين وقيمه مباشرة على الرسم)
Page 7: Slab Top Reinforcement (مسقط تسليح الرقة العلوية - الشبكة الرئيسية + الإضافي + شوك الكوابيل وقيمها مباشرة على الرسم)
Page 8: Column Caps Additional Top Reinforcement (مسقط كبات الأعمدة - الإضافي العلوي فوق الأعمدة بالاتجاهين وتفاصيله)
================================================================================
"""

import math
import io
import base64
from typing import List, Dict, Any, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from modules.report_generator import html_to_pdf_bytes


def _ar(text: Any) -> str:
    """Helper to reshape and reorder Arabic text for matplotlib rendering."""
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        if any('\u0600' <= char <= '\u06FF' for char in str(text)):
            reshaped_text = arabic_reshaper.reshape(str(text))
            return get_display(reshaped_text)
        return str(text)
    except Exception:
        return str(text)



# ── Helper: Convert Matplotlib Figure to Base64 ────────────────────────────────
def fig_to_b64(fig: plt.Figure) -> Optional[str]:
    if fig is None:
        return None
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=140)
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None
    finally:
        try:
            plt.close(fig)
        except Exception:
            pass


# ── PAGE 1: Inputs Plan View (مسقط صامت بالأبعاد فقط دون مسميات) ───────────────
def draw_page1_silent_inputs(
    Lx_spans: List[float],
    Ly_spans: List[float],
    cantilevers: Dict[str, float],
    active_cols: List[Dict[str, Any]],
    drop_beams: Optional[List[Dict[str, Any]]] = None,
    void_boxes: Optional[List[Any]] = None,
) -> plt.Figure:
    """
    Page 1: Engineering geometry drawing showing slabs, voids, beams, columns.
    STRICT REQUIREMENT: Show dimension lines only. No labels or section text anywhere.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, ax = plt.subplots(figsize=(14, 8.5), dpi=140, facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")

    cant_l = float(cantilevers.get("left", 0.0) or 0.0) if cantilevers else 0.0
    cant_r = float(cantilevers.get("right", 0.0) or 0.0) if cantilevers else 0.0
    cant_b = float(cantilevers.get("bottom", 0.0) or 0.0) if cantilevers else 0.0
    cant_t = float(cantilevers.get("top", 0.0) or 0.0) if cantilevers else 0.0

    x_grid = [0.0]
    for lx in Lx_spans:
        x_grid.append(x_grid[-1] + float(lx))
    y_grid = [0.0]
    for ly in Ly_spans:
        y_grid.append(y_grid[-1] + float(ly))

    x_min_slab = x_grid[0] - cant_l
    x_max_slab = x_grid[-1] + cant_r
    y_min_slab = y_grid[0] - cant_b
    y_max_slab = y_grid[-1] + cant_t

    slab_w = x_max_slab - x_min_slab
    slab_h = y_max_slab - y_min_slab

    # 1. Slab Outline
    slab_rect = patches.Rectangle(
        (x_min_slab, y_min_slab), slab_w, slab_h,
        facecolor="#ffffff", edgecolor="#0f172a", lw=2.5, zorder=1
    )
    ax.add_patch(slab_rect)

    # 2. Voids / Openings
    if void_boxes:
        for vb in void_boxes:
            if len(vb) >= 4:
                vx1, vx2, vy1, vy2 = vb[0], vb[1], vb[2], vb[3]
                vw, vh = vx2 - vx1, vy2 - vy1
                vr = patches.Rectangle(
                    (vx1, vy1), vw, vh,
                    facecolor="#fee2e2", edgecolor="#ef4444", lw=1.8, zorder=2
                )
                ax.add_patch(vr)
                ax.plot([vx1, vx2], [vy1, vy2], color="#ef4444", lw=1.2, ls="--", zorder=3)
                ax.plot([vx1, vx2], [vy2, vy1], color="#ef4444", lw=1.2, ls="--", zorder=3)

    # 3. Drop Beams (Silent bars with no labels)
    if drop_beams:
        for b in drop_beams:
            p1 = b.get("p1", [0, 0])
            p2 = b.get("p2", [0, 0])
            bw_m = float(b.get("b_cm", b.get("b", 25.0))) / 100.0
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            if abs(dx) >= abs(dy):
                bx0 = min(p1[0], p2[0])
                bw = abs(dx)
                by0 = p1[1] - bw_m / 2.0
                r_bm = patches.Rectangle(
                    (bx0, by0), bw, bw_m,
                    facecolor="#e2e8f0", edgecolor="#475569", lw=1.5, zorder=4
                )
                ax.add_patch(r_bm)
            else:
                by0 = min(p1[1], p2[1])
                bh = abs(dy)
                bx0 = p1[0] - bw_m / 2.0
                r_bm = patches.Rectangle(
                    (bx0, by0), bw_m, bh,
                    facecolor="#e2e8f0", edgecolor="#475569", lw=1.5, zorder=4
                )
                ax.add_patch(r_bm)

    # 4. Columns (Solid rectangles, NO LABELS)
    if active_cols:
        for c in active_cols:
            cx = float(c.get("center_x", c.get("x", 0.0)))
            cy = float(c.get("center_y", c.get("y", 0.0)))
            cw = float(c.get("width_m", c.get("tc", 50.0) / 100.0))
            ch = float(c.get("height_m", c.get("bc", 30.0) / 100.0))
            cr = patches.Rectangle(
                (cx - cw / 2.0, cy - ch / 2.0), cw, ch,
                facecolor="#1e293b", edgecolor="#0f172a", lw=1.6, zorder=5
            )
            ax.add_patch(cr)

    # 5. Grid lines & Bubbles
    y_bubble_top = y_max_slab + 1.2
    x_bubble_left = x_min_slab - 1.2
    for idx, gx in enumerate(x_grid, 1):
        ax.plot([gx, gx], [y_min_slab - 0.4, y_bubble_top], color="#94a3b8", ls="--", lw=1.0, zorder=1)
        ax.text(gx, y_bubble_top, f"Y{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=10,
                bbox=dict(boxstyle="circle,pad=0.26", fc="#f8fafc", ec="#334155", lw=1.3), zorder=8)

    for idx, gy in enumerate(y_grid, 1):
        ax.plot([x_bubble_left, x_max_slab + 0.4], [gy, gy], color="#94a3b8", ls="--", lw=1.0, zorder=1)
        ax.text(x_bubble_left, gy, f"X{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=10,
                bbox=dict(boxstyle="circle,pad=0.26", fc="#f8fafc", ec="#334155", lw=1.3), zorder=8)

    # 6. Dimension Lines (TOP: X spans & Total)
    y_dim1 = y_max_slab + 0.5
    for i in range(len(x_grid) - 1):
        x1, x2 = x_grid[i], x_grid[i + 1]
        ax.annotate("", xy=(x1, y_dim1), xytext=(x2, y_dim1), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.4), zorder=6)
        ax.text((x1 + x2) / 2.0, y_dim1 + 0.08, f"{x2 - x1:.2f} m", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#1e293b",
                bbox=dict(boxstyle="square,pad=0.12", fc="#ffffff", ec="none", alpha=0.9), zorder=7)

    y_dim2 = y_max_slab + 0.95
    if len(x_grid) > 2:
        ax.annotate("", xy=(x_grid[0], y_dim2), xytext=(x_grid[-1], y_dim2), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6), zorder=6)
        ax.text((x_grid[0] + x_grid[-1]) / 2.0, y_dim2 + 0.08, f"Total L = {x_grid[-1] - x_grid[0]:.2f} m", ha="center", va="bottom",
                fontsize=9.5, fontweight="bold", color="#0f172a", bbox=dict(boxstyle="square,pad=0.15", fc="#ffffff", ec="none", alpha=0.9), zorder=7)

    # Dimension Lines (LEFT: Y spans & Total)
    x_dim1 = x_min_slab - 0.5
    for j in range(len(y_grid) - 1):
        y1, y2 = y_grid[j], y_grid[j + 1]
        ax.annotate("", xy=(x_dim1, y1), xytext=(x_dim1, y2), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.4), zorder=6)
        ax.text(x_dim1 - 0.08, (y1 + y2) / 2.0, f"{y2 - y1:.2f} m", ha="right", va="center", rotation=90, fontsize=8.5, fontweight="bold", color="#1e293b",
                bbox=dict(boxstyle="square,pad=0.12", fc="#ffffff", ec="none", alpha=0.9), zorder=7)

    x_dim2 = x_min_slab - 0.95
    if len(y_grid) > 2:
        ax.annotate("", xy=(x_dim2, y_grid[0]), xytext=(x_dim2, y_grid[-1]), arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.6), zorder=6)
        ax.text(x_dim2 - 0.08, (y_grid[0] + y_grid[-1]) / 2.0, f"Total B = {y_grid[-1] - y_grid[0]:.2f} m", ha="right", va="center", rotation=90,
                fontsize=9.5, fontweight="bold", color="#0f172a", bbox=dict(boxstyle="square,pad=0.15", fc="#ffffff", ec="none", alpha=0.9), zorder=7)

    # Cantilever Overhang Dimensions if any
    if cant_l > 0.05:
        ax.text(x_min_slab + cant_l / 2.0, y_min_slab - 0.35, f"Cant = {cant_l:.2f} m", ha="center", va="top", fontsize=8.0, fontweight="bold", color="#64748b")
    if cant_r > 0.05:
        ax.text(x_max_slab - cant_r / 2.0, y_min_slab - 0.35, f"Cant = {cant_r:.2f} m", ha="center", va="top", fontsize=8.0, fontweight="bold", color="#64748b")

    ax.set_xlim(x_min_slab - 1.8, x_max_slab + 1.2)
    ax.set_ylim(y_min_slab - 1.0, y_max_slab + 1.8)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig


# ── PAGE 2: Columns Design (مسقط برموز C1, C2, C3 فقط) ────────────────────────
def draw_page2_columns_plan(
    active_cols: List[Dict[str, Any]],
    Lx_spans: List[float],
    Ly_spans: List[float],
    cantilevers: Dict[str, float],
) -> plt.Figure:
    """
    Page 2: Column plan with ONLY model tags (C1, C2, C3...) written on columns.
    Legend is positioned cleanly below the drawing in a dedicated enlarged subplot (1.7x panel).
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, (ax, ax_leg) = plt.subplots(
        2, 1, figsize=(14, 8.5), dpi=140, facecolor="#ffffff",
        gridspec_kw={"height_ratios": [1, 0.14], "hspace": 0.07}
    )
    ax.set_facecolor("#f8fafc")
    ax_leg.set_facecolor("#ffffff")
    ax_leg.axis("off")

    cant_l = float(cantilevers.get("left", 0.0) or 0.0) if cantilevers else 0.0
    cant_r = float(cantilevers.get("right", 0.0) or 0.0) if cantilevers else 0.0
    cant_b = float(cantilevers.get("bottom", 0.0) or 0.0) if cantilevers else 0.0
    cant_t = float(cantilevers.get("top", 0.0) or 0.0) if cantilevers else 0.0

    x_grid = [0.0]
    for lx in Lx_spans: x_grid.append(x_grid[-1] + float(lx))
    y_grid = [0.0]
    for ly in Ly_spans: y_grid.append(y_grid[-1] + float(ly))

    x_min_slab = x_grid[0] - cant_l
    x_max_slab = x_grid[-1] + cant_r
    y_min_slab = y_grid[0] - cant_b
    y_max_slab = y_grid[-1] + cant_t

    # Slab boundary
    ax.add_patch(patches.Rectangle((x_min_slab, y_min_slab), x_max_slab - x_min_slab, y_max_slab - y_min_slab,
                                  facecolor="#f1f5f9", edgecolor="#cbd5e1", lw=1.8, ls="--", zorder=1))

    # Grid lines
    y_bubble_top = y_max_slab + 1.2
    x_bubble_left = x_min_slab - 1.2
    for idx, gx in enumerate(x_grid, 1):
        ax.plot([gx, gx], [y_min_slab - 0.4, y_bubble_top], color="#94a3b8", ls="--", lw=0.9, zorder=1)
        ax.text(gx, y_bubble_top, f"Y{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=9.5,
                bbox=dict(boxstyle="circle,pad=0.25", fc="#f8fafc", ec="#334155", lw=1.2), zorder=8)
    for idx, gy in enumerate(y_grid, 1):
        ax.plot([x_bubble_left, x_max_slab + 0.4], [gy, gy], color="#94a3b8", ls="--", lw=0.9, zorder=1)
        ax.text(x_bubble_left, gy, f"X{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=9.5,
                bbox=dict(boxstyle="circle,pad=0.25", fc="#f8fafc", ec="#334155", lw=1.2), zorder=8)

    # Dynamic column marks mapping based on existing categories: Priority (Interior -> Edge -> Corner)
    has_int = any(str(c.get("type", "")).lower() == "interior" for c in active_cols)
    has_edge = any("edge" in str(c.get("type", "")).lower() or "طرف" in str(c.get("type", "")).lower() for c in active_cols)
    has_corner = any("corner" in str(c.get("type", "")).lower() or "ركن" in str(c.get("type", "")).lower() for c in active_cols)

    dyn_col_map = {}
    dyn_idx = 1
    if has_int:
        dyn_col_map["interior"] = f"C{dyn_idx}"
        dyn_idx += 1
    if has_edge:
        dyn_col_map["edge"] = f"C{dyn_idx}"
        dyn_idx += 1
    if has_corner:
        dyn_col_map["corner"] = f"C{dyn_idx}"
        dyn_idx += 1

    col_style = {
        "C1": {"fc": "#1e40af", "ec": "#1e3a8a", "tc": "#ffffff"},
        "C2": {"fc": "#ea580c", "ec": "#c2410c", "tc": "#ffffff"},
        "C3": {"fc": "#7e22ce", "ec": "#581c87", "tc": "#ffffff"},
    }

    for c in active_cols:
        cx = float(c.get("center_x", c.get("x", 0.0)))
        cy = float(c.get("center_y", c.get("y", 0.0)))
        cw = float(c.get("width_m", c.get("tc", 50.0) / 100.0))
        ch = float(c.get("height_m", c.get("bc", 30.0) / 100.0))

        model_tag = c.get("model_mark")
        if not model_tag:
            ctype = str(c.get("type", "Interior")).lower()
            if "edge" in ctype or "طرف" in ctype:
                model_tag = dyn_col_map.get("edge", "C1")
            elif "corner" in ctype or "ركن" in ctype:
                model_tag = dyn_col_map.get("corner", "C1")
            else:
                model_tag = dyn_col_map.get("interior", "C1")

        cfg = col_style.get(model_tag, col_style["C1"])
        cr = patches.Rectangle((cx - cw / 2.0, cy - ch / 2.0), cw, ch,
                               facecolor=cfg["fc"], edgecolor=cfg["ec"], lw=1.8, zorder=5)
        ax.add_patch(cr)
        # Label model tag OUTSIDE the column element (positioned above column rectangle)
        y_lbl = cy + ch / 2.0 + 0.30
        ax.text(cx, y_lbl, model_tag, ha="center", va="bottom", color=cfg["ec"], fontweight="bold", fontsize=10.5,
                bbox=dict(boxstyle="round,pad=0.18", fc="#ffffff", ec=cfg["ec"], lw=1.2, alpha=0.95), zorder=7)

    # Dynamic Legend placed cleanly below drawing in ax_leg (English Only, 2 Lines, 1.7x panel)
    leg_items = []
    if has_int:
        leg_items.append(f"■ {dyn_col_map['interior']}: Interior Columns")
    if has_edge:
        leg_items.append(f"■ {dyn_col_map['edge']}: Edge Columns")
    if has_corner:
        leg_items.append(f"■ {dyn_col_map['corner']}: Corner Columns")
    items_str = "    |    ".join([f"[ {it} ]" for it in leg_items])
    leg_str = f"COLUMN MODELS (LEGEND)\n{items_str}"
    ax_leg.text(0.5, 0.5, leg_str, ha="center", va="center", fontsize=12.5, fontweight="bold", color="#1e293b",
                bbox=dict(boxstyle="round,pad=0.6", fc="#ffffff", ec="#cbd5e1", lw=1.5, alpha=0.98))

    ax.set_xlim(x_min_slab - 1.8, x_max_slab + 1.2)
    ax.set_ylim(y_min_slab - 0.8, y_max_slab + 1.8)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig


# ── PAGE 3: Footings Design (مسقط برموز F1, F2, F3 فقط) ───────────────────────
def draw_page3_footings_plan(
    active_cols: List[Dict[str, Any]],
    ftg_analysis: Dict[str, Any],
    Lx_spans: List[float],
    Ly_spans: List[float],
    cantilevers: Dict[str, float],
) -> plt.Figure:
    """
    Page 3: Footings layout plan with ONLY model tags (F1, F2, F3...) on footings.
    Legend is positioned cleanly below the drawing in a dedicated enlarged subplot (1.7x panel).
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, (ax, ax_leg) = plt.subplots(
        2, 1, figsize=(14, 8.5), dpi=140, facecolor="#ffffff",
        gridspec_kw={"height_ratios": [1, 0.14], "hspace": 0.07}
    )
    ax.set_facecolor("#f8fafc")
    ax_leg.set_facecolor("#ffffff")
    ax_leg.axis("off")

    cant_l = float(cantilevers.get("left", 0.0) or 0.0) if cantilevers else 0.0
    cant_r = float(cantilevers.get("right", 0.0) or 0.0) if cantilevers else 0.0
    cant_b = float(cantilevers.get("bottom", 0.0) or 0.0) if cantilevers else 0.0
    cant_t = float(cantilevers.get("top", 0.0) or 0.0) if cantilevers else 0.0

    x_grid = [0.0]
    for lx in Lx_spans: x_grid.append(x_grid[-1] + float(lx))
    y_grid = [0.0]
    for ly in Ly_spans: y_grid.append(y_grid[-1] + float(ly))

    x_min_slab = x_grid[0] - cant_l
    x_max_slab = x_grid[-1] + cant_r
    y_min_slab = y_grid[0] - cant_b
    y_max_slab = y_grid[-1] + cant_t

    # Grid lines
    y_bubble_top = y_max_slab + 1.2
    x_bubble_left = x_min_slab - 1.2
    for idx, gx in enumerate(x_grid, 1):
        ax.plot([gx, gx], [y_min_slab - 0.4, y_bubble_top], color="#94a3b8", ls="--", lw=0.9, zorder=1)
        ax.text(gx, y_bubble_top, f"Y{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=9.5,
                bbox=dict(boxstyle="circle,pad=0.25", fc="#f8fafc", ec="#334155", lw=1.2), zorder=8)
    for idx, gy in enumerate(y_grid, 1):
        ax.plot([x_bubble_left, x_max_slab + 0.4], [gy, gy], color="#94a3b8", ls="--", lw=0.9, zorder=1)
        ax.text(x_bubble_left, gy, f"X{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=9.5,
                bbox=dict(boxstyle="circle,pad=0.25", fc="#f8fafc", ec="#334155", lw=1.2), zorder=8)

    ftg_style = {
        "F1": {"fc": "#bae6fd", "ec": "#0284c7", "tc": "#0369a1"},
        "F2": {"fc": "#fed7aa", "ec": "#ea580c", "tc": "#c2410c"},
        "F3": {"fc": "#e9d5ff", "ec": "#9333ea", "tc": "#6b21a8"},
        "ST1": {"fc": "#fef08a", "ec": "#ca8a04", "tc": "#854d0e"},
    }

    dyn_ftg_map = (ftg_analysis.get("ftg_label_map") or {}) if ftg_analysis else {}
    iso_by_col = {}
    if ftg_analysis and "isolated_footings" in ftg_analysis:
        for f in ftg_analysis["isolated_footings"]:
            iso_by_col[f.get("col_id", "")] = f

    if not dyn_ftg_map:
        has_int_f = any(str(c.get("type", "")).lower() == "interior" for c in active_cols)
        has_edge_f = any("edge" in str(c.get("type", "")).lower() or "طرف" in str(c.get("type", "")).lower() for c in active_cols)
        has_corner_f = any("corner" in str(c.get("type", "")).lower() or "ركن" in str(c.get("type", "")).lower() for c in active_cols)
        f_idx = 1
        if has_int_f:
            dyn_ftg_map["Interior"] = f"F{f_idx}"
            f_idx += 1
        if has_edge_f:
            dyn_ftg_map["Edge"] = f"F{f_idx}"
            f_idx += 1
        if has_corner_f:
            dyn_ftg_map["Corner"] = f"F{f_idx}"
            f_idx += 1

    for c in active_cols:
        cx = float(c.get("center_x", c.get("x", 0.0)))
        cy = float(c.get("center_y", c.get("y", 0.0)))
        cw = float(c.get("width_m", c.get("tc", 50.0) / 100.0))
        ch = float(c.get("height_m", c.get("bc", 30.0) / 100.0))
        cid = c.get("id", "")

        ctype = str(c.get("type", "Interior")).title()
        if "Edge" in ctype or "طرف" in ctype:
            raw_k = "Edge"
        elif "Corner" in ctype or "ركن" in ctype:
            raw_k = "Corner"
        else:
            raw_k = "Interior"

        f_inst = iso_by_col.get(cid)
        if f_inst:
            ftg_tag = f_inst.get("name", dyn_ftg_map.get(raw_k, "F1"))
            L_ftg = float(f_inst.get("L_cm", 240)) / 100.0
            B_ftg = float(f_inst.get("B_cm", 200)) / 100.0
        else:
            ftg_tag = dyn_ftg_map.get(raw_k, "F1")
            if raw_k == "Corner":
                L_ftg, B_ftg = 2.0, 1.8
            elif raw_k == "Edge":
                L_ftg, B_ftg = 2.4, 2.0
            else:
                L_ftg, B_ftg = 2.8, 2.4

        cfg = ftg_style.get(ftg_tag, ftg_style["F1"])

        # Draw RC footing
        fr = patches.Rectangle((cx - L_ftg / 2.0, cy - B_ftg / 2.0), L_ftg, B_ftg,
                               facecolor=cfg["fc"], edgecolor=cfg["ec"], lw=1.8, alpha=0.88, zorder=3)
        ax.add_patch(fr)

        # Draw Column anchor at center
        cr = patches.Rectangle((cx - cw / 2.0, cy - ch / 2.0), cw, ch,
                               facecolor="#1e293b", edgecolor="#0f172a", lw=1.2, zorder=5)
        ax.add_patch(cr)

        # Label model tag OUTSIDE the footing rectangle (positioned below the footing)
        y_ftg_lbl = cy - B_ftg / 2.0 - 0.35
        ax.text(cx, y_ftg_lbl, ftg_tag, ha="center", va="top", color=cfg["tc"], fontweight="bold", fontsize=11.0, zorder=7,
                bbox=dict(boxstyle="round,pad=0.20", fc="#ffffff", ec=cfg["ec"], lw=1.2, alpha=0.96))

    # Dynamic Legend placed cleanly below drawing in ax_leg (English Only, 2 Lines, 1.7x panel)
    leg_items = []
    if "Interior" in dyn_ftg_map:
        leg_items.append(f"■ {dyn_ftg_map['Interior']}: Interior Footings")
    if "Edge" in dyn_ftg_map:
        leg_items.append(f"■ {dyn_ftg_map['Edge']}: Edge Footings")
    if "Corner" in dyn_ftg_map:
        leg_items.append(f"■ {dyn_ftg_map['Corner']}: Corner Footings")
    items_str = "    |    ".join([f"[ {it} ]" for it in leg_items])
    leg_str = f"RC FOOTING MODELS (LEGEND)\n{items_str}"
    ax_leg.text(0.5, 0.5, leg_str, ha="center", va="center", fontsize=12.5, fontweight="bold", color="#1e293b",
                bbox=dict(boxstyle="round,pad=0.6", fc="#ffffff", ec="#cbd5e1", lw=1.5, alpha=0.98))

    min_xc = min(float(c.get("center_x", c.get("x", 0.0))) for c in active_cols) if active_cols else x_min_slab
    max_xc = max(float(c.get("center_x", c.get("x", 0.0))) for c in active_cols) if active_cols else x_max_slab
    min_yc = min(float(c.get("center_y", c.get("y", 0.0))) - 1.5 for c in active_cols) if active_cols else y_min_slab
    max_yc = max(float(c.get("center_y", c.get("y", 0.0))) + 1.5 for c in active_cols) if active_cols else y_max_slab

    ax.set_xlim(min(x_min_slab - 1.8, min_xc - 1.8), max(x_max_slab + 1.2, max_xc + 1.8))
    ax.set_ylim(min(y_min_slab - 1.2, min_yc - 1.2), max(y_max_slab + 1.8, max_yc + 1.8))
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig


# ── PAGE 4: Ground Beams Design (مسقط برموز B1, B2, B3 فقط) ───────────────────
def draw_page4_ground_beams_plan(
    gb_analysis: Dict[str, Any],
    active_cols: List[Dict[str, Any]],
    Lx_spans: List[float],
    Ly_spans: List[float],
    cantilevers: Dict[str, float],
) -> plt.Figure:
    """
    Page 4: Ground beams layout plan with ONLY model tags (B1, B2, B3...) on beams.
    Legend is positioned cleanly below the drawing in a dedicated enlarged subplot (1.7x panel).
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, (ax, ax_leg) = plt.subplots(
        2, 1, figsize=(14, 8.5), dpi=140, facecolor="#ffffff",
        gridspec_kw={"height_ratios": [1, 0.14], "hspace": 0.07}
    )
    ax.set_facecolor("#f8fafc")
    ax_leg.set_facecolor("#ffffff")
    ax_leg.axis("off")

    cant_l = float(cantilevers.get("left", 0.0) or 0.0) if cantilevers else 0.0
    cant_r = float(cantilevers.get("right", 0.0) or 0.0) if cantilevers else 0.0
    cant_b = float(cantilevers.get("bottom", 0.0) or 0.0) if cantilevers else 0.0
    cant_t = float(cantilevers.get("top", 0.0) or 0.0) if cantilevers else 0.0

    x_grid = [0.0]
    for lx in Lx_spans: x_grid.append(x_grid[-1] + float(lx))
    y_grid = [0.0]
    for ly in Ly_spans: y_grid.append(y_grid[-1] + float(ly))

    x_min_slab = x_grid[0] - cant_l
    x_max_slab = x_grid[-1] + cant_r
    y_min_slab = y_grid[0] - cant_b
    y_max_slab = y_grid[-1] + cant_t

    # Grid lines
    y_bubble_top = y_max_slab + 1.2
    x_bubble_left = x_min_slab - 1.2
    for idx, gx in enumerate(x_grid, 1):
        ax.plot([gx, gx], [y_min_slab - 0.4, y_bubble_top], color="#94a3b8", ls="--", lw=0.9, zorder=1)
        ax.text(gx, y_bubble_top, f"Y{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=9.5,
                bbox=dict(boxstyle="circle,pad=0.25", fc="#f8fafc", ec="#334155", lw=1.2), zorder=8)
    for idx, gy in enumerate(y_grid, 1):
        ax.plot([x_bubble_left, x_max_slab + 0.4], [gy, gy], color="#94a3b8", ls="--", lw=0.9, zorder=1)
        ax.text(x_bubble_left, gy, f"X{idx}", ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=9.5,
                bbox=dict(boxstyle="circle,pad=0.25", fc="#f8fafc", ec="#334155", lw=1.2), zorder=8)

    beam_style = {
        "GB1": {"fc": "#dcfce7", "ec": "#15803d", "tc": "#14532d"},
        "GB2": {"fc": "#e0f2fe", "ec": "#0284c7", "tc": "#0369a1"},
        "GB3": {"fc": "#f3e8ff", "ec": "#7e22ce", "tc": "#581c87"},
        "B1": {"fc": "#dcfce7", "ec": "#15803d", "tc": "#14532d"},
        "B2": {"fc": "#e0f2fe", "ec": "#0284c7", "tc": "#0369a1"},
        "B3": {"fc": "#f3e8ff", "ec": "#7e22ce", "tc": "#581c87"},
        "ST1": {"fc": "#ffedd5", "ec": "#ea580c", "tc": "#9a3412"},
    }

    # Draw Ground Beams with Strict Centerline Continuity
    from modules.ground_beam_layout import align_ground_beam_coords, _get_grid_axes_gb
    col_xs, col_ys, _, _ = _get_grid_axes_gb(active_cols)
    eff_grid_xs = col_xs if col_xs else x_grid
    eff_grid_ys = col_ys if col_ys else y_grid

    gb_list = gb_analysis.get("ground_beams", []) if gb_analysis else []
    for b in gb_list:
        alg = align_ground_beam_coords(b, eff_grid_xs, eff_grid_ys, active_columns=active_cols)
        p1 = alg["p1"]
        p2 = alg["p2"]
        dir_b = alg["dir"]
        tag = b.get("tag", b.get("model_mark", "GB1"))
        bw_m = float(b.get("b_cm", 25.0)) / 100.0
        cfg = beam_style.get(tag, beam_style.get("GB1", beam_style["B1"]))

        if dir_b == "X":
            bx0 = alg.get("bx0", min(p1[0], p2[0]))
            bw = alg.get("bw", abs(p2[0] - p1[0]))
            by0 = alg.get("by0", alg["cl_y"] - bw_m / 2.0)
            r_b = patches.Rectangle((bx0, by0), bw, bw_m, facecolor=cfg["fc"], edgecolor=cfg["ec"], lw=1.8, alpha=0.92, zorder=3)
            ax.add_patch(r_b)
            # Label model tag OUTSIDE the ground beam element (above beam)
            y_lbl = by0 + bw_m + 0.20
            ax.text(bx0 + bw / 2.0, y_lbl, tag, ha="center", va="bottom", color=cfg["tc"], fontweight="bold", fontsize=10.5, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15", fc="#ffffff", ec=cfg["ec"], lw=1.0, alpha=0.95))
        elif dir_b == "Y":
            by0 = alg.get("by0", min(p1[1], p2[1]))
            bh = alg.get("bh", abs(p2[1] - p1[1]))
            bx0 = alg.get("bx0", alg["cl_x"] - bw_m / 2.0)
            r_b = patches.Rectangle((bx0, by0), bw_m, bh, facecolor=cfg["fc"], edgecolor=cfg["ec"], lw=1.8, alpha=0.92, zorder=3)
            ax.add_patch(r_b)
            # Label model tag OUTSIDE the ground beam element (to the right of beam)
            x_lbl = bx0 + bw_m + 0.20
            ax.text(x_lbl, by0 + bh / 2.0, tag, ha="left", va="center", color=cfg["tc"], fontweight="bold", fontsize=10.5, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15", fc="#ffffff", ec=cfg["ec"], lw=1.0, alpha=0.95))
        else:
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            th_gb = math.atan2(dy, dx)
            nx_gb = -math.sin(th_gb) * bw_m / 2.0
            ny_gb = math.cos(th_gb) * bw_m / 2.0
            poly_b = patches.Polygon([
                (p1[0] + nx_gb, p1[1] + ny_gb), (p2[0] + nx_gb, p2[1] + ny_gb),
                (p2[0] - nx_gb, p2[1] - ny_gb), (p1[0] - nx_gb, p1[1] - ny_gb)
            ], facecolor=cfg["fc"], edgecolor=cfg["ec"], lw=1.8, alpha=0.92, zorder=3)
            ax.add_patch(poly_b)
            mid_x = (p1[0] + p2[0]) / 2.0 + nx_gb * 1.4
            mid_y = (p1[1] + p2[1]) / 2.0 + ny_gb * 1.4
            rot_deg = math.degrees(th_gb)
            if rot_deg > 90:
                rot_deg -= 180
            elif rot_deg < -90:
                rot_deg += 180
            ax.text(mid_x, mid_y, tag, ha="center", va="center", rotation=rot_deg, color=cfg["tc"], fontweight="bold", fontsize=10.5, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15", fc="#ffffff", ec=cfg["ec"], lw=1.0, alpha=0.95))

    # Draw Columns
    for c in active_cols:
        cx = float(c.get("center_x", c.get("x", 0.0)))
        cy = float(c.get("center_y", c.get("y", 0.0)))
        cw = float(c.get("width_m", c.get("tc", 50.0) / 100.0))
        ch = float(c.get("height_m", c.get("bc", 30.0) / 100.0))
        cr = patches.Rectangle((cx - cw / 2.0, cy - ch / 2.0), cw, ch, facecolor="#1e293b", edgecolor="#0f172a", lw=1.4, zorder=5)
        ax.add_patch(cr)

    # Dynamic Legend placed cleanly below drawing in ax_leg (English Only, 2 Lines, 1.7x panel)
    leg_items = [
        "■ B1: Heavy Ground Beams",
        "■ B2: Medium Ground Beams",
        "■ B3: Light Ground Beams",
    ]
    items_str = "    |    ".join([f"[ {it} ]" for it in leg_items])
    leg_str = f"GROUND BEAM MODELS (LEGEND)\n{items_str}"
    ax_leg.text(0.5, 0.5, leg_str, ha="center", va="center", fontsize=12.5, fontweight="bold", color="#1e293b",
                bbox=dict(boxstyle="round,pad=0.6", fc="#ffffff", ec="#cbd5e1", lw=1.5, alpha=0.98))

    ax.set_xlim(x_min_slab - 1.8, x_max_slab + 1.2)
    ax.set_ylim(y_min_slab - 0.8, y_max_slab + 1.8)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig


# ── PAGE 5: Roof Beams & Cantilevers Design (مسقط بأسماء النماذج فقط) ──────────
def draw_page5_roof_beams_plan(
    rb_analysis: Dict[str, Any],
    active_cols: List[Dict[str, Any]],
    Lx_spans: Optional[List[float]] = None,
    Ly_spans: Optional[List[float]] = None,
    cantilevers: Optional[Dict[str, float]] = None,
    slab_bounds: Optional[Dict[str, Any]] = None,
) -> plt.Figure:
    """
    Page 5: Roof beams & cantilevers layout plan synchronized 100% with actual user inputs.
    Displays modeled roof drop beams (B1, B2, B3) and cantilever beams (CB1) with their dimensions (b x t),
    slab footprint, cantilever zones, grid lines, and columns.
    Legend is positioned cleanly below the drawing in a dedicated enlarged subplot (1.7x panel).
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, (ax, ax_leg) = plt.subplots(
        2, 1, figsize=(14, 8.5), dpi=140, facecolor="#ffffff",
        gridspec_kw={"height_ratios": [1, 0.14], "hspace": 0.07}
    )
    ax.set_facecolor("#f8fafc")
    ax_leg.set_facecolor("#ffffff")
    ax_leg.axis("off")

    from modules.roof_beam_layout import _get_grid_axes_rb, _hdim, _vdim

    unique_xs, unique_ys, label_map_x, label_map_y = _get_grid_axes_rb(active_cols) if active_cols else ([], [], {}, {})

    # Fallback if active_cols was empty
    if not unique_xs and Lx_spans:
        x_g = [0.0]
        for lx in Lx_spans: x_g.append(x_g[-1] + float(lx))
        unique_xs = x_g
        label_map_x = {x: f"Y{i+1}" for i, x in enumerate(x_g)}
    if not unique_ys and Ly_spans:
        y_g = [0.0]
        for ly in Ly_spans: y_g.append(y_g[-1] + float(ly))
        unique_ys = y_g
        label_map_y = {y: f"X{i+1}" for i, y in enumerate(y_g)}

    eff_sb = slab_bounds or (rb_analysis.get("slab_bounds") if rb_analysis else None) or {}
    c_dict = (cantilevers or {}) or (rb_analysis.get("cantilevers") if rb_analysis else {}) or {}
    cant_l = float(eff_sb.get("cant_left", c_dict.get("left", 0.0) or 0.0) or 0.0)
    cant_r = float(eff_sb.get("cant_right", c_dict.get("right", 0.0) or 0.0) or 0.0)
    cant_b = float(eff_sb.get("cant_bottom", c_dict.get("bottom", 0.0) or 0.0) or 0.0)
    cant_t = float(eff_sb.get("cant_top", c_dict.get("top", 0.0) or 0.0) or 0.0)

    col_xs = [float(c.get("center_x", c.get("x", 0.0))) for c in active_cols] if active_cols else [0.0]
    col_ys = [float(c.get("center_y", c.get("y", 0.0))) for c in active_cols] if active_cols else [0.0]

    x_core_min = float(eff_sb.get("min_x", unique_xs[0] if unique_xs else min(col_xs)))
    x_core_max = float(eff_sb.get("max_x", unique_xs[-1] if unique_xs else max(col_xs)))
    y_core_min = float(eff_sb.get("min_y", unique_ys[0] if unique_ys else min(col_ys)))
    y_core_max = float(eff_sb.get("max_y", unique_ys[-1] if unique_ys else max(col_ys)))

    x_slab_min = x_core_min - cant_l
    x_slab_max = x_core_max + cant_r
    y_slab_min = y_core_min - cant_b
    y_slab_max = y_core_max + cant_t

    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min

    # Slab footprint
    ax.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, slab_h,
                                  facecolor="#f8fafc", edgecolor="#334155", lw=2.0, zorder=1))

    has_cant = (cant_l > 0.05 or cant_r > 0.05 or cant_t > 0.05 or cant_b > 0.05)
    if has_cant:
        core_w = x_core_max - x_core_min
        core_h = y_core_max - y_core_min
        if core_w > 0 and core_h > 0:
            ax.add_patch(patches.Rectangle((x_core_min, y_core_min), core_w, core_h,
                                          facecolor="none", edgecolor="#94a3b8", lw=1.2, ls="--", zorder=1.4))
        if cant_l > 0.05:
            ax.add_patch(patches.Rectangle((x_slab_min, y_slab_min), cant_l, slab_h,
                                          facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.0, ls=":", alpha=0.5, zorder=1.2))
            ax.text(x_slab_min + cant_l / 2.0, (y_slab_min + y_slab_max) / 2.0, f"Left Cantilever ({cant_l:.2f}m)",
                    ha="center", va="center", fontsize=8.0, color="#b45309", fontweight="bold", rotation=90, zorder=2)
        if cant_r > 0.05:
            ax.add_patch(patches.Rectangle((x_core_max, y_slab_min), cant_r, slab_h,
                                          facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.0, ls=":", alpha=0.5, zorder=1.2))
            ax.text(x_core_max + cant_r / 2.0, (y_slab_min + y_slab_max) / 2.0, f"Right Cantilever ({cant_r:.2f}m)",
                    ha="center", va="center", fontsize=8.0, color="#b45309", fontweight="bold", rotation=90, zorder=2)
        if cant_t > 0.05:
            ax.add_patch(patches.Rectangle((x_slab_min, y_core_max), slab_w, cant_t,
                                          facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.0, ls=":", alpha=0.5, zorder=1.2))
            ax.text((x_slab_min + x_slab_max) / 2.0, y_core_max + cant_t / 2.0, f"Top Cantilever ({cant_t:.2f}m)",
                    ha="center", va="center", fontsize=8.0, color="#b45309", fontweight="bold", zorder=2)
        if cant_b > 0.05:
            ax.add_patch(patches.Rectangle((x_slab_min, y_slab_min), slab_w, cant_b,
                                          facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.0, ls=":", alpha=0.5, zorder=1.2))
            ax.text((x_slab_min + x_slab_max) / 2.0, y_slab_min + cant_b / 2.0, f"Bottom Cantilever ({cant_b:.2f}m)",
                    ha="center", va="center", fontsize=8.0, color="#b45309", fontweight="bold", zorder=2)

    # Grid lines & bubbles
    min_gx = unique_xs[0] if unique_xs else x_core_min
    max_gx = unique_xs[-1] if unique_xs else x_core_max
    min_gy = unique_ys[0] if unique_ys else y_core_min
    max_gy = unique_ys[-1] if unique_ys else y_core_max

    y_bubble_top = max(y_slab_max, max_gy) + 1.2
    x_bubble_left = min(x_slab_min, min_gx) - 1.2

    for idx, gx in enumerate(unique_xs, start=1):
        lbl = label_map_x.get(gx, f"Y{idx}")
        ax.plot([gx, gx], [min(y_slab_min, min_gy) - 0.4, y_bubble_top], color="#94a3b8", ls="--", lw=0.9, zorder=1)
        ax.text(gx, y_bubble_top, lbl, ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=9.5,
                bbox=dict(boxstyle="circle,pad=0.25", fc="#f8fafc", ec="#334155", lw=1.2), zorder=8)
    for idx, gy in enumerate(unique_ys, start=1):
        lbl = label_map_y.get(gy, f"X{idx}")
        ax.plot([x_bubble_left, max(x_slab_max, max_gx) + 0.4], [gy, gy], color="#94a3b8", ls="--", lw=0.9, zorder=1)
        ax.text(x_bubble_left, gy, lbl, ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=9.5,
                bbox=dict(boxstyle="circle,pad=0.25", fc="#f8fafc", ec="#334155", lw=1.2), zorder=8)

    beam_style = {
        "B1": {"fc": "#dbeafe", "ec": "#1d4ed8", "tc": "#1e40af", "badge_bg": "#eff6ff", "hatch": None},
        "B2": {"fc": "#dcfce7", "ec": "#15803d", "tc": "#166534", "badge_bg": "#f0fdf4", "hatch": None},
        "B3": {"fc": "#f3e8ff", "ec": "#7e22ce", "tc": "#6b21a8", "badge_bg": "#faf5ff", "hatch": None},
        "CB1": {"fc": "#ffedd5", "ec": "#ea580c", "tc": "#9a3412", "badge_bg": "#fff7ed", "hatch": "///"},
    }

    all_beams = rb_analysis.get("all_roof_beams", []) if rb_analysis else []
    for b in all_beams:
        p1 = b["p1"]
        p2 = b["p2"]
        bw_m = float(b.get("b_cm", 25.0)) / 100.0
        t_cm = int(b.get("exec_t_cm", b.get("t_calc", 50.0)))
        b_cm = int(b.get("b_cm", 25.0))
        tag = b.get("tag", b.get("model_mark", "GB1"))
        cfg = beam_style.get(tag, beam_style.get("GB1", beam_style["B1"]))

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        if abs(dx) >= abs(dy):
            bx0 = min(p1[0], p2[0])
            bw = abs(dx)
            by0 = p1[1] - bw_m / 2.0
            r_b = patches.Rectangle((bx0, by0), bw, bw_m, facecolor=cfg["fc"], edgecolor=cfg["ec"],
                                    hatch=cfg["hatch"], lw=1.8, alpha=0.92, zorder=3)
            ax.add_patch(r_b)
            # Label model tag ONLY (no dimensions) OUTSIDE the beam (above beam)
            y_lbl = by0 + bw_m + 0.20
            ax.text(bx0 + bw / 2.0, y_lbl, tag, ha="center", va="bottom", color=cfg["tc"], fontweight="bold", fontsize=10.5, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15", fc="#ffffff", ec=cfg["ec"], lw=1.0, alpha=0.95))
        else:
            by0 = min(p1[1], p2[1])
            bh = abs(dy)
            bx0 = p1[0] - bw_m / 2.0
            r_b = patches.Rectangle((bx0, by0), bw_m, bh, facecolor=cfg["fc"], edgecolor=cfg["ec"],
                                    hatch=cfg["hatch"], lw=1.8, alpha=0.92, zorder=3)
            ax.add_patch(r_b)
            # Label model tag ONLY (no dimensions) OUTSIDE the beam (to the right of beam)
            x_lbl = bx0 + bw_m + 0.20
            ax.text(x_lbl, by0 + bh / 2.0, tag, ha="left", va="center", color=cfg["tc"], fontweight="bold", fontsize=10.5, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15", fc="#ffffff", ec=cfg["ec"], lw=1.0, alpha=0.95))

    # Draw Columns with label OUTSIDE the column
    for c in active_cols:
        cx = float(c.get("center_x", c.get("x", 0.0)))
        cy = float(c.get("center_y", c.get("y", 0.0)))
        cw = float(c.get("width_m", c.get("tc", 50.0) / 100.0))
        ch = float(c.get("height_m", c.get("bc", 30.0) / 100.0))
        cr = patches.Rectangle((cx - cw / 2.0, cy - ch / 2.0), cw, ch, facecolor="#1e293b", edgecolor="#0f172a", lw=1.4, zorder=5)
        ax.add_patch(cr)
        c_lbl = str(c.get("model_mark") or c.get("orig_id") or c.get("id", "C")).split("(")[0].strip()
        y_clbl = cy + ch / 2.0 + 0.25
        ax.text(cx, y_clbl, c_lbl, ha="center", va="bottom", color="#1e293b", fontweight="bold", fontsize=10.5,
                bbox=dict(boxstyle="round,pad=0.18", fc="#ffffff", ec="#334155", lw=1.2, alpha=0.95), zorder=7)

    # Dynamic Legend placed cleanly below drawing in ax_leg (English Only, 2 Lines, 1.7x panel)
    models_dict = rb_analysis.get("models_dict", {}) if rb_analysis else {}
    leg_items = []
    for mk in ["B1", "B2", "B3", "CB1"]:
        if mk in models_dict:
            m = models_dict[mk]
            if mk == "CB1":
                dot = f"■ CB1: Cantilever Beam [{m['dimensions_str']} cm]"
            else:
                dot = f"■ {mk}: Drop Beam [{m['dimensions_str']} cm]"
            leg_items.append(dot)
    if not leg_items:
        leg_items = [
            "■ B1: Drop Beam [25×60 cm]",
            "■ B2: Drop Beam [25×50 cm]",
            "■ B3: Drop Beam [25×40 cm]",
            "■ CB1: Cantilever Beam [25×60 cm]",
        ]
    items_str = "    |    ".join([f"[ {it} ]" for it in leg_items])
    leg_str = f"ROOF BEAMS & CANTILEVERS (LEGEND)\n{items_str}"
    ax_leg.text(0.5, 0.5, leg_str, ha="center", va="center", fontsize=12.5, fontweight="bold", color="#1e293b",
                bbox=dict(boxstyle="round,pad=0.6", fc="#ffffff", ec="#cbd5e1", lw=1.5, alpha=0.98))

    ax.set_xlim(x_slab_min - 1.8, x_slab_max + 1.2)
    ax.set_ylim(y_slab_min - 0.8, y_slab_max + 1.8)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig


# ── PAGE 6: Slab Bottom Reinforcement Plan (الرقة السفلية + الإضافي بالاتجاهين) ─
def draw_page6_slab_bottom_rebar(
    Lx_spans: List[float],
    Ly_spans: List[float],
    cantilevers: Dict[str, float],
    btm_extra_spans: List[Dict[str, Any]],
    n_mesh_btm: float,
    bottom_mesh_dia: int,
    active_cols: List[Dict[str, Any]],
    void_boxes: Optional[List[Any]] = None,
) -> plt.Figure:
    """
    Page 6: Slab Bottom Rebar Plan with Base Mesh & Extra Bottom Bars in X and Y directions.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, ax = plt.subplots(figsize=(14, 8.5), dpi=140, facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")

    cant_l = float(cantilevers.get("left", 0.0) or 0.0) if cantilevers else 0.0
    cant_r = float(cantilevers.get("right", 0.0) or 0.0) if cantilevers else 0.0
    cant_b = float(cantilevers.get("bottom", 0.0) or 0.0) if cantilevers else 0.0
    cant_t = float(cantilevers.get("top", 0.0) or 0.0) if cantilevers else 0.0

    x_grid = [0.0]
    for lx in Lx_spans: x_grid.append(x_grid[-1] + float(lx))
    y_grid = [0.0]
    for ly in Ly_spans: y_grid.append(y_grid[-1] + float(ly))

    x_min_slab = x_grid[0] - cant_l
    x_max_slab = x_grid[-1] + cant_r
    y_min_slab = y_grid[0] - cant_b
    y_max_slab = y_grid[-1] + cant_t

    # Slab boundary
    ax.add_patch(patches.Rectangle((x_min_slab, y_min_slab), x_max_slab - x_min_slab, y_max_slab - y_min_slab,
                                  facecolor="#ffffff", edgecolor="#0f172a", lw=2.2, zorder=1))

    # Grid lines
    for idx, gx in enumerate(x_grid, 1):
        ax.plot([gx, gx], [y_min_slab - 0.3, y_max_slab + 0.8], color="#cbd5e1", ls="--", lw=0.9, zorder=1)
        ax.text(gx, y_max_slab + 0.9, f"Y{idx}", ha="center", va="center", color="#334155", fontweight="bold", fontsize=9,
                bbox=dict(boxstyle="circle,pad=0.22", fc="#f8fafc", ec="#475569", lw=1.0), zorder=8)
    for idx, gy in enumerate(y_grid, 1):
        ax.plot([x_min_slab - 0.8, x_max_slab + 0.3], [gy, gy], color="#cbd5e1", ls="--", lw=0.9, zorder=1)
        ax.text(x_min_slab - 0.9, gy, f"X{idx}", ha="center", va="center", color="#334155", fontweight="bold", fontsize=9,
                bbox=dict(boxstyle="circle,pad=0.22", fc="#f8fafc", ec="#475569", lw=1.0), zorder=8)

    # Voids
    if void_boxes:
        for vb in void_boxes:
            if len(vb) >= 4:
                vx1, vx2, vy1, vy2 = vb[0], vb[1], vb[2], vb[3]
                vr = patches.Rectangle((vx1, vy1), vx2 - vx1, vy2 - vy1, facecolor="#fee2e2", edgecolor="#ef4444", lw=1.5, zorder=2)
                ax.add_patch(vr)
                ax.plot([vx1, vx2], [vy1, vy2], color="#ef4444", lw=1.0, ls="--", zorder=3)
                ax.plot([vx1, vx2], [vy2, vy1], color="#ef4444", lw=1.0, ls="--", zorder=3)

    # Columns
    for c in active_cols:
        cx = float(c.get("center_x", c.get("x", 0.0)))
        cy = float(c.get("center_y", c.get("y", 0.0)))
        cw = float(c.get("width_m", c.get("tc", 50.0) / 100.0))
        ch = float(c.get("height_m", c.get("bc", 30.0) / 100.0))
        cr = patches.Rectangle((cx - cw / 2.0, cy - ch / 2.0), cw, ch, facecolor="#334155", edgecolor="#0f172a", lw=1.2, zorder=4)
        ax.add_patch(cr)

    # Bottom Extra Reinforcement in both directions (X & Y)
    has_any_extra = False
    if btm_extra_spans:
        for sp in btm_extra_spans:
            req_as = float(sp.get("As_extra_req", sp.get("req_as", 0.0)))
            if req_as > 0.05:
                has_any_extra = True
                d_dir = str(sp.get("dir", sp.get("direction", "X"))).upper()
                nb = int(sp.get("n_bars", sp.get("n", 4)))
                dia = int(sp.get("dia", sp.get("phi", 12)))
                L_m = float(sp.get("bar_len", sp.get("L", 3.8)))

                # Span centers
                x_mid = float(sp.get("center_x", sp.get("x", (x_grid[0] + x_grid[-1]) / 2.0)))
                y_mid = float(sp.get("center_y", sp.get("y", (y_grid[0] + y_grid[-1]) / 2.0)))

                if d_dir == "X":
                    bx1 = x_mid - L_m / 2.0
                    bx2 = x_mid + L_m / 2.0
                    # Horizontal blue bar with hooks
                    ax.plot([bx1, bx2], [y_mid - 0.25, y_mid - 0.25], color="#1d4ed8", lw=3.0, zorder=6)
                    ax.plot([bx1, bx1], [y_mid - 0.25, y_mid - 0.10], color="#1d4ed8", lw=2.5, zorder=6)
                    ax.plot([bx2, bx2], [y_mid - 0.25, y_mid - 0.10], color="#1d4ed8", lw=2.5, zorder=6)
                    ax.text(x_mid, y_mid - 0.45, f"Bottom Extra X: + {nb}Ø{dia}/m (L={L_m:.2f}m)",
                            ha="center", va="top", fontsize=8.2, fontweight="bold", color="#1e3a8a",
                            bbox=dict(boxstyle="round,pad=0.12", fc="#eff6ff", ec="#3b82f6", lw=0.9, alpha=0.95), zorder=7)
                else:
                    by1 = y_mid - L_m / 2.0
                    by2 = y_mid + L_m / 2.0
                    # Vertical purple bar with hooks
                    ax.plot([x_mid + 0.25, x_mid + 0.25], [by1, by2], color="#7e22ce", lw=3.0, zorder=6)
                    ax.plot([x_mid + 0.25, x_mid + 0.40], [by1, by1], color="#7e22ce", lw=2.5, zorder=6)
                    ax.plot([x_mid + 0.25, x_mid + 0.40], [by2, by2], color="#7e22ce", lw=2.5, zorder=6)
                    ax.text(x_mid + 0.50, y_mid, f"Bottom Extra Y: + {nb}Ø{dia}/m (L={L_m:.2f}m)",
                            ha="left", va="center", rotation=90, fontsize=8.2, fontweight="bold", color="#581c87",
                            bbox=dict(boxstyle="round,pad=0.12", fc="#faf5ff", ec="#a855f7", lw=0.9, alpha=0.95), zorder=7)

    # Base Mesh Banner Box
    mesh_box_text = f"Bottom Base Mesh: {n_mesh_btm:.0f}Ø{bottom_mesh_dia}/m (Both Directions T1 & T2)"
    if not has_any_extra:
        mesh_box_text += "\n[OK] Base mesh is sufficient to resist all positive moments — No bottom extra rebar required"
    ax.text(0.50, 0.96, mesh_box_text, transform=ax.transAxes, ha="center", va="top",
            fontsize=10.5, fontweight="bold", color="#064e3b",
            bbox=dict(boxstyle="round,pad=0.45", fc="#dcfce7", ec="#16a34a", lw=1.6, alpha=0.96), zorder=9)

    ax.set_xlim(x_min_slab - 1.6, x_max_slab + 1.2)
    ax.set_ylim(y_min_slab - 0.8, y_max_slab + 1.6)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig


# ── PAGE 7: Slab Top Reinforcement Plan (الرقة العلوية + شوك الكوابيل) ────────
def draw_page7_slab_top_rebar(
    Lx_spans: List[float],
    Ly_spans: List[float],
    cantilevers: Dict[str, float],
    cant_rft_list: Optional[List[Dict[str, Any]]],
    n_mesh_top: float,
    top_mesh_dia: int,
    active_cols: List[Dict[str, Any]],
    void_boxes: Optional[List[Any]] = None,
) -> plt.Figure:
    """
    Page 7: Slab Top Rebar Plan with Base Top Mesh & Cantilever Forks (شوك الكوابيل).
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, ax = plt.subplots(figsize=(14, 8.5), dpi=140, facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")

    cant_l = float(cantilevers.get("left", 0.0) or 0.0) if cantilevers else 0.0
    cant_r = float(cantilevers.get("right", 0.0) or 0.0) if cantilevers else 0.0
    cant_b = float(cantilevers.get("bottom", 0.0) or 0.0) if cantilevers else 0.0
    cant_t = float(cantilevers.get("top", 0.0) or 0.0) if cantilevers else 0.0

    x_grid = [0.0]
    for lx in Lx_spans: x_grid.append(x_grid[-1] + float(lx))
    y_grid = [0.0]
    for ly in Ly_spans: y_grid.append(y_grid[-1] + float(ly))

    x_min_slab = x_grid[0] - cant_l
    x_max_slab = x_grid[-1] + cant_r
    y_min_slab = y_grid[0] - cant_b
    y_max_slab = y_grid[-1] + cant_t

    # Slab boundary
    ax.add_patch(patches.Rectangle((x_min_slab, y_min_slab), x_max_slab - x_min_slab, y_max_slab - y_min_slab,
                                  facecolor="#ffffff", edgecolor="#0f172a", lw=2.2, zorder=1))

    # Grid lines
    for idx, gx in enumerate(x_grid, 1):
        ax.plot([gx, gx], [y_min_slab - 0.3, y_max_slab + 0.8], color="#cbd5e1", ls="--", lw=0.9, zorder=1)
        ax.text(gx, y_max_slab + 0.9, f"Y{idx}", ha="center", va="center", color="#334155", fontweight="bold", fontsize=9,
                bbox=dict(boxstyle="circle,pad=0.22", fc="#f8fafc", ec="#475569", lw=1.0), zorder=8)
    for idx, gy in enumerate(y_grid, 1):
        ax.plot([x_min_slab - 0.8, x_max_slab + 0.3], [gy, gy], color="#cbd5e1", ls="--", lw=0.9, zorder=1)
        ax.text(x_min_slab - 0.9, gy, f"X{idx}", ha="center", va="center", color="#334155", fontweight="bold", fontsize=9,
                bbox=dict(boxstyle="circle,pad=0.22", fc="#f8fafc", ec="#475569", lw=1.0), zorder=8)

    # Columns
    for c in active_cols:
        cx = float(c.get("center_x", c.get("x", 0.0)))
        cy = float(c.get("center_y", c.get("y", 0.0)))
        cw = float(c.get("width_m", c.get("tc", 50.0) / 100.0))
        ch = float(c.get("height_m", c.get("bc", 30.0) / 100.0))
        cr = patches.Rectangle((cx - cw / 2.0, cy - ch / 2.0), cw, ch, facecolor="#334155", edgecolor="#0f172a", lw=1.2, zorder=4)
        ax.add_patch(cr)

    # Draw Cantilever Forks / Shok (U-bars)
    has_cantilevers = False
    cant_sides = [
        ("left", cant_l, x_min_slab, 0.0, "H"),
        ("right", cant_r, x_max_slab, x_grid[-1], "H"),
        ("bottom", cant_b, y_min_slab, 0.0, "V"),
        ("top", cant_t, y_max_slab, y_grid[-1], "V"),
    ]

    for side, c_val, c_outer, c_inner, orient in cant_sides:
        if c_val > 0.15:
            has_cantilevers = True
            ext_len = c_val * 1.50
            dia_cant = 16
            n_cant = 6

            if side == "left":
                x_tip = c_outer + 0.10
                x_end = c_inner + ext_len
                for gy in y_grid:
                    # Draw U-bar with hook
                    ax.plot([x_tip, x_end], [gy, gy], color="#dc2626", lw=2.6, zorder=6)
                    ax.plot([x_tip, x_tip], [gy - 0.15, gy + 0.15], color="#dc2626", lw=2.6, zorder=6)
                    ax.plot([x_end, x_end], [gy, gy - 0.15], color="#dc2626", lw=2.2, zorder=6)
                ax.text(x_min_slab + c_val / 2.0, (y_grid[0] + y_grid[-1]) / 2.0,
                        f"Left Cantilever Forks:\n{n_cant}Ø{dia_cant}/m (L_tot={c_val + ext_len:.2f}m)",
                        ha="center", va="center", rotation=90, fontsize=8.5, fontweight="bold", color="#991b1b",
                        bbox=dict(boxstyle="round,pad=0.15", fc="#fef2f2", ec="#ef4444", lw=1.0, alpha=0.92), zorder=7)

            elif side == "right":
                x_tip = c_outer - 0.10
                x_end = c_inner - ext_len
                for gy in y_grid:
                    ax.plot([x_end, x_tip], [gy, gy], color="#dc2626", lw=2.6, zorder=6)
                    ax.plot([x_tip, x_tip], [gy - 0.15, gy + 0.15], color="#dc2626", lw=2.6, zorder=6)
                    ax.plot([x_end, x_end], [gy, gy - 0.15], color="#dc2626", lw=2.2, zorder=6)
                ax.text(x_max_slab - c_val / 2.0, (y_grid[0] + y_grid[-1]) / 2.0,
                        f"Right Cantilever Forks:\n{n_cant}Ø{dia_cant}/m (L_tot={c_val + ext_len:.2f}m)",
                        ha="center", va="center", rotation=90, fontsize=8.5, fontweight="bold", color="#991b1b",
                        bbox=dict(boxstyle="round,pad=0.15", fc="#fef2f2", ec="#ef4444", lw=1.0, alpha=0.92), zorder=7)

            elif side == "bottom":
                y_tip = c_outer + 0.10
                y_end = c_inner + ext_len
                for gx in x_grid:
                    ax.plot([gx, gx], [y_tip, y_end], color="#dc2626", lw=2.6, zorder=6)
                    ax.plot([gx - 0.15, gx + 0.15], [y_tip, y_tip], color="#dc2626", lw=2.6, zorder=6)
                    ax.plot([gx, gx - 0.15], [y_end, y_end], color="#dc2626", lw=2.2, zorder=6)
                ax.text((x_grid[0] + x_grid[-1]) / 2.0, y_min_slab + c_val / 2.0,
                        f"Bottom Cantilever Forks: {n_cant}Ø{dia_cant}/m (L_tot={c_val + ext_len:.2f}m)",
                        ha="center", va="center", fontsize=8.5, fontweight="bold", color="#991b1b",
                        bbox=dict(boxstyle="round,pad=0.15", fc="#fef2f2", ec="#ef4444", lw=1.0, alpha=0.92), zorder=7)

            elif side == "top":
                y_tip = c_outer - 0.10
                y_end = c_inner - ext_len
                for gx in x_grid:
                    ax.plot([gx, gx], [y_end, y_tip], color="#dc2626", lw=2.6, zorder=6)
                    ax.plot([gx - 0.15, gx + 0.15], [y_tip, y_tip], color="#dc2626", lw=2.6, zorder=6)
                    ax.plot([gx, gx - 0.15], [y_end, y_end], color="#dc2626", lw=2.2, zorder=6)
                ax.text((x_grid[0] + x_grid[-1]) / 2.0, y_max_slab - c_val / 2.0,
                        f"Top Cantilever Forks: {n_cant}Ø{dia_cant}/m (L_tot={c_val + ext_len:.2f}m)",
                        ha="center", va="center", fontsize=8.5, fontweight="bold", color="#991b1b",
                        bbox=dict(boxstyle="round,pad=0.15", fc="#fef2f2", ec="#ef4444", lw=1.0, alpha=0.92), zorder=7)

    # Top Mesh Banner Box
    top_mesh_box = f"Top Base Mesh: {n_mesh_top:.0f}Ø{top_mesh_dia}/m (Both Directions T1 & T2)"
    if not has_cantilevers:
        top_mesh_box += "\nℹ️ No exterior cantilevers — Top base mesh distributed across full slab area"
    ax.text(0.50, 0.96, top_mesh_box, transform=ax.transAxes, ha="center", va="top",
            fontsize=10.5, fontweight="bold", color="#1e3a8a",
            bbox=dict(boxstyle="round,pad=0.45", fc="#eff6ff", ec="#2563eb", lw=1.6, alpha=0.96), zorder=9)

    ax.set_xlim(x_min_slab - 1.6, x_max_slab + 1.2)
    ax.set_ylim(y_min_slab - 0.8, y_max_slab + 1.6)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig


# ── PAGE 8: Column Caps Reinforcement (الإضافي العلوي فوق الأعمدة) ─────────────
def draw_page8_column_caps(
    Lx_spans: List[float],
    Ly_spans: List[float],
    cantilevers: Dict[str, float],
    ts_cm: float,
    top_extra_cols: List[Dict[str, Any]],
    active_cols: List[Dict[str, Any]],
    void_boxes: Optional[List[Any]] = None,
) -> plt.Figure:
    """
    Page 8: Over-Column Caps Top Extra Reinforcement in both directions with exact callouts.
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, ax = plt.subplots(figsize=(14, 8.5), dpi=140, facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")

    cant_l = float(cantilevers.get("left", 0.0) or 0.0) if cantilevers else 0.0
    cant_r = float(cantilevers.get("right", 0.0) or 0.0) if cantilevers else 0.0
    cant_b = float(cantilevers.get("bottom", 0.0) or 0.0) if cantilevers else 0.0
    cant_t = float(cantilevers.get("top", 0.0) or 0.0) if cantilevers else 0.0

    x_grid = [0.0]
    for lx in Lx_spans: x_grid.append(x_grid[-1] + float(lx))
    y_grid = [0.0]
    for ly in Ly_spans: y_grid.append(y_grid[-1] + float(ly))

    x_min_slab = x_grid[0] - cant_l
    x_max_slab = x_grid[-1] + cant_r
    y_min_slab = y_grid[0] - cant_b
    y_max_slab = y_grid[-1] + cant_t

    # Slab boundary
    ax.add_patch(patches.Rectangle((x_min_slab, y_min_slab), x_max_slab - x_min_slab, y_max_slab - y_min_slab,
                                  facecolor="#ffffff", edgecolor="#0f172a", lw=2.2, zorder=1))

    # Grid lines
    for idx, gx in enumerate(x_grid, 1):
        ax.plot([gx, gx], [y_min_slab - 0.3, y_max_slab + 0.8], color="#cbd5e1", ls="--", lw=0.9, zorder=1)
        ax.text(gx, y_max_slab + 0.9, f"Y{idx}", ha="center", va="center", color="#334155", fontweight="bold", fontsize=9,
                bbox=dict(boxstyle="circle,pad=0.22", fc="#f8fafc", ec="#475569", lw=1.0), zorder=8)
    for idx, gy in enumerate(y_grid, 1):
        ax.plot([x_min_slab - 0.8, x_max_slab + 0.3], [gy, gy], color="#cbd5e1", ls="--", lw=0.9, zorder=1)
        ax.text(x_min_slab - 0.9, gy, f"X{idx}", ha="center", va="center", color="#334155", fontweight="bold", fontsize=9,
                bbox=dict(boxstyle="circle,pad=0.22", fc="#f8fafc", ec="#475569", lw=1.0), zorder=8)

    # Columns
    for c in active_cols:
        cx = float(c.get("center_x", c.get("x", 0.0)))
        cy = float(c.get("center_y", c.get("y", 0.0)))
        cw = float(c.get("width_m", c.get("tc", 50.0) / 100.0))
        ch = float(c.get("height_m", c.get("bc", 30.0) / 100.0))
        cr = patches.Rectangle((cx - cw / 2.0, cy - ch / 2.0), cw, ch, facecolor="#1e293b", edgecolor="#0f172a", lw=1.4, zorder=4)
        ax.add_patch(cr)

        # Label ONLY column model/tag outside element (matching Page 4 font size 10.5 bold, no safe/unsafe text)
        col_tag = str(c.get("model_mark") or c.get("orig_id") or c.get("id", "C")).split("(")[0].strip()
        y_lbl = cy + ch / 2.0 + 0.28
        ax.text(cx, y_lbl, col_tag, ha="center", va="bottom", color="#1e293b", fontweight="bold", fontsize=10.5,
                bbox=dict(boxstyle="round,pad=0.18", fc="#ffffff", ec="#334155", lw=1.2, alpha=0.95), zorder=7)

    # Draw Column Caps (Top Extra over columns in both directions)
    if top_extra_cols:
        for cap in top_extra_cols:
            cx = float(cap.get("center_x", cap.get("x", 0.0)))
            cy = float(cap.get("center_y", cap.get("y", 0.0)))
            req_as = float(cap.get("As_extra_req", cap.get("req_as", cap.get("As_extra", 0.0))))
            is_needed = cap.get("is_needed", False) or (req_as > 0.05) or (int(cap.get("bars_per_m", 0)) > 0)
            nb = int(cap.get("n_bars", cap.get("bars_per_m", 5)))
            dia = int(cap.get("dia", cap.get("dia_extra", cap.get("phi", 12))))
            L_cap = float(cap.get("bar_len", cap.get("L_extra", cap.get("L", 2.40))))

            if is_needed:
                # Cap X-bars (Horizontal)
                x1, x2 = cx - L_cap / 2.0, cx + L_cap / 2.0
                ax.plot([x1, x2], [cy + 0.18, cy + 0.18], color="#b91c1c", lw=2.8, zorder=6)
                ax.plot([x1, x1], [cy + 0.18, cy + 0.08], color="#b91c1c", lw=2.4, zorder=6)
                ax.plot([x2, x2], [cy + 0.18, cy + 0.08], color="#b91c1c", lw=2.4, zorder=6)

                # Cap Y-bars (Vertical)
                y1, y2 = cy - L_cap / 2.0, cy + L_cap / 2.0
                ax.plot([cx + 0.18, cx + 0.18], [y1, y2], color="#991b1b", lw=2.8, zorder=6)
                ax.plot([cx + 0.18, cx + 0.08], [y1, y1], color="#991b1b", lw=2.4, zorder=6)
                ax.plot([cx + 0.18, cx + 0.08], [y2, y2], color="#991b1b", lw=2.4, zorder=6)

    # Title Banner Box
    title_text = "Column Caps Top Extra Reinforcement for Negative Moments & Punching Shear (ECP 203)"
    ax.text(0.50, 0.96, title_text, transform=ax.transAxes, ha="center", va="top",
            fontsize=10.5, fontweight="bold", color="#991b1b",
            bbox=dict(boxstyle="round,pad=0.40", fc="#fef2f2", ec="#ef4444", lw=1.6, alpha=0.96), zorder=9)

    ax.set_xlim(x_min_slab - 1.6, x_max_slab + 1.2)
    ax.set_ylim(y_min_slab - 0.8, y_max_slab + 1.6)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig


# ── FULL 8-PAGE HTML DOCUMENT BUILDER ─────────────────────────────────────────
def generate_concise_design_report_html(
    project_name: str,
    num_floors: int,
    ts: float,
    Fcu: float,
    Fy: float,
    Wu: float,
    SDL: float,
    wall_load: float,
    LL: float,
    img_page1_b64: str,
    img_page2_b64: str,
    img_page3_b64: str,
    img_page4_b64: str,
    img_page5_b64: str,
    img_page6_b64: str,
    img_page7_b64: str,
    img_page8_b64: str,
    cols_table_data: List[Dict[str, Any]],
    ftgs_table_data: List[Dict[str, Any]],
    gb_table_data: List[Dict[str, Any]],
    rb_table_data: List[Dict[str, Any]],
    mesh_btm_str: str,
    mesh_top_str: str,
    slab_area_val: float,
    btm_extra_spans: Optional[List[Dict[str, Any]]] = None,
    cant_rft_list: Optional[List[Dict[str, Any]]] = None,
    cantilevers: Optional[Dict[str, float]] = None,
    top_extra_cols: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Builds the complete 8-page standalone HTML calculation report ready for PDF printing.
    """
    # Filter and normalize tables for concise PDF:
    # 1. Page 2 Columns Table: exactly 5 cells (Model, Section, Longitudinal Rebar, Stirrups, Count)
    clean_cols_table = []
    if cols_table_data:
        for r in cols_table_data:
            def _find_val_c(terms, default="—"):
                for k, val in r.items():
                    if any(t.lower() in str(k).lower() for t in terms):
                        return val
                return default
            raw_model = str(_find_val_c(["column model", "نموذج العمود", "model", "tag"], "C1"))
            clean_model = raw_model.split("(")[0].strip() if "(" in raw_model else raw_model.strip()
            ordered = {
                "mark": clean_model,
                "b_t": _find_val_c(["section", "القطاع", "الأبعاد", "b × t"]),
                "rebar": _find_val_c(["longitudinal", "التسليح الرأسي", "التسليح الطولي", "rebar", "main"]),
                "ties": _find_val_c(["ties", "stirrups", "الكانات"]),
                "count": _find_val_c(["column count", "count", "العدد"]),
            }
            clean_cols_table.append(ordered)

    # 2. Page 3 Footings Table: exactly 5 cells (Model, Supported Columns, RC Footing, PC Footing, Reinforcement)
    # Excluded per user request: Classification, Design Axial Load, Structural Status
    clean_ftgs_table = []
    if ftgs_table_data:
        for r in ftgs_table_data:
            def _find_val_f(terms, default="—"):
                for k, val in r.items():
                    if any(t.lower() in str(k).lower() for t in terms):
                        return val
                return default
            raw_model = str(_find_val_f(["نموذج القاعدة", "footing model", "model", "mark"], "F1"))
            clean_model = raw_model.split("(")[0].strip() if "(" in raw_model else raw_model.strip()
            ordered = {
                "model": clean_model,
                "cols": _find_val_f(["الأعمدة المرتكزة", "supported columns", "نموذج العمود", "columns", "cols"]),
                "rc": _find_val_f(["أبعاد المسلحة", "rc footing", "r.c."]),
                "pc": _find_val_f(["أبعاد العادية", "pc footing", "p.c."]),
                "rft": _find_val_f(["التسليح", "reinforcement", "rft"]),
            }
            clean_ftgs_table.append(ordered)

    # 3. Page 4 Ground Beams Table: exactly 6 cells (Beam Mark, Section, Bottom, Top, Stirrups, Side Bars)
    # Excluded per user request: Classification, Count, Total Length
    clean_gb_table = []
    if gb_table_data:
        for r in gb_table_data:
            def _find_val_g(terms, default="—"):
                for k, val in r.items():
                    if any(t.lower() in str(k).lower() for t in terms):
                        return val
                return default
            ordered = {
                "mark": _find_val_g(["النموذج", "mark", "tag"]),
                "b_t": _find_val_g(["الأبعاد", "القطاع", "b × t", "section"]),
                "bot": _find_val_g(["السفلي", "bottom", "bot"]),
                "top": _find_val_g(["العلوي", "top"]),
                "stirrups": _find_val_g(["الكانات", "stirrups"]),
                "side": _find_val_g(["براندات", "side"]),
            }
            clean_gb_table.append(ordered)

    # 4. Page 5 Roof Beams Table: exactly 6 cells (Beam Mark, Section, Bottom, Top/Forks, Stirrups, Side Bars)
    # Excluded per user request: Classification, Count, Total Length (Identical structure to Page 4)
    clean_rb_table = []
    if rb_table_data:
        for r in rb_table_data:
            def _find_val_r(terms, default="—"):
                for k, val in r.items():
                    if any(t.lower() in str(k).lower() for t in terms):
                        return val
                return default
            ordered = {
                "mark": _find_val_r(["النموذج", "mark", "tag"]),
                "b_t": _find_val_r(["الأبعاد", "القطاع", "b × t", "section"]),
                "bot": _find_val_r(["السفلي", "bottom", "bot"]),
                "top": _find_val_r(["العلوي", "top", "شوك"]),
                "stirrups": _find_val_r(["الكانات", "stirrups"]),
                "side": _find_val_r(["براندات", "side"]),
            }
            clean_rb_table.append(ordered)

    # 5. Page 6 Slab Bottom Reinforcement Table (Base Mesh & Additional Bottom Rebar)
    clean_btm_table = []
    clean_btm_table.append({
        "comp": "Bottom Base Mesh (T1 & T2)",
        "zone": "Full Slab Area (Both Directions)",
        "rft": _clean_cell_to_en(mesh_btm_str),
        "cut_len": "Continuous across all spans",
        "notes": "Bottom Main Layer (ECP 203)",
    })
    has_btm_extra = False
    if btm_extra_spans:
        for sp in btm_extra_spans:
            req_as = float(sp.get("As_extra_req", sp.get("req_as", sp.get("delta_As", 0.0))))
            is_nec = sp.get("is_needed", False) or (req_as > 0.05) or (int(sp.get("n_extra", sp.get("bars_per_m", 0))) > 0)
            if is_nec:
                has_btm_extra = True
                s_dir = str(sp.get("dir", sp.get("direction", "X"))).upper()
                nb = int(sp.get("n_bars", sp.get("bars_per_m", sp.get("n_extra", 4))))
                dia = int(sp.get("dia", sp.get("dia_extra", sp.get("phi", 12))))
                L_m = float(sp.get("bar_len", sp.get("L_extra", sp.get("L", 3.8))))
                B_m = float(sp.get("B_zone", sp.get("w_ms", 2.4)))
                bay_lbl = str(sp.get("bay_label", sp.get("panel_id", "Mid-span Bay")))
                clean_btm_table.append({
                    "comp": f"Bottom Extra Rebar ({s_dir}-Dir)",
                    "zone": bay_lbl,
                    "rft": f"+ {nb}Ø{dia}/m",
                    "cut_len": f"L = {L_m:.2f} m",
                    "notes": f"Band B = {B_m:.2f} m (Mid-span)",
                })
    if not has_btm_extra:
        clean_btm_table.append({
            "comp": "Bottom Extra Reinforcement",
            "zone": "All Spans (X & Y Directions)",
            "rft": "None Required",
            "cut_len": "—",
            "notes": "Base mesh is 100% sufficient for all positive moments",
        })

    # 6. Page 7 Slab Top Reinforcement Table (Base Mesh & Cantilever Forks)
    clean_top_table = []
    clean_top_table.append({
        "comp": "Top Base Mesh (T1 & T2)",
        "zone": "Full Slab Area (Both Directions)",
        "rft": _clean_cell_to_en(mesh_top_str),
        "cut_len": "Continuous across full slab",
        "notes": "Top Layer for Shrinkage & Secondary Moments",
    })
    has_cant_forks = False
    if cant_rft_list:
        for cr in cant_rft_list:
            lc = float(cr.get("length", 0.0))
            if lc > 0.05:
                has_cant_forks = True
                side = str(cr.get("side", "Cantilever")).title()
                rft_txt = str(cr.get("rft_callout", "6Ø12/m'"))
                ext_l = float(cr.get("ext_length", lc * 1.5))
                L_tot = lc + ext_l
                clean_top_table.append({
                    "comp": "Cantilever Forks (U-bars / Shok)",
                    "zone": f"{side} Cantilever (L={lc:.2f}m)",
                    "rft": _clean_cell_to_en(rft_txt),
                    "cut_len": f"L_tot = {L_tot:.2f} m",
                    "notes": f"Ext inside = {ext_l:.2f}m (1.5 × L_cant)",
                })
    elif cantilevers:
        for c_side, c_val in cantilevers.items():
            if float(c_val or 0.0) > 0.05:
                has_cant_forks = True
                lc = float(c_val)
                ext_l = lc * 1.5
                clean_top_table.append({
                    "comp": "Cantilever Forks (U-bars / Shok)",
                    "zone": f"{c_side.title()} Cantilever (L={lc:.2f}m)",
                    "rft": "6Ø12/m",
                    "cut_len": f"L_tot = {lc + ext_l:.2f} m",
                    "notes": f"Ext inside = {ext_l:.2f}m (1.5 × L_cant)",
                })
    if not has_cant_forks:
        clean_top_table.append({
            "comp": "Cantilever Forks / Top Extra",
            "zone": "Perimeter & Cantilever Zones",
            "rft": "None Required",
            "cut_len": "—",
            "notes": "No exterior cantilevers — Top base mesh covers entire slab",
        })

    # 7. Page 8 Column Caps Top Reinforcement Table
    clean_caps_table = []
    has_cap_extras = False
    if top_extra_cols:
        for cap in top_extra_cols:
            req_as = float(cap.get("As_extra_req", cap.get("req_as", cap.get("As_extra", 0.0))))
            is_nec = cap.get("is_needed", False) or (req_as > 0.05) or (int(cap.get("bars_per_m", 0)) > 0)
            if is_nec:
                has_cap_extras = True
                cid = str(cap.get("col_id", cap.get("id", "C"))).split("(")[0].strip()
                ctype = str(cap.get("type", "Column")).title()
                grid_txt = str(cap.get("grid", "—"))
                bx = int(cap.get("bars_per_m_x", cap.get("bars_per_m", 4)))
                by = int(cap.get("bars_per_m_y", cap.get("bars_per_m", 4)))
                dia = int(cap.get("dia_extra", cap.get("dia", 12)))
                Lx = float(cap.get("L_extra_x", cap.get("L_extra", 2.40)))
                Ly = float(cap.get("L_extra_y", cap.get("L_extra", 2.40)))
                wx = float(cap.get("cap_width_x", cap.get("cap_width", 2.0)))
                wy = float(cap.get("cap_width_y", cap.get("cap_width", 2.0)))
                clean_caps_table.append({
                    "col": cid,
                    "loc": f"{ctype} ({grid_txt})",
                    "x_rft": f"+ {bx}Ø{dia}/m",
                    "y_rft": f"+ {by}Ø{dia}/m",
                    "cut_len": f"Lx={Lx:.2f}m, Ly={Ly:.2f}m",
                    "band": f"Bx={wx:.2f}m, By={wy:.2f}m",
                })
    if not has_cap_extras:
        clean_caps_table.append({
            "col": "All Columns (C1 to C_max)",
            "loc": "Full Structural Grid (Over-Column Heads)",
            "x_rft": "Safe by Base Mesh",
            "y_rft": "Safe by Base Mesh",
            "cut_len": "—",
            "band": "Top base mesh covers negative moments & punching shear",
        })

    html_content = f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <title>Concise Structural Design Outputs — {project_name}</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 7mm 9mm 7mm 9mm;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', 'Arial', 'Calibri', sans-serif;
        }}
        body {{
            background: #ffffff;
            color: #0f172a;
            font-size: 11pt;
            line-height: 1.5;
            direction: ltr;
            text-align: left;
        }}
        .pdf-page {{
            width: 100%;
            height: 281mm;
            max-height: 281mm;
            page-break-after: always;
            break-after: page;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            overflow: hidden;
            background: #ffffff;
            padding: 2mm 0;
        }}
        .pdf-page:last-child {{
            page-break-after: avoid;
            break-after: avoid;
        }}
        /* Page Header */
        .page-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2.5px solid #1e3a8a;
            padding-bottom: 5px;
            margin-bottom: 6px;
        }}
        .header-title {{
            font-size: 14pt;
            font-weight: 900;
            color: #1e3a8a;
        }}
        .header-subtitle {{
            font-size: 9.5pt;
            font-weight: 700;
            color: #475569;
            margin-top: 2px;
        }}
        .header-badge {{
            background: #1e3a8a;
            color: #ffffff;
            font-size: 9pt;
            font-weight: 800;
            padding: 4px 10px;
            border-radius: 6px;
            text-align: right;
        }}
        /* Drawing Area */
        .drawing-container {{
            width: 100%;
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1.5px solid #cbd5e1;
            border-radius: 8px;
            background: #f8fafc;
            padding: 4px;
            margin-bottom: 8px;
            overflow: hidden;
        }}
        .drawing-img {{
            max-width: 100%;
            max-height: 165mm;
            object-fit: contain;
            border-radius: 4px;
        }}
        /* Tables & Cards */
        .table-container {{
            width: 100%;
            margin-bottom: 4px;
        }}
        table.design-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9.5pt;
            text-align: center;
            border: 1.2px solid #cbd5e1;
            border-radius: 6px;
            overflow: hidden;
        }}
        table.design-table th {{
            background: #1e3a8a;
            color: #ffffff;
            font-weight: 800;
            padding: 5.5px 7px;
            font-size: 9.5pt;
            border: 1px solid #0f172a;
        }}
        table.design-table td {{
            padding: 5px 7px;
            border: 1px solid #e2e8f0;
            font-weight: 600;
            color: #1e293b;
            font-size: 9.5pt;
        }}
        table.design-table tr:nth-child(even) {{
            background: #f8fafc;
        }}
        /* Info Cards */
        .info-card {{
            background: #f8fafc;
            border: 1.2px solid #cbd5e1;
            border-left: 5px solid #1e3a8a;
            border-right: none;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 9pt;
            line-height: 1.6;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-top: 4px;
        }}
        .info-item {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 5px;
            padding: 5px 8px;
            text-align: center;
        }}
        .info-item-label {{
            font-size: 8pt;
            color: #64748b;
            font-weight: 700;
        }}
        .info-item-val {{
            font-size: 9.5pt;
            color: #0f172a;
            font-weight: 900;
        }}
        /* Page Footer */
        .page-footer {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-top: 1.2px solid #e2e8f0;
            padding-top: 4px;
            font-size: 8pt;
            color: #64748b;
            font-weight: 600;
        }}
    </style>
</head>
<body>

    <!-- ══════════════════════════════════════════════════════════════════════
         PAGE 1: Inputs Plan View
         ══════════════════════════════════════════════════════════════════════ -->
    <div class="pdf-page">
        <div class="page-header">
            <div>
                <div class="header-title">Inputs Plan View</div>
                <div class="header-subtitle">Engineering geometry and dimensioned layout for slabs, beams, columns and openings (ECP 203)</div>
            </div>
            <div class="header-badge">Page 1 of 8</div>
        </div>

        <div class="drawing-container">
            <img class="drawing-img" src="{img_page1_b64}" alt="Inputs Plan View">
        </div>

        <div class="info-card">
            <div style="font-size: 10pt; font-weight: 800; color: #1e3a8a; margin-bottom: 4px;">
                📋 Project Structural Parameters & Design Criteria:
            </div>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-item-label">Slab Area</div>
                    <div class="info-item-val">{slab_area_val:.1f} m²</div>
                </div>
                <div class="info-item">
                    <div class="info-item-label">Slab Thickness ts</div>
                    <div class="info-item-val">{ts:.0f} cm</div>
                </div>
                <div class="info-item">
                    <div class="info-item-label">Number of Stories</div>
                    <div class="info-item-val">{num_floors} Floors</div>
                </div>
                <div class="info-item">
                    <div class="info-item-label">Ultimate Load Wu</div>
                    <div class="info-item-val">{Wu:.2f} t/m²</div>
                </div>
                <div class="info-item">
                    <div class="info-item-label">Concrete Strength Fcu</div>
                    <div class="info-item-val">{Fcu:.0f} kg/cm²</div>
                </div>
                <div class="info-item">
                    <div class="info-item-label">Steel Yield Fy</div>
                    <div class="info-item-val">{Fy:.0f} kg/cm²</div>
                </div>
                <div class="info-item">
                    <div class="info-item-label">Live Load LL</div>
                    <div class="info-item-val">{LL:.2f} t/m²</div>
                </div>
                <div class="info-item">
                    <div class="info-item-label">Superimposed Dead Load SDL</div>
                    <div class="info-item-val">{SDL:.2f} t/m²</div>
                </div>
            </div>
        </div>

        <div class="page-footer">
            <span>Project: {project_name}</span>
            <span>Integrated Structural Design System — ECP 203</span>
            <span>Page 1 of 8</span>
        </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════
         PAGE 2: Columns Design
         ══════════════════════════════════════════════════════════════════════ -->
    <div class="pdf-page">
        <div class="page-header">
            <div>
                <div class="header-title">Columns Design & Layout Plan</div>
                <div class="header-subtitle">Column models layout (C1, C2, C3) and governing axial design schedule for {num_floors} floors</div>
            </div>
            <div class="header-badge">Page 2 of 8</div>
        </div>

        <div class="drawing-container">
            <img class="drawing-img" src="{img_page2_b64}" alt="Columns Design Plan">
        </div>

        <div class="table-container">
            <table class="design-table">
                <thead>
                    <tr>
                        <th>Column Model (Tag)</th>
                        <th>Section b × t (cm)</th>
                        <th>Longitudinal Rebar</th>
                        <th>Ties / Stirrups</th>
                        <th>Column Count</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_html_table_rows(clean_cols_table)}
                </tbody>
            </table>
        </div>

        <div class="page-footer">
            <span>Project: {project_name}</span>
            <span>Columns Direct Axial Design — ECP 203</span>
            <span>Page 2 of 8</span>
        </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════
         PAGE 3: Footings Design
         ══════════════════════════════════════════════════════════════════════ -->
    <div class="pdf-page">
        <div class="page-header">
            <div>
                <div class="header-title">Reinforced Concrete Footings Design</div>
                <div class="header-subtitle">Isolated footings layout (F1, F2, F3) with reinforced & plain concrete dimensions and schedule</div>
            </div>
            <div class="header-badge">Page 3 of 8</div>
        </div>

        <div class="drawing-container">
            <img class="drawing-img" src="{img_page3_b64}" alt="Footings Design Plan">
        </div>

        <div class="table-container">
            <table class="design-table">
                <colgroup>
                    <col style="width: 15%;">
                    <col style="width: 20%;">
                    <col style="width: 18%;">
                    <col style="width: 18%;">
                    <col style="width: 29%;">
                </colgroup>
                <thead>
                    <tr>
                        <th>Footing Model (Tag)</th>
                        <th>Supported Columns</th>
                        <th>RC Footing b × a × t (cm)</th>
                        <th>PC Footing b × a × t (cm)</th>
                        <th>Reinforcement Details</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_html_table_rows(clean_ftgs_table)}
                </tbody>
            </table>
        </div>

        <div class="page-footer">
            <span>Project: {project_name}</span>
            <span>Building Foundation Design — ECP 203</span>
            <span>Page 3 of 8</span>
        </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════
         PAGE 4: Ground Beams Design
         ══════════════════════════════════════════════════════════════════════ -->
    <div class="pdf-page">
        <div class="page-header">
            <div>
                <div class="header-title">Ground Beams Design & Schedule</div>
                <div class="header-subtitle">Ground beams layout (B1, B2, B3) with cross-sections, reinforcement, ties and skin bars</div>
            </div>
            <div class="header-badge">Page 4 of 8</div>
        </div>

        <div class="drawing-container">
            <img class="drawing-img" src="{img_page4_b64}" alt="Ground Beams Plan">
        </div>

        <div class="table-container">
            <table class="design-table">
                <colgroup>
                    <col style="width: 14%;">
                    <col style="width: 16%;">
                    <col style="width: 18%;">
                    <col style="width: 18%;">
                    <col style="width: 17%;">
                    <col style="width: 17%;">
                </colgroup>
                <thead>
                    <tr>
                        <th>Beam Mark</th>
                        <th>Section b × t (cm)</th>
                        <th>Bottom Reinforcement</th>
                        <th>Top Reinforcement</th>
                        <th>Stirrups</th>
                        <th>Side Shrinkage Bars</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_html_table_rows(clean_gb_table)}
                </tbody>
            </table>
        </div>

        <div class="page-footer">
            <span>Project: {project_name}</span>
            <span>Ground Beams & Straps Design — ECP 203</span>
            <span>Page 4 of 8</span>
        </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════
         PAGE 5: Slab Beams & Cantilevers Design
         ══════════════════════════════════════════════════════════════════════ -->
    <div class="pdf-page">
        <div class="page-header">
            <div>
                <div class="header-title">Roof Beams & Cantilevers Design</div>
                <div class="header-subtitle">Roof drop beams and cantilever layout (B1, B2, B3, CB1) with structural schedule</div>
            </div>
            <div class="header-badge">Page 5 of 8</div>
        </div>

        <div class="drawing-container">
            <img class="drawing-img" src="{img_page5_b64}" alt="Roof Beams & Cantilevers Plan">
        </div>

        <div class="table-container">
            <table class="design-table">
                <colgroup>
                    <col style="width: 14%;">
                    <col style="width: 16%;">
                    <col style="width: 18%;">
                    <col style="width: 18%;">
                    <col style="width: 17%;">
                    <col style="width: 17%;">
                </colgroup>
                <thead>
                    <tr>
                        <th>Beam Mark</th>
                        <th>Section b × t (cm)</th>
                        <th>Bottom Reinforcement</th>
                        <th>Top Rebar / Forks</th>
                        <th>Stirrups</th>
                        <th>Side Shrinkage Bars</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_html_table_rows(clean_rb_table)}
                </tbody>
            </table>
        </div>

        <div class="page-footer">
            <span>Project: {project_name}</span>
            <span>Roof Drop Beams & Cantilevers Design — ECP 203</span>
            <span>Page 5 of 8</span>
        </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════
         PAGE 6: Slab Bottom Reinforcement
         ══════════════════════════════════════════════════════════════════════ -->
    <div class="pdf-page">
        <div class="page-header">
            <div>
                <div class="header-title">Slab Bottom Reinforcement Plan</div>
                <div class="header-subtitle">Bottom base mesh layout and orthogonal bottom extra reinforcement detailed schedule</div>
            </div>
            <div class="header-badge">Page 6 of 8</div>
        </div>

        <div class="drawing-container">
            <img class="drawing-img" src="{img_page6_b64}" alt="Slab Bottom Reinforcement Plan">
        </div>

        <div class="table-container">
            <table class="design-table">
                <colgroup>
                    <col style="width: 22%;">
                    <col style="width: 24%;">
                    <col style="width: 18%;">
                    <col style="width: 18%;">
                    <col style="width: 18%;">
                </colgroup>
                <thead>
                    <tr>
                        <th>Reinforcement Component</th>
                        <th>Zone / Location</th>
                        <th>Rebar Details</th>
                        <th>Cut Length (L)</th>
                        <th>Distribution Band / Notes</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_html_table_rows(clean_btm_table)}
                </tbody>
            </table>
        </div>

        <div class="page-footer">
            <span>Project: {project_name}</span>
            <span>Flat Slab Bottom Reinforcement Plan — ECP 203</span>
            <span>Page 6 of 8</span>
        </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════
         PAGE 7: Slab Top Reinforcement
         ══════════════════════════════════════════════════════════════════════ -->
    <div class="pdf-page">
        <div class="page-header">
            <div>
                <div class="header-title">Slab Top Reinforcement & Cantilever Forks Plan</div>
                <div class="header-subtitle">Top base mesh distribution and cantilever U-bars (shok) extension schedule</div>
            </div>
            <div class="header-badge">Page 7 of 8</div>
        </div>

        <div class="drawing-container">
            <img class="drawing-img" src="{img_page7_b64}" alt="Slab Top Reinforcement Plan">
        </div>

        <div class="table-container">
            <table class="design-table">
                <colgroup>
                    <col style="width: 22%;">
                    <col style="width: 24%;">
                    <col style="width: 18%;">
                    <col style="width: 18%;">
                    <col style="width: 18%;">
                </colgroup>
                <thead>
                    <tr>
                        <th>Reinforcement Component</th>
                        <th>Zone / Location</th>
                        <th>Rebar Details</th>
                        <th>Cut Length (L)</th>
                        <th>Anchorage & Extension Notes</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_html_table_rows(clean_top_table)}
                </tbody>
            </table>
        </div>

        <div class="page-footer">
            <span>Project: {project_name}</span>
            <span>Flat Slab Top Reinforcement & Cantilevers — ECP 203</span>
            <span>Page 7 of 8</span>
        </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════
         PAGE 8: Column Caps Reinforcement
         ══════════════════════════════════════════════════════════════════════ -->
    <div class="pdf-page">
        <div class="page-header">
            <div>
                <div class="header-title">Column Caps Top Reinforcement Plan</div>
                <div class="header-subtitle">Top extra rebar over column heads for negative moments and punching shear resistance (ECP 203)</div>
            </div>
            <div class="header-badge">Page 8 of 8</div>
        </div>

        <div class="drawing-container">
            <img class="drawing-img" src="{img_page8_b64}" alt="Column Caps Plan">
        </div>

        <div class="table-container">
            <table class="design-table">
                <colgroup>
                    <col style="width: 15%;">
                    <col style="width: 20%;">
                    <col style="width: 17%;">
                    <col style="width: 17%;">
                    <col style="width: 16%;">
                    <col style="width: 15%;">
                </colgroup>
                <thead>
                    <tr>
                        <th>Column Tag (ID)</th>
                        <th>Location & Grid</th>
                        <th>Top Extra Rebar (X-Dir)</th>
                        <th>Top Extra Rebar (Y-Dir)</th>
                        <th>Cut Length (L)</th>
                        <th>Band Width (B)</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_html_table_rows(clean_caps_table)}
                </tbody>
            </table>
        </div>

        <div class="page-footer">
            <span>Project: {project_name}</span>
            <span>Column Caps Layout Plan — ECP 203</span>
            <span>Page 8 of 8</span>
        </div>
    </div>

</body>
</html>
"""
    return html_content


def _clean_cell_to_en(val: Any) -> str:
    """Translates Arabic phrases and units into clean structural engineering English, removing any residual Arabic text."""
    if val is None:
        return "—"
    s = str(val).strip()
    if not s or s in ["—", "-", "None"]:
        return "—"

    # Extensive replacements for all Arabic technical engineering terms
    replacements = [
        # Columns & classification
        ("أعمدة داخلية", "Interior Columns"),
        ("أعمدة طرفية", "Edge Columns"),
        ("أعمدة ركن", "Corner Columns"),
        ("أعمدة جانبية", "Edge Columns"),
        ("عمود ركن", "Corner Col"),
        ("داخلي", "Interior"),
        ("طرفي", "Edge"),
        ("ركن", "Corner"),
        ("أركان", "Corners"),
        ("داخلية", "Interior"),
        ("طرفية", "Edge"),
        ("جانبي", "Side"),
        ("جانبية", "Side"),
        # Governing & Design criteria
        ("الحاكم", "Gov"),
        ("حاكم", "Gov"),
        ("أقصى عمود", "Max Col"),
        ("أقصى", "Max"),
        # Beams
        ("سملات قطاع ثقيل", "Heavy Ground Beam"),
        ("سملات قطاع متوسط", "Medium Ground Beam"),
        ("سملات قطاع خفيف", "Light Ground Beam"),
        ("كمرات ساقطة ثقيل", "Heavy Drop Beam"),
        ("كمرات ساقطة متوسط", "Medium Drop Beam"),
        ("كمرات ساقطة خفيف", "Light Drop Beam"),
        ("كمرات كابولية", "Cantilever Beam"),
        ("ساقطة ثقيل", "Heavy Drop Beam"),
        ("ساقطة متوسط", "Medium Drop Beam"),
        ("ساقطة خفيف", "Light Drop Beam"),
        ("كابولية بشوك", "Cantilever Beam"),
        ("كابولي", "Cantilever"),
        ("كوابيل", "Cantilevers"),
        ("سملة", "GB"),
        ("سملات", "Ground Beams"),
        ("كمرة", "Beam"),
        ("كمرات", "Beams"),
        # Footings
        ("قاعدة منفصلة", "Isolated Footing"),
        ("قواعد منفصلة", "Isolated Footings"),
        ("قاعدة مشتركة", "Combined Footing"),
        ("قواعد مشتركة", "Combined Footings"),
        ("قواعد", "Footings"),
        ("قاعدة", "Footing"),
        # Structural status & reinforcement terms
        ("Safe ومحقق للكود", "Safe (ECP 203)"),
        ("آمن ومحقق للكود", "Safe (ECP 203)"),
        ("آمن تماماً", "Safe (ECP 203)"),
        ("آمن بالشبكة", "Safe by Mesh"),
        ("آمن", "Safe"),
        ("غير آمن", "Unsafe"),
        ("محقق", "Compliant"),
        ("للكود", "to Code"),
        ("فرش:", "Btm (Main):"),
        ("فرش", "Btm (Main)"),
        ("غطاء:", "Btm (Sec):"),
        ("غطاء", "Btm (Sec)"),
        ("علوي:", "Top:"),
        ("علوي", "Top"),
        ("سفلي:", "Bottom:"),
        ("سفلي", "Bottom"),
        ("كانات:", "Stirrups:"),
        ("كانات", "Stirrups"),
        ("كانة", "Stirrup"),
        ("براندات الانكماش", "Side Shrinkage Bars"),
        ("براندات جانبية", "Side Bars"),
        ("براندات الجوانب", "Side Bars"),
        ("براندات:", "Side:"),
        ("براندات", "Side Bars"),
        ("انكماش", "Shrinkage"),
        ("تسليح جانبي", "Side Rebar"),
        ("تسليح رئيسي", "Main Rebar"),
        ("تسليح", "Rebar"),
        ("شوك", "Forks"),
        ("شوكة", "Forks"),
        ("عمود", "Cols"),
        ("أعمدة", "Cols"),
        ("طوابق", "Floors"),
        ("طابق", "Floors"),
        ("دور", "Floors"),
        ("أدوار", "Floors"),
        ("سقف", "Slab"),
        ("بلاطة", "Slab"),
        ("/م'", "/m"),
        ("/م", "/m"),
    ]
    for ar_term, en_term in replacements:
        s = s.replace(ar_term, en_term)

    # Secondary regex sweep: completely purge any residual Arabic characters
    import re
    if re.search(r'[\u0600-\u06FF]', s):
        s = re.sub(r'[\u0600-\u06FF]+', '', s)
        s = re.sub(r'\(\s*\)', '', s)
        s = re.sub(r'\[\s*\]', '', s)
        s = re.sub(r'\{\s*\}', '', s)
        s = re.sub(r'\|\s*\|', '|', s)
        s = re.sub(r'—\s*—', '—', s)
        s = re.sub(r'\s+', ' ', s).strip()
        s = s.strip(' |-,:')
        if not s:
            s = "—"

    return s


def _render_html_table_rows(data_rows: List[Dict[str, Any]]) -> str:
    """Helper to convert list of dict rows to clean English HTML table rows."""
    if not data_rows:
        return '<tr><td colspan="8">No data available</td></tr>'
    html_rows = []
    for r in data_rows:
        tds = "".join([f"<td>{_clean_cell_to_en(val)}</td>" for val in r.values()])
        html_rows.append(f"<tr>{tds}</tr>")
    return "\n".join(html_rows)
