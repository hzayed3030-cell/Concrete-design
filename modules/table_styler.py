"""
modules/table_styler.py
-----------------------
Unified Elegant Table Rendering Engine for ECP 203 Concrete Design App.
Replicates the luxury styling, glowing cyber-navy borders, gradient headers,
vibrant neon accents, and smart status badges of Module 4 (Ground Slab Analysis & Checks).
Includes auto-adaptive typography for wide / multi-column tables.
"""

import re
import pandas as pd
import streamlit as st


def _is_numeric_or_measurement(val_str: str) -> bool:
    """Check if text represents numerical values, measurements, coordinates, percentages, or equations."""
    s = val_str.strip()
    if not s or s == "—" or s == "-":
        return False
    # If it contains digits and standard measurement tokens or symbols
    if re.search(r"\d", s):
        # Coordinates or math
        if s.startswith("(") and s.endswith(")"):
            return True
        # Units
        if re.search(r"(?:ton|t\.m|kg|cm|m'|m²|m³|mm|%|EGP|ج\.م|Φ|Ø|bars|L_|As|Pu|Mu|λ|min|max)", s, re.IGNORECASE):
            return True
        # Simple numbers or expressions like '10.5 / 20.0' or '25.0 × 30.0'
        if re.match(r"^[\d\.\,\+\-\×\/\s\(\)\:\@\=]+$", s):
            return True
    return False


def _is_status_cell(val_str: str) -> bool:
    """Check if the string is a status or safety verification note."""
    s = val_str.strip()
    keywords = ["SAFE", "UNSAFE", "Safe", "Unsafe", "Review", "آمن", "غير آمن", "تجاوز", "مطابق", "✅", "❌", "⚠️", "🚨", "Pass", "Fail"]
    return any(kw in s for kw in keywords)


def _format_status_badge(val_str: str, font_size_px: float) -> str:
    """Format status text into a glowing neon pill badge."""
    s = val_str.strip()
    badge_fs = max(8.5, font_size_px * 0.90)
    pad_v = max(2.0, font_size_px * 0.20)
    pad_h = max(5.0, font_size_px * 0.60)

    # Safe / Pass / Compliant
    if any(k in s for k in ["SAFE", "Safe", "آمن", "مطابق", "✅", "Pass", "OK"]):
        return (
            f'<span style="background: rgba(34, 197, 94, 0.20) !important; color: #4ade80 !important; '
            f'border: 1.5px solid #22c55e !important; padding: {pad_v:.0f}px {pad_h:.0f}px !important; '
            f'border-radius: 6px !important; font-size: {badge_fs:.1f}px !important; font-weight: 900 !important; '
            f'display: inline-block !important; white-space: nowrap !important; box-shadow: 0 0 8px rgba(34,197,94,0.25) !important;">'
            f'{s}</span>'
        )
    # Unsafe / Fail / Critical
    elif any(k in s for k in ["UNSAFE", "Unsafe", "غير آمن", "تجاوز", "❌", "Fail", "🚨"]):
        return (
            f'<span style="background: rgba(239, 68, 68, 0.20) !important; color: #f87171 !important; '
            f'border: 1.5px solid #ef4444 !important; padding: {pad_v:.0f}px {pad_h:.0f}px !important; '
            f'border-radius: 6px !important; font-size: {badge_fs:.1f}px !important; font-weight: 900 !important; '
            f'display: inline-block !important; white-space: nowrap !important; box-shadow: 0 0 8px rgba(239,68,68,0.25) !important;">'
            f'{s}</span>'
        )
    # Warning / Review
    elif any(k in s for k in ["⚠️", "Review", "تنبيه", "تحذير", "Warn"]):
        return (
            f'<span style="background: rgba(245, 158, 11, 0.20) !important; color: #fbbf24 !important; '
            f'border: 1.5px solid #f59e0b !important; padding: {pad_v:.0f}px {pad_h:.0f}px !important; '
            f'border-radius: 6px !important; font-size: {badge_fs:.1f}px !important; font-weight: 900 !important; '
            f'display: inline-block !important; white-space: nowrap !important; box-shadow: 0 0 8px rgba(245,158,11,0.25) !important;">'
            f'{s}</span>'
        )
    # Neutral Info
    else:
        return (
            f'<span style="background: rgba(56, 189, 248, 0.18) !important; color: #38bdf8 !important; '
            f'border: 1.5px solid #38bdf8 !important; padding: {pad_v:.0f}px {pad_h:.0f}px !important; '
            f'border-radius: 6px !important; font-size: {badge_fs:.1f}px !important; font-weight: 900 !important; '
            f'display: inline-block !important; white-space: nowrap !important;">'
            f'{s}</span>'
        )


def _is_total_row(row_vals: list) -> bool:
    """Check if the row represents a grand total or summary row."""
    if not row_vals:
        return False
    first_cell = str(row_vals[0]).strip()
    keywords = ["الإجمالي", "Grand Total", "Total", "TOTAL", "المجموع", "★", "📌 الإجمالي", "✅ الإجمالي", "🔷 إجمالي"]
    return any(k in first_cell for k in keywords)


