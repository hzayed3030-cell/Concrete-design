"""
Module 10 — Equipment & Liquid Storage Tank Foundations
(تصميم القواعد الإنشائية للمعدات الميكانيكية وخزانات السوائل)
================================================================
ECP 203 - Egyptian Code of Practice / ACI 351.3R / ACI 350 / ACI 318
Comprehensive Structural & Geotechnical Design Module for:
1. Mechanical Equipment Foundations (Static & Dynamic / Vibrating Machinery)
2. Liquid Storage Tank Foundations (Circular & Rectangular, Steel & Plastic)
"""

import io
import math
import base64
import datetime
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
import wave
import struct
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon

from modules import settings as S
from modules.steel_bars import BARS
from modules.report_generator import html_to_pdf_bytes

BAR_WEIGHTS = {b["dia_mm"]: b["weight_kgm"] for b in BARS}
BAR_AREAS = {b["dia_mm"]: b["area_cm2"] for b in BARS}
ECP_DIAMETERS = [10, 12, 16, 18, 20, 22, 25, 28, 32]



# ── GENTLE SOFT WARNING CHIME HELPER ──
@st.cache_data
def _get_siren_wav_base64():
    sample_rate = 16000
    duration = 0.38  # 380 ms short gentle alert
    n_samples = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        phase = 0.0
        for i in range(n_samples):
            t = i / sample_rate
            # 2 soft gentle tones: 520 Hz for first 180ms, then 620 Hz for remaining 200ms
            freq = 520.0 if t < 0.18 else 620.0
            phase += 2.0 * math.pi * freq / sample_rate
            t_note = t if t < 0.18 else (t - 0.18)
            dur_note = 0.18 if t < 0.18 else 0.20
            env = math.sin(math.pi * min(1.0, t_note / dur_note)) ** 1.5
            # Soft, calm amplitude (3500 out of 32767, pleasant and gentle)
            val = int(3500.0 * env * math.sin(phase))
            val = max(-32767, min(32767, val))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def play_siren_alarm():
    """Plays a calm, soft 380ms gentle chime using pure sine waves and low gain."""
    wav_b64 = _get_siren_wav_base64()
    components.html(
        f"""
        <audio id="siren-audio" autoplay style="display:none;">
            <source src="data:audio/wav;base64,{wav_b64}" type="audio/wav">
        </audio>
        <script>
        (function() {{
            try {{
                var AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) {{
                    var ctx = new AudioContext();
                    var playSoft = function() {{
                        var now = ctx.currentTime;
                        var osc = ctx.createOscillator();
                        var gain = ctx.createGain();
                        osc.type = 'sine';  // Pure, soft sine wave (zero harsh distortion)
                        osc.frequency.setValueAtTime(520, now);
                        osc.frequency.setValueAtTime(620, now + 0.18);
                        
                        // Very soft, quiet ambient gain (0.06 instead of 0.35)
                        gain.gain.setValueAtTime(0.01, now);
                        gain.gain.linearRampToValueAtTime(0.06, now + 0.04);
                        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.38);
                        
                        osc.connect(gain);
                        gain.connect(ctx.destination);
                        osc.start(now);
                        osc.stop(now + 0.38);
                    }};
                    if (ctx.state === 'suspended') {{
                        ctx.resume().then(playSoft).catch(function(){{}});
                    }} else {{
                        playSoft();
                    }}
                }} else {{
                    var a = document.getElementById('siren-audio');
                    if (a) {{
                        a.volume = 0.25;
                        a.play().catch(function(){{}});
                    }}
                }}
            }} catch(e) {{
                var a = document.getElementById('siren-audio');
                if (a) {{
                    a.volume = 0.25;
                    a.play().catch(function(){{}});
                }}
            }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

# ===============================================================================
#  1. ENGINEERING COMPUTATION ENGINE — EQUIPMENT FOUNDATIONS (STATIC & DYNAMIC)
# ===============================================================================

def compute_equipment_foundation_T_design(
    Lf_m: float,
    Bf_m: float,
    eq_weight_ton: float,
    eq_shape: str,
    Lm_m: float,
    Bm_m: float,
    is_isolated: bool,
    P_eq_design_ton: float,
    target_mass_ratio: float,
    fc_kg_cm2: float,
    cover_cm: float,
    gamma_c: float = 2.50,
) -> float:
    """
    Computes the minimum code-safe structural thickness (T_design) for Equipment Foundation
    given plan dimensions (Lf, Bf), strictly satisfying:
    1. Code minimum baseline thickness (0.50m for isolated, 0.70m for fixed-base).
    2. Minimum inertia mass ratio (2.0x - 3.0x) for fixed-base dynamic machinery.
    3. ECP 203 punching shear safety (q_up <= q_cup).
    4. ECP 203 one-way beam shear safety (qu_1way <= qcu_1way).
    Returns thickness rounded up to nearest 0.05m (5 cm).
    """
    is_circular_eq = "دائرية" in eq_shape or "Circular" in eq_shape
    Af_m2 = max(float(Lf_m) * float(Bf_m), 0.10)

    # 1. Baseline rigidity & mass requirement
    if is_isolated:
        t_cand = 0.50
    else:
        clamped_ratio = max(2.0, min(3.0, float(target_mass_ratio)))
        req_min_wf_ton = float(eq_weight_ton) * clamped_ratio
        req_vol_m3 = req_min_wf_ton / gamma_c
        t_mass = req_vol_m3 / Af_m2
        t_cand = max(0.70, math.ceil(t_mass * 20.0) / 20.0)

    # 2. Iterative shear & punching convergence loop
    fcu_mpa = float(fc_kg_cm2) / 10.0
    gamma_c_mat = 1.50
    Pu_eq_ton = 1.50 * float(P_eq_design_ton)
    qu_net_ton_m2 = Pu_eq_ton / Af_m2
    alpha_col = 4.0

    for _ in range(60):
        t_cand = math.ceil(t_cand * 20.0) / 20.0
        d_cm = max(t_cand * 100.0 - float(cover_cm), 10.0)
        d_m = d_cm / 100.0

        if is_circular_eq:
            bo_m = math.pi * (Lm_m + d_m)
            area_punch_m2 = (math.pi / 4.0) * ((Lm_m + d_m) ** 2)
            q_cup_all = min(0.316 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0, 16.0)
        else:
            bo_m = 2.0 * ((Lm_m + d_m) + (Bm_m + d_m))
            area_punch_m2 = (Lm_m + d_m) * (Bm_m + d_m)
            beta_c = min(Lm_m, Bm_m) / max(Lm_m, Bm_m, 0.01)
            q_cup_1 = 0.80 * ((alpha_col * d_cm / (bo_m * 100.0)) + 0.20) * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
            q_cup_2 = 0.316 * (0.50 + beta_c) * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
            q_cup_3 = 0.316 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
            q_cup_all = min(q_cup_1, q_cup_2, q_cup_3, 16.0)

        Q_up_ton = max(0.0, Pu_eq_ton - qu_net_ton_m2 * min(area_punch_m2, Af_m2))
        q_up_kg_cm2 = (Q_up_ton * 1000.0) / (bo_m * 100.0 * d_cm)

        # One-way beam shear check
        cant_L_m = max(0.0, (float(Lf_m) - Lm_m) / 2.0)
        cant_B_m = max(0.0, (float(Bf_m) - Bm_m) / 2.0)
        crit_shear_arm_m = max(0.0, max(cant_L_m, cant_B_m) - d_m)
        Qu_1way_ton_m = qu_net_ton_m2 * crit_shear_arm_m
        qu_1way_kg_cm2 = (Qu_1way_ton_m * 1000.0) / (100.0 * d_cm)
        qcu_1way_kg_cm2 = 0.16 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0

        if (q_up_kg_cm2 > q_cup_all) or (qu_1way_kg_cm2 > qcu_1way_kg_cm2):
            t_cand = round(t_cand + 0.05, 2)
            continue
        break

    return round(t_cand, 2)


def compute_equipment_foundation_auto_dimensions(
    eq_weight_ton: float,
    eq_shape: str,
    eq_length_m: float,
    eq_width_m: float,
    eq_dia_m: float,
    isolation_type: str,
    target_mass_ratio: float,
    q_all_kg_cm2: float,
    fc_kg_cm2: float,
    cover_cm: float,
) -> tuple:
    """
    Computes auto-sized plan dimensions (Lf, Bf) and corresponding code-safe design
    thickness T_design for equipment foundation.
    """
    gamma_c = 2.50
    q_all_ton_m2 = float(q_all_kg_cm2) * 10.0

    is_circular_eq = "دائرية" in eq_shape or "Circular" in eq_shape
    is_fixed_base = "عدم وجود" in isolation_type or "Fixed Base" in isolation_type
    is_isolated = not is_fixed_base

    if is_circular_eq:
        Lm_m = max(float(eq_dia_m), 0.20)
        Bm_m = max(float(eq_dia_m), 0.20)
    else:
        Lm_m = max(float(eq_length_m), 0.20)
        Bm_m = max(float(eq_width_m), 0.20)

    min_clearance_m = 0.40
    min_Lf = round(Lm_m + 2.0 * min_clearance_m, 2)
    min_Bf = round(Bm_m + 2.0 * min_clearance_m, 2)

    if is_isolated:
        dyn_factor = 1.20
        P_eq_design_ton = float(eq_weight_ton) * dyn_factor
        req_min_wf_ton = 0.0
    else:
        dyn_factor = 1.50
        P_eq_design_ton = float(eq_weight_ton) * dyn_factor
        clamped_ratio = max(2.0, min(3.0, float(target_mass_ratio)))
        req_min_wf_ton = float(eq_weight_ton) * clamped_ratio

    Lf_m = max(min_Lf, 1.20)
    Bf_m = max(min_Bf, 1.20)
    tf_m = 0.50 if is_isolated else 0.70

    if not is_isolated:
        req_vol_m3 = req_min_wf_ton / gamma_c
        current_vol = Lf_m * Bf_m * tf_m
        if current_vol < req_vol_m3:
            scale_3d = (req_vol_m3 / max(current_vol, 0.01)) ** (1.0 / 3.0)
            Lf_m = math.ceil((Lf_m * scale_3d) * 20.0) / 20.0
            Bf_m = math.ceil((Bf_m * scale_3d) * 20.0) / 20.0
            tf_m = math.ceil((req_vol_m3 / (Lf_m * Bf_m)) * 20.0) / 20.0
            tf_m = max(tf_m, 0.60)

    for _ in range(50):
        vol_f = Lf_m * Bf_m * tf_m
        Wf_ton = vol_f * gamma_c
        P_total_working = P_eq_design_ton + Wf_ton
        Af_m2 = Lf_m * Bf_m
        q_act_ton_m2 = P_total_working / Af_m2

        if q_act_ton_m2 > q_all_ton_m2:
            Lf_m = round(Lf_m + 0.15, 2)
            Bf_m = round(Bf_m + 0.15, 2)
            continue

        d_cm = max(tf_m * 100.0 - float(cover_cm), 15.0)
        d_m = d_cm / 100.0
        if is_circular_eq:
            bo_m = math.pi * (Lm_m + d_m)
            area_punch_m2 = (math.pi / 4.0) * ((Lm_m + d_m) ** 2)
        else:
            bo_m = 2.0 * ((Lm_m + d_m) + (Bm_m + d_m))
            area_punch_m2 = (Lm_m + d_m) * (Bm_m + d_m)

        Pu_eq_ton = 1.50 * P_eq_design_ton
        qu_net_ton_m2 = Pu_eq_ton / Af_m2
        Q_up_ton = max(0.0, Pu_eq_ton - qu_net_ton_m2 * min(area_punch_m2, Af_m2))
        q_up_kg_cm2 = (Q_up_ton * 1000.0) / (bo_m * 100.0 * d_cm)

        fcu_mpa = float(fc_kg_cm2) / 10.0
        q_cup_kg_cm2 = min(0.316 * math.sqrt(fcu_mpa / 1.50) * 10.0, 16.0)

        if q_up_kg_cm2 > q_cup_kg_cm2:
            tf_m = round(tf_m + 0.05, 2)
            continue

        break

    T_design = compute_equipment_foundation_T_design(
        Lf_m=Lf_m,
        Bf_m=Bf_m,
        eq_weight_ton=eq_weight_ton,
        eq_shape=eq_shape,
        Lm_m=Lm_m,
        Bm_m=Bm_m,
        is_isolated=is_isolated,
        P_eq_design_ton=P_eq_design_ton,
        target_mass_ratio=target_mass_ratio,
        fc_kg_cm2=fc_kg_cm2,
        cover_cm=cover_cm,
        gamma_c=gamma_c,
    )
    return (round(Lf_m, 2), round(Bf_m, 2), max(round(tf_m, 2), T_design))


def compute_equipment_foundation_design(
    eq_weight_ton: float = 15.0,
    eq_shape: str = "مستطيلة (Rectangular)",
    eq_length_m: float = 2.50,
    eq_width_m: float = 1.50,
    eq_dia_m: float = 2.00,
    isolation_type: str = "وجود نظام عزل اهتزازات (Springs & Isolators)",
    operating_rpm: float = 1500.0,
    ks_kg_cm3: float = 4.0,
    fc_kg_cm2: float = 300.0,
    fy_kg_cm2: float = 3600.0,
    q_all_kg_cm2: float = 1.50,
    sizing_mode: str = "حساب أوتوماتيكي للأبعاد (Auto-Sizing)",
    manual_Lf_m: float = 3.50,
    manual_Bf_m: float = 2.50,
    manual_tf_m: float = None,
    target_mass_ratio: float = 2.50,
    cover_cm: float = 7.5,
    phi_bot_mm: int = 16,
    phi_top_mm: int = 12,
) -> dict:
    """
    Executes full structural, geotechnical, and dynamic vibration design for
    Mechanical Equipment Foundations according to ECP 203 & ACI 351.3R.
    """
    gamma_c = 2.50  # ton/m³ (Reinforced Concrete Density)
    q_all_ton_m2 = q_all_kg_cm2 * 10.0  # 1 kg/cm² = 10 ton/m²

    is_circular_eq = "دائرية" in eq_shape or "Circular" in eq_shape
    is_fixed_base = "عدم وجود" in isolation_type or "Fixed Base" in isolation_type
    is_isolated = not is_fixed_base

    if is_circular_eq:
        Lm_m = max(eq_dia_m, 0.20)
        Bm_m = max(eq_dia_m, 0.20)
    else:
        Lm_m = max(eq_length_m, 0.20)
        Bm_m = max(eq_width_m, 0.20)

    # Clearance around equipment footprint (min 0.30m to 0.50m per side)
    min_clearance_m = 0.40
    min_Lf = round(Lm_m + 2.0 * min_clearance_m, 2)
    min_Bf = round(Bm_m + 2.0 * min_clearance_m, 2)

    # Dynamic Factor & Target Mass Ratio Logic
    if is_isolated:
        dyn_factor = 1.20
        P_eq_design_ton = eq_weight_ton * dyn_factor
        req_min_wf_ton = 0.0  # Governed by geometry, soil & punching
    else:
        # Fixed Base (No isolation): Concrete weight must be 2.0 to 3.0 times equipment weight
        dyn_factor = 1.50  # Dynamic impact amplification for non-isolated strength check
        P_eq_design_ton = eq_weight_ton * dyn_factor
        clamped_ratio = max(2.0, min(3.0, target_mass_ratio))
        req_min_wf_ton = eq_weight_ton * clamped_ratio

    # Determine Foundation Dimensions (Lf, Bf, tf) and Safe Design Thickness (T_design)
    if "Auto" in sizing_mode or "أوتوماتيكي" in sizing_mode:
        auto_Lf, auto_Bf, T_design = compute_equipment_foundation_auto_dimensions(
            eq_weight_ton=eq_weight_ton,
            eq_shape=eq_shape,
            eq_length_m=eq_length_m,
            eq_width_m=eq_width_m,
            eq_dia_m=eq_dia_m,
            isolation_type=isolation_type,
            target_mass_ratio=target_mass_ratio,
            q_all_kg_cm2=q_all_kg_cm2,
            fc_kg_cm2=fc_kg_cm2,
            cover_cm=cover_cm,
        )
        Lf_m = auto_Lf
        Bf_m = auto_Bf
        if manual_tf_m is not None and float(manual_tf_m) >= T_design - 1e-4:
            tf_m = round(float(manual_tf_m), 2)
        else:
            tf_m = T_design
    else:
        Lf_m = max(float(manual_Lf_m), 0.50)
        Bf_m = max(float(manual_Bf_m), 0.50)
        T_design = compute_equipment_foundation_T_design(
            Lf_m=Lf_m,
            Bf_m=Bf_m,
            eq_weight_ton=eq_weight_ton,
            eq_shape=eq_shape,
            Lm_m=Lm_m,
            Bm_m=Bm_m,
            is_isolated=is_isolated,
            P_eq_design_ton=P_eq_design_ton,
            target_mass_ratio=target_mass_ratio,
            fc_kg_cm2=fc_kg_cm2,
            cover_cm=cover_cm,
            gamma_c=gamma_c,
        )
        if manual_tf_m is not None and float(manual_tf_m) >= T_design - 1e-4:
            tf_m = round(float(manual_tf_m), 2)
        else:
            tf_m = T_design

    # Final Geometry & Self-Weight Automatic Calculation
    Af_m2 = Lf_m * Bf_m
    vol_f_m3 = Af_m2 * tf_m
    Wf_ton = vol_f_m3 * gamma_c  # Automatic Self-Weight (2.5 t/m³)
    actual_mass_ratio = Wf_ton / max(eq_weight_ton, 0.01)

    if is_isolated:
        is_mass_ratio_safe = True
        req_mass_ratio_min = 0.0
    else:
        req_mass_ratio_min = 2.0
        is_mass_ratio_safe = actual_mass_ratio >= 1.999

    # Total Working & Ultimate Loads
    P_total_working_ton = P_eq_design_ton + Wf_ton
    Pu_total_ton = 1.40 * Wf_ton + 1.50 * P_eq_design_ton
    Pu_net_ton = 1.50 * P_eq_design_ton  # Net upward pressure causing bending/shear

    # 1. Soil Bearing Check
    q_act_ton_m2 = P_total_working_ton / Af_m2
    q_act_kg_cm2 = q_act_ton_m2 / 10.0
    ratio_soil = q_act_kg_cm2 / max(q_all_kg_cm2, 0.01)
    is_soil_safe = ratio_soil <= 1.0001

    # 2. Natural Frequency & Resonance Check (ACI 351.3R / Richart-Whitman)
    # Spring constant of soil Kz = ks * Af
    # ks in kg/cm³ -> 1 kg/cm³ = 1000 ton/m³
    ks_ton_m3 = ks_kg_cm3 * 1000.0
    Kz_ton_m = ks_ton_m3 * Af_m2
    Kz_N_m = Kz_ton_m * 9806.65
    total_mass_kg = ((eq_weight_ton + Wf_ton) * 1000.0)
    omega_n_rad_s = math.sqrt(Kz_N_m / max(total_mass_kg, 1.0))
    fn_hz = omega_n_rad_s / (2.0 * math.pi)
    f_op_hz = operating_rpm / 60.0
    freq_ratio = f_op_hz / max(fn_hz, 0.01)

    # Resonance band is 0.70 <= f_op / fn <= 1.30 for fixed-base foundations
    if is_isolated:
        # With springs & isolators (tuned low natural frequency), isolation efficiency > 85%
        is_resonance_safe = True
        resonance_status_ar = "آمن (معزول بديناميكية نوابض وعوازل)"
    else:
        is_resonance_safe = (freq_ratio < 0.70) or (freq_ratio > 1.30)
        if is_resonance_safe:
            resonance_status_ar = f"آمن ضد الرنين (r = {freq_ratio:.2f} خارج نطاق 0.7–1.3)"
        else:
            resonance_status_ar = f"⚠️ خطر رنين ديناميكي (r = {freq_ratio:.2f} ضمن النطاق الحرج 0.7–1.3)"

    # 3. Punching Shear & One-Way Shear Checks (ECP 203)
    d_cm = max(tf_m * 100.0 - cover_cm, 10.0)
    d_m = d_cm / 100.0
    fcu_mpa = fc_kg_cm2 / 10.0
    gamma_c_mat = 1.50
    gamma_s_mat = 1.15

    if is_circular_eq:
        bo_m = math.pi * (Lm_m + d_m)
        area_punch_m2 = (math.pi / 4.0) * ((Lm_m + d_m) ** 2)
    else:
        bo_m = 2.0 * ((Lm_m + d_m) + (Bm_m + d_m))
        area_punch_m2 = (Lm_m + d_m) * (Bm_m + d_m)

    qu_net_ton_m2 = Pu_net_ton / Af_m2
    Q_up_ton = max(0.0, Pu_net_ton - qu_net_ton_m2 * min(area_punch_m2, Af_m2))
    q_up_kg_cm2 = (Q_up_ton * 1000.0) / (bo_m * 100.0 * d_cm)

    # ECP 203 Allowable Concrete Punching Shear Stress
    alpha_col = 4.0
    q_cup_1 = 0.80 * ((alpha_col * d_cm / (bo_m * 100.0)) + 0.20) * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    if is_circular_eq:
        q_cup_2 = 0.316 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    else:
        beta_c = min(Lm_m, Bm_m) / max(Lm_m, Bm_m)
        q_cup_2 = 0.316 * (0.50 + beta_c) * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    q_cup_3 = 0.316 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    q_cup_all_kg_cm2 = min(q_cup_1, q_cup_2, q_cup_3, 16.0)

    ratio_punching = q_up_kg_cm2 / max(q_cup_all_kg_cm2, 0.01)
    is_punching_safe = ratio_punching <= 1.0001

    # One-Way Shear Check
    cant_L_m = max(0.0, (Lf_m - Lm_m) / 2.0)
    cant_B_m = max(0.0, (Bf_m - Bm_m) / 2.0)
    crit_shear_arm_m = max(0.0, max(cant_L_m, cant_B_m) - d_m)
    Qu_1way_ton_m = qu_net_ton_m2 * crit_shear_arm_m
    qu_1way_kg_cm2 = (Qu_1way_ton_m * 1000.0) / (100.0 * d_cm)
    qcu_1way_kg_cm2 = 0.16 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    ratio_1way_shear = qu_1way_kg_cm2 / max(qcu_1way_kg_cm2, 0.01)
    is_1way_shear_safe = ratio_1way_shear <= 1.0001

    # 4. Flexural Design & Reinforcement (Bottom & Top Meshes per ECP 203 / ACI)
    # Bottom reinforcement: Cantilever moment under net upward soil reaction
    Mu_bot_L_tm = qu_net_ton_m2 * (cant_L_m ** 2) / 2.0
    Mu_bot_B_tm = qu_net_ton_m2 * (cant_B_m ** 2) / 2.0
    Mu_bot_max_tm = max(Mu_bot_L_tm, Mu_bot_B_tm, 1.50)

    # Top reinforcement: Dynamic reversal / shrinkage / thermal / uplift moment (min 50% of bottom or shrinkage)
    Mu_top_max_tm = max(0.50 * Mu_bot_max_tm, 1.0)

    j_factor = 0.826
    fy_design = fy_kg_cm2 / gamma_s_mat

    As_bot_flex_cm2_m = (Mu_bot_max_tm * 1e5) / (fy_design * j_factor * d_cm)
    As_top_flex_cm2_m = (Mu_top_max_tm * 1e5) / (fy_design * j_factor * d_cm)

    # Minimum Reinforcement per ECP 203 (0.15% of d or 1.5/fy * b * d, min 5Φ12/m)
    As_min_ecp_cm2_m = max(0.0015 * 100.0 * d_cm, (0.60 / (fy_kg_cm2 / 10.0)) * 100.0 * d_cm, 5.65)
    # Top mesh minimum for dynamic/massive equipment foundations (shrinkage & vibration crack control)
    As_min_top_cm2_m = max(0.0012 * 100.0 * d_cm, 5.65)

    As_bot_req_cm2_m = max(As_bot_flex_cm2_m, As_min_ecp_cm2_m)
    As_top_req_cm2_m = max(As_top_flex_cm2_m, As_min_top_cm2_m)

    area_bar_bot = BAR_AREAS.get(phi_bot_mm, (math.pi * (phi_bot_mm / 10.0) ** 2) / 4.0)
    area_bar_top = BAR_AREAS.get(phi_top_mm, (math.pi * (phi_top_mm / 10.0) ** 2) / 4.0)

    n_bars_bot_m = max(5, math.ceil(As_bot_req_cm2_m / area_bar_bot))
    n_bars_top_m = max(5, math.ceil(As_top_req_cm2_m / area_bar_top))

    spacing_bot_cm = round(100.0 / n_bars_bot_m, 1)
    spacing_top_cm = round(100.0 / n_bars_top_m, 1)

    As_bot_prov_cm2_m = n_bars_bot_m * area_bar_bot
    As_top_prov_cm2_m = n_bars_top_m * area_bar_top

    # Total Steel Quantities (Bottom X+Y + Top X+Y + Side Dowels/Stirrups)
    wt_bar_bot_kg_m = BAR_WEIGHTS.get(phi_bot_mm, (phi_bot_mm ** 2) / 162.0)
    wt_bar_top_kg_m = BAR_WEIGHTS.get(phi_top_mm, (phi_top_mm ** 2) / 162.0)

    # Length of bars including U-legs (2 * (tf - 2*cover))
    u_leg_m = max(0.20, tf_m - 2.0 * (cover_cm / 100.0))
    len_bar_L_m = Lf_m - 2.0 * (cover_cm / 100.0) + 2.0 * u_leg_m
    len_bar_B_m = Bf_m - 2.0 * (cover_cm / 100.0) + 2.0 * u_leg_m

    total_bars_bot_L = math.ceil(n_bars_bot_m * Bf_m) + 1
    total_bars_bot_B = math.ceil(n_bars_bot_m * Lf_m) + 1
    weight_bot_kg = (total_bars_bot_L * len_bar_L_m + total_bars_bot_B * len_bar_B_m) * wt_bar_bot_kg_m

    total_bars_top_L = math.ceil(n_bars_top_m * Bf_m) + 1
    total_bars_top_B = math.ceil(n_bars_top_m * Lf_m) + 1
    weight_top_kg = (total_bars_top_L * len_bar_L_m + total_bars_top_B * len_bar_B_m) * wt_bar_top_kg_m

    total_rebar_weight_kg = (weight_bot_kg + weight_top_kg) * 1.05  # +5% side shrinkage bars & chairs
    total_rebar_weight_ton = total_rebar_weight_kg / 1000.0
    steel_rate_kg_m3 = total_rebar_weight_kg / max(vol_f_m3, 0.01)

    # Geometric Footprint & Edge Clearance Safety Check
    clearance_L_m = (Lf_m - Lm_m) / 2.0
    clearance_B_m = (Bf_m - Bm_m) / 2.0
    is_footprint_safe = (Lf_m >= Lm_m - 0.001) and (Bf_m >= Bm_m - 0.001)
    is_clearance_safe = (clearance_L_m >= 0.20 - 0.001) and (clearance_B_m >= 0.20 - 0.001)

    is_all_safe = (
        is_footprint_safe
        and is_soil_safe
        and is_punching_safe
        and is_1way_shear_safe
        and is_mass_ratio_safe
        and is_resonance_safe
    )

    return {
        "eq_weight_ton": eq_weight_ton,
        "eq_shape": eq_shape,
        "is_circular_eq": is_circular_eq,
        "Lm_m": Lm_m,
        "Bm_m": Bm_m,
        "isolation_type": isolation_type,
        "is_isolated": is_isolated,
        "operating_rpm": operating_rpm,
        "ks_kg_cm3": ks_kg_cm3,
        "fc_kg_cm2": fc_kg_cm2,
        "fy_kg_cm2": fy_kg_cm2,
        "q_all_kg_cm2": q_all_kg_cm2,
        "q_all_ton_m2": q_all_ton_m2,
        "sizing_mode": sizing_mode,
        "Lf_m": Lf_m,
        "Bf_m": Bf_m,
        "tf_m": tf_m,
        "T_design": T_design,
        "T_design_m": T_design,
        "T_design_cm": round(T_design * 100.0, 1),
        "is_tf_overridden": bool(tf_m > T_design + 1e-4),
        "tf_cm": tf_m * 100.0,
        "d_cm": d_cm,
        "cover_cm": cover_cm,
        "Af_m2": Af_m2,
        "vol_f_m3": vol_f_m3,
        "Wf_ton": Wf_ton,
        "dyn_factor": dyn_factor,
        "P_eq_design_ton": P_eq_design_ton,
        "P_total_working_ton": P_total_working_ton,
        "Pu_total_ton": Pu_total_ton,
        "Pu_net_ton": Pu_net_ton,
        "actual_mass_ratio": actual_mass_ratio,
        "req_mass_ratio_min": req_mass_ratio_min,
        "req_min_wf_ton": req_min_wf_ton,
        "is_mass_ratio_safe": is_mass_ratio_safe,
        "q_act_ton_m2": q_act_ton_m2,
        "q_act_kg_cm2": q_act_kg_cm2,
        "ratio_soil": ratio_soil,
        "is_soil_safe": is_soil_safe,
        "fn_hz": fn_hz,
        "f_op_hz": f_op_hz,
        "freq_ratio": freq_ratio,
        "is_resonance_safe": is_resonance_safe,
        "resonance_status_ar": resonance_status_ar,
        "bo_m": bo_m,
        "Q_up_ton": Q_up_ton,
        "q_up_kg_cm2": q_up_kg_cm2,
        "q_cup_all_kg_cm2": q_cup_all_kg_cm2,
        "ratio_punching": ratio_punching,
        "is_punching_safe": is_punching_safe,
        "Qu_1way_ton_m": Qu_1way_ton_m,
        "qu_1way_kg_cm2": qu_1way_kg_cm2,
        "qcu_1way_kg_cm2": qcu_1way_kg_cm2,
        "ratio_1way_shear": ratio_1way_shear,
        "is_1way_shear_safe": is_1way_shear_safe,
        "Mu_bot_max_tm": Mu_bot_max_tm,
        "Mu_top_max_tm": Mu_top_max_tm,
        "As_bot_req_cm2_m": As_bot_req_cm2_m,
        "As_top_req_cm2_m": As_top_req_cm2_m,
        "phi_bot_mm": phi_bot_mm,
        "phi_top_mm": phi_top_mm,
        "n_bars_bot_m": n_bars_bot_m,
        "n_bars_top_m": n_bars_top_m,
        "spacing_bot_cm": spacing_bot_cm,
        "spacing_top_cm": spacing_top_cm,
        "As_bot_prov_cm2_m": As_bot_prov_cm2_m,
        "As_top_prov_cm2_m": As_top_prov_cm2_m,
        "weight_bot_kg": weight_bot_kg,
        "weight_top_kg": weight_top_kg,
        "total_rebar_weight_kg": total_rebar_weight_kg,
        "total_rebar_weight_ton": total_rebar_weight_ton,
        "steel_rate_kg_m3": steel_rate_kg_m3,
        "is_footprint_safe": is_footprint_safe,
        "is_clearance_safe": is_clearance_safe,
        "clearance_L_cm": round(clearance_L_m * 100.0, 1),
        "clearance_B_cm": round(clearance_B_m * 100.0, 1),
        "min_req_Lf_m": round(Lm_m, 2),
        "min_req_Bf_m": round(Bm_m, 2),
        "is_all_safe": is_all_safe,
    }


# ===============================================================================
#  2. ENGINEERING COMPUTATION ENGINE — LIQUID STORAGE TANK FOUNDATIONS
# ===============================================================================

def compute_liquid_tank_foundation_design(
    tank_shape: str = "دائري (Circular)",
    tank_dia_m: float = 6.00,
    tank_length_m: float = 6.00,
    tank_width_m: float = 4.00,
    tank_material: str = "صاج صلب (Steel Sheet)",
    sheet_thk_mm: float = 8.0,
    capacity_barrels: float = 1000.0,
    specific_gravity: float = 0.85,
    fc_kg_cm2: float = 300.0,
    fy_kg_cm2: float = 3600.0,
    q_all_kg_cm2: float = 1.50,
    sizing_mode: str = "حساب أوتوماتيكي للأبعاد (Auto-Sizing)",
    manual_overhang_m: float = 0.60,
    manual_tf_m: float = 0.60,
    gwt_depth_m: float = 1.00,
    wind_seismic_coeff: float = 0.08,
    cover_cm: float = 7.5,
    phi_bot_mm: int = 16,
    phi_top_mm: int = 12,
) -> dict:
    """
    Executes full structural, hydrostatic, buoyancy, overturning, punching shear,
    and reinforcement design for Liquid Storage Tank Foundations per ECP 203 / ACI 350.
    """
    gamma_c = 2.50  # ton/m³ (Reinforced Concrete Density - Mandatory)
    gamma_water = 1.00  # ton/m³
    q_all_ton_m2 = q_all_kg_cm2 * 10.0

    is_circular = "دائري" in tank_shape or "Circular" in tank_shape
    is_steel = "صاج" in tank_material or "Steel" in tank_material

    # 1 Barrel (US Oil Barrel) = 42 US Gallons = 158.9873 Liters = 0.1589873 m³
    BBL_TO_M3 = 0.1589873
    vol_liquid_m3 = capacity_barrels * BBL_TO_M3
    gamma_liquid_ton_m3 = specific_gravity * gamma_water
    W_liquid_ton = vol_liquid_m3 * gamma_liquid_ton_m3

    # Tank Plan Area & Effective Liquid Height
    if is_circular:
        D_tank_m = max(tank_dia_m, 0.50)
        L_tank_m = D_tank_m
        B_tank_m = D_tank_m
        A_tank_m2 = (math.pi / 4.0) * (D_tank_m ** 2)
        perimeter_tank_m = math.pi * D_tank_m
    else:
        L_tank_m = max(tank_length_m, 0.50)
        B_tank_m = max(tank_width_m, 0.50)
        D_tank_m = max(L_tank_m, B_tank_m)
        A_tank_m2 = L_tank_m * B_tank_m
        perimeter_tank_m = 2.0 * (L_tank_m + B_tank_m)

    H_liquid_m = vol_liquid_m3 / max(A_tank_m2, 0.01)
    freeboard_m = max(0.30, 0.10 * H_liquid_m)
    H_tank_total_m = H_liquid_m + freeboard_m

    # Tank Structure Empty Self-Weight Calculation (Automatic based on Material, Dimensions & Thickness)
    # Total Surface Area = Bottom Floor + Side Shell Wall + Roof Cover (with 15% stiffeners/nozzles allowance)
    area_shell_m2 = perimeter_tank_m * H_tank_total_m
    area_total_plates_m2 = (2.0 * A_tank_m2 + area_shell_m2) * 1.15
    thk_m = max(sheet_thk_mm, 1.0) / 1000.0
    if is_steel:
        gamma_mat_ton_m3 = 7.85  # Steel density = 7.85 ton/m³
    else:
        gamma_mat_ton_m3 = 1.40  # High-density Polyethylene / GRP Plastic = 1.40 ton/m³

    W_tank_empty_ton = area_total_plates_m2 * thk_m * gamma_mat_ton_m3

    # Hydrostatic Pressure on Tank Base
    p_hydrostatic_ton_m2 = gamma_liquid_ton_m3 * H_liquid_m
    p_hydrostatic_kg_cm2 = p_hydrostatic_ton_m2 / 10.0

    # Auto-Sizing or Manual Foundation Dimensions
    if "Auto" in sizing_mode or "أوتوماتيكي" in sizing_mode:
        overhang_m = 0.50
        tf_m = 0.50

        for _ in range(45):
            if is_circular:
                Df_m = D_tank_m + 2.0 * overhang_m
                Lf_m = Df_m
                Bf_m = Df_m
                Af_m2 = (math.pi / 4.0) * (Df_m ** 2)
            else:
                Lf_m = L_tank_m + 2.0 * overhang_m
                Bf_m = B_tank_m + 2.0 * overhang_m
                Df_m = Lf_m
                Af_m2 = Lf_m * Bf_m

            vol_f_m3 = Af_m2 * tf_m
            Wf_ton = vol_f_m3 * gamma_c  # Mandatory Self-Weight (2.5 t/m³)
            P_total_working = W_tank_empty_ton + W_liquid_ton + Wf_ton
            q_act_ton_m2 = P_total_working / Af_m2

            # 1. Check Soil Bearing
            if q_act_ton_m2 > q_all_ton_m2:
                overhang_m = round(overhang_m + 0.10, 2)
                continue

            # 2. Check Buoyancy (Uplift when Tank is Empty & submerged by gwt_depth_m)
            U_buoyancy_ton = Af_m2 * max(0.0, gwt_depth_m) * gamma_water
            W_resisting_uplift = W_tank_empty_ton + Wf_ton
            fos_buoyancy = W_resisting_uplift / max(U_buoyancy_ton, 0.01) if U_buoyancy_ton > 0 else 99.9
            if U_buoyancy_ton > 0 and fos_buoyancy < 1.25:
                tf_m = round(tf_m + 0.05, 2)
                continue

            # 3. Check Punching Shear under Shell / Tank Footprint
            d_cm = max(tf_m * 100.0 - cover_cm, 15.0)
            d_m = d_cm / 100.0
            if is_circular:
                bo_m = math.pi * (D_tank_m + d_m)
                area_punch_m2 = (math.pi / 4.0) * ((D_tank_m + d_m) ** 2)
            else:
                bo_m = 2.0 * ((L_tank_m + d_m) + (B_tank_m + d_m))
                area_punch_m2 = (L_tank_m + d_m) * (B_tank_m + d_m)

            Pu_tank_liq_ton = 1.40 * W_tank_empty_ton + 1.50 * W_liquid_ton
            qu_net_ton_m2 = Pu_tank_liq_ton / Af_m2
            Q_up_ton = max(0.0, Pu_tank_liq_ton - qu_net_ton_m2 * min(area_punch_m2, Af_m2))
            q_up_kg_cm2 = (Q_up_ton * 1000.0) / (bo_m * 100.0 * d_cm)

            fcu_mpa = fc_kg_cm2 / 10.0
            q_cup_all_kg_cm2 = min(0.316 * math.sqrt(fcu_mpa / 1.50) * 10.0, 16.0)
            if q_up_kg_cm2 > q_cup_all_kg_cm2:
                tf_m = round(tf_m + 0.05, 2)
                continue

            break
    else:
        overhang_m = max(manual_overhang_m, 0.15)
        tf_m = max(manual_tf_m, 0.25)

    # Final Geometry & Mandatory Foundation Self-Weight Calculation
    if is_circular:
        Df_m = round(D_tank_m + 2.0 * overhang_m, 2)
        Lf_m = Df_m
        Bf_m = Df_m
        Af_m2 = (math.pi / 4.0) * (Df_m ** 2)
        If_m4 = (math.pi / 64.0) * (Df_m ** 4)
        c_edge_m = Df_m / 2.0
    else:
        Lf_m = round(L_tank_m + 2.0 * overhang_m, 2)
        Bf_m = round(B_tank_m + 2.0 * overhang_m, 2)
        Df_m = Lf_m
        Af_m2 = Lf_m * Bf_m
        # Bending about shorter axis Bf_m for conservative overturning check
        B_gov_m = min(Lf_m, Bf_m)
        L_gov_m = max(Lf_m, Bf_m)
        If_m4 = (L_gov_m * (B_gov_m ** 3)) / 12.0
        c_edge_m = B_gov_m / 2.0

    vol_f_m3 = Af_m2 * tf_m
    Wf_ton = vol_f_m3 * gamma_c  # Mandatory Self-Weight = V_f * 2.5 ton/m³

    # Total Working & Ultimate Loads (Tank + Liquid + Foundation Self-Weight)
    P_total_working_ton = W_tank_empty_ton + W_liquid_ton + Wf_ton
    Pu_total_ton = 1.40 * (W_tank_empty_ton + Wf_ton) + 1.50 * W_liquid_ton
    Pu_net_ton = 1.40 * W_tank_empty_ton + 1.50 * W_liquid_ton

    # Stability against Overturning (Wind / Seismic Lateral Force)
    V_lateral_ton = wind_seismic_coeff * (W_tank_empty_ton + W_liquid_ton)
    lever_arm_m = 0.50 * H_liquid_m + tf_m
    M_overturning_tm = V_lateral_ton * lever_arm_m

    # Resisting Moment about toe
    M_resisting_full_tm = P_total_working_ton * c_edge_m
    fos_overturning = M_resisting_full_tm / max(M_overturning_tm, 0.01)
    is_overturning_safe = fos_overturning >= 1.50

    # Stability against Buoyancy / Uplift (Empty Tank + Groundwater Head)
    U_buoyancy_ton = Af_m2 * max(0.0, gwt_depth_m) * gamma_water
    W_empty_total_ton = W_tank_empty_ton + Wf_ton
    fos_buoyancy = W_empty_total_ton / max(U_buoyancy_ton, 0.01) if U_buoyancy_ton > 0 else 99.9
    is_buoyancy_safe = fos_buoyancy >= 1.25

    # Soil Bearing Stress Check (Direct + Eccentricity from Overturning Moment)
    q_avg_ton_m2 = P_total_working_ton / Af_m2
    q_moment_ton_m2 = (M_overturning_tm * c_edge_m) / max(If_m4, 0.01)
    q_max_ton_m2 = q_avg_ton_m2 + q_moment_ton_m2
    q_min_ton_m2 = q_avg_ton_m2 - q_moment_ton_m2

    q_max_kg_cm2 = q_max_ton_m2 / 10.0
    q_min_kg_cm2 = q_min_ton_m2 / 10.0
    ratio_soil = q_max_kg_cm2 / max(q_all_kg_cm2, 0.01)
    is_soil_safe = (ratio_soil <= 1.0001) and (q_min_kg_cm2 >= 0.0)

    # Punching Shear & One-Way Shear Checks (ECP 203)
    d_cm = max(tf_m * 100.0 - cover_cm, 10.0)
    d_m = d_cm / 100.0
    fcu_mpa = fc_kg_cm2 / 10.0
    gamma_c_mat = 1.50
    gamma_s_mat = 1.15

    if is_circular:
        bo_m = math.pi * (D_tank_m + d_m)
        area_punch_m2 = (math.pi / 4.0) * ((D_tank_m + d_m) ** 2)
    else:
        bo_m = 2.0 * ((L_tank_m + d_m) + (B_tank_m + d_m))
        area_punch_m2 = (L_tank_m + d_m) * (B_tank_m + d_m)

    qu_net_ton_m2 = Pu_net_ton / Af_m2
    # Shell wall reaction + overhang net upward soil shear
    W_shell_ult_ton = 1.40 * W_tank_empty_ton + 0.15 * (1.50 * W_liquid_ton)
    Q_up_overhang_ton = max(0.0, Pu_net_ton - qu_net_ton_m2 * min(area_punch_m2, Af_m2))
    Q_up_ton = max(W_shell_ult_ton, Q_up_overhang_ton)

    q_up_kg_cm2 = (Q_up_ton * 1000.0) / (bo_m * 100.0 * d_cm)
    q_cup_all_kg_cm2 = min(0.316 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0, 16.0)
    ratio_punching = q_up_kg_cm2 / max(q_cup_all_kg_cm2, 0.01)
    is_punching_safe = ratio_punching <= 1.0001

    # One-Way Shear Check at d from Tank Wall
    shear_span_m = max(overhang_m - d_m, 0.15 * min(L_tank_m, B_tank_m))
    Qu_1way_ton_m = qu_net_ton_m2 * shear_span_m * 0.35
    qu_1way_kg_cm2 = (Qu_1way_ton_m * 1000.0) / (100.0 * d_cm)
    qcu_1way_kg_cm2 = 0.16 * math.sqrt(fcu_mpa / gamma_c_mat) * 10.0
    ratio_1way_shear = qu_1way_kg_cm2 / max(qcu_1way_kg_cm2, 0.01)
    is_1way_shear_safe = ratio_1way_shear <= 1.0001

    # Flexural Design (Hydrostatic + Overhang + Edge Shell Wall Effect + Uplift)
    # 1. Cantilever moment at tank wall edge:
    Mu_cant_tm = qu_net_ton_m2 * (overhang_m ** 2) / 2.0 + (W_shell_ult_ton / perimeter_tank_m) * (overhang_m * 0.50)
    # 2. Interior slab radial/longitudinal moment under hydrostatic pressure & soil subgrade interaction:
    span_ref_m = D_tank_m if is_circular else min(L_tank_m, B_tank_m)
    Mu_interior_pos_tm = max(Mu_cant_tm, 0.035 * (1.50 * p_hydrostatic_ton_m2) * (span_ref_m ** 2))
    # 3. Top Moment (Negative moment from shell fixity / groundwater uplift when empty):
    q_uplift_ult_ton_m2 = 1.40 * max(0.0, gwt_depth_m * gamma_water)
    Mu_top_neg_tm = max(0.65 * Mu_interior_pos_tm, 0.045 * q_uplift_ult_ton_m2 * (span_ref_m ** 2), 1.50)

    # Water-tightness / Crack Control factor per ECP 203 Liquid Structures (reduce fs or multiply moment by 1.25)
    crack_control_factor = 1.20
    j_factor = 0.826
    fy_design = fy_kg_cm2 / gamma_s_mat

    As_bot_flex_cm2_m = (Mu_interior_pos_tm * crack_control_factor * 1e5) / (fy_design * j_factor * d_cm)
    As_top_flex_cm2_m = (Mu_top_neg_tm * crack_control_factor * 1e5) / (fy_design * j_factor * d_cm)

    # ECP 203 Minimum Rebar for Liquid Retaining Foundations (0.20% for crack control or min 6Φ12/m)
    As_min_bot_cm2_m = max(0.0018 * 100.0 * d_cm, 6.78)
    As_min_top_cm2_m = max(0.0015 * 100.0 * d_cm, 5.65)

    As_bot_req_cm2_m = max(As_bot_flex_cm2_m, As_min_bot_cm2_m)
    As_top_req_cm2_m = max(As_top_flex_cm2_m, As_min_top_cm2_m)

    area_bar_bot = BAR_AREAS.get(phi_bot_mm, (math.pi * (phi_bot_mm / 10.0) ** 2) / 4.0)
    area_bar_top = BAR_AREAS.get(phi_top_mm, (math.pi * (phi_top_mm / 10.0) ** 2) / 4.0)

    n_bars_bot_m = max(5, math.ceil(As_bot_req_cm2_m / area_bar_bot))
    n_bars_top_m = max(5, math.ceil(As_top_req_cm2_m / area_bar_top))

    spacing_bot_cm = round(100.0 / n_bars_bot_m, 1)
    spacing_top_cm = round(100.0 / n_bars_top_m, 1)

    As_bot_prov_cm2_m = n_bars_bot_m * area_bar_bot
    As_top_prov_cm2_m = n_bars_top_m * area_bar_top

    # Total Steel Weight in Tank Foundation
    wt_bar_bot_kg_m = BAR_WEIGHTS.get(phi_bot_mm, (phi_bot_mm ** 2) / 162.0)
    wt_bar_top_kg_m = BAR_WEIGHTS.get(phi_top_mm, (phi_top_mm ** 2) / 162.0)

    # Equivalent weight per m² for orthogonal/radial-tangential 2-directional mesh
    wt_bot_per_m2 = 2.0 * n_bars_bot_m * wt_bar_bot_kg_m
    wt_top_per_m2 = 2.0 * n_bars_top_m * wt_bar_top_kg_m

    weight_bot_kg = wt_bot_per_m2 * Af_m2 * 1.08  # +8% hooks & laps
    weight_top_kg = wt_top_per_m2 * Af_m2 * 1.08

    total_rebar_weight_kg = weight_bot_kg + weight_top_kg
    total_rebar_weight_ton = total_rebar_weight_kg / 1000.0
    steel_rate_kg_m3 = total_rebar_weight_kg / max(vol_f_m3, 0.01)

    is_all_safe = (
        is_soil_safe
        and is_punching_safe
        and is_1way_shear_safe
        and is_overturning_safe
        and is_buoyancy_safe
    )

    return {
        "tank_shape": tank_shape,
        "is_circular": is_circular,
        "D_tank_m": D_tank_m,
        "L_tank_m": L_tank_m,
        "B_tank_m": B_tank_m,
        "A_tank_m2": A_tank_m2,
        "H_liquid_m": H_liquid_m,
        "H_tank_total_m": H_tank_total_m,
        "tank_material": tank_material,
        "is_steel": is_steel,
        "sheet_thk_mm": sheet_thk_mm,
        "capacity_barrels": capacity_barrels,
        "vol_liquid_m3": vol_liquid_m3,
        "specific_gravity": specific_gravity,
        "gamma_liquid_ton_m3": gamma_liquid_ton_m3,
        "W_tank_empty_ton": W_tank_empty_ton,
        "W_liquid_ton": W_liquid_ton,
        "p_hydrostatic_ton_m2": p_hydrostatic_ton_m2,
        "p_hydrostatic_kg_cm2": p_hydrostatic_kg_cm2,
        "fc_kg_cm2": fc_kg_cm2,
        "fy_kg_cm2": fy_kg_cm2,
        "q_all_kg_cm2": q_all_kg_cm2,
        "q_all_ton_m2": q_all_ton_m2,
        "sizing_mode": sizing_mode,
        "overhang_m": overhang_m,
        "Df_m": Df_m,
        "Lf_m": Lf_m,
        "Bf_m": Bf_m,
        "tf_m": tf_m,
        "tf_cm": tf_m * 100.0,
        "d_cm": d_cm,
        "cover_cm": cover_cm,
        "Af_m2": Af_m2,
        "vol_f_m3": vol_f_m3,
        "Wf_ton": Wf_ton,
        "P_total_working_ton": P_total_working_ton,
        "Pu_total_ton": Pu_total_ton,
        "Pu_net_ton": Pu_net_ton,
        "gwt_depth_m": gwt_depth_m,
        "wind_seismic_coeff": wind_seismic_coeff,
        "V_lateral_ton": V_lateral_ton,
        "M_overturning_tm": M_overturning_tm,
        "M_resisting_full_tm": M_resisting_full_tm,
        "fos_overturning": fos_overturning,
        "is_overturning_safe": is_overturning_safe,
        "U_buoyancy_ton": U_buoyancy_ton,
        "W_empty_total_ton": W_empty_total_ton,
        "fos_buoyancy": fos_buoyancy,
        "is_buoyancy_safe": is_buoyancy_safe,
        "q_avg_ton_m2": q_avg_ton_m2,
        "q_max_ton_m2": q_max_ton_m2,
        "q_min_ton_m2": q_min_ton_m2,
        "q_max_kg_cm2": q_max_kg_cm2,
        "q_min_kg_cm2": q_min_kg_cm2,
        "ratio_soil": ratio_soil,
        "is_soil_safe": is_soil_safe,
        "bo_m": bo_m,
        "Q_up_ton": Q_up_ton,
        "q_up_kg_cm2": q_up_kg_cm2,
        "q_cup_all_kg_cm2": q_cup_all_kg_cm2,
        "ratio_punching": ratio_punching,
        "is_punching_safe": is_punching_safe,
        "Qu_1way_ton_m": Qu_1way_ton_m,
        "qu_1way_kg_cm2": qu_1way_kg_cm2,
        "qcu_1way_kg_cm2": qcu_1way_kg_cm2,
        "ratio_1way_shear": ratio_1way_shear,
        "is_1way_shear_safe": is_1way_shear_safe,
        "Mu_interior_pos_tm": Mu_interior_pos_tm,
        "Mu_top_neg_tm": Mu_top_neg_tm,
        "As_bot_req_cm2_m": As_bot_req_cm2_m,
        "As_top_req_cm2_m": As_top_req_cm2_m,
        "phi_bot_mm": phi_bot_mm,
        "phi_top_mm": phi_top_mm,
        "n_bars_bot_m": n_bars_bot_m,
        "n_bars_top_m": n_bars_top_m,
        "spacing_bot_cm": spacing_bot_cm,
        "spacing_top_cm": spacing_top_cm,
        "As_bot_prov_cm2_m": As_bot_prov_cm2_m,
        "As_top_prov_cm2_m": As_top_prov_cm2_m,
        "weight_bot_kg": weight_bot_kg,
        "weight_top_kg": weight_top_kg,
        "total_rebar_weight_kg": total_rebar_weight_kg,
        "total_rebar_weight_ton": total_rebar_weight_ton,
        "steel_rate_kg_m3": steel_rate_kg_m3,
        "is_all_safe": is_all_safe,
    }


# ===============================================================================
#  3. 2D CAD ENGINEERING SKETCH GENERATORS (EQUIPMENT & LIQUID TANK)
# ===============================================================================

def generate_equipment_foundation_sketches(res: dict) -> str:
    """Generates a high-resolution 2-panel CAD blueprint (Plan + Section) for Equipment Foundation."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.8), dpi=130)
    fig.patch.set_facecolor("#0b1329")

    for ax in (ax1, ax2):
        ax.set_facecolor("#0f172a")
        for spine in ax.spines.values():
            spine.set_color("#334155")
            spine.set_linewidth(1.5)

    Lf = res["Lf_m"]
    Bf = res["Bf_m"]
    tf = res["tf_m"]
    Lm = res["Lm_m"]
    Bm = res["Bm_m"]
    d_m = res["d_cm"] / 100.0

    # --- Panel 1: Top Plan View ---
    ax1.set_title("1. Top Plan View & Critical Punching Perimeter", color="#38bdf8", fontsize=13, fontweight="bold", pad=12)
    rect_f = Rectangle((-Lf / 2, -Bf / 2), Lf, Bf, facecolor="#1e293b", edgecolor="#38bdf8", linewidth=2.5, label="RC Foundation")
    ax1.add_patch(rect_f)

    # Rebar grid lines in Plan
    nx_lines = np.linspace(-Lf / 2 + 0.15, Lf / 2 - 0.15, 9)
    ny_lines = np.linspace(-Bf / 2 + 0.15, Bf / 2 - 0.15, 7)
    for xl in nx_lines:
        ax1.plot([xl, xl], [-Bf / 2 + 0.08, Bf / 2 - 0.08], color="#22c55e", alpha=0.30, linewidth=1.0, linestyle="--")
    for yl in ny_lines:
        ax1.plot([-Lf / 2 + 0.08, Lf / 2 - 0.08], [yl, yl], color="#22c55e", alpha=0.30, linewidth=1.0, linestyle="--")

    # Punching perimeter at d/2
    if res["is_circular_eq"]:
        cir_p = Circle((0, 0), radius=(Lm + d_m) / 2, facecolor="none", edgecolor="#f59e0b", linewidth=2.0, linestyle="-.")
        cir_m = Circle((0, 0), radius=Lm / 2, facecolor="#334155", edgecolor="#f87171", linewidth=2.2)
        ax1.add_patch(cir_p)
        ax1.add_patch(cir_m)
    else:
        Lp = min(Lm + d_m, Lf - 0.05)
        Bp = min(Bm + d_m, Bf - 0.05)
        rect_p = Rectangle((-Lp / 2, -Bp / 2), Lp, Bp, facecolor="none", edgecolor="#f59e0b", linewidth=2.0, linestyle="-.")
        rect_m = Rectangle((-Lm / 2, -Bm / 2), Lm, Bm, facecolor="#334155", edgecolor="#f87171", linewidth=2.2)
        ax1.add_patch(rect_p)
        ax1.add_patch(rect_m)

    # Dimension annotations (separated cleanly from dimension line & arrows)
    dim_offset_y = max(0.32, Bf * 0.14)
    text_offset_y = dim_offset_y + max(0.24, Bf * 0.11)
    ax1.annotate("", xy=(-Lf / 2, -Bf / 2 - dim_offset_y), xytext=(Lf / 2, -Bf / 2 - dim_offset_y),
                 arrowprops=dict(arrowstyle="<->", color="#e2e8f0", lw=1.8))
    ax1.text(0, -Bf / 2 - text_offset_y, f"Lf = {Lf:.2f} m", color="#ffffff", fontsize=11, fontweight="bold",
             ha="center", va="top", bbox=dict(boxstyle="round,pad=0.25", facecolor="#0f172a", edgecolor="#38bdf8", lw=1.0))

    dim_offset_x = max(0.32, Lf * 0.14)
    text_offset_x = dim_offset_x + max(0.26, Lf * 0.11)
    ax1.annotate("", xy=(-Lf / 2 - dim_offset_x, -Bf / 2), xytext=(-Lf / 2 - dim_offset_x, Bf / 2),
                 arrowprops=dict(arrowstyle="<->", color="#e2e8f0", lw=1.8))
    ax1.text(-Lf / 2 - text_offset_x, 0, f"Bf = {Bf:.2f} m", color="#ffffff", fontsize=11, fontweight="bold",
             ha="right", va="center", rotation=90, bbox=dict(boxstyle="round,pad=0.25", facecolor="#0f172a", edgecolor="#38bdf8", lw=1.0))

    ax1.text(0, 0, f"Equipment\n{Lm:.2f}×{Bm:.2f} m\nW = {res['eq_weight_ton']:.1f} t",
             color="#fde047", fontsize=10, fontweight="bold", ha="center", va="center")

    margin_x = text_offset_x + max(0.45, Lf * 0.16)
    margin_y = text_offset_y + max(0.45, Bf * 0.16)
    ax1.set_xlim(-Lf / 2 - margin_x, Lf / 2 + max(0.40, Lf * 0.18))
    ax1.set_ylim(-Bf / 2 - margin_y, Bf / 2 + max(0.40, Bf * 0.18))
    ax1.set_aspect("equal", "box")
    ax1.axis("off")

    # --- Panel 2: Structural Cross-Section & Rebar Cage ---
    ax2.set_title("2. Cross-Section & Top/Bottom Rebar Detailing", color="#38bdf8", fontsize=13, fontweight="bold", pad=12)

    # Soil Subgrade Hatch
    soil_rect = Rectangle((-Lf / 2 - 0.4, -0.35), Lf + 0.8, 0.35, facecolor="#422006", edgecolor="#ca8a04", hatch="//", alpha=0.6)
    ax2.add_patch(soil_rect)

    # Concrete Foundation Block
    conc_rect = Rectangle((-Lf / 2, 0), Lf, tf, facecolor="#334155", edgecolor="#94a3b8", linewidth=2.5)
    ax2.add_patch(conc_rect)

    # Rebar Cage (Bottom & Top U-Bars)
    cov_m = res["cover_cm"] / 100.0
    ax2.plot([-Lf / 2 + cov_m, Lf / 2 - cov_m], [cov_m, cov_m], color="#4ade80", linewidth=3.2, label="Bottom Mesh")
    ax2.plot([-Lf / 2 + cov_m, Lf / 2 - cov_m], [tf - cov_m, tf - cov_m], color="#38bdf8", linewidth=2.8, label="Top Mesh")
    ax2.plot([-Lf / 2 + cov_m, -Lf / 2 + cov_m], [cov_m, tf - cov_m], color="#4ade80", linewidth=2.5)
    ax2.plot([Lf / 2 - cov_m, Lf / 2 - cov_m], [cov_m, tf - cov_m], color="#4ade80", linewidth=2.5)

    # Isolators / Springs or Anchor Bolts
    eq_base_y = tf + (0.18 if res["is_isolated"] else 0.04)
    if res["is_isolated"]:
        n_sp = 4
        sp_xs = np.linspace(-Lm / 2 + 0.15, Lm / 2 - 0.15, n_sp)
        for sx in sp_xs:
            ax2.plot([sx, sx], [tf, eq_base_y], color="#facc15", linewidth=3.5, linestyle=":")
            ax2.add_patch(Rectangle((sx - 0.08, tf), 0.16, 0.04, facecolor="#eab308"))
    else:
        for ax_x in (-Lm / 2 + 0.15, Lm / 2 - 0.15):
            ax2.plot([ax_x, ax_x], [tf - 0.50 * tf, tf + 0.12], color="#f87171", linewidth=2.5)

    # Equipment Body
    eq_h = max(0.55, 0.45 * tf)
    eq_rect = FancyBboxPatch((-Lm / 2, eq_base_y), Lm, eq_h, boxstyle="round,pad=0.02", facecolor="#1e3a8a", edgecolor="#60a5fa", linewidth=2.2)
    ax2.add_patch(eq_rect)
    ax2.text(0, eq_base_y + eq_h / 2, f"Mechanical Equipment\nP_op = {res['eq_weight_ton']:.1f} ton (DF = {res['dyn_factor']:.2f})",
             color="#ffffff", fontsize=10, fontweight="bold", ha="center", va="center")

    # Rebar & Thickness Callouts
    ax2.text(0, cov_m + 0.06 * tf, f"Bottom: {res['n_bars_bot_m']} Φ {res['phi_bot_mm']}/m' (As = {res['As_bot_prov_cm2_m']:.2f} cm²/m')",
             color="#4ade80", fontsize=10, fontweight="bold", ha="center")
    ax2.text(0, tf - cov_m - 0.10 * tf, f"Top: {res['n_bars_top_m']} Φ {res['phi_top_mm']}/m' (As = {res['As_top_prov_cm2_m']:.2f} cm²/m')",
             color="#38bdf8", fontsize=10, fontweight="bold", ha="center")
    ax2.text(0, -0.22, f"q_act = {res['q_act_kg_cm2']:.2f} kg/cm² ≤ q_all = {res['q_all_kg_cm2']:.2f} kg/cm² | W_f (Self) = {res['Wf_ton']:.2f} ton",
             color="#fde047", fontsize=10, fontweight="bold", ha="center")

    tf_dim_x = Lf / 2 + max(0.28, Lf * 0.08)
    tf_txt_x = tf_dim_x + max(0.22, Lf * 0.07)
    ax2.annotate("", xy=(tf_dim_x, 0), xytext=(tf_dim_x, tf),
                 arrowprops=dict(arrowstyle="<->", color="#f87171", lw=2.0))
    ax2.text(tf_txt_x, tf / 2, f"tf = {tf:.2f} m", color="#f87171", fontsize=11, fontweight="bold",
             ha="left", va="center", rotation=90, bbox=dict(boxstyle="round,pad=0.2", facecolor="#0f172a", edgecolor="#f87171", lw=1.0))

    ax2.set_xlim(-Lf / 2 - max(0.85, Lf * 0.20), tf_txt_x + max(0.55, Lf * 0.14))
    ax2.set_ylim(-0.55, eq_base_y + eq_h + 0.35)
    ax2.axis("off")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_liquid_tank_foundation_sketches(res: dict) -> str:
    """Generates a high-resolution 2-panel CAD blueprint (Plan + Section) for Liquid Storage Tank Foundation."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.8), dpi=130)
    fig.patch.set_facecolor("#0b1329")

    for ax in (ax1, ax2):
        ax.set_facecolor("#0f172a")
        for spine in ax.spines.values():
            spine.set_color("#334155")
            spine.set_linewidth(1.5)

    Lf = res["Lf_m"]
    Bf = res["Bf_m"]
    tf = res["tf_m"]
    Lt = res["L_tank_m"]
    Bt = res["B_tank_m"]

    # --- Panel 1: Foundation & Tank Plan View ---
    ax1.set_title("1. Tank & Foundation Plan View (ECP 203 / ACI 350)", color="#38bdf8", fontsize=13, fontweight="bold", pad=12)

    if res["is_circular"]:
        cir_f = Circle((0, 0), radius=Lf / 2, facecolor="#1e293b", edgecolor="#38bdf8", linewidth=2.5)
        cir_t = Circle((0, 0), radius=Lt / 2, facecolor="#0284c7", alpha=0.35, edgecolor="#fde047", linewidth=2.5)
        ax1.add_patch(cir_f)
        ax1.add_patch(cir_t)
        # Radial & Tangential Rebar schematic lines
        for r_rad in np.linspace(0.25 * Lf / 2, 0.90 * Lf / 2, 4):
            ax1.add_patch(Circle((0, 0), radius=r_rad, facecolor="none", edgecolor="#4ade80", alpha=0.30, linestyle="--"))
        for ang in np.linspace(0, np.pi, 6, endpoint=False):
            x_r = (Lf / 2 - 0.1) * np.cos(ang)
            y_r = (Lf / 2 - 0.1) * np.sin(ang)
            ax1.plot([-x_r, x_r], [-y_r, y_r], color="#4ade80", alpha=0.25, linewidth=1.0)
        dim_lbl = f"Df = {Lf:.2f} m (D_tank = {Lt:.2f} m)"
    else:
        rect_f = Rectangle((-Lf / 2, -Bf / 2), Lf, Bf, facecolor="#1e293b", edgecolor="#38bdf8", linewidth=2.5)
        rect_t = Rectangle((-Lt / 2, -Bt / 2), Lt, Bt, facecolor="#0284c7", alpha=0.35, edgecolor="#fde047", linewidth=2.5)
        ax1.add_patch(rect_f)
        ax1.add_patch(rect_t)
        for xl in np.linspace(-Lf / 2 + 0.2, Lf / 2 - 0.2, 8):
            ax1.plot([xl, xl], [-Bf / 2 + 0.1, Bf / 2 - 0.1], color="#4ade80", alpha=0.28, linestyle="--")
        for yl in np.linspace(-Bf / 2 + 0.2, Bf / 2 - 0.2, 6):
            ax1.plot([-Lf / 2 + 0.1, Lf / 2 - 0.1], [yl, yl], color="#4ade80", alpha=0.28, linestyle="--")
        dim_lbl = f"Lf × Bf = {Lf:.2f} × {Bf:.2f} m"

    ax1.text(0, 0, f"Liquid Storage Tank\n{res['capacity_barrels']:.0f} BBL ({res['vol_liquid_m3']:.1f} m³)\nW_liq = {res['W_liquid_ton']:.1f} t",
             color="#ffffff", fontsize=10, fontweight="bold", ha="center", va="center")

    dim_offset_y = max(0.35, Bf * 0.12)
    text_offset_y = dim_offset_y + max(0.26, Bf * 0.09)
    ax1.annotate("", xy=(-Lf / 2, -Bf / 2 - dim_offset_y), xytext=(Lf / 2, -Bf / 2 - dim_offset_y),
                 arrowprops=dict(arrowstyle="<->", color="#e2e8f0", lw=1.8))
    ax1.text(0, -Bf / 2 - text_offset_y, dim_lbl, color="#fde047", fontsize=11, fontweight="bold",
             ha="center", va="top", bbox=dict(boxstyle="round,pad=0.25", facecolor="#0f172a", edgecolor="#38bdf8", lw=1.0))

    if not res["is_circular"]:
        dim_offset_x = max(0.35, Lf * 0.12)
        text_offset_x = dim_offset_x + max(0.28, Lf * 0.09)
        ax1.annotate("", xy=(-Lf / 2 - dim_offset_x, -Bf / 2), xytext=(-Lf / 2 - dim_offset_x, Bf / 2),
                     arrowprops=dict(arrowstyle="<->", color="#e2e8f0", lw=1.8))
        ax1.text(-Lf / 2 - text_offset_x, 0, f"Bf = {Bf:.2f} m", color="#fde047", fontsize=11, fontweight="bold",
                 ha="right", va="center", rotation=90, bbox=dict(boxstyle="round,pad=0.25", facecolor="#0f172a", edgecolor="#38bdf8", lw=1.0))
        margin_x = text_offset_x + max(0.45, Lf * 0.14)
    else:
        margin_x = max(Lf, Bf) * 0.30

    margin_y = text_offset_y + max(0.45, Bf * 0.14)
    ax1.set_xlim(-Lf / 2 - margin_x, Lf / 2 + max(0.40, Lf * 0.18))
    ax1.set_ylim(-Bf / 2 - margin_y, Bf / 2 + max(0.40, Bf * 0.18))
    ax1.set_aspect("equal", "box")
    ax1.axis("off")

    # --- Panel 2: Elevation Section (Tank + Liquid + RC Foundation) ---
    ax2.set_title("2. Structural Elevation, Hydrostatic Load & Rebar Mesh", color="#38bdf8", fontsize=13, fontweight="bold", pad=12)

    H_draw_tank = min(max(res["H_tank_total_m"] * 0.35, 1.20), 2.60)
    H_draw_liq = H_draw_tank * (res["H_liquid_m"] / max(res["H_tank_total_m"], 0.1))

    # Subgrade
    ax2.add_patch(Rectangle((-Lf / 2 - 0.5, -0.35), Lf + 1.0, 0.35, facecolor="#422006", edgecolor="#ca8a04", hatch="//", alpha=0.6))

    # RC Foundation Slab
    ax2.add_patch(Rectangle((-Lf / 2, 0), Lf, tf, facecolor="#334155", edgecolor="#94a3b8", linewidth=2.5))

    # Rebar Top & Bottom
    cov_m = min(res["cover_cm"] / 100.0, tf * 0.2)
    ax2.plot([-Lf / 2 + cov_m, Lf / 2 - cov_m], [cov_m, cov_m], color="#4ade80", linewidth=3.0)
    ax2.plot([-Lf / 2 + cov_m, Lf / 2 - cov_m], [tf - cov_m, tf - cov_m], color="#38bdf8", linewidth=2.8)

    # Tank Shell & Liquid Fill
    ax2.add_patch(Rectangle((-Lt / 2, tf), Lt, H_draw_liq, facecolor="#0284c7", alpha=0.55, edgecolor="none"))
    ax2.add_patch(Rectangle((-Lt / 2, tf), Lt, H_draw_tank, facecolor="none", edgecolor="#fde047", linewidth=2.8))

    # Labels
    ax2.text(0, tf + H_draw_liq / 2,
             f"Stored Liquid (SG = {res['specific_gravity']:.2f})\nH_liq = {res['H_liquid_m']:.2f} m | p_hyd = {res['p_hydrostatic_ton_m2']:.2f} t/m²\nW_liquid = {res['W_liquid_ton']:.2f} ton",
             color="#ffffff", fontsize=9.5, fontweight="bold", ha="center", va="center")
    ax2.text(0, tf / 2,
             f"RC Foundation (tf = {tf:.2f} m, W_f = {res['Wf_ton']:.2f} ton)\nBot: {res['n_bars_bot_m']}Φ{res['phi_bot_mm']}/m' | Top: {res['n_bars_top_m']}Φ{res['phi_top_mm']}/m'",
             color="#4ade80", fontsize=9.5, fontweight="bold", ha="center", va="center")
    ax2.text(0, -0.22,
             f"q_max = {res['q_max_kg_cm2']:.2f} kg/cm² ≤ {res['q_all_kg_cm2']:.2f} kg/cm² | FOS_overturn = {res['fos_overturning']:.2f} | FOS_uplift = {res['fos_buoyancy']:.2f}",
             color="#fde047", fontsize=9.5, fontweight="bold", ha="center")

    ax2.set_xlim(-Lf / 2 - 0.9, Lf / 2 + 0.9)
    ax2.set_ylim(-0.55, tf + H_draw_tank + 0.45)
    ax2.axis("off")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ===============================================================================
#  4. STANDALONE HTML/PDF CALCULATION SHEET GENERATOR
# ===============================================================================

def generate_m10_calculation_sheet_html(title_ar: str, subtitle_en: str, rows_summary: list, checks_list: list, sketch_b64: str) -> str:
    """Generates a clean, print-ready Arabic RTL HTML calculation report for Module 10."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    summary_trs = "".join(
        f"<tr><td style='padding:8px 12px; font-weight:700; border:1px solid #cbd5e1;'>{k}</td>"
        f"<td style='padding:8px 12px; font-weight:800; color:#1e40af; border:1px solid #cbd5e1;' dir='ltr'>{v}</td></tr>"
        for k, v in rows_summary
    )
    checks_trs = "".join(
        f"<tr>"
        f"<td style='padding:8px 12px; font-weight:700; border:1px solid #cbd5e1;'>{item}</td>"
        f"<td style='padding:8px 12px; text-align:center; border:1px solid #cbd5e1;' dir='ltr'>{act}</td>"
        f"<td style='padding:8px 12px; text-align:center; border:1px solid #cbd5e1;' dir='ltr'>{lim}</td>"
        f"<td style='padding:8px 12px; text-align:center; font-weight:800; color:{'#15803d' if ok else '#b91c1c'}; border:1px solid #cbd5e1;'>{'✅ SAFE' if ok else '⚠️ UNSAFE'}</td>"
        f"</tr>"
        for item, act, lim, ok in checks_list
    )
    img_block = f'<div style="text-align:center; margin:18px 0;"><img src="data:image/png;base64,{sketch_b64}" style="max-width:100%; border:1.5px solid #1e3a8a; border-radius:8px;"/><div class="drawing-caption">{title_ar} — {subtitle_en}</div></div>' if sketch_b64 else ""

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<title>{title_ar}</title>
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; margin: 24px; color: #0f172a; background: #ffffff; direction: rtl; }}
    .hdr {{ background: linear-gradient(135deg, #0f172a, #1e3a8a); color: #fff; padding: 18px 24px; border-radius: 10px; margin-bottom: 20px; }}
    .hdr h1 {{ margin: 0 0 6px 0; font-size: 22px; color: #fde047; }}
    .hdr p {{ margin: 0; font-size: 13px; color: #e2e8f0; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; }}
    th {{ background: #1e293b; color: #ffffff; padding: 10px 12px; border: 1px solid #cbd5e1; text-align: right; }}
    .drawing-caption {{ font-size: 12px; color: #475569; margin-top: 6px; font-weight: bold; }}
</style>
</head>
<body>
    <div class="hdr">
        <h1>{title_ar}</h1>
        <p>{subtitle_en} | الكود المصري ECP 203 & ACI | تاريخ التقرير: {now_str}</p>
    </div>
    <h3>1. ملخص البيانات الهندسية والأوزان والأبعاد والتسليح (Design Summary)</h3>
    <table>
        <thead><tr><th>البند الهندسي (Parameter)</th><th>القيمة المعتمدة (Design Value)</th></tr></thead>
        <tbody>{summary_trs}</tbody>
    </table>
    <h3>2. جدول التحققات الكودية والاتزان (Code Verification Checks)</h3>
    <table>
        <thead><tr><th>بند التحقق (Check)</th><th>القيمة الفعلية (Actual)</th><th>الحد الكودي (Allowable)</th><th>الحالة (Status)</th></tr></thead>
        <tbody>{checks_trs}</tbody>
    </table>
    {img_block}
</body>
</html>"""


# ===============================================================================
#  5. STREAMLIT UI RENDERER — SECTION 1: EQUIPMENT FOUNDATIONS
# ===============================================================================

# ===============================================================================
#  4.5 MODAL DIALOG: VIBRATION ISOLATION PHILOSOPHY & FOUNDATION DESIGN
# ===============================================================================

@st.dialog("📖 فلسفة التصميم للعزل الاهتزازي وقواعد المعدات (ECP 203 & ACI 351.3R)", width="large")
def show_dialog_vibration_philosophy():
    html_content = """<style>
div[data-testid="stDialog"],
div[data-testid="stDialog"] > div,
div[data-testid="stDialog"] div[data-testid="stVerticalBlock"],
div[data-testid="stDialog"] [data-testid="stMarkdownContainer"],
div[role="dialog"],
div[role="dialog"] * {
direction: rtl !important;
text-align: right !important;
}
div[data-testid="stDialog"] [dir="ltr"],
div[role="dialog"] [dir="ltr"],
span[dir="ltr"] {
direction: ltr !important;
unicode-bidi: isolate !important;
display: inline-block !important;
}
div[data-testid="stDialog"] ul,
div[data-testid="stDialog"] ol,
div[role="dialog"] ul,
div[role="dialog"] ol {
direction: rtl !important;
text-align: right !important;
padding-right: 26px !important;
padding-left: 0 !important;
margin-right: 0 !important;
list-style-position: outside !important;
}
div[data-testid="stDialog"] li,
div[role="dialog"] li {
direction: rtl !important;
text-align: right !important;
margin-bottom: 12px !important;
line-height: 1.95 !important;
}
</style>
<div dir="rtl" style="direction: rtl !important; text-align: right !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.9; color: #0f172a;">
<div dir="rtl" style="direction: rtl !important; text-align: center !important; background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #0f172a 100%); color: #ffffff; padding: 22px 26px; border-radius: 14px; margin-bottom: 22px; border: 2px solid #38bdf8; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.35);">
<h2 dir="rtl" style="direction: rtl !important; text-align: center !important; margin: 0 0 10px 0; color: #fde047; font-size: 22px; font-weight: 900; line-height: 1.4;">
📳 فلسفة التصميم الإنشائي والديناميكي للعزل الاهتزازي وقواعد المعدات الميكانيكية
</h2>
<div style="font-size: 15.5px; color: #bfdbfe; font-weight: 700; margin-bottom: 10px; text-align: center;" dir="ltr">
ECP 203-2018 & ACI 351.3R (Foundations for Dynamic Equipment)
</div>
<p dir="rtl" style="direction: rtl !important; text-align: center !important; margin: 0; font-size: 15.5px; color: #e2e8f0; line-height: 1.85;">
دليل هندسي استرشادي شامل يوضح فلسفة التصميم وميكانيكية عمل أنظمة التخميد والعزل الاهتزازي للماكينات، والأسس الكودية لحساب الأحمال الاستاتيكية والديناميكية، والفارق الجوهري بين <b>وجود نظام عزل (Springs & Isolators)</b> و<b>القاعدة الثابتة الجاسئة (Fixed Base)</b>.
</p>
</div>
<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: #ffffff; border: 2px solid #cbd5e1; border-right: 8px solid #0284c7; border-radius: 12px; padding: 22px 26px; margin-bottom: 22px; box-shadow: 0 4px 14px rgba(0,0,0,0.06);">
<div dir="rtl" style="display: flex; align-items: center; justify-content: space-between; flex-direction: row; direction: rtl !important; text-align: right !important; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px;">
<div dir="rtl" style="color: #0369a1; font-size: 19.5px; font-weight: 900; direction: rtl !important; text-align: right !important;">
1️⃣ الحالة الأولى: وجود نظام عزل اهتزازات (Springs & Isolators)
</div>
<span dir="ltr" style="background: #e0f2fe; color: #0284c7; padding: 5px 14px; border-radius: 20px; font-size: 13.5px; font-weight: 800; direction: ltr !important; unicode-bidi: isolate;">Isolated Base</span>
</div>
<h4 dir="rtl" style="direction: rtl !important; text-align: right !important; color: #0f172a; font-size: 17px; font-weight: 800; margin: 16px 0 10px 0;">
🔹 أ. فلسفة التصميم وميكانيكية عمل نظام العزل (Isolation Mechanism & Decoupling):
</h4>
<ul dir="rtl" style="direction: rtl !important; text-align: right !important; margin: 0; padding-right: 26px; padding-left: 0; font-size: 16px; line-height: 1.95; color: #334155; list-style-position: outside;">
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>مبدأ فك الارتباط الديناميكي (Dynamic Decoupling):</b> ترتكز شاسيهات المعدة على وسائط مرنة ميكانيكية متخصصة تشمل النوابض الفولاذية الحلزونية (<span dir="ltr"><b>Helical Steel Springs</b></span>) أو وسائد ومخمدات المطاط الصناعي والنيوبرين (<span dir="ltr"><b>Elastomeric / Neoprene Pads</b></span>) أو النوابض الهوائية (<span dir="ltr"><b>Air Springs</b></span>). تعمل هذه الوسائط كمرشح ميكانيكي عازل يمنع انتقال موجات الطاقة الحركية والترددات إلى كتلة الخرسانة وتربة التأسيس.
</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>معامل الانتقال الديناميكي (Transmissibility Ratio Tr):</b> تُصمم العوازل وتُضبط بحيث يكون ترددها الطبيعي (<span dir="ltr"><b>ωn</b></span>) أقل بكثير من تردد دوران وتشغيل الماكينة (<span dir="ltr"><b>ω</b></span>) بنسبة ضبط (<span dir="ltr"><b>ω / ωn ≥ 3.0</b></span>). يؤدي ذلك إلى خفض معامل انتقال القوة الاهتزازية إلى أقل من <span dir="ltr"><b>Tr ≤ 0.05 ~ 0.10</b></span>، ما يعني <b>امتصاص وعزل أكثر من 90% إلى 95% من القوى الاهتزازية</b> وتشتيتها داخل النوابض دون أن تصل إلى القاعدة الخرسانية.
</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>حماية التربة والمنشآت المجاورة:</b> نظراً لاختزال وتبديد الطاقة الحركية داخل النوابض، فإن الإجهادات المنقولة لتربة التأسيس تكون شبه استاتيكية وهادئة، مما يمنع حدوث أي هبوط تفاضلي أو تخلخل في حبيبات التربة الرملية أو تصدع للمباني المجاورة.
</li>
</ul>
<h4 dir="rtl" style="direction: rtl !important; text-align: right !important; color: #0f172a; font-size: 17px; font-weight: 800; margin: 18px 0 10px 0;">
🔹 ب. نظام حساب الأحمال والمعاملات التصميمية (Load Calculation):
</h4>
<ul dir="rtl" style="direction: rtl !important; text-align: right !important; margin: 0; padding-right: 26px; padding-left: 0; font-size: 16px; line-height: 1.95; color: #334155; list-style-position: outside;">
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>الحمل الرأسي التصميمي للمعدة (<span dir="ltr">Peq,design</span>):</b>
<div dir="ltr" style="direction: ltr !important; text-align: center !important; background: #f8fafc; border: 1.5px solid #94a3b8; border-radius: 8px; padding: 10px 16px; margin: 10px 0; font-family: Consolas, monospace; font-size: 15.5px; font-weight: bold; color: #0369a1; unicode-bidi: isolate;">
Peq,design = Weq × 1.20 &nbsp; (Dynamic Amplification Factor = 1.20)
</div>
يطبق الكود معامل أثر ديناميكي خفيف قدره <b>1.20</b> فقط (زيادة 20% استاتيكية مكافئة)، وهو مخصص فقط لتغطية القوى العابرة اللحظية أثناء مراحل بدء التشغيل والتوقف والمرور بالتردد الحرج للنوابض (<span dir="ltr">Transient Resonant Passing at Startup & Rundown</span>)، نظراً لأن الاهتزازات التشغيلية الدائمة تُمتص بالكامل داخل منظومة العزل.
</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>الوزن الذاتي المطلوب للقاعدة الخرسانية (<span dir="ltr">Wf</span>):</b>
<b>لا يشترط الكود نسبة كتلة ضخمة</b> (مثل 2.5x أو 3.0x)، بل يتم حساب وتحديد أبعاد وسمك القاعدة أوتوماتيكياً استناداً إلى المحددات الهندسية التالية:
<ol dir="rtl" style="direction: rtl !important; text-align: right !important; margin-top: 8px; padding-right: 28px; padding-left: 0; line-height: 1.95; list-style-position: outside;">
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 8px;">استيعاب بصمة المعدة ونقاط ارتكاز النوابض مع توفير خلوص أمان محيطي إضافي لا يقل عن <span dir="ltr"><b>40 cm</b></span> من جميع الجوانب لسهولة التركيب والصيانة وتثبيت المسامير.</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 8px;">التحقق التام من مقاومة إجهادات القص الثاقب (<span dir="ltr"><b>Punching Shear Check</b></span>) المركزة أسفل ركائز النوابض والعوازل.</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 8px;">ألا يتعدى إجهاد التماس الفعلي مع التربة إجهاد التحمل المسموح به (<span dir="ltr"><b>q_act ≤ q_all</b></span>).</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 8px;">تحقيق سمك إنشائي أدنى لا يقل عن <span dir="ltr"><b>0.50 m</b></span> لضمان تصرف القاعدة كعنصر جاسيء (<span dir="ltr">Rigid Foundation</span>).</li>
</ol>
</li>
</ul>
<h4 dir="rtl" style="direction: rtl !important; text-align: right !important; color: #0f172a; font-size: 17px; font-weight: 800; margin: 18px 0 10px 0;">
🔹 ج. التطبيقات والمعدات النموذجية:
</h4>
<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: #f0f9ff; border: 1.5px solid #bae6fd; border-radius: 8px; padding: 14px 18px; font-size: 15.5px; color: #0369a1; line-height: 1.85;">
تعتبر الخيار القياسي والإلزامي للمعدات ذات سرعات الدوران العالية (<span dir="ltr"><b>Rotary Equipment > 1000 RPM</b></span>) مثل التوربينات، مضخات الطرد المركزي، الضواغط الدوارة، ومولدات الكهرباء، وكافة المعدات المركبة في الطوابق العليا أو فوق أسقف المباني السكنية والتجارية لمنع انتشار الاهتزازات والضوضاء.
</div>
</div>
<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: #ffffff; border: 2px solid #cbd5e1; border-right: 8px solid #dc2626; border-radius: 12px; padding: 22px 26px; margin-bottom: 22px; box-shadow: 0 4px 14px rgba(0,0,0,0.06);">
<div dir="rtl" style="display: flex; align-items: center; justify-content: space-between; flex-direction: row; direction: rtl !important; text-align: right !important; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px;">
<div dir="rtl" style="color: #b91c1c; font-size: 19.5px; font-weight: 900; direction: rtl !important; text-align: right !important;">
2️⃣ الحالة الثانية: عدم وجود نظام عزل - قاعدة ثابتة (Fixed Base)
</div>
<span dir="ltr" style="background: #fee2e2; color: #dc2626; padding: 5px 14px; border-radius: 20px; font-size: 13.5px; font-weight: 800; direction: ltr !important; unicode-bidi: isolate;">Inertia Block (2.5x ~ 3.0x)</span>
</div>
<h4 dir="rtl" style="direction: rtl !important; text-align: right !important; color: #0f172a; font-size: 17px; font-weight: 800; margin: 16px 0 10px 0;">
🔹 أ. فلسفة التصميم بكتلة القصور الذاتي الضخمة (Inertia Block & Mass-Damping Philosophy):
</h4>
<ul dir="rtl" style="direction: rtl !important; text-align: right !important; margin: 0; padding-right: 26px; padding-left: 0; font-size: 16px; line-height: 1.95; color: #334155; list-style-position: outside;">
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>التثبيت المباشر الصلب:</b> يتم ربط شاسيه المعدة ميكانيكياً بصورة صلبة ومباشرة على القاعدة الخرسانية بواسطة مسامير تثبيت جشمة (<span dir="ltr"><b>Anchor Bolts</b></span>) ومونة جراوت إيبوكسية أو أسمنتية غير قابلة للانكماش عالية المقاومة (<span dir="ltr"><b>Non-Shrink High-Strength Grout</b></span>). في هذا النظام، تنتقل كامل القوى الديناميكية والقوى الطاردة المركزية غير المتزنة (<span dir="ltr"><b>Centrifugal Unbalanced Forces & Couples</b></span>) مباشرة وبلا وسيط إلى القاعدة وتربة التأسيس.
</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>آلية التخميد بكتلة القصور الذاتي (Ballast Inertia Mass):</b> نظراً لغياب عوازل النوابض، تعتمد الفلسفة الهندسية بالكامل على تحويل القاعدة الخرسانية المسلحة إلى "كتلة قصور ذاتي هائلة" (<span dir="ltr"><b>Inertia Block</b></span>) لامتصاص وتبديد الطاقة الحركية، وتقييد سعة الإزاحة الاهتزازية (<span dir="ltr"><b>Vibration Amplitude</b></span>) في حدود ميكرونية ضئيلة جداً تتطابق بدقة مع اشتراطات الكود الدولي <span dir="ltr"><b>ISO 10816</b></span> و <span dir="ltr"><b>ACI 351.3R</b></span>.
</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>خفض مركز ثقل المنظومة (Center of Gravity Alignment):</b> توفر الكتلة الخرسانية الضخمة عمقاً كافياً لخفض مركز ثقل النظام المجمع (المعدة + القاعدة) إلى أدنى مستوى ممكن، مما يقلل ذراع العزم ويحد من العزوم الانقلابية الديناميكية المتأرجحة (<span dir="ltr">Dynamic Rocking & Pitching Moments</span>).
</li>
</ul>
<h4 dir="rtl" style="direction: rtl !important; text-align: right !important; color: #0f172a; font-size: 17px; font-weight: 800; margin: 18px 0 10px 0;">
🔹 ب. اشتراط نسبة الكتلة الكودية الإلزامية (Mass Ratio ≥ 2.5x ~ 3.0x):
</h4>
<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: #fff1f2; border: 1.5px solid #fecdd3; border-radius: 8px; padding: 16px 20px; margin: 12px 0; font-size: 16px; line-height: 1.95; color: #9f1239;">
ينص كود معهد الخرسانة الأمريكي <b>ACI 351.3R (Section 3.2)</b> ومحددات الكود المصري <b>ECP 203</b> على الاشتراطات الصارمة التالية للوزن الذاتي للقاعدة الخرسانية:
<ul dir="rtl" style="direction: rtl !important; text-align: right !important; margin: 10px 0 0 0; padding-right: 24px; padding-left: 0;">
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 10px;">
<b>للمعدات الدوارة الطاردة المركزية (<span dir="ltr">Rotary Machinery</span>):</b> يجب ألا يقل وزن القاعدة الخرسانية المسلحة عن <b>2.5 ضعف</b> وزن المعدة التشغيلي الكامل:
<div dir="ltr" style="direction: ltr !important; text-align: center !important; background: #ffffff; border: 1px solid #fda4af; border-radius: 6px; padding: 8px 14px; margin: 8px 0; font-family: Consolas, monospace; font-size: 15.5px; font-weight: bold; color: #be123c; unicode-bidi: isolate;">
W_foundation ≥ 2.50 × W_equipment &nbsp; [Wf ≥ 2.50 Weq]
</div>
</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important;">
<b>للمعدات الترددية ذات المكابس (<span dir="ltr">Reciprocating Machinery</span>):</b> مثل ضواغط الهواء الترددية ومحركات الديزل، يرتفع الاشتراط الكودي الإلزامي إلى <b>3.0 إلى 5.0 أضعاف</b> وزن المعدة (<span dir="ltr"><b>Wf ≥ 3.0 ~ 5.0 Weq</b></span>) نظراً لوجود قوى ترددية غير متزنة وعزوم دورانية ديناميكية من الدرجة الأولى والثانية (<span dir="ltr">Primary & Secondary Dynamic Couples</span>).
</li>
</ul>
</div>
<h4 dir="rtl" style="direction: rtl !important; text-align: right !important; color: #0f172a; font-size: 17px; font-weight: 800; margin: 18px 0 10px 0;">
🔹 ج. نظام حساب الأحمال والمعاملات التصميمية:
</h4>
<ul dir="rtl" style="direction: rtl !important; text-align: right !important; margin: 0; padding-right: 26px; padding-left: 0; font-size: 16px; line-height: 1.95; color: #334155; list-style-position: outside;">
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>الحمل التشغيلي الديناميكي المكافئ للمعدة (<span dir="ltr">Peq,design</span>):</b>
<div dir="ltr" style="direction: ltr !important; text-align: center !important; background: #f8fafc; border: 1.5px solid #94a3b8; border-radius: 8px; padding: 10px 16px; margin: 10px 0; font-family: Consolas, monospace; font-size: 15.5px; font-weight: bold; color: #b91c1c; unicode-bidi: isolate;">
Peq,design = Weq × 1.50 &nbsp; (Dynamic Impact Factor = 1.50)
</div>
يطبق معامل تكبير ديناميكي مقداره <b>1.50</b> (زيادة 50% استاتيكية مكافئة) لأخذ أثر قوى الصدم والنبضات الاهتزازية المباشرة في الحسبان عند فحص إجهادات التربة ومقاومة القطاعات الخرسانية.
</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>الحمل الإجمالي المنقول لتربة التأسيس (<span dir="ltr">Ptotal</span>):</b>
<div dir="ltr" style="direction: ltr !important; text-align: center !important; background: #f8fafc; border: 1.5px solid #94a3b8; border-radius: 8px; padding: 10px 16px; margin: 10px 0; font-family: Consolas, monospace; font-size: 15.5px; font-weight: bold; color: #0f172a; unicode-bidi: isolate;">
Ptotal = Peq,design + Wf = 1.50 × Weq + (γc × Lf × Bf × tf)
</div>
مع شرط التحقق الصارم من عدم تجاوز إجهاد التحمل المسموح للتربة: <span dir="ltr"><b>q_act = Ptotal / (Lf × Bf) ≤ q_all</b></span>.
</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>السمك الإنشائي الأدنى والجساءة العالية (<span dir="ltr">Rigid Body Behavior</span>):</b>
يجب ألا يقل سمك القاعدة الخرسانية عن <span dir="ltr"><b>0.70 m</b></span> (أو <span dir="ltr">Lf / 6</span>) لضمان تصرف الكتلة كجسم جاسيء غير قابل للانحناء الموضعي، وحماية محاذاة واستقامة أعمدة الدوران الميكانيكية (<span dir="ltr">Shaft Alignment</span>) من أي انحرافات قد تؤدي إلى تآكل الكراسي والمحامل.
</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 12px;">
<b>التحقق من الرنين مع التردد الطبيعي للتربة (<span dir="ltr">Resonance Check</span>):</b>
يتم حساب التردد الطبيعي الرأسي للمنظومة التأسيسية مع التربة (<span dir="ltr">fn</span>):
<div dir="ltr" style="direction: ltr !important; text-align: center !important; background: #f8fafc; border: 1.5px solid #94a3b8; border-radius: 8px; padding: 10px 14px; margin: 8px 0; font-family: Consolas, monospace; font-size: 15px; font-weight: bold; color: #0f172a; unicode-bidi: isolate;">
fn = (1 / 2π) × √(Kz / m_total) &nbsp; [حيث Kz = ks × Af]
</div>
ويشترط الكود ابتعاد تردد دوران الماكينة التشغيلي (<span dir="ltr">f_op = RPM / 60</span>) عن التردد الطبيعي لمنظومة التربة بنسبة أمان لا تقل عن <b>±20%</b> منعاً لحدوث ظاهرة الرنين الخطرة وتسييل حبيبات التربة (<span dir="ltr">Avoid Resonance: f_op / fn &lt; 0.80 or f_op / fn &gt; 1.20</span>).
</li>
</ul>
</div>
<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: #ffffff; border: 2px solid #cbd5e1; border-radius: 12px; padding: 22px 24px; margin-bottom: 22px; box-shadow: 0 4px 14px rgba(0,0,0,0.06);">
<h3 dir="rtl" style="direction: rtl !important; text-align: center !important; color: #0f172a; margin: 0 0 16px 0; font-size: 19px; font-weight: 900;">
⚖️ جدول المقارنة الفنية والهندسية الشاملة بين حالتي التأسيس
</h3>
<table dir="rtl" style="direction: rtl !important; text-align: right !important; width: 100%; border-collapse: collapse; font-size: 15.5px;">
<thead>
<tr style="background: #0f172a; color: #ffffff;">
<th dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #334155; width: 28%; font-size: 15.5px;">بند المقارنة (Criterion)</th>
<th dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #334155; width: 36%; color: #38bdf8; font-size: 15.5px;">1️⃣ وجود نظام عزل (Springs & Isolators)</th>
<th dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #334155; width: 36%; color: #f87171; font-size: 15.5px;">2️⃣ قاعدة ثابتة بدون عزل (Fixed Base)</th>
</tr>
</thead>
<tbody>
<tr style="background: #f8fafc;">
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; font-weight: 800; color: #0f172a;">نسبة وزن القاعدة لوزن المعدة (Wf / Weq)</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #0284c7; font-weight: 700;">غير مقيدة بنسبة محددة (محكومة بالتربة والقص الثاقب فقط)</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #b91c1c; font-weight: 800;">إلزامية: لا تقل عن 2.5x إلى 3.0x أضعاف وزن المعدة</td>
</tr>
<tr>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; font-weight: 800; color: #0f172a;">معامل الحمل الديناميكي المكافئ (Dynamic Factor)</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #0284c7; font-weight: 700;"><span dir="ltr"><b>1.20</b></span> (أحمال هادئة ومنقولة بنسبة ضئيلة)</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #b91c1c; font-weight: 800;"><span dir="ltr"><b>1.50</b></span> (أثر صدم واهتزاز مستمر مباشر)</td>
</tr>
<tr style="background: #f8fafc;">
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; font-weight: 800; color: #0f172a;">آلية إخماد وتبديد الاهتزازات</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #334155;">امتصاص ميكانيكي وتشتيت بالزنبرك والمطاط (<span dir="ltr">Tr &lt; 0.10</span>)</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #334155;">تخميد بالكتلة الخرسانية الضخمة القاصرة (<span dir="ltr">Inertia Mass</span>)</td>
</tr>
<tr>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; font-weight: 800; color: #0f172a;">انتقال الاهتزازات للتربة والمجاورات</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #16a34a; font-weight: 800;">معزولة ومشتتة بنسبة تفوق 90% إلى 95%</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #ea580c; font-weight: 700;">تنتقل قوى للتربة وتتطلب أمان كافي ضد الرنين (<span dir="ltr">Resonance</span>)</td>
</tr>
<tr style="background: #f8fafc;">
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; font-weight: 800; color: #0f172a;">السمك الإنشائي الأدنى للقاعدة (tf)</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #334155;">يبدأ من <span dir="ltr"><b>0.50 m</b></span></td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #334155;">يبدأ من <span dir="ltr"><b>0.70 m</b></span> لضمان الجساءة العالية وتأمين الوزن</td>
</tr>
<tr>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; font-weight: 800; color: #0f172a;">حالات الاستخدام المثالية</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #334155;">الماكينات السريعة (> 1000 RPM) والمعدات داخل المباني والأسقف</td>
<td dir="rtl" style="direction: rtl !important; text-align: right !important; padding: 12px 14px; border: 1px solid #e2e8f0; color: #334155;">محطات التوليد والمصانع المفتوحة وقواعد التأسيس المباشر بالأرض</td>
</tr>
</tbody>
</table>
</div>
<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: #f1f5f9; border: 1.5px solid #cbd5e1; border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;">
<h4 dir="rtl" style="direction: rtl !important; text-align: right !important; color: #0f172a; margin: 0 0 12px 0; font-size: 17px; font-weight: 800;">
📐 اشتراطات التسليح والتنفيذ الإنشائي طبقاً للكود المصري (ECP 203) و ACI 351.3R:
</h4>
<ul dir="rtl" style="direction: rtl !important; text-align: right !important; margin: 0; padding-right: 26px; padding-left: 0; font-size: 15.5px; line-height: 1.95; color: #334155; list-style-position: outside;">
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 10px;"><b>شبكة تسليح مزدوجة (Top & Bottom Meshes):</b> يلزم تزويد القاعدة بشبكتين من حديد التسليح (سفلية وعلوية) في الاتجاهين الطولي والعرضي لمقاومة إجهادات الانحناء والانكماش والاهتزازات الدورية المتكررة.</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 10px;"><b>الحد الأدنى لنسبة التسليح (As,min):</b> لا تقل مساحة حديد التسليح عن <span dir="ltr"><b>0.15%</b></span> من مساحة القطاع الخرساني الفعال لكل شبكة في كل اتجاه (<span dir="ltr">As,min = 0.0015 × b × d</span>).</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 10px;"><b>الغطاء الخرساني الصافي (Concrete Cover):</b> لا يقل عن <span dir="ltr"><b>7.5 cm</b></span> في الأسطح الملامسة لتربة التأسيس لتأمين حماية حديد التسليح من الرطوبة والمياه الجوفية.</li>
<li dir="rtl" style="direction: rtl !important; text-align: right !important; margin-bottom: 10px;"><b>مسامير التثبيت والجراوت (Anchor Bolts & Grouting):</b> تستخدم مسامير تثبيت مجلفنة عالية المقاومة مع لوحات ارتكاز (<span dir="ltr">Anchor Plates / Sleeves</span>) لسهولة الضبط الدقيق لمحاذاة شاسيه الماكينة قبل صب مونة الجراوت غير المنكمشة (<span dir="ltr">Non-Shrink High-Strength Grout</span>).</li>
</ul>
</div>
</div>"""
    st.html(html_content)
    if st.button("✖️ إغلاق نافذة الشرح (Close)", key="btn_close_vibration_modal", use_container_width=True):
        st.rerun()


def _render_equipment_foundations_tab():
    st.markdown(
        """
        <div class="m10-centered-panel" dir="rtl" style="direction: rtl !important; text-align: center !important; background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #0f172a 100%); border: 2px solid #38bdf8; border-radius: 12px; padding: 18px 24px; margin-bottom: 18px; box-shadow: 0 4px 18px rgba(56, 189, 248, 0.2);">
            <div style="font-size: 20px; font-weight: 900; color: #fde047; margin-bottom: 8px; direction: rtl !important; text-align: center !important;">
                ⚙️ أولاً: تصميم القواعد الإنشائية للمعدات الميكانيكية الثابتة والديناميكية (Equipment Foundation Design)
            </div>
            <div style="font-size: 14.5px; color: #e2e8f0; line-height: 1.8; font-weight: 600; direction: rtl !important; text-align: center !important;">
                تصميم متكامل لقواعد الماكينات والمضخات والضواغط والمولدات وفقاً للكود المصري <span dir="ltr">ECP 203</span> و <span dir="ltr">ACI 351.3R</span>، مع الحساب التلقائي للوزن الذاتي للقاعدة (<span dir="ltr">γc = 2.5 t/m³</span>) ومعالجة الأحمال الاهتزازية في حالتي وجود نظام عزل (<span dir="ltr">Springs & Isolators</span>) أو القاعدة الثابتة (<span dir="ltr">Fixed Base</span>).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📥 1. مدخلات المعدة والتربة والمواد ونظام العزل (Equipment, Materials & Soil Inputs)", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#38bdf8; margin-bottom:10px;'>⚙️ 1. بيانات المعدة (Equipment Data)</div>", unsafe_allow_html=True)
            eq_weight = S.number_input(
                "الوزن التشغيلي للمعدة (Operating Weight) [ton]:",
                "m10_eq_weight_ton",
                value=15.0,
                min_value=0.5,
                max_value=500.0,
                step=0.5,
            )
            eq_shape = S.selectbox(
                "الشكل الهندسي لبصمة المعدة (Footprint Shape):",
                "m10_eq_shape",
                ["مستطيلة (Rectangular)", "دائرية (Circular)"],
            )
            if "دائرية" in eq_shape:
                eq_dia = S.number_input(
                    "قطر قاعدة المعدة D_eq [m]:",
                    "m10_eq_dia_m",
                    value=2.00,
                    min_value=0.30,
                    max_value=20.0,
                    step=0.10,
                )
                eq_len, eq_wid = eq_dia, eq_dia
            else:
                col_l, col_b = st.columns(2)
                with col_l:
                    eq_len = S.number_input(
                        "طول المعدة L_eq [m]:",
                        "m10_eq_len_m",
                        value=2.50,
                        min_value=0.30,
                        max_value=25.0,
                        step=0.10,
                    )
                with col_b:
                    eq_wid = S.number_input(
                        "عرض المعدة B_eq [m]:",
                        "m10_eq_wid_m",
                        value=1.50,
                        min_value=0.30,
                        max_value=25.0,
                        step=0.10,
                    )
                eq_dia = eq_len

        with c2:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#38bdf8; margin-bottom:10px;'>🧱 2. خواص المواد والتربة (Materials & Soil)</div>", unsafe_allow_html=True)
            fc_eq = S.number_input(
                "إجهاد الخرسانة fc' / fcu [kg/cm²]:",
                "m10_eq_fc",
                value=300.0,
                min_value=200.0,
                max_value=600.0,
                step=25.0,
            )
            fy_eq = S.number_input(
                "إجهاد حديد التسليح fy [kg/cm²]:",
                "m10_eq_fy",
                value=3600.0,
                min_value=2400.0,
                max_value=5000.0,
                step=200.0,
            )
            q_all_eq = S.number_input(
                "إجهاد التحمل المسموح للتربة q_all [kg/cm²]:",
                "m10_eq_q_all",
                value=1.50,
                min_value=0.40,
                max_value=6.00,
                step=0.10,
                help="1.0 kg/cm² = 10 ton/m²",
            )
            ks_eq = S.number_input(
                "معامل رد فعل التربة الديناميكي ks [kg/cm³]:",
                "m10_eq_ks",
                value=4.0,
                min_value=1.0,
                max_value=20.0,
                step=0.5,
            )

        with c3:
            st.markdown(
                """
                <style>
                /* Red Vibration Philosophy Button */
                div[class*="st-key-btn_vibration_philosophy"] button,
                .st-key-btn_vibration_philosophy button {
                    background-color: #dc2626 !important;
                    background: linear-gradient(135deg, #ef4444 0%, #dc2626 50%, #b91c1c 100%) !important;
                    color: #ffffff !important;
                    border: 1.5px solid #ef4444 !important;
                    border-radius: 8px !important;
                    font-weight: 800 !important;
                    font-size: 13px !important;
                    padding: 5px 10px !important;
                    box-shadow: 0 4px 12px rgba(220, 38, 38, 0.45) !important;
                    transition: all 0.25s ease-in-out !important;
                    white-space: nowrap !important;
                }
                div[class*="st-key-btn_vibration_philosophy"] button *,
                div[class*="st-key-btn_vibration_philosophy"] button p,
                div[class*="st-key-btn_vibration_philosophy"] button span,
                .st-key-btn_vibration_philosophy button *,
                .st-key-btn_vibration_philosophy button p,
                .st-key-btn_vibration_philosophy button span {
                    color: #ffffff !important;
                    font-weight: 800 !important;
                    font-size: 13px !important;
                }
                div[class*="st-key-btn_vibration_philosophy"] button:hover,
                .st-key-btn_vibration_philosophy button:hover {
                    background-color: #b91c1c !important;
                    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 50%, #991b1b 100%) !important;
                    color: #ffffff !important;
                    border-color: #fca5a5 !important;
                    box-shadow: 0 6px 16px rgba(220, 38, 38, 0.65) !important;
                    transform: translateY(-1.5px) !important;
                }
                div[class*="st-key-btn_vibration_philosophy"] button:hover *,
                div[class*="st-key-btn_vibration_philosophy"] button:hover p,
                div[class*="st-key-btn_vibration_philosophy"] button:hover span,
                .st-key-btn_vibration_philosophy button:hover *,
                .st-key-btn_vibration_philosophy button:hover p,
                .st-key-btn_vibration_philosophy button:hover span {
                    color: #ffffff !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            col_iso_t, col_iso_b = st.columns([1.1, 1.1], vertical_alignment="center")
            with col_iso_t:
                st.markdown(
                    "<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:16px; font-weight:900; color:#38bdf8; line-height:1.3;'>📳 3. نظام العزل الاهتزازي والأبعاد</div>",
                    unsafe_allow_html=True,
                )
            with col_iso_b:
                if st.button(
                    "فلسفة التصميم للعزل الاهتزازي",
                    key="btn_vibration_philosophy",
                    use_container_width=True,
                    help="عرض شرح وفلسفة التصميم الإنشائي والديناميكي للعزل الاهتزازي وقواعد المعدات (ACI 351.3R & ECP 203)",
                ):
                    show_dialog_vibration_philosophy()
            iso_type = S.selectbox(
                "حالة العزل الديناميكي (Vibration Isolation):",
                "m10_eq_iso_type",
                [
                    "وجود نظام عزل اهتزازات (Springs & Isolators)",
                    "عدم وجود نظام عزل - قاعدة ثابتة (Fixed Base)",
                ],
            )
            op_rpm = S.number_input(
                "سرعة دوران التشغيل (Operating Speed) [RPM]:",
                "m10_eq_rpm",
                value=1500.0,
                min_value=100.0,
                max_value=10000.0,
                step=100.0,
            )
            if "Fixed Base" in iso_type or "عدم وجود" in iso_type:
                mass_ratio_target = S.number_input(
                    "نسبة وزن القاعدة لوزن المعدة (2.0 إلى 3.0 أضعاف):",
                    "m10_eq_mass_ratio",
                    value=2.50,
                    min_value=2.00,
                    max_value=3.00,
                    step=0.10,
                )
            else:
                mass_ratio_target = 2.50

            sizing_mode_eq = S.selectbox(
                "نظام تحديد أبعاد القاعدة الخرسانية:",
                "m10_eq_sizing_mode",
                ["حساب أوتوماتيكي للأبعاد (Auto-Sizing)", "إدخال يدوي للأبعاد (Manual Override)"],
            )

        st.markdown("---")
        is_manual_mode = ("Manual" in sizing_mode_eq or "يدوي" in sizing_mode_eq)

        if is_manual_mode:
            st.markdown(
                """
                <style>
                /* Align label baselines and uniform heights across the columns */
                div[data-testid="column"] label {
                    min-height: 44px !important;
                    display: flex !important;
                    align-items: flex-end !important;
                }
                </style>
                <div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:23px; font-weight:900; color:#38bdf8; margin: 18px 0 14px 0; border-bottom: 2px solid rgba(56, 189, 248, 0.35); padding-bottom: 8px;'>
                    🛠️ المدخلات اليدوية لأبعاد القاعدة الخرسانية وقطر حديد التسليح
                </div>
                """,
                unsafe_allow_html=True,
            )

            min_Lf_req = round(float(eq_len), 2)
            min_Bf_req = round(float(eq_wid), 2)

            # Ensure saved / session values do not violate the min_value constraint before widget instantiation
            saved_man_Lf = S.cfg_val("m10_eq_man_Lf")
            if saved_man_Lf is not None and float(saved_man_Lf) < 0.50:
                if "cfg" in st.session_state:
                    st.session_state["cfg"]["m10_eq_man_Lf"] = 0.50
                if "w_m10_eq_man_Lf" in st.session_state and float(st.session_state["w_m10_eq_man_Lf"]) < 0.50:
                    st.session_state["w_m10_eq_man_Lf"] = 0.50

            saved_man_Bf = S.cfg_val("m10_eq_man_Bf")
            if saved_man_Bf is not None and float(saved_man_Bf) < 0.50:
                if "cfg" in st.session_state:
                    st.session_state["cfg"]["m10_eq_man_Bf"] = 0.50
                if "w_m10_eq_man_Bf" in st.session_state and float(st.session_state["w_m10_eq_man_Bf"]) < 0.50:
                    st.session_state["w_m10_eq_man_Bf"] = 0.50

            # 5 equal columns for rebar diameters, cover, and manual L & B
            c_in1, c_in2, c_in3, c_in4, c_in5 = st.columns(5)
            with c_in1:
                phi_bot_eq = S.selectbox("قطر التسليح السفلي Φ_bot [mm]:", "m10_eq_phi_bot", ECP_DIAMETERS, index=2)
            with c_in2:
                phi_top_eq = S.selectbox("قطر التسليح العلوي Φ_top [mm]:", "m10_eq_phi_top", ECP_DIAMETERS, index=1)
            with c_in3:
                cover_eq = S.number_input("الغطاء الخرساني Cover [cm]:", "m10_eq_cover", value=7.5, min_value=5.0, max_value=12.0, step=0.5)
            with c_in4:
                man_Lf = S.number_input(
                    f"الطول Lf [m] (الموصى به ≥ {min_Lf_req:.2f} m):",
                    "m10_eq_man_Lf",
                    value=max(3.50, min_Lf_req + 0.40),
                    min_value=0.50,
                    max_value=30.0,
                    step=0.10,
                    help=f"يجب ألا يقل طول القاعدة عن طول بصمة المعدة ({min_Lf_req:.2f} m) لتأمين مسامير التثبيت ومسافة الخلوص الكودية.",
                )
            with c_in5:
                man_Bf = S.number_input(
                    f"العرض Bf [m] (الموصى به ≥ {min_Bf_req:.2f} m):",
                    "m10_eq_man_Bf",
                    value=max(2.50, min_Bf_req + 0.40),
                    min_value=0.50,
                    max_value=30.0,
                    step=0.10,
                    help=f"يجب ألا يقل عرض القاعدة عن عرض بصمة المعدة ({min_Bf_req:.2f} m) لتأمين مسامير التثبيت ومسافة الخلوص الكودية.",
                )

            # Compute safe design thickness T_design for the manual L & B dimensions
            is_iso_bool = ("Fixed Base" not in iso_type and "عدم وجود" not in iso_type)
            dyn_factor_val = 1.20 if is_iso_bool else 1.50
            P_eq_design_val = float(eq_weight) * dyn_factor_val
            T_design = compute_equipment_foundation_T_design(
                Lf_m=float(man_Lf),
                Bf_m=float(man_Bf),
                eq_weight_ton=float(eq_weight),
                eq_shape=eq_shape,
                Lm_m=float(eq_dia) if "دائرية" in eq_shape else float(eq_len),
                Bm_m=float(eq_dia) if "دائرية" in eq_shape else float(eq_wid),
                is_isolated=is_iso_bool,
                P_eq_design_ton=P_eq_design_val,
                target_mass_ratio=float(mass_ratio_target),
                fc_kg_cm2=float(fc_eq),
                cover_cm=float(cover_eq),
            )
        else:
            st.markdown(
                """<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:22px; font-weight:900; color:#38bdf8; margin: 18px 0 14px 0; border-bottom: 2px solid rgba(56, 189, 248, 0.35); padding-bottom: 8px;'>
                    🔩 مدخلات قطر حديد التسليح والغطاء الخرساني والأبعاد المحسوبة (Reinforcement & Geometry)
                </div>""",
                unsafe_allow_html=True,
            )
            c_in1, c_in2, c_in3 = st.columns(3)
            with c_in1:
                phi_bot_eq = S.selectbox("قطر التسليح السفلي Φ_bot [mm]:", "m10_eq_phi_bot", ECP_DIAMETERS, index=2)
            with c_in2:
                phi_top_eq = S.selectbox("قطر التسليح العلوي Φ_top [mm]:", "m10_eq_phi_top", ECP_DIAMETERS, index=1)
            with c_in3:
                cover_eq = S.number_input("الغطاء الخرساني Cover [cm]:", "m10_eq_cover", value=7.5, min_value=5.0, max_value=12.0, step=0.5)

            min_Lf_req = round(float(eq_len), 2)
            min_Bf_req = round(float(eq_wid), 2)

            # Compute auto-sized dimensions and T_design
            auto_Lf, auto_Bf, T_design = compute_equipment_foundation_auto_dimensions(
                eq_weight_ton=float(eq_weight),
                eq_shape=eq_shape,
                eq_length_m=float(eq_len),
                eq_width_m=float(eq_wid),
                eq_dia_m=float(eq_dia),
                isolation_type=iso_type,
                target_mass_ratio=float(mass_ratio_target),
                q_all_kg_cm2=float(q_all_eq),
                fc_kg_cm2=float(fc_eq),
                cover_cm=float(cover_eq),
            )
            man_Lf, man_Bf = auto_Lf, auto_Bf
            st.markdown(
                f"""<div dir='rtl' style='direction:rtl !important; background:rgba(16,185,129,0.12); border:1.5px solid #10b981; border-radius:8px; padding:10px 14px; text-align:center; color:#a7f3d0; font-weight:800; margin-top:8px;'>
                    ✨ <b>الأبعاد المحسوبة أوتوماتيكياً:</b> الطول <span dir="ltr" style="color:#ffffff; font-weight:900;">Lf = {man_Lf:.2f} m</span> | العرض <span dir="ltr" style="color:#ffffff; font-weight:900;">Bf = {man_Bf:.2f} m</span> (مستوفية لإجهاد التربة ومسافات الخلوص الكودية).
                </div>""",
                unsafe_allow_html=True,
            )

        # ── INTERACTIVE THICKNESS / DEPTH VALIDATION & RECALCULATION ──
        st.markdown(
            """
            <div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:20px; font-weight:900; color:#38bdf8; margin: 18px 0 10px 0; border-bottom: 2px solid rgba(56, 189, 248, 0.35); padding-bottom: 6px;'>
                📏 سمك الخرسانة والعمق الإنشائي للقاعدة (Concrete Thickness / Depth tf)
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Signature to detect changes in foundation parameters and auto-update T_design
        curr_m10_design_sig = (
            float(eq_weight), str(eq_shape), float(eq_len), float(eq_wid), float(eq_dia),
            str(iso_type), float(op_rpm), float(fc_eq), float(fy_eq), float(q_all_eq), float(ks_eq),
            float(mass_ratio_target), str(sizing_mode_eq), round(float(man_Lf), 2), round(float(man_Bf), 2),
            float(cover_eq)
        )
        prev_m10_design_sig = st.session_state.get("_m10_eq_last_design_sig")

        if prev_m10_design_sig is None or prev_m10_design_sig != curr_m10_design_sig:
            st.session_state["_m10_eq_last_design_sig"] = curr_m10_design_sig
            st.session_state["w_m10_eq_man_tf"] = float(T_design)
            S.cfg_set("m10_eq_man_tf", float(T_design))
            st.session_state.pop("_m10_tf_error_msg", None)

        current_val_in_state = st.session_state.get("w_m10_eq_man_tf")
        if current_val_in_state is None:
            saved_tf = S.cfg_val("m10_eq_man_tf")
            current_val_in_state = float(saved_tf) if saved_tf is not None else float(T_design)
            st.session_state["w_m10_eq_man_tf"] = float(current_val_in_state)

        c_tf1, c_tf2 = st.columns([1.5, 2.5], vertical_alignment="center")
        with c_tf1:
            raw_tf = st.number_input(
                f"السمك tf [m] (سمك التصميم T_design = {T_design:.2f} m):",
                min_value=0.10,
                max_value=6.0,
                step=0.05,
                key="w_m10_eq_man_tf",
                help=f"سمك القاعدة الإنشائي tf. سمك التصميم الآمن الأدنى T_design = {T_design:.2f} m. يُسمح بزيادة السمك لإعادة حساب حديد التسليح والتحققات تلقائياً، ويتم قفل المخرجات ومنع عرضها إذا قل عن {T_design:.2f} m.",
            )

        is_thickness_safe = (float(raw_tf) >= T_design - 1e-4)

        if not is_thickness_safe:
            play_siren_alarm()
            st.html(
                f"""<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #7f1d1d 0%, #b91c1c 50%, #7f1d1d 100%) !important; color: #ffffff !important; border: 2.5px solid #ef4444 !important; border-radius: 12px !important; padding: 14px 20px !important; margin: 10px 0 14px 0 !important; box-shadow: 0 6px 18px rgba(239, 68, 68, 0.45) !important;">
                    <div style="font-size: 19px; font-weight: 900; color: #ffffff !important; display: flex; align-items: center; gap: 8px;">
                        <span>🚨 ❌ خطأ في إدخال سمك الخرسانة:</span>
                    </div>
                    <div style="font-size: 18px; font-weight: 900; color: #fef08a !important; margin-top: 6px; line-height: 1.6;">
                        لا يمكن أن يقل العمق الآمن عن القيمة الناتجة في التصميم ([{T_design:.2f} m])
                    </div>
                </div>"""
            )
            with c_tf2:
                st.html(
                    f"""<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: rgba(239, 68, 68, 0.15); border: 1.5px solid #ef4444; border-radius: 10px !important; padding: 10px 16px !important; margin: 2px 0 !important;">
                        <div style="font-size: 14.5px; font-weight: 800; color: #fca5a5 !important; line-height: 1.5;">
                            ⛔ <b>السمك غير آمن:</b> القيمة المدخلة (<span dir="ltr" style="color: #ffffff;">{raw_tf:.2f} m</span>) أقل من سمك التصميم الإنشائي المطلوب (<span dir="ltr" style="color: #fde047;">[{T_design:.2f} m]</span>).
                            <br>
                            🔒 <b>تم قفل الأقسام ومنع عرض المخرجات حتى يتم تصحيح السمك.</b>
                        </div>
                    </div>"""
                )
        else:
            S.cfg_set("m10_eq_man_tf", float(raw_tf))
            with c_tf2:
                if float(raw_tf) > T_design + 1e-4:
                    st.html(
                        f"""<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #064e3b 0%, #059669 50%, #064e3b 100%) !important; color: #ffffff !important; border: 2px solid #34d399 !important; border-radius: 10px !important; padding: 10px 16px !important; margin: 2px 0 !important; box-shadow: 0 4px 14px rgba(5, 150, 105, 0.3) !important;">
                            <div style="font-size: 15px; font-weight: 800; color: #ffffff !important; line-height: 1.5;">
                                ✅ <b>تم زيادة واعتماد السمك الجديد:</b> <span dir="ltr" style="font-weight: 900; color: #fde047;">tf = {raw_tf:.2f} m</span> (أكبر من سمك التصميم <span dir="ltr" style="color: #a7f3d0;">T_design = {T_design:.2f} m</span>).
                                <br>
                                🔄 <b>تم اعتماد السمك الجديد وإعادة حساب حديد التسليح والتحققات الإنشائية تلقائياً.</b>
                            </div>
                        </div>"""
                    )
                else:
                    st.html(
                        f"""<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: rgba(15, 23, 42, 0.75); border: 1.5px solid #38bdf8; border-radius: 10px !important; padding: 10px 16px !important; margin: 2px 0 !important;">
                            <div style="font-size: 14.5px; font-weight: 700; color: #e2e8f0 !important; line-height: 1.5;">
                                📐 <b>سمك التصميم المعتمد تلقائياً:</b> <span dir="ltr" style="font-weight: 900; color: #38bdf8;">T_design = {T_design:.2f} m</span> (محقق للقص الثاقب والقص ذي الاتجاه الواحد والوزن الذاتي).
                                <br>
                                💡 <span style="color: #94a3b8; font-size: 13px;">يمكنك زيادة السمك في خانة الإدخال وسيقوم البرنامج فوراً بإعادة حساب حديد التسليح تلقائياً.</span>
                            </div>
                        </div>"""
                    )

        man_tf = float(raw_tf)

        is_manual_sizing = "Manual" in sizing_mode_eq or "يدوي" in sizing_mode_eq
        c_L_side = (man_Lf - min_Lf_req) / 2.0
        c_B_side = (man_Bf - min_Bf_req) / 2.0

        if is_manual_sizing:
            is_edge_clearance_safe = (
                (man_Lf >= min_Lf_req - 1e-4)
                and (man_Bf >= min_Bf_req - 1e-4)
                and (c_L_side >= 0.20 - 1e-4)
                and (c_B_side >= 0.20 - 1e-4)
            )
            if man_Lf < min_Lf_req or man_Bf < min_Bf_req:
                play_siren_alarm()
                st.html(
                    f"""<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #7f1d1d 0%, #b91c1c 50%, #7f1d1d 100%) !important; color: #ffffff !important; border: 3px solid #ef4444 !important; border-radius: 14px !important; padding: 20px 24px !important; margin: 16px 0 !important; box-shadow: 0 10px 28px rgba(185, 28, 28, 0.6) !important;">
<div style="font-size: 24px; font-weight: 900; color: #ffffff !important; margin-bottom: 10px; line-height: 1.4; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">
🚨 ❌ خطأ هندسي وإنشائي جسيم (Footprint Dimensions Violation):
</div>
<div style="font-size: 21px; font-weight: 800; color: #ffffff !important; line-height: 1.9; text-shadow: 0 1px 3px rgba(0,0,0,0.5);">
أبعاد القاعدة الخرسانية (<span dir="ltr" style="color: #fca5a5 !important; font-weight: 900; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 6px;">{man_Lf:.2f} × {man_Bf:.2f} m</span>) أصغر من بصمة المعدة (<span dir="ltr" style="color: #fde047 !important; font-weight: 900;">{min_Lf_req:.2f} × {min_Bf_req:.2f} m</span>)! يجب ألا يقل طول وعرض القاعدة عن بصمة المعدة لتأمين تثبيت مسامير الجشمة (<span dir="ltr">Anchor Bolts</span>) والعوازل داخل الكتلة الخرسانية.
</div>
</div>"""
                )
            elif not is_edge_clearance_safe:
                play_siren_alarm()
                st.html(
                    f"""<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #991b1b 0%, #dc2626 50%, #991b1b 100%) !important; color: #ffffff !important; border: 3px solid #fca5a5 !important; border-radius: 14px !important; padding: 22px 26px !important; margin: 16px 0 !important; box-shadow: 0 10px 28px rgba(220, 38, 38, 0.65) !important;">
<div style="font-size: 25px; font-weight: 900; color: #ffffff !important; margin-bottom: 12px; line-height: 1.4; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">
🚨 ⚠️ تنبيه هندسي لخلوص الحواف (Edge Distance Warning):
</div>
<div style="font-size: 22px; font-weight: 800; color: #ffffff !important; line-height: 1.95; text-shadow: 0 1px 3px rgba(0,0,0,0.5);">
خلوص الحواف الفعلي (<span dir="ltr" style="color: #fef08a !important; font-weight: 900; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 6px;">{max(0.0, c_L_side*100):.1f} cm طولياً / {max(0.0, c_B_side*100):.1f} cm عرضياً</span>) أقل من الموصى به كودياً (<span dir="ltr" style="color: #ffffff !important; font-weight: 900;">20 ~ 40 cm</span>). يُرجى زيادة الأبعاد لتأمين مسامير التثبيت ومنع تشظي حواف الخرسانة (<span dir="ltr">Edge Spalling</span>).
</div>
</div>"""
                )
            else:
                st.html(
                    f"""<div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #064e3b 0%, #059669 50%, #064e3b 100%) !important; color: #ffffff !important; border: 2px solid #34d399 !important; border-radius: 12px !important; padding: 16px 22px !important; margin: 14px 0 !important; box-shadow: 0 6px 20px rgba(5, 150, 105, 0.35) !important;">
<div style="font-size: 20px; font-weight: 900; color: #ffffff !important; line-height: 1.6;">
✅ أبعاد القاعدة وخلوص الحواف آمنة ومستوفية كودياً:
<span style="font-size: 18px; font-weight: 800; color: #a7f3d0 !important;">خلوص إضافي = <span dir="ltr">{c_L_side*100:.1f} cm</span> طولياً، و <span dir="ltr">{c_B_side*100:.1f} cm</span> عرضياً.</span>
</div>
</div>"""
                )
        else:
            is_edge_clearance_safe = True

    # ── OUTPUT SECTIONS & EXPANDERS ──
    is_outputs_allowed = is_edge_clearance_safe and is_thickness_safe

    if not is_outputs_allowed:
        # Sections 2 & 3 are completely locked and cannot be opened or expanded
        lock_reasons = []
        if not is_thickness_safe:
            lock_reasons.append(
                f"سمك الخرسانة الفعلي المدخل (<span dir='ltr' style='color:#fca5a5; font-weight:900;'>{man_tf:.2f} m</span>) أقل من الحد الأدنى للعمق الآمن الناتج عن التصميم الإنشائي (<span dir='ltr' style='color:#fde047; font-weight:900;'>[{T_design:.2f} m]</span>). يُرجى تعديل السمك ليصبح ≥ <span dir='ltr' style='color:#fde047; font-weight:900;'>{T_design:.2f} m</span>."
            )
        if not is_edge_clearance_safe:
            lock_reasons.append(
                f"أبعاد القاعدة الخرسانية أو خلوص الحواف الفعلي (<span dir='ltr' style='color:#fef08a; font-weight:900;'>{max(0.0, c_L_side*100):.1f} cm طولياً / {max(0.0, c_B_side*100):.1f} cm عرضياً</span>) غير مستوفية للحد الأدنى الموصى به كودياً (<span dir='ltr' style='color:#fde047; font-weight:900;'>20 ~ 40 cm</span>) لتأمين مسامير التثبيت ومنع تشظي الحواف."
            )
        reasons_html = "<br>⚠️ ".join(lock_reasons)

        st.html(
            f"""<div dir="rtl" style="direction: rtl !important; text-align: right !important; margin: 20px 0;">
<div style="background: rgba(15, 23, 42, 0.75); border: 2px dashed #ef4444; border-radius: 12px; padding: 18px 24px; margin-bottom: 16px; box-shadow: 0 4px 16px rgba(239, 68, 68, 0.15); cursor: not-allowed;">
<div style="font-size: 20px; font-weight: 900; color: #f87171; display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
<span style="font-size: 22px;">🔒</span>
<span>📊 2. المخرجات النهائية والتحققات الهندسية والتسليح (مُقفل - غير متاح للفتح)</span>
</div>
<div style="font-size: 16px; color: #cbd5e1; line-height: 1.8; font-weight: 700;">
⚠️ <b>تم قفل هذا القسم بالكامل وتعطيل إمكانية فتحه:</b> {reasons_html}<br>
⚙️ يُرجى تصحيح المدخلات في قسم البيانات أعلاه لتستوفي المحددات الهندسية والكودية، وسيتم تلقائياً فك القفل وجعل الأقسام متاحة كـ Expanders وعرض كامل الحسابات والتسليح والمخططات.
</div>
</div>

<div style="background: rgba(15, 23, 42, 0.75); border: 2px dashed #ef4444; border-radius: 12px; padding: 18px 24px; box-shadow: 0 4px 16px rgba(239, 68, 68, 0.15); cursor: not-allowed;">
<div style="font-size: 20px; font-weight: 900; color: #f87171; display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
<span style="font-size: 22px;">🔒</span>
<span>📐 3. المخططات الهندسية وتصدير المذكرة الحسابية (مُقفل - غير متاح للفتح)</span>
</div>
<div style="font-size: 16px; color: #cbd5e1; line-height: 1.8; font-weight: 700;">
⚠️ <b>تم قفل هذا القسم بالكامل وتعطيل إمكانية فتحه:</b> لا يمكن توليد المخططات الهندسية (2D CAD Blueprints) أو تصدير المذكرات الحسابية (HTML / PDF) قبل استيفاء سمك الخرسانة الآمن المطلوب كودياً وخلوص الحواف وأبعاد بصمة المعدة.
</div>
</div>
</div>"""
        )
    else:
        res_eq = compute_equipment_foundation_design(
            eq_weight_ton=float(eq_weight),
            eq_shape=eq_shape,
            eq_length_m=float(eq_len),
            eq_width_m=float(eq_wid),
            eq_dia_m=float(eq_dia),
            isolation_type=iso_type,
            operating_rpm=float(op_rpm),
            ks_kg_cm3=float(ks_eq),
            fc_kg_cm2=float(fc_eq),
            fy_kg_cm2=float(fy_eq),
            q_all_kg_cm2=float(q_all_eq),
            sizing_mode=sizing_mode_eq,
            manual_Lf_m=float(man_Lf),
            manual_Bf_m=float(man_Bf),
            manual_tf_m=float(man_tf),
            target_mass_ratio=float(mass_ratio_target),
            cover_cm=float(cover_eq),
            phi_bot_mm=int(phi_bot_eq),
            phi_top_mm=int(phi_top_eq),
        )
        with st.expander("📊 2. المخرجات النهائية والتحققات الهندسية والتسليح (Final Outputs & Code Verification)", expanded=True):
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                bg_k1 = "#0f172a" if res_eq["is_footprint_safe"] else "#7f1d1d"
                bd_k1 = "#38bdf8" if res_eq["is_footprint_safe"] else "#ef4444"
                footprint_badge = "✅ مستوفية لبصمة المعدة" if res_eq["is_footprint_safe"] else "⚠️ أصغر من بصمة المعدة!"
                overridden_lbl = " (مُعدل بالزيادة)" if res_eq.get("is_tf_overridden") else " (المعتمد كودياً)"
                st.markdown(
                    f"""<div dir="rtl" style="direction:rtl !important; background:{bg_k1}; border:2px solid {bd_k1}; border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:15px; color:#93c5fd; font-weight:800;">الأبعاد النهائية للقاعدة (Lf × Bf × tf)</div>
                        <div style="font-size:25px; font-weight:900; color:#ffffff; margin:6px 0;" dir="ltr">{res_eq['Lf_m']:.2f} × {res_eq['Bf_m']:.2f} × {res_eq['tf_m']:.2f} m</div>
                        <div style="font-size:13.5px; color:#fde047; font-weight:700;">سمك التصميم: <span dir="ltr">T_design = {res_eq['T_design_m']:.2f} m</span>{overridden_lbl}</div>
                        <div style="font-size:14px; color:{'#a7f3d0' if res_eq['is_footprint_safe'] else '#fca5a5'}; font-weight:700;">{footprint_badge} (الحجم = <span dir="ltr">{res_eq['vol_f_m3']:.2f} m³</span>)</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with k2:
                st.markdown(
                    f"""<div dir="rtl" style="direction:rtl !important; background:#0f172a; border:2px solid #f59e0b; border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:15px; color:#fde047; font-weight:800;">الوزن الذاتي المحسوب تلقائياً (W_f)</div>
                        <div style="font-size:26px; font-weight:900; color:#fde047; margin:6px 0;" dir="ltr">{res_eq['Wf_ton']:.2f} ton</div>
                        <div style="font-size:14px; color:#cbd5e1; font-weight:700;">نسبة الكتلة <span dir="ltr">W_f / W_eq = {res_eq['actual_mass_ratio']:.2f}x</span></div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with k3:
                bg_s = "#064e3b" if res_eq["is_soil_safe"] else "#7f1d1d"
                bd_s = "#22c55e" if res_eq["is_soil_safe"] else "#ef4444"
                st.markdown(
                    f"""<div dir="rtl" style="direction:rtl !important; background:{bg_s}; border:2px solid {bd_s}; border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:15px; color:#e2e8f0; font-weight:800;">إجهاد التربة الفعلي / المسموح</div>
                        <div style="font-size:25px; font-weight:900; color:#ffffff; margin:6px 0;" dir="ltr">{res_eq['q_act_kg_cm2']:.2f} / {res_eq['q_all_kg_cm2']:.2f} kg/cm²</div>
                        <div style="font-size:14px; color:#a7f3d0; font-weight:700;">{'✅ آمن (SAFE)' if res_eq['is_soil_safe'] else '⚠️ غير آمن (UNSAFE)'} (<span dir="ltr">{res_eq['ratio_soil']*100:.1f}%</span>)</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with k4:
                bg_p = "#064e3b" if res_eq["is_punching_safe"] else "#7f1d1d"
                bd_p = "#22c55e" if res_eq["is_punching_safe"] else "#ef4444"
                st.markdown(
                    f"""<div dir="rtl" style="direction:rtl !important; background:{bg_p}; border:2px solid {bd_p}; border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:15px; color:#e2e8f0; font-weight:800;">فحص الاختراق (Punching Shear)</div>
                        <div style="font-size:25px; font-weight:900; color:#ffffff; margin:6px 0;" dir="ltr">{res_eq['q_up_kg_cm2']:.2f} / {res_eq['q_cup_all_kg_cm2']:.2f} kg/cm²</div>
                        <div style="font-size:14px; color:#a7f3d0; font-weight:700;">{'✅ آمن (SAFE)' if res_eq['is_punching_safe'] else '⚠️ غير آمن (UNSAFE)'} (<span dir="ltr">{res_eq['ratio_punching']*100:.1f}%</span>)</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

            # Reinforcement & Dynamic Summary Banner
            r_c1, r_c2 = st.columns(2)
            with r_c1:
                st.markdown(
                    f"""<div class="m10-rtl-panel" dir="rtl" style="direction:rtl !important; text-align:right !important; background:rgba(15,23,42,0.85); border:2px solid #22c55e; border-radius:12px; padding:16px 20px; unicode-bidi:isolate;">
                        <div dir="rtl" style="font-size:18px; font-weight:900; color:#4ade80; margin-bottom:10px; direction:rtl !important; text-align:right !important; width:100%;">🔩 تسليح القاعدة السفلي والعلوي والكميات (Reinforcement Summary)</div>
                        <div dir="rtl" style="font-size:15.5px; color:#f1f5f9; line-height:1.95; font-weight:700; direction:rtl !important; text-align:right !important; width:100%;">
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>شبكة التسليح السفلية (Bottom Mesh):</b> <span dir="ltr" style="color:#fde047; font-size:18px; font-weight:900; unicode-bidi:isolate;">{res_eq['n_bars_bot_m']} Φ {res_eq['phi_bot_mm']} / m'</span> في الاتجاهين (المسافة = <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['spacing_bot_cm']} cm</span>)</div>
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important; padding-right:16px;">▫️ المساحة المطلوبة = <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['As_bot_req_cm2_m']:.2f} cm²/m'</span> | المساحة المتوفرة = <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_eq['As_bot_prov_cm2_m']:.2f} cm²/m'</span></div>
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>شبكة التسليح العلوية (Top Mesh):</b> <span dir="ltr" style="color:#38bdf8; font-size:18px; font-weight:900; unicode-bidi:isolate;">{res_eq['n_bars_top_m']} Φ {res_eq['phi_top_mm']} / m'</span> في الاتجاهين (المسافة = <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['spacing_top_cm']} cm</span>)</div>
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important; padding-right:16px;">▫️ المساحة المطلوبة = <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['As_top_req_cm2_m']:.2f} cm²/m'</span> | المساحة المتوفرة = <span dir="ltr" style="color:#38bdf8; unicode-bidi:isolate;">{res_eq['As_top_prov_cm2_m']:.2f} cm²/m'</span></div>
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>إجمالي وزن حديد التسليح للقاعدة:</b> <span dir="ltr" style="color:#f472b6; font-size:17px; font-weight:900; unicode-bidi:isolate;">{res_eq['total_rebar_weight_kg']:.1f} kg ({res_eq['total_rebar_weight_ton']:.3f} ton)</span> — بمعدل <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['steel_rate_kg_m3']:.1f} kg/m³</span></div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            with r_c2:
                st.markdown(
                    f"""<div class="m10-rtl-panel" dir="rtl" style="direction:rtl !important; text-align:right !important; background:rgba(15,23,42,0.85); border:2px solid #38bdf8; border-radius:12px; padding:16px 20px; unicode-bidi:isolate;">
                        <div dir="rtl" style="font-size:18px; font-weight:900; color:#38bdf8; margin-bottom:10px; direction:rtl !important; text-align:right !important; width:100%;">📳 تحليل الأحمال الاهتزازية والرنين (Dynamic & Vibration Analysis)</div>
                        <div dir="rtl" style="font-size:15.5px; color:#f1f5f9; line-height:1.95; font-weight:700; direction:rtl !important; text-align:right !important; width:100%;">
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>حالة الارتكاز والعزل:</b> {res_eq['isolation_type']}</div>
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>حمل المعدة التصميمي بالمضاعف الديناميكي (<span dir="ltr" style="unicode-bidi:isolate;">DF = {res_eq['dyn_factor']:.2f}</span>):</b> <span dir="ltr" style="color:#fde047; unicode-bidi:isolate;">{res_eq['P_eq_design_ton']:.2f} ton</span></div>
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>الوزن الذاتي للقاعدة (<span dir="ltr" style="unicode-bidi:isolate;">V × 2.5 t/m³</span>):</b> <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_eq['Wf_ton']:.2f} ton</span> | <b>الحمل الكلي:</b> <span dir="ltr" style="color:#38bdf8; unicode-bidi:isolate;">{res_eq['P_total_working_ton']:.2f} ton</span></div>
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>التردد الطبيعي للقاعدة والتربة (<span dir="ltr" style="unicode-bidi:isolate;">fn</span>):</b> <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['fn_hz']:.2f} Hz</span> | <b>تردد التشغيل (<span dir="ltr" style="unicode-bidi:isolate;">f_op</span>):</b> <span dir="ltr" style="unicode-bidi:isolate;">{res_eq['f_op_hz']:.2f} Hz</span></div>
                            <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>حالة الرنين الديناميكي:</b> <span style="color:{'#4ade80' if res_eq['is_resonance_safe'] else '#f87171'};">{res_eq['resonance_status_ar']}</span></div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            # Detailed Verification Table
            eq_checks = [
                (
                    "1. كفاية الأبعاد الهندسية وبصمة المعدة (Footprint & Clearance Check)",
                    f"Lf = {res_eq['Lf_m']:.2f} m, Bf = {res_eq['Bf_m']:.2f} m (خلوص: {res_eq['clearance_L_cm']:.0f}×{res_eq['clearance_B_cm']:.0f} cm)",
                    f"≥ بصمة المعدة ({res_eq['min_req_Lf_m']:.2f}×{res_eq['min_req_Bf_m']:.2f} m)",
                    res_eq["is_footprint_safe"],
                ),
                (
                    "2. كفاية سمك الخرسانة والعمق الآمن (Safe Concrete Thickness tf ≥ T_design)",
                    f"tf = {res_eq['tf_m']:.2f} m ({'مُزاد ومُعاد حسابه' if res_eq.get('is_tf_overridden') else 'مطابق لسمك التصميم'})",
                    f"≥ T_design ({res_eq['T_design_m']:.2f} m)",
                    res_eq["tf_m"] >= res_eq["T_design_m"] - 1e-4,
                ),
                (
                    "3. الوزن الذاتي للقاعدة ونسبة القصور الذاتي (Foundation Self-Weight Ratio)",
                    f"W_f = {res_eq['Wf_ton']:.2f} t ({res_eq['actual_mass_ratio']:.2f} W_eq)",
                    "محسوب تلقائياً (DF = 1.2)" if res_eq["is_isolated"] else f"≥ {res_eq['req_mass_ratio_min']:.1f}×W_eq ({res_eq['req_min_wf_ton']:.1f} t)",
                    res_eq["is_mass_ratio_safe"],
                ),
                (
                    "4. فحص إجهاد التربة تحت الأحمال الكلية (Soil Bearing Capacity Check)",
                    f"q_act = {res_eq['q_act_kg_cm2']:.2f} kg/cm² ({res_eq['q_act_ton_m2']:.1f} t/m²)",
                    f"q_all = {res_eq['q_all_kg_cm2']:.2f} kg/cm² ({res_eq['q_all_ton_m2']:.1f} t/m²)",
                    res_eq["is_soil_safe"],
                ),
                (
                    "5. فحص القص الثاقب / الاختراق (Punching Shear Check - ECP 203)",
                    f"q_up = {res_eq['q_up_kg_cm2']:.2f} kg/cm²",
                    f"q_cup = {res_eq['q_cup_all_kg_cm2']:.2f} kg/cm²",
                    res_eq["is_punching_safe"],
                ),
                (
                    "6. فحص القص الحرج ذو الاتجاه الواحد (One-Way Beam Shear Check)",
                    f"q_u = {res_eq['qu_1way_kg_cm2']:.2f} kg/cm²",
                    f"q_cu = {res_eq['qcu_1way_kg_cm2']:.2f} kg/cm²",
                    res_eq["is_1way_shear_safe"],
                ),
                (
                    "7. التحقق من التردد الطبيعي وتجنب الرنين (Resonance Check)",
                    f"f_op / f_n = {res_eq['freq_ratio']:.2f} ({res_eq['f_op_hz']:.1f} / {res_eq['fn_hz']:.1f} Hz)",
                    "خارج نطاق الرنين [0.70 – 1.30]",
                    res_eq["is_resonance_safe"],
                ),
            ]

            rows_html = []
            for idx, (c_name, c_act, c_lim, c_ok) in enumerate(eq_checks):
                bg_r = "rgba(15, 23, 42, 0.75)" if idx % 2 == 0 else "rgba(30, 41, 59, 0.75)"
                badge = (
                    '<span style="background:rgba(34,197,94,0.2); color:#4ade80; border:1.5px solid #22c55e; padding:4px 12px; border-radius:8px; font-weight:900;">✅ آمن ومطابق (SAFE)</span>'
                    if c_ok else
                    '<span style="background:rgba(239,68,68,0.2); color:#f87171; border:1.5px solid #ef4444; padding:4px 12px; border-radius:8px; font-weight:900;">⚠️ غير آمن (UNSAFE)</span>'
                )
                rows_html.append(
                    f'<tr style="background:{bg_r}; border-bottom:1px solid #334155;">'
                    f'<td style="padding:12px 16px; font-size:17px; font-weight:800; color:#ffffff; text-align:right; direction:rtl;">{c_name}</td>'
                    f'<td style="padding:12px 16px; font-size:18px; font-weight:900; color:#38bdf8; text-align:center;" dir="ltr">{c_act}</td>'
                    f'<td style="padding:12px 16px; font-size:17px; font-weight:800; color:#fbbf24; text-align:center;" dir="ltr">{c_lim}</td>'
                    f'<td style="padding:12px 16px; text-align:center;">{badge}</td>'
                    f'</tr>'
                )

            st.markdown(
                '<div dir="rtl" style="direction:rtl !important; overflow-x:auto; border:2px solid #38bdf8; border-radius:12px; margin-top:16px;">'
                '<table dir="rtl" style="direction:rtl !important; width:100%; border-collapse:collapse; background:#0b1329;">'
                '<thead><tr style="background:#1e293b; border-bottom:2px solid #38bdf8;">'
                '<th style="padding:14px 16px; font-size:18px; color:#38bdf8; text-align:right;">بند التحقق الكودي (Verification Item)</th>'
                '<th style="padding:14px 16px; font-size:18px; color:#38bdf8; text-align:center;">القيمة المحسوبة (Actual)</th>'
                '<th style="padding:14px 16px; font-size:18px; color:#fbbf24; text-align:center;">الحد المسموح (Allowable)</th>'
                '<th style="padding:14px 16px; font-size:18px; color:#4ade80; text-align:center;">الحالة (Status)</th>'
                '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>',
                unsafe_allow_html=True,
            )

        with st.expander("📐 3. المخططات الهندسية وتصدير المذكرة الحسابية (2D CAD Blueprints & Report Export)", expanded=True):
            sketch_eq_b64 = generate_equipment_foundation_sketches(res_eq)
            st.image(f"data:image/png;base64,{sketch_eq_b64}", use_container_width=True)

            summary_eq_rows = [
                ("الوزن التشغيلي للمعدة (Operating Weight)", f"{res_eq['eq_weight_ton']:.2f} ton"),
                ("حالة العزل الاهتزازي (Isolation Mode)", res_eq["isolation_type"]),
                ("الأبعاد النهائية للقاعدة (Lf × Bf × tf)", f"{res_eq['Lf_m']:.2f} m × {res_eq['Bf_m']:.2f} m × {res_eq['tf_m']:.2f} m"),
                ("حجم الخرسانة والوزن الذاتي للقاعدة (W_f @ 2.5 t/m³)", f"V = {res_eq['vol_f_m3']:.2f} m³ | W_f = {res_eq['Wf_ton']:.2f} ton"),
                ("إجمالي الحمل التصميمي التشغيلي (Total Working Load)", f"{res_eq['P_total_working_ton']:.2f} ton"),
                ("إجهاد التربة الفعلي / المسموح به", f"{res_eq['q_act_kg_cm2']:.2f} / {res_eq['q_all_kg_cm2']:.2f} kg/cm²"),
                ("إجهاد الاختراق الفعلي / المسموح (Punching Shear)", f"{res_eq['q_up_kg_cm2']:.2f} / {res_eq['q_cup_all_kg_cm2']:.2f} kg/cm²"),
                ("التسليح السفلي في الاتجاهين (Bottom Reinforcement)", f"{res_eq['n_bars_bot_m']} Φ {res_eq['phi_bot_mm']} / m' (As = {res_eq['As_bot_prov_cm2_m']:.2f} cm²/m')"),
                ("التسليح العلوي في الاتجاهين (Top Reinforcement)", f"{res_eq['n_bars_top_m']} Φ {res_eq['phi_top_mm']} / m' (As = {res_eq['As_top_prov_cm2_m']:.2f} cm²/m')"),
                ("إجمالي كمية حديد التسليح للقاعدة", f"{res_eq['total_rebar_weight_kg']:.1f} kg ({res_eq['total_rebar_weight_ton']:.3f} ton)"),
            ]
            html_eq_report = generate_m10_calculation_sheet_html(
                title_ar="مذكرة الحسابات الإنشائية لقاعدة المعدة الميكانيكية",
                subtitle_en="Equipment Foundation Structural & Dynamic Calculation Sheet (ECP 203 / ACI 351.3R)",
                rows_summary=summary_eq_rows,
                checks_list=eq_checks,
                sketch_b64=sketch_eq_b64,
            )

            dl1, dl2, dl3 = st.columns(3)
            with dl1:
                st.download_button(
                    "📥 تحميل المخطط الهندسي (PNG)",
                    data=base64.b64decode(sketch_eq_b64),
                    file_name=f"Equipment_Foundation_{res_eq['Lf_m']:.1f}x{res_eq['Bf_m']:.1f}m.png",
                    mime="image/png",
                    use_container_width=True,
                )
            with dl2:
                st.download_button(
                    "🌐 تحميل المذكرة الحسابية (HTML)",
                    data=html_eq_report,
                    file_name=f"Equipment_Foundation_Report_{res_eq['Lf_m']:.1f}x{res_eq['Bf_m']:.1f}m.html",
                    mime="text/html",
                    use_container_width=True,
                )
            with dl3:
                if st.button("📕 توليد وتحميل ملف PDF", key="btn_m10_eq_pdf", use_container_width=True):
                    with st.spinner("جاري تجهيز ملف PDF..."):
                        pdf_b = html_to_pdf_bytes(html_eq_report)
                        if pdf_b:
                            st.download_button(
                                "📥 اضغط لحفظ التقرير PDF",
                                data=pdf_b,
                                file_name="Equipment_Foundation_Report.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )


# ===============================================================================
#  6. STREAMLIT UI RENDERER — SECTION 2: LIQUID STORAGE TANK FOUNDATIONS
# ===============================================================================

def _render_liquid_storage_tanks_tab():
    st.markdown(
        """
        <div dir="rtl" style="direction: rtl !important; text-align: right !important; background: linear-gradient(135deg, #0f172a 0%, #064e3b 60%, #0f172a 100%); border: 2px solid #10b981; border-radius: 12px; padding: 16px 22px; margin-bottom: 18px; box-shadow: 0 4px 18px rgba(16, 185, 129, 0.25);">
            <div style="font-size: 20px; font-weight: 900; color: #fde047; margin-bottom: 6px; direction: rtl !important; text-align: right !important;">
                🛢️ ثانياً: قسم تصميم قواعد الخزانات السائلة (Liquid Storage Tank Foundations)
            </div>
            <div style="font-size: 14.5px; color: #e2e8f0; line-height: 1.75; font-weight: 600; direction: rtl !important; text-align: right !important;">
                قسم مستقل ومتكامل لتصميم القواعد الخرسانية المسلحة للخزانات الدائرية (<span dir="ltr">Circular</span>) والمستطيلة (<span dir="ltr">Rectangular</span>) المصنوعة من الصاج (<span dir="ltr">Steel Sheet</span>) أو البلاستيك (<span dir="ltr">Plastic</span>)، مع الحساب التلقائي لوزن الخزان ووزن السائل من السعة بالبراميل (<span dir="ltr">Barrels</span>) والوزن الذاتي الإجباري للقاعدة (<span dir="ltr">2.5 t/m³</span>) وفقاً للكود المصري <span dir="ltr">ECP 203</span> و <span dir="ltr">ACI 350</span>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📥 1. مدخلات الخزان الهندسية وسعة التخزين والمواد والتربة (Tank, Capacity & Soil Inputs)", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#34d399; margin-bottom:10px;'>🛢️ 1. بيانات هندسية ومادية للخزان</div>", unsafe_allow_html=True)
            tank_shape = S.selectbox(
                "الشكل الهندسي للخزان (Tank Shape):",
                "m10_tk_shape",
                ["دائري (Circular)", "مستطيل (Rectangular)"],
            )
            if "دائري" in tank_shape or "Circular" in tank_shape:
                tank_dia = S.number_input(
                    "قطر الخزان الدائري D_tank [m]:",
                    "m10_tk_dia_m",
                    value=6.00,
                    min_value=1.00,
                    max_value=60.0,
                    step=0.25,
                )
                tank_len, tank_wid = tank_dia, tank_dia
            else:
                tc1, tc2 = st.columns(2)
                with tc1:
                    tank_len = S.number_input(
                        "طول الخزان L_tank [m]:",
                        "m10_tk_len_m",
                        value=6.00,
                        min_value=1.00,
                        max_value=60.0,
                        step=0.25,
                    )
                with tc2:
                    tank_wid = S.number_input(
                        "عرض الخزان B_tank [m]:",
                        "m10_tk_wid_m",
                        value=4.00,
                        min_value=1.00,
                        max_value=60.0,
                        step=0.25,
                    )
                tank_dia = tank_len

            tank_mat = S.selectbox(
                "نوع مادة جسم الخزان (Tank Material):",
                "m10_tk_material",
                ["صاج صلب (Steel Sheet)", "بلاستيك مقوى / بولي إيثيلين (Plastic)"],
            )
            sheet_thk = S.number_input(
                "تخانة الصاج / الجدار (Sheet Thickness) [mm]:",
                "m10_tk_sheet_thk_mm",
                value=8.0,
                min_value=2.0,
                max_value=40.0,
                step=0.5,
            )

        with c2:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#34d399; margin-bottom:10px;'>🛢️ 2. سعة التخزين وخصائص السائل</div>", unsafe_allow_html=True)
            cap_bbl = S.number_input(
                "سعة الخزان بالبراميل (Storage Capacity) [Barrels]:",
                "m10_tk_cap_bbl",
                value=1000.0,
                min_value=10.0,
                max_value=200000.0,
                step=50.0,
                help="1 برميل قياسي = 158.987 لتر = 0.158987 م³",
            )
            sg_liq = S.number_input(
                "الكثافة النوعية للسائل / البترول (Specific Gravity):",
                "m10_tk_sg",
                value=0.85,
                min_value=0.60,
                max_value=1.50,
                step=0.05,
                help="الكثافة النوعية للبترول الخام والوقود تتراوح عادة بين 0.80 و 0.90 (الماء = 1.00)",
            )
            gwt_head = S.number_input(
                "عمق الغمر بالمياه الجوفية لفحص الطفو [m]:",
                "m10_tk_gwt_m",
                value=0.50,
                min_value=0.0,
                max_value=5.0,
                step=0.10,
            )
            lat_coeff = S.number_input(
                "معامل القوة الأفقية للرياح/الزلازل (Lateral Coeff):",
                "m10_tk_lat_coeff",
                value=0.08,
                min_value=0.02,
                max_value=0.30,
                step=0.01,
            )

        with c3:
            st.markdown("<div dir='rtl' style='direction:rtl !important; text-align:right !important; font-size:18px; font-weight:900; color:#34d399; margin-bottom:10px;'>🧱 3. خواص المواد والتربة وأبعاد القاعدة</div>", unsafe_allow_html=True)
            fc_tk = S.number_input(
                "إجهاد الخرسانة fc' / fcu [kg/cm²]:",
                "m10_tk_fc",
                value=300.0,
                min_value=200.0,
                max_value=600.0,
                step=25.0,
            )
            fy_tk = S.number_input(
                "إجهاد حديد التسليح fy [kg/cm²]:",
                "m10_tk_fy",
                value=3600.0,
                min_value=2400.0,
                max_value=5000.0,
                step=200.0,
            )
            q_all_tk = S.number_input(
                "إجهاد التربة المسموح به q_all [kg/cm²]:",
                "m10_tk_q_all",
                value=1.50,
                min_value=0.40,
                max_value=6.00,
                step=0.10,
            )
            sizing_mode_tk = S.selectbox(
                "نظام تحديد أبعاد القاعدة الخرسانية:",
                "m10_tk_sizing_mode",
                ["حساب أوتوماتيكي للأبعاد (Auto-Sizing)", "إدخال يدوي للأبعاد (Manual Override)"],
            )

        st.markdown("---")
        t_reb1, t_reb2, t_reb3, t_reb4 = st.columns(4)
        with t_reb1:
            phi_bot_tk = S.selectbox("قطر التسليح السفلي Φ_bot [mm]:", "m10_tk_phi_bot", ECP_DIAMETERS, index=2)
        with t_reb2:
            phi_top_tk = S.selectbox("قطر التسليح العلوي Φ_top [mm]:", "m10_tk_phi_top", ECP_DIAMETERS, index=1)
        with t_reb3:
            cover_tk = S.number_input("الغطاء الخرساني Cover [cm]:", "m10_tk_cover", value=7.5, min_value=5.0, max_value=12.0, step=0.5)
        with t_reb4:
            if "Manual" in sizing_mode_tk or "يدوي" in sizing_mode_tk:
                mc1, mc2 = st.columns(2)
                with mc1:
                    man_ov_tk = S.number_input("رفرفة القاعدة c [m]:", "m10_tk_man_ov", value=0.60, min_value=0.20, max_value=5.0, step=0.10)
                with mc2:
                    man_tf_tk = S.number_input("سمك القاعدة tf [m]:", "m10_tk_man_tf", value=0.60, min_value=0.30, max_value=4.0, step=0.05)
            else:
                man_ov_tk, man_tf_tk = 0.60, 0.60
                st.markdown(
                    "<div dir='rtl' style='direction:rtl !important; background:rgba(16,185,129,0.15); border:1.5px solid #10b981; border-radius:8px; padding:10px; text-align:center; color:#a7f3d0; font-weight:800; margin-top:6px;'>✨ الأبعاد والرفرفة والسمك تحسب تلقائياً</div>",
                    unsafe_allow_html=True,
                )

    res_tk = compute_liquid_tank_foundation_design(
        tank_shape=tank_shape,
        tank_dia_m=float(tank_dia),
        tank_length_m=float(tank_len),
        tank_width_m=float(tank_wid),
        tank_material=tank_mat,
        sheet_thk_mm=float(sheet_thk),
        capacity_barrels=float(cap_bbl),
        specific_gravity=float(sg_liq),
        fc_kg_cm2=float(fc_tk),
        fy_kg_cm2=float(fy_tk),
        q_all_kg_cm2=float(q_all_tk),
        sizing_mode=sizing_mode_tk,
        manual_overhang_m=float(man_ov_tk),
        manual_tf_m=float(man_tf_tk),
        gwt_depth_m=float(gwt_head),
        wind_seismic_coeff=float(lat_coeff),
        cover_cm=float(cover_tk),
        phi_bot_mm=int(phi_bot_tk),
        phi_top_mm=int(phi_top_tk),
    )

    # ── DETAILED WEIGHTS & OUTPUTS ──
    with st.expander("📊 2. التقرير الحسابي التفصيلي للأوزان والأبعاد والتحققات والتسليح (Detailed Calculation Report)", expanded=True):
        # 4 Weight & Dimension Highlight Cards
        w1, w2, w3, w4 = st.columns(4)
        with w1:
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#0f172a; border:2px solid #38bdf8; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#93c5fd; font-weight:800;">وزن هيكل الخزان الفارغ (W_tank)</div>
                    <div style="font-size:26px; font-weight:900; color:#ffffff; margin:6px 0;" dir="ltr">{res_tk['W_tank_empty_ton']:.2f} ton</div>
                    <div style="font-size:13.5px; color:#cbd5e1; font-weight:700;">{res_tk['tank_material']} (تخانة <span dir="ltr">{res_tk['sheet_thk_mm']:.1f} mm</span>)</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with w2:
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#0f172a; border:2px solid #0ea5e9; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#7dd3fc; font-weight:800;">وزن السائل الإجمالي (W_liquid)</div>
                    <div style="font-size:26px; font-weight:900; color:#38bdf8; margin:6px 0;" dir="ltr">{res_tk['W_liquid_ton']:.2f} ton</div>
                    <div style="font-size:13.5px; color:#cbd5e1; font-weight:700;" dir="ltr">{res_tk['capacity_barrels']:.0f} BBL = {res_tk['vol_liquid_m3']:.1f} m³ (SG={res_tk['specific_gravity']:.2f})</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with w3:
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#0f172a; border:2px solid #f59e0b; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#fde047; font-weight:800;">الوزن الذاتي للقاعدة (W_foundation)</div>
                    <div style="font-size:26px; font-weight:900; color:#fde047; margin:6px 0;" dir="ltr">{res_tk['Wf_ton']:.2f} ton</div>
                    <div style="font-size:13.5px; color:#cbd5e1; font-weight:700;">الحجم = <span dir="ltr">{res_tk['vol_f_m3']:.2f} m³ × 2.5 t/m³</span></div>
                </div>""",
                unsafe_allow_html=True,
            )
        with w4:
            dim_str = (
                f"D_f = {res_tk['Df_m']:.2f} m × tf = {res_tk['tf_m']:.2f} m"
                if res_tk["is_circular"]
                else f"{res_tk['Lf_m']:.2f} × {res_tk['Bf_m']:.2f} × {res_tk['tf_m']:.2f} m"
            )
            st.markdown(
                f"""<div dir="rtl" style="direction:rtl !important; background:#064e3b; border:2px solid #10b981; border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:15px; color:#a7f3d0; font-weight:800;">الأبعاد الهندسية النهائية للقاعدة</div>
                    <div style="font-size:22px; font-weight:900; color:#ffffff; margin:8px 0;" dir="ltr">{dim_str}</div>
                    <div style="font-size:13.5px; color:#fde047; font-weight:700;">الحمل الكلي = <span dir="ltr">{res_tk['P_total_working_ton']:.2f} ton</span></div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        tk_c1, tk_c2 = st.columns(2)
        with tk_c1:
            st.markdown(
                f"""<div class="m10-rtl-panel" dir="rtl" style="direction:rtl !important; text-align:right !important; background:rgba(15,23,42,0.85); border:2px solid #22c55e; border-radius:12px; padding:16px 20px; unicode-bidi:isolate;">
                    <div dir="rtl" style="font-size:18px; font-weight:900; color:#4ade80; margin-bottom:10px; direction:rtl !important; text-align:right !important; width:100%;">🔩 تسليح قاعدة الخزان السفلي والعلوي طبقاً للكود (Reinforcement)</div>
                    <div dir="rtl" style="font-size:15.5px; color:#f1f5f9; line-height:1.95; font-weight:700; direction:rtl !important; text-align:right !important; width:100%;">
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>شبكة التسليح السفلية (Bottom Mesh):</b> <span dir="ltr" style="color:#fde047; font-size:18px; font-weight:900; unicode-bidi:isolate;">{res_tk['n_bars_bot_m']} Φ {res_tk['phi_bot_mm']} / m'</span> في الاتجاهين (المسافة = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['spacing_bot_cm']} cm</span>)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important; padding-right:16px;">▫️ المساحة المطلوبة = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['As_bot_req_cm2_m']:.2f} cm²/m'</span> | المساحة المتوفرة = <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_tk['As_bot_prov_cm2_m']:.2f} cm²/m'</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>شبكة التسليح العلوية (Top Mesh):</b> <span dir="ltr" style="color:#38bdf8; font-size:18px; font-weight:900; unicode-bidi:isolate;">{res_tk['n_bars_top_m']} Φ {res_tk['phi_top_mm']} / m'</span> في الاتجاهين (المسافة = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['spacing_top_cm']} cm</span>)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important; padding-right:16px;">▫️ المساحة المطلوبة = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['As_top_req_cm2_m']:.2f} cm²/m'</span> | المساحة المتوفرة = <span dir="ltr" style="color:#38bdf8; unicode-bidi:isolate;">{res_tk['As_top_prov_cm2_m']:.2f} cm²/m'</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>إجمالي وزن حديد التسليح للقاعدة:</b> <span dir="ltr" style="color:#f472b6; font-size:17px; font-weight:900; unicode-bidi:isolate;">{res_tk['total_rebar_weight_kg']:.1f} kg ({res_tk['total_rebar_weight_ton']:.3f} ton)</span> — بمعدل <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['steel_rate_kg_m3']:.1f} kg/m³</span></div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        with tk_c2:
            st.markdown(
                f"""<div class="m10-rtl-panel" dir="rtl" style="direction:rtl !important; text-align:right !important; background:rgba(15,23,42,0.85); border:2px solid #38bdf8; border-radius:12px; padding:16px 20px; unicode-bidi:isolate;">
                    <div dir="rtl" style="font-size:18px; font-weight:900; color:#38bdf8; margin-bottom:10px; direction:rtl !important; text-align:right !important; width:100%;">🌊 الضغط الهيدروستاتيكي والاتزان ضد الانقلاب والطفو</div>
                    <div dir="rtl" style="font-size:15.5px; color:#f1f5f9; line-height:1.95; font-weight:700; direction:rtl !important; text-align:right !important; width:100%;">
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>ارتفاع السائل داخل الخزان (<span dir="ltr" style="unicode-bidi:isolate;">H_liquid</span>):</b> <span dir="ltr" style="color:#fde047; unicode-bidi:isolate;">{res_tk['H_liquid_m']:.2f} m</span> (الارتفاع الكلي = <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['H_tank_total_m']:.2f} m</span>)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>الضغط الهيدروستاتيكي على القاع (<span dir="ltr" style="unicode-bidi:isolate;">p = γ_liq × H</span>):</b> <span dir="ltr" style="color:#38bdf8; unicode-bidi:isolate;">{res_tk['p_hydrostatic_ton_m2']:.2f} ton/m² ({res_tk['p_hydrostatic_kg_cm2']:.2f} kg/cm²)</span></div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>معامل الأمان ضد الانقلاب (<span dir="ltr" style="unicode-bidi:isolate;">FOS_overturning</span>):</b> <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_tk['fos_overturning']:.2f}</span> (المطلوب ≥ 1.50)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>معامل الأمان ضد الطفو (<span dir="ltr" style="unicode-bidi:isolate;">FOS_buoyancy</span>):</b> <span dir="ltr" style="color:#4ade80; unicode-bidi:isolate;">{res_tk['fos_buoyancy']:.2f}</span> (المطلوب ≥ 1.25)</div>
                        <div dir="rtl" style="direction:rtl !important; text-align:right !important;">• <b>أقصى إجهاد تربة فعلي (<span dir="ltr" style="unicode-bidi:isolate;">q_max</span>):</b> <span dir="ltr" style="color:#fde047; unicode-bidi:isolate;">{res_tk['q_max_kg_cm2']:.2f} kg/cm²</span> ≤ المسموح <span dir="ltr" style="unicode-bidi:isolate;">{res_tk['q_all_kg_cm2']:.2f} kg/cm²</span></div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        tk_checks = [
            (
                "1. التحقق من عدم تجاوز إجهاد التربة المسموح به (Soil Bearing Pressure)",
                f"q_max = {res_tk['q_max_kg_cm2']:.2f} kg/cm² ({res_tk['q_max_ton_m2']:.1f} t/m²)",
                f"q_all = {res_tk['q_all_kg_cm2']:.2f} kg/cm² ({res_tk['q_all_ton_m2']:.1f} t/m²)",
                res_tk["is_soil_safe"],
            ),
            (
                "2. فحص مقاومة الاختراق تحت جدار وحمل الخزان (Punching Shear - ECP 203)",
                f"q_up = {res_tk['q_up_kg_cm2']:.2f} kg/cm²",
                f"q_cup = {res_tk['q_cup_all_kg_cm2']:.2f} kg/cm²",
                res_tk["is_punching_safe"],
            ),
            (
                "3. فحص مقاومة القص ذو الاتجاه الواحد (One-Way Shear Strength)",
                f"q_u = {res_tk['qu_1way_kg_cm2']:.2f} kg/cm²",
                f"q_cu = {res_tk['qcu_1way_kg_cm2']:.2f} kg/cm²",
                res_tk["is_1way_shear_safe"],
            ),
            (
                "4. التحقق من الاستقرار ضد الانقلاب (Overturning Stability)",
                f"FOS = {res_tk['fos_overturning']:.2f} (M_res={res_tk['M_resisting_full_tm']:.1f} / M_ot={res_tk['M_overturning_tm']:.1f})",
                "FOS ≥ 1.50",
                res_tk["is_overturning_safe"],
            ),
            (
                "5. التحقق من مقاومة قوى الطفو (Buoyancy / Uplift Stability)",
                f"FOS = {res_tk['fos_buoyancy']:.2f} (W_empty={res_tk['W_empty_total_ton']:.1f} t / U={res_tk['U_buoyancy_ton']:.1f} t)",
                "FOS ≥ 1.25",
                res_tk["is_buoyancy_safe"],
            ),
        ]

        rows_tk_html = []
        for idx, (c_name, c_act, c_lim, c_ok) in enumerate(tk_checks):
            bg_r = "rgba(15, 23, 42, 0.75)" if idx % 2 == 0 else "rgba(30, 41, 59, 0.75)"
            badge = (
                '<span style="background:rgba(34,197,94,0.2); color:#4ade80; border:1.5px solid #22c55e; padding:4px 12px; border-radius:8px; font-weight:900;">✅ آمن ومطابق (SAFE)</span>'
                if c_ok else
                '<span style="background:rgba(239,68,68,0.2); color:#f87171; border:1.5px solid #ef4444; padding:4px 12px; border-radius:8px; font-weight:900;">⚠️ غير آمن (UNSAFE)</span>'
            )
            rows_tk_html.append(
                f'<tr style="background:{bg_r}; border-bottom:1px solid #334155;">'
                f'<td style="padding:12px 16px; font-size:17px; font-weight:800; color:#ffffff; text-align:right; direction:rtl;">{c_name}</td>'
                f'<td style="padding:12px 16px; font-size:18px; font-weight:900; color:#38bdf8; text-align:center;" dir="ltr">{c_act}</td>'
                f'<td style="padding:12px 16px; font-size:17px; font-weight:800; color:#fbbf24; text-align:center;" dir="ltr">{c_lim}</td>'
                f'<td style="padding:12px 16px; text-align:center;">{badge}</td>'
                f'</tr>'
            )

        st.markdown(
            '<div dir="rtl" style="direction:rtl !important; overflow-x:auto; border:2px solid #10b981; border-radius:12px; margin-top:16px;">'
            '<table dir="rtl" style="direction:rtl !important; width:100%; border-collapse:collapse; background:#0b1329;">'
            '<thead><tr style="background:#1e293b; border-bottom:2px solid #10b981;">'
            '<th style="padding:14px 16px; font-size:18px; color:#34d399; text-align:right;">بند التحقق الكودي للخزان (Verification Item)</th>'
            '<th style="padding:14px 16px; font-size:18px; color:#38bdf8; text-align:center;">القيمة المحسوبة (Actual)</th>'
            '<th style="padding:14px 16px; font-size:18px; color:#fbbf24; text-align:center;">الحد المسموح (Allowable)</th>'
            '<th style="padding:14px 16px; font-size:18px; color:#4ade80; text-align:center;">الحالة (Status)</th>'
            '</tr></thead><tbody>' + "".join(rows_tk_html) + '</tbody></table></div>',
            unsafe_allow_html=True,
        )

    # ── CAD SKETCH & REPORT EXPORT ──
    with st.expander("📐 3. المخططات الهندسية وتصدير التقرير الحسابي للخزان (2D Tank Blueprints & Report)", expanded=True):
        sketch_tk_b64 = generate_liquid_tank_foundation_sketches(res_tk)
        st.image(f"data:image/png;base64,{sketch_tk_b64}", use_container_width=True)

        summary_tk_rows = [
            ("الشكل الهندسي ومادة الخزان", f"{res_tk['tank_shape']} — {res_tk['tank_material']} (تخانة {res_tk['sheet_thk_mm']:.1f} mm)"),
            ("سعة وحجم التخزين", f"{res_tk['capacity_barrels']:.0f} Barrels ({res_tk['vol_liquid_m3']:.2f} m³) — الكثافة النوعية = {res_tk['specific_gravity']:.2f}"),
            ("وزن الخزان الفارغ المحسوب تلقائياً (W_tank)", f"{res_tk['W_tank_empty_ton']:.2f} ton"),
            ("وزن السائل الإجمالي المحسوب تلقائياً (W_liquid)", f"{res_tk['W_liquid_ton']:.2f} ton"),
            ("الوزن الذاتي للقاعدة الخرسانية (W_foundation @ 2.5 t/m³)", f"V = {res_tk['vol_f_m3']:.2f} m³ | W_f = {res_tk['Wf_ton']:.2f} ton"),
            ("إجمالي الأحمال الكلية (المعدة + السائل + القاعدة)", f"{res_tk['P_total_working_ton']:.2f} ton"),
            ("الأبعاد الهندسية النهائية للقاعدة (Lf × Bf × tf)", f"{res_tk['Lf_m']:.2f} m × {res_tk['Bf_m']:.2f} m × {res_tk['tf_m']:.2f} m"),
            ("إجهاد التربة الأقصى الفعلي / المسموح به", f"{res_tk['q_max_kg_cm2']:.2f} / {res_tk['q_all_kg_cm2']:.2f} kg/cm²"),
            ("تسليح القاعدة السفلي (Bottom Mesh)", f"{res_tk['n_bars_bot_m']} Φ {res_tk['phi_bot_mm']} / m' (As = {res_tk['As_bot_prov_cm2_m']:.2f} cm²/m')"),
            ("تسليح القاعدة العلوي (Top Mesh)", f"{res_tk['n_bars_top_m']} Φ {res_tk['phi_top_mm']} / m' (As = {res_tk['As_top_prov_cm2_m']:.2f} cm²/m')"),
            ("إجمالي وزن حديد التسليح للقاعدة", f"{res_tk['total_rebar_weight_kg']:.1f} kg ({res_tk['total_rebar_weight_ton']:.3f} ton)"),
        ]
        html_tk_report = generate_m10_calculation_sheet_html(
            title_ar="التقرير الحسابي التفصيلي لقاعدة خزان السوائل",
            subtitle_en="Liquid Storage Tank Foundation Calculation Sheet (ECP 203 / ACI 350)",
            rows_summary=summary_tk_rows,
            checks_list=tk_checks,
            sketch_b64=sketch_tk_b64,
        )

        td1, td2, td3 = st.columns(3)
        with td1:
            st.download_button(
                "📥 تحميل مخطط قاعدة الخزان (PNG)",
                data=base64.b64decode(sketch_tk_b64),
                file_name=f"Liquid_Tank_Foundation_{res_tk['Lf_m']:.1f}x{res_tk['Bf_m']:.1f}m.png",
                mime="image/png",
                use_container_width=True,
            )
        with td2:
            st.download_button(
                "🌐 تحميل التقرير الحسابي للخزان (HTML)",
                data=html_tk_report,
                file_name=f"Liquid_Tank_Foundation_Report_{res_tk['capacity_barrels']:.0f}BBL.html",
                mime="text/html",
                use_container_width=True,
            )
        with td3:
            if st.button("📕 توليد وتحميل ملف PDF للخزان", key="btn_m10_tk_pdf", use_container_width=True):
                with st.spinner("جاري تجهيز ملف PDF..."):
                    pdf_b2 = html_to_pdf_bytes(html_tk_report)
                    if pdf_b2:
                        st.download_button(
                            "📥 اضغط لحفظ التقرير PDF",
                            data=pdf_b2,
                            file_name="Liquid_Tank_Foundation_Report.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )


# ===============================================================================
#  7. MAIN MODULE 10 ENTRY POINT
# ===============================================================================

def render_circular_tank_foundations_module():
    """
    Main Streamlit renderer for Module 10:
    1. Equipment Foundation Design (Static & Dynamic Mechanical Equipment)
    2. Liquid Storage Tank Foundations (Circular & Rectangular Liquid Tanks)
    """
    st.markdown(
        """
        <style>
        /* Keep Expander Section Headers LTR (Left-to-Right) just like all other modules */
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] summary,
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] summary * {
            direction: ltr !important;
            text-align: left !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stTabs"] button[data-baseweb="tab"] {
            font-size: 18px !important;
            font-weight: 900 !important;
            padding: 12px 24px !important;
        }
        /* Ensure RTL inside custom Arabic panels & widget labels */
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stWidgetLabel"],
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] [data-testid="stWidgetLabel"] * {
            direction: rtl !important;
            text-align: right !important;
            width: 100% !important;
            justify-content: flex-start !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stExpander"] div[data-baseweb="select"] {
            direction: rtl !important;
            text-align: right !important;
        }
        [data-testid="stMainBlockContainer"] .m10-rtl-panel,
        [data-testid="stMainBlockContainer"] .m10-rtl-panel > div,
        [data-testid="stMainBlockContainer"] .m10-rtl-panel div {
            direction: rtl !important;
            text-align: right !important;
        }
        [data-testid="stMainBlockContainer"] .m10-centered-panel,
        [data-testid="stMainBlockContainer"] .m10-centered-panel > div,
        [data-testid="stMainBlockContainer"] .m10-centered-panel div {
            direction: rtl !important;
            text-align: center !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    tab_eq, tab_tank = st.tabs([
        "⚙️ أولاً: تصميم قواعد المعدات الميكانيكية (Equipment Foundations)",
        "🛢️ ثانياً: تصميم قواعد الخزانات السائلة (Liquid Storage Tank Foundations)",
    ])

    with tab_eq:
        _render_equipment_foundations_tab()

    with tab_tank:
        _render_liquid_storage_tanks_tab()
