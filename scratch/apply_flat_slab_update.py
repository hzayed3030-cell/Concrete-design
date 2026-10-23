with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update import
t1 = """from modules.drop_beams_engine import (
    design_drop_beam,
    recompute_all_drop_beams,
    auto_merge_collinear_beams,
    draw_beam_polygon_on_plan,
    generate_beam_cross_section_sketch,
    build_beams_summary_dataframe,
)"""

r1 = """from modules.drop_beams_engine import (
    design_drop_beam,
    recompute_all_drop_beams,
    remap_beams_on_span_change,
    auto_merge_collinear_beams,
    draw_beam_polygon_on_plan,
    generate_beam_cross_section_sketch,
    build_beams_summary_dataframe,
)"""

assert t1 in content, "Target 1 (import) not found!"
content = content.replace(t1, r1, 1)

# 2. Update _geometry_key
t2 = """def _geometry_key(Lx_spans, Ly_spans):
    \"\"\"Return a hashable key representing the current span geometry, used to detect input changes.\"\"\"
    return (tuple(round(x, 4) for x in Lx_spans), tuple(round(y, 4) for y in Ly_spans))"""

r2 = """def _geometry_key(Lx_spans, Ly_spans, cantilevers=None):
    \"\"\"Return a hashable key representing the current span geometry, used to detect input changes.\"\"\"
    c_tup = ()
    if isinstance(cantilevers, dict):
        c_tup = (
            round(float(cantilevers.get("left", 0.0) or 0.0), 4),
            round(float(cantilevers.get("right", 0.0) or 0.0), 4),
            round(float(cantilevers.get("bottom", 0.0) or 0.0), 4),
            round(float(cantilevers.get("top", 0.0) or 0.0), 4),
        )
    return (tuple(round(x, 4) for x in Lx_spans), tuple(round(y, 4) for y in Ly_spans), c_tup)"""

assert t2 in content, "Target 2 (_geometry_key) not found!"
content = content.replace(t2, r2, 1)

# 3. Update split_span (X-dir)
t3 = """        cur_beams = list(
            st.session_state.get("fs_drop_beams")
            or cfg.get("fs_drop_beams")
            or S.cfg_val("fs_drop_beams", [])
            or []
        )
        updated_beams = []
        for b in cur_beams:
            b_copy = dict(b)
            if b_copy.get("axis_type") == "Y":
                old_ax_idx = b_copy.get("axis_index", 1) - 1
                if old_ax_idx >= inserted_col_idx:
                    new_ax_idx = old_ax_idx + 1
                    b_copy["axis_index"] = new_ax_idx + 1
                    b_copy["axis_name"] = f"Y{new_ax_idx + 1}"
            bp1_g = list(b.get("p1_grid", b.get("p1", [0, 0])))
            bp2_g = list(b.get("p2_grid", b.get("p2", [0, 0])))
            b_copy["p1_grid"] = bp1_g
            b_copy["p2_grid"] = bp2_g
            b_copy["p1"] = list(bp1_g)
            b_copy["p2"] = list(bp2_g)
            updated_beams.append(b_copy)"""

r3 = """        cur_beams = list(
            st.session_state.get("fs_drop_beams")
            or cfg.get("fs_drop_beams")
            or S.cfg_val("fs_drop_beams", [])
            or []
        )
        if cur_beams:
            updated_beams = remap_beams_on_span_change(
                cur_beams=cur_beams,
                old_Lx_spans=Lx_spans,
                new_Lx_spans=new_spans,
                old_Ly_spans=Ly_spans,
                new_Ly_spans=Ly_spans,
                old_cantilevers=_cur_cant,
                new_cantilevers=_cur_cant,
            )
        else:
            updated_beams = []"""

assert t3 in content, "Target 3 (split_span X) not found!"
content = content.replace(t3, r3, 1)

# 4. Update split_span (Y-dir)
t4 = """        cur_beams = list(
            st.session_state.get("fs_drop_beams")
            or cfg.get("fs_drop_beams")
            or S.cfg_val("fs_drop_beams", [])
            or []
        )
        updated_beams = []
        for b in cur_beams:
            b_copy = dict(b)
            if b_copy.get("axis_type") == "X":
                old_ax_idx = b_copy.get("axis_index", 1) - 1
                if old_ax_idx >= inserted_row_idx:
                    new_ax_idx = old_ax_idx + 1
                    b_copy["axis_index"] = new_ax_idx + 1
                    b_copy["axis_name"] = f"X{new_ax_idx + 1}"
            bp1_g = list(b.get("p1_grid", b.get("p1", [0, 0])))
            bp2_g = list(b.get("p2_grid", b.get("p2", [0, 0])))
            b_copy["p1_grid"] = bp1_g
            b_copy["p2_grid"] = bp2_g
            b_copy["p1"] = list(bp1_g)
            b_copy["p2"] = list(bp2_g)
            updated_beams.append(b_copy)"""

r4 = """        cur_beams = list(
            st.session_state.get("fs_drop_beams")
            or cfg.get("fs_drop_beams")
            or S.cfg_val("fs_drop_beams", [])
            or []
        )
        if cur_beams:
            updated_beams = remap_beams_on_span_change(
                cur_beams=cur_beams,
                old_Lx_spans=Lx_spans,
                new_Lx_spans=Lx_spans,
                old_Ly_spans=Ly_spans,
                new_Ly_spans=new_spans,
                old_cantilevers=_cur_cant,
                new_cantilevers=_cur_cant,
            )
        else:
            updated_beams = []"""

