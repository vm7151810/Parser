#!/usr/bin/env python3
"""
Evaluation Harness for Japanese Financial Table Parsers.

Evaluates parser output JSON against gold reference JSON using an enumerated
discrepancy ledger as the primary output.

Closed Taxonomy of Discrepancies:
  CRITICAL:
    - missing_row: A gold row is completely absent from parser output
    - extra_row: A parser row has no counterpart in gold
    - wrong_metadata: Mismatch in unit, column headers, or column count
  ERROR:
    - wrong_label: Row paired by identical values but has wrong label
    - wrong_printed_value: Cell printed string or parsed numeric mismatch
    - sign_error: Same magnitude, different sign marker or direction (incl. △0 vs 0)
    - nil_zero: Explicit nil dash (－) converted to zero (0), or vice versa
    - nil_missing: Explicit nil dash omitted as null/empty, or vice versa
    - wrong_parent: Hierarchy visual parent mismatch resolved through alignment

Usage:
  python3 eval/evaluate.py --gold eval/gold.json --input output.json [--waivers waivers.json] [--format text|json|markdown]
"""

from __future__ import annotations
import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple, Set


def normalize_label(text: Optional[str]) -> str:
    """Normalize label: NFKC, strip line breaks, tabs, half/full-width spaces."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text)
    norm = re.sub(r"[\s\u3000\n\r\t]+", "", norm)
    return norm


def label_similarity(s1: str, s2: str) -> float:
    """Compute Levenshtein similarity ratio between two normalized strings [0.0, 1.0]."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    m, n = len(s1), len(s2)
    prev = list(range(n + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1] * (n + 1)
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr[j + 1] = min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost)
        prev = curr
    dist = prev[n]
    max_len = max(m, n)
    return 1.0 - (dist / max_len)


def parse_numeric_cell(val: Any) -> Tuple[Optional[float], bool, bool, bool]:
    """
    Parse a cell value into:
      (numeric_value: Optional[float], is_nil: bool, is_negative: bool, is_null: bool)
    """
    if val is None:
        return None, False, False, True

    s = unicodedata.normalize("NFKC", str(val)).strip()
    if not s:
        return None, False, False, True

    # Nil indicators: full-width dash, hyphen, em-dash, horizontal bar
    if s in ("－", "-", "—", "―", "‐", "−"):
        return None, True, False, False

    # Check for negative markers: △, ▲, -, or surrounding parens
    is_neg = False
    clean = s
    if clean.startswith("△") or clean.startswith("▲"):
        is_neg = True
        clean = clean[1:].strip()
    elif clean.startswith("-") or clean.startswith("−"):
        is_neg = True
        clean = clean[1:].strip()
    elif clean.startswith("(") and clean.endswith(")"):
        is_neg = True
        clean = clean[1:-1].strip()

    # Remove thousands separators and commas
    clean = clean.replace(",", "").replace("，", "")

    try:
        num = float(clean)
        if is_neg:
            num = -num
        return num, False, is_neg, False
    except ValueError:
        return None, False, False, False


def extract_numeric_tokens(text: Any) -> List[str]:
    """Extract sequences of digits from text string."""
    if text is None:
        return []
    s = unicodedata.normalize("NFKC", str(text))
    clean = s.replace(",", "").replace("，", "")
    return re.findall(r"\d+", clean)


def sequence_align(gold_labels: List[str], parser_labels: List[str]) -> List[Tuple[Optional[int], Optional[int]]]:
    """
    Global sequence alignment (Needleman-Wunsch) strictly preserving page order.
    Deterministic tie-breaking:
      - When parser has adjacent duplicate rows, earlier occurrence matches gold; later is extra (prefer left on tie with diag).
      - When gold has adjacent duplicate rows, earlier occurrence matches parser; later is missing (prefer up on tie with diag).
    Returns list of aligned (gold_index, parser_index) pairs (0-indexed).
    """
    m = len(gold_labels)
    n = len(parser_labels)

    norm_gold = [normalize_label(g) for g in gold_labels]
    norm_parser = [normalize_label(p) for p in parser_labels]

    GAP_PENALTY = -1.0
    MATCH_SCORE = 2.0
    PARTIAL_SCORE = 1.0
    MISMATCH_PENALTY = -1.5

    dp = [[0.0] * (n + 1) for _ in range(m + 1)]
    backtrack = [[0] * (n + 1) for _ in range(m + 1)]  # 0: diag, 1: up, 2: left

    for i in range(1, m + 1):
        dp[i][0] = i * GAP_PENALTY
        backtrack[i][0] = 1
    for j in range(1, n + 1):
        dp[0][j] = j * GAP_PENALTY
        backtrack[0][j] = 2

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            g_lbl = norm_gold[i - 1]
            p_lbl = norm_parser[j - 1]

            if g_lbl == p_lbl and g_lbl != "":
                sim = MATCH_SCORE
            else:
                sim_ratio = label_similarity(g_lbl, p_lbl)
                if sim_ratio >= 0.8:
                    sim = PARTIAL_SCORE
                else:
                    sim = MISMATCH_PENALTY

            score_diag = dp[i - 1][j - 1] + sim
            score_up = dp[i - 1][j] + GAP_PENALTY
            score_left = dp[i][j - 1] + GAP_PENALTY

            best = max(score_diag, score_up, score_left)
            dp[i][j] = best

            # Deterministic tie-breaking: prefer left over diag, up over diag
            if best == score_left:
                backtrack[i][j] = 2
            elif best == score_up:
                backtrack[i][j] = 1
            else:
                backtrack[i][j] = 0

    # Backtrace
    i, j = m, n
    alignment: List[Tuple[Optional[int], Optional[int]]] = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and backtrack[i][j] == 0:
            alignment.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or backtrack[i][j] == 1):
            alignment.append((i - 1, None))
            i -= 1
        else:
            alignment.append((None, j - 1))
            j -= 1

    alignment.reverse()
    return alignment


