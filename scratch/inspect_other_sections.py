# -*- coding: utf-8 -*-
with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

def show_range(title, start, end, filter_kw=None):
    print(f"\n================ {title} (L{start}-L{end}) ================")
    for i in range(start, min(end + 1, len(lines) + 1)):
        l = lines[i - 1].rstrip()
        if filter_kw is None or any(k in l for k in filter_kw):
            print(f"L{i:5d}: {l[:140]}")

show_range("Columns Design (draw/render/svg/plot/fig/sketch)", 21997, 22946, ["draw", "plot", "fig", "svg", "sketch", "render_", "st.image", "st.pyplot", "st.expander", "components", "zoomable"])
show_range("Ground Beams (draw/render/svg/plot/fig/sketch)", 25952, 26331, ["draw", "plot", "fig", "svg", "sketch", "render_", "st.image", "st.pyplot", "st.expander", "components", "zoomable"])
show_range("Roof Beams (draw/render/svg/plot/fig/sketch)", 26332, 26702, ["draw", "plot", "fig", "svg", "sketch", "render_", "st.image", "st.pyplot", "st.expander", "components", "zoomable"])
show_range("Final Design & 3D BIM (L26703-L27128)", 26703, 27128, ["draw", "plot", "fig", "svg", "sketch", "render_", "st.image", "st.pyplot", "st.expander", "components", "zoomable", "bim_3d", "3D"])