assert t4 in content, "Target 4 (split_span Y) not found!"
content = content.replace(t4, r4, 1)

# 5. Update geometry-change guard
t5 = """    # ── 5a. Geometry-change guard ────────────────────────────────────────────
    # If the user edits spans, the column & panel numbering changes → auto-reset pending.
    _geom_key = _geometry_key(Lx_spans, Ly_spans)
    if st.session_state.get("_fs_last_geom_key") != _geom_key:
        st.session_state["_fs_last_geom_key"]        = _geom_key
        st.session_state["_fs_pending_removals"]     = []
        st.session_state["_fs_pending_voids"]        = []
        st.session_state["_fs_show_confirm"]         = False
        st.session_state["_fs_show_void_confirm"]    = False
        st.session_state["_fs_pending_snapshot"]     = []
        st.session_state["_fs_pending_void_snapshot"] = []"""

r5 = """    # ── 5a. Geometry-change guard & Drop beams remapping ─────────────────────
    # If the user edits spans, the axes, columns & drop beams shift seamlessly to track the new geometry.
    _geom_key = _geometry_key(Lx_spans, Ly_spans, cantilevers)
    _last_geom_key = st.session_state.get("_fs_last_geom_key")
    _last_pname = st.session_state.get("_fs_last_active_profile")

    if _last_pname != active_profile_name:
        st.session_state["_fs_last_active_profile"] = active_profile_name
        st.session_state["_fs_last_geom_key"] = _geom_key
        st.session_state["_fs_prev_Lx_spans"] = list(Lx_spans)
        st.session_state["_fs_prev_Ly_spans"] = list(Ly_spans)
        st.session_state["_fs_prev_cantilevers"] = dict(cantilevers)
        S.cfg_set("_fs_saved_Lx_spans", list(Lx_spans))
        S.cfg_set("_fs_saved_Ly_spans", list(Ly_spans))
        S.cfg_set("_fs_saved_cantilevers", dict(cantilevers))
    elif _last_geom_key is not None and _last_geom_key != _geom_key:
        st.session_state["_fs_last_geom_key"]        = _geom_key
        st.session_state["_fs_pending_removals"]     = []
        st.session_state["_fs_pending_voids"]        = []
        st.session_state["_fs_show_confirm"]         = False
        st.session_state["_fs_show_void_confirm"]    = False
        st.session_state["_fs_pending_snapshot"]     = []
        st.session_state["_fs_pending_void_snapshot"] = []

        old_Lx = st.session_state.get("_fs_prev_Lx_spans") or S.cfg_val("_fs_saved_Lx_spans")
        old_Ly = st.session_state.get("_fs_prev_Ly_spans") or S.cfg_val("_fs_saved_Ly_spans")
        old_cant = st.session_state.get("_fs_prev_cantilevers") or S.cfg_val("_fs_saved_cantilevers") or {}

        if old_Lx and old_Ly and (list(old_Lx) != list(Lx_spans) or list(old_Ly) != list(Ly_spans) or old_cant != cantilevers):
            cur_b_list = list(st.session_state.get("fs_drop_beams") or cfg.get("fs_drop_beams") or S.cfg_val("fs_drop_beams", []) or [])
            if cur_b_list:
                remapped_beams = remap_beams_on_span_change(
                    cur_beams=cur_b_list,
                    old_Lx_spans=old_Lx,
                    new_Lx_spans=Lx_spans,
                    old_Ly_spans=old_Ly,
                    new_Ly_spans=Ly_spans,
                    old_cantilevers=old_cant,
                    new_cantilevers=cantilevers,
                )
                cfg["fs_drop_beams"] = remapped_beams
                st.session_state["fs_drop_beams"] = remapped_beams
                S.cfg_set("fs_drop_beams", remapped_beams)
                S.save_settings()

        st.session_state["_fs_prev_Lx_spans"] = list(Lx_spans)
        st.session_state["_fs_prev_Ly_spans"] = list(Ly_spans)
        st.session_state["_fs_prev_cantilevers"] = dict(cantilevers)
        S.cfg_set("_fs_saved_Lx_spans", list(Lx_spans))
        S.cfg_set("_fs_saved_Ly_spans", list(Ly_spans))
        S.cfg_set("_fs_saved_cantilevers", dict(cantilevers))
        try:
            get_flat_slab_columns.clear()
            get_flat_slab_panels.clear()
        except Exception:
            pass
        st.session_state.pop("_fs_active_cols", None)
    else:
        st.session_state["_fs_last_geom_key"] = _geom_key
        st.session_state["_fs_last_active_profile"] = active_profile_name
        st.session_state["_fs_prev_Lx_spans"] = list(Lx_spans)
        st.session_state["_fs_prev_Ly_spans"] = list(Ly_spans)
        st.session_state["_fs_prev_cantilevers"] = dict(cantilevers)
        S.cfg_set("_fs_saved_Lx_spans", list(Lx_spans))
        S.cfg_set("_fs_saved_Ly_spans", list(Ly_spans))
        S.cfg_set("_fs_saved_cantilevers", dict(cantilevers))"""

assert t5 in content, "Target 5 (guard) not found!"
content = content.replace(t5, r5, 1)

with open('modules/flat_slab.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully applied updates to modules/flat_slab.py!")
