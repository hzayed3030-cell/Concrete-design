"""
Module 12 -- Brick & Plastering Survey
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
    _ensure_module12_state,
    reset_module_12_state,
)
from modules.table_styler import render_styled_table

_WALL_THIN=12; _WALL_THICK=25; _SHIFT_COL=6

# ─── خيارات ترحيل الأعمدة بالنسبة للمحاور (6 سم) ──────────────────────────
M12_SHIFT_X_OPTIONS = [
    "متمركز على المحور (Centered)",
    "جسم العمود يميناً (الوجه يسار المحور - 6 cm)",
    "جسم العمود يساراً (الوجه يمين المحور + 6 cm)",
]
M12_SHIFT_Y_OPTIONS = [
    "متمركز على المحور (Centered)",
    "جسم العمود لأعلى (الوجه أسفل المحور - 6 cm)",
    "جسم العمود لأسفل (الوجه أعلى المحور + 6 cm)",
]
_CLR_WALL_12="#EFA368"; _CLR_WALL_25="#8B1A1A"
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
    if "m12_x_axes" not in st.session_state or "module_12_data" not in st.session_state:
        _ensure_module12_state(cfg)
    if "m12_preview_opening" not in st.session_state:
        st.session_state["m12_preview_opening"] = None
    if "m12_win_preview_disabled" not in st.session_state:
        st.session_state["m12_win_preview_disabled"] = False
    if "m12_door_preview_disabled" not in st.session_state:
        st.session_state["m12_door_preview_disabled"] = False
    if "m12_win_preview_sig" not in st.session_state:
        st.session_state["m12_win_preview_sig"] = None
    if "m12_door_preview_sig" not in st.session_state:
        st.session_state["m12_door_preview_sig"] = None
    if "m12_show_conflict_modal" not in st.session_state:
        st.session_state["m12_show_conflict_modal"] = False
    if "m12_conflict_errors" not in st.session_state:
        st.session_state["m12_conflict_errors"] = []
    if "m12_openings_keep_expanded" not in st.session_state:
        st.session_state["m12_openings_keep_expanded"] = False
    if "m12_commit_success_msg" not in st.session_state:
        st.session_state["m12_commit_success_msg"] = None
    if "m12_openings_win_wall_sel" not in st.session_state:
        st.session_state["m12_openings_win_wall_sel"] = 0
    if "m12_openings_door_wall_sel" not in st.session_state:
        st.session_state["m12_openings_door_wall_sel"] = 0
    if "m12_openings_expander_open" not in st.session_state:
        st.session_state["m12_openings_expander_open"] = False
    if "m12_parapet_wall_height" not in st.session_state:
        st.session_state["m12_parapet_wall_height"] = 1.0
    if "m12_parapet_walls" not in st.session_state:
        st.session_state["m12_parapet_walls"] = set()
    if "m12_col_length_cm" not in st.session_state:
        st.session_state["m12_col_length_cm"] = 60.0
    if "m12_col_width_cm" not in st.session_state:
        st.session_state["m12_col_width_cm"] = 30.0

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
    xs=st.session_state["m12_x_axes"]; ys=st.session_state["m12_y_axes"]
    removed=st.session_state["m12_col_removed"]
    m={}; n=1
    for j in range(len(ys)):
        for i in range(len(xs)):
            if (i,j) not in removed: m[(i,j)]=f"C{n}"; n+=1
    return m

def _get_wall_name_map():
    removed=st.session_state["m12_wall_removed"]
    m={}; n=1
    for wk in _get_all_walls():
        if wk not in removed: m[wk]=f"L{n}"; n+=1
    return m

def _next_op_id(prefix="op"):
    nid = st.session_state.get("m12_next_op_id", 1)
    st.session_state["m12_next_op_id"] = nid + 1
    return f"{prefix}_{nid}"

def _ensure_opening_names():
    """ضمان وجود معرف فريد (id) وتسلسل متتابع سليم لكافة الشبابيك والأبواب."""
    _normalize_wall_keys()
    if "m12_windows" not in st.session_state:
        st.session_state["m12_windows"] = {}
    if "m12_doors" not in st.session_state:
        st.session_state["m12_doors"] = {}

    for wk, wl in st.session_state["m12_windows"].items():
        for w in wl:
            if "id" not in w:
                w["id"] = _next_op_id("win")
    for wk, dl in st.session_state["m12_doors"].items():
        for d in dl:
            if "id" not in d:
                d["id"] = _next_op_id("door")

    _resequence_openings()

def _ensure_opening_ids():
    _ensure_opening_names()

def _get_active_windows_list():
    """الحصول على قائمة مرتبة هندسياً بكافة الشبابيك النشطة غير المحذوفة."""
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m12_wall_removed", set())
    active_wins = []
    seen_wids = set()
    for w_idx, wk in enumerate(all_walls):
        if wk in removed_walls:
            continue
        for win in st.session_state.get("m12_windows", {}).get(wk, []):
            wid = win.get("id")
            if not win.get("removed", False) and wid and wid not in seen_wids:
                seen_wids.add(wid)
                active_wins.append((w_idx, float(win.get("pos_m", 0.0)), win, wk))
    for wk, w_list in st.session_state.get("m12_windows", {}).items():
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
    removed_walls = st.session_state.get("m12_wall_removed", set())
    active_doors = []
    seen_dids = set()
    for w_idx, wk in enumerate(all_walls):
        if wk in removed_walls:
            continue
        for door in st.session_state.get("m12_doors", {}).get(wk, []):
            did = door.get("id")
            if not door.get("removed", False) and did and did not in seen_dids:
                seen_dids.add(did)
                active_doors.append((w_idx, float(door.get("pos_m", 0.0)), door, wk))
    for wk, d_list in st.session_state.get("m12_doors", {}).items():
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
        for wl in st.session_state.get("m12_windows", {}).values():
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
        for dl in st.session_state.get("m12_doors", {}).values():
            for d in dl:
                if d.get("id") == did:
                    d["name"] = seq_name



def _remove_opening_by_id(op_id, kind="win"):
    """
    حذف الفتحة (نقلها إلى سلة المهملات) والتأكد من وضع علامة الحذف عليها في كافة القوائم،
    ثم إعادة تسلسل الفتحات النشطة فوراً لضبط الرسم والبرنامج.
    """
    store = st.session_state.get("m12_windows" if kind == "win" else "m12_doors", {})
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


def _wall_display_label(w_key,cm,wm):
    i1,j1,i2,j2=w_key
    cs=cm.get((i1,j1),f"({i1+1},{j1+1})"); ce=cm.get((i2,j2),f"({i2+1},{j2+1})")
    return f"{wm.get(w_key,'—')}: {cs}\u2192{ce}"

def _get_all_walls():
    """
    كافة حوائط المشروع الممتدة بين المحاور المتجاورة أفقياً ورأسياً.
    تبقى الحوائط ثابتة ومستقلة على شبكة المحاور ولا تُحذف عند حذف أي عمود.
    """
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        return []
    w = []
    # 1. الحوائط الأفقية على كل محور Y
    for j in range(len(ys)):
        for i in range(len(xs) - 1):
            w.append((i, j, i + 1, j))
    # 2. الحوائط الرأسية على كل محور X
    for i in range(len(xs)):
        for j in range(len(ys) - 1):
            w.append((i, j, i, j + 1))
    return w

def _get_all_columns():
    """كافة أعمدة المشروع الافتراضية عند تقاطعات المحاور."""
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    return [(i, j) for j in range(len(ys)) for i in range(len(xs))]

def _normalize_wall_keys():
    """
    تسوية مفاتيح الحوائط القديمة المدمجة لضمان تقسيمها إلى مفاتيح فردية بين المحاور المتجاورة
    بحيث لا تضيع أي بيانات سمك أو شبابيك أو أبواب من جلسات سابقة.
    """
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        return

    # 1. تسوية سمك الحوائط
    wt = st.session_state.get("m12_wall_thickness", {})
    new_wt = {}
    for wk, val in wt.items():
        i1, j1, i2, j2 = wk
        if j1 == j2 and abs(i2 - i1) > 1:
            for i in range(min(i1, i2), max(i1, i2)):
                new_wt[(i, j1, i + 1, j1)] = val
        elif i1 == i2 and abs(j2 - j1) > 1:
            for j in range(min(j1, j2), max(j1, j2)):
                new_wt[(i1, j, i1, j + 1)] = val
        else:
            new_wt[wk] = val
    st.session_state["m12_wall_thickness"] = new_wt

    # 2. تسوية ارتفاعات الحوائط
    wh = st.session_state.get("m12_wall_heights", {})
    new_wh = {}
    for wk, val in wh.items():
        i1, j1, i2, j2 = wk
        if j1 == j2 and abs(i2 - i1) > 1:
            for i in range(min(i1, i2), max(i1, i2)):
                new_wh[(i, j1, i + 1, j1)] = val
        elif i1 == i2 and abs(j2 - j1) > 1:
            for j in range(min(j1, j2), max(j1, j2)):
                new_wh[(i1, j, i1, j + 1)] = val
        else:
            new_wh[wk] = val
    st.session_state["m12_wall_heights"] = new_wh

    # 2.5 تسوية حوائط الدروة
    pw = st.session_state.get("m12_parapet_walls", set())
    new_pw = set()
    for wk in pw:
        i1, j1, i2, j2 = wk
        if j1 == j2 and abs(i2 - i1) > 1:
            for i in range(min(i1, i2), max(i1, i2)):
                new_pw.add((i, j1, i + 1, j1))
        elif i1 == i2 and abs(j2 - j1) > 1:
            for j in range(min(j1, j2), max(j1, j2)):
                new_pw.add((i1, j, i1, j + 1))
        else:
            new_pw.add(wk)
    st.session_state["m12_parapet_walls"] = new_pw

    # 3. تسوية الحوائط المحذوفة
    rw = st.session_state.get("m12_wall_removed", set())
    new_rw = set()
    for wk in rw:
        i1, j1, i2, j2 = wk
        if j1 == j2 and abs(i2 - i1) > 1:
            for i in range(min(i1, i2), max(i1, i2)):
                new_rw.add((i, j1, i + 1, j1))
        elif i1 == i2 and abs(j2 - j1) > 1:
            for j in range(min(j1, j2), max(j1, j2)):
                new_rw.add((i1, j, i1, j + 1))
        else:
            new_rw.add(wk)
    st.session_state["m12_wall_removed"] = new_rw

    # 4. تسوية الشبابيك والأبواب
    for kind_key in ["m12_windows", "m12_doors"]:
        store = st.session_state.get(kind_key, {})
        new_store = {}
        for wk, ops in list(store.items()):
            i1, j1, i2, j2 = wk
            is_h = (j1 == j2)
            span_len = abs(i2 - i1) if is_h else abs(j2 - j1)
            if span_len > 1:
                for op in ops:
                    p = float(op.get("pos_m", 0.0))
                    cur_start = 0.0
                    if is_h:
                        for i in range(min(i1, i2), max(i1, i2)):
                            seg_len = abs(xs[i + 1] - xs[i])
                            if cur_start <= p <= (cur_start + seg_len + 0.01) or i == max(i1, i2) - 1:
                                sub_wk = (i, j1, i + 1, j1)
                                op_copy = dict(op)
                                op_copy["pos_m"] = round(max(0.0, min(seg_len, p - cur_start)), 2)
                                new_store.setdefault(sub_wk, []).append(op_copy)
                                break
                            cur_start += seg_len
                    else:
                        for j in range(min(j1, j2), max(j1, j2)):
                            seg_len = abs(ys[j + 1] - ys[j])
                            if cur_start <= p <= (cur_start + seg_len + 0.01) or j == max(j1, j2) - 1:
                                sub_wk = (i1, j, i1, j + 1)
                                op_copy = dict(op)
                                op_copy["pos_m"] = round(max(0.0, min(seg_len, p - cur_start)), 2)
                                new_store.setdefault(sub_wk, []).append(op_copy)
                                break
                            cur_start += seg_len
            else:
                # ── الحائط العادي (قطعة واحدة): انسخ بياناته كما هي ─────
                if ops:
                    new_store[wk] = list(ops)
        st.session_state[kind_key] = new_store

    # 5. تسوية أوجه المحارة المحددة
    pf = st.session_state.get("m12_plaster_faces", {})
    new_pf = {}
    for wk, val in pf.items():
        i1, j1, i2, j2 = wk
        if j1 == j2 and abs(i2 - i1) > 1:
            for i in range(min(i1, i2), max(i1, i2)):
                new_pf[(i, j1, i + 1, j1)] = list(val)
        elif i1 == i2 and abs(j2 - j1) > 1:
            for j in range(min(j1, j2), max(j1, j2)):
                new_pf[(i1, j, i1, j + 1)] = list(val)
        else:
            new_pf[wk] = list(val)
    st.session_state["m12_plaster_faces"] = new_pf

def _wall_length_m(wk):
    i1,j1,i2,j2=wk; xs=st.session_state["m12_x_axes"]; ys=st.session_state["m12_y_axes"]
    return abs(xs[i2]-xs[i1]) if j1==j2 else abs(ys[j2]-ys[j1])

def _get_col_wh(i, j):
    col_l = float(st.session_state.get("m12_col_length_cm", 60.0)) / 100.0
    col_w = float(st.session_state.get("m12_col_width_cm", 30.0)) / 100.0
    d = st.session_state.get("m12_col_dirs", {}).get((i, j), "NS")
    cw, ch = (col_w, col_l) if d == "NS" else (col_l, col_w)
    return cw, ch

def _get_col_size():
    col_l = float(st.session_state.get("m12_col_length_cm", 60.0)) / 100.0
    col_w = float(st.session_state.get("m12_col_width_cm", 30.0)) / 100.0
    return max(col_l, col_w)

def _normalize_m12_col_shift(val, axis="x"):
    s = str(val or "").strip()
    if axis == "x":
        if "جسم العمود يمين" in s or s.startswith("يمين") or "Right" in s.capitalize() or "+X" in s:
            return M12_SHIFT_X_OPTIONS[1]
        elif "جسم العمود يسار" in s or s.startswith("يسار") or "Left" in s.capitalize() or "-X" in s:
            return M12_SHIFT_X_OPTIONS[2]
        return M12_SHIFT_X_OPTIONS[0]
    else:
        if "جسم العمود لأعلى" in s or "جسم العمود لاعلي" in s or s.startswith("أعلى") or s.startswith("اعلي") or "Top" in s.capitalize() or "Up" in s.capitalize() or "+Y" in s:
            return M12_SHIFT_Y_OPTIONS[1]
        elif "جسم العمود لأسفل" in s or "جسم العمود لاسفل" in s or s.startswith("أسفل") or s.startswith("اسفل") or "Bottom" in s.capitalize() or "Down" in s.capitalize() or "-Y" in s:
            return M12_SHIFT_Y_OPTIONS[2]
        return M12_SHIFT_Y_OPTIONS[0]

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
    norm_sx = _normalize_m12_col_shift(sx_choice, axis="x")
    norm_sy = _normalize_m12_col_shift(sy_choice, axis="y")

    if norm_sx == M12_SHIFT_X_OPTIONS[1]:
        dx_m = (cw_m / 2.0) - off_m
    elif norm_sx == M12_SHIFT_X_OPTIONS[2]:
        dx_m = off_m - (cw_m / 2.0)
    else:
        dx_m = 0.0

    if norm_sy == M12_SHIFT_Y_OPTIONS[1]:
        dy_m = (ch_m / 2.0) - off_m
    elif norm_sy == M12_SHIFT_Y_OPTIONS[2]:
        dy_m = off_m - (ch_m / 2.0)
    else:
        dy_m = 0.0

    return dx_m, dy_m

def _col_center(i, j):
    xs = st.session_state["m12_x_axes"]
    ys = st.session_state["m12_y_axes"]
    col_shifts = st.session_state.get("m12_col_shifts", {})
    if (i, j) in col_shifts:
        tr = col_shifts[(i, j)]
        cw, ch = _get_col_wh(i, j)
        dx_m, dy_m = _compute_col_offsets(cw, ch, tr.get("shift_x"), tr.get("shift_y"))
        return xs[i] + dx_m, ys[j] + dy_m
    col_shifted = st.session_state.get("m12_col_shifted", {})
    dx, dy = col_shifted.get((i, j), (0.0, 0.0))
    return xs[i] + dx / 100.0, ys[j] + dy / 100.0

def _get_column_bounds_along_wall(wk):
    """
    حساب حدود أوجه الأعمدة الخرسانية على طول الحائط (wk) لتحديد المسافة الصافية المتاحة للفتحات.
    يُرجع: (col1_limit_m, col2_limit_m, col1_name, col2_name, wlen)
    """
    i1, j1, i2, j2 = wk
    xs = st.session_state["m12_x_axes"]
    ys = st.session_state["m12_y_axes"]
    removed_cols = st.session_state.get("m12_col_removed", set())
    cm = _get_col_name_map()
    wlen = _wall_length_m(wk)
    is_h = (j1 == j2)
    
    if is_h:
        x_min_w = min(xs[i1], xs[i2])
        i_start = min(i1, i2)
        i_end = max(i1, i2)
        # العمود في بداية الحائط (يسار)
        if (i_start, j1) not in removed_cols:
            cx1, cy1 = _col_center(i_start, j1)
            cw1, _ = _get_col_wh(i_start, j1)
            col1_limit = max(0.0, (cx1 + cw1 / 2.0) - x_min_w)
            col1_name = cm.get((i_start, j1), f"C({i_start+1},{j1+1})")
        else:
            col1_limit = 0.0
            col1_name = None
        
        # العمود في نهاية الحائط (يمين)
        if (i_end, j1) not in removed_cols:
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
        if (i1, j_start) not in removed_cols:
            cx1, cy1 = _col_center(i1, j_start)
            _, ch1 = _get_col_wh(i1, j_start)
            col1_limit = max(0.0, (cy1 + ch1 / 2.0) - y_min_w)
            col1_name = cm.get((i1, j_start), f"C({i1+1},{j_start+1})")
        else:
            col1_limit = 0.0
            col1_name = None
            
        # العمود في نهاية الحائط (أعلى)
        if (i1, j_end) not in removed_cols:
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
    i1, j1, i2, j2 = wk
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    thick = _get_wall_thickness(wk)
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
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
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
    removed_cols = st.session_state.get("m12_col_removed", set())
    n_xi = len(xs)
    n_yj = len(ys)

    for ci in range(n_xi):
        for cj in range(n_yj):
            if (ci, cj) in removed_cols:
                continue
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
    cand_pos = round((best_iv[0] + best_iv[1] - cand_w) / 2.0, 2)
    
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
    cand_pos = round((best_iv[0] + best_iv[1] - cand_w) / 2.0, 2)
    return True, "", cand_w, cand_pos

def _check_add_column(x_val, y_val, col_dir):
    """
    التحقق الهندسي الصارم عند إضافة عمود:
    1- التأكد من عدم الخروج من مساحة المسقط الأفقي.
    2- التأكد من عدم التعارض والتداخل مع إحداثيات الأعمدة القائمة.
    3- التأكد من عدم التداخل مع فتحات الشبابيك والأبواب القائمة.
    """
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    if not xs or not ys:
        return False, "يجب تحديد شبكة المحاور أولاً."
    x_min_p, x_max_p = min(xs), max(xs)
    y_min_p, y_max_p = min(ys), max(ys)
    col_l = float(st.session_state.get("m12_col_length_cm", 60.0)) / 100.0
    col_w = float(st.session_state.get("m12_col_width_cm", 30.0)) / 100.0
    cw, ch = (col_w, col_l) if col_dir == "NS" else (col_l, col_w)
    
    if x_val < x_min_p - 0.01 or x_val > x_max_p + 0.01 or y_val < y_min_p - 0.01 or y_val > y_max_p + 0.01:
        return False, f"إحداثيات العمود المطلوب عند ({x_val:.2f}, {y_val:.2f})م تقع خارج مساحة المسقط الأفقي! (حدود المسقط: X من {x_min_p:.2f} إلى {x_max_p:.2f}م | Y من {y_min_p:.2f} إلى {y_max_p:.2f}م)."

    removed_cols = st.session_state.get("m12_col_removed", set())
    cm = _get_col_name_map()
    all_cols = [(i, j) for j in range(len(ys)) for i in range(len(xs))]
    for (ci, cj) in all_cols:
        if (ci, cj) in removed_cols: continue
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
    removed_walls = st.session_state.get("m12_wall_removed", set())

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
    errors = st.session_state.get("m12_conflict_errors", [])
    preview = st.session_state.get("m12_preview_opening") or {}
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
            ℹ️ يبقى {op_kind_ar} المؤقت في مكانه على الرسم؛ اضغط زر الإغلاق ثم عدّل قيمة "بعد بداية {op_kind_ar} عن بداية الحائط" أدناه.
        </div>
        </div>""",
        unsafe_allow_html=True
    )

    if st.button("❌ إغلاق التنبيه", key="m12_conflict_dismiss_btn", type="primary", use_container_width=True, help="إغلاق التنبيه مع بقاء العنصر المؤقت في مكانه على الرسم بانتظار تعديل البعد"):
        st.session_state["m12_show_conflict_modal"] = False
        st.session_state["m12_conflict_errors"] = []
        st.session_state["m12_openings_keep_expanded"] = True

        # ضمان بقاء الفتحة المؤقتة ومطابقة كافة مدخلاتها في التشغيل القادم قبل إنشاء الـ widgets
        if preview and preview.get("wk"):
            preview["has_conflict"] = True
            preview["is_preview"] = True
            st.session_state["m12_preview_opening"] = preview
            st.session_state["m12_sync_preview_on_next_run"] = True

        st.rerun()

def _render_opening_commit_success_banner(info: dict):
    """
    عرض رسالة تأكيد خضراء عند اعتماد وتثبيت الشباك أو الباب:
    - خلفية خضراء واضحة مع إشعار التثبيت النهائي.
    - عرض رسالة التثبيت المطلوبة:
      "انه تم تثبيت مكان الشباك/الباب في المكان المحدد ، ولا يمكن تحريكة الان ، يمكن حذف فقط من قسم الحذف"
    - زر 'غلق التنبيه' للعودة إلى الشاشة السابقة (قسم إسقاط وتحريك الشبابيك والأبواب).
    """
    kind = info.get("kind", "win")
    kind_ar = info.get("kind_ar", "الشباك" if kind == "win" else "الباب")
    name = info.get("name", "")
    wall_label = info.get("wall_label", "")
    pos_m = float(info.get("pos_m", 0.0))
    w_m = float(info.get("w_m", 1.0))
    h_m = float(info.get("h_m", 1.2))
    msg_text = info.get("msg", f"انه تم تثبيت مكان {kind_ar} في المكان المحدد ، ولا يمكن تحريكة الان ، يمكن حذف فقط من قسم الحذف")

    st.markdown(
        f"""<div style='background:linear-gradient(135deg,#E8F5E9,#C8E6C9);border:2px solid #2E7D32;
        border-radius:10px;padding:14px 18px;margin:6px 0 14px 0;box-shadow:0 3px 10px rgba(46,125,50,0.18);' dir='rtl'>
        <div style='color:#1B5E20;font-size:1.02rem;font-weight:900;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;gap:8px;'>
            <div style='display:flex;align-items:center;gap:6px;'>
                <span style='font-size:1.3rem;'>✅</span>
                <span>تم تثبيت وإسقاط {kind_ar} بنجاح ({name})</span>
            </div>
            <span style='background:#A5D6A7;color:#1B5E20;font-size:0.78rem;padding:3px 10px;border-radius:12px;font-weight:bold;'>تثبيت نهائي</span>
        </div>
        <p style='color:#1B5E20;font-size:0.92rem;margin:0 0 10px 0;font-weight:800;line-height:1.5;'>
            {msg_text}
        </p>
        <div style='background:rgba(255,255,255,0.75);border-radius:6px;padding:8px 12px;font-size:0.83rem;color:#1B5E20;font-weight:700;margin-bottom:4px;line-height:1.6;'>
            📍 <b>الحائط:</b> {wall_label} &nbsp;|&nbsp; 📏 <b>الموضع:</b> {pos_m:.2f}م من بداية الحائط &nbsp;|&nbsp; 📐 <b>الأبعاد:</b> {w_m:.2f}م عرض × {h_m:.2f}م ارتفاع
        </div>
        </div>""",
        unsafe_allow_html=True
    )

    if st.button("غلق التنبيه", key="m12_commit_dismiss_btn", type="primary", use_container_width=True, help="العودة إلى شاشة إسقاط الشبابيك والأبواب"):
        st.session_state["m12_commit_success_msg"] = None
        st.session_state["m12_openings_keep_expanded"] = True
        st.rerun()

def _get_all_deleted_openings():
    """تجميع كافة الشبابيك والأبواب المحذوفة في المشروع لعرضها في سلة المحذوفات الموحدة."""
    _ensure_opening_names()
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    deleted = []
    for wk, wl in list(st.session_state.get("m12_windows", {}).items()):
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
    for wk, dl in list(st.session_state.get("m12_doors", {}).items()):
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

def _restore_opening(item, target_wk):
    """استعادة فتحة محذوفة إلى الحائط الأصلي أو حائط بديل تم اختياره من القائمة المنسدلة مع إعادة التسلسل فوراً."""
    s_wk = item["wk"]
    s_id = item["id"]
    is_win = (item["kind"] == "win")
    store = st.session_state["m12_windows"] if is_win else st.session_state["m12_doors"]

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
    store = st.session_state["m12_windows"] if is_win else st.session_state["m12_doors"]
    for wk in list(store.keys()):
        store[wk] = [op for op in store[wk] if op.get("id") != s_id]