def get_styled_table_html(
    data,
    headers: list = None,
    col_alignments: list = None,
    col_colors: list = None,
    accent_border_color: str = "#38bdf8",
    font_size_override: float = None,
    container_margin: str = "12px 0 20px 0",
) -> str:
    """
    Generate dark luxury HTML string for a table adhering to Module 4 ground design.
    """
    # ── Normalize Data to Headers & Rows Matrix ──────────────────────────────
    if isinstance(data, pd.DataFrame):
        hdr_list = list(data.columns) if headers is None else headers
        rows_matrix = data.values.tolist()
    elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        hdr_list = list(data[0].keys()) if headers is None else headers
        rows_matrix = [[d.get(k, "") for k in hdr_list] for d in data]
    elif isinstance(data, dict):
        hdr_list = list(data.keys()) if headers is None else headers
        # Determine number of rows
        num_rows = max((len(v) for v in data.values() if isinstance(v, list)), default=0)
        rows_matrix = []
        for r_idx in range(num_rows):
            row = [data[k][r_idx] if r_idx < len(data[k]) else "" for k in hdr_list]
            rows_matrix.append(row)
    elif isinstance(data, list):
        hdr_list = headers if headers is not None else [f"Col {i+1}" for i in range(len(data[0]) if data else 1)]
        rows_matrix = data
    else:
        return ""

    num_cols = len(hdr_list)
    if num_cols == 0:
        return ""

    # ── Adaptive Typography & Padding based on column count ─────────────────
    if font_size_override is not None:
        fs_hdr = font_size_override + 1.2
        fs_cell = font_size_override
        fs_num = font_size_override + 0.5
        pad_v = max(3, int(font_size_override * 0.45))
        pad_h = max(5, int(font_size_override * 0.65))
    elif num_cols <= 3:
        fs_hdr = 20.0
        fs_cell = 18.0
        fs_num = 20.0
        pad_v = 13
        pad_h = 16
    elif num_cols <= 5:
        fs_hdr = 18.0
        fs_cell = 16.0
        fs_num = 18.0
        pad_v = 11
        pad_h = 14
    elif num_cols <= 7:
        fs_hdr = 16.0
        fs_cell = 14.5
        fs_num = 15.5
        pad_v = 9
        pad_h = 12
    elif num_cols <= 9:
        fs_hdr = 14.5
        fs_cell = 13.0
        fs_num = 14.0
        pad_v = 7
        pad_h = 10
    else:
        # 10 or more columns (e.g. Punching & Deflection verification tables)
        fs_hdr = 12.0
        fs_cell = 11.0
        fs_num = 11.5
        pad_v = 5
        pad_h = 7

    # ── Default Column Alignments & Colors ───────────────────────────────────
    if not col_alignments or len(col_alignments) != num_cols:
        alignments = []
        for i, h in enumerate(hdr_list):
            h_str = str(h).lower()
            if i == 0 and not any(k in h_str for k in ["#", "م", "ø", "dia", "id", "grid"]):
                alignments.append("right")
            elif any(k in h_str for k in ["item", "بند", "وصف", "desc", "parameter", "name", "location", "application", "note", "ملاحظ"]):
                alignments.append("right")
            else:
                alignments.append("center")
    else:
        alignments = col_alignments

    if not col_colors or len(col_colors) != num_cols:
        header_colors = []
        for i, h in enumerate(hdr_list):
            h_str = str(h).lower()
            if any(k in h_str for k in ["status", "حالة", "أمان"]):
                header_colors.append("#4ade80")
            elif any(k in h_str for k in ["allow", "مسموح", "note", "ref", "مرجع", "سعر", "price"]):
                header_colors.append("#fbbf24")
            elif ("δ" in h_str or "delta" in h_str or "δ" in h_str) and ("tot" in h_str or "long" in h_str or "كلي" in h_str):
                header_colors.append("#ffffff")
            elif i == 0 and any(k in h_str for k in ["#", "م", "no"]):
                header_colors.append("#fbbf24")
            else:
                header_colors.append("#38bdf8")
    else:
        header_colors = col_colors

    # ── Build Header HTML ───────────────────────────────────────────────────
    hdr_ths = []
    for i, h in enumerate(hdr_list):
        align = alignments[i]
        c_color = header_colors[i]
        hdr_ths.append(
            f'<th style="padding: {pad_v + 3}px {pad_h}px !important; font-size: {fs_hdr:.1f}px !important; '
            f'font-weight: 900 !important; color: {c_color} !important; text-align: {align} !important; white-space: normal !important; line-height: 1.3 !important;">'
            f'{h}</th>'
        )

    thead_html = (
        '<thead>'
        f'<tr style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important; '
        f'border-bottom: 2.5px solid {accent_border_color} !important;">'
        + "".join(hdr_ths) +
        '</tr>'
        '</thead>'
    )

    # ── Build Rows HTML ─────────────────────────────────────────────────────
    tbody_trs = []
    for r_idx, row in enumerate(rows_matrix):
        is_tot = _is_total_row(row)
        if is_tot:
            bg_row = "linear-gradient(90deg, rgba(30, 58, 138, 0.45) 0%, rgba(15, 23, 42, 0.75) 100%)"
            border_row = f"border-top: 2.5px solid {accent_border_color}; border-bottom: 2.5px solid {accent_border_color};"
        else:
            bg_row = "rgba(15, 23, 42, 0.75)" if r_idx % 2 == 0 else "rgba(30, 41, 59, 0.75)"
            border_row = "border-bottom: 1.5px solid rgba(148, 163, 184, 0.25);"

        tds = []
        for c_idx, val in enumerate(row):
            val_str = str(val) if val is not None else ""
            align = alignments[c_idx]

            # Check if this cell is a status badge
            if _is_status_cell(val_str) and len(val_str) < 60:
                cell_content = _format_status_badge(val_str, fs_cell)
                tds.append(
                    f'<td style="padding: {pad_v}px {pad_h}px !important; text-align: center !important; vertical-align: middle !important;">'
                    f'{cell_content}</td>'
                )
            elif is_tot:
                # Highlighted total row cell
                text_color = "#fbbf24" if c_idx == 0 else ("#38bdf8" if _is_numeric_or_measurement(val_str) else "#ffffff")
                dir_attr = ' dir="ltr"' if _is_numeric_or_measurement(val_str) else ''
                tds.append(
                    f'<td style="padding: {pad_v + 2}px {pad_h}px !important; font-size: {fs_num:.1f}px !important; '
                    f'font-weight: 900 !important; color: {text_color} !important; text-align: {align} !important; vertical-align: middle !important; line-height: 1.3 !important;"{dir_attr}>'
                    f'{val_str}</td>'
                )
            elif c_idx == 0 and align == "right":
                # Primary text / parameter column
                tds.append(
                    f'<td style="padding: {pad_v}px {pad_h}px !important; font-size: {fs_cell:.1f}px !important; '
                    f'font-weight: 800 !important; color: #ffffff !important; text-align: {align} !important; vertical-align: middle !important; line-height: 1.3 !important;">'
                    f'{val_str}</td>'
                )
            elif _is_numeric_or_measurement(val_str):
                # Numeric / Result / Dimension column
                h_name = str(hdr_list[c_idx]).lower()
                if ("δ" in h_name or "delta" in h_name or "δ" in h_name) and ("tot" in h_name or "long" in h_name or "كلي" in h_name):
                    num_color = "#ffffff"
                else:
                    num_color = "#38bdf8"
                tds.append(
                    f'<td style="padding: {pad_v}px {pad_h}px !important; font-size: {fs_num:.1f}px !important; '
                    f'font-weight: 900 !important; color: {num_color} !important; text-align: {align} !important; vertical-align: middle !important; line-height: 1.3 !important;" dir="ltr">'
                    f'{val_str}</td>'
                )
            else:
                # Standard secondary text / code reference / notes
                h_name = str(hdr_list[c_idx]).lower()
                if ("δ" in h_name or "delta" in h_name or "δ" in h_name) and ("tot" in h_name or "long" in h_name or "كلي" in h_name):
                    text_color = "#ffffff"
                elif any(k in h_name for k in ["allow", "مسموح", "ref", "مرجع"]):
                    text_color = "#fbbf24"
                else:
                    text_color = "#cbd5e1"
                tds.append(
                    f'<td style="padding: {pad_v}px {pad_h}px !important; font-size: {fs_cell:.1f}px !important; '
                    f'font-weight: 700 !important; color: {text_color} !important; text-align: {align} !important; vertical-align: middle !important; line-height: 1.3 !important;">'
                    f'{val_str}</td>'
                )

        tbody_trs.append(
            f'<tr style="background: {bg_row} !important; {border_row}">'
            + "".join(tds) +
            '</tr>'
        )

    tbody_html = '<tbody>' + "".join(tbody_trs) + '</tbody>'

    full_html = (
        f'<div class="ecp-custom-table-container" style="overflow-x: auto; border: 2px solid {accent_border_color}; '
        f'border-radius: 12px; box-shadow: 0 6px 25px rgba(0, 0, 0, 0.50); margin: {container_margin};">'
        '<table class="ecp-styled-dark-table" style="width: 100% !important; border-collapse: collapse !important; background: #0b1329 !important; '
        'font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif !important;">'
        + thead_html + tbody_html +
        '</table>'
        '</div>'
    )
    return full_html


def render_styled_table(
    data,
    headers: list = None,
    col_alignments: list = None,
    col_colors: list = None,
    accent_border_color: str = "#38bdf8",
    font_size_override: float = None,
    container_margin: str = "12px 0 20px 0",
):
    """
    Render dark luxury styled table directly in Streamlit UI.
    """
    html_code = get_styled_table_html(
        data=data,
        headers=headers,
        col_alignments=col_alignments,
        col_colors=col_colors,
        accent_border_color=accent_border_color,
        font_size_override=font_size_override,
        container_margin=container_margin,
    )
    if html_code:
        if hasattr(st, "html"):
            st.html(html_code)
        else:
            st.markdown(html_code, unsafe_allow_html=True)
