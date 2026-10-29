# -*- coding: utf-8 -*-
"""
Drop Beams Engine for Flat Slabs (موديول كمرات البلاطات المسطحة)
Structural Design, Interactive Detailing & Cross-Section Generation according to ECP 203.
"""

import math
import io
import base64
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def point_to_segment_distance_and_projection(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> tuple:
    """
    حساب أقرب مسافة ونقطة إسقاط لنقطة P(px, py) على قطعة مستقيمة AB(x1,y1 -> x2,y2).
    ترجع (distance, [proj_x, proj_y], t_param).
    """
    dx = x2 - x1
    dy = y2 - y1
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-6:
        d = math.hypot(px - x1, py - y1)
        return d, [x1, y1], 0.0

    t = ((px - x1) * dx + (py - y1) * dy) / seg_len_sq
    t_clamped = max(0.0, min(1.0, t))
    proj_x = x1 + t_clamped * dx
    proj_y = y1 + t_clamped * dy
    d = math.hypot(px - proj_x, py - proj_y)
    return d, [proj_x, proj_y], t


def detect_support_at_point(
    p: list,
    beam_vec: tuple,
    col_w_m: float = 0.30,
    col_d_m: float = 0.30,
    columns_list: list = None,
    beams_list: list = None,
    current_beam_id: str = None,
    tol_col: float = 0.35,
    tol_beam: float = 0.35,
    cantilevers: dict = None,
    grid_bounds: dict = None,
) -> dict:
    """
    التعرف التلقائي الذكي على ركيزة طرف الكمرة:
    1. عمود خرساني (Column Support): يُخصم بعد وجه العمود.
    2. كمرة رئيسية حاملة (Beam Support): تُخصم مسافة نصف عرض الكمرة الحاملة (b_main / 2).
    3. كابولي / طرف حر (Cantilever / Free End): بدون خصم.
    """
    px, py = float(p[0]), float(p[1])
    ux, uy = beam_vec

    # 1. فحص وجود عمود خرساني كركيزة
    if columns_list:
        for c in columns_list:
            if not isinstance(c, dict):
                continue
            gx = float(c.get("grid_x_m", c.get("center_x", c.get("x", 0.0))))
            gy = float(c.get("grid_y_m", c.get("center_y", c.get("y", 0.0))))
            cx = float(c.get("center_x", c.get("x", gx)))
            cy = float(c.get("center_y", c.get("y", gy)))

            dist_grid = math.hypot(gx - px, gy - py)
            dist_center = math.hypot(cx - px, cy - py)
            in_bbox = False
            if "x_min" in c and "x_max" in c and "y_min" in c and "y_max" in c:
                in_bbox = (float(c["x_min"]) - 0.15 <= px <= float(c["x_max"]) + 0.15) and \
                          (float(c["y_min"]) - 0.15 <= py <= float(c["y_max"]) + 0.15)

            if dist_grid <= 0.60 or dist_center <= 0.60 or in_bbox:
                cid = str(c.get("id", "Column"))
                # حساب بُعد وجه العمود باتجاه مسار الكمرة الصافية بدقة هندسية 100%
                if abs(ux) >= abs(uy):
                    if "x_max" in c and "x_min" in c:
                        offset = (float(c["x_max"]) - px) if ux > 0 else (px - float(c["x_min"]))
                    else:
                        w = float(c.get("width_m", col_w_m))
                        offset = w / 2.0
                else:
                    if "y_max" in c and "y_min" in c:
                        offset = (float(c["y_max"]) - py) if uy > 0 else (py - float(c["y_min"]))
                    else:
                        h = float(c.get("height_m", col_d_m))
                        offset = h / 2.0
                return {
                    "type": "column",
                    "id": cid,
                    "name": f"عمود {cid}",
                    "offset": max(0.05, float(offset)),
                    "obj": c,
                }

    # 2. فحص وجود كمرة رئيسية حاملة متقاطعة (ليست على نفس الامتداد المحوري)
    if beams_list:
        for b in beams_list:
            if not isinstance(b, dict):
                continue
            bid = str(b.get("id", ""))
            if current_beam_id and bid == current_beam_id:
                continue
            bp1 = b.get("p1_grid", b.get("p1", [0, 0]))
            bp2 = b.get("p2_grid", b.get("p2", [0, 0]))
            bx1, by1 = float(bp1[0]), float(bp1[1])
            bx2, by2 = float(bp2[0]), float(bp2[1])
            bL = math.hypot(bx2 - bx1, by2 - by1)
            if bL > 0.1:
                bux, buy = (bx2 - bx1) / bL, (by2 - by1) / bL
                # إذا كانت الكمرة على نفس المحور الهندسي (موازية)، فهي كمرة امتداد وليست كمرة حاملة متقاطعة
                if abs(ux * bux + uy * buy) > 0.85:
                    continue
            dist_b, proj_pt, t_val = point_to_segment_distance_and_projection(
                px, py, bx1, by1, bx2, by2
            )
            if dist_b <= tol_beam:
                # كمرة حاملة رئيسية
                b_main_cm = float(b.get("b_cm", 25.0))
                offset = (b_main_cm / 100.0) / 2.0  # نصف عرض الكمرة الحاملة
                return {
                    "type": "beam",
                    "id": bid,
                    "name": f"كمرة {bid}",
                    "offset": max(0.06, offset),
                    "b_cm": b_main_cm,
                    "obj": b,
                }

    # 3. فحص كابولي البلاطة / نهاية كابولي البلاطة الخارجية
    if cantilevers and grid_bounds:
        cant_l = float(cantilevers.get("left", 0.0) or 0.0)
        cant_r = float(cantilevers.get("right", 0.0) or 0.0)
        cant_b = float(cantilevers.get("bottom", 0.0) or 0.0)
        cant_t = float(cantilevers.get("top", 0.0) or 0.0)

        gx_min = float(grid_bounds.get("min_x", grid_bounds.get("xmin", 0.0)))
        gx_max = float(grid_bounds.get("max_x", grid_bounds.get("xmax", 0.0)))
        gy_min = float(grid_bounds.get("min_y", grid_bounds.get("ymin", 0.0)))
        gy_max = float(grid_bounds.get("max_y", grid_bounds.get("ymax", 0.0)))

        is_at_cant_edge = False
        if cant_l > 0.05 and abs(px - (gx_min - cant_l)) <= 0.35 and (gy_min - cant_b - 0.20 <= py <= gy_max + cant_t + 0.20):
            is_at_cant_edge = True
        elif cant_r > 0.05 and abs(px - (gx_max + cant_r)) <= 0.35 and (gy_min - cant_b - 0.20 <= py <= gy_max + cant_t + 0.20):
            is_at_cant_edge = True
        elif cant_b > 0.05 and abs(py - (gy_min - cant_b)) <= 0.35 and (gx_min - cant_l - 0.20 <= px <= gx_max + cant_r + 0.20):
            is_at_cant_edge = True
        elif cant_t > 0.05 and abs(py - (gy_max + cant_t)) <= 0.35 and (gx_min - cant_l - 0.20 <= px <= gx_max + cant_r + 0.20):
            is_at_cant_edge = True

        if is_at_cant_edge:
            return {
                "type": "cantilever_edge",
                "id": "CantileverEdge",
                "name": "طرف حر (نهاية كابولي البلاطة)",
                "offset": 0.0,
                "obj": None,
            }

    # 4. طرف حر غير مستند (داخل البلاطة)
    return {
        "type": "free",
        "id": "Free",
        "name": "طرف حر (غير مستند)",
        "offset": 0.0,
        "obj": None,
    }


def compute_beam_face_coordinates(
    p1,
    p2,
    col_w_m: float = 0.30,
    col_d_m: float = 0.30,
    columns_list: list = None,
    beams_list: list = None,
    current_beam_id: str = None,
    cantilevers: dict = None,
    grid_bounds: dict = None,
) -> tuple:
    """
    حساب إحداثيات بداية ونهاية الكمرة من وجه الركيزة الداخلي (سواء كانت الركيزة عموداً أو كمرة رئيسية)
    Clear Span from face-to-face of supporting columns or supporting beams.
    ترجع: (p1_face, p2_face, clear_L, supp1_info, supp2_info)
    """
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 0.1:
        default_supp = {"type": "free", "id": "Free", "name": "طرف حر", "offset": 0.0}
        return [x1, y1], [x2, y2], L, default_supp, default_supp

    dx = x2 - x1
    dy = y2 - y1
    ux = dx / L
    uy = dy / L

    supp1 = detect_support_at_point(
        [x1, y1], (ux, uy),
        col_w_m=col_w_m, col_d_m=col_d_m,
        columns_list=columns_list, beams_list=beams_list,
        current_beam_id=current_beam_id,
        cantilevers=cantilevers,
        grid_bounds=grid_bounds,
    )

    supp2 = detect_support_at_point(
        [x2, y2], (-ux, -uy),
        col_w_m=col_w_m, col_d_m=col_d_m,
        columns_list=columns_list, beams_list=beams_list,
        current_beam_id=current_beam_id,
        cantilevers=cantilevers,
        grid_bounds=grid_bounds,
    )

    offset_1 = supp1.get("offset", 0.15)
    offset_2 = supp2.get("offset", 0.15)

    # التحقق من أن مجموع الإزاحات لا يتجاوز طول البحر
    tot_offset = offset_1 + offset_2
    if tot_offset >= L - 0.20:
        offset_1 = min(offset_1, L * 0.25)
        offset_2 = min(offset_2, L * 0.25)

    p1_face = [round(x1 + ux * offset_1, 4), round(y1 + uy * offset_1, 4)]
    p2_face = [round(x2 - ux * offset_2, 4), round(y2 - uy * offset_2, 4)]
    clear_L = math.hypot(p2_face[0] - p1_face[0], p2_face[1] - p1_face[1])

    return p1_face, p2_face, clear_L, supp1, supp2


def find_adjacent_backspan_beam(
    p_root: list,
    p_free: list,
    beams_list: list,
    current_beam_id: str = None,
    tol: float = 0.45,
) -> dict:
    """
    فحص وجود كمرة مجاورة مستمرة (Backspan Beam) على نفس المحور الهندسي تتصل مباشرة بنقطة الركيزة الرأسية (p_root)
    في الاتجاه المعاكس للطرف الحر للكابولي (p_free) لتأمين التثبيت والاستمرارية التامة للعزوم (Full Moment Continuity).
    """
    if not beams_list or not p_root or not p_free:
        return None
    xr, yr = float(p_root[0]), float(p_root[1])
    xf, yf = float(p_free[0]), float(p_free[1])
    L_cant = math.hypot(xf - xr, yf - yr)
    if L_cant < 0.1:
        return None
    ux = (xf - xr) / L_cant
    uy = (yf - yr) / L_cant

    for b in beams_list:
        if not isinstance(b, dict):
            continue
        bid = str(b.get("id", ""))
        if current_beam_id and bid == str(current_beam_id):
            continue
        bp1 = b.get("p1_grid", b.get("p1", [0, 0]))
        bp2 = b.get("p2_grid", b.get("p2", [0, 0]))
        if not bp1 or not bp2:
            continue
        try:
            bx1, by1 = float(bp1[0]), float(bp1[1])
            bx2, by2 = float(bp2[0]), float(bp2[1])
        except (ValueError, TypeError, IndexError):
            continue
        bL = math.hypot(bx2 - bx1, by2 - by1)
        if bL < 0.25:
            continue
        bux = (bx2 - bx1) / bL
        buy = (by2 - by1) / bL
        # يجب أن تقع الكمرة المجاورة على نفس المحور الهندسي
        if abs(ux * bux + uy * buy) < 0.90:
            continue
        # فحص اتصال أحد طرفي الكمرة المجاورة بنقطة الركيزة الرأسية وامتداد الطرف الآخر في الاتجاه المعاكس للكابولي
        d1 = math.hypot(bx1 - xr, by1 - yr)
        d2 = math.hypot(bx2 - xr, by2 - yr)
        if d1 <= tol:
            vec_other_x = bx2 - xr
            vec_other_y = by2 - yr
            if (vec_other_x * ux + vec_other_y * uy) < -0.25 * bL:
                return b
        elif d2 <= tol:
            vec_other_x = bx1 - xr
            vec_other_y = by1 - yr
            if (vec_other_x * ux + vec_other_y * uy) < -0.25 * bL:
                return b
    return None


def design_drop_beam(
    p1: list,
    p2: list,
    b_cm: float = 25.0,
    dia_main: int = 16,
    col_w_cm: float = 30.0,
    col_d_cm: float = 30.0,
    Fcu: float = 250.0,
    Fy: float = 4000.0,
    Wu_slab: float = 1.45,
    wall_load: float = 0.50,
    ts_cm: float = 20.0,
    beam_id: str = "B1",
    is_continuous: str = "simple",
    columns_list: list = None,
    beams_list: list = None,
    user_t_cm: float = 0.0,
    cantilevers: dict = None,
    grid_bounds: dict = None,
) -> dict:
    """
    التصميم الإنشائي الآلي للكمرة الساقطة (Drop / Marginal Beam) وفق الكود المصري ECP 203:
    1. ضبط أطراف الكمرة من وجه العمود حتى وجه العمود الآخر (Face to Face).
    2. حساب عمق الكمرة الكلي t المقرب لأقرب 5 سم بالزيادة لمقاومة الترخيم (أو تطبيق العمق المحدد يدوياً).
    3. حساب التسليح الرئيسي السفلي وفق أقصى عزم انحناء Mu والحد الأدنى As,min (أو علوي لكمرات الكابولي).
    4. حساب التسليح الثانوي لتعليق الكانات (لا يقل عن 20% أو 2Φ12).
    5. حساب قوى القص وإجهادات الكانات وتحديد التكرار والقطر وعدد الفروع.
    6. إضافة أسياخ الانكماش الجانبية (Skin Reinforcement) إذا تجاوز العمق 60 سم.
    """
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    total_span_m = math.hypot(x2 - x1, y2 - y1)

    if not grid_bounds and columns_list:
        xs_c = [float(c.get("center_x", c.get("x", 0.0))) for c in columns_list if isinstance(c, dict)]
        ys_c = [float(c.get("center_y", c.get("y", 0.0))) for c in columns_list if isinstance(c, dict)]
        if xs_c and ys_c:
            grid_bounds = {"xmin": min(xs_c), "xmax": max(xs_c), "ymin": min(ys_c), "ymax": max(ys_c)}

    # حساب إحداثيات أوجه الركائز الصافية (Clear Span from Face to Face)
    p1_face, p2_face, clear_span_m, supp1, supp2 = compute_beam_face_coordinates(
        [x1, y1], [x2, y2],
        col_w_m=col_w_cm / 100.0,
        col_d_m=col_d_cm / 100.0,
        columns_list=columns_list,
        beams_list=beams_list,
        current_beam_id=beam_id,
        cantilevers=cantilevers,
        grid_bounds=grid_bounds,
    )
    clear_span_m = max(0.50, clear_span_m)

    # تحديد نوع الارتكاز وتوصيف الركائز
    s1_type = supp1.get("type", "free")
    s2_type = supp2.get("type", "free")
    s1_name = supp1.get("name", "طرف حر")
    s2_name = supp2.get("name", "طرف حر")

    # قاعدة التعميم الموحدة للكمرات الكابولية:
    # أي كمرة ذات طرف حر ("free" أو "cantilever_edge") تتصل في طرفها الآخر بركيزة رأسية ("column" أو "wall")
    # وتتصل مباشرة بكمرة مجاورة مستمرة على نفس المحور الهندسي تُقبل ككمرة كابولية بتثبيت تام الاستمرارية (Full Moment Continuity).
    backspan_beam = None
    free_is_s2 = None
    if s1_type in ("column", "wall") and s2_type in ("free", "cantilever_edge"):
        backspan_beam = find_adjacent_backspan_beam([x1, y1], [x2, y2], beams_list, current_beam_id=beam_id)
        free_is_s2 = True
    elif s2_type in ("column", "wall") and s1_type in ("free", "cantilever_edge"):
        backspan_beam = find_adjacent_backspan_beam([x2, y2], [x1, y1], beams_list, current_beam_id=beam_id)
        free_is_s2 = False

    is_valid_cantilever = (
        (free_is_s2 is not None and (backspan_beam is not None or is_continuous == "cantilever"))
        or (s1_type == "cantilever_edge" and s2_type in ("column", "wall"))
        or (s2_type == "cantilever_edge" and s1_type in ("column", "wall"))
    )
    is_cantilever_beam = bool(is_valid_cantilever)

    if is_cantilever_beam:
        if free_is_s2 is True or s2_type in ("free", "cantilever_edge"):
            fixed_supp = supp1
            free_supp = supp2
            free_is_s2 = True
        else:
            fixed_supp = supp2
            free_supp = supp1
            free_is_s2 = False
        free_supp["type"] = "cantilever_edge"
        free_supp["id"] = "CantileverFreeEnd"
        free_supp["name"] = "طرف حر كابولي"
        free_supp["offset"] = 0.0
        s1_type = supp1.get("type", "free")
        s2_type = supp2.get("type", "free")
        s1_name = supp1.get("name", "طرف حر")
        s2_name = supp2.get("name", "طرف حر")
        s_fix_name = fixed_supp.get("name", "عمود")
        backspan_lbl = f"كمرة {backspan_beam.get('id')}" if isinstance(backspan_beam, dict) and backspan_beam.get("id") else "كمرة مجاورة مستمرة"
        beam_type_category = "cantilever_beam"
        supports_desc = f"كمرة كابولية (مرتكزة على {s_fix_name} باتصال جاسئ تام الاستمرارية مع {backspan_lbl} ⟷ طرف حر)"
        is_continuous = "cantilever"
        is_secondary = False
    elif s1_type == "beam" and s2_type == "beam":
        beam_type_category = "secondary_2_beams"
        supports_desc = f"كمرة ثانوية (مرتكزة على {s1_name} ⟷ {s2_name})"
        is_secondary = True
    elif (s1_type == "beam" and s2_type == "column") or (s1_type == "column" and s2_type == "beam"):
        beam_type_category = "secondary_beam_col"
        supports_desc = f"كمرة ثانوية (مرتكزة على {s1_name} ⟷ {s2_name})"
        is_secondary = True
    elif s1_type == "column" and s2_type == "column":
        beam_type_category = "main_beam"
        supports_desc = f"كمرة رئيسية (مرتكزة على {s1_name} ⟷ {s2_name})"
        is_secondary = False
    elif s1_type in ("free", "cantilever_edge") or s2_type in ("free", "cantilever_edge"):
        beam_type_category = "unsupported_beam"
        supports_desc = f"⚠️ كمرة بطرف حر غير مستند ({s1_name} ⟷ {s2_name})"
        is_secondary = (s1_type == "beam" or s2_type == "beam")
    else:
        beam_type_category = "marginal_beam"
        supports_desc = f"كمرة ساقطة ({s1_name} ⟷ {s2_name})"
        is_secondary = False

    # 1. حساب العمق الأدنى لمقاومة الترخيم وفق الكود المصري
    # كابولي L/8، بسيطة L/16، مستمرة من طرف L/18.5، مستمرة من طرفين L/21
    if is_continuous == "both_ends":
        t_min_cm = (clear_span_m * 100.0) / 21.0
    elif is_continuous == "one_end":
        t_min_cm = (clear_span_m * 100.0) / 18.5
    elif is_continuous == "cantilever":
        t_min_cm = (clear_span_m * 100.0) / 8.0
    else:
        t_min_cm = (clear_span_m * 100.0) / 16.0

    # فحص ما إذا كان المستخدم أدخل عمقاً محدداً أم تركه آلياً
    if user_t_cm and float(user_t_cm) > 0.0:
        t_cm = math.ceil(float(user_t_cm) / 5.0) * 5.0
        is_auto_t = False
    else:
        # قاعدة التقريب الهندسي: تقريب العمق المحسوب تلقائياً إلى أقرب 5 سم بالزيادة
        t_cm = math.ceil(t_min_cm / 5.0) * 5.0
        min_beam_depth_cm = max(40.0, math.ceil((1.8 * ts_cm) / 5.0) * 5.0)
        t_cm = max(t_cm, min_beam_depth_cm)
        is_auto_t = True

    b_mm = int(round(b_cm * 10.0))
    t_mm = int(round(t_cm * 10.0))
    d_cm = max(10.0, t_cm - 5.0)  # غطاء خرساني وفرش 5 سم

    # 2. أحمال الكمرة القصوى (Ultimate Design Loads)
    # أ- الوزن الذاتي لسقوط الكمرة أسفل البلاطة: b * (t - ts) * γc * 1.4
    w_drop_own = (b_cm / 100.0) * max(0.0, (t_cm - ts_cm) / 100.0) * 2.5 * 1.4
    # ب- حمل الحائط: wall_load * 1.4
    w_wall_ult = float(wall_load) * 1.4
    # ج- حمل شريحة البلاطة المسطحة المنقولة للكمرة (عرض الشريحة Tributary Width ~ 0.25 Ln)
    trib_width_m = min(1.8, max(0.8, clear_span_m * 0.25))
    w_slab_ult = float(Wu_slab) * trib_width_m
    w_ult_tot = w_drop_own + w_wall_ult + w_slab_ult

    # 3. عزم الانحناء التصميمي الأقصى Mu (ton·m)
    if is_continuous == "both_ends":
        km = 12.0
    elif is_continuous == "one_end":
        km = 10.0
    elif is_continuous == "cantilever":
        km = 2.0
    else:
        km = 8.0

    Mu_ton_m = (w_ult_tot * (clear_span_m ** 2)) / km
    Mu_kg_cm = Mu_ton_m * 1e5

    # 4. حساب التسليح الرئيسي (السفلي)
    fy_val = float(Fy)
    fcu_val = float(Fcu)
    j_val = 0.826

    As_req = Mu_kg_cm / ((fy_val / 1.15) * j_val * d_cm) if d_cm > 0 else 0.0

    # الحد الأدنى لكود الخرسانة المصري As,min
    As_min1 = (0.225 * math.sqrt(max(100.0, fcu_val)) / fy_val) * b_cm * d_cm
    As_min2 = (1.1 / fy_val) * b_cm * d_cm
    As_min = max(As_min1, As_min2)
    As_final = max(As_req, As_min)

    # تحويل مساحة الحديد لعدد أسياخ من القطر المختار
    bar_area_cm2 = math.pi * ((dia_main / 10.0) ** 2) / 4.0
    n_bars_btm = max(2, math.ceil(As_final / bar_area_cm2))
    rft_btm_str = f"{n_bars_btm}Ø{dia_main}"

    # 5. حساب التسليح الثانوي (العلوي - تعليق كانات)
    # لا يقل عن 20% من التسليح الرئيسي أو 2Ø12
    As_top = max(0.20 * As_final, 2.0 * (math.pi * 1.2**2 / 4.0))
    n_bars_top = max(2, math.ceil(As_top / (math.pi * 1.2**2 / 4.0)))
    rft_top_str = f"{n_bars_top}Ø12"

    if is_cantilever_beam or is_continuous == "cantilever":
        # في كمرات الكابولي: العزم سالب والشد بالكامل في الألياف العلوية
        # لذا يكون التسليح الرئيسي المحسوب As,final علوياً، والتسليح السفلي تعليق كانات
        rft_top_str = f"{n_bars_btm}Ø{dia_main}"
        rft_btm_str = f"{max(2, n_bars_top)}Ø12"
        _temp_btm = n_bars_btm
        n_bars_btm = max(2, n_bars_top)
        n_bars_top = _temp_btm

    # 6. حساب قوى القص وإجهادات الكانات (Shear Design)
    Vu_ton = (w_ult_tot * clear_span_m) / 2.0 if is_continuous != "cantilever" else (w_ult_tot * clear_span_m)
    Vu_kg = Vu_ton * 1000.0
    qu = Vu_kg / (b_cm * d_cm) if (b_cm * d_cm) > 0 else 0.0
    qcu = 0.24 * math.sqrt(max(100.0, fcu_val) / 1.5) * 10.0  # kg/cm²

    n_branches = 4 if b_cm >= 40.0 else 2
    branch_str = "4 فروع" if n_branches == 4 else "فرعين"

    if qu <= qcu:
        stirrup_n = 5
        stirrups_str = f"5Ø8/m ({branch_str})"
    else:
        qsu = max(1.0, qu - (qcu / 2.0))
        ast_1br = 0.503  # Ø8
        s_cm = (n_branches * ast_1br * (2400.0 / 1.15)) / (b_cm * qsu)
        stirrup_n = min(10, max(5, math.ceil(100.0 / s_cm)))
        stirrups_str = f"{stirrup_n}Ø8/m ({branch_str})"

    # 7. حديد الانكماش الجانبي (Skin Reinforcement) طبقاً للحدود القياسية
    # يضاف أسياخ جانبية كل 30 سم في حال تجاوز العمق الكلي 60 سم
    if t_cm >= 90.0:
        skin_rft_str = "4Ø10 لكل جانب"
        n_skin_per_side = 4
    elif t_cm >= 60.0:
        skin_rft_str = "2Ø10 لكل جانب"
        n_skin_per_side = 2
    else:
        skin_rft_str = "—"
        n_skin_per_side = 0

    # 8. حساب رد الفعل المنقول وكانات التعليق الإضافية (ECP 203 Hanging Stirrups)
    # إذا كانت الكمرة ثانوية وترتكز على كمرة رئيسية، يلزم كانات تعليق إضافية لنقل رد الفعل Ru
    reaction_ton = round(Vu_ton, 2)
    if is_cantilever_beam:
        reaction_s1_ton = 0.0 if (free_is_s2 is False) else reaction_ton
        reaction_s2_ton = 0.0 if (free_is_s2 is True) else reaction_ton
    else:
        reaction_s1_ton = reaction_ton
        reaction_s2_ton = reaction_ton

    hanging_stirrups_str = "—"
    if is_secondary:
        # مساحة كانات التعليق Ash = Ru / (fy / 1.15)
        # Ash (cm²) = (reaction_ton * 1000 kg) / (2400 / 1.15 kg/cm²)
        ash_req_cm2 = (reaction_ton * 1000.0) / (2400.0 / 1.15)
        # مساحة فرعين لكانة Ø8 = 2 * 0.503 = 1.006 سم²
        n_hanging = max(3, math.ceil(ash_req_cm2 / 1.006))
        hanging_stirrups_str = f"{n_hanging}Ø8 إضافي عند الركيزة"

    # 9. حالة الأمان والتحقق الإنشائي (Safe / OK)
    q_max = 0.70 * math.sqrt(max(100.0, fcu_val) / 1.5) * 10.0
    is_safe = (qu <= q_max) and (As_final <= 0.04 * b_cm * d_cm) and (t_cm >= t_min_cm)
    if is_cantilever_beam:
        status_str = "Safe / OK (كمرة كابولية — Full Moment Continuity)" if is_safe else "Review Dimensions"
    elif s1_type in ("free", "cantilever_edge") or s2_type in ("free", "cantilever_edge"):
        status_str = "⚠️ غير كودي: طرف حر غير مستند داخل البلاطة"
    else:
        status_str = "Safe / OK" if is_safe else "Review Dimensions"

    return {
        "id": beam_id,
        "p1": [p1_face[0], p1_face[1]],
        "p2": [p2_face[0], p2_face[1]],
        "p1_grid": [round(x1, 4), round(y1, 4)],
        "p2_grid": [round(x2, 4), round(y2, 4)],
        "p1_face": [p1_face[0], p1_face[1]],
        "p2_face": [p2_face[0], p2_face[1]],
        "supp1": supp1,
        "supp2": supp2,
        "supports_desc": supports_desc,
        "beam_type_category": beam_type_category,
        "is_secondary": is_secondary,
        "reaction_ton": reaction_ton,
        "reaction_s1_ton": reaction_s1_ton,
        "reaction_s2_ton": reaction_s2_ton,
        "hanging_stirrups_str": hanging_stirrups_str,
        "total_span_m": round(total_span_m, 2),
        "clear_span_m": round(clear_span_m, 2),
        "b_cm": b_cm,
        "b_mm": b_mm,
        "t_cm": t_cm,
        "t_mm": t_mm,
        "user_t_cm": float(user_t_cm) if user_t_cm else 0.0,
        "is_auto_t": is_auto_t,
        "d_cm": d_cm,
        "dia_main": dia_main,
        "n_bars_btm": n_bars_btm,
        "rft_btm_str": rft_btm_str,
        "n_bars_top": n_bars_top,
        "rft_top_str": rft_top_str,
        "stirrup_n": stirrup_n,
        "stirrups_str": stirrups_str,
        "skin_rft_str": skin_rft_str,
        "n_skin_per_side": n_skin_per_side,
        "status": status_str,
        "Mu_ton_m": round(Mu_ton_m, 2),
        "Vu_ton": round(Vu_ton, 2),
        "w_ult_tot": round(w_ult_tot, 2),
        "is_continuous": is_continuous,
        "full_moment_continuity": bool(is_cantilever_beam),
        "backspan_beam_id": backspan_beam.get("id") if isinstance(backspan_beam, dict) else None,
    }


def determine_beam_continuity(p1: list, p2: list, other_beams: list, tol: float = 0.45) -> str:
    """
    تحديد طبيعة استمرارية الكمرة (بسيطة / مستمرة من طرف / مستمرة من طرفين)
    وفق اتصال أطرافها بكمرات أخرى على نفس الامتداد.
    """
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    L = math.hypot(dx, dy)
    if L < 0.1:
        return "simple"
    ux, uy = dx / L, dy / L

    cont_start = False
    cont_end = False

    for b in other_beams:
        # فحص باستخدام إحداثيات المحاور (Grid) إن وجدت لضمان دقة 100%
        bp1 = b.get("p1_grid", b.get("p1", [0, 0]))
        bp2 = b.get("p2_grid", b.get("p2", [0, 0]))
        bdx = bp2[0] - bp1[0]
        bdy = bp2[1] - bp1[1]
        bL = math.hypot(bdx, bdy)
        if bL < 0.1:
            continue
        bux, buy = bdx / bL, bdy / bL

        # فحص التوازي على نفس الخط
        dot = abs(ux * bux + uy * buy)
        if dot > 0.90:
            # فحص الاتصال عند P1
            if math.hypot(x1 - bp1[0], y1 - bp1[1]) < tol or math.hypot(x1 - bp2[0], y1 - bp2[1]) < tol:
                cont_start = True
            # فحص الاتصال عند P2
            if math.hypot(x2 - bp1[0], y2 - bp1[1]) < tol or math.hypot(x2 - bp2[0], y2 - bp2[1]) < tol:
                cont_end = True

    if cont_start and cont_end:
        return "both_ends"
    elif cont_start or cont_end:
        return "one_end"
    return "simple"


def auto_merge_collinear_beams(
    beams_list: list,
    columns_list: list = None,
    tol_adjacent: float = 0.35,
    tol_col: float = 0.60,
) -> list:
    """
    فحص ودمج الكمرات المتجاورة الواقعة على استقامة واحدة (Collinear / Adjacent Beams):
    إذا وُجدت كمرتان متجاورتان متصلا النهايات ولا يفصل بينهما أي عمود خرساني (Column)،
    يتم دمج الكمرتين تلقائياً في عنصر إنشائي واحد (كمرة واحدة متصلة) وإعطاؤهما اسماً واحداً موحداً (الأصغر ترقيماً).
    """
    if not beams_list or len(beams_list) < 2:
        return beams_list

    def _has_column_at(pt):
        if not columns_list:
            return False
        px, py = float(pt[0]), float(pt[1])
        for c in columns_list:
            if not isinstance(c, dict):
                continue
            cx = float(c.get("center_x", c.get("x", c.get("grid_x_m", 0.0))))
            cy = float(c.get("center_y", c.get("y", c.get("grid_y_m", 0.0))))
            if math.hypot(cx - px, cy - py) <= tol_col:
                return True
            if "x_min" in c and "x_max" in c and "y_min" in c and "y_max" in c:
                if (float(c["x_min"]) - 0.15 <= px <= float(c["x_max"]) + 0.15 and
                    float(c["y_min"]) - 0.15 <= py <= float(c["y_max"]) + 0.15):
                    return True
        return False

    def _beam_num(bid: str):
        try:
            return int(str(bid).lstrip("B"))
        except Exception:
            return 999999

    merged_any = True
    result = [dict(b) for b in beams_list]

    while merged_any:
        merged_any = False
        n = len(result)
        for i in range(n):
            if merged_any:
                break
            for j in range(i + 1, n):
                b1 = result[i]
                b2 = result[j]
                p1_1 = b1.get("p1_grid", b1.get("p1"))
                p1_2 = b1.get("p2_grid", b1.get("p2"))
                p2_1 = b2.get("p1_grid", b2.get("p1"))
                p2_2 = b2.get("p2_grid", b2.get("p2"))
                if not (p1_1 and p1_2 and p2_1 and p2_2):
                    continue

                dx1, dy1 = float(p1_2[0]) - float(p1_1[0]), float(p1_2[1]) - float(p1_1[1])
                dx2, dy2 = float(p2_2[0]) - float(p2_1[0]), float(p2_2[1]) - float(p2_1[1])
                L1 = math.hypot(dx1, dy1)
                L2 = math.hypot(dx2, dy2)
                if L1 < 0.1 or L2 < 0.1:
                    continue

                u1 = (dx1 / L1, dy1 / L1)
                u2 = (dx2 / L2, dy2 / L2)
                dot = abs(u1[0] * u2[0] + u1[1] * u2[1])
                if dot < 0.98:
                    continue

                # Check collinearity via distance to infinite line of b1
                dist_line = abs(dy1 * float(p2_1[0]) - dx1 * float(p2_1[1]) + float(p1_2[0]) * float(p1_1[1]) - float(p1_2[1]) * float(p1_1[0])) / L1
                if dist_line > 0.35:
                    continue

                # Check shared endpoint junction
                junction = None
                new_p1, new_p2 = None, None
                if math.hypot(float(p1_2[0]) - float(p2_1[0]), float(p1_2[1]) - float(p2_1[1])) <= tol_adjacent:
                    junction = [(float(p1_2[0]) + float(p2_1[0])) / 2.0, (float(p1_2[1]) + float(p2_1[1])) / 2.0]
                    new_p1, new_p2 = list(p1_1), list(p2_2)
                elif math.hypot(float(p1_2[0]) - float(p2_2[0]), float(p1_2[1]) - float(p2_2[1])) <= tol_adjacent:
                    junction = [(float(p1_2[0]) + float(p2_2[0])) / 2.0, (float(p1_2[1]) + float(p2_2[1])) / 2.0]
                    new_p1, new_p2 = list(p1_1), list(p2_1)
                elif math.hypot(float(p1_1[0]) - float(p2_1[0]), float(p1_1[1]) - float(p2_1[1])) <= tol_adjacent:
                    junction = [(float(p1_1[0]) + float(p2_1[0])) / 2.0, (float(p1_1[1]) + float(p2_1[1])) / 2.0]
                    new_p1, new_p2 = list(p1_2), list(p2_2)
                elif math.hypot(float(p1_1[0]) - float(p2_2[0]), float(p1_1[1]) - float(p2_2[1])) <= tol_adjacent:
                    junction = [(float(p1_1[0]) + float(p2_2[0])) / 2.0, (float(p1_1[1]) + float(p2_2[1])) / 2.0]
                    new_p1, new_p2 = list(p1_2), list(p2_1)

                if junction is None:
                    continue

                # Check if an intermediate column exists at the junction
                if _has_column_at(junction):
                    continue

                # Determine primary beam ID (lower number, e.g. B12 instead of B13)
                num1 = _beam_num(b1.get("id"))
                num2 = _beam_num(b2.get("id"))
                if num1 <= num2:
                    pri_b, sec_b = b1, b2
                else:
                    pri_b, sec_b = b2, b1

                pri_id = pri_b.get("id", "B")
                sec_id = sec_b.get("id", "B")

                # Canonical orientation of endpoints (min X, then min Y)
                if (float(new_p1[0]) > float(new_p2[0])) or (abs(float(new_p1[0]) - float(new_p2[0])) < 1e-4 and float(new_p1[1]) > float(new_p2[1])):
                    new_p1, new_p2 = new_p2, new_p1

                merged_beam = dict(pri_b)
                merged_beam["id"] = pri_id
                merged_beam["name"] = f"كمرة {pri_id}"
                merged_beam["p1_grid"] = [round(float(new_p1[0]), 4), round(float(new_p1[1]), 4)]
                merged_beam["p2_grid"] = [round(float(new_p2[0]), 4), round(float(new_p2[1]), 4)]
                merged_beam["p1"] = list(merged_beam["p1_grid"])
                merged_beam["p2"] = list(merged_beam["p2_grid"])
                merged_beam["b_cm"] = max(float(b1.get("b_cm", 25.0)), float(b2.get("b_cm", 25.0)))
                merged_beam["dia_main"] = max(int(b1.get("dia_main", 16)), int(b2.get("dia_main", 16)))

                t1 = float(b1.get("user_t_cm", 0.0) or 0.0)
                t2 = float(b2.get("user_t_cm", 0.0) or 0.0)
                merged_beam["user_t_cm"] = max(t1, t2)

                if "axis_type" not in merged_beam and "axis_type" in sec_b:
                    merged_beam["axis_type"] = sec_b["axis_type"]
                if "axis_index" not in merged_beam and "axis_index" in sec_b:
                    merged_beam["axis_index"] = sec_b["axis_index"]
                if "axis_name" not in merged_beam and "axis_name" in sec_b:
                    merged_beam["axis_name"] = sec_b["axis_name"]

                result[i] = merged_beam
                del result[j]

                # Update any references to sec_id in remaining beams
                for rb in result:
                    for sk in ("supp1", "supp2"):
                        if isinstance(rb.get(sk), dict) and rb[sk].get("id") == sec_id:
                            rb[sk]["id"] = pri_id
                            rb[sk]["name"] = f"كمرة {pri_id}"

                try:
                    import streamlit as st
                    if st.session_state.get("fs_selected_beam_id") == sec_id:
                        st.session_state["fs_selected_beam_id"] = pri_id
                    if st.session_state.get("fs_pending_delete_beam_id") == sec_id:
                        st.session_state["fs_pending_delete_beam_id"] = None
                    gb_ov = st.session_state.get("gb_overrides") or st.session_state.get("cfg", {}).get("gb_overrides")
                    if isinstance(gb_ov, dict):
                        prefix_sec = f"{sec_id}_"
                        prefix_pri = f"{pri_id}_"
                        keys_to_migrate = [k for k in gb_ov if k.startswith(prefix_sec)]
                        for k in keys_to_migrate:
                            new_k = prefix_pri + k[len(prefix_sec):]
                            if new_k not in gb_ov:
                                gb_ov[new_k] = gb_ov[k]
                            del gb_ov[k]
                except Exception:
                    pass

                merged_any = True
                break

    return result


def renumber_drop_beams_sequentially(beams_list: list) -> list:
    """
    إعادة ترتيب وترقيم كمرات النموذج تسلسلياً (B1, B2, B3, ...) بدون فجوات
    بعد أي عملية حذف أو دمج، وتحديث أي مراجع للركائز (supp1 / supp2) المستندة على كمرات أخرى.
    """
    if not beams_list:
        return []

    def _beam_sort_key(b):
        bid = str(b.get("id", ""))
        num = 999999
        if bid.startswith("B"):
            try:
                num = int(bid[1:])
            except Exception:
                pass
        p1 = b.get("p1_grid", b.get("p1", [0, 0]))
        p2 = b.get("p2_grid", b.get("p2", [0, 0]))
        min_y = min(float(p1[1]), float(p2[1])) if len(p1) > 1 and len(p2) > 1 else 0.0
        min_x = min(float(p1[0]), float(p2[0])) if len(p1) > 0 and len(p2) > 0 else 0.0
        return (num, round(min_y, 2), round(min_x, 2))

    sorted_beams = sorted(beams_list, key=_beam_sort_key)
    id_map = {}
    renumbered = []
    for idx, b in enumerate(sorted_beams, start=1):
        old_id = str(b.get("id", f"B{idx}"))
        new_id = f"B{idx}"
        id_map[old_id] = new_id
        b_copy = dict(b)
        b_copy["id"] = new_id
        b_copy["name"] = f"كمرة {new_id}"
        renumbered.append(b_copy)

    # تحديث مراجع الكمرات الثانوية المستندة على كمرات أخرى
    for b in renumbered:
        for sk in ("supp1", "supp2"):
            supp = b.get(sk)
            if isinstance(supp, dict) and supp.get("type") == "beam":
                old_supp_id = str(supp.get("id", ""))
                if old_supp_id in id_map:
                    supp["id"] = id_map[old_supp_id]
                    supp["name"] = f"كمرة {id_map[old_supp_id]}"

    return renumbered


def recompute_all_drop_beams(
    beams_list: list,
    b_cm: float = 25.0,
    dia_main: int = 16,
    col_w_cm: float = 30.0,
    col_d_cm: float = 30.0,
    Fcu: float = 250.0,
    Fy: float = 4000.0,
    Wu_slab: float = 1.45,
    wall_load: float = 0.50,
    ts_cm: float = 20.0,
    columns_list: list = None,
    cantilevers: dict = None,
    grid_bounds: dict = None,
) -> list:
    """
    إعادة الحساب والتصميم اللحظي الشامل لكافة الكمرات في النموذج مع تحديث الاستمرارية والضبط بين أوجه الأعمدة،
    ودمج الكمرات المتجاورة على استقامة واحدة تلقائياً في حال عدم وجود عمود فاصل،
    وتطبيق الاستمرارية التامة للعزوم (Full Moment Continuity) واتزان ردود الأفعال عند ركائز الكمرات الكابولية.
    """
    if columns_list is not None and beams_list:
        beams_list = auto_merge_collinear_beams(beams_list, columns_list=columns_list)

    if beams_list:
        beams_list = renumber_drop_beams_sequentially(beams_list)

    updated = []
    for i, b in enumerate(beams_list):
        # استخدام إحداثيات المحور الأصلية لإعادة اشتقاق أوجه الأعمدة والاستمرارية
        p1 = b.get("p1_grid", b.get("p1", [0, 0]))
        p2 = b.get("p2_grid", b.get("p2", [0, 0]))
        b_val = float(b.get("b_cm", b_cm))
        dia_val = int(b.get("dia_main", dia_main))
        beam_id = b.get("id", f"B{i+1}")
        user_t = float(b.get("user_t_cm", 0.0))

        # تحديد الاستمرارية مقارنة بباقي الكمرات
        others = [ob for j, ob in enumerate(beams_list) if j != i]
        cont = determine_beam_continuity(p1, p2, others)
        if b.get("is_continuous") == "cantilever" or b.get("beam_type_category") == "cantilever_beam":
            cont = "cantilever"

        des = design_drop_beam(
            p1=p1,
            p2=p2,
            b_cm=b_val,
            dia_main=dia_val,
            col_w_cm=col_w_cm,
            col_d_cm=col_d_cm,
            Fcu=Fcu,
            Fy=Fy,
            Wu_slab=Wu_slab,
            wall_load=wall_load,
            ts_cm=ts_cm,
            beam_id=beam_id,
            is_continuous=cont,
            columns_list=columns_list,
            beams_list=beams_list,
            user_t_cm=user_t,
            cantilevers=cantilevers,
            grid_bounds=grid_bounds,
        )
        if "axis_type" in b: des["axis_type"] = b["axis_type"]
        if "axis_index" in b: des["axis_index"] = b["axis_index"]
        if "axis_name" in b: des["axis_name"] = b["axis_name"]
        updated.append(des)

    # ── المرحلة الثانية: تطبيق Full Moment Continuity واتزان العزوم وردود الأفعال بين الكابولي والكمرة المجاورة والعمود ──
    fy_val = float(Fy)
    fcu_val = float(Fcu)
    j_val = 0.826
    for cb in updated:
        if cb.get("is_continuous") != "cantilever" and cb.get("beam_type_category") != "cantilever_beam":
            continue
        s1_t = cb.get("supp1", {}).get("type", "free")
        s2_t = cb.get("supp2", {}).get("type", "free")
        p1_g = cb.get("p1_grid", cb.get("p1", [0, 0]))
        p2_g = cb.get("p2_grid", cb.get("p2", [0, 0]))
        if s1_t in ("column", "wall") and s2_t in ("free", "cantilever_edge"):
            p_root, p_free = p1_g, p2_g
            root_is_s1 = True
        elif s2_t in ("column", "wall") and s1_t in ("free", "cantilever_edge"):
            p_root, p_free = p2_g, p1_g
            root_is_s1 = False
        else:
            continue

        adj_b = find_adjacent_backspan_beam(p_root, p_free, updated, current_beam_id=cb.get("id"))
        if not adj_b:
            continue

        Mu_cant_neg = float(cb.get("Mu_ton_m", 0.0))
        Vu_cant = float(cb.get("Vu_ton", 0.0))
        Ln_adj = max(0.50, float(adj_b.get("clear_span_m", 1.0)))
        w_adj = float(adj_b.get("w_ult_tot", 0.0))
        Mu_adj_neg = max(float(adj_b.get("Mu_ton_m", 0.0)), (w_adj * (Ln_adj ** 2)) / 10.0)

        # العزم السالب المتزن عند الركيزة الجاسئة المشتركة (Full Moment Continuity)
        Mu_joint_neg = max(Mu_adj_neg, Mu_cant_neg)
        joint_d_cm = max(10.0, float(adj_b.get("d_cm", 55.0)), float(cb.get("d_cm", 55.0)))
        adj_b_cm = max(12.0, float(adj_b.get("b_cm", 25.0)))
        adj_dia = int(adj_b.get("dia_main", dia_main))
        As_top_req_joint = (Mu_joint_neg * 1e5) / ((fy_val / 1.15) * j_val * joint_d_cm)
        As_min_adj = max(
            (0.225 * math.sqrt(max(100.0, fcu_val)) / fy_val) * adj_b_cm * joint_d_cm,
            (1.1 / fy_val) * adj_b_cm * joint_d_cm,
        )
        As_top_joint_final = max(As_top_req_joint, As_min_adj)
        bar_area_adj = math.pi * ((adj_dia / 10.0) ** 2) / 4.0
        n_top_joint = max(2, math.ceil(As_top_joint_final / bar_area_adj))

        # مد التسليح العلوي الرئيسي للكابولي باستمرارية تامة داخل الكمرة المجاورة لمقاومة العزم السالب المتزن
        if Mu_cant_neg >= 0.50 * Mu_adj_neg:
            n_top_cant = int(cb.get("n_bars_top", 2))
            n_top_cont = max(n_top_joint, n_top_cant)
            adj_b["n_bars_top"] = n_top_cont
            adj_b["rft_top_str"] = f"{n_top_cont}Ø{adj_dia} (مستمر مع كابولي {cb.get('id')})"

        # ازدواج الاتزان الإنشائي (Overturning / Continuity Balancing Couple): ΔR = Mu_cant / Ln_adj
        delta_R = Mu_cant_neg / Ln_adj
        adj_p1 = adj_b.get("p1_grid", adj_b.get("p1", [0, 0]))
        adj_p2 = adj_b.get("p2_grid", adj_b.get("p2", [0, 0]))
        d_adj_s1 = math.hypot(float(adj_p1[0]) - float(p_root[0]), float(adj_p1[1]) - float(p_root[1]))
        d_adj_s2 = math.hypot(float(adj_p2[0]) - float(p_root[0]), float(adj_p2[1]) - float(p_root[1]))
        base_rxn_s1 = float(adj_b.get("reaction_s1_ton", adj_b.get("reaction_ton", 0.0)))
        base_rxn_s2 = float(adj_b.get("reaction_s2_ton", adj_b.get("reaction_ton", 0.0)))
        if d_adj_s1 <= d_adj_s2:
            adj_b["reaction_s1_ton"] = round(base_rxn_s1 + delta_R, 2)
            adj_b["reaction_s2_ton"] = round(max(0.15 * base_rxn_s2, base_rxn_s2 - delta_R), 2)
        else:
            adj_b["reaction_s2_ton"] = round(base_rxn_s2 + delta_R, 2)
            adj_b["reaction_s1_ton"] = round(max(0.15 * base_rxn_s1, base_rxn_s1 - delta_R), 2)
        adj_b["reaction_ton"] = round(max(adj_b["reaction_s1_ton"], adj_b["reaction_s2_ton"]), 2)
        adj_b["connected_cantilever_id"] = cb.get("id")
        adj_b["Mu_support_neg_ton_m"] = round(Mu_joint_neg, 2)
        adj_b["full_moment_continuity"] = True

        cb["full_moment_continuity"] = True
        cb["backspan_beam_id"] = adj_b.get("id")
        cb["Mu_neg_support_ton_m"] = round(Mu_cant_neg, 2)
        cb["delta_R_equilibrium_ton"] = round(delta_R, 2)
        cb["Mu_col_transferred_ton_m"] = round(Mu_cant_neg, 2)
        if root_is_s1:
            cb["reaction_s1_ton"] = round(Vu_cant, 2)
            cb["reaction_s2_ton"] = 0.0
        else:
            cb["reaction_s1_ton"] = 0.0
            cb["reaction_s2_ton"] = round(Vu_cant, 2)

    return updated


def remap_beams_on_span_change(
    cur_beams: list,
    old_Lx_spans: list,
    new_Lx_spans: list,
    old_Ly_spans: list,
    new_Ly_spans: list,
    old_cantilevers: dict = None,
    new_cantilevers: dict = None,
) -> list:
    """
    إعادة ربط وإزاحة إحداثيات الكمرات الساقطة عند تعديل أي بحر إنشائي (span) بالزيادة أو النقصان.
    تضمن تحريك المحور بكل ما يقع عليه من أعمدة وكمرات ساقطة وكوابيل تلقائياً وبدقة هندسية تامة.
    """
    if not cur_beams:
        return []

    old_cant = old_cantilevers or {}
    new_cant = new_cantilevers or {}

    old_x = [0.0]
    for lx in (old_Lx_spans or []):
        old_x.append(round(old_x[-1] + float(lx), 4))
    new_x = [0.0]
    for lx in (new_Lx_spans or []):
        new_x.append(round(new_x[-1] + float(lx), 4))

    old_y = [0.0]
    for ly in (old_Ly_spans or []):
        old_y.append(round(old_y[-1] + float(ly), 4))
    new_y = [0.0]
    for ly in (new_Ly_spans or []):
        new_y.append(round(new_y[-1] + float(ly), 4))

    if not old_x or not new_x or not old_y or not new_y:
        return cur_beams

    old_cl = float(old_cant.get("left", 0.0) or 0.0)
    new_cl = float(new_cant.get("left", 0.0) or 0.0)
    old_cr = float(old_cant.get("right", 0.0) or 0.0)
    new_cr = float(new_cant.get("right", 0.0) or 0.0)
    old_cb = float(old_cant.get("bottom", 0.0) or 0.0)
    new_cb = float(new_cant.get("bottom", 0.0) or 0.0)
    old_ct = float(old_cant.get("top", 0.0) or 0.0)
    new_ct = float(new_cant.get("top", 0.0) or 0.0)

    def map_x_coord(val):
        v = float(val)
        # Snap to nearest old axis if within 0.35m
        best_i, best_d = None, 0.35
        for i, ox in enumerate(old_x):
            d = abs(v - ox)
            if d < best_d:
                best_d = d
                best_i = i
        if best_i is not None and best_i < len(new_x):
            offset = v - old_x[best_i]
            return round(new_x[best_i] + offset, 4)

        # Cantilever left
        if v < old_x[0]:
            dist = old_x[0] - v
            if old_cl > 0.01 and new_cl > 0.01:
                return round(new_x[0] - (dist * (new_cl / old_cl)), 4)
            return round(new_x[0] - dist, 4)

        # Cantilever right
        if v > old_x[-1]:
            dist = v - old_x[-1]
            if old_cr > 0.01 and new_cr > 0.01:
                return round(new_x[-1] + (dist * (new_cr / old_cr)), 4)
            return round(new_x[-1] + dist, 4)

        # Interpolate inside spans
        for k in range(len(old_x) - 1):
            xa, xb = old_x[k], old_x[k + 1]
            if xa <= v <= xb:
                span_len = xb - xa
                ratio = (v - xa) / span_len if span_len > 1e-6 else 0.0
                if k < len(new_x) - 1:
                    return round(new_x[k] + ratio * (new_x[k + 1] - new_x[k]), 4)
                return round(new_x[-1], 4)

        return round(v, 4)

    def map_y_coord(val):
        v = float(val)
        # Snap to nearest old axis if within 0.35m
        best_j, best_d = None, 0.35
        for j, oy in enumerate(old_y):
            d = abs(v - oy)
            if d < best_d:
                best_d = d
                best_j = j
        if best_j is not None and best_j < len(new_y):
            offset = v - old_y[best_j]
            return round(new_y[best_j] + offset, 4)

        # Cantilever bottom
        if v < old_y[0]:
            dist = old_y[0] - v
            if old_cb > 0.01 and new_cb > 0.01:
                return round(new_y[0] - (dist * (new_cb / old_cb)), 4)
            return round(new_y[0] - dist, 4)

        # Cantilever top
        if v > old_y[-1]:
            dist = v - old_y[-1]
            if old_ct > 0.01 and new_ct > 0.01:
                return round(new_y[-1] + (dist * (new_ct / old_ct)), 4)
            return round(new_y[-1] + dist, 4)

        # Interpolate inside spans
        for k in range(len(old_y) - 1):
            ya, yb = old_y[k], old_y[k + 1]
            if ya <= v <= yb:
                span_len = yb - ya
                ratio = (v - ya) / span_len if span_len > 1e-6 else 0.0
                if k < len(new_y) - 1:
                    return round(new_y[k] + ratio * (new_y[k + 1] - new_y[k]), 4)
                return round(new_y[-1], 4)

        return round(v, 4)

    remapped = []
    for b in cur_beams:
        b_copy = dict(b)
        p1 = list(b.get("p1_grid", b.get("p1", [0, 0])))
        p2 = list(b.get("p2_grid", b.get("p2", [0, 0])))
        ax_type = b.get("axis_type")
        ax_idx = b.get("axis_index")

        # Determine orientation if not explicit
        if not ax_type:
            if abs(p2[0] - p1[0]) >= abs(p2[1] - p1[1]):
                ax_type = "X"
            else:
                ax_type = "Y"
            b_copy["axis_type"] = ax_type

        if ax_type == "X":
            # Horizontal beam along X-axis
            if ax_idx is not None and isinstance(ax_idx, int) and ax_idx > len(new_y):
                continue
            if ax_idx is not None and isinstance(ax_idx, int) and 1 <= ax_idx <= len(new_y):
                target_y = new_y[ax_idx - 1]
                b_copy["axis_index"] = ax_idx
                b_copy["axis_name"] = f"X{ax_idx}"
            else:
                target_y = map_y_coord((p1[1] + p2[1]) / 2.0)
                c_idx = min(range(len(new_y)), key=lambda idx: abs(new_y[idx] - target_y))
                if abs(new_y[c_idx] - target_y) <= 0.35:
                    target_y = new_y[c_idx]
                    b_copy["axis_index"] = c_idx + 1
                    b_copy["axis_name"] = f"X{c_idx + 1}"

            new_x1 = map_x_coord(p1[0])
            new_x2 = map_x_coord(p2[0])
            if abs(new_x2 - new_x1) < 0.20:
                continue

            b_copy["p1_grid"] = [new_x1, target_y]
            b_copy["p2_grid"] = [new_x2, target_y]
            b_copy["p1"] = [new_x1, target_y]
            b_copy["p2"] = [new_x2, target_y]
            b_copy["p1_face"] = [new_x1, target_y]
            b_copy["p2_face"] = [new_x2, target_y]

        else:
            # Vertical beam along Y-axis
            if ax_idx is not None and isinstance(ax_idx, int) and ax_idx > len(new_x):
                continue
            if ax_idx is not None and isinstance(ax_idx, int) and 1 <= ax_idx <= len(new_x):
                target_x = new_x[ax_idx - 1]
                b_copy["axis_index"] = ax_idx
                b_copy["axis_name"] = f"Y{ax_idx}"
            else:
                target_x = map_x_coord((p1[0] + p2[0]) / 2.0)
                c_idx = min(range(len(new_x)), key=lambda idx: abs(new_x[idx] - target_x))
                if abs(new_x[c_idx] - target_x) <= 0.35:
                    target_x = new_x[c_idx]
                    b_copy["axis_index"] = c_idx + 1
                    b_copy["axis_name"] = f"Y{c_idx + 1}"

            new_y1 = map_y_coord(p1[1])
            new_y2 = map_y_coord(p2[1])
            if abs(new_y2 - new_y1) < 0.20:
                continue

            b_copy["p1_grid"] = [target_x, new_y1]
            b_copy["p2_grid"] = [target_x, new_y2]
            b_copy["p1"] = [target_x, new_y1]
            b_copy["p2"] = [target_x, new_y2]
            b_copy["p1_face"] = [target_x, new_y1]
            b_copy["p2_face"] = [target_x, new_y2]

        b_copy["total_span_m"] = round(math.hypot(b_copy["p2_grid"][0] - b_copy["p1_grid"][0], b_copy["p2_grid"][1] - b_copy["p1_grid"][1]), 2)
        remapped.append(b_copy)

    return remapped


def draw_beam_polygon_on_plan(ax, p1, p2, b_m, label="", rft_label="", is_steel_layout=False, is_pending=False):
    """
    رسم كمرة ساقطة كقطاع خرساني مزدوج الحدود على المسقط الأفقي مع وسوم التصميم.
    عند اختيار الكمرة للحذف (is_pending=True) يتم تلوينها بلون باهت مع حدود متقطعة.
    """
    x1, y1 = p1
    x2, y2 = p2
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 0.1:
        return

    dx = (x2 - x1) / L
    dy = (y2 - y1) / L
    nx = -dy * (b_m / 2.0)
    ny = dx * (b_m / 2.0)

    poly_pts = [
        [x1 + nx, y1 + ny],
        [x2 + nx, y2 + ny],
        [x2 - nx, y2 - ny],
        [x1 - nx, y1 - ny],
    ]

    if is_pending:
        edge_col = "#f97316"
        poly = patches.Polygon(
            poly_pts, closed=True, facecolor="#fed7aa",
            edgecolor=edge_col, lw=2.2, zorder=8, linestyle="--", alpha=0.60
        )
        ax.add_patch(poly)
        ax.plot([x1, x2], [y1, y2], color="#ea580c", lw=1.4, linestyle="--", alpha=0.75, zorder=8)
    elif is_steel_layout:
        edge_col = "#1e3a8a"
        poly = patches.Polygon(
            poly_pts, closed=True, facecolor=(37/255.0, 99/255.0, 235/255.0, 0.16),
            edgecolor=edge_col, lw=2.0, zorder=6, linestyle="--"
        )
        ax.add_patch(poly)
        # خطوط التسليح داخل الكمرة
        rnx = -dy * (b_m / 4.0)
        rny = dx * (b_m / 4.0)
        ax.plot([x1 + rnx, x2 + rnx], [y1 + rny, y2 + rny], color="#dc2626", lw=1.8, zorder=7)
        ax.plot([x1 - rnx, x2 - rnx], [y1 - rny, y2 - rny], color="#1e40af", lw=1.8, zorder=7)
    else:
        edge_col = "#0284c7"
        poly = patches.Polygon(
            poly_pts, closed=True, facecolor="#e0f2fe",
            edgecolor=edge_col, lw=2.0, zorder=6
        )
        ax.add_patch(poly)
        # محور الكمرة المنقط
        ax.plot([x1, x2], [y1, y2], color="#0284c7", lw=1.3, linestyle=":", zorder=7)

    # وسام الكمرة في منتصف البحر
    mx = (x1 + x2) / 2.0
    my = (y1 + y2) / 2.0

    angle_deg = math.degrees(math.atan2(dy, dx))
    if angle_deg > 90:
        angle_deg -= 180
    elif angle_deg < -90:
        angle_deg += 180

    txt = rft_label if (is_steel_layout and rft_label) else label
    if is_pending and txt:
        txt = f"{txt} ?"
    if txt:
        txt_col = "#c2410c" if is_pending else "#0f172a"
        box_fc = "#fff7ed" if is_pending else "#ffffff"
        box_alpha = 0.85 if is_pending else 0.95
        ax.text(
            mx, my, txt,
            color=txt_col, fontsize=9.5, weight="bold",
            ha="center", va="center", rotation=angle_deg,
            bbox=dict(boxstyle="round,pad=0.28", facecolor=box_fc, edgecolor=edge_col, lw=1.3, alpha=box_alpha),
            zorder=9 if is_pending else 8,
        )


def generate_beam_cross_section_sketch(beam_data: dict, figsize=(5.5, 6.5)):
    """
    رسم تفصيلي هندسي عالي الدقة للقطاع العرضي للكمرة الساقطة يوضح:
    - الأبعاد الخرسانية (b × t مم)
    - الكانة المغلقة مع قفل 135 درجة
    - أسياخ التسليح الرئيسي السفلي
    - أسياخ تعليق الكانات العلوية
    - أسياخ الانكماش الجانبية (Skin Reinforcement)
    - الغطاء الخرساني والمقاسات بالأسهم
    """
    b_mm = beam_data.get("b_mm", 250)
    t_mm = beam_data.get("t_mm", 600)
    b_cm = b_mm / 10.0
    t_cm = t_mm / 10.0
    cover_cm = 2.5

    fig, ax = plt.subplots(figsize=figsize, dpi=125)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    # 1. رسم القطاع الخرساني (Concrete Section)
    conc_rect = patches.Rectangle(
        (0, 0), b_cm, t_cm,
        linewidth=2.5, edgecolor="#0f172a", facecolor="#f8fafc", zorder=2
    )
    ax.add_patch(conc_rect)

    # 2. رسم الكانة (Stirrup)
    stirrup_x = cover_cm
    stirrup_y = cover_cm
    stirrup_w = max(2.0, b_cm - 2 * cover_cm)
    stirrup_h = max(2.0, t_cm - 2 * cover_cm)
    stirrup_rect = patches.Rectangle(
        (stirrup_x, stirrup_y), stirrup_w, stirrup_h,
        linewidth=2.2, edgecolor="#2563eb", facecolor="none",
        linestyle="-", zorder=3
    )
    ax.add_patch(stirrup_rect)

    # قفل الكانة بزاوية 135 درجة عند الركن العلوي الأيمن
    hook_len = min(2.5, stirrup_w * 0.25)
    ax.plot(
        [stirrup_x + stirrup_w, stirrup_x + stirrup_w - hook_len],
        [stirrup_y + stirrup_h, stirrup_y + stirrup_h - hook_len],
        color="#2563eb", lw=2.2, zorder=4
    )
    ax.plot(
        [stirrup_x + stirrup_w, stirrup_x + stirrup_w - hook_len],
        [stirrup_y + stirrup_h - 0.4, stirrup_y + stirrup_h - hook_len - 0.4],
        color="#2563eb", lw=2.2, zorder=4
    )

    # 3. أسياخ التسليح السفلي (Bottom Main Rebars)
    n_btm = beam_data.get("n_bars_btm", 4)
    dia_main = beam_data.get("dia_main", 16)
    r_bar_cm = (dia_main / 10.0) / 2.0
    if n_btm == 1:
        x_btm_coords = [stirrup_x + stirrup_w / 2.0]
    else:
        spacing_btm = (stirrup_w - 2 * r_bar_cm) / max(1, n_btm - 1)
        x_btm_coords = [stirrup_x + r_bar_cm + i * spacing_btm for i in range(n_btm)]

    y_btm = stirrup_y + r_bar_cm + 0.25
    for bx in x_btm_coords:
        bar_c = patches.Circle((bx, y_btm), r_bar_cm, facecolor="#1e40af", edgecolor="#0f172a", lw=1.2, zorder=5)
        ax.add_patch(bar_c)

    # 4. أسياخ التسليح العلوي (Top Hanger Rebars)
    n_top = beam_data.get("n_bars_top", 2)
    dia_top = 12
    r_top_cm = (dia_top / 10.0) / 2.0
    if n_top == 1:
        x_top_coords = [stirrup_x + stirrup_w / 2.0]
    else:
        spacing_top = (stirrup_w - 2 * r_top_cm) / max(1, n_top - 1)
        x_top_coords = [stirrup_x + r_top_cm + i * spacing_top for i in range(n_top)]

    y_top = stirrup_y + stirrup_h - r_top_cm - 0.25
    for tx in x_top_coords:
        bar_c = patches.Circle((tx, y_top), r_top_cm, facecolor="#dc2626", edgecolor="#0f172a", lw=1.2, zorder=5)
        ax.add_patch(bar_c)

    # 5. أسياخ الانكماش الجانبية (Skin Reinforcement)
    n_skin = beam_data.get("n_skin_per_side", 0)
    dia_skin = 10
    r_skin_cm = (dia_skin / 10.0) / 2.0
    if n_skin > 0:
        step_skin = (stirrup_h - 2 * r_bar_cm - 2 * r_top_cm) / (n_skin + 1)
        for i in range(1, n_skin + 1):
            sy = stirrup_y + r_bar_cm + i * step_skin
            bar_l = patches.Circle((stirrup_x + r_skin_cm + 0.1, sy), r_skin_cm, facecolor="#16a34a", edgecolor="#0f172a", lw=1.2, zorder=5)
            bar_r = patches.Circle((stirrup_x + stirrup_w - r_skin_cm - 0.1, sy), r_skin_cm, facecolor="#16a34a", edgecolor="#0f172a", lw=1.2, zorder=5)
            ax.add_patch(bar_l)
            ax.add_patch(bar_r)

    # 6. أبعاد العرض والعمق (Dimensions)
    dim_y = -3.8
    ax.annotate("", xy=(b_cm, dim_y), xytext=(0, dim_y),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.5, shrinkA=0, shrinkB=0))
    ax.plot([0, 0], [dim_y - 0.8, 0], color="#94a3b8", lw=0.8, linestyle=":")
    ax.plot([b_cm, b_cm], [dim_y - 0.8, 0], color="#94a3b8", lw=0.8, linestyle=":")
    ax.text(b_cm / 2.0, dim_y - 1.2, f"b = {b_mm} mm", color="#0f172a", fontsize=11, weight="bold", ha="center", va="top")

    dim_x = -3.8
    ax.annotate("", xy=(dim_x, t_cm), xytext=(dim_x, 0),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.5, shrinkA=0, shrinkB=0))
    ax.plot([dim_x - 0.8, 0], [0, 0], color="#94a3b8", lw=0.8, linestyle=":")
    ax.plot([dim_x - 0.8, 0], [t_cm, t_cm], color="#94a3b8", lw=0.8, linestyle=":")
    ax.text(dim_x - 1.2, t_cm / 2.0, f"t = {t_mm} mm", color="#0f172a", fontsize=11, weight="bold", ha="right", va="center", rotation=90)

    # 7. وسوم وشروحات التسليح (Annotations / Callouts)
    callout_x = b_cm + 3.2
    # وسام التسليح السفلي
    ax.annotate(
        f"Bottom RFT: {beam_data.get('rft_btm_str', '')}\n(تسليح رئيسي سفلي)",
        xy=(b_cm - cover_cm - r_bar_cm, y_btm),
        xytext=(callout_x, y_btm - 1.2),
        arrowprops=dict(arrowstyle="->", color="#1e40af", lw=1.5),
        fontsize=10, weight="bold", color="#1e40af", va="center"
    )

    # وسام التسليح العلوي
    ax.annotate(
        f"Top RFT: {beam_data.get('rft_top_str', '')}\n(تعليق كانات علوي)",
        xy=(b_cm - cover_cm - r_top_cm, y_top),
        xytext=(callout_x, y_top + 1.2),
        arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.5),
        fontsize=10, weight="bold", color="#dc2626", va="center"
    )

    # وسام الكانات
    ax.annotate(
        f"Stirrups: {beam_data.get('stirrups_str', '')}\n(كانات مقفولة - غطاء {int(cover_cm*10)} مم)",
        xy=(stirrup_x, t_cm / 2.0),
        xytext=(callout_x, t_cm / 2.0),
        arrowprops=dict(arrowstyle="->", color="#2563eb", lw=1.5),
        fontsize=9.5, weight="bold", color="#2563eb", va="center"
    )

    # وسام حديد الانكماش إذا وجد
    if n_skin > 0:
        ax.annotate(
            f"Skin RFT: {beam_data.get('skin_rft_str', '')}\n(حديد انكماش جانبي)",
            xy=(b_cm - stirrup_x, t_cm / 2.0 - 4.0),
            xytext=(callout_x, t_cm / 2.0 - 5.5),
            arrowprops=dict(arrowstyle="->", color="#16a34a", lw=1.5),
            fontsize=9.5, weight="bold", color="#16a34a", va="center"
        )

    ax.set_xlim(-7.5, b_cm + 17.5)
    ax.set_ylim(-7.5, t_cm + 5.5)
    ax.set_aspect("equal")
    ax.axis("off")

    fig.suptitle(
        f"قطاع كمرة {beam_data.get('id', 'B1')} ({b_mm} × {t_mm} مم) — ECP 203",
        fontsize=12.5, weight="bold", color="#0f172a", y=0.97
    )
    fig.tight_layout()
    return fig


