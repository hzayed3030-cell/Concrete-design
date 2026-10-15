import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def design_drop_beam(
    p1: list,
    p2: list,
    b_cm: float = 25.0,
    dia_main: int = 16,
    col_w_cm: float = 30.0,
    Fcu: float = 250.0,
    Fy: float = 4000.0,
    Wu_slab: float = 1.45,
    wall_load: float = 0.50,
    ts_cm: float = 20.0,
    beam_id: str = "B1",
    is_continuous: str = "simple",
):
    """
    التصميم الإنشائي الآلي للكمرة الساقطة وفق الكود المصري ECP 203.
    """
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    total_span_m = math.hypot(x2 - x1, y2 - y1)
    
    # حساب طول البحر الصافي Ln
    col_supp_m = col_w_cm / 100.0
    clear_span_m = max(0.5, total_span_m - col_supp_m)
    
    # 1. حساب العمق الأدنى لمقاومة الترخيم وفق الكود المصري
    # بسيطة L/16، مستمرة من طرف L/18.5، مستمرة من طرفين L/21
    if is_continuous == "both_ends":
        t_min_cm = (clear_span_m * 100.0) / 21.0
    elif is_continuous == "one_end":
        t_min_cm = (clear_span_m * 100.0) / 18.5
    else:
        t_min_cm = (clear_span_m * 100.0) / 16.0
        
    # قاعدة التقريب الهندسي: لأقرب 5 سم بالزيادة
    t_cm = math.ceil(t_min_cm / 5.0) * 5.0
    # الحد الأدنى لعمق الكمرة الساقطة (لا يقل عن 40 سم أو ضعفي سمك البلاطة)
    t_cm = max(t_cm, 40.0, math.ceil((2.0 * ts_cm) / 5.0) * 5.0)
    
    b_mm = int(round(b_cm * 10.0))
    t_mm = int(round(t_cm * 10.0))
    d_cm = t_cm - 5.0  # غطاء خرساني 5 سم
    
    # 2. أحمال الكمرة
    # وزن سقوط الكمرة أسفل البلاطة (t - ts)
    w_drop_own = (b_cm / 100.0) * max(0.0, (t_cm - ts_cm) / 100.0) * 2.5 * 1.4
    # حمل الحائط
    w_wall_ult = float(wall_load) * 1.4
    # حمل شريحة البلاطة المحمولة على الكمرة (عرض تقريبي ~ 1.2 م)
    trib_width_m = min(1.5, max(0.8, clear_span_m * 0.25))
    w_slab_ult = float(Wu_slab) * trib_width_m
    w_ult_tot = w_drop_own + w_wall_ult + w_slab_ult
    
    # 3. عزم الانحناء الأقصى Mu
    km = 12.0 if is_continuous == "both_ends" else (10.0 if is_continuous == "one_end" else 8.0)
    Mu_ton_m = (w_ult_tot * (clear_span_m ** 2)) / km
    Mu_kg_cm = Mu_ton_m * 1e5
    
    # 4. التسليح الرئيسي السفلي
    fy_val = float(Fy)
    fcu_val = float(Fcu)
    # ذراع العزم j تقريباً 0.826
    j_val = 0.826
    As_req = Mu_kg_cm / ((fy_val / 1.15) * j_val * d_cm) if d_cm > 0 else 0.0
    
    # الحد الأدنى للتسليح As,min طبقاً للكود
    As_min1 = (0.225 * math.sqrt(fcu_val) / fy_val) * b_cm * d_cm
    As_min2 = (1.1 / fy_val) * b_cm * d_cm
    As_min = max(As_min1, As_min2)
    As_final = max(As_req, As_min)
    
    bar_area_cm2 = math.pi * ((dia_main / 10.0) ** 2) / 4.0
    n_bars_btm = max(2, math.ceil(As_final / bar_area_cm2))
    rft_btm_str = f"{n_bars_btm}Φ{dia_main}"
    
    # 5. التسليح الثانوي العلوي (تعليق كانات)
    As_top = max(0.20 * As_final, 2.0 * (math.pi * 1.2**2 / 4.0))
    n_bars_top = max(2, math.ceil(As_top / (math.pi * 1.2**2 / 4.0)))
    rft_top_str = f"{n_bars_top}Φ12"
    
    # 6. قوى القص والكانات
    Vu_ton = (w_ult_tot * clear_span_m) / 2.0
    Vu_kg = Vu_ton * 1000.0
    qu = Vu_kg / (b_cm * d_cm) if (b_cm * d_cm) > 0 else 0.0
    qcu = 0.24 * math.sqrt(fcu_val / 1.5) * 10.0  # kg/cm²
    
    if qu <= qcu:
        stirrup_n = 5
        stirrups_str = "5Φ8/m (فرعين)"
    else:
        qsu = max(1.0, qu - (qcu / 2.0))
        # مساحة فرعين فاي 8 = 2 * 0.503
        s_cm = (2.0 * 0.503 * (2400.0 / 1.15)) / (b_cm * qsu)
        stirrup_n = min(10, max(5, math.ceil(100.0 / s_cm)))
        stirrups_str = f"{stirrup_n}Φ8/m (فرعين)"
        
    # 7. حديد الانكماش الجانبي (Skin Reinforcement)
    if t_cm >= 90.0:
        skin_rft_str = "4Φ10 لكل جانب"
        n_skin_per_side = 4
    elif t_cm >= 60.0:
        skin_rft_str = "2Φ10 لكل جانب"
        n_skin_per_side = 2
    else:
        skin_rft_str = "—"
        n_skin_per_side = 0
        
    status_str = "Safe / OK"
    
    return {
        "id": beam_id,
        "p1": [x1, y1],
        "p2": [x2, y2],
        "total_span_m": round(total_span_m, 2),
        "clear_span_m": round(clear_span_m, 2),
        "b_cm": b_cm,
        "b_mm": b_mm,
        "t_cm": t_cm,
        "t_mm": t_mm,
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
    }

b = design_drop_beam([0, 0], [5.0, 0], b_cm=25.0, dia_main=16, col_w_cm=30.0)
print("Beam Design Output:")
for k, v in b.items():
    print(f"  {k}: {v}")
