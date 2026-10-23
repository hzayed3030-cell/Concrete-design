9: Lx_spans: horizontal distances between vertical axes  (direction X)
10: Ly_spans: vertical   distances between horizontal axes (direction Y)
106: def _geometry_key(Lx_spans, Ly_spans):
107: """Return a hashable key representing the current span geometry, used to detect input changes."""
108: return (tuple(round(x, 4) for x in Lx_spans), tuple(round(y, 4) for y in Ly_spans))
111: def _compute_effective_spans(Lx_spans, Ly_spans, removed_ij_set):
114: Lx and Ly spans that remain active for DDM calculations.
116: A Y-axis index i is considered 'inactive' (no support) only when ALL columns
117: along that axis are removed. Similarly for X-axis index j.
119: Returns (eff_Lx_spans, eff_Ly_spans, active_x_indices, active_y_indices,
120: full_axis_x_removed, full_axis_y_removed, ddm_valid_warning).
123: for lx in Lx_spans:
126: for ly in Ly_spans:
129: n_xi = len(x_coords)   # number of Y-axis lines (i indices)
130: n_yj = len(y_coords)   # number of X-axis lines (j indices)
132: # Count remaining columns per axis line
133: remaining_per_xi = {}   # i -> count of remaining cols at that Y-axis
134: remaining_per_yj = {}   # j -> count of remaining cols at that X-axis
140: # An axis line remains active as long as it has at least 1 active column;
148: # Compute effective spans between consecutive active axis lines
149: eff_Lx = [x_coords[active_xi[k+1]] - x_coords[active_xi[k]] for k in range(len(active_xi)-1)]
150: eff_Ly = [y_coords[active_yj[k+1]] - y_coords[active_yj[k]] for k in range(len(active_yj)-1)]
152: # Detect fully-removed intermediate axis lines (for warning)
156: # DDM validity check: adjacent effective spans ratio must be ≤ 1.33
158: for spans, label in [(eff_Lx, "X"), (eff_Ly, "Y")]:
160: ratio = max(spans[k], spans[k+1]) / max(0.001, min(spans[k], spans[k+1]))
170: return eff_Lx, eff_Ly, active_xi, active_yj, full_x_removed, full_y_removed, ddm_warning
186: sx = str(trans.get("shift_x", "متمركز على المحور (Centered)")).strip()
188: norm_sx = "جسم العمود يميناً (الوجه يسار المحور -6 cm)"
190: norm_sx = "جسم العمود يساراً (الوجه يمين المحور +6 cm)"
192: norm_sx = "متمركز على المحور (Centered)"
194: sy = str(trans.get("shift_y", "متمركز على المحور (Centered)")).strip()
196: norm_sy = "جسم العمود لأعلى (الوجه أسفل المحور -6 cm)"
198: norm_sy = "جسم العمود لأسفل (الوجه أعلى المحور +6 cm)"
200: norm_sy = "متمركز على المحور (Centered)"
209: def compute_column_geometry(grid_x, grid_y, bc_cm, tc_cm, trans=None):
214: - Centered: x_min = grid_x - Width/2, y_min = grid_y - Height/2
215: - Right (جسم العمود يميناً): x_min = grid_x - 0.06
216: - Left  (جسم العمود يساراً): x_min = grid_x + 0.06 - Width
217: - Top   (جسم العمود لأعلى): y_min = grid_y - 0.06
218: - Bottom(جسم العمود لأسفل): y_min = grid_y + 0.06 - Height
226: grid_x = float(grid_x)
228: grid_x = 0.0
230: grid_y = float(grid_y)
232: grid_y = 0.0
250: x_min = grid_x - off_m
252: x_min = grid_x + off_m - width_m
254: x_min = grid_x - (width_m / 2.0)
258: y_min = grid_y - off_m
260: y_min = grid_y + off_m - height_m
262: y_min = grid_y - (height_m / 2.0)
281: "grid_x": grid_x,
282: "grid_y": grid_y,
297: 2. The maximum allowed offset beyond the axis does not exceed 6 cm in the specified neighbor directi
323: # Resolve numeric grid_x coordinate in meters
325: if "grid_x_m" in geom and geom["grid_x_m"] is not None:
326: gx = _to_float(geom["grid_x_m"], None)
328: gx = _to_float(geom.get("grid_x"), None)
334: # Resolve numeric grid_y coordinate in meters
336: if "grid_y_m" in geom and geom["grid_y_m"] is not None:
337: gy = _to_float(geom["grid_y_m"], None)
339: gy = _to_float(geom.get("grid_y"), None)
601: Lx_spans,
602: Ly_spans,
617: Lx_spans:       List of span lengths in X-direction (m).
618: Ly_spans:       List of span lengths in Y-direction (m).
635: eff_Lx_spans:    Effective Lx spans for DDM after axis merging.
636: eff_Ly_spans:    Effective Ly spans for DDM after axis merging.
642: for lx in Lx_spans:
645: for ly in Ly_spans:
712: "grid_x_m":  x,
713: "grid_y_m":  y,
714: "grid_x":    f"Y{i+1}",
715: "grid_y":    f"X{j+1}",
743: # ── Build (i, j) removed set for axis analysis ───────────────────────────
748: eff_Lx, eff_Ly, active_xi, active_yj, _, _, ddm_warning = _compute_effective_spans(
749: Lx_spans, Ly_spans, removed_ij
752: eff_Lx, eff_Ly = list(Lx_spans), list(Ly_spans)
765: # Reclassify based on effective grid boundaries
774: return active_columns, all_columns, eff_Lx, eff_Ly, ddm_warning
778: def get_flat_slab_panels(Lx_spans, Ly_spans, void_ids=None):
784: Lx_spans: List of span lengths in X-direction (m).
785: Ly_spans: List of span lengths in Y-direction (m).
794: for lx in Lx_spans:
797: for ly in Ly_spans:
802: for j in range(len(Ly_spans)):
803: for i in range(len(Lx_spans)):
808: lx = Lx_spans[i]
809: ly = Ly_spans[j]
811: grid_x = f"Y{i+1}-Y{i+2}"
812: grid_y = f"X{j+1}-X{j+2}"
825: "Lx": lx,
826: "Ly": ly,
828: "grid_x": grid_x,
829: "grid_y": grid_y,
831: "label": f"Panel P ({i+1},{j+1}) [{grid_x} × {grid_y}] ({lx:.2f}m × {ly:.2f}m — {area:.1f} m²)",
856: Unified renderer for Drop Beams and Cantilever Drop Beams on any 2D plan axis.
882: Lx_spans,
883: Ly_spans,
912: preview_axis=None,      # dict e.g. {"dir": "X"/"Y", "pos": float, "label": str} for live axis previ
926: for lx in Lx_spans:
930: for ly in Ly_spans:
959: offset_grid_top = max(1.0, slab_h * 0.09)
960: offset_grid_left = max(1.0, slab_w * 0.09)
1025: all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _voids)
1047: (p["x1"], p["y1"]), p["Lx"], p["Ly"],
1062: (p["x1"], p["y1"]), p["Lx"], p["Ly"],
1085: y_top_ext = y_slab_max + offset_grid_top
1094: x_left_ext = x_slab_min - offset_grid_left
1101: # ── Live Preview Axis (المحور الجاري إدراجه قبل التأكيد النهائي مع خطوط الأبعاد Dimension) ──
1102: if isinstance(preview_axis, dict) and preview_axis.get("pos") is not None:
1103: p_dir = preview_axis.get("dir", "X")
1104: p_pos = float(preview_axis.get("pos", 0.0))
1105: p_lbl = str(preview_axis.get("label", "NEW"))
1106: p_dist_val = float(preview_axis.get("dist", 0.0))
1107: p_rem_val = float(preview_axis.get("rem", 0.0))
1108: p_ref_start = float(preview_axis.get("ref_start", p_pos))
1109: p_ref_end = float(preview_axis.get("ref_end", p_pos))
1110: p_is_split = bool(preview_axis.get("is_split", False))
1114: y_top_ext = y_slab_max + offset_grid_top
1156: x_left_ext = x_slab_min - offset_grid_left
1197: # Columns at axis intersections — with removal state visualisation
1297: # Span Dimensions (Lx along Bottom)
1299: for i, lx in enumerate(Lx_spans):
1321: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.30, f"Total Lx = {slab_w:.2f} m",
1325: # Span Dimensions (Ly along Right)
1327: for j, ly in enumerate(Ly_spans):
1349: x_dim_tot + 0.30, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
1368: ax_plan.axis("off")
1415: ax_card.axis("off")
1501: Lx_spans,
1502: Ly_spans,
1524: for lx in Lx_spans:
1528: for ly in Ly_spans:
1546: offset_grid_top = max(1.8, slab_h * 0.10)
1547: offset_grid_left = max(1.8, slab_w * 0.10)
1616: all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _voids)
1620: (p["x1"], p["y1"]), p["Lx"], p["Ly"],
1635: y_top_ext = y_slab_max + offset_grid_top
1644: x_left_ext = x_slab_min - offset_grid_left
1653: min_span_x = min(Lx_spans) if Lx_spans else 6.0
1654: min_span_y = min(Ly_spans) if Ly_spans else 6.0
1668: patch_w = min(max(l_ext * 0.65, col_w_m + 0.9), min_span_x * 0.44)
1669: patch_h = min(max(l_ext * 0.50, col_d_m + 0.9), min_span_y * 0.44)
1723: # Span Dimensions (Lx along Bottom)
1725: for i, lx in enumerate(Lx_spans):
1747: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.45, f"Total Lx = {slab_w:.2f} m",
1751: # Span Dimensions (Ly along Right)
1754: for j, ly in enumerate(Ly_spans):
1776: x_dim_tot + 0.45, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
1831: ax_plan.axis("off")
1835: ax_legend.axis("off")
1887: Lx_spans,
1888: Ly_spans,
1892: btm_extra_spans,
1911: for lx in Lx_spans:
1915: for ly in Ly_spans:
1933: offset_grid_top = max(1.8, slab_h * 0.10)
1934: offset_grid_left = max(1.8, slab_w * 0.10)
2003: all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _voids)
2007: (p["x1"], p["y1"]), p["Lx"], p["Ly"],
2022: y_top_ext = y_slab_max + offset_grid_top
2031: x_left_ext = x_slab_min - offset_grid_left
2040: min_span_x = min(Lx_spans) if Lx_spans else 6.0
2041: min_span_y = min(Ly_spans) if Ly_spans else 6.0
2076: if btm_extra_spans:
2080: be for be in btm_extra_spans
2084: active_btm_extras = [be for be in btm_extra_spans if isinstance(be, dict) and be.get("n_extra", 0) >
2098: box_w = min(max(l_b * 0.55, 3.2), span_len * 0.55)
2099: box_h = min(max(slab_h * 0.12, 1.5), min_span_y * 0.35)
2117: box_w = min(max(slab_w * 0.12, 1.5), min_span_x * 0.35)
2118: box_h = min(max(l_b * 0.55, 3.2), span_len * 0.55)
2136: # Span Dimensions (Lx along Bottom)
2138: for i, lx in enumerate(Lx_spans):
2160: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.45, f"Total Lx = {slab_w:.2f} m",
2164: # Span Dimensions (Ly along Right)
2167: for j, ly in enumerate(Ly_spans):
2189: x_dim_tot + 0.45, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
2196: ax_plan.axis("off")
2200: ax_legend.axis("off")
2252: Lx_spans,
2253: Ly_spans,
2273: for lx in Lx_spans:
2277: for ly in Ly_spans:
2295: offset_grid_top = max(1.8, slab_h * 0.10)
2296: offset_grid_left = max(1.8, slab_w * 0.10)
2364: all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _voids)
2368: (p["x1"], p["y1"]), p["Lx"], p["Ly"],
2381: # Tributary area boundary dividers (mid-spans)
2382: for i in range(len(Lx_spans)):
2385: for j in range(len(Ly_spans)):
2391: y_top_ext = y_slab_max + offset_grid_top
2400: x_left_ext = x_slab_min - offset_grid_left
2417: orig_grid_id = f"C{j_idx * len(x_coords) + i_idx + 1}"
2418: if orig_grid_id in rem_orig_ids or (round(float(x), 3), round(float(y), 3)) in rem_coords:
2509: # Span Dimensions (Lx along Bottom)
2511: for i, lx in enumerate(Lx_spans):
2533: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.45, f"Total Lx = {slab_w:.2f} m",
2537: # Span Dimensions (Ly along Right)
2540: for j, ly in enumerate(Ly_spans):
2562: x_dim_tot + 0.45, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
2569: ax_plan.axis("off")
2573: ax_legend.axis("off")
2586: ("EDGE COLUMNS\n(أعمدة طرفية / وسط خارجي)", "Half-span spandrel tributary area\nSubject to edge unba
2587: ("CORNER COLUMNS\n(أعمدة أركان)", "Quarter-span corner tributary area\nSubject to biaxial corner mom
2625: Lx_spans,
2626: Ly_spans,
2634: btm_extra_spans=None,
2652: for lx in Lx_spans:
2655: for ly in Ly_spans:
2666: nx_pts = max(grid_res, int(grid_res * slab_w / max(slab_h, 1.0)))
2667: ny_pts = max(grid_res, int(grid_res * slab_h / max(slab_w, 1.0)))
2670: X, Y = np.meshgrid(x_vec, y_vec)
2675: Lx_avg = np.mean(Lx_spans) if Lx_spans else 6.0
2676: Ly_avg = np.mean(Ly_spans) if Ly_spans else 6.0
2677: h_cs_y = min(Lx_avg, Ly_avg) / 4.0
2678: h_cs_x = min(Lx_avg, Ly_avg) / 4.0
2720: cx = c.get("grid_x_m", c.get("x"))
2721: cy = c.get("grid_y_m", c.get("y"))
2772: for j_idx in range(len(Ly_spans)):
2773: for i_idx in range(len(Lx_spans)):
2819: for j_idx, ly_val in enumerate(Ly_spans):
2822: L_span_y = max(0.5, y_top - y_bot)
2824: solid_i = [i_idx for i_idx in range(len(Lx_spans)) if not is_panel_void(i_idx, j_idx)]
2839: # Governing design positive moment for this Y-span:
2842: m_pos_22 = (r_y.get("cs_pos", 0.60 * r_y.get("M_pos", 10.0)) / max(0.1, r_y.get("cs_w", min(ly_val, 
2844: m_pos_22 = 0.52 * Wu * (min(L_span_y, 6.0) ** 2) / 8.0
2855: eta = np.clip((Y[mask_seg] - y_bot) / L_span_y, 0.0, 1.0)
2866: for i_idx, lx_val in enumerate(Lx_spans):
2869: L_span_x = max(0.5, x_right - x_left)
2871: solid_j = [j_idx for j_idx in range(len(Ly_spans)) if not is_panel_void(i_idx, j_idx)]
2886: # Governing design positive moment for this X-span:
2889: m_pos_11 = (r_x.get("cs_pos", 0.60 * r_x.get("M_pos", 10.0)) / max(0.1, r_x.get("cs_w", min(lx_val, 
2891: m_pos_11 = 0.52 * Wu * (min(L_span_x, 6.0) ** 2) / 8.0
2902: xi = np.clip((X[mask_seg] - x_left) / L_span_x, 0.0, 1.0)
2913: h_bridge_y = max(1.2, Ly_avg * 0.45)
2914: h_bridge_x = max(1.2, Lx_avg * 0.45)
2921: if not (j_idx < len(Ly_spans) and is_panel_void(i_idx - 1, j_idx) and is_panel_void(i_idx, j_idx)):
2925: m_pos_11_a = (rows_x[i_idx - 1].get("cs_pos", 10.0) / max(0.1, rows_x[i_idx - 1].get("cs_w", 2.0))) 
2936: if not (i_idx < len(Lx_spans) and is_panel_void(i_idx, j_idx - 1) and is_panel_void(i_idx, j_idx)):
2940: m_pos_22_a = (rows_y[j_idx - 1].get("cs_pos", 10.0) / max(0.1, rows_y[j_idx - 1].get("cs_w", 2.0))) 
2954: cx = c.get("grid_x_m", c.get("x"))
2955: cy = c.get("grid_y_m", c.get("y"))
2965: m_neg_peak_x = 0.75 * Wu * (Lx_avg ** 2) / 8.0 * 0.65 / max(0.1, h_cs_x) if Lx_avg else 8.0
2966: m_neg_peak_y = 0.75 * Wu * (Ly_avg ** 2) / 8.0 * 0.65 / max(0.1, h_cs_y) if Ly_avg else 8.0
2972: r_col_eff = max(0.75, min(Lx_avg, Ly_avg) * 0.18)
3000: # (extended continuously into the adjacent backspan beam). For the slab panel itself, the cantilever
3070: if btm_extra_spans:
3072: for item in btm_extra_spans:
3080: if cx is None or cy is None or span_len <= 0 or w_bay <= 0:
3084: px1 = cx - span_len / 2.0
3085: px2 = cx + span_len / 2.0
3094: py1 = cy - span_len / 2.0
3095: py2 = cy + span_len / 2.0
3112: for j in range(len(Ly_spans)):
3113: for i in range(len(Lx_spans)):
3125: def build_grid_axes_info(x_coords, y_coords, active_cols, active_x_labels=None, active_y_labels=None
3127: Resolves complete structural grid lines (X and Y) with their correct coordinates and CAD bubble labe
3128: If active_cols are provided with grid_x/grid_y metadata, ensures all active grid axes (e.g. X1, X2, 
3134: gx = c.get("grid_x")
3135: gxm = c.get("grid_x_m", c.get("x"))
3149: gy = c.get("grid_y")
3150: gym = c.get("grid_y_m", c.get("y"))
3190: cx = float(c.get("center_x", c.get("grid_x_m", c.get("x", 0.0))))
3191: cy = float(c.get("center_y", c.get("grid_y_m", c.get("y", 0.0))))
3325: Lx_spans,
3326: Ly_spans,
3355: Strictly ignores virtual grid lines, computing spans, supports, and moments from TRUE physical suppo
3361: for lx in Lx_spans: x_coords.append(round(x_coords[-1] + float(lx), 4))
3363: for ly in Ly_spans: y_coords.append(round(y_coords[-1] + float(ly), 4))
3377: w_strip = min(np.mean(Lx_spans), np.mean(Ly_spans)) / 2.0
3385: w_strip = min(np.mean(Lx_spans), np.mean(Ly_spans)) / 2.0
3399: num_spans = max(1, len(support_pts) - 1)
3539: # Build span_moments with true net mid-span positive moment (m_pos_k > 0) and free sagging height (h
3552: # Net positive mid-span moment M_pos (strictly positive, sagging below baseline) per ECP 203:
3557: # Exterior / End span in continuous system
3560: # Interior span in continuous system
3565: # Check if a longitudinal beam in cut_beams physically covers THIS specific span (Column Strip only)
3582: # Total parabolic free sagging drop height from negative support chord line to positive mid-span pea
3613: if not np.any(mask_span):
3616: xi = np.clip((s_vec[mask_span] - sk_left) / Lk, 0.0, 1.0)
3618: m_span = sm["left_neg"] * (1.0 - xi) + sm["right_neg"] * xi + 4.0 * sm["h_free"] * xi * (1.0 - xi)
3786: ax_bmd.fill_between(s_vec, y_bmd, 0, where=(y_bmd <= 0), interpolate=True, color='#e0f2fe', alpha=0.
3838: idx_span = np.where((s_vec >= x_left + 0.15) & (s_vec <= x_right - 0.15))[0]
3839: if len(idx_span) > 0:
3840: valid_span = m_vec[idx_span]
3842: m_pos_peak = float(np.nanmax(valid_span))
3844: s_pos_peak = float(s_vec[idx_span[np.nanargmax(valid_span)]])
3873: ax_bmd.yaxis.set_major_formatter(ticker.FuncFormatter(_moment_tick_formatter))
3876: ax_bmd.grid(True, linestyle=':', alpha=0.55, color='#94a3b8')
3902: Lx_spans,
3903: Ly_spans,
3914: btm_extra_spans=None,
3936: for lx in Lx_spans:
3940: for ly in Ly_spans:
3969: Lx_spans, Ly_spans, cantilevers, rows_x, rows_y, Wu,
3971: btm_extra_spans=btm_extra_spans,
3983: offset_grid_top = max(1.8, slab_h * 0.10)
3984: offset_grid_left = max(1.8, slab_w * 0.10)
4075: for j in range(len(Ly_spans)):
4076: for i in range(len(Lx_spans)):
4094: axes_x_info, axes_y_info = build_grid_axes_info(x_coords, y_coords, active_cols, active_x_labels, ac
4098: y_top_ext = y_slab_max + offset_grid_top
4107: x_left_ext = x_slab_min - offset_grid_left
4160: grid_idx = 1
4164: orig_id = f"C{grid_idx}"
4165: grid_idx += 1
4210: # Peak Positive Moment Badges at Bay Midspans (with Anti-Overlap Staggering)
4211: for j in range(len(Ly_spans)):
4212: Ly = y_coords[j+1] - y_coords[j]
4213: for i in range(len(Lx_spans)):
4214: Lx = x_coords[i+1] - x_coords[i]
4217: # Check if midspan is inside any void
4232: has_narrow_x = (Lx < 2.5) or (i > 0 and Lx_spans[i-1] < 2.5) or (i < len(Lx_spans)-1 and Lx_spans[i+
4233: has_narrow_y = (Ly < 2.5) or (j > 0 and Ly_spans[j-1] < 2.5) or (j < len(Ly_spans)-1 and Ly_spans[j+
4237: if has_narrow_x and Ly >= 2.0:
4238: y_stagger = min(1.10, Ly * 0.20)
4241: elif has_narrow_y and Lx >= 2.0:
4242: x_stagger = min(1.10, Lx * 0.18)
4246: if Lx < 2.2:
4263: # Span Dimensions (Lx along Bottom)
4265: for i, lx in enumerate(Lx_spans):
4287: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.45, f"Total Lx = {slab_w:.2f} m",
4291: # Span Dimensions (Ly along Right)
4294: for j, ly in enumerate(Ly_spans):
4316: x_dim_tot + 0.45, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
4323: ax_plan.axis("off")
4325: dir_txt_ar = "اتجاه المحور الأفقي X" if mode == "M11" else "اتجاه المحور الرأسي Y"
4355: Lx_spans,
4356: Ly_spans,
4367: btm_extra_spans=None,
4377: for lx in Lx_spans:
4381: for ly in Ly_spans:
4398: Lx_spans, Ly_spans, cantilevers, rows_x, rows_y, Wu,
4400: btm_extra_spans=btm_extra_spans,
4406: offset_grid_top = max(1.5, slab_h * 0.09)
4407: offset_grid_left = max(1.5, slab_w * 0.09)
4454: for j in range(len(Ly_spans)):
4455: for i in range(len(Lx_spans)):
4469: ax.plot([x, x], [y_slab_min - 0.4, y_slab_max + offset_grid_top], color="#dc2626", linestyle=":", li
4470: bubble = Circle((x, y_slab_max + offset_grid_top), radius=bubble_radius, facecolor="#fee2e2", edgeco
4472: ax.text(x, y_slab_max + offset_grid_top, f"Y{idx+1}", color="#991b1b", fontsize=13, weight="bold", h
4475: ax.plot([x_slab_min - offset_grid_left, x_slab_max + 0.4], [y, y], color="#dc2626", linestyle=":", l
4476: bubble = Circle((x_slab_min - offset_grid_left, y), radius=bubble_radius, facecolor="#fee2e2", edgec
4478: ax.text(x_slab_min - offset_grid_left, y, f"X{idx+1}", color="#991b1b", fontsize=13, weight="bold", 
4531: ax.axis("off")
4538: Lx_spans,
4539: Ly_spans,
4555: btm_extra_spans=None,
4576: is_top_bay = ("bay" in layer_str or "spans" in layer_str)
4597: for lx in Lx_spans:
4601: for ly in Ly_spans:
4619: Lx_spans, Ly_spans, cantilevers, rows_x, rows_y, Wu,
4621: btm_extra_spans=btm_extra_spans,
4642: # Column zone extends roughly col_dim/2 + L_span/4 around each column center
4643: Lx_avg = float(np.mean(Lx_spans)) if Lx_spans else 5.0
4644: Ly_avg = float(np.mean(Ly_spans)) if Ly_spans else 5.0
4645: # Half-width of column strip per ECP 203: min(Lx, Ly)/4
4646: cs_half_x = max(1.20, min(Lx_avg, Ly_avg) * 0.32)
4647: cs_half_y = max(1.20, min(Lx_avg, Ly_avg) * 0.32)
4683: offset_grid_top  = max(1.8, slab_h * 0.10)
4684: offset_grid_left = max(1.8, slab_w * 0.10)
4767: # 0. Primary source: Directly register known deficit bays from btm_extra_spans
4769: if btm_extra_spans:
4771: for sp in btm_extra_spans:
4780: sp_w = sp.get("span_len", 0.0) if target_dir == "X" else sp.get("W_bay", 0.0)
4781: sp_h = sp.get("W_bay", 0.0) if target_dir == "X" else sp.get("span_len", 0.0)
4961: for j in range(len(Ly_spans)):
4962: for i in range(len(Lx_spans)):
4982: axes_x_info, axes_y_info = build_grid_axes_info(x_coords, y_coords, active_cols, active_x_labels, ac
4985: y_top_ext = y_slab_max + offset_grid_top
4992: x_left_ext = x_slab_min - offset_grid_left
5026: grid_idx = 1
5030: orig_id = f"C{grid_idx}"
5031: grid_idx += 1
5057: for i, lx in enumerate(Lx_spans):
5073: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.45, f"Total Lx = {slab_w:.2f} m",
5079: for j, ly in enumerate(Ly_spans):
5095: x_dim_tot + 0.45, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
5102: ax_plan.axis("off")
5106: ax_legend.axis("off")
5116: dir_txt_ar = "اتجاه المحور الأفقي X" if mode == "M11" else "اتجاه المحور الرأسي Y"
5194: Lx_spans, Ly_spans, cantilevers, ts_cm,
5198: btm_extra_spans=None,
5212: total_w = sum(Lx_spans) + cant_L + cant_R
5213: total_h = sum(Ly_spans) + cant_B + cant_T
5248: avg_Lx = float(np.mean(Lx_spans)) if Lx_spans else 5.0
5249: avg_Ly = float(np.mean(Ly_spans)) if Ly_spans else 5.0
5250: cap_cov_w = min(avg_Lx, avg_Ly) / 2.0
5254: active_btm_extras = [be for be in (btm_extra_spans or []) if isinstance(be, dict) and be.get("n_extr
5259: btm_ex_area = sum(be.get("span_len", 5.0) * avg_Ly for be in active_btm_extras)
5287: # Create 8-panel grid figure (4 rows x 2 columns)
5319: "notes": "Straight continuous bottom bar spanning across Ly spans perpendicular to M11."
5382: "density": "1 Chair / m² (Spaced @ 1.0 m grid)",
5393: ax.axis("off")
5534: Lx_spans, Ly_spans, cantilevers, ts_cm,
5548: for lx in Lx_spans:
5551: for ly in Ly_spans:
5568: offset_grid_top = max(2.2, slab_h * 0.11)
5569: offset_grid_left = max(2.2, slab_w * 0.11)
5607: for j in range(len(Ly_spans)):
5608: for i in range(len(Lx_spans)):
5620: axes_x_info, axes_y_info = build_grid_axes_info(x_coords, y_coords, active_cols, active_x_labels, ac
5623: y_top_ext = y_slab_max + offset_grid_top
5630: x_left_ext = x_slab_min - offset_grid_left
5676: grid_idx = 1
5680: orig_id = f"C{grid_idx}"
5681: grid_idx += 1
5804: # Adjacent span extensions (>= 0.25 L_max from column face into adjacent bays, bounded by slab edges
5805: lx_left = Lx_spans[ci - 1] if (ci > 0 and ci - 1 < len(Lx_spans)) else 0.0
5806: lx_right = Lx_spans[ci] if (ci < len(Lx_spans)) else 0.0
5807: ly_bot = Ly_spans[cj - 1] if (cj > 0 and cj - 1 < len(Ly_spans)) else 0.0
5808: ly_top = Ly_spans[cj] if (cj < len(Ly_spans)) else 0.0
5810: lx_max_adj = max(lx_left, lx_right, Lx_spans[0] if Lx_spans else 4.0)
5811: ly_max_adj = max(ly_bot, ly_top, Ly_spans[0] if Ly_spans else 4.0)
5828: Lx_cap = float(c_info.get("L_extra_x", round(cap_w, 2)))
5829: Ly_cap = float(c_info.get("L_extra_y", round(cap_h, 2)))
5856: if bpm_x == bpm_y and dia_x == dia_y and abs(Lx_cap - Ly_cap) < 0.08:
5857: tag_text = f"{bpm_x}Ø{dia_x} /m - L = {Lx_cap:.2f} m"
5860: f"X: {bpm_x}Ø{dia_x} /m - L = {Lx_cap:.2f} m\n"
5861: f"Y: {bpm_y}Ø{dia_y} /m - L = {Ly_cap:.2f} m"
5864: tag_text = f"{bpm_x}Ø{dia_x} /m - L = {Lx_cap:.2f} m"
5866: tag_text = f"{bpm_y}Ø{dia_y} /m - L = {Ly_cap:.2f} m"
5868: min_span_xy = min(min(Lx_spans) if Lx_spans else 4.0, min(Ly_spans) if Ly_spans else 4.0)
5869: font_sz = 8.2 if (cap_w < 2.2 or min_span_xy < 2.5) else 9.0
5870: pad_sz = 0.18 if (cap_w < 2.2 or min_span_xy < 2.5) else 0.22
5939: if cb_y1 > y_slab_max + offset_grid_top - bubble_radius - 0.15:
5940: penalty += 250.0 + (cb_y1 - (y_slab_max + offset_grid_top - bubble_radius)) * 200.0
5943: if cb_x0 < x_slab_min - offset_grid_left + bubble_radius + 0.15:
5994: for i, lx in enumerate(Lx_spans):
6011: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.38, f"Total Lx = {slab_w:.2f} m",
6019: for j, ly in enumerate(Ly_spans):
6036: x_dim_tot + 0.38, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
6043: ax_plan.axis("off")
6056: Lx_spans,
6057: Ly_spans,
6079: - As_total = Bottom Basic Mesh + Extra Bottom Bars in midspan (tension steel for Icr & Ie).
6080: - A's = Top Basic Mesh (compression steel in midspan for creep factor lambda = xi / (1 + 50*mu')).
6087: for lx in Lx_spans:
6090: for ly in Ly_spans:
6093: n_x = len(Lx_spans)
6094: n_y = len(Ly_spans)
6136: span_x = Lx_spans[i]
6137: span_y = Ly_spans[j]
6141: Ln_x = max(1.0, span_x - bc_m)
6142: Ln_y = max(1.0, span_y - tc_m)
6270: "span_x": span_x,
6271: "span_y": span_y,
6338: # Transformed neutral axis
6732: ax.grid(True, linestyle=":", alpha=0.35, color="#94a3b8")
6866: ax.axis("off")
6869: f"Detailed Midspan Cross Section & Rebar Arrangement — {panel_dict['Panel ID']} ({panel_dict['Bay La
6882: Lx_spans,
6883: Ly_spans,
6905: for lx in Lx_spans:
6908: for ly in Ly_spans:
6925: offset_grid_top = max(2.2, slab_h * 0.11)
6926: offset_grid_left = max(2.2, slab_w * 0.11)
6954: x_grid = np.linspace(x_slab_min, x_slab_max, nx_mesh)
6955: y_grid = np.linspace(y_slab_min, y_slab_max, ny_mesh)
6956: X_m, Y_m = np.meshgrid(x_grid, y_grid)
6967: span_x = x1 - x0
6968: span_y = y1 - y0
6969: sin_x = np.sin(np.pi * np.clip((X_m - x0) / max(0.1, span_x), 0.0, 1.0))
6970: sin_y = np.sin(np.pi * np.clip((Y_m - y0) / max(0.1, span_y), 0.0, 1.0))
6979: for j in range(len(Ly_spans)):
6980: for i in range(len(Lx_spans)):
7048: for j in range(len(Ly_spans)):
7049: for i in range(len(Lx_spans)):
7066: axes_x_info, axes_y_info = build_grid_axes_info(x_coords, y_coords, active_cols, active_x_labels, ac
7069: y_top_ext = y_slab_max + offset_grid_top
7076: x_left_ext = x_slab_min - offset_grid_left
7172: span_x_val = p.get("span_x", max(1.0, (p.get("x1", xm + 2.0) - p.get("x0", xm - 2.0))))
7173: span_y_val = p.get("span_y", max(1.0, (p.get("y1", ym + 2.0) - p.get("y0", ym - 2.0))))
7180: # Dynamic vertical stagger offset scaled to span height
7181: # Typically 18% to 22% of span height, constrained between 0.35m and 1.10m
7182: offset_y = min(1.10, max(0.35, span_y_val * 0.20))
7185: # Adaptive typography based on span size
7186: if min(span_x_val, span_y_val) < 2.5:
7189: elif min(span_x_val, span_y_val) < 3.8:
7227: dim_y2 = dim_y1 - 1.2 if (len(Lx_spans) > 1 or cant_left > 0 or cant_right > 0) else dim_y1
7237: for i, lx in enumerate(Lx_spans):
7253: if len(Lx_spans) > 1 or cant_left > 0 or cant_right > 0:
7257: ax_plan.text((x_slab_min + x_slab_max) / 2.0, dim_y2 - 0.38, f"Total Lx = {slab_w:.2f} m", ha="cente
7261: dim_x2 = dim_x1 + 1.2 if (len(Ly_spans) > 1 or cant_bottom > 0 or cant_top > 0) else dim_x1
7271: for j, ly in enumerate(Ly_spans):
7287: if len(Ly_spans) > 1 or cant_bottom > 0 or cant_top > 0:
7291: ax_plan.text(dim_x2 + 0.38, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m", ha="left"
7296: ax_plan.axis("off")
7315: Lx_spans,
7316: Ly_spans,
7336: for lx in Lx_spans:
7339: for ly in Ly_spans:
7356: offset_grid_top = max(2.2, slab_h * 0.11)
7357: offset_grid_left = max(2.2, slab_w * 0.11)
7391: x_grid = np.linspace(x_slab_min, x_slab_max, nx_mesh)
7392: y_grid = np.linspace(y_slab_min, y_slab_max, ny_mesh)
7393: X_m, Y_m = np.meshgrid(x_grid, y_grid)
7396: avg_span = (np.mean(Lx_spans) + np.mean(Ly_spans)) / 2.0 if len(Lx_spans) > 0 else 5.0
7397: sigma_punch = max(0.55, avg_span * 0.14)
7413: for j in range(len(Ly_spans)):
7414: for i in range(len(Lx_spans)):
7475: for j in range(len(Ly_spans)):
7476: for i in range(len(Lx_spans)):
7493: axes_x_info, axes_y_info = build_grid_axes_info(x_coords, y_coords, active_cols, active_x_labels, ac
7496: y_top_ext = y_slab_max + offset_grid_top
7503: x_left_ext = x_slab_min - offset_grid_left
7516: for i in range(len(Lx_spans)):
7521: ax_plan.text((x0 + x1)/2.0, dim_y - 0.35, f"{Lx_spans[i]:.2f} m", color="#1e293b", fontsize=13.5, we
7537: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.45, f"Total Lx = {slab_w:.2f} m",
7547: for j in range(len(Ly_spans)):
7552: ax_plan.text(dim_x + 0.35, (y0 + y1)/2.0, f"{Ly_spans[j]:.2f} m", color="#1e293b", fontsize=13.5, we
7568: x_dim_tot + 0.45, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
7706: ax_plan.axis("off")
7711: ax_legend.axis("off")
7942: ax_plan.axis("off")
7952: ax_spec.axis("off")
8006: ax_sec.axis("off")
8408: ax_spec.axis("off")
8486: Lx_spans, Ly_spans, cantilevers, ts_cm,
8487: btm_extra_spans, cant_rft_list,
8504: for lx in Lx_spans:
8507: for ly in Ly_spans:
8524: offset_grid_top = max(2.2, slab_h * 0.11)
8525: offset_grid_left = max(2.2, slab_w * 0.11)
8564: for j in range(len(Ly_spans)):
8565: for i in range(len(Lx_spans)):
8578: axes_x_info, axes_y_info = build_grid_axes_info(x_coords, y_coords, active_cols, active_x_labels, ac
8581: y_top_ext = y_slab_max + offset_grid_top
8588: x_left_ext = x_slab_min - offset_grid_left
8631: grid_idx = 1
8635: orig_id = f"C{grid_idx}"
8636: grid_idx += 1
8666: b for b in (btm_extra_spans or [])
8681: L_ext_raw = float(b_info.get("L_extra", 0.68 * span_len_b))
8682: L_ext = min(L_ext_raw, 0.72 * span_len_b)
8733: f_sz = 9.5 if (L_ext < 2.2 or min(Lx_spans) < 2.0) else 10.8
8734: p_sz = 0.22 if (L_ext < 2.2 or min(Lx_spans) < 2.0) else 0.28
8824: for i, lx in enumerate(Lx_spans):
8841: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.38, f"Total Lx = {slab_w:.2f} m",
8849: for j, ly in enumerate(Ly_spans):
8866: x_dim_tot + 0.38, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
8873: ax_plan.axis("off")
8877: y_badge_c = y_slab_max + offset_grid_top + bubble_radius * 2 + 1.25
8907: Lx_spans, Ly_spans, cantilevers, ts_cm,
8926: for lx in Lx_spans:
8929: for ly in Ly_spans:
8946: offset_grid_top = max(2.2, slab_h * 0.11)
8947: offset_grid_left = max(2.2, slab_w * 0.11)
8986: for j in range(len(Ly_spans)):
8987: for i in range(len(Lx_spans)):
9000: axes_x_info, axes_y_info = build_grid_axes_info(x_coords, y_coords, active_cols, active_x_labels, ac
9003: y_top_ext = y_slab_max + offset_grid_top
9010: x_left_ext = x_slab_min - offset_grid_left
9053: grid_idx = 1
9057: orig_id = f"C{grid_idx}"
9058: grid_idx += 1
9151: f_sz = 9.5 if (L_ext < 2.2 or min(Lx_spans) < 2.0) else 10.5
9152: p_sz = 0.22 if (L_ext < 2.2 or min(Lx_spans) < 2.0) else 0.28
9329: for i, lx in enumerate(Lx_spans):
9346: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.38, f"Total Lx = {slab_w:.2f} m",
9354: for j, ly in enumerate(Ly_spans):
9371: x_dim_tot + 0.38, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
9378: ax_plan.axis("off")
9382: y_badge_c = y_slab_max + offset_grid_top + bubble_radius * 2 + 1.25
9411: Lx_spans, Ly_spans, cantilevers, ts_cm,
9415: btm_extra_spans=None,
9436: for lx in Lx_spans:
9440: for ly in Ly_spans:
9458: offset_grid_top = max(1.8, slab_h * 0.10)
9459: offset_grid_left = max(1.8, slab_w * 0.10)
9505: for j in range(len(Ly_spans)):
9506: for i in range(len(Lx_spans)):
9520: y_top_ext = y_slab_max + offset_grid_top
9527: x_left_ext = x_slab_min - offset_grid_left
9539: grid_idx = 1
9543: orig_id = f"C{grid_idx}"
9544: grid_idx += 1
9570: mid_i = len(Lx_spans) // 2
9571: mid_j = len(Ly_spans) // 2
9572: bm_x0 = x_coords[mid_i] + 0.3 * Lx_spans[mid_i]
9573: bm_y0 = y_coords[mid_j] + 0.3 * Ly_spans[mid_j]
9588: top_i = 0 if len(Lx_spans) > 1 else mid_i
9589: top_j = 0 if len(Ly_spans) > 1 else mid_j
9590: tm_x0 = x_coords[top_i] + 0.5 * Lx_spans[top_i]
9591: tm_y0 = y_coords[top_j] + 0.5 * Ly_spans[top_j]
9614: adj_lx = Lx_spans[min(ci, len(Lx_spans)-1)]
9615: adj_ly = Ly_spans[min(cj, len(Ly_spans)-1)]
9646: for b_info in (btm_extra_spans or []):
9651: L_ext = min(float(b_info.get("L_extra", Ln * 0.68)), 0.72 * span_len)
9659: for i in range(len(Lx_spans)):
9660: for j in range(len(Ly_spans)):
9735: for i, lx in enumerate(Lx_spans):
9752: (x_slab_min + x_slab_max) / 2.0, y_dim_tot - 0.35, f"Total Lx = {slab_w:.2f} m",
9760: for j, ly in enumerate(Ly_spans):
9777: x_dim_tot + 0.35, (y_slab_min + y_slab_max) / 2.0, f"Total Ly = {slab_h:.2f} m",
9787: ax_plan.axis("off")
9793: ax_legend.axis("off")
10112: def calculate_punching_shear(columns, Lx_spans, Ly_spans, cantilevers, Wu, d_cm, Fcu, Fy=4000, ts_cm
10123: n_x = len(Lx_spans)
10124: n_y = len(Ly_spans)
10140: ltx = cant_L + Lx_spans[0] / 2.0
10142: ltx = Lx_spans[-1] / 2.0 + cant_R
10144: ltx = (Lx_spans[min(max(0, i - 1), len(Lx_spans)-1)] + Lx_spans[min(i, len(Lx_spans)-1)]) / 2.0
10147: lty = cant_B + Ly_spans[0] / 2.0
10149: lty = Ly_spans[-1] / 2.0 + cant_T
10151: lty = (Ly_spans[min(max(0, j - 1), len(Ly_spans)-1)] + Ly_spans[min(j, len(Ly_spans)-1)]) / 2.0
10187: "Grid": f"{col['grid_x']} - {col['grid_y']}",
10265: Lx_spans,
10266: Ly_spans,
10292: for lx in Lx_spans:
10295: for ly in Ly_spans:
10312: # Adjacent spans in X and Y around this column
10314: if i > 0 and (i - 1) < len(Lx_spans):
10315: adj_lx_list.append(float(Lx_spans[i - 1]))
10316: if i < len(Lx_spans):
10317: adj_lx_list.append(float(Lx_spans[i]))
10318: lx_adj = max(adj_lx_list) if adj_lx_list else float(Lx_spans[min(max(0, i), len(Lx_spans) - 1)])
10321: if j > 0 and (j - 1) < len(Ly_spans):
10322: adj_ly_list.append(float(Ly_spans[j - 1]))
10323: if j < len(Ly_spans):
10324: adj_ly_list.append(float(Ly_spans[j]))
10325: ly_adj = max(adj_ly_list) if adj_ly_list else float(Ly_spans[min(max(0, j), len(Ly_spans) - 1)])
10339: is_ext_x = (i == 0) or (i >= len(Lx_spans))
10340: is_ext_y = (j == 0) or (j >= len(Ly_spans))
10348: if math.hypot(cx - eb.get("mid_x", 0), cy - eb.get("mid_y", 0)) <= eb.get("span_len", 6.0) * 0.75:
10431: Lx_extra = XZ.round_up_length(max(0.8, x_bar_1 - x_bar_0))
10432: Ly_extra = XZ.round_up_length(max(0.8, y_bar_1 - y_bar_0))
10448: tag_lbl_x = f"{bpm_x}Ø{eff_cap_dia} /m - L = {Lx_extra:.2f} m" if bpm_x > 0 else ""
10449: tag_lbl_y = f"{bpm_y}Ø{eff_cap_dia} /m - L = {Ly_extra:.2f} m" if bpm_y > 0 else ""
10453: f"{max(bpm_x, bpm_y)}Ø{eff_cap_dia} /m - L = {max(Lx_extra, Ly_extra):.2f} m "
10454: f"(X: {bpm_x}Ø{eff_cap_dia} /m, L={Lx_extra:.2f}m | Y: {bpm_y}Ø{eff_cap_dia} /m, L={Ly_extra:.2f}m)"
10465: "grid": f"{col['grid_x']} - {col['grid_y']}",
10489: "L_extra": max(Lx_extra, Ly_extra),
10490: "L_extra_x": Lx_extra,
10491: "L_extra_y": Ly_extra,
10557: def calculate_boq(Lx_spans, Ly_spans, cantilevers, ts_cm, mesh_btm_n, mesh_btm_dia, mesh_top_n, mesh
10567: total_w = sum(Lx_spans) + cant_L + cant_R
10568: total_h = sum(Ly_spans) + cant_B + cant_T
10616: if btm_extra_spans:
10617: for be in btm_extra_spans:
10871: '<span dir="ltr" style="font-size: 15px; color: #bfdbfe; font-weight: 600;">(ECP 203 Structural Desi
10874: 'شرح هندسي تفصيلي لمسار انتقال الأحمال <span dir="ltr" style="font-weight:700; color:#60a5fa;">(Load
10880: '1️⃣ فلسفة حساب ردود أفعال وأحمال الأعمدة <span dir="ltr" style="font-size:14px; color:#3b82f6;">(Co
10884: '<b>رد فعل السقف الواحد <span dir="ltr" style="color:#1d4ed8;">Pu(1F)</span>:</b> '
10885: 'يُحسب رد الفعل الرأسي الصافي المنقول من البلاطة اللاكمرية لكل عمود بدقة متناهية بناءً على مساحة تأث
10889: 'حيث يمثل <span dir="ltr" style="font-weight:700;">Wu(Slab)</span> الحمل التصميمي الأقصى للمتر المرب
10892: '<b>الحمل الرأسي التراكمي لعدد <span dir="ltr">N</span> طابق <span dir="ltr" style="color:#1d4ed8;">
10899: '<b>معامل أمان ووزن الأعمدة <span dir="ltr" style="font-weight:700;">(Safety Factor & Columns Weight
10900: 'المعامل المدخل (الافتراضي <span dir="ltr">1.10</span> أي إضافة <span dir="ltr">10%</span>) يغطي هند
10907: '2️⃣ فلسفة تصميم قطاعات وتسليح الأعمدة <span dir="ltr" style="font-size:14px; color:#16a34a;">(Colum
10911: '<b>الأبعاد الخرسانية للعمود <span dir="ltr" style="font-weight:700;">(Column Dimensions b × t)</spa
10912: 'يتم تصميم أبعاد القطاع الخرساني (العرض <span dir="ltr">bc</span> والعمق <span dir="ltr">tc</span>) 
10915: '<b>حديد التسليح الطولي والكانات <span dir="ltr" style="font-weight:700;">(Longitudinal Rebar As & S
10923: '3️⃣ فلسفة تصميم الأساسات والقواعد <span dir="ltr" style="font-size:14px; color:#d97706;">(Foundatio
10927: '<b>منسوب التأسيس <span dir="ltr" style="font-weight:700;">(Foundation Level)</span>:</b> '
10931: '<b>القواعد المنفصلة <span dir="ltr" style="font-weight:700;">(Isolated Footings F1, F2, F3)</span>:
10936: 'تدقيق أبعاد الخرسانة العادية والمسلحة للتأكد من عدم تجاوز جهد التربة الصافي المسموح به <span dir="l
10939: '<b>القواعد المشتركة والشدادات <span dir="ltr" style="font-weight:700;">(Combined Footings & Strap B
10940: 'في حالات تداخل القواعد أو قواعد الجار <span dir="ltr">(Property Line)</span>، يتم تصميم قواعد مشترك
10947: '4️⃣ فلسفة حصر الكميات والمواد الإنشائية <span dir="ltr" style="font-size:14px; color:#7c3aed;">(Qua
10960: '<td style="padding: 10px 14px; font-weight: 700; color: #0f172a;">سقف الدور النمطي الواحد <span dir
10962: '<td style="padding: 10px 14px; color: #334155;">تحديد كمية ومواد "صبة السقف الواحد" للطلبيات الميدا
10965: '<td style="padding: 10px 14px; font-weight: 700; color: #0f172a;">أسقف المبنى المتكررة <span dir="l
10970: '<td style="padding: 10px 14px; font-weight: 700; color: #0f172a;">أعمدة المبنى <span dir="ltr">(Bui
10975: '<td style="padding: 10px 14px; font-weight: 700; color: #0f172a;">أساسات وسملات المبنى <span dir="l
10977: '<td style="padding: 10px 14px; color: #334155;">تُصب مرة واحدة في منسوب التأسيس لخدمة وحمل كامل أدو
10980: '<td style="padding: 11px 14px; font-weight: 900; color: #1e3a8a;">الإجمالي الشامل للمبنى <span dir=
11015: Lx_spans: list,
11016: Ly_spans: list,
11046: adj_lx = Lx_spans[min(i, len(Lx_spans) - 1)] if Lx_spans else 5.0
11047: adj_ly = Ly_spans[min(j, len(Ly_spans) - 1)] if Ly_spans else 5.0
11059: shift_x = FS_SHIFT_X_OPTIONS[0]  # متمركز على المحور
11070: shift_y = FS_SHIFT_Y_OPTIONS[0]  # متمركز على المحور
11079: def _ensure_fs_selective_mode_initialized(Lx_spans: list, Ly_spans: list) -> tuple:
11086: n_xi = len(Lx_spans) + 1
11087: n_yj = len(Ly_spans) + 1
11111: Lx_spans: list,
11112: Ly_spans: list,
11127: n_xi = len(Lx_spans) + 1
11128: n_yj = len(Ly_spans) + 1
11129: cfg, placed_list, removed_list = _ensure_fs_selective_mode_initialized(Lx_spans, Ly_spans)
11166: ti, tj, n_xi, n_yj, Lx_spans, Ly_spans, cantilevers,
11212: Lx_spans: list,
11213: Ly_spans: list,
11222: for lx in Lx_spans:
11225: for ly in Ly_spans:
11292: targets_ij, Lx_spans, Ly_spans, cantilevers
11314: def remap_columns_after_axis_insertion(
11315: axis_dir: str,
11316: span_index: int,
11327: Lx_spans: list = None,
11328: Ly_spans: list = None,
11332: Safely re-index and preserve columns after inserting a new intermediate axis at span_index.
11334: - Shifts existing columns located at or after the insertion point by +1 on the inserted axis.
11335: - Zero auto-columns on the newly inserted axis: all new intersections are strictly empty by default.
11339: if axis_dir == "X":
11340: inserted_idx = span_index + 1
11348: inserted_idx = span_index + 1
11424: if not isinstance(tr, dict) and Lx_spans and Ly_spans:
11426: new_i, new_j, new_nx, new_ny, Lx_spans, Ly_spans, cantilevers or {}
11455: "shift_x": (tr or {}).get("shift_x", "متمركز على المحور (Centered)"),
11456: "shift_y": (tr or {}).get("shift_y", "متمركز على المحور (Centered)"),
11472: # Any new grid intersections are strictly empty by default (isActive: false / hasColumn: false)
11486: axis_dir: str,  # "X" (splits an Lx span, adds a vertical Y axis) or "Y" (splits an Ly span, adds a 
11487: span_index: int,
11489: Lx_spans: list,
11490: Ly_spans: list,
11494: Subdivide an existing span Li into two consecutive spans [d1, d2] where d2 = Li - d1,
11495: inserting an intermediate structural grid axis, incrementing total spans and axes by +1,
11502: if axis_dir == "X":
11503: if span_index < 0 or span_index >= len(Lx_spans):
11504: st.error("Invalid span index.")
11506: old_span = float(Lx_spans[span_index])
11515: new_spans = list(Lx_spans)
11516: new_spans[span_index] = offset_d1
11517: new_spans.insert(span_index + 1, d2)
11518: inserted_col_idx = span_index + 1
11520: n_lx = len(Lx_spans)
11521: n_ly = len(Ly_spans)
11541: new_removed, new_placed, new_col_props, new_col_trans, new_edge_cols, new_nx, new_ny = remap_columns
11542: axis_dir="X",
11543: span_index=span_index,
11554: Lx_spans=new_spans,
11555: Ly_spans=Ly_spans,
11559: new_n_lx = len(new_spans)
11564: for idx_s, sp_val in enumerate(new_spans):
11591: if pi < span_index:
11593: elif pi == span_index:
11605: for lx in Lx_spans:
11608: for lx in new_spans:
11620: if b_copy.get("axis_type") == "Y":
11621: old_ax_idx = b_copy.get("axis_index", 1) - 1
11624: b_copy["axis_index"] = new_ax_idx + 1
11625: b_copy["axis_name"] = f"Y{new_ax_idx + 1}"
11628: b_copy["p1_grid"] = bp1_g
11629: b_copy["p2_grid"] = bp2_g
11635: new_spans, Ly_spans,
11661: else:  # axis_dir == "Y"
11662: if span_index < 0 or span_index >= len(Ly_spans):
11663: st.error("Invalid span index.")
11665: old_span = float(Ly_spans[span_index])
11674: new_spans = list(Ly_spans)
11675: new_spans[span_index] = offset_d1
11676: new_spans.insert(span_index + 1, d2)
11677: inserted_row_idx = span_index + 1
11679: n_lx = len(Lx_spans)
11680: n_ly = len(Ly_spans)
11700: new_removed, new_placed, new_col_props, new_col_trans, new_edge_cols, new_nx, new_ny = remap_columns
11701: axis_dir="Y",
11702: span_index=span_index,
11713: Lx_spans=Lx_spans,
11714: Ly_spans=new_spans,
11718: new_n_ly = len(new_spans)
11722: for idx_s, sp_val in enumerate(new_spans):
11749: if pj < span_index:
11751: elif pj == span_index:
11762: for ly in Ly_spans:
11765: for ly in new_spans:
11777: if b_copy.get("axis_type") == "X":
11778: old_ax_idx = b_copy.get("axis_index", 1) - 1
11781: b_copy["axis_index"] = new_ax_idx + 1
11782: b_copy["axis_name"] = f"X{new_ax_idx + 1}"
11785: b_copy["p1_grid"] = bp1_g
11786: b_copy["p2_grid"] = bp2_g
11792: Lx_spans, new_spans,
11836: if axis_dir == "X":
11837: st.session_state[f"{prefix}w_fs_n_lx_v{grid_ver}"] = int(new_n_lx)
11839: for idx_s, sp_val in enumerate(new_spans):
11840: st.session_state[f"{prefix}w_fs_lx_{idx_s}_v{grid_ver}"] = float(sp_val)
11843: st.session_state[f"{prefix}w_fs_n_ly_v{grid_ver}"] = int(new_n_ly)
11845: for idx_s, sp_val in enumerate(new_spans):
11846: st.session_state[f"{prefix}w_fs_ly_{idx_s}_v{grid_ver}"] = float(sp_val)
11849: # Clean up obsolete previous versioned keys (excluding _fs_grid_ver itself)
11854: st.session_state["_fs_preview_axis"] = None
11857: axis_name = f"Y{span_index + 2}" if axis_dir == "X" else f"X{span_index + 2}"
11858: st.toast(f"✅ تم تقسيم البحر بنجاح وإدراج المحور {axis_name} مع الحفاظ التام على شبكة الأعمدة والكمرا
11863: def _execute_fs_insert_axis(
11864: axis_dir: str,
11868: Lx_spans: list,
11869: Ly_spans: list,
11872: """Backwards compatibility adapter pointing to split_span."""
11874: axis_dir=axis_dir,
11875: span_index=ref_idx,
11877: Lx_spans=Lx_spans,
11878: Ly_spans=Ly_spans,
11881: def _has_adjacent_backspan_beam(
11942: def _find_beam_spans_on_line(
11962: cy = float(c.get("center_y", c.get("y", c.get("grid_y_m", 0.0))))
11963: cx = float(c.get("center_x", c.get("x", c.get("grid_x_m", 0.0))))
12009: cx = float(c.get("center_x", c.get("x", c.get("grid_x_m", 0.0))))
12010: cy = float(c.get("center_y", c.get("y", c.get("grid_y_m", 0.0))))
12071: axis_coords = x_coords if is_horizontal else y_coords
12081: right_grid_pts = [g for g in axis_coords if g >= max(click_pos - 0.15, left_s[-1]["coord"] + 0.50)]
12082: free_coord = right_grid_pts[0] if right_grid_pts else max(click_pos, left_s[-1]["coord"] + 1.0)
12088: left_grid_pts = [g for g in axis_coords if g <= min(click_pos + 0.15, right_s[0]["coord"] - 0.50)]
12089: free_coord = left_grid_pts[-1] if left_grid_pts else min(click_pos, right_s[0]["coord"] - 1.0)
12114: prev_g_list = [g for g in axis_coords if g < first_s["coord"] - 0.50]
12118: cand_g_left = [g for g in axis_coords if (sel_min - tol) <= g <= (first_s["coord"] - 0.50)]
12136: next_g_list = [g for g in axis_coords if g > last_s["coord"] + 0.50]
12140: cand_g_right = [g for g in axis_coords if (last_s["coord"] + 0.50) <= g <= (sel_max + tol)]
12176: "span_m": abs(s2["coord"] - s1["coord"]),
12182: def _execute_fs_add_beam_box(data: dict, Lx_spans: list, Ly_spans: list, cantilevers: dict, trigger_
12195: for lx in Lx_spans:
12198: for ly in Ly_spans:
12244: dist_to_axis = abs(line_coord - ((wy1 + wy2) / 2.0))
12250: dist_to_axis = abs(line_coord - ((wx1 + wx2) / 2.0))
12252: if dist_to_axis > 0.65:
12283: Lx_spans, Ly_spans, bc_cm=col_w_cm, tc_cm=col_d_cm,
12325: spans, chosen_sups, _ = _find_beam_spans_on_line(
12354: # فحص كمرات الكابولي والتأكد من تحقق شرط الركيزة الرأسية (عمود/حائط) والاتصال المباشر بكمرة مجاورة م
12364: has_backspan = _has_adjacent_backspan_beam(
12378: f"2. اتصالها المباشر بكمرة داخلية مجاورة مستمرة على نفس المحور الهندسي لتأمين التثبيت التام (Full Mo
12421: axis_idx = min(range(len(y_coords)), key=lambda idx: abs(y_coords[idx] - line_coord))
12422: des["axis_type"] = "X"
12423: des["axis_index"] = axis_idx + 1
12424: des["axis_name"] = f"X{axis_idx + 1}"
12426: axis_idx = min(range(len(x_coords)), key=lambda idx: abs(x_coords[idx] - line_coord))
12427: des["axis_type"] = "Y"
12428: des["axis_index"] = axis_idx + 1
12429: des["axis_name"] = f"Y{axis_idx + 1}"
12462: def _execute_fs_add_drop_beam(data: dict, Lx_spans: list, Ly_spans: list, cantilevers: dict, trigger
12467: _execute_fs_add_beam_box(data, Lx_spans, Ly_spans, cantilevers, trigger_rerun=trigger_rerun)
12509: def _handle_fs_sync_payload(Lx_spans: list, Ly_spans: list, cantilevers: dict, payload_str: str = No
12533: _handle_fs_sync_payload(Lx_spans, Ly_spans, cantilevers, payload_str=_q_item)
12608: _execute_fs_add_beam_box(data, Lx_spans, Ly_spans, cantilevers, trigger_rerun=True)
12618: _execute_fs_add_drop_beam(data, Lx_spans, Ly_spans, cantilevers, trigger_rerun=True)
12631: data, Lx_spans, Ly_spans, cantilevers, trigger_rerun=False
12662: box_hint = "اسحب صندوقاً بالماوس على المحور لتحديد مسار وبحور الكمرة الساقطة (اضغط Esc للإلغاء)"
12670: box_hint = "اسحب صندوقاً بالماوس أو انقر مباشرة على تقاطع المحورين لإسقاط العمود فوراً"
12736: snaps_list.append({"x": float(xv), "y": float(yv), "type": "grid", "label": f"محور Y{i_x+1} × X{j_y+
12770: snaps_list.append({"x": x_min_s, "y": float(yv), "type": "cantilever_edge", "label": f"🌐 نهاية كابول
12772: snaps_list.append({"x": x_max_s, "y": float(yv), "type": "cantilever_edge", "label": f"🌐 نهاية كابول
12775: snaps_list.append({"x": float(xv), "y": y_min_s, "type": "cantilever_edge", "label": f"🌐 نهاية كابول
12777: snaps_list.append({"x": float(xv), "y": y_max_s, "type": "cantilever_edge", "label": f"🌐 نهاية كابول
12801: snaps_list.append({"x": float(xv), "y": by, "type": "beam_grid", "label": f"تقاطع كمرة {bid_v} مع مح
12809: snaps_list.append({"x": bx, "y": float(yv), "type": "beam_grid", "label": f"تقاطع كمرة {bid_v} مع مح
12844: span_x = max(x_coords) - min(x_coords) if x_coords else 10.0
12845: span_y = max(y_coords) - min(y_coords) if y_coords else 10.0
12846: ratio = (span_y + 3.0) / max(span_x + 3.0, 1.0)
12853: <span style="font-size:1.15rem;">{banner_icon}</span>
12854: <span>{box_hint}</span>
13171: <div id="selection-box"><div id="selection-badge">اسحب لتحديد تقاطع المحورين</div></div>
13556: selBadge.textContent = 'اسحب لتحديد مسار وبحور الكمرة على المحور...';
13559: selBadge.textContent = 'اسحب أو انقر لتحديد تقاطع المحورين...';
13599: const spanDist = Math.hypot(pC.x - pS.x, pC.y - pS.y);
13607: const axisIdx = bboxInfo.ys.indexOf(closeY);
13608: const axisName = 'X' + (axisIdx >= 0 ? (axisIdx + 1) : '');
13609: selBadge.innerHTML = '📏 إسقاط كمرة على المحور ' + axisName + ' (طول التحديد: ' + spanDist.toFixed(2)
13618: const axisIdx = bboxInfo.xs.indexOf(closeX);
13619: const axisName = 'Y' + (axisIdx >= 0 ? (axisIdx + 1) : '');
13620: selBadge.innerHTML = '📏 إسقاط كمرة على المحور ' + axisName + ' (طول التحديد: ' + spanDist.toFixed(2)
13829: Lx_spans: list,
13830: Ly_spans: list,
13863: for lx in Lx_spans:
13866: for ly in Ly_spans:
13883: c["id"]: f"{c['id']} ({c.get('grid_x', '')} × {c.get('grid_y', '')} — {c.get('width_cm', _bc_col):.0
14069: "shift_x": tgt_col_obj.get("shift_x", "متمركز على المحور (Centered)"),
14070: "shift_y": tgt_col_obj.get("shift_y", "متمركز على المحور (Centered)"),
14122: tgt_col_obj.get("grid_x_m", tgt_col_obj.get("x", 0.0)),
14123: tgt_col_obj.get("grid_y_m", tgt_col_obj.get("y", 0.0)),
14129: gx_col_e = tgt_col_obj.get("grid_x_m", tgt_col_obj.get("x", 0.0))
14130: gy_col_e = tgt_col_obj.get("grid_y_m", tgt_col_obj.get("y", 0.0))
14152: is_grid_left_e   = (gx_col_e <= min_x_e + tol_e)
14153: is_grid_right_e  = (gx_col_e >= max_x_e - tol_e)
14154: is_grid_bottom_e = (gy_col_e <= min_y_e + tol_e)
14155: is_grid_top_e    = (gy_col_e >= max_y_e - tol_e)
14317: _edge_badge_html = "<span style='color:#64748b;'>⚪ عمود داخلي (Interior Column)</span>"
14320: _edge_badge_html = "<span style='color:#2563eb;'>⏳ بانتظار اختيار اتجاه الجار</span>"
14322: _edge_badge_html = f"<span style='color:#db2777;font-weight:800;'>🌸 عمود جار ({edit_sel_edge_dir}) —
14324: _edge_badge_html = "<span style='color:#b91c1c;'>⚠️ غير محقق لشرط بروز الجار (≤ 6 سم)</span>"
14326: _edge_badge_html = "<span style='color:#64748b;'>⚪ عمود محيطي غير ملاصق لجار</span>"
14331: 📐 القطاع الحالي: <span style='color:#0f766e;'><bdi dir='ltr'>{col_geom_prev['width_cm']:.0f} × {col_
14332: &nbsp;|&nbsp; 📍 الترحيل: <span style='color:#b45309;'><bdi dir='ltr'>X = {_off_x_txt} , Y = {_off_y_
14413: f"<b>{cid}</b> <span style='font-size:12px;color:#991b1b;'>({ _active_cols[active_col_ids.index(cid)
14441: cfg_obj, placed_list, _ = _ensure_fs_selective_mode_initialized(Lx_spans, Ly_spans)
14767: Lx_spans, Ly_spans, cantilevers,
14795: preview_axis=st.session_state.get("_fs_preview_axis"),
14945: div[data-testid="stExpander"] details summary span,
14949: div[data-testid="stExpander"] summary span,
14953: .streamlit-expanderHeader span,
14996: div[data-testid="stExpander"] summary span,
15193: div[class*="btn_show_design_philosophy_top"] button span,
15194: div[class*="btn_show_design_philosophy_step2"] button span,
15195: div[class*="btn_design_philosophy_boq"] button span {
15227: Lx_spans = []
15228: Ly_spans = []
15235: <span style="font-size: 26px;">📥</span>
15236: <span>مدخلات وأبعاد ومواصفات السقف والأحمال (Flat Slab Design & Geometry Inputs)</span>
15260: "Number of Lx spans (horizontal — between vertical axes)",
15262: key=f"{prefix}w_fs_n_lx_v{grid_ver}",
15267: "Number of Ly spans (vertical — between horizontal axes)",
15269: key=f"{prefix}w_fs_n_ly_v{grid_ver}",
15274: cur_lx_spans = []
15276: w_k = f"{prefix}w_fs_lx_{k}_v{grid_ver}"
15278: cur_lx_spans.append(float(st.session_state[w_k]))
15280: cur_lx_spans.append(float(S.cfg_val(f"fs_lx_{k}", 6.0)))
15282: cur_ly_spans = []
15284: w_k = f"{prefix}w_fs_ly_{k}_v{grid_ver}"
15286: cur_ly_spans.append(float(st.session_state[w_k]))
15288: cur_ly_spans.append(float(S.cfg_val(f"fs_ly_{k}", 6.0)))
15290: # Absolute axis coordinates recalculation
15292: for lx in cur_lx_spans:
15297: for ly in cur_ly_spans:
15301: # ── X-Direction Spans (Lx) ──
15306: <span style='font-size: 15px; font-weight: 700; color: #ffffff;'>
15307: 📏 بحور اتجاه X (Lx Spans — بين المحاور الرأسية Y)
15309: <span style='font-size: 12.5px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189
15317: Lx_spans = []
15320: span_val = cur_lx_spans[i]
15325: label_str = f"Lx{i+1} ({y_start} - {y_end})"
15326: w_key = f"{prefix}w_fs_lx_{i}_v{grid_ver}"
15333: help=f"البحر Lx{i+1} بين المحورين {y_start} ({coord_start:.2f}م) و {y_end} ({coord_end:.2f}م)"
15335: Lx_spans.append(val)
15337: with st.popover("✂️ Split Axis", use_container_width=True, help=f"تقسيم البحر Lx{i+1} وإدراج محور رأ
15338: st.markdown(f"<div dir='rtl'><b>✂️ تقسيم البحر Lx{i+1} ({y_start} - {y_end})</b><br><small>الطول الح
15342: f"المسافة d₁ من المحور {y_start} (م):",
15347: key=f"{prefix}split_d1_lx_{i}_v{grid_ver}",
15348: help=f"المسافة من المحور {y_start} إلى المحور الرأسي الجديد."
15351: new_axis_coord = coord_start + float(d1_input)
15356: • البحر Lx{i+1} الجديد: <b>{d1_input:.2f} م</b> ({y_start} ➔ المحور الجديد عند {new_axis_coord:.2f}م
15357: • البحر Lx{i+2} الجديد: <b>{d2_calc:.2f} م</b> (المحور الجديد ➔ {y_end} عند {coord_end:.2f}م)<br>
15363: if st.button("🚀 تأكيد التقسيم وإدراج المحور", key=f"{prefix}btn_confirm_split_lx_{i}_v{grid_ver}", t
15364: active_lx = list(cur_lx_spans)
15366: active_ly = list(cur_ly_spans)
15367: split_span("X", i, float(d1_input), active_lx, active_ly, trigger_rerun=True)
15369: # ── Y-Direction Spans (Ly) ──
15374: <span style='font-size: 15px; font-weight: 700; color: #ffffff;'>
15375: 📏 بحور اتجاه Y (Ly Spans — بين المحاور الأفقية X)
15377: <span style='font-size: 12.5px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189
15385: Ly_spans = []
15388: span_val = cur_ly_spans[j]
15393: label_str = f"Ly{j+1} ({x_start} - {x_end})"
15394: w_key = f"{prefix}w_fs_ly_{j}_v{grid_ver}"
15401: help=f"البحر Ly{j+1} بين المحورين {x_start} ({coord_start:.2f}م) و {x_end} ({coord_end:.2f}م)"
15403: Ly_spans.append(val)
15405: with st.popover("✂️ Split Axis", use_container_width=True, help=f"تقسيم البحر Ly{j+1} وإدراج محور أف
15406: st.markdown(f"<div dir='rtl'><b>✂️ تقسيم البحر Ly{j+1} ({x_start} - {x_end})</b><br><small>الطول الح
15410: f"المسافة d₁ من المحور {x_start} (م):",
15415: key=f"{prefix}split_d1_ly_{j}_v{grid_ver}",
15416: help=f"المسافة من المحور {x_start} إلى المحور الأفقي الجديد."
15419: new_axis_coord = coord_start + float(d1_input)
15424: • البحر Ly{j+1} الجديد: <b>{d1_input:.2f} م</b> ({x_start} ➔ المحور الجديد عند {new_axis_coord:.2f}م
15425: • البحر Ly{j+2} الجديد: <b>{d2_calc:.2f} م</b> (المحور الجديد ➔ {x_end} عند {coord_end:.2f}م)<br>
15431: if st.button("🚀 تأكيد التقسيم وإدراج المحور", key=f"{prefix}btn_confirm_split_ly_{j}_v{grid_ver}", t
15432: active_lx = list(cur_lx_spans)
15433: active_ly = list(cur_ly_spans)
15435: split_span("Y", j, float(d1_input), active_lx, active_ly, trigger_rerun=True)
15526: f"(<span dir='ltr' style='unicode-bidi:isolate; display:inline-block; background:rgba(0,0,0,0.28); p
15527: f"أقل من الحد الأدنى الكودي (<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>ECP
15529: f"<span dir='ltr' style='unicode-bidi:isolate; display:inline-block; background:#ffffff; color:#991b
15534: f"(<span dir='ltr' style='unicode-bidi:isolate; display:inline-block; background:rgba(0,0,0,0.28); p
15535: f"أقل من الحد الأدنى الكودي (<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>ECP
15537: f"<span dir='ltr' style='unicode-bidi:isolate; display:inline-block; background:#ffffff; color:#991b
15567: <span style="font-size: 16px; font-weight: 900; color: #ffffff; text-shadow: 0 1px 3px rgba(0,0,0,0.
15570: <span style="font-size: 12px; font-weight: bold; background: rgba(0,0,0,0.35); color: #fecaca; paddi
15652: <li><b style="color: #fca5a5;">القص الثاقب (Punching Shear):</b> يرفع معامل تركيز الإجهادات (<b styl
15679: if any(lx <= 0 for lx in Lx_spans):   errs.append("All Lx spans must be > 0.")
15680: if any(ly <= 0 for ly in Ly_spans):   errs.append("All Ly spans must be > 0.")
15693: # If the user edits spans, the column & panel numbering changes → auto-reset pending.
15694: _geom_key = _geometry_key(Lx_spans, Ly_spans)
15705: _handle_fs_sync_payload(Lx_spans, Ly_spans, cantilevers)
15729: _handle_fs_sync_payload(Lx_spans, Ly_spans, cantilevers, _fs_sync_val)
15757: Lx_spans, Ly_spans, bc_cm=_bc_col, tc_cm=_tc_col,
15771: _all_panels_ref = get_flat_slab_panels(Lx_spans, Ly_spans)
15779: _all_panels = get_flat_slab_panels(Lx_spans, Ly_spans, _confirmed_voids)
15784: for lx in Lx_spans:
15787: for ly in Ly_spans:
15803: _active_cols, _all_cols, _eff_Lx, _eff_Ly, _ddm_warn = get_flat_slab_columns(
15804: Lx_spans, Ly_spans, bc_cm=_bc_col, tc_cm=_tc_col,
15818: _orig_panels_sk = get_flat_slab_panels(Lx_spans, Ly_spans)
15825: st.session_state["_fs_Lx_spans_arch"] = list(Lx_spans)
15826: st.session_state["_fs_Ly_spans_arch"] = list(Ly_spans)
15863: Lx_spans=Lx_spans,
15864: Ly_spans=Ly_spans,
15917: p["id"]: f"{p['name']} [{p['grid_x']} × {p['grid_y']}] ({p['Lx']:.2f}m × {p['Ly']:.2f}m — {p['area']
15952: f"<span style='background:#ffffff; border:1px solid #fcd34d; border-radius:4px; padding:2px 8px; fon
15960: ⚠️ <b>Pending Void Creation Confirmation:</b> سيتم تفريغ البلاطات كـ <b>مناور معمارية (Voids)</b> بم
16110: # Effective spans (merged where full axis was removed)
16111: Lx_calc = _eff_Lx if _eff_Lx else list(Lx_spans)
16112: Ly_calc = _eff_Ly if _eff_Ly else list(Ly_spans)
16139: f"(<span dir='ltr' style='unicode-bidi:isolate; display:inline-block; background:rgba(0,0,0,0.28); p
16140: f"أقل من الحد الأدنى الكودي (<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>ECP
16142: f"<span dir='ltr' style='unicode-bidi:isolate; display:inline-block; background:#ffffff; color:#991b
16147: f"(<span dir='ltr' style='unicode-bidi:isolate; display:inline-block; background:rgba(0,0,0,0.28); p
16148: f"أقل من الحد الأدنى الكودي (<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>ECP
16150: f"<span dir='ltr' style='unicode-bidi:isolate; display:inline-block; background:#ffffff; color:#991b
16181: nx_sp = len(Lx_spans)
16182: ny_sp = len(Ly_spans)
16193: col_atrib += (Lx_spans[i-1] / 2.0) * (Ly_spans[j-1] / 2.0)
16195: col_atrib += cant_L * (Ly_spans[j-1] / 2.0)
16197: col_atrib += (Lx_spans[i-1] / 2.0) * cant_B
16204: col_atrib += (Lx_spans[i] / 2.0) * (Ly_spans[j-1] / 2.0)
16206: col_atrib += cant_R * (Ly_spans[j-1] / 2.0)
16208: col_atrib += (Lx_spans[i] / 2.0) * cant_B
16215: col_atrib += (Lx_spans[i-1] / 2.0) * (Ly_spans[j] / 2.0)
16217: col_atrib += cant_L * (Ly_spans[j] / 2.0)
16219: col_atrib += (Lx_spans[i-1] / 2.0) * cant_T
16226: col_atrib += (Lx_spans[i] / 2.0) * (Ly_spans[j] / 2.0)
16228: col_atrib += cant_R * (Ly_spans[j] / 2.0)
16230: col_atrib += (Lx_spans[i] / 2.0) * cant_T
16287: ln_b = max(0.5, float(b.get("clear_span_m", b.get("span_m", 1.0))))
16331: btm_extra_spans = []
16336: for lx in Lx_spans:
16339: for ly in Ly_spans:
16345: for lx in Lx_calc:
16348: for ly in Ly_calc:
16351: # Labels and indices for active grid axes (preserving perimeter axes and any axis with >= 1 active c
16364: Ly_avg = sum(Ly_calc) / len(Ly_calc)
16365: Lx_avg = sum(Lx_calc) / len(Lx_calc)
16367: for i, lx in enumerate(Lx_calc):
16375: for j, ly in enumerate(Ly_calc):
16383: for i, lx in enumerate(Lx_calc):
16384: is_ext = (i == 0) or (i == len(Lx_calc) - 1)
16385: L_perp = Ly_avg
16393: span_label = f"Lx{i+1} = {lx:.2f} m",
16394: span_type  = "Exterior" if is_ext else "Interior",
16418: for j, ly in enumerate(Ly_calc):
16419: is_ext = (j == 0) or (j == len(Ly_calc) - 1)
16420: L_perp = Lx_avg
16428: span_label = f"Ly{j+1} = {ly:.2f} m",
16429: span_type  = "Exterior" if is_ext else "Interior",
16452: _orig_panels_sk = get_flat_slab_panels(Lx_spans, Ly_spans)
16459: st.session_state["_fs_Lx_spans_arch"] = list(Lx_spans)
16460: st.session_state["_fs_Ly_spans_arch"] = list(Ly_spans)
16475: Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
16485: for j in range(len(Ly_calc)):
16486: for i in range(len(Lx_calc)):
16493: span_lx = Lx_calc[i]
16494: span_ly = Ly_calc[j]
16542: Mo_x = Wu * span_ly * (Ln_x ** 2) / 8.0
16544: w_cs_x = min(span_lx, span_ly) / 2.0
16546: ms_w_x = max(0.1, span_ly - w_cs_x)
16566: Mo_y = Wu * span_lx * (Ln_y ** 2) / 8.0
16568: w_cs_y = min(span_lx, span_ly) / 2.0
16570: ms_w_y = max(0.1, span_lx - w_cs_y)
16594: B_zone_x = round(0.45 * span_ly, 2)
16620: # Curtailment length inside bay: clear span Ln minus curtailment or 0.65~0.68 L
16621: _L_raw_x = min(0.68 * span_lx, max(0.60 * span_lx, Ln_x - 0.30))
16631: L_ext_x = round(0.65 * span_lx, 2)
16634: is_ext_x = (i == 0) or (i == len(Lx_calc) - 1)
16635: span_type_x = "باكية مكبرة (Enlarged)" if is_enlarged else ("بحر طرفي (Exterior)" if is_ext_x else "
16640: "span_type": span_type_x,
16642: "span_len": span_lx,
16644: "W_bay": span_ly,
16683: btm_extra_spans.append(item_x)
16692: B_zone_y = round(0.45 * span_lx, 2)
16718: _L_raw_y = min(0.68 * span_ly, max(0.60 * span_ly, Ln_y - 0.30))
16728: L_ext_y = round(0.65 * span_ly, 2)
16731: is_ext_y = (j == 0) or (j == len(Ly_calc) - 1)
16732: span_type_y = "باكية مكبرة (Enlarged)" if is_enlarged else ("بحر طرفي (Exterior)" if is_ext_y else "
16737: "span_type": span_type_y,
16739: "span_len": span_ly,
16741: "W_bay": span_lx,
16780: btm_extra_spans.append(item_y)
16787: "grid_x_range": (f"X{i+1}", f"X{i+2}"),
16788: "grid_y_range": (f"Y{j+1}", f"Y{j+2}"),
16794: "Lx": span_lx,
16795: "Ly": span_ly,
16805: btm_x_indep = XZ.cluster_and_merge_bays([b for b in btm_extra_spans if b.get("dir") == "X"])
16806: btm_y_indep = XZ.cluster_and_merge_bays([b for b in btm_extra_spans if b.get("dir") == "Y"])
16808: btm_extra_spans = btm_x_indep + btm_y_indep
16810: # Global max clear span & code minimum thickness
16816: col_list, Lx_calc, Ly_calc, cantilevers, Wu, d, Fcu, Fy=Fy, ts_cm=ts, is_high_safety=high_safety_mod
16834: col_list, rows_x, rows_y, Lx_calc, Ly_calc, d, Fcu, Fy, ts, prov_top_mesh_cm2m, col_extra_dia,
16847: grid_x_range=bg["grid_x_range"],
16848: grid_y_range=bg["grid_y_range"],
16854: Lx=bg["Lx"],
16855: Ly=bg["Ly"],
16879: Lx_calc, Ly_calc, cantilevers, ts, d, Fcu, DL_tot, LL,
16894: Lx_calc, Ly_calc, cantilevers, ts,
16896: top_extra_cols, cant_rft_list, btm_extra_spans=btm_extra_spans,
16956: <div class="ecp-metric-val" style="color:#60a5fa;">{qcup_ref_val:.2f} <span style="font-size:12px;">
16966: <div class="ecp-metric-val" style="color:#fbbf24;">{qu_max_ref_val:.2f} <span style="font-size:12px;
16982: Lx_spans, Ly_spans, cantilevers, ts, d, Fcu, Wu,
17238: {sel_design['Ast_req_mm2']:.1f} mm² <span style="font-size:11px; color:#94a3b8;">({sel_design['Ast_r
17250: {sel_design['s_cm']:.1f} cm <span style="font-size:11px; color:#94a3b8;">(أول كانة s0 = {sel_design[
17262: {sel_design['n_rows']} صفوف <span style="font-size:11px; color:#94a3b8;">(إجمالي {sel_design['total_
17278: {L_strip_x_val:.1f} cm <span style="font-size:11px; color:#94a3b8;">(امتداد {sel_x_ext:.1f} cm)</spa
17290: {L_strip_y_val:.1f} cm <span style="font-size:11px; color:#94a3b8;">(امتداد {sel_x_ext:.1f} cm)</spa
17302: في الاتجاهين (X & Y) <span style="font-size:11px; color:#94a3b8;">(Orthogonal)</span>
17473: _dirs_top.append("اتجاه <span dir='ltr' style='unicode-bidi:isolate;'>X</span>")
17475: _dirs_top.append("اتجاه <span dir='ltr' style='unicode-bidi:isolate;'>Y</span>")
17478: f"<li style='margin-bottom:6px;'>🔴 <b>الشبكة العلوية (<span {_ltr_inline}>Top Mesh</span> — {_dirs_t
17487: _dirs_btm.append("اتجاه <span dir='ltr' style='unicode-bidi:isolate;'>X</span>")
17489: _dirs_btm.append("اتجاه <span dir='ltr' style='unicode-bidi:isolate;'>Y</span>")
17492: f"<li style='margin-bottom:4px;'>🔶 <b>الشبكة السفلية (<span {_ltr_inline}>Bottom Mesh</span> — {_dir
17531: Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
17537: btm_extra_spans=btm_extra_spans,
17569: Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
17575: btm_extra_spans=btm_extra_spans,
17646: for lx in Lx_calc: x_coords_ui.append(round(x_coords_ui[-1] + float(lx), 4))
17648: for ly in Ly_calc: y_coords_ui.append(round(y_coords_ui[-1] + float(ly), 4))
17669: cy = float(c.get("center_y", c.get("grid_y_m", c.get("y", 0.0))))
17703: lbl = f"📍 شريحة منتصف البحر بين Y={y1_v:.2f}m و Y={y2_v:.2f}m — (Y = {y_mid:.2f} m)"
17709: cx = float(c.get("center_x", c.get("grid_x_m", c.get("x", 0.0))))
17743: lbl = f"📍 شريحة منتصف البحر بين X={x1_v:.2f}m و X={x2_v:.2f}m — (X = {x_mid:.2f} m)"
17776: Lx_calc,
17777: Ly_calc,
17826: active_btm_extras   = [b for b in btm_extra_spans if isinstance(b, dict) and b.get("n_extra", 0) > 0
17893: "نوع البحر (Span Classification)": bx["span_type"],
17894: "طول البحر L / الصافي Ln (m)": f"{bx['span_len']:.2f} / {bx['Ln']:.2f} m",
17922: "نوع البحر (Span Classification)": by["span_type"],
17923: "طول البحر L / الصافي Ln (m)": f"{by['span_len']:.2f} / {by['Ln']:.2f} m",
17975: • <b>سعة العزم للشبكة الأساسية (<span dir="ltr" style="unicode-bidi:isolate; display:inline-block;">
17977: <span dir="ltr" style="unicode-bidi:isolate; display:inline-block; font-size:1.25rem; font-weight:90
17979: <span dir="ltr" style="unicode-bidi:isolate; display:inline-block; font-size:1.12rem; font-weight:80
17981: <span dir="ltr" style="unicode-bidi:isolate; display:inline-block; font-size:1.25rem; font-weight:90
17983: <span dir="ltr" style="unicode-bidi:isolate; display:inline-block; font-size:1.12rem; font-weight:80
17984: • <b>تحديد الحديد الإضافي (<span dir="ltr" style="unicode-bidi:isolate; display:inline-block;">ΔM = 
18014: Lx_calc, Ly_calc, cantilevers, ts,
18071: Lx_calc, Ly_calc, cantilevers, ts,
18072: btm_extra_spans=btm_extra_spans,
18118: Lx_calc, Ly_calc, cantilevers, ts,
18119: btm_extra_spans=btm_extra_spans,
18164: Lx_calc, Ly_calc, cantilevers, ts,
18210: Lx_calc, Ly_calc, cantilevers, ts,
18274: tot_len_m = sum(b.get("clear_span_m", 0.0) for b in _cfg_curr_beams)
18276: tot_vol_m3 = sum((b.get("b_cm", 25.0) / 100.0) * (b.get("t_cm", 60.0) / 100.0) * b.get("clear_span_m
18377: 📝 بطاقة المواصفات الفنية — كمرة <span style="color:#2563eb;">{selected_preview_id}</span>
18380: <tr><td><b>طول البحر الصافي (Ln):</b></td><td style="color:#0f172a; font-weight:700;">{sel_beam_obj.
18409: تم التحقق من سهم الانحناء طويل الأمد (Long-Term Cracked Deflection) بالاعتماد الفعلي على كامل شبكات 
18418: Lx_calc, Ly_calc, cantilevers, ts, d, Fcu, DL_tot, LL,
18685: file_name=f"{prefix}Deflection_Midspan_Section_{sel_panel_data['Panel ID']}.png",
18709: "Grid": f"{c['grid_x']} - {c['grid_y']}",
18739: Lx_spans, Ly_spans, cantilevers, num_floors, Wu,
18777: st.caption(f"ℹ️ الأحمال المحورية $P_u$ تشمل معامل الأمان ووزن الأعمدة (Factor of Safety & Columns We
18902: "grid_x": c.get("grid_x", ""),
18903: "grid_y": c.get("grid_y", ""),
18915: st.session_state["fs_Lx_spans"] = [float(x) for x in Lx_calc]
18916: st.session_state["fs_Ly_spans"] = [float(y) for y in Ly_calc]
18922: S.cfg_set("fs_Lx_spans", [float(x) for x in Lx_calc])
18923: S.cfg_set("fs_Ly_spans", [float(y) for y in Ly_calc])
19315: نظام متكامل لتصميم أساسات المبنى لعدد <span style="font-weight:800; color:#c2410c;">{num_floors} طوا
19348: nbr_cols_str = "، ".join([f"<span dir='ltr'><b>{cid}</b></span>" for cid in auto_nbr_ids])
19357: <span dir="rtl" style="font-size:1.35rem; font-weight:900; color:#b91c1c; background:#fef2f2; paddin
19360: <span style="font-size:1.05rem; font-weight:600; color:#475569;">
19409: "grid_x": c_item.get("grid_x", ""),
19410: "grid_y": c_item.get("grid_y", ""),
19411: "grid_x_m": float(c_item.get("grid_x_m", c_item["x"])),
19412: "grid_y_m": float(c_item.get("grid_y_m", c_item["y"])),
19487: <span style="font-size: 13.5px; background: #0284c7; color: #ffffff; padding: 4px 12px; border-radiu
19489: <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; m
19493: <div style="font-size: 20px; font-weight: 900; color: #ffffff;">{counts['isolated_count']} <span sty
19499: <div style="font-size: 20px; font-weight: 900; color: #ffffff;">{counts['edge_strap_count']} <span s
19505: <div style="font-size: 20px; font-weight: 900; color: #ffffff;">{counts['corner_strap_count']} <span
19566: <br/>• <b>قوى الربط المحوري (Axial Tie Action):</b> تصميم السملات على قوى ربط محوري بنسبة <span dir=
19686: len_gb = sum(b["span_m"] for b in gb_analysis["ground_beams"])
19687: len_st = sum(b["span_m"] for b in gb_analysis["strap_beams"])
19691: <div dir="rtl" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); ga
19694: <div style="font-size:20px; font-weight:900; color:#1e1b4b;">{cnt_gb} <span style="font-size:13px; f
19699: <div style="font-size:20px; font-weight:900; color:#431407;">{cnt_st} <span style="font-size:13px; f
19704: <div style="font-size:20px; font-weight:900; color:#052e16;">{gb_analysis['boq']['conc_vol_rc']:.2f}
19709: <div style="font-size:20px; font-weight:900; color:#2e1065;">{gb_analysis['boq']['steel_ton_tot']:.3
19922: لوحة تنفيذية متكاملة لأساسات المبنى لعدد <span style="font-weight:800; color:#1e3a8a;">{num_floors} 
20177: Lx_calc=Lx_calc,
20178: Ly_calc=Ly_calc,
20190: btm_extra_spans=btm_extra_spans if 'btm_extra_spans' in locals() else None,
20202: Lx_spans=Lx_spans if 'Lx_spans' in locals() else None,
20203: Ly_spans=Ly_spans if 'Ly_spans' in locals() else None,
20288: <span style="font-size: 1.45rem;">⚠️</span>
20579: Lx_calc=Lx_calc,
20580: Ly_calc=Ly_calc,
20586: btm_extra_spans=btm_extra_spans if 'btm_extra_spans' in locals() else None,
20599: Lx_spans=Lx_spans if 'Lx_spans' in locals() else None,
20600: Ly_spans=Ly_spans if 'Ly_spans' in locals() else None,
20773: div[data-testid="stExpander"] div.stButton > button span {{
20795: div[data-testid="stExpander"] div.stDownloadButton > button span {{
20803: <span style="font-size: 12px; background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: 
20852: Lx_spans, Ly_spans, cantilevers,
20886: top_extra_cols=top_extra_cols, btm_extra_spans=btm_extra_spans,
20901: Lx_spans, Ly_spans, cantilevers,
20933: Lx_spans, Ly_spans, cantilevers, ts, d, Fcu, Wu,
20952: Lx_calc, Ly_calc, cantilevers, ts, d, Fcu, DL_tot, LL,
20973: Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
20976: top_extra_cols=top_extra_cols, btm_extra_spans=btm_extra_spans,
20992: Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
20995: top_extra_cols=top_extra_cols, btm_extra_spans=btm_extra_spans,
21010: Lx_calc, Ly_calc, cantilevers, ts,
21029: Lx_calc, Ly_calc, cantilevers, ts,
21030: btm_extra_spans=btm_extra_spans,
21052: Lx_calc, Ly_calc, cantilevers, ts,
21053: btm_extra_spans=btm_extra_spans,
21075: Lx_calc, Ly_calc, cantilevers, ts,
21098: Lx_calc, Ly_calc, cantilevers, ts,
21121: Lx_calc, Ly_calc, cantilevers, ts,
21125: btm_extra_spans=btm_extra_spans,
21141: Lx_calc, Ly_calc, cantilevers, num_floors, Wu,
21158: Lx_calc, Ly_calc, cantilevers, ts,
21162: btm_extra_spans=btm_extra_spans,
21173: Lx_spans=Lx_calc, Ly_spans=Ly_calc, cantilevers=cantilevers,
21178: top_extra_cols=top_extra_cols, btm_extra_spans=btm_extra_spans,
21409: Lx_spans, Ly_spans, cantilevers,
21439: Lx_calc, Ly_calc, cantilevers, ts,
21453: Lx_calc, Ly_calc, cantilevers, ts,
21454: btm_extra_spans=btm_extra_spans,
21473: Lx_calc, Ly_calc, cantilevers, ts,
21474: btm_extra_spans=btm_extra_spans,
21493: Lx_calc, Ly_calc, cantilevers, ts,
21513: Lx_calc, Ly_calc, cantilevers, ts,
21533: Lx_spans, Ly_spans, cantilevers, ts, d, Fcu, Wu,
21546: Lx_calc, Ly_calc, cantilevers, ts, d, Fcu, DL_tot, LL,
21560: Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
21563: top_extra_cols=top_extra_cols, btm_extra_spans=btm_extra_spans,
21572: Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
21575: top_extra_cols=top_extra_cols, btm_extra_spans=btm_extra_spans,
21584: Lx_calc, Ly_calc, cantilevers, rows_x, rows_y, Wu,
21588: btm_extra_spans=btm_extra_spans,
21594: Lx_calc, Ly_calc, cantilevers, ts_cm=ts,
21605: Lx_calc, Ly_calc, cantilevers, ts,
21609: btm_extra_spans=btm_extra_spans,
21618: Lx_calc, Ly_calc, cantilevers, num_floors, Wu,
21628: Lx_calc, Ly_calc, cantilevers, ts,
21632: btm_extra_spans=btm_extra_spans,
