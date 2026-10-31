"""
modules/roof_beam_layout.py
================================================================================
Automated Roof Beams & Drop Beams (تصميم وتفريد ونماذج كمرات السقف والكوابيل)
Classification, Continuity Derivation, Structural Design, and 3-Model Grouping
Engine for Module 1 (ECP 203-2018).

Key Capabilities:
1. Coordinates & Connectivity Extraction:
   - Reads active columns and grid layout from Module 1.
   - Merges any existing custom drop beams from Drop Beams Engine.
   - Extracts orthogonal grid lines (X and Y directions) connecting columns.
   - Identifies cantilever zones (left, right, top, bottom) and generates
     cantilever beams (CB) extending to the slab edge.
2. Support Continuity Derivation (حالة الاستمرارية والدعم):
   - Simply Supported (حر من الطرفين) for 2-column line
   - Continuous from One End (مستمر من طرف واحد) for terminal spans of multi-column lines
   - Continuous from Both Ends (مستمر من الطرفين) for interior spans
   - Cantilever (كابولي) for cantilever beams with main top steel
3. Comprehensive Structural Design (per ECP 203):
   - Drop Beam Self-weight (stem below slab) + Tributary Slab Load (which already includes equivalent distributed wall load).
   - Bending moments (positive and negative), shear forces.
   - Recommended depth t_calc (deflection limit & flexure).
   - Bottom & top reinforcement, skin/shrinkage side bars (t >= 60 cm), stirrups.
4. Automatic Grouping into 3 Execution Models (B1, B2, B3) + Cantilevers (CB):
   - Sorts regular beams descending by structural demand.
   - Divides into B1 (Heavy), B2 (Medium), B3 (Light), plus CB (Cantilevers).
   - Applies Governing Envelope Rule (max t, max As_bot, max As_top, max stirrups).
   - Dynamic re-design when depth is modified by the user.
5. Bill of Quantities (BOQ):
   - Concrete volume, rebar weight by bar diameter, cement, sand, gravel.
================================================================================
"""

