"""
modules/extra_steel_zones.py
----------------------------
Zone Enveloping & Optimization engine for the *additional* reinforcement of the
Flat-Slab module (top column caps, bottom extra M11/M22, top field extra).

Philosophy
----------
* Every additional-steel item is designed as ONE uniform rectangular "zone":
      Bars_per_meter = max(ceil(As_extra_per_m / A_bar), 3)
      Total_Bars     = ceil(Bars_per_meter * Zone_Width)
      L_bar          = roundup(Zone_Length + 2 * Ld)      (25 cm / 50 cm steps)
* Demand zones are detected by comparing the applied moment profile against the
  resisting moment of the base mesh; close zones (gap < max(1.0 m, Ld)) are
  merged, and the governing (maximum) moment of the merged zone is enveloped
  over the whole zone (no density change inside a zone).

Units: m, cm, kg/cm2, ton.m (same as flat_slab.py).  Pure python + numpy only.
"""

import math
import numpy as np

MIN_BARS_PER_M = 3          # minimum executable density of additional bars
GAP_MERGE_M = 1.0           # demand zones closer than this are merged
MIN_ZONE_LEN_M = 0.25       # zones shorter than this are ignored
DELTA_AS_TOL = 0.05         # cm2/m  (same tolerance used by the legacy code)

# Hogging (negative) support moment ratios of the DDM, as a fraction of Mo
DDM_NEG_INTERIOR = 0.65
DDM_NEG_EXTERIOR = 0.00


# ─────────────────────────────────────────────────────────────────────────────
#  Basic helpers
# ─────────────────────────────────────────────────────────────────────────────
def bar_area_cm2(dia_mm):
    return math.pi * (dia_mm / 10.0) ** 2 / 4.0


def development_length(dia_mm, fcu, fy, top_bar=False):
    """
    Approximate ECP 203 development length Ld (m).
        fbu = 1.5 * 0.3 * sqrt(fcu / 1.5)   (deformed bars, MPa)
        Ld  = phi * (fy / 1.15) / (4 * fbu)  (x1.3 for top bars), min 0.30 m
    The result is rounded up to the next 5 cm.
    """
    fcu_mpa = max(fcu, 1.0) / 10.0
    fy_mpa = max(fy, 1.0) / 10.0
    fbu = 1.5 * 0.3 * math.sqrt(fcu_mpa / 1.5)
    ld_m = (dia_mm / 1000.0) * (fy_mpa / 1.15) / (4.0 * fbu)
    if top_bar:
        ld_m *= 1.3
    ld_m = max(0.30, ld_m)
    return math.ceil(round(ld_m / 0.05, 6)) * 0.05


def round_up_length(length_m, step=None):
    """Round a bar length up to a multiple of 25 cm (L<6 m) or 50 cm (L>=6 m)."""
    if step is None:
        step = 0.25 if length_m < 6.0 else 0.50
    return round(math.ceil(round(length_m / step, 6)) * step, 2)


def bars_per_meter(as_per_m_cm2, dia_mm, min_bpm=MIN_BARS_PER_M):
    a_bar = bar_area_cm2(dia_mm)
    return max(int(math.ceil(round(as_per_m_cm2 / a_bar, 6))), int(min_bpm))


def total_bars(bpm, width_m):
    return int(math.ceil(round(bpm * width_m, 6)))


def mu_capacity_per_m(as_cm2_per_m, d_cm, fcu, fy):
    """Moment capacity (t.m per metre width) of a mesh with As cm2/m."""
    as_ = max(as_cm2_per_m, 0.001)
    a = (as_ * fy) / (0.85 * fcu * 100.0)
    return 0.9 * fy * as_ * max(0.1, d_cm - a / 2.0) / 100_000.0


def as_required_per_m(m_ton_m_per_m, d_cm, fcu, fy):
    """Required As (cm2/m) for a design moment per metre width (no As_min)."""
    m = max(m_ton_m_per_m, 0.001) * 100_000.0
    a_est = 0.1 * d_cm
    as_est = m / (0.9 * fy * max(0.1, d_cm - a_est / 2.0))
    a_ref = (as_est * fy) / (0.85 * fcu * 100.0)
    return m / (0.9 * fy * max(0.1, d_cm - a_ref / 2.0))


