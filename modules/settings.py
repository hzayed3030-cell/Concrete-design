"""
modules/settings.py
-------------------
Persistent multi-profile user-settings layer for the ECP 203 Dashboard.

Strategy
--------
* A unified JSON file (profiles.json) lives next to app.py.
* Each profile represents a distinct flat / apartment design with its own spans,
  loads, thicknesses, columns, footing settings, and quantity survey data.
* On app run:
    - load_settings() reads profiles.json (migrating user_settings.json if needed).
    - Merges active profile's data into st.session_state["cfg"].
    - Every widget uses st.session_state["cfg"]["<key>"] as default value,
      and saves immediately to the active profile in profiles.json.
* Provides full CRUD operations for profiles:
    - create_profile, rename_profile, delete_profile, duplicate_profile,
      set_active_profile, get_all_profiles, get_profile_summary.
"""

import json
import os
import re
import sys
import io
import wave
import struct
import math
import base64
from datetime import datetime
import streamlit as st

# ── Paths to settings & profiles files ──────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

PROFILES_FILE = os.path.join(BASE_DIR, "profiles.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "user_settings.json")

# ── Factory / ECP 203 Default Values ────────────────────────────────────────
ECP_DEFAULTS: dict = {
    # App-level Navigation
    "selected_module_idx": 0,

    # Profile metadata inside cfg
    "apartment_name": "flat 1",

    # Module 1 – Rectangular Columns
    "col_Pu_input":      160.0,
    "col_Safety_Factor": 1.20,
    "col_b":             30,
    "col_H_clear":       300,
    "col_K_index":       1,        # index into [0.50, 0.70, 1.00, 1.20, 2.00] -> 0.70
    "col_Fcu":           250,
    "col_Fy":            4000,
    "col_Fyk":           2400,
    "col_mu_target":     1.0,
    "col_Phi_index":     3,        # index into [12, 16, 18, 20, 25] -> 20mm
    "col_Phi_st_index":  1,        # index into [6, 8, 10] -> 8mm

    # Module 2 – Isolated Footings
    "ftg_bc":            30,
    "ftg_tc":            50,
    "ftg_Pu":            160.0,
    "ftg_Wf_est":        10.0,
    "ftg_q_all":         1.5,
    "ftg_Df":            1.5,
    "ftg_gamma_soil":    1.8,
    "ftg_Fcu":           250,
    "ftg_Fy":            4000,
    "ftg_cover":         7,
    "ftg_Phi_index":     2,        # index into [12, 16, 18, 22, 25] -> 18mm
    # L, B, t_rc are derived at runtime and saved when the user overrides them
    "ftg_L_override":    None,
    "ftg_B_override":    None,
    "ftg_trc_override":  None,

    # Module 7 – Two-Column Footings (Isolated or Combined)
    "tcf_P1":           80.0,       # ton – Service load Column 1
    "tcf_P2":           120.0,      # ton – Service load Column 2
    "tcf_c1":           40,         # cm – Column 1 dim parallel to link axis
    "tcf_b1":           40,         # cm – Column 1 dim perpendicular
    "tcf_c2":           50,         # cm – Column 2 dim parallel to link axis
    "tcf_b2":           40,         # cm – Column 2 dim perpendicular
    "tcf_S":            4.0,        # m  – Center-to-center spacing
    "tcf_q_net":        1.5,        # kg/cm² – Net allowable soil bearing capacity
    "tcf_Fcu":          250,        # kg/cm² – Concrete characteristic strength
    "tcf_Fy":           4000,       # kg/cm² – Steel yield strength
    "tcf_cover":        7,          # cm – Concrete cover
    "tcf_Phi_index":    1,          # index into [12, 16, 18, 22, 25] -> 16mm
    # Override dimensions (computed at runtime, None = use auto)
    "tcf_L1_ov":        None,
    "tcf_B1_ov":        None,
    "tcf_t1_ov":        None,
    "tcf_L2_ov":        None,
    "tcf_B2_ov":        None,
    "tcf_t2_ov":        None,
    "tcf_Lc_ov":        None,
    "tcf_Bc_ov":        None,
    "tcf_tc_ov":        None,

    # Module 3 – Flat Slabs (dynamic multi-span)
    "fs_n_lx":           2,
    "fs_n_ly":           2,
    "slab_bc":           30,
    "slab_tc":           50,
    "slab_SDL":          0.15,
    "slab_wall_load":    0.50,
    "slab_LL":           0.25,
    "slab_gamma_c":      2.5,
    "slab_Fcu":          250,
    "slab_Fy":           4000,
    "slab_cover":                  1.5,      # Net concrete cover in cm (15 mm)
    "slab_ts_initial":             20,       # Initial thickness in cm
    "slab_n_floors":               1,        # Number of floors for column load calculation
    "slab_col_safety_factor":      1.10,     # Factor of safety & Columns weight for vertical load calculation
    "slab_bottom_mesh_dia_idx":    2,        # index into BAR_DIA -> 12mm
    "slab_n_btm_mesh":             5,        # number of bars per meter for bottom base mesh
    "slab_top_mesh_dia_idx":       1,        # index into BAR_DIA -> 10mm
    "slab_n_top_mesh":             5,        # number of bars per meter for top base mesh
    "slab_col_extra_dia_idx":      2,        # index into BAR_DIA -> 12mm
    "slab_strip_top_extra_dia_idx": 2,       # index into BAR_DIA -> 12mm
    "slab_strip_bottom_extra_dia_idx": 2,    # index into BAR_DIA -> 12mm
    "slab_Phi_index":              2,        # index into BAR_DIA -> 12mm
    # Dynamic span values (up to 10 each)
    "fs_lx_0": 6.0, "fs_lx_1": 6.0, "fs_lx_2": 6.0, "fs_lx_3": 6.0, "fs_lx_4": 6.0,
    "fs_lx_5": 6.0, "fs_lx_6": 6.0, "fs_lx_7": 6.0, "fs_lx_8": 6.0, "fs_lx_9": 6.0,
    "fs_ly_0": 6.0, "fs_ly_1": 6.0, "fs_ly_2": 6.0, "fs_ly_3": 6.0, "fs_ly_4": 6.0,
    "fs_ly_5": 6.0, "fs_ly_6": 6.0, "fs_ly_7": 6.0, "fs_ly_8": 6.0, "fs_ly_9": 6.0,
    # Cantilevers
    "fs_cant_left":   0.0,
    "fs_cant_right":  0.0,
    "fs_cant_bottom": 0.0,
    "fs_cant_top":    0.0,
    "fs_removed_cols": [],
    "fs_void_panels": [],
    "fs_col_transforms": {},

    # Customs Module – Concrete Survey, Flat Slabs & Material Prices
    "cs_n_types": 2,
    "cs_col_h": 300.0,
    "cs_t_slab": 20.0,
    "cs_fcu": 350.0,
    "cs_fs_n_slabs": 1,
    "cs_fs_ts": 20.0,
    "cs_fs_fcu": 350.0,
    "cs_fs_phi_btm": 12,
    "cs_fs_nb_btm": 6,
    "cs_fs_phi_top": 10,
    "cs_fs_nb_top": 6,
    "cs_fs_phi_btm_x": 12,
    "cs_fs_phi_btm_y": 12,
    "cs_fs_nb_btm_x": 6,
    "cs_fs_nb_btm_y": 6,
    "cs_fs_phi_top_x": 10,
    "cs_fs_phi_top_y": 10,
    "cs_fs_nb_top_x": 6,
    "cs_fs_nb_top_y": 6,
    "cs_fs_phi_top_add": 12,
    "cs_fs_add_top_lx": 3.0,
    "cs_fs_add_top_ly": 2.5,
    "cs_fs_n_top_add_x": 0,
    "cs_fs_n_top_add_y": 0,
    "cs_fs_phi_btm_add": 12,
    "cs_fs_add_btm_lx": 4.0,
    "cs_fs_add_btm_ly": 3.0,
    "cs_fs_n_btm_add_x": 0,
    "cs_fs_n_btm_add_y": 0,
    "cs_price_steel": 40000.0,
    "cs_price_cement": 4000.0,
    "cs_price_gravel": 600.0,
    "cs_price_sand": 200.0,
    "cs_price_labor": 2000.0,
    "cs_project_name": "مشروع حصر خرسانات ومقايسة مالية",
    # Module – Ground Slab (Slab on Grade - SOG)
    "gs_lx":                   30.0,     # Total length in meters
    "gs_ly":                   20.0,     # Total width in meters
    "gs_ts":                   20.0,     # Slab thickness in cm
    "gs_cover":                4.0,      # Clear cover in cm
    "gs_fcu":                  300.0,    # fcu in kg/cm²
    "gs_fy":                   4200.0,   # fy in kg/cm² (420 N/mm²)
    "gs_ks":                   5.0,      # Modulus of subgrade reaction in kg/cm³
    "gs_q_all":                1.5,      # Allowable soil bearing capacity in kg/cm²
    "gs_h_base":               20.0,     # Subbase gravel layer thickness in cm
    "gs_w_ll":                 2.5,      # Uniform live load in ton/m²
    "gs_p_wheel":              4.0,      # Forklift wheel point load in ton
    "gs_wheel_b":              20.0,     # Wheel contact width in cm
    "gs_wheel_l":              25.0,     # Wheel contact length in cm
    "gs_p_post":               3.5,      # Rack post point load in ton
    "gs_post_bp":              15.0,     # Post base plate width in cm
    "gs_post_tp":              15.0,     # Post base plate length in cm
    "gs_rebar_mesh_type":      "شبكة علوية وسفلية (Double Mesh)",
    "gs_phi_mesh":             10,       # Rebar mesh diameter in mm
    "gs_mesh_spacing":         20.0,     # Rebar mesh spacing in cm
    "gs_joint_spacing_x":      4.5,      # Contraction joint spacing in X (m)
    "gs_joint_spacing_y":      4.5,      # Contraction joint spacing in Y (m)
    "gs_dowel_phi":            20,       # Dowel bar diameter in mm
    "gs_dowel_len":            45.0,     # Dowel bar length in cm
    "gs_dowel_spacing":        30.0,     # Dowel bar spacing in cm

    # Typography / Fixed Font Sizes (in pixels)
    "font_size_inputs":  14,
    "font_size_outputs": 14,
}


def _get_now_str() -> str:
    """Return formatted current timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _sanitize_for_json(val):
    """Convert numpy scalars and other non-standard types to JSON-serializable primitives."""
    if hasattr(val, "item") and not isinstance(val, (list, tuple, dict, set)):
        return val.item()
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    if isinstance(val, (list, tuple)):
        return [_sanitize_for_json(x) for x in val]
    if isinstance(val, set):
        return [_sanitize_for_json(x) for x in sorted(val, key=lambda x: str(x))]
    if isinstance(val, dict):
        return {str(k): _sanitize_for_json(v) for k, v in val.items()}
    return str(val)


# ═══════════════════════════════════════════════════════════════════════════════
#  PROFILES JSON ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _migrate_user_settings_if_needed() -> dict:
    """
    If profiles.json doesn't exist:
    - If user_settings.json exists, migrate it as 'flat 1'.
    - Else create default profiles data with 'flat 1'.
    """
    migrated_data = dict(ECP_DEFAULTS)
    has_old_settings = False
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                for k, v in saved.items():
                    migrated_data[k] = v
                has_old_settings = True
        except Exception:
            pass

    default_profile_name = "flat 1"
    migrated_data["apartment_name"] = default_profile_name
    
    now_str = _get_now_str()
    initial_profiles = {
        "active_profile": default_profile_name,
        "profiles": {
            default_profile_name: {
                "name": default_profile_name,
                "description": "النموذج الافتراضي المحفوظ" if has_old_settings else "نموذج شقة رقم 1",
                "created_at": now_str,
                "updated_at": now_str,
                "data": migrated_data,
            }
        }
    }
    save_profiles_data(initial_profiles)
    return initial_profiles


def _sanitize_tcf_values(pdata_dict: dict) -> bool:
    """Sanitize Module 7 legacy keys if needed."""
    if not isinstance(pdata_dict, dict):
        return False
    modified = False
    # Legacy key migrations (lowercase to uppercase)
    if "tcf_fcu" in pdata_dict:
        val = pdata_dict.pop("tcf_fcu")
        if "tcf_Fcu" not in pdata_dict:
            pdata_dict["tcf_Fcu"] = val if (val and val >= 100) else 250
        modified = True
    if "tcf_fy" in pdata_dict:
        val = pdata_dict.pop("tcf_fy")
        if "tcf_Fy" not in pdata_dict:
            pdata_dict["tcf_Fy"] = val if (val and val >= 1000) else 4000
        modified = True
    return modified


def load_profiles_data() -> dict:
    """Read profiles.json from disk, migrating or creating if missing."""
    if not os.path.exists(PROFILES_FILE):
        return _migrate_user_settings_if_needed()

    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "profiles" in data and isinstance(data["profiles"], dict) and data["profiles"]:
            # Ensure active_profile is valid
            if "active_profile" not in data or data["active_profile"] not in data["profiles"]:
                first_name = list(data["profiles"].keys())[0]
                data["active_profile"] = first_name

            # Auto-enable newly added modules (e.g. Module 7 idx 6) and sanitize units across all existing projects
            modified = False
            for pname, pinfo in data["profiles"].items():
                pdata_dict = pinfo.get("data", {}) if isinstance(pinfo, dict) else {}
                trash = pdata_dict.get("deleted_modules_trash", {})
                deleted_indices = [int(k) for k in trash.keys()] if isinstance(trash, dict) else []

                # Sanitize old kN/MPa/mm units in tcf_ keys if present
                if _sanitize_tcf_values(pdata_dict):
                    modified = True

                if "enabled_modules" in pdata_dict and isinstance(pdata_dict["enabled_modules"], list):
                    curr_enabled = list(pdata_dict["enabled_modules"])
                    for mod in ALL_MODULES:
                        midx = mod["idx"]
                        if midx not in deleted_indices and midx not in curr_enabled:
                            curr_enabled.append(midx)
                            modified = True
                    pdata_dict["enabled_modules"] = sorted(curr_enabled)

            if modified:
                save_profiles_data(data)

            return data
    except Exception:
        pass

    return _migrate_user_settings_if_needed()


def save_profiles_data(data: dict) -> bool:
    """Atomic save for profiles.json to prevent corruption."""
    if not data or not isinstance(data, dict):
        return False
    try:
        clean_data = {
            "active_profile": str(data.get("active_profile", "flat 1")),
            "profiles": {}
        }
        for pname, pinfo in data.get("profiles", {}).items():
            clean_data["profiles"][str(pname)] = {
                "name": str(pinfo.get("name", pname)),
                "description": str(pinfo.get("description", "")),
                "created_at": str(pinfo.get("created_at", _get_now_str())),
                "updated_at": str(pinfo.get("updated_at", _get_now_str())),
                "data": {str(k): _sanitize_for_json(v) for k, v in pinfo.get("data", {}).items()}
            }

        temp_file = PROFILES_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(clean_data, f, indent=2, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass

        if os.path.exists(PROFILES_FILE):
            os.replace(temp_file, PROFILES_FILE)
        else:
            os.rename(temp_file, PROFILES_FILE)
        return True
    except Exception:
        try:
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False


def get_all_profiles() -> dict:
    """Return dictionary of all profiles: {profile_name: profile_dict}."""
    pdata = load_profiles_data()
    return pdata.get("profiles", {})


def get_active_profile_name() -> str:
    """Return the name of the currently active profile."""
    if "_active_profile_name" in st.session_state and st.session_state["_active_profile_name"]:
        return str(st.session_state["_active_profile_name"])
    pdata = load_profiles_data()
    active = pdata.get("active_profile", "flat 1")
    st.session_state["_active_profile_name"] = active
    return active


def get_active_profile() -> dict:
    """Return active profile dict {name, description, created_at, updated_at, data}."""
    active_name = get_active_profile_name()
    profiles = get_all_profiles()
    if active_name in profiles:
        return profiles[active_name]
    if profiles:
        first_name = list(profiles.keys())[0]
        return profiles[first_name]
    return {
        "name": "flat 1",
        "description": "",
        "created_at": _get_now_str(),
        "updated_at": _get_now_str(),
        "data": dict(ECP_DEFAULTS),
    }


def _clear_widget_cache():
    """
    Comprehensively clear Streamlit widget session state and calculation caches
    so loaded project values refresh cleanly without cross-project state leakage.
    Uses strict whitelist approach: preserves ONLY system keys and wipes all widget/temp keys.
    """
    preserve_keys = {
        "_active_profile_name",
        "cfg",
        "_settings_loaded_from_file",
        "_last_save_ok",
        "nav_view",
    }
    keys_to_del = [k for k in list(st.session_state.keys()) if k not in preserve_keys]
    for k in keys_to_del:
        del st.session_state[k]

    # Clear calculation caches so that previous project calculations are never reused
    try:
        st.cache_data.clear()
    except Exception:
        pass


def set_active_profile(profile_name: str, clear_cache: bool = True) -> None:
    """Switch active profile, load its data into cfg, and clear widget session cache."""
    pdata = load_profiles_data()
    profiles = pdata.get("profiles", {})
    if profile_name not in profiles:
        return

    pdata["active_profile"] = profile_name
    save_profiles_data(pdata)

    st.session_state["_active_profile_name"] = profile_name

    # Merge target profile's data with defaults
    new_cfg = dict(ECP_DEFAULTS)
    profile_cfg = profiles[profile_name].get("data", {})
    for k, v in profile_cfg.items():
        new_cfg[k] = v
    new_cfg["apartment_name"] = profile_name
    new_cfg["cs_project_name"] = profile_name

    # Ensure deleted_modules_trash and enabled_modules are explicitly present in session
    trash = profile_cfg.get("deleted_modules_trash", {})
    new_cfg["deleted_modules_trash"] = trash
    new_cfg["enabled_modules"] = get_project_enabled_modules(profile_name)

    st.session_state["cfg"] = new_cfg
    st.session_state["_settings_loaded_from_file"] = True

    if clear_cache:
        _clear_widget_cache()


def create_project(
    project_name: str,
    owner_name: str = "",
    copy_from: str = None,
    description: str = "",
    enabled_modules: list = None,
) -> str:
    """Create a new project with clean defaults or cloned from an existing project."""
    name = (project_name or "").strip()
    if not name:
        # Generate auto-incremented name like 'مشروع 1', 'مشروع 2'
        projects = get_all_projects()
        idx = len(projects) + 1
        while f"مشروع {idx}" in projects:
            idx += 1
        name = f"مشروع {idx}"

    pdata = load_profiles_data()
    profiles = pdata.get("profiles", {})

    # Ensure uniqueness
    base_name = name
    counter = 2
    while name in profiles:
        name = f"{base_name} ({counter})"
        counter += 1

    # Populate data
    if copy_from and copy_from in profiles:
        src_data = dict(profiles[copy_from].get("data", {}))
        new_data = dict(ECP_DEFAULTS)
        new_data.update(src_data)
        if not description:
            description = f"نسخة من {copy_from}"
    else:
        new_data = dict(ECP_DEFAULTS)

    # Apply enabled_modules if provided or inherited
    if enabled_modules is not None and isinstance(enabled_modules, list):
        valid_mods = [int(i) for i in enabled_modules if int(i) in range(len(ALL_MODULES))]
        new_data["enabled_modules"] = sorted(list(set(valid_mods))) if valid_mods else [0]
    elif copy_from and copy_from in profiles and "enabled_modules" in src_data:
        new_data["enabled_modules"] = src_data["enabled_modules"]
    elif "enabled_modules" not in new_data:
        new_data["enabled_modules"] = [m["idx"] for m in ALL_MODULES]

    new_data["apartment_name"] = name
    new_data["cs_project_name"] = name
    if owner_name:
        new_data["cs_owner_name"] = owner_name.strip()

    now_str = _get_now_str()

    profiles[name] = {
        "name": name,
        "description": description or f"مشروع {name}",
        "created_at": now_str,
        "updated_at": now_str,
        "data": new_data,
    }
    pdata["profiles"] = profiles
    pdata["active_profile"] = name
    save_profiles_data(pdata)

    set_active_project(name, clear_cache=True)
    return name

create_profile = create_project


def rename_project(old_name: str, new_name: str) -> bool:
    """Rename an existing project without losing data."""
    new_clean = (new_name or "").strip()
    if not new_clean or old_name == new_clean:
        return False

    pdata = load_profiles_data()
    profiles = pdata.get("profiles", {})
    if old_name not in profiles:
        return False

    # Check if target name already exists
    if new_clean in profiles and new_clean != old_name:
        return False

    pinfo = profiles.pop(old_name)
    pinfo["name"] = new_clean
    pinfo["updated_at"] = _get_now_str()
    pinfo["data"]["apartment_name"] = new_clean
    pinfo["data"]["cs_project_name"] = new_clean
    profiles[new_clean] = pinfo
    pdata["profiles"] = profiles

    if pdata.get("active_profile") == old_name:
        pdata["active_profile"] = new_clean
        st.session_state["_active_profile_name"] = new_clean
        if "cfg" in st.session_state:
            st.session_state["cfg"]["apartment_name"] = new_clean
            st.session_state["cfg"]["cs_project_name"] = new_clean

    save_profiles_data(pdata)
    _clear_widget_cache()
    return True

rename_profile = rename_project


def delete_project(project_name: str) -> bool:
    """Delete a project. If it is the active project, switch to another."""
    pdata = load_profiles_data()
    profiles = pdata.get("profiles", {})
    if project_name not in profiles:
        return False

    profiles.pop(project_name)

    if not profiles:
        # Recreate a clean default project
        now_str = _get_now_str()
        def_name = "مشروع 1"
        def_data = dict(ECP_DEFAULTS)
        def_data["apartment_name"] = def_name
        def_data["cs_project_name"] = def_name
        profiles[def_name] = {
            "name": def_name,
            "description": "مشروع افتراضي 1",
            "created_at": now_str,
            "updated_at": now_str,
            "data": def_data,
        }
        pdata["active_profile"] = def_name
    elif pdata.get("active_profile") == project_name:
        pdata["active_profile"] = list(profiles.keys())[0]

    pdata["profiles"] = profiles
    save_profiles_data(pdata)

    target_active = pdata["active_profile"]
    set_active_project(target_active, clear_cache=True)
    return True

delete_profile = delete_project


def duplicate_project(source_name: str, new_name: str = None) -> str:
    """Clone an existing project with a new name."""
    if not new_name:
        new_name = f"{source_name} (نسخة)"
    return create_project(new_name, copy_from=source_name)

duplicate_profile = duplicate_project


# ── PROJECT MODULE CUSTOMIZATION DEFINITIONS & HELPERS ───────────────────────
ALL_MODULES = [
    {"idx": 0, "key": "flat_slab", "name": "🟦 Module 1 — Flat Slabs", "short": "Module 1"},
    {"idx": 1, "key": "columns", "name": "🏛️ Module 2 — Rectangular Columns", "short": "Module 2"},
    {"idx": 2, "key": "footings", "name": "🪸 Module 3 — Isolated Footings", "short": "Module 3"},
    {"idx": 3, "key": "ground_slab", "name": "🏗️ Module 4 — Ground Slabs", "short": "Module 4"},
    {"idx": 4, "key": "steel_bars", "name": "⚙️ Module 5 — Steel Rebar Diameters & Weights", "short": "Module 5"},
    {"idx": 5, "key": "concrete_survey", "name": "📊 Module 6 — Concrete Quantity Survey", "short": "Module 6"},
    {"idx": 6, "key": "two_col_footings", "name": "🏗️ Module 7 — Combined Footing Design", "short": "Module 7"},
]


def get_project_enabled_modules(project_name: str) -> list:
    """
    Return list of enabled module indices (0..5) for the given project.
    Strictly excludes any module currently present in deleted_modules_trash.
    Defaults to all non-deleted modules if not specifically configured.
    """
    profiles = get_all_projects()
    pinfo = profiles.get(project_name, {})
    data = pinfo.get("data", {}) if pinfo else {}

    trash = data.get("deleted_modules_trash", {})
    deleted_indices = [int(k) for k in trash.keys()] if isinstance(trash, dict) else []
    available_indices = [m["idx"] for m in ALL_MODULES if m["idx"] not in deleted_indices]

    if not available_indices:
        return []

    enabled = data.get("enabled_modules", None)
    if isinstance(enabled, list) and len(enabled) > 0:
        valid_indices = [
            int(i) for i in enabled
            if isinstance(i, (int, float, str)) and str(i).isdigit() and int(i) in available_indices
        ]
        if valid_indices:
            return sorted(list(set(valid_indices)))

    return available_indices


def set_project_enabled_modules(project_name: str, enabled_indices: list) -> bool:
    """
    Save enabled module indices for a project into profiles.json.
    Guarantees that deleted modules (in deleted_modules_trash) can NEVER be re-enabled.
    """
    pdata = load_profiles_data()
    profiles = pdata.get("profiles", {})
    if project_name not in profiles:
        return False

    project_data = profiles[project_name].get("data", {})
    trash = project_data.get("deleted_modules_trash", {})
    deleted_indices = [int(k) for k in trash.keys()] if isinstance(trash, dict) else []
    available_indices = [m["idx"] for m in ALL_MODULES if m["idx"] not in deleted_indices]

    valid_indices = sorted(list(set([
        int(i) for i in enabled_indices if int(i) in available_indices
    ])))
    if not valid_indices and available_indices:
        valid_indices = [available_indices[0]]

    if "data" not in profiles[project_name]:
        profiles[project_name]["data"] = {}
    profiles[project_name]["data"]["enabled_modules"] = valid_indices
    profiles[project_name]["updated_at"] = _get_now_str()

    ok = save_profiles_data(pdata)
    if ok and project_name == get_active_project_name() and "cfg" in st.session_state:
        st.session_state["cfg"]["enabled_modules"] = valid_indices
    return ok


def get_project_summary(project_name: str) -> dict:
    """
    Extract geometric & design summary metrics for a project
    to render on the project management cards.
    Accurately detects whether the project is in Flat Slab, Concrete Survey, or Ground Slab mode.
    """
    profiles = get_all_projects()
    pinfo = profiles.get(project_name, {})
    data = pinfo.get("data", {}) if pinfo else {}

    mod_idx = int(data.get("selected_module_idx", 0))

    if mod_idx == 5:
        # ── Module 6: Concrete Survey & Takeoff (حصر الخرسانات) ──
        n_col_types = int(data.get("cs_n_types", 1))
        n_cols_active = sum(int(data.get(f"cs_ncols_{i}", 0)) for i in range(n_col_types))
        n_cols_total = n_cols_active

        n_slabs = int(data.get("cs_fs_n_slabs", 1))
        slab_areas = []
        for i in range(n_slabs):
            slx = float(data.get(f"cs_fs_lx_{i}", 0.0))
            sly = float(data.get(f"cs_fs_ly_{i}", 0.0))
            srep = int(data.get(f"cs_fs_n_rep_{i}", 1))
            slab_areas.append(slx * sly * srep)
        area = sum(slab_areas) if slab_areas else 0.0
        total_w = float(data.get("cs_fs_lx_0", 0.0))
        total_h = float(data.get("cs_fs_ly_0", 0.0))
        n_lx = n_slabs
        n_ly = 1
        ts = float(data.get("cs_fs_ts", data.get("cs_t_slab", 20.0)))
        floors = 1
        module_name = "Concrete Quantity Survey"

    elif mod_idx == 3:
        # ── Module 4: Ground Slab (البلاطات الأرضية) ──
        total_w = float(data.get("gs_lx", 30.0))
        total_h = float(data.get("gs_ly", 20.0))
        area = total_w * total_h
        n_cols_active = 0
        n_cols_total = 0
        n_lx = 1
        n_ly = 1
        ts = float(data.get("gs_ts", 20.0))
        floors = 1
        module_name = "Ground Slabs"

    elif mod_idx == 1:
        # ── Module 2: Rectangular Columns ──
        total_w = 0.0
        total_h = 0.0
        area = 0.0
        n_cols_active = 1
        n_cols_total = 1
        n_lx = 1
        n_ly = 1
        ts = 0.0
        floors = 1
        module_name = "Rectangular Columns"

    elif mod_idx == 2:
        # ── Module 3: Isolated Footings ──
        total_w = 0.0
        total_h = 0.0
        area = 0.0
        n_cols_active = 1
        n_cols_total = 1
        n_lx = 1
        n_ly = 1
        ts = 0.0
        floors = 1
        module_name = "Isolated Footings"

    elif mod_idx == 4:
        # ── Tool: Steel Rebar ──
        total_w = 0.0
        total_h = 0.0
        area = 0.0
        n_cols_active = 0
        n_cols_total = 0
        n_lx = 1
        n_ly = 1
        ts = 0.0
        floors = 1
        module_name = "Steel Rebar"

    else:
        # ── Module 1: Flat Slabs & General Grid ──
        n_lx = int(data.get("fs_n_lx", 2))
        n_ly = int(data.get("fs_n_ly", 2))

        lx_spans = [float(data.get(f"fs_lx_{i}", 6.0)) for i in range(n_lx)]
        ly_spans = [float(data.get(f"fs_ly_{j}", 6.0)) for j in range(n_ly)]

        c_left = float(data.get("fs_cant_left", 0.0))
        c_right = float(data.get("fs_cant_right", 0.0))
        c_btm = float(data.get("fs_cant_bottom", 0.0))
        c_top = float(data.get("fs_cant_top", 0.0))

        total_w = sum(lx_spans) + c_left + c_right
        total_h = sum(ly_spans) + c_btm + c_top
        area = total_w * total_h

        n_cols_total = (n_lx + 1) * (n_ly + 1)
        removed_cols = data.get("fs_removed_cols", [])
        n_cols_active = n_cols_total - len(removed_cols) if isinstance(removed_cols, list) else n_cols_total

        ts = float(data.get("slab_ts_initial", 20.0))
        floors = int(data.get("slab_n_floors", 1))
        module_name = "Flat Slabs"

    # Project name is the project's primary identity
    p_name = pinfo.get("name", project_name)
    owner_name = str(data.get("cs_owner_name", "")).strip()

    return {
        "name": p_name,
        "project_name": p_name,
        "owner_name": owner_name,
        "description": pinfo.get("description", ""),
        "created_at": pinfo.get("created_at", ""),
        "updated_at": pinfo.get("updated_at", ""),
        "n_lx": n_lx,
        "n_ly": n_ly,
        "total_w": total_w,
        "total_h": total_h,
        "area": area,
        "n_cols_active": n_cols_active,
        "n_cols_total": n_cols_total,
        "ts": ts,
        "floors": floors,
        "module_idx": mod_idx,
        "module_name": module_name,
    }

get_profile_summary = get_project_summary


def get_safe_profile_filename_prefix(project_name: str = None) -> str:
    """
    Generate a clean, sanitized prefix for exported files (PNG, PDF, HTML, DXF)
    e.g. 'Villa_Shorouk_' or 'Tower_Al_Amal_' to ensure outputs are distinct.
    """
    name = project_name or get_active_project_name()
    clean = re.sub(r'[\s/\\:*?"<>|]+', '_', name).strip('_')
    return f"{clean}_" if clean else "Project_"

get_safe_project_filename_prefix = get_safe_profile_filename_prefix


def export_project_json(project_name: str) -> str:
    """Return a standalone JSON export string for a single project."""
    projects = get_all_projects()
    if project_name not in projects:
        return ""
    pinfo = projects[project_name]
    export_payload = {
        "version": "1.0",
        "type": "single_project",
        "exported_at": _get_now_str(),
        "project": pinfo,
    }
    return json.dumps(export_payload, indent=2, ensure_ascii=False)

export_profile_json = export_project_json


def export_all_projects_json() -> str:
    """Return a full backup JSON export string containing all projects."""
    pdata = load_profiles_data()
    export_payload = {
        "version": "1.0",
        "type": "all_projects",
        "exported_at": _get_now_str(),
        "active_project": pdata.get("active_profile", "مشروع 1"),
        "projects": pdata.get("profiles", {}),
    }
    return json.dumps(export_payload, indent=2, ensure_ascii=False)

export_all_profiles_json = export_all_projects_json


def import_project_json(json_content: str, overwrite: bool = False) -> tuple:
    """
    Import projects from a JSON string.
    Supports single_project, all_projects, raw project dicts, or legacy profiles/settings.
    Returns (success: bool, message: str).
    """
    try:
        data = json.loads(json_content)
    except Exception as e:
        return False, f"فشل قراءة ملف الـ JSON: {e}"

    if not isinstance(data, dict):
        return False, "تنسيق الملف غير صالح: المحتوى ليس كائناً صحيحاً (JSON Object)."

    pdata = load_profiles_data()
    existing_profiles = pdata.get("profiles", {})
    imported_count = 0
    now_str = _get_now_str()

    # Case A: Full backup package with "projects" or "profiles" dict
    items_dict = data.get("projects") or data.get("profiles")
    if items_dict and isinstance(items_dict, dict):
        for pname, pinfo in items_dict.items():
            if not isinstance(pinfo, dict):
                continue
            target_name = pname
            if target_name in existing_profiles and not overwrite:
                target_name = f"{pname} (مستورد)"
                counter = 2
                while target_name in existing_profiles:
                    target_name = f"{pname} (مستورد {counter})"
                    counter += 1

            new_profile_entry = {
                "name": target_name,
                "description": pinfo.get("description", "مستورد من ملف خارجي"),
                "created_at": pinfo.get("created_at", now_str),
                "updated_at": now_str,
                "data": pinfo.get("data", {}),
            }
            new_profile_entry["data"]["apartment_name"] = target_name
            new_profile_entry["data"]["cs_project_name"] = target_name
            existing_profiles[target_name] = new_profile_entry
            imported_count += 1

    # Case B: Single project / profile container
    elif (data.get("type") in ("single_project", "single_profile")) and (data.get("project") or data.get("profile")):
        pinfo = data.get("project") or data.get("profile")
        orig_name = pinfo.get("name", "Project Imported")
        target_name = orig_name
        if target_name in existing_profiles and not overwrite:
            target_name = f"{orig_name} (مستورد)"
            counter = 2
            while target_name in existing_profiles:
                target_name = f"{orig_name} (مستورد {counter})"
                counter += 1

        new_profile_entry = {
            "name": target_name,
            "description": pinfo.get("description", "مستورد من ملف خارجي"),
            "created_at": pinfo.get("created_at", now_str),
            "updated_at": now_str,
            "data": pinfo.get("data", {}),
        }
        new_profile_entry["data"]["apartment_name"] = target_name
        new_profile_entry["data"]["cs_project_name"] = target_name
        existing_profiles[target_name] = new_profile_entry
        pdata["active_profile"] = target_name
        imported_count += 1

    # Case C: Raw single project dict (contains 'name' and 'data')
    elif "name" in data and "data" in data and isinstance(data["data"], dict):
        orig_name = data.get("name", "Project Imported")
        target_name = orig_name
        if target_name in existing_profiles and not overwrite:
            target_name = f"{orig_name} (مستورد)"
            counter = 2
            while target_name in existing_profiles:
                target_name = f"{orig_name} (مستورد {counter})"
                counter += 1

        new_profile_entry = {
            "name": target_name,
            "description": data.get("description", "مستورد من ملف خارجي"),
            "created_at": data.get("created_at", now_str),
            "updated_at": now_str,
            "data": data.get("data", {}),
        }
        new_profile_entry["data"]["apartment_name"] = target_name
        new_profile_entry["data"]["cs_project_name"] = target_name
        existing_profiles[target_name] = new_profile_entry
        pdata["active_profile"] = target_name
        imported_count += 1

    # Case D: Raw flat settings dict (e.g. legacy user_settings.json)
    elif "fs_n_lx" in data or "slab_bc" in data or "col_Pu_input" in data:
        orig_name = str(data.get("cs_project_name") or data.get("apartment_name") or f"مشروع {len(existing_profiles) + 1}")
        target_name = orig_name
        if target_name in existing_profiles and not overwrite:
            target_name = f"{orig_name} (مستورد)"
            counter = 2
            while target_name in existing_profiles:
                target_name = f"{orig_name} (مستورد {counter})"
                counter += 1

        new_profile_entry = {
            "name": target_name,
            "description": "مستورد من ملف إعدادات",
            "created_at": now_str,
            "updated_at": now_str,
            "data": data,
        }
        new_profile_entry["data"]["apartment_name"] = target_name
        new_profile_entry["data"]["cs_project_name"] = target_name
        existing_profiles[target_name] = new_profile_entry
        pdata["active_profile"] = target_name
        imported_count += 1

    else:
        return False, "لم يتم التعرف على بنية ملف المشروع (تأكد من اختيار ملف JSON صالح)."

    if imported_count > 0:
        pdata["profiles"] = existing_profiles
        save_profiles_data(pdata)
        set_active_project(pdata.get("active_profile", list(existing_profiles.keys())[0]))
        return True, f"تم استيراد {imported_count} مشروع بنجاح وتحديث قائمة المشاريع."

    return False, "لم يتم العثور على مشاريع صالحة للاستيراد داخل الملف."

import_profile_json = import_project_json
get_all_projects = get_all_profiles
get_active_project_name = get_active_profile_name
get_active_project = get_active_profile
set_active_project = set_active_profile



# ═══════════════════════════════════════════════════════════════════════════════
#  INTEGRATED SETTINGS LOAD / SAVE / RESET
# ═══════════════════════════════════════════════════════════════════════════════

def load_settings() -> None:
    """
    Read active project from profiles.json → merge into st.session_state["cfg"].
    Called once per session or on project switch before modules render.
    """
    if "cfg" in st.session_state and st.session_state.get("_settings_loaded_from_file"):
        return

    pdata = load_profiles_data()
    active_name = pdata.get("active_profile", "مشروع 1")
    profiles = pdata.get("profiles", {})

    if active_name not in profiles and profiles:
        active_name = list(profiles.keys())[0]
        pdata["active_profile"] = active_name

    cfg = dict(ECP_DEFAULTS)
    if active_name in profiles:
        profile_data = profiles[active_name].get("data", {})
        for k, v in profile_data.items():
            cfg[k] = v

        cfg["apartment_name"] = active_name
        cfg["cs_project_name"] = active_name

        # Ensure deleted_modules_trash and enabled_modules are strictly synced
        trash = profile_data.get("deleted_modules_trash", {})
        cfg["deleted_modules_trash"] = trash
        cfg["enabled_modules"] = get_project_enabled_modules(active_name)

        if not isinstance(cfg.get("fs_col_transforms"), dict):
            cfg["fs_col_transforms"] = {}

        st.session_state["_settings_loaded_from_file"] = True
    else:
        st.session_state["_settings_loaded_from_file"] = False

    if not isinstance(cfg.get("fs_col_transforms"), dict):
        cfg["fs_col_transforms"] = {}

    st.session_state["cfg"] = cfg
    st.session_state["_active_profile_name"] = active_name


def save_settings() -> None:
    """
    Write st.session_state["cfg"] into active project inside profiles.json immediately.
    Guarantees instant persistence on widget modification and keeps Project Name synced.
    Never overwrites or drops enabled_modules or deleted_modules_trash.
    """
    cfg = st.session_state.get("cfg", {})
    if not cfg:
        return

    active_name = get_active_project_name()
    pdata = load_profiles_data()
    profiles = pdata.get("profiles", {})

    # Check if user typed a new project name in any Project Name input field
    new_pname = str(cfg.get("cs_project_name", "")).strip()
    if new_pname and new_pname != active_name and new_pname != "مشروع حصر خرسانات ومقايسة مالية":
        if active_name in profiles:
            pinfo = profiles.pop(active_name)
            pinfo["name"] = new_pname
            pinfo["updated_at"] = _get_now_str()
            pinfo["data"]["apartment_name"] = new_pname
            pinfo["data"]["cs_project_name"] = new_pname
            profiles[new_pname] = pinfo
            active_name = new_pname
            pdata["active_profile"] = new_pname
            st.session_state["_active_profile_name"] = new_pname
            cfg["apartment_name"] = new_pname
            cfg["cs_project_name"] = new_pname

    if active_name not in profiles:
        profiles[active_name] = {
            "name": active_name,
            "description": f"مشروع {active_name}",
            "created_at": _get_now_str(),
            "updated_at": _get_now_str(),
            "data": {},
        }

    clean_cfg = {k: _sanitize_for_json(v) for k, v in cfg.items()}

    # CRITICAL: enabled_modules and deleted_modules_trash must NEVER be overwritten with stale cfg values.
    # Pull authoritative values from existing_data in profiles.json if they exist.
    clean_cfg.pop("enabled_modules", None)
    clean_cfg.pop("deleted_modules_trash", None)

    existing_data = profiles[active_name].get("data", {})
    if "enabled_modules" in existing_data:
        clean_cfg["enabled_modules"] = existing_data["enabled_modules"]
    elif "enabled_modules" in cfg:
        clean_cfg["enabled_modules"] = cfg["enabled_modules"]

    if "deleted_modules_trash" in existing_data:
        clean_cfg["deleted_modules_trash"] = existing_data["deleted_modules_trash"]
    elif "deleted_modules_trash" in cfg:
        clean_cfg["deleted_modules_trash"] = cfg["deleted_modules_trash"]

    profiles[active_name]["data"] = clean_cfg
    profiles[active_name]["updated_at"] = _get_now_str()
    pdata["profiles"] = profiles
    pdata["active_profile"] = active_name

    ok = save_profiles_data(pdata)
    st.session_state["_last_save_ok"] = ok


    # Also keep user_settings.json in sync for legacy compatibility
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(clean_cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def reset_settings() -> None:
    """
    Reset the active profile's configuration to standard ECP defaults.
    """
    active_name = get_active_profile_name()
    cfg = dict(ECP_DEFAULTS)
    cfg["apartment_name"] = active_name
    st.session_state["cfg"] = cfg
    save_settings()
    _clear_widget_cache()


def reset_font_sizes() -> None:
    """Reset font sizes to fixed 14px."""
    cfg = st.session_state.get("cfg", {})
    cfg["font_size_inputs"] = 14
    cfg["font_size_outputs"] = 14
    st.session_state["cfg"] = cfg
    save_settings()


def render_font_controls() -> None:
    """No-op: Font sizes are fixed at 14px."""
    pass


def cfg_val(key: str, default=None):
    """Convenience getter: returns the current value for a settings key, properly preserving 0/False."""
    if "cfg" not in st.session_state:
        load_settings()
    cfg_dict = st.session_state.get("cfg", {})
    if key in cfg_dict and cfg_dict[key] is not None:
        return cfg_dict[key]
    if key in ECP_DEFAULTS and ECP_DEFAULTS[key] is not None:
        return ECP_DEFAULTS[key]
    return default


def cfg_set(key: str, value) -> None:
    """Set a value in cfg and immediately persist to disk."""
    if "cfg" not in st.session_state:
        load_settings()
    st.session_state["cfg"][key] = value
    save_settings()


# ── Widget helpers ──────────────────────────────────────────────────────────

def _make_on_change(cfg_key: str, widget_key: str, force_int: bool = False):
    """Return a callback that syncs widget session_state → cfg → disk."""
    def _cb():
        val = st.session_state.get(widget_key)
        if val is not None:
            if "cfg" not in st.session_state:
                load_settings()
            if force_int:
                try:
                    val = int(round(float(val)))
                except (ValueError, TypeError):
                    pass
            st.session_state["cfg"][cfg_key] = val
            save_settings()
    return _cb


def number_input(label: str, cfg_key: str, **kwargs):
    """
    Drop-in replacement for st.number_input that persists the value.
    'value' is overridden by cfg if a saved value exists.
    """
    widget_key = f"w_{cfg_key}"
    saved = cfg_val(cfg_key)
    if saved is not None:
        kwargs["value"] = saved

    bounds_keys = ("min_value", "max_value", "step")
    all_numeric = ("value", "min_value", "max_value", "step")

    is_explicit_float = any(
        isinstance(kwargs.get(k), float)
        for k in bounds_keys
        if kwargs.get(k) is not None
    )
    is_explicit_int = any(
        isinstance(kwargs.get(k), int)
        for k in bounds_keys
        if kwargs.get(k) is not None
    )

    if is_explicit_float:
        for k in all_numeric:
            if k in kwargs and kwargs[k] is not None:
                try:
                    kwargs[k] = float(kwargs[k])
                except (ValueError, TypeError):
                    pass
    elif is_explicit_int:
        for k in all_numeric:
            if k in kwargs and kwargs[k] is not None:
                try:
                    kwargs[k] = int(round(float(kwargs[k])))
                except (ValueError, TypeError):
                    pass
    elif isinstance(kwargs.get("value"), float):
        for k in all_numeric:
            if k in kwargs and kwargs[k] is not None:
                try:
                    kwargs[k] = float(kwargs[k])
                except (ValueError, TypeError):
                    pass

    _force_int = is_explicit_int and not is_explicit_float

    val = st.number_input(
        label,
        key=widget_key,
        on_change=_make_on_change(cfg_key, widget_key, force_int=_force_int),
        **kwargs,
    )
    if val is not None:
        val_clean = int(round(float(val))) if _force_int else val
        if "cfg" in st.session_state and st.session_state["cfg"].get(cfg_key) != val_clean:
            st.session_state["cfg"][cfg_key] = val_clean
            save_settings()
    return val


def integer_input(label: str, cfg_key: str, **kwargs):
    """
    Convenience wrapper around number_input strictly for pure-integer fields.
    """
    kwargs.setdefault("step", 1)
    for k in ("min_value", "max_value", "step", "value"):
        if k in kwargs and kwargs[k] is not None:
            try:
                kwargs[k] = int(round(float(kwargs[k])))
            except (ValueError, TypeError):
                pass
    saved = cfg_val(cfg_key)
    if saved is not None:
        try:
            kwargs["value"] = int(round(float(saved)))
        except (ValueError, TypeError):
            pass

    widget_key = f"w_{cfg_key}"
    val = st.number_input(
        label,
        key=widget_key,
        on_change=_make_on_change(cfg_key, widget_key, force_int=True),
        **kwargs,
    )
    if val is not None:
        try:
            val_clean = int(round(float(val)))
        except (ValueError, TypeError):
            val_clean = val
        if "cfg" in st.session_state and st.session_state["cfg"].get(cfg_key) != val_clean:
            st.session_state["cfg"][cfg_key] = val_clean
            save_settings()
    return val


def selectbox(label: str, cfg_key=None, options=None, **kwargs):
    """
    Drop-in replacement for st.selectbox that persists the index.
    Robustly handles (label, cfg_key, options) or (label, options, cfg_key).
    """
    if options is None and "options" in kwargs:
        options = kwargs.pop("options")
    if cfg_key is None and "cfg_key" in kwargs:
        cfg_key = kwargs.pop("cfg_key")

    if isinstance(cfg_key, (list, tuple)) and isinstance(options, str):
        cfg_key, options = options, cfg_key
    elif isinstance(cfg_key, (list, tuple)) and options is None:
        options = cfg_key
        cfg_key = f"sb_{abs(hash(label))}"

    if not isinstance(cfg_key, str):
        cfg_key = str(cfg_key)
    if options is None:
        options = []
    options = list(options)

    widget_key = f"w_{cfg_key}"
    saved_index = cfg_val(cfg_key)
    if saved_index is not None and len(options) > 0:
        try:
            saved_index = max(0, min(int(saved_index), len(options) - 1))
            kwargs["index"] = saved_index
        except (ValueError, TypeError):
            pass

    def _cb():
        chosen = st.session_state.get(widget_key)
        if chosen is not None and chosen in options:
            if "cfg" not in st.session_state:
                load_settings()
            st.session_state["cfg"][cfg_key] = options.index(chosen)
            save_settings()

    res = st.selectbox(label, options=options, key=widget_key, on_change=_cb, **kwargs)
    if res in options:
        idx = options.index(res)
        if "cfg" in st.session_state and st.session_state["cfg"].get(cfg_key) != idx:
            st.session_state["cfg"][cfg_key] = idx
            save_settings()
    return res


def radio(label: str, cfg_key=None, options=None, **kwargs):
    """
    Drop-in replacement for st.radio that persists the index.
    Robustly handles (label, cfg_key, options) or (label, options, cfg_key).
    """
    if options is None and "options" in kwargs:
        options = kwargs.pop("options")
    if cfg_key is None and "cfg_key" in kwargs:
        cfg_key = kwargs.pop("cfg_key")

    if isinstance(cfg_key, (list, tuple)) and isinstance(options, str):
        cfg_key, options = options, cfg_key
    elif isinstance(cfg_key, (list, tuple)) and options is None:
        options = cfg_key
        cfg_key = f"rad_{abs(hash(label))}"

    if not isinstance(cfg_key, str):
        cfg_key = str(cfg_key)
    if options is None:
        options = []
    options = list(options)

    widget_key = f"w_{cfg_key}"
    saved_index = cfg_val(cfg_key)
    if saved_index is not None and len(options) > 0:
        try:
            saved_index = max(0, min(int(saved_index), len(options) - 1))
            kwargs["index"] = saved_index
        except (ValueError, TypeError):
            pass

    def _cb():
        chosen = st.session_state.get(widget_key)
        if chosen is not None and chosen in options:
            if "cfg" not in st.session_state:
                load_settings()
            st.session_state["cfg"][cfg_key] = options.index(chosen)
            save_settings()

    res = st.radio(label, options=options, key=widget_key, on_change=_cb, **kwargs)
    if res in options:
        idx = options.index(res)
        if "cfg" in st.session_state and st.session_state["cfg"].get(cfg_key) != idx:
            st.session_state["cfg"][cfg_key] = idx
            save_settings()
    return res


def text_input(label: str, cfg_key: str, **kwargs):
    """Drop-in replacement for st.text_input that persists the text value."""
    widget_key = f"w_{cfg_key}"
    saved = cfg_val(cfg_key)
    if saved is not None:
        kwargs["value"] = str(saved)

    res = st.text_input(
        label,
        key=widget_key,
        on_change=_make_on_change(cfg_key, widget_key),
        **kwargs,
    )
    if res is not None and "cfg" in st.session_state and st.session_state["cfg"].get(cfg_key) != res:
        st.session_state["cfg"][cfg_key] = res
        save_settings()
    return res


def checkbox(label: str, cfg_key: str, **kwargs):
    """Drop-in replacement for st.checkbox that persists the boolean value."""
    widget_key = f"w_{cfg_key}"
    saved = cfg_val(cfg_key)
    if saved is not None:
        kwargs["value"] = bool(saved)

    res = st.checkbox(
        label,
        key=widget_key,
        on_change=_make_on_change(cfg_key, widget_key),
        **kwargs,
    )
    if res is not None and "cfg" in st.session_state and st.session_state["cfg"].get(cfg_key) != res:
        st.session_state["cfg"][cfg_key] = res
        save_settings()
    return res


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE SOFT-DELETE / RESTORE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

# Key prefixes/patterns that belong to each module.
# Used to snapshot a module's data before soft-deleting it.
MODULE_DATA_KEY_PREFIXES = {
    0: [  # Flat Slabs
        "fs_n_lx", "fs_n_ly",
        "fs_lx_", "fs_ly_",
        "fs_cant_left", "fs_cant_right", "fs_cant_bottom", "fs_cant_top",
        "fs_removed_cols", "fs_void_panels",
        "fs_col_pu_int", "fs_col_pu_edge", "fs_col_pu_corner",
        "fs_col_tot_pu_int", "fs_col_tot_pu_edge", "fs_col_tot_pu_corner",
        "fs_building_columns", "fs_col_b", "fs_col_c", "fs_Lx_spans", "fs_Ly_spans",
        "slab_bc", "slab_tc", "slab_SDL", "slab_wall_load", "slab_LL",
        "slab_gamma_c", "slab_Fcu", "slab_Fy", "slab_cover",
        "slab_ts_initial", "slab_n_floors",
        "slab_bottom_mesh_dia_idx", "slab_n_btm_mesh",
        "slab_top_mesh_dia_idx", "slab_n_top_mesh",
        "slab_col_extra_dia_idx", "slab_strip_top_extra_dia_idx",
        "slab_strip_bottom_extra_dia_idx", "slab_Phi_index",
    ],
    1: [  # Rectangular Columns
        "col_Pu_input", "col_Safety_Factor", "col_b", "col_H_clear",
        "col_K_index", "col_Fcu", "col_Fy", "col_Fyk",
        "col_mu_target", "col_Phi_index", "col_Phi_st_index",
    ],
    2: [  # Isolated Footings
        "ftg_bc", "ftg_tc", "ftg_Pu", "ftg_Wf_est", "ftg_q_all",
        "ftg_Df", "ftg_gamma_soil", "ftg_Fcu", "ftg_Fy", "ftg_cover",
        "ftg_Phi_index", "ftg_L_override", "ftg_B_override", "ftg_trc_override",
    ],
    3: [  # Ground Slabs
        "gs_lx", "gs_ly", "gs_ts", "gs_cover", "gs_fcu", "gs_fy",
        "gs_ks", "gs_q_all", "gs_h_base", "gs_w_ll", "gs_p_wheel",
        "gs_wheel_b", "gs_wheel_l", "gs_p_post", "gs_post_bp", "gs_post_tp",
        "gs_rebar_mesh_type", "gs_phi_mesh", "gs_mesh_spacing",
        "gs_joint_spacing_x", "gs_joint_spacing_y",
        "gs_dowel_phi", "gs_dowel_len", "gs_dowel_spacing",
    ],
    4: [  # Steel Rebar — no persistent data keys
    ],
    5: [  # Concrete Survey — 100% Standalone Data Keys
        "cs_n_types", "cs_col_h", "cs_t_slab", "cs_fcu",
        "cs_fs_n_slabs", "cs_fs_ts", "cs_fs_fcu",
        "cs_fs_phi_btm", "cs_fs_nb_btm", "cs_fs_phi_top", "cs_fs_nb_top",
        "cs_fs_phi_btm_x", "cs_fs_phi_btm_y", "cs_fs_nb_btm_x", "cs_fs_nb_btm_y",
        "cs_fs_phi_top_x", "cs_fs_phi_top_y", "cs_fs_nb_top_x", "cs_fs_nb_top_y",
        "cs_fs_phi_top_add", "cs_fs_add_top_lx", "cs_fs_add_top_ly",
        "cs_fs_n_top_add_x", "cs_fs_n_top_add_y",
        "cs_fs_phi_btm_add", "cs_fs_add_btm_lx", "cs_fs_add_btm_ly",
        "cs_fs_n_btm_add_x", "cs_fs_n_btm_add_y",
        "cs_price_steel", "cs_price_cement", "cs_price_gravel",
        "cs_price_sand", "cs_price_labor",
        "cs_project_name", "cs_owner_name",
        # Dynamic per-column-type, per-slab, and elements takeoff keys
        "cs_", "surv_", "custom_takeoff_rows",
    ],
    6: [  # Two-Column Footings (Isolated or Combined)
        "tcf_P1", "tcf_P2", "tcf_c1", "tcf_b1", "tcf_c2", "tcf_b2",
        "tcf_S", "tcf_q_net", "tcf_Fcu", "tcf_Fy", "tcf_cover", "tcf_Phi_index",
        "tcf_L1_ov", "tcf_B1_ov", "tcf_t1_ov",
        "tcf_L2_ov", "tcf_B2_ov", "tcf_t2_ov",
        "tcf_Lc_ov", "tcf_Bc_ov", "tcf_tc_ov",
    ],
}

# Dependency map: which modules DEPEND ON a given module.
# Bidirectional & Functional Module Dependency Map
# Key = module index; Value = list of (linked_idx, relationship_description)
# Module 1 (Flat Slab) and Module 2 (Columns) have a direct, mutual BIDIRECTIONAL dependency.
# Module 3 (Footings) depends on Module 2 (Columns).
# Module 4, 5, 6, 7 (Ground Slabs, Steel Rebar, Quantity Survey, Two-Column Footings) are 100% standalone.
FUNCTIONAL_DEPENDENCIES: dict[int, list] = {
    0: [  # Module 1 — Flat Slabs (البلاطات اللاكمرية) -> Requires Columns (1)
        (1, "مرتبط بنماذج وتصميم الأعمدة: يغذي الأعمدة بالأحمال المحسوبة وتعتمد بحور السقف والقص الثاقب عليها"),
    ],
    1: [  # Module 2 — Columns (الأعمدة المستطيلة) -> Requires Flat Slabs (0)
        (0, "مرتبط بالألواح المسطحة: يستقبل أحمال الأعمدة المحسوبة من السقف وتعتمد عليها قطاعات الأعمدة للقص الثاقب"),
    ],
    2: [  # Module 3 — Footings (القواعد المنفصلة) -> Requires Columns (1)
        (1, "مرتبط بالأعمدة: يستقبل أبعاد قطاعات الأعمدة وأحمالها لتصميم القواعد"),
    ],
    3: [],  # Module 4 — Ground Slabs: Standalone
    4: [],  # Module 5 — Steel Rebar: Standalone
    5: [],  # Module 6 — Concrete Quantity Survey: 100% Standalone
    6: [],  # Module 7 — Two-Column Footings: Standalone
}


def validate_new_project_module_selection(selected_indices: list) -> tuple[bool, list[dict]]:
    """
    Validates a list of selected module indices for a NEW project.
    Enforces functional engineering dependencies:
      - If module A is selected, any required module B must also be selected.
      - If module A requires B and B is missing, produces a clear violation.
      - Standalone modules (e.g. Concrete Quantity Survey) have 0 dependencies and can be selected alone.
    Returns:
      (is_valid: bool, violations: list[dict])
      where each violation dict contains:
        {"module_a_idx": int, "module_a_name": str, "module_b_idx": int, "module_b_name": str,
         "relationship": str, "message": str}
    """
    if not selected_indices:
        return False, [{"message": "يرجى اختيار موديول واحد على الأقل للمشروع الجديد."}]

    selected_set = set(int(i) for i in selected_indices if int(i) in range(len(ALL_MODULES)))
    if not selected_set:
        return False, [{"message": "يرجى اختيار موديول واحد على الأقل للمشروع الجديد."}]

    violations = []
    seen_pairs = set()

    for midx in selected_set:
        # Check forward dependencies
        forward_deps = FUNCTIONAL_DEPENDENCIES.get(midx, [])
        for dep_idx, relationship in forward_deps:
            if dep_idx not in selected_set:
                pair_key = tuple(sorted([midx, dep_idx]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    m_a = next((m for m in ALL_MODULES if m["idx"] == midx), None)
                    m_b = next((m for m in ALL_MODULES if m["idx"] == dep_idx), None)
                    name_a = m_a["name"] if m_a else f"Module {midx}"
                    name_b = m_b["name"] if m_b else f"Module {dep_idx}"
                    violations.append({
                        "module_a_idx": midx,
                        "module_a_name": name_a,
                        "module_b_idx": dep_idx,
                        "module_b_name": name_b,
                        "relationship": relationship,
                        "message": f"الموديول «{name_a}» والموديول «{name_b}» مرتبطان هندسياً ويجب اختيارهما معاً في المشروع الجديد.",
                    })

    is_valid = len(violations) == 0
    return is_valid, violations


def get_module_data_keys(project_data: dict, module_idx: int) -> dict:
    """
    Extract all data keys belonging to a specific module from a project's data dict.
    Returns a dict {key: value} snapshot of that module's data.
    Uses prefix matching to capture dynamic keys (e.g. cs_name_0, fs_lx_0..9).
    """
    if module_idx not in MODULE_DATA_KEY_PREFIXES:
        return {}

    prefixes = MODULE_DATA_KEY_PREFIXES[module_idx]
    snapshot = {}

    for key, value in project_data.items():
        # Skip system keys that must never be snapshotted
        if key in ("enabled_modules", "deleted_modules_trash",
                   "apartment_name", "cs_project_name", "selected_module_idx"):
            continue
        for prefix in prefixes:
            if key == prefix or (prefix.endswith("_") and key.startswith(prefix)):
                snapshot[key] = value
                break

    return snapshot


def check_module_dependencies(project_name: str, module_idx: int) -> list:
    """
    Check which active (non-deleted) modules are linked to module_idx within a project.
    Performs a strict BIDIRECTIONAL scan (forward + reverse linkages).
    Returns a list of dicts:
        [{"idx": int, "name": str, "relationship": str}, ...]
    Only returns dependencies for modules that currently exist in the project (not deleted).
    Applies universally across all projects and all models/modules.
    """
    trash = get_deleted_modules_trash(project_name)
    deleted_indices = [int(k) for k in trash.keys()] if isinstance(trash, dict) else []

    # Available (non-deleted) modules in the project
    available_indices = [m["idx"] for m in ALL_MODULES if m["idx"] not in deleted_indices]

    # If the target module itself is not in available_indices or already deleted, return empty
    if module_idx not in available_indices or module_idx in deleted_indices:
        return []

    dependent_modules = []
    seen_deps = set()

    # 1. Forward dependencies: modules that module_idx explicitly declares a relationship with
    forward_deps = FUNCTIONAL_DEPENDENCIES.get(module_idx, [])
    for dep_idx, relationship in forward_deps:
        if dep_idx != module_idx and dep_idx in available_indices and dep_idx not in deleted_indices:
            if dep_idx not in seen_deps:
                seen_deps.add(dep_idx)
                dep_info = next((m for m in ALL_MODULES if m["idx"] == dep_idx), None)
                dep_name = dep_info["name"] if dep_info else f"Module {dep_idx}"
                dependent_modules.append({
                    "idx": dep_idx,
                    "name": dep_name,
                    "relationship": relationship,
                })

    # 2. Reverse dependencies: other non-deleted modules that declare a relationship with module_idx
    for other_idx, other_deps in FUNCTIONAL_DEPENDENCIES.items():
        if other_idx != module_idx and other_idx in available_indices and other_idx not in deleted_indices:
            for target_idx, rel in other_deps:
                if target_idx == module_idx and other_idx not in seen_deps:
                    seen_deps.add(other_idx)
                    dep_info = next((m for m in ALL_MODULES if m["idx"] == other_idx), None)
                    dep_name = dep_info["name"] if dep_info else f"Module {other_idx}"
                    dependent_modules.append({
                        "idx": other_idx,
                        "name": dep_name,
                        "relationship": rel,
                    })

    return dependent_modules


def get_deleted_modules_trash(project_name: str) -> dict:
    """
    Return the deleted_modules_trash dict for a project.
    Structure: {str(module_idx): {"deleted_at": str, "module_idx": int,
                                   "module_name": str, "snapshot": dict}}
    Returns empty dict if no modules have been deleted.
    """
    profiles = get_all_projects()
    pinfo = profiles.get(project_name, {})
    data = pinfo.get("data", {}) if pinfo else {}
    trash = data.get("deleted_modules_trash", {})
    return trash if isinstance(trash, dict) else {}


def generate_alarm_wav_bytes() -> bytes:
    """Generates a loud, high-contrast double-beep WAV buffer in memory."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)

        # Tone 1: 850 Hz for 0.14s (loud alert tone)
        n1 = int(22050 * 0.14)
        for i in range(n1):
            env = 1.0 - (i / n1) * 0.3
            val = int(32767.0 * 0.85 * env * math.sin(2.0 * math.pi * 850.0 * (i / 22050.0)))
            wav_file.writeframesraw(struct.pack('<h', val))

        # Pause 0.04s
        np = int(22050 * 0.04)
        for i in range(np):
            wav_file.writeframesraw(struct.pack('<h', 0))

        # Tone 2: 550 Hz for 0.20s (secondary warning tone)
        n2 = int(22050 * 0.20)
        for i in range(n2):
            env = 1.0 - (i / n2) * 0.35
            val = int(32767.0 * 0.90 * env * math.sin(2.0 * math.pi * 550.0 * (i / 22050.0)))
            wav_file.writeframesraw(struct.pack('<h', val))

    return buf.getvalue()


ALARM_WAV_BYTES: bytes = generate_alarm_wav_bytes()
ALARM_WAV_B64: str = base64.b64encode(ALARM_WAV_BYTES).decode('ascii')


def play_warning_sound() -> None:
    """
    Centralized, Multi-Layer Warning Sound mechanism for ANY blocked delete across the application.
    Executes complementary audio layers without displaying any UI player controls:
      Layer 1: Browser iframe HTML5 Web Audio API synthesis + invisible audio element via components.html
      Layer 2: Native Host OS System Sound (winsound on Windows)
    """
    # ── Layer 1: Browser Frontend Sound (Completely Invisible) ──────────────
    try:
        import streamlit.components.v1 as components
        js_code = f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body style="margin:0;padding:0;overflow:hidden;background:transparent;">
        <audio autoplay style="display:none;" src="data:audio/wav;base64,{ALARM_WAV_B64}"></audio>
        <script>
        (function() {{
            try {{
                var AudioCtx = window.AudioContext || window.webkitAudioContext || (window.parent && (window.parent.AudioContext || window.parent.webkitAudioContext));
                if (AudioCtx) {{
                    var ctx = new AudioCtx();
                    if (ctx.state === 'suspended') {{ ctx.resume(); }}
                    var now = ctx.currentTime;
                    var osc1 = ctx.createOscillator();
                    var gain1 = ctx.createGain();
                    osc1.type = 'sawtooth';
                    osc1.frequency.setValueAtTime(850, now);
                    gain1.gain.setValueAtTime(0.50, now);
                    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.14);
                    osc1.connect(gain1);
                    gain1.connect(ctx.destination);
                    osc1.start(now);
                    osc1.stop(now + 0.14);

                    var osc2 = ctx.createOscillator();
                    var gain2 = ctx.createGain();
                    osc2.type = 'sawtooth';
                    osc2.frequency.setValueAtTime(550, now + 0.18);
                    gain2.gain.setValueAtTime(0.55, now + 0.18);
                    gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.38);
                    osc2.connect(gain2);
                    gain2.connect(ctx.destination);
                    osc2.start(now + 0.18);
                    osc2.stop(now + 0.38);
                }}
            }} catch(e) {{}}
        }})();
        </script>
        </body>
        </html>
        """
        components.html(js_code, height=0, width=0)
    except Exception:
        pass

    # ── Layer 3: Native Host OS Hardware Alert Sound ────────────────────────
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONHAND)
        try:
            winsound.Beep(850, 140)
            winsound.Beep(550, 200)
        except Exception:
            pass
    except Exception:
        try:
            sys.stdout.write('\a')
            sys.stdout.flush()
        except Exception:
            pass


play_system_delete_blocked_sound = play_warning_sound


def soft_delete_module(project_name: str, module_idx: int) -> bool:
    """
    Soft-delete a module from a project:
      0. BACKEND SECURITY: Enforce zero-dependency rule (strictly blocks delete if dependencies exist).
      1. Snapshot all module-specific data keys into deleted_modules_trash.
      2. Remove the module index from enabled_modules.
      3. Switch selected_module_idx to a remaining active module if needed.
      4. Atomically persist to profiles.json.

    Returns True on success, False on failure / blocked.
    """
    # ── 0. Strict Backend Enforcement: Block Deletion if Dependencies Exist ──
    deps = check_module_dependencies(project_name, module_idx)
    if deps:
        # Emit centralized warning sound & reject deletion
        play_warning_sound()
        return False

    pdata = load_profiles_data()
    profiles = pdata.get("profiles", {})
    if project_name not in profiles:
        return False

    pinfo = profiles[project_name]
    project_data = pinfo.get("data", {})


    # ── 1. Build snapshot ────────────────────────────────────────────────────
    snapshot = get_module_data_keys(project_data, module_idx)

    # ── 2. Record in trash ───────────────────────────────────────────────────
    trash = project_data.get("deleted_modules_trash", {})
    if not isinstance(trash, dict):
        trash = {}

    mod_info = next((m for m in ALL_MODULES if m["idx"] == module_idx), None)
    mod_name = mod_info["name"] if mod_info else f"Module {module_idx}"

    trash[str(module_idx)] = {
        "deleted_at": _get_now_str(),
        "module_idx": module_idx,
        "module_name": mod_name,
        "snapshot": snapshot,
    }
    project_data["deleted_modules_trash"] = trash

    # ── 3. Remove from enabled_modules ───────────────────────────────────────
    curr_enabled = project_data.get("enabled_modules", [m["idx"] for m in ALL_MODULES])
    if not isinstance(curr_enabled, list):
        curr_enabled = [m["idx"] for m in ALL_MODULES]

    deleted_str_keys = set(trash.keys())
    new_enabled = [i for i in curr_enabled if i != module_idx and str(i) not in deleted_str_keys]
    if not new_enabled:
        remaining = [m["idx"] for m in ALL_MODULES if str(m["idx"]) not in deleted_str_keys]
        new_enabled = [remaining[0]] if remaining else []
    project_data["enabled_modules"] = new_enabled

    # ── 4. Redirect selected_module_idx if the deleted one was active ────────
    if int(project_data.get("selected_module_idx", 0)) == module_idx:
        project_data["selected_module_idx"] = new_enabled[0] if new_enabled else 0

    pinfo["data"] = project_data
    pinfo["updated_at"] = _get_now_str()
    profiles[project_name] = pinfo
    pdata["profiles"] = profiles

    ok = save_profiles_data(pdata)

    # If deleting from the active project, immediately sync session state
    if ok and project_name == get_active_project_name():
        cfg = st.session_state.get("cfg", {})
        cfg["enabled_modules"] = new_enabled
        cfg["deleted_modules_trash"] = trash
        if int(st.session_state.get("selected_module_idx", 0)) == module_idx:
            fallback_idx = new_enabled[0] if new_enabled else 0
            st.session_state["selected_module_idx"] = fallback_idx
            cfg["selected_module_idx"] = fallback_idx
        st.session_state["cfg"] = cfg
        _clear_widget_cache()

    return ok


def restore_module(project_name: str, module_idx: int) -> tuple:
    """
    Restore a soft-deleted module:
      1. Find the module's snapshot in deleted_modules_trash.
      2. Re-apply snapshot data keys back into project data.
      3. Add module index back to enabled_modules.
      4. Remove module from trash.
      5. Atomically persist to profiles.json.

    Returns (success: bool, message: str).
    """
    pdata = load_profiles_data()
    profiles = pdata.get("profiles", {})
    if project_name not in profiles:
        return False, f"المشروع «{project_name}» غير موجود."

    pinfo = profiles[project_name]
    project_data = pinfo.get("data", {})
    trash = project_data.get("deleted_modules_trash", {})

    if not isinstance(trash, dict) or str(module_idx) not in trash:
        mod_info = next((m for m in ALL_MODULES if m["idx"] == module_idx), None)
        mod_name = mod_info["name"] if mod_info else f"Module {module_idx}"
        return False, f"الموديول «{mod_name}» غير موجود في قائمة المحذوفات."

    trash_entry = trash[str(module_idx)]
    snapshot = trash_entry.get("snapshot", {})

    # ── 1. Re-apply snapshot data ─────────────────────────────────────────────
    for key, value in snapshot.items():
        project_data[key] = value

    # ── 2. Remove from trash FIRST so get_project_enabled_modules sees it as restored
    del trash[str(module_idx)]
    project_data["deleted_modules_trash"] = trash

    # ── 3. Add back to enabled_modules ───────────────────────────────────────
    enabled = project_data.get("enabled_modules", [])
    if not isinstance(enabled, list):
        enabled = []
    if module_idx not in enabled:
        enabled.append(module_idx)
    enabled = sorted(list(set([int(i) for i in enabled if str(i) not in trash])))
    project_data["enabled_modules"] = enabled

    pinfo["data"] = project_data
    pinfo["updated_at"] = _get_now_str()
    profiles[project_name] = pinfo
    pdata["profiles"] = profiles

    ok = save_profiles_data(pdata)

    # Sync active project session state if needed
    if ok and project_name == get_active_project_name():
        cfg = st.session_state.get("cfg", {})
        for key, value in snapshot.items():
            cfg[key] = value
        cfg["enabled_modules"] = enabled
        cfg["deleted_modules_trash"] = trash
        st.session_state["cfg"] = cfg
        _clear_widget_cache()

    mod_info = next((m for m in ALL_MODULES if m["idx"] == module_idx), None)
    mod_name = mod_info["name"] if mod_info else f"Module {module_idx}"
    if ok:
        return True, f"تم استعادة الموديول «{mod_name}» وبياناته بنجاح."
    return False, "فشل حفظ البيانات على القرص."

