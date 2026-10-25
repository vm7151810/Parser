"""
Row Assembler: groups data-zone tokens into rows by y-band overlap,
distinguishes nil tokens from missing cells, and attaches cell provenance.
"""
from __future__ import annotations
from typing import Any

from parser.config import ScaledThresholds
from parser.table_model import Row, CellValue, Provenance
from parser.value_parser import parse_value
from parser.indent_clusterer import IndentClusterer
from parser.header_parser import is_page_note


def assemble_rows(
    tokens: list[dict[str, Any]],
    header_y_cutoff: float,
    page_height: float,
    column_centroids: list[float],
    period_labels: list[str],
    indent_clusterer: IndentClusterer,
    thresholds: ScaledThresholds,
    page_number: int = 1
) -> list[Row]:
    """
    Assembles raw rows from tokens in the data zone.
    """
    # 1. Filter tokens to data zone
    data_tokens = [t for t in tokens if t["top"] > header_y_cutoff]
    if not data_tokens:
        return []

    # Sort primarily by vertical position (top)
    data_tokens.sort(key=lambda t: (round(t["top"], 1), t["x0"]))

    # 2. Group into y-bands
    y_bands: list[list[dict[str, Any]]] = []
    current_band: list[dict[str, Any]] = [data_tokens[0]]

    for t in data_tokens[1:]:
        # Compare with the vertical center of the current band
        band_top = min(x["top"] for x in current_band)
        band_bottom = max(x["bottom"] for x in current_band)
        band_mid = (band_top + band_bottom) / 2.0
        t_mid = (t["top"] + t["bottom"]) / 2.0

        # Check if t overlaps or is within y_band_tol of the current band
        overlap = not (t["bottom"] < band_top - thresholds.y_band_tol or
                       band_bottom < t["top"] - thresholds.y_band_tol)
        close_mid = abs(t_mid - band_mid) <= thresholds.y_band_tol * 2.0

        if overlap or close_mid:
            current_band.append(t)
        else:
            y_bands.append(current_band)
            current_band = [t]

    if current_band:
        y_bands.append(current_band)

    # 3. Assemble each band into a Row
    first_col_x1 = column_centroids[0] if column_centroids else float("inf")
    rows: list[Row] = []
    row_counter = 1

    for band in y_bands:
        # Check if this band is a page note / footer
        if is_page_note(band, page_height):
            continue

        # Sort tokens horizontally
        band.sort(key=lambda t: t["x0"])

        # Label tokens: left of first column minus assignment margin
        label_tokens = [t for t in band if t["x1"] < (first_col_x1 - thresholds.col_assign)]

        # If there are no label tokens, but there are tokens left of first col centroid
        if not label_tokens:
            label_tokens = [t for t in band if t["x1"] < first_col_x1]

        raw_label = "".join(t.get("text", "").strip() for t in label_tokens)
        import unicodedata
        label_text = unicodedata.normalize('NFKC', raw_label)
        if not label_text:
            # Fallback if band has no label but has numbers (e.g. wrapped numbers)
            # Skip or treat as orphan
            continue

        # Label provenance
        prov_label = Provenance(
            page=page_number,
            x0=min(t["x0"] for t in label_tokens),
            y0=min(t["top"] for t in label_tokens),
            x1=max(t["x1"] for t in label_tokens),
            y1=max(t["bottom"] for t in label_tokens),
            token_index=label_tokens[0].get("token_index")
        )

        level, is_uncertain = indent_clusterer.get_level(prov_label.x0)
        row_flags = ["level_uncertain"] if is_uncertain else []

        # Value tokens in each column
        values: dict[str, CellValue] = {}

        for col_idx, col_x1 in enumerate(column_centroids):
            period_name = period_labels[col_idx] if col_idx < len(period_labels) else f"col_{col_idx}"

            # Find matching token near col_x1
            candidates = [
                t for t in band
                if abs(t["x1"] - col_x1) <= thresholds.col_assign
            ]

            if candidates:
                # Pick the closest candidate
                cand = min(candidates, key=lambda t: abs(t["x1"] - col_x1))
                val_text = cand.get("text", "").strip()
                num, is_nil, is_neg, parse_flags = parse_value(val_text)

                prov = Provenance(
                    page=page_number,
                    x0=cand["x0"],
                    y0=cand["top"],
                    x1=cand["x1"],
                    y1=cand["bottom"],
                    token_index=cand.get("token_index")
                )

                values[period_name] = CellValue(
                    raw=val_text,
                    numeric=num,
                    nil=is_nil,
                    negative=is_neg,
                    flags=parse_flags,
                    provenance=prov
                )
            else:
                # Missing cell
                values[period_name] = CellValue(
                    raw="",
                    numeric=None,
                    nil=False,
                    negative=False,
                    flags=["cell_missing"],
                    provenance=None
                )

        row_id = f"row_{row_counter:03d}"
        row_counter += 1

        row = Row(
            id=row_id,
            structural_path=[],  # Will be populated by hierarchy_builder
            label=label_text,
            level=level,
            row_type="item",     # Will be determined by row_typer
            gross_parent=None,
            block_id=None,
            sum_parent_path=None,
            values=values,
            provenance_label=prov_label,
            flags=row_flags
        )
        rows.append(row)

    return rows