# ─────────────────────────────────────────────────────────────────────────────
#  Moment profile & zone detection
# ─────────────────────────────────────────────────────────────────────────────
def ddm_span_profile(Mo, mneg_l, mneg_r, Ln, m_pos_design=None, n=241):
    """
    Moment profile along the clear span (s = 0..Ln, measured from the left face).
    Returns (s, pos, neg): sagging magnitude and hogging magnitude arrays.
    The sagging part is rescaled so its peak equals the DDM design M+ value.
    """
    s = np.linspace(0.0, max(Ln, 1e-6), n)
    t = s / max(Ln, 1e-6)
    raw = 4.0 * Mo * t * (1.0 - t) - (mneg_l * (1.0 - t) + mneg_r * t)
    pos = np.maximum(raw, 0.0)
    neg = np.maximum(-raw, 0.0)
    if m_pos_design is not None and pos.max() > 1e-9:
        pos = pos * (m_pos_design / pos.max())
    return s, pos, neg


def detect_zones(s, m_applied, m_res):
    """Intervals [s0, s1, m_max] where m_applied > m_res (linear crossings)."""
    zones, start, mmax = [], None, 0.0
    for k in range(len(s)):
        over = m_applied[k] > m_res
        if over and start is None:
            if k == 0:
                start = s[0]
            else:
                a, b = m_applied[k - 1], m_applied[k]
                f = (m_res - a) / (b - a) if b != a else 0.0
                start = s[k - 1] + f * (s[k] - s[k - 1])
            mmax = m_applied[k]
        elif over:
            mmax = max(mmax, m_applied[k])
        elif (not over) and start is not None:
            a, b = m_applied[k - 1], m_applied[k]
            f = (a - m_res) / (a - b) if a != b else 0.0
            end = s[k - 1] + f * (s[k] - s[k - 1])
            zones.append([start, end, mmax])
            start = None
    if start is not None:
        zones.append([start, s[-1], mmax])
    return zones


def merge_zones(zones, gap_tol):
    """Merge zones whose gap is smaller than gap_tol; keep the governing M_max."""
    if not zones:
        return []
    zs = sorted([list(z) for z in zones], key=lambda z: z[0])
    out = [zs[0]]
    for z in zs[1:]:
        if z[0] - out[-1][1] < gap_tol:
            out[-1][1] = max(out[-1][1], z[1])
            out[-1][2] = max(out[-1][2], z[2])
        else:
            out.append(z)
    return out


def subtract_intervals(seg, blockers):
    """Remove blocker intervals from seg=(a,b); returns the remaining segments."""
    segs = [tuple(seg)]
    for c0, c1 in blockers:
        new = []
        for p, q in segs:
            if c1 <= p or c0 >= q:
                new.append((p, q))
                continue
            if c0 > p:
                new.append((p, c0))
            if c1 < q:
                new.append((c1, q))
        segs = new
    return segs


# ─────────────────────────────────────────────────────────────────────────────
#  Zone design (shared by bottom / top-field)
# ─────────────────────────────────────────────────────────────────────────────
def _finish_zone(u0, u1, m_max, as_mesh_m, dia_mm, d_cm, fcu, fy, zone_width, top_bar):
    as_req = as_required_per_m(m_max, d_cm, fcu, fy)
    delta = max(0.0, as_req - as_mesh_m)
    if delta <= DELTA_AS_TOL:
        return None
    bpm = bars_per_meter(delta, dia_mm)
    tot = total_bars(bpm, zone_width)
    ld = development_length(dia_mm, fcu, fy, top_bar=top_bar)
    zone_len = max(u1 - u0, 0.0)
    l_bar = round_up_length(zone_len + 2.0 * ld)
    a_bar = bar_area_cm2(dia_mm)
    res = dict(
        u0=u0, u1=u1, zone_len=zone_len, zone_width=zone_width,
        M_max=m_max, As_req_m=as_req, As_mesh_m=as_mesh_m,
        delta_As_calc=delta, bars_per_m=bpm, n_total=tot, Ld=ld,
        L_bar=l_bar, As_extra_prov_m=bpm * a_bar,
        As_total_prov_m=as_mesh_m + bpm * a_bar,
        u_bar0=0.5 * (u0 + u1) - 0.5 * l_bar,
        u_bar1=0.5 * (u0 + u1) + 0.5 * l_bar,
    )
    return {k: (int(v) if k in ("bars_per_m", "n_total") else float(v)) for k, v in res.items()}


