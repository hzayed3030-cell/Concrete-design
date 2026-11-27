"""
Module 15 — Agreement & Work Order (W.O) Engine
================================================
Automated Excel-to-JSON Sync with MD5 Change Detection, Smart Search & Cart,
Work Order Generation Form, Professional RTL Excel Export (openpyxl),
and Persistent Work Order History Log.
"""

from __future__ import annotations

import datetime
import hashlib
import html
import io
import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from modules.iframe_helper import render_html_iframe
try:
    from modules.settings import play_warning_sound
except Exception:
    def play_warning_sound(force: bool = False) -> None:  # type: ignore
        return None


# ═════════════════════════════════════════════════════════════════════════════
# File Paths & Constants
# ═════════════════════════════════════════════════════════════════════════════

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")

DEFAULT_EXCEL_PATH = os.path.join(_DATA_DIR, "agreement_m15.xlsx")
JSON_CACHE_PATH = os.path.join(_DATA_DIR, "agreement_m15.json")
HASH_FILE_PATH = os.path.join(_DATA_DIR, "agreement_m15.hash")
WO_HISTORY_PATH = os.path.join(_DATA_DIR, "wo_history_m15.json")

CANONICAL_COLS = ["Item_Code", "Description", "Unit", "Unit_Price"]

_COL_SYNONYMS: Dict[str, List[str]] = {
    "Item_Code": [
        "#", "item no.", "item no", "item_no", "item_code", "item code", "code", "no", "no.", "id",
        "رقم البند", "كود البند", "الكود", "الرقم", "بند", "م", "رقم",
    ],
    "Description": [
        "description", "desc", "item_description", "item description", "item_name",
        "item name", "item", "work item", "details", "specification",
        "التوصيف", "توصيف البند", "بيان الأعمال", "بيان الاعمال", "الوصف",
        "اسم البند", "البند", "وصف البند", "توصيف",
    ],
    "Unit": [
        "unit", "uom", "measure", "unit of measure",
        "الوحدة", "وحده", "وحدة القياس", "وحدة",
    ],
    "Unit_Price": [
        "unit_price", "unit price", "price", "price (egp)", "rate", "unit_rate",
        "unit rate", "cost", "egp", "material & labor", "labor only",
        "supply & apply", "manpower",
        "سعر الوحدة", "الفئة", "السعر", "فئة البند", "تكلفة الوحدة", "سعر",
    ],
}

_HEADER_CORRECTIONS: Dict[str, str] = {
    "#": "Item No.",
    "heli": "Description",
    "material & labor egp": "Supply & Apply",
    "material & labor": "Supply & Apply",
    "labor only egp": "Manpower",
    "labor only": "Manpower",
}

_HEADER_HINT_TOKENS = {
    "#", "no", "no.", "code", "item", "description", "desc", "unit", "uom",
    "price", "egp", "rate", "cost", "material", "labor", "qty", "quantity",
    "رقم", "كود", "بند", "توصيف", "وصف", "بيان", "وحدة", "الوحدة", "سعر", "فئة", "الفئة",
}


def _ensure_data_dir() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


def _compute_file_md5(file_path: str) -> str:
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _clean_cell_str(val: Any) -> str:
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    s = str(val).strip()
    if s.lower() in ("nan", "none", "nat"):
        return ""
    return s


def _clean_item_code(val: Any) -> str:
    s = _clean_cell_str(val)
    if re.fullmatch(r"\d+\.0+", s):
        return s.split(".")[0]
    return s


def _clean_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
    except Exception:
        pass
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("ج.م", "").replace("EGP", "").strip()
    if not s:
        return default
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def _is_pure_number(val: Any) -> bool:
    if val is None or isinstance(val, bool):
        return False
    if isinstance(val, (int, float)):
        try:
            return not pd.isna(val)
        except Exception:
            return True
    s = str(val).strip().replace(",", "").replace("ج.م", "").replace("EGP", "").strip()
    if not s:
        return False
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _get_excel_sheet_info(excel_path: str) -> Tuple[List[Tuple[str, str]], str]:
    """
    Inspect workbook sheets and return:
    - list of (sheet_name, display_label)
    - active_sheet_name (workbook's active sheet, fallback to first sheet)
    """
    if not excel_path or not os.path.exists(excel_path):
        return [], ""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
        sheet_names = list(wb.sheetnames)
        active_name = wb.active.title if wb.active is not None else (sheet_names[0] if sheet_names else "")
        info: List[Tuple[str, str]] = []
        for sname in sheet_names:
            ws = wb[sname]
            title_hint = ""
            for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=4, values_only=True)):
                non_empty = [_clean_cell_str(v) for v in row if _clean_cell_str(v)]
                if len(non_empty) == 1:
                    title_hint = non_empty[0]
                    break
                if len(non_empty) >= 2:
                    break
            lbl = f"{sname} — {title_hint}" if title_hint else sname
            info.append((sname, lbl))
        wb.close()
        return info, active_name
    except Exception:
        return [], ""


def _resolve_column_roles(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Dynamically identify semantic column roles (code, description, unit, price columns)
    while keeping the DataFrame's EXACT original Excel column headers intact.
    """
    cols = [c for c in df.columns if not str(c).startswith("_") and c not in ("Select", "Req. Quantity", "اختيار", "الكمية المطلوبة")]
    if not cols:
        return {"code_col": None, "desc_col": None, "unit_col": None, "price_cols": [], "numeric_cols": set()}

    norm_map = {c: re.sub(r"\s+", " ", str(c).strip().lower()) for c in cols}

    def _find_by_synonyms(target: str, exclude: set) -> Optional[str]:
        aliases = _COL_SYNONYMS.get(target, [])
        # Exact match first
        for c in cols:
            if c in exclude:
                continue
            if norm_map[c] in aliases:
                return c
        # Substring match fallback
        for c in cols:
            if c in exclude:
                continue
            if any(a in norm_map[c] for a in aliases if len(a) >= 3):
                return c
        return None

    used: set = set()
    code_col = _find_by_synonyms("Item_Code", used)
    if code_col:
        used.add(code_col)

    unit_col = _find_by_synonyms("Unit", used)
    if unit_col:
        used.add(unit_col)

    # Identify all price / numeric columns (excluding code_col and unit_col)
    price_cols: List[str] = []
    numeric_cols: set = set()
    price_aliases = _COL_SYNONYMS.get("Unit_Price", [])
    for c in cols:
        if c in (code_col, unit_col):
            continue
        series = df[c]
        non_empty = [v for v in series.tolist() if _clean_cell_str(v) != ""]
        all_numeric = bool(non_empty) and all(_is_pure_number(v) for v in non_empty)
        if all_numeric:
            numeric_cols.add(c)
        header_is_price = (norm_map[c] in price_aliases) or any(
            a in norm_map[c] for a in price_aliases if len(a) >= 3
        )
        if header_is_price or all_numeric:
            price_cols.append(c)
            used.add(c)

    desc_col = _find_by_synonyms("Description", used)
    if desc_col is None:
        # Fallback: pick remaining text column with longest average text length (e.g. 'heli' in Civil sheet)
        candidates = [c for c in cols if c not in used]
        if candidates:
            desc_col = max(
                candidates,
                key=lambda c: sum(len(_clean_cell_str(v)) for v in df[c].tolist()) / max(1, len(df)),
            )
            used.add(desc_col)

    if code_col is None and cols:
        code_col = cols[0]

    return {
        "code_col": code_col,
        "desc_col": desc_col,
        "unit_col": unit_col,
        "price_cols": price_cols,
        "numeric_cols": numeric_cols,
    }


def _read_excel_sheet_exact(
    excel_path: str,
    sheet_name: Optional[str] = None,
) -> Tuple[pd.DataFrame, str]:
    """
    Read an Excel sheet while automatically detecting the real header row,
    dropping completely empty leading/trailing columns & rows, and preserving
    the EXACT column header names from the Excel sheet.
    """
    import openpyxl

    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    sheet_names = list(wb.sheetnames)
    if not sheet_names:
        wb.close()
        return pd.DataFrame(), ""

    if sheet_name and sheet_name in sheet_names:
        target_sheet = sheet_name
    elif wb.active is not None and wb.active.title in sheet_names:
        target_sheet = wb.active.title
    else:
        target_sheet = sheet_names[0]

    ws = wb[target_sheet]
    raw_rows: List[List[Any]] = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    if not raw_rows:
        return pd.DataFrame(), target_sheet

    # Detect header row within the first 20 rows
    hdr_idx: Optional[int] = None
    scan_limit = min(20, len(raw_rows))

    # Pass 1: look for a row with >= 2 non-empty cells that matches header keywords
    for idx in range(scan_limit):
        row = raw_rows[idx]
        non_empty = [_clean_cell_str(v) for v in row if _clean_cell_str(v) != ""]
        if len(non_empty) < 2:
            continue
        lowered_tokens = set()
        for cell_txt in non_empty:
            low = cell_txt.lower()
            lowered_tokens.add(low)
            for tok in re.split(r"[\s()/\-&]+", low):
                if tok:
                    lowered_tokens.add(tok)
        if lowered_tokens & _HEADER_HINT_TOKENS:
            hdr_idx = idx
            break

    # Pass 2: fallback to first row with >= 2 non-empty mostly-text cells
    if hdr_idx is None:
        for idx in range(scan_limit):
            row = raw_rows[idx]
            non_empty = [v for v in row if _clean_cell_str(v) != ""]
            if len(non_empty) >= 2:
                text_cnt = sum(1 for v in non_empty if not _is_pure_number(v))
                if text_cnt >= max(1, len(non_empty) // 2):
                    hdr_idx = idx
                    break

    # Pass 3: fallback to first non-empty row
    if hdr_idx is None:
        for idx in range(len(raw_rows)):
            if any(_clean_cell_str(v) != "" for v in raw_rows[idx]):
                hdr_idx = idx
                break

    if hdr_idx is None:
        return pd.DataFrame(), target_sheet

    hdr_row = raw_rows[hdr_idx]
    data_rows = raw_rows[hdr_idx + 1:]

    max_cols = max([len(hdr_row)] + [len(r) for r in data_rows] if data_rows else [len(hdr_row)])

    # Keep only columns that have a non-empty header OR non-empty data
    active_col_indices: List[int] = []
    for c_idx in range(max_cols):
        h_val = _clean_cell_str(hdr_row[c_idx]) if c_idx < len(hdr_row) else ""
        has_data = any(
            (c_idx < len(r) and _clean_cell_str(r[c_idx]) != "")
            for r in data_rows
        )
        if h_val or has_data:
            active_col_indices.append(c_idx)

    if not active_col_indices:
        return pd.DataFrame(), target_sheet

    # Build exact unique header names (applying explicit header corrections)
    exact_headers: List[str] = []
    seen_headers: Dict[str, int] = {}
    for pos, c_idx in enumerate(active_col_indices, start=1):
        raw_h = _clean_cell_str(hdr_row[c_idx]) if c_idx < len(hdr_row) else ""
        base_h = raw_h if raw_h else f"Col_{pos}"
        corr = _HEADER_CORRECTIONS.get(base_h.strip().lower())
        if corr:
            base_h = corr
        if base_h in ("Select", "Req. Quantity", "اختيار", "الكمية المطلوبة", "_row_key"):
            base_h = f"{base_h} (Excel)"
        cnt = seen_headers.get(base_h, 0) + 1
        seen_headers[base_h] = cnt
        exact_headers.append(base_h if cnt == 1 else f"{base_h} ({cnt})")

    # Build cleaned records (dropping completely empty rows, preserving EXACT Excel row order)
    records: List[Dict[str, Any]] = []
    for r in data_rows:
        row_vals = [r[c_idx] if c_idx < len(r) else None for c_idx in active_col_indices]
        if not any(_clean_cell_str(v) != "" for v in row_vals):
            continue
        records.append(dict(zip(exact_headers, row_vals)))

    df = pd.DataFrame(records, columns=exact_headers)
    return _clean_exact_dataframe(df), target_sheet


def _clean_exact_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean cell values while preserving the DataFrame's EXACT Excel column names and row order.
    """
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=list(raw_df.columns) if raw_df is not None else [])

    df = raw_df.copy()
    # Apply explicit header corrections even when loading from an older cache
    renamed_cols = []
    seen_c: Dict[str, int] = {}
    for col in df.columns:
        base_h = str(col).strip()
        corr = _HEADER_CORRECTIONS.get(base_h.lower())
        if corr:
            base_h = corr
        cnt = seen_c.get(base_h, 0) + 1
        seen_c[base_h] = cnt
        renamed_cols.append(base_h if cnt == 1 else f"{base_h} ({cnt})")
    df.columns = renamed_cols

    df = df.dropna(how="all").reset_index(drop=True)
    if df.empty:
        return df

    roles = _resolve_column_roles(df)
    code_col = roles["code_col"]
    numeric_cols = roles["numeric_cols"]

    for col in df.columns:
        if col == code_col:
            df[col] = df[col].apply(_clean_item_code)
        elif col in numeric_cols:
            def _to_num_or_none(v: Any) -> Optional[float]:
                if _clean_cell_str(v) == "":
                    return None
                return round(_clean_float(v, 0.0), 2)
            df[col] = df[col].apply(_to_num_or_none)
        else:
            df[col] = df[col].apply(_clean_cell_str)

    return df