import math
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def extract_roof_beams_and_models(
    active_columns: list,
    drop_beams: list = None,
    cantilevers: dict = None,
    Lx_spans: list = None,
    Ly_spans: list = None,
    ts_cm: float = 20.0,
    Wu_slab: float = 1.45,
    Fcu: float = 250.0,
    Fy: float = 4000.0,
    b_unified: float = 25.0,
    has_wall: bool = False,
    h_wall: float = 0.0,
    t_wall: float = 0.0,
    gamma_brick: float = 1.80,
    phi_bot: int = 16,
    phi_top: int = 12,
    phi_st: int = 8,
    phi_side: int = 10,
    stirrups_per_m: int = 6,
    user_overrides: dict = None,
    slab_bounds: dict = None,
) -> dict:
    """
    Extracts, designs, and groups actual user-defined roof beams and cantilevers from
    Plan Structural Management (fs_drop_beams) without fabricating unentered grid beams.
    """
    # 1. Fetch user drop beams from parameter or session_state as single source of truth
    if drop_beams is None:
        try:
            import streamlit as st
            drop_beams = st.session_state.get("fs_drop_beams")
            if drop_beams is None and "cfg" in st.session_state:
                drop_beams = st.session_state["cfg"].get("fs_drop_beams")
        except Exception:
            drop_beams = None

    if not isinstance(drop_beams, list):
        drop_beams = []

    # If no drop beams are defined in Plan Structural Management, return clean empty structure
    if not active_columns or not drop_beams:
        return {
            "all_links": [],
            "roof_beams": [],
            "cantilever_beams": [],
            "all_roof_beams": [],
            "models_schedule": [],
            "models_dict": {},
            "boq": {
                "conc_vol_rc": 0.0, "steel_kg_tot": 0.0, "steel_ton_tot": 0.0,
                "cement_ton": 0.0, "cement_bags": 0, "sand_m3": 0.0,
                "gravel_m3": 0.0, "dia_map": {}, "steel_ratio_kg_m3": 0.0,
            },
            "classification_rows": [],
            "detailed_schedule_rows": [],
            "slab_bounds": slab_bounds or {},
            "cantilevers": cantilevers or {},
        }

    cover_cm = 4.0
    fy_st = 2400.0 if phi_st <= 8 else 4000.0
    qcu = 0.75 * math.sqrt(max(1.0, Fcu) / 1.5)
    qu_max = 2.20 * math.sqrt(max(1.0, Fcu) / 1.5)
    area_1bot = math.pi * ((phi_bot / 10.0) ** 2) / 4.0
    area_1top = math.pi * ((phi_top / 10.0) ** 2) / 4.0
    area_1st = math.pi * ((phi_st / 10.0) ** 2) / 4.0
    n_branches = 4 if b_unified >= 40.0 else 2

    from modules.drop_beams_engine import recompute_all_drop_beams
    eff_sb = slab_bounds or {}
    cant_dict = cantilevers or {}

    # ── Step A: Structural Recomputation of User Beams ──────────────────────
    recomputed_user_beams = recompute_all_drop_beams(
        drop_beams,
        b_cm=b_unified,
        dia_main=phi_bot,
        col_w_cm=30.0,
        col_d_cm=50.0,
        Fcu=Fcu,
        Fy=Fy,
        Wu_slab=Wu_slab,
        wall_load=(gamma_brick * t_wall * h_wall) if has_wall else 0.45,
        ts_cm=ts_cm,
        columns_list=active_columns,
        cantilevers=cant_dict,
        grid_bounds=eff_sb,
    )

    analyzed_roof_beams = []
    for idx, b in enumerate(recomputed_user_beams, start=1):
        p1 = b.get("p1_face") or b.get("p1_grid") or b.get("p1", [0, 0])
        p2 = b.get("p2_face") or b.get("p2_grid") or b.get("p2", [0, 0])
        p1_g = b.get("p1_grid") or b.get("p1", [0, 0])
        p2_g = b.get("p2_grid") or b.get("p2", [0, 0])

        is_cant = bool(b.get("is_cantilever") or b.get("beam_type_category") == "cantilever_beam" or b.get("is_continuous") == "cantilever")
        span_m = float(b.get("total_span_m", math.hypot(p2[0] - p1[0], p2[1] - p1[1])))
        clear_span_m = float(b.get("clear_span_m", span_m))

        Mu_pos = 0.0 if is_cant else float(b.get("Mu_ton_m", 0.0))
        Mu_neg = float(b.get("Mu_ton_m", 0.0)) if is_cant else 0.0
        Qu = float(b.get("Vu_ton", 0.0))

        b_cm = float(b.get("b_cm", b_unified))
        t_cm = float(b.get("t_cm", 60.0))
        d_cm = float(b.get("d_cm", max(10.0, t_cm - cover_cm)))

        n_bot = int(b.get("n_bars_btm", 2))
        n_top = int(b.get("n_bars_top", 2))
        st_req = int(b.get("stirrup_n", stirrups_per_m))
        n_side = int(b.get("n_skin_per_side", 0) * 2)

        cont_str = b.get("is_continuous", "simple")
        if is_cant:
            supp_cond = "Cantilever (كابولي طرفي)"
        elif cont_str == "both_ends":
            supp_cond = "Continuous from Both Ends (مستمر من الطرفين)"
        elif cont_str == "one_end":
            supp_cond = "Continuous from One End (مستمر من طرف واحد)"
        else:
            supp_cond = "Simply Supported (حر من الطرفين)"

        supp_desc = str(b.get("supports_desc", "ركيزة ⟷ ركيزة"))
        axis_name = str(b.get("axis_name", ""))
        instance_id = str(b.get("id", f"B{idx}"))

        demand_score = round(max(Mu_pos, Mu_neg) * 10.0 + span_m * 2.0 + t_cm, 2)

        qu = (Qu * 1000.0) / (b_cm * d_cm) if (b_cm * d_cm) > 0 else 0.0
        if qu > qu_max:
            shear_status = "⚠️ غير آمن قصاً (يلزم زيادة القطاع)"
        elif qu > qcu:
            shear_status = "✅ آمن بالكانات"
        else:
            shear_status = "✅ آمن خرسانة فقط"

        n_br = 4 if b_cm >= 40.0 else 2

        analyzed_roof_beams.append({
            "elem_id": instance_id,
            "beam_id": instance_id,
            "instance_id": instance_id,
            "dir": "X" if abs(p2[0] - p1[0]) >= abs(p2[1] - p1[1]) else "Y",
            "axis_name": axis_name or f"Beam {instance_id}",
            "col_str": supp_desc,
            "span_m": span_m,
            "clear_span_m": clear_span_m,
            "L_des": span_m,
            "supp_cond": supp_cond,
            "is_cantilever": is_cant,
            "b_cm": b_cm,
            "t_calc": t_cm,
            "t_cm": t_cm,
            "Mu_pos": Mu_pos,
            "Mu_neg": Mu_neg,
            "Qu": Qu,
            "As_bot_req": n_bot * area_1bot,
            "As_top_req": n_top * area_1top,
            "n_bot": n_bot,
            "phi_bot": phi_bot,
            "n_top": n_top,
            "phi_top": phi_top,
            "total_side_bars": n_side,
            "phi_side": phi_side,
            "stirrups_per_m": st_req,
            "phi_st": phi_st,
            "n_branches": n_br,
            "demand_score": demand_score,
            "shear_status": shear_status,
            "p1": p1,
            "p2": p2,
            "p1_grid": p1_g,
            "p2_grid": p2_g,
        })

    # ── Step B: Grouping into Models (B1, B2, B3, CB1) ──────────────────────
    reg_beams = [b for b in analyzed_roof_beams if not b["is_cantilever"]]
    cant_beams = [b for b in analyzed_roof_beams if b["is_cantilever"]]

    reg_beams.sort(key=lambda b: b["demand_score"], reverse=True)
    n_reg = len(reg_beams)
    group_assignments = {}

    if n_reg == 1:
        group_assignments[reg_beams[0]["beam_id"]] = "B1"
    elif n_reg == 2:
        group_assignments[reg_beams[0]["beam_id"]] = "B1"
        group_assignments[reg_beams[1]["beam_id"]] = "B2"
    elif n_reg >= 3:
        cut1 = int(math.ceil(n_reg / 3.0))
        cut2 = int(math.ceil(2.0 * n_reg / 3.0))
        for i, rb in enumerate(reg_beams):
            if i < cut1:
                group_assignments[rb["beam_id"]] = "B1"
            elif i < cut2:
                group_assignments[rb["beam_id"]] = "B2"
            else:
                group_assignments[rb["beam_id"]] = "B3"

    for cb in cant_beams:
        group_assignments[cb["beam_id"]] = "CB1"

    # Compute Governing Envelopes
    models_dict = {}
    overrides = user_overrides or {}

    model_categories = [
        ("B1", "B1 (Heavy — قطاع ثقيل لأعلى عزوم وبحور سقف)"),
        ("B2", "B2 (Medium — قطاع متوسط للبحور المعتدلة بالسقف)"),
        ("B3", "B3 (Light — قطاع خفيف للبحور القصيرة وقواطيع المباني)"),
    ]
    if cant_beams:
        model_categories.append(("CB1", "CB1 (Cantilever — كمرات كابولية بأعلى عزوم سالبة وشوك علوية)"))

    for mark, label in model_categories:
        grp = [b for b in analyzed_roof_beams if group_assignments.get(b["beam_id"]) == mark]
        if not grp:
            continue

        env_t = max(b["t_calc"] for b in grp)
        env_t = float(math.ceil(env_t / 5.0) * 5.0)
        ov_t = float(overrides.get(f"{mark}_t", env_t))

        env_b = max(b["b_cm"] for b in grp)
        env_nbot = max(b["n_bot"] for b in grp)
        env_ntop = max(b["n_top"] for b in grp)
        env_st = max(b["stirrups_per_m"] for b in grp)

        ov_nbot = int(overrides.get(f"{mark}_nbot", env_nbot))
        ov_ntop = int(overrides.get(f"{mark}_ntop", env_ntop))
        ov_st = int(overrides.get(f"{mark}_stirrups", env_st))

        if ov_t >= 60.0:
            side_spaces = math.ceil((ov_t - 2.0 * cover_cm) / 30.0)
            env_side_rows = max(1, side_spaces - 1)
        else:
            env_side_rows = 0
        env_side_bars = 2 * env_side_rows

        tot_len_m = sum(b["span_m"] for b in grp)
        n_br = 4 if env_b >= 40.0 else 2

        models_dict[mark] = {
            "mark": mark,
            "label": label,
            "count": len(grp),
            "total_len_m": tot_len_m,
            "b_cm": env_b,
            "t_cm": ov_t,
            "t_env_calc": env_t,
            "n_bot": ov_nbot,
            "phi_bot": phi_bot,
            "n_top": ov_ntop,
            "phi_top": phi_top,
            "total_side_bars": env_side_bars,
            "phi_side": phi_side,
            "stirrups_per_m": ov_st,
            "phi_st": phi_st,
            "n_branches": n_br,
            "rft_bot_str": f"{ov_nbot}Ø{phi_bot}",
            "rft_top_str": f"{ov_ntop}Ø{phi_top}",
            "rft_side_str": f"{env_side_bars}Ø{phi_side} (براندات)" if env_side_bars > 0 else "—",
            "stirrups_str": f"{ov_st}Ø{phi_st}/m ({n_br} فروع)",
            "dimensions_str": f"{int(env_b)} × {int(ov_t)}",
            "is_cantilever": (mark == "CB1"),
        }

    # Assign Model Tag to each beam
    for b in analyzed_roof_beams:
        b["model_mark"] = group_assignments.get(b["beam_id"], "B1")
        b["tag"] = b["model_mark"]
        m_info = models_dict.get(b["model_mark"], {})
        b["exec_t_cm"] = m_info.get("t_cm", b["t_calc"])
        b["exec_n_bot"] = m_info.get("n_bot", b["n_bot"])
        b["exec_n_top"] = m_info.get("n_top", b["n_top"])
        b["exec_stirrups_per_m"] = m_info.get("stirrups_per_m", b["stirrups_per_m"])
        b["exec_side_bars"] = m_info.get("total_side_bars", 0)

    # ── Step C: Master Roof Beams Schedule ────────────────────────────────────
    models_schedule = []
    for mark in ["B1", "B2", "B3", "CB1"]:
        if mark in models_dict:
            m = models_dict[mark]
            models_schedule.append({
                "النموذج (Mark)": m["mark"],
                "التصنيف والأهمية الإنشائية": m["label"].split("—")[1].strip(" )") if "—" in m["label"] else m["label"],
                "الأبعاد b × t (cm)": m["dimensions_str"],
                "التسليح السفلي (Bottom Rft)": m["rft_bot_str"],
                "التسليح العلوي / الشوك (Top Rft)": m["rft_top_str"],
                "براندات الانكماش (Side Bars)": m["rft_side_str"],
                "الكانات (Stirrups)": m["stirrups_str"],
                "العدد بالمشروع (Count)": f"{m['count']} كمرة",
                "إجمالي الأطوال (Total Length)": f"{m['total_len_m']:.2f} m",
            })

    # ── Step D: Classification Rows ──────────────────────────────────────────
    classification_rows = []
    for rb in analyzed_roof_beams:
        rft_str = f"سفلي: {rb['exec_n_bot']}Ø{rb['phi_bot']} | علوي: {rb['exec_n_top']}Ø{rb['phi_top']} | كانات: {rb['exec_stirrups_per_m']}Ø{rb['phi_st']}/m"
        if rb.get("exec_side_bars", 0) > 0:
            rft_str += f" | براندات: {rb['exec_side_bars']}Ø{rb['phi_side']}"

        forces_str = f"Mu- = {rb['Mu_neg']:.2f} t.m | Qu = {rb['Qu']:.2f} t" if rb["is_cantilever"] else f"Mu+ = {rb['Mu_pos']:.2f} t.m | Qu = {rb['Qu']:.2f} t"
        type_str = "Cantilever Beam (كمرة كابولية — نموذج CB1)" if rb["is_cantilever"] else f"Roof Drop Beam (كمرة سقف ساقطة — نموذج {rb['tag']})"

        classification_rows.append({
            "Element ID": rb["elem_id"],
            "Tag / Mark": rb["tag"],
            "Type (التصنيف الإنشائي)": type_str,
            "From Column — To Column": rb["col_str"],
            "Axis / Location": rb["axis_name"],
            "Span L (m)": f"{rb['span_m']:.2f} m (صافي {rb['clear_span_m']:.2f}m)",
            "Cross-Section (b × t)": f"{int(rb['b_cm'])} × {int(rb['exec_t_cm'])}",
            "Structural Behavior / Notes": rb["supp_cond"],
            "Design Capacity / Forces": forces_str,
            "Reinforcement Summary": rft_str,
        })

    # ── Step E: Detailed Schedule Rows ───────────────────────────────────────
    detailed_schedule_rows = []
    for rb in analyzed_roof_beams:
        forces_str = f"Mu- = {rb['Mu_neg']:.2f}" if rb["is_cantilever"] else f"Mu+ = {rb['Mu_pos']:.2f}"
        detailed_schedule_rows.append({
            "الكمرة (ID)": rb["elem_id"],
            "النموذج (Mark)": rb["tag"],
            "المحور / الموقع": rb["axis_name"],
            "الأعمدة / الركائز": rb["col_str"],
            "البحر S (m)": f"{rb['span_m']:.2f}",
            "البحر الصافي Ln (m)": f"{rb['clear_span_m']:.2f}",
            "القطاع b × t (cm)": f"{int(rb['b_cm'])} × {int(rb['exec_t_cm'])}",
            "حالة الاستمرارية": rb["supp_cond"].split("(")[0].strip(),
            "عزم التصميم Mu (t.m)": forces_str,
            "قوة القص Qu (ton)": f"{rb['Qu']:.2f}",
            "التسليح السفلي (Bottom Steel)": f"{rb['exec_n_bot']}Ø{rb['phi_bot']}",
            "التسليح العلوي (Top Steel)": f"{rb['exec_n_top']}Ø{rb['phi_top']}",
            "براندات الجوانب (Side Bars)": f"{rb['exec_side_bars']}Ø{rb['phi_side']}" if rb.get('exec_side_bars', 0) > 0 else "—",
            "الكانات (Stirrups)": f"{rb['exec_stirrups_per_m']}Ø{rb['phi_st']}/m",
            "حالة التحقق (Status)": rb["shear_status"],
        })

    # ── Step F: BOQ (حصر الكميات الحقيقي) ───────────────────────────────────
    conc_vol_rc = sum((b["b_cm"] / 100.0) * (b["exec_t_cm"] / 100.0) * b["span_m"] for b in analyzed_roof_beams)
    steel_kg_tot = 0.0
    dia_map = {}

    def _add_dia_wt(d_mm, wt_kg, app_desc):
        if wt_kg <= 0:
            return
        if d_mm not in dia_map:
            dia_map[d_mm] = {"weight_kg": 0.0, "apps": app_desc}
        dia_map[d_mm]["weight_kg"] += wt_kg

    for rb in analyzed_roof_beams:
        L_m = rb["span_m"]
        L_bar_bot = L_m + 2.0 * max(0.40, (50.0 * rb["phi_bot"]) / 1000.0)
        wt_bot = rb["exec_n_bot"] * L_bar_bot * ((rb["phi_bot"] ** 2) / 162.0)

        L_bar_top = (2.5 * L_m + 0.50) if rb["is_cantilever"] else (L_m + 2.0 * max(0.40, (50.0 * rb["phi_top"]) / 1000.0))
        wt_top = rb["exec_n_top"] * L_bar_top * ((rb["phi_top"] ** 2) / 162.0)

        wt_side = 0.0
        if rb["exec_side_bars"] > 0:
            L_bar_side = L_m + 0.30
            wt_side = rb["exec_side_bars"] * L_bar_side * ((rb["phi_side"] ** 2) / 162.0)

        st_w_m = (rb["b_cm"] - 2.0 * cover_cm) / 100.0
        st_h_m = (rb["exec_t_cm"] - 2.0 * cover_cm) / 100.0
        st_perim = 2.0 * (st_w_m + st_h_m) + 0.15
        if rb["n_branches"] == 4:
            st_perim *= 2.0
        n_st = max(5, int(math.ceil(rb["exec_stirrups_per_m"] * L_m)))
        wt_st = n_st * st_perim * ((rb["phi_st"] ** 2) / 162.0)

        wt_b_tot = wt_bot + wt_top + wt_side + wt_st
        steel_kg_tot += wt_b_tot

        _add_dia_wt(rb["phi_bot"], wt_bot, "تسليح سفلي رئيسي لكمرات السقف (Roof Beams Bottom Rebar)")
        _add_dia_wt(rb["phi_top"], wt_top, "تسليح علوي وشوك كمرات السقف (Roof Beams Top Rebar / Cantilever Shok)")
        if wt_side > 0:
            _add_dia_wt(rb["phi_side"], wt_side, "براندات انكماش جانبية لكمرات السقف (Roof Beams Side Shrinkage)")
        _add_dia_wt(rb["phi_st"], wt_st, "كانات كمرات السقف (Roof Beams Stirrups)")

    steel_ton_tot = steel_kg_tot / 1000.0
    cement_ton = (conc_vol_rc * 350.0) / 1000.0
    cement_bags = int(round(cement_ton * 1000.0 / 50.0))
    sand_m3 = conc_vol_rc * 0.40
    gravel_m3 = conc_vol_rc * 0.80

    boq = {
        "conc_vol_rc": conc_vol_rc,
        "steel_kg_tot": steel_kg_tot,
        "steel_ton_tot": steel_ton_tot,
        "cement_ton": cement_ton,
        "cement_bags": cement_bags,
        "sand_m3": sand_m3,
        "gravel_m3": gravel_m3,
        "dia_map": dia_map,
        "steel_ratio_kg_m3": (steel_kg_tot / conc_vol_rc) if conc_vol_rc > 0 else 0.0,
    }

    return {
        "all_links": classification_rows,
        "roof_beams": [b for b in analyzed_roof_beams if not b["is_cantilever"]],
        "cantilever_beams": [b for b in analyzed_roof_beams if b["is_cantilever"]],
        "all_roof_beams": analyzed_roof_beams,
        "models_schedule": models_schedule,
        "models_dict": models_dict,
        "boq": boq,
        "classification_rows": classification_rows,
        "detailed_schedule_rows": detailed_schedule_rows,
        "slab_bounds": slab_bounds or {},
        "cantilevers": cant_dict,
    }