def design_bottom_zone(Mo, Ln, left_exterior, right_exterior, m_pos_design,
                       mu_pos_per_m, as_mesh_m, dia_mm, d_cm, fcu, fy,
                       zone_width, u_fl=0.0):
    """
    Unified bottom extra zone of one bay in one direction (M11 or M22).
    u-coordinates are measured from the left AXIS of the bay.
    Returns a zone dict or None.
    """
    if m_pos_design <= 0 or mu_pos_per_m <= 0:
        return None
    ml = 0.0 if left_exterior else DDM_NEG_INTERIOR * Mo
    mr = 0.0 if right_exterior else DDM_NEG_INTERIOR * Mo
    s, pos, _ = ddm_span_profile(Mo, ml, mr, Ln, m_pos_design)
    app = pos * (mu_pos_per_m / m_pos_design)
    cap = mu_capacity_per_m(as_mesh_m, d_cm, fcu, fy)
    ld = development_length(dia_mm, fcu, fy)
    zones = merge_zones(detect_zones(s, app, cap), max(GAP_MERGE_M, ld))
    zones = [z for z in zones if (z[1] - z[0]) >= MIN_ZONE_LEN_M]
    if not zones:
        return None
    z0 = min(z[0] for z in zones)
    z1 = max(z[1] for z in zones)
    mmax = max(z[2] for z in zones)
    return _finish_zone(u_fl + z0, u_fl + z1, mmax, as_mesh_m, dia_mm, d_cm,
                        fcu, fy, zone_width, top_bar=False)


def design_top_field_zones(Mo, Ln, left_exterior, right_exterior, peak_per_m,
                           as_mesh_m, dia_mm, d_cm, fcu, fy, zone_width,
                           u_fl, span_len, cap_len_left=0.0, cap_len_right=0.0):
    """
    Unified top extra zones in the field (between columns, OUTSIDE the cap zones).
    Returns a list of zone dicts (0, 1 or 2 zones).
    """
    if peak_per_m <= 0:
        return []
    ml = 0.0 if left_exterior else DDM_NEG_INTERIOR * Mo
    mr = 0.0 if right_exterior else DDM_NEG_INTERIOR * Mo
    s, _, neg = ddm_span_profile(Mo, ml, mr, Ln, None)
    if neg.max() <= 1e-9:
        return []
    app = neg / neg.max() * peak_per_m
    cap = mu_capacity_per_m(as_mesh_m, d_cm, fcu, fy)
    ld = development_length(dia_mm, fcu, fy, top_bar=True)
    zones = merge_zones(detect_zones(s, app, cap), max(GAP_MERGE_M, ld))

    blockers = []
    if cap_len_left > 0:
        blockers.append((-cap_len_left / 2.0, cap_len_left / 2.0))
    if cap_len_right > 0:
        blockers.append((span_len - cap_len_right / 2.0, span_len + cap_len_right / 2.0))

    out = []
    for z0, z1, _m in zones:
        for a, b in subtract_intervals((u_fl + z0, u_fl + z1), blockers):
            if (b - a) < MIN_ZONE_LEN_M:
                continue
            probe = np.linspace(a, b, 25) - u_fl
            m_here = float(np.max(np.interp(probe, s, app)))
            zd = _finish_zone(a, b, m_here, as_mesh_m, dia_mm, d_cm, fcu, fy,
                              zone_width, top_bar=True)
            if zd:
                out.append(zd)
    return out


def design_cap(as_extra_m, dia_mm, cap_width, l_extra_raw):
    """Column cap: density per metre over the distribution width, min 3 bars/m'."""
    if as_extra_m <= DELTA_AS_TOL:
        return dict(is_needed=False, bars_per_m=0, n_total=0,
                    L_bar=round_up_length(l_extra_raw), As_extra_prov_m=0.0)
    bpm = bars_per_meter(as_extra_m, dia_mm)
    return dict(is_needed=True, bars_per_m=bpm, n_total=total_bars(bpm, cap_width),
                L_bar=round_up_length(l_extra_raw),
                As_extra_prov_m=bpm * bar_area_cm2(dia_mm))


