"""
Module 12 -- Brick & Plastering Survey
"""
import io, math, base64
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
    if not cfg.get("_m12_reset_v1_done"):
        cfg["_m12_reset_v1_done"] = True
        reset_module_12_state(cfg)
    elif "m12_x_axes" not in st.session_state or "module_12_data" not in st.session_state:
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

def _col_center(i,j):
    xs=st.session_state["m12_x_axes"]; ys=st.session_state["m12_y_axes"]
    dx,dy=st.session_state["m12_col_shifted"].get((i,j),(0.0,0.0))
    return xs[i]+dx/100.0, ys[j]+dy/100.0

def _get_col_size():
    xs = st.session_state.get("m12_x_axes", [])
    ys = st.session_state.get("m12_y_axes", [])
    if not xs or not ys: return 0.25
    span_x = max(xs) - min(xs) or 1.0
    span_y = max(ys) - min(ys) or 1.0
    col_size = max(span_x, span_y) * 0.028
    return max(0.15, min(col_size, 0.40))

def _get_col_wh(i, j):
    col_size = _get_col_size()
    d = st.session_state.get("m12_col_dirs", {}).get((i, j), "NS")
    cw, ch = (col_size * 0.55, col_size) if d == "NS" else (col_size, col_size * 0.55)
    return cw, ch

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
    thick_m = _get_wall_thickness(wk) / 100.0
    w_val = float(w_m)
    pos = float(pos_m)

    # 1. حساب حدود الفتحة في المسقط الأفقي (2D Bounding Box) — pos يمثل بداية الفتحة من بداية الحائط
    if is_h:
        x_base = min(xs[i1], xs[i2])
        op_xmin = x_base + pos
        op_xmax = x_base + pos + w_val
        y_wall = ys[j1]
        op_ymin = y_wall - thick_m / 2.0
        op_ymax = y_wall + thick_m / 2.0

        # فحص الخروج عن بداية أو نهاية الحائط
        if pos < -0.005:
            errors.append(f"خروج {op_name} خارج بداية الحائط بمقدار {abs(pos):.2f}م!")
        if (pos + w_val) > wlen + 0.005:
            errors.append(f"خروج {op_name} خارج نهاية الحائط بمقدار {(pos + w_val - wlen):.2f}م!")
    else:
        y_base = min(ys[j1], ys[j2])
        op_ymin = y_base + pos
        op_ymax = y_base + pos + w_val
        x_wall = xs[i1]
        op_xmin = x_wall - thick_m / 2.0
        op_xmax = x_wall + thick_m / 2.0

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
    col_size = _get_col_size()
    cw, ch = (col_size * 0.55, col_size) if col_dir == "NS" else (col_size, col_size * 0.55)
    
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

def _get_wall_height(w_key, default_h):
    wall_heights = st.session_state["m12_wall_heights"]
    if w_key in wall_heights:
        return wall_heights[w_key]
    i1, j1, i2, j2 = w_key
    if j1 == j2:
        for i in range(min(i1, i2), max(i1, i2)):
            if (i, j1, i + 1, j1) in wall_heights:
                return wall_heights[(i, j1, i + 1, j1)]
    else:
        for j in range(min(j1, j2), max(j1, j2)):
            if (i1, j, i1, j + 1) in wall_heights:
                return wall_heights[(i1, j, i1, j + 1)]
    return default_h

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

def _draw_plan():
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
        thick = _get_wall_thickness(wk); half_t = thick / 200.0
        color = _CLR_WALL_12 if thick == _WALL_THIN else _CLR_WALL_25
        is_h = (j1 == j2)
        wlen = _wall_length_m(wk)
        lname = wm.get(wk, "")
        if removed:
            # 4- رسم خط استرشادي مكان الحائط المحذوف فقط دون حسابات أو كتابة أبعاد
            ax.plot([xs[i1], xs[i2]], [ys[j1], ys[j2]], color="#94a3b8", ls=":", lw=1.2, alpha=0.75, zorder=2)
        else:
            if is_h: rx = min(xs[i1], xs[i2]); ry = ys[j1] - half_t; rw = abs(xs[i2] - xs[i1]); rh = half_t * 2
            else: rx = xs[i1] - half_t; ry = min(ys[j1], ys[j2]); rw = half_t * 2; rh = abs(ys[j2] - ys[j1])
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
                            p_x, p_y = rx, ys[j1] + half_t
                            p_w, p_h = rw, p_th
                        elif f_dir == "أسفل":
                            p_x, p_y = rx, ys[j1] - half_t - p_th
                            p_w, p_h = rw, p_th
                        else:
                            continue
                    else:
                        if f_dir == "يمين":
                            p_x, p_y = xs[i1] + half_t, ry
                            p_w, p_h = p_th, rh
                        elif f_dir == "يسار":
                            p_x, p_y = xs[i1] - half_t - p_th, ry
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
                if is_h:
                    ax.text(mx, my + half_t * 2.0, label_text, ha="center", va="bottom",
                            fontsize=fs_wall, color="#1e293b", fontweight="bold", zorder=5,
                            bbox=dict(boxstyle="round,pad=0.18", facecolor="#ffffff", edgecolor="#cbd5e1", lw=0.6, alpha=0.92))
                else:
                    ax.text(mx + half_t * 2.0, my, label_text, ha="left", va="center",
                            fontsize=fs_wall, color="#1e293b", fontweight="bold", zorder=5,
                            bbox=dict(boxstyle="round,pad=0.18", facecolor="#ffffff", edgecolor="#cbd5e1", lw=0.6, alpha=0.92))
        wins = _get_wall_windows(wk)
        if not removed and wins:
            wlen = _wall_length_m(wk)
            win_groups = {}
            for winfo in wins:
                if winfo.get("removed", False) or winfo.get("id") in del_win_ids: continue
                w_w = float(winfo.get("w_m", 1.0)); w_pos = float(winfo.get("pos_m", (wlen - w_w) / 2)); hw = w_w / 2
                if is_h: wx = min(xs[i1], xs[i2]) + w_pos; wy = ys[j1] - half_t; ww = w_w; wh2 = half_t * 2
                else: wx = xs[i1] - half_t; wy = min(ys[j1], ys[j2]) + w_pos; ww = half_t * 2; wh2 = w_w
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
                    ax.text(g["wx"] + g["ww"] / 2, ys[j1] - half_t * 1.8, w_label, ha="center", va="top", fontsize=fs_win, color=t_col, fontweight="bold", zorder=6)
                else:
                    ax.text(xs[i1] - half_t * 1.8, g["wy"] + g["wh2"] / 2, w_label, ha="right", va="center", fontsize=fs_win, color=t_col, fontweight="bold", zorder=6)


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
                    y_c = ys[j1]
                    
                    # قراءة اتجاه الخطين المتعامدين وموضع المفصلة
                    def_leaf = "أسفل" if y_c >= y_max - 1e-4 else "أعلى"
                    leaf_d = dinfo.get("leaf_dir", def_leaf)
                    if leaf_d not in ["أعلى", "أسفل"]: leaf_d = def_leaf
                    
                    d_errs = _validate_opening_coords(wk, dname or "باب", "door", d_w, float(dinfo.get("h_m", 2.1)), d_pos, leaf_dir=leaf_d, current_op_id=dinfo.get("id"))
                    door_clr = "#D32F2F" if d_errs else _CLR_DOOR
                    door_lw = 2.4 if d_errs else 1.8
                    
                    # تفريغ فتحة الباب في الحائط
                    ax.add_patch(patches.Rectangle((x0, y_c - half_t - 0.002), d_w, half_t * 2 + 0.004,
                                                   facecolor="#F8F8F8", edgecolor="none", zorder=3))
                    # خطي الحلق عند طرفي الفتحة
                    ax.plot([x0, x0], [y_c - half_t, y_c + half_t], color="#D32F2F" if d_errs else "#333333", lw=1.2 if d_errs else 1.0, zorder=3.5)
                    ax.plot([x1, x1], [y_c - half_t, y_c + half_t], color="#D32F2F" if d_errs else "#333333", lw=1.2 if d_errs else 1.0, zorder=3.5)
                    if dname:
                        ax.text(x_c, y_c, dname, ha="center", va="center", fontsize=fs_door, color=door_clr, fontweight="bold", zorder=6)
                    
                    sdir = 1 if leaf_d == "أعلى" else -1
                    y_ref = y_c + half_t if sdir == 1 else y_c - half_t
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
                    x_c = xs[i1]
                    
                    # قراءة اتجاه الخطين المتعامدين وموضع المفصلة
                    def_leaf = "يسار" if x_c >= x_max - 1e-4 else "يمين"
                    leaf_d = dinfo.get("leaf_dir", def_leaf)
                    if leaf_d not in ["يمين", "يسار"]: leaf_d = def_leaf
                    
                    d_errs = _validate_opening_coords(wk, dname or "باب", "door", d_w, float(dinfo.get("h_m", 2.1)), d_pos, leaf_dir=leaf_d, current_op_id=dinfo.get("id"))
                    door_clr = "#D32F2F" if d_errs else _CLR_DOOR
                    door_lw = 2.4 if d_errs else 1.8
                    
                    # تفريغ فتحة الباب في الحائط
                    ax.add_patch(patches.Rectangle((x_c - half_t - 0.002, y0), half_t * 2 + 0.004, d_w,
                                                   facecolor="#F8F8F8", edgecolor="none", zorder=3))
                    # خطي الحلق عند طرفي الفتحة
                    ax.plot([x_c - half_t, x_c + half_t], [y0, y0], color="#D32F2F" if d_errs else "#333333", lw=1.2 if d_errs else 1.0, zorder=3.5)
                    ax.plot([x_c - half_t, x_c + half_t], [y1, y1], color="#D32F2F" if d_errs else "#333333", lw=1.2 if d_errs else 1.0, zorder=3.5)
                    if dname:
                        ax.text(x_c, y_c, dname, ha="center", va="center", fontsize=fs_door, color=door_clr, fontweight="bold", zorder=6)
                    
                    sdir = 1 if leaf_d == "يمين" else -1
                    x_ref = x_c + half_t if sdir == 1 else x_c - half_t
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
                    pwy = ys[j1] - half_t
                    pww = pw_w
                    pwh2 = half_t * 2
                else:
                    pwx = xs[i1] - half_t
                    pwy = min(ys[j1], ys[j2]) + pw_pos
                    pww = half_t * 2
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
                    ax.text(pwx + pww / 2, ys[j1] - half_t * 2.2, pw_lbl, ha="center", va="top",
                            fontsize=fs_win, color=pw_txt_clr, fontweight="bold", zorder=7,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=pw_edge, lw=1.0, alpha=0.95))
                else:
                    ax.text(xs[i1] - half_t * 2.2, pwy + pwh2 / 2, pw_lbl, ha="right", va="center",
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
                    py_c = ys[j1]
                    def_leaf = "أسفل" if py_c >= y_max - 1e-4 else "أعلى"
                    leaf_d = preview_op.get("leaf_dir", def_leaf)
                    if leaf_d not in ["أعلى", "أسفل"]: leaf_d = def_leaf

                    ax.add_patch(patches.Rectangle(
                        (px0, py_c - half_t - 0.002), pd_w, half_t * 2 + 0.004,
                        facecolor="#FFEBEE" if has_err else "#F8F8F8", edgecolor=pd_clr, lw=1.5, linestyle="--", zorder=3.2
                    ))
                    ax.plot([px0, px0], [py_c - half_t, py_c + half_t], color=pd_clr, lw=1.4, linestyle="--", zorder=3.5)
                    ax.plot([px1, px1], [py_c - half_t, py_c + half_t], color=pd_clr, lw=1.4, linestyle="--", zorder=3.5)
                    ax.text(px_c, py_c, pd_lbl, ha="center", va="center", fontsize=fs_door, color=pd_clr, fontweight="bold", zorder=7,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=pd_clr, lw=1.0, alpha=0.95))

                    sdir = 1 if leaf_d == "أعلى" else -1
                    y_ref = py_c + half_t if sdir == 1 else py_c - half_t
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
                    px_c = xs[i1]
                    def_leaf = "يسار" if px_c >= x_max - 1e-4 else "يمين"
                    leaf_d = preview_op.get("leaf_dir", def_leaf)
                    if leaf_d not in ["يمين", "يسار"]: leaf_d = def_leaf

                    ax.add_patch(patches.Rectangle(
                        (px_c - half_t - 0.002, py0), half_t * 2 + 0.004, pd_w,
                        facecolor="#FFEBEE" if has_err else "#F8F8F8", edgecolor=pd_clr, lw=1.5, linestyle="--", zorder=3.2
                    ))
                    ax.plot([px_c - half_t, px_c + half_t], [py0, py0], color=pd_clr, lw=1.4, linestyle="--", zorder=3.5)
                    ax.plot([px_c - half_t, px_c + half_t], [py1, py1], color=pd_clr, lw=1.4, linestyle="--", zorder=3.5)
                    ax.text(px_c, py_c, pd_lbl, ha="center", va="center", fontsize=fs_door, color=pd_clr, fontweight="bold", zorder=7,
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=pd_clr, lw=1.0, alpha=0.95))

                    sdir = 1 if leaf_d == "يمين" else -1
                    x_ref = px_c + half_t if sdir == 1 else px_c - half_t
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
    buf = _draw_plan()
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
        row={"الحائط":display,"الطول (م)":round(length,3),"الارتفاع (م)":round(height,3),
             "المساحة الإجمالية (م2)":round(gross,3),"مساحة الفتحات (م2)":round(op,3),
             "المساحة الصافية (م2)":round(net,3),"حجم الطوب (م3)":round(vol,3),
             "عدد الطوب (وحدة)": brick_cnt}
        (rows_12 if thick==_WALL_THIN else rows_25).append(row)
    return {"rows_12":rows_12,"rows_25":rows_25}

