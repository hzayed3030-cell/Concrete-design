r"""
modules/extra_steel_zones.py
============================
Unified engine for **Extra Reinforcement Zones** (Bottom & Top, X & Y directions,
plus Column-Cap zones) in the Flat Slab module (ECP 203).

Philosophy (Capacity-Based Additional Reinforcement & Layout Detailing)
-----------------------------------------------------------------------
1. **Capacity Check (حساب سعة العزم للشبكة الأساسية)**:
   - Calculate the maximum resisting moment capacity of the entered base mesh $M_{cap}$
     (bottom / top in each direction $X$ and $Y$).
   - Compare the applied moment per meter $M_u$ ($M_{11}$ for X-direction or $M_{22}$
     for Y-direction) against $M_{cap}$.
   - If $M_u \le M_{cap}$, no additional steel is needed ($n_{add} = 0$) and the zone
     relies solely on the base mesh.

2. **Additional Rebar Calculation (تحديد فرق العزم والحديد الإضافي)**:
   - When $\Delta M = M_u - M_{cap} > 0$, calculate the required additional steel area
     $A_{s,add}$ to cover $\Delta M$ using the specified bar diameter.
   - Round the number of additional bars per meter up to the nearest practical integer:
     * Small moment difference: 1 bar/m -> $+1$ bar/m.
     * Medium to large moment difference: 2, 3, or more bars/m -> actual calculated integer count.

3. **Layout Annotation Rules (قواعد التسمية والترميز على المخطط)**:
   - Full descriptive text:
     * 1 bar: `حديد إضافي: 1 سيخ فاي [القطر] / م (إضافة إلى الشبكة الأساسية [العدد] فاي [القطر] / م)`
     * Multiple bars: `حديد إضافي: [العدد] أسياخ فاي [القطر] / م (إضافة إلى الشبكة الأساسية [العدد] فاي [القطر] / م)`
   - Practical drawing Tag (`Text Label`):
     * `إضافي: [العدد] T[القطر] / م (+ شبكة أساسية [العدد] T[القطر] / م)`

4. **Visual CAD Representation (in "🗺️ Steel Layout (مسقط أفقي لتسليح البلاطة)")**:
   - Hatched rectangular zone covering `(length × distribution width)` so the
     moment concentration zone is visually unmistakable.
   - Bold representative rebar line along the bar direction with end ticks,
     plus a perpendicular distribution-extent line with arrows.
   - A single consolidated callout tag placed at the **center of the distribution distance**.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Union
import matplotlib.patches as patches


# Legacy constant kept at 0.0 so any external import remains compatible without suppressing small diffs
EXTRA_STEEL_THRESHOLD_CM2_M: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
#  1. FLEXURAL & DETAILING HELPERS (ECP 203 — Working Units: ton, m, cm, kg/cm²)
# ═══════════════════════════════════════════════════════════════════════════

def bar_area(dia_mm: float) -> float:
    """Cross-sectional area of one bar in cm²."""
    return math.pi * (dia_mm / 10.0) ** 2 / 4.0


def round_up_5cm(val_m: float) -> float:
    """Round a length in meters UP to the nearest 0.05 m (5 cm)."""
    return math.ceil(round(float(val_m or 0.0) * 100.0, 4) / 5.0) * 0.05


def round_up_length(val_m: float) -> float:
    """Alias for round_up_5cm (rounds bar length in meters up to nearest 5 cm)."""
    return round_up_5cm(val_m)


def development_length(
    dia_mm: float,
    fcu_kgcm2: float = 250.0,
    fy_kgcm2: float = 4000.0,
    top_bar: bool = False,
) -> float:
    """
    ECP 203 Anchorage / Development Length Ld in meters.
    Accounts for top-bar modification factor (1.30) and concrete/steel grades.
    """
    dia_m = float(dia_mm or 12) / 1000.0
    fcu_mpa = max(20.0, float(fcu_kgcm2 or 250.0) * 0.0980665)
    fy_mpa = max(240.0, float(fy_kgcm2 or 4000.0) * 0.0980665)
    fbu = 0.30 * math.sqrt(fcu_mpa / 1.50)
    ld_raw = ((fy_mpa / 1.15) * dia_m) / (4.0 * max(0.5, fbu))
    if top_bar:
        ld_raw *= 1.30
    return round(max(0.35, 40.0 * dia_m, ld_raw), 2)


def bars_per_meter(delta_As_cm2_m: float, dia_mm: float) -> int:
    """
    Calculate the practical integer number of additional bars per meter
    required to cover *delta_As_cm2_m* (cm²/m) using diameter *dia_mm*:
      - If delta_As_cm2_m <= 0: returns 0.
      - If requires 1 bar: returns 1 (+1 bar/m).
      - If requires 2, 3, or more bars: returns the rounded-up integer count.
    """
    d_as = float(delta_As_cm2_m or 0.0)
    if d_as <= 1e-4:
        return 0
    a_b = bar_area(float(dia_mm or 12))
    if a_b <= 1e-6:
        return 0
    return max(1, int(math.ceil(round(d_as / a_b, 6) - 1e-9)))


def total_bars(n_bars_per_m: int, dist_width_m: float) -> int:
    """Total number of extra bars distributed across *dist_width_m* (m)."""
    bpm = int(n_bars_per_m or 0)
    w = float(dist_width_m or 0.0)
    if bpm <= 0 or w <= 1e-4:
        return 0
    return max(1, int(math.ceil(round(bpm * w, 6) - 1e-9)))


def as_required_per_m(
    Mu_ton_m_per_m: float,
    d_cm: float,
    fcu_kgcm2: float,
    fy_kgcm2: float,
) -> float:
    """
    Exact ECP 203 Ultimate Limit State flexural steel per 1.0 m width (cm²/m)
    needed to resist *Mu_ton_m_per_m* (ton·m / m).
    Does NOT clamp to As,min because we want the true demand vs. the base mesh.
    """
    Mu = abs(float(Mu_ton_m_per_m or 0.0))
    if Mu <= 1e-6 or d_cm <= 0 or fcu_kgcm2 <= 0 or fy_kgcm2 <= 0:
        return 0.0
    b_cm = 100.0
    gamma_c = 1.50
    gamma_s = 1.15
    fcd = 0.67 * fcu_kgcm2 / gamma_c
    fyd = fy_kgcm2 / gamma_s
    M_kgcm = Mu * 1e5
    rn = M_kgcm / (fcd * b_cm * (d_cm ** 2))
    # Cap at R_max (c/d_max ≈ 0.44 → a/d ≈ 0.352 → rn_max ≈ 0.29)
    rn = min(rn, 0.29)
    disc = max(0.0, 1.0 - 2.0 * rn)
    omega = 1.0 - math.sqrt(disc)
    As_req = omega * b_cm * d_cm * (fcd / fyd)
    return max(0.0, As_req)


def mu_capacity_per_m(
    As_prov_cm2_m: float,
    d_cm: float,
    fcu_kgcm2: float,
    fy_kgcm2: float,
) -> float:
    """
    Moment capacity (ton·m / m) of a 1.0 m slab strip reinforced with
    *As_prov_cm2_m* (cm²/m) according to ECP 203.
    """
    if As_prov_cm2_m <= 0 or d_cm <= 0 or fcu_kgcm2 <= 0 or fy_kgcm2 <= 0:
        return 0.0
    b_cm = 100.0
    fcd = 0.67 * fcu_kgcm2 / 1.50
    fyd = fy_kgcm2 / 1.15
    a_cm = (As_prov_cm2_m * fyd) / (b_cm * fcd)
    a_cm = min(a_cm, 0.36 * d_cm)
    lever = max(0.5 * d_cm, d_cm - a_cm / 2.0)
    M_kgcm = As_prov_cm2_m * fyd * lever
    return M_kgcm / 1e5


class RebarCalcResult(tuple):
    """
    2-tuple `(n_add, text_label)` returned by `calculate_additional_reinforcement`
    that also supports attribute and dictionary-key access to full calculation details:
      - `n_add, text_label = calculate_additional_reinforcement(...)`
      - `res.full_label`, `res.delta_M`, `res.As_add_req`, `res.As_add_prov`, etc.
    """
    def __new__(cls, n_add: int, text_label: str, meta: Optional[Dict] = None):
        obj = super().__new__(cls, (int(n_add), str(text_label)))
        obj._meta = dict(meta or {})
        obj._meta.setdefault("n_add", int(n_add))
        obj._meta.setdefault("text_label", str(text_label))
        return obj

    def __getattr__(self, name: str):
        if "_meta" in self.__dict__ and name in self._meta:
            return self._meta[name]
        raise AttributeError(f"'RebarCalcResult' object has no attribute '{name}'")

    def get(self, key: str, default=None):
        return self._meta.get(key, default)

    def to_dict(self) -> Dict:
        return dict(self._meta)


def format_additional_rebar_annotations(
    n_add: int,
    bar_diameter: int,
    base_bars_count: int,
    base_bar_diameter: Optional[int] = None,
) -> Tuple[str, str]:
    """
    Returns `(text_label, full_label)` using the standard engineering notation:
      - `text_label` (drawing tag):
        `{n_add}Ø{bar_diameter} /m`  (e.g. `3Ø12 /m`)
      - `full_label` (descriptive text):
        `{n_add}Ø{bar_diameter} /m (+ شبكة أساسية {base_bars_count}Ø{base_dia} /m)`
    """
    n_add_int = int(max(0, n_add))
    dia_int = int(bar_diameter or 12)
    base_cnt_int = int(base_bars_count or 5)
    base_dia_int = int(base_bar_diameter if base_bar_diameter is not None else dia_int)

    if n_add_int <= 0:
        return "", f"الشبكة الأساسية كافية ({base_cnt_int}Ø{base_dia_int} /m)"

    text_label = f"{n_add_int}Ø{dia_int} /m"
    full_label = f"{n_add_int}Ø{dia_int} /m (+ شبكة أساسية {base_cnt_int}Ø{base_dia_int} /m)"
    return text_label, full_label


def calculate_additional_reinforcement(
    M_applied: float,
    M_mesh: float,
    bar_diameter: int,
    base_bars_count: int,
    d_cm: Optional[float] = None,
    fcu: float = 250.0,
    fy: float = 4000.0,
    base_bar_diameter: Optional[int] = None,
) -> RebarCalcResult:
    """
    ربط نتائج عزوم البلاطة (M11, M22) بسعة شبكة التسليح الأساسية وتوليد نصوص التسليح الإضافي تلقائياً.

    Parameters
    ----------
    M_applied : float
        العزم المطبق لكل متر (ton.m/m) سواء M11 للاتجاه X أو M22 للاتجاه Y.
    M_mesh : float
        العزم الأقصى المقاوم للشبكة الأساسية المدخلة M_cap لكل متر (ton.m/m).
    bar_diameter : int
        قطر حديد التسليح الإضافي بالملليمتر (mm).
    base_bars_count : int
        عدد أسياخ الشبكة الأساسية في المتر الطولي.
    d_cm : float, optional
        العمق الفعال للبلاطة (cm). في حال تمريره يتم حساب As_add بمعادلات الاتزان الكودية الدقيقة ECP 203.
    fcu : float, optional
        مقاومة الخرسانة المميزة (kg/cm²)، افتراضياً 250.
    fy : float, optional
        إجهاد خضوع الحديد (kg/cm²)، افتراضياً 4000.
    base_bar_diameter : int, optional
        قطر حديد الشبكة الأساسية بالملليمتر (إن اختلف عن قطر الإضافي).

    Returns
    -------
    RebarCalcResult (2-tuple `(n_add, text_label)` with extra metadata attributes)
        - `n_add` (int): عدد الأسياخ الإضافية لكل متر (0 إذا كان M_applied <= M_mesh، أو 1، 2، 3...).
        - `text_label` (str): نص الوسم الجاهز للرسم على المخطط، مثال:
          `"3Ø12 /m"`
        - كما يحتوي الكائن المُرجع على الخصائص:
          `.full_label`, `.delta_M`, `.As_add_req`, `.As_add_prov`, `.As_req_total`, `.As_mesh_prov`.
    """
    M_app = abs(float(M_applied or 0.0))
    M_cap = abs(float(M_mesh or 0.0))
    dia = int(bar_diameter or 12)
    base_cnt = int(base_bars_count or 5)
    base_dia = int(base_bar_diameter if base_bar_diameter is not None else dia)

    a_bar = bar_area(dia)
    a_base = bar_area(base_dia)
    as_mesh_prov = base_cnt * a_base

    # 1. Capacity Check: If M_applied <= M_mesh, no additional steel is needed
    if M_app <= M_cap + 1e-4:
        _, full_lbl = format_additional_rebar_annotations(0, dia, base_cnt, base_dia)
        as_req_tot = as_required_per_m(M_app, d_cm, fcu, fy) if (d_cm and d_cm > 0) else (
            as_mesh_prov * (M_app / M_cap) if M_cap > 1e-6 else 0.0
        )
        return RebarCalcResult(
            0,
            "",
            {
                "n_add": 0,
                "text_label": "",
                "full_label": full_lbl,
                "delta_M": 0.0,
                "As_req_total": round(as_req_tot, 3),
                "As_mesh_prov": round(as_mesh_prov, 3),
                "As_add_req": 0.0,
                "As_add_prov": 0.0,
                "M_applied": round(M_app, 3),
                "M_mesh": round(M_cap, 3),
                "bar_diameter": dia,
                "base_bars_count": base_cnt,
                "base_bar_diameter": base_dia,
            },
        )

    # 2. Additional Rebar Calculation: ΔM = M_applied - M_mesh > 0
    delta_M = M_app - M_cap
    if d_cm is not None and d_cm > 0:
        as_req_total = as_required_per_m(M_app, d_cm, fcu, fy)
        as_cap_equiv = as_required_per_m(M_cap, d_cm, fcu, fy)
        as_add_req = max(0.0, as_req_total - max(as_mesh_prov, as_cap_equiv))
        if as_add_req <= 1e-4:
            as_add_req = max(0.0, as_required_per_m(delta_M, d_cm, fcu, fy))
    else:
        if M_cap > 1e-6:
            as_add_req = as_mesh_prov * (delta_M / M_cap)
            as_req_total = as_mesh_prov + as_add_req
        else:
            as_add_req = as_required_per_m(delta_M, 17.5, fcu, fy)
            as_req_total = as_mesh_prov + as_add_req

    # Practical integer rounding per meter (+1 bar/m for small ΔM, +2, +3, ... for larger ΔM)
    n_add = bars_per_meter(as_add_req, dia)
    as_add_prov = n_add * a_bar

    text_label, full_label = format_additional_rebar_annotations(n_add, dia, base_cnt, base_dia)

    return RebarCalcResult(
        n_add,
        text_label,
        {
            "n_add": n_add,
            "text_label": text_label,
            "full_label": full_label,
            "delta_M": round(delta_M, 3),
            "As_req_total": round(as_req_total, 3),
            "As_mesh_prov": round(as_mesh_prov, 3),
            "As_add_req": round(as_add_req, 3),
            "As_add_prov": round(as_add_prov, 3),
            "M_applied": round(M_app, 3),
            "M_mesh": round(M_cap, 3),
            "bar_diameter": dia,
            "base_bars_count": base_cnt,
            "base_bar_diameter": base_dia,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
#  2. DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ExtraRebarZone:
    """A single rectangular zone of extra slab reinforcement (top or bottom)."""
    zone_id: str                  # e.g. "BTM-X-P_1_1-CS" or "TOP-Y-P_2_1-INT"
    layer: str                    # "bottom" | "top"
    direction: str                # "X" | "Y"  (direction in which the bars RUN)
    strip_type: str               # "CS" (Column Strip) | "MS" (Middle Strip)
    location: str                 # "midspan" | "int_support" | "ext_support"
    panel_id: str                 # "P_i_j"
    bay_label: str                # e.g. "Y1–Y2 / X1–X2"

    # Geometry in plan (m)
    x_min: float = 0.0
    x_max: float = 0.0
    y_min: float = 0.0
    y_max: float = 0.0
    length_bar_m: float = 0.0     # bar cut length (along *direction*)
    width_dist_m: float = 0.0     # perpendicular distribution width B

    # Moment & steel demand/supply (per 1.0 m width)
    Mu_strip_ton_m: float = 0.0   # total strip moment (ton·m)
    Mu_per_m: float = 0.0         # Mu / width_dist_m  (ton·m/m)
    M_cap_per_m: float = 0.0      # Base mesh resisting moment capacity (ton·m/m)
    delta_M_per_m: float = 0.0    # Excess moment Mu_per_m - M_cap_per_m (ton·m/m)
    As_req_cm2_m: float = 0.0     # required steel per m
    As_mesh_cm2_m: float = 0.0    # provided by base mesh per m
    As_extra_req_cm2_m: float = 0.0  # deficit = max(0, As_req - As_mesh)

    # Chosen extra bars
    dia_mm: int = 12
    base_bars_count: int = 5
    base_dia_mm: int = 12
    n_bars_per_m: int = 0         # integer bars/m (1, 2, 3, …)
    n_bars_total: int = 0         # total bars across width_dist_m
    spacing_cm: float = 0.0       # 100 / n_bars_per_m
    As_extra_prov_cm2_m: float = 0.0
    As_total_prov_cm2_m: float = 0.0
    needed: bool = False          # True only if Mu_per_m > M_cap_per_m
    tag_label: str = ""           # Short annotation for plan drawing
    full_annotation: str = ""     # Full Arabic engineering annotation

    @property
    def cx(self) -> float:
        return 0.5 * (self.x_min + self.x_max)

    @property
    def cy(self) -> float:
        return 0.5 * (self.y_min + self.y_max)


@dataclass
class ColumnCapZone:
    """Concentrated top extra reinforcement over a single column (X & Y)."""
    col_id: str
    grid_label: str
    col_type: str                 # "Interior" | "Edge" | "Corner"
    cx: float
    cy: float

    # Cap footprint (m)
    x_min: float = 0.0
    x_max: float = 0.0
    y_min: float = 0.0
    y_max: float = 0.0
    Lx_cap_m: float = 0.0         # bar length in X
    Ly_cap_m: float = 0.0         # bar length in Y
    Bx_dist_m: float = 0.0        # distribution width for X-bars (measured along Y)
    By_dist_m: float = 0.0        # distribution width for Y-bars (measured along X)

    # Demand vs. mesh
    Mu_neg_col_ton_m: float = 0.0
    w_cs_m: float = 0.0
    Mu_neg_per_m: float = 0.0
    M_cap_per_m: float = 0.0
    delta_M_per_m: float = 0.0
    As_req_cm2_m: float = 0.0
    As_mesh_cm2_m: float = 0.0
    As_extra_req_cm2_m: float = 0.0

    dia_mm: int = 12
    base_bars_count: int = 5
    base_dia_mm: int = 12
    n_bars_per_m_x: int = 0
    n_bars_per_m_y: int = 0
    n_bars_total_x: int = 0
    n_bars_total_y: int = 0
    As_extra_prov_cm2_m: float = 0.0
    needed: bool = False
    tag_label_x: str = ""
    tag_label_y: str = ""
    full_annotation_x: str = ""
    full_annotation_y: str = ""


# ═══════════════════════════════════════════════════════════════════════════
#  3. ZONE DESIGNERS (Capacity Check + Additional Rebar Calculation)
# ═══════════════════════════════════════════════════════════════════════════

def _finish_zone(
    z: ExtraRebarZone,
    d_cm: float,
    fcu: float,
    fy: float,
    base_bars_count: Optional[int] = None,
    base_dia_mm: Optional[int] = None,
) -> ExtraRebarZone:
    """Compute capacity check, additional bars, and annotation tags for *z*."""
    if z.width_dist_m <= 1e-6:
        z.needed = False
        return z

    z.Mu_per_m = abs(z.Mu_strip_ton_m) / z.width_dist_m
    z.M_cap_per_m = mu_capacity_per_m(z.As_mesh_cm2_m, d_cm, fcu, fy)
    z.As_req_cm2_m = as_required_per_m(z.Mu_per_m, d_cm, fcu, fy)

    b_dia = int(base_dia_mm if base_dia_mm is not None else z.dia_mm)
    b_cnt = int(
        base_bars_count
        if base_bars_count is not None
        else max(5, round(z.As_mesh_cm2_m / max(bar_area(b_dia), 1e-6)))
    )
    z.base_bars_count = b_cnt
    z.base_dia_mm = b_dia

    calc_res = calculate_additional_reinforcement(
        M_applied=z.Mu_per_m,
        M_mesh=z.M_cap_per_m,
        bar_diameter=z.dia_mm,
        base_bars_count=b_cnt,
        d_cm=d_cm,
        fcu=fcu,
        fy=fy,
        base_bar_diameter=b_dia,
    )

    n_add, tag_lbl = calc_res
    z.delta_M_per_m = calc_res.delta_M
    z.As_extra_req_cm2_m = calc_res.As_add_req

    if n_add <= 0:
        z.needed = False
        z.n_bars_per_m = 0
        z.n_bars_total = 0
        z.spacing_cm = 0.0
        z.As_extra_prov_cm2_m = 0.0
        z.As_total_prov_cm2_m = z.As_mesh_cm2_m
        z.tag_label = ""
        z.full_annotation = calc_res.full_label
        return z

    a_bar = bar_area(z.dia_mm)
    z.n_bars_per_m = n_add
    z.spacing_cm = round(100.0 / n_add, 1)
    z.n_bars_total = max(1, int(math.ceil(n_add * z.width_dist_m)))
    z.As_extra_prov_cm2_m = round(n_add * a_bar, 2)
    z.As_total_prov_cm2_m = round(z.As_mesh_cm2_m + z.As_extra_prov_cm2_m, 2)
    z.needed = True
    z.tag_label = tag_lbl
    z.full_annotation = calc_res.full_label
    return z


def design_bottom_zone(
    *,
    panel_id: str,
    bay_label: str,
    direction: str,               # "X" or "Y"
    strip_type: str,              # "CS" or "MS"
    x_l: float,
    x_r: float,
    y_b: float,
    y_t: float,
    Mu_strip_ton_m: float,
    strip_width_m: float,
    As_mesh_btm_cm2_m: float,
    dia_extra_mm: int,
    d_cm: float,
    fcu: float,
    fy: float,
    base_bars_count: Optional[int] = None,
    base_dia_mm: Optional[int] = None,
) -> ExtraRebarZone:
    """
    Build & size a Bottom Mid-Span extra reinforcement zone (either X or Y,
    Column Strip or Middle Strip).
    """
    span_lx = x_r - x_l
    span_ly = y_t - y_b
    cx = 0.5 * (x_l + x_r)
    cy = 0.5 * (y_b + y_t)

    if direction.upper() == "X":
        L_bar = min(span_lx, round_up_5cm(0.70 * span_lx))
        B_dist = min(span_ly, round(strip_width_m, 2))
        x_min, x_max = cx - 0.5 * L_bar, cx + 0.5 * L_bar
        y_min, y_max = cy - 0.5 * B_dist, cy + 0.5 * B_dist
    else:
        L_bar = min(span_ly, round_up_5cm(0.70 * span_ly))
        B_dist = min(span_lx, round(strip_width_m, 2))
        x_min, x_max = cx - 0.5 * B_dist, cx + 0.5 * B_dist
        y_min, y_max = cy - 0.5 * L_bar, cy + 0.5 * L_bar

    z = ExtraRebarZone(
        zone_id=f"BTM-{direction.upper()}-{panel_id}-{strip_type}",
        layer="bottom",
        direction=direction.upper(),
        strip_type=strip_type,
        location="midspan",
        panel_id=panel_id,
        bay_label=bay_label,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        length_bar_m=L_bar,
        width_dist_m=B_dist,
        Mu_strip_ton_m=Mu_strip_ton_m,
        As_mesh_cm2_m=As_mesh_btm_cm2_m,
        dia_mm=int(dia_extra_mm),
    )
    return _finish_zone(z, d_cm, fcu, fy, base_bars_count=base_bars_count, base_dia_mm=base_dia_mm)


def design_top_field_zones(
    *,
    panel_id: str,
    bay_label: str,
    direction: str,               # "X" or "Y"
    x_l: float,
    x_r: float,
    y_b: float,
    y_t: float,
    ms_neg_int_ton_m: float,
    ms_neg_ext_ton_m: float,
    ms_width_m: float,
    is_ext_start: bool,
    is_ext_end: bool,
    As_mesh_top_cm2_m: float,
    dia_extra_mm: int,
    d_cm: float,
    fcu: float,
    fy: float,
    base_bars_count: Optional[int] = None,
    base_dia_mm: Optional[int] = None,
) -> List[ExtraRebarZone]:
    """
    Build Top Middle-Strip negative-moment extra zones over support lines.
    """
    span_lx = x_r - x_l
    span_ly = y_t - y_b
    cx = 0.5 * (x_l + x_r)
    cy = 0.5 * (y_b + y_t)
    zones: List[ExtraRebarZone] = []

    Mu_gov = max(abs(ms_neg_int_ton_m), abs(ms_neg_ext_ton_m))
    if Mu_gov <= 1e-6 or ms_width_m <= 1e-6:
        return zones

    if direction.upper() == "X":
        L_bar = min(span_lx, round_up_5cm(0.67 * span_lx))
        B_dist = min(span_ly, round(ms_width_m, 2))
        x_min, x_max = cx - 0.5 * L_bar, cx + 0.5 * L_bar
        y_min, y_max = cy - 0.5 * B_dist, cy + 0.5 * B_dist
    else:
        L_bar = min(span_ly, round_up_5cm(0.67 * span_ly))
        B_dist = min(span_lx, round(ms_width_m, 2))
        x_min, x_max = cx - 0.5 * B_dist, cx + 0.5 * B_dist
        y_min, y_max = cy - 0.5 * L_bar, cy + 0.5 * L_bar

    z = ExtraRebarZone(
        zone_id=f"TOP-{direction.upper()}-{panel_id}-MS",
        layer="top",
        direction=direction.upper(),
        strip_type="MS",
        location="int_support" if not (is_ext_start and is_ext_end) else "ext_support",
        panel_id=panel_id,
        bay_label=bay_label,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        length_bar_m=L_bar,
        width_dist_m=B_dist,
        Mu_strip_ton_m=Mu_gov,
        As_mesh_cm2_m=As_mesh_top_cm2_m,
        dia_mm=int(dia_extra_mm),
    )
    _finish_zone(z, d_cm, fcu, fy, base_bars_count=base_bars_count, base_dia_mm=base_dia_mm)
    if z.needed:
        zones.append(z)
    return zones


def design_cap(
    *args,
    **kwargs,
):
    """
    Supports both calling conventions:
      1) Positional 4-arg call used in `flat_slab.py`:
         `design_cap(As_extra_m, dia_mm, w_cs, L_extra_raw, base_bars_count=5, base_bar_dia=None)`
         -> returns dict `{"is_needed", "bars_per_m", "n_total", "L_bar", "As_extra_prov_m", "tag_label", "full_annotation"}`
      2) Keyword-based zone call:
         `design_cap(col_id=..., grid_label=..., ...)` -> returns `ColumnCapZone`.
    """
    if len(args) >= 4:
        As_extra_m = float(args[0] or 0.0)
        dia_mm = int(args[1] or 12)
        w_cs = float(args[2] or 1.0)
        L_raw = float(args[3] or 1.5)
        base_cnt = int(kwargs.get("base_bars_count", args[4] if len(args) > 4 else 5))
        base_dia = int(kwargs.get("base_bar_dia", args[5] if len(args) > 5 else dia_mm))

        L_bar = round_up_5cm(L_raw)
        bpm = bars_per_meter(As_extra_m, dia_mm)
        is_needed = bpm > 0
        n_tot = total_bars(bpm, w_cs) if is_needed else 0
        as_prov_m = round(bpm * bar_area(dia_mm), 2) if is_needed else 0.0
        tag_lbl, full_lbl = format_additional_rebar_annotations(bpm, dia_mm, base_cnt, base_dia)
        return {
            "is_needed": is_needed,
            "bars_per_m": bpm,
            "n_total": n_tot,
            "L_bar": L_bar,
            "As_extra_prov_m": as_prov_m,
            "tag_label": tag_lbl,
            "full_annotation": full_lbl,
        }

    col_id = kwargs["col_id"]
    grid_label = kwargs["grid_label"]
    col_type = kwargs["col_type"]
    cx = float(kwargs["cx"])
    cy = float(kwargs["cy"])
    adj_lx = float(kwargs["adj_lx"])
    adj_ly = float(kwargs["adj_ly"])
    x_slab_min = float(kwargs["x_slab_min"])
    x_slab_max = float(kwargs["x_slab_max"])
    y_slab_min = float(kwargs["y_slab_min"])
    y_slab_max = float(kwargs["y_slab_max"])
    Mu_neg_col_ton_m = float(kwargs["Mu_neg_col_ton_m"])
    w_cs_m = float(kwargs["w_cs_m"])
    As_mesh_top_cm2_m = float(kwargs["As_mesh_top_cm2_m"])
    dia_extra_mm = int(kwargs["dia_extra_mm"])
    d_cm = float(kwargs["d_cm"])
    fcu = float(kwargs["fcu"])
    fy = float(kwargs["fy"])
    base_bars_count = kwargs.get("base_bars_count")
    base_dia_mm = kwargs.get("base_dia_mm")

    ext_x = round_up_5cm(adj_lx / 3.0)
    ext_y = round_up_5cm(adj_ly / 3.0)

    x_min = max(x_slab_min, cx - ext_x)
    x_max = min(x_slab_max, cx + ext_x)
    y_min = max(y_slab_min, cy - ext_y)
    y_max = min(y_slab_max, cy + ext_y)

    Lx_cap = round(max(0.40, x_max - x_min), 2)
    Ly_cap = round(max(0.40, y_max - y_min), 2)
    Bx_dist = round(min(Ly_cap, max(0.50, w_cs_m)), 2)
    By_dist = round(min(Lx_cap, max(0.50, w_cs_m)), 2)

    w_eff = max(0.50, w_cs_m)
    Mu_per_m = abs(Mu_neg_col_ton_m) / w_eff
    M_cap_per_m = mu_capacity_per_m(As_mesh_top_cm2_m, d_cm, fcu, fy)
    As_req = as_required_per_m(Mu_per_m, d_cm, fcu, fy)

    b_dia = int(base_dia_mm if base_dia_mm is not None else dia_extra_mm)
    b_cnt = int(
        base_bars_count
        if base_bars_count is not None
        else max(5, round(As_mesh_top_cm2_m / max(bar_area(b_dia), 1e-6)))
    )

    calc_res = calculate_additional_reinforcement(
        M_applied=Mu_per_m,
        M_mesh=M_cap_per_m,
        bar_diameter=int(dia_extra_mm),
        base_bars_count=b_cnt,
        d_cm=d_cm,
        fcu=fcu,
        fy=fy,
        base_bar_diameter=b_dia,
    )
    n_add, tag_lbl = calc_res

    cap = ColumnCapZone(
        col_id=col_id,
        grid_label=grid_label,
        col_type=col_type,
        cx=cx,
        cy=cy,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        Lx_cap_m=Lx_cap,
        Ly_cap_m=Ly_cap,
        Bx_dist_m=Bx_dist,
        By_dist_m=By_dist,
        Mu_neg_col_ton_m=Mu_neg_col_ton_m,
        w_cs_m=w_eff,
        Mu_neg_per_m=round(Mu_per_m, 2),
        M_cap_per_m=round(M_cap_per_m, 2),
        delta_M_per_m=calc_res.delta_M,
        As_req_cm2_m=round(As_req, 2),
        As_mesh_cm2_m=round(As_mesh_top_cm2_m, 2),
        As_extra_req_cm2_m=round(calc_res.As_add_req, 2),
        dia_mm=int(dia_extra_mm),
        base_bars_count=b_cnt,
        base_dia_mm=b_dia,
    )

    if n_add <= 0:
        cap.needed = False
        cap.full_annotation_x = calc_res.full_label
        cap.full_annotation_y = calc_res.full_label
        return cap

    a_bar = bar_area(dia_extra_mm)
    cap.n_bars_per_m_x = n_add
    cap.n_bars_per_m_y = n_add
    cap.n_bars_total_x = max(1, int(math.ceil(n_add * Bx_dist)))
    cap.n_bars_total_y = max(1, int(math.ceil(n_add * By_dist)))
    cap.As_extra_prov_cm2_m = round(n_add * a_bar, 2)
    cap.needed = True
    cap.tag_label_x = tag_lbl
    cap.tag_label_y = tag_lbl
    cap.full_annotation_x = calc_res.full_label
    cap.full_annotation_y = calc_res.full_label
    return cap


# ═══════════════════════════════════════════════════════════════════════════
#  4. CALLOUT FORMATTER & CAD RENDERERS (Matplotlib Axes)
# ═══════════════════════════════════════════════════════════════════════════

def callout_text(
    z_or_bpm: Union[ExtraRebarZone, int],
    n_total: Optional[int] = None,
    dia_mm: Optional[int] = None,
    base_bars_count: Optional[int] = None,
    base_bar_dia: Optional[int] = None,
) -> str:
    """
    Standard engineering callout placed at the center of the distribution distance:
        `{n}Ø{dia} /m`
    Supports both:
      - `callout_text(z: ExtraRebarZone)`
      - `callout_text(bars_per_m, n_total, dia_mm, base_bars_count=5, base_bar_dia=12)`
    """
    if isinstance(z_or_bpm, ExtraRebarZone):
        z = z_or_bpm
        if z.tag_label and base_bars_count is None and base_bar_dia is None:
            line1 = z.tag_label
        else:
            b_cnt = int(base_bars_count if base_bars_count is not None else getattr(z, "base_bars_count", 5))
            b_dia = int(base_bar_dia if base_bar_dia is not None else getattr(z, "base_dia_mm", z.dia_mm))
            line1, _ = format_additional_rebar_annotations(z.n_bars_per_m, z.dia_mm, b_cnt, b_dia)
        return f"{line1}\n(L = {z.length_bar_m:.2f} m, B = {z.width_dist_m:.2f} m)"

    bpm = int(z_or_bpm or 0)
    dia = int(dia_mm or 12)
    b_cnt = int(base_bars_count if base_bars_count is not None else 5)
    b_dia = int(base_bar_dia if base_bar_dia is not None else dia)
    line1, _ = format_additional_rebar_annotations(bpm, dia, b_cnt, b_dia)
    if n_total is not None and n_total > 0:
        return f"{line1} [Total: {int(n_total)}Ø{dia}]"
    return line1


def draw_extra_zone(
    ax,
    z: ExtraRebarZone,
    *,
    color_main: str = "#c2410c",
    color_fill: str = "#fed7aa",
    hatch: str = "//",
    zorder_base: int = 5,
    font_size: float = 9.5,
) -> None:
    """
    Render a single `ExtraRebarZone` on a Matplotlib plan `ax`:
      1. Semi-transparent hatched rectangle (`length × distribution width`)
         showing the exact moment concentration / distribution zone.
      2. One bold representative rebar line with 45° end hooks/ticks along
         `z.direction`.
      3. One perpendicular distribution-width line with `<->` arrows.
      4. Consolidated callout badge centered at `(z.cx, z.cy)` (the exact middle
         of the distribution distance).
    """
    if not z.needed or z.n_bars_per_m <= 0:
        return

    w_rect = z.x_max - z.x_min
    h_rect = z.y_max - z.y_min
    if w_rect <= 0.05 or h_rect <= 0.05:
        return

    # 1. Hatched zone patch
    zone_patch = patches.Rectangle(
        (z.x_min, z.y_min),
        w_rect,
        h_rect,
        linewidth=1.5,
        edgecolor=color_main,
        facecolor=color_fill,
        alpha=0.26,
        linestyle="--",
        hatch=hatch,
        zorder=zorder_base,
    )
    ax.add_patch(zone_patch)

    cx, cy = z.cx, z.cy
    tick = min(0.16, 0.08 * min(w_rect, h_rect))

    if z.direction == "X":
        bar_y = cy + 0.14 * h_rect
        ax.plot(
            [z.x_min, z.x_max],
            [bar_y, bar_y],
            color=color_main,
            linewidth=2.8,
            solid_capstyle="round",
            zorder=zorder_base + 2,
        )
        ax.plot([z.x_min, z.x_min], [bar_y - tick, bar_y + tick], color=color_main, lw=2.2, zorder=zorder_base + 2)
        ax.plot([z.x_max, z.x_max], [bar_y - tick, bar_y + tick], color=color_main, lw=2.2, zorder=zorder_base + 2)

        dist_x = cx - 0.28 * w_rect
        ax.annotate(
            "",
            xy=(dist_x, z.y_max),
            xytext=(dist_x, z.y_min),
            arrowprops=dict(arrowstyle="<->", color=color_main, lw=1.4, linestyle=":"),
            zorder=zorder_base + 1,
        )
    else:
        bar_x = cx + 0.14 * w_rect
        ax.plot(
            [bar_x, bar_x],
            [z.y_min, z.y_max],
            color=color_main,
            linewidth=2.8,
            solid_capstyle="round",
            zorder=zorder_base + 2,
        )
        ax.plot([bar_x - tick, bar_x + tick], [z.y_min, z.y_min], color=color_main, lw=2.2, zorder=zorder_base + 2)
        ax.plot([bar_x - tick, bar_x + tick], [z.y_max, z.y_max], color=color_main, lw=2.2, zorder=zorder_base + 2)

        dist_y = cy - 0.28 * h_rect
        ax.annotate(
            "",
            xy=(z.x_max, dist_y),
            xytext=(z.x_min, dist_y),
            arrowprops=dict(arrowstyle="<->", color=color_main, lw=1.4, linestyle=":"),
            zorder=zorder_base + 1,
        )

    # Callout badge placed at the exact middle of the distribution distance (cx, cy)
    ax.text(
        cx,
        cy,
        callout_text(z),
        color="#0f172a",
        fontsize=font_size,
        weight="bold",
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.28",
            facecolor="#ffffff",
            edgecolor=color_main,
            lw=1.6,
            alpha=0.95,
        ),
        zorder=zorder_base + 3,
    )


def draw_cap_zone(
    ax,
    cap: ColumnCapZone,
    *,
    color_main: str = "#b91c1c",
    color_fill: str = "#fecaca",
    zorder_base: int = 5,
    font_size: float = 9.0,
) -> None:
    """
    Render a `ColumnCapZone` on a Matplotlib plan `ax` with hatched box,
    orthogonal representative bars (X & Y), and a single callout tag at the
    center of the distribution distance.
    """
    if not cap.needed or cap.n_bars_per_m_x <= 0:
        return

    w_rect = cap.x_max - cap.x_min
    h_rect = cap.y_max - cap.y_min
    if w_rect <= 0.05 or h_rect <= 0.05:
        return

    patch = patches.Rectangle(
        (cap.x_min, cap.y_min),
        w_rect,
        h_rect,
        linewidth=1.8,
        edgecolor=color_main,
        facecolor=color_fill,
        alpha=0.28,
        linestyle="--",
        hatch="xx",
        zorder=zorder_base,
    )
    ax.add_patch(patch)

    ax.plot([cap.x_min, cap.x_max], [cap.cy, cap.cy], color=color_main, lw=2.4, zorder=zorder_base + 1)
    ax.plot([cap.cx, cap.cx], [cap.y_min, cap.y_max], color="#1d4ed8", lw=2.4, zorder=zorder_base + 1)

    tag_str = cap.tag_label_x or format_additional_rebar_annotations(
        cap.n_bars_per_m_x, cap.dia_mm, cap.base_bars_count, cap.base_dia_mm
    )[0]
    label = (
        f"{cap.col_id}: {tag_str}\n"
        f"(Lx={cap.Lx_cap_m:.2f}×Ly={cap.Ly_cap_m:.2f} m)"
    )
    ax.text(
        cap.cx,
        cap.cy,
        label,
        color="#7f1d1d",
        fontsize=font_size,
        weight="bold",
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.26",
            facecolor="#fffbeb",
            edgecolor=color_main,
            lw=1.5,
            alpha=0.96,
        ),
        zorder=zorder_base + 3,
    )


@dataclass
class PanelRebarDetail:
    """
    كائن برمجي مستقل لكل باكية إنشائية (Independent Structural Bay / Panel Object P_i_j)
    محددة بـ 4 أعمدة ركنية ومحاور X و Y، يجمع تفاصيل الحديد الإضافي السفلي بمنتصف الباكية
    والحديد الإضافي العلوي عند رؤوس الأعمدة المحيطة بها.
    """
    panel_id: str
    bay_label: str
    axes_bounds: Dict
    corner_columns: List[str]
    bottom_rebar_x: Dict
    bottom_rebar_y: Dict
    top_column_heads: List[Dict]

    def to_dict(self) -> Dict:
        return {
            "panel_id": self.panel_id,
            "bay_label": self.bay_label,
            "axes_bounds": dict(self.axes_bounds),
            "corner_columns": list(self.corner_columns),
            "bottom_rebar_x": dict(self.bottom_rebar_x),
            "bottom_rebar_y": dict(self.bottom_rebar_y),
            "top_column_heads": [dict(c) for c in self.top_column_heads],
        }

    def __getitem__(self, key: str):
        return self.to_dict()[key]

    def get(self, key: str, default=None):
        return self.to_dict().get(key, default)


def build_bay_rebar_detail_object(
    *,
    panel_id: str,
    bay_label: str,
    corner_columns: List[str],
    axes_bounds: Optional[Dict] = None,
    bottom_rebar_x: Optional[Dict] = None,
    bottom_rebar_y: Optional[Dict] = None,
    btm_rebar_x: Optional[Dict] = None,
    btm_rebar_y: Optional[Dict] = None,
    top_column_heads: Optional[List[Dict]] = None,
    grid_x_range: Optional[Tuple[str, str]] = None,
    grid_y_range: Optional[Tuple[str, str]] = None,
    x0: float = 0.0,
    x1: float = 0.0,
    y0: float = 0.0,
    y1: float = 0.0,
    Lx: float = 0.0,
    Ly: float = 0.0,
    Ln_x: float = 0.0,
    Ln_y: float = 0.0,
    M_pos_x_m: float = 0.0,
    M_pos_y_m: float = 0.0,
    M_cap_btm_m: float = 0.0,
) -> PanelRebarDetail:
    """Create a structured `PanelRebarDetail` object/dictionary for a single bay $P_{i,j}$."""
    bounds = dict(axes_bounds) if axes_bounds else {
        "grid_x": list(grid_x_range) if grid_x_range else [],
        "grid_y": list(grid_y_range) if grid_y_range else [],
        "x0": x0,
        "x1": x1,
        "y0": y0,
        "y1": y1,
        "Lx": Lx,
        "Ly": Ly,
        "Ln_x": Ln_x,
        "Ln_y": Ln_y,
        "M_pos_x_m": M_pos_x_m,
        "M_pos_y_m": M_pos_y_m,
        "M_cap_btm_m": M_cap_btm_m,
    }
    bx = dict(bottom_rebar_x if bottom_rebar_x is not None else (btm_rebar_x or {}))
    by = dict(bottom_rebar_y if bottom_rebar_y is not None else (btm_rebar_y or {}))
    return PanelRebarDetail(
        panel_id=panel_id,
        bay_label=bay_label,
        axes_bounds=bounds,
        corner_columns=list(corner_columns or []),
        bottom_rebar_x=bx,
        bottom_rebar_y=by,
        top_column_heads=list(top_column_heads or []),
    )


def cluster_and_merge_bays(bays: List[Dict], tol: float = 0.15) -> List[Dict]:
    """
    Preserves each structural bay P_{i,j} as an independent entity without merging
    across adjacent bays, ensuring bottom/top additional reinforcement is detailed
    and drawn per individual bay.
    """
    if not bays:
        return []

    independent_bays: List[Dict] = []
    for b in bays:
        if not isinstance(b, dict):
            continue
        bpm = int(b.get("bars_per_m", 0) or 0)
        n_ext = int(b.get("n_extra", 0) or 0)
        if bpm <= 0 and n_ext <= 0:
            continue
        item = dict(b)
        raw_w = float(item.get("W_bay", item.get("dist_width_m", 4.0)) or 4.0)
        # Middle-strip (الثلث الأوسط / شريحة الوسط) distribution width strictly inside the bay
        item["B_zone"] = round(float(item.get("B_zone", raw_w * 0.45) or (raw_w * 0.45)), 2)
        item["dist_width_m"] = item["B_zone"]
        item["is_merged"] = False
        independent_bays.append(item)

    return independent_bays