def callout_text(bpm, total, dia_mm):
    return f"{bpm} Φ {dia_mm} / m' (Total: {total} Φ {dia_mm})"


# ─────────────────────────────────────────────────────────────────────────────
#  Multi-Bay Contour Cluster Merging
# ─────────────────────────────────────────────────────────────────────────────
def cluster_and_merge_bays(bays, gap_tol=1.0):
    """
    Groups adjacent/overlapping demand bays into unified single-zone bounding boxes.
    Applies the governing principle:
      - Envelopes maximum bars/m' among all merged bays.
      - Envelopes total length and width.
      - Calculates continuous cutting bar length rounded to 25/50 cm steps.
    """
    if not bays:
        return []

    # Filter only bays that have demand
    active = [b for b in bays if isinstance(b, dict) and b.get("is_needed", False) and b.get("n_extra", 0) > 0]
    if not active:
        return []

    # Build bounding boxes for each bay if not present
    items = []
    for b in active:
        b_copy = dict(b)
        cx = b.get("cx", 0.0)
        cy = b.get("cy", 0.0)
        span_x = b.get("span_len", 4.0) if b.get("dir", "X") == "X" else b.get("W_bay", 4.0)
        span_y = b.get("W_bay", 4.0) if b.get("dir", "X") == "X" else b.get("span_len", 4.0)
        x0 = b.get("x0", cx - span_x / 2.0)
        x1 = b.get("x1", cx + span_x / 2.0)
        y0 = b.get("y0", cy - span_y / 2.0)
        y1 = b.get("y1", cy + span_y / 2.0)
        b_copy["_x0"] = x0
        b_copy["_x1"] = x1
        b_copy["_y0"] = y0
        b_copy["_y1"] = y1
        items.append(b_copy)

    # Disjoint-set / Connected-component clustering
    n = len(items)
    parent = list(range(n))

    def find(p):
        while p != parent[p]:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    def union(p, q):
        root_p = find(p)
        root_q = find(q)
        if root_p != root_q:
            parent[root_q] = root_p

    for a in range(n):
        for b in range(a + 1, n):
            dir_a = items[a].get("dir", "X").upper()
            dir_b = items[b].get("dir", "X").upper()
            if dir_a != dir_b:
                continue

            # In the bar span direction, bays must be continuous or close within gap_tol.
            # In the transverse distribution direction, they must truly share the same strip (meaningful transverse overlap).
            if dir_a == "X":
                # Continuous along X
                close_along_bar = not (items[a]["_x1"] + gap_tol < items[b]["_x0"] or items[b]["_x1"] + gap_tol < items[a]["_x0"])
                # Shared strip along Y (transverse overlap of at least 0.20 m)
                y_overlap = min(items[a]["_y1"], items[b]["_y1"]) - max(items[a]["_y0"], items[b]["_y0"])
                if close_along_bar and (y_overlap > 0.20 or (abs(items[a]["_y0"] - items[b]["_y0"]) < gap_tol and abs(items[a]["_y1"] - items[b]["_y1"]) < gap_tol)):
                    union(a, b)
            else:
                # Continuous along Y
                close_along_bar = not (items[a]["_y1"] + gap_tol < items[b]["_y0"] or items[b]["_y1"] + gap_tol < items[a]["_y0"])
                # Shared strip along X (transverse overlap of at least 0.20 m)
                x_overlap = min(items[a]["_x1"], items[b]["_x1"]) - max(items[a]["_x0"], items[b]["_x0"])
                if close_along_bar and (x_overlap > 0.20 or (abs(items[a]["_x0"] - items[b]["_x0"]) < gap_tol and abs(items[a]["_x1"] - items[b]["_x1"]) < gap_tol)):
                    union(a, b)

    clusters = {}
    for idx in range(n):
        root = find(idx)
        clusters.setdefault(root, []).append(items[idx])

    merged_zones = []
    for group in clusters.values():
        dir_b = group[0].get("dir", "X").upper()
        dia = group[0].get("dia_extra", 12)
        ld = max(b.get("Ld", 0.60) for b in group)

        # Enveloping bounding box
        x_min = min(b["_x0"] for b in group)
        x_max = max(b["_x1"] for b in group)
        y_min = min(b["_y0"] for b in group)
        y_max = max(b["_y1"] for b in group)

        # Governing maximum bars/m'
        gov_bpm = max(b.get("bars_per_m", 3) for b in group)
        gov_bpm = max(gov_bpm, MIN_BARS_PER_M)

        if dir_b == "X":
            eff_len = x_max - x_min
            eff_width = y_max - y_min
            L_ext = round_up_length(0.70 * eff_len + 2.0 * ld) if len(group) == 1 else round_up_length(eff_len + 2.0 * ld)
            n_tot = total_bars(gov_bpm, eff_width)
        else:
            eff_len = y_max - y_min
            eff_width = x_max - x_min
            L_ext = round_up_length(0.70 * eff_len + 2.0 * ld) if len(group) == 1 else round_up_length(eff_len + 2.0 * ld)
            n_tot = total_bars(gov_bpm, eff_width)

        cx = (x_min + x_max) / 2.0
        cy = (y_min + y_max) / 2.0

        pids = [b.get("panel_id", "") for b in group]
        label = f"Unified Zone ({len(group)} Bays: {', '.join(pids)})" if len(group) > 1 else group[0].get("bay_label", "Bay Zone")

        merged_item = {
            "panel_id": "+".join(pids),
            "bay_label": label,
            "dir": dir_b,
            "cx": cx,
            "cy": cy,
            "x0": x_min,
            "x1": x_max,
            "y0": y_min,
            "y1": y_max,
            "span_len": eff_len,
            "W_bay": eff_width,
            "bars_per_m": gov_bpm,
            "n_extra": n_tot,
            "dia_extra": dia,
            "L_extra": L_ext,
            "Ld": ld,
            "is_needed": True,
            "bays_count": len(group),
            "callout": (
                f"Unified Zone: {gov_bpm} Φ {dia} / m'\n"
                f"(Total: {n_tot} Φ {dia}, L = {L_ext:.2f} m | Ld = {ld:.2f} m)"
            ),
        }
        merged_zones.append(merged_item)

    return merged_zones