def classify_cell_discrepancy(
    g_cell: Any,
    p_cell: Any,
    p_has_col: bool
) -> Optional[Tuple[str, str, Any, Any, dict]]:
    """
    Total classification function for cell kinds:
      Gold: {null, nil, unsigned number, negative number incl. △0}
      Parser: {same + missing}

    Returns:
      None if matched, or (type, severity, expected, actual, detail)
    """
    if not p_has_col:
        # Cell column omitted from parser row
        if g_cell is None:
            return ("wrong_printed_value", "ERROR", None, None, {"numeric_match": False, "reason": "missing_column"})
        g_num, g_nil, g_neg, g_null = parse_numeric_cell(g_cell)
        if g_nil:
            return ("nil_missing", "ERROR", g_cell, None, {"numeric_match": False})
        return ("wrong_printed_value", "ERROR", g_cell, None, {"numeric_match": False})

    # Exact string match (handles both None or identical strings)
    if str(g_cell) == str(p_cell):
        return None

    g_num, g_nil, g_neg, g_null = parse_numeric_cell(g_cell)
    p_num, p_nil, p_neg, p_null = parse_numeric_cell(p_cell)

    # 1. Gold is null (category header cell)
    if g_null:
        if p_null:
            return None
        if p_nil:
            # gold null + parser nil = nil_missing
            return ("nil_missing", "ERROR", None, p_cell, {"numeric_match": False})
        # gold null + parser value = wrong_printed_value
        return ("wrong_printed_value", "ERROR", None, p_cell, {"numeric_match": False})

    # 2. Gold is nil (e.g. "－")
    if g_nil:
        if p_null:
            # gold nil + parser null = nil_missing
            return ("nil_missing", "ERROR", g_cell, None, {"numeric_match": False})
        if p_nil:
            # Different glyph (e.g. "－" vs "-") -> wrong_printed_value with detail numeric_match=true
            return ("wrong_printed_value", "ERROR", g_cell, p_cell, {"numeric_match": True})
        if p_num is not None:
            if abs(p_num) < 1e-4:
                # gold nil + parser zero (0 or △0) = nil_zero
                return ("nil_zero", "ERROR", g_cell, p_cell, {"numeric_match": False})
            return ("wrong_printed_value", "ERROR", g_cell, p_cell, {"numeric_match": False})
        return ("wrong_printed_value", "ERROR", g_cell, p_cell, {"numeric_match": False})

    # 3. Gold is numeric (unsigned or negative)
    if g_num is not None:
        if p_null:
            return ("wrong_printed_value", "ERROR", g_cell, None, {"numeric_match": False})
        if p_nil:
            if abs(g_num) < 1e-4:
                return ("nil_zero", "ERROR", g_cell, p_cell, {"numeric_match": False})
            return ("wrong_printed_value", "ERROR", g_cell, p_cell, {"numeric_match": False})
        if p_num is not None:
            same_magnitude = (abs(abs(g_num) - abs(p_num)) < 1e-4)
            if same_magnitude:
                if g_neg != p_neg:
                    # Same magnitude, different sign marker (incl. △0 vs 0) = sign_error
                    return ("sign_error", "ERROR", g_cell, p_cell, {"numeric_match": abs(g_num - p_num) < 1e-4})
                # Same magnitude, same sign, but string differs
                return ("wrong_printed_value", "ERROR", g_cell, p_cell, {"numeric_match": True})
            # Different magnitude
            return ("wrong_printed_value", "ERROR", g_cell, p_cell, {"numeric_match": False})

    # Fallback
    return ("wrong_printed_value", "ERROR", g_cell, p_cell, {"numeric_match": False})


def entry_sort_key(entry: dict) -> tuple:
    """Sort ledger entries: CRITICAL first, then ERROR; then by gold row / parser row / metadata, then col."""
    sev_order = {"CRITICAL": 0, "ERROR": 1}.get(entry.get("severity", ""), 9)
    eid = entry.get("id", "")
    if eid.startswith("META:"):
        return (sev_order, 0, eid)
    if eid.startswith("EXTRA:P"):
        try:
            p_idx = int(eid.split("P")[1])
        except Exception:
            p_idx = 9999
        return (sev_order, 2, p_idx)
    m = re.match(r"R(\d+)(?::(.+))?", eid)
    if m:
        r_idx = int(m.group(1))
        col_str = m.group(2) or ""
        col_m = re.match(r"C(\d+)", col_str)
        col_val = int(col_m.group(1)) if col_m else 0
        return (sev_order, 1, r_idx, col_val, col_str)
    return (sev_order, 3, eid)


