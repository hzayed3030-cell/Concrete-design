"""
ECP 203 - Egyptian Code of Practice
Reinforced Concrete Engineering Dashboard
==========================================
Run with:  streamlit run app.py
Last Updated: 2026-09-06 (Module 9 Table Styling Refresh)
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

# ── Load / initialise persistent settings BEFORE any styling or module renders (Single Whistle Alert Active) ─
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
    ALL_MODULES,
    get_project_enabled_modules,
    set_project_enabled_modules,
    # Module soft-delete / restore / creation validation
    check_module_dependencies,
    validate_new_project_module_selection,
    validate_batch_module_deletion,
    play_warning_sound,
    play_strong_whistle_siren,
    play_system_delete_blocked_sound,
    get_deleted_modules_trash,
    soft_delete_module,
    soft_delete_modules_batch,
    restore_module,
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
from modules.two_col_footings import render as render_two_col_footings
from modules.module_9_strap_footing import render_strap_footing_module
from modules.module_10_diagonal_strap import render_diagonal_strap_module
from modules.module_11_ground_beam import render_ground_beam_module
from modules.module_12_brick_survey import render_brick_survey_module
from modules.module_13_standalone_flat_slab import render as render_standalone_flat_slab

# ── CSS Injection: Fixed Unified Typography (75% Compact Scale) ─────────────
st.markdown(
    """
    <style>
    :root {
        /* ═══════════════════════════════════════════════════════════════════════
           BALANCED COMFORTABLE TYPOGRAPHY (75% Compact Scale for Inputs & Outputs)
           ═══════════════════════════════════════════════════════════════════════ */
        --ecp-modules-base-font-size: 12px;
        --ecp-input-font-size: 14.25px;
        --ecp-output-font-size: 14.25px;

        /* Proportional Scales for Module Output Elements (75% Baseline) */
        --ecp-font-size-title: 18.75px;
        --ecp-font-size-h1: 18.75px;
        --ecp-font-size-h2: 16.5px;
        --ecp-font-size-h3: 15px;
        --ecp-font-size-body: 13.5px;
        --ecp-font-size-table-hdr: 13.5px;
        --ecp-font-size-table-cell: 12.75px;
        --ecp-font-size-small: 12px;
        --ecp-font-size-metric-val: 13.5px;
        --ecp-font-size-metric-lbl: 9.75px;
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
        line-height: 1.35 !important;
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
    
    /* ═══════════════════════════════════════════════════════════════════════════
       INPUT GROUP SUB-HEADERS & FIELDSET TITLES (Standalone White Text Only)
       ═══════════════════════════════════════════════════════════════════════════ */
    [data-testid="stMainBlockContainer"] div[data-testid="element-container"]:not(:has([data-testid="stWidgetLabel"])) [data-testid="stMarkdownContainer"] p,
    [data-testid="stMainBlockContainer"] div[data-testid="element-container"]:not(:has([data-testid="stWidgetLabel"])) [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] details > div > div:not(:has([data-testid="stWidgetLabel"])) [data-testid="stMarkdownContainer"] p,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] details > div > div:not(:has([data-testid="stWidgetLabel"])) [data-testid="stMarkdownContainer"] strong {
        font-size: calc(var(--ecp-input-font-size) * 1.08) !important;
        font-weight: 700 !important;
        line-height: 1.4 !important;
        color: #ffffff !important;
        display: block !important;
        margin-top: 14px !important;
        margin-bottom: 10px !important;
        padding-bottom: 2px !important;
    }

    [data-testid="stMainBlockContainer"] div[data-testid="element-container"]:not(:has([data-testid="stWidgetLabel"])):has([data-testid="stMarkdownContainer"] strong) {
        margin-top: 10px !important;
        margin-bottom: 8px !important;
    }

    /* First element inside an expander doesn't need excessive top margin */
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] details > div > div:first-child:not(:has([data-testid="stWidgetLabel"])) [data-testid="stMarkdownContainer"] p,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] details > div > div:first-child:not(:has([data-testid="stWidgetLabel"])) [data-testid="stMarkdownContainer"] strong {
        margin-top: 4px !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       1. FORM INPUT LABELS (GUARANTEED VIBRANT YELLOW: #fde047 / #facc15)
       ═══════════════════════════════════════════════════════════════════════════ */
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"],
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] *,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] label,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] p,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] span,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] div,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] [data-testid="stMarkdownContainer"],
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] [data-testid="stMarkdownContainer"] *,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] [data-testid="stMarkdownContainer"] span,
    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMainBlockContainer"] label[data-testid="stWidgetLabel"] p,
    [data-testid="stMainBlockContainer"] label[data-testid="stWidgetLabel"] span,
    [data-testid="stMainBlockContainer"] .stNumberInput label,
    [data-testid="stMainBlockContainer"] .stNumberInput label *,
    [data-testid="stMainBlockContainer"] .stNumberInput [data-testid="stWidgetLabel"] *,
    [data-testid="stMainBlockContainer"] .stSelectbox label,
    [data-testid="stMainBlockContainer"] .stSelectbox label *,
    [data-testid="stMainBlockContainer"] .stSelectbox [data-testid="stWidgetLabel"] *,
    [data-testid="stMainBlockContainer"] .stTextInput label,
    [data-testid="stMainBlockContainer"] .stTextInput label *,
    [data-testid="stMainBlockContainer"] .stTextInput [data-testid="stWidgetLabel"] *,
    [data-testid="stMainBlockContainer"] .stTextArea label,
    [data-testid="stMainBlockContainer"] .stTextArea label *,
    [data-testid="stMainBlockContainer"] .stTextArea [data-testid="stWidgetLabel"] *,
    [data-testid="stMainBlockContainer"] .stRadio > label,
    [data-testid="stMainBlockContainer"] .stRadio > label *,
    [data-testid="stMainBlockContainer"] .stRadio [data-testid="stWidgetLabel"] *,
    [data-testid="stMainBlockContainer"] .stCheckbox > label,
    [data-testid="stMainBlockContainer"] .stCheckbox > label *,
    [data-testid="stMainBlockContainer"] .stCheckbox [data-testid="stWidgetLabel"] *,
    [data-testid="stMainBlockContainer"] .stSlider label,
    [data-testid="stMainBlockContainer"] .stSlider label *,
    [data-testid="stMainBlockContainer"] .stSlider [data-testid="stWidgetLabel"] *,
    [data-testid="stMainBlockContainer"] .stFileUploader label,
    [data-testid="stMainBlockContainer"] .stFileUploader label *,
    [data-testid="stMainBlockContainer"] .stMultiSelect label,
    [data-testid="stMainBlockContainer"] .stMultiSelect label * {
        font-size: var(--ecp-input-font-size) !important;
        font-weight: 700 !important;
        line-height: 1.25 !important;
        color: #fde047 !important; /* Elegant light yellow */
        margin-top: 0px !important;
        margin-bottom: 2px !important;
        display: inline-block !important;
    }

    /* Checkbox Label Flex Container (Preserve flex and prevent box/text overlap) */
    [data-testid="stMainBlockContainer"] .stCheckbox > label {
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
    }

    [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] {
        margin-bottom: 2px !important;
        margin-top: 2px !important;
        min-height: 0px !important;
    }

    /* Widget Containers Compact Vertical Spacing (Universal Across Modules) */
    [data-testid="stMainBlockContainer"] .stNumberInput,
    [data-testid="stMainBlockContainer"] .stSelectbox,
    [data-testid="stMainBlockContainer"] .stTextInput,
    [data-testid="stMainBlockContainer"] .stTextArea,
    [data-testid="stMainBlockContainer"] .stRadio,
    [data-testid="stMainBlockContainer"] .stCheckbox,
    [data-testid="stMainBlockContainer"] .stSlider,
    [data-testid="stMainBlockContainer"] .stMultiSelect {
        margin-bottom: 2px !important;
        margin-top: 0px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stNumberInput,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stSelectbox,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stTextInput,
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] .stTextArea {
        margin-bottom: 2px !important;
        margin-top: 0px !important;
    }
    [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {
        gap: 0.2rem !important;
    }
    [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"] {
        gap: 0.4rem !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stVerticalBlock"] {
        gap: 0.15rem !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] details {
        padding: 4px 8px !important;
        margin-bottom: 4px !important;
    }

    /* Entered Numbers & Values inside Input Fields */
    [data-testid="stMainBlockContainer"] input,
    [data-testid="stMainBlockContainer"] input[type="number"],
    [data-testid="stMainBlockContainer"] input[type="text"],
    [data-testid="stMainBlockContainer"] div[data-baseweb="input"] input,
    [data-testid="stMainBlockContainer"] .stNumberInput input,
    [data-testid="stMainBlockContainer"] .stTextInput input {
        font-size: var(--ecp-input-font-size) !important;
        min-height: 28px !important;
        height: 28px !important;
        line-height: 28px !important;
        padding-top: 1px !important;
        padding-bottom: 1px !important;
        padding-left: 6px !important;
        padding-right: 6px !important;
    }
    [data-testid="stMainBlockContainer"] div[data-baseweb="input"] {
        min-height: 28px !important;
        height: 28px !important;
    }
    [data-testid="stMainBlockContainer"] textarea,
    [data-testid="stMainBlockContainer"] div[data-baseweb="textarea"] textarea,
    [data-testid="stMainBlockContainer"] .stTextArea textarea {
        font-size: var(--ecp-input-font-size) !important;
        min-height: 44px !important;
        line-height: 1.25 !important;
        padding-top: 3px !important;
        padding-bottom: 3px !important;
    }

    /* Stepper Buttons (+ / -) */
    [data-testid="stMainBlockContainer"] button[data-testid="stNumberInputStepUp"],
    [data-testid="stMainBlockContainer"] button[data-testid="stNumberInputStepDown"] {
        min-height: 14px !important;
        height: 14px !important;
        width: calc(var(--ecp-input-font-size) * 1.5) !important;
        padding: 0px !important;
    }
    [data-testid="stMainBlockContainer"] button[data-testid="stNumberInputStepUp"] svg,
    [data-testid="stMainBlockContainer"] button[data-testid="stNumberInputStepDown"] svg {
        width: calc(var(--ecp-input-font-size) * 0.65) !important;
        height: calc(var(--ecp-input-font-size) * 0.65) !important;
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
        min-height: 28px !important;
    }
    [data-testid="stMainBlockContainer"] div[data-baseweb="select"] > div {
        min-height: 28px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }

    /* Radios & Checkboxes */
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label *,
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] span,
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] p,
    [data-testid="stMainBlockContainer"] div[data-testid="stCheckbox"] label *,
    [data-testid="stMainBlockContainer"] div[data-testid="stCheckbox"] span,
    [data-testid="stMainBlockContainer"] div[data-testid="stCheckbox"] p {
        font-size: var(--ecp-input-font-size) !important;
        line-height: 1.2 !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.35rem !important;
    }

    /* Tabs Styling */
    div[data-baseweb="tab-list"] {
        gap: 4px !important;
    }
    button[data-baseweb="tab"] {
        padding: 5px 12px !important;
    }
    button[data-baseweb="tab"] p,
    button[data-baseweb="tab"] div,
    button[data-baseweb="tab"] span {
        font-size: 13.5px !important;
        font-weight: 700 !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       2. GENERAL UI, RESULTS, TITLES & TABLES
       ═══════════════════════════════════════════════════════════════════════════ */
    
    /* Main Content Top Margin - زيادة الهامش العلوي بعد فتح المشروع بمقدار سطرين لظهور شريط المشروع النشط بوضوح */
    [data-testid="stMainBlockContainer"],
    section.main > div.block-container {
        padding-top: 4.0rem !important;
    }
    
    /* Distinctive Centered Input Section Header (White Background & Black Text) */
    [data-testid="stMainBlockContainer"] .input-section-header,
    [data-testid="stMainBlockContainer"] .input-section-header * {
        font-size: var(--ecp-font-size-h2) !important;
        font-weight: 900 !important;
        line-height: 1.3 !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        text-shadow: none !important;
    }
    [data-testid="stMainBlockContainer"] .input-section-header {
        background: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 10px !important;
        padding: 8px 16px !important;
        margin: 8px 0 6px 0 !important;
        text-align: center !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06) !important;
        text-shadow: none !important;
    }

    /* Section & Output Headers (White Background & Black Text) */
    [data-testid="stMainBlockContainer"] .section-header,
    [data-testid="stMainBlockContainer"] .section-header * {
        font-size: var(--ecp-font-size-h3) !important;
        font-weight: 800 !important;
        line-height: 1.3 !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        text-shadow: none !important;
    }
    [data-testid="stMainBlockContainer"] .section-header {
        background: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        border: 1.5px solid #cbd5e1 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06) !important;
        padding: calc(var(--ecp-output-font-size) * 0.35) calc(var(--ecp-output-font-size) * 0.7) !important;
        border-radius: 8px !important;
        margin: 12px 0 10px 0 !important;
        text-shadow: none !important;
    }

    /* Module Specific Subheaders (White Background & Black Text) */
    .m9-hdr, .m9-subhdr, .m10-hdr, .m11-hdr, .cs-inputs-header-badge,
    .m9-hdr *, .m9-subhdr *, .m10-hdr *, .m11-hdr *, .cs-inputs-header-badge * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    .m9-hdr, .m9-subhdr, .m10-hdr, .m11-hdr, .cs-inputs-header-badge {
        background: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 6px !important;
        padding: 6px 12px !important;
        text-shadow: none !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04) !important;
    }
    [data-testid="stMainBlockContainer"] h1, [data-testid="stMainBlockContainer"] h1 * { font-size: var(--ecp-font-size-h1) !important; font-weight: 700 !important; margin-top: 14px !important; margin-bottom: 10px !important; }
    [data-testid="stMainBlockContainer"] h2, [data-testid="stMainBlockContainer"] h2 * { font-size: var(--ecp-font-size-h2) !important; font-weight: 700 !important; margin-top: 14px !important; margin-bottom: 10px !important; }
    [data-testid="stMainBlockContainer"] h3, [data-testid="stMainBlockContainer"] h3 * { font-size: var(--ecp-font-size-h3) !important; font-weight: 600 !important; margin-top: 14px !important; margin-bottom: 8px !important; }
    [data-testid="stMainBlockContainer"] h4, [data-testid="stMainBlockContainer"] h4 * { font-size: calc(var(--ecp-output-font-size) * 1.05) !important; font-weight: 600 !important; margin-top: 12px !important; margin-bottom: 8px !important; }
    [data-testid="stMainBlockContainer"] h5, [data-testid="stMainBlockContainer"] h5 * { font-size: var(--ecp-output-font-size) !important; font-weight: 600 !important; margin-top: 10px !important; margin-bottom: 6px !important; }

    /* General Body Text outside inputs */
    [data-testid="stMainBlockContainer"] p:not([data-testid="stWidgetLabel"] *),
    [data-testid="stMainBlockContainer"] span:not([data-testid="stWidgetLabel"] *):not([data-baseweb="select"] *),
    [data-testid="stMainBlockContainer"] li,
    [data-testid="stMainBlockContainer"] strong:not([data-testid="stWidgetLabel"] *),
    [data-testid="stMainBlockContainer"] em {
        font-size: var(--ecp-font-size-body);
        line-height: 1.45;
    }

    /* Calculation Tables, DataFrames, Headers & Cell Numbers */
    [data-testid="stMainBlockContainer"] div[data-testid="stTable"],
    [data-testid="stMainBlockContainer"] div[data-testid="stTable"] *,
    [data-testid="stMainBlockContainer"] div[data-testid="stDataFrame"],
    [data-testid="stMainBlockContainer"] div[data-testid="stDataFrame"] *,
    [data-testid="stMainBlockContainer"] .stDataFrame,
    [data-testid="stMainBlockContainer"] .stDataFrame *,
    [data-testid="stMainBlockContainer"] table:not(.ecp-styled-dark-table),
    [data-testid="stMainBlockContainer"] table:not(.ecp-styled-dark-table) *,
    [data-testid="stMainBlockContainer"] table:not(.ecp-styled-dark-table) th,
    [data-testid="stMainBlockContainer"] table:not(.ecp-styled-dark-table) th *,
    [data-testid="stMainBlockContainer"] table:not(.ecp-styled-dark-table) td,
    [data-testid="stMainBlockContainer"] table:not(.ecp-styled-dark-table) td *,
    [data-testid="stMainBlockContainer"] div[data-testid="glide-cell"],
    [data-testid="stMainBlockContainer"] div[data-testid="glide-cell"] *,
    [data-testid="stMainBlockContainer"] .dvn-scroller,
    [data-testid="stMainBlockContainer"] .dvn-scroller * {
        font-size: var(--ecp-font-size-table-cell) !important;
        line-height: 1.35 !important;
    }

    [data-testid="stMainBlockContainer"] table:not(.ecp-styled-dark-table) th,
    [data-testid="stMainBlockContainer"] table:not(.ecp-styled-dark-table) th * {
        font-size: var(--ecp-font-size-table-hdr) !important;
        font-weight: 700 !important;
    }

    /* Metric Cards / Result Summaries */
    [data-testid="stMainBlockContainer"] [data-testid="stMetric"],
    [data-testid="stMainBlockContainer"] div[data-testid="metric-container"] {
        background: #f0f4ff !important;
        border: 1px solid #c8d4f0 !important;
        border-radius: 6px !important;
        padding: 6px 10px !important;
        box-sizing: border-box !important;
        margin-top: 4px !important;
        margin-bottom: 4px !important;
    }

    /* Metric Container Rows & Grids Spacing (Universal Across All Modules) */
    [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]),
    [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"]:has(div[data-testid="metric-container"]),
    [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"]:has(.ecp-metric-box),
    [data-testid="stMainBlockContainer"] div:has(> [data-testid="column"] [data-testid="stMetric"]),
    [data-testid="stMainBlockContainer"] div:has(> [data-testid="column"] .ecp-metric-box) {
        margin-top: 14px !important;
        margin-bottom: 14px !important;
    }

    [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"],
    [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] *,
    [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] > div,
    [data-testid="stMainBlockContainer"] div[data-testid="metric-container"] [data-testid="stMetricValue"],
    [data-testid="stMainBlockContainer"] div[data-testid="metric-container"] [data-testid="stMetricValue"] * {
        font-size: var(--ecp-font-size-metric-val) !important;
        white-space: normal !important;
        overflow: visible !important;
        line-height: 1.2 !important;
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
        line-height: 1.15 !important;
    }

    [data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"],
    [data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"] * {
        font-size: 11.25px !important;
        color: #1d4ed8 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"]:has([data-testid*="stMetricDeltaIcon-Up"]) * {
        color: #16a34a !important;
    }
    [data-testid="stMainBlockContainer"] [data-testid="stMetricDelta"]:has([data-testid*="stMetricDeltaIcon-Down"]) * {
        color: #dc2626 !important;
    }

    /* Result Highlight Cards & Structural Banners */
    [data-testid="stMainBlockContainer"] div[style*="border:2px solid"],
    [data-testid="stMainBlockContainer"] div[style*="border:2px solid"] *,
    [data-testid="stMainBlockContainer"] div[style*="border:3px solid"],
    [data-testid="stMainBlockContainer"] div[style*="border:3px solid"] * {
        font-size: var(--ecp-output-font-size) !important;
        line-height: 1.45;
    }

    [data-testid="stMainBlockContainer"] .result-ok,
    [data-testid="stMainBlockContainer"] .result-warn,
    [data-testid="stMainBlockContainer"] .result-fail {
        display: block !important;
        font-size: var(--ecp-output-font-size) !important;
        line-height: 1.45 !important;
        font-weight: 700 !important;
        padding: 8px 16px !important;
        margin-top: 6px !important;
        margin-bottom: 8px !important;
        border-radius: 8px !important;
        box-sizing: border-box !important;
    }

    [data-testid="stMainBlockContainer"] .result-ok *,
    [data-testid="stMainBlockContainer"] .result-warn *,
    [data-testid="stMainBlockContainer"] .result-fail * {
        font-size: var(--ecp-output-font-size) !important;
        line-height: 1.45 !important;
        font-weight: 700 !important;
    }

    [data-testid="stMainBlockContainer"] .result-ok {
        background: rgba(34, 197, 94, 0.12) !important;
        border: 1.5px solid #22c55e !important;
        color: #15803d !important;
    }
    [data-testid="stMainBlockContainer"] .result-ok * {
        color: #15803d !important;
    }

    [data-testid="stMainBlockContainer"] .result-warn {
        background: rgba(234, 179, 8, 0.12) !important;
        border: 1.5px solid #eab308 !important;
        color: #b45309 !important;
    }
    [data-testid="stMainBlockContainer"] .result-warn * {
        color: #b45309 !important;
    }

    [data-testid="stMainBlockContainer"] .result-fail {
        background: rgba(239, 68, 68, 0.12) !important;
        border: 1.5px solid #ef4444 !important;
        color: #b91c1c !important;
    }
    [data-testid="stMainBlockContainer"] .result-fail * {
        color: #b91c1c !important;
    }

    @media (prefers-color-scheme: dark) {
        [data-testid="stMainBlockContainer"] .result-ok,
        [data-testid="stMainBlockContainer"] .result-ok * {
            color: #4ade80 !important;
            background: rgba(34, 197, 94, 0.20) !important;
        }
        [data-testid="stMainBlockContainer"] .result-warn,
        [data-testid="stMainBlockContainer"] .result-warn * {
            color: #fde047 !important;
            background: rgba(234, 179, 8, 0.20) !important;
        }
        [data-testid="stMainBlockContainer"] .result-fail,
        [data-testid="stMainBlockContainer"] .result-fail * {
            color: #fca5a5 !important;
            background: rgba(239, 68, 68, 0.20) !important;
        }
    }
    [data-theme="dark"] .result-ok, [data-theme="dark"] .result-ok * { color: #4ade80 !important; background: rgba(34, 197, 94, 0.20) !important; }
    [data-theme="dark"] .result-warn, [data-theme="dark"] .result-warn * { color: #fde047 !important; background: rgba(234, 179, 8, 0.20) !important; }
    [data-theme="dark"] .result-fail, [data-theme="dark"] .result-fail * { color: #fca5a5 !important; background: rgba(239, 68, 68, 0.20) !important; }

    /* Separator Lines */
    [data-testid="stMainBlockContainer"] hr {
        margin-top: 14px !important;
        margin-bottom: 14px !important;
    }

    /* Alerts & Notifications - Right-to-Left Arabic Support */
    [data-testid="stMainBlockContainer"] .stAlert,
    [data-testid="stMainBlockContainer"] div[data-testid="stAlert"],
    div[data-testid="stAlert"] {
        direction: rtl !important;
        text-align: right !important;
        padding: calc(var(--ecp-output-font-size) * 0.35) calc(var(--ecp-output-font-size) * 0.65) !important;
        border-radius: 8px !important;
        margin-top: 8px !important;
        margin-bottom: 10px !important;
        unicode-bidi: isolate !important;
    }
    [data-testid="stMainBlockContainer"] .stAlert p,
    [data-testid="stMainBlockContainer"] .stAlert span,
    [data-testid="stMainBlockContainer"] .stAlert div,
    [data-testid="stMainBlockContainer"] .stAlert li,
    [data-testid="stMainBlockContainer"] .stAlert strong,
    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] span,
    div[data-testid="stAlert"] div,
    div[data-testid="stAlert"] strong {
        direction: rtl !important;
        text-align: right !important;
        font-size: var(--ecp-output-font-size) !important;
        line-height: 1.5 !important;
        unicode-bidi: isolate !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       EXPANDER HEADERS (عناوين الأقسام المطوية / Collapsed Sections) - 15.75px BOLD with Background
       ═══════════════════════════════════════════════════════════════════════════ */
    div[data-testid="stExpander"] details summary,
    div[data-testid="stExpander"] summary,
    .stExpander details summary,
    .stExpander summary,
    details summary,
    .streamlit-expanderHeader {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 6px 12px !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04) !important;
        transition: background-color 0.2s ease, border-color 0.2s ease !important;
    }

    div[data-testid="stExpander"] details summary:hover,
    div[data-testid="stExpander"] summary:hover,
    .stExpander summary:hover {
        background: #f8fafc !important;
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
        font-size: 15.75px !important;
        font-weight: 800 !important;
        line-height: 1.35 !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }

    div[data-testid="stExpander"] details summary svg,
    div[data-testid="stExpander"] summary svg,
    .stExpander summary svg,
    details summary svg {
        width: 15px !important;
        height: 15px !important;
        min-width: 15px !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        color: #000000 !important;
    }

    /* Dark Mode Theme Adaptive Rules */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stExpander"] details summary,
        div[data-testid="stExpander"] summary,
        .stExpander summary {
            background: #ffffff !important;
            border-color: #cbd5e1 !important;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05) !important;
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
       PROFILES DASHBOARD & METRIC BOXES THEME-ADAPTIVE STYLING (75% Compact Scale)
       ═══════════════════════════════════════════════════════════════════════════ */
    .profile-card {
        background: #ffffff;
        border: 2px solid #cbd5e1;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        transition: all 0.2s ease;
    }
    .profile-card.active {
        border: 2.5px solid #2563eb !important;
        background: #eff6ff;
    }
    .profile-card-title {
        font-size: 23px;
        font-weight: 800;
        color: #0f172a;
    }
    .profile-card-meta {
        font-size: 17px;
        color: #64748b;
        margin-bottom: 6px;
    }
    .profile-card-specs {
        background: #f8fafc;
        border: 1.5px solid #e2e8f0;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 18px;
        color: #1e293b;
        line-height: 1.5;
        margin-bottom: 8px;
    }
    .profile-card-specs div {
        font-size: 18px !important;
        color: #1e293b !important;
    }
    .profile-card-specs b {
        font-size: 18px !important;
        color: #0f172a !important;
    }

    .ecp-metric-box {
        background: #f8fafc;
        border: 1.5px solid #cbd5e1;
        border-radius: 6px;
        padding: 6px 8px;
        text-align: center;
    }
    .ecp-metric-lbl {
        font-size: 9.75px !important;
        font-weight: 700 !important;
        color: #64748b;
        margin-bottom: 2px !important;
        line-height: 1.2 !important;
    }
    .ecp-metric-val {
        font-size: 13.5px !important;
        font-weight: 800 !important;
        color: #1e40af;
        line-height: 1.2 !important;
    }

    /* Proportional font sizes for all interactive widgets in Profile Manager View */
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) button,
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) button p,
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) button span,
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) label p,
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) div[data-baseweb="select"] span {
        font-size: 1.0rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) input {
        font-size: 1.0rem !important;
        font-weight: 800 !important;
        padding: 6px 10px !important;
    }
    div[data-testid="stAppViewContainer"]:has(.profile-mgr-active-flag) button {
        min-height: 36px !important;
        padding: 6px 12px !important;
    }

    /* Sidebar Profile Manager Font Scale */
    div[data-testid="stSidebar"]:has(.sidebar-profile-mgr-badge) button,
    div[data-testid="stSidebar"]:has(.sidebar-profile-mgr-badge) button p,
    div[data-testid="stSidebar"]:has(.sidebar-profile-mgr-badge) button span {
        font-size: 0.95rem !important;
        font-weight: 800 !important;
        min-height: 36px !important;
    }
    div[data-testid="stSidebar"]:has(.sidebar-profile-mgr-badge) small {
        font-size: 14px !important;
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
        font-size: 13.5px !important;
        font-weight: 800 !important;
        padding: 6px 16px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stStatusWidget"] button:hover {
        background: #ef4444 !important;
        color: #ffffff !important;
        box-shadow: 0 0 16px rgba(239, 68, 68, 0.6) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       GLOBAL PROJECT NAME (اسم المشروع) LUXURY CENTERED STYLING (75% Compact Scale)
       ═══════════════════════════════════════════════════════════════════════════ */
    
    /* Target ANY Project Name Text Input container across ALL modules and forms */
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]),
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) {
        text-align: center !important;
        margin: 2px auto 6px auto !important;
        width: 100% !important;
        background: linear-gradient(135deg, #0b1329 0%, #1e293b 50%, #0b1329 100%) !important;
        border: 2px solid #fbbf24 !important;
        border-radius: 10px !important;
        padding: 4px 12px 6px 12px !important;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.6), 0 0 14px rgba(251, 191, 36, 0.2) !important;
    }

    /* Target the Label */
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]) label,
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) label,
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]) label p,
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) label p,
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]) [data-testid="stWidgetLabel"] p,
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) [data-testid="stWidgetLabel"] p {
        font-size: 1.20rem !important;
        font-weight: 900 !important;
        color: #fbbf24 !important;
        text-align: center !important;
        display: block !important;
        width: 100% !important;
        margin: 0 auto 2px auto !important;
        line-height: 1.2 !important;
        text-shadow: 0 0 12px rgba(251, 191, 36, 0.45) !important;
        letter-spacing: 0.4px !important;
    }

    /* Target the Input Box (Distinctive Luminous Cyan / Sky Blue Text) */
    div[data-testid="stTextInput"]:has(input[aria-label*="Project Name"]) input,
    div[data-testid="stTextInput"]:has(input[aria-label*="اسم المشروع"]) input {
        font-size: 1.24rem !important;
        font-weight: 900 !important;
        color: #38bdf8 !important;
        background: #080f1d !important;
        border: 1.8px solid #38bdf8 !important;
        border-radius: 6px !important;
        padding: 4px 10px !important;
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
            root.style.setProperty('--ecp-modules-base-font-size', '12px');
            root.style.setProperty('--ecp-input-font-size', '14.25px');
            root.style.setProperty('--ecp-output-font-size', '14.25px');
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

def render_custom_html(html_str: str) -> None:
    """Render HTML safely without markdown indentation or pre-code issues."""
    clean_lines = [
        line.strip() for line in html_str.splitlines()
        if line.strip() and not line.strip().startswith("<!--")
    ]
    clean_html = "".join(clean_lines)
    if hasattr(st, "html"):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)


