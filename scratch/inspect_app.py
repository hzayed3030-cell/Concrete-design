86: from modules.flat_slab import render as render_flat_slab
92: from modules.module_10_diagonal_strap import render_diagonal_strap_module
93: from modules.module_11_ground_beam import render_ground_beam_module
95: from modules.module_15_masonry_plaster import render_masonry_plaster_module
96: from modules.module_13_standalone_flat_slab import render as render_standalone_flat_slab
267: /* Radio Container (بانيل الموديولات) */
284: gap: 7px !important; /* فراغ Gap واضح ومنسق لفصل الموديولات عن بعض */
1950: <span>🎛️</span> New Project – Select Modules (تحديد الموديولات للمشروع الجديد)
1953: Please select the Modules you want to open in this new Project. (يرجى اختيار الموديولات التي ترغب في
2069: <span>اختيار الموديولات غير مسموح — MODULE SELECTION NOT ALLOWED</span>
2077: ℹ️ <b>تعليمات الارتباط الهندسي:</b> عند اختيار Module 1 (التصميم الإنشائي المتكامل)، يجب تفعيل موديو
2093: help="إنشاء المشروع الجديد وفتحه للعمل فوراً" if not btn_next_disabled else "يرجى تصحيح اختيار المود
2176: ⚠️ سيتم حذف المشروع بالكامل بجميع البيانات والموديولات  !
2417: custom_badge_html = f'<span style="background: rgba(2, 132, 199, 0.15); color: #0369a1; border: 1.5p
2507: btn_mod_label = "🔼 إخفاء" if is_mod_open else "🎛️ موديولات"
2512: help=f"تخصيص الموديولات المتاحة لمشروع {pname}",
2521: btn_del_mod_label = "🔼 إخفاء" if is_del_mod_open else "🗑️ حذف موديولات"
2526: help=f"حذف (soft delete) موديولات من مشروع {pname} مع إمكانية الاستعادة لاحقاً",
2542: help=f"استعادة موديول محذوف في مشروع {pname}" if has_trash else "لا توجد موديولات محذوفة في هذا المش
2590: أدخل الاسم الجديد للمشروع واضغط «حفظ الاسم الجديد» أو اضغط Enter. سيتم تحديث اسم المشروع في كافة الس
2666: <span>🎛️</span> تخصيص الموديولات المتاحة لمشروع: <b style="color: #38bdf8;">«{pname}»</b>
2669: اختر الموديولات التي ترغب في إظهارها في القائمة الجانبية لهذا المشروع، وسيتم إخفاء باقي الموديولات غ
2749: st.info("ℹ️ جميع الموديولات في هذا المشروع محذوفة. يمكنك استعادتها من زر ♻️ استعادة.")
2754: st.warning("⚠️ يرجى اختيار موديول واحد على الأقل.")
2782: f'<span>خريطة وقواعد الارتباطات الهندسية لحذف الموديولات — مشروع: <b style="color: #fbcfe8;">«{pname
2785: # Rule 1: Module 1 (Can be deleted alone)
2789: f'<span>1️⃣ موديول 1: التصميم الإنشائي المتكامل (Module 1: Integrated Structural Design) — [مسموح حذ
2792: f'يمكن حذف هذا الموديول بمفرده بأمان تام؛ وستستمر الموديولات التابعة التالية بالعمل في المشروع كأنظم
2795: f'• <span style="color: #818cf8;">موديول 2: الأعمدة المستطيلة (Module 2: Rectangular Columns)</span>
2796: f'• <span style="color: #fbbf24;">موديول 3: القواعد المنفصلة (Module 3: Isolated Footings ECP 203)</
2797: f'• <span style="color: #fbbf24;">موديول 4: تصميم قاعدة مشتركة لعمودين (Module 4: Two-columns combin
2798: f'• <span style="color: #fbbf24;">موديول 5: قواعد الشدادات - الجار (Module 5: Reinforced Concrete St
2799: f'• <span style="color: #fbbf24;">موديول 6: قاعدة جار ركن بشداد مائل (Module 6: Corner Footing with 
2800: f'• <span style="color: #34d399;">موديول 7: تصميم وتفاصيل الميدات والسملات (Module 7: Ground Beam De
2803: f'← لا يتأثر عمل أي موديول من الموديولات التابعة الستة المذكورة أعلاه عند حذف موديول 1 منفرداً.'
2807: # Rule 2: Modules 2..7 (Cannot be deleted alone while Module 1 is active)
2811: f'<span>2️⃣ الموديولات التابعة لموديول 1 (لا يمكن حذف أي منها بمفرده طالما موديول 1 نشط في المشروع):
2814: f'⚠️ السبب: موديول 1 يستدعي معادلات وحسابات هذه الموديولات لشبكة الأعمدة والأساسات والميدات، لذا لا 
2817: f'• <span style="color: #818cf8;">موديول 2: الأعمدة المستطيلة (Module 2: Rectangular Columns)</span>
2818: f'• <span style="color: #fbbf24;">موديول 3: القواعد المنفصلة (Module 3: Isolated Footings ECP 203)</
2819: f'• <span style="color: #fbbf24;">موديول 4: تصميم قاعدة مشتركة لعمودين (Module 4: Two-columns combin
2820: f'• <span style="color: #fbbf24;">موديول 5: قواعد الشدادات - الجار (Module 5: Reinforced Concrete St
2821: f'• <span style="color: #fbbf24;">موديول 6: قاعدة جار ركن بشداد مائل (Module 6: Corner Footing with 
2822: f'• <span style="color: #34d399;">موديول 7: تصميم وتفاصيل الميدات والسملات (Module 7: Ground Beam De
2830: f'<span>3️⃣ باقي الموديولات المستقلة (يمكن حذف أي موديول منها بحرية تامة دون أي ارتباط):</span>'
2833: f'✅ هذه الموديولات مستقلة بـ 0 اعتماديات متبادلة، ويمكن حذف أي منها منفرداً أو ضمن مجموعة دون التأثي
2836: f'• <span style="color: #60a5fa;">موديول 8: اللبشة المسلحة (Module 8: Raft Foundations)</span><br/>'
2837: f'• <span style="color: #a7f3d0;">موديول 9: بلاطات الأرضيات الخرسانية SOG (Module 9: Ground Slabs)</
2838: f'• <span style="color: #34d399;">موديول 10: قواعد الخزانات الدائرية (Module 10: Circular Tank Found
2839: f'• <span style="color: #93c5fd;">موديول 11: البلاطة اللاكمرية المستقلة (Module 11: Standalone - Fla
2840: f'• <span style="color: #f472b6;">موديول 12: أقطار وأوزان حديد التسليح (Module 12: Steel Rebar Dimen
2841: f'• <span style="color: #c084fc;">موديول 13: حصر الكميات الخرسانية (Module 13: Concrete Quantity Sur
2842: f'• <span style="color: #fb923c;">موديول 15: اعمال المباني والمحارة (Module 15: Masonry & Plastering
2851: st.info("✅ لا توجد موديولات نشطة يمكن حذفها في هذا المشروع.")
2860: <div style='font-size: 15px; color: #cbd5e1; margin-bottom: 10px; font-weight: 700;'>حدد الموديولات 
2930: st.warning("⚠️ يرجى تحديد موديول واحد على الأقل للحذف.")
2969: f'💡 <b>الحل الهندسي:</b> لحذف أي موديول من موديولات الأعمدة أو القواعد أو الميدات (Modules 2..7)، يج
3000: f'⚠️ <b>تنبيه ارتباط متبادل:</b> تحتوي هذه العملية على موديولات مرتبطة ببعضها وسيتم حذفها معاً كحزمة
3011: f'<span>تأكيد حذف الموديولات المحددة ({len(del_names)} موديول) — مشروع: «{pname}»</span>'
3014: f'سيتم حذف الموديولات التالية من المشروع ونقلها إلى سلة المحذوفات:'
3021: f'✅ <b>الحفظ الآمن:</b> سيتم حفظ نسخة كاملة (Snapshot) من جميع بيانات ومدخلات هذه الموديولات، ويمكنك
3081: f'<span>♻️</span> استعادة موديول محذوف — مشروع: <b style="color: #86efac;">«{pname}»</b>'
3084: f'سيتم استعادة الموديول وجميع بياناته وإعداداته كما كانت قبل الحذف.'
3091: st.info("✅ لا توجد موديولات محذوفة يمكن استعادتها في هذا المشروع.")
3094: "<div style='font-size: 14px; color: #cbd5e1; margin-bottom: 8px; font-weight: 600;'>الموديولات المح
3196: custom_badge_html = f'<span style="background: rgba(56, 189, 248, 0.15); color: #7dd3fc; border: 1px
3493: if "Module 15" in module or "masonry_plaster" in module or "اعمال المباني" in module:
3495: elif "Module 13" in module or "concrete_survey" in module or ("Concrete" in module and "Survey" in m
3497: elif "Module 12" in module or "steel_bars" in module or "Steel Rebar" in module or "أقطار" in module
3499: elif "Module 11" in module or "standalone_flat_slab" in module or "المستقلة" in module:
3500: target_k = "standalone_flat_slab"
3501: elif "Module 10" in module or "circular_tank" in module or "الخزانات" in module:
3519: elif "Module 1" in module or "Integrated" in module or "flat_slab" in module:
3520: target_k = "flat_slab"
3523: if target_k and target_k != "flat_slab":
3527: if mod_key == "masonry_plaster" or "Module 15" in module or "masonry_plaster" in module or "اعمال ال
3531: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 15: {ex}")
3533: elif mod_key == "concrete_survey" or "Module 13" in module or "concrete_survey" in module or ("Concr
3537: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 13: {ex}")
3539: elif mod_key == "steel_bars" or "Module 12" in module or "steel_bars" in module or "Steel Rebar" in 
3541: elif mod_key == "standalone_flat_slab" or "Module 11" in module or "standalone_flat_slab" in module 
3543: render_standalone_flat_slab()
3545: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 11: {ex}")
3547: elif mod_key == "circular_tank_foundations" or "Module 10" in module or "circular_tank" in module or
3551: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 10: {ex}")
3559: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 8: {ex}")
3565: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 7: {ex}")
3571: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 6: {ex}")
3577: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 5: {ex}")
3583: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 4: {ex}")
3589: elif mod_key == "flat_slab" or "Module 1" in module or "Integrated" in module or "flat_slab" in modu
3591: render_flat_slab()
3593: st.error(f"⚠️ حدث خطأ أثناء تشغيل موديول 1: {ex}")
3596: render_flat_slab()
