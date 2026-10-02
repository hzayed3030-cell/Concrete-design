"""
Module 15 -- Masonry & Plastering Works (اعمال المباني والمحارة)
"""
import io, math, base64, json, time
import matplotlib
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
matplotlib.use("Agg")
from modules.settings import (
    cfg_val,
    cfg_set,
    save_settings,
    play_warning_sound,
    play_delete_confirmation_whistle,
    ALARM_WAV_B64,
    _ensure_module15_state,
    reset_module_15_state,
)
from modules.table_styler import render_styled_table

_WALL_THIN=12; _WALL_THICK=25; _SHIFT_COL=6

# ─── خيارات ترحيل الأعمدة بالنسبة للمحاور (6 سم) ──────────────────────────
M15_SHIFT_X_OPTIONS = [
    "متمركز على المحور (Centered)",
    "جسم العمود يميناً (الوجه يسار المحور - 6 cm)",
    "جسم العمود يساراً (الوجه يمين المحور + 6 cm)",
]
M15_SHIFT_Y_OPTIONS = [
    "متمركز على المحور (Centered)",
    "جسم العمود لأعلى (الوجه أسفل المحور - 6 cm)",
    "جسم العمود لأسفل (الوجه أعلى المحور + 6 cm)",
]
_CLR_WALL_12="#EFA368"; _CLR_WALL_25="#8B1A1A"; _CLR_WALL_PARAPET="#0284C7"
_CLR_COL="#2F4F8F"; _CLR_COL_REMOVED="#BBBBBB"
_CLR_WIN="#87CEEB"; _CLR_DOOR="#2E7D32"
_CLR_AXIS_X="#E53935"; _CLR_AXIS_Y="#1565C0"

# ─── قاموس أنواع ومقاسات الطوب المصري (BOQ فقط) ───────────────────────────
# الصيغة: "طول × عرض × ارتفاع" (سم)
_BRICK_SIZES = {
    "الطوب الأحمر الطفلي": [
        "25×12×6",
        "24×11×6",
        "20×10×6",
        "19×9×6",
        "25×12×12",
        "24×11×12",
        "20×10×12",
        "19×9×12",
        "25×12×13",
        "مقاس آخر / مخصص",
    ],
    "الطوب الأسمنتي": [
        "40×20×10",
        "40×20×12",
        "40×20×15",
        "40×20×20",
        "20×20×10",
        "20×20×20",
        "مقاس آخر / مخصص",
    ],
    "الطوب الخفيف": [
        "60×20×10",
        "60×20×12",
        "60×20×15",
        "60×20×20",
        "60×25×10",
        "60×25×15",
        "60×25×20",
        "مقاس آخر / مخصص",
    ],
}

_BRICK_TYPES = list(_BRICK_SIZES.keys())
_CUSTOM_SIZE_LABEL = "مقاس آخر / مخصص"

def _parse_brick_size(size_str: str):
    """تحليل سلسلة المقاس 'L×W×H' إلى أرقام عشرية (l_cm, w_cm, h_cm)."""
    try:
        parts = [float(x.strip()) for x in size_str.replace("×", "x").split("x")]
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
    except Exception:
        pass
    return 25.0, 12.0, 6.0


def _init_state():
    cfg = st.session_state.get("cfg", {})
    if "m15_x_axes" not in st.session_state or "module_15_data" not in st.session_state:
        _ensure_module15_state(cfg)
    if "m15_preview_opening" not in st.session_state:
        st.session_state["m15_preview_opening"] = None
    if "m15_win_preview_disabled" not in st.session_state:
        st.session_state["m15_win_preview_disabled"] = False
    if "m15_door_preview_disabled" not in st.session_state:
        st.session_state["m15_door_preview_disabled"] = False
    if "m15_win_preview_sig" not in st.session_state:
        st.session_state["m15_win_preview_sig"] = None
    if "m15_door_preview_sig" not in st.session_state:
        st.session_state["m15_door_preview_sig"] = None
    if "m15_show_conflict_modal" not in st.session_state:
        st.session_state["m15_show_conflict_modal"] = False
    if "m15_conflict_errors" not in st.session_state:
        st.session_state["m15_conflict_errors"] = []
    if "m15_openings_keep_expanded" not in st.session_state:
        st.session_state["m15_openings_keep_expanded"] = False
    if "m15_openings_win_wall_sel" not in st.session_state:
        st.session_state["m15_openings_win_wall_sel"] = 0
    if "m15_openings_door_wall_sel" not in st.session_state:
        st.session_state["m15_openings_door_wall_sel"] = 0
    if "m15_openings_expander_open" not in st.session_state:
        st.session_state["m15_openings_expander_open"] = False
    if "m15_parapet_wall_height" not in st.session_state:
        st.session_state["m15_parapet_wall_height"] = 1.0
    if "m15_parapet_walls" not in st.session_state:
        st.session_state["m15_parapet_walls"] = set()
    def_col_w = float(st.session_state.get("m15_new_col_b", st.session_state.get("m15_col_width_cm", 25.0)))
    def_col_l = float(st.session_state.get("m15_new_col_t", st.session_state.get("m15_col_length_cm", 60.0)))
    if "m15_col_length_cm" not in st.session_state:
        st.session_state["m15_col_length_cm"] = def_col_l
    if "m15_col_width_cm" not in st.session_state:
        st.session_state["m15_col_width_cm"] = def_col_w
    if "m15_col_placed" not in st.session_state:
        st.session_state["m15_col_placed"] = set()
    if "m15_add_col_mode" not in st.session_state:
        st.session_state["m15_add_col_mode"] = False
    if "m15_restore_col_mode" not in st.session_state:
        st.session_state["m15_restore_col_mode"] = False
    if "m15_new_col_b" not in st.session_state:
        st.session_state["m15_new_col_b"] = def_col_w
    if "m15_new_col_t" not in st.session_state:
        st.session_state["m15_new_col_t"] = def_col_l
    if "m15_new_col_model" not in st.session_state:
        st.session_state["m15_new_col_model"] = f"C({int(st.session_state['m15_new_col_b'])}x{int(st.session_state['m15_new_col_t'])})"
    if "m15_new_col_dir" not in st.session_state:
        st.session_state["m15_new_col_dir"] = "رأسي"
    if "m15_new_col_anchor" not in st.session_state:
        st.session_state["m15_new_col_anchor"] = "السنتر"
    if "m15_new_col_corner" not in st.session_state:
        st.session_state["m15_new_col_corner"] = "أعلى اليمين"
    if "m15_col_props" not in st.session_state:
        st.session_state["m15_col_props"] = {}
    if "m15_deleted_cols_history" not in st.session_state:
        st.session_state["m15_deleted_cols_history"] = {}
    if "m15_del_wall_mode" not in st.session_state:
        st.session_state["m15_del_wall_mode"] = False
    if "m15_add_wall_mode" not in st.session_state:
        st.session_state["m15_add_wall_mode"] = False
    if "m15_pending_delete_wall" not in st.session_state:
        st.session_state["m15_pending_delete_wall"] = None
    if "m15_add_win_mode" not in st.session_state:
        st.session_state["m15_add_win_mode"] = False
    if "m15_add_door_mode" not in st.session_state:
        st.session_state["m15_add_door_mode"] = False
    if "m15_named_spaces" not in st.session_state:
        st.session_state["m15_named_spaces"] = []
    if "m15_merged_wall_label_style" not in st.session_state:
        st.session_state["m15_merged_wall_label_style"] = "single"
    if "m15_new_wall_thick_choice" not in st.session_state:
        st.session_state["m15_new_wall_thick_choice"] = 12

    # تنظيف المتغيرات القديمة الخاصة بآلية الإضافة والاستعادة السابقة والمفاتيح المتضاربة
    for old_k in ["m15_add_col_sel", "m15_del_active_col_sel", "m15_confirm_del_col_tab", "m15_col_restore_expander_open"]:
        st.session_state.pop(old_k, None)
    for k in list(st.session_state.keys()):
        if k.startswith("m15_col_dir_radio_") or k.startswith("m15_col_shift_x_") or k.startswith("m15_col_shift_y_"):
            st.session_state.pop(k, None)

    _sanitize_and_prune_grid_data()

def _safe_coord_tuple(val, expected_len=None):
    """تحويل آمن لأي قيمة (tuple, list, string) إلى tuple أعداد صحيحة مع حماية كاملة ضد الاستثناءات."""
    if isinstance(val, (tuple, list)):
        try:
            t = tuple(int(x) for x in val)
            if expected_len is None or len(t) == expected_len:
                return t
        except (ValueError, TypeError):
            return None
    elif isinstance(val, str):
        cleaned = val.strip("()[] \t\r\n")
        if cleaned:
            try:
                parts = tuple(int(x.strip()) for x in cleaned.split(",") if x.strip())
                if expected_len is None or len(parts) == expected_len:
                    return parts
            except (ValueError, TypeError):
                return None
    return None

def _sanitize_and_prune_grid_data():
    """
    فحص وتطهير شامل لكافة بيانات شبكة المحاور والأعمدة والحوائط في session_state:
    1. إزالة أي سلاسل نصية أو قيم مشوهة (مثل أسماء الحوائط التنسيقية L12: C6 -> C9).
    2. حذف أي أعمدة أو حوائط خارج حدود شبكة المحاور الحالية (X, Y).
    3. ضمان أن كافة المفاتيح عبارة عن tuples عددية صحيحة 100%.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    nx = len(xs)
    ny = len(ys)
    if nx < 2 or ny < 2:
        return

    # التأكد من صحة المحاور (عدم وجود تكرار وتصاعدية الإحداثيات)
    if len(set(round(x, 4) for x in xs)) < len(xs) or sorted(xs) != xs:
        fixed_xs = [0.0]
        for i in range(1, len(xs)):
            fixed_xs.append(round(fixed_xs[-1] + 3.0, 2))
        st.session_state["m15_x_axes"] = fixed_xs
        xs = fixed_xs
        nx = len(xs)

    if len(set(round(y, 4) for y in ys)) < len(ys) or sorted(ys) != ys:
        fixed_ys = [0.0]
        for j in range(1, len(ys)):
            fixed_ys.append(round(fixed_ys[-1] + 3.0, 2))
        st.session_state["m15_y_axes"] = fixed_ys
        ys = fixed_ys
        ny = len(ys)

    # 1. تطهير الأعمدة المحذوفة (m15_col_removed)
    cr = st.session_state.get("m15_col_removed", set())
    clean_cr = set()
    for item in cr:
        t = _safe_coord_tuple(item, 2)
        if t and 0 <= t[0] < nx and 0 <= t[1] < ny:
            clean_cr.add(t)
    st.session_state["m15_col_removed"] = clean_cr

    # 1b. تطهير الأعمدة الموضوعة (m15_col_placed) — إزالة أي تقاطع خارج شبكة المحاور
    cp = st.session_state.get("m15_col_placed", set())
    clean_cp = set()
    for item in cp:
        t = _safe_coord_tuple(item, 2)
        if t and 0 <= t[0] < nx and 0 <= t[1] < ny:
            clean_cp.add(t)
    st.session_state["m15_col_placed"] = clean_cp

    # 2. تطهير اتجاهات وإزاحات الأعمدة
    for key in ["m15_col_dirs", "m15_col_shifts", "m15_col_shifted"]:
        store = st.session_state.get(key, {})
        clean_store = {}
        for k, v in store.items():
            t = _safe_coord_tuple(k, 2)
            if t and 0 <= t[0] < nx and 0 <= t[1] < ny:
                clean_store[t] = v
        st.session_state[key] = clean_store

    # 3. تطهير حوائط الدروة (m15_parapet_walls)
    pw = st.session_state.get("m15_parapet_walls", set())
    clean_pw = set()
    for item in pw:
        t = _safe_coord_tuple(item, 4)
        if t and 0 <= t[0] < nx and 0 <= t[2] < nx and 0 <= t[1] < ny and 0 <= t[3] < ny:
            clean_pw.add(t)
    st.session_state["m15_parapet_walls"] = clean_pw

    # 4. تطهير الحوائط المحذوفة (m15_wall_removed)
    rw = st.session_state.get("m15_wall_removed", set())
    clean_rw = set()
    for item in rw:
        t = _safe_coord_tuple(item, 4)
        if t and 0 <= t[0] < nx and 0 <= t[2] < nx and 0 <= t[1] < ny and 0 <= t[3] < ny:
            clean_rw.add(t)
    st.session_state["m15_wall_removed"] = clean_rw

    # 5. تطهير سمك الحوائط وارتفاعاتها وأوجه المحارة
    for key in ["m15_wall_thickness", "m15_wall_heights", "m15_plaster_faces"]:
        store = st.session_state.get(key, {})
        clean_store = {}
        for k, v in store.items():
            t = _safe_coord_tuple(k, 4)
            if t and 0 <= t[0] < nx and 0 <= t[2] < nx and 0 <= t[1] < ny and 0 <= t[3] < ny:
                clean_store[t] = v
        st.session_state[key] = clean_store

    # 6. تطهير الشبابيك والأبواب
    for key in ["m15_windows", "m15_doors"]:
        store = st.session_state.get(key, {})
        clean_store = {}
        for k, v in store.items():
            t = _safe_coord_tuple(k, 4)
            if t and 0 <= t[0] < nx and 0 <= t[2] < nx and 0 <= t[1] < ny and 0 <= t[3] < ny:
                clean_store[t] = v
        st.session_state[key] = clean_store

    # 7. تنظيف أي widget state يحتوي سلاسل نصية قديمة لحوائط الدروة
    for k in list(st.session_state.keys()):
        if k == "m15_parapet_multiselect_widget" or k.startswith("m15_parapet_ms_"):
            val = st.session_state.get(k)
            if isinstance(val, (list, set)):
                clean_val = [t for item in val if (t := _safe_coord_tuple(item, 4)) and 0 <= t[0] < nx and 0 <= t[2] < nx and 0 <= t[1] < ny and 0 <= t[3] < ny]
                st.session_state[k] = clean_val

    # 8. ضبط مواضع الفتحات (pos_m) ومفاتيح الـ widgets لتناسب أطوال الحوائط الجديدة ومنع تجاوز max_value
    for wk, w_list in list(st.session_state.get("m15_windows", {}).items()):
        t = _safe_coord_tuple(wk, 4)
        if not t:
            continue
        wlen = _wall_length_m(t)
        for w in w_list:
            if isinstance(w, dict):
                p = float(w.get("pos_m", 0.0))
                if p > wlen or p < 0.0:
                    w["pos_m"] = round(max(0.0, min(wlen, p)), 2)
                wid = w.get("id")
                if wid:
                    k = f"m15_mv_w_pos_{wid}"
                    if k in st.session_state:
                        try:
                            val = float(st.session_state[k])
                            if val > wlen or val < 0.0:
                                st.session_state[k] = round(max(0.0, min(wlen, val)), 2)
                        except (ValueError, TypeError):
                            st.session_state[k] = w["pos_m"]

    for wk, d_list in list(st.session_state.get("m15_doors", {}).items()):
        t = _safe_coord_tuple(wk, 4)
        if not t:
            continue
        wlen = _wall_length_m(t)
        for d in d_list:
            if isinstance(d, dict):
                p = float(d.get("pos_m", 0.0))
                if p > wlen or p < 0.0:
                    d["pos_m"] = round(max(0.0, min(wlen, p)), 2)
                did = d.get("id")
                if did:
                    k = f"m15_mv_d_pos_{did}"
                    if k in st.session_state:
                        try:
                            val = float(st.session_state[k])
                            if val > wlen or val < 0.0:
                                st.session_state[k] = round(max(0.0, min(wlen, val)), 2)
                        except (ValueError, TypeError):
                            st.session_state[k] = d["pos_m"]

    for k in list(st.session_state.keys()):
        if k.startswith("m15_new_win_pos_") or k.startswith("m15_new_door_pos_"):
            try:
                parts = k.split("_")[4:]
                if len(parts) == 4:
                    twk = tuple(int(x) for x in parts)
                    twlen = _wall_length_m(twk)
                    val = float(st.session_state[k])
                    if val > twlen or val < 0.0:
                        st.session_state[k] = round(max(0.0, min(twlen, val)), 2)
            except Exception:
                st.session_state.pop(k, None)

def _safe_idx(key, max_len):
    """التحقق الآمن من الفهرس في session_state ومنع تعارض الأنواع (str مع int)."""
    if max_len <= 0:
        st.session_state[key] = 0
        return 0
    val = st.session_state.get(key, 0)
    try:
        val = int(val)
        if val < 0 or val >= max_len:
            val = 0
    except (TypeError, ValueError):
        val = 0
    st.session_state[key] = val
    return val

def _get_col_name_map():
    m={}; n=1
    for (i, j) in _get_active_columns():
        m[(i, j)] = f"C{n}"; n+=1
    return m

def _get_wall_name_map():
    removed=st.session_state["m15_wall_removed"]
    m={}; n=1
    for wk in _get_all_walls():
        if wk not in removed: m[wk]=f"L{n}"; n+=1
    return m

def _next_op_id(prefix="op"):
    nid = st.session_state.get("m15_next_op_id", 1)
    st.session_state["m15_next_op_id"] = nid + 1
    return f"{prefix}_{nid}"

def _ensure_opening_names():
    """ضمان وجود معرف فريد (id) وتسلسل متتابع سليم لكافة الشبابيك والأبواب."""
    _normalize_wall_keys()
    if "m15_windows" not in st.session_state:
        st.session_state["m15_windows"] = {}
    if "m15_doors" not in st.session_state:
        st.session_state["m15_doors"] = {}

    purged = False
    for wk in list(st.session_state["m15_doors"].keys()):
        before_len = len(st.session_state["m15_doors"][wk])
        st.session_state["m15_doors"][wk] = [
            d for d in st.session_state["m15_doors"][wk]
            if d.get("id") != "door_5" and not d.get("has_conflict", False) and not d.get("is_preview", False)
        ]
        if len(st.session_state["m15_doors"][wk]) != before_len:
            purged = True
    for wk in list(st.session_state["m15_windows"].keys()):
        before_len = len(st.session_state["m15_windows"][wk])
        st.session_state["m15_windows"][wk] = [
            w for w in st.session_state["m15_windows"][wk]
            if not w.get("has_conflict", False) and not w.get("is_preview", False)
        ]
        if len(st.session_state["m15_windows"][wk]) != before_len:
            purged = True
    if purged:
        save_settings()

    for wk, wl in st.session_state["m15_windows"].items():
        for w in wl:
            if "id" not in w:
                w["id"] = _next_op_id("win")
    for wk, dl in st.session_state["m15_doors"].items():
        for d in dl:
            if "id" not in d:
                d["id"] = _next_op_id("door")

    _resequence_openings()

def _ensure_opening_ids():
    _ensure_opening_names()

def _get_active_windows_list():
    """الحصول على قائمة مرتبة هندسياً بكافة الشبابيك النشطة غير المحذوفة."""
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    active_wins = []
    seen_wids = set()
    for w_idx, wk in enumerate(all_walls):
        if wk in removed_walls:
            continue
        for win in st.session_state.get("m15_windows", {}).get(wk, []):
            wid = win.get("id")
            if not win.get("removed", False) and wid and wid not in seen_wids:
                seen_wids.add(wid)
                active_wins.append((w_idx, float(win.get("pos_m", 0.0)), win, wk))
    for wk, w_list in st.session_state.get("m15_windows", {}).items():
        if wk not in all_walls and wk not in removed_walls:
            for win in w_list:
                wid = win.get("id")
                if not win.get("removed", False) and wid and wid not in seen_wids:
                    seen_wids.add(wid)
                    active_wins.append((9999, float(win.get("pos_m", 0.0)), win, wk))
    active_wins.sort(key=lambda x: (x[0], x[1]))
    return active_wins

def _get_active_doors_list():
    """الحصول على قائمة مرتبة هندسياً بكافة الأبواب النشطة غير المحذوفة."""
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    active_doors = []
    seen_dids = set()
    for w_idx, wk in enumerate(all_walls):
        if wk in removed_walls:
            continue
        for door in st.session_state.get("m15_doors", {}).get(wk, []):
            did = door.get("id")
            if not door.get("removed", False) and did and did not in seen_dids:
                seen_dids.add(did)
                active_doors.append((w_idx, float(door.get("pos_m", 0.0)), door, wk))
    for wk, d_list in st.session_state.get("m15_doors", {}).items():
        if wk not in all_walls and wk not in removed_walls:
            for door in d_list:
                did = door.get("id")
                if not door.get("removed", False) and did and did not in seen_dids:
                    seen_dids.add(did)
                    active_doors.append((9999, float(door.get("pos_m", 0.0)), door, wk))
    active_doors.sort(key=lambda x: (x[0], x[1]))
    return active_doors

def _resequence_openings():
    """
    إعادة الترقيم والتسلسل المتتابع لكافة الشبابيك والأبواب النشطة على الرسم والبرنامج.
    صيغة الترقيم الجديدة: [رمز النموذج]-[رقم تسلسلي مستقل لكل نموذج]
    مثال: W1-1, W1-2, W2-1, W2-2, D1-1, D1-2, D2-1
    إن لم يكن للفتحة type_label (فتحات قديمة)، تُعامَل كـ W1 أو D1.
    """
    active_wins = _get_active_windows_list()
    # عداد مستقل لكل نموذج
    win_type_counters = {}
    for idx, (_, _, win, _) in enumerate(active_wins):
        type_lbl = win.get("type_label", "W1")
        if not type_lbl:
            type_lbl = "W1"
        win_type_counters[type_lbl] = win_type_counters.get(type_lbl, 0) + 1
        seq_name = f"{type_lbl}-{win_type_counters[type_lbl]}"
        win["name"] = seq_name
        wid = win.get("id")
        for wl in st.session_state.get("m15_windows", {}).values():
            for w in wl:
                if w.get("id") == wid:
                    w["name"] = seq_name

    active_doors = _get_active_doors_list()
    door_type_counters = {}
    for idx, (_, _, door, _) in enumerate(active_doors):
        type_lbl = door.get("type_label", "D1")
        if not type_lbl:
            type_lbl = "D1"
        door_type_counters[type_lbl] = door_type_counters.get(type_lbl, 0) + 1
        seq_name = f"{type_lbl}-{door_type_counters[type_lbl]}"
        door["name"] = seq_name
        did = door.get("id")
        for dl in st.session_state.get("m15_doors", {}).values():
            for d in dl:
                if d.get("id") == did:
                    d["name"] = seq_name



def _remove_opening_by_id(op_id, kind="win"):
    """
    حذف الفتحة (نقلها إلى سلة المهملات) والتأكد من وضع علامة الحذف عليها في كافة القوائم،
    ثم إعادة تسلسل الفتحات النشطة فوراً لضبط الرسم والبرنامج.
    """
    store = st.session_state.get("m15_windows" if kind == "win" else "m15_doors", {})
    for wk in list(store.keys()):
        for op in store[wk]:
            if op.get("id") == op_id:
                op["removed"] = True
    _resequence_openings()
    save_settings()

def _next_window_name(type_label="W1"):
    """إرجاع اسم الشباك التالي بناءً على النموذج المختار."""
    active_wins = _get_active_windows_list()
    count = sum(1 for (_, _, w, _) in active_wins if w.get("type_label", "W1") == type_label)
    return f"{type_label}-{count + 1}"

def _next_door_name(type_label="D1"):
    """إرجاع اسم الباب التالي بناءً على النموذج المختار."""
    active_doors = _get_active_doors_list()
    count = sum(1 for (_, _, d, _) in active_doors if d.get("type_label", "D1") == type_label)
    return f"{type_label}-{count + 1}"

def _get_window_name_map():
    """خريطة id → اسم لكل شباك نشط (تعكس الترقيم الحالي)."""
    m = {}
    win_type_counters = {}
    active_wins = _get_active_windows_list()
    for (_, _, win, _) in active_wins:
        type_lbl = win.get("type_label", "W1") or "W1"
        win_type_counters[type_lbl] = win_type_counters.get(type_lbl, 0) + 1
        m[win["id"]] = f"{type_lbl}-{win_type_counters[type_lbl]}"
    return m


def _get_door_name_map():
    m = {}
    door_type_counters = {}
    active_doors = _get_active_doors_list()
    for (_, _, door, _) in active_doors:
        type_lbl = door.get("type_label", "D1") or "D1"
        door_type_counters[type_lbl] = door_type_counters.get(type_lbl, 0) + 1
        m[door["id"]] = f"{type_lbl}-{door_type_counters[type_lbl]}"
    return m



def _get_wall_clear_length(wk):
    """حساب الطول الصافي المتاح للحائط بين أوجه الأعمدة الطرفية (أو طرفي الحائط)."""
    res = _get_column_bounds_along_wall(wk)
    if isinstance(res, (tuple, list)) and len(res) >= 2:
        col1_l = res[0]
        col2_l = res[1]
        return max(0.0, float(col2_l) - float(col1_l))
    return float(_wall_length_m(wk))

def _wall_display_label(w_key, cm, wm):
    t = _safe_coord_tuple(w_key, 4)
    if not t:
        return str(w_key)
    i1, j1, i2, j2 = t
    cs = cm.get((i1, j1), f"({i1+1},{j1+1})")
    ce = cm.get((i2, j2), f"({i2+1},{j2+1})")
    return f"{wm.get(t, '—')}: {cs}\u2192{ce}"

def _compute_effective_walls():
    """
    يحسب الحوائط الفعالة لموديول 15:
    - دمج الحوائط المتلاصقة على نفس الاستقامة في حائط واحد متصل وبطول إجمالي موحد،
      طالما لا يفصل بينها عمود نشط أو حائط متعامد، وتتطابق في السُمك وحالة الدروة والحذف.
    - يتيح ذلك إسقاط الشبابيك والأبواب على كامل طول الحائط المدمج (مثل L49 بطول 3.8م).
    """
    placed = st.session_state.get("m15_walls_placed", [])
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    nx, ny = len(xs), len(ys)
    if nx < 2 or ny < 2 or not placed:
        return []

    h_intervals = {}
    v_intervals = {}

    for item in placed:
        t = _safe_coord_tuple(item, 4)
        if not t:
            continue
        i1, j1, i2, j2 = t
        if j1 == j2:  # حائط أفقي على المحور Y_j
            i_min, i_max = min(i1, i2), max(i1, i2)
            for k in range(i_min, i_max):
                if 0 <= k < nx - 1 and 0 <= j1 < ny:
                    h_intervals.setdefault(j1, set()).add((k, k + 1))
        elif i1 == i2:  # حائط رأسي على المحور X_i
            j_min, j_max = min(j1, j2), max(j1, j2)
            for k in range(j_min, j_max):
                if 0 <= k < ny - 1 and 0 <= i1 < nx:
                    v_intervals.setdefault(i1, set()).add((k, k + 1))

    active_cols = set(_get_active_columns())
    removed_walls = st.session_state.get("m15_wall_removed", set())

    def _is_unit_removed(s):
        if not removed_walls:
            return False
        if s in removed_walls:
            return True
        i1, j1, i2, j2 = s
        for rw in removed_walls:
            t = _safe_coord_tuple(rw, 4)
            if not t:
                continue
            ri1, rj1, ri2, rj2 = t
            if j1 == j2 == rj1 == rj2:
                if min(ri1, ri2) <= min(i1, i2) and max(ri1, ri2) >= max(i1, i2):
                    return True
            elif i1 == i2 == ri1 == ri2:
                if min(rj1, rj2) <= min(j1, j2) and max(rj1, rj2) >= max(j1, j2):
                    return True
        return False

    def _has_active_perp_at_h(k, j):
        if k in v_intervals:
            if j > 0 and (j - 1, j) in v_intervals[k]:
                if not _is_unit_removed((k, j - 1, k, j)):
                    return True
            if j < ny - 1 and (j, j + 1) in v_intervals[k]:
                if not _is_unit_removed((k, j, k, j + 1)):
                    return True
        return False

    def _has_active_perp_at_v(i, k):
        if k in h_intervals:
            if i > 0 and (i - 1, i) in h_intervals[k]:
                if not _is_unit_removed((i - 1, k, i, k)):
                    return True
            if i < nx - 1 and (i, i + 1) in h_intervals[k]:
                if not _is_unit_removed((i, k, i + 1, k)):
                    return True
        return False

    effective = []

    # 1. دمج الحوائط الأفقية المتلاصقة
    for j in sorted(h_intervals.keys()):
        unit_list = sorted(list(h_intervals[j]), key=lambda u: u[0])
        if not unit_list:
            continue
        cur_start_i, cur_end_i = unit_list[0]
        cur_seg = (cur_start_i, j, cur_end_i, j)
        cur_rem = _is_unit_removed(cur_seg)
        cur_th = _get_wall_thickness(cur_seg)
        cur_pw = _is_parapet_wall(cur_seg)

        for nxt in unit_list[1:]:
            nxt_start_i, nxt_end_i = nxt
            if nxt_start_i == cur_end_i:
                mid_k = cur_end_i
                nxt_seg = (nxt_start_i, j, nxt_end_i, j)
                nxt_rem = _is_unit_removed(nxt_seg)
                nxt_th = _get_wall_thickness(nxt_seg)
                nxt_pw = _is_parapet_wall(nxt_seg)

                has_col = (mid_k, j) in active_cols
                has_perp = _has_active_perp_at_h(mid_k, j)
                same_state = (cur_rem == nxt_rem) and (cur_th == nxt_th) and (cur_pw == nxt_pw)

                if not has_col and not has_perp and same_state:
                    cur_end_i = nxt_end_i
                    continue

            effective.append((cur_start_i, j, cur_end_i, j))
            cur_start_i, cur_end_i = nxt_start_i, nxt_end_i
            cur_seg = (cur_start_i, j, cur_end_i, j)
            cur_rem = _is_unit_removed(cur_seg)
            cur_th = _get_wall_thickness(cur_seg)
            cur_pw = _is_parapet_wall(cur_seg)

        effective.append((cur_start_i, j, cur_end_i, j))

    # 2. دمج الحوائط الرأسية المتلاصقة
    for i in sorted(v_intervals.keys()):
        unit_list = sorted(list(v_intervals[i]), key=lambda u: u[0])
        if not unit_list:
            continue
        cur_start_j, cur_end_j = unit_list[0]
        cur_seg = (i, cur_start_j, i, cur_end_j)
        cur_rem = _is_unit_removed(cur_seg)
        cur_th = _get_wall_thickness(cur_seg)
        cur_pw = _is_parapet_wall(cur_seg)

        for nxt in unit_list[1:]:
            nxt_start_j, nxt_end_j = nxt
            if nxt_start_j == cur_end_j:
                mid_k = cur_end_j
                nxt_seg = (i, nxt_start_j, i, nxt_end_j)
                nxt_rem = _is_unit_removed(nxt_seg)
                nxt_th = _get_wall_thickness(nxt_seg)
                nxt_pw = _is_parapet_wall(nxt_seg)

                has_col = (i, mid_k) in active_cols
                has_perp = _has_active_perp_at_v(i, mid_k)
                same_state = (cur_rem == nxt_rem) and (cur_th == nxt_th) and (cur_pw == nxt_pw)

                if not has_col and not has_perp and same_state:
                    cur_end_j = nxt_end_j
                    continue

            effective.append((i, cur_start_j, i, cur_end_j))
            cur_start_j, cur_end_j = nxt_start_j, nxt_end_j
            cur_seg = (i, cur_start_j, i, cur_end_j)
            cur_rem = _is_unit_removed(cur_seg)
            cur_th = _get_wall_thickness(cur_seg)
            cur_pw = _is_parapet_wall(cur_seg)

        effective.append((i, cur_start_j, i, cur_end_j))

    return effective


def _get_all_walls():
    """كافة الحوائط الفعالة لموديول 15 (كل فترة بين تقاطعين متجاورين حائط مستقل)."""
    return _compute_effective_walls()


def _get_wall_for_segment(seg, walls_list=None):
    """
    إرجاع الحائط الفعلي (المدمج أو المنفصل) من قائمة الحوائط الذي يغطي القطعة المعطاة (i1, j1, i2, j2).
    """
    t = _safe_coord_tuple(seg, 4)
    if not t:
        return None
    if walls_list is None:
        walls_list = _get_all_walls()
    i1, j1, i2, j2 = t
    if j1 == j2:
        si_min, si_max = min(i1, i2), max(i1, i2)
        for w in walls_list:
            if w[1] == w[3] == j1:
                wi_min, wi_max = min(w[0], w[2]), max(w[0], w[2])
                if wi_min <= si_min and wi_max >= si_max:
                    return w
    else:
        sj_min, sj_max = min(j1, j2), max(j1, j2)
        for w in walls_list:
            if w[0] == w[2] == i1:
                wj_min, wj_max = min(w[1], w[3]), max(w[1], w[3])
                if wj_min <= sj_min and wj_max >= sj_max:
                    return w
    return None



def _get_all_columns():
    """كافة أعمدة المشروع الافتراضية عند تقاطعات المحاور."""
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    return [(i, j) for j in range(len(ys)) for i in range(len(xs))]

def _get_active_columns():
    """
    الأعمدة النشطة الفعلية فقط:
    - من قائمة الأعمدة الموضوعة (m15_col_placed) التي تحتوي على التقاطعات التي أضافها المستخدم
    - مطروحاً منها الأعمدة المحذوفة (m15_col_removed)
    - محاذرةً أي تقاطع خارج حدود شبكة المحاور الحالية
    """
    placed = st.session_state.get("m15_col_placed", set())
    if not isinstance(placed, set):
        placed = set(_safe_coord_tuple(item, 2) for item in placed if _safe_coord_tuple(item, 2))
    removed = st.session_state.get("m15_col_removed", set())
    if not isinstance(removed, set):
        removed = set(_safe_coord_tuple(item, 2) for item in removed if _safe_coord_tuple(item, 2))
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    nx, ny = len(xs), len(ys)
    return [
        (i, j) for (i, j) in sorted(placed)
        if (i, j) not in removed and 0 <= i < nx and 0 <= j < ny
    ]


def _get_merged_wall_display_groups():
    """
    تجميع الحوائط المتلاصقة على نفس الاستقامة في المسقط الأفقي المصمم:
    - الحوائط المتلاصقة التي لا يفصلها عمود نشط ولا حائط متعامد عليها،
      والتي تشترك في نفس السُمك ونفس حالة الدروة،
      يتم دمجها في مجموعة واحدة لوضع اسم واحد موحد لها في منتصف الحائط المدمج.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    removed_walls = st.session_state.get("m15_wall_removed", set())
    all_walls = _get_all_walls()
    active_walls = [w for w in all_walls if w not in removed_walls]
    if not active_walls or len(xs) < 2 or len(ys) < 2:
        return []

    active_cols = set(_get_active_columns())
    active_set = set(active_walls)
    parapet_set = set(st.session_state.get("m15_parapet_walls", set()))

    groups = []

    # 1. الحوائط الأفقية مجمعة حسب خط المحور Y_j
    h_by_j = {}
    for w in active_walls:
        if w[1] == w[3]:
            h_by_j.setdefault(w[1], []).append(w)

    for j, segs in sorted(h_by_j.items()):
        segs.sort(key=lambda x: (min(x[0], x[2]), max(x[0], x[2])))
        cur_group = [segs[0]]
        for nxt in segs[1:]:
            prev = cur_group[-1]
            prev_x_max = max(prev[0], prev[2])
            nxt_x_min = min(nxt[0], nxt[2])
            if prev_x_max == nxt_x_min:
                mid_pt = (prev_x_max, j)
                has_col = mid_pt in active_cols
                # فحص الحوائط المتعامدة (الرأسية) التي تلتقي عند نقطة الاتصال
                has_perp = (
                    (prev_x_max, j - 1, prev_x_max, j) in active_set or
                    (prev_x_max, j, prev_x_max, j + 1) in active_set
                )
                same_th = (_get_wall_thickness(prev) == _get_wall_thickness(nxt))
                same_parapet = ((prev in parapet_set) == (nxt in parapet_set))
                if not has_col and not has_perp and same_th and same_parapet:
                    cur_group.append(nxt)
                    continue
            groups.append(cur_group)
            cur_group = [nxt]
        if cur_group:
            groups.append(cur_group)

    # 2. الحوائط الرأسية مجمعة حسب خط المحور X_i
    v_by_i = {}
    for w in active_walls:
        if w[0] == w[2]:
            v_by_i.setdefault(w[0], []).append(w)

    for i, segs in sorted(v_by_i.items()):
        segs.sort(key=lambda x: (min(x[1], x[3]), max(x[1], x[3])))
        cur_group = [segs[0]]
        for nxt in segs[1:]:
            prev = cur_group[-1]
            prev_y_max = max(prev[1], prev[3])
            nxt_y_min = min(nxt[1], nxt[3])
            if prev_y_max == nxt_y_min:
                mid_pt = (i, prev_y_max)
                has_col = mid_pt in active_cols
                # فحص الحوائط المتعامدة (الأفقية) التي تلتقي عند نقطة الاتصال
                has_perp = (
                    (i - 1, prev_y_max, i, prev_y_max) in active_set or
                    (i, prev_y_max, i + 1, prev_y_max) in active_set
                )
                same_th = (_get_wall_thickness(prev) == _get_wall_thickness(nxt))
                same_parapet = ((prev in parapet_set) == (nxt in parapet_set))
                if not has_col and not has_perp and same_th and same_parapet:
                    cur_group.append(nxt)
                    continue
            groups.append(cur_group)
            cur_group = [nxt]
        if cur_group:
            groups.append(cur_group)

    return groups


def _sync_wall_stores_to_effective_walls():
    """
    مزامنة وتوحيد بيانات الحوائط (السمك، الارتفاع، الدروة، الحذف، والفتحات)
    مع الحوائط الفعالة المدمجة الحالية لضمان بقاء الفتحات على الحائط المدمج بكامل طوله.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        return

    eff_walls = _compute_effective_walls()
    if not eff_walls:
        return

    wt = st.session_state.get("m15_wall_thickness", {})
    wh = st.session_state.get("m15_wall_heights", {})
    pw = set(st.session_state.get("m15_parapet_walls", set()))

    for ew in eff_walls:
        if ew not in wt:
            wt[ew] = _get_wall_thickness(ew)
        if ew not in wh:
            wh[ew] = _get_wall_height(ew)
        if _is_parapet_wall(ew):
            pw.add(ew)

    st.session_state["m15_wall_thickness"] = wt
    st.session_state["m15_wall_heights"] = wh
    st.session_state["m15_parapet_walls"] = pw

    for kind_key in ["m15_windows", "m15_doors"]:
        store = st.session_state.get(kind_key, {})
        new_store = {}
        for old_wk, ops in list(store.items()):
            t = _safe_coord_tuple(old_wk, 4)
            if not t or not ops:
                continue
            matched_eff = _get_wall_for_segment(t, eff_walls)
            target_wk = matched_eff if matched_eff else t
            offset = 0.0
            if matched_eff and matched_eff != t:
                if t[1] == t[3] == matched_eff[1] == matched_eff[3]:
                    offset = abs(xs[min(t[0], t[2])] - xs[min(matched_eff[0], matched_eff[2])])
                elif t[0] == t[2] == matched_eff[0] == matched_eff[2]:
                    offset = abs(ys[min(t[1], t[3])] - ys[min(matched_eff[1], matched_eff[3])])

            target_list = new_store.setdefault(target_wk, [])
            seen_ids = set(op.get("id") for op in target_list if op.get("id"))
            for op in ops:
                oid = op.get("id")
                if oid and oid in seen_ids:
                    continue
                if oid:
                    seen_ids.add(oid)
                op_c = dict(op)
                op_c["wk"] = target_wk
                if matched_eff and matched_eff != t and offset > 0:
                    op_c["pos_m"] = round(float(op.get("pos_m", 0.0)) + offset, 2)
                target_list.append(op_c)

        st.session_state[kind_key] = new_store

    # 4. مزامنة وتوحيد أوجه المحارة مع الحوائط الفعالة المدمجة
    pf = st.session_state.get("m15_plaster_faces", {})
    new_pf = {}
    for old_wk, faces in pf.items():
        t = _safe_coord_tuple(old_wk, 4)
        if not t or not faces:
            continue
        matched_eff = _get_wall_for_segment(t, eff_walls)
        target_wk = matched_eff if matched_eff else t
        cur_list = new_pf.setdefault(target_wk, [])
        for f in faces:
            if f not in cur_list:
                cur_list.append(f)
    st.session_state["m15_plaster_faces"] = new_pf


def _normalize_wall_keys():
    """
    تسوية مفاتيح الحوائط لضمان مطابقتها لحدود شبكة المحاور الحالية وتوحيد الفتحات على الحوائط المدمجة.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    nx = len(xs)
    ny = len(ys)
    if nx < 2 or ny < 2:
        return

    # 0. تسوية قائمة الحوائط الموضوعة (m15_walls_placed)
    placed = st.session_state.get("m15_walls_placed", [])
    new_placed = []
    for item in placed:
        t = _safe_coord_tuple(item, 4)
        if not t:
            continue
        i1, j1, i2, j2 = t
        if j1 == j2:
            i_min, i_max = min(i1, i2), max(i1, i2)
            for k in range(i_min, i_max):
                if 0 <= k < nx - 1 and 0 <= j1 < ny:
                    seg = (k, j1, k + 1, j1)
                    if seg not in new_placed:
                        new_placed.append(seg)
        elif i1 == i2:
            j_min, j_max = min(j1, j2), max(j1, j2)
            for k in range(j_min, j_max):
                if 0 <= k < ny - 1 and 0 <= i1 < nx:
                    seg = (i1, k, i1, k + 1)
                    if seg not in new_placed:
                        new_placed.append(seg)
        else:
            if max(i1, i2) < nx and max(j1, j2) < ny:
                if t not in new_placed:
                    new_placed.append(t)
    st.session_state["m15_walls_placed"] = new_placed

    # 1. تسوية سمك الحوائط
    wt = st.session_state.get("m15_wall_thickness", {})
    new_wt = {}
    for wk, val in wt.items():
        t = _safe_coord_tuple(wk, 4)
        if not t:
            continue
        if max(t[0], t[2]) < nx and max(t[1], t[3]) < ny:
            new_wt[t] = val
    st.session_state["m15_wall_thickness"] = new_wt

    # 2. تسوية ارتفاعات الحوائط
    wh = st.session_state.get("m15_wall_heights", {})
    new_wh = {}
    for wk, val in wh.items():
        t = _safe_coord_tuple(wk, 4)
        if not t:
            continue
        if max(t[0], t[2]) < nx and max(t[1], t[3]) < ny:
            new_wh[t] = val
    st.session_state["m15_wall_heights"] = new_wh

    # 2.5 تسوية حوائط الدروة
    pw = st.session_state.get("m15_parapet_walls", set())
    new_pw = set()
    for wk in pw:
        t = _safe_coord_tuple(wk, 4)
        if not t:
            continue
        if max(t[0], t[2]) < nx and max(t[1], t[3]) < ny:
            new_pw.add(t)
    st.session_state["m15_parapet_walls"] = new_pw

    # 3. تسوية الحوائط المحذوفة
    rw = st.session_state.get("m15_wall_removed", set())
    new_rw = set()
    for wk in rw:
        t = _safe_coord_tuple(wk, 4)
        if not t:
            continue
        if max(t[0], t[2]) < nx and max(t[1], t[3]) < ny:
            new_rw.add(t)
    st.session_state["m15_wall_removed"] = new_rw

    # 4. مزامنة الفتحات مع الحوائط المدمجة
    _sync_wall_stores_to_effective_walls()

    # 5. تسوية أوجه المحارة المحددة
    pf = st.session_state.get("m15_plaster_faces", {})
    new_pf = {}
    for wk, val in pf.items():
        t = _safe_coord_tuple(wk, 4)
        if not t:
            continue
        if max(t[0], t[2]) < nx and max(t[1], t[3]) < ny:
            new_pf[t] = list(val)
    st.session_state["m15_plaster_faces"] = new_pf

def _wall_length_m(wk):
    t = _safe_coord_tuple(wk, 4)
    if not t:
        return 0.0
    i1, j1, i2, j2 = t
    xs = st.session_state.get("m15_x_axes", []); ys = st.session_state.get("m15_y_axes", [])
    if j1 == j2:
        if i1 < len(xs) and i2 < len(xs):
            return abs(xs[i2] - xs[i1])
    else:
        if j1 < len(ys) and j2 < len(ys):
            return abs(ys[j2] - ys[j1])
    return 0.0

def _get_col_wh(i, j):
    props = st.session_state.get("m15_col_props", {}).get((i, j))
    if props and "b_cm" in props and "t_cm" in props:
        col_w = float(props["b_cm"]) / 100.0
        col_l = float(props["t_cm"]) / 100.0
        d = props.get("dir_code") or st.session_state.get("m15_col_dirs", {}).get((i, j), "NS")
    else:
        col_l = float(st.session_state.get("m15_col_length_cm", 60.0)) / 100.0
        col_w = float(st.session_state.get("m15_col_width_cm", 30.0)) / 100.0
        d = st.session_state.get("m15_col_dirs", {}).get((i, j), "NS")
    cw, ch = (col_w, col_l) if d == "NS" else (col_l, col_w)
    return cw, ch

def _get_col_size():
    col_l = float(st.session_state.get("m15_col_length_cm", 60.0)) / 100.0
    col_w = float(st.session_state.get("m15_col_width_cm", 30.0)) / 100.0
    return max(col_l, col_w)

def _normalize_m15_col_shift(val, axis="x"):
    s = str(val or "").strip()
    if axis == "x":
        if "جسم العمود يمين" in s or s.startswith("يمين") or "Right" in s.capitalize() or "+X" in s:
            return M15_SHIFT_X_OPTIONS[1]
        elif "جسم العمود يسار" in s or s.startswith("يسار") or "Left" in s.capitalize() or "-X" in s:
            return M15_SHIFT_X_OPTIONS[2]
        return M15_SHIFT_X_OPTIONS[0]
    else:
        if "جسم العمود لأعلى" in s or "جسم العمود لاعلي" in s or s.startswith("أعلى") or s.startswith("اعلي") or "Top" in s.capitalize() or "Up" in s.capitalize() or "+Y" in s:
            return M15_SHIFT_Y_OPTIONS[1]
        elif "جسم العمود لأسفل" in s or "جسم العمود لاسفل" in s or s.startswith("أسفل") or s.startswith("اسفل") or "Bottom" in s.capitalize() or "Down" in s.capitalize() or "-Y" in s:
            return M15_SHIFT_Y_OPTIONS[2]
        return M15_SHIFT_Y_OPTIONS[0]

def _compute_col_offsets(cw_m, ch_m, sx_choice, sy_choice):
    """
    حساب إزاحة مركز العمود (dx_m, dy_m) بالمتر بالنسبة لتقاطع المحاور بناءً على:
    - أبعاد العمود الصافية المعتمدة (cw_m موازياً لمحور X، و ch_m موازياً لمحور Y).
    - الترحيل الأفقي (X):
        * جسم العمود يميناً (الوجه يسار المحور - 6 cm): الوجه الأيسر = -0.06م => المركز = cw_m/2 - 0.06
        * جسم العمود يساراً (الوجه يمين المحور + 6 cm): الوجه الأيمن = +0.06م => المركز = 0.06 - cw_m/2
        * متمركز على المحور: المركز = 0.0
    - الترحيل الرأسي (Y):
        * جسم العمود لأعلى (الوجه أسفل المحور - 6 cm): الوجه السفلي = -0.06م => المركز = ch_m/2 - 0.06
        * جسم العمود لأسفل (الوجه أعلى المحور + 6 cm): الوجه العلوي = +0.06م => المركز = 0.06 - ch_m/2
        * متمركز على المحور: المركز = 0.0
    يُرجع: (dx_m, dy_m)
    """
    off_m = 0.06  # 6 cm in meters
    norm_sx = _normalize_m15_col_shift(sx_choice, axis="x")
    norm_sy = _normalize_m15_col_shift(sy_choice, axis="y")

    if norm_sx == M15_SHIFT_X_OPTIONS[1]:
        dx_m = (cw_m / 2.0) - off_m
    elif norm_sx == M15_SHIFT_X_OPTIONS[2]:
        dx_m = off_m - (cw_m / 2.0)
    else:
        dx_m = 0.0

    if norm_sy == M15_SHIFT_Y_OPTIONS[1]:
        dy_m = (ch_m / 2.0) - off_m
    elif norm_sy == M15_SHIFT_Y_OPTIONS[2]:
        dy_m = off_m - (ch_m / 2.0)
    else:
        dy_m = 0.0

    return dx_m, dy_m

def _col_center(i, j):
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if i >= len(xs) or j >= len(ys):
        return 0.0, 0.0
    col_shifts = st.session_state.get("m15_col_shifts", {})
    if (i, j) in col_shifts:
        tr = col_shifts[(i, j)]
        cw, ch = _get_col_wh(i, j)
        dx_m, dy_m = _compute_col_offsets(cw, ch, tr.get("shift_x"), tr.get("shift_y"))
        return xs[i] + dx_m, ys[j] + dy_m
    col_shifted = st.session_state.get("m15_col_shifted", {})
    dx, dy = col_shifted.get((i, j), (0.0, 0.0))
    return xs[i] + dx / 100.0, ys[j] + dy / 100.0

def _record_col_deletion(ci, cj):
    """
    تسجيل بيانات وخصائص العمود الأصلية في سجل المحذوفات (Deleted Columns History)
    بحيث يتم استعادتها لاحقاً بكامل خصائصها الأصلية (النموذج، الأبعاد، الاتجاه، والإحداثيات).
    """
    history = st.session_state.setdefault("m15_deleted_cols_history", {})
    props = st.session_state.get("m15_col_props", {}).get((ci, cj), {})
    dirs = st.session_state.get("m15_col_dirs", {})
    shifts = st.session_state.get("m15_col_shifts", {})
    shifted = st.session_state.get("m15_col_shifted", {})
    cn = _get_col_name_map()
    orig_name = cn.get((ci, cj), f"C(Y{ci+1},X{cj+1})")

    dir_code = dirs.get((ci, cj), "NS")
    tr = shifts.get((ci, cj), {})
    shift_x = tr.get("shift_x", "متمركز على المحور")
    shift_y = tr.get("shift_y", "متمركز على المحور")
    b_cm = props.get("b_cm", float(st.session_state.get("m15_col_width_cm", 30.0)))
    t_cm = props.get("t_cm", float(st.session_state.get("m15_col_length_cm", 60.0)))

    history[(ci, cj)] = {
        "model": props.get("model", f"{orig_name}: {int(round(b_cm))}x{int(round(t_cm))}"),
        "b_cm": b_cm,
        "t_cm": t_cm,
        "dir": props.get("dir", "رأسي" if dir_code == "NS" else "أفقي"),
        "dir_code": dir_code,
        "anchor": props.get("anchor", "السنتر"),
        "corner": props.get("corner", "السنتر"),
        "shift_x": shift_x,
        "shift_y": shift_y,
        "shifted": shifted.get((ci, cj), (0.0, 0.0)),
        "deleted_at": time.time(),
        "name": orig_name
    }
    st.session_state["m15_deleted_cols_history"] = history

def _get_column_bounds_along_wall(wk):
    """
    حساب حدود أوجه الأعمدة الخرسانية على طول الحائط (wk) لتحديد المسافة الصافية المتاحة للفتحات.
    يُرجع: (col1_limit_m, col2_limit_m, col1_name, col2_name, wlen)
    """
    t = _safe_coord_tuple(wk, 4)
    if not t:
        return 0.0, 0.0, None, None, 0.0
    i1, j1, i2, j2 = t
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if max(i1, i2) >= len(xs) or max(j1, j2) >= len(ys):
        return 0.0, 0.0, None, None, 0.0
    active_set = set(_get_active_columns())
    cm = _get_col_name_map()
    wlen = _wall_length_m(t)
    is_h = (j1 == j2)
    
    if is_h:
        x_min_w = min(xs[i1], xs[i2])
        i_start = min(i1, i2)
        i_end = max(i1, i2)
        # العمود في بداية الحائط (يسار)
        if (i_start, j1) in active_set:
            cx1, cy1 = _col_center(i_start, j1)
            cw1, _ = _get_col_wh(i_start, j1)
            col1_limit = max(0.0, (cx1 + cw1 / 2.0) - x_min_w)
            col1_name = cm.get((i_start, j1), f"C({i_start+1},{j1+1})")
        else:
            col1_limit = 0.0
            col1_name = None
        
        # العمود في نهاية الحائط (يمين)
        if (i_end, j1) in active_set:
            cx2, cy2 = _col_center(i_end, j1)
            cw2, _ = _get_col_wh(i_end, j1)
            col2_limit = min(wlen, (cx2 - cw2 / 2.0) - x_min_w)
            col2_name = cm.get((i_end, j1), f"C({i_end+1},{j1+1})")
        else:
            col2_limit = wlen
            col2_name = None
    else:
        y_min_w = min(ys[j1], ys[j2])
        j_start = min(j1, j2)
        j_end = max(j1, j2)
        # العمود في بداية الحائط (أسفل)
        if (i1, j_start) in active_set:
            cx1, cy1 = _col_center(i1, j_start)
            _, ch1 = _get_col_wh(i1, j_start)
            col1_limit = max(0.0, (cy1 + ch1 / 2.0) - y_min_w)
            col1_name = cm.get((i1, j_start), f"C({i1+1},{j_start+1})")
        else:
            col1_limit = 0.0
            col1_name = None
            
        # العمود في نهاية الحائط (أعلى)
        if (i1, j_end) in active_set:
            cx2, cy2 = _col_center(i1, j_end)
            _, ch2 = _get_col_wh(i1, j_end)
            col2_limit = min(wlen, (cy2 - ch2 / 2.0) - y_min_w)
            col2_name = cm.get((i1, j_end), f"C({i1+1},{j_end+1})")
        else:
            col2_limit = wlen
            col2_name = None
            
    return col1_limit, col2_limit, col1_name, col2_name, wlen

def _get_wall_cross_bounds(wk):
    """
    حساب حدود الحائط العرضية وإزاحتها بالنسبة للمحور مع مراعاة اشتراطات حدود الجار:
    - للحوائط على المحاور الخارجية (أول/آخر محور X، أول/آخر محور Y) عندما تكون التخانة 25 سم:
      الجزء الخارجي جهة الجار لا يزيد عن 6 سم (0.06م)، وباقي الـ 19 سم (0.19م) يكون لداخل المبنى.
    - للحوائط الداخلية أو الحوائط بسمك 12 سم: الحائط يتمركز على المحور بالتساوي (half_t من كل جهة).
    يُرجع: (min_coord, max_coord, center_coord, thick_m)
    """
    t = _safe_coord_tuple(wk, 4)
    if not t:
        return 0.0, 0.0, 0.0, 0.12
    i1, j1, i2, j2 = t
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if max(i1, i2) >= len(xs) or max(j1, j2) >= len(ys):
        return 0.0, 0.0, 0.0, 0.12
    thick = _get_wall_thickness(t)
    thick_m = thick / 100.0
    half_t = thick / 200.0
    is_h = (j1 == j2)

    if is_h:
        y_axis = ys[j1] if j1 < len(ys) else 0.0
        min_j = min(j1, j2)
        if min_j == 0 and len(ys) > 1 and thick == _WALL_THICK:
            # أول محور Y (حد الجار السفلي): 6 سم للخارج (أسفل) و 19 سم للداخل (أعلى)
            y_min = y_axis - 0.06
            y_max = y_axis + (thick_m - 0.06)
        elif min_j == (len(ys) - 1) and len(ys) > 1 and thick == _WALL_THICK:
            # آخر محور Y (حد الجار العلوي): 6 سم للخارج (أعلى) و 19 سم للداخل (أسفل)
            y_min = y_axis - (thick_m - 0.06)
            y_max = y_axis + 0.06
        else:
            # حائط داخلي أو سمك 12 سم: متمركز على المحور
            y_min = y_axis - half_t
            y_max = y_axis + half_t
        y_c = (y_min + y_max) / 2.0
        return y_min, y_max, y_c, thick_m
    else:
        x_axis = xs[i1] if i1 < len(xs) else 0.0
        min_i = min(i1, i2)
        if min_i == 0 and len(xs) > 1 and thick == _WALL_THICK:
            # أول محور X (حد الجار الأيسر): 6 سم للخارج (يسار) و 19 سم للداخل (يمين)
            x_min = x_axis - 0.06
            x_max = x_axis + (thick_m - 0.06)
        elif min_i == (len(xs) - 1) and len(xs) > 1 and thick == _WALL_THICK:
            # آخر محور X (حد الجار الأيمن): 6 سم للخارج (يمين) و 19 سم للداخل (يسار)
            x_min = x_axis - (thick_m - 0.06)
            x_max = x_axis + 0.06
        else:
            # حائط داخلي أو سمك 12 سم: متمركز على المحور
            x_min = x_axis - half_t
            x_max = x_axis + half_t
        x_c = (x_min + x_max) / 2.0
        return x_min, x_max, x_c, thick_m

def _validate_opening_coords(wk, op_name, op_type, w_m, h_m, pos_m, leaf_dir=None, current_op_id=None):
    """
    التحقق الهندسي الدقيق من إحداثيات الفتحة:
    1- التداخل والتعارض مع إحداثيات أي عمود قائم في المبنى.
    2- الخروج خارج حدود المسقط الأفقي العام أو حدود الحائط.
    """
    errors = []
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if not xs or not ys:
        return errors

    x_plan_min, x_plan_max = min(xs), max(xs)
    y_plan_min, y_plan_max = min(ys), max(ys)

    i1, j1, i2, j2 = wk
    is_h = (j1 == j2)
    wlen = _wall_length_m(wk)
    cross_min, cross_max, cross_c, thick_m = _get_wall_cross_bounds(wk)
    w_val = float(w_m)
    pos = float(pos_m)

    # 1. حساب حدود الفتحة في المسقط الأفقي (2D Bounding Box) — pos يمثل بداية الفتحة من بداية الحائط
    if is_h:
        x_base = min(xs[i1], xs[i2])
        op_xmin = x_base + pos
        op_xmax = x_base + pos + w_val
        y_wall = cross_c
        op_ymin = cross_min
        op_ymax = cross_max

        # فحص الخروج عن بداية أو نهاية الحائط
        if pos < -0.005:
            errors.append(f"خروج {op_name} خارج بداية الحائط بمقدار {abs(pos):.2f}م!")
        if (pos + w_val) > wlen + 0.005:
            errors.append(f"خروج {op_name} خارج نهاية الحائط بمقدار {(pos + w_val - wlen):.2f}م!")
    else:
        y_base = min(ys[j1], ys[j2])
        op_ymin = y_base + pos
        op_ymax = y_base + pos + w_val
        x_wall = cross_c
        op_xmin = cross_min
        op_xmax = cross_max

        # فحص الخروج عن بداية أو نهاية الحائط
        if pos < -0.005:
            errors.append(f"خروج {op_name} خارج بداية الحائط بمقدار {abs(pos):.2f}م!")
        if (pos + w_val) > wlen + 0.005:
            errors.append(f"خروج {op_name} خارج نهاية الحائط بمقدار {(pos + w_val - wlen):.2f}م!")

    # 2. فحص التداخل مع إحداثيات أي عمود قائم في المشروع
    cm = _get_col_name_map()

    for (ci, cj) in _get_active_columns():
        cx_center, cy_center = _col_center(ci, cj)
        col_w, col_h = _get_col_wh(ci, cj)
        col_xmin = cx_center - col_w / 2.0
        col_xmax = cx_center + col_w / 2.0
        col_ymin = cy_center - col_h / 2.0
        col_ymax = cy_center + col_h / 2.0

        # التحقق من تداخل مستطيل الفتحة مع مستطيل العمود
        ov_x = min(op_xmax, col_xmax) - max(op_xmin, col_xmin)
        ov_y = min(op_ymax, col_ymax) - max(op_ymin, col_ymin)
        if ov_x > 0.005 and ov_y > 0.005:
            cname = cm.get((ci, cj), f"C({ci+1},{cj+1})")
            errors.append(f"تعارض وتداخل هندسي: فتحة {op_name} تتداخل مع إحداثيات العمود الخرساني {cname} بمقدار {max(ov_x, ov_y):.2f}م!")

        # فحص إضافي: تداخل مسار دوران ضلفة الباب مع العمود الخرساني
        if op_type == "door" and leaf_dir:
            if is_h:
                swing_ymin = y_wall if leaf_dir == "أعلى" else (y_wall - w_val)
                swing_ymax = (y_wall + w_val) if leaf_dir == "أعلى" else y_wall
                s_ov_x = min(op_xmax, col_xmax) - max(op_xmin, col_xmin)
                s_ov_y = min(swing_ymax, col_ymax) - max(swing_ymin, col_ymin)
                if s_ov_x > 0.005 and s_ov_y > 0.005:
                    cname = cm.get((ci, cj), f"C({ci+1},{cj+1})")
                    errors.append(f"تداخل ضلفة {op_name} مع إحداثيات العمود {cname} بمقدار {s_ov_x:.2f}م!")
            else:
                swing_xmin = x_wall if leaf_dir == "يمين" else (x_wall - w_val)
                swing_xmax = (x_wall + w_val) if leaf_dir == "يمين" else x_wall
                s_ov_x = min(swing_xmax, col_xmax) - max(swing_xmin, col_xmin)
                s_ov_y = min(op_ymax, col_ymax) - max(op_ymin, col_ymin)
                if s_ov_x > 0.005 and s_ov_y > 0.005:
                    cname = cm.get((ci, cj), f"C({ci+1},{cj+1})")
                    errors.append(f"تداخل ضلفة {op_name} مع إحداثيات العمود {cname} بمقدار {s_ov_y:.2f}م!")

    # 3. فحص التداخل الهندسي (الكامل والجزئي) مع الفتحات الأخرى على نفس الحائط
    op_title = op_name.strip() if (op_name and op_name.strip()) else ("شباك" if op_type == "win" else "باب")
    start_pos = pos
    end_pos = pos + w_val
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()
    cur_id_str = str(current_op_id) if current_op_id is not None else None

    # أ) فحص التداخل بين الشبابيك (إذا كان العنصر المفحوص شباك)
    if op_type == "win":
        active_wins = [w for w in _get_wall_windows(wk) if not w.get("removed", False) and (cur_id_str is None or str(w.get("id")) != cur_id_str)]
        for ow in active_wins:
            ow_id = ow.get("id")
            ow_name = wm_win.get(ow_id) or ow.get("name") or f"W{ow_id}"
            ow_w = float(ow.get("w_m", 1.0))
            ow_pos = float(ow.get("pos_m", 0.0))
            o_start = ow_pos
            o_end = ow_pos + ow_w
            overlap = min(end_pos, o_end) - max(start_pos, o_start)
            if overlap > 0.005:
                if abs(pos - ow_pos) < 0.01 and abs(w_val - ow_w) < 0.01:
                    errors.append(f"غير مسموح تداخل شبابيك! تداخل وتطابق كامل في نفس الموضع الهندسي بين {op_title} و {ow_name} (بمقدار {overlap:.2f}م) على الحائط!")
                elif overlap >= min(w_val, ow_w) - 0.01:
                    errors.append(f"غير مسموح تداخل شبابيك! تداخل كامل في الموضع الهندسي بين {op_title} و {ow_name} (بمقدار {overlap:.2f}م) على الحائط!")
                else:
                    errors.append(f"غير مسموح تداخل شبابيك! تم رصد تداخل جزئي بين {op_title} و {ow_name} بمقدار {overlap:.2f}م على الحائط!")

        # فحص التداخل مع أي باب قائم على نفس الحائط
        active_doors = [d for d in _get_wall_doors(wk) if not d.get("removed", False) and (cur_id_str is None or str(d.get("id")) != cur_id_str)]
        for od in active_doors:
            od_id = od.get("id")
            od_name = wm_door.get(od_id) or od.get("name") or f"D{od_id}"
            od_w = float(od.get("w_m", 0.9))
            od_pos = float(od.get("pos_m", 0.0))
            o_start = od_pos
            o_end = od_pos + od_w
            overlap = min(end_pos, o_end) - max(start_pos, o_start)
            if overlap > 0.005:
                errors.append(f"غير مسموح تداخل الفتحات! تم رصد تداخل هندسي بين {op_title} والباب {od_name} بمقدار {overlap:.2f}م على الحائط!")

    # ب) فحص التداخل بين الأبواب (إذا كان العنصر المفحوص باب)
    elif op_type == "door":
        active_doors = [d for d in _get_wall_doors(wk) if not d.get("removed", False) and (cur_id_str is None or str(d.get("id")) != cur_id_str)]
        for od in active_doors:
            od_id = od.get("id")
            od_name = wm_door.get(od_id) or od.get("name") or f"D{od_id}"
            od_w = float(od.get("w_m", 0.9))
            od_pos = float(od.get("pos_m", 0.0))
            o_start = od_pos
            o_end = od_pos + od_w
            overlap = min(end_pos, o_end) - max(start_pos, o_start)
            if overlap > 0.005:
                if abs(pos - od_pos) < 0.01 and abs(w_val - od_w) < 0.01:
                    errors.append(f"غير مسموح تداخل ابواب! تداخل وتطابق كامل في نفس الموضع الهندسي بين {op_title} و {od_name} (بمقدار {overlap:.2f}م) على الحائط!")
                elif overlap >= min(w_val, od_w) - 0.01:
                    errors.append(f"غير مسموح تداخل ابواب! تداخل كامل في الموضع الهندسي بين {op_title} و {od_name} (بمقدار {overlap:.2f}م) على الحائط!")
                else:
                    errors.append(f"غير مسموح تداخل ابواب! تم رصد تداخل جزئي بين {op_title} و {od_name} بمقدار {overlap:.2f}م على الحائط!")

        # فحص التداخل مع أي شباك قائم على نفس الحائط
        active_wins = [w for w in _get_wall_windows(wk) if not w.get("removed", False) and (cur_id_str is None or str(w.get("id")) != cur_id_str)]
        for ow in active_wins:
            ow_id = ow.get("id")
            ow_name = wm_win.get(ow_id) or ow.get("name") or f"W{ow_id}"
            ow_w = float(ow.get("w_m", 1.0))
            ow_pos = float(ow.get("pos_m", 0.0))
            o_start = ow_pos
            o_end = ow_pos + ow_w
            overlap = min(end_pos, o_end) - max(start_pos, o_start)
            if overlap > 0.005:
                errors.append(f"غير مسموح تداخل الفتحات! تم رصد تداخل هندسي بين {op_title} والشباك {ow_name} بمقدار {overlap:.2f}م على الحائط!")

    return errors

def _check_add_window(wk):
    """التحقق الهندسي قبل إضافة شباك جديد على الحائط المختار."""
    col1_l, col2_l, c1_nm, c2_nm, wlen = _get_column_bounds_along_wall(wk)
    clear_wall = col2_l - col1_l if col2_l > col1_l else 0.0
    min_win_w = 0.40
    if clear_wall < min_win_w:
        c_names = f"({c1_nm or 'بداية الحائط'} و {c2_nm or 'نهاية الحائط'})"
        return False, f"لا توجد مسافة كافية لإضافة شباك: المسافة الصافية المتاحة بين وجهي العمودين {c_names} هي {clear_wall:.2f}م فقط (أقل من {min_win_w}م)، وسيحدث تعارض مع إحداثيات الأعمدة!", None, None

    active_wins = [w for w in _get_wall_windows(wk) if not w.get("removed", False)]
    active_doors = [d for d in _get_wall_doors(wk) if not d.get("removed", False)]
    occupied = []
    for w in active_wins:
        ow = float(w.get("w_m", 1.0)); opos = float(w.get("pos_m", 0.0))
        occupied.append((max(0.0, opos - 0.05), min(wlen, opos + ow + 0.05)))
    for d in active_doors:
        dw = float(d.get("w_m", 0.9)); dpos = float(d.get("pos_m", 0.0))
        occupied.append((max(0.0, dpos - 0.05), min(wlen, dpos + dw + 0.05)))
    occupied.sort(key=lambda x: x[0])
    free_intervals = []
    cur_start = col1_l
    for occ_start, occ_end in occupied:
        if occ_end <= cur_start: continue
        if occ_start > cur_start:
            end_lim = min(occ_start, col2_l)
            if end_lim - cur_start >= min_win_w:
                free_intervals.append((cur_start, end_lim))
        cur_start = max(cur_start, occ_end)
        if cur_start >= col2_l: break
    if cur_start < col2_l and (col2_l - cur_start) >= min_win_w:
        free_intervals.append((cur_start, col2_l))
        
    if not free_intervals:
        return False, "لا يمكن إضافة شباك جديد: لا توجد مسافة شاغرة كافية بين الفتحات القائمة وإحداثيات الأعمدة على هذا الحائط!", None, None
        
    free_intervals.sort(key=lambda iv: iv[1] - iv[0], reverse=True)
    best_iv = free_intervals[0]
    best_len = best_iv[1] - best_iv[0]
    cand_w = round(min(1.0, max(min_win_w, best_len - 0.10)), 2)
    cand_pos = round(max(0.0, (wlen - cand_w) / 2.0), 2)
    
    return True, "", cand_w, cand_pos

def _check_add_door(wk):
    """التحقق الهندسي قبل إضافة باب جديد على الحائط المختار."""
    col1_l, col2_l, c1_nm, c2_nm, wlen = _get_column_bounds_along_wall(wk)
    clear_wall = col2_l - col1_l if col2_l > col1_l else 0.0
    min_door_w = 0.50
    if clear_wall < min_door_w:
        c_names = f"({c1_nm or 'بداية الحائط'} و {c2_nm or 'نهاية الحائط'})"
        return False, f"لا توجد مسافة كافية لإضافة باب: المسافة الصافية بين وجهي العمودين {c_names} هي {clear_wall:.2f}م فقط (أقل من {min_door_w}م)، وسيحدث تعارض مع إحداثيات الأعمدة!", None, None

    active_wins = [w for w in _get_wall_windows(wk) if not w.get("removed", False)]
    active_doors = [d for d in _get_wall_doors(wk) if not d.get("removed", False)]
    occupied = []
    for w in active_wins:
        ow = float(w.get("w_m", 1.0)); opos = float(w.get("pos_m", 0.0))
        occupied.append((max(0.0, opos - 0.05), min(wlen, opos + ow + 0.05)))
    for d in active_doors:
        dw = float(d.get("w_m", 0.9)); dpos = float(d.get("pos_m", 0.0))
        occupied.append((max(0.0, dpos - 0.05), min(wlen, dpos + dw + 0.05)))
    occupied.sort(key=lambda x: x[0])
    free_intervals = []
    cur_start = col1_l
    for occ_start, occ_end in occupied:
        if occ_end <= cur_start: continue
        if occ_start > cur_start:
            end_lim = min(occ_start, col2_l)
            if end_lim - cur_start >= min_door_w:
                free_intervals.append((cur_start, end_lim))
        cur_start = max(cur_start, occ_end)
        if cur_start >= col2_l: break
    if cur_start < col2_l and (col2_l - cur_start) >= min_door_w:
        free_intervals.append((cur_start, col2_l))
        
    if not free_intervals:
        return False, "لا يمكن إضافة باب جديد: لا توجد مسافة شاغرة كافية بين الفتحات القائمة وإحداثيات الأعمدة على هذا الحائط!", None, None
        
    free_intervals.sort(key=lambda iv: iv[1] - iv[0], reverse=True)
    best_iv = free_intervals[0]
    best_len = best_iv[1] - best_iv[0]
    cand_w = round(min(0.9, max(min_door_w, best_len - 0.10)), 2)
    cand_pos = round(max(0.0, (wlen - cand_w) / 2.0), 2)
    return True, "", cand_w, cand_pos

def _check_add_column(x_val, y_val, col_dir):
    """
    التحقق الهندسي الصارم عند إضافة عمود:
    1- التأكد من عدم الخروج من مساحة المسقط الأفقي.
    2- التأكد من عدم التعارض والتداخل مع إحداثيات الأعمدة القائمة.
    3- التأكد من عدم التداخل مع فتحات الشبابيك والأبواب القائمة.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if not xs or not ys:
        return False, "يجب تحديد شبكة المحاور أولاً."
    x_min_p, x_max_p = min(xs), max(xs)
    y_min_p, y_max_p = min(ys), max(ys)
    col_l = float(st.session_state.get("m15_col_length_cm", 60.0)) / 100.0
    col_w = float(st.session_state.get("m15_col_width_cm", 30.0)) / 100.0
    cw, ch = (col_w, col_l) if col_dir == "NS" else (col_l, col_w)
    
    if x_val < x_min_p - 0.01 or x_val > x_max_p + 0.01 or y_val < y_min_p - 0.01 or y_val > y_max_p + 0.01:
        return False, f"إحداثيات العمود المطلوب عند ({x_val:.2f}, {y_val:.2f})م تقع خارج مساحة المسقط الأفقي! (حدود المسقط: X من {x_min_p:.2f} إلى {x_max_p:.2f}م | Y من {y_min_p:.2f} إلى {y_max_p:.2f}م)."

    cm = _get_col_name_map()
    for (ci, cj) in _get_active_columns():
        cx, cy = _col_center(ci, cj)
        ecw, ech = _get_col_wh(ci, cj)
        dx = abs(x_val - cx); dy = abs(y_val - cy)
        min_dx = (cw + ecw) / 2.0 - 0.005; min_dy = (ch + ech) / 2.0 - 0.005
        if dx < min_dx and dy < min_dy:
            cname = cm.get((ci, cj), f"C({ci+1},{cj+1})")
            overlap_dist = max(min_dx - dx, min_dy - dy)
            return False, f"تعارض في الإحداثيات: العمود المطلوب عند ({x_val:.2f}, {y_val:.2f})م يتداخل ويتعارض مع العمود القائم {cname} عند ({cx:.2f}, {cy:.2f})م بمقدار {overlap_dist:.2f}م!"

    for wk in _get_all_walls():
        w_i1, w_j1, w_i2, w_j2 = wk
        w_is_h = (w_j1 == w_j2)
        if w_is_h:
            y_wall = ys[w_j1]
            if abs(y_val - y_wall) < (ch / 2.0 + 0.12):
                x_start = min(xs[w_i1], xs[w_i2])
                for win in _get_wall_windows(wk):
                    if win.get("removed", False): continue
                    w_pos = float(win.get("pos_m", 0.0)); w_w = float(win.get("w_m", 1.0))
                    w_x1 = x_start + w_pos; w_x2 = w_x1 + w_w
                    c_x1 = x_val - cw / 2.0; c_x2 = x_val + cw / 2.0
                    if min(w_x2, c_x2) - max(w_x1, c_x1) > 0.005:
                        return False, f"تعارض هندسي: موقع العمود يتعارض ويتداخل مع فتحة {win.get('name', 'شباك')} القائمة على الحائط الأفقي!"
                for door in _get_wall_doors(wk):
                    if door.get("removed", False): continue
                    d_pos = float(door.get("pos_m", 0.0)); d_w = float(door.get("w_m", 0.9))
                    d_x1 = x_start + d_pos; d_x2 = d_x1 + d_w
                    c_x1 = x_val - cw / 2.0; c_x2 = x_val + cw / 2.0
                    if min(d_x2, c_x2) - max(d_x1, c_x1) > 0.005:
                        return False, f"تعارض هندسي: موقع العمود يتعارض ويتداخل مع فتحة {door.get('name', 'باب')} القائمة على الحائط الأفقي!"
        else:
            x_wall = xs[w_i1]
            if abs(x_val - x_wall) < (cw / 2.0 + 0.12):
                y_start = min(ys[w_j1], ys[w_j2])
                for win in _get_wall_windows(wk):
                    if win.get("removed", False): continue
                    w_pos = float(win.get("pos_m", 0.0)); w_w = float(win.get("w_m", 1.0))
                    w_y1 = y_start + w_pos; w_y2 = w_y1 + w_w
                    c_y1 = y_val - ch / 2.0; c_y2 = y_val + ch / 2.0
                    if min(w_y2, c_y2) - max(w_y1, c_y1) > 0.005:
                        return False, f"تعارض هندسي: موقع العمود يتعارض ويتداخل مع فتحة {win.get('name', 'شباك')} القائمة على الحائط الرأسي!"
                for door in _get_wall_doors(wk):
                    if door.get("removed", False): continue
                    d_pos = float(door.get("pos_m", 0.0)); d_w = float(door.get("w_m", 0.9))
                    d_y1 = y_start + d_pos; d_y2 = d_y1 + d_w
                    c_y1 = y_val - ch / 2.0; c_y2 = y_val + ch / 2.0
                    if min(d_y2, c_y2) - max(d_y1, c_y1) > 0.005:
                        return False, f"تعارض هندسي: موقع العمود يتعارض ويتداخل مع فتحة {door.get('name', 'باب')} القائمة على الحائط الرأسي!"
    return True, ""
    return True, ""

def _get_all_opening_conflicts():
    """فحص شامل لكافة الفتحات في المسقط الأفقي ورصد أي تداخلات أو أخطاء إحداثيات."""
    conflicts = []
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()
    removed_walls = st.session_state.get("m15_wall_removed", set())

    for wk in _get_all_walls():
        if wk in removed_walls:
            continue
        wlbl = _wall_display_label(wk, cm, wm)

        # فحص الشبابيك
        for winfo in _get_wall_windows(wk):
            if winfo.get("removed", False):
                continue
            wid = winfo.get("id")
            wname = wm_win.get(wid) or winfo.get("name") or f"W_{wid}"
            errs = _validate_opening_coords(wk, f"الشباك {wname}", "win", winfo.get("w_m", 1.0), winfo.get("h_m", 1.2), winfo.get("pos_m", 0.0), current_op_id=wid)
            for e in errs:
                msg = f"[{wlbl}] {e}"
                if msg not in conflicts:
                    conflicts.append(msg)

        # فحص الأبواب
        for dinfo in _get_wall_doors(wk):
            if dinfo.get("removed", False):
                continue
            did = dinfo.get("id")
            dname = wm_door.get(did) or dinfo.get("name") or f"D_{did}"
            errs = _validate_opening_coords(wk, f"الباب {dname}", "door", dinfo.get("w_m", 0.9), dinfo.get("h_m", 2.1), dinfo.get("pos_m", 0.0), leaf_dir=dinfo.get("leaf_dir"), current_op_id=did)
            for e in errs:
                msg = f"[{wlbl}] {e}"
                if msg not in conflicts:
                    conflicts.append(msg)

    return conflicts

def _render_big_warning(errors):
    """عرض رسالة تحذيرية بخط كبير وبارز وإطلاق صافرة الإنذار الترددية."""
    if not errors: return
    play_warning_sound()
    items_html = "".join([f"<li style='margin-bottom:5px;'>{e}</li>" for e in errors])
    st.markdown(
        f"""<div style='background:linear-gradient(135deg,#FFEBEE,#FFCDD2);border:2.5px solid #D32F2F;
            border-radius:10px;padding:14px 18px;margin:12px 0 16px 0;box-shadow:0 4px 12px rgba(211,47,47,0.25);'>
            <div style='color:#B71C1C;font-size:1.20rem;font-weight:900;margin-bottom:8px;display:flex;align-items:center;gap:10px;'>
                <span style='font-size:1.4rem;'>🚨</span>
                <span>تحذير هندسي: تم رصد تجاوز في الإحداثيات أو تداخل في الفتحات والأعمدة!</span>
            </div>
            <ul style='color:#B71C1C;font-size:1.05rem;font-weight:700;margin:0;padding-right:24px;line-height:1.75;'>
                {items_html}
            </ul>
        </div>""",
        unsafe_allow_html=True
    )

def _check_opening_spatial_conflict(wk, op_name, op_type, w_m, h_m, pos_m, leaf_dir=None):
    """
    فحص التحقق المكاني الصارم للفتحة المعمارية (Spatial Conflict & Boundary Detection):
    1. Boundary Containment: احتواء الحائط بالكامل لكامل أبعاد الفتحة دون تجاوز حدود أو أطراف الحائط أو الاصطدام بالأعمدة.
    2. Intersection / Clashing: التأكد من عدم وجود أي تداخل في الإحداثيات (Overlap) مع أي فتحات موجودة مسبقاً (شبابيك أو أبواب) على الحائط نفسه.
    """
    return _validate_opening_coords(
        wk=wk,
        op_name=op_name,
        op_type=op_type,
        w_m=w_m,
        h_m=h_m,
        pos_m=pos_m,
        leaf_dir=leaf_dir,
        current_op_id=None
    )

def _find_first_available_opening_pos(wk, op_type, w_m, h_m, leaf_dir=None):
    """
    البحث الذكي عن أول موضع متاح هندسياً وخالٍ من أي تعارضات أو اصطدام بالأعمدة
    أو الفتحات القائمة على الحائط لإسقاط الفتحة الجديدة.
    """
    wlen = _wall_length_m(wk)
    col1_l, col2_l, _, _, _ = _get_column_bounds_along_wall(wk)
    min_pos = round(col1_l + 0.05, 2)
    max_pos = round(col2_l - w_m - 0.05, 2)

    # 1. تجربة المنتصف أولاً إذا كان متاحاً وخالياً من التعارض
    mid_pos = round(max(0.0, (wlen - w_m) / 2.0), 2)
    if min_pos <= mid_pos <= max_pos:
        if not _check_opening_spatial_conflict(wk, "اختبار", op_type, w_m, h_m, mid_pos, leaf_dir=leaf_dir):
            return mid_pos

    if max_pos < min_pos:
        return mid_pos

    # 2. المسح التدريجي عبر طول الحائط بخطوة 5 سم
    cur = min_pos
    while cur <= max_pos + 1e-4:
        errs = _check_opening_spatial_conflict(
            wk=wk,
            op_name="اختبار",
            op_type=op_type,
            w_m=w_m,
            h_m=h_m,
            pos_m=round(cur, 2),
            leaf_dir=leaf_dir
        )
        if not errs:
            return round(cur, 2)
        cur = round(cur + 0.05, 2)

    return mid_pos

def _render_opening_conflict_banner():
    """
    عرض رسالة تنبيه التعارض المكاني والهندسي بصورة مضغوطة وأنيقة فوق شاشة المدخلات:
    - تشغيل تنبيه صوتي فوري (Audio Warning / Beep Alert).
    - صندوق تحذيري مدمج بدون إهدار رأسي يعرض تفاصيل التعارض.
    - زر إغلاق التنبيه مع بقاء الكائن المؤقت في مكانه على الرسم بانتظار تعديل البعد.
    """
    play_warning_sound()
    errors = st.session_state.get("m15_conflict_errors", [])
    preview = st.session_state.get("m15_preview_opening") or {}
    op_kind_ar = "شباك" if preview.get("kind") == "win" else "باب"
    op_name = preview.get("name") or ("W_new" if preview.get("kind") == "win" else "D_new")

    err_items = "".join([f"<li style='margin-bottom:2px;'>{e}</li>" for e in errors])

    st.markdown(
        f"""<div style='background:linear-gradient(135deg,#FFF5F5,#FFEBEE);border:1.8px solid #E53935;
        border-radius:8px;padding:8px 12px;margin:4px 0 8px 0;box-shadow:0 2px 6px rgba(229,57,53,0.18);' dir='rtl'>
        <div style='color:#B71C1C;font-size:0.95rem;font-weight:900;margin-bottom:4px;display:flex;align-items:center;justify-content:space-between;gap:8px;'>
            <div style='display:flex;align-items:center;gap:6px;'>
                <span style='font-size:1.15rem;'>🚨</span>
                <span>تنبيه تعارض مكاني وهندسي / Spatial Conflict Alert ({op_kind_ar}: {op_name})</span>
            </div>
            <span style='background:#FFCDD2;color:#B71C1C;font-size:0.75rem;padding:2px 8px;border-radius:10px;font-weight:bold;'>تعارض مكاني</span>
        </div>
        <p style='color:#7F0000;font-size:0.83rem;margin:0 0 4px 0;font-weight:700;'>
            ⚠️ تم رصد تعارض في الإحداثيات أو تجاوز لحدود الحائط (يظهر الكائن المؤقت بوضوح باللون الأحمر المتقطع ⚠️ على الرسم):
        </p>
        <ul style='color:#B71C1C;font-size:0.83rem;font-weight:700;margin:0 0 6px 0;padding-right:20px;line-height:1.4;'>
            {err_items}
        </ul>
        <div style='color:#616161;font-size:0.78rem;font-weight:600;margin-top:2px;'>
            💡 يمكنك إلغاء وحذف {op_kind_ar} المؤقت ومسحه تماماً من على الرسم، أو الإبقاء عليه لتعديل الموضع أدناه.
        </div>
        </div>""",
        unsafe_allow_html=True
    )

    c_conf1, c_conf2 = st.columns([1.5, 1.2])
    with c_conf1:
        if st.button(f"🗑️ إلغاء وحذف {op_kind_ar} المتعارض من الرسم", key="m15_conflict_cancel_btn", type="primary", use_container_width=True, help=f"إلغاء وحذف {op_kind_ar} المؤقت المتعارض فوراً ومسحه تماماً من على الرسم"):
            st.session_state["m15_show_conflict_modal"] = False
            st.session_state["m15_conflict_errors"] = []
            st.session_state["m15_preview_opening"] = None
            p_wk = preview.get("wk")
            p_name = preview.get("name")
            if preview.get("kind") == "door":
                st.session_state["m15_door_preview_disabled"] = True
                if p_wk and "m15_doors" in st.session_state and p_wk in st.session_state["m15_doors"]:
                    st.session_state["m15_doors"][p_wk] = [
                        d for d in st.session_state["m15_doors"][p_wk]
                        if not (d.get("has_conflict") or d.get("is_preview") or (p_name and d.get("name") == p_name))
                    ]
            else:
                st.session_state["m15_win_preview_disabled"] = True
                if p_wk and "m15_windows" in st.session_state and p_wk in st.session_state["m15_windows"]:
                    st.session_state["m15_windows"][p_wk] = [
                        w for w in st.session_state["m15_windows"][p_wk]
                        if not (w.get("has_conflict") or w.get("is_preview") or (p_name and w.get("name") == p_name))
                    ]
            st.session_state.pop("m15_sync_preview_on_next_run", None)
            st.session_state["m15_openings_keep_expanded"] = True
            save_settings()
            st.toast(f"✅ تم إلغاء وحذف {op_kind_ar} المؤقت المتعارض من على الرسم.", icon="🗑️")
            st.rerun()

    with c_conf2:
        if st.button("✏️ الإبقاء لتعديل الموضع", key="m15_conflict_dismiss_btn", type="secondary", use_container_width=True, help="إغلاق التنبيه مع بقاء العنصر المؤقت على الرسم لتعديل البعد"):
            st.session_state["m15_show_conflict_modal"] = False
            st.session_state["m15_conflict_errors"] = []
            st.session_state["m15_openings_keep_expanded"] = True
            if preview and preview.get("wk"):
                preview["has_conflict"] = True
                preview["is_preview"] = True
                st.session_state["m15_preview_opening"] = preview
                st.session_state["m15_sync_preview_on_next_run"] = True
            st.rerun()

def _get_all_deleted_openings():
    """تجميع كافة الشبابيك والأبواب المحذوفة في المشروع لعرضها في سلة المحذوفات الموحدة."""
    _ensure_opening_names()
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    deleted = []
    for wk, wl in list(st.session_state.get("m15_windows", {}).items()):
        wlbl = _wall_display_label(wk, cm, wm)
        for w in wl:
            if w.get("removed", False):
                nm = w.get("name") or "W?"
                deleted.append({
                    "id": w["id"],
                    "name": nm,
                    "kind": "win",
                    "kind_ar": "🪟 شباك",
                    "wk": wk,
                    "wall_label": wlbl,
                    "w_m": float(w.get("w_m", 1.0)),
                    "h_m": float(w.get("h_m", 1.2)),
                    "pos_m": float(w.get("pos_m", 0.0)),
                    "raw": w,
                    "label": f"🪟 {nm} [عرض {float(w.get('w_m',1.0)):.2f}م × ارتفاع {float(w.get('h_m',1.2)):.2f}م] — حائط {wlbl}"
                })
    for wk, dl in list(st.session_state.get("m15_doors", {}).items()):
        wlbl = _wall_display_label(wk, cm, wm)
        for d in dl:
            if d.get("removed", False):
                nm = d.get("name") or "D?"
                deleted.append({
                    "id": d["id"],
                    "name": nm,
                    "kind": "door",
                    "kind_ar": "🚪 باب",
                    "wk": wk,
                    "wall_label": wlbl,
                    "w_m": float(d.get("w_m", 0.9)),
                    "h_m": float(d.get("h_m", 2.1)),
                    "pos_m": float(d.get("pos_m", 0.0)),
                    "leaf_dir": d.get("leaf_dir", "أعلى"),
                    "hinge_dir": d.get("hinge_dir", "يسار"),
                    "raw": d,
                    "label": f"🚪 {nm} [عرض {float(d.get('w_m',0.9)):.2f}م × ارتفاع {float(d.get('h_m',2.1)):.2f}م] — حائط {wlbl}"
                })
    def _sort_key(item):
        k = 0 if item["kind"] == "win" else 1
        num = 0
        nm = item["name"]
        if len(nm) > 1 and nm[1:].isdigit():
            num = int(nm[1:])
        return (k, num)
    deleted.sort(key=_sort_key)
    return deleted

_get_deleted_openings = _get_all_deleted_openings

def _restore_opening(item, target_wk):
    """استعادة فتحة محذوفة إلى الحائط الأصلي أو حائط بديل تم اختياره من القائمة المنسدلة مع إعادة التسلسل فوراً."""
    s_wk = item["wk"]
    s_id = item["id"]
    is_win = (item["kind"] == "win")
    store = st.session_state["m15_windows"] if is_win else st.session_state["m15_doors"]

    raw_obj = None
    orig_list = store.get(s_wk, [])
    for op in orig_list:
        if op.get("id") == s_id:
            raw_obj = op
            break

    if not raw_obj:
        raw_obj = dict(item["raw"])

    raw_obj["removed"] = False

    if target_wk == s_wk:
        if raw_obj not in orig_list:
            orig_list.append(raw_obj)
        store[s_wk] = orig_list
    else:
        if raw_obj in orig_list:
            orig_list.remove(raw_obj)
        store[s_wk] = orig_list
        target_wlen = _wall_length_m(target_wk)
        op_w = float(raw_obj.get("w_m", 1.0))
        if float(raw_obj.get("pos_m", 0.0)) + op_w > target_wlen:
            raw_obj["pos_m"] = round(max(0.0, (target_wlen - op_w) / 2.0), 2)
        target_list = store.setdefault(target_wk, [])
        target_list.append(raw_obj)
        store[target_wk] = target_list

    # ضمان إلغاء علامة الحذف لجميع النسخ التي تحمل نفس المعرف
    for wk in list(store.keys()):
        for op in store[wk]:
            if op.get("id") == s_id:
                op["removed"] = False

    _resequence_openings()
    save_settings()

def _purge_opening(item):
    """حذف نهائي للفتحة من الذاكرة والبيانات."""
    s_id = item["id"]
    is_win = (item["kind"] == "win")
    store = st.session_state["m15_windows"] if is_win else st.session_state["m15_doors"]
    for wk in list(store.keys()):
        store[wk] = [op for op in store[wk] if op.get("id") != s_id]

def _get_wall_thickness(w_key):
    wall_thick = st.session_state.get("m15_wall_thickness", {})
    if w_key in wall_thick:
        return wall_thick[w_key]
    t = _safe_coord_tuple(w_key, 4)
    if not t:
        return _WALL_THIN
    i1, j1, i2, j2 = t
    if j1 == j2:
        for i in range(min(i1, i2), max(i1, i2)):
            if wall_thick.get((i, j1, i + 1, j1)) == _WALL_THICK:
                return _WALL_THICK
    else:
        for j in range(min(j1, j2), max(j1, j2)):
            if wall_thick.get((i1, j, i1, j + 1)) == _WALL_THICK:
                return _WALL_THICK
    return _WALL_THIN

def _is_parapet_wall(w_key):
    """التحقق مما إذا كان الحائط (أو أي من أجزائه الفرعية) مصنفاً كدروة (Parapet)."""
    parapet_walls = st.session_state.get("m15_parapet_walls", set())
    if w_key in parapet_walls:
        return True
    t = _safe_coord_tuple(w_key, 4)
    if not t:
        return False
    i1, j1, i2, j2 = t
    if j1 == j2:
        for i in range(min(i1, i2), max(i1, i2)):
            if (i, j1, i + 1, j1) in parapet_walls:
                return True
    else:
        for j in range(min(j1, j2), max(j1, j2)):
            if (i1, j, i1, j + 1) in parapet_walls:
                return True
    return False

def _get_wall_height(w_key, default_h=None):
    """
    تحديد ارتفاع الحائط وفق قواعد المشروع:
    1. الحوائط المحددة كدروة (Parapet) تأخذ دائماً قيمة مدخل 'ارتفاع دروة' (Parapet Height).
    2. فحص مصفوفة ارتفاعات الحوائط المخصصة (m15_wall_heights) للحائط أو أجزائه.
    3. إذا لم يوجد ارتفاع مخصص، استخدام الارتفاع الافتراضي (Wall Height).
    """
    if _is_parapet_wall(w_key):
        return float(st.session_state.get("m15_parapet_wall_height", st.session_state.get("m15_parapet_h_input", 1.0)))
    wh_map = st.session_state.get("m15_wall_heights", {})
    if w_key in wh_map:
        return float(wh_map[w_key])
    t = _safe_coord_tuple(w_key, 4)
    if t:
        i1, j1, i2, j2 = t
        if j1 == j2:
            for i in range(min(i1, i2), max(i1, i2)):
                if (i, j1, i + 1, j1) in wh_map:
                    return float(wh_map[(i, j1, i + 1, j1)])
        else:
            for j in range(min(j1, j2), max(j1, j2)):
                if (i1, j, i1, j + 1) in wh_map:
                    return float(wh_map[(i1, j, i1, j + 1)])
    if default_h is not None:
        return float(default_h)
    return float(st.session_state.get("m15_default_wall_height", st.session_state.get("m15_default_h_input", 3.0)))

def _detect_perimeter_walls():
    """
    كشف حوائط المحيط الخارجي (Perimeter Boundary Walls) تلقائياً:
    وهي الحوائط الواقعة على الحدود الخارجية لشبكة المحاور (أدنى/أعلى Y وأدنى/أعلى X).
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        return []
    nx = len(xs)
    ny = len(ys)
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    perim = []
    for wk in all_walls:
        if wk in removed_walls:
            continue
        t = _safe_coord_tuple(wk, 4)
        if not t:
            continue
        i1, j1, i2, j2 = t
        if j1 == j2 and (j1 == 0 or j1 == ny - 1):
            perim.append(t)
        elif i1 == i2 and (i1 == 0 or i1 == nx - 1):
            perim.append(t)
    return perim

def _get_wall_windows(w_key):
    win_data = st.session_state.get("m15_windows", {})
    if w_key in win_data and win_data[w_key]:
        return [w for w in win_data[w_key] if not w.get("removed", False)]
    t = _safe_coord_tuple(w_key, 4)
    if not t:
        return []
    i1, j1, i2, j2 = t
    xs = st.session_state.get("m15_x_axes", []); ys = st.session_state.get("m15_y_axes", [])
    collected = []
    if j1 == j2:
        for i in range(min(i1, i2), max(i1, i2)):
            if i >= len(xs) or i1 >= len(xs):
                break
            offset = abs(xs[i] - xs[i1])
            for win in win_data.get((i, j1, i + 1, j1), []):
                if not win.get("removed", False):
                    wc = dict(win); wc["pos_m"] = win.get("pos_m", 0.0) + offset
                    collected.append(wc)
    else:
        for j in range(min(j1, j2), max(j1, j2)):
            if j >= len(ys) or j1 >= len(ys):
                break
            offset = abs(ys[j] - ys[j1])
            for win in win_data.get((i1, j, i1, j + 1), []):
                if not win.get("removed", False):
                    wc = dict(win); wc["pos_m"] = win.get("pos_m", 0.0) + offset
                    collected.append(wc)
    return collected

def _get_wall_doors(w_key):
    door_data = st.session_state.get("m15_doors", {})
    if w_key in door_data and door_data[w_key]:
        return [d for d in door_data[w_key] if not d.get("removed", False)]

    t = _safe_coord_tuple(w_key, 4)
    if not t:
        return []
    i1, j1, i2, j2 = t
    xs = st.session_state.get("m15_x_axes", []); ys = st.session_state.get("m15_y_axes", [])
    collected = []
    if j1 == j2:
        for i in range(min(i1, i2), max(i1, i2)):
            if i >= len(xs) or i1 >= len(xs):
                break
            offset = abs(xs[i] - xs[i1])
            for d in door_data.get((i, j1, i + 1, j1), []):
                if not d.get("removed", False):
                    dc = dict(d); dc["pos_m"] = d.get("pos_m", 0.0) + offset
                    collected.append(dc)
    else:
        for j in range(min(j1, j2), max(j1, j2)):
            if j >= len(ys) or j1 >= len(ys):
                break
            offset = abs(ys[j] - ys[j1])
            for d in door_data.get((i1, j, i1, j + 1), []):
                if not d.get("removed", False):
                    dc = dict(d); dc["pos_m"] = d.get("pos_m", 0.0) + offset
                    collected.append(dc)
    return collected

def _draw_plan(with_dim=True):
    xs=st.session_state["m15_x_axes"]; ys=st.session_state["m15_y_axes"]
    removed_cols=st.session_state["m15_col_removed"]
    removed_walls=st.session_state["m15_wall_removed"]
    _resequence_openings()
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()
    del_win_ids = {item["id"] for item in _get_all_deleted_openings() if item["kind"] == "win"}
    del_door_ids = {item["id"] for item in _get_all_deleted_openings() if item["kind"] == "door"}
    if not xs or not ys:
        fig,ax=plt.subplots(figsize=(6,4))
        ax.text(0.5,0.5,"No axes yet",ha="center",va="center",fontsize=round(14*1.4,1),transform=ax.transAxes)

        ax.axis("off"); buf=io.BytesIO(); fig.savefig(buf,format="png",dpi=120); plt.close(fig); buf.seek(0); return buf
    x_min,x_max=min(xs),max(xs); y_min,y_max=min(ys),max(ys)
    span_x=x_max-x_min or 1.0; span_y=y_max-y_min or 1.0
    fig_w=min(18,max(10,span_x*1.6+2.5)); fig_h=min(15,max(8,span_y*1.6+2.5))
    fig,ax=plt.subplots(figsize=(fig_w,fig_h)); ax.set_aspect("equal")
    # ── تباعد خطوط الأبعاد والمحيط الخارجي بنمط الأوتوكاد الهندسي المتناسق ──
    min_span = min(span_x, span_y) if (span_x and span_y) else 5.0
    d_bay = max(0.60, min(1.10, min_span * 0.09))
    d_tot = max(0.50, min(0.90, min_span * 0.075))
    d_bub = max(0.50, min(0.90, min_span * 0.075))
    cad_bubble_r = max(0.16, min(0.22, min_span * 0.026))
    dt_tick = max(0.08, min(0.14, min_span * 0.015))

    # إحداثيات خطوط الأبعاد والفقاعات الخارجية
    y_dim_bot_bay = y_min - d_bay
    y_dim_bot_tot = y_dim_bot_bay - d_tot
    y_bub_bot     = y_dim_bot_tot - d_bub

    y_dim_top_bay = y_max + d_bay
    y_dim_top_tot = y_dim_top_bay + d_tot
    y_bub_top     = y_dim_top_tot + d_bub

    x_dim_left_bay = x_min - d_bay
    x_dim_left_tot = x_dim_left_bay - d_tot
    x_bub_left     = x_dim_left_tot - d_bub

    x_dim_right_bay = x_max + d_bay
    x_dim_right_tot = x_dim_right_bay + d_tot
    x_bub_right     = x_dim_right_tot + d_bub

    margin_x = d_bay + d_tot + d_bub + cad_bubble_r + 0.35
    margin_y = d_bay + d_tot + d_bub + cad_bubble_r + 0.35

    ax.set_xlim(x_min - margin_x, x_max + margin_x)
    ax.set_ylim(y_min - margin_y, y_max + margin_y)
    ax.set_facecolor("#FBFBFB")
    fig.patch.set_facecolor("#F0F2F5")
    fs_scale = 1.4
    fs_axis = round(9.5 * fs_scale, 1)    # 13.3
    fs_thick = round(8.0 * fs_scale, 1)   # 11.2
    fs_wall = round(8.5 * fs_scale, 1)    # 11.9
    fs_col = round(10.0 * fs_scale, 1)    # 14.0
    fs_win = round(8.5 * fs_scale, 1)     # 11.9
    fs_door = round(8.0 * fs_scale, 1)    # 11.2
    fs_leg = round(8.5 * fs_scale, 1)     # 11.9
    fs_title = round(11.0 * fs_scale, 1)  # 15.4
    fs_lbl = round(9.0 * fs_scale, 1)     # 12.6
    fs_tick = round(8.0 * fs_scale, 1)    # 11.2
    fs_dim = round(8.5 * fs_scale, 1)     # 11.9
    fs_bubble = round((fs_axis * 0.72) * 1.3, 1)

    # رسم خطوط المحاور الهندسية الواصلة مباشرة بين دوائر المحاور بنمط الأوتوكاد
    for x in xs:
        ax.plot([x, x], [y_bub_bot, y_bub_top], color=_CLR_AXIS_Y, lw=0.9, ls="--", alpha=0.50, zorder=1)
    for y in ys:
        ax.plot([x_bub_left, x_bub_right], [y, y], color=_CLR_AXIS_X, lw=0.9, ls="--", alpha=0.50, zorder=1)

    for wk in _get_all_walls():
        i1, j1, i2, j2 = wk; removed = wk in removed_walls
        thick = _get_wall_thickness(wk)
        cross_min, cross_max, cross_c, thick_m = _get_wall_cross_bounds(wk)
        half_t = thick_m / 2.0
        is_p = _is_parapet_wall(wk)
        if is_p:
            color = _CLR_WALL_PARAPET
        elif thick == _WALL_THIN:
            color = _CLR_WALL_12
        else:
            color = _CLR_WALL_25
        is_h = (j1 == j2)
        wlen = _wall_length_m(wk)
        lname = wm.get(wk, "")
        if removed:
            # 4- رسم خط استرشادي مكان الحائط المحذوف فقط دون حسابات أو كتابة أبعاد
            ax.plot([xs[i1], xs[i2]], [ys[j1], ys[j2]], color="#94a3b8", ls=":", lw=1.2, alpha=0.75, zorder=2)
        else:
            if is_h: rx = min(xs[i1], xs[i2]); ry = cross_min; rw = abs(xs[i2] - xs[i1]); rh = thick_m
            else: rx = cross_min; ry = min(ys[j1], ys[j2]); rw = thick_m; rh = abs(ys[j2] - ys[j1])
            edge_clr = "#0369a1" if is_p else "#333333"
            edge_lw = 1.3 if is_p else 1.0
            ax.add_patch(patches.Rectangle((rx, ry), rw, rh, lw=edge_lw, edgecolor=edge_clr, facecolor=color, alpha=0.88, zorder=2))

            # ── رسم أوجه المحارة بخطوط مائلة وردية واسعة فقط (بدون أي إطار أو خطوط حدود) ──
            plaster_faces_map = st.session_state.get("m15_plaster_faces", {})
            chosen_faces = plaster_faces_map.get(wk, [])
            if chosen_faces:
                p_th = max(0.12, half_t * 1.10)   # مضاعفة طول خطوط التهشير
                import matplotlib as _mpl
                for f_dir in chosen_faces:
                    if is_h:
                        if f_dir == "أعلى":
                            p_x, p_y = rx, cross_max
                            p_w, p_h = rw, p_th
                        elif f_dir == "أسفل":
                            p_x, p_y = rx, cross_min - p_th
                            p_w, p_h = rw, p_th
                        else:
                            continue
                    else:
                        if f_dir == "يمين":
                            p_x, p_y = cross_max, ry
                            p_w, p_h = p_th, rh
                        elif f_dir == "يسار":
                            p_x, p_y = cross_min - p_th, ry
                            p_w, p_h = p_th, rh
                        else:
                            continue
                    # خطوط تهشير مائلة وردية نقية فقط (lw=0 تلغي أي خط إطار خارجي تماماً)
                    with _mpl.rc_context({"hatch.linewidth": 2.2}):
                        ax.add_patch(patches.Rectangle(
                            (p_x, p_y), p_w, p_h,
                            lw=0, edgecolor="#EC4899", facecolor="none",
                            hatch="/", alpha=1.0, zorder=3.5
                        ))
        wins = _get_wall_windows(wk)
        if not removed and wins:
            wlen = _wall_length_m(wk)
            win_groups = {}
            for winfo in wins:
                if winfo.get("removed", False) or winfo.get("id") in del_win_ids: continue
                w_w = float(winfo.get("w_m", 1.0)); w_pos = float(winfo.get("pos_m", (wlen - w_w) / 2)); hw = w_w / 2
                if is_h: wx = min(xs[i1], xs[i2]) + w_pos; wy = cross_min; ww = w_w; wh2 = thick_m
                else: wx = cross_min; wy = min(ys[j1], ys[j2]) + w_pos; ww = thick_m; wh2 = w_w
                wname = wm_win.get(winfo.get("id")) or winfo.get("name", "")
                w_errs = _validate_opening_coords(wk, wname or "شباك", "win", w_w, float(winfo.get("h_m", 1.2)), w_pos, current_op_id=winfo.get("id"))
                w_edge = "#D32F2F" if w_errs else "#004488"
                w_lw = 2.2 if w_errs else 1.2
                ax.add_patch(patches.Rectangle((wx, wy), ww, wh2, lw=w_lw, edgecolor=w_edge, facecolor=_CLR_WIN, alpha=0.88, zorder=4))
                if wname:
                    pk = round(w_pos, 2)
                    win_groups.setdefault(pk, {"names": [], "has_err": False, "wx": wx, "ww": ww, "wy": wy, "wh2": wh2})
                    win_groups[pk]["names"].append(wname)
                    if w_errs: win_groups[pk]["has_err"] = True

            for pk, g in win_groups.items():
                w_label = " / ".join(g["names"])
                t_col = "#B71C1C" if (g["has_err"] or len(g["names"]) > 1) else "#003366"
                if is_h:
                    ax.text(g["wx"] + g["ww"] / 2, cross_min - half_t * 1.5, w_label, ha="center", va="top", fontsize=fs_win, color=t_col, fontweight="bold", zorder=6)
                else:
                    ax.text(cross_min - half_t * 1.5, g["wy"] + g["wh2"] / 2, w_label, ha="right", va="center", fontsize=fs_win, color=t_col, fontweight="bold", zorder=6)


        doors = _get_wall_doors(wk)
        if not removed and doors:
            wlen = _wall_length_m(wk)
            door_t = 0.05  # 5 سم المسافة بين خطي ضلفة الباب
            for dinfo in doors:
                if dinfo.get("removed", False) or dinfo.get("id") in del_door_ids: continue
                d_w = float(dinfo.get("w_m", 0.9)); d_pos = float(dinfo.get("pos_m", (wlen - d_w) / 2)); hd = d_w / 2
                dt = min(door_t, d_w * 0.15)
                dname = wm_door.get(dinfo.get("id")) or dinfo.get("name", "")
                if is_h:
                    x_start = min(xs[i1], xs[i2])
                    x0 = x_start + d_pos
                    x1 = x0 + d_w
                    x_c = (x0 + x1) / 2.0
                    y_c = cross_c
                    
                    # قراءة اتجاه الخطين المتعامدين وموضع المفصلة
                    def_leaf = "أسفل" if y_c >= y_max - 1e-4 else "أعلى"
                    leaf_d = dinfo.get("leaf_dir", def_leaf)
                    if leaf_d not in ["أعلى", "أسفل"]: leaf_d = def_leaf
                    
                    d_errs = _validate_opening_coords(wk, dname or "باب", "door", d_w, float(dinfo.get("h_m", 2.1)), d_pos, leaf_dir=leaf_d, current_op_id=dinfo.get("id"))
                    door_clr = "#D32F2F" if d_errs else _CLR_DOOR
                    door_lw = 2.4 if d_errs else 1.8
                    
                    # تفريغ فتحة الباب في الحائط
                    ax.add_patch(patches.Rectangle((x0, cross_min - 0.002), d_w, thick_m + 0.004,
                                                   facecolor="#F8F8F8", edgecolor="none", zorder=3))
                    # خطي الحلق عند طرفي الفتحة
                    ax.plot([x0, x0], [cross_min, cross_max], color="#D32F2F" if d_errs else "#333333", lw=1.2 if d_errs else 1.0, zorder=3.5)
                    ax.plot([x1, x1], [cross_min, cross_max], color="#D32F2F" if d_errs else "#333333", lw=1.2 if d_errs else 1.0, zorder=3.5)
                    if dname:
                        ax.text(x_c, y_c, dname, ha="center", va="center", fontsize=fs_door, color=door_clr, fontweight="bold", zorder=6)
                    
                    sdir = 1 if leaf_d == "أعلى" else -1
                    y_ref = cross_max if sdir == 1 else cross_min
                    y_tip = y_ref + sdir * d_w
                    
                    hinge_d = dinfo.get("hinge_dir", "يسار")
                    if hinge_d not in ["يسار", "يمين"]: hinge_d = "يسار"
                    
                    if hinge_d == "يسار":
                        hx = x0; opp_x = x1
                        ax.plot([hx, hx], [y_ref, y_tip], color=door_clr, lw=door_lw, zorder=5)
                        ax.plot([hx + dt, hx + dt], [y_ref, y_tip], color=door_clr, lw=door_lw, zorder=5)
                        ax.plot([hx, hx + dt], [y_tip, y_tip], color=door_clr, lw=door_lw * 0.8, zorder=5)
                        ax.plot([hx, opp_x], [y_tip, y_ref], color=door_clr, lw=1.3, ls="-", zorder=5)
                        theta1, theta2 = (0, 90) if sdir == 1 else (270, 360)
                        ax.add_patch(patches.Arc((hx, y_ref), 2 * d_w, 2 * d_w, angle=0,
                                                 theta1=theta1, theta2=theta2, color=door_clr, lw=1.0, ls="--", zorder=5))
                    else: # يمين
                        hx = x1; opp_x = x0
                        ax.plot([hx, hx], [y_ref, y_tip], color=door_clr, lw=door_lw, zorder=5)
                        ax.plot([hx - dt, hx - dt], [y_ref, y_tip], color=door_clr, lw=door_lw, zorder=5)
                        ax.plot([hx - dt, hx], [y_tip, y_tip], color=door_clr, lw=door_lw * 0.8, zorder=5)
                        ax.plot([hx, opp_x], [y_tip, y_ref], color=door_clr, lw=1.3, ls="-", zorder=5)
                        theta1, theta2 = (90, 180) if sdir == 1 else (180, 270)
                        ax.add_patch(patches.Arc((hx, y_ref), 2 * d_w, 2 * d_w, angle=0,
                                                 theta1=theta1, theta2=theta2, color=door_clr, lw=1.0, ls="--", zorder=5))
                else:
                    y_start = min(ys[j1], ys[j2])
                    y0 = y_start + d_pos
                    y1 = y0 + d_w
                    y_c = (y0 + y1) / 2.0
                    x_c = cross_c
                    
                    # قراءة اتجاه الخطين المتعامدين وموضع المفصلة
                    def_leaf = "يسار" if x_c >= x_max - 1e-4 else "يمين"
                    leaf_d = dinfo.get("leaf_dir", def_leaf)
                    if leaf_d not in ["يمين", "يسار"]: leaf_d = def_leaf
                    
                    d_errs = _validate_opening_coords(wk, dname or "باب", "door", d_w, float(dinfo.get("h_m", 2.1)), d_pos, leaf_dir=leaf_d, current_op_id=dinfo.get("id"))
                    door_clr = "#D32F2F" if d_errs else _CLR_DOOR
                    door_lw = 2.4 if d_errs else 1.8
                    
                    # تفريغ فتحة الباب في الحائط
                    ax.add_patch(patches.Rectangle((cross_min - 0.002, y0), thick_m + 0.004, d_w,
                                                   facecolor="#F8F8F8", edgecolor="none", zorder=3))
                    # خطي الحلق عند طرفي الفتحة
                    ax.plot([cross_min, cross_max], [y0, y0], color="#D32F2F" if d_errs else "#333333", lw=1.2 if d_errs else 1.0, zorder=3.5)
                    ax.plot([cross_min, cross_max], [y1, y1], color="#D32F2F" if d_errs else "#333333", lw=1.2 if d_errs else 1.0, zorder=3.5)
                    if dname:
                        ax.text(x_c, y_c, dname, ha="center", va="center", fontsize=fs_door, color=door_clr, fontweight="bold", zorder=6)
                    
                    sdir = 1 if leaf_d == "يمين" else -1
                    x_ref = cross_max if sdir == 1 else cross_min
                    x_tip = x_ref + sdir * d_w
                    
                    hinge_d = dinfo.get("hinge_dir", "أسفل")
                    if hinge_d not in ["أسفل", "أعلى"]: hinge_d = "أسفل"
                    
                    if hinge_d == "أسفل":
                        hy = y0; opp_y = y1
                        ax.plot([x_ref, x_tip], [hy, hy], color=door_clr, lw=door_lw, zorder=5)
                        ax.plot([x_ref, x_tip], [hy + dt, hy + dt], color=door_clr, lw=door_lw, zorder=5)
                        ax.plot([x_tip, x_tip], [hy, hy + dt], color=door_clr, lw=door_lw * 0.8, zorder=5)
                        ax.plot([x_tip, x_ref], [hy, opp_y], color=door_clr, lw=1.3, ls="-", zorder=5)
                        theta1, theta2 = (0, 90) if sdir == 1 else (90, 180)
                        ax.add_patch(patches.Arc((x_ref, hy), 2 * d_w, 2 * d_w, angle=0,
                                                 theta1=theta1, theta2=theta2, color=door_clr, lw=1.0, ls="--", zorder=5))
                    else: # أعلى
                        hy = y1; opp_y = y0
                        ax.plot([x_ref, x_tip], [hy, hy], color=door_clr, lw=door_lw, zorder=5)
                        ax.plot([x_ref, x_tip], [hy - dt, hy - dt], color=door_clr, lw=door_lw, zorder=5)
                        ax.plot([x_tip, x_tip], [hy - dt, hy], color=door_clr, lw=door_lw * 0.8, zorder=5)
                        ax.plot([x_tip, x_ref], [hy, opp_y], color=door_clr, lw=1.3, ls="-", zorder=5)
                        theta1, theta2 = (270, 360) if sdir == 1 else (180, 270)
                        ax.add_patch(patches.Arc((x_ref, hy), 2 * d_w, 2 * d_w, angle=0,
                                                 theta1=theta1, theta2=theta2, color=door_clr, lw=1.0, ls="--", zorder=5))

        # ── رسم الكائن الافتراضي المؤقت (Preview / Ghost Instance Object) على الحائط ──
        preview_op = st.session_state.get("m15_preview_opening")
        if not removed and preview_op and preview_op.get("wk") == wk:
            p_kind = preview_op.get("kind")
            has_err = preview_op.get("has_conflict", False)
            p_name = preview_op.get("name", "Ghost")

            if p_kind == "win":
                pw_w = float(preview_op.get("w_m", 1.0))
                pw_pos = float(preview_op.get("pos_m", 0.0))
                if is_h:
                    pwx = min(xs[i1], xs[i2]) + pw_pos
                    pwy = cross_min
                    pww = pw_w
                    pwh2 = thick_m
                else:
                    pwx = cross_min
                    pwy = min(ys[j1], ys[j2]) + pw_pos
                    pww = thick_m
                    pwh2 = pw_w
                pw_edge = "#D32F2F" if has_err else "#1565C0"
                pw_face = "#FFCDD2" if has_err else "#BBDEFB"
                pw_hatch = "//" if has_err else ".."
                ax.add_patch(patches.Rectangle(
                    (pwx, pwy), pww, pwh2, lw=2.4, linestyle="--", edgecolor=pw_edge,
                    facecolor=pw_face, alpha=0.88, hatch=pw_hatch, zorder=6
                ))
                pw_lbl = f"⚠️ {p_name} [مؤقت/تعارض]" if has_err else f"🪟 {p_name} [معاينة مؤقتة]"
                pw_txt_clr = "#B71C1C" if has_err else "#0D47A1"
                if is_h:
                    ax.text(pwx + pww / 2, cross_min - half_t * 1.8, pw_lbl, ha="center", va="top",
                            fontsize=fs_win, color=pw_txt_clr, fontweight="bold", zorder=7,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=pw_edge, lw=1.0, alpha=0.95))
                else:
                    ax.text(cross_min - half_t * 1.8, pwy + pwh2 / 2, pw_lbl, ha="right", va="center",
                            fontsize=fs_win, color=pw_txt_clr, fontweight="bold", zorder=7,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=pw_edge, lw=1.0, alpha=0.95))
            elif p_kind == "door":
                pd_w = float(preview_op.get("w_m", 0.9))
                pd_pos = float(preview_op.get("pos_m", 0.0))
                pdt = min(0.05, pd_w * 0.15)
                pd_clr = "#D32F2F" if has_err else "#2E7D32"
                pd_lw = 2.4 if has_err else 1.8
                pd_ls = "--"
                pd_lbl = f"⚠️ {p_name} [مؤقت/تعارض]" if has_err else f"🚪 {p_name} [معاينة مؤقتة]"

                if is_h:
                    x_start = min(xs[i1], xs[i2])
                    px0 = x_start + pd_pos
                    px1 = px0 + pd_w
                    px_c = (px0 + px1) / 2.0
                    py_c = cross_c
                    def_leaf = "أسفل" if py_c >= y_max - 1e-4 else "أعلى"
                    leaf_d = preview_op.get("leaf_dir", def_leaf)
                    if leaf_d not in ["أعلى", "أسفل"]: leaf_d = def_leaf

                    ax.add_patch(patches.Rectangle(
                        (px0, cross_min - 0.002), pd_w, thick_m + 0.004,
                        facecolor="#FFEBEE" if has_err else "#F8F8F8", edgecolor=pd_clr, lw=1.5, linestyle="--", zorder=3.2
                    ))
                    ax.plot([px0, px0], [cross_min, cross_max], color=pd_clr, lw=1.4, linestyle="--", zorder=3.5)
                    ax.plot([px1, px1], [cross_min, cross_max], color=pd_clr, lw=1.4, linestyle="--", zorder=3.5)
                    ax.text(px_c, py_c, pd_lbl, ha="center", va="center", fontsize=fs_door, color=pd_clr, fontweight="bold", zorder=7,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=pd_clr, lw=1.0, alpha=0.95))

                    sdir = 1 if leaf_d == "أعلى" else -1
                    y_ref = cross_max if sdir == 1 else cross_min
                    y_tip = y_ref + sdir * pd_w
                    hinge_d = preview_op.get("hinge_dir", "يسار")
                    if hinge_d not in ["يسار", "يمين"]: hinge_d = "يسار"

                    if hinge_d == "يسار":
                        hx = px0; opp_x = px1
                        ax.plot([hx, hx], [y_ref, y_tip], color=pd_clr, lw=pd_lw, linestyle=pd_ls, zorder=5)
                        ax.plot([hx + pdt, hx + pdt], [y_ref, y_tip], color=pd_clr, lw=pd_lw, linestyle=pd_ls, zorder=5)
                        ax.plot([hx, hx + pdt], [y_tip, y_tip], color=pd_clr, lw=pd_lw * 0.8, linestyle=pd_ls, zorder=5)
                        ax.plot([hx, opp_x], [y_tip, y_ref], color=pd_clr, lw=1.3, ls=":", zorder=5)
                        theta1, theta2 = (0, 90) if sdir == 1 else (270, 360)
                        ax.add_patch(patches.Arc((hx, y_ref), 2 * pd_w, 2 * pd_w, angle=0,
                                                 theta1=theta1, theta2=theta2, color=pd_clr, lw=1.2, ls="--", zorder=5))
                    else:
                        hx = px1; opp_x = px0
                        ax.plot([hx, hx], [y_ref, y_tip], color=pd_clr, lw=pd_lw, linestyle=pd_ls, zorder=5)
                        ax.plot([hx - pdt, hx - pdt], [y_ref, y_tip], color=pd_clr, lw=pd_lw, linestyle=pd_ls, zorder=5)
                        ax.plot([hx - pdt, hx], [y_tip, y_tip], color=pd_clr, lw=pd_lw * 0.8, linestyle=pd_ls, zorder=5)
                        ax.plot([hx, opp_x], [y_tip, y_ref], color=pd_clr, lw=1.3, ls=":", zorder=5)
                        theta1, theta2 = (90, 180) if sdir == 1 else (180, 270)
                        ax.add_patch(patches.Arc((hx, y_ref), 2 * pd_w, 2 * pd_w, angle=0,
                                                 theta1=theta1, theta2=theta2, color=pd_clr, lw=1.2, ls="--", zorder=5))
                else:
                    y_start = min(ys[j1], ys[j2])
                    py0 = y_start + pd_pos
                    py1 = py0 + pd_w
                    py_c = (py0 + py1) / 2.0
                    px_c = cross_c
                    def_leaf = "يسار" if px_c >= x_max - 1e-4 else "يمين"
                    leaf_d = preview_op.get("leaf_dir", def_leaf)
                    if leaf_d not in ["يمين", "يسار"]: leaf_d = def_leaf

                    ax.add_patch(patches.Rectangle(
                        (cross_min - 0.002, py0), thick_m + 0.004, pd_w,
                        facecolor="#FFEBEE" if has_err else "#F8F8F8", edgecolor=pd_clr, lw=1.5, linestyle="--", zorder=3.2
                    ))
                    ax.plot([cross_min, cross_max], [py0, py0], color=pd_clr, lw=1.4, linestyle="--", zorder=3.5)
                    ax.plot([cross_min, cross_max], [py1, py1], color=pd_clr, lw=1.4, linestyle="--", zorder=3.5)
                    ax.text(px_c, py_c, pd_lbl, ha="center", va="center", fontsize=fs_door, color=pd_clr, fontweight="bold", zorder=7,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=pd_clr, lw=1.0, alpha=0.95))

                    sdir = 1 if leaf_d == "يمين" else -1
                    x_ref = cross_max if sdir == 1 else cross_min
                    x_tip = x_ref + sdir * pd_w
                    hinge_d = preview_op.get("hinge_dir", "أسفل")
                    if hinge_d not in ["أسفل", "أعلى"]: hinge_d = "أسفل"

                    if hinge_d == "أسفل":
                        hy = py0; opp_y = py1
                        ax.plot([x_ref, x_tip], [hy, hy], color=pd_clr, lw=pd_lw, linestyle=pd_ls, zorder=5)
                        ax.plot([x_ref, x_tip], [hy + pdt, hy + pdt], color=pd_clr, lw=pd_lw, linestyle=pd_ls, zorder=5)
                        ax.plot([x_tip, x_tip], [hy, hy + pdt], color=pd_clr, lw=pd_lw * 0.8, linestyle=pd_ls, zorder=5)
                        ax.plot([x_tip, x_ref], [hy, opp_y], color=pd_clr, lw=1.3, ls=":", zorder=5)
                        theta1, theta2 = (0, 90) if sdir == 1 else (90, 180)
                        ax.add_patch(patches.Arc((x_ref, hy), 2 * pd_w, 2 * pd_w, angle=0,
                                                 theta1=theta1, theta2=theta2, color=pd_clr, lw=1.2, ls="--", zorder=5))
                    else:
                        hy = py1; opp_y = py0
                        ax.plot([x_ref, x_tip], [hy, hy], color=pd_clr, lw=pd_lw, linestyle=pd_ls, zorder=5)
                        ax.plot([x_ref, x_tip], [hy - pdt, hy - pdt], color=pd_clr, lw=pd_lw, linestyle=pd_ls, zorder=5)
                        ax.plot([x_tip, x_tip], [hy - pdt, hy], color=pd_clr, lw=pd_lw * 0.8, linestyle=pd_ls, zorder=5)
                        ax.plot([x_tip, x_ref], [hy, opp_y], color=pd_clr, lw=1.3, ls=":", zorder=5)
                        theta1, theta2 = (270, 360) if sdir == 1 else (180, 270)
                        ax.add_patch(patches.Arc((x_ref, hy), 2 * pd_w, 2 * pd_w, angle=0,
                                                 theta1=theta1, theta2=theta2, color=pd_clr, lw=1.2, ls="--", zorder=5))

    # ── كتابة أسماء الحوائط المدمجة على المسقط الأفقي المصمم ──
    # دمج أسماء الحوائط المتلاصقة التي لا يفصلها عمود ولا حائط متعامد في اسم واحد بمنتصف الحائط
    merged_groups = _get_merged_wall_display_groups()
    merge_style = st.session_state.get("m15_merged_wall_label_style", "single")
    for grp in merged_groups:
        names = [wm.get(s, "") for s in grp if wm.get(s, "")]
        if not names:
            continue
        first_seg = grp[0]
        i1, j1, i2, j2 = first_seg
        is_h = (j1 == j2)
        cross_min, cross_max, cross_c, thick_m = _get_wall_cross_bounds(first_seg)
        half_t = thick_m / 2.0
        is_parapet = any(_is_parapet_wall(s) for s in grp)

        if len(names) > 1 and merge_style == "range":
            base_name = f"{names[0]}-{names[-1]}"
        else:
            base_name = names[0]

        label_text = f"{base_name} [حائط دروة]" if is_parapet else base_name
        t_box_edge = "#0284c7" if is_parapet else "#cbd5e1"
        t_box_bg = "#e0f2fe" if is_parapet else "#ffffff"
        t_color = "#0369a1" if is_parapet else "#1e293b"

        if is_h:
            min_x = min(min(xs[s[0]], xs[s[2]]) for s in grp)
            max_x = max(max(xs[s[0]], xs[s[2]]) for s in grp)
            mx = (min_x + max_x) / 2.0
            ax.text(mx, cross_max + half_t * 1.5, label_text, ha="center", va="bottom",
                    fontsize=fs_wall, color=t_color, fontweight="bold", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.18", facecolor=t_box_bg, edgecolor=t_box_edge, lw=0.8 if is_parapet else 0.6, alpha=0.92))
        else:
            min_y = min(min(ys[s[1]], ys[s[3]]) for s in grp)
            max_y = max(max(ys[s[1]], ys[s[3]]) for s in grp)
            my = (min_y + max_y) / 2.0
            ax.text(cross_max + half_t * 1.5, my, label_text, ha="left", va="center",
                    fontsize=fs_wall, color=t_color, fontweight="bold", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.18", facecolor=t_box_bg, edgecolor=t_box_edge, lw=0.8 if is_parapet else 0.6, alpha=0.92))

    col_size = _get_col_size()
    for (i, j) in _get_active_columns():
        cx, cy = _col_center(i, j)
        cw, ch = _get_col_wh(i, j)
        ax.add_patch(patches.Rectangle((cx - cw / 2, cy - ch / 2), cw, ch, lw=1.0, edgecolor="#000022", facecolor=_CLR_COL, alpha=0.92, zorder=6))
        cname = cm.get((i, j), "")
        if cname:
            # كتابة اسم العمود أعلى يمين العمود الموجود في الرسم
            ax.text(cx + cw / 2 + col_size * 0.15, cy + ch / 2 + col_size * 0.15, cname,
                    ha="left", va="bottom", fontsize=fs_col, color="#1A1A6E", fontweight="bold", zorder=7)

    # ── علامات بصرية توضيحية أثناء وضع استعادة الأعمدة (عرض الأعمدة المحذوفة كأشباح استرشادية) ──
    if st.session_state.get("m15_restore_col_mode", False):
        deleted_hist = st.session_state.get("m15_deleted_cols_history", {})
        for (ri, rj) in removed_cols:
            if 0 <= ri < len(xs) and 0 <= rj < len(ys):
                rcx, rcy = _col_center(ri, rj)
                rcw, rch = _get_col_wh(ri, rj)
                ax.add_patch(patches.Rectangle((rcx - rcw / 2, rcy - rch / 2), rcw, rch, lw=1.5, ls="--", edgecolor="#ef4444", facecolor="#fee2e2", alpha=0.6, zorder=6.5))
                orig_cn = f"C{rj * len(xs) + ri + 1}"
                r_model = deleted_hist.get((ri, rj), {}).get("model", orig_cn)
                ax.text(rcx, rcy, f"🗑️ {r_model}", ha="center", va="center", fontsize=round(fs_col * 0.82, 1), color="#dc2626", fontweight="bold", zorder=7)

    # ── علامات استرشادية لتقاطعات المحاور الشاغرة أثناء وضع إضافة الأعمدة ──
    if st.session_state.get("m15_add_col_mode", False):
        active_set = set(_get_active_columns())
        for i_idx, ax_x in enumerate(xs):
            for j_idx, ax_y in enumerate(ys):
                if (i_idx, j_idx) not in active_set:
                    ax.plot(ax_x, ax_y, marker="+", markersize=10, markeredgewidth=1.5, color="#0284c7", alpha=0.8, zorder=5.8)

    # ── إسقاط تسميات المساحات الداخلية المحددة طبقاً للحوائط فقط (وليس طبقاً للمحاور) ──
    named_spaces = st.session_state.get("m15_named_spaces", [])
    if named_spaces:
        for s in named_spaces:
            sx, sy = s["cx"], s["cy"]
            s_name = s.get("name", s.get("id", ""))
            s_code = s.get("code", "")
            s_area = s.get("clear_area_m2", 0.0)
            if s_code and s_code not in s_name:
                txt_lbl = f"{s_name} ({s_code})\n{s_area:.2f} م²" if s_area > 0 else f"{s_name} ({s_code})"
            else:
                txt_lbl = f"{s_name}\n{s_area:.2f} م²" if s_area > 0 else s_name
            ax.text(
                sx, sy, txt_lbl,
                ha="center", va="center",
                fontsize=fs_col * 0.95,
                color="#0369a1",
                fontweight="heavy",
                zorder=7.5,
                bbox=dict(
                    boxstyle="round,pad=0.42",
                    facecolor="#f0f9ff",
                    edgecolor="#0284c7",
                    lw=1.6,
                    alpha=0.94
                )
            )

    # ── خط أبعاد مؤقت لموضع تحريك الفتحة (نافذة/باب) مع نقطة بداية الحائط ──
    active_move_dim = (st.session_state.get("m15_active_move_dim") if with_dim else None)
    if active_move_dim:
        m_ts = float(active_move_dim.get("ts", 0.0))
        if (time.time() - m_ts) < 4.2:
            m_wk = active_move_dim.get("wk")
            if m_wk and m_wk in _get_all_walls() and m_wk not in removed_walls:
                mi1, mj1, mi2, mj2 = m_wk
                m_thick = _get_wall_thickness(m_wk)
                m_cross_min, m_cross_max, m_cross_c, m_thick_m = _get_wall_cross_bounds(m_wk)
                m_half_t = m_thick_m / 2.0
                m_is_h = (mj1 == mj2)
                m_pos = float(active_move_dim.get("pos_m", 0.0))
                m_w = float(active_move_dim.get("w_m", 1.0))
                m_kind_ar = active_move_dim.get("kind_ar", "الفتحة")
                m_name = active_move_dim.get("name", "")

                if m_is_h:
                    m_x_start = min(xs[mi1], xs[mi2])
                    m_y_wall = m_cross_c
                    m_x_op_start = m_x_start + m_pos
                    m_x_op_end = m_x_op_start + m_w
                    
                    y_sign = -1.0 if (m_cross_max >= max(ys) - 1e-4) else 1.0
                    m_y_dim = (m_cross_max if y_sign == 1.0 else m_cross_min) + y_sign * 0.42
                    
                    # 1. علامة نقطة بداية الحائط (نقطة الأصل 0.00م)
                    ax.plot([m_x_start], [m_y_wall], marker="o", markersize=9, color="#DC2626", markeredgecolor="#FFFFFF", markeredgewidth=2.0, zorder=10)
                    ax.plot([m_x_start], [m_y_wall], marker="o", markersize=3, color="#FFFFFF", zorder=10.1)
                    orig_y = (m_cross_min if y_sign == 1.0 else m_cross_max) - y_sign * 0.26
                    va_orig = "top" if y_sign == 1.0 else "bottom"
                    ax.text(m_x_start, orig_y, "📍 بداية الحائط (0.00م)", ha="center", va=va_orig,
                            fontsize=fs_dim, color="#B91C1C", fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.25", facecolor="#FEF2F2", edgecolor="#DC2626", lw=1.2, alpha=0.96), zorder=10.2)
                    
                    # 2. إطار تحديد مضيء للفتحة المتحركة
                    ax.add_patch(patches.Rectangle((m_x_op_start, m_cross_min), m_w, m_thick_m,
                                                   fill=False, edgecolor="#2563EB", lw=2.4, linestyle="--", zorder=9.5))
                    ax.plot([m_x_op_start], [m_y_wall], marker="d", markersize=8, color="#2563EB", markeredgecolor="#FFFFFF", markeredgewidth=1.6, zorder=10)

                    # 3. خط البعد المعماري
                    y_ref_line = m_cross_max if y_sign == 1.0 else m_cross_min
                    if m_pos >= 0.04:
                        ax.plot([m_x_start, m_x_start], [y_ref_line, m_y_dim + y_sign * 0.10],
                                color="#2563EB", lw=1.3, ls=":", zorder=9.8)
                        ax.plot([m_x_op_start, m_x_op_start], [y_ref_line, m_y_dim + y_sign * 0.10],
                                color="#2563EB", lw=1.3, ls=":", zorder=9.8)
                        ax.plot([m_x_start, m_x_op_start], [m_y_dim, m_y_dim], color="#1D4ED8", lw=2.0, ls="-", zorder=9.9)
                        dt_s = 0.08
                        ax.plot([m_x_start - dt_s, m_x_start + dt_s], [m_y_dim - dt_s, m_y_dim + dt_s], color="#1D4ED8", lw=2.2, zorder=10)
                        ax.plot([m_x_op_start - dt_s, m_x_op_start + dt_s], [m_y_dim - dt_s, m_y_dim + dt_s], color="#1D4ED8", lw=2.2, zorder=10)
                        x_mid = (m_x_start + m_x_op_start) / 2.0
                        y_txt = m_y_dim + y_sign * 0.09
                        va_txt = "bottom" if y_sign == 1.0 else "top"
                        txt_val = f"📏 بعد بداية {m_kind_ar}: {m_pos:.2f}م"
                        ax.text(x_mid, y_txt, txt_val, ha="center", va=va_txt, fontsize=fs_dim + 1.2,
                                color="#1E3A8A", fontweight="bold",
                                bbox=dict(boxstyle="round,pad=0.32", facecolor="#EFF6FF", edgecolor="#2563EB", lw=1.5, alpha=0.98), zorder=10.3)
                    else:
                        y_txt = y_ref_line + y_sign * 0.35
                        va_txt = "bottom" if y_sign == 1.0 else "top"
                        ax.text(m_x_start, y_txt, f"📏 بداية {m_kind_ar} عند نقطة الأصل (0.00م)", ha="center", va=va_txt,
                                fontsize=fs_dim + 1.2, color="#1E3A8A", fontweight="bold",
                                bbox=dict(boxstyle="round,pad=0.32", facecolor="#EFF6FF", edgecolor="#2563EB", lw=1.5, alpha=0.98), zorder=10.3)

                else:
                    m_y_start = min(ys[mj1], ys[mj2])
                    m_x_wall = m_cross_c
                    m_y_op_start = m_y_start + m_pos
                    m_y_op_end = m_y_op_start + m_w

                    x_sign = -1.0 if (m_cross_max >= max(xs) - 1e-4) else 1.0
                    m_x_dim = (m_cross_max if x_sign == 1.0 else m_cross_min) + x_sign * 0.42

                    # 1. علامة نقطة بداية الحائط
                    ax.plot([m_x_wall], [m_y_start], marker="o", markersize=9, color="#DC2626", markeredgecolor="#FFFFFF", markeredgewidth=2.0, zorder=10)
                    ax.plot([m_x_wall], [m_y_start], marker="o", markersize=3, color="#FFFFFF", zorder=10.1)
                    orig_x = (m_cross_min if x_sign == 1.0 else m_cross_max) - x_sign * 0.26
                    ha_orig = "right" if x_sign == 1.0 else "left"
                    ax.text(orig_x, m_y_start, "📍 بداية الحائط (0.00م)", ha=ha_orig, va="center",
                            fontsize=fs_dim, color="#B91C1C", fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.25", facecolor="#FEF2F2", edgecolor="#DC2626", lw=1.2, alpha=0.96), zorder=10.2)

                    # 2. إطار تحديد مضيء للفتحة المتحركة
                    ax.add_patch(patches.Rectangle((m_cross_min, m_y_op_start), m_thick_m, m_w,
                                                   fill=False, edgecolor="#2563EB", lw=2.4, linestyle="--", zorder=9.5))
                    ax.plot([m_x_wall], [m_y_op_start], marker="d", markersize=8, color="#2563EB", markeredgecolor="#FFFFFF", markeredgewidth=1.6, zorder=10)

                    # 3. خط البعد المعماري
                    x_ref_line = m_cross_max if x_sign == 1.0 else m_cross_min
                    if m_pos >= 0.04:
                        ax.plot([x_ref_line, m_x_dim + x_sign * 0.10], [m_y_start, m_y_start],
                                color="#2563EB", lw=1.3, ls=":", zorder=9.8)
                        ax.plot([x_ref_line, m_x_dim + x_sign * 0.10], [m_y_op_start, m_y_op_start],
                                color="#2563EB", lw=1.3, ls=":", zorder=9.8)
                        ax.plot([m_x_dim, m_x_dim], [m_y_start, m_y_op_start], color="#1D4ED8", lw=2.0, ls="-", zorder=9.9)
                        dt_s = 0.08
                        ax.plot([m_x_dim - dt_s, m_x_dim + dt_s], [m_y_start - dt_s, m_y_start + dt_s], color="#1D4ED8", lw=2.2, zorder=10)
                        ax.plot([m_x_dim - dt_s, m_x_dim + dt_s], [m_y_op_start - dt_s, m_y_op_start + dt_s], color="#1D4ED8", lw=2.2, zorder=10)
                        y_mid = (m_y_start + m_y_op_start) / 2.0
                        x_txt = m_x_dim + x_sign * 0.09
                        ha_txt = "left" if x_sign == 1.0 else "right"
                        txt_val = f"📏 بعد بداية {m_kind_ar}: {m_pos:.2f}م"
                        ax.text(x_txt, y_mid, txt_val, ha=ha_txt, va="center", rotation=90, fontsize=fs_dim + 1.2,
                                color="#1E3A8A", fontweight="bold",
                                bbox=dict(boxstyle="round,pad=0.32", facecolor="#EFF6FF", edgecolor="#2563EB", lw=1.5, alpha=0.98), zorder=10.3)
                    else:
                        x_txt = x_ref_line + x_sign * 0.35
                        ha_txt = "left" if x_sign == 1.0 else "right"
                        ax.text(x_txt, m_y_start, f"📏 بداية {m_kind_ar} عند نقطة الأصل (0.00م)", ha=ha_txt, va="center",
                                rotation=90, fontsize=fs_dim + 1.2, color="#1E3A8A", fontweight="bold",
                                bbox=dict(boxstyle="round,pad=0.32", facecolor="#EFF6FF", edgecolor="#2563EB", lw=1.5, alpha=0.98), zorder=10.3)

    # ── خطوط الأبعاد المعمارية الخارجية على نمط الأوتوكاد (AutoCAD Dimension Chains) ──
    def _draw_cad_tick(tx, ty):
        ax.plot([tx - dt_tick, tx + dt_tick], [ty - dt_tick, ty + dt_tick], color="#0f172a", lw=1.6, zorder=4.5)

    # 1. الأبعاد السفلية (Bottom Chains) — المحاور الرأسية Y1, Y2, Y3...
    ax.plot([xs[0], xs[-1]], [y_dim_bot_bay, y_dim_bot_bay], color="#0f172a", lw=1.1, zorder=3)
    for x in xs:
        _draw_cad_tick(x, y_dim_bot_bay)
    for i in range(len(xs) - 1):
        x1, x2 = xs[i], xs[i + 1]
        sp = abs(x2 - x1)
        ax.text((x1 + x2) / 2.0, y_dim_bot_bay + dt_tick * 1.2, f"{sp:.2f}m", ha="center", va="bottom",
                fontsize=fs_dim, fontweight="bold", color="#0f172a", zorder=5,
                bbox=dict(boxstyle="square,pad=0.15", facecolor="#ffffff", edgecolor="none", alpha=0.90))

    # خط البعد الكلي الأفقي السفلي (Total Lx)
    ax.plot([xs[0], xs[-1]], [y_dim_bot_tot, y_dim_bot_tot], color="#1e3a8a", lw=1.2, zorder=3)
    _draw_cad_tick(xs[0], y_dim_bot_tot)
    _draw_cad_tick(xs[-1], y_dim_bot_tot)
    ax.text((xs[0] + xs[-1]) / 2.0, y_dim_bot_tot + dt_tick * 1.2, f"Total Lx = {span_x:.2f}m", ha="center", va="bottom",
            fontsize=fs_dim, fontweight="bold", color="#1e3a8a", zorder=5,
            bbox=dict(boxstyle="square,pad=0.15", facecolor="#ffffff", edgecolor="none", alpha=0.90))

    # دوائر المحاور السفلية (Bottom CAD Bubbles)
    for idx, x in enumerate(xs):
        bub = patches.Circle((x, y_bub_bot), radius=cad_bubble_r, facecolor="#ffffff", edgecolor=_CLR_AXIS_Y, lw=1.6, zorder=6)
        ax.add_patch(bub)
        ax.text(x, y_bub_bot, f"Y{idx+1}", color=_CLR_AXIS_Y, fontsize=fs_bubble, fontweight="bold", ha="center", va="center", zorder=7)

    # 2. الأبعاد العلوية (Top Chains) — المحاور الرأسية Y1, Y2, Y3...
    ax.plot([xs[0], xs[-1]], [y_dim_top_bay, y_dim_top_bay], color="#0f172a", lw=1.1, zorder=3)
    for x in xs:
        _draw_cad_tick(x, y_dim_top_bay)
    for i in range(len(xs) - 1):
        x1, x2 = xs[i], xs[i + 1]
        sp = abs(x2 - x1)
        ax.text((x1 + x2) / 2.0, y_dim_top_bay + dt_tick * 1.2, f"{sp:.2f}m", ha="center", va="bottom",
                fontsize=fs_dim, fontweight="bold", color="#0f172a", zorder=5,
                bbox=dict(boxstyle="square,pad=0.15", facecolor="#ffffff", edgecolor="none", alpha=0.90))

    # دوائر المحاور العلوية (Top CAD Bubbles)
    for idx, x in enumerate(xs):
        bub = patches.Circle((x, y_bub_top), radius=cad_bubble_r, facecolor="#ffffff", edgecolor=_CLR_AXIS_Y, lw=1.6, zorder=6)
        ax.add_patch(bub)
        ax.text(x, y_bub_top, f"Y{idx+1}", color=_CLR_AXIS_Y, fontsize=fs_bubble, fontweight="bold", ha="center", va="center", zorder=7)

    # 3. الأبعاد باليسار (Left Chains) — المحاور الأفقية X1, X2, X3...
    ax.plot([x_dim_left_bay, x_dim_left_bay], [ys[0], ys[-1]], color="#0f172a", lw=1.1, zorder=3)
    for y in ys:
        _draw_cad_tick(x_dim_left_bay, y)
    for j in range(len(ys) - 1):
        y1, y2 = ys[j], ys[j + 1]
        sp = abs(y2 - y1)
        ax.text(x_dim_left_bay - dt_tick * 1.2, (y1 + y2) / 2.0, f"{sp:.2f}m", ha="center", va="center", rotation=90,
                fontsize=fs_dim, fontweight="bold", color="#0f172a", zorder=5,
                bbox=dict(boxstyle="square,pad=0.15", facecolor="#ffffff", edgecolor="none", alpha=0.90))

    # خط البعد الكلي الرأسي باليسار (Total Ly)
    ax.plot([x_dim_left_tot, x_dim_left_tot], [ys[0], ys[-1]], color="#1e3a8a", lw=1.2, zorder=3)
    _draw_cad_tick(x_dim_left_tot, ys[0])
    _draw_cad_tick(x_dim_left_tot, ys[-1])
    ax.text(x_dim_left_tot - dt_tick * 1.2, (ys[0] + ys[-1]) / 2.0, f"Total Ly = {span_y:.2f}m", ha="center", va="center", rotation=90,
            fontsize=fs_dim, fontweight="bold", color="#1e3a8a", zorder=5,
            bbox=dict(boxstyle="square,pad=0.15", facecolor="#ffffff", edgecolor="none", alpha=0.90))

    # دوائر المحاور باليسار (Left CAD Bubbles)
    for idx, y in enumerate(ys):
        bub = patches.Circle((x_bub_left, y), radius=cad_bubble_r, facecolor="#ffffff", edgecolor=_CLR_AXIS_X, lw=1.6, zorder=6)
        ax.add_patch(bub)
        ax.text(x_bub_left, y, f"X{idx+1}", color=_CLR_AXIS_X, fontsize=fs_bubble, fontweight="bold", ha="center", va="center", zorder=7)

    # 4. الأبعاد باليمين (Right Chains) — المحاور الأفقية X1, X2, X3...
    ax.plot([x_dim_right_bay, x_dim_right_bay], [ys[0], ys[-1]], color="#0f172a", lw=1.1, zorder=3)
    for y in ys:
        _draw_cad_tick(x_dim_right_bay, y)
    for j in range(len(ys) - 1):
        y1, y2 = ys[j], ys[j + 1]
        sp = abs(y2 - y1)
        ax.text(x_dim_right_bay + dt_tick * 1.2, (y1 + y2) / 2.0, f"{sp:.2f}m", ha="center", va="center", rotation=90,
                fontsize=fs_dim, fontweight="bold", color="#0f172a", zorder=5,
                bbox=dict(boxstyle="square,pad=0.15", facecolor="#ffffff", edgecolor="none", alpha=0.90))

    # دوائر المحاور باليمين (Right CAD Bubbles)
    for idx, y in enumerate(ys):
        bub = patches.Circle((x_bub_right, y), radius=cad_bubble_r, facecolor="#ffffff", edgecolor=_CLR_AXIS_X, lw=1.6, zorder=6)
        ax.add_patch(bub)
        ax.text(x_bub_right, y, f"X{idx+1}", color=_CLR_AXIS_X, fontsize=fs_bubble, fontweight="bold", ha="center", va="center", zorder=7)

    # إخفاء تدرجات المحاور الإحداثية لتجنب التشويش مع خطوط الأبعاد
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#e2e8f0")
        spine.set_linewidth(1.0)

    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    leg = [
        Patch(facecolor=_CLR_WALL_12, alpha=0.85, label="حائط 12سم"),
        Patch(facecolor=_CLR_WALL_25, alpha=0.85, label="حائط 25سم"),
        Patch(facecolor=_CLR_WALL_PARAPET, alpha=0.90, label="حائط دروة"),
        Patch(facecolor=_CLR_WIN, alpha=0.85, label="شباك (W#)"),
        Patch(facecolor=_CLR_DOOR, alpha=0.90, label="باب (D#)"),
        Patch(facecolor=_CLR_COL, alpha=0.90, label="عمود (C#)"),
        Patch(facecolor="#f0f9ff", edgecolor="#0284c7", lw=1.5, label="مساحة (A#)"),
        Patch(facecolor="none", edgecolor="#EC4899", hatch="/", lw=0, label="وجه محارة"),
        Line2D([0], [0], color="#94a3b8", ls=":", lw=1.5, label="محذوف"),
        Line2D([0], [0], color="#0f172a", lw=1.2, marker="|", label="خط بعد"),
    ]
    ax.legend(
        handles=leg,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=len(leg),
        fontsize=round(fs_leg * 0.80, 1),
        frameon=True,
        framealpha=0.96,
        edgecolor="#cbd5e1",
        facecolor="#ffffff",
        borderaxespad=0.15,
        columnspacing=0.8,
        handletextpad=0.35,
        handlelength=1.2,
    )
    ax.set_title("Floor Plan — Module 15: Brick & Plastering Survey", fontsize=fs_title, fontweight="bold", pad=36)

    plt.tight_layout()
    pos = ax.get_position()
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    st.session_state["m15_plan_bbox_info"] = {
        "x0": float(pos.x0),
        "y0": float(pos.y0),
        "x1": float(pos.x1),
        "y1": float(pos.y1),
        "xlim": [float(xlim[0]), float(xlim[1])],
        "ylim": [float(ylim[0]), float(ylim[1])],
        "xs": [float(x) for x in xs],
        "ys": [float(y) for y in ys]
    }
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    try:
        st.session_state["m15_plan_png_b64"] = base64.b64encode(buf.getvalue()).decode("utf-8")
        buf.seek(0)
    except Exception:
        pass
    return buf

def _render_interactive_plan(b64_override=None, b64_clean=None, rem_ms=0, box_mode=None, box_hint=""):
    """
    عرض المسقط الأفقي تفاعلياً مع أدوات تحكم مباشرة على الرسم ونمط التحديد بصندوق الماوس (Box Selection Mode):
    - نمط إضافة الأعمدة (Add Mode) أو نمط استعادة الأعمدة (Restore Mode).
    - التقاط إحداثيات الصندوق [Xmin, Xmax, Ymin, Ymax] واستخراج نقطة تقاطع المحاور.
    - دعم كامل لأدوات الـ CAD: Zoom In, Zoom Out, Pan, Reset, Fullscreen, Download.
    - دعم زر Esc وزر 'إنهاء' للخروج من الوضع التفاعلي.
    """
    if box_mode is None:
        if st.session_state.get("m15_add_col_mode", False):
            box_mode = "add"
        elif st.session_state.get("m15_restore_col_mode", False):
            box_mode = "restore"
        elif st.session_state.get("m15_add_wall_mode", False):
            box_mode = "add_wall"
        elif st.session_state.get("m15_del_wall_mode", False):
            box_mode = "delete_wall"
        elif st.session_state.get("m15_add_win_mode", False):
            box_mode = "add_window"
        elif st.session_state.get("m15_add_door_mode", False):
            box_mode = "add_door"

    if box_mode == "add":
        box_hint = "اختر بالماوس صندوقاً يكون بداخله تقاطع المحورين الواقع العمود بداخله"
        banner_border = "#3b82f6"
        banner_bg = "linear-gradient(135deg, rgba(239, 246, 255, 0.98), rgba(219, 234, 254, 0.98))"
        banner_txt = "#1e40af"
        banner_icon = "🎯"
        box_border = "2px dashed #0284c7"
        box_bg = "rgba(2, 132, 199, 0.20)"
    elif box_mode == "restore":
        box_hint = "اسحب مربعاً بالماوس يحتوي على تقاطع المحورين المراد استعادة العمود عنده"
        banner_border = "#10b981"
        banner_bg = "linear-gradient(135deg, rgba(236, 253, 245, 0.98), rgba(209, 250, 229, 0.98))"
        banner_txt = "#065f46"
        banner_icon = "♻️"
        box_border = "2px dashed #059669"
        box_bg = "rgba(5, 150, 105, 0.20)"
    elif box_mode == "add_wall":
        box_hint = "اسحب مربعاً بالماوس يحدد بداية ونهاية الحائط المراد إسقاطه"
        banner_border = "#f59e0b"
        banner_bg = "linear-gradient(135deg, rgba(254, 243, 199, 0.98), rgba(253, 230, 138, 0.98))"
        banner_txt = "#92400e"
        banner_icon = "🧱"
        box_border = "2px dashed #f59e0b"
        box_bg = "rgba(245, 158, 11, 0.20)"
    elif box_mode == "delete_wall":
        box_hint = "اختر بالماوس صندوقاً يكون بداخله الحائط المراد حذفه"
        banner_border = "#ef4444"
        banner_bg = "linear-gradient(135deg, rgba(254, 242, 242, 0.98), rgba(254, 226, 226, 0.98))"
        banner_txt = "#991b1b"
        banner_icon = "🗑️"
        box_border = "2px dashed #ef4444"
        box_bg = "rgba(239, 68, 68, 0.20)"
    elif box_mode == "add_window":
        box_hint = "انقر أو اسحب بالماوس فوق الحائط لإسقاط الشباك في منتصفه"
        banner_border = "#0284c7"
        banner_bg = "linear-gradient(135deg, rgba(224, 242, 254, 0.98), rgba(186, 230, 253, 0.98))"
        banner_txt = "#0369a1"
        banner_icon = "🪟"
        box_border = "2px dashed #0284c7"
        box_bg = "rgba(2, 132, 199, 0.20)"
    elif box_mode == "add_door":
        box_hint = "انقر أو اسحب بالماوس فوق الحائط لإسقاط الباب في منتصفه"
        banner_border = "#16a34a"
        banner_bg = "linear-gradient(135deg, rgba(240, 253, 244, 0.98), rgba(220, 252, 231, 0.98))"
        banner_txt = "#15803d"
        banner_icon = "🚪"
        box_border = "2px dashed #16a34a"
        box_bg = "rgba(22, 163, 74, 0.20)"
    else:
        box_hint = ""
        banner_border = "#94a3b8"
        banner_bg = "rgba(255, 255, 255, 0.95)"
        banner_txt = "#1e293b"
        banner_icon = ""
        box_border = "1.5px dashed #0284c7"
        box_bg = "rgba(2, 132, 199, 0.15)"

    if b64_override:
        b64_img = b64_override
    else:
        buf = _draw_plan(with_dim=False)
        if buf is None:
            return
        img_bytes = buf.getvalue() if hasattr(buf, "getvalue") else buf.read()
        b64_img = base64.b64encode(img_bytes).decode("utf-8")

    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    span_x = max(xs) - min(xs) if xs else 1.0
    span_y = max(ys) - min(ys) if ys else 1.0
    fig_w = min(18, max(10, span_x * 1.6 + 2.5))
    fig_h = min(15, max(8, span_y * 1.6 + 2.5))
    ratio = fig_h / fig_w
    viewer_h = int(max(540, min(820, 740 * ratio)))

    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    if not isinstance(removed_walls, set):
        removed_walls = set(removed_walls)
    walls_list = []
    for wk in _get_all_walls():
        i1, j1, i2, j2 = wk
        if i1 < len(xs) and i2 < len(xs) and j1 < len(ys) and j2 < len(ys):
            walls_list.append({
                "wk": list(wk),
                "name": wm.get(wk, ""),
                "label": _wall_display_label(wk, cm, wm),
                "x1": round(float(xs[i1]), 3),
                "y1": round(float(ys[j1]), 3),
                "x2": round(float(xs[i2]), 3),
                "y2": round(float(ys[j2]), 3),
                "is_h": (j1 == j2),
                "thick_m": round(float(_get_wall_thickness(wk)) / 100.0, 3),
                "removed": wk in removed_walls
            })

    bbox_info = dict(st.session_state.get("m15_plan_bbox_info", {
        "x0": 0.05, "y0": 0.05, "x1": 0.95, "y1": 0.95,
        "xlim": [min(xs) - 1.5, max(xs) + 1.5] if xs else [0, 10],
        "ylim": [min(ys) - 1.5, max(ys) + 1.5] if ys else [0, 10],
        "xs": list(xs), "ys": list(ys)
    }))
    bbox_info["walls"] = walls_list
    bbox_json = json.dumps(bbox_info)
    mode_str = box_mode or ""
    box_banner_display = "none"
    viewport_box_class = "box-mode" if box_mode else ""
    if box_mode == "delete_wall":
        hint_text_toolbar = "🗑️ اسحب صندوقاً حول الحائط لحذفه"
    elif box_mode == "add_wall":
        hint_text_toolbar = "🧱 اسحب لتحديد بداية ونهاية الحائط المطلوب"
    elif box_mode == "add_window":
        hint_text_toolbar = "🪟 انقر أو اسحب لاختيار الحائط لإسقاط الشباك"
    elif box_mode == "add_door":
        hint_text_toolbar = "🚪 انقر أو اسحب لاختيار الحائط لإسقاط الباب"
    elif box_mode:
        hint_text_toolbar = "🎯 اسحب صندوقاً حول تقاطع المحورين"
    else:
        hint_text_toolbar = "✋ اسحب للتحريك | 🔍 بكرة الماوس للتكبير"

    html_content = f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body, html {{ width: 100%; height: 100%; overflow: hidden; background: #F8FAFC; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  
  #viewport {{
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #F8FAFC;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    cursor: grab;
    user-select: none;
    touch-action: none;
    box-shadow: inset 0 0 10px rgba(0,0,0,0.03);
  }}
  #viewport.box-mode,
  #viewport.box-mode #canvas-wrapper,
  #viewport.box-mode #plan-img {{
    cursor: crosshair !important;
  }}
  .cad-toolbar, .cad-toolbar *,
  #box-mode-banner, #box-mode-banner * {{
    cursor: default !important;
  }}
  .tb-btn, .btn-box-exit {{
    cursor: pointer !important;
  }}
  #viewport:active, #viewport.panning {{
    cursor: grabbing;
  }}
  
  /* علامات التحكم العائمة على الرسم مباشرة (Floating CAD Toolbar) */
  .cad-toolbar {{
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 1000;
    display: flex;
    align-items: center;
    gap: 5px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(6px);
    border: 1.5px solid #94a3b8;
    border-radius: 8px;
    padding: 5px 9px;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.15);
    direction: rtl;
  }}
  
  .tb-btn {{
    background: #1e293b;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
    color: #ffffff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    transition: all 0.15s ease;
    text-decoration: none;
    line-height: 1.2;
  }}
  .tb-btn-fp {{
    background: linear-gradient(135deg, #1e3a8a, #2563eb) !important;
    border: 1px solid #60a5fa !important;
    color: #ffffff !important;
  }}
  .tb-btn-fp:hover {{
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    box-shadow: 0 0 10px rgba(96, 165, 250, 0.5) !important;
  }}
  .tb-btn:hover {{
    background: #334155;
    border-color: #64748b;
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  }}
  .tb-btn:active {{
    transform: translateY(0);
    background: #475569;
  }}
  
  .zoom-badge {{
    font-size: 11.5px;
    font-weight: 800;
    color: #ffffff;
    background: #1e40af;
    border: 1px solid #3b82f6;
    border-radius: 12px;
    padding: 3px 8px;
    min-width: 46px;
    text-align: center;
    user-select: none;
  }}
  
  .tb-hint {{
    font-size: 11px;
    font-weight: 600;
    color: #64748b;
    margin-left: 6px;
    white-space: nowrap;
  }}

  /* شريط التنبيه الإرشادي لنمط التحديد بالصندوق */
  .box-mode-banner {{
    position: absolute;
    top: 10px;
    left: 10px;
    z-index: 1005;
    display: none !important;
    align-items: center;
    gap: 10px;
    background: {banner_bg};
    border: 2px solid {banner_border};
    border-radius: 8px;
    padding: 6px 14px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
    direction: rtl;
    max-width: 60%;
  }}
  .box-banner-text {{
    font-size: 12.5px;
    font-weight: 700;
    color: {banner_txt};
    line-height: 1.3;
  }}
  .btn-box-exit {{
    background: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11.5px;
    font-weight: 800;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s ease;
  }}
  .btn-box-exit:hover {{
    background: #dc2626;
    transform: scale(1.04);
  }}

  /* مربع التحديد التفاعلي (Selection Box) */
  #selection-box {{
    position: absolute;
    display: none;
    pointer-events: none;
    border: {box_border};
    background: {box_bg};
    border-radius: 4px;
    z-index: 999;
  }}
  #selection-badge {{
    position: absolute;
    bottom: -28px;
    right: 0;
    background: #0f172a;
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 6px;
    white-space: nowrap;
    box-shadow: 0 2px 8px rgba(0,0,0,0.35);
    pointer-events: none;
  }}

  #canvas-wrapper {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    transform-origin: 0 0;
    will-change: transform;
    display: flex;
    align-items: center;
    justify-content: center;
  }}

  #plan-img {{
    max-width: 98%;
    max-height: 98%;
    object-fit: contain;
    display: block;
    user-select: none;
    -webkit-user-drag: none;
    pointer-events: none;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
  }}
</style>
</head>
<body>

<div id="viewport" class="{viewport_box_class}">
  <!-- Floating CAD Toolbar -->
  <div class="cad-toolbar">
    <button class="tb-btn tb-btn-fp" id="btn-toggle-floating-plan" title="عرض / إخفاء المسقط المعماري الاسترشادي (Ctrl + Alt + F)">🖼️ المسقط الاسترشادي</button>
    <button class="tb-btn" id="btn-zoom-in" title="تكبير (Zoom In)">🔍➕ تكبير</button>
    <button class="tb-btn" id="btn-zoom-out" title="تصغير (Zoom Out)">🔍➖ تصغير</button>
    <button class="tb-btn" id="btn-reset" title="استعادة المركز والحجم الطبيعي (Reset 100%)">🔄 ضبط</button>
    <button class="tb-btn" id="btn-fullscreen" title="عرض ملء الشاشة (Fullscreen)">⛶ كامل الشاشة</button>
    <a class="tb-btn" id="btn-download" href="data:image/png;base64,{b64_img}" download="Floor_Plan_Module14.png" title="تنزيل الصورة (Download PNG)">💾 حفظ</a>
    <span class="zoom-badge" id="zoom-badge">100%</span>
    <span class="tb-hint">{hint_text_toolbar}</span>
  </div>

  <!-- Guidance banner for Box Selection Mode (hidden) -->
  <div class="box-mode-banner" id="box-mode-banner" style="display:none !important;">
    <span style="font-size: 1.15rem;">{banner_icon}</span>
    <span class="box-banner-text">{box_hint}</span>
    <button class="btn-box-exit" id="btn-box-exit" title="إنهاء (Esc)">⏹️ إنهاء (Esc)</button>
  </div>

  <!-- Selection Box Overlay -->
  <div id="selection-box">
    <div id="selection-badge"></div>
  </div>

  <div id="canvas-wrapper">
    <img id="plan-img" src="data:image/png;base64,{b64_img}" alt="Floor Plan" />
  </div>
</div>

<script>
(function() {{
  const viewport = document.getElementById('viewport');
  const wrapper = document.getElementById('canvas-wrapper');
  const planImg = document.getElementById('plan-img');
  const badge = document.getElementById('zoom-badge');
  const selBox = document.getElementById('selection-box');
  const selBadge = document.getElementById('selection-badge');
  const exitBtn = document.getElementById('btn-box-exit');

  const bboxInfo = {bbox_json};
  const currentBoxMode = "{mode_str}";

  let scale = 1.0;
  let panX = 0;
  let panY = 0;
  let isDragging = false;
  let startX = 0;
  let startY = 0;

  // Box selection state
  let isBoxSelecting = false;
  let boxStartX = 0;
  let boxStartY = 0;

  function updateTransform() {{
    wrapper.style.transform = 'translate(' + panX + 'px, ' + panY + 'px) scale(' + scale + ')';
    badge.textContent = Math.round(scale * 100) + '%';
  }}

  function applyZoom(factor, clientX, clientY) {{
    const newScale = Math.min(Math.max(scale * factor, 0.3), 8.0);
    if (newScale === scale) return;

    let cx, cy;
    if (clientX === undefined || clientY === undefined) {{
      const rect = viewport.getBoundingClientRect();
      cx = rect.width / 2;
      cy = rect.height / 2;
    }} else {{
      const rect = viewport.getBoundingClientRect();
      cx = clientX - rect.left;
      cy = clientY - rect.top;
    }}

    panX = cx - (cx - panX) * (newScale / scale);
    panY = cy - (cy - panY) * (newScale / scale);
    scale = newScale;
    updateTransform();
  }}

  function resetView() {{
    scale = 1.0;
    panX = 0;
    panY = 0;
    updateTransform();
  }}

  var btnFp = document.getElementById('btn-toggle-floating-plan');
  if (btnFp) {{
    btnFp.addEventListener('click', function(e) {{
      e.stopPropagation();
      try {{
        var pWin = (window.parent && window.parent.document) ? window.parent : window;
        if (pWin.m15ToggleFloatingPlan) pWin.m15ToggleFloatingPlan();
        else if (pWin.m12ToggleFloatingPlan) pWin.m12ToggleFloatingPlan();
      }} catch(err) {{}}
    }});
  }}

  document.getElementById('btn-zoom-in').addEventListener('click', function(e) {{
    e.stopPropagation();
    applyZoom(1.25);
  }});

  document.getElementById('btn-zoom-out').addEventListener('click', function(e) {{
    e.stopPropagation();
    applyZoom(0.80);
  }});

  document.getElementById('btn-reset').addEventListener('click', function(e) {{
    e.stopPropagation();
    resetView();
  }});

  document.getElementById('btn-fullscreen').addEventListener('click', function(e) {{
    e.stopPropagation();
    if (!document.fullscreenElement) {{
      if (viewport.requestFullscreen) viewport.requestFullscreen();
      else if (viewport.webkitRequestFullscreen) viewport.webkitRequestFullscreen();
    }} else {{
      if (document.exitFullscreen) document.exitFullscreen();
      else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
    }}
  }});

  // ── Sync to Streamlit Bridge ──
  function syncToStreamlit(payload) {{
    try {{
      const jsonStr = JSON.stringify(payload);
      let synced = false;
      try {{
        if (window.parent && window.parent.document) {{
          const pDoc = window.parent.document;
          let input = pDoc.querySelector('input[aria-label="m15_3d_sync_payload"]');
          if (!input) {{
            input = pDoc.querySelector('div[data-testid="stTextInput"] input');
          }}
          if (input) {{
            const proto = (window.parent.HTMLInputElement || window.HTMLInputElement).prototype;
            const desc = Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) {{
              desc.set.call(input, jsonStr);
            }} else {{
              input.value = jsonStr;
            }}
            if (input._valueTracker) {{
              input._valueTracker.setValue('');
            }}
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            input.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13, which: 13 }}));
            input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13, which: 13 }}));
            input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            synced = true;
          }}
        }}
      }} catch(e) {{
        console.warn("React bridge error:", e);
      }}

      // If React bridge couldn't find input or was blocked, immediately fallback to URL param
      if (!synced) {{
        try {{
          if (window.parent && window.parent.location) {{
            const pUrl = new URL(window.parent.location.href);
            pUrl.searchParams.set('m15_op_move', jsonStr);
            pUrl.searchParams.set('module', '12');
            window.parent.location.href = pUrl.toString();
          }}
        }} catch(e) {{
          console.warn("syncToStreamlit fallback error:", e);
        }}
      }} else {{
        // Extra resilience: If React bridge didn't trigger Streamlit rerun within 450ms, push via URL
        setTimeout(function() {{
          try {{
            if (window.parent && window.parent.location) {{
              const pUrl = new URL(window.parent.location.href);
              if (!pUrl.searchParams.has('m15_op_move')) {{
                pUrl.searchParams.set('m15_op_move', jsonStr);
                pUrl.searchParams.set('module', '12');
                window.parent.location.href = pUrl.toString();
              }}
            }}
          }} catch(e) {{}}
        }}, 450);
      }}
    }} catch(err) {{
      console.error("syncToStreamlit error:", err);
    }}
  }}

  // ── Mathematical Coordinate Transformations ──
  function screenToWorld(clientX, clientY) {{
    if (!bboxInfo || !bboxInfo.xlim || !planImg) return null;
    const imgRect = planImg.getBoundingClientRect();
    if (imgRect.width <= 0 || imgRect.height <= 0) return null;

    const imgX = clientX - imgRect.left;
    const imgY = clientY - imgRect.top;
    const u = imgX / imgRect.width;
    const v = 1.0 - (imgY / imgRect.height);

    const xSpan = bboxInfo.xlim[1] - bboxInfo.xlim[0];
    const ySpan = bboxInfo.ylim[1] - bboxInfo.ylim[0];
    const axW = bboxInfo.x1 - bboxInfo.x0;
    const axH = bboxInfo.y1 - bboxInfo.y0;

    const worldX = bboxInfo.xlim[0] + ((u - bboxInfo.x0) / axW) * xSpan;
    const worldY = bboxInfo.ylim[0] + ((v - bboxInfo.y0) / axH) * ySpan;
    return {{ x: worldX, y: worldY }};
  }}

  function getBoxWorldBounds(cLeft, cTop, cWidth, cHeight) {{
    const p1 = screenToWorld(cLeft, cTop);
    const p2 = screenToWorld(cLeft + cWidth, cTop + cHeight);
    if (!p1 || !p2) return null;
    return {{
      xmin: Math.min(p1.x, p2.x),
      xmax: Math.max(p1.x, p2.x),
      ymin: Math.min(p1.y, p2.y),
      ymax: Math.max(p1.y, p2.y)
    }};
  }}

  function findIntersectionInBox(bounds) {{
    if (!bboxInfo || !bboxInfo.xs || !bboxInfo.ys) return null;
    const candidates = [];
    for (let i = 0; i < bboxInfo.xs.length; i++) {{
      const x = bboxInfo.xs[i];
      if (x >= bounds.xmin && x <= bounds.xmax) {{
        for (let j = 0; j < bboxInfo.ys.length; j++) {{
          const y = bboxInfo.ys[j];
          if (y >= bounds.ymin && y <= bounds.ymax) {{
            candidates.push({{ i: i, j: j, x: x, y: y }});
          }}
        }}
      }}
    }}
    if (candidates.length === 0) {{
      // Expanded search tolerance (+/- 0.45m)
      const expXmin = bounds.xmin - 0.45;
      const expXmax = bounds.xmax + 0.45;
      const expYmin = bounds.ymin - 0.45;
      const expYmax = bounds.ymax + 0.45;
      for (let i = 0; i < bboxInfo.xs.length; i++) {{
        const x = bboxInfo.xs[i];
        if (x >= expXmin && x <= expXmax) {{
          for (let j = 0; j < bboxInfo.ys.length; j++) {{
            const y = bboxInfo.ys[j];
            if (y >= expYmin && y <= expYmax) {{
              candidates.push({{ i: i, j: j, x: x, y: y }});
            }}
          }}
        }}
      }}
    }}
    if (candidates.length === 0) return null;
    if (candidates.length === 1) return candidates[0];
    const cx = (bounds.xmin + bounds.xmax) / 2.0;
    const cy = (bounds.ymin + bounds.ymax) / 2.0;
    candidates.sort((a, b) => Math.hypot(a.x - cx, a.y - cy) - Math.hypot(b.x - cx, b.y - cy));
    return candidates[0];
  }}

  function findClosestIntersection(wx, wy, maxDist) {{
    if (!bboxInfo || !bboxInfo.xs || !bboxInfo.ys) return null;
    let best = null;
    let minDist = maxDist || 0.65;
    for (let i = 0; i < bboxInfo.xs.length; i++) {{
      for (let j = 0; j < bboxInfo.ys.length; j++) {{
        const d = Math.hypot(bboxInfo.xs[i] - wx, bboxInfo.ys[j] - wy);
        if (d < minDist) {{
          minDist = d;
          best = {{ i: i, j: j, x: bboxInfo.xs[i], y: bboxInfo.ys[j] }};
        }}
      }}
    }}
    return best;
  }}

  function distToWallSegment(px, py, x1, y1, x2, y2) {{
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return Math.hypot(px - x1, py - y1);
    let t = ((px - x1) * dx + (py - y1) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    const projX = x1 + t * dx;
    const projY = y1 + t * dy;
    return Math.hypot(px - projX, py - projY);
  }}

  function findWallInBox(bounds) {{
    if (!bboxInfo || !bboxInfo.walls) return null;
    const candidates = [];
    const bCx = (bounds.xmin + bounds.xmax) / 2.0;
    const bCy = (bounds.ymin + bounds.ymax) / 2.0;

    for (let idx = 0; idx < bboxInfo.walls.length; idx++) {{
      const w = bboxInfo.walls[idx];
      if (w.removed) continue;
      const wxMin = Math.min(w.x1, w.x2);
      const wxMax = Math.max(w.x1, w.x2);
      const wyMin = Math.min(w.y1, w.y2);
      const wyMax = Math.max(w.y1, w.y2);

      const mx = (w.x1 + w.x2) / 2.0;
      const my = (w.y1 + w.y2) / 2.0;

      // 1. Both endpoints inside box
      const fullyInside = (wxMin >= bounds.xmin && wxMax <= bounds.xmax && wyMin >= bounds.ymin && wyMax <= bounds.ymax);

      // 2. Midpoint inside box
      const midInside = (mx >= bounds.xmin && mx <= bounds.xmax && my >= bounds.ymin && my <= bounds.ymax);

      // 3. Segment intersects box
      let intersects = false;
      if (w.is_h) {{
        const y = w.y1;
        if (y >= bounds.ymin && y <= bounds.ymax) {{
          if (!(wxMax < bounds.xmin || wxMin > bounds.xmax)) {{
            intersects = true;
          }}
        }}
      }} else {{
        const x = w.x1;
        if (x >= bounds.xmin && x <= bounds.xmax) {{
          if (!(wyMax < bounds.ymin || wyMin > bounds.ymax)) {{
            intersects = true;
          }}
        }}
      }}

      const dMid = Math.hypot(mx - bCx, my - bCy);
      if (fullyInside) {{
        candidates.push({{ wall: w, priority: 1, dist: dMid }});
      }} else if (midInside) {{
        candidates.push({{ wall: w, priority: 2, dist: dMid }});
      }} else if (intersects) {{
        candidates.push({{ wall: w, priority: 3, dist: dMid }});
      }}
    }}

    if (candidates.length === 0) return null;
    candidates.sort((a, b) => {{
      if (a.priority !== b.priority) return a.priority - b.priority;
      return a.dist - b.dist;
    }});
    return candidates[0].wall;
  }}

  function findClosestWall(wx, wy, maxDist) {{
    if (!bboxInfo || !bboxInfo.walls) return null;
    let best = null;
    let minDist = maxDist || 0.65;
    for (let idx = 0; idx < bboxInfo.walls.length; idx++) {{
      const w = bboxInfo.walls[idx];
      if (w.removed) continue;
      const d = distToWallSegment(wx, wy, w.x1, w.y1, w.x2, w.y2);
      if (d < minDist) {{
        minDist = d;
        best = w;
      }}
    }}
    return best;
  }}

  function findAllIntersectionsInBox(bounds) {{
    if (!bboxInfo || !bboxInfo.xs || !bboxInfo.ys) return [];
    const list = [];
    for (let i = 0; i < bboxInfo.xs.length; i++) {{
      const x = bboxInfo.xs[i];
      if (x >= bounds.xmin - 0.35 && x <= bounds.xmax + 0.35) {{
        for (let j = 0; j < bboxInfo.ys.length; j++) {{
          const y = bboxInfo.ys[j];
          if (y >= bounds.ymin - 0.35 && y <= bounds.ymax + 0.35) {{
            list.push({{ i: i, j: j, x: x, y: y }});
          }}
        }}
      }}
    }}
    return list;
  }}

  // ── Mouse & Interaction Handlers ──
  viewport.addEventListener('mousedown', function(e) {{
    if (e.target.closest('.cad-toolbar') || e.target.closest('#box-mode-banner')) return;

    if (currentBoxMode) {{
      isBoxSelecting = true;
      isDragging = false;
      const vRect = viewport.getBoundingClientRect();
      boxStartX = e.clientX;
      boxStartY = e.clientY;
      const left = boxStartX - vRect.left;
      const top = boxStartY - vRect.top;
      selBox.style.left = left + 'px';
      selBox.style.top = top + 'px';
      selBox.style.width = '0px';
      selBox.style.height = '0px';
      selBox.style.display = 'block';
      if (currentBoxMode === 'delete_wall') {{
        selBadge.textContent = 'اسحب لتحديد الحائط المراد حذفه...';
        selBadge.style.background = '#dc2626';
      }} else if (currentBoxMode === 'add_wall') {{
        selBadge.textContent = 'اسحب لتحديد بداية ونهاية الحائط...';
        selBadge.style.background = '#d97706';
      }} else if (currentBoxMode === 'add_window') {{
        selBadge.textContent = 'اختر الحائط لإسقاط الشباك عليه...';
        selBadge.style.background = '#0284c7';
      }} else if (currentBoxMode === 'add_door') {{
        selBadge.textContent = 'اختر الحائط لإسقاط الباب عليه...';
        selBadge.style.background = '#16a34a';
      }} else {{
        selBadge.textContent = 'اسحب لتحديد تقاطع المحورين...';
        selBadge.style.background = '#0f172a';
      }}
      e.preventDefault();
      return;
    }}

    isDragging = true;
    startX = e.clientX - panX;
    startY = e.clientY - panY;
    viewport.classList.add('panning');
  }});

  window.addEventListener('mousemove', function(e) {{
    if (currentBoxMode && isBoxSelecting) {{
      const vRect = viewport.getBoundingClientRect();
      const curX = e.clientX;
      const curY = e.clientY;
      const left = Math.min(boxStartX, curX) - vRect.left;
      const top = Math.min(boxStartY, curY) - vRect.top;
      const width = Math.abs(curX - boxStartX);
      const height = Math.abs(curY - boxStartY);

      selBox.style.left = left + 'px';
      selBox.style.top = top + 'px';
      selBox.style.width = width + 'px';
      selBox.style.height = height + 'px';

      const bounds = getBoxWorldBounds(Math.min(boxStartX, curX), Math.min(boxStartY, curY), width, height);
      if (bounds) {{
        if (currentBoxMode === 'delete_wall') {{
          const wall = findWallInBox(bounds);
          if (wall) {{
            selBadge.innerHTML = '🗑️ الحائط المحدد: ' + (wall.name || wall.label);
            selBadge.style.background = '#dc2626';
          }} else {{
            selBadge.innerHTML = 'اسحب ليشمل الحائط المراد حذفه';
            selBadge.style.background = '#0f172a';
          }}
        }} else if (currentBoxMode === 'add_window' || currentBoxMode === 'add_door') {{
          const wall = findWallInBox(bounds);
          if (wall) {{
            const icon = (currentBoxMode === 'add_window') ? '🪟' : '🚪';
            selBadge.innerHTML = icon + ' الحائط المحدد: ' + (wall.name || wall.label);
            selBadge.style.background = (currentBoxMode === 'add_window') ? '#0284c7' : '#16a34a';
          }} else {{
            selBadge.innerHTML = 'اسحب أو انقر فوق الحائط المطلوب';
            selBadge.style.background = '#0f172a';
          }}
        }} else if (currentBoxMode === 'add_wall') {{
          const pStart = screenToWorld(boxStartX, boxStartY);
          const pCur = screenToWorld(curX, curY);
          let interStart = pStart ? findClosestIntersection(pStart.x, pStart.y, 1.8) : null;
          let interEnd = pCur ? findClosestIntersection(pCur.x, pCur.y, 1.8) : null;

          if (!interStart || !interEnd || (interStart.i === interEnd.i && interStart.j === interEnd.j)) {{
            const allInBox = findAllIntersectionsInBox(bounds);
            if (allInBox.length >= 2) {{
              const dxBox = bounds.xmax - bounds.xmin;
              const dyBox = bounds.ymax - bounds.ymin;
              if (dxBox >= dyBox) {{
                allInBox.sort((a, b) => a.x - b.x);
                interStart = allInBox[0];
                interEnd = allInBox[allInBox.length - 1];
              }} else {{
                allInBox.sort((a, b) => a.y - b.y);
                interStart = allInBox[0];
                interEnd = allInBox[allInBox.length - 1];
              }}
            }}
          }}

          if (interStart && interEnd && (interStart.i !== interEnd.i || interStart.j !== interEnd.j)) {{
            const dx = Math.abs(interEnd.x - interStart.x);
            const dy = Math.abs(interEnd.y - interStart.y);
            if (dx >= dy) {{
              const sj = interStart.j;
              const i1 = Math.min(interStart.i, interEnd.i);
              const i2 = Math.max(interStart.i, interEnd.i);
              const nBays = Math.max(1, i2 - i1);
              if (nBays > 1) {{
                selBadge.innerHTML = '🧱 إسقاط ' + nBays + ' حوائط منفصلة بين التقاطعات على المحور X' + (sj + 1) + ' (من Y' + (i1 + 1) + ' إلى Y' + (i2 + 1) + ')';
              }} else {{
                selBadge.innerHTML = '🧱 إسقاط حائط بين تقاطعين متجاورين على المحور X' + (sj + 1) + ' (Y' + (i1 + 1) + ' ⟷ Y' + (i2 + 1) + ')';
              }}
              selBadge.style.background = '#d97706';
            }} else {{
              const si = interStart.i;
              const j1 = Math.min(interStart.j, interEnd.j);
              const j2 = Math.max(interStart.j, interEnd.j);
              const nBays = Math.max(1, j2 - j1);
              if (nBays > 1) {{
                selBadge.innerHTML = '🧱 إسقاط ' + nBays + ' حوائط منفصلة بين التقاطعات على المحور Y' + (si + 1) + ' (من X' + (j1 + 1) + ' إلى X' + (j2 + 1) + ')';
              }} else {{
                selBadge.innerHTML = '🧱 إسقاط حائط بين تقاطعين متجاورين على المحور Y' + (si + 1) + ' (X' + (j1 + 1) + ' ⟷ X' + (j2 + 1) + ')';
              }}
              selBadge.style.background = '#d97706';
            }}
          }} else {{
            selBadge.innerHTML = 'اسحب لتغطية بداية ونهاية الحائط...';
            selBadge.style.background = '#0f172a';
          }}
        }} else {{
          const inter = findIntersectionInBox(bounds);
          if (inter) {{
            selBadge.innerHTML = '📍 تقاطع المحاور: Y' + (inter.i + 1) + ' × X' + (inter.j + 1);
            selBadge.style.background = (currentBoxMode === 'add') ? '#0284c7' : '#059669';
          }} else {{
            selBadge.innerHTML = 'اسحب ليشمل تقاطع المحورين';
            selBadge.style.background = '#0f172a';
          }}
        }}
      }}
      e.preventDefault();
      return;
    }}

    if (!isDragging) return;
    panX = e.clientX - startX;
    panY = e.clientY - startY;
    updateTransform();
  }});

  window.addEventListener('mouseup', function(e) {{
    if (currentBoxMode && isBoxSelecting) {{
      isBoxSelecting = false;
      selBox.style.display = 'none';

      const curX = e.clientX;
      const curY = e.clientY;
      const minX = Math.min(boxStartX, curX);
      const minY = Math.min(boxStartY, curY);
      const width = Math.abs(curX - boxStartX);
      const height = Math.abs(curY - boxStartY);

      if (currentBoxMode === 'delete_wall' || currentBoxMode === 'add_window' || currentBoxMode === 'add_door') {{
        let wall = null;
        if (width >= 4 || height >= 4) {{
          const bounds = getBoxWorldBounds(minX, minY, Math.max(width, 10), Math.max(height, 10));
          if (bounds) {{
            wall = findWallInBox(bounds);
          }}
        }}
        if (!wall) {{
          const pt = screenToWorld(boxStartX, boxStartY);
          if (pt) {{
            wall = findClosestWall(pt.x, pt.y, 0.65);
          }}
        }}
        if (wall) {{
          let act = 'select_delete_wall_box';
          if (currentBoxMode === 'add_window') act = 'add_window_box';
          else if (currentBoxMode === 'add_door') act = 'add_door_box';
          syncToStreamlit({{
            action: act,
            wk: wall.wk,
            name: wall.name,
            label: wall.label,
            mode: currentBoxMode,
            ts: Date.now()
          }});
        }}
      }} else if (currentBoxMode === 'add_wall') {{
        let p1 = null;
        let p2 = null;
        const pStart = screenToWorld(boxStartX, boxStartY);
        const pEnd = screenToWorld(curX, curY);

        let interStart = pStart ? findClosestIntersection(pStart.x, pStart.y, 1.8) : null;
        let interEnd = pEnd ? findClosestIntersection(pEnd.x, pEnd.y, 1.8) : null;

        if (width >= 6 || height >= 6) {{
          const bounds = getBoxWorldBounds(minX, minY, Math.max(width, 10), Math.max(height, 10));
          if (bounds) {{
            const allInBox = findAllIntersectionsInBox(bounds);
            if (allInBox.length >= 2) {{
              const dxBox = bounds.xmax - bounds.xmin;
              const dyBox = bounds.ymax - bounds.ymin;
              if (dxBox >= dyBox) {{
                allInBox.sort((a, b) => a.x - b.x);
                interStart = allInBox[0];
                interEnd = allInBox[allInBox.length - 1];
              }} else {{
                allInBox.sort((a, b) => a.y - b.y);
                interStart = allInBox[0];
                interEnd = allInBox[allInBox.length - 1];
              }}
            }}
          }}
        }}

        if (interStart && interEnd && (interStart.i !== interEnd.i || interStart.j !== interEnd.j)) {{
          const dx = Math.abs(interEnd.x - interStart.x);
          const dy = Math.abs(interEnd.y - interStart.y);
          if (dx >= dy) {{
            p1 = [interStart.i, interStart.j];
            p2 = [interEnd.i, interStart.j];
          }} else {{
            p1 = [interStart.i, interStart.j];
            p2 = [interStart.i, interEnd.j];
          }}
        }} else if (pStart) {{
          let bestSpan = null;
          let minDist = 0.8;
          for (let j = 0; j < bboxInfo.ys.length; j++) {{
            const y = bboxInfo.ys[j];
            if (Math.abs(pStart.y - y) < 0.6) {{
              for (let i = 0; i < bboxInfo.xs.length - 1; i++) {{
                const x1 = bboxInfo.xs[i];
                const x2 = bboxInfo.xs[i + 1];
                if (pStart.x >= Math.min(x1, x2) - 0.2 && pStart.x <= Math.max(x1, x2) + 0.2) {{
                  const d = Math.abs(pStart.y - y);
                  if (d < minDist) {{
                    minDist = d;
                    bestSpan = {{ p1: [i, j], p2: [i + 1, j] }};
                  }}
                }}
              }}
            }}
          }}
          for (let i = 0; i < bboxInfo.xs.length; i++) {{
            const x = bboxInfo.xs[i];
            if (Math.abs(pStart.x - x) < 0.6) {{
              for (let j = 0; j < bboxInfo.ys.length - 1; j++) {{
                const y1 = bboxInfo.ys[j];
                const y2 = bboxInfo.ys[j + 1];
                if (pStart.y >= Math.min(y1, y2) - 0.2 && pStart.y <= Math.max(y1, y2) + 0.2) {{
                  const d = Math.abs(pStart.x - x);
                  if (d < minDist) {{
                    minDist = d;
                    bestSpan = {{ p1: [i, j], p2: [i, j + 1] }};
                  }}
                }}
              }}
            }}
          }}
          if (bestSpan) {{
            p1 = bestSpan.p1;
            p2 = bestSpan.p2;
          }}
        }}

        if (p1 && p2) {{
          syncToStreamlit({{
            action: 'add_wall_box',
            p1: p1,
            p2: p2,
            mode: 'add_wall',
            ts: Date.now()
          }});
        }}
      }} else {{
        if (width >= 4 || height >= 4) {{
          const bounds = getBoxWorldBounds(minX, minY, Math.max(width, 10), Math.max(height, 10));
          if (bounds) {{
            const inter = findIntersectionInBox(bounds);
            syncToStreamlit({{
              action: (currentBoxMode === 'add') ? 'add_column_box' : 'restore_column_box',
              box: [bounds.xmin, bounds.xmax, bounds.ymin, bounds.ymax],
              grid_i: inter ? inter.i : null,
              grid_j: inter ? inter.j : null,
              mode: currentBoxMode,
              ts: Date.now()
            }});
          }}
        }} else {{
          // Single click tolerance: find closest intersection within 0.85m
          const pt = screenToWorld(boxStartX, boxStartY);
          if (pt) {{
            const inter = findClosestIntersection(pt.x, pt.y, 0.85);
            if (inter) {{
              syncToStreamlit({{
                action: (currentBoxMode === 'add') ? 'add_column_box' : 'restore_column_box',
                box: [pt.x - 0.5, pt.x + 0.5, pt.y - 0.5, pt.y + 0.5],
                grid_i: inter.i,
                grid_j: inter.j,
                mode: currentBoxMode,
                ts: Date.now()
              }});
            }}
          }}
        }}
      }}
      e.preventDefault();
      return;
    }}

    if (isDragging) {{
      isDragging = false;
      viewport.classList.remove('panning');
    }}
  }});

  // Keyboard Shortcuts (Esc to exit, Ctrl + Alt + F for Floating Plan)
  window.addEventListener('keydown', function(e) {{
    if (!e) return;
    var codeMatches = (e.code === 'KeyF');
    var keyMatches = (e.key === 'f' || e.key === 'F' || e.key === 'ب' || e.key === 'B' || e.key === 'ـ' || e.key === '[' || e.key === ']' || e.keyCode === 70 || e.which === 70);
    var isF = codeMatches || keyMatches;
    var hasAlt = e.altKey || (e.getModifierState && e.getModifierState('Alt'));
    var hasCtrl = e.ctrlKey || e.metaKey || (e.getModifierState && e.getModifierState('Control'));
    var hasAltGr = (e.getModifierState && e.getModifierState('AltGraph'));
    var isToggleShortcut = isF && ((hasCtrl && hasAlt) || hasAltGr || (hasCtrl && e.shiftKey));

    if (isToggleShortcut) {{
      e.preventDefault();
      e.stopPropagation();
      try {{
        var pWin = (window.parent && window.parent.document) ? window.parent : window;
        if (pWin.m15ToggleFloatingPlan) pWin.m15ToggleFloatingPlan();
        else if (pWin.m12ToggleFloatingPlan) pWin.m12ToggleFloatingPlan();
      }} catch(err) {{}}
      return false;
    }}

    if ((e.key === 'Escape' || e.keyCode === 27) && currentBoxMode) {{
      syncToStreamlit({{ action: 'exit_box_mode', ts: Date.now() }});
    }}
  }});

  if (exitBtn) {{
    exitBtn.addEventListener('click', function(e) {{
      e.stopPropagation();
      syncToStreamlit({{ action: 'exit_box_mode', ts: Date.now() }});
    }});
  }}

  viewport.addEventListener('wheel', function(e) {{
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 0.87;
    applyZoom(factor, e.clientX, e.clientY);
  }}, {{ passive: false }});

  viewport.addEventListener('dblclick', function(e) {{
    if (e.target.closest('.cad-toolbar') || e.target.closest('#box-mode-banner')) return;
    applyZoom(1.4, e.clientX, e.clientY);
  }});

  let touchStartDist = 0;
  let touchInitialScale = 1.0;
  let touchStartX = 0;
  let touchStartY = 0;

  viewport.addEventListener('touchstart', function(e) {{
    if (e.target.closest('.cad-toolbar') || e.target.closest('#box-mode-banner')) return;
    if (e.touches.length === 1) {{
      isDragging = true;
      touchStartX = e.touches[0].clientX - panX;
      touchStartY = e.touches[0].clientY - panY;
    }} else if (e.touches.length === 2) {{
      isDragging = false;
      touchStartDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      touchInitialScale = scale;
    }}
  }}, {{ passive: false }});

  viewport.addEventListener('touchmove', function(e) {{
    if (e.touches.length === 1 && isDragging) {{
      e.preventDefault();
      panX = e.touches[0].clientX - touchStartX;
      panY = e.touches[0].clientY - touchStartY;
      updateTransform();
    }} else if (e.touches.length === 2 && touchStartDist > 0) {{
      e.preventDefault();
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      const factor = dist / touchStartDist;
      scale = Math.min(Math.max(touchInitialScale * factor, 0.3), 8.0);
      updateTransform();
    }}
  }}, {{ passive: false }});

  viewport.addEventListener('touchend', function() {{
    isDragging = false;
    touchStartDist = 0;
  }});

  const cleanSrc = "{b64_clean or ''}";
  const switchMs = {int(rem_ms) if rem_ms else 0};
  if (switchMs > 0 && cleanSrc.length > 20) {{
    setTimeout(function() {{
      const pimg = document.getElementById('plan-img');
      if (pimg) {{
        pimg.src = 'data:image/png;base64,' + cleanSrc;
      }}
      const dbtn = document.getElementById('btn-download');
      if (dbtn) {{
        dbtn.href = 'data:image/png;base64,' + cleanSrc;
      }}
      try {{
        if (window.parent && window.parent.document) {{
          var pb = window.parent.document.getElementById('m15_dim_banner_container');
          if (pb) {{
            pb.style.opacity = '0';
            pb.style.transform = 'translateY(-6px)';
            setTimeout(function() {{ pb.style.display = 'none'; }}, 400);
          }}
        }}
      }} catch(e) {{}}
    }}, switchMs);
  }}
}})();
</script>
</body>
</html>"""

    components.html(html_content, height=viewer_h, scrolling=False)


def _compute_survey(len_mode=None):
    removed_walls = st.session_state.get("m15_wall_removed", set())
    default_h = float(st.session_state.get("m15_default_wall_height", 3.0))
    if len_mode is None:
        len_mode = st.session_state.get("m15_masonry_len_mode", "clear")
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    rows_12 = []
    rows_25 = []

    brick_size_v = st.session_state.get("m15_brick_size", "25×12×6")
    mortar_v = float(st.session_state.get("m15_mortar_thickness_cm", 1.0))
    if brick_size_v == _CUSTOM_SIZE_LABEL:
        b_l = float(st.session_state.get("m15_brick_custom_l", 25.0))
        b_w = float(st.session_state.get("m15_brick_custom_w", 12.0))
        b_h = float(st.session_state.get("m15_brick_custom_h", 6.0))
    else:
        b_l, b_w, b_h = _parse_brick_size(brick_size_v)

    for wk in _get_all_walls():
        if wk in removed_walls:
            continue
        thick = _get_wall_thickness(wk)
        axis_len = _wall_length_m(wk)
        col1_l, col2_l, _, _, wlen = _get_column_bounds_along_wall(wk)
        clear_len = max(0.0, col2_l - col1_l)
        col_ded = round(axis_len - clear_len, 2)
        calc_len = clear_len if len_mode == "clear" else axis_len
        height = _get_wall_height(wk, default_h)
        gross = calc_len * height

        op = 0.0
        for wi in _get_wall_windows(wk):
            if not wi.get("removed", False):
                op += float(wi.get("w_m", 1.0)) * float(wi.get("h_m", 1.2))
        for di in _get_wall_doors(wk):
            if not di.get("removed", False):
                op += float(di.get("w_m", 0.9)) * float(di.get("h_m", 2.1))

        net = max(0.0, gross - op)
        vol = net * (thick / 100.0)
        i1, j1, i2, j2 = wk
        cs = cm.get((i1, j1), f"({i1+1},{j1+1})")
        ce = cm.get((i2, j2), f"({i2+1},{j2+1})")
        lname = wm.get(wk, "—")
        display = f"{lname}: {cs}\u2192{ce}"
        brick_cnt = _compute_brick_qty(net, thick, b_l, b_w, b_h, mortar_v)

        row = {
            "الحائط": display,
            "طول المحور (م)": round(axis_len, 2),
            "خصم الأعمدة (م)": round(col_ded, 2) if len_mode == "clear" else 0.0,
            "طول المباني الصافي (م)": round(calc_len, 2),
            "الارتفاع (م)": round(height, 2),
            "المساحة الإجمالية (م2)": round(gross, 2),
            "مساحة الفتحات (م2)": round(op, 2),
            "المساحة الصافية (م2)": round(net, 2),
            "حجم الطوب (م3)": round(vol, 2),
            "عدد الطوب (وحدة)": brick_cnt,
        }
        (rows_12 if thick == _WALL_THIN else rows_25).append(row)

    return {"rows_12": rows_12, "rows_25": rows_25, "len_mode": len_mode}


def _totals_row(rows):
    if not rows:
        return {}
    tot = {k: "" for k in rows[0]}
    tot["الحائط"] = "✅ الإجمالي"
    for k in ["طول المحور (م)", "خصم الأعمدة (م)", "طول المباني الصافي (م)", "المساحة الإجمالية (م2)", "مساحة الفتحات (م2)", "المساحة الصافية (م2)", "حجم الطوب (م3)"]:
        if k in rows[0]:
            tot[k] = round(sum(r.get(k, 0) for r in rows), 2)
    if "عدد الطوب (وحدة)" in rows[0]:
        tot["عدد الطوب (وحدة)"] = int(sum(r.get("عدد الطوب (وحدة)", 0) for r in rows))
    return tot


def _compute_brick_qty(net_area_m2, wall_thick_cm, brick_l, brick_w, brick_h, mortar_cm):
    """
    حساب عدد وحدات الطوب للمساحة الصافية (م²) مع مراعاة فاصل المونة وسُمك الحائط.
    BOQ فقط — لا يُستخدم في الحسابات الإنشائية.
    net_area_m2: المساحة الصافية بالمتر المربع
    wall_thick_cm: سمك الحائط بالسنتيمتر (12 أو 25)
    brick_l, brick_w, brick_h: أبعاد الطوبة بالسنتيمتر
    mortar_cm: سمك فاصل المونة بالسنتيمتر
    """
    if net_area_m2 <= 0 or brick_l <= 0 or brick_h <= 0:
        return 0
    # عدد الطوب في الصف الواحد (اتجاه الطول لكل متر طولي)
    units_per_row = 100.0 / (brick_l + mortar_cm)
    # عدد الصفوف في اتجاه الارتفاع (لكل متر ارتفاع)
    rows_per_m = 100.0 / (brick_h + mortar_cm)
    # عدد طبقات/صفوف البناء في اتجاه سمك الحائط (نصف طوبة = 1، طوبة كاملة = 2)
    layers = max(1, round(wall_thick_cm / brick_w)) if brick_w > 0 else 1
    # عدد الوحدات لكل متر مربع مسطح من الحائط
    units_per_m2 = units_per_row * rows_per_m * layers
    return math.ceil(net_area_m2 * units_per_m2)



def _section_brick_type():
    """
    قسم اختيار نوع ومقاس الطوب وسمك فاصل المونة.
    هذا القسم مخصص فقط لحصر كميات الطوب (BOQ).
    لا يُستخدم في الحسابات الإنشائية أو الأحمال.
    """

    # ── 1. نوع الطوب ──────────────────────────────────────────────────
    cur_brick_type = st.session_state.get("m15_brick_type", _BRICK_TYPES[0])
    if cur_brick_type not in _BRICK_TYPES:
        cur_brick_type = _BRICK_TYPES[0]

    new_brick_type = st.selectbox(
        "🧱 نوع الطوب (Brick Type)",
        options=_BRICK_TYPES,
        index=_BRICK_TYPES.index(cur_brick_type),
        key="m15_brick_type_sel"
    )
    if new_brick_type != st.session_state.get("m15_brick_type"):
        st.session_state["m15_brick_type"] = new_brick_type
        # إعادة ضبط المقاس للقيمة الأولى في النوع الجديد
        st.session_state["m15_brick_size"] = _BRICK_SIZES[new_brick_type][0]
        save_settings()
        st.rerun()

    # ── 2. مقاس الطوب (مرتبط بنوع الطوب) ──────────────────────────
    available_sizes = _BRICK_SIZES.get(st.session_state["m15_brick_type"], [])
    cur_brick_size = st.session_state.get("m15_brick_size", available_sizes[0] if available_sizes else "")
    if cur_brick_size not in available_sizes:
        cur_brick_size = available_sizes[0] if available_sizes else ""

    new_brick_size = st.selectbox(
        "📐 مقاس الطوب (Brick Size) — طول×عرض×ارتفاع (سم)",
        options=available_sizes,
        index=available_sizes.index(cur_brick_size) if cur_brick_size in available_sizes else 0,
        key="m15_brick_size_sel"
    )
    if new_brick_size != st.session_state.get("m15_brick_size"):
        st.session_state["m15_brick_size"] = new_brick_size
        save_settings()

    # ── 3. مقاس مخصص ────────────────────────────────────────────────
    if st.session_state.get("m15_brick_size") == _CUSTOM_SIZE_LABEL:
        st.markdown("<span style='font-size:0.88rem;color:#ffffff;font-weight:bold;'>🔧 إدخال مقاس مخصص (سم):</span>", unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns(3)
        new_cl = cc1.number_input("الطول (L)", min_value=5.0, max_value=200.0,
                                   value=float(st.session_state.get("m15_brick_custom_l", 25.0)),
                                   step=0.5, format="%.1f", key="m15_brick_cl")
        new_cw = cc2.number_input("العرض (W)", min_value=5.0, max_value=100.0,
                                   value=float(st.session_state.get("m15_brick_custom_w", 12.0)),
                                   step=0.5, format="%.1f", key="m15_brick_cw")
        new_ch = cc3.number_input("الارتفاع (H)", min_value=2.0, max_value=50.0,
                                   value=float(st.session_state.get("m15_brick_custom_h", 6.0)),
                                   step=0.5, format="%.1f", key="m15_brick_ch")
        changed = False
        if abs(new_cl - st.session_state.get("m15_brick_custom_l", 25.0)) > 0.01: st.session_state["m15_brick_custom_l"] = new_cl; changed = True
        if abs(new_cw - st.session_state.get("m15_brick_custom_w", 12.0)) > 0.01: st.session_state["m15_brick_custom_w"] = new_cw; changed = True
        if abs(new_ch - st.session_state.get("m15_brick_custom_h", 6.0)) > 0.01:  st.session_state["m15_brick_custom_h"] = new_ch; changed = True
        if changed: save_settings()

    # ── 4. سمك فاصل المونة ───────────────────────────────────────────
    st.markdown("<span style='font-size:0.88rem;color:#555;'>━━━━━━━━━━━━━━━━━━━━━━━━━━</span>", unsafe_allow_html=True)
    cur_mortar = float(st.session_state.get("m15_mortar_thickness_cm", 1.0))
    new_mortar = st.number_input(
        "🔩 سمك فاصل المونة (سم) — القيمة الافتراضية 1.0 سم",
        min_value=0.3, max_value=3.0, value=cur_mortar, step=0.1, format="%.1f",
        key="m15_mortar_input",
        help="متوسط سمك فاصل المونة بين وحدات الطوب المتجاورة. لا يُضاف للأبعاد الفعلية للطوبة."
    )
    if abs(new_mortar - cur_mortar) > 0.01:
        st.session_state["m15_mortar_thickness_cm"] = new_mortar
        save_settings()

    # ── 5. عرض معلومات المقاس الحالي ─────────────────────────────────
    brick_type_v = st.session_state.get("m15_brick_type", "")
    brick_size_v = st.session_state.get("m15_brick_size", "")
    mortar_v = float(st.session_state.get("m15_mortar_thickness_cm", 1.0))
    if brick_size_v == _CUSTOM_SIZE_LABEL:
        bl = st.session_state.get("m15_brick_custom_l", 25.0)
        bw = st.session_state.get("m15_brick_custom_w", 12.0)
        bh = st.session_state.get("m15_brick_custom_h", 6.0)
        size_display = f"{bl}×{bw}×{bh} سم (مخصص)"
    else:
        size_display = f"{brick_size_v} سم"
        bl, bw, bh = _parse_brick_size(brick_size_v)
    # حساب عدد وحدات تقريبي لكل م²
    upm2 = (100.0 / (bl + mortar_v)) * (100.0 / (bh + mortar_v)) if bl > 0 and bh > 0 else 0
    st.markdown(
        f"""<div dir='rtl' style='background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1.5px solid #10b981; border-radius: 8px; padding: 12px 16px; margin-top: 10px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);'>
            <div style='display:flex; align-items:center; gap:8px; font-weight:bold; font-size:0.95rem; color:#34d399; margin-bottom:8px;'>
                <span>📊</span>
                <span>ملخص مواصفات الطوب المختار:</span>
            </div>
            <div style='font-size:0.88rem; color:#cbd5e1; line-height:1.8;'>
                النوع: <b style='color:#60a5fa;'>{brick_type_v}</b> &nbsp;|&nbsp; 
                المقاس: <b style='color:#fbbf24;'>{size_display}</b> &nbsp;|&nbsp; 
                فاصل المونة: <b style='color:#a78bfa;'>{mortar_v} سم</b>
            </div>
            <div style='margin-top:8px; padding-top:8px; border-top:1px solid #334155; font-size:0.88rem; color:#cbd5e1;'>
                عدد الطوب التقريبي لكل 1 م² (وجه الحائط): 
                <b style='color:#4ade80; font-size:1.05rem; margin-right:4px;'>≈ {upm2:.1f} وحدة</b>
            </div>
        </div>""",
        unsafe_allow_html=True
    )


def _section_opening_types():
    """
    قسم تعريف نماذج الشبابيك والأبواب (Window/Door Types):
    - تعريف أبعاد كل نموذج شباك (W1، W2...) مع الجلسة Sill.
    - تعريف أبعاد كل نموذج باب (D1، D2...).
    - الإسقاط الفعلي يتم في قسمي 'إسقاط الشبابيك' و 'إسقاط الأبواب'.
    """
    tab_w, tab_d = st.tabs(["🪟 نماذج الشبابيك (Window Types)", "🚪 نماذج الأبواب (Door Types)"])

    # ── تبويبة نماذج الشبابيك ──────────────────────────────────────────────
    with tab_w:
        win_types = st.session_state.get("m15_window_types", [])
        if not win_types:
            win_types = [{"id": "wt_1", "label": "W1", "w_cm": 100.0, "h_cm": 120.0, "sill_cm": 90.0}]
            st.session_state["m15_window_types"] = win_types

        n_win_types = st.number_input(
            "عدد نماذج الشبابيك المطلوب تعريفها:",
            min_value=1, max_value=20, value=max(1, len(win_types)), step=1,
            key="m15_n_win_types"
        )
        n_win_types = int(n_win_types)

        while len(win_types) < n_win_types:
            n = len(win_types) + 1
            win_types.append({"id": f"wt_{n}", "label": f"W{n}", "w_cm": 100.0, "h_cm": 120.0, "sill_cm": 90.0})
        while len(win_types) > n_win_types:
            win_types.pop()

        changed_wt = False
        for i, wt in enumerate(win_types):
            lbl = wt.get("label", f"W{i+1}")
            with st.expander(f"🪟 نموذج {lbl}", expanded=(len(win_types) <= 3)):
                wc1, wc2, wc3 = st.columns(3)
                new_wl = wc1.number_input(f"عرض الشباك (سم) — {lbl}:", min_value=20.0, max_value=500.0,
                                           value=float(wt.get("w_cm", 100.0)), step=5.0, format="%.0f",
                                           key=f"m15_wt_w_{i}")
                new_wh = wc2.number_input(f"ارتفاع الشباك (سم) — {lbl}:", min_value=20.0, max_value=400.0,
                                           value=float(wt.get("h_cm", 120.0)), step=5.0, format="%.0f",
                                           key=f"m15_wt_h_{i}")
                new_ws = wc3.number_input(f"ارتفاع جلسة الشباك Sill (سم) — {lbl}:", min_value=0.0, max_value=300.0,
                                           value=float(wt.get("sill_cm", 90.0)), step=5.0, format="%.0f",
                                           key=f"m15_wt_sill_{i}")
                if abs(new_wl - wt.get("w_cm", 100.0)) > 0.1 or abs(new_wh - wt.get("h_cm", 120.0)) > 0.1 or abs(new_ws - wt.get("sill_cm", 90.0)) > 0.1:
                    wt["w_cm"] = new_wl; wt["h_cm"] = new_wh; wt["sill_cm"] = new_ws
                    changed_wt = True
                st.caption(f"📐 {lbl}: {new_wl:.0f}×{new_wh:.0f}سم | جلسة: {new_ws:.0f}سم ({new_wl/100:.2f}م × {new_wh/100:.2f}م)")

        if changed_wt or win_types != st.session_state.get("m15_window_types", []):
            st.session_state["m15_window_types"] = win_types
            save_settings()

    # ── تبويبة نماذج الأبواب ───────────────────────────────────────────────
    with tab_d:
        door_types = st.session_state.get("m15_door_types", [])
        if not door_types:
            door_types = [{"id": "dt_1", "label": "D1", "w_cm": 90.0, "h_cm": 210.0}]
            st.session_state["m15_door_types"] = door_types

        n_door_types = st.number_input(
            "عدد نماذج الأبواب المطلوب تعريفها:",
            min_value=1, max_value=20, value=max(1, len(door_types)), step=1,
            key="m15_n_door_types"
        )
        n_door_types = int(n_door_types)

        while len(door_types) < n_door_types:
            n = len(door_types) + 1
            door_types.append({"id": f"dt_{n}", "label": f"D{n}", "w_cm": 90.0, "h_cm": 210.0})
        while len(door_types) > n_door_types:
            door_types.pop()

        changed_dt = False
        for i, dt in enumerate(door_types):
            lbl = dt.get("label", f"D{i+1}")
            with st.expander(f"🚪 نموذج {lbl}", expanded=(len(door_types) <= 3)):
                dc1, dc2 = st.columns(2)
                new_dw = dc1.number_input(f"عرض الباب (سم) — {lbl}:", min_value=50.0, max_value=400.0,
                                           value=float(dt.get("w_cm", 90.0)), step=5.0, format="%.0f",
                                           key=f"m15_dt_w_{i}")
                new_dh = dc2.number_input(f"ارتفاع الباب (سم) — {lbl}:", min_value=150.0, max_value=400.0,
                                           value=float(dt.get("h_cm", 210.0)), step=5.0, format="%.0f",
                                           key=f"m15_dt_h_{i}")
                if abs(new_dw - dt.get("w_cm", 90.0)) > 0.1 or abs(new_dh - dt.get("h_cm", 210.0)) > 0.1:
                    dt["w_cm"] = new_dw; dt["h_cm"] = new_dh
                    changed_dt = True
                st.caption(f"📐 {lbl}: {new_dw:.0f}×{new_dh:.0f}سم ({new_dw/100:.2f}م × {new_dh/100:.2f}م)")

        if changed_dt or door_types != st.session_state.get("m15_door_types", []):
            st.session_state["m15_door_types"] = door_types
            save_settings()


def _get_active_interactive_mode():
    """
    إرجاع معلومات النمط التفاعلي النشط حالياً على المسقط الأفقي (إن وجد).
    Return dict: {'key': ..., 'name': ..., 'type': 'إسقاط'|'حذف'|'استعادة'} or None
    """
    modes = [
        {"key": "m15_add_wall_mode", "name": "إسقاط الحوائط", "type": "إسقاط"},
        {"key": "m15_add_col_mode", "name": "إسقاط الأعمدة", "type": "إسقاط"},
        {"key": "m15_add_win_mode", "name": "إسقاط الشبابيك", "type": "إسقاط"},
        {"key": "m15_add_door_mode", "name": "إسقاط الأبواب", "type": "إسقاط"},
        {"key": "m15_del_wall_mode", "name": "حذف الحوائط", "type": "حذف"},
        {"key": "m15_restore_col_mode", "name": "استعادة الأعمدة", "type": "استعادة"},
    ]
    for m in modes:
        if st.session_state.get(m["key"], False):
            return m
    return None


def _close_all_interactive_modes():
    """إغلاق كافة الأنماط التفاعلية دفعة واحدة."""
    st.session_state["m15_add_col_mode"] = False
    st.session_state["m15_restore_col_mode"] = False
    st.session_state["m15_del_wall_mode"] = False
    st.session_state["m15_add_wall_mode"] = False
    st.session_state["m15_add_win_mode"] = False
    st.session_state["m15_add_door_mode"] = False
    st.session_state["m15_pending_delete_wall"] = None
    save_settings()


def _render_mode_conflict_warning(current_op_name, active_mode_info, context_key=""):
    """
    عرض رسالة تحذيرية بعدم إمكانية بدء أو تنفيذ العملية الحالية لوجود نمط تفاعلي نشط آخر،
    مع زر مريح لإنهاء أو إغلاق النمط النشط فوراً.
    """
    active_name = active_mode_info.get("name", "أخرى")
    warning_html = f"""<div style='background:rgba(239, 68, 68, 0.12); border:1.5px solid #ef4444; border-right:4px solid #ef4444; border-radius:8px; padding:12px 14px; margin:10px 0 12px 0;' dir='rtl'>
        <div style='display:flex; align-items:center; gap:8px;'>
            <span style='font-size:1.15rem;'>⚠️</span>
            <span style='color:#f87171; font-weight:800; font-size:0.92rem;'>تنبيه: لا يمكن بدء العملية</span>
        </div>
        <div style='color:#fecaca; font-size:0.87rem; line-height:1.6; margin-top:6px;'>
            لا يمكن بدء عملية <b>{current_op_name}</b> نظراً لأن نمط <b>{active_name}</b> لا يزال نشطاً حالياً على المسقط الأفقي.<br>
            يُرجى إنهاء أو إغلاق نمط <b>{active_name}</b> أولاً لتتمكن من تفعيل {current_op_name}.
        </div>
    </div>"""
    st.markdown(warning_html, unsafe_allow_html=True)
    if st.button(f"⏹️ إغلاق نمط {active_name} الآن", key=f"m15_force_close_active_{context_key}", use_container_width=True):
        _close_all_interactive_modes()
        st.rerun()


def _section_add_walls():
    """
    قسم إسقاط الحوائط على المحاور (Interactive Wall Placement):
    - إسقاط الحوائط بين نقطتي تقاطع محورين (x1, y1) و (x2, y2).
    - الدمج التلقائي للحوائط المتصلة في حالة عدم تواجد أعمدة فاصلة بينها.
    - اختيار سمك الحائط (12 سم أو 25 سم).
    - التحديد التفاعلي بالسحب بالماوس على لوحة المسقط الأفقي.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        st.info("⚠️ أدخل محاور X و Y أولاً في قسم 'شبكة المحاور'.")
        return

    is_add_wall_active = bool(st.session_state.get("m15_add_wall_mode", False))

    st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#ffffff; margin-bottom:10px;'>🧱 إعدادات سمك وارتفاع الحائط المطلوب إسقاطه:</div>", unsafe_allow_html=True)

    c_th, c_h = st.columns(2)
    with c_th:
        thick_choice = st.radio(
            "سمك الحائط المطلوب:",
            options=[12, 25],
            index=0,
            format_func=lambda x: f"{x} سم ({'نصف طوبة' if x == 12 else 'طوبة كاملة'})",
            horizontal=True,
            key="m15_new_wall_thick_choice"
        )
    with c_h:
        cur_h = float(st.session_state.get("m15_new_wall_height_choice", st.session_state.get("m15_default_wall_height", 3.0)))
        wall_h = st.number_input(
            "ارتفاع الحائط (م):",
            min_value=0.5,
            max_value=12.0,
            value=cur_h,
            step=0.1,
            key="m15_new_wall_height_choice"
        )
        st.session_state["m15_default_wall_height"] = wall_h

    st.markdown("<hr style='margin: 12px 0 14px 0; border: none; border-top: 1px dashed #cbd5e1;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.92rem; font-weight:700; color:#ffffff; margin-bottom:10px;'>🎯 إسقاط الحائط بسحب الماوس في المكان المطلوب في المسقط الأفقي:</div>", unsafe_allow_html=True)

    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None and active_mode.get("key") != "m15_add_wall_mode")

    if has_conflict:
        _render_mode_conflict_warning("إسقاط الحوائط", active_mode, context_key="add_walls")
        st.button("🎯 تفعيل إسقاط الحائط بسحب الماوس في المسقط", type="primary", use_container_width=True, key="m15_btn_start_add_wall", disabled=True)
    elif not is_add_wall_active:
        if st.button("🎯 تفعيل إسقاط الحائط بسحب الماوس في المسقط", type="primary", use_container_width=True, key="m15_btn_start_add_wall"):
            _close_all_interactive_modes()
            st.session_state["m15_add_wall_mode"] = True
            st.rerun()
    else:
        if st.button("⏹️ إنهاء وضع إسقاط الحوائط (Esc)", key="m15_btn_exit_add_wall", use_container_width=True):
            st.session_state["m15_add_wall_mode"] = False
            st.rerun()

def _section_axes():
    cxs = st.session_state["m15_x_axes"]
    cys = st.session_state["m15_y_axes"]

    # ═════════════════════════════════════════════════════════════════════════
    # 🔵 Vertical Axes — Y1, Y2, Y3...   (m15_x_axes → خطوط رأسية في المسقط)
    # تُحدد الأبعاد الأفقية (العرض) بين المحاور الرأسية
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"""<div style='display:flex;align-items:center;gap:8px;margin-top:8px;margin-bottom:18px;'>
            <span style='background:#1e40af;color:#ffffff;font-weight:bold;padding:5px 14px;border-radius:6px;font-size:0.95rem;border:1px solid #3b82f6;white-space:nowrap;'>
                🔵 المحاور الرأسية — Y1, Y2, Y3... (الأبعاد الأفقية بين المحاور)
            </span>
        </div>""",
        unsafe_allow_html=True
    )

    cur_nx = len(cxs)
    if "m15_n_v_axes" in st.session_state and st.session_state.get("_m15_synced_nx") != cur_nx:
        st.session_state["m15_n_v_axes"] = cur_nx
        st.session_state["_m15_synced_nx"] = cur_nx

    c_ny1, c_ny2 = st.columns([1.2, 2.8])
    with c_ny1:
        n_y_axes = st.number_input(
            "عدد المحاور الرأسية Y",
            min_value=2,
            max_value=20,
            value=cur_nx,
            step=1,
            key="m15_n_v_axes"
        )
        n_y_axes = int(n_y_axes)
    with c_ny2:
        st.caption("📐 أدخل الأبعاد الأفقية (العرض) بين كل محورين رأسيين متتاليين (م) [المحور الأول Y1 = 0.00م]:")

    # مزامنة مفاتيح الواجهة إذا تم تعديل الإحداثيات من خارج القسم
    if st.session_state.get("_m15_synced_x_axes") != cxs:
        for idx in range(len(cxs) - 1):
            st.session_state[f"m15_x_sp_{idx}"] = float(round(cxs[idx + 1] - cxs[idx], 2))
        st.session_state["_m15_synced_x_axes"] = list(cxs)

    spacings_x = []
    n_spans_x = n_y_axes - 1
    for row_start in range(0, n_spans_x, 3):
        chunk = range(row_start, min(row_start + 3, n_spans_x))
        cols = st.columns(3)
        for ci, idx in enumerate(chunk):
            if idx < len(cxs) - 1:
                dsp = round(cxs[idx + 1] - cxs[idx], 2)
            elif spacings_x:
                dsp = spacings_x[-1]
            else:
                dsp = 4.0
            if f"m15_x_sp_{idx}" not in st.session_state:
                st.session_state[f"m15_x_sp_{idx}"] = float(dsp)
            sp = cols[ci].number_input(
                f"البعد الأفقي Y{idx+1} → Y{idx+2}",
                min_value=0.25,
                max_value=50.0,
                value=float(st.session_state[f"m15_x_sp_{idx}"]),
                step=0.25,
                format="%.2f",
                key=f"m15_x_sp_{idx}"
            )
            spacings_x.append(float(sp))

    # حساب الإحداثيات التراكمية للمحاور الرأسية
    x_vals = [0.0]
    for s in spacings_x:
        x_vals.append(round(x_vals[-1] + s, 3))

    if x_vals != cxs:
        st.session_state["m15_x_axes"] = x_vals
        st.session_state["_m15_synced_x_axes"] = list(x_vals)
        st.session_state["_m15_synced_nx"] = len(x_vals)
        _sanitize_and_prune_grid_data()
        _normalize_wall_keys()
        save_settings()

    # ─────────────────────────────────────────────────────────────────────────
    # فاصل أنيق بين محاور Y الرأسية ومحاور X الأفقية
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("<hr style='margin:18px 0;border:0;border-top:1.5px dashed #cbd5e1;'>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # 🔴 Horizontal Axes — X1, X2, X3...   (m15_y_axes → خطوط أفقية في المسقط)
    # تُحدد الأبعاد الرأسية (العمق) بين المحاور الأفقية
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"""<div style='display:flex;align-items:center;gap:8px;margin-top:10px;margin-bottom:18px;'>
            <span style='background:#fee2e2;color:{_CLR_AXIS_X};font-weight:bold;padding:5px 14px;border-radius:6px;font-size:0.95rem;border:1px solid #fca5a5;white-space:nowrap;'>
                🔴 المحاور الأفقية — X1, X2, X3... (الأبعاد الرأسية بين المحاور)
            </span>
        </div>""",
        unsafe_allow_html=True
    )

    cur_ny = len(cys)
    if "m15_n_h_axes" in st.session_state and st.session_state.get("_m15_synced_ny") != cur_ny:
        st.session_state["m15_n_h_axes"] = cur_ny
        st.session_state["_m15_synced_ny"] = cur_ny

    c_nx1, c_nx2 = st.columns([1.2, 2.8])
    with c_nx1:
        n_x_axes = st.number_input(
            "عدد المحاور الأفقية X",
            min_value=2,
            max_value=20,
            value=cur_ny,
            step=1,
            key="m15_n_h_axes"
        )
        n_x_axes = int(n_x_axes)
    with c_nx2:
        st.caption("📐 أدخل الأبعاد الرأسية (العمق) بين كل محورين أفقيين متتاليين (م) [المحور الأول X1 = 0.00م]:")

    # مزامنة مفاتيح الواجهة إذا تم تعديل الإحداثيات من خارج القسم
    if st.session_state.get("_m15_synced_y_axes") != cys:
        for idx in range(len(cys) - 1):
            st.session_state[f"m15_y_sp_{idx}"] = float(round(cys[idx + 1] - cys[idx], 2))
        st.session_state["_m15_synced_y_axes"] = list(cys)

    spacings_y = []
    n_spans_y = n_x_axes - 1
    for row_start in range(0, n_spans_y, 3):
        chunk = range(row_start, min(row_start + 3, n_spans_y))
        cols = st.columns(3)
        for ci, idx in enumerate(chunk):
            if idx < len(cys) - 1:
                dsp = round(cys[idx + 1] - cys[idx], 2)
            elif spacings_y:
                dsp = spacings_y[-1]
            else:
                dsp = 3.0
            if f"m15_y_sp_{idx}" not in st.session_state:
                st.session_state[f"m15_y_sp_{idx}"] = float(dsp)
            sp = cols[ci].number_input(
                f"البعد الرأسي X{idx+1} → X{idx+2}",
                min_value=0.25,
                max_value=50.0,
                value=float(st.session_state[f"m15_y_sp_{idx}"]),
                step=0.25,
                format="%.2f",
                key=f"m15_y_sp_{idx}"
            )
            spacings_y.append(float(sp))

    # حساب الإحداثيات التراكمية للمحاور الأفقية
    y_vals = [0.0]
    for s in spacings_y:
        y_vals.append(round(y_vals[-1] + s, 3))

    if y_vals != cys:
        st.session_state["m15_y_axes"] = y_vals
        st.session_state["_m15_synced_y_axes"] = list(y_vals)
        st.session_state["_m15_synced_ny"] = len(y_vals)
        _sanitize_and_prune_grid_data()
        _normalize_wall_keys()
        save_settings()

def _confirm_delete_wall(wk):
    """
    تأكيد وحذف الحائط المحدد:
    - إضافة مفتاح الحائط إلى مجموعة الحوائط المحذوفة m15_wall_removed.
    - تصفير الحائط المعلق m15_pending_delete_wall.
    - تحديث كاش صورة المسقط وحفظ الإعدادات.
    - إظهار إشعار تأكيد مع إبقاء إمكانية الاستعادة في أي وقت.
    """
    if not wk or len(wk) != 4:
        return
    wk = tuple(int(x) for x in wk)
    removed_walls = st.session_state.get("m15_wall_removed", set())
    if not isinstance(removed_walls, set):
        removed_walls = set(removed_walls)
    removed_walls.add(wk)
    st.session_state["m15_wall_removed"] = removed_walls
    st.session_state["m15_pending_delete_wall"] = None
    st.session_state.pop("_last_del_confirm_whistle_token", None)
    st.session_state.pop("m15_plan_png_b64", None)
    save_settings()
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    lbl = _wall_display_label(wk, cm, wm)
    st.toast(f"🗑️ تم حذف الحائط ({lbl}) بنجاح! يمكنك استعادته في أي وقت من قسم استعادة الحوائط.", icon="🗑️")
    st.rerun()


def _execute_select_delete_wall_box(data):
    """التقاط الحائط المحدد بواسطة الصندوق وتخزينه كحائط معلق لطلب تأكيد الحذف."""
    wk_raw = data.get("wk")
    if not wk_raw or len(wk_raw) != 4:
        return
    wk = tuple(int(x) for x in wk_raw)
    all_walls = _get_all_walls()
    if wk not in all_walls:
        rev = (wk[2], wk[3], wk[0], wk[1])
        if rev in all_walls:
            wk = rev
        else:
            return

    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    lbl = _wall_display_label(wk, cm, wm)

    st.session_state["m15_pending_delete_wall"] = wk
    st.session_state["m15_del_wall_mode"] = True
    save_settings()
    st.toast(f"🎯 تم تحديد الحائط ({lbl}) — يرجى تأكيد الحذف!", icon="🗑️")
    st.rerun()


def _execute_confirm_delete_wall_box(data):
    """تنفيذ حذف الحائط بعد التأكيد من الصندوق أو النافذة التفاعلية."""
    wk_raw = data.get("wk")
    if not wk_raw and st.session_state.get("m15_pending_delete_wall"):
        wk_raw = st.session_state.get("m15_pending_delete_wall")
    if not wk_raw or len(wk_raw) != 4:
        return
    wk = tuple(int(x) for x in wk_raw)
    _confirm_delete_wall(wk)


def _execute_add_column_box(data):
    """تنفيذ إسقاط ورسم العمود عند التقاطع المحدد بالصندوق وتحديث الحالة فوراً."""
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 1 or len(ys) < 1:
        return

    box = data.get("box", [])
    gi = data.get("grid_i")
    gj = data.get("grid_j")

    target_i = None
    target_j = None

    if gi is not None and gj is not None:
        try:
            gi, gj = int(gi), int(gj)
            if 0 <= gi < len(xs) and 0 <= gj < len(ys):
                target_i, target_j = gi, gj
        except (ValueError, TypeError):
            pass

    if target_i is None or target_j is None:
        if len(box) == 4:
            xmin, xmax, ymin, ymax = box
            candidates = []
            for i, x in enumerate(xs):
                if xmin <= x <= xmax:
                    for j, y in enumerate(ys):
                        if ymin <= y <= ymax:
                            candidates.append((i, j))
            if not candidates:
                for i, x in enumerate(xs):
                    if (xmin - 0.45) <= x <= (xmax + 0.45):
                        for j, y in enumerate(ys):
                            if (ymin - 0.45) <= y <= (ymax + 0.45):
                                candidates.append((i, j))
            if candidates:
                cx = (xmin + xmax) / 2.0
                cy = (ymin + ymax) / 2.0
                candidates.sort(key=lambda item: math.hypot(xs[item[0]] - cx, ys[item[1]] - cy))
                target_i, target_j = candidates[0]

    if target_i is None or target_j is None:
        st.toast("⚠️ لم يتم تحديد تقاطع محاور صحيح داخل حدود الصندوق.", icon="⚠️")
        return

    # التحقق مما إذا كان هناك عمود قائم بالفعل عند هذا التقاطع
    active_cols = _get_active_columns()
    is_existing = (target_i, target_j) in active_cols

    # قراءة إعدادات العمود المحددة من الواجهة
    b_cm = float(st.session_state.get("m15_new_col_b", 25.0))
    t_cm = float(st.session_state.get("m15_new_col_t", 60.0))
    model_name = str(st.session_state.get("m15_new_col_model", f"C({int(b_cm)}x{int(t_cm)})"))
    cur_dirs = st.session_state.get("m15_col_dirs", {})
    cur_shifts = st.session_state.get("m15_col_shifts", {})
    dir_code = cur_dirs.get((target_i, target_j), "NS")
    col_dir_choice = "رأسي" if dir_code == "NS" else "أفقي"
    col_anchor = "السنتر"
    corner_choice = "أعلى اليمين"

    existing_tr = cur_shifts.get((target_i, target_j), {})
    shift_x = existing_tr.get("shift_x", M15_SHIFT_X_OPTIONS[0])
    shift_y = existing_tr.get("shift_y", M15_SHIFT_Y_OPTIONS[0])

    # تحديث مجموعات الأعمدة الموضوعة والمحذوفة
    placed_set = st.session_state.get("m15_col_placed", set())
    if not isinstance(placed_set, set): placed_set = set(placed_set)
    placed_set.add((target_i, target_j))
    st.session_state["m15_col_placed"] = placed_set

    removed_cols = st.session_state.get("m15_col_removed", set())
    if not isinstance(removed_cols, set): removed_cols = set(removed_cols)
    removed_cols.discard((target_i, target_j))
    st.session_state["m15_col_removed"] = removed_cols

    # حفظ الخصائص المستقلة للعمود
    col_props = st.session_state.setdefault("m15_col_props", {})
    col_props[(target_i, target_j)] = {
        "model": model_name,
        "b_cm": b_cm,
        "t_cm": t_cm,
        "dir": col_dir_choice,
        "dir_code": dir_code,
        "anchor": col_anchor,
        "corner": corner_choice,
        "shift_x": shift_x,
        "shift_y": shift_y
    }
    st.session_state["m15_col_props"] = col_props

    col_dirs = st.session_state.setdefault("m15_col_dirs", {})
    col_dirs[(target_i, target_j)] = dir_code
    st.session_state["m15_col_dirs"] = col_dirs

    col_shifts = st.session_state.setdefault("m15_col_shifts", {})
    col_shifts[(target_i, target_j)] = {"shift_x": shift_x, "shift_y": shift_y}
    st.session_state["m15_col_shifts"] = col_shifts

    # حساب الإزاحة الهندسية
    col_w_m = b_cm / 100.0
    col_l_m = t_cm / 100.0
    cw = col_w_m if dir_code == "NS" else col_l_m
    ch = col_l_m if dir_code == "NS" else col_w_m
    dx_m, dy_m = _compute_col_offsets(cw, ch, shift_x, shift_y)
    col_shifted = st.session_state.setdefault("m15_col_shifted", {})
    col_shifted[(target_i, target_j)] = (dx_m * 100.0, dy_m * 100.0)
    st.session_state["m15_col_shifted"] = col_shifted

    # الحفاظ على آخر أبعاد مدخلة كـ default مستمر لباقي الأعمدة
    st.session_state["m15_col_width_cm"] = b_cm
    st.session_state["m15_col_length_cm"] = t_cm
    st.session_state["m15_new_col_b"] = b_cm
    st.session_state["m15_new_col_t"] = t_cm
    st.session_state["m15_new_col_model"] = f"C({int(b_cm)}x{int(t_cm)})"
    st.session_state["_m15_saved_col_b"] = b_cm
    st.session_state["_m15_saved_col_t"] = t_cm
    m15_data = st.session_state.get("module_15_data")
    if isinstance(m15_data, dict):
        m15_data["col_width_cm"] = b_cm
        m15_data["col_length_cm"] = t_cm
        m15_data["new_col_b"] = b_cm
        m15_data["new_col_t"] = t_cm

    if is_existing:
        st.toast(f"🔄 تم تحديث مواصفات العمود {model_name} عند تقاطع Y{target_i+1} × X{target_j+1} بنجاح!", icon="🏗️")
    else:
        st.toast(f"✅ تم إضافة العمود {model_name} عند تقاطع Y{target_i+1} × X{target_j+1} بنجاح!", icon="🏗️")
    st.session_state.pop("m15_plan_png_b64", None)
    save_settings()
    st.session_state["m15_add_col_mode"] = True
    st.rerun()


def _execute_restore_column_box(data):
    """فحص التقاطع المحصور داخل حدود الصندوق واستعادته بكامل خصائصه الأصلية من سجل المحذوفات."""
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 1 or len(ys) < 1:
        return

    box = data.get("box", [])
    gi = data.get("grid_i")
    gj = data.get("grid_j")

    target_i = None
    target_j = None

    if gi is not None and gj is not None:
        try:
            gi, gj = int(gi), int(gj)
            if 0 <= gi < len(xs) and 0 <= gj < len(ys):
                target_i, target_j = gi, gj
        except (ValueError, TypeError):
            pass

    if target_i is None or target_j is None:
        if len(box) == 4:
            xmin, xmax, ymin, ymax = box
            candidates = []
            for i, x in enumerate(xs):
                if xmin <= x <= xmax:
                    for j, y in enumerate(ys):
                        if ymin <= y <= ymax:
                            candidates.append((i, j))
            if not candidates:
                for i, x in enumerate(xs):
                    if (xmin - 0.45) <= x <= (xmax + 0.45):
                        for j, y in enumerate(ys):
                            if (ymin - 0.45) <= y <= (ymax + 0.45):
                                candidates.append((i, j))
            if candidates:
                cx = (xmin + xmax) / 2.0
                cy = (ymin + ymax) / 2.0
                candidates.sort(key=lambda item: math.hypot(xs[item[0]] - cx, ys[item[1]] - cy))
                target_i, target_j = candidates[0]

    if target_i is None or target_j is None:
        st.toast("⚠️ لم يتم تحديد تقاطع محاور داخل حدود الصندوق.", icon="⚠️")
        return

    removed_cols = st.session_state.get("m15_col_removed", set())
    if not isinstance(removed_cols, set):
        removed_cols = set(removed_cols)

    deleted_history = st.session_state.get("m15_deleted_cols_history", {})
    is_deleted = (target_i, target_j) in removed_cols or (target_i, target_j) in deleted_history

    if not is_deleted:
        active_cols = _get_active_columns()
        if (target_i, target_j) in active_cols:
            st.toast(f"ℹ️ العمود عند تقاطع Y{target_i+1} × X{target_j+1} قائم ونشط بالفعل!", icon="ℹ️")
        else:
            st.toast(f"⚠️ لا يوجد عمود محذوف مسجل عند تقاطع Y{target_i+1} × X{target_j+1} لاستعادته!", icon="⚠️")
        return

    # استرجاع الخصائص الأصلية الكاملة من سجل المحذوفات
    hist_props = deleted_history.get((target_i, target_j), {})
    model_name = hist_props.get("model", f"C(Y{target_i+1},X{target_j+1})")
    b_cm = hist_props.get("b_cm", st.session_state.get("m15_col_width_cm", 30.0))
    t_cm = hist_props.get("t_cm", st.session_state.get("m15_col_length_cm", 60.0))
    dir_code = hist_props.get("dir_code", hist_props.get("dir", "NS"))
    if dir_code not in ["NS", "EW"]:
        dir_code = "NS" if dir_code == "رأسي" else "EW"
    shift_x = hist_props.get("shift_x", "متمركز على المحور")
    shift_y = hist_props.get("shift_y", "متمركز على المحور")
    anchor = hist_props.get("anchor", "السنتر")
    corner = hist_props.get("corner", "السنتر")

    placed_set = st.session_state.get("m15_col_placed", set())
    if not isinstance(placed_set, set): placed_set = set(placed_set)
    placed_set.add((target_i, target_j))
    st.session_state["m15_col_placed"] = placed_set

    removed_cols.discard((target_i, target_j))
    st.session_state["m15_col_removed"] = removed_cols

    col_props = st.session_state.setdefault("m15_col_props", {})
    col_props[(target_i, target_j)] = {
        "model": model_name,
        "b_cm": b_cm,
        "t_cm": t_cm,
        "dir": "رأسي" if dir_code == "NS" else "أفقي",
        "dir_code": dir_code,
        "anchor": anchor,
        "corner": corner,
        "shift_x": shift_x,
        "shift_y": shift_y
    }
    st.session_state["m15_col_props"] = col_props

    col_dirs = st.session_state.setdefault("m15_col_dirs", {})
    col_dirs[(target_i, target_j)] = dir_code
    st.session_state["m15_col_dirs"] = col_dirs

    col_shifts = st.session_state.setdefault("m15_col_shifts", {})
    col_shifts[(target_i, target_j)] = {"shift_x": shift_x, "shift_y": shift_y}
    st.session_state["m15_col_shifts"] = col_shifts

    cw = (b_cm / 100.0) if dir_code == "NS" else (t_cm / 100.0)
    ch = (t_cm / 100.0) if dir_code == "NS" else (b_cm / 100.0)
    dx_m, dy_m = _compute_col_offsets(cw, ch, shift_x, shift_y)
    col_shifted = st.session_state.setdefault("m15_col_shifted", {})
    col_shifted[(target_i, target_j)] = (dx_m * 100.0, dy_m * 100.0)
    st.session_state["m15_col_shifted"] = col_shifted

    st.session_state.pop("m15_plan_png_b64", None)
    save_settings()
    st.toast(f"♻️ تم استعادة العمود {model_name} عند تقاطع Y{target_i+1} × X{target_j+1} بنجاح بكامل خصائصه الأصلية!", icon="♻️")
    st.session_state["m15_restore_col_mode"] = True
    st.rerun()


def _execute_add_window_box(data):
    """
    إسقاط شباك تفاعلي بالماوس مباشرة على الحائط المختار:
    - موضع الشباك الافتراضي: منتصف الحائط تماماً (Center to Center).
    - الترقيم التلقائي حسب نموذج الشباك (W1-1, W1-2...).
    - التحقق من المسافة الصافية وخلو الموضع من التعارضات.
    """
    raw_wk = data.get("wk")
    if not raw_wk or len(raw_wk) != 4:
        st.toast("⚠️ لم يتم تحديد حائط صحيح.", icon="⚠️")
        return

    wk = (int(raw_wk[0]), int(raw_wk[1]), int(raw_wk[2]), int(raw_wk[3]))
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    if wk not in all_walls or wk in removed_walls:
        st.toast("⚠️ الحائط المختار غير نشط أو محذوف.", icon="⚠️")
        return

    win_types = st.session_state.get("m15_window_types", [])
    if not win_types:
        win_types = [{"id": "wt_1", "label": "W1", "w_cm": 100.0, "h_cm": 120.0, "sill_cm": 90.0}]
        st.session_state["m15_window_types"] = win_types

    sel_label = st.session_state.get("m15_active_drop_win_type")
    chosen_type = next((wt for wt in win_types if wt.get("label") == sel_label), win_types[0])

    w_m = float(chosen_type.get("w_cm", 100.0)) / 100.0
    h_m = float(chosen_type.get("h_cm", 120.0)) / 100.0
    sill_m = float(chosen_type.get("sill_cm", 90.0)) / 100.0
    type_lbl = chosen_type.get("label", "W1")

    wlen = _wall_length_m(wk)
    col1_l, col2_l, _, _, _ = _get_column_bounds_along_wall(wk)
    clear_wall = max(0.0, col2_l - col1_l) if col2_l > col1_l else 0.0

    if clear_wall < w_m - 0.01:
        st.toast(f"⚠️ المسافة الصافية على الحائط ({clear_wall:.2f}م) أقل من عرض الشباك ({w_m:.2f}م)!", icon="🚫")
        return

    center_pos = round(max(0.0, (wlen - w_m) / 2.0), 2)
    new_wname = _next_window_name(type_lbl)

    conflict_errs = _check_opening_spatial_conflict(
        wk=wk,
        op_name=f"الشباك {new_wname}",
        op_type="win",
        w_m=w_m,
        h_m=h_m,
        pos_m=center_pos
    )

    final_pos = center_pos
    if conflict_errs:
        alt_pos = _find_first_available_opening_pos(wk, "win", w_m, h_m)
        alt_errs = _check_opening_spatial_conflict(
            wk=wk,
            op_name=f"الشباك {new_wname}",
            op_type="win",
            w_m=w_m,
            h_m=h_m,
            pos_m=alt_pos
        )
        if not alt_errs:
            final_pos = alt_pos
        else:
            st.toast(f"⚠️ لا يمكن إسقاط الشباك: يوجد تعارض مع فتحة أخرى على الحائط!", icon="🚫")
            return

    win_to_add = {
        "id": _next_op_id("win"),
        "kind": "win",
        "wk": wk,
        "name": new_wname,
        "type_label": type_lbl,
        "w_m": float(w_m),
        "h_m": float(h_m),
        "pos_m": float(final_pos),
        "sill_m": float(sill_m),
        "removed": False,
        "is_preview": False,
        "has_conflict": False,
    }

    if "m15_windows" not in st.session_state:
        st.session_state["m15_windows"] = {}
    if wk not in st.session_state["m15_windows"]:
        st.session_state["m15_windows"][wk] = []

    st.session_state["m15_windows"][wk].append(win_to_add)
    _resequence_openings()
    st.session_state["m15_add_win_mode"] = True
    st.session_state.pop("m15_plan_png_b64", None)
    save_settings()
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    w_label = _wall_display_label(wk, cm, wm)
    st.toast(f"✅ تم إسقاط الشباك {new_wname} في منتصف الحائط ({w_label}) بنجاح!", icon="🪟")
    st.rerun()


def _execute_add_door_box(data):
    """
    إسقاط باب تفاعلي بالماوس مباشرة على الحائط المختار:
    - موضع الباب الافتراضي: منتصف الحائط تماماً (Center to Center).
    - الترقيم التلقائي حسب نموذج الباب (D1-1, D1-2...).
    - التحقق من المسافة الصافية وخلو الموضع من التعارضات.
    """
    raw_wk = data.get("wk")
    if not raw_wk or len(raw_wk) != 4:
        st.toast("⚠️ لم يتم تحديد حائط صحيح.", icon="⚠️")
        return

    wk = (int(raw_wk[0]), int(raw_wk[1]), int(raw_wk[2]), int(raw_wk[3]))
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    if wk not in all_walls or wk in removed_walls:
        st.toast("⚠️ الحائط المختار غير نشط أو محذوف.", icon="⚠️")
        return

    door_types = st.session_state.get("m15_door_types", [])
    if not door_types:
        door_types = [{"id": "dt_1", "label": "D1", "w_cm": 90.0, "h_cm": 210.0}]
        st.session_state["m15_door_types"] = door_types

    sel_label = st.session_state.get("m15_active_drop_door_type")
    chosen_type = next((dt for dt in door_types if dt.get("label") == sel_label), door_types[0])

    w_m = float(chosen_type.get("w_cm", 90.0)) / 100.0
    h_m = float(chosen_type.get("h_cm", 210.0)) / 100.0
    door_type_lbl = chosen_type.get("label", "D1")

    wlen = _wall_length_m(wk)
    col1_l, col2_l, _, _, _ = _get_column_bounds_along_wall(wk)
    clear_wall = max(0.0, col2_l - col1_l) if col2_l > col1_l else 0.0

    if clear_wall < w_m - 0.01:
        st.toast(f"⚠️ المسافة الصافية على الحائط ({clear_wall:.2f}م) أقل من عرض الباب ({w_m:.2f}م)!", icon="🚫")
        return

    center_pos = round(max(0.0, (wlen - w_m) / 2.0), 2)
    is_h_wall = (wk[1] == wk[3])
    new_leaf = "أعلى" if is_h_wall else "يمين"
    new_hinge = "يسار" if is_h_wall else "أسفل"
    new_dname = _next_door_name(door_type_lbl)

    conflict_errs = _check_opening_spatial_conflict(
        wk=wk,
        op_name=f"الباب {new_dname}",
        op_type="door",
        w_m=w_m,
        h_m=h_m,
        pos_m=center_pos,
        leaf_dir=new_leaf
    )

    final_pos = center_pos
    if conflict_errs:
        alt_pos = _find_first_available_opening_pos(wk, "door", w_m, h_m, leaf_dir=new_leaf)
        alt_errs = _check_opening_spatial_conflict(
            wk=wk,
            op_name=f"الباب {new_dname}",
            op_type="door",
            w_m=w_m,
            h_m=h_m,
            pos_m=alt_pos,
            leaf_dir=new_leaf
        )
        if not alt_errs:
            final_pos = alt_pos
        else:
            st.toast(f"⚠️ لا يمكن إسقاط الباب: يوجد تعارض مع فتحة أخرى على الحائط!", icon="🚫")
            return

    door_to_add = {
        "id": _next_op_id("door"),
        "kind": "door",
        "wk": wk,
        "name": new_dname,
        "type_label": door_type_lbl,
        "w_m": float(w_m),
        "h_m": float(h_m),
        "pos_m": float(final_pos),
        "leaf_dir": new_leaf,
        "hinge_dir": new_hinge,
        "removed": False,
        "is_preview": False,
        "has_conflict": False,
    }

    if "m15_doors" not in st.session_state:
        st.session_state["m15_doors"] = {}
    if wk not in st.session_state["m15_doors"]:
        st.session_state["m15_doors"][wk] = []

    st.session_state["m15_doors"][wk].append(door_to_add)
    _resequence_openings()
    st.session_state["m15_add_door_mode"] = True
    st.session_state.pop("m15_plan_png_b64", None)
    save_settings()
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    w_label = _wall_display_label(wk, cm, wm)
    st.toast(f"✅ تم إسقاط الباب {new_dname} في منتصف الحائط ({w_label}) بنجاح!", icon="🚪")
    st.rerun()


def _handle_sync_payload(payload_str=None):
    """
    معالجة جميع الإشارات التفاعلية الواردة من المسقط الأفقي والعارض ثلاثي الأبعاد 3D:
    - إضافة عمود تفاعلي بالصندوق (add_column_box).
    - استعادة عمود تفاعلي بالصندوق (restore_column_box).
    - إسقاط شباك تفاعلي بالماوس (add_window_box).
    - إسقاط باب تفاعلي بالماوس (add_door_box).
    - إنهاء وضع الصندوق التفاعلي (exit_box_mode).
    - تحريك الفتحات وحذف الحوائط/الأعمدة من المجسم ثلاثي الأبعاد.
    """
    val = payload_str
    if not val:
        val = st.session_state.get("m15_3d_sync_input")
    from_query = False
    if not val and "m15_op_move" in st.query_params:
        val = st.query_params["m15_op_move"]
        from_query = True

    if not val:
        return

    try:
        data = json.loads(val) if isinstance(val, str) else val
        action = str(data.get("action", "")).lower()
        op_type = str(data.get("type", "")).lower()

        if from_query:
            if "m15_op_move" in st.query_params:
                try: del st.query_params["m15_op_move"]
                except Exception: pass
            if "module" in st.query_params:
                try: del st.query_params["module"]
                except Exception: pass

        st.session_state["m15_3d_sync_input"] = ""

        if action == "exit_box_mode":
            st.session_state["m15_add_col_mode"] = False
            st.session_state["m15_restore_col_mode"] = False
            st.session_state["m15_del_wall_mode"] = False
            st.session_state["m15_add_wall_mode"] = False
            st.session_state["m15_add_win_mode"] = False
            st.session_state["m15_add_door_mode"] = False
            st.session_state["m15_pending_delete_wall"] = None
            save_settings()
            st.rerun()

        elif action in ["add_window_box", "add_window"]:
            _execute_add_window_box(data)

        elif action in ["add_door_box", "add_door"]:
            _execute_add_door_box(data)

        elif action == "add_wall_box":
            p1 = data.get("p1")
            p2 = data.get("p2")
            if p1 and p2 and len(p1) == 2 and len(p2) == 2:
                si, sj = int(p1[0]), int(p1[1])
                ei, ej = int(p2[0]), int(p2[1])
                placed_list = list(st.session_state.get("m15_walls_placed", []))
                wt = dict(st.session_state.get("m15_wall_thickness", {}))
                wh = dict(st.session_state.get("m15_wall_heights", {}))
                th_val = int(st.session_state.get("m15_new_wall_thick_choice", 12))
                h_val = float(st.session_state.get("m15_new_wall_height_choice", st.session_state.get("m15_default_wall_height", 3.0)))
                removed_walls = set(st.session_state.get("m15_wall_removed", set()))

                added_count = 0
                # محاذاة أفقية أو رأسية بحسب المحور الأطول
                if sj == ej or abs(si - ei) >= abs(sj - ej):
                    i_min, i_max = min(si, ei), max(si, ei)
                    for k in range(i_min, i_max):
                        seg = (k, sj, k + 1, sj)
                        if seg not in placed_list:
                            placed_list.append(seg)
                            added_count += 1
                        wt[seg] = th_val; wh[seg] = h_val
                        removed_walls.discard(seg)
                else:
                    j_min, j_max = min(sj, ej), max(sj, ej)
                    for k in range(j_min, j_max):
                        seg = (si, k, si, k + 1)
                        if seg not in placed_list:
                            placed_list.append(seg)
                            added_count += 1
                        wt[seg] = th_val; wh[seg] = h_val
                        removed_walls.discard(seg)

                st.session_state["m15_walls_placed"] = placed_list
                st.session_state["m15_wall_thickness"] = wt
                st.session_state["m15_wall_heights"] = wh
                st.session_state["m15_wall_removed"] = removed_walls
                _normalize_wall_keys()
                st.session_state["m15_add_wall_mode"] = True
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                if added_count > 1:
                    st.toast(f"✅ تم إسقاط {added_count} حوائط منفصلة بين كل تقاطعين متجاورين بنجاح!", icon="🧱")
                else:
                    st.toast("✅ تم إسقاط الحائط بين التقاطعين المتجاورين بنجاح!", icon="🧱")
                st.rerun()

        elif action in ["select_delete_wall_box", "select_delete_wall"]:
            _execute_select_delete_wall_box(data)

        elif action in ["confirm_delete_wall_box", "confirm_delete_wall"]:
            _execute_confirm_delete_wall_box(data)

        elif action in ["add_column_box", "add_column"]:
            _execute_add_column_box(data)

        elif action in ["restore_column_box", "restore_column"]:
            _execute_restore_column_box(data)

        elif action == "delete_column" or op_type == "delete_column":
            col_coords = data.get("col")
            if col_coords and len(col_coords) == 2:
                ci, cj = int(col_coords[0]), int(col_coords[1])
                _record_col_deletion(ci, cj)
                removed_cols = st.session_state.get("m15_col_removed", set())
                if not isinstance(removed_cols, set):
                    removed_cols = set(removed_cols)
                removed_cols.add((ci, cj))
                st.session_state["m15_col_removed"] = removed_cols
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                cn = _get_col_name_map()
                c_name = data.get("name") or cn.get((ci, cj), f"C({ci+1},{cj+1})")
                st.toast(f"🗑️ تم حذف العمود ({c_name}) وحفظه في قسم استعادة الأعمدة!", icon="🗑️")
                st.rerun()

        elif action == "delete_wall" or op_type == "delete_wall":
            wall_list = data.get("wall")
            if wall_list and len(wall_list) == 4:
                wk = tuple(int(x) for x in wall_list)
                removed_walls = st.session_state.get("m15_wall_removed", set())
                if not isinstance(removed_walls, set):
                    removed_walls = set(removed_walls)
                removed_walls.add(wk)
                st.session_state["m15_wall_removed"] = removed_walls
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                cm = _get_col_name_map()
                wm = _get_wall_name_map()
                w_name = data.get("name") or _wall_display_label(wk, cm, wm)
                st.toast(f"🗑️ تم حذف الحائط ({w_name}) وحفظه في قسم استعادة الحوائط المحذوفة!", icon="🗑️")
                st.rerun()

        elif action == "delete_window" or op_type == "delete_window":
            win_id = data.get("id")
            win_name = data.get("name", "الشباك")
            if win_id:
                _remove_opening_by_id(win_id, "win")
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.toast(f"🗑️ تم حذف الشباك ({win_name}) وحفظه في قسم استعادة الشبابيك والأبواب!", icon="🗑️")
                st.rerun()

        elif action == "delete_door" or op_type == "delete_door":
            door_id = data.get("id")
            door_name = data.get("name", "الباب")
            if door_id:
                _remove_opening_by_id(door_id, "door")
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.toast(f"🗑️ تم حذف الباب ({door_name}) وحفظه في قسم استعادة الشبابيك والأبواب!", icon="🗑️")
                st.rerun()

        else:
            _apply_3d_opening_move(val)
    except Exception as e:
        pass


def _section_add_columns():
    """
    قسم إضافة الأعمدة التفاعلي (Interactive Column Addition):
    - إعدادات العمود: نموذج، أبعاد b و t، اتجاه (أفقي/رأسي)، نقطة الارتكاز (السنتر/محاذاة أركان).
    - زر 'اختيار عمود على المسقط الأفقي'.
    - تفعيل نمط التحديد بصندوق الماوس Box Selection Mode على لوحة المسقط الأفقي.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 1 or len(ys) < 1:
        st.info("⚠️ أدخل محاور X و Y أولاً في قسم 'شبكة المحاور'.")
        return

    is_add_active = bool(st.session_state.get("m15_add_col_mode", False))

    def _on_col_dims_change():
        cur_b = float(st.session_state.get("m15_new_col_b", 25.0))
        cur_t = float(st.session_state.get("m15_new_col_t", 60.0))
        st.session_state["m15_col_width_cm"] = cur_b
        st.session_state["m15_col_length_cm"] = cur_t
        st.session_state["m15_new_col_model"] = f"C({int(cur_b)}x{int(cur_t)})"
        st.session_state["_m15_saved_col_b"] = cur_b
        st.session_state["_m15_saved_col_t"] = cur_t
        m15_data = st.session_state.get("module_15_data")
        if isinstance(m15_data, dict):
            m15_data["col_width_cm"] = cur_b
            m15_data["col_length_cm"] = cur_t
            m15_data["new_col_b"] = cur_b
            m15_data["new_col_t"] = cur_t
        save_settings()

    c_b, c_t = st.columns(2)
    with c_b:
        b_val = st.number_input(
            "العرض b (سم):",
            min_value=12.0,
            max_value=200.0,
            value=float(st.session_state.get("m15_new_col_b", 25.0)),
            step=5.0,
            key="m15_new_col_b",
            on_change=_on_col_dims_change,
            help="عرض العمود بالسنتمتر (يتم اعتماده كـ default للأعمدة التالية)"
        )
    with c_t:
        t_val = st.number_input(
            "الطول t (سم):",
            min_value=15.0,
            max_value=300.0,
            value=float(st.session_state.get("m15_new_col_t", 60.0)),
            step=5.0,
            key="m15_new_col_t",
            on_change=_on_col_dims_change,
            help="طول العمود بالسنتمتر (يتم اعتماده كـ default للأعمدة التالية)"
        )

    cur_b = float(b_val)
    cur_t = float(t_val)
    st.session_state["m15_col_width_cm"] = cur_b
    st.session_state["m15_col_length_cm"] = cur_t
    st.session_state["m15_new_col_model"] = f"C({int(cur_b)}x{int(cur_t)})"

    if (st.session_state.get("_m15_saved_col_b") != cur_b or 
        st.session_state.get("_m15_saved_col_t") != cur_t):
        st.session_state["_m15_saved_col_b"] = cur_b
        st.session_state["_m15_saved_col_t"] = cur_t
        m15_data = st.session_state.get("module_15_data")
        if isinstance(m15_data, dict):
            m15_data["col_width_cm"] = cur_b
            m15_data["col_length_cm"] = cur_t
            m15_data["new_col_b"] = cur_b
            m15_data["new_col_t"] = cur_t
        save_settings()

    st.markdown("<hr style='margin: 12px 0 14px 0; border: none; border-top: 1px dashed #cbd5e1;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.92rem; font-weight:700; color:#ffffff; margin-bottom:10px;'>اسقاط اعمدة بسحب صندوق بالماوس</div>", unsafe_allow_html=True)

    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None and active_mode.get("key") != "m15_add_col_mode")

    if has_conflict:
        _render_mode_conflict_warning("إسقاط الأعمدة", active_mode, context_key="add_cols")
        st.button("🎯 تفعيل اختيار عمود بالسحب على المسقط", type="primary", use_container_width=True, key="m15_btn_start_add_col", disabled=True)
    elif not is_add_active:
        if st.button("🎯 تفعيل اختيار عمود بالسحب على المسقط", type="primary", use_container_width=True, key="m15_btn_start_add_col"):
            _close_all_interactive_modes()
            st.session_state["m15_add_col_mode"] = True
            st.rerun()
    else:
        if st.button("⏹️ إنهاء وضع الإضافة (Esc)", key="m15_btn_exit_add_col", use_container_width=True):
            st.session_state["m15_add_col_mode"] = False
            st.rerun()


def _section_column_orientations():
    """
    قسم ضبط اتجاهات وضرب الأعمدة (Column Orientations & Offsets):
    بنفس فلسفة موديول 1 (قسم Structural Geometry Sketch & Verification)
    يحتوي فقط على المدخلات الأربعة التالية:
    1. اسم العمود (اختيار العمود القائم مع كود التقاطع Y{i+1} × X{j+1})
    2. اتجاه ضرب العمود (رأسي موازٍ لـ Y / أفقي موازٍ لـ X)
    3. الترحيل الأفقي (X)
    4. الترحيل الرأسي (Y)
    دون تحديد أعمدة جار أو اتجاهاتها.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 1 or len(ys) < 1:
        st.info("⚠️ أدخل محاور X و Y أولاً في قسم 'شبكة المحاور'.")
        return

    active_cols = _get_active_columns()
    if not active_cols:
        st.info("💡 لا توجد أعمدة قائمة حالياً. أضف أعمدة أولاً من قسم '➕ إضافة الأعمدة على المحاور'.")
        return

    cn = _get_col_name_map()
    col_dirs = st.session_state.setdefault("m15_col_dirs", {})
    col_shifts = st.session_state.setdefault("m15_col_shifts", {})
    col_shifted = st.session_state.setdefault("m15_col_shifted", {})
    col_props = st.session_state.setdefault("m15_col_props", {})

    def _col_opt_label(coord):
        i, j = coord
        orig_cname = f"C{j * len(xs) + i + 1}"
        cname = cn.get((i, j), orig_cname)
        return f"{cname} — (Y{i+1} × X{j+1}) [Y={xs[i]:.2f}م، X={ys[j]:.2f}م]"

    cur_sel = st.session_state.get("m15_col_orient_sel")
    if cur_sel not in active_cols:
        cur_sel = active_cols[0]
        st.session_state["m15_col_orient_sel"] = cur_sel

    sel_coord = st.selectbox(
        "اسم العمود",
        options=active_cols,
        index=active_cols.index(cur_sel),
        format_func=_col_opt_label,
        key="m15_col_orient_sel",
        help="اختر العمود المراد ضبط ضربه وترحيله من المسقط الأفقي الحالي."
    )
    si, sj = sel_coord

    # قراءة بيانات العمود المختار
    cur_dir_code = col_dirs.get((si, sj), "NS")
    DIR_OPTIONS = ["رأسي (موازٍ لمحور Y)", "أفقي (موازٍ لمحور X)"]
    idx_dir = 0 if cur_dir_code == "NS" else 1

    cur_tr = col_shifts.get((si, sj), {})
    if not cur_tr:
        leg_dx, leg_dy = col_shifted.get((si, sj), (0.0, 0.0))
        sx_init = M15_SHIFT_X_OPTIONS[0]
        if leg_dx > 0.01:
            sx_init = M15_SHIFT_X_OPTIONS[1]
        elif leg_dx < -0.01:
            sx_init = M15_SHIFT_X_OPTIONS[2]
        sy_init = M15_SHIFT_Y_OPTIONS[0]
        if leg_dy > 0.01:
            sy_init = M15_SHIFT_Y_OPTIONS[1]
        elif leg_dy < -0.01:
            sy_init = M15_SHIFT_Y_OPTIONS[2]
        cur_tr = {"shift_x": sx_init, "shift_y": sy_init}
        col_shifts[(si, sj)] = cur_tr

    norm_cur_sx = _normalize_m15_col_shift(cur_tr.get("shift_x"), axis="x")
    norm_cur_sy = _normalize_m15_col_shift(cur_tr.get("shift_y"), axis="y")

    idx_sx = M15_SHIFT_X_OPTIONS.index(norm_cur_sx) if norm_cur_sx in M15_SHIFT_X_OPTIONS else 0
    idx_sy = M15_SHIFT_Y_OPTIONS.index(norm_cur_sy) if norm_cur_sy in M15_SHIFT_Y_OPTIONS else 0

    k_dir = f"m15_orient_dir_{si}_{sj}"
    k_sx = f"m15_orient_sx_{si}_{sj}"
    k_sy = f"m15_orient_sy_{si}_{sj}"

    def _apply_orient_update():
        dir_val = st.session_state.get(k_dir)
        sx_val = st.session_state.get(k_sx)
        sy_val = st.session_state.get(k_sy)

        new_dc = "NS" if dir_val and "رأسي" in str(dir_val) else "EW"
        norm_sx = _normalize_m15_col_shift(sx_val, axis="x")
        norm_sy = _normalize_m15_col_shift(sy_val, axis="y")

        cdirs = st.session_state.setdefault("m15_col_dirs", {})
        cdirs[(si, sj)] = new_dc
        st.session_state["m15_col_dirs"] = cdirs

        cshifts = st.session_state.setdefault("m15_col_shifts", {})
        cshifts[(si, sj)] = {"shift_x": norm_sx, "shift_y": norm_sy}
        st.session_state["m15_col_shifts"] = cshifts

        cprops = st.session_state.setdefault("m15_col_props", {})
        cp = cprops.setdefault((si, sj), {})
        cp["dir"] = "رأسي" if new_dc == "NS" else "أفقي"
        cp["dir_code"] = new_dc
        cp["shift_x"] = norm_sx
        cp["shift_y"] = norm_sy
        st.session_state["m15_col_props"] = cprops

        cw_now, ch_now = _get_col_wh(si, sj)
        dx_m, dy_m = _compute_col_offsets(cw_now, ch_now, norm_sx, norm_sy)
        cshifted = st.session_state.setdefault("m15_col_shifted", {})
        cshifted[(si, sj)] = (dx_m * 100.0, dy_m * 100.0)
        st.session_state["m15_col_shifted"] = cshifted

        st.session_state.pop("m15_plan_png_b64", None)
        save_settings()

    # مزامنة مسبقة لحالة عناصر التحكم في حال وجود قيم مخزنة سابقة تختلف عن قيم العمود المختار
    if k_dir in st.session_state:
        state_dir_code = "NS" if "رأسي" in str(st.session_state[k_dir]) else "EW"
        if state_dir_code != cur_dir_code:
            st.session_state[k_dir] = DIR_OPTIONS[idx_dir]

    if k_sx in st.session_state:
        if _normalize_m15_col_shift(st.session_state[k_sx], axis="x") != norm_cur_sx:
            st.session_state[k_sx] = M15_SHIFT_X_OPTIONS[idx_sx]

    if k_sy in st.session_state:
        if _normalize_m15_col_shift(st.session_state[k_sy], axis="y") != norm_cur_sy:
            st.session_state[k_sy] = M15_SHIFT_Y_OPTIONS[idx_sy]

    sel_dir = st.selectbox(
        "اتجاه ضرب العمود",
        options=DIR_OPTIONS,
        index=idx_dir,
        key=k_dir,
        on_change=_apply_orient_update,
        help="اتجاه البعد الأكبر للعمود (موازٍ لمحور Y أو لمحور X)."
    )

    sel_sx = st.selectbox(
        "الترحيل الأفقي (X)",
        options=M15_SHIFT_X_OPTIONS,
        index=idx_sx,
        key=k_sx,
        on_change=_apply_orient_update,
        help="الترحيل الأفقي لجسم العمود بالنسبة للمحور الرأسي Y (6 سم)."
    )

    sel_sy = st.selectbox(
        "الترحيل الرأسي (Y)",
        options=M15_SHIFT_Y_OPTIONS,
        index=idx_sy,
        key=k_sy,
        on_change=_apply_orient_update,
        help="الترحيل الرأسي لجسم العمود بالنسبة للمحور الأفقي X (6 سم)."
    )

    new_dir_code = "NS" if "رأسي" in str(sel_dir) else "EW"
    norm_new_sx = _normalize_m15_col_shift(sel_sx, axis="x")
    norm_new_sy = _normalize_m15_col_shift(sel_sy, axis="y")

    if new_dir_code != col_dirs.get((si, sj)) or norm_new_sx != norm_cur_sx or norm_new_sy != norm_cur_sy:
        _apply_orient_update()

    # بطاقة معلومات توضيحية لترحيل العمود الحالي (أوفست بالسنتيمتر)
    dx_val, dy_val = col_shifted.get((si, sj), (0.0, 0.0))
    dir_badge = "رأسي (موازٍ لمحور Y)" if new_dir_code == "NS" else "أفقي (موازٍ لمحور X)"
    badge_bg = "#1e40af" if new_dir_code == "NS" else "#b45309"
    badge_clr = "#ffffff"

    st.markdown(
        f"""<div style='background:rgba(30, 41, 59, 0.75); border:1px solid #334155; border-radius:8px; padding:10px 14px; margin-top:8px;' dir='rtl'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;'>
                <span style='font-size:0.85rem; color:#cbd5e1;'>ضرب العمود:</span>
                <span style='background:{badge_bg}; color:{badge_clr}; font-weight:700; font-size:0.82rem; padding:2px 8px; border-radius:4px;'>{dir_badge}</span>
            </div>
            <div style='display:flex; justify-content:space-between; align-items:center; font-size:0.84rem; color:#ffffff;'>
                <span>إزاحة المركز (ΔX): <b>{dx_val:+.1f} سم</b></span>
                <span>إزاحة المركز (ΔY): <b>{dy_val:+.1f} سم</b></span>
            </div>
        </div>""",
        unsafe_allow_html=True
    )


def _section_restore_columns():
    """
    قسم استعادة الأعمدة التفاعلي (Interactive Column Restoration):
    - زر 'استعادة عمود على المسقط الأفقي'.
    - تفعيل نمط التحديد بصندوق الماوس على المسقط الأفقي.
    - فحص ومطابقة التقاطع مع سجل الأعمدة الأصلية/المحذوفة (Deleted Columns History).
    - استعادة العمود بكامل خصائصه الأصلية فوراً.
    - استمرار النمط مع زر إنهاء أو Esc.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 1 or len(ys) < 1:
        st.info("⚠️ أدخل محاور X و Y أولاً في قسم 'شبكة المحاور'.")
        return

    is_restore_active = bool(st.session_state.get("m15_restore_col_mode", False))
    deleted_history = st.session_state.get("m15_deleted_cols_history", {})
    removed_cols = st.session_state.get("m15_col_removed", set())
    if not isinstance(removed_cols, set):
        removed_cols = set(removed_cols)

    rem_count = len(removed_cols)

    st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#ffffff; margin-top:8px; margin-bottom:16px;'>♻️ استعادة الأعمدة المحذوفة على المسقط</div>", unsafe_allow_html=True)

    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None and active_mode.get("key") != "m15_restore_col_mode")

    if has_conflict:
        _render_mode_conflict_warning("استعادة الأعمدة", active_mode, context_key="restore_cols")
        st.button("♻️ استعادة عمود على المسقط الأفقي", type="primary", use_container_width=True, key="m15_btn_start_restore_col", disabled=True)
    elif not is_restore_active:
        if st.button("♻️ استعادة عمود على المسقط الأفقي", type="primary", use_container_width=True, key="m15_btn_start_restore_col"):
            _close_all_interactive_modes()
            st.session_state["m15_restore_col_mode"] = True
            st.rerun()
    else:
        st.markdown(
            """<div style='background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 2px solid #10b981; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px;' dir='rtl'>
                <div style='display: flex; align-items: center; gap: 8px; font-weight: 700; color: #065f46; font-size: 0.92rem;'>
                    <span>♻️</span>
                    <span>اسحب مربعاً بالماوس يحتوي على تقاطع المحورين المراد استعادة العمود عنده</span>
                </div>
                <div style='font-size: 0.80rem; color: #059669; margin-top: 4px;'>
                    اسحب مؤشر الماوس فوق تقاطع العمود المحذوف في المسقط الأفقي (باليمين). يستمر وضع الاستعادة نشطاً لاستعادة أعمدة أخرى تباعاً.
                </div>
            </div>""",
            unsafe_allow_html=True
        )
        if st.button("⏹️ إنهاء وضع الاستعادة (Esc)", key="m15_btn_exit_restore_col", use_container_width=True):
            st.session_state["m15_restore_col_mode"] = False
            st.rerun()

    if rem_count == 0:
        st.success("✅ لا توجد أعمدة محذوفة حالياً. كافة أعمدة شبكة المحاور قائمة ونشطة.")
    else:
        st.info(f"💡 يوجد حالياً **{rem_count}** عمود محذوف في سجل المحذوفات يمكن استعادتها بالسحب على المسقط.")
        with st.expander(f"📋 سجل الأعمدة المحذوفة ({rem_count})", expanded=False):
            cn = _get_col_name_map()
            hist_rows = []
            for (i, j) in sorted(removed_cols):
                h_item = deleted_history.get((i, j), {})
                orig_cname = f"C{j * len(xs) + i + 1}"
                cname = h_item.get("model") or h_item.get("name") or cn.get((i, j), orig_cname)
                b_cm = h_item.get("b_cm", st.session_state.get("m15_col_width_cm", 30.0))
                t_cm = h_item.get("t_cm", st.session_state.get("m15_col_length_cm", 60.0))
                c_dir = h_item.get("dir_code", h_item.get("dir", "NS"))
                hist_rows.append({
                    "العمود": cname,
                    "التقاطع": f"Y{i+1} × X{j+1}",
                    "الأبعاد (سم)": f"{int(round(b_cm))}×{int(round(t_cm))}",
                    "الاتجاه": "رأسي" if c_dir == "NS" else "أفقي"
                })
            import pandas as pd
            st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)


def _section_delete_walls():
    """
    قسم حذف الحوائط التفاعلي (Interactive Wall Deletion):
    - زر 'اختيار حائط للحذف على المسقط الأفقي' لتفعيل نمط الصندوق الأحمر.
    - رسالة تأكيد الحذف عند التقاط الحائط بالصندوق أو النقر عليه مع زري [✅ نعم، تأكيد الحذف] و [❌ إلغاء].
    - إمكانية اختيار حائط يدوي من قائمة الحوائط النشطة كبديل سريع.
    - إحصائيات الحوائط القائمة والمحذوفة.
    - قسم استعادة الحوائط المحذوفة مع زر استعادة فردي وزر '♻️ استعادة جميع الحوائط المحذوفة'.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 1 or len(ys) < 1:
        st.info("⚠️ أدخل محاور X و Y أولاً في قسم 'شبكة المحاور'.")
        return

    all_walls = _get_all_walls()
    if not all_walls:
        st.info("ℹ️ لا توجد حوائط مرسومة في المخطط حالياً.")
        return

    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    if not isinstance(removed_walls, set):
        removed_walls = set(removed_walls)

    active_walls = [w for w in all_walls if w not in removed_walls]
    is_del_wall_active = bool(st.session_state.get("m15_del_wall_mode", False))
    pending_wk = st.session_state.get("m15_pending_delete_wall")

    st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#ffffff; margin-top:8px; margin-bottom:16px;'>🗑️ حذف حوائط (Interactive Box Selection)</div>", unsafe_allow_html=True)

    # 1. زر تفعيل نمط التحديد بالصندوق على المسقط الأفقي
    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None and active_mode.get("key") != "m15_del_wall_mode")

    if has_conflict:
        _render_mode_conflict_warning("حذف الحوائط", active_mode, context_key="del_walls")
        st.button("🎯 اختيار حائط للحذف على المسقط الأفقي", type="primary", use_container_width=True, key="m15_btn_start_del_wall", disabled=True)
    elif not is_del_wall_active:
        if st.button("🎯 اختيار حائط للحذف على المسقط الأفقي", type="primary", use_container_width=True, key="m15_btn_start_del_wall"):
            _close_all_interactive_modes()
            st.session_state["m15_del_wall_mode"] = True
            st.rerun()
    else:
        if st.button("⏹️ إنهاء وضع الحذف (Esc)", key="m15_btn_exit_del_wall", use_container_width=True):
            st.session_state["m15_del_wall_mode"] = False
            st.session_state["m15_pending_delete_wall"] = None
            st.rerun()

    # 2. بطاقة تأكيد الحذف عند التقاط حائط معلق
    if pending_wk and pending_wk in all_walls:
        play_delete_confirmation_whistle(f"m15_del_wall_{pending_wk}")
        w_name = wm.get(pending_wk, "—")
        st.markdown(
            f"""<div style='background: #fff1f2; border: 2px solid #e11d48; border-radius: 8px; padding: 10px 14px; margin: 10px 0; font-weight: 800; color: #9f1239; font-size: 0.95rem;' dir='rtl'>
                ⚠️ تأكيد حذف الحائط <b>{w_name}</b>
            </div>""",
            unsafe_allow_html=True
        )
        c_sec_y, c_sec_n = st.columns(2)
        with c_sec_y:
            if st.button("✅ نعم، تأكيد حذف الحائط", key="m15_sec_conf_del_wall_yes", type="primary", use_container_width=True):
                _confirm_delete_wall(pending_wk)
        with c_sec_n:
            if st.button("❌ إلغاء", key="m15_sec_conf_del_wall_no", use_container_width=True):
                st.session_state["m15_pending_delete_wall"] = None
                st.session_state.pop("_last_del_confirm_whistle_token", None)
                st.rerun()

    # 3. اختيار يدوي بديل من القائمة
    if active_walls:
        with st.expander("🔍 أو اختر حائطاً مباشرة من القائمة للحذف", expanded=False):
            wall_options = [0] + list(range(1, len(active_walls) + 1))
            def _fmt_w(idx):
                if idx == 0: return "-- اختر حائطاً للحذف مباشرة --"
                w = active_walls[idx - 1]
                return f"{_wall_display_label(w, cm, wm)} (طول: {_wall_length_m(w):.2f}م | سُمك: {_get_wall_thickness(w)}سم)"
            sel_w_idx = st.selectbox("الحائط المراد حذفه:", options=wall_options, format_func=_fmt_w, key="m15_dropdown_del_wall")
            if sel_w_idx != 0:
                target_wk = active_walls[sel_w_idx - 1]
                if has_conflict:
                    st.button("🗑️ حذف هذا الحائط", key="m15_btn_request_dropdown_del_wall", use_container_width=True, disabled=True, help="لا يمكن الحذف لوجود نمط نشط على المسقط")
                else:
                    if st.button("🗑️ حذف هذا الحائط", key="m15_btn_request_dropdown_del_wall", use_container_width=True):
                        st.session_state["m15_pending_delete_wall"] = target_wk
                        play_delete_confirmation_whistle(f"m15_del_wall_{target_wk}")
                        st.session_state["m15_del_wall_mode"] = True
                        st.rerun()

    if removed_walls:
        st.caption("💡 لاستعادة أي من الحوائط المحذوفة، تفضل بفتح قسم **'♻️ استعادة الحوائط المحذوفة'** بالأسفل.")


def _section_restore_walls():
    """
    قسم استعادة الحوائط المحذوفة (Restore Deleted Walls):
    - عرض إحصائيات الحوائط المحذوفة.
    - زر '♻️ استعادة جميع الحوائط المحذوفة' دفعة واحدة.
    - قائمة تفاعلية للحوائط المحذوفة مع زر استعادة لكل حائط ومواصفاته (المحاور، الطول، السُمك).
    - جدول تفصيلي منظم لكافة الحوائط المحذوفة.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 1 or len(ys) < 1:
        st.info("⚠️ أدخل محاور X و Y أولاً في قسم 'شبكة المحاور'.")
        return

    all_walls = _get_all_walls()
    if not all_walls:
        st.info("ℹ️ لا توجد حوائط في المخطط حالياً.")
        return

    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    if not isinstance(removed_walls, set):
        removed_walls = set(removed_walls)

    rem_count = len(removed_walls)
    active_count = len(all_walls) - rem_count

    st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#ffffff; margin-top:8px; margin-bottom:14px;'>♻️ استعادة الحوائط المحذوفة</div>", unsafe_allow_html=True)

    c_st1, c_st2 = st.columns(2)
    with c_st1:
        st.caption(f"🧱 الحوائط النشطة: **{active_count}** حائط")
    with c_st2:
        st.caption(f"🗑️ الحوائط المحذوفة: **{rem_count}** حائط")

    if rem_count == 0:
        st.success("✅ لا توجد حوائط محذوفة حالياً. كافة حوائط المخطط نشطة وظاهرة في الحصر و 3D.")
        return

    st.info(f"💡 يوجد حالياً **{rem_count}** حائط محذوف في سجل المحذوفات. يمكنك استعادتها فردياً أو استعادة الكل دفعة واحدة:")

    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None)
    if has_conflict:
        _render_mode_conflict_warning("استعادة الحوائط المحذوفة", active_mode, context_key="restore_walls")

    if st.button("♻️ استعادة جميع الحوائط المحذوفة", key="m15_sec_restore_all_walls", type="primary", use_container_width=True, disabled=has_conflict):
        st.session_state["m15_wall_removed"] = set()
        st.session_state["m15_pending_delete_wall"] = None
        st.session_state.pop("m15_plan_png_b64", None)
        save_settings()
        st.toast("✅ تم استعادة جميع الحوائط المحذوفة بنجاح!", icon="♻️")
        st.rerun()

    st.markdown("<hr style='margin: 10px 0 12px 0; border: none; border-top: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    sorted_rem = sorted(list(removed_walls), key=lambda x: all_walls.index(x) if x in all_walls else 9999)
    for r_wk in sorted_rem:
        if r_wk in all_walls:
            rc_col1, rc_col2 = st.columns([2.6, 1.2], vertical_alignment="center")
            with rc_col1:
                st.markdown(
                    f"**🗑️ {_wall_display_label(r_wk, cm, wm)}**<br>"
                    f"<span style='font-size:0.78rem;color:#94a3b8;'>الطول: `{_wall_length_m(r_wk):.2f}م` | السُمك: `{_get_wall_thickness(r_wk)}سم`</span>",
                    unsafe_allow_html=True
                )
            with rc_col2:
                btn_k = f"m15_restore_wall_btn_{r_wk[0]}_{r_wk[1]}_{r_wk[2]}_{r_wk[3]}"
                if st.button("♻️ استعادة", key=btn_k, use_container_width=True, disabled=has_conflict):
                    removed_walls.discard(r_wk)
                    st.session_state["m15_wall_removed"] = removed_walls
                    st.session_state.pop("m15_plan_png_b64", None)
                    save_settings()
                    st.toast(f"✅ تم استعادة الحائط بنجاح!", icon="♻️")
                    st.rerun()

    with st.expander(f"📋 جدول الحوائط المحذوفة ({rem_count})", expanded=False):
        import pandas as pd
        wall_table = []
        for r_wk in sorted_rem:
            if r_wk in all_walls:
                c1_name = cm.get((r_wk[0], r_wk[1]), f"C({r_wk[0]+1},{r_wk[1]+1})")
                c2_name = cm.get((r_wk[2], r_wk[3]), f"C({r_wk[2]+1},{r_wk[3]+1})")
                wall_table.append({
                    "الحائط": _wall_display_label(r_wk, cm, wm),
                    "بين الأعمدة": f"{c1_name} ↔ {c2_name}",
                    "الطول (م)": round(_wall_length_m(r_wk), 2),
                    "السُمك (سم)": _get_wall_thickness(r_wk),
                    "الحالة": "🗑️ محذوف"
                })
        if wall_table:
            st.dataframe(pd.DataFrame(wall_table), use_container_width=True, hide_index=True)


def _section_columns():
    """قسم حذف الأعمدة (Delete Columns)."""
    xs = st.session_state["m15_x_axes"]
    ys = st.session_state["m15_y_axes"]
    if not xs or not ys:
        st.info("أدخل المحاور أولاً.")
        return

    removed_cols = st.session_state.get("m15_col_removed", set())
    if not isinstance(removed_cols, set):
        removed_cols = set(removed_cols)
    col_dirs = st.session_state["m15_col_dirs"]
    col_shifted = st.session_state["m15_col_shifted"]
    cn = _get_col_name_map()

    placed_set = st.session_state.get("m15_col_placed", set())
    if not isinstance(placed_set, set):
        placed_set = set(_safe_coord_tuple(item, 2) for item in placed_set if _safe_coord_tuple(item, 2))
    all_cols = sorted(placed_set | removed_cols)
    if not all_cols:
        st.info("💡 لم تُضَف أي أعمدة بعد. استخدم قسم '➕ إضافة الأعمدة على المحاور' أعلاه لإسقاط الأعمدة على المسقط.")
        return

    def _clbl(k):
        i, j = all_cols[k]
        orig_cname = f"C{j * len(xs) + i + 1}"
        if (i, j) in removed_cols:
            return f"🗑️ {orig_cname} محذوف (Y{i+1},X{j+1}) — Y{i+1}={xs[i]:.2f}م, X{j+1}={ys[j]:.2f}م"
        nm = cn.get((i, j), orig_cname)
        return f"✅ {nm} — Y{i+1}={xs[i]:.2f}م, X{j+1}={ys[j]:.2f}م"

    _safe_idx("m15_sel_col", len(all_cols))
    sel = st.selectbox("اختر عموداً", options=range(len(all_cols)), format_func=_clbl, key="m15_sel_col")
    si,sj=all_cols[sel]; is_rem=(si,sj) in removed_cols
    cur_dir=col_dirs.get((si,sj),"NS"); dx,dy=col_shifted.get((si,sj),(0.0,0.0))
    orig_cname = f"C{sj * len(xs) + si + 1}"
    cname = cn.get((si, sj), orig_cname)
    if is_rem:
        st.info(f"🗑️ العمود **{orig_cname}** عند تقاطع (Y{si+1}, X{sj+1}) محذوف — يمكنك استعادته من قسم '♻️ استعادة أعمدة' بالسحب على المسقط.")

    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None)
    if has_conflict:
        _render_mode_conflict_warning("حذف الأعمدة", active_mode, context_key="del_cols")

    # تأكيد حذف العمود
    if not is_rem and st.session_state.get("m15_confirm_del_col") == (si,sj):
        play_delete_confirmation_whistle(f"m15_del_col_{si}_{sj}")
        st.warning(f"⚠️ تأكيد حذف العمود {cname}؟ سيتم إزالة العمود الخرساني مع بقاء الحوائط قائمة على المحاور، وتسجيله في سجل المحذوفات.")
        cyes, cno = st.columns(2)
        with cyes:
            if st.button("✅ نعم، تأكيد حذف العمود", type="primary", key="m15_confirm_del_yes", use_container_width=True, disabled=has_conflict):
                _record_col_deletion(si, sj)
                removed_cols.add((si,sj)); st.session_state["m15_col_removed"]=removed_cols
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.session_state.pop("m15_confirm_del_col", None)
                st.session_state.pop("_last_del_confirm_whistle_token", None)
                st.toast(f"🗑️ تم حذف العمود {cname} وحفظه في سجل استعادة الأعمدة!", icon="🗑️")
                st.rerun()
        with cno:
            if st.button("❌ إلغاء", key="m15_confirm_del_no", use_container_width=True):
                st.session_state.pop("m15_confirm_del_col", None)
                st.session_state.pop("_last_del_confirm_whistle_token", None)
                st.rerun()

    if not is_rem:
        if st.session_state.get("m15_confirm_del_col") != (si, sj):
            if st.button("🗑️ حذف العمود", key="m15_del_col", use_container_width=True, disabled=has_conflict):
                st.session_state["m15_confirm_del_col"] = (si, sj)
                play_delete_confirmation_whistle(f"m15_del_col_{si}_{sj}")
                st.rerun()
    else:
        st.info("💡 استخدم زر '♻️ استعادة أعمدة' لاستعادة هذا العمود بالسحب على المسقط.")

    col_shifts = st.session_state.get("m15_col_shifts", {})


    cd = []
    for (i, j) in all_cols:
        cx2, cy2 = _col_center(i, j)
        cw2, ch2 = _get_col_wh(i, j)
        orig_cn = f"C{j * len(xs) + i + 1}"
        cn2 = cn.get((i, j), f"{orig_cn} (محذوف)")
        tr2 = col_shifts.get((i, j), {})
        sx_info = tr2.get("shift_x", "متمركز")
        sy_info = tr2.get("shift_y", "متمركز")
        sx_short = "يمين (-6)" if ("جسم العمود يمين" in sx_info or sx_info.startswith("يمين")) else ("يسار (+6)" if ("جسم العمود يسار" in sx_info or sx_info.startswith("يسار")) else "متمركز")
        sy_short = "أعلى (-6)" if ("جسم العمود لأعلى" in sy_info or "جسم العمود لاعلي" in sy_info or sy_info.startswith("أعلى") or sy_info.startswith("اعلي")) else ("أسفل (+6)" if ("جسم العمود لأسفل" in sy_info or "جسم العمود لاسفل" in sy_info or sy_info.startswith("أسفل") or sy_info.startswith("اسفل")) else "متمركز")
        cd.append({
            "الاسم": cn2,
            "X (م)": round(cx2, 2),
            "Y (م)": round(cy2, 2),
            "الأبعاد (سم)": f"{int(round(cw2 * 100))}×{int(round(ch2 * 100))}",
            "الاتجاه": col_dirs.get((i, j), "NS"),
            "ترحيل X": sx_short,
            "ترحيل Y": sy_short,
            "الحالة": "🗑️ محذوف" if (i, j) in removed_cols else "✅ نشط"
        })
    with st.expander("📋 جدول الأعمدة", expanded=False):
        st.dataframe(pd.DataFrame(cd).style.format(lambda v: f"{v:.2f}" if isinstance(v, float) else v), use_container_width=True, hide_index=True)


def _section_walls():
    xs = st.session_state["m15_x_axes"]
    ys = st.session_state["m15_y_axes"]
    if len(xs) < 2 or len(ys) < 2:
        st.info("أدخل على الأقل محورين في كل اتجاه.")
        return

    removed_walls = st.session_state["m15_wall_removed"]
    wall_thick = st.session_state["m15_wall_thickness"]
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    all_walls = _get_all_walls()
    if not all_walls:
        st.info("لا توجد حوائط متصلة بين الأعمدة.")
        return

    active_walls = [wk for wk in all_walls if wk not in removed_walls]
    parapet_walls = set(st.session_state.get("m15_parapet_walls", set()))

    def _on_default_h_change():
        new_dh = float(st.session_state.get("m15_default_h_input", 3.0))
        st.session_state["m15_default_wall_height"] = new_dh
        new_ph = float(st.session_state.get("m15_parapet_wall_height", st.session_state.get("m15_parapet_h_input", 1.0)))
        wh = st.session_state.get("m15_wall_heights", {})
        for w_item in _get_all_walls():
            wh[w_item] = new_ph if _is_parapet_wall(w_item) else new_dh
        st.session_state["m15_wall_heights"] = wh
        save_settings()

    def _on_parapet_h_change():
        new_ph = float(st.session_state.get("m15_parapet_h_input", 1.0))
        st.session_state["m15_parapet_wall_height"] = new_ph
        new_dh = float(st.session_state.get("m15_default_wall_height", st.session_state.get("m15_default_h_input", 3.0)))
        wh = st.session_state.get("m15_wall_heights", {})
        for w_item in _get_all_walls():
            wh[w_item] = new_ph if _is_parapet_wall(w_item) else new_dh
        st.session_state["m15_wall_heights"] = wh
        save_settings()

    # ── 1. مدخلات الارتفاعات الرئيسية (Height Inputs) ──
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        cur_dh = float(st.session_state.get("m15_default_wall_height", 3.0))
        if "m15_default_h_input" not in st.session_state:
            st.session_state["m15_default_h_input"] = cur_dh
        dh = st.number_input(
            "ارتفاع الحائط (Wall Height)",
            min_value=0.5,
            max_value=8.0,
            value=float(st.session_state.get("m15_default_h_input", cur_dh)),
            step=0.1,
            format="%.2f",
            key="m15_default_h_input",
            on_change=_on_default_h_change,
            help="الارتفاع الافتراضي لجميع الحوائط في المشروع كارتفاع أساسي للبثق ثلاثي الأبعاد والحسابات (ترثه L1, L2, ... تلقائياً)"
        )
        if abs(dh - cur_dh) > 0.001:
            st.session_state["m15_default_wall_height"] = dh
            save_settings()

    with col_h2:
        cur_ph = float(st.session_state.get("m15_parapet_wall_height", 1.0))
        if "m15_parapet_h_input" not in st.session_state:
            st.session_state["m15_parapet_h_input"] = cur_ph
        ph = st.number_input(
            "ارتفاع دروة",
            min_value=0.2,
            max_value=5.0,
            value=float(st.session_state.get("m15_parapet_h_input", cur_ph)),
            step=0.05,
            format="%.2f",
            key="m15_parapet_h_input",
            on_change=_on_parapet_h_change,
            help="ارتفاع الاستثناء المطبق فقط على الحوائط المحددة كدروة، متجاوزاً القيمة الافتراضية"
        )
        if abs(ph - cur_ph) > 0.001:
            st.session_state["m15_parapet_wall_height"] = ph
            save_settings()

    # مزامنة سريعة لـ m15_wall_heights لضمان تطابق البيانات
    wall_heights = st.session_state.get("m15_wall_heights", {})
    for wk in all_walls:
        wall_heights[wk] = ph if _is_parapet_wall(wk) else dh
    st.session_state["m15_wall_heights"] = wall_heights

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    # ── 2. قائمة اختيار متعدد / Check-list لحوائط الدروة ──
    clean_parapets = {wk for wk in active_walls if wk in parapet_walls}
    if clean_parapets != parapet_walls:
        parapet_walls = clean_parapets
        st.session_state["m15_parapet_walls"] = clean_parapets

    current_selected = [wk for wk in active_walls if wk in parapet_walls]

    # مفتاح ديناميكي يعتمد على عدد المحاور والحوائط لمنع تشوه deserialization عند تغيير المحاور
    ms_key = f"m15_parapet_ms_{len(xs)}_{len(ys)}_{len(all_walls)}"

    def _on_parapet_ms_change():
        selected = st.session_state.get(ms_key, [])
        new_pw = set()
        for item in selected:
            t = _safe_coord_tuple(item, 4)
            if t and t in active_walls:
                new_pw.add(t)
        st.session_state["m15_parapet_walls"] = new_pw
        wh = st.session_state.get("m15_wall_heights", {})
        c_ph = float(st.session_state.get("m15_parapet_wall_height", st.session_state.get("m15_parapet_h_input", 1.0)))
        c_dh = float(st.session_state.get("m15_default_wall_height", st.session_state.get("m15_default_h_input", 3.0)))
        for w_item in _get_all_walls():
            wh[w_item] = c_ph if w_item in new_pw else c_dh
        st.session_state["m15_wall_heights"] = wh
        st.session_state.pop("m15_plan_png_b64", None)
        save_settings()

    if ms_key not in st.session_state:
        st.session_state[ms_key] = current_selected

    def _format_wall_item(wk):
        t = _safe_coord_tuple(wk, 4)
        if not t:
            return str(wk)
        lname = wm.get(t, "—")
        i1, j1, i2, j2 = t
        cs = cm.get((i1, j1), f"({i1+1},{j1+1})")
        ce = cm.get((i2, j2), f"({i2+1},{j2+1})")
        return f"{lname}: {cs} \u2192 {ce}"

    st.multiselect(
        "📋 قائمة اختيار حوائط الدروة:",
        options=active_walls,
        format_func=_format_wall_item,
        key=ms_key,
        on_change=_on_parapet_ms_change,
        help="الحوائط المحددة (Checked) تُصنف فوراً كدروة وتأخذ قيمة 'ارتفاع دروة'. الحوائط غير المحددة تستمر تلقائياً باعتماد قيمة 'ارتفاع الحائط'."
    )



    # ── نمط دمج أسماء الحوائط المتلاصقة في المسقط الأفقي المصمم ──
    st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px dashed #cbd5e1;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.90rem; font-weight:700; color:#ffffff; margin-bottom:6px;'>🏷️ نمط تسمية الحوائط المتلاصقة في المسقط الأفقي:</div>", unsafe_allow_html=True)
    cur_style = st.session_state.get("m15_merged_wall_label_style", "single")
    style_choice = st.radio(
        "نمط عرض أسماء الحوائط المتلاصقة على المسقط:",
        options=["single", "range"],
        index=0 if cur_style == "single" else 1,
        format_func=lambda x: "اسم واحد موحد (مثال: L49)" if x == "single" else "نطاق الحوائط المدمجة (مثال: L49-L51)",
        horizontal=True,
        key="m15_merged_wall_label_style_radio",
        label_visibility="collapsed",
        help="دمج أسماء مجموعات الحوائط المتلاصقة التي لا يفصلها عمود أو حائط متعامد في المسقط الأفقي المصمم."
    )
    if style_choice != cur_style:
        st.session_state["m15_merged_wall_label_style"] = style_choice
        st.session_state.pop("m15_plan_png_b64", None)
        save_settings()
        st.rerun()

    # ── 3. قائمة اختيار وتعديل مواصفات الحوائط (Multi-Wall Inspector & Modifier) ──
    ms_edit_key = f"m15_walls_edit_ms_{len(xs)}_{len(ys)}_{len(all_walls)}"

    # تنظيف القائمة الحالية لضمان صحة الإحداثيات
    cur_sel_raw = st.session_state.get(ms_edit_key, [])
    valid_sel = []
    for item in cur_sel_raw:
        t = _safe_coord_tuple(item, 4)
        if t and t in all_walls:
            valid_sel.append(t)
    if ms_edit_key not in st.session_state or valid_sel != cur_sel_raw:
        st.session_state[ms_edit_key] = valid_sel

    def _format_wall_edit_item(wk):
        t = _safe_coord_tuple(wk, 4)
        if not t:
            return str(wk)
        lname = wm.get(t, "—")
        i1, j1, i2, j2 = t
        cs = cm.get((i1, j1), f"({i1+1},{j1+1})")
        ce = cm.get((i2, j2), f"({i2+1},{j2+1})")
        th = _get_wall_thickness(t)
        st_badge = "🗑️ " if t in removed_walls else ("🧱 [دروة] " if _is_parapet_wall(t) else "")
        return f"{st_badge}{lname}: {cs} \u2192 {ce} ({th}سم)"

    # أزرار مساعدة سريعة لاختيار الحوائط
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    with c_btn1:
        if st.button("☑️ تحديد الكل", key="m15_btn_select_all_walls", use_container_width=True):
            st.session_state[ms_edit_key] = list(all_walls)
            st.rerun()
    with c_btn2:
        if st.button("🏢 تحديد الحوائط النشطة", key="m15_btn_select_active_walls", use_container_width=True):
            st.session_state[ms_edit_key] = [w for w in all_walls if w not in removed_walls]
            st.rerun()
    with c_btn3:
        if st.button("◻️ إلغاء التحديد", key="m15_btn_clear_sel_walls", use_container_width=True):
            st.session_state[ms_edit_key] = []
            st.rerun()

    sel_walls = st.multiselect(
        "📋 قائمة اختيار الحوائط لمعاينة وتعديل الخصائص:",
        options=all_walls,
        default=valid_sel,
        format_func=_format_wall_edit_item,
        key=ms_edit_key,
        help="اختر حائطاً أو أكثر لتعديل سُمكه أو تصنيفه كدروة أو حذفه/استعادته دفعة واحدة."
    )

    if sel_walls:
        sel_tuples = [_safe_coord_tuple(w, 4) for w in sel_walls if _safe_coord_tuple(w, 4) in all_walls]
        act_sel = [w for w in sel_tuples if w not in removed_walls]
        rem_sel = [w for w in sel_tuples if w in removed_walls]

        # فحص التعارض مع أي نمط تفاعلي نشط على المسقط
        active_mode = _get_active_interactive_mode()
        has_conflict = (active_mode is not None)

        # ── تأكيد حذف الحوائط المحددة ──
        if act_sel and st.session_state.get("m15_confirm_del_multi_walls"):
            play_delete_confirmation_whistle(f"m15_del_multi_walls_{tuple(sorted(act_sel))}")
            st.markdown(
                f"""<div style='background: #fff1f2; border: 2px solid #e11d48; border-radius: 8px; padding: 10px 14px; margin: 10px 0;' dir='rtl'>
                    <div style='font-weight: 800; color: #9f1239; font-size: 0.95rem;'>
                        ⚠️ هل أنت متأكد من رغبتك في حذف عدد <b>{len(act_sel)}</b> حائط محدد؟
                    </div>
                    <div style='font-size: 0.82rem; color: #be123c; margin-top: 4px;'>
                        يمكنك استعادتها في أي وقت من قسم '♻️ استعادة الحوائط المحذوفة'.
                    </div>
                </div>""",
                unsafe_allow_html=True
            )
            cyes, cno = st.columns(2)
            with cyes:
                if st.button(f"✅ نعم، تأكيد حذف {len(act_sel)} حائط", type="primary", key="m15_conf_del_multi_yes", use_container_width=True, disabled=has_conflict):
                    for w in act_sel:
                        removed_walls.add(w)
                    st.session_state["m15_wall_removed"] = removed_walls
                    st.session_state.pop("m15_confirm_del_multi_walls", None)
                    st.session_state.pop("_last_del_confirm_whistle_token", None)
                    st.session_state.pop("m15_plan_png_b64", None)
                    save_settings()
                    st.toast(f"🗑️ تم حذف {len(act_sel)} حائط بنجاح!", icon="🗑️")
                    st.rerun()
            with cno:
                if st.button("❌ إلغاء", key="m15_conf_del_multi_no", use_container_width=True):
                    st.session_state.pop("m15_confirm_del_multi_walls", None)
                    st.session_state.pop("_last_del_confirm_whistle_token", None)
                    st.rerun()

        # بطاقة ملخص الحوائط المحددة
        summary_txt = f"🎯 تم تحديد <b>{len(sel_tuples)}</b> حائط"
        if rem_sel:
            summary_txt += f" (<b>{len(act_sel)}</b> نشط | <b>{len(rem_sel)}</b> محذوف)"
        st.markdown(
            f"""<div style='background: rgba(30, 41, 59, 0.85); border: 1px solid #334155; border-radius: 8px; padding: 8px 12px; margin: 8px 0;' dir='rtl'>
                <div style='color: #38bdf8; font-weight: 700; font-size: 0.88rem;'>{summary_txt}</div>
            </div>""",
            unsafe_allow_html=True
        )

        st.markdown(
            """<style>
            /* ═══════════════════════════════════════════════════════════════════
               1. حاوية وبطاقات سُمك الحائط (العمود الأول)
               ═══════════════════════════════════════════════════════════════════ */
            div[class*="m15_multi_thick_radio"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] {
                background: linear-gradient(135deg, rgba(30, 41, 59, 0.88) 0%, rgba(15, 23, 42, 0.88) 100%) !important;
                border: 1.5px solid rgba(148, 163, 184, 0.35) !important;
                border-radius: 8px !important;
                padding: 6px 10px !important;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3) !important;
                min-height: 48px !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                width: 100% !important;
                box-sizing: border-box !important;
                margin: 0 auto !important;
            }
            div[class*="m15_multi_thick_radio"] > div[data-testid="stRadio"] {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
                margin: 0 !important;
                width: 100% !important;
            }
            div[class*="m15_multi_thick_radio"] label[data-testid="stWidgetLabel"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
                display: block !important;
                width: 100% !important;
                text-align: center !important;
                margin: 0 0 5px 0 !important;
                padding: 0 !important;
            }
            div[class*="m15_multi_thick_radio"] label[data-testid="stWidgetLabel"] p,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] p {
                color: #fde047 !important;
                font-size: 13.5px !important;
                font-weight: 700 !important;
                text-align: center !important;
                margin: 0 !important;
                line-height: 1.25 !important;
            }
            div[class*="m15_multi_thick_radio"] div[role="radiogroup"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] {
                display: flex !important;
                flex-direction: row !important;
                justify-content: center !important;
                align-items: center !important;
                gap: 8px !important;
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            div[class*="m15_multi_thick_radio"] div[role="radiogroup"] > label,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label {
                background: rgba(51, 65, 85, 0.7) !important;
                border: 1.2px solid rgba(148, 163, 184, 0.45) !important;
                border-radius: 6px !important;
                padding: 3px 8px !important;
                cursor: pointer !important;
                margin: 0 !important;
                display: inline-flex !important;
                flex-direction: row !important;
                align-items: center !important;
                gap: 6px !important;
                transition: all 0.2s ease !important;
            }
            div[class*="m15_multi_thick_radio"] div[role="radiogroup"] > label:hover,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
                border-color: #fde047 !important;
                background: rgba(51, 65, 85, 0.95) !important;
            }
            div[class*="m15_multi_thick_radio"] div[role="radiogroup"] > label[data-selected="true"],
            div[class*="m15_multi_thick_radio"] div[role="radiogroup"] > label:has(input:checked),
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label[data-selected="true"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
                background: rgba(2, 132, 199, 0.35) !important;
                border-color: #38bdf8 !important;
            }
            div[class*="m15_multi_thick_radio"] div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p {
                color: #fde047 !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                margin: 0 !important;
                padding: 0 !important;
                white-space: nowrap !important;
            }

            /* ═══════════════════════════════════════════════════════════════════
               2. بانيل تصنيف كحائط دروة (العمود الثاني)
               ═══════════════════════════════════════════════════════════════════ */
            div[class*="st-key-m15_multi_parapet_chk"],
            div.stCheckbox[class*="st-key-m15_multi_parapet_chk"],
            div.stCheckbox:has(input[id*="m15_multi_parapet_chk"]),
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stCheckbox"] {
                background: linear-gradient(135deg, rgba(30, 41, 59, 0.88) 0%, rgba(15, 23, 42, 0.88) 100%) !important;
                border: 1.5px solid rgba(148, 163, 184, 0.35) !important;
                border-radius: 8px !important;
                padding: 6px 12px !important;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3) !important;
                min-height: 48px !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                width: 100% !important;
                box-sizing: border-box !important;
                margin: 0 auto !important;
            }
            div[class*="st-key-m15_multi_parapet_chk"] label,
            div.stCheckbox[class*="st-key-m15_multi_parapet_chk"] label,
            div.stCheckbox:has(input[id*="m15_multi_parapet_chk"]) label,
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stCheckbox"] label {
                display: flex !important;
                flex-direction: column-reverse !important;
                align-items: center !important;
                justify-content: center !important;
                gap: 4px !important;
                cursor: pointer !important;
                margin: 0 auto !important;
                padding: 0 !important;
                width: auto !important;
                background: transparent !important;
            }
            div[class*="st-key-m15_multi_parapet_chk"] label p,
            div.stCheckbox[class*="st-key-m15_multi_parapet_chk"] label p,
            div.stCheckbox:has(input[id*="m15_multi_parapet_chk"]) label p,
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stCheckbox"] label p {
                color: #fde047 !important;
                font-size: 13.5px !important;
                font-weight: 700 !important;
                text-align: center !important;
                line-height: 1.25 !important;
                white-space: nowrap !important;
                margin: 0 !important;
            }

            /* ═══════════════════════════════════════════════════════════════════
               3. أزرار الحذف/الاستعادة (العمود الثالث)
               ═══════════════════════════════════════════════════════════════════ */
            .stButton:has(button[key="m15_btn_del_multi"]) > button,
            .stButton:has(button[key="m15_btn_restore_multi"]) > button,
            .stButton:has(button[key="m15_btn_del_multi_dis"]) > button,
            div[data-testid="stHorizontalBlock"] .stButton > button {
                min-height: 48px !important;
                font-size: 14px !important;
                font-weight: 700 !important;
                border-radius: 8px !important;
                padding: 6px 14px !important;
            }
            </style>""",
            unsafe_allow_html=True
        )

        # صف التحكم التفاعلي في الحوائط المحددة (3 أعمدة متوازنة الارتفاع)
        c1, c2, c3 = st.columns([1.3, 1.3, 1.0], vertical_alignment="center")

        sel_hash = sum(w[0]*1000 + w[1]*100 + w[2]*10 + w[3] for w in sel_tuples) % 100000

        with c1:
            th_vals = [_get_wall_thickness(w) for w in act_sel] if act_sel else [_WALL_THICK]
            all_12 = bool(act_sel and all(t == _WALL_THIN for t in th_vals))
            cur_th_idx = 0 if all_12 else 1

            nt = st.radio(
                "سُمك الحوائط",
                options=[_WALL_THIN, _WALL_THICK],
                index=cur_th_idx,
                format_func=lambda v: f"{v} سم",
                horizontal=True,
                label_visibility="visible",
                key=f"m15_multi_thick_radio_{sel_hash}",
                disabled=not act_sel
            )
            if act_sel and any(_get_wall_thickness(w) != nt for w in act_sel):
                for w in act_sel:
                    wall_thick[w] = nt
                st.session_state["m15_wall_thickness"] = wall_thick
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.rerun()

        with c2:
            all_p = bool(act_sel and all(_is_parapet_wall(w) for w in act_sel))
            new_is_p = st.checkbox(
                "تفعيل كحوائط دروة",
                value=all_p,
                key=f"m15_multi_parapet_chk_{sel_hash}",
                help="عند التحديد، تأخذ كافة الحوائط المحددة ارتفاع الدروة تلقائياً",
                disabled=not act_sel
            )
            if act_sel:
                needs_update = any(_is_parapet_wall(w) != new_is_p for w in act_sel)
                if needs_update:
                    pw_set = set(st.session_state.get("m15_parapet_walls", set()))
                    for w in act_sel:
                        if new_is_p:
                            pw_set.add(w)
                        else:
                            pw_set.discard(w)
                    st.session_state["m15_parapet_walls"] = pw_set
                    for w_item in all_walls:
                        wall_heights[w_item] = ph if w_item in pw_set else dh
                    st.session_state["m15_wall_heights"] = wall_heights
                    st.session_state.pop("m15_plan_png_b64", None)
                    save_settings()
                    st.rerun()

        with c3:
            if act_sel:
                if not st.session_state.get("m15_confirm_del_multi_walls"):
                    if st.button(f"🗑️ حذف ({len(act_sel)})", key="m15_btn_del_multi", use_container_width=True, disabled=has_conflict, help="حذف الحوائط النشطة المحددة"):
                        st.session_state["m15_confirm_del_multi_walls"] = True
                        play_delete_confirmation_whistle(f"m15_del_multi_walls_{tuple(sorted(act_sel))}")
                        st.rerun()
                else:
                    st.button("⏳ تأكيد بالأعلى", key="m15_btn_del_multi_dis", disabled=True, use_container_width=True)
            elif rem_sel:
                if st.button(f"♻️ استعادة ({len(rem_sel)})", key="m15_btn_restore_multi", use_container_width=True, type="primary", disabled=has_conflict):
                    for w in rem_sel:
                        removed_walls.discard(w)
                    st.session_state["m15_wall_removed"] = removed_walls
                    st.session_state.pop("m15_plan_png_b64", None)
                    save_settings()
                    st.toast(f"✅ تم استعادة {len(rem_sel)} حائط بنجاح!", icon="♻️")
                    st.rerun()

        # زر إضافي مريح لاستعادة الحوائط المحذوفة إذا كان التحديد يجمع بين حوائط نشطة ومحذوفة
        if rem_sel and act_sel:
            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
            if st.button(f"♻️ استعادة الحوائط المحذوفة فقط من التحديد ({len(rem_sel)} حائط)", key="m15_btn_restore_only_rem", use_container_width=True, disabled=has_conflict):
                for w in rem_sel:
                    removed_walls.discard(w)
                st.session_state["m15_wall_removed"] = removed_walls
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.toast(f"✅ تم استعادة {len(rem_sel)} حائط بنجاح!", icon="♻️")
                st.rerun()
    else:
        st.info("💡 اختر حائطاً أو أكثر من القائمة أعلاه لمعاينة وتعديل سُمكه أو تصنيفه كدروة أو حذفه/استعادته دفعة واحدة.")

    # ── 4. جدول الحوائط مع عمود التصنيف والارتفاع الدقيق ──
    wd = []
    for wk2 in all_walls:
        is_p = _is_parapet_wall(wk2)
        h_val = round(_get_wall_height(wk2, dh), 2)
        wd.append({
            "الحائط": _wall_display_label(wk2, cm, wm),
            "التصنيف": "🧱 دروة" if is_p else "🏢 رئيسي",
            "الطول (م)": round(_wall_length_m(wk2), 2),
            "السُمك (سم)": _get_wall_thickness(wk2),
            "الارتفاع (م)": h_val,
            "الحالة": "🗑️ محذوف" if wk2 in removed_walls else "✅ نشط"
        })
    with st.expander("📋 جدول الحوائط", expanded=False):
        def _sr(row):
            if row.get("الحالة") == "🗑️ محذوف":
                return ["background-color:rgba(148,163,184,0.12); color:#64748b;"] * len(row)
            if row.get("التصنيف") == "🧱 دروة":
                return ["background-color:rgba(2,132,199,0.12)"] * len(row)
            c2b = "rgba(239,163,104,0.18)" if row["السُمك (سم)"] == _WALL_THIN else "rgba(139,26,26,0.12)"
            return [f"background-color:{c2b}"] * len(row)
        st.dataframe(pd.DataFrame(wd).style.apply(_sr, axis=1).format(lambda v: f"{v:.2f}" if isinstance(v, float) else v), use_container_width=True, hide_index=True)

def _section_add_windows():
    """
    قسم إسقاط الشبابيك التفاعلي على الحوائط:
    1- مدخل خاص بعدد نماذج الشبابيك، وكل نموذج يتم إدخال عرض الشباك وارتفاع الشباك وجلسة الشباك.
    2- اختيار النموذج المراد إسقاطه بالماوس.
    3- زر تفعيل إسقاط الشباك بالماوس على المسقط (مركز الشباك بمركز الحائط center to center تلقائياً).
    4- ملخص الشبابيك القائمة.
    """
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    active_walls = [w for w in all_walls if w not in removed_walls]
    if not active_walls:
        st.info("⚠️ لا توجد حوائط نشطة لإسقاط الشبابيك. أضف حوائط أولاً من قسم 'إسقاط الحوائط على المحاور'.")
        return

    _ensure_opening_names()
    is_add_win_active = bool(st.session_state.get("m15_add_win_mode", False))

    win_types = st.session_state.get("m15_window_types", [])
    if not win_types:
        win_types = [{"id": "wt_1", "label": "W1", "w_cm": 100.0, "h_cm": 120.0, "sill_cm": 90.0}]
        st.session_state["m15_window_types"] = win_types

    win_type_labels = [wt["label"] for wt in win_types]
    cur_sel_type = st.session_state.get("m15_active_drop_win_type", win_type_labels[0])
    if cur_sel_type not in win_type_labels:
        cur_sel_type = win_type_labels[0]
        st.session_state["m15_active_drop_win_type"] = cur_sel_type

    sel_idx = win_type_labels.index(cur_sel_type) if cur_sel_type in win_type_labels else 0
    st.selectbox(
        "🪟 اختر نموذج الشباك المراد إسقاطه بالماوس:",
        options=win_type_labels,
        index=sel_idx,
        format_func=lambda lbl: f"{lbl} — عرض {next((w['w_cm'] for w in win_types if w['label']==lbl), 100):.0f}سم × ارتفاع {next((w['h_cm'] for w in win_types if w['label']==lbl), 120):.0f}سم (جلسة {next((w['sill_cm'] for w in win_types if w['label']==lbl), 90):.0f}سم)",
        key="m15_active_drop_win_type"
    )
    st.caption("💡 لتعديل أبعاد النماذج أو إضافة نماذج جديدة للشبابيك، انتقل إلى قسم **«نماذج الشبابيك والأبواب»** أعلاه.")

    st.markdown("<div style='font-size:0.92rem; font-weight:700; color:#ffffff; margin-top:8px; margin-bottom:10px;'>🎯 إسقاط الشباك بالماوس على المسقط الأفقي:</div>", unsafe_allow_html=True)

    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None and active_mode.get("key") != "m15_add_win_mode")

    if has_conflict:
        _render_mode_conflict_warning("إسقاط الشبابيك", active_mode, context_key="add_wins")
        st.button("🎯 تفعيل إسقاط الشباك بالماوس على الحائط", type="primary", use_container_width=True, key="m15_btn_start_add_win", disabled=True)
    elif not is_add_win_active:
        if st.button("🎯 تفعيل إسقاط الشباك بالماوس على الحائط", type="primary", use_container_width=True, key="m15_btn_start_add_win"):
            _close_all_interactive_modes()
            st.session_state["m15_add_win_mode"] = True
            st.rerun()
    else:
        if st.button("⏹️ إنهاء وضع إسقاط الشبابيك (Esc)", key="m15_btn_exit_add_win", use_container_width=True):
            st.session_state["m15_add_win_mode"] = False
            st.rerun()

    active_wins = _get_active_windows_list()
    wm_win = _get_window_name_map()
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    if active_wins:
        wins_str = ", ".join([f"<b>{wm_win.get(w.get('id'), w.get('name', 'W'))}</b> [{_wall_display_label(wk, cm, wm)}]" for (_, _, w, wk) in active_wins[:12]])
        extra_wins = f" و <b>{len(active_wins)-12}</b> شبابيك أخرى..." if len(active_wins) > 12 else ""
        panel_win_html = f"""<div style='background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.3);border-radius:8px;padding:10px 14px;margin-top:12px;' dir='rtl'>
<div style='color:#ffffff;font-weight:bold;font-size:0.9rem;margin-bottom:4px;'>ℹ️ إجمالي الشبابيك القائمة على المسقط ({len(active_wins)}):</div>
<div style='color:#e2e8f0;font-size:0.84rem;line-height:1.6;'>{wins_str}{extra_wins}</div>
<div style='color:#38bdf8;font-size:0.80rem;margin-top:4px;'>💡 لتحريك موضع أي شباك بعد إسقاطه، يمكنك سحبه وتعديل موضعه مباشرة في <b>العارض ثلاثي الأبعاد 3D</b> بالأسفل.</div>
</div>"""
        st.html(panel_win_html) if hasattr(st, "html") else st.markdown(panel_win_html, unsafe_allow_html=True)


def _section_add_doors():
    """
    قسم إسقاط الأبواب التفاعلي على الحوائط:
    1- مدخل خاص بعدد نماذج الأبواب، وكل نموذج يتم إدخال عرض الباب وارتفاع الباب.
    2- اختيار النموذج المراد إسقاطه بالماوس.
    3- زر تفعيل إسقاط الباب بالماوس على المسقط (مركز الباب بمركز الحائط center to center تلقائياً).
    4- ملخص الأبواب القائمة.
    """
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    active_walls = [w for w in all_walls if w not in removed_walls]
    if not active_walls:
        st.info("⚠️ لا توجد حوائط نشطة لإسقاط الأبواب. أضف حوائط أولاً من قسم 'إسقاط الحوائط على المحاور'.")
        return

    _ensure_opening_names()
    is_add_door_active = bool(st.session_state.get("m15_add_door_mode", False))

    door_types = st.session_state.get("m15_door_types", [])
    if not door_types:
        door_types = [{"id": "dt_1", "label": "D1", "w_cm": 90.0, "h_cm": 210.0}]
        st.session_state["m15_door_types"] = door_types

    door_type_labels = [dt["label"] for dt in door_types]
    cur_sel_type = st.session_state.get("m15_active_drop_door_type", door_type_labels[0])
    if cur_sel_type not in door_type_labels:
        cur_sel_type = door_type_labels[0]
        st.session_state["m15_active_drop_door_type"] = cur_sel_type

    sel_idx = door_type_labels.index(cur_sel_type) if cur_sel_type in door_type_labels else 0
    st.selectbox(
        "🚪 اختر نموذج الباب المراد إسقاطه بالماوس:",
        options=door_type_labels,
        index=sel_idx,
        format_func=lambda lbl: f"{lbl} — عرض {next((d['w_cm'] for d in door_types if d['label']==lbl), 90):.0f}سم × ارتفاع {next((d['h_cm'] for d in door_types if d['label']==lbl), 210):.0f}سم",
        key="m15_active_drop_door_type"
    )
    st.caption("💡 لتعديل أبعاد النماذج أو إضافة نماذج جديدة للأبواب، انتقل إلى قسم **«نماذج الشبابيك والأبواب»** أعلاه.")

    st.markdown("<div style='font-size:0.92rem; font-weight:700; color:#ffffff; margin-top:8px; margin-bottom:10px;'>🎯 إسقاط الباب بالماوس على المسقط الأفقي:</div>", unsafe_allow_html=True)

    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None and active_mode.get("key") != "m15_add_door_mode")

    if has_conflict:
        _render_mode_conflict_warning("إسقاط الأبواب", active_mode, context_key="add_doors")
        st.button("🎯 تفعيل إسقاط الباب بالماوس على الحائط", type="primary", use_container_width=True, key="m15_btn_start_add_door", disabled=True)
    elif not is_add_door_active:
        if st.button("🎯 تفعيل إسقاط الباب بالماوس على الحائط", type="primary", use_container_width=True, key="m15_btn_start_add_door"):
            _close_all_interactive_modes()
            st.session_state["m15_add_door_mode"] = True
            st.rerun()
    else:
        if st.button("⏹️ إنهاء وضع إسقاط الأبواب (Esc)", key="m15_btn_exit_add_door", use_container_width=True):
            st.session_state["m15_add_door_mode"] = False
            st.rerun()

    active_doors = _get_active_doors_list()
    wm_door = _get_door_name_map()
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    if active_doors:
        doors_str = ", ".join([f"<b>{wm_door.get(d.get('id'), d.get('name', 'D'))}</b> [{_wall_display_label(wk, cm, wm)}]" for (_, _, d, wk) in active_doors[:12]])
        extra_doors = f" و <b>{len(active_doors)-12}</b> أبواب أخرى..." if len(active_doors) > 12 else ""
        panel_door_html = f"""<div style='background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.3);border-radius:8px;padding:10px 14px;margin-top:12px;' dir='rtl'>
<div style='color:#ffffff;font-weight:bold;font-size:0.9rem;margin-bottom:4px;'>ℹ️ إجمالي الأبواب القائمة على المسقط ({len(active_doors)}):</div>
<div style='color:#e2e8f0;font-size:0.84rem;line-height:1.6;'>{doors_str}{extra_doors}</div>
<div style='color:#4ade80;font-size:0.80rem;margin-top:4px;'>💡 لتحريك موضع أي باب وتعديل موضعه بعد إسقاطه، يمكنك سحبه مباشرة في <b>العارض ثلاثي الأبعاد 3D</b> بالأسفل.</div>
</div>"""
        st.html(panel_door_html) if hasattr(st, "html") else st.markdown(panel_door_html, unsafe_allow_html=True)


def _section_delete_openings():
    """
    قسم حذف الشبابيك والأبواب:
    - اختيار الشباك أو الباب المراد حذفه من قائمة منسدلة.
    - عرض بطاقة تأكيد أنيقة للمستخدم لتأكيد عملية الحذف.
    - عند التأكيد يتم وضع علامة الحذف ونقل الفتحة تلقائياً إلى قسم '♻️ استعادة الشبابيك والأبواب المحذوفة'.
    """
    _ensure_opening_names()
    active_wins = _get_active_windows_list()
    active_doors = _get_active_doors_list()

    st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#ffffff; margin-top:8px; margin-bottom:12px;'>🗑️ حذف الشبابيك والأبواب</div>", unsafe_allow_html=True)

    if not active_wins and not active_doors:
        st.info("ℹ️ لا توجد شبابيك أو أبواب نشطة حالياً على المسقط لإجراء الحذف.")
        return

    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()

    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None)
    if has_conflict:
        _render_mode_conflict_warning("حذف الشبابيك والأبواب", active_mode, context_key="del_openings")

    c_stat1, c_stat2 = st.columns(2)
    with c_stat1:
        st.caption(f"🪟 إجمالي الشبابيك النشطة: **{len(active_wins)}**")
    with c_stat2:
        st.caption(f"🚪 إجمالي الأبواب النشطة: **{len(active_doors)}**")

    filter_type = st.radio(
        "تصفية نوع الفتحة المراد حذفها:",
        options=["الكل", "شبابيك فقط 🪟", "أبواب فقط 🚪"],
        horizontal=True,
        key="m15_del_op_filter_choice"
    )

    items = []
    if filter_type in ["الكل", "شبابيك فقط 🪟"]:
        for (_, _, w, wk) in active_wins:
            w_id = w.get("id")
            w_name = wm_win.get(w_id) or w.get("name", "W")
            w_lbl = _wall_display_label(wk, cm, wm)
            w_w = float(w.get("w_m", 1.0))
            w_h = float(w.get("h_m", 1.2))
            w_pos = float(w.get("pos_m", 0.0))
            w_sill = float(w.get("sill_m", 0.9))
            items.append({
                "id": w_id,
                "kind": "win",
                "kind_ar": "شباك",
                "icon": "🪟",
                "name": w_name,
                "wk": wk,
                "wall_label": w_lbl,
                "w_m": w_w,
                "h_m": w_h,
                "pos_m": w_pos,
                "sill_m": w_sill,
                "display": f"🪟 شباك {w_name} — حائط [{w_lbl}] (عرض {w_w*100:.0f}سم × ارتفاع {w_h*100:.0f}سم | موضع: {w_pos:.2f}م)"
            })

    if filter_type in ["الكل", "أبواب فقط 🚪"]:
        for (_, _, d, wk) in active_doors:
            d_id = d.get("id")
            d_name = wm_door.get(d_id) or d.get("name", "D")
            d_lbl = _wall_display_label(wk, cm, wm)
            d_w = float(d.get("w_m", 0.9))
            d_h = float(d.get("h_m", 2.1))
            d_pos = float(d.get("pos_m", 0.0))
            items.append({
                "id": d_id,
                "kind": "door",
                "kind_ar": "باب",
                "icon": "🚪",
                "name": d_name,
                "wk": wk,
                "wall_label": d_lbl,
                "w_m": d_w,
                "h_m": d_h,
                "pos_m": d_pos,
                "display": f"🚪 باب {d_name} — حائط [{d_lbl}] (عرض {d_w*100:.0f}سم × ارتفاع {d_h*100:.0f}سم | موضع: {d_pos:.2f}م)"
            })

    if not items:
        st.info("ℹ️ لا توجد عناصر مطابقة للتصفية المختارة.")
        return

    # قائمة منسدلة لاختيار الفتحة
    options_idx = [0] + list(range(1, len(items) + 1))
    def _format_opening_item(i):
        if i == 0:
            return "-- اختر الشباك أو الباب المراد حذفه --"
        return items[i - 1]["display"]

    cur_idx = st.session_state.get("m15_sel_delete_opening_idx", 0)
    if cur_idx >= len(options_idx):
        cur_idx = 0
        st.session_state["m15_sel_delete_opening_idx"] = 0

    sel_idx = st.selectbox(
        "🎯 اختر الشباك أو الباب المراد حذفه من القائمة المنسدلة:",
        options=options_idx,
        index=cur_idx,
        format_func=_format_opening_item,
        key="m15_sel_delete_opening_idx"
    )

    if sel_idx != 0:
        chosen = items[sel_idx - 1]
        kind_title = "الشباك" if chosen["kind"] == "win" else "الباب"
        play_delete_confirmation_whistle(f"m15_del_op_{chosen['id']}_{chosen['kind']}")
        st.markdown(
            f"""<div style='background: #fff1f2; border: 2px solid #e11d48; border-radius: 8px; padding: 10px 14px; margin: 10px 0;' dir='rtl'>
                <div style='font-weight: 800; color: #9f1239; font-size: 0.95rem; margin-bottom: 4px;'>
                    ⚠️ هل أنت متأكد من رغبتك في حذف {kind_title}: <b>{chosen["name"]}</b>؟
                </div>
                <div style='font-size: 0.84rem; color: #be123c;'>
                    الحائط: <b>{chosen["wall_label"]}</b> | الأبعاد: <b>{chosen["w_m"]*100:.0f}سم × {chosen["h_m"]*100:.0f}سم</b> | الموضع: <b>{chosen["pos_m"]:.2f}م</b>
                </div>
                <div style='font-size: 0.78rem; color: #e11d48; margin-top: 4px;'>
                    💡 سيتم نقل الفتحة إلى قسم <b>«♻️ استعادة الشبابيك والأبواب المحذوفة»</b> ويمكنك استعادتها في أي وقت.
                </div>
            </div>""",
            unsafe_allow_html=True
        )

        c_yes, c_no = st.columns(2)
        with c_yes:
            if st.button(f"🗑️ نعم، تأكيد حذف {chosen['name']}", key="m15_btn_conf_del_op", type="primary", use_container_width=True, disabled=has_conflict):
                _remove_opening_by_id(chosen["id"], kind=chosen["kind"])
                st.session_state["m15_sel_delete_opening_idx"] = 0
                st.session_state.pop("_last_del_confirm_whistle_token", None)
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.toast(f"🗑️ تم حذف {kind_title} {chosen['name']} بنجاح ونقله إلى قسم الاستعادة!", icon="🗑️")
                st.rerun()
        with c_no:
            if st.button("❌ إلغاء", key="m15_btn_cancel_del_op", use_container_width=True):
                st.session_state["m15_sel_delete_opening_idx"] = 0
                st.session_state.pop("_last_del_confirm_whistle_token", None)
                st.rerun()

    # خيار حذف جماعي إضافي
    st.markdown("<hr style='margin: 16px 0 10px 0; border: none; border-top: 1px dashed rgba(255,255,255,0.15);'>", unsafe_allow_html=True)
    with st.expander("⚠️ خيارات الحذف الجماعي للفتحات", expanded=False):
        st.caption("يمكنك حذف كافة الشبابيك أو الأبواب دفعة واحدة ونقلها جميعاً إلى قسم الاستعادة:")
        c_all_w, c_all_d = st.columns(2)
        with c_all_w:
            if active_wins and st.button("🗑️ حذف جميع الشبابيك القائمة", key="m15_btn_del_all_wins", use_container_width=True, disabled=has_conflict):
                win_store = st.session_state.get("m15_windows", {})
                for wk in win_store:
                    for w in win_store[wk]:
                        w["removed"] = True
                _resequence_openings()
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.toast("🗑️ تم حذف جميع الشبابيك ونقلها إلى قسم الاستعادة بنجاح!", icon="🗑️")
                st.rerun()
        with c_all_d:
            if active_doors and st.button("🗑️ حذف جميع الأبواب القائمة", key="m15_btn_del_all_doors", use_container_width=True, disabled=has_conflict):
                door_store = st.session_state.get("m15_doors", {})
                for wk in door_store:
                    for d in door_store[wk]:
                        d["removed"] = True
                _resequence_openings()
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.toast("🗑️ تم حذف جميع الأبواب ونقلها إلى قسم الاستعادة بنجاح!", icon="🗑️")
                st.rerun()


def _section_restore_openings():
    """
    قسم استعادة الشبابيك والأبواب المحذوفة:
    - استعراض كافة الفتحات التي تم حذفها من العارض ثلاثي الأبعاد أو المسقط.
    - إمكانية استعادة الفتحة إلى حائطها الأصلي أو اختيار حائط بديل نشط.
    - زر استعادة جماعية لكافة الفتحات المحذوفة بنقرة واحدة.
    - حماية تامة لكافة مواصفات الفتحة الأصلية (الأبعاد، الجلسة، العتب، النموذج).
    """
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    active_walls = [w for w in all_walls if w not in removed_walls]
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    _ensure_opening_names()

    deleted = _get_all_deleted_openings()

    st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#ffffff; margin-top:8px; margin-bottom:12px;'>♻️ استعادة الشبابيك والأبواب المحذوفة</div>", unsafe_allow_html=True)

    if not deleted:
        st.success("✅ لا توجد شبابيك أو أبواب محذوفة حالياً. كافة الفتحات نشطة ومسقطة في الحصر وثلاثي الأبعاد.")
        return

    n_wins = sum(1 for item in deleted if item["kind"] == "win")
    n_doors = sum(1 for item in deleted if item["kind"] == "door")

    c1, c2 = st.columns(2)
    with c1:
        st.caption(f"🪟 الشبابيك المحذوفة: **{n_wins}**")
    with c2:
        st.caption(f"🚪 الأبواب المحذوفة: **{n_doors}**")

    active_mode = _get_active_interactive_mode()
    has_conflict = (active_mode is not None)
    if has_conflict:
        _render_mode_conflict_warning("استعادة الشبابيك والأبواب", active_mode, context_key="restore_openings")

    if st.button("♻️ استعادة جميع الشبابيك والأبواب المحذوفة", key="m15_btn_restore_all_openings", type="primary", use_container_width=True, disabled=has_conflict):
        win_store = st.session_state.get("m15_windows", {})
        for wk in win_store:
            for w in win_store[wk]:
                w["removed"] = False
        door_store = st.session_state.get("m15_doors", {})
        for wk in door_store:
            for d in door_store[wk]:
                d["removed"] = False
        _resequence_openings()
        st.session_state.pop("m15_plan_png_b64", None)
        save_settings()
        st.toast("✅ تم استعادة جميع الشبابيك والأبواب المحذوفة بنجاح!", icon="♻️")
        st.rerun()

    st.markdown("<hr style='margin: 10px 0 12px 0; border: none; border-top: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    for idx, item in enumerate(deleted):
        op_id = item["id"]
        op_name = item["name"]
        kind = item["kind"]
        icon = "🪟" if kind == "win" else "🚪"
        orig_wk = item["wk"]
        orig_lbl = item["wall_label"]
        w_m = float(item["w_m"])
        h_m = float(item["h_m"])
        pos_m = float(item["pos_m"])

        with st.container():
            st.markdown(
                f"""<div style='background:rgba(30, 41, 59, 0.7);border:1px solid #334155;border-right:4px solid {"#3b82f6" if kind == "win" else "#10b981"};
                    border-radius:6px;padding:8px 12px;margin-bottom:6px;' dir='rtl'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <div>
                            <b style='font-size:1.0rem;color:#ffffff;'>{icon} {item["kind_ar"]} {op_name}</b>
                            <span style='color:#cbd5e1;font-size:0.84rem;margin-right:10px;'>
                                (عرض {w_m:.2f}م × ارتفاع {h_m:.2f}م)
                            </span>
                        </div>
                        <div style='color:#94a3b8;font-size:0.80rem;'>أصله على {orig_lbl}</div>
                    </div>
                </div>""",
                unsafe_allow_html=True
            )

            rc1, rc2 = st.columns([1.8, 1.2], vertical_alignment="center")
            with rc1:
                wall_choices = active_walls
                default_choice_idx = 0
                if orig_wk in wall_choices:
                    default_choice_idx = wall_choices.index(orig_wk)

                wall_labels = [f"حائط {_wall_display_label(w, cm, wm)}" for w in wall_choices]
                chosen_w_idx = st.selectbox(
                    f"الحائط المستهدف:",
                    options=range(len(wall_choices)),
                    index=default_choice_idx,
                    format_func=lambda i: wall_labels[i],
                    key=f"m15_restore_op_target_wall_{op_id}_{idx}",
                    label_visibility="collapsed"
                )
                target_wk = wall_choices[chosen_w_idx] if wall_choices else orig_wk

            with rc2:
                if st.button(f"♻️ استعادة {op_name}", key=f"m15_btn_restore_single_op_{op_id}_{idx}", use_container_width=True, disabled=has_conflict):
                    _restore_opening(item, target_wk)
                    st.session_state.pop("m15_plan_png_b64", None)
                    save_settings()
                    st.toast(f"✅ تم استعادة {item['kind_ar']} ({op_name}) بنجاح!", icon="♻️")
                    st.rerun()


def _compute_plaster_survey(deduction_rule=None):
    """
    حساب حصر كميات ومواد أعمال البياض (المحارة) طبقاً للكود المصري لأعمال البياض (ECP):
    - حساب مساحة كل وجه محدد (Gross Area = Length × Height).
    - قواعد خصم الفتحات:
        1. الكود المصري ECP: الفتحات حتى 4.00 م² لا تُخصم إطلاقاً (عوضاً عن بياض الجوانب والأكتاف والسوك والجلسات).
           والفتحات أكبر من 4.00 م² يُخصم ما زاد عن 4.00 م² فقط.
        2. الحصر الصافي الكامل (Net): تُخصم كامل مساحات الفتحات 100%.
    - صافي المسطح النهائي (Net Area = Gross - Deductions).
    - استهلاك الرمل: 1 م³ رمل لكل 42 م² مسطح صافي، مع 5% هالك تشغيل:
        Sand_m3 = (Net Area / 42.0) * 1.05
    - استهلاك الأسمنت: 350 كجم أسمنت لكل 1 م³ رمل (7 شكاير / م³):
        Cement_kg = Sand_m3 * 350.0
        Cement_tons = Cement_kg / 1000.0
        Cement_bags = ceil(Cement_kg / 50.0)
    """
    if deduction_rule is None:
        deduction_rule = st.session_state.get("m15_plaster_deduction_rule", "ecp")

    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    plaster_faces_map = st.session_state.get("m15_plaster_faces", {})
    default_h = float(st.session_state.get("m15_default_wall_height", 3.0))
    cm = _get_col_name_map()
    wm = _get_wall_name_map()

    rows = []
    tot_gross = 0.0
    tot_op_gross = 0.0
    tot_ded = 0.0
    tot_net = 0.0
    tot_sand = 0.0
    tot_cement_kg = 0.0

    for wk in all_walls:
        if wk in removed_walls:
            continue
        faces = plaster_faces_map.get(wk, [])
        if not faces:
            continue

        i1, j1, i2, j2 = wk
        is_h = (j1 == j2)
        valid_options = ["أعلى", "أسفل"] if is_h else ["يمين", "يسار"]
        active_faces = [f for f in faces if f in valid_options]
        if not active_faces:
            continue

        n_faces = len(active_faces)
        length = _wall_length_m(wk)
        height = _get_wall_height(wk, default_h)
        face_gross = length * height
        wall_gross = face_gross * n_faces

        # حصر الفتحات النشطة على الحائط وتطبيق قواعد الخصم
        single_face_op_gross = 0.0
        single_face_ded = 0.0
        for wi in _get_wall_windows(wk):
            if not wi.get("removed", False):
                area = float(wi.get("w_m", 1.0)) * float(wi.get("h_m", 1.2))
                single_face_op_gross += area
                if deduction_rule == "ecp":
                    single_face_ded += max(0.0, area - 4.0) if area > 4.0 else 0.0
                else:
                    single_face_ded += area
        for di in _get_wall_doors(wk):
            if not di.get("removed", False):
                area = float(di.get("w_m", 0.9)) * float(di.get("h_m", 2.1))
                single_face_op_gross += area
                if deduction_rule == "ecp":
                    single_face_ded += max(0.0, area - 4.0) if area > 4.0 else 0.0
                else:
                    single_face_ded += area

        wall_op_gross = single_face_op_gross * n_faces
        wall_ded = single_face_ded * n_faces
        wall_net = max(0.0, wall_gross - wall_ded)

        # استهلاك الرمل والأسمنت طبقاً للكود المصري
        sand_m3 = (wall_net / 42.0) * 1.05 if wall_net > 0 else 0.0
        cement_kg = sand_m3 * 350.0
        cement_tons = cement_kg / 1000.0
        cement_bags = math.ceil(cement_kg / 50.0) if cement_kg > 0 else 0

        cs = cm.get((i1, j1), f"({i1+1},{j1+1})")
        ce = cm.get((i2, j2), f"({i2+1},{j2+1})")
        lname = wm.get(wk, "—")
        display = f"{lname}: {cs}→{ce}"

        face_label = " + ".join(active_faces)
        if n_faces == 2:
            face_label = f"كلا الوجهين ({face_label})"

        rows.append({
            "الحائط": display,
            "الوجه المحدد": face_label,
            "عدد الأوجه": n_faces,
            "الطول (م)": round(length, 2),
            "الارتفاع (م)": round(height, 2),
            "إجمالي مسطح المحارة (m^2)": round(wall_gross, 2),
            "إجمالي مساحة الفتحات (m^2)": round(wall_op_gross, 2),
            "الفتحات المخصومة المعتمدة (m^2)": round(wall_ded, 2),
            "صافي مسطح المحارة النهائي (m^2)": round(wall_net, 2),
            "كمية الرمل المطلوبة (m^3)": round(sand_m3, 2),
            "كمية الأسمنت (طن)": round(cement_tons, 2),
            "شكاير الأسمنت (50 كجم)": cement_bags,
            "كمية الأسمنت المطلوبة": f"{cement_tons:.2f} طن ({cement_bags} شكارة)",
        })

        tot_gross += wall_gross
        tot_op_gross += wall_op_gross
        tot_ded += wall_ded
        tot_net += wall_net
        tot_sand += sand_m3
        tot_cement_kg += cement_kg

    tot_cement_tons = tot_cement_kg / 1000.0
    tot_cement_bags = math.ceil(tot_cement_kg / 50.0) if tot_cement_kg > 0 else 0

    return {
        "rows": rows,
        "tot_gross": tot_gross,
        "tot_op_gross": tot_op_gross,
        "tot_ded": tot_ded,
        "tot_net": tot_net,
        "tot_sand": tot_sand,
        "tot_cement_kg": tot_cement_kg,
        "tot_cement_tons": tot_cement_tons,
        "tot_cement_bags": tot_cement_bags,
        "active_walls_count": len(rows),
        "deduction_rule": deduction_rule,
    }


def _compute_wall_bounded_spaces():
    """
    حساب المساحات المحصورة بناءً على وجود الحوائط الفعلية (وليس طبقاً للمحاور فقط):
    - تعتبر الباكية (bay) مساحةً مسماةً إذا كان لها حائط واحد على الأقل على أي ضلع من أضلعها الأربعة.
    - الحوائط الجزئية (التي لا تمتد من محور إلى محور بالكامل) تُحتسب كحوائط.
    - المساحات تُرقَّم تسلسلياً بدءاً من S1, S2, S3, ...
    - تُحسب إحداثيات مركز كل مساحة وأبعادها الداخلية الصافية (بعد خصم سُمك الحوائط).
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    nx, ny = len(xs), len(ys)
    if nx < 2 or ny < 2:
        return []

    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    active_walls = set(wk for wk in all_walls if wk not in removed_walls)

    spaces = []
    space_idx = 1

    for j in range(ny - 1):
        y_bot = min(ys[j], ys[j + 1])
        y_top = max(ys[j], ys[j + 1])

        for i in range(nx - 1):
            x_left = min(xs[i], xs[i + 1])
            x_right = max(xs[i], xs[i + 1])

            # مفاتيح الحوائط الأربعة المحيطة بهذه الباكية
            wk_top   = (i, j + 1, i + 1, j + 1)
            wk_bot   = (i, j,     i + 1, j)
            wk_left  = (i, j,     i,     j + 1)
            wk_right = (i + 1, j, i + 1, j + 1)

            w_top   = _get_wall_for_segment(wk_top, active_walls)
            w_bot   = _get_wall_for_segment(wk_bot, active_walls)
            w_left  = _get_wall_for_segment(wk_left, active_walls)
            w_right = _get_wall_for_segment(wk_right, active_walls)

            has_top   = w_top is not None
            has_bot   = w_bot is not None
            has_left  = w_left is not None
            has_right = w_right is not None

            # يُعتبر مساحةً إذا وُجد حائط واحد على الأقل على أي ضلع
            wall_count = sum([has_top, has_bot, has_left, has_right])
            if wall_count == 0:
                continue

            # حساب الحدود الداخلية الصافية بعد خصم سُمك الحوائط
            if has_left:
                _min_x, _max_x, _c, _th = _get_wall_cross_bounds(w_left)
                x_inner_left = _max_x
            else:
                x_inner_left = x_left

            if has_right:
                _min_x, _max_x, _c, _th = _get_wall_cross_bounds(w_right)
                x_inner_right = _min_x
            else:
                x_inner_right = x_right

            if has_bot:
                _min_y, _max_y, _c, _th = _get_wall_cross_bounds(w_bot)
                y_inner_bot = _max_y
            else:
                y_inner_bot = y_bot

            if has_top:
                _min_y, _max_y, _c, _th = _get_wall_cross_bounds(w_top)
                y_inner_top = _min_y
            else:
                y_inner_top = y_top

            clear_span_x = max(0.10, x_inner_right - x_inner_left)
            clear_span_y = max(0.10, y_inner_top - y_inner_bot)
            clear_area_m2 = round(clear_span_x * clear_span_y, 2)
            cx = (x_inner_left + x_inner_right) / 2.0
            cy = (y_inner_bot + y_inner_top) / 2.0

            space_code = f"S{space_idx}"
            spaces.append({
                "code": space_code,
                "name": space_code,
                "id": space_code,
                "index": space_idx,
                "i": i,
                "j": j,
                "cx": cx,
                "cy": cy,
                "x_inner_left": x_inner_left,
                "x_inner_right": x_inner_right,
                "y_inner_bot": y_inner_bot,
                "y_inner_top": y_inner_top,
                "span_x": round(clear_span_x, 2),
                "span_y": round(clear_span_y, 2),
                "clear_area_m2": clear_area_m2,
                "wall_count": wall_count,
                "walls_present": {
                    "أعلى": has_top,
                    "أسفل": has_bot,
                    "يسار": has_left,
                    "يمين": has_right,
                }
            })
            space_idx += 1

    return spaces


def _compute_bays():

    """
    حساب وتقسيم المساحات الداخلية (ترقيم وتسمية الباكيات A1, A2, ...):
    - يقوم النظام بحساب المساحات المحصورة بين شبكة المحاور المتقاطعة.
    - ترتيب المساحات كودياً يبدأ بـ A1, A2, A3, ...
    - يحدد لكل مساحة إحداثيات المركز والأبعاد الأربعة والحوائط المحددة لها.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    nx, ny = len(xs), len(ys)
    if nx < 2 or ny < 2:
        return []

    bays = []
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    active_walls = [wk for wk in all_walls if wk not in removed_walls]

    bay_idx = 1

    # فرز المحاور لضمان الترتيب الإحداثي الدقيق
    # قيم Y (المحاور الأفقية X1, X2...): من j = 0 إلى ny - 2
    # قيم X (المحاور الرأسية Y1, Y2...): من i = 0 إلى nx - 2
    for j in range(ny - 1):
        y_bot = min(ys[j], ys[j + 1])
        y_top = max(ys[j], ys[j + 1])

        for i in range(nx - 1):
            x_left = min(xs[i], xs[i + 1])
            x_right = max(xs[i], xs[i + 1])

            # الحوائط المحيطة بالباكية وأوجهها الداخلية:
            # 1. أعلى: الحائط الأفقي عند j+1 بين i و i+1 -> الوجه الداخلي نحو الباكية هو "أسفل"
            # 2. أسفل: الحائط الأفقي عند j بين i و i+1 -> الوجه الداخلي نحو الباكية هو "أعلى"
            # 3. يسار: الحائط الرأسي عند i بين j و j+1 -> الوجه الداخلي نحو الباكية هو "يمين"
            # 4. يمين: الحائط الرأسي عند i+1 بين j و j+1 -> الوجه الداخلي نحو الباكية هو "يسار"
            wk_top = (i, j + 1, i + 1, j + 1)
            wk_bot = (i, j, i + 1, j)
            wk_left = (i, j, i, j + 1)
            wk_right = (i + 1, j, i + 1, j + 1)

            w_top = _get_wall_for_segment(wk_top, active_walls)
            w_bot = _get_wall_for_segment(wk_bot, active_walls)
            w_left = _get_wall_for_segment(wk_left, active_walls)
            w_right = _get_wall_for_segment(wk_right, active_walls)

            # حساب أوجه الحوائط الداخلية للباكية (Face-to-Face Inner Boundaries):
            if w_left:
                _min_x, _max_x, _c, _th = _get_wall_cross_bounds(w_left)
                x_inner_left = _max_x
            else:
                x_inner_left = x_left

            if w_right:
                _min_x, _max_x, _c, _th = _get_wall_cross_bounds(w_right)
                x_inner_right = _min_x
            else:
                x_inner_right = x_right

            if w_bot:
                _min_y, _max_y, _c, _th = _get_wall_cross_bounds(w_bot)
                y_inner_bot = _max_y
            else:
                y_inner_bot = y_bot

            if w_top:
                _min_y, _max_y, _c, _th = _get_wall_cross_bounds(w_top)
                y_inner_top = _min_y
            else:
                y_inner_top = y_top

            clear_span_x = max(0.10, x_inner_right - x_inner_left)
            clear_span_y = max(0.10, y_inner_top - y_inner_bot)
            clear_area_m2 = round(clear_span_x * clear_span_y, 2)
            cx = (x_inner_left + x_inner_right) / 2.0
            cy = (y_inner_bot + y_inner_top) / 2.0

            bay_code = f"A{bay_idx}"
            bays.append({
                "id": bay_code,
                "index": bay_idx,
                "i": i,
                "j": j,
                "x_left": x_left,
                "x_right": x_right,
                "y_bot": y_bot,
                "y_top": y_top,
                "x_inner_left": x_inner_left,
                "x_inner_right": x_inner_right,
                "y_inner_bot": y_inner_bot,
                "y_inner_top": y_inner_top,
                "span_x": round(clear_span_x, 2),
                "span_y": round(clear_span_y, 2),
                "clear_span_x": round(clear_span_x, 2),
                "clear_span_y": round(clear_span_y, 2),
                "clear_area_m2": clear_area_m2,
                "cx": cx,
                "cy": cy,
                "walls": {
                    "أعلى": {"wk": w_top or wk_top, "face": "أسفل", "exists": (w_top is not None)},
                    "أسفل": {"wk": w_bot or wk_bot, "face": "أعلى", "exists": (w_bot is not None)},
                    "يسار": {"wk": w_left or wk_left, "face": "يمين", "exists": (w_left is not None)},
                    "يمين": {"wk": w_right or wk_right, "face": "يسار", "exists": (w_right is not None)},
                },
                "label": f"{bay_code} — [X{j+1}-X{j+2} × Y{i+1}-Y{i+2}] ({clear_span_x:.2f}م × {clear_span_y:.2f}م = {clear_area_m2:.2f}م²)"
            })
            bay_idx += 1

    return bays


def _get_exterior_facades():
    """
    تحديد الحوائط الخارجية لواجهات المبنى الأربع:
    - الواجهة العلوية للمبنى: الحوائط الأفقية الخارجية بأعلى المبنى (الوجه الخارجي: أعلى)
    - الواجهة السفلية للمبنى: الحوائط الأفقية الخارجية بأسفل المبنى (الوجه الخارجي: أسفل)
    - الواجهة اليسرى للمبنى: الحوائط الرأسية الخارجية بأقصى اليسار (الوجه الخارجي: يسار)
    - الواجهة اليمنى للمبنى: الحوائط الرأسية الخارجية بأقصى اليمين (الوجه الخارجي: يمين)
    مع الحفاظ التام على استقلالية كل حائط باسمه وبياناته وحصره الهندسي دون دمج الكيانات.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    nx, ny = len(xs), len(ys)
    if nx < 2 or ny < 2:
        return {}

    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    active_walls = [wk for wk in all_walls if wk not in removed_walls]

    h_walls = [wk for wk in active_walls if wk[1] == wk[3]]
    v_walls = [wk for wk in active_walls if wk[0] == wk[2]]

    facades = {
        "top": {
            "key": "top",
            "name": "الواجهة العلوية للمبنى",
            "icon": "🔼",
            "face": "أعلى",
            "walls": []
        },
        "bottom": {
            "key": "bottom",
            "name": "الواجهة السفلية للمبنى",
            "icon": "🔽",
            "face": "أسفل",
            "walls": []
        },
        "left": {
            "key": "left",
            "name": "الواجهة اليسرى للمبنى",
            "icon": "◀️",
            "face": "يسار",
            "walls": []
        },
        "right": {
            "key": "right",
            "name": "الواجهة اليمنى للمبنى",
            "icon": "▶️",
            "face": "يمين",
            "walls": []
        },
    }

    # 1. الواجهات الأفقية (العلوية والسفلية):
    # لكل فترة أفقية بين محورين متجاورين (i إلى i+1):
    top_walls_order = []
    bot_walls_order = []
    for i in range(nx - 1):
        covering = [w for w in h_walls if min(w[0], w[2]) <= i and max(w[0], w[2]) >= i + 1]
        if covering:
            # أعلى حائط أفقي لهذه الفترة (أقصى Y)
            tw = max(covering, key=lambda w: w[1])
            if tw not in top_walls_order:
                top_walls_order.append(tw)
            # أسفل حائط أفقي لهذه الفترة (أدنى Y)
            bw = min(covering, key=lambda w: w[1])
            if bw not in bot_walls_order:
                bot_walls_order.append(bw)

    facades["top"]["walls"] = top_walls_order
    facades["bottom"]["walls"] = bot_walls_order

    # 2. الواجهات الرأسية (اليسرى واليمنى):
    # لكل فترة رأسية بين محورين متجاورين (j إلى j+1):
    left_walls_order = []
    right_walls_order = []
    for j in range(ny - 1):
        covering = [w for w in v_walls if min(w[1], w[3]) <= j and max(w[1], w[3]) >= j + 1]
        if covering:
            # أقصى يسار (أقل X)
            lw = min(covering, key=lambda w: w[0])
            if lw not in left_walls_order:
                left_walls_order.append(lw)
            # أقصى يمين (أكبر X)
            rw = max(covering, key=lambda w: w[0])
            if rw not in right_walls_order:
                right_walls_order.append(rw)

    facades["left"]["walls"] = left_walls_order
    facades["right"]["walls"] = right_walls_order

    return facades


def _section_plaster_walls():
    """
    قسم تحديد حوائط المحارة (المساحات الداخلية A1, A2... والواجهات الخارجية الأربع).
    1. تقسيم المساحات الداخلية (ترقيم وتسمية الباكيات A1, A2, ...).
    2. واجهة اختيار المحارة الداخلية (المساحات) بخيارات التوجيه:
       [يمين | يسار | أعلى | أسفل | جميع الأوجه].
    3. واجهة اختيار المحارة الخارجية (واجهات المبنى الأربع: نعم / لا)
       مع الحفاظ التام على استقلالية كل حائط باسمه وبياناته وحصره الهندسي دون دمج الكيانات.
    4. ضوابط فلسفة التهشير (خطوط مائلة 45° ومسافات معيارية بدون إطارات).
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        st.info("💡 أدخل على الأقل محورين في كل اتجاه أولاً لحساب المساحات والواجهات.")
        return

    all_walls = _get_all_walls()
    if not all_walls:
        st.info("💡 لا توجد حوائط متصلة بين المحاور.")
        return

    removed_walls = st.session_state.get("m15_wall_removed", set())
    active_walls = [wk for wk in all_walls if wk not in removed_walls]
    if not active_walls:
        st.info("💡 لا توجد حوائط نشطة بالمشروع. استعد بعض الحوائط المحذوفة أولاً.")
        return

    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    plaster_faces_map = st.session_state.setdefault("m15_plaster_faces", {})

    st.markdown(
        """<div style='background:rgba(30, 41, 59, 0.75);border:1px solid #334155;border-right:4px solid #3b82f6;
            border-radius:6px;padding:8px 12px;margin-bottom:10px;font-size:0.87rem;' dir='rtl'>
            <b style='color:#ffffff;font-size:0.95rem;'>🎨 تحديد حوائط المحارة (المساحات الداخلية والواجهات الخارجية):</b><br>
            <span style='color:#cbd5e1;'>
            حدد محارة المساحات الداخلية (الباكيات A1, A2...) بالاتجاهات الأربعة أو كامل الأوجه، ومحارة الواجهات الخارجية (نعم / لا) مع تطبيق التهشير اللحظي وحصر الخامات بدقة.
            </span>
        </div>""",
        unsafe_allow_html=True
    )

    bays = _compute_bays()

    # تنسيق التبويبات كشبكة متناسقة وأنيقة
    st.markdown(
        """<div id='m15_plaster_tabs_marker'></div>
        <style>
        /* تنسيق تبويبات المحارة بنظام grid أنيق ومتناسق */
        div[data-testid="stExpander"]:has(#m15_plaster_tabs_marker) div[data-baseweb="tab-list"],
        .m15-tabs-2x2 {
            display: grid !important;
            grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)) !important;
            gap: 8px !important;
            width: 100% !important;
        }
        div[data-testid="stExpander"]:has(#m15_plaster_tabs_marker) button[data-baseweb="tab"],
        .m15-tabs-2x2 button[data-baseweb="tab"] {
            width: 100% !important;
            text-align: center !important;
            justify-content: center !important;
            padding: 10px 8px !important;
            font-size: 0.86rem !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            border: 1.5px solid #334155 !important;
            background: rgba(15, 23, 42, 0.75) !important;
            color: #94a3b8 !important;
            white-space: normal !important;
            min-height: 48px !important;
            box-sizing: border-box !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stExpander"]:has(#m15_plaster_tabs_marker) button[data-baseweb="tab"]:hover,
        .m15-tabs-2x2 button[data-baseweb="tab"]:hover {
            border-color: #0284c7 !important;
            color: #ffffff !important;
            background: rgba(2, 132, 199, 0.22) !important;
        }
        div[data-testid="stExpander"]:has(#m15_plaster_tabs_marker) button[data-baseweb="tab"][aria-selected="true"],
        .m15-tabs-2x2 button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #1e3a8a, #0284c7) !important;
            color: #ffffff !important;
            border-color: #38bdf8 !important;
            box-shadow: 0 2px 8px rgba(2, 132, 199, 0.35) !important;
        }
        div[data-testid="stExpander"]:has(#m15_plaster_tabs_marker) div[data-baseweb="tab-highlight"],
        .m15-tabs-2x2 div[data-baseweb="tab-highlight"] {
            display: none !important;
        }
        div[data-testid="stExpander"]:has(#m15_plaster_tabs_marker) div[data-baseweb="tab-border"],
        .m15-tabs-2x2 div[data-baseweb="tab-border"] {
            display: none !important;
        }
        </style>
        <script>
        (function() {
          function applyGrid() {
            var m = document.getElementById('m15_plaster_tabs_marker');
            if (!m) return;
            var exp = m.closest('div[data-testid="stExpander"]') || m.parentElement;
            if (!exp) return;
            var tl = exp.querySelector('div[data-baseweb="tab-list"]');
            if (tl && !tl.classList.contains('m15-tabs-2x2')) {
              tl.classList.add('m15-tabs-2x2');
            }
          }
          applyGrid();
          setTimeout(applyGrid, 80);
          setTimeout(applyGrid, 250);
        })();
        </script>
        """,
        unsafe_allow_html=True
    )

    tab_quick, tab_int, tab_ext = st.tabs([
        "⚡ الاختيار السريع للحوائط الداخلية",
        "🏠 المحارة الداخلية (المساحات)",
        "🏢 المحارة الخارجية (الواجهات)"
    ])

    # ════════════════════════════════════════════════════════════
    # ⚡ التبويب 1: الاختيار السريع للحوائط الداخلية
    # ════════════════════════════════════════════════════════════
    with tab_quick:
        if not bays:
            st.info("💡 لا توجد مساحات داخلية محصورة بين المحاور.")
        else:
            st.markdown(
                """<div style='background:linear-gradient(135deg,#0f172a,#1e293b); border:1.5px solid #0284c7;
                    border-radius:8px; padding:12px 16px; margin-bottom:12px;' dir='rtl'>
                    <b style='color:#38bdf8; font-size:1.0rem;'>⚡ الاختيار السريع للحوائط الداخلية:</b><br>
                    <span style='color:#cbd5e1; font-size:0.86rem; line-height:1.7;'>
                    تحكم فوري شامل لتطبيق تهشير المحارة على جميع الأوجه الداخلية لكافة المساحات والباكيات (A1, A2...) دفعة واحدة، أو إلغاء وتفريغ المحارة الداخلية بالكامل، مع التحديث الفوري في رسم المسقط الأفقي المصمم وحسابات الحصر الهندسي.
                    </span>
                </div>""",
                unsafe_allow_html=True
            )

            # إحصائيات سريعة للباكيات
            total_bay_faces = len(bays) * 4
            active_bay_faces = 0
            for b in bays:
                for d_n in ["أعلى", "أسفل", "يسار", "يمين"]:
                    winf = b["walls"][d_n]
                    if winf["face"] in plaster_faces_map.get(winf["wk"], []):
                        active_bay_faces += 1

            c_st1, c_st2 = st.columns(2)
            with c_st1:
                st.markdown(f"""
                <div style='background:rgba(2,132,199,0.14); border:1px solid #0284c7; border-radius:6px; padding:8px 10px; text-align:center;'>
                    <div style='color:#7dd3fc; font-size:0.78rem;'>إجمالي المساحات المعرفة</div>
                    <div style='color:#ffffff; font-size:1.20rem; font-weight:900;'>{len(bays)} مساحة</div>
                </div>
                """, unsafe_allow_html=True)
            with c_st2:
                pct = int((active_bay_faces / total_bay_faces * 100)) if total_bay_faces > 0 else 0
                st.markdown(f"""
                <div style='background:rgba(16,185,129,0.14); border:1px solid #10b981; border-radius:6px; padding:8px 10px; text-align:center;'>
                    <div style='color:#6ee7b7; font-size:0.78rem;'>أوجه المحارة الداخلية المحددة</div>
                    <div style='color:#ffffff; font-size:1.20rem; font-weight:900;'>{active_bay_faces} / {total_bay_faces} ({pct}%)</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

            # 1. زر اختيار المحارة الداخلية لجميع المساحات
            if st.button("✨ اختيار المحارة الداخلية لجميع المساحات", key="m15_btn_select_all_interior_plaster", use_container_width=True):
                st.session_state.pop("m15_confirm_cancel_all_interior", None)
                pfm = st.session_state.setdefault("m15_plaster_faces", {})
                for b in bays:
                    for d_n in ["أعلى", "أسفل", "يسار", "يمين"]:
                        winf = b["walls"][d_n]
                        wk = winf["wk"]
                        face = winf["face"]
                        if wk in active_walls:
                            cur = list(pfm.get(wk, []))
                            if face not in cur:
                                cur.append(face)
                            pfm[wk] = cur
                st.session_state["m15_plaster_faces"] = pfm
                # تحديث قيم مربعات الاختيار في تبويب المساحات
                for b in bays:
                    bid = b["id"]
                    st.session_state[f"m15_cb_all_{bid}"] = True
                    st.session_state[f"m15_cb_top_{bid}"] = True
                    st.session_state[f"m15_cb_bot_{bid}"] = True
                    st.session_state[f"m15_cb_left_{bid}"] = True
                    st.session_state[f"m15_cb_right_{bid}"] = True
                save_settings()
                st.rerun()

            # 2. زر إلغاء المحارة الداخلية لجميع المساحات
            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ إلغاء المحارة الداخلية لجميع المساحات", key="m15_btn_trigger_cancel_interior", use_container_width=True):
                st.session_state["m15_confirm_cancel_all_interior"] = True
                st.session_state["m15_play_cancel_whistle"] = True
                st.session_state["_last_whistle_time"] = 0.0
                st.rerun()

            # نافذة / صندوق التأكيد بخلفية حمراء وصافرة تحذيرية وخط عريض واضح (تطلق الصافرة فوراً عند طلب الإلغاء قبل الحذف)
            if st.session_state.get("m15_confirm_cancel_all_interior", False):
                if st.session_state.pop("m15_play_cancel_whistle", False):
                    # تشغيل الصافرة التحذيرية فوراً بمجرد الضغط على الزر وظهور رسالة التحذير
                    components.html(
                        f"""
                        <audio autoplay src="data:audio/wav;base64,{ALARM_WAV_B64}" style="display:none;"></audio>
                        <script>
                        (function() {{
                            try {{
                                var AudioCtx = window.AudioContext || window.webkitAudioContext;
                                if (AudioCtx) {{
                                    var ctx = new AudioCtx();
                                    if (ctx.state === 'suspended') {{ ctx.resume(); }}
                                    var t = ctx.currentTime;
                                    var osc = ctx.createOscillator();
                                    var gain = ctx.createGain();
                                    osc.type = 'sine';
                                    osc.frequency.setValueAtTime(2600.0, t);
                                    gain.gain.setValueAtTime(0.0001, t);
                                    gain.gain.linearRampToValueAtTime(0.40, t + 0.015);
                                    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.32);
                                    osc.connect(gain);
                                    gain.connect(ctx.destination);
                                    osc.start(t);
                                    osc.stop(t + 0.32);
                                }}
                            }} catch(e) {{}}
                        }})();
                        </script>
                        """,
                        height=0,
                        width=0
                    )
                st.markdown(
                    """<div style='background: linear-gradient(135deg, #7f1d1d, #991b1b);
                        border: 3px solid #ef4444; border-radius: 12px; padding: 18px 20px;
                        margin: 14px 0 12px 0; text-align: center; box-shadow: 0 6px 20px rgba(239, 68, 68, 0.45);' dir='rtl'>
                        <div style='font-size: 2.2rem; margin-bottom: 6px;'>⚠️ 🚨 ⚠️</div>
                        <div style='color: #ffffff; font-size: 1.25rem; font-weight: 900; line-height: 1.8; margin-bottom: 10px;'>
                            تأكيد حذف وإلغاء المحارة الداخلية لجميع المساحات والحوائط الداخلية
                        </div>
                        <div style='color: #fee2e2; font-size: 0.96rem; font-weight: 700; line-height: 1.6;'>
                            هل أنت متأكد من رغبتك في حذف محارة جميع الحوائط الداخلية؟<br>
                            سيتم فوراً إزالة تهشير المحارة من كافة المساحات والباكيات الداخلية في المسقط الأفقي المصمم وتحديث كميات وجداول الحصر فورياً.
                        </div>
                    </div>""",
                    unsafe_allow_html=True
                )

                c_cf1, c_cf2 = st.columns(2)
                with c_cf1:
                    if st.button("🔥 نعم، تأكيد حذف المحارة الداخلية لجميع المساحات", key="m15_btn_confirm_cancel_all_int", use_container_width=True):
                        pfm = st.session_state.setdefault("m15_plaster_faces", {})
                        for b in bays:
                            for d_n in ["أعلى", "أسفل", "يسار", "يمين"]:
                                winf = b["walls"][d_n]
                                wk = winf["wk"]
                                face = winf["face"]
                                if wk in pfm:
                                    cur = list(pfm[wk])
                                    if face in cur:
                                        cur.remove(face)
                                    if cur:
                                        pfm[wk] = cur
                                    else:
                                        pfm.pop(wk, None)
                        st.session_state["m15_plaster_faces"] = pfm
                        # تحديث قيم مربعات الاختيار في تبويب المساحات
                        for b in bays:
                            bid = b["id"]
                            st.session_state[f"m15_cb_all_{bid}"] = False
                            st.session_state[f"m15_cb_top_{bid}"] = False
                            st.session_state[f"m15_cb_bot_{bid}"] = False
                            st.session_state[f"m15_cb_left_{bid}"] = False
                            st.session_state[f"m15_cb_right_{bid}"] = False
                        st.session_state.pop("m15_confirm_cancel_all_interior", None)
                        st.session_state.pop("m15_play_cancel_whistle", None)
                        save_settings()
                        st.rerun()

                with c_cf2:
                    if st.button("❌ تراجع / إلغاء الأمر", key="m15_btn_cancel_abort", use_container_width=True):
                        st.session_state.pop("m15_confirm_cancel_all_interior", None)
                        st.session_state.pop("m15_play_cancel_whistle", None)
                        st.rerun()

    # ════════════════════════════════════════════════════════════
    # 🏠 التبويب 2: المحارة الداخلية (المساحات والباكيات A1, A2...)
    # ════════════════════════════════════════════════════════════
    with tab_int:
        if not bays:
            st.info("💡 لا توجد مساحات داخلية محصورة بين المحاور.")
        else:
            # 1. القائمة المنسدلة لاختيار المساحة
            bay_labels = [b["label"] for b in bays]
            _safe_idx("m15_sel_bay_idx", len(bays))
            sel_bay_idx = st.selectbox(
                "اختر المساحة الداخلية (الباكية)",
                options=range(len(bays)),
                format_func=lambda idx: bay_labels[idx],
                key="m15_sel_bay_idx"
            )
            sel_bay = bays[sel_bay_idx]
            bay_id = sel_bay["id"]

            # معلومات الحوائط المحيطة بالباكية
            w_top_info = sel_bay["walls"]["أعلى"]
            w_bot_info = sel_bay["walls"]["أسفل"]
            w_left_info = sel_bay["walls"]["يسار"]
            w_right_info = sel_bay["walls"]["يمين"]

            wk_top, f_top = w_top_info["wk"], w_top_info["face"]
            wk_bot, f_bot = w_bot_info["wk"], w_bot_info["face"]
            wk_left, f_left = w_left_info["wk"], w_left_info["face"]
            wk_right, f_right = w_right_info["wk"], w_right_info["face"]

            ex_top = (wk_top in active_walls)
            ex_bot = (wk_bot in active_walls)
            ex_left = (wk_left in active_walls)
            ex_right = (wk_right in active_walls)

            cur_top = (f_top in plaster_faces_map.get(wk_top, [])) if ex_top else False
            cur_bot = (f_bot in plaster_faces_map.get(wk_bot, [])) if ex_bot else False
            cur_left = (f_left in plaster_faces_map.get(wk_left, [])) if ex_left else False
            cur_right = (f_right in plaster_faces_map.get(wk_right, [])) if ex_right else False

            ex_count = sum([ex_top, ex_bot, ex_left, ex_right])
            on_count = sum([cur_top, cur_bot, cur_left, cur_right])
            cur_all = (ex_count > 0 and on_count == ex_count)

            name_top = wm.get(wk_top, _wall_display_label(wk_top, cm, wm)) if ex_top else "—"
            name_bot = wm.get(wk_bot, _wall_display_label(wk_bot, cm, wm)) if ex_bot else "—"
            name_left = wm.get(wk_left, _wall_display_label(wk_left, cm, wm)) if ex_left else "—"
            name_right = wm.get(wk_right, _wall_display_label(wk_right, cm, wm)) if ex_right else "—"

            # بطاقة تعريفية للمساحة المحددة
            st.markdown(f"""
            <div style='background:linear-gradient(135deg,#0f172a,#1e293b); border:1.5px solid #0284c7; border-radius:8px; padding:10px 14px; margin-bottom:12px;' dir='rtl'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <b style='color:#38bdf8; font-size:1.02rem;'>🏷️ المساحة {bay_id} [الأبعاد: {sel_bay["span_x"]:.2f}م × {sel_bay["span_y"]:.2f}م]</b>
                    <span style='background:rgba(2,132,199,0.20); color:#7dd3fc; border:1px solid #0284c7; padding:2px 10px; border-radius:12px; font-size:0.80rem; font-weight:bold;'>
                        المسطح التقريبي: {(sel_bay["span_x"] * sel_bay["span_y"]):.2f} م²
                    </span>
                </div>
                <div style='color:#94a3b8; font-size:0.82rem; margin-top:5px;'>
                    الحوائط المحيطة: أعلى (<b>{name_top}</b>) | أسفل (<b>{name_bot}</b>) | يسار (<b>{name_left}</b>) | يمين (<b>{name_right}</b>)
                </div>
            </div>
            """, unsafe_allow_html=True)

            # دالة تحديث وجه محدد
            def _toggle_bay_face(wk, face, enable):
                pfm = st.session_state.setdefault("m15_plaster_faces", {})
                cur = list(pfm.get(wk, []))
                if enable:
                    if face not in cur: cur.append(face)
                else:
                    if face in cur: cur.remove(face)
                pfm[wk] = cur
                st.session_state["m15_plaster_faces"] = pfm
                save_settings()

            # دالة تفعيل/إلغاء جميع الأوجه للمساحة
            def _toggle_bay_all(enable):
                pfm = st.session_state.setdefault("m15_plaster_faces", {})
                for d_n in ["أعلى", "أسفل", "يسار", "يمين"]:
                    w_inf = sel_bay["walls"][d_n]
                    w_k = w_inf["wk"]
                    f_c = w_inf["face"]
                    if w_k in active_walls:
                        cur = list(pfm.get(w_k, []))
                        if enable:
                            if f_c not in cur: cur.append(f_c)
                        else:
                            if f_c in cur: cur.remove(f_c)
                        pfm[w_k] = cur
                st.session_state["m15_plaster_faces"] = pfm
                save_settings()

            # مفاتيح الويدجت الخاصة بالباكية
            k_all = f"m15_cb_all_{bay_id}"
            k_top = f"m15_cb_top_{bay_id}"
            k_bot = f"m15_cb_bot_{bay_id}"
            k_left = f"m15_cb_left_{bay_id}"
            k_right = f"m15_cb_right_{bay_id}"

            # 5. خيار جميع الأوجه (تحديد جميع الأوجه الأربعة دفعة واحدة)
            def _on_all_change():
                val = st.session_state.get(k_all, False)
                _toggle_bay_all(val)
                st.session_state[k_top] = val if ex_top else False
                st.session_state[k_bot] = val if ex_bot else False
                st.session_state[k_left] = val if ex_left else False
                st.session_state[k_right] = val if ex_right else False

            st.checkbox(
                "✨ 5. جميع الأوجه (تحديد جميع الأوجه الأربعة دفعة واحدة)",
                value=cur_all,
                key=k_all,
                on_change=_on_all_change,
                help="تطبيق التهشير على الأوجه الداخلية الأربعة المحيطة بهذه المساحة فوراً."
            )

            st.markdown("<div style='margin-top:6px; font-weight:bold; font-size:0.88rem; color:#cbd5e1;'>خيارات توجيه المحارة الفردية للمساحة:</div>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)

            with col_b1:
                # 1. يمين
                def _on_right_change():
                    _toggle_bay_face(wk_right, f_right, st.session_state.get(k_right, False))
                lbl_r = f"▶️ 1. يمين (الحائط {name_right})" if ex_right else "▶️ 1. يمين (لا يوجد حائط)"
                st.checkbox(lbl_r, value=cur_right, key=k_right, on_change=_on_right_change, disabled=not ex_right)

                # 2. يسار
                def _on_left_change():
                    _toggle_bay_face(wk_left, f_left, st.session_state.get(k_left, False))
                lbl_l = f"◀️ 2. يسار (الحائط {name_left})" if ex_left else "◀️ 2. يسار (لا يوجد حائط)"
                st.checkbox(lbl_l, value=cur_left, key=k_left, on_change=_on_left_change, disabled=not ex_left)

            with col_b2:
                # 3. أعلى
                def _on_top_change():
                    _toggle_bay_face(wk_top, f_top, st.session_state.get(k_top, False))
                lbl_t = f"🔼 3. أعلى (الحائط {name_top})" if ex_top else "🔼 3. أعلى (لا يوجد حائط)"
                st.checkbox(lbl_t, value=cur_top, key=k_top, on_change=_on_top_change, disabled=not ex_top)

                # 4. أسفل
                def _on_bot_change():
                    _toggle_bay_face(wk_bot, f_bot, st.session_state.get(k_bot, False))
                lbl_b = f"🔽 4. أسفل (الحائط {name_bot})" if ex_bot else "🔽 4. أسفل (لا يوجد حائط)"
                st.checkbox(lbl_b, value=cur_bot, key=k_bot, on_change=_on_bot_change, disabled=not ex_bot)

            # أزرار تحكم سريعة إضافية
            c_q1, c_q2 = st.columns(2)
            with c_q1:
                if st.button(f"✨ تفعيل كافة أوجه المساحة {bay_id}", key=f"m15_btn_all_bay_{bay_id}", use_container_width=True):
                    _toggle_bay_all(True)
                    st.session_state[k_all] = True
                    st.session_state[k_top] = ex_top
                    st.session_state[k_bot] = ex_bot
                    st.session_state[k_left] = ex_left
                    st.session_state[k_right] = ex_right
                    st.rerun()
            with c_q2:
                if st.button(f"🧹 تفريغ محارة المساحة {bay_id}", key=f"m15_btn_clear_bay_{bay_id}", use_container_width=True):
                    _toggle_bay_all(False)
                    st.session_state[k_all] = False
                    st.session_state[k_top] = False
                    st.session_state[k_bot] = False
                    st.session_state[k_left] = False
                    st.session_state[k_right] = False
                    st.rerun()

    # ════════════════════════════════════════════════════════════
    # 🏢 التبويب 3: المحارة الخارجية (واجهات المبنى)
    # ════════════════════════════════════════════════════════════
    with tab_ext:
        facades = _get_exterior_facades()
        if not facades:
            st.info("💡 لا توجد حوائط نشطة لتحديد الواجهات الخارجية.")
        else:
            st.markdown(
                """<div style='color:#cbd5e1; font-size:0.85rem; margin-bottom:10px;' dir='rtl'>
                نظام مستقل لعزل الواجهات الخارجية مع الحفاظ التام على استقلالية كل حائط باسمه وبياناته وحصره دون دمج:
                </div>""",
                unsafe_allow_html=True
            )

            def _apply_facade(fac_walls, fac_face, is_yes):
                pfm = st.session_state.setdefault("m15_plaster_faces", {})
                for wk in fac_walls:
                    cur = list(pfm.get(wk, []))
                    if is_yes:
                        if fac_face not in cur: cur.append(fac_face)
                    else:
                        if fac_face in cur: cur.remove(fac_face)
                    pfm[wk] = cur
                st.session_state["m15_plaster_faces"] = pfm
                save_settings()

            for f_key in ["right", "left", "top", "bottom"]:
                fac = facades[f_key]
                fac_name = fac["name"]
                fac_icon = fac["icon"]
                fac_face = fac["face"]
                fac_walls = fac["walls"]

                w_names = [wm.get(wk, _wall_display_label(wk, cm, wm)) for wk in fac_walls]
                total_len = sum(_wall_length_m(wk) for wk in fac_walls)
                is_active = (all(fac_face in plaster_faces_map.get(wk, []) for wk in fac_walls) if fac_walls else False)

                st.markdown(f"""
                <div style='background:#1e293b; border:1px solid #334155; border-right:4px solid #3b82f6; border-radius:8px; padding:10px 14px; margin-top:10px; margin-bottom:4px;' dir='rtl'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <b style='color:#f8fafc; font-size:0.95rem;'>{fac_icon} {fac_name}</b>
                        <span style='background:#0f172a; color:#38bdf8; padding:2px 10px; border-radius:12px; font-size:0.80rem; border:1px solid #0284c7;'>
                            الطول: {total_len:.2f}م | {len(fac_walls)} حوائط مستقلة
                        </span>
                    </div>
                    <div style='color:#94a3b8; font-size:0.82rem; margin-top:4px;'>
                        الحوائط الإنشائية المكونة: <b>{', '.join(w_names) if w_names else 'لا يوجد'}</b> (الوجه الخارجي: <b>{fac_face}</b>)
                    </div>
                </div>
                """, unsafe_allow_html=True)

                r_key = f"m15_ext_radio_{f_key}"
                cur_idx = 0 if is_active else 1

                def _make_ext_cb(w_list, f_face, k_radio):
                    def _cb():
                        ans = st.session_state.get(k_radio, "لا")
                        _apply_facade(w_list, f_face, (ans == "نعم"))
                    return _cb

                st.radio(
                    f"حالة محارة {fac_name}:",
                    options=["نعم", "لا"],
                    index=cur_idx,
                    horizontal=True,
                    key=r_key,
                    on_change=_make_ext_cb(fac_walls, fac_face, r_key),
                    help=f"تطبيق التهشير على كامل حوائط {fac_name} مع الحفاظ على استقلالية كل حائط."
                )

            st.divider()
            c_f_all1, c_f_all2 = st.columns(2)
            with c_f_all1:
                if st.button("✨ تفعيل جميع الواجهات الخارجية الأربع (نعم للكل)", key="m15_btn_ext_all_yes", use_container_width=True):
                    for f_k in ["right", "left", "top", "bottom"]:
                        _apply_facade(facades[f_k]["walls"], facades[f_k]["face"], True)
                        st.session_state[f"m15_ext_radio_{f_k}"] = "نعم"
                    st.rerun()
            with c_f_all2:
                if st.button("🧹 إلغاء محارة جميع الواجهات الخارجية (لا للكل)", key="m15_btn_ext_all_no", use_container_width=True):
                    for f_k in ["right", "left", "top", "bottom"]:
                        _apply_facade(facades[f_k]["walls"], facades[f_k]["face"], False)
                        st.session_state[f"m15_ext_radio_{f_k}"] = "لا"
                    st.rerun()

    # ════════════════════════════════════════════════════════════
    # 🏷️ زر تسمية المساحات بناءً على وجود الحوائط الفعلية
    # ════════════════════════════════════════════════════════════
    st.markdown("<hr style='margin: 16px 0 14px 0; border: none; border-top: 2px dashed #334155;'>", unsafe_allow_html=True)
    st.markdown(
        """<div style='background:linear-gradient(135deg,#0f172a,#1e293b); border:1.5px solid #7c3aed;
            border-radius:8px; padding:10px 14px; margin-bottom:10px;' dir='rtl'>
            <b style='color:#c4b5fd; font-size:0.97rem;'>🏷️ تسمية المساحات طبقاً للحوائط:</b><br>
            <span style='color:#cbd5e1; font-size:0.84rem; line-height:1.7;'>
            اضغط الزر أدناه لتسمية المساحات الداخلية طبقاً لوجود الحوائط الفعلية وليس طبقاً للمحاور.
            تُعتبر أي باكية مساحةً مسماةً إذا كان لها حائط واحد على الأقل على أي ضلع من أضلعها الأربعة،
            حتى لو لم يكتمل الحائط إلى المحاور المجاورة.
            </span>
        </div>""",
        unsafe_allow_html=True
    )

    named_spaces_cur = st.session_state.get("m15_named_spaces", [])
    c_name1, c_name2 = st.columns([2, 1])
    with c_name1:
        if st.button(
            "🏷️ اضغط لتسمية المساحات للمحارة",
            key="m15_btn_label_spaces_by_walls",
            use_container_width=True,
            type="primary",
            help="يحسب الكود المساحات المحصورة بناءً على الحوائط الموجودة ويضعها كتسميات على المسقط الأفقي."
        ):
            computed = _compute_wall_bounded_spaces()
            if computed:
                st.session_state["m15_named_spaces"] = computed
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.toast(f"✅ تم تسمية {len(computed)} مساحة بناءً على الحوائط الموجودة!", icon="🏷️")
                st.rerun()
            else:
                st.toast("⚠️ لا توجد حوائط نشطة لتحديد المساحات. أضف حوائط أولاً.", icon="⚠️")

    with c_name2:
        if named_spaces_cur:
            if st.button(
                "🗑️ حذف التسميات",
                key="m15_btn_clear_named_spaces",
                use_container_width=True,
                help="إزالة جميع تسميات المساحات من المسقط الأفقي."
            ):
                st.session_state["m15_named_spaces"] = []
                st.session_state.pop("m15_plan_png_b64", None)
                save_settings()
                st.toast("🗑️ تم حذف جميع تسميات المساحات.", icon="🗑️")
                st.rerun()

    # عرض التسميات الحالية إن وجدت
    if named_spaces_cur:
        n_count = len(named_spaces_cur)
        st.markdown(
            f"""<div style='background:rgba(124,58,237,0.12); border:1px solid #7c3aed; border-radius:6px;
                padding:8px 12px; margin-top:6px; font-size:0.84rem; color:#c4b5fd;' dir='rtl'>
                ✅ يوجد حالياً <b style='color:#ffffff;'>{n_count} مساحة مسماة</b> معروضة على المسقط الأفقي.
                (التسميات: {", ".join([s["name"] for s in named_spaces_cur[:8]])}{" ..." if n_count > 8 else ""})
            </div>""",
            unsafe_allow_html=True
        )

    # ملخص كميات المحارة التنفيذي السريع في قسم التحديد
    p_summary = _compute_plaster_survey()

    if p_summary["rows"]:
        st.markdown(f"""
        <div style='background:linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border:1.5px solid #0284c7; border-radius:8px; padding:12px 16px; margin-top:12px;' dir='rtl'>
            <div style='display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155; padding-bottom:8px; margin-bottom:8px;'>
                <b style='color:#38bdf8; font-size:0.95rem;'>📊 ملخص كميات المحارة التنفيذية (طبقاً للكود المصري ECP):</b>
                <span style='background:#0284c7; color:#fff; font-size:0.75rem; font-weight:bold; padding:2px 8px; border-radius:10px;'>
                    {p_summary['active_walls_count']} حائط مشمول
                </span>
            </div>
            <div style='display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px; font-size:0.84rem; color:#cbd5e1;'>
                <div>• إجمالي المسطح: <b style='color:#93c5fd;'>{p_summary['tot_gross']:.2f} م²</b></div>
                <div>• الفتحات المخصومة: <b style='color:#f87171;'>{p_summary['tot_ded']:.2f} م²</b></div>
                <div>• صافي المسطح: <b style='color:#4ade80;'>{p_summary['tot_net']:.2f} م²</b></div>
                <div>• الرمل (5% هالك): <b style='color:#fde047;'>{p_summary['tot_sand']:.2f} م³</b></div>
                <div>• الأسمنت: <b style='color:#67e8f9;'>{p_summary['tot_cement_tons']:.2f} طن</b> <span style='color:#94a3b8;'>({p_summary['tot_cement_bags']} شكارة)</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.82rem;color:#94a3b8;margin-top:8px;text-align:center;'>📋 تم نقل وتخصيص <b>جدول حصر وخامات البياض التفصيلي</b> في قسم منفصل مطوي أسفل المسقط الأفقي قبل قسم الأسعار.</div>", unsafe_allow_html=True)


def _section_plaster_boq():
    """
    قسم منفصل مطوي: جدول الحصر وخامات البياض (طبقاً للكود المصري ECP):
    - جدول تفصيلي لكل حائط والأوجه المحددة ومساحات الخصم وصافي المسطح والأسمنت والرمل.
    - خيار تحديد أسلوب خصم الفتحات (الكود المصري ECP مقابل الخصم الصافي الكامل).
    - ملخص تنفيذي بارز لكميات المحارة الإجمالية.
    - زر تحميل جدول الحصر بصيغة CSV.
    """
    # ── أسلوب حصر وخصم الفتحات في أعمال البياض ──
    rule_opts = [
        "📐 الكود المصري ECP (الفتحات ≤ 4.0 م² لا تُخصم، وما زاد عنها يُخصم الفارق)",
        "✂️ الحصر الصافي الكامل (خصم كامل مساحة الفتحات دون استثناء)"
    ]
    cur_rule_str = st.session_state.get("m15_plaster_deduction_rule_str", rule_opts[0])
    if cur_rule_str not in rule_opts:
        cur_rule_str = rule_opts[0]

    col_r1, col_r2 = st.columns([2.2, 1.0], vertical_alignment="center")
    with col_r1:
        chosen_rule_str = st.radio(
            "📐 طريقة خصم فتحات الأبواب والشبابيك في حصر البياض:",
            options=rule_opts,
            index=rule_opts.index(cur_rule_str),
            key="m15_plaster_rule_radio",
            horizontal=True,
            help="طبقاً للكود المصري للبياض، الفتحات حتى 4 م² لا تخصم لأن مساحتها تقابل تكلفة ومسطح بياض الجوانب والأكتاف والسوك والجلسات."
        )
    with col_r2:
        rule_key = "ecp" if "الكود المصري" in chosen_rule_str else "net"
        st.session_state["m15_plaster_deduction_rule"] = rule_key
        st.session_state["m15_plaster_deduction_rule_str"] = chosen_rule_str

    p_res = _compute_plaster_survey(deduction_rule=rule_key)
    p_rows = p_res["rows"]

    if not p_rows:
        st.info("💡 لم يتم تفعيل المحارة لأي حائط بعد. قم باختيار أوجه المحارة من قسم '7️⃣ تحديد حوائط المحارة' لتظهر النتائج والكميات هنا.")
    else:
        display_rows = []
        for r in p_rows:
            display_rows.append({
                "الحائط": r["الحائط"],
                "الوجه المحدد": r["الوجه المحدد"],
                "عدد الأوجه": r["عدد الأوجه"],
                "الطول (م)": r["الطول (م)"],
                "الارتفاع (م)": r["الارتفاع (م)"],
                "إجمالي المسطح (م²)": r["إجمالي مسطح المحارة (m^2)"],
                "مساحة الفتحات (م²)": r["إجمالي مساحة الفتحات (m^2)"],
                "الخصم المعتمد (م²)": r["الفتحات المخصومة المعتمدة (m^2)"],
                "صافي مسطح المحارة (م²)": r["صافي مسطح المحارة النهائي (m^2)"],
                "الرمل المطلوب (م³)": r["كمية الرمل المطلوبة (m^3)"],
                "الأسمنت المطلوب": r["كمية الأسمنت المطلوبة"],
            })

        tot_display = {
            "الحائط": "✅ الإجمالي العام",
            "الوجه المحدد": f"{sum(r['عدد الأوجه'] for r in p_rows)} وجه",
            "عدد الأوجه": sum(r["عدد الأوجه"] for r in p_rows),
            "الطول (م)": round(sum(r["الطول (م)"] for r in p_rows), 2),
            "الارتفاع (م)": "—",
            "إجمالي المسطح (م²)": round(p_res["tot_gross"], 2),
            "مساحة الفتحات (م²)": round(p_res["tot_op_gross"], 2),
            "الخصم المعتمد (م²)": round(p_res["tot_ded"], 2),
            "صافي مسطح المحارة (م²)": round(p_res["tot_net"], 2),
            "الرمل المطلوب (م³)": round(p_res["tot_sand"], 2),
            "الأسمنت المطلوب": f"{p_res['tot_cement_tons']:.2f} طن ({p_res['tot_cement_bags']} شكارة)",
        }

        df_p = pd.DataFrame(display_rows + [tot_display])
        def _st_plaster(row):
            if row["الحائط"] == "✅ الإجمالي العام":
                return ["background-color:#1e3a8a;color:white;font-weight:bold"] * len(row)
            return [""] * len(row)

        st.dataframe(df_p.style.apply(_st_plaster, axis=1).format(lambda v: f"{v:.2f}" if isinstance(v, float) else v), use_container_width=True, hide_index=True)

        cb_p = io.StringIO()
        df_p.to_csv(cb_p, index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ تحميل جدول حصر المحارة CSV",
            data=cb_p.getvalue().encode("utf-8-sig"),
            file_name="plaster_survey_ecp.csv",
            mime="text/csv",
            key="m15_dl_plaster_sec"
        )

        rule_badge = "الكود المصري ECP (خصم الفتحات > 4م²)" if rule_key == "ecp" else "الحصر الصافي الكامل (خصم كافة الفتحات)"
        st.markdown(f"""
        <div style='background:linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border:1.5px solid #0284c7; border-radius:8px; padding:14px 18px; margin-top:12px;' dir='rtl'>
            <div style='display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155; padding-bottom:8px; margin-bottom:10px;'>
                <b style='color:#38bdf8; font-size:0.98rem;'>📊 ملخص كميات المحارة التنفيذية ({rule_badge}):</b>
                <span style='background:#0284c7; color:#fff; font-size:0.75rem; font-weight:bold; padding:3px 10px; border-radius:12px;'>
                    {p_res['active_walls_count']} حائط مشمول
                </span>
            </div>
            <div style='display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:10px; font-size:0.86rem; color:#cbd5e1;'>
                <div>• إجمالي مسطح البياض: <b style='color:#93c5fd;'>{p_res['tot_gross']:.2f} م²</b></div>
                <div>• إجمالي الفتحات: <b style='color:#fbbf24;'>{p_res['tot_op_gross']:.2f} م²</b></div>
                <div>• الخصم المعتمد: <b style='color:#f87171;'>{p_res['tot_ded']:.2f} م²</b></div>
                <div>• صافي مسطح البياض: <b style='color:#4ade80;'>{p_res['tot_net']:.2f} م²</b></div>
                <div>• الرمل (5% هالك): <b style='color:#fde047;'>{p_res['tot_sand']:.2f} م³</b></div>
                <div>• الأسمنت: <b style='color:#67e8f9;'>{p_res['tot_cement_tons']:.2f} طن</b> <span style='color:#94a3b8;'>({p_res['tot_cement_bags']} شكارة)</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


_FLOATING_PLAN_CSS = """
/* Dragging overlay helper: prevents iframes from swallowing mouse movements */
body.m12-dragging-active iframe {
    pointer-events: none !important;
}

#m12-floating-plan-modal {
    position: fixed;
    top: 75px;
    right: 35px;
    width: 760px;
    height: 560px;
    min-width: 280px;
    min-height: 200px;
    max-width: 98vw;
    max-height: 96vh;
    background: rgba(15, 23, 42, 0.96);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1.5px solid rgba(59, 130, 246, 0.45);
    border-radius: 12px;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.75), 0 0 30px rgba(59, 130, 246, 0.22);
    z-index: 999999;
    display: none;
    flex-direction: column;
    overflow: visible;
    resize: none;
    user-select: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Kufi Arabic", sans-serif;
    direction: rtl;
    box-sizing: border-box;
}

#m12-floating-plan-modal.m12-show {
    display: flex !important;
}

/* 8-Way Resize Handles */
.m12-rh {
    position: absolute;
    z-index: 120;
    touch-action: none;
    box-sizing: border-box;
}
.m12-rh-n { top: -6px; left: 24px; right: 24px; height: 10px; cursor: ns-resize; }
.m12-rh-s { bottom: -6px; left: 24px; right: 24px; height: 10px; cursor: ns-resize; }
.m12-rh-w { left: -6px; top: 24px; bottom: 24px; width: 10px; cursor: ew-resize; }
.m12-rh-e { right: -6px; top: 24px; bottom: 24px; width: 10px; cursor: ew-resize; }
.m12-rh-nw { top: -7px; left: -7px; width: 22px; height: 22px; cursor: nwse-resize; z-index: 125; }
.m12-rh-ne { top: -7px; right: -7px; width: 22px; height: 22px; cursor: nesw-resize; z-index: 125; }
.m12-rh-sw { bottom: -7px; left: -7px; width: 22px; height: 22px; cursor: nesw-resize; z-index: 125; }
.m12-rh-se { bottom: -7px; right: -7px; width: 22px; height: 22px; cursor: nwse-resize; z-index: 125; }

.m12-corner-mark {
    position: absolute;
    width: 9px;
    height: 9px;
    pointer-events: none;
    opacity: 0.7;
    transition: opacity 0.15s, border-color 0.15s;
}
.m12-rh:hover .m12-corner-mark, .m12-rh.m12-rh-active .m12-corner-mark {
    opacity: 1;
    border-color: #60a5fa !important;
}
.m12-rh-nw .m12-corner-mark { top: 4px; left: 4px; border-top: 2.5px solid rgba(147, 197, 253, 0.85); border-left: 2.5px solid rgba(147, 197, 253, 0.85); border-top-left-radius: 4px; }
.m12-rh-ne .m12-corner-mark { top: 4px; right: 4px; border-top: 2.5px solid rgba(147, 197, 253, 0.85); border-right: 2.5px solid rgba(147, 197, 253, 0.85); border-top-right-radius: 4px; }
.m12-rh-sw .m12-corner-mark { bottom: 4px; left: 4px; border-bottom: 2.5px solid rgba(147, 197, 253, 0.85); border-left: 2.5px solid rgba(147, 197, 253, 0.85); border-bottom-left-radius: 4px; }
.m12-rh-se .m12-corner-mark { bottom: 4px; right: 4px; border-bottom: 2.5px solid rgba(147, 197, 253, 0.85); border-right: 2.5px solid rgba(147, 197, 253, 0.85); border-bottom-right-radius: 4px; }

.m12-rh-n:hover, .m12-rh-n.m12-rh-active { border-top: 2.5px solid #60a5fa; }
.m12-rh-s:hover, .m12-rh-s.m12-rh-active { border-bottom: 2.5px solid #60a5fa; }
.m12-rh-w:hover, .m12-rh-w.m12-rh-active { border-left: 2.5px solid #60a5fa; }
.m12-rh-e:hover, .m12-rh-e.m12-rh-active { border-right: 2.5px solid #60a5fa; }

.m12-fp-header {
    position: relative;
    z-index: 150;
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-bottom: 1.5px solid rgba(59, 130, 246, 0.3);
    border-top-left-radius: 11px;
    border-top-right-radius: 11px;
    padding: 8px 12px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 6px 8px;
    cursor: grab;
    direction: rtl;
    flex-shrink: 0;
    box-sizing: border-box;
    width: 100%;
    max-width: 100%;
}
.m12-fp-header:active {
    cursor: grabbing;
}
.m12-fp-title-wrap {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    font-size: 13px;
    font-weight: 700;
    color: #93c5fd;
    flex: 1 1 auto;
    min-width: 0;
    max-width: 100%;
}
.m12-fp-title-text {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 1;
}
.m12-fp-badge {
    font-size: 10.5px;
    background: rgba(59, 130, 246, 0.2);
    color: #93c5fd;
    padding: 2px 7px;
    border-radius: 5px;
    border: 1px solid rgba(59, 130, 246, 0.35);
    font-weight: normal;
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    direction: ltr;
    flex-shrink: 1;
}
.m12-fp-shortcut-badge {
    font-size: 10.5px;
    background: rgba(255, 255, 255, 0.1);
    color: #e2e8f0;
    padding: 2px 7px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    font-family: Consolas, monospace;
    direction: ltr;
    white-space: nowrap;
    flex-shrink: 0;
}
.m12-fp-actions {
    position: relative;
    z-index: 160;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 5px;
    direction: ltr;
    flex-shrink: 0;
    margin-inline-start: auto;
    max-width: 100%;
}
.m12-fp-btn {
    position: relative;
    z-index: 170;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 6px;
    color: #e2e8f0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    pointer-events: auto !important;
    font-size: 14px;
    font-weight: bold;
    transition: all 0.15s ease;
    flex-shrink: 0;
    user-select: none;
    -webkit-user-select: none;
}
.m12-fp-btn:hover {
    background: rgba(59, 130, 246, 0.35);
    color: #ffffff;
    border-color: rgba(96, 165, 250, 0.8);
    transform: scale(1.05);
}
.m12-fp-btn-close:hover {
    background: rgba(239, 68, 68, 0.45) !important;
    color: #ffffff !important;
    border-color: rgba(239, 68, 68, 0.8) !important;
}
.m12-fp-viewport {
    flex: 1;
    position: relative;
    overflow: hidden;
    background-color: #070b14;
    background-image: radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px);
    background-size: 20px 20px;
    cursor: grab;
    display: flex;
    border-bottom-left-radius: 11px;
    border-bottom-right-radius: 11px;
}
.m12-fp-viewport:active {
    cursor: grabbing;
}
.m12-fp-layer {
    position: absolute;
    top: 0;
    left: 0;
    transform-origin: 0 0;
    will-change: transform;
}
.m12-fp-img {
    max-width: none;
    max-height: none;
    display: block;
    pointer-events: none;
    -webkit-user-drag: none;
    user-select: none;
    border-radius: 4px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}
"""

_FLOATING_PLAN_CONTROLLER_JS = r"""(function() {
    var doc = document;
    var win = window;
    win.__m15FloatingPlanVersion = '__VERSION_TOKEN__';

    var state = {
        hasImage: false,
        imgName: 'المسقط المعماري الاسترشادي',
        imgType: 'image/png',
        imgB64: '',
        scale: 1.0,
        panX: 0,
        panY: 0,
        isMax: false,
        preMax: null,
        isDraggingWin: false,
        winStartX: 0,
        winStartY: 0,
        isResizing: false,
        resizeDir: '',
        rStartMouseX: 0,
        rStartMouseY: 0,
        rStartLeft: 0,
        rStartTop: 0,
        rStartWidth: 0,
        rStartHeight: 0,
        activeHandle: null,
        isPanning: false,
        panStartX: 0,
        panStartY: 0,
        toastTimer: null
    };

    function getModal() {
        return doc.getElementById('m12-floating-plan-modal');
    }

    var modal = getModal();
    var wasOpen = false;
    var prevL = null, prevT = null, prevW = null, prevH = null;

    if (modal && modal.getAttribute('data-v') !== '__VERSION_TOKEN__') {
        wasOpen = modal.classList.contains('m12-show');
        prevL = modal.style.left;
        prevT = modal.style.top;
        prevW = modal.style.width;
        prevH = modal.style.height;
        modal.remove();
        modal = null;
    }

    if (!modal) {
        modal = doc.createElement('div');
        modal.id = 'm12-floating-plan-modal';
        modal.setAttribute('data-v', '__VERSION_TOKEN__');
        modal.innerHTML = `
            <!-- 8-Way Resize Handles -->
            <div class="m12-rh m12-rh-n" data-dir="n" title="سحب لتغيير الارتفاع"></div>
            <div class="m12-rh m12-rh-s" data-dir="s" title="سحب لتغيير الارتفاع"></div>
            <div class="m12-rh m12-rh-e" data-dir="e" title="سحب لتغيير العرض"></div>
            <div class="m12-rh m12-rh-w" data-dir="w" title="سحب لتغيير العرض"></div>
            <div class="m12-rh m12-rh-nw" data-dir="nw" title="سحب لتغيير المقاس"><span class="m12-corner-mark"></span></div>
            <div class="m12-rh m12-rh-ne" data-dir="ne" title="سحب لتغيير المقاس"><span class="m12-corner-mark"></span></div>
            <div class="m12-rh m12-rh-sw" data-dir="sw" title="سحب لتغيير المقاس"><span class="m12-corner-mark"></span></div>
            <div class="m12-rh m12-rh-se" data-dir="se" title="سحب لتغيير المقاس"><span class="m12-corner-mark"></span></div>

            <div class="m12-fp-header" id="m12-fp-header">
                <div class="m12-fp-title-wrap">
                    <span style="font-size:16px;">🖼️</span>
                    <span class="m12-fp-title-text">المسقط المعماري الاسترشادي</span>
                    <span class="m12-fp-badge" id="m12-fp-name-badge"></span>
                    <span class="m12-fp-shortcut-badge">Ctrl + Alt + F (ب)</span>
                    <span class="m12-fp-badge" id="m12-fp-zoom-badge" style="color:#60a5fa; font-weight:700; font-family:Consolas, monospace;">100%</span>
                </div>
                <div class="m12-fp-actions">
                    <button type="button" class="m12-fp-btn" id="m12-fp-btn-zoom-out" title="تصغير (−)" onclick="window.m15FloatingPlan && window.m15FloatingPlan.zoomBy(0.8)">−</button>
                    <button type="button" class="m12-fp-btn" id="m12-fp-btn-zoom-in" title="تكبير (+)" onclick="window.m15FloatingPlan && window.m15FloatingPlan.zoomBy(1.25)">+</button>
                    <button type="button" class="m12-fp-btn" id="m12-fp-btn-reset" title="إعادة ضبط (Reset)" onclick="window.m15FloatingPlan && window.m15FloatingPlan.resetView(true)">↺</button>
                    <button type="button" class="m12-fp-btn" id="m12-fp-btn-max" title="تكبير / استعادة الإطار" onclick="window.m15FloatingPlan && window.m15FloatingPlan.toggleMax()">⛶</button>
                    <button type="button" class="m12-fp-btn m12-fp-btn-close" id="m12-fp-btn-close" title="إغلاق (Esc)" onclick="window.m15FloatingPlan && window.m15FloatingPlan.close()">×</button>
                </div>
            </div>
            <div class="m12-fp-viewport" id="m12-fp-viewport">
                <div class="m12-fp-layer" id="m12-fp-layer">
                    <img class="m12-fp-img" id="m12-fp-img" src="" alt="المسقط المعماري الاسترشادي" />
                </div>
                <div id="m12-fp-no-img" style="display:none; position:absolute; inset:0; flex-direction:column; align-items:center; justify-content:center; padding:24px; text-align:center; direction:rtl; z-index:10; background:rgba(15,23,42,0.94);">
                    <div style="font-size:42px; margin-bottom:12px;">🖼️</div>
                    <div style="font-size:16px; font-weight:700; color:#ffffff; margin-bottom:8px;">النافذة العائمة الحرة للمسقط المعماري</div>
                    <div style="font-size:13px; color:#cbd5e1; max-width:440px; line-height:1.7; background:rgba(30,41,59,0.75); border:1.5px solid rgba(59,130,246,0.35); border-radius:10px; padding:12px 18px; margin-bottom:12px;">
                        لم يتم تحميل صورة مسقط استرشادي بعد.<br/>
                        يمكنك رفع صورة من قسم <b>«🖼️ تحميل صورة مسقط افقي استرشادي للمباني»</b>، وستظهر هنا فوراً مع إمكانية التكبير والتصغير وتغيير الحجم والتحريك بحرية تامة أثناء التصميم.
                    </div>
                    <div style="font-size:11.5px; color:#60a5fa;">💡 يمكنك الضغط على <b>Ctrl + Alt + F (أو ب)</b> في أي وقت لفتح أو إغلاق هذه النافذة.</div>
                </div>
            </div>
        `;
        doc.body.appendChild(modal);

        if (prevW) {
            modal.style.width = prevW;
            modal.style.height = prevH;
            modal.style.left = prevL;
            modal.style.top = prevT;
            modal.style.right = 'auto';
            modal.style.bottom = 'auto';
        }
        if (wasOpen) {
            modal.classList.add('m12-show');
        }
    }

    function applyTransform(animated) {
        var layer = doc.getElementById('m12-fp-layer');
        var zoomVal = doc.getElementById('m12-fp-zoom-badge');
        if (layer) {
            layer.style.transition = animated ? 'transform 0.18s cubic-bezier(0.1, 0.9, 0.2, 1)' : 'none';
            layer.style.transform = 'translate(' + state.panX + 'px, ' + state.panY + 'px) scale(' + state.scale + ')';
        }
        if (zoomVal) {
            zoomVal.textContent = Math.round(state.scale * 100) + '%';
        }
    }

    function resetView(animated) {
        var m = getModal();
        if (!m) return;
        var viewport = doc.getElementById('m12-fp-viewport');
        var img = doc.getElementById('m12-fp-img');
        if (!viewport || !img) return;

        var vw = viewport.clientWidth || 700;
        var vh = viewport.clientHeight || 500;
        var iw = img.naturalWidth || img.width || 800;
        var ih = img.naturalHeight || img.height || 600;
        if (!iw || !ih || iw <= 0 || ih <= 0) return;

        var pad = 24;
        var sX = (vw - pad * 2) / iw;
        var sY = (vh - pad * 2) / ih;
        state.scale = Math.min(sX, sY, 1.0);
        if (state.scale < 0.05) state.scale = 0.5;

        state.panX = (vw - iw * state.scale) / 2;
        state.panY = (vh - ih * state.scale) / 2;
        applyTransform(animated);
    }

    function zoomBy(factor) {
        var viewport = doc.getElementById('m12-fp-viewport');
        if (!viewport) return;
        var vw = viewport.clientWidth || 700;
        var vh = viewport.clientHeight || 500;
        var cx = vw / 2;
        var cy = vh / 2;
        var newScale = Math.min(Math.max(state.scale * factor, 0.08), 30.0);
        state.panX = cx - (cx - state.panX) * (newScale / state.scale);
        state.panY = cy - (cy - state.panY) * (newScale / state.scale);
        state.scale = newScale;
        applyTransform(true);
    }

    function toggleMax() {
        var m = getModal();
        if (!m) return;
        var maxBtn = doc.getElementById('m12-fp-btn-max');
        if (!state.isMax) {
            state.preMax = {
                left: m.style.left,
                top: m.style.top,
                width: m.style.width,
                height: m.style.height,
                right: m.style.right,
                bottom: m.style.bottom
            };
            m.style.left = '16px';
            m.style.top = '16px';
            m.style.width = 'calc(100vw - 32px)';
            m.style.height = 'calc(100vh - 32px)';
            m.style.right = 'auto';
            m.style.bottom = 'auto';
            state.isMax = true;
            if (maxBtn) {
                maxBtn.textContent = '❐';
                maxBtn.title = 'استعادة الإطار (Restore)';
            }
        } else {
            if (state.preMax) {
                m.style.left = state.preMax.left;
                m.style.top = state.preMax.top;
                m.style.width = state.preMax.width;
                m.style.height = state.preMax.height;
                m.style.right = state.preMax.right;
                m.style.bottom = state.preMax.bottom;
            }
            state.isMax = false;
            if (maxBtn) {
                maxBtn.textContent = '⛶';
                maxBtn.title = 'تكبير الإطار (Maximize)';
            }
        }
        setTimeout(function() { resetView(true); }, 120);
    }

    function close() {
        var m = getModal();
        if (m) m.classList.remove('m12-show');
    }

    function show() {
        var m = getModal();
        if (!m) return;
        syncImageElements();
        m.classList.add('m12-show');
        if (state.hasImage) {
            setTimeout(function() { resetView(false); }, 60);
        } else {
            showNoImageToast();
        }
    }

    function toggle() {
        var m = getModal();
        if (!m) return;
        if (m.classList.contains('m12-show')) {
            close();
        } else {
            show();
        }
    }

    function isOpen() {
        var m = getModal();
        return !!(m && m.classList.contains('m12-show'));
    }

    function syncImageElements() {
        var m = getModal();
        if (!m) return;
        var nameBadge = doc.getElementById('m12-fp-name-badge');
        var imgEl = doc.getElementById('m12-fp-img');
        var noImgEl = doc.getElementById('m12-fp-no-img');
        var layerEl = doc.getElementById('m12-fp-layer');

        if (nameBadge) {
            nameBadge.textContent = state.hasImage ? state.imgName : 'بانتظار تحميل صورة';
        }
        if (state.hasImage && state.imgB64) {
            if (noImgEl) noImgEl.style.display = 'none';
            if (layerEl) layerEl.style.display = 'block';
            if (imgEl) {
                imgEl.style.display = 'block';
                var newSrc = 'data:' + state.imgType + ';base64,' + state.imgB64;
                if (imgEl.src !== newSrc) {
                    imgEl.src = newSrc;
                }
            }
        } else {
            if (imgEl) {
                imgEl.src = '';
                imgEl.style.display = 'none';
            }
            if (layerEl) layerEl.style.display = 'none';
            if (noImgEl) noImgEl.style.display = 'flex';
        }
    }

    function updateImage(hasImg, name, type, b64) {
        state.hasImage = Boolean(hasImg && b64);
        state.imgName = name || 'المسقط المعماري الاسترشادي';
        state.imgType = type || 'image/png';
        state.imgB64 = b64 || '';
        syncImageElements();
    }

    function showNoImageToast() {
        var t = doc.getElementById('m12-float-no-img-toast');
        if (!t) {
            t = doc.createElement('div');
            t.id = 'm12-float-no-img-toast';
            t.style.cssText = 'position:fixed; top:28px; left:50%; transform:translateX(-50%) translateY(-20px); background:linear-gradient(135deg, #1e293b, #0f172a); border:1.5px solid #f59e0b; border-radius:10px; padding:12px 22px; color:#ffffff; font-size:13.5px; font-weight:700; z-index:1000000; box-shadow:0 12px 35px rgba(0,0,0,0.65), 0 0 15px rgba(245,158,11,0.25); display:flex; align-items:center; gap:10px; direction:rtl; opacity:0; pointer-events:none; transition:all 0.3s cubic-bezier(0.16,1,0.3,1); font-family:system-ui, -apple-system, sans-serif;';
            doc.body.appendChild(t);
        }
        t.innerHTML = '<span style="font-size:18px;">⚠️</span><span>لم يتم تحميل صورة مسقط استرشادي بعد. يمكنك رفع صورة من قسم <b>«🖼️ تحميل صورة مسقط افقي استرشادي للمباني»</b>.</span>';
        t.style.opacity = '1';
        t.style.transform = 'translateX(-50%) translateY(0)';
        if (state.toastTimer) clearTimeout(state.toastTimer);
        state.toastTimer = setTimeout(function() {
            t.style.opacity = '0';
            t.style.transform = 'translateX(-50%) translateY(-20px)';
        }, 3800);
    }

    // Direct element click bindings
    var bZoomIn = doc.getElementById('m12-fp-btn-zoom-in');
    if (bZoomIn) bZoomIn.onclick = function() { zoomBy(1.25); };
    var bZoomOut = doc.getElementById('m12-fp-btn-zoom-out');
    if (bZoomOut) bZoomOut.onclick = function() { zoomBy(0.8); };
    var bReset = doc.getElementById('m12-fp-btn-reset');
    if (bReset) bReset.onclick = function() { resetView(true); };
    var bMax = doc.getElementById('m12-fp-btn-max');
    if (bMax) bMax.onclick = function() { toggleMax(); };
    var bClose = doc.getElementById('m12-fp-btn-close');
    if (bClose) bClose.onclick = function() { close(); };

    var img = doc.getElementById('m12-fp-img');
    if (img) {
        img.onload = function() {
            resetView(false);
        };
    }

    // Header Dragging
    var header = doc.getElementById('m12-fp-header');
    if (header && !header._hasDragBound) {
        header._hasDragBound = true;
        header.addEventListener('mousedown', function(e) {
            if (e.target.closest('button') || e.target.closest('.m12-fp-actions')) return;
            state.isDraggingWin = true;
            var m = getModal();
            var rect = m.getBoundingClientRect();
            m.style.right = 'auto';
            m.style.bottom = 'auto';
            m.style.left = rect.left + 'px';
            m.style.top = rect.top + 'px';
            state.winStartX = e.clientX - rect.left;
            state.winStartY = e.clientY - rect.top;
            header.style.cursor = 'grabbing';
            doc.body.classList.add('m12-dragging-active');
        });
    }

    // Resizing Handles
    modal.querySelectorAll('.m12-rh').forEach(function(handle) {
        handle.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            state.isResizing = true;
            state.resizeDir = handle.getAttribute('data-dir');
            state.activeHandle = handle;
            handle.classList.add('m12-rh-active');

            state.rStartMouseX = e.clientX;
            state.rStartMouseY = e.clientY;

            var m = getModal();
            var rect = m.getBoundingClientRect();
            state.rStartLeft = rect.left;
            state.rStartTop = rect.top;
            state.rStartWidth = rect.width;
            state.rStartHeight = rect.height;

            m.style.right = 'auto';
            m.style.bottom = 'auto';
            m.style.left = state.rStartLeft + 'px';
            m.style.top = state.rStartTop + 'px';
            m.style.width = state.rStartWidth + 'px';
            m.style.height = state.rStartHeight + 'px';

            doc.body.style.userSelect = 'none';
            doc.body.style.cursor = win.getComputedStyle(handle).cursor;
            doc.body.classList.add('m12-dragging-active');
        });
    });

    // Viewport Panning & Zooming
    var viewport = doc.getElementById('m12-fp-viewport');
    if (viewport && !viewport._hasPanBound) {
        viewport._hasPanBound = true;
        viewport.addEventListener('mousedown', function(e) {
            if (e.button !== 0) return;
            state.isPanning = true;
            state.panStartX = e.clientX - state.panX;
            state.panStartY = e.clientY - state.panY;
            viewport.style.cursor = 'grabbing';
            doc.body.classList.add('m12-dragging-active');
        });

        viewport.addEventListener('wheel', function(e) {
            e.preventDefault();
            var rect = viewport.getBoundingClientRect();
            var mouseX = e.clientX - rect.left;
            var mouseY = e.clientY - rect.top;

            var factor = e.deltaY < 0 ? 1.15 : 0.87;
            var newScale = Math.min(Math.max(state.scale * factor, 0.08), 30.0);

            state.panX = mouseX - (mouseX - state.panX) * (newScale / state.scale);
            state.panY = mouseY - (mouseY - state.panY) * (newScale / state.scale);
            state.scale = newScale;
            applyTransform(false);
        }, { passive: false });
    }

    // Document MouseMove and MouseUp
    if (!win._hasM15DocMouseBound) {
        win._hasM15DocMouseBound = true;
        doc.addEventListener('mousemove', function(e) {
            var m = getModal();
            if (!m) return;

            if (state.isResizing) {
                e.preventDefault();
                var dx = e.clientX - state.rStartMouseX;
                var dy = e.clientY - state.rStartMouseY;

                var minW = 280, minH = 200;
                var maxW = win.innerWidth - 20;
                var maxH = win.innerHeight - 20;

                var newWidth = state.rStartWidth;
                var newHeight = state.rStartHeight;
                var newLeft = state.rStartLeft;
                var newTop = state.rStartTop;

                if (state.resizeDir.indexOf('e') !== -1) {
                    newWidth = Math.min(Math.max(state.rStartWidth + dx, minW), maxW);
                }
                if (state.resizeDir.indexOf('w') !== -1) {
                    var rawW = state.rStartWidth - dx;
                    if (rawW < minW) {
                        newWidth = minW;
                        newLeft = state.rStartLeft + (state.rStartWidth - minW);
                    } else if (rawW > maxW) {
                        newWidth = maxW;
                        newLeft = state.rStartLeft + (state.rStartWidth - maxW);
                    } else {
                        newWidth = rawW;
                        newLeft = state.rStartLeft + dx;
                    }
                }

                if (state.resizeDir.indexOf('s') !== -1) {
                    newHeight = Math.min(Math.max(state.rStartHeight + dy, minH), maxH);
                }
                if (state.resizeDir.indexOf('n') !== -1) {
                    var rawH = state.rStartHeight - dy;
                    if (rawH < minH) {
                        newHeight = minH;
                        newTop = state.rStartTop + (state.rStartHeight - minH);
                    } else if (rawH > maxH) {
                        newHeight = maxH;
                        newTop = state.rStartTop + (state.rStartHeight - maxH);
                    } else {
                        newHeight = rawH;
                        newTop = state.rStartTop + dy;
                    }
                }

                m.style.width = newWidth + 'px';
                m.style.height = newHeight + 'px';
                m.style.left = newLeft + 'px';
                m.style.top = newTop + 'px';
                return;
            }

            if (state.isDraggingWin) {
                e.preventDefault();
                var newL = e.clientX - state.winStartX;
                var newT = e.clientY - state.winStartY;
                var maxL = win.innerWidth - 80;
                var maxT = win.innerHeight - 40;
                newL = Math.max(-m.offsetWidth + 80, Math.min(newL, maxL));
                newT = Math.max(0, Math.min(newT, maxT));
                m.style.left = newL + 'px';
                m.style.top = newT + 'px';
                return;
            }

            if (state.isPanning) {
                e.preventDefault();
                state.panX = e.clientX - state.panStartX;
                state.panY = e.clientY - state.panStartY;
                applyTransform(false);
            }
        });

        doc.addEventListener('mouseup', function(e) {
            doc.body.classList.remove('m12-dragging-active');
            if (state.isResizing) {
                state.isResizing = false;
                state.resizeDir = '';
                if (state.activeHandle) {
                    state.activeHandle.classList.remove('m12-rh-active');
                    state.activeHandle = null;
                }
                doc.body.style.userSelect = '';
                doc.body.style.cursor = '';
            }
            if (state.isDraggingWin) {
                state.isDraggingWin = false;
                var header = doc.getElementById('m12-fp-header');
                if (header) header.style.cursor = 'grab';
            }
            if (state.isPanning) {
                state.isPanning = false;
                var viewport = doc.getElementById('m12-fp-viewport');
                if (viewport) viewport.style.cursor = 'grab';
            }
        });
    }

    // Global KeyDown handler
    function onGlobalKeyDown(e) {
        if (!e) return;
        var codeMatches = (e.code === 'KeyF');
        var keyMatches = (e.key === 'f' || e.key === 'F' || e.key === 'ب' || e.key === 'B' || e.key === 'ـ' || e.key === '[' || e.key === ']' || e.keyCode === 70 || e.which === 70);
        var isF = codeMatches || keyMatches;
        var hasAlt = e.altKey || (e.getModifierState && e.getModifierState('Alt'));
        var hasCtrl = e.ctrlKey || e.metaKey || (e.getModifierState && e.getModifierState('Control'));
        var hasAltGr = (e.getModifierState && e.getModifierState('AltGraph'));
        var isToggleShortcut = isF && ((hasCtrl && hasAlt) || hasAltGr || (hasCtrl && e.shiftKey));

        if (isToggleShortcut) {
            e.preventDefault();
            e.stopPropagation();
            toggle();
            return false;
        }
        if (e.key === 'Escape' || e.key === 'Esc' || e.keyCode === 27) {
            if (isOpen()) {
                e.preventDefault();
                close();
            }
        }
    }

    win.m15FloatingPlanGlobalKeyDown = onGlobalKeyDown;

    if (win._m15_active_keydown) {
        try {
            win.removeEventListener('keydown', win._m15_active_keydown, true);
            doc.removeEventListener('keydown', win._m15_active_keydown, true);
        } catch(err) {}
    }
    win._m15_active_keydown = onGlobalKeyDown;
    try { win.addEventListener('keydown', onGlobalKeyDown, true); } catch(err) {}
    try { doc.addEventListener('keydown', onGlobalKeyDown, true); } catch(err) {}

    // Public API
    var api = {
        toggle: toggle,
        show: show,
        close: close,
        isOpen: isOpen,
        zoomBy: zoomBy,
        resetView: resetView,
        toggleMax: toggleMax,
        updateImage: updateImage
    };

    win.m15FloatingPlan = api;
    win.m12FloatingPlan = api;
    win.m15ToggleFloatingPlan = toggle;
    win.m12ToggleFloatingPlan = toggle;
    win.m15ShowFloatingPlan = show;
    win.m12ShowFloatingPlan = show;
    win.m15HideFloatingPlan = close;
    win.m12HideFloatingPlan = close;
    win.m15UpdateFloatingPlanImage = updateImage;
    win.m12UpdateFloatingPlanImage = updateImage;
})();
"""


def _inject_floating_plan_viewer():
    """
    مكون النافذة العائمة الحرة (Floating & Draggable & Resizable Window) للمسقط الاسترشادي:
    - اختصار لوحة المفاتيح الشامل: Ctrl + Alt + F (تبديل Toggle).
    - سحب النافذة بحرية من شريط العنوان في أي مكان على الشاشة (Drag Window).
    - تغيير مقاس إطار النافذة بحرية من 8 اتجاهات (8-Way Resize Window).
    - تكبير وتصغير فائق السلاسة (Mouse Wheel Zoom متمركز على موضع المؤشر + أزرار + / -).
    - سحب وتحريك الصورة (Pan / Drag) للتنقل بين المحاور والتفاصيل.
    - زر إعادة ضبط (Reset ↺) لإرجاع الصورة للمقاس المتمركز المناسب للإطار.
    - زر تكبير وتصغير الإطار (Maximize / Restore ⛶).
    - زر إغلاق (×)، مفتاح Esc، أو تكرار Ctrl + Alt + F.
    - تنفيذ مستقل في النافذة الرئيسية (Parent Realm) غير متأثر بإعادة تشغيل Streamlit إطلاقاً.
    - Zero-lag Client-side بدون أي Rerun لضمان أعلى سلاسة.
    """
    cur_b64 = st.session_state.get("m15_uploaded_image_b64") or st.session_state.get("m12_uploaded_image_b64", "")
    cur_name = st.session_state.get("m15_uploaded_image_name") or st.session_state.get("m12_uploaded_image_name", "المسقط الاسترشادي")
    cur_type = st.session_state.get("m15_uploaded_image_type") or st.session_state.get("m12_uploaded_image_type", "image/png")
    has_image = bool(cur_b64)

    has_img_js = "true" if has_image else "false"
    cur_name_js = json.dumps(cur_name)
    cur_type_js = json.dumps(cur_type)
    cur_b64_js = json.dumps(cur_b64) if has_image else '""'

    CONTROLLER_VERSION = "2026.10.01.v2"
    js_controller = _FLOATING_PLAN_CONTROLLER_JS.replace("__VERSION_TOKEN__", CONTROLLER_VERSION)

    inject_code = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0; padding:0; overflow:hidden; background:transparent;">
    <script>
    (function() {{
        var parentDoc = null;
        var parentWin = null;
        try {{
            if (window.parent && window.parent.document) {{
                parentDoc = window.parent.document;
                parentWin = window.parent;
            }} else {{
                parentDoc = document;
                parentWin = window;
            }}
        }} catch(e) {{
            parentDoc = document;
            parentWin = window;
        }}

        var HAS_IMAGE = {has_img_js};
        var IMG_NAME = {cur_name_js};
        var IMG_TYPE = {cur_type_js};
        var IMG_B64 = {cur_b64_js};
        var CONTROLLER_VER = {json.dumps(CONTROLLER_VERSION)};
        var CONTROLLER_CODE = {json.dumps(js_controller)};

        // 1. Inject or update CSS styles in parentDoc.head
        var styleEl = parentDoc.getElementById('m12-floating-plan-styles');
        if (!styleEl) {{
            styleEl = parentDoc.createElement('style');
            styleEl.id = 'm12-floating-plan-styles';
            parentDoc.head.appendChild(styleEl);
        }}
        styleEl.textContent = {json.dumps(_FLOATING_PLAN_CSS)};

        // 2. Inject or update permanent Controller Script in parentDoc.head
        if (!parentWin.__m15FloatingPlanVersion || parentWin.__m15FloatingPlanVersion !== CONTROLLER_VER) {{
            var oldScript = parentDoc.getElementById('m12-floating-plan-controller-script');
            if (oldScript) {{
                try {{ oldScript.remove(); }} catch(e) {{}}
            }}
            var s = parentDoc.createElement('script');
            s.id = 'm12-floating-plan-controller-script';
            s.textContent = CONTROLLER_CODE;
            parentDoc.head.appendChild(s);
        }}

        // 3. Update Image & Title in controller
        try {{
            if (parentWin.m15FloatingPlan && parentWin.m15FloatingPlan.updateImage) {{
                parentWin.m15FloatingPlan.updateImage(HAS_IMAGE, IMG_NAME, IMG_TYPE, IMG_B64);
            }} else if (parentWin.m15UpdateFloatingPlanImage) {{
                parentWin.m15UpdateFloatingPlanImage(HAS_IMAGE, IMG_NAME, IMG_TYPE, IMG_B64);
            }}
        }} catch(e) {{}}

        // 4. Ensure child iframes forward keydown events to parentWin.m15FloatingPlan
        try {{
            parentDoc.querySelectorAll('iframe').forEach(function(ifr) {{
                try {{
                    if (ifr.contentWindow && ifr.contentDocument && !ifr._hasM15KeyBound) {{
                        ifr._hasM15KeyBound = true;
                        ifr.contentWindow.addEventListener('keydown', function(e) {{
                            if (parentWin.m15FloatingPlanGlobalKeyDown) {{
                                parentWin.m15FloatingPlanGlobalKeyDown(e);
                            }}
                        }}, true);
                    }}
                }} catch(e) {{}}
            }});
        }} catch(e) {{}}
    }})();
    </script>
    </body>
    </html>
    """

    components.html(inject_code, height=0, width=0)


def _section_upload_image():
    """
    قسم تحميل صورة:
    إمكانية تحميل صورة من جهاز الكمبيوتر (الهارد ديسك) بنقرة زر واحدة "تحميل الصورة"،
    وعرض الصورة بكامل مساحة هذا القسم الجديد مع أدوات تحكم تفاعلية (تكبير، حفظ، حذف، وبيانات الملف).
    """
    st.markdown(
        """<style>
        .m12-upload-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.90) 100%);
            border: 1.5px solid rgba(148, 163, 184, 0.28);
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        }
        div[data-testid="stFileUploader"] {
            width: 100% !important;
            margin-top: 4px !important;
            margin-bottom: 10px !important;
        }
        div[data-testid="stFileUploader"] section {
            padding: 16px 20px !important;
            border-radius: 10px !important;
            border: 2px dashed #3b82f6 !important;
            background: rgba(30, 41, 59, 0.55) !important;
            transition: all 0.25s ease !important;
            text-align: center !important;
        }
        div[data-testid="stFileUploader"] section:hover {
            border-color: #60a5fa !important;
            background: rgba(30, 41, 59, 0.85) !important;
        }
        div[data-testid="stFileUploader"] button[data-testid="baseButton-secondary"] {
            background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
            color: #ffffff !important;
            border: 1px solid #60a5fa !important;
            border-radius: 8px !important;
            padding: 10px 28px !important;
            font-size: 0px !important;
            box-shadow: 0 3px 10px rgba(37, 99, 235, 0.40) !important;
            cursor: pointer !important;
            position: relative !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stFileUploader"] button[data-testid="baseButton-secondary"]::after {
            content: "📁 تحميل الصورة";
            font-size: 14.5px !important;
            font-weight: 700 !important;
            color: #ffffff !important;
            display: inline-block !important;
        }
        div[data-testid="stFileUploader"] button[data-testid="baseButton-secondary"]:hover {
            background: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.55) !important;
        }
        .m12-img-container {
            width: 100% !important;
            border-radius: 10px !important;
            overflow: hidden !important;
            border: 1.5px solid #334155 !important;
            background: #0b1120 !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.35) !important;
            margin-top: 10px !important;
            padding: 6px !important;
            text-align: center !important;
        }
        .m12-img-container img {
            width: 100% !important;
            height: auto !important;
            border-radius: 6px !important;
            display: block !important;
            margin: 0 auto !important;
            object-fit: contain !important;
        }
        </style>""",
        unsafe_allow_html=True
    )

    # أداة تحميل الصورة من الهارد ديسك
    uploaded_file = st.file_uploader(
        "تحميل الصورة",
        type=["png", "jpg", "jpeg", "webp", "bmp", "svg", "tiff"],
        key="m15_user_hard_drive_image",
        label_visibility="collapsed",
        help="اضغط على زر تحميل الصورة لاختيار ملف صورة من جهاز الكمبيوتر"
    )

    if uploaded_file is not None:
        curr_uploader_file = uploaded_file.name
        last_uploader_file = st.session_state.get("_m15_last_uploader_file")
        if curr_uploader_file != last_uploader_file:
            img_bytes = uploaded_file.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            st.session_state["m15_uploaded_image_b64"] = img_b64
            st.session_state["m15_uploaded_image_name"] = uploaded_file.name
            st.session_state["m15_uploaded_image_type"] = uploaded_file.type or "image/png"
            st.session_state["m15_uploaded_image_size_kb"] = round(len(img_bytes) / 1024.0, 1)

            try:
                from PIL import Image as _PILImage
                with _PILImage.open(io.BytesIO(img_bytes)) as _pimg:
                    st.session_state["m15_uploaded_image_w"] = _pimg.width
                    st.session_state["m15_uploaded_image_h"] = _pimg.height
            except Exception:
                st.session_state["m15_uploaded_image_w"] = None
                st.session_state["m15_uploaded_image_h"] = None
            st.session_state["_m15_last_uploader_file"] = curr_uploader_file
            save_settings()

    cur_b64 = st.session_state.get("m15_uploaded_image_b64")
    cur_name = st.session_state.get("m15_uploaded_image_name", "uploaded_image.png")
    cur_type = st.session_state.get("m15_uploaded_image_type", "image/png")
    cur_size = st.session_state.get("m15_uploaded_image_size_kb", 0.0)
    cur_w = st.session_state.get("m15_uploaded_image_w")
    cur_h = st.session_state.get("m15_uploaded_image_h")
    dim_str = f"{cur_w}×{cur_h} px" if cur_w and cur_h else ""

    # زر النافذة العائمة السريع التفاعلي
    float_btn_html = """<div style='margin-top:6px; margin-bottom:12px; width:100%;' dir='rtl'>
        <button type='button' id='m15_btn_open_floating' onclick='(function(){ var fn = (window.parent && window.parent.m15ToggleFloatingPlan) || (window.parent && window.parent.m12ToggleFloatingPlan) || window.m15ToggleFloatingPlan || window.m12ToggleFloatingPlan; if(fn) fn(); })()'
        style='width:100%; display:flex; align-items:center; justify-content:space-between; background:linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #0f172a 100%); color:#ffffff; border:1.5px solid #60a5fa; border-radius:9px; padding:9px 13px; font-weight:700; font-size:13px; cursor:pointer; box-shadow:0 4px 14px rgba(37, 99, 235, 0.35); transition:all 0.2s ease;'>
            <span style='display:flex; align-items:center; gap:8px;'>
                <span style='font-size:16px;'>🖼️</span>
                <span>النافذة العائمة الحرة للمسقط</span>
            </span>
            <span style='background:rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.32); border-radius:5px; padding:2px 7px; font-size:10.5px; font-family:Consolas, monospace; letter-spacing:0.5px;'>Ctrl + Alt + F (ب)</span>
        </button>
    </div>"""
    st.html(float_btn_html) if hasattr(st, "html") else st.markdown(float_btn_html, unsafe_allow_html=True)

    if cur_b64:
        preview_html = f"""<div style='width:100%;text-align:center;background:#0b1120;border:1.5px solid #334155;border-radius:10px;padding:6px;box-shadow:0 4px 14px rgba(0,0,0,0.35);margin-top:4px;margin-bottom:8px;'>
<img src='data:{cur_type};base64,{cur_b64}' style='width:100%;max-height:360px;height:auto;display:block;border-radius:6px;object-fit:contain;margin:0 auto;' alt='{cur_name}' />
</div>"""
        st.html(preview_html) if hasattr(st, "html") else st.markdown(preview_html, unsafe_allow_html=True)

        st.markdown(
            f"""<div style='font-size:0.80rem;color:#cbd5e1;margin-bottom:8px;' dir='rtl'>
                📄 <b>{cur_name}</b> | الحجم: <b style='color:#ffffff;'>{cur_size:.1f} KB</b> {('| الأبعاد: <b style="color:#ffffff;">' + dim_str + '</b>') if dim_str else ''}
            </div>""",
            unsafe_allow_html=True
        )

        if st.button("🗑️ إزالة الصورة الاسترشادية الحالية", key="m15_btn_remove_uploaded_img", use_container_width=True):
            st.session_state.pop("m15_uploaded_image_b64", None)
            st.session_state.pop("m15_uploaded_image_name", None)
            st.session_state.pop("m15_uploaded_image_type", None)
            st.session_state.pop("m15_uploaded_image_size_kb", None)
            st.session_state.pop("m15_uploaded_image_w", None)
            st.session_state.pop("m15_uploaded_image_h", None)
            st.session_state["_m15_last_uploader_file"] = None
            save_settings()
            st.rerun()


def _prepare_3d_scene_data():
    """
    تجهيز وتوليد البيانات الهندسية للمجسمات ثلاثية الأبعاد (Data Processing & 3D Modeling):
    - الحوائط (Walls): مجسمات ثلاثية الأبعاد مع كامل بيانات الحصر والمساحات للـ Inspector.
    - الأعمدة (Columns): أعمدة إنشائية خرسانية بارزة واضحة في التقاطعات مع الأبعاد.
    - النوافذ (Windows): مجسمات زجاجية وإطارات مع مقابض تحريك وبيانات هندسية وخلوص أمان.
    - الأبواب (Doors): مجسمات أبواب معمارية مع مقابض تحريك وبيانات هندسية كاملة.
    """
    xs = st.session_state.get("m15_x_axes", [])
    ys = st.session_state.get("m15_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        return None

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cx_mid = (min_x + max_x) / 2.0
    cy_mid = (min_y + max_y) / 2.0
    span_x = max_x - min_x
    span_y = max_y - min_y

    dh = float(st.session_state.get("m15_default_wall_height", st.session_state.get("m15_default_h_input", 3.0)))
    ph = float(st.session_state.get("m15_parapet_wall_height", st.session_state.get("m15_parapet_h_input", 1.0)))

    # خرائط الأسماء
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()

    # أبعاد الطوب لحسابات الحصر في الـ Inspector
    brick_size_v = st.session_state.get("m15_brick_size", "25×12×6")
    mortar_v = float(st.session_state.get("m15_mortar_thickness_cm", 1.0))
    if brick_size_v == _CUSTOM_SIZE_LABEL:
        b_l = float(st.session_state.get("m15_brick_custom_l", 25.0))
        b_w = float(st.session_state.get("m15_brick_custom_w", 12.0))
        b_h = float(st.session_state.get("m15_brick_custom_h", 6.0))
    else:
        b_l, b_w, b_h = _parse_brick_size(brick_size_v)

    # 1. الأعمدة (Columns)
    columns_data = []
    col_height = dh + 0.08  # بارزة طفيفاً فوق الحوائط للوضوح الإنشائي

    for (i, j) in _get_active_columns():
        cx, cy = _col_center(i, j)
        cw, cd = _get_col_wh(i, j)
        c_name = cm.get((i, j), f"C({i+1},{j+1})")
        columns_data.append({
            "id": f"col_{i}_{j}",
            "name": c_name,
            "grid": f"Y{i+1} - X{j+1}",
            "col_key": [i, j],
            "x": round(cx - cx_mid, 3),
            "y": round(col_height / 2.0, 3),
            "z": round(-(cy - cy_mid), 3),
            "w": round(cw, 3),
            "h": round(col_height, 3),
            "d": round(cd, 3),
            "cx_real": round(cx, 2),
            "cy_real": round(cy, 2),
        })

    # 2. الحوائط والنوافذ والأبواب (Walls, Windows & Doors)
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m15_wall_removed", set())
    plaster_walls = st.session_state.get("m15_plaster_walls", set())
    walls_data = []
    windows_data = []
    doors_data = []

    for wk in all_walls:
        if wk in removed_walls:
            continue
        i1, j1, i2, j2 = wk
        is_h = (j1 == j2)
        wlen = _wall_length_m(wk)
        if wlen <= 0.001:
            continue

        wall_h = _get_wall_height(wk, dh)
        thick_cm = _get_wall_thickness(wk)  # 12 or 25 cm
        thick = thick_cm / 100.0
        is_parapet = _is_parapet_wall(wk)
        col1_limit, col2_limit, col1_name, col2_name, _ = _get_column_bounds_along_wall(wk)
        w_name = wm.get(wk, f"Wall-{i1+1}{j1+1}-{i2+1}{j2+1}")
        w_label = _wall_display_label(wk, cm, wm)
        has_plaster = (wk in plaster_walls)

        # جمع الفتحات (نوافذ وأبواب)
        openings = []
        for wi in _get_wall_windows(wk):
            if not wi.get("removed", False):
                pos = float(wi.get("pos_m", 0.0))
                w_m = float(wi.get("w_m", 1.0))
                h_m = float(wi.get("h_m", 1.2))
                sill = float(wi.get("sill_m", 0.9))
                wid = wi.get("id", f"win_{pos}")
                wname = wm_win.get(wid) or wi.get("name") or "W"
                openings.append({
                    "type": "window",
                    "pos": max(0.0, pos),
                    "w": min(w_m, max(0.0, wlen - pos)),
                    "h": h_m,
                    "sill": sill,
                    "id": wid,
                    "name": wname,
                    "type_label": wi.get("type_label", "W1"),
                })

        for di in _get_wall_doors(wk):
            if not di.get("removed", False):
                pos = float(di.get("pos_m", 0.0))
                w_m = float(di.get("w_m", 0.9))
                h_m = float(di.get("h_m", 2.1))
                did = di.get("id", f"door_{pos}")
                dname = wm_door.get(did) or di.get("name") or "D"
                openings.append({
                    "type": "door",
                    "pos": max(0.0, pos),
                    "w": min(w_m, max(0.0, wlen - pos)),
                    "h": h_m,
                    "sill": 0.0,
                    "id": did,
                    "name": dname,
                    "type_label": di.get("type_label", "D1"),
                })

        openings.sort(key=lambda o: o["pos"])

        # حسابات الحصر الهندسية للحائط
        gross_area = round(wlen * wall_h, 2)
        openings_area = round(sum(o["w"] * o["h"] for o in openings), 2)
        net_area = round(max(0.0, gross_area - openings_area), 2)
        brick_qty = _compute_brick_qty(net_area, thick_cm, b_l, b_w, b_h, mortar_v)
        if thick_cm == _WALL_THICK:
            brick_vol_m3 = round(net_area * thick, 3)
            sand_m3 = round(brick_vol_m3 * 0.200 * 1.05, 3)
        else:
            brick_vol_m3 = 0.0
            sand_m3 = round(net_area * 0.025 * 1.05, 3)
        cement_kg = round(sand_m3 * 350.0, 1)

        cross_min, cross_max, cross_c, thick_m = _get_wall_cross_bounds(wk)
        # نقطة البداية للحائط في 2D
        if is_h:
            x_start_2d = min(xs[i1], xs[i2])
            y_2d = cross_c
            x_start_3d = x_start_2d - cx_mid
            z_start_3d = -(y_2d - cy_mid)
        else:
            y_start_2d = min(ys[j1], ys[j2])
            x_2d = cross_c
            x_start_3d = x_2d - cx_mid
            z_start_3d = -(y_start_2d - cy_mid)

        def _add_wall_box(d_start, d_len, y_bot, h_box, piece_type="wall_solid"):
            if d_len <= 0.001 or h_box <= 0.001:
                return
            d_mid = d_start + d_len / 2.0
            y_center = y_bot + h_box / 2.0
            if is_h:
                wx = (x_start_2d + d_mid) - cx_mid
                wz = -(y_2d - cy_mid)
                box_w = d_len
                box_d = thick
            else:
                wx = x_2d - cx_mid
                wz = -((y_start_2d + d_mid) - cy_mid)
                box_w = thick
                box_d = d_len
            walls_data.append({
                "wall_key": list(wk),
                "wall_name": w_name,
                "wall_label": w_label,
                "length": round(wlen, 2),
                "height": round(wall_h, 2),
                "thickness_cm": thick_cm,
                "gross_area": gross_area,
                "openings_area": openings_area,
                "net_area": net_area,
                "brick_vol_m3": brick_vol_m3,
                "brick_qty": brick_qty,
                "sand_m3": sand_m3,
                "cement_kg": cement_kg,
                "is_parapet": is_parapet,
                "has_plaster": has_plaster,
                "is_h": is_h,
                "col1_name": col1_name or "حر",
                "col2_name": col2_name or "حر",
                "col1_limit": round(col1_limit, 2),
                "col2_limit": round(col2_limit, 2),
                "piece_type": piece_type,
                "d_start": round(d_start, 3),
                "d_len": round(d_len, 3),
                "y_bot": round(y_bot, 3),
                "h_box": round(h_box, 3),
                "x": round(wx, 3),
                "y": round(y_center, 3),
                "z": round(wz, 3),
                "w": round(box_w, 3),
                "h": round(h_box, 3),
                "d": round(box_d, 3),
            })

        def _add_window_mesh(d_start, d_len, y_bot, h_box, op_obj):
            if d_len <= 0.001 or h_box <= 0.001:
                return
            d_mid = d_start + d_len / 2.0
            y_center = y_bot + h_box / 2.0
            glass_t = max(0.03, thick * 0.35)
            if is_h:
                wx = (x_start_2d + d_mid) - cx_mid
                wz = -(y_2d - cy_mid)
                box_w = d_len
                box_d = glass_t
            else:
                wx = x_2d - cx_mid
                wz = -((y_start_2d + d_mid) - cy_mid)
                box_w = glass_t
                box_d = d_len

            dist_to_end = max(0.0, wlen - (op_obj["pos"] + op_obj["w"]))
            windows_data.append({
                "id": op_obj["id"],
                "name": op_obj["name"],
                "op_kind": "win",
                "type_label": op_obj.get("type_label", "W1"),
                "wall_key": list(wk),
                "wall_name": w_name,
                "wall_label": w_label,
                "wall_len": round(wlen, 2),
                "wall_h": round(wall_h, 2),
                "pos_m": round(op_obj["pos"], 2),
                "w_m": round(op_obj["w"], 2),
                "h_m": round(op_obj["h"], 2),
                "sill_m": round(op_obj["sill"], 2),
                "lintel_m": round(op_obj["sill"] + op_obj["h"], 2),
                "dist_to_end": round(dist_to_end, 2),
                "area_m2": round(op_obj["w"] * op_obj["h"], 2),
                "col1_limit": round(col1_limit, 2),
                "col2_limit": round(col2_limit, 2),
                "col1_name": col1_name or "حر",
                "col2_name": col2_name or "حر",
                "is_h": is_h,
                "x_start_3d": round(x_start_3d, 3),
                "z_start_3d": round(z_start_3d, 3),
                "x": round(wx, 3),
                "y": round(y_center, 3),
                "z": round(wz, 3),
                "w": round(box_w, 3),
                "h": round(h_box, 3),
                "d": round(box_d, 3),
                "thick": round(thick, 3),
            })

        def _add_door_mesh(d_start, d_len, y_bot, h_box, op_obj):
            if d_len <= 0.001 or h_box <= 0.001:
                return
            d_mid = d_start + d_len / 2.0
            y_center = y_bot + h_box / 2.0
            door_t = max(0.04, thick * 0.45)
            if is_h:
                wx = (x_start_2d + d_mid) - cx_mid
                wz = -(y_2d - cy_mid)
                box_w = d_len
                box_d = door_t
            else:
                wx = x_2d - cx_mid
                wz = -((y_start_2d + d_mid) - cy_mid)
                box_w = door_t
                box_d = d_len

            dist_to_end = max(0.0, wlen - (op_obj["pos"] + op_obj["w"]))
            doors_data.append({
                "id": op_obj["id"],
                "name": op_obj["name"],
                "op_kind": "door",
                "type_label": op_obj.get("type_label", "D1"),
                "wall_key": list(wk),
                "wall_name": w_name,
                "wall_label": w_label,
                "wall_len": round(wlen, 2),
                "wall_h": round(wall_h, 2),
                "pos_m": round(op_obj["pos"], 2),
                "w_m": round(op_obj["w"], 2),
                "h_m": round(op_obj["h"], 2),
                "sill_m": 0.0,
                "lintel_m": round(op_obj["h"], 2),
                "dist_to_end": round(dist_to_end, 2),
                "area_m2": round(op_obj["w"] * op_obj["h"], 2),
                "col1_limit": round(col1_limit, 2),
                "col2_limit": round(col2_limit, 2),
                "col1_name": col1_name or "حر",
                "col2_name": col2_name or "حر",
                "is_h": is_h,
                "x_start_3d": round(x_start_3d, 3),
                "z_start_3d": round(z_start_3d, 3),
                "x": round(wx, 3),
                "y": round(y_center, 3),
                "z": round(wz, 3),
                "w": round(box_w, 3),
                "h": round(h_box, 3),
                "d": round(box_d, 3),
                "thick": round(thick, 3),
            })

        # تقسيم الحائط إلى كتل حول الفتحات
        cur = 0.0
        for op in openings:
            op_start = max(cur, op["pos"])
            op_end = min(wlen, op["pos"] + op["w"])
            if op_start > cur:
                # كتلة حائط مصمتة كاملة الارتفاع قبل الفتحة
                _add_wall_box(cur, op_start - cur, 0.0, wall_h, "wall_solid")

            op_w = op_end - op_start
            if op_w > 0.001:
                if op["type"] == "window":
                    # أسفل النافذة (جلسة)
                    sill_h = min(op["sill"], wall_h)
                    if sill_h > 0:
                        _add_wall_box(op_start, op_w, 0.0, sill_h, "wall_sill")
                    # النافذة نفسها (مسطح زجاجي شفاف)
                    if wall_h > op["sill"]:
                        win_actual_h = min(op["h"], wall_h - op["sill"])
                        _add_window_mesh(op_start, op_w, op["sill"], win_actual_h, op)
                    # أعلى النافذة (عتب)
                    lintel_bot = op["sill"] + op["h"]
                    if wall_h > lintel_bot:
                        _add_wall_box(op_start, op_w, lintel_bot, wall_h - lintel_bot, "wall_lintel")
                elif op["type"] == "door":
                    # مجسم الباب المعماري
                    door_actual_h = min(op["h"], wall_h)
                    _add_door_mesh(op_start, op_w, 0.0, door_actual_h, op)
                    # أعلى الباب (عتب)
                    door_top = op["h"]
                    if wall_h > door_top:
                        _add_wall_box(op_start, op_w, door_top, wall_h - door_top, "wall_lintel")

            cur = max(cur, op_end)

        if cur < wlen:
            # كتلة حائط مصمتة كاملة الارتفاع بعد آخر فتحة
            _add_wall_box(cur, wlen - cur, 0.0, wall_h, "wall_solid")

    ext = max(1.6, max(span_x, span_y) * 0.12)
    axes_x_data = []
    for idx, x_val in enumerate(xs):
        x_3d = round(x_val - cx_mid, 3)
        z_start = round(-((max_y + ext) - cy_mid), 3)
        z_end = round(-((min_y - ext) - cy_mid), 3)
        axes_x_data.append({
            "name": f"Y{idx+1}",
            "val": round(x_val, 2),
            "x_3d": x_3d,
            "z_start": z_start,
            "z_end": z_end,
        })

    axes_y_data = []
    for idx, y_val in enumerate(ys):
        z_3d = round(-(y_val - cy_mid), 3)
        x_start = round((min_x - ext) - cx_mid, 3)
        x_end = round((max_x + ext) - cx_mid, 3)
        axes_y_data.append({
            "name": f"X{idx+1}",
            "val": round(y_val, 2),
            "z_3d": z_3d,
            "x_start": x_start,
            "x_end": x_end,
        })

    return {
        "span_x": round(span_x, 2),
        "span_y": round(span_y, 2),
        "default_h": round(dh, 2),
        "parapet_h": round(ph, 2),
        "n_walls": len(walls_data),
        "n_columns": len(columns_data),
        "n_windows": len(windows_data),
        "n_doors": len(doors_data),
        "columns": columns_data,
        "walls": walls_data,
        "windows": windows_data,
        "doors": doors_data,
        "grid_axes": {
            "ext": round(ext, 2),
            "axes_x": axes_x_data,
            "axes_y": axes_y_data,
        },
    }


def _section_3d_viewer():
    """
    قسم العارض ثلاثي الأبعاد التفاعلي بتقنية Three.js و OrbitControls:
    3D (Data Processing & Rendering) مع مسقط أفقي مصغر تفاعلي، مقابض تحريك الأبواب والشبابيك
    البارزة ثلاثية الأبعاد والشارات العائمة، منع التعارض الهندسي، عرض أبعاد التحريك في الوقت الفعلي،
    وجعل الحائط وحدة واحدة متكاملة عند النقر على أي جزء منه حول الفتحات.
    """
    scene_data = _prepare_3d_scene_data()
    if not scene_data:
        st.info("💡 أدخل محاور الشبكة أولاً لمعاينة المبنى ثلاثي الأبعاد.")
        return

    plan_b64 = st.session_state.get("m15_plan_png_b64", "")
    if not plan_b64:
        try:
            pbuf = _draw_plan()
            if pbuf:
                plan_b64 = base64.b64encode(pbuf.getvalue()).decode("utf-8")
                st.session_state["m15_plan_png_b64"] = plan_b64
        except Exception:
            plan_b64 = ""

    json_str = json.dumps(scene_data)

    html_template = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
  body, html { width: 100%; height: 100%; overflow: hidden; background: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
  #canvas-container { width: 100%; height: 100%; position: absolute; top: 0; left: 0; cursor: grab; }
  #canvas-container:active { cursor: grabbing; }
  
  .toolbar {
    position: absolute;
    top: 10px;
    left: 10px;
    right: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    pointer-events: none;
    z-index: 20;
  }
  .tb-group {
    display: flex;
    gap: 8px;
    align-items: center;
    pointer-events: auto;
    background: rgba(15, 23, 42, 0.88);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(148, 163, 184, 0.3);
    border-radius: 8px;
    padding: 5px 10px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.3);
  }
  .btn-tool {
    background: #1e293b;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 5px 11px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.2s ease;
  }
  .btn-tool:hover {
    background: #334155;
    border-color: #ffffff;
    color: #ffffff;
  }
  .badge-legend {
    font-size: 11px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    display: inline-block;
  }
  
  .stats-panel {
    position: absolute;
    bottom: 10px;
    right: 10px;
    background: rgba(15, 23, 42, 0.88);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(148, 163, 184, 0.3);
    border-radius: 8px;
    padding: 6px 14px;
    color: #cbd5e1;
    font-size: 11.5px;
    display: flex;
    gap: 12px;
    align-items: center;
    pointer-events: auto;
    z-index: 10;
    box-shadow: 0 4px 14px rgba(0,0,0,0.3);
  }
  .stats-item b {
    color: #ffffff;
  }

  .help-tip {
    position: absolute;
    bottom: 10px;
    left: 10px;
    background: rgba(15, 23, 42, 0.88);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(148, 163, 184, 0.3);
    border-radius: 8px;
    padding: 6px 12px;
    color: #94a3b8;
    font-size: 11px;
    pointer-events: auto;
    z-index: 10;
  }

  /* ── لوحة المسقط الأفقي المصغر (Mini-Plan Panel) ── */
  .mini-plan-panel {
    position: absolute;
    top: 55px;
    left: 12px;
    width: 280px;
    background: rgba(15, 23, 42, 0.94);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(148, 163, 184, 0.35);
    border-radius: 9px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    z-index: 25;
    overflow: hidden;
    user-select: none;
    transition: width 0.2s ease, opacity 0.2s ease;
  }
  .mini-plan-header {
    background: rgba(30, 41, 59, 0.96);
    padding: 6px 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: move;
    border-bottom: 1px solid rgba(148, 163, 184, 0.25);
  }
  .mini-plan-title {
    font-size: 11.5px;
    font-weight: 700;
    color: #f8fafc;
    display: flex;
    align-items: center;
    gap: 5px;
    pointer-events: none;
  }
  .mini-plan-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .mini-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 12px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    line-height: 1;
    transition: all 0.15s ease;
  }
  .mini-btn:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #ffffff;
  }
  .mini-plan-body {
    padding: 8px;
    background: #0f172a;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .mini-plan-img-wrapper {
    width: 100%;
    border-radius: 6px;
    overflow: hidden;
    background: #ffffff;
    border: 1px solid #334155;
    cursor: zoom-in;
    position: relative;
    box-shadow: inset 0 0 4px rgba(0,0,0,0.1);
  }
  .mini-plan-img {
    width: 100%;
    height: auto;
    max-height: 170px;
    object-fit: contain;
    display: block;
    transition: transform 0.2s ease;
  }
  .mini-plan-img-wrapper:hover .mini-plan-img {
    transform: scale(1.02);
  }
  .mini-plan-zoom-hint {
    position: absolute;
    bottom: 4px;
    left: 4px;
    background: rgba(15, 23, 42, 0.85);
    color: #ffffff;
    font-size: 9px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 4px;
    pointer-events: none;
    opacity: 0.85;
  }
  .mini-plan-caption {
    font-size: 10px;
    color: #94a3b8;
    margin-top: 5px;
    text-align: center;
    font-weight: 500;
  }
  .mini-plan-panel.minimized {
    width: 180px;
  }
  .mini-plan-panel.minimized .mini-plan-body {
    display: none;
  }

  /* ── نافذة تكبير المسقط (Modal) ── */
  .plan-modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 100;
    align-items: center;
    justify-content: center;
    padding: 15px;
  }
  .plan-modal-backdrop {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(15, 23, 42, 0.80);
    backdrop-filter: blur(6px);
  }
  .plan-modal-content {
    position: relative;
    max-width: 92%;
    max-height: 92%;
    background: #1e293b;
    border: 1px solid #475569;
    border-radius: 10px;
    box-shadow: 0 16px 36px rgba(0,0,0,0.6);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    z-index: 101;
  }
  .plan-modal-header {
    padding: 8px 14px;
    background: #0f172a;
    border-bottom: 1px solid #334155;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #f8fafc;
    font-size: 12.5px;
    font-weight: 700;
    direction: ltr;
  }
  .modal-close-btn {
    background: #334155;
    color: #f1f5f9;
    border: none;
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 12px;
    cursor: pointer;
    font-weight: 600;
  }
  .modal-close-btn:hover { background: #ef4444; }
  .plan-modal-body {
    padding: 8px;
    background: #ffffff;
    overflow: auto;
    display: flex;
    justify-content: center;
    align-items: center;
  }
  .modal-img { max-width: 100%; max-height: 75vh; object-fit: contain; }

  /* ── لوحة فاحص العناصر ثلاثية الأبعاد (3D Element Inspector Panel) ── */
  .inspector-panel {
    position: absolute;
    top: 55px;
    right: 12px;
    width: 325px;
    max-height: calc(100% - 110px);
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1.5px solid #38bdf8;
    border-radius: 10px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.65);
    z-index: 25;
    overflow: hidden;
    display: none;
    flex-direction: column;
    animation: slideInRtl 0.2s ease-out;
  }
  @keyframes slideInRtl {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
  }
  .inspector-header {
    background: rgba(30, 41, 59, 0.98);
    padding: 8px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(148, 163, 184, 0.25);
  }
  .inspector-title {
    font-size: 12.5px;
    font-weight: 700;
    color: #f8fafc;
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .inspector-body {
    padding: 12px;
    overflow-y: auto;
    font-size: 11.5px;
    color: #cbd5e1;
    line-height: 1.6;
  }
  .insp-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10.5px;
    font-weight: 700;
    margin-bottom: 6px;
  }
  .wall-tag { background: #0369a1; color: #ffffff; border: 1px solid #38bdf8; }
  .win-tag { background: #0284c7; color: #ffffff; border: 1px solid #7dd3fc; }
  .door-tag { background: #b45309; color: #ffffff; border: 1px solid #fde68a; }
  .col-tag { background: #334155; color: #cbd5e1; border: 1px solid #64748b; }

  .insp-name {
    font-size: 13.5px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 3px;
  }
  .insp-sub {
    font-size: 11px;
    color: #94a3b8;
    margin-bottom: 10px;
    border-bottom: 1px dashed rgba(148, 163, 184, 0.3);
    padding-bottom: 6px;
  }
  .insp-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px 10px;
    margin-bottom: 10px;
  }
  .insp-item {
    background: rgba(30, 41, 59, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 5px;
    padding: 5px 8px;
  }
  .insp-label { font-size: 10px; color: #94a3b8; display: block; margin-bottom: 2px; }
  .insp-val { font-size: 11.5px; font-weight: 700; color: #f1f5f9; }
  .insp-val b { color: #ffffff; }
  .insp-section-title {
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    margin: 8px 0 5px 0;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .insp-actions {
    margin-top: 10px;
    display: flex;
    gap: 6px;
  }
  .insp-btn {
    flex: 1;
    background: #0284c7;
    color: #ffffff;
    border: 1px solid #38bdf8;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    text-align: center;
    transition: all 0.15s;
  }
  .insp-btn:hover { background: #0369a1; }

  /* ── شارات الأبعاد الثلاثية الأبعاد (Live 3D Dimensions Badges) ── */
  .dim-badge {
    position: absolute;
    background: rgba(15, 23, 42, 0.94);
    border: 1.5px solid #ffffff;
    color: #ffffff;
    font-weight: 800;
    font-size: 10.5px;
    padding: 2px 8px;
    border-radius: 5px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.55);
    pointer-events: none;
    z-index: 30;
    white-space: nowrap;
    transform: translate(-50%, -50%);
    transition: opacity 0.1s;
  }
  /* ── شريط إجراءات الحائط العائم (Floating Wall Action Bar) ── */
  .wall-floating-bar {
    position: absolute;
    bottom: 22px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(15, 23, 42, 0.94);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1.5px solid #ef4444;
    border-radius: 10px;
    padding: 8px 16px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.55), 0 0 15px rgba(239, 68, 68, 0.25);
    z-index: 30;
    user-select: none;
    animation: bounceInUp 0.25s ease-out;
  }
  @keyframes bounceInUp {
    from { opacity: 0; transform: translate(-50%, 20px); }
    to { opacity: 1; transform: translate(-50%, 0); }
  }
  .wbar-info { display: flex; align-items: center; gap: 10px; }
  .wbar-icon { font-size: 20px; line-height: 1; }
  .wbar-title { font-size: 13px; font-weight: 800; color: #f8fafc; }
  .wbar-sub { font-size: 11px; color: #94a3b8; }
  .wbar-actions { display: flex; align-items: center; gap: 8px; }
  .wbar-btn-del {
    background: linear-gradient(135deg, #ef4444, #dc2626);
    color: #ffffff;
    border: 1px solid #f87171;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    box-shadow: 0 2px 6px rgba(220, 38, 38, 0.4);
    transition: all 0.15s ease;
  }
  .wbar-btn-del:hover { background: #b91c1c; transform: translateY(-1px); }
  .wbar-btn-cancel {
    background: #334155;
    color: #cbd5e1;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .wbar-btn-cancel:hover { background: #475569; color: #ffffff; }

  /* ── شريط إرشادات أداة القياس ثلاثية الأبعاد (3D Measure Banner) ── */
  .measure-banner {
    position: absolute;
    top: 55px;
    left: 50%;
    transform: translateX(-50%);
    background: transparent; /* خلفية شفافة تماماً 100% لإظهار كامل عناصر المشهد ثلاثي الأبعاد خلفها */
    border: 1.5px solid #38bdf8;
    border-radius: 8px;
    padding: 8px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.45);
    z-index: 35;
    user-select: none;
    color: #ffffff;
    text-shadow: 0 1px 4px rgba(0, 0, 0, 0.95), 0 2px 8px rgba(0, 0, 0, 0.9);
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
    animation: bounceInDown 0.25s ease-out;
  }
  @keyframes bounceInDown {
    from { opacity: 0; transform: translate(-50%, -20px); }
    to { opacity: 1; transform: translate(-50%, 0); }
  }
  .measure-banner-close {
    background: #334155;
    color: #cbd5e1;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .measure-banner-close:hover {
    background: #ef4444;
    color: #ffffff;
    border-color: #f87171;
  }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
<div id="canvas-container"></div>

<!-- شريط الأدوات العلوي -->
<div class="toolbar">
  <div class="tb-group">
    <button class="btn-tool" id="btn-reset" title="إعادة ضبط زاوية الكاميرا للوضع الافتراضي">🔄 ضبط الكاميرا</button>
    <button class="btn-tool" id="btn-theme" title="تبديل لون الخلفية">🌙 / ☀️</button>
    <button class="btn-tool" id="btn-fs" title="عرض ملء الشاشة">⛶ ملء الشاشة</button>
    <button class="btn-tool" id="btn-toggle-plan" style="background:#0284c7; border-color:#38bdf8; color:#ffffff; font-weight:700;" title="عرض أو إخفاء المسقط الأفقي المصغر">📐 المسقط الأفقي</button>
    <button class="btn-tool" id="btn-toggle-axes" style="background:#dc2626; border-color:#f87171; color:#ffffff; font-weight:700;" title="إظهار أو إخفاء محاور الشبكة وأسمائها ثلاثية الأبعاد">🔴 المحاور</button>
    <button class="btn-tool" id="btn-measure" title="أداة قياس تفاعلية ثلاثية الأبعاد بين أي نقطتين">📏 أداة القياس</button>
    <button class="btn-tool" id="btn-clear-measure" style="display:none; background:#7f1d1d; border-color:#ef4444; color:#ffffff; font-weight:700;" title="مسح القياس والعودة للوضع الافتراضي">🗑️ مسح القياس</button>
  </div>
  <div class="tb-group">
    <span class="badge-legend" style="color:#fca5a5;"><span class="dot" style="background:#dc2626; border:1px solid #ef4444;"></span> محاور (حمراء)</span>
    <span class="badge-legend" style="color:#f1f5f9;"><span class="dot" style="background:#cbd5e1; border:1px solid #94a3b8;"></span> حائط كامل (وحدة واحدة)</span>
    <span class="badge-legend" style="color:#cbd5e1;"><span class="dot" style="background:#475569; border:1px solid #334155;"></span> أعمدة</span>
    <span class="badge-legend" style="color:#ffffff;"><span class="dot" style="background:#38bdf8; opacity:0.85; border:1px solid #ffffff;"></span> شبابيك (مقبض ⟷)</span>
    <span class="badge-legend" style="color:#f59e0b;"><span class="dot" style="background:#b45309; border:1px solid #f59e0b;"></span> أبواب (مقبض ⟷)</span>
    <span class="badge-legend" style="color:#38bdf8;"><span class="dot" style="background:#0284c7; border:1px solid #38bdf8;"></span> أداة القياس</span>
  </div>
</div>

<!-- شريط إرشادات أداة القياس ثلاثية الأبعاد -->
<div id="measure-banner" class="measure-banner" style="display:none;">
  <span id="measure-banner-icon">📏</span>
  <span id="measure-banner-text">وضع القياس ثلاثي الأبعاد: انقر بالزر الأيسر لتحديد نقطة البداية (Point A) • التدوير بالزر الأيمن أو العجلة • اضغط Esc للإلغاء</span>
  <button id="btn-measure-banner-close" class="measure-banner-close" title="إلغاء وضع القياس">✕</button>
</div>

<!-- حاوية شارات الأبعاد الثلاثية الأبعاد (باللون اللبني فقط) -->
<div id="dim-badge-1" class="dim-badge" style="display:none;"></div>
<div id="dim-badge-3" class="dim-badge" style="display:none;"></div>

<!-- لوحة فاحص العناصر (3D Element Inspector Panel) -->
<div id="inspector-card" class="inspector-panel">
  <div class="inspector-header">
    <div class="inspector-title">
      <span id="insp-icon">🧱</span>
      <span id="insp-header-text">فاحص مواصفات العنصر</span>
    </div>
    <button class="mini-btn" id="btn-insp-close" title="إغلاق اللوحة">✕</button>
  </div>
  <div class="inspector-body" id="insp-body">
    <!-- محتوى مواصفات العنصر المختار ديناميكياً -->
  </div>
</div>

<!-- شريط إجراءات الحائط العائم أسفل الشاشة ثلاثية الأبعاد (3D Wall Floating Action Bar) -->
<div id="wall-floating-bar" class="wall-floating-bar" style="display:none;">
  <div class="wbar-info">
    <span class="wbar-icon" id="wbar-icon">🧱</span>
    <div class="wbar-text">
      <div class="wbar-title" id="wbar-title">الحائط المحدد</div>
      <div class="wbar-sub" id="wbar-sub">تفاصيل الحائط</div>
    </div>
  </div>
  <div class="wbar-actions" id="wbar-actions-init">
    <button class="wbar-btn-del" id="btn-wbar-del-init">
      🗑️ حذف هذا الحائط
    </button>
    <button class="wbar-btn-cancel" id="btn-wbar-cancel">
      ✕ إلغاء
    </button>
  </div>
  <div class="wbar-actions" id="wbar-actions-confirm" style="display:none;">
    <span id="wbar-confirm-prompt" style="color:#fca5a5; font-size:11.5px; font-weight:700;">⚠️ تأكيد الحذف؟</span>
    <button class="wbar-btn-del" id="btn-wbar-del-confirm" style="background:#dc2626; box-shadow:0 2px 8px rgba(220,38,38,0.6);">
      ✅ نعم، احذف
    </button>
    <button class="wbar-btn-cancel" id="btn-wbar-cancel-confirm">
      تراجع
    </button>
  </div>
</div>

<!-- لوحة المسقط الأفقي المصغر على جانب الشاشة -->
<div id="mini-plan-card" class="mini-plan-panel">
  <div class="mini-plan-header" id="mini-plan-drag" title="اسحب لتحريك المسقط">
    <div class="mini-plan-title">
      <span>📐 المسقط المصغر (2D Plan)</span>
    </div>
    <div class="mini-plan-actions">
      <button class="mini-btn" id="btn-mini-expand" title="تكبير المعاينة">🔍</button>
      <button class="mini-btn" id="btn-mini-toggle" title="طي / توسيع">➖</button>
      <button class="mini-btn" id="btn-mini-close" title="إخفاء">✕</button>
    </div>
  </div>
  <div class="mini-plan-body" id="mini-plan-body">
    <div class="mini-plan-img-wrapper" id="mini-plan-wrapper" title="انقر لتكبير المسقط الأفقي">
      <img src="data:image/png;base64,__PLAN_B64__" alt="Floor Plan — Module 15: Brick & Plastering Survey" class="mini-plan-img" id="mini-plan-img" />
      <div class="mini-plan-zoom-hint">🔍 انقر للتكبير</div>
    </div>
    <div class="mini-plan-caption">Floor Plan — Module 15: Brick & Plastering Survey</div>
  </div>
</div>

<!-- نافذة تكبير المسقط (Lightbox Modal) -->
<div id="plan-modal" class="plan-modal">
  <div class="plan-modal-backdrop" id="modal-backdrop"></div>
  <div class="plan-modal-content">
    <div class="plan-modal-header">
      <span>📐 Floor Plan — Module 15: Brick & Plastering Survey</span>
      <button class="modal-close-btn" id="modal-close">✕ إغلاق</button>
    </div>
    <div class="plan-modal-body">
      <img src="data:image/png;base64,__PLAN_B64__" class="modal-img" alt="Floor Plan Full" />
    </div>
  </div>
</div>

<div class="stats-panel">
  <span class="stats-item">🧱 الحوائط: <b>__N_WALLS__</b></span>
  <span class="stats-item">🏛️ الأعمدة: <b>__N_COLS__</b></span>
  <span class="stats-item">🪟 الشبابيك: <b>__N_WINS__</b></span>
  <span class="stats-item">🚪 الأبواب: <b>__N_DOORS__</b></span>
  <span class="stats-item">📐 الارتفاع: <b>__DEF_H__م</b> (الدروة: <b>__PAR_H__م</b>)</span>
</div>

<div class="help-tip">
  🖱️ تدوير: سحب بالماوس &nbsp;|&nbsp; Zoom: عجلة &nbsp;|&nbsp; 👈 انقر على الحائط لاختياره كوحدة كاملة &nbsp;|&nbsp; ⟷ اسحب المقبض لتحريك الفتحة
</div>

<script>
(function() {
  const data = __SCENE_DATA__;
  const container = document.getElementById('canvas-container');

  // Scene & Background
  const scene = new THREE.Scene();
  const bgDark = 0x0f172a;
  const bgLight = 0xf8fafc;
  let isDark = true;
  scene.background = new THREE.Color(bgDark);

  // Camera
  const width = window.innerWidth;
  const height = window.innerHeight;
  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);

  // Renderer
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = false;
  container.appendChild(renderer.domElement);

  // OrbitControls
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;
  controls.minDistance = 1.0;
  controls.maxDistance = 250.0;
  controls.maxPolarAngle = Math.PI / 2 + 0.1;

  // Architectural Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
  scene.add(ambientLight);

  const maxDim = Math.max(data.span_x || 10, data.span_y || 10, 8.0);

  const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.90);
  dirLight1.position.set(maxDim * 1.5, maxDim * 2.2, maxDim * 1.4);
  scene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(0x93c5fd, 0.45);
  dirLight2.position.set(-maxDim * 1.5, maxDim * 1.2, -maxDim * 1.4);
  scene.add(dirLight2);

  const rootGroup = new THREE.Group();
  scene.add(rootGroup);

  // Materials
  const wallMat = new THREE.MeshStandardMaterial({ color: 0xd4d4d8, roughness: 0.80, metalness: 0.05 });
  const parapetWallMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.70, metalness: 0.10 });
  const wallEdgeMat = new THREE.LineBasicMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.60 });

  const colMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.90, metalness: 0.10 });
  const colEdgeMat = new THREE.LineBasicMaterial({ color: 0x1e293b, transparent: true, opacity: 0.75 });

  const winMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.50, roughness: 0.10, metalness: 0.25 });
  const winEdgeMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85 });

  const doorMat = new THREE.MeshStandardMaterial({ color: 0x92400e, roughness: 0.60, metalness: 0.15 });
  const doorEdgeMat = new THREE.LineBasicMaterial({ color: 0x78350f, transparent: true, opacity: 0.90 });
  const doorKnobMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.20, metalness: 0.80 });

  // Handle Materials (Accurate Depth Testing & Depth Write - Occlusion Aware)
  const handleMat = new THREE.MeshStandardMaterial({
    color: 0xfbbf24,
    emissive: 0xd97706,
    emissiveIntensity: 0.8,
    roughness: 0.2,
    metalness: 0.5,
    depthTest: true,
    depthWrite: true
  });
  const handleHoverMat = new THREE.MeshStandardMaterial({
    color: 0x38bdf8,
    emissive: 0x0284c7,
    emissiveIntensity: 0.9,
    roughness: 0.15,
    metalness: 0.6,
    depthTest: true,
    depthWrite: true
  });
  const handleDragMat = new THREE.MeshStandardMaterial({
    color: 0x34d399,
    emissive: 0x059669,
    emissiveIntensity: 0.9,
    roughness: 0.15,
    metalness: 0.6,
    depthTest: true,
    depthWrite: true
  });
  const handleWarnMat = new THREE.MeshStandardMaterial({
    color: 0xf87171,
    emissive: 0xdc2626,
    emissiveIntensity: 1.0,
    roughness: 0.15,
    metalness: 0.6,
    depthTest: true,
    depthWrite: true
  });

  // Selection Outline Material (Vivid Red)
  const highlightMat = new THREE.LineBasicMaterial({ color: 0xff0000, linewidth: 2.5, depthTest: false, transparent: true, opacity: 0.98 });

  // 3D Dimension Lines Material (Pure White)
  const dimLineMat = new THREE.LineBasicMaterial({ color: 0xffffff, depthTest: false, transparent: true, opacity: 0.95 });

  // Collections for Raycasting & Selection
  const selectableObjects = [];
  const handleMeshes = [];
  const wallGroups = {};
  const allOpenings = [];
  const openingMeshesById = {};

  // ── 0. Red Grid Axes & Name Labels (المحاور الإنشائية وأسماؤها باللون الأحمر) ──
  const axesGroup = new THREE.Group();
  axesGroup.name = "grid_axes_group";
  rootGroup.add(axesGroup);

  const axisRedMat = new THREE.MeshStandardMaterial({
    color: 0xef4444,
    emissive: 0xdc2626,
    emissiveIntensity: 0.35,
    roughness: 0.35,
    metalness: 0.15
  });
  const axisRedLineMat = new THREE.LineBasicMaterial({
    color: 0xef4444,
    linewidth: 2,
    transparent: true,
    opacity: 0.90
  });

  function createAxisBubbleSprite(name, valText, spriteSize) {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext('2d');

    // Canvas Clear
    ctx.clearRect(0, 0, 256, 256);

    // Drop shadow
    ctx.shadowColor = 'rgba(0, 0, 0, 0.40)';
    ctx.shadowBlur = 12;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 4;

    // Outer circle fill
    ctx.beginPath();
    ctx.arc(128, 128, 102, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    // Reset shadow
    ctx.shadowColor = 'transparent';

    // Outer bold red border
    ctx.beginPath();
    ctx.arc(128, 128, 102, 0, Math.PI * 2);
    ctx.lineWidth = 12;
    ctx.strokeStyle = '#dc2626';
    ctx.stroke();

    // Inner accent red ring
    ctx.beginPath();
    ctx.arc(128, 128, 92, 0, Math.PI * 2);
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#fca5a5';
    ctx.stroke();

    // Text in RED
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    ctx.fillStyle = '#dc2626';
    ctx.font = 'bold 74px "Segoe UI", Arial, sans-serif';
    ctx.fillText(name, 128, valText ? 104 : 128);

    if (valText) {
      ctx.fillStyle = '#991b1b';
      ctx.font = 'bold 34px "Segoe UI", Arial, sans-serif';
      ctx.fillText(valText, 128, 168);
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;

    const mat = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: true,
      depthWrite: false
    });

    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(spriteSize, spriteSize, 1.0);
    sprite.renderOrder = 950;
    return sprite;
  }

  const gAxes = data.grid_axes || {};
  const gAxesX = gAxes.axes_x || [];
  const gAxesY = gAxes.axes_y || [];

  let minSp = 999.0;
  gAxesX.forEach(function(ax, idx) {
    if (idx < gAxesX.length - 1) minSp = Math.min(minSp, Math.abs(gAxesX[idx + 1].val - ax.val));
  });
  gAxesY.forEach(function(ay, idx) {
    if (idx < gAxesY.length - 1) minSp = Math.min(minSp, Math.abs(gAxesY[idx + 1].val - ay.val));
  });
  if (minSp <= 0 || minSp > 100) minSp = 3.0;
  const axisBubbleSize = Math.max(0.60, Math.min(1.05, minSp * 0.55, maxDim * 0.065));

  // 1) X-Axes (parallel to Z in 3D)
  gAxesX.forEach(function(ax) {
    const lenZ = Math.abs(ax.z_end - ax.z_start);
    if (lenZ <= 0.01) return;

    // Solid red 3D line (thin cylinder)
    const cylGeom = new THREE.CylinderGeometry(0.018, 0.018, lenZ, 12);
    const cylMesh = new THREE.Mesh(cylGeom, axisRedMat);
    cylMesh.rotation.x = Math.PI / 2;
    cylMesh.position.set(ax.x_3d, 0.015, (ax.z_start + ax.z_end) / 2);
    axesGroup.add(cylMesh);

    // Backup crisp line
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(ax.x_3d, 0.015, ax.z_start),
      new THREE.Vector3(ax.x_3d, 0.015, ax.z_end)
    ]);
    axesGroup.add(new THREE.Line(lineGeo, axisRedLineMat));

    // End 1 (North)
    const stalk1 = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, 0.38, 12), axisRedMat);
    stalk1.position.set(ax.x_3d, 0.20, ax.z_start);
    axesGroup.add(stalk1);
    const anchor1 = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.02, 16), axisRedMat);
    anchor1.position.set(ax.x_3d, 0.02, ax.z_start);
    axesGroup.add(anchor1);
    const sprite1 = createAxisBubbleSprite(ax.name, ax.val.toFixed(2) + "m", axisBubbleSize);
    sprite1.position.set(ax.x_3d, 0.48, ax.z_start);
    axesGroup.add(sprite1);

    // End 2 (South)
    const stalk2 = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, 0.38, 12), axisRedMat);
    stalk2.position.set(ax.x_3d, 0.20, ax.z_end);
    axesGroup.add(stalk2);
    const anchor2 = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.02, 16), axisRedMat);
    anchor2.position.set(ax.x_3d, 0.02, ax.z_end);
    axesGroup.add(anchor2);
    const sprite2 = createAxisBubbleSprite(ax.name, ax.val.toFixed(2) + "m", axisBubbleSize);
    sprite2.position.set(ax.x_3d, 0.48, ax.z_end);
    axesGroup.add(sprite2);
  });

  // 2) Y-Axes (parallel to X in 3D)
  gAxesY.forEach(function(ay) {
    const lenX = Math.abs(ay.x_end - ay.x_start);
    if (lenX <= 0.01) return;

    // Solid red 3D line (thin cylinder)
    const cylGeom = new THREE.CylinderGeometry(0.018, 0.018, lenX, 12);
    const cylMesh = new THREE.Mesh(cylGeom, axisRedMat);
    cylMesh.rotation.z = Math.PI / 2;
    cylMesh.position.set((ay.x_start + ay.x_end) / 2, 0.015, ay.z_3d);
    axesGroup.add(cylMesh);

    // Backup crisp line
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(ay.x_start, 0.015, ay.z_3d),
      new THREE.Vector3(ay.x_end, 0.015, ay.z_3d)
    ]);
    axesGroup.add(new THREE.Line(lineGeo, axisRedLineMat));

    // End 1 (West)
    const stalk1 = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, 0.38, 12), axisRedMat);
    stalk1.position.set(ay.x_start, 0.20, ay.z_3d);
    axesGroup.add(stalk1);
    const anchor1 = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.02, 16), axisRedMat);
    anchor1.position.set(ay.x_start, 0.02, ay.z_3d);
    axesGroup.add(anchor1);
    const sprite1 = createAxisBubbleSprite(ay.name, ay.val.toFixed(2) + "m", axisBubbleSize);
    sprite1.position.set(ay.x_start, 0.48, ay.z_3d);
    axesGroup.add(sprite1);

    // End 2 (East)
    const stalk2 = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, 0.38, 12), axisRedMat);
    stalk2.position.set(ay.x_end, 0.20, ay.z_3d);
    axesGroup.add(stalk2);
    const anchor2 = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.02, 16), axisRedMat);
    anchor2.position.set(ay.x_end, 0.02, ay.z_3d);
    axesGroup.add(anchor2);
    const sprite2 = createAxisBubbleSprite(ay.name, ay.val.toFixed(2) + "m", axisBubbleSize);
    sprite2.position.set(ay.x_end, 0.48, ay.z_3d);
    axesGroup.add(sprite2);
  });

  // 1. Columns (الأعمدة)
  (data.columns || []).forEach(function(c) {
    const geom = new THREE.BoxGeometry(c.w, c.h, c.d);
    const mesh = new THREE.Mesh(geom, colMat.clone());
    mesh.position.set(c.x, c.y, c.z);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom), colEdgeMat.clone());
    mesh.add(edges);
    mesh.userData = { elementType: 'column', data: c };
    rootGroup.add(mesh);
    selectableObjects.push(mesh);
  });

  // 2. Walls as Single Unified Units (الحوائط كوحدة واحدة متكاملة)
  (data.walls || []).forEach(function(w) {
    const keyStr = JSON.stringify(w.wall_key);
    let wallGroup = wallGroups[keyStr];
    if (!wallGroup) {
      wallGroup = new THREE.Group();
      wallGroup.name = "wall_group_" + keyStr;
      wallGroup.userData = { elementType: 'wall', wallKeyStr: keyStr, data: w };
      wallGroups[keyStr] = wallGroup;
      wallGroup.wallPieces = [];
      rootGroup.add(wallGroup);
    }

    const geom = new THREE.BoxGeometry(w.w, w.h, w.d);
    const meshMat = (w.is_parapet ? parapetWallMat : wallMat).clone();
    const mesh = new THREE.Mesh(geom, meshMat);
    mesh.position.set(w.x, w.y, w.z);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom), wallEdgeMat.clone());
    mesh.add(edges);

    mesh.userData = {
      elementType: 'wall_piece',
      parentWallGroup: wallGroup,
      wallKeyStr: keyStr,
      data: w,
      pieceData: w
    };

    wallGroup.add(mesh);
    wallGroup.wallPieces.push({ mesh: mesh, data: w });
    selectableObjects.push(mesh);
  });

  // ── إنشاء مقبض ثلاثي الأبعاد بارز وخاضع لاختبار العمق (Depth-Tested 3D Handle) ──
  function create3DHandle(op, isDoor) {
    const hGroup = new THREE.Group();
    const isH = op.is_h;

    // Bar dimensions - prominent horizontal grip bar
    const barLen = Math.max(0.45, Math.min(0.85, op.w_m * 0.50));
    const barRad = 0.055;
    const barGeom = new THREE.CylinderGeometry(barRad, barRad, barLen, 16);
    const barMesh = new THREE.Mesh(barGeom, handleMat);
    if (isH) {
      barMesh.rotation.z = Math.PI / 2;
    } else {
      barMesh.rotation.x = Math.PI / 2;
    }
    hGroup.add(barMesh);

    // Arrow cones at both ends
    const coneGeom = new THREE.ConeGeometry(0.09, 0.16, 16);
    const cone1 = new THREE.Mesh(coneGeom, handleMat);
    const cone2 = new THREE.Mesh(coneGeom, handleMat);

    if (isH) {
      cone1.rotation.z = -Math.PI / 2;
      cone1.position.x = barLen / 2 + 0.08;
      cone2.rotation.z = Math.PI / 2;
      cone2.position.x = -(barLen / 2 + 0.08);
    } else {
      cone1.rotation.x = Math.PI / 2;
      cone1.position.z = barLen / 2 + 0.08;
      cone2.rotation.x = -Math.PI / 2;
      cone2.position.z = -(barLen / 2 + 0.08);
    }
    hGroup.add(cone1);
    hGroup.add(cone2);

    // Center grip sphere
    const sphereGeom = new THREE.SphereGeometry(0.085, 16, 16);
    const sphereMesh = new THREE.Mesh(sphereGeom, handleMat);
    hGroup.add(sphereMesh);

    // Outer prominent ring
    const ringGeom = new THREE.TorusGeometry(0.12, 0.022, 12, 24);
    const ringMesh = new THREE.Mesh(ringGeom, handleMat);
    if (!isH) ringMesh.rotation.y = Math.PI / 2;
    hGroup.add(ringMesh);

    // Invisible pickup volume to make grabbing the handle effortless from any angle
    const hitBoxGeom = new THREE.BoxGeometry(
      isH ? Math.max(0.70, barLen + 0.35) : 0.40,
      0.40,
      isH ? 0.40 : Math.max(0.70, barLen + 0.35)
    );
    const hitBoxMat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false });
    const hitBoxMesh = new THREE.Mesh(hitBoxGeom, hitBoxMat);
    hitBoxMesh.userData = { isHitBox: true, isHandle: true, op: op };
    hGroup.add(hitBoxMesh);

    // Position handle at the center of the opening where it is open space (NOT inside lintel!)
    const yHandle = isDoor ? (op.h / 2.0) : op.y;
    hGroup.position.set(op.x, yHandle, op.z);

    hGroup.userData = {
      isHandle: true,
      elementType: 'handle',
      isDoor: isDoor,
      op: op,
      barMesh: barMesh,
      cone1: cone1,
      cone2: cone2,
      sphereMesh: sphereMesh,
      ringMesh: ringMesh,
      hitBoxMesh: hitBoxMesh
    };

    hGroup.children.forEach(c => {
      c.userData = c.userData || {};
      c.userData.isHandle = true;
      c.userData.op = op;
    });

    rootGroup.add(hGroup);
    handleMeshes.push(hGroup);

    return hGroup;
  }

  // 3. Windows (الشبابيك - كوحدة منفصلة قابلة للتحريك)
  (data.windows || []).forEach(function(win) {
    const geom = new THREE.BoxGeometry(win.w, win.h, win.d);
    const mesh = new THREE.Mesh(geom, winMat.clone());
    mesh.position.set(win.x, win.y, win.z);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom), winEdgeMat.clone());
    mesh.add(edges);
    mesh.userData = { elementType: 'window', data: win };
    rootGroup.add(mesh);
    selectableObjects.push(mesh);
    openingMeshesById[win.id] = mesh;

    // Handle Gizmo
    const hGizmo = create3DHandle(win, false);
    win.handleGroup = hGizmo;
    win.mesh = mesh;
    allOpenings.push(win);
  });

  // 4. Doors (الأبواب - كوحدة منفصلة قابلة للتحريك)
  (data.doors || []).forEach(function(door) {
    const doorGroup = new THREE.Group();
    doorGroup.position.set(door.x, door.y, door.z);

    // Door leaf (ضلفة الباب الخشبية)
    const geom = new THREE.BoxGeometry(door.w, door.h, door.d);
    const mesh = new THREE.Mesh(geom, doorMat.clone());
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom), doorEdgeMat.clone());
    mesh.add(edges);
    doorGroup.add(mesh);

    // Decorative door knob / handle (أكرة الباب)
    const knobGeom = new THREE.CylinderGeometry(0.02, 0.02, 0.08, 8);
    const knob = new THREE.Mesh(knobGeom, doorKnobMat.clone());
    const knobOffset = door.w * 0.35;
    if (door.is_h) {
      knob.rotation.x = Math.PI / 2;
      knob.position.set(knobOffset, 0, (door.d / 2) + 0.03);
    } else {
      knob.rotation.z = Math.PI / 2;
      knob.position.set((door.d / 2) + 0.03, 0, knobOffset);
    }
    doorGroup.add(knob);

    doorGroup.userData = { elementType: 'door', data: door };
    mesh.userData = { elementType: 'door', data: door, parentGroup: doorGroup };
    knob.userData = { elementType: 'door', data: door, parentGroup: doorGroup };
    rootGroup.add(doorGroup);
    selectableObjects.push(mesh);
    openingMeshesById[door.id] = doorGroup;

    // Handle Gizmo
    const hGizmo = create3DHandle(door, true);
    door.handleGroup = hGizmo;
    door.mesh = doorGroup;
    allOpenings.push(door);
  });

  // ── 3D Dimension Lines & Witness Marks ──
  const dimLineGeo = new THREE.BufferGeometry();
  const dimLine = new THREE.LineSegments(dimLineGeo, dimLineMat);
  dimLine.renderOrder = 999;
  scene.add(dimLine);

  // ── Selection Highlight System (تحديد العنصر بلون أحمر وبخطوط سميكة) ──
  let selectedObject = null;
  let highlightWire = null;

  // ── High-Precision Live Hover Bounding Box System (المؤشر البصري اللحظي) ──
  const hoverBoxGroup = new THREE.Group();
  hoverBoxGroup.name = "hover_bounding_box_group";
  hoverBoxGroup.visible = false;
  scene.add(hoverBoxGroup);

  const hoverWireGeom = new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1));
  const hoverWireMat = new THREE.LineBasicMaterial({
    color: 0x00f0ff,
    linewidth: 2.5,
    depthTest: true,
    depthWrite: false,
    transparent: true,
    opacity: 0.95
  });
  const hoverWireMesh = new THREE.LineSegments(hoverWireGeom, hoverWireMat);
  hoverWireMesh.renderOrder = 998;
  hoverBoxGroup.add(hoverWireMesh);

  const hoverFillGeom = new THREE.BoxGeometry(1, 1, 1);
  const hoverFillMat = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
    transparent: true,
    opacity: 0.12,
    depthTest: true,
    depthWrite: false,
    side: THREE.DoubleSide
  });
  const hoverFillMesh = new THREE.Mesh(hoverFillGeom, hoverFillMat);
  hoverFillMesh.renderOrder = 997;
  hoverBoxGroup.add(hoverFillMesh);

  // Corner Accent Brackets for CAD Precision
  const cornerBracketGeo = new THREE.BufferGeometry();
  const cornerBracketPositions = new Float32Array(144);
  cornerBracketGeo.setAttribute('position', new THREE.BufferAttribute(cornerBracketPositions, 3));
  const cornerBracketMat = new THREE.LineBasicMaterial({
    color: 0xffffff,
    linewidth: 3.0,
    depthTest: true,
    depthWrite: false,
    transparent: true,
    opacity: 0.98
  });
  const cornerBracketMesh = new THREE.LineSegments(cornerBracketGeo, cornerBracketMat);
  cornerBracketMesh.renderOrder = 999;
  scene.add(cornerBracketMesh);
  cornerBracketMesh.visible = false;

  function updateHoverBoundingBox(box) {
    if (!box) {
      hoverBoxGroup.visible = false;
      cornerBracketMesh.visible = false;
      return;
    }
    const size = new THREE.Vector3();
    box.getSize(size);
    const center = new THREE.Vector3();
    box.getCenter(center);

    const pad = Math.max(0.012, Math.min(0.035, Math.min(size.x, size.y, size.z) * 0.05));
    const lenX = size.x + pad * 2;
    const lenY = size.y + pad * 2;
    const lenZ = size.z + pad * 2;

    hoverBoxGroup.position.copy(center);
    hoverBoxGroup.scale.set(lenX, lenY, lenZ);
    hoverBoxGroup.visible = true;

    const hx = lenX / 2;
    const hy = lenY / 2;
    const hz = lenZ / 2;
    const armX = Math.min(0.20, lenX * 0.28);
    const armY = Math.min(0.20, lenY * 0.28);
    const armZ = Math.min(0.20, lenZ * 0.28);

    const corners = [
      [-1, -1, -1], [1, -1, -1], [-1, 1, -1], [1, 1, -1],
      [-1, -1, 1],  [1, -1, 1],  [-1, 1, 1],  [1, 1, 1]
    ];

    let ptr = 0;
    const pos = cornerBracketPositions;
    for (let i = 0; i < 8; i++) {
      const sx = corners[i][0];
      const sy = corners[i][1];
      const sz = corners[i][2];
      const cx = center.x + sx * hx;
      const cy = center.y + sy * hy;
      const cz = center.z + sz * hz;

      pos[ptr++] = cx; pos[ptr++] = cy; pos[ptr++] = cz;
      pos[ptr++] = cx - sx * armX; pos[ptr++] = cy; pos[ptr++] = cz;

      pos[ptr++] = cx; pos[ptr++] = cy; pos[ptr++] = cz;
      pos[ptr++] = cx; pos[ptr++] = cy - sy * armY; pos[ptr++] = cz;

      pos[ptr++] = cx; pos[ptr++] = cy; pos[ptr++] = cz;
      pos[ptr++] = cx; pos[ptr++] = cy; pos[ptr++] = cz - sz * armZ;
    }
    cornerBracketGeo.attributes.position.needsUpdate = true;
    cornerBracketMesh.visible = true;
  }

  function hideHoverBoundingBox() {
    hoverBoxGroup.visible = false;
    cornerBracketMesh.visible = false;
  }

  function applyHoverMeshGlow(obj) {
    if (!obj || obj === selectedObject) return;
    obj.traverse(function(child) {
      if (child.isMesh && child.material && !child.userData.isHitBox) {
        child.userData = child.userData || {};
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        if (child.userData.origHoverEmissives === undefined) {
          child.userData.origHoverEmissives = mats.map(function(m) { return m.emissive ? m.emissive.getHex() : null; });
          child.userData.origHoverEmissiveIntensities = mats.map(function(m) { return m.emissiveIntensity !== undefined ? m.emissiveIntensity : 0.0; });
        }
        mats.forEach(function(m) {
          if (m.emissive) {
            m.emissive.setHex(0x00f0ff);
            m.emissiveIntensity = 0.40;
          }
        });
      }
    });
  }

  function removeHoverMeshGlow(obj) {
    if (!obj) return;
    obj.traverse(function(child) {
      if (child.isMesh && child.material && child.userData && child.userData.origHoverEmissives) {
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        mats.forEach(function(m, i) {
          const hex = child.userData.origHoverEmissives[i];
          const inten = child.userData.origHoverEmissiveIntensities ? child.userData.origHoverEmissiveIntensities[i] : 0.0;
          if (hex !== null && hex !== undefined && m.emissive) {
            m.emissive.setHex(hex);
            m.emissiveIntensity = inten;
          }
        });
        delete child.userData.origHoverEmissives;
        delete child.userData.origHoverEmissiveIntensities;
      }
    });
  }

  function createThickRedSelectionCage(size, center) {
    const group = new THREE.Group();
    group.name = "thick_red_selection_cage";

    const minDim = Math.min(size.x, size.y, size.z);
    const r = Math.max(0.016, Math.min(0.035, minDim * 0.08));
    const pad = Math.max(0.03, Math.min(0.06, minDim * 0.12));

    const lenX = size.x + pad * 2;
    const lenY = size.y + pad * 2;
    const lenZ = size.z + pad * 2;
    const hx = lenX / 2;
    const hy = lenY / 2;
    const hz = lenZ / 2;

    // خامة حمراء مشعة للأضلاع السميكة ثلاثية الأبعاد
    const thickMat = new THREE.MeshStandardMaterial({
      color: 0xef4444,
      emissive: 0xdc2626,
      emissiveIntensity: 0.95,
      roughness: 0.25,
      metalness: 0.2,
      depthTest: true,
      depthWrite: false,
      transparent: true,
      opacity: 0.95
    });

    // 4 أضلاع أفقية موازية لـ X (أسطوانات ثلاثية الأبعاد سميكة)
    if (lenX > 0.01) {
      const geomX = new THREE.CylinderGeometry(r, r, lenX, 8);
      geomX.rotateZ(Math.PI / 2);
      [-hy, hy].forEach(function(y) {
        [-hz, hz].forEach(function(z) {
          const m = new THREE.Mesh(geomX, thickMat);
          m.position.set(0, y, z);
          m.renderOrder = 999;
          group.add(m);
        });
      });
    }

    // 4 أضلاع رأسية موازية لـ Y (أسطوانات ثلاثية الأبعاد سميكة)
    if (lenY > 0.01) {
      const geomY = new THREE.CylinderGeometry(r, r, lenY, 8);
      [-hx, hx].forEach(function(x) {
        [-hz, hz].forEach(function(z) {
          const m = new THREE.Mesh(geomY, thickMat);
          m.position.set(x, 0, z);
          m.renderOrder = 999;
          group.add(m);
        });
      });
    }

    // 4 أضلاع عمودية موازية لـ Z (أسطوانات ثلاثية الأبعاد سميكة)
    if (lenZ > 0.01) {
      const geomZ = new THREE.CylinderGeometry(r, r, lenZ, 8);
      geomZ.rotateX(Math.PI / 2);
      [-hx, hx].forEach(function(x) {
        [-hy, hy].forEach(function(y) {
          const m = new THREE.Mesh(geomZ, thickMat);
          m.position.set(x, y, 0);
          m.renderOrder = 999;
          group.add(m);
        });
      });
    }

    // 8 كرات حمراء مضيئة في الأركان للربط الانسيابي للأضلاع
    const sphereGeom = new THREE.SphereGeometry(r * 1.35, 8, 8);
    [-hx, hx].forEach(function(x) {
      [-hy, hy].forEach(function(y) {
        [-hz, hz].forEach(function(z) {
          const sm = new THREE.Mesh(sphereGeom, thickMat);
          sm.position.set(x, y, z);
          sm.renderOrder = 999;
          group.add(sm);
        });
      });
    });

    // خطوط داخلية حمراء فاقعة لمزيد من التحديد
    const lineGeo = new THREE.EdgesGeometry(new THREE.BoxGeometry(lenX, lenY, lenZ));
    const lineMat = new THREE.LineBasicMaterial({
      color: 0xff0000,
      depthTest: false,
      transparent: true,
      opacity: 0.95
    });
    const lineSegs = new THREE.LineSegments(lineGeo, lineMat);
    lineSegs.renderOrder = 998;
    group.add(lineSegs);

    // توهج حجمي أحمر شفاف يغلف كامل أبعاد العنصر
    const fillMat = new THREE.MeshBasicMaterial({
      color: 0xef4444,
      transparent: true,
      opacity: 0.15,
      depthTest: false,
      side: THREE.DoubleSide
    });
    const fillMesh = new THREE.Mesh(new THREE.BoxGeometry(lenX, lenY, lenZ), fillMat);
    fillMesh.renderOrder = 997;
    group.add(fillMesh);

    group.position.copy(center);
    return group;
  }

  function disposeThickRedSelectionCage(cage) {
    if (!cage) return;
    scene.remove(cage);
    cage.traverse(function(child) {
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) child.material.forEach(function(m) { m.dispose(); });
        else child.material.dispose();
      }
    });
  }

  // ── أداة القياس التفاعلية ثلاثية الأبعاد (Interactive 3D Measurement & Dimension Tool) ──
  let isMeasureMode = false;
  let measureStep = 0; // 0: Idle/Wait Point A, 1: Rubber-band to Point B, 2: Finalized
  let pointA = new THREE.Vector3();
  let pointB = new THREE.Vector3();
  let currentCandidatePoint = new THREE.Vector3();
  let isCandidateSnapped = false;
  let snapVertices = [];
  let firstMeasureObj = null;
  let activeFaceSnapA = new THREE.Vector3();
  let activeFaceSnapB = new THREE.Vector3();
  let isFaceToFaceActive = false;

  // Anchor Markers (A: Start Point, B: End Point)
  const markerGeoA = new THREE.SphereGeometry(0.065, 16, 16);
  const markerMatA = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
    depthTest: false,
    transparent: true,
    opacity: 0.95
  });
  const markerA = new THREE.Mesh(markerGeoA, markerMatA);
  markerA.renderOrder = 1000;
  scene.add(markerA);
  markerA.visible = false;

  const markerGeoB = new THREE.SphereGeometry(0.065, 16, 16);
  const markerMatB = new THREE.MeshBasicMaterial({
    color: 0x22c55e,
    depthTest: false,
    transparent: true,
    opacity: 0.95
  });
  const markerB = new THREE.Mesh(markerGeoB, markerMatB);
  markerB.renderOrder = 1000;
  scene.add(markerB);
  markerB.visible = false;

  // Dynamic Dimension Line Mesh
  const measureLineGeo = new THREE.BufferGeometry();
  const measureLinePositions = new Float32Array(6);
  measureLineGeo.setAttribute('position', new THREE.BufferAttribute(measureLinePositions, 3));
  const measureLineMat = new THREE.LineBasicMaterial({
    color: 0xfbbf24,
    linewidth: 3,
    depthTest: false,
    transparent: true,
    opacity: 0.95
  });
  const measureLineMesh = new THREE.Line(measureLineGeo, measureLineMat);
  measureLineMesh.renderOrder = 999;
  scene.add(measureLineMesh);
  measureLineMesh.visible = false;

  // Witness Ticks Mesh (Architectural CAD Ticks at Point A & Point B)
  const measureTicksGeo = new THREE.BufferGeometry();
  const measureTicksPositions = new Float32Array(24);
  measureTicksGeo.setAttribute('position', new THREE.BufferAttribute(measureTicksPositions, 3));
  const measureTicksMat = new THREE.LineBasicMaterial({
    color: 0x38bdf8,
    linewidth: 2.5,
    depthTest: false,
    transparent: true,
    opacity: 0.95
  });
  const measureTicksMesh = new THREE.LineSegments(measureTicksGeo, measureTicksMat);
  measureTicksMesh.renderOrder = 999;
  scene.add(measureTicksMesh);
  measureTicksMesh.visible = false;

  // Smart Vertex Snapping Magnetic Marker Group
  const snapMarkerGroup = new THREE.Group();
  snapMarkerGroup.name = "snap_marker_group";
  const snapMarkerDotGeo = new THREE.SphereGeometry(0.05, 16, 16);
  const snapMarkerDotMat = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
    depthTest: false,
    transparent: true,
    opacity: 0.95
  });
  const snapMarkerDot = new THREE.Mesh(snapMarkerDotGeo, snapMarkerDotMat);
  snapMarkerGroup.add(snapMarkerDot);

  const snapMarkerRingGeo = new THREE.RingGeometry(0.075, 0.105, 32);
  const snapMarkerRingMat = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
    side: THREE.DoubleSide,
    depthTest: false,
    transparent: true,
    opacity: 0.85
  });
  const snapMarkerRing = new THREE.Mesh(snapMarkerRingGeo, snapMarkerRingMat);
  snapMarkerGroup.add(snapMarkerRing);
  snapMarkerGroup.renderOrder = 1001;
  scene.add(snapMarkerGroup);
  snapMarkerGroup.visible = false;

  // AutoCAD Perpendicular Snapping Marker Group (رمز الزاوية القائمة المعمارية)
  const perpMarkerGroup = new THREE.Group();
  perpMarkerGroup.name = "perp_marker_group";

  const perpLinePositions = new Float32Array(24);
  const perpLineGeo = new THREE.BufferGeometry();
  perpLineGeo.setAttribute('position', new THREE.BufferAttribute(perpLinePositions, 3));
  const perpLineMat = new THREE.LineBasicMaterial({
    color: 0x00f0ff,
    linewidth: 3,
    depthTest: false,
    transparent: true,
    opacity: 0.95
  });
  const perpLineMesh = new THREE.LineSegments(perpLineGeo, perpLineMat);
  perpLineMesh.renderOrder = 1005;
  perpMarkerGroup.add(perpLineMesh);

  const perpDotGeo = new THREE.SphereGeometry(0.045, 16, 16);
  const perpDotMat = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
    depthTest: false,
    transparent: true,
    opacity: 0.95
  });
  const perpDotMesh = new THREE.Mesh(perpDotGeo, perpDotMat);
  perpDotMesh.renderOrder = 1006;
  perpMarkerGroup.add(perpDotMesh);

  scene.add(perpMarkerGroup);
  perpMarkerGroup.visible = false;

  function updatePerpMarker(perpPoint, dimVector, faceNormal) {
    const vDim = dimVector.clone().normalize();
    let vNorm = faceNormal.clone().normalize();

    const camDir = new THREE.Vector3().subVectors(camera.position, perpPoint).normalize();
    let vWall = new THREE.Vector3().crossVectors(vNorm, camDir).normalize();
    if (vWall.lengthSq() < 0.05) {
      let fallbackUp = new THREE.Vector3(0, 1, 0);
      if (Math.abs(vNorm.y) > 0.85) fallbackUp = new THREE.Vector3(1, 0, 0);
      vWall = new THREE.Vector3().crossVectors(vNorm, fallbackUp).normalize();
    }

    const L = 0.22;
    const s = 0.08;
    const p = perpLinePositions;
    let ptr = 0;

    // Segment 1: Arm along wall face (Corner to L * vWall)
    p[ptr++] = perpPoint.x;
    p[ptr++] = perpPoint.y;
    p[ptr++] = perpPoint.z;
    p[ptr++] = perpPoint.x + vWall.x * L;
    p[ptr++] = perpPoint.y + vWall.y * L;
    p[ptr++] = perpPoint.z + vWall.z * L;

    // Segment 2: Arm along dimension line towards Point A (Corner to L * vDim)
    p[ptr++] = perpPoint.x;
    p[ptr++] = perpPoint.y;
    p[ptr++] = perpPoint.z;
    p[ptr++] = perpPoint.x + vDim.x * L;
    p[ptr++] = perpPoint.y + vDim.y * L;
    p[ptr++] = perpPoint.z + vDim.z * L;

    // Segment 3: Inner right-angle box edge 1 (from s * vWall to s * vWall + s * vDim)
    p[ptr++] = perpPoint.x + vWall.x * s;
    p[ptr++] = perpPoint.y + vWall.y * s;
    p[ptr++] = perpPoint.z + vWall.z * s;
    p[ptr++] = perpPoint.x + vWall.x * s + vDim.x * s;
    p[ptr++] = perpPoint.y + vWall.y * s + vDim.y * s;
    p[ptr++] = perpPoint.z + vWall.z * s + vDim.z * s;

    // Segment 4: Inner right-angle box edge 2 (from s * vWall + s * vDim to s * vDim)
    p[ptr++] = perpPoint.x + vWall.x * s + vDim.x * s;
    p[ptr++] = perpPoint.y + vWall.y * s + vDim.y * s;
    p[ptr++] = perpPoint.z + vWall.z * s + vDim.z * s;
    p[ptr++] = perpPoint.x + vDim.x * s;
    p[ptr++] = perpPoint.y + vDim.y * s;
    p[ptr++] = perpPoint.z + vDim.z * s;

    perpLineGeo.attributes.position.needsUpdate = true;
    perpDotMesh.position.copy(perpPoint);
    perpMarkerGroup.visible = true;
  }

  // Dynamic Billboard Text Sprite (Always Faces Camera)
  const measureCanvas = document.createElement('canvas');
  measureCanvas.width = 512;
  measureCanvas.height = 128;
  const measureCanvasCtx = measureCanvas.getContext('2d');
  const measureTexture = new THREE.CanvasTexture(measureCanvas);
  measureTexture.minFilter = THREE.LinearFilter;
  const measureSpriteMat = new THREE.SpriteMaterial({
    map: measureTexture,
    depthTest: false,
    depthWrite: false,
    transparent: true
  });
  const measureLabelSprite = new THREE.Sprite(measureSpriteMat);
  measureLabelSprite.renderOrder = 1002;
  scene.add(measureLabelSprite);
  measureLabelSprite.visible = false;

  function collectSnapVertices() {
    snapVertices = [];
    const vertexSet = new Set();
    function addPt(x, y, z) {
      const rx = Math.round(x * 1000) / 1000;
      const ry = Math.round(y * 1000) / 1000;
      const rz = Math.round(z * 1000) / 1000;
      const key = `${rx}_${ry}_${rz}`;
      if (!vertexSet.has(key)) {
        vertexSet.add(key);
        snapVertices.push(new THREE.Vector3(rx, ry, rz));
      }
    }

    selectableObjects.forEach(function(obj) {
      if (!obj || obj.visible === false) return;
      const box = new THREE.Box3().setFromObject(obj);
      if (box.isEmpty()) return;
      const min = box.min;
      const max = box.max;
      // 8 bounding box corners
      addPt(min.x, min.y, min.z);
      addPt(max.x, min.y, min.z);
      addPt(min.x, max.y, min.z);
      addPt(max.x, max.y, min.z);
      addPt(min.x, min.y, max.z);
      addPt(max.x, min.y, max.z);
      addPt(min.x, max.y, max.z);
      addPt(max.x, max.y, max.z);

      // نقاط منتصف أوجه الحوائط والأعمدة الحقيقية (Face Centers & Face Midpoints)
      // الوجه 1 والوجه 2 في اتجاه Z (أوجه الحوائط الأفقية والأعمدة)
      addPt((min.x + max.x) / 2, min.y, min.z);
      addPt((min.x + max.x) / 2, max.y, min.z);
      addPt((min.x + max.x) / 2, (min.y + max.y) / 2, min.z);

      addPt((min.x + max.x) / 2, min.y, max.z);
      addPt((min.x + max.x) / 2, max.y, max.z);
      addPt((min.x + max.x) / 2, (min.y + max.y) / 2, max.z);

      // الوجه 1 والوجه 2 في اتجاه X (أوجه الحوائط الرأسية والأعمدة)
      addPt(min.x, min.y, (min.z + max.z) / 2);
      addPt(min.x, max.y, (min.z + max.z) / 2);
      addPt(min.x, (min.y + max.y) / 2, (min.z + max.z) / 2);

      addPt(max.x, min.y, (min.z + max.z) / 2);
      addPt(max.x, max.y, (min.z + max.z) / 2);
      addPt(max.x, (min.y + max.y) / 2, (min.z + max.z) / 2);
    });
  }

  function drawMeasureLabel(dist, ptA, ptB) {
    const m = dist.toFixed(2);
    const text = `📏 ${m} م`;

    measureCanvasCtx.clearRect(0, 0, 512, 128);

    // Text centered with high-contrast shadow without any outer frame or border
    measureCanvasCtx.save();
    measureCanvasCtx.shadowColor = 'rgba(0, 0, 0, 0.95)';
    measureCanvasCtx.shadowBlur = 12;
    measureCanvasCtx.shadowOffsetX = 2;
    measureCanvasCtx.shadowOffsetY = 3;
    measureCanvasCtx.font = 'bold 46px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    measureCanvasCtx.fillStyle = '#ffffff';
    measureCanvasCtx.textAlign = 'center';
    measureCanvasCtx.textBaseline = 'middle';
    measureCanvasCtx.direction = 'rtl';
    measureCanvasCtx.fillText(text, 256, 64);
    measureCanvasCtx.restore();

    measureTexture.needsUpdate = true;

    // Position at midpoint elevated slightly
    const mid = new THREE.Vector3().addVectors(ptA, ptB).multiplyScalar(0.5);
    mid.y += 0.25;
    measureLabelSprite.position.copy(mid);
    measureLabelSprite.visible = true;
  }

  function updateMeasureGeometry(ptA, ptB, isFinal) {
    const linePos = measureLinePositions;
    linePos[0] = ptA.x; linePos[1] = ptA.y; linePos[2] = ptA.z;
    linePos[3] = ptB.x; linePos[4] = ptB.y; linePos[5] = ptB.z;
    measureLineGeo.attributes.position.needsUpdate = true;
    measureLineMesh.visible = true;

    if (isFinal) {
      measureLineMesh.material.color.setHex(0x38bdf8);
      const dir = new THREE.Vector3().subVectors(ptB, ptA);
      const dist = dir.length();
      if (dist > 0.02) {
        dir.normalize();

        // Dynamically compute perpendicular direction facing camera so ticks & slashes are always clearly visible
        let camVec = new THREE.Vector3().subVectors(camera.position, ptA).normalize();
        let perp = new THREE.Vector3().crossVectors(dir, camVec).normalize();
        if (perp.lengthSq() < 0.1) {
          let up = new THREE.Vector3(0, 1, 0);
          if (Math.abs(dir.dot(up)) > 0.92) up = new THREE.Vector3(1, 0, 0);
          perp = new THREE.Vector3().crossVectors(dir, up).normalize();
        }

        const tickLen = 0.22; // Witness tick length 22cm on each side (total 44cm)
        const slashLen = 0.16; // 45° architectural slash length 16cm on each side
        const slash = new THREE.Vector3().addVectors(dir, perp).normalize().multiplyScalar(slashLen);

        const tPos = measureTicksPositions;
        let ptr = 0;

        // Witness Line at Point A (Perpendicular CAD witness line)
        tPos[ptr++] = ptA.x - perp.x * tickLen; tPos[ptr++] = ptA.y - perp.y * tickLen; tPos[ptr++] = ptA.z - perp.z * tickLen;
        tPos[ptr++] = ptA.x + perp.x * tickLen; tPos[ptr++] = ptA.y + perp.y * tickLen; tPos[ptr++] = ptA.z + perp.z * tickLen;

        // Architectural 45° Slash Tick at Point A
        tPos[ptr++] = ptA.x - slash.x; tPos[ptr++] = ptA.y - slash.y; tPos[ptr++] = ptA.z - slash.z;
        tPos[ptr++] = ptA.x + slash.x; tPos[ptr++] = ptA.y + slash.y; tPos[ptr++] = ptA.z + slash.z;

        // Witness Line at Point B (Perpendicular CAD witness line)
        tPos[ptr++] = ptB.x - perp.x * tickLen; tPos[ptr++] = ptB.y - perp.y * tickLen; tPos[ptr++] = ptB.z - perp.z * tickLen;
        tPos[ptr++] = ptB.x + perp.x * tickLen; tPos[ptr++] = ptB.y + perp.y * tickLen; tPos[ptr++] = ptB.z + perp.z * tickLen;

        // Architectural 45° Slash Tick at Point B
        tPos[ptr++] = ptB.x - slash.x; tPos[ptr++] = ptB.y - slash.y; tPos[ptr++] = ptB.z - slash.z;
        tPos[ptr++] = ptB.x + slash.x; tPos[ptr++] = ptB.y + slash.y; tPos[ptr++] = ptB.z + slash.z;

        measureTicksGeo.attributes.position.needsUpdate = true;
        measureTicksMesh.visible = true;
      }
    } else {
      measureLineMesh.material.color.setHex(0xfbbf24);
      measureTicksMesh.visible = false;
    }
  }

  function updateMeasureHover(clientX, clientY) {
    const rect = renderer.domElement.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    const halfW = rect.width / 2;
    const halfH = rect.height / 2;

    // Prepare mouse raycaster
    mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    const solidHits = raycaster.intersectObjects(selectableObjects, false);

    // 1. In Step 1: Check for Wall-to-Wall Face-to-Face clear measurement (قياس صافي المسافة بين أوجه الحوائط)
    isFaceToFaceActive = false;
    let faceSnapNorm = null;

    if (measureStep === 1 && solidHits.length > 0 && firstMeasureObj) {
      const hitB = solidHits[0];
      const secondObj = hitB.object;

      if (secondObj && firstMeasureObj !== secondObj) {
        let tObjA = firstMeasureObj;
        if (tObjA.userData && tObjA.userData.parentWallGroup) tObjA = tObjA.userData.parentWallGroup;
        let tObjB = secondObj;
        if (tObjB.userData && tObjB.userData.parentWallGroup) tObjB = tObjB.userData.parentWallGroup;

        if (tObjA !== tObjB) {
          const boxA = new THREE.Box3().setFromObject(tObjA);
          const boxB = new THREE.Box3().setFromObject(tObjB);
          const centerA = new THREE.Vector3();
          const centerB = new THREE.Vector3();
          boxA.getCenter(centerA);
          boxB.getCenter(centerB);
          const diff = new THREE.Vector3().subVectors(centerB, centerA);

          const absX = Math.abs(diff.x);
          const absZ = Math.abs(diff.z);

          if (absZ >= absX && absZ > 0.15) {
            // Walls separated primarily along Z axis (e.g. horizontal walls X1, X2... or north-south faces)
            let snapA_z, snapB_z;
            if (diff.z > 0) {
              snapA_z = boxA.max.z; // Facing face of Wall 1
              snapB_z = boxB.min.z; // Facing face of Wall 2
              faceSnapNorm = new THREE.Vector3(0, 0, -1);
            } else {
              snapA_z = boxA.min.z; // Facing face of Wall 1
              snapB_z = boxB.max.z; // Facing face of Wall 2
              faceSnapNorm = new THREE.Vector3(0, 0, 1);
            }
            const hitPt = hitB.point;
            activeFaceSnapA.set(hitPt.x, hitPt.y, snapA_z);
            activeFaceSnapB.set(hitPt.x, hitPt.y, snapB_z);
            isFaceToFaceActive = true;
          } else if (absX > absZ && absX > 0.15) {
            // Walls separated primarily along X axis (e.g. vertical walls Y1, Y2... or east-west faces)
            let snapA_x, snapB_x;
            if (diff.x > 0) {
              snapA_x = boxA.max.x; // Facing face of Wall 1
              snapB_x = boxB.min.x; // Facing face of Wall 2
              faceSnapNorm = new THREE.Vector3(-1, 0, 0);
            } else {
              snapA_x = boxA.min.x; // Facing face of Wall 1
              snapB_x = boxB.max.x; // Facing face of Wall 2
              faceSnapNorm = new THREE.Vector3(1, 0, 0);
            }
            const hitPt = hitB.point;
            activeFaceSnapA.set(snapA_x, hitPt.y, hitPt.z);
            activeFaceSnapB.set(snapB_x, hitPt.y, hitPt.z);
            isFaceToFaceActive = true;
          }
        }
      }
    }

    if (isFaceToFaceActive) {
      currentCandidatePoint.copy(activeFaceSnapB);
      markerA.position.copy(activeFaceSnapA);
      isCandidateSnapped = true;

      // Show AutoCAD Right-Angle Perpendicular Symbol on the face of Wall 2
      snapMarkerGroup.visible = false;
      const dirToA = new THREE.Vector3().subVectors(activeFaceSnapA, activeFaceSnapB).normalize();
      updatePerpMarker(activeFaceSnapB, dirToA, faceSnapNorm);

      updateMeasureGeometry(activeFaceSnapA, activeFaceSnapB, false);
      const d = activeFaceSnapA.distanceTo(activeFaceSnapB);
      drawMeasureLabel(d, activeFaceSnapA, activeFaceSnapB);

      const bannerText = document.getElementById('measure-banner-text');
      if (bannerText) {
        bannerText.innerHTML = `📐 <b>قياس صافي من وجه الحائط إلى وجه الحائط: ${d.toFixed(2)} م</b> • انقر بالزر الأيسر لتثبيت البعد`;
      }
      return;
    }

    // 2. In Step 1: Detect Perpendicular Snap on General Opposing Surfaces (وضع التعامد العام)
    let isPerpActive = false;
    let perpSnapPt = null;
    let perpFaceNorm = null;

    if (measureStep === 1) {
      if (solidHits.length > 0 && solidHits[0].face) {
        const hit = solidHits[0];
        let norm = hit.face.normal.clone().transformDirection(hit.object.matrixWorld).normalize();
        if (Math.abs(norm.x) > 0.85) norm.set(Math.sign(norm.x), 0, 0);
        else if (Math.abs(norm.y) > 0.85) norm.set(0, Math.sign(norm.y), 0);
        else if (Math.abs(norm.z) > 0.85) norm.set(0, 0, Math.sign(norm.z));

        const dPerp = new THREE.Vector3().subVectors(pointA, hit.point).dot(norm);
        if (dPerp > 0.10) {
          const pCandidate = pointA.clone().sub(norm.clone().multiplyScalar(dPerp));
          if (Math.abs(norm.y) < 0.15) {
            pCandidate.y = pointA.y;
          }

          let targetObj = hit.object;
          if (targetObj.userData && targetObj.userData.parentWallGroup) {
            targetObj = targetObj.userData.parentWallGroup;
          }
          const objBox = new THREE.Box3().setFromObject(targetObj);
          objBox.expandByScalar(0.35);

          if (objBox.containsPoint(pCandidate)) {
            const vProjPerp = pCandidate.clone().project(camera);
            if (vProjPerp.z >= -1 && vProjPerp.z <= 1) {
              const sx = (vProjPerp.x * halfW) + halfW + rect.left;
              const sy = -(vProjPerp.y * halfH) + halfH + rect.top;
              const screenDist = Math.hypot(sx - clientX, sy - clientY);
              const dist3D = hit.point.distanceTo(pCandidate);
              if (screenDist < 55 || dist3D < 1.2) {
                isPerpActive = true;
                perpSnapPt = pCandidate;
                perpFaceNorm = norm;
              }
            }
          }
        }
      }
    }

    // 3. Smart Vertex Snapping (screen space projection strictly on faces)
    let bestVertex = null;
    let minScreenDist = 24; // 24px magnetic snap radius
    const vProj = new THREE.Vector3();

    for (let i = 0; i < snapVertices.length; i++) {
      const v = snapVertices[i];
      vProj.copy(v).project(camera);
      if (vProj.z < -1 || vProj.z > 1) continue;
      const sx = (vProj.x * halfW) + halfW + rect.left;
      const sy = -(vProj.y * halfH) + halfH + rect.top;
      const d = Math.hypot(sx - clientX, sy - clientY);
      if (d < minScreenDist) {
        minScreenDist = d;
        bestVertex = v;
      }
    }

    // Verify unoccluded line of sight for vertex
    if (bestVertex) {
      const dir = new THREE.Vector3().subVectors(bestVertex, camera.position);
      const distToV = dir.length();
      if (distToV > 0.1) {
        dir.normalize();
        const snapRay = new THREE.Raycaster(camera.position, dir, 0.1, distToV - 0.08);
        const occluding = snapRay.intersectObjects(selectableObjects, false);
        if (occluding.length > 0) {
          bestVertex = null;
        }
      }
    }

    // Priority: If user hovers directly on an exact vertex (minScreenDist < 12px), snap vertex
    // Otherwise, if perpendicular alignment is detected, perpendicular snap takes priority!
    if (isPerpActive && (!bestVertex || minScreenDist >= 12)) {
      currentCandidatePoint.copy(perpSnapPt);
      isCandidateSnapped = true;

      // Transform circular marker into AutoCAD right-angle symbol
      snapMarkerGroup.visible = false;
      const dirToA = new THREE.Vector3().subVectors(pointA, currentCandidatePoint).normalize();
      updatePerpMarker(currentCandidatePoint, dirToA, perpFaceNorm);

      const bannerText = document.getElementById('measure-banner-text');
      if (bannerText) {
        bannerText.innerHTML = '📐 <b>وضع تعامد قائم 90° (AutoCAD Perpendicular)</b> • انقر بالزر الأيسر لتثبيت نقطة النهاية (Point B) وتوليد خط البعد';
      }
    } else {
      perpMarkerGroup.visible = false;

      if (bestVertex) {
        currentCandidatePoint.copy(bestVertex);
        isCandidateSnapped = true;
      } else {
        if (solidHits.length > 0) {
          currentCandidatePoint.copy(solidHits[0].point);
          isCandidateSnapped = false;
        } else {
          const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
          const groundPt = new THREE.Vector3();
          if (raycaster.ray.intersectPlane(groundPlane, groundPt)) {
            currentCandidatePoint.copy(groundPt);
            isCandidateSnapped = false;
          } else {
            snapMarkerGroup.visible = false;
            return;
          }
        }
      }

      snapMarkerGroup.position.copy(currentCandidatePoint);
      snapMarkerGroup.visible = true;

      if (isCandidateSnapped) {
        snapMarkerDot.material.color.setHex(0x00f0ff);
        snapMarkerRing.material.color.setHex(0x00f0ff);
        snapMarkerGroup.scale.set(1.35, 1.35, 1.35);
      } else {
        snapMarkerDot.material.color.setHex(0x38bdf8);
        snapMarkerRing.material.color.setHex(0x38bdf8);
        snapMarkerGroup.scale.set(0.85, 0.85, 0.85);
      }
      snapMarkerRing.quaternion.copy(camera.quaternion);

      if (measureStep === 1) {
        const bannerText = document.getElementById('measure-banner-text');
        if (bannerText) {
          bannerText.innerHTML = '📏 <b>تم تثبيت نقطة البداية (Point A)</b> • حرّك الفأرة لمعاينة البعد وانقر بالزر الأيسر لتثبيت نقطة النهاية (Point B)';
        }
      }
    }

    // In step 1: Live dynamic rubber-band preview
    if (measureStep === 1) {
      updateMeasureGeometry(pointA, currentCandidatePoint, false);
      const d = pointA.distanceTo(currentCandidatePoint);
      drawMeasureLabel(d, pointA, currentCandidatePoint);
    }
  }

  function handleMeasureClick(clientX, clientY) {
    const rect = renderer.domElement.getBoundingClientRect();
    if (measureStep === 0) {
      pointA.copy(currentCandidatePoint);

      // Identify the clicked solid element (wall, column, etc.)
      mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObjects(selectableObjects, false);
      if (hits.length > 0) {
        firstMeasureObj = hits[0].object;
      } else {
        firstMeasureObj = null;
      }

      markerA.position.copy(pointA);
      markerA.visible = true;
      measureStep = 1;

      updateMeasureGeometry(pointA, pointA, false);
      measureLineMesh.visible = true;
      drawMeasureLabel(0, pointA, pointA);

      const bannerText = document.getElementById('measure-banner-text');
      if (bannerText) {
        bannerText.innerHTML = '📏 <b>تم تحديد الحائط الأول (Point A)</b> • حرّك الفأرة نحو الحائط المقابل للقياس الصافي من وجه الحائط (Point B)';
      }
    } else if (measureStep === 1) {
      // If we are in face-to-face snapping mode, lock the exact facing wall faces
      if (isFaceToFaceActive) {
        pointA.copy(activeFaceSnapA);
        pointB.copy(activeFaceSnapB);
      } else {
        pointB.copy(currentCandidatePoint);
      }

      markerA.position.copy(pointA);
      markerB.position.copy(pointB);
      markerB.visible = true;
      measureStep = 2;

      // Finalize CAD witness lines and line geometry
      updateMeasureGeometry(pointA, pointB, true);
      const d = pointA.distanceTo(pointB);
      drawMeasureLabel(d, pointA, pointB);

      // Hide live hover snap markers
      snapMarkerGroup.visible = false;
      perpMarkerGroup.visible = false;

      // Re-enable camera rotation via Left Click for free 3D inspection!
      controls.mouseButtons = {
        LEFT: THREE.MOUSE.ROTATE,
        MIDDLE: THREE.MOUSE.DOLLY,
        RIGHT: THREE.MOUSE.PAN
      };
      renderer.domElement.style.cursor = 'default';
      container.style.cursor = 'default';
      document.body.style.cursor = 'default';

      const bannerText = document.getElementById('measure-banner-text');
      if (bannerText) {
        bannerText.innerHTML = `✅ تم إتمام القياس الصافي بين أوجه الحوائط: <b>${d.toFixed(2)} م</b> • تم تفعيل التدوير بالزر الأيسر لفحص البعد بحرية`;
      }
    }
  }

  function clearMeasurements() {
    measureStep = 0;
    pointA.set(0, 0, 0);
    pointB.set(0, 0, 0);
    firstMeasureObj = null;
    isFaceToFaceActive = false;
    activeFaceSnapA.set(0, 0, 0);
    activeFaceSnapB.set(0, 0, 0);
    if (markerA) markerA.visible = false;
    if (markerB) markerB.visible = false;
    if (measureLineMesh) measureLineMesh.visible = false;
    if (measureTicksMesh) measureTicksMesh.visible = false;
    if (measureLabelSprite) measureLabelSprite.visible = false;
    if (snapMarkerGroup) snapMarkerGroup.visible = false;
    if (perpMarkerGroup) perpMarkerGroup.visible = false;
  }

  function enterMeasureMode() {
    isMeasureMode = true;
    measureStep = 0;
    clearMeasurements();
    clearHover();
    clearSelection();

    collectSnapVertices();

    // Lock Left Click exclusively for picking measurement points
    // Delegate rotation to Right Click and zoom to Wheel
    controls.mouseButtons = {
      LEFT: null,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.ROTATE
    };

    renderer.domElement.style.cursor = 'crosshair';
    container.style.cursor = 'crosshair';
    document.body.style.cursor = 'crosshair';

    const btnM = document.getElementById('btn-measure');
    if (btnM) {
      btnM.style.background = '#0284c7';
      btnM.style.borderColor = '#38bdf8';
      btnM.style.color = '#ffffff';
      btnM.style.boxShadow = '0 0 12px rgba(56, 189, 248, 0.6)';
      btnM.innerHTML = '📏 وضع القياس (نشط)';
    }

    const btnClear = document.getElementById('btn-clear-measure');
    if (btnClear) btnClear.style.display = 'inline-flex';

    const banner = document.getElementById('measure-banner');
    const bannerText = document.getElementById('measure-banner-text');
    if (banner) banner.style.display = 'flex';
    if (bannerText) {
      bannerText.innerHTML = '📏 <b>وضع القياس ثلاثي الأبعاد</b>: انقر بالزر الأيسر لتحديد نقطة البداية (Point A) • التدوير بالزر الأيمن أو العجلة • اضغط Esc للإلغاء';
    }
  }

  function exitMeasureMode() {
    isMeasureMode = false;
    clearMeasurements();

    // Restore standard OrbitControls behavior
    controls.mouseButtons = {
      LEFT: THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.PAN
    };

    renderer.domElement.style.cursor = 'default';
    container.style.cursor = 'default';
    document.body.style.cursor = 'default';

    const btnM = document.getElementById('btn-measure');
    if (btnM) {
      btnM.style.background = '#1e293b';
      btnM.style.borderColor = '#475569';
      btnM.style.color = '#f1f5f9';
      btnM.style.boxShadow = 'none';
      btnM.innerHTML = '📏 أداة القياس';
    }

    const btnClear = document.getElementById('btn-clear-measure');
    if (btnClear) btnClear.style.display = 'none';

    const banner = document.getElementById('measure-banner');
    if (banner) banner.style.display = 'none';
  }

  function highlightObjectMeshes(obj) {
    if (!obj) return;
    obj.traverse(function(child) {
      if (child.isMesh && child.material) {
        child.userData = child.userData || {};
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        if (child.userData.origColors === undefined) {
          child.userData.origColors = mats.map(function(m) { return m.color ? m.color.getHex() : null; });
        }
        if (child.userData.origEmissives === undefined) {
          child.userData.origEmissives = mats.map(function(m) { return m.emissive ? m.emissive.getHex() : null; });
          child.userData.origEmissiveIntensities = mats.map(function(m) { return m.emissiveIntensity !== undefined ? m.emissiveIntensity : 0.0; });
        }
        mats.forEach(function(m) {
          if (m.emissive) {
            m.emissive.setHex(0xdc2626);
            m.emissiveIntensity = 0.55;
          } else if (m.color) {
            m.color.setHex(0xf87171);
          }
        });
      }
    });
  }

  function unhighlightObjectMeshes(obj) {
    if (!obj) return;
    obj.traverse(function(child) {
      if (child.isMesh && child.material && child.userData) {
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        if (child.userData.origColors) {
          mats.forEach(function(m, i) {
            const hex = child.userData.origColors[i];
            if (hex !== null && hex !== undefined && m.color) m.color.setHex(hex);
          });
        }
        if (child.userData.origEmissives) {
          mats.forEach(function(m, i) {
            const hex = child.userData.origEmissives[i];
            const inten = child.userData.origEmissiveIntensities ? child.userData.origEmissiveIntensities[i] : 0.0;
            if (hex !== null && hex !== undefined && m.emissive) {
              m.emissive.setHex(hex);
              m.emissiveIntensity = inten;
            }
          });
        }
      }
    });
  }

  function clearSelection() {
    hideWallFloatingBar();
    if (highlightWire) {
      disposeThickRedSelectionCage(highlightWire);
      highlightWire = null;
    }
    if (selectedObject) {
      unhighlightObjectMeshes(selectedObject);
    }
    selectedObject = null;
    hideDimensionLines();
    document.getElementById('inspector-card').style.display = 'none';
  }

  // ── تحديد واختيار العنصر مع إبرازه بلون أحمر وبخطوط سميكة ──
  function setSelection(obj, elemType, elemData) {
    clearSelection();
    if (obj) removeHoverMeshGlow(obj);
    hideHoverBoundingBox();
    selectedObject = obj;

    const box = new THREE.Box3().setFromObject(obj);
    const size = new THREE.Vector3();
    box.getSize(size);
    const center = new THREE.Vector3();
    box.getCenter(center);

    // 1. إضافة القفص السميك ثلاثي الأبعاد باللون الأحمر
    highlightWire = createThickRedSelectionCage(size, center);
    scene.add(highlightWire);

    // 2. تمييز خامات كتل العنصر نفسه بتوهج أحمر مميز
    highlightObjectMeshes(obj);

    if (elemType === 'wall') {
      showWallFloatingBar(elemData);
    } else if (elemType === 'column') {
      showColumnFloatingBar(elemData);
    } else if (elemType === 'window') {
      showWindowFloatingBar(elemData);
    } else if (elemType === 'door') {
      showDoorFloatingBar(elemData);
    }

    showInspector(elemType, elemData);

    if (elemType === 'window' || elemType === 'door') {
      showDimensionLines(elemData);
    } else {
      hideDimensionLines();
    }
  }

  // ── Warning Audio Beep (صافرة تنبيه صوتية عند طلب الحذف) ──
  function playWarningBeep() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(620, ctx.currentTime);
      osc.frequency.setValueAtTime(880, ctx.currentTime + 0.08);
      osc.frequency.setValueAtTime(440, ctx.currentTime + 0.16);
      gain.gain.setValueAtTime(0.30, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.28);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.30);
    } catch(err) {
      console.warn("playWarningBeep error:", err);
    }
  }

  // ── Inspector Panel Logic ──
  const inspCard = document.getElementById('inspector-card');
  const inspBody = document.getElementById('insp-body');
  const inspIcon = document.getElementById('insp-icon');
  const inspHeader = document.getElementById('insp-header-text');
  const btnInspClose = document.getElementById('btn-insp-close');

  if (btnInspClose) {
    btnInspClose.addEventListener('click', function(e) {
      e.stopPropagation();
      clearSelection();
    });
  }

  function showInspector(type, d) {
    inspCard.style.display = 'flex';
    let html = '';

    if (type === 'wall') {
      inspIcon.textContent = '🧱';
      inspHeader.textContent = 'فاحص الحائط بالكامل (وحدة واحدة)';
      const parapetBadge = d.is_parapet ? '<span style="color:#ffffff;font-size:10px;margin-right:5px;">[دروة سطح]</span>' : '';
      const plasterBadge = d.has_plaster ? '<span style="color:#ec4899;font-size:10px;margin-right:5px;">[وجه محارة]</span>' : '';

      html = `
        <div class="insp-tag wall-tag">■ الحائط بالكامل (${d.thickness_cm} سم) ${parapetBadge} ${plasterBadge}</div>
        <div class="insp-name">${d.wall_name}</div>
        <div class="insp-sub">${d.wall_label}</div>

        <div class="insp-section-title">📐 الأبعاد والمساحات الإجمالية</div>
        <div class="insp-grid">
          <div class="insp-item"><span class="insp-label">الطول الكلي</span><span class="insp-val"><b>${d.length.toFixed(2)} م</b></span></div>
          <div class="insp-item"><span class="insp-label">الارتفاع</span><span class="insp-val">${d.height.toFixed(2)} م</span></div>
          <div class="insp-item"><span class="insp-label">المساحة الإجمالية</span><span class="insp-val">${d.gross_area.toFixed(2)} م²</span></div>
          <div class="insp-item"><span class="insp-label">مساحة الفتحات</span><span class="insp-val">${d.openings_area.toFixed(2)} م²</span></div>
          <div class="insp-item" style="grid-column: span 2; background:rgba(2,132,199,0.20); border-color:#0284c7;">
            <span class="insp-label">صافي مسطح المباني (للحائط كاملاً)</span>
            <span class="insp-val"><b style="font-size:13px;color:#ffffff;">${d.net_area.toFixed(2)} م²</b></span>
          </div>
        </div>

        <div class="insp-section-title">🧱 حصر الخامات والمونة للحائط بالكامل</div>
        <div class="insp-grid">
          <div class="insp-item"><span class="insp-label">عدد الطوب المقدر</span><span class="insp-val" style="color:#f59e0b;"><b>${d.brick_qty.toLocaleString()} طوبة</b></span></div>
          <div class="insp-item"><span class="insp-label">${d.thickness_cm === 25 ? 'حجم الطوب' : 'مسطح الطوب'}</span><span class="insp-val">${d.thickness_cm === 25 ? d.brick_vol_m3.toFixed(2) + ' م³' : d.net_area.toFixed(2) + ' م²'}</span></div>
          <div class="insp-item"><span class="insp-label">رمل المونة</span><span class="insp-val">${d.sand_m3.toFixed(3)} م³</span></div>
          <div class="insp-item"><span class="insp-label">أسمنت المونة</span><span class="insp-val">${d.cement_kg.toFixed(0)} كجم</span></div>
        </div>

        <div class="insp-section-title">🏛️ حدود الأعمدة المجاورة على الحائط</div>
        <div style="font-size:11px;color:#94a3b8;background:#1e293b;padding:6px 9px;border-radius:5px;border:1px solid #334155;">
          من العمود <b>${d.col1_name}</b> (خلوص: ${d.col1_limit.toFixed(2)}م) <br>
          إلى العمود <b>${d.col2_name}</b> (خلوص: ${d.col2_limit.toFixed(2)}م)
        </div>

        <div class="insp-actions" style="margin-top:14px;">
          <button class="insp-btn" id="btn-insp-del-wall" style="background:linear-gradient(135deg,#ef4444,#dc2626);border:1px solid #f87171;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;gap:6px;width:100%;padding:8px 12px;border-radius:6px;cursor:pointer;">
            <span>🗑️</span> <span>حذف الحائط ${d.wall_name}</span>
          </button>
          <div id="insp-del-confirm-box" style="display:none;margin-top:8px;padding:10px;background:rgba(239,68,68,0.18);border:1.5px solid #ef4444;border-radius:8px;text-align:center;">
            <div style="font-size:12px;color:#fca5a5;font-weight:700;margin-bottom:8px;">⚠️ تأكيد حذف الحائط ${d.wall_name} بالكامل؟ سيتم حفظه في قسم الاستعادة.</div>
            <div style="display:flex;gap:8px;justify-content:center;">
              <button class="insp-btn" id="btn-insp-confirm-del" style="background:#dc2626;border:1px solid #f87171;color:#fff;padding:5px 14px;font-size:11.5px;font-weight:700;border-radius:5px;cursor:pointer;">✅ تأكيد حذف الحائط ${d.wall_name}</button>
              <button class="insp-btn" id="btn-insp-cancel-del" style="background:#334155;border:1px solid #475569;color:#cbd5e1;padding:5px 12px;font-size:11.5px;border-radius:5px;cursor:pointer;">تراجع</button>
            </div>
          </div>
        </div>
      `;
    } else if (type === 'window' || type === 'door') {
      const isWin = (type === 'window');
      inspIcon.textContent = isWin ? '🪟' : '🚪';
      inspHeader.textContent = isWin ? 'فاحص مواصفات الشباك' : 'فاحص مواصفات الباب';
      const tagClass = isWin ? 'win-tag' : 'door-tag';
      const kindAr = isWin ? 'شباك' : 'باب';
      const delBtnId = isWin ? 'btn-insp-del-win' : 'btn-insp-del-door';
      const delBoxId = isWin ? 'insp-del-win-confirm-box' : 'insp-del-door-confirm-box';
      const confBtnId = isWin ? 'btn-insp-confirm-del-win' : 'btn-insp-confirm-del-door';
      const cancBtnId = isWin ? 'btn-insp-cancel-del-win' : 'btn-insp-cancel-del-door';
      const delActionLabel = isWin ? `حذف الشباك ${d.name}` : `حذف الباب ${d.name}`;
      const confPrompt = isWin ? `⚠️ تأكيد حذف الشباك ${d.name} من الحائط (${d.wall_label})؟ سيتم حفظه في قسم الاستعادة.` : `⚠️ تأكيد حذف الباب ${d.name} من الحائط (${d.wall_label})؟ سيتم حفظه في قسم الاستعادة.`;
      const confBtnLabel = isWin ? `✅ تأكيد حذف الشباك ${d.name}` : `✅ تأكيد حذف الباب ${d.name}`;

      html = `
        <div class="insp-tag ${tagClass}">${kindAr} منفصل [${d.type_label}]</div>
        <div class="insp-name">${kindAr} ${d.name}</div>
        <div class="insp-sub">الحائط الحامل: ${d.wall_label}</div>

        <div class="insp-section-title">📐 الأبعاد والارتفاعات</div>
        <div class="insp-grid">
          <div class="insp-item"><span class="insp-label">العرض</span><span class="insp-val"><b>${d.w_m.toFixed(2)} م</b></span></div>
          <div class="insp-item"><span class="insp-label">الارتفاع</span><span class="insp-val">${d.h_m.toFixed(2)} م</span></div>
          ${isWin ? `<div class="insp-item"><span class="insp-label">الجلسة (Sill)</span><span class="insp-val">${d.sill_m.toFixed(2)} م</span></div>` : ''}
          <div class="insp-item"><span class="insp-label">العتب (Lintel)</span><span class="insp-val">${d.lintel_m.toFixed(2)} م</span></div>
          <div class="insp-item"><span class="insp-label">المساحة</span><span class="insp-val">${d.area_m2.toFixed(2)} م²</span></div>
        </div>

        <div class="insp-section-title">📍 الموضع والخلوص على الحائط</div>
        <div class="insp-grid">
          <div class="insp-item"><span class="insp-label">المسافة من البداية</span><span class="insp-val" id="insp-pos-val"><b>${d.pos_m.toFixed(2)} م</b></span></div>
          <div class="insp-item"><span class="insp-label">المسافة لنهاية الحائط</span><span class="insp-val" id="insp-dist-end-val">${(d.wall_len - d.pos_m - d.w_m).toFixed(2)} م</span></div>
          <div class="insp-item" style="grid-column: span 2;">
            <span class="insp-label">الخلوص الآمن المتاح للتحريك</span>
            <span class="insp-val">من ${d.col1_limit.toFixed(2)}م إلى ${d.col2_limit.toFixed(2)}م</span>
          </div>
        </div>

        <div class="insp-actions" style="margin-top:14px;display:flex;flex-direction:column;gap:8px;">
          <button class="insp-btn" id="btn-focus-handle" style="background:#1e293b;border:1px solid #475569;color:#e2e8f0;padding:6px 12px;font-size:11px;border-radius:6px;cursor:pointer;">🎯 تركيز الكاميرا على المقبض</button>
          <button class="insp-btn" id="${delBtnId}" style="background:linear-gradient(135deg,#ef4444,#dc2626);border:1px solid #f87171;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;gap:6px;width:100%;padding:8px 12px;border-radius:6px;cursor:pointer;">
            <span>🗑️</span> <span>${delActionLabel}</span>
          </button>
          <div id="${delBoxId}" style="display:none;margin-top:4px;padding:10px;background:rgba(239,68,68,0.18);border:1.5px solid #ef4444;border-radius:8px;text-align:center;">
            <div style="font-size:12px;color:#fca5a5;font-weight:700;margin-bottom:8px;">${confPrompt}</div>
            <div style="display:flex;gap:8px;justify-content:center;">
              <button class="insp-btn" id="${confBtnId}" style="background:#dc2626;border:1px solid #f87171;color:#fff;padding:5px 14px;font-size:11.5px;font-weight:700;border-radius:5px;cursor:pointer;">${confBtnLabel}</button>
              <button class="insp-btn" id="${cancBtnId}" style="background:#334155;border:1px solid #475569;color:#cbd5e1;padding:5px 12px;font-size:11.5px;border-radius:5px;cursor:pointer;">تراجع</button>
            </div>
          </div>
        </div>
      `;
    } else if (type === 'column') {
      inspIcon.textContent = '🏛️';
      inspHeader.textContent = 'فاحص مواصفات العمود';

      html = `
        <div class="insp-tag col-tag">عمود خرساني إنشائي</div>
        <div class="insp-name">العمود ${d.name}</div>
        <div class="insp-sub">تقاطع المحاور: ${d.grid}</div>

        <div class="insp-section-title">📐 أبعاد القطاع الخرساني</div>
        <div class="insp-grid">
          <div class="insp-item"><span class="insp-label">العرض (W)</span><span class="insp-val"><b>${d.w.toFixed(2)} م</b></span></div>
          <div class="insp-item"><span class="insp-label">العمق (D)</span><span class="insp-val"><b>${d.d.toFixed(2)} م</b></span></div>
          <div class="insp-item"><span class="insp-label">الارتفاع (H)</span><span class="insp-val">${d.h.toFixed(2)} م</span></div>
          <div class="insp-item"><span class="insp-label">المسطح</span><span class="insp-val">${(d.w * d.d).toFixed(3)} م²</span></div>
        </div>

        <div class="insp-section-title">📍 الإحداثيات الإنشائية</div>
        <div class="insp-grid">
          <div class="insp-item"><span class="insp-label">إحداثي X</span><span class="insp-val">${d.cx_real.toFixed(2)} م</span></div>
          <div class="insp-item"><span class="insp-label">إحداثي Y</span><span class="insp-val">${d.cy_real.toFixed(2)} م</span></div>
        </div>

        <div class="insp-actions" style="margin-top:14px;">
          <button class="insp-btn" id="btn-insp-del-col" style="background:linear-gradient(135deg,#ef4444,#dc2626);border:1px solid #f87171;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;gap:6px;width:100%;padding:8px 12px;border-radius:6px;cursor:pointer;">
            <span>🗑️</span> <span>حذف العمود ${d.name}</span>
          </button>
          <div id="insp-del-col-confirm-box" style="display:none;margin-top:8px;padding:10px;background:rgba(239,68,68,0.18);border:1.5px solid #ef4444;border-radius:8px;text-align:center;">
            <div style="font-size:12px;color:#fca5a5;font-weight:700;margin-bottom:8px;">⚠️ تأكيد حذف العمود ${d.name}؟ سيتم حفظه في قسم استعادة الأعمدة.</div>
            <div style="display:flex;gap:8px;justify-content:center;">
              <button class="insp-btn" id="btn-insp-confirm-del-col" style="background:#dc2626;border:1px solid #f87171;color:#fff;padding:5px 14px;font-size:11.5px;font-weight:700;border-radius:5px;cursor:pointer;">✅ تأكيد حذف العمود ${d.name}</button>
              <button class="insp-btn" id="btn-insp-cancel-del-col" style="background:#334155;border:1px solid #475569;color:#cbd5e1;padding:5px 12px;font-size:11.5px;border-radius:5px;cursor:pointer;">تراجع</button>
            </div>
          </div>
        </div>
      `;
    }

    inspBody.innerHTML = html;

    const btnInspDel = document.getElementById('btn-insp-del-wall');
    const inspDelBox = document.getElementById('insp-del-confirm-box');
    const btnInspConf = document.getElementById('btn-insp-confirm-del');
    const btnInspCanc = document.getElementById('btn-insp-cancel-del');

    if (btnInspDel && inspDelBox) {
      btnInspDel.addEventListener('click', function(e) {
        e.stopPropagation();
        playWarningBeep();
        btnInspDel.style.display = 'none';
        inspDelBox.style.display = 'block';
      });
    }
    if (btnInspCanc && inspDelBox && btnInspDel) {
      btnInspCanc.addEventListener('click', function(e) {
        e.stopPropagation();
        inspDelBox.style.display = 'none';
        btnInspDel.style.display = 'flex';
      });
    }
    if (btnInspConf) {
      btnInspConf.addEventListener('click', function(e) {
        e.stopPropagation();
        executeDeleteWall(d);
      });
    }

    const btnInspDelCol = document.getElementById('btn-insp-del-col');
    const inspDelColBox = document.getElementById('insp-del-col-confirm-box');
    const btnInspConfCol = document.getElementById('btn-insp-confirm-del-col');
    const btnInspCancCol = document.getElementById('btn-insp-cancel-del-col');

    if (btnInspDelCol && inspDelColBox) {
      btnInspDelCol.addEventListener('click', function(e) {
        e.stopPropagation();
        playWarningBeep();
        btnInspDelCol.style.display = 'none';
        inspDelColBox.style.display = 'block';
      });
    }
    if (btnInspCancCol && inspDelColBox && btnInspDelCol) {
      btnInspCancCol.addEventListener('click', function(e) {
        e.stopPropagation();
        inspDelColBox.style.display = 'none';
        btnInspDelCol.style.display = 'flex';
      });
    }
    if (btnInspConfCol) {
      btnInspConfCol.addEventListener('click', function(e) {
        e.stopPropagation();
        executeDeleteColumn(d);
      });
    }

    const btnInspDelWin = document.getElementById('btn-insp-del-win');
    const inspDelWinBox = document.getElementById('insp-del-win-confirm-box');
    const btnInspConfWin = document.getElementById('btn-insp-confirm-del-win');
    const btnInspCancWin = document.getElementById('btn-insp-cancel-del-win');

    if (btnInspDelWin && inspDelWinBox) {
      btnInspDelWin.addEventListener('click', function(e) {
        e.stopPropagation();
        playWarningBeep();
        btnInspDelWin.style.display = 'none';
        inspDelWinBox.style.display = 'block';
      });
    }
    if (btnInspCancWin && inspDelWinBox && btnInspDelWin) {
      btnInspCancWin.addEventListener('click', function(e) {
        e.stopPropagation();
        inspDelWinBox.style.display = 'none';
        btnInspDelWin.style.display = 'flex';
      });
    }
    if (btnInspConfWin) {
      btnInspConfWin.addEventListener('click', function(e) {
        e.stopPropagation();
        executeDeleteWindow(d);
      });
    }

    const btnInspDelDoor = document.getElementById('btn-insp-del-door');
    const inspDelDoorBox = document.getElementById('insp-del-door-confirm-box');
    const btnInspConfDoor = document.getElementById('btn-insp-confirm-del-door');
    const btnInspCancDoor = document.getElementById('btn-insp-cancel-del-door');

    if (btnInspDelDoor && inspDelDoorBox) {
      btnInspDelDoor.addEventListener('click', function(e) {
        e.stopPropagation();
        playWarningBeep();
        btnInspDelDoor.style.display = 'none';
        inspDelDoorBox.style.display = 'block';
      });
    }
    if (btnInspCancDoor && inspDelDoorBox && btnInspDelDoor) {
      btnInspCancDoor.addEventListener('click', function(e) {
        e.stopPropagation();
        inspDelDoorBox.style.display = 'none';
        btnInspDelDoor.style.display = 'flex';
      });
    }
    if (btnInspConfDoor) {
      btnInspConfDoor.addEventListener('click', function(e) {
        e.stopPropagation();
        executeDeleteDoor(d);
      });
    }

    const btnFocus = document.getElementById('btn-focus-handle');
    if (btnFocus && d.handleGroup) {
      btnFocus.addEventListener('click', function() {
        controls.target.set(d.handleGroup.position.x, d.handleGroup.position.y, d.handleGroup.position.z);
        controls.update();
        updateHandlesOcclusion();
        setHandleMaterial(d.handleGroup, handleHoverMat);
      });
    }
  }

  // ── شريط إجراءات العنصر العائم (Floating Element Action Bar) ──
  const wallFloatingBar = document.getElementById('wall-floating-bar');
  const wbarIcon = document.getElementById('wbar-icon');
  const wbarTitle = document.getElementById('wbar-title');
  const wbarSub = document.getElementById('wbar-sub');
  const wbarActionsInit = document.getElementById('wbar-actions-init');
  const wbarActionsConfirm = document.getElementById('wbar-actions-confirm');
  const btnWbarDelInit = document.getElementById('btn-wbar-del-init');
  const btnWbarDelConfirm = document.getElementById('btn-wbar-del-confirm');
  const btnWbarCancel = document.getElementById('btn-wbar-cancel');
  const btnWbarCancelConfirm = document.getElementById('btn-wbar-cancel-confirm');
  let currentSelectedWallData = null;
  let currentSelectedColData = null;
  let currentSelectedWinData = null;
  let currentSelectedDoorData = null;

  function showWallFloatingBar(data) {
    if (!wallFloatingBar || !data) return;
    currentSelectedWallData = data;
    currentSelectedColData = null;
    currentSelectedWinData = null;
    currentSelectedDoorData = null;
    if (wbarIcon) wbarIcon.textContent = '🧱';
    if (wbarTitle) wbarTitle.textContent = (data.wall_name || 'حائط') + ' (' + (data.wall_label || '') + ')';
    if (wbarSub) wbarSub.textContent = 'الطول: ' + (data.length ? data.length.toFixed(2) : '0') + 'م | الارتفاع: ' + (data.height ? data.height.toFixed(2) : '0') + 'م | سُمك: ' + (data.thickness_cm || '12') + ' سم';
    if (btnWbarDelInit) btnWbarDelInit.innerHTML = '🗑️ حذف الحائط ' + (data.wall_name || '');
    if (wbarActionsInit) wbarActionsInit.style.display = 'flex';
    if (wbarActionsConfirm) wbarActionsConfirm.style.display = 'none';
    wallFloatingBar.style.display = 'flex';
  }

  function showColumnFloatingBar(data) {
    if (!wallFloatingBar || !data) return;
    currentSelectedColData = data;
    currentSelectedWallData = null;
    currentSelectedWinData = null;
    currentSelectedDoorData = null;
    if (wbarIcon) wbarIcon.textContent = '🏛️';
    if (wbarTitle) wbarTitle.textContent = (data.name || 'عمود') + ' (' + (data.grid || '') + ')';
    const cw_cm = Math.round((data.w || 0.3) * 100);
    const cd_cm = Math.round((data.d || 0.3) * 100);
    if (wbarSub) wbarSub.textContent = 'الأبعاد: ' + cw_cm + '×' + cd_cm + ' سم | الارتفاع: ' + (data.h ? data.h.toFixed(2) : '3.0') + 'م | إحداثي X: ' + (data.cx_real !== undefined ? data.cx_real.toFixed(2) : '0') + 'م, Y: ' + (data.cy_real !== undefined ? data.cy_real.toFixed(2) : '0') + 'م';
    if (btnWbarDelInit) btnWbarDelInit.innerHTML = '🗑️ حذف العمود ' + (data.name || '');
    if (wbarActionsInit) wbarActionsInit.style.display = 'flex';
    if (wbarActionsConfirm) wbarActionsConfirm.style.display = 'none';
    wallFloatingBar.style.display = 'flex';
  }

  function showWindowFloatingBar(data) {
    if (!wallFloatingBar || !data) return;
    currentSelectedWinData = data;
    currentSelectedWallData = null;
    currentSelectedColData = null;
    currentSelectedDoorData = null;
    if (wbarIcon) wbarIcon.textContent = '🪟';
    if (wbarTitle) wbarTitle.textContent = 'شباك ' + (data.name || '') + ' (' + (data.wall_label || '') + ')';
    if (wbarSub) wbarSub.textContent = 'العرض: ' + (data.w_m ? data.w_m.toFixed(2) : '1.00') + 'م | الارتفاع: ' + (data.h_m ? data.h_m.toFixed(2) : '1.20') + 'م | الجلسة: ' + (data.sill_m !== undefined ? data.sill_m.toFixed(2) : '0.90') + 'م';
    if (btnWbarDelInit) btnWbarDelInit.innerHTML = '🗑️ حذف الشباك ' + (data.name || '');
    if (wbarActionsInit) wbarActionsInit.style.display = 'flex';
    if (wbarActionsConfirm) wbarActionsConfirm.style.display = 'none';
    wallFloatingBar.style.display = 'flex';
  }

  function showDoorFloatingBar(data) {
    if (!wallFloatingBar || !data) return;
    currentSelectedDoorData = data;
    currentSelectedWallData = null;
    currentSelectedColData = null;
    currentSelectedWinData = null;
    if (wbarIcon) wbarIcon.textContent = '🚪';
    if (wbarTitle) wbarTitle.textContent = 'باب ' + (data.name || '') + ' (' + (data.wall_label || '') + ')';
    if (wbarSub) wbarSub.textContent = 'العرض: ' + (data.w_m ? data.w_m.toFixed(2) : '0.90') + 'م | الارتفاع: ' + (data.h_m ? data.h_m.toFixed(2) : '2.10') + 'م | الموضع: ' + (data.pos_m ? data.pos_m.toFixed(2) : '0.00') + 'م';
    if (btnWbarDelInit) btnWbarDelInit.innerHTML = '🗑️ حذف الباب ' + (data.name || '');
    if (wbarActionsInit) wbarActionsInit.style.display = 'flex';
    if (wbarActionsConfirm) wbarActionsConfirm.style.display = 'none';
    wallFloatingBar.style.display = 'flex';
  }

  function hideWallFloatingBar() {
    if (!wallFloatingBar) return;
    wallFloatingBar.style.display = 'none';
    if (wbarActionsInit) wbarActionsInit.style.display = 'flex';
    if (wbarActionsConfirm) wbarActionsConfirm.style.display = 'none';
    currentSelectedWallData = null;
    currentSelectedColData = null;
    currentSelectedWinData = null;
    currentSelectedDoorData = null;
  }

  if (btnWbarDelInit) {
    btnWbarDelInit.addEventListener('click', function(e) {
      e.stopPropagation();
      playWarningBeep();
      const pText = document.getElementById('wbar-confirm-prompt');
      if (pText) {
        if (currentSelectedWallData) pText.textContent = '⚠️ تأكيد حذف الحائط ' + (currentSelectedWallData.wall_name || '') + '؟';
        else if (currentSelectedColData) pText.textContent = '⚠️ تأكيد حذف العمود ' + (currentSelectedColData.name || '') + '؟';
        else if (currentSelectedWinData) pText.textContent = '⚠️ تأكيد حذف الشباك ' + (currentSelectedWinData.name || '') + '؟';
        else if (currentSelectedDoorData) pText.textContent = '⚠️ تأكيد حذف الباب ' + (currentSelectedDoorData.name || '') + '؟';
      }
      if (wbarActionsInit) wbarActionsInit.style.display = 'none';
      if (wbarActionsConfirm) wbarActionsConfirm.style.display = 'flex';
    });
  }

  if (btnWbarCancel) {
    btnWbarCancel.addEventListener('click', function(e) {
      e.stopPropagation();
      clearSelection();
    });
  }

  if (btnWbarCancelConfirm) {
    btnWbarCancelConfirm.addEventListener('click', function(e) {
      e.stopPropagation();
      if (wbarActionsInit) wbarActionsInit.style.display = 'flex';
      if (wbarActionsConfirm) wbarActionsConfirm.style.display = 'none';
    });
  }

  if (btnWbarDelConfirm) {
    btnWbarDelConfirm.addEventListener('click', function(e) {
      e.stopPropagation();
      if (currentSelectedWallData && currentSelectedWallData.wall_key) {
        executeDeleteWall(currentSelectedWallData);
      } else if (currentSelectedColData && currentSelectedColData.col_key) {
        executeDeleteColumn(currentSelectedColData);
      } else if (currentSelectedWinData && currentSelectedWinData.id) {
        executeDeleteWindow(currentSelectedWinData);
      } else if (currentSelectedDoorData && currentSelectedDoorData.id) {
        executeDeleteDoor(currentSelectedDoorData);
      }
    });
  }

  function executeDeleteWall(wallData) {
    if (!wallData || !wallData.wall_key) return;
    hideWallFloatingBar();
    if (inspCard) inspCard.style.display = 'none';
    syncDeleteWallToStreamlit(wallData.wall_key, wallData.wall_name || '');
  }

  function executeDeleteColumn(colData) {
    if (!colData || !colData.col_key) return;
    hideWallFloatingBar();
    if (inspCard) inspCard.style.display = 'none';
    syncDeleteColumnToStreamlit(colData.col_key, colData.name || '');
  }

  function executeDeleteWindow(winData) {
    if (!winData || !winData.id) return;
    hideWallFloatingBar();
    if (inspCard) inspCard.style.display = 'none';
    syncDeleteWindowToStreamlit(winData.id, winData.name || '');
  }

  function executeDeleteDoor(doorData) {
    if (!doorData || !doorData.id) return;
    hideWallFloatingBar();
    if (inspCard) inspCard.style.display = 'none';
    syncDeleteDoorToStreamlit(doorData.id, doorData.name || '');
  }

  // ── Keyboard shortcut listener for Floating Plan inside 3D canvas (Ctrl + Alt + F & Esc) ──
  window.addEventListener('keydown', function(e) {
    if (!e) return;
    if (e.key === 'Escape' || e.keyCode === 27) {
      if (isMeasureMode) {
        e.preventDefault();
        e.stopPropagation();
        exitMeasureMode();
        return false;
      }
      try {
        if (window.parent && window.parent.m15FloatingPlan && window.parent.m15FloatingPlan.isOpen && window.parent.m15FloatingPlan.isOpen()) {
          e.preventDefault();
          e.stopPropagation();
          window.parent.m15FloatingPlan.close();
          return false;
        } else if (window.parent && window.parent.m15HideFloatingPlan) {
          window.parent.m15HideFloatingPlan();
        }
      } catch(err) {}
    }
    var codeMatches = (e.code === 'KeyF');
    var keyMatches = (e.key === 'f' || e.key === 'F' || e.key === 'ب' || e.key === 'B' || e.key === 'ـ' || e.key === '[' || e.key === ']' || e.keyCode === 70 || e.which === 70);
    var isF = codeMatches || keyMatches;
    var hasAlt = e.altKey || (e.getModifierState && e.getModifierState('Alt'));
    var hasCtrl = e.ctrlKey || e.metaKey || (e.getModifierState && e.getModifierState('Control'));
    var hasAltGr = (e.getModifierState && e.getModifierState('AltGraph'));
    if (isF && ((hasCtrl && hasAlt) || hasAltGr || (hasCtrl && e.shiftKey))) {
      e.preventDefault();
      e.stopPropagation();
      try {
        if (window.parent && window.parent.m15ToggleFloatingPlan) {
          window.parent.m15ToggleFloatingPlan();
        } else if (window.parent && window.parent.m12ToggleFloatingPlan) {
          window.parent.m12ToggleFloatingPlan();
        }
      } catch(err) {}
      return false;
    }
  }, true);

  // ── Live 3D Dimensions & Badges (Light blue start/end dimensions only) ──
  let activeDimOp = null;
  const badge1 = document.getElementById('dim-badge-1');
  const badge3 = document.getElementById('dim-badge-3');

  function showDimensionLines(op) {
    activeDimOp = op;
    updateDimensionsGeometry(op);
  }

  function hideDimensionLines() {
    activeDimOp = null;
    dimLineGeo.setFromPoints([]);
    if (badge1) badge1.style.display = 'none';
    if (badge3) badge3.style.display = 'none';
  }

  let p1_3d = new THREE.Vector3();
  let p3_3d = new THREE.Vector3();

  function updateDimensionsGeometry(op) {
    if (!op) return;
    const isH = op.is_h;
    const yDim = op.y + op.h / 2.0 + 0.35;
    const tickH = 0.14;

    const points = [];
    const x0 = op.x_start_3d;
    const z0 = op.z_start_3d;
    const pos = op.pos_m;
    const w = op.w_m;
    const wlen = op.wall_len;
    const end = pos + w;

    if (isH) {
      const xStart = x0;
      const xOp1 = x0 + pos;
      const xOp2 = x0 + end;
      const xEnd = x0 + wlen;
      const zLine = z0;

      // Segment 1: Start to Opening Start
      points.push(new THREE.Vector3(xStart, yDim, zLine), new THREE.Vector3(xOp1, yDim, zLine));
      points.push(new THREE.Vector3(xStart, yDim - tickH, zLine), new THREE.Vector3(xStart, yDim + tickH, zLine));
      points.push(new THREE.Vector3(xOp1, yDim - tickH, zLine), new THREE.Vector3(xOp1, yDim + tickH, zLine));

      // Segment 2: Opening Width
      points.push(new THREE.Vector3(xOp1, yDim, zLine), new THREE.Vector3(xOp2, yDim, zLine));
      points.push(new THREE.Vector3(xOp2, yDim - tickH, zLine), new THREE.Vector3(xOp2, yDim + tickH, zLine));

      // Segment 3: Opening End to Wall End
      points.push(new THREE.Vector3(xOp2, yDim, zLine), new THREE.Vector3(xEnd, yDim, zLine));
      points.push(new THREE.Vector3(xEnd, yDim - tickH, zLine), new THREE.Vector3(xEnd, yDim + tickH, zLine));

      p1_3d.set((xStart + xOp1) / 2.0, yDim + 0.08, zLine);
      p3_3d.set((xOp2 + xEnd) / 2.0, yDim + 0.08, zLine);
    } else {
      const zStart = z0;
      const zOp1 = z0 - pos;
      const zOp2 = z0 - end;
      const zEnd = z0 - wlen;
      const xLine = x0;

      // Segment 1
      points.push(new THREE.Vector3(xLine, yDim, zStart), new THREE.Vector3(xLine, yDim, zOp1));
      points.push(new THREE.Vector3(xLine, yDim - tickH, zStart), new THREE.Vector3(xLine, yDim + tickH, zStart));
      points.push(new THREE.Vector3(xLine, yDim - tickH, zOp1), new THREE.Vector3(xLine, yDim + tickH, zOp1));

      // Segment 2
      points.push(new THREE.Vector3(xLine, yDim, zOp1), new THREE.Vector3(xLine, yDim, zOp2));
      points.push(new THREE.Vector3(xLine, yDim - tickH, zOp2), new THREE.Vector3(xLine, yDim + tickH, zOp2));

      // Segment 3
      points.push(new THREE.Vector3(xLine, yDim, zOp2), new THREE.Vector3(xLine, yDim, zEnd));
      points.push(new THREE.Vector3(xLine, yDim - tickH, zEnd), new THREE.Vector3(xLine, yDim + tickH, zEnd));

      p1_3d.set(xLine, yDim + 0.08, (zStart + zOp1) / 2.0);
      p3_3d.set(xLine, yDim + 0.08, (zOp2 + zEnd) / 2.0);
    }

    dimLineGeo.setFromPoints(points);

    const distToEnd = Math.max(0.0, op.wall_len - op.pos_m - op.w_m);
    if (badge1) badge1.innerHTML = `↤ ${op.pos_m.toFixed(2)} م`;
    if (badge3) badge3.innerHTML = `${distToEnd.toFixed(2)} م ↦`;
  }

  function projectToScreen(vec3) {
    const v = vec3.clone().project(camera);
    const x = (v.x * 0.5 + 0.5) * window.innerWidth;
    const y = (-(v.y * 0.5) + 0.5) * window.innerHeight;
    return { x: x, y: y, inFront: v.z < 1.0 };
  }

  function updateDimensionBadgesScreen() {
    if (!activeDimOp) return;
    const b1 = projectToScreen(p1_3d);
    const b3 = projectToScreen(p3_3d);

    if (b1.inFront && activeDimOp.pos_m > 0.05) {
      badge1.style.display = 'block';
      badge1.style.left = b1.x + 'px';
      badge1.style.top = b1.y + 'px';
    } else {
      badge1.style.display = 'none';
    }

    const distToEnd = activeDimOp.wall_len - activeDimOp.pos_m - activeDimOp.w_m;
    if (b3.inFront && distToEnd > 0.05) {
      badge3.style.display = 'block';
      badge3.style.left = b3.x + 'px';
      badge3.style.top = b3.y + 'px';
    } else {
      badge3.style.display = 'none';
    }
  }


  // ── Real-time Wall Cuts Re-layout ──
  function rebuildWallCuts(wallKeyStr) {
    const wallGroup = wallGroups[wallKeyStr];
    if (!wallGroup || !wallGroup.wallPieces) return;

    const opList = allOpenings.filter(o => JSON.stringify(o.wall_key) === wallKeyStr);
    opList.sort((a, b) => a.pos_m - b.pos_m);

    wallGroup.wallPieces.forEach(p => {
      const pData = p.data;
      if (pData.piece_type === 'wall_solid') {
        if (opList.length === 1) {
          const op = opList[0];
          const isH = op.is_h;
          const wlen = op.wall_len;
          const isStartPiece = (pData.d_start < 0.001);
          if (isStartPiece) {
            const newLen = Math.max(0.001, op.pos_m);
            p.mesh.scale.set(isH ? (newLen / pData.w) : 1, 1, isH ? 1 : (newLen / pData.d));
            const newCenter = op.x_start_3d + (newLen / 2.0);
            if (isH) p.mesh.position.x = newCenter;
            else p.mesh.position.z = op.z_start_3d - (newLen / 2.0);
          } else {
            const newLen = Math.max(0.001, wlen - (op.pos_m + op.w_m));
            p.mesh.scale.set(isH ? (newLen / pData.w) : 1, 1, isH ? 1 : (newLen / pData.d));
            const startD = op.pos_m + op.w_m;
            const newCenter = op.x_start_3d + startD + (newLen / 2.0);
            if (isH) p.mesh.position.x = newCenter;
            else p.mesh.position.z = op.z_start_3d - (startD + (newLen / 2.0));
          }
        }
      } else if (pData.piece_type === 'wall_sill' || pData.piece_type === 'wall_lintel') {
        if (opList.length === 1) {
          const op = opList[0];
          const isH = op.is_h;
          const centerD = op.pos_m + op.w_m / 2.0;
          if (isH) p.mesh.position.x = op.x_start_3d + centerD;
          else p.mesh.position.z = op.z_start_3d - centerD;
        }
      }
    });

    // If wall is currently selected, update its bounding highlight
    if (selectedObject === wallGroup && highlightWire) {
      const box = new THREE.Box3().setFromObject(wallGroup);
      const size = new THREE.Vector3();
      box.getSize(size);
      const center = new THREE.Vector3();
      box.getCenter(center);
      highlightWire.position.copy(center);
    }
  }

  // ── Drag & Drop Interaction System ──
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  let isDraggingOpening = false;
  let activeHandle = null;
  let activeOpening = null;
  let dragPlane = new THREE.Plane();
  let planeIntersect = new THREE.Vector3();
  let dragStartIntersect = new THREE.Vector3();
  let dragStartPos = 0;
  let minSafeLimit = 0;
  let maxSafeLimit = 0;
  let pointerDownPos = { x: 0, y: 0 };
  let hasPendingMove = false;
  let lastMovedOp = null;

  function setHandleMaterial(hGroup, mat) {
    if (!hGroup) return;
    hGroup.children.forEach(c => {
      if (c.userData && c.userData.isHitBox) return;
      if (c.material) c.material = mat;
    });
  }

  function syncToStreamlit(type, id, wallKey, newPos) {
    try {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
          px: camera.position.x, py: camera.position.y, pz: camera.position.z,
          tx: controls.target.x, ty: controls.target.y, tz: controls.target.z
        }));
      } catch(e) {}

      const moveData = {
        type: type,
        id: id,
        wall: wallKey,
        pos: Math.round(newPos * 100) / 100,
        ts: Date.now()
      };
      const jsonStr = JSON.stringify(moveData);

      // Method 1: React Bridge directly in window.parent (Zero Page Reload - Stays in Module 12)
      let synced = false;
      try {
        if (window.parent && window.parent.document) {
          const input = window.parent.document.querySelector('input[aria-label="m15_3d_sync_payload"]');
          if (input) {
            const proto = (window.parent.HTMLInputElement || window.HTMLInputElement).prototype;
            const desc = Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) {
              desc.set.call(input, jsonStr);
            } else {
              input.value = jsonStr;
            }
            if (input._valueTracker) {
              input._valueTracker.setValue('');
            }
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: 'Enter', keyCode: 13, which: 13 }));
            input.dispatchEvent(new Event('blur', { bubbles: true }));
            synced = true;
          }
        }
      } catch(e) {
        console.warn("React bridge error:", e);
      }

      if (synced) return;

      // Method 2 Fallback: If React bridge didn't find the input, use location with module=12
      try {
        if (window.parent && window.parent.location) {
          const pUrl = new URL(window.parent.location.href);
          pUrl.searchParams.set('m15_op_move', jsonStr);
          pUrl.searchParams.set('module', '12');
          window.parent.location.href = pUrl.toString();
        }
      } catch(e) {
        console.warn("syncToStreamlit fallback error:", e);
      }
    } catch(e) {
      console.warn("syncToStreamlit error:", e);
    }
  }

  function syncDeleteWallToStreamlit(wallKey, wallName) {
    try {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
          px: camera.position.x, py: camera.position.y, pz: camera.position.z,
          tx: controls.target.x, ty: controls.target.y, tz: controls.target.z
        }));
      } catch(e) {}

      const deletePayload = {
        action: 'delete_wall',
        type: 'delete_wall',
        wall: wallKey,
        name: wallName,
        ts: Date.now()
      };
      const jsonStr = JSON.stringify(deletePayload);

      let synced = false;
      try {
        if (window.parent && window.parent.document) {
          const input = window.parent.document.querySelector('input[aria-label="m15_3d_sync_payload"]');
          if (input) {
            const proto = (window.parent.HTMLInputElement || window.HTMLInputElement).prototype;
            const desc = Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) {
              desc.set.call(input, jsonStr);
            } else {
              input.value = jsonStr;
            }
            if (input._valueTracker) {
              input._valueTracker.setValue('');
            }
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: 'Enter', keyCode: 13, which: 13 }));
            input.dispatchEvent(new Event('blur', { bubbles: true }));
            synced = true;
          }
        }
      } catch(e) {
        console.warn("React bridge delete error:", e);
      }

      if (synced) return;

      try {
        if (window.parent && window.parent.location) {
          const pUrl = new URL(window.parent.location.href);
          pUrl.searchParams.set('m15_op_move', jsonStr);
          pUrl.searchParams.set('module', '12');
          window.parent.location.href = pUrl.toString();
        }
      } catch(e) {
        console.warn("syncDeleteWallToStreamlit fallback error:", e);
      }
    } catch(e) {
      console.warn("syncDeleteWallToStreamlit error:", e);
    }
  }

  function syncDeleteColumnToStreamlit(colKey, colName) {
    try {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
          px: camera.position.x, py: camera.position.y, pz: camera.position.z,
          tx: controls.target.x, ty: controls.target.y, tz: controls.target.z
        }));
      } catch(e) {}

      const deletePayload = {
        action: 'delete_column',
        type: 'delete_column',
        col: colKey,
        name: colName,
        ts: Date.now()
      };
      const jsonStr = JSON.stringify(deletePayload);

      let synced = false;
      try {
        if (window.parent && window.parent.document) {
          const input = window.parent.document.querySelector('input[aria-label="m15_3d_sync_payload"]');
          if (input) {
            const proto = (window.parent.HTMLInputElement || window.HTMLInputElement).prototype;
            const desc = Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) {
              desc.set.call(input, jsonStr);
            } else {
              input.value = jsonStr;
            }
            if (input._valueTracker) {
              input._valueTracker.setValue('');
            }
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: 'Enter', keyCode: 13, which: 13 }));
            input.dispatchEvent(new Event('blur', { bubbles: true }));
            synced = true;
          }
        }
      } catch(e) {
        console.warn("React bridge col delete error:", e);
      }

      if (synced) return;

      try {
        if (window.parent && window.parent.location) {
          const pUrl = new URL(window.parent.location.href);
          pUrl.searchParams.set('m15_op_move', jsonStr);
          pUrl.searchParams.set('module', '12');
          window.parent.location.href = pUrl.toString();
        }
      } catch(e) {
        console.warn("syncDeleteColumnToStreamlit fallback error:", e);
      }
    } catch(e) {
      console.warn("syncDeleteColumnToStreamlit error:", e);
    }
  }

  function syncDeleteWindowToStreamlit(winId, winName) {
    try {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
          px: camera.position.x, py: camera.position.y, pz: camera.position.z,
          tx: controls.target.x, ty: controls.target.y, tz: controls.target.z
        }));
      } catch(e) {}

      const deletePayload = {
        action: 'delete_window',
        type: 'delete_window',
        id: winId,
        name: winName,
        ts: Date.now()
      };
      const jsonStr = JSON.stringify(deletePayload);

      let synced = false;
      try {
        if (window.parent && window.parent.document) {
          const input = window.parent.document.querySelector('input[aria-label="m15_3d_sync_payload"]');
          if (input) {
            const proto = (window.parent.HTMLInputElement || window.HTMLInputElement).prototype;
            const desc = Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) {
              desc.set.call(input, jsonStr);
            } else {
              input.value = jsonStr;
            }
            if (input._valueTracker) {
              input._valueTracker.setValue('');
            }
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: 'Enter', keyCode: 13, which: 13 }));
            input.dispatchEvent(new Event('blur', { bubbles: true }));
            synced = true;
          }
        }
      } catch(e) {
        console.warn("React bridge window delete error:", e);
      }

      if (synced) return;

      try {
        if (window.parent && window.parent.location) {
          const pUrl = new URL(window.parent.location.href);
          pUrl.searchParams.set('m15_op_move', jsonStr);
          pUrl.searchParams.set('module', '12');
          window.parent.location.href = pUrl.toString();
        }
      } catch(e) {
        console.warn("syncDeleteWindowToStreamlit fallback error:", e);
      }
    } catch(e) {
      console.warn("syncDeleteWindowToStreamlit error:", e);
    }
  }

  function syncDeleteDoorToStreamlit(doorId, doorName) {
    try {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
          px: camera.position.x, py: camera.position.y, pz: camera.position.z,
          tx: controls.target.x, ty: controls.target.y, tz: controls.target.z
        }));
      } catch(e) {}

      const deletePayload = {
        action: 'delete_door',
        type: 'delete_door',
        id: doorId,
        name: doorName,
        ts: Date.now()
      };
      const jsonStr = JSON.stringify(deletePayload);

      let synced = false;
      try {
        if (window.parent && window.parent.document) {
          const input = window.parent.document.querySelector('input[aria-label="m15_3d_sync_payload"]');
          if (input) {
            const proto = (window.parent.HTMLInputElement || window.HTMLInputElement).prototype;
            const desc = Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) {
              desc.set.call(input, jsonStr);
            } else {
              input.value = jsonStr;
            }
            if (input._valueTracker) {
              input._valueTracker.setValue('');
            }
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: 'Enter', keyCode: 13, which: 13 }));
            input.dispatchEvent(new Event('blur', { bubbles: true }));
            synced = true;
          }
        }
      } catch(e) {
        console.warn("React bridge door delete error:", e);
      }

      if (synced) return;

      try {
        if (window.parent && window.parent.location) {
          const pUrl = new URL(window.parent.location.href);
          pUrl.searchParams.set('m15_op_move', jsonStr);
          pUrl.searchParams.set('module', '12');
          window.parent.location.href = pUrl.toString();
        }
      } catch(e) {
        console.warn("syncDeleteDoorToStreamlit fallback error:", e);
      }
    } catch(e) {
      console.warn("syncDeleteDoorToStreamlit error:", e);
    }
  }

  // Start dragging an opening (called by clicking 3D handle)
  function startDraggingOpening(op, clientX, clientY) {
    isDraggingOpening = true;
    activeOpening = op;
    activeHandle = op.handleGroup;
    controls.enabled = false;

    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    dragPlane.set(new THREE.Vector3(0, 1, 0), -activeHandle.position.y);
    raycaster.ray.intersectPlane(dragPlane, dragStartIntersect);
    dragStartPos = activeOpening.pos_m;

    minSafeLimit = activeOpening.col1_limit || 0.0;
    maxSafeLimit = (activeOpening.col2_limit || activeOpening.wall_len) - activeOpening.w_m;

    const myWallKey = JSON.stringify(activeOpening.wall_key);
    const siblings = allOpenings.filter(o => JSON.stringify(o.wall_key) === myWallKey && o.id !== activeOpening.id);
    siblings.forEach(sib => {
      if (sib.pos_m < dragStartPos) {
        minSafeLimit = Math.max(minSafeLimit, sib.pos_m + sib.w_m + 0.05);
      } else if (sib.pos_m > dragStartPos) {
        maxSafeLimit = Math.min(maxSafeLimit, sib.pos_m - activeOpening.w_m - 0.05);
      }
    });

    setHandleMaterial(activeHandle, handleDragMat);
    showDimensionLines(activeOpening);
    const elemType = activeOpening.handleGroup.userData.isDoor ? 'door' : (activeOpening.type_label ? 'window' : 'door');
    setSelection(activeOpening.mesh, elemType, activeOpening);
  }

  // ── High-Precision Raycasting & Hover Tracking System ──
  let mouseMoved = false;
  let mouseClientX = -1;
  let mouseClientY = -1;
  let isPointerDown = false;
  let currentHoveredItem = null;

  function resolvePickableElement(hitMesh) {
    if (!hitMesh) return null;
    let curr = hitMesh;
    while (curr && !curr.userData.elementType && curr.parent && curr.parent !== rootGroup && curr.parent !== scene) {
      curr = curr.parent;
    }
    if (!curr || !curr.userData || !curr.userData.elementType) return null;

    const elType = curr.userData.elementType;
    if (elType === 'wall_piece' || elType === 'wall') {
      const targetWallGroup = curr.userData.parentWallGroup || (elType === 'wall' ? curr : null);
      const targetData = (targetWallGroup && targetWallGroup.userData.data) || curr.userData.data;
      return {
        object: targetWallGroup,
        type: 'wall',
        data: targetData,
        hitMesh: hitMesh
      };
    } else if (elType === 'window') {
      return {
        object: curr,
        type: 'window',
        data: curr.userData.data,
        hitMesh: hitMesh
      };
    } else if (elType === 'door') {
      const doorGroup = curr.userData.parentGroup || (curr.isGroup ? curr : curr.parent);
      const doorData = (doorGroup && doorGroup.userData.data) || curr.userData.data;
      return {
        object: doorGroup || curr,
        type: 'door',
        data: doorData,
        hitMesh: hitMesh
      };
    } else if (elType === 'column') {
      return {
        object: curr,
        type: 'column',
        data: curr.userData.data,
        hitMesh: hitMesh
      };
    }
    return null;
  }

  // ── اختبار الحجب البصري اللحظي للمقابض وربطها برؤية الحائط (Occlusion & Line of Sight) ──
  const occRaycaster = new THREE.Raycaster();
  const occDir = new THREE.Vector3();
  const occTarget = new THREE.Vector3();
  const lastCamPos = new THREE.Vector3();
  const lastCamTarget = new THREE.Vector3();

  function checkCameraChanged() {
    const moved = (
      Math.abs(camera.position.x - lastCamPos.x) > 0.001 ||
      Math.abs(camera.position.y - lastCamPos.y) > 0.001 ||
      Math.abs(camera.position.z - lastCamPos.z) > 0.001 ||
      Math.abs(controls.target.x - lastCamTarget.x) > 0.001 ||
      Math.abs(controls.target.y - lastCamTarget.y) > 0.001 ||
      Math.abs(controls.target.z - lastCamTarget.z) > 0.001
    );
    if (moved) {
      lastCamPos.copy(camera.position);
      lastCamTarget.copy(controls.target);
    }
    return moved;
  }

  function updateHandlesOcclusion() {
    if (!handleMeshes || handleMeshes.length === 0) return;

    for (let i = 0; i < handleMeshes.length; i++) {
      const hGroup = handleMeshes[i];
      const op = hGroup.userData && hGroup.userData.op;
      if (!op) continue;

      // 1. إذا كان المقبض قيد السحب حالياً من قبل المستخدم، يظل مرئياً ومفعلاً
      if (isDraggingOpening && activeOpening === op) {
        hGroup.visible = true;
        continue;
      }

      // 2. التحقق من حالة الحائط الحاضن للفتحة (Wall Visibility Dependency)
      const wallKeyStr = JSON.stringify(op.wall_key);
      const hostWall = wallGroups[wallKeyStr];
      if (!hostWall || hostWall.visible === false) {
        hGroup.visible = false;
        continue;
      }

      // 3. التحقق من حالة مجسم الفتحة نفسها
      if (op.mesh && op.mesh.visible === false) {
        hGroup.visible = false;
        continue;
      }

      // 4. اختبار خط الرؤية المباشر من الكاميرا إلى المقبض (Line of Sight Raycast)
      hGroup.getWorldPosition(occTarget);
      occDir.subVectors(occTarget, camera.position);
      const distToHandle = occDir.length();
      if (distToHandle < 0.10) {
        hGroup.visible = true;
        continue;
      }
      occDir.normalize();

      occRaycaster.set(camera.position, occDir);
      occRaycaster.near = 0.1;
      occRaycaster.far = distToHandle;

      const hits = occRaycaster.intersectObjects(selectableObjects, false);
      let isBlocked = false;

      for (let j = 0; j < hits.length; j++) {
        const hit = hits[j];
        // يجب أن يكون العائق أمام المقبض بمسافة خلوص هندسية
        if (hit.distance >= distToHandle - 0.15) break;

        // استبعاد مجسم الفتحة نفسها (ضلفة الباب أو زجاج الشباك) من حجب مقبضها الخاص
        const hitElem = resolvePickableElement(hit.object);
        if (hitElem && (hitElem.type === 'window' || hitElem.type === 'door')) {
          if (hitElem.data && hitElem.data.id === op.id) {
            continue;
          }
        }

        // وجود حائط مصمت أو عمود أو كتلة إنشائية أخرى تحجب المقبض بصرياً تماماً
        isBlocked = true;
        break;
      }

      hGroup.visible = !isBlocked;
    }
  }

  function performPreciseRaycast(clientX, clientY) {
    const rect = renderer.domElement.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    // 1. حساب تقاطعات الكتل الإنشائية المصمتة أولاً لتحديد عمق العناصر الأمامية
    const solidIntersects = raycaster.intersectObjects(selectableObjects, false);
    const closestSolid = (solidIntersects.length > 0) ? solidIntersects[0] : null;

    // 2. التحقق من مقابض التحكم المرئية وغير المحجوبة فقط (Visible & Unoccluded Handles)
    const visibleHandles = handleMeshes.filter(h => {
      if (!h.visible) return false;
      const op = h.userData && h.userData.op;
      if (op) {
        const wGroup = wallGroups[JSON.stringify(op.wall_key)];
        if (wGroup && wGroup.visible === false) return false;
        if (op.mesh && op.mesh.visible === false) return false;
      }
      return true;
    });

    const handleIntersects = raycaster.intersectObjects(visibleHandles, true);
    for (let k = 0; k < handleIntersects.length; k++) {
      const hHit = handleIntersects[k];
      let hitH = hHit.object;
      while (hitH && !hitH.userData.isHandle && hitH.parent) {
        hitH = hitH.parent;
      }
      if (hitH && hitH.userData && hitH.userData.isHandle && hitH.visible) {
        const op = hitH.userData.op;
        // منع الالتقاط إذا كان هناك حائط مصمت أو عنصر إنشائي يقع أمام المقبض
        let isOccludedBySolid = false;
        if (closestSolid && closestSolid.distance < hHit.distance - 0.05) {
          const solidElem = resolvePickableElement(closestSolid.object);
          // لا يعتبر محجوباً إذا كان العنصر الأقرب هو مجسم الفتحة نفسها
          if (!solidElem || !((solidElem.type === 'window' || solidElem.type === 'door') && solidElem.data && op && solidElem.data.id === op.id)) {
            isOccludedBySolid = true;
          }
        }

        if (!isOccludedBySolid) {
          return {
            isHandle: true,
            handleGroup: hitH,
            op: op,
            distance: hHit.distance
          };
        }
      }
    }

    if (!closestSolid) return null;

    // 3. ترتيب التقاط الكتل بحسب المسافة للكاميرا مع حل التداخلات الدقيقة
    let chosenIntersect = closestSolid;
    if (solidIntersects.length > 1) {
      const d0 = solidIntersects[0].distance;
      const d1 = solidIntersects[1].distance;
      if (Math.abs(d0 - d1) < 0.002) {
        const el0 = resolvePickableElement(solidIntersects[0].object);
        const el1 = resolvePickableElement(solidIntersects[1].object);
        if (el0 && el1 && el0.object !== el1.object) {
          if (el1.type === 'window' || el1.type === 'door') {
            chosenIntersect = solidIntersects[1];
          } else if (el0.type === 'wall' && el1.type === 'column') {
            chosenIntersect = solidIntersects[1];
          }
        }
      }
    }

    const resolved = resolvePickableElement(chosenIntersect.object);
    if (!resolved) return null;
    resolved.distance = chosenIntersect.distance;
    resolved.point = chosenIntersect.point;
    return resolved;
  }

  function clearHover() {
    if (currentHoveredItem) {
      if (currentHoveredItem.object && currentHoveredItem.object !== selectedObject) {
        removeHoverMeshGlow(currentHoveredItem.object);
      }
      currentHoveredItem = null;
    }
    selectableObjects.forEach(function(obj) {
      if (obj !== selectedObject && obj.userData && obj.userData.origHoverEmissives) {
        removeHoverMeshGlow(obj);
      }
    });
    hideHoverBoundingBox();
    handleMeshes.forEach(h => {
      if (h !== activeHandle) setHandleMaterial(h, handleMat);
    });
    document.body.style.cursor = 'default';
  }

  function updateHoverState(clientX, clientY) {
    const hit = performPreciseRaycast(clientX, clientY);

    if (!hit) {
      clearHover();
      return;
    }

    if (hit.isHandle) {
      if (currentHoveredItem && currentHoveredItem.object !== selectedObject) {
        removeHoverMeshGlow(currentHoveredItem.object);
      }
      currentHoveredItem = hit;
      document.body.style.cursor = 'grab';
      setHandleMaterial(hit.handleGroup, handleHoverMat);

      if (hit.op && hit.op.mesh) {
        const box = new THREE.Box3().setFromObject(hit.op.mesh);
        updateHoverBoundingBox(box);
      }
      return;
    }

    handleMeshes.forEach(h => {
      if (h !== activeHandle) setHandleMaterial(h, handleMat);
    });

    document.body.style.cursor = 'pointer';

    if (currentHoveredItem && currentHoveredItem.object === hit.object) {
      return;
    }

    if (currentHoveredItem && currentHoveredItem.object && currentHoveredItem.object !== selectedObject) {
      removeHoverMeshGlow(currentHoveredItem.object);
    }

    currentHoveredItem = hit;

    if (hit.object === selectedObject) {
      hideHoverBoundingBox();
      return;
    }

    const box = new THREE.Box3().setFromObject(hit.object);
    updateHoverBoundingBox(box);
    applyHoverMeshGlow(hit.object);
  }

  function handleOpeningDrag(clientX, clientY) {
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    document.body.style.cursor = 'grabbing';
    if (raycaster.ray.intersectPlane(dragPlane, planeIntersect)) {
      let delta = 0;
      if (activeOpening.is_h) {
        delta = planeIntersect.x - dragStartIntersect.x;
      } else {
        delta = -(planeIntersect.z - dragStartIntersect.z);
      }

      const rawPos = dragStartPos + delta;
      const clampedPos = Math.max(minSafeLimit, Math.min(maxSafeLimit, rawPos));
      const isBlocked = (rawPos < minSafeLimit - 0.015 || rawPos > maxSafeLimit + 0.015);

      setHandleMaterial(activeHandle, isBlocked ? handleWarnMat : handleDragMat);

      activeOpening.pos_m = Math.round(clampedPos * 100) / 100;

      const isH = activeOpening.is_h;
      const newMid = activeOpening.pos_m + activeOpening.w_m / 2.0;

      if (isH) {
        const newX = activeOpening.x_start_3d + newMid;
        activeOpening.mesh.position.x = newX;
        activeHandle.position.x = newX;
      } else {
        const newZ = activeOpening.z_start_3d - newMid;
        activeOpening.mesh.position.z = newZ;
        activeHandle.position.z = newZ;
      }

      rebuildWallCuts(JSON.stringify(activeOpening.wall_key));
      updateDimensionsGeometry(activeOpening);

      if (selectedObject && highlightWire) {
        const sBox = new THREE.Box3().setFromObject(selectedObject);
        const sCenter = new THREE.Vector3();
        sBox.getCenter(sCenter);
        highlightWire.position.copy(sCenter);
      }

      const inspPos = document.getElementById('insp-pos-val');
      if (inspPos) inspPos.innerHTML = `<b>${activeOpening.pos_m.toFixed(2)} م</b>`;
      const inspEnd = document.getElementById('insp-dist-end-val');
      if (inspEnd) inspEnd.innerHTML = `${(activeOpening.wall_len - activeOpening.pos_m - activeOpening.w_m).toFixed(2)} م`;

      hasPendingMove = true;
      lastMovedOp = activeOpening;
    }
  }

  function onPointerDown(e) {
    isPointerDown = true;
    pointerDownPos.x = e.clientX;
    pointerDownPos.y = e.clientY;

    if (isMeasureMode && measureStep < 2) {
      if (e.button === 0) {
        return; // Left click is strictly reserved for picking measure points
      }
    }

    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    // 1. Check if clicked on an unoccluded 3D Handle Gizmo
    const hit = performPreciseRaycast(e.clientX, e.clientY);
    if (hit && hit.isHandle) {
      clearHover();
      startDraggingOpening(hit.op, e.clientX, e.clientY);
      return;
    }
  }

  function onPointerMove(e) {
    mouseClientX = e.clientX;
    mouseClientY = e.clientY;
    mouseMoved = true;

    if (isMeasureMode && measureStep < 2) {
      updateMeasureHover(e.clientX, e.clientY);
      return;
    }

    if (isDraggingOpening && activeOpening) {
      handleOpeningDrag(e.clientX, e.clientY);
    }
  }

  function onPointerUp(e) {
    isPointerDown = false;

    if (isMeasureMode && measureStep < 2) {
      if (e.button === 0) {
        const dist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);
        if (dist < 6) {
          handleMeasureClick(e.clientX, e.clientY);
        }
      }
      return;
    }

    if (isMeasureMode && measureStep === 2) {
      // In measure mode after completing dimension Point B:
      // Left click is for camera rotation so engineer can inspect dimension from all angles.
      return;
    }

    if (isDraggingOpening) {
      isDraggingOpening = false;
      controls.enabled = true;
      setHandleMaterial(activeHandle, handleMat);
      document.body.style.cursor = 'default';

      if (hasPendingMove && lastMovedOp) {
        const didMove = Math.abs(lastMovedOp.pos_m - dragStartPos) > 0.005;
        if (didMove) {
          const opKind = lastMovedOp.op_kind || ((lastMovedOp.handleGroup && lastMovedOp.handleGroup.userData && lastMovedOp.handleGroup.userData.isDoor) ? 'door' : 'win');
          syncToStreamlit(opKind, lastMovedOp.id, lastMovedOp.wall_key, lastMovedOp.pos_m);
        }
        hasPendingMove = false;
      }
    } else {
      // Click selection: Detect elements or walls as complete units
      const dist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);
      if (dist < 5 && e.button === 0) {
        let targetHit = currentHoveredItem;
        if (!targetHit || targetHit.isHandle) {
          targetHit = performPreciseRaycast(e.clientX, e.clientY);
        }

        if (targetHit && !targetHit.isHandle && targetHit.object) {
          removeHoverMeshGlow(targetHit.object);
          hideHoverBoundingBox();
          currentHoveredItem = null;
          setSelection(targetHit.object, targetHit.type, targetHit.data);
        } else if (!targetHit || (!targetHit.isHandle && !targetHit.object)) {
          clearSelection();
          clearHover();
        }
      }
    }
  }

  container.addEventListener('pointerdown', onPointerDown);
  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp);
  container.addEventListener('pointerleave', function() {
    mouseMoved = false;
    if (!isMeasureMode || measureStep === 2) {
      clearHover();
    } else {
      if (snapMarkerGroup) snapMarkerGroup.visible = false;
      if (perpMarkerGroup) perpMarkerGroup.visible = false;
    }
  });

  // Camera Setup & State Preservation across Streamlit reruns
  const STORAGE_KEY = 'm15_threejs_camera_state';
  const defCamPos = { x: maxDim * 1.35, y: maxDim * 1.15, z: maxDim * 1.45 };
  const defTarget = { x: 0, y: (data.default_h || 3.0) / 2.0, z: 0 };

  let savedCam = null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) savedCam = JSON.parse(raw);
  } catch(e) {}

  if (savedCam && typeof savedCam.px === 'number' && !isNaN(savedCam.px)) {
    camera.position.set(savedCam.px, savedCam.py, savedCam.pz);
    controls.target.set(savedCam.tx, savedCam.ty, savedCam.tz);
  } else {
    camera.position.set(defCamPos.x, defCamPos.y, defCamPos.z);
    controls.target.set(defTarget.x, defTarget.y, defTarget.z);
  }
  controls.update();

  let saveTimer = null;
  controls.addEventListener('change', function() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(function() {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
          px: camera.position.x, py: camera.position.y, pz: camera.position.z,
          tx: controls.target.x, ty: controls.target.y, tz: controls.target.z
        }));
      } catch(e) {}
    }, 50);
  });

  document.getElementById('btn-reset').addEventListener('click', function() {
    try { sessionStorage.removeItem(STORAGE_KEY); } catch(e) {}
    camera.position.set(defCamPos.x, defCamPos.y, defCamPos.z);
    controls.target.set(defTarget.x, defTarget.y, defTarget.z);
    controls.update();
  });

  document.getElementById('btn-theme').addEventListener('click', function() {
    isDark = !isDark;
    scene.background.set(isDark ? bgDark : bgLight);
    hoverWireMat.color.setHex(isDark ? 0x00f0ff : 0x0284c7);
    hoverFillMat.color.setHex(isDark ? 0x00f0ff : 0x0284c7);
    cornerBracketMat.color.setHex(isDark ? 0xffffff : 0x0369a1);
  });

  document.getElementById('btn-fs').addEventListener('click', function() {
    const el = document.documentElement;
    if (!document.fullscreenElement) {
      if (el.requestFullscreen) el.requestFullscreen();
      else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    } else {
      if (document.exitFullscreen) document.exitFullscreen();
      else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
    }
  });

  // ── زر تبديل إظهار / إخفاء المحاور الإنشائية ثلاثية الأبعاد ──
  let axesVisible = true;
  const btnToggleAxes = document.getElementById('btn-toggle-axes');
  if (btnToggleAxes) {
    btnToggleAxes.addEventListener('click', function() {
      axesVisible = !axesVisible;
      axesGroup.visible = axesVisible;
      btnToggleAxes.style.background = axesVisible ? '#dc2626' : '#475569';
      btnToggleAxes.style.borderColor = axesVisible ? '#f87171' : '#64748b';
      btnToggleAxes.textContent = axesVisible ? '🔴 المحاور' : '⚪ المحاور (مخفية)';
    });
  }

  // ── زر تشغيل أداة القياس التفاعلية ثلاثية الأبعاد (Measure Tool) ──
  const btnMeasure = document.getElementById('btn-measure');
  const btnClearMeasure = document.getElementById('btn-clear-measure');
  const btnMeasureBannerClose = document.getElementById('btn-measure-banner-close');

  if (btnMeasure) {
    btnMeasure.addEventListener('click', function(e) {
      e.stopPropagation();
      if (!isMeasureMode) {
        enterMeasureMode();
      } else if (measureStep === 2) {
        // Start a fresh new measurement
        clearMeasurements();
        measureStep = 0;
        controls.mouseButtons = {
          LEFT: null,
          MIDDLE: THREE.MOUSE.DOLLY,
          RIGHT: THREE.MOUSE.ROTATE
        };
        renderer.domElement.style.cursor = 'crosshair';
        container.style.cursor = 'crosshair';
        document.body.style.cursor = 'crosshair';
        const bannerText = document.getElementById('measure-banner-text');
        if (bannerText) {
          bannerText.innerHTML = '📏 <b>قياس جديد</b>: انقر بالزر الأيسر لتحديد نقطة البداية (Point A) • التدوير بالزر الأيمن أو العجلة • اضغط Esc للإلغاء';
        }
      } else {
        exitMeasureMode();
      }
    });
  }

  if (btnClearMeasure) {
    btnClearMeasure.addEventListener('click', function(e) {
      e.stopPropagation();
      exitMeasureMode();
    });
  }

  if (btnMeasureBannerClose) {
    btnMeasureBannerClose.addEventListener('click', function(e) {
      e.stopPropagation();
      exitMeasureMode();
    });
  }

  // ── Mini-Plan Interactive Logic ──
  const miniCard = document.getElementById('mini-plan-card');
  const miniDrag = document.getElementById('mini-plan-drag');
  const btnMiniToggle = document.getElementById('btn-mini-toggle');
  const btnMiniClose = document.getElementById('btn-mini-close');
  const btnToolbarPlan = document.getElementById('btn-toggle-plan');
  const btnMiniExpand = document.getElementById('btn-mini-expand');
  const miniWrapper = document.getElementById('mini-plan-wrapper');
  const modal = document.getElementById('plan-modal');
  const modalClose = document.getElementById('modal-close');
  const modalBackdrop = document.getElementById('modal-backdrop');

  const DEFAULT_LEFT = 12;
  const DEFAULT_TOP = 55;

  [miniCard, modal, inspCard].forEach(function(el) {
    if (!el) return;
    el.addEventListener('mousedown', function(e) { e.stopPropagation(); });
    el.addEventListener('touchstart', function(e) { e.stopPropagation(); }, { passive: true });
    el.addEventListener('wheel', function(e) { e.stopPropagation(); });
  });

  let isDraggingMini = false;
  let startX = 0, startY = 0, startLeft = 0, startTop = 0;

  function onMiniDragStart(cx, cy) {
    isDraggingMini = true;
    startX = cx;
    startY = cy;
    const rect = miniCard.getBoundingClientRect();
    startLeft = rect.left;
    startTop = rect.top;
    miniCard.style.transition = 'none';
  }

  function onMiniDragMove(cx, cy) {
    if (!isDraggingMini) return;
    const dx = cx - startX;
    const dy = cy - startY;
    const maxLeft = window.innerWidth - miniCard.offsetWidth - 8;
    const maxTop = window.innerHeight - miniCard.offsetHeight - 8;
    const newLeft = Math.max(8, Math.min(startLeft + dx, maxLeft));
    const newTop = Math.max(8, Math.min(startTop + dy, maxTop));
    miniCard.style.left = newLeft + 'px';
    miniCard.style.top = newTop + 'px';
    miniCard.style.right = 'auto';
  }

  function onMiniDragEnd() {
    if (isDraggingMini) {
      isDraggingMini = false;
      miniCard.style.transition = '';
      try {
        sessionStorage.setItem('m15_mini_plan_pos', JSON.stringify({
          left: miniCard.offsetLeft,
          top: miniCard.offsetTop
        }));
      } catch(e) {}
    }
  }

  if (miniDrag) {
    miniDrag.addEventListener('mousedown', function(e) {
      if (e.target.closest('.mini-btn')) return;
      e.preventDefault();
      e.stopPropagation();
      onMiniDragStart(e.clientX, e.clientY);
    });
  }

  window.addEventListener('mousemove', function(e) { onMiniDragMove(e.clientX, e.clientY); });
  window.addEventListener('mouseup', onMiniDragEnd);

  let isMinimized = false;
  if (btnMiniToggle) {
    btnMiniToggle.addEventListener('click', function(e) {
      e.stopPropagation();
      isMinimized = !isMinimized;
      if (isMinimized) {
        miniCard.classList.add('minimized');
        btnMiniToggle.textContent = '➕';
      } else {
        miniCard.classList.remove('minimized');
        btnMiniToggle.textContent = '➖';
      }
    });
  }

  function resetAndShowPlan() {
    miniCard.style.display = 'block';
    miniCard.style.opacity = '1.0';
    miniCard.style.left = DEFAULT_LEFT + 'px';
    miniCard.style.top = DEFAULT_TOP + 'px';
    try {
      sessionStorage.setItem('m15_mini_plan_visible', 'true');
    } catch(e) {}
  }

  function hidePlan() {
    miniCard.style.display = 'none';
    try {
      sessionStorage.setItem('m15_mini_plan_visible', 'false');
    } catch(e) {}
  }

  if (btnMiniClose) btnMiniClose.addEventListener('click', hidePlan);
  if (btnToolbarPlan) {
    btnToolbarPlan.addEventListener('click', function() {
      if (miniCard.style.display === 'none') resetAndShowPlan();
      else hidePlan();
    });
  }

  function openModal() { if (modal) modal.style.display = 'flex'; }
  function closeModal() { if (modal) modal.style.display = 'none'; }
  if (btnMiniExpand) btnMiniExpand.addEventListener('click', openModal);
  if (miniWrapper) miniWrapper.addEventListener('click', openModal);
  if (modalClose) modalClose.addEventListener('click', closeModal);
  if (modalBackdrop) modalBackdrop.addEventListener('click', closeModal);

  window.addEventListener('resize', function() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });

  function animate() {
    requestAnimationFrame(animate);
    controls.update();

    if (checkCameraChanged()) {
      updateHandlesOcclusion();
    }

    if (mouseMoved && !isPointerDown && !isDraggingOpening) {
      if (!isMeasureMode || measureStep === 2) {
        updateHoverState(mouseClientX, mouseClientY);
      }
      mouseMoved = false;
    }

    // Dynamic distance-based scaling for billboard dimension sprite
    if (measureLabelSprite && measureLabelSprite.visible) {
      const camDist = camera.position.distanceTo(measureLabelSprite.position);
      const s = Math.max(0.5, Math.min(5.0, camDist * 0.11));
      measureLabelSprite.scale.set(s * 2.2, s * 0.55, 1.0);
    }

    renderer.render(scene, camera);
    updateDimensionBadgesScreen();
  }
  updateHandlesOcclusion();
  animate();
})();
</script>
</body>
</html>"""

    final_html = (
        html_template
        .replace("__SCENE_DATA__", json_str)
        .replace("__PLAN_B64__", plan_b64)
        .replace("__N_WALLS__", str(scene_data["n_walls"]))
        .replace("__N_COLS__", str(scene_data["n_columns"]))
        .replace("__N_WINS__", str(scene_data["n_windows"]))
        .replace("__N_DOORS__", str(scene_data.get("n_doors", len(scene_data.get("doors", [])))))
        .replace("__DEF_H__", f"{scene_data['default_h']:.2f}")
        .replace("__PAR_H__", f"{scene_data['parapet_h']:.2f}")
    )

    # ── Real-time In-Session Sync Input (Zero-Reload Bridge) ──
    st.markdown(
        """<style>
        div[data-testid="stTextInput"]:has(input[aria-label="m15_3d_sync_payload"]) {
            display: none !important;
            height: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
            position: absolute !important;
            pointer-events: none !important;
            opacity: 0 !important;
        }
        </style>""",
        unsafe_allow_html=True
    )
    components.html(final_html, height=680, scrolling=False)


def _section_survey():
    # ── 0. خيارات القياس والحصر الهندسي ──
    len_opts = [
        "📏 الطول الصافي الخالص بين أوجه الأعمدة (خصم تداخل الأعمدة) [الكود المصري ECP]",
        "📐 طول المحور كاملاً من السنتر للسنتر (Axis-to-Axis)"
    ]
    cur_len_str = st.session_state.get("m15_masonry_len_str", len_opts[0])
    if cur_len_str not in len_opts:
        cur_len_str = len_opts[0]

    chosen_len_str = st.radio(
        "📐 طريقة قياس أطوال حوائط المباني في الحصر الهندسي:",
        options=len_opts,
        index=len_opts.index(cur_len_str),
        key="m15_len_mode_radio",
        horizontal=True,
        help="طبقاً لأصول الحصر بالكود المصري، حوائط المباني تُقاس من وش العمود لوش العمود الصافي بعد خصم مسقط الأعمدة الخرسانية."
    )
    len_mode = "clear" if "الصافي" in chosen_len_str else "axis"
    st.session_state["m15_masonry_len_mode"] = len_mode
    st.session_state["m15_masonry_len_str"] = chosen_len_str

    res = _compute_survey(len_mode=len_mode)
    r12 = res["rows_12"]
    r25 = res["rows_25"]

    # 1. إحصائيات طوب 12 سم (بالمسطح م2)
    g12 = sum(r.get("المساحة الإجمالية (م2)", 0.0) for r in r12)
    op12 = sum(r.get("مساحة الفتحات (م2)", 0.0) for r in r12)
    n12 = sum(r.get("المساحة الصافية (م2)", 0.0) for r in r12)

    # 2. إحصائيات طوب 25 سم (بالمكعب م3)
    g25 = sum(r.get("المساحة الإجمالية (م2)", 0.0) for r in r25)
    op25 = sum(r.get("مساحة الفتحات (م2)", 0.0) for r in r25)
    n25 = sum(r.get("المساحة الصافية (م2)", 0.0) for r in r25)
    v25 = sum(r.get("حجم الطوب (م3)", 0.0) for r in r25)

    total_openings_masonry = op12 + op25

    # 3. حسابات المونة ومواد البناء للمباني طبقاً للكود المصري ECP:
    # - مباني 12 سم (نصف طوبة): 0.025 م3 رمل / م2 مسطح
    # - مباني 25 سم (طوبة كاملة): 0.200 م3 رمل / م3 مكعب
    # - نسبة هالك تشغيل طبيعي: 5% (× 1.05)
    sand_12 = n12 * 0.025
    sand_25 = v25 * 0.200
    sand_net_masonry = sand_12 + sand_25
    sand_total_masonry = sand_net_masonry * 1.05

    # محتوى الأسمنت في مونة المباني: 350 كجم أسمنت لكل 1 م3 رمل (7 شكاير / م3)
    cement_masonry_kg = sand_total_masonry * 350.0
    cement_masonry_tons = cement_masonry_kg / 1000.0
    cement_masonry_bags = math.ceil(cement_masonry_kg / 50.0) if cement_masonry_kg > 0 else 0

    # ── حساب عدد الطوب بناءً على النوع والمقاس المحدد من المستخدم (BOQ) ──
    brick_size_v = st.session_state.get("m15_brick_size", "25×12×6")
    mortar_v = float(st.session_state.get("m15_mortar_thickness_cm", 1.0))
    if brick_size_v == _CUSTOM_SIZE_LABEL:
        b_l = float(st.session_state.get("m15_brick_custom_l", 25.0))
        b_w = float(st.session_state.get("m15_brick_custom_w", 12.0))
        b_h = float(st.session_state.get("m15_brick_custom_h", 6.0))
    else:
        b_l, b_w, b_h = _parse_brick_size(brick_size_v)

    bricks_12 = _compute_brick_qty(n12, _WALL_THIN, b_l, b_w, b_h, mortar_v)
    bricks_25 = _compute_brick_qty(n25, _WALL_THICK, b_l, b_w, b_h, mortar_v)
    bricks_total = bricks_12 + bricks_25
    brick_type_display = st.session_state.get("m15_brick_type", "")
    brick_size_display = f"{b_l:.0f}×{b_w:.0f}×{b_h:.0f} سم" if brick_size_v == _CUSTOM_SIZE_LABEL else f"{brick_size_v} سم"

    # ── 4. حسابات حصر المحارة التوريدي والتنفيذي ──
    p_res = _compute_plaster_survey()
    p_net_m2 = p_res["tot_net"]
    p_sand_m3 = p_res["tot_sand"]
    p_cement_tons = p_res["tot_cement_tons"]
    p_cement_bags = p_res["tot_cement_bags"]

    # ── 5. إجماليات الخامات المشتركة لكامل المشروع (مباني + محارة) ──
    total_sand_all = sand_total_masonry + p_sand_m3
    total_cement_tons_all = cement_masonry_tons + p_cement_tons
    total_cement_bags_all = cement_masonry_bags + p_cement_bags

    # بطاقة الملخص التنفيذي للحصر الهندسي
    len_badge = "طول صافي بين الأعمدة" if len_mode == "clear" else "طول المحور كاملاً"
    st.markdown(
        f"""<div style='background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1.5px solid #334155; border-radius: 12px; padding: 18px 22px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.25);' dir='rtl'>
        <div style='display:flex; align-items:center; justify-content:space-between; border-bottom: 1px solid #334155; padding-bottom: 12px; margin-bottom: 14px; flex-wrap:wrap; gap:8px;'>
            <div style='font-weight:bold; font-size:1.05rem; color:#f8fafc; display:flex; align-items:center; gap:8px;'>
                <span>📋</span>
                <span>الملخص الهندسي الموحد لحصر أعمال المباني والمحارة والخامات (الكود المصري ECP)</span>
            </div>
            <span style='background: linear-gradient(135deg, #1e40af, #2563eb); color:#ffffff; font-size:0.80rem; font-weight:bold; padding:4px 12px; border-radius:20px; border:1px solid #60a5fa;'>
                {len_badge}
            </span>
        </div>
        <div style='display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:12px;'>
            <div style='background: rgba(249, 115, 22, 0.12); border: 1px solid rgba(249, 115, 22, 0.35); border-right: 4px solid #f97316; padding: 12px 14px; border-radius: 8px;'>
                <div style='font-size:0.84rem; color:#fdba74; font-weight:bold;'>🧱 1️⃣ حصر مباني طوب 12 سم:</div>
                <div style='font-size:1.30rem; font-weight:bold; color:#ffedd5; margin-top:4px;'>{n12:.2f} <span style='font-size:0.85rem; font-weight:normal; color:#fed7aa;'>م² مسطح صافي</span></div>
                <div style='font-size:0.75rem; color:#94a3b8; margin-top:3px;'>إجمالي شامل الفتحات: {g12:.2f} م² | فتحات: {op12:.2f} م²</div>
            </div>
            <div style='background: rgba(236, 72, 153, 0.12); border: 1px solid rgba(236, 72, 153, 0.35); border-right: 4px solid #ec4899; padding: 12px 14px; border-radius: 8px;'>
                <div style='font-size:0.84rem; color:#f472b6; font-weight:bold;'>🏗️ 2️⃣ حصر مباني طوب 25 سم:</div>
                <div style='font-size:1.30rem; font-weight:bold; color:#fdf2f8; margin-top:4px;'>{v25:.2f} <span style='font-size:0.85rem; font-weight:normal; color:#fbcfe8;'>م³ مكعب صافي</span></div>
                <div style='font-size:0.75rem; color:#94a3b8; margin-top:3px;'>صافي المسطح: {n25:.2f} م² | فتحات: {op25:.2f} م²</div>
            </div>
            <div style='background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-right: 4px solid #10b981; padding: 12px 14px; border-radius: 8px;'>
                <div style='font-size:0.84rem; color:#6ee7b7; font-weight:bold;'>🎨 3️⃣ صافي مسطح أعمال المحارة:</div>
                <div style='font-size:1.30rem; font-weight:bold; color:#ecfdf5; margin-top:4px;'>{p_net_m2:.2f} <span style='font-size:0.85rem; font-weight:normal; color:#a7f3d0;'>م² مسطح معتمد</span></div>
                <div style='font-size:0.75rem; color:#94a3b8; margin-top:3px;'>إجمالي الأوجه: {p_res['tot_gross']:.2f} م² | خصم الفتحات: {p_res['tot_ded']:.2f} م²</div>
            </div>
            <div style='background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.40); border-right: 4px solid #3b82f6; padding: 12px 14px; border-radius: 8px;'>
                <div style='font-size:0.84rem; color:#93c5fd; font-weight:bold;'>🧱 4️⃣ إجمالي عدد الطوب المطلوب:</div>
                <div style='font-size:1.30rem; font-weight:bold; color:#eff6ff; margin-top:4px;'>{bricks_total:,} <span style='font-size:0.85rem; font-weight:normal; color:#bfdbfe;'>وحدة طوب</span></div>
                <div style='font-size:0.75rem; color:#94a3b8; margin-top:3px;'>{brick_type_display} | {brick_size_display} | مونة {mortar_v}سم</div>
            </div>
        </div>
        <div style='margin-top:14px; background: rgba(15, 23, 42, 0.80); border: 1px solid #334155; border-radius: 8px; padding: 12px 16px; display:flex; align-items:center; justify-content:space-around; flex-wrap:wrap; gap:16px;'>
            <div style='display:flex; align-items:center; gap:10px;'>
                <span style='font-size:1.6rem;'>🏜️</span>
                <div>
                    <div style='font-size:0.80rem; color:#cbd5e1; font-weight:bold;'>5️⃣ إجمالي الرمل الكلي (مباني {sand_total_masonry:.2f} + محارة {p_sand_m3:.2f}):</div>
                    <div style='font-size:1.25rem; font-weight:bold; color:#fbbf24;'>{total_sand_all:.2f} <span style='font-size:0.85rem; color:#fde68a;'>م³ شامل 5% هالك</span></div>
                </div>
            </div>
            <div style='height:36px; width:1px; background-color:#334155;'></div>
            <div style='display:flex; align-items:center; gap:10px;'>
                <span style='font-size:1.6rem;'>🏗️</span>
                <div>
                    <div style='font-size:0.80rem; color:#cbd5e1; font-weight:bold;'>6️⃣ إجمالي الأسمنت الكلي (مباني {cement_masonry_tons:.2f}ط + محارة {p_cement_tons:.2f}ط):</div>
                    <div style='font-size:1.25rem; font-weight:bold; color:#38bdf8;'>{total_cement_tons_all:.2f} <span style='font-size:0.85rem; color:#bae6fd;'>طن</span> &nbsp;<span style='font-size:0.85rem; color:#e2e8f0; font-weight:normal;'>({total_cement_bags_all} شكارة 50 كجم)</span></div>
                </div>
            </div>
        </div>
    </div>""",
        unsafe_allow_html=True
    )

    # ── قسم مدخلات الأسعار وتكاليف أعمال المباني والمحارة ──
    header_pricing_html = """<div style='background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1.5px solid #3b82f6; border-radius: 12px; padding: 14px 20px; margin-top: 14px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.25);' dir='rtl'>
<div style='display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;'>
<div style='font-weight:bold; font-size:1.02rem; color:#60a5fa; display:flex; align-items:center; gap:8px;'>
<span>💵</span>
<span>مدخلات أسعار خامات ومصنعيات المباني والمحارة (تسعير بنود المقايسة)</span>
</div>
<span style='background: rgba(59, 130, 246, 0.2); color:#93c5fd; font-size:0.78rem; font-weight:bold; padding:4px 12px; border-radius:20px; border:1px solid #3b82f6;'>
تسعير فوري متكامل
</span>
</div>
<div style='color:#cbd5e1; font-size:0.83rem; margin-top: 6px;'>
أدخل أسعار التوريد والتشوين والمصنعيات لحساب تكلفة أعمال المباني والمحارة بدقة وتفصيل:
</div>
</div>"""
    st.html(header_pricing_html) if hasattr(st, "html") else st.markdown(header_pricing_html, unsafe_allow_html=True)

    col_pr1, col_pr2, col_pr3, col_pr4 = st.columns(4)
    with col_pr1:
        p_brick_in = st.number_input(
            "🧱 سعر الألف طوبة توريد وتشوين (ج.م / 1000)",
            min_value=0.0,
            max_value=1000000.0,
            value=float(st.session_state.get("m15_price_brick_per_thousand", 2500.0)),
            step=50.0,
            help="سعر الألف طوبة شاملاً التوريد والتشوين والمصنعية بالموقع",
            key="m15_price_brick_per_thousand",
            on_change=save_settings
        )
    with col_pr2:
        p_sand_in = st.number_input(
            "🏜️ سعر متر الرمل بالتشوين (ج.م / م³)",
            min_value=0.0,
            max_value=100000.0,
            value=float(st.session_state.get("m15_price_sand_per_m3", 200.0)),
            step=10.0,
            help="سعر المتر المكعب للرمل شاملاً التشوين في الموقع لكافة الأعمال",
            key="m15_price_sand_per_m3",
            on_change=save_settings
        )
    with col_pr3:
        p_cement_in = st.number_input(
            "🏗️ سعر طن الأسمنت (ج.م / طن)",
            min_value=0.0,
            max_value=100000.0,
            value=float(st.session_state.get("m15_price_cement_per_ton", 4000.0)),
            step=50.0,
            help="سعر طن الأسمنت البورتلاندي العادي شاملاً التشوين",
            key="m15_price_cement_per_ton",
            on_change=save_settings
        )
    with col_pr4:
        p_plaster_labor_in = st.number_input(
            "🎨 سعر مصنعية بياض المحارة (ج.م / م²)",
            min_value=0.0,
            max_value=10000.0,
            value=float(st.session_state.get("m15_price_plaster_labor_per_m2", 70.0)),
            step=5.0,
            help="أجرة مصنعية المبيض للمتر المسطح (طرطشة وبؤج وأوتار ومحارة)",
            key="m15_price_plaster_labor_per_m2",
            on_change=save_settings
        )

    # ── حسابات تكاليف أعمال المباني ──
    brick_thousands = round(bricks_total / 1000.0, 3)
    cost_brick = round(brick_thousands * p_brick_in, 2)
    sand_masonry_qty = round(sand_total_masonry, 2)
    cost_sand_masonry = round(sand_masonry_qty * p_sand_in, 2)
    cement_masonry_qty = round(cement_masonry_tons, 3)
    cost_cement_masonry = round(cement_masonry_qty * p_cement_in, 2)
    cost_masonry_total = round(cost_brick + cost_sand_masonry + cost_cement_masonry, 2)

    # ── حسابات تكاليف أعمال المحارة ──
    plaster_area_qty = round(p_net_m2, 2)
    cost_plaster_labor = round(plaster_area_qty * p_plaster_labor_in, 2)
    sand_plaster_qty = round(p_sand_m3, 2)
    cost_sand_plaster = round(sand_plaster_qty * p_sand_in, 2)
    cement_plaster_qty = round(p_cement_tons, 3)
    cost_cement_plaster = round(cement_plaster_qty * p_cement_in, 2)
    cost_plaster_total = round(cost_plaster_labor + cost_sand_plaster + cost_cement_plaster, 2)

    # ── التكلفة الإجمالية العامة للمشروع (المباني + المحارة) ──
    grand_total_cost = round(cost_masonry_total + cost_plaster_total, 2)
    cost_sand_all = round((sand_masonry_qty + sand_plaster_qty) * p_sand_in, 2)
    cost_cement_all = round((cement_masonry_qty + cement_plaster_qty) * p_cement_in, 2)

    # ── بانيل مخرجات وتكاليف أعمال المباني والمحارة ──
    panel_cost_html = f"""<div style='background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); border: 2px solid #6366f1; border-radius: 12px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 6px 20px rgba(99, 102, 241, 0.25);' dir='rtl'>
<div style='display:flex; align-items:center; justify-content:space-between; border-bottom: 1px solid rgba(99, 102, 241, 0.4); padding-bottom: 12px; margin-bottom: 14px; flex-wrap:wrap; gap:8px;'>
<div style='font-weight:900; font-size:1.10rem; color:#ffffff; display:flex; align-items:center; gap:8px;'>
<span>📊</span>
<span>بانيل مخرجات وتكاليف أعمال المباني والمحارة (التسعير التقديري الشامل)</span>
</div>
<span style='background: linear-gradient(135deg, #4f46e5, #7c3aed); color:#ffffff; font-size:0.80rem; font-weight:bold; padding:4px 14px; border-radius:20px; border:1px solid #a5b4fc; box-shadow: 0 2px 8px rgba(79, 70, 229, 0.4);'>
نتائج التسعير النهائي
</span>
</div>
<div style='display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:12px; margin-bottom: 14px;'>
<div style='background: rgba(30, 41, 59, 0.85); border: 1.5px solid rgba(249, 115, 22, 0.5); border-right: 5px solid #f97316; padding: 14px 16px; border-radius: 10px;'>
<div style='display:flex; align-items:center; justify-content:space-between;'>
<span style='font-size:0.85rem; color:#fdba74; font-weight:bold;'>🧱 1️⃣ إجمالي تكلفة المباني:</span>
<span style='font-size:0.75rem; color:#94a3b8; background:rgba(249,115,22,0.15); padding:2px 8px; border-radius:6px;'>طوب + مونة</span>
</div>
<div style='font-size:1.35rem; font-weight:900; color:#ffedd5; margin-top:6px;'>
{cost_masonry_total:,.2f} <span style='font-size:0.85rem; font-weight:normal; color:#fed7aa;'>ج.م</span>
</div>
<div style='font-size:0.75rem; color:#cbd5e1; margin-top:4px;'>
طوب ({cost_brick:,.0f}) + رمل ({cost_sand_masonry:,.0f}) + أسمنت ({cost_cement_masonry:,.0f})
</div>
</div>
<div style='background: rgba(30, 41, 59, 0.85); border: 1.5px solid rgba(14, 165, 233, 0.5); border-right: 5px solid #0ea5e9; padding: 14px 16px; border-radius: 10px;'>
<div style='display:flex; align-items:center; justify-content:space-between;'>
<span style='font-size:0.85rem; color:#7dd3fc; font-weight:bold;'>🎨 2️⃣ إجمالي تكلفة المحارة:</span>
<span style='font-size:0.75rem; color:#94a3b8; background:rgba(14,165,233,0.15); padding:2px 8px; border-radius:6px;'>مصنعية + خامات</span>
</div>
<div style='font-size:1.35rem; font-weight:900; color:#e0f2fe; margin-top:6px;'>
{cost_plaster_total:,.2f} <span style='font-size:0.85rem; font-weight:normal; color:#bae6fd;'>ج.م</span>
</div>
<div style='font-size:0.75rem; color:#cbd5e1; margin-top:4px;'>
مصنعية ({cost_plaster_labor:,.0f}) + رمل ({cost_sand_plaster:,.0f}) + أسمنت ({cost_cement_plaster:,.0f})
</div>
</div>
<div style='background: rgba(30, 41, 59, 0.85); border: 1.5px solid rgba(234, 179, 8, 0.5); border-right: 5px solid #eab308; padding: 14px 16px; border-radius: 10px;'>
<div style='display:flex; align-items:center; justify-content:space-between;'>
<span style='font-size:0.85rem; color:#fde047; font-weight:bold;'>📦 3️⃣ إجمالي الخامات المشتركة:</span>
<span style='font-size:0.75rem; color:#94a3b8; background:rgba(234,179,8,0.15); padding:2px 8px; border-radius:6px;'>رمل + أسمنت</span>
</div>
<div style='font-size:1.35rem; font-weight:900; color:#fef08a; margin-top:6px;'>
{(cost_sand_all + cost_cement_all):,.2f} <span style='font-size:0.85rem; font-weight:normal; color:#fef9c3;'>ج.م</span>
</div>
<div style='font-size:0.75rem; color:#cbd5e1; margin-top:4px;'>
رمل كلي ({cost_sand_all:,.0f} ج.م) + أسمنت كلي ({cost_cement_all:,.0f} ج.م)
</div>
</div>
<div style='background: linear-gradient(135deg, rgba(16, 185, 129, 0.25), rgba(6, 78, 59, 0.5)); border: 2px solid #10b981; border-right: 6px solid #10b981; padding: 14px 16px; border-radius: 10px; box-shadow: 0 4px 14px rgba(16,185,129,0.3);'>
<div style='display:flex; align-items:center; justify-content:space-between;'>
<span style='font-size:0.88rem; color:#6ee7b7; font-weight:900;'>💰 4️⃣ الإجمالي العام الشامل:</span>
<span style='font-size:0.75rem; color:#ecfdf5; background:#059669; padding:2px 8px; border-radius:6px; font-weight:bold;'>المشروع كاملاً</span>
</div>
<div style='font-size:1.55rem; font-weight:900; color:#a7f3d0; margin-top:6px;'>
{grand_total_cost:,.2f} <span style='font-size:0.90rem; font-weight:bold; color:#6ee7b7;'>ج.م</span>
</div>
<div style='font-size:0.75rem; color:#e2e8f0; margin-top:4px;'>
مباني ({cost_masonry_total:,.0f}) + محارة ({cost_plaster_total:,.0f})
</div>
</div>
</div>
<div style='overflow-x:auto; margin-top:10px;'>
<table style='width:100%; border-collapse:collapse; font-size:0.85rem; text-align:center;' dir='rtl'>
<thead>
<tr style='background:rgba(15,23,42,0.9); border-bottom:2px solid #475569;'>
<th style='padding:9px 10px; color:#f8fafc; text-align:right;'>بند التكلفة والمقايسة</th>
<th style='padding:9px 10px; color:#cbd5e1;'>الكمية المحصورة</th>
<th style='padding:9px 10px; color:#cbd5e1;'>الوحدة</th>
<th style='padding:9px 10px; color:#fbbf24;'>سعر الوحدة (ج.م)</th>
<th style='padding:9px 10px; color:#93c5fd; text-align:right;'>معادلة الحساب التفصيلية</th>
<th style='padding:9px 10px; color:#4ade80;'>إجمالي التكلفة (ج.م)</th>
</tr>
</thead>
<tbody>
<tr style='background:rgba(30,41,59,0.5); border-bottom:1px solid #334155;'>
<td style='padding:8px 10px; text-align:right; font-weight:bold; color:#fdba74;'>🧱 1. توريد وتشوين الطوب</td>
<td style='padding:8px 10px; color:#f1f5f9; font-weight:bold;'>{brick_thousands:.3f}</td>
<td style='padding:8px 10px; color:#cbd5e1;'>ألف طوبة ({bricks_total:,} طوبة)</td>
<td style='padding:8px 10px; color:#fbbf24; font-weight:bold;'>{p_brick_in:,.2f}</td>
<td style='padding:8px 10px; text-align:right; color:#cbd5e1;'>{brick_thousands:.3f} ألف × {p_brick_in:,.2f} ج.م</td>
<td style='padding:8px 10px; font-weight:bold; color:#ffedd5;'>{cost_brick:,.2f}</td>
</tr>
<tr style='background:rgba(30,41,59,0.3); border-bottom:1px solid #334155;'>
<td style='padding:8px 10px; text-align:right; font-weight:bold; color:#fde047;'>🏜️ 2. رمل مونة المباني (شامل 5% هالك)</td>
<td style='padding:8px 10px; color:#f1f5f9; font-weight:bold;'>{sand_masonry_qty:.2f}</td>
<td style='padding:8px 10px; color:#cbd5e1;'>متر مكعب (م³)</td>
<td style='padding:8px 10px; color:#fbbf24; font-weight:bold;'>{p_sand_in:,.2f}</td>
<td style='padding:8px 10px; text-align:right; color:#cbd5e1;'>{sand_masonry_qty:.2f} م³ × {p_sand_in:,.2f} ج.م</td>
<td style='padding:8px 10px; font-weight:bold; color:#fef08a;'>{cost_sand_masonry:,.2f}</td>
</tr>
<tr style='background:rgba(30,41,59,0.5); border-bottom:1px solid #334155;'>
<td style='padding:8px 10px; text-align:right; font-weight:bold; color:#7dd3fc;'>🏗️ 3. أسمنت مونة المباني (350 كجم/م³)</td>
<td style='padding:8px 10px; color:#f1f5f9; font-weight:bold;'>{cement_masonry_qty:.3f}</td>
<td style='padding:8px 10px; color:#cbd5e1;'>طن ({cement_masonry_bags} شكارة)</td>
<td style='padding:8px 10px; color:#fbbf24; font-weight:bold;'>{p_cement_in:,.2f}</td>
<td style='padding:8px 10px; text-align:right; color:#cbd5e1;'>{cement_masonry_qty:.3f} طن × {p_cement_in:,.2f} ج.م</td>
<td style='padding:8px 10px; font-weight:bold; color:#e0f2fe;'>{cost_cement_masonry:,.2f}</td>
</tr>
<tr style='background:rgba(249,115,22,0.18); font-weight:bold; border-bottom:2px solid #f97316;'>
<td style='padding:9px 10px; text-align:right; color:#fdba74;'>⬅️ إجمالي بند أعمال المباني</td>
<td style='padding:9px 10px; color:#e2e8f0;'>—</td>
<td style='padding:9px 10px; color:#e2e8f0;'>—</td>
<td style='padding:9px 10px; color:#fde047;'>—</td>
<td style='padding:9px 10px; text-align:right; color:#fed7aa;'>مجموع (الطوب + رمل المباني + أسمنت المباني)</td>
<td style='padding:9px 10px; color:#ffedd5; font-size:1.02rem;'>{cost_masonry_total:,.2f} ج.م</td>
</tr>
<tr style='background:rgba(30,41,59,0.5); border-bottom:1px solid #334155;'>
<td style='padding:8px 10px; text-align:right; font-weight:bold; color:#38bdf8;'>🎨 4. مصنعية بياض المحارة (أجرة المبيض)</td>
<td style='padding:8px 10px; color:#f1f5f9; font-weight:bold;'>{plaster_area_qty:.2f}</td>
<td style='padding:8px 10px; color:#cbd5e1;'>متر مسطح (م²)</td>
<td style='padding:8px 10px; color:#fbbf24; font-weight:bold;'>{p_plaster_labor_in:,.2f}</td>
<td style='padding:8px 10px; text-align:right; color:#cbd5e1;'>{plaster_area_qty:.2f} م² × {p_plaster_labor_in:,.2f} ج.م</td>
<td style='padding:8px 10px; font-weight:bold; color:#bae6fd;'>{cost_plaster_labor:,.2f}</td>
</tr>
<tr style='background:rgba(30,41,59,0.3); border-bottom:1px solid #334155;'>
<td style='padding:8px 10px; text-align:right; font-weight:bold; color:#fde047;'>🏜️ 5. رمل بياض المحارة (شامل 5% هالك)</td>
<td style='padding:8px 10px; color:#f1f5f9; font-weight:bold;'>{sand_plaster_qty:.2f}</td>
<td style='padding:8px 10px; color:#cbd5e1;'>متر مكعب (م³)</td>
<td style='padding:8px 10px; color:#fbbf24; font-weight:bold;'>{p_sand_in:,.2f}</td>
<td style='padding:8px 10px; text-align:right; color:#cbd5e1;'>{sand_plaster_qty:.2f} م³ × {p_sand_in:,.2f} ج.م</td>
<td style='padding:8px 10px; font-weight:bold; color:#fef08a;'>{cost_sand_plaster:,.2f}</td>
</tr>
<tr style='background:rgba(30,41,59,0.5); border-bottom:1px solid #334155;'>
<td style='padding:8px 10px; text-align:right; font-weight:bold; color:#7dd3fc;'>🏗️ 6. أسمنت بياض المحارة (350 كجم/م³)</td>
<td style='padding:8px 10px; color:#f1f5f9; font-weight:bold;'>{cement_plaster_qty:.3f}</td>
<td style='padding:8px 10px; color:#cbd5e1;'>طن ({p_cement_bags} شكارة)</td>
<td style='padding:8px 10px; color:#fbbf24; font-weight:bold;'>{p_cement_in:,.2f}</td>
<td style='padding:8px 10px; text-align:right; color:#cbd5e1;'>{cement_plaster_qty:.3f} طن × {p_cement_in:,.2f} ج.م</td>
<td style='padding:8px 10px; font-weight:bold; color:#e0f2fe;'>{cost_cement_plaster:,.2f}</td>
</tr>
<tr style='background:rgba(14,165,233,0.18); font-weight:bold; border-bottom:2px solid #0ea5e9;'>
<td style='padding:9px 10px; text-align:right; color:#7dd3fc;'>⬅️ إجمالي بند أعمال المحارة</td>
<td style='padding:9px 10px; color:#e2e8f0;'>—</td>
<td style='padding:9px 10px; color:#e2e8f0;'>—</td>
<td style='padding:9px 10px; color:#fde047;'>—</td>
<td style='padding:9px 10px; text-align:right; color:#bae6fd;'>مجموع (مصنعية المحارة + رمل المحارة + أسمنت المحارة)</td>
<td style='padding:9px 10px; color:#e0f2fe; font-size:1.02rem;'>{cost_plaster_total:,.2f} ج.م</td>
</tr>
<tr style='background:linear-gradient(90deg, #1e3a8a, #065f46); font-weight:900;'>
<td style='padding:12px 10px; text-align:right; color:#ffffff; font-size:0.95rem;'>🏆 الإجمالي العام الشامل للمشروع (المباني + المحارة)</td>
<td style='padding:12px 10px; color:#e2e8f0;'>—</td>
<td style='padding:12px 10px; color:#e2e8f0;'>—</td>
<td style='padding:12px 10px; color:#fde047;'>—</td>
<td style='padding:12px 10px; text-align:right; color:#bae6fd;'>إجمالي أعمال المباني ({cost_masonry_total:,.2f}) + إجمالي أعمال المحارة ({cost_plaster_total:,.2f})</td>
<td style='padding:12px 10px; color:#a7f3d0; font-size:1.20rem; font-weight:900;'>{grand_total_cost:,.2f} ج.م</td>
</tr>
</tbody>
</table>
</div>
</div>"""
    st.html(panel_cost_html) if hasattr(st, "html") else st.markdown(panel_cost_html, unsafe_allow_html=True)

    # 6. رسالة توضيحية لطريقة حساب كمية الرمل والأسمنت طبقاً للكود المصري
    with st.expander("💡 6️⃣ رسالة توضيحية: طريقة حساب كميات الرمل والأسمنت والمحارة طبقاً للكود المصري وأصول التنفيذ", expanded=False):
        st.markdown(
            f"""<div dir='rtl' style='direction: rtl !important; text-align: right !important; line-height: 1.85; font-size: 0.90rem; color: #f1f5f9; background: rgba(15, 23, 42, 0.6); border: 1px solid #334155; border-radius: 8px; padding: 14px 18px;'>
            <p style='direction: rtl !important; text-align: right !important; font-weight: bold; color: #38bdf8; margin-bottom: 12px; font-size: 0.92rem;'>
                استندت الحسابات التقديرية لكميات المونة ومواد البناء وأعمال المحارة إلى المواصفات الفنية بالكود المصري للبناء وأصول الصناعة:
            </p>
            <ol style='direction: rtl !important; text-align: right !important; padding-right: 25px; padding-left: 0; margin: 0 0 12px 0;'>
                <li style='direction: rtl !important; text-align: right !important; margin-bottom: 12px; color: #e2e8f0;'>
                    <b style='color: #fdba74;'>أعمال مباني طوب سمك 12 سم (نصف طوبة):</b>
                    <div style='padding-right: 12px; margin-top: 4px; color: #cbd5e1; direction: rtl !important; text-align: right !important;'>
                        • تُحصر هندسياً بالمتر المسطح (م²). الطول الصافي يُقاس من وش العمود لوش العمود الخالص.<br>
                        • المساحة الصافية = المساحة الإجمالية للمسقط مطروحاً منها مساحة فتحات الأبواب والشبابيك.<br>
                        • معدل استهلاك الرمل لمونة البناء = <b style='color: #fde68a;'>0.025 م³ رمل</b> لكل 1 م² مسطح مباني.<br>
                        • حساب عدد الطوب = يُحسب بدقة هندسية لكل حائط استناداً إلى المقاس المختار (<b style='color: #60a5fa;'>{brick_type_display} | {brick_size_display}</b>) وفاصل مونة <b style='color: #a78bfa;'>{mortar_v} سم</b>.
                    </div>
                </li>
                <li style='direction: rtl !important; text-align: right !important; margin-bottom: 12px; color: #e2e8f0;'>
                    <b style='color: #f472b6;'>أعمال مباني طوب سمك 25 سم (طوبة كاملة):</b>
                    <div style='padding-right: 12px; margin-top: 4px; color: #cbd5e1; direction: rtl !important; text-align: right !important;'>
                        • تُحصر هندسياً بالمتر المكعب (م³ = المساحة الصافية × 0.25 م).<br>
                        • معدل استهلاك الرمل لمونة البناء = <b style='color: #fde68a;'>0.200 م³ رمل</b> لكل 1 م³ مكعب مباني.<br>
                        • حساب عدد الطوب = يُحسب بدقة هندسية استناداً إلى المقاس المختار وفاصل المونة.
                    </div>
                </li>
                <li style='direction: rtl !important; text-align: right !important; margin-bottom: 12px; color: #e2e8f0;'>
                    <b style='color: #38bdf8;'>أعمال بياض المحارة (طبقاً للكود المصري ECP):</b>
                    <div style='padding-right: 12px; margin-top: 4px; color: #cbd5e1; direction: rtl !important; text-align: right !important;'>
                        • سُمك البياض المتوسط 2 سم شاملاً الطرطشة العمومية وبؤج وأوتار والملء والتخشين.<br>
                        • معدل استهلاك الرمل: <b style='color: #fde68a;'>1 م³ رمل لكل 42 م² مسطح صافي</b> (شامل 5% نسبة هالك تشغيل).<br>
                        • محتوى الأسمنت القياسي للبياض: <b style='color: #bae6fd;'>350 كجم أسمنت لكل 1 م³ رمل</b> (7 شكاير أسمنت زنة 50 كجم).<br>
                        • قواعد خصم الفتحات: الفتحات حتى 4.00 م² لا تُخصم في الكود المصري وتعتبر مقابلاً لسوك وأكتاف الفتحات.
                    </div>
                </li>
                <li style='direction: rtl !important; text-align: right !important; margin-bottom: 6px; color: #e2e8f0;'>
                    <b style='color: #4ade80;'>معامل الهالك والتشغيل (Waste Allowance):</b>
                    <div style='padding-right: 12px; margin-top: 4px; color: #cbd5e1; direction: rtl !important; text-align: right !important;'>
                        • تم احتساب نسبة هالك قدرها <b style='color: #86efac;'>5%</b> مضافة إلى كميات الرمل والأسمنت لتعويض الفواقد الطبيعية أثناء التشوين والخلط والتشغيل في الموقع.
                    </div>
                </li>
            </ol>
        </div>""",
            unsafe_allow_html=True
        )

    t12, t25, tpl, tmat = st.tabs(["🧱 طوب 12 سم", "🏗️ طوب 25 سم", "🪣 حصر المحارة", "📦 مقايسة الخامات والمونة"])

    def _rt(rows, lbl):
        if not rows:
            st.info(f"لا توجد حوائط {lbl} نشطة.")
            return
        tot = _totals_row(rows)
        df = pd.DataFrame(rows + [tot])
        def _st2(row):
            if row["الحائط"] == "✅ الإجمالي":
                return ["background-color:#1a3a5c;color:white;font-weight:bold"] * len(row)
            return [""] * len(row)
        styled_df = df.style.apply(_st2, axis=1).format(lambda v: f"{v:.2f}" if isinstance(v, float) else v)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        cb = io.StringIO()
        df.to_csv(cb, index=False, encoding="utf-8-sig")
        st.download_button(
            f"⬇️ تحميل {lbl} CSV",
            data=cb.getvalue().encode("utf-8-sig"),
            file_name=f"brick_{lbl.replace(' ', '_')}.csv",
            mime="text/csv",
            key=f"m15_dl_{lbl}"
        )

    with t12:
        _rt(r12, "12 سم")

    with t25:
        _rt(r25, "25 سم")

    with tpl:
        st.markdown("<b style='font-size:1.05rem;color:#ffffff;'>🪣 حصر كميات ومواد أعمال البياض (المحارة)</b>", unsafe_allow_html=True)
        p_rows = p_res["rows"]
        if not p_rows:
            st.info("💡 لم يتم تفعيل أوجه المحارة لأي حائط بعد. يرجى التوجه إلى قسم '7️⃣ تحديد حوائط المحارة' بالقائمة الجانبية لتحديد الأوجه المطلوبة.")
            ar = r12 + r25
            if ar:
                tn = sum(r.get("المساحة الصافية (م2)", 0.0) for r in ar)
                st.caption(f"ℹ️ كتقدير استرشادي: إجمالي المسطح الصافي لكافة الحوائط = {tn:.2f} م² (محارة كاملة للوجهين = {tn * 2:.2f} م²).")
        else:
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("إجمالي مسطح المحارة", f"{p_res['tot_gross']:.2f} م²")
            m2.metric("الفتحات المخصومة", f"{p_res['tot_ded']:.2f} م²")
            m3.metric("صافي مسطح المحارة", f"{p_res['tot_net']:.2f} م²")
            m4.metric("كمية الرمل المطلوبة", f"{p_res['tot_sand']:.2f} م³")
            m5.metric("الأسمنت المطلوب", f"{p_res['tot_cement_tons']:.2f} طن", f"{p_res['tot_cement_bags']} شكارة")

            display_rows = []
            for r in p_rows:
                display_rows.append({
                    "الحائط": r["الحائط"],
                    "الوجه المحدد": r["الوجه المحدد"],
                    "عدد الأوجه": r["عدد الأوجه"],
                    "الطول (م)": r["الطول (م)"],
                    "الارتفاع (م)": r["الارتفاع (م)"],
                    "إجمالي المسطح (م²)": r["إجمالي مسطح المحارة (m^2)"],
                    "مساحة الفتحات (م²)": r["إجمالي مساحة الفتحات (m^2)"],
                    "الخصم المعتمد (م²)": r["الفتحات المخصومة المعتمدة (m^2)"],
                    "صافي مسطح المحارة (م²)": r["صافي مسطح المحارة النهائي (m^2)"],
                    "كمية الرمل (م³)": r["كمية الرمل المطلوبة (m^3)"],
                    "الأسمنت المطلوب": r["كمية الأسمنت المطلوبة"],
                })

            tot_display = {
                "الحائط": "✅ الإجمالي",
                "الوجه المحدد": f"{sum(r['عدد الأوجه'] for r in p_rows)} وجه",
                "عدد الأوجه": sum(r["عدد الأوجه"] for r in p_rows),
                "الطول (م)": round(sum(r["الطول (م)"] for r in p_rows), 2),
                "الارتفاع (م)": "—",
                "إجمالي المسطح (م²)": round(p_res["tot_gross"], 2),
                "مساحة الفتحات (م²)": round(p_res["tot_op_gross"], 2),
                "الخصم المعتمد (م²)": round(p_res["tot_ded"], 2),
                "صافي مسطح المحارة (م²)": round(p_res["tot_net"], 2),
                "كمية الرمل (م³)": round(p_res["tot_sand"], 2),
                "الأسمنت المطلوب": f"{p_res['tot_cement_tons']:.2f} طن ({p_res['tot_cement_bags']} شكارة)",
            }

            df_p = pd.DataFrame(display_rows + [tot_display])
            def _st_plaster_tab(row):
                if row["الحائط"] == "✅ الإجمالي":
                    return ["background-color:#1e3a8a;color:white;font-weight:bold"] * len(row)
                return [""] * len(row)

            st.dataframe(df_p.style.apply(_st_plaster_tab, axis=1).format(lambda v: f"{v:.2f}" if isinstance(v, float) else v), use_container_width=True, hide_index=True)

            cb_p = io.StringIO()
            df_p.to_csv(cb_p, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ تحميل جدول حصر المحارة CSV",
                data=cb_p.getvalue().encode("utf-8-sig"),
                file_name="plaster_survey_ecp.csv",
                mime="text/csv",
                key="m15_dl_plaster_tab"
            )

            st.markdown(
                """<div style='background-color:rgba(30,58,138,0.25);border:1px solid #3b82f6;border-right:4px solid #3b82f6;border-radius:8px;padding:12px 16px;margin-top:10px;color:#ffffff;font-size:0.87rem;line-height:1.7;' dir='rtl'>
                    <div style='font-weight:bold;margin-bottom:4px;display:flex;align-items:center;gap:6px;'>
                        <span>💡</span>
                        <span>مواصفات حصر المحارة المعتمدة بالكود المصري ECP:</span>
                    </div>
                    <div>
                        تم تقدير كميات المونة بناءً على سمك بياض متوسط <b>2 سم</b> شاملاً الطرطشة وبؤج وأوتار والملء والتخشين، بمعدل استهلاك: <b>1 m³ رمل + 350 كجم أسمنت لكل 42 m² مسطح</b>، مع اعتبار نسبة هالك <b>5%</b>. الفتحات حتى 4 م² لا تخصم طبقاً للكود المصري.
                    </div>
                </div>""",
                unsafe_allow_html=True
            )

    with tmat:
        st.markdown("### 📦 مقايسة خامات المونة ومواد البناء الشاملة (طبقاً للكود المصري)")
        brick_col_name = f"عدد الطوب ({brick_type_display} | {brick_size_display})"
        mat_rows = [
            {
                "بند الأعمال": f"مباني طوب سمك {_WALL_THIN} سم (نصف طوبة)",
                "الوحدة": "م² مسطح",
                "الكمية الصافية": round(n12, 2),
                "رمل صافي (م³)": round(sand_12, 2),
                "رمل مع الهالك 5% (م³)": round(sand_12 * 1.05, 2),
                "أسمنت (طن)": round((sand_12 * 1.05 * 350) / 1000.0, 2),
                "شكاير أسمنت (50كجم)": math.ceil((sand_12 * 1.05 * 350) / 50.0) if n12 > 0 else 0,
                brick_col_name: bricks_12,
            },
            {
                "بند الأعمال": f"مباني طوب سمك {_WALL_THICK} سم (طوبة كاملة)",
                "الوحدة": "م³ مكعب",
                "الكمية الصافية": round(v25, 2),
                "رمل صافي (م³)": round(sand_25, 2),
                "رمل مع الهالك 5% (م³)": round(sand_25 * 1.05, 2),
                "أسمنت (طن)": round((sand_25 * 1.05 * 350) / 1000.0, 2),
                "شكاير أسمنت (50كجم)": math.ceil((sand_25 * 1.05 * 350) / 50.0) if v25 > 0 else 0,
                brick_col_name: bricks_25,
            },
            {
                "بند الأعمال": "⬅️ إجمالي مواد أعمال المباني",
                "الوحدة": "—",
                "الكمية الصافية": "—",
                "رمل صافي (م³)": round(sand_net_masonry, 2),
                "رمل مع الهالك 5% (م³)": round(sand_total_masonry, 2),
                "أسمنت (طن)": round(cement_masonry_tons, 2),
                "شكاير أسمنت (50كجم)": cement_masonry_bags,
                brick_col_name: bricks_total,
            }
        ]

        if p_res["active_walls_count"] > 0:
            mat_rows.append({
                "بند الأعمال": "بياض محارة (أوجه الحوائط المحددة - سمك 2 سم شامل الطرطشة)",
                "الوحدة": "م² مسطح",
                "الكمية الصافية": round(p_net_m2, 2),
                "رمل صافي (م³)": round(p_sand_m3 / 1.05, 2),
                "رمل مع الهالك 5% (م³)": round(p_sand_m3, 2),
                "أسمنت (طن)": round(p_cement_tons, 2),
                "شكاير أسمنت (50كجم)": p_cement_bags,
                brick_col_name: "—",
            })
            mat_rows.append({
                "بند الأعمال": "✅ الإجمالي العام لكامل المشروع (مباني + محارة)",
                "الوحدة": "—",
                "الكمية الصافية": "—",
                "رمل صافي (م³)": round(sand_net_masonry + (p_sand_m3 / 1.05), 2),
                "رمل مع الهالك 5% (م³)": round(total_sand_all, 2),
                "أسمنت (طن)": round(total_cement_tons_all, 2),
                "شكاير أسمنت (50كجم)": total_cement_bags_all,
                brick_col_name: bricks_total,
            })

        df_mat = pd.DataFrame(mat_rows)
        def _st_mat(row):
            if "الإجمالي العام" in str(row["بند الأعمال"]) or "إجمالي مواد" in str(row["بند الأعمال"]):
                return ["background-color:#1e3a8a;color:white;font-weight:bold"] * len(row)
            return [""] * len(row)
        st.dataframe(df_mat.style.apply(_st_mat, axis=1).format(lambda v: f"{v:.2f}" if isinstance(v, float) else v), use_container_width=True, hide_index=True)
        cb_mat = io.StringIO()
        df_mat.to_csv(cb_mat, index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ تحميل مقايسة الخامات CSV",
            data=cb_mat.getvalue().encode("utf-8-sig"),
            file_name="materials_boq_ecp.csv",
            mime="text/csv",
            key="m15_dl_materials"
        )

def _apply_3d_opening_move(payload_str=None):
    """
    مزامنة التعديلات الواردة من العارض ثلاثي الأبعاد 3D (تحريك الأبواب والشبابيك).
    تستقبل payload_str مباشرة من الـ React bridge أو query param 'm15_op_move'.
    وتقوم بتحديث موقع الفتحة في session_state وحفظ الإعدادات دون إعادة تحميل الصفحة.
    """
    val = payload_str
    if not val:
        val = st.session_state.get("m15_3d_sync_input")
    from_query = False
    if not val and "m15_op_move" in st.query_params:
        val = st.query_params["m15_op_move"]
        from_query = True

    if val:
        try:
            data = json.loads(val) if isinstance(val, str) else val
            action = str(data.get("action", "")).lower()
            op_type = str(data.get("type", "")).lower()

            if action == "delete_wall" or op_type == "delete_wall":
                wall_list = data.get("wall")
                if wall_list and len(wall_list) == 4:
                    wk = tuple(int(x) for x in wall_list)
                    removed_walls = st.session_state.get("m15_wall_removed", set())
                    if not isinstance(removed_walls, set):
                        removed_walls = set(removed_walls)
                    removed_walls.add(wk)
                    st.session_state["m15_wall_removed"] = removed_walls

                    # تحديد الحائط المحذوف في سيلكت بوكس القسم 3 لسرعة استعراضه واستعادته
                    all_walls = _get_all_walls()
                    if wk in all_walls:
                        st.session_state["m15_sel_wall"] = all_walls.index(wk) + 1

                    st.session_state.pop("m15_plan_png_b64", None)
                    st.session_state["m15_3d_sync_input"] = ""

                    if from_query:
                        if "m15_op_move" in st.query_params:
                            try:
                                del st.query_params["m15_op_move"]
                            except Exception:
                                pass
                        if "module" in st.query_params:
                            try:
                                del st.query_params["module"]
                            except Exception:
                                pass

                    save_settings()
                    cm = _get_col_name_map()
                    wm = _get_wall_name_map()
                    w_name = data.get("name") or _wall_display_label(wk, cm, wm)
                    st.toast(f"🗑️ تم حذف الحائط ({w_name}) وحفظه في قسم الحوائط لإمكانية استعادته!", icon="🗑️")
                    st.rerun()
                return

            if action == "delete_column" or op_type == "delete_column":
                col_coords = data.get("col")
                if col_coords and len(col_coords) == 2:
                    ci, cj = int(col_coords[0]), int(col_coords[1])
                    _record_col_deletion(ci, cj)
                    removed_cols = st.session_state.get("m15_col_removed", set())
                    if not isinstance(removed_cols, set):
                        removed_cols = set(removed_cols)
                    removed_cols.add((ci, cj))
                    st.session_state["m15_col_removed"] = removed_cols

                    all_cols = _get_all_columns()
                    if (ci, cj) in all_cols:
                        st.session_state["m15_sel_col"] = all_cols.index((ci, cj))

                    st.session_state["m15_col_restore_expander_open"] = True
                    st.session_state.pop("m15_plan_png_b64", None)
                    st.session_state["m15_3d_sync_input"] = ""

                    if from_query:
                        if "m15_op_move" in st.query_params:
                            try:
                                del st.query_params["m15_op_move"]
                            except Exception:
                                pass
                        if "module" in st.query_params:
                            try:
                                del st.query_params["module"]
                            except Exception:
                                pass

                    save_settings()
                    cn = _get_col_name_map()
                    c_name = data.get("name") or cn.get((ci, cj), f"C({ci+1},{cj+1})")
                    st.toast(f"🗑️ تم حذف العمود ({c_name}) وحفظه في قسم استعادة الأعمدة!", icon="🗑️")
                    st.rerun()
                return

            if action == "delete_window" or op_type == "delete_window":
                win_id = data.get("id")
                win_name = data.get("name", "الشباك")
                if win_id:
                    _remove_opening_by_id(win_id, "win")
                    st.session_state.pop("m15_plan_png_b64", None)
                    st.session_state["m15_3d_sync_input"] = ""
                    if from_query:
                        if "m15_op_move" in st.query_params:
                            try: del st.query_params["m15_op_move"]
                            except Exception: pass
                        if "module" in st.query_params:
                            try: del st.query_params["module"]
                            except Exception: pass
                    save_settings()
                    st.toast(f"🗑️ تم حذف الشباك ({win_name}) وحفظه في قسم استعادة الشبابيك والأبواب!", icon="🗑️")
                    st.rerun()
                return

            if action == "delete_door" or op_type == "delete_door":
                door_id = data.get("id")
                door_name = data.get("name", "الباب")
                if door_id:
                    _remove_opening_by_id(door_id, "door")
                    st.session_state.pop("m15_plan_png_b64", None)
                    st.session_state["m15_3d_sync_input"] = ""
                    if from_query:
                        if "m15_op_move" in st.query_params:
                            try: del st.query_params["m15_op_move"]
                            except Exception: pass
                        if "module" in st.query_params:
                            try: del st.query_params["module"]
                            except Exception: pass
                    save_settings()
                    st.toast(f"🗑️ تم حذف الباب ({door_name}) وحفظه في قسم استعادة الشبابيك والأبواب!", icon="🗑️")
                    st.rerun()
                return

            op_id = data.get("id")
            wall_list = data.get("wall")
            new_pos = float(data.get("pos", 0.0))
            if wall_list and len(wall_list) == 4 and op_id:
                wk = tuple(wall_list)
                found = False
                # 1. Primary lookup by op_type
                if op_type in ("win", "window"):
                    win_dict = st.session_state.get("m15_windows", {})
                    for w in win_dict.get(wk, []):
                        if w.get("id") == op_id:
                            w["pos_m"] = round(new_pos, 2)
                            st.session_state[f"m15_edit_wpos_{op_id}"] = round(new_pos, 2)
                            st.session_state[f"m15_mv_w_pos_{op_id}"] = round(new_pos, 2)
                            st.session_state["m15_active_move_dim"] = {
                                "op_id": op_id,
                                "kind": "win",
                                "kind_ar": "الشباك",
                                "name": w.get("name", op_id),
                                "wk": wk,
                                "pos_m": round(new_pos, 2),
                                "w_m": float(w.get("w_m", 1.0)),
                                "ts": time.time(),
                            }
                            found = True
                            break
                elif op_type in ("door", "doors"):
                    door_dict = st.session_state.get("m15_doors", {})
                    for d in door_dict.get(wk, []):
                        if d.get("id") == op_id:
                            d["pos_m"] = round(new_pos, 2)
                            st.session_state[f"m15_edit_dpos_{op_id}"] = round(new_pos, 2)
                            st.session_state[f"m15_mv_d_pos_{op_id}"] = round(new_pos, 2)
                            st.session_state["m15_active_move_dim"] = {
                                "op_id": op_id,
                                "kind": "door",
                                "kind_ar": "الباب",
                                "name": d.get("name", op_id),
                                "wk": wk,
                                "pos_m": round(new_pos, 2),
                                "w_m": float(d.get("w_m", 0.9)),
                                "ts": time.time(),
                            }
                            found = True
                            break

                # 2. Fallback search across both stores if not found
                if not found:
                    for w in st.session_state.get("m15_windows", {}).get(wk, []):
                        if w.get("id") == op_id:
                            w["pos_m"] = round(new_pos, 2)
                            st.session_state[f"m15_edit_wpos_{op_id}"] = round(new_pos, 2)
                            st.session_state[f"m15_mv_w_pos_{op_id}"] = round(new_pos, 2)
                            st.session_state["m15_active_move_dim"] = {
                                "op_id": op_id,
                                "kind": "win",
                                "kind_ar": "الشباك",
                                "name": w.get("name", op_id),
                                "wk": wk,
                                "pos_m": round(new_pos, 2),
                                "w_m": float(w.get("w_m", 1.0)),
                                "ts": time.time(),
                            }
                            found = True
                            break
                    if not found:
                        for d in st.session_state.get("m15_doors", {}).get(wk, []):
                            if d.get("id") == op_id:
                                d["pos_m"] = round(new_pos, 2)
                                st.session_state[f"m15_edit_dpos_{op_id}"] = round(new_pos, 2)
                                st.session_state[f"m15_mv_d_pos_{op_id}"] = round(new_pos, 2)
                                st.session_state["m15_active_move_dim"] = {
                                    "op_id": op_id,
                                    "kind": "door",
                                    "kind_ar": "الباب",
                                    "name": d.get("name", op_id),
                                    "wk": wk,
                                    "pos_m": round(new_pos, 2),
                                    "w_m": float(d.get("w_m", 0.9)),
                                    "ts": time.time(),
                                }
                                found = True
                                break

            if from_query:
                if "m15_op_move" in st.query_params:
                    try:
                        del st.query_params["m15_op_move"]
                    except Exception:
                        pass
                if "module" in st.query_params:
                    try:
                        del st.query_params["module"]
                    except Exception:
                        pass

            st.session_state["m15_3d_sync_input"] = ""
            _resequence_openings()
            st.session_state.pop("m15_plan_png_b64", None)
            save_settings()
            st.toast(f"✅ تم اعتماد وحفظ موضع الفتحة ({new_pos:.2f}م) في الحصر بنجاح!", icon="💾")
        except Exception:
            if from_query:
                if "m15_op_move" in st.query_params:
                    try:
                        del st.query_params["m15_op_move"]
                    except Exception:
                        pass
                if "module" in st.query_params:
                    try:
                        del st.query_params["module"]
                    except Exception:
                        pass


def render_masonry_plaster_module():
    """نقطة الدخول الرئيسية للـ Module 12."""
    st.session_state["nav_view"] = "module"
    st.session_state["in_module"] = True
    _handle_sync_payload()
    _init_state()

    def _on_openings_expander_change():
        is_now_open = bool(st.session_state.get("m15_openings_expander", False))
        st.session_state["m15_openings_expander_open"] = is_now_open
        if not is_now_open:
            st.session_state["m15_openings_win_wall_sel"] = 0
            st.session_state["m15_openings_door_wall_sel"] = 0
            st.session_state["m15_preview_opening"] = None
            st.session_state["m15_openings_keep_expanded"] = False
            st.session_state["m15_show_conflict_modal"] = False
            st.session_state["m15_conflict_errors"] = []

    is_openings_exp = bool(st.session_state.get("m15_openings_keep_expanded", False) or st.session_state.get("m15_show_conflict_modal", False))
    if is_openings_exp:
        st.session_state["m15_openings_expander_open"] = True

    is_add_wall_active = bool(st.session_state.get("m15_add_wall_mode", False))
    is_add_active = bool(st.session_state.get("m15_add_col_mode", False))
    is_restore_active = bool(st.session_state.get("m15_restore_col_mode", False))
    is_del_wall_active = bool(st.session_state.get("m15_del_wall_mode", False))
    is_add_win_active = bool(st.session_state.get("m15_add_win_mode", False))
    is_add_door_active = bool(st.session_state.get("m15_add_door_mode", False))

    # Hidden bridge text_input placed at top of module so it is always present in DOM
    st.markdown(
        """<style>
        div[data-testid="stTextInput"]:has(input[aria-label="m15_3d_sync_payload"]) {
            position: fixed !important;
            top: -9999px !important;
            left: -9999px !important;
            width: 1px !important;
            height: 1px !important;
            opacity: 0 !important;
            pointer-events: none !important;
            z-index: -9999 !important;
        }
        </style>""",
        unsafe_allow_html=True
    )
    sync_val = st.text_input(
        "m15_3d_sync_payload",
        value="",
        key="m15_3d_sync_input",
        label_visibility="collapsed"
    )
    if sync_val:
        _handle_sync_payload(sync_val)
    elif "m15_op_move" in st.query_params:
        _handle_sync_payload(st.query_params["m15_op_move"])

    lc,rc=st.columns([0.82,1.65],gap="medium")
    with lc:
        with st.expander("🖼️ تحميل صورة مسقط افقي استرشادي للمباني", expanded=False):
            _section_upload_image()
        with st.expander("1️⃣ شبكة المحاور", expanded=False): _section_axes()
        is_add_wall_active = bool(st.session_state.get("m15_add_wall_mode", False))
        with st.expander("2️⃣ إسقاط الحوائط على المحاور", expanded=is_add_wall_active): _section_add_walls()
        with st.expander("➕ إضافة الأعمدة على المحاور", expanded=is_add_active): _section_add_columns()
        with st.expander("🚪🪟 نماذج الشبابيك والأبواب", expanded=False):
            _section_opening_types()
        with st.expander("4️⃣ إسقاط الشبابيك", expanded=is_add_win_active):
            _section_add_windows()
        with st.expander("5️⃣ إسقاط الأبواب", expanded=is_add_door_active):
            _section_add_doors()
        with st.expander("3️⃣ تحديد مواصفات وتعديل الحوائط", expanded=False): _section_walls()
        with st.expander("📐 ضبط اتجاهات وضرب الأعمدة", expanded=False): _section_column_orientations()
        with st.expander("🗑️ حذف الشبابيك والأبواب", expanded=False):
            _section_delete_openings()
        with st.expander("🗑️ حذف حوائط", expanded=is_del_wall_active): _section_delete_walls()
        with st.expander("🗑️ حذف الأعمدة", expanded=False): _section_columns()
        with st.expander("♻️ استعادة الحوائط المحذوفة", expanded=False): _section_restore_walls()
        with st.expander("♻️ استعادة أعمدة (Interactive)", expanded=is_restore_active): _section_restore_columns()
        with st.expander("♻️ استعادة الشبابيك والأبواب المحذوفة", expanded=False):
            _section_restore_openings()
        with st.expander("7️⃣ تحديد حوائط المحارة", expanded=False):
            _section_plaster_walls()
        with st.expander("6️⃣ أنواع مقاسات الطوب", expanded=False):
            _section_brick_type()

    with rc:
        st.markdown(
            "<div style='font-size:1.15rem;font-weight:700;color:#ffffff;line-height:32px;margin:0 0 18px 0;display:flex;align-items:center;' dir='rtl'>"
            "📐 المسقط الأفقي المصمم"
            "</div>",
            unsafe_allow_html=True
        )

        active_dim = st.session_state.get("m15_active_move_dim")
        is_active_dim = False
        dim_elapsed = 0.0
        if active_dim:
            dim_elapsed = time.time() - float(active_dim.get("ts", 0.0))
            if dim_elapsed < 4.2:
                is_active_dim = True
            else:
                st.session_state.pop("m15_active_move_dim", None)
                active_dim = None

        if is_active_dim and active_dim:
            kind_ar = active_dim.get("kind_ar", "الفتحة")
            name = active_dim.get("name", "")
            pos_m = float(active_dim.get("pos_m", 0.0))
            rem_sec = max(1, int(math.ceil(4.0 - dim_elapsed)))
            rem_ms = max(200, int((4.0 - dim_elapsed) * 1000))

            buf_dim = _draw_plan(with_dim=True)
            b64_dim = base64.b64encode(buf_dim.getvalue()).decode("utf-8")
            buf_clean = _draw_plan(with_dim=False)
            b64_clean = base64.b64encode(buf_clean.getvalue()).decode("utf-8")

            # إظهار المسقط مع خطوط الأبعاد مباشرة وبدون أي بانيلات
            st.markdown(
                f"""<div style="width: 100%; text-align: center; background: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
                    <img id="m15_plan_static_img" src="data:image/png;base64,{b64_dim}" style="width: 100%; max-width: 100%; height: auto; display: block; border-radius: 6px;" />
                    <img src="//:0" style="display:none;" onerror="
                        (function() {{
                            setTimeout(function() {{
                                var banner = document.getElementById('m15_dim_banner_container');
                                if (banner) {{
                                    banner.style.opacity = '0';
                                    banner.style.transform = 'translateY(-6px)';
                                    setTimeout(function() {{ banner.style.display = 'none'; }}, 400);
                                }}
                                var img = document.getElementById('m15_plan_static_img');
                                if (img) {{
                                    img.src = 'data:image/png;base64,{b64_clean}';
                                }}
                            }}, {rem_ms});
                        }})();
                    " />
                </div>""",
                unsafe_allow_html=True
            )
            try:
                import streamlit.components.v1 as _comp
                _comp.html(
                    f"""<script>
                    (function() {{
                        var remMs = {rem_ms};
                        setTimeout(function() {{
                            try {{
                                var pDoc = (window.parent && window.parent.document) ? window.parent.document : document;
                                var b = pDoc.getElementById('m15_dim_banner_container');
                                if (b) {{
                                    b.style.opacity = '0';
                                    b.style.transform = 'translateY(-6px)';
                                    setTimeout(function() {{ b.style.display = 'none'; }}, 400);
                                }}
                                var img = pDoc.getElementById('m15_plan_static_img');
                                if (img) {{
                                    img.src = 'data:image/png;base64,{b64_clean}';
                                }}
                            }} catch(e) {{}}
                        }}, remMs);
                    }})();
                    </script>""",
                    height=0,
                    width=0
                )
            except Exception:
                pass
        else:
            pending_del_w = st.session_state.get("m15_pending_delete_wall")
            if pending_del_w:
                all_walls = _get_all_walls()
                if pending_del_w in all_walls:
                    play_delete_confirmation_whistle(f"m15_plan_del_wall_{pending_del_w}")
                    wm = _get_wall_name_map()
                    w_name = wm.get(pending_del_w, "—")
                    st.markdown(
                        f"""<div style='background: linear-gradient(135deg, #fff1f2, #ffe4e6); border: 2px solid #f43f5e;
                        border-radius: 8px; padding: 8px 16px; margin-bottom: 8px; font-weight: 800; color: #9f1239; font-size: 0.95rem;' dir='rtl'>
                            ⚠️ تأكيد حذف الحائط <b>{w_name}</b>
                        </div>""",
                        unsafe_allow_html=True
                    )
                    c_rc_y, c_rc_n = st.columns([1.2, 1.0])
                    with c_rc_y:
                        if st.button("✅ نعم، تأكيد حذف الحائط", type="primary", key="m15_rc_conf_del_wall_btn", use_container_width=True):
                            _confirm_delete_wall(pending_del_w)
                    with c_rc_n:
                        if st.button("❌ إلغاء", key="m15_rc_cancel_del_wall_btn", use_container_width=True):
                            st.session_state["m15_pending_delete_wall"] = None
                            st.session_state.pop("_last_del_confirm_whistle_token", None)
                            st.rerun()

            if is_add_active:
                _render_interactive_plan(box_mode="add")
            elif is_restore_active:
                _render_interactive_plan(box_mode="restore")
            elif is_del_wall_active:
                _render_interactive_plan(box_mode="delete_wall")
            elif is_add_wall_active:
                _render_interactive_plan(box_mode="add_wall")
            elif is_add_win_active:
                _render_interactive_plan(box_mode="add_window")
            elif is_add_door_active:
                _render_interactive_plan(box_mode="add_door")
            else:
                st.image(_draw_plan(with_dim=False), use_container_width=True)
            st.markdown(
                f"""<div style='font-size:0.78rem;margin-top:3px;display:flex;gap:12px;flex-wrap:wrap;'>
                    <span style='color:{_CLR_WALL_12};font-weight:bold;'>■ حائط 12سم</span>
                    <span style='color:{_CLR_WALL_25};font-weight:bold;'>■ حائط 25سم</span>
                    <span style='color:{_CLR_WALL_PARAPET};font-weight:bold;'>■ حائط دروة</span>
                    <span style='color:{_CLR_WIN};font-weight:bold;'>■ شباك (W#)</span>
                    <span style='color:{_CLR_DOOR};font-weight:bold;'>■ باب (D#)</span>
                    <span style='color:{_CLR_COL};font-weight:bold;'>■ عمود (C#)</span>
                    <span style='color:#EC4899;font-weight:bold;'>▨ وجه محارة (وردي)</span>
                    <span style='color:#222;font-weight:bold;'>■ حائط (L#)</span>
                    <span style='color:#888;font-weight:bold;'>┄ خط استرشادي (محذوف)</span>
                </div>""",unsafe_allow_html=True)
    st.divider()
    with st.expander("🌐 3D (Data Processing & Rendering) — العارض ثلاثي الأبعاد التفاعلي", expanded=False):
        _section_3d_viewer()
    st.divider()
    with st.expander("📋 جدول الحصر وخامات البياض", expanded=False):
        _section_plaster_boq()
    st.divider()
    with st.expander("8️⃣ اسعار وتكلفة المباني والمحارة", expanded=False):
        _section_survey()
    save_settings()
    _inject_floating_plan_viewer()

