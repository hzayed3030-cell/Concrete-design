"""
modules/steel_bars.py
---------------------
المساعد — اقطار وأوزان الحديد
Steel Reinforcement Bar Diameters & Weights Reference

Displays:
  • Full reference table: diameter → weight per metre, cross-sectional area
  • Interactive calculator: enter count & length → compute total weight & area
"""

import math
import streamlit as st
import pandas as pd
from modules.table_styler import render_styled_table

# ── Bar data (diameter mm, weight kg/m, area cm²) ───────────────────────────
BARS = [
    {"dia_mm": 6,  "weight_kgm": 0.222, "area_cm2": 0.283},
    {"dia_mm": 8,  "weight_kgm": 0.395, "area_cm2": 0.503},
    {"dia_mm": 10, "weight_kgm": 0.617, "area_cm2": 0.785},
    {"dia_mm": 12, "weight_kgm": 0.888, "area_cm2": 1.131},
    {"dia_mm": 14, "weight_kgm": 1.208, "area_cm2": 1.539},
    {"dia_mm": 16, "weight_kgm": 1.578, "area_cm2": 2.011},
    {"dia_mm": 18, "weight_kgm": 1.998, "area_cm2": 2.545},
    {"dia_mm": 20, "weight_kgm": 2.466, "area_cm2": 3.142},
    {"dia_mm": 22, "weight_kgm": 2.984, "area_cm2": 3.801},
    {"dia_mm": 25, "weight_kgm": 3.853, "area_cm2": 4.909},
    {"dia_mm": 28, "weight_kgm": 4.834, "area_cm2": 6.158},
    {"dia_mm": 32, "weight_kgm": 6.313, "area_cm2": 8.042},
]

DIAMETERS = [b["dia_mm"] for b in BARS]
BAR_MAP   = {b["dia_mm"]: b for b in BARS}

# Grade yield strengths (for info display)
GRADES = {
    "St 240 — High-Tensile (عالي المقاومة)": 2400,
    "St 360 — Normal (عادي)":               3600,
    "St 400 — High-Strength (عالي الجودة)":  4000,
    "St 450 — Extra-High (فائق المقاومة)":   4500,
}

# ── Helper ───────────────────────────────────────────────────────────────────
def _area(d_mm: float) -> float:
    """Cross-sectional area in cm² for a given diameter in mm."""
    return math.pi * (d_mm / 10) ** 2 / 4   # mm → cm

def _weight_per_m(d_mm: float) -> float:
    """Weight in kg/m using density 7.85 t/m³."""
    area_m2 = math.pi * (d_mm / 1000) ** 2 / 4
    return area_m2 * 7_850  # kg/m


