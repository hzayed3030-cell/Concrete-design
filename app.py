"""
ECP 203 - Egyptian Code of Practice
Reinforced Concrete Engineering Dashboard
==========================================
Run with:  streamlit run app.py
"""

import os
import sys
import subprocess
import shutil
import datetime

# Ensure root directory is always first in sys.path regardless of CMD working directory
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

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
    cfg_set,
    radio as S_radio,
    get_all_projects,
    get_active_project_name,
    get_active_project,
    set_active_project,
    create_project,
    rename_project,
    delete_project,
    duplicate_project,
    get_project_summary,
    get_safe_project_filename_prefix,
    export_project_json,
    export_all_projects_json,
    import_project_json,
    # Aliases for backward compatibility
    get_all_profiles,
    get_active_profile_name,
    get_active_profile,
    set_active_profile,
    create_profile,
    rename_profile,
    delete_profile,
    duplicate_profile,
    get_profile_summary,
    get_safe_profile_filename_prefix,
    export_profile_json,
    export_all_profiles_json,
    import_profile_json,
)
load_settings()


from modules.columns   import render as render_columns
from modules.footings  import render as render_footings
from modules.flat_slab import render as render_flat_slab
from modules.steel_bars import render as render_steel_bars
from modules.concrete_survey import render as render_concrete_survey
from modules.ground_slab import render as render_ground_slab

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

    /* ═══════════════════════════════════════════════════════════════════════════
       PROFILES DASHBOARD & METRIC BOXES THEME-ADAPTIVE STYLING (2X ENLARGED)
       ═══════════════════════════════════════════════════════════════════════════ */
    .profile-card {
        background: #ffffff;
        border: 2px solid #cbd5e1;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        transition: all 0.2s ease;
    }
    .profile-card.active {
        border: 3px solid #2563eb !important;
        background: #eff6ff;
    }
    .profile-card-title {
        font-size: 31px;
        font-weight: 800;
        color: #0f172a;
    }
    .profile-card-meta {
        font-size: 23px;
        color: #64748b;
        margin-bottom: 8px;
    }
    .profile-card-specs {
        background: #f8fafc;
        border: 1.5px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 24px;
        color: #1e293b;
        line-height: 1.6;
        margin-bottom: 12px;
    }
    .profile-card-specs div {
        font-size: 24px !important;
        color: #1e293b !important;
    }
    .profile-card-specs b {
        font-size: 24px !important;
        color: #0f172a !important;
    }

    .ecp-metric-box {
        background: #f8fafc;
        border: 1.5px solid #cbd5e1;
        border-radius: 10px;
        padding: 12px 16px;
        text-align: center;
    }
    .ecp-metric-lbl {
        font-size: 26px;
        font-weight: 600;
        color: #64748b;
        margin-bottom: 4px;
    }
    .ecp-metric-val {
        font-size: 36px;
        font-weight: 700;
        color: #1e40af;
    }

    /* Double font sizes for all interactive widgets in Profile Manager View */
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) button,
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) button p,
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) button span,
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) label p,
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) div[data-baseweb="select"] span {
        font-size: 1.30rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) input {
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        padding: 8px 12px !important;
    }
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) button {
        min-height: 48px !important;
        padding: 8px 14px !important;
    }

    /* Sidebar Profile Manager 2x Font Scale */
    div[data-testid="stSidebar"]:has(.sidebar-profile-mgr-badge) button,
    div[data-testid="stSidebar"]:has(.sidebar-profile-mgr-badge) button p,
    div[data-testid="stSidebar"]:has(.sidebar-profile-mgr-badge) button span {
        font-size: 1.25rem !important;
        font-weight: 800 !important;
        min-height: 48px !important;
    }
    div[data-testid="stSidebar"]:has(.sidebar-profile-mgr-badge) small {
        font-size: 19px !important;
    }

    /* Dark Mode Adaptive Rules */
    @media (prefers-color-scheme: dark) {
        .profile-card {
            background: #1e293b !important;
            border-color: #334155 !important;
        }
        .profile-card.active {
            border-color: #3b82f6 !important;
            background: #1e3a8a !important;
        }
        .profile-card-title {
            color: #f8fafc !important;
        }
        .profile-card-meta {
            color: #94a3b8 !important;
        }
        .profile-card-specs {
            background: #0f172a !important;
            border-color: #334155 !important;
            color: #e2e8f0 !important;
        }
        .profile-card-specs div {
            color: #e2e8f0 !important;
        }
        .profile-card-specs b {
            color: #93c5fd !important;
        }
        .ecp-metric-box {
            background: #1e293b !important;
            border-color: #334155 !important;
        }
        .ecp-metric-lbl {
            color: #94a3b8 !important;
        }
        .ecp-metric-val {
            color: #60a5fa !important;
        }
    }

    [data-theme="dark"] .profile-card,
    .stApp[data-theme="dark"] .profile-card {
        background: #1e293b !important;
        border-color: #334155 !important;
    }
    [data-theme="dark"] .profile-card.active,
    .stApp[data-theme="dark"] .profile-card.active {
        border-color: #3b82f6 !important;
        background: #1e3a8a !important;
    }
    [data-theme="dark"] .profile-card-title,
    .stApp[data-theme="dark"] .profile-card-title {
        color: #f8fafc !important;
    }
    [data-theme="dark"] .profile-card-meta,
    .stApp[data-theme="dark"] .profile-card-meta {
        color: #94a3b8 !important;
    }
    [data-theme="dark"] .profile-card-specs,
    .stApp[data-theme="dark"] .profile-card-specs {
        background: #0f172a !important;
        border-color: #334155 !important;
        color: #e2e8f0 !important;
    }
    [data-theme="dark"] .profile-card-specs div,
    .stApp[data-theme="dark"] .profile-card-specs div {
        color: #e2e8f0 !important;
    }
    [data-theme="dark"] .profile-card-specs b,
    .stApp[data-theme="dark"] .profile-card-specs b {
        color: #93c5fd !important;
    }
    [data-theme="dark"] .ecp-metric-box,
    .stApp[data-theme="dark"] .ecp-metric-box {
        background: #1e293b !important;
        border-color: #334155 !important;
    }
    [data-theme="dark"] .ecp-metric-lbl,
    .stApp[data-theme="dark"] .ecp-metric-lbl {
        color: #94a3b8 !important;
    }
    [data-theme="dark"] .ecp-metric-val,
    .stApp[data-theme="dark"] .ecp-metric-val {
        color: #60a5fa !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       PROJECT NAME & OWNER NAME HIGH-CONTRAST BRIGHT BADGES (DARK MODE OPTIMIZED)
       ═══════════════════════════════════════════════════════════════════════════ */
    .profile-project-badge {
        font-size: 24px !important;
        font-weight: 800 !important;
        color: #0369a1 !important;
        background: #e0f2fe !important;
        border: 2px solid #38bdf8 !important;
        padding: 4px 14px !important;
        border-radius: 8px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }
    .profile-owner-badge {
        font-size: 23px !important;
        font-weight: 800 !important;
        color: #15803d !important;
        background: #dcfce7 !important;
        border: 2px solid #4ade80 !important;
        padding: 4px 14px !important;
        border-radius: 8px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }

    /* Dark Mode Adaptation - Vivid Luminous High Contrast */
    @media (prefers-color-scheme: dark) {
        .profile-project-badge {
            color: #38bdf8 !important;
            background: rgba(56, 189, 248, 0.22) !important;
            border-color: #38bdf8 !important;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.25) !important;
        }
        .profile-owner-badge {
            color: #4ade80 !important;
            background: rgba(74, 222, 128, 0.22) !important;
            border-color: #4ade80 !important;
            box-shadow: 0 0 10px rgba(74, 222, 128, 0.25) !important;
        }
    }
    [data-theme="dark"] .profile-project-badge,
    .stApp[data-theme="dark"] .profile-project-badge {
        color: #38bdf8 !important;
        background: rgba(56, 189, 248, 0.22) !important;
        border-color: #38bdf8 !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.25) !important;
    }
    [data-theme="dark"] .profile-owner-badge,
    .stApp[data-theme="dark"] .profile-owner-badge {
        color: #4ade80 !important;
        background: rgba(74, 222, 128, 0.22) !important;
        border-color: #4ade80 !important;
        box-shadow: 0 0 10px rgba(74, 222, 128, 0.25) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       CENTERED & ENLARGED LOADING ANIMATION (مؤشر التحميل والتنفيذ بمنتصف الشاشة)
       ═══════════════════════════════════════════════════════════════════════════ */

    /* Hide unnecessary Deploy button from top toolbar */
    [data-testid="stDeployButton"],
    .stDeployButton {
        display: none !important;
    }

    /* Center and Enlarge the Running Man / Status Widget (Green Theme) */
    div[data-testid="stStatusWidget"]:has(svg),
    div[data-testid="stStatusWidget"]:has(button),
    div[data-testid="stStatusWidget"]:not(:empty) {
        position: fixed !important;
        top: 48% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        z-index: 9999999 !important;
        background: linear-gradient(135deg, #064e3b 0%, #14532d 50%, #064e3b 100%) !important;
        border: 2.5px solid #22c55e !important;
        border-radius: 20px !important;
        padding: 20px 36px !important;
        box-shadow: 0 0 50px rgba(34, 197, 94, 0.6), 0 20px 70px rgba(0, 0, 0, 0.95) !important;
        backdrop-filter: blur(14px) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 18px !important;
        animation: st-center-pulse-green 1.4s infinite alternate ease-in-out !important;
    }

    @keyframes st-center-pulse-green {
        0% {
            box-shadow: 0 0 30px rgba(34, 197, 94, 0.45), 0 15px 50px rgba(0, 0, 0, 0.9);
            border-color: #22c55e;
        }
        100% {
            box-shadow: 0 0 60px rgba(74, 222, 128, 0.8), 0 25px 80px rgba(0, 0, 0, 1);
            border-color: #4ade80;
        }
    }

    /* Magnify the Running Man SVG Icon */
    div[data-testid="stStatusWidget"] svg {
        width: 52px !important;
        height: 52px !important;
        transform: scale(1.6) !important;
        filter: drop-shadow(0 0 12px rgba(74, 222, 128, 0.9)) !important;
    }

    /* Enlarge Running Status Text */
    div[data-testid="stStatusWidget"] span,
    div[data-testid="stStatusWidget"] p {
        font-size: 24px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        text-shadow: 0 0 12px rgba(74, 222, 128, 0.7) !important;
        letter-spacing: 0.5px !important;
    }

    /* Enlarge & Style Stop Button */
    div[data-testid="stStatusWidget"] button {
        background: rgba(239, 68, 68, 0.25) !important;
        border: 2px solid #ef4444 !important;
        border-radius: 12px !important;
        color: #fca5a5 !important;
        font-size: 18px !important;
        font-weight: 800 !important;
        padding: 8px 20px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stStatusWidget"] button:hover {
        background: #ef4444 !important;
        color: #ffffff !important;
        box-shadow: 0 0 16px rgba(239, 68, 68, 0.6) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       GLOBAL PROJECT NAME (اسم المشروع) LUXURY CENTERED STYLING (1.80rem THEME)
       ═══════════════════════════════════════════════════════════════════════════ */
    
    /* Target ANY Project Name Text Input container across ALL modules and forms */
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]),
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) {
        text-align: center !important;
        margin: 2px auto 8px auto !important;
        width: 100% !important;
        background: linear-gradient(135deg, #0b1329 0%, #1e293b 50%, #0b1329 100%) !important;
        border: 2px solid #fbbf24 !important;
        border-radius: 12px !important;
        padding: 6px 16px 8px 16px !important;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.6), 0 0 14px rgba(251, 191, 36, 0.2) !important;
    }

    /* Target the Label */
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]) label,
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) label,
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]) label p,
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) label p,
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]) [data-testid="stWidgetLabel"] p,
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) [data-testid="stWidgetLabel"] p {
        font-size: 1.60rem !important;
        font-weight: 900 !important;
        color: #fbbf24 !important;
        text-align: center !important;
        display: block !important;
        width: 100% !important;
        margin: 0 auto 3px auto !important;
        line-height: 1.2 !important;
        text-shadow: 0 0 12px rgba(251, 191, 36, 0.45) !important;
        letter-spacing: 0.5px !important;
    }

    /* Target the Input Box (Distinctive Luminous Cyan / Sky Blue Text) */
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]) input,
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) input {
        font-size: 1.65rem !important;
        font-weight: 900 !important;
        color: #38bdf8 !important;
        background: #080f1d !important;
        border: 1.8px solid #38bdf8 !important;
        border-radius: 8px !important;
        padding: 6px 14px !important;
        text-align: center !important;
        box-shadow: 0 0 14px rgba(56, 189, 248, 0.25), 0 4px 14px rgba(0, 0, 0, 0.5) !important;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important;
        transition: all 0.25s ease-in-out !important;
    }

    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]) input:focus,
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) input:focus {
        border-color: #67e8f9 !important;
        box-shadow: 0 0 22px rgba(103, 232, 249, 0.55) !important;
        color: #67e8f9 !important;
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

# ── PROFILE MANAGEMENT & NAVIGATION HELPERS ─────────────────────────────────

# ── PROJECT MANAGEMENT & NAVIGATION HELPERS ─────────────────────────────────

def render_top_profile_bar():
    """Top navigation banner displayed when viewing design modules."""
    active_pname = get_active_project_name()
    all_projects = list(get_all_projects().keys())
    if active_pname not in all_projects and all_projects:
        active_pname = all_projects[0]

    c_hdr1, c_hdr2, c_hdr3 = st.columns([4, 2, 2])
    with c_hdr1:
        st.markdown(
            f"""<div style="background:rgba(30,41,59,0.07); border:1px solid rgba(30,41,59,0.15); border-radius:8px; padding:6px 14px; display:inline-flex; align-items:center; gap:10px; flex-wrap:wrap;">
                <span style="font-size:15px; font-weight:700;">📁 المشروع النشط:</span>
                <span style="font-size:17px; font-weight:800; color:#2563eb;">{active_pname}</span>
            </div>""",
            unsafe_allow_html=True,
        )
    with c_hdr2:
        if st.button("🏠 إدارة المشاريع", use_container_width=True, key="top_bar_projects"):
            st.session_state["nav_view"] = "profile_manager"
            st.rerun()
    with c_hdr3:
        fs_mode = st.session_state.get("fs_mode", "run")
        mode_label = "✏️ وضع التعديل" if fs_mode == "edit" else "🚀 وضع التشغيل"
        if st.button(mode_label, use_container_width=True, key="top_bar_mode_toggle"):
            st.session_state["fs_mode"] = "edit" if fs_mode == "run" else "run"
            st.rerun()

    st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)


