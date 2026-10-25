#!/usr/bin/env python3
"""
Evaluation Harness for Japanese Financial Table Parsers.

Evaluates parser output JSON against gold reference JSON.
Metrics:
  1. Row Match (Sequence Alignment preserving page order)
  2. Hierarchy Accuracy (Parent match on visual indentation / subtotal closing)
  3. Cell Accuracy (Separately reported for Value cells [74] and No-Value cells [12])
  4. Numeric-Token Coverage (Multiset Counter match)
Diagnostics:
  - Accounting Consistency Checks (with scaled rounding tolerance; NOT accuracy)

Usage:
  python3 eval/evaluate.py --gold eval/gold.json --input output.json
"""

from __future__ import annotations
import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def normalize_label(text: Optional[str]) -> str:
    """Normalize label: NFKC, strip line breaks, tabs, half/full-width spaces."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text)
    # Remove all whitespace, line breaks, full-width spaces
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

            if best == score_diag:
                backtrack[i][j] = 0
            elif best == score_up:
                backtrack[i][j] = 1
            else:
                backtrack[i][j] = 2

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


def evaluate_table(gold_data: dict, parser_data: dict) -> dict:
    """
    Core evaluation logic comparing parser data against gold reference.
    """
    gold_rows = gold_data.get("rows", [])
    parser_rows = parser_data.get("rows", [])

    eval_flags = gold_data.get("eval_flags", {})
    score_hierarchy = eval_flags.get("score_hierarchy", True)

    gold_labels = [r.get("label", "") for r in gold_rows]
    parser_labels = [r.get("label", "") for r in parser_rows]

    # 1. Row Sequence Alignment
    alignment = sequence_align(gold_labels, parser_labels)

    matched_pairs: List[Tuple[int, int]] = []
    unmatched_gold_indices: List[int] = []
    unmatched_parser_indices: List[int] = []

    gold_to_parser_map: Dict[int, int] = {}
    parser_to_gold_map: Dict[int, int] = {}

    for g_idx, p_idx in alignment:
        if g_idx is not None and p_idx is not None:
            g_lbl = normalize_label(gold_labels[g_idx])
            p_lbl = normalize_label(parser_labels[p_idx])
            if g_lbl == p_lbl and g_lbl != "":
                matched_pairs.append((g_idx, p_idx))
                gold_to_parser_map[g_idx] = p_idx
                parser_to_gold_map[p_idx] = g_idx
            else:
                unmatched_gold_indices.append(g_idx)
                unmatched_parser_indices.append(p_idx)
        elif g_idx is not None:
            unmatched_gold_indices.append(g_idx)
        elif p_idx is not None:
            unmatched_parser_indices.append(p_idx)

    num_gold = len(gold_rows)
    num_parser = len(parser_rows)
    num_matched = len(matched_pairs)

    row_recall = num_matched / num_gold if num_gold > 0 else 1.0
    row_precision = num_matched / num_parser if num_parser > 0 else 1.0
    row_f1 = (2 * row_precision * row_recall / (row_precision + row_recall)) if (row_precision + row_recall) > 0 else 0.0

    # 2. Hierarchy Accuracy (enforce 1-indexed parent_index)
    correct_hierarchy = 0
    total_hierarchy_candidates = 0
    hierarchy_details: List[dict] = []

    if score_hierarchy:
        for g_idx, p_idx in matched_pairs:
            g_row = gold_rows[g_idx]
            p_row = parser_rows[p_idx]

            g_parent_lbl = normalize_label(g_row.get("parent_label"))
            p_parent_lbl = normalize_label(p_row.get("parent_label"))

            if g_parent_lbl:
                total_hierarchy_candidates += 1
                parent_match = False

                # Check label match
                if g_parent_lbl == p_parent_lbl:
                    # Enforce strict 1-indexed parent_index if provided
                    p_parent_idx = p_row.get("parent_index")
                    g_parent_idx = g_row.get("parent_index")

                    if p_parent_idx is not None and g_parent_idx is not None:
                        # Gold parent_index is 1-indexed -> 0-indexed is g_parent_idx - 1
                        expected_parser_idx = gold_to_parser_map.get(g_parent_idx - 1)
                        # Parser parent_index is 1-indexed -> 0-indexed is p_parent_idx - 1
                        p_parent_idx_zero = p_parent_idx - 1
                        if p_parent_idx_zero == expected_parser_idx:
                            parent_match = True
                        else:
                            parent_match = False
                    else:
                        parent_match = True

                if parent_match:
                    correct_hierarchy += 1
                else:
                    hierarchy_details.append({
                        "row_index": g_row.get("row_index", g_idx + 1),
                        "label": g_row.get("label"),
                        "expected_parent": g_row.get("parent_label"),
                        "expected_parent_index": g_row.get("parent_index"),
                        "parser_parent": p_row.get("parent_label"),
                        "parser_parent_index": p_row.get("parent_index"),
                    })

        hierarchy_accuracy = correct_hierarchy / total_hierarchy_candidates if total_hierarchy_candidates > 0 else 1.0
    else:
        hierarchy_accuracy = None

    # 3. Cell Accuracy (Split into Value Cells and No-Value Cells)
    # Number of columns based on gold headers or first row
    num_cols = len(gold_data.get("metadata", {}).get("column_headers", []))
    if num_cols == 0 and gold_rows:
        num_cols = len(gold_rows[0].get("values", []))

    val_cells_total = 0
    val_cells_exact_match = 0
    val_cells_numeric_match = 0

    no_val_cells_total = 0
    no_val_cells_match = 0

    cell_discrepancies: List[dict] = []

    # Count parser value cells for precision calculation
    parser_val_cells_count = 0
    for p_r in parser_rows:
        p_v_list = p_r.get("values", [])
        for c_i in range(num_cols):
            c_val = p_v_list[c_i] if c_i < len(p_v_list) else None
            if c_val is not None:
                parser_val_cells_count += 1

    for g_idx, g_row in enumerate(gold_rows):
        g_vals = g_row.get("values", [])
        p_idx = gold_to_parser_map.get(g_idx)

        # Guard: if row is unaligned, p_vals is None
        p_vals = parser_rows[p_idx].get("values", []) if p_idx is not None else None

        for col_idx in range(num_cols):
            g_cell = g_vals[col_idx] if col_idx < len(g_vals) else None
            g_is_value_cell = (g_cell is not None)

            g_num, g_nil, g_neg, g_null = parse_numeric_cell(g_cell)

            if p_vals is not None:
                p_cell = p_vals[col_idx] if col_idx < len(p_vals) else None
                p_num, p_nil, p_neg, p_null = parse_numeric_cell(p_cell)
            else:
                p_cell = None
                p_num, p_nil, p_neg, p_null = None, False, False, True

            # If row is unaligned, all cells fail automatically
            row_aligned = (p_idx is not None)

            if g_is_value_cell:
                val_cells_total += 1

                exact_match = False
                numeric_match = False

                if row_aligned:
                    # Exact string match
                    if str(g_cell) == str(p_cell):
                        exact_match = True

                    # Numeric match
                    if g_nil:
                        # Nil must match ONLY nil: "－" vs "0" must fail!
                        if p_nil:
                            numeric_match = True
                    elif g_num is not None:
                        # Must be a number and not a nil marker, matching sign and value
                        if p_num is not None and not p_nil:
                            if abs(g_num - p_num) < 1e-4 and g_neg == p_neg:
                                numeric_match = True

                if exact_match:
                    val_cells_exact_match += 1
                if numeric_match:
                    val_cells_numeric_match += 1

                if not exact_match or not numeric_match:
                    cell_discrepancies.append({
                        "row_index": g_row.get("row_index", g_idx + 1),
                        "label": g_row.get("label"),
                        "column_index": col_idx + 1,
                        "type": "value_cell",
                        "gold_raw": g_cell,
                        "parser_raw": p_cell,
                        "exact_match": exact_match,
                        "numeric_match": numeric_match,
                        "reason": "unaligned_row" if not row_aligned else "value_mismatch"
                    })

            else:
                # No-value (category header) cell
                no_val_cells_total += 1
                # Must be null AND row must be aligned!
                if row_aligned and p_null and p_cell is None:
                    no_val_cells_match += 1
                else:
                    cell_discrepancies.append({
                        "row_index": g_row.get("row_index", g_idx + 1),
                        "label": g_row.get("label"),
                        "column_index": col_idx + 1,
                        "type": "no_value_cell",
                        "gold_raw": None,
                        "parser_raw": p_cell,
                        "exact_match": False,
                        "numeric_match": False,
                        "reason": "unaligned_row" if not row_aligned else "spurious_value_in_header_cell"
                    })

    # Value cell accuracies
    val_exact_acc = val_cells_exact_match / val_cells_total if val_cells_total > 0 else 1.0
    val_numeric_acc = val_cells_numeric_match / val_cells_total if val_cells_total > 0 else 1.0
    val_cell_precision = val_cells_exact_match / parser_val_cells_count if parser_val_cells_count > 0 else 1.0
    val_cell_recall = val_exact_acc
    val_cell_f1 = (2 * val_cell_precision * val_cell_recall / (val_cell_precision + val_cell_recall)) if (val_cell_precision + val_cell_recall) > 0 else 0.0

    # No-value cell accuracy
    no_val_acc = no_val_cells_match / no_val_cells_total if no_val_cells_total > 0 else 1.0

    # Overall cell accuracy
    total_cells = val_cells_total + no_val_cells_total
    overall_exact_acc = (val_cells_exact_match + no_val_cells_match) / total_cells if total_cells > 0 else 1.0
    overall_numeric_acc = (val_cells_numeric_match + no_val_cells_match) / total_cells if total_cells > 0 else 1.0

    # 4. Numeric-Token Coverage (Multiset Match)
    gold_tokens = Counter()
    for r in gold_rows:
        for val in r.get("values", []):
            for t in extract_numeric_tokens(val):
                gold_tokens[t] += 1

    parser_tokens = Counter()
    for r in parser_rows:
        for val in r.get("values", []):
            for t in extract_numeric_tokens(val):
                parser_tokens[t] += 1

    intersection_count = sum((gold_tokens & parser_tokens).values())
    total_gold_token_count = sum(gold_tokens.values())
    total_parser_token_count = sum(parser_tokens.values())

    token_recall = intersection_count / total_gold_token_count if total_gold_token_count > 0 else 1.0
    token_precision = intersection_count / total_parser_token_count if total_parser_token_count > 0 else 1.0
    token_f1 = (2 * token_precision * token_recall / (token_precision + token_recall)) if (token_precision + token_recall) > 0 else 0.0

    # 5. Diagnostic Accounting Checks (remove abs, use signed values with +1 for all addends)
    checks_def = gold_data.get("checks", [])
    accounting_results: List[dict] = []

    for check in checks_def:
        check_id = check.get("check_id")
        check_name = check.get("name")
        target_g_idx = check.get("target_row_index") - 1  # 0-indexed
        addends = check.get("addend_rows", [])
        num_terms = check.get("tolerance_terms", len(addends))
        tolerance = max(1, math.ceil(num_terms / 2.0))
        rationale = check.get("tolerance_rationale", "")

        target_p_idx = gold_to_parser_map.get(target_g_idx)

        for c in range(num_cols):
            col_name = (
                gold_data.get("metadata", {}).get("column_headers", [])[c]
                if c < len(gold_data.get("metadata", {}).get("column_headers", []))
                else f"Col {c+1}"
            )

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
                val, is_nil, _, is_null = parse_numeric_cell(addend_raw)

                if is_nil:
                    computed_sum += 0.0
                elif val is not None:
                    # Use signed printed value directly with sign (+1)
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

    report = {
        "summary": {
            "gold_rows": num_gold,
            "parser_rows": num_parser,
            "aligned_rows": num_matched,
            "row_precision": row_precision,
            "row_recall": row_recall,
            "row_f1": row_f1,
            "score_hierarchy": score_hierarchy,
            "hierarchy_accuracy": hierarchy_accuracy,
            "cell_metrics": {
                "value_cells": {
                    "total": val_cells_total,
                    "exact_matches": val_cells_exact_match,
                    "numeric_matches": val_cells_numeric_match,
                    "exact_accuracy": val_exact_acc,
                    "numeric_accuracy": val_numeric_acc,
                    "precision": val_cell_precision,
                    "recall": val_cell_recall,
                    "f1": val_cell_f1,
                },
                "no_value_cells": {
                    "total": no_val_cells_total,
                    "matches": no_val_cells_match,
                    "accuracy": no_val_acc,
                },
                "all_cells": {
                    "total": total_cells,
                    "exact_accuracy": overall_exact_acc,
                    "numeric_accuracy": overall_numeric_acc,
                }
            },
            "token_precision": token_precision,
            "token_recall": token_recall,
            "token_f1": token_f1,
        },
        "discrepancies": {
            "unmatched_gold_rows": [
                {"row_index": g_idx + 1, "label": gold_rows[g_idx].get("label")}
                for g_idx in unmatched_gold_indices
            ],
            "unmatched_parser_rows": [
                {"row_index": p_idx + 1, "label": parser_rows[p_idx].get("label")}
                for p_idx in unmatched_parser_indices
            ],
            "hierarchy_mismatches": hierarchy_details,
            "cell_mismatches": cell_discrepancies,
        },
        "diagnostics": {
            "total_accounting_checks": len(accounting_results),
            "passed_checks": sum(1 for c in accounting_results if c["passed"]),
            "exact_checks": sum(1 for c in accounting_results if c["status"] == "EXACT_MATCH"),
            "rounding_checks": sum(1 for c in accounting_results if c["status"] == "SOURCE_ROUNDING"),
            "failed_checks": sum(1 for c in accounting_results if not c["passed"]),
            "details": accounting_results
        }
    }

    return report


def format_text_report(report: dict) -> str:
    s = report["summary"]
    cm = s["cell_metrics"]
    vc = cm["value_cells"]
    nvc = cm["no_value_cells"]
    ac = cm["all_cells"]
    d = report["diagnostics"]

    hier_str = f"{s['hierarchy_accuracy']:.2%}" if s["score_hierarchy"] else "N/A (Flat Indent Variant)"

    out = []
    out.append("=====================================================================")
    out.append("      JAPANESE FINANCIAL TABLE PARSER EVALUATION REPORT              ")
    out.append("=====================================================================")
    out.append(f" 1. ROW MATCH (Page-Order Sequence Alignment):")
    out.append(f"    - Gold Rows:      {s['gold_rows']:<4} | Parser Rows: {s['parser_rows']:<4}")
    out.append(f"    - Aligned Rows:   {s['aligned_rows']:<4}")
    out.append(f"    - Row Precision:  {s['row_precision']:>7.2%}")
    out.append(f"    - Row Recall:     {s['row_recall']:>7.2%}")
    out.append(f"    - Row F1 Score:   {s['row_f1']:>7.2%}")
    out.append("---------------------------------------------------------------------")
    out.append(f" 2. HIERARCHY ACCURACY (Parent Visual Indent Match):")
    out.append(f"    - Hierarchy Match: {hier_str}")
    out.append("---------------------------------------------------------------------")
    out.append(f" 3. CELL ACCURACY:")
    out.append(f"    [A] Value Cells ({vc['total']} cells) -- Gated by --fail-under-cell:")
    out.append(f"        - Exact Printed String: {vc['exact_accuracy']:>7.2%} ({vc['exact_matches']}/{vc['total']})")
    out.append(f"        - Normalized Numeric:   {vc['numeric_accuracy']:>7.2%} ({vc['numeric_matches']}/{vc['total']})")
    out.append(f"        - Precision / Recall:   {vc['precision']:>7.2%} / {vc['recall']:>7.2%} (F1: {vc['f1']:>7.2%})")
    out.append(f"    [B] No-Value Cells ({nvc['total']} header cells):")
    out.append(f"        - Null Match Accuracy:  {nvc['accuracy']:>7.2%} ({nvc['matches']}/{nvc['total']})")
    out.append(f"    [C] Overall Cells ({ac['total']} total cells):")
    out.append(f"        - Exact String Accuracy: {ac['exact_accuracy']:>7.2%}")
    out.append(f"        - Numeric Accuracy:      {ac['numeric_accuracy']:>7.2%}")
    out.append("---------------------------------------------------------------------")
    out.append(f" 4. NUMERIC-TOKEN COVERAGE (Multiset Match):")
    out.append(f"    - Token Precision: {s['token_precision']:>7.2%}")
    out.append(f"    - Token Recall:    {s['token_recall']:>7.2%}")
    out.append(f"    - Token F1 Score:  {s['token_f1']:>7.2%}")
    out.append("=====================================================================")
    out.append(f" DIAGNOSTICS: ACCOUNTING CONSISTENCY CHECKS")
    out.append(f" (Reported separately with scaled rounding tolerance; NOT accuracy)")
    out.append(f" Total Checks: {d['total_accounting_checks']} | Passed: {d['passed_checks']} (Exact: {d['exact_checks']}, Rounding: {d['rounding_checks']}) | Failed: {d['failed_checks']}")
    out.append("=====================================================================")

    disc = report["discrepancies"]
    if disc["unmatched_gold_rows"]:
        out.append("\n[!] Unmatched Gold Rows (Dropped):")
        for r in disc["unmatched_gold_rows"][:5]:
            out.append(f"    - Row {r['row_index']}: {r['label']}")
        if len(disc["unmatched_gold_rows"]) > 5:
            out.append(f"    ... and {len(disc['unmatched_gold_rows']) - 5} more")

    if disc["unmatched_parser_rows"]:
        out.append("\n[!] Unmatched Parser Rows (Spurious):")
        for r in disc["unmatched_parser_rows"][:5]:
            out.append(f"    - Row {r['row_index']}: {r['label']}")

    if disc["hierarchy_mismatches"]:
        out.append("\n[!] Hierarchy Mismatches:")
        for h in disc["hierarchy_mismatches"][:5]:
            out.append(f"    - Row {h['row_index']} ({h['label']}): Expected parent '{h['expected_parent']}' [Idx {h['expected_parent_index']}], got '{h['parser_parent']}' [Idx {h['parser_parent_index']}]")

    if disc["cell_mismatches"]:
        out.append(f"\n[!] Cell Mismatches ({len(disc['cell_mismatches'])} cells):")
        for c in disc["cell_mismatches"][:10]:
            out.append(f"    - Row {c['row_index']} '{c['label']}' Col {c['column_index']} [{c['type']}]: Gold='{c['gold_raw']}', Parser='{c['parser_raw']}' ({c['reason']})")
        if len(disc["cell_mismatches"]) > 10:
            out.append(f"    ... and {len(disc['cell_mismatches']) - 10} more")

    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Japanese Financial Statement Table Evaluation Harness")
    parser.add_argument("--gold", required=True, help="Path to gold reference JSON")
    parser.add_argument("--input", required=True, help="Path to parser output JSON")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text", help="Output report format")

    # Explicit threshold flags (no hidden thresholds)
    # Note: --fail-under-cell gates specifically on value cells accuracy
    parser.add_argument("--fail-under-cell", type=float, default=None, help="Fail if value cell exact accuracy is below threshold (0.0 - 1.0)")
    parser.add_argument("--fail-under-row", type=float, default=None, help="Fail if row match F1 is below threshold (0.0 - 1.0)")
    parser.add_argument("--fail-under-hierarchy", type=float, default=None, help="Fail if hierarchy accuracy is below threshold (0.0 - 1.0)")
    parser.add_argument("--fail-under-numeric-token", type=float, default=None, help="Fail if numeric token F1 is below threshold (0.0 - 1.0)")

    args = parser.parse_args()

    with open(args.gold, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    with open(args.input, "r", encoding="utf-8") as f:
        parser_data = json.load(f)

    report = evaluate_table(gold_data, parser_data)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.format == "markdown":
        s = report["summary"]
        cm = s["cell_metrics"]
        vc = cm["value_cells"]
        nvc = cm["no_value_cells"]
        d = report["diagnostics"]
        hier_str = f"{s['hierarchy_accuracy']:.2%}" if s["score_hierarchy"] else "N/A"
        md = f"""# Table Extraction Evaluation Report

