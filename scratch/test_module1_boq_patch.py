# -*- coding: utf-8 -*-
"""
Full helper functions and render components for Module 1 BOQ & Takeoff
"""
import os, json, math, re, io, html, uuid
import streamlit as st

_CW_PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "m1_manual_boq_presets.json")
CW_MANUAL_BOQ_UNIT_OPTIONS = ["م² (m²)", "م³ (m³)", "متر طولي L.M", "عدد (No.)", "طن (Ton)", "كجم (Kg)", "مقطوعية (L.S)"]

def _get_cw_manual_boq_presets_list():
    """قراءة قائمة قوالب البنود الجاهزة المحفوظة على مستوى النظام لجميع المشاريع في Module 1."""
    presets = None
    if os.path.exists(_CW_PRESETS_FILE):
        try:
            with open(_CW_PRESETS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list) and len(loaded) > 0:
                    presets = loaded
        except Exception:
            presets = None
    if not presets:
        presets = [
            {
                "label": "✨ بند حر مخصص (إدخال يدوي حر)",
                "name": "بند إنشائي / مدني إضافي مخصص",
                "unit": "م² (m²)",
                "unit_price": 500.0,
                "mat_category": "supply_install",
                "description": "بالمتر المربع، توريد وتركيب وتنفيذ البند طبقاً للمواصفات الفنية وأصول الصناعة المعتمدة واشتراطات المهندس المشرف والكود المصري ECP."
            },
            {
                "label": "🪜 رخام درج السلالم (نائمة وقائمة)",
                "name": "أعمال رخام درج السلالم (نائمة 4 سم وقائمة 2 سم)",
                "unit": "متر طولي L.M",
                "unit_price": 950.0,
                "mat_category": "marble",
                "description": "بالمتر الطولي، توريد وتركيب رخام درج السلالم نائمة سماكة 4 سم بحلية مستديرة وقائمة سماكة 2 سم من الرخام الممتاز مع المونة واللصق والسقية وميزان المياه."
            },
            {
                "label": "🏛️ أعمال رخام وجرانيت بسطات وصدفات سلالم وأرضيات مداخل",
                "name": "رخام وجرانيت بسطات وصدفات السلالم والمداخل",
                "unit": "م² (m²)",
                "unit_price": 1300.0,
                "mat_category": "marble",
                "description": "بالمتر المربع، توريد وتركيب ألواح وترابيع رخام أو جرانيت سمك 2 سم لبسطات وصدفات السلالم والمداخل شاملاً فرشة الرمل ومونة اللصق والسقية والتشطيب وجلاء وتلميع الفواصل."
            },
            {
                "label": "🏛️ تكسية واجهات وحوائط بالحجر الفرعوني / الهاشمي",
                "name": "تكسية واجهات بحجر فرعوني / هاشمي هيصم مقاسات متنوعة",
                "unit": "م² (m²)",
                "unit_price": 650.0,
                "mat_category": "stone",
                "description": "بالمتر المربع، توريد وتركيب حجر فرعوني أو هاشمي للواجهات الخارجية والأسوار شاملاً المونة وتفتيح الفواصل والكانات والتثبيت الميكانيكي أو بالمونة الأسمنتية عيار 350 كجم/م³ ورش المياه."
            },
            {
                "label": "🪨 تكسية حوائط وواجهات بحجر مايكا / حجر طبيعي",
                "name": "تكسية حوائط بحجر مايكا طبيعي مجمع شرائح ديكورية",
                "unit": "م² (m²)",
                "unit_price": 850.0,
                "mat_category": "stone",
                "description": "بالمتر المربع، توريد وتركيب حجر مايكا طبيعي شرائح ديكورية للواجهات والأعمدة والمداخل شاملاً مونة اللصق ذات الإضافات ومادة السيلر العازل للرطوبة وتثبيت الزوايا."
            },
            {
                "label": "🛡️ درابزين وهاندريل سلالم وبلكونات (كريتال / استانلس)",
                "name": "درابزين وهاندريل سلالم وبلكونات حديد كريتال أو استانلس ستيل",
                "unit": "متر طولي L.M",
                "unit_price": 1400.0,
                "mat_category": "metal",
                "description": "بالمتر الطولي، توريد وتصنيع وتركيب درابزين حديد مشغول كريتال أو مواسير استانلس ستيل 304 للسلالم والتراسات شاملاً التثبيت بالجوايط والمونة والإيبوكسي والدهان المقاوم للصدأ والتشطيب."
            },
            {
                "label": "🚪 رخام أو جرانيت معابر وعتب وجلسات شبابيك",
                "name": "رخام وجرانيت معابر الأبواب وجلسات الشبابيك والدراوي",
                "unit": "متر طولي L.M",
                "unit_price": 450.0,
                "mat_category": "marble",
                "description": "بالمتر الطولي، توريد وتركيب جلسات شبابيك ومعابر أبواب من الرخام أو الجرانيت سمك 3-4 سم بعرض الحائط مع عمل شطف وقطر مياه ومونة التثبيت والسقية."
            },
            {
                "label": "🧱 وزرات رخام / جرانيت للسلالم والطرقات",
                "name": "وزرات رخام وجرانيت ارتفاع 10 سم للسلالم والممرات",
                "unit": "متر طولي L.M",
                "unit_price": 220.0,
                "mat_category": "marble",
                "description": "بالمتر الطولي، توريد وتركيب وزرات رخام أو جرانيت ارتفاع 10 سم سمك 2 سم بحلية أو شطف مائل شاملاً مونة اللصق والسقية والوزن التام مع التشطيب."
            },
            {
                "label": "🚪 باب رئيسي مصفح / بوابة حديد خارجية",
                "name": "أبواب مصفحة للمداخل أو بوابات حديد خارجية للمبنى",
                "unit": "عدد (No.)",
                "unit_price": 12000.0,
                "mat_category": "doors",
                "description": "بالعدد، توريد وتركيب باب شقة مصفح تركي درجة أولى شاملاً الحلق المصفح والضلع والإكسسوارات والكوالين الذكية والتثبيت التام بالكانات الإنشائية وحشو الحلق بالخرسانة والمونة."
            },
            {
                "label": "🏗️ خرسانة رغوية خفيفة لميول الأسطح (Foam Concrete)",
                "name": "خرسانة رغوية خفيفة الوزن لضبط ميول صرف مياه الأمطار بالأسطح",
                "unit": "م³ (m³)",
                "unit_price": 900.0,
                "mat_category": "concrete_special",
                "description": "بالمتر المكعب، توريد وصب خرسانة رغوية خفيفة الوزن بكثافة 800-1000 كجم/م³ لعمل ميول تصريف مياه الأمطار بالأسطح باتجاه الجراجير بميول لا تقل عن 1% مع التسوية والتنعيم بالهيلكوبتر."
            },
            {
                "label": "📐 أعمال فواصل التمدد والهبوط والووترستوب (Expansion Joints & Waterstop)",
                "name": "معالجة وتقفيل فواصل التمدد والهبوط وشرائح الووترستوب PVC",
                "unit": "متر طولي L.M",
                "unit_price": 650.0,
                "mat_category": "structural_joints",
                "description": "بالمتر الطولي، توريد وتنفيذ فواصل التمدد والهبوط الإنشائية شاملاً شرائح الووترستوب المطاطية PVC وحشو الفوم ومادة البولي يوريثان المطاطية المقاومة للعوامل الجوية وتغطية الفاصل ببلتات ألومنيوم."
            },
            {
                "label": "🛡️ أرضيات إيبوكسية مقاومة للمواد الكيميائية والاحتكاك (Epoxy Flooring)",
                "name": "أرضيات إيبوكسية ذاتية التسوية للجراجات وغرف الخدمات",
                "unit": "م² (m²)",
                "unit_price": 420.0,
                "mat_category": "epoxy",
                "description": "بالمتر المربع، توريد وتطبيق دهانات وأرضيات إيبوكسية ذاتية التسوية Self-Leveling Epoxy سمك 2-3 مم شاملاً تجهيز السطح بالصنفرة الميكانيكية وطبقة البرايمر والطبقة الإيبوكسية المقاومة للبري والكيماويات."
            }
        ]
        try:
            with open(_CW_PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(presets, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return presets

def _save_cw_manual_boq_presets_list(presets):
    """حفظ قائمة القوالب الجاهزة في ملف JSON."""
    try:
        with open(_CW_PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def _get_cw_manual_boq_items_list(prefix=""):
    """إرجاع قائمة البنود اليدوية المخزنة في session_state وإعدادات المشروع لـ Module 1."""
    from modules import settings as _S
    raw = st.session_state.get(f"{prefix}cw_manual_boq_items")
    if not isinstance(raw, list):
        raw = st.session_state.get("cw_manual_boq_items")
    if not isinstance(raw, list):
        raw = _S.cfg_val(f"{prefix}cw_manual_boq_items") or _S.cfg_val("cw_manual_boq_items") or []
    if not isinstance(raw, list):
        return []
    cleaned = []
    for x in raw:
        if isinstance(x, dict):
            c = dict(x)
            u = str(c.get("unit", "")).strip()
            if u in ("م.ط", "م.ط (m)", "متر طولي", "متر طولي L.M"):
                c["unit"] = "متر طولي L.M"
            cleaned.append(c)
    return cleaned

def _persist_cw_manual_boq_items(items_list, prefix=""):
    """حفظ البنود اليدوية لـ Module 1 في session_state والإعدادات."""
    from modules import settings as _S
    clean_list = [dict(x) for x in items_list if isinstance(x, dict)]
    st.session_state[f"{prefix}cw_manual_boq_items"] = clean_list
    st.session_state["cw_manual_boq_items"] = clean_list
    _S.cfg_set(f"{prefix}cw_manual_boq_items", clean_list)
    _S.cfg_set("cw_manual_boq_items", clean_list)
    _S.save_settings()

def _get_cw_manual_boq_t2_tuples(cw_qty_factor=1.00, start_idx=13, prefix=""):
    """تحويل البنود اليدوية الإضافية إلى صيغة تابل (name, net_q, unit, u_price, details) لتدمج في المقايسة."""
    manual_items = _get_cw_manual_boq_items_list(prefix=prefix)
    tuples_out = []
    for offset, m_item in enumerate(manual_items):
        idx = start_idx + offset
        raw_name = str(m_item.get("name", f"بند يدوي {idx}")).strip() or f"بند يدوي {idx}"
        net_q = round(float(m_item.get("net_qty", 0.0)), 2)
        unit = str(m_item.get("unit", "م² (m²)")).strip() or "م² (m²)"
        u_price = round(float(m_item.get("unit_price", 0.0)), 2)
        tot_q = round(net_q * float(cw_qty_factor), 2)
        details = (
            f"إدخال يدوي مباشر (خاضع لمعامل الزيادة): الكمية الصافية المدخلة ({net_q:,.2f} {unit}) "
            f"× معامل الزيادة ({float(cw_qty_factor):.2f}) = الكمية الإجمالية المعتمدة ({tot_q:,.2f} {unit})"
        )
        item_label = f"{idx}- {raw_name} (إدخال يدوي)"
        tuples_out.append((item_label, net_q, unit, u_price, details))
    return tuples_out

def _compute_cw_boq_items_materials_breakdown(
    cw_items_data,
    cw_qty_factor=1.00,
    slab_steel_ton=0.0,
    brick_l=25.0,
    brick_w=12.0,
    brick_h=6.0,
    mortar_cm=1.0,
    prefix=""
):
    """
    حساب تفصيلي لكميات المواد الأساسية المستخدمة في كل بند من بنود المقايسة الشاملة:
    (حديد التسليح - الخرسانة - الرمل - الأسمنت - الزلط - الطوب - المواد التكميلية)
    """
    mat_items = []
    tot_sand = 0.0
    tot_cement_kg = 0.0
    tot_gravel = 0.0
    tot_steel_ton = 0.0
    tot_bricks = 0

    import re as _re_mod

    for idx, (name, net_q, unit, u_price, details) in enumerate(cw_items_data, start=1):
        tot_q = round(net_q * cw_qty_factor, 2)
        clean_name = _re_mod.sub(r'^\d+\s*[-–.]\s*', '', str(name)).strip()

        sand_m3 = 0.0
        cem_kg = 0.0
        gravel_m3 = 0.0
        steel_ton = 0.0
        b_cnt = 0
        other_mat = "—"

        if tot_q > 0.0001:
            if idx == 1:
                # 1. خرسانة مسلحة أسقف وكمرات (م³)
                sand_m3 = round(tot_q * 0.40, 2)
                gravel_m3 = round(tot_q * 0.80, 2)
                cem_kg = round(tot_q * 350.0, 1)
                steel_ton = round(slab_steel_ton if slab_steel_ton > 0 else (tot_q * 0.110), 2)
                other_mat = f"خرسانة مسلحة ECP 203 + حديد عالي المقاومة ({steel_ton:,.2f} طن)"
            elif idx == 2:
                # 2. خرسانة مسلحة أعمدة (م³)
                sand_m3 = round(tot_q * 0.40, 2)
                gravel_m3 = round(tot_q * 0.80, 2)
                cem_kg = round(tot_q * 375.0, 1)
                steel_ton = round(tot_q * 0.150, 2)
                other_mat = f"خرسانة مسلحة أعمدة + حديد تسليح وكانات ({steel_ton:,.2f} طن)"
            elif idx == 3:
                # 3. خرسانة مسلحة أساسات وسملات (م³)
                sand_m3 = round(tot_q * 0.40, 2)
                gravel_m3 = round(tot_q * 0.80, 2)
                cem_kg = round(tot_q * 350.0, 1)
                steel_ton = round(tot_q * 0.090, 2)
                other_mat = f"أسمنت SRC مقاوم للكبريتات + حديد تسليح ({steel_ton:,.2f} طن)"
            elif idx == 4:
                # 4. خرسانة عادية أسفل القواعد والسملات (م³)
                sand_m3 = round(tot_q * 0.40, 2)
                gravel_m3 = round(tot_q * 0.80, 2)
                cem_kg = round(tot_q * 250.0, 1)
                other_mat = "خرسانة عادية 250 كجم/م³ (5 شكائر) بدون تسليح"
            elif idx == 5:
                # 5. أعمال الردم (م³)
                sand_m3 = round(tot_q, 2)
                other_mat = "رمال نظيفة متدرجة ودمك ميكانيكي على طبقات"
            elif idx == 6:
                # 6. طوب أسمنتي (طوبة)
                b_cnt = int(tot_q)
                sand_m3 = round(b_cnt * 0.00075, 2)
                cem_kg = round(sand_m3 * 350.0, 1)
                other_mat = "طوب أسمنتي مصمت/مفرغ + مونة أسمنتية عيار 350 كجم/م³"
            elif idx == 7:
                # 7. انترلوك أرصفة (م²)
                sand_m3 = round(tot_q * 0.06, 2)
                other_mat = f"بلاطات انترلوك سمك 6 سم ({tot_q:,.1f} م²) + فرشة رمل"
            elif idx == 8:
                # 8. بردورة أرصفة (م.ط)
                sand_m3 = round(tot_q * 0.02, 2)
                cem_kg = round(tot_q * 10.0, 1)
                gravel_m3 = round(tot_q * 0.03, 2)
                other_mat = f"بردورات خرسانية جاهزة ({tot_q:,.1f} م.ط) + فرشة خرسانة عادية"
            elif idx == 9:
                # 9. عزل رطوبة للقواعد والسملات (م²)
                other_mat = f"دهان بيتومين مؤكسد وجهين ({tot_q * 0.85:.1f} كجم بيتومين)"
            elif idx == 10:
                # 10. عزل مائي للسطح انسومات (م²)
                other_mat = f"لفائف ممبرين 4 مم ({tot_q * 1.10:.1f} م²) + برايمر ({tot_q * 0.30:.1f} لتر)"
            elif idx == 11:
                # 11. عازل حراري (م²)
                other_mat = f"ألواح بوليسترين XPS كثافة 35 كجم/م³ سمك 5 سم ({tot_q:,.1f} م²)"
            elif idx == 12:
                # 12. بلاط أسطح (م²)
                sand_m3 = round(tot_q * 0.06, 2)
                cem_kg = round(tot_q * 12.0, 1)
                other_mat = f"بلاط أسمنتي للسطح ({tot_q:,.1f} م²) + رمل فرشة ومونة وسقية"
            else:
                # بنود يدوية إضافية (Manual Items)
                u_str = str(unit)
                if "م²" in u_str or "متر مربع" in u_str:
                    sand_m3 = round(tot_q * 0.04, 2)
                    cem_kg = round(tot_q * 10.0, 1)
                    other_mat = f"توريد وتركيب خامات البند ({tot_q:,.2f} {unit}) ومونة التثبيت"
                elif "متر طولي" in u_str or "L.M" in u_str or "م.ط" in u_str:
                    sand_m3 = round(tot_q * 0.02, 2)
                    cem_kg = round(tot_q * 8.0, 1)
                    other_mat = f"توريد وتركيب خامات البند ({tot_q:,.2f} {unit}) ومونة التثبيت"
                elif "م³" in u_str or "متر مكعب" in u_str:
                    sand_m3 = round(tot_q * 0.40, 2)
                    gravel_m3 = round(tot_q * 0.80, 2)
                    cem_kg = round(tot_q * 300.0, 1)
                    other_mat = f"خامات خرسانة ومواد البند ({tot_q:,.2f} {unit})"
                else:
                    other_mat = f"توريد وتركيب طبقاً لأصول الصناعة ({tot_q:,.2f} {unit})"

        tot_sand += sand_m3
        tot_cement_kg += cem_kg
        tot_gravel += gravel_m3
        tot_steel_ton += steel_ton
        tot_bricks += b_cnt

        mat_items.append({
            "idx": idx,
            "name": clean_name,
            "tot_q": tot_q,
            "unit": unit,
            "sand_m3": sand_m3,
            "cem_kg": cem_kg,
            "cem_bags": int(round(cem_kg / 50.0)),
            "cem_tons": round(cem_kg / 1000.0, 2),
            "gravel_m3": gravel_m3,
            "steel_ton": steel_ton,
            "bricks": b_cnt,
            "other": other_mat,
        })

    tot_cement_tons = round(tot_cement_kg / 1000.0, 2)
    tot_cement_bags = int(round(tot_cement_kg / 50.0))

    return {
        "mat_items": mat_items,
        "tot_sand": round(tot_sand, 2),
        "tot_cement_kg": round(tot_cement_kg, 1),
        "tot_cement_tons": tot_cement_tons,
        "tot_cement_bags": tot_cement_bags,
        "tot_gravel": round(tot_gravel, 2),
        "tot_steel_ton": round(tot_steel_ton, 2),
        "tot_bricks": tot_bricks,
    }

print("Loaded all core functions successfully!")