def build_beams_summary_dataframe(beams_list: list) -> pd.DataFrame:
    """
    توليد جدول مخرجات مجمع (Beams Summary Table) كـ DataFrame تفصيلي.
    يتضمن توصيف الركائز (أعمدة / كمرات حاملة) وكانات التعليق الإضافية للكمرات الثانوية.
    """
    rows = []
    for b in beams_list:
        rows.append({
            "كود الكمرة": b.get("id", ""),
            "توصيف الركائز": b.get("supports_desc", "كمرة ساقطة"),
            "البحر الصافي Ln (م)": f"{b.get('clear_span_m', 0.0):.2f}",
            "الأبعاد الخرسانية (b × t مم)": f"{b.get('b_mm', 250)} × {b.get('t_mm', 600)}",
            "التسليح السفلي (الرئيسي)": b.get("rft_btm_str", ""),
            "التسليح العلوي (تعليق كانات)": b.get("rft_top_str", ""),
            "الكانات (القص)": b.get("stirrups_str", ""),
            "كانات التعليق (Hanging)": b.get("hanging_stirrups_str", "—"),
            "حديد الانكماش (Skin RFT)": b.get("skin_rft_str", "—"),
            "عزم الانحناء Mu (t·m)": f"{b.get('Mu_ton_m', 0.0):.2f}",
            "قوة القص Vu (t)": f"{b.get('Vu_ton', 0.0):.2f}",
            "حالة الأمان (Status)": b.get("status", "Safe / OK"),
        })
    return pd.DataFrame(rows)
