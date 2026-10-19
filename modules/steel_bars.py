"""
modules/steel_bars.py
---------------------
المساعد — اقطار وأوزان الحديد
Steel Reinforcement Bar Diameters & Weights Reference

Displays:
  • Tab 1 (Steel bars): Reference table & Multi-Bar schedule calculator
  • Tab 2 (Moment against Steel): Ultimate moment capacity calculator (Mu = As * fy * j * d)
"""

import math
import os
import streamlit as st
import streamlit.components.v1 as components
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

# Egyptian standard diameters for Moment calculator (excluding Ø14 mm)
MOMENT_DIAMETERS = [d for d in DIAMETERS if d != 14]

# Yield strength options (kg/cm²)
FY_OPTIONS = [2400, 3600, 4000, 4200, 4500]

# ── Helper ───────────────────────────────────────────────────────────────────
def _area(d_mm: float) -> float:
    """Cross-sectional area in cm² for a given diameter in mm."""
    return math.pi * (d_mm / 10) ** 2 / 4   # mm → cm

def _weight_per_m(d_mm: float) -> float:
    """Weight in kg/m using density 7.85 t/m³."""
    area_m2 = math.pi * (d_mm / 1000) ** 2 / 4
    return area_m2 * 7_850  # kg/m


def calculate_concrete_properties(fcu_kg_cm2: float) -> dict:
    """
    Calculate concrete properties according to Egyptian (ECP 203) and American (ACI 318 / AISC) codes:
      • fcu (MPa) = fcu (kg/cm²) / 10.0
      • E_c ECP (MPa) = 4400 * sqrt(fcu)  -->  E_c ECP (t/m²) = E_c (MPa) * 100
      • f'c (MPa) = 0.80 * fcu            -->  f'c (t/m²) = f'c (MPa) * 100
      • E_c ACI (MPa) = 4700 * sqrt(f'c)  -->  E_c ACI (t/m²) = E_c (MPa) * 100
    """
    fcu_kg = max(0.0, float(fcu_kg_cm2))
    fcu_mpa = fcu_kg / 10.0
    fcu_ton_m2 = fcu_mpa * 100.0

    # Egyptian Code ECP 203: Ec = 4400 * sqrt(fcu) [MPa]
    ec_ecp_mpa = 4400.0 * math.sqrt(fcu_mpa)
    ec_ecp_ton_m2 = ec_ecp_mpa * 100.0  # 1 MPa = 100 t/m²

    # American Code ACI 318 / AISC: f'c = 0.80 * fcu [MPa]
    fc_prime_mpa = 0.80 * fcu_mpa
    fc_prime_ton_m2 = fc_prime_mpa * 100.0
    fc_prime_kg_cm2 = fc_prime_mpa * 10.0

    # American Code ACI 318 / AISC: Ec = 4700 * sqrt(f'c) [MPa]
    ec_aci_mpa = 4700.0 * math.sqrt(fc_prime_mpa)
    ec_aci_ton_m2 = ec_aci_mpa * 100.0  # 1 MPa = 100 t/m²

    return {
        "fcu_kg_cm2": fcu_kg,
        "fcu_mpa": fcu_mpa,
        "fcu_ton_m2": fcu_ton_m2,
        "fc_prime_kg_cm2": fc_prime_kg_cm2,
        "fc_prime_mpa": fc_prime_mpa,
        "fc_prime_ton_m2": fc_prime_ton_m2,
        "ec_ecp_mpa": ec_ecp_mpa,
        "ec_ecp_ton_m2": ec_ecp_ton_m2,
        "ec_aci_mpa": ec_aci_mpa,
        "ec_aci_ton_m2": ec_aci_ton_m2,
    }



