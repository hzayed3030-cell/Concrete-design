"""
modules/axes_columns_copy.py
----------------------------
نسخ المحاور والأعمدة بين المشاريع (Axes & Columns Copy Engine).

- Compatibility Map: تحليل بنية بيانات كل موديول، ولا يُسمح بالنسخ إلا بين الموديولات
  التي تملك نفس مجموعة حقول الإدخال (المحاور، الأبعاد، الأعمدة، الترحيل، الاتجاه).
- Canonical model: تمثيل وسيط موحد {x_axes, y_axes, cols{(i,j): b,t,dir,sx,sy}}.
- لا يتم المساس بأي بيانات أخرى في المشروع الهدف (باستثناء تنظيف مخرجات مشتقة
  تعتمد على الشبكة، وحذف الحوائط/الفتحات التي تشير إلى محاور لم تعد موجودة).
"""

import copy
import re
import streamlit as st

import modules.settings as S

CAPS = ("axes", "dimensions", "columns", "offset", "orientation")

# ── Schema registry (مستخرجة من فحص كود الموديولات ومفاتيح profiles.json) ────────
MODULE_SCHEMAS = {
    0: {  # Module 1 — flat_slab.py
        "family": "FS_SPANS",
        "storage": "مفاتيح مسطحة fs_* (بحور spans)",
        "fields": {
            "axes": "fs_n_lx, fs_n_ly",
            "dimensions": "fs_lx_k, fs_ly_k (أبعاد البحور بين المحاور)",
            "columns": "fs_placed_cols, fs_removed_cols, fs_col_props (b_cm, t_cm)",
            "offset": "fs_col_transforms.shift_x / shift_y (±6 cm)",
            "orientation": "fs_col_transforms.direction (اتجاه X / اتجاه Y)",
        },
    },
    10: {  # Module 11 — Standalone Flat Slab (يستدعي نفس render و نفس المفاتيح)
        "family": "FS_SPANS",
        "storage": "مفاتيح مسطحة fs_* (نفس Module 1)",
        "fields": {
            "axes": "fs_n_lx, fs_n_ly",
            "dimensions": "fs_lx_k, fs_ly_k",
            "columns": "fs_placed_cols, fs_removed_cols, fs_col_props",
            "offset": "fs_col_transforms.shift_x / shift_y",
            "orientation": "fs_col_transforms.direction",
        },
    },
    14: {  # Module 15 — module_15_masonry_plaster.py
        "family": "M15_ABS",
        "storage": "module_15_masonry_plaster (إحداثيات محاور مطلقة)",
        "fields": {
            "axes": "x_axes, y_axes",
            "dimensions": "الفروق بين إحداثيات x_axes / y_axes",
            "columns": "col_placed, col_removed, col_props (b_cm, t_cm)",
            "offset": "col_shifts.shift_x / shift_y + col_shifted",
            "orientation": "col_dirs / col_props.dir_code (NS / EW)",
        },
    },
}

FAMILY_LABEL = {
    "FS_SPANS": "بنية البحور (fs_*)",
    "M15_ABS": "بنية الإحداثيات المطلقة (m15)",
}

FS_SHIFT_X = [
    "متمركز على المحور (Centered)",
    "جسم العمود يميناً (الوجه يسار المحور -6 cm)",
    "جسم العمود يساراً (الوجه يمين المحور +6 cm)",
]
FS_SHIFT_Y = [
    "متمركز على المحور (Centered)",
    "جسم العمود لأعلى (الوجه أسفل المحور -6 cm)",
    "جسم العمود لأسفل (الوجه أعلى المحور +6 cm)",
]
M15_SHIFT_X = [
    "متمركز على المحور (Centered)",
    "جسم العمود يميناً (الوجه يسار المحور - 6 cm)",
    "جسم العمود يساراً (الوجه يمين المحور + 6 cm)",
]
M15_SHIFT_Y = [
    "متمركز على المحور (Centered)",
    "جسم العمود لأعلى (الوجه أسفل المحور - 6 cm)",
    "جسم العمود لأسفل (الوجه أعلى المحور + 6 cm)",
]

MAX_SPANS = 20
M15_KEY = "module_15_masonry_plaster"


# ═════════════════════════════ Compatibility ═══════════════════════════════════
def _mod_short(idx: int) -> str:
    m = next((m for m in S.ALL_MODULES if m["idx"] == idx), None)
    return m["short"] if m else f"Module {idx + 1}"