def evaluate_table(
    gold_data: dict,
    parser_data: dict,
    waivers: Optional[List[dict]] = None
) -> dict:
    """
    Core evaluation logic comparing parser data against gold reference.
    Returns structured report dictionary containing discrepancy ledger, rates, and diagnostics.
    """
    if waivers is None:
        waivers = []

    # Validate parser input basic schema
    if "rows" not in parser_data or not isinstance(parser_data["rows"], list):
        raise ValueError("Parser data missing 'rows' array.")

    gold_rows = gold_data.get("rows", [])
    parser_rows = parser_data.get("rows", [])

    eval_flags = gold_data.get("eval_flags", {})
    score_hierarchy = eval_flags.get("score_hierarchy", True)

    gold_labels = [r.get("label", "") for r in gold_rows]
    parser_labels = [r.get("label", "") for r in parser_rows]

    ledger: List[dict] = []

    # =================================================================
    # 1. Metadata Verification (wrong_metadata, CRITICAL)
    # =================================================================
    gold_meta = gold_data.get("metadata") or gold_data.get("meta") or {}
    parser_meta = parser_data.get("metadata") or parser_data.get("meta") or {}
    if not parser_meta and "unit" in parser_data:
        parser_meta = parser_data

    # 1a. Unit
    gold_unit = gold_meta.get("unit")
    parser_unit = parser_meta.get("unit") if parser_meta else parser_data.get("unit")
    if gold_unit is not None:
        if normalize_label(gold_unit) != normalize_label(parser_unit):
            ledger.append({
                "id": "META:unit",
                "type": "wrong_metadata",
                "severity": "CRITICAL",
                "expected": gold_unit,
                "actual": parser_unit,
                "detail": {},
                "waived": False,
                "waiver_reason": None
            })

    # 1b. Column Headers & Column Count
    gold_headers = gold_meta.get("column_headers", [])
    parser_headers = parser_meta.get("column_headers", [])
    if not parser_headers and "column_headers" in parser_data:
        parser_headers = parser_data["column_headers"]

    num_gold_cols = len(gold_headers)
    num_parser_cols = len(parser_headers)
    common_cols = min(num_gold_cols, num_parser_cols) if (num_gold_cols > 0 and num_parser_cols > 0) else max(num_gold_cols, num_parser_cols)

    if num_gold_cols > 0 and num_parser_cols > 0 and num_gold_cols != num_parser_cols:
        ignored = list(range(common_cols + 1, max(num_gold_cols, num_parser_cols) + 1))
        ledger.append({
            "id": "META:columns",
            "type": "wrong_metadata",
            "severity": "CRITICAL",
            "expected": num_gold_cols,
            "actual": num_parser_cols,
            "detail": {
                "gold_columns": gold_headers,
                "parser_columns": parser_headers,
                "ignored_columns": ignored
            },
            "waived": False,
            "waiver_reason": None
        })

    # Header texts for common columns
    for c_i in range(min(num_gold_cols, num_parser_cols)):
        g_h = gold_headers[c_i]
        p_h = parser_headers[c_i]
        if normalize_label(g_h) != normalize_label(p_h):
            ledger.append({
                "id": f"META:col{c_i + 1}",
                "type": "wrong_metadata",
                "severity": "CRITICAL",
                "expected": g_h,
                "actual": p_h,
                "detail": {},
                "waived": False,
                "waiver_reason": None
            })

    # =================================================================
    # 2. Sequence Alignment & Gap Pairing (wrong_label)
    # =================================================================
    raw_alignment = sequence_align(gold_labels, parser_labels)

    # Decompose alignment into anchors and gaps
    matched_pairs: List[Tuple[int, int]] = []
    gold_to_parser_map: Dict[int, int] = {}
    parser_to_gold_map: Dict[int, int] = {}

    # Identify anchored matches where label matches
    is_anchor: List[bool] = []
    for g_idx, p_idx in raw_alignment:
        if g_idx is not None and p_idx is not None:
            g_lbl = normalize_label(gold_labels[g_idx])
            p_lbl = normalize_label(parser_labels[p_idx])
            if g_lbl == p_lbl and g_lbl != "":
                is_anchor.append(True)
                continue
        is_anchor.append(False)

    # Process gaps between anchors
    gap_g_indices: List[int] = []
    gap_p_indices: List[int] = []

    unmatched_gold_indices: List[int] = []
    unmatched_parser_indices: List[int] = []

    def flush_gap(gaps_g: List[int], gaps_p: List[int]):
        """Pair unmatched rows in gap ONLY if identical non-empty value tuples."""
        paired_p: Set[int] = set()
        for g_i in gaps_g:
            g_row = gold_rows[g_i]
            g_vals = g_row.get("values", [])
            # Must be non-empty (at least one non-null value)
            has_val = any(v is not None for v in g_vals)

            found_p = None
            if has_val:
                for p_i in gaps_p:
                    if p_i in paired_p:
                        continue
                    p_row = parser_rows[p_i]
                    p_vals = p_row.get("values", [])
                    if tuple(g_vals) == tuple(p_vals):
                        found_p = p_i
                        break

            if found_p is not None:
                paired_p.add(found_p)
                matched_pairs.append((g_i, found_p))
                gold_to_parser_map[g_i] = found_p
                parser_to_gold_map[found_p] = g_i
                ledger.append({
                    "id": f"R{g_i + 1}:label",
                    "type": "wrong_label",
                    "severity": "ERROR",
                    "expected": g_row.get("label"),
                    "actual": parser_rows[found_p].get("label"),
                    "detail": {
                        "gold_row_index": g_i + 1,
                        "parser_row_index": found_p + 1,
                        "values": g_vals
                    },
                    "waived": False,
                    "waiver_reason": None
                })
            else:
                unmatched_gold_indices.append(g_i)

        for p_i in gaps_p:
            if p_i not in paired_p:
                unmatched_parser_indices.append(p_i)

    for idx, (g_idx, p_idx) in enumerate(raw_alignment):
        if is_anchor[idx]:
            flush_gap(gap_g_indices, gap_p_indices)
            gap_g_indices = []
            gap_p_indices = []
            matched_pairs.append((g_idx, p_idx))
            gold_to_parser_map[g_idx] = p_idx
            parser_to_gold_map[p_idx] = g_idx
        else:
            if g_idx is not None:
                gap_g_indices.append(g_idx)
            if p_idx is not None:
                gap_p_indices.append(p_idx)
    flush_gap(gap_g_indices, gap_p_indices)

    # Missing Gold Rows (missing_row, CRITICAL)
    missing_gold_row_indices_set = set(unmatched_gold_indices)
    for g_idx in unmatched_gold_indices:
        g_row = gold_rows[g_idx]
        g_row_num = g_row.get("row_index", g_idx + 1)
        subsumed_cells = len(g_row.get("values", []))
        orphaned = [
            child.get("row_index", c_i + 1)
            for c_i, child in enumerate(gold_rows)
            if child.get("parent_index") == g_row_num
        ]
        ledger.append({
            "id": f"R{g_row_num}:row",
            "type": "missing_row",
            "severity": "CRITICAL",
            "expected": {
                "row_index": g_row_num,
                "label": g_row.get("label")
            },
            "actual": None,
            "detail": {
                "subsumed_cells": subsumed_cells,
                "orphaned_children": orphaned
            },
            "waived": False,
            "waiver_reason": None
        })

    # Extra Parser Rows (extra_row, CRITICAL)
    for p_idx in unmatched_parser_indices:
        p_row = parser_rows[p_idx]
        ledger.append({
            "id": f"EXTRA:P{p_idx + 1}",
            "type": "extra_row",
            "severity": "CRITICAL",
            "expected": None,
            "actual": {
                "parser_row_index": p_idx + 1,
                "label": p_row.get("label")
            },
            "detail": {},
            "waived": False,
            "waiver_reason": None
        })

    # =================================================================
    # 3. Hierarchy Verification (wrong_parent, ERROR)
    # =================================================================
    correct_hierarchy = 0
    total_hierarchy_candidates = 0

    has_explicit_row_index = any("row_index" in r for r in parser_rows)
    p_row_idx_map = (
        {r["row_index"]: i for i, r in enumerate(parser_rows) if "row_index" in r}
        if has_explicit_row_index else {}
    )

    if score_hierarchy:
        for g_idx, p_idx in matched_pairs:
            g_row = gold_rows[g_idx]
            p_row = parser_rows[p_idx]

            g_parent_lbl = normalize_label(g_row.get("parent_label"))
            g_parent_idx = g_row.get("parent_index")  # 1-indexed

            # If gold row has no parent (root row)
            if not g_parent_lbl and g_parent_idx is None:
                continue

            total_hierarchy_candidates += 1

            # Check if gold parent was an unaligned / missing row
            # If gold parent is missing, child produces NO wrong_parent (it is orphaned child)
            if g_parent_idx is not None and (g_parent_idx - 1) in missing_gold_row_indices_set:
                correct_hierarchy += 1
                continue

            # Resolve parser's parent_index to gold row through alignment
            p_parent_idx = p_row.get("parent_index")  # 1-indexed
            p_parent_lbl = normalize_label(p_row.get("parent_label"))

            if p_parent_idx is not None:
                if has_explicit_row_index and p_parent_idx in p_row_idx_map:
                    p_parent_zero = p_row_idx_map[p_parent_idx]
                else:
                    p_parent_zero = p_parent_idx - 1 if (1 <= p_parent_idx <= len(parser_rows)) else None

                if p_parent_zero is not None:
                    resolved_gold_parent_zero = parser_to_gold_map.get(p_parent_zero)
                    actual_gold_parent_idx = (resolved_gold_parent_zero + 1) if resolved_gold_parent_zero is not None else None
                else:
                    actual_gold_parent_idx = None
            else:
                actual_gold_parent_idx = None

            parent_match = (
                (g_parent_lbl == p_parent_lbl) and
                (actual_gold_parent_idx == g_parent_idx)
            )

            if parent_match:
                correct_hierarchy += 1
            else:
                g_row_num = g_row.get("row_index", g_idx + 1)
                ledger.append({
                    "id": f"R{g_row_num}:parent",
                    "type": "wrong_parent",
                    "severity": "ERROR",
                    "expected": {
                        "parent_index": g_parent_idx,
                        "parent_label": g_row.get("parent_label")
                    },
                    "actual": {
                        "parent_index": actual_gold_parent_idx,
                        "parent_label": p_row.get("parent_label")
                    },
                    "detail": {
                        "parser_parent_index": p_parent_idx
                    },
                    "waived": False,
                    "waiver_reason": None
                })

        hierarchy_accuracy = correct_hierarchy / total_hierarchy_candidates if total_hierarchy_candidates > 0 else 1.0
    else:
        hierarchy_accuracy = None

    # =================================================================
    # 4. Cell Verification
    # =================================================================
    num_cols_to_compare = min(len(gold_headers), len(parser_headers)) if (gold_headers and parser_headers) else 2

    val_cells_total = 0
    val_cells_exact_match = 0
    val_cells_numeric_match = 0
    no_val_cells_total = 0
    no_val_cells_match = 0

    for g_idx, g_row in enumerate(gold_rows):
        g_vals = g_row.get("values", [])
        p_idx = gold_to_parser_map.get(g_idx)
        p_row = parser_rows[p_idx] if p_idx is not None else None
        p_vals = p_row.get("values", []) if p_row is not None else None

        for c_i in range(num_cols_to_compare):
            g_cell = g_vals[c_i] if c_i < len(g_vals) else None
            is_val_cell = (g_cell is not None)

            if is_val_cell:
                val_cells_total += 1
            else:
                no_val_cells_total += 1

            if p_idx is None:
                # Subsumed under missing_row! No duplicate cell entry emitted.
                continue

            p_has_col = (p_vals is not None and c_i < len(p_vals))
            p_cell = p_vals[c_i] if p_has_col else None

            # Rate statistics
            exact = (str(g_cell) == str(p_cell))
            if is_val_cell:
                if exact:
                    val_cells_exact_match += 1
                g_num, g_nil, g_neg, _ = parse_numeric_cell(g_cell)
                p_num, p_nil, p_neg, _ = parse_numeric_cell(p_cell)
                if g_nil and p_nil:
                    val_cells_numeric_match += 1
                elif g_num is not None and p_num is not None and not p_nil and abs(g_num - p_num) < 1e-4 and g_neg == p_neg:
                    val_cells_numeric_match += 1
            else:
                if exact and p_cell is None:
                    no_val_cells_match += 1

            disc = classify_cell_discrepancy(g_cell, p_cell, p_has_col)
            if disc is not None:
                disc_type, disc_sev, expected, actual, detail = disc
                g_row_num = g_row.get("row_index", g_idx + 1)
                ledger.append({
                    "id": f"R{g_row_num}:C{c_i + 1}",
                    "type": disc_type,
                    "severity": disc_sev,
                    "expected": expected,
                    "actual": actual,
                    "detail": detail,
                    "waived": False,
                    "waiver_reason": None
                })

    # Value cell precision & recall
    parser_val_cells_count = sum(
        1 for pr in parser_rows for c in pr.get("values", [])[:num_cols_to_compare] if c is not None
    )
    val_exact_acc = val_cells_exact_match / val_cells_total if val_cells_total > 0 else 1.0
    val_numeric_acc = val_cells_numeric_match / val_cells_total if val_cells_total > 0 else 1.0
    val_cell_precision = val_cells_exact_match / parser_val_cells_count if parser_val_cells_count > 0 else 1.0
    val_cell_recall = val_exact_acc
    val_cell_f1 = (2 * val_cell_precision * val_cell_recall / (val_cell_precision + val_cell_recall)) if (val_cell_precision + val_cell_recall) > 0 else 0.0

    # No-value cell accuracy
    no_val_acc = no_val_cells_match / no_val_cells_total if no_val_cells_total > 0 else 1.0

    # Row metrics
    num_gold = len(gold_rows)
    num_parser = len(parser_rows)
    num_matched = len(matched_pairs)
    row_recall = num_matched / num_gold if num_gold > 0 else 1.0
    row_precision = num_matched / num_parser if num_parser > 0 else 1.0
    row_f1 = (2 * row_precision * row_recall / (row_precision + row_recall)) if (row_precision + row_recall) > 0 else 0.0

    # Multiset Token Match
    gold_tokens = Counter(t for r in gold_rows for val in r.get("values", []) for t in extract_numeric_tokens(val))
    parser_tokens = Counter(t for r in parser_rows for val in r.get("values", []) for t in extract_numeric_tokens(val))
    intersection_count = sum((gold_tokens & parser_tokens).values())
    total_gold_token_count = sum(gold_tokens.values())
    total_parser_token_count = sum(parser_tokens.values())
    token_recall = intersection_count / total_gold_token_count if total_gold_token_count > 0 else 1.0
    token_precision = intersection_count / total_parser_token_count if total_parser_token_count > 0 else 1.0
    token_f1 = (2 * token_precision * token_recall / (token_precision + token_recall)) if (token_precision + token_recall) > 0 else 0.0

    # =================================================================
    # 5. Diagnostic Accounting Checks (Non-gating, separate section)
    # =================================================================
    checks_def = gold_data.get("checks", [])
    accounting_results: List[dict] = []

    for check in checks_def:
        check_id = check.get("check_id")
        check_name = check.get("name")
        target_g_idx = check.get("target_row_index") - 1
        addends = check.get("addend_rows", [])
        num_terms = check.get("tolerance_terms", len(addends))
        tolerance = max(1, math.ceil(num_terms / 2.0))
        rationale = check.get("tolerance_rationale", "")

        target_p_idx = gold_to_parser_map.get(target_g_idx)

        for c in range(num_cols_to_compare):
            col_name = gold_headers[c] if c < len(gold_headers) else f"Col {c+1}"

            if target_p_idx is None:
                accounting_results.append({
                    "check_id": check_id,
                    "name": check_name,
                    "column": col_name,
                    "status": "UNALIGNED_TARGET",
                    "target_val": None,
                    "computed_sum": None,
                    "diff": None,
                    "tolerance": tolerance,
                    "rationale": rationale,
                    "passed": False
                })
                continue

            target_vals = parser_rows[target_p_idx].get("values", [])
            target_raw = target_vals[c] if c < len(target_vals) else None
            target_val, _, _, _ = parse_numeric_cell(target_raw)

            computed_sum = 0.0
            missing_addend = False

            for addend in addends:
                addend_g_idx = addend.get("row_index") - 1
                sign = addend.get("sign", 1)
                addend_p_idx = gold_to_parser_map.get(addend_g_idx)

                if addend_p_idx is None:
                    missing_addend = True
                    break

                addend_vals = parser_rows[addend_p_idx].get("values", [])
                addend_raw = addend_vals[c] if c < len(addend_vals) else None
                val, is_nil, _, _ = parse_numeric_cell(addend_raw)

                if is_nil:
                    computed_sum += 0.0
                elif val is not None:
                    computed_sum += sign * val

            if missing_addend or target_val is None:
                accounting_results.append({
                    "check_id": check_id,
                    "name": check_name,
                    "column": col_name,
                    "status": "MISSING_ADDEND_OR_TARGET",
                    "target_val": target_val,
                    "computed_sum": computed_sum,
                    "diff": None,
                    "tolerance": tolerance,
                    "rationale": rationale,
                    "passed": False
                })
                continue

            diff = abs(computed_sum - target_val)
            if diff < 1e-4:
                status = "EXACT_MATCH"
                passed = True
            elif diff <= tolerance + 1e-4:
                status = "SOURCE_ROUNDING"
                passed = True
            else:
                status = "INCONSISTENCY"
                passed = False

            accounting_results.append({
                "check_id": check_id,
                "name": check_name,
                "column": col_name,
                "status": status,
                "target_val": target_val,
                "computed_sum": computed_sum,
                "diff": diff,
                "tolerance": tolerance,
                "rationale": rationale,
                "passed": passed
            })

    # =================================================================
    # 6. Apply Waivers & Match Validation
    # =================================================================
    used_waiver_indices: Set[int] = set()

    for entry in ledger:
        for w_i, w in enumerate(waivers):
            # A waiver matches if id, type, and actual all match
            if (
                w.get("id") == entry["id"] and
                w.get("type") == entry["type"] and
                str(w.get("actual")) == str(entry["actual"])
            ):
                entry["waived"] = True
                entry["waiver_reason"] = w.get("reason")
                used_waiver_indices.add(w_i)
                break

    stale_waivers = [w for w_i, w in enumerate(waivers) if w_i not in used_waiver_indices]

    # Sort ledger deterministically: CRITICAL then ERROR, then by stable ID
    ledger.sort(key=entry_sort_key)

    unwaived_count = sum(1 for e in ledger if not e["waived"])
    waived_count = sum(1 for e in ledger if e["waived"])
    critical_count = sum(1 for e in ledger if e["severity"] == "CRITICAL" and not e["waived"])
    error_count = sum(1 for e in ledger if e["severity"] == "ERROR" and not e["waived"])

    exit_code = 1 if unwaived_count > 0 else 0
    status_str = "FAIL" if exit_code == 1 else "PASS"

    report = {
        "status": status_str,
        "exit_code": exit_code,
        "summary": {
            "total_discrepancies": len(ledger),
            "unwaived": unwaived_count,
            "waived": waived_count,
            "critical": critical_count,
            "error": error_count,
            "gold_rows": num_gold,
            "parser_rows": num_parser,
            "aligned_rows": num_matched,
        },
        "ledger": ledger,
        "stale_waivers": stale_waivers,
        "diagnostics": {
            "total_accounting_checks": len(accounting_results),
            "passed_checks": sum(1 for c in accounting_results if c["passed"]),
            "exact_checks": sum(1 for c in accounting_results if c["status"] == "EXACT_MATCH"),
            "rounding_checks": sum(1 for c in accounting_results if c["status"] == "SOURCE_ROUNDING"),
            "failed_checks": sum(1 for c in accounting_results if not c["passed"]),
            "details": accounting_results
        },
        "rates": {
            "row_precision": row_precision,
            "row_recall": row_recall,
            "row_f1": row_f1,
            "score_hierarchy": score_hierarchy,
            "hierarchy_accuracy": hierarchy_accuracy,
            "value_cell_exact_accuracy": val_exact_acc,
            "value_cell_numeric_accuracy": val_numeric_acc,
            "value_cell_precision": val_cell_precision,
            "value_cell_recall": val_cell_recall,
            "value_cell_f1": val_cell_f1,
            "no_value_cell_accuracy": no_val_acc,
            "token_precision": token_precision,
            "token_recall": token_recall,
            "token_f1": token_f1,
        }
    }

    return report