# ─────────────────────────────────────────────────────────────────────────────
#  Drawing helpers (matplotlib axes passed in by flat_slab.py)
# ─────────────────────────────────────────────────────────────────────────────
# (line colour, face colour, text colour)  — X vs Y and Bottom vs Top/Caps
ZONE_STYLE = {
    "btm_X": ("#ea580c", "#ffedd5", "#9a3412"),
    "btm_Y": ("#0d9488", "#ccfbf1", "#115e59"),
    "top_X": ("#2563eb", "#dbeafe", "#1e40af"),
    "top_Y": ("#7c3aed", "#ede9fe", "#5b21b6"),
    "cap":   ("#dc2626", "#fee2e2", "#991b1b"),
}


def _tag(ax, text, xy, xytext, color, fontsize, rotation=0):
    ax.annotate(
        text, xy=xy, xytext=xytext, textcoords="data",
        ha="center", va="center", fontsize=fontsize, fontweight="bold",
        color=color, rotation=rotation, zorder=9,
        bbox=dict(boxstyle="round,pad=0.28", facecolor="#ffffff", edgecolor=color, lw=1.6),
        arrowprops=dict(arrowstyle="-", color=color, lw=1.3, shrinkA=0, shrinkB=0),
    )


def draw_extra_zone(ax, item, style_key, prefix, stagger=0, fontsize=11.0, patches_mod=None):
    """
    Draw one unified additional-steel zone:
      * transparent hatched bounding box (the enveloped zone, length x width)
      * bar line with Ld extension guide lines (dashed) beyond the zone
      * leader-line callout: '<prefix>: n Φd/m' (Total: N Φd, L = x.xx m)'
    `item` needs: dir, zone_x0/x1/y0/y1, bar_a0/bar_a1, bars_per_m, n_extra,
    dia_extra, L_extra, Ld.  Returns True when drawn.
    """
    if "zone_x0" not in item:
        return False
    import matplotlib.patches as patches
    line_c, face_c, text_c = ZONE_STYLE[style_key]
    x0, x1, y0, y1 = item["zone_x0"], item["zone_x1"], item["zone_y0"], item["zone_y1"]
    w, h = x1 - x0, y1 - y0
    ax.add_patch(patches.Rectangle((x0, y0), w, h, lw=2.0, edgecolor=line_c,
                                   facecolor=face_c, alpha=0.55, linestyle="--",
                                   hatch="///", zorder=3))
    d = item.get("dir", "X").upper()
    a0, a1 = item["bar_a0"], item["bar_a1"]
    ld = item.get("Ld", 0.0)
    if d == "X":
        yc = 0.5 * (y0 + y1)
        z0, z1 = x0, x1
        ax.plot([a0, a1], [yc, yc], color=line_c, lw=4.0, solid_capstyle="round", zorder=6)
        for xe in (a0, a1):
            ax.plot([xe, xe], [yc - 0.2, yc + 0.2], color=line_c, lw=3.0, zorder=6)
        # Ld guide lines outside the moment zone
        ax.plot([a0, z0], [yc + 0.28, yc + 0.28], color=line_c, lw=1.4, ls=":", zorder=6)
        ax.plot([z1, a1], [yc + 0.28, yc + 0.28], color=line_c, lw=1.4, ls=":", zorder=6)
        anchor = (0.5 * (x0 + x1), yc)
        off = (0.28 * h + 0.55) * (1 if stagger % 2 == 0 else -1)
        tpos = (0.5 * (x0 + x1), yc + off)
        rot = 0
    else:
        xc = 0.5 * (x0 + x1)
        z0, z1 = y0, y1
        ax.plot([xc, xc], [a0, a1], color=line_c, lw=4.0, solid_capstyle="round", zorder=6)
        for ye in (a0, a1):
            ax.plot([xc - 0.2, xc + 0.2], [ye, ye], color=line_c, lw=3.0, zorder=6)
        ax.plot([xc + 0.28, xc + 0.28], [a0, z0], color=line_c, lw=1.4, ls=":", zorder=6)
        ax.plot([xc + 0.28, xc + 0.28], [z1, a1], color=line_c, lw=1.4, ls=":", zorder=6)
        anchor = (xc, 0.5 * (y0 + y1))
        off = (0.28 * w + 0.55) * (1 if stagger % 2 == 0 else -1)
        tpos = (xc + off, 0.5 * (y0 + y1))
        rot = 90
    dia = item.get("dia_extra", 12)
    txt = (f"{prefix}: {item['bars_per_m']} Φ{dia}/m' "
           f"(Total: {item['n_extra']} Φ{dia}, L = {item['L_extra']:.2f} m)\n"
           f"Zone {item['zone_len']:.2f} × {item['zone_width']:.2f} m  |  Ld = {ld:.2f} m")
    _tag(ax, txt, anchor, tpos, text_c, fontsize, rotation=rot)
    return True


