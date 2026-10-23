with open('modules/flat_slab.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update DPI in generate_flat_slab_sketch
t_fig = 'fig = plt.figure(figsize=(fig_w, fig_h), dpi=110, facecolor="#ffffff")'
r_fig = 'fig = plt.figure(figsize=(fig_w, fig_h), dpi=100, facecolor="#ffffff")'
assert t_fig in content, "t_fig not found!"
content = content.replace(t_fig, r_fig, 1)

# 2. Update DPI and cache key in _render_fs_interactive_plan
t_render = """    # حفظ الصورة بدون bbox_inches="tight" لضمان التطابق الرياضي التام مع ax_plan.get_position()
    buf_cad = io.BytesIO()
    fig_verif.savefig(buf_cad, format="png", dpi=145)
    buf_cad.seek(0)
    b64_img = base64.b64encode(buf_cad.getvalue()).decode("utf-8")"""

r_render = """    # حفظ الصورة بدون bbox_inches="tight" لضمان التطابق الرياضي التام مع ax_plan.get_position()
    buf_cad = io.BytesIO()
    fig_verif.savefig(buf_cad, format="png", dpi=100)
    buf_cad.seek(0)
    b64_img = base64.b64encode(buf_cad.getvalue()).decode("utf-8")
    st.session_state["_fs_cached_interactive_b64"] = b64_img"""

assert t_render in content, "t_render not found!"
content = content.replace(t_render, r_render, 1)

# 3. Add quick rotate button in Column Modification section
t_edit_box = """                edit_sel_dir = st.selectbox(
                    "ضرب العمود",
                    options=EDIT_DIR_OPTIONS,
                    index=idx_edit_dir,
                    key=f"{prefix}edit_dir_widget_{tgt_orig_id}",
                    help="اتجاه البعد الأكبر للعمود D (موازٍ لمحور X أو لمحور Y).",
                )"""

r_edit_box = """                col_dir_a, col_dir_b = st.columns([2.5, 1.5])
                with col_dir_a:
                    edit_sel_dir = st.selectbox(
                        "ضرب العمود",
                        options=EDIT_DIR_OPTIONS,
                        index=idx_edit_dir,
                        key=f"{prefix}edit_dir_widget_{tgt_orig_id}",
                        help="اتجاه البعد الأكبر للعمود D (موازٍ لمحور X أو لمحور Y).",
                    )
                with col_dir_b:
                    st.markdown("<div style='margin-top: 27px;'></div>", unsafe_allow_html=True)
                    if st.button("🔄 تدوير فوراً", key=f"{prefix}btn_quick_rotate_{tgt_orig_id}", use_container_width=True, help="تدوير ضرب العمود فوراً بين اتجاه X واتجاه Y بنقرة واحدة"):
                        edit_sel_dir = "اتجاه Y" if norm_trans_edit["direction"] == "اتجاه X" else "اتجاه X"
                        st.session_state[f"{prefix}edit_dir_widget_{tgt_orig_id}"] = edit_sel_dir"""

assert t_edit_box in content, "t_edit_box not found!"
content = content.replace(t_edit_box, r_edit_box, 1)

# 4. In-place update without double rerun
t_rerun_blk = """                if trans_changed_e or edge_changed_e:
                    if trans_changed_e:
                        upd_trans_map = dict(col_transforms_curr)
                        new_trans_entry = {
                            "direction": edit_sel_dir,
                            "shift_x": edit_sel_sx,
                            "shift_y": edit_sel_sy,
                        }
                        upd_trans_map[tgt_orig_id] = new_trans_entry
                        upd_trans_map[tgt_ij_str] = dict(new_trans_entry)
                        cfg["fs_col_transforms"] = upd_trans_map

                        col_props_curr = cfg.get("fs_col_props", {})
                        if not isinstance(col_props_curr, dict):
                            col_props_curr = {}
                        for _k_p in (tgt_orig_id, tgt_ij_str):
                            _existing_p = dict(col_props_curr.get(_k_p, {})) if isinstance(col_props_curr.get(_k_p), dict) else {
                                "b_cm": float(tgt_col_obj.get("b_cm", _bc_col)),
                                "t_cm": float(tgt_col_obj.get("t_cm", _tc_col)),
                            }
                            _existing_p["direction"] = edit_sel_dir
                            _existing_p["shift_x"] = edit_sel_sx
                            _existing_p["shift_y"] = edit_sel_sy
                            col_props_curr[_k_p] = _existing_p
                        cfg["fs_col_props"] = col_props_curr

                        st.session_state[f"_fs_dir_widget_{tgt_orig_id}"] = edit_sel_dir
                        st.session_state[f"_fs_sx_widget_{tgt_orig_id}"] = edit_sel_sx
                        st.session_state[f"_fs_sy_widget_{tgt_orig_id}"] = edit_sel_sy

                    if edge_changed_e:
                        upd_edge_map = dict(edge_cols_curr)
                        upd_edge_map[tgt_orig_id] = new_edge_entry
                        cfg["fs_edge_columns"] = upd_edge_map
                        st.session_state[f"_fs_is_edge_widget_{tgt_orig_id}"] = edit_sel_is_edge
                        if has_real_dir_e:
                            st.session_state[f"_fs_edge_dir_widget_{tgt_orig_id}"] = edit_sel_edge_dir

                    S.save_settings()
                    st.rerun()"""

r_rerun_blk = """                if trans_changed_e or edge_changed_e:
                    if trans_changed_e:
                        upd_trans_map = dict(col_transforms_curr)
                        new_trans_entry = {
                            "direction": edit_sel_dir,
                            "shift_x": edit_sel_sx,
                            "shift_y": edit_sel_sy,
                        }
                        upd_trans_map[tgt_orig_id] = new_trans_entry
                        upd_trans_map[tgt_ij_str] = dict(new_trans_entry)
                        cfg["fs_col_transforms"] = upd_trans_map
                        S.cfg_set("fs_col_transforms", upd_trans_map)

                        col_props_curr = cfg.get("fs_col_props", {})
                        if not isinstance(col_props_curr, dict):
                            col_props_curr = {}
                        for _k_p in (tgt_orig_id, tgt_ij_str):
                            _existing_p = dict(col_props_curr.get(_k_p, {})) if isinstance(col_props_curr.get(_k_p), dict) else {
                                "b_cm": float(tgt_col_obj.get("b_cm", _bc_col)),
                                "t_cm": float(tgt_col_obj.get("t_cm", _tc_col)),
                            }
                            _existing_p["direction"] = edit_sel_dir
                            _existing_p["shift_x"] = edit_sel_sx
                            _existing_p["shift_y"] = edit_sel_sy
                            col_props_curr[_k_p] = _existing_p
                        cfg["fs_col_props"] = col_props_curr
                        S.cfg_set("fs_col_props", col_props_curr)

                        st.session_state[f"_fs_dir_widget_{tgt_orig_id}"] = edit_sel_dir
                        st.session_state[f"_fs_sx_widget_{tgt_orig_id}"] = edit_sel_sx
                        st.session_state[f"_fs_sy_widget_{tgt_orig_id}"] = edit_sel_sy

                        # تحديث مباشر ومحلي لمصفوفة التحويلات والأعمدة لتظهر على الرسم فوراً في نفس المسار دون دورة Rerun ثانية
                        _col_transforms[tgt_orig_id] = new_trans_entry
                        _col_transforms[tgt_ij_str] = dict(new_trans_entry)
                        geom = compute_column_geometry(
                            tgt_col_obj.get("grid_x_m", tgt_col_obj.get("x", 0.0)),
                            tgt_col_obj.get("grid_y_m", tgt_col_obj.get("y", 0.0)),
                            float(tgt_col_obj.get("b_cm", _bc_col)),
                            float(tgt_col_obj.get("t_cm", _tc_col)),
                            new_trans_entry,
                        )
                        tgt_col_obj.update(geom)
                        tgt_col_obj["direction"] = edit_sel_dir
                        tgt_col_obj["shift_x"] = edit_sel_sx
                        tgt_col_obj["shift_y"] = edit_sel_sy

                    if edge_changed_e:
                        upd_edge_map = dict(edge_cols_curr)
                        upd_edge_map[tgt_orig_id] = new_edge_entry
                        cfg["fs_edge_columns"] = upd_edge_map
                        S.cfg_set("fs_edge_columns", upd_edge_map)
                        st.session_state[f"_fs_is_edge_widget_{tgt_orig_id}"] = edit_sel_is_edge
                        if has_real_dir_e:
                            st.session_state[f"_fs_edge_dir_widget_{tgt_orig_id}"] = edit_sel_edge_dir
                        _edge_columns[tgt_orig_id] = new_edge_entry

                    try:
                        get_flat_slab_columns.clear()
                    except Exception:
                        pass
                    S.save_settings()"""

assert t_rerun_blk in content, "t_rerun_blk not found!"
content = content.replace(t_rerun_blk, r_rerun_blk, 1)

# 5. Remove redundant savefig at line 14889
t_second_save = """        try:
            import io, base64
            buf_plan = io.BytesIO()
            fig_interactive.savefig(buf_plan, format="png", bbox_inches="tight", dpi=140)
            buf_plan.seek(0)
            plan_b64 = "data:image/png;base64," + base64.b64encode(buf_plan.getvalue()).decode("utf-8")
            st.session_state[f"{prefix}flat_slab_plan_b64"] = plan_b64
            st.session_state["fs_flat_slab_plan_b64"] = plan_b64
            st.session_state["flat_slab_plan_b64"] = plan_b64
        except Exception:
            pass
        plt.close(fig_interactive)"""

r_second_save = """        try:
            cached_interactive_b64 = st.session_state.get("_fs_cached_interactive_b64")
            if cached_interactive_b64:
                plan_b64 = "data:image/png;base64," + cached_interactive_b64
                st.session_state[f"{prefix}flat_slab_plan_b64"] = plan_b64
                st.session_state["fs_flat_slab_plan_b64"] = plan_b64
                st.session_state["flat_slab_plan_b64"] = plan_b64
        except Exception:
            pass
        plt.close(fig_interactive)"""

assert t_second_save in content, "t_second_save not found!"
content = content.replace(t_second_save, r_second_save, 1)

with open('modules/flat_slab.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Optimization successfully applied to modules/flat_slab.py!")