def format_text_report(report: dict) -> str:
    """Format human-readable text report: Ledger -> Stale Waivers -> Diagnostics -> Rates footer."""
    out = []
    out.append("=====================================================================")
    out.append("      JAPANESE FINANCIAL TABLE PARSER EVALUATION REPORT              ")
    out.append("=====================================================================")

    ledger = report["ledger"]
    s = report["summary"]
    stale = report.get("stale_waivers", [])
    d = report["diagnostics"]
    r = report["rates"]

    out.append(f" STATUS: {report['status']} (Exit Code: {report['exit_code']})")
    out.append(f" Total Discrepancies: {s['total_discrepancies']} | Unwaived: {s['unwaived']} (Critical: {s['critical']}, Error: {s['error']}) | Waived: {s['waived']}")
    out.append("=====================================================================")
    out.append(" 1. DISCREPANCY LEDGER:")

    if not ledger:
        out.append("    (Empty ledger - 100% extraction match. PASSED)")
    else:
        for idx, entry in enumerate(ledger, 1):
            tag = "[WAIVED]  " if entry["waived"] else "[UNWAIVED]"
            out.append(f"    {idx:02d}. {tag} {entry['id']:<14} | Type: {entry['type']:<20} | Severity: {entry['severity']}")
            out.append(f"        Expected: {json.dumps(entry['expected'], ensure_ascii=False)}")
            out.append(f"        Actual:   {json.dumps(entry['actual'], ensure_ascii=False)}")
            if entry.get("detail"):
                out.append(f"        Detail:   {json.dumps(entry['detail'], ensure_ascii=False)}")
            if entry["waived"]:
                out.append(f"        Reason:   {entry.get('waiver_reason')}")

    if stale:
        out.append("---------------------------------------------------------------------")
        out.append(f" WARNING: STALE / UNMATCHED WAIVERS ({len(stale)} waivers):")
        for w in stale:
            out.append(f"    - ID: {w.get('id')} | Type: {w.get('type')} | Actual: {w.get('actual')} | Reason: {w.get('reason')}")

    out.append("=====================================================================")
    out.append(" 2. DIAGNOSTICS: ACCOUNTING CONSISTENCY CHECKS (Non-Gating)")
    out.append(f" Total Checks: {d['total_accounting_checks']} | Passed: {d['passed_checks']} (Exact: {d['exact_checks']}, Rounding: {d['rounding_checks']}) | Failed: {d['failed_checks']}")
    if d["failed_checks"] > 0:
        for c in d["details"]:
            if not c["passed"]:
                out.append(f"    [!] Check '{c['name']}' ({c['column']}): Status {c['status']}, Diff={c.get('diff')}, Tolerance={c.get('tolerance')}")

    out.append("=====================================================================")
    hier_str = f"{r['hierarchy_accuracy']:.2%}" if r["score_hierarchy"] else "N/A"
    rates_line = (
        f"Rates: Row F1={r['row_f1']:.2%} | "
        f"Hierarchy={hier_str} | "
        f"Value Cell Exact={r['value_cell_exact_accuracy']:.2%} (Numeric={r['value_cell_numeric_accuracy']:.2%}) | "
        f"Token F1={r['token_f1']:.2%}"
    )
    out.append(rates_line)
    out.append("=====================================================================")

    return "\n".join(out)


