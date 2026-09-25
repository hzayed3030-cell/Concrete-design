# -*- coding: utf-8 -*-
"""
Module Philosophy & Unified Engineering Header System
======================================================
Unified Visual Identity & ECP 203 Engineering Philosophy Modals for ALL Modules (1 to 14)
Designed strictly in accordance with ECP 203-2018 and project guidelines:
  1. Centered Amber Gradient Title Banner (25.2px, font-weight: 900, white text)
  2. Full-width Amber Gradient Philosophy Button (14.5px, font-weight: 900)
  3. In-depth, comprehensive ECP 203 Modal Dialogs with RTL layout and preserved English terms.
"""

import streamlit as st


# ═══════════════════════════════════════════════════════════════════════════════
#  SHARED CSS INJECTION FOR TITLE BANNERS & PHILOSOPHY BUTTONS
# ═══════════════════════════════════════════════════════════════════════════════

def inject_module_philosophy_css():
    """Injects high-specificity CSS for the amber title banners and philosophy buttons."""
    st.markdown(
        """
        <style>
        .module-unified-title-banner {
            background: linear-gradient(135deg, #1c1917 0%, #78350f 45%, #92400e 100%) !important;
            color: #ffffff !important;
            border: 2px solid #f59e0b !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 14px rgba(120, 53, 15, 0.40) !important;
            padding: 12px 20px !important;
            margin: 6px 0 8px 0 !important;
            font-family: 'Cairo', 'Tajawal', 'Segoe UI', Tahoma, sans-serif !important;
            font-size: 25.2px !important;
            font-weight: 900 !important;
            text-align: center !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 10px !important;
            letter-spacing: 0.4px !important;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.65) !important;
            line-height: 1.35 !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }

        div[class*="btn_unified_philo_"] {
            width: 100% !important;
            margin-top: 4px !important;
            margin-bottom: 8px !important;
        }

        div[class*="btn_unified_philo_"] button {
            background: linear-gradient(135deg, #1c1917 0%, #78350f 45%, #92400e 100%) !important;
            color: #ffffff !important;
            font-size: 14.5px !important;
            font-weight: 900 !important;
            border: 2px solid #f59e0b !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 14px rgba(120, 53, 15, 0.40) !important;
            padding: 8px 16px !important;
            letter-spacing: 0.3px !important;
            white-space: nowrap !important;
            width: 100% !important;
            height: 42px !important;
            line-height: 1.2 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.25s ease-in-out !important;
        }

        div[class*="btn_unified_philo_"] button:hover {
            background: linear-gradient(135deg, #78350f 0%, #92400e 45%, #b45309 100%) !important;
            border-color: #fde68a !important;
            box-shadow: 0 6px 20px rgba(245, 158, 11, 0.60) !important;
            transform: translateY(-2px) !important;
        }

        div[class*="btn_unified_philo_"] button p,
        div[class*="btn_unified_philo_"] button span {
            color: #ffffff !important;
            font-weight: 900 !important;
            font-size: 14.5px !important;
            white-space: nowrap !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 2: RECTANGULAR COLUMNS MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم الأعمدة المستطيلة (ECP 203 Columns Philosophy)", width="large")
def show_dialog_m2_columns():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>🏛️ دليل وفلسفة تصميم الأعمدة المستطيلة</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Rectangular Columns Design)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'الاشتراطات الهندسية وميكانيكية نقل الأحمال الرأسية <span dir="ltr" style="font-weight:700; color:#60a5fa;">(Axial Loads)</span> '
        'وعزوم الانبعاج واللامركزية <span dir="ltr" style="font-weight:700; color:#60a5fa;">(Buckling & Secondary Moments)</span> '
        'طبقاً للكود المصري لتصميم وتنفيذ المنشآت الخرسانية المسلحة <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203-2018</span>.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ معادلة التحمل المحوري القصوى للأعمدة القصيرة <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Axial Load Capacity Pu)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>معادلة الكود المصري للأعمدة ذات الكانات المنفصلة <span dir="ltr">(Tied Columns)</span>:</b>'
        '<div dir="ltr" style="background: #f1f5f9; padding: 8px 14px; border-radius: 6px; font-size: 13.5px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        'Pu = 0.35 × fcu × Ac + 0.67 × fy × Asc'
        '</div>'
        'حيث يمثل <span dir="ltr" style="font-weight:700;">fcu</span> رتبة مقاومة الخرسانة للضغط (كجم/سم²)، '
        '<span dir="ltr" style="font-weight:700;">Ac</span> مساحة القطاع الخرساني الإجمالي (سم²)، '
        '<span dir="ltr" style="font-weight:700;">fy</span> حد خضوع حديد التسليح الطولي، و '
        '<span dir="ltr" style="font-weight:700;">Asc</span> إجمالي مساحة أسياخ التسليح الطولي.'
        '</li>'
        '<li>'
        '<b>فلسفة المعاملات الكودية:</b> المعامل <span dir="ltr">0.35</span> يمثل <span dir="ltr">0.67 fcu / 1.5</span> مع أخذ أثر اللامركزية الدنيا غير المقصودة <span dir="ltr">(Minimum Accidental Eccentricity = 0.05 t ≥ 20 mm)</span> في الحسبان دون الحاجة لحساب عزوم منفصلة للأعمدة القصيرة.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ حدود واشتراطات حديد التسليح الطولي <span dir="ltr" style="font-size:14px; color:#16a34a;">(Longitudinal Reinforcement Limits)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>النسبة الدنيا للتسليح <span dir="ltr" style="color:#15803d;">(Minimum Reinforcement Ratio μ_min)</span>:</b> '
        'يجب ألا تقل مساحة التسليح الطولي <span dir="ltr">Asc</span> عن <span dir="ltr">0.8%</span> من مساحة القطاع الخرساني المطلوب <span dir="ltr">(Ac,req)</span>، أو <span dir="ltr">0.6%</span> من مساحة القطاع الفعلي المختار <span dir="ltr">(Ac,actual)</span>.'
        '</li>'
        '<li style="margin-bottom: 8px;">'
        '<b>النسبة القصوى للتسليح <span dir="ltr" style="color:#15803d;">(Maximum Reinforcement Ratio μ_max)</span>:</b> '
        '<span dir="ltr">4.0%</span> للأعمدة الداخلية <span dir="ltr">(Interior Columns)</span>، '
        '<span dir="ltr">5.0%</span> للأعمدة الطرفية <span dir="ltr">(Edge Columns)</span>، و '
        '<span dir="ltr">6.0%</span> لأعمدة الزاوية والأركان <span dir="ltr">(Corner Columns)</span> لتجنب تعشيش الخرسانة وتكدس الأسياخ.'
        '</li>'
        '<li>'
        '<b>المسافات بين الأسياخ:</b> أقصى مسافة بين سيخين طوليين متتاليين هي <span dir="ltr">250 mm</span> لضمان عدم انبعاج القشرة الخرسانية، والحد الأدنى للقطر هو <span dir="ltr">Φ 12 mm</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ النحافة والانبعاج والعزوم الإضافية <span dir="ltr" style="font-size:14px; color:#d97706;">(Slenderness & Buckling Moments)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>معامل النحافة <span dir="ltr" style="color:#b45309;">(Slenderness Ratio λ)</span>:</b> '
        'يُحسب المعامل <span dir="ltr">λb = He / b</span> للأعمدة المستطيلة؛ حيث يعتبر العمود قصيراً <span dir="ltr">(Short Column)</span> إذا كان <span dir="ltr">λb ≤ 15</span> في المنشآت غير المقيدة <span dir="ltr">(Unbraced)</span>، أو <span dir="ltr">λb ≤ 30</span> في المنشآت المقيدة جدارياً <span dir="ltr">(Braced)</span>.'
        '</li>'
        '<li>'
        '<b>العزم الإضافي للانبعاج <span dir="ltr">(Additional Buckling Moment Madd)</span>:</b> '
        'إذا تجاوز العمود حد النحافة، يتولد عزم إضافي ناتج عن الإزاحة الجانبية:'
        '<div dir="ltr" style="background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        'δ = (λb² × b) / 2000 &nbsp;&nbsp;|&nbsp;&nbsp; Madd = Pu × δ'
        '</div>'
        'ويتم تصميم القطاع على تراكب العزم التصميمي <span dir="ltr">Mu = max(M_initial + Madd, Pu × emin)</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ تفاصيل الكانات ومناطق التكثيف الزلزالي <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Stirrup Ties & Confinement Zones)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>اشتراطات الكانات العادية:</b> ألا يقل قطر الكانة عن <span dir="ltr">8 mm</span> أو ربع قطر أكبر سيخ طولي. أقصى خطوة للكانات لا تتجاوز الأصغر من: <span dir="ltr">15 مرة قطر أصغر سيخ طولي</span>، أو <span dir="ltr">عرض العمود الأصغر b</span>، أو <span dir="ltr">200 mm</span>.'
        '</li>'
        '<li style="margin-bottom: 8px;">'
        '<b>تربيط الأسياخ بالكانات:</b> يجب ألا تزيد المسافة بين الأسياخ المربوطة بفرع كانة عن <span dir="ltr">150 mm</span>، وإذا زادت المسافة عن ذلك يوضع فرع كانة داخلي إضافي أو كانة حباية.'
        '</li>'
        '<li>'
        '<b>مناطق التكثيف الزلزالي <span dir="ltr">(End Confinement Zones)</span>:</b> يتم تكثيف الكانات في الثلثين العلوي والسفلي من العمود على مسافة <span dir="ltr">L0 = max(b, t, H/6, 500 mm)</span> بخطوة لا تتجاوز <span dir="ltr">80 mm ~ 100 mm</span> لضمان الحبس الخرساني ومقاومة قوى القص الزلزالية.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 3: ISOLATED FOOTINGS MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم القواعد المنفصلة (ECP 203 Isolated Footings)", width="large")
def show_dialog_m3_footings():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>🪸 دليل وفلسفة تصميم القواعد المنفصلة</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Isolated Footings Design)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'الأصول الهندسية ومسار انتقال ردود الأفعال المحورية من الأعمدة إلى طبقات التربة، وتحديد أبعاد الخرسانة العادية والمسلحة وتدقيق القص والقص الثاقب طبقاً لـ <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203-2018</span>.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ أبعاد الخرسانة العادية والمسلحة وإجهاد التربة <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Bearing Capacity & Sizing)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>مساحة التأسيس المطلوبة:</b> تُحسب بناءً على حمل التشغيل الكلي للعمود <span dir="ltr">P_working = Pu / 1.50</span> مقسوماً على جهد التربة الصافي المسموح به <span dir="ltr">q_all,net</span>:'
        '<div dir="ltr" style="background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 13.5px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        'Area_req = P_working / q_all,net'
        '</div>'
        '</li>'
        '<li>'
        '<b>دور الخرسانة العادية (P.C):</b> إذا كان سمك الخرسانة العادية <span dir="ltr">Tpc ≥ 20 cm</span>، فإنها تساهم إنشائياً في نقل وتوزيع الأحمال إلى التربة بزاوية <span dir="ltr">45°</span>، وتكون أبعاد الخرسانة المسلحة مساوية لأبعاد العادية مطروحاً منها ضعف رفرفة العادية.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ فلسفة تماثل الرفرفات وتوحيد العزوم <span dir="ltr" style="font-size:14px; color:#16a34a;">(Equal Projections & Bending Moments)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>شرط تماثل الرفرفة:</b> لضمان أن يكون العزم التصميمي في الاتجاه الطولي مساوياً تقريباً للعزم في الاتجاه العرضي، يتم جعل رفرفة المسلحة عن وجه العمود متساوية في الاتجاهين:'
        '<div dir="ltr" style="background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 13.5px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        '(L_rc - a) / 2 = (B_rc - b) / 2 &nbsp;⟹&nbsp; L_rc - B_rc = a - b'
        '</div>'
        'حيث يمثل <span dir="ltr">a, b</span> أبعاد قطاع العمود المستطيل، و <span dir="ltr">L_rc, B_rc</span> أبعاد القاعدة المسلحة.'
        '</li>'
        '<li>'
        '<b>أقصى عزم تصميمي:</b> يُحسب العزم عند وجه العمود مباشرة باعتبار رفرفة القاعدة ككابولي مقلوب محمل بضغط التماس الأقصى <span dir="ltr">q_u</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ تدقيق القص العرضي والقص الثاقب <span dir="ltr" style="font-size:14px; color:#d97706;">(One-Way Shear & Punching Shear)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>القص العرضي الحرج <span dir="ltr">(One-Way Beam Shear)</span>:</b> يُحسب القطاع الحرج على مسافة <span dir="ltr">d / 2</span> من وجه العمود، ويجب ألا يتجاوز إجهاد القص الفعلي مقاومة الخرسانة غير المسلحة للقص:'
        '<div dir="ltr" style="background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        'qu = Qu / (B × d) ≤ qcu = 0.16 × √(fcu / γc)'
        '</div>'
        '</li>'
        '<li>'
        '<b>القص الثاقب <span dir="ltr">(Punching Shear)</span>:</b> يُحسب على محيط حرج يبعد مسافة <span dir="ltr">d / 2</span> من جميع أوجه العمود، بمحيط <span dir="ltr">bo = 2 × (a + d + b + d)</span>، ويجب ألا يتجاوز إجهاد الثقب الحد الكودي الأصغر من معادلات الكود المصري الثلاث.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ متطلبات حديد التسليح وأطوال التماسك <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Reinforcement & Development Length)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الحد الأدنى لسمك القاعدة المسلحة:</b> لا يقل عمق القاعدة المسلحة عن <span dir="ltr">d ≥ 30 cm</span> (سمك <span dir="ltr">T ≥ 35 ~ 40 cm</span>) لضمان متانة ونقل أحمال آمن.'
        '</li>'
        '<li style="margin-bottom: 8px;">'
        '<b>النسبة الدنيا للتسليح:</b> لا يقل التسليح في أي اتجاه عن <span dir="ltr">0.15%</span> من مساحة القطاع الخرساني الفعال <span dir="ltr">(0.0015 × B × d)</span> وبما لا يقل عن <span dir="ltr">5 Φ 12 mm / m</span>.'
        '</li>'
        '<li>'
        '<b>طول الرباط والتثبيت <span dir="ltr">(Ld)</span>:</b> يجب توفير طول تماسك كافٍ لأسياخ التسليح السفلية من القطاع الحرج عند وجه العمود حتى نهاية السيخ مع عمل أرجل قائمة للأعلى <span dir="ltr">(U-shape stirrups / hooks)</span>.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 4: TWO-COLUMNS COMBINED FOOTINGS MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم القواعد المشتركة لعمودين (ECP 203 Combined Footings)", width="large")
def show_dialog_m4_two_col():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>📐 دليل وفلسفة تصميم القواعد المشتركة لعمودين</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Combined Footings Design)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'فلسفة التصميم عند تداخل القواعد المنفصلة أو وجود حدود الجار الملاصقة، ومطابقة مركز المحصلة مع مركز مساحة القاعدة لتفادي أي دوران أو إجهاد غير منتظم على التربة طبقاً لـ <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203</span>.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ مطابقة محصلة الأحمال مع مركز مساحة القاعدة <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Resultant & Centroid Alignment)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>تحديد موقع المحصلة R:</b> يُحسب موقع المحصلة <span dir="ltr">R = P1 + P2</span> بأخذ العزوم حول محور أحد العمودين:'
        '<div dir="ltr" style="background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 13.5px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        'x_bar = (P2 × S) / (P1 + P2)'
        '</div>'
        'حيث يمثل <span dir="ltr">S</span> المسافة الصافية أو المحورية بين مركزي العمودين.'
        '</li>'
        '<li>'
        '<b>شرط توزيع الإجهاد المنتظم (e = 0):</b> يتم اختيار طول القاعدة <span dir="ltr">L_rc</span> بحيث يقع مركز ثقل مساحتها تماماً فوق نقطة تأثير المحصلة <span dir="ltr">R</span> لضمان إجهاد تماس مستوٍ ومنتظم <span dir="ltr">q = R / Area</span> دون تولد أي عزوم دوران أو هبوط تفاضلي.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ التحليل الإنشائي ومخططات العزوم والقص <span dir="ltr" style="font-size:14px; color:#16a34a;">(Longitudinal BMD & SFD)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>العزم السالب العلوي الرئيسي <span dir="ltr">(Main Negative Moment M_top)</span>:</b> تتصرف القاعدة المشتركة في الاتجاه الطولي ككمرة مقلوبة ترتكز على العمودين، مما يولد عزماً سالباً كبيراً في الجزء العلوي بين العمودين يتطلب وضع شبكة تسليح علوية رئيسية قوية.'
        '</li>'
        '<li>'
        '<b>العزم الموجب السفلي <span dir="ltr">(Bottom Positive Moments)</span>:</b> يتولد عزم موجب سفلي أسفل كل عمود بسبب بروز كوابيل القاعدة عن محاور الأعمدة.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ تصميم الكمرة العرضية المخفية <span dir="ltr" style="font-size:14px; color:#d97706;">(Transverse Beam Distribution)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>نقل الحمل في الاتجاه العرضي:</b> لتوزيع الحمل المركز لكل عمود على كامل عرض القاعدة <span dir="ltr">B_rc</span>، يتم اعتبار قطاع كمرة عرضية افتراضية أسفل كل عمود بعرض فعال <span dir="ltr">b_beam = col_b + 2 × d</span>.'
        '</li>'
        '<li>'
        '<b>التسليح السفلي العرضي:</b> يوضع تسليح عرضي مركز أسفل كل عمود في نطاق الكمرة العرضية لمقاومة الانحناء العرضي، وتسليح ثانوي موزع بانتظام في باقي أجزاء القاعدة.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ التحقق من القص الثاقب المتعدد <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Multi-Column Punching Shear)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>فحص الثقب المنفصل لكل عمود:</b> يُفحص القص الثاقب على مسافة <span dir="ltr">d / 2</span> من محيط كل عمود مستقلاً، مع مراعاة حالة عمود الجار المفتوح من جهة حد الملكية.'
        '</li>'
        '<li>'
        '<b>القص الحرج عند نقطة الصفر عزم:</b> يتم فحص القص العرضي عند قطاع أقصى قوى قص <span dir="ltr">(Maximum Shear Force)</span> الواقع بالقرب من أوجه الأعمدة في الاتجاه الطولي.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 5: STRAP FOOTINGS MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم قواعد الشدادات والجار (ECP 203 Strap Footings)", width="large")
def show_dialog_m5_strap():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>🔗 دليل وفلسفة تصميم قواعد الشدادات والجار</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Strap Footings Design)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'ميكانيكية اتزان عمود الجار المعرض للامركزية شديدة، وتصميم كمرة الشداد الجسئة <span dir="ltr" style="font-weight:700; color:#60a5fa;">(Rigid Strap Beam)</span> '
        'لنقل عزم الانقلاب إلى العمود الداخلي وإعادة توزيع ردود الأفعال الصاعدة بأمان وفقاً لـ <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203-2018</span>.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ ميكانيكية الاتزان الاستاتيكي وردود الأفعال <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Equilibrium & Reactions)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>عزم الانقلاب الناتج عن عمود الجار:</b> وقوع عمود الجار <span dir="ltr">P1</span> على حافة القاعدة المسلحة يُنشئ لامركزية مقدارها <span dir="ltr">e = (L1 - a1) / 2</span>، مما يولد عزم انقلاب <span dir="ltr">M = P1 × e</span>.'
        '</li>'
        '<li>'
        '<b>قوة رد الفعل التصميمية الصاعدة <span dir="ltr">(R1 & R2)</span>:</b> تقوم كمرة الشداد بمقاومة عزم الانقلاب، مما يزيد من رد الفعل الصاعد أسفل قاعدة الجار إلى <span dir="ltr">R1 = P1 × (1 + e/S)</span>، بينما يخفف الحمل عن العمود الداخلي بمقدار قوة الشد الصاعدة <span dir="ltr">ΔP = P1 × e / S</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ اشتراطات جساءة وأبعاد كمرة الشداد <span dir="ltr" style="font-size:14px; color:#16a34a;">(Strap Beam Rigidity & Dimensions)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>شرط الجساءة العالية <span dir="ltr">(High Flexural Rigidity EI)</span>:</b> لكي يعمل الشداد طبقاً للفرضية الكودية بنقل كامل العزم دون دوران القاعدة، يجب أن يكون عمقه كبيراً بحيث <span dir="ltr">D_strap ≥ L_span / 6 ~ L_span / 7</span> وبما لا يقل عادة عن <span dir="ltr">80 cm ~ 100 cm</span>.'
        '</li>'
        '<li>'
        '<b>عرض كمرة الشداد:</b> يوصى بألا يقل عرض الشداد <span dir="ltr">b_strap</span> عن عرض عمود الجار لضمان الرباط الكامل للأسياخ والكانات.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ تسليح الشداد لمقاومة أقصى عزم سالب وقوى القص <span dir="ltr" style="font-size:14px; color:#d97706;">(Top Steel & Heavy Shear Ties)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>حديد التسليح العلوي الرئيسي <span dir="ltr">(As_top)</span>:</b> يتحمل الشداد أقصى عزم انحناء سالب <span dir="ltr">M_max(-)</span> عند وجه عمود الجار الداخلي، ولذا يوضع حديد رئيسي مكثف في الرقة العلوية بكامل طول الشداد.'
        '</li>'
        '<li>'
        '<b>كانات القص المغلقة ذات الفروع المتعددة:</b> يتعرض الشداد لقوى قص قصوى هائلة ناتجة عن فرق الأحمال، ويجب تصميم كانات مغلقة ذات 4 فروع أو أكثر بخطوة تكثيف محكمة وتوفير أسياخ انكماش جانبية <span dir="ltr">(Side Skin Bars)</span> كل <span dir="ltr">30 cm</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ تصميم قاعدتي الجار والعمود الداخلي <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Footings Structural Behavior)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>قاعدة الجار المستطيلة:</b> تتصرف قاعدة الجار كقاعدة في اتجاه واحد <span dir="ltr">(One-Way Cantilever Slab)</span> ترتكز على جانبي كمرة الشداد، ويوضع تسليحها الرئيسي في الاتجاه العرضي الموازي لخط الجار.'
        '</li>'
        '<li>'
        '<b>القاعدة الداخلية:</b> تُصمم كقاعدة منفصلة عادية متماثلة على رد الفعل الصافي بعد خصم قوة الشد الصاعدة المنقولة من الشداد.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 6: CORNER FOOTING WITH DIAGONAL STRAP MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم قواعد الجار بشداد مائل (ECP 203 Diagonal Strap)", width="large")
def show_dialog_m6_diagonal_strap():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>📐 دليل وفلسفة تصميم قواعد الجار الركنية بشداد مائل</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(Corner Footing with Diagonal Strap - ECP 203)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'فلسفة التصميم المعقد للأعمدة الركنية المتاخمة لحدود جار في اتجاهين متعامدين، وتوجيه الشداد قطرياً نحو أقرب عمود داخلي لتحقيق التوازن الفضائي الكامل طبقاً لـ <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203-2018</span>.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ اللامركزية ثنائية المحور في ركن المبنى <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Biaxial Eccentricity in Corners)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>تحدي حدود الجار المزدوجة:</b> يقع عمود الركن على نقطة التقاء خطي جار متعامدين، مما يمنع رفرفة القاعدة في كلا الاتجاهين X و Y وينتج عنه لا مركزية مزدوجة <span dir="ltr">(ex = Lx/2 - cx/2, ey = Ly/2 - cy/2)</span>.'
        '</li>'
        '<li>'
        '<b>توجيه محصلة الانقلاب:</b> تنتج محصلة العزم في اتجاه مائل بقطر الركن، مما يجعل الحل الهندسي الأمثل والأكثر اقتصادية هو مد كمرة شداد جسئة مائلة قطرياً تربط عمود الركن بالعمود الداخلي المقابل.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ التحليل الإنشائي والفضائي للشداد المائل <span dir="ltr" style="font-size:14px; color:#16a34a;">(3D Spatial Equilibrium & Strap Angle)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>زاوية ميل الشداد θ:</b> تُحسب الزاوية هندسياً <span dir="ltr">tan θ = ΔY / ΔX</span> من المسافات المحورية للمبنى، ويتم تحليل قوى الشد والضغط والعزوم على طول محور الشداد المائل.'
        '</li>'
        '<li>'
        '<b>تراكب العزوم وقوى الالتواء:</b> تدقيق تأثير المركبات المتعامدة على الشداد والتأكد من تسليحه لمقاومة عزوم الانحناء المصحوبة بعزوم لي محتملة <span dir="ltr">(Torsion Mt)</span> عند عدم تطابق محور العمودين تماماً مع محور الشداد.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ أبعاد قاعدة الركن ومنع إجهادات الشد <span dir="ltr" style="font-size:14px; color:#d97706;">(No Soil Tension Criteria)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>ضمان انضغاط كامل التربة:</b> تصميم أبعاد القاعدة للتأكد من بقاء محصلة الإجهادات داخل القلب المركزي للقطاع <span dir="ltr">(Kern of Section)</span> بحيث تكون جميع إجهادات التماس موجبة (انضغاط) ولا يحدث أي انفصال للقاعدة عن التربة.'
        '</li>'
        '<li>'
        '<b>فحص أقصى ضغط تماس:</b> التأكد من أن أقصى إجهاد عند الركن الخارجي لا يتجاوز جهد التربة المسموح به <span dir="ltr">q_max ≤ q_all,net</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ تفاصيل التسليح وأطوال التماسك في الركن <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Rebar Detailing & Corner Confinement)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>تسليح الشداد المائل:</b> وضع تسليح علوي رئيسي ثقيل ممتد بالكامل داخل العمودين مع عمل كرافات وأرجل رباط كاملة <span dir="ltr">Ld</span> لا تقل عن <span dir="ltr">60 Φ</span> داخل منطقة قلب العمود.'
        '</li>'
        '<li>'
        '<b>الكانات المغلقة المقاومة لقص الركن:</b> تكثيف الكانات المغلقة الصندوقية في منطقة التقاء الشداد المائل بقاعدة الركن لضمان عدم حدوث شروخ قطرية.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 7: GROUND BEAMS & TIE BEAMS MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم الميدات والسملات (ECP 203 Ground Beams)", width="large")
def show_dialog_m7_ground_beam():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>🧱 دليل وفلسفة تصميم الميدات والكمرات الأرضية</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Ground Beams & Tie Beams)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'الوظائف الإنشائية للميدات والسملات والشدادات في ربط الأساسات ومنع الهبوط التفاضلي ومقاومة قوى الشد والضغط الزلزالية وحمل حوائط الدور الأرضي طبقاً لـ <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203-2018</span>.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ الوظائف الإنشائية المعيارية طبقاً للكود المصري <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Structural Functions)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الربط ومنع الهبوط التفاضلي <span dir="ltr">(Differential Settlement Control)</span>:</b> تعمل الميدات كشبكة ربط جسئة تمنع الحركة النسبية بين القواعد عند حدوث أي انضغاط غير متجانس في طبقات التأسيس.'
        '</li>'
        '<li style="margin-bottom: 8px;">'
        '<b>حمل حوائط وقواطيع الدور الأرضي:</b> نقل أحمال مباني القواطيع والحوائط الخارجية مباشرة إلى الأساسات وحماية أرضية الدور الأرضي من التشريخ.'
        '</li>'
        '<li>'
        '<b>تقليل طول الانبعاج لرقاب الأعمدة:</b> ربط رقاب الأعمدة <span dir="ltr">(Column Necks)</span> يقلل من الارتفاع الحر للعمود <span dir="ltr">Ho</span> ويمنع انبعاجها تحت الأحمال الرأسية.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ قوى الشد والضغط الزلزالية المحورية <span dir="ltr" style="font-size:14px; color:#16a34a;">(Seismic Axial Tension & Compression)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الاشتراط الكودي للقوة الزلزالية:</b> ينص الكود المصري على تصميم الميدات على قوة محورية شد/ضغط لا تقل عن <span dir="ltr">10%</span> من الحمل الرأسي الأقصى للعمود الأثقل من العمودين المتصلين:'
        '<div dir="ltr" style="background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 13.5px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        'Tu = 0.10 × max(Pu1, Pu2)'
        '</div>'
        '</li>'
        '<li>'
        '<b>التصميم على الشد المحوري:</b> يُحسب حديد التسليح لمقاومة الشد المحوري بالكامل بواسطة الصلب <span dir="ltr">As_tension = Tu / (fy / γs)</span> دون الاعتماد على مقاومة الخرسانة للشد.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ أبعاد القطاع والعمق التنفيذي <span dir="ltr" style="font-size:14px; color:#d97706;">(Depth & Sizing Criteria)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الربط بمنسوب ظهر القواعد المسلحة:</b> يفضل أن يكون عمق الميدة مساوياً لعمق القاعدة المسلحة <span dir="ltr">(D_beam = D_footing)</span> لتشكيل ديافرام أرضي صلب يمنع دوران القواعد.'
        '</li>'
        '<li>'
        '<b>العرض الأدنى للقطاع:</b> لا يقل عرض الميدة عن <span dir="ltr">25 cm</span> أو سمك الحوائط المرتكزة عليها أيهما أكبر لضمان ارتكاز كامل للمباني وتوفير غطاء خرساني كافٍ للحديد.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ فلسفة التسليح المتماثل والكانات <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Symmetrical Rebar & Stirrups)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>التسليح المتماثل (علوي وسفلي متطابق):</b> نظراً لاحتمالية حدوث الهبوط التفاضلي في أي من الاتجاهين (هبوط القاعدة اليمنى أو اليسرى)، يتم تسليح الميدات بتسليح علوي مساوٍ للتسليح السفلي لمقاومة العزوم الانعكاسية التبادلية بأمان تام.'
        '</li>'
        '<li>'
        '<b>أطوال التماسك وتكثيف الكانات:</b> تمتد أسياخ التسليح العلوية والسفلية داخل رقاب الأعمدة أو القواعد بكامل طول الرباط والتماسك <span dir="ltr">Ld</span>، وتكثف الكانات بالقرب من الركائز لمقاومة القص المصاحب لقوى الزلازل.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 8: RAFT FOUNDATIONS MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم اللبشة المسلحة (ECP 203 Raft Foundations)", width="large")
def show_dialog_m8_raft():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>🏗️ دليل وفلسفة تصميم اللبشة المسلحة</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Raft / Mat Foundations Design)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'معايير التحليل الإنشائي وتوزيع إجهادات التماس على كامل مساحة المبنى، وفحص القص الثاقب تحت كافة الأعمدة ومنظومة التسليح المزدوج طبقاً لـ <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203-2018</span>.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ ميكانيكية عمل الأساسات الحصيرية والمساند المرنة <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Winkler Subgrade Model)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>معامل رد فعل التربة <span dir="ltr">(Modulus of Subgrade Reaction ks)</span>:</b> يتم تمثيل تفاعل التربة مع اللبشة كنوابض مرنة تعتمد على جساءة التربة ونوعيتها (كجم/سم³)، حيث يتناسب ضغط التماس مع مقدار الهبوط اللحظي.'
        '</li>'
        '<li>'
        '<b>متى نلجأ للبشة المسلحة:</b> يوصي الكود باللجوء للبشة عندما تتجاوز المساحة الإجمالية المطلوبة للقواعد المنفصلة <span dir="ltr">60% ~ 65%</span> من مساحة بصمة المبنى الكلية.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ تطابق مركز ثقل الأحمال وتفادي اللامركزية <span dir="ltr" style="font-size:14px; color:#16a34a;">(Total Loads Resultant & Center of Area)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>ضبط اللامركزية الكلية:</b> يتم ضبط رفارف اللبشة من جهات المبنى المختلفة بحيث ينطبق مركز ثقل الأحمال التراكمية <span dir="ltr">∑Pu</span> تماماً مع مركز مساحة اللبشة <span dir="ltr">(ex ≈ 0, ey ≈ 0)</span> لتجنب تركيز الإجهادات على أحد الأطراف.'
        '</li>'
        '<li>'
        '<b>تدقيق الاستقرار ضد الانقلاب:</b> التأكد من أن معامل الأمان ضد الانقلاب <span dir="ltr">(Safety Factor against Overturning)</span> لا يقل عن <span dir="ltr">2.0</span> تحت أقصى أحمال رياح وزلازل.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ تدقيق سمك اللبشة لمقاومة القص الثاقب <span dir="ltr" style="font-size:14px; color:#d97706;">(Punching Shear Verification)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>السمك الحاكم للبشة <span dir="ltr">(Raft Thickness Tr)</span>:</b> يُحدد سمك اللبشة غالباً بناءً على قدرتها على مقاومة قوى القص الثاقب تحت الأعمدة الأثقل حملاً (خاصة الأعمدة الداخلية وأعمدة المصاعد وحوائط القص Core) بدون استخدام حديد تسليح للقص.'
        '</li>'
        '<li>'
        '<b>الحد الأدنى للسمك:</b> لا يقل سمك اللبشة المسلحة عادة عن <span dir="ltr">60 cm ~ 80 cm</span> للمباني متعددة الطوابق.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ منظومة التسليح المزدوج والحديد الإضافي <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Dual Mat Rebar & Additional Bars)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الرقة السفلية والرقة العلوية:</b> تسلح اللبشة بشبكتين كاملتين من الصلب عالي المقاومة (سفلية وعلوية في الاتجاهين) مع كراسي حديد لضبط المنسوب.'
        '</li>'
        '<li>'
        '<b>توزيع مناطق العزوم:</b> الرقة السفلية تقاوم العزوم الموجبة في منتصف البحور بين الأعمدة، بينما الرقة العلوية تقاوم العزوم السالبة أعلى الأعمدة ومحيطها، ويتم وضع حديد إضافي سفلي وعلوي مركز في المناطق الحرجة.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 9: GROUND SLABS (SOG) MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم أرضيات الخرسانة المسلحة SOG (ECP 203 / ACI 360R)", width="large")
def show_dialog_m9_ground_slab():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>🏗️ دليل وفلسفة تصميم البلاطات الأرضية الخرسانية</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(Slab on Grade SOG - ECP 203 & ACI 360R)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'الأصول الهندسية لتصميم الأرضيات الصناعية المرتكزة على التربة تحت أحمال عجلات الرافعات الشوكية <span dir="ltr" style="font-weight:700; color:#60a5fa;">(Forklifts)</span> '
        'وأحمال أرجل أرفف المستودعات الثقيلة <span dir="ltr" style="font-weight:700; color:#60a5fa;">(Post Loads)</span> وتفاصيل الفواصل والدواول.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ نظرية ويسترجارد للأحمال المركزة <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Westergaard Stress Analysis)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الحالات الثلاث لتحميل البلاطة:</b> تُحسب إجهادات الانحناء عند ثلاثة مواضع حرجة:'
        '<br/>• تحميل منتصف البلاطة <span dir="ltr">(Interior Loading)</span>: أقل إجهاد وأعلى أمان.'
        '<br/>• تحميل حافة البلاطة <span dir="ltr">(Edge Loading)</span>: إجهاد انحناء أعلى بحوالي <span dir="ltr">50%</span>.'
        '<br/>• تحميل ركن البلاطة <span dir="ltr">(Corner Loading)</span>: أشد الحالات حرجاً ويحكم تحديد السمك.'
        '</li>'
        '<li>'
        '<b>نصف قطر الصلابة النسبية <span dir="ltr">(Radius of Relative Stiffness ℓ)</span>:</b>'
        '<div dir="ltr" style="background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 13.5px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        'ℓ = [ (Ec × h³) / (12 × (1 - ν²) × k) ]^(1/4)'
        '</div>'
        'حيث يمثل <span dir="ltr">k</span> معامل رد فعل التربة، و <span dir="ltr">h</span> سمك البلاطة الخرسانية.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ فحص القص الثاقب لقوائم الأرفف والمعدات <span dir="ltr" style="font-size:14px; color:#16a34a;">(Rack Post Punching Shear)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>تركيز الأحمال على لوح التثبيت <span dir="ltr">(Base Plate)</span>:</b> تنتقل أحمال أرفف التخزين المرتفعة عبر لوح معدني صغير المساحة <span dir="ltr">(15×15 cm)</span>، مما يولد إجهادات قص ثاقب موضعية هائلة.'
        '</li>'
        '<li>'
        '<b>معيار التحقق:</b> تدقيق إجهاد الثقب على مسافة <span dir="ltr">d / 2</span> من محيط اللوح المعدني للتأكد من عدم تجاوزه للحد المسموح به <span dir="ltr">qp ≤ 0.8 × √(fcu / γc)</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ فلسفة وتخطيط فواصل التحكم والانكماش <span dir="ltr" style="font-size:14px; color:#d97706;">(Control & Contraction Joints)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>المسافات البينية للفواصل:</b> طبقاً لـ <span dir="ltr">ACI 360R</span>، يجب ألا تزيد المسافة بين فواصل الانكماش عن <span dir="ltr">24 ~ 30</span> ضعف سمك البلاطة (عادة من <span dir="ltr">4.0 m إلى 6.0 m</span> كحد أقصى).'
        '</li>'
        '<li>'
        '<b>عمق قطع الفاصل:</b> يُقطع الفاصل بالمنشار الخرساني بعمق لا يقل عن ربع سمك البلاطة <span dir="ltr">(h / 4)</span> خلال أول <span dir="ltr">12 ~ 24</span> ساعة من الصب لتوجيه الشروخ داخل الفاصل.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ قضبان الدواول وتفاصيل نقل قوى القص <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Dowel Bars & Load Transfer)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>قضبان الصلب الأملس المدهونة <span dir="ltr">(Smooth Dowels)</span>:</b> تستخدم لنقل قوى القص بين البلاطات المتجاورة عند الفواصل مع السماح بالحركة الأفقية الحرة للبلاطة نتيجة التمدد والانكماش.'
        '</li>'
        '<li>'
        '<b>أبعاد الدواول:</b> استخدام أسياخ ملساء بقطر <span dir="ltr">16 ~ 25 mm</span> وطول <span dir="ltr">40 ~ 50 cm</span> على مسافات <span dir="ltr">30 cm</span> مع دهان نصف السيخ بمادة مانعة للالتصاق ووضع جراب بلاستيكي نهايته.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 10: CIRCULAR TANK FOUNDATIONS MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم قواعد الخزانات الدائرية (ECP 203 Circular Tanks)", width="large")
def show_dialog_m10_circular_tank():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>🛢️ دليل وفلسفة تصميم قواعد الخزانات الدائرية</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Circular Tank Foundations Design)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'الاشتراطات الهندسية الخاصة للمنشآت المائية وخزانات حفظ السوائل، والتحليل القطري للعزوم الشعاعية والمماسية وقوى الشد الحلقي طبقاً لـ <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203</span> (ملحق المنشآت المائية).'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ توزيع الضغوط الهيدروستاتيكية وردود أفعال التربة <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Axisymmetric Hydrostatic Loading)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>التناظر المحوري الدائري <span dir="ltr">(Axisymmetry)</span>:</b> يتميز الخزان الدائري بتناظر تام في الأحمال حول المركز، حيث ينتقل وزن السائل <span dir="ltr">γw × H</span> والوزن الذاتي لحوائط الخزان وقاعدته بانتظام إلى تربة التأسيس.'
        '</li>'
        '<li>'
        '<b>حالات التحميل الحرجة:</b> دراسة حالتي الخزان ممتلئ تماماً بالماء مع ضغط التربة، وحالة الخزان فارغ مع ضغط المياه الجوفية الخارجية الصاعدة <span dir="ltr">(Uplift Pressure)</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ العزوم الشعاعية والعزوم المماسية <span dir="ltr" style="font-size:14px; color:#16a34a;">(Radial & Tangential Bending Moments)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>العزوم الشعاعية <span dir="ltr">(Radial Moments Mr)</span>:</b> تمثل العزوم على طول نصف القطر من المركز باتجاه الحافة، وتبلغ قيمتها العظمى إما عند المركز أو عند اتصال القاعدة الدائرية مع جدار الخزان حسب درجة التثبيت <span dir="ltr">(Fixed or Hinged Base)</span>.'
        '</li>'
        '<li>'
        '<b>العزوم المماسية <span dir="ltr">(Tangential Moments Mθ)</span>:</b> تمثل العزوم في الاتجاه الحلقي الدائري المتعامد مع نصف القطر، وتكون متساوية مع العزم الشعاعي عند المركز تماماً <span dir="ltr">(Mr = Mθ at r = 0)</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ قوى الشد الحلقي وحدود اتساع الشروخ <span dir="ltr" style="font-size:14px; color:#d97706;">(Ring Tension & Crack Width Limitation)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>التحكم الصارم في الشروخ <span dir="ltr">(Water-Tightness Criteria)</span>:</b> ينص الكود المصري للمنشآت المائية على ألا يتجاوز اتساع الشرخ المحسوب <span dir="ltr">wk ≤ 0.15 mm</span> للعناصر المعرضة لضغط السوائل لضمان عدم تسرب المياه وحماية حديد التسليح من الصدأ.'
        '</li>'
        '<li>'
        '<b>إجهاد الشد الخرساني المسموح به:</b> تصميم القطاعات المائية على مرحلة التشغيل <span dir="ltr">(Working Stress Design)</span> للتأكد من عدم تجاوز إجهاد الشد في الخرسانة لمقاومة الشد في الانحناء <span dir="ltr">fctr</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ تفاصيل شبكات التسليح الدائري والقطري <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Circular & Radial Rebar Detailing)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>التسليح الحلقي والقطري:</b> توضع أسياخ التسليح السفلية والعلوية في هيئة شبكة قطب دائرية (أسياخ دائرية متحدة المركز وأسياخ شعاعية متجهة للمركز) أو شبكة مربعة متعامدة مكافئة مع تعويض الحواف.'
        '</li>'
        '<li>'
        '<b>فواصل الصب وموانع تسرب المياه <span dir="ltr">(Waterstops)</span>:</b> وضع شريط مانع التسرب المطاطي أو الـ PVC عند فاصل الصب بين القاعدة الدائرية وحائط الخزان.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 11: STANDALONE FLAT SLAB MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 فلسفة واشتراطات تصميم البلاطات اللاكمرية المستقلة (Standalone Flat Slab - ECP 203)", width="large")
def show_dialog_m11_standalone_flat():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>🏢 دليل وفلسفة تصميم البلاطة اللاكمرية المستقلة</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(Standalone Flat Slab Design - ECP 203)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'الاشتراطات الهندسية وطريقة التصميم المباشر <span dir="ltr" style="font-weight:700; color:#60a5fa;">(Direct Design Method DDM)</span> '
        'وتوزيع العزوم على شرائح الأعمدة والوسط وفحص القص الثاقب وتفاصيل التسليح طبقاً لـ <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203-2018</span>.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ شروط تطبيق طريقة التصميم المباشر للكود المصري <span dir="ltr" style="font-size:14px; color:#3b82f6;">(DDM Limitations)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الاشتراطات الكودية الثلاثية:</b>'
        '<br/>• وجود 3 بحور على الأقل في كل اتجاه.'
        '<br/>• ألا تزيد نسبة البحر الأكبر إلى البحر الأصغر في أي باكية عن <span dir="ltr">1.33</span>.'
        '<br/>• ألا يتجاوز الحمل الحي ضعف الحمل الميت <span dir="ltr">(LL ≤ 2 × DL)</span>.'
        '</li>'
        '<li>'
        '<b>العزم الساكن الكلي للباكية <span dir="ltr">(Mo)</span>:</b>'
        '<div dir="ltr" style="background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 13.5px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        'Mo = (Wu × L2 × Ln²) / 8'
        '</div>'
        'حيث يمثل <span dir="ltr">Ln</span> البحر الصافي بين أوجه الأعمدة، و <span dir="ltr">L2</span> عرض شريحة الباكية.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ توزيع العزوم على شرائح الأعمدة والوسط <span dir="ltr" style="font-size:14px; color:#16a34a;">(Column & Field Strips)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>تقسيم العزم بين السالب والموجب:</b> في البواكي الداخلية، يوزع العزم الساكن بنسبة <span dir="ltr">65%</span> للعزم السالب أعلى الأعمدة و <span dir="ltr">35%</span> للعزم الموجب بمنتصف البحر.'
        '</li>'
        '<li>'
        '<b>شريحة العمود <span dir="ltr">(Column Strip)</span>:</b> تستحوذ على <span dir="ltr">75%</span> من العزم السالب الكلي و <span dir="ltr">60%</span> من العزم الموجب نظراً لصلابتها العالية بالقرب من الركائز.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ تدقيق القص الثاقب وتيجان الأعمدة <span dir="ltr" style="font-size:14px; color:#d97706;">(Punching Shear & Drop Panels)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>المحيط الحرج للثقب:</b> يُفحص القص الثاقب على بعد <span dir="ltr">d / 2</span> من محيط رأس العمود أو محيط سقوط البلاطة <span dir="ltr">(Drop Panel)</span>.'
        '</li>'
        '<li>'
        '<b>دور سقوط البلاطة:</b> يقلل من إجهادات الثقب بنسبة تتجاوز <span dir="ltr">40%</span> ويزيد من جساءة السقف ضد الترخيم الحرج <span dir="ltr">(Deflection)</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ تفاصيل التسليح وشبكتي الصلب <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Bottom & Top Reinforcement Details)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الشبكة السفلية المستمرة:</b> لا يقل التسليح السفلي المستمر في كامل البلاطة عن <span dir="ltr">0.25%</span> من مساحة القطاع الخرساني.'
        '</li>'
        '<li>'
        '<b>الحديد الإضافي العلوي:</b> يوضع حديد إضافي علوي مكثف في شريحة العمود بطول يمتد حتى ربع البحر الصافي <span dir="ltr">(0.25 Ln)</span> لمقاومة العزوم السالبة العظمى.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 12: STEEL REBAR PROPERTIES MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 المواصفات القياسية لأقطار وأوزان وتفاصيل حديد التسليح (ECP 203 Rebar Standards)", width="large")
def show_dialog_m12_steel_bars():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>⚙️ دليل المواصفات القياسية لحديد التسليح</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Steel Rebar Standards & Detailing)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'المرجع القياسي لخصائص ومواصفات حديد التسليح عالي المقاومة والصلب الأملس وفقاً للمواصفات القياسية المصرية <span dir="ltr" style="font-weight:700; color:#60a5fa;">ES 262</span> والكود المصري <span dir="ltr" style="font-weight:700; color:#60a5fa;">ECP 203-2018</span>.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ أوزان ومساحات الأقطار الاسمية القياسية <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Nominal Weight & Cross-Section Area)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>معادلة الوزن النظري للمتر الطولي:</b> تُحسب بدقة استناداً لكثافة الصلب <span dir="ltr">(7850 kg/m³)</span>:'
        '<div dir="ltr" style="background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 13.5px; font-family: Consolas, monospace; color: #0f172a; margin: 6px 0; font-weight: 700; border: 1px solid #cbd5e1; text-align: left;">'
        'Weight (kg/m) = D² (mm) / 162.2'
        '</div>'
        '</li>'
        '<li>'
        '<b>أوزان الأقطار الشائعة:</b> Φ8 = 0.395 kg/m | Φ10 = 0.617 kg/m | Φ12 = 0.888 kg/m | Φ16 = 1.580 kg/m | Φ18 = 2.000 kg/m | Φ25 = 3.850 kg/m.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ رتب الصلب وخواص الشد والمرونة <span dir="ltr" style="font-size:14px; color:#16a34a;">(Steel Grades & Elastic Modulus)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>رتب الكود المصري المعتمدة:</b>'
        '<br/>• صلب طري أملس <span dir="ltr">B240D-P (fy = 240 N/mm²)</span> للكانات الخفيفة.'
        '<br/>• صلب عالي المقاومة مشرشر <span dir="ltr">B400D-R (fy = 400 N/mm²)</span> للتسليح الطولي القياسي.'
        '<br/>• صلب عالي المقاومة فائق <span dir="ltr">B420D-R / B500D-R</span> للمباني الشاهقة والأبراج.'
        '</li>'
        '<li>'
        '<b>معامل المرونة القياسي:</b> يثبت لجميع الرتب بقيمة <span dir="ltr">Es = 200,000 N/mm² (2.0 × 10^6 kg/cm²)</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ أطوال التماسك وأطوال الوصلات بالركوب <span dir="ltr" style="font-size:14px; color:#d97706;">(Development & Splice Lengths)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>طول التماسك في الشد <span dir="ltr">(Ld Tension)</span>:</b> لا يقل عن <span dir="ltr">55 Φ</span> في الخرسانة العادية و <span dir="ltr">60 Φ ~ 65 Φ</span> للأسياخ العلوية المعرضة لظاهرة الخرسانة الرخوة أسفلها <span dir="ltr">(Top Bar Effect)</span>.'
        '</li>'
        '<li>'
        '<b>وصلات التراكب <span dir="ltr">(Lap Splices)</span>:</b> تبادل الوصلات <span dir="ltr">(Staggered Splices)</span> بحيث لا يزيد عدد الأسياخ الموصولة في قطاع واحد عن <span dir="ltr">50%</span>، مع تجنب الوصل في مناطق العزوم القصوى.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ أقطار بكرات الثني والتفريد التنفيذي <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Mandrel Diameters & Bending Rules)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>قطر بكرة ثني الأسياخ الطولية:</b> لا يقل القطر الداخلي لبكرة الثني عن <span dir="ltr">4 Φ</span> للأقطار حتى <span dir="ltr">Φ16</span>، و <span dir="ltr">6 Φ</span> للأقطار الأكبر لتفادي تهشم الخرسانة داخل زاوية الثني.'
        '</li>'
        '<li>'
        '<b>أطراف كانات الأعمدة والكمرات:</b> ثني طرف الكانة بزاوية <span dir="ltr">135°</span> مع امتداد طرف لا يقل عن <span dir="ltr">10 Φ</span> أو <span dir="ltr">75 mm</span> للحبس الزلزالي المحكم.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 13: CONCRETE QUANTITY SURVEY MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 الأصول الهندسية لحصر وتكعيب الكميات الخرسانية (ECP 203 Concrete Survey)", width="large")
def show_dialog_m13_concrete_survey():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>📊 دليل وأصول حصر وتكعيب الكميات الخرسانية</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Concrete Quantity Survey & BOQ)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'القواعد القياسية المعتمدة لحصر وتكعيب الخرسانة المسلحة والعادية، ومعدلات استهلاك حديد التسليح للمتر المكعب، واستخراج جداول الكميات التنفيذية والمستخلصات طبقاً للمواصفات القياسية المصرية.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ الأصول الهندسية للقياس الهندسي بالمتر المكعب <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Standard Measurement Rules m³)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>حجم الخرسانة الهندسي الصافي:</b> تُقاس الخرسانة هندسياً طبقاً للأبعاد الصريحة بالمخططات التنفيذية، مع عدم خصم حجم حديد التسليح المدفون بالخرسانة مهما بلغت نسبته.'
        '</li>'
        '<li>'
        '<b>خصم الفتحات:</b> تخصم الفتحات الإنشائية الكبرى (المناور، فتحات السلالم والمصاعد)، بينما لا تخصم الفتحات الصغيرة لمواسير الخدمات <span dir="ltr">(Sleeves)</span> الأقل من <span dir="ltr">0.05 m³</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ قواعد فصل وتكعيب العناصر الإنشائية <span dir="ltr" style="font-size:14px; color:#16a34a;">(Element Volumetric Separation)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الأعمدة ورقاب الأعمدة:</b> يقاس ارتفاع العمود من ظهر الخرسانة المسلحة للسقف أو القاعدة السفلية حتى بطنية السقف العلوي مباشرة منعاً لتكرار حساب مناطق تقاطع السقف مع الأعمدة.'
        '</li>'
        '<li>'
        '<b>الأسقف والكمرات:</b> تقاس البلاطات بكامل مسطحها الإجمالي شاملاً مناطق اتصالها برؤوس الأعمدة، ويسقط سمك البلاطة من عمق الكمرات الساقطة.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ المعدلات القياسية لاستهلاك حديد التسليح <span dir="ltr" style="font-size:14px; color:#d97706;">(Rebar Consumption Rates kg/m³)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>النسب الاسترشادية المعتمدة للمتر المكعب:</b>'
        '<br/>• القواعد والأساسات المنفصلة: <span dir="ltr">80 ~ 100 kg/m³</span>.'
        '<br/>• اللبشة المسلحة: <span dir="ltr">100 ~ 125 kg/m³</span>.'
        '<br/>• الأعمدة الخرسانية: <span dir="ltr">140 ~ 180 kg/m³</span>.'
        '<br/>• البلاطات اللاكمرية (Flat Slab): <span dir="ltr">120 ~ 155 kg/m³</span>.'
        '</li>'
        '<li>'
        '<b>معامل الهالك والوصلات:</b> يضاف معامل أمان وهالك تنفيذي <span dir="ltr">(Scrap & Lap Factor)</span> يتراوح بين <span dir="ltr">3% إلى 5%</span> عند إعداد طلبيات توريد وتوريد أطنان الحديد بالموقع.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ إعداد تقارير الحصر والتصدير التنفيذي <span dir="ltr" style="font-size:14px; color:#7c3aed;">(BOQ Breakdown & Exporting)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الفصل بين الدور الواحد وكامل المبنى:</b> توفير جداول حصر صبة السقف الفردي للطلبيات اللحظية للخرسانة الجاهزة <span dir="ltr">(Ready-Mix)</span>، وجداول الحصر التراكمي الشامل لكامل أدوار المبنى لإدارة عقود المقاولة ومستخلصات التنفيذ.'
        '</li>'
        '<li>'
        '<b>التصدير إلى Excel و PDF:</b> تنسيق البيانات الإنشائية بدقة مع دعم الطباعة باللغة العربية والتوجيه من اليمين لليسار.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 14: BRICK & PLASTERING SURVEY MODAL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

@st.dialog("📖 أصول وحسابات حصر أعمال المباني والمحارة والبياض (Brick & Plastering Survey)", width="large")
def show_dialog_m14_brick_survey():
    html_dialog = (
        '<div dir="rtl" style="direction: rtl; text-align: right; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; line-height: 1.85; color: #0f172a;">'
        '<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%); color: #ffffff; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; border: 1.5px solid #3b82f6; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.25);">'
        '<h3 style="margin: 0 0 10px 0; color: #93c5fd; font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">'
        '<span>🏠 دليل وأصول حصر أعمال المباني والمحارة</span> '
        '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(Brick & Plastering Survey Standards)</span>'
        '</h3>'
        '<p style="margin: 0; font-size: 14px; color: #e2e8f0; line-height: 1.7;">'
        'الأصول الهندسية والاشتراطات الفنية المعتمدة لحصر كميات الطوب الأحمر والإسمنتي، واستهلاك المونة الإسمنتية، وقواعد خصم الفتحات، وتكعيب ومساحات أعمال البياض والمحارة الداخلية والخارجية.'
        '</p>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #2563eb; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #1e40af; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '1️⃣ أصول قياس أعمال المباني بالعدد والمكعب والمسطح <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Units of Measurement)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الحوائط سمك 25 سم فأكثر (طوبة كاملة):</b> تُحصر هندسياً بالمتر المكعب <span dir="ltr">(m³)</span>، حيث يستهلك المتر المكعب مباني حوالي <span dir="ltr">420 ~ 450 طوبة</span> مقاس <span dir="ltr">25×12×6 cm</span>.'
        '</li>'
        '<li>'
        '<b>القواطيع سمك 12 سم (نصف طوبة):</b> تُحصر هندسياً بالمتر المربع <span dir="ltr">(m²)</span>، حيث يستهلك المتر المربع حوالي <span dir="ltr">55 ~ 58 طوبة</span>.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #16a34a; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #15803d; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '2️⃣ القواعد القياسية لخصم الفتحات هندسياً <span dir="ltr" style="font-size:14px; color:#16a34a;">(Openings Deduction Criteria)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>الفتحات الصغيرة (أقل من 0.5 م²):</b> لا تخصم إطلاقاً من مسطح المباني مقابل تكلفة هالك القص وتلبيش الأكتاف.'
        '</li>'
        '<li style="margin-bottom: 8px;">'
        '<b>الفتحات المتوسطة (من 0.5 م² إلى 3.0 م²):</b> يخصم نصف مساحة الفتحة مقابل مصنعيات الجلسات والأعتاب وتأسيس الحلوق.'
        '</li>'
        '<li>'
        '<b>الفتحات الكبيرة (أكبر من 3.0 م²):</b> تخصم مساحة الفتحة بالكامل من مسطح الحائط.'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #d97706; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #b45309; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '3️⃣ استهلاك المونة الإسمنتية ومكوناتها <span dir="ltr" style="font-size:14px; color:#d97706;">(Mortar Consumption & Mix Proportions)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>حجم المونة الإسمنتية الفعلي:</b> يمثل حجم المونة الفعلي حوالي <span dir="ltr">20% ~ 25%</span> من إجمالي حجم حائط المباني.'
        '</li>'
        '<li>'
        '<b>نسب خلط مونة المباني:</b> يخلط المتر المكعب رمل مع <span dir="ltr">300 ~ 350 kg</span> إسمنت بورتلاندي (حوالي <span dir="ltr">6 ~ 7 شكاير</span> إسمنت لكل متر مكعب رمل ناعم أو حرش).'
        '</li>'
        '</ul>'
        '</div>'

        '<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-right: 6px solid #7c3aed; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
        '<h4 style="color: #6d28d9; margin-top: 0; margin-bottom: 10px; font-size: 16.5px; font-weight: 800;">'
        '4️⃣ أصول حصر أعمال المحارة والبياض <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Plastering Take-off Standards)</span>'
        '</h4>'
        '<ul style="margin-bottom: 6px; padding-right: 22px; line-height: 1.8;">'
        '<li style="margin-bottom: 8px;">'
        '<b>طبقات البياض المتكاملة:</b>'
        '<br/>• الطرطشة العمومية <span dir="ltr">(Spatterdash)</span>: بمعدل <span dir="ltr">450 kg</span> إسمنت/م³ رمل سمك <span dir="ltr">0.5 cm</span>.'
        '<br/>• البؤج والأوتار <span dir="ltr">(Screeds & Dots)</span>: لضبط الاستواء والتعامد التام للحوائط.'
        '<br/>• البطانة والظهارة <span dir="ltr">(Undercoat & Finish Coat)</span>: سمك <span dir="ltr">1.5 ~ 2.0 cm</span> للحوائط و <span dir="ltr">1.0 cm</span> للأسقف.'
        '</li>'
        '<li>'
        '<b>حصر المسطحات:</b> تحصر مساحات المحارة بالمتر المربع الصافي للحوائط والأسقف والواجهات، مع حساب الجوانب <span dir="ltr">(Reveals)</span> لفتحات الأبواب والنوافذ.'
        '</li>'
        '</ul>'
        '</div>'
        '</div>'
    )
    st.markdown(html_dialog, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE METADATA MAPPING (KEYS 1 TO 14)
# ═══════════════════════════════════════════════════════════════════════════════

MODULE_PHILOSOPHY_MAP = {
    "columns": {
        "title": "🏛️ Module 2 – Rectangular Columns Design (ECP 203) (تصميم وتفاصيل الأعمدة المستطيلة)",
        "btn_text": "📖 الاطلاع على فلسفة واشتراطات تصميم الأعمدة المستطيلة (ECP 203)",
        "help_text": "عرض دليل واشتراطات الكود المصري لتصميم وتفاصيل الأعمدة المستطيلة ومقاومة الانبعاج",
        "dialog_func": show_dialog_m2_columns,
    },
    "footings": {
        "title": "🪸 Module 3 – Isolated Footings Design (ECP 203) (تصميم وتفاصيل القواعد المنفصلة)",
        "btn_text": "📖 الاطلاع على فلسفة واشتراطات تصميم القواعد المنفصلة (ECP 203)",
        "help_text": "عرض دليل واشتراطات تصميم القواعد المنفصلة والرفرفات وفحص القص والقص الثاقب",
        "dialog_func": show_dialog_m3_footings,
    },
    "two_col_footings": {
        "title": "📐 Module 4 – Combined Footings Design (ECP 203) (تصميم وتفاصيل القواعد المشتركة لعمودين)",
        "btn_text": "📖 الاطلاع على فلسفة واشتراطات تصميم القواعد المشتركة لعمودين (ECP 203)",
        "help_text": "عرض دليل واشتراطات الكود لتصميم القواعد المشتركة وتطابق المحصلة مع مركز المساحة",
        "dialog_func": show_dialog_m4_two_col,
    },
    "strap_footing": {
        "title": "🔗 Module 5 – Strap Footings Design (ECP 203) (تصميم وتفاصيل قواعد الشدادات والجار)",
        "btn_text": "📖 الاطلاع على فلسفة واشتراطات تصميم قواعد الشدادات والجار (ECP 203)",
        "help_text": "عرض دليل واشتراطات تصميم قواعد الجار والكمرات الشداد الجسئة لمقاومة عزوم الانقلاب",
        "dialog_func": show_dialog_m5_strap,
    },
    "diagonal_strap_footing": {
        "title": "📐 Module 6 – Corner Footing with Diagonal Strap (ECP 203) (تصميم قاعدة جار ركن بشداد مائل)",
        "btn_text": "📖 الاطلاع على فلسفة واشتراطات تصميم قواعد الجار بشداد مائل (ECP 203)",
        "help_text": "عرض دليل واشتراطات تصميم قواعد الركن المزدوجة اللامركزية والشداد المائل الفراغي",
        "dialog_func": show_dialog_m6_diagonal_strap,
    },
    "ground_beam": {
        "title": "🧱 Module 7 – Ground Beams Design & Detailing (ECP 203) (تصميم وتفاصيل الميدات والسملات)",
        "btn_text": "📖 الاطلاع على فلسفة واشتراطات تصميم الميدات والسملات (ECP 203)",
        "help_text": "عرض دليل واشتراطات تصميم السملات والميدات لمقاومة الهبوط التفاضلي وأحمال الحوائط",
        "dialog_func": show_dialog_m7_ground_beam,
    },
    "raft_foundations": {
        "title": "🏗️ Module 8 – Raft Foundations Design (ECP 203) (تصميم وتفاصيل اللبشة المسلحة)",
        "btn_text": "📖 الاطلاع على فلسفة واشتراطات تصميم اللبشة المسلحة (ECP 203)",
        "help_text": "عرض دليل واشتراطات تصميم اللبشة المسلحة وتوزيع إجهادات التربة والقص الثاقب",
        "dialog_func": show_dialog_m8_raft,
    },
    "ground_slab": {
        "title": "🏗️ Module 9 – Concrete Slabs on Grade SOG (ECP 203 / ACI 360R) (تصميم أرضيات الخرسانة المسلحة)",
        "btn_text": "📖 الاطلاع على فلسفة واشتراطات تصميم أرضيات الخرسانة المسلحة SOG (ECP 203 / ACI 360R)",
        "help_text": "عرض دليل واشتراطات تحليل ويسترجارد وفحص الأحمال المركزة وفواصل الانكماش والدواول",
        "dialog_func": show_dialog_m9_ground_slab,
    },
    "circular_tank_foundations": {
        "title": "🛢️ Module 10 – Circular Tank Foundations (ECP 203) (تصميم قواعد الخزانات الدائرية)",
        "btn_text": "📖 الاطلاع على فلسفة واشتراطات تصميم قواعد الخزانات الدائرية (ECP 203)",
        "help_text": "عرض دليل واشتراطات التصميم الدائري والعزوم الشعاعية والمماسية والشد الحلقي للخزانات",
        "dialog_func": show_dialog_m10_circular_tank,
    },
    "standalone_flat_slab": {
        "title": "🏢 Module 11 – Standalone Flat Slab Design (ECP 203) (تصميم البلاطات اللاكمرية المستقلة)",
        "btn_text": "📖 الاطلاع على فلسفة وتفاصيل تصميم البلاطة اللاكمرية المستقلة (ECP 203)",
        "help_text": "عرض دليل واشتراطات طريقة التصميم المباشر وفحص القص الثاقب وتفاصيل التسليح",
        "dialog_func": show_dialog_m11_standalone_flat,
    },
    "steel_bars": {
        "title": "⚙️ Module 12 – Steel Rebar Dimensions & Quantities (ECP 203) (أقطار وأوزان ومواصفات حديد التسليح)",
        "btn_text": "📖 الاطلاع على المواصفات القياسية لأقطار وأوزان وتفاصيل حديد التسليح (ECP 203)",
        "help_text": "عرض دليل الخصائص القياسية لأقطار حديد التسليح وأوزان المتر الطولي وأطوال التماسك والوصلات",
        "dialog_func": show_dialog_m12_steel_bars,
    },
    "concrete_survey": {
        "title": "📊 Module 13 – Comprehensive Concrete Quantity Survey (حصر وتدقيق الكميات الخرسانية)",
        "btn_text": "📖 الاطلاع على أصول وضوابط حصر الكميات والمواد الإنشائية (ECP 203 & BOQ)",
        "help_text": "عرض دليل القواعد الهندسية لحصر وتكعيب الخرسانة المسلحة والعادية ومعدلات استهلاك التسليح",
        "dialog_func": show_dialog_m13_concrete_survey,
    },
    "brick_survey": {
        "title": "🏠 Module 14 – Brick & Plastering Survey (حصر وتدقيق أعمال المباني والمحارة)",
        "btn_text": "📖 الاطلاع على أصول وحسابات حصر أعمال المباني والمحارة والبياض",
        "help_text": "عرض دليل القواعد الهندسية لحصر أعمال المباني بالمتر المكعب والمربع وخصم الفتحات والمحارة",
        "dialog_func": show_dialog_m14_brick_survey,
    },
}

# Aliases for robust matching from different router keys or module labels
_KEY_ALIASES = {
    "module 2": "columns",
    "module_2": "columns",
    "الأعمدة": "columns",
    "module 3": "footings",
    "module_3": "footings",
    "القواعد": "footings",
    "module 4": "two_col_footings",
    "module_4": "two_col_footings",
    "مشتركة": "two_col_footings",
    "module 5": "strap_footing",
    "module_5": "strap_footing",
    "الشدادات": "strap_footing",
    "module 6": "diagonal_strap_footing",
    "module_6": "diagonal_strap_footing",
    "مائل": "diagonal_strap_footing",
    "module 7": "ground_beam",
    "module_7": "ground_beam",
    "الميدات": "ground_beam",
    "module 8": "raft_foundations",
    "module_8": "raft_foundations",
    "اللبشة": "raft_foundations",
    "module 9": "ground_slab",
    "module_9": "ground_slab",
    "الأرضيات": "ground_slab",
    "module 10": "circular_tank_foundations",
    "module_10": "circular_tank_foundations",
    "الخزانات": "circular_tank_foundations",
    "module 11": "standalone_flat_slab",
    "module_11": "standalone_flat_slab",
    "المستقلة": "standalone_flat_slab",
    "module 12": "steel_bars",
    "module_12": "steel_bars",
    "أقطار": "steel_bars",
    "module 13": "concrete_survey",
    "module_13": "concrete_survey",
    "حصر": "concrete_survey",
    "module 14": "brick_survey",
    "module_14": "brick_survey",
    "طوب": "brick_survey",
    "المباني": "brick_survey",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  UNIFIED RENDERER FOR MODULE TITLE BANNER & PHILOSOPHY BUTTON
# ═══════════════════════════════════════════════════════════════════════════════

def render_module_header_and_philosophy(mod_key: str, prefix: str = ""):
    """
    Renders the centered amber title banner and the full-width amber philosophy button
    for any specified module (Modules 2 to 14) directly below the active project banner.
    """
    # Resolve key if alias passed
    normalized_key = mod_key.lower().strip() if mod_key else ""
    target_key = normalized_key
    if target_key not in MODULE_PHILOSOPHY_MAP:
        for alias, real_key in _KEY_ALIASES.items():
            if alias in target_key or target_key in alias:
                target_key = real_key
                break

    info = MODULE_PHILOSOPHY_MAP.get(target_key)
    if not info:
        return

    # 1. Inject styling
    inject_module_philosophy_css()

    # 2. Render Centered Amber Gradient Title Banner
    st.markdown(
        f"""
        <div class="module-unified-title-banner">
            <span>{info['title']}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Render Full-width Amber Gradient Philosophy Button
    btn_key = f"{prefix}btn_unified_philo_{target_key}"
    if st.button(
        info["btn_text"],
        key=btn_key,
        use_container_width=True,
        help=info["help_text"],
    ):
        info["dialog_func"]()

    st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)