def _get_wall_thickness(w_key):
    wall_thick = st.session_state["m12_wall_thickness"]
    if w_key in wall_thick:
        return wall_thick[w_key]
    i1, j1, i2, j2 = w_key
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
    parapet_walls = st.session_state.get("m12_parapet_walls", set())
    if w_key in parapet_walls:
        return True
    i1, j1, i2, j2 = w_key
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
    2. باقي الحوائط ترث تلقائياً القيمة الافتراضية من مدخل 'ارتفاع الحائط' (Wall Height).
    """
    if _is_parapet_wall(w_key):
        return float(st.session_state.get("m12_parapet_wall_height", st.session_state.get("m12_parapet_h_input", 1.0)))
    if default_h is not None:
        return float(default_h)
    return float(st.session_state.get("m12_default_wall_height", st.session_state.get("m12_default_h_input", 3.0)))

def _detect_perimeter_walls():
    """
    كشف حوائط المحيط الخارجي (Perimeter Boundary Walls) تلقائياً:
    وهي الحوائط الواقعة على الحدود الخارجية لشبكة المحاور (أدنى/أعلى Y وأدنى/أعلى X).
    """
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        return []
    nx = len(xs)
    ny = len(ys)
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m12_wall_removed", set())
    perim = []
    for wk in all_walls:
        if wk in removed_walls:
            continue
        i1, j1, i2, j2 = wk
        if j1 == j2 and (j1 == 0 or j1 == ny - 1):
            perim.append(wk)
        elif i1 == i2 and (i1 == 0 or i1 == nx - 1):
            perim.append(wk)
    return perim

def _get_wall_windows(w_key):
    win_data = st.session_state.get("m12_windows", {})
    if w_key in win_data and win_data[w_key]:
        return [w for w in win_data[w_key] if not w.get("removed", False)]
    i1, j1, i2, j2 = w_key
    xs = st.session_state["m12_x_axes"]; ys = st.session_state["m12_y_axes"]
    collected = []
    if j1 == j2:
        for i in range(min(i1, i2), max(i1, i2)):
            offset = abs(xs[i] - xs[i1])
            for win in win_data.get((i, j1, i + 1, j1), []):
                if not win.get("removed", False):
                    wc = dict(win); wc["pos_m"] = win.get("pos_m", 0.0) + offset
                    collected.append(wc)
    else:
        for j in range(min(j1, j2), max(j1, j2)):
            offset = abs(ys[j] - ys[j1])
            for win in win_data.get((i1, j, i1, j + 1), []):
                if not win.get("removed", False):
                    wc = dict(win); wc["pos_m"] = win.get("pos_m", 0.0) + offset
                    collected.append(wc)
    return collected

def _get_wall_doors(w_key):
    door_data = st.session_state.get("m12_doors", {})
    if w_key in door_data and door_data[w_key]:
        return [d for d in door_data[w_key] if not d.get("removed", False)]

    i1, j1, i2, j2 = w_key
    xs = st.session_state["m12_x_axes"]; ys = st.session_state["m12_y_axes"]
    collected = []
    if j1 == j2:
        for i in range(min(i1, i2), max(i1, i2)):
            offset = abs(xs[i] - xs[i1])
            for d in door_data.get((i, j1, i + 1, j1), []):
                if not d.get("removed", False):
                    dc = dict(d); dc["pos_m"] = d.get("pos_m", 0.0) + offset
                    collected.append(dc)
    else:
        for j in range(min(j1, j2), max(j1, j2)):
            offset = abs(ys[j] - ys[j1])
            for d in door_data.get((i1, j, i1, j + 1), []):
                if not d.get("removed", False):
                    dc = dict(d); dc["pos_m"] = d.get("pos_m", 0.0) + offset
                    collected.append(dc)
    return collected

def _draw_plan(with_dim=True):
    xs=st.session_state["m12_x_axes"]; ys=st.session_state["m12_y_axes"]
    removed_cols=st.session_state["m12_col_removed"]
    removed_walls=st.session_state["m12_wall_removed"]
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
    # ── تباعد خطوط الأبعاد والمحيط الخارجي بشكل مضغوط لزيادة مساحة الرسم ──
    d_bays = max(0.48, min(0.68, max(span_x, span_y) * 0.065))
    d_tot_gap = max(0.45, min(0.58, max(span_x, span_y) * 0.055))
    d_tag_gap = max(0.42, min(0.55, max(span_x, span_y) * 0.050))
    pad_extra = 0.30

    margin_b = d_bays + d_tot_gap + d_tag_gap + pad_extra
    margin_l = d_bays + d_tot_gap + d_tag_gap + pad_extra
    margin_r = max(0.80, min(1.3, span_x * 0.08 + 0.3))
    margin_t = max(1.50, min(2.0, max(span_x, span_y) * 0.11 + 0.8))

    ax.set_xlim(x_min - margin_l, x_max + margin_r)
    ax.set_ylim(y_min - margin_b, y_max + margin_t)
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

    # ── دالتا مساعدة لرسم خطوط الأبعاد المعمارية بالشَرطات المائلة ──
    def draw_dim_h(x1, x2, y_pos, text, color="#0f172a", is_active=True, tick_h=0.08):
        if abs(x2 - x1) < 1e-4: return
        xa, xb = min(x1, x2), max(x1, x2)
        ls = "-" if is_active else "--"
        lw = 1.2 if is_active else 0.9
        ax.plot([xa, xb], [y_pos, y_pos], color=color, lw=lw, ls=ls, zorder=5)
        dt = tick_h
        ax.plot([xa - dt, xa + dt], [y_pos - dt, y_pos + dt], color=color, lw=1.6 if is_active else 1.1, zorder=5.5)
        ax.plot([xb - dt, xb + dt], [y_pos - dt, y_pos + dt], color=color, lw=1.6 if is_active else 1.1, zorder=5.5)
        bg = "#ffffff" if is_active else "#f1f5f9"
        ax.text((xa + xb) / 2.0, y_pos + dt * 1.2, text, ha="center", va="bottom",
                fontsize=fs_dim, fontweight="bold" if is_active else "normal", color=color, zorder=6,
                bbox=dict(boxstyle="round,pad=0.2", facecolor=bg, edgecolor="#cbd5e1" if not is_active else "#94a3b8", lw=0.6, alpha=0.95))

    def draw_dim_v(y1, y2, x_pos, text, color="#0f172a", is_active=True, tick_w=0.08):
        if abs(y2 - y1) < 1e-4: return
        ya, yb = min(y1, y2), max(y1, y2)
        ls = "-" if is_active else "--"
        lw = 1.2 if is_active else 0.9
        ax.plot([x_pos, x_pos], [ya, yb], color=color, lw=lw, ls=ls, zorder=5)
        dt = tick_w
        ax.plot([x_pos - dt, x_pos + dt], [ya - dt, ya + dt], color=color, lw=1.6 if is_active else 1.1, zorder=5.5)
        ax.plot([x_pos - dt, x_pos + dt], [yb - dt, yb + dt], color=color, lw=1.6 if is_active else 1.1, zorder=5.5)
        bg = "#ffffff" if is_active else "#f1f5f9"
        ax.text(x_pos - dt * 1.2, (ya + yb) / 2.0, text, ha="center", va="center", rotation=90,
                fontsize=fs_dim, fontweight="bold" if is_active else "normal", color=color, zorder=6,
                bbox=dict(boxstyle="round,pad=0.2", facecolor=bg, edgecolor="#cbd5e1" if not is_active else "#94a3b8", lw=0.6, alpha=0.95))

    # رسم خطوط المحاور الهندسية
    for idx, x in enumerate(xs):
        ax.axvline(x=x, color=_CLR_AXIS_X, lw=0.7, ls="--", alpha=0.35, zorder=1)
    for idx, y in enumerate(ys):
        ax.axhline(y=y, color=_CLR_AXIS_Y, lw=0.7, ls="--", alpha=0.35, zorder=1)

    for wk in _get_all_walls():
        i1, j1, i2, j2 = wk; removed = wk in removed_walls
        thick = _get_wall_thickness(wk)
        cross_min, cross_max, cross_c, thick_m = _get_wall_cross_bounds(wk)
        half_t = thick_m / 2.0
        color = _CLR_WALL_12 if thick == _WALL_THIN else _CLR_WALL_25
        is_h = (j1 == j2)
        wlen = _wall_length_m(wk)
        lname = wm.get(wk, "")
        if removed:
            # 4- رسم خط استرشادي مكان الحائط المحذوف فقط دون حسابات أو كتابة أبعاد
            ax.plot([xs[i1], xs[i2]], [ys[j1], ys[j2]], color="#94a3b8", ls=":", lw=1.2, alpha=0.75, zorder=2)
        else:
            if is_h: rx = min(xs[i1], xs[i2]); ry = cross_min; rw = abs(xs[i2] - xs[i1]); rh = thick_m
            else: rx = cross_min; ry = min(ys[j1], ys[j2]); rw = thick_m; rh = abs(ys[j2] - ys[j1])
            ax.add_patch(patches.Rectangle((rx, ry), rw, rh, lw=1.0, edgecolor="#333333", facecolor=color, alpha=0.85, zorder=2))

            # ── رسم أوجه المحارة بخطوط مائلة وردية واسعة فقط (بدون أي إطار أو خطوط حدود) ──
            plaster_faces_map = st.session_state.get("m12_plaster_faces", {})
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

            mx = rx + rw / 2; my = ry + rh / 2
            # كتابة اسم الحائط فقط دون الطول (تم الاكتفاء بخطوط الأبعاد الخارجية)
            label_text = lname
            if label_text:
                is_parapet = _is_parapet_wall(wk)
                if is_parapet:
                    label_text += " [دروة]"
                t_box_edge = "#0284c7" if is_parapet else "#cbd5e1"
                t_box_bg = "#f0f9ff" if is_parapet else "#ffffff"
                t_color = "#0369a1" if is_parapet else "#1e293b"
                if is_h:
                    ax.text(mx, cross_max + half_t * 1.5, label_text, ha="center", va="bottom",
                            fontsize=fs_wall, color=t_color, fontweight="bold", zorder=5,
                            bbox=dict(boxstyle="round,pad=0.18", facecolor=t_box_bg, edgecolor=t_box_edge, lw=0.8 if is_parapet else 0.6, alpha=0.92))
                else:
                    ax.text(cross_max + half_t * 1.5, my, label_text, ha="left", va="center",
                            fontsize=fs_wall, color=t_color, fontweight="bold", zorder=5,
                            bbox=dict(boxstyle="round,pad=0.18", facecolor=t_box_bg, edgecolor=t_box_edge, lw=0.8 if is_parapet else 0.6, alpha=0.92))
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
        preview_op = st.session_state.get("m12_preview_opening")
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

    col_size = _get_col_size()
    for j in range(len(ys)):
        for i in range(len(xs)):
            if (i, j) in removed_cols:
                continue # إخفاء العمود المحذوف ليمر الحائط متصلاً مكانه
            cx, cy = _col_center(i, j)
            cw, ch = _get_col_wh(i, j)
            ax.add_patch(patches.Rectangle((cx - cw / 2, cy - ch / 2), cw, ch, lw=1.0, edgecolor="#000022", facecolor=_CLR_COL, alpha=0.92, zorder=6))
            cname = cm.get((i, j), "")
            if cname:
                # 3- كتابة اسم العمود أعلى يمين العمود الموجود في الرسم
                ax.text(cx + cw / 2 + col_size * 0.15, cy + ch / 2 + col_size * 0.15, cname,
                        ha="left", va="bottom", fontsize=fs_col, color="#1A1A6E", fontweight="bold", zorder=7)

    # ── خط أبعاد مؤقت لموضع تحريك الفتحة (نافذة/باب) مع نقطة بداية الحائط ──
    active_move_dim = (st.session_state.get("m12_active_move_dim") if with_dim else None)
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

    # ── خطوط الأبعاد المعمارية الخارجية (Exterior Dimension Chains) ─────────
    # تُعاد ضبط الأبعاد تلقائياً عند حذف حائط أو استعادته
    # خطوط الأبعاد السفلية المضغوطة (Bottom Chains)
    y_dim_bays = y_min - d_bays
    y_dim_tot  = y_min - (d_bays + d_tot_gap)
    y_tag      = y_min - (d_bays + d_tot_gap + d_tag_gap)

    bot_active_spans = []
    for i in range(len(xs) - 1):
        x1, x2 = xs[i], xs[i + 1]
        span = abs(x2 - x1)
        wk_bot = (i, 0, i + 1, 0)
        is_active = (wk_bot in _get_all_walls()) and (wk_bot not in removed_walls)
        
        # خطوط إسقاط الأبعاد (Witness lines)
        ax.plot([x1, x1], [y_min, y_dim_bays - 0.08], color="#94a3b8", lw=0.8, ls="--", zorder=3)
        ax.plot([x2, x2], [y_min, y_dim_bays - 0.08], color="#94a3b8", lw=0.8, ls="--", zorder=3)

        if is_active:
            bot_active_spans.append(span)
            draw_dim_h(x1, x2, y_dim_bays, f"{span:.2f}m", color="#0f172a", is_active=True)
        else:
            # إعادة ضبط البعد عند حذف الحائط: يظهر كبحر مفتوح بخط متقطع
            draw_dim_h(x1, x2, y_dim_bays, f"{span:.2f}m (—)", color="#94a3b8", is_active=False)

    # خط البعد الكلي الأفقي (Total Lx)
    ax.plot([x_min, x_min], [y_min, y_dim_tot - 0.08], color="#1e3a8a", lw=1.0, ls="--", zorder=3)
    ax.plot([x_max, x_max], [y_min, y_dim_tot - 0.08], color="#1e3a8a", lw=1.0, ls="--", zorder=3)
    tot_bot_active = sum(bot_active_spans)
    if tot_bot_active == span_x:
        txt_tot_x = f"Total Lx = {span_x:.2f}m"
    else:
        txt_tot_x = f"Lx = {span_x:.2f}m (Active: {tot_bot_active:.2f}m)"
    draw_dim_h(x_min, x_max, y_dim_tot, txt_tot_x, color="#1e3a8a", is_active=True)

    # وسوم المحاور الأفقية السفلية
    for idx, x in enumerate(xs):
        ax.text(x, y_tag, f"X{idx+1}\n{x:.2f}m", ha="center", va="top",
                fontsize=fs_axis, color=_CLR_AXIS_X, fontweight="bold")

    # خطوط الأبعاد الرأسية باليسار المضغوطة (Left Chains)
    x_dim_bays = x_min - d_bays
    x_dim_tot  = x_min - (d_bays + d_tot_gap)
    x_tag      = x_min - (d_bays + d_tot_gap + d_tag_gap)

    left_active_spans = []
    for j in range(len(ys) - 1):
        y1, y2 = ys[j], ys[j + 1]
        span = abs(y2 - y1)
        wk_left = (0, j, 0, j + 1)
        is_active = (wk_left in _get_all_walls()) and (wk_left not in removed_walls)

        # خطوط إسقاط الأبعاد (Witness lines)
        ax.plot([x_min, x_dim_bays - 0.08], [y1, y1], color="#94a3b8", lw=0.8, ls="--", zorder=3)
        ax.plot([x_min, x_dim_bays - 0.08], [y2, y2], color="#94a3b8", lw=0.8, ls="--", zorder=3)

        if is_active:
            left_active_spans.append(span)
            draw_dim_v(y1, y2, x_dim_bays, f"{span:.2f}m", color="#0f172a", is_active=True)
        else:
            # إعادة ضبط البعد عند حذف الحائط
            draw_dim_v(y1, y2, x_dim_bays, f"{span:.2f}m (—)", color="#94a3b8", is_active=False)

    # خط البعد الكلي الرأسي (Total Ly)
    ax.plot([x_min, x_dim_tot - 0.08], [y_min, y_min], color="#1e3a8a", lw=1.0, ls="--", zorder=3)
    ax.plot([x_min, x_dim_tot - 0.08], [y_max, y_max], color="#1e3a8a", lw=1.0, ls="--", zorder=3)
    tot_left_active = sum(left_active_spans)
    if tot_left_active == span_y:
        txt_tot_y = f"Total Ly = {span_y:.2f}m"
    else:
        txt_tot_y = f"Ly = {span_y:.2f}m (Active: {tot_left_active:.2f}m)"
    draw_dim_v(y_min, y_max, x_dim_tot, txt_tot_y, color="#1e3a8a", is_active=True)

    # وسوم المحاور الرأسية باليسار
    for idx, y in enumerate(ys):
        ax.text(x_tag, y, f"Y{idx+1} {y:.2f}m", ha="right", va="center",
                fontsize=fs_axis, color=_CLR_AXIS_Y, fontweight="bold")

    # إخفاء تدرجات المحاور الإحداثية لتجنب التشويش مع خطوط الأبعاد
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#e2e8f0")
        spine.set_linewidth(1.0)

    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    leg = [
        Patch(facecolor=_CLR_WALL_12, alpha=0.82, label="Wall 12cm"),
        Patch(facecolor=_CLR_WALL_25, alpha=0.82, label="Wall 25cm"),
        Patch(facecolor=_CLR_WIN, alpha=0.85, label="Window (W#)"),
        Patch(facecolor=_CLR_DOOR, alpha=0.90, label="Door (D#)"),
        Patch(facecolor=_CLR_COL, alpha=0.90, label="Column (C#)"),
        Patch(facecolor="none", edgecolor="#EC4899", hatch="/", lw=0, label="Plaster Face (وجه محارة)"),
        Line2D([0], [0], color="#94a3b8", ls=":", lw=1.5, label="Wall Removed (محذوف)"),
        Line2D([0], [0], color="#0f172a", lw=1.2, marker="|", label="Dimension (خط بعد)"),
    ]
    ax.legend(handles=leg, loc="upper right", fontsize=fs_leg, framealpha=0.92, ncol=2)
    ax.set_title("Floor Plan — Module 12: Brick & Plastering Survey", fontsize=fs_title, fontweight="bold", pad=12)

    plt.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=150, bbox_inches="tight"); plt.close(fig); buf.seek(0)
    try:
        st.session_state["m12_plan_png_b64"] = base64.b64encode(buf.getvalue()).decode("utf-8")
        buf.seek(0)
    except Exception:
        pass
    return buf

def _render_interactive_plan():
    """
    عرض المسقط الأفقي تفاعلياً مع أدوات تحكم مباشرة على الرسم (Zoom In, Zoom Out, Pan, Reset, Fullscreen):
    - علامات تحكم عائمة مباشرة فوق الرسم في شريط أدوات هندسي (CAD Toolbar).
    - أزرار: 🔍➕ تكبير (Zoom In)، 🔍➖ تصغير (Zoom Out)، 🔄 ضبط (Reset)، ⛶ ملء الشاشة (Fullscreen)، 💾 حفظ (Download PNG).
    - إمكانية التحريك والسحب الحر بالماوس (Click & Drag to Pan) في جميع الاتجاهات.
    - إمكانية التكبير والتصغير بواسطة بكرة الماوس (Mouse Wheel Zoom) عند موضع المؤشر.
    - النقر المزدوج (Double Click) للتكبير اللحظي.
    - دعم الإيماءات اللمسية على أجهزة اللمس (Pinch to Zoom & Touch Pan).
    - عداد نسبة التكبير اللحظية (Zoom %).
    """
def _render_interactive_plan(b64_override=None, b64_clean=None, rem_ms=0):
    if b64_override:
        b64_img = b64_override
    else:
        buf = _draw_plan(with_dim=False)
        if buf is None:
            return
        img_bytes = buf.getvalue() if hasattr(buf, "getvalue") else buf.read()
        b64_img = base64.b64encode(img_bytes).decode("utf-8")

    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    span_x = max(xs) - min(xs) if xs else 1.0
    span_y = max(ys) - min(ys) if ys else 1.0
    fig_w = min(18, max(10, span_x * 1.6 + 2.5))
    fig_h = min(15, max(8, span_y * 1.6 + 2.5))
    ratio = fig_h / fig_w
    viewer_h = int(max(540, min(820, 740 * ratio)))

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
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
    color: #1e293b;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    transition: all 0.15s ease;
    text-decoration: none;
    line-height: 1.2;
  }}
  .tb-btn:hover {{
    background: #e2e8f0;
    border-color: #64748b;
    color: #0f172a;
    transform: translateY(-1px);
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  }}
  .tb-btn:active {{
    transform: translateY(0);
    background: #cbd5e1;
  }}
  
  .zoom-badge {{
    font-size: 11.5px;
    font-weight: 800;
    color: #1d4ed8;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
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

<div id="viewport">
  <div class="cad-toolbar">
    <button class="tb-btn" id="btn-zoom-in" title="تكبير (Zoom In)">🔍➕ تكبير</button>
    <button class="tb-btn" id="btn-zoom-out" title="تصغير (Zoom Out)">🔍➖ تصغير</button>
    <button class="tb-btn" id="btn-reset" title="استعادة المركز والحجم الطبيعي (Reset 100%)">🔄 ضبط</button>
    <button class="tb-btn" id="btn-fullscreen" title="عرض ملء الشاشة (Fullscreen)">⛶ كامل الشاشة</button>
    <a class="tb-btn" id="btn-download" href="data:image/png;base64,{b64_img}" download="Floor_Plan_Module12.png" title="تنزيل الصورة (Download PNG)">💾 حفظ</a>
    <span class="zoom-badge" id="zoom-badge">100%</span>
    <span class="tb-hint">✋ اسحب للتحريك | 🔍 بكرة الماوس للتكبير</span>
  </div>

  <div id="canvas-wrapper">
    <img id="plan-img" src="data:image/png;base64,{b64_img}" alt="Floor Plan" />
  </div>
</div>

<script>
(function() {{
  const viewport = document.getElementById('viewport');
  const wrapper = document.getElementById('canvas-wrapper');
  const badge = document.getElementById('zoom-badge');

  let scale = 1.0;
  let panX = 0;
  let panY = 0;
  let isDragging = false;
  let startX = 0;
  let startY = 0;

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

  viewport.addEventListener('mousedown', function(e) {{
    if (e.target.closest('.cad-toolbar')) return;
    isDragging = true;
    startX = e.clientX - panX;
    startY = e.clientY - panY;
    viewport.classList.add('panning');
  }});

  window.addEventListener('mousemove', function(e) {{
    if (!isDragging) return;
    panX = e.clientX - startX;
    panY = e.clientY - startY;
    updateTransform();
  }});

  window.addEventListener('mouseup', function() {{
    if (isDragging) {{
      isDragging = false;
      viewport.classList.remove('panning');
    }}
  }});

  viewport.addEventListener('wheel', function(e) {{
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 0.87;
    applyZoom(factor, e.clientX, e.clientY);
  }}, {{ passive: false }});

  viewport.addEventListener('dblclick', function(e) {{
    if (e.target.closest('.cad-toolbar')) return;
    applyZoom(1.4, e.clientX, e.clientY);
  }});

  let touchStartDist = 0;
  let touchInitialScale = 1.0;
  let touchStartX = 0;
  let touchStartY = 0;

  viewport.addEventListener('touchstart', function(e) {{
    if (e.target.closest('.cad-toolbar')) return;
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
          var pb = window.parent.document.getElementById('m12_dim_banner_container');
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

def _compute_survey():
    removed_walls=st.session_state["m12_wall_removed"]
    default_h=float(st.session_state.get("m12_default_wall_height",3.0))
    cm=_get_col_name_map(); wm=_get_wall_name_map(); rows_12=[]; rows_25=[]

    brick_size_v = st.session_state.get("m12_brick_size", "25×12×6")
    mortar_v = float(st.session_state.get("m12_mortar_thickness_cm", 1.0))
    if brick_size_v == _CUSTOM_SIZE_LABEL:
        b_l = float(st.session_state.get("m12_brick_custom_l", 25.0))
        b_w = float(st.session_state.get("m12_brick_custom_w", 12.0))
        b_h = float(st.session_state.get("m12_brick_custom_h", 6.0))
    else:
        b_l, b_w, b_h = _parse_brick_size(brick_size_v)

    for wk in _get_all_walls():
        if wk in removed_walls: continue
        thick=_get_wall_thickness(wk); length=_wall_length_m(wk)
        height=_get_wall_height(wk,default_h); gross=length*height
        op=0.0
        for wi in _get_wall_windows(wk):
            if not wi.get("removed", False): op += float(wi.get("w_m", 1.0)) * float(wi.get("h_m", 1.2))
        for di in _get_wall_doors(wk):
            if not di.get("removed", False): op += float(di.get("w_m", 0.9)) * float(di.get("h_m", 2.1))
        net=max(0.0,gross-op); vol=net*(thick/100.0)
        i1,j1,i2,j2=wk
        cs=cm.get((i1,j1),f"({i1+1},{j1+1})"); ce=cm.get((i2,j2),f"({i2+1},{j2+1})")
        lname=wm.get(wk,"—"); display=f"{lname}: {cs}\u2192{ce}"
        brick_cnt = _compute_brick_qty(net, thick, b_l, b_w, b_h, mortar_v)
        row={"الحائط":display,"الطول (م)":round(length,2),"الارتفاع (م)":round(height,2),
             "المساحة الإجمالية (م2)":round(gross,2),"مساحة الفتحات (م2)":round(op,2),
             "المساحة الصافية (م2)":round(net,2),"حجم الطوب (م3)":round(vol,2),
             "عدد الطوب (وحدة)": brick_cnt}
        (rows_12 if thick==_WALL_THIN else rows_25).append(row)
    return {"rows_12":rows_12,"rows_25":rows_25}

def _totals_row(rows):
    if not rows: return {}
    tot={k:"" for k in rows[0]}; tot["الحائط"]="✅ الإجمالي"
    for k in ["المساحة الإجمالية (م2)","مساحة الفتحات (م2)","المساحة الصافية (م2)","حجم الطوب (م3)"]:
        tot[k]=round(sum(r.get(k,0) for r in rows),2)
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
    cur_brick_type = st.session_state.get("m12_brick_type", _BRICK_TYPES[0])
    if cur_brick_type not in _BRICK_TYPES:
        cur_brick_type = _BRICK_TYPES[0]

    new_brick_type = st.selectbox(
        "🧱 نوع الطوب (Brick Type)",
        options=_BRICK_TYPES,
        index=_BRICK_TYPES.index(cur_brick_type),
        key="m12_brick_type_sel"
    )
    if new_brick_type != st.session_state.get("m12_brick_type"):
        st.session_state["m12_brick_type"] = new_brick_type
        # إعادة ضبط المقاس للقيمة الأولى في النوع الجديد
        st.session_state["m12_brick_size"] = _BRICK_SIZES[new_brick_type][0]
        save_settings()
        st.rerun()

    # ── 2. مقاس الطوب (مرتبط بنوع الطوب) ──────────────────────────
    available_sizes = _BRICK_SIZES.get(st.session_state["m12_brick_type"], [])
    cur_brick_size = st.session_state.get("m12_brick_size", available_sizes[0] if available_sizes else "")
    if cur_brick_size not in available_sizes:
        cur_brick_size = available_sizes[0] if available_sizes else ""

    new_brick_size = st.selectbox(
        "📐 مقاس الطوب (Brick Size) — طول×عرض×ارتفاع (سم)",
        options=available_sizes,
        index=available_sizes.index(cur_brick_size) if cur_brick_size in available_sizes else 0,
        key="m12_brick_size_sel"
    )
    if new_brick_size != st.session_state.get("m12_brick_size"):
        st.session_state["m12_brick_size"] = new_brick_size
        save_settings()

    # ── 3. مقاس مخصص ────────────────────────────────────────────────
    if st.session_state.get("m12_brick_size") == _CUSTOM_SIZE_LABEL:
        st.markdown("<span style='font-size:0.88rem;color:#1d4ed8;font-weight:bold;'>🔧 إدخال مقاس مخصص (سم):</span>", unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns(3)
        new_cl = cc1.number_input("الطول (L)", min_value=5.0, max_value=200.0,
                                   value=float(st.session_state.get("m12_brick_custom_l", 25.0)),
                                   step=0.5, format="%.1f", key="m12_brick_cl")
        new_cw = cc2.number_input("العرض (W)", min_value=5.0, max_value=100.0,
                                   value=float(st.session_state.get("m12_brick_custom_w", 12.0)),
                                   step=0.5, format="%.1f", key="m12_brick_cw")
        new_ch = cc3.number_input("الارتفاع (H)", min_value=2.0, max_value=50.0,
                                   value=float(st.session_state.get("m12_brick_custom_h", 6.0)),
                                   step=0.5, format="%.1f", key="m12_brick_ch")
        changed = False
        if abs(new_cl - st.session_state.get("m12_brick_custom_l", 25.0)) > 0.01: st.session_state["m12_brick_custom_l"] = new_cl; changed = True
        if abs(new_cw - st.session_state.get("m12_brick_custom_w", 12.0)) > 0.01: st.session_state["m12_brick_custom_w"] = new_cw; changed = True
        if abs(new_ch - st.session_state.get("m12_brick_custom_h", 6.0)) > 0.01:  st.session_state["m12_brick_custom_h"] = new_ch; changed = True
        if changed: save_settings()

    # ── 4. سمك فاصل المونة ───────────────────────────────────────────
    st.markdown("<span style='font-size:0.88rem;color:#555;'>━━━━━━━━━━━━━━━━━━━━━━━━━━</span>", unsafe_allow_html=True)
    cur_mortar = float(st.session_state.get("m12_mortar_thickness_cm", 1.0))
    new_mortar = st.number_input(
        "🔩 سمك فاصل المونة (سم) — القيمة الافتراضية 1.0 سم",
        min_value=0.3, max_value=3.0, value=cur_mortar, step=0.1, format="%.1f",
        key="m12_mortar_input",
        help="متوسط سمك فاصل المونة بين وحدات الطوب المتجاورة. لا يُضاف للأبعاد الفعلية للطوبة."
    )
    if abs(new_mortar - cur_mortar) > 0.01:
        st.session_state["m12_mortar_thickness_cm"] = new_mortar
        save_settings()

    # ── 5. عرض معلومات المقاس الحالي ─────────────────────────────────
    brick_type_v = st.session_state.get("m12_brick_type", "")
    brick_size_v = st.session_state.get("m12_brick_size", "")
    mortar_v = float(st.session_state.get("m12_mortar_thickness_cm", 1.0))
    if brick_size_v == _CUSTOM_SIZE_LABEL:
        bl = st.session_state.get("m12_brick_custom_l", 25.0)
        bw = st.session_state.get("m12_brick_custom_w", 12.0)
        bh = st.session_state.get("m12_brick_custom_h", 6.0)
        size_display = f"{bl}×{bw}×{bh} سم (مخصص)"
    else:
        size_display = f"{brick_size_v} سم"
        bl, bw, bh = _parse_brick_size(brick_size_v)
    # حساب عدد وحدات تقريبي لكل م²
    upm2 = (100.0 / (bl + mortar_v)) * (100.0 / (bh + mortar_v)) if bl > 0 and bh > 0 else 0
    st.markdown(
        f"""<div dir='rtl' style='background:#f0fdf4;border:1px solid #86efac;border-radius:6px;
            padding:8px 12px;margin-top:6px;font-size:0.85rem;'>
            <b style='color:#15803d;'>📊 ملخص الطوب الحالي:</b><br>
            النوع: <b>{brick_type_v}</b> &nbsp;|&nbsp; المقاس: <b>{size_display}</b>
            &nbsp;|&nbsp; المونة: <b>{mortar_v} سم</b><br>
            <span style='color:#166534;'>عدد الطوب التقريبي لكل م² (وجه الحائط):
            <b>≈ {upm2:.1f} وحدة</b></span>
        </div>""",
        unsafe_allow_html=True
    )


def _section_opening_types():
    """
    قسم تعريف نماذج الشبابيك والأبواب (Window/Door Types).
    يُحدد المستخدم هنا أبعاد كل نموذج (W1، W2...) و(D1، D2...).
    الإسقاط الفعلي على الحوائط يتم لاحقاً في _section_openings().
    """
    # ── نماذج الشبابيك ──────────────────────────────────────────────
    st.markdown("<b style='color:#1565C0;font-size:0.95rem;'>🪟 تعريف نماذج الشبابيك (Window Types)</b>", unsafe_allow_html=True)

    win_types = st.session_state.get("m12_window_types", [])
    n_win_types = st.number_input(
        "عدد نماذج الشبابيك",
        min_value=0, max_value=20, value=len(win_types), step=1,
        key="m12_n_win_types"
    )
    n_win_types = int(n_win_types)

    # تعديل الحجم إذا تغير العدد
    while len(win_types) < n_win_types:
        n = len(win_types) + 1
        win_types.append({"id": f"wt_{n}", "label": f"W{n}", "w_cm": 100.0, "h_cm": 120.0, "sill_cm": 90.0})
    while len(win_types) > n_win_types:
        win_types.pop()

    changed_wt = False
    for i, wt in enumerate(win_types):
        lbl = wt.get("label", f"W{i+1}")
        with st.expander(f"🪟 نموذج {lbl}", expanded=True):
            wc1, wc2, wc3 = st.columns(3)
            new_wl = wc1.number_input(f"عرض الشباك (سم) — {lbl}", min_value=20.0, max_value=500.0,
                                       value=float(wt.get("w_cm", 100.0)), step=5.0, format="%.0f",
                                       key=f"m12_wt_w_{i}")
            new_wh = wc2.number_input(f"ارتفاع الشباك (سم) — {lbl}", min_value=20.0, max_value=400.0,
                                       value=float(wt.get("h_cm", 120.0)), step=5.0, format="%.0f",
                                       key=f"m12_wt_h_{i}")
            new_ws = wc3.number_input(f"ارتفاع جلسة الشباك Sill (سم) — {lbl}", min_value=0.0, max_value=300.0,
                                       value=float(wt.get("sill_cm", 90.0)), step=5.0, format="%.0f",
                                       key=f"m12_wt_sill_{i}")
            if abs(new_wl - wt.get("w_cm", 100.0)) > 0.1 or abs(new_wh - wt.get("h_cm", 120.0)) > 0.1 or abs(new_ws - wt.get("sill_cm", 90.0)) > 0.1:
                wt["w_cm"] = new_wl; wt["h_cm"] = new_wh; wt["sill_cm"] = new_ws
                changed_wt = True
            st.caption(f"📐 {lbl}: {new_wl:.0f}سم × {new_wh:.0f}سم | جلسة: {new_ws:.0f}سم "
                       f"({new_wl/100:.2f}م × {new_wh/100:.2f}م)")

    if changed_wt or win_types != st.session_state.get("m12_window_types", []):
        st.session_state["m12_window_types"] = win_types
        save_settings()

    st.divider()

    # ── نماذج الأبواب ───────────────────────────────────────────────
    st.markdown("<b style='color:#2E7D32;font-size:0.95rem;'>🚪 تعريف نماذج الأبواب (Door Types)</b>", unsafe_allow_html=True)

    door_types = st.session_state.get("m12_door_types", [])
    n_door_types = st.number_input(
        "عدد نماذج الأبواب",
        min_value=0, max_value=20, value=len(door_types), step=1,
        key="m12_n_door_types"
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
        with st.expander(f"🚪 نموذج {lbl}", expanded=True):
            dc1, dc2 = st.columns(2)
            new_dw = dc1.number_input(f"عرض الباب (سم) — {lbl}", min_value=50.0, max_value=400.0,
                                       value=float(dt.get("w_cm", 90.0)), step=5.0, format="%.0f",
                                       key=f"m12_dt_w_{i}")
            new_dh = dc2.number_input(f"ارتفاع الباب (سم) — {lbl}", min_value=150.0, max_value=400.0,
                                       value=float(dt.get("h_cm", 210.0)), step=5.0, format="%.0f",
                                       key=f"m12_dt_h_{i}")
            if abs(new_dw - dt.get("w_cm", 90.0)) > 0.1 or abs(new_dh - dt.get("h_cm", 210.0)) > 0.1:
                dt["w_cm"] = new_dw; dt["h_cm"] = new_dh
                changed_dt = True
            st.caption(f"📐 {lbl}: {new_dw:.0f}سم × {new_dh:.0f}سم ({new_dw/100:.2f}م × {new_dh/100:.2f}م)")

    if changed_dt or door_types != st.session_state.get("m12_door_types", []):
        st.session_state["m12_door_types"] = door_types
        save_settings()

def _section_axes():
    col_x, col_y = st.columns(2)
    with col_x:
        st.markdown(f"<b style='color:{_CLR_AXIS_X};font-size:0.9rem;'>محاور X (م)</b>", unsafe_allow_html=True)
        n_x = st.number_input("عدد محاور X", min_value=2, max_value=20, value=len(st.session_state["m12_x_axes"]), step=1, key="m12_n_x")
        x_vals = []
        cxs = st.session_state["m12_x_axes"]
        for row_start in range(0, int(n_x), 4):
            chunk = range(row_start, min(row_start + 4, int(n_x)))
            cols = st.columns(4)
            for ci, idx in enumerate(chunk):
                dv = cxs[idx] if idx < len(cxs) else (cxs[-1] + 3.0 if cxs else float(idx * 3))
                v = cols[ci].number_input(f"X{idx+1}", value=float(dv), step=0.25, format="%.2f", key=f"m12_x_val_{idx}")
                x_vals.append(v)
        if sorted(x_vals) != x_vals:
            st.warning("⚠️ قيم محاور X يجب أن تكون متصاعدة!")
        elif len(set(round(v, 4) for v in x_vals)) < len(x_vals):
            st.warning("⚠️ لا يمكن تكرار قيمة محور X!")
        else:
            if x_vals != cxs:
                st.session_state["m12_x_axes"] = x_vals
                save_settings()
    with col_y:
        st.markdown(f"<b style='color:{_CLR_AXIS_Y};font-size:0.9rem;'>محاور Y (م)</b>", unsafe_allow_html=True)
        n_y = st.number_input("عدد محاور Y", min_value=2, max_value=20, value=len(st.session_state["m12_y_axes"]), step=1, key="m12_n_y")
        y_vals = []
        cys = st.session_state["m12_y_axes"]
        for row_start in range(0, int(n_y), 4):
            chunk = range(row_start, min(row_start + 4, int(n_y)))
            cols = st.columns(4)
            for ci, idx in enumerate(chunk):
                dv = cys[idx] if idx < len(cys) else (cys[-1] + 3.0 if cys else float(idx * 3))
                v = cols[ci].number_input(f"Y{idx+1}", value=float(dv), step=0.25, format="%.2f", key=f"m12_y_val_{idx}")
                y_vals.append(v)
        if sorted(y_vals) != y_vals:
            st.warning("⚠️ قيم محاور Y يجب أن تكون متصاعدة!")
        elif len(set(round(v, 4) for v in y_vals)) < len(y_vals):
            st.warning("⚠️ لا يمكن تكرار قيمة محور Y!")
        else:
            if y_vals != cys:
                st.session_state["m12_y_axes"] = y_vals
                save_settings()

def _section_columns():
    xs=st.session_state["m12_x_axes"]; ys=st.session_state["m12_y_axes"]
    if not xs or not ys: st.info("أدخل المحاور أولاً."); return

    # ── أبعاد الأعمدة الموحدة المعتمدة لكافة أعمدة المشروع ──
    def _on_col_dim_change():
        new_l = float(st.session_state.get("m12_col_length_input", 60.0))
        new_w = float(st.session_state.get("m12_col_width_input", 30.0))
        st.session_state["m12_col_length_cm"] = new_l
        st.session_state["m12_col_width_cm"] = new_w
        col_shifts = st.session_state.get("m12_col_shifts", {})
        col_shifted = st.session_state.get("m12_col_shifted", {})
        for k, tr in col_shifts.items():
            if isinstance(k, tuple) and len(k) == 2:
                cw, ch = _get_col_wh(k[0], k[1])
                dx_m, dy_m = _compute_col_offsets(cw, ch, tr.get("shift_x"), tr.get("shift_y"))
                col_shifted[k] = (dx_m * 100.0, dy_m * 100.0)
        st.session_state["m12_col_shifted"] = col_shifted
        save_settings()

    col_dim1, col_dim2 = st.columns(2)
    with col_dim1:
        cur_l = float(st.session_state.get("m12_col_length_cm", 60.0))
        if "m12_col_length_input" not in st.session_state:
            st.session_state["m12_col_length_input"] = cur_l
        val_l = st.number_input(
            "طول العمود سم",
            min_value=15.0,
            max_value=300.0,
            value=float(st.session_state.get("m12_col_length_input", cur_l)),
            step=5.0,
            format="%.1f",
            key="m12_col_length_input",
            on_change=_on_col_dim_change,
            help="طول العمود المعتمد لجميع الأعمدة بالسنتمتر (افتراضي: 60 سم)"
        )
        if abs(val_l - cur_l) > 0.01:
            st.session_state["m12_col_length_cm"] = val_l
            save_settings()

    with col_dim2:
        cur_w = float(st.session_state.get("m12_col_width_cm", 30.0))
        if "m12_col_width_input" not in st.session_state:
            st.session_state["m12_col_width_input"] = cur_w
        val_w = st.number_input(
            "عرض العمود سم",
            min_value=12.0,
            max_value=200.0,
            value=float(st.session_state.get("m12_col_width_input", cur_w)),
            step=5.0,
            format="%.1f",
            key="m12_col_width_input",
            on_change=_on_col_dim_change,
            help="عرض العمود المعتمد لجميع الأعمدة بالسنتمتر (افتراضي: 30 سم)"
        )
        if abs(val_w - cur_w) > 0.01:
            st.session_state["m12_col_width_cm"] = val_w
            save_settings()

    st.markdown("<hr style='margin: 8px 0 14px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

    removed_cols=st.session_state["m12_col_removed"]; col_dirs=st.session_state["m12_col_dirs"]
    col_shifted=st.session_state["m12_col_shifted"]; cn=_get_col_name_map()
    all_cols=[(i,j) for j in range(len(ys)) for i in range(len(xs))]
    def _clbl(k):
        i, j = all_cols[k]
        orig_cname = f"C{j * len(xs) + i + 1}"
        if (i, j) in removed_cols:
            return f"🗑️ {orig_cname} محذوف (X{i+1},Y{j+1}) — X{i+1}={xs[i]:.2f}م, Y{j+1}={ys[j]:.2f}م"
        nm = cn.get((i, j), orig_cname)
        return f"✅ {nm} — X{i+1}={xs[i]:.2f}م, Y{j+1}={ys[j]:.2f}م"
    _safe_idx("m12_sel_col", len(all_cols))
    sel = st.selectbox("اختر عموداً", options=range(len(all_cols)), format_func=_clbl, key="m12_sel_col")
    si,sj=all_cols[sel]; is_rem=(si,sj) in removed_cols
    cur_dir=col_dirs.get((si,sj),"NS"); dx,dy=col_shifted.get((si,sj),(0.0,0.0))
    orig_cname = f"C{sj * len(xs) + si + 1}"
    cname = cn.get((si, sj), orig_cname)
    if is_rem:
        st.error(f"🗑️ العمود **{orig_cname}** عند تقاطع (X{si+1}, Y{sj+1}) محذوف — الحوائط قائمة ومستمرة.")

    # ── رسالة تأكيد الحذف بعرض كامل الحاوية لتجنب تكسر الكلمات ──
    if not is_rem and st.session_state.get("m12_confirm_del_col") == (si,sj):
        st.warning(f"⚠️ تأكيد حذف العمود {cname}؟ سيتم إزالة العمود الخرساني مع بقاء الحوائط قائمة على المحاور.")
        cyes, cno = st.columns(2)
        with cyes:
            if st.button("✅ نعم، تأكيد حذف العمود", type="primary", key="m12_confirm_del_yes", use_container_width=True):
                removed_cols.add((si,sj)); st.session_state["m12_col_removed"]=removed_cols
                save_settings()
                st.session_state.pop("m12_confirm_del_col",None); st.rerun()
        with cno:
            if st.button("❌ إلغاء", key="m12_confirm_del_no", use_container_width=True):
                st.session_state.pop("m12_confirm_del_col",None); st.rerun()

    col_shifts = st.session_state.setdefault("m12_col_shifts", {})
    cur_tr = col_shifts.get((si, sj))
    if not cur_tr:
        leg_dx, leg_dy = col_shifted.get((si, sj), (0.0, 0.0))
        sx_init = M12_SHIFT_X_OPTIONS[0]
        if leg_dx > 0.01:
            sx_init = M12_SHIFT_X_OPTIONS[1]
        elif leg_dx < -0.01:
            sx_init = M12_SHIFT_X_OPTIONS[2]

        sy_init = M12_SHIFT_Y_OPTIONS[0]
        if leg_dy > 0.01:
            sy_init = M12_SHIFT_Y_OPTIONS[1]
        elif leg_dy < -0.01:
            sy_init = M12_SHIFT_Y_OPTIONS[2]
        cur_tr = {"shift_x": sx_init, "shift_y": sy_init}
        col_shifts[(si, sj)] = cur_tr

    norm_cur_sx = _normalize_m12_col_shift(cur_tr.get("shift_x"), axis="x")
    norm_cur_sy = _normalize_m12_col_shift(cur_tr.get("shift_y"), axis="y")

    row1_c1, row1_c2 = st.columns([1, 1])
    with row1_c1:
        if is_rem:
            if st.button(f"♻️ استعادة العمود {orig_cname}", key="m12_restore_col", use_container_width=True):
                if si < len(xs) and sj < len(ys):
                    removed_cols.discard((si, sj)); st.session_state["m12_col_removed"] = removed_cols
                    save_settings()
                    st.session_state.pop("m12_confirm_del_col", None)
                    st.success(f"✅ تم استعادة العمود {orig_cname} بنجاح.")
                    st.rerun()
                else:
                    st.error("🚨 لا يمكن استعادة العمود: المحاور التي يقع عليها العمود لم تعد موجودة في شبكة المحاور!")
        else:
            if st.session_state.get("m12_confirm_del_col") != (si, sj):
                if st.button("🗑️ حذف العمود", key="m12_del_col", use_container_width=True):
                    st.session_state["m12_confirm_del_col"] = (si, sj)
                    st.rerun()

    with row1_c2:
        nd = st.radio(
            "ضرب العمود (الاتجاه)",
            options=["NS", "EW"],
            format_func=lambda d: "NS (طولي موازٍ لـ Y)" if d == "NS" else "EW (عرضي موازٍ لـ X)",
            index=0 if cur_dir == "NS" else 1,
            horizontal=True,
            key=f"m12_col_dir_radio_{si}_{sj}",
            help="NS: البعد الأكبر موازٍ لمحور Y / EW: البعد الأكبر موازٍ لمحور X"
        )
        if nd != cur_dir:
            col_dirs[(si, sj)] = nd
            st.session_state["m12_col_dirs"] = col_dirs
            cw_now, ch_now = _get_col_wh(si, sj)
            dx_m, dy_m = _compute_col_offsets(cw_now, ch_now, norm_cur_sx, norm_cur_sy)
            col_shifted[(si, sj)] = (dx_m * 100.0, dy_m * 100.0)
            st.session_state["m12_col_shifted"] = col_shifted
            save_settings()
            st.rerun()

    row2_c1, row2_c2 = st.columns(2)
    with row2_c1:
        idx_sx = M12_SHIFT_X_OPTIONS.index(norm_cur_sx) if norm_cur_sx in M12_SHIFT_X_OPTIONS else 0
        sel_sx = st.selectbox(
            "الترحيل الأفقي (X)",
            options=M12_SHIFT_X_OPTIONS,
            index=idx_sx,
            key=f"m12_col_shift_x_{si}_{sj}",
            help="الترحيل الأفقي بالنسبة للمحور الرأسي X (6 سم)."
        )

    with row2_c2:
        idx_sy = M12_SHIFT_Y_OPTIONS.index(norm_cur_sy) if norm_cur_sy in M12_SHIFT_Y_OPTIONS else 0
        sel_sy = st.selectbox(
            "الترحيل الرأسي (Y)",
            options=M12_SHIFT_Y_OPTIONS,
            index=idx_sy,
            key=f"m12_col_shift_y_{si}_{sj}",
            help="الترحيل الرأسي بالنسبة للمحور الأفقي Y (6 سم)."
        )

    norm_new_sx = _normalize_m12_col_shift(sel_sx, axis="x")
    norm_new_sy = _normalize_m12_col_shift(sel_sy, axis="y")
    if norm_new_sx != norm_cur_sx or norm_new_sy != norm_cur_sy:
        col_shifts[(si, sj)] = {"shift_x": norm_new_sx, "shift_y": norm_new_sy}
        st.session_state["m12_col_shifts"] = col_shifts
        cw_now, ch_now = _get_col_wh(si, sj)
        dx_m, dy_m = _compute_col_offsets(cw_now, ch_now, norm_new_sx, norm_new_sy)
        col_shifted[(si, sj)] = (dx_m * 100.0, dy_m * 100.0)
        st.session_state["m12_col_shifted"] = col_shifted
        save_settings()
        st.rerun()

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
    xs = st.session_state["m12_x_axes"]
    ys = st.session_state["m12_y_axes"]
    if len(xs) < 2 or len(ys) < 2:
        st.info("أدخل على الأقل محورين في كل اتجاه.")
        return

    removed_walls = st.session_state["m12_wall_removed"]
    wall_thick = st.session_state["m12_wall_thickness"]
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    all_walls = _get_all_walls()
    if not all_walls:
        st.info("لا توجد حوائط متصلة بين الأعمدة.")
        return

    active_walls = [wk for wk in all_walls if wk not in removed_walls]
    parapet_walls = set(st.session_state.get("m12_parapet_walls", set()))

    def _on_default_h_change():
        new_dh = float(st.session_state.get("m12_default_h_input", 3.0))
        st.session_state["m12_default_wall_height"] = new_dh
        new_ph = float(st.session_state.get("m12_parapet_wall_height", st.session_state.get("m12_parapet_h_input", 1.0)))
        wh = st.session_state.get("m12_wall_heights", {})
        for w_item in _get_all_walls():
            wh[w_item] = new_ph if _is_parapet_wall(w_item) else new_dh
        st.session_state["m12_wall_heights"] = wh
        save_settings()

    def _on_parapet_h_change():
        new_ph = float(st.session_state.get("m12_parapet_h_input", 1.0))
        st.session_state["m12_parapet_wall_height"] = new_ph
        new_dh = float(st.session_state.get("m12_default_wall_height", st.session_state.get("m12_default_h_input", 3.0)))
        wh = st.session_state.get("m12_wall_heights", {})
        for w_item in _get_all_walls():
            wh[w_item] = new_ph if _is_parapet_wall(w_item) else new_dh
        st.session_state["m12_wall_heights"] = wh
        save_settings()

    # ── 1. مدخلات الارتفاعات الرئيسية (Height Inputs) ──
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        cur_dh = float(st.session_state.get("m12_default_wall_height", 3.0))
        if "m12_default_h_input" not in st.session_state:
            st.session_state["m12_default_h_input"] = cur_dh
        dh = st.number_input(
            "ارتفاع الحائط (Wall Height)",
            min_value=0.5,
            max_value=8.0,
            value=float(st.session_state.get("m12_default_h_input", cur_dh)),
            step=0.1,
            format="%.2f",
            key="m12_default_h_input",
            on_change=_on_default_h_change,
            help="الارتفاع الافتراضي لجميع الحوائط في المشروع كارتفاع أساسي للبثق ثلاثي الأبعاد والحسابات (ترثه L1, L2, ... تلقائياً)"
        )
        if abs(dh - cur_dh) > 0.001:
            st.session_state["m12_default_wall_height"] = dh
            save_settings()

    with col_h2:
        cur_ph = float(st.session_state.get("m12_parapet_wall_height", 1.0))
        if "m12_parapet_h_input" not in st.session_state:
            st.session_state["m12_parapet_h_input"] = cur_ph
        ph = st.number_input(
            "ارتفاع دروة",
            min_value=0.2,
            max_value=5.0,
            value=float(st.session_state.get("m12_parapet_h_input", cur_ph)),
            step=0.05,
            format="%.2f",
            key="m12_parapet_h_input",
            on_change=_on_parapet_h_change,
            help="ارتفاع الاستثناء المطبق فقط على الحوائط المحددة كدروة، متجاوزاً القيمة الافتراضية"
        )
        if abs(ph - cur_ph) > 0.001:
            st.session_state["m12_parapet_wall_height"] = ph
            save_settings()

    # مزامنة سريعة لـ m12_wall_heights لضمان تطابق البيانات
    wall_heights = st.session_state.get("m12_wall_heights", {})
    for wk in all_walls:
        wall_heights[wk] = ph if _is_parapet_wall(wk) else dh
    st.session_state["m12_wall_heights"] = wall_heights

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    # ── 2. قائمة اختيار متعدد / Check-list لحوائط الدروة ──
    current_selected = [wk for wk in active_walls if wk in parapet_walls]

    def _on_parapet_ms_change():
        selected = st.session_state.get("m12_parapet_multiselect_widget", [])
        new_pw = set(selected)
        st.session_state["m12_parapet_walls"] = new_pw
        wh = st.session_state.get("m12_wall_heights", {})
        c_ph = float(st.session_state.get("m12_parapet_wall_height", st.session_state.get("m12_parapet_h_input", 1.0)))
        c_dh = float(st.session_state.get("m12_default_wall_height", st.session_state.get("m12_default_h_input", 3.0)))
        for w_item in _get_all_walls():
            wh[w_item] = c_ph if w_item in new_pw else c_dh
        st.session_state["m12_wall_heights"] = wh
        save_settings()

    if "m12_parapet_multiselect_widget" not in st.session_state or set(st.session_state.get("m12_parapet_multiselect_widget", [])) != parapet_walls:
        st.session_state["m12_parapet_multiselect_widget"] = current_selected

    def _format_wall_item(wk):
        lname = wm.get(wk, "—")
        i1, j1, i2, j2 = wk
        cs = cm.get((i1, j1), f"({i1+1},{j1+1})")
        ce = cm.get((i2, j2), f"({i2+1},{j2+1})")
        return f"{lname}: {cs} \u2192 {ce}"

    st.multiselect(
        "📋 قائمة اختيار حوائط الدروة:",
        options=active_walls,
        format_func=_format_wall_item,
        key="m12_parapet_multiselect_widget",
        on_change=_on_parapet_ms_change,
        help="الحوائط المحددة (Checked) تُصنف فوراً كدروة وتأخذ قيمة 'ارتفاع دروة'. الحوائط غير المحددة تستمر تلقائياً باعتماد قيمة 'ارتفاع الحائط'."
    )



    # ── 3. فاحص ومعدل الحائط الفردي (Single Wall Inspector) ──
    _safe_idx("m12_sel_wall", len(all_walls) + 1)
    def _wlbl(k):
        if k == 0:
            return "لم يتم اختيار حائط"
        wk = all_walls[k - 1]
        st2 = "🗑️ " if wk in removed_walls else ("🧱 [دروة] " if _is_parapet_wall(wk) else "")
        return st2 + _wall_display_label(wk, cm, wm)

    sel = st.selectbox("اختر حائطاً لمعاينة وتعديل خصائصه", options=range(len(all_walls) + 1), format_func=_wlbl, key="m12_sel_wall")
    if sel != 0:
        wk = all_walls[sel - 1]
        is_rem = wk in removed_walls
        tc = _get_wall_thickness(wk)
        wlen = _wall_length_m(wk)
        is_p_wall = _is_parapet_wall(wk)

        # ── تأكيد حذف الحائط ──
        if not is_rem and st.session_state.get("m12_confirm_del_wall") == wk:
            st.warning(f"⚠️ تأكيد حذف الحائط {_wall_display_label(wk, cm, wm)}؟ يمكن استعادته لاحقاً.")
            cyes, cno = st.columns(2)
            with cyes:
                if st.button("✅ نعم، تأكيد حذف الحائط", type="primary", key="m12_conf_wall_yes", use_container_width=True):
                    removed_walls.add(wk)
                    st.session_state["m12_wall_removed"] = removed_walls
                    st.session_state.pop("m12_confirm_del_wall", None)
                    save_settings()
                    st.rerun()
            with cno:
                if st.button("❌ إلغاء", key="m12_conf_wall_no", use_container_width=True):
                    st.session_state.pop("m12_confirm_del_wall", None)
                    st.rerun()

        # ── الاختيارات الثلاث للتحكم في الحائط المختار ──
        st.markdown(
            """<style>
            /* ═══════════════════════════════════════════════════════════════════
               1. حاوية وبطاقات سُمك الحائط (العمود الأول)
               ═══════════════════════════════════════════════════════════════════ */
            div[class*="m12_wall_thick_radio"],
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
            div[class*="m12_wall_thick_radio"] > div[data-testid="stRadio"] {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
                margin: 0 !important;
                width: 100% !important;
            }
            /* عنوان سُمك الحائط داخل أعلى البانيل */
            div[class*="m12_wall_thick_radio"] label[data-testid="stWidgetLabel"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
                display: block !important;
                width: 100% !important;
                text-align: center !important;
                margin: 0 0 5px 0 !important;
                padding: 0 !important;
            }
            div[class*="m12_wall_thick_radio"] label[data-testid="stWidgetLabel"] p,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] p {
                color: #fde047 !important;
                font-size: 13.5px !important;
                font-weight: 700 !important;
                text-align: center !important;
                margin: 0 !important;
                line-height: 1.25 !important;
            }
            /* صف خيارات الراديو */
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"],
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
            /* بطاقات خيارات سُمك الحائط (12 سم و 25 سم) */
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label,
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
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label:hover,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
                border-color: #fde047 !important;
                background: rgba(51, 65, 85, 0.95) !important;
            }
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label[data-selected="true"],
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label:has(input:checked),
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label[data-selected="true"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
                background: rgba(2, 132, 199, 0.35) !important;
                border-color: #38bdf8 !important;
            }
            /* دوائر الراديو الخارجية - بيضاء ناصعة مع إطار رمادي واضح */
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label div[class*="etak9234"],
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label > div > div > div:first-child,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label div[class*="etak9234"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label > div > div > div:first-child {
                background-color: #ffffff !important;
                border: 2px solid #94a3b8 !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35) !important;
                border-radius: 50% !important;
                width: 16px !important;
                height: 16px !important;
                min-width: 16px !important;
                min-height: 16px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* الدائرة الخارجية عند الاختيار */
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label[data-selected="true"] div[class*="etak9234"],
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label:has(input:checked) div[class*="etak9234"],
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label[data-selected="true"] > div > div > div:first-child,
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label:has(input:checked) > div > div > div:first-child,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label[data-selected="true"] div[class*="etak9234"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) div[class*="etak9234"] {
                border-color: #0284c7 !important;
                background-color: #ffffff !important;
                box-shadow: 0 0 8px rgba(2, 132, 199, 0.6) !important;
            }
            /* النقطة الداخلية */
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label div[class*="etak9235"],
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label > div > div > div:first-child > div,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label div[class*="etak9235"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label > div > div > div:first-child > div {
                background-color: #ffffff !important;
                border-radius: 50% !important;
                width: 7px !important;
                height: 7px !important;
            }
            /* النقطة الداخلية عند الاختيار - أزرق سماوي */
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label[data-selected="true"] div[class*="etak9235"],
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label:has(input:checked) div[class*="etak9235"],
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label[data-selected="true"] > div > div > div:first-child > div,
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label:has(input:checked) > div > div > div:first-child > div,
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label[data-selected="true"] div[class*="etak9235"],
            div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) div[class*="etak9235"] {
                background-color: #0284c7 !important;
            }
            /* نصوص خيارات الراديو (12 سم و 25 سم) - استهداف دقيق لـ p فقط دون المساس بـ span */
            div[class*="m12_wall_thick_radio"] div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p,
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
            div[class*="st-key-m12_single_parapet_chk"],
            div.stCheckbox[class*="st-key-m12_single_parapet_chk"],
            div.stCheckbox:has(input[id*="m12_single_parapet_chk"]),
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
            div[class*="st-key-m12_single_parapet_chk"] label,
            div.stCheckbox[class*="st-key-m12_single_parapet_chk"] label,
            div.stCheckbox:has(input[id*="m12_single_parapet_chk"]) label,
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
            div[class*="st-key-m12_single_parapet_chk"] label p,
            div.stCheckbox[class*="st-key-m12_single_parapet_chk"] label p,
            div.stCheckbox:has(input[id*="m12_single_parapet_chk"]) label p,
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stCheckbox"] label p {
                color: #fde047 !important;
                font-size: 13.5px !important;
                font-weight: 700 !important;
                text-align: center !important;
                line-height: 1.25 !important;
                white-space: nowrap !important;
                margin: 0 !important;
            }
            /* مربع الاختيار (Checkbox Square) - أبيض ناصع مع إطار رمادي واضح */
            div[class*="st-key-m12_single_parapet_chk"] label div[class*="ew2p8o3"],
            div[class*="st-key-m12_single_parapet_chk"] label > div:not([data-testid="stWidgetLabel"]),
            div.stCheckbox:has(input[id*="m12_single_parapet_chk"]) label div[class*="ew2p8o3"],
            div.stCheckbox:has(input[id*="m12_single_parapet_chk"]) label > div:not([data-testid="stWidgetLabel"]),
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stCheckbox"] label > div:not([data-testid="stWidgetLabel"]) {
                background-color: #ffffff !important;
                border: 2px solid #94a3b8 !important;
                border-radius: 4px !important;
                width: 17px !important;
                height: 17px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
                margin: 0 !important;
            }
            /* عند تفعيل حائط دروة (Checked) */
            div[class*="st-key-m12_single_parapet_chk"] label:has(input:checked) div[class*="ew2p8o3"],
            div[class*="st-key-m12_single_parapet_chk"] label:has(input:checked) > div:not([data-testid="stWidgetLabel"]),
            div.stCheckbox:has(input[id*="m12_single_parapet_chk"]) label:has(input:checked) div[class*="ew2p8o3"],
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stCheckbox"] label:has(input:checked) > div:not([data-testid="stWidgetLabel"]) {
                background-color: #0284c7 !important;
                border-color: #38bdf8 !important;
                box-shadow: 0 0 8px rgba(2, 132, 199, 0.5) !important;
            }
            div[class*="st-key-m12_single_parapet_chk"] label:has(input:checked) svg polyline,
            div.stCheckbox:has(input[id*="m12_single_parapet_chk"]) label:has(input:checked) svg polyline,
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stCheckbox"] label:has(input:checked) svg polyline {
                stroke: #ffffff !important;
            }

            /* ═══════════════════════════════════════════════════════════════════
               3. زر الحذف/الاستعادة (العمود الثالث)
               ═══════════════════════════════════════════════════════════════════ */
            .stButton:has(button[key="m12_del_wall"]) > button,
            .stButton:has(button[key="m12_restore_wall"]) > button,
            .stButton:has(button[key="m12_del_wall_dis"]) > button,
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

        # صف التحكم التفاعلي في الحائط المختار (3 أعمدة متوازنة الارتفاع)
        c1, c2, c3 = st.columns([1.3, 1.3, 1.0], vertical_alignment="center")
        with c1:
            nt = st.radio(
                "سُمك الحائط",
                options=[_WALL_THIN, _WALL_THICK],
                index=0 if tc == _WALL_THIN else 1,
                format_func=lambda v: f"{v} سم",
                horizontal=True,
                label_visibility="visible",
                key=f"m12_wall_thick_radio_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}",
                disabled=is_rem
            )
            if nt != tc and not is_rem:
                wall_thick[wk] = nt
                st.session_state["m12_wall_thickness"] = wall_thick
                save_settings()

        with c2:
            new_is_p = st.checkbox(
                "تفعيل كحائط دروة",
                value=is_p_wall,
                key=f"m12_single_parapet_chk_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}",
                help="عند التحديد، يأخذ هذا الحائط ارتفاع دروة تلقائياً",
                disabled=is_rem
            )
            if new_is_p != is_p_wall and not is_rem:
                pw_set = set(st.session_state.get("m12_parapet_walls", set()))
                if new_is_p:
                    pw_set.add(wk)
                else:
                    pw_set.discard(wk)
                st.session_state["m12_parapet_walls"] = pw_set
                for w_item in all_walls:
                    wall_heights[w_item] = ph if w_item in pw_set else dh
                st.session_state["m12_wall_heights"] = wall_heights
                save_settings()
                st.rerun()

        with c3:
            if is_rem:
                if st.button("♻️ استعادة الحائط", key="m12_restore_wall", use_container_width=True, type="primary"):
                    removed_walls.discard(wk)
                    st.session_state["m12_wall_removed"] = removed_walls
                    save_settings()
                    st.rerun()
            else:
                if st.session_state.get("m12_confirm_del_wall") != wk:
                    if st.button("🗑️ حذف الحائط", key="m12_del_wall", use_container_width=True):
                        st.session_state["m12_confirm_del_wall"] = wk
                        st.rerun()
                else:
                    st.button("⏳ تأكيد الحذف بالأعلى", key="m12_del_wall_dis", disabled=True, use_container_width=True)

        if is_rem:
            st.warning(f"🗑️ الحائط '{_wlbl(sel)}' محذوف حالياً (يظهر كخط استرشادي رمادي فقط ولا يُحسب في الحصر الهندسـي).")

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