def _ar(text):
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        if any('\u0600' <= char <= '\u06FF' for char in str(text)):
            reshaped_text = arabic_reshaper.reshape(str(text))
            return get_display(reshaped_text)
        return str(text)
    except Exception:
        return str(text)


def _hdim(ax, y, x1, x2, label, side="top", fs=9.0, offset=0.18, draw_ext=True):
    ym = y + offset if side == "top" else y - offset
    ax.annotate("", xy=(x1, ym), xytext=(x2, ym), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.2))
    if draw_ext:
        ax.plot([x1, x1], [y, ym], color="#94a3b8", lw=0.8, ls="--", alpha=0.7)
        ax.plot([x2, x2], [y, ym], color="#94a3b8", lw=0.8, ls="--", alpha=0.7)
    ax.text((x1 + x2) / 2.0, ym + (0.08 if side == "top" else -0.08),
            label, ha="center", va="bottom" if side == "top" else "top",
            fontsize=fs, fontweight="bold", color="#1e293b")


def _vdim(ax, x, y1, y2, label, side="left", fs=9.0, offset=0.18, draw_ext=True):
    xm = x + offset if side == "right" else x - offset
    ax.annotate("", xy=(xm, y1), xytext=(xm, y2), arrowprops=dict(arrowstyle="<->", color="#334155", lw=1.2))
    if draw_ext:
        ax.plot([x, xm], [y1, y1], color="#94a3b8", lw=0.8, ls="--", alpha=0.7)
        ax.plot([x, xm], [y2, y2], color="#94a3b8", lw=0.8, ls="--", alpha=0.7)
    ax.text(xm + (0.08 if side == "right" else -0.08), (y1 + y2) / 2.0,
            label, ha="right" if side == "left" else "left", va="center",
            rotation=90, fontsize=fs, fontweight="bold", color="#1e293b")