def render_delete_alarm_beep() -> None:
    """
    Centralized Delete Blocked Alarm:
    Invokes the multi-layer play_warning_sound() mechanism across browser and host OS.
    """
    play_warning_sound()


def render_top_profile_bar():
    """Top navigation banner displayed when viewing design modules."""
    active_pname = get_active_project_name()
    all_projects = list(get_all_projects().keys())
    if active_pname not in all_projects and all_projects:
        active_pname = all_projects[0]

    render_custom_html(
        f"""
        <div style="background: linear-gradient(135deg, #0b1329 0%, #1e293b 50%, #0b1329 100%); border: 1px solid rgba(56, 189, 248, 0.40); border-radius: 8px; padding: 4px 14px; margin-top: 8px; margin-bottom: 8px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; min-height: 32px;">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span style="font-size: 18px; filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.4)); line-height: 1;">🏗️</span>
                <span style="font-size: 12px; font-weight: 700; color: #94a3b8;">المشروع النشط:</span>
                <span style="font-size: 15px; font-weight: 900; color: #38bdf8; text-shadow: 0 0 8px rgba(56, 189, 248, 0.35);">📁 {active_pname}</span>
                <span style="background: rgba(34, 197, 94, 0.18); color: #4ade80; border: 1px solid #22c55e; padding: 1px 9px; border-radius: 12px; font-size: 11.5px; font-weight: 800; line-height: 1.4;">🟢 متزامن</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #cbd5e1; font-weight: 700;">
                <span style="background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.30); padding: 2px 10px; border-radius: 6px; color: #38bdf8;">📐 ECP 203</span>
                <span style="background: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.30); padding: 2px 10px; border-radius: 6px; color: #fbbf24;">⚖️ ton·m·cm</span>
            </div>
        </div>
        """
    )


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

    # ── Centered Distinctive Header Banner ──
    render_custom_html(
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
        """
    )

    # ── Global Actions Toolbar (Compact) ────────────────────────────────────
    g1, g2, g3, g4, g5 = st.columns([1.1, 1.1, 1.3, 1.3, 1.3])
    with g1:
        if st.button("➕ مشروع جديد", use_container_width=True, type="primary", key="btn_global_new"):
            is_open = st.session_state.get("show_create_profile_form", False)
            st.session_state["show_create_profile_form"] = not is_open
            st.session_state["_new_proj_step"] = 1
            st.session_state["show_import_profile_form"] = False
            st.session_state["show_git_update_form"] = False
            if not is_open:
                st.session_state.pop("_new_proj_saved_name", None)
                st.session_state.pop("_new_proj_selected_indices", None)
                for m in ALL_MODULES:
                    st.session_state.pop(f"chk_new_proj_{m['idx']}", None)
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

    # ── Create New Project Form (Enhanced 2-Step Workflow with Dependency Validation) ──
    if st.session_state.get("show_create_profile_form", False):
        col_cf_pad1, col_cf_center, col_cf_pad2 = st.columns([0.5, 7.0, 0.5])
        with col_cf_center:
            with st.container(border=True):
                st.markdown(
                    """
                    <style>
                    div.new-project-box div[data-testid="stTextInput"] label,
                    div.new-project-box div[data-testid="stTextInput"] label p {
                        font-size: 1.40rem !important;
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
                        font-size: 1.45rem !important;
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
                            margin-bottom: 12px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            gap: 10px;
                            border: 1.5px solid #fbbf24;
                            box-shadow: 0 0 16px rgba(251, 191, 36, 0.35);
                        ">
                            <span style="font-size: 24px;">✨</span>
                            <span style="color: #ffffff !important; font-size: 20px; font-weight: 900;">إنشاء مشروع إنشائي جديد — New Project</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Track workflow step (Step 1: Selection & Check, Step 2: Confirmation & Default Values)
                curr_step = st.session_state.get("_new_proj_step", 1)

                if curr_step == 1:
                    # ── Step 1: Project Name & Module Selection ──────────────────────
                    st.markdown('<div class="new-project-box">', unsafe_allow_html=True)
                    new_p_name = st.text_input(
                        "اسم المشروع الجديد (Project Name):",
                        value=st.session_state.get("_new_proj_saved_name", f"مشروع {len(projects) + 1}"),
                        placeholder="أدخل اسم المشروع (مثلاً: حصر الخرسانات، برج النور...)",
                        key="input_new_project_name",
                    )
                    st.session_state["_new_proj_saved_name"] = new_p_name
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown(
                        """
                        <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border: 1.5px solid #818cf8; border-radius: 10px; padding: 12px 18px; margin: 10px 0 12px 0;">
                            <div style="font-weight: 900; font-size: 17px; color: #ffffff; display: flex; align-items: center; gap: 8px;">
                                <span>🎛️</span> New Project – Select Modules (تحديد الموديولات للمشروع الجديد)
                            </div>
                            <div style="font-size: 14px; color: #cbd5e1; margin-top: 4px; font-weight: 600;">
                                Please select the Modules you want to open in this new Project. (يرجى اختيار الموديولات التي ترغب في تفعيلها وفتحها في هذا المشروع الجديد).
                            </div>
                        </div>
                        <style>
                        /* ── New Project Module Selection Checkbox Cards & Text Wrap (Compact) ── */
                        [data-testid="stMainBlockContainer"] div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(div[class*="st-key-chk_new_proj_"]) {
                            gap: 4px !important;
                        }
                        [data-testid="stMainBlockContainer"] div[data-testid="stColumn"]:has(div[class*="st-key-chk_new_proj_"]) div[data-testid="stVerticalBlock"] {
                            gap: 4px !important;
                        }
                        [data-testid="stMainBlockContainer"] div[class*="st-key-chk_new_proj_"] {
                            background: rgba(15, 23, 42, 0.65) !important;
                            border: 1.2px solid rgba(148, 163, 184, 0.25) !important;
                            border-radius: 8px !important;
                            padding: 4px 10px !important;
                            margin-bottom: 4px !important;
                            min-height: 38px !important;
                            display: flex !important;
                            align-items: center !important;
                            box-sizing: border-box !important;
                            transition: all 0.2s ease-in-out !important;
                        }
                        [data-testid="stMainBlockContainer"] div[class*="st-key-chk_new_proj_"]:hover {
                            background: rgba(30, 27, 75, 0.75) !important;
                            border-color: #818cf8 !important;
                            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.25) !important;
                        }
                        [data-testid="stMainBlockContainer"] div[class*="st-key-chk_new_proj_"] div[data-baseweb="checkbox"],
                        [data-testid="stMainBlockContainer"] div[class*="st-key-chk_new_proj_"] label[data-baseweb="checkbox"] {
                            margin: 0 !important;
                            padding: 0 !important;
                        }
                        [data-testid="stMainBlockContainer"] div[class*="st-key-chk_new_proj_"] > label {
                            display: flex !important;
                            flex-direction: row !important;
                            align-items: center !important;
                            gap: 8px !important;
                            width: 100% !important;
                            margin: 0 !important;
                            padding: 0 !important;
                            cursor: pointer !important;
                        }
                        [data-testid="stMainBlockContainer"] div[class*="st-key-chk_new_proj_"] label div[data-testid="stMarkdownContainer"] {
                            flex: 1 1 auto !important;
                            min-width: 0 !important;
                            width: 100% !important;
                            white-space: normal !important;
                            word-break: break-word !important;
                            overflow-wrap: break-word !important;
                        }
                        [data-testid="stMainBlockContainer"] div[class*="st-key-chk_new_proj_"] label div[data-testid="stMarkdownContainer"] p,
                        [data-testid="stMainBlockContainer"] div[class*="st-key-chk_new_proj_"] label span {
                            white-space: normal !important;
                            word-break: break-word !important;
                            overflow-wrap: break-word !important;
                            line-height: 1.24 !important;
                            font-size: 12.8px !important;
                            font-weight: 700 !important;
                            color: #f1f5f9 !important;
                            margin: 0 !important;
                            padding: 0 !important;
                            display: block !important;
                            unicode-bidi: plaintext !important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Quick Select / Deselect Toolbar
                    c_sel_all, c_desel_all, _ = st.columns([1.5, 1.8, 4.7])
                    with c_sel_all:
                        if st.button("☑️ تحديد الكل", key="btn_new_proj_sel_all", use_container_width=True):
                            for m in ALL_MODULES:
                                st.session_state[f"chk_new_proj_{m['idx']}"] = True
                            st.rerun()
                    with c_desel_all:
                        if st.button("🔄 إلغاء تحديد الكل", key="btn_new_proj_desel_all", use_container_width=True):
                            for m in ALL_MODULES:
                                st.session_state[f"chk_new_proj_{m['idx']}"] = False
                            st.rerun()

                    # Grid of Module Checkboxes
                    grid_del_cols = 2
                    del_cols = st.columns(grid_del_cols)
                    selected_module_indices = []

                    for ci, mod in enumerate(ALL_MODULES):
                        default_val = st.session_state.get(f"chk_new_proj_{mod['idx']}", True)
                        with del_cols[ci % grid_del_cols]:
                            is_checked = st.checkbox(
                                mod["name"],
                                value=default_val,
                                key=f"chk_new_proj_{mod['idx']}",
                            )
                            if is_checked:
                                selected_module_indices.append(mod["idx"])

                    # ── Live Dependency Validation ─────────────────────────────
                    is_valid_sel, sel_violations = validate_new_project_module_selection(selected_module_indices)

                    if not is_valid_sel:
                        violation_items_html = "".join([
                            f"""<li style="margin: 6px 0; color: #ffffff; font-size: 15px;">
                                ⚠️ <b>{v.get('message', '')}</b>
                                {f"<div style='color: #fecaca; font-size: 13px; margin-top: 2px;'>🔗 طبيعة الاعتمادية: {v['relationship']}</div>" if 'relationship' in v else ''}
                            </li>"""
                            for v in sel_violations
                        ])

                        st.markdown(
                            f"""
                            <div style="background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 50%, #3f0a0a 100%); border: 2.5px solid #ef4444; border-radius: 12px; padding: 16px 20px; margin: 14px 0 10px 0; box-shadow: 0 6px 25px rgba(239, 68, 68, 0.40);">
                                <div style="color: #ffffff; font-weight: 900; font-size: 18px; display: flex; align-items: center; gap: 10px; border-bottom: 1.5px solid rgba(239, 68, 68, 0.6); padding-bottom: 8px;">
                                    <span style="font-size: 24px;">⛔</span>
                                    <span>اختيار الموديولات غير مسموح — MODULE SELECTION NOT ALLOWED</span>
                                </div>
                                <div style="margin-top: 10px;">
                                    <ul style="margin: 0; padding-right: 20px; list-style: disc;">
                                        {violation_items_html}
                                    </ul>
                                </div>
                                <div style="color: #fef08a; font-size: 13.5px; font-weight: 700; margin-top: 10px; background: rgba(0, 0, 0, 0.35); padding: 8px 12px; border-radius: 6px; border-right: 4px solid #fef08a;">
                                    ℹ️ <b>تعليمات الارتباط الهندسي:</b> يرجى اختيار الموديولات المرتبطة معاً أو إلغاء اختيارهما معاً (Please select both Modules or deselect both Modules).
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Action Buttons in Step 1
                    c_next, c_cancel, _ = st.columns([1.8, 1.2, 5.0])
                    with c_next:
                        btn_next_disabled = not is_valid_sel or not new_p_name.strip()
                        if st.button(
                            "➡️ متابعة والتأكيد (Next)",
                            type="primary",
                            use_container_width=True,
                            disabled=btn_next_disabled,
                            help="انتقل إلى شاشة تأكيد الموديولات وبدء المشروع" if not btn_next_disabled else "يرجى تصحيح اختيار الموديولات وإدخال اسم المشروع أولاً",
                        ):
                            st.session_state["_new_proj_selected_indices"] = selected_module_indices
                            st.session_state["_new_proj_step"] = 2
                            st.rerun()
                    with c_cancel:
                        if st.button("❌ إلغاء", key="btn_cancel_step1", use_container_width=True):
                            st.session_state["show_create_profile_form"] = False
                            st.session_state["_new_proj_step"] = 1
                            st.session_state.pop("_new_proj_saved_name", None)
                            st.session_state.pop("_new_proj_selected_indices", None)
                            for m in ALL_MODULES:
                                st.session_state.pop(f"chk_new_proj_{m['idx']}", None)
                            st.rerun()

                elif curr_step == 2:
                    # ── Step 2: Confirmation & Default Values Initialization ────────
                    p_name_final = st.session_state.get("_new_proj_saved_name", f"مشروع {len(projects) + 1}").strip()
                    chosen_indices = st.session_state.get("_new_proj_selected_indices", [0])

                    # 1. New Project Confirmation Card
                    selected_mods_html = "".join([
                        f"""<li style="margin: 3px 0; color: #ffffff; font-size: 13.5px; display: flex; align-items: center; gap: 8px; line-height: 1.25; word-break: break-word;">
                            <span style="color: #4ade80; font-size: 16px; line-height: 1;">✓</span>
                            <span style="flex: 1; word-break: break-word;">{m['name']}</span>
                        </li>"""
                        for m in ALL_MODULES if m["idx"] in chosen_indices
                    ])

                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, #064e3b 0%, #065f46 100%); border: 2px solid #34d399; border-radius: 12px; padding: 18px 22px; margin-bottom: 12px; box-shadow: 0 4px 20px rgba(52, 211, 153, 0.25);">
                            <div style="font-weight: 900; font-size: 19px; color: #ffffff; display: flex; align-items: center; gap: 10px; border-bottom: 1.5px solid rgba(52, 211, 153, 0.4); padding-bottom: 8px;">
                                <span style="font-size: 22px;">📋</span>
                                <span>New Project Confirmation (تأكيد إنشاء المشروع)</span>
                            </div>
                            <div style="color: #d1fae5; font-size: 16px; font-weight: 700; margin: 10px 0 6px 0;">
                                اسم المشروع: <b style="color: #fef08a; font-size: 18px;">«{p_name_final}»</b>
                            </div>
                            <div style="color: #ffffff; font-size: 14.5px; font-weight: 600; margin-bottom: 8px;">
                                The following Modules will be opened in the new Project (الموديولات التي سيتم فتحها وتفعيلها في المشروع):
                            </div>
                            <div style="background: rgba(0, 0, 0, 0.25); border-radius: 8px; padding: 10px 16px;">
                                <ul style="margin: 0; padding: 0; list-style: none;">
                                    {selected_mods_html}
                                </ul>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # 2. Explanatory Message about Default Values (⚠️ New Modules Initialization)
                    st.markdown(
                        """
                        <div style="background: linear-gradient(135deg, #0c2d48 0%, #145da0 100%); border: 2px solid #38bdf8; border-radius: 12px; padding: 18px 22px; margin-bottom: 16px; box-shadow: 0 4px 20px rgba(56, 189, 248, 0.25);">
                            <div style="color: #38bdf8; font-weight: 900; font-size: 18px; display: flex; align-items: center; gap: 10px; border-bottom: 1.5px solid rgba(56, 189, 248, 0.4); padding-bottom: 8px;">
                                <span style="font-size: 22px;">⚠️</span>
                                <span>New Modules Initialization (بدء الموديولات بالقيم الافتراضية)</span>
                            </div>
                            <div style="color: #f0f9ff; font-size: 14.5px; line-height: 1.7; margin-top: 10px; font-weight: 500;">
                                <p style="margin: 4px 0;">• <b>The selected Modules will be opened with their initial default values and recommended starting parameters provided by the system.</b></p>
                                <p style="margin: 4px 0; color: #bae6fd;">• <i>These are only default/initial values and do not represent final project inputs or design results.</i></p>
                                <p style="margin: 4px 0;">• <b>After entering the actual project inputs, the Modules will perform the required calculations and design according to the applicable design code (ECP 203), calculation procedures, and design steps implemented in the system.</b></p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Action Buttons in Step 2
                    c_create, c_back, c_cancel2, _ = st.columns([2.2, 1.6, 1.2, 3.0])
                    with c_create:
                        if st.button("🚀 إنشاء المشروع وتفعيله (Create Project)", type="primary", use_container_width=True, key="btn_confirm_create_proj"):
                            # Clean Creation: strictly using ECP_DEFAULTS (copy_from=None)
                            created_name = create_project(p_name_final, copy_from=None, enabled_modules=chosen_indices)
                            set_project_enabled_modules(created_name, chosen_indices)
                            st.session_state["show_create_profile_form"] = False
                            st.session_state["_new_proj_step"] = 1
                            st.session_state.pop("_new_proj_saved_name", None)
                            st.session_state.pop("_new_proj_selected_indices", None)
                            for m in ALL_MODULES:
                                st.session_state.pop(f"chk_new_proj_{m['idx']}", None)
                            st.session_state["nav_view"] = "module"
                            st.session_state["in_module"] = True
                            st.session_state["selected_module_idx"] = chosen_indices[0]
                            st.success(f"✅ تم إنشاء وتفعيل المشروع الجديد «{created_name}» بنجاح!")
                            st.rerun()
                    with c_back:
                        if st.button("↩️ تعديل الاختيار (Back)", use_container_width=True, key="btn_back_step1"):
                            st.session_state["_new_proj_step"] = 1
                            st.rerun()
                    with c_cancel2:
                        if st.button("❌ إلغاء", key="btn_cancel_step2", use_container_width=True):
                            st.session_state["show_create_profile_form"] = False
                            st.session_state["_new_proj_step"] = 1
                            st.session_state.pop("_new_proj_saved_name", None)
                            st.session_state.pop("_new_proj_selected_indices", None)
                            for m in ALL_MODULES:
                                st.session_state.pop(f"chk_new_proj_{m['idx']}", None)
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

    # ── Delete Confirmation Dialog (ENLARGED + WARNING BEEP) ───────────────
    if st.session_state.get("_profile_to_delete"):
        del_target = st.session_state["_profile_to_delete"]
        # Trigger strong emergency warning whistle / siren before the confirmation message
        if st.session_state.get("_play_strong_whistle_now", True):
            play_strong_whistle_siren()
            st.session_state["_play_strong_whistle_now"] = False
        st.markdown(
            f"""
            <div dir="rtl" style="background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 50%, #3f0a0a 100%); border: 3.5px solid #ef4444; border-radius: 14px; padding: 22px 26px; margin: 12px 0 16px 0; box-shadow: 0 10px 35px rgba(239, 68, 68, 0.45); text-align: right;">
                <div style="color: #ffffff; font-weight: 900; font-size: 24px; margin-bottom: 12px; display: flex; align-items: center; gap: 12px; border-bottom: 2px solid rgba(239, 68, 68, 0.6); padding-bottom: 10px;">
                    <span style="font-size: 32px;">🚨</span>
                    <span>تأكيد حذف المشروع بالكامل — DELETE PROJECT CONFIRMATION</span>
                </div>
                <div style="font-size: 20px; color: #fef08a; font-weight: 900; line-height: 1.7; margin-bottom: 10px;">
                    ⚠️ سيتم حذف المشروع بالكامل بجميع البيانات والموديولات  !
                </div>
                <div style="font-size: 17px; color: #fee2e2; font-weight: 700; line-height: 1.6; margin-bottom: 12px;">
                    المشروع المستهدف بالحذف: <b style="color: #ffffff; font-size: 20px; text-decoration: underline;">«{del_target}»</b>
                </div>
                <div style="background: rgba(0, 0, 0, 0.45); border: 1.5px solid rgba(254, 202, 202, 0.3); border-radius: 8px; padding: 12px 18px; color: #fca5a5; font-size: 15px; font-weight: 700;">
                    🚨 <b>تحذير:</b> سيتم حذف ملفات المشروع وجميع الحسابات والتصميمات الخاصة به بشكل نهائي.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_in_sure, col_btn_sure, col_btn_cancel = st.columns([3.4, 2.2, 1.4])
        with col_in_sure:
            sure_text = st.text_input(
                'اكتب العبارة "I am sure" لتأكيد حذف المشروع:',
                key=f"input_sure_del_proj_{del_target}",
                placeholder="I am sure",
                help="اكتب العبارة بدقة لتفعيل زر حذف المشروع النهائي",
            )
        is_sure_matched = (sure_text or "").strip().lower() == "i am sure"

        with col_btn_sure:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button(
                "🗑️ نعم، احذف المشروع",
                key=f"btn_confirm_del_proj_{del_target}",
                use_container_width=True,
                type="primary",
                disabled=not is_sure_matched,
            ):
                delete_project(del_target)
                st.session_state["_profile_to_delete"] = None
                st.session_state.pop("_play_strong_whistle_now", None)
                st.session_state.pop(f"input_sure_del_proj_{del_target}", None)
                st.success(f"✅ تم حذف المشروع «{del_target}» بالكامل بنجاح.")
                st.rerun()

        with col_btn_cancel:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("❌ تراجع / إلغاء", key=f"btn_cancel_del_proj_{del_target}", use_container_width=True):
                st.session_state["_profile_to_delete"] = None
                st.session_state.pop("_play_strong_whistle_now", None)
                st.session_state.pop(f"input_sure_del_proj_{del_target}", None)
                st.rerun()

        if not is_sure_matched:
            st.caption("💡 اكتب **I am sure** في الحقل أعلاه لتفعيل زر الحذف النهائي للمشروع.")

        st.markdown("<hr style='margin:6px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)

    # ── CSS for Project Manager: Active Project Card (Green Theme) & Saved Projects Directory ─────────
    render_custom_html(
        """
        <style>
        /* ── Top Pinned Active Project Card (Calm Light Mint Green Theme) ── */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-active) {
            border: 2.5px solid #059669 !important;
            border-radius: 14px !important;
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 45%, #bbf7d0 100%) !important;
            box-shadow: 0 6px 24px rgba(5, 150, 105, 0.20), 0 0 14px rgba(16, 185, 129, 0.12) !important;
            padding: 14px 18px 16px 18px !important;
            margin-bottom: 20px !important;
            transition: all 0.25s ease-in-out !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-active):hover {
            border-color: #047857 !important;
            box-shadow: 0 8px 30px rgba(5, 150, 105, 0.32), 0 0 18px rgba(16, 185, 129, 0.22) !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-active) > div[data-testid="stVerticalBlock"] {
            background: transparent !important;
        }

        /* Distinct styling for primary button inside Active Project Card */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-active) button[kind="primary"] {
            background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
            border: 1.5px solid #047857 !important;
            color: #ffffff !important;
            font-weight: 900 !important;
            box-shadow: 0 2px 8px rgba(5, 150, 105, 0.30) !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-active) button[kind="primary"]:hover {
            background: linear-gradient(135deg, #047857 0%, #064e3b 100%) !important;
            box-shadow: 0 4px 14px rgba(5, 150, 105, 0.45) !important;
        }

        /* Distinct styling for secondary buttons and download button inside Active Project Card */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-active) button[kind="secondary"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-active) [data-testid="stDownloadButton"] button {
            background: #ffffff !important;
            border: 1.5px solid #059669 !important;
            color: #064e3b !important;
            font-weight: 800 !important;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
            transition: all 0.2s ease !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-active) button[kind="secondary"]:hover,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-active) [data-testid="stDownloadButton"] button:hover {
            background: #ecfdf5 !important;
            border-color: #047857 !important;
            color: #047857 !important;
            box-shadow: 0 3px 10px rgba(5, 150, 105, 0.25) !important;
        }

        /* Distinct Delete Project button */
        div[class*="st-key-btn_del_"] button {
            border-color: #ef4444 !important;
            color: #dc2626 !important;
        }
        div[class*="st-key-btn_del_"] button:hover {
            background: #fef2f2 !important;
            border-color: #b91c1c !important;
            color: #b91c1c !important;
            box-shadow: 0 3px 10px rgba(239, 68, 68, 0.25) !important;
        }

        /* ── Saved Projects Cards - Dark (Odd items) ── */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-saved.project-box-dark),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-saved):has(.project-box-dark) {
            border: 1.8px solid rgba(148, 163, 184, 0.25) !important;
            border-radius: 12px !important;
            background: linear-gradient(135deg, #090d16 0%, #0f172a 60%, #1e293b 100%) !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.40) !important;
            padding: 10px 14px !important;
            margin-bottom: 8px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-saved.project-box-dark):hover,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-saved):has(.project-box-dark):hover {
            border-color: #38bdf8 !important;
            box-shadow: 0 6px 22px rgba(0, 0, 0, 0.55), 0 0 14px rgba(56, 189, 248, 0.25) !important;
        }

        /* ── Saved Projects Cards - Light Gray (Even items) ── */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-saved.project-box-light),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-saved):has(.project-box-light) {
            border: 1.8px solid rgba(15, 23, 42, 0.35) !important;
            border-radius: 12px !important;
            background: linear-gradient(135deg, #94a3b8 0%, #64748b 50%, #475569 100%) !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
            padding: 10px 14px !important;
            margin-bottom: 8px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-saved.project-box-light):hover,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-saved):has(.project-box-light):hover {
            border-color: #38bdf8 !important;
            box-shadow: 0 6px 22px rgba(0, 0, 0, 0.35), 0 0 14px rgba(56, 189, 248, 0.30) !important;
        }

        /* Ensure inner vertical block doesn't set conflicting background */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.project-box-saved) > div[data-testid="stVerticalBlock"] {
            background: transparent !important;
        }

        /* ── Set Active Button Styling ── */
        div[class*="st-key-btn_set_active_"] button {
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            color: #ffffff !important;
            border: 1.5px solid #38bdf8 !important;
            font-weight: 800 !important;
            font-size: 13.5px !important;
            border-radius: 8px !important;
            padding: 6px 10px !important;
            transition: all 0.2s ease !important;
        }
        div[class*="st-key-btn_set_active_"] button:hover {
            background: linear-gradient(135deg, #0369a1 0%, #075985 100%) !important;
            border-color: #7dd3fc !important;
            box-shadow: 0 3px 12px rgba(56, 189, 248, 0.45) !important;
            transform: translateY(-1px) !important;
        }
        </style>
        """
    )

    all_pnames = list(projects.keys())
    if not all_pnames:
        st.info("ℹ️ لا توجد مشاريع مسجلة حالياً. يمكنك إنشاء أول مشروع عبر زر «➕ مشروع جديد» بالأعلى.")
        return

    # Ensure active_name is valid and exists in projects
    if active_name not in all_pnames and all_pnames:
        active_name = all_pnames[0]
        set_active_project(active_name)

    ACCENT_PALETTE = [
        {"accent": "#0ea5e9", "bg": "rgba(14, 165, 233, 0.12)", "border": "rgba(14, 165, 233, 0.40)", "tag": "#38bdf8"},  # Sky Cyan
        {"accent": "#a855f7", "bg": "rgba(168, 85, 247, 0.12)", "border": "rgba(168, 85, 247, 0.40)", "tag": "#c084fc"},  # Purple
        {"accent": "#f59e0b", "bg": "rgba(245, 158, 11, 0.12)", "border": "rgba(245, 158, 11, 0.40)", "tag": "#fbbf24"},  # Amber
        {"accent": "#14b8a6", "bg": "rgba(20, 184, 166, 0.12)", "border": "rgba(20, 184, 166, 0.40)", "tag": "#2dd4bf"},  # Teal
        {"accent": "#6366f1", "bg": "rgba(99, 102, 241, 0.12)", "border": "rgba(99, 102, 241, 0.40)", "tag": "#818cf8"},  # Indigo
        {"accent": "#f43f5e", "bg": "rgba(244, 63, 94, 0.12)", "border": "rgba(244, 63, 94, 0.40)", "tag": "#fb7185"},   # Rose
    ]

    # ── SECTION 1: ACTIVE PROJECT (PINNED AT THE TOP IN GREEN) ──────────────
    st.markdown(
        "<div style='margin:10px 0 8px 0; font-weight: 800; font-size: 18px; color: #4ade80; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;'>"
        "<span>🟢 المشروع الحالي النشط (Active Project):</span>"
        "<span style='font-size: 12.5px; font-weight: 800; color: #4ade80; background: rgba(34, 197, 94, 0.15); padding: 3px 12px; border-radius: 8px; border: 1px solid rgba(34, 197, 94, 0.4);'>⭐ Pinned Active</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    pname = active_name
    summary = get_project_summary(pname)
    safe_pname = get_safe_project_filename_prefix(pname)
    project_json_str = export_project_json(pname)
    p_updated = summary.get("updated_at", "-")
    p_last_used = summary.get("last_used_at", p_updated)
    enabled_mods = get_project_enabled_modules(pname)

    # Detect clone/copy count
    copy_count = pname.count("(نسخة)")
    if copy_count >= 2:
        copy_badge_html = f'<span style="background: rgba(245, 158, 11, 0.22); color: #92400e; border: 1.5px solid #d97706; padding: 2px 9px; border-radius: 6px; font-size: 12px; font-weight: 800;">📋 نسخة مكررة ({copy_count})</span>'
    elif copy_count == 1:
        copy_badge_html = '<span style="background: rgba(245, 158, 11, 0.18); color: #b45309; border: 1.5px solid #d97706; padding: 2px 9px; border-radius: 6px; font-size: 12px; font-weight: 800;">📋 نسخة</span>'
    else:
        copy_badge_html = ""

    # Modules badge
    if len(enabled_mods) < len(ALL_MODULES):
        short_names = ", ".join([ALL_MODULES[i]["short"] for i in enabled_mods if i in range(len(ALL_MODULES))])
        custom_badge_html = f'<span style="background: rgba(245, 158, 11, 0.18); color: #b45309; border: 1.5px solid #f59e0b; padding: 3px 10px; border-radius: 14px; font-size: 12.5px; font-weight: 800;">🎛️ مخصص ({len(enabled_mods)}): {short_names}</span>'
    else:
        custom_badge_html = '<span style="background: rgba(2, 132, 199, 0.15); color: #0369a1; border: 1.5px solid #0284c7; padding: 3px 10px; border-radius: 14px; font-size: 12px; font-weight: 800;">🧩 كافة الموديولات (12)</span>'

    p_last_used_clean = p_last_used[:16] if p_last_used and len(p_last_used) >= 16 else (p_last_used or "-")
    p_updated_clean = p_updated[:16] if p_updated and len(p_updated) >= 16 else (p_updated or "-")

    last_used_pill_html = f'''<div style="color: #94a3b8; display: inline-flex; align-items: center; gap: 5px; font-size: 13px; text-shadow: 0 1px 2px rgba(0,0,0,0.85);">
        <span style="font-weight: 700;">🕒 آخر تشغيل:</span>
        <span style="font-weight: 800; font-family: monospace;">{p_last_used_clean}</span>
    </div>'''

    if p_last_used_clean != p_updated_clean and p_updated_clean != "-":
        updated_pill_html = f'''<div style="color: #94a3b8; display: inline-flex; align-items: center; gap: 5px; font-size: 13px; text-shadow: 0 1px 2px rgba(0,0,0,0.85);">
            <span style="font-weight: 700;">✏️ آخر تعديل:</span>
            <span style="font-weight: 800; font-family: monospace;">{p_updated_clean}</span>
        </div>'''
    else:
        updated_pill_html = ""

    with st.container(border=True):
        row_html = f"""<div class="project-box-active">
            <div style="
                background: transparent;
                border-radius: 8px;
                border-right: 7px solid #059669;
                padding: 4px 12px 10px 12px;
                margin-bottom: 12px;
                border-bottom: 1.5px solid rgba(5, 150, 105, 0.25);
            ">
                <!-- Top Row: Number Badge, Project Title, Copy Badge & Status Badges -->
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                        <span style="background: linear-gradient(135deg, #059669 0%, #047857 100%); color: #ffffff; font-weight: 900; font-size: 13.5px; padding: 3px 10px; border-radius: 6px; border: 1.5px solid #047857; letter-spacing: 0.5px;">★ المشروع النشط</span>
                        <span style="font-size: 21px; font-weight: 900; color: #fde047; letter-spacing: 0.3px; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45), 0 0 1px rgba(0, 0, 0, 0.5);">⭐ 🏗️ {pname}</span>
                        {copy_badge_html}
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span style="background: rgba(5, 150, 105, 0.15); color: #065f46; border: 1.5px solid #059669; padding: 3px 12px; border-radius: 16px; font-size: 13px; font-weight: 800; display: inline-flex; align-items: center; gap: 6px;">🟢 المشروع النشط حالياً</span>
                        {custom_badge_html}
                    </div>
                </div>
                <!-- Bottom Sub-Row: Timestamps & Activity Chips -->
                <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap; padding-top: 4px; font-size: 12.5px;">
                    {last_used_pill_html}
                    {updated_pill_html}
                </div>
            </div>
        </div>"""
        render_custom_html(row_html)

        # Action buttons — Run, Rename, Modules Config, Delete Module, Restore Module, JSON Export, Clone, Delete Project
        trash_for_pname = get_deleted_modules_trash(pname)
        has_trash = len(trash_for_pname) > 0

        b1, b_rn, b2, b3, b4, b5, b6, b7, _pad = st.columns([1.05, 1.2, 1.15, 1.05, 1.05, 0.95, 0.8, 0.45, 1.3])
        with b1:
            if st.button(
                "🚀 تشغيل",
                key=f"btn_run_{pname}",
                type="primary",
                use_container_width=True,
            ):
                set_active_project(pname)
                st.session_state["nav_view"] = "module"
                st.session_state["in_module"] = True
                saved_mod = summary.get("module_idx", 0)
                target_mod = saved_mod if saved_mod in enabled_mods else enabled_mods[0]
                st.session_state["selected_module_idx"] = target_mod
                st.rerun()
        with b_rn:
            is_rn_open = st.session_state.get(f"_show_rename_{pname}", False)
            btn_rn_label = "🔼 إخفاء" if is_rn_open else "✏️ تغيير الاسم"
            if st.button(
                btn_rn_label,
                key=f"btn_rename_{pname}",
                use_container_width=True,
                help=f"تغيير اسم مشروع {pname}",
            ):
                st.session_state[f"_show_rename_{pname}"] = not is_rn_open
                st.session_state[f"_show_mod_config_{pname}"] = False
                st.session_state[f"_show_delete_mod_{pname}"] = False
                st.session_state[f"_show_restore_mod_{pname}"] = False
                st.rerun()
        with b2:
            is_mod_open = st.session_state.get(f"_show_mod_config_{pname}", False)
            btn_mod_label = "🔼 إخفاء" if is_mod_open else "🎛️ موديولات"
            if st.button(
                btn_mod_label,
                key=f"btn_mod_cfg_{pname}",
                use_container_width=True,
                help=f"تخصيص الموديولات المتاحة لمشروع {pname}",
            ):
                st.session_state[f"_show_mod_config_{pname}"] = not is_mod_open
                st.session_state[f"_show_rename_{pname}"] = False
                st.session_state[f"_show_delete_mod_{pname}"] = False
                st.session_state[f"_show_restore_mod_{pname}"] = False
                st.rerun()
        with b3:
            is_del_mod_open = st.session_state.get(f"_show_delete_mod_{pname}", False)
            btn_del_mod_label = "🔼 إخفاء" if is_del_mod_open else "🗑️ حذف موديولات"
            if st.button(
                btn_del_mod_label,
                key=f"btn_delete_mod_{pname}",
                use_container_width=True,
                help=f"حذف (soft delete) موديولات من مشروع {pname} مع إمكانية الاستعادة لاحقاً",
            ):
                st.session_state[f"_show_delete_mod_{pname}"] = not is_del_mod_open
                st.session_state[f"_show_rename_{pname}"] = False
                st.session_state[f"_show_mod_config_{pname}"] = False
                st.session_state[f"_show_restore_mod_{pname}"] = False
                st.session_state.pop(f"_pending_batch_del_{pname}", None)
                st.session_state.pop(f"_batch_warning_{pname}", None)
                st.rerun()
        with b4:
            is_restore_open = st.session_state.get(f"_show_restore_mod_{pname}", False)
            btn_restore_label = "🔼 إخفاء" if is_restore_open else "♻️ استعادة"
            if st.button(
                btn_restore_label,
                key=f"btn_restore_mod_{pname}",
                use_container_width=True,
                help=f"استعادة موديول محذوف في مشروع {pname}" if has_trash else "لا توجد موديولات محذوفة في هذا المشروع",
                disabled=not has_trash,
            ):
                st.session_state[f"_show_restore_mod_{pname}"] = not is_restore_open
                st.session_state[f"_show_rename_{pname}"] = False
                st.session_state[f"_show_mod_config_{pname}"] = False
                st.session_state[f"_show_delete_mod_{pname}"] = False
                st.rerun()

        with b5:
            st.download_button(
                label="📤 تصدير JSON",
                data=project_json_str,
                file_name=f"{safe_pname}project.json",
                mime="application/json",
                key=f"btn_exp_{pname}",
                use_container_width=True,
            )
        with b6:
            if st.button(
                "📋 نسخ",
                key=f"btn_dup_{pname}",
                use_container_width=True,
            ):
                new_cloned = duplicate_project(pname)
                st.success(f"تم نسخ المشروع: {new_cloned}")
                st.rerun()
        with b7:
            if st.button(
                "🗑️",
                key=f"btn_del_{pname}",
                use_container_width=True,
                help=f"حذف مشروع {pname}",
            ):
                st.session_state["_profile_to_delete"] = pname
                st.session_state["_play_strong_whistle_now"] = True
                st.rerun()

        # ── Interactive Rename Project Drawer (Hide/Show) ───────────────────
        if st.session_state.get(f"_show_rename_{pname}", False):
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #0b1f3a 0%, #1e3a8a 100%); border: 1.5px solid #38bdf8; border-radius: 8px; padding: 10px 16px; margin-bottom: 10px;">
                        <div style="font-weight: 800; font-size: 16px; color: #ffffff; display: flex; align-items: center; gap: 8px;">
                            <span>✏️</span> تغيير اسم المشروع (Rename Project): <b style="color: #fef08a;">«{pname}»</b>
                        </div>
                        <div style="font-size: 13px; color: #cbd5e1; margin-top: 4px;">
                            أدخل الاسم الجديد للمشروع واضغط «حفظ الاسم الجديد». سيتم تحديث اسم المشروع في كافة السجلات مع الحفاظ الكامل على جميع الحسابات والموديولات والتصميمات.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_rn_input, col_rn_save, col_rn_cancel, _rn_pad = st.columns([4.2, 1.8, 1.2, 2.8])
                with col_rn_input:
                    new_name_val = st.text_input(
                        "اسم المشروع الجديد:",
                        value=pname,
                        key=f"input_new_name_{pname}",
                        label_visibility="collapsed",
                        placeholder="اكتب الاسم الجديد للمشروع...",
                    )
                with col_rn_save:
                    if st.button("💾 حفظ الاسم الجديد", type="primary", use_container_width=True, key=f"btn_save_rename_{pname}"):
                        cleaned_name = (new_name_val or "").strip()
                        if not cleaned_name:
                            st.error("⚠️ يرجى إدخال اسم صحيح وغير فارغ للمشروع.")
                        elif cleaned_name == pname:
                            st.warning("⚠️ الاسم المدخل مطابق للاسم الحالي للمشروع دون تغيير.")
                        elif cleaned_name in projects:
                            st.error(f"⛔ يوجد مشروع آخر بالفعل بنفس الاسم «{cleaned_name}». يرجى اختيار اسم فريد.")
                        else:
                            if rename_project(pname, cleaned_name):
                                st.session_state[f"_show_rename_{pname}"] = False
                                st.success(f"✅ تم تغيير اسم المشروع بنجاح إلى: «{cleaned_name}»")
                                st.rerun()
                            else:
                                st.error("❌ تعذر تغيير اسم المشروع. يرجى المحاولة مرة أخرى.")
                with col_rn_cancel:
                    if st.button("❌ إلغاء", key=f"btn_cancel_rename_{pname}", use_container_width=True):
                        st.session_state[f"_show_rename_{pname}"] = False
                        st.rerun()

        # ── Interactive Module Customizer Drawer (Hide/Show) ─────────────────
        if st.session_state.get(f"_show_mod_config_{pname}", False):
            with st.container(border=True):
                cur_enabled = get_project_enabled_modules(pname)
                cur_trash = get_deleted_modules_trash(pname)
                deleted_indices = [int(k) for k in cur_trash.keys()]
                # Available modules that are currently active (NOT in trash)
                avail_mods = [m for m in ALL_MODULES if m["idx"] not in deleted_indices]

                with st.form(key=f"form_mod_config_{pname}"):
                    # Top Row with Info Banner + Submit Save Button
                    col_head_info, col_head_save = st.columns([5.4, 1.6])
                    with col_head_info:
                        st.markdown(
                            f"""
                            <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border: 1.5px solid #818cf8; border-radius: 8px; padding: 8px 14px;">
                                <div style="font-weight: 800; font-size: 16px; color: #ffffff; display: flex; align-items: center; gap: 8px;">
                                    <span>🎛️</span> تخصيص الموديولات المتاحة لمشروع: <b style="color: #38bdf8;">«{pname}»</b>
                                </div>
                                <div style="font-size: 13px; color: #cbd5e1; margin-top: 2px;">
                                    اختر الموديولات التي ترغب في إظهارها في القائمة الجانبية لهذا المشروع، وسيتم إخفاء باقي الموديولات غير المحددة.
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with col_head_save:
                        st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
                        submit_save = st.form_submit_button("💾 حفظ التخصيص", type="primary", use_container_width=True)

                    st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

                    # Dynamically render checkboxes ONLY for available (non-deleted) modules
                    checkbox_results = {}
                    if avail_mods:
                        grid_num_cols = min(len(avail_mods), 3)
                        grid_cols = st.columns(grid_num_cols)
                        for ci, mod in enumerate(avail_mods):
                            with grid_cols[ci % grid_num_cols]:
                                checkbox_results[mod["idx"]] = st.checkbox(
                                    mod["name"],
                                    value=(mod["idx"] in cur_enabled),
                                    key=f"chk_mod_cfg_{pname}_{mod['idx']}",
                                )
                    else:
                        st.info("ℹ️ جميع الموديولات في هذا المشروع محذوفة. يمكنك استعادتها من زر ♻️ استعادة.")

                    if submit_save:
                        chosen_mods = [idx for idx, checked in checkbox_results.items() if checked]
                        if not chosen_mods and avail_mods:
                            st.warning("⚠️ يرجى اختيار موديول واحد على الأقل.")
                        else:
                            set_project_enabled_modules(pname, chosen_mods)
                            st.session_state[f"_show_mod_config_{pname}"] = False
                            st.rerun()

                # Close button
                c_close, _ = st.columns([1.5, 8.5])
                with c_close:
                    if st.button("❌ إغلاق بدون حفظ", key=f"btn_close_mods_{pname}", use_container_width=True):
                        st.session_state[f"_show_mod_config_{pname}"] = False
                        st.rerun()

            st.markdown("<hr style='margin:6px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)

        # ── Delete Modules Drawer (Checklist + Smart Dependency Validation + "I am sure" Confirmation) ──
        if st.session_state.get(f"_show_delete_mod_{pname}", False):
            with st.container(border=True):
                cur_trash_del = get_deleted_modules_trash(pname)
                deleted_idxs_del = [int(k) for k in cur_trash_del.keys()]
                # Available modules that are currently active (NOT in trash)
                deletable_mods = [m for m in ALL_MODULES if m["idx"] not in deleted_idxs_del]

                # Informational Header on Linked & Unlinked Modules
                links_map_html = (
                    f'<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #2e1065 100%); border: 2.5px solid #8b5cf6; border-radius: 14px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 6px 24px rgba(139, 92, 246, 0.25);">'
                    f'<div style="font-weight: 900; font-size: 20px; color: #f5d0fe; display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-bottom: 16px; border-bottom: 1.5px solid rgba(216, 180, 254, 0.30); padding-bottom: 10px; direction: rtl; text-align: right;">'
                    f'<span style="font-size: 26px;">🔗</span>'
                    f'<span>خريطة الارتباطات الهندسية بين الموديولات — مشروع: <b style="color: #fbcfe8;">«{pname}»</b></span>'
                    f'</div>'

                    # Section 1: Linked Modules (Cannot be deleted individually, must be deleted together)
                    f'<div style="background: rgba(15, 23, 42, 0.75); border: 2px solid #ef4444; border-right: 7px solid #dc2626; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;">'
                    f'<div style="color: #fca5a5; font-weight: 900; font-size: 16.5px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">'
                    f'<span style="font-size: 20px;">🔒</span>'
                    f'<span>1️⃣ الموديولات المرتبطة ببعضها (لا يمكن حذف أي موديول منها منفرداً، بل يمكن حذفهم معاً جميعاً كحزمة واحدة):</span>'
                    f'</div>'
                    f'<div style="color: #ffffff; font-size: 14.5px; font-weight: 700; line-height: 2; padding-right: 12px;">'
                    f'• <span style="color: #60a5fa;">Module 1: Integrated Structural Design</span> (البلاطة اللاكمرية والتصميم الإنشائي المتكامل)<br/>'
                    f'• <span style="color: #818cf8;">Module 2: Rectangular Columns</span> (الأعمدة المستطيلة)<br/>'
                    f'• <span style="color: #fbbf24;">Module 3: Isolated Footings</span> (القواعد المنفصلة ECP 203)<br/>'
                    f'• <span style="color: #fbbf24;">Module 7: Quick Two-Column Combined Footing</span> (تصميم قاعدة مشتركة لعمودين)<br/>'
                    f'• <span style="color: #fbbf24;">Module 9: Reinforced Concrete Strap Footing</span> (قواعد الشدادات - الجار)<br/>'
                    f'• <span style="color: #fbbf24;">Module 10: Corner Footing with Diagonal Strap</span> (قاعدة جار ركن بشداد مائل)<br/>'
                    f'• <span style="color: #34d399;">Module 11: Ground Beam Design & Detailing</span> (تصميم وتفاصيل الميدات والسملات)'
                    f'</div>'
                    f'</div>'

                    # Section 2: Unlinked Modules (Can be deleted individually without affecting other modules)
                    f'<div style="background: rgba(15, 23, 42, 0.75); border: 2px solid #22c55e; border-right: 7px solid #16a34a; border-radius: 12px; padding: 16px 20px;">'
                    f'<div style="color: #86efac; font-weight: 900; font-size: 16.5px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">'
                    f'<span style="font-size: 20px;">🔓</span>'
                    f'<span>2️⃣ الموديولات غير المرتبطة ببعضها (مستقلة تماماً ويمكن حذف أي موديول منها دون التأثير على الموديولات الأخرى):</span>'
                    f'</div>'
                    f'<div style="color: #ffffff; font-size: 14.5px; font-weight: 700; line-height: 2; padding-right: 12px;">'
                    f'• <span style="color: #a7f3d0;">Module 4: Ground Slabs</span> (بلاطات الأرضيات الخرسانية SOG)<br/>'
                    f'• <span style="color: #f472b6;">Module 5: Steel Rebar Diameters & Weights</span> (أقطار وأوزان حديد التسليح)<br/>'
                    f'• <span style="color: #c084fc;">Module 6: Concrete Quantity Survey</span> (حصر الكميات الخرسانية)<br/>'
                    f'• <span style="color: #fb923c;">Module 12: Brick & Plastering Survey</span> (حصر أعمال الطوب والمحارة)<br/>'
                    f'• <span style="color: #93c5fd;">Module 13: Standalone - Flat slabs</span> (البلاطة اللاكمرية المستقلة)'
                    f'</div>'
                    f'</div>'

                    f'</div>'
                )
                st.markdown(links_map_html, unsafe_allow_html=True)

                if not deletable_mods:
                    st.info("✅ لا توجد موديولات نشطة يمكن حذفها في هذا المشروع.")
                else:
                    pending_batch = st.session_state.get(f"_pending_batch_del_{pname}", None)
                    batch_warning = st.session_state.get(f"_batch_warning_{pname}", None)

                    # Stage 1: Checklist of Available Modules
                    if pending_batch is None and batch_warning is None:
                        st.markdown(
                            """
                            <div style='font-size: 15px; color: #cbd5e1; margin-bottom: 10px; font-weight: 700;'>حدد الموديولات التي ترغب في حذفها من المشروع (Checklist):</div>
                            <style>
                            [data-testid="stMainBlockContainer"] div[class*="st-key-chk_batch_del_"] {
                                background: rgba(15, 23, 42, 0.65) !important;
                                border: 1.2px solid rgba(148, 163, 184, 0.25) !important;
                                border-radius: 10px !important;
                                padding: 10px 14px !important;
                                margin-bottom: 10px !important;
                                min-height: 66px !important;
                                display: flex !important;
                                align-items: center !important;
                                box-sizing: border-box !important;
                                transition: all 0.2s ease-in-out !important;
                            }
                            [data-testid="stMainBlockContainer"] div[class*="st-key-chk_batch_del_"]:hover {
                                background: rgba(69, 10, 10, 0.45) !important;
                                border-color: #ef4444 !important;
                                box-shadow: 0 4px 14px rgba(239, 68, 68, 0.25) !important;
                            }
                            [data-testid="stMainBlockContainer"] div[class*="st-key-chk_batch_del_"] > label {
                                display: flex !important;
                                flex-direction: row !important;
                                align-items: flex-start !important;
                                gap: 12px !important;
                                width: 100% !important;
                                margin: 0 !important;
                                cursor: pointer !important;
                            }
                            [data-testid="stMainBlockContainer"] div[class*="st-key-chk_batch_del_"] label div[data-testid="stMarkdownContainer"] {
                                flex: 1 1 auto !important;
                                min-width: 0 !important;
                                width: 100% !important;
                                white-space: normal !important;
                                word-break: break-word !important;
                                overflow-wrap: break-word !important;
                            }
                            [data-testid="stMainBlockContainer"] div[class*="st-key-chk_batch_del_"] label div[data-testid="stMarkdownContainer"] p,
                            [data-testid="stMainBlockContainer"] div[class*="st-key-chk_batch_del_"] label span {
                                white-space: normal !important;
                                word-break: break-word !important;
                                overflow-wrap: break-word !important;
                                line-height: 1.45 !important;
                                font-size: 13.5px !important;
                                font-weight: 700 !important;
                                color: #f1f5f9 !important;
                                margin: 0 !important;
                                display: block !important;
                                unicode-bidi: plaintext !important;
                            }
                            </style>
                            """,
                            unsafe_allow_html=True,
                        )
                        selected_for_del = {}
                        grid_del_cols = min(len(deletable_mods), 2)
                        del_cols = st.columns(grid_del_cols)
                        for ci, mod in enumerate(deletable_mods):
                            with del_cols[ci % grid_del_cols]:
                                selected_for_del[mod["idx"]] = st.checkbox(
                                    f"🗑️ {mod['name']}",
                                    key=f"chk_batch_del_{pname}_{mod['idx']}",
                                    value=False,
                                )

                        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
                        btn_c1, btn_c2, _ = st.columns([2.0, 1.2, 6.8])
                        with btn_c1:
                            if st.button("🔍 متابعة ومراجعة الحذف", key=f"btn_review_del_{pname}", type="primary", use_container_width=True):
                                chosen_indices = [idx for idx, checked in selected_for_del.items() if checked]
                                if not chosen_indices:
                                    st.warning("⚠️ يرجى تحديد موديول واحد على الأقل للحذف.")
                                else:
                                    is_valid, violations, linked_pairs = validate_batch_module_deletion(pname, chosen_indices)
                                    if not is_valid:
                                        play_warning_sound()
                                        st.session_state[f"_batch_warning_{pname}"] = violations
                                        st.rerun()
                                    else:
                                        play_warning_sound()
                                        st.session_state[f"_pending_batch_del_{pname}"] = {
                                            "indices": chosen_indices,
                                            "linked_pairs": linked_pairs,
                                        }
                                        st.rerun()
                        with btn_c2:
                            if st.button("❌ إلغاء", key=f"btn_cancel_del_drawer_{pname}", use_container_width=True):
                                st.session_state[f"_show_delete_mod_{pname}"] = False
                                st.rerun()

                    # Stage 2a: Broken Dependency Warning (Blocked)
                    elif batch_warning is not None:
                        play_warning_sound()
                        viol_items_html = "".join([
                            f"<li style='margin: 8px 0; color: #fee2e2; font-size: 15px; font-weight: 600;'>{v}</li>"
                            for v in batch_warning
                        ])
                        warn_dialog_html = (
                            f'<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 50%, #3f0a0a 100%); border: 3px solid #ef4444; border-radius: 12px; padding: 20px 24px; margin: 10px 0 14px 0; box-shadow: 0 10px 35px rgba(239, 68, 68, 0.45);">'
                            f'<div style="color: #ffffff; font-weight: 900; font-size: 22px; margin-bottom: 12px; display: flex; align-items: center; justify-content: flex-start; gap: 10px; border-bottom: 2px solid rgba(239, 68, 68, 0.6); padding-bottom: 10px; direction: rtl; text-align: right;">'
                            f'<span style="font-size: 28px;">🚫</span>'
                            f'<span>تعذر إتمام الحذف لوجود ارتباطات هندسية غير مكتملة</span>'
                            f'</div>'
                            f'<div style="color: #fee2e2; font-size: 16px; font-weight: 700; line-height: 1.6; margin-bottom: 12px; direction: rtl; text-align: right;">'
                            f'تم رفض تنفيذ عملية الحذف للأسباب التالية:'
                            f'</div>'
                            f'<ul style="margin: 0 0 14px 0; padding-right: 24px; list-style: disc; direction: rtl; text-align: right;">'
                            f'{viol_items_html}'
                            f'</ul>'
                            f'<div style="background: rgba(0, 0, 0, 0.35); border: 1.5px solid rgba(254, 202, 202, 0.25); border-radius: 8px; padding: 10px 16px; color: #fef08a; font-size: 14px; font-weight: 700; direction: rtl; text-align: right;">'
                            f'💡 <b>الحل الهندسي:</b> لحذف الموديولات المرتبطة، يرجى اختيارهما معاً في قائمة الحذف لحذف المنظومة كحزمة متكاملة، أو إبقاء الموديولات التابعة نشطة.'
                            f'</div>'
                            f'</div>'
                        )
                        st.markdown(warn_dialog_html, unsafe_allow_html=True)
                        btn_back, _ = st.columns([2.5, 7.5])
                        with btn_back:
                            if st.button("↩️ العودة وتعديل قائمة الاختيار", key=f"btn_back_from_warn_{pname}", type="primary", use_container_width=True):
                                st.session_state.pop(f"_batch_warning_{pname}", None)
                                st.rerun()

                    # Stage 2b: Valid Selection -> "I am sure" Confirmation Dialog
                    elif pending_batch is not None:
                        play_warning_sound()
                        indices_to_del = pending_batch["indices"]
                        linked_pairs = pending_batch.get("linked_pairs", [])

                        del_names = [
                            next((m["name"] for m in ALL_MODULES if m["idx"] == idx), f"Module {idx}")
                            for idx in indices_to_del
                        ]
                        del_names_html = "".join([
                            f"<li style='margin: 6px 0; color: #ffffff; font-size: 16px; font-weight: 700;'><span style='color: #fef08a;'>{name}</span></li>"
                            for name in del_names
                        ])

                        linked_banner_html = ""
                        if linked_pairs:
                            linked_items = "".join([f"<li style='margin: 4px 0;'>{lp}</li>" for lp in linked_pairs])
                            linked_banner_html = (
                                f'<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: rgba(234, 179, 8, 0.18); border: 1.5px solid #eab308; border-radius: 8px; padding: 10px 16px; color: #fef08a; font-size: 14px; font-weight: 700; margin-bottom: 12px;">'
                                f'⚠️ <b>تنبيه ارتباط متبادل:</b> تحتوي هذه العملية على موديولات مرتبطة ببعضها وسيتم حذفها معاً كحزمة متكاملة:'
                                f'<ul style="margin: 6px 0 0 0; padding-right: 20px; list-style: circle;">'
                                f'{linked_items}'
                                f'</ul>'
                                f'</div>'
                            )

                        confirm_dialog_html = (
                            f'<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 50%, #3f0a0a 100%); border: 3.5px solid #ef4444; border-radius: 14px; padding: 22px 26px; margin: 10px 0 14px 0; box-shadow: 0 10px 35px rgba(239, 68, 68, 0.45);">'
                            f'<div style="color: #ffffff; font-weight: 900; font-size: 23px; margin-bottom: 12px; display: flex; align-items: center; justify-content: flex-start; gap: 12px; border-bottom: 2px solid rgba(239, 68, 68, 0.6); padding-bottom: 10px; direction: rtl; text-align: right;">'
                            f'<span style="font-size: 30px;">⚠️</span>'
                            f'<span>تأكيد حذف الموديولات المحددة ({len(del_names)} موديول) — مشروع: «{pname}»</span>'
                            f'</div>'
                            f'<div style="color: #fee2e2; font-size: 16px; font-weight: 700; margin-bottom: 10px; direction: rtl; text-align: right;">'
                            f'سيتم حذف الموديولات التالية من المشروع ونقلها إلى سلة المحذوفات:'
                            f'</div>'
                            f'<ul style="margin: 0 0 12px 0; padding-right: 24px; list-style: disc; direction: rtl; text-align: right;">'
                            f'{del_names_html}'
                            f'</ul>'
                            f'{linked_banner_html}'
                            f'<div style="background: rgba(0, 0, 0, 0.35); border: 1.5px solid rgba(254, 202, 202, 0.25); border-radius: 8px; padding: 10px 16px; color: #86efac; font-size: 14px; font-weight: 700; margin-bottom: 14px; direction: rtl; text-align: right;">'
                            f'✅ <b>الحفظ الآمن:</b> سيتم حفظ نسخة كاملة (Snapshot) من جميع بيانات ومدخلات هذه الموديولات، ويمكنك استعادتها لاحقاً في أي وقت عبر زر ♻️ استعادة.'
                            f'</div>'
                            f'</div>'
                        )
                        st.markdown(confirm_dialog_html, unsafe_allow_html=True)

                        col_sure_in, col_sure_btn, col_sure_cancel = st.columns([3.5, 2.2, 1.3])
                        with col_sure_in:
                            sure_input = st.text_input(
                                'اكتب العبارة "I am sure" لتأكيد الحذف:',
                                key=f"input_sure_{pname}",
                                placeholder="I am sure",
                                help="اكتب العبارة بدقة لتفعيل زر الحذف",
                            )
                        with col_sure_btn:
                            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                            is_phrase_matched = (sure_input or "").strip() == "I am sure"
                            if st.button(
                                "🗑️ تأكيد الحذف النهائي",
                                key=f"btn_confirm_sure_del_{pname}",
                                type="primary",
                                disabled=not is_phrase_matched,
                                use_container_width=True,
                            ):
                                ok, msg = soft_delete_modules_batch(pname, indices_to_del)
                                st.session_state.pop(f"_pending_batch_del_{pname}", None)
                                st.session_state[f"_show_delete_mod_{pname}"] = False
                                if ok:
                                    st.success(f"✅ {msg}")
                                else:
                                    st.error(f"❌ {msg}")
                                st.rerun()
                        with col_sure_cancel:
                            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                            if st.button("❌ تراجع", key=f"btn_cancel_sure_del_{pname}", use_container_width=True):
                                st.session_state.pop(f"_pending_batch_del_{pname}", None)
                                st.rerun()

                # Close Delete Drawer button
                c_close_del, _ = st.columns([1.8, 8.2])
                with c_close_del:
                    if st.button("❌ إغلاق", key=f"btn_close_del_mod_{pname}", use_container_width=True):
                        st.session_state[f"_show_delete_mod_{pname}"] = False
                        st.session_state.pop(f"_pending_batch_del_{pname}", None)
                        st.session_state.pop(f"_batch_warning_{pname}", None)
                        st.rerun()

            st.markdown("<hr style='margin:6px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)

        # ── Restore Module Drawer ────────────────────────────────────────────
        if st.session_state.get(f"_show_restore_mod_{pname}", False):
            with st.container(border=True):
                trash_restore = get_deleted_modules_trash(pname)

                st.markdown(
                    f'<div style="background: linear-gradient(135deg, #052e16 0%, #14532d 100%); border: 1.5px solid #4ade80; border-radius: 8px; padding: 8px 14px; margin-bottom: 10px;">'
                    f'<div style="font-weight: 800; font-size: 16px; color: #ffffff; display: flex; align-items: center; gap: 8px;">'
                    f'<span>♻️</span> استعادة موديول محذوف — مشروع: <b style="color: #86efac;">«{pname}»</b>'
                    f'</div>'
                    f'<div style="font-size: 13px; color: #bbf7d0; margin-top: 2px;">'
                    f'سيتم استعادة الموديول وجميع بياناته وإعداداته كما كانت قبل الحذف.'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if not trash_restore:
                    st.info("✅ لا توجد موديولات محذوفة يمكن استعادتها في هذا المشروع.")
                else:
                    st.markdown(
                        "<div style='font-size: 14px; color: #cbd5e1; margin-bottom: 8px; font-weight: 600;'>الموديولات المحذوفة المتاحة للاستعادة:</div>",
                        unsafe_allow_html=True,
                    )
                    for mod_idx_str, trash_entry in trash_restore.items():
                        mod_idx_int = int(mod_idx_str)
                        t_name = trash_entry.get("module_name", f"Module {mod_idx_str}")
                        t_date = trash_entry.get("deleted_at", "—")
                        t_snap_count = len(trash_entry.get("snapshot", {}))

                        rc1, rc2 = st.columns([5, 1.6])
                        with rc1:
                            st.markdown(
                                f'<div style="background: rgba(74, 222, 128, 0.08); border: 1px solid rgba(74, 222, 128, 0.3); border-radius: 6px; padding: 8px 12px; margin-bottom: 4px;">'
                                f'<div style="color: #4ade80; font-weight: 700; font-size: 14px;">{t_name}</div>'
                                f'<div style="color: #94a3b8; font-size: 12px; margin-top: 2px;">'
                                f'🕒 حُذف في: {t_date} &nbsp;|&nbsp; 💾 {t_snap_count} قيمة محفوظة في الـ snapshot'
                                f'</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        with rc2:
                            st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
                            if st.button(
                                "♻️ استعادة",
                                key=f"btn_do_restore_{pname}_{mod_idx_str}",
                                use_container_width=True,
                                type="primary",
                            ):
                                ok, msg = restore_module(pname, mod_idx_int)
                                st.session_state[f"_show_restore_mod_{pname}"] = False
                                if ok:
                                    st.success(f"✅ {msg}")
                                else:
                                    st.error(f"❌ {msg}")
                                st.rerun()

                # Close Restore Drawer button
                c_close_res, _ = st.columns([1.8, 8.2])
                with c_close_res:
                    if st.button("❌ إغلاق", key=f"btn_close_restore_mod_{pname}", use_container_width=True):
                        st.session_state[f"_show_restore_mod_{pname}"] = False
                        st.rerun()

            st.markdown("<hr style='margin:6px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)

    # ── SECTION 2: SAVED PROJECTS DIRECTORY (سائر المشروعات المحفوظة) ───────
    other_pnames = [p for p in all_pnames if p != active_name]

    st.markdown(
        "<div style='margin:28px 0 10px 0; font-weight: 800; font-size: 18px; color: #e2e8f0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;'>"
        "<span>📋 سائر المشروعات المحفوظة (Saved Projects Directory):</span>"
        f"<span style='font-size: 13px; font-weight: 800; color: #38bdf8; background: rgba(56, 189, 248, 0.12); padding: 3px 12px; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.3);'>📁 {len(other_pnames)} مشاريع محفوظة</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if not other_pnames:
        st.info("ℹ️ لا توجد مشاريع أخرى محفوظة حالياً. يمكنك إنشاء مشروع جديد من زر «➕ مشروع جديد» أعلاه.")
    else:
        for p_idx, s_pname in enumerate(other_pnames, 2):
            s_summary = get_project_summary(s_pname)
            is_odd = (p_idx % 2 == 1)
            stripe_class = "project-box-dark" if is_odd else "project-box-light"
            marker_class = f"project-box-saved {stripe_class}"
            s_updated = s_summary.get("updated_at", "-")
            s_last_used = s_summary.get("last_used_at", s_updated)
            s_enabled_mods = get_project_enabled_modules(s_pname)

            copy_count = s_pname.count("(نسخة)")
            if copy_count >= 2:
                copy_badge_html = f'<span style="background: rgba(245, 158, 11, 0.22); color: #fbbf24; border: 1.5px solid #f59e0b; padding: 2px 9px; border-radius: 6px; font-size: 12px; font-weight: 800;">📋 نسخة مكررة ({copy_count})</span>'
            elif copy_count == 1:
                copy_badge_html = '<span style="background: rgba(245, 158, 11, 0.18); color: #fde047; border: 1.5px solid rgba(245, 158, 11, 0.5); padding: 2px 9px; border-radius: 6px; font-size: 12px; font-weight: 800;">📋 نسخة</span>'
            else:
                copy_badge_html = ""

            pal = ACCENT_PALETTE[(p_idx - 2) % len(ACCENT_PALETTE)]
            panel_accent = pal["accent"]

            if is_odd:
                num_badge_bg = "rgba(15, 23, 42, 0.85)"
                num_badge_color = pal["tag"]
                num_badge_border = pal["accent"]
                num_badge_text = f"#{p_idx:02d}"
                title_color = "#f8fafc"
                title_shadow = "0 2px 4px rgba(0,0,0,0.6)"
                badge_html = f'<span style="background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">📁 محفوظ #{p_idx}</span>'
            else:
                num_badge_bg = "rgba(15, 23, 42, 0.90)"
                num_badge_color = pal["tag"]
                num_badge_border = pal["accent"]
                num_badge_text = f"#{p_idx:02d}"
                title_color = "#f8fafc"
                title_shadow = "0 2px 4px rgba(15, 23, 42, 0.95), 0 0 3px rgba(0, 0, 0, 0.90)"
                badge_html = f'<span style="background: rgba(15, 23, 42, 0.85); color: #f1f5f9; border: 1.5px solid #475569; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">📁 محفوظ #{p_idx}</span>'

            if len(s_enabled_mods) < len(ALL_MODULES):
                short_names = ", ".join([ALL_MODULES[i]["short"] for i in s_enabled_mods if i in range(len(ALL_MODULES))])
                custom_badge_html = f'<span style="background: rgba(251, 191, 36, 0.2); color: #fbbf24; border: 1.5px solid #f59e0b; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 800;">🎛️ ({len(s_enabled_mods)}): {short_names}</span>'
            else:
                custom_badge_html = '<span style="background: rgba(56, 189, 248, 0.15); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.35); padding: 2px 8px; border-radius: 12px; font-size: 11.5px; font-weight: 700;">🧩 كافة الموديولات (12)</span>'

            s_last_used_clean = s_last_used[:16] if s_last_used and len(s_last_used) >= 16 else (s_last_used or "-")
            s_updated_clean = s_updated[:16] if s_updated and len(s_updated) >= 16 else (s_updated or "-")

            last_used_pill_html = f'''<div style="color: #94a3b8; display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; text-shadow: 0 1px 2px rgba(0,0,0,0.85);">
                <span style="font-weight: 700;">🕒 آخر تشغيل:</span>
                <span style="font-weight: 800; font-family: monospace;">{s_last_used_clean}</span>
            </div>'''

            if s_last_used_clean != s_updated_clean and s_updated_clean != "-":
                updated_pill_html = f'''<div style="color: #94a3b8; display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; text-shadow: 0 1px 2px rgba(0,0,0,0.85);">
                    <span style="font-weight: 700;">✏️ آخر تعديل:</span>
                    <span style="font-weight: 800; font-family: monospace;">{s_updated_clean}</span>
                </div>'''
            else:
                updated_pill_html = ""

            with st.container(border=True):
                col_row_info, col_row_btn = st.columns([8.2, 1.8])
                with col_row_info:
                    row_html = f"""<div class="{marker_class}">
                        <div style="
                            background: transparent;
                            border-radius: 8px;
                            border-right: 6px solid {panel_accent};
                            padding: 2px 10px 4px 10px;
                        ">
                            <!-- Top Row: Number Badge, Project Title, Copy Badge & Status Badges -->
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 4px;">
                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    <span style="background: {num_badge_bg}; color: {num_badge_color}; font-weight: 900; font-size: 12.5px; padding: 2px 8px; border-radius: 5px; border: 1.5px solid {num_badge_border};">{num_badge_text}</span>
                                    <span style="font-size: 17px; font-weight: 800; color: {title_color}; letter-spacing: 0.3px; text-shadow: {title_shadow};">📁 {s_pname}</span>
                                    {copy_badge_html}
                                </div>
                                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                                    {badge_html}
                                    {custom_badge_html}
                                </div>
                            </div>
                            <!-- Bottom Sub-Row: Timestamps & Activity Chips -->
                            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 12px;">
                                {last_used_pill_html}
                                {updated_pill_html}
                            </div>
                        </div>
                    </div>"""
                    render_custom_html(row_html)
                with col_row_btn:
                    st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
                    if st.button(
                        "📌 تعيين كنشط",
                        key=f"btn_set_active_{s_pname}",
                        use_container_width=True,
                        help=f"تعيين مشروع «{s_pname}» كمشروع نشط ليظهر بالأعلى وتتاح كافة أزراره",
                    ):
                        set_active_project(s_pname)
                        st.rerun()


# ── MAIN EXECUTION & SIDEBAR CONDITIONAL ROUTING ──────────────────────────────
# 1. Fresh application startup: Default to the Projects Manager screen
if "_app_session_started" not in st.session_state:
    st.session_state["_app_session_started"] = True
    if "m12_op_move" in st.query_params or st.query_params.get("module") == "12":
        st.session_state["nav_view"] = "module"
        st.session_state["in_module"] = True
        cfg_set("selected_module_idx", 10)
    else:
        st.session_state["nav_view"] = "profile_manager"
        st.session_state["in_module"] = False

# 2. Strict Navigation Guard: Once inside a module, modifying ANY input NEVER exits to Projects screen!
if st.session_state.get("in_module", False) or st.session_state.get("nav_view") == "module" or "m12_op_move" in st.query_params or st.query_params.get("module") == "12":
    current_nav = "module"
    st.session_state["nav_view"] = "module"
    st.session_state["in_module"] = True
    if "m12_op_move" in st.query_params or st.query_params.get("module") == "12":
        cfg_set("selected_module_idx", 10)
else:
    current_nav = "profile_manager"
    st.session_state["nav_view"] = "profile_manager"
    st.session_state["in_module"] = False

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
        render_custom_html(
            """
            <div style="background: linear-gradient(135deg, #0b1329 0%, #1e293b 100%); border: 1.5px solid rgba(56, 189, 248, 0.45); border-radius: 12px; padding: 14px 16px; margin-bottom: 14px; text-align: center; box-shadow: 0 4px 16px rgba(0,0,0,0.4);">
                <div style="font-size: 26px; margin-bottom: 4px;">🏗️</div>
                <div style="font-size: 19px; font-weight: 900; color: #38bdf8; letter-spacing: 0.5px;">ECP 203 DASHBOARD</div>
                <div style="font-size: 12.5px; color: #94a3b8; font-weight: 600; margin-top: 2px;">الكود المصري للمنشآت الخرسانية</div>
            </div>
            """
        )

        active_project_sidebar = get_active_project_name()
        all_projects_dict = get_all_projects()
        all_projects_list = list(all_projects_dict.keys())
        if active_project_sidebar not in all_projects_list and all_projects_list:
            active_project_sidebar = all_projects_list[0]

        mod_card_html = (
            f'<div style="background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding:12px 14px; border-radius:10px; border:1.5px solid #38bdf8; margin-bottom:12px; box-shadow:0 0 14px rgba(56,189,248,0.25);">'
            f'<div style="font-size:12px; font-weight:700; color:#94a3b8; margin-bottom:2px;">📁 المشروع الإنشائي النشط:</div>'
            f'<div style="font-size:19px; font-weight:900; color:#38bdf8; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{active_project_sidebar}</div>'
            f'<div style="margin-top:6px; font-size:12px; color:#4ade80; display:flex; align-items:center; gap:6px;"><span>🟢</span><span>متزامن ونشط</span></div>'
            f'</div>'
        )
        render_custom_html(mod_card_html)

        if st.button("🏠 المشاريع", use_container_width=True, key="sb_btn_projects_mgr", help="العودة إلى شاشة إدارة المشاريع الرئيسية"):
            st.session_state["nav_view"] = "profile_manager"
            st.session_state["in_module"] = False
            st.rerun()

        st.markdown("---")

        # Load enabled modules for this specific active project
        proj_enabled_indices = get_project_enabled_modules(active_project_sidebar)
        project_module_options = [
            ALL_MODULES[i]["name"] for i in proj_enabled_indices if i in range(len(ALL_MODULES))
        ]
        if not project_module_options:
            project_module_options = [ALL_MODULES[0]["name"]]
            proj_enabled_indices = [0]

        # Determine current active selection
        raw_saved_idx = int(cfg_val("selected_module_idx", proj_enabled_indices[0]))
        if raw_saved_idx not in proj_enabled_indices:
            raw_saved_idx = proj_enabled_indices[0]
            cfg_set("selected_module_idx", raw_saved_idx)

        default_radio_idx = 0
        for opt_i, mod_i in enumerate(proj_enabled_indices):
            if mod_i == raw_saved_idx:
                default_radio_idx = opt_i
                break

        radio_key = f"sb_mod_radio_{active_project_sidebar}"
        target_mod_name = next((m["name"] for m in ALL_MODULES if m["idx"] == raw_saved_idx), None)
        if target_mod_name and target_mod_name in project_module_options:
            if st.session_state.get(radio_key) != target_mod_name:
                st.session_state[radio_key] = target_mod_name

        selected_module_name = st.radio(
            "📂 Select Design Module / Engineering Module:",
            options=project_module_options,
            index=default_radio_idx,
            key=radio_key,
        )

        # Sync the selected module global index back to cfg
        for m in ALL_MODULES:
            if m["name"] == selected_module_name:
                cfg_set("selected_module_idx", m["idx"])
                break
        module = selected_module_name
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

    mod_info = next((m for m in ALL_MODULES if m["name"] == module or m.get("short") == module), None)
    mod_key = mod_info["key"] if mod_info else ""

    if mod_key == "standalone_flat_slab" or "Module 13" in module or "standalone_flat_slab" in module:
        try:
            render_standalone_flat_slab()
        except Exception as ex:
            st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 13: {ex}")
            st.exception(ex)
    elif mod_key == "brick_survey" or "Module 12" in module or "brick_survey" in module or "طوب" in module or "المحارة" in module:
        try:
            render_brick_survey_module()
        except Exception as ex:
            st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 12: {ex}")
            st.exception(ex)
    elif mod_key == "ground_beam" or "Module 11" in module or "ground_beam" in module or "الميدات" in module or "السملات" in module:
        try:
            render_ground_beam_module()
        except Exception as ex:
            st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 11: {ex}")
            st.exception(ex)
    elif mod_key == "diagonal_strap_footing" or "Module 10" in module or "diagonal_strap" in module or "بشداد مائل" in module:
        try:
            render_diagonal_strap_module()
        except Exception as ex:
            st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 10: {ex}")
            st.exception(ex)
    elif mod_key == "strap_footing" or "Module 9" in module or "strap_footing" in module or "قواعد الشدادات" in module:
        try:
            render_strap_footing_module()
        except Exception as ex:
            st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 9: {ex}")
            st.exception(ex)
    elif mod_key == "two_col_footings" or "Module 7" in module or "Two-Column" in module or "two_col_footings" in module or "مشتركة لعمودين" in module:
        try:
            render_two_col_footings()
        except Exception as ex:
            st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 7: {ex}")
            st.exception(ex)
    elif mod_key == "concrete_survey" or "Module 6" in module or "concrete_survey" in module or ("Concrete" in module and "Survey" in module) or "حصر الخرسانات" in module:
        try:
            render_concrete_survey()
        except Exception as ex:
            st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 6: {ex}")
            st.exception(ex)
    elif mod_key == "steel_bars" or "Module 5" in module or "steel_bars" in module or "Steel Rebar" in module or "اقطار" in module:
        render_steel_bars()
    elif mod_key == "ground_slab" or "Module 4" in module or "ground_slab" in module or "Ground Slabs" in module or "الأرضية" in module:
        render_ground_slab()
    elif mod_key == "footings" or "Module 3" in module or "footings" in module or "Isolated Footings" in module or "المنفصلة" in module or ("القواعد" in module and "الشدادات" not in module and "مشتركة" not in module):
        render_footings()
    elif mod_key == "columns" or "Module 2" in module or "columns" in module or "Rectangular Columns" in module or "الأعمدة" in module:
        render_columns()
    elif mod_key == "flat_slab" or "Module 1 " in module or "Module 1 —" in module or "Integrated" in module or "flat_slab" in module:
        try:
            render_flat_slab()
        except Exception as ex:
            st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 1: {ex}")
            st.exception(ex)
    else:
        render_flat_slab()

# ── GUARANTEED DISK PERSISTENCE ──────────────────────────────────────────────
save_settings()