def _section_openings():
    all_walls = _get_all_walls()
    removed_walls = st.session_state["m12_wall_removed"]
    active = [w for w in all_walls if w not in removed_walls]
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    _ensure_opening_names()

    # ── عرض شاشة التأكيد الخضراء عند اعتماد وتثبيت الفتحة ──
    success_info = st.session_state.get("m12_commit_success_msg")
    if success_info:
        _render_opening_commit_success_banner(success_info)
        return

    # ── مزامنة التبويب النشط واختيار الحائط مع كائن المعاينة المؤقت قبل إنشاء الـ widgets ──
    curr_prev = st.session_state.get("m12_preview_opening")
    if st.session_state.pop("m12_sync_preview_on_next_run", False) and curr_prev and curr_prev.get("wk"):
        p_kind = curr_prev.get("kind")
        p_wk = curr_prev.get("wk")
        p_pos = float(curr_prev.get("pos_m", 0.0))
        if p_kind == "door":
            st.session_state["m12_openings_active_tab"] = "🚪 أبواب"
            st.session_state["m12_door_preview_disabled"] = False
            if p_wk in active:
                st.session_state["m12_openings_door_wall_sel"] = active.index(p_wk) + 1
            d_key = f"m12_add_new_door_offset_{p_wk[0]}_{p_wk[1]}_{p_wk[2]}_{p_wk[3]}"
            st.session_state[d_key] = p_pos
            st.session_state.setdefault("m12_pending_offsets", {})[d_key] = p_pos
        else:
            st.session_state["m12_openings_active_tab"] = "🪟 شبابيك"
            st.session_state["m12_win_preview_disabled"] = False
            if p_wk in active:
                st.session_state["m12_openings_win_wall_sel"] = active.index(p_wk) + 1
            w_key = f"m12_add_new_win_offset_{p_wk[0]}_{p_wk[1]}_{p_wk[2]}_{p_wk[3]}"
            st.session_state[w_key] = p_pos
            st.session_state.setdefault("m12_pending_offsets", {})[w_key] = p_pos
    elif curr_prev and curr_prev.get("kind") == "door":
        if "m12_openings_active_tab" not in st.session_state:
            st.session_state["m12_openings_active_tab"] = "🚪 أبواب"
    elif curr_prev and curr_prev.get("kind") == "win":
        if "m12_openings_active_tab" not in st.session_state:
            st.session_state["m12_openings_active_tab"] = "🪟 شبابيك"

    tab_options = ["🪟 شبابيك", "🚪 أبواب"]
    current_tab = st.session_state.get("m12_openings_active_tab", "🪟 شبابيك")
    if current_tab not in tab_options:
        current_tab = "🪟 شبابيك"
    tab_idx = tab_options.index(current_tab)

    op_mode = st.radio(
        "اختر نوع العنصر المعماري المراد إسقاطه:",
        options=tab_options,
        index=tab_idx,
        horizontal=True,
        key="m12_openings_active_tab"
    )

    # ── رسالة تنبيه تعارض مكاني وهندسي بصورة مضغوطة فوق شاشة المدخلات ──
    if st.session_state.get("m12_show_conflict_modal"):
        _render_opening_conflict_banner()

    if op_mode == "🪟 شبابيك":
        if not active:
            st.info("لا توجد حوائط نشطة لإسقاط الشبابيك.")
            st.session_state["m12_preview_opening"] = None
        else:
            def_w_idx = 0
            if curr_prev and curr_prev.get("kind") == "win" and curr_prev.get("wk") in active:
                def_w_idx = active.index(curr_prev["wk"]) + 1
                if "m12_openings_win_wall_sel" not in st.session_state:
                    st.session_state["m12_openings_win_wall_sel"] = def_w_idx

            _safe_idx("m12_openings_win_wall_sel", len(active) + 1)
            sel_w = st.selectbox(
                "اختر الحائط لإسقاط الشباك عليه:",
                options=range(len(active) + 1),
                index=st.session_state.get("m12_openings_win_wall_sel", def_w_idx),
                format_func=lambda k: "لم يتم اختيار حائط" if k == 0 else _wall_display_label(active[k - 1], cm, wm),
                key="m12_openings_win_wall_sel"
            )
            if sel_w == 0:
                st.session_state["m12_preview_opening"] = None
                st.info("💡 لم يتم اختيار حائط. يرجى اختيار حائط من القائمة المنسدلة أعلاه لإسقاط الشباك عليه.")
            else:
                wk = active[sel_w - 1]
                wlen = _wall_length_m(wk)
                wh = _get_wall_height(wk, float(st.session_state.get("m12_default_wall_height", 3.0)))
                col1_l, col2_l, c1_nm, c2_nm, _ = _get_column_bounds_along_wall(wk)

                wm_win = _get_window_name_map()
                wl = st.session_state.get("m12_windows", {}).setdefault(wk, [])

                # ── اختيار نموذج الشباك ────────────────────────────────────
                win_types = st.session_state.get("m12_window_types", [])
                if not win_types:
                    st.info("💡 لم تُعرَّف أي نماذج شبابيك بعد. أضف نماذج في قسم '4️⃣ نماذج الفتحات' أولاً.")
                    win_type_opts = ["W1 (افتراضي)"]
                    win_type_labels = ["W1"]
                else:
                    win_type_opts = [f"{wt['label']} — عرض {wt['w_cm']:.0f}سم × ارتفاع {wt['h_cm']:.0f}سم" for wt in win_types]
                    win_type_labels = [wt["label"] for wt in win_types]

                _safe_idx(f"m12_add_win_type_sel_{wk}", len(win_type_opts))
                sel_win_type_idx = st.selectbox(
                    "🪟 اختر نموذج الشباك المراد إسقاطه:",
                    options=range(len(win_type_opts)),
                    format_func=lambda k: win_type_opts[k],
                    key=f"m12_add_win_type_sel_{wk}"
                )
                sel_win_type_lbl = win_type_labels[sel_win_type_idx] if win_type_labels and sel_win_type_idx < len(win_type_labels) else "W1"

                # ── أبعاد الشباك المختار ─────────────────────────────────
                active_wins = [w for w in wl if not w.get("removed", False)]
                if win_types and sel_win_type_idx < len(win_types):
                    chosen_wtype = win_types[sel_win_type_idx]
                    init_w_preview = float(chosen_wtype.get("w_cm", 100.0)) / 100.0
                    init_h_preview = float(chosen_wtype.get("h_cm", 120.0)) / 100.0
                    init_sill_preview = float(chosen_wtype.get("sill_cm", 90.0)) / 100.0
                    type_lbl = chosen_wtype.get("label", "W1")
                else:
                    init_w_preview = 1.0
                    init_h_preview = 1.2
                    init_sill_preview = 0.9
                    type_lbl = "W1"

                offset_key = f"m12_add_new_win_offset_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}"
                if "m12_pending_offsets" in st.session_state and offset_key in st.session_state["m12_pending_offsets"]:
                    st.session_state[offset_key] = st.session_state["m12_pending_offsets"].pop(offset_key)

                if offset_key not in st.session_state:
                    if curr_prev and curr_prev.get("kind") == "win" and curr_prev.get("wk") == wk:
                        st.session_state[offset_key] = float(curr_prev.get("pos_m", 0.0))
                    else:
                        suggested_pos = _find_first_available_opening_pos(wk, "win", init_w_preview, init_h_preview)
                        st.session_state[offset_key] = suggested_pos if suggested_pos is not None else round(max(0.0, (wlen - init_w_preview) / 2.0), 2)

                default_new_win_pos = float(st.session_state.get(offset_key, (wlen - init_w_preview) / 2.0))
                default_new_win_pos = max(0.0, min(float(wlen), default_new_win_pos))

                # ── بعد بداية الشباك عن بداية الحائط (م) ───────────
                c_wpos1, c_wpos2 = st.columns([1.6, 1.0])
                with c_wpos1:
                    new_win_offset = st.number_input(
                        "بعد بداية الشباك عن بداية الحائط (م)",
                        min_value=0.0, max_value=max(float(wlen), 0.1),
                        value=float(default_new_win_pos),
                        step=0.05, format="%.2f",
                        key=offset_key,
                        help=f"المسافة المقاسة من بداية الحائط حتى بداية الشباك [طول الحائط: {wlen:.2f}م]"
                    )

                new_wname = _next_window_name(type_lbl)
                conflict_errs = _check_opening_spatial_conflict(
                    wk=wk,
                    op_name=f"الشباك {new_wname}",
                    op_type="win",
                    w_m=init_w_preview,
                    h_m=init_h_preview,
                    pos_m=new_win_offset,
                )

                # ── تتبع توقيع التعديل وإدارة حالة المعاينة المؤقتة للشباك ──
                win_sig = (wk, sel_win_type_idx, round(float(new_win_offset), 3))
                if st.session_state.get("m12_win_preview_sig") != win_sig:
                    st.session_state["m12_win_preview_disabled"] = False
                    st.session_state["m12_win_preview_sig"] = win_sig
                    st.session_state["m12_show_conflict_modal"] = False
                    st.session_state["m12_conflict_errors"] = []

                is_win_disabled = bool(st.session_state.get("m12_win_preview_disabled", False))

                preview_win = {
                    "kind": "win",
                    "wk": wk,
                    "name": new_wname,
                    "type_label": type_lbl,
                    "w_m": float(init_w_preview),
                    "h_m": float(init_h_preview),
                    "pos_m": float(new_win_offset),
                    "sill_m": float(init_sill_preview),
                    "removed": False,
                    "is_preview": True,
                    "has_conflict": bool(conflict_errs),
                }
                if not is_win_disabled:
                    st.session_state["m12_preview_opening"] = preview_win
                else:
                    st.session_state["m12_preview_opening"] = None

                with c_wpos2:
                    if is_win_disabled:
                        st.markdown(
                            "<div style='margin-top:28px;color:#757575;font-weight:bold;font-size:0.86rem;'>"
                            "⚪ الشباك المؤقت مخفي حالياً عن الرسم"
                            "</div>", unsafe_allow_html=True
                        )
                    elif conflict_errs:
                        st.markdown(
                            "<div style='margin-top:28px;color:#D32F2F;font-weight:bold;font-size:0.86rem;'>"
                            "⚠️ تعارض في الموضع! (يظهر الشباك بالأحمر على الرسم)"
                            "</div>", unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            "<div style='margin-top:28px;color:#2E7D32;font-weight:bold;font-size:0.86rem;'>"
                            "✅ الموضع متاح هندسياً (يظهر الشباك بالأزرق على الرسم)"
                            "</div>", unsafe_allow_html=True
                        )

                # صف أزرار التحكم: زر الاعتماد وزر إلغاء الشباك المؤقت
                col_wbtn1, col_wbtn2 = st.columns([1.4, 1.0])
                with col_wbtn1:
                    btn_w_text = "➕ اعتماد وإسقاط الشباك على الحائط"
                    if st.button(btn_w_text, key=f"m12_add_win_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}", type="primary", use_container_width=True):
                        if not conflict_errs:
                            # الحالة الأولى: النجاح (No Conflicts Detected)
                            win_to_add = dict(preview_win)
                            win_to_add["id"] = _next_op_id("win")
                            win_to_add["is_preview"] = False
                            win_to_add["has_conflict"] = False
                            if "m12_windows" not in st.session_state:
                                st.session_state["m12_windows"] = {}
                            if wk not in st.session_state["m12_windows"]:
                                st.session_state["m12_windows"][wk] = []
                            st.session_state["m12_windows"][wk].append(win_to_add)
                            st.session_state["m12_preview_opening"] = None
                            st.session_state["m12_win_preview_disabled"] = False
                            st.session_state["m12_win_preview_sig"] = None
                            st.session_state["m12_show_conflict_modal"] = False
                            st.session_state["m12_conflict_errors"] = []
                            st.session_state["m12_openings_keep_expanded"] = True
                            _resequence_openings()
                            # حفظ موضع المؤشر للموضع التالي المتاح هندسياً للتشغيل القادم
                            next_wpos = _find_first_available_opening_pos(wk, "win", init_w_preview, init_h_preview)
                            if next_wpos is not None:
                                st.session_state.setdefault("m12_pending_offsets", {})[offset_key] = next_wpos
                            save_settings()
                            st.session_state["m12_commit_success_msg"] = {
                                "kind": "win",
                                "kind_ar": "الشباك",
                                "name": new_wname,
                                "wall_label": _wall_display_label(wk, cm, wm),
                                "pos_m": float(new_win_offset),
                                "w_m": float(init_w_preview),
                                "h_m": float(init_h_preview),
                                "msg": "تم تثبيت وإسقاط الشباك بنجاح على الحائط. لتحريك الشباك أو تعديل أبعاده وجلسته، توجه إلى قسم «6️⃣ تحريك الشبابيك والأبواب» أو استخدم العارض ثلاثي الأبعاد 3D."
                            }
                            st.rerun()
                        else:
                            # الحالة الثانية: التعارض (Conflict / Out of Bounds Detected)
                            preview_win["has_conflict"] = True
                            st.session_state["m12_preview_opening"] = preview_win
                            st.session_state["m12_win_preview_disabled"] = False
                            st.session_state["m12_conflict_errors"] = conflict_errs
                            st.session_state["m12_show_conflict_modal"] = True
                            st.session_state["m12_openings_keep_expanded"] = True
                            st.rerun()

                with col_wbtn2:
                    if not is_win_disabled:
                        if st.button("❌ إلغاء الشباك المؤقت", key=f"m12_cancel_win_preview_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}", type="secondary", use_container_width=True, help="إلغاء وإخفاء الشباك المؤقت من على الرسم"):
                            st.session_state["m12_win_preview_disabled"] = True
                            st.session_state["m12_preview_opening"] = None
                            st.session_state["m12_show_conflict_modal"] = False
                            st.session_state["m12_conflict_errors"] = []
                            st.session_state["m12_openings_keep_expanded"] = True
                            st.rerun()
                    else:
                        if st.button("👁️ إظهار الشباك المؤقت", key=f"m12_restore_win_preview_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}", type="secondary", use_container_width=True, help="إعادة إظهار الشباك المؤقت على الرسم"):
                            st.session_state["m12_win_preview_disabled"] = False
                            st.session_state["m12_openings_keep_expanded"] = True
                            st.rerun()

                active_wins = [w for w in wl if not w.get("removed", False)]
                if active_wins:
                    st.markdown(
                        f"""<div style='background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.3);border-radius:8px;padding:10px 14px;margin-top:12px;' dir='rtl'>
                            <div style='color:#0284c7;font-weight:bold;font-size:0.9rem;margin-bottom:4px;'>
                                ℹ️ الشبابيك القائمة على هذا الحائط ({len(active_wins)}):
                            </div>
                            <div style='color:#334155;font-size:0.84rem;margin-bottom:6px;'>
                                {', '.join([f"<b>{wm_win.get(w.get('id'), w.get('name', 'W'))}</b> (موضع {w.get('pos_m',0.0):.2f}م)" for w in active_wins])}
                            </div>
                            <div style='color:#0369a1;font-size:0.82rem;font-weight:600;'>
                                💡 لتحريك أي شباك أو تعديل أبعاده وجلسته، توجه إلى قسم <b>«6️⃣ تحريك الشبابيك والأبواب»</b> أو حرّكه مباشرة بالمقبض في العارض 3D.
                            </div>
                        </div>""",
                        unsafe_allow_html=True
                    )
                st.session_state["m12_windows"][wk] = wl

    else:
        if not active:
            st.info("لا توجد حوائط نشطة لإضافة أو تعديل الأبواب.")
            st.session_state["m12_preview_opening"] = None
        else:
            def_d_idx = 0
            if curr_prev and curr_prev.get("kind") == "door" and curr_prev.get("wk") in active:
                def_d_idx = active.index(curr_prev["wk"]) + 1
                if "m12_openings_door_wall_sel" not in st.session_state:
                    st.session_state["m12_openings_door_wall_sel"] = def_d_idx

            _safe_idx("m12_openings_door_wall_sel", len(active) + 1)
            sel_d = st.selectbox(
                "اختر الحائط لإسقاط الباب عليه:",
                options=range(len(active) + 1),
                index=st.session_state.get("m12_openings_door_wall_sel", def_d_idx),
                format_func=lambda k: "لم يتم اختيار حائط" if k == 0 else _wall_display_label(active[k - 1], cm, wm),
                key="m12_openings_door_wall_sel"
            )
            if sel_d == 0:
                st.session_state["m12_preview_opening"] = None
                st.info("💡 لم يتم اختيار حائط. يرجى اختيار حائط من القائمة المنسدلة أعلاه لإسقاط الباب عليه.")
            else:
                wk = active[sel_d - 1]
                wlen = _wall_length_m(wk)
                wh = _get_wall_height(wk, float(st.session_state.get("m12_default_wall_height", 3.0)))
                col1_l, col2_l, c1_nm, c2_nm, _ = _get_column_bounds_along_wall(wk)

                wm_door = _get_door_name_map()
                dl = st.session_state.get("m12_doors", {}).setdefault(wk, [])
                is_h_wall = (wk[1] == wk[3])

                # ── اختيار نموذج الباب ──────────────────────────────────────
                door_types = st.session_state.get("m12_door_types", [])
                if not door_types:
                    st.info("💡 لم تُعرَّف أي نماذج أبواب بعد. أضف نماذج في قسم '4️⃣ نماذج الفتحات' أولاً.")
                    door_type_opts = ["D1 (افتراضي)"]
                    door_type_labels = ["D1"]
                else:
                    door_type_opts = [f"{dt['label']} — عرض {dt['w_cm']:.0f}سم × ارتفاع {dt['h_cm']:.0f}سم" for dt in door_types]
                    door_type_labels = [dt["label"] for dt in door_types]

                _safe_idx(f"m12_add_door_type_sel_{wk}", len(door_type_opts))
                sel_door_type_idx = st.selectbox(
                    "🚪 اختر نموذج الباب المراد إسقاطه:",
                    options=range(len(door_type_opts)),
                    format_func=lambda k: door_type_opts[k],
                    key=f"m12_add_door_type_sel_{wk}"
                )
                sel_door_type_lbl = door_type_labels[sel_door_type_idx] if door_type_labels and sel_door_type_idx < len(door_type_labels) else "D1"

                # ── أبعاد الباب المختار ─────────────────────────────────
                active_doors = [d for d in dl if not d.get("removed", False)]
                if door_types and sel_door_type_idx < len(door_types):
                    chosen_dtype = door_types[sel_door_type_idx]
                    init_dw_preview = float(chosen_dtype.get("w_cm", 90.0)) / 100.0
                    init_dh_preview = float(chosen_dtype.get("h_cm", 210.0)) / 100.0
                    door_type_lbl = chosen_dtype.get("label", "D1")
                else:
                    init_dw_preview = 0.9
                    init_dh_preview = 2.1
                    door_type_lbl = "D1"

                # تحديد اتجاه الخطين المتعامدين وموضع المفصلة للباب الجديد
                c_dleaf, c_dhinge = st.columns(2)
                if is_h_wall:
                    new_leaf_opts = ["أعلى", "أسفل"]
                    new_hinge_opts = ["يسار", "يمين"]
                else:
                    new_leaf_opts = ["يمين", "يسار"]
                    new_hinge_opts = ["أسفل", "أعلى"]

                with c_dleaf:
                    new_door_leaf = st.selectbox(
                        "اتجاه ضلفة الباب:",
                        options=new_leaf_opts,
                        key=f"m12_new_door_leaf_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}"
                    )
                with c_dhinge:
                    new_door_hinge = st.selectbox(
                        "موضع المفصلة:",
                        options=new_hinge_opts,
                        key=f"m12_new_door_hinge_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}"
                    )

                d_offset_key = f"m12_add_new_door_offset_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}"
                if "m12_pending_offsets" in st.session_state and d_offset_key in st.session_state["m12_pending_offsets"]:
                    st.session_state[d_offset_key] = st.session_state["m12_pending_offsets"].pop(d_offset_key)

                if d_offset_key not in st.session_state:
                    if curr_prev and curr_prev.get("kind") == "door" and curr_prev.get("wk") == wk:
                        st.session_state[d_offset_key] = float(curr_prev.get("pos_m", 0.0))
                    else:
                        suggested_dpos = _find_first_available_opening_pos(wk, "door", init_dw_preview, init_dh_preview, leaf_dir=new_door_leaf)
                        st.session_state[d_offset_key] = suggested_dpos if suggested_dpos is not None else round(max(0.0, (wlen - init_dw_preview) / 2.0), 2)

                default_new_door_pos = float(st.session_state.get(d_offset_key, (wlen - init_dw_preview) / 2.0))
                default_new_door_pos = max(0.0, min(float(wlen), default_new_door_pos))

                # ── بعد بداية الباب عن بداية الحائط (م) ───────────
                c_dpos1, c_dpos2 = st.columns([1.6, 1.0])
                with c_dpos1:
                    new_door_offset = st.number_input(
                        "بعد بداية الباب عن بداية الحائط (م)",
                        min_value=0.0, max_value=max(float(wlen), 0.1),
                        value=float(default_new_door_pos),
                        step=0.05, format="%.2f",
                        key=d_offset_key,
                        help=f"المسافة المقاسة من بداية الحائط حتى بداية الباب [طول الحائط: {wlen:.2f}م]"
                    )

                new_dname = _next_door_name(door_type_lbl)
                test_derr = _check_opening_spatial_conflict(
                    wk=wk,
                    op_name=f"الباب {new_dname}",
                    op_type="door",
                    w_m=init_dw_preview,
                    h_m=init_dh_preview,
                    pos_m=new_door_offset,
                    leaf_dir=new_door_leaf
                )

                # ── تتبع توقيع التعديل وإدارة حالة المعاينة المؤقتة للباب ──
                door_sig = (wk, sel_door_type_idx, round(float(new_door_offset), 3), new_door_leaf, new_door_hinge)
                if st.session_state.get("m12_door_preview_sig") != door_sig:
                    st.session_state["m12_door_preview_disabled"] = False
                    st.session_state["m12_door_preview_sig"] = door_sig
                    st.session_state["m12_show_conflict_modal"] = False
                    st.session_state["m12_conflict_errors"] = []

                is_door_disabled = bool(st.session_state.get("m12_door_preview_disabled", False))

                preview_door = {
                    "kind": "door",
                    "wk": wk,
                    "name": new_dname,
                    "type_label": door_type_lbl,
                    "w_m": float(init_dw_preview),
                    "h_m": float(init_dh_preview),
                    "pos_m": float(new_door_offset),
                    "leaf_dir": new_door_leaf,
                    "hinge_dir": new_door_hinge,
                    "removed": False,
                    "is_preview": True,
                    "has_conflict": bool(test_derr),
                }
                if not is_door_disabled:
                    st.session_state["m12_preview_opening"] = preview_door
                else:
                    st.session_state["m12_preview_opening"] = None

                with c_dpos2:
                    if is_door_disabled:
                        st.markdown(
                            "<div style='margin-top:28px;color:#757575;font-weight:bold;font-size:0.86rem;'>"
                            "⚪ الباب المؤقت مخفي حالياً عن الرسم"
                            "</div>", unsafe_allow_html=True
                        )
                    elif test_derr:
                        st.markdown(
                            "<div style='margin-top:28px;color:#D32F2F;font-weight:bold;font-size:0.86rem;'>"
                            "⚠️ تعارض في الموضع! (يظهر الباب بالأحمر على الرسم)"
                            "</div>", unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            "<div style='margin-top:28px;color:#2E7D32;font-weight:bold;font-size:0.86rem;'>"
                            "✅ الموضع متاح هندسياً (يظهر الباب بالأخضر على الرسم)"
                            "</div>", unsafe_allow_html=True
                        )

                # صف أزرار التحكم: زر الاعتماد وزر إلغاء الباب المؤقت
                col_dbtn1, col_dbtn2 = st.columns([1.4, 1.0])
                with col_dbtn1:
                    btn_d_text = "➕ اعتماد وإسقاط الباب على الحائط"
                    if st.button(btn_d_text, key=f"m12_add_door_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}", type="primary", use_container_width=True):
                        if not test_derr:
                            door_to_add = dict(preview_door)
                            door_to_add["id"] = _next_op_id("door")
                            door_to_add["is_preview"] = False
                            door_to_add["has_conflict"] = False
                            if "m12_doors" not in st.session_state:
                                st.session_state["m12_doors"] = {}
                            if wk not in st.session_state["m12_doors"]:
                                st.session_state["m12_doors"][wk] = []
                            st.session_state["m12_doors"][wk].append(door_to_add)
                            st.session_state["m12_preview_opening"] = None
                            st.session_state["m12_door_preview_disabled"] = False
                            st.session_state["m12_door_preview_sig"] = None
                            st.session_state["m12_show_conflict_modal"] = False
                            st.session_state["m12_conflict_errors"] = []
                            st.session_state["m12_openings_keep_expanded"] = True
                            _resequence_openings()
                            # حفظ موضع المؤشر للموضع التالي المتاح هندسياً للتشغيل القادم
                            next_dpos = _find_first_available_opening_pos(wk, "door", init_dw_preview, init_dh_preview, leaf_dir=new_door_leaf)
                            if next_dpos is not None:
                                st.session_state.setdefault("m12_pending_offsets", {})[d_offset_key] = next_dpos
                            save_settings()
                            st.session_state["m12_commit_success_msg"] = {
                                "kind": "door",
                                "kind_ar": "الباب",
                                "name": new_dname,
                                "wall_label": _wall_display_label(wk, cm, wm),
                                "pos_m": float(new_door_offset),
                                "w_m": float(init_dw_preview),
                                "h_m": float(init_dh_preview),
                                "msg": "تم تثبيت وإسقاط الباب بنجاح على الحائط. لتحريك الباب أو تعديل اتجاهه وأبعاده، توجه إلى قسم «6️⃣ تحريك الشبابيك والأبواب» أو استخدم العارض ثلاثي الأبعاد 3D."
                            }
                            st.rerun()
                        else:
                            preview_door["has_conflict"] = True
                            st.session_state["m12_preview_opening"] = preview_door
                            st.session_state["m12_door_preview_disabled"] = False
                            st.session_state["m12_conflict_errors"] = test_derr
                            st.session_state["m12_show_conflict_modal"] = True
                            st.session_state["m12_openings_keep_expanded"] = True
                            st.rerun()

                with col_dbtn2:
                    if not is_door_disabled:
                        if st.button("❌ إلغاء الباب المؤقت", key=f"m12_cancel_door_preview_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}", type="secondary", use_container_width=True, help="إلغاء وإخفاء الباب المؤقت من على الرسم"):
                            st.session_state["m12_door_preview_disabled"] = True
                            st.session_state["m12_preview_opening"] = None
                            st.session_state["m12_show_conflict_modal"] = False
                            st.session_state["m12_conflict_errors"] = []
                            st.session_state["m12_openings_keep_expanded"] = True
                            st.rerun()
                    else:
                        if st.button("👁️ إظهار الباب المؤقت", key=f"m12_restore_door_preview_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}", type="secondary", use_container_width=True, help="إعادة إظهار الباب المؤقت على الرسم"):
                            st.session_state["m12_door_preview_disabled"] = False
                            st.session_state["m12_openings_keep_expanded"] = True
                            st.rerun()

                active_doors = [d for d in dl if not d.get("removed", False)]
                if active_doors:
                    st.markdown(
                        f"""<div style='background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.3);border-radius:8px;padding:10px 14px;margin-top:12px;' dir='rtl'>
                            <div style='color:#16a34a;font-weight:bold;font-size:0.9rem;margin-bottom:4px;'>
                                ℹ️ الأبواب القائمة على هذا الحائط ({len(active_doors)}):
                            </div>
                            <div style='color:#334155;font-size:0.84rem;margin-bottom:6px;'>
                                {', '.join([f"<b>{wm_door.get(d.get('id'), d.get('name', 'D'))}</b> (موضع {d.get('pos_m',0.0):.2f}م)" for d in active_doors])}
                            </div>
                            <div style='color:#15803d;font-size:0.82rem;font-weight:600;'>
                                💡 لتحريك أي باب أو تعديل اتجاهه وأبعاده، توجه إلى قسم <b>«6️⃣ تحريك الشبابيك والأبواب»</b> أو حرّكه مباشرة بالمقبض في العارض 3D.
                            </div>
                        </div>""",
                        unsafe_allow_html=True
                    )
                st.session_state["m12_doors"][wk] = dl


