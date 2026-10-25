"""
Column Detector: identifies financial tokens and clusters their right-edges (x1)
to dynamically discover value columns.
"""
from __future__ import annotations
import re
import statistics
from typing import Any

from parser.config import ScaledThresholds
from parser.value_parser import NIL_CHARS, NEG_PREFIXES

# A token is financial if it has thousands commas, negative prefix, or is a nil marker
FINANCIAL_NUM_RE = re.compile(r'^\d{1,3}(,\d{3})+$|^\d+,\d+$')


def is_financial_token(text: str) -> bool:
    """
    Checks if a token text qualifies as a financial value token
    (eligible to seed column right-edge detection).
    Prevents years (2025), days (31), or page numbers (4) from seeding columns.
    """
    t = text.strip()
    if not t:
        return False

    # Nil marker
    if t in NIL_CHARS:
        return True

    # Negative prefix marker (△, ▲)
    if t.startswith(NEG_PREFIXES):
        # Could be △2,979 or △0
        rem = t[1:].strip().replace(',', '')
        if rem.isdigit():
            return True

    # Number with thousands comma(s)
    if ',' in t:
        clean = t.replace(',', '')
        if clean.isdigit():
            return True

    return False


def detect_columns(
    tokens: list[dict[str, Any]],
    header_y_cutoff: float,
    thresholds: ScaledThresholds
) -> list[float]:
    """
    Clusters the right-edges (x1) of financial tokens in the data zone.
    Returns a sorted list of representative x1 coordinates (one per column).
    """
    # 1. Collect x1 of financial tokens in the data zone
    financial_x1s = []
    for t in tokens:
        if t["top"] > header_y_cutoff:
            text = t.get("text", "").strip()
            if is_financial_token(text):
                financial_x1s.append(round(t["x1"], 2))

    if not financial_x1s:
        return []

    # 2. Sort unique x1 coordinates
    unique_x1s = sorted(set(financial_x1s))

    # 3. Cluster with gap threshold
    clusters: list[list[float]] = [[unique_x1s[0]]]
    for x1 in unique_x1s[1:]:
        if x1 - clusters[-1][-1] <= thresholds.col_x1_gap:
            clusters[-1].append(x1)
        else:
            clusters.append([x1])

    # 4. Compute cluster centroids (median of all observations in cluster)
    centroids = []
    for c in clusters:
        # Get all original occurrences falling into this cluster range
        min_c, max_c = min(c), max(c)
        pts = [x for x in financial_x1s if min_c <= x <= max_c]
        centroids.append(round(statistics.median(pts), 2))

    centroids.sort()
    return centroids