def _mod_name(idx: int) -> str:
    m = next((m for m in S.ALL_MODULES if m["idx"] == idx), None)
    return m["name"] if m else f"Module {idx + 1}"


def is_eligible_module(idx: int) -> bool:
    sch = MODULE_SCHEMAS.get(idx)
    return bool(sch) and set(sch["fields"].keys()) == set(CAPS)


def modules_compatible(a: int, b: int) -> bool:
    """تطابق تام في مجموعة حقول (المحاور، الأبعاد، الأعمدة، الترحيل، الاتجاه)."""
    if not (is_eligible_module(a) and is_eligible_module(b)):
        return False
    return set(MODULE_SCHEMAS[a]["fields"]) == set(MODULE_SCHEMAS[b]["fields"])


def list_compatible_target_modules(source_idx: int) -> list:
    """قائمة فهارس الموديولات المتوافقة مع الموديول المصدر لإنشاء مشروع جديد بها."""
    return [
        m["idx"]
        for m in S.ALL_MODULES
        if is_eligible_module(m["idx"]) and modules_compatible(source_idx, m["idx"])
    ]


def get_compatibility_map() -> dict:
    """يعيد خريطة التوافق: {idx: {eligible, family, compatible_with:[idx...]}}."""
    out = {}
    for m in S.ALL_MODULES:
        i = m["idx"]
        ok = is_eligible_module(i)
        out[i] = {
            "name": m["name"],
            "short": m["short"],
            "eligible": ok,
            "family": MODULE_SCHEMAS[i]["family"] if ok else None,
            "compatible_with": [j["idx"] for j in S.ALL_MODULES if j["idx"] != i and modules_compatible(i, j["idx"])] if ok else [],
        }
    return out


def _pair_allowed(src_proj, src_idx, tgt_proj, tgt_idx) -> bool:
    if not modules_compatible(src_idx, tgt_idx):
        return False
    if src_proj == tgt_proj:
        if src_idx == tgt_idx:
            return False
        # نفس المشروع + نفس بنية المفاتيح (مثل Module 1 و 11) = نفس البيانات تماماً
        if MODULE_SCHEMAS[src_idx]["family"] == MODULE_SCHEMAS[tgt_idx]["family"]:
            return False
    return True


def list_endpoints() -> list:
    """كل (مشروع، موديول) مؤهل: [(project_name, idx)]."""
    res = []
    for pname in S.get_all_projects().keys():
        for idx in S.get_project_enabled_modules(pname):
            if is_eligible_module(idx):
                res.append((pname, idx))
    return res


def list_sources() -> list:
    """مصادر لها نظير متطابق واحد على الأقل يمكن النسخ إليه."""
    eps = list_endpoints()
    return [s for s in eps if any(_pair_allowed(s[0], s[1], t[0], t[1]) for t in eps)]


def list_targets(source: tuple) -> list:
    """أهداف مفلترة ديناميكياً حسب المصدر."""
    if not source:
        return []
    return [t for t in list_endpoints() if _pair_allowed(source[0], source[1], t[0], t[1])]


def endpoint_label(ep: tuple) -> str:
    return f"{ep[0]}  —  {_mod_short(ep[1])}"