def format_markdown_report(report: dict) -> str:
    """Format markdown report: Ledger -> Stale Waivers -> Diagnostics -> Rates footer."""
    ledger = report["ledger"]
    s = report["summary"]
    stale = report.get("stale_waivers", [])
    d = report["diagnostics"]
    r = report["rates"]

    lines = []
    lines.append("# Parser Evaluation Discrepancy Ledger")
    lines.append("")
    lines.append(f"**Status:** `{report['status']}` (Exit Code `{report['exit_code']}`)")
    lines.append(f"- **Total Discrepancies:** {s['total_discrepancies']} (Unwaived: **{s['unwaived']}**, Waived: {s['waived']})")
    lines.append(f"- **Unwaived by Severity:** Critical: **{s['critical']}**, Error: **{s['error']}**")
    lines.append("")
    lines.append("## 1. Discrepancy Ledger")
    lines.append("")

    if not ledger:
        lines.append("*(Discrepancy ledger is empty — all rows, hierarchy, cells, and metadata match perfectly.)*")
    else:
        lines.append("| Status | ID | Type | Severity | Expected | Actual | Details / Waiver Reason |")
        lines.append("|---|---|---|---|---|---|---|")
        for entry in ledger:
            st = "**UNWAIVED**" if not entry["waived"] else "*WAIVED*"
            exp = json.dumps(entry["expected"], ensure_ascii=False)
            act = json.dumps(entry["actual"], ensure_ascii=False)
            det = []
            if entry.get("detail"):
                det.append(f"`{json.dumps(entry['detail'], ensure_ascii=False)}`")
            if entry["waived"]:
                det.append(f"**Waiver Reason:** {entry.get('waiver_reason')}")
            det_str = "<br>".join(det)
            lines.append(f"| {st} | `{entry['id']}` | `{entry['type']}` | `{entry['severity']}` | `{exp}` | `{act}` | {det_str} |")

    if stale:
        lines.append("")
        lines.append("## Stale / Unmatched Waivers")
        lines.append("> [!WARNING]")
        lines.append(f"> Found {len(stale)} waiver(s) that did not match any active ledger entries:")
        for w in stale:
            lines.append(f"- ID: `{w.get('id')}` | Type: `{w.get('type')}` | Actual: `{w.get('actual')}` | Reason: *{w.get('reason')}*")

    lines.append("")
    lines.append("## 2. Diagnostics: Accounting Consistency (Non-Gating)")
    lines.append(f"- **Total Checks:** {d['total_accounting_checks']}")
    lines.append(f"- **Passed:** {d['passed_checks']} (Exact: {d['exact_checks']}, Source Rounding: {d['rounding_checks']})")
    lines.append(f"- **Failed:** {d['failed_checks']}")

    lines.append("")
    lines.append("---")
    hier_str = f"{r['hierarchy_accuracy']:.2%}" if r["score_hierarchy"] else "N/A"
    lines.append(
        f"**Rates:** Row F1: {r['row_f1']:.2%} | "
        f"Hierarchy: {hier_str} | "
        f"Value Cell Exact: {r['value_cell_exact_accuracy']:.2%} (Numeric: {r['value_cell_numeric_accuracy']:.2%}) | "
        f"Token F1: {r['token_f1']:.2%}"
    )

    return "\n".join(lines)


