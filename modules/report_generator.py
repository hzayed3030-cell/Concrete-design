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
        status_color = "#16a34a" if "Safe" in p.get("Status", "") else "#dc2626"
        punching_rows += f"""
        <tr>
            <td><b>{p.get('Column ID', '')}</b></td>
            <td>{p.get('Grid', '')}</td>
            <td>{p.get('Location Type', '')}</td>
            <td>{p.get('Pu (ton)', 0.0):.2f}</td>
            <td>{p.get('bo (cm)', 0.0):.1f}</td>
            <td>{p.get('qup (kg/cm²)', 0.0):.2f}</td>
            <td>{p.get('qcup (kg/cm²)', 0.0):.2f}</td>
            <td>{p.get('Ratio', 0.0):.2f}</td>
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
                <th>Pu (ton)</th>
                <th>bo (cm)</th>
                <th>qup (kg/cm²)</th>
                <th>qcup (kg/cm²)</th>
                <th>qup / qcup</th>
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

    <!-- Section 4: Column Reactions & Multi-Storey Loads -->
    <div class="section-title page-break">4. ردود أفعال وأحمال الأعمدة ({num_floors} طوابق) — (Column Reactions & Loads)</div>
    {reaction_drawing_html}
    {reactions_table_html}

    <div class="subsection-title">📌 نماذج التصميم الحاكمة للأعمدة (Governing Column Models by Type):</div>
    {models_table_html}

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
) -> str:
    """
    Generates a print-ready, professional HTML/PDF calculation sheet for the
    Concrete Column Quantity Survey (Customs module) according to ECP 203.
    Supports single or multiple column types and renders drawings for every column model.
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    top_floor_str = "دور أخير (Top Floor)" if is_top_floor else "متكرر (Typical Floor - Overlap Splice)"

    drawings_html = ""
    if drawings_list and len(drawings_list) > 0:
        drawings_cards = ""
        for idx, d in enumerate(drawings_list, 1):
            d_name = d.get("name", f"C{idx}")
            d_b = d.get("b", 30.0)
            d_t = d.get("t", 60.0)
            d_nb = d.get("n_bars", 8)
            d_phi = d.get("phi_main", 16)
            d_img = d.get("img_b64", "")
            if d_img:
                drawings_cards += f"""
                <div class="drawing-card" style="margin: 18px 0 24px 0; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 12px; background: #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.05); page-break-inside: avoid;">
                    <div style="font-size: 1.02rem; font-weight: 800; color: #1e3a8a; margin-bottom: 8px; text-align: right; border-bottom: 2px solid #3b82f6; padding-bottom: 4px; display:flex; justify-content:space-between; align-items:center;">
                        <span>📐 مخطط وتفريد تسليح نموذج: <b style="color:#2563eb;">{d_name}</b></span>
                        <span style="font-size:0.90rem; color:#475569;" dir="ltr">{d_b:.0f} × {d_t:.0f} cm | {d_nb} Φ {d_phi} mm</span>
                    </div>
                    <div style="text-align: center;">
                        <img src="{d_img}" alt="CAD Drawing {d_name}" style="max-width: 100%; height: auto; border-radius: 6px;">
                    </div>
                </div>
                """
        drawings_html = f"""
        <div class="section-title">2. المخططات الإنشائية وتفريد التسليح لجميع نماذج الأعمدة ({len(drawings_list)} نماذج)</div>
        {drawings_cards}
        """
    elif img_plan_b64 and img_elev_b64:
        drawings_html = f"""
        <div class="section-title">2. الرسومات الهندسية وتفريد حديد التسليح (Engineering Drawings & BBS)</div>
        <div class="drawings-grid" style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin:16px 0;">
            <div class="drawing-box">
                <img src="{img_plan_b64}" alt="Column Cross Section" style="max-width:100%; height:auto; border-radius:6px;">
                <div class="drawing-caption" style="margin-top:6px; font-weight:700; color:#1e3a8a;">Figure 1: مسقط أفقي لقطاع العمود وتوزيع الكانات والأسياخ</div>
            </div>
            <div class="drawing-box">
                <img src="{img_elev_b64}" alt="Column Elevation & BBS" style="max-width:100%; height:auto; border-radius:6px;">
                <div class="drawing-caption" style="margin-top:6px; font-weight:700; color:#1e3a8a;">Figure 2: قطاع رأسي وتفريد الحديد والوصلات</div>
            </div>
        </div>
        """
    elif img_plan_b64:
        drawings_html = f"""
        <div class="section-title">2. المخطط الإنشائي المتكامل وتفريد التسليح (Structural Drawings & BBS Detailing)</div>
        <div class="drawing-box" style="margin:16px 0; text-align:center;">
            <img src="{img_plan_b64}" alt="Unified CAD Drawing" style="max-width:100%; height:auto; border-radius:8px; border:1px solid #cbd5e1; box-shadow:0 3px 8px rgba(0,0,0,0.06);">
        </div>
        """

    # Multi-Type or Single Type Rendering Logic
    if col_results and len(col_results) > 0:
        total_cols_count = sum(r.get("n_cols", 0) for r in col_results)
        total_vol_all = sum(r.get("vol_col_total_m3", 0.0) for r in col_results)
        total_w_main_kg_all = sum(r.get("w_main_total_kg", 0.0) for r in col_results)
        total_w_st_kg_all = sum(r.get("w_st_total_kg", 0.0) for r in col_results)
        total_w_steel_kg_all = total_w_main_kg_all + total_w_st_kg_all
        total_w_steel_ton_all = total_w_steel_kg_all / 1000.0
        overall_rate = (total_w_steel_kg_all / total_vol_all) if total_vol_all > 0 else 0.0

        # Section 1: Geometric Specs for Multi-Type
        specs_rows = ""
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

        section1_html = f"""
        <div class="section-title">1. البيانات الهندسية لقطاعات ونماذج الأعمدة ({len(col_results)} نماذج — إجمالي {total_cols_count} عمود)</div>
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
        """

        # Section 3: Takeoff Breakdown Table for Multi-Type
        takeoff_body_rows = ""
        total_steel_linear_m = 0.0
        item_counter = 1
        rebar_by_dia_rg = {}

        for r in col_results:
            c_name = r.get("name", f"C{item_counter}")
            c_b = r.get("b", 30.0)
            c_t = r.get("t", 60.0)
            c_nc = r.get("n_cols", 1)
            c_nb = r.get("n_bars", 8)
            c_phi = r.get("phi_main", 16)
            c_nr = r.get("n_rows", 4)
            c_tie = r.get("tie_type", "Automatic").split(' ')[0]
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

            c_main_linear = c_nc * c_nb * c_L_bar_m
            c_st_linear = c_nc * c_n_ties * c_L_tie_m
            total_steel_linear_m += (c_main_linear + c_st_linear)

            # Aggregate by diameter
            if c_phi not in rebar_by_dia_rg:
                rebar_by_dia_rg[c_phi] = {"phi": c_phi, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
            rebar_by_dia_rg[c_phi]["total_len_m"] += c_main_linear
            rebar_by_dia_rg[c_phi]["total_w_kg"] += c_w_main_kg
            rebar_by_dia_rg[c_phi]["main_pieces"] += (c_nc * c_nb)
            rebar_by_dia_rg[c_phi]["desc"].append(f"رئيسي {c_name} ({c_nc * c_nb} سيخ)")

            if phi_st not in rebar_by_dia_rg:
                rebar_by_dia_rg[phi_st] = {"phi": phi_st, "total_len_m": 0.0, "total_w_kg": 0.0, "main_pieces": 0, "tie_pieces": 0, "desc": []}
            rebar_by_dia_rg[phi_st]["total_len_m"] += c_st_linear
            rebar_by_dia_rg[phi_st]["total_w_kg"] += c_w_st_kg
            rebar_by_dia_rg[phi_st]["tie_pieces"] += (c_nc * c_n_ties)
            rebar_by_dia_rg[phi_st]["desc"].append(f"كانات {c_name} ({c_nc * c_n_ties} كانة)")

            takeoff_body_rows += f"""
            <tr style="background:#f8fafc;">
                <td style="font-weight:bold; text-align:right; color:#1e3a8a;">{item_counter}.1. خرسانة مسلحة ({c_name})</td>
                <td class="val-cell" style="font-weight:bold; color:#1e3a8a;"><span dir="ltr">{c_b:.0f} × {c_t:.0f} cm</span></td>
                <td style="font-weight:bold;"><span dir="ltr">{c_nc}</span> عمود</td>
                <td class="val-cell" style="font-weight:bold; color:#1e40af; background:#eff6ff;"><span dir="ltr">{c_vol_total:.2f} m³</span></td>
                <td style="font-size:0.85rem; color:#64748b;">حجم العمود = <span dir="ltr">{c_vol_single:.3f} m³</span> (صافي <span dir="ltr">H={H/100:.2f}m</span>)</td>
            </tr>
            <tr>
                <td style="font-weight:bold; text-align:right; color:#b91c1c;">{item_counter}.2. تسليح رئيسي ({c_name})</td>
                <td class="val-cell" style="font-weight:bold; color:#b91c1c;"><span dir="ltr">{c_nb} Φ {c_phi} mm [{c_nr} Rows]</span></td>
                <td style="font-weight:bold;"><span dir="ltr">{c_nc * c_nb}</span> سيخ</td>
                <td class="val-cell" style="font-weight:bold; color:#b91c1c; background:#fef2f2;"><span dir="ltr">{c_w_main_kg:.1f} kg ({c_w_main_ton:.3f} Ton)</span></td>
                <td style="font-size:0.85rem; color:#64748b;">طول السيخ = <span dir="ltr">{c_L_bar_m:.2f}m</span> (ارتفاع <span dir="ltr">{H:.0f}</span> + سقف <span dir="ltr">{t_slab:.0f}</span> + وصلة <span dir="ltr">{lap_factor:.0f}Φ</span>)</td>
            </tr>
            <tr style="background:#f8fafc;">
                <td style="font-weight:bold; text-align:right; color:#15803d; border-bottom:3px solid #334155 !important;">{item_counter}.3. كانات ({c_name})</td>
                <td class="val-cell" style="font-weight:bold; color:#15803d; border-bottom:3px solid #334155 !important;"><span dir="ltr">{c_tie} - Φ{phi_st} mm</span></td>
                <td style="font-weight:bold; border-bottom:3px solid #334155 !important;"><span dir="ltr">{c_nc * c_n_ties}</span> كانة (<span dir="ltr">{c_n_ties}/عمود)</span></td>
                <td class="val-cell" style="font-weight:bold; color:#15803d; background:#f0fdf4; border-bottom:3px solid #334155 !important;"><span dir="ltr">{c_w_st_kg:.1f} kg ({c_w_st_ton:.3f} Ton)</span></td>
                <td style="font-size:0.85rem; color:#64748b; border-bottom:3px solid #334155 !important;">طول الكانة = <span dir="ltr">{c_L_tie_m:.2f}m</span> (كثافة <span dir="ltr">{n_st_m} Φ{phi_st}/m'</span> | كانة <span dir="ltr">{c_b-2*2.5:.0f}×{c_t-2*2.5:.0f} cm</span>)</td>
            </tr>
            """
            item_counter += 1

        # Build diameter breakdown rows for report
        dia_rows_report = ""
        total_pieces_report = 0
        for phi_key in sorted(rebar_by_dia_rg.keys()):
            d_info = rebar_by_dia_rg[phi_key]
            d_phi = d_info["phi"]
            d_len_m = d_info["total_len_m"]
            d_w_kg = d_info["total_w_kg"]
            d_w_ton = d_w_kg / 1000.0
            d_w_per_m = (d_phi**2) / 162.0
            
            p_parts = []
            tot_p = 0
            if d_info["main_pieces"] > 0:
                p_parts.append(f"{d_info['main_pieces']} سيخ")
                tot_p += d_info["main_pieces"]
            if d_info["tie_pieces"] > 0:
                p_parts.append(f"{d_info['tie_pieces']} كانة")
                tot_p += d_info["tie_pieces"]
            total_pieces_report += tot_p
            
            role_label = "رئيسي + كانات" if (d_info["main_pieces"] > 0 and d_info["tie_pieces"] > 0) else ("تسليح رئيسي" if d_info["main_pieces"] > 0 else "حديد كانات")
            pieces_str = " + ".join(p_parts)
            desc_str = " | ".join(d_info["desc"])

            dia_rows_report += f"""
            <tr style="background:#fffbeb;">
                <td style="font-weight:bold; text-align:right; color:#b45309;">🔹 حديد تسليح <span dir="ltr">Φ{d_phi} mm</span> ({role_label})</td>
                <td class="val-cell" style="font-weight:bold; color:#b45309;"><span dir="ltr">{d_w_per_m:.3f} kg/m'</span></td>
                <td style="font-weight:bold; color:#b45309;"><span dir="ltr">{pieces_str}</span> (<span dir="ltr">{d_len_m:.1f} m'</span>)</td>
                <td class="val-cell" style="font-weight:bold; color:#92400e; background:#fef3c7;"><span dir="ltr">{d_w_kg:.1f} kg ({d_w_ton:.3f} Ton)</span></td>
                <td style="font-size:0.85rem; color:#64748b;">{desc_str}</td>
            </tr>
            """

        takeoff_table_html = f"""
        <table class="survey-table">
            <thead>
                <tr>
                    <th style="text-align:right;">البند / Component</th>
                    <th>مقاس العمود / المواصفة</th>
                    <th>العدد</th>
                    <th style="background-color:#1d4ed8 !important;">الوزن / الحجم الإجمالي</th>
                    <th>ملاحظات</th>
                </tr>
            </thead>
            <tbody>
                {takeoff_body_rows}
                <tr style="background:#eff6ff !important; font-weight:bold; color:#1e3a8a; font-size:0.95rem; border-top:2px solid #3b82f6;">
                    <td style="text-align:right; font-weight:bold;">🔷 إجمالي الخرسانة المسلحة ({len(col_results)} نماذج)</td>
                    <td class="val-cell">كافة قطاعات الأعمدة</td>
                    <td class="val-cell" style="font-weight:bold;"><span dir="ltr">{total_cols_count}</span> عمود</td>
                    <td class="val-cell" style="font-weight:bold; color:#1e40af; background:#dbeafe;"><span dir="ltr">{total_vol_all:.2f} m³</span></td>
                    <td style="font-size:0.85rem; color:#475569;">إجمالي خرسانة الأعمدة بالمشروع</td>
                </tr>
                {dia_rows_report}
                <tr class="survey-total-row">
                    <td style="text-align:right; font-size:1.02rem;">✅ الإجمالي العام لحديد التسليح (كافة النماذج)</td>
                    <td class="val-cell">رئيسي + كانات (كافة الأقطار)</td>
                    <td><span dir="ltr">{total_pieces_report}</span> قطعة (<span dir="ltr">{total_steel_linear_m:.1f} m'</span>)</td>
                    <td class="val-cell" style="font-size:1.08rem; color:#854d0e;"><span dir="ltr">{total_w_steel_kg_all:.1f} kg ({total_w_steel_ton_all:.3f} Ton)</span></td>
                    <td>معدل الحديد الكلي = <span dir="ltr">{overall_rate:.1f} kg/m³</span></td>
                </tr>
            </tbody>
        </table>
        """
    else:
        # Fallback to single column type
        section1_html = f"""
        <div class="section-title">1. البيانات الهندسية لقطاع العمود (Column Geometric Specifications)</div>
        <div class="info-grid">
            <div class="info-card">
                <div class="card-lbl">أبعاد القطاع (b × t)</div>
                <div class="card-val"><span dir="ltr">{b:.0f} × {t:.0f} cm</span></div>
            </div>
            <div class="info-card">
                <div class="card-lbl">ارتفاع العمود الصافي (H)</div>
                <div class="card-val"><span dir="ltr">{H:.0f} cm ({H/100:.2f} m)</span></div>
            </div>
            <div class="info-card">
                <div class="card-lbl">تخانة السقف / الكمرة (ts)</div>
                <div class="card-val"><span dir="ltr">{t_slab:.0f} cm</span></div>
            </div>
            <div class="info-card">
                <div class="card-lbl">عدد الأعمدة الإجمالي (N)</div>
                <div class="card-val" style="color:#1e40af;"><span dir="ltr">{n_cols}</span> عمود</div>
            </div>
            <div class="info-card">
                <div class="card-lbl">التسليح الرئيسي (Main Rebar)</div>
                <div class="card-val" style="color:#b91c1c;"><span dir="ltr">{n_bars} Φ {phi_main} mm [{n_rows} Rows]</span></div>
            </div>
            <div class="info-card">
                <div class="card-lbl">نوع وتوزيع الكانات (Stirrup Ties)</div>
                <div class="card-val" style="color:#15803d;"><span dir="ltr">{n_st_m} Φ {phi_st} / m'</span> | {tie_type.split(' ')[0]}</div>
            </div>
        </div>
        """

        takeoff_table_html = f"""
        <table class="survey-table">
            <thead>
                <tr>
                    <th style="text-align:right;">البند / Component</th>
                    <th>مقاس العمود / المواصفة</th>
                    <th>العدد</th>
                    <th style="background-color:#1d4ed8 !important;">الوزن / الحجم الإجمالي</th>
                    <th>ملاحظات</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="font-weight:bold; text-align:right;">1. الخرسانة المسلحة للأعمدة</td>
                    <td class="val-cell" style="font-weight:bold; color:#1e3a8a;"><span dir="ltr">{b:.0f} × {t:.0f} cm</span></td>
                    <td style="font-weight:bold;"><span dir="ltr">{n_cols}</span> عمود</td>
                    <td class="val-cell" style="font-weight:bold; color:#1e40af; background:#eff6ff;"><span dir="ltr">{vol_col_total_m3:.2f} m³</span></td>
                    <td style="font-size:0.85rem; color:#64748b;">حجم العمود = <span dir="ltr">{vol_col_single_m3:.3f} m³</span> (صافي <span dir="ltr">H={H/100:.2f}m</span>)</td>
                </tr>
                <tr>
                    <td style="font-weight:bold; text-align:right;">2. حديد التسليح الرئيسي</td>
                    <td class="val-cell" style="font-weight:bold; color:#b91c1c;"><span dir="ltr">{n_bars} Φ {phi_main} mm [{n_rows} Rows]</span></td>
                    <td style="font-weight:bold;"><span dir="ltr">{n_cols * n_bars}</span> سيخ</td>
                    <td class="val-cell" style="font-weight:bold; color:#b91c1c; background:#fef2f2;"><span dir="ltr">{w_main_total_kg:.1f} kg ({w_main_total_ton:.3f} Ton)</span></td>
                    <td style="font-size:0.85rem; color:#64748b;">طول السيخ = <span dir="ltr">{L_bar_m:.2f}m</span> (ارتفاع <span dir="ltr">{H:.0f}</span> + سقف <span dir="ltr">{t_slab:.0f}</span> + وصلة <span dir="ltr">{lap_factor:.0f}Φ</span>)</td>
                </tr>
                <tr>
                    <td style="font-weight:bold; text-align:right;">3. حديد الكانات</td>
                    <td class="val-cell" style="font-weight:bold; color:#15803d;"><span dir="ltr">{tie_type.split(' ')[0]} - Φ{phi_st} mm</span></td>
                    <td style="font-weight:bold;"><span dir="ltr">{n_cols * n_ties_per_col}</span> كانة (<span dir="ltr">{n_ties_per_col}</span>/عمود)</td>
                    <td class="val-cell" style="font-weight:bold; color:#15803d; background:#f0fdf4;"><span dir="ltr">{w_st_total_kg:.1f} kg ({w_st_total_ton:.3f} Ton)</span></td>
                    <td style="font-size:0.85rem; color:#64748b;">طول الكانة = <span dir="ltr">{L_tie_m:.2f}m</span> (كثافة <span dir="ltr">{n_st_m} Φ{phi_st}/m'</span> | كانة <span dir="ltr">{b-2*2.5:.0f}×{t-2*2.5:.0f} cm</span>)</td>
                </tr>
                <tr class="survey-total-row">
                    <td style="text-align:right; font-size:1.0rem;">✅ الإجمالي العام لحديد التسليح</td>
                    <td class="val-cell"><span dir="ltr">Φ{phi_main} + Φ{phi_st}</span></td>
                    <td>—</td>
                    <td class="val-cell" style="font-size:1.05rem; color:#854d0e;"><span dir="ltr">{w_steel_total_kg:.1f} kg ({w_steel_total_ton:.3f} Ton)</span></td>
                    <td>معدل الحديد = <span dir="ltr">{steel_rate_kg_m3:.1f} kg/m³</span></td>
                </tr>
            </tbody>
        </table>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ECP 203 - Concrete Columns Quantity Survey</title>
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
        <div style="font-weight:700; font-size:1.05rem;">📊 تقرير حصر خرسانات وحديد الأعمدة — Concrete Columns Quantity Survey</div>
        <button class="btn-print" onclick="window.print();">🖨️ طباعة التقرير / حفظ كـ PDF (Print / Save as PDF)</button>
    </div>

    <!-- Report Header -->
    <div class="report-header">
        <div class="header-title">
            <h1>تقرير حصر كميات الخرسانات والحديد للأعمدة (Columns Takeoff Sheet)</h1>
            <span class="code-badge">الكود المصري لتصميم وتنفيذ المنشآت الخرسانية ECP 203-2018</span>
        </div>
        <div class="header-meta">
            <div><b>المشروع:</b> {project_name}</div>
            <div><b>تاريخ الحصر:</b> {now_str}</div>
            <div><b>حالة الدور:</b> {top_floor_str}</div>
        </div>
    </div>

    <!-- Section 1 -->
    {section1_html}

    {drawings_html}

    <!-- Section 3: Takeoff Breakdown Table -->
    <div class="section-title">3. جدول حصر وتفريد حديد التسليح والخرسانة (Detailed Takeoff Breakdown)</div>
    {takeoff_table_html}

    <!-- Section 4: Concrete Mix Materials -->
    <div class="section-title">4. تقدير كميات مواد الخلطة الخرسانية للأعمدة (Concrete Mix Estimation)</div>
    <div class="info-grid">
        <div class="info-card">
            <div class="card-lbl">الأسمنت (350 kg/m³)</div>
            <div class="card-val"><span dir="ltr">{cement_tons:.2f} Ton</span> ({cement_bags} شكارة)</div>
        </div>
        <div class="info-card">
            <div class="card-lbl">الرمل النظيف (0.40 m³/m³)</div>
            <div class="card-val"><span dir="ltr">{sand_m3:.2f} m³</span></div>
        </div>
        <div class="info-card">
            <div class="card-lbl">السن / الزلط (0.80 m³/m³)</div>
            <div class="card-val"><span dir="ltr">{gravel_m3:.2f} m³</span></div>
        </div>
        <div class="info-card">
            <div class="card-lbl">مياه الخلط الصالحة (W/C=0.50)</div>
            <div class="card-val"><span dir="ltr">{water_liters:.0f} L</span> (<span dir="ltr">{water_liters/1000:.2f} m³</span>)</div>
        </div>
    </div>


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