def _totals_row(rows):
    if not rows: return {}
    tot={k:"" for k in rows[0]}; tot["الحائط"]="✅ الإجمالي"
    for k in ["المساحة الإجمالية (م2)","مساحة الفتحات (م2)","المساحة الصافية (م2)","حجم الطوب (م3)"]:
        tot[k]=round(sum(r.get(k,0) for r in rows),3)
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
    st.markdown(
        """<div dir='rtl' style='background:#fff8e1;border:1.5px solid #f59e0b;border-radius:8px;
            padding:8px 14px;margin-bottom:8px;font-size:0.83rem;color:#78350f;'>
            <b>📦 هذا القسم مخصص فقط لحصر كميات الطوب (BOQ)</b><br>
            لا تُستخدم بياناته في حسابات الأحمال الإنشائية أو التصميم الخرساني.
        </div>""",
        unsafe_allow_html=True
    )
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
            play_warning_sound()
        elif len(set(round(v, 4) for v in x_vals)) < len(x_vals):
            st.warning("⚠️ لا يمكن تكرار قيمة محور X!")
            play_warning_sound()
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
            play_warning_sound()
        elif len(set(round(v, 4) for v in y_vals)) < len(y_vals):
            st.warning("⚠️ لا يمكن تكرار قيمة محور Y!")
            play_warning_sound()
        else:
            if y_vals != cys:
                st.session_state["m12_y_axes"] = y_vals
                save_settings()

def _section_columns():
    xs=st.session_state["m12_x_axes"]; ys=st.session_state["m12_y_axes"]
    if not xs or not ys: st.info("أدخل المحاور أولاً."); return
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
    cname=cn.get((si,sj),orig_cname)
    if is_rem: st.error(f"🗑️ العمود **{orig_cname}** عند تقاطع (X{si+1}, Y{sj+1}) محذوف — الحوائط قائمة ومستمرة.")
    else: st.success(f"✅ العمود **{cname}** — X{si+1}={xs[si]:.2f}م, Y{sj+1}={ys[sj]:.2f}م")

    # ── رسالة تأكيد الحذف بعرض كامل الحاوية لتجنب تكسر الكلمات ──
    if not is_rem and st.session_state.get("m12_confirm_del_col") == (si,sj):
        play_warning_sound()
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

    c1,c2,c3=st.columns(3)
    with c1:
        if is_rem:
            if st.button(f"♻️ استعادة العمود {orig_cname}",key="m12_restore_col", use_container_width=True):
                if si < len(xs) and sj < len(ys):
                    removed_cols.discard((si,sj)); st.session_state["m12_col_removed"]=removed_cols
                    save_settings()
                    st.session_state.pop("m12_confirm_del_col",None)
                    st.success(f"✅ تم استعادة العمود {orig_cname} بنجاح.")
                    st.rerun()
                else:
                    play_warning_sound()
                    st.error("🚨 لا يمكن استعادة العمود: المحاور التي يقع عليها العمود لم تعد موجودة في شبكة المحاور!")
        else:
            if st.session_state.get("m12_confirm_del_col") != (si,sj):
                if st.button("🗑️ حذف العمود", key="m12_del_col", use_container_width=True):
                    st.session_state["m12_confirm_del_col"] = (si,sj)
                    st.rerun()
    with c2:
        nd=st.radio("اتجاه العمود",options=["NS","EW"],index=0 if cur_dir=="NS" else 1,horizontal=True,key=f"m12_col_dir_radio_{si}_{sj}",help="NS=طولي / EW=عرضي")
        if nd != cur_dir:
            col_dirs[(si,sj)]=nd; st.session_state["m12_col_dirs"]=col_dirs
            save_settings()
    with c3:
        so={"بدون ترحيل":(0.0,0.0),"ترحيل +X":(_SHIFT_COL,0.0),"ترحيل -X":(-_SHIFT_COL,0.0),"ترحيل +Y":(0.0,_SHIFT_COL),"ترحيل -Y":(0.0,-_SHIFT_COL)}
        cl=next((l for l,v in so.items() if abs(v[0]-dx)<0.01 and abs(v[1]-dy)<0.01),"بدون ترحيل")
        ch=st.selectbox("ترحيل (6سم)",options=list(so.keys()),index=list(so.keys()).index(cl),key=f"m12_col_shift_{si}_{sj}")
        if so[ch] != (dx, dy):
            col_shifted[(si,sj)]=so[ch]; st.session_state["m12_col_shifted"]=col_shifted
            save_settings()


    cd=[]
    for (i,j) in all_cols:
        cx2,cy2=_col_center(i,j)
        orig_cn = f"C{j * len(xs) + i + 1}"
        cn2 = cn.get((i,j), f"{orig_cn} (محذوف)")
        cd.append({"الاسم":cn2,"X (م)":round(cx2,3),"Y (م)":round(cy2,3),"الاتجاه":col_dirs.get((i,j),"NS"),"الحالة":"🗑️ محذوف" if (i,j) in removed_cols else "✅ نشط"})
    with st.expander("📋 جدول الأعمدة",expanded=False):
        st.dataframe(pd.DataFrame(cd),use_container_width=True,hide_index=True)