def load_waivers(waiver_path: str) -> List[dict]:
    """Load and validate waivers JSON file. Exits with code 2 on malformed file."""
    try:
        with open(waiver_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[HARNESS ERROR] Could not read waiver file '{waiver_path}': {e}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(data, list):
        print(f"[HARNESS ERROR] Waiver file '{waiver_path}' must contain a JSON list of waiver objects.", file=sys.stderr)
        sys.exit(2)

    for idx, w in enumerate(data):
        if not isinstance(w, dict):
            print(f"[HARNESS ERROR] Waiver entry #{idx+1} is not an object.", file=sys.stderr)
            sys.exit(2)
        if "id" not in w or "type" not in w or "actual" not in w:
            print(f"[HARNESS ERROR] Waiver entry #{idx+1} missing required keys ('id', 'type', 'actual').", file=sys.stderr)
            sys.exit(2)
        reason = w.get("reason")
        if not reason or not isinstance(reason, str) or not reason.strip():
            print(f"[HARNESS ERROR] Waiver entry '{w.get('id')}' missing non-empty written reason.", file=sys.stderr)
            sys.exit(2)

    return data


def main():
    parser = argparse.ArgumentParser(description="Japanese Financial Statement Table Evaluation Harness")
    parser.add_argument("--gold", required=True, help="Path to gold reference JSON")
    parser.add_argument("--input", required=True, help="Path to parser output JSON")
    parser.add_argument("--waivers", default=None, help="Path to waivers JSON file")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text", help="Output report format")

    # Removed rate-based flags: detect and reject with exit code 2
    parser.add_argument("--fail-under-cell", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--fail-under-row", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--fail-under-hierarchy", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--fail-under-numeric-token", type=float, default=None, help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Reject deprecated/removed fail-under flags
    if any(f is not None for f in (args.fail_under_cell, args.fail_under_row, args.fail_under_hierarchy, args.fail_under_numeric_token)):
        print(
            "[HARNESS ERROR] Rate-based pass/fail gates (--fail-under-*) have been removed. "
            "Pass/fail is now strictly governed by the discrepancy ledger (exit 0 on empty/waived, exit 1 on unwaived).",
            file=sys.stderr
        )
        sys.exit(2)

    try:
        with open(args.gold, "r", encoding="utf-8") as f:
            gold_data = json.load(f)
    except Exception as e:
        print(f"[HARNESS ERROR] Could not read gold file '{args.gold}': {e}", file=sys.stderr)
        sys.exit(2)

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            parser_data = json.load(f)
    except Exception as e:
        print(f"[HARNESS ERROR] Could not read input file '{args.input}': {e}", file=sys.stderr)
        sys.exit(2)

    waivers: List[dict] = []
    if args.waivers:
        waivers = load_waivers(args.waivers)

    try:
        report = evaluate_table(gold_data, parser_data, waivers=waivers)
    except Exception as e:
        print(f"[HARNESS ERROR] Evaluation failed due to invalid schema: {e}", file=sys.stderr)
        sys.exit(2)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.format == "markdown":
        print(format_markdown_report(report))
    else:
        print(format_text_report(report))

    sys.exit(report["exit_code"])


if __name__ == "__main__":
    main()