def draw_cap_zone(ax, c_info, cx, cy, col_d_m, label_above=True, fontsize=11.0):
    """Column cap zone: length L along X x distribution width, with leader callout."""
    import matplotlib.patches as patches
    line_c, face_c, text_c = ZONE_STYLE["cap"]
    L = c_info.get("L_extra", 3.0)
    wcap = c_info.get("cap_width", 1.5)
    ax.add_patch(patches.Rectangle((cx - L / 2.0, cy - wcap / 2.0), L, wcap, lw=2.0,
                                   edgecolor=line_c, facecolor=face_c, alpha=0.55,
                                   linestyle="--", hatch="\\\\\\", zorder=4))
    bar_y = cy + col_d_m / 2.0 + 0.15
    ax.plot([cx - L / 2.0, cx + L / 2.0], [bar_y, bar_y], color=line_c, lw=4.0, zorder=6)
    ax.plot([cx - L / 2.0, cx - L / 2.0], [bar_y, bar_y - 0.25], color=line_c, lw=3.0, zorder=6)
    ax.plot([cx + L / 2.0, cx + L / 2.0], [bar_y, bar_y - 0.25], color=line_c, lw=3.0, zorder=6)
    dia = c_info.get("dia_extra", 12)
    txt = (f"Top Cap Col {c_info['id']}: {c_info['bars_per_m']} Φ{dia}/m' "
           f"(Total: {c_info['n_extra']} Φ{dia}, L = {L:.2f} m)\n"
           f"Zone {L:.2f} × {wcap:.2f} m")
    ty = cy + wcap / 2.0 + 0.55 if label_above else cy - wcap / 2.0 - 0.55
    _tag(ax, txt, (cx, cy + (wcap / 2.0 if label_above else -wcap / 2.0)), (cx, ty), text_c, fontsize)