def _section_walls():
    xs=st.session_state["m12_x_axes"]; ys=st.session_state["m12_y_axes"]
    if len(xs)<2 or len(ys)<2: st.info("أدخل على الأقل محورين في كل اتجاه."); return
    removed_walls=st.session_state["m12_wall_removed"]; wall_thick=st.session_state["m12_wall_thickness"]
    wall_heights=st.session_state["m12_wall_heights"]; cm=_get_col_name_map(); wm=_get_wall_name_map()
    dh=st.number_input("ارتفاع الحوائط الافتراضي (م)",min_value=1.5,max_value=8.0,
        value=float(st.session_state.get("m12_default_wall_height",3.0)),step=0.1,format="%.1f",key="m12_default_h_input")
    if abs(dh - float(st.session_state.get("m12_default_wall_height", 3.0))) > 0.001:
        st.session_state["m12_default_wall_height"]=dh
        save_settings()
    all_walls=_get_all_walls()
    if not all_walls:
        st.info("لا توجد حوائط متصلة بين الأعمدة.")
        return
    _safe_idx("m12_sel_wall", len(all_walls) + 1)
    def _wlbl(k):
        if k == 0:
            return "لم يتم اختيار حائط"
        wk = all_walls[k - 1]
        st2 = "🗑️ " if wk in removed_walls else ""
        return st2 + _wall_display_label(wk, cm, wm)
    sel = st.selectbox("اختر حائطاً", options=range(len(all_walls) + 1), format_func=_wlbl, key="m12_sel_wall")
    if sel == 0:
        st.info("💡 لم يتم اختيار حائط. يرجى اختيار حائط من القائمة المنسدلة أعلاه لتعديل خصائصه أو حذفه.")
    else:
        wk = all_walls[sel - 1]
        is_rem = wk in removed_walls
        tc = _get_wall_thickness(wk)
        hc = _get_wall_height(wk, dh)
        wlen = _wall_length_m(wk)

        # ── رسالة تأكيد حذف الحائط بعرض كامل الحاوية لتجنب تكسر الكلمات ──
        if not is_rem and st.session_state.get("m12_confirm_del_wall") == wk:
            play_warning_sound()
            st.warning(f"⚠️ تأكيد حذف الحائط {_wall_display_label(wk,cm,wm)}؟ يمكن استعادته لاحقاً.")
            cyes, cno = st.columns(2)
            with cyes:
                if st.button("✅ نعم، تأكيد حذف الحائط", type="primary", key="m12_conf_wall_yes", use_container_width=True):
                    removed_walls.add(wk); st.session_state["m12_wall_removed"]=removed_walls
                    st.session_state.pop("m12_confirm_del_wall", None)
                    save_settings()
                    st.rerun()
            with cno:
                if st.button("❌ إلغاء", key="m12_conf_wall_no", use_container_width=True):
                    st.session_state.pop("m12_confirm_del_wall", None)
                    st.rerun()

        c1, c2, c3 = st.columns(3)
        with c1:
            if is_rem:
                if st.button("♻️ استعادة الحائط", key="m12_restore_wall", use_container_width=True):
                    removed_walls.discard(wk); st.session_state["m12_wall_removed"] = removed_walls
                    save_settings()
                    st.rerun()
            else:
                if st.session_state.get("m12_confirm_del_wall") != wk:
                    if st.button("🗑️ حذف الحائط", key="m12_del_wall", use_container_width=True):
                        st.session_state["m12_confirm_del_wall"] = wk
                        st.rerun()
        with c2:
            nt = st.radio("سُمك الحائط", options=[_WALL_THIN, _WALL_THICK], index=0 if tc == _WALL_THIN else 1,
                format_func=lambda v: f"{v} سم", horizontal=True, key=f"m12_wall_thick_radio_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}")
            if nt != tc:
                wall_thick[wk] = nt; st.session_state["m12_wall_thickness"] = wall_thick
                save_settings()
            st.markdown(f"<div style='font-size:13.5px; color:#1e293b; margin-top:2px;'>📏 <b>سُمك الحائط:</b> {nt} سم</div>", unsafe_allow_html=True)
        with c3:
            nh = st.number_input("الارتفاع (م)", min_value=1.0, max_value=8.0, value=float(hc), step=0.05, format="%.2f", key=f"m12_wall_h_input_{wk[0]}_{wk[1]}_{wk[2]}_{wk[3]}")
            if abs(nh - hc) > 0.001:
                wall_heights[wk] = nh; st.session_state["m12_wall_heights"] = wall_heights
                save_settings()
            st.markdown(f"<div style='font-size:13.5px; color:#1e293b; margin-top:2px;'>📐 <b>طول الحائط:</b> {wlen:.3f} م</div>", unsafe_allow_html=True)
        if is_rem: st.error(f"🗑️ الحائط '{_wlbl(sel)}' محذوف (يظهر كخط استرشادي فقط ولا يحسب في الحصر).")
    wd=[]
    for wk2 in all_walls:
        wd.append({"الحائط":_wall_display_label(wk2,cm,wm),"الطول (م)":round(_wall_length_m(wk2),3),
            "السُمك (سم)":_get_wall_thickness(wk2),"الارتفاع (م)":round(_get_wall_height(wk2,dh),3),
            "الحالة":"🗑️ محذوف" if wk2 in removed_walls else "✅ نشط"})
    with st.expander("📋 جدول الحوائط",expanded=False):
        def _sr(row):
            c2b="rgba(239,163,104,0.18)" if row["السُمك (سم)"]==_WALL_THIN else "rgba(139,26,26,0.12)"
            return [f"background-color:{c2b}"]*len(row)
        st.dataframe(pd.DataFrame(wd).style.apply(_sr,axis=1),use_container_width=True,hide_index=True)

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
        "اختر نوع العنصر المعماري المراد إسقاطه أو تعديله:",
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
            st.info("لا توجد حوائط نشطة لإضافة أو تعديل الشبابيك.")
            st.session_state["m12_preview_opening"] = None
        else:
            def_w_idx = 0
            if curr_prev and curr_prev.get("kind") == "win" and curr_prev.get("wk") in active:
                def_w_idx = active.index(curr_prev["wk"]) + 1
                if "m12_openings_win_wall_sel" not in st.session_state:
                    st.session_state["m12_openings_win_wall_sel"] = def_w_idx

            _safe_idx("m12_openings_win_wall_sel", len(active) + 1)
            sel_w = st.selectbox(
                "اختر الحائط لعرض وإضافة الشبابيك:",
                options=range(len(active) + 1),
                index=st.session_state.get("m12_openings_win_wall_sel", def_w_idx),
                format_func=lambda k: "لم يتم اختيار حائط" if k == 0 else _wall_display_label(active[k - 1], cm, wm),
                key="m12_openings_win_wall_sel"
            )
            if sel_w == 0:
                st.session_state["m12_preview_opening"] = None
                st.info("💡 لم يتم اختيار حائط. يرجى اختيار حائط من القائمة المنسدلة أعلاه لعرض وإضافة الشبابيك.")
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
                                "msg": "انه تم تثبيت مكان الشباك في المكان المحدد ، ولا يمكن تحريكة الان ، يمكن حذف فقط من قسم الحذف"
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
                            play_warning_sound()
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
                if not active_wins:
                    st.info("لا توجد شبابيك نشطة على هذا الحائط حالياً.")

                for wi, winfo in enumerate(active_wins):
                    wid = winfo["id"]
                    wname = wm_win.get(wid) or winfo.get("name") or f"W{wi+1}"
                    winfo["name"] = wname
                    type_lbl_w = winfo.get("type_label", "")
                    expander_title = f"🪟 شباك {wname}"
                    if type_lbl_w:
                        expander_title += f" [{type_lbl_w}]"
                    expander_title += f" (عرض {winfo.get('w_m',1.0):.2f}م)"
                    with st.expander(expander_title, expanded=True):
                        wc1, wc2, wc3, wc4 = st.columns(4)
                        winfo["w_m"] = wc1.number_input("العرض (م)", 0.3, max(wlen, 0.31), float(winfo.get("w_m", 1.0)), 0.05, "%.2f", key=f"m12_w_w_{wid}")
                        winfo["h_m"] = wc2.number_input("الارتفاع (م)", 0.3, max(wh, 0.31), float(winfo.get("h_m", 1.2)), 0.05, "%.2f", key=f"m12_w_h_{wid}")
                        def_w_pos = round(max(0.0, (wlen - float(winfo.get("w_m", 1.0))) / 2.0), 2)
                        old_wpos = float(winfo.get("pos_m", def_w_pos))
                        new_wpos = wc3.number_input("بعد بداية الشباك عن بداية الحائط (م)", 0.0, wlen, old_wpos, 0.05, "%.2f", key=f"m12_w_pos_{wid}", help="المسافة من بداية الحائط حتى بداية الشباك")
                        if new_wpos != old_wpos:
                            winfo["pos_m"] = new_wpos
                            save_settings()
                        else:
                            winfo["pos_m"] = new_wpos
                        winfo["sill_m"] = wc4.number_input("ارتفاع الجلسة Sill (م)", 0.0, wh, float(winfo.get("sill_m", 0.9)), 0.05, "%.2f", key=f"m12_w_sill_{wid}")

                        # فحص الإحداثيات والتداخل مع الأعمدة وحدود المسقط الأفقي
                        w_errs = _validate_opening_coords(wk, f"الشباك {wname}", "win", winfo["w_m"], winfo["h_m"], winfo["pos_m"], current_op_id=wid)
                        if winfo["h_m"] > wh:
                            st.error(f"⚠️ ارتفاع الشباك ({winfo['h_m']:.2f}م) أكبر من ارتفاع الحائط ({wh:.2f}م)!")
                        if (winfo.get("sill_m", 0.9) + winfo["h_m"]) > wh:
                            st.error(f"⚠️ مجموع ارتفاع الجلسة مع الشباك ({(winfo.get('sill_m', 0.9) + winfo['h_m']):.2f}م) يتجاوز ارتفاع الحائط ({wh:.2f}م)!")

                        if w_errs:
                            _render_big_warning(w_errs)

                        if st.session_state.get(f"m12_confirm_del_win_{wid}"):
                            play_warning_sound()
                            st.warning(f"⚠️ تأكيد حذف الشباك {wname} ونقله إلى سلة المهملات؟ (يمكنك استعادته لاحقاً)")
                            c_y_w, c_n_w = st.columns(2)
                            with c_y_w:
                                if st.button(f"✅ نعم، تأكيد حذف {wname}", type="primary", key=f"m12_conf_del_win_yes_{wid}", use_container_width=True):
                                    _remove_opening_by_id(wid, "win")
                                    st.session_state.pop(f"m12_confirm_del_win_{wid}", None)
                                    st.rerun()
                            with c_n_w:
                                if st.button("❌ إلغاء", key=f"m12_conf_del_win_no_{wid}", use_container_width=True):
                                    st.session_state.pop(f"m12_confirm_del_win_{wid}", None)
                                    st.rerun()
                        else:
                            if st.button(f"🗑️ حذف الشباك ونقله الي سلة المهملات", key=f"m12_del_win_btn_{wid}", use_container_width=True):
                                st.session_state[f"m12_confirm_del_win_{wid}"] = True
                                play_warning_sound()
                                st.rerun()

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
                "اختر الحائط لعرض وإضافة الأبواب:",
                options=range(len(active) + 1),
                index=st.session_state.get("m12_openings_door_wall_sel", def_d_idx),
                format_func=lambda k: "لم يتم اختيار حائط" if k == 0 else _wall_display_label(active[k - 1], cm, wm),
                key="m12_openings_door_wall_sel"
            )
            if sel_d == 0:
                st.session_state["m12_preview_opening"] = None
                st.info("💡 لم يتم اختيار حائط. يرجى اختيار حائط من القائمة المنسدلة أعلاه لعرض وإضافة الأبواب.")
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
                                "msg": "انه تم تثبيت مكان الباب في المكان المحدد ، ولا يمكن تحريكة الان ، يمكن حذف فقط من قسم الحذف"
                            }
                            st.rerun()
                        else:
                            preview_door["has_conflict"] = True
                            st.session_state["m12_preview_opening"] = preview_door
                            st.session_state["m12_door_preview_disabled"] = False
                            st.session_state["m12_conflict_errors"] = test_derr
                            st.session_state["m12_show_conflict_modal"] = True
                            st.session_state["m12_openings_keep_expanded"] = True
                            play_warning_sound()
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
                if not active_doors:
                    st.info("لا توجد أبواب نشطة على هذا الحائط حالياً.")

                for di, dinfo in enumerate(active_doors):
                    did = dinfo["id"]
                    dname = wm_door.get(did) or dinfo.get("name") or f"D{di+1}"
                    dinfo["name"] = dname
                    type_lbl_d = dinfo.get("type_label", "")
                    door_exp_title = f"🚪 باب {dname}"
                    if type_lbl_d:
                        door_exp_title += f" [{type_lbl_d}]"
                    door_exp_title += f" (عرض {dinfo.get('w_m',0.9):.2f}م)"
                    with st.expander(door_exp_title, expanded=True):
                        dc1, dc2, dc3 = st.columns(3)
                        dinfo["w_m"] = dc1.number_input("العرض (م)", 0.5, max(wlen, 0.51), float(dinfo.get("w_m", 0.9)), 0.05, "%.2f", key=f"m12_d_w_{did}")
                        dinfo["h_m"] = dc2.number_input("الارتفاع (م)", 1.5, max(wh, 1.51), float(dinfo.get("h_m", 2.1)), 0.05, "%.2f", key=f"m12_d_h_{did}")
                        def_d_pos = round(max(0.0, (wlen - float(dinfo.get("w_m", 0.9))) / 2.0), 2)
                        old_dpos = float(dinfo.get("pos_m", def_d_pos))
                        new_dpos = dc3.number_input("بعد بداية الباب عن بداية الحائط (م)", 0.0, wlen, old_dpos, 0.05, "%.2f", key=f"m12_d_pos_{did}", help="المسافة من بداية الحائط حتى بداية الباب")
                        if new_dpos != old_dpos:
                            dinfo["pos_m"] = new_dpos
                            save_settings()
                        else:
                            dinfo["pos_m"] = new_dpos

                        dc4, dc5 = st.columns(2)
                        if is_h_wall:
                            leaf_opts = ["أعلى", "أسفل"]
                            hinge_opts = ["يسار", "يمين"]
                            leaf_lbl = "اتجاه الخطين المتعامدين (أعلى / أسفل)"
                            hinge_lbl = "اتجاه الباب / موضع المفصلة (يسار / يمين)"
                        else:
                            leaf_opts = ["يمين", "يسار"]
                            hinge_opts = ["أسفل", "أعلى"]
                            leaf_lbl = "اتجاه الخطين المتعامدين (يمين / يسار)"
                            hinge_lbl = "اتجاه الباب / موضع المفصلة (أسفل / أعلى)"

                        _dir_icons = {"أعلى": "⬆️ أعلى", "أسفل": "⬇️ أسفل", "يمين": "➡️ يمين", "يسار": "⬅️ يسار"}
                        cur_leaf = dinfo.get("leaf_dir", leaf_opts[0])
                        if cur_leaf not in leaf_opts: cur_leaf = leaf_opts[0]
                        idx_leaf = leaf_opts.index(cur_leaf)
                        cur_hinge = dinfo.get("hinge_dir", hinge_opts[0])
                        if cur_hinge not in hinge_opts: cur_hinge = hinge_opts[0]
                        idx_hinge = hinge_opts.index(cur_hinge)

                        with dc4:
                            dinfo["leaf_dir"] = st.selectbox(leaf_lbl, options=leaf_opts, index=idx_leaf,
                                                             format_func=lambda v: _dir_icons.get(v, v), key=f"m12_d_leaf_{did}")
                        with dc5:
                            dinfo["hinge_dir"] = st.selectbox(hinge_lbl, options=hinge_opts, index=idx_hinge,
                                                              format_func=lambda v: _dir_icons.get(v, v), key=f"m12_d_hinge_{did}")

                        # فحص الإحداثيات والتداخل مع الأعمدة وحدود المسقط الأفقي
                        d_errs = _validate_opening_coords(wk, f"الباب {dname}", "door", dinfo["w_m"], dinfo["h_m"], dinfo["pos_m"], leaf_dir=dinfo.get("leaf_dir"), current_op_id=did)
                        if dinfo["h_m"] > wh:
                            st.error(f"⚠️ ارتفاع الباب ({dinfo['h_m']:.2f}م) أكبر من ارتفاع الحائط ({wh:.2f}م)!")

                        if d_errs:
                            _render_big_warning(d_errs)

                        if st.session_state.get(f"m12_confirm_del_door_{did}"):
                            play_warning_sound()
                            st.warning(f"⚠️ تأكيد حذف الباب {dname} ونقله إلى سلة المهملات؟ (يمكنك استعادته لاحقاً)")
                            c_y_d, c_n_d = st.columns(2)
                            with c_y_d:
                                if st.button(f"✅ نعم، تأكيد حذف {dname}", type="primary", key=f"m12_conf_del_door_yes_{did}", use_container_width=True):
                                    _remove_opening_by_id(did, "door")
                                    st.session_state.pop(f"m12_confirm_del_door_{did}", None)
                                    st.rerun()
                            with c_n_d:
                                if st.button("❌ إلغاء", key=f"m12_conf_del_door_no_{did}", use_container_width=True):
                                    st.session_state.pop(f"m12_confirm_del_door_{did}", None)
                                    st.rerun()
                        else:
                            if st.button(f"🗑️ حذف الباب ونقله الي سلة المهملات", key=f"m12_del_door_btn_{did}", use_container_width=True):
                                st.session_state[f"m12_confirm_del_door_{did}"] = True
                                play_warning_sound()
                                st.rerun()
                st.session_state["m12_doors"][wk] = dl