# ═════════════════════════════ Helpers ═════════════════════════════════════════
def _f(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return float(d)


def _shift_idx_x(s) -> int:
    s = str(s or "").strip()
    # التحقق من "يسار" أولاً لتفادي تداخل نص "(الوجه يمين المحور)" مع "يمين"
    if "جسم العمود يسار" in s or s.startswith("يسار") or "Left" in s or "-X" in s or "يساراً" in s.split("(")[0]:
        return 2
    if "جسم العمود يمين" in s or s.startswith("يمين") or "Right" in s or "+X" in s or "يميناً" in s.split("(")[0]:
        return 1
    return 0


def _shift_idx_y(s) -> int:
    s = str(s or "").strip()
    # التحقق من "أسفل" و "أعلى" بالترتيب السليم
    if "جسم العمود لأسفل" in s or "جسم العمود لاسفل" in s or s.startswith("أسفل") or s.startswith("اسفل") or "Bottom" in s or "Down" in s or "-Y" in s or "لأسفل" in s.split("(")[0] or "لاسفل" in s.split("(")[0]:
        return 2
    if "جسم العمود لأعلى" in s or "جسم العمود لاعلي" in s or "جسم العمود لأعلي" in s or s.startswith("أعلى") or s.startswith("اعلي") or s.startswith("أعلي") or "Top" in s or "Up" in s or "+Y" in s or "لأعلى" in s.split("(")[0] or "لاعلي" in s.split("(")[0]:
        return 1
    return 0


def _cum(spans):
    out = [0.0]
    for s in spans:
        out.append(round(out[-1] + float(s), 4))
    return out


def _parse_ij(k):
    m = re.match(r"^\s*\(?\s*(-?\d+)\s*,\s*(-?\d+)\s*\)?\s*$", str(k))
    return (int(m.group(1)), int(m.group(2))) if m else None


# ═════════════════════════════ Readers (→ canonical) ═══════════════════════════
def _read_fs(d: dict) -> dict:
    n_lx = int(d.get("fs_n_lx", 0) or 0)
    n_ly = int(d.get("fs_n_ly", 0) or 0)
    lx = [_f(d.get(f"fs_lx_{k}", 6.0), 6.0) for k in range(n_lx)]
    ly = [_f(d.get(f"fs_ly_{k}", 6.0), 6.0) for k in range(n_ly)]
    if (not lx) and isinstance(d.get("fs_Lx_spans"), list):
        lx = [float(v) for v in d["fs_Lx_spans"]]
    if (not ly) and isinstance(d.get("fs_Ly_spans"), list):
        ly = [float(v) for v in d["fs_Ly_spans"]]
    n_xi, n_yj = len(lx) + 1, len(ly) + 1

    cols = {}
    used_canonical_fn = False
    try:
        from modules.flat_slab import get_flat_slab_columns, sync_all_columns_with_models
        active_cols, _, _, _, _ = get_flat_slab_columns(
            lx, ly,
            bc_cm=_f(d.get("slab_bc", 30.0), 30.0),
            tc_cm=_f(d.get("slab_tc", 50.0), 50.0),
            removed_ids=d.get("fs_removed_cols"),
            col_transforms=d.get("fs_col_transforms"),
            edge_columns=d.get("fs_edge_columns"),
            placed_cols=d.get("fs_placed_cols"),
            zero_col_mode=bool(d.get("fs_zero_col_mode", False)),
            col_props=d.get("fs_col_props"),
        )
        confirmed = d.get("fs_confirmed_col_dims") or {}
        if isinstance(confirmed, dict) and confirmed:
            try:
                active_cols = sync_all_columns_with_models(active_cols, confirmed)
            except Exception:
                pass

        for c in active_cols:
            i, j = int(c["i"]), int(c["j"])
            if 0 <= i < n_xi and 0 <= j < n_yj:
                dr = str(c.get("direction", "اتجاه Y"))
                cols[(i, j)] = {
                    "b": _f(c.get("b_cm", 30.0), 30.0),
                    "t": _f(c.get("t_cm", 50.0), 50.0),
                    "dir": "X" if "اتجاه X" in dr else "Y",
                    "sx": _shift_idx_x(c.get("shift_x")),
                    "sy": _shift_idx_y(c.get("shift_y")),
                }
        used_canonical_fn = True
    except Exception:
        used_canonical_fn = False

    if not used_canonical_fn:
        props = d.get("fs_col_props") if isinstance(d.get("fs_col_props"), dict) else {}
        trans = d.get("fs_col_transforms") if isinstance(d.get("fs_col_transforms"), dict) else {}
        removed = d.get("fs_removed_cols") if isinstance(d.get("fs_removed_cols"), list) else []
        placed = d.get("fs_placed_cols")
        zero = bool(d.get("fs_zero_col_mode", False))
        all_ids = [f"C{k}" for k in range(1, n_xi * n_yj + 1)]
        if zero or isinstance(placed, list):
            ids = [c for c in (placed or []) if c not in removed]
        else:
            ids = [c for c in all_ids if c not in removed]

        def_b = _f(d.get("fs_new_col_b", d.get("slab_bc", 30.0)), 30.0)
        def_t = _f(d.get("fs_new_col_t", d.get("slab_tc", 50.0)), 50.0)

        for cid in ids:
            m = re.match(r"^C(\d+)$", str(cid))
            if not m:
                continue
            k = int(m.group(1)) - 1
            i, j = k % n_xi, k // n_xi
            p = props.get(f"{i},{j}") or props.get(cid) or {}
            tr = trans.get(f"{i},{j}") or trans.get(cid) or p
            if "i" in p and "j" in p:
                i, j = int(p["i"]), int(p["j"])
            if not (0 <= i < n_xi and 0 <= j < n_yj):
                continue
            dr = str(tr.get("direction", p.get("direction", "اتجاه Y")))
            cols[(i, j)] = {
                "b": _f(p.get("b_cm", def_b), def_b),
                "t": _f(p.get("t_cm", def_t), def_t),
                "dir": "X" if "اتجاه X" in dr else "Y",
                "sx": _shift_idx_x(tr.get("shift_x", p.get("shift_x"))),
                "sy": _shift_idx_y(tr.get("shift_y", p.get("shift_y"))),
            }

    return {"x_axes": _cum(lx), "y_axes": _cum(ly), "cols": cols}


def _read_m15(d: dict) -> dict:
    m = d.get(M15_KEY) if isinstance(d.get(M15_KEY), dict) else {}
    dflt = S.get_default_module_15_state()
    xs = [float(v) for v in (m.get("x_axes") or dflt["x_axes"])]
    ys = [float(v) for v in (m.get("y_axes") or dflt["y_axes"])]
    placed = {tuple(int(v) for v in c) for c in (m.get("col_placed") or []) if len(c) == 2}
    removed = {tuple(int(v) for v in c) for c in (m.get("col_removed") or []) if len(c) == 2}
    props = m.get("col_props") or {}
    dirs = m.get("col_dirs") or {}
    shifts = m.get("col_shifts") or {}
    def_b = _f(m.get("new_col_b", m.get("col_width_cm", 25.0)), 25.0)
    def_t = _f(m.get("new_col_t", m.get("col_length_cm", 60.0)), 60.0)
    cols = {}
    for (i, j) in sorted(placed - removed):
        if not (0 <= i < len(xs) and 0 <= j < len(ys)):
            continue
        key = f"{i},{j}"
        p = props.get(key) or props.get((i, j)) or {}
        sh = shifts.get(key) or shifts.get((i, j)) or {}
        dc = p.get("dir_code") or dirs.get(key) or dirs.get((i, j)) or "NS"
        cols[(i, j)] = {
            "b": _f(p.get("b_cm", def_b), def_b),
            "t": _f(p.get("t_cm", def_t), def_t),
            "dir": "X" if str(dc) == "EW" else "Y",
            "sx": _shift_idx_x(sh.get("shift_x", p.get("shift_x"))),
            "sy": _shift_idx_y(sh.get("shift_y", p.get("shift_y"))),
        }
    return {"x_axes": xs, "y_axes": ys, "cols": cols}


def read_canonical(pdata: dict, idx: int) -> dict:
    fam = MODULE_SCHEMAS[idx]["family"]
    return _read_fs(pdata) if fam == "FS_SPANS" else _read_m15(pdata)


# ═════════════════════════════ Writers (canonical →) ═══════════════════════════
def _write_fs(d: dict, canon: dict) -> dict:
    xs, ys = canon["x_axes"], canon["y_axes"]
    n_lx, n_ly = len(xs) - 1, len(ys) - 1
    if n_lx < 1 or n_ly < 1:
        raise ValueError("المشروع المصدر لا يحتوي على محاور كافية (يلزم محورين على الأقل في كل اتجاه).")
    if n_lx > MAX_SPANS or n_ly > MAX_SPANS:
        raise ValueError(f"عدد البحور في المصدر ({n_lx}×{n_ly}) يتجاوز الحد الأقصى المسموح في الموديول الهدف ({MAX_SPANS}).")
    lx = [round(xs[k + 1] - xs[k], 4) for k in range(n_lx)]
    ly = [round(ys[k + 1] - ys[k], 4) for k in range(n_ly)]
    d["fs_n_lx"], d["fs_n_ly"] = n_lx, n_ly
    for k, v in enumerate(lx):
        d[f"fs_lx_{k}"] = v
    for k, v in enumerate(ly):
        d[f"fs_ly_{k}"] = v
    d["fs_Lx_spans"], d["fs_Ly_spans"] = list(lx), list(ly)

    n_xi = n_lx + 1
    placed, props, trans = [], {}, {}
    for (i, j), c in sorted(canon["cols"].items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if not (0 <= i < n_xi and 0 <= j <= n_ly):
            continue
        cid = f"C{j * n_xi + i + 1}"
        placed.append(cid)
        direction = "اتجاه X" if c["dir"] == "X" else "اتجاه Y"
        p = {
            "model": f"C({int(round(c['b']))}x{int(round(c['t']))})",
            "b_cm": float(c["b"]), "t_cm": float(c["t"]),
            "direction": direction,
            "shift_x": FS_SHIFT_X[c["sx"]], "shift_y": FS_SHIFT_Y[c["sy"]],
            "i": int(i), "j": int(j),
        }
        t = {"direction": direction, "shift_x": p["shift_x"], "shift_y": p["shift_y"]}
        props[cid], props[f"{i},{j}"] = p, dict(p)
        trans[cid], trans[f"{i},{j}"] = t, dict(t)
    d["fs_zero_col_mode"] = True
    d["fs_placed_cols"] = placed
    d["fs_removed_cols"] = []
    d["fs_col_props"] = props
    d["fs_col_transforms"] = trans

    # تحديث الأبعاد الافتراضية للأعمدة الجديدة لتماثل النموذج المنسوخ
    first_c = next(iter(canon["cols"].values()), None)
    if first_c:
        d["slab_bc"] = float(first_c["b"])
        d["slab_tc"] = float(first_c["t"])
        d["fs_new_col_b"] = float(first_c["b"])
        d["fs_new_col_t"] = float(first_c["t"])

    # مخرجات مشتقة تعتمد على الشبكة القديمة (يعاد توليدها عند إعادة التصميم)
    for k in ("fs_building_columns", "fs_confirmed_col_dims", "fs_col_models_dict"):
        d.pop(k, None)
    d["fs_edge_columns"] = {}
    vp = d.get("fs_void_panels")
    if isinstance(vp, list):
        keep = []
        for pid in vp:
            m = re.match(r"^P_(\d+)_(\d+)$", str(pid))
            if m and int(m.group(1)) <= n_lx and int(m.group(2)) <= n_ly:
                keep.append(pid)
        d["fs_void_panels"] = keep
    d["_fs_grid_ver"] = int(d.get("_fs_grid_ver", 0) or 0) + 1
    return {"pruned": 0}


def _wall_ok(t, nx, ny):
    try:
        i1, j1, i2, j2 = [int(v) for v in t]
    except Exception:
        return False
    return 0 <= i1 < nx and 0 <= i2 < nx and 0 <= j1 < ny and 0 <= j2 < ny


def _wall_key_ok(k, nx, ny):
    parts = str(k).strip("() ").split(",")
    return len(parts) == 4 and _wall_ok(parts, nx, ny)


def _write_m15(d: dict, canon: dict) -> dict:
    xs, ys = canon["x_axes"], canon["y_axes"]
    if len(xs) < 2 or len(ys) < 2:
        raise ValueError("المشروع المصدر لا يحتوي على محاور كافية.")
    m = d.get(M15_KEY)
    if not isinstance(m, dict):
        m = S.get_default_module_15_state()
    m["x_axes"], m["y_axes"] = [float(v) for v in xs], [float(v) for v in ys]
    nx, ny = len(xs), len(ys)

    placed, dirs, shifts, shifted, props = [], {}, {}, {}, {}
    for (i, j), c in sorted(canon["cols"].items()):
        if not (0 <= i < nx and 0 <= j < ny):
            continue
        key = f"{i},{j}"
        code = "EW" if c["dir"] == "X" else "NS"
        cw, ch = (c["t"], c["b"]) if code == "EW" else (c["b"], c["t"])  # سم
        dx = (cw / 2.0 - 6.0) if c["sx"] == 1 else ((6.0 - cw / 2.0) if c["sx"] == 2 else 0.0)
        dy = (ch / 2.0 - 6.0) if c["sy"] == 1 else ((6.0 - ch / 2.0) if c["sy"] == 2 else 0.0)
        placed.append([i, j])
        dirs[key] = code
        shifts[key] = {"shift_x": M15_SHIFT_X[c["sx"]], "shift_y": M15_SHIFT_Y[c["sy"]]}
        shifted[key] = [round(dx, 4), round(dy, 4)]
        props[key] = {
            "model": f"C({int(round(c['b']))}x{int(round(c['t']))})",
            "b_cm": float(c["b"]), "t_cm": float(c["t"]),
            "dir": "أفقي" if code == "EW" else "رأسي", "dir_code": code,
            "anchor": "السنتر", "corner": "أعلى اليمين",
            "shift_x": M15_SHIFT_X[c["sx"]], "shift_y": M15_SHIFT_Y[c["sy"]],
        }
    m["col_placed"], m["col_removed"] = placed, []
    m["col_dirs"], m["col_shifts"], m["col_shifted"], m["col_props"] = dirs, shifts, shifted, props
    m["deleted_cols_history"] = {}

    first_c = next(iter(canon["cols"].values()), None)
    if first_c:
        m["col_width_cm"] = float(first_c["b"])
        m["col_length_cm"] = float(first_c["t"])
        m["new_col_b"] = float(first_c["b"])
        m["new_col_t"] = float(first_c["t"])
        m["new_col_model"] = f"C({int(round(first_c['b']))}x{int(round(first_c['t']))})"

    # حذف أي عناصر حوائط/فتحات تشير إلى محاور لم تعد موجودة (حماية من الأخطاء)
    pruned = 0
    for fld in ("walls_placed", "wall_removed", "parapet_walls"):
        old = m.get(fld) or []
        new = [w for w in old if _wall_ok(w, nx, ny)]
        pruned += len(old) - len(new)
        m[fld] = new
    for fld in ("wall_thickness", "wall_heights", "windows", "doors", "plaster_faces"):
        old = m.get(fld) or {}
        new = {k: v for k, v in old.items() if _wall_key_ok(k, nx, ny)}
        pruned += len(old) - len(new) if fld in ("windows", "doors") else 0
        m[fld] = new
    spaces = m.get("named_spaces") or []
    keep_sp = []
    for s in spaces:
        cells = s.get("cells", []) if isinstance(s, dict) else []
        if all(0 <= int(c[0]) < nx - 1 and 0 <= int(c[1]) < ny - 1 for c in cells):
            keep_sp.append(s)
    pruned += len(spaces) - len(keep_sp)
    m["named_spaces"] = keep_sp
    d[M15_KEY] = m
    return {"pruned": pruned}


def write_canonical(pdata: dict, idx: int, canon: dict) -> dict:
    fam = MODULE_SCHEMAS[idx]["family"]
    return _write_fs(pdata, canon) if fam == "FS_SPANS" else _write_m15(pdata, canon)


# ═════════════════════════════ Public API ══════════════════════════════════════
def target_has_data(tgt_proj: str, tgt_idx: int) -> bool:
    """هل يحتوي الهدف على أعمدة موجودة مسبقاً (يستلزم رسالة تأكيد)؟"""
    pdata = S.get_all_projects().get(tgt_proj, {}).get("data", {})
    try:
        return len(read_canonical(pdata, tgt_idx)["cols"]) > 0
    except Exception:
        return False


def summarize(proj: str, idx: int) -> str:
    pdata = S.get_all_projects().get(proj, {}).get("data", {})
    c = read_canonical(pdata, idx)
    return f"{len(c['x_axes'])} محور رأسي × {len(c['y_axes'])} محور أفقي، {len(c['cols'])} عمود"


def copy_axes_columns(src: tuple, tgt: tuple) -> dict:
    """ينفذ النسخ. يعيد {ok, message, pruned}. يرفع استثناء عند عدم التوافق."""
    sp, si = src
    tp, ti = tgt
    if not _pair_allowed(sp, si, tp, ti):
        raise ValueError("النسخ غير مسموح: الموديولان غير متطابقين في حقول المحاور والأعمدة.")

    active = S.get_active_project_name()
    if active in (sp, tp):
        try:
            S.save_settings()  # تثبيت آخر تعديلات المشروع النشط قبل القراءة/الكتابة
        except Exception:
            pass

    pdata_all = S.load_profiles_data()
    profiles = pdata_all.get("profiles", {})
    if sp not in profiles or tp not in profiles:
        raise ValueError("تعذر العثور على المشروع المصدر أو الهدف.")

    canon = copy.deepcopy(read_canonical(profiles[sp].get("data", {}), si))
    if len(canon["x_axes"]) < 2 or len(canon["y_axes"]) < 2:
        raise ValueError("المشروع المصدر لا يحتوي على محاور.")

    tdata = profiles[tp].setdefault("data", {})
    work = copy.deepcopy(tdata)  # كتابة على نسخة؛ لا يتم الحفظ إلا عند نجاح كل شيء
    res = write_canonical(work, ti, canon)
    profiles[tp]["data"] = work
    profiles[tp]["updated_at"] = S._get_now_str()
    if not S.save_profiles_data(pdata_all):
        raise ValueError("فشل حفظ الملف profiles.json.")

    if tp == active:
        S.set_active_profile(tp)  # إعادة تحميل الجلسة من البيانات الجديدة

    return {"ok": True, "pruned": res.get("pruned", 0), "n_cols": len(canon["cols"])}


def create_project_with_copied_axes(
    source: tuple,
    target_module_idx: int,
    new_project_name: str,
    description: str = "",
) -> dict:
    """
    إنشاء مشروع جديد كلياً بالاعتماد على نسخ المحاور والأبعاد والأعمدة وترحيلاتها
    واتجاهاتها من مشروع مصدر مؤهل.
    """
    sp, si = source
    ti = int(target_module_idx)
    if not is_eligible_module(ti):
        raise ValueError("الموديول المستهدف غير مؤهل للنسخ.")
    if not modules_compatible(si, ti):
        raise ValueError("الموديولان غير متطابقين في بنية مدخلات المحاور والأعمدة.")

    name = (new_project_name or "").strip()
    if not name:
        raise ValueError("يرجى إدخال اسم للمشروع الجديد.")

    # 1. تحديد enabled_modules للمشروع الجديد مع مراعاة التبعيات الإنشائية
    if ti == 0:  # Module 1 يتطلب الموديولات 1..6
        enabled_modules = [0, 1, 2, 3, 4, 5, 6]
    elif ti == 10:  # Module 11 Standalone
        enabled_modules = [10]
    elif ti == 14:  # Module 15 Masonry & Plastering
        enabled_modules = [14]
    else:
        enabled_modules = [ti]

    # 2. استخراج النموذج الوسيط الموحد من المشروع المصدر
    active = S.get_active_project_name()
    if active == sp and "cfg" in st.session_state:
        try:
            S.save_settings()
        except Exception:
            pass

    pdata_all = S.load_profiles_data()
    profiles = pdata_all.get("profiles", {})
    if sp not in profiles:
        raise ValueError(f"تعذر العثور على المشروع المصدر «{sp}».")

    canon = copy.deepcopy(read_canonical(profiles[sp].get("data", {}), si))
    if len(canon["x_axes"]) < 2 or len(canon["y_axes"]) < 2:
        raise ValueError("المشروع المصدر لا يحتوي على محاور صالحة للنسخ.")

    # 3. إنشاء المشروع الجديد بنظافة مع الإعدادات الافتراضية
    desc = description.strip() or f"مشروع جديد منسوخ المحاور والأعمدة من «{sp}»"
    created_name = S.create_project(
        project_name=name,
        description=desc,
        enabled_modules=enabled_modules,
    )

    # 4. إعادة تحميل المشاريع وتطبيق المحاور والأعمدة المنسوخة في المشروع المنشأ
    pdata_all = S.load_profiles_data()
    profiles = pdata_all.get("profiles", {})
    if created_name not in profiles:
        raise ValueError("حدث خطأ غير متوقع أثناء حفظ المشروع الجديد.")

    work = copy.deepcopy(profiles[created_name].get("data", {}))
    res = write_canonical(work, ti, canon)
    work["selected_module_idx"] = ti
    profiles[created_name]["data"] = work
    profiles[created_name]["updated_at"] = S._get_now_str()

    if not S.save_profiles_data(pdata_all):
        raise ValueError("فشل حفظ ملف المشاريع profiles.json.")

    # 5. تفعيل المشروع الجديد وتحديث شاشة العمل
    try:
        S.set_active_profile(created_name, clear_cache=True)
        st.session_state["selected_module_idx"] = ti
        st.session_state["_force_module_idx"] = ti
    except Exception:
        pass

    return {
        "ok": True,
        "project_name": created_name,
        "n_cols": len(canon["cols"]),
        "n_x": len(canon["x_axes"]),
        "n_y": len(canon["y_axes"]),
        "pruned": res.get("pruned", 0),
        "target_mod_name": _mod_short(ti),
    }