def _build_unique_key_map(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Build an ordered key -> row dict map keyed by the detected code column (e.g. 'Item No.'),
    preserving exact Excel sheet row order.
    """
    key_map: Dict[str, Dict[str, Any]] = {}
    seen_counts: Dict[str, int] = {}
    roles = _resolve_column_roles(df)
    code_col = roles["code_col"]

    for idx, row in df.iterrows():
        raw_code = _clean_cell_str(row.get(code_col, "")) if code_col else ""
        base_key = raw_code if raw_code else f"ROW_{idx + 1}"
        count = seen_counts.get(base_key, 0) + 1
        seen_counts[base_key] = count
        unique_key = base_key if count == 1 else f"{base_key} (#{count})"
        row_dict = {col: row[col] for col in df.columns}
        row_dict["_display_code"] = unique_key
        key_map[unique_key] = row_dict
    return key_map


def diff_agreement_data(old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare old agreement DataFrame against new agreement DataFrame using the detected
    code column as unique key (with graceful duplicate/missing code fallback).
    Returns English-only changelog DataFrame with exact Excel column names.
    """
    changelog_cols = [
        "Change Type",
        "Item No.",
        "Modified Column",
        "Old Value",
        "New Value",
    ]
    if old_df is None or old_df.empty:
        return pd.DataFrame(columns=changelog_cols)

    old_roles = _resolve_column_roles(old_df)
    new_roles = _resolve_column_roles(new_df)
    old_map = _build_unique_key_map(old_df)
    new_map = _build_unique_key_map(new_df)
    all_cols = list(dict.fromkeys(list(old_df.columns) + list(new_df.columns)))
    numeric_cols = old_roles["numeric_cols"] | new_roles["numeric_cols"]

    changes: List[Dict[str, str]] = []

    def _row_preview(r_dict: Dict[str, Any], roles: Dict[str, Any]) -> str:
        d_col = roles.get("desc_col")
        p_cols = roles.get("price_cols") or []
        desc_preview = _clean_cell_str(r_dict.get(d_col, ""))[:90] if d_col else ""
        if p_cols:
            p_val = _clean_float(r_dict.get(p_cols[0], 0.0))
            return f"{desc_preview} | {p_cols[0]}: {p_val:,.2f}"
        return desc_preview or "—"

    # Added items
    for key, new_row in new_map.items():
        if key not in old_map:
            changes.append({
                "Change Type": "➕ Added Item",
                "Item No.": key,
                "Modified Column": "Full Row",
                "Old Value": "—",
                "New Value": _row_preview(new_row, new_roles),
            })

    # Deleted items
    for key, old_row in old_map.items():
        if key not in new_map:
            changes.append({
                "Change Type": "❌ Deleted Item",
                "Item No.": key,
                "Modified Column": "Full Row",
                "Old Value": _row_preview(old_row, old_roles),
                "New Value": "—",
            })

    # Modified cells
    for key, new_row in new_map.items():
        if key not in old_map:
            continue
        old_row = old_map[key]
        for col in all_cols:
            if str(col).startswith("_"):
                continue
            old_v = old_row.get(col, "")
            new_v = new_row.get(col, "")
            if col in numeric_cols:
                s_old_empty = _clean_cell_str(old_v) == ""
                s_new_empty = _clean_cell_str(new_v) == ""
                if s_old_empty and s_new_empty:
                    continue
                f_old = round(_clean_float(old_v, 0.0), 2)
                f_new = round(_clean_float(new_v, 0.0), 2)
                if (s_old_empty != s_new_empty) or abs(f_old - f_new) > 1e-4:
                    changes.append({
                        "Change Type": "✏️ Modified",
                        "Item No.": key,
                        "Modified Column": str(col),
                        "Old Value": "—" if s_old_empty else f"{f_old:,.2f}",
                        "New Value": "—" if s_new_empty else f"{f_new:,.2f}",
                    })
            else:
                s_old = _clean_cell_str(old_v)
                s_new = _clean_cell_str(new_v)
                if s_old != s_new:
                    changes.append({
                        "Change Type": "✏️ Modified",
                        "Item No.": key,
                        "Modified Column": str(col),
                        "Old Value": s_old or "—",
                        "New Value": s_new or "—",
                    })

    return pd.DataFrame(changes, columns=changelog_cols)


def _load_json_cache() -> Tuple[pd.DataFrame, str]:
    if not os.path.exists(JSON_CACHE_PATH):
        return pd.DataFrame(), ""
    try:
        with open(JSON_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "rows" in data:
            cols = data.get("columns") or []
            rows = data.get("rows") or []
            sheet_name = str(data.get("sheet_name") or "")
            df = pd.DataFrame(rows, columns=cols) if cols else pd.DataFrame(rows)
            return _clean_exact_dataframe(df), sheet_name
        if isinstance(data, list):
            return _clean_exact_dataframe(pd.DataFrame(data)), ""
    except Exception:
        pass
    return pd.DataFrame(), ""


def _save_json_cache(df: pd.DataFrame, sheet_name: str = "") -> None:
    _ensure_data_dir()
    clean_records = []
    for rec in df.to_dict(orient="records"):
        clean_records.append({
            k: (None if (isinstance(v, float) and pd.isna(v)) else v)
            for k, v in rec.items()
        })
    payload = {
        "sheet_name": sheet_name,
        "columns": list(df.columns),
        "rows": clean_records,
    }
    with open(JSON_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _read_saved_hash() -> str:
    if not os.path.exists(HASH_FILE_PATH):
        return ""
    try:
        with open(HASH_FILE_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _write_saved_hash(md5_hex: str) -> None:
    _ensure_data_dir()
    with open(HASH_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(md5_hex.strip())


def sync_agreement_excel(
    excel_path: str = DEFAULT_EXCEL_PATH,
    force: bool = False,
    sheet_name: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str]:
    """
    Synchronize local Excel agreement file with JSON cache using MD5 + sheet change detection.
    Preserves EXACT column headers and row order from the Excel sheet.
    Returns: (agreement_df, changelog_df, status_message, resolved_sheet_name)
    """
    _ensure_data_dir()
    excel_exists = bool(excel_path) and os.path.exists(excel_path)
    cache_exists = os.path.exists(JSON_CACHE_PATH)

    # Fallback when Excel is missing
    if not excel_exists:
        if cache_exists:
            df_cached, cached_sheet = _load_json_cache()
            return (
                df_cached,
                pd.DataFrame(),
                f"📂 Loaded from local JSON Cache ({len(df_cached)} items) — Excel file not found at specified path.",
                cached_sheet,
            )
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            "⚠️ Agreement file `data/agreement_m15.xlsx` and local cache `data/agreement_m15.json` were not found.",
            "",
        )

    sheets_info, active_sheet = _get_excel_sheet_info(excel_path)
    valid_sheet_names = [s[0] for s in sheets_info]
    resolved_sheet = sheet_name if (sheet_name and sheet_name in valid_sheet_names) else active_sheet

    current_sig = f"v3::{_compute_file_md5(excel_path)}::{resolved_sheet}"
    saved_sig = _read_saved_hash()

    # Fast path: no change & cache exists & same sheet
    if (not force) and cache_exists and saved_sig and (current_sig == saved_sig):
        df_cached, cached_sheet = _load_json_cache()
        return (
            df_cached,
            pd.DataFrame(),
            f"⚡ Data is synced & up-to-date ({len(df_cached)} items — Sheet: `{cached_sheet or resolved_sheet}` — instant load from JSON Cache).",
            cached_sheet or resolved_sheet,
        )

    # Read new Excel & diff against existing cache (only if same sheet)
    old_df, old_sheet = _load_json_cache() if cache_exists else (pd.DataFrame(), "")
    try:
        new_df, used_sheet = _read_excel_sheet_exact(excel_path, sheet_name=resolved_sheet)
    except Exception as exc:
        if cache_exists:
            df_cached, cached_sheet = _load_json_cache()
            return (
                df_cached,
                pd.DataFrame(),
                f"⚠️ Failed to read Excel file ({exc}) — loaded fallback from JSON Cache.",
                cached_sheet,
            )
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            f"❌ Failed to read Excel file: {exc}",
            resolved_sheet,
        )

    same_sheet_diff = cache_exists and (not old_df.empty) and (old_sheet == used_sheet) and (list(old_df.columns) == list(new_df.columns))
    changelog_df = diff_agreement_data(old_df, new_df) if same_sheet_diff else pd.DataFrame()

    _save_json_cache(new_df, sheet_name=used_sheet)
    _write_saved_hash(f"v3::{_compute_file_md5(excel_path)}::{used_sheet}")

    if not changelog_df.empty:
        msg = f"🔄 Agreement updated from Excel ({len(new_df)} items — Sheet: `{used_sheet}`) — {len(changelog_df)} change(s) detected."
    else:
        msg = f"✅ Synced successfully from Excel & updated local JSON Cache ({len(new_df)} items — Sheet: `{used_sheet}`)."

    return new_df, changelog_df, msg, used_sheet


# ═════════════════════════════════════════════════════════════════════════════
# Work Order History Persistence
# ═════════════════════════════════════════════════════════════════════════════

def _load_wo_history() -> List[Dict[str, Any]]:
    if not os.path.exists(WO_HISTORY_PATH):
        return []
    try:
        with open(WO_HISTORY_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            return loaded if isinstance(loaded, list) else []
    except Exception:
        return []


def _save_wo_history(history: List[Dict[str, Any]]) -> None:
    _ensure_data_dir()
    with open(WO_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def _suggest_next_wo_number(history: List[Dict[str, Any]]) -> str:
    max_num = 0
    for rec in history:
        wo_no = str(rec.get("wo_number", ""))
        m = re.search(r"(\d+)\s*$", wo_no)
        if m:
            try:
                max_num = max(max_num, int(m.group(1)))
            except ValueError:
                pass
    return f"WO-M15-{max_num + 1:03d}"


# ═════════════════════════════════════════════════════════════════════════════
# Professional RTL Excel Export (openpyxl)
# ═════════════════════════════════════════════════════════════════════════════

def export_wo_to_excel(
    metadata: Dict[str, Any],
    items_df: pd.DataFrame,
) -> bytes:
    """
    Generate a professionally formatted Arabic RTL .xlsx Work Order file using openpyxl.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Work Order"
    ws.views.sheetView[0].rightToLeft = True

    # Styles
    navy_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    sub_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    meta_lbl_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    meta_val_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    zebra_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    total_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    sig_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    title_font = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    hdr_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    meta_lbl_font = Font(name="Calibri", size=11, bold=True, color="0F172A")
    meta_val_font = Font(name="Calibri", size=11, bold=False, color="0F172A")
    body_font = Font(name="Calibri", size=10.5, color="0F172A")
    bold_font = Font(name="Calibri", size=11, bold=True, color="065F46")
    sig_font = Font(name="Calibri", size=10.5, bold=True, color="1E293B")

    thin = Side(border_style="thin", color="94A3B8")
    med = Side(border_style="medium", color="1E3A8A")
    dbl = Side(border_style="double", color="065F46")

    cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_border = Border(left=thin, right=thin, top=med, bottom=med)
    total_border = Border(left=thin, right=thin, top=med, bottom=dbl)

    # Row 1: Title Banner
    ws.merge_cells("A1:G1")
    ws["A1"] = "أمر شغل أعمال المباني والمحارة — WORK ORDER (Module 15)"
    ws["A1"].font = title_font
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 34

    # Metadata Block (Rows 3-6)
    meta_pairs = [
        ("رقم أمر الشغل (W.O No.):", str(metadata.get("wo_number", "")),
         "تاريخ الإصدار (Issue Date):", str(metadata.get("issue_date", ""))),
        ("المشروع / الموقع (Project / Site):", str(metadata.get("project_site", "")),
         "مدة التنفيذ (Duration):", str(metadata.get("duration", "") or "—")),
        ("اسم الشركة / المقاول (Contractor):", str(metadata.get("contractor", "")),
         "عدد البنود (Items Count):", str(len(items_df))),
        ("ملاحظات (Notes):", str(metadata.get("notes", "") or "—"), "", ""),
    ]

    for offset, (l1, v1, l2, v2) in enumerate(meta_pairs, start=3):
        ws.row_dimensions[offset].height = 24
        ws.cell(row=offset, column=1, value=l1).font = meta_lbl_font
        ws.cell(row=offset, column=1).fill = meta_lbl_fill
        ws.cell(row=offset, column=1).alignment = Alignment(horizontal="right", vertical="center")
        ws.cell(row=offset, column=1).border = cell_border

        if l2:
            ws.merge_cells(start_row=offset, start_column=2, end_row=offset, end_column=4)
            ws.cell(row=offset, column=2, value=v1).font = meta_val_font
            ws.cell(row=offset, column=2).fill = meta_val_fill
            ws.cell(row=offset, column=2).alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
            for c_i in range(2, 5):
                ws.cell(row=offset, column=c_i).border = cell_border

            ws.cell(row=offset, column=5, value=l2).font = meta_lbl_font
            ws.cell(row=offset, column=5).fill = meta_lbl_fill
            ws.cell(row=offset, column=5).alignment = Alignment(horizontal="right", vertical="center")
            ws.cell(row=offset, column=5).border = cell_border

            ws.merge_cells(start_row=offset, start_column=6, end_row=offset, end_column=7)
            ws.cell(row=offset, column=6, value=v2).font = meta_val_font
            ws.cell(row=offset, column=6).fill = meta_val_fill
            ws.cell(row=offset, column=6).alignment = Alignment(horizontal="center", vertical="center")
            for c_i in range(6, 8):
                ws.cell(row=offset, column=c_i).border = cell_border
        else:
            ws.merge_cells(start_row=offset, start_column=2, end_row=offset, end_column=7)
            ws.cell(row=offset, column=2, value=v1).font = meta_val_font
            ws.cell(row=offset, column=2).fill = meta_val_fill
            ws.cell(row=offset, column=2).alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
            for c_i in range(2, 8):
                ws.cell(row=offset, column=c_i).border = cell_border

    # Table Header (Row 8)
    hdr_row = 8
    headers = [
        "م",
        "رقم البند\n(Item Code)",
        "توصيف البند\n(Description)",
        "الوحدة\n(Unit)",
        "الكمية المطلوبة\n(W.O Qty)",
        "سعر الوحدة\n(Unit Price)",
        "الإجمالي\n(Total Price)",
    ]
    ws.row_dimensions[hdr_row].height = 32
    for col_idx, text in enumerate(headers, start=1):
        cell = ws.cell(row=hdr_row, column=col_idx, value=text)
        cell.font = hdr_font
        cell.fill = sub_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = hdr_border

    # Table Body
    grand_total = 0.0
    cur_row = hdr_row + 1
    for seq_idx, (_, r) in enumerate(items_df.iterrows(), start=1):
        qty = round(_clean_float(r.get("W.O Qty", 0.0)), 2)
        u_price = round(_clean_float(r.get("Unit_Price", 0.0)), 2)
        tot = round(qty * u_price, 2)
        grand_total += tot

        vals = [
            seq_idx,
            _clean_cell_str(r.get("Item_Code", "")),
            _clean_cell_str(r.get("Description", "")),
            _clean_cell_str(r.get("Unit", "")),
            qty,
            u_price,
            tot,
        ]
        is_even = (seq_idx % 2 == 0)
        for col_idx, val in enumerate(vals, start=1):
            cell = ws.cell(row=cur_row, column=col_idx, value=val)
            cell.font = body_font
            cell.border = cell_border
            if is_even:
                cell.fill = zebra_fill
            if col_idx == 3:
                cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if col_idx in (5, 6, 7):
                cell.number_format = "#,##0.00"

        desc_len = len(str(vals[2]))
        ws.row_dimensions[cur_row].height = max(24, min(90, 18 + (desc_len // 55) * 16))
        cur_row += 1

    # Grand Total Row
    ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=6)
    tot_lbl = ws.cell(row=cur_row, column=1, value="الإجمالي العام لقيمة أمر الشغل (Grand Total Cost — EGP)")
    tot_lbl.font = bold_font
    tot_lbl.alignment = Alignment(horizontal="center", vertical="center")
    for c_i in range(1, 7):
        ws.cell(row=cur_row, column=c_i).fill = total_fill
        ws.cell(row=cur_row, column=c_i).border = total_border

    tot_val = ws.cell(row=cur_row, column=7, value=round(grand_total, 2))
    tot_val.font = bold_font
    tot_val.fill = total_fill
    tot_val.alignment = Alignment(horizontal="center", vertical="center")
    tot_val.number_format = "#,##0.00"
    tot_val.border = total_border
    ws.row_dimensions[cur_row].height = 28

    # Signature Blocks
    sig_row = cur_row + 3
    sigs = [
        (1, 2, "المهندس المختص\n(Site / QS Engineer)"),
        (3, 4, "مدير المشروع\n(Project Manager)"),
        (5, 7, "المقاول / الشركة المنفذة\n(Contractor Approval)"),
    ]
    ws.row_dimensions[sig_row].height = 34
    ws.row_dimensions[sig_row + 1].height = 30
    for c_start, c_end, title in sigs:
        ws.merge_cells(start_row=sig_row, start_column=c_start, end_row=sig_row, end_column=c_end)
        c_hdr = ws.cell(row=sig_row, column=c_start, value=title)
        c_hdr.font = sig_font
        c_hdr.fill = meta_lbl_fill
        c_hdr.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        ws.merge_cells(start_row=sig_row + 1, start_column=c_start, end_row=sig_row + 1, end_column=c_end)
        c_box = ws.cell(row=sig_row + 1, column=c_start, value="الاسم / التوقيع: ___________________")
        c_box.font = body_font
        c_box.fill = sig_fill
        c_box.alignment = Alignment(horizontal="center", vertical="center")

        for r_i in (sig_row, sig_row + 1):
            for c_i in range(c_start, c_end + 1):
                ws.cell(row=r_i, column=c_i).border = cell_border

    # Auto-fit Column Widths with sensible bounds
    col_widths = {1: 8, 2: 18, 3: 54, 4: 14, 5: 16, 6: 16, 7: 18}
    for col_idx, min_w in col_widths.items():
        letter = get_column_letter(col_idx)
        ws.column_dimensions[letter].width = min_w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ═════════════════════════════════════════════════════════════════════════════
# Main UI Section Renderer ("Agreement & W.O")
# ═════════════════════════════════════════════════════════════════════════════

_OPTIONAL_UPLOAD_COLS = {
    "req. quantity", "req quantity", "required quantity", "required quntity",
    "req. qty", "req qty", "estimated cost", "select",
}


def _extract_raw_excel_headers_from_bytes(
    file_bytes: bytes,
    sheet_name: Optional[str] = None,
) -> Tuple[List[str], str]:
    """
    Extract the RAW column headers from an uploaded .xlsx byte buffer (active sheet or specified sheet)
    WITHOUT applying header auto-corrections, so strict validation catches any header mismatch.
    """
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    sheet_names = list(wb.sheetnames)
    if not sheet_names:
        wb.close()
        return [], ""

    if sheet_name and sheet_name in sheet_names:
        target_sheet = sheet_name
    elif wb.active is not None and wb.active.title in sheet_names:
        target_sheet = wb.active.title
    else:
        target_sheet = sheet_names[0]

    ws = wb[target_sheet]
    raw_rows: List[List[Any]] = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    if not raw_rows:
        return [], target_sheet

    hdr_idx: Optional[int] = None
    scan_limit = min(20, len(raw_rows))

    # Pass 1: header keyword match
    for idx in range(scan_limit):
        row = raw_rows[idx]
        non_empty = [_clean_cell_str(v) for v in row if _clean_cell_str(v) != ""]
        if len(non_empty) < 2:
            continue
        lowered_tokens = set()
        for cell_txt in non_empty:
            low = cell_txt.lower()
            lowered_tokens.add(low)
            for tok in re.split(r"[\s()/\-&]+", low):
                if tok:
                    lowered_tokens.add(tok)
        if lowered_tokens & _HEADER_HINT_TOKENS:
            hdr_idx = idx
            break

    # Pass 2: mostly-text row with >= 2 cells
    if hdr_idx is None:
        for idx in range(scan_limit):
            row = raw_rows[idx]
            non_empty = [v for v in row if _clean_cell_str(v) != ""]
            if len(non_empty) >= 2:
                text_cnt = sum(1 for v in non_empty if not _is_pure_number(v))
                if text_cnt >= max(1, len(non_empty) // 2):
                    hdr_idx = idx
                    break

    # Pass 3: first non-empty row
    if hdr_idx is None:
        for idx in range(len(raw_rows)):
            if any(_clean_cell_str(v) != "" for v in raw_rows[idx]):
                hdr_idx = idx
                break

    if hdr_idx is None:
        return [], target_sheet

    hdr_row = raw_rows[hdr_idx]
    data_rows = raw_rows[hdr_idx + 1:]
    max_cols = max([len(hdr_row)] + [len(r) for r in data_rows] if data_rows else [len(hdr_row)])

    raw_headers: List[str] = []
    for c_idx in range(max_cols):
        h_val = _clean_cell_str(hdr_row[c_idx]) if c_idx < len(hdr_row) else ""
        has_data = any(
            (c_idx < len(r) and _clean_cell_str(r[c_idx]) != "")
            for r in data_rows
        )
        if h_val or has_data:
            raw_headers.append(h_val if h_val else f"(Empty Col {c_idx + 1})")

    return raw_headers, target_sheet


def _validate_uploaded_excel_headers(
    file_bytes: bytes,
    expected_cols: List[str],
    sheet_name: Optional[str] = None,
) -> Tuple[bool, List[str], List[str], str]:
    """
    Strictly validate that the uploaded Excel sheet's column headers match `expected_cols`
    in exact spelling and exact order. Optional UI columns ('Req. Quantity', 'Estimated cost', 'Select')
    are allowed to be omitted (or ignored if present).
    Returns: (is_valid, raw_headers_found, diff_messages, used_sheet_name)
    """
    raw_headers, used_sheet = _extract_raw_excel_headers_from_bytes(file_bytes, sheet_name=sheet_name)
    if not raw_headers:
        return False, [], ["The uploaded Excel sheet appears to be empty or has no recognizable header row."], used_sheet

    core_uploaded = [
        h for h in raw_headers
        if h.strip().lower() not in _OPTIONAL_UPLOAD_COLS
    ]
    exp_list = list(expected_cols)

    if core_uploaded == exp_list:
        return True, raw_headers, [], used_sheet

    diffs: List[str] = []
    if set(core_uploaded) == set(exp_list) and len(core_uploaded) == len(exp_list):
        diffs.append("Column names exist, but their ORDER does not match the current table.")

    max_len = max(len(exp_list), len(core_uploaded))
    for i in range(max_len):
        exp_h = exp_list[i] if i < len(exp_list) else None
        got_h = core_uploaded[i] if i < len(core_uploaded) else None
        if exp_h is not None and got_h is not None:
            if exp_h != got_h:
                diffs.append(f'Column {i + 1}: Expected "{exp_h}" — Found "{got_h}"')
        elif exp_h is not None:
            diffs.append(f'Column {i + 1}: Missing required column "{exp_h}"')
        elif got_h is not None:
            diffs.append(f'Column {i + 1}: Unexpected extra column "{got_h}"')

    return False, raw_headers, diffs, used_sheet


def _render_upload_error_modal(
    expected_cols: List[str],
    found_cols: List[str],
    diffs: List[str],
    filename: str,
    sheet_name: str,
) -> None:
    """Render a centered red warning modal in the parent viewport explaining header mismatches."""
    exp_json = json.dumps(expected_cols, ensure_ascii=False)
    found_json = json.dumps(found_cols, ensure_ascii=False)
    diffs_json = json.dumps(diffs, ensure_ascii=False)
    fname_json = json.dumps(str(filename or ""), ensure_ascii=False)
    sname_json = json.dumps(str(sheet_name or ""), ensure_ascii=False)

    modal_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><script>
    (function() {{
      try {{
        var pDoc = (window.parent && window.parent.document) ? window.parent.document : document;
        var MODAL_ID = 'm15-agr-upload-err-modal';
        var old = pDoc.getElementById(MODAL_ID);
        if (old) old.remove();

        var expectedCols = {exp_json};
        var foundCols = {found_json};
        var diffs = {diffs_json};
        var fileName = {fname_json};
        var sheetName = {sname_json};

        var backdrop = pDoc.createElement('div');
        backdrop.id = MODAL_ID;
        backdrop.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,0.62);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:16px;font-family:Segoe UI,Tahoma,sans-serif;direction:ltr;';

        var card = pDoc.createElement('div');
        card.style.cssText = 'background:linear-gradient(145deg,#7f1d1d 0%,#450a0a 100%);border:2.5px solid #ef4444;border-radius:14px;max-width:650px;width:94%;color:#fef2f2;box-shadow:0 22px 60px rgba(239,68,68,0.48),0 0 0 1px rgba(254,202,202,0.22);overflow:hidden;';

        var hdr = pDoc.createElement('div');
        hdr.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:14px 20px;background:rgba(153,27,27,0.75);border-bottom:1.5px solid rgba(248,113,113,0.45);';
        var title = pDoc.createElement('div');
        title.style.cssText = 'font-size:16.5px;font-weight:900;color:#fecaca;letter-spacing:0.01em;';
        title.textContent = '⚠️ Excel Column Headers Mismatch — Upload Rejected';
        var closeX = pDoc.createElement('button');
        closeX.type = 'button';
        closeX.textContent = '✕';
        closeX.style.cssText = 'background:rgba(239,68,68,0.28);border:1.5px solid #f87171;color:#ffffff;border-radius:7px;width:30px;height:30px;font-size:15px;font-weight:900;cursor:pointer;';
        hdr.appendChild(title);
        hdr.appendChild(closeX);

        var body = pDoc.createElement('div');
        body.style.cssText = 'padding:16px 20px;font-size:14.5px;line-height:1.55;max-height:70vh;overflow-y:auto;';

        var meta = pDoc.createElement('div');
        meta.style.cssText = 'margin-bottom:12px;color:#fecaca;font-size:13.5px;font-weight:700;';
        meta.textContent = 'File: ' + fileName + (sheetName ? ('  |  Sheet: ' + sheetName) : '');
        body.appendChild(meta);

        function makeRow(lblText, items, badgeBg, badgeBdr, badgeClr) {{
          var wrap = pDoc.createElement('div');
          wrap.style.cssText = 'margin-bottom:10px;padding:9px 12px;border-radius:8px;background:rgba(0,0,0,0.28);border:1px solid rgba(248,113,113,0.32);';
          var lbl = pDoc.createElement('div');
          lbl.style.cssText = 'font-size:13px;font-weight:800;color:#fca5a5;margin-bottom:6px;';
          lbl.textContent = lblText;
          wrap.appendChild(lbl);
          var list = pDoc.createElement('div');
          list.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;';
          if (!items.length) {{
            var em = pDoc.createElement('span');
            em.style.cssText = 'font-size:13px;color:#cbd5e1;font-style:italic;';
            em.textContent = '(None found)';
            list.appendChild(em);
          }} else {{
            items.forEach(function(it, idx) {{
              var b = pDoc.createElement('span');
              b.style.cssText = 'padding:3px 9px;border-radius:6px;font-size:13px;font-weight:800;background:' + badgeBg + ';border:1px solid ' + badgeBdr + ';color:' + badgeClr + ';';
              b.textContent = (idx + 1) + '. ' + it;
              list.appendChild(b);
            }});
          }}
          wrap.appendChild(list);
          return wrap;
        }}

        body.appendChild(makeRow('Expected Column Headers (Exact Order):', expectedCols, 'rgba(16,185,129,0.22)', '#34d399', '#a7f3d0'));
        body.appendChild(makeRow('Uploaded Excel Column Headers:', foundCols, 'rgba(239,68,68,0.26)', '#f87171', '#fee2e2'));

        var diffBox = pDoc.createElement('div');
        diffBox.style.cssText = 'margin-top:10px;padding:10px 14px;border-radius:8px;background:rgba(0,0,0,0.35);border-left:4px solid #f87171;';
        var diffTitle = pDoc.createElement('div');
        diffTitle.style.cssText = 'font-size:14px;font-weight:900;color:#fde047;margin-bottom:6px;';
        diffTitle.textContent = 'Detected Differences:';
        diffBox.appendChild(diffTitle);
        var ul = pDoc.createElement('ul');
        ul.style.cssText = 'margin:0;padding-left:18px;font-size:14px;font-weight:700;color:#ffffff;';
        diffs.forEach(function(d) {{
          var li = pDoc.createElement('li');
          li.style.cssText = 'margin-bottom:4px;';
          li.textContent = d;
          ul.appendChild(li);
        }});
        diffBox.appendChild(ul);
        body.appendChild(diffBox);

        var note = pDoc.createElement('div');
        note.style.cssText = 'margin-top:12px;font-size:13.5px;font-weight:700;color:#fed7aa;';
        note.textContent = 'Please update the Excel file column headers and order to match the current table, then upload again. (Optional columns "Req. Quantity" and "Estimated cost" do not need to be present in the Excel file.)';
        body.appendChild(note);

        var footer = pDoc.createElement('div');
        footer.style.cssText = 'padding:12px 20px;background:rgba(0,0,0,0.25);border-top:1px solid rgba(248,113,113,0.30);display:flex;justify-content:flex-end;';
        var okBtn = pDoc.createElement('button');
        okBtn.type = 'button';
        okBtn.textContent = 'OK — I Will Fix the Excel File';
        okBtn.style.cssText = 'padding:8px 20px;border-radius:8px;border:1.5px solid #fca5a5;background:#dc2626;color:#ffffff;font-size:14.5px;font-weight:900;cursor:pointer;';
        footer.appendChild(okBtn);

        function closeModal() {{
          try {{ pDoc.removeEventListener('keydown', onKey); }} catch(e) {{}}
          try {{ backdrop.remove(); }} catch(e) {{}}
        }}
        function onKey(ev) {{ if (ev.key === 'Escape') closeModal(); }}

        closeX.addEventListener('click', closeModal);
        okBtn.addEventListener('click', closeModal);
        backdrop.addEventListener('click', function(ev) {{ if (ev.target === backdrop) closeModal(); }});
        pDoc.addEventListener('keydown', onKey);

        card.appendChild(hdr);
        card.appendChild(body);
        card.appendChild(footer);
        backdrop.appendChild(card);
        pDoc.body.appendChild(backdrop);
      }} catch (e) {{}}
    }})();
    </script></body></html>"""
    render_html_iframe(modal_html, height=1, hidden=True)


def _render_upload_success_toast(filename: str, rows_count: int, sheet_name: str) -> None:
    """Render a centered green success panel for exactly 3 seconds in the parent viewport."""
    fname_json = json.dumps(str(filename or ""), ensure_ascii=False)
    sname_json = json.dumps(str(sheet_name or ""), ensure_ascii=False)

    toast_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><script>
    (function() {{
      try {{
        var pDoc = (window.parent && window.parent.document) ? window.parent.document : document;
        var TOAST_ID = 'm15-agr-upload-ok-toast';
        var old = pDoc.getElementById(TOAST_ID);
        if (old) old.remove();

        var fileName = {fname_json};
        var sheetName = {sname_json};

        var box = pDoc.createElement('div');
        box.id = TOAST_ID;
        box.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:999999;background:linear-gradient(145deg,#065f46 0%,#064e3b 100%);border:2.5px solid #10b981;border-radius:14px;padding:20px 30px;min-width:340px;max-width:560px;text-align:center;color:#ecfdf5;font-family:Segoe UI,Tahoma,sans-serif;direction:ltr;box-shadow:0 20px 55px rgba(16,185,129,0.48),0 0 0 1px rgba(167,243,208,0.25);transition:opacity 0.35s ease;';

        var title = pDoc.createElement('div');
        title.style.cssText = 'font-size:17px;font-weight:900;color:#6ee7b7;margin-bottom:6px;';
        title.textContent = '✅ Excel File Uploaded & Synced Successfully!';

        var sub = pDoc.createElement('div');
        sub.style.cssText = 'font-size:14px;font-weight:700;color:#d1fae5;';
        sub.textContent = 'File: ' + fileName + (sheetName ? ('  |  Sheet: ' + sheetName) : '') + '  |  Items: {int(rows_count)}';

        box.appendChild(title);
        box.appendChild(sub);
        pDoc.body.appendChild(box);

        setTimeout(function() {{
          try {{
            box.style.opacity = '0';
            setTimeout(function() {{ try {{ box.remove(); }} catch(e) {{}} }}, 360);
          }} catch(e) {{}}
        }}, 3000);
      }} catch (e) {{}}
    }})();
    </script></body></html>"""
    render_html_iframe(toast_html, height=1, hidden=True)


def _process_m15_agr_cart_sync() -> None:
    """Process incoming JSON cart updates dispatched from the resizable Agreement table iframe."""
    raw = str(st.session_state.get("m15_agr_cart_sync_payload", "") or "").strip()
    if not raw:
        return
    try:
        payload = json.loads(raw)
        updates = payload.get("updates") if isinstance(payload, dict) else None
        if isinstance(updates, dict):
            cart: Dict[str, Dict[str, Any]] = dict(st.session_state.get("m15_agr_cart", {}))
            lookup: Dict[str, Dict[str, Any]] = st.session_state.get("m15_agr_row_lookup", {})
            for rk, info in updates.items():
                if not isinstance(info, dict):
                    continue
                sel_price_col = str(info.get("selected_price_col") or "").strip()
                qty_val = round(_clean_float(info.get("qty", 0.0), 0.0), 2)
                if sel_price_col:
                    base_item = lookup.get(rk, cart.get(rk, {}))
                    prices_map = base_item.get("prices", {}) if isinstance(base_item, dict) else {}
                    u_price = round(_clean_float(prices_map.get(sel_price_col, base_item.get("Unit_Price", 0.0)), 0.0), 2)
                    cart[rk] = {
                        "Item_Code": _clean_cell_str(base_item.get("Item_Code", rk)),
                        "Description": _clean_cell_str(base_item.get("Description", "")),
                        "Unit": _clean_cell_str(base_item.get("Unit", "")),
                        "Unit_Price": u_price,
                        "selected_price_col": sel_price_col,
                        "qty": qty_val,
                    }
                else:
                    cart.pop(rk, None)
            st.session_state["m15_agr_cart"] = cart
    except Exception:
        pass
    finally:
        st.session_state["m15_agr_cart_sync_payload"] = ""


def _build_agreement_resizable_table_html(
    filtered_df: pd.DataFrame,
    excel_cols: List[str],
    code_col: Optional[str],
    desc_col: Optional[str],
    unit_col: Optional[str],
    price_cols: List[str],
    numeric_cols: set,
    cart: Dict[str, Dict[str, Any]],
    sheet_sig: str,
) -> str:
    """
    Build an LTR, English-only, non-sortable HTML table inside iframe with:
    - Exact BOQ-style orange & blue headers matching Module 15 BOQ & Cost table
    - Mouse-drag column width resizing (⟷) persisted in localStorage
    - Mouse-drag row height resizing (↕) persisted in localStorage
    - Dedicated mutually-exclusive 'Select' column right next to each price column
      (styled in the same color as Material & Labor EGP)
    - 'Req. Quantity' and 'Estimated cost' columns at the end of the table
    """
    # Build ordered column specs:
    # 'Req. Quantity' is placed right after 'Unit' (or right before the first price column if no Unit col).
    # Each price column is immediately followed by its own 'Select' column.
    # At the end of the table: 'Estimated cost'.
    col_specs: List[Dict[str, Any]] = []
    qty_inserted = False
    for c in excel_cols:
        if c in price_cols:
            if not qty_inserted:
                col_specs.append({"kind": "qty", "name": "Req. Quantity", "label": "Req. Quantity"})
                qty_inserted = True
            col_specs.append({"kind": "price", "name": c, "label": c})
            col_specs.append({"kind": "select", "name": f"__sel__{c}", "label": "Select", "price_col": c})
        elif c == code_col:
            col_specs.append({"kind": "code", "name": c, "label": c})
        elif c == desc_col:
            col_specs.append({"kind": "desc", "name": c, "label": c})
        elif c == unit_col:
            col_specs.append({"kind": "unit", "name": c, "label": c})
            if not qty_inserted:
                col_specs.append({"kind": "qty", "name": "Req. Quantity", "label": "Req. Quantity"})
                qty_inserted = True
        else:
            col_specs.append({"kind": "other", "name": c, "label": c})

    if not qty_inserted:
        col_specs.append({"kind": "qty", "name": "Req. Quantity", "label": "Req. Quantity"})
    col_specs.append({"kind": "est_cost", "name": "Estimated cost", "label": "Estimated cost"})

    n_cols = len(col_specs)

    # Default proportional column weights & minimum pixel widths
    col_weights: List[float] = []
    min_widths: List[int] = []
    for spec in col_specs:
        k = spec["kind"]
        if k == "code":
            col_weights.append(0.80)
            min_widths.append(54)
        elif k == "desc":
            col_weights.append(3.55)
            min_widths.append(135)
        elif k == "unit":
            col_weights.append(0.60)
            min_widths.append(46)
        elif k == "price":
            col_weights.append(1.10)
            min_widths.append(72)
        elif k == "select":
            col_weights.append(0.56)
            min_widths.append(46)
        elif k == "qty":
            col_weights.append(1.00)
            min_widths.append(80)
        elif k == "est_cost":
            col_weights.append(1.15)
            min_widths.append(85)
        else:
            col_weights.append(0.95)
            min_widths.append(60)

    total_w = sum(col_weights) or 1.0
    default_ratios = [round(w / total_w, 5) for w in col_weights]

    colgroup_html = "".join(
        f'<col id="agr-col-{i}" style="width: {(w / total_w) * 100.0:.2f}%;">'
        for i, w in enumerate(col_weights)
    )

    # Build <thead> cells (Orange panels + Blue panel for Description)
    # Add prominent vertical dividers after 'Req. Quantity' (before first price col),
    # between consecutive (Price + Select) groups, and after the last 'Select' (before 'Estimated cost')
    th_parts: List[str] = []
    for i, spec in enumerate(col_specs):
        th_cls = "agr-th agr-th-blue" if spec["kind"] == "desc" else "agr-th agr-th-orange"
        if spec["kind"] in ("qty", "select") and (i + 1 < n_cols) and col_specs[i + 1]["kind"] in ("price", "est_cost"):
            th_cls += " price-group-divider-r"
        col_resizer_html = (
            f'<div class="col-resizer" data-col="{i}" title="Drag with mouse to resize column width"></div>'
            if i < n_cols - 1 else ""
        )
        th_parts.append(
            f'<th class="{th_cls}">'
            f'<span class="th-main-title">{html.escape(str(spec["label"]))}</span>'
            f'{col_resizer_html}'
            f'<div class="row-resizer" data-row="header" title="Drag with mouse to resize header row height"></div>'
            f'</th>'
        )
    thead_row_html = "".join(th_parts)

    # Build <tbody> rows strictly in Excel sheet order (NO sorting)
    tbody_parts: List[str] = []
    if filtered_df.empty:
        tbody_parts.append(
            f'<tr><td colspan="{n_cols}" style="padding:28px; text-align:center; color:#94a3b8; font-weight:700; font-size:0.88rem;">'
            f'No matching items found.</td></tr>'
        )
    else:
        for row_idx, (_, r) in enumerate(filtered_df.iterrows()):
            rk = str(r["_row_key"])
            rk_esc = html.escape(rk, quote=True)
            code_val = _clean_cell_str(r[code_col]) if code_col else ""
            desc_val = _clean_cell_str(r[desc_col]) if desc_col else ""
            unit_val = _clean_cell_str(r[unit_col]) if unit_col else ""
            all_prices_empty = all(_clean_cell_str(r[pc]) == "" for pc in price_cols) if price_cols else True

            # Excel sub-section banner row (e.g. "Brick Walls", "Insulation & Plastering")
            is_section_banner = (code_val == "") and (unit_val == "") and all_prices_empty and (desc_val != "")
            if is_section_banner:
                tbody_parts.append(
                    f'<tr class="agr-row agr-section-row" data-row-idx="{row_idx}">'
                    f'<td colspan="{n_cols}" class="agr-td agr-section-td">'
                    f'<div class="agr-section-inner">📌 {html.escape(desc_val)}</div>'
                    f'<div class="row-resizer" data-row="{row_idx}" title="Drag with mouse to resize row height"></div>'
                    f'</td></tr>'
                )
                continue

            in_cart = rk in cart
            cur_qty = round(_clean_float(cart[rk]["qty"], 0.0), 2) if in_cart else 0.0
            cur_sel_pcol = str(cart[rk].get("selected_price_col") or "") if in_cart else ""
            if in_cart and not cur_sel_pcol and price_cols:
                cur_sel_pcol = price_cols[0]

            # Calculate initial Estimated cost
            sel_price_val = round(_clean_float(r[cur_sel_pcol], 0.0), 2) if (cur_sel_pcol and cur_sel_pcol in r) else 0.0
            est_cost_val = round(cur_qty * sel_price_val, 2) if (cur_sel_pcol and cur_qty > 0) else 0.0
            est_cost_str = f"{est_cost_val:,.2f}" if est_cost_val > 0 else "0.00"

            qty_str = f"{cur_qty:.2f}" if cur_qty > 0 else "0"
            zebra_cls = "agr-even-row" if (row_idx % 2 == 0) else "agr-odd-row"
            sel_cls = " agr-row-selected" if bool(cur_sel_pcol) else ""

            tds: List[str] = []
            for col_i, spec in enumerate(col_specs):
                k = spec["kind"]
                if k == "code":
                    tds.append(
                        f'<td class="agr-td cell-code">'
                        f'<div class="cell-center-wrap">{html.escape(_clean_cell_str(r[spec["name"]]) or "—")}</div>'
                        f'<div class="row-resizer" data-row="{row_idx}" title="Drag with mouse to resize row height"></div>'
                        f'</td>'
                    )
                elif k == "desc":
                    tds.append(
                        f'<td class="agr-td cell-desc">'
                        f'<div class="cell-desc-wrap">{html.escape(_clean_cell_str(r[spec["name"]]))}</div>'
                        f'<div class="row-resizer" data-row="{row_idx}" title="Drag with mouse to resize row height"></div>'
                        f'</td>'
                    )
                elif k == "unit":
                    tds.append(
                        f'<td class="agr-td cell-unit">'
                        f'<div class="cell-center-wrap">{html.escape(_clean_cell_str(r[spec["name"]]) or "—")}</div>'
                        f'<div class="row-resizer" data-row="{row_idx}" title="Drag with mouse to resize row height"></div>'
                        f'</td>'
                    )
                elif k == "price":
                    p_raw = r[spec["name"]]
                    num_str = "—" if _clean_cell_str(p_raw) == "" else f"{_clean_float(p_raw, 0.0):,.2f}"
                    tds.append(
                        f'<td class="agr-td cell-price-ml">'
                        f'<div class="cell-center-wrap">{num_str}</div>'
                        f'<div class="row-resizer" data-row="{row_idx}" title="Drag with mouse to resize row height"></div>'
                        f'</td>'
                    )
                elif k == "select":
                    p_col_name = spec["price_col"]
                    p_col_esc = html.escape(p_col_name, quote=True)
                    p_val_num = round(_clean_float(r[p_col_name], 0.0), 2) if p_col_name in r else 0.0
                    chk_attr = " checked" if (cur_sel_pcol == p_col_name) else ""
                    div_cls = " price-group-divider-r" if ((col_i + 1 < n_cols) and col_specs[col_i + 1]["kind"] in ("price", "est_cost")) else ""
                    tds.append(
                        f'<td class="agr-td cell-sel-ml{div_cls}">'
                        f'<div class="cell-center-wrap">'
                        f'<input type="checkbox" class="agr-price-chk" data-rk="{rk_esc}" data-pcol="{p_col_esc}" data-price="{p_val_num:.2f}"{chk_attr} />'
                        f'</div>'
                        f'<div class="row-resizer" data-row="{row_idx}" title="Drag with mouse to resize row height"></div>'
                        f'</td>'
                    )
                elif k == "qty":
                    div_cls = " price-group-divider-r" if ((col_i + 1 < n_cols) and col_specs[col_i + 1]["kind"] in ("price", "est_cost")) else ""
                    tds.append(
                        f'<td class="agr-td cell-qty{div_cls}">'
                        f'<div class="cell-center-wrap">'
                        f'<input type="number" class="agr-qty-input" min="0" step="1" value="{qty_str}" data-rk="{rk_esc}" />'
                        f'</div>'
                        f'<div class="row-resizer" data-row="{row_idx}" title="Drag with mouse to resize row height"></div>'
                        f'</td>'
                    )
                elif k == "est_cost":
                    tds.append(
                        f'<td class="agr-td cell-est-cost">'
                        f'<div class="cell-center-wrap"><span class="agr-est-val" data-rk="{rk_esc}">{est_cost_str}</span></div>'
                        f'<div class="row-resizer" data-row="{row_idx}" title="Drag with mouse to resize row height"></div>'
                        f'</td>'
                    )
                else:
                    tds.append(
                        f'<td class="agr-td cell-unit">'
                        f'<div class="cell-center-wrap">{html.escape(_clean_cell_str(r[spec["name"]]) or "—")}</div>'
                        f'<div class="row-resizer" data-row="{row_idx}" title="Drag with mouse to resize row height"></div>'
                        f'</td>'
                    )

            tbody_parts.append(
                f'<tr class="agr-row {zebra_cls}{sel_cls}" data-row-idx="{row_idx}" data-rk="{rk_esc}">'
                + "".join(tds) +
                f'</tr>'
            )

    tbody_joined = "".join(tbody_parts)
    default_ratios_json = json.dumps(default_ratios)
    min_widths_json = json.dumps(min_widths)
    col_storage_key = f"m15_agr_col_widths_v3_{sheet_sig}_{n_cols}"
    row_storage_key = f"m15_agr_row_heights_v2_{sheet_sig}"

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8" />
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    background: transparent;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #f8fafc;
    direction: ltr;
    overflow: hidden;
  }}
  #agr-root-container {{
    width: 100%;
    direction: ltr;
    padding: 2px 0 4px 0;
  }}

  /* ── Top Banner (Matches Module 15 BOQ Table Banner) ── */
  .agr-top-banner {{
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(30, 41, 59, 0.94) 100%);
    border: 1.5px solid rgba(234, 88, 12, 0.65);
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 8px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
  }}
  .agr-top-flex {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }}
  .agr-title-group {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .agr-main-title {{
    font-size: 0.86rem;
    font-weight: 900;
    color: #fb923c;
  }}
  .agr-sub-badge {{
    font-size: 0.72rem;
    font-weight: 700;
    color: #94a3b8;
  }}
  .agr-actions-group {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }}
  .agr-save-status {{
    display: none;
    align-items: center;
    padding: 3px 9px;
    border-radius: 6px;
    background: rgba(16, 185, 129, 0.20);
    border: 1px solid #10b981;
    color: #6ee7b7;
    font-size: 0.74rem;
    font-weight: 800;
  }}
  .agr-reset-btn {{
    padding: 4px 11px;
    border-radius: 7px;
    border: 1.5px solid rgba(251, 146, 60, 0.65);
    background: rgba(234, 88, 12, 0.18);
    color: #fed7aa;
    font-size: 0.74rem;
    font-weight: 800;
    cursor: pointer;
    transition: all 0.15s ease;
    font-family: inherit;
  }}
  .agr-reset-btn:hover {{
    background: rgba(234, 88, 12, 0.38);
    border-color: #fb923c;
    color: #ffffff;
  }}

  /* ── Unified Table Wrapper (Identical to Module 15 BOQ Table) ── */
  .agr-table-wrapper {{
    width: 100%;
    max-height: 520px;
    border: 2px solid #ea580c;
    border-radius: 10px;
    background: #0f172a;
    box-shadow: 0 8px 26px rgba(0, 0, 0, 0.45);
    overflow-x: hidden;
    overflow-y: auto;
    position: relative;
  }}
  table#m15-agr-table {{
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    table-layout: fixed;
    border-collapse: collapse;
    border-spacing: 0;
    direction: ltr;
    background: #0f172a;
  }}

  /* ── Sticky Orange & Blue Column Header Panels (Identical to BOQ Table) ── */
  thead.agr-thead {{
    position: sticky;
    top: 0;
    z-index: 40;
    background: #0f172a;
  }}
  thead.agr-thead tr.agr-header-row {{
    height: 40px;
  }}
  th.agr-th {{
    position: relative;
    padding: 5px 4px;
    vertical-align: middle;
    text-align: center;
    border-bottom: 2px solid #ea580c;
    user-select: text;
    -webkit-user-select: text;
    cursor: text;
    overflow: visible;
  }}
  th.agr-th .th-main-title,
  .agr-main-title,
  .agr-sub-badge {{
    user-select: text;
    -webkit-user-select: text;
    cursor: text;
  }}
  th.agr-th-orange {{
    background: linear-gradient(180deg, rgba(234, 88, 12, 0.42) 0%, rgba(194, 65, 12, 0.26) 100%);
    border-right: 1.5px solid rgba(251, 146, 60, 0.50);
  }}
  th.agr-th-orange:last-child {{
    border-right: none;
  }}
  th.agr-th-orange .th-main-title {{
    display: block;
    font-size: 0.72rem;
    font-weight: 900;
    color: #fb923c;
    text-shadow: 0 0 8px rgba(251, 146, 60, 0.75), 0 1px 2px #000000;
    line-height: 1.25;
  }}
  th.agr-th-blue {{
    background: linear-gradient(180deg, rgba(2, 132, 199, 0.48) 0%, rgba(14, 165, 233, 0.26) 100%);
    border-right: 1.5px solid rgba(56, 189, 248, 0.45);
    border-bottom: 2px solid #38bdf8;
  }}
  th.agr-th-blue .th-main-title {{
    display: block;
    font-size: 0.72rem;
    font-weight: 900;
    color: #00f5ff;
    text-shadow: 0 0 8px rgba(0, 245, 255, 0.80), 0 1px 2px #000000;
    line-height: 1.25;
  }}

  /* ── Section Banner Rows (e.g. Brick Walls, Insulation & Plastering) ── */
  tr.agr-section-row td.agr-section-td {{
    background: linear-gradient(90deg, rgba(49, 46, 129, 0.94) 0%, rgba(109, 40, 217, 0.82) 50%, rgba(49, 46, 129, 0.94) 100%);
    border-bottom: 2px solid #a78bfa;
    padding: 6px 12px;
  }}
  .agr-section-inner {{
    font-size: 0.78rem;
    font-weight: 900;
    color: #fde047;
    text-shadow: 0 1px 4px rgba(0, 0, 0, 0.85);
    text-align: left;
  }}

  /* ── Data Rows & Cells ── */
  tr.agr-row {{
    transition: background-color 0.12s ease;
    min-height: 32px;
  }}
  tr.agr-even-row {{
    background-color: rgba(15, 23, 42, 0.92);
  }}
  tr.agr-odd-row {{
    background-color: rgba(30, 41, 59, 0.78);
  }}
  tr.agr-row:hover:not(.agr-section-row) {{
    background-color: rgba(51, 65, 85, 0.65);
  }}
  tr.agr-row-selected {{
    background-color: rgba(6, 78, 59, 0.45) !important;
  }}
  td.agr-td {{
    position: relative;
    vertical-align: middle;
    border-bottom: 1px solid rgba(148, 163, 184, 0.20);
    border-right: 1px solid rgba(148, 163, 184, 0.18);
    overflow: visible;
  }}
  td.agr-td:last-child {{
    border-right: none;
  }}
  .cell-center-wrap {{
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    width: 100%;
    height: 100%;
    padding: 4px 4px;
    white-space: normal;
    word-wrap: break-word;
    user-select: text;
  }}
  td.cell-code .cell-center-wrap {{
    font-size: 0.75rem;
    font-weight: 900;
    color: #fbbf24;
  }}
  td.cell-desc {{
    background: rgba(2, 132, 199, 0.04);
  }}
  .cell-desc-wrap {{
    padding: 5px 8px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #f8fafc;
    line-height: 1.4;
    text-align: left;
    white-space: normal;
    word-wrap: break-word;
    overflow-wrap: break-word;
    user-select: text;
  }}
  td.cell-unit .cell-center-wrap {{
    font-size: 0.74rem;
    font-weight: 700;
    color: #e2e8f0;
  }}
  /* Unified Material & Labor EGP color for BOTH price columns AND BOTH adjacent Select columns */
  td.cell-price-ml {{
    background: rgba(56, 189, 248, 0.06);
  }}
  td.cell-price-ml .cell-center-wrap {{
    font-size: 0.75rem;
    font-weight: 900;
    color: #38bdf8;
  }}
  td.cell-sel-ml {{
    background: rgba(56, 189, 248, 0.06);
  }}
  /* Prominent vertical divider line separating (Material & Labor EGP + Select) from (Labor Only EGP + Select) */
  th.agr-th.price-group-divider-r {{
    border-right: 3px solid #f59e0b !important;
    box-shadow: inset -2px 0 0 rgba(251, 191, 36, 0.40);
  }}
  td.agr-td.price-group-divider-r {{
    border-right: 3px solid #f59e0b !important;
    box-shadow: inset -1px 0 0 rgba(251, 191, 36, 0.30);
  }}
  .agr-price-chk {{
    width: 17px;
    height: 17px;
    accent-color: #38bdf8;
    cursor: pointer;
  }}

  /* ── Req. Quantity & Estimated Cost Cells ── */
  .agr-qty-input {{
    width: 92%;
    max-width: 105px;
    padding: 3px 6px;
    border-radius: 5px;
    border: 1.5px solid rgba(148, 163, 184, 0.40);
    background: rgba(15, 23, 42, 0.90);
    color: #ffffff;
    font-size: 0.76rem;
    font-weight: 800;
    text-align: center;
    outline: none;
    transition: border-color 0.15s ease;
  }}
  .agr-qty-input:focus {{
    border-color: #38bdf8;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25);
  }}
  td.cell-est-cost {{
    background: rgba(16, 185, 129, 0.08);
  }}
  td.cell-est-cost .agr-est-val {{
    font-size: 0.78rem;
    font-weight: 900;
    color: #34d399;
    text-shadow: 0 0 6px rgba(16, 185, 129, 0.35);
  }}

  /* ── Mouse Resize Handles (Column Width & Row Height — LTR) ── */
  .col-resizer {{
    position: absolute;
    top: 0;
    bottom: 0;
    right: -5px;
    width: 10px;
    cursor: col-resize;
    z-index: 50;
    background: transparent;
    transition: background-color 0.15s ease;
  }}
  .col-resizer:hover,
  .col-resizer.active-resize {{
    background: rgba(249, 115, 22, 0.85);
    box-shadow: 0 0 8px rgba(249, 115, 22, 0.9);
  }}
  .row-resizer {{
    position: absolute;
    left: 0;
    right: 0;
    bottom: -4px;
    height: 8px;
    cursor: row-resize;
    z-index: 30;
    background: transparent;
    transition: background-color 0.15s ease;
  }}
  .row-resizer:hover,
  .row-resizer.active-resize {{
    background: rgba(56, 189, 248, 0.85);
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.9);
  }}
  body.is-resizing-col,
  body.is-resizing-col * {{
    cursor: col-resize !important;
    user-select: none !important;
  }}
  body.is-resizing-row,
  body.is-resizing-row * {{
    cursor: row-resize !important;
    user-select: none !important;
  }}
</style>
</head>
<body>
<div id="agr-root-container" dir="ltr">
  <div class="agr-top-banner">
    <div class="agr-top-flex">
      <div class="agr-title-group">
        <span class="agr-main-title">📋 Agreement Items Table (Excel Sheet Order — LTR)</span>
        <span class="agr-sub-badge">
          Showing {len(filtered_df)} item(s) • Drag column borders (⟷) or row borders (↕) with mouse to resize widths &amp; heights
        </span>
      </div>
      <div class="agr-actions-group">
        <span id="agr-save-indicator" class="agr-save-status">💾 Synced</span>
        <button type="button" id="agr-reset-dims-btn" class="agr-reset-btn" title="Reset column widths and row heights to defaults">
          ↺ Reset Table Dimensions
        </button>
      </div>
    </div>
  </div>

  <div class="agr-table-wrapper" id="agr-table-wrapper">
    <table id="m15-agr-table" dir="ltr">
      <colgroup>
        {colgroup_html}
      </colgroup>
      <thead class="agr-thead">
        <tr class="agr-header-row" id="agr-header-tr" data-row-idx="header">
          {thead_row_html}
        </tr>
      </thead>
      <tbody id="agr-tbody">
        {tbody_joined}
      </tbody>
    </table>
  </div>
</div>

<script>
(function() {{
  const COL_STORAGE_KEY = '{col_storage_key}';
  const ROW_STORAGE_KEY = '{row_storage_key}';
  const N_COLS = {n_cols};
  const DEFAULT_RATIOS = {default_ratios_json};
  const MIN_COL_WIDTHS = {min_widths_json};

  const table = document.getElementById('m15-agr-table');
  const wrapper = document.getElementById('agr-table-wrapper');
  const rootContainer = document.getElementById('agr-root-container');
  const cols = [];
  for (let i = 0; i < N_COLS; i++) {{
    cols.push(document.getElementById('agr-col-' + i));
  }}

  let hasInitializedVisibleWidth = false;

  function updateIframeHeight() {{
    try {{
      if (!rootContainer) return;
      const rect = rootContainer.getBoundingClientRect();
      const contentH = Math.ceil(rect.height || rootContainer.scrollHeight || rootContainer.offsetHeight || 0);
      if (contentH < 120) return;
      const h = contentH + 8;
      if (window.frameElement) {{
        window.frameElement.style.height = h + 'px';
        window.frameElement.style.minHeight = h + 'px';
        window.frameElement.style.maxHeight = h + 'px';
        window.frameElement.setAttribute('height', String(h));
        let p = window.frameElement.parentElement;
        let depth = 0;
        while (p && depth < 5) {{
          const testId = (p.getAttribute && p.getAttribute('data-testid')) || '';
          const cls = (typeof p.className === 'string') ? p.className : '';
          if (
            testId === 'stVerticalBlock' || testId === 'stVerticalBlockBorderWrapper' ||
            testId === 'stExpander' || testId === 'stExpanderDetails' ||
            testId === 'stColumn' || testId === 'stMainBlockContainer' ||
            cls.indexOf('stExpander') !== -1 ||
            p.tagName === 'DETAILS' || p.tagName === 'SECTION' || p.tagName === 'MAIN' || p.tagName === 'BODY'
          ) break;
          p.style.height = h + 'px';
          p.style.minHeight = h + 'px';
          p.style.maxHeight = h + 'px';
          p = p.parentElement;
          depth++;
        }}
      }}
    }} catch (e) {{}}
  }}

  if (typeof ResizeObserver !== 'undefined' && rootContainer) {{
    const ro = new ResizeObserver(function() {{
      if (wrapper && wrapper.clientWidth > 350 && !hasInitializedVisibleWidth) {{
        hasInitializedVisibleWidth = true;
        initColumnWidths(false);
        initRowHeights(false);
      }}
      updateIframeHeight();
    }});
    ro.observe(rootContainer);
    if (wrapper) ro.observe(wrapper);
  }}

  function initColumnWidths(forceDefault) {{
    let savedWidths = null;
    if (!forceDefault) {{
      try {{
        const raw = localStorage.getItem(COL_STORAGE_KEY);
        if (raw) {{
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed) && parsed.length === N_COLS && parsed.every(x => typeof x === 'number' && x >= 30)) {{
            savedWidths = parsed;
          }}
        }}
      }} catch (e) {{}}
    }}
    if (savedWidths) {{
      const totalW = savedWidths.reduce((a, b) => a + b, 0);
      if (totalW > 0) {{
        for (let i = 0; i < N_COLS; i++) {{
          if (cols[i]) cols[i].style.width = ((savedWidths[i] / totalW) * 100).toFixed(2) + '%';
        }}
      }}
    }} else {{
      for (let i = 0; i < N_COLS; i++) {{
        if (cols[i]) cols[i].style.width = (DEFAULT_RATIOS[i] * 100).toFixed(2) + '%';
      }}
    }}
    table.style.width = '100%';
    updateIframeHeight();
  }}

  function initRowHeights(forceDefault) {{
    if (forceDefault) {{
      const hdrTr = document.getElementById('agr-header-tr');
      if (hdrTr) hdrTr.style.height = '';
      document.querySelectorAll('tr.agr-row').forEach(tr => {{ tr.style.height = ''; }});
      updateIframeHeight();
      return;
    }}
    try {{
      const raw = localStorage.getItem(ROW_STORAGE_KEY);
      if (!raw) return;
      const savedRows = JSON.parse(raw);
      if (savedRows && typeof savedRows === 'object') {{
        if (savedRows['header']) {{
          const hdrTr = document.getElementById('agr-header-tr');
          if (hdrTr) hdrTr.style.height = savedRows['header'] + 'px';
        }}
        document.querySelectorAll('tr.agr-row').forEach(tr => {{
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
      const ths = table.querySelectorAll('thead th.agr-th');
      const arr = Array.from(ths).map(th => Math.round(th.getBoundingClientRect().width));
      if (arr.length === N_COLS) {{
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

  // ── Column Width Mouse-Drag Resizing (LTR) ──
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
      if (isNaN(cIdx) || cIdx < 0 || cIdx >= N_COLS - 1) return;

      const ths = table.querySelectorAll('thead th.agr-th');
      const curWidths = Array.from(ths).map(th => th.getBoundingClientRect().width);
      for (let i = 0; i < N_COLS; i++) {{
        if (cols[i]) cols[i].style.width = Math.round(curWidths[i]) + 'px';
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

  // ── Row Height Mouse-Drag Resizing ──
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
      const deltaRight = e.clientX - colStartX;
      const minCur = MIN_COL_WIDTHS[activeColIdx] || 46;
      const minNext = MIN_COL_WIDTHS[activeColIdx + 1] || 46;

      let newCurW = Math.max(minCur, colStartW + deltaRight);
      let actualDelta = newCurW - colStartW;
      let newNextW = nextColStartW - actualDelta;

      if (newNextW < minNext) {{
        newNextW = minNext;
        actualDelta = nextColStartW - minNext;
        newCurW = colStartW + actualDelta;
      }}

      const tblW = table.getBoundingClientRect().width || (wrapper ? wrapper.clientWidth : 1000) || 1000;
      if (cols[activeColIdx]) cols[activeColIdx].style.width = ((newCurW / tblW) * 100).toFixed(2) + '%';
      if (cols[activeColIdx + 1]) cols[activeColIdx + 1].style.width = ((newNextW / tblW) * 100).toFixed(2) + '%';

      table.style.width = '100%';
      updateIframeHeight();
      return;
    }}

    if (activeRowTr !== null) {{
      e.preventDefault();
      const deltaY = e.clientY - rowStartY;
      const minH = (activeRowKey === 'header') ? 34 : 28;
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
      if (activeRowKey) saveRowHeight(activeRowKey, finalH);
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

  // Reset Dimensions button
  const resetBtn = document.getElementById('agr-reset-dims-btn');
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

  // ── Live Estimated cost calculation + mutually-exclusive per-price Select sync ──
  const pendingUpdates = {{}};
  let syncTimer = null;

  function formatMoney(num) {{
    const n = Number(num) || 0;
    return n.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
  }}

  function recomputeRowAndQueue(tr, rk, delayMs) {{
    if (!tr || !rk) return;
    const chks = Array.from(tr.querySelectorAll('.agr-price-chk'));
    const activeChk = chks.find(c => c.checked) || null;
    const qtyInp = tr.querySelector('.agr-qty-input');
    const estSpan = tr.querySelector('.agr-est-val');

    const qty = qtyInp ? Math.max(0, parseFloat(qtyInp.value) || 0) : 0;
    const selPcol = activeChk ? (activeChk.getAttribute('data-pcol') || '') : '';
    const selPrice = activeChk ? (parseFloat(activeChk.getAttribute('data-price')) || 0) : 0;
    const estCost = (selPcol && qty > 0) ? (qty * selPrice) : 0;

    if (estSpan) estSpan.textContent = formatMoney(estCost);
    tr.classList.toggle('agr-row-selected', Boolean(selPcol));

    pendingUpdates[rk] = {{ selected_price_col: selPcol, qty: qty }};
    if (syncTimer) clearTimeout(syncTimer);
    syncTimer = setTimeout(flushSyncToStreamlit, delayMs);
  }}

  function flushSyncToStreamlit() {{
    const keys = Object.keys(pendingUpdates);
    if (!keys.length) return;
    const payload = {{ ts: Date.now(), updates: Object.assign({{}}, pendingUpdates) }};
    for (const k of keys) delete pendingUpdates[k];
    const jsonStr = JSON.stringify(payload);

    const badge = document.getElementById('agr-save-indicator');
    if (badge) {{
      badge.style.display = 'inline-flex';
      setTimeout(() => {{ badge.style.display = 'none'; }}, 2000);
    }}

    try {{
      if (window.parent && window.parent.document) {{
        const pDoc = window.parent.document;
        const input = pDoc.querySelector('input[aria-label="m15_agr_cart_sync_payload"]');
        if (input) {{
          const proto = (window.parent.HTMLInputElement || window.HTMLInputElement).prototype;
          const desc = Object.getOwnPropertyDescriptor(proto, 'value');
          if (desc && desc.set) desc.set.call(input, jsonStr);
          else input.value = jsonStr;
          if (input._valueTracker) input._valueTracker.setValue('');
          input.dispatchEvent(new Event('input', {{ bubbles: true }}));
          input.dispatchEvent(new Event('change', {{ bubbles: true }}));
          input.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13, which: 13 }}));
          input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13, which: 13 }}));
          input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        }}
      }}
    }} catch (err) {{
      console.warn('Agreement cart sync error:', err);
    }}
  }}

  // Mutually exclusive Select checkboxes per row (only ONE price column can be selected per row)
  document.querySelectorAll('.agr-price-chk').forEach(chk => {{
    chk.addEventListener('change', function() {{
      const rk = chk.getAttribute('data-rk');
      const tr = chk.closest('tr');
      if (chk.checked && tr) {{
        tr.querySelectorAll('.agr-price-chk').forEach(other => {{
          if (other !== chk) other.checked = false;
        }});
      }}
      recomputeRowAndQueue(tr, rk, 80);
    }});
  }});

  // Req. Quantity live calculation & sync
  document.querySelectorAll('.agr-qty-input').forEach(inp => {{
    inp.addEventListener('input', function() {{
      const rk = inp.getAttribute('data-rk');
      const tr = inp.closest('tr');
      if (!tr) return;
      const chks = Array.from(tr.querySelectorAll('.agr-price-chk'));
      const qty = Math.max(0, parseFloat(inp.value) || 0);
      // If user enters qty > 0 and no price column is selected yet, default to the first price column
      if (qty > 0 && chks.length > 0 && !chks.some(c => c.checked)) {{
        chks[0].checked = true;
      }}
      const activeChk = chks.find(c => c.checked) || null;
      const selPrice = activeChk ? (parseFloat(activeChk.getAttribute('data-price')) || 0) : 0;
      const estSpan = tr.querySelector('.agr-est-val');
      if (estSpan) estSpan.textContent = formatMoney(activeChk ? qty * selPrice : 0);
    }});
    inp.addEventListener('change', function() {{
      const rk = inp.getAttribute('data-rk');
      const tr = inp.closest('tr');
      if (!tr) return;
      const chks = Array.from(tr.querySelectorAll('.agr-price-chk'));
      const qty = Math.max(0, parseFloat(inp.value) || 0);
      if (qty > 0 && chks.length > 0 && !chks.some(c => c.checked)) {{
        chks[0].checked = true;
      }}
      recomputeRowAndQueue(tr, rk, 120);
    }});
    inp.addEventListener('keydown', function(e) {{
      if (e.key === 'Enter') inp.blur();
    }});
  }});

  window.addEventListener('load', updateIframeHeight);
  window.addEventListener('resize', updateIframeHeight);
  setTimeout(updateIframeHeight, 80);
  setTimeout(updateIframeHeight, 300);
}})();
</script>
</body>
</html>"""


def render_m15_agreement_wo_section() -> None:
    """
    Render the dedicated 'Agreement & W.O' section inside Module 15 (Masonry & Plastering).
    All titles/headers are English-only, strictly LTR, non-sortable (preserving Excel row order),
    with BOQ-style column headers matching the Module 15 BOQ & Cost table.
    """
    with st.expander(
        "📋 Agreement & W.O (Masonry & Plastering Works)",
        expanded=bool(st.session_state.get("m15_agreement_wo_expander", False)),
        key="m15_agreement_wo_expander",
    ):
        # ── Session state initialization ──
        if "m15_agr_excel_path" not in st.session_state:
            st.session_state["m15_agr_excel_path"] = DEFAULT_EXCEL_PATH
        if "m15_agr_sheet_name" not in st.session_state:
            st.session_state["m15_agr_sheet_name"] = ""
        if "m15_agr_cart" not in st.session_state:
            st.session_state["m15_agr_cart"] = {}  # {row_key: {"qty": float, ...}}
        if "m15_agr_cart_ver" not in st.session_state:
            st.session_state["m15_agr_cart_ver"] = 0
        if "m15_agr_changelog" not in st.session_state:
            st.session_state["m15_agr_changelog"] = pd.DataFrame()
        if "m15_agr_sync_status" not in st.session_state:
            st.session_state["m15_agr_sync_status"] = ""
        if "m15_agr_last_wo" not in st.session_state:
            st.session_state["m15_agr_last_wo"] = None
        if "m15_agr_page" not in st.session_state:
            st.session_state["m15_agr_page"] = 1

        # ── 1. Automatic Sync Once Per Session ──
        if not st.session_state.get("m15_agr_synced_once", False):
            df_synced, chg_df, status_msg, used_sheet = sync_agreement_excel(
                excel_path=st.session_state["m15_agr_excel_path"],
                force=False,
                sheet_name=st.session_state.get("m15_agr_sheet_name") or None,
            )
            st.session_state["m15_agr_df"] = df_synced
            st.session_state["m15_agr_sheet_name"] = used_sheet
            st.session_state["m15_agr_sync_status"] = status_msg
            if not chg_df.empty:
                st.session_state["m15_agr_changelog"] = chg_df
            st.session_state["m15_agr_synced_once"] = True

        # ── 2. Configuration & Sync Bar (Separate from W.O Generation Form) ──
        c_top_status, c_top_sync = st.columns([3.4, 1.2], gap="small")
        with c_top_status:
            st.markdown(
                f"""<div dir="ltr" style="direction:ltr; text-align:left; padding:9px 14px; border-radius:8px;
                    background:rgba(14,165,233,0.14); border:1.5px solid rgba(56,189,248,0.55);
                    color:#e0f2fe; font-size:0.92rem; font-weight:700;">
                    {html.escape(st.session_state.get("m15_agr_sync_status") or "Ready to sync agreement Excel file.")}
                </div>""",
                unsafe_allow_html=True,
            )
        with c_top_sync:
            if st.button(
                "🔄 Sync / Re-check Excel",
                key="m15_agr_btn_sync_now",
                use_container_width=True,
                help="Check Excel MD5 hash, refresh local JSON Cache, and detect any changes",
            ):
                df_synced, chg_df, status_msg, used_sheet = sync_agreement_excel(
                    excel_path=st.session_state["m15_agr_excel_path"],
                    force=True,
                    sheet_name=st.session_state.get("m15_agr_sheet_name") or None,
                )
                st.session_state["m15_agr_df"] = df_synced
                st.session_state["m15_agr_sheet_name"] = used_sheet
                st.session_state["m15_agr_sync_status"] = status_msg
                if not chg_df.empty:
                    st.session_state["m15_agr_changelog"] = chg_df
                st.rerun()

        with st.expander("⚙️ Agreement File Path & Excel Upload (Sync Settings)", expanded=False):
            new_path = st.text_input(
                "📁 Agreement Excel File Path:",
                value=st.session_state["m15_agr_excel_path"],
                key="m15_agr_path_input",
                help="Default path: data/agreement_m15.xlsx",
            )

            # Sheet selector when workbook contains multiple sheets
            sheets_info, active_sheet_default = _get_excel_sheet_info(st.session_state["m15_agr_excel_path"])
            if len(sheets_info) > 1:
                sheet_names_list = [s[0] for s in sheets_info]
                sheet_label_map = {s[0]: s[1] for s in sheets_info}
                cur_sheet = st.session_state.get("m15_agr_sheet_name") or active_sheet_default
                if cur_sheet not in sheet_names_list:
                    cur_sheet = active_sheet_default if active_sheet_default in sheet_names_list else sheet_names_list[0]
                chosen_sheet = st.selectbox(
                    "📑 Select Excel Sheet:",
                    options=sheet_names_list,
                    index=sheet_names_list.index(cur_sheet),
                    format_func=lambda s: sheet_label_map.get(s, s),
                    key="m15_agr_sheet_select",
                )
                if chosen_sheet != st.session_state.get("m15_agr_sheet_name"):
                    df_synced, chg_df, status_msg, used_sheet = sync_agreement_excel(
                        excel_path=st.session_state["m15_agr_excel_path"],
                        force=True,
                        sheet_name=chosen_sheet,
                    )
                    st.session_state["m15_agr_df"] = df_synced
                    st.session_state["m15_agr_sheet_name"] = used_sheet
                    st.session_state["m15_agr_sync_status"] = status_msg
                    st.session_state["m15_agr_cart"] = {}
                    st.session_state["m15_agr_cart_ver"] += 1
                    st.session_state["m15_agr_page"] = 1
                    st.session_state["m15_agr_changelog"] = chg_df if not chg_df.empty else pd.DataFrame()
                    st.rerun()

            c_p1, c_p2 = st.columns([1.5, 2.5])
            with c_p1:
                if st.button("💾 Save Path & Sync", key="m15_agr_save_path_btn", use_container_width=True):
                    st.session_state["m15_agr_excel_path"] = str(new_path or DEFAULT_EXCEL_PATH).strip()
                    df_synced, chg_df, status_msg, used_sheet = sync_agreement_excel(
                        excel_path=st.session_state["m15_agr_excel_path"],
                        force=True,
                        sheet_name=None,
                    )
                    st.session_state["m15_agr_df"] = df_synced
                    st.session_state["m15_agr_sheet_name"] = used_sheet
                    st.session_state["m15_agr_sync_status"] = status_msg
                    st.session_state["m15_agr_page"] = 1
                    if not chg_df.empty:
                        st.session_state["m15_agr_changelog"] = chg_df
                    st.rerun()
            with c_p2:
                uploaded_xlsx = st.file_uploader(
                    "📤 Or upload Excel file (.xlsx) to update data/agreement_m15.xlsx:",
                    type=["xlsx"],
                    key="m15_agr_file_uploader",
                )
                if uploaded_xlsx is not None:
                    if st.button("✅ Apply Uploaded File & Sync", key="m15_agr_apply_upload_btn", type="primary"):
                        cur_df_ref = st.session_state.get("m15_agr_df")
                        if isinstance(cur_df_ref, pd.DataFrame) and not cur_df_ref.empty:
                            cur_df_clean = _clean_exact_dataframe(cur_df_ref)
                            expected_upload_cols = [
                                c for c in cur_df_clean.columns
                                if not str(c).startswith("_") and str(c).strip().lower() not in _OPTIONAL_UPLOAD_COLS
                            ]
                        else:
                            expected_upload_cols = ["Item No.", "Description", "Unit", "Supply & Apply", "Manpower"]

                        uploaded_bytes = uploaded_xlsx.getvalue()
                        try:
                            is_ok, found_hdrs, diff_list, chk_sheet = _validate_uploaded_excel_headers(
                                file_bytes=uploaded_bytes,
                                expected_cols=expected_upload_cols,
                                sheet_name=None,
                            )
                        except Exception as val_exc:
                            is_ok = False
                            found_hdrs = []
                            diff_list = [f"Could not read the uploaded Excel file: {val_exc}"]
                            chk_sheet = ""

                        if not is_ok:
                            play_warning_sound(force=True)
                            _render_upload_error_modal(
                                expected_cols=expected_upload_cols,
                                found_cols=found_hdrs,
                                diffs=diff_list,
                                filename=getattr(uploaded_xlsx, "name", "uploaded.xlsx"),
                                sheet_name=chk_sheet,
                            )
                        else:
                            _ensure_data_dir()
                            target_xlsx = st.session_state["m15_agr_excel_path"] or DEFAULT_EXCEL_PATH
                            os.makedirs(os.path.dirname(os.path.abspath(target_xlsx)), exist_ok=True)
                            with open(target_xlsx, "wb") as f_out:
                                f_out.write(uploaded_bytes)
                            df_synced, chg_df, status_msg, used_sheet = sync_agreement_excel(
                                excel_path=target_xlsx,
                                force=True,
                                sheet_name=None,
                            )
                            st.session_state["m15_agr_df"] = df_synced
                            st.session_state["m15_agr_sheet_name"] = used_sheet
                            st.session_state["m15_agr_sync_status"] = status_msg
                            st.session_state["m15_agr_cart"] = {}
                            st.session_state["m15_agr_cart_ver"] += 1
                            st.session_state["m15_agr_page"] = 1
                            if not chg_df.empty:
                                st.session_state["m15_agr_changelog"] = chg_df
                            st.session_state["m15_agr_upload_success_toast"] = {
                                "filename": getattr(uploaded_xlsx, "name", "agreement_m15.xlsx"),
                                "rows": len(df_synced),
                                "sheet": used_sheet,
                            }
                            st.rerun()

        # Show 3-second green success panel after a valid Excel upload
        _ok_toast = st.session_state.pop("m15_agr_upload_success_toast", None)
        if isinstance(_ok_toast, dict):
            _render_upload_success_toast(
                filename=str(_ok_toast.get("filename", "")),
                rows_count=int(_ok_toast.get("rows", 0)),
                sheet_name=str(_ok_toast.get("sheet", "")),
            )

        # ── 3. Persistent Change-Detection Warning Banner ──
        chg_df_live: pd.DataFrame = st.session_state.get("m15_agr_changelog", pd.DataFrame())
        if isinstance(chg_df_live, pd.DataFrame) and not chg_df_live.empty:
            st.warning(
                f"⚠️ **{len(chg_df_live)} change(s) detected in the Agreement Excel file compared to the previous cached version!** "
                "Review the details below."
            )
            with st.expander(f"🔎 View Detected Changes ({len(chg_df_live)} change(s))", expanded=False):
                st.dataframe(chg_df_live, use_container_width=True, hide_index=True)
                if st.button("✔️ Dismiss Changes Banner", key="m15_agr_dismiss_chg_btn"):
                    st.session_state["m15_agr_changelog"] = pd.DataFrame()
                    st.rerun()

        agr_df: pd.DataFrame = st.session_state.get("m15_agr_df", pd.DataFrame())
        if agr_df is None or agr_df.empty:
            st.info(
                "ℹ️ No agreement items are currently loaded. Place `data/agreement_m15.xlsx` "
                "or upload an Excel file in Sync Settings above, then click **🔄 Sync / Re-check Excel**."
            )
            return

        # Clean headers on loaded df to guarantee '# -> Item No.' & 'heli -> Description'
        agr_df = _clean_exact_dataframe(agr_df)

        # Resolve dynamic semantic roles while preserving EXACT Excel column names & row order
        excel_cols = [
            c for c in agr_df.columns
            if not str(c).startswith("_") and c not in ("Select", "Req. Quantity", "اختيار", "الكمية المطلوبة")
        ]
        roles = _resolve_column_roles(agr_df[excel_cols])
        code_col = roles["code_col"]
        desc_col = roles["desc_col"]
        unit_col = roles["unit_col"]
        price_cols = roles["price_cols"]
        numeric_cols = roles["numeric_cols"]

        # Build ordered row list (strictly preserving Excel sheet order, NO sorting)
        key_map = _build_unique_key_map(agr_df[excel_cols])
        all_rows = []
        for u_key, r_dict in key_map.items():
            row_copy = {c: r_dict.get(c, "") for c in excel_cols}
            row_copy["_row_key"] = u_key
            all_rows.append(row_copy)
        full_df = pd.DataFrame(all_rows)

        # ── 4. Smart Search & Resizable Interactive Table (English Only, LTR, BOQ-Style Resizing) ──
        st.markdown(
            """<div dir="ltr" style="direction:ltr; text-align:left; font-size:1.05rem; font-weight:900; color:#38bdf8; margin:10px 0 6px 0;">
                🔍 Smart Search & Work Order Item Selection
            </div>""",
            unsafe_allow_html=True,
        )

        c_srch, c_cart_info, c_cart_clr = st.columns([2.6, 1.25, 0.9], gap="small")

        with c_srch:
            search_query = st.text_input(
                "🔎 Search (Item No., Description, Unit...):",
                value="",
                key="m15_agr_search_query",
                placeholder="e.g. C.009, plastering, brick, M2...",
            )

        # Build row metadata lookup (with ALL price columns per row) so iframe cart sync computes exact Unit_Price
        row_lookup: Dict[str, Dict[str, Any]] = {}
        for _, r_all in full_df.iterrows():
            rk_all = str(r_all["_row_key"])
            prices_dict = {pc: round(_clean_float(r_all[pc], 0.0), 2) for pc in price_cols}
            default_price = prices_dict[price_cols[0]] if price_cols else 0.0
            row_lookup[rk_all] = {
                "Item_Code": (_clean_cell_str(r_all[code_col]) if code_col else "") or rk_all,
                "Description": _clean_cell_str(r_all[desc_col]) if desc_col else "",
                "Unit": _clean_cell_str(r_all[unit_col]) if unit_col else "",
                "Unit_Price": default_price,
                "prices": prices_dict,
            }
        st.session_state["m15_agr_row_lookup"] = row_lookup

        # Hidden bridge input for receiving Req. Quantity & per-price Select updates from the resizable table iframe
        st.markdown(
            """<style>
            div[data-testid="stTextInput"]:has(input[aria-label="m15_agr_cart_sync_payload"]) {
                position: fixed !important;
                left: -9999px !important;
                top: -9999px !important;
                width: 1px !important;
                height: 1px !important;
                opacity: 0 !important;
                pointer-events: none !important;
                margin: 0 !important;
                padding: 0 !important;
                overflow: hidden !important;
            }
            </style>""",
            unsafe_allow_html=True,
        )
        st.text_input(
            "m15_agr_cart_sync_payload",
            key="m15_agr_cart_sync_payload",
            label_visibility="collapsed",
            on_change=_process_m15_agr_cart_sync,
        )

        # Keep existing cart Unit_Price synced with each item's selected price column
        cart: Dict[str, Dict[str, Any]] = st.session_state["m15_agr_cart"]
        for rk_c, c_item in cart.items():
            if rk_c in row_lookup:
                sel_pc = str(c_item.get("selected_price_col") or (price_cols[0] if price_cols else ""))
                c_item["selected_price_col"] = sel_pc
                c_item["Unit_Price"] = row_lookup[rk_c]["prices"].get(sel_pc, row_lookup[rk_c]["Unit_Price"])

        with c_cart_info:
            st.markdown(
                f"""<div dir="ltr" style="direction:ltr; margin-top:26px; padding:7px 10px; border-radius:8px;
                    background:rgba(16,185,129,0.16); border:1.5px solid #10b981; color:#a7f3d0;
                    font-weight:800; text-align:center;">
                    🛒 Selected: {len(cart)}
                </div>""",
                unsafe_allow_html=True,
            )
        with c_cart_clr:
            st.markdown("<div style='margin-top:26px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Clear Cart", key="m15_agr_clear_cart_btn", use_container_width=True, disabled=(len(cart) == 0)):
                st.session_state["m15_agr_cart"] = {}
                st.session_state["m15_agr_cart_ver"] += 1
                st.rerun()

        # Filter rows strictly in original Excel sheet order (NO sorting)
        filtered_df = full_df.copy()
        q_clean = str(search_query or "").strip().lower()
        if q_clean:
            tokens = [t for t in q_clean.split() if t]
            def _row_matches(r: pd.Series) -> bool:
                hay = " ".join(_clean_cell_str(r[c]) for c in excel_cols).lower()
                return all(tok in hay for tok in tokens)
            filtered_df = filtered_df[filtered_df.apply(_row_matches, axis=1)].reset_index(drop=True)

        # Render full BOQ-style resizable table (mouse-drag column widths & row heights, LTR, non-sortable)
        sheet_sig = hashlib.md5(f"{st.session_state.get('m15_agr_sheet_name', '')}||{'|'.join(excel_cols)}".encode("utf-8")).hexdigest()[:6]
        table_html = _build_agreement_resizable_table_html(
            filtered_df=filtered_df,
            excel_cols=excel_cols,
            code_col=code_col,
            desc_col=desc_col,
            unit_col=unit_col,
            price_cols=price_cols,
            numeric_cols=numeric_cols,
            cart=cart,
            sheet_sig=sheet_sig,
        )
        est_height = min(610, 120 + max(1, len(filtered_df)) * 42)
        render_html_iframe(table_html, height=est_height, scrolling=False)

        # ── 5. Work Order Generation Form (st.form) ──
        history = _load_wo_history()
        suggested_wo_no = _suggest_next_wo_number(history)
        default_proj_name = str(st.session_state.get("active_project") or st.session_state.get("cfg", {}).get("project_name", "") or "")

        st.markdown(
            """<div dir="ltr" style="direction:ltr; text-align:left; font-size:1.05rem; font-weight:900; color:#fbbf24; margin:14px 0 6px 0;">
                📝 Work Order Generation Form
            </div>""",
            unsafe_allow_html=True,
        )

        with st.form("wo_generation_form", clear_on_submit=False):
            f_r1_c1, f_r1_c2, f_r1_c3 = st.columns([1.2, 1.0, 1.4])
            with f_r1_c1:
                wo_number = st.text_input("🔢 Work Order No. (W.O No.):", value=suggested_wo_no)
            with f_r1_c2:
                issue_date = st.date_input("📅 Issue Date:", value=datetime.date.today())
            with f_r1_c3:
                project_site = st.text_input("🏗️ Project / Site:", value=default_proj_name)

            f_r2_c1, f_r2_c2 = st.columns([1.6, 1.2])
            with f_r2_c1:
                contractor_name = st.text_input("🏢 Contractor / Company Name:", placeholder="Enter contractor or company name...")
            with f_r2_c2:
                exec_duration = st.text_input("⏱️ Execution Duration (Optional):", placeholder="e.g. 30 Days")

            wo_notes = st.text_area("📄 Notes / Special Instructions:", height=70, placeholder="Enter any technical conditions or site instructions...")

            submitted_wo = st.form_submit_button(
                "Generate & Review Work Order",
                type="primary",
                use_container_width=True,
            )

        auto_expand_output = False
        if submitted_wo:
            selected_list = [
                v for v in st.session_state["m15_agr_cart"].values()
                if round(_clean_float(v.get("qty", 0.0)), 2) > 0.0
            ]
            if not selected_list:
                st.error("⚠️ Please select at least one item and enter a 'Req. Quantity' greater than zero before generating the Work Order.")
            elif not str(wo_number or "").strip():
                st.error("⚠️ Please enter a valid Work Order No. (W.O No.).")
            else:
                summary_rows = []
                grand_total = 0.0
                for it in selected_list:
                    q_v = round(_clean_float(it["qty"]), 2)
                    p_v = round(_clean_float(it["Unit_Price"]), 2)
                    t_v = round(q_v * p_v, 2)
                    grand_total += t_v
                    summary_rows.append({
                        "Item_Code": it["Item_Code"],
                        "Description": it["Description"],
                        "Unit": it["Unit"],
                        "W.O Qty": q_v,
                        "Unit_Price": p_v,
                        "Total_Price": t_v,
                    })

                wo_meta = {
                    "wo_number": str(wo_number).strip(),
                    "issue_date": str(issue_date),
                    "project_site": str(project_site or "").strip(),
                    "contractor": str(contractor_name or "").strip(),
                    "duration": str(exec_duration or "").strip(),
                    "notes": str(wo_notes or "").strip(),
                    "items_count": len(summary_rows),
                    "grand_total": round(grand_total, 2),
                    "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "items": summary_rows,
                }

                # Persist to W.O history log
                history.append(wo_meta)
                _save_wo_history(history)
                st.session_state["m15_agr_last_wo"] = wo_meta
                auto_expand_output = True
                st.success(f"✅ Work Order '{wo_meta['wo_number']}' generated and saved to W.O History Log!")

        # ── 6. Output & Export Section (Collapsed by Default, Auto-Expands on Submit) ──
        last_wo = st.session_state.get("m15_agr_last_wo")
        with st.expander(
            "📦 Work Order Output & Export",
            expanded=auto_expand_output,
        ):
            if not last_wo or not last_wo.get("items"):
                st.info("ℹ️ No Work Order generated in this session yet — select items and click 'Generate & Review Work Order'.")
            else:
                out_df = pd.DataFrame(last_wo["items"])
                m_c1, m_c2, m_c3 = st.columns(3)
                with m_c1:
                    st.metric("🔢 Work Order No.", last_wo["wo_number"])
                with m_c2:
                    st.metric("📦 Selected Items", f"{len(out_df)} item(s)")
                with m_c3:
                    st.metric("💰 Grand Total (EGP)", f"{float(last_wo['grand_total']):,.2f}")

                st.dataframe(
                    out_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Item_Code": st.column_config.TextColumn("Item No."),
                        "Description": st.column_config.TextColumn("Description"),
                        "Unit": st.column_config.TextColumn("Unit"),
                        "W.O Qty": st.column_config.NumberColumn("Req. Quantity", format="%.2f"),
                        "Unit_Price": st.column_config.NumberColumn("Unit Price", format="%.2f"),
                        "Total_Price": st.column_config.NumberColumn("Total Price", format="%.2f"),
                    },
                )

                xlsx_bytes = export_wo_to_excel(last_wo, out_df)
                safe_fname = re.sub(r"[^A-Za-z0-9_\-]+", "_", str(last_wo["wo_number"]))
                st.download_button(
                    label="📥 Download Work Order (.xlsx)",
                    data=xlsx_bytes,
                    file_name=f"{safe_fname}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                    key=f"m15_agr_dl_xlsx_{safe_fname}",
                )

        # ── 7. Secondary Collapsed Expander: Work Order History & Cumulative Consumed Quantities ──
        with st.expander(
            f"📚 Work Order History Log & Cumulative Quantities ({len(history)})",
            expanded=False,
        ):
            if not history:
                st.info("ℹ️ No previous Work Orders recorded in `data/wo_history_m15.json`.")
            else:
                hist_summary = []
                cum_map: Dict[str, Dict[str, Any]] = {}
                for h_rec in reversed(history):
                    hist_summary.append({
                        "W.O No.": h_rec.get("wo_number", ""),
                        "Issue Date": h_rec.get("issue_date", ""),
                        "Project / Site": h_rec.get("project_site", ""),
                        "Contractor": h_rec.get("contractor", ""),
                        "Items Count": h_rec.get("items_count", len(h_rec.get("items", []))),
                        "Grand Total (EGP)": round(_clean_float(h_rec.get("grand_total", 0.0)), 2),
                    })
                    for it in h_rec.get("items", []):
                        ic = _clean_cell_str(it.get("Item_Code", "")) or _clean_cell_str(it.get("Description", ""))[:30]
                        if ic not in cum_map:
                            cum_map[ic] = {
                                "Item No.": it.get("Item_Code", ""),
                                "Description": it.get("Description", ""),
                                "Unit": it.get("Unit", ""),
                                "Cumulative Qty": 0.0,
                                "Cumulative Cost (EGP)": 0.0,
                            }
                        cum_map[ic]["Cumulative Qty"] = round(
                            cum_map[ic]["Cumulative Qty"] + _clean_float(it.get("W.O Qty", 0.0)), 2
                        )
                        cum_map[ic]["Cumulative Cost (EGP)"] = round(
                            cum_map[ic]["Cumulative Cost (EGP)"] + _clean_float(it.get("Total_Price", 0.0)), 2
                        )

                st.markdown("**📋 Issued Work Orders:**")
                st.dataframe(pd.DataFrame(hist_summary), use_container_width=True, hide_index=True)

                if cum_map:
                    st.markdown("**📊 Cumulative Consumed Quantities per Item:**")
                    st.dataframe(pd.DataFrame(list(cum_map.values())), use_container_width=True, hide_index=True)
