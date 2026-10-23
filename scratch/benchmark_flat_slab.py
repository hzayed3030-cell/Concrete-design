import time
import sys
sys.path.insert(0, '.')

import modules.flat_slab as fs
from modules.flat_slab import (
    get_flat_slab_columns,
    generate_flat_slab_sketch,
    calculate_punching_shear,
    calculate_flat_slab_deflections,
    calculate_boq,
)

Lx = [6.0, 6.0, 6.0, 6.0]
Ly = [6.0, 6.0, 6.0]
cant = {"left": 1.5, "right": 1.5, "bottom": 1.0, "top": 1.0}

print("Profiling Flat Slab execution...")

# 1. Column geometry & registry
t0 = time.perf_counter()
cols, all_c, eff_lx, eff_ly, _ = get_flat_slab_columns(Lx, Ly, bc_cm=30, tc_cm=60)
t_cols = time.perf_counter() - t0
print(f"1. Column Registry ({len(cols)} cols): {t_cols*1000:.1f} ms")

# 2. Matplotlib interactive sketch generation + rasterization
t0 = time.perf_counter()
fig = generate_flat_slab_sketch(Lx, Ly, cant, ts_initial=22, n_floors=5)
t_gen_fig = time.perf_counter() - t0

import io
t0 = time.perf_counter()
buf = io.BytesIO()
fig.savefig(buf, format="png", bbox_inches="tight", dpi=140)
t_save_fig = time.perf_counter() - t0
print(f"2. Interactive Sketch Draw: {t_gen_fig*1000:.1f} ms | Savefig (DPI 140): {t_save_fig*1000:.1f} ms | Total Sketch: {(t_gen_fig+t_save_fig)*1000:.1f} ms")

# 3. Punching shear calculation
t0 = time.perf_counter()
p_res = calculate_punching_shear(cols, Lx, Ly, cant, Wu=1.45, d_cm=19.0, Fcu=250.0, ts_cm=22.0)
t_punch = time.perf_counter() - t0
print(f"3. Punching Shear Check ({len(p_res)} cols): {t_punch*1000:.1f} ms")

# 4. Deflection calculation
t0 = time.perf_counter()
d_res = calculate_flat_slab_deflections(
    Lx, Ly, ts_cm=22.0, Wu_total=1.45, Wu_dead=1.05, Wu_live=0.40,
    Fcu=250.0, Fy=4000.0, cantilevers=cant, active_cols=cols
)
t_defl = time.perf_counter() - t0
print(f"4. Deflection Analysis: {t_defl*1000:.1f} ms")

# 5. BOQ calculation
t0 = time.perf_counter()
boq = calculate_boq(Lx, Ly, cant, ts_cm=22.0, mesh_btm_n=5, mesh_btm_dia=12, mesh_top_n=5, mesh_top_dia=10)
t_boq = time.perf_counter() - t0
print(f"5. BOQ: {t_boq*1000:.1f} ms")

# 6. Save settings file I/O
import json
t0 = time.perf_counter()
with open('profiles.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
with open('scratch/bench_save.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
t_io = time.perf_counter() - t0
print(f"6. JSON Profiles I/O: {t_io*1000:.1f} ms")