def _section_move_openings():
    """قسم مخصص لتحريك الشبابيك والأبواب على محاورها مع فحص هندسي مسبق لمنع التجاوز أو التداخل."""
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m12_wall_removed", set())
    active_walls = [w for w in all_walls if w not in removed_walls]
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()
    _ensure_opening_names()

    tw, td = st.tabs(["🪟 تحريك الشبابيك", "🚪 تحريك الأبواب"])

    # ═══════════════════════════════════════════════════════════════════════
    # التبويبة 1: تحريك الشبابيك
    # ═══════════════════════════════════════════════════════════════════════
    with tw:
        st.markdown("<h5 style='color:#004488;margin-bottom:8px;'>↔️ تحريك الشبابيك على الحوائط</h5>", unsafe_allow_html=True)
        active_wins = []
        for wk in active_walls:
            for w in _get_wall_windows(wk):
                if not w.get("removed", False):
                    active_wins.append((wk, w))

        if not active_wins:
            st.info("💡 لا توجد شبابيك نشطة مُسقطة على الحوائط حالياً.")
        else:
            def _fmt_win(idx):
                wk_i, w_i = active_wins[idx]
                wn = wm_win.get(w_i.get("id")) or w_i.get("name", f"W_{w_i.get('id')}")
                wl = _wall_display_label(wk_i, cm, wm)
                is_h_i = (wk_i[1] == wk_i[3])
                ax_name = "محور أفقي" if is_h_i else "محور رأسي"
                pos_val = float(w_i.get("pos_m", 0.0))
                return f"🪟 {wn} [{w_i.get('type_label','W')}] على {wl} ({ax_name}) — الموضع الحالي: {pos_val:.2f}م"

            _safe_idx("m12_move_sel_win", len(active_wins))
            sel_win_idx = st.selectbox(
                "🪟 اختر الشباك المراد تحريكه:",
                options=range(len(active_wins)),
                format_func=_fmt_win,
                key="m12_move_sel_win"
            )

            sel_wk, sel_win = active_wins[sel_win_idx]
            wid = sel_win["id"]
            wname = wm_win.get(wid) or sel_win.get("name", "W")
            wlen = _wall_length_m(sel_wk)
            cur_pos = float(sel_win.get("pos_m", 0.0))
            w_w = float(sel_win.get("w_m", 1.0))
            w_h = float(sel_win.get("h_m", 1.2))
            is_h = (sel_wk[1] == sel_wk[3])
            wlbl = _wall_display_label(sel_wk, cm, wm)

            axis_desc = "محور أفقي (يمين ➡️ / يسار ⬅️)" if is_h else "محور رأسي (أعلى ⬆️ / أسفل ⬇️)"
            st.markdown(
                f"""<div style='background:#F8F9FA;border:1px solid #E2E8F0;border-right:5px solid #004488;
                    border-radius:6px;padding:8px 12px;margin-bottom:10px;' dir='rtl'>
                    <b style='font-size:1.02rem;color:#004488;'>🪟 شباك {wname} [{sel_win.get('type_label','W1')}]</b>
                    <span style='color:#555;font-size:0.86rem;margin-right:8px;'>على {wlbl} ({axis_desc})</span><br>
                    <span style='color:#444;font-size:0.86rem;'>
                        طول الحائط: <b>{wlen:.2f}م</b> &nbsp;|&nbsp;
                        عرض الشباك: <b>{w_w:.2f}م</b> &nbsp;|&nbsp;
                        الموضع الحالي (بعد البداية): <b>{cur_pos:.2f}م</b> (يمتد من {cur_pos:.2f}م إلى {cur_pos + w_w:.2f}م)
                    </span>
                </div>""",
                unsafe_allow_html=True
            )

            c_dist_w, c_dir_w = st.columns([1.2, 1.4])
            with c_dist_w:
                move_dist_w = st.number_input(
                    "📏 مسافة تحريك الشباك (م):",
                    min_value=0.01,
                    max_value=float(wlen),
                    value=0.50,
                    step=0.05,
                    format="%.2f",
                    key=f"m12_mv_dist_w_{wid}",
                    help="المسافة بالأمتار المراد إزاحة الشباك بها على الحائط"
                )

            with c_dir_w:
                if is_h:
                    dir_opts_w = ["يمين", "يسار"]
                    dir_icons_w = {"يمين": "➡️ يمين (زيادة الإحداثي)", "يسار": "⬅️ يسار (تقليل الإحداثي)"}
                    move_dir_w = st.radio(
                        "اتجاه تحريك الشباك:",
                        options=dir_opts_w,
                        format_func=lambda d: dir_icons_w[d],
                        horizontal=True,
                        key=f"m12_mv_dir_w_{wid}"
                    )
                else:
                    dir_opts_w = ["أعلى", "أسفل"]
                    dir_icons_w = {"أعلى": "⬆️ أعلى (زيادة الإحداثي)", "أسفل": "⬇️ أسفل (تقليل الإحداثي)"}
                    move_dir_w = st.radio(
                        "اتجاه تحريك الشباك:",
                        options=dir_opts_w,
                        format_func=lambda d: dir_icons_w[d],
                        horizontal=True,
                        key=f"m12_mv_dir_w_{wid}"
                    )

            if move_dir_w in ["يمين", "أعلى"]:
                new_pos_w = round(cur_pos + float(move_dist_w), 2)
            else:
                new_pos_w = round(cur_pos - float(move_dist_w), 2)

            move_errs_w = _validate_opening_coords(
                sel_wk, f"الشباك {wname}", "win", w_w, w_h, new_pos_w, current_op_id=wid
            )

            # بطاقة معاينة الموضع المستهدف قبل التنفيذ
            status_clr_w = "#DC2626" if move_errs_w else "#16A34A"
            status_txt_w = "🚨 يتعارض مع حدود الحائط أو فتحة أخرى!" if move_errs_w else "✅ الموضع المقترح متاح هندسياً"
            st.markdown(
                f"""<div style='background:#FAFAFA;border:1px dashed {status_clr_w};border-radius:6px;
                    padding:6px 12px;margin-bottom:8px;font-size:0.86rem;' dir='rtl'>
                    الموضع بعد التحريك: <b>{new_pos_w:.2f}م</b> (من {new_pos_w:.2f}م إلى {new_pos_w + w_w:.2f}م)
                    &nbsp;|&nbsp; <span style='color:{status_clr_w};font-weight:bold;'>{status_txt_w}</span>
                </div>""",
                unsafe_allow_html=True
            )

            if move_errs_w:
                _render_big_warning(move_errs_w)

            if st.button(f"🚀 تنفيذ تحريك الشباك {wname}", key=f"m12_btn_apply_mv_w_{wid}", type="primary", use_container_width=True):
                if move_errs_w:
                    play_warning_sound()
                    st.error("🚨 غير مسموح بالتحريك! إحداثيات الشباك بعد التحريك تتعارض مع حدود الحائط أو العمود أو فتحة أخرى.")
                else:
                    for wl in st.session_state.get("m12_windows", {}).values():
                        for w in wl:
                            if w.get("id") == wid:
                                w["pos_m"] = new_pos_w
                    _resequence_openings()
                    save_settings()
                    st.success(f"✅ تم تحريك الشباك {wname} بنجاح باتجاه {move_dir_w} بمقدار {move_dist_w:.2f}م (الموضع الجديد: {new_pos_w:.2f}م من بداية الحائط).")
                    st.rerun()

    # ═══════════════════════════════════════════════════════════════════════
    # التبويبة 2: تحريك الأبواب
    # ═══════════════════════════════════════════════════════════════════════
    with td:
        st.markdown("<h5 style='color:#2E7D32;margin-bottom:8px;'>↔️ تحريك الأبواب على الحوائط</h5>", unsafe_allow_html=True)
        active_doors = []
        for wk in active_walls:
            for d in _get_wall_doors(wk):
                if not d.get("removed", False):
                    active_doors.append((wk, d))

        if not active_doors:
            st.info("💡 لا توجد أبواب نشطة مُسقطة على الحوائط حالياً.")
        else:
            def _fmt_door(idx):
                wk_i, d_i = active_doors[idx]
                dn = wm_door.get(d_i.get("id")) or d_i.get("name", f"D_{d_i.get('id')}")
                wl = _wall_display_label(wk_i, cm, wm)
                is_h_i = (wk_i[1] == wk_i[3])
                ax_name = "محور أفقي" if is_h_i else "محور رأسي"
                pos_val = float(d_i.get("pos_m", 0.0))
                return f"🚪 {dn} [{d_i.get('type_label','D')}] على {wl} ({ax_name}) — الموضع الحالي: {pos_val:.2f}م"

            _safe_idx("m12_move_sel_door", len(active_doors))
            sel_door_idx = st.selectbox(
                "🚪 اختر الباب المراد تحريكه:",
                options=range(len(active_doors)),
                format_func=_fmt_door,
                key="m12_move_sel_door"
            )

            sel_wk_d, sel_door = active_doors[sel_door_idx]
            did = sel_door["id"]
            dname = wm_door.get(did) or sel_door.get("name", "D")
            wlen_d = _wall_length_m(sel_wk_d)
            cur_pos_d = float(sel_door.get("pos_m", 0.0))
            d_w = float(sel_door.get("w_m", 0.9))
            d_h = float(sel_door.get("h_m", 2.1))
            is_h_d = (sel_wk_d[1] == sel_wk_d[3])
            wlbl_d = _wall_display_label(sel_wk_d, cm, wm)

            axis_desc_d = "محور أفقي (يمين ➡️ / يسار ⬅️)" if is_h_d else "محور رأسي (أعلى ⬆️ / أسفل ⬇️)"
            st.markdown(
                f"""<div style='background:#F8F9FA;border:1px solid #E2E8F0;border-right:5px solid #2E7D32;
                    border-radius:6px;padding:8px 12px;margin-bottom:10px;' dir='rtl'>
                    <b style='font-size:1.02rem;color:#2E7D32;'>🚪 باب {dname} [{sel_door.get('type_label','D1')}]</b>
                    <span style='color:#555;font-size:0.86rem;margin-right:8px;'>على {wlbl_d} ({axis_desc_d})</span><br>
                    <span style='color:#444;font-size:0.86rem;'>
                        طول الحائط: <b>{wlen_d:.2f}م</b> &nbsp;|&nbsp;
                        عرض الباب: <b>{d_w:.2f}م</b> &nbsp;|&nbsp;
                        الموضع الحالي (بعد البداية): <b>{cur_pos_d:.2f}م</b> (يمتد من {cur_pos_d:.2f}م إلى {cur_pos_d + d_w:.2f}م)
                    </span>
                </div>""",
                unsafe_allow_html=True
            )

            c_dist_d, c_dir_d = st.columns([1.2, 1.4])
            with c_dist_d:
                move_dist_d = st.number_input(
                    "📏 مسافة تحريك الباب (م):",
                    min_value=0.01,
                    max_value=float(wlen_d),
                    value=0.50,
                    step=0.05,
                    format="%.2f",
                    key=f"m12_mv_dist_d_{did}",
                    help="المسافة بالأمتار المراد إزاحة الباب بها على الحائط"
                )

            with c_dir_d:
                if is_h_d:
                    dir_opts_d = ["يمين", "يسار"]
                    dir_icons_d = {"يمين": "➡️ يمين (زيادة الإحداثي)", "يسار": "⬅️ يسار (تقليل الإحداثي)"}
                    move_dir_d = st.radio(
                        "اتجاه تحريك الباب:",
                        options=dir_opts_d,
                        format_func=lambda d: dir_icons_d[d],
                        horizontal=True,
                        key=f"m12_mv_dir_d_{did}"
                    )
                else:
                    dir_opts_d = ["أعلى", "أسفل"]
                    dir_icons_d = {"أعلى": "⬆️ أعلى (زيادة الإحداثي)", "أسفل": "⬇️ أسفل (تقليل الإحداثي)"}
                    move_dir_d = st.radio(
                        "اتجاه تحريك الباب:",
                        options=dir_opts_d,
                        format_func=lambda d: dir_icons_d[d],
                        horizontal=True,
                        key=f"m12_mv_dir_d_{did}"
                    )

            if move_dir_d in ["يمين", "أعلى"]:
                new_pos_d = round(cur_pos_d + float(move_dist_d), 2)
            else:
                new_pos_d = round(cur_pos_d - float(move_dist_d), 2)

            move_errs_d = _validate_opening_coords(
                sel_wk_d, f"الباب {dname}", "door", d_w, d_h, new_pos_d,
                leaf_dir=sel_door.get("leaf_dir"), current_op_id=did
            )

            # بطاقة معاينة الموضع المستهدف قبل التنفيذ
            status_clr_d = "#DC2626" if move_errs_d else "#16A34A"
            status_txt_d = "🚨 يتعارض مع حدود الحائط أو فتحة أخرى!" if move_errs_d else "✅ الموضع المقترح متاح هندسياً"
            st.markdown(
                f"""<div style='background:#FAFAFA;border:1px dashed {status_clr_d};border-radius:6px;
                    padding:6px 12px;margin-bottom:8px;font-size:0.86rem;' dir='rtl'>
                    الموضع بعد التحريك: <b>{new_pos_d:.2f}م</b> (من {new_pos_d:.2f}م إلى {new_pos_d + d_w:.2f}م)
                    &nbsp;|&nbsp; <span style='color:{status_clr_d};font-weight:bold;'>{status_txt_d}</span>
                </div>""",
                unsafe_allow_html=True
            )

            if move_errs_d:
                _render_big_warning(move_errs_d)

            if st.button(f"🚀 تنفيذ تحريك الباب {dname}", key=f"m12_btn_apply_mv_d_{did}", type="primary", use_container_width=True):
                if move_errs_d:
                    play_warning_sound()
                    st.error("🚨 غير مسموح بالتحريك! إحداثيات الباب بعد التحريك تتعارض مع حدود الحائط أو العمود أو فتحة أخرى.")
                else:
                    for dl in st.session_state.get("m12_doors", {}).values():
                        for d in dl:
                            if d.get("id") == did:
                                d["pos_m"] = new_pos_d
                    _resequence_openings()
                    save_settings()
                    st.success(f"✅ تم تحريك الباب {dname} بنجاح باتجاه {move_dir_d} بمقدار {move_dist_d:.2f}م (الموضع الجديد: {new_pos_d:.2f}م من بداية الحائط).")
                    st.rerun()