# ── Main render ──────────────────────────────────────────────────────────────
def render() -> None:
    st.markdown(
        '<div class="section-header">⚙️ Module 5 – Steel Rebar Diameters, Weights & Areas (ECP 203)</div>',
        unsafe_allow_html=True,
    )

    tab_ref, tab_calc, tab_multi = st.tabs([
        "📋 Reference Table (جدول مرجعي)",
        "🔢 Single-Bar Calculator (حاسبة بار واحد)",
        "📦 Multi-Bar Calculator (حاسبة متعددة)",
    ])

    # ────────────────────────────────────────────────────────────────────────
    # TAB 1 — Reference Table
    # ────────────────────────────────────────────────────────────────────────
    with tab_ref:
        st.markdown("#### جدول اقطار حديد التسليح وأوزانها  |  Rebar Properties Table")

        rows = []
        for b in BARS:
            d   = b["dia_mm"]
            w   = b["weight_kgm"]
            a   = b["area_cm2"]
            per = f"{w:.3f}"
            rows.append({
                "القطر Ø (mm)":              d,
                "المساحة المستعرضة (cm²)":   f"{a:.3f}",
                "الوزن / متر طولي (kg/m)":  per,
                "الوزن / 12م (kg/bar)":      f"{w * 12:.2f}",
                "الوزن / 6م  (kg/bar)":      f"{w * 6:.2f}",
                "القطر بالسم (cm)":           f"{d / 10:.1f}",
            })

        df = pd.DataFrame(rows)
        render_styled_table(df)

        st.caption(
            "الكثافة المستخدمة: **7,850 kg/m³**  |  "
            "المساحة = π × d² / 4  |  "
            "الوزن = المساحة (m²) × الكثافة"
        )

        # Grade info
        with st.expander("📌 Steel Grades & Yield Strengths (درجات الحديد وحدود الخضوع)"):
            g_rows = [
                {"الدرجة / Grade": g, "حد الخضوع Fy (kg/cm²)": fy}
                for g, fy in GRADES.items()
            ]
            render_styled_table(g_rows)

        # Areas per metre for multiple bars
        with st.expander("📐 As (n bars/m) Table (مساحة n بار / متر طولي)"):
            counts = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]
            area_rows = []
            for b in BARS:
                row = {"Ø (mm)": f"Ø {b['dia_mm']}"}
                for n in counts:
                    row[f"{n} bars (cm²/m)"] = f"{b['area_cm2'] * n:.3f}"
                area_rows.append(row)
            render_styled_table(area_rows)

    # ────────────────────────────────────────────────────────────────────────
    # TAB 2 — Single-Bar Calculator
    # ────────────────────────────────────────────────────────────────────────
    with tab_calc:
        st.markdown(
            """
            <div class="input-section-header">
                <span style="font-size: 24px;">📥</span>
                <span>بيانات ومدخلات حساب حديد التسليح (Rebar Input Parameters)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("أدخل القطر والعدد وطول السيخ لحساب الوزن الكلي والمساحة الكلية ومعدل الاستهلاك.")

        c1, c2, c3 = st.columns(3)
        with c1:
            dia_sel = st.selectbox(
                "📏 قطر السيخ Ø (mm)",
                options=DIAMETERS,
                format_func=lambda d: f"Ø{d} mm",
                key="sb_dia",
            )
        with c2:
            n_bars = st.number_input(
                "🔢 عدد الأسياخ (n) | No. of Bars",
                min_value=1, max_value=10_000, value=10, step=1,
                key="sb_n",
            )
        with c3:
            length_m = st.number_input(
                "📐 طول السيخ الواحد L (m) | Length per Bar",
                min_value=0.01, max_value=1_000.0, value=12.0, step=0.5,
                key="sb_len",
            )

        bar      = BAR_MAP[dia_sel]
        a_bar    = bar["area_cm2"]
        w_single = bar["weight_kgm"] * length_m
        w_total  = w_single * n_bars
        a_total  = bar["area_cm2"] * n_bars

        st.markdown("---")
        r1, r2, r3, r4, r5 = st.columns(5)
        r1.metric("وزن سيخ واحد  (kg)",     f"{w_single:.3f}")
        r2.metric("الوزن الكلي  (kg)",      f"{w_total:.2f}")
        r3.metric("الوزن الكلي  (ton)",     f"{w_total / 1000:.4f}")
        r4.metric("مساحة مقطع السيخ (cm²)", f"{a_bar:.3f}")
        r5.metric("المساحة الكلية  (cm²)",   f"{a_total:.3f}")

        st.info(
            f"**Ø{dia_sel} mm** (مساحة السيخ $A_s$ = **{a_bar:.3f} cm²**) — {n_bars} سيخ × {length_m} m  →  "
            f"الوزن = **{w_total:.2f} kg** = **{w_total/1000:.4f} ton** | المساحة الكلية = **{a_total:.3f} cm²**"
        )

    # ────────────────────────────────────────────────────────────────────────
    # TAB 3 — Multi-Bar Calculator (dynamic rows)
    # ────────────────────────────────────────────────────────────────────────
    with tab_calc:
        pass  # handled above

    with tab_multi:
        st.markdown(
            """
            <div class="input-section-header">
                <span style="font-size: 24px;">📥</span>
                <span>جدول بنود ومدخلات حديد التسليح المتعددة (Multi-Diameter Rebar Input Schedule)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "أضف بنود حديد التسليح بأقطار وأعداد وأطوال مختلفة لحساب الأوزان والمساحات لكل بند والإجمالي العام."
        )

        # Session state init
        if "sb_rows" not in st.session_state:
            st.session_state["sb_rows"] = [
                {"dia": 16, "n": 10, "length": 12.0, "desc": ""},
            ]

        def _add_row():
            st.session_state["sb_rows"].append(
                {"dia": 16, "n": 5, "length": 12.0, "desc": ""}
            )

        def _clear_rows():
            st.session_state["sb_rows"] = [
                {"dia": 16, "n": 10, "length": 12.0, "desc": ""}
            ]

        col_add, col_clr, _ = st.columns([1.2, 1.2, 3.6])
        col_add.button("➕ إضافة بند تسليح", on_click=_add_row, use_container_width=True)
        col_clr.button("🗑️ مسح الجدول",  on_click=_clear_rows, use_container_width=True)

        st.markdown(
            """
            <div style="background:linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border:1px solid rgba(56, 189, 248, 0.35); border-radius:8px 8px 0 0; padding:10px 14px; margin-top:14px;">
                <div style="font-weight:900; font-size:15px; color:#38bdf8;">📋 تفاصيل مدخلات وبنود التسليح (Rebar Items Input Table):</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Header titles row above dynamic input boxes
        h_desc, h_dia, h_n, h_len, h_del = st.columns([3, 1.5, 1, 1.5, 0.5])
        h_desc.markdown("<div style='font-size:14.5px; font-weight:800; color:#38bdf8; text-align:right; padding:4px 0;'>📝 وصف البند / العنصر</div>", unsafe_allow_html=True)
        h_dia.markdown("<div style='font-size:14.5px; font-weight:800; color:#38bdf8; text-align:center; padding:4px 0;'>📏 قطر السيخ Ø</div>", unsafe_allow_html=True)
        h_n.markdown("<div style='font-size:14.5px; font-weight:800; color:#38bdf8; text-align:center; padding:4px 0;'>🔢 العدد (n)</div>", unsafe_allow_html=True)
        h_len.markdown("<div style='font-size:14.5px; font-weight:800; color:#38bdf8; text-align:center; padding:4px 0;'>📐 الطول L (m)</div>", unsafe_allow_html=True)
        h_del.markdown("<div style='font-size:14.5px; font-weight:800; color:#f87171; text-align:center; padding:4px 0;'>حذف</div>", unsafe_allow_html=True)

        rows_data = st.session_state["sb_rows"]
        to_delete = []

        for i, row in enumerate(rows_data):
            c_desc, c_dia, c_n, c_len, c_del = st.columns([3, 1.5, 1, 1.5, 0.5])
            with c_desc:
                rows_data[i]["desc"] = st.text_input(
                    f"وصف / Desc #{i+1}", value=row["desc"],
                    key=f"mb_desc_{i}", label_visibility="collapsed",
                    placeholder=f"بند #{i+1} (مثال: أشاير أعمدة دور أرضي)",
                )
            with c_dia:
                rows_data[i]["dia"] = st.selectbox(
                    f"Ø #{i+1}", options=DIAMETERS,
                    index=DIAMETERS.index(row["dia"]) if row["dia"] in DIAMETERS else 5,
                    format_func=lambda d: f"Ø{d} mm",
                    key=f"mb_dia_{i}", label_visibility="collapsed",
                )
            with c_n:
                rows_data[i]["n"] = st.number_input(
                    f"n #{i+1}", min_value=1, max_value=100_000,
                    value=int(row["n"]), step=1,
                    key=f"mb_n_{i}", label_visibility="collapsed",
                )
            with c_len:
                rows_data[i]["length"] = st.number_input(
                    f"L #{i+1}", min_value=0.01, max_value=10_000.0,
                    value=float(row["length"]), step=0.5, format="%.2f",
                    key=f"mb_len_{i}", label_visibility="collapsed",
                )
            with c_del:
                if st.button("✕", key=f"mb_del_{i}", help="حذف هذا السطر"):
                    to_delete.append(i)

        # Remove deleted rows
        for idx in reversed(to_delete):
            st.session_state["sb_rows"].pop(idx)
        if to_delete:
            st.rerun()

        # Results table
        st.markdown("---")
        result_rows = []
        total_kg  = 0.0
        total_a   = 0.0
        for row in rows_data:
            b   = BAR_MAP[row["dia"]]
            w   = b["weight_kgm"] * row["length"] * row["n"]
            a   = b["area_cm2"]   * row["n"]
            total_kg += w
            total_a  += a
            result_rows.append({
                "الوصف":               row["desc"] or "—",
                "Ø (mm)":              row["dia"],
                "العدد":               row["n"],
                "الطول (m)":           row["length"],
                "الوزن الكلي (kg)":   f"{w:.2f}",
                "المساحة الكلية (cm²)": f"{a:.3f}",
            })

        result_rows.append({
            "الوصف":               "✅ الإجمالي / TOTAL",
            "Ø (mm)":              "—",
            "العدد":               "—",
            "الطول (m)":           "—",
            "الوزن الكلي (kg)":   f"{total_kg:.2f}",
            "المساحة الكلية (cm²)": f"{total_a:.3f}",
        })

        render_styled_table(result_rows)

        m1, m2, m3 = st.columns(3)
        m1.metric("إجمالي الوزن (kg)",  f"{total_kg:.2f}")
        m2.metric("إجمالي الوزن (ton)", f"{total_kg / 1000:.4f}")
        m3.metric("إجمالي المساحة (cm²)", f"{total_a:.3f}")