def get_github_repo_url():
    try:
        res = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=app_dir, capture_output=True, text=True)
        url = (res.stdout or "").strip()
        if url.endswith(".git"):
            url = url[:-4]
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url[len("git@github.com:"):]
        if not url:
            url = "https://github.com/hzayed3030-cell/Concrete-design"
        return url
    except Exception:
        return "https://github.com/hzayed3030-cell/Concrete-design"


def render_profile_manager():
    """Start Screen: Ultra-Compact High-Density Dark Mode Projects Dashboard."""
    projects = get_all_projects()
    active_name = get_active_project_name()

    if st.session_state.get("git_push_success_msg"):
        st.success(st.session_state["git_push_success_msg"])
        st.balloons()
        del st.session_state["git_push_success_msg"]

    # ── Centered Distinctive Header Banner (White Text on Dark Background) ──
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #0b1329 0%, #1e293b 50%, #0b1329 100%);
            padding: 14px 20px;
            border-radius: 12px;
            margin-bottom: 12px;
            border: 1.5px solid rgba(56, 189, 248, 0.4);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5), 0 0 15px rgba(56, 189, 248, 0.15);
            text-align: center;
        ">
            <div style="display: flex; justify-content: center; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span style="font-size: 32px;">📁</span>
                <span style="
                    font-size: 28px;
                    font-weight: 900;
                    color: #ffffff;
                    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.6);
                    letter-spacing: 0.5px;
                ">
                    إدارة المشاريع (Projects Manager)
                </span>
                <span style="
                    background: rgba(56, 189, 248, 0.18);
                    color: #38bdf8;
                    border: 1.5px solid #38bdf8;
                    padding: 3px 14px;
                    border-radius: 16px;
                    font-size: 15px;
                    font-weight: 800;
                    margin-right: 10px;
                    box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
                ">
                    📊 {len(projects)} مشاريع
                </span>
            </div>
            <div style="
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                margin-top: 6px;
            ">
                حفظ وتصميم ومتابعة المشاريع الإنشائية — <span style="color: #ffffff; font-weight: 900;">ECP 203</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Global Actions Toolbar (Compact) ────────────────────────────────────
    g1, g2, g3, g4, g5 = st.columns([1.1, 1.1, 1.3, 1.3, 1.3])
    with g1:
        if st.button("➕ مشروع جديد", use_container_width=True, type="primary", key="btn_global_new"):
            st.session_state["show_create_profile_form"] = not st.session_state.get("show_create_profile_form", False)
            st.session_state["show_import_profile_form"] = False
            st.session_state["show_git_update_form"] = False
            st.rerun()
    with g2:
        if st.button("📥 استيراد JSON", use_container_width=True, key="btn_global_import"):
            st.session_state["show_import_profile_form"] = not st.session_state.get("show_import_profile_form", False)
            st.session_state["show_create_profile_form"] = False
            st.session_state["show_git_update_form"] = False
            st.rerun()
    with g3:
        all_projects_json = export_all_projects_json()
        st.download_button(
            label="📤 تصدير الكل (Backup JSON)",
            data=all_projects_json,
            file_name="ECP203_All_Projects_Backup.json",
            mime="application/json",
            use_container_width=True,
            key="btn_global_backup",
        )
    with g4:
        if st.button("🚀 Update git hub", use_container_width=True, key="btn_global_github_sync"):
            st.session_state["show_git_update_form"] = not st.session_state.get("show_git_update_form", False)
            st.session_state["show_create_profile_form"] = False
            st.session_state["show_import_profile_form"] = False
            st.rerun()
    with g5:
        gh_url = get_github_repo_url()
        st.link_button("🌐 Explore git hub", gh_url, use_container_width=True)

    # ── Update GitHub Form & Verification ──────────────────────────────────
    if st.session_state.get("show_git_update_form", False):
        col_git_pad1, col_git_center, col_git_pad2 = st.columns([0.6, 6.8, 0.6])
        with col_git_center:
            with st.container(border=True):
                # 1. Check for dist / build directories
                dist_dirs = [d for d in ["dist", "build", "built"] if os.path.exists(os.path.join(app_dir, d))]
                if dist_dirs:
                    st.markdown(
                        f"""
                        <div style="background: rgba(239, 68, 68, 0.15); border: 2px solid #ef4444; border-radius: 10px; padding: 14px 18px; color: #fecaca; margin-bottom: 12px; box-shadow: 0 4px 16px rgba(239, 68, 68, 0.25);">
                            <div style="color: #f87171; font-weight: 900; font-size: 1.15rem; display:flex; align-items:center; gap:8px;">
                                <span>⛔</span> تم رفض الرفع إلى GitHub (الحجم كبير لوجود مجلدات dist / build)
                            </div>
                            <div style="font-size: 0.95rem; margin-top: 8px; line-height: 1.5; color: #ffffff;">
                                تم اكتشاف وجود فهارس بناء وتوزيع (<b>{' / '.join(dist_dirs)}</b>) في المجلد الرئيسي للمشروع.<br>
                                تم رفض عملية الرفع لتفادي تجاوز سعة المستودع ورفع ملفات ضخمة غير مرغوبة إلى GitHub.<br>
                                <b>الحل:</b> يرجى حذف مجلدات <code>dist</code> أو <code>build</code> أولاً ثم إعادة المحاولة.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    cg1, cg2 = st.columns([2, 1])
                    with cg1:
                        if st.button("🗑️ حذف مجلدات dist و build والمتابعة فوراً", use_container_width=True, type="primary", key="btn_clean_dist_build"):
                            for d in dist_dirs:
                                shutil.rmtree(os.path.join(app_dir, d), ignore_errors=True)
                            st.success("تم حذف مجلدات البناء بنجاح.")
                            st.rerun()
                    with cg2:
                        if st.button("❌ إلغاء", use_container_width=True, key="btn_cancel_dist_error"):
                            st.session_state["show_git_update_form"] = False
                            st.rerun()
                else:
                    st.markdown(
                        """
                        <div style="background: linear-gradient(135deg, #0b1329 0%, #1e293b 50%, #0b1329 100%); border: 2px solid #38bdf8; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 4px 16px rgba(56, 189, 248, 0.2);">
                            <div style="display:flex; align-items:center; gap:8px; font-weight:900; font-size:1.15rem; color:#38bdf8;">
                                <span>🚀</span> تأكيد رفع التحديثات إلى مستودع GitHub (Update git hub)
                            </div>
                            <div style="color:#cbd5e1; font-size:0.92rem; margin-top:6px; line-height: 1.4;">
                                سيتم حفظ كافة الملفات والتعديلات وإرسالها إلى مستودع GitHub الرئيسي عبر الأوامر (<code>git add .</code> ⬅️ <code>git commit</code> ⬅️ <code>git push</code>).
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    commit_msg = st.text_input(
                        "اسم التعديل (Commit Message):",
                        value=f"Update project - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        placeholder="اكتب وصف التعديل الذي سيظهر بعد علامات التنصيص في أمر commit...",
                        key="input_git_commit_msg",
                        help="اسم ورسالة التعديل التي ستسجل في سجل Git و GitHub بعد علامات التنصيص -m \"...\"",
                    )
                    col_gbtn1, col_gbtn2 = st.columns([2, 1])
                    with col_gbtn1:
                        if st.button("🚀 تأكيد ورفع التحديثات إلى GitHub", use_container_width=True, type="primary", key="btn_exec_git_push"):
                            # Final safety check
                            cur_dist_dirs = [d for d in ["dist", "build", "built"] if os.path.exists(os.path.join(app_dir, d))]
                            if cur_dist_dirs:
                                st.error("⛔ تم رفض الرفع لوجود مجلدات dist أو build!")
                            else:
                                with st.spinner("⏳ جاري رفع التحديثات إلى GitHub... (git add . ; git commit ; git push)"):
                                    msg_final = commit_msg.strip() if commit_msg and commit_msg.strip() else "Update project files"
                                    # git add .
                                    subprocess.run(["git", "add", "."], cwd=app_dir, capture_output=True, text=True)
                                    # git commit -m
                                    res_commit = subprocess.run(["git", "commit", "-m", msg_final], cwd=app_dir, capture_output=True, text=True)
                                    # git push
                                    res_push = subprocess.run(["git", "push"], cwd=app_dir, capture_output=True, text=True)

                                    if res_push.returncode == 0:
                                        st.session_state["git_push_success_msg"] = f"✅ تم رفع وتحديث المشروع إلى GitHub بنجاح! باسم التعديل: «{msg_final}»"
                                        st.session_state["show_git_update_form"] = False
                                        st.rerun()
                                    else:
                                        err_text = (res_push.stderr or res_push.stdout or "").strip()
                                        if "Everything up-to-date" in err_text or "nothing to commit" in (res_commit.stdout or ""):
                                            st.session_state["git_push_success_msg"] = "✅ تم التحقق: المستودع متزامن مع GitHub بالفعل ولا توجد تعديلات جديدة للرفع (Everything up-to-date)."
                                            st.session_state["show_git_update_form"] = False
                                            st.rerun()
                                        else:
                                            st.error(f"❌ حدث خطأ أثناء الرفع إلى GitHub:\n\n{err_text}")
                    with col_gbtn2:
                        if st.button("❌ إلغاء", use_container_width=True, key="btn_cancel_git_form"):
                            st.session_state["show_git_update_form"] = False
                            st.rerun()

        st.markdown("<hr style='margin: 10px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)

    # ── Create New Project Form (Centered & Compact Cyan Theme) ──────────
    if st.session_state.get("show_create_profile_form", False):
        col_cf_pad1, col_cf_center, col_cf_pad2 = st.columns([0.6, 6.8, 0.6])
        with col_cf_center:
            with st.container(border=True):
                st.markdown(
                    """
                    <style>
                    div.new-project-box div[data-testid="stTextInput"] label,
                    div.new-project-box div[data-testid="stTextInput"] label p {
                        font-size: 1.60rem !important;
                        font-weight: 900 !important;
                        color: #fbbf24 !important;
                        line-height: 1.2 !important;
                        text-align: center !important;
                        display: block !important;
                        width: 100% !important;
                        margin-bottom: 4px !important;
                        text-shadow: 0 0 12px rgba(251, 191, 36, 0.45) !important;
                    }
                    div.new-project-box div[data-testid="stTextInput"] input {
                        font-size: 1.65rem !important;
                        font-weight: 900 !important;
                        color: #38bdf8 !important;
                        background: #080f1d !important;
                        border: 1.8px solid #38bdf8 !important;
                        border-radius: 8px !important;
                        padding: 6px 14px !important;
                        text-align: center !important;
                        box-shadow: 0 0 14px rgba(56, 189, 248, 0.25) !important;
                        text-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important;
                    }
                    div.new-project-box div[data-testid="stTextInput"] input:focus {
                        border-color: #67e8f9 !important;
                        box-shadow: 0 0 22px rgba(103, 232, 249, 0.55) !important;
                        color: #67e8f9 !important;
                    }
                    </style>
                    <div class="new-project-box" style="margin-bottom: 4px;">
                        <div style="
                            background: linear-gradient(135deg, #b45309 0%, #d97706 50%, #b45309 100%);
                            color: #ffffff !important;
                            padding: 6px 16px;
                            border-radius: 8px;
                            font-weight: 900;
                            font-size: 18px;
                            margin-bottom: 14px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            gap: 10px;
                            border: 1.5px solid #fbbf24;
                            box-shadow: 0 0 16px rgba(251, 191, 36, 0.35);
                        ">
                            <span style="font-size: 24px;">✨</span>
                            <span style="color: #ffffff !important; font-size: 20px; font-weight: 900;">إنشاء مشروع إنشائي جديد (New Project)</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown('<div class="new-project-box">', unsafe_allow_html=True)
                new_p_name = st.text_input(
                    "اسم المشروع (Project Name)",
                    value=f"مشروع {len(projects) + 1}",
                    placeholder="أدخل اسم المشروع (مثلاً: حصر الخرسانات، برج النور...)",
                    key="input_new_project_name",
                )
                st.markdown('</div>', unsafe_allow_html=True)

                col_tmpl, col_btns = st.columns([1.5, 1])
                with col_tmpl:
                    template_options = ["مشروع جديد (ECP Defaults)"] + [f"نسخ الأبعاد من: {p}" for p in projects.keys()]
                    selected_tmpl = st.selectbox("بدء من:", options=template_options, key="input_new_project_template")
                with col_btns:
                    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
                    cs1, cs2 = st.columns(2)
                    with cs1:
                        if st.button("✅ حفظ وتفعيل", use_container_width=True, type="primary"):
                            if new_p_name.strip():
                                copy_src = None
                                if "نسخ الأبعاد من: " in selected_tmpl:
                                    copy_src = selected_tmpl.replace("نسخ الأبعاد من: ", "").strip()
                                created_name = create_project(new_p_name.strip(), copy_from=copy_src)
                                st.session_state["show_create_profile_form"] = False
                                st.session_state["nav_view"] = "module"
                                st.session_state["fs_mode"] = "edit"
                                st.session_state["selected_module_idx"] = 0
                                st.success(f"تم إنشاء وتفعيل المشروع: {created_name}")
                                st.rerun()
                            else:
                                st.error("يرجى إدخال اسم صحيح.")
                    with cs2:
                        if st.button("❌ إلغاء", use_container_width=True, key="btn_cancel_create"):
                            st.session_state["show_create_profile_form"] = False
                            st.rerun()

        st.markdown("<hr style='margin: 10px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)

    # ── Import Project Form (Compact) ──────────────────────────────────────
    if st.session_state.get("show_import_profile_form", False):
        st.markdown(
            """<div style="background: rgba(22, 101, 52, 0.2); border: 1.5px solid #4ade80; border-radius: 8px; padding: 10px 16px; margin: 8px 0 10px 0;">
                <div style="font-weight: 800; color: #4ade80; font-size: 18px;">📥 استيراد مشاريع من ملف JSON</div>
            </div>""",
            unsafe_allow_html=True,
        )
        ci1, ci2 = st.columns([3, 1])
        with ci1:
            uploaded_json = st.file_uploader("📂 اختر ملف JSON:", type=["json"], key="uploader_project_json_file")
            overwrite_choice = st.checkbox("استبدال المشاريع الموجودة بنفس الاسم (Overwrite)", value=False)
        with ci2:
            st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
            ci_a, ci_b = st.columns(2)
            with ci_a:
                if st.button("📥 استيراد", use_container_width=True, type="primary"):
                    if uploaded_json is not None:
                        try:
                            json_raw = uploaded_json.read().decode("utf-8")
                            ok, msg = import_project_json(json_raw, overwrite=overwrite_choice)
                            if ok:
                                st.session_state["show_import_profile_form"] = False
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                        except Exception as ex:
                            st.error(f"خطأ: {ex}")
                    else:
                        st.warning("يرجى اختيار ملف أولاً.")
            with ci_b:
                if st.button("❌ إلغاء", use_container_width=True, key="btn_cancel_import"):
                    st.session_state["show_import_profile_form"] = False
                    st.rerun()
        st.markdown("<hr style='margin:6px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)

    # ── Delete Confirmation Dialog ─────────────────────────────────────────
    if st.session_state.get("_profile_to_delete"):
        del_target = st.session_state["_profile_to_delete"]
        st.markdown(
            f"""<div style="background: rgba(239, 68, 68, 0.15); border: 1.5px solid #ef4444; border-radius: 8px; padding: 10px 16px; margin: 8px 0 10px 0;">
                <div style="color: #f87171; font-weight: 800; font-size: 18px;">⚠️ تأكيد حذف المشروع</div>
                <div style="font-size: 16px; color: #f1f5f9; margin-top: 4px;">هل أنت متأكد من حذف المشروع <b>«{del_target}»</b> وجميع بياناته؟</div>
            </div>""",
            unsafe_allow_html=True,
        )
        cd1, cd2, _ = st.columns([1.4, 1.4, 5])
        with cd1:
            if st.button("🗑️ تأكيد الحذف", use_container_width=True, type="primary"):
                delete_project(del_target)
                st.session_state["_profile_to_delete"] = None
                st.success(f"تم حذف «{del_target}».")
                st.rerun()
        with cd2:
            if st.button("❌ تراجع", use_container_width=True):
                st.session_state["_profile_to_delete"] = None
                st.rerun()
        st.markdown("<hr style='margin:6px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)

    # ── Compact Projects List ───────────────────────────────────────────────
    st.markdown(
        "<div style='margin:8px 0 6px 0; font-weight: 800; font-size: 18px; color: #e2e8f0;'>📋 قائمة المشاريع المسجلة:</div>",
        unsafe_allow_html=True,
    )

    all_pnames = list(projects.keys())
    # Sort active project to the very top (first)
    if active_name in all_pnames:
        sorted_pnames = [active_name] + [p for p in all_pnames if p != active_name]
    else:
        sorted_pnames = all_pnames

    for pname in sorted_pnames:
        summary = get_project_summary(pname)
        is_active = (pname == active_name)
        safe_pname = get_safe_project_filename_prefix(pname)
        project_json_str = export_project_json(pname)
        p_updated = summary.get("updated_at", "-")

        if is_active:
            card_border = "1.5px solid #38bdf8"
            card_bg = "linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 58, 138, 0.3) 100%)"
            card_shadow = "box-shadow: 0 2px 10px rgba(56, 189, 248, 0.18);"
            title_color = "#38bdf8"
            badge_html = """<span style="background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; padding: 2px 8px; border-radius: 6px; font-size: 13px; font-weight: 800;">🟢 النشط حالياً</span>"""
        else:
            card_border = "1px solid rgba(148, 163, 184, 0.18)"
            card_bg = "linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.45) 100%)"
            card_shadow = "box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);"
            title_color = "#f1f5f9"
            badge_html = """<span style="background: rgba(148, 163, 184, 0.12); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.25); padding: 2px 7px; border-radius: 6px; font-size: 12px; font-weight: 700;">📁 محفوظ</span>"""

        row_html = f"""<div style="background: {card_bg}; border: {card_border}; {card_shadow} border-radius: 8px; padding: 8px 14px; margin-bottom: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span style="font-size: 18px; font-weight: 800; color: {title_color};">📁 {pname}</span>
                    {badge_html}
                </div>
                <div style="font-size: 13px; color: #94a3b8; font-weight: 600;">
                    <span>🕒 آخر تعديل:</span>
                    <span style="color: #cbd5e1; font-weight: 700;">{p_updated}</span>
                </div>
            </div>
        </div>"""
        st.markdown(row_html, unsafe_allow_html=True)

        # Action buttons — compact & only 'تشغيل' with file tools
        b1, b2, b3, b4, _pad = st.columns([1.1, 1.0, 0.8, 0.5, 5.8])
        with b1:
            if st.button(
                "🚀 تشغيل",
                key=f"btn_run_{pname}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                set_active_project(pname)
                st.session_state["nav_view"] = "module"
                st.session_state["selected_module_idx"] = 0
                st.session_state["fs_mode"] = "run"
                st.rerun()
        with b2:
            st.download_button(
                label="📤 تصدير JSON",
                data=project_json_str,
                file_name=f"{safe_pname}project.json",
                mime="application/json",
                key=f"btn_exp_{pname}",
                use_container_width=True,
            )
        with b3:
            if st.button(
                "📋 نسخ",
                key=f"btn_dup_{pname}",
                use_container_width=True,
            ):
                new_cloned = duplicate_project(pname)
                st.success(f"تم نسخ المشروع: {new_cloned}")
                st.rerun()
        with b4:
            if st.button(
                "🗑️",
                key=f"btn_del_{pname}",
                use_container_width=True,
                help=f"حذف مشروع {pname}",
            ):
                st.session_state["_profile_to_delete"] = pname
                st.rerun()

        st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)


# ── MAIN EXECUTION & SIDEBAR CONDITIONAL ROUTING ──────────────────────────────
current_nav = st.session_state.get("nav_view", "profile_manager")

if current_nav == "profile_manager":
    # ── FULL SCREEN: Projects Manager Mode (Sidebar completely hidden to prevent repetition) ──
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        section.main > div.block-container {
            max-width: 98% !important;
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    render_profile_manager()

else:
    # ── SIDEBAR: Design Modules Dashboard Mode ─────────────────────────────
    with st.sidebar:
        st.markdown("## 🏗️ ECP 203 Dashboard")
        st.markdown("**Egyptian Code of Practice**")
        st.markdown("---")

        active_project_sidebar = get_active_project_name()
        all_projects_dict = get_all_projects()
        all_projects_list = list(all_projects_dict.keys())
        if active_project_sidebar not in all_projects_list and all_projects_list:
            active_project_sidebar = all_projects_list[0]

        mod_card_html = (
            f'<div style="background:rgba(255,255,255,0.08); padding:10px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.15); margin-bottom:10px;">'
            f'<div style="font-size:13px; color:#94a3b8;">📁 المشروع النشط:</div>'
            f'<div style="font-size:18px; font-weight:800; color:#60a5fa;">{active_project_sidebar}</div>'
            f'</div>'
        )
        st.markdown(mod_card_html, unsafe_allow_html=True)

        if st.button("🏠 شاشة إدارة المشاريع (Projects)", use_container_width=True):
            st.session_state["nav_view"] = "profile_manager"
            st.rerun()

        st.markdown("---")

        module = S_radio(
            "📂 Select Module (اختر موديول التصميم أو المساعد)",
            "selected_module_idx",
            options=[
                "🟦  Module 1 — Flat Slabs (البلاطات اللاكمرية)",
                "🏛️  Module 2 — Rectangular Columns (الأعمدة المستطيلة)",
                "🪸  Module 3 — Isolated Footings (القواعد المنفصلة)",
                "🏗️  Module 4 — Ground Slabs (البلاطات الأرضية)",
                "⚙️  المساعد — اقطار واوزان الحديد (Steel Rebar)",
                "📊  المساعد — حصر الخرسانات (Concrete Qty. Survey)",
            ],
        )
        st.markdown("---")

        st.markdown("<small>Units: **ton · kg · cm · kg/cm²**</small>", unsafe_allow_html=True)
        st.markdown("<small>Code: **ECP 203-2018**</small>", unsafe_allow_html=True)
        st.markdown("---")

        loaded_from_file = st.session_state.get("_settings_loaded_from_file", False)
        last_save_ok     = st.session_state.get("_last_save_ok", None)
        if last_save_ok is True:
            st.markdown(
                f"<small style='color:#6fcf97;'>💾 تم حفظ التعديلات في المشروع <b>{active_project_sidebar}</b>.</small>",
                unsafe_allow_html=True,
            )
        elif loaded_from_file:
            st.markdown(
                f"<small style='color:#6fcf97;'>✅ تم تحميل المشروع <b>{active_project_sidebar}</b> بنجاح.</small>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<small style='color:#a0aec0;'>📋 يتم استخدام القيم الافتراضية للكود المصري ECP 203.</small>", unsafe_allow_html=True)

        if st.session_state.get("_confirm_reset_project", False):
            st.markdown(
                f"""<div style="background: rgba(239, 68, 68, 0.15); border: 1.5px solid #ef4444; border-radius: 8px; padding: 10px 12px; margin: 8px 0 10px 0;">
                    <div style="color: #f87171; font-weight: 800; font-size: 15px;">⚠️ تأكيد إعادة الضبط</div>
                    <div style="font-size: 13px; color: #f1f5f9; margin-top: 4px;">هل أنت متأكد من استعادة القيم الافتراضية للمشروع <b>«{active_project_sidebar}»</b>؟</div>
                </div>""",
                unsafe_allow_html=True,
            )
            col_rc1, col_rc2 = st.columns(2)
            with col_rc1:
                if st.button("✅ نعم، تأكيد", use_container_width=True, type="primary", key="sb_btn_confirm_reset"):
                    reset_settings()
                    st.session_state["_confirm_reset_project"] = False
                    st.success("تمت استعادة القيم الافتراضية بنجاح.")
                    st.rerun()
            with col_rc2:
                if st.button("❌ تراجع", use_container_width=True, key="sb_btn_cancel_reset"):
                    st.session_state["_confirm_reset_project"] = False
                    st.rerun()
        else:
            if st.button("🔄 إعادة ضبط المشروع إلى القيم الافتراضية", use_container_width=True, key="sb_btn_reset_proj"):
                st.session_state["_confirm_reset_project"] = True
                st.rerun()

    # ── Render Top Profile Bar & Selected Module ──────────────────────────
    render_top_profile_bar()

    if "Flat Slabs" in module or "Flat" in module:
        render_flat_slab()
    elif "Columns" in module or "الأعمدة" in module:
        render_columns()
    elif "Footings" in module or "القواعد" in module:
        render_footings()
    elif "Ground Slabs" in module or "الأرضية" in module:
        render_ground_slab()
    elif "اقطار" in module or "Steel" in module:
        render_steel_bars()
    elif "حصر" in module or "Survey" in module:
        render_concrete_survey()
    else:
        render_flat_slab()

# ── GUARANTEED DISK PERSISTENCE ──────────────────────────────────────────────
save_settings()
