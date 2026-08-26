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
    "cs_owner_name": "",

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
    """Clear Streamlit widget cache so loaded profile values refresh cleanly."""
    keys_to_del = [
        k for k in list(st.session_state.keys())
        if k.startswith("w_") or k.startswith("_fs_") or k.startswith("w_cs_") or k.startswith("btn_")
    ]
    for k in keys_to_del:
        del st.session_state[k]


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
    st.session_state["cfg"] = new_cfg
    st.session_state["_settings_loaded_from_file"] = True

    if clear_cache:
        _clear_widget_cache()


def create_project(project_name: str, owner_name: str = "", copy_from: str = None, description: str = "") -> str:
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


def get_project_summary(project_name: str) -> dict:
    """
    Extract geometric & design summary metrics for a project
    to render on the project management cards.
    """
    profiles = get_all_projects()
    pinfo = profiles.get(project_name, {})
    data = pinfo.get("data", {}) if pinfo else {}

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

        # If user has set a custom project name inside data, ensure it is the active project identity
        stored_proj = str(cfg.get("cs_project_name", "")).strip()
        if stored_proj and stored_proj != "مشروع حصر خرسانات ومقايسة مالية":
            if stored_proj != active_name and stored_proj not in profiles:
                pinfo = profiles.pop(active_name)
                pinfo["name"] = stored_proj
                pinfo["data"]["apartment_name"] = stored_proj
                pinfo["data"]["cs_project_name"] = stored_proj
                profiles[stored_proj] = pinfo
                active_name = stored_proj
                pdata["active_profile"] = active_name
                pdata["profiles"] = profiles
                save_profiles_data(pdata)

        cfg["apartment_name"] = active_name
        cfg["cs_project_name"] = active_name
        st.session_state["_settings_loaded_from_file"] = True
    else:
        st.session_state["_settings_loaded_from_file"] = False

    st.session_state["cfg"] = cfg
    st.session_state["_active_profile_name"] = active_name


def save_settings() -> None:
    """
    Write st.session_state["cfg"] into active project inside profiles.json immediately.
    Guarantees instant persistence on widget modification and keeps Project Name synced.
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


def selectbox(label: str, cfg_key: str, options: list, **kwargs):
    """
    Drop-in replacement for st.selectbox that persists the index.
    """
    widget_key = f"w_{cfg_key}"
    saved_index = cfg_val(cfg_key)
    if saved_index is not None:
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


def radio(label: str, cfg_key: str, options: list, **kwargs):
    """
    Drop-in replacement for st.radio that persists the index.
    """
    widget_key = f"w_{cfg_key}"
    saved_index = cfg_val(cfg_key)
    if saved_index is not None:
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
