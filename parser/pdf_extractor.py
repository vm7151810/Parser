"""
PDF Extractor: extracts word bounding boxes, glyph statistics,
and merges detached negative markers (△, ▲).
"""
from __future__ import annotations
import re
import statistics
from typing import Any
import pdfplumber

from parser.config import ParserConfig, ScaledThresholds

NEG_MARKERS = frozenset(['△', '▲'])
NUM_OR_SEP_RE = re.compile(r'^\d[\d,]*$')


def extract_page_tokens(
    page: pdfplumber.page.Page,
    config: ParserConfig,
    page_number: int = 1
) -> tuple[list[dict[str, Any]], float, ScaledThresholds, dict[str, Any]]:
    """
    Extracts words from a PDF page, calculates median glyph width,
    scales thresholds, and merges detached negative markers.

    Returns:
        tokens: list of merged word dicts with keys (text, x0, top, x1, bottom, token_index)
        median_glyph_width: float
        thresholds: ScaledThresholds
        page_info: dict with page geometry (width, height, page_number)
    """
    page_width = float(page.width)
    page_height = float(page.height)

    # 1. Compute median glyph width from page characters
    non_space_chars = [
        c for c in page.chars
        if c.get("text", "").strip() and not c.get("text", "").isdigit()
    ]
    if not non_space_chars:
        non_space_chars = [c for c in page.chars if c.get("text", "").strip()]

    if non_space_chars:
        widths = [float(c.get("width", 0)) for c in non_space_chars if c.get("width", 0) > 0]
        median_glyph_width = statistics.median(widths) if widths else 8.0
    else:
        median_glyph_width = 8.0

    # Ensure reasonable bounds for glyph width (e.g. between 3.0 and 30.0 pts)
    median_glyph_width = max(3.0, min(median_glyph_width, 30.0))
    thresholds = config.scale(median_glyph_width)

    # 2. Extract words
    raw_words = page.extract_words(
        x_tolerance=3,
        y_tolerance=3,
        keep_blank_chars=False
    )

    # 3. Merge detached negative markers
    # When a font or PDF engine outputs '△' as a separate glyph before the digits
    merged_tokens: list[dict[str, Any]] = []
    skip_next = False

    for i, w in enumerate(raw_words):
        if skip_next:
            skip_next = False
            continue

        token = dict(w)
        text = token.get("text", "").strip()

        if text in NEG_MARKERS and i + 1 < len(raw_words):
            next_w = raw_words[i + 1]
            next_text = next_w.get("text", "").strip()

            # Check vertical overlap
            top_overlap = not (token["bottom"] < next_w["top"] - thresholds.detach_merge_y_tol or
                              next_w["bottom"] < token["top"] - thresholds.detach_merge_y_tol)

            # Check horizontal proximity (marker must precede number within 1.5 glyph widths)
            h_prox = 0 <= (next_w["x0"] - token["x1"]) <= (1.5 * median_glyph_width)

            if top_overlap and h_prox and NUM_OR_SEP_RE.match(next_text):
                merged_token = {
                    "text": text + next_text,
                    "x0": token["x0"],
                    "top": min(token["top"], next_w["top"]),
                    "x1": next_w["x1"],
                    "bottom": max(token["bottom"], next_w["bottom"]),
                    "upright": token.get("upright", True),
                }
                merged_tokens.append(merged_token)
                skip_next = True
                continue

        merged_tokens.append(token)

    # Assign sequential token indices for provenance
    for idx, t in enumerate(merged_tokens):
        t["token_index"] = idx

    page_info = {
        "width": page_width,
        "height": page_height,
        "page_number": page_number,
        "median_glyph_width": median_glyph_width,
    }

    return merged_tokens, median_glyph_width, thresholds, page_info
