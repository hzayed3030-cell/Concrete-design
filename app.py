"""
ECP 203 - Egyptian Code of Practice
Reinforced Concrete Engineering Dashboard
==========================================
Run with:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="ECP 203 - RC Engineering Dashboard",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load / initialise persistent settings BEFORE any styling or module renders ─
from modules.settings import (
    load_settings,
    reset_settings,
    save_settings,
    cfg_val,
    radio as S_radio,
)
load_settings()

from modules.columns   import render as render_columns
from modules.footings  import render as render_footings
from modules.flat_slab import render as render_flat_slab
from modules.steel_bars import render as render_steel_bars
from modules.concrete_survey import render as render_concrete_survey

# ── CSS Injection: Fixed Unified Typography (14px) ───────────────────────────
st.markdown(
    """
    <style>
    :root {
        /* ═══════════════════════════════════════════════════════════════════════
           BALANCED COMFORTABLE TYPOGRAPHY (19px Base for Inputs & Outputs)
           ═══════════════════════════════════════════════════════════════════════ */
        --ecp-modules-base-font-size: 16px;
        --ecp-input-font-size: 19px;
        --ecp-output-font-size: 19px;

        /* Proportional Scales for Module Output Elements */
        --ecp-font-size-title: 25px;
        --ecp-font-size-h1: 25px;
        --ecp-font-size-h2: 22px;
        --ecp-font-size-h3: 20px;
        --ecp-font-size-body: 18px;
        --ecp-font-size-table-hdr: 18px;
        --ecp-font-size-table-cell: 17px;
        --ecp-font-size-small: 16px;
        --ecp-font-size-caption: 14px;
        --ecp-font-size-metric-val: 22px;
        --ecp-font-size-metric-lbl: 15px;
    }

    /* Global Base */
    html, body, [class*="css"] {
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       DASHBOARD SHELL TYPOGRAPHY ISOLATION
       ═══════════════════════════════════════════════════════════════════════════ */
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2340 0%, #0d1726 100%);
    }
    
    /* Sidebar typography */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] small {
        font-size: var(--ecp-modules-base-font-size) !important;
        color: #e0e6f0 !important;
        line-height: 1.4 !important;
    }

    /* Sidebar Headings */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 {
        font-size: calc(var(--ecp-modules-base-font-size) * 1.15) !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }

    /* Sidebar Radio Module Selector */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label,
    [data-testid="stSidebar"] div[data-testid="stRadio"] label * {
        font-size: var(--ecp-modules-base-font-size) !important;
        font-weight: 500 !important;
    }

    /* Sidebar Buttons (Reset buttons) */
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] button * {
        font-size: var(--ecp-modules-base-font-size) !important;
        font-weight: 600 !important;
    }

    /* Topbar / Header Chrome */
    [data-testid="stHeader"],
    [data-testid="stHeader"] * {
        font-size: var(--ecp-modules-base-font-size) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       1. FORM INPUT CONTROLS: LABELS, TITLES, & ENTERED NUMBERS
       ═══════════════════════════════════════════════════════════════════════════ */
    
    /* Input Labels */
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"],
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] *,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] label,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] p,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] span,
    [data-testid="stMainBlockContainer"] .stNumberInput label,
    [data-testid="stMainBlockContainer"] .stNumberInput label *,
    [data-testid="stMainBlockContainer"] .stSelectbox label,
    [data-testid="stMainBlockContainer"] .stSelectbox label *,
    [data-testid="stMainBlockContainer"] .stTextInput label,
    [data-testid="stMainBlockContainer"] .stTextInput label *,
    [data-testid="stMainBlockContainer"] .stTextArea label,
    [data-testid="stMainBlockContainer"] .stTextArea label *,
    [data-testid="stMainBlockContainer"] .stRadio label,
    [data-testid="stMainBlockContainer"] .stRadio label *,
    [data-testid="stMainBlockContainer"] .stCheckbox label,
    [data-testid="stMainBlockContainer"] .stCheckbox label * {
        font-size: var(--ecp-input-font-size) !important;
        font-weight: 600 !important;
        line-height: 1.25 !important;
    }

    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] {
        margin-bottom: 3px !important;
        min-height: 0px !important;
    }
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] p,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] label {
        margin-bottom: 1px !important;
        margin-top: 0px !important;
        line-height: 1.2 !important;
    }

    /* Input Sub-headers & Section Labels inside Input Groups */
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] details > div [data-testid="stMarkdownContainer"] p,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] details > div [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] details > div [data-testid="stMarkdownContainer"] span {
        font-size: calc(var(--ecp-input-font-size) * 1.05) !important;
        font-weight: 700 !important;
        line-height: 1.25 !important;
        margin-top: 4px !important;
        margin-bottom: 3px !important;
    }

    /* Widget Containers Compact Vertical Spacing */
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stNumberInput,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stSelectbox,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stTextInput,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stTextArea {
        margin-bottom: 3px !important;
        margin-top: 0px !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stVerticalBlock"] {
        gap: 0.4rem !important;
    }

    /* Entered Numbers & Values inside Input Fields */
    [data-testid="stMainBlockContainer"] input,
    [data-testid="stMainBlockContainer"] input[type="number"],
    [data-testid="stMainBlockContainer"] input[type="text"],
    [data-testid="stMainBlockContainer"] textarea,
    [data-testid="stMainBlockContainer"] div[data-baseweb="input"] input,
    [data-testid="stMainBlockContainer"] .stNumberInput input,
    [data-testid="stMainBlockContainer"] .stTextInput input,
    [data-testid="stMainBlockContainer"] div[data-baseweb="textarea"] textarea,
    [data-testid="stMainBlockContainer"] .stTextArea textarea {
        font-size: var(--ecp-input-font-size) !important;
        min-height: 38px !important;
        line-height: 1.3 !important;
        padding-top: 4px !important;
        padding-bottom: 4px !important;
    }

    /* Stepper Buttons (+ / -) */
    [data-testid="stMainBlockContainer"] button[data-testid="stNumberInputStepUp"],
    [data-testid="stMainBlockContainer"] button[data-testid="stNumberInputStepDown"] {
        min-height: 18px !important;
        height: 18px !important;
        width: calc(var(--ecp-input-font-size) * 1.6) !important;
    }
    [data-testid="stMainBlockContainer"] button[data-testid="stNumberInputStepUp"] svg,
    [data-testid="stMainBlockContainer"] button[data-testid="stNumberInputStepDown"] svg {
        width: calc(var(--ecp-input-font-size) * 0.70) !important;
        height: calc(var(--ecp-input-font-size) * 0.70) !important;
    }

    /* Dropdown Menus & Select Option Values */
    [data-testid="stMainBlockContainer"] div[data-baseweb="select"],
    [data-testid="stMainBlockContainer"] div[data-baseweb="select"] *,
    [data-testid="stMainBlockContainer"] div[data-baseweb="select"] div,
    [data-testid="stMainBlockContainer"] div[data-baseweb="select"] span,
    [data-testid="stMainBlockContainer"] div[data-baseweb="select"] [aria-selected="true"],
    [data-testid="stMainBlockContainer"] div[data-baseweb="popover"] *,
    li[role="option"],
    li[role="option"] * {
        font-size: var(--ecp-input-font-size) !important;
    }
    [data-testid="stMainBlockContainer"] div[data-baseweb="select"] {
        min-height: 38px !important;
    }

    /* Radios & Checkboxes */
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label *,
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] span,
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] p,
    [data-testid="stMainBlockContainer"] div[data-testid="stCheckbox"] label *,
    [data-testid="stMainBlockContainer"] div[data-testid="stCheckbox"] span,
    [data-testid="stMainBlockContainer"] div[data-testid="stCheckbox"] p {
        font-size: var(--ecp-input-font-size) !important;
    }

    /* Tabs Styling */
    button[data-baseweb="tab"] p,
    button[data-baseweb="tab"] div,
    button[data-baseweb="tab"] span {
        font-size: 18px !important;
        font-weight: 700 !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       2. GENERAL UI, RESULTS, TITLES & TABLES
       ═══════════════════════════════════════════════════════════════════════════ */
    
    /* Section & Output Headers */
    [data-testid="stMainBlockContainer"] .section-header,
    [data-testid="stMainBlockContainer"] .section-header * {
        font-size: var(--ecp-font-size-h3) !important;
        font-weight: 700 !important;
        line-height: 1.35 !important;
    }
    [data-testid="stMainBlockContainer"] .section-header {
        background: linear-gradient(90deg, #1a2340, #2e4080);
        color: white !important;
        padding: calc(var(--ecp-output-font-size) * 0.4) calc(var(--ecp-output-font-size) * 0.75);
        border-radius: 8px;
        margin: 14px 0 8px 0;
    }
    [data-testid="stMainBlockContainer"] h1, [data-testid="stMainBlockContainer"] h1 * { font-size: var(--ecp-font-size-h1) !important; font-weight: 700 !important; }
    [data-testid="stMainBlockContainer"] h2, [data-testid="stMainBlockContainer"] h2 * { font-size: var(--ecp-font-size-h2) !important; font-weight: 700 !important; }
    [data-testid="stMainBlockContainer"] h3, [data-testid="stMainBlockContainer"] h3 * { font-size: var(--ecp-font-size-h3) !important; font-weight: 600 !important; }
    [data-testid="stMainBlockContainer"] h4, [data-testid="stMainBlockContainer"] h4 * { font-size: calc(var(--ecp-output-font-size) * 1.05) !important; font-weight: 600 !important; }
    [data-testid="stMainBlockContainer"] h5, [data-testid="stMainBlockContainer"] h5 * { font-size: var(--ecp-output-font-size) !important; font-weight: 600 !important; }

    /* General Body Text outside inputs */
    [data-testid="stMainBlockContainer"] p:not([data-testid="stWidgetLabel"] *),
    [data-testid="stMainBlockContainer"] span:not([data-testid="stWidgetLabel"] *):not([data-baseweb="select"] *),
    [data-testid="stMainBlockContainer"] li,
    [data-testid="stMainBlockContainer"] strong:not([data-testid="stWidgetLabel"] *),
    [data-testid="stMainBlockContainer"] em {
        font-size: var(--ecp-font-size-body);
        line-height: 1.5;
    }

    /* Calculation Tables, DataFrames, Headers & Cell Numbers */
    [data-testid="stMainBlockContainer"] div[data-testid="stTable"],
    [data-testid="stMainBlockContainer"] div[data-testid="stTable"] *,
    [data-testid="stMainBlockContainer"] div[data-testid="stDataFrame"],
    [data-testid="stMainBlockContainer"] div[data-testid="stDataFrame"] *,
    [data-testid="stMainBlockContainer"] .stDataFrame,
    [data-testid="stMainBlockContainer"] .stDataFrame *,
    [data-testid="stMainBlockContainer"] table,
    [data-testid="stMainBlockContainer"] table *,
    [data-testid="stMainBlockContainer"] table th,
    [data-testid="stMainBlockContainer"] table th *,
    [data-testid="stMainBlockContainer"] table td,
    [data-testid="stMainBlockContainer"] table td *,
    [data-testid="stMainBlockContainer"] div[data-testid="glide-cell"],
    [data-testid="stMainBlockContainer"] div[data-testid="glide-cell"] *,
    [data-testid="stMainBlockContainer"] .dvn-scroller,
    [data-testid="stMainBlockContainer"] .dvn-scroller * {
        font-size: var(--ecp-font-size-table-cell) !important;
        line-height: 1.4 !important;
    }

    [data-testid="stMainBlockContainer"] table th,
    [data-testid="stMainBlockContainer"] table th * {
        font-size: var(--ecp-font-size-table-hdr) !important;
        font-weight: 700 !important;
    }

    /* Metric Cards / Result Summaries */
    [data-testid="stMainBlockContainer"] [data-testid="stMetric"],
    [data-testid="stMainBlockContainer"] div[data-testid="metric-container"] {
        background: #f0f4ff !important;
        border: 1px solid #c8d4f0 !important;
        border-radius: 8px !important;
        padding: 7px 11px !important;
        box-sizing: border-box !important;
    }

    [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"],
    [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] *,
    [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] > div,
    [data-testid="stMainBlockContainer"] div[data-testid="metric-container"] [data-testid="stMetricValue"],
    [data-testid="stMainBlockContainer"] div[data-testid="metric-container"] [data-testid="stMetricValue"] * {
        font-size: var(--ecp-font-size-metric-val) !important;
        white-space: normal !important;
        overflow: visible !important;
        line-height: 1.25 !important;
        font-weight: 700 !important;
        color: #1e3a8a !important;
    }

    [data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"],
    [data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] *,
    [data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] p,
    [data-testid="stMainBlockContainer"] div[data-testid="metric-container"] [data-testid="stMetricLabel"],
    [data-testid="stMainBlockContainer"] div[data-testid="metric-container"] [data-testid="stMetricLabel"] * {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: var(--ecp-font-size-metric-lbl) !important;
        white-space: normal !important;
        line-height: 1.2 !important;
    }

    [data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"],
    [data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"] * {
        font-size: 15px !important;
    }

    /* Result Highlight Cards & Banners */
    [data-testid="stMainBlockContainer"] div[style*="border:2px solid"],
    [data-testid="stMainBlockContainer"] div[style*="border:2px solid"] *,
    [data-testid="stMainBlockContainer"] div[style*="border:3px solid"],
    [data-testid="stMainBlockContainer"] div[style*="border:3px solid"] *,
    [data-testid="stMainBlockContainer"] .result-ok,
    [data-testid="stMainBlockContainer"] .result-ok *,
    [data-testid="stMainBlockContainer"] .result-warn,
    [data-testid="stMainBlockContainer"] .result-warn *,
    [data-testid="stMainBlockContainer"] .result-fail,
    [data-testid="stMainBlockContainer"] .result-fail * {
        font-size: var(--ecp-output-font-size) !important;
        line-height: 1.45;
    }

    /* Alerts & Notifications */
    [data-testid="stMainBlockContainer"] .stAlert {
        padding: calc(var(--ecp-output-font-size) * 0.4) calc(var(--ecp-output-font-size) * 0.75) !important;
        border-radius: 6px !important;
    }
    [data-testid="stMainBlockContainer"] .stAlert p,
    [data-testid="stMainBlockContainer"] .stAlert span,
    [data-testid="stMainBlockContainer"] .stAlert div,
    [data-testid="stMainBlockContainer"] .stAlert li,
    [data-testid="stMainBlockContainer"] .stAlert strong {
        font-size: var(--ecp-output-font-size) !important;
        line-height: 1.4 !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       EXPANDER HEADERS (عناوين الأقسام المطوية / Collapsed Sections) - 21px BOLD with Background
       ═══════════════════════════════════════════════════════════════════════════ */
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
        font-size: 21px !important;
        font-weight: 800 !important;
        line-height: 1.4 !important;
        color: #0f172a !important;
    }

    div[data-testid="stExpander"] details summary svg,
    div[data-testid="stExpander"] summary svg,
    .stExpander summary svg,
    details summary svg {
        width: 19px !important;
        height: 19px !important;
        min-width: 19px !important;
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

    /* Responsive Safeguards */
    div[data-testid="column"] { min-width: 0 !important; }
    div[data-testid="stDataFrame"] { width: 100% !important; overflow-x: auto !important; }
    </style>

    <script>
    (function() {
        try {
            const root = document.documentElement;
            root.style.setProperty('--ecp-modules-base-font-size', '16px');
            root.style.setProperty('--ecp-input-font-size', '19px');
            root.style.setProperty('--ecp-output-font-size', '19px');
        } catch(e) {
            console.warn('Init error:', e);
        }
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏗️ ECP 203 Dashboard")
    st.markdown("**Egyptian Code of Practice**")
    st.markdown("---")
    module = S_radio(
        "📂 Select Module (اختر موديول التصميم أو المساعد)",
        "selected_module_idx",
        options=[
            "🟦  Module 1 — Flat Slabs (البلاطات اللاكمرية)",
            "🏛️  Module 2 — Rectangular Columns (الأعمدة المستطيلة)",
            "🪨  Module 3 — Isolated Footings (القواعد المنفصلة)",
            "⚙️  المساعد — اقطار واوزان الحديد (Steel Rebar)",
            "📊  المساعد — حصر الخرسانات (Concrete Qty. Survey)",
        ],
    )
    st.markdown("---")

    st.markdown("<small>Units: **ton · kg · cm · kg/cm²**</small>", unsafe_allow_html=True)
    st.markdown("<small>Code: **ECP 203-2018**</small>", unsafe_allow_html=True)

    # ── Persistent-settings status & controls ────────────────────────────────
    st.markdown("---")

    loaded_from_file = st.session_state.get("_settings_loaded_from_file", False)
    last_save_ok     = st.session_state.get("_last_save_ok", None)

    if last_save_ok is True:
        st.markdown(
            "<small style='color:#6fcf97;'>💾 Settings auto-saved to user profile.</small>",
            unsafe_allow_html=True,
        )
    elif loaded_from_file:
        st.markdown(
            "<small style='color:#6fcf97;'>✅ Custom profile loaded.</small>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<small style='color:#a0aec0;'>📋 Using standard ECP 203 defaults.</small>",
            unsafe_allow_html=True,
        )

    if st.button("🔄 Reset to Standard ECP Defaults", use_container_width=True):
        reset_settings()
        st.rerun()

# ── MODULE ROUTING ───────────────────────────────────────────────────────────
if "Flat Slabs" in module or "Flat" in module:
    render_flat_slab()
elif "Columns" in module:
    render_columns()
elif "Footings" in module or "القواعد" in module:
    render_footings()
elif "اقطار" in module or "Steel" in module:
    render_steel_bars()
elif "حصر" in module or "Survey" in module:
    render_concrete_survey()
else:
    render_flat_slab()

# ── GUARANTEED DISK PERSISTENCE ──────────────────────────────────────────────
save_settings()

