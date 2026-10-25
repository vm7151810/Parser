"""
Accounting Consistency Engine: verifies subtotals, net values, and grand totals
using dynamic addend discovery and scaled rounding tolerance.
"""
from __future__ import annotations
import math
from typing import Optional

from parser.table_model import Row, AccountingCheck


def run_accounting_checks(
    rows: list[Row],
    period_labels: list[str]
) -> list[AccountingCheck]:
    """
    Executes accounting consistency checks across all periods.
    """
    checks: list[AccountingCheck] = []

    # 1. Net-value checks (gross + contra == net per block_id)
    block_ids = sorted(list(set(r.block_id for r in rows if r.block_id)))
    for b_id in block_ids:
        block_rows = [r for r in rows if r.block_id == b_id]
        gross_row = next((r for r in block_rows if r.row_type == "gross"), None)
        contra_row = next((r for r in block_rows if r.row_type == "contra"), None)
        net_row = next((r for r in block_rows if r.row_type == "net"), None)

        if not (gross_row and contra_row and net_row):
            continue

        for p in period_labels:
            g_val = gross_row.values.get(p)
            c_val = contra_row.values.get(p)
            n_val = net_row.values.get(p)

            if not (g_val and c_val and n_val):
                continue
            if g_val.numeric is None or c_val.numeric is None or n_val.numeric is None:
                continue

            computed = round(g_val.numeric + c_val.numeric, 2)
            stated = round(n_val.numeric, 2)
            diff = abs(round(computed - stated, 2))
            tol = 1.0

            if diff == 0.0:
                classification = "exact"
                passed = True
            elif diff <= tol:
                classification = "source_rounding"
                passed = True
            elif diff <= 10.0 * tol:
                classification = "suspect"
                passed = False
            else:
                classification = "parse_error"
                passed = False

            check = AccountingCheck(
                check_id=f"net_check_{b_id}_{p}",
                check_type="net_value",
                period=p,
                stated_path=net_row.structural_path,
                n_terms=2,
                tolerance=int(tol),
                addend_paths=[gross_row.structural_path, contra_row.structural_path],
                computed=computed,
                stated=stated,
                diff=diff,
                classification=classification,
                passed=passed,
                notes=f"Gross ({gross_row.label}) + Contra ({contra_row.label}) vs Net ({net_row.label})"
            )
            checks.append(check)

    # 2. Subtotal checks
    subtotal_rows = [r for r in rows if r.row_type == "subtotal"]
    for sub in subtotal_rows:
        sub_parent = tuple(sub.structural_path[:-1])

        # Find direct addends sharing this subtotal's parent path
        direct_addends = [
            r for r in rows
            if r.sum_parent_path == sub_parent and r.row_type in ("item", "net", "contra_standalone")
        ]

        # If empty, check if subtotal name without 合計 matches a subsection under sub_parent
        if not direct_addends:
            stem = sub.label.replace("合計", "").strip()
            if stem:
                stem_parent = sub_parent + (stem,)
                direct_addends = [
                    r for r in rows
                    if r.sum_parent_path == stem_parent and r.row_type in ("item", "net", "contra_standalone")
                ]

        # If still no direct item addends, check if this is a composite subtotal summing subordinate subtotals
        if not direct_addends:
            candidates = [
                r for r in subtotal_rows
                if r.id != sub.id
                and len(r.structural_path) > len(sub_parent)
                and tuple(r.structural_path[:len(sub_parent)]) == sub_parent
            ]
            child_levels = sorted(set(r.level for r in candidates if r.level > sub.level))
            if child_levels:
                target_level = child_levels[0]
                direct_addends = [r for r in candidates if r.level == target_level]

        if not direct_addends:
            continue

        n_terms = len(direct_addends)
        tol = max(1, math.ceil(n_terms / 2.0))

        for p in period_labels:
            sub_val = sub.values.get(p)
            if not sub_val or sub_val.numeric is None:
                continue

            addend_vals = []
            valid = True
            for a in direct_addends:
                aval = a.values.get(p)
                if not aval or aval.numeric is None:
                    # Nil is treated as 0 in summation if nil=True
                    if aval and aval.nil:
                        addend_vals.append(0.0)
                    else:
                        valid = False
                        break
                else:
                    addend_vals.append(aval.numeric)

            if not valid:
                continue

            computed = round(sum(addend_vals), 2)
            stated = round(sub_val.numeric, 2)
            diff = abs(round(computed - stated, 2))

            if diff == 0.0:
                classification = "exact"
                passed = True
            elif diff <= tol:
                classification = "source_rounding"
                passed = True
            elif diff <= 10.0 * tol:
                classification = "suspect"
                passed = False
            else:
                classification = "parse_error"
                passed = False

            check_type = "grand_total" if len(sub.structural_path) <= 2 else "subtotal"
            check = AccountingCheck(
                check_id=f"{check_type}_{sub.label}_{p}",
                check_type=check_type,
                period=p,
                stated_path=sub.structural_path,
                n_terms=n_terms,
                tolerance=tol,
                addend_paths=[a.structural_path for a in direct_addends],
                computed=computed,
                stated=stated,
                diff=diff,
                classification=classification,
                passed=passed,
                notes=f"Sum of {n_terms} items feeding {sub.label}"
            )
            checks.append(check)

    return checks