def _section_delete_restore_openings():
    """قسم مخصص لحذف واستعادة الشبابيك والأبواب بتأكيد صوتي ورسائل واضحة."""
    all_walls = _get_all_walls()
    removed_walls = st.session_state.get("m12_wall_removed", set())
    active_walls = [w for w in all_walls if w not in removed_walls]
    cm = _get_col_name_map()
    wm = _get_wall_name_map()
    wm_win = _get_window_name_map()
    wm_door = _get_door_name_map()
    _ensure_opening_names()

    all_del = _get_all_deleted_openings()
    del_wins = [x for x in all_del if x["kind"] == "win"]
    del_doors = [x for x in all_del if x["kind"] == "door"]

    tab_w_lbl = f"🪟 حذف واستعادة الشبابيك ({len(del_wins)} محذوف)" if del_wins else "🪟 حذف واستعادة الشبابيك"
    tab_d_lbl = f"🚪 حذف واستعادة الأبواب ({len(del_doors)} محذوف)" if del_doors else "🚪 حذف واستعادة الأبواب"

    tw, td = st.tabs([tab_w_lbl, tab_d_lbl])

    # ═══════════════════════════════════════════════════════════════════════
    # التبويبة 1: حذف واستعادة الشبابيك
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
                        
                        # رسالة تأكيد الحذف الخاصة بالشباك مع صافرة
                        if st.session_state.get(f"m12_del_sec_conf_win_{wid}"):
                            play_warning_sound()
                            st.warning(f"⚠️ تأكيد حذف الشباك {wname} من {wlbl} ونقله إلى المحذوفات؟ (يمكنك استعادته لاحقاً)")
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
                                play_warning_sound()
                                st.rerun()

        st.markdown("---")
        st.markdown("<h5 style='color:#E65100;margin-bottom:8px;'>♻️ استعادة الشبابيك المحذوفة</h5>", unsafe_allow_html=True)
        if not del_wins:
            st.success("✅ لا توجد شبابيك محذوفة حالياً في المشروع.")
        else:
            top_w1, top_w2 = st.columns([3.5, 1.4])
            with top_w1:
                st.info(f"يوجد حالياً **{len(del_wins)}** شباك محذوف يمكن استعادتها إلى حوائطها الأصلية أو أي حائط بديل.")
            with top_w2:
                if st.button("♻️ استعادة كافة الشبابيك", key="m12_restore_all_wins"):
                    for itm in del_wins:
                        s_id = itm["id"]
                        for wl in st.session_state.get("m12_windows", {}).values():
                            for w in wl:
                                if w.get("id") == s_id:
                                    w["removed"] = False
                    _resequence_openings()
                    save_settings()
                    st.success("✅ تم استعادة كافة الشبابيك بنجاح.")
                    st.rerun()

            for item in del_wins:
                iid = item["id"]
                iname = item["name"]
                iwk = item["wk"]
                with st.container():
                    st.markdown(
                        f"""<div style='background:#FFFDF7;border:1px solid #FFE0B2;border-right:5px solid #FF9800;
                            border-radius:6px;padding:8px 12px;margin-bottom:6px;' dir='rtl'>
                            <b style='font-size:1.02rem;color:#E65100;'>🪟 شباك {iname}</b>
                            <span style='color:#666;font-size:0.86rem;margin-right:12px;'>[العرض: {item['w_m']:.2f}م × الارتفاع: {item['h_m']:.2f}م]</span>
                        </div>""",
                        unsafe_allow_html=True
                    )
                    rc1, rc2 = st.columns([3.8, 1.4])
                    with rc1:
                        def_idx = active_walls.index(iwk) if iwk in active_walls else 0
                        target_wall_idx = st.selectbox(
                            f"الحائط المستهدف لاستعادة {iname}:",
                            options=range(len(active_walls)),
                            index=def_idx,
                            format_func=lambda idx: _wall_display_label(active_walls[idx], cm, wm),
                            key=f"m12_restore_win_target_wall_{iid}"
                        )
                    with rc2:
                        st.write("")
                        if st.button(f"♻️ استعادة {iname}", key=f"m12_btn_restore_win_{iid}"):
                            target_wk = active_walls[target_wall_idx]
                            _restore_opening(item, target_wk)
                            save_settings()
                            st.success(f"✅ تم استعادة الشباك {iname} بنجاح إلى الحائط {_wall_display_label(target_wk, cm, wm)}.")
                            st.rerun()

    # ═══════════════════════════════════════════════════════════════════════
    # التبويبة 2: حذف واستعادة الأبواب
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
                        
                        # رسالة تأكيد الحذف الخاصة بالباب مع صافرة
                        if st.session_state.get(f"m12_del_sec_conf_door_{did}"):
                            play_warning_sound()
                            st.warning(f"⚠️ تأكيد حذف الباب {dname} من {wlbl} ونقله إلى المحذوفات؟ (يمكنك استعادته لاحقاً)")
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
                                play_warning_sound()
                                st.rerun()

        st.markdown("---")
        st.markdown("<h5 style='color:#2E7D32;margin-bottom:8px;'>♻️ استعادة الأبواب المحذوفة</h5>", unsafe_allow_html=True)
        if not del_doors:
            st.success("✅ لا توجد أبواب محذوفة حالياً في المشروع.")
        else:
            top_d1, top_d2 = st.columns([3.5, 1.4])
            with top_d1:
                st.info(f"يوجد حالياً **{len(del_doors)}** باب محذوف يمكن استعادتها إلى حوائطها الأصلية أو أي حائط بديل.")
            with top_d2:
                if st.button("♻️ استعادة كافة الأبواب", key="m12_restore_all_doors"):
                    for itm in del_doors:
                        s_id = itm["id"]
                        for dl in st.session_state.get("m12_doors", {}).values():
                            for d in dl:
                                if d.get("id") == s_id:
                                    d["removed"] = False
                    _resequence_openings()
                    save_settings()
                    st.success("✅ تم استعادة كافة الأبواب بنجاح.")
                    st.rerun()

            for item in del_doors:
                iid = item["id"]
                iname = item["name"]
                iwk = item["wk"]
                with st.container():
                    st.markdown(
                        f"""<div style='background:#FFFDF7;border:1px solid #C8E6C9;border-right:5px solid #388E3C;
                            border-radius:6px;padding:8px 12px;margin-bottom:6px;' dir='rtl'>
                            <b style='font-size:1.02rem;color:#2E7D32;'>🚪 باب {iname}</b>
                            <span style='color:#666;font-size:0.86rem;margin-right:12px;'>[العرض: {item['w_m']:.2f}م × الارتفاع: {item['h_m']:.2f}م]</span>
                        </div>""",
                        unsafe_allow_html=True
                    )
                    rd1, rd2 = st.columns([3.8, 1.4])
                    with rd1:
                        def_idx = active_walls.index(iwk) if iwk in active_walls else 0
                        target_wall_idx = st.selectbox(
                            f"الحائط المستهدف لاستعادة {iname}:",
                            options=range(len(active_walls)),
                            index=def_idx,
                            format_func=lambda idx: _wall_display_label(active_walls[idx], cm, wm),
                            key=f"m12_restore_door_target_wall_{iid}"
                        )
                    with rd2:
                        st.write("")
                        if st.button(f"♻️ استعادة {iname}", key=f"m12_btn_restore_door_{iid}"):
                            target_wk = active_walls[target_wall_idx]
                            _restore_opening(item, target_wk)
                            save_settings()
                            st.success(f"✅ تم استعادة الباب {iname} بنجاح إلى الحائط {_wall_display_label(target_wk, cm, wm)}.")
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
            "الطول (م)": round(length, 3),
            "الارتفاع (م)": round(height, 3),
            "إجمالي مسطح المحارة (m^2)": round(wall_gross, 3),
            "إجمالي مساحة الفتحات المخصومة (m^2)": round(wall_ded, 3),
            "صافي مسطح المحارة النهائي (m^2)": round(wall_net, 3),
            "كمية الرمل المطلوبة (m^3)": round(sand_m3, 3),
            "كمية الأسمنت (طن)": round(cement_tons, 3),
            "شكاير الأسمنت (50 كجم)": cement_bags,
            "كمية الأسمنت المطلوبة": f"{cement_tons:.3f} طن ({cement_bags} شكارة)",
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
                📦 <b>الخامات للحائط:</b> رمل: <b>{sel_sand:.3f} م³</b> | أسمنت: <b>{sel_cement_tons:.3f} طن ({sel_cement_bags} شكارة)</b>
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
            "إجمالي مسطح المحارة (m^2)": round(p_res["tot_gross"], 3),
            "إجمالي مساحة الفتحات المخصومة (m^2)": round(p_res["tot_ded"], 3),
            "صافي مسطح المحارة النهائي (m^2)": round(p_res["tot_net"], 3),
            "كمية الرمل المطلوبة (m^3)": round(p_res["tot_sand"], 3),
            "كمية الأسمنت المطلوبة": f"{p_res['tot_cement_tons']:.3f} طن ({p_res['tot_cement_bags']} شكارة)",
        }

        df_p = pd.DataFrame(display_rows + [tot_display])
        def _st_plaster(row):
            if row["الحائط"] == "✅ الإجمالي":
                return ["background-color:#1e3a8a;color:white;font-weight:bold"] * len(row)
            return [""] * len(row)

        st.dataframe(df_p.style.apply(_st_plaster, axis=1), use_container_width=True, hide_index=True)

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
                <div style='font-size:1.25rem;font-weight:bold;color:#c2410c;margin-top:4px;'>{g12:.3f} <span style='font-size:0.85rem;font-weight:normal;'>م² مسطح</span></div>
            </div>
            <div style='background-color:#f0fdf4;border-right:4px solid #16a34a;padding:10px 14px;border-radius:6px;'>
                <div style='font-size:0.82rem;color:#14532d;font-weight:bold;'>2️⃣ مساحة فتحات الأبواب والشبابيك:</div>
                <div style='font-size:1.25rem;font-weight:bold;color:#15803d;margin-top:4px;'>{op12:.3f} <span style='font-size:0.85rem;font-weight:normal;'>م² (لحوائط 12سم)</span> &nbsp;<span style='font-size:0.75rem;color:#4b5563;'>(الإجمالي العام: {total_openings:.3f} م²)</span></div>
            </div>
            <div style='background-color:#eff6ff;border-right:4px solid #2563eb;padding:10px 14px;border-radius:6px;'>
                <div style='font-size:0.82rem;color:#1e3a8a;font-weight:bold;'>3️⃣ صافي إجمالي مسطح طوب 12 سم:</div>
                <div style='font-size:1.25rem;font-weight:bold;color:#1d4ed8;margin-top:4px;'>{n12:.3f} <span style='font-size:0.85rem;font-weight:normal;'>م² مسطح صافي</span></div>
            </div>
            <div style='background-color:#fdf2f8;border-right:4px solid #db2777;padding:10px 14px;border-radius:6px;'>
                <div style='font-size:0.82rem;color:#831843;font-weight:bold;'>4️⃣ صافي إجمالي مكعب طوب 25 سم:</div>
                <div style='font-size:1.25rem;font-weight:bold;color:#be185d;margin-top:4px;'>{v25:.3f} <span style='font-size:0.85rem;font-weight:normal;'>م³ مكعب صافي</span></div>
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
        st.dataframe(df.style.apply(_st2, axis=1), use_container_width=True, hide_index=True)
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
                "إجمالي مسطح المحارة (m^2)": round(p_res["tot_gross"], 3),
                "إجمالي مساحة الفتحات المخصومة (m^2)": round(p_res["tot_ded"], 3),
                "صافي مسطح المحارة النهائي (m^2)": round(p_res["tot_net"], 3),
                "كمية الرمل المطلوبة (m^3)": round(p_res["tot_sand"], 3),
                "كمية الأسمنت المطلوبة": f"{p_res['tot_cement_tons']:.3f} طن ({p_res['tot_cement_bags']} شكارة)",
            }

            df_p = pd.DataFrame(display_rows + [tot_display])
            def _st_plaster_tab(row):
                if row["الحائط"] == "✅ الإجمالي":
                    return ["background-color:#1e3a8a;color:white;font-weight:bold"] * len(row)
                return [""] * len(row)

            st.dataframe(df_p.style.apply(_st_plaster_tab, axis=1), use_container_width=True, hide_index=True)

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
                "الكمية الصافية": round(n12, 3),
                "رمل صافي (م³)": round(sand_12, 3),
                "رمل مع الهالك 5% (م³)": round(sand_12 * 1.05, 3),
                "أسمنت (طن)": round((sand_12 * 1.05 * 350) / 1000.0, 3),
                "شكاير أسمنت (50كجم)": math.ceil((sand_12 * 1.05 * 350) / 50.0) if n12 > 0 else 0,
                brick_col_name: bricks_12,
            },
            {
                "بند الأعمال": f"مباني طوب سمك {_WALL_THICK} سم (طوبة كاملة)",
                "الوحدة": "م³ مكعب",
                "الكمية الصافية": round(v25, 3),
                "رمل صافي (م³)": round(sand_25, 3),
                "رمل مع الهالك 5% (م³)": round(sand_25 * 1.05, 3),
                "أسمنت (طن)": round((sand_25 * 1.05 * 350) / 1000.0, 3),
                "شكاير أسمنت (50كجم)": math.ceil((sand_25 * 1.05 * 350) / 50.0) if v25 > 0 else 0,
                brick_col_name: bricks_25,
            },
            {
                "بند الأعمال": "✅ الإجمالي الكلي لمواد البناء",
                "الوحدة": "—",
                "الكمية الصافية": "—",
                "رمل صافي (م³)": round(sand_net, 3),
                "رمل مع الهالك 5% (م³)": round(sand_total, 3),
                "أسمنت (طن)": round(cement_tons, 3),
                "شكاير أسمنت (50كجم)": cement_bags,
                brick_col_name: bricks_total,
            }
        ]

        if p_res["active_walls_count"] > 0:
            mat_rows.insert(-1, {
                "بند الأعمال": "بياض محارة (أوجه الحوائط المحددة - سمك 2 سم شامل الطرطشة)",
                "الوحدة": "م² مسطح",
                "الكمية الصافية": round(p_res["tot_net"], 3),
                "رمل صافي (م³)": round(p_res["tot_sand"] / 1.05, 3),
                "رمل مع الهالك 5% (م³)": round(p_res["tot_sand"], 3),
                "أسمنت (طن)": round(p_res["tot_cement_tons"], 3),
                "شكاير أسمنت (50كجم)": p_res["tot_cement_bags"],
                brick_col_name: "—",
            })
            total_sand_all = sand_total + p_res["tot_sand"]
            total_cement_tons_all = cement_tons + p_res["tot_cement_tons"]
            total_cement_bags_all = cement_bags + p_res["tot_cement_bags"]
            mat_rows[-1]["بند الأعمال"] = "✅ الإجمالي العام (مباني + محارة)"
            mat_rows[-1]["رمل مع الهالك 5% (م³)"] = round(total_sand_all, 3)
            mat_rows[-1]["أسمنت (طن)"] = round(total_cement_tons_all, 3)
            mat_rows[-1]["شكاير أسمنت (50كجم)"] = total_cement_bags_all

        df_mat = pd.DataFrame(mat_rows)
        def _st_mat(row):
            if row["بند الأعمال"] == "✅ الإجمالي الكلي لمواد البناء":
                return ["background-color:#1e3a8a;color:white;font-weight:bold"] * len(row)
            return [""] * len(row)
        st.dataframe(df_mat.style.apply(_st_mat, axis=1), use_container_width=True, hide_index=True)
        cb_mat = io.StringIO()
        df_mat.to_csv(cb_mat, index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ تحميل مقايسة الخامات CSV",
            data=cb_mat.getvalue().encode("utf-8-sig"),
            file_name="materials_boq_ecp.csv",
            mime="text/csv",
            key="m12_dl_materials"
        )