def _get_grid_axes_rb(columns_list):
    if not columns_list:
        return [], [], {}, {}
    has_grid_m = any("grid_x_m" in c for c in columns_list)
    if has_grid_m:
        unique_xs = sorted(list(set(round(float(c["grid_x_m"]), 3) for c in columns_list if "grid_x_m" in c)))
        unique_ys = sorted(list(set(round(float(c["grid_y_m"]), 3) for c in columns_list if "grid_y_m" in c)))
    else:
        def _cluster(coords, tol=0.35):
            if not coords:
                return []
            sc = sorted(coords)
            clusters = [[sc[0]]]
            for val in sc[1:]:
                if val - clusters[-1][-1] <= tol:
                    clusters[-1].append(val)
                else:
                    clusters.append([val])
            return sorted([round(sum(cl) / len(cl), 2) for cl in clusters])

        unique_xs = _cluster([c["x"] for c in columns_list])
        unique_ys = _cluster([c["y"] for c in columns_list])

    label_map_x = {}
    label_map_y = {}
    for c in columns_list:
        gx = c.get("grid_x_m", c.get("x"))
        gy = c.get("grid_y_m", c.get("y"))
        if "grid_x" in c and c["grid_x"] and unique_xs:
            best_x = min(unique_xs, key=lambda u: abs(u - gx))
            label_map_x[best_x] = str(c["grid_x"])
        if "grid_y" in c and c["grid_y"] and unique_ys:
            best_y = min(unique_ys, key=lambda u: abs(u - gy))
            label_map_y[best_y] = str(c["grid_y"])

    return unique_xs, unique_ys, label_map_x, label_map_y