| Metric | Score | Details |
|---|---|---|
| **Row Match F1** | **{s['row_f1']:.2%}** | Precision: {s['row_precision']:.2%}, Recall: {s['row_recall']:.2%} |
| **Hierarchy Accuracy** | **{hier_str}** | Parent visual indent match |
| **Value Cell Exact Accuracy** | **{vc['exact_accuracy']:.2%}** | {vc['exact_matches']}/{vc['total']} value cells |
| **Value Cell Numeric Accuracy** | **{vc['numeric_accuracy']:.2%}** | {vc['numeric_matches']}/{vc['total']} value cells |
| **No-Value Cell Accuracy** | **{nvc['accuracy']:.2%}** | {nvc['matches']}/{nvc['total']} header cells |
| **Numeric-Token F1** | **{s['token_f1']:.2%}** | Multiset token match |

### Accounting Diagnostics (Not Scored)
- Total Checks: {d['total_accounting_checks']}
- Passed: {d['passed_checks']} (Exact: {d['exact_checks']}, Source Rounding: {d['rounding_checks']})
- Discrepancies: {d['failed_checks']}
"""
        print(md)
    else:
        print(format_text_report(report))

    # Evaluate fail-under criteria
    exit_code = 0
    s = report["summary"]
    vc = s["cell_metrics"]["value_cells"]

    # --fail-under-cell gates specifically on value cells
    if args.fail_under_cell is not None and vc["exact_accuracy"] < args.fail_under_cell:
        print(f"\n[FAILURE] Value cell exact accuracy ({vc['exact_accuracy']:.2%}) is below threshold ({args.fail_under_cell:.2%})", file=sys.stderr)
        exit_code = 1

    if args.fail_under_row is not None and s["row_f1"] < args.fail_under_row:
        print(f"\n[FAILURE] Row match F1 ({s['row_f1']:.2%}) is below threshold ({args.fail_under_row:.2%})", file=sys.stderr)
        exit_code = 1

    if args.fail_under_hierarchy is not None and s["score_hierarchy"] and s["hierarchy_accuracy"] is not None:
        if s["hierarchy_accuracy"] < args.fail_under_hierarchy:
            print(f"\n[FAILURE] Hierarchy accuracy ({s['hierarchy_accuracy']:.2%}) is below threshold ({args.fail_under_hierarchy:.2%})", file=sys.stderr)
            exit_code = 1

    if args.fail_under_numeric_token is not None and s["token_f1"] < args.fail_under_numeric_token:
        print(f"\n[FAILURE] Numeric token F1 ({s['token_f1']:.2%}) is below threshold ({args.fail_under_numeric_token:.2%})", file=sys.stderr)
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
