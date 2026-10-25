"""
Header Parser: identifies header zone boundary, statement title,
amendment status, unit, period labels, and dates.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Any

from parser.config import ScaledThresholds
from parser.value_parser import normalize_japanese_date

METADATA_HEADER_PATTERNS = [
    re.compile(r'\d{4}\s*年'),
    re.compile(r'\d{1,2}\s*月'),
    re.compile(r'前.*連結|当.*連結|前.*事業年度|当.*事業年度|前.*期|当.*期|中間|四半期'),
    re.compile(r'会計年度'),
    re.compile(r'単位[：:]'),
    re.compile(r'貸借対照表|損益計算書|キャッシュ・フロー'),
]

UNIT_RE = re.compile(r'単位[：:]\s*([^\s)）]+)')
PAGE_NOTE_RE = re.compile(r'^[-－—―]?\s*\d+\s*[-－—―]?$')
TITLE_RE = re.compile(r'([（(]?[０-９0-9一二三四五六七八九十]+[)）]?[．.、]?)?\s*(連結貸借対照表|個別貸借対照表|貸借対照表)')
AMENDMENT_RE = re.compile(r'[（(]?(訂正[前後]|訂正)[)）]?')


def find_header_boundary(
    tokens: list[dict[str, Any]],
    page_height: float,
    fallback_fraction: float = 0.15
) -> float:
    """
    Finds the vertical bottom cutoff for the header zone.
    Data rows begin strictly below this y-coordinate.
    """
    header_token_bottoms = []

    for t in tokens:
        text = t.get("text", "").strip()
        # Only check tokens in the upper 40% of the page
        if t["top"] < page_height * 0.40:
            for pat in METADATA_HEADER_PATTERNS:
                if pat.search(text):
                    header_token_bottoms.append(t["bottom"])
                    break

    if header_token_bottoms:
        # Give a small 2.0 pt margin below the lowest header metadata token
        return max(header_token_bottoms) + 2.0

    return page_height * fallback_fraction


def is_page_note(row_tokens: list[dict[str, Any]], page_height: float) -> bool:
    """
    Determines if a y-band of tokens is purely a page number or footer note.
    """
    if not row_tokens:
        return False

    # Must be in the lower 25% of the page or solitary
    avg_top = sum(t["top"] for t in row_tokens) / len(row_tokens)
    if avg_top < page_height * 0.75:
        return False

    # Check if all tokens match page note pattern
    joined = "".join(t.get("text", "").strip() for t in row_tokens)
    return bool(PAGE_NOTE_RE.match(joined))


def extract_metadata(
    header_tokens: list[dict[str, Any]],
    source_file: str,
    page_number: int
) -> dict[str, Any]:
    """
    Extracts high-level metadata (title, unit, amendment) from header zone tokens.
    """
    title = "貸借対照表"
    unit = "千円"  # Japanese standard default if unspecified
    amendment = None

    for t in header_tokens:
        text = t.get("text", "").strip()

        # Check for title
        m_title = TITLE_RE.search(text)
        if m_title:
            title = m_title.group(2)

        # Check for amendment
        m_amend = AMENDMENT_RE.search(text)
        if m_amend:
            amendment = m_amend.group(1)

        # Check for unit
        m_unit = UNIT_RE.search(text)
        if m_unit:
            unit = m_unit.group(1)

    return {
        "source_file": source_file,
        "page": page_number,
        "title": title,
        "unit": unit,
        "amendment": amendment,
    }


def associate_period_headers(
    header_tokens: list[dict[str, Any]],
    column_centroids: list[float],
    col_assign_pts: float
) -> list[dict[str, Any]]:
    """
    Maps header text and dates to each column centroid.
    """
    # Group header tokens by column proximity
    col_header_tokens: dict[int, list[dict[str, Any]]] = {
        i: [] for i in range(len(column_centroids))
    }

    for t in header_tokens:
        x_center = (t["x0"] + t["x1"]) / 2.0
        # Find closest column centroid
        best_col = None
        min_dist = float("inf")
        for i, c_x1 in enumerate(column_centroids):
            # Centroid is right-edge x1, so text should be close to or slightly left of c_x1
            dist = abs(t["x1"] - c_x1)
            if dist < min_dist:
                min_dist = dist
                best_col = i

        if best_col is not None and min_dist <= (col_assign_pts * 3.0):
            col_header_tokens[best_col].append(t)

    periods = []
    for col_idx, tokens in col_header_tokens.items():
        # Sort top-to-bottom
        tokens.sort(key=lambda t: t["top"])
        label_parts = []
        date_str = None
        raw_date = None

        for t in tokens:
            text = t.get("text", "").strip()
            iso_date, ok = normalize_japanese_date(text)
            if ok:
                date_str = iso_date
                raw_date = text
            else:
                # Exclude units and titles
                if not UNIT_RE.search(text) and not TITLE_RE.search(text) and not AMENDMENT_RE.search(text):
                    label_parts.append(text)

        raw_period = "".join(label_parts) if label_parts else f"期間_{col_idx+1}"
        period_label = unicodedata.normalize('NFKC', raw_period)
        header_text = f"{period_label} {raw_date}" if raw_date else period_label
        periods.append({
            "column_index": col_idx,
            "label": period_label,
            "date": date_str,
            "raw_date": raw_date,
            "header": header_text,
        })


    return periods