def draw_roof_beams_layout_sketch(
    active_columns: list,
    roof_beams_analysis: dict,
    slab_bounds: dict = None,
    title: str = "ECP 203 — Roof Drop Beams & Cantilevers 2D Framing Plan",
):
    """
    Renders comprehensive 2D roof beams and cantilevers framing plan sketch:
    - B1 Heavy Roof Beams: Royal Blue (#1d4ed8)
    - B2 Medium Roof Beams: Emerald Green (#15803d)
    - B3 Light Roof Beams: Soft Purple/Violet (#7e22ce)
    - CB1 Cantilever Beams: Warm Coral/Orange (#ea580c) with top shok rebar
    - Slab footprint with outer and core boundaries & shaded cantilever zones
    - Structural grid lines with circular bubbles, bay spans, and total dimensions
    - Shaded column rectangles with column IDs
    - Full Legend matching Master Roof Beams Schedule (100% data consistency)
    """
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Calibri", "sans-serif"]
    fig, ax = plt.subplots(figsize=(16, 13), dpi=160, facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")

    if not active_columns:
        ax.text(0.5, 0.5, "No Active Columns Found / لا توجد أعمدة مفعلة", ha="center", va="center", fontsize=14, color="#64748b")
        ax.axis("off")
        return fig

    unique_xs, unique_ys, label_map_x, label_map_y = _get_grid_axes_rb(active_columns)

    eff_sb = slab_bounds or roof_beams_analysis.get("slab_bounds") or {}
    c_dict = roof_beams_analysis.get("cantilevers") or {}
    cant_left = float(eff_sb.get("cant_left", c_dict.get("left", 0.0) or 0.0) or 0.0)
    cant_right = float(eff_sb.get("cant_right", c_dict.get("right", 0.0) or 0.0) or 0.0)
    cant_bottom = float(eff_sb.get("cant_bottom", c_dict.get("bottom", 0.0) or 0.0) or 0.0)
    cant_top = float(eff_sb.get("cant_top", c_dict.get("top", 0.0) or 0.0) or 0.0)

    col_xs = [float(c["x"]) for c in active_columns]
    col_ys = [float(c["y"]) for c in active_columns]

    x_core_min = float(eff_sb.get("min_x", unique_xs[0] if unique_xs else min(col_xs)))
    x_core_max = float(eff_sb.get("max_x", unique_xs[-1] if unique_xs else max(col_xs)))
    y_core_min = float(eff_sb.get("min_y", unique_ys[0] if unique_ys else min(col_ys)))
    y_core_max = float(eff_sb.get("max_y", unique_ys[-1] if unique_ys else max(col_ys)))

    # Outer slab boundary including cantilevers
    x_slab_min = x_core_min - cant_left
    x_slab_max = x_core_max + cant_right
    y_slab_min = y_core_min - cant_bottom
    y_slab_max = y_core_max + cant_top

    min_gx = unique_xs[0] if unique_xs else x_core_min
    max_gx = unique_xs[-1] if unique_xs else x_core_max
    min_gy = unique_ys[0] if unique_ys else y_core_min
    max_gy = unique_ys[-1] if unique_ys else y_core_max

    y_top_ref = max(y_slab_max, max_gy) + 0.6
    x_left_ref = min(x_slab_min, min_gx) - 0.6
    y_bottom_ref = min(y_slab_min, min_gy) - 0.6
    x_right_ref = max(x_slab_max, max_gx) + 0.6

    y_dim1 = y_top_ref + 0.5
    y_dim2 = y_top_ref + 1.2
    y_bubble = y_top_ref + 2.1

    x_dim1 = x_left_ref - 0.5
    x_dim2 = x_left_ref - 1.2
    x_bubble = x_left_ref - 2.1

    # 1. Draw Slab Footprint Outline & Cantilevers
    slab_w = x_slab_max - x_slab_min
    slab_h = y_slab_max - y_slab_min
    if slab_w > 0 and slab_h > 0:
        slab_rect = patches.Rectangle(
            (x_slab_min, y_slab_min), slab_w, slab_h,
            facecolor="#f8fafc", edgecolor="#334155", lw=2.2, zorder=1
        )
        ax.add_patch(slab_rect)

    has_cant = (cant_left > 0.05 or cant_right > 0.05 or cant_top > 0.05 or cant_bottom > 0.05)
    if has_cant:
        core_w = x_core_max - x_core_min
        core_h = y_core_max - y_core_min
        if core_w > 0 and core_h > 0:
            core_rect = patches.Rectangle(
                (x_core_min, y_core_min), core_w, core_h,
                facecolor="none", edgecolor="#94a3b8", lw=1.3, ls="--", zorder=1.4
            )
            ax.add_patch(core_rect)

        # Cantilever shaded zones with labels
        if cant_left > 0.05:
            ax.add_patch(patches.Rectangle(
                (x_slab_min, y_slab_min), cant_left, slab_h,
                facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.0, ls=":", alpha=0.5, zorder=1.2
            ))
            ax.text(x_slab_min + cant_left / 2.0, (y_slab_min + y_slab_max) / 2.0,
                    _ar(f"كابولي أيسر ({cant_left:.2f}m)"),
                    ha="center", va="center", fontsize=8.0, color="#b45309", fontweight="bold", rotation=90, zorder=2)

        if cant_right > 0.05:
            ax.add_patch(patches.Rectangle(
                (x_core_max, y_slab_min), cant_right, slab_h,
                facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.0, ls=":", alpha=0.5, zorder=1.2
            ))
            ax.text(x_core_max + cant_right / 2.0, (y_slab_min + y_slab_max) / 2.0,
                    _ar(f"كابولي أيمن ({cant_right:.2f}m)"),
                    ha="center", va="center", fontsize=8.0, color="#b45309", fontweight="bold", rotation=90, zorder=2)

        if cant_top > 0.05:
            ax.add_patch(patches.Rectangle(
                (x_slab_min, y_core_max), slab_w, cant_top,
                facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.0, ls=":", alpha=0.5, zorder=1.2
            ))
            ax.text((x_slab_min + x_slab_max) / 2.0, y_core_max + cant_top / 2.0,
                    _ar(f"كابولي علوي ({cant_top:.2f}m)"),
                    ha="center", va="center", fontsize=8.0, color="#b45309", fontweight="bold", zorder=2)

        if cant_bottom > 0.05:
            ax.add_patch(patches.Rectangle(
                (x_slab_min, y_slab_min), slab_w, cant_bottom,
                facecolor="#fffbeb", edgecolor="#f59e0b", lw=1.0, ls=":", alpha=0.5, zorder=1.2
            ))
            ax.text((x_slab_min + x_slab_max) / 2.0, y_slab_min + cant_bottom / 2.0,
                    _ar(f"كابولي سفلي ({cant_bottom:.2f}m)"),
                    ha="center", va="center", fontsize=8.0, color="#b45309", fontweight="bold", zorder=2)

        ax.text(
            x_slab_min + 0.15, y_slab_max - 0.25, _ar("حدود بلاطة السقف والكوابيل (Slab & Cantilevers Footprint)"),
            fontsize=8.5, color="#64748b", fontweight="bold", zorder=2
        )
    else:
        ax.text(
            x_slab_min + 0.15, y_slab_max - 0.25, _ar("حدود بلاطة السقف (Slab Footprint)"),
            fontsize=8.5, color="#64748b", fontweight="bold", zorder=2
        )

    # 2. Draw Grid Lines, Bubbles & Bay Dimensions
    for idx, gx in enumerate(unique_xs, start=1):
        lbl = label_map_x.get(gx, f"Y{idx}")
        ax.plot([gx, gx], [y_bottom_ref, y_bubble], color="#94a3b8", ls="--", lw=1.1, zorder=1.5)
        ax.text(gx, y_bubble, lbl, ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=10.5,
                bbox=dict(boxstyle="circle,pad=0.30", fc="#f8fafc", ec="#334155", lw=1.5), zorder=8)

    for idx, gy in enumerate(unique_ys, start=1):
        lbl = label_map_y.get(gy, f"X{idx}")
        ax.plot([x_bubble, x_right_ref], [gy, gy], color="#94a3b8", ls="--", lw=1.1, zorder=1.5)
        ax.text(x_bubble, gy, lbl, ha="center", va="center", color="#1e293b", fontweight="bold", fontsize=10.5,
                bbox=dict(boxstyle="circle,pad=0.30", fc="#f8fafc", ec="#334155", lw=1.5), zorder=8)

    # Intermediate Bay Dimensions & Total Dimensions
    if len(unique_xs) > 1:
        for i in range(len(unique_xs) - 1):
            _hdim(ax, y_top_ref, unique_xs[i], unique_xs[i + 1], f"{unique_xs[i+1]-unique_xs[i]:.2f} m", side="top", fs=9.0, offset=0.5, draw_ext=False)
        _hdim(ax, y_top_ref, unique_xs[0], unique_xs[-1], f"Total L = {unique_xs[-1]-unique_xs[0]:.2f} m", side="top", fs=10.0, offset=1.2, draw_ext=False)

    if len(unique_ys) > 1:
        for j in range(len(unique_ys) - 1):
            _vdim(ax, x_left_ref, unique_ys[j], unique_ys[j + 1], f"{unique_ys[j+1]-unique_ys[j]:.2f} m", side="left", fs=9.0, offset=0.5, draw_ext=False)
        _vdim(ax, x_left_ref, unique_ys[0], unique_ys[-1], f"Total B = {unique_ys[-1]-unique_ys[0]:.2f} m", side="left", fs=10.0, offset=1.2, draw_ext=False)

    # 3. Draw Unified Roof Beams (Color-coded by Model)
    color_map = {
        "B1": {"fc": "#dbeafe", "ec": "#1d4ed8", "tc": "#1e40af", "badge_bg": "#eff6ff", "hatch": None},
        "B2": {"fc": "#dcfce7", "ec": "#15803d", "tc": "#166534", "badge_bg": "#f0fdf4", "hatch": None},
        "B3": {"fc": "#f3e8ff", "ec": "#7e22ce", "tc": "#6b21a8", "badge_bg": "#faf5ff", "hatch": None},
        "CB1": {"fc": "#ffedd5", "ec": "#ea580c", "tc": "#9a3412", "badge_bg": "#fff7ed", "hatch": "///"},
    }

    all_beams = roof_beams_analysis.get("all_roof_beams", [])
    if not all_beams:
        mid_x_c = (x_slab_min + x_slab_max) / 2.0
        mid_y_c = (y_slab_min + y_slab_max) / 2.0
        ax.text(
            mid_x_c, mid_y_c,
            _ar("لم يتم إضافة كمرات ساقطة أو كوابيل في إدارة عناصر المسقط (Plan Structural Management)\nقم بإضافة كمرات أو كوابيل من القسم لتظهر هنا وتُنمذج وتُحسب تلقائياً"),
            ha="center", va="center", fontsize=10.5, fontweight="bold", color="#92400e",
            bbox=dict(boxstyle="round,pad=0.7", fc="#fef3c7", ec="#f59e0b", lw=1.5, alpha=0.96),
            zorder=10
        )
    for b in all_beams:
        p1 = b["p1"]
        p2 = b["p2"]
        bw_m = float(b.get("b_cm", 25.0)) / 100.0
        t_cm = int(b.get("exec_t_cm", b.get("t_calc", 50.0)))
        b_cm = int(b.get("b_cm", 25.0))
        tag = b.get("tag", b.get("model_mark", "B1"))
        cfg = color_map.get(tag, {"fc": "#f1f5f9", "ec": "#475569", "tc": "#334155", "badge_bg": "#ffffff", "hatch": None})

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        if abs(dx) >= abs(dy):
            bx0 = min(p1[0], p2[0])
            bw = abs(dx)
            by0 = p1[1] - bw_m / 2.0
            rect = patches.Rectangle(
                (bx0, by0), bw, bw_m,
                facecolor=cfg["fc"], edgecolor=cfg["ec"], hatch=cfg["hatch"], lw=1.8, alpha=0.92, zorder=3
            )
            ax.add_patch(rect)
            mid_x = bx0 + bw / 2.0
            mid_y = by0 + bw_m / 2.0
            rot = 0
        else:
            by0 = min(p1[1], p2[1])
            bh = abs(dy)
            bx0 = p1[0] - bw_m / 2.0
            rect = patches.Rectangle(
                (bx0, by0), bw_m, bh,
                facecolor=cfg["fc"], edgecolor=cfg["ec"], hatch=cfg["hatch"], lw=1.8, alpha=0.92, zorder=3
            )
            ax.add_patch(rect)
            mid_x = bx0 + bw_m / 2.0
            mid_y = by0 + bh / 2.0
            rot = 90

        span_len = b.get("span_m", math.hypot(dx, dy))
        if b.get("is_cantilever"):
            lbl = f"{tag} ({b_cm}×{t_cm})"
            if span_len >= 1.6:
                lbl += f"\n{b.get('exec_n_top', 2)}Ø{b.get('phi_top', 12)} " + _ar("شوك")
        else:
            lbl = f"{tag} ({b_cm}×{t_cm})"
            if span_len >= 3.2:
                lbl += f"\n{b.get('exec_n_bot', 2)}Ø{b.get('phi_bot', 16)} / {b.get('exec_n_top', 2)}Ø{b.get('phi_top', 12)}"

        ax.text(
            mid_x, mid_y, lbl,
            ha="center", va="center", rotation=rot, fontsize=7.5, fontweight="bold", color=cfg["tc"],
            bbox=dict(boxstyle="round,pad=0.20", fc=cfg["badge_bg"], ec=cfg["ec"], lw=0.9, alpha=0.95),
            zorder=6
        )

    # 4. Draw Shaded Columns
    for c in active_columns:
        w_m = float(c.get("width_m", c.get("bc", 30.0) / 100.0))
        h_m = float(c.get("height_m", c.get("tc", 50.0) / 100.0))
        cx = float(c["x"])
        cy = float(c["y"])
        col_r = patches.Rectangle(
            (cx - w_m / 2.0, cy - h_m / 2.0), w_m, h_m,
            facecolor="#1e293b", edgecolor="#0f172a", lw=1.5, zorder=5
        )
        ax.add_patch(col_r)
        c_lbl = str(c.get("orig_id", c.get("id", "C")))
        ax.text(
            cx, cy, c_lbl,
            ha="center", va="center", color="#ffffff", fontweight="bold", fontsize=8.2, zorder=7
        )

    # 5. Legend Box (Matching Master Roof Beams Schedule 100%)
    models_dict = roof_beams_analysis.get("models_dict", {})
    if not models_dict:
        leg_lines = [_ar("دليل نماذج كمرات السقف: لم يتم نمذجة أي كمرات بعد (0 كمرة)")]
    else:
        leg_lines = [_ar("دليل نماذج كمرات السقف التنفيذي (Roof Beams Schedule Legend):")]
    for mk in ["B1", "B2", "B3", "CB1"]:
        if mk in models_dict:
            m = models_dict[mk]
            if mk == "B1":
                dot = "■ B1 (Heavy)"
            elif mk == "B2":
                dot = "■ B2 (Medium)"
            elif mk == "B3":
                dot = "■ B3 (Light)"
            else:
                dot = "■ CB1 (Cantilever)"
            leg_lines.append(
                f"{dot}: {m['dimensions_str']} cm | " + _ar(f"سفلي: {m['rft_bot_str']} | علوي: {m['rft_top_str']} | كانات: {m['stirrups_str']} ({m['count']} كمرة - {m['total_len_m']:.1f}m)")
            )
    leg_text = "\n".join(leg_lines)
    ax.text(
        0.02, 0.02, leg_text, transform=ax.transAxes,
        fontsize=8.5, fontweight="bold", color="#1e293b", va="bottom", ha="left",
        bbox=dict(boxstyle="round,pad=0.45", fc="#ffffff", ec="#cbd5e1", lw=1.3, alpha=0.96),
        zorder=9
    )

    ax.set_xlim(x_bubble - 1.2, x_right_ref + 1.2)
    ax.set_ylim(y_bottom_ref - 1.2, y_bubble + 1.2)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(title, fontsize=13.5, fontweight="bold", color="#0f172a", pad=20)
    return fig
