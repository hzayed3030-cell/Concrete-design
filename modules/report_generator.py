"""
ECP 203 - Egyptian Code of Practice
Design Calculation Sheet & Report Generator
============================================
Generates comprehensive, standalone, print-ready HTML/PDF calculation sheets
with high-resolution embedded base64 CAD sketches, design tables, punching checks,
column reactions, and engineering sign-off blocks.
"""

import io
import os
import math
import shutil
import base64
import tempfile
import subprocess
import datetime
from typing import Dict, List, Any, Optional


def find_browser_executable() -> Optional[str]:
    """Finds an installed Edge or Chrome executable for headless PDF generation."""
    candidates = [
        shutil.which("msedge"),
        shutil.which("chrome"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def html_to_pdf_bytes(html_content: str, timeout_sec: int = 25) -> Optional[bytes]:
    """
    Converts standalone HTML calculation sheet content directly into a PDF byte stream
    using the system's built-in Edge / Chrome headless printing engine.
    """
    browser_exe = find_browser_executable()
    if not browser_exe:
        return None

    html_file = None
    pdf_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
            f.write(html_content)
            html_file = f.name

        pdf_file = html_file.replace(".html", ".pdf")

        cmd = [
            browser_exe,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_file}",
            html_file
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        if res.returncode == 0 and os.path.exists(pdf_file):
            with open(pdf_file, "rb") as pf:
                return pf.read()
    except Exception as e:
        print("PDF generation error:", e)
        return None
    finally:
        if html_file and os.path.exists(html_file):
            try:
                os.remove(html_file)
            except OSError:
                pass
        if pdf_file and os.path.exists(pdf_file):
            try:
                os.remove(pdf_file)
            except OSError:
                pass

    return None


def fig_to_base64(fig) -> str:
    """Converts a matplotlib figure into a high-resolution base64 PNG data URI."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=300)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _get_base_report_css() -> str:
    """Returns the print and screen CSS for standalone calculation sheets."""
    return """
    <style>
        :root {
            --primary: #1e3a8a;
            --primary-dark: #0f172a;
            --primary-light: #eff6ff;
            --accent: #2563eb;
            --success: #16a34a;
            --warning: #d97706;
            --danger: #dc2626;
            --border-color: #cbd5e1;
            --text-main: #0f172a;
            --text-muted: #475569;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, Tahoma, sans-serif;
            background-color: #f8fafc;
            color: var(--text-main);
            line-height: 1.5;
            padding: 24px 16px;
        }

        .report-container {
            max-width: 1100px;
            margin: 0 auto;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            padding: 36px 44px;
        }

        /* Top Action Bar (Visible only on screen) */
        .action-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #1e293b;
            color: #ffffff;
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 24px;
        }

        .btn-print {
            background: #2563eb;
            color: #ffffff;
            border: none;
            padding: 9px 20px;
            font-size: 0.95rem;
            font-weight: 700;
            border-radius: 6px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
        }

        .btn-print:hover {
            background: #1d4ed8;
            transform: translateY(-1px);
        }

        /* Report Header Block */
        .report-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid var(--primary);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }

        .header-title h1 {
            color: var(--primary-dark);
            font-size: 1.6rem;
            font-weight: 800;
            margin-bottom: 4px;
        }

        .header-title .code-badge {
            display: inline-block;
            background: #dbeafe;
            color: #1e40af;
            font-size: 0.85rem;
            font-weight: 700;
            padding: 2px 10px;
            border-radius: 6px;
            border: 1px solid #bfdbfe;
        }

        .header-meta {
            text-align: right;
            font-size: 0.85rem;
            color: var(--text-muted);
            line-height: 1.4;
        }

        /* Section Headings */
        .section-title {
            background: linear-gradient(90deg, #1e3a8a, #3b82f6);
            color: #ffffff;
            font-size: 1.1rem;
            font-weight: 700;
            padding: 8px 14px;
            border-radius: 6px;
            margin: 22px 0 12px 0;
        }

        .subsection-title {
            color: #1e3a8a;
            font-size: 0.95rem;
            font-weight: 700;
            margin: 14px 0 8px 0;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 4px;
        }

        /* Engineering Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 18px 0;
            font-size: 0.88rem;
        }

        th, td {
            padding: 8px 10px;
            text-align: left;
            border: 1px solid #cbd5e1;
        }

        th {
            background-color: #f1f5f9;
            color: #1e293b;
            font-weight: 700;
        }

        tr:nth-child(even) td {
            background-color: #f8fafc;
        }

        /* Metric Grid / Key-Value Grid */
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin: 12px 0;
        }

        .info-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px 14px;
        }

        .info-card .card-lbl {
            font-size: 0.8rem;
            font-weight: 600;
            color: #64748b;
        }

        .info-card .card-val {
            font-size: 1.05rem;
            font-weight: 700;
            color: #0f172a;
            margin-top: 2px;
            direction: ltr !important;
            unicode-bidi: isolate !important;
            text-align: right;
            display: block;
        }

        /* BiDi numbers and units isolation */
        .val-ltr, [dir="ltr"] {
            direction: ltr !important;
            unicode-bidi: isolate !important;
            display: inline-block;
        }

        .val-cell {
            direction: ltr !important;
            unicode-bidi: isolate !important;
            text-align: center !important;
        }

        /* Classification Highlight Cards */
        .classification-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin: 14px 0;
        }

        .type-card {
            border-radius: 8px;
            padding: 12px 14px;
            font-size: 0.85rem;
        }

        .type-card-int {
            background: #f0fdf4;
            border: 2px solid #22c55e;
        }

        .type-card-edge {
            background: #eff6ff;
            border: 2px solid #3b82f6;
        }

        .type-card-corner {
            background: #fff7ed;
            border: 2px solid #f97316;
        }

        /* Drawings and CAD Sketches */
        .drawing-box {
            text-align: center;
            margin: 16px 0;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 10px;
            background: #ffffff;
            page-break-inside: avoid;
        }

        .drawing-box img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }

        .drawing-caption {
            font-size: 0.85rem;
            font-weight: 700;
            color: #475569;
            margin-top: 6px;
        }

        /* Highlight Notes & Banners */
        .note-banner {
            border-radius: 8px;
            padding: 12px 16px;
            margin: 14px 0;
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .note-success {
            background: #f0fdf4;
            border-left: 5px solid #16a34a;
            color: #15803d;
        }

        .note-info {
            background: #eff6ff;
            border-left: 5px solid #2563eb;
            color: #1e40af;
        }

        .note-warning {
            background: #fffbeb;
            border-left: 5px solid #f59e0b;
            color: #92400e;
        }

        /* Sign-off / Approval Block */
        .signature-block {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-top: 36px;
            padding-top: 20px;
            border-top: 2px solid #e2e8f0;
            font-size: 0.85rem;
            page-break-inside: avoid;
        }

        .sig-box {
            border: 1px dashed #94a3b8;
            border-radius: 6px;
            padding: 12px;
            min-height: 90px;
        }

        .sig-title {
            font-weight: 700;
            color: #334155;
            margin-bottom: 4px;
        }

        /* Print Media Rules */
        @media print {
            .no-print {
                display: none !important;
            }

            body {
                background: #ffffff !important;
                padding: 0 !important;
                font-size: 9.5pt !important;
            }

            .report-container {
                box-shadow: none !important;
                border: none !important;
                padding: 0 !important;
                max-width: 100% !important;
            }

            .section-title {
                background: #1e3a8a !important;
                color: #ffffff !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                margin-top: 16px !important;
            }

            .page-break {
                page-break-before: always;
            }

            .drawing-box, .info-card, .type-card, table, .signature-block {
                page-break-inside: avoid;
            }

            @page {
                size: A4;
                margin: 12mm 10mm 15mm 10mm;
            }
        }
    </style>
    """


def generate_flat_slab_report_html(
    project_name: str,
    ts: float,
    d: float,
    num_floors: int,
    Wu: float,
    Lx_spans: List[float],
    Ly_spans: List[float],
    cantilevers: Dict[str, float],
    mesh_btm_str: str,
    mesh_top_str: str,
    prov_btm_mesh_cm2m: float,
    prov_top_mesh_cm2m: float,
    Fcu: float,
    Fy: float,
    SDL: float,
    wall_load: float,
    LL: float,
    bc: float,
    tc: float,
    boq: Dict[str, Any],
    top_extra_cols: List[Dict[str, Any]],
    btm_extra_spans: List[Dict[str, Any]],
    punching_results: List[Dict[str, Any]],
    all_punching_safe: bool,
    col_reactions_data: List[Dict[str, Any]],
    summary_models: List[Dict[str, Any]],
    img_verif_b64: Optional[str] = None,
    img_top_rft_b64: Optional[str] = None,
    img_btm_rft_b64: Optional[str] = None,
    img_reactions_b64: Optional[str] = None,
    img_m11_b64: Optional[str] = None,
    img_m22_b64: Optional[str] = None,
    img_dual_moment_b64: Optional[str] = None,
) -> str:
    """
    Generates a complete, standalone, print-ready HTML engineering calculation sheet
    for Module 3: Flat Slabs (ECP 203).
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    active_btm_extras = [b for b in btm_extra_spans if isinstance(b, dict) and b.get("n_extra", 0) > 0]

    # Build Inputs Table HTML
    inputs_html = f"""
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">Slab Thickness (ts)</div>
            <div class="card-val">{ts:.0f} cm  <span style="font-size:0.8rem; color:#64748b;">(d = {d:.1f} cm)</span></div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Number of Floors (عدد الأدوار)</div>
            <div class="card-val">{num_floors} Floors</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Design Load (Wu)</div>
            <div class="card-val">{Wu:.3f} t/m²</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Materials (Fcu / Fy)</div>
            <div class="card-val">{Fcu:.0f} / {Fy:.0f} kg/cm²</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Column Size (bc × tc)</div>
            <div class="card-val">{bc:.0f} × {tc:.0f} cm</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Surface Loads (DL/LL/WL)</div>
            <div class="card-val">{SDL:.2f} / {LL:.2f} / {wall_load:.2f} t/m²</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Bottom Mesh (B1, B2)</div>
            <div class="card-val" style="color:#1d4ed8;">{mesh_btm_str}</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Top Mesh (T1, T2)</div>
            <div class="card-val" style="color:#1d4ed8;">{mesh_top_str}</div>
        </div>
    </div>
    """

    # Build Drawings Section HTML
    drawings_html = ""
    fig_idx = 1
    if img_verif_b64:
        drawings_html += f"""
        <div class="drawing-box">
            <img src="{img_verif_b64}" alt="Structural Geometry Sketch & Verification Card">
            <div class="drawing-caption">Figure {fig_idx}: Structural Geometry Layout & Data Card Verification Plan</div>
        </div>
        """
        fig_idx += 1

    if img_m11_b64:
        drawings_html += f"""
        <div class="drawing-box">
            <img src="{img_m11_b64}" alt="2D Bending Moment M11 Contour Plan">
            <div class="drawing-caption">Figure {fig_idx}: 2D Bending Moment M11 Matrix & Color Contour Map (X-Direction / اتجاه X)</div>
        </div>
        """
        fig_idx += 1
    if img_m22_b64:
        drawings_html += f"""
        <div class="drawing-box">
            <img src="{img_m22_b64}" alt="2D Bending Moment M22 Contour Plan">
            <div class="drawing-caption">Figure {fig_idx}: 2D Bending Moment M22 Matrix & Color Contour Map (Y-Direction / اتجاه Y)</div>
        </div>
        """
        fig_idx += 1
    if img_dual_moment_b64 and not (img_m11_b64 or img_m22_b64):
        drawings_html += f"""
        <div class="drawing-box">
            <img src="{img_dual_moment_b64}" alt="Dual Bending Moment Contours">
            <div class="drawing-caption">Figure {fig_idx}: Dual Bending Moment Matrix & Color Contour Maps (M11 & M22)</div>
        </div>
        """
        fig_idx += 1

    if img_top_rft_b64:
        drawings_html += f"""
        <div class="drawing-box">
            <img src="{img_top_rft_b64}" alt="Top Reinforcement Plan">
            <div class="drawing-caption">Figure {fig_idx}: Top Reinforcement Plan (Top Mesh, Top Extra @ Columns, Cantilever Shawka)</div>
        </div>
        """
        fig_idx += 1
    if active_btm_extras and img_btm_rft_b64:
        drawings_html += f"""
        <div class="drawing-box">
            <img src="{img_btm_rft_b64}" alt="Bottom Reinforcement Plan">
            <div class="drawing-caption">Figure {fig_idx}: Bottom Reinforcement Plan (Bottom Mesh & Bay Extra Bottom Steel)</div>
        </div>
        """
        fig_idx += 1
    elif not active_btm_extras:
        drawings_html += f"""
        <div class="note-banner note-success" style="text-align:center; font-weight:700; font-size:1.05rem;">
            ✅ ملاحظة إنشائية: لا حاجة لحديد إضافي سفلي في أي باكية — الشبكة السفلية الأساسية ({mesh_btm_str}) تغطي بالكامل جميع عزوم الانحناء الموجبة (+M).
        </div>
        """

    # Build Punching Shear Table HTML
    punching_rows = ""
    for p in punching_results:
        is_p_safe = "Safe" in p.get("Status", "")
        status_color = "#16a34a" if is_p_safe else "#dc2626"
        s_des = p.get("stirrups_design", {})
        stirrup_summary = f"{s_des.get('n_legs_per_row', 0)} Φ{s_des.get('stirrup_dia_mm', 10)} @ {s_des.get('s_cm', 10):.0f}cm ({s_des.get('n_rows', 0)} rows)" if not is_p_safe and s_des.get("Ast_req_mm2", 0) > 0 else "—"
        punching_rows += f"""
        <tr>
            <td><b>{p.get('Column ID', '')}</b></td>
            <td>{p.get('Grid', '')}</td>
            <td>{p.get('Location Type', '')}</td>
            <td>{p.get('Section (cm)', '30 × 30')}</td>
            <td>{p.get('Pu (ton)', 0.0):.2f}</td>
            <td>{p.get('bo (cm)', 0.0):.1f}</td>
            <td>{p.get('qup (kg/cm²)', 0.0):.2f}</td>
            <td>{p.get('qcup (kg/cm²)', 0.0):.2f}</td>
            <td>{p.get('qu_max (kg/cm²)', 21.2):.2f}</td>
            <td>{p.get('Ratio', 0.0):.2f}</td>
            <td>{stirrup_summary}</td>
            <td style="color:{status_color}; font-weight:bold;">{p.get('Status', '')}</td>
        </tr>
        """
    punching_table_html = f"""
    <table>
        <thead>
            <tr>
                <th>Column ID</th>
                <th>Grid</th>
                <th>Type</th>
                <th>Section (cm)</th>
                <th>Pu (ton)</th>
                <th>bo (cm)</th>
                <th>qu (kg/cm²)</th>
                <th>qcup (kg/cm²)</th>
                <th>qu,max (kg/cm²)</th>
                <th>Ratio</th>
                <th>Stirrups Design (ECP 203)</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {punching_rows}
        </tbody>
    </table>
    """

    # Build Column Reactions Table HTML
    reaction_rows = ""
    for r in col_reactions_data:
        reaction_rows += f"""
        <tr>
            <td><b>{r.get('Column ID', '')}</b></td>
            <td>{r.get('Grid', '')}</td>
            <td>{r.get('Location Type', '')}</td>
            <td>{r.get('Tributary Area (m²)', '')}</td>
            <td><b>{r.get('Pu (1 Floor) [ton]', '')}</b></td>
            <td style="color:#1e40af; font-weight:bold;">{r.get(f'Total Pu ({num_floors} Floors) [ton]', '')}</td>
        </tr>
        """
    reactions_table_html = f"""
    <table>
        <thead>
            <tr>
                <th>Column ID</th>
                <th>Grid Axes</th>
                <th>Location Type</th>
                <th>Tributary Area (m²)</th>
                <th>Pu (1 Floor) [ton]</th>
                <th>Total Pu ({num_floors} Floors) [ton]</th>
            </tr>
        </thead>
        <tbody>
            {reaction_rows}
        </tbody>
    </table>
    """

    # Build BOQ HTML Tables
    boq_items_rows = ""
    for it in boq.get("items", []):
        boq_items_rows += f"""
        <tr>
            <td><b>{it.get('item_name', '')}</b></td>
            <td style="color:#1d4ed8; font-weight:bold;">{it.get('dia_str', '—')}</td>
            <td style="color:#1e293b; font-weight:bold;">{it.get('qty_str', '')}</td>
            <td>{it.get('length_str', '—')}</td>
            <td style="font-size:0.82rem; color:#475569;">{it.get('spec', '')}</td>
        </tr>
        """
    boq_items_table_html = f"""
    <table>
        <thead>
            <tr>
                <th>بند حديد التسليح / المادة (Material Component)</th>
                <th>قطر الحديد Φ (Bar Dia)</th>
                <th>الكمية الإجمالية (Quantity)</th>
                <th>إجمالي الطول (Total Length)</th>
                <th>المواصفات والملاحظات الإنشائية (Specification / Notes)</th>
            </tr>
        </thead>
        <tbody>
            {boq_items_rows}
        </tbody>
    </table>
    """

    boq_dia_rows = ""
    for d in boq.get("by_dia", []):
        boq_dia_rows += f"""
        <tr>
            <td><b style="color:#1e3a8a;">{d.get('dia_str', '')}</b></td>
            <td>{d.get('unit_w_kg_m', 0.0):.3f} kg/m'</td>
            <td>{d.get('length_str', '')}</td>
            <td>{d.get('weight_kg_str', '')}</td>
            <td style="color:#15803d; font-weight:bold;">{d.get('weight_ton_str', '')}</td>
            <td><b>{d.get('percent_str', '')}</b></td>
            <td style="font-size:0.82rem; color:#475569;">{d.get('apps', '')}</td>
        </tr>
        """
    boq_dia_rows += f"""
    <tr style="background:#edf2f7; font-weight:bold; border-top:2px solid #0f172a;">
        <td style="color:#0f172a;">📌 الإجمالي الكلي لحديد التسليح (Grand Total)</td>
        <td>—</td>
        <td style="color:#0f172a;">{boq.get('total_steel_len_m', 0.0):,.1f} m'</td>
        <td style="color:#0f172a;">{boq.get('total_steel_kg', 0.0):,.1f} kg</td>
        <td style="color:#15803d; font-size:1.0rem;">{boq.get('total_steel_ton', 0.0):.3f} Ton</td>
        <td>100.0 %</td>
        <td style="color:#1e40af;">معدل الاستهلاك: {boq.get('steel_ratio_kg_m3', 0.0):.1f} kg/m³ خرسانة</td>
    </tr>
    """
    boq_dia_table_html = f"""
    <table>
        <thead>
            <tr>
                <th>قطر السيخ Φ (Bar Dia)</th>
                <th>وزن المتر الطولي</th>
                <th>إجمالي الطول (m')</th>
                <th>إجمالي الوزن (kg)</th>
                <th>إجمالي الوزن (Ton)</th>
                <th>النسبة المئوية (%)</th>
                <th>الاستخدامات الإنشائية في السقف (Applications)</th>
            </tr>
        </thead>
        <tbody>
            {boq_dia_rows}
        </tbody>
    </table>
    """

    boq_concrete_mat_table_html = f"""
    <table>
        <thead>
            <tr>
                <th>المادة / المكون الإنشائي (Material Component)</th>
                <th>الكمية الإجمالية (Quantity)</th>
                <th>الوحدة (Unit)</th>
                <th>معدل الخلط والنسب المعيارية (Mix Proportion / Standard)</th>
                <th>ملاحظات التنفيذ والتوريد بالموقع (Procurement & Site Notes)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><b>1. الخرسانة المسلحة الجاهزة (Reinforced Concrete Volume)</b></td>
                <td style="color:#166534; font-weight:bold; font-size:0.95rem;">{boq.get('concrete_vol_m3', 0.0):.2f} m³</td>
                <td>متر مكعب (m³)</td>
                <td>مسطح السقف: {boq.get('slab_area_m2', 0.0):.1f} m² × سمك {ts:.0f} cm</td>
                <td>رتبة الخرسانة Fcu = {Fcu:.0f} kg/cm² (صب بالمضخة Pump)</td>
            </tr>
            <tr>
                <td><b>2. الأسمنت البورتلاندي العادي (Ordinary Portland Cement)</b></td>
                <td style="color:#1e3a8a; font-weight:bold; font-size:0.95rem;">{boq.get('cement_ton', 0.0):.2f} Ton <span style="font-size:0.8rem; color:#475569;">({boq.get('cement_kg', 0.0):,.0f} kg)</span></td>
                <td>طن (Ton) / شكارة (Bag)</td>
                <td>{boq.get('cement_content_kg_m3', 350.0):.0f} kg/m³ ({boq.get('cement_content_kg_m3', 350.0)/50:.0f} شكاير / م³ خرسانة)</td>
                <td>إجمالي عدد الشكائر: <b>{boq.get('cement_bags', 0):,} شكارة</b> (وزن الشكارة 50 كجم)</td>
            </tr>
            <tr>
                <td><b>3. الزلط / الركام الكبير (Gravel / Coarse Aggregate)</b></td>
                <td style="color:#92400e; font-weight:bold; font-size:0.95rem;">{boq.get('gravel_m3', 0.0):.2f} m³</td>
                <td>متر مكعب (m³)</td>
                <td>0.80 m³ زلط لكل 1.0 m³ خرسانة مسلحة</td>
                <td>زلط نظيف متدرج الحبيبات خالٍ من الشوائب والمواد العضوية</td>
            </tr>
            <tr>
                <td><b>4. الرمل الحرش / الركام الصغير (Clean Coarse Sand)</b></td>
                <td style="color:#991b1b; font-weight:bold; font-size:0.95rem;">{boq.get('sand_m3', 0.0):.2f} m³</td>
                <td>متر مكعب (m³)</td>
                <td>0.40 m³ رمل لكل 1.0 m³ خرسانة مسلحة (نصف حجم الزلط)</td>
                <td>رمل حرش نظيف متدرج خالٍ من الطفلة والأملاح الضارة</td>
            </tr>
            <tr>
                <td><b>5. مياه الخلط التقريبية (Mixing Water)</b></td>
                <td style="color:#0284c7; font-weight:bold;">{boq.get('water_liters', 0.0):,.0f} لتر</td>
                <td>لتر (Liters) / m³</td>
                <td>175 لتر / م³ خرسانة (نسبة مياه/أسمنت w/c ≈ 0.50)</td>
                <td>مياه صالحة للشرب وخالية من الشوائب والزيوت</td>
            </tr>
        </tbody>
    </table>
    """

    # Build Governing Models HTML
    models_rows = ""
    for m in summary_models:
        models_rows += f"""
        <tr>
            <td><b>{m.get('Column Model (نموذج التصميم)', '')}</b></td>
            <td>{m.get('Governing Column', '')}</td>
            <td>{m.get('Location Type', '')}</td>
            <td>{m.get('Tributary Area (m²)', '')}</td>
            <td><b>{m.get('Pu (1 Floor) [ton]', '')}</b></td>
            <td style="color:#1e40af; font-weight:bold; font-size:1.0rem;">{m.get(f'Total Pu ({num_floors} Floors) [ton]', '')}</td>
        </tr>
        """
    models_table_html = f"""
    <table>
        <thead>
            <tr>
                <th>Design Model (النموذج)</th>
                <th>Governing Column</th>
                <th>Location Type</th>
                <th>Tributary Area (m²)</th>
                <th>Pu (1 Floor) [ton]</th>
                <th>Total Pu ({num_floors} Floors) [ton]</th>
            </tr>
        </thead>
        <tbody>
            {models_rows}
        </tbody>
    </table>
    """

    reaction_drawing_html = f"""
    <div class="drawing-box">
        <img src="{img_reactions_b64}" alt="Column Reactions & Multi-Storey Load Plan">
        <div class="drawing-caption">Column Reactions & Vertical Load Distribution Plan ({num_floors} Floors)</div>
    </div>
    """ if img_reactions_b64 else ""

    section_4_html = f"""
    <!-- Section 4: Column Reactions & Multi-Storey Loads -->
    <div class="section-title page-break">4. ردود أفعال وأحمال الأعمدة ({num_floors} طوابق) — (Column Reactions & Loads)</div>
    {reaction_drawing_html}
    {reactions_table_html}

    <div class="subsection-title">📌 نماذج التصميم الحاكمة للأعمدة (Governing Column Models by Type):</div>
    {models_table_html}
    """ if col_reactions_data and len(col_reactions_data) > 0 else ""

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ECP 203 - Flat Slab Calculation Sheet</title>
    {_get_base_report_css()}
</head>
<body>

<div class="report-container">

    <!-- Top Action Bar -->
    <div class="action-bar no-print">
        <div style="font-weight:700; font-size:1.05rem;">📑 مذكرة الحسابات الإنشائية — Flat Slab Design Sheet</div>
        <button class="btn-print" onclick="window.print();">🖨️ طباعة المذكرة / حفظ كـ PDF (Print / Save as PDF)</button>
    </div>

    <!-- Report Header -->
    <div class="report-header">
        <div class="header-title">
            <h1>مذكرة الحسابات والتصميم الإنشائي للأسقف اللاكمرية (Flat Slab)</h1>
            <span class="code-badge">الكود المصري لتصميم وتنفيذ المنشآت الخرسانية ECP 203-2018</span>
        </div>
        <div class="header-meta">
            <div><b>المشروع:</b> {project_name}</div>
            <div><b>تاريخ التصميم:</b> {now_str}</div>
            <div><b>عدد الطوابق:</b> {num_floors} طوابق</div>
        </div>
    </div>

    <!-- Section 1: Design Inputs -->
    <div class="section-title">1. مدخلات التصميم والخصائص الهندسية (Design Parameters & Loads)</div>
    {inputs_html}

    <!-- Section 2: Drawings -->
    <div class="section-title">2. المخططات الإنشائية وتفاصيل التسليح (Structural Drawings & Reinforcement)</div>
    {drawings_html}

    <!-- Section 3: Punching Shear -->
    <div class="section-title page-break">3. التحقق من القص الثاقب للأعمدة (Punching Shear Verification)</div>
    <div class="note-banner {'note-success' if all_punching_safe else 'note-warning'}">
        {'✅ جميع الأعمدة آمنة تماماً ضد القص الثاقب (All Columns Safe in Punching Shear).' if all_punching_safe else '⚠️ تنبيه: بعض الأعمدة تتطلب زيادة سمك البلاطة أو إضافة سقوط Drop Panel.'}
    </div>
    {punching_table_html}

    {section_4_html}

    <!-- Section 5: BOQ & Quantities -->
    <div class="section-title page-break">5. حصر الكميات التقديري وجداول تفريد الأقطار (Estimated BOQ & Steel Take-off)</div>
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">إجمالي مسطح السقف (Total Slab Area)</div>
            <div class="card-val" style="color:#1e40af;">{boq.get('slab_area_m2', 0.0):.1f} m²</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">إجمالي حجم الخرسانة المسلحة</div>
            <div class="card-val" style="color:#1e40af;">{boq.get('concrete_vol_m3', 0.0):.2f} m³</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">إجمالي وزن حديد التسليح الكلي</div>
            <div class="card-val" style="color:#15803d;">{boq.get('total_steel_ton', 0.0):.3f} Ton ({boq.get('total_steel_kg', 0.0):,.0f} kg)</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">معدل استهلاك الحديد (Steel Ratio)</div>
            <div class="card-val">{boq.get('steel_ratio_kg_m3', 0.0):.1f} kg/m³</div>
        </div>
    </div>

    <div class="subsection-title">📋 5.1 جدول حصر بنود حديد التسليح والمواد (Reinforcement & Material Breakdown):</div>
    {boq_items_table_html}

    <div class="subsection-title">📊 5.2 جدول إجمالي كميات الحديد لكل قطر والإجمالي الكلي (Total Quantities by Bar Diameter & Grand Total):</div>
    {boq_dia_table_html}

    <div class="subsection-title">🧱 5.3 جدول حصر كميات الخرسانة المسلحة والمواد الأولية (Concrete & Raw Materials Estimate):</div>
    {boq_concrete_mat_table_html}

    <!-- Sign-off Block -->
    <div class="signature-block">
        <div class="sig-box">
            <div class="sig-title">مهندس التصميم الإنشائي (Designer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">المراجعة الهندسية (Reviewer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">اعتماد المكتب الاستشاري (Approval):</div>
            <div style="margin-top:20px; color:#94a3b8;">الختم والتاريخ: ______________</div>
        </div>
    </div>

</div>

</body>
</html>
"""
    return html_content


def generate_flat_slab_outputs_report_html(
    project_name: str,
    ts: float,
    d: float,
    num_floors: int,
    Wu: float,
    Fcu: float,
    Fy: float,
    SDL: float,
    wall_load: float,
    LL: float,
    bc: float,
    tc: float,
    mesh_btm_str: str,
    mesh_top_str: str,
    top_extra_cols: List[Dict[str, Any]],
    btm_extra_spans: List[Dict[str, Any]],
    cant_rft_list: Optional[List[Dict[str, Any]]] = None,
    punching_results: Optional[List[Dict[str, Any]]] = None,
    all_punching_safe: bool = True,
    deflection_results: Optional[List[Dict[str, Any]]] = None,
    all_deflection_safe: bool = True,
    img_verif_b64: Optional[str] = None,
) -> str:
    """
    Generates a concise, high-level Output Summary calculation sheet (تقرير مخرجات التصميم المعتمد).
    Contains:
    1. Structural Geometry Layout & Verification Sketch
    2. Primary Design Inputs & Material Properties
    3. Comprehensive Design Outputs Table:
       - Slab Thickness ts & d
       - Bottom & Top Primary Meshes
       - Column Top Extra Steel (Caps / كابات الأعمدة)
       - Bay Bottom Extra Steel (الحديد الإضافي السفلي)
       - Top Slab Middle Strip Extra Steel (الحديد الإضافي العلوي للبلاطة)
       - Cantilever Reinforcement (الشوك)
       - Punching Shear & Long-term Deflection Safety Verification
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 1. Inputs Section
    inputs_html = f"""
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">Slab Thickness (ts)</div>
            <div class="card-val">{ts:.0f} cm  <span style="font-size:0.8rem; color:#64748b;">(d = {d:.1f} cm)</span></div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Number of Floors (عدد الأدوار)</div>
            <div class="card-val">{num_floors} Floors</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Ultimate Load (Wu)</div>
            <div class="card-val">{Wu:.3f} t/m²</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Materials (Fcu / Fy)</div>
            <div class="card-val">{Fcu:.0f} / {Fy:.0f} kg/cm²</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Standard Column (bc × tc)</div>
            <div class="card-val">{bc:.0f} × {tc:.0f} cm</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Loads (SDL / LL / Walls)</div>
            <div class="card-val">{SDL:.2f} / {LL:.2f} / {wall_load:.2f} t/m²</div>
        </div>
    </div>
    """

    # 2. Geometry Sketch
    drawing_html = ""
    if img_verif_b64:
        drawing_html = f"""
        <div class="drawing-box">
            <img src="{img_verif_b64}" alt="Structural Geometry Sketch & Verification Card">
            <div class="drawing-caption">مخطط التحقق الهندسي وتوزيع المحاور والأعمدة (Structural Geometry & Column Layout Plan)</div>
        </div>
        """

    # 3. Master Design Outputs Table
    # Filter active top extra at columns
    active_top_cols = [c for c in top_extra_cols if c.get("is_needed", False) and c.get("n_extra", 0) > 0]
    top_cols_summary = []
    for c in active_top_cols:
        col_lbl = c.get("col_label", f"C{c.get('i', 0)+1}-{c.get('j', 0)+1}")
        top_cols_summary.append(f"<b>{col_lbl}:</b> {c.get('callout', '')}")
    top_cols_str = "<br>".join(top_cols_summary) if top_cols_summary else "الشبكة العلوية كافية ولا حاجة لكابات إضافية ✅"

    # Filter active bottom extra
    active_btm_spans = [b for b in btm_extra_spans if b.get("is_needed", False) and b.get("n_extra", 0) > 0]
    btm_spans_summary = []
    for b in active_btm_spans:
        bay_lbl = b.get("bay_label", f"Bay {b.get('panel_id', '')}")
        btm_spans_summary.append(f"<b>{bay_lbl} [{b.get('dir', 'X')}]:</b> {b.get('callout', '')}")
    btm_spans_str = "<br>".join(btm_spans_summary) if btm_spans_summary else "الشبكة السفلية كافية وتغطي كامل عزوم منتصف البحر ✅"

    # Cantilevers summary
    cant_summary = []
    if cant_rft_list:
        for c in cant_rft_list:
            cant_summary.append(f"<b>{c.get('side_ar', c.get('side', ''))} (L={c.get('length', 0):.2f}m):</b> شوكة {c.get('rft_callout', '')} (طول القطع: {c.get('total_bar_length', 0):.2f}m)")
    cant_str = "<br>".join(cant_summary) if cant_summary else "لا توجد كوابيل (No Cantilevers)"

    # Punching summary
    unsafe_punch = [p for p in (punching_results or []) if not p.get("is_safe", True)]
    if not punching_results or len(unsafe_punch) == 0:
        punch_status_html = "<span style='color:#16a34a; font-weight:bold;'>✅ جميع الأعمدة آمنة تماماً بمقاومة الخرسانة بمفردها (qu ≤ qcup)</span>"
    else:
        unsafe_names = ", ".join([p.get("Column ID", "") for p in unsafe_punch])
        punch_status_html = f"<span style='color:#dc2626; font-weight:bold;'>⚠️ يوجد {len(unsafe_punch)} عمود يتطلب كانات قص ثاقب أو زيادة السُمك: ({unsafe_names})</span>"

    # Deflection summary
    unsafe_def = [d_p for d_p in (deflection_results or []) if not d_p.get("is_safe", True)]
    if not deflection_results or len(unsafe_def) == 0:
        def_status_html = "<span style='color:#16a34a; font-weight:bold;'>✅ جميع الباكيات آمنة ومحققة لحدود الكود لسهم الانحناء طويل الأمد (Δtotal ≤ Ln/250)</span>"
    else:
        unsafe_p_names = ", ".join([d_p.get("Panel ID", "") for d_p in unsafe_def])
        def_status_html = f"<span style='color:#dc2626; font-weight:bold;'>⚠️ تجاوز سهم الانحناء المسموح في {len(unsafe_def)} باكية: ({unsafe_p_names})</span>"

    outputs_table_html = f"""
    <table>
        <thead>
            <tr>
                <th style="width:25%;">عنصر المخرجات الإنشائية (Output Component)</th>
                <th style="width:45%;">المواصفات والكميات المعتمدة (Adopted Specification & Rebar)</th>
                <th style="width:30%;">الملاحظات وحالة الأمان الكودية (Code Verification)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><b>1. تخانة البلاطة والعمق الفعال (Thickness & Depth)</b></td>
                <td><b>ts = {ts:.0f} cm</b>  │  <b>d = {d:.1f} cm</b></td>
                <td>يحقق متطلبات الصلابة الكودية ECP 203</td>
            </tr>
            <tr>
                <td><b>2. الشبكة السفلية الأساسية (Bottom Mesh B1, B2)</b></td>
                <td style="color:#1d4ed8; font-weight:bold; font-size:1.0rem;">{mesh_btm_str}</td>
                <td>رقة سفلية موحدة تغطي العزوم الموجبة بالكامل (+M)</td>
            </tr>
            <tr>
                <td><b>3. الشبكة العلوية الأساسية (Top Mesh T1, T2)</b></td>
                <td style="color:#1d4ed8; font-weight:bold; font-size:1.0rem;">{mesh_top_str}</td>
                <td>رقة علوية موحدة لمقاومة الانكماش والعزوم السالبة</td>
            </tr>
            <tr>
                <td><b>4. كابات الأعمدة والحديد الإضافي العلوي (Top Extra at Columns)</b></td>
                <td style="line-height:1.7;">{top_cols_str}</td>
                <td>لتغطية ذروة العزوم السالبة (-M) فوق رؤوس الأعمدة</td>
            </tr>
            <tr>
                <td><b>5. الحديد الإضافي السفلي بالباكيات (Bottom Extra in Panels)</b></td>
                <td style="line-height:1.7;">{btm_spans_str}</td>
                <td>لتغطية عزوم البحور المكبرة والأطراف الحرة</td>
            </tr>
            <tr>
                <td><b>6. تسليح الكوابيل والشوكة (Cantilever Reinforcement)</b></td>
                <td style="line-height:1.7;">{cant_str}</td>
                <td>امتداد الشوكة 1.5 مرة طول الكابولي داخل السقف</td>
            </tr>
            <tr>
                <td><b>7. التحقق من القص الثاقب (Punching Shear Safety)</b></td>
                <td colspan="2">{punch_status_html}</td>
            </tr>
            <tr>
                <td><b>8. التحقق من الترخيم طويل الأمد (Long-term Deflection)</b></td>
                <td colspan="2">{def_status_html}</td>
            </tr>
        </tbody>
    </table>
    """

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ECP 203 - Flat Slab Design Outputs Summary</title>
    {_get_base_report_css()}
</head>
<body>

<div class="report-container">

    <!-- Top Action Bar -->
    <div class="action-bar no-print">
        <div style="font-weight:700; font-size:1.05rem;">📕 تقرير مخرجات التصميم الإنشائي — Flat Slab Design Outputs</div>
        <button class="btn-print" onclick="window.print();">🖨️ طباعة المخرجات / حفظ كـ PDF</button>
    </div>

    <!-- Report Header -->
    <div class="report-header">
        <div class="header-title">
            <h1>تقرير مخرجات التصميم الإنشائي للبلاطات اللاكمرية (Flat Slab)</h1>
            <span class="code-badge">الكود المصري ECP 203-2018 │ مخرجات معتمدة للمكاتب الاستشارية</span>
        </div>
        <div class="header-meta">
            <div><b>المشروع:</b> {project_name}</div>
            <div><b>تاريخ التوليد:</b> {now_str}</div>
            <div><b>عدد الطوابق:</b> {num_floors} طوابق</div>
        </div>
    </div>

    <!-- Section 1: Sketch & Inputs -->
    <div class="section-title">1. المخطط الهندسي ومدخلات التصميم الأساسية (Geometry Sketch & Primary Inputs)</div>
    {drawing_html}
    {inputs_html}

    <!-- Section 2: Master Outputs -->
    <div class="section-title page-break">2. جدول مخرجات التصميم والتسليح المعتمد (Master Design & Reinforcement Outputs)</div>
    {outputs_table_html}

    <!-- Sign-off Block -->
    <div class="signature-block">
        <div class="sig-box">
            <div class="sig-title">مهندس التصميم الإنشائي (Designer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">المراجعة الهندسية (Reviewer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">اعتماد المكتب الاستشاري (Consultant Approval):</div>
            <div style="margin-top:20px; color:#94a3b8;">الختم والتاريخ: ______________</div>
        </div>
    </div>

</div>

</body>
</html>
"""
    return html_content


def generate_column_report_html(
    project_name: str,
    b: float,
    t: float,
    H: float,
    Pu: float,
    fcu: float,
    fy: float,
    main_steel_str: str,
    stirrups_str: str,
    pu_cap: float,
    slender_str: str,
    img_col_b64: Optional[str] = None,
) -> str:
    """Generates a standalone, print-ready HTML calculation sheet for Module 1: Columns."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ratio = (Pu / pu_cap * 100.0) if pu_cap and pu_cap > 0 else 0.0

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ECP 203 - Column Design Calculation Sheet</title>
    {_get_base_report_css()}
</head>
<body>

<div class="report-container">

    <!-- Top Action Bar -->
    <div class="action-bar no-print">
        <div style="font-weight:700; font-size:1.05rem;">📑 مذكرة الحسابات الإنشائية — Column Design Sheet</div>
        <button class="btn-print" onclick="window.print();">🖨️ طباعة المذكرة / حفظ كـ PDF (Print / Save as PDF)</button>
    </div>

    <!-- Report Header -->
    <div class="report-header">
        <div class="header-title">
            <h1>مذكرة الحسابات والتصميم الإنشائي للأعمدة المستطيلة (Rectangular Columns)</h1>
            <span class="code-badge">الكود المصري لتصميم وتنفيذ المنشآت الخرسانية ECP 203-2018</span>
        </div>
        <div class="header-meta">
            <div><b>المشروع:</b> {project_name}</div>
            <div><b>تاريخ التصميم:</b> {now_str}</div>
        </div>
    </div>

    <!-- Section 1: Inputs & Parameters -->
    <div class="section-title">1. مدخلات التصميم والخصائص الهندسية (Design Parameters & Loads)</div>
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">Column Dimensions (b × t)</div>
            <div class="card-val">{b:.0f} × {t:.0f} cm</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Clear Height (H)</div>
            <div class="card-val">{H:.2f} m</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Ultimate Load (Pu)</div>
            <div class="card-val" style="color:#1e40af;">{Pu:.2f} Ton</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Material Strength (Fcu / Fy)</div>
            <div class="card-val">{fcu:.0f} / {fy:.0f} kg/cm²</div>
        </div>
    </div>

    <!-- Section 2: Reinforcement & CAD Sketch -->
    <div class="section-title">2. تفاصيل التسليح والمخطط الإنشائي للقطاع (CAD Cross-Section)</div>
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">Main Reinforcement (التسليح الرأسي)</div>
            <div class="card-val" style="color:#15803d;">{main_steel_str}</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Stirrups / Ties (الكانات)</div>
            <div class="card-val" style="color:#1d4ed8;">{stirrups_str}</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Section Capacity (Pu,capacity)</div>
            <div class="card-val" style="color:#16a34a;">{pu_cap:.2f} Ton</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Capacity Utilization Ratio</div>
            <div class="card-val">{ratio:.1f}%</div>
        </div>
    </div>

    {f'<div class="drawing-box"><img src="{img_col_b64}" alt="Column Cross-Section"><div class="drawing-caption">Figure 1: Column Cross-Section & Reinforcement Detailing</div></div>' if img_col_b64 else ''}

    <!-- Sign-off Block -->
    <div class="signature-block">
        <div class="sig-box">
            <div class="sig-title">مهندس التصميم الإنشائي (Designer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">المراجعة الهندسية (Reviewer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">اعتماد المكتب الاستشاري (Approval):</div>
            <div style="margin-top:20px; color:#94a3b8;">الختم والتاريخ: ______________</div>
        </div>
    </div>

</div>

</body>
</html>
"""
    return html_content


def generate_footing_report_html(
    project_name: str,
    col_bc: float,
    col_tc: float,
    P_serv: float,
    Pu: float,
    q_all: float,
    L_rc: float,
    B_rc: float,
    d_rc: float,
    rebar_L_str: str,
    rebar_B_str: str,
    img_footing_b64: Optional[str] = None,
    img_plan_b64: Optional[str] = None,
    img_sec_b64: Optional[str] = None,
) -> str:
    """Generates a standalone, print-ready HTML calculation sheet for Module 3: Isolated Footings."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Determine drawings HTML
    drawings_html = ""
    if img_plan_b64 and img_sec_b64:
        drawings_html = f"""
        <div class="drawing-box" style="margin-top:20px;">
            <img src="{img_plan_b64}" alt="Footing Plan View">
            <div class="drawing-caption">Figure 1: Isolated Footing Plan View (المسقط الأفقي للقاعدة الخرسانية المسلحة والعادية)</div>
        </div>
        <div class="drawing-box" style="margin-top:24px;">
            <img src="{img_sec_b64}" alt="Footing Section Elevation">
            <div class="drawing-caption">Figure 2: Isolated Footing Section Elevation A-A (القطاع الرأسي وتفاصيل التسليح الإنشائي)</div>
        </div>
        """
    elif img_footing_b64:
        drawings_html = f"""
        <div class="drawing-box" style="margin-top:20px;">
            <img src="{img_footing_b64}" alt="Footing Detailing">
            <div class="drawing-caption">Figure 1: Isolated Footing Structural Detailing Sketch (المخطط الإنشائي وتفاصيل تسليح القاعدة)</div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ECP 203 - Isolated Footing Calculation Sheet</title>
    {_get_base_report_css()}
</head>
<body>

<div class="report-container">

    <!-- Top Action Bar -->
    <div class="action-bar no-print">
        <div style="font-weight:700; font-size:1.05rem;">📑 مذكرة الحسابات الإنشائية — Isolated Footing Design Sheet</div>
        <button class="btn-print" onclick="window.print();">🖨️ طباعة المذكرة / حفظ كـ PDF (Print / Save as PDF)</button>
    </div>

    <!-- Report Header -->
    <div class="report-header">
        <div class="header-title">
            <h1>مذكرة الحسابات والتصميم الإنشائي للقواعد المنفصلة (Isolated Footing)</h1>
            <span class="code-badge">الكود المصري لتصميم وتنفيذ المنشآت الخرسانية ECP 203-2018</span>
        </div>
        <div class="header-meta">
            <div><b>المشروع:</b> {project_name}</div>
            <div><b>تاريخ التصميم:</b> {now_str}</div>
        </div>
    </div>

    <!-- Section 1: Inputs & Parameters -->
    <div class="section-title">1. مدخلات التصميم وأبعاد العمود والتربة (Parameters & Loads)</div>
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">Column Size (bc × tc)</div>
            <div class="card-val">{col_bc:.0f} × {col_tc:.0f} cm</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Service Load (P_service)</div>
            <div class="card-val">{P_serv:.2f} Ton</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Ultimate Load (Pu)</div>
            <div class="card-val" style="color:#1e40af;">{Pu:.2f} Ton</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Allowable Soil Stress (q_all)</div>
            <div class="card-val">{q_all:.2f} kg/cm²</div>
        </div>
    </div>

    <!-- Section 2: Footing Dimensions & Reinforcement -->
    <div class="section-title">2. أبعاد وتفاصيل تسليح القاعدة المسلحة (RC Footing Output)</div>
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">RC Footing Dimensions (L × B)</div>
            <div class="card-val" style="color:#1e40af;">{L_rc:.2f} × {B_rc:.2f} m</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Effective Depth (d)</div>
            <div class="card-val">{d_rc:.0f} cm</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Reinforcement in Long Dir (L)</div>
            <div class="card-val" style="color:#15803d;">{rebar_L_str}</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">Reinforcement in Short Dir (B)</div>
            <div class="card-val" style="color:#15803d;">{rebar_B_str}</div>
        </div>
    </div>

    {drawings_html}

    <!-- Sign-off Block -->
    <div class="signature-block">
        <div class="sig-box">
            <div class="sig-title">مهندس التصميم الإنشائي (Designer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">المراجعة الهندسية (Reviewer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">اعتماد المكتب الاستشاري (Approval):</div>
            <div style="margin-top:20px; color:#94a3b8;">الختم والتاريخ: ______________</div>
        </div>
    </div>

</div>

</body>
</html>
"""
    return html_content


def generate_column_survey_report_html(
    project_name: str = "ECP 203 Column Quantity Survey",
    b: float = 30.0,
    t: float = 60.0,
    H: float = 300.0,
    t_slab: float = 20.0,
    fcu: float = 350.0,
    n_cols: int = 15,
    n_bars: int = 8,
    phi_main: int = 16,
    n_rows: int = 2,
    tie_type: str = "Automatic",
    n_st_m: int = 6,
    phi_st: int = 8,
    is_top_floor: bool = False,
    lap_factor: float = 50.0,
    L_bar_m: float = 4.0,
    L_bar_cm: float = 400.0,
    w_main_total_kg: float = 757.0,
    w_main_total_ton: float = 0.757,
    L_tie_m: float = 2.4,
    L_tie_cm: float = 240.0,
    n_ties_per_col: int = 18,
    w_st_total_kg: float = 255.0,
    w_st_total_ton: float = 0.255,
    vol_col_single_m3: float = 0.54,
    vol_col_total_m3: float = 8.10,
    w_steel_total_kg: float = 1012.0,
    w_steel_total_ton: float = 1.012,
    steel_rate_kg_m3: float = 124.9,
    cement_tons: float = 2.84,
    cement_bags: int = 57,
    sand_m3: float = 3.24,
    gravel_m3: float = 6.48,
    water_liters: float = 1418.0,
    img_plan_b64: Optional[str] = None,
    img_elev_b64: Optional[str] = None,
    col_results: Optional[List[Dict[str, Any]]] = None,
    drawings_list: Optional[List[Dict[str, Any]]] = None,
    slab_results: Optional[List[Dict[str, Any]]] = None,
    slab_drawings_list: Optional[List[Dict[str, Any]]] = None,
    pricing_data: Optional[Dict[str, Any]] = None,
    owner_name: Optional[str] = None,
) -> str:
    """
    Generates a print-ready, professional HTML/PDF calculation sheet for the
    Concrete Column & Flat Slab Quantity Survey with Material Pricing (Customs module) according to ECP 203.
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    top_floor_str = "دور أخير (Top Floor)" if is_top_floor else "متكرر (Typical Floor - Overlap Splice)"

    owner_html = ""
    if owner_name and str(owner_name).strip():
        owner_html = f"""<div style="font-size: 1.05rem; font-weight: 700; color: #1e3a8a; margin: 4px 0 6px 0;"><b>اسم المالك:</b> <span style="color:#0f172a; font-weight: 800;">{str(owner_name).strip()}</span></div>"""

    drawings_html = ""
    combined_drawings = list(drawings_list or [])
    if slab_drawings_list:
        combined_drawings.extend(slab_drawings_list)

    if combined_drawings and len(combined_drawings) > 0:
        drawings_cards = ""
        for idx, d in enumerate(combined_drawings, 1):
            d_name = d.get("name", f"Model {idx}")
            d_b = d.get("b", 30.0)
            d_t = d.get("t", 60.0)
            d_nb = d.get("n_bars", 8)
            d_phi = d.get("phi_main", 16)
            d_img = d.get("img_b64", "")
            d_is_slab = "lx" in d
            if d_is_slab:
                d_desc = f"{d.get('lx', 10):.1f} × {d.get('ly', 8):.1f} m | ts = {d.get('ts', 20):.0f} cm"
                d_label = f"📐 مخطط وتفريد تسليح بلاطة مسطحة: <b style='color:#059669;'>{d_name}</b>"
            else:
                d_desc = f"{d_b:.0f} × {d_t:.0f} cm | {d_nb} Φ {d_phi} mm"
                d_label = f"📐 مخطط وتفريد تسليح نموذج عمود: <b style='color:#2563eb;'>{d_name}</b>"

            if d_img:
                drawings_cards += f"""
                <div class="drawing-card" style="margin: 18px 0 24px 0; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 12px; background: #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.05); page-break-inside: avoid;">
                    <div style="font-size: 1.02rem; font-weight: 800; color: #1e3a8a; margin-bottom: 8px; text-align: right; border-bottom: 2px solid #3b82f6; padding-bottom: 4px; display:flex; justify-content:space-between; align-items:center;">
                        <span>{d_label}</span>
                        <span style="font-size:0.90rem; color:#475569;" dir="ltr">{d_desc}</span>
                    </div>
                    <div style="text-align: center;">
                        <img src="{d_img}" alt="CAD Drawing {d_name}" style="max-width: 100%; height: auto; border-radius: 6px;">
                    </div>
                </div>
                """
        drawings_html = f"""
        <div class="section-title">2. المخططات الإنشائية وتفريد التسليح للعناصر ({len(combined_drawings)} نماذج ومخططات)</div>
        {drawings_cards}
        """
    elif img_plan_b64:
        drawings_html = f"""
        <div class="section-title">2. المخطط الإنشائي المتكامل وتفريد التسليح (Structural Drawings & BBS Detailing)</div>
        <div class="drawing-box" style="margin:16px 0; text-align:center;">
            <img src="{img_plan_b64}" alt="Unified CAD Drawing" style="max-width:100%; height:auto; border-radius:8px; border:1px solid #cbd5e1; box-shadow:0 3px 8px rgba(0,0,0,0.06);">
        </div>
        """

    # Multi-Type or Single Type Rendering Logic for Columns
    total_cols_count = sum(r.get("n_cols", 0) for r in col_results) if col_results else n_cols
    total_vol_all = sum(r.get("vol_col_total_m3", r.get("vol_m3", 0.0)) for r in col_results) if col_results else vol_col_total_m3
    total_w_main_kg_all = sum(r.get("w_main_total_kg", r.get("w_main_kg", 0.0)) for r in col_results) if col_results else w_main_total_kg
    total_w_st_kg_all = sum(r.get("w_st_total_kg", r.get("w_tie_col_kg", 0.0)) for r in col_results) if col_results else w_st_total_kg
    total_w_steel_kg_all = total_w_main_kg_all + total_w_st_kg_all
    total_w_steel_ton_all = total_w_steel_kg_all / 1000.0
    overall_rate = (total_w_steel_kg_all / total_vol_all) if total_vol_all > 0 else 0.0

    specs_rows = ""
    takeoff_body_rows = ""
    total_steel_linear_m = 0.0
    item_counter = 1
    rebar_by_dia_rg = {}

    if col_results and len(col_results) > 0:
        for r in col_results:
            c_name = r.get("name", "C")
            c_b = r.get("b", 30.0)
            c_t = r.get("t", 60.0)
            c_nc = r.get("n_cols", 1)
            c_nb = r.get("n_bars", 8)
            c_phi = r.get("phi_main", 16)
            c_nr = r.get("n_rows", 2)
            c_tie = r.get("tie_type", "Box").split(' ')[0]
            specs_rows += f"""
            <tr>
                <td style="font-weight:800; color:#1e3a8a; text-align:right;">{c_name}</td>
                <td class="val-cell"><span dir="ltr">{c_b:.0f} × {c_t:.0f} cm</span></td>
                <td class="val-cell" style="font-weight:700;"><span dir="ltr">{c_nc}</span> عمود</td>
                <td class="val-cell"><span dir="ltr">H = {H/100:.2f} m ({H:.0f} cm)</span></td>
                <td class="val-cell"><span dir="ltr">ts = {t_slab:.0f} cm</span></td>
                <td class="val-cell" style="color:#b91c1c; font-weight:700;"><span dir="ltr">{c_nb} Φ {c_phi} mm [{c_nr} Rows]</span></td>
                <td class="val-cell" style="color:#15803d; font-weight:700;"><span dir="ltr">{n_st_m} Φ {phi_st}/m'</span> | {c_tie}</td>
            </tr>
            """

            c_L_bar_m = r.get("L_bar_m", 4.0)
            c_L_bar_cm = r.get("L_bar_cm", 400.0)
            c_w_main_kg = r.get("w_main_total_kg", 0.0)
            c_w_main_ton = r.get("w_main_total_ton", 0.0)
            c_n_ties = r.get("n_ties_per_col", 18)
            c_L_tie_m = r.get("L_tie_m", 2.0)
            c_L_tie_cm = r.get("L_tie_cm", 200.0)
            c_w_st_kg = r.get("w_st_total_kg", 0.0)
            c_w_st_ton = r.get("w_st_total_ton", 0.0)
            c_vol_single = r.get("vol_col_single_m3", 0.0)
            c_vol_total = r.get("vol_col_total_m3", 0.0)

            foot_rep_tag = f" + رجل <span dir='ltr'>{r.get('L_foot_cm', 0):.0f}cm</span>" if r.get("L_foot_cm", 0) > 0 else ""
            top_rep_tag = f"جنش <span dir='ltr'>{((lap_factor * c_phi) / 10.0):.0f}cm</span>" if is_top_floor else f"وصلة <span dir='ltr'>{lap_factor:.0f}Φ</span>"

            takeoff_body_rows += f"""
            <tr style="background:#f8fafc;">
                <td style="font-weight:bold; text-align:right; color:#1e3a8a;">{item_counter}.1. خرسانة مسلحة ({c_name})</td>
                <td class="val-cell" style="font-weight:bold; color:#1e3a8a;"><span dir="ltr">{c_b:.0f} × {c_t:.0f} cm</span></td>
                <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{c_nc}</span> عمود</td>
                <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{c_nc}</span> صبة</td>
                <td class="val-cell"><span dir="ltr">H = {H/100:.2f} m</span></td>
                <td class="val-cell" style="font-weight:bold; color:#1e40af; background:#eff6ff;"><span dir="ltr">{c_vol_total:.2f} m³</span></td>
                <td style="font-size:0.85rem; color:#64748b;">حجم العمود = <span dir="ltr">{c_vol_single:.3f} m³</span> (صافي <span dir="ltr">H={H/100:.2f}m</span>)</td>
            </tr>
            <tr>
                <td style="font-weight:bold; text-align:right; color:#b91c1c;">{item_counter}.2. تسليح رئيسي ({c_name})</td>
                <td class="val-cell" style="font-weight:bold; color:#b91c1c;"><span dir="ltr">{c_nb} Φ {c_phi} mm [{c_nr} Rows]</span></td>
                <td class="val-cell"><span dir="ltr">{c_nc}</span> عمود</td>
                <td class="val-cell" style="font-weight:bold; color:#b91c1c;"><span dir="ltr">{c_nc * c_nb}</span> قطعة<br><span style="font-size:0.75rem; color:#991b1b;" dir="ltr">({c_nb} قطعة/عمود)</span></td>
                <td class="val-cell" style="font-weight:bold; color:#15803d;"><span dir="ltr">{c_L_bar_m:.2f} m'</span> ({c_L_bar_cm:.0f} cm)</td>
                <td class="val-cell" style="font-weight:bold; color:#b91c1c; background:#fef2f2;"><span dir="ltr">{c_w_main_kg:.1f} kg ({c_w_main_ton:.3f} Ton)</span></td>
                <td style="font-size:0.85rem; color:#64748b;">طول السيخ = <span dir="ltr">{c_L_bar_m:.2f}m</span> (ارتفاع <span dir="ltr">{H:.0f}</span> + سقف <span dir="ltr">{t_slab:.0f}</span> + {top_rep_tag}{foot_rep_tag})</td>
            </tr>
            <tr style="background:#f8fafc;">
                <td style="font-weight:bold; text-align:right; color:#15803d; border-bottom:3px solid #334155 !important;">{item_counter}.3. كانات ({c_name})</td>
                <td class="val-cell" style="font-weight:bold; color:#15803d; border-bottom:3px solid #334155 !important;"><span dir="ltr">{c_tie} - Φ{phi_st} mm</span></td>
                <td class="val-cell" style="border-bottom:3px solid #334155 !important;"><span dir="ltr">{c_nc}</span> عمود</td>
                <td class="val-cell" style="font-weight:bold; color:#15803d; border-bottom:3px solid #334155 !important;"><span dir="ltr">{c_nc * c_n_ties}</span> قطعة<br><span style="font-size:0.75rem; color:#166534;" dir="ltr">({c_n_ties} كانة/عمود)</span></td>
                <td class="val-cell" style="font-weight:bold; color:#15803d; border-bottom:3px solid #334155 !important;"><span dir="ltr">{c_L_tie_m:.2f} m'</span> ({c_L_tie_cm:.0f} cm)</td>
                <td class="val-cell" style="font-weight:bold; color:#15803d; background:#f0fdf4; border-bottom:3px solid #334155 !important;"><span dir="ltr">{c_w_st_kg:.1f} kg ({c_w_st_ton:.3f} Ton)</span></td>
                <td style="font-size:0.85rem; color:#64748b; border-bottom:3px solid #334155 !important;">طول الكانة = <span dir="ltr">{c_L_tie_m:.2f}m</span> (كثافة <span dir="ltr">{n_st_m} Φ{phi_st}/m'</span> | كانة <span dir="ltr">{c_b-2*2.5:.0f}×{c_t-2*2.5:.0f} cm</span>)</td>
            </tr>
            """
            item_counter += 1

    # Flat Slabs Section in HTML
    slab_specs_html = ""
    slab_takeoff_rows = ""
    total_slabs_vol_rep = 0.0
    total_slabs_steel_kg_rep = 0.0

    if slab_results and len(slab_results) > 0:
        slab_specs_body = ""
        for s in slab_results:
            s_name = s.get("name", "S1")
            s_lx = s.get("lx", 10.0)
            s_ly = s.get("ly", 8.0)
            s_ts = s.get("ts", 20.0)
            s_n_rep = s.get("n_rep", 1)
            s_fcu = s.get("fcu", 350.0)
            s_vol = s.get("vol_total_m3", 0.0)
            s_w_st = s.get("w_steel_total_kg", 0.0)
            s_nb_bx = s.get("nb_bx", 6)
            s_phi_bx = s.get("phi_bx", 12)
            s_nb_by = s.get("nb_by", 6)
            s_phi_by = s.get("phi_by", 12)
            s_nb_tx = s.get("nb_tx", 6)
            s_phi_tx = s.get("phi_tx", 10)
            s_nb_ty = s.get("nb_ty", 6)
            s_phi_ty = s.get("phi_ty", 10)

            total_slabs_vol_rep += s_vol
            total_slabs_steel_kg_rep += s_w_st

            slab_specs_body += f"""
            <tr>
                <td style="font-weight:bold; color:#065f46; text-align:right;">{s_name} ({s_n_rep} تكرار)</td>
                <td class="val-cell"><span dir="ltr">{s_lx:.2f} × {s_ly:.2f} m</span></td>
                <td class="val-cell"><span dir="ltr">{s_ts:.0f} cm</span></td>
                <td class="val-cell"><span dir="ltr">{s_fcu:.0f} kg/m³</span></td>
                <td class="val-cell" style="color:#1d4ed8; font-weight:bold;"><span dir="ltr">{s_nb_bx}Φ{s_phi_bx}/m' (X) + {s_nb_by}Φ{s_phi_by}/m' (Y)</span></td>
                <td class="val-cell" style="color:#15803d; font-weight:bold;"><span dir="ltr">{s_nb_tx}Φ{s_phi_tx}/m' (X) + {s_nb_ty}Φ{s_phi_ty}/m' (Y)</span></td>
                <td class="val-cell" style="font-weight:bold; color:#065f46; background:#f0fdf4;"><span dir="ltr">{s_vol:.2f} m³</span></td>
                <td class="val-cell" style="font-weight:bold; color:#92400e; background:#fffbeb;"><span dir="ltr">{s_w_st:.1f} kg</span></td>
            </tr>
            """

            # Flat slab rebar takeoff rows
            s_n_bx = s.get("n_runs_bx", 0) * s_n_rep
            s_n_by = s.get("n_runs_by", 0) * s_n_rep
            s_n_tx = s.get("n_runs_tx", 0) * s_n_rep
            s_n_ty = s.get("n_runs_ty", 0) * s_n_rep

            slab_takeoff_rows += f"""
            <tr style="background:#f0fdf4;">
                <td style="font-weight:bold; text-align:right; color:#065f46;">{item_counter}.1. خرسانة مسلحة ({s_name})</td>
                <td class="val-cell" style="font-weight:bold; color:#065f46;"><span dir="ltr">{s_lx:.2f}×{s_ly:.2f} m (ts={s_ts:.0f}cm)</span></td>
                <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{s_n_rep}</span> مسطح</td>
                <td class="val-cell"><span dir="ltr">ts = {s_ts:.0f} cm</span></td>
                <td class="val-cell" style="font-weight:bold; color:#065f46; background:#dcfce7;"><span dir="ltr">{s_vol:.2f} m³</span></td>
                <td style="font-size:0.85rem; color:#64748b;">مسطح = <span dir="ltr">{s_lx*s_ly:.1f} m²</span> للبلاطة الواحدة</td>
            </tr>
            <tr>
                <td style="font-weight:bold; text-align:right; color:#1d4ed8;">{item_counter}.2. شبكة سفلية ({s_name})</td>
                <td class="val-cell" style="color:#1d4ed8; font-weight:bold;"><span dir="ltr">{s_nb_bx}Φ{s_phi_bx} (X) + {s_nb_by}Φ{s_phi_by} (Y)</span></td>
                <td class="val-cell"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                <td class="val-cell" style="font-weight:bold; color:#1d4ed8;"><span dir="ltr">{s_n_bx + s_n_by}</span> قطعة<br><span style="font-size:0.78rem; color:#1e40af;" dir="ltr">(X={s_n_bx}, Y={s_n_by})</span></td>
                <td class="val-cell" style="font-weight:bold; color:#15803d;"><span dir="ltr">X={s.get('L_cut_bx',0):.2f}m, Y={s.get('L_cut_by',0):.2f}m</span></td>
                <td class="val-cell" style="font-weight:bold; color:#1d4ed8; background:#eff6ff;"><span dir="ltr">{s.get('w_bx_kg',0)+s.get('w_by_kg',0):.1f} kg</span></td>
                <td style="font-size:0.85rem; color:#64748b;">سفلي X (<span dir="ltr">{s.get('w_bx_kg',0):.1f}kg</span>) + سفلي Y (<span dir="ltr">{s.get('w_by_kg',0):.1f}kg</span>)</td>
            </tr>
            <tr style="background:#f0fdf4;">
                <td style="font-weight:bold; text-align:right; color:#15803d; border-bottom:1px solid #cbd5e1 !important;">{item_counter}.3. شبكة علوية وكراسي ({s_name})</td>
                <td class="val-cell" style="color:#15803d; font-weight:bold; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{s_nb_tx}Φ{s_phi_tx} (X) + {s_nb_ty}Φ{s_phi_ty} (Y)</span></td>
                <td class="val-cell" style="border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                <td class="val-cell" style="font-weight:bold; color:#15803d; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{s_n_tx + s_n_ty + s.get('n_chairs',0)}</span> قطعة<br><span style="font-size:0.78rem; color:#166534;" dir="ltr">(X={s_n_tx}, Y={s_n_ty} + {s.get('n_chairs',0)} كرسي)</span></td>
                <td class="val-cell" style="font-weight:bold; color:#15803d; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">X={s.get('L_cut_tx',0):.2f}m, Y={s.get('L_cut_ty',0):.2f}m</span></td>
                <td class="val-cell" style="font-weight:bold; color:#15803d; background:#dcfce7; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{s.get('w_tx_kg',0)+s.get('w_ty_kg',0)+s.get('w_chairs_kg',0):.1f} kg</span></td>
                <td style="font-size:0.85rem; color:#64748b; border-bottom:1px solid #cbd5e1 !important;">علوي X+Y (<span dir="ltr">{s.get('w_tx_kg',0)+s.get('w_ty_kg',0):.1f}kg</span>) + كراسي (<span dir="ltr">{s.get('w_chairs_kg',0):.1f}kg</span>)</td>
            </tr>
            """

            if s.get("top_add_models_res"):
                for m_i, tm in enumerate(s.get("top_add_models_res", []), 1):
                    if tm["w_total_kg"] > 0:
                        tot_pcs_x = tm["n_runs_x"] * tm["n_zones"] * s_n_rep
                        tot_pcs_y = tm["n_runs_y"] * tm["n_zones"] * s_n_rep
                        tot_pcs = tot_pcs_x + tot_pcs_y
                        slab_takeoff_rows += f"""
                        <tr style="background:#fffbeb;">
                            <td style="font-weight:bold; text-align:right; color:#b45309; border-bottom:1px solid #cbd5e1 !important;">{item_counter}.4.{m_i}. إضافي علوي [{tm['name']}] ({s_name})</td>
                            <td class="val-cell" style="color:#b45309; font-weight:bold; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">X={tm['nx']:.0f}Φ{tm['phi']}/م' + Y={tm['ny']:.0f}Φ{tm['phi']}/م' ({tm['n_zones']} مناطق)</span></td>
                            <td class="val-cell" style="border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                            <td class="val-cell" style="font-weight:bold; color:#b45309; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{tot_pcs}</span> قطعة<br><span style="font-size:0.78rem; color:#92400e;" dir="ltr">(X={tot_pcs_x}, Y={tot_pcs_y})</span></td>
                            <td class="val-cell" style="font-weight:bold; color:#b45309; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">Lx={tm['lx']:.2f}m, Ly={tm['ly']:.2f}m</span></td>
                            <td class="val-cell" style="font-weight:bold; color:#b45309; background:#fef3c7; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{tm['w_total_kg']:.1f} kg</span></td>
                            <td style="font-size:0.85rem; color:#64748b; border-bottom:1px solid #cbd5e1 !important;">علوي X: <span dir="ltr">{tot_pcs_x} قطعة ({tm['w_x_kg']:.1f}kg)</span> + علوي Y: <span dir="ltr">{tot_pcs_y} قطعة ({tm['w_y_kg']:.1f}kg)</span></td>
                        </tr>
                        """
            elif s.get("w_top_add_kg", 0.0) > 0:
                n_tax_x = s.get('n_runs_x', 0) * s_n_rep
                n_tax_y = s.get('n_runs_y', 0) * s_n_rep
                n_tax_tot = n_tax_x + n_tax_y
                w_tax_tot = s.get("w_top_add_kg", 0.0)
                slab_takeoff_rows += f"""
                <tr style="background:#fffbeb;">
                    <td style="font-weight:bold; text-align:right; color:#b45309; border-bottom:1px solid #cbd5e1 !important;">{item_counter}.4. حديد إضافي علوي ({s_name})</td>
                    <td class="val-cell" style="color:#b45309; font-weight:bold; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">X={s.get('nx',0):.0f}Φ{s.get('phi_top_add',12)}/م' + Y={s.get('ny',0):.0f}Φ{s.get('phi_top_add',12)}/م'</span></td>
                    <td class="val-cell" style="border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                    <td class="val-cell" style="font-weight:bold; color:#b45309; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{n_tax_tot}</span> قطعة<br><span style="font-size:0.78rem; color:#92400e;" dir="ltr">(X={n_tax_x}, Y={n_tax_y})</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#b45309; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">Lx={s.get('add_top_lx',0):.2f}m, Ly={s.get('add_top_ly',0):.2f}m</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#b45309; background:#fef3c7; border-bottom:1px solid #cbd5e1 !important;"><span dir="ltr">{w_tax_tot:.1f} kg</span></td>
                    <td style="font-size:0.85rem; color:#64748b; border-bottom:1px solid #cbd5e1 !important;">إضافي علوي X (<span dir="ltr">{s.get('w_top_add_x_kg',0):.1f}kg</span>) + إضافي علوي Y (<span dir="ltr">{s.get('w_top_add_y_kg',0):.1f}kg</span>)</td>
                </tr>
                """

            if s.get("btm_add_models_res"):
                for m_i, bm in enumerate(s.get("btm_add_models_res", []), 1):
                    if bm["w_total_kg"] > 0:
                        tot_pcs_x = bm["n_runs_x"] * bm["n_zones"] * s_n_rep
                        tot_pcs_y = bm["n_runs_y"] * bm["n_zones"] * s_n_rep
                        tot_pcs = tot_pcs_x + tot_pcs_y
                        slab_takeoff_rows += f"""
                        <tr style="background:#fffbeb;">
                            <td style="font-weight:bold; text-align:right; color:#b45309; border-bottom:2px solid #065f46 !important;">{item_counter}.5.{m_i}. إضافي سفلي [{bm['name']}] ({s_name})</td>
                            <td class="val-cell" style="color:#b45309; font-weight:bold; border-bottom:2px solid #065f46 !important;"><span dir="ltr">X={bm['nx']:.0f}Φ{bm['phi']}/م' + Y={bm['ny']:.0f}Φ{bm['phi']}/م' ({bm['n_zones']} مناطق)</span></td>
                            <td class="val-cell" style="border-bottom:2px solid #065f46 !important;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                            <td class="val-cell" style="font-weight:bold; color:#b45309; border-bottom:2px solid #065f46 !important;"><span dir="ltr">{tot_pcs}</span> قطعة<br><span style="font-size:0.78rem; color:#92400e;" dir="ltr">(X={tot_pcs_x}, Y={tot_pcs_y})</span></td>
                            <td class="val-cell" style="font-weight:bold; color:#b45309; border-bottom:2px solid #065f46 !important;"><span dir="ltr">Lx={bm['lx']:.2f}m, Ly={bm['ly']:.2f}m</span></td>
                            <td class="val-cell" style="font-weight:bold; color:#b45309; background:#fef3c7; border-bottom:2px solid #065f46 !important;"><span dir="ltr">{bm['w_total_kg']:.1f} kg</span></td>
                            <td style="font-size:0.85rem; color:#64748b; border-bottom:2px solid #065f46 !important;">سفلي X: <span dir="ltr">{tot_pcs_x} قطعة ({bm['w_x_kg']:.1f}kg)</span> + سفلي Y: <span dir="ltr">{tot_pcs_y} قطعة ({bm['w_y_kg']:.1f}kg)</span></td>
                        </tr>
                        """
            elif s.get("w_btm_add_kg", 0.0) > 0:
                n_bax_x = s.get('n_runs_x', 0) * s_n_rep
                n_bax_y = s.get('n_runs_y', 0) * s_n_rep
                n_bax_tot = n_bax_x + n_bax_y
                w_bax_tot = s.get("w_btm_add_kg", 0.0)
                slab_takeoff_rows += f"""
                <tr style="background:#fffbeb;">
                    <td style="font-weight:bold; text-align:right; color:#b45309; border-bottom:2px solid #065f46 !important;">{item_counter}.5. حديد إضافي سفلي ({s_name})</td>
                    <td class="val-cell" style="color:#b45309; font-weight:bold; border-bottom:2px solid #065f46 !important;"><span dir="ltr">X={s.get('nx',0):.0f}Φ{s.get('phi_btm_add',12)}/م' + Y={s.get('ny',0):.0f}Φ{s.get('phi_btm_add',12)}/م'</span></td>
                    <td class="val-cell" style="border-bottom:2px solid #065f46 !important;"><span dir="ltr">{s_n_rep}</span> بلاطة</td>
                    <td class="val-cell" style="font-weight:bold; color:#b45309; border-bottom:2px solid #065f46 !important;"><span dir="ltr">{n_bax_tot}</span> قطعة<br><span style="font-size:0.78rem; color:#92400e;" dir="ltr">(X={n_bax_x}, Y={n_bax_y})</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#b45309; border-bottom:2px solid #065f46 !important;"><span dir="ltr">Lx={s.get('add_btm_lx',0):.2f}m, Ly={s.get('add_btm_ly',0):.2f}m</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#b45309; background:#fef3c7; border-bottom:2px solid #065f46 !important;"><span dir="ltr">{w_bax_tot:.1f} kg</span></td>
                    <td style="font-size:0.85rem; color:#64748b; border-bottom:2px solid #065f46 !important;">إضافي سفلي X (<span dir="ltr">{s.get('w_btm_add_x_kg',0):.1f}kg</span>) + إضافي سفلي Y (<span dir="ltr">{s.get('w_btm_add_y_kg',0):.1f}kg</span>)</td>
                </tr>
                """

            item_counter += 1

        slab_specs_html = f"""
        <div class="section-title" style="background:#065f46; margin-top:20px;">1.2. البيانات الهندسية للبلاطات المسطحة Flat Slabs ({len(slab_results)} نماذج — إجمالي {total_slabs_vol_rep:.2f} m³)</div>
        <table class="survey-table" style="margin-bottom:16px;">
            <thead>
                <tr style="background:#065f46 !important;">
                    <th style="text-align:right;">النموذج</th>
                    <th>الأبعاد (Lx × Ly)</th>
                    <th>التخانة ts</th>
                    <th>العدد</th>
                    <th>الشبكة السفلية</th>
                    <th>الشبكة العلوية</th>
                    <th>الحجم الإجمالي</th>
                </tr>
            </thead>
            <tbody>
                {slab_specs_body}
            </tbody>
        </table>
        """

    # Combine totals
    grand_vol_concrete = total_vol_all + total_slabs_vol_rep
    grand_steel_kg = total_w_steel_kg_all + total_slabs_steel_kg_rep
    grand_steel_ton = grand_steel_kg / 1000.0
    grand_steel_rate = (grand_steel_kg / grand_vol_concrete) if grand_vol_concrete > 0 else 0.0

    # Pricing Table HTML
    pricing_table_html = ""
    c_grand_tot = 0.0
    if pricing_data:
        p_steel = pricing_data.get("price_steel", 40000.0)
        p_cement = pricing_data.get("price_cement", 4000.0)
        p_gravel = pricing_data.get("price_gravel", 600.0)
        p_sand = pricing_data.get("price_sand", 200.0)
        p_labor = pricing_data.get("price_labor", 2000.0)
        tot_cement_cols = (total_vol_all * fcu / 1000.0)
        tot_cement_slabs = sum(s.get("vol_total_m3", 0.0) * s.get("fcu", fcu) / 1000.0 for s in slab_results)
        tot_cement_ton = tot_cement_cols + tot_cement_slabs

        # Cost breakdown per element
        c_steel_cols = (total_w_steel_kg_all / 1000.0) * p_steel
        c_cement_cols = tot_cement_cols * p_cement
        c_gravel_cols = (total_vol_all * 0.80) * p_gravel
        c_sand_cols = (total_vol_all * 0.40) * p_sand
        c_labor_cols = total_vol_all * p_labor
        cost_cols_tot = c_steel_cols + c_cement_cols + c_gravel_cols + c_sand_cols + c_labor_cols
        rate_cols_per_m3 = (cost_cols_tot / total_vol_all) if total_vol_all > 0 else 0.0

        c_steel_cols_m3 = (c_steel_cols / total_vol_all) if total_vol_all > 0 else 0.0
        c_cement_cols_m3 = (c_cement_cols / total_vol_all) if total_vol_all > 0 else 0.0
        c_gravel_cols_m3 = (c_gravel_cols / total_vol_all) if total_vol_all > 0 else 0.0
        c_sand_cols_m3 = (c_sand_cols / total_vol_all) if total_vol_all > 0 else 0.0

        c_steel_slabs = (total_slabs_steel_kg_rep / 1000.0) * p_steel
        c_cement_slabs = tot_cement_slabs * p_cement
        c_gravel_slabs = (total_slabs_vol_rep * 0.80) * p_gravel
        c_sand_slabs = (total_slabs_vol_rep * 0.40) * p_sand
        c_labor_slabs = total_slabs_vol_rep * p_labor
        cost_slabs_tot = c_steel_slabs + c_cement_slabs + c_gravel_slabs + c_sand_slabs + c_labor_slabs
        rate_slabs_per_m3 = (cost_slabs_tot / total_slabs_vol_rep) if total_slabs_vol_rep > 0 else 0.0

        c_steel_slabs_m3 = (c_steel_slabs / total_slabs_vol_rep) if total_slabs_vol_rep > 0 else 0.0
        c_cement_slabs_m3 = (c_cement_slabs / total_slabs_vol_rep) if total_slabs_vol_rep > 0 else 0.0
        c_gravel_slabs_m3 = (c_gravel_slabs / total_slabs_vol_rep) if total_slabs_vol_rep > 0 else 0.0
        c_sand_slabs_m3 = (c_sand_slabs / total_slabs_vol_rep) if total_slabs_vol_rep > 0 else 0.0

        c_steel_tot = grand_steel_ton * p_steel
        c_cement_tot = tot_cement_ton * p_cement
        c_gravel_tot = (grand_vol_concrete * 0.80) * p_gravel
        c_sand_tot = (grand_vol_concrete * 0.40) * p_sand
        c_labor_tot = grand_vol_concrete * p_labor
        c_grand_tot = c_steel_tot + c_cement_tot + c_gravel_tot + c_sand_tot + c_labor_tot
        cost_per_m3_all_inclusive = (c_grand_tot / grand_vol_concrete) if grand_vol_concrete > 0 else 0.0

        pricing_table_html = f"""
        <div class="section-title" style="background:#b45309; margin-top:24px;">4. جدول المقايسة المالية التقديرية وحصر أسعار المواد والمصنعيات (Bill of Quantities & Prices)</div>
        <table class="survey-table" style="margin-bottom:20px;">
            <thead>
                <tr style="background:#b45309 !important;">
                    <th style="text-align:right;">م</th>
                    <th style="text-align:right;">البند بمواصفاته الفنية</th>
                    <th>الوحدة</th>
                    <th>الكمية المحصورة</th>
                    <th>سعر البند (ج.م)</th>
                    <th style="background:#92400e !important;">إجمالي السعر (ج.م)</th>
                    <th>ملاحظات وتفاصيل الحساب</th>
                </tr>
            </thead>
            <tbody>
                <tr style="background:#f8fafc;">
                    <td style="font-weight:bold;">1</td>
                    <td style="font-weight:bold; text-align:right; color:#1e3a8a;">خرسانة مسلحة للأعمدة الخرسانية (شاملة المواد والمصنعيات)</td>
                    <td class="val-cell">متر مكعب (m³)</td>
                    <td class="val-cell" style="font-weight:bold; color:#1e3a8a;"><span dir="ltr">{total_vol_all:.2f} m³</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#1e3a8a;"><span dir="ltr">{rate_cols_per_m3:,.2f}</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#1e3a8a; background:#eff6ff;"><span dir="ltr">{cost_cols_tot:,.2f} ج.م</span></td>
                    <td style="font-size:0.85rem; color:#64748b;">حديد: <span dir="ltr">{c_steel_cols_m3:,.0f}</span> + أسمنت: <span dir="ltr">{c_cement_cols_m3:,.0f}</span> + سن: <span dir="ltr">{c_gravel_cols_m3:,.0f}</span> + رمل: <span dir="ltr">{c_sand_cols_m3:,.0f}</span> + مصنعية: <span dir="ltr">{p_labor:,.0f}</span> ج.م/م³</td>
                </tr>
                <tr style="background:#f0fdf4;">
                    <td style="font-weight:bold;">2</td>
                    <td style="font-weight:bold; text-align:right; color:#065f46;">خرسانة مسلحة للبلاطات المسطحة Flat Slabs (شاملة المواد والمصنعيات)</td>
                    <td class="val-cell">متر مكعب (m³)</td>
                    <td class="val-cell" style="font-weight:bold; color:#065f46;"><span dir="ltr">{total_slabs_vol_rep:.2f} m³</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#065f46;"><span dir="ltr">{rate_slabs_per_m3:,.2f}</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#065f46; background:#dcfce7;"><span dir="ltr">{cost_slabs_tot:,.2f} ج.م</span></td>
                    <td style="font-size:0.85rem; color:#64748b;">حديد: <span dir="ltr">{c_steel_slabs_m3:,.0f}</span> + أسمنت: <span dir="ltr">{c_cement_slabs_m3:,.0f}</span> + سن: <span dir="ltr">{c_gravel_slabs_m3:,.0f}</span> + رمل: <span dir="ltr">{c_sand_slabs_m3:,.0f}</span> + مصنعية: <span dir="ltr">{p_labor:,.0f}</span> ج.م/م³</td>
                </tr>
                <tr style="background:#fffbeb; font-weight:bold; color:#b45309; border-top:2px solid #ca8a04;">
                    <td style="font-weight:bold;">3</td>
                    <td style="font-weight:bold; text-align:right;">إجمالي توريد حديد التسليح للمشروع (أعمدة + بلاطات)</td>
                    <td class="val-cell">طن (Ton)</td>
                    <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{grand_steel_ton:.3f} Ton</span></td>
                    <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{p_steel:,.2f}</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#92400e; background:#fef3c7;"><span dir="ltr">{c_steel_tot:,.2f} ج.م</span></td>
                    <td style="font-size:0.85rem;">إجمالي {grand_steel_kg:,.1f} kg (أعمدة <span dir="ltr">{total_w_steel_kg_all/1000.0:.3f}T</span> + بلاطات <span dir="ltr">{total_slabs_steel_kg_rep/1000.0:.3f}T</span>)</td>
                </tr>
                <tr style="background:#fffbeb;">
                    <td style="font-weight:bold;">4</td>
                    <td style="font-weight:bold; text-align:right; color:#78350f;">إجمالي توريد الأسمنت البورتلاندي العادي للمشروع</td>
                    <td class="val-cell">طن (Ton)</td>
                    <td class="val-cell"><span dir="ltr">{tot_cement_ton:.2f} Ton</span></td>
                    <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{p_cement:,.2f}</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#78350f;"><span dir="ltr">{c_cement_tot:,.2f} ج.م</span></td>
                    <td style="font-size:0.85rem; color:#64748b;">إجمالي <span dir="ltr">{round(tot_cement_ton * 20.0)}</span> شكارة 50kg (أعمدة <span dir="ltr">{tot_cement_cols:.2f}T</span> + بلاطات <span dir="ltr">{tot_cement_slabs:.2f}T</span>)</td>
                </tr>
                <tr style="background:#fffbeb;">
                    <td style="font-weight:bold;">5</td>
                    <td style="font-weight:bold; text-align:right; color:#78350f;">إجمالي توريد السن / الزلط المتدرج النظيف للخرسانة</td>
                    <td class="val-cell">متر مكعب (m³)</td>
                    <td class="val-cell"><span dir="ltr">{grand_vol_concrete * 0.80:.2f} m³</span></td>
                    <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{p_gravel:,.2f}</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#78350f;"><span dir="ltr">{c_gravel_tot:,.2f} ج.م</span></td>
                    <td style="font-size:0.85rem; color:#64748b;">نسبة زلط <span dir="ltr">0.80 m³/m³</span> خرسانة مسلحة</td>
                </tr>
                <tr style="background:#fffbeb;">
                    <td style="font-weight:bold;">6</td>
                    <td style="font-weight:bold; text-align:right; color:#78350f;">إجمالي توريد الرمل الحرش النظيف للخرسانة</td>
                    <td class="val-cell">متر مكعب (m³)</td>
                    <td class="val-cell"><span dir="ltr">{grand_vol_concrete * 0.40:.2f} m³</span></td>
                    <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{p_sand:,.2f}</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#78350f;"><span dir="ltr">{c_sand_tot:,.2f} ج.م</span></td>
                    <td style="font-size:0.85rem; color:#64748b;">نسبة رمل <span dir="ltr">0.40 m³/m³</span> خرسانة مسلحة</td>
                </tr>
                <tr style="background:#fffbeb;">
                    <td style="font-weight:bold;">7</td>
                    <td style="font-weight:bold; text-align:right; color:#78350f;">إجمالي مصنعيات الصب والحدادة والنجارة والتشغيل</td>
                    <td class="val-cell">متر مكعب (m³)</td>
                    <td class="val-cell"><span dir="ltr">{grand_vol_concrete:.2f} m³</span></td>
                    <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{p_labor:,.2f}</span></td>
                    <td class="val-cell" style="font-weight:bold; color:#78350f;"><span dir="ltr">{c_labor_tot:,.2f} ج.م</span></td>
                    <td style="font-size:0.85rem; color:#64748b;">تنفيذ وتشغيل متكامل لكافة مسطحات المشروع</td>
                </tr>
                <tr style="background:#fef08a !important; font-weight:bold; color:#854d0e; font-size:1.05rem; border-top:3px solid #ca8a04;">
                    <td colspan="2" style="text-align:right; font-weight:bold; font-size:1.05rem;">★ الإجمالي المالي العام الشامل للمشروع (Grand Total Budget)</td>
                    <td class="val-cell" style="font-weight:bold;">مشروع شامل (L.S)</td>
                    <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{grand_vol_concrete:.2f} m³ خرسانة</span></td>
                    <td class="val-cell" style="font-weight:bold;">-</td>
                    <td class="val-cell" style="font-weight:900; font-size:1.15rem; color:#92400e;"><span dir="ltr">{c_grand_tot:,.2f} EGP</span></td>
                    <td style="font-weight:bold; font-size:0.92rem;">شامل كافة المواد والمصنعيات بالكامل (متوسط <span dir="ltr">{cost_per_m3_all_inclusive:,.1f} ج.م/م³</span>)</td>
                </tr>
            </tbody>
        </table>
        """

    section1_html = f"""
    <div class="section-title">1. البيانات الهندسية لقطاعات ونماذج الأعمدة ({len(col_results or [])} نماذج — إجمالي {total_cols_count} عمود)</div>
    <table class="survey-table" style="margin-bottom:16px;">
        <thead>
            <tr>
                <th style="text-align:right;">النموذج</th>
                <th>أبعاد القطاع (b × t)</th>
                <th>العدد</th>
                <th>الارتفاع الصافي</th>
                <th>سقوط السقف</th>
                <th>التسليح الرئيسي</th>
                <th>الكانات</th>
            </tr>
        </thead>
        <tbody>
            {specs_rows}
        </tbody>
    </table>
    {slab_specs_html}
    """

    takeoff_table_html = f"""
    <table class="survey-table">
        <thead>
            <tr>
                <th style="text-align:right;">البند / Component</th>
                <th>القطاع / المقاس / المواصفة</th>
                <th>العدد</th>
                <th>عدد القطع (Pieces)</th>
                <th>طول القطع (Cut Length)</th>
                <th style="background-color:#1d4ed8 !important;">الوزن / الحجم الإجمالي</th>
                <th>ملاحظات الحصر والتفريد</th>
            </tr>
        </thead>
        <tbody>
            {takeoff_body_rows}
            {slab_takeoff_rows}
            <tr style="background:#eff6ff !important; font-weight:bold; color:#1e3a8a; font-size:0.95rem; border-top:2px solid #3b82f6;">
                <td style="text-align:right; font-weight:bold;">🔷 إجمالي الخرسانة المسلحة الكلية (أعمدة + بلاطات)</td>
                <td class="val-cell">كافة العناصر الخرسانية</td>
                <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{total_cols_count} عمود + {len(slab_results or [])} بلاطة</span></td>
                <td class="val-cell" style="font-weight:bold;">-</td>
                <td class="val-cell">-</td>
                <td class="val-cell" style="font-weight:bold; color:#1e40af; background:#dbeafe;"><span dir="ltr">{grand_vol_concrete:.2f} m³</span></td>
                <td style="font-size:0.85rem; color:#475569;">أعمدة: <span dir="ltr">{total_vol_all:.2f} m³</span> | بلاطات: <span dir="ltr">{total_slabs_vol_rep:.2f} m³</span></td>
            </tr>
            <tr class="survey-total-row">
                <td style="text-align:right; font-size:1.02rem;">✅ الإجمالي العام لحديد التسليح بالمشروع (أعمدة + بلاطات)</td>
                <td class="val-cell">كافة الأقطار والشبكات</td>
                <td class="val-cell">-</td>
                <td class="val-cell" style="font-weight:bold; font-size:1.05rem;">-</td>
                <td class="val-cell">-</td>
                <td class="val-cell" style="font-size:1.08rem; color:#854d0e;"><span dir="ltr">{grand_steel_kg:,.1f} kg ({grand_steel_ton:.3f} Ton)</span></td>
                <td>معدل استهلاك الحديد الكلي = <span dir="ltr">{grand_steel_rate:.1f} kg/m³</span></td>
            </tr>
        </tbody>
    </table>
    """

    grand_cement_t = (grand_vol_concrete * fcu) / 1000.0
    grand_cement_b = int(round((grand_vol_concrete * fcu) / 50.0))
    grand_sand_v = grand_vol_concrete * 0.40
    grand_gravel_v = grand_vol_concrete * 0.80
    grand_water_l = grand_vol_concrete * fcu * 0.50

    tot_area_slabs_rep = sum(s.get("area_total_m2", s.get("lx", 10.0) * s.get("ly", 8.0) * s.get("n_rep", 1)) for s in (slab_results or [])) if slab_results else 0.0
    cost_per_m2_slab_rep = (c_grand_tot / tot_area_slabs_rep) if (pricing_data and tot_area_slabs_rep > 0) else 0.0

    slabs_cost_m2_note_html = ""
    if slab_results and len(slab_results) > 0 and tot_area_slabs_rep > 0 and pricing_data:
        slabs_names_str = " + ".join(f"{s.get('name', 'S')}" for s in slab_results)
        slabs_areas_str = " + ".join(f"{s.get('name', 'S')} ({s.get('area_total_m2', s.get('lx',10.0)*s.get('ly',8.0)*s.get('n_rep',1)):.1f} m²)" for s in slab_results)
        slabs_cost_m2_note_html = f"""
        <div style="background:#0f172a; border:2px solid #6366f1; border-radius:10px; padding:16px 20px; margin-top:20px; margin-bottom:20px; color:#ffffff;">
            <div style="font-size:1.05rem; font-weight:bold; color:#a5b4fc; margin-bottom:12px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid rgba(165,180,252,0.3); padding-bottom:8px;">
                <div>📌 <b>ملاحظة مالية هامة وحساب متوسط تكلفة المتر المسطح (Cost per Square Meter Note)</b></div>
                <span style="font-size:0.85rem; background:rgba(99,102,241,0.3); padding:3px 12px; border-radius:10px;">{len(slab_results)} نماذج بلاطات ({slabs_names_str})</span>
            </div>
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:14px;">
                <div style="background:rgba(255,255,255,0.05); padding:12px 14px; border-radius:8px; border-right:4px solid #f59e0b;">
                    <div style="font-size:0.82rem; color:#cbd5e1; font-weight:bold;">★ الإجمالي المالي العام الشامل للمشروع:</div>
                    <div style="font-size:1.25rem; font-weight:bold; color:#fbbf24;" dir="ltr">{c_grand_tot:,.2f} EGP</div>
                </div>
                <div style="background:rgba(255,255,255,0.05); padding:12px 14px; border-radius:8px; border-right:4px solid #10b981;">
                    <div style="font-size:0.82rem; color:#cbd5e1; font-weight:bold;">📐 إجمالي مسطح نماذج البلاطات ({slabs_names_str}):</div>
                    <div style="font-size:1.25rem; font-weight:bold; color:#34d399;" dir="ltr">{tot_area_slabs_rep:,.2f} m²</div>
                    <div style="font-size:0.75rem; color:#a7f3d0; margin-top:2px;">{slabs_areas_str}</div>
                </div>
                <div style="background:rgba(56,189,248,0.15); padding:12px 14px; border-radius:8px; border-right:4px solid #38bdf8; border:1px solid rgba(56,189,248,0.3);">
                    <div style="font-size:0.82rem; color:#ffffff; font-weight:bold;">💰 تكلفة المتر المسطح بالجنيه (Cost / m²):</div>
                    <div style="font-size:1.35rem; font-weight:bold; color:#38bdf8;" dir="ltr">{cost_per_m2_slab_rep:,.2f} ج.م / م²</div>
                    <div style="font-size:0.75rem; color:#e0f2fe; margin-top:2px;">= ({c_grand_tot:,.0f} ج.م ÷ {tot_area_slabs_rep:,.1f} م²)</div>
                </div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>{project_name} - ECP 203</title>
    {_get_base_report_css()}
    <style>
        .survey-table th {{ background-color: #1e3a8a !important; color:#ffffff !important; font-size:0.92rem; font-weight:bold; }}
        .survey-table td {{ font-size:0.90rem; padding: 10px 8px; text-align:center; }}
        .survey-table tr:nth-child(even) {{ background-color: #f8fafc; }}
        .survey-total-row {{ background-color: #fef08a !important; font-weight:bold; color:#854d0e; font-size:0.95rem !important; border-top: 2px solid #ca8a04; }}
    </style>
</head>
<body>

<div class="report-container">

    <!-- Top Action Bar -->
    <div class="action-bar no-print">
        <div style="font-weight:700; font-size:1.05rem;">📊 {project_name}</div>
        <button class="btn-print" onclick="window.print();">🖨️ طباعة التقرير / حفظ كـ PDF (Print / Save as PDF)</button>
    </div>

    <!-- Report Header -->
    <div class="report-header">
        <div class="header-title">
            <h1 style="font-size: 1.45rem; font-weight: 900; color: #0f172a; margin-bottom: 4px; line-height: 1.35;">{project_name}</h1>
            {owner_html}
            <span class="code-badge" style="font-size: 0.82rem; margin-top: 4px;">الكود المصري لتصميم وتنفيذ المنشآت الخرسانية ECP 203-2018</span>
        </div>
        <div class="header-meta">
            <div><b>تاريخ الحصر:</b> {now_str}</div>
            <div><b>حالة الدور:</b> {top_floor_str}</div>
            <div><b>إجهاد الخرسانة fcu:</b> <span dir="ltr">{fcu:.0f} kg/cm²</span></div>
        </div>
    </div>

    <!-- Section 1 -->
    {section1_html}

    {drawings_html}

    <!-- Section 3: Takeoff Breakdown Table -->
    <div class="section-title">3. جدول حصر وتفريد حديد التسليح والخرسانة (Detailed Takeoff Breakdown)</div>
    {takeoff_table_html}

    {pricing_table_html}

    <!-- Section 5: Concrete Mix Materials -->
    <div class="section-title">5. تقدير كميات مواد الخلطة الخرسانية الإجمالية للمشروع (Concrete Mix Estimation)</div>
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">الأسمنت ({fcu:.0f} kg/m³)</div>
            <div class="card-val"><span dir="ltr">{grand_cement_t:.2f} Ton</span> ({grand_cement_b} شكارة)</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">الرمل النظيف (0.40 m³/m³)</div>
            <div class="card-val"><span dir="ltr">{grand_sand_v:.2f} m³</span></div>
        </div>
        <div class="info-card">
            <div class="card-lbl">السن / الزلط (0.80 m³/m³)</div>
            <div class="card-val"><span dir="ltr">{grand_gravel_v:.2f} m³</span></div>
        </div>
        <div class="info-card">
            <div class="card-lbl">مياه الخلط الصالحة (W/C=0.50)</div>
            <div class="card-val"><span dir="ltr">{grand_water_l:.0f} L</span> (<span dir="ltr">{grand_water_l/1000:.2f} m³</span>)</div>
        </div>
    </div>

    {slabs_cost_m2_note_html}

    <!-- Sign-off Block -->
    <div class="signature-block">
        <div class="sig-box">
            <div class="sig-title">مهندس الحصر والكميات (QS Engineer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">المراجعة والاعتماد (Reviewer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">اعتماد الاستشاري (Consultant):</div>
            <div style="margin-top:20px; color:#94a3b8;">الختم والتاريخ: ______________</div>
        </div>
    </div>

</div>

</body>
</html>

"""
    return html_content



def generate_ground_slab_report_html(
    res: dict,
    project_name: str = "ECP 203 Ground Slab Design (Slab on Grade)",
    img_plan_b64: Optional[str] = None,
    img_detail_b64: Optional[str] = None,
) -> str:
    """
    Generates a print-ready, professional HTML/PDF calculation sheet for Ground Slabs (Slab on Grade)
    according to ECP 203-2018 and ACI 360R.
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>{project_name} - Ground Slab Design</title>
    {_get_base_report_css()}
    <style>
        .sog-table th {{ background-color: #1e3a8a !important; color:#ffffff !important; font-size:0.92rem; font-weight:bold; }}
        .sog-table td {{ font-size:0.90rem; padding: 10px 8px; text-align:center; }}
        .sog-table tr:nth-child(even) {{ background-color: #f8fafc; }}
    </style>
</head>
<body>

<div class="report-container">

    <!-- Top Action Bar -->
    <div class="action-bar no-print">
        <div style="font-weight:700; font-size:1.05rem;">📊 {project_name} — Slab on Grade Calculation Sheet</div>
        <button class="btn-print" onclick="window.print();">🖨️ طباعة التقرير / حفظ كـ PDF (Print / Save as PDF)</button>
    </div>

    <!-- Report Header -->
    <div class="report-header">
        <div class="header-title">
            <h1 style="font-size: 1.45rem; font-weight: 900; color: #0f172a; margin-bottom: 4px; line-height: 1.35;">{project_name}</h1>
            <div style="font-size:1.10rem; font-weight:bold; color:#2563eb; margin:2px 0;">مذكرة الحسابات والتصميم الإنشائي للبلاطات الأرضية (Slab on Grade / Ground Slab)</div>
            <span class="code-badge" style="font-size: 0.82rem; margin-top: 4px;">الكود المصري ECP 203-2018 · كود الأساسات · ACI 360R / PCA</span>
        </div>
        <div class="header-meta">
            <div><b>تاريخ التصميم:</b> {now_str}</div>
            <div><b>أبعاد الصالة:</b> {res['Lx_m']:.1f} × {res['Ly_m']:.1f} m</div>
            <div><b>سمك البلاطة:</b> {res['ts_cm']:.0f} cm</div>
            <div><b>إجهاد الخرسانة fcu:</b> <span dir="ltr">{res['fcu_kg_cm2']:.0f} kg/cm²</span></div>
        </div>
    </div>

    <!-- Section 1: Design Parameters -->
    <div class="section-title">1. مدخلات التصميم والخصائص الهندسية والجيوتقنية (Design Parameters & Loads)</div>
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">أبعاد البلاطة والمساحة (Lx × Ly)</div>
            <div class="card-val"><span dir="ltr">{res['Lx_m']:.1f} × {res['Ly_m']:.1f} m</span> ({res['total_area_m2']:.1f} m²)</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">سمك البلاطة والغطاء (ts & Cover)</div>
            <div class="card-val"><span dir="ltr">ts = {res['ts_cm']:.0f} cm</span> (Cover = {res['cover_cm']:.1f} cm)</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">معامل رد فعل التربة (ks)</div>
            <div class="card-val"><span dir="ltr">{res['ks_kg_cm3']:.1f} kg/cm³</span> (q_all = {res['q_all_kg_cm2']:.1f} kg/cm²)</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">الأحمال المركزة والموزعة</div>
            <div class="card-val"><span dir="ltr">P_wheel={res['p_wheel_ton']:.1f}t | P_post={res['p_post_ton']:.1f}t | LL={res['w_ll_ton_m2']:.1f}t/m²</span></div>
        </div>
    </div>

    <!-- Section 2: Drawings -->
    <div class="section-title">2. المخططات الهندسية وتفاصيل فواصل التحكم والانكماش (CAD Drawings & Joint Details)</div>
    <div style="display:flex; flex-direction:column; gap:16px; margin:16px 0;">
        {f'<div class="drawing-box" style="text-align:center;"><img src="{img_plan_b64}" alt="Ground Slab 2D Plan" style="max-width:100%; border-radius:8px; border:1px solid #cbd5e1;"></div>' if img_plan_b64 else ''}
        {f'<div class="drawing-box" style="text-align:center;"><img src="{img_detail_b64}" alt="Joint Detail" style="max-width:100%; border-radius:8px; border:1px solid #cbd5e1;"></div>' if img_detail_b64 else ''}
    </div>

    <!-- Section 3: Verification Checks -->
    <div class="section-title">3. نتائج الفحوصات الإنشائية والجيوتقنية (Structural & Geotechnical Verification)</div>
    <table class="data-table sog-table" style="width:100%; border-collapse:collapse; margin-top:8px;">
        <thead>
            <tr>
                <th style="text-align:right;">بند التحقق الهندسي (Item)</th>
                <th>القيمة الفعلية (Actual)</th>
                <th>القيمة المسموحة (Allowable)</th>
                <th>نسبة الكفاءة (Ratio)</th>
                <th>الحالة والنتيجة (Status)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="text-align:right; font-weight:bold;">1. إجهادات الانحناء (Westergaard Flexural Stress)</td>
                <td><span dir="ltr">{res['sigma_act_flexure']:.2f} kg/cm²</span></td>
                <td><span dir="ltr">{res['sigma_all_flexure']:.2f} kg/cm²</span></td>
                <td><span dir="ltr">{res['ratio_flexure']*100:.1f}%</span></td>
                <td style="font-weight:bold; color:{'#15803d' if res['is_flexure_safe'] else '#b91c1c'};">{'✅ SAFE' if res['is_flexure_safe'] else '⚠️ UNSAFE'}</td>
            </tr>
            <tr>
                <td style="text-align:right; font-weight:bold;">2. القص الثاقب لأرجل الأرفف (Punching Shear)</td>
                <td><span dir="ltr">{res['qup_post_kg_cm2']:.2f} kg/cm²</span></td>
                <td><span dir="ltr">{res['qcu_punching_kg_cm2']:.2f} kg/cm²</span></td>
                <td><span dir="ltr">{res['ratio_punching']*100:.1f}%</span></td>
                <td style="font-weight:bold; color:{'#15803d' if res['is_punching_safe'] else '#b91c1c'};">{'✅ SAFE' if res['is_punching_safe'] else '⚠️ UNSAFE'}</td>
            </tr>
            <tr>
                <td style="text-align:right; font-weight:bold;">3. ضغط التربة المباشر (Subgrade Contact Pressure)</td>
                <td><span dir="ltr">{res['q_total_act_kg_cm2']:.2f} kg/cm²</span></td>
                <td><span dir="ltr">{res['q_all_kg_cm2']:.2f} kg/cm²</span></td>
                <td><span dir="ltr">{res['ratio_soil']*100:.1f}%</span></td>
                <td style="font-weight:bold; color:{'#15803d' if res['is_soil_safe'] else '#b91c1c'};">{'✅ SAFE' if res['is_soil_safe'] else '⚠️ UNSAFE'}</td>
            </tr>
            <tr>
                <td style="text-align:right; font-weight:bold;">4. تسليح الانكماش والحرارة (Shrinkage Rebar Mesh)</td>
                <td><span dir="ltr">{res['As_provided_cm2_m']:.2f} cm²/m'</span></td>
                <td><span dir="ltr">Min {res['As_required_cm2_m']:.2f} cm²/m'</span></td>
                <td><span dir="ltr">{(res['As_required_cm2_m']/res['As_provided_cm2_m'])*100:.1f}%</span></td>
                <td style="font-weight:bold; color:{'#15803d' if res['is_rebar_safe'] else '#b91c1c'};">{'✅ SAFE' if res['is_rebar_safe'] else '⚠️ UNSAFE'}</td>
            </tr>
            <tr>
                <td style="text-align:right; font-weight:bold;">5. مسافات فواصل الانكماش (Joint Spacing Ratio)</td>
                <td><span dir="ltr">{max(res['actual_bay_lx'], res['actual_bay_ly']):.2f} m</span></td>
                <td><span dir="ltr">Max {res['max_rec_joint_spacing_m']:.2f} m</span></td>
                <td><span dir="ltr">{(max(res['actual_bay_lx'], res['actual_bay_ly'])/res['max_rec_joint_spacing_m'])*100:.1f}%</span></td>
                <td style="font-weight:bold; color:{'#15803d' if (max(res['actual_bay_lx'], res['actual_bay_ly']) <= res['max_rec_joint_spacing_m']) else '#b91c1c'};">{'✅ SAFE' if (max(res['actual_bay_lx'], res['actual_bay_ly']) <= res['max_rec_joint_spacing_m']) else '⚠️ UNSAFE'}</td>
            </tr>
        </tbody>
    </table>

    <!-- Section 4: BOQ Breakdown Table -->
    <div class="section-title">4. جدول حصر الكميات والمقايسة المادية (Takeoff & BOQ Breakdown)</div>
    <table class="data-table sog-table" style="width:100%; border-collapse:collapse; margin-top:8px;">
        <thead>
            <tr>
                <th style="width:40px;">م</th>
                <th style="text-align:right;">بند الأعمال (Item)</th>
                <th>المواصفة الفنية (Specifications)</th>
                <th>الكمية (Qty)</th>
                <th>الوحدة (Unit)</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>1</td><td style="text-align:right; font-weight:bold;">خرسانة مسلحة للبلاطة الأرضية</td><td>fcu={res['fcu_kg_cm2']:.0f} kg/cm² (ts={res['ts_cm']:.0f} cm)</td><td><span dir="ltr">{res['concrete_vol_m3']:.2f}</span></td><td>m³</td></tr>
            <tr><td>2</td><td style="text-align:right; font-weight:bold;">حديد تسليح شبكات الانكماش</td><td>{res['mesh_type']} (Φ{res['phi_mesh_mm']} @ {res['spacing_mesh_cm']:.0f} cm)</td><td><span dir="ltr">{res['total_mesh_weight_ton']:.3f}</span></td><td>Ton</td></tr>
            <tr><td>3</td><td style="text-align:right; font-weight:bold;">أسياخ دواول نقل القص الملساء</td><td>Φ{res['dowel_phi_mm']} mm (L={res['dowel_len_cm']:.0f} cm @ {res['dowel_spacing_cm']:.0f} cm)</td><td><span dir="ltr">{res['total_dowel_weight_ton']:.3f} ({res['total_dowels_count']} سيخ)</span></td><td>Ton</td></tr>
            <tr><td>4</td><td style="text-align:right; font-weight:bold;">إجمالي حديد التسليح والدواول</td><td>معدل التسليح = {res['steel_rate_kg_m3']:.1f} kg/m³</td><td><span dir="ltr">{res['total_steel_weight_ton']:.3f}</span></td><td>Ton</td></tr>
            <tr><td>5</td><td style="text-align:right; font-weight:bold;">قطع فواصل الانكماش بالمنشار</td><td>عمق القطع = {res['saw_cut_depth_cm']:.1f} cm</td><td><span dir="ltr">{res['total_joint_length_m']:.1f}</span></td><td>m'</td></tr>
            <tr><td>6</td><td style="text-align:right; font-weight:bold;">مادة ملء وحقن الفواصل المرنة</td><td>Polyurethane Elastomeric Sealant</td><td><span dir="ltr">{res['total_joint_length_m']:.1f}</span></td><td>m'</td></tr>
            <tr><td>7</td><td style="text-align:right; font-weight:bold;">عازل رطوبة بولي إيثيلين (PE)</td><td>Heavy-duty 500 Micron Polyethylene Sheet</td><td><span dir="ltr">{res['vapor_barrier_m2']:.1f}</span></td><td>m²</td></tr>
            <tr><td>8</td><td style="text-align:right; font-weight:bold;">طبقة إحلال من الحصى المتدرج المدموك</td><td>سمك الطبقة = {res['subbase_vol_m3'] / res['total_area_m2'] * 100:.0f} cm (Compaction >= 98%)</td><td><span dir="ltr">{res['subbase_vol_m3']:.2f}</span></td><td>m³</td></tr>
        </tbody>
    </table>

    <!-- Sign-off Block -->
    <div class="signature-block">
        <div class="sig-box">
            <div class="sig-title">مهندس التصميم الإنشائي (Structural Engineer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">المراجعة والاعتماد (Reviewer):</div>
            <div style="margin-top:20px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box">
            <div class="sig-title">اعتماد الاستشاري (Consultant):</div>
            <div style="margin-top:20px; color:#94a3b8;">الختم والتاريخ: ______________</div>
        </div>
    </div>

</div>

</body>
</html>
"""
    return html_content


def generate_masonry_plaster_report_html(
    project_name: str = "ECP Masonry & Plaster Design",
    owner_name: Optional[str] = None,
    img_plan_b64: Optional[str] = None,
    masonry_summary: Optional[Dict[str, Any]] = None,
    plaster_summary: Optional[Dict[str, Any]] = None,
    total_materials: Optional[Dict[str, Any]] = None,
    pricing_summary: Optional[Dict[str, Any]] = None,
    walls_12_rows: Optional[List[Dict[str, Any]]] = None,
    walls_25_rows: Optional[List[Dict[str, Any]]] = None,
    openings_details: Optional[List[Dict[str, Any]]] = None,
    plaster_rows: Optional[List[Dict[str, Any]]] = None,
    materials_rows: Optional[List[Dict[str, Any]]] = None,
    pricing_rows: Optional[List[Dict[str, Any]]] = None,
    brick_type_display: str = "الطوب الأحمر الطفلي",
    brick_size_display: str = "25×12×6 سم",
    mortar_cm: float = 1.0,
    deduction_rule_str: str = "الكود المصري ECP",
    include_inputs: bool = False,
    inputs_data: Optional[Dict[str, Any]] = None,
    only_summary_and_plan: bool = False,
) -> str:
    """
    Generates a print-ready, professional HTML/PDF calculation sheet for
    Module 15 (Masonry & Plaster Works - أعمال المباني والمحارة وحصر الكميات والمقايسة)
    according to Egyptian Code of Practice ECP 203 & ECP Plaster/Masonry Specs.
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ms = masonry_summary or {}
    ps = plaster_summary or {}
    tm = total_materials or {}
    pr = pricing_summary or {}

    n12 = ms.get("n12", 0.0)
    g12 = ms.get("g12", 0.0)
    op12 = ms.get("op12", 0.0)
    n25 = ms.get("n25", 0.0)
    g25 = ms.get("g25", 0.0)
    op25 = ms.get("op25", 0.0)
    v25 = ms.get("v25", 0.0)
    bricks_12 = ms.get("bricks_12", 0)
    bricks_25 = ms.get("bricks_25", 0)
    bricks_total = ms.get("bricks_total", 0)
    sand_total_masonry = ms.get("sand_total_masonry", 0.0)
    cement_masonry_tons = ms.get("cement_masonry_tons", 0.0)
    cement_masonry_bags = ms.get("cement_masonry_bags", 0)

    p_net_m2 = ps.get("tot_net", 0.0)
    p_gross_m2 = ps.get("tot_gross", 0.0)
    p_ded_m2 = ps.get("tot_ded", 0.0)
    p_sand_m3 = ps.get("tot_sand", 0.0)
    p_cement_tons = ps.get("tot_cement_tons", 0.0)
    p_cement_bags = ps.get("tot_cement_bags", 0)
    p_active_walls = ps.get("active_walls_count", 0)

    total_sand_all = tm.get("total_sand_all", 0.0)
    total_cement_tons_all = tm.get("total_cement_tons_all", 0.0)
    total_cement_bags_all = tm.get("total_cement_bags_all", 0)

    cost_masonry_total = pr.get("cost_masonry_total", 0.0)
    cost_plaster_total = pr.get("cost_plaster_total", 0.0)
    grand_total_cost = pr.get("grand_total_cost", 0.0)

    owner_html = ""
    if owner_name and str(owner_name).strip():
        owner_html = f"""<div style="font-size: 1.0rem; font-weight: 700; color: #1e3a8a; margin: 4px 0 6px 0;"><b>اسم المالك:</b> <span style="color:#0f172a; font-weight: 800;">{str(owner_name).strip()}</span></div>"""

    # Section Inputs (when include_inputs is True)
    inputs_section_html = ""
    if include_inputs and inputs_data:
        x_axes_info = inputs_data.get("x_axes_info", [])
        y_axes_info = inputs_data.get("y_axes_info", [])
        cols_list = inputs_data.get("columns_list", [])
        wins_models = inputs_data.get("windows_models", [])
        doors_models = inputs_data.get("doors_models", [])

        axes_table = ""
        if x_axes_info or y_axes_info:
            axes_table = f"""
            <table class="data-table" style="width:100%; border-collapse:collapse; margin-top:6px; font-size:0.85rem;">
                <thead>
                    <tr>
                        <th style="text-align:right;">الاتجاه</th>
                        <th>عدد المحاور</th>
                        <th>تسميات المحاور</th>
                        <th style="text-align:right;">الإحداثيات والمسافات البينية (م)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="font-weight:700; text-align:right; color:#c2410c;">المحاور الرأسية (X-Axes)</td>
                        <td class="val-cell">{len(x_axes_info)}</td>
                        <td class="val-cell">{inputs_data.get('x_axes_labels', '—')}</td>
                        <td style="text-align:right;"><span dir="ltr">{inputs_data.get('x_axes_spans', '—')}</span></td>
                    </tr>
                    <tr>
                        <td style="font-weight:700; text-align:right; color:#0284c7;">المحاور الأفقية (Y-Axes)</td>
                        <td class="val-cell">{len(y_axes_info)}</td>
                        <td class="val-cell">{inputs_data.get('y_axes_labels', '—')}</td>
                        <td style="text-align:right;"><span dir="ltr">{inputs_data.get('y_axes_spans', '—')}</span></td>
                    </tr>
                </tbody>
            </table>
            """

        cols_table = ""
        if cols_list:
            c_trs = ""
            for c in cols_list:
                c_trs += f"""
                <tr>
                    <td style="font-weight:700; text-align:right; color:#1e40af;">{c.get('name', '—')}</td>
                    <td class="val-cell">{c.get('axis_coord', '—')}</td>
                    <td class="val-cell"><span dir="ltr">{c.get('b', 30):.0f} × {c.get('t', 60):.0f} cm</span></td>
                    <td class="val-cell">{c.get('orient', 'رأسي')}</td>
                    <td class="val-cell">{c.get('shift', 'متمركز')}</td>
                </tr>
                """
            cols_table = f"""
            <table class="data-table" style="width:100%; border-collapse:collapse; margin-top:6px; font-size:0.85rem;">
                <thead>
                    <tr>
                        <th style="text-align:right;">العمود</th>
                        <th>الموقع على المحاور</th>
                        <th>القطاع (عرض × عمق)</th>
                        <th>اتجاه ضرب العمود</th>
                        <th>الترحيل عن المحور</th>
                    </tr>
                </thead>
                <tbody>{c_trs}</tbody>
            </table>
            """

        openings_table = ""
        if wins_models or doors_models:
            op_m_trs = ""
            for wm in wins_models:
                op_m_trs += f"""
                <tr>
                    <td style="font-weight:700; text-align:right; color:#0284c7;">شباك ({wm.get('name', '—')})</td>
                    <td class="val-cell"><span dir="ltr">{wm.get('w_m', 1.0):.2f} م</span></td>
                    <td class="val-cell"><span dir="ltr">{wm.get('h_m', 1.2):.2f} م</span></td>
                    <td class="val-cell"><span dir="ltr">{wm.get('area_m2', 1.2):.2f} م²</span></td>
                    <td class="val-cell"><span dir="ltr">{wm.get('sill_m', 1.0):.2f} م</span></td>
                    <td class="val-cell">{wm.get('count', 0)}</td>
                </tr>
                """
            for dm in doors_models:
                op_m_trs += f"""
                <tr>
                    <td style="font-weight:700; text-align:right; color:#15803d;">باب ({dm.get('name', '—')})</td>
                    <td class="val-cell"><span dir="ltr">{dm.get('w_m', 0.9):.2f} م</span></td>
                    <td class="val-cell"><span dir="ltr">{dm.get('h_m', 2.1):.2f} م</span></td>
                    <td class="val-cell"><span dir="ltr">{dm.get('area_m2', 1.89):.2f} م²</span></td>
                    <td class="val-cell">0.00 م</td>
                    <td class="val-cell">{dm.get('count', 0)}</td>
                </tr>
                """
            openings_table = f"""
            <table class="data-table" style="width:100%; border-collapse:collapse; margin-top:6px; font-size:0.85rem;">
                <thead>
                    <tr>
                        <th style="text-align:right;">نموذج الفتحة</th>
                        <th>العرض</th>
                        <th>الارتفاع</th>
                        <th>المساحة</th>
                        <th>ارتفاع الجلسة</th>
                        <th>العدد المنفذ</th>
                    </tr>
                </thead>
                <tbody>{op_m_trs}</tbody>
            </table>
            """

        inputs_section_html = f"""
        <div class="section-title">3. جدول بيانات ومدخلات التصميم والمشروع (Design Inputs & Specifications)</div>
        <div style="margin-bottom: 16px; page-break-inside: avoid;">
            <div class="subsection-title">3.1 شبكة المحاور الإنشائية والمسافات البينية:</div>
            {axes_table}
            <div class="subsection-title" style="margin-top:12px;">3.2 جدول نماذج وتوصيف الأعمدة الخرسانية ({len(cols_list)} عمود):</div>
            {cols_table}
            <div class="subsection-title" style="margin-top:12px;">3.3 جدول نماذج ومقاسات فتحات الشبابيك والأبواب:</div>
            {openings_table}
        </div>
        """

    # 1. 2D Plan Drawing Box
    plan_drawing_html = ""
    if img_plan_b64:
        plan_drawing_html = f"""
        <div class="section-title">2. المخطط الهندسي للمسقط الأفقي المصمم (Designed Plan & Structural Layout)</div>
        <div style="margin: 14px 0 20px 0; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 12px; background: #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.05); text-align: center; page-break-inside: avoid;">
            <div style="font-size: 0.95rem; font-weight: 700; color: #1e3a8a; margin-bottom: 8px; text-align: right; border-bottom: 2px solid #3b82f6; padding-bottom: 4px; display:flex; justify-content:space-between; align-items:center;">
                <span>📐 المسقط الأفقي التنفيذي متضمناً المحاور، الحوائط، الأعمدة، الشبابيك والأبواب، وأوجه المحارة</span>
                <span style="font-size:0.85rem; color:#64748b;" dir="ltr">ECP Architectural & Structural Layout</span>
            </div>
            <img src="data:image/png;base64,{img_plan_b64}" alt="ECP Designed Plan" style="max-width: 100%; height: auto; border-radius: 6px;" />
            <div style="font-size:0.80rem; margin-top:8px; display:flex; gap:14px; justify-content:center; flex-wrap:wrap; color:#334155; font-weight:bold;">
                <span style="color:#EFA368;">■ حائط 12سم</span>
                <span style="color:#8B1A1A;">■ حائط 25سم</span>
                <span style="color:#0284C7;">■ حائط دروة</span>
                <span style="color:#87CEEB;">■ شباك (W#)</span>
                <span style="color:#2E7D32;">■ باب (D#)</span>
                <span style="color:#2F4F8F;">■ عمود (C#)</span>
                <span style="color:#EC4899;">▨ وجه محارة (وردي)</span>
            </div>
        </div>
        """

    # 2. Table: Walls 12 cm
    rows_12_html = ""
    if walls_12_rows:
        for r in walls_12_rows:
            rows_12_html += f"""
            <tr>
                <td style="font-weight:700; text-align:right;">{r.get('الحائط', '—')}</td>
                <td class="val-cell"><span dir="ltr">{r.get('طول المحور (م)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('خصم الأعمدة (م)', 0.0):.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#c2410c;"><span dir="ltr">{r.get('طول المباني الصافي (م)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('الارتفاع (م)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('المساحة الإجمالية (م2)', 0.0):.2f}</span></td>
                <td class="val-cell" style="color:#dc2626;"><span dir="ltr">{r.get('مساحة الفتحات (م2)', 0.0):.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#15803d;"><span dir="ltr">{r.get('المساحة الصافية (م2)', 0.0):.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#1e40af;"><span dir="ltr">{r.get('عدد الطوب (وحدة)', 0):,}</span></td>
            </tr>
            """
        # Total row
        rows_12_html += f"""
        <tr style="background:#e0f2fe; font-weight:800; border-top:2px solid #0284c7;">
            <td style="text-align:right; color:#0369a1;">✅ إجمالي مباني 12 سم</td>
            <td class="val-cell">—</td>
            <td class="val-cell">—</td>
            <td class="val-cell">—</td>
            <td class="val-cell">—</td>
            <td class="val-cell"><span dir="ltr">{g12:.2f}</span></td>
            <td class="val-cell" style="color:#b91c1c;"><span dir="ltr">{op12:.2f}</span></td>
            <td class="val-cell" style="color:#15803d; font-size:1.0rem;"><span dir="ltr">{n12:.2f} م²</span></td>
            <td class="val-cell" style="color:#1e40af; font-size:1.0rem;"><span dir="ltr">{bricks_12:,} طوبة</span></td>
        </tr>
        """
    else:
        rows_12_html = "<tr><td colspan='9' style='text-align:center; padding:12px; color:#64748b;'>لا توجد حوائط سمك 12 سم نشطة</td></tr>"

    # 3. Table: Walls 25 cm
    rows_25_html = ""
    if walls_25_rows:
        for r in walls_25_rows:
            rows_25_html += f"""
            <tr>
                <td style="font-weight:700; text-align:right;">{r.get('الحائط', '—')}</td>
                <td class="val-cell"><span dir="ltr">{r.get('طول المحور (م)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('خصم الأعمدة (م)', 0.0):.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#701a75;"><span dir="ltr">{r.get('طول المباني الصافي (م)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('الارتفاع (م)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('المساحة الإجمالية (م2)', 0.0):.2f}</span></td>
                <td class="val-cell" style="color:#dc2626;"><span dir="ltr">{r.get('مساحة الفتحات (م2)', 0.0):.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#15803d;"><span dir="ltr">{r.get('المساحة الصافية (م2)', 0.0):.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#b45309;"><span dir="ltr">{r.get('حجم الطوب (م3)', 0.0):.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#1e40af;"><span dir="ltr">{r.get('عدد الطوب (وحدة)', 0):,}</span></td>
            </tr>
            """
        # Total row
        rows_25_html += f"""
        <tr style="background:#fce7f3; font-weight:800; border-top:2px solid #db2777;">
            <td style="text-align:right; color:#9d174d;">✅ إجمالي مباني 25 سم</td>
            <td class="val-cell">—</td>
            <td class="val-cell">—</td>
            <td class="val-cell">—</td>
            <td class="val-cell">—</td>
            <td class="val-cell"><span dir="ltr">{g25:.2f}</span></td>
            <td class="val-cell" style="color:#b91c1c;"><span dir="ltr">{op25:.2f}</span></td>
            <td class="val-cell" style="color:#15803d;"><span dir="ltr">{n25:.2f} م²</span></td>
            <td class="val-cell" style="color:#b45309; font-size:1.0rem;"><span dir="ltr">{v25:.2f} م³</span></td>
            <td class="val-cell" style="color:#1e40af; font-size:1.0rem;"><span dir="ltr">{bricks_25:,} طوبة</span></td>
        </tr>
        """
    else:
        rows_25_html = "<tr><td colspan='10' style='text-align:center; padding:12px; color:#64748b;'>لا توجد حوائط سمك 25 سم نشطة</td></tr>"

    # 4. Openings breakdown table
    openings_html = ""
    if openings_details and len(openings_details) > 0:
        op_tr = ""
        tot_op_all = sum(o.get("إجمالي الفتحات (م²)", 0.0) for o in openings_details)
        tot_wins_all = sum(o.get("عدد شبابيك", 0) for o in openings_details)
        tot_doors_all = sum(o.get("عدد أبواب", 0) for o in openings_details)
        for o in openings_details:
            if o.get("إجمالي الفتحات (م²)", 0.0) > 0:
                op_tr += f"""
                <tr>
                    <td style="font-weight:700; text-align:right;">{o.get('حائط', '—')}</td>
                    <td class="val-cell"><span dir="ltr">{o.get('سُمك', '—')}</span></td>
                    <td class="val-cell"><span dir="ltr">{o.get('عدد شبابيك', 0)} ({o.get('شبابيك (م²)', 0.0):.2f} م²)</span></td>
                    <td class="val-cell"><span dir="ltr">{o.get('عدد أبواب', 0)} ({o.get('أبواب (م²)', 0.0):.2f} م²)</span></td>
                    <td class="val-cell" style="font-weight:700; color:#b45309;"><span dir="ltr">{o.get('إجمالي الفتحات (م²)', 0.0):.2f} م²</span></td>
                </tr>
                """
        op_tr += f"""
        <tr style="background:#f1f5f9; font-weight:800; border-top:2px solid #475569;">
            <td style="text-align:right;">✅ إجمالي الفتحات المخصومة</td>
            <td class="val-cell">—</td>
            <td class="val-cell"><span dir="ltr">{tot_wins_all} شباك</span></td>
            <td class="val-cell"><span dir="ltr">{tot_doors_all} باب</span></td>
            <td class="val-cell" style="color:#b45309; font-size:1.0rem;"><span dir="ltr">{tot_op_all:.2f} م²</span></td>
        </tr>
        """
        openings_html = f"""
        <div class="section-title">5. تفصيل مساحات الفتحات (الأبواب والشبابيك) المخصومة من أعمال المباني</div>
        <table class="data-table" style="width:100%; border-collapse:collapse; margin-top:8px;">
            <thead>
                <tr>
                    <th style="text-align:right;">الحائط</th>
                    <th>سُمك الطوب</th>
                    <th>الشبابيك ومساحتها</th>
                    <th>الأبواب ومساحتها</th>
                    <th>إجمالي المساحة المخصومة</th>
                </tr>
            </thead>
            <tbody>
                {op_tr}
            </tbody>
        </table>
        """

    # 5. Plaster Survey Table
    plaster_table_html = ""
    if plaster_rows and len(plaster_rows) > 0:
        p_tr = ""
        for r in plaster_rows:
            p_tr += f"""
            <tr>
                <td style="font-weight:700; text-align:right;">{r.get('الحائط', '—')}</td>
                <td class="val-cell">{r.get('الوجه المحدد', '—')}</td>
                <td class="val-cell"><span dir="ltr">{r.get('عدد الأوجه', 1)}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('الطول (م)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('الارتفاع (م)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('إجمالي مسطح المحارة (m^2)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('إجمالي مساحة الفتحات (m^2)', 0.0):.2f}</span></td>
                <td class="val-cell" style="color:#dc2626;"><span dir="ltr">{r.get('الفتحات المخصومة المعتمدة (m^2)', 0.0):.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#15803d;"><span dir="ltr">{r.get('صافي مسطح المحارة النهائي (m^2)', 0.0):.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('كمية الرمل المطلوبة (m^3)', 0.0):.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#1e40af;">{r.get('كمية الأسمنت المطلوبة', '—')}</td>
            </tr>
            """
        p_tr += f"""
        <tr style="background:#e0f2fe; font-weight:800; border-top:2px solid #0284c7;">
            <td style="text-align:right; color:#0369a1;">✅ إجمالي أعمال المحارة</td>
            <td class="val-cell">—</td>
            <td class="val-cell"><span dir="ltr">{sum(r.get('عدد الأوجه', 0) for r in plaster_rows)}</span></td>
            <td class="val-cell"><span dir="ltr">{sum(r.get('الطول (م)', 0.0) for r in plaster_rows):.2f}</span></td>
            <td class="val-cell">—</td>
            <td class="val-cell"><span dir="ltr">{p_gross_m2:.2f}</span></td>
            <td class="val-cell"><span dir="ltr">{ps.get('tot_op_gross', 0.0):.2f}</span></td>
            <td class="val-cell" style="color:#b91c1c;"><span dir="ltr">{p_ded_m2:.2f}</span></td>
            <td class="val-cell" style="color:#15803d; font-size:1.0rem;"><span dir="ltr">{p_net_m2:.2f} م²</span></td>
            <td class="val-cell" style="color:#b45309;"><span dir="ltr">{p_sand_m3:.2f} م³</span></td>
            <td class="val-cell" style="color:#1e40af;"><span dir="ltr">{p_cement_tons:.2f} طن ({p_cement_bags} شكارة)</span></td>
        </tr>
        """
        plaster_table_html = f"""
        <div class="section-title">6. جدول حصر كميات ومواد أعمال البياض (المحارة) طبقاً للكود المصري ECP</div>
        <table class="data-table" style="width:100%; border-collapse:collapse; margin-top:8px;">
            <thead>
                <tr>
                    <th style="text-align:right;">الحائط</th>
                    <th>الوجه المحدد</th>
                    <th>عدد الأوجه</th>
                    <th>الطول (م)</th>
                    <th>الارتفاع (م)</th>
                    <th>إجمالي المسطح (م²)</th>
                    <th>مسطح الفتحات (م²)</th>
                    <th>الخصم المعتمد (م²)</th>
                    <th>صافي المسطح (م²)</th>
                    <th>الرمل المطلوب (م³)</th>
                    <th>الأسمنت المطلوب</th>
                </tr>
            </thead>
            <tbody>
                {p_tr}
            </tbody>
        </table>
        """
    else:
        plaster_table_html = f"""
        <div class="section-title">6. جدول حصر أعمال البياض (المحارة)</div>
        <div style="padding:14px; background:#f8fafc; border:1px dashed #cbd5e1; border-radius:8px; text-align:center; color:#64748b;">
            لم يتم تفعيل أوجه المحارة لأي حائط في هذا المسقط.
        </div>
        """

    # 6. Materials BOQ Table
    mat_rows_html = ""
    if materials_rows and len(materials_rows) > 0:
        for r in materials_rows:
            is_tot = "الإجمالي" in str(r.get("بند الأعمال", "")) or "إجمالي" in str(r.get("بند الأعمال", ""))
            style = "background:#e2e8f0; font-weight:800;" if is_tot else ""
            b_cnt = r.get(f"عدد الطوب ({brick_type_display} | {brick_size_display})", r.get("عدد الطوب", "—"))
            mat_rows_html += f"""
            <tr style="{style}">
                <td style="font-weight:700; text-align:right;">{r.get('بند الأعمال', '—')}</td>
                <td class="val-cell">{r.get('الوحدة', '—')}</td>
                <td class="val-cell"><span dir="ltr">{r.get('الكمية الصافية', '—')}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('رمل صافي (م³)', '—')}</span></td>
                <td class="val-cell" style="font-weight:700; color:#b45309;"><span dir="ltr">{r.get('رمل مع الهالك 5% (م³)', '—')}</span></td>
                <td class="val-cell" style="font-weight:700; color:#0284c7;"><span dir="ltr">{r.get('أسمنت (طن)', '—')}</span></td>
                <td class="val-cell"><span dir="ltr">{r.get('شكاير أسمنت (50كجم)', '—')}</span></td>
                <td class="val-cell" style="font-weight:700; color:#1e40af;"><span dir="ltr">{b_cnt}</span></td>
            </tr>
            """
    else:
        # Default fallback rows
        mat_rows_html = f"""
        <tr>
            <td style="font-weight:700; text-align:right;">مباني طوب سمك 12 سم (نصف طوبة)</td>
            <td class="val-cell">م² مسطح</td>
            <td class="val-cell"><span dir="ltr">{n12:.2f}</span></td>
            <td class="val-cell"><span dir="ltr">{n12 * 0.025:.2f}</span></td>
            <td class="val-cell" style="font-weight:700; color:#b45309;"><span dir="ltr">{n12 * 0.025 * 1.05:.2f}</span></td>
            <td class="val-cell" style="font-weight:700; color:#0284c7;"><span dir="ltr">{(n12 * 0.025 * 1.05 * 350)/1000.0:.2f}</span></td>
            <td class="val-cell"><span dir="ltr">{math.ceil((n12 * 0.025 * 1.05 * 350)/50.0) if n12>0 else 0}</span></td>
            <td class="val-cell" style="font-weight:700; color:#1e40af;"><span dir="ltr">{bricks_12:,}</span></td>
        </tr>
        <tr>
            <td style="font-weight:700; text-align:right;">مباني طوب سمك 25 سم (طوبة كاملة)</td>
            <td class="val-cell">م³ مكعب</td>
            <td class="val-cell"><span dir="ltr">{v25:.2f}</span></td>
            <td class="val-cell"><span dir="ltr">{v25 * 0.200:.2f}</span></td>
            <td class="val-cell" style="font-weight:700; color:#b45309;"><span dir="ltr">{v25 * 0.200 * 1.05:.2f}</span></td>
            <td class="val-cell" style="font-weight:700; color:#0284c7;"><span dir="ltr">{(v25 * 0.200 * 1.05 * 350)/1000.0:.2f}</span></td>
            <td class="val-cell"><span dir="ltr">{math.ceil((v25 * 0.200 * 1.05 * 350)/50.0) if v25>0 else 0}</span></td>
            <td class="val-cell" style="font-weight:700; color:#1e40af;"><span dir="ltr">{bricks_25:,}</span></td>
        </tr>
        <tr style="background:#e0f2fe; font-weight:800;">
            <td style="text-align:right; color:#0369a1;">⬅️ إجمالي مواد أعمال المباني</td>
            <td class="val-cell">—</td>
            <td class="val-cell">—</td>
            <td class="val-cell"><span dir="ltr">{sand_total_masonry/1.05:.2f}</span></td>
            <td class="val-cell" style="color:#b45309;"><span dir="ltr">{sand_total_masonry:.2f}</span></td>
            <td class="val-cell" style="color:#0284c7;"><span dir="ltr">{cement_masonry_tons:.2f}</span></td>
            <td class="val-cell"><span dir="ltr">{cement_masonry_bags}</span></td>
            <td class="val-cell" style="color:#1e40af;"><span dir="ltr">{bricks_total:,}</span></td>
        </tr>
        """
        if p_active_walls > 0:
            mat_rows_html += f"""
            <tr>
                <td style="font-weight:700; text-align:right;">بياض محارة (سمك 2 سم شامل الطرطشة)</td>
                <td class="val-cell">م² مسطح</td>
                <td class="val-cell"><span dir="ltr">{p_net_m2:.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{p_sand_m3/1.05:.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#b45309;"><span dir="ltr">{p_sand_m3:.2f}</span></td>
                <td class="val-cell" style="font-weight:700; color:#0284c7;"><span dir="ltr">{p_cement_tons:.2f}</span></td>
                <td class="val-cell"><span dir="ltr">{p_cement_bags}</span></td>
                <td class="val-cell">—</td>
            </tr>
            <tr style="background:#ecfdf5; font-weight:900; border-top:2px solid #059669;">
                <td style="text-align:right; color:#047857; font-size:1.0rem;">✅ الإجمالي العام لكامل المشروع (مباني + محارة)</td>
                <td class="val-cell">—</td>
                <td class="val-cell">—</td>
                <td class="val-cell"><span dir="ltr">{(sand_total_masonry/1.05) + (p_sand_m3/1.05):.2f}</span></td>
                <td class="val-cell" style="color:#b45309; font-size:1.0rem;"><span dir="ltr">{total_sand_all:.2f} م³</span></td>
                <td class="val-cell" style="color:#0284c7; font-size:1.0rem;"><span dir="ltr">{total_cement_tons_all:.2f} طن</span></td>
                <td class="val-cell" style="font-size:1.0rem;"><span dir="ltr">{total_cement_bags_all} شكارة</span></td>
                <td class="val-cell" style="color:#1e40af; font-size:1.0rem;"><span dir="ltr">{bricks_total:,} طوبة</span></td>
            </tr>
            """

    # 7. Pricing Table
    p_brick_in = pr.get("p_brick_in", 2500.0)
    p_sand_in = pr.get("p_sand_in", 200.0)
    p_cement_in = pr.get("p_cement_in", 4000.0)
    p_plaster_labor_in = pr.get("p_plaster_labor_in", 70.0)
    brick_thousands = round(bricks_total / 1000.0, 3)
    cost_brick = pr.get("cost_brick", round(brick_thousands * p_brick_in, 2))
    cost_sand_masonry = pr.get("cost_sand_masonry", round(sand_total_masonry * p_sand_in, 2))
    cost_cement_masonry = pr.get("cost_cement_masonry", round(cement_masonry_tons * p_cement_in, 2))
    cost_plaster_labor = pr.get("cost_plaster_labor", round(p_net_m2 * p_plaster_labor_in, 2))
    cost_sand_plaster = pr.get("cost_sand_plaster", round(p_sand_m3 * p_sand_in, 2))
    cost_cement_plaster = pr.get("cost_cement_plaster", round(p_cement_tons * p_cement_in, 2))
    cost_sand_all = pr.get("cost_sand_all", round(total_sand_all * p_sand_in, 2))
    cost_cement_all = pr.get("cost_cement_all", round(total_cement_tons_all * p_cement_in, 2))

    pricing_table_html = f"""
    <div class="section-title">8. جدول تسعير المقايسة والتكلفة التقديرية الشاملة (Cost Estimation & BOQ)</div>
    <table class="data-table" style="width:100%; border-collapse:collapse; margin-top:8px;">
        <thead>
            <tr>
                <th style="text-align:right;">بند التكلفة والمقايسة</th>
                <th>الكمية المحصورة</th>
                <th>الوحدة</th>
                <th>سعر الوحدة (ج.م)</th>
                <th style="text-align:right;">معادلة الحساب التفصيلية</th>
                <th>إجمالي التكلفة (ج.م)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="text-align:right; font-weight:bold; color:#c2410c;">🧱 1. توريد وتشوين الطوب</td>
                <td class="val-cell"><span dir="ltr">{brick_thousands:.3f}</span></td>
                <td>ألف طوبة ({bricks_total:,})</td>
                <td class="val-cell"><span dir="ltr">{p_brick_in:,.2f}</span></td>
                <td style="text-align:right;"><span dir="ltr">{brick_thousands:.3f}</span> ألف × <span dir="ltr">{p_brick_in:,.2f}</span> ج.م</td>
                <td class="val-cell" style="font-weight:bold; color:#c2410c;"><span dir="ltr">{cost_brick:,.2f}</span></td>
            </tr>
            <tr>
                <td style="text-align:right; font-weight:bold; color:#b45309;">🏜️ 2. رمل مونة المباني (شامل 5% هالك)</td>
                <td class="val-cell"><span dir="ltr">{sand_total_masonry:.2f}</span></td>
                <td>متر مكعب (م³)</td>
                <td class="val-cell"><span dir="ltr">{p_sand_in:,.2f}</span></td>
                <td style="text-align:right;"><span dir="ltr">{sand_total_masonry:.2f}</span> م³ × <span dir="ltr">{p_sand_in:,.2f}</span> ج.م</td>
                <td class="val-cell" style="font-weight:bold; color:#b45309;"><span dir="ltr">{cost_sand_masonry:,.2f}</span></td>
            </tr>
            <tr>
                <td style="text-align:right; font-weight:bold; color:#0284c7;">🏗️ 3. أسمنت مونة المباني (350 كجم/م³)</td>
                <td class="val-cell"><span dir="ltr">{cement_masonry_tons:.3f}</span></td>
                <td>طن ({cement_masonry_bags} شكارة)</td>
                <td class="val-cell"><span dir="ltr">{p_cement_in:,.2f}</span></td>
                <td style="text-align:right;"><span dir="ltr">{cement_masonry_tons:.3f}</span> طن × <span dir="ltr">{p_cement_in:,.2f}</span> ج.م</td>
                <td class="val-cell" style="font-weight:bold; color:#0284c7;"><span dir="ltr">{cost_cement_masonry:,.2f}</span></td>
            </tr>
            <tr style="background:#ffedd5; font-weight:800; border-top:1.5px solid #ea580c;">
                <td style="text-align:right; color:#c2410c;">⬅️ إجمالي بند أعمال المباني</td>
                <td class="val-cell">—</td>
                <td>—</td>
                <td class="val-cell">—</td>
                <td style="text-align:right;">مجموع (الطوب + رمل المباني + أسمنت المباني)</td>
                <td class="val-cell" style="font-weight:900; color:#c2410c; font-size:1.0rem;"><span dir="ltr">{cost_masonry_total:,.2f} ج.م</span></td>
            </tr>
            <tr>
                <td style="text-align:right; font-weight:bold; color:#0284c7;">🎨 4. مصنعية بياض المحارة (أجرة المبيض)</td>
                <td class="val-cell"><span dir="ltr">{p_net_m2:.2f}</span></td>
                <td>متر مسطح (م²)</td>
                <td class="val-cell"><span dir="ltr">{p_plaster_labor_in:,.2f}</span></td>
                <td style="text-align:right;"><span dir="ltr">{p_net_m2:.2f}</span> م² × <span dir="ltr">{p_plaster_labor_in:,.2f}</span> ج.م</td>
                <td class="val-cell" style="font-weight:bold; color:#0284c7;"><span dir="ltr">{cost_plaster_labor:,.2f}</span></td>
            </tr>
            <tr>
                <td style="text-align:right; font-weight:bold; color:#b45309;">🏜️ 5. رمل بياض المحارة (شامل 5% هالك)</td>
                <td class="val-cell"><span dir="ltr">{p_sand_m3:.2f}</span></td>
                <td>متر مكعب (م³)</td>
                <td class="val-cell"><span dir="ltr">{p_sand_in:,.2f}</span></td>
                <td style="text-align:right;"><span dir="ltr">{p_sand_m3:.2f}</span> م³ × <span dir="ltr">{p_sand_in:,.2f}</span> ج.م</td>
                <td class="val-cell" style="font-weight:bold; color:#b45309;"><span dir="ltr">{cost_sand_plaster:,.2f}</span></td>
            </tr>
            <tr>
                <td style="text-align:right; font-weight:bold; color:#0284c7;">🏗️ 6. أسمنت بياض المحارة (350 كجم/م³)</td>
                <td class="val-cell"><span dir="ltr">{p_cement_tons:.3f}</span></td>
                <td>طن ({p_cement_bags} شكارة)</td>
                <td class="val-cell"><span dir="ltr">{p_cement_in:,.2f}</span></td>
                <td style="text-align:right;"><span dir="ltr">{p_cement_tons:.3f}</span> طن × <span dir="ltr">{p_cement_in:,.2f}</span> ج.م</td>
                <td class="val-cell" style="font-weight:bold; color:#0284c7;"><span dir="ltr">{cost_cement_plaster:,.2f}</span></td>
            </tr>
            <tr style="background:#e0f2fe; font-weight:800; border-top:1.5px solid #0284c7;">
                <td style="text-align:right; color:#0369a1;">⬅️ إجمالي بند أعمال المحارة</td>
                <td class="val-cell">—</td>
                <td>—</td>
                <td class="val-cell">—</td>
                <td style="text-align:right;">مجموع (مصنعية المحارة + رمل المحارة + أسمنت المحارة)</td>
                <td class="val-cell" style="font-weight:900; color:#0369a1; font-size:1.0rem;"><span dir="ltr">{cost_plaster_total:,.2f} ج.م</span></td>
            </tr>
            <tr style="background:linear-gradient(90deg, #1e3a8a, #065f46); color:#ffffff; font-weight:900;">
                <td style="text-align:right; color:#ffffff; font-size:1.0rem;">🏆 الإجمالي العام الشامل للمشروع (المباني + المحارة)</td>
                <td class="val-cell" style="color:#ffffff;">—</td>
                <td style="color:#ffffff;">—</td>
                <td class="val-cell" style="color:#ffffff;">—</td>
                <td style="text-align:right; color:#e0f2fe;">إجمالي أعمال المباني ({cost_masonry_total:,.2f}) + إجمالي أعمال المحارة ({cost_plaster_total:,.2f})</td>
                <td class="val-cell" style="color:#86efac; font-size:1.25rem; font-weight:900;"><span dir="ltr">{grand_total_cost:,.2f} ج.م</span></td>
            </tr>
        </tbody>
    </table>
    """
    report_heading_title = "مذكرة التصميم وحصر الكميات والمقايسة الشاملة — جميع المدخلات والمخرجات" if include_inputs else ("تقرير مخرجات المسقط والملخص التنفيذي — أعمال المباني والمحارة" if only_summary_and_plan else "مذكرة حصر الكميات والمقايسة التقديرية — مخرجات أعمال المباني والمحارة")

    if only_summary_and_plan:
        html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_heading_title} — {project_name}</title>
    {_get_base_report_css()}
    <style>
        @media print {{
            .page-break {{
                page-break-before: always !important;
                break-before: page !important;
            }}
            body {{
                padding: 0 !important;
                margin: 0 !important;
            }}
            .report-container {{
                padding: 10px 14px !important;
            }}
        }}
    </style>
</head>
<body>

<div class="report-container">

    <!-- Action Bar (hidden in print) -->
    <div class="action-bar no-print">
        <div style="font-weight:700; font-size:1.0rem; display:flex; align-items:center; gap:8px;">
            <span>🧱</span>
            <span>{report_heading_title} (الكود المصري ECP)</span>
        </div>
        <button class="btn-print" onclick="window.print()">
            🖨️ طباعة المذكرة / تصدير PDF
        </button>
    </div>

    <!-- ==================== الصفحة الأولى: المسقط الأفقي المصمم ==================== -->
    <div style="page-break-after: always; break-after: page;">
        <!-- Header Page 1 -->
        <div class="report-header" style="margin-bottom: 10px; padding-bottom: 8px;">
            <div class="header-title">
                <h1 style="font-size: 1.35rem; color:#1e3a8a;">المخطط الهندسي للمسقط الأفقي المصمم (Designed Plan & Structural Layout)</h1>
                <div style="margin-top:4px; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    <span class="code-badge">الكود المصري ECP للمباني والبياض</span>
                    <span style="font-size:0.85rem; color:#334155;">المشروع: <b style="color:#1e3a8a;">{project_name}</b></span>
                    <span style="font-size:0.80rem; background:#f1f5f9; padding:2px 8px; border-radius:6px; border:1px solid #cbd5e1; color:#475569;">
                        نوع الطوب: <b>{brick_type_display} ({brick_size_display})</b> | مونة <b>{mortar_cm} سم</b>
                    </span>
                </div>
                {owner_html}
            </div>
            <div class="header-meta" style="font-size: 0.80rem;">
                <div><b>تاريخ التصدير:</b> {now_str}</div>
                <div><b>قياس المباني:</b> صافي خالص بين الأعمدة (ECP)</div>
                <div><b>الصفحة:</b> 1 من 2 (المسقط الأفقي المصمم)</div>
            </div>
        </div>

        <!-- Plan Image Box -->
        <div style="border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 10px; background: #ffffff; text-align: center;">
            <div style="font-size: 0.90rem; font-weight: 700; color: #1e3a8a; margin-bottom: 6px; text-align: right; border-bottom: 1.5px solid #3b82f6; padding-bottom: 4px; display:flex; justify-content:space-between; align-items:center;">
                <span>📐 المسقط الأفقي التنفيذي متضمناً المحاور، الحوائط، الأعمدة، الشبابيك والأبواب، وأوجه المحارة</span>
                <span style="font-size:0.80rem; color:#64748b;" dir="ltr">Designed Plan & Structural Layout</span>
            </div>
            <img src="data:image/png;base64,{img_plan_b64}" alt="ECP Designed Plan" style="max-width: 100%; max-height: 200mm; object-fit: contain; border-radius: 6px;" />
            <div style="font-size:0.78rem; margin-top:6px; display:flex; gap:12px; justify-content:center; flex-wrap:wrap; color:#334155; font-weight:bold;">
                <span style="color:#EFA368;">■ حائط 12سم</span>
                <span style="color:#8B1A1A;">■ حائط 25سم</span>
                <span style="color:#0284C7;">■ حائط دروة</span>
                <span style="color:#87CEEB;">■ شباك (W#)</span>
                <span style="color:#2E7D32;">■ باب (D#)</span>
                <span style="color:#2F4F8F;">■ عمود (C#)</span>
                <span style="color:#EC4899;">▨ وجه محارة (وردي)</span>
            </div>
        </div>
    </div>

    <!-- ==================== الصفحة الثانية: بانيلات الإجماليات التنفيذية ==================== -->
    <div class="page-break" style="padding-top: 6px;">
        <!-- Header Page 2 -->
        <div class="report-header" style="margin-bottom: 12px; padding-bottom: 8px;">
            <div class="header-title">
                <h1 style="font-size: 1.35rem; color:#1e3a8a;">1. الملخص الهندسي التنفيذي لحصر المباني والمحارة والخامات التوريدية</h1>
                <div style="margin-top:4px; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    <span class="code-badge">الكود المصري ECP للمباني والبياض</span>
                    <span style="font-size:0.85rem; color:#334155;">المشروع: <b style="color:#1e3a8a;">{project_name}</b></span>
                </div>
            </div>
            <div class="header-meta" style="font-size: 0.80rem;">
                <div><b>تاريخ التصدير:</b> {now_str}</div>
                <div><b>الصفحة:</b> 2 من 2 (لوحة الإجماليات التنفيذية)</div>
            </div>
        </div>

        <div style="background: #1e3a8a; color:#ffffff; font-size:1.05rem; font-weight:bold; padding:8px 14px; border-radius:6px; margin: 8px 0 14px 0; text-align:right;">
            1. الملخص الهندسي التنفيذي لحصر المباني والمحارة والخامات التوريدية
        </div>

        <!-- 3 Top Cards (Masonry 12cm, Masonry 25cm, Plaster) -->
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom: 12px;">
            <!-- Card 1: مسطح مباني 12 سم -->
            <div style="background:#ffffff; border:1.5px solid #fdba74; border-top:4px solid #ea580c; border-radius:10px; padding:14px 12px; text-align:center;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-size:0.85rem; font-weight:700; color:#c2410c; background:#ffedd5; padding:2px 8px; border-radius:4px;">مسطح مباني 12 سم (نصف طوبة)</span>
                    <span style="font-size:1.15rem;">🧱</span>
                </div>
                <div style="font-size:1.6rem; font-weight:900; color:#1e293b; margin:8px 0 4px 0;">
                    <span dir="ltr">{n12:.2f}</span> <span style="font-size:1.1rem; color:#ea580c;">م² مسطح</span>
                </div>
                <div style="font-size:0.80rem; color:#64748b; margin-top:2px;">
                    إجمالي {g12:.2f} م² | فتحات {op12:.2f} م²
                </div>
            </div>

            <!-- Card 2: مكعب مباني 25 سم -->
            <div style="background:#ffffff; border:1.5px solid #f9a8d4; border-top:4px solid #db2777; border-radius:10px; padding:14px 12px; text-align:center;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-size:0.85rem; font-weight:700; color:#be185d; background:#fce7f3; padding:2px 8px; border-radius:4px;">مكعب مباني 25 سم (طوبة كاملة)</span>
                    <span style="font-size:1.15rem;">🏗️</span>
                </div>
                <div style="font-size:1.6rem; font-weight:900; color:#be185d; margin:8px 0 4px 0;">
                    <span dir="ltr">{v25:.2f}</span> <span style="font-size:1.1rem; color:#be185d;">م³ مكعب</span>
                </div>
                <div style="font-size:0.80rem; color:#64748b; margin-top:2px;">
                    صافي المسطح: {n25:.2f} م² | فتحات {op25:.2f} م²
                </div>
            </div>

            <!-- Card 3: صافي مسطح أعمال المحارة -->
            <div style="background:#ffffff; border:1.5px solid #86efac; border-top:4px solid #16a34a; border-radius:10px; padding:14px 12px; text-align:center;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-size:0.85rem; font-weight:700; color:#15803d; background:#dcfce7; padding:2px 8px; border-radius:4px;">صافي مسطح أعمال المحارة</span>
                    <span style="font-size:1.15rem;">🎨</span>
                </div>
                <div style="font-size:1.6rem; font-weight:900; color:#15803d; margin:8px 0 4px 0;">
                    <span dir="ltr">{p_net_m2:.2f}</span> <span style="font-size:1.1rem; color:#15803d;">م² معتمد</span>
                </div>
                <div style="font-size:0.80rem; color:#64748b; margin-top:2px;">
                    إجمالي {p_gross_m2:.2f} م² | خصم {p_ded_m2:.2f} م² ({p_active_walls} حائط)
                </div>
            </div>
        </div>

        <!-- 3 Middle Cards (Bricks Qty & Price, Sand Qty & Price, Cement Qty & Price) -->
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom: 14px;">
            <!-- Card 4: إجمالي عدد الطوب -->
            <div style="background:#ffffff; border:1.5px solid #93c5fd; border-right:4px solid #2563eb; border-radius:10px; padding:14px 12px; text-align:center;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:0.85rem; font-weight:700; color:#1d4ed8;">🧱 4️⃣ إجمالي عدد الطوب المطلوب</span>
                    <span style="font-size:1.15rem;">🧱</span>
                </div>
                <div style="font-size:1.6rem; font-weight:900; color:#1e40af; margin:8px 0 2px 0;">
                    <span dir="ltr">{bricks_total:,}</span> <span style="font-size:1.1rem;">طوبة</span>
                </div>
                <div style="font-size:0.76rem; color:#64748b; margin-bottom:6px;">
                    {brick_type_display} ({brick_size_display})
                </div>
                <div style="padding-top:6px; border-top:1px dashed #bfdbfe; font-size:0.82rem; font-weight:bold; color:#1e40af;">
                    💵 السعر التقديري: <span dir="ltr">{cost_brick:,.2f}</span> ج.م
                    <div style="font-size:0.72rem; font-weight:normal; color:#64748b; margin-top:2px;">
                        ({brick_thousands:.3f} ألف × {p_brick_in:,.0f} ج.م)
                    </div>
                </div>
            </div>

            <!-- Card 5: إجمالي الرمل الكلي -->
            <div style="background:#ffffff; border:1.5px solid #fde047; border-right:4px solid #ca8a04; border-radius:10px; padding:14px 12px; text-align:center;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:0.85rem; font-weight:700; color:#a16207;">🏜️ 5️⃣ إجمالي الرمل الكلي للمشروع</span>
                    <span style="font-size:1.15rem;">🏜️</span>
                </div>
                <div style="font-size:1.6rem; font-weight:900; color:#854d0e; margin:8px 0 2px 0;">
                    <span dir="ltr">{total_sand_all:.2f}</span> <span style="font-size:1.1rem;">م³</span>
                </div>
                <div style="font-size:0.76rem; color:#64748b; margin-bottom:6px;">
                    مباني ({sand_total_masonry:.2f}م³) + محارة ({p_sand_m3:.2f}م³) شامل 5% هالك
                </div>
                <div style="padding-top:6px; border-top:1px dashed #fef08a; font-size:0.82rem; font-weight:bold; color:#a16207;">
                    💵 السعر التقديري: <span dir="ltr">{cost_sand_all:,.2f}</span> ج.م
                    <div style="font-size:0.72rem; font-weight:normal; color:#64748b; margin-top:2px;">
                        ({total_sand_all:.2f} م³ × {p_sand_in:,.0f} ج.م)
                    </div>
                </div>
            </div>

            <!-- Card 6: إجمالي الأسمنت الكلي -->
            <div style="background:#ffffff; border:1.5px solid #7dd3fc; border-right:4px solid #0284c7; border-radius:10px; padding:14px 12px; text-align:center;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:0.85rem; font-weight:700; color:#0369a1;">🏗️ 6️⃣ إجمالي الأسمنت الكلي للمشروع</span>
                    <span style="font-size:1.15rem;">🏗️</span>
                </div>
                <div style="font-size:1.6rem; font-weight:900; color:#075985; margin:8px 0 2px 0;">
                    <span dir="ltr">{total_cement_tons_all:.2f}</span> <span style="font-size:1.1rem;">طن</span>
                </div>
                <div style="font-size:0.76rem; color:#64748b; margin-bottom:6px;">
                    {total_cement_bags_all} شكارة 50كجم (مباني {cement_masonry_tons:.2f}ط + محارة {p_cement_tons:.2f}ط)
                </div>
                <div style="padding-top:6px; border-top:1px dashed #bae6fd; font-size:0.82rem; font-weight:bold; color:#0369a1;">
                    💵 السعر التقديري: <span dir="ltr">{cost_cement_all:,.2f}</span> ج.م
                    <div style="font-size:0.72rem; font-weight:normal; color:#64748b; margin-top:2px;">
                        ({total_cement_tons_all:.2f} طن × {p_cement_in:,.0f} ج.م)
                    </div>
                </div>
            </div>
        </div>

        <!-- Bottom Full Width Card: الإجمالي المالي التقديري الشامل للمشروع -->
        <div style="background:#ffffff; border:2px solid #16a34a; border-radius:12px; padding:16px 20px; text-align:center; box-shadow:0 3px 10px rgba(22, 163, 74, 0.12); margin-bottom: 20px;">
            <div style="font-size:1.05rem; font-weight:800; color:#15803d; margin-bottom:6px; display:flex; justify-content:center; align-items:center; gap:8px;">
                <span>💰</span>
                <span>الإجمالي المالي التقديري الشامل للمشروع (المباني + المحارة)</span>
                <span>💰</span>
            </div>
            <div style="font-size:2.0rem; font-weight:900; color:#166534; margin:6px 0;">
                <span dir="ltr">{grand_total_cost:,.2f}</span> <span style="font-size:1.3rem;">ج.م</span>
            </div>
            <div style="font-size:0.88rem; color:#475569; margin-top:4px;">
                إجمالي أعمال المباني (<span dir="ltr">{cost_masonry_total:,.2f}</span> ج.م) + إجمالي أعمال المحارة (<span dir="ltr">{cost_plaster_total:,.2f}</span> ج.م)
            </div>
        </div>

        <!-- Sign-off Block on Page 2 -->
        <div class="signature-block" style="display:flex; justify-content:space-between; margin-top:20px; padding-top:14px; border-top:2px solid #cbd5e1;">
            <div class="sig-box" style="flex:1; text-align:center; padding:10px;">
                <div class="sig-title" style="font-weight:700; color:#1e3a8a;">مهندس المكتب الفني / الحصر:</div>
                <div style="margin-top:24px; color:#94a3b8;">التوقيع: ___________________</div>
            </div>
            <div class="sig-box" style="flex:1; text-align:center; padding:10px;">
                <div class="sig-title" style="font-weight:700; color:#1e3a8a;">مهندس التنفيذ وإدارة المشروع:</div>
                <div style="margin-top:24px; color:#94a3b8;">التوقيع: ___________________</div>
            </div>
            <div class="sig-box" style="flex:1; text-align:center; padding:10px;">
                <div class="sig-title" style="font-weight:700; color:#1e3a8a;">اعتماد الاستشاري المشرف:</div>
                <div style="margin-top:24px; color:#94a3b8;">الختم والتاريخ: ______________</div>
            </div>
        </div>
    </div>

</div>

</body>
</html>
"""
        return html_content

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_heading_title} — {project_name}</title>
    {_get_base_report_css()}
    <style>
        .badge-tag {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.80rem;
            font-weight: 700;
        }}
        .kpi-card {{
            border-radius: 8px;
            padding: 12px 14px;
            border: 1px solid #cbd5e1;
            page-break-inside: avoid;
        }}
        .kpi-title {{ font-size: 0.82rem; font-weight: 700; color: #475569; }}
        .kpi-val {{ font-size: 1.25rem; font-weight: 800; margin-top: 4px; }}
        .kpi-sub {{ font-size: 0.75rem; color: #64748b; margin-top: 2px; }}
    </style>
</head>
<body>

<div class="report-container">

    <!-- Action Bar (hidden in print) -->
    <div class="action-bar no-print">
        <div style="font-weight:700; font-size:1.0rem; display:flex; align-items:center; gap:8px;">
            <span>🧱</span>
            <span>{report_heading_title} (الكود المصري ECP)</span>
        </div>
        <button class="btn-print" onclick="window.print()">
            🖨️ طباعة المذكرة / تصدير PDF
        </button>
    </div>

    <!-- Report Header Block -->
    <div class="report-header">
        <div class="header-title">
            <h1>{report_heading_title}</h1>
            <div style="margin-top:6px; display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                <span class="code-badge">الكود المصري ECP للمباني والبياض</span>
                <span style="font-size:0.92rem; color:#334155;">المشروع: <b style="color:#1e3a8a;">{project_name}</b></span>
                <span style="font-size:0.85rem; background:#f1f5f9; padding:2px 8px; border-radius:6px; border:1px solid #cbd5e1; color:#475569;">
                    نوع الطوب: <b>{brick_type_display} ({brick_size_display})</b> | مونة <b>{mortar_cm} سم</b>
                </span>
            </div>
            {owner_html}
        </div>
        <div class="header-meta">
            <div><b>تاريخ التصدير:</b> {now_str}</div>
            <div><b>قياس المباني:</b> صافي خالص بين الأعمدة (ECP)</div>
            <div><b>خصم المحارة:</b> {deduction_rule_str}</div>
        </div>
    </div>

    <!-- Section 1: Executive KPI Cards -->
    <div class="section-title">1. الملخص الهندسي التنفيذي لحصر المباني والمحارة والخامات التوريدية</div>
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin: 12px 0 18px 0;">
        <div class="kpi-card" style="background:#fff7ed; border-right:4px solid #ea580c;">
            <div class="kpi-title" style="color:#c2410c;">🧱 مسطح مباني 12 سم (نصف طوبة)</div>
            <div class="kpi-val" style="color:#9a3412;"><span dir="ltr">{n12:.2f}</span> م² مسطح</div>
            <div class="kpi-sub">إجمالي {g12:.2f} م² | فتحات {op12:.2f} م²</div>
        </div>
        <div class="kpi-card" style="background:#fdf2f8; border-right:4px solid #db2777;">
            <div class="kpi-title" style="color:#be185d;">🏗️ مكعب مباني 25 سم (طوبة كاملة)</div>
            <div class="kpi-val" style="color:#9d174d;"><span dir="ltr">{v25:.2f}</span> م³ مكعب</div>
            <div class="kpi-sub">صافي المسطح: {n25:.2f} م² | فتحات {op25:.2f} م²</div>
        </div>
        <div class="kpi-card" style="background:#f0fdf4; border-right:4px solid #16a34a;">
            <div class="kpi-title" style="color:#15803d;">🎨 صافي مسطح أعمال المحارة</div>
            <div class="kpi-val" style="color:#166534;"><span dir="ltr">{p_net_m2:.2f}</span> م² معتمد</div>
            <div class="kpi-sub">إجمالي {p_gross_m2:.2f} م² | خصم {p_ded_m2:.2f} م² ({p_active_walls} حائط)</div>
        </div>
        <div class="kpi-card" style="background:#eff6ff; border-right:4px solid #2563eb;">
            <div class="kpi-title" style="color:#1d4ed8;">🧱 4️⃣ إجمالي عدد الطوب المطلوب</div>
            <div class="kpi-val" style="color:#1e40af;"><span dir="ltr">{bricks_total:,}</span> طوبة</div>
            <div class="kpi-sub">{brick_type_display} ({brick_size_display})</div>
            <div style="margin-top:6px; padding-top:6px; border-top:1px dashed #bfdbfe; font-size:0.82rem; font-weight:bold; color:#1e40af;">
                💵 السعر التقديري: <span dir="ltr">{cost_brick:,.2f}</span> ج.م <span style="font-size:0.73rem; font-weight:normal; color:#475569;">({brick_thousands:.3f} ألف × {p_brick_in:,.0f} ج.م)</span>
            </div>
        </div>
        <div class="kpi-card" style="background:#fefce8; border-right:4px solid #ca8a04;">
            <div class="kpi-title" style="color:#a16207;">🏜️ 5️⃣ إجمالي الرمل الكلي للمشروع</div>
            <div class="kpi-val" style="color:#854d0e;"><span dir="ltr">{total_sand_all:.2f}</span> م³</div>
            <div class="kpi-sub">مباني ({sand_total_masonry:.2f}م³) + محارة ({p_sand_m3:.2f}م³) شامل 5% هالك</div>
            <div style="margin-top:6px; padding-top:6px; border-top:1px dashed #fef08a; font-size:0.80rem; font-weight:bold; color:#a16207;">
                💵 السعر التقديري: <span dir="ltr">{cost_sand_all:,.2f}</span> ج.م <span style="font-size:0.73rem; font-weight:normal; color:#475569;">({total_sand_all:.2f} م³ × {p_sand_in:,.0f} ج.م)</span>
            </div>
        </div>
        <div class="kpi-card" style="background:#f0f9ff; border-right:4px solid #0284c7;">
            <div class="kpi-title" style="color:#0369a1;">🏗️ 6️⃣ إجمالي الأسمنت الكلي للمشروع</div>
            <div class="kpi-val" style="color:#075985;"><span dir="ltr">{total_cement_tons_all:.2f}</span> طن</div>
            <div class="kpi-sub">{total_cement_bags_all} شكارة 50كجم (مباني {cement_masonry_tons:.2f}ط + محارة {p_cement_tons:.2f}ط)</div>
            <div style="margin-top:6px; padding-top:6px; border-top:1px dashed #bae6fd; font-size:0.80rem; font-weight:bold; color:#0369a1;">
                💵 السعر التقديري: <span dir="ltr">{cost_cement_all:,.2f}</span> ج.م <span style="font-size:0.73rem; font-weight:normal; color:#475569;">({total_cement_tons_all:.2f} طن × {p_cement_in:,.0f} ج.م)</span>
            </div>
        </div>
        <div class="kpi-card" style="background:#f0fdf4; border:2px solid #16a34a; border-right:5px solid #15803d; grid-column: 1 / -1;">
            <div class="kpi-title" style="color:#15803d; font-size:0.90rem;">💰 الإجمالي المالي التقديري الشامل للمشروع (المباني + المحارة)</div>
            <div class="kpi-val" style="color:#166534; font-size:1.55rem;"><span dir="ltr">{grand_total_cost:,.2f}</span> ج.م</div>
            <div class="kpi-sub" style="color:#334155; font-size:0.82rem;">إجمالي أعمال المباني ({cost_masonry_total:,.2f} ج.م) + إجمالي أعمال المحارة ({cost_plaster_total:,.2f} ج.م)</div>
        </div>
    </div>

    <!-- Section 2: Plan Drawing Box -->
    {plan_drawing_html}

    {inputs_section_html}

    <!-- Section 3: Walls 12 cm Takeoff -->
    <div class="section-title">3. جدول حصر كميات أعمال مباني طوب سمك 12 سم (نصف طوبة — بالمتر المسطح م²)</div>
    <table class="data-table" style="width:100%; border-collapse:collapse; margin-top:8px;">
        <thead>
            <tr>
                <th style="text-align:right;">الحائط</th>
                <th>طول المحور (م)</th>
                <th>خصم الأعمدة (م)</th>
                <th>طول المباني الصافي (م)</th>
                <th>الارتفاع (م)</th>
                <th>المساحة الإجمالية (م²)</th>
                <th>مساحة الفتحات (م²)</th>
                <th>المساحة الصافية (م²)</th>
                <th>عدد الطوب (وحدة)</th>
            </tr>
        </thead>
        <tbody>
            {rows_12_html}
        </tbody>
    </table>

    <!-- Section 4: Walls 25 cm Takeoff -->
    <div class="section-title">4. جدول حصر كميات أعمال مباني طوب سمك 25 سم (طوبة كاملة — بالمتر المكعب م³)</div>
    <table class="data-table" style="width:100%; border-collapse:collapse; margin-top:8px;">
        <thead>
            <tr>
                <th style="text-align:right;">الحائط</th>
                <th>طول المحور (م)</th>
                <th>خصم الأعمدة (م)</th>
                <th>طول المباني الصافي (م)</th>
                <th>الارتفاع (م)</th>
                <th>المساحة الإجمالية (م²)</th>
                <th>مساحة الفتحات (م²)</th>
                <th>المساحة الصافية (م²)</th>
                <th>حجم الطوب (م³)</th>
                <th>عدد الطوب (وحدة)</th>
            </tr>
        </thead>
        <tbody>
            {rows_25_html}
        </tbody>
    </table>

    <!-- Section 5: Openings Detail -->
    {openings_html}

    <!-- Section 6: Plaster Survey -->
    {plaster_table_html}

    <!-- Section 7: Materials BOQ -->
    <div class="section-title">7. مقايسة خامات المونة ومواد البناء الشاملة (طبقاً للكود المصري وأصول الصناعة)</div>
    <table class="data-table" style="width:100%; border-collapse:collapse; margin-top:8px;">
        <thead>
            <tr>
                <th style="text-align:right;">بند الأعمال</th>
                <th>الوحدة</th>
                <th>الكمية الصافية</th>
                <th>رمل صافي (م³)</th>
                <th>رمل مع الهالك 5% (م³)</th>
                <th>أسمنت (طن)</th>
                <th>شكاير أسمنت (50كجم)</th>
                <th>عدد الطوب المطلوب</th>
            </tr>
        </thead>
        <tbody>
            {mat_rows_html}
        </tbody>
    </table>

    <!-- Section 8: Pricing Table -->
    {pricing_table_html}

    <!-- Section 9: ECP Engineering Notes & Specifications -->
    <div class="section-title">9. الملاحظات الفنية والاشتراطات الهندسية المعتمدة (ECP Technical Specs)</div>
    <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:16px 20px; font-size:0.86rem; line-height:1.8; color:#334155; margin-top:10px; page-break-inside: avoid;">
        <ol style="padding-right:20px; margin:0;">
            <li><b>قياس أطوال حوائط المباني:</b> تم الاعتماد على الطول الصافي الخالص بين أوجه الأعمدة الخرسانية بعد خصم تداخلات قطاعات الأعمدة آلياً طبقاً للمواصفات الفنية للكود المصري.</li>
            <li><b>مونة أعمال المباني:</b> تم احتساب نسبة خلط المونة بمعدل <b>350 كجم أسمنت بورتلاندي عادي لكل 1 م³ رمل حرش نظيف</b> (ما يعادل 7 شكاير أسمنت)، مع إضافة <b>5% نسبة هالك تشغيل طبيعي</b>.</li>
            <li><b>حصر أعمال البياض (المحارة):</b> سمك البياض المعتمد <b>2.0 سم</b> شاملاً الطرطشة العمومية المسمارية، البؤج، الأوتار، البطانة والضهارة. معدل استهلاك الرمل: <b>1 م³ رمل لكل 42 م² مسطح بياض</b> بمحتوى أسمنت 350 كجم/م³.</li>
            <li><b>قواعد خصم الفتحات في المحارة:</b> الفتحات حتى مساحة <b>4.00 م² لا تُخصم</b> طبقاً للكود المصري وتعتبر مقابلاً لمصنعية وخامات السوك والأكتاف والجلسات. والفتحات التي تتجاوز مساحتها 4.00 م² يُخصم الفارق الزائد عن 4.00 م² فقط.</li>
            <li><b>الأسعار والمقايسة:</b> الأسعار المذكورة تقديرية استرشادية بناءً على المدخلات المحددة بالموقع، وتعتبر ملزمة متى اعتمدت في العقد التنفيذي.</li>
        </ol>
    </div>

    <!-- Sign-off Block -->
    <div class="signature-block" style="display:flex; justify-content:space-between; margin-top:30px; padding-top:16px; border-top:2px solid #cbd5e1; page-break-inside: avoid;">
        <div class="sig-box" style="flex:1; text-align:center; padding:10px;">
            <div class="sig-title" style="font-weight:700; color:#1e3a8a;">مهندس المكتب الفني / الحصر:</div>
            <div style="margin-top:28px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box" style="flex:1; text-align:center; padding:10px;">
            <div class="sig-title" style="font-weight:700; color:#1e3a8a;">مهندس التنفيذ وإدارة المشروع:</div>
            <div style="margin-top:28px; color:#94a3b8;">التوقيع: ___________________</div>
        </div>
        <div class="sig-box" style="flex:1; text-align:center; padding:10px;">
            <div class="sig-title" style="font-weight:700; color:#1e3a8a;">اعتماد الاستشاري المشرف:</div>
            <div style="margin-top:28px; color:#94a3b8;">الختم والتاريخ: ______________</div>
        </div>
    </div>

</div>

</body>
</html>
"""
    return html_content