def render_brick_survey_module():
    """نقطة الدخول الرئيسية للـ Module 12."""
    st.session_state["nav_view"] = "module"
    st.session_state["in_module"] = True
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
        with st.expander("1️⃣ شبكة المحاور",expanded=(not is_openings_exp)): _section_axes()
        with st.expander("2️⃣ الأعمدة",expanded=False): _section_columns()
        with st.expander("3️⃣ الحوائط",expanded=False): _section_walls()
        with st.expander("4️⃣ نماذج الفتحات (Types)",expanded=False): _section_opening_types()
        openings_exp = st.expander(
            "5️⃣ إسقاط وتحريك الشبابيك والأبواب",
            expanded=bool(st.session_state.get("m12_openings_expander_open", is_openings_exp)),
            key="m12_openings_expander",
            on_change=_on_openings_expander_change
        )
        with openings_exp:
            _section_openings()
        with st.expander("6️⃣ حذف واستعادة الشبابيك والابواب",expanded=False): _section_delete_restore_openings()
        with st.expander("7️⃣ بيانات الطوب (BOQ)",expanded=False): _section_brick_type()
        with st.expander("8️⃣ تحديد حوائط المحارة",expanded=False): _section_plaster_walls()

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

        if is_interactive:
            _render_interactive_plan()
        else:
            st.image(_draw_plan(), use_container_width=True)
        st.markdown(
            f"""<div style='font-size:0.78rem;margin-top:3px;display:flex;gap:12px;flex-wrap:wrap;'>
                <span style='color:{_CLR_WALL_12};font-weight:bold;'>■ حائط 12سم</span>
                <span style='color:{_CLR_WALL_25};font-weight:bold;'>■ حائط 25سم</span>
                <span style='color:{_CLR_WIN};font-weight:bold;'>■ شباك (W#)</span>
                <span style='color:{_CLR_DOOR};font-weight:bold;'>■ باب (D#)</span>
                <span style='color:{_CLR_COL};font-weight:bold;'>■ عمود (C#)</span>
                <span style='color:#EC4899;font-weight:bold;'>▨ وجه محارة (وردي)</span>
                <span style='color:#222;font-weight:bold;'>■ حائط (L#)</span>
                <span style='color:#888;font-weight:bold;'>┄ خط استرشادي (محذوف)</span>
            </div>""",unsafe_allow_html=True)
        all_conflicts = _get_all_opening_conflicts()
        if all_conflicts and not st.session_state.get("m12_show_conflict_modal"):
            _render_big_warning(all_conflicts)
    st.divider()
    with st.expander("9️⃣ جدول الحصر النهائي", expanded=False):
        _section_survey()
    save_settings()