def _section_move_openings():
    """
    قسم مخصص لتحريك وتعديل الشبابيك والأبواب:
    - تعديل الأبعاد (العرض والارتفاع والجلسة).
    - تعديل البعد المباشر عن بداية الحائط مع فحص التعارض المكاني الفوري.
    - تعديل اتجاه ضلفة الباب وموضع المفصلة.
    - إمكانية الإزاحة السريعة باتجاهات المحاور (يمين/يسار وأعلى/أسفل).
    """
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m12_wall_removed", set())
    active_walls = [w for w in all_walls if w not in removed_walls]
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()
    _ensure_opening_names()

    tab_w, tab_d = st.tabs(["🪟 تحريك وتعديل الشبابيك", "🚪 تحريك وتعديل الأبواب"])

    # ═══════════════════════════════════════════════════════════════════════
    # التبويبة 1: تحريك وتعديل الشبابيك
    # ═══════════════════════════════════════════════════════════════════════
    with tab_w:
        walls_with_wins = [wk for wk in active_walls if any(not w.get("removed", False) for w in _get_wall_windows(wk))]
        
        if not walls_with_wins:
            st.info("💡 لا توجد شبابيك نشطة مُسقطة على الحوائط حالياً. يمكنك إسقاط شبابيك جديدة من قسم «5️⃣ إسقاط الشبابيك والأبواب».")
        else:
            c_sel_w1, c_sel_w2 = st.columns([1.6, 1.0])
            with c_sel_w1:
                _safe_idx("m12_mv_win_wall_sel", len(walls_with_wins))
                sel_w_idx = st.selectbox(
                    "اختر الحائط لعرض وتحريك الشبابيك:",
                    options=range(len(walls_with_wins)),
                    format_func=lambda k: _wall_display_label(walls_with_wins[k], cm, wm),
                    key="m12_mv_win_wall_sel"
                )
            with c_sel_w2:
                show_all_wins = st.checkbox("عرض شبابيك كل الحوائط معاً", value=False, key="m12_mv_win_show_all")

            target_wks = walls_with_wins if show_all_wins else [walls_with_wins[sel_w_idx]]

            for wk in target_wks:
                wlen = _wall_length_m(wk)
                wh = _get_wall_height(wk, float(st.session_state.get("m12_default_wall_height", 3.0)))
                wlbl = _wall_display_label(wk, cm, wm)
                is_h_wall = (wk[1] == wk[3])
                
                wl = st.session_state.get("m12_windows", {}).get(wk, [])
                active_wins = [w for w in wl if not w.get("removed", False)]
                if not active_wins:
                    continue

                if show_all_wins:
                    st.markdown(f"<div style='font-weight:bold;color:#004488;margin:10px 0 4px 0;font-size:0.95rem;' dir='rtl'>🧱 {wlbl} [طول الحائط: {wlen:.2f}م]:</div>", unsafe_allow_html=True)

                for wi, winfo in enumerate(active_wins):
                    wid = winfo["id"]
                    wname = wm_win.get(wid) or winfo.get("name") or f"W{wi+1}"
                    winfo["name"] = wname
                    type_lbl_w = winfo.get("type_label", "")
                    cur_pos = float(winfo.get("pos_m", 0.0))
                    cur_w = float(winfo.get("w_m", 1.0))
                    cur_h = float(winfo.get("h_m", 1.2))
                    cur_sill = float(winfo.get("sill_m", 0.9))

                    expander_title = f"🪟 شباك {wname}" + (f" [{type_lbl_w}]" if type_lbl_w else "") + f" — أبعاد النموذج: ({cur_w:.2f}×{cur_h:.2f}م | جلسة {cur_sill:.2f}م) — الموضع: {cur_pos:.2f}م على {wlbl}"

                    with st.expander(expander_title, expanded=True):
                        # تطبيق الإرجاع المؤجل الآمن قبل إنشاء الودجت لتجنب أي StreamlitAPIException
                        if f"m12_pending_pos_win_{wid}" in st.session_state:
                            target_wpos = float(st.session_state.pop(f"m12_pending_pos_win_{wid}"))
                            winfo["pos_m"] = target_wpos
                            cur_pos = target_wpos
                            st.session_state[f"m12_mv_w_pos_{wid}"] = target_wpos
                            st.session_state["m12_active_move_dim"] = {
                                "op_id": wid,
                                "kind": "win",
                                "kind_ar": "الشباك",
                                "name": wname,
                                "wk": wk,
                                "pos_m": target_wpos,
                                "w_m": float(winfo.get("w_m", 1.0)),
                                "ts": time.time(),
                            }
                            st.session_state.pop("m12_plan_png_b64", None)
                            save_settings()

                        # صف تحريك الشباك وتحديد البعد عن بداية الحائط
                        new_wpos = st.number_input(
                            "📏 بعد بداية الشباك عن بداية الحائط (م):",
                            min_value=0.0,
                            max_value=float(wlen),
                            value=cur_pos,
                            step=0.05,
                            format="%.2f",
                            key=f"m12_mv_w_pos_{wid}",
                            help=f"تحديد موضع الشباك بدقة من بداية الحائط [طول الحائط: {wlen:.2f}م]"
                        )
                        if new_wpos != cur_pos:
                            winfo["pos_m"] = round(new_wpos, 2)
                            st.session_state["m12_active_move_dim"] = {
                                "op_id": wid,
                                "kind": "win",
                                "kind_ar": "الشباك",
                                "name": wname,
                                "wk": wk,
                                "pos_m": round(new_wpos, 2),
                                "w_m": float(winfo.get("w_m", 1.0)),
                                "ts": time.time(),
                            }
                            st.session_state.pop("m12_plan_png_b64", None)
                            save_settings()

                        if f"m12_prev_safe_pos_win_{wid}" not in st.session_state:
                            st.session_state[f"m12_prev_safe_pos_win_{wid}"] = cur_pos

                        # فحص التعارضات الهندسية والصلاحية
                        w_errs = _validate_opening_coords(wk, f"الشباك {wname}", "win", winfo["w_m"], winfo["h_m"], winfo["pos_m"], current_op_id=wid)
                        if winfo["h_m"] > wh:
                            st.error(f"⚠️ ارتفاع الشباك ({winfo['h_m']:.2f}م) أكبر من ارتفاع الحائط ({wh:.2f}م)!")
                        if (winfo["sill_m"] + winfo["h_m"]) > wh:
                            st.error(f"⚠️ مجموع ارتفاع الجلسة مع الشباك ({(winfo['sill_m'] + winfo['h_m']):.2f}م) يتجاوز ارتفاع الحائط ({wh:.2f}م)!")

                        if w_errs:
                            _render_big_warning(w_errs)
                            if st.button("OK", key=f"m12_revert_w_ok_{wid}", use_container_width=True, type="primary", help="التراجع عن التحريك وإعادة الشباك إلى موضعه السابق قبل التداخل"):
                                revert_pos = float(st.session_state.get(f"m12_prev_safe_pos_win_{wid}", cur_pos))
                                st.session_state[f"m12_pending_pos_win_{wid}"] = revert_pos
                                st.rerun()
                        else:
                            st.session_state[f"m12_prev_safe_pos_win_{wid}"] = round(float(winfo.get("pos_m", 0.0)), 2)
                            st.markdown(
                                f"<div style='color:#15803d;font-size:0.83rem;font-weight:700;margin-top:4px;' dir='rtl'>"
                                f"✅ الموضع متاح هندسياً (يمتد من {winfo['pos_m']:.2f}م إلى {winfo['pos_m'] + winfo['w_m']:.2f}م من بداية الحائط)"
                                f"</div>",
                                unsafe_allow_html=True
                            )

    # ═══════════════════════════════════════════════════════════════════════
    # التبويبة 2: تحريك وتعديل الأبواب
    # ═══════════════════════════════════════════════════════════════════════
    with tab_d:
        walls_with_doors = [wk for wk in active_walls if any(not d.get("removed", False) for d in _get_wall_doors(wk))]
        
        if not walls_with_doors:
            st.info("💡 لا توجد أبواب نشطة مُسقطة على الحوائط حالياً. يمكنك إسقاط أبواب جديدة من قسم «5️⃣ إسقاط الشبابيك والأبواب».")
        else:
            c_sel_d1, c_sel_d2 = st.columns([1.6, 1.0])
            with c_sel_d1:
                _safe_idx("m12_mv_door_wall_sel", len(walls_with_doors))
                sel_d_idx = st.selectbox(
                    "اختر الحائط لعرض وتحريك الأبواب:",
                    options=range(len(walls_with_doors)),
                    format_func=lambda k: _wall_display_label(walls_with_doors[k], cm, wm),
                    key="m12_mv_door_wall_sel"
                )
            with c_sel_d2:
                show_all_doors = st.checkbox("عرض أبواب كل الحوائط معاً", value=False, key="m12_mv_door_show_all")

            target_d_wks = walls_with_doors if show_all_doors else [walls_with_doors[sel_d_idx]]

            for wk in target_d_wks:
                wlen = _wall_length_m(wk)
                wh = _get_wall_height(wk, float(st.session_state.get("m12_default_wall_height", 3.0)))
                wlbl = _wall_display_label(wk, cm, wm)
                is_h_wall = (wk[1] == wk[3])
                
                dl = st.session_state.get("m12_doors", {}).get(wk, [])
                active_doors = [d for d in dl if not d.get("removed", False)]
                if not active_doors:
                    continue

                if show_all_doors:
                    st.markdown(f"<div style='font-weight:bold;color:#16a34a;margin:10px 0 4px 0;font-size:0.95rem;' dir='rtl'>🧱 {wlbl} [طول الحائط: {wlen:.2f}م]:</div>", unsafe_allow_html=True)

                for di, dinfo in enumerate(active_doors):
                    did = dinfo["id"]
                    dname = wm_door.get(did) or dinfo.get("name") or f"D{di+1}"
                    dinfo["name"] = dname
                    type_lbl_d = dinfo.get("type_label", "")
                    cur_pos_d = float(dinfo.get("pos_m", 0.0))
                    cur_w_d = float(dinfo.get("w_m", 0.9))
                    cur_h_d = float(dinfo.get("h_m", 2.1))

                    door_exp_title = f"🚪 باب {dname}" + (f" [{type_lbl_d}]" if type_lbl_d else "") + f" — أبعاد النموذج: ({cur_w_d:.2f}×{cur_h_d:.2f}م) — الموضع: {cur_pos_d:.2f}م على {wlbl}"

                    with st.expander(door_exp_title, expanded=True):
                        # صف اتجاه الباب والمفصلة (اتجاه الباب وخلافه)
                        dc3, dc4 = st.columns(2)
                        if is_h_wall:
                            leaf_opts = ["أعلى", "أسفل"]
                            hinge_opts = ["يسار", "يمين"]
                            leaf_lbl = "اتجاه ضلفة الباب (أعلى / أسفل):"
                            hinge_lbl = "موضع المفصلة (يسار / يمين):"
                        else:
                            leaf_opts = ["يمين", "يسار"]
                            hinge_opts = ["أسفل", "أعلى"]
                            leaf_lbl = "اتجاه ضلفة الباب (يمين / يسار):"
                            hinge_lbl = "موضع المفصلة (أسفل / أعلى):"

                        _dir_icons = {"أعلى": "⬆️ أعلى", "أسفل": "⬇️ أسفل", "يمين": "➡️ يمين", "يسار": "⬅️ يسار"}
                        cur_leaf = dinfo.get("leaf_dir", leaf_opts[0])
                        if cur_leaf not in leaf_opts: cur_leaf = leaf_opts[0]
                        cur_hinge = dinfo.get("hinge_dir", hinge_opts[0])
                        if cur_hinge not in hinge_opts: cur_hinge = hinge_opts[0]

                        with dc3:
                            new_leaf = st.selectbox(leaf_lbl, options=leaf_opts, index=leaf_opts.index(cur_leaf),
                                                    format_func=lambda v: _dir_icons.get(v, v), key=f"m12_mv_d_leaf_{did}")
                            if new_leaf != cur_leaf:
                                dinfo["leaf_dir"] = new_leaf
                                save_settings()
                        with dc4:
                            new_hinge = st.selectbox(hinge_lbl, options=hinge_opts, index=hinge_opts.index(cur_hinge),
                                                     format_func=lambda v: _dir_icons.get(v, v), key=f"m12_mv_d_hinge_{did}")
                            if new_hinge != cur_hinge:
                                dinfo["hinge_dir"] = new_hinge
                                save_settings()

                        # تطبيق الإرجاع المؤجل الآمن قبل إنشاء ودجت الباب لتجنب أي StreamlitAPIException
                        if f"m12_pending_pos_door_{did}" in st.session_state:
                            target_dpos = float(st.session_state.pop(f"m12_pending_pos_door_{did}"))
                            dinfo["pos_m"] = target_dpos
                            cur_pos_d = target_dpos
                            st.session_state[f"m12_mv_d_pos_{did}"] = target_dpos
                            st.session_state["m12_active_move_dim"] = {
                                "op_id": did,
                                "kind": "door",
                                "kind_ar": "الباب",
                                "name": dname,
                                "wk": wk,
                                "pos_m": target_dpos,
                                "w_m": float(dinfo.get("w_m", 0.9)),
                                "ts": time.time(),
                            }
                            st.session_state.pop("m12_plan_png_b64", None)
                            save_settings()

                        # صف تحريك الباب والبعد عن بداية الحائط
                        st.markdown("<hr style='margin:6px 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)
                        new_dpos = st.number_input(
                            "📏 بعد بداية الباب عن بداية الحائط (م):",
                            min_value=0.0,
                            max_value=float(wlen),
                            value=cur_pos_d,
                            step=0.05,
                            format="%.2f",
                            key=f"m12_mv_d_pos_{did}",
                            help=f"تحديد موضع الباب بدقة من بداية الحائط [طول الحائط: {wlen:.2f}م]"
                        )
                        if new_dpos != cur_pos_d:
                            dinfo["pos_m"] = round(new_dpos, 2)
                            st.session_state["m12_active_move_dim"] = {
                                "op_id": did,
                                "kind": "door",
                                "kind_ar": "الباب",
                                "name": dname,
                                "wk": wk,
                                "pos_m": round(new_dpos, 2),
                                "w_m": float(dinfo.get("w_m", 0.9)),
                                "ts": time.time(),
                            }
                            st.session_state.pop("m12_plan_png_b64", None)
                            save_settings()

                        if f"m12_prev_safe_pos_door_{did}" not in st.session_state:
                            st.session_state[f"m12_prev_safe_pos_door_{did}"] = cur_pos_d

                        # فحص التعارضات الهندسية والصلاحية
                        d_errs = _validate_opening_coords(wk, f"الباب {dname}", "door", dinfo["w_m"], dinfo["h_m"], dinfo["pos_m"], leaf_dir=dinfo.get("leaf_dir"), current_op_id=did)
                        if dinfo["h_m"] > wh:
                            st.error(f"⚠️ ارتفاع الباب ({dinfo['h_m']:.2f}م) أكبر من ارتفاع الحائط ({wh:.2f}م)!")

                        if d_errs:
                            _render_big_warning(d_errs)
                            if st.button("OK", key=f"m12_revert_d_ok_{did}", use_container_width=True, type="primary", help="التراجع عن التحريك وإعادة الباب إلى موضعه السابق قبل التداخل"):
                                revert_pos = float(st.session_state.get(f"m12_prev_safe_pos_door_{did}", cur_pos_d))
                                st.session_state[f"m12_pending_pos_door_{did}"] = revert_pos
                                st.rerun()
                        else:
                            st.session_state[f"m12_prev_safe_pos_door_{did}"] = round(float(dinfo.get("pos_m", 0.0)), 2)
                            st.markdown(
                                f"<div style='color:#15803d;font-size:0.83rem;font-weight:700;margin-top:4px;' dir='rtl'>"
                                f"✅ الموضع متاح هندسياً (يمتد من {dinfo['pos_m']:.2f}م إلى {dinfo['pos_m'] + dinfo['w_m']:.2f}م من بداية الحائط)"
                                f"</div>",
                                unsafe_allow_html=True
                            )


def _section_delete_restore_openings():
    """قسم مخصص لحذف الشبابيك والأبواب."""
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m12_wall_removed", set())
    active_walls = [w for w in all_walls if w not in removed_walls]
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()
    _ensure_opening_names()

    tab_w_lbl = "🪟 حذف الشبابيك"
    tab_d_lbl = "🚪 حذف الأبواب"

    tw, td = st.tabs([tab_w_lbl, tab_d_lbl])

    # ═══════════════════════════════════════════════════════════════════════
    # التبويبة 1: حذف الشبابيك
    # ═══════════════════════════════════════════════════════════════════════
    with tw:
        st.markdown("<h5 style='color:#004488;margin-bottom:8px;'>🗑️ حذف الشبابيك القائمة</h5>", unsafe_allow_html=True)
        if not active_walls:
            st.info("لا توجد حوائط نشطة في المشروع.")
        else:
            wall_options = ["— كافة الحوائط النشطة —"] + [f"حائط {_wall_display_label(w, cm, wm)}" for w in active_walls]
            sel_wall_idx = st.selectbox("تصفية الشبابيك حسب الحائط:", options=range(len(wall_options)),
                                        format_func=lambda idx: wall_options[idx], key="m12_del_w_wall_filter")
            
            target_walls = active_walls if sel_wall_idx == 0 else [active_walls[sel_wall_idx - 1]]

            active_wins = []
            for wk in target_walls:
                for w in _get_wall_windows(wk):
                    if not w.get("removed", False):
                        active_wins.append((wk, w))

            if not active_wins:
                st.info("لا توجد شبابيك نشطة في النطاق المختار.")
            else:
                for wk, winfo in active_wins:
                    wid = winfo["id"]
                    wname = wm_win.get(wid) or winfo.get("name") or f"W_{wid}"
                    wlbl = _wall_display_label(wk, cm, wm)
                    
                    with st.container():
                        st.markdown(
                            f"""<div style='background:#F8F9FA;border:1px solid #E2E8F0;border-right:5px solid #004488;
                                border-radius:6px;padding:8px 12px;margin-bottom:6px;' dir='rtl'>
                                <div style='display:flex;justify-content:space-between;align-items:center;'>
                                    <div>
                                        <b style='font-size:1.02rem;color:#004488;'>🪟 شباك {wname} [{winfo.get('type_label','W1')}]</b>
                                        <span style='color:#555;font-size:0.86rem;margin-right:12px;'>
                                            (عرض {float(winfo.get('w_m',1.0)):.2f}م × ارتفاع {float(winfo.get('h_m',1.2)):.2f}م | بعد البداية: {float(winfo.get('pos_m',0.0)):.2f}م)
                                        </span>
                                    </div>
                                    <div style='color:#666;font-size:0.82rem;'>على {wlbl}</div>
                                </div>
                            </div>""",
                            unsafe_allow_html=True
                        )
                        
                        # رسالة تأكيد الحذف الخاصة بالشباك
                        if st.session_state.get(f"m12_del_sec_conf_win_{wid}"):
                            st.warning(f"⚠️ تأكيد حذف الشباك {wname} من {wlbl}؟")
                            c_y, c_n = st.columns(2)
                            with c_y:
                                if st.button(f"💥 تأكيد: حذف الشباك {wname}", key=f"m12_btn_sec_conf_del_win_yes_{wid}", use_container_width=True):
                                    _remove_opening_by_id(wid, "win")
                                    st.session_state.pop(f"m12_del_sec_conf_win_{wid}", None)
                                    st.rerun()
                            with c_n:
                                if st.button("❌ إلغاء", key=f"m12_btn_sec_conf_del_win_no_{wid}", use_container_width=True):
                                    st.session_state.pop(f"m12_del_sec_conf_win_{wid}", None)
                                    st.rerun()
                        else:
                            if st.button(f"🗑️ حذف الشباك {wname}", key=f"m12_btn_sec_del_win_{wid}", use_container_width=True):
                                st.session_state[f"m12_del_sec_conf_win_{wid}"] = True
                                st.rerun()

    # ═══════════════════════════════════════════════════════════════════════
    # التبويبة 2: حذف الأبواب
    # ═══════════════════════════════════════════════════════════════════════
    with td:
        st.markdown("<h5 style='color:#2E7D32;margin-bottom:8px;'>🗑️ حذف الأبواب القائمة</h5>", unsafe_allow_html=True)
        if not active_walls:
            st.info("لا توجد حوائط نشطة في المشروع.")
        else:
            wall_options_d = ["— كافة الحوائط النشطة —"] + [f"حائط {_wall_display_label(w, cm, wm)}" for w in active_walls]
            sel_wall_idx_d = st.selectbox("تصفية الأبواب حسب الحائط:", options=range(len(wall_options_d)),
                                          format_func=lambda idx: wall_options_d[idx], key="m12_del_d_wall_filter")
            
            target_walls_d = active_walls if sel_wall_idx_d == 0 else [active_walls[sel_wall_idx_d - 1]]

            active_doors = []
            for wk in target_walls_d:
                for d in _get_wall_doors(wk):
                    if not d.get("removed", False):
                        active_doors.append((wk, d))

            if not active_doors:
                st.info("لا توجد أبواب نشطة في النطاق المختار.")
            else:
                for wk, dinfo in active_doors:
                    did = dinfo["id"]
                    dname = wm_door.get(did) or dinfo.get("name") or f"D_{did}"
                    wlbl = _wall_display_label(wk, cm, wm)
                    
                    with st.container():
                        st.markdown(
                            f"""<div style='background:#F8F9FA;border:1px solid #E2E8F0;border-right:5px solid #2E7D32;
                                border-radius:6px;padding:8px 12px;margin-bottom:6px;' dir='rtl'>
                                <div style='display:flex;justify-content:space-between;align-items:center;'>
                                    <div>
                                        <b style='font-size:1.02rem;color:#2E7D32;'>🚪 باب {dname} [{dinfo.get('type_label','D1')}]</b>
                                        <span style='color:#555;font-size:0.86rem;margin-right:12px;'>
                                            (عرض {float(dinfo.get('w_m',0.9)):.2f}م × ارتفاع {float(dinfo.get('h_m',2.1)):.2f}م | بعد البداية: {float(dinfo.get('pos_m',0.0)):.2f}م | ضلفة {dinfo.get('leaf_dir','')})
                                        </span>
                                    </div>
                                    <div style='color:#666;font-size:0.82rem;'>على {wlbl}</div>
                                </div>
                            </div>""",
                            unsafe_allow_html=True
                        )
                        
                        # رسالة تأكيد الحذف الخاصة بالباب
                        if st.session_state.get(f"m12_del_sec_conf_door_{did}"):
                            st.warning(f"⚠️ تأكيد حذف الباب {dname} من {wlbl}؟")
                            c_y_d, c_n_d = st.columns(2)
                            with c_y_d:
                                if st.button(f"💥 تأكيد: حذف الباب {dname}", key=f"m12_btn_sec_conf_del_door_yes_{did}", use_container_width=True):
                                    _remove_opening_by_id(did, "door")
                                    st.session_state.pop(f"m12_del_sec_conf_door_{did}", None)
                                    st.rerun()
                            with c_n_d:
                                if st.button("❌ إلغاء", key=f"m12_btn_sec_conf_del_door_no_{did}", use_container_width=True):
                                    st.session_state.pop(f"m12_del_sec_conf_door_{did}", None)
                                    st.rerun()
                        else:
                            if st.button(f"🗑️ حذف الباب {dname}", key=f"m12_btn_sec_del_door_{did}", use_container_width=True):
                                st.session_state[f"m12_del_sec_conf_door_{did}"] = True
                                st.rerun()


def _compute_plaster_survey():
    """
    حساب حصر كميات ومواد أعمال البياض (المحارة) طبقاً للكود المصري لأعمال البياض:
    - حساب مساحة كل وجه محدد (Gross Area = Length × Height).
    - حصر الفتحات (الأبواب والشبابيك) وخصمها لكل وجه محدد (Deductions = Σ (w × h)).
    - صافي المسطح (Net Area = Gross - Deductions).
    - استهلاك الرمل: 1 م³ رمل لكل 42 م² مسطح صافي، مع 5% هالك تشغيل:
        Sand_m3 = (Net Area / 42.0) * 1.05
    - استهلاك الأسمنت: 350 كجم أسمنت لكل 1 م³ رمل (7 شكاير / م³):
        Cement_kg = Sand_m3 * 350.0
        Cement_tons = Cement_kg / 1000.0
        Cement_bags = ceil(Cement_kg / 50.0)
    """
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m12_wall_removed", set())
    plaster_faces_map = st.session_state.get("m12_plaster_faces", {})
    default_h = float(st.session_state.get("m12_default_wall_height", 3.0))
    cm = _get_col_name_map()
    wm = _get_wall_name_map()

    rows = []
    tot_gross = 0.0
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

        # حصر الفتحات النشطة على الحائط
        single_face_op = 0.0
        for wi in _get_wall_windows(wk):
            if not wi.get("removed", False):
                single_face_op += float(wi.get("w_m", 1.0)) * float(wi.get("h_m", 1.2))
        for di in _get_wall_doors(wk):
            if not di.get("removed", False):
                single_face_op += float(di.get("w_m", 0.9)) * float(di.get("h_m", 2.1))

        wall_ded = single_face_op * n_faces
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
            "إجمالي مساحة الفتحات المخصومة (m^2)": round(wall_ded, 2),
            "صافي مسطح المحارة النهائي (m^2)": round(wall_net, 2),
            "كمية الرمل المطلوبة (m^3)": round(sand_m3, 2),
            "كمية الأسمنت (طن)": round(cement_tons, 2),
            "شكاير الأسمنت (50 كجم)": cement_bags,
            "كمية الأسمنت المطلوبة": f"{cement_tons:.2f} طن ({cement_bags} شكارة)",
        })

        tot_gross += wall_gross
        tot_ded += wall_ded
        tot_net += wall_net
        tot_sand += sand_m3
        tot_cement_kg += cement_kg

    tot_cement_tons = tot_cement_kg / 1000.0
    tot_cement_bags = math.ceil(tot_cement_kg / 50.0) if tot_cement_kg > 0 else 0

    return {
        "rows": rows,
        "tot_gross": tot_gross,
        "tot_ded": tot_ded,
        "tot_net": tot_net,
        "tot_sand": tot_sand,
        "tot_cement_kg": tot_cement_kg,
        "tot_cement_tons": tot_cement_tons,
        "tot_cement_bags": tot_cement_bags,
        "active_walls_count": len(rows),
    }


