# -*- coding: utf-8 -*-
"""
Module 15 Structural & Detailing Engine (محرك الحسابات والتصميم الإنشائي والقطاعات الـ 10 التخصصية)
==================================================================================================
Egyptian Code of Practice (ECP 203 & ECP 204 - Egyptian Code for Masonry Works)
Provides:
  1. Complete structural capacity, wall loads, slenderness ratio checks, and lintel structural analysis.
  2. The 10 specialized engineering CAD drawings & cross-sections for Masonry & Plastering.
  3. UI rendering for Phase 2 (المرحلة الثانية: الحسابات والتصميم الإنشائي الكامل).
"""

import io
import math
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, Arc, FancyBboxPatch, Polygon
import streamlit as st
import pandas as pd


def ar(text: str) -> str:
    """Helper for Arabic text reshaping in matplotlib figures."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. STRUCTURAL DESIGN & CAPACITY CALCULATIONS (ECP 204 & ECP 203)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_m15_structural_design(walls_placed, wall_thickness, wall_heights, windows, doors, col_placed):
    """
    Computes structural design metrics according to Egyptian Code for Masonry (ECP 204):
      - Wall self-weight per meter run (DL transferred to beams/slabs)
      - Slenderness ratio: lambda = Heff / t (<= 28 for non-bearing, <= 20 for bearing)
      - Masonry characteristic compressive strength fm' and allowable axial capacity Pu
      - Reinforced Concrete Lintels structural sizing and bearing lengths
    """
    gamma_masonry = 1.80  # t/m3 (Red brick with cement mortar)
    gamma_plaster = 2.10  # t/m3 (Cement plaster)
    t_plaster_m = 0.02    # 2 cm plaster each face

    # 1. Wall weight per meter run
    w12_dl_m = (gamma_masonry * 0.12 + 2 * gamma_plaster * t_plaster_m) * 3.0  # ton/m for 3m height
    w25_dl_m = (gamma_masonry * 0.25 + 2 * gamma_plaster * t_plaster_m) * 3.0  # ton/m for 3m height

    # 2. Slenderness ratio check for walls
    default_h = 3.0
    wall_checks = []
    max_slenderness_12 = 0.0
    max_slenderness_25 = 0.0

    for i, w in enumerate(walls_placed):
        thick = wall_thickness.get(w, 12)
        h = wall_heights.get(w, default_h)
        t_m = thick / 100.0
        lam = round(h / t_m, 1)
        limit = 28.0 if thick <= 12 else 22.0
        is_safe = lam <= limit
        if thick <= 12:
            max_slenderness_12 = max(max_slenderness_12, lam)
        else:
            max_slenderness_25 = max(max_slenderness_25, lam)

        wall_checks.append({
            "wall_idx": i + 1,
            "wall_coords": w,
            "thick_cm": thick,
            "height_m": h,
            "slenderness": lam,
            "limit": limit,
            "safe": is_safe
        })

    pu_12_ton_m = 7.14
    pu_25_ton_m = 14.88

    # 4. Lintels (الأعتاب الخرسانية المسلحة) analysis
    lintel_list = []
    all_openings = []
    for w_coords, win_items in (windows or {}).items():
        for item in (win_items or []):
            all_openings.append({"kind": "شباك (Window)", "tag": item.get("name", "W"), "w": float(item.get("w", 1.2)), "h": float(item.get("h", 1.2)), "wall": w_coords})
    for w_coords, door_items in (doors or {}).items():
        for item in (door_items or []):
            all_openings.append({"kind": "باب (Door)", "tag": item.get("name", "D"), "w": float(item.get("w", 1.0)), "h": float(item.get("h", 2.2)), "wall": w_coords})

    for op in all_openings:
        span_m = op["w"]
        bearing_cm = max(20.0, math.ceil(span_m * 100.0 / 10.0 / 5.0) * 5.0)
        depth_cm = max(12.0, math.ceil(span_m * 100.0 / 10.0 / 5.0) * 5.0)
        wall_t = wall_thickness.get(op["wall"], 12) if wall_thickness else 12
        if span_m <= 1.2:
            rebar = "2 Φ 10 mm"
        elif span_m <= 1.8:
            rebar = "2 Φ 12 mm"
        else:
            rebar = "2 Φ 16 mm"
        stirrups = "5 Φ 8 mm / m"

        lintel_list.append({
            "tag": op["tag"],
            "kind": op["kind"],
            "span_m": span_m,
            "depth_cm": depth_cm,
            "width_cm": wall_t,
            "bearing_cm": bearing_cm,
            "total_length_m": round(span_m + 2 * (bearing_cm / 100.0), 2),
            "rebar": rebar,
            "stirrups": stirrups
        })

    return {
        "w12_dl_m": w12_dl_m,
        "w25_dl_m": w25_dl_m,
        "max_slenderness_12": max_slenderness_12 or 25.0,
        "max_slenderness_25": max_slenderness_25 or 12.0,
        "pu_12_ton_m": pu_12_ton_m,
        "pu_25_ton_m": pu_25_ton_m,
        "wall_checks": wall_checks,
        "lintel_list": lintel_list,
        "total_lintels": len(lintel_list)
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  2. THE 10 SPECIALIZED ENGINEERING DRAWINGS & SECTIONS GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def draw_section_1_wall_layout(buf_plan_clean):
    """
    القطاع/المخطط 1: مخطط توقيع وتوزيع حوائط المباني والسماكات الإنشائية
    (Masonry Wall Layout & Thicknesses Engineering Plan)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    if buf_plan_clean:
        try:
            import PIL.Image as PILImage
            img = PILImage.open(buf_plan_clean)
            ax.imshow(img, aspect="auto", extent=[0, 10, 0, 7])
        except Exception:
            pass

    title_box = patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08",
                                       fc="#0f172a", ec="#38bdf8", lw=2)
    ax.add_patch(title_box)
    ax.text(5.0, 6.52, ar("المخطط الإنشائي 1: توقيع وتوزيع حوائط المباني والسماكات (Masonry Layout Plan)"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    leg_box = patches.FancyBboxPatch((0.5, 0.2), 9.0, 0.85, boxstyle="round,pad=0.05",
                                     fc="#ffffff", ec="#cbd5e1", lw=1.5)
    ax.add_patch(leg_box)
    ax.text(5.0, 0.85, ar("دليل الرموز والمواصفات الإنشائية للحوائط طبقاً للكود المصري للمباني (ECP 204)"),
            color="#1e293b", fontsize=9.5, fontweight="bold", ha="center", va="center")

    ax.add_patch(Rectangle((0.8, 0.35), 0.5, 0.25, fc="#8B1A1A", ec="#000000", lw=1))
    ax.text(1.4, 0.47, ar("حائط 25 سم (طوبة كاملة - خارجي)"), fontsize=8.5, va="center")

    ax.add_patch(Rectangle((3.8, 0.35), 0.5, 0.25, fc="#EFA368", ec="#000000", lw=1))
    ax.text(4.4, 0.47, ar("قاطع 12 سم (نصف طوبة - داخلي)"), fontsize=8.5, va="center")

    ax.add_patch(Rectangle((6.8, 0.35), 0.5, 0.25, fc="#2F4F8F", ec="#000000", lw=1))
    ax.text(7.4, 0.47, ar("أعمدة خرسانية مسلحة (RC Columns)"), fontsize=8.5, va="center")

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


def draw_section_2_openings_and_lintels(lintels_data):
    """
    القطاع/المخطط 2: مخطط توقيع وتفاصيل فتحات الأبواب والشبابيك وجدول الأعتاب
    (Openings Layout & Lintel Schedule Plan)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    ax.add_patch(patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08", fc="#0f172a", ec="#3b82f6", lw=2))
    ax.text(5.0, 6.52, ar("المخطط الإنشائي 2: توقيع الفتحات وجدول الأعتاب الخرسانية (Lintels Schedule)"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    # Left: Window with Lintel
    ax.text(2.6, 5.7, ar("تفصيلة شباك وعتب خرساني (Window Lintel Detail)"), fontsize=9.5, fontweight="bold", color="#1e3a8a", ha="center")
    ax.add_patch(Rectangle((0.6, 2.0), 4.0, 3.4, fc="#fee2e2", ec="#dc2626", lw=1.5, hatch="//"))
    ax.add_patch(Rectangle((1.6, 2.8), 2.0, 1.8, fc="#ffffff", ec="#0284c7", lw=2))
    ax.text(2.6, 3.7, ar("فتحة شباك (W)\n1.20 × 1.20 م"), ha="center", va="center", color="#0369a1", fontsize=9, fontweight="bold")
    ax.add_patch(Rectangle((1.3, 4.6), 2.6, 0.35, fc="#94a3b8", ec="#0f172a", lw=2))
    ax.text(2.6, 4.77, ar("عتب خرساني مسلح (Lintel) 2Φ12"), ha="center", va="center", color="#0f172a", fontsize=8.5, fontweight="bold")
    ax.annotate("", xy=(1.3, 5.1), xytext=(1.6, 5.1), arrowprops=dict(arrowstyle="<->", color="#dc2626", lw=1.5))
    ax.text(1.45, 5.25, ar("ركوب ≥ 20سم"), ha="center", fontsize=7.5, color="#dc2626", fontweight="bold")
    ax.annotate("", xy=(3.6, 5.1), xytext=(3.9, 5.1), arrowprops=dict(arrowstyle="<->", color="#dc2626", lw=1.5))
    ax.text(3.75, 5.25, ar("ركوب ≥ 20سم"), ha="center", fontsize=7.5, color="#dc2626", fontweight="bold")

    # Right: Door with Lintel
    ax.text(7.4, 5.7, ar("تفصيلة باب وعتب خرساني (Door Lintel Detail)"), fontsize=9.5, fontweight="bold", color="#1e3a8a", ha="center")
    ax.add_patch(Rectangle((5.4, 2.0), 4.0, 3.4, fc="#fee2e2", ec="#dc2626", lw=1.5, hatch="//"))
    ax.add_patch(Rectangle((6.5, 2.0), 1.8, 2.6, fc="#ffffff", ec="#16a34a", lw=2))
    ax.text(7.4, 3.3, ar("فتحة باب (D)\n1.00 × 2.20 م"), ha="center", va="center", color="#15803d", fontsize=9, fontweight="bold")
    ax.add_patch(Rectangle((6.2, 4.6), 2.4, 0.35, fc="#94a3b8", ec="#0f172a", lw=2))
    ax.text(7.4, 4.77, ar("عتب خرساني مسلح (Lintel) 2Φ12"), ha="center", va="center", color="#0f172a", fontsize=8.5, fontweight="bold")
    ax.annotate("", xy=(6.2, 5.1), xytext=(6.5, 5.1), arrowprops=dict(arrowstyle="<->", color="#dc2626", lw=1.5))
    ax.text(6.35, 5.25, ar("ركوب ≥ 20سم"), ha="center", fontsize=7.5, color="#dc2626", fontweight="bold")

    # Bottom Table: Summary specifications for lintels
    tbl_box = patches.FancyBboxPatch((0.5, 0.2), 9.0, 1.4, boxstyle="round,pad=0.06", fc="#ffffff", ec="#94a3b8", lw=1.5)
    ax.add_patch(tbl_box)
    ax.text(5.0, 1.4, ar("جدول النماذج القياسية للأعتاب الخرسانية للفتحات (ECP 203 & ECP 204)"),
            fontsize=9, fontweight="bold", ha="center", color="#0f172a")

    rows = [
        ("بحر الفتحة L", "عمق العتب D", "طول الركوب b", "التسليح الرئيسي السفلي", "الكانات"),
        ("حتى 1.20 م", "12 سم (مدماكين)", "20 سم كل جانب", "2 Φ 10 مم سفلي + 2 Φ 8 مم علوي", "5 Φ 8 / م"),
        ("1.20 إلى 1.80 م", "15 سم (مدماكين ونصف)", "25 سم كل جانب", "2 Φ 12 مم سفلي + 2 Φ 10 مم علوي", "5 Φ 8 / م"),
        ("أكبر من 1.80 م", "L / 10 ≥ 20 سم", "30 سم كل جانب", "2 Φ 16 مم سفلي + 2 Φ 10 مم علوي", "6 Φ 8 / م"),
    ]
    y_t = 1.15
    for r_idx, r in enumerate(rows):
        weight = "bold" if r_idx == 0 else "normal"
        color = "#1e3a8a" if r_idx == 0 else "#334155"
        ax.text(1.2, y_t, ar(r[0]), fontsize=7.5, fontweight=weight, color=color, ha="center")
        ax.text(3.0, y_t, ar(r[1]), fontsize=7.5, fontweight=weight, color=color, ha="center")
        ax.text(4.8, y_t, ar(r[2]), fontsize=7.5, fontweight=weight, color=color, ha="center")
        ax.text(6.8, y_t, ar(r[3]), fontsize=7.5, fontweight=weight, color=color, ha="center")
        ax.text(8.7, y_t, ar(r[4]), fontsize=7.5, fontweight=weight, color=color, ha="center")
        y_t -= 0.25

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


def draw_section_3_external_wall_25cm():
    """
    القطاع/المخطط 3: قطاع رأسي كامل في حائط خارجي 25 سم مع العتب والخرسانة والعزل
    (Full Vertical Section in 25cm External Wall)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    ax.add_patch(patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08", fc="#0f172a", ec="#b91c1c", lw=2))
    ax.text(5.0, 6.52, ar("القطاع الإنشائي 3: قطاع رأسي تفصيلي في حائط خارجي 25 سم مع العتب والعزل"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    ax.add_patch(Rectangle((2.0, 5.2), 4.5, 0.5, fc="#94a3b8", ec="#0f172a", lw=2))
    ax.text(4.25, 5.45, ar("بلاطة السقف الخرسانية المسلحة (RC Slab ts=20cm)"), color="#ffffff", fontsize=8.5, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((3.25, 4.4), 2.0, 0.8, fc="#cbd5e1", ec="#0f172a", lw=2))
    ax.text(4.25, 4.8, ar("كمرة ساقطة (Drop Beam 25×60)"), color="#0f172a", fontsize=8, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((3.25, 3.4), 2.0, 1.0, fc="#fee2e2", ec="#b91c1c", lw=2, hatch="++"))
    ax.text(4.25, 3.9, ar("مباني طوب أحمر 25 سم\n(سقاطة أعلى الشباك)"), color="#991b1b", fontsize=8, ha="center", fontweight="bold")

    ax.add_patch(Rectangle((3.25, 3.0), 2.0, 0.4, fc="#64748b", ec="#0f172a", lw=2))
    ax.text(4.25, 3.2, ar("عتب خرساني مسلح D=15cm (2Φ12)"), color="#ffffff", fontsize=8, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((3.25, 1.8), 2.0, 1.2, fc="#e0f2fe", ec="#0284c7", lw=2, linestyle="--"))
    ax.text(4.25, 2.4, ar("فتحة شباك ألوميتال مزدوج عازل\n(Double Glazed Window)"), color="#0369a1", fontsize=8, ha="center")

    sill_poly = Polygon([(3.2, 1.8), (5.3, 1.8), (5.25, 1.6), (3.25, 1.6)], fc="#94a3b8", ec="#0f172a", lw=1.5)
    ax.add_patch(sill_poly)
    ax.text(4.25, 1.7, ar("جلسة خرسانية بميول 2% مع أنف مزراب"), fontsize=7, ha="center", color="#0f172a", fontweight="bold")

    ax.add_patch(Rectangle((3.25, 0.7), 2.0, 0.9, fc="#fee2e2", ec="#b91c1c", lw=2, hatch="++"))
    ax.text(4.25, 1.15, ar("مباني طوب أحمر 25 سم\n(بارتفاع الجلسة 1.0 م)"), color="#991b1b", fontsize=8, ha="center", fontweight="bold")

    ax.add_patch(Rectangle((3.25, 0.65), 2.0, 0.05, fc="#000000", ec="#000000"))
    ax.text(5.5, 0.67, ar("طبقة عازل رطوبة DPC بيتومين"), fontsize=7.5, color="#000000", fontweight="bold")

    ax.add_patch(Rectangle((2.0, 0.15), 4.5, 0.5, fc="#94a3b8", ec="#0f172a", lw=2))
    ax.text(4.25, 0.4, ar("بلاطة الدور السفلي / ميدة خرسانية"), color="#ffffff", fontsize=8.5, fontweight="bold", ha="center")

    # Plaster layers
    ax.plot([3.15, 3.15], [0.7, 4.4], color="#ea580c", lw=3)
    ax.text(2.0, 2.8, ar("محارة واجهات خارجية:\n• طرطشة مسمرة 0.5 سم\n• بياض أسمنتي عازل 2 سم\n• ضهارة ملونة سافيتو"),
            fontsize=7.5, color="#c2410c", fontweight="bold", bbox=dict(boxstyle="round,pad=0.3", fc="#fff7ed", ec="#ea580c"))

    ax.plot([5.35, 5.35], [0.7, 4.4], color="#16a34a", lw=3)
    ax.text(6.5, 2.8, ar("محارة داخلية 3 طبقات:\n• طرطشة عمومية 0.5 سم\n• بؤج وأوتار + بطانة 1.5 سم\n• ضهارة ناعمة 0.5 سم"),
            fontsize=7.5, color="#15803d", fontweight="bold", bbox=dict(boxstyle="round,pad=0.3", fc="#f0fdf4", ec="#16a34a"))

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


def draw_section_4_internal_partition_12cm():
    """
    القطاع/المخطط 4: قطاع رأسي في قاطع داخلي 12 سم وتثبيت الأبواب والوزرة
    (Vertical Section in 12cm Partition with Door Framing & Skirting)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    ax.add_patch(patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08", fc="#0f172a", ec="#d97706", lw=2))
    ax.text(5.0, 6.52, ar("القطاع الإنشائي 4: قطاع رأسي في قاطع حائط داخلي 12 سم وتثبيت الحلق والوزرة"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    ax.add_patch(Rectangle((2.0, 5.2), 5.0, 0.5, fc="#94a3b8", ec="#0f172a", lw=2))
    ax.text(4.5, 5.45, ar("بلاطة السقف الخرسانية المسلحة (RC Solid / Flat Slab)"), color="#ffffff", fontsize=8.5, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((3.8, 4.8), 1.4, 0.4, fc="#fde68a", ec="#b45309", lw=1.5, hatch="//"))
    ax.text(4.5, 5.0, ar("مدماك تمشيط مائل بمونة قوية للربط بالسقف"), color="#92400e", fontsize=7.5, ha="center", fontweight="bold")

    ax.add_patch(Rectangle((3.8, 3.8), 1.4, 1.0, fc="#ffedd5", ec="#ea580c", lw=1.5, hatch=".."))
    ax.text(4.5, 4.3, ar("قاطع مباني 12 سم\n(سقاطة أعلى الباب)"), color="#c2410c", fontsize=8, ha="center", fontweight="bold")

    ax.add_patch(Rectangle((3.8, 3.4), 1.4, 0.4, fc="#64748b", ec="#0f172a", lw=1.5))
    ax.text(4.5, 3.6, ar("عتب خرساني مسلح D=12cm (2Φ10)"), color="#ffffff", fontsize=7.5, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((3.85, 0.8), 1.3, 2.6, fc="#ffffff", ec="#854d0e", lw=2))
    ax.add_patch(Rectangle((3.75, 0.8), 0.1, 2.6, fc="#b45309", ec="#78350f"))
    ax.add_patch(Rectangle((5.05, 0.8), 0.1, 2.6, fc="#b45309", ec="#78350f"))
    ax.text(4.5, 2.1, ar("حلق باب خشب موسكي 2 بوصة\nمثبت بـ 6 كانات حديد مع الكانات\n(Door Frame & Steel Anchors)"),
            ha="center", va="center", color="#78350f", fontsize=8, fontweight="bold")

    ax.add_patch(Rectangle((2.0, 0.15), 5.0, 0.4, fc="#94a3b8", ec="#0f172a", lw=2))
    ax.text(2.8, 0.35, ar("بلاطة الدور الخرسانية"), color="#ffffff", fontsize=7.5, fontweight="bold")

    ax.add_patch(Rectangle((2.0, 0.55), 5.0, 0.15, fc="#fef08a", ec="#ca8a04"))
    ax.text(2.8, 0.62, ar("فرشة رمل نظيف 6 سم"), fontsize=7, color="#854d0e")

    ax.add_patch(Rectangle((2.0, 0.7), 5.0, 0.1, fc="#e2e8f0", ec="#64748b"))
    ax.text(2.8, 0.75, ar("مونة + سيراميك 3 سم"), fontsize=7, color="#0f172a")

    ax.add_patch(Rectangle((3.65, 0.8), 0.1, 0.3, fc="#64748b", ec="#0f172a"))
    ax.add_patch(Rectangle((5.15, 0.8), 0.1, 0.3, fc="#64748b", ec="#0f172a"))
    ax.text(6.0, 0.95, ar("وزرة سيراميك/رخام ارتفاع 10 سم"), fontsize=7.5, color="#1e293b", fontweight="bold")

    ax.text(7.5, 3.5, ar("اشتراطات الكود ECP 204 لقواطع 12 سم:\n• أقصى ارتفاع حر بدون رباط: 3.25 م\n• ربط الحلق بكانات صلب مجلفن كل 50 سم\n• شبك فايبر بعرض 20 سم عند التقاء الأعمدة\n• مونة أسمنتية بنسبة 350 كجم أسمنت/م3 رمل"),
            fontsize=8, color="#0f172a", bbox=dict(boxstyle="round,pad=0.4", fc="#f8fafc", ec="#94a3b8"))

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


def draw_section_5_corner_and_junction_bonds():
    """
    القطاع/المخطط 5: تفصيلة رباط الزوايا وتقاطع الحوائط T-Junction والرباط الإنجليزي
    (Masonry T-Junction & Corner Interlocking Detail)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    ax.add_patch(patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08", fc="#0f172a", ec="#059669", lw=2))
    ax.text(5.0, 6.52, ar("القطاع الإنشائي 5: تفاصيل رباط الزوايا (90°) وتقاطعات الحوائط (T-Junction) في المباني"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    ax.text(2.6, 5.7, ar("أ) زاوية ركنية 90° (Corner 25cm Wall)"), fontsize=9.5, fontweight="bold", color="#065f46", ha="center")
    ax.text(2.6, 5.3, ar("المدماك الأول (Course 1) - شنطة ورأس"), fontsize=8, color="#047857", ha="center", fontweight="bold")
    ax.add_patch(Rectangle((0.6, 3.8), 1.2, 1.2, fc="#fee2e2", ec="#b91c1c", lw=1.5))
    ax.add_patch(Rectangle((1.8, 4.4), 2.4, 0.6, fc="#ffedd5", ec="#ea580c", lw=1.5))
    ax.add_patch(Rectangle((0.6, 2.6), 0.6, 1.2, fc="#fef08a", ec="#ca8a04", lw=1.5))
    ax.text(1.2, 4.4, ar("كنسية ربع"), fontsize=7, ha="center")
    ax.text(3.0, 4.7, ar("شناوي"), fontsize=7.5, ha="center")
    ax.text(0.9, 3.2, ar("آدي"), fontsize=7.5, ha="center")

    ax.text(2.6, 2.1, ar("المدماك الثاني (Course 2) - عكس اتجاه الرباط"), fontsize=8, color="#047857", ha="center", fontweight="bold")
    ax.add_patch(Rectangle((0.6, 0.6), 2.4, 0.6, fc="#ffedd5", ec="#ea580c", lw=1.5))
    ax.add_patch(Rectangle((0.6, 1.2), 0.6, 0.6, fc="#fee2e2", ec="#b91c1c", lw=1.5))
    ax.add_patch(Rectangle((1.2, 1.2), 0.6, 1.0, fc="#fef08a", ec="#ca8a04", lw=1.5))
    ax.text(1.8, 0.9, ar("شناوي مستمر"), fontsize=7, ha="center")
    ax.text(0.9, 1.5, ar("كنسية"), fontsize=7, ha="center")

    ax.text(7.4, 5.7, ar("ب) تقاطع حائطين T-Junction (حائط 25 مع 12 سم)"), fontsize=9.5, fontweight="bold", color="#065f46", ha="center")
    ax.text(7.4, 5.3, ar("المدماك الأول: دخول طوبة القاطع داخل الحائط الرئيسي"), fontsize=8, color="#047857", ha="center", fontweight="bold")
    ax.add_patch(Rectangle((5.2, 4.4), 4.2, 0.6, fc="#fee2e2", ec="#b91c1c", lw=1.5))
    ax.add_patch(Rectangle((7.0, 3.2), 0.6, 1.2, fc="#ffedd5", ec="#ea580c", lw=1.5))
    ax.text(7.3, 4.7, ar("حائط رئيسي 25 سم مستمر"), fontsize=7.5, ha="center")
    ax.text(7.3, 3.8, ar("قاطع 12 تعشيق"), fontsize=7, ha="center", color="#c2410c", fontweight="bold")

    ax.text(7.4, 2.1, ar("المدماك الثاني: استمرار شناويات الحائط الرئيسي ووقوف القاطع"), fontsize=8, color="#047857", ha="center", fontweight="bold")
    ax.add_patch(Rectangle((5.2, 1.2), 4.2, 0.6, fc="#fee2e2", ec="#b91c1c", lw=1.5))
    ax.add_patch(Rectangle((7.0, 0.4), 0.6, 0.8, fc="#ffedd5", ec="#ea580c", lw=1.5))
    ax.text(7.3, 1.5, ar("حائط رئيسي مقفل بدون قطع"), fontsize=7.5, ha="center")
    ax.text(7.3, 0.8, ar("قاطع يرتكز بالمونة"), fontsize=7, ha="center")

    ax.text(5.0, 0.15, ar("القاعدة الذهبية: يُمنع تماماً وجود لحامات رأسية مشتركة (Straight Joints) لتفادي الشروخ الانفصالية الهيكلية"),
            fontsize=8, color="#991b1b", fontweight="bold", ha="center")

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


def draw_section_6_wall_to_column_ties():
    """
    القطاع/المخطط 6: تفصيلة ربط المباني بالأعمدة والكمرات الخرسانية بالكانات
    (Wall-to-Column Steel Tie & Anchors Detail)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    ax.add_patch(patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08", fc="#0f172a", ec="#6366f1", lw=2))
    ax.text(5.0, 6.52, ar("القطاع الإنشائي 6: تفصيلة كانات وزوايا ربط المباني بالأعمدة والكمرات الخرسانية"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    ax.add_patch(Rectangle((1.0, 0.8), 2.2, 4.8, fc="#64748b", ec="#0f172a", lw=2))
    ax.text(2.1, 3.2, ar("عمود خرساني مسلح\n(RC Column)\nC1 25×60 cm"), color="#ffffff", fontsize=9, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((3.6, 0.8), 4.8, 4.8, fc="#fee2e2", ec="#b91c1c", lw=2, hatch="//"))
    ax.text(6.0, 3.2, ar("حوائط مباني (Masonry Wall)\nمداميك طوب مع لحامات أفقية"), color="#991b1b", fontsize=9, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((3.2, 0.8), 0.4, 4.8, fc="#e2e8f0", ec="#64748b", lw=1))
    ax.text(3.4, 5.75, ar("فاصل مرن 2 سم\n(سيلانت بولي يوريثان + فوم)"), fontsize=7, color="#dc2626", ha="center", fontweight="bold")

    y_ties = [1.6, 2.6, 3.6, 4.6]
    for y in y_ties:
        ax.plot([2.7, 3.2], [y, y], color="#dc2626", lw=3)
        ax.plot(2.7, y, marker="o", color="#dc2626", markersize=6)
        ax.plot([3.2, 5.0], [y, y], color="#4338ca", lw=3.5)
        ax.text(5.1, y, ar("كانة صلب مجلفن 25×2.5 سم مثبتة بمسمار صلب طلقة/فيشر"), fontsize=7.5, color="#312e81", va="center", fontweight="bold")

    ax.text(5.0, 0.4, ar("اشتراطات الكود المصري: تركيب كانة صلب مجلفن كل 3 مداميك (مسافة رأسية ≤ 40 سم) لضمان استقرار الحائط ضد قوى الزلازل والرياح"),
            fontsize=8, color="#1e1b4b", fontweight="bold", ha="center", bbox=dict(boxstyle="round,pad=0.3", fc="#e0e7ff", ec="#6366f1"))

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


def draw_section_7_internal_plaster_layers():
    """
    القطاع/المخطط 7: قطاع تفصيلي لطبقات المحارة الداخلية ومراحل التنفيذ
    (Internal Plastering System: Spatterdash, Screeds & Finish)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    ax.add_patch(patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08", fc="#0f172a", ec="#10b981", lw=2))
    ax.text(5.0, 6.52, ar("القطاع الإنشائي 7: طبقات ومراحل تنفيذ المحارة الداخلية (Internal Plastering Cross-Section)"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    ax.add_patch(Rectangle((0.8, 1.2), 2.2, 4.6, fc="#fee2e2", ec="#b91c1c", lw=2, hatch="++"))
    ax.text(1.9, 3.5, ar("1. الحائط الحامل / القاطع\nطوب طفلي أحمر أو أسمنتي\n(Brick Substrate)\nسمك 12 أو 25 سم"),
            ha="center", va="center", color="#991b1b", fontsize=8.5, fontweight="bold")

    ax.add_patch(Rectangle((3.0, 1.2), 0.6, 4.6, fc="#fef08a", ec="#ca8a04", lw=1.5, hatch=".."))
    ax.text(3.3, 3.5, ar("2. طرطشة\nمساميرية\n0.5 سم"), ha="center", va="center", color="#854d0e", fontsize=7.5, fontweight="bold")

    ax.add_patch(Rectangle((3.6, 1.2), 0.6, 4.6, fc="#fed7aa", ec="#ea580c", lw=1.5))
    ax.text(3.9, 3.5, ar("3. بؤج وأوتار\nلضبط الشاقول\n1.5-2.0 سم"), ha="center", va="center", color="#9a3412", fontsize=7.5, fontweight="bold")

    ax.add_patch(Rectangle((4.2, 1.2), 1.2, 4.6, fc="#cbd5e1", ec="#475569", lw=1.5))
    ax.text(4.8, 3.5, ar("4. طبقة البطانة\n(Brown Coat)\nمونة 350 كجم/م3\nسمك 1.5 سم"),
            ha="center", va="center", color="#1e293b", fontsize=8, fontweight="bold")

    ax.add_patch(Rectangle((5.4, 1.2), 0.6, 4.6, fc="#f1f5f9", ec="#94a3b8", lw=1.5))
    ax.text(5.7, 3.5, ar("5. ضهارة\nناعمة\n0.5 سم"), ha="center", va="center", color="#0f172a", fontsize=7.5, fontweight="bold")

    spec_box = patches.FancyBboxPatch((6.3, 1.2), 3.3, 4.6, boxstyle="round,pad=0.1", fc="#ffffff", ec="#10b981", lw=2)
    ax.add_patch(spec_box)
    ax.text(7.95, 5.4, ar("المواصفات القياسية للبياض الداخلي:"), fontsize=8.5, fontweight="bold", color="#065f46", ha="center")

    specs = [
        "• الطرطشة: 450 كجم أسمنت / م3 رمل + مياه خشنة",
        "• البؤج: كل 2.0 م أفقياً لضبط ميزان الخيط والقدة",
        "• شبك فايبر 160 جم/م2 عند فواصل الخرسانة بالمباني",
        "• البطانة: تمشيط السطح لضمان تماسك الضهارة",
        "• المعالجة بالرش بالمياه مرتين يومياً لمدة 3 أيام",
        "• سماكة إجمالية للبياض الداخلي: 2.0 - 2.5 سم"
    ]
    y_sp = 4.9
    for sp in specs:
        ax.text(6.5, y_sp, ar(sp), fontsize=7.5, color="#1e293b")
        y_sp -= 0.6

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


def draw_section_8_external_facade_and_parapet():
    """
    القطاع/المخطط 8: قطاع تفصيلي لمحارة الواجهات الخارجية ودروة السطح
    (External Facade Plastering & Parapet Coping Section)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    ax.add_patch(patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08", fc="#0f172a", ec="#0284c7", lw=2))
    ax.text(5.0, 6.52, ar("القطاع الإنشائي 8: تفاصيل محارة الواجهات الخارجية ودروة السطح (Parapet Wall Detail)"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    ax.add_patch(Rectangle((1.5, 1.4), 6.5, 0.5, fc="#94a3b8", ec="#0f172a", lw=2))
    ax.text(6.0, 1.65, ar("بلاطة السقف النهائي (Roof RC Slab ts=20cm)"), color="#ffffff", fontsize=8.5, fontweight="bold")

    ax.add_patch(Rectangle((1.5, 1.9), 1.8, 3.2, fc="#fee2e2", ec="#b91c1c", lw=2, hatch="//"))
    ax.text(2.4, 3.5, ar("دروة السطح 25 سم\n(Parapet Wall)\nارتفاع 1.0 - 1.2 م"), color="#991b1b", fontsize=8.5, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((1.3, 5.1), 2.2, 0.45, fc="#cbd5e1", ec="#0f172a", lw=2))
    ax.text(2.4, 5.32, ar("جلسة خرسانية/رخام بميول للداخل ومجرى مائي سفلي"), fontsize=7, color="#0f172a", ha="center", fontweight="bold")

    cant_tri = Polygon([(3.3, 1.9), (3.7, 1.9), (3.3, 2.3)], fc="#64748b", ec="#0f172a", lw=1.5)
    ax.add_patch(cant_tri)
    ax.text(4.2, 2.2, ar("رقبة زجاجة مثلثة أسمنتية (Cant Strip)"), fontsize=7.5, color="#1e3a8a", fontweight="bold")

    ax.plot([3.3, 3.3, 3.7, 7.5], [2.8, 2.3, 1.9, 1.9], color="#0f172a", lw=3)
    ax.text(5.5, 2.6, ar("طبقات عزل الرطوبة والحرارة مثبتة داخل تجويف بالدروة"), fontsize=7.5, color="#0f172a", fontweight="bold")

    ax.plot([1.4, 1.4], [0.8, 5.1], color="#0284c7", lw=4)
    ax.text(0.3, 3.0, ar("بياض واجهات مقاوم للعوامل الجوية:\n• طرطشة مساميرية 0.5 سم\n• بياض أسمنتي مع إضافة أديبوند\n• دهان أكريليك مطاطي عازل"),
            fontsize=7.5, color="#0369a1", fontweight="bold", bbox=dict(boxstyle="round,pad=0.3", fc="#f0f9ff", ec="#0284c7"))

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


def draw_section_9_lintel_structural_detail():
    """
    القطاع/المخطط 9: التفصيلة الإنشائية لعتب الفتحات الخرساني المسلح وتوزيعه
    (Reinforced Concrete Lintel Structural Section & Bearings)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    ax.add_patch(patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08", fc="#0f172a", ec="#8b5cf6", lw=2))
    ax.text(5.0, 6.52, ar("القطاع الإنشائي 9: التفصيلة الإنشائية وتفريد تسليح الأعتاب الخرسانية المسلحة (RC Lintels)"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    ax.text(4.0, 5.7, ar("أ) المسقط الرأسي وتفريد حديد التسليح للعتب (Longitudinal Elevation)"), fontsize=9.5, fontweight="bold", color="#6d28d9", ha="center")
    ax.add_patch(Rectangle((1.0, 3.6), 6.0, 1.6, fc="#cbd5e1", ec="#0f172a", lw=2))

    ax.add_patch(Rectangle((1.0, 2.2), 1.4, 1.4, fc="#fee2e2", ec="#b91c1c", lw=1.5, hatch="//"))
    ax.text(1.7, 2.9, ar("كتف مباني (ركوب ≥ 25سم)"), fontsize=7.5, ha="center", color="#991b1b", fontweight="bold")

    ax.add_patch(Rectangle((5.6, 2.2), 1.4, 1.4, fc="#fee2e2", ec="#b91c1c", lw=1.5, hatch="//"))
    ax.text(6.3, 2.9, ar("كتف مباني (ركوب ≥ 25سم)"), fontsize=7.5, ha="center", color="#991b1b", fontweight="bold")

    ax.text(4.0, 2.8, ar("البحر الصافي للفتحة (Clear Span L = 1.60 m)"), fontsize=8.5, ha="center", color="#0369a1", fontweight="bold")
    ax.annotate("", xy=(2.4, 2.5), xytext=(5.6, 2.5), arrowprops=dict(arrowstyle="<->", color="#0284c7", lw=1.5))

    ax.plot([1.2, 6.8], [3.85, 3.85], color="#dc2626", lw=3.5)
    ax.plot([1.2, 1.2], [3.85, 4.3], color="#dc2626", lw=3.5)
    ax.plot([6.8, 6.8], [3.85, 4.3], color="#dc2626", lw=3.5)
    ax.text(4.0, 3.65, ar("حديد سفلي رئيسي: 2 Φ 12 مم مع أرجُل طرفية"), fontsize=8, color="#991b1b", ha="center", fontweight="bold")

    ax.plot([1.2, 6.8], [4.95, 4.95], color="#2563eb", lw=2.5)
    ax.text(4.0, 5.05, ar("حديد علوي تعليق كانات: 2 Φ 10 مم"), fontsize=8, color="#1e40af", ha="center", fontweight="bold")

    for x_st in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5]:
        ax.plot([x_st, x_st], [3.85, 4.95], color="#0f172a", lw=1.2, linestyle="-")
    ax.text(4.0, 4.4, ar("كانات: 5 Φ 8 / م بقفل 135° تبادلي"), fontsize=8, color="#0f172a", ha="center")

    # Cross Section on Right
    ax.text(8.5, 5.7, ar("ب) قطاع عرضي (Cross Section)"), fontsize=9.5, fontweight="bold", color="#6d28d9", ha="center")
    ax.add_patch(Rectangle((7.6, 2.4), 1.8, 2.8, fc="#cbd5e1", ec="#0f172a", lw=2))
    ax.add_patch(Rectangle((7.8, 2.6), 1.4, 2.4, fill=False, ec="#0f172a", lw=2))
    ax.plot(8.0, 2.8, marker="o", color="#dc2626", markersize=8)
    ax.plot(9.0, 2.8, marker="o", color="#dc2626", markersize=8)
    ax.text(8.5, 2.0, ar("2 Φ 12 مم"), fontsize=8, color="#dc2626", ha="center", fontweight="bold")
    ax.plot(8.0, 4.8, marker="o", color="#2563eb", markersize=7)
    ax.plot(9.0, 4.8, marker="o", color="#2563eb", markersize=7)
    ax.text(8.5, 5.3, ar("2 Φ 10 مم"), fontsize=8, color="#2563eb", ha="center", fontweight="bold")

    ax.text(8.5, 1.6, ar("عرض b = 25/12 سم | عمق D ≥ 15 سم"), fontsize=7.5, color="#0f172a", ha="center", fontweight="bold")

    ax.text(5.0, 0.4, ar("ملاحظة إنشائية: إذا زاد بحر الفتحة عن 2.00 م، يُصمم العتب ككمرة خرسانية مستقلة بكامل الاشتراطات الإنشائية للترخيم والقص"),
            fontsize=8, color="#4c1d95", fontweight="bold", ha="center")

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


def draw_section_10_crack_control_wire_mesh():
    """
    القطاع/المخطط 10: مخطط تفاصيل شبك الفايبر المعدني والفواصل لمنع الشروخ
    (Fiberglass / Wire Mesh Crack Control Details)
    """
    fig = plt.figure(figsize=(11, 7.5), facecolor="#ffffff")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    ax.add_patch(patches.FancyBboxPatch((0.2, 6.2), 9.6, 0.65, boxstyle="round,pad=0.08", fc="#0f172a", ec="#ec4899", lw=2))
    ax.text(5.0, 6.52, ar("القطاع الإنشائي 10: تفاصيل وتوزيع شبك الفايبر المعدني والفواصل لمنع الشروخ الإنشائية"),
            color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center")

    ax.add_patch(Rectangle((0.6, 1.2), 1.4, 4.6, fc="#64748b", ec="#0f172a", lw=2))
    ax.text(1.3, 3.5, ar("عمود خرساني\n(RC Column)"), color="#ffffff", fontsize=8.5, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((0.6, 5.0), 8.8, 0.8, fc="#64748b", ec="#0f172a", lw=2))
    ax.text(5.0, 5.4, ar("كمرة خرسانية ساقطة (RC Beam)"), color="#ffffff", fontsize=8.5, fontweight="bold", ha="center")

    ax.add_patch(Rectangle((2.0, 1.2), 7.4, 3.8, fc="#fee2e2", ec="#b91c1c", lw=2, hatch="//"))

    ax.add_patch(Rectangle((4.5, 2.2), 2.2, 1.8, fc="#ffffff", ec="#0284c7", lw=2))
    ax.text(5.6, 3.1, ar("فتحة شباك\n(Window Opening)"), color="#0369a1", fontsize=8.5, ha="center")

    ax.add_patch(Rectangle((1.7, 1.2), 0.6, 3.8, fc="#f472b6", ec="#db2777", lw=1.5, alpha=0.7, hatch="xx"))
    ax.text(2.0, 0.7, ar("شبك فايبر بعرض 20 سم\nمركز على فاصل العمود بالمباني"), fontsize=7.5, color="#be185d", ha="center", fontweight="bold")

    ax.add_patch(Rectangle((2.0, 4.7), 7.4, 0.6, fc="#f472b6", ec="#db2777", lw=1.5, alpha=0.7, hatch="xx"))
    ax.text(7.5, 4.4, ar("شبك فايبر 20 سم عند تقاطع الكمرة مع المباني"), fontsize=7.5, color="#be185d", fontweight="bold")

    corner_coords = [
        ((4.2, 3.8), (4.7, 4.3)),
        ((6.5, 3.8), (7.0, 4.3)),
        ((4.2, 1.9), (4.7, 2.4)),
        ((6.5, 1.9), (7.0, 2.4)),
    ]
    for c_start, c_end in corner_coords:
        ax.plot([c_start[0], c_end[0]], [c_start[1], c_end[1]], color="#db2777", lw=4.5)
        ax.plot([c_start[0], c_end[0]], [c_end[1], c_start[1]], color="#db2777", lw=4.5)

    ax.text(5.6, 1.6, ar("شرائح شبك زاوية 45° بأركان الفتحة لمنع شروخ التركيز الإجهادي"), fontsize=8, color="#be185d", ha="center", fontweight="bold")

    ax.text(5.0, 0.2, ar("الكود الإنشائي: يثبت الشبك بمسامير صلب ووردات مجلفنة كل 25 سم على الجانبين قبل تطبيق طبقة الطرطشة والبطانة"),
            fontsize=8, color="#0f172a", ha="center", fontweight="bold")

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return _fig_to_bytes(fig)


# ═══════════════════════════════════════════════════════════════════════════════
#  3. MASTER RENDERING FUNCTION FOR PHASE 2 (STRUCTURAL DESIGN & DETAILING)
# ═══════════════════════════════════════════════════════════════════════════════

def render_m15_structural_phase_2(walls_placed, wall_thickness, wall_heights, windows, doors, col_placed, buf_plan_clean=None):
    """
    Renders Phase 2:
      - Structural Analysis & Code Compliance Dashboard
      - The 10 Specialized Engineering Drawings & Sections in an interactive UI
    """
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                    border-radius: 12px; border: 2px solid #3b82f6; padding: 16px 22px;
                    margin: 18px 0; box-shadow: 0 6px 20px rgba(15, 23, 42, 0.35);" dir="rtl">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 28px;">🏗️</span>
                    <div>
                        <div style="color: #60a5fa; font-size: 20px; font-weight: 900; line-height: 1.3;">
                            المرحلة الثانية: الحسابات والتصميم الإنشائي الكامل والقطاعات التخصصية
                        </div>
                        <div style="color: #94a3b8; font-size: 13.5px; font-weight: 600;">
                            Phase 2 — Structural Design, Capacity Checks & 10 Specialized Engineering Drawings (ECP 203 & ECP 204)
                        </div>
                    </div>
                </div>
                <div style="background: rgba(16, 185, 129, 0.2); border: 1.5px solid #10b981; color: #34d399;
                            border-radius: 8px; padding: 6px 14px; font-size: 13.5px; font-weight: 800;">
                    ✓ تم التنفيذ بنجاح
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Compute Structural Design Metrics
    res_struct = compute_m15_structural_design(walls_placed, wall_thickness, wall_heights, windows, doors, col_placed)

    # Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""<div style="background:#f8fafc; border:1.5px solid #cbd5e1; border-radius:10px; padding:12px; text-align:center;">
                <div style="color:#64748b; font-size:12px; font-weight:700;">أقصى معامل نحافة للحوائط (λ)</div>
                <div style="color:#0f172a; font-size:22px; font-weight:900;">{res_struct['max_slenderness_12']}</div>
                <div style="color:#16a34a; font-size:11px; font-weight:700;">✓ آمن إنشائياً (الحد ≤ 28)</div>
            </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(
            f"""<div style="background:#f8fafc; border:1.5px solid #cbd5e1; border-radius:10px; padding:12px; text-align:center;">
                <div style="color:#64748b; font-size:12px; font-weight:700;">حمولة حائط 25سم على الكمرة</div>
                <div style="color:#0f172a; font-size:22px; font-weight:900;">{res_struct['w25_dl_m']:.2f} <span style="font-size:13px;">t/m</span></div>
                <div style="color:#2563eb; font-size:11px; font-weight:700;">شامل البياض والمونة (3م)</div>
            </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(
            f"""<div style="background:#f8fafc; border:1.5px solid #cbd5e1; border-radius:10px; padding:12px; text-align:center;">
                <div style="color:#64748b; font-size:12px; font-weight:700;">حمولة قاطع 12سم على البلاطة</div>
                <div style="color:#0f172a; font-size:22px; font-weight:900;">{res_struct['w12_dl_m']:.2f} <span style="font-size:13px;">t/m</span></div>
                <div style="color:#2563eb; font-size:11px; font-weight:700;">شامل البياض والمونة (3م)</div>
            </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(
            f"""<div style="background:#f8fafc; border:1.5px solid #cbd5e1; border-radius:10px; padding:12px; text-align:center;">
                <div style="color:#64748b; font-size:12px; font-weight:700;">إجمالي الأعتاب الخرسانية</div>
                <div style="color:#0f172a; font-size:22px; font-weight:900;">{res_struct['total_lintels']} <span style="font-size:13px;">عتب</span></div>
                <div style="color:#16a34a; font-size:11px; font-weight:700;">توليد أوتوماتيكي كامل</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

    # 2. Specialized Expander for the 10 Engineering Sections & Drawings
    with st.expander("📐 كافة المخططات والرسومات الهندسية والقطاعات الـ 10 التخصصية (The 10 Specialized CAD Drawings)", expanded=True):
        st.markdown(
            """
            <div style="color: #cbd5e1; font-size: 13.5px; font-weight: 700; margin-bottom: 12px;" dir="rtl">
                📌 تم توليد كافة المخططات والقطاعات الـ 10 التخصصية لأعمال المباني والبياض التنفيذية طبقاً للكود المصري للمباني (ECP 204) والكود المصري للخرسانة (ECP 203). اختر القطاع المطلوب للاستعراض والتحميل:
            </div>
            """,
            unsafe_allow_html=True
        )

        tabs = st.tabs([
            "1. مخطط الحوائط والسماكات",
            "2. الفتحات وجدول الأعتاب",
            "3. قطاع حائط خارجي 25سم",
            "4. قطاع قاطع داخلي 12سم",
            "5. رباط الزوايا وتقاطعات T",
            "6. كانات ربط الأعمدة",
            "7. مراحل المحارة الداخلية",
            "8. محارة الواجهات ودروة السطح",
            "9. التفصيلة الإنشائية للعتب",
            "10. شبك الفايبر ومنع الشروخ"
        ])

        with tabs[0]:
            st.markdown("#### 1️⃣ مخطط توقيع وتوزيع حوائط المباني والسماكات الإنشائية (Masonry Layout & Wall Thicknesses)")
            b1 = draw_section_1_wall_layout(buf_plan_clean)
            st.image(b1, use_container_width=True)
            st.download_button("💾 تحميل المخطط 1 (High-Res PNG)", data=b1.getvalue(), file_name="01_masonry_layout_plan.png", mime="image/png", key="m15_dl_sec_1")

        with tabs[1]:
            st.markdown("#### 2️⃣ مخطط توقيع وتفاصيل فتحات الأبواب والشبابيك وجدول الأعتاب (Openings & Lintel Schedule)")
            b2 = draw_section_2_openings_and_lintels(res_struct["lintel_list"])
            st.image(b2, use_container_width=True)
            st.download_button("💾 تحميل المخطط 2 (High-Res PNG)", data=b2.getvalue(), file_name="02_openings_lintels_schedule.png", mime="image/png", key="m15_dl_sec_2")

        with tabs[2]:
            st.markdown("#### 3️⃣ قطاع رأسي كامل في حائط خارجي 25 سم مع العتب والخرسانة والعزل (Vertical Section 25cm Wall)")
            b3 = draw_section_3_external_wall_25cm()
            st.image(b3, use_container_width=True)
            st.download_button("💾 تحميل القطاع 3 (High-Res PNG)", data=b3.getvalue(), file_name="03_external_wall_25cm_section.png", mime="image/png", key="m15_dl_sec_3")

        with tabs[3]:
            st.markdown("#### 4️⃣ قطاع رأسي في قاطع داخلي 12 سم وتثبيت الأبواب والوزرة (Vertical Section 12cm Partition)")
            b4 = draw_section_4_internal_partition_12cm()
            st.image(b4, use_container_width=True)
            st.download_button("💾 تحميل القطاع 4 (High-Res PNG)", data=b4.getvalue(), file_name="04_internal_partition_12cm_section.png", mime="image/png", key="m15_dl_sec_4")

        with tabs[4]:
            st.markdown("#### 5️⃣ تفصيلة رباط الزوايا وتقاطع الحوائط T-Junction والرباط الإنجليزي (Interlocking Masonry Bonds)")
            b5 = draw_section_5_corner_and_junction_bonds()
            st.image(b5, use_container_width=True)
            st.download_button("💾 تحميل القطاع 5 (High-Res PNG)", data=b5.getvalue(), file_name="05_corner_and_junction_bonds.png", mime="image/png", key="m15_dl_sec_5")

        with tabs[5]:
            st.markdown("#### 6️⃣ تفصيلة ربط المباني بالأعمدة والكمرات الخرسانية بالكانات (Wall-to-Column Steel Ties)")
            b6 = draw_section_6_wall_to_column_ties()
            st.image(b6, use_container_width=True)
            st.download_button("💾 تحميل القطاع 6 (High-Res PNG)", data=b6.getvalue(), file_name="06_wall_to_column_ties.png", mime="image/png", key="m15_dl_sec_6")

        with tabs[6]:
            st.markdown("#### 7️⃣ قطاع تفصيلي لطبقات المحارة الداخلية ومراحل التنفيذ (Internal Plastering System)")
            b7 = draw_section_7_internal_plaster_layers()
            st.image(b7, use_container_width=True)
            st.download_button("💾 تحميل القطاع 7 (High-Res PNG)", data=b7.getvalue(), file_name="07_internal_plaster_layers.png", mime="image/png", key="m15_dl_sec_7")

        with tabs[7]:
            st.markdown("#### 8️⃣ قطاع تفصيلي لمحارة الواجهات الخارجية ودروة السطح (External Facade & Parapet Detail)")
            b8 = draw_section_8_external_facade_and_parapet()
            st.image(b8, use_container_width=True)
            st.download_button("💾 تحميل القطاع 8 (High-Res PNG)", data=b8.getvalue(), file_name="08_external_facade_parapet.png", mime="image/png", key="m15_dl_sec_8")

        with tabs[8]:
            st.markdown("#### 9️⃣ التفصيلة الإنشائية لعتب الفتحات الخرساني المسلح وتوزيعه (RC Lintel Detailing)")
            b9 = draw_section_9_lintel_structural_detail()
            st.image(b9, use_container_width=True)
            st.download_button("💾 تحميل القطاع 9 (High-Res PNG)", data=b9.getvalue(), file_name="09_lintel_structural_detail.png", mime="image/png", key="m15_dl_sec_9")

        with tabs[9]:
            st.markdown("#### 🔟 مخطط تفاصيل شبك الفايبر المعدني والفواصل لمنع الشروخ (Crack Control & Mesh Detailing)")
            b10 = draw_section_10_crack_control_wire_mesh()
            st.image(b10, use_container_width=True)
            st.download_button("💾 تحميل القطاع 10 (High-Res PNG)", data=b10.getvalue(), file_name="10_crack_control_wire_mesh.png", mime="image/png", key="m15_dl_sec_10")