# ── Main render ──────────────────────────────────────────────────────────────
def render() -> None:
    # Resolve Word file path
    _module_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_module_dir)
    docx_file_path = os.path.join(_project_root, "assets", "خطوات تصميم بلاطات وكمرات برنامج SAFE.docx")
    if not os.path.exists(docx_file_path):
        docx_file_path = os.path.join("assets", "خطوات تصميم بلاطات وكمرات برنامج SAFE.docx")

    # ── Word button anchor & absolute positioning on the tab bar ─────────────
    st.markdown(
        """
        <div id="m12_word_btn_anchor" style="display:none;"></div>
        <style>
        /* Make the parent vertical block relative so the button pins to its top-right */
        div[data-testid="stVerticalBlock"]:has(#m12_word_btn_anchor) {
            position: relative !important;
        }

        /* Collapse the marker container completely so it occupies 0 height */
        div[data-testid="stElementContainer"]:has(#m12_word_btn_anchor),
        div[data-testid="element-container"]:has(#m12_word_btn_anchor),
        div:has(> #m12_word_btn_anchor) {
            height: 0px !important;
            min-height: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
            overflow: hidden !important;
            line-height: 0px !important;
        }

        /* Position the Word button container at the exact top-right of the tab list */
        div[data-testid="stElementContainer"]:has(#m12_word_btn_anchor) + div[data-testid="stElementContainer"],
        div[data-testid="element-container"]:has(#m12_word_btn_anchor) + div[data-testid="element-container"],
        div:has(> #m12_word_btn_anchor) + div {
            position: absolute !important;
            right: 0 !important;
            top: 2px !important;
            z-index: 999 !important;
            width: auto !important;
            max-width: fit-content !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Modern styled button matching the title width */
        div:has(> #m12_word_btn_anchor) + div button {
            border-radius: 8px !important;
            font-weight: 800 !important;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35) !important;
            height: 36px !important;
            min-height: 36px !important;
            white-space: nowrap !important;
            width: auto !important;
            max-width: fit-content !important;
            padding: 0 16px !important;
            background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
            border: 1px solid #38bdf8 !important;
            color: #ffffff !important;
        }

        div:has(> #m12_word_btn_anchor) + div button:hover {
            background: linear-gradient(135deg, #0369a1 0%, #1e40af 100%) !important;
            box-shadow: 0 6px 16px rgba(2, 132, 199, 0.55) !important;
            transform: translateY(-1px);
        }

        div:has(> #m12_word_btn_anchor) + div button * {
            font-weight: 800 !important;
            font-size: 13.5px !important;
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button("📝 خطوات تصميم البلاطات والكمرات برنامج CSI SAFE", key="module_top_open_word_btn", type="primary", use_container_width=False):
        if os.path.exists(docx_file_path):
            try:
                os.startfile(os.path.abspath(docx_file_path))
                st.toast("✅ تم فتح ملف الورد في برنامج Microsoft Word!", icon="📄")
            except Exception as err:
                st.error(f"تعذر فتح ملف Word: {err}")
        else:
            st.error("ملف Word غير موجود في مسار assets.")

    tab_csi_safe, tab_steel, tab_slab_weight = st.tabs([
        "CSI SAFE assistant sections",
        "Steel bars",
        "Slab on Grade / Mat Steel Weight",
    ])

    # ────────────────────────────────────────────────────────────────────────
    # TAB 1 — CSI SAFE assistant sections
    # ────────────────────────────────────────────────────────────────────────
    with tab_csi_safe:
        with st.expander("⚡ Moment Capacity vs. Provided Reinforcement (حساب العزم المقاوم لحديد التسليح)", expanded=True):
            st.markdown(
                """
                <div dir="rtl" style="font-size: 15px; font-weight: 500; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; line-height: 1.8; text-align: right; margin-bottom: 16px; padding: 12px 16px; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border-right: 4px solid #38bdf8;">
                    <div style="font-weight: 700; font-size: 15px; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; margin-bottom: 8px;">
                        معادلة حساب عزم الانحناء المقاوم: <span style="color:#38bdf8; font-weight:700;">M<sub>u</sub> = A<sub>s</sub> × f<sub>y</sub> × j × d</span>
                    </div>
                    <div style="font-weight: 700; font-size: 15px; color: #fbbf24 !important; -webkit-text-fill-color: #fbbf24 !important; margin-top: 10px; margin-bottom: 4px;">
                        💡 تنبيه وإرشاد هندسي (Engineering Design Note):
                    </div>
                    <div style="font-size: 14px; color: #e2e8f0; line-height: 1.8;">
                        • <strong>الخيار الأكثر أماناً وتحفظاً:</strong> استخدام (<span style="color:#38bdf8; font-weight:700;">f<sub>y</sub> = 3,600 kg/cm²</span>) مع (<span style="color:#38bdf8; font-weight:700;">j = 0.80</span>) يمنح المنشأ معامل أمان إضافي بنحو 15% ضد عيوب التنفيذ وهبوط الشدات، ويساهم بفعالية في تقليص الترخيم والتحكم في اتساع الشروخ للبلاطات.<br>
                        • <strong>الخيار الاقتصادي المطابق للمواصفات:</strong> استخدام (<span style="color:#38bdf8; font-weight:700;">f<sub>y</sub> = 4,000 kg/cm²</span>) مع (<span style="color:#38bdf8; font-weight:700;">j = 0.826</span>) يطابق رتب حديد التسليح الفعلي المنتج بالمصانع المعتمدة والحد الأقصى لذراع العزم وفق الكود المصري ECP 203، ويوفر في كميات التسليح دون الإخلال بحدود الأمان الإنشائي.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # CSS for wrapping input labels in single-row layout & forcing 6-column nowrap
            st.markdown(
                """
                <style>
                details summary, details summary * {
                    user-select: none !important;
                    -webkit-user-select: none !important;
                }
                div[data-testid="column"] label,
                div[data-testid="stColumn"] label {
                    min-height: 20px !important;
                    height: 20px !important;
                    margin-bottom: 4px !important;
                    display: flex !important;
                    align-items: center !important;
                }
                div[data-testid="column"] label p,
                div[data-testid="stColumn"] label p {
                    font-size: 12px !important;
                    font-weight: 700 !important;
                    margin: 0 !important;
                    white-space: nowrap !important;
                    line-height: 1.2 !important;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) {
                    display: flex !important;
                    flex-direction: row !important;
                    flex-wrap: nowrap !important;
                    align-items: flex-start !important;
                    gap: 6px !important;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) > div {
                    min-width: 0 !important;
                    flex-shrink: 1 !important;
                }
                @media (max-width: 900px) {
                    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) {
                        flex-wrap: nowrap !important;
                    }
                    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) > div {
                        min-width: 0 !important;
                    }
                }

                /* Stepper Buttons (+ / −) styling for Bars (n) & number inputs */
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) button[data-testid="stNumberInputStepUp"],
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) button[data-testid="stNumberInputStepDown"] {
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    background: rgba(56, 189, 248, 0.12) !important;
                    border: 1px solid rgba(56, 189, 248, 0.35) !important;
                    min-width: 18px !important;
                    cursor: pointer !important;
                    transition: all 0.15s ease !important;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) button[data-testid="stNumberInputStepUp"]:hover,
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) button[data-testid="stNumberInputStepDown"]:hover {
                    background: rgba(56, 189, 248, 0.35) !important;
                    border-color: #38bdf8 !important;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) button[data-testid="stNumberInputStepUp"] svg,
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) button[data-testid="stNumberInputStepDown"] svg {
                    display: none !important;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) button[data-testid="stNumberInputStepUp"]::after {
                    content: "+" !important;
                    font-size: 13px !important;
                    font-weight: 900 !important;
                    color: #38bdf8 !important;
                    line-height: 1 !important;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(6)) button[data-testid="stNumberInputStepDown"]::after {
                    content: "−" !important;
                    font-size: 13px !important;
                    font-weight: 900 !important;
                    color: #38bdf8 !important;
                    line-height: 1 !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            # Control: Number of Reinforcement Models
            col_n_mod, _ = st.columns([2, 4])
            with col_n_mod:
                n_models = st.number_input(
                    "🔢 عدد نماذج التسليح (No. of Models)",
                    min_value=1,
                    max_value=10,
                    value=1,
                    step=1,
                    key="mas_n_models",
                    help="اختر عدد نماذج التسليح",
                )

            total_all_mu_tm = 0.0

            for i in range(int(n_models)):
                st.markdown(
                    f"""
                    <div style="font-weight: 800; font-size: 14px; color: #38bdf8; margin-top: {24 if i > 0 else 14}px; margin-bottom: 14px; padding-bottom: 6px; border-bottom: 1px dashed rgba(56, 189, 248, 0.25); text-align: right;">
                        🔹 نموذج تسليح رقم #{i+1}:
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # 5 inputs + 1 compact output panel in a single row
                c1, c2, c3, c4, c5, c6 = st.columns([0.85, 1.05, 1.02, 1.02, 0.85, 1.15])

                with c1:
                    num_bars = st.number_input(
                        "Bars (n)",
                        min_value=1,
                        max_value=1000,
                        value=5,
                        step=1,
                        key=f"mas_n_{i}",
                        help="عدد الأسياخ (n)",
                    )

                with c2:
                    dia_default_idx = MOMENT_DIAMETERS.index(12) if 12 in MOMENT_DIAMETERS else 0
                    diameter = st.selectbox(
                        "Diameter (Φ)",
                        options=MOMENT_DIAMETERS,
                        index=dia_default_idx,
                        format_func=lambda d: f"Φ{d} mm",
                        key=f"mas_dia_{i}",
                        help="قطر سيخ التسليح بالمليمتر (بدون 14 مم)",
                    )

                with c3:
                    depth_d = st.number_input(
                        "Depth d [cm]",
                        min_value=5.0,
                        max_value=500.0,
                        value=18.0,
                        step=0.5,
                        key=f"mas_depth_{i}",
                        help="العمق الفعال للقطاع الخرساني (d = t - cover)",
                    )

                with c4:
                    fy_default_idx = FY_OPTIONS.index(3600) if 3600 in FY_OPTIONS else 0
                    fy = st.selectbox(
                        "Yield fy",
                        options=FY_OPTIONS,
                        index=fy_default_idx,
                        format_func=lambda f: f"{f} kg/cm²",
                        key=f"mas_fy_{i}",
                        help="إجهاد خضوع حديد التسليح",
                    )

                with c5:
                    j_factor = st.number_input(
                        "Arm (j)",
                        min_value=0.50,
                        max_value=0.95,
                        value=0.80,
                        step=0.01,
                        key=f"mas_j_{i}",
                        help="معامل ذراع العزم (الافتراضي 0.80)",
                    )

                # Calculations for model i
                area_single_bar_cm2 = (math.pi * ((diameter / 10.0) ** 2)) / 4.0
                total_as_cm2 = num_bars * area_single_bar_cm2
                moment_kg_cm = total_as_cm2 * fy * j_factor * depth_d
                moment_t_m = moment_kg_cm / 100000.0

                total_all_mu_tm += moment_t_m

                # c6: Compact output panel - header aligned with labels (20px), value box aligned with inputs (28px)
                with c6:
                    st.markdown(
                        f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; height: 22px; margin-bottom: 4px; gap: 4px;">
                            <span style="font-size: 12px; font-weight: 800; color: #38bdf8; line-height: 1; white-space: nowrap;">M<sub>u</sub> #{i+1}</span>
                            <button class="ecp-copy-mu-btn" data-copy-val="{moment_t_m:.2f}"
                                    title="نسخ القيمة العددية ({moment_t_m:.2f})" 
                                    style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); 
                                           border: 1px solid #38bdf8; border-radius: 5px; 
                                           color: #ffffff; cursor: pointer; 
                                           padding: 0 8px; font-size: 11px; font-weight: 700; 
                                           height: 22px; line-height: 20px; min-width: 58px;
                                           display: inline-flex; align-items: center; justify-content: center; gap: 4px;
                                           box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35); transition: all 0.2s ease;">
                                <span style="font-size: 11px;">📋</span> <span>نسخ</span>
                            </button>
                        </div>
                        <div class="ecp-copy-mu-box" data-copy-val="{moment_t_m:.2f}"
                             title="انقر لنسخ القيمة العددية ({moment_t_m:.2f})"
                             style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                                    border: 1.5px solid #38bdf8; border-radius: 6px; height: 28px; box-sizing: border-box;
                                    display: flex; justify-content: center; align-items: center; gap: 7px; direction: ltr;
                                    box-shadow: 0 2px 6px rgba(0,0,0,0.3); white-space: nowrap; padding: 0 6px; cursor: pointer; transition: all 0.2s ease;">
                            <span id="mu_val_{i}" style="font-size: 16px; font-weight: 900; color: #ffffff; line-height: 1; user-select: all; -webkit-user-select: all;">{moment_t_m:.2f}</span>
                            <span style="font-size: 11.5px; font-weight: 700; color: #38bdf8; user-select: none; -webkit-user-select: none; pointer-events: none;">t.m</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Panel for Total Moments of all panels (مجموع عزوم البانيلات)
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                            border: 2px solid #38bdf8; border-radius: 10px; padding: 12px 20px; margin-top: 22px; margin-bottom: 12px;
                            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 22px;">🏆</span>
                            <div>
                                <div style="font-weight: 900; font-size: 16px; color: #38bdf8; text-align: right;">
                                    مجموع عزوم البانيلات (Total Moment Capacity)
                                </div>
                                <div style="font-size: 12.5px; color: #94a3b8; text-align: right;">
                                    العزم الإجمالي المقاوم الناتج من نماذج التسليح ({n_models} نموذج)
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 16px;">
                            <div class="ecp-copy-mu-box" data-copy-val="{total_all_mu_tm:.2f}"
                                 title="انقر لنسخ القيمة العددية ({total_all_mu_tm:.2f})"
                                 style="display: flex; align-items: baseline; gap: 8px; direction: ltr; cursor: pointer;">
                                <span id="mu_total_val" style="font-size: 26px; font-weight: 900; color: #ffffff; user-select: all; -webkit-user-select: all;">{total_all_mu_tm:.2f}</span>
                                <span style="font-size: 16px; font-weight: 800; color: #38bdf8; user-select: none; -webkit-user-select: none; pointer-events: none;">t.m</span>
                            </div>
                            <button class="ecp-copy-mu-total-btn" data-copy-val="{total_all_mu_tm:.2f}"
                                    title="نسخ القيمة العددية ({total_all_mu_tm:.2f})" 
                                    style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); border: 1.5px solid #38bdf8; border-radius: 6px; color: #ffffff; cursor: pointer; padding: 6px 16px; font-size: 13px; font-weight: 800; box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4); display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s ease;">
                                <span>📋</span> <span>نسخ الإجمالي</span>
                            </button>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Inject parent document event listener & floating toast via components.html
            components.html(
                """
                <script>
                (function() {
                    var parentDoc = (window.parent && window.parent.document) ? window.parent.document : document;
                    var parentWin = (window.parent) ? window.parent : window;

                    function showCopyToast(val, customMsg) {
                        var toast = parentDoc.getElementById('ecp-mu-copy-toast');
                        if (!toast) {
                            toast = parentDoc.createElement('div');
                            toast.id = 'ecp-mu-copy-toast';
                            toast.style.cssText = 'position:fixed;bottom:35px;left:50%;transform:translateX(-50%) translateY(20px);background:linear-gradient(135deg,#065f46 0%,#059669 50%,#10b981 100%);color:#ffffff;padding:10px 24px;border-radius:24px;font-size:14.5px;font-weight:800;font-family:system-ui,-apple-system,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,0.5),0 0 15px rgba(16,185,129,0.4);z-index:9999999;display:flex;align-items:center;gap:10px;direction:rtl;pointer-events:none;transition:opacity 0.25s cubic-bezier(0.4,0,0.2,1),transform 0.25s cubic-bezier(0.4,0,0.2,1);opacity:0;border:1.5px solid rgba(255,255,255,0.4);';
                            parentDoc.body.appendChild(toast);
                        }
                        if (customMsg) {
                            toast.innerHTML = '<span style="font-size:18px;">📋</span> <span>' + customMsg + '</span>';
                            toast.style.background = 'linear-gradient(135deg, #991b1b 0%, #dc2626 50%, #ef4444 100%)';
                            toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5), 0 0 16px rgba(239,68,68,0.55)';
                            toast.style.border = '1.5px solid #f87171';
                        } else {
                            toast.innerHTML = '<span style="font-size:18px;">✓</span> <span>تم نسخ القيمة: <strong style="color:#ffffff;text-decoration:underline;">' + val + '</strong> بنجاح!</span>';
                            toast.style.background = 'linear-gradient(135deg,#065f46 0%,#059669 50%,#10b981 100%)';
                            toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5),0 0 15px rgba(16,185,129,0.4)';
                            toast.style.border = '1.5px solid rgba(255,255,255,0.4)';
                        }
                        
                        requestAnimationFrame(function() {
                            toast.style.opacity = '1';
                            toast.style.transform = 'translateX(-50%) translateY(0)';
                        });

                        if (parentWin.__ecp_toast_timer) {
                            clearTimeout(parentWin.__ecp_toast_timer);
                        }
                        parentWin.__ecp_toast_timer = setTimeout(function() {
                            toast.style.opacity = '0';
                            toast.style.transform = 'translateX(-50%) translateY(20px)';
                        }, 2200);
                    }

                    function extractNumericVal(el) {
                        if (!el) return null;
                        var v = el.getAttribute('data-copy-val');
                        if (v && /^[0-9.]+$/.test(v.trim())) return v.trim();
                        var t = el.getAttribute('title') || '';
                        var m = t.match(/([0-9]+\\.[0-9]+|[0-9]+)/);
                        if (m) return m[1];
                        var txt = el.textContent || '';
                        var m2 = txt.match(/([0-9]+\\.[0-9]+|[0-9]+)/);
                        if (m2) return m2[1];
                        return null;
                    }

                    function fallbackCopy(text, callback) {
                        try {
                            var ta = parentDoc.createElement('textarea');
                            ta.value = text;
                            ta.setAttribute('readonly', '');
                            ta.style.position = 'fixed';
                            ta.style.top = '0';
                            ta.style.left = '0';
                            ta.style.width = '1px';
                            ta.style.height = '1px';
                            ta.style.opacity = '0.01';
                            parentDoc.body.appendChild(ta);
                            ta.focus();
                            ta.select();
                            parentDoc.execCommand('copy');
                            parentDoc.body.removeChild(ta);
                        } catch (e) {}
                        if (callback) callback();
                    }

                    function copyPureNumber(val, feedbackEl, isTotalBtn, isBox) {
                        var cleanVal = String(val).trim();
                        showCopyToast(cleanVal);
                        var done = function() {
                            if (!feedbackEl) return;
                            if (isBox) {
                                var oldBorder = feedbackEl.style.borderColor;
                                feedbackEl.style.borderColor = '#10b981';
                                feedbackEl.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.6)';
                                setTimeout(function() { 
                                    feedbackEl.style.borderColor = oldBorder; 
                                    feedbackEl.style.boxShadow = '0 2px 6px rgba(0,0,0,0.3)';
                                }, 2000);
                            } else if (isTotalBtn) {
                                var oldHtml = feedbackEl.innerHTML;
                                feedbackEl.innerHTML = '<span>✓</span> <span>تم النسخ (' + cleanVal + ')</span>';
                                feedbackEl.style.background = 'linear-gradient(135deg, #059669 0%, #10b981 100%)';
                                setTimeout(function() { 
                                    feedbackEl.innerHTML = oldHtml; 
                                    feedbackEl.style.background = 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)';
                                }, 2000);
                            } else {
                                var oldHtml = feedbackEl.innerHTML;
                                feedbackEl.innerHTML = '<span>✓</span> <span>تم النسخ</span>';
                                feedbackEl.style.background = 'linear-gradient(135deg, #059669 0%, #10b981 100%)';
                                setTimeout(function() { 
                                    feedbackEl.innerHTML = oldHtml; 
                                    feedbackEl.style.background = 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)';
                                }, 2000);
                            }
                        };

                        if (parentWin.navigator && parentWin.navigator.clipboard && parentWin.navigator.clipboard.writeText) {
                            parentWin.navigator.clipboard.writeText(cleanVal).then(done).catch(function() {
                                fallbackCopy(cleanVal, done);
                            });
                        } else {
                            fallbackCopy(cleanVal, done);
                        }
                    }

                    if (parentWin.__ecp_mu_copy_handler) {
                        parentDoc.removeEventListener('click', parentWin.__ecp_mu_copy_handler, true);
                    }

                    parentWin.__ecp_mu_copy_handler = function(e) {
                        var target = e.target.closest('button[title*="نسخ القيمة العددية"], div[title*="نسخ القيمة العددية"], .ecp-copy-mu-btn, .ecp-copy-mu-total-btn, .ecp-copy-mu-box');
                        if (!target) return;

                        var val = extractNumericVal(target);
                        if (val === null) return;

                        e.preventDefault();
                        e.stopPropagation();

                        var isBox = target.tagName.toLowerCase() === 'div';
                        var isTotalBtn = !isBox && ((target.textContent || '').indexOf('الإجمالي') !== -1 || target.classList.contains('ecp-copy-mu-total-btn'));
                        copyPureNumber(val, target, isTotalBtn, isBox);
                    };

                    parentDoc.addEventListener('click', parentWin.__ecp_mu_copy_handler, true);

                    // ── Section Title Auto-Select & Quick Copy on Mouse Hover ──
                    if (parentWin.__ecp_title_hover_handler) {
                        parentDoc.removeEventListener('mouseover', parentWin.__ecp_title_hover_handler, true);
                    }
                    if (parentWin.__ecp_title_leave_handler) {
                        parentDoc.removeEventListener('mouseout', parentWin.__ecp_title_leave_handler, true);
                    }
                    if (parentWin.__ecp_title_click_handler) {
                        parentDoc.removeEventListener('click', parentWin.__ecp_title_click_handler, true);
                    }

                    parentWin.__ecp_title_hover_handler = function(e) {
                        var summaryEl = e.target.closest('div[data-testid="stExpander"] summary');
                        if (!summaryEl) return;

                        var targetNode = summaryEl.querySelector('[data-testid="stMarkdownContainer"] p') || 
                                         summaryEl.querySelector('[data-testid="stMarkdownContainer"] span') ||
                                         summaryEl.querySelector('[data-testid="stMarkdownContainer"]');
                        if (!targetNode) return;

                        var txt = (targetNode.textContent || '').trim();
                        // Target sections including Concrete Modulus of Elasticity, CSI SAFE, Moment Capacity, etc.
                        if (txt.indexOf('Concrete Modulus') !== -1 || txt.indexOf('Elasticity') !== -1 || txt.indexOf('CSI SAFE') !== -1 || txt.indexOf('Moment Capacity') !== -1 || txt.indexOf('إضافة سريعة') !== -1) {
                            try {
                                var range = parentDoc.createRange();
                                range.selectNodeContents(targetNode);
                                var sel = parentWin.getSelection();
                                sel.removeAllRanges();
                                sel.addRange(range);
                            } catch(err) {}
                        }
                    };

                    parentWin.__ecp_title_leave_handler = function(e) {
                        var summaryEl = e.target.closest('div[data-testid="stExpander"] summary');
                        if (!summaryEl) return;

                        var related = e.relatedTarget;
                        if (related && summaryEl.contains(related)) {
                            return; // still moving within summary bounds
                        }

                        // Remove text selection immediately when cursor leaves title area
                        try {
                            var sel = parentWin.getSelection();
                            if (sel) {
                                sel.removeAllRanges();
                            }
                        } catch(err) {}
                    if (parentWin.__ecp_title_click_handler) {
                        parentDoc.removeEventListener('click', parentWin.__ecp_title_click_handler, true);
                        parentWin.__ecp_title_click_handler = null;
                    }

                    parentDoc.addEventListener('mouseover', parentWin.__ecp_title_hover_handler, true);
                    parentDoc.addEventListener('mouseout', parentWin.__ecp_title_leave_handler, true);
                })();
                </script>
                """,
                height=0,
                width=0,
            )

        # ────────────────────────────────────────────────────────────────────
        # Concrete Modulus of Elasticity Ec & Specific Compressive Strength F'c
        # ────────────────────────────────────────────────────────────────────
        with st.expander("🧪 Concrete Modulus of Elasticity (Ec) & Specific Compressive Strength (f'c) — خواص الخرسانة ومعاير المرونة", expanded=True):
            st.markdown(
                """
                <div dir="rtl" style="font-size: 14.5px; font-weight: 500; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; line-height: 1.8; text-align: right; margin-bottom: 16px; padding: 12px 16px; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border-right: 4px solid #38bdf8;">
                    <div style="font-weight: 700; font-size: 15px; color: #38bdf8; margin-bottom: 6px;">
                        📌 القوانين والمعادلات الهندسية المعتمدة (ECP 203 & ACI 318 / AISC):
                    </div>
                    <div style="font-size: 13.5px; color: #e2e8f0; line-height: 1.9;">
                        • <strong>الكود المصري (ECP 203):</strong> رتبة المكعب القياسي 15×15×15 سم <span style="color:#38bdf8; font-weight:700;">f<sub>cu</sub> (MPa) = f<sub>cu</sub> (kg/cm²) / 10</span> &nbsp;|&nbsp; معاير المرونة: <span style="color:#38bdf8; font-weight:700;">E<sub>c</sub> = 4400 √f<sub>cu</sub> (MPa) = 4400 √f<sub>cu</sub> × 100 (t/m²)</span><br>
                        • <strong>الكود الأمريكي (ACI 318 / AISC):</strong> مقاومة الأسطوانة القياسية 15×30 سم <span style="color:#38bdf8; font-weight:700;">f'<sub>c</sub> = 0.80 × f<sub>cu</sub> (MPa)</span> &nbsp;|&nbsp; معاير المرونة: <span style="color:#38bdf8; font-weight:700;">E<sub>c</sub> = 4700 √f'<sub>c</sub> (MPa) = 4700 √f'<sub>c</sub> × 100 (t/m²)</span><br>
                        • <strong>علاقة التحويل المباشرة:</strong> <span style="color:#fbbf24; font-weight:700;">1 MPa = 1 N/mm² = 10 kg/cm² = 100 t/m²</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Scoped styling for common grades selectbox and vertical spacing
            st.markdown(
                """
                <style>
                .ec-grade-box-wrap {
                    margin-bottom: 22px !important;
                }
                .ec-grade-box-wrap label,
                .ec-grade-box-wrap label p {
                    font-size: 16.5px !important;
                    font-weight: 800 !important;
                    color: #38bdf8 !important;
                    margin-bottom: 8px !important;
                }
                .ec-grade-box-wrap div[data-baseweb="select"] {
                    border-radius: 8px !important;
                }
                .ec-grade-box-wrap div[data-baseweb="select"] > div {
                    background: #0f172a !important;
                    border: 2px solid #0284c7 !important;
                    min-height: 48px !important;
                    height: 48px !important;
                }
                .ec-grade-box-wrap div[data-baseweb="select"] span,
                .ec-grade-box-wrap div[data-baseweb="select"] div {
                    font-size: 18px !important;
                    font-weight: 900 !important;
                    color: #ffffff !important;
                }
                div[data-baseweb="popover"] li,
                div[data-baseweb="popover"] li span,
                div[data-baseweb="menu"] li {
                    font-size: 16px !important;
                    font-weight: 800 !important;
                }
                </style>
                <div class="ec-grade-box-wrap">
                """,
                unsafe_allow_html=True,
            )

            is_custom_mode = (
                "ec_grade_preset_select" in st.session_state
                and st.session_state["ec_grade_preset_select"].startswith("إدخال يدوي")
            )

            if is_custom_mode:
                col_ec_opt, col_ec_val = st.columns([1.5, 1])
                with col_ec_opt:
                    preset_sel = st.selectbox(
                        "🏷️ رتب الخرسانة الشائعة في السوق المصري (Common Grades)",
                        options=[
                            "250 kg/cm² (25 MPa)",
                            "200 kg/cm² (20 MPa)",
                            "225 kg/cm² (22.5 MPa)",
                            "275 kg/cm² (27.5 MPa)",
                            "300 kg/cm² (30 MPa)",
                            "350 kg/cm² (35 MPa)",
                            "400 kg/cm² (40 MPa)",
                            "إدخال يدوي مخصص (Custom Value)",
                        ],
                        index=7,
                        key="ec_grade_preset_select",
                        help="اختر رتبة خرسانة قياسية أو اختر مخصص لإدخال أي قيمة",
                    )
                with col_ec_val:
                    fcu_input_val = st.number_input(
                        "⚡ مقاومة المكعب المخصصة fcu (kg/cm²)",
                        min_value=50.0,
                        max_value=1500.0,
                        value=250.0,
                        step=10.0,
                        key="ec_fcu_custom_input",
                        help="أدخل قيمة fcu بالمكعب القياسي (kg/cm²)",
                    )
            else:
                col_ec_opt, _ = st.columns([1.6, 1])
                with col_ec_opt:
                    preset_sel = st.selectbox(
                        "🏷️ رتب الخرسانة الشائعة في السوق المصري (Common Grades)",
                        options=[
                            "250 kg/cm² (25 MPa)",
                            "200 kg/cm² (20 MPa)",
                            "225 kg/cm² (22.5 MPa)",
                            "275 kg/cm² (27.5 MPa)",
                            "300 kg/cm² (30 MPa)",
                            "350 kg/cm² (35 MPa)",
                            "400 kg/cm² (40 MPa)",
                            "إدخال يدوي مخصص (Custom Value)",
                        ],
                        index=0,
                        key="ec_grade_preset_select",
                        help="اختر رتبة خرسانة قياسية أو اختر مخصص لإدخال أي قيمة",
                    )
                if preset_sel.startswith("إدخال يدوي"):
                    fcu_input_val = 250.0
                else:
                    fcu_input_val = float(preset_sel.split()[0])

            st.markdown('</div><div style="margin-bottom: 20px;"></div>', unsafe_allow_html=True)

            # Perform calculations
            prop = calculate_concrete_properties(fcu_input_val)

            # 3 Metric Cards (Panel 1: fcu display only kg/cm2, Panel 2: Ec ECP, Panel 3: f'c ACI)
            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                                border: 1.5px solid #64748b; border-radius: 10px; padding: 14px 16px; 
                                box-shadow: 0 4px 12px rgba(0,0,0,0.3); height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                                <span style="font-size: 18.5px; font-weight: 900; color: #94a3b8;">مقاومة المكعب f<sub>cu</sub></span>
                                <span style="font-size: 11.5px; background: rgba(148,163,184,0.18); color: #94a3b8; border: 1px solid rgba(148,163,184,0.35); border-radius: 4px; padding: 2px 7px; font-weight: 700;">ECP 203</span>
                            </div>
                            <div style="font-size: 11.5px; color: #64748b; margin-bottom: 12px; font-weight: 600;">
                                Characteristic Cube Strength (15cm)
                            </div>
                            <div style="background: rgba(15, 23, 42, 0.7); border: 1.5px solid #475569; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: baseline;">
                                <span style="font-size: 26px; font-weight: 900; color: #ffffff; text-shadow: 0 0 10px rgba(255,255,255,0.3);">{round(prop['fcu_kg_cm2']):d}</span>
                                <span style="font-size: 14px; font-weight: 800; color: #cbd5e1;">kg/cm²</span>
                            </div>
                            <div style="background: rgba(15, 23, 42, 0.4); border: 1px dashed rgba(100, 116, 139, 0.4); border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: baseline;">
                                <span style="font-size: 15px; font-weight: 800; color: #94a3b8;">{round(prop['fcu_ton_m2']):,d} t/m²</span>
                                <span style="font-size: 12.5px; font-weight: 700; color: #64748b;">({round(prop['fcu_mpa']):d} MPa)</span>
                            </div>
                        </div>
                        <div style="text-align: center; padding: 8px 0 2px 0; font-size: 12px; font-weight: 700; color: #64748b; border-top: 1px dashed rgba(100,116,139,0.3);">
                            🔒 بطاقة مرجعية للعرض المباشر (Display Only)
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c2:
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                                border: 1.5px solid #38bdf8; border-radius: 10px; padding: 14px 16px; 
                                box-shadow: 0 4px 12px rgba(0,0,0,0.3); height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                                <span style="font-size: 18.5px; font-weight: 900; color: #38bdf8; text-shadow: 0 0 12px rgba(56, 189, 248, 0.4);">معاير المرونة E<sub>c</sub></span>
                                <span style="font-size: 11.5px; background: rgba(56,189,248,0.18); color: #7dd3fc; border: 1px solid rgba(56,189,248,0.35); border-radius: 4px; padding: 2px 7px; font-weight: 700;">الكود المصري ECP</span>
                            </div>
                            <div style="font-size: 11.5px; color: #94a3b8; margin-bottom: 12px; font-weight: 600;">
                                E<sub>c</sub> = 4400 √f<sub>cu</sub> (MPa)
                            </div>
                            <!-- Metric Unit (t/m²): COPYABLE -->
                            <div class="ecp-copy-mu-box" data-copy-val="{round(prop['ec_ecp_ton_m2']):d}" title="انقر لنسخ القيمة ({round(prop['ec_ecp_ton_m2']):,d} t/m²)"
                                 style="background: rgba(15, 23, 42, 0.7); border: 1.5px solid #0284c7; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; cursor: pointer; display: flex; justify-content: space-between; align-items: baseline; transition: all 0.2s ease;">
                                <span style="font-size: 22px; font-weight: 900; color: #ffffff;">{round(prop['ec_ecp_ton_m2']):,d}</span>
                                <span style="font-size: 14px; font-weight: 800; color: #38bdf8;">t/m²</span>
                            </div>
                            <!-- Non-Metric Unit (MPa): DISPLAY ONLY, NOT COPYABLE -->
                            <div style="background: rgba(15, 23, 42, 0.4); border: 1px dashed rgba(56, 189, 248, 0.4); border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: baseline; user-select: text; cursor: default;">
                                <span style="font-size: 15px; font-weight: 800; color: #cbd5e1;">{round(prop['ec_ecp_mpa']):,d}</span>
                                <span style="font-size: 12.5px; font-weight: 700; color: #94a3b8;">MPa</span>
                            </div>
                        </div>
                        <!-- Button only copies metric t/m² -->
                        <button class="ecp-copy-mu-btn" data-copy-val="{round(prop['ec_ecp_ton_m2']):d}" title="نسخ القيمة بوحدة t/m² ({round(prop['ec_ecp_ton_m2']):d})"
                                style="width: 100%; background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); border: 1px solid #38bdf8; border-radius: 6px; color: #ffffff; cursor: pointer; padding: 7px 10px; font-size: 12px; font-weight: 800; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35);">
                            <span>📋</span> <span>نسخ Ec مصري ({round(prop['ec_ecp_ton_m2']):,d} t/m²)</span>
                        </button>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c3:
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                                border: 1.5px solid #38bdf8; border-radius: 10px; padding: 14px 16px; 
                                box-shadow: 0 4px 12px rgba(0,0,0,0.3); height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                                <span style="font-size: 18.5px; font-weight: 900; color: #38bdf8; text-shadow: 0 0 12px rgba(56, 189, 248, 0.4);">مقاومة الأسطوانة f'<sub>c</sub></span>
                                <span style="font-size: 11.5px; background: rgba(56,189,248,0.18); color: #7dd3fc; border: 1px solid rgba(56,189,248,0.35); border-radius: 4px; padding: 2px 7px; font-weight: 700;">ACI / AISC</span>
                            </div>
                            <div style="font-size: 11.5px; color: #94a3b8; margin-bottom: 12px; font-weight: 600;">
                                Specified Cylinder Strength (0.80 f<sub>cu</sub>)
                            </div>
                            <!-- Metric Unit (t/m²): COPYABLE -->
                            <div class="ecp-copy-mu-box" data-copy-val="{round(prop['fc_prime_ton_m2']):d}" title="انقر لنسخ القيمة ({round(prop['fc_prime_ton_m2']):,d} t/m²)"
                                 style="background: rgba(15, 23, 42, 0.7); border: 1.5px solid #0284c7; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; cursor: pointer; display: flex; justify-content: space-between; align-items: baseline; transition: all 0.2s ease;">
                                <span style="font-size: 22px; font-weight: 900; color: #ffffff;">{round(prop['fc_prime_ton_m2']):,d}</span>
                                <span style="font-size: 14px; font-weight: 800; color: #38bdf8;">t/m²</span>
                            </div>
                            <!-- Non-Metric Unit (MPa): DISPLAY ONLY, NOT COPYABLE -->
                            <div style="background: rgba(15, 23, 42, 0.4); border: 1px dashed rgba(56, 189, 248, 0.4); border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: baseline; user-select: text; cursor: default;">
                                <span style="font-size: 15px; font-weight: 800; color: #cbd5e1;">{round(prop['fc_prime_mpa']):d}</span>
                                <span style="font-size: 12.5px; font-weight: 700; color: #94a3b8;">MPa ({round(prop['fc_prime_kg_cm2']):d} kg/cm²)</span>
                            </div>
                        </div>
                        <!-- Button only copies metric t/m² -->
                        <button class="ecp-copy-mu-btn" data-copy-val="{round(prop['fc_prime_ton_m2']):d}" title="نسخ القيمة بوحدة t/m² ({round(prop['fc_prime_ton_m2']):d})"
                                style="width: 100%; background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); border: 1px solid #38bdf8; border-radius: 6px; color: #ffffff; cursor: pointer; padding: 7px 10px; font-size: 12px; font-weight: 800; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35);">
                            <span>📋</span> <span>نسخ f'c أمريكي ({round(prop['fc_prime_ton_m2']):,d} t/m²)</span>
                        </button>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ────────────────────────────────────────────────────────────────────────
    # TAB 2 — Steel bars
    # ────────────────────────────────────────────────────────────────────────
    with tab_steel:
        with st.expander("📋 جدول أقطار حديد التسليح وأوزانها (Rebar Properties Table)", expanded=False):
            rows = []
            for b in BARS:
                d       = b["dia_mm"]
                w       = b["weight_kgm"]
                a       = b["area_cm2"]
                per     = f"{w:.3f}"
                w12     = w * 12
                bars_ton_12m = 1000.0 / w12 if w12 > 0 else 0
                rows.append({
                    "القطر Ø (mm)":              d,
                    "المساحة المستعرضة (cm²)":   f"{a:.3f}",
                    "الوزن / متر طولي (kg/m)":  per,
                    "الوزن / 12م (kg/bar)":      f"{w12:.2f}",
                    "الوزن / 6م  (kg/bar)":      f"{w * 6:.2f}",
                    "عدد الأسياخ في الطن (12م)":  f"{round(bars_ton_12m):d} سيخ ({bars_ton_12m:.1f})",
                    "القطر بالسم (cm)":           f"{d / 10:.1f}",
                })

            df = pd.DataFrame(rows)
            render_styled_table(df)

            st.markdown(
                """
                <div dir="rtl" style="font-size: 15.5px; font-weight: 500; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; line-height: 1.8; text-align: right; margin-top: 12px; margin-bottom: 8px;">
                    الكثافة المستخدمة: <span style="color:#38bdf8; font-weight:700;">7,850 kg/m³</span> &nbsp;|&nbsp; 
                    المساحة = <span style="color:#38bdf8; font-weight:700;">π × d² / 4</span> &nbsp;|&nbsp; 
                    الوزن = <span style="color:#38bdf8; font-weight:700;">المساحة (m²) × الكثافة</span> &nbsp;|&nbsp; 
                    عدد الأسياخ في الطن (طول 12م) = <span style="color:#38bdf8; font-weight:700;">1000 كجم / وزن السيخ 12م</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Grade info
        with st.expander("📌 Steel Grades & Yield Strengths (درجات الحديد وحدود الخضوع)", expanded=False):
            g_rows = [
                {"الدرجة / Grade": g, "حد الخضوع Fy (kg/cm²)": fy}
                for g, fy in GRADES.items()
            ]
            render_styled_table(g_rows)

        # Areas per metre for multiple bars
        with st.expander("📐 As (n bars/m) Table (مساحة n بار / متر طولي)", expanded=False):
            counts = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]
            area_rows = []
            for b in BARS:
                row = {"Ø (mm)": f"Ø {b['dia_mm']}"}
                for n in counts:
                    row[f"{n} bars (cm²/m)"] = f"{b['area_cm2'] * n:.3f}"
                area_rows.append(row)
            render_styled_table(area_rows)

        with st.expander("📥 جدول بنود ومدخلات حديد التسليح المتعددة (Multi-Diameter Rebar Input Schedule)", expanded=False):
            st.markdown(
                """
                <div style="font-size: 17.5px; font-weight: 600; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; margin: 8px 0 28px 0; line-height: 1.6; text-align: right;">
                    أضف بنود حديد التسليح بأقطار وأعداد وأطوال مختلفة لحساب الأوزان والمساحات لكل بند والإجمالي العام.
                </div>
                """,
                unsafe_allow_html=True,
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
                <div style="background:linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border:1px solid rgba(56, 189, 248, 0.35); border-radius:8px; padding:10px 14px; margin-top:14px; margin-bottom:20px;">
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

    # ────────────────────────────────────────────────────────────────────────
    # TAB 3 — Slab On Grade / Mat Steel Weight
    # ────────────────────────────────────────────────────────────────────────
    with tab_slab_weight:
        # Scoped CSS to reduce vertical heights and gaps across inputs and panels
        st.markdown(
            """
            <style>
            div[data-testid="stVerticalBlock"]:has(.slab-weight-scope) {
                gap: 0.30rem !important;
            }
            div[data-testid="stVerticalBlock"]:has(.slab-weight-scope) .stSelectbox div[data-baseweb="select"] > div {
                min-height: 35px !important;
                height: 35px !important;
            }
            div[data-testid="stVerticalBlock"]:has(.slab-weight-scope) .stNumberInput div[data-baseweb="input"] {
                min-height: 35px !important;
                height: 35px !important;
            }
            .slab-row-label {
                display: flex;
                align-items: center;
                height: 35px;
                font-size: 13px;
                font-weight: 700;
            }
            </style>
            <div class="slab-weight-scope" style="display:flex; align-items:center; justify-content:space-between; margin-top:2px; margin-bottom:8px; padding:7px 12px; background:rgba(30,41,59,0.55); border-radius:8px; border-right:4px solid #38bdf8;">
                <span style="font-size:15px; font-weight:700; color:#38bdf8;">
                    📋 مدخلات شبكات التسليح وقطاع البلاطة (Slab Reinforcement & Geometry Inputs)
                </span>
                <span style="font-size:12px; color:#94a3b8;">Slab On Grade / Mat</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        def get_unit_weight(diameter_mm: float) -> float:
            return (diameter_mm ** 2) / 162.0

        diameters_options = MOMENT_DIAMETERS  # [8, 10, 12, 16, 18, 20, 22, 25, 28, 32] without 14 mm

        # ----------------- 1. بار معاملات القطاع والهالك -----------------
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            slab_thickness = st.number_input(
                "📏 سمك البلاطة الخرسانية - Slab Thickness (ts) [متر]",
                min_value=0.08,
                max_value=3.00,
                value=0.15,
                step=0.01,
                format="%.2f",
                key="slab_thickness_m",
                help="السمك الإجمالي للبلاطة الخرسانية بالمتر (مثلاً 0.15م للبلاطات الأرضية Slab On Grade، أو أكبر للبشة Mat)",
            )
        with p_col2:
            waste_lap_pct = st.number_input(
                "✂️ نسبة التداخل والهالك - Lap & Waste [%]",
                min_value=0.0,
                max_value=30.0,
                value=8.0,
                step=0.5,
                format="%.1f",
                key="waste_lap_pct",
                help="النسبة المناسبة طبقاً للكود والممارسات الهندسية: 8% (5% وصلات تراكب Lap Splices للأسياخ 12م + 3% هالك تشكيل وقص Cutting Waste)",
            )

        waste_factor = 1.0 + (waste_lap_pct / 100.0)

        # خط سميك وبلون واضح وفاتح بين مدخل سمك البلاطة ومدخلات طبقات التسليح
        st.markdown(
            """
            <div style="height: 3.5px; background: linear-gradient(90deg, #38bdf8 0%, #67e8f9 50%, #38bdf8 100%); margin: 12px 0 12px 0; border-radius: 3px; box-shadow: 0 0 10px rgba(56, 189, 248, 0.75);"></div>
            """,
            unsafe_allow_html=True,
        )

        # مدخل قائمة منسدلة لاختيار نظام شبكة التسليح
        c_mesh_sel, _ = st.columns([2.6, 3.4])
        with c_mesh_sel:
            mesh_type = st.selectbox(
                "🕸️ نظام شبكة التسليح (Mesh Configuration):",
                options=[
                    "طبقتين تسليح سفلية وعلوية",
                    "طبقة تسليح واحدة",
                ],
                index=0,
                key="slab_mesh_type",
                help="اختر 'طبقة تسليح واحدة' لإظهار الشبكة السفلية فقط، أو 'طبقتين تسليح سفلية وعلوية' لإظهار الشبكتين العلوية والسفلية",
            )

        is_double_mesh = (mesh_type == "طبقتين تسليح سفلية وعلوية")

        # Helper to render layer output panels matching Tab 2 (Moment against Steel)
        def _render_layer_box(val: float, unit: str, border_color: str, text_color: str, title_tip: str) -> str:
            return f"""
            <div class="ecp-copy-mu-box" data-copy-val="{val:.2f}"
                 title="{title_tip} ({val:.2f} {unit})"
                 style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                        border: 1.5px solid {border_color}; border-radius: 6px; height: 35px; box-sizing: border-box;
                        display: flex; justify-content: center; align-items: center; gap: 6px; direction: ltr;
                        box-shadow: 0 2px 6px rgba(0,0,0,0.3); white-space: nowrap; padding: 0 6px; cursor: pointer; transition: all 0.2s ease;">
                <span style="font-size: 15px; font-weight: 900; color: #ffffff; user-select: all; -webkit-user-select: all;">{val:.2f}</span>
                <span style="font-size: 11px; font-weight: 700; color: {text_color}; user-select: none; pointer-events: none;">{unit}</span>
            </div>
            """

        # ----------------- 2. جدول المدخلات وبانيلات المخرجات -----------------
        # Column headers (5 columns) with increased bottom spacing
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1.9, 0.9, 0.9, 1.15, 1.15])
        h_col1.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; padding-bottom:12px; margin-bottom:6px;'>الطبقة والاتجاه (Layer / Dir)</div>", unsafe_allow_html=True)
        h_col2.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; padding-bottom:12px; margin-bottom:6px;'>القطر (Φ mm)</div>", unsafe_allow_html=True)
        h_col3.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; padding-bottom:12px; margin-bottom:6px;'>العدد / م (Bars/m)</div>", unsafe_allow_html=True)
        h_col4.markdown("<div style='font-size:13px; font-weight:700; color:#38bdf8; text-align:center; padding-bottom:12px; margin-bottom:6px;'>وزن المتر المسطح (kg/m²)</div>", unsafe_allow_html=True)
        h_col5.markdown("<div style='font-size:13px; font-weight:700; color:#34d399; text-align:center; padding-bottom:12px; margin-bottom:6px;'>وزن المتر المكعب (kg/m³)</div>", unsafe_allow_html=True)

        total_weight_net = 0.0
        total_weight_gross = 0.0

        # تظهر الشبكة العلوية فقط في حالة اختيار "طبقتين تسليح سفلية وعلوية"
        if is_double_mesh:
            # 1. الشبكة العلوية - اتجاه قصير (Top Short X)
            r1_col1, r1_col2, r1_col3, r1_col4, r1_col5 = st.columns([1.9, 0.9, 0.9, 1.15, 1.15])
            r1_col1.markdown("<div class='slab-row-label' style='color: #38bdf8;'>🔹 علوي قصير (Top Short - X)</div>", unsafe_allow_html=True)
            dia_top_x = r1_col2.selectbox("قطر Top X", diameters_options, index=diameters_options.index(10) if 10 in diameters_options else 1, key="dia_top_x", label_visibility="collapsed")
            n_top_x = r1_col3.number_input("عدد Top X", min_value=1.0, max_value=50.0, value=7.0, step=0.5, key="n_top_x", label_visibility="collapsed")
            w_meter_top_x = get_unit_weight(dia_top_x)
            w_m2_net_top_x = n_top_x * w_meter_top_x
            w_m2_top_x = w_m2_net_top_x * waste_factor
            w_m3_top_x = w_m2_top_x / slab_thickness if slab_thickness > 0 else 0.0
            total_weight_net += w_m2_net_top_x
            total_weight_gross += w_m2_top_x
            r1_col4.markdown(_render_layer_box(w_m2_top_x, "kg/m²", "#38bdf8", "#38bdf8", "انقر لنسخ وزن المتر المسطح"), unsafe_allow_html=True)
            r1_col5.markdown(_render_layer_box(w_m3_top_x, "kg/m³", "#10b981", "#34d399", "انقر لنسخ وزن المتر المكعب"), unsafe_allow_html=True)

            # 2. الشبكة العلوية - اتجاه طويل (Top Long Y)
            r2_col1, r2_col2, r2_col3, r2_col4, r2_col5 = st.columns([1.9, 0.9, 0.9, 1.15, 1.15])
            r2_col1.markdown("<div class='slab-row-label' style='color: #38bdf8;'>🔹 علوي طويل (Top Long - Y)</div>", unsafe_allow_html=True)
            dia_top_y = r2_col2.selectbox("قطر Top Y", diameters_options, index=diameters_options.index(10) if 10 in diameters_options else 1, key="dia_top_y", label_visibility="collapsed")
            n_top_y = r2_col3.number_input("عدد Top Y", min_value=1.0, max_value=50.0, value=7.0, step=0.5, key="n_top_y", label_visibility="collapsed")
            w_meter_top_y = get_unit_weight(dia_top_y)
            w_m2_net_top_y = n_top_y * w_meter_top_y
            w_m2_top_y = w_m2_net_top_y * waste_factor
            w_m3_top_y = w_m2_top_y / slab_thickness if slab_thickness > 0 else 0.0
            total_weight_net += w_m2_net_top_y
            total_weight_gross += w_m2_top_y
            r2_col4.markdown(_render_layer_box(w_m2_top_y, "kg/m²", "#38bdf8", "#38bdf8", "انقر لنسخ وزن المتر المسطح"), unsafe_allow_html=True)
            r2_col5.markdown(_render_layer_box(w_m3_top_y, "kg/m³", "#10b981", "#34d399", "انقر لنسخ وزن المتر المكعب"), unsafe_allow_html=True)

        # 3. الشبكة السفلية - اتجاه قصير (Bottom Short X)
        r3_col1, r3_col2, r3_col3, r3_col4, r3_col5 = st.columns([1.9, 0.9, 0.9, 1.15, 1.15])
        r3_col1.markdown("<div class='slab-row-label' style='color: #fbbf24;'>🔸 سفلي قصير (Bottom Short - X)</div>", unsafe_allow_html=True)
        dia_bot_x = r3_col2.selectbox("قطر Bot X", diameters_options, index=diameters_options.index(12) if 12 in diameters_options else 2, key="dia_bot_x", label_visibility="collapsed")
        n_bot_x = r3_col3.number_input("عدد Bot X", min_value=1.0, max_value=50.0, value=7.0, step=0.5, key="n_bot_x", label_visibility="collapsed")
        w_meter_bot_x = get_unit_weight(dia_bot_x)
        w_m2_net_bot_x = n_bot_x * w_meter_bot_x
        w_m2_bot_x = w_m2_net_bot_x * waste_factor
        w_m3_bot_x = w_m2_bot_x / slab_thickness if slab_thickness > 0 else 0.0
        total_weight_net += w_m2_net_bot_x
        total_weight_gross += w_m2_bot_x
        r3_col4.markdown(_render_layer_box(w_m2_bot_x, "kg/m²", "#38bdf8", "#38bdf8", "انقر لنسخ وزن المتر المسطح"), unsafe_allow_html=True)
        r3_col5.markdown(_render_layer_box(w_m3_bot_x, "kg/m³", "#10b981", "#34d399", "انقر لنسخ وزن المتر المكعب"), unsafe_allow_html=True)

        # 4. الشبكة السفلية - اتجاه طويل (Bottom Long Y)
        r4_col1, r4_col2, r4_col3, r4_col4, r4_col5 = st.columns([1.9, 0.9, 0.9, 1.15, 1.15])
        r4_col1.markdown("<div class='slab-row-label' style='color: #fbbf24;'>🔸 سفلي طويل (Bottom Long - Y)</div>", unsafe_allow_html=True)
        dia_bot_y = r4_col2.selectbox("قطر Bot Y", diameters_options, index=diameters_options.index(12) if 12 in diameters_options else 2, key="dia_bot_y", label_visibility="collapsed")
        n_bot_y = r4_col3.number_input("عدد Bot Y", min_value=1.0, max_value=50.0, value=7.0, step=0.5, key="n_bot_y", label_visibility="collapsed")
        w_meter_bot_y = get_unit_weight(dia_bot_y)
        w_m2_net_bot_y = n_bot_y * w_meter_bot_y
        w_m2_bot_y = w_m2_net_bot_y * waste_factor
        w_m3_bot_y = w_m2_bot_y / slab_thickness if slab_thickness > 0 else 0.0
        total_weight_net += w_m2_net_bot_y
        total_weight_gross += w_m2_bot_y
        r4_col4.markdown(_render_layer_box(w_m2_bot_y, "kg/m²", "#38bdf8", "#38bdf8", "انقر لنسخ وزن المتر المسطح"), unsafe_allow_html=True)
        r4_col5.markdown(_render_layer_box(w_m3_bot_y, "kg/m³", "#10b981", "#34d399", "انقر لنسخ وزن المتر المكعب"), unsafe_allow_html=True)

        # Calculate totals
        total_weight_m3_gross = total_weight_gross / slab_thickness if slab_thickness > 0 else 0.0

        # ----------------- 3. صف البانيلات الإجمالية أسفل الأعمدة -----------------
        tot_col1, tot_col2, tot_col3 = st.columns([3.7, 1.15, 1.15])
        tot_title = "الإجمالي العام لجميع الطبقات (Total All Layers)" if is_double_mesh else "إجمالي شبكة التسليح السفلية (Total Bottom Mesh)"
        with tot_col1:
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; justify-content: space-between; height: 42px; background: linear-gradient(135deg, rgba(15,23,42,0.85) 0%, rgba(30,41,59,0.85) 100%); border: 1.5px solid #475569; border-radius: 6px; padding: 0 12px; box-sizing: border-box;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 18px;">🏆</span>
                        <span style="font-weight: 800; font-size: 14px; color: #38bdf8;">{tot_title}</span>
                    </div>
                    <span style="font-size: 13.5px; font-weight: 800; color: #fbbf24; background: rgba(245, 158, 11, 0.18); border: 1.5px solid #f59e0b; padding: 3px 10px; border-radius: 6px; white-space: nowrap;">
                        شامل الهالك والتداخل ({waste_lap_pct:.1f}%)
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with tot_col2:
            st.markdown(
                f"""
                <div class="ecp-copy-mu-box" data-copy-val="{total_weight_gross:.2f}"
                     title="انقر لنسخ إجمالي وزن المتر المسطح ({total_weight_gross:.2f} kg/m²)"
                     style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                            border: 2px solid #38bdf8; border-radius: 6px; height: 42px; box-sizing: border-box;
                            display: flex; justify-content: center; align-items: center; gap: 6px; direction: ltr;
                            box-shadow: 0 2px 8px rgba(56, 189, 248, 0.35); white-space: nowrap; padding: 0 6px; cursor: pointer; transition: all 0.2s ease;">
                    <span style="font-size: 16px; font-weight: 900; color: #ffffff; user-select: all; -webkit-user-select: all;">{total_weight_gross:.2f}</span>
                    <span style="font-size: 11.5px; font-weight: 800; color: #38bdf8; user-select: none; pointer-events: none;">kg/m²</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with tot_col3:
            st.markdown(
                f"""
                <div class="ecp-copy-mu-box" data-copy-val="{total_weight_m3_gross:.2f}"
                     title="انقر لنسخ إجمالي معدل المتر المكعب ({total_weight_m3_gross:.2f} kg/m³)"
                     style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                            border: 2px solid #10b981; border-radius: 6px; height: 42px; box-sizing: border-box;
                            display: flex; justify-content: center; align-items: center; gap: 6px; direction: ltr;
                            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.35); white-space: nowrap; padding: 0 6px; cursor: pointer; transition: all 0.2s ease;">
                    <span style="font-size: 16px; font-weight: 900; color: #ffffff; user-select: all; -webkit-user-select: all;">{total_weight_m3_gross:.2f}</span>
                    <span style="font-size: 11.5px; font-weight: 800; color: #34d399; user-select: none; pointer-events: none;">kg/m³</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Toast listener support for Tab 3 copying
        components.html(
            """
            <script>
            (function() {
                var parentDoc = (window.parent && window.parent.document) ? window.parent.document : document;
                var parentWin = (window.parent) ? window.parent : window;

                function showCopyToast(val) {
                    var toast = parentDoc.getElementById('ecp-mu-copy-toast');
                    if (!toast) {
                        toast = parentDoc.createElement('div');
                        toast.id = 'ecp-mu-copy-toast';
                        toast.style.cssText = 'position:fixed;bottom:35px;left:50%;transform:translateX(-50%) translateY(20px);background:linear-gradient(135deg,#065f46 0%,#059669 50%,#10b981 100%);color:#ffffff;padding:10px 24px;border-radius:24px;font-size:14.5px;font-weight:800;font-family:system-ui,-apple-system,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,0.5),0 0 15px rgba(16,185,129,0.4);z-index:9999999;display:flex;align-items:center;gap:10px;direction:rtl;pointer-events:none;transition:opacity 0.25s cubic-bezier(0.4,0,0.2,1),transform 0.25s cubic-bezier(0.4,0,0.2,1);opacity:0;border:1.5px solid rgba(255,255,255,0.4);';
                        parentDoc.body.appendChild(toast);
                    }
                    toast.innerHTML = '<span style="font-size:18px;">✓</span> <span>تم نسخ القيمة: <strong style="color:#ffffff;text-decoration:underline;">' + val + '</strong> بنجاح!</span>';
                    
                    requestAnimationFrame(function() {
                        toast.style.opacity = '1';
                        toast.style.transform = 'translateX(-50%) translateY(0)';
                    });

                    if (parentWin.__ecp_toast_timer) {
                        clearTimeout(parentWin.__ecp_toast_timer);
                    }
                    parentWin.__ecp_toast_timer = setTimeout(function() {
                        toast.style.opacity = '0';
                        toast.style.transform = 'translateX(-50%) translateY(20px)';
                    }, 2000);
                }

                function copyPureNumber(val, feedbackEl) {
                    var cleanVal = String(val).trim();
                    showCopyToast(cleanVal);
                    if (feedbackEl) {
                        var oldBorder = feedbackEl.style.borderColor;
                        feedbackEl.style.borderColor = '#10b981';
                        feedbackEl.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.6)';
                        setTimeout(function() { 
                            feedbackEl.style.borderColor = oldBorder; 
                            feedbackEl.style.boxShadow = '0 2px 6px rgba(0,0,0,0.3)';
                        }, 2000);
                    }
                    if (parentWin.navigator && parentWin.navigator.clipboard && parentWin.navigator.clipboard.writeText) {
                        parentWin.navigator.clipboard.writeText(cleanVal);
                    }
                }

                if (parentWin.__ecp_slab_copy_handler) {
                    parentDoc.removeEventListener('click', parentWin.__ecp_slab_copy_handler, true);
                }

                parentWin.__ecp_slab_copy_handler = function(e) {
                    var target = e.target.closest('.ecp-copy-mu-box');
                    if (!target) return;
                    var val = target.getAttribute('data-copy-val');
                    if (!val) return;
                    e.preventDefault();
                    e.stopPropagation();
                    copyPureNumber(val, target);
                };

                parentDoc.addEventListener('click', parentWin.__ecp_slab_copy_handler, true);
            })();
            </script>
            """,
            height=0,
            width=0,
        )