def _section_plaster_walls():
    """
    قسم تحديد وحصر حوائط المحارة (Plaster Walls Calculation & Visualization).
    - اختيار الحائط وتعديل أوجه المحارة.
    - تحديد الاتجاه ديناميكياً:
        * حائط أفقي: [أعلى | أسفل]
        * حائط رأسي: [يمين | يسار]
    - تفاعل وتحديث بصري لحظي على الـ Canvas.
    - حصر فوري لمسطحات المحارة والخامات طبقاً للكود المصري.
    """
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        st.info("💡 أدخل على الأقل محورين في كل اتجاه أولاً.")
        return

    all_walls = _get_all_walls()
    if not all_walls:
        st.info("💡 لا توجد حوائط متصلة بين المحاور.")
        return

    removed_walls = st.session_state.get("m12_wall_removed", set())
    active_walls = [wk for wk in all_walls if wk not in removed_walls]
    if not active_walls:
        st.info("💡 لا توجد حوائط نشطة بالمشروع. استعد بعض الحوائط المحذوفة أولاً.")
        return

    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    plaster_faces_map = st.session_state.setdefault("m12_plaster_faces", {})

    st.markdown(
        """<div style='background:#f8fafc;border:1px solid #cbd5e1;border-right:4px solid #1e3a8a;
            border-radius:6px;padding:8px 12px;margin-bottom:10px;font-size:0.87rem;' dir='rtl'>
            <b style='color:#1e3a8a;font-size:0.95rem;'>🎨 تحديد وتعديل أوجه المحارة (Plaster Faces):</b><br>
            <span style='color:#475569;'>
            اختر الحائط وحدد الوجه المطلوب لتطبيق تهشير أزرق غامق بخطوط خضراء فوراً على الرسم وحصر الخامات بدقة.
            </span>
        </div>""",
        unsafe_allow_html=True
    )

    # 1. قائمة اختيار الحائط
    def _plaster_wall_label(idx):
        wk = active_walls[idx]
        i1, j1, i2, j2 = wk
        is_h = (j1 == j2)
        disp = _wall_display_label(wk, cm, wm)
        cur_faces = plaster_faces_map.get(wk, [])
        valid_faces = [f for f in cur_faces if (f in (["أعلى", "أسفل"] if is_h else ["يمين", "يسار"]))]
        if not valid_faces:
            status = "⚪ بدون محارة"
        elif len(valid_faces) == 2:
            status = "🟢 كلا الوجهين"
        else:
            status = f"🟢 وجه ({valid_faces[0]})"
        orient = "أفقي" if is_h else "رأسي"
        return f"{disp} [{orient}] — {status}"

    _safe_idx("m12_plaster_sel_wall", len(active_walls))
    sel_idx = st.selectbox(
        "اختيار أوجه المحارة (تعديل أوجه المحارة)",
        options=range(len(active_walls)),
        format_func=_plaster_wall_label,
        key="m12_plaster_sel_wall"
    )
    sel_wk = active_walls[sel_idx]
    i1, j1, i2, j2 = sel_wk
    is_h = (j1 == j2)

    # 2. تحديد الخيارات المتاحة ديناميكياً طبقاً لزاوية ومحور الحائط
    # إذا كان أفقياً: [أعلى | أسفل]
    # إذا كان رأسياً: [يمين | يسار]
    available_options = ["أعلى", "أسفل"] if is_h else ["يمين", "يسار"]
    current_faces = [f for f in plaster_faces_map.get(sel_wk, []) if f in available_options]

    orient_str = "أفقي (محور Y)" if is_h else "رأسي (محور X)"
    st.markdown(
        f"<div style='font-size:0.85rem;color:#334155;margin-bottom:4px;' dir='rtl'>"
        f"<b>محور الحائط:</b> {orient_str} &nbsp;|&nbsp; "
        f"<b>الخيارات المتاحة:</b> {' | '.join(available_options)}"
        f"</div>",
        unsafe_allow_html=True
    )

    ms_key = f"m12_plaster_ms_{sel_wk[0]}_{sel_wk[1]}_{sel_wk[2]}_{sel_wk[3]}"
    ms_stage_key = f"m12_plaster_ms_stage_{sel_wk[0]}_{sel_wk[1]}_{sel_wk[2]}_{sel_wk[3]}"

    # ── تطبيق القيمة المُعلَّقة (staged) من الزر قبل رسم الـ widget
    if ms_stage_key in st.session_state:
        st.session_state[ms_key] = st.session_state.pop(ms_stage_key)

    # ── تهيئة القيمة الأولى فقط إن لم يوجد ms_key بعد
    if ms_key not in st.session_state:
        st.session_state[ms_key] = list(current_faces)

    def _on_plaster_ms_change():
        new_val = st.session_state.get(ms_key, [])
        pfm = st.session_state.setdefault("m12_plaster_faces", {})
        pfm[sel_wk] = list(new_val)
        st.session_state["m12_plaster_faces"] = pfm
        save_settings()

    st.multiselect(
        "اتجاه المحارة",
        options=available_options,
        key=ms_key,
        on_change=_on_plaster_ms_change,
        help="اختر وجهاً واحداً أو كلا الوجهين، أو احذف الوجه لإلغاء التحديد."
    )

    # أزرار تحكم سريعة للوجه
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("✨ تفعيل كلا الوجهين", key=f"m12_btn_both_{sel_wk[0]}_{sel_wk[1]}_{sel_wk[2]}_{sel_wk[3]}", use_container_width=True):
            plaster_faces_map[sel_wk] = list(available_options)
            st.session_state["m12_plaster_faces"] = plaster_faces_map
            # نستخدم staging key لأن الـ widget رُسم بالفعل في هذا الـ run
            st.session_state[ms_stage_key] = list(available_options)
            save_settings()
            st.rerun()
    with c_btn2:
        if st.button("🗑️ إلغاء المحارة لهذا الحائط", key=f"m12_btn_clear_{sel_wk[0]}_{sel_wk[1]}_{sel_wk[2]}_{sel_wk[3]}", use_container_width=True):
            plaster_faces_map[sel_wk] = []
            st.session_state["m12_plaster_faces"] = plaster_faces_map
            # نستخدم staging key لأن الـ widget رُسم بالفعل في هذا الـ run
            st.session_state[ms_stage_key] = []
            save_settings()
            st.rerun()

    # إجراءات جماعية سريعة للمشروع
    with st.expander("⚡ إجراءات جماعية سريعة لكافة الحوائط", expanded=False):
        c_all1, c_all2 = st.columns(2)
        with c_all1:
            if st.button("➕ تفعيل كلا الوجهين للكل", key="m12_plaster_all_both", use_container_width=True):
                for wk in active_walls:
                    is_wk_h = (wk[1] == wk[3])
                    plaster_faces_map[wk] = ["أعلى", "أسفل"] if is_wk_h else ["يمين", "يسار"]
                st.session_state["m12_plaster_faces"] = plaster_faces_map
                save_settings()
                st.rerun()
        with c_all2:
            if st.button("🧹 مسح محارة كافة الحوائط", key="m12_plaster_clear_all", use_container_width=True):
                for wk in active_walls:
                    plaster_faces_map[wk] = []
                st.session_state["m12_plaster_faces"] = plaster_faces_map
                save_settings()
                st.rerun()

    # بطاقة فحص سريع للحائط المختار
    default_h = float(st.session_state.get("m12_default_wall_height", 3.0))
    sel_len = _wall_length_m(sel_wk)
    sel_h = _get_wall_height(sel_wk, default_h)
    sel_active_faces = [f for f in plaster_faces_map.get(sel_wk, []) if f in available_options]
    n_sel_faces = len(sel_active_faces)
    sel_gross = sel_len * sel_h * n_sel_faces

    sel_op = 0.0
    for wi in _get_wall_windows(sel_wk):
        if not wi.get("removed", False):
            sel_op += float(wi.get("w_m", 1.0)) * float(wi.get("h_m", 1.2))
    for di in _get_wall_doors(sel_wk):
        if not di.get("removed", False):
            sel_op += float(di.get("w_m", 0.9)) * float(di.get("h_m", 2.1))
    sel_ded = sel_op * n_sel_faces
    sel_net = max(0.0, sel_gross - sel_ded)
    sel_sand = (sel_net / 42.0) * 1.05 if sel_net > 0 else 0.0
    sel_cement_kg = sel_sand * 350.0
    sel_cement_tons = sel_cement_kg / 1000.0
    sel_cement_bags = math.ceil(sel_cement_kg / 50.0) if sel_cement_kg > 0 else 0

    st.markdown(
        f"""<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:8px 12px;margin:8px 0;' dir='rtl'>
            <div style='font-weight:bold;color:#166534;font-size:0.88rem;'>
                🔍 بيانات محارة الحائط المختار ({_wall_display_label(sel_wk, cm, wm)}):
            </div>
            <div style='display:grid;grid-template-columns:repeat(auto-fit, minmax(130px, 1fr));gap:6px;font-size:0.80rem;color:#1e293b;margin-top:4px;'>
                <div>• الطول: <b>{sel_len:.2f} م</b></div>
                <div>• الارتفاع: <b>{sel_h:.2f} م</b></div>
                <div>• الأوجه: <b>{n_sel_faces} وجه ({' + '.join(sel_active_faces) if sel_active_faces else 'لا يوجد'})</b></div>
                <div>• الإجمالي: <b>{sel_gross:.2f} م²</b></div>
                <div>• الفتحات المخصومة: <b>{sel_ded:.2f} م²</b></div>
                <div>• الصافي: <b style='color:#15803d;'>{sel_net:.2f} م²</b></div>
            </div>
            <div style='font-size:0.80rem;color:#1e3a8a;margin-top:4px;border-top:1px dashed #bbf7d0;padding-top:4px;'>
                📦 <b>الخامات للحائط:</b> رمل: <b>{sel_sand:.2f} م³</b> | أسمنت: <b>{sel_cement_tons:.2f} طن ({sel_cement_bags} شكارة)</b>
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    st.divider()

    # 4. جدول حصر كميات المحارة
    st.markdown("<b style='font-size:0.95rem;color:#0f172a;'>📋 جدول حصر حوائط المحارة والخامات (طبقاً للكود المصري):</b>", unsafe_allow_html=True)

    p_res = _compute_plaster_survey()
    p_rows = p_res["rows"]

    if not p_rows:
        st.info("💡 لم يتم تفعيل المحارة لأي حائط بعد. قم باختيار أوجه المحارة للحوائط أعلاه لتظهر النتائج والكميات.")
    else:
        # تجهيز جدول الحصر المطلوب في المواصفات
        display_rows = []
        for r in p_rows:
            display_rows.append({
                "الحائط": r["الحائط"],
                "الوجه المحدد": r["الوجه المحدد"],
                "إجمالي مسطح المحارة (m^2)": r["إجمالي مسطح المحارة (m^2)"],
                "إجمالي مساحة الفتحات المخصومة (m^2)": r["إجمالي مساحة الفتحات المخصومة (m^2)"],
                "صافي مسطح المحارة النهائي (m^2)": r["صافي مسطح المحارة النهائي (m^2)"],
                "كمية الرمل المطلوبة (m^3)": r["كمية الرمل المطلوبة (m^3)"],
                "كمية الأسمنت المطلوبة": r["كمية الأسمنت المطلوبة"],
            })

        tot_display = {
            "الحائط": "✅ الإجمالي",
            "الوجه المحدد": f"{sum(r['عدد الأوجه'] for r in p_rows)} وجه",
            "إجمالي مسطح المحارة (m^2)": round(p_res["tot_gross"], 2),
            "إجمالي مساحة الفتحات المخصومة (m^2)": round(p_res["tot_ded"], 2),
            "صافي مسطح المحارة النهائي (m^2)": round(p_res["tot_net"], 2),
            "كمية الرمل المطلوبة (m^3)": round(p_res["tot_sand"], 2),
            "كمية الأسمنت المطلوبة": f"{p_res['tot_cement_tons']:.2f} طن ({p_res['tot_cement_bags']} شكارة)",
        }

        df_p = pd.DataFrame(display_rows + [tot_display])
        def _st_plaster(row):
            if row["الحائط"] == "✅ الإجمالي":
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
            key="m12_dl_plaster_sec"
        )

    # رسالة إرشادية (Information Note)
    st.markdown(
        """<div style='background-color:#eff6ff;border-right:4px solid #2563eb;border-radius:8px;padding:12px 16px;margin-top:10px;color:#1e3a8a;font-size:0.87rem;line-height:1.7;' dir='rtl'>
            <div style='font-weight:bold;margin-bottom:4px;display:flex;align-items:center;gap:6px;'>
                <span>💡</span>
                <span>رسالة إرشادية (Information Note) — الفرضيات ومعدلات الاستهلاك المعتمدة:</span>
            </div>
            <div>
                تم تقدير كميات المونة بناءً على مواصفات الكود المصري لسمك بياض متوسط <b>2 سم</b> شاملاً الطرطشة والملء، بمعدل استهلاك تقريبي: <b>1 m³ رمل + 350 كجم أسمنت لكل 40-45 m² مسطح</b>، مع اعتبار نسبة هالك <b>5%</b>.
            </div>
        </div>""",
        unsafe_allow_html=True
    )


def _prepare_3d_scene_data():
    """
    تجهيز وتوليد البيانات الهندسية للمجسمات ثلاثية الأبعاد (Data Processing & 3D Modeling):
    - الحوائط (Walls): مجسمات ثلاثية الأبعاد مع كامل بيانات الحصر والمساحات للـ Inspector.
    - الأعمدة (Columns): أعمدة إنشائية خرسانية بارزة واضحة في التقاطعات مع الأبعاد.
    - النوافذ (Windows): مجسمات زجاجية وإطارات مع مقابض تحريك وبيانات هندسية وخلوص أمان.
    - الأبواب (Doors): مجسمات أبواب معمارية مع مقابض تحريك وبيانات هندسية كاملة.
    """
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    if len(xs) < 2 or len(ys) < 2:
        return None

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cx_mid = (min_x + max_x) / 2.0
    cy_mid = (min_y + max_y) / 2.0
    span_x = max_x - min_x
    span_y = max_y - min_y

    dh = float(st.session_state.get("m12_default_wall_height", st.session_state.get("m12_default_h_input", 3.0)))
    ph = float(st.session_state.get("m12_parapet_wall_height", st.session_state.get("m12_parapet_h_input", 1.0)))

    # خرائط الأسماء
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()

    # أبعاد الطوب لحسابات الحصر في الـ Inspector
    brick_size_v = st.session_state.get("m12_brick_size", "25×12×6")
    mortar_v = float(st.session_state.get("m12_mortar_thickness_cm", 1.0))
    if brick_size_v == _CUSTOM_SIZE_LABEL:
        b_l = float(st.session_state.get("m12_brick_custom_l", 25.0))
        b_w = float(st.session_state.get("m12_brick_custom_w", 12.0))
        b_h = float(st.session_state.get("m12_brick_custom_h", 6.0))
    else:
        b_l, b_w, b_h = _parse_brick_size(brick_size_v)

    # 1. الأعمدة (Columns)
    all_cols = _get_all_columns()
    removed_cols = st.session_state.get("m12_col_removed", set())
    columns_data = []
    col_height = dh + 0.08  # بارزة طفيفاً فوق الحوائط للوضوح الإنشائي

    for (i, j) in all_cols:
        if (i, j) in removed_cols:
            continue
        cx, cy = _col_center(i, j)
        cw, cd = _get_col_wh(i, j)
        c_name = cm.get((i, j), f"C({i+1},{j+1})")
        columns_data.append({
            "id": f"col_{i}_{j}",
            "name": c_name,
            "grid": f"X{i+1} - Y{j+1}",
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
    removed_walls = st.session_state.get("m12_wall_removed", set())
    plaster_walls = st.session_state.get("m12_plaster_walls", set())
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

    plan_b64 = st.session_state.get("m12_plan_png_b64", "")
    if not plan_b64:
        try:
            pbuf = _draw_plan()
            if pbuf:
                plan_b64 = base64.b64encode(pbuf.getvalue()).decode("utf-8")
                st.session_state["m12_plan_png_b64"] = plan_b64
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
    border-color: #0284c7;
    color: #38bdf8;
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
    color: #38bdf8;
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
    color: #38bdf8;
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
    color: #38bdf8;
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
  .insp-val b { color: #38bdf8; }
  .insp-section-title {
    font-size: 11px;
    font-weight: 700;
    color: #38bdf8;
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

  /* ── شارات الأبعاد الثلاثية الأبعاد باللون اللبني (Live 3D Dimensions Badges) ── */
  .dim-badge {
    position: absolute;
    background: rgba(15, 23, 42, 0.94);
    border: 1.5px solid #38bdf8;
    color: #38bdf8;
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
  </div>
  <div class="tb-group">
    <span class="badge-legend" style="color:#f1f5f9;"><span class="dot" style="background:#cbd5e1; border:1px solid #94a3b8;"></span> حائط كامل (وحدة واحدة)</span>
    <span class="badge-legend" style="color:#cbd5e1;"><span class="dot" style="background:#475569; border:1px solid #334155;"></span> أعمدة</span>
    <span class="badge-legend" style="color:#38bdf8;"><span class="dot" style="background:#38bdf8; opacity:0.85; border:1px solid #0284c7;"></span> شبابيك (مقبض ⟷)</span>
    <span class="badge-legend" style="color:#f59e0b;"><span class="dot" style="background:#b45309; border:1px solid #f59e0b;"></span> أبواب (مقبض ⟷)</span>
  </div>
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
      <img src="data:image/png;base64,__PLAN_B64__" alt="Floor Plan — Module 12: Brick & Plastering Survey" class="mini-plan-img" id="mini-plan-img" />
      <div class="mini-plan-zoom-hint">🔍 انقر للتكبير</div>
    </div>
    <div class="mini-plan-caption">Floor Plan — Module 12: Brick & Plastering Survey</div>
  </div>
</div>

<!-- نافذة تكبير المسقط (Lightbox Modal) -->
<div id="plan-modal" class="plan-modal">
  <div class="plan-modal-backdrop" id="modal-backdrop"></div>
  <div class="plan-modal-content">
    <div class="plan-modal-header">
      <span>📐 Floor Plan — Module 12: Brick & Plastering Survey</span>
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
  const parapetWallMat = new THREE.MeshStandardMaterial({ color: 0xbac7d5, roughness: 0.80, metalness: 0.05 });
  const wallEdgeMat = new THREE.LineBasicMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.60 });

  const colMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.90, metalness: 0.10 });
  const colEdgeMat = new THREE.LineBasicMaterial({ color: 0x1e293b, transparent: true, opacity: 0.75 });

  const winMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.50, roughness: 0.10, metalness: 0.25 });
  const winEdgeMat = new THREE.LineBasicMaterial({ color: 0x0284c7, transparent: true, opacity: 0.85 });

  const doorMat = new THREE.MeshStandardMaterial({ color: 0x92400e, roughness: 0.60, metalness: 0.15 });
  const doorEdgeMat = new THREE.LineBasicMaterial({ color: 0x78350f, transparent: true, opacity: 0.90 });
  const doorKnobMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.20, metalness: 0.80 });

  // Handle Materials (Always visible with depthTest false and bright emissive)
  const handleMat = new THREE.MeshStandardMaterial({
    color: 0xfbbf24,
    emissive: 0xd97706,
    emissiveIntensity: 0.8,
    roughness: 0.2,
    metalness: 0.5,
    depthTest: false
  });
  const handleHoverMat = new THREE.MeshStandardMaterial({
    color: 0x38bdf8,
    emissive: 0x0284c7,
    emissiveIntensity: 0.9,
    roughness: 0.15,
    metalness: 0.6,
    depthTest: false
  });
  const handleDragMat = new THREE.MeshStandardMaterial({
    color: 0x34d399,
    emissive: 0x059669,
    emissiveIntensity: 0.9,
    roughness: 0.15,
    metalness: 0.6,
    depthTest: false
  });
  const handleWarnMat = new THREE.MeshStandardMaterial({
    color: 0xf87171,
    emissive: 0xdc2626,
    emissiveIntensity: 1.0,
    roughness: 0.15,
    metalness: 0.6,
    depthTest: false
  });

  // Selection Outline Material (Bright cyan glow)
  const highlightMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 2.5, depthTest: false, transparent: true, opacity: 0.98 });

  // 3D Dimension Lines Material
  const dimLineMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, depthTest: false, transparent: true, opacity: 0.95 });

  // Collections for Raycasting & Selection
  const selectableObjects = [];
  const handleMeshes = [];
  const wallGroups = {};
  const allOpenings = [];
  const openingMeshesById = {};

  // 1. Columns (الأعمدة)
  (data.columns || []).forEach(function(c) {
    const geom = new THREE.BoxGeometry(c.w, c.h, c.d);
    const mesh = new THREE.Mesh(geom, colMat);
    mesh.position.set(c.x, c.y, c.z);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom), colEdgeMat);
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
    const mesh = new THREE.Mesh(geom, w.is_parapet ? parapetWallMat : wallMat);
    mesh.position.set(w.x, w.y, w.z);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom), wallEdgeMat);
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

  // ── إنشاء مقبض ثلاثي الأبعاد بارز وواضح تماماً في وسط الفتحة ──
  function create3DHandle(op, isDoor) {
    const hGroup = new THREE.Group();
    const isH = op.is_h;

    // Bar dimensions - prominent horizontal grip bar
    const barLen = Math.max(0.45, Math.min(0.85, op.w_m * 0.50));
    const barRad = 0.055;
    const barGeom = new THREE.CylinderGeometry(barRad, barRad, barLen, 16);
    const barMesh = new THREE.Mesh(barGeom, handleMat);
    barMesh.renderOrder = 998;
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
    cone1.renderOrder = 998;
    cone2.renderOrder = 998;

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
    sphereMesh.renderOrder = 998;
    hGroup.add(sphereMesh);

    // Outer prominent ring
    const ringGeom = new THREE.TorusGeometry(0.12, 0.022, 12, 24);
    const ringMesh = new THREE.Mesh(ringGeom, handleMat);
    ringMesh.renderOrder = 998;
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
    hitBoxMesh.renderOrder = 998;
    hitBoxMesh.userData = { isHitBox: true, isHandle: true, op: op };
    hGroup.add(hitBoxMesh);

    // Position handle at the center of the opening where it is open space (NOT inside lintel!)
    const yHandle = isDoor ? (op.h / 2.0) : op.y;
    hGroup.position.set(op.x, yHandle, op.z);
    hGroup.renderOrder = 998;

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
    const mesh = new THREE.Mesh(geom, winMat);
    mesh.position.set(win.x, win.y, win.z);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom), winEdgeMat);
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
    const mesh = new THREE.Mesh(geom, doorMat);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom), doorEdgeMat);
    mesh.add(edges);
    doorGroup.add(mesh);

    // Decorative door knob / handle (أكرة الباب)
    const knobGeom = new THREE.CylinderGeometry(0.02, 0.02, 0.08, 8);
    const knob = new THREE.Mesh(knobGeom, doorKnobMat);
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

  // Selection Highlight Outline
  let selectedObject = null;
  let highlightWire = null;

  function clearSelection() {
    if (highlightWire) {
      scene.remove(highlightWire);
      highlightWire.geometry.dispose();
      highlightWire = null;
    }
    if (selectedObject && selectedObject.userData && selectedObject.userData.elementType === 'wall') {
      selectedObject.children.forEach(c => {
        if (c.material && c.userData && c.userData.origColor !== undefined) {
          c.material.color.setHex(c.userData.origColor);
        }
      });
    }
    selectedObject = null;
    hideDimensionLines();
    document.getElementById('inspector-card').style.display = 'none';
  }

  // ── تحديد واختيار العنصر مع إبراز الحائط بالكامل كوحدة واحدة ──
  function setSelection(obj, elemType, elemData) {
    clearSelection();
    selectedObject = obj;

    if (elemType === 'wall') {
      // اختيار الحائط بالكامل كوحدة واحدة متكاملة
      const box = new THREE.Box3().setFromObject(obj);
      const size = new THREE.Vector3();
      box.getSize(size);
      const center = new THREE.Vector3();
      box.getCenter(center);

      // إطار سلكي مضيء يحيط بالحائط بالكامل من أوله إلى آخره
      const wireGeo = new THREE.BoxGeometry(size.x + 0.08, size.y + 0.08, size.z + 0.08);
      highlightWire = new THREE.LineSegments(new THREE.EdgesGeometry(wireGeo), highlightMat);
      highlightWire.position.copy(center);
      highlightWire.renderOrder = 998;
      scene.add(highlightWire);

      // تمييز كتل الحائط بالكامل بلون ناصع
      obj.children.forEach(c => {
        if (c.material) {
          c.userData = c.userData || {};
          if (c.userData.origColor === undefined) c.userData.origColor = c.material.color.getHex();
          c.material.color.setHex(0xe2e8f0);
        }
      });
    } else {
      // الشباك أو الباب أو العمود كوحدة منفصلة ومحددة
      const box = new THREE.Box3().setFromObject(obj);
      const size = new THREE.Vector3();
      box.getSize(size);
      const center = new THREE.Vector3();
      box.getCenter(center);

      const wireGeo = new THREE.BoxGeometry(size.x + 0.06, size.y + 0.06, size.z + 0.06);
      highlightWire = new THREE.LineSegments(new THREE.EdgesGeometry(wireGeo), highlightMat);
      highlightWire.position.copy(center);
      highlightWire.renderOrder = 998;
      scene.add(highlightWire);
    }

    showInspector(elemType, elemData);

    if (elemType === 'window' || elemType === 'door') {
      showDimensionLines(elemData);
    } else {
      hideDimensionLines();
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
      const parapetBadge = d.is_parapet ? '<span style="color:#38bdf8;font-size:10px;margin-right:5px;">[دروة سطح]</span>' : '';
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
            <span class="insp-val"><b style="font-size:13px;color:#38bdf8;">${d.net_area.toFixed(2)} م²</b></span>
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
      `;
    } else if (type === 'window' || type === 'door') {
      const isWin = (type === 'window');
      inspIcon.textContent = isWin ? '🪟' : '🚪';
      inspHeader.textContent = isWin ? 'فاحص مواصفات الشباك' : 'فاحص مواصفات الباب';
      const tagClass = isWin ? 'win-tag' : 'door-tag';
      const kindAr = isWin ? 'شباك' : 'باب';

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

        <div class="insp-actions">
          <button class="insp-btn" id="btn-focus-handle">🎯 تركيز الكاميرا على المقبض</button>
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
      `;
    }

    inspBody.innerHTML = html;

    const btnFocus = document.getElementById('btn-focus-handle');
    if (btnFocus && d.handleGroup) {
      btnFocus.addEventListener('click', function() {
        controls.target.set(d.handleGroup.position.x, d.handleGroup.position.y, d.handleGroup.position.z);
        controls.update();
        setHandleMaterial(d.handleGroup, handleHoverMat);
      });
    }
  }

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
          const input = window.parent.document.querySelector('input[aria-label="m12_3d_sync_payload"]');
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
          pUrl.searchParams.set('m12_op_move', jsonStr);
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

  function onPointerDown(e) {
    pointerDownPos.x = e.clientX;
    pointerDownPos.y = e.clientY;

    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    // 1. Check if clicked on a 3D Handle Gizmo
    const handleIntersects = raycaster.intersectObjects(handleMeshes, true);
    if (handleIntersects.length > 0) {
      let hitH = handleIntersects[0].object;
      while (hitH && !hitH.userData.isHandle && hitH.parent) {
        hitH = hitH.parent;
      }
      if (hitH && hitH.userData.isHandle) {
        startDraggingOpening(hitH.userData.op, e.clientX, e.clientY);
        return;
      }
    }
  }

  function onPointerMove(e) {
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    if (isDraggingOpening && activeOpening) {
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

        const inspPos = document.getElementById('insp-pos-val');
        if (inspPos) inspPos.innerHTML = `<b>${activeOpening.pos_m.toFixed(2)} م</b>`;
        const inspEnd = document.getElementById('insp-dist-end-val');
        if (inspEnd) inspEnd.innerHTML = `${(activeOpening.wall_len - activeOpening.pos_m - activeOpening.w_m).toFixed(2)} م`;

        hasPendingMove = true;
        lastMovedOp = activeOpening;
      }
    } else {
      // Hover feedback
      const handleIntersects = raycaster.intersectObjects(handleMeshes, true);
      if (handleIntersects.length > 0) {
        document.body.style.cursor = 'grab';
        let hitH = handleIntersects[0].object;
        while (hitH && !hitH.userData.isHandle && hitH.parent) {
          hitH = hitH.parent;
        }
        if (hitH && hitH.userData && hitH.userData.op && hitH.userData.op.handleGroup) {
          setHandleMaterial(hitH.userData.op.handleGroup, handleHoverMat);
        }
      } else {
        handleMeshes.forEach(h => {
          if (h !== activeHandle) setHandleMaterial(h, handleMat);
        });
        const objIntersects = raycaster.intersectObjects(selectableObjects, true);
        if (objIntersects.length > 0) {
          document.body.style.cursor = 'pointer';
        } else {
          document.body.style.cursor = 'default';
        }
      }
    }
  }

  function onPointerUp(e) {
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
      if (dist < 5) {
        const intersects = raycaster.intersectObjects(selectableObjects, true);
        if (intersects.length > 0) {
          let hit = intersects[0].object;
          while (hit && !hit.userData.elementType && hit.parent && hit.parent !== rootGroup && hit.parent !== scene) {
            hit = hit.parent;
          }

          if (hit && hit.userData && hit.userData.elementType) {
            const elType = hit.userData.elementType;
            if (elType === 'wall_piece' || elType === 'wall') {
              // اختار الحائط بالكامل كوحدة واحدة متكاملة
              const targetWallGroup = hit.userData.parentWallGroup || (elType === 'wall' ? hit : null);
              const targetData = (targetWallGroup && targetWallGroup.userData.data) || hit.userData.data;
              setSelection(targetWallGroup, 'wall', targetData);
            } else if (elType === 'window') {
              setSelection(hit, 'window', hit.userData.data);
            } else if (elType === 'door') {
              setSelection(hit, 'door', hit.userData.data);
            } else if (elType === 'column') {
              setSelection(hit, 'column', hit.userData.data);
            }
          }
        } else {
          clearSelection();
        }
      }
    }
  }

  container.addEventListener('pointerdown', onPointerDown);
  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp);

  // Camera Setup & State Preservation across Streamlit reruns
  const STORAGE_KEY = 'm12_threejs_camera_state';
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
        sessionStorage.setItem('m12_mini_plan_pos', JSON.stringify({
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
      sessionStorage.setItem('m12_mini_plan_visible', 'true');
    } catch(e) {}
  }

  function hidePlan() {
    miniCard.style.display = 'none';
    try {
      sessionStorage.setItem('m12_mini_plan_visible', 'false');
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
    renderer.render(scene, camera);
    updateDimensionBadgesScreen();
  }
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
        div[data-testid="stTextInput"]:has(input[aria-label="m12_3d_sync_payload"]) {
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
    sync_val = st.text_input(
        "m12_3d_sync_payload",
        value="",
        key="m12_3d_sync_input",
        label_visibility="collapsed"
    )
    if sync_val:
        _apply_3d_opening_move(sync_val)

    components.html(final_html, height=680, scrolling=False)


def _section_survey():
    res = _compute_survey()
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

    total_openings = op12 + op25

    # 3. حسابات المونة ومواد البناء طبقاً للكود المصري ECP:
    # - مباني 12 سم (نصف طوبة): 0.025 م3 رمل / م2 مسطح
    # - مباني 25 سم (طوبة كاملة): 0.200 م3 رمل / م3 مكعب
    # - نسبة هالك تشغيل طبيعي: 5% (× 1.05)
    sand_12 = n12 * 0.025
    sand_25 = v25 * 0.200
    sand_net = sand_12 + sand_25
    sand_total = sand_net * 1.05

    # محتوى الأسمنت في المونة طبقاً للكود المصري: 350 كجم أسمنت لكل 1 م3 رمل (7 شكاير / م3)
    cement_kg = sand_total * 350.0
    cement_tons = cement_kg / 1000.0
    cement_bags = math.ceil(cement_kg / 50.0) if cement_kg > 0 else 0

    # ── حساب عدد الطوب بناءً على النوع والمقاس المحدد من المستخدم (BOQ) ──
    brick_size_v = st.session_state.get("m12_brick_size", "25×12×6")
    mortar_v = float(st.session_state.get("m12_mortar_thickness_cm", 1.0))
    if brick_size_v == _CUSTOM_SIZE_LABEL:
        b_l = float(st.session_state.get("m12_brick_custom_l", 25.0))
        b_w = float(st.session_state.get("m12_brick_custom_w", 12.0))
        b_h = float(st.session_state.get("m12_brick_custom_h", 6.0))
    else:
        b_l, b_w, b_h = _parse_brick_size(brick_size_v)

    bricks_12 = _compute_brick_qty(n12, _WALL_THIN, b_l, b_w, b_h, mortar_v)
    bricks_25 = _compute_brick_qty(n25, _WALL_THICK, b_l, b_w, b_h, mortar_v)
    bricks_total = bricks_12 + bricks_25
    brick_type_display = st.session_state.get("m12_brick_type", "")
    brick_size_display = f"{b_l:.0f}×{b_w:.0f}×{b_h:.0f} سم" if brick_size_v == _CUSTOM_SIZE_LABEL else f"{brick_size_v} سم"



    # بطاقة الملخص التنفيذي للحصر (الأرقام المطلوبة كخطوط مباشرة وواضحة)
    st.markdown(
        f"""<div style='background-color:#ffffff;border:1.5px solid #cbd5e1;border-radius:10px;padding:16px 20px;margin-bottom:16px;box-shadow:0 2px 5px rgba(0,0,0,0.04);' dir='rtl'>
        <div style='display:flex;align-items:center;justify-content:space-between;border-bottom:2px solid #e2e8f0;padding-bottom:10px;margin-bottom:12px;'>
            <div style='font-weight:bold;font-size:1.05rem;color:#0f172a;display:flex;align-items:center;gap:8px;'>
                <span>📋</span>
                <span>الملخص الهندسي لحصر أعمال المباني والخامات (طبقاً للكود المصري ECP)</span>
            </div>
            <span style='background-color:#eff6ff;color:#1d4ed8;font-size:0.80rem;font-weight:bold;padding:3px 10px;border-radius:20px;border:1px solid #bfdbfe;'>
                حسابات دقيقة للمواد
            </span>
        </div>
        <div style='display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:12px;'>
            <div style='background-color:#fff7ed;border-right:4px solid #f97316;padding:10px 14px;border-radius:6px;'>
                <div style='font-size:0.82rem;color:#7c2d12;font-weight:bold;'>1️⃣ إجمالي مسطح طوب 12 سم (شامل الفتحات):</div>
                <div style='font-size:1.25rem;font-weight:bold;color:#c2410c;margin-top:4px;'>{g12:.2f} <span style='font-size:0.85rem;font-weight:normal;'>م² مسطح</span></div>
            </div>
            <div style='background-color:#f0fdf4;border-right:4px solid #16a34a;padding:10px 14px;border-radius:6px;'>
                <div style='font-size:0.82rem;color:#14532d;font-weight:bold;'>2️⃣ مساحة فتحات الأبواب والشبابيك:</div>
                <div style='font-size:1.25rem;font-weight:bold;color:#15803d;margin-top:4px;'>{op12:.2f} <span style='font-size:0.85rem;font-weight:normal;'>م² (لحوائط 12سم)</span> &nbsp;<span style='font-size:0.75rem;color:#4b5563;'>(الإجمالي العام: {total_openings:.2f} م²)</span></div>
            </div>
            <div style='background-color:#eff6ff;border-right:4px solid #2563eb;padding:10px 14px;border-radius:6px;'>
                <div style='font-size:0.82rem;color:#1e3a8a;font-weight:bold;'>3️⃣ صافي إجمالي مسطح طوب 12 سم:</div>
                <div style='font-size:1.25rem;font-weight:bold;color:#1d4ed8;margin-top:4px;'>{n12:.2f} <span style='font-size:0.85rem;font-weight:normal;'>م² مسطح صافي</span></div>
            </div>
            <div style='background-color:#fdf2f8;border-right:4px solid #db2777;padding:10px 14px;border-radius:6px;'>
                <div style='font-size:0.82rem;color:#831843;font-weight:bold;'>4️⃣ صافي إجمالي مكعب طوب 25 سم:</div>
                <div style='font-size:1.25rem;font-weight:bold;color:#be185d;margin-top:4px;'>{v25:.2f} <span style='font-size:0.85rem;font-weight:normal;'>م³ مكعب صافي</span></div>
            </div>
        </div>
        <div style='margin-top:12px;background:linear-gradient(to left, #f8fafc, #f1f5f9);border:1px solid #cbd5e1;border-radius:8px;padding:12px 16px;display:flex;align-items:center;justify-content:space-around;flex-wrap:wrap;gap:16px;'>
            <div style='display:flex;align-items:center;gap:10px;'>
                <span style='font-size:1.5rem;'>🏜️</span>
                <div>
                    <div style='font-size:0.80rem;color:#475569;font-weight:bold;'>5️⃣ إجمالي الرمل المطلوب للمباني (شامل 5% هالك):</div>
                    <div style='font-size:1.2rem;font-weight:bold;color:#0f172a;'>{sand_total:.2f} <span style='font-size:0.85rem;'>م³</span></div>
                </div>
            </div>
            <div style='height:36px;width:1px;background-color:#cbd5e1;'></div>
            <div style='display:flex;align-items:center;gap:10px;'>
                <span style='font-size:1.5rem;'>🏗️</span>
                <div>
                    <div style='font-size:0.80rem;color:#475569;font-weight:bold;'>5️⃣ إجمالي الأسمنت المطلوب (محتوى 350 كجم/م³):</div>
                    <div style='font-size:1.2rem;font-weight:bold;color:#0f172a;'>{cement_tons:.2f} <span style='font-size:0.85rem;'>طن</span> &nbsp;<span style='font-size:0.88rem;color:#2563eb;'>({cement_bags} شكارة سعة 50 كجم)</span></div>
                </div>
            </div>
            <div style='height:36px;width:1px;background-color:#cbd5e1;'></div>
            <div style='display:flex;align-items:center;gap:10px;'>
                <span style='font-size:1.5rem;'>🧱</span>
                <div>
                    <div style='font-size:0.80rem;color:#475569;font-weight:bold;'>عدد الطوب المطلوب ({brick_type_display} | {brick_size_display} | مونة {mortar_v}سم):</div>
                    <div style='font-size:1.2rem;font-weight:bold;color:#0f172a;'>{bricks_total:,} <span style='font-size:0.85rem;'>وحدة طوب</span></div>
                </div>
            </div>
        </div>
    </div>""",
        unsafe_allow_html=True
    )

    # 6. رسالة توضيحية لطريقة حساب كمية الرمل والأسمنت طبقاً للكود المصري
    with st.expander("💡 6️⃣ رسالة توضيحية: طريقة حساب كميات الرمل والأسمنت طبقاً للكود المصري وأصول التنفيذ", expanded=False):
        st.markdown(
            f"""<div style='line-height:1.8;font-size:0.88rem;color:#1e293b;' dir='rtl'>
            <p><b>استندت الحسابات التقديرية لكميات المونة ومواد البناء إلى المواصفات الفنية لبنود الأعمال بالكود المصري للبناء وأصول الصناعة:</b></p>
            <ol style='padding-right:20px;margin-bottom:12px;'>
                <li>
                    <b>أعمال مباني طوب سمك 12 سم (نصف طوبة):</b>
                    <br>• تُحصر هندسياً بالمتر المسطح (م²).
                    <br>• المساحة الصافية = المساحة الإجمالية للمسقط مطروحاً منها مساحة فتحات الأبواب والشبابيك.
                    <br>• معدل استهلاك الرمل لمونة البناء = <b>0.025 م³ رمل</b> لكل 1 م² مسطح مباني.
                    <br>• حساب عدد الطوب = يُحسب بدقة هندسية لكل حائط استناداً إلى المقاس المختار (<b>{brick_type_display} | {brick_size_display}</b>) وفاصل مونة <b>{mortar_v} سم</b>.
                </li>
                <li style='margin-top:8px;'>
                    <b>أعمال مباني طوب سمك 25 سم (طوبة كاملة):</b>
                    <br>• تُحصر هندسياً بالمتر المكعب (م³ = المساحة الصافية × 0.25 م).
                    <br>• معدل استهلاك الرمل لمونة البناء = <b>0.200 م³ رمل</b> لكل 1 م³ مكعب مباني (نسبة العراميس والمداميك).
                    <br>• حساب عدد الطوب = يُحسب بدقة هندسية لكل حائط استناداً إلى المقاس المختار (<b>{brick_type_display} | {brick_size_display}</b>) وفاصل مونة <b>{mortar_v} سم</b>.
                </li>
                <li style='margin-top:8px;'>
                    <b>نسبة خلط الأسمنت في مونة البناء (طبقاً لاشتراطات الكود المصري):</b>
                    <br>• نسبة الخلط القياسية لمونة ربط الطوب هي <b>350 كجم أسمنت بورتلاندي عادي لكل 1 م³ رمل</b> نظيف متدرج (ما يعادل <b>7 شكاير أسمنت</b> زنة 50 كجم لكل متر مكعب رمل).
                    <br>• إجمالي وزن الأسمنت (كجم) = حجم الرمل الإجمالي (م³) × 350 كجم.
                    <br>• وزن الأسمنت بالطن = الأسمنت (كجم) ÷ 1000، وعدد الشكاير = سقف تقريبي (الأسمنت كجم ÷ 50).
                </li>
                <li style='margin-top:8px;'>
                    <b>معامل الهالك والتشغيل (Waste Allowance):</b>
                    <br>• تم احتساب نسبة هالك قدرها <b>5%</b> مضافة إلى كميات الرمل والأسمنت لتعويض الفواقد الطبيعية أثناء التشوين والخلط والتشغيل في الموقع.
                </li>
            </ol>
        </div>""",
            unsafe_allow_html=True
        )

    t12, t25, tpl, tmat = st.tabs(["🧱 طوب 12 سم", "🏗️ طوب 25 سم", "🪣 ملخص المحارة", "📦 مقايسة الخامات والمونة"])

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
            key=f"m12_dl_{lbl}"
        )

    with t12:
        _rt(r12, "12 سم")

    with t25:
        _rt(r25, "25 سم")

    with tpl:
        st.markdown("<b style='font-size:1.05rem;color:#1e3a8a;'>🪣 حصر كميات ومواد أعمال البياض (المحارة)</b>", unsafe_allow_html=True)
        p_res = _compute_plaster_survey()
        p_rows = p_res["rows"]
        if not p_rows:
            st.info("💡 لم يتم تفعيل أوجه المحارة لأي حائط بعد. يرجى التوجه إلى قسم '9️⃣ تحديد حوائط المحارة' بالقائمة الجانبية لتحديد الأوجه المطلوبة.")
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
                    "إجمالي مسطح المحارة (m^2)": r["إجمالي مسطح المحارة (m^2)"],
                    "إجمالي مساحة الفتحات المخصومة (m^2)": r["إجمالي مساحة الفتحات المخصومة (m^2)"],
                    "صافي مسطح المحارة النهائي (m^2)": r["صافي مسطح المحارة النهائي (m^2)"],
                    "كمية الرمل المطلوبة (m^3)": r["كمية الرمل المطلوبة (m^3)"],
                    "كمية الأسمنت المطلوبة": r["كمية الأسمنت المطلوبة"],
                })

            tot_display = {
                "الحائط": "✅ الإجمالي",
                "الوجه المحدد": f"{sum(r['عدد الأوجه'] for r in p_rows)} وجه",
                "إجمالي مسطح المحارة (m^2)": round(p_res["tot_gross"], 2),
                "إجمالي مساحة الفتحات المخصومة (m^2)": round(p_res["tot_ded"], 2),
                "صافي مسطح المحارة النهائي (m^2)": round(p_res["tot_net"], 2),
                "كمية الرمل المطلوبة (m^3)": round(p_res["tot_sand"], 2),
                "كمية الأسمنت المطلوبة": f"{p_res['tot_cement_tons']:.2f} طن ({p_res['tot_cement_bags']} شكارة)",
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
                key="m12_dl_plaster_tab"
            )

            st.markdown(
                """<div style='background-color:#eff6ff;border-right:4px solid #2563eb;border-radius:8px;padding:12px 16px;margin-top:10px;color:#1e3a8a;font-size:0.87rem;line-height:1.7;' dir='rtl'>
                    <div style='font-weight:bold;margin-bottom:4px;display:flex;align-items:center;gap:6px;'>
                        <span>💡</span>
                        <span>رسالة إرشادية (Information Note) — الفرضيات ومعدلات الاستهلاك المعتمدة:</span>
                    </div>
                    <div>
                        تم تقدير كميات المونة بناءً على مواصفات الكود المصري لسمك بياض متوسط <b>2 سم</b> شاملاً الطرطشة والملء، بمعدل استهلاك تقريبي: <b>1 m³ رمل + 350 كجم أسمنت لكل 40-45 m² مسطح</b>، مع اعتبار نسبة هالك <b>5%</b>.
                    </div>
                </div>""",
                unsafe_allow_html=True
            )

    with tmat:
        st.markdown("### 📦 مقايسة خامات المونة ومواد البناء (طبقاً للكود المصري)")
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
                "بند الأعمال": "✅ الإجمالي الكلي لمواد البناء",
                "الوحدة": "—",
                "الكمية الصافية": "—",
                "رمل صافي (م³)": round(sand_net, 2),
                "رمل مع الهالك 5% (م³)": round(sand_total, 2),
                "أسمنت (طن)": round(cement_tons, 2),
                "شكاير أسمنت (50كجم)": cement_bags,
                brick_col_name: bricks_total,
            }
        ]

        if p_res["active_walls_count"] > 0:
            mat_rows.insert(-1, {
                "بند الأعمال": "بياض محارة (أوجه الحوائط المحددة - سمك 2 سم شامل الطرطشة)",
                "الوحدة": "م² مسطح",
                "الكمية الصافية": round(p_res["tot_net"], 2),
                "رمل صافي (م³)": round(p_res["tot_sand"] / 1.05, 2),
                "رمل مع الهالك 5% (م³)": round(p_res["tot_sand"], 2),
                "أسمنت (طن)": round(p_res["tot_cement_tons"], 2),
                "شكاير أسمنت (50كجم)": p_res["tot_cement_bags"],
                brick_col_name: "—",
            })
            total_sand_all = sand_total + p_res["tot_sand"]
            total_cement_tons_all = cement_tons + p_res["tot_cement_tons"]
            total_cement_bags_all = cement_bags + p_res["tot_cement_bags"]
            mat_rows[-1]["بند الأعمال"] = "✅ الإجمالي العام (مباني + محارة)"
            mat_rows[-1]["رمل مع الهالك 5% (م³)"] = round(total_sand_all, 2)
            mat_rows[-1]["أسمنت (طن)"] = round(total_cement_tons_all, 2)
            mat_rows[-1]["شكاير أسمنت (50كجم)"] = total_cement_bags_all

        df_mat = pd.DataFrame(mat_rows)
        def _st_mat(row):
            if row["بند الأعمال"] == "✅ الإجمالي الكلي لمواد البناء" or row["بند الأعمال"] == "✅ الإجمالي العام (مباني + محارة)":
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
            key="m12_dl_materials"
        )

def _apply_3d_opening_move(payload_str=None):
    """
    مزامنة التعديلات الواردة من العارض ثلاثي الأبعاد 3D (تحريك الأبواب والشبابيك).
    تستقبل payload_str مباشرة من الـ React bridge أو query param 'm12_op_move'.
    وتقوم بتحديث موقع الفتحة في session_state وحفظ الإعدادات دون إعادة تحميل الصفحة.
    """
    val = payload_str
    if not val:
        val = st.session_state.get("m12_3d_sync_input")
    from_query = False
    if not val and "m12_op_move" in st.query_params:
        val = st.query_params["m12_op_move"]
        from_query = True

    if val:
        try:
            data = json.loads(val) if isinstance(val, str) else val
            op_type = str(data.get("type", "")).lower()
            op_id = data.get("id")
            wall_list = data.get("wall")
            new_pos = float(data.get("pos", 0.0))
            if wall_list and len(wall_list) == 4 and op_id:
                wk = tuple(wall_list)
                found = False
                # 1. Primary lookup by op_type
                if op_type in ("win", "window"):
                    win_dict = st.session_state.get("m12_windows", {})
                    for w in win_dict.get(wk, []):
                        if w.get("id") == op_id:
                            w["pos_m"] = round(new_pos, 2)
                            st.session_state[f"m12_edit_wpos_{op_id}"] = round(new_pos, 2)
                            st.session_state[f"m12_mv_w_pos_{op_id}"] = round(new_pos, 2)
                            st.session_state["m12_active_move_dim"] = {
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
                    door_dict = st.session_state.get("m12_doors", {})
                    for d in door_dict.get(wk, []):
                        if d.get("id") == op_id:
                            d["pos_m"] = round(new_pos, 2)
                            st.session_state[f"m12_edit_dpos_{op_id}"] = round(new_pos, 2)
                            st.session_state[f"m12_mv_d_pos_{op_id}"] = round(new_pos, 2)
                            st.session_state["m12_active_move_dim"] = {
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
                    for w in st.session_state.get("m12_windows", {}).get(wk, []):
                        if w.get("id") == op_id:
                            w["pos_m"] = round(new_pos, 2)
                            st.session_state[f"m12_edit_wpos_{op_id}"] = round(new_pos, 2)
                            st.session_state[f"m12_mv_w_pos_{op_id}"] = round(new_pos, 2)
                            st.session_state["m12_active_move_dim"] = {
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
                        for d in st.session_state.get("m12_doors", {}).get(wk, []):
                            if d.get("id") == op_id:
                                d["pos_m"] = round(new_pos, 2)
                                st.session_state[f"m12_edit_dpos_{op_id}"] = round(new_pos, 2)
                                st.session_state[f"m12_mv_d_pos_{op_id}"] = round(new_pos, 2)
                                st.session_state["m12_active_move_dim"] = {
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
                if "m12_op_move" in st.query_params:
                    try:
                        del st.query_params["m12_op_move"]
                    except Exception:
                        pass
                if "module" in st.query_params:
                    try:
                        del st.query_params["module"]
                    except Exception:
                        pass

            st.session_state["m12_3d_sync_input"] = ""
            _resequence_openings()
            st.session_state.pop("m12_plan_png_b64", None)
            save_settings()
            st.toast(f"✅ تم اعتماد وحفظ موضع الفتحة ({new_pos:.2f}م) في الحصر بنجاح!", icon="💾")
        except Exception:
            if from_query:
                if "m12_op_move" in st.query_params:
                    try:
                        del st.query_params["m12_op_move"]
                    except Exception:
                        pass
                if "module" in st.query_params:
                    try:
                        del st.query_params["module"]
                    except Exception:
                        pass


def render_brick_survey_module():
    """نقطة الدخول الرئيسية للـ Module 12."""
    st.session_state["nav_view"] = "module"
    st.session_state["in_module"] = True
    _apply_3d_opening_move()
    _init_state()
    st.markdown(
        """<div style='background:linear-gradient(135deg,#7B1818,#C45E20);padding:4px 14px;
            border-radius:7px;margin-bottom:12px;display:flex;align-items:center;gap:10px;min-height:32px;'>
            <span style='font-size:1.1rem;line-height:1;'>🧱</span>
            <div style='display:flex;align-items:center;flex-wrap:wrap;gap:8px;'>
                <span style='color:white;font-weight:bold;font-size:0.95rem;'>Module 12 — Brick &amp; Plastering Survey</span>
                <span style='color:rgba(255,255,255,0.85);font-size:0.80rem;'>
                    حصر أعمال الطوب والمحارة &nbsp;|&nbsp; سم / م / م² / م³
                </span>
            </div>
        </div>""",unsafe_allow_html=True)

    def _on_openings_expander_change():
        is_now_open = bool(st.session_state.get("m12_openings_expander", False))
        st.session_state["m12_openings_expander_open"] = is_now_open
        if not is_now_open:
            st.session_state["m12_openings_win_wall_sel"] = 0
            st.session_state["m12_openings_door_wall_sel"] = 0
            st.session_state["m12_preview_opening"] = None
            st.session_state["m12_openings_keep_expanded"] = False
            st.session_state["m12_show_conflict_modal"] = False
            st.session_state["m12_conflict_errors"] = []
            st.session_state.pop("m12_commit_success_msg", None)

    is_openings_exp = bool(st.session_state.get("m12_openings_keep_expanded", False) or st.session_state.get("m12_show_conflict_modal", False) or st.session_state.get("m12_commit_success_msg"))
    if is_openings_exp:
        st.session_state["m12_openings_expander_open"] = True

    lc,rc=st.columns([0.82,1.65],gap="medium")
    with lc:
        with st.expander("1️⃣ شبكة المحاور", expanded=False): _section_axes()
        with st.expander("2️⃣ الأعمدة", expanded=False): _section_columns()
        with st.expander("3️⃣ تحديد مواصفات وتعديل وحذف واستعادة الحوائط", expanded=False): _section_walls()
        with st.expander("4️⃣ نماذج الفتحات (Types)", expanded=False): _section_opening_types()
        openings_exp = st.expander(
            "5️⃣ إسقاط الشبابيك والأبواب",
            expanded=bool(st.session_state.get("m12_openings_expander_open", False)),
            key="m12_openings_expander",
            on_change=_on_openings_expander_change
        )
        with openings_exp:
            _section_openings()
        with st.expander("6️⃣ تحريك الشبابيك والأبواب", expanded=False):
            _section_move_openings()
        with st.expander("7️⃣ حذف الشبابيك والأبواب", expanded=False): _section_delete_restore_openings()
        with st.expander("8️⃣ أنواع مقاسات الطوب", expanded=False): _section_brick_type()
        with st.expander("9️⃣ تحديد حوائط المحارة", expanded=False): _section_plaster_walls()

    with rc:
        c_plan_t, c_plan_mode = st.columns([1.4, 1.1], vertical_alignment="center")
        with c_plan_t:
            st.markdown(
                "<div style='font-size:1.15rem;font-weight:700;color:#ffffff;line-height:32px;margin:0;display:flex;align-items:center;'>"
                "📐 المسقط الأفقي"
                "</div>",
                unsafe_allow_html=True
            )
        with c_plan_mode:
            is_interactive = st.toggle("🎮 تحكم تفاعلي (Zoom & Pan)", value=False, key="m12_plan_interactive_toggle", help="تفعيل أدوات التكبير والتصغير والسحب بالماوس فوق الرسم")

        # ── مراقبة خط البعد المؤقت للتحريك ومؤقت الإخفاء التلقائي (4 ثوانٍ) ──
        active_dim = st.session_state.get("m12_active_move_dim")
        is_active_dim = False
        dim_elapsed = 0.0
        if active_dim:
            dim_elapsed = time.time() - float(active_dim.get("ts", 0.0))
            if dim_elapsed < 4.2:
                is_active_dim = True
            else:
                st.session_state.pop("m12_active_move_dim", None)
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

            # شريط التنبيه المعماري العلوي مع اختفاء تدريجي تلقائي
            st.markdown(
                f"""<div id="m12_dim_banner_container" style='background: linear-gradient(135deg, #eff6ff, #dbeafe); border: 1.5px solid #3b82f6;
                border-radius: 8px; padding: 8px 14px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; transition: all 0.4s ease;' dir='rtl'>
                    <div style='display: flex; align-items: center; gap: 8px;'>
                        <span style='font-size: 1.2rem;'>📏</span>
                        <span style='font-weight: 700; color: #1e40af; font-size: 0.90rem;'>
                            خط أبعاد موضع {kind_ar} <b>{name}</b>: البعد عن بداية الحائط = <b>{pos_m:.2f}م</b>
                        </span>
                    </div>
                    <div style='background: #3b82f6; color: #ffffff; padding: 3px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; white-space: nowrap;'>
                        ⏱️ يختفي تلقائياً خلال {rem_sec} ثوانٍ
                    </div>
                </div>""",
                unsafe_allow_html=True
            )

            if is_interactive:
                _render_interactive_plan(b64_override=b64_dim, b64_clean=b64_clean, rem_ms=rem_ms)
            else:
                # عرض المسقط الأفقي مع تبديل تلقائي سلس لصورة المسقط النظيف بعد 4 ثوانٍ دون إعادة تحميل
                st.markdown(
                    f"""<div style="width: 100%; text-align: center; background: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
                        <img id="m12_plan_static_img" src="data:image/png;base64,{b64_dim}" style="width: 100%; max-width: 100%; height: auto; display: block; border-radius: 6px;" />
                        <img src="//:0" style="display:none;" onerror="
                            (function() {{
                                setTimeout(function() {{
                                    var banner = document.getElementById('m12_dim_banner_container');
                                    if (banner) {{
                                        banner.style.opacity = '0';
                                        banner.style.transform = 'translateY(-6px)';
                                        setTimeout(function() {{ banner.style.display = 'none'; }}, 400);
                                    }}
                                    var img = document.getElementById('m12_plan_static_img');
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
                                    var b = pDoc.getElementById('m12_dim_banner_container');
                                    if (b) {{
                                        b.style.opacity = '0';
                                        b.style.transform = 'translateY(-6px)';
                                        setTimeout(function() {{ b.style.display = 'none'; }}, 400);
                                    }}
                                    var img = pDoc.getElementById('m12_plan_static_img');
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
            # العرض المستقر الافتراضي للمسقط الأفقي
            if is_interactive:
                _render_interactive_plan()
            else:
                st.image(_draw_plan(with_dim=False), use_container_width=True)
        st.markdown(
            f"""<div style='font-size:0.78rem;margin-top:3px;display:flex;gap:12px;flex-wrap:wrap;'>
                <span style='color:{_CLR_WALL_12};font-weight:bold;'>■ حائط 12سم</span>
                <span style='color:{_CLR_WALL_25};font-weight:bold;'>■ حائط 25سم</span>
                <span style='color:{_CLR_WIN};font-weight:bold;'>■ شباك (W#)</span>
                <span style='color:{_CLR_DOOR};font-weight:bold;'>■ باب (D#)</span>
                <span style='color:{_CLR_COL};font-weight:bold;'>■ عمود (C#)</span>
                <span style='color:#EC4899;font-weight:bold;'>▨ وجه محارة (وردي)</span>
                <span style='color:#0284c7;font-weight:bold;'>■ حائط دروة [دروة]</span>
                <span style='color:#222;font-weight:bold;'>■ حائط (L#)</span>
                <span style='color:#888;font-weight:bold;'>┄ خط استرشادي (محذوف)</span>
            </div>""",unsafe_allow_html=True)
    st.divider()
    with st.expander("🌐 3D (Data Processing & Rendering) — العارض ثلاثي الأبعاد التفاعلي", expanded=False):
        _section_3d_viewer()
    st.divider()
    with st.expander("🔟 جدول الحصر النهائي", expanded=False):
        _section_survey()
    save_settings()

