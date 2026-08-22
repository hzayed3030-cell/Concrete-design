"""
modules/settings.py
-------------------
Persistent user-settings layer for the ECP 203 Dashboard.

Strategy
--------
* A single JSON file  (user_settings.json)  lives next to app.py.
* On every app run:
    - load_settings()  is called from app.py BEFORE any module renders.
      It reads the JSON file (if it exists) and merges values into
      st.session_state under the key  "cfg".
* Every widget uses  st.session_state["cfg"]["<key>"]  as its default
  value, and passes  on_change=save_settings  so the file is updated
  the instant the user edits anything.
* A sidebar "Reset" button calls  reset_settings()  which deletes the
  file and clears the in-memory dict so the next render uses ECP defaults.
"""

import json
import os
import streamlit as st

# ── Path to the persistent settings file ────────────────────────────────────
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_settings.json")

# ── Factory / ECP 203 Default Values ────────────────────────────────────────
ECP_DEFAULTS: dict = {
    # App-level Navigation
    "selected_module_idx": 0,

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

    # Column removal registry (list of original column IDs removed by user, e.g. ["C3", "C7"])
    "fs_removed_cols": [],
    "fs_void_panels": [],

    # Typography / Fixed Font Sizes (in pixels)
    "font_size_inputs":  14,       # Inputs & labels (14px)
    "font_size_outputs": 14,       # Outputs & results (14px)
}


def load_settings() -> None:
    """
    Read user_settings.json → merge into st.session_state["cfg"].
    Called once per session from app.py before any module renders.
    """
    if "cfg" in st.session_state:
        return  # already loaded this session

    cfg = dict(ECP_DEFAULTS)  # start from defaults

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                for k, v in saved.items():
                    cfg[k] = v
                st.session_state["_settings_loaded_from_file"] = True
            else:
                st.session_state["_settings_loaded_from_file"] = False
        except (json.JSONDecodeError, OSError):
            st.session_state["_settings_loaded_from_file"] = False
    else:
        st.session_state["_settings_loaded_from_file"] = False

    st.session_state["cfg"] = cfg


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


def save_settings() -> None:
    """
    Write st.session_state["cfg"] to disk immediately.
    Flushes and syncs to guarantee zero data loss on restart.
    """
    cfg = st.session_state.get("cfg", {})
    if not cfg:
        return
    try:
        clean_cfg = {k: _sanitize_for_json(v) for k, v in cfg.items()}
        temp_file = SETTINGS_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(clean_cfg, f, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        if os.path.exists(SETTINGS_FILE):
            os.replace(temp_file, SETTINGS_FILE)
        else:
            os.rename(temp_file, SETTINGS_FILE)
        st.session_state["_last_save_ok"] = True
    except Exception:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(clean_cfg, f, indent=2)
            st.session_state["_last_save_ok"] = True
        except Exception:
            st.session_state["_last_save_ok"] = False


def reset_settings() -> None:
    """
    Delete user_settings.json and clear all keys from session_state
    so the next render falls back to ECP_DEFAULTS.
    """
    if os.path.exists(SETTINGS_FILE):
        try:
            os.remove(SETTINGS_FILE)
        except OSError:
            pass
    for key in list(st.session_state.keys()):
        del st.session_state[key]


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
# These wrappers forward all normal st.number_input / st.selectbox arguments
# but automatically wire up the session-state key and on_change callback so
# every change is saved. Modules call these instead of bare st.* widgets.

def _make_on_change(cfg_key: str, widget_key: str, force_int: bool = False):
    """Return a callback that syncs the widget's session_state → cfg → disk."""
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
    All normal st.number_input kwargs (min_value, max_value, step, help …)
    are forwarded as-is. 'value' is overridden by cfg if a saved value exists.
    Ensures type consistency (all float or all int) to prevent StreamlitMixedNumericTypesError.
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

    # Use force_int so that integer-typed saved values are stored as int, not float
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
    Convenience wrapper around number_input strictly for pure-integer fields
    (e.g. span counts, rebar counts).  Always stores the value as int in cfg.
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
    Drop-in replacement for st.selectbox that persists the *index*.
    cfg stores the integer index; the actual value is options[index].
    All normal st.selectbox kwargs (format_func, help …) are forwarded.
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
    Drop-in replacement for st.radio that persists the *index*.
    cfg stores the integer index; the actual value is options[index].
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
