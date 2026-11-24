
            # ── جسر المزامنة الفورية لتوصيفات البنود والبنود اليدوية (Hidden Sync Bridge) ──
            _cw_sync_aria_lbl = f"{prefix}cw_boq_sync_payload"
            _cw_sync_key = f"{prefix}cw_boq_sync_input"
            st.markdown(
                f"""<style>
                div[data-testid="stTextInput"]:has(input[aria-label="{_cw_sync_aria_lbl}"]) {{
                    position: fixed !important;
                    top: -9999px !important;
                    left: -9999px !important;
                    width: 1px !important;
                    height: 1px !important;
                    opacity: 0 !important;
                    pointer-events: none !important;
                    z-index: -9999 !important;
                }}
                </style>""",
                unsafe_allow_html=True,
            )
            _cw_sync_val = st.text_input(
                _cw_sync_aria_lbl,
                value="",
                key=_cw_sync_key,
                on_change=_on_cw_boq_sync_change,
                args=(_cw_sync_key, prefix),
                label_visibility="collapsed",
            )
            _queued_cw_val = st.session_state.pop(f"{prefix}_cw_queued_sync_payload", None)
            _active_cw_val = _queued_cw_val or _cw_sync_val
            if _active_cw_val:
                try:
                    _cw_payload = json.loads(_active_cw_val) if isinstance(_active_cw_val, str) else _active_cw_val
                    if isinstance(_cw_payload, dict):
                        _act = _cw_payload.get("action")
                        if _act == "update_cw_boq_descriptions":
                            _op_ts = _cw_payload.get("ts")
                            _last_ts = st.session_state.get(f"{prefix}_last_cw_boq_sync_ts")
                            if _op_ts is None or _op_ts != _last_ts:
                                if _op_ts is not None:
                                    st.session_state[f"{prefix}_last_cw_boq_sync_ts"] = _op_ts
                                _new_descs = _cw_payload.get("descriptions")
                                if isinstance(_new_descs, dict):
                                    _cur_d = dict(st.session_state.get(f"{prefix}cw_item_descriptions") or S.cfg_val(f"{prefix}cw_item_descriptions") or S.cfg_val("cw_item_descriptions") or {})
                                    _d_changed = False
                                    for _k_d, _v_d in _new_descs.items():
                                        _ks = str(_k_d)
                                        _vs = str(_v_d).strip()
                                        if _cur_d.get(_ks) != _vs:
                                            _cur_d[_ks] = _vs
                                            _d_changed = True
                                    if _d_changed:
                                        st.session_state[f"{prefix}cw_item_descriptions"] = dict(_cur_d)
                                        S.cfg_set(f"{prefix}cw_item_descriptions", dict(_cur_d))
                                        S.cfg_set("cw_item_descriptions", dict(_cur_d))
                                        S.save_settings()
                                        st.session_state.pop(f"{prefix}_cached_report_html", None)
                                        st.session_state.pop(f"{prefix}_last_concise_pdf_bytes", None)
                        elif _act == "update_manual_boq_items":
                            _upd_items = _cw_payload.get("items")
                            if isinstance(_upd_items, list):
                                _persist_cw_manual_boq_items(_upd_items, prefix=prefix)
                                st.session_state.pop(f"{prefix}_cached_report_html", None)
                                st.session_state.pop(f"{prefix}_last_concise_pdf_bytes", None)
                                st.rerun()
                        elif _act == "delete_manual_boq_item":
                            _del_id = _cw_payload.get("item_id")
                            if _del_id:
                                _m_items = _get_cw_manual_boq_items_list(prefix=prefix)
                                _new_m = [x for x in _m_items if str(x.get("id")) != str(_del_id)]
                                _persist_cw_manual_boq_items(_new_m, prefix=prefix)
                                st.session_state.pop(f"{prefix}_cached_report_html", None)
                                st.session_state.pop(f"{prefix}_last_concise_pdf_bytes", None)
                                st.rerun()
                except Exception:
                    pass
                finally:
                    try:
                        st.session_state[_cw_sync_key] = ""
                    except Exception:
                        pass

            # ═════════════════════════════════════════════════════════════════════════
            #  1. عنوان أسعار البنود وصناديق إدخال الأسعار (برواز سميك عنبري ذهبي مميز)
            # ═════════════════════════════════════════════════════════════════════════
            st.markdown(
                """
                <div dir="rtl" style="text-align: center; margin: 18px auto 14px auto; background: linear-gradient(135deg, rgba(30, 41, 59, 0.90) 0%, rgba(15, 23, 42, 0.96) 100%); border: 1.5px solid rgba(245, 158, 11, 0.5); border-top: 3px solid #f59e0b; border-radius: 8px; padding: 9px 24px; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);">
                    <span style="font-size: 1.45rem; font-weight: 900; color: #fbbf24; text-shadow: 0 2px 6px rgba(0,0,0,0.7); letter-spacing: 0.5px;">
                        💰 أسعار البنود
                    </span>
                </div>
                <style>
                /* برواز سميك بلون عنبري ذهبي مختلف تماماً عن حواف خانات الإدخال السماوية */
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.m1-rates-container-marker),
                div[class*="st-key-m1_rates_container"] {
                    border: 3.5px solid #f59e0b !important;
                    border-radius: 12px !important;
                    background: linear-gradient(180deg, rgba(15, 23, 42, 0.90) 0%, rgba(30, 41, 59, 0.75) 100%) !important;
                    padding: 14px 16px 12px 16px !important;
                    margin-top: 6px !important;
                    margin-bottom: 16px !important;
                    box-shadow: 0 4px 22px rgba(0, 0, 0, 0.50), 0 0 18px rgba(245, 158, 11, 0.30) !important;
                    transition: all 0.25s ease !important;
                }
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.m1-rates-container-marker):hover,
                div[class*="st-key-m1_rates_container"]:hover {
                    border-color: #fbbf24 !important;
                    box-shadow: 0 6px 28px rgba(0, 0, 0, 0.65), 0 0 24px rgba(251, 191, 36, 0.45) !important;
                }
                div[data-testid="stColumn"]:has(div[class*="cw_rate_"]) label p {
                    font-size: 0.80rem !important;
                    font-weight: 700 !important;
                    color: #e2e8f0 !important;
                    white-space: nowrap !important;
                    overflow: hidden !important;
                    text-overflow: ellipsis !important;
                    margin-bottom: 2px !important;
                }
                div[data-testid="stColumn"]:has(div[class*="cw_rate_"]) input {
                    font-size: 0.88rem !important;
                    font-weight: 800 !important;
                    color: #38bdf8 !important;
                    background-color: #0f172a !important;
                    border: 1px solid #334155 !important;
                    border-radius: 6px !important;
                    padding: 3px 5px !important;
                    text-align: center !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            _saved_rate_slabs_beams = float(S.cfg_val(f"{prefix}cw_rate_slabs_beams", S.cfg_val("cw_rate_slabs_beams", 4500.0)))
            _saved_rate_cols = float(S.cfg_val(f"{prefix}cw_rate_cols", S.cfg_val("cw_rate_cols", 4800.0)))
            _saved_rate_ftgs_gb = float(S.cfg_val(f"{prefix}cw_rate_ftgs_gb", S.cfg_val("cw_rate_ftgs_gb", 4400.0)))
            _saved_rate_pc = float(S.cfg_val(f"{prefix}cw_rate_pc", S.cfg_val("cw_rate_pc", 2200.0)))
            _saved_rate_backfill = float(S.cfg_val(f"{prefix}cw_rate_backfill", S.cfg_val("cw_rate_backfill", 120.0)))
            _saved_rate_bricks = float(S.cfg_val(f"{prefix}cw_rate_bricks", S.cfg_val("cw_rate_bricks", 2.5)))
            _saved_rate_interlock = float(S.cfg_val(f"{prefix}cw_rate_interlock", S.cfg_val("cw_rate_interlock", 220.0)))
            _saved_rate_curbs = float(S.cfg_val(f"{prefix}cw_rate_curbs", S.cfg_val("cw_rate_curbs", 160.0)))
            _saved_rate_damp_proof = float(S.cfg_val(f"{prefix}cw_rate_damp_proof", S.cfg_val("cw_rate_damp_proof", 95.0)))
            _saved_rate_waterproof = float(S.cfg_val(f"{prefix}cw_rate_waterproof", S.cfg_val("cw_rate_waterproof", 170.0)))
            _saved_rate_thermal = float(S.cfg_val(f"{prefix}cw_rate_thermal", S.cfg_val("cw_rate_thermal", 130.0)))
            _saved_rate_roof_tiles = float(S.cfg_val(f"{prefix}cw_rate_roof_tiles", S.cfg_val("cw_rate_roof_tiles", 150.0)))

            with st.container(border=True):
                st.markdown('<div class="m1-rates-container-marker" style="display:none;"></div>', unsafe_allow_html=True)
                cw_pr1_c1, cw_pr1_c2, cw_pr1_c3, cw_pr1_c4 = st.columns(4)
                with cw_pr1_c1:
                    price_cw_slabs_beams = st.number_input(
                        "(م3) خرسانة مسلحة سقف وكمرات:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_slabs_beams,
                        step=50.0, format="%.1f",
                        key=f"{prefix}cw_rate_slabs_beams",
                        help="سعر المتر المكعب لخرسانة السقف والكمرات المسلحة شامل الحديد والشدة والصب",
                    )
                with cw_pr1_c2:
                    price_cw_cols = st.number_input(
                        "(م3) خرسانة مسلحة أعمدة:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_cols,
                        step=50.0, format="%.1f",
                        key=f"{prefix}cw_rate_cols",
                        help="سعر المتر المكعب للخرسانة المسلحة لأعمدة المبنى",
                    )
                with cw_pr1_c3:
                    price_cw_ftgs_gb = st.number_input(
                        "(م3) خرسانة مسلحة قواعد وسملات:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_ftgs_gb,
                        step=50.0, format="%.1f",
                        key=f"{prefix}cw_rate_ftgs_gb",
                        help="سعر المتر المكعب للخرسانة المسلحة للقواعد والسملات والشدادات والقواعد المشتركة",
                    )
                with cw_pr1_c4:
                    price_cw_pc = st.number_input(
                        "(م3) خرسانة عادية وأرضيات:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_pc,
                        step=50.0, format="%.1f",
                        key=f"{prefix}cw_rate_pc",
                        help="سعر المتر المكعب للخرسانة العادية أسفل القواعد والسملات ودكة الأرضيات",
                    )

                cw_pr2_c1, cw_pr2_c2, cw_pr2_c3, cw_pr2_c4 = st.columns(4)
                with cw_pr2_c1:
                    price_cw_backfill = st.number_input(
                        "(م3) أعمال الردم:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_backfill,
                        step=5.0, format="%.1f",
                        key=f"{prefix}cw_rate_backfill",
                        help="سعر المتر المكعب لأعمال الردم بالرمل النظيف والدمك أسفل وأعلى سطح الأرض",
                    )
                with cw_pr2_c2:
                    price_cw_bricks = st.number_input(
                        "(طوبة) الطوب الأسمنتي:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_bricks,
                        step=0.25, format="%.2f",
                        key=f"{prefix}cw_rate_bricks",
                        help="سعر الطوبة الأسمنتية الواحدة شاملة التوريد والمونة والبناء (مثلاً 2.50 ج.م أي 2500 ج.م للألف طوبة)",
                    )
                with cw_pr2_c3:
                    price_cw_interlock = st.number_input(
                        "(م2) الانترلوك:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_interlock,
                        step=5.0, format="%.1f",
                        key=f"{prefix}cw_rate_interlock",
                        help="سعر المتر المسطح لبلاط انترلوك الأرصفة الخارجية",
                    )
                with cw_pr2_c4:
                    price_cw_curbs = st.number_input(
                        "(م.ط) البردورات:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_curbs,
                        step=5.0, format="%.1f",
                        key=f"{prefix}cw_rate_curbs",
                        help="سعر المتر الطولي لبردورات الأرصفة الخارجية",
                    )

                cw_pr3_c1, cw_pr3_c2, cw_pr3_c3, cw_pr3_c4 = st.columns(4)
                with cw_pr3_c1:
                    price_cw_damp_proof = st.number_input(
                        "(م2) عزل الرطوبة للأساسات:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_damp_proof,
                        step=5.0, format="%.1f",
                        key=f"{prefix}cw_rate_damp_proof",
                        help="سعر المتر المسطح لعزل الرطوبة البيتوميني للقواعد المسلحة والسملات",
                    )
                with cw_pr3_c2:
                    price_cw_waterproof = st.number_input(
                        "(م2) عازل مائي (انسومات):",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_waterproof,
                        step=5.0, format="%.1f",
                        key=f"{prefix}cw_rate_waterproof",
                        help="سعر المتر المسطح للعزل المائي للأسطح بمادة الأنسومات",
                    )
                with cw_pr3_c3:
                    price_cw_thermal = st.number_input(
                        "(م2) عازل حراري للسطح:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_thermal,
                        step=5.0, format="%.1f",
                        key=f"{prefix}cw_rate_thermal",
                        help="سعر المتر المسطح للعزل الحراري للأسطح",
                    )
                with cw_pr3_c4:
                    price_cw_roof_tiles = st.number_input(
                        "(م2) بلاط اسطح:",
                        min_value=0.0, max_value=100000.0,
                        value=_saved_rate_roof_tiles,
                        step=5.0, format="%.1f",
                        key=f"{prefix}cw_rate_roof_tiles",
                        help="سعر المتر المسطح لبلاط أسطح المبنى",
                    )

            if (
                abs(price_cw_slabs_beams - _saved_rate_slabs_beams) > 1e-4
                or abs(price_cw_cols - _saved_rate_cols) > 1e-4
                or abs(price_cw_ftgs_gb - _saved_rate_ftgs_gb) > 1e-4
                or abs(price_cw_pc - _saved_rate_pc) > 1e-4
                or abs(price_cw_backfill - _saved_rate_backfill) > 1e-4
                or abs(price_cw_bricks - _saved_rate_bricks) > 1e-4
                or abs(price_cw_interlock - _saved_rate_interlock) > 1e-4
                or abs(price_cw_curbs - _saved_rate_curbs) > 1e-4
                or abs(price_cw_damp_proof - _saved_rate_damp_proof) > 1e-4
                or abs(price_cw_waterproof - _saved_rate_waterproof) > 1e-4
                or abs(price_cw_thermal - _saved_rate_thermal) > 1e-4
                or abs(price_cw_roof_tiles - _saved_rate_roof_tiles) > 1e-4
            ):
                S.cfg_set(f"{prefix}cw_rate_slabs_beams", price_cw_slabs_beams)
                S.cfg_set("cw_rate_slabs_beams", price_cw_slabs_beams)
                S.cfg_set(f"{prefix}cw_rate_cols", price_cw_cols)
                S.cfg_set("cw_rate_cols", price_cw_cols)
                S.cfg_set(f"{prefix}cw_rate_ftgs_gb", price_cw_ftgs_gb)
                S.cfg_set("cw_rate_ftgs_gb", price_cw_ftgs_gb)
                S.cfg_set(f"{prefix}cw_rate_pc", price_cw_pc)
                S.cfg_set("cw_rate_pc", price_cw_pc)
                S.cfg_set(f"{prefix}cw_rate_backfill", price_cw_backfill)
                S.cfg_set("cw_rate_backfill", price_cw_backfill)
                S.cfg_set(f"{prefix}cw_rate_bricks", price_cw_bricks)
                S.cfg_set("cw_rate_bricks", price_cw_bricks)
                S.cfg_set(f"{prefix}cw_rate_interlock", price_cw_interlock)
                S.cfg_set("cw_rate_interlock", price_cw_interlock)
                S.cfg_set(f"{prefix}cw_rate_curbs", price_cw_curbs)
                S.cfg_set("cw_rate_curbs", price_cw_curbs)
                S.cfg_set(f"{prefix}cw_rate_damp_proof", price_cw_damp_proof)
                S.cfg_set("cw_rate_damp_proof", price_cw_damp_proof)
                S.cfg_set(f"{prefix}cw_rate_waterproof", price_cw_waterproof)
                S.cfg_set("cw_rate_waterproof", price_cw_waterproof)
                S.cfg_set(f"{prefix}cw_rate_thermal", price_cw_thermal)
                S.cfg_set("cw_rate_thermal", price_cw_thermal)
                S.cfg_set(f"{prefix}cw_rate_roof_tiles", price_cw_roof_tiles)
                S.cfg_set("cw_rate_roof_tiles", price_cw_roof_tiles)
                S.save_settings()
                st.session_state.pop(f"{prefix}_cached_report_html", None)
                st.session_state.pop(f"{prefix}_last_concise_pdf_bytes", None)

            # معامل زيادة للكميات التي تم حسابها
            _qf_key = f"{prefix}w_cw_qty_factor"
            _saved_qty_factor = float(S.cfg_val(f"{prefix}cw_qty_factor", S.cfg_val("cw_qty_factor", 1.20)))

            def _sync_cw_qty_factor():
                _v_qf = float(st.session_state.get(_qf_key, 1.20))
                S.cfg_set(f"{prefix}cw_qty_factor", _v_qf)
                S.cfg_set("cw_qty_factor", _v_qf)
                S.save_settings()
                st.session_state.pop(f"{prefix}_cached_report_html", None)
                st.session_state.pop(f"{prefix}_last_concise_pdf_bytes", None)

            if _qf_key not in st.session_state:
                st.session_state[_qf_key] = _saved_qty_factor
            else:
                _saved_qty_factor = float(st.session_state[_qf_key])

            c_cw_factor_lbl, c_cw_factor_inp = st.columns([1, 1], gap="small")
            with c_cw_factor_lbl:
                st.markdown(
                    """<div dir="rtl" style="display: flex; align-items: center; justify-content: center; height: 100%; font-size: 1.08rem; font-weight: 900; color: #ffffff; text-shadow: 0 1px 3px rgba(0,0,0,0.9), 0 0 16px rgba(192,132,252,0.7); white-space: nowrap; line-height: 1.2; margin: 0; padding: 0;">
                        ✨ معامل زيادة للكميات التي تم حسابها:
                    </div>""",
                    unsafe_allow_html=True,
                )
            with c_cw_factor_inp:
                cw_qty_factor = st.number_input(
                    "",
                    min_value=0.10, max_value=5.00,
                    value=_saved_qty_factor,
                    step=0.05, format="%.2f",
                    key=_qf_key,
                    on_change=_sync_cw_qty_factor,
                    label_visibility="collapsed",
                )
            if abs(cw_qty_factor - float(S.cfg_val(f"{prefix}cw_qty_factor", S.cfg_val("cw_qty_factor", 1.20)))) > 1e-4:
                S.cfg_set(f"{prefix}cw_qty_factor", cw_qty_factor)
                S.cfg_set("cw_qty_factor", cw_qty_factor)
                S.save_settings()
                st.session_state.pop(f"{prefix}_cached_report_html", None)
                st.session_state.pop(f"{prefix}_last_concise_pdf_bytes", None)

            # ═════════════════════════════════════════════════════════════════════════
            #  2. إدارة وتخصيص مكتبة القوالب الجاهزة (12 قالب متاح لجميع المشاريع)
            # ═════════════════════════════════════════════════════════════════════════
            _cw_presets = _get_cw_manual_boq_presets_list()
            with st.expander(
                f"⚙️ 📚 إدارة وتخصيص مكتبة القوالب الجاهزة ({len(_cw_presets)} قالب متاح لجميع المشاريع)",
                expanded=False,
            ):
                _render_cw_presets_library_manager(_cw_presets, prefix=prefix)

            # ═════════════════════════════════════════════════════════════════════════
            #  3. إضافة وإدارة بنود الحصر اليدوية الإضافية (رخام سلالم، حجر فرعوني، وبنود أخرى)
            # ═════════════════════════════════════════════════════════════════════════
            with st.expander(
                "➕ إضافة وإدارة بنود الحصر اليدوية الإضافية (رخام سلالم، حجر فرعوني، وبنود أخرى)",
                expanded=False,
            ):
                _render_cw_manual_boq_items_manager(cur_factor=cw_qty_factor, prefix=prefix)

            # ── دمج البنود الأساسية الـ 12 مع البنود اليدوية المضافة ──
            _sum_slabs_beams_net = round(_v_slabs_conc + _v_beams_conc, 2)
            _sum_cols_net = round(_v_cols_conc, 2)
            _sum_ftgs_gb_only_net = round(_v_ftgs_rc + _v_gb_conc, 2)
            _sum_ftgs_gb_with_floor_tot = round((_v_ftgs_rc + _v_gb_conc + _v_rc_floor) * cw_qty_factor, 2)
            _sum_pc_net = round(_v_pc_ftg_floor + _v_pc_gb + _v_rc_floor, 2)
            _sum_pc_only_net = round(_v_pc_ftg_floor + _v_pc_gb, 2)
            _sum_backfill_net = round(_v_backfill_sub + _v_backfill_above, 2)
            _sum_bricks_net = _n_bricks_total
            _sum_bricks_tot = int(math.ceil(_sum_bricks_net * cw_qty_factor))
            _sum_masonry_m3_tot = round(_v_masonry_m3 * cw_qty_factor, 2)
            _sum_interlock_net = round(_area_interlock_m2, 2)
            _sum_curb_net = round(_len_curb_m, 2)
            _sum_damp_proof_net = round(_area_damp_proof_m2, 2)
            _sum_waterproof_net = round(_area_waterproof_m2, 2)
            _sum_thermal_ins_net = round(_area_thermal_ins_m2, 2)
            _sum_roof_tiles_net = round(_area_roof_tiles_m2, 2)

            base_cw_items_data = [
                ("1- اجمالي خرسانه مسلحة للسقف والكمرات (سقف + كمرات)",
                 _sum_slabs_beams_net, "م³ (m³)", price_cw_slabs_beams,
                 f"(سقف {_v_slabs_conc:.2f} m³ + كمرات {_v_beams_conc:.2f} m³) × {cw_qty_factor:.2f}"),

                ("2- اجمالي خرسانة مسلحة الاعمدة",
                 _sum_cols_net, "م³ (m³)", price_cw_cols,
                 f"إجمالي خرسانة أعمدة المبنى ({_v_cols_conc:.2f} m³) × {cw_qty_factor:.2f}"),

                ("3- اجمالي خرسانة مسحة للقواعد والسملات (قواعد + سملات + شدادات + قواعد مشتركة)",
                 _sum_ftgs_gb_only_net, "م³ (m³)", price_cw_ftgs_gb,
                 f"(قواعد وشدادات وقواعد مشتركة {_v_ftgs_rc:.2f} m³ + سملات {_v_gb_conc:.2f} m³) × {cw_qty_factor:.2f} │ (وشامل بلاطة الأرضية المسلحة = {_sum_ftgs_gb_with_floor_tot:.2f} m³)"),

                ("4- اجمالي الخرسانة العادية (اسفل القواعد المسلحة + اسفل السملات + اسفل بلاطة الارضية السلحة) واي خرسانة عادية اخري",
                 _sum_pc_net, "م³ (m³)", price_cw_pc,
                 f"(عادية أسفل القواعد المسلحة {_v_pc_ftg_floor:.2f} m³ + عادية أسفل السملات {_v_pc_gb:.2f} m³ + بلاطة الأرضية {_v_rc_floor:.2f} m³) × {cw_qty_factor:.2f} │ (والعادية أسفل القواعد والسملات فقط = {_sum_pc_only_net * cw_qty_factor:.2f} m³)"),

                ("5- اجمالي الردم (ردم فوق سطح الارض + ردم اسفل سطح الارض)",
                 _sum_backfill_net, "م³ (m³)", price_cw_backfill,
                 f"(ردم أسفل سطح الأرض {_v_backfill_sub:.2f} m³ + ردم أعلى سطح الأرض {_v_backfill_above:.2f} m³) × {cw_qty_factor:.2f}"),

                ("6- اجمالي الطوب",
                 _sum_bricks_net, "طوبة (Brick)", price_cw_bricks,
                 f"{_sum_bricks_tot / 1000.0:.2f} ألف طوبة │ حجم المباني الإجمالي بالمعامل = {_sum_masonry_m3_tot:.2f} m³"),

                ("7- اجمالي الانترلوك",
                 _sum_interlock_net, "م² (m²)", price_cw_interlock,
                 f"مساحة انترلوك الأرصفة ({_area_interlock_m2:.2f} m²) × {cw_qty_factor:.2f}"),

                ("8- اجمالي البردورات",
                 _sum_curb_net, "م.ط (m)", price_cw_curbs,
                 f"إجمالي طول البردورات للمحيط الخارجي للانترلوك ({_len_curb_m:.2f} m) × {cw_qty_factor:.2f}"),

                ("9- اجمالي عزل الرطوبة للقواعد المسلحة للسملات والقواعد المسلحة",
                 _sum_damp_proof_net, "م² (m²)", price_cw_damp_proof,
                 f"(جوانب القواعد {_ftg_sides_area_m2:.2f} m² + السطح العلوي للقواعد {_ftg_top_area_m2:.2f} m² + جوانب السملات {_gb_sides_area_m2:.2f} m²) × {cw_qty_factor:.2f}"),

                ("10- اجمالي بند العزل المائي للسطح (انسومات)",
                 _sum_waterproof_net, "م² (m²)", price_cw_waterproof,
                 f"مسطح المبنى ({_bldg_footprint_m2:.2f} m²) × {cw_qty_factor:.2f}"),

                ("11- اجمالي عازل حراري",
                 _sum_thermal_ins_net, "م² (m²)", price_cw_thermal,
                 f"مسطح المبنى ({_bldg_footprint_m2:.2f} m²) × {cw_qty_factor:.2f}"),

                ("12- اجمالي بلاط اسطح",
                 _sum_roof_tiles_net, "م² (m²)", price_cw_roof_tiles,
                 f"مسطح المبنى ({_bldg_footprint_m2:.2f} m²) × {cw_qty_factor:.2f}"),
            ]

            _cw_manual_tuples = _get_cw_manual_boq_t2_tuples(cw_qty_factor=cw_qty_factor, start_idx=13, prefix=prefix)
            cw_items_data = base_cw_items_data + _cw_manual_tuples

            DEFAULT_CW_ITEM_DESCRIPTIONS = {
                "item_1": "بالمتر المكعب، توريد وصب خرسانة مسلحة للأسقف والكمرات (بلاطات لاكمرية Flat Slab وكمرات ساقطة/مدفونة) بمحتوى أسمنتي لا يقل عن 350 كجم أسمنت بورتلاندي عادي/م³ خرسانة ومقاومة مميزة طبقاً للتصميم الإنشائي، والسعر يشمل الشدات الخشبية أو المعدنية وحديد التسليح والفرم والصب والدمك الميكانيكي والمعالجة بالمياه طبقاً للكود المصري ECP 203.",
                "item_2": "بالمتر المكعب، توريد وصب خرسانة مسلحة للأعمدة الإنشائية لكافة أدوار المبنى بمحتوى أسمنتي لا يقل عن 350-400 كجم/م³ ومقاومة مميزة طبقاً للتصميم، والسعر يشمل أعمال النجارة والتقويات والشدات وحديد التسليح الطولي والكانات والصب والدمك والمعالجة طبقاً لاشتراطات الكود المصري ECP 203.",
                "item_3": "بالمتر المكعب، توريد وصب خرسانة مسلحة للأساسات (قواعد منفصلة + قواعد مشتركة + شدادات + سملات وميد أرضية) باستخدام أسمنت مقاوم للكبريتات (أو حسب تقرير التربة) بمحتوى لا يقل عن 350 كجم/م³، شاملاً الشدات وحديد التسليح والصب والدمك والمعالجة طبقاً للكود المصري ECP 203.",
                "item_4": "بالمتر المكعب، توريد وصب خرسانة عادية للفرشات أسفل القواعد المسلحة وأسفل السملات ودكة الأرضيات بمحتوى أسمنتي 250 كجم أسمنت/م³ خرسانة، والسعر يشمل النظافة وضبط المناسيب والفرم والصب والدمك والتسوية والمعالجة بالمياه طبقاً للمواصفات الفنية والكود المصري.",
                "item_5": "بالمتر المكعب، توريد وردم برمل نظيف خالٍ من الشوائب والأملاح والطفلة حول الأساسات أسفل سطح الأرض وداخل أحواض الردم أعلى سطح الأرض حتى منسوب دكة الأرضية، على طبقات لا يتجاوز سمك الطبقة 25 سم مع الرش الغزير بالمياه والدمك الميكانيكي الجيد للوصول لأقصى كثافة جافة طبقاً لأصول الصناعة.",
                "item_6": "بالعدد (طوبة)، توريد وبناء طوب أسمنتي مصمت لمباني قصية الردم والأساسات أعلى السملات حتى منسوب الردم بالمونة الأسمنتية بنسبة لا تقل عن 350 كجم أسمنت/م³ رمل، شاملاً التشحيط وضبط الرأسية والأفقية وتفريغ اللحامات والمعالجة بالمياه طبقاً للمواصفات الفنية والكود المصري.",
                "item_7": "بالمتر المسطح، توريد وتركيب بلاط انترلوك خرساني متداخل للأرصفة الخارجية حول محيط المبنى سمك 6-8 سم على فرشة رمل نظيف مدكوك مع الدك الهزاز الميكانيكي وملء الفواصل بالرمل الناعم وضبط المناسيب والميول السطحية طبقاً لأصول الصناعة.",
                "item_8": "بالمتر الطولي، توريد وتركيب بردورات خرسانية جاهزة للأرصفة الخارجية حول داير الانترلوك شاملة الحفر والفرشة الخرسانية العادية أسفلها والتثبيت والسنادة الخلفية بالخرسانة وتكحيل اللحامات بمونة الأسمنت والرمل طبقاً للمواصفات.",
                "item_9": "بالمتر المسطح، توريد ودهان عزل رطوبة بيتوميني (وجهين أو ثلاثة أوجه متعامدة من البيتومين المؤكسد الساخن أو المستحلب البيتوميني المطاطي البارد) لجميع جوانب وأسطح القواعد المسلحة وجوانب السملات ومباني قصية الردم الملامسة للتربة بعد النظافة التامة طبقاً لأصول الصناعة.",
                "item_10": "بالمتر المسطح، توريد وتنفيذ طبقة عزل مائي للسطح النهائي باستخدام لفائف البيتومين المعدل المسلح بالبوليستر (أنسومات سمك 4 مم) تركب باللهب فوق وجه برايمر بيتوميني مع عمل ركوب لا يقل عن 10 سم ورفع العزل على الدروة وعمل رقبة القزازة والاختبار بالغمر بالمياه لمدة 48 ساعة.",
                "item_11": "بالمتر المسطح، توريد وتركيب ألواح عزل حراري للسطح من البوليستيرين المبثوق عالي الكثافة (Extruded Polystyrene - XPS / فوم أزرق) سمك 5 سم عاشق ومعشوق يرص فوق طبقة العزل المائي وحمايته بطبقة مشمع بولي إيثيلين قبل عمل خرسانة الميول والبلاط.",
                "item_12": "بالمتر المسطح، توريد وتركيب بلاط أسطح (بلاط موزايكو / سنجابي / أسمنتي مقاس 20×20×2 سم) فوق فرشة الرمل والمونة الأسمنتية مع ضبط أوتار الميول نحو جرجوري صرف الأمطار وعمل الوزرات المائلة والسقية بلباني الأسمنت وفواصل التمدد المملوءة بالبيتومين.",
            }

            # إضافة توصيفات البنود اليدوية للقائمة الافتراضية
            _cur_manual_items_list = _get_cw_manual_boq_items_list(prefix=prefix)
            for _m_idx, _m_item in enumerate(_cur_manual_items_list, start=13):
                _k = f"item_{_m_idx}"
                DEFAULT_CW_ITEM_DESCRIPTIONS[_k] = str(_m_item.get("description", "")).strip() or "توريد وتركيب وتنفيذ البند طبقاً للمواصفات الفنية وأصول الصناعة المعتمدة واشتراطات المهندس المشرف."

            cw_grand_total_cost = 0.0
            for _name, _net_q, _unit, _u_price, _details in cw_items_data:
                _tot_q = round(_net_q * cw_qty_factor, 2)
                _tot_cost = round(_tot_q * _u_price, 2)
                cw_grand_total_cost += _tot_cost

            # ── إعداد جدول ملخص الكميات وتوصيفات البنود التفاعلي المدمج (تنسيق 1.1x المدمج من موديول 15) ──
            _cur_cw_desc_dict = dict(st.session_state.get(f"{prefix}cw_item_descriptions", {}) or {})
            if not _cur_cw_desc_dict:
                _cur_cw_desc_dict = dict(S.cfg_val(f"{prefix}cw_item_descriptions", S.cfg_val("cw_item_descriptions", {})) or {})

            cw_live_descriptions = {}
            cw_boq_table_rows_data = []
            import re as _re_mod
            import html as _html_mod

            for _idx, (_name, _net_q, _unit, _u_price, _details) in enumerate(cw_items_data, start=1):
                _c_key = f"item_{_idx}"
                _tot_q = round(_net_q * cw_qty_factor, 2)
                _tot_cost = round(_tot_q * _u_price, 2)
                if _c_key in _cur_cw_desc_dict and _cur_cw_desc_dict[_c_key] is not None:
                    _saved_d = str(_cur_cw_desc_dict[_c_key]).strip()
                elif _name in _cur_cw_desc_dict and _cur_cw_desc_dict[_name] is not None:
                    _saved_d = str(_cur_cw_desc_dict[_name]).strip()
                else:
                    _saved_d = str(DEFAULT_CW_ITEM_DESCRIPTIONS.get(_c_key, "")).strip()
                cw_live_descriptions[_c_key] = _saved_d

                _clean_name = _re_mod.sub(r'^\d+\s*[-–.]\s*', '', str(_name)).strip()

                cw_boq_table_rows_data.append({
                    "code": _c_key,
                    "seq": str(_idx),
                    "clean_name": _clean_name,
                    "unit": str(_unit),
                    "tot_qty": f"{_tot_q:,.2f}",
                    "unit_price": f"{_u_price:,.2f}",
                    "tot_cost": f"{_tot_cost:,.2f}",
                    "desc": _saved_d,
                    "is_total": False,
                })

            if "total_cost" in _cur_cw_desc_dict and _cur_cw_desc_dict["total_cost"] is not None:
                _saved_cw_total_d = str(_cur_cw_desc_dict["total_cost"]).strip()
            else:
                _saved_cw_total_d = "إجمالي تكلفة جميع بنود الخرسانات المسلحة والعادية والردم والمباني والأرصفة والعزل شامل معامل الزيادة"
            cw_live_descriptions["total_cost"] = _saved_cw_total_d
            cw_boq_table_rows_data.append({
                "code": "total_cost",
                "seq": "💰",
                "clean_name": "إجمالي التكلفة (Total Cost)",
                "unit": "ج.م (EGP)",
                "tot_qty": "—",
                "unit_price": "—",
                "tot_cost": f"{cw_grand_total_cost:,.2f}",
                "desc": _saved_cw_total_d,
                "is_total": True,
            })

            if st.session_state.get(f"{prefix}cw_item_descriptions") != cw_live_descriptions:
                st.session_state[f"{prefix}cw_item_descriptions"] = dict(cw_live_descriptions)
                S.cfg_set(f"{prefix}cw_item_descriptions", dict(cw_live_descriptions))
                S.cfg_set("cw_item_descriptions", dict(cw_live_descriptions))

            _cw_tbody_rows_html = []
            for _r_idx, _r_info in enumerate(cw_boq_table_rows_data):
                _code_esc = _html_mod.escape(_r_info["code"])
                _seq_esc = _html_mod.escape(_r_info["seq"])
                _name_esc = _html_mod.escape(_r_info["clean_name"])
                _unit_esc = _html_mod.escape(_r_info["unit"])
                _qty_esc = _html_mod.escape(_r_info["tot_qty"])
                _uprice_esc = _html_mod.escape(_r_info["unit_price"])
                _tcost_esc = _html_mod.escape(_r_info["tot_cost"])
                _desc_esc = _html_mod.escape(_r_info["desc"])
                _is_tot = _r_info["is_total"]

                if _is_tot:
                    _cw_tbody_rows_html.append(f"""
                    <tr class="boq-row boq-total-row" id="boq-tr-total" data-row-idx="{_r_idx}">
                        <td class="boq-td cell-summary" id="cell-0-{_r_idx}">
                            <div class="summary-item-wrap">
                                <span class="seq-badge">{_seq_esc}</span>
                                <span class="item-name-txt" style="color: #10b981; font-weight: 900;">{_name_esc}</span>
                            </div>
                            <div class="row-resizer" data-row="{_r_idx}" title="اسحب بالماوس لتغيير ارتفاع الصف"></div>
                        </td>
                        <td class="boq-td cell-unit" id="cell-1-{_r_idx}">
                            <div class="cell-center-wrap" style="color: #6ee7b7; font-weight: 900;">{_unit_esc}</div>
                        </td>
                        <td class="boq-td cell-qty" id="cell-2-{_r_idx}">
                            <div class="cell-center-wrap" style="color: #6ee7b7; font-weight: 900;">—</div>
                        </td>
                        <td class="boq-td cell-uprice" id="cell-3-{_r_idx}">
                            <div class="cell-center-wrap" style="color: #6ee7b7; font-weight: 900;">—</div>
                        </td>
                        <td class="boq-td cell-tcost" id="cell-4-{_r_idx}">
                            <div class="cell-center-wrap" style="color: #34d399; font-weight: 900; font-size: 0.73rem;">{_tcost_esc}</div>
                        </td>
                        <td class="boq-td cell-desc" id="cell-5-{_r_idx}">
                            <div class="desc-editor" contenteditable="true" data-item-code="{_code_esc}" id="desc-edit-{_code_esc}" style="color: #e2e8f0; font-weight: 700;">{_desc_esc}</div>
                        </td>
                    </tr>
                    """)
                else:
                    _row_cls = "boq-even-row" if (_r_idx % 2 == 0) else "boq-odd-row"
                    _cw_tbody_rows_html.append(f"""
                    <tr class="boq-row {_row_cls}" id="boq-tr-{_r_idx}" data-row-idx="{_r_idx}">
                        <td class="boq-td cell-summary" id="cell-0-{_r_idx}">
                            <div class="summary-item-wrap">
                                <span class="seq-badge">{_seq_esc}.</span>
                                <span class="item-name-txt">{_name_esc}</span>
                            </div>
                            <div class="row-resizer" data-row="{_r_idx}" title="اسحب بالماوس لتغيير ارتفاع الصف"></div>
                        </td>
                        <td class="boq-td cell-unit" id="cell-1-{_r_idx}">
                            <div class="cell-center-wrap">{_unit_esc}</div>
                        </td>
                        <td class="boq-td cell-qty" id="cell-2-{_r_idx}">
                            <div class="cell-center-wrap">{_qty_esc}</div>
                        </td>
                        <td class="boq-td cell-uprice" id="cell-3-{_r_idx}">
                            <div class="cell-center-wrap">{_uprice_esc}</div>
                        </td>
                        <td class="boq-td cell-tcost" id="cell-4-{_r_idx}">
                            <div class="cell-center-wrap">{_tcost_esc}</div>
                        </td>
                        <td class="boq-td cell-desc" id="cell-5-{_r_idx}">
                            <div class="desc-editor" contenteditable="true" data-item-code="{_code_esc}" id="desc-edit-{_code_esc}">{_desc_esc}</div>
                        </td>
                    </tr>
                    """)

            _initial_cw_descs_json = json.dumps(cw_live_descriptions, ensure_ascii=False)
            _cw_tbody_combined = "".join(_cw_tbody_rows_html)

            # حقن الجدول التفاعلي الكامل مع دعم الـ BiDi ومقاسات الخطوط 1.1x
            _cw_full_table_html = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}
  html, body {{
    width: 100%;
    margin: 0;
    padding: 0;
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Kufi Arabic", sans-serif;
    direction: rtl;
    color: #e2e8f0;
    overflow-x: hidden !important;
  }}
  body.is-resizing-col {{
    cursor: col-resize !important;
    user-select: none !important;
  }}
  body.is-resizing-row {{
    cursor: row-resize !important;
    user-select: none !important;
  }}

  .boq-root-container {{
    width: 100% !important;
    max-width: 100% !important;
    padding: 4px 2px 14px 2px;
    box-sizing: border-box;
    overflow-x: hidden !important;
  }}

  /* ── شريط الأدوات العلوي المدمج ── */
  .boq-top-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);
    border: 1.5px solid rgba(56, 189, 248, 0.50);
    border-radius: 8px;
    padding: 6px 12px;
    margin-bottom: 8px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
  }}
  .boq-top-title {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    font-weight: 900;
    color: #38bdf8;
    text-shadow: 0 1px 3px rgba(0,0,0,0.8);
  }}
  .boq-controls-group {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .boq-btn {{
    background: rgba(15, 23, 42, 0.85);
    color: #e2e8f0;
    border: 1px solid rgba(148, 163, 184, 0.4);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.65rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    user-select: none;
  }}
  .boq-btn:hover {{
    background: rgba(56, 189, 248, 0.20);
    border-color: #38bdf8;
    color: #ffffff;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
  }}
  .boq-save-badge {{
    display: none;
    align-items: center;
    gap: 4px;
    background: rgba(16, 185, 129, 0.25);
    color: #34d399;
    border: 1px solid #10b981;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 0.62rem;
    font-weight: 800;
    animation: fadeInOut 2.5s ease forwards;
  }}

  /* ── جدول المقايسة الكامل ── */
  .boq-table-wrapper {{
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
    border: 2px solid rgba(56, 189, 248, 0.50);
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.50);
    background: #0f172a;
    box-sizing: border-box;
  }}

  table#m1-cw-boq-table {{
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    table-layout: fixed;
    border-collapse: collapse;
    border-spacing: 0;
    direction: rtl;
    background: #0f172a;
  }}

  /* ── عناوين الجدول (برتقالي وأزرق) ── */
  thead.boq-thead tr.boq-header-row {{
    height: 38px;
  }}
  th.boq-th {{
    position: relative;
    padding: 4px 2px;
    vertical-align: middle;
    text-align: center;
    border-bottom: 2px solid #ea580c;
    user-select: none;
    overflow: visible;
  }}
  th.boq-th-orange {{
    background: linear-gradient(180deg, rgba(234, 88, 12, 0.42) 0%, rgba(194, 65, 12, 0.26) 100%);
    border-left: 1.5px solid rgba(251, 146, 60, 0.50);
  }}
  th.boq-th-orange .th-main-title {{
    display: block;
    font-size: 0.68rem;
    font-weight: 900;
    color: #fb923c;
    text-shadow: 0 0 8px rgba(251, 146, 60, 0.75), 0 1px 2px #000000;
    line-height: 1.25;
  }}
  th.boq-th-orange .th-sub-title {{
    display: block;
    font-size: 0.56rem;
    font-weight: 800;
    color: #fed7aa;
    margin-top: 1px;
    line-height: 1.15;
  }}
  th.boq-th-blue {{
    background: linear-gradient(180deg, rgba(2, 132, 199, 0.48) 0%, rgba(14, 165, 233, 0.26) 100%);
    border-left: none;
    border-bottom: 2px solid #38bdf8;
  }}
  th.boq-th-blue .th-main-title {{
    display: block;
    font-size: 0.68rem;
    font-weight: 900;
    color: #00f5ff;
    text-shadow: 0 0 8px rgba(0, 245, 255, 0.80), 0 1px 2px #000000;
    line-height: 1.25;
  }}
  th.boq-th-blue .th-sub-title {{
    display: block;
    font-size: 0.56rem;
    font-weight: 800;
    color: #7dd3fc;
    margin-top: 1px;
    text-shadow: 0 0 6px rgba(125, 211, 252, 0.65);
    line-height: 1.15;
  }}

  /* ── صفوف وخلايا الجدول ── */
  tr.boq-row {{
    transition: background-color 0.12s ease;
    min-height: 30px;
  }}
  tr.boq-even-row {{
    background-color: rgba(15, 23, 42, 0.92);
  }}
  tr.boq-odd-row {{
    background-color: rgba(30, 41, 59, 0.78);
  }}
  tr.boq-row:hover:not(.boq-total-row) {{
    background-color: rgba(51, 65, 85, 0.65);
  }}
  td.boq-td {{
    position: relative;
    vertical-align: middle;
    border-bottom: 1px solid rgba(148, 163, 184, 0.20);
    border-left: 1px solid rgba(148, 163, 184, 0.18);
    overflow: visible;
  }}
  td.boq-td:last-child {{
    border-left: none;
  }}

  /* ── تنسيق عمود البند ── */
  td.cell-summary {{
    direction: rtl;
    text-align: right;
    padding: 4px 8px 4px 6px;
    background: rgba(234, 88, 12, 0.05);
  }}
  .summary-item-wrap {{
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    justify-content: flex-start;
    gap: 4px;
    direction: rtl;
    text-align: right;
    width: 100%;
    margin-right: 2px;
  }}
  .seq-badge {{
    flex-shrink: 0;
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 900;
    color: #fb923c;
    min-width: 20px;
    text-align: right;
    line-height: 1.4;
    user-select: text;
  }}
  .item-name-txt {{
    flex: 1;
    font-size: 0.68rem;
    font-weight: 800;
    color: #f8fafc;
    line-height: 1.4;
    text-align: start;
    unicode-bidi: plaintext;
    white-space: normal;
    word-wrap: break-word;
    overflow-wrap: break-word;
    user-select: text;
  }}

  /* ── تنسيق الأعمدة الرقمية والوحدة بحجم 1.1x ── */
  .cell-center-wrap {{
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    width: 100%;
    height: 100%;
    padding: 3px 2px;
    white-space: normal;
    word-wrap: break-word;
    user-select: text;
  }}
  td.cell-unit .cell-center-wrap {{
    font-size: 0.68rem;
    font-weight: 700;
    color: #e2e8f0;
  }}
  td.cell-qty .cell-center-wrap {{
    font-size: 0.68rem;
    font-weight: 800;
    color: #f8fafc;
  }}
  td.cell-uprice .cell-center-wrap {{
    font-size: 0.68rem;
    font-weight: 800;
    color: #fdba74;
  }}
  td.cell-tcost .cell-center-wrap {{
    font-size: 0.68rem;
    font-weight: 900;
    color: #fbbf24;
  }}

  /* ── تنسيق عمود توصيف البند القابل للتعديل ── */
  td.cell-desc {{
    padding: 3px 6px;
    background: rgba(2, 132, 199, 0.04);
    overflow: visible;
  }}
  .desc-editor {{
    width: 100%;
    min-height: 26px;
    padding: 3px 6px;
    text-align: start;
    unicode-bidi: plaintext;
    font-size: 0.68rem;
    font-weight: 600;
    color: #ffffff;
    line-height: 1.4;
    border: 1.5px solid transparent;
    border-radius: 5px;
    background: transparent;
    outline: none;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
    transition: all 0.15s ease;
    cursor: text;
    user-select: text;
  }}
  .desc-editor:hover {{
    border-color: rgba(56, 189, 248, 0.40);
    background: rgba(15, 23, 42, 0.65);
  }}
  .desc-editor:focus {{
    border-color: #38bdf8;
    background: rgba(15, 23, 42, 0.95);
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.22);
  }}

  /* ── تنسيق صف إجمالي التكلفة ── */
  tr.boq-total-row {{
    background: linear-gradient(90deg, rgba(6, 78, 59, 0.70) 0%, rgba(4, 120, 87, 0.50) 100%) !important;
    border-top: 2px solid #10b981;
  }}
  tr.boq-total-row td.boq-td {{
    border-bottom: none;
  }}
  tr.boq-total-row .seq-badge,
  tr.boq-total-row .item-name-txt {{
    font-size: 0.70rem !important;
    font-weight: 900 !important;
  }}

  /* ── مقابض تغيير الأبعاد ── */
  .col-resizer {{
    position: absolute;
    top: 0;
    left: 0;
    width: 7px;
    height: 100%;
    cursor: col-resize;
    z-index: 10;
    user-select: none;
  }}
  .col-resizer:hover, .col-resizer.active-resize {{
    background: rgba(56, 189, 248, 0.85);
    box-shadow: 0 0 8px #38bdf8;
  }}
  .row-resizer {{
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 6px;
    cursor: row-resize;
    z-index: 9;
    user-select: none;
  }}
  .row-resizer:hover, .row-resizer.active-resize {{
    background: rgba(234, 88, 12, 0.85);
    box-shadow: 0 0 8px #ea580c;
  }}
</style>
</head>
<body>
<div class="boq-root-container" id="boq-root-container">
    <div class="boq-top-bar">
        <div class="boq-top-title">
            <span>📋 جدول ملخص الكميات وتوصيفات البنود (BOQ Takeoff & Descriptions)</span>
        </div>
        <div class="boq-controls-group">
            <span class="boq-save-badge" id="boq-save-indicator">💾 تم حفظ التوصيفات تلقائياً</span>
            <button type="button" class="boq-btn" id="boq-reset-dims-btn" title="إعادة ضبط أبعاد الأعمدة والصفوف إلى الوضع التلقائي">
                🔄 ضبط الأبعاد
            </button>
        </div>
    </div>

    <div class="boq-table-wrapper" id="boq-table-wrapper">
        <table id="m1-cw-boq-table" dir="rtl">
            <colgroup>
                <col id="boq-col-0" style="width: 24%;">
                <col id="boq-col-1" style="width: 7%;">
                <col id="boq-col-2" style="width: 9%;">
                <col id="boq-col-3" style="width: 10%;">
                <col id="boq-col-4" style="width: 11%;">
                <col id="boq-col-5" style="width: 39%;">
            </colgroup>
            <thead class="boq-thead">
                <tr class="boq-header-row" id="boq-header-tr" data-row-idx="header">
                    <th class="boq-th boq-th-orange">
                        <span class="th-main-title">🟠 البند</span>
                        <span class="th-sub-title">(Item)</span>
                        <div class="col-resizer" data-col="0" title="اسحب بالماوس لتغيير عرض العمود"></div>
                        <div class="row-resizer" data-row="header" title="اسحب بالماوس لتغيير ارتفاع صف العناوين"></div>
                    </th>
                    <th class="boq-th boq-th-orange">
                        <span class="th-main-title">🟠 الوحدة</span>
                        <span class="th-sub-title">(Unit)</span>
                        <div class="col-resizer" data-col="1" title="اسحب بالماوس لتغيير عرض العمود"></div>
                        <div class="row-resizer" data-row="header" title="اسحب بالماوس لتغيير ارتفاع صف العناوين"></div>
                    </th>
                    <th class="boq-th boq-th-orange">
                        <span class="th-main-title">🟠 الكمية</span>
                        <span class="th-sub-title">الإجمالية</span>
                        <div class="col-resizer" data-col="2" title="اسحب بالماوس لتغيير عرض العمود"></div>
                        <div class="row-resizer" data-row="header" title="اسحب بالماوس لتغيير ارتفاع صف العناوين"></div>
                    </th>
                    <th class="boq-th boq-th-orange">
                        <span class="th-main-title">🟠 تكلفة الوحدة</span>
                        <span class="th-sub-title">(ج.م)</span>
                        <div class="col-resizer" data-col="3" title="اسحب بالماوس لتغيير عرض العمود"></div>
                        <div class="row-resizer" data-row="header" title="اسحب بالماوس لتغيير ارتفاع صف العناوين"></div>
                    </th>
                    <th class="boq-th boq-th-orange">
                        <span class="th-main-title">🟠 إجمالي التكلفة</span>
                        <span class="th-sub-title">(ج.م)</span>
                        <div class="col-resizer" data-col="4" title="اسحب بالماوس لتغيير عرض العمود"></div>
                        <div class="row-resizer" data-row="header" title="اسحب بالماوس لتغيير ارتفاع صف العناوين"></div>
                    </th>
                    <th class="boq-th boq-th-blue">
                        <span class="th-main-title">✏️ توصيف البند</span>
                        <span class="th-sub-title">متاح للتعديل ✍️</span>
                        <div class="row-resizer" data-row="header" title="اسحب بالماوس لتغيير ارتفاع صف العناوين"></div>
                    </th>
                </tr>
            </thead>
            <tbody>
                {_cw_tbody_combined}
            </tbody>
        </table>
    </div>
</div>

<script>
(function() {{
    const COL_STORAGE_KEY = 'm1_cw_boq_col_widths_v1';
    const ROW_STORAGE_KEY = 'm1_cw_boq_row_heights_v1';
    const DEFAULT_RATIOS = [0.24, 0.07, 0.09, 0.10, 0.11, 0.39];
    const MIN_COL_WIDTHS = [90, 40, 45, 50, 55, 120];

    const table = document.getElementById('m1-cw-boq-table');
    const wrapper = document.getElementById('boq-table-wrapper');
    const rootContainer = document.getElementById('boq-root-container');
    const cols = [
        document.getElementById('boq-col-0'),
        document.getElementById('boq-col-1'),
        document.getElementById('boq-col-2'),
        document.getElementById('boq-col-3'),
        document.getElementById('boq-col-4'),
        document.getElementById('boq-col-5')
    ];

    let descriptionsMap = {_initial_cw_descs_json};
    let lastSyncedJson = JSON.stringify(descriptionsMap);
    let hasInitializedVisibleWidth = false;

    function updateIframeHeight() {{
        try {{
            if (!rootContainer) return;
            const contentH = Math.max(rootContainer.offsetHeight || 0, rootContainer.scrollHeight || 0);
            if (contentH < 200) return;
            const h = contentH + 24;
            if (window.frameElement) {{
                window.frameElement.style.height = h + 'px';
                window.frameElement.style.minHeight = h + 'px';
                window.frameElement.setAttribute('height', String(h));

                let p = window.frameElement.parentElement;
                let depth = 0;
                while (p && depth < 5) {{
                    const testId = (p.getAttribute && p.getAttribute('data-testid')) || '';
                    const cls = (typeof p.className === 'string') ? p.className : '';
                    if (
                        testId === 'stVerticalBlock' ||
                        testId === 'stVerticalBlockBorderWrapper' ||
                        testId === 'stExpander' ||
                        testId === 'stExpanderDetails' ||
                        testId === 'stColumn' ||
                        testId === 'stMainBlockContainer' ||
                        cls.indexOf('stExpander') !== -1 ||
                        p.tagName === 'DETAILS' ||
                        p.tagName === 'SECTION' ||
                        p.tagName === 'MAIN' ||
                        p.tagName === 'BODY'
                    ) {{
                        break;
                    }}
                    p.style.height = h + 'px';
                    p.style.minHeight = h + 'px';
                    p = p.parentElement;
                    depth++;
                }}
            }}
        }} catch (e) {{}}
    }}

    if (typeof ResizeObserver !== 'undefined' && rootContainer) {{
        const ro = new ResizeObserver(function() {{
            if (wrapper && wrapper.clientWidth > 400 && !hasInitializedVisibleWidth) {{
                hasInitializedVisibleWidth = true;
                initColumnWidths(false);
                initRowHeights(false);
            }}
            updateIframeHeight();
        }});
        ro.observe(rootContainer);
        if (wrapper) ro.observe(wrapper);
    }}

    try {{
        if (window.frameElement) {{
            const parentDetails = window.frameElement.closest('details');
            if (parentDetails) {{
                parentDetails.addEventListener('toggle', function() {{
                    if (parentDetails.open) {{
                        setTimeout(function() {{
                            initColumnWidths(false);
                            initRowHeights(false);
                            updateIframeHeight();
                        }}, 40);
                        setTimeout(updateIframeHeight, 200);
                    }}
                }});
            }}
        }}
    }} catch (e) {{}}

    window.addEventListener('load', updateIframeHeight);
    window.addEventListener('resize', updateIframeHeight);
    setTimeout(updateIframeHeight, 80);
    setTimeout(updateIframeHeight, 300);
    setTimeout(updateIframeHeight, 700);

    function initColumnWidths(forceDefault) {{
        let savedWidths = null;
        if (!forceDefault) {{
            try {{
                const raw = localStorage.getItem(COL_STORAGE_KEY);
                if (raw) {{
                    const parsed = JSON.parse(raw);
                    if (Array.isArray(parsed) && parsed.length === 6 && parsed.every(x => typeof x === 'number' && x >= 30)) {{
                        savedWidths = parsed;
                    }}
                }}
            }} catch (e) {{}}
        }}

        if (savedWidths) {{
            let totalW = savedWidths.reduce((a, b) => a + b, 0);
            if (totalW > 0) {{
                for (let i = 0; i < 6; i++) {{
                    const pct = ((savedWidths[i] / totalW) * 100).toFixed(2);
                    cols[i].style.width = pct + '%';
                }}
            }}
        }} else {{
            for (let i = 0; i < 6; i++) {{
                const pct = (DEFAULT_RATIOS[i] * 100).toFixed(2);
                cols[i].style.width = pct + '%';
            }}
        }}
        table.style.width = '100%';
        updateIframeHeight();
    }}

    function initRowHeights(forceDefault) {{
        if (forceDefault) {{
            const hdrTr = document.getElementById('boq-header-tr');
            if (hdrTr) hdrTr.style.height = '';
            document.querySelectorAll('tr.boq-row').forEach(tr => {{
                tr.style.height = '';
            }});
            updateIframeHeight();
            return;
        }}
        try {{
            const raw = localStorage.getItem(ROW_STORAGE_KEY);
            if (!raw) return;
            const savedRows = JSON.parse(raw);
            if (savedRows && typeof savedRows === 'object') {{
                if (savedRows['header']) {{
                    const hdrTr = document.getElementById('boq-header-tr');
                    if (hdrTr) hdrTr.style.height = savedRows['header'] + 'px';
                }}
                document.querySelectorAll('tr.boq-row').forEach(tr => {{
                    const rIdx = tr.getAttribute('data-row-idx');
                    if (rIdx && savedRows[rIdx]) {{
                        tr.style.height = savedRows[rIdx] + 'px';
                    }}
                }});
            }}
        }} catch (e) {{}}
        updateIframeHeight();
    }}

    function saveColumnWidths() {{
        try {{
            const ths = table.querySelectorAll('thead th.boq-th');
            const arr = Array.from(ths).map(th => Math.round(th.getBoundingClientRect().width));
            if (arr.length === 6) {{
                localStorage.setItem(COL_STORAGE_KEY, JSON.stringify(arr));
            }}
        }} catch (e) {{}}
    }}

    function saveRowHeight(rowKey, hPx) {{
        try {{
            let savedRows = {{}};
            const raw = localStorage.getItem(ROW_STORAGE_KEY);
            if (raw) savedRows = JSON.parse(raw) || {{}};
            savedRows[rowKey] = Math.round(hPx);
            localStorage.setItem(ROW_STORAGE_KEY, JSON.stringify(savedRows));
        }} catch (e) {{}}
    }}

    initColumnWidths(false);
    initRowHeights(false);

    let activeColIdx = null;
    let colStartX = 0;
    let colStartW = 0;
    let nextColStartW = 0;
    let activeColHandle = null;

    document.querySelectorAll('.col-resizer').forEach(handle => {{
        handle.addEventListener('mousedown', function(e) {{
            e.preventDefault();
            e.stopPropagation();
            const cIdx = parseInt(handle.getAttribute('data-col'), 10);
            if (isNaN(cIdx) || cIdx < 0 || cIdx >= 5) return;

            const ths = table.querySelectorAll('thead th.boq-th');
            const curWidths = Array.from(ths).map(th => th.getBoundingClientRect().width);
            for (let i = 0; i < 6; i++) {{
                cols[i].style.width = Math.round(curWidths[i]) + 'px';
            }}

            activeColIdx = cIdx;
            colStartX = e.clientX;
            colStartW = curWidths[cIdx];
            nextColStartW = curWidths[cIdx + 1];
            activeColHandle = handle;
            handle.classList.add('active-resize');
            document.body.classList.add('is-resizing-col');
        }});
    }});

    let activeRowTr = null;
    let activeRowKey = null;
    let rowStartY = 0;
    let rowStartH = 0;
    let activeRowHandle = null;

    document.querySelectorAll('.row-resizer').forEach(handle => {{
        handle.addEventListener('mousedown', function(e) {{
            e.preventDefault();
            e.stopPropagation();
            const rKey = handle.getAttribute('data-row');
            const tr = handle.closest('tr');
            if (!tr) return;

            activeRowTr = tr;
            activeRowKey = rKey;
            rowStartY = e.clientY;
            rowStartH = tr.getBoundingClientRect().height;
            activeRowHandle = handle;
            handle.classList.add('active-resize');
            document.body.classList.add('is-resizing-row');
        }});
    }});

    window.addEventListener('mousemove', function(e) {{
        if (activeColIdx !== null) {{
            e.preventDefault();
            const deltaLeft = colStartX - e.clientX;
            const minCur = MIN_COL_WIDTHS[activeColIdx] || 45;
            const minNext = MIN_COL_WIDTHS[activeColIdx + 1] || 45;

            let newCurW = Math.max(minCur, colStartW + deltaLeft);
            let actualDelta = newCurW - colStartW;
            let newNextW = nextColStartW - actualDelta;

            if (newNextW < minNext) {{
                newNextW = minNext;
                actualDelta = nextColStartW - minNext;
                newCurW = colStartW + actualDelta;
            }}

            const tblW = table.getBoundingClientRect().width || (wrapper ? wrapper.clientWidth : 1000) || 1000;
            const pctCur = ((newCurW / tblW) * 100).toFixed(2);
            const pctNext = ((newNextW / tblW) * 100).toFixed(2);

            cols[activeColIdx].style.width = pctCur + '%';
            cols[activeColIdx + 1].style.width = pctNext + '%';

            table.style.width = '100%';
            updateIframeHeight();
            return;
        }}

        if (activeRowTr !== null) {{
            e.preventDefault();
            const deltaY = e.clientY - rowStartY;
            const minH = (activeRowKey === 'header') ? 48 : 32;
            const newH = Math.max(minH, Math.round(rowStartH + deltaY));
            activeRowTr.style.height = newH + 'px';
            updateIframeHeight();
            return;
        }}
    }});

    window.addEventListener('mouseup', function() {{
        if (activeColIdx !== null) {{
            saveColumnWidths();
            activeColIdx = null;
            if (activeColHandle) {{
                activeColHandle.classList.remove('active-resize');
                activeColHandle = null;
            }}
            document.body.classList.remove('is-resizing-col');
            updateIframeHeight();
        }}
        if (activeRowTr !== null) {{
            const finalH = activeRowTr.getBoundingClientRect().height;
            if (activeRowKey) {{
                saveRowHeight(activeRowKey, finalH);
            }}
            activeRowTr = null;
            activeRowKey = null;
            if (activeRowHandle) {{
                activeRowHandle.classList.remove('active-resize');
                activeRowHandle = null;
            }}
            document.body.classList.remove('is-resizing-row');
            updateIframeHeight();
        }}
    }});

    const resetBtn = document.getElementById('boq-reset-dims-btn');
    if (resetBtn) {{
        resetBtn.addEventListener('click', function() {{
            try {{
                localStorage.removeItem(COL_STORAGE_KEY);
                localStorage.removeItem(ROW_STORAGE_KEY);
            }} catch (e) {{}}
            initColumnWidths(true);
            initRowHeights(true);
        }});
    }}

    let activeFocusedEditor = null;

    function collectAllDescriptions() {{
        document.querySelectorAll('.desc-editor').forEach(ed => {{
            const code = ed.getAttribute('data-item-code');
            if (code) {{
                descriptionsMap[code] = (ed.innerText || ed.textContent || '').trim();
            }}
        }});
    }}

    function syncDescriptionsToStreamlit() {{
        collectAllDescriptions();
        const curJson = JSON.stringify(descriptionsMap);
        if (curJson === lastSyncedJson) return;
        lastSyncedJson = curJson;

        const saveBadge = document.getElementById('boq-save-indicator');
        if (saveBadge) {{
            saveBadge.style.display = 'inline-flex';
            setTimeout(() => {{ saveBadge.style.display = 'none'; }}, 2500);
        }}

        const payload = {{
            action: 'update_cw_boq_descriptions',
            descriptions: descriptionsMap,
            ts: Date.now()
        }};
        const jsonStr = JSON.stringify(payload);
        try {{
            if (window.parent && window.parent.document) {{
                const pDoc = window.parent.document;
                let input = pDoc.querySelector('input[aria-label="{_cw_sync_aria_lbl}"]');
                if (!input) {{
                    input = pDoc.querySelector('div[data-testid="stTextInput"] input');
                }}
                if (input) {{
                    const proto = (window.parent.HTMLInputElement || window.HTMLInputElement).prototype;
                    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (desc && desc.set) {{
                        desc.set.call(input, jsonStr);
                    }} else {{
                        input.value = jsonStr;
                    }}
                    if (input._valueTracker) {{
                        input._valueTracker.setValue('');
                    }}
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    input.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13, which: 13 }}));
                    input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13, which: 13 }}));
                    input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    setTimeout(() => {{
                        try {{
                            if (desc && desc.set) {{ desc.set.call(input, ''); }} else {{ input.value = ''; }}
                        }} catch (e) {{}}
                    }}, 450);
                }}
            }}
        }} catch (err) {{
            console.warn('BOQ description sync error:', err);
        }}
    }}

    function applyBiDiDirection(elem) {{
        if (!elem) return;
        const txt = (elem.innerText || elem.textContent || '').trim();
        if (!txt) {{
            elem.setAttribute('dir', 'auto');
            elem.style.textAlign = 'start';
            return;
        }}
        const arabicRegex = /[\\u0600-\\u06FF\\u0750-\\u077F\\u08A0-\\u08FF\\uFB50-\\uFDFF\\uFE70-\\uFEFF]/;
        const latinRegex = /[a-zA-Z]/;

        let isArabic = false;
        for (let i = 0; i < txt.length; i++) {{
            const ch = txt[i];
            if (arabicRegex.test(ch)) {{
                isArabic = true;
                break;
            }} else if (latinRegex.test(ch)) {{
                isArabic = false;
                break;
            }}
        }}

        if (isArabic) {{
            elem.setAttribute('dir', 'rtl');
            elem.style.textAlign = 'right';
        }} else {{
            elem.setAttribute('dir', 'ltr');
            elem.style.textAlign = 'left';
        }}
    }}

    document.querySelectorAll('.desc-editor, .item-name-txt').forEach(applyBiDiDirection);

    document.querySelectorAll('.desc-editor').forEach(editor => {{
        editor.addEventListener('focus', function() {{
            activeFocusedEditor = editor;
        }});
        editor.addEventListener('input', function() {{
            applyBiDiDirection(editor);
            const code = editor.getAttribute('data-item-code');
            if (code) {{
                descriptionsMap[code] = (editor.innerText || editor.textContent || '').trim();
            }}
            updateIframeHeight();
        }});
        editor.addEventListener('blur', function() {{
            applyBiDiDirection(editor);
            if (activeFocusedEditor === editor) activeFocusedEditor = null;
            const code = editor.getAttribute('data-item-code');
            if (code) {{
                descriptionsMap[code] = (editor.innerText || editor.textContent || '').trim();
            }}
            syncDescriptionsToStreamlit();
        }});
        editor.addEventListener('paste', function() {{
            setTimeout(() => {{
                applyBiDiDirection(editor);
                updateIframeHeight();
            }}, 25);
        }});
    }});

    window.addEventListener('blur', function() {{
        syncDescriptionsToStreamlit();
    }});
    document.addEventListener('visibilitychange', function() {{
        if (document.visibilityState === 'hidden') {{
            syncDescriptionsToStreamlit();
        }}
    }});
}})();
</script>
</body>
</html>
"""
            _cw_tbl_lines = len(cw_items_data) + 2
            _cw_tbl_calc_height = max(420, min(1400, _cw_tbl_lines * 48 + 120))
            components.html(_cw_full_table_html, height=_cw_tbl_calc_height, scrolling=False)

            # ═════════════════════════════════════════════════════════════════════════
            #  4. جدول البنود المستخدمة في المقايسة
            # ═════════════════════════════════════════════════════════════════════════
            _m1_used_items = []
            _m1_unused_items = []
            for _idx, (_name, _net_q, _unit, _u_price, _details) in enumerate(cw_items_data, start=1):
                _tot_q = round(_net_q * cw_qty_factor, 2)
                _clean_name = _re_mod.sub(r'^\d+\s*[-–.]\s*', '', str(_name)).strip()
                if _tot_q > 0.0001:
                    _m1_used_items.append((_idx, _clean_name, _tot_q, str(_unit)))
                else:
                    _m1_unused_items.append((_idx, _clean_name, 0.0, str(_unit)))

            with st.expander("جدول البنود المستخدمة في المقايسة", expanded=False):
                _max_rows = max(len(_m1_used_items), len(_m1_unused_items))
                if _max_rows == 0:
                    _max_rows = 1

                _u_nu_rows_html = []
                for _r_i in range(_max_rows):
                    _bg_row = "rgba(15, 23, 42, 0.75)" if _r_i % 2 == 0 else "rgba(30, 41, 59, 0.75)"

                    if _r_i < len(_m1_used_items):
                        _u_idx, _u_name, _u_qty, _u_unit = _m1_used_items[_r_i]
                        _u_html = (
                            f'<div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">'
                            f'<span style="color:#f8fafc; font-weight:800; font-size:1.00rem; line-height:1.4;">'
                            f'<span style="color:#38bdf8; font-weight:900; margin-left:6px; font-size:1.05rem;">{_u_idx}.</span> {_html_mod.escape(_u_name)}'
                            f'</span>'
                            f'<span style="background:rgba(16, 185, 129, 0.22); color:#34d399; border:1.5px solid rgba(16, 185, 129, 0.60); border-radius:6px; padding:3px 10px; font-weight:900; font-size:0.95rem; white-space:nowrap; direction:ltr; box-shadow:0 2px 6px rgba(16,185,129,0.25);">'
                            f'{_u_qty:,.2f} {_html_mod.escape(_u_unit)}'
                            f'</span>'
                            f'</div>'
                        )
                    elif len(_m1_used_items) == 0 and _r_i == 0:
                        _u_html = '<span style="color:#94a3b8; font-weight:800; font-size:0.95rem; display:block; text-align:center;">لا توجد بنود مستخدمة حتى الآن</span>'
                    else:
                        _u_html = '<span style="color:#64748b; font-weight:700; font-size:0.95rem; display:block; text-align:center;">—</span>'

                    if _r_i < len(_m1_unused_items):
                        _nu_idx, _nu_name, _nu_qty, _nu_unit = _m1_unused_items[_r_i]
                        _nu_html = (
                            f'<div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">'
                            f'<span style="color:#cbd5e1; font-weight:700; font-size:0.95rem; line-height:1.4;">'
                            f'<span style="color:#94a3b8; font-weight:900; margin-left:6px; font-size:1.00rem;">{_nu_idx}.</span> {_html_mod.escape(_nu_name)}'
                            f'</span>'
                            f'<span style="background:rgba(239, 68, 68, 0.16); color:#fca5a5; border:1.5px solid rgba(239, 68, 68, 0.45); border-radius:6px; padding:3px 8px; font-weight:800; font-size:0.92rem; white-space:nowrap; direction:ltr;">'
                            f'0.00 {_html_mod.escape(_nu_unit)}'
                            f'</span>'
                            f'</div>'
                        )
                    elif len(_m1_unused_items) == 0 and _r_i == 0:
                        _nu_html = '<span style="color:#38bdf8; font-weight:800; font-size:0.95rem; display:block; text-align:center;">✨ جميع بنود المقايسة مستخدمة ولها حصر كميات</span>'
                    else:
                        _nu_html = '<span style="color:#64748b; font-weight:700; font-size:0.95rem; display:block; text-align:center;">—</span>'

                    _u_nu_rows_html.append(
                        f'<tr style="border-bottom:1px solid rgba(148, 163, 184, 0.22); background:{_bg_row};">'
                        f'<td style="padding:10px 14px; vertical-align:middle; border-left:1.5px solid rgba(56, 189, 248, 0.35);">{_u_html}</td>'
                        f'<td style="padding:10px 14px; vertical-align:middle;">{_nu_html}</td>'
                        f'</tr>'
                    )

                st.markdown(
                    f"""
                    <div dir="rtl" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; background:linear-gradient(90deg, rgba(15,23,42,0.90) 0%, rgba(30,41,59,0.95) 100%); padding:10px 16px; border-radius:8px; border:1.5px solid rgba(56,189,248,0.45); margin-bottom:10px;">
                        <div style="color:#4ade80; font-weight:900; font-size:1.02rem;">
                            🟢 عدد البنود المستخدمة في المقايسة (الكمية > 0): <span style="background:rgba(16,185,129,0.25); padding:2px 10px; border-radius:6px; border:1.5px solid #10b981; font-size:1.05rem;">{len(_m1_used_items)} بند</span>
                        </div>
                        <div style="color:#f87171; font-weight:900; font-size:1.02rem;">
                            ⚪ عدد البنود الغير مستخدمة في المقايسة (الكمية = 0): <span style="background:rgba(239,68,68,0.25); padding:2px 10px; border-radius:6px; border:1.5px solid #ef4444; font-size:1.05rem;">{len(_m1_unused_items)} بند</span>
                        </div>
                    </div>
                    <div dir="rtl" style="overflow-x:auto; border:2px solid rgba(56, 189, 248, 0.50); border-radius:8px; box-shadow:0 4px 18px rgba(0,0,0,0.45); margin:6px 0 14px 0;">
                        <table style="width:100%; border-collapse:collapse; text-align:right;">
                            <thead>
                                <tr style="border-bottom:2px solid rgba(56, 189, 248, 0.60);">
                                    <th style="width:50%; padding:12px 16px; background:linear-gradient(135deg, rgba(6, 78, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%); color:#4ade80; font-size:1.08rem; font-weight:900; border-left:2px solid rgba(56, 189, 248, 0.40);">
                                        🟢 البنود المستخدمة في المقايسة
                                    </th>
                                    <th style="width:50%; padding:12px 16px; background:linear-gradient(135deg, rgba(127, 29, 29, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%); color:#f87171; font-size:1.08rem; font-weight:900;">
                                        ⚪ البنود الغير مستخدمة في المقايسة
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join(_u_nu_rows_html)}
                            </tbody>
                        </table>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # ═════════════════════════════════════════════════════════════════════════
            #  5. تفاصيل حصر جميع البنود
            # ═════════════════════════════════════════════════════════════════════════
            with st.expander("تفاصيل حصر جميع البنود", expanded=False):
                # دمج بنود الحصر الأساسية مع البنود اليدوية الإضافية في جدول الحصر التفصيلي
                _full_detailed_takeoff_rows = list(comp_works_table_rows)
                for _m_idx, _m_item in enumerate(_cur_manual_items_list, start=13):
                    _m_name = str(_m_item.get("name", f"بند يدوي {_m_idx}")).strip()
                    _m_net_q = float(_m_item.get("net_qty", 0.0))
                    _m_unit = str(_m_item.get("unit", "م² (m²)")).strip()
                    _m_tot_q = round(_m_net_q * cw_qty_factor, 2)
                    _full_detailed_takeoff_rows.append({
                        "م (No.)": str(_m_idx),
                        "بند الأعمال (Work Item)": f"{_m_idx}- {_m_name} (بند إضافي)",
                        "الكمية الصافية (Net Qty)": f"{_m_net_q:,.2f}",
                        "الوحدة (Unit)": _m_unit,
                        "المحددات والتفصيل (Details)": f"إدخال يدوي: {_m_net_q:,.2f} × معامل الزيادة ({cw_qty_factor:.2f}) = {_m_tot_q:,.2f} {_m_unit}",
                    })
                render_styled_table(_full_detailed_takeoff_rows, font_size_override=9.8)

            # ═════════════════════════════════════════════════════════════════════════
            #  6. حساب كميات المواد المستخدمة في البنود
            # ═════════════════════════════════════════════════════════════════════════
            _slab_steel_ton_val = float(st.session_state.get(f"{prefix}slab_steel_ton") or st.session_state.get("slab_steel_ton") or 0.0)
            _boq_materials_dict = _compute_cw_boq_items_materials_breakdown(
                cw_items_data=cw_items_data,
                cw_qty_factor=cw_qty_factor,
                slab_steel_ton=_slab_steel_ton_val,
                prefix=prefix,
            )
            _mat_items = _boq_materials_dict["mat_items"]
            _tot_sand = _boq_materials_dict["tot_sand"]
            _tot_cem_tons = _boq_materials_dict["tot_cement_tons"]
            _tot_cem_bags = _boq_materials_dict["tot_cement_bags"]
            _tot_gravel = _boq_materials_dict["tot_gravel"]
            _tot_steel_ton = _boq_materials_dict["tot_steel_ton"]
            _tot_bricks = _boq_materials_dict["tot_bricks"]

            with st.expander("حساب كميات المواد المستخدمة في البنود", expanded=False):
                # بانيلات المؤشرات الرقمية التراكمية لكميات المواد (6 مؤشرات مميزة)
                st.markdown(
                    f"""
                    <div dir="rtl" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px; margin-bottom:14px;">
                        <div style="background:linear-gradient(135deg, rgba(220,38,38,0.25) 0%, rgba(15,23,42,0.92) 100%); border:1.5px solid #dc2626; border-radius:9px; padding:10px 12px; text-align:center; box-shadow:0 3px 12px rgba(220,38,38,0.25);">
                            <div style="font-size:0.95rem; font-weight:800; color:#fca5a5;">🏗️ حديد التسليح الكلي</div>
                            <div style="font-size:1.50rem; font-weight:900; color:#ef4444; margin-top:3px;"><span dir="ltr">{_tot_steel_ton:,.2f}</span> <span style="font-size:0.95rem;">طن</span></div>
                            <div style="font-size:0.80rem; color:#fee2e2; margin-top:2px;">أسقف + كمرات + أعمدة + قواعد</div>
                        </div>
                        <div style="background:linear-gradient(135deg, rgba(234,88,12,0.25) 0%, rgba(15,23,42,0.92) 100%); border:1.5px solid #ea580c; border-radius:9px; padding:10px 12px; text-align:center; box-shadow:0 3px 12px rgba(234,88,12,0.25);">
                            <div style="font-size:0.95rem; font-weight:800; color:#fdba74;">🧱 إجمالي عدد الطوب الكلي</div>
                            <div style="font-size:1.50rem; font-weight:900; color:#fb923c; margin-top:3px;"><span dir="ltr">{_tot_bricks:,}</span> <span style="font-size:0.95rem;">طوبة</span></div>
                            <div style="font-size:0.80rem; color:#fed7aa; margin-top:2px;">طوب أسمنتي مصمت لمباني الردم</div>
                        </div>
                        <div style="background:linear-gradient(135deg, rgba(202,138,4,0.25) 0%, rgba(15,23,42,0.92) 100%); border:1.5px solid #ca8a04; border-radius:9px; padding:10px 12px; text-align:center; box-shadow:0 3px 12px rgba(202,138,4,0.25);">
                            <div style="font-size:0.95rem; font-weight:800; color:#fef08a;">🏜️ إجمالي الرمل الكلي</div>
                            <div style="font-size:1.50rem; font-weight:900; color:#facc15; margin-top:3px;"><span dir="ltr">{_tot_sand:,.2f}</span> <span style="font-size:0.95rem;">م³</span></div>
                            <div style="font-size:0.80rem; color:#fef9c3; margin-top:2px;">خرسانات + ردم + أرضيات + مباني</div>
                        </div>
                        <div style="background:linear-gradient(135deg, rgba(2,132,199,0.25) 0%, rgba(15,23,42,0.92) 100%); border:1.5px solid #0284c7; border-radius:9px; padding:10px 12px; text-align:center; box-shadow:0 3px 12px rgba(2,132,199,0.25);">
                            <div style="font-size:0.95rem; font-weight:800; color:#bae6fd;">🏗️ إجمالي الأسمنت الكلي</div>
                            <div style="font-size:1.50rem; font-weight:900; color:#38bdf8; margin-top:3px;"><span dir="ltr">{_tot_cem_tons:,.2f}</span> <span style="font-size:0.95rem;">طن</span></div>
                            <div style="font-size:0.80rem; color:#e0f2fe; margin-top:2px;">ما يعادل <span dir="ltr">{_tot_cem_bags:,}</span> شكارة 50 كجم</div>
                        </div>
                        <div style="background:linear-gradient(135deg, rgba(16,185,129,0.25) 0%, rgba(15,23,42,0.92) 100%); border:1.5px solid #10b981; border-radius:9px; padding:10px 12px; text-align:center; box-shadow:0 3px 12px rgba(16,185,129,0.25);">
                            <div style="font-size:0.95rem; font-weight:800; color:#a7f3d0;">🪨 إجمالي الزلط الكلي (السن)</div>
                            <div style="font-size:1.50rem; font-weight:900; color:#34d399; margin-top:3px;"><span dir="ltr">{_tot_gravel:,.2f}</span> <span style="font-size:0.95rem;">م³</span></div>
                            <div style="font-size:0.80rem; color:#d1fae5; margin-top:2px;">للخرسانات المسلحة والعادية والبردورات</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                _mat_rows_html = []
                for _m_item in _mat_items:
                    _m_idx = _m_item["idx"]
                    _m_name = _m_item["name"]
                    _m_tot_q = _m_item["tot_q"]
                    _m_unit = _m_item["unit"]
                    _m_sand = _m_item["sand_m3"]
                    _m_cem_tons = _m_item["cem_tons"]
                    _m_cem_bags = _m_item["cem_bags"]
                    _m_gravel = _m_item["gravel_m3"]
                    _m_steel = _m_item["steel_ton"]
                    _m_bricks = _m_item["bricks"]
                    _m_other = _m_item["other"]

                    _bg_mat_row = "rgba(15, 23, 42, 0.75)" if _m_idx % 2 == 1 else "rgba(30, 41, 59, 0.75)"
                    _is_used = (_m_tot_q > 0.0001)

                    _sand_disp = f"{_m_sand:,.2f}" if _m_sand > 0 else "—"
                    _cem_disp = f"{_m_cem_tons:,.2f} ط ({_m_cem_bags} ش)" if _m_cem_tons > 0 else "—"
                    _gravel_disp = f"{_m_gravel:,.2f}" if _m_gravel > 0 else "—"
                    _steel_disp = f"{_m_steel:,.2f} طن" if _m_steel > 0 else "—"
                    _bricks_disp = f"{_m_bricks:,}" if _m_bricks > 0 else "—"

                    _name_color = "#f8fafc" if _is_used else "#94a3b8"
                    _qty_badge = (
                        f'<span style="background:rgba(16, 185, 129, 0.20); color:#34d399; border:1px solid rgba(16, 185, 129, 0.5); border-radius:5px; padding:2px 8px; font-weight:900; font-size:0.92rem; white-space:nowrap; direction:ltr;">{_m_tot_q:,.2f} {_html_mod.escape(_m_unit)}</span>'
                        if _is_used else
                        f'<span style="background:rgba(239, 68, 68, 0.14); color:#fca5a5; border:1px solid rgba(239, 68, 68, 0.35); border-radius:5px; padding:2px 6px; font-weight:800; font-size:0.88rem; white-space:nowrap; direction:ltr;">0.00 {_html_mod.escape(_m_unit)}</span>'
                    )

                    _mat_rows_html.append(
                        f'<tr style="border-bottom:1px solid rgba(148, 163, 184, 0.22); background:{_bg_mat_row};">'
                        f'<td style="padding:8px 6px; text-align:center; font-weight:900; color:#38bdf8; font-size:0.98rem; border-left:1px solid rgba(148,163,184,0.2);">{_m_idx}</td>'
                        f'<td style="padding:8px 12px; text-align:right; font-weight:800; color:{_name_color}; font-size:0.95rem; border-left:1px solid rgba(148,163,184,0.2); line-height:1.4;">{_html_mod.escape(_m_name)}</td>'
                        f'<td style="padding:8px 8px; text-align:center; border-left:1px solid rgba(148,163,184,0.2);">{_qty_badge}</td>'
                        f'<td style="padding:8px 8px; text-align:center; font-weight:900; color:#fde047; font-size:0.95rem; border-left:1px solid rgba(148,163,184,0.2); direction:ltr;">{_sand_disp}</td>'
                        f'<td style="padding:8px 8px; text-align:center; font-weight:900; color:#7dd3fc; font-size:0.95rem; border-left:1px solid rgba(148,163,184,0.2); direction:ltr;">{_cem_disp}</td>'
                        f'<td style="padding:8px 8px; text-align:center; font-weight:900; color:#6ee7b7; font-size:0.95rem; border-left:1px solid rgba(148,163,184,0.2); direction:ltr;">{_gravel_disp}</td>'
                        f'<td style="padding:8px 8px; text-align:center; font-weight:900; color:#f87171; font-size:0.95rem; border-left:1px solid rgba(148,163,184,0.2); direction:ltr;">{_steel_disp}</td>'
                        f'<td style="padding:8px 8px; text-align:center; font-weight:900; color:#fdba74; font-size:0.95rem; border-left:1px solid rgba(148,163,184,0.2); direction:ltr;">{_bricks_disp}</td>'
                        f'<td style="padding:8px 12px; text-align:right; font-weight:700; color:#e2e8f0; font-size:0.90rem; line-height:1.4;">{_html_mod.escape(_m_other)}</td>'
                        f'</tr>'
                    )

                st.markdown(
                    f"""
                    <div dir="rtl" style="overflow-x:auto; border:2px solid rgba(56, 189, 248, 0.50); border-radius:8px; box-shadow:0 4px 18px rgba(0,0,0,0.45); margin:6px 0 14px 0;">
                        <table style="width:100%; border-collapse:collapse; text-align:right;">
                            <thead>
                                <tr style="border-bottom:2px solid rgba(56, 189, 248, 0.60); background:linear-gradient(135deg, rgba(15,23,42,0.98) 0%, rgba(30,41,59,0.95) 100%);">
                                    <th style="padding:10px 6px; color:#38bdf8; font-size:0.98rem; font-weight:900; text-align:center; width:40px; border-left:1px solid rgba(148,163,184,0.25);">م</th>
                                    <th style="padding:10px 12px; color:#f8fafc; font-size:1.00rem; font-weight:900; width:24%; border-left:1px solid rgba(148,163,184,0.25);">بند الأعمال بالمقايسة</th>
                                    <th style="padding:10px 8px; color:#a7f3d0; font-size:0.98rem; font-weight:900; text-align:center; width:13%; border-left:1px solid rgba(148,163,184,0.25);">الكمية الإجمالية</th>
                                    <th style="padding:10px 8px; color:#fde047; font-size:0.98rem; font-weight:900; text-align:center; width:9%; border-left:1px solid rgba(148,163,184,0.25);">الرمل (م³)</th>
                                    <th style="padding:10px 8px; color:#7dd3fc; font-size:0.98rem; font-weight:900; text-align:center; width:13%; border-left:1px solid rgba(148,163,184,0.25);">الأسمنت (طن / شكارة)</th>
                                    <th style="padding:10px 8px; color:#6ee7b7; font-size:0.98rem; font-weight:900; text-align:center; width:8%; border-left:1px solid rgba(148,163,184,0.25);">الزلط (م³)</th>
                                    <th style="padding:10px 8px; color:#f87171; font-size:0.98rem; font-weight:900; text-align:center; width:9%; border-left:1px solid rgba(148,163,184,0.25);">الحديد (طن)</th>
                                    <th style="padding:10px 8px; color:#fdba74; font-size:0.98rem; font-weight:900; text-align:center; width:9%; border-left:1px solid rgba(148,163,184,0.25);">الطوب (طوبة)</th>
                                    <th style="padding:10px 12px; color:#c084fc; font-size:0.98rem; font-weight:900; text-align:right; width:15%;">المواد التكميلية</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join(_mat_rows_html)}
                                <tr style="background:linear-gradient(90deg, rgba(6,78,59,0.92) 0%, rgba(15,23,42,0.96) 100%); border-top:2.5px solid #10b981; font-weight:900;">
                                    <td colspan="2" style="padding:12px 14px; color:#34d399; font-size:1.08rem; text-align:center; border-left:1px solid rgba(16,185,129,0.4);">🏆 الإجمالي العام لجميع المواد</td>
                                    <td style="padding:12px 8px; color:#6ee7b7; font-size:1.00rem; text-align:center; border-left:1px solid rgba(16,185,129,0.4);">—</td>
                                    <td style="padding:12px 8px; color:#facc15; font-size:1.08rem; text-align:center; border-left:1px solid rgba(16,185,129,0.4); direction:ltr;"><span dir="ltr">{_tot_sand:,.2f} م³</span></td>
                                    <td style="padding:12px 8px; color:#38bdf8; font-size:1.08rem; text-align:center; border-left:1px solid rgba(16,185,129,0.4); direction:ltr;"><span dir="ltr">{_tot_cem_tons:,.2f} ط ({_tot_cem_bags} ش)</span></td>
                                    <td style="padding:12px 8px; color:#34d399; font-size:1.08rem; text-align:center; border-left:1px solid rgba(16,185,129,0.4); direction:ltr;"><span dir="ltr">{_tot_gravel:,.2f} م³</span></td>
                                    <td style="padding:12px 8px; color:#f87171; font-size:1.08rem; text-align:center; border-left:1px solid rgba(16,185,129,0.4); direction:ltr;"><span dir="ltr">{_tot_steel_ton:,.2f} طن</span></td>
                                    <td style="padding:12px 8px; color:#fb923c; font-size:1.08rem; text-align:center; border-left:1px solid rgba(16,185,129,0.4); direction:ltr;"><span dir="ltr">{_tot_bricks:,}</span></td>
                                    <td style="padding:12px 14px; color:#d8b4fe; font-size:0.95rem; text-align:right;">شامل جميع بنود الأعمال والمواد التكميلية</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # ═════════════════════════════════════════════════════════════════════════
            #  7. تصدير ملف الاكسيل بنفس الفلسفة (زر أحمر مميز مع ملف إكسيل متعدد الصفحات)
            # ═════════════════════════════════════════════════════════════════════════
            def _style_cw_openpyxl_worksheet(ws, desc_cols=None):
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                from openpyxl.utils import get_column_letter

                ws.views.sheetView[0].rightToLeft = True
                header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
                header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                body_font = Font(name="Calibri", size=10, color="0F172A")
                summary_font = Font(name="Calibri", size=10, bold=True, color="0F172A")
                grand_font = Font(name="Calibri", size=11, bold=True, color="065F46")
                summary_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
                grand_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
                thin_side = Side(border_style="thin", color="CBD5E1")
                double_bottom = Side(border_style="double", color="065F46")
                cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                grand_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=double_bottom)
                ws.row_dimensions[1].height = 32

                desc_cols = desc_cols or []
                for col_idx in range(1, ws.max_column + 1):
                    col_letter = get_column_letter(col_idx)
                    max_len = 0
                    header_val = str(ws.cell(row=1, column=col_idx).value or "")
                    is_desc_col = (col_idx in desc_cols) or ("توصيف" in header_val)

                    for row_idx in range(1, ws.max_row + 1):
                        cell = ws.cell(row=row_idx, column=col_idx)
                        cell.border = cell_border
                        val_str = str(cell.value or "")
                        if row_idx == 1:
                            cell.fill = header_fill
                            cell.font = header_font
                            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        else:
                            row_text_all = "".join(str(ws.cell(row=row_idx, column=c).value or "") for c in range(1, ws.max_column + 1))
                            is_grand = ("إجمالي" in row_text_all and "التكلفة" in row_text_all) or "الإجمالي العام" in row_text_all or "المجموع" in row_text_all
                            is_sub = "✅" in row_text_all
                            if is_grand:
                                cell.fill = grand_fill
                                cell.font = grand_font
                                cell.border = grand_border
                            elif is_sub:
                                cell.fill = summary_fill
                                cell.font = summary_font
                            else:
                                cell.font = body_font

                            if isinstance(cell.value, float) and header_val != "م":
                                cell.number_format = "#,##0.00"

                            if is_desc_col:
                                needs_wrap = (len(val_str) > 65) or ("\n" in val_str)
                                cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=needs_wrap)
                            elif any(k in header_val for k in ["البند", "ملخص"]):
                                needs_wrap = (len(val_str) > 40) or ("\n" in val_str)
                                cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=needs_wrap)
                            elif header_val == "م":
                                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
                            else:
                                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
                            if len(val_str) < 50:
                                max_len = max(max_len, len(val_str))

                    if header_val == "م":
                        ws.column_dimensions[col_letter].width = 8
                    elif is_desc_col:
                        ws.column_dimensions[col_letter].width = 65
                    elif any(k in header_val for k in ["البند", "ملخص"]):
                        ws.column_dimensions[col_letter].width = 40
                    elif "الكمية" in header_val:
                        ws.column_dimensions[col_letter].width = 24
                    elif "سعر" in header_val:
                        ws.column_dimensions[col_letter].width = 18
                    elif "إجمالي" in header_val or "التكلفة" in header_val:
                        ws.column_dimensions[col_letter].width = 22
                    elif "الوحدة" in header_val:
                        ws.column_dimensions[col_letter].width = 14
                    else:
                        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

            def _build_cw_full_takeoff_excel_bytes(items_data, live_descs, qf_val=1.0, grand_tot=0.0):
                try:
                    import openpyxl
                    import io
                    wb = openpyxl.Workbook()

                    # ── الورقة الأولى: جدول ملخص المقايسة والتكلفة ──
                    ws1 = wb.active
                    ws1.title = "حصر وتكلفة جميع البنود"

                    headers1 = [
                        "م",
                        "توصيف البند",
                        "الوحدة",
                        f"الكمية بالمعامل (× {qf_val:.2f})",
                        "سعر الوحدة (ج.م)",
                        "إجمالي التكلفة (ج.م)",
                        "البند / ملخص الكميات (Summary Item)",
                    ]
                    ws1.append(headers1)

                    calc_total_cost = 0.0
                    for idx, (name, net_q, unit, u_price, details) in enumerate(items_data, start=1):
                        c_key = f"item_{idx}"
                        tot_q = round(net_q * qf_val, 2)
                        tot_cost = round(tot_q * u_price, 2)
                        calc_total_cost += tot_cost
                        desc_text = str(live_descs.get(c_key, "")).strip() or str(DEFAULT_CW_ITEM_DESCRIPTIONS.get(c_key, ""))
                        clean_name = _re_mod.sub(r'^\d+\s*[-–.]\s*', '', str(name)).strip()
                        ws1.append([
                            idx,
                            desc_text,
                            unit,
                            tot_q,
                            u_price,
                            tot_cost,
                            clean_name,
                        ])

                    tot_desc = str(live_descs.get("total_cost", "")).strip() or "إجمالي تكلفة جميع بنود الخرسانات المسلحة والعادية والردم والمباني والأرصفة والعزل شامل معامل الزيادة"
                    ws1.append([
                        "💰",
                        tot_desc,
                        "ج.م (EGP)",
                        "",
                        "",
                        calc_total_cost,
                        "الإجمالي العام للتكلفة (Grand Total Cost)",
                    ])
                    _style_cw_openpyxl_worksheet(ws1, desc_cols=[2])

                    # ── الورقة الثانية: حساب كميات المواد المستخدمة ──
                    ws2 = wb.create_sheet(title="كميات المواد المستخدمة")
                    headers2 = [
                        "م",
                        "بند الأعمال بالمقايسة",
                        "الكمية الإجمالية",
                        "الوحدة",
                        "الرمل (م³)",
                        "الأسمنت (طن)",
                        "الأسمنت (شكارة)",
                        "الزلط (م³)",
                        "حديد التسليح (طن)",
                        "الطوب (طوبة)",
                        "المواد التكميلية",
                    ]
                    ws2.append(headers2)

                    for _m_item in _mat_items:
                        ws2.append([
                            _m_item["idx"],
                            _m_item["name"],
                            _m_item["tot_q"],
                            _m_item["unit"],
                            _m_item["sand_m3"] if _m_item["sand_m3"] > 0 else "",
                            _m_item["cem_tons"] if _m_item["cem_tons"] > 0 else "",
                            _m_item["cem_bags"] if _m_item["cem_bags"] > 0 else "",
                            _m_item["gravel_m3"] if _m_item["gravel_m3"] > 0 else "",
                            _m_item["steel_ton"] if _m_item["steel_ton"] > 0 else "",
                            _m_item["bricks"] if _m_item["bricks"] > 0 else "",
                            _m_item["other"],
                        ])

                    ws2.append([
                        "🏆",
                        "الإجمالي العام لجميع المواد",
                        "",
                        "",
                        _tot_sand,
                        _tot_cem_tons,
                        _tot_cem_bags,
                        _tot_gravel,
                        _tot_steel_ton,
                        _tot_bricks,
                        "شامل كافة بنود الأعمال",
                    ])
                    _style_cw_openpyxl_worksheet(ws2)

                    # ── الورقة الثالثة: تفاصيل الحصر الهندسي ──
                    ws3 = wb.create_sheet(title="تفاصيل الحصر الهندسي")
                    headers3 = [
                        "م (No.)",
                        "بند الأعمال (Work Item)",
                        "الكمية الصافية (Net Qty)",
                        "الوحدة (Unit)",
                        "المحددات والتفصيل (Details)",
                    ]
                    ws3.append(headers3)
                    for row in _full_detailed_takeoff_rows:
                        ws3.append([
                            row.get("م (No.)", ""),
                            row.get("بند الأعمال (Work Item)", ""),
                            row.get("الكمية الصافية (Net Qty)", ""),
                            row.get("الوحدة (Unit)", ""),
                            row.get("المحددات والتفصيل (Details)", ""),
                        ])
                    _style_cw_openpyxl_worksheet(ws3, desc_cols=[5])

                    # ── الورقة الرابعة: البنود المستخدمة والغير مستخدمة ──
                    ws4 = wb.create_sheet(title="البنود المستخدمة والغير مستخدمة")
                    headers4 = [
                        "م",
                        "البند المستخدم بالمقايسة",
                        "الكمية الإجمالية",
                        "الوحدة",
                        "م",
                        "البند الغير مستخدم (كمية = 0)",
                        "الوحدة",
                    ]
                    ws4.append(headers4)
                    _max_r_xl = max(len(_m1_used_items), len(_m1_unused_items))
                    for _ri in range(_max_r_xl):
                        _u_row = _m1_used_items[_ri] if _ri < len(_m1_used_items) else ("", "", "", "")
                        _nu_row = _m1_unused_items[_ri] if _ri < len(_m1_unused_items) else ("", "", "", "")
                        ws4.append([
                            _u_row[0],
                            _u_row[1],
                            _u_row[2] if _u_row[0] != "" else "",
                            _u_row[3],
                            _nu_row[0],
                            _nu_row[1],
                            _nu_row[3],
                        ])
                    _style_cw_openpyxl_worksheet(ws4)

                    output = io.BytesIO()
                    wb.save(output)
                    return output.getvalue()
                except Exception as e:
                    print(f"Error generating Excel: {e}")
                    return None

            _cw_full_xl_bytes = _build_cw_full_takeoff_excel_bytes(
                items_data=cw_items_data,
                live_descs=cw_live_descriptions,
                qf_val=cw_qty_factor,
                grand_tot=cw_grand_total_cost,
            )

            _cw_dl_key = f"{prefix}dl_comp_bldg_works_excel_red_v{_ftg_exp_ver}"
            st.markdown(
                f"""
                <style>
                div.stDownloadButton:has(> button[key="{_cw_dl_key}"]),
                div.stDownloadButton:has(> button#m1-cw-export-btn),
                div[data-testid="stVerticalBlock"]:has(#m1-cw-export-boq-anchor) [data-testid="stDownloadButton"] button,
                button[key="{_cw_dl_key}"] {{
                    width: 100% !important;
                    background: linear-gradient(135deg, #b91c1c 0%, #dc2626 50%, #ef4444 100%) !important;
                    color: #ffffff !important;
                    border: 1.5px solid #f87171 !important;
                    border-radius: 9px !important;
                    padding: 12px 18px !important;
                    font-size: 1.15rem !important;
                    font-weight: 900 !important;
                    box-shadow: 0 4px 18px rgba(220, 38, 38, 0.45) !important;
                    transition: all 0.25s ease !important;
                    margin: 8px 0 14px 0 !important;
                    text-align: center !important;
                }}
                div.stDownloadButton:has(> button[key="{_cw_dl_key}"]):hover,
                button[key="{_cw_dl_key}"]:hover,
                div[data-testid="stVerticalBlock"]:has(#m1-cw-export-boq-anchor) [data-testid="stDownloadButton"] button:hover {{
                    background: linear-gradient(135deg, #991b1b 0%, #b91c1c 50%, #dc2626 100%) !important;
                    border-color: #fca5a5 !important;
                    box-shadow: 0 6px 24px rgba(239, 68, 68, 0.65) !important;
                    transform: translateY(-2px) !important;
                }}
                div[data-testid="stVerticalBlock"]:has(#m1-cw-export-boq-anchor) [data-testid="stDownloadButton"] button p,
                div[data-testid="stVerticalBlock"]:has(#m1-cw-export-boq-anchor) [data-testid="stDownloadButton"] button span,
                div[data-testid="stVerticalBlock"]:has(#m1-cw-export-boq-anchor) [data-testid="stDownloadButton"] button div,
                button[key="{_cw_dl_key}"] p,
                button[key="{_cw_dl_key}"] span {{
                    color: #ffffff !important;
                    font-weight: 900 !important;
                    font-size: 1.15rem !important;
                    text-shadow: 0 1px 3px rgba(0,0,0,0.5) !important;
                }}
                </style>
                <div id="m1-cw-export-boq-anchor" style="display:none; margin:0; padding:0;"></div>
                """,
                unsafe_allow_html=True,
            )
            if _cw_full_xl_bytes:
                st.download_button(
                    "📥 تصدير جدول الحصر EXCEL SHEET",
                    data=_cw_full_xl_bytes,
                    file_name=f"حصر_وتكلفة_جميع_البنود_{cw_qty_factor:.2f}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=_cw_dl_key,
                )
