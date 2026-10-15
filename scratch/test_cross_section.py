import sys
sys.stdout.reconfigure(encoding='utf-8')
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_beam_cross_section_sketch(beam_data: dict, figsize=(5.5, 6.5)):
    """
    رسم تفصيلي هندسي عالي الدقة للقطاع العرضي للكمرة الساقطة يوضح:
    - الأبعاد الخرسانية (b × t مم)
    - الكانة المغلقة مع الأركان والغلق بزاوية 135 درجة
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
    
    fig, ax = plt.subplots(figsize=figsize, dpi=120)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')
    
    # 1. رسم القطاع الخرساني (Concrete Section)
    conc_rect = patches.Rectangle(
        (0, 0), b_cm, t_cm,
        linewidth=2.5, edgecolor='#0f172a', facecolor='#f1f5f9', zorder=2
    )
    ax.add_patch(conc_rect)
    
    # 2. رسم الكانة (Stirrup)
    stirrup_x = cover_cm
    stirrup_y = cover_cm
    stirrup_w = b_cm - 2 * cover_cm
    stirrup_h = t_cm - 2 * cover_cm
    stirrup_rect = patches.Rectangle(
        (stirrup_x, stirrup_y), stirrup_w, stirrup_h,
        linewidth=2.0, edgecolor='#2563eb', facecolor='none',
        linestyle='-', zorder=3
    )
    ax.add_patch(stirrup_rect)
    
    # رسم قفل الكانة 135 درجة عند الركن العلوي الأيمن
    hook_len = 2.0
    ax.plot([stirrup_x + stirrup_w, stirrup_x + stirrup_w - hook_len],
            [stirrup_y + stirrup_h, stirrup_y + stirrup_h - hook_len],
            color='#2563eb', lw=2.0, zorder=3)
    ax.plot([stirrup_x + stirrup_w, stirrup_x + stirrup_w - hook_len],
            [stirrup_y + stirrup_h - 0.4, stirrup_y + stirrup_h - hook_len - 0.4],
            color='#2563eb', lw=2.0, zorder=3)
            
    # 3. أسياخ التسليح السفلي (Bottom Main Rebars)
    n_btm = beam_data.get("n_bars_btm", 4)
    dia_main = beam_data.get("dia_main", 16)
    r_bar_cm = (dia_main / 10.0) / 2.0
    # رسم الأسياخ داخل حدود الكانة
    if n_btm == 1:
        x_btm_coords = [stirrup_x + stirrup_w / 2.0]
    else:
        spacing_btm = (stirrup_w - 2 * r_bar_cm) / (n_btm - 1)
        x_btm_coords = [stirrup_x + r_bar_cm + i * spacing_btm for i in range(n_btm)]
        
    y_btm = stirrup_y + r_bar_cm + 0.2
    for bx in x_btm_coords:
        bar_c = patches.Circle((bx, y_btm), r_bar_cm, facecolor='#1e40af', edgecolor='#0f172a', lw=1.2, zorder=5)
        ax.add_patch(bar_c)
        
    # 4. أسياخ التسليح العلوي (Top Hanger Rebars)
    n_top = beam_data.get("n_bars_top", 2)
    dia_top = 12
    r_top_cm = (dia_top / 10.0) / 2.0
    if n_top == 1:
        x_top_coords = [stirrup_x + stirrup_w / 2.0]
    else:
        spacing_top = (stirrup_w - 2 * r_top_cm) / (n_top - 1)
        x_top_coords = [stirrup_x + r_top_cm + i * spacing_top for i in range(n_top)]
        
    y_top = stirrup_y + stirrup_h - r_top_cm - 0.2
    for tx in x_top_coords:
        bar_c = patches.Circle((tx, y_top), r_top_cm, facecolor='#dc2626', edgecolor='#0f172a', lw=1.2, zorder=5)
        ax.add_patch(bar_c)
        
    # 5. أسياخ الانكماش الجانبية (Skin Reinforcement)
    n_skin = beam_data.get("n_skin_per_side", 0)
    dia_skin = 10
    r_skin_cm = (dia_skin / 10.0) / 2.0
    if n_skin > 0:
        step_skin = (stirrup_h - 2 * r_bar_cm - 2 * r_top_cm) / (n_skin + 1)
        for i in range(1, n_skin + 1):
            sy = stirrup_y + r_bar_cm + i * step_skin
            # سيخ على اليسار
            bar_l = patches.Circle((stirrup_x + r_skin_cm + 0.1, sy), r_skin_cm, facecolor='#16a34a', edgecolor='#0f172a', lw=1.2, zorder=5)
            # سيخ على اليمين
            bar_r = patches.Circle((stirrup_x + stirrup_w - r_skin_cm - 0.1, sy), r_skin_cm, facecolor='#16a34a', edgecolor='#0f172a', lw=1.2, zorder=5)
            ax.add_patch(bar_l)
            ax.add_patch(bar_r)
            
    # 6. أبعاد العرض والعمق (Dimensions)
    # بعد العرض أسفل القطاع
    dim_y = -3.5
    ax.annotate("", xy=(b_cm, dim_y), xytext=(0, dim_y),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.5, shrinkA=0, shrinkB=0))
    ax.plot([0, 0], [dim_y - 0.8, 0], color="#94a3b8", lw=0.8, linestyle=":")
    ax.plot([b_cm, b_cm], [dim_y - 0.8, 0], color="#94a3b8", lw=0.8, linestyle=":")
    ax.text(b_cm / 2.0, dim_y - 1.2, f"b = {b_mm} mm", color="#0f172a", fontsize=11, weight="bold", ha="center", va="top")
    
    # بعد العمق يسار القطاع
    dim_x = -3.5
    ax.annotate("", xy=(dim_x, t_cm), xytext=(dim_x, 0),
                arrowprops=dict(arrowstyle="<->", color="#0f172a", lw=1.5, shrinkA=0, shrinkB=0))
    ax.plot([dim_x - 0.8, 0], [0, 0], color="#94a3b8", lw=0.8, linestyle=":")
    ax.plot([dim_x - 0.8, 0], [t_cm, t_cm], color="#94a3b8", lw=0.8, linestyle=":")
    ax.text(dim_x - 1.2, t_cm / 2.0, f"t = {t_mm} mm", color="#0f172a", fontsize=11, weight="bold", ha="right", va="center", rotation=90)
    
    # 7. وسوم وشروحات التسليح (Annotations / Callouts)
    # وسام التسليح السفلي
    callout_x = b_cm + 3.0
    ax.annotate(
        f"Bottom RFT: {beam_data.get('rft_btm_str', '')}\n(تسليح رئيسي سفلي)",
        xy=(b_cm - cover_cm - r_bar_cm, y_btm),
        xytext=(callout_x, y_btm - 1.5),
        arrowprops=dict(arrowstyle="->", color="#1e40af", lw=1.5),
        fontsize=10, weight="bold", color="#1e40af", va="center"
    )
    
    # وسام التسليح العلوي
    ax.annotate(
        f"Top RFT: {beam_data.get('rft_top_str', '')}\n(تعليق كانات علوي)",
        xy=(b_cm - cover_cm - r_top_cm, y_top),
        xytext=(callout_x, y_top + 1.5),
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
            xytext=(callout_x, t_cm / 2.0 - 6.0),
            arrowprops=dict(arrowstyle="->", color="#16a34a", lw=1.5),
            fontsize=9.5, weight="bold", color="#16a34a", va="center"
        )
        
    ax.set_xlim(-7.0, b_cm + 17.0)
    ax.set_ylim(-7.0, t_cm + 6.0)
    ax.set_aspect("equal")
    ax.axis("off")
    
    fig.suptitle(f"Cross-Section: {beam_data.get('id', 'B1')} ({b_mm} × {t_mm} mm)", fontsize=13, weight="bold", color="#0f172a", y=0.96)
    fig.tight_layout()
    return fig

b_test = {
    "id": "B1", "b_mm": 250, "t_mm": 600,
    "n_bars_btm": 4, "dia_main": 16, "rft_btm_str": "4Φ16",
    "n_bars_top": 2, "rft_top_str": "2Φ12",
    "stirrups_str": "6Φ8/m (فرعين)",
    "n_skin_per_side": 2, "skin_rft_str": "2Φ10 لكل جانب"
}
fig = generate_beam_cross_section_sketch(b_test)
fig.savefig("scratch/test_cross_section.png", dpi=120)
print("Cross section figure saved successfully!")
