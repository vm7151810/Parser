"""
Row Typer: assigns deterministic row types via label morphology (stem matching)
and structural position. Inspects values for flags only (values never decide type).
"""
from __future__ import annotations
import re
from parser.table_model import Row

NET_SUFFIXES = ("（純額）", "(純額)")
CONTRA_KEYWORDS = ("累計額", "引当金")


def type_rows(rows: list[Row]) -> list[Row]:
    """
    Classifies rows into:
    section, header, item, gross, contra, contra_standalone, net, net_orphan, subtotal.
    Also assigns block_id, gross_parent, and sum_parent_path.
    """
    # 1. Initial pass: identify headers, sections, subtotals, and candidate nets
    for r in rows:
        # Check if row has any numeric/nil values
        has_values = any(
            v.numeric is not None or v.nil
            for v in r.values.values()
        )

        if not has_values:
            if r.level == 0:
                r.row_type = "section"
            else:
                r.row_type = "header"
            r.sum_parent_path = None
        elif r.label.endswith("合計"):
            r.row_type = "subtotal"
            # Subtotals themselves don't feed standard item sums
            r.sum_parent_path = None
        elif any(r.label.endswith(sfx) for sfx in NET_SUFFIXES):
            r.row_type = "net"
        elif any(kw in r.label for kw in CONTRA_KEYWORDS):
            # Candidate contra (may become paired contra or standalone)
            r.row_type = "contra_candidate"
        else:
            r.row_type = "item"

    # 2. Triplet stem-pairing pass: match net rows with preceding gross and contra rows
    for i, r in enumerate(rows):
        if r.row_type != "net":
            continue

        # Extract base stem
        stem = r.label
        for sfx in NET_SUFFIXES:
            if stem.endswith(sfx):
                stem = stem[:-len(sfx)].strip()
                break

        # Scan backwards to locate the matching gross row
        matched_gross_idx = None
        for j in range(i - 1, -1, -1):
            prev_row = rows[j]
            # Stop if we hit a subtotal or section boundary
            if prev_row.row_type in ("section", "subtotal"):
                break
            if prev_row.label == stem:
                matched_gross_idx = j
                break

        if matched_gross_idx is not None:
            gross_row = rows[matched_gross_idx]
            gross_row.row_type = "gross"
            block_id = f"block_{stem}_{matched_gross_idx}"
            gross_row.block_id = block_id
            gross_row.sum_parent_path = None

            r.gross_parent = stem
            r.block_id = block_id

            # Mark intervening contra rows
            for k in range(matched_gross_idx + 1, i):
                interv = rows[k]
                if "累計額" in interv.label or interv.row_type == "contra_candidate":
                    interv.row_type = "contra"
                    interv.gross_parent = stem
                    interv.block_id = block_id
                    interv.sum_parent_path = None
        else:
            r.row_type = "net_orphan"
            r.flags.append("gross_parent_missing")

    # 3. Classify remaining contra candidates as contra_standalone (e.g. 貸倒引当金)
    for r in rows:
        if r.row_type == "contra_candidate":
            r.row_type = "contra_standalone"

    # 4. Assign sum_parent_path for rows that contribute to sums
    for r in rows:
        if r.row_type in ("item", "contra_standalone"):
            # Direct child of immediate parent
            if len(r.structural_path) >= 2:
                r.sum_parent_path = tuple(r.structural_path[:-1])
            else:
                r.sum_parent_path = tuple(r.structural_path)
        elif r.row_type in ("net", "net_orphan"):
            # If the gross parent was pushed onto the stack, skip it to reach subsection parent
            if len(r.structural_path) >= 3 and r.gross_parent and r.structural_path[-2] == r.gross_parent:
                r.sum_parent_path = tuple(r.structural_path[:-2])
            elif len(r.structural_path) >= 2:
                r.sum_parent_path = tuple(r.structural_path[:-1])
            else:
                r.sum_parent_path = tuple(r.structural_path)
        elif r.row_type == "subtotal":
            # For second-tier subtotals (like 固定資産合計 rolling up subsections)
            if len(r.structural_path) >= 3:
                r.sum_parent_path = tuple(r.structural_path[:-2])
            elif len(r.structural_path) >= 2:
                r.sum_parent_path = tuple(r.structural_path[:-1])
            else:
                r.sum_parent_path = None
        else:
            # gross, contra, section, header do not enter subtotal sums
            r.sum_parent_path = None

    # 5. Value Sign Sanity Check (Verification Flags Only)
    for r in rows:
        non_nil_vals = [
            v.numeric for v in r.values.values()
            if v.numeric is not None and not v.nil
        ]
        if not non_nil_vals:
            continue

        # Item with all negative values
        if r.row_type == "item" and all(v < 0 for v in non_nil_vals):
            r.flags.append("all_values_negative_unexpected")

        # Contra or contra_standalone with any positive value
        if r.row_type in ("contra", "contra_standalone") and any(v > 0 for v in non_nil_vals):
            r.flags.append("contra_has_positive_value")

    return rows
