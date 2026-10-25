import json
import copy
from parser.pipeline import parse_pdf_page
import parser.consistency as consistency
import parser.coverage_auditor as coverage_auditor
import parser.pipeline as pipeline

# 1. Baseline
orig_json_path = "output/balance_sheet_p1.json"
with open(orig_json_path, encoding="utf-8") as f:
    baseline_json = json.load(f)

# Proposed consistency replacement
def run_accounting_checks_agnostic(rows, period_labels):
    checks = []
    # 1. Net checks
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
            if not (g_val and c_val and n_val) or g_val.numeric is None or c_val.numeric is None or n_val.numeric is None:
                continue
            computed = round(g_val.numeric + c_val.numeric, 2)
            stated = round(n_val.numeric, 2)
            diff = abs(round(computed - stated, 2))
            tol = 1.0
            classification = "exact" if diff == 0.0 else ("source_rounding" if diff <= tol else ("suspect" if diff <= 10.0*tol else "parse_error"))
            checks.append(consistency.AccountingCheck(
                check_id=f"net_check_{b_id}_{p}", check_type="net_value", period=p,
                stated_path=net_row.structural_path, n_terms=2, tolerance=int(tol),
                addend_paths=[gross_row.structural_path, contra_row.structural_path],
                computed=computed, stated=stated, diff=diff, classification=classification,
                passed=diff <= tol, notes=f"Gross ({gross_row.label}) + Contra ({contra_row.label}) vs Net ({net_row.label})"
            ))

    # 2. Subtotal checks (Fully Dynamic Hierarchical Addend Discovery)
    subtotal_rows = [r for r in rows if r.row_type == "subtotal"]
    for sub in subtotal_rows:
        sub_parent = tuple(sub.structural_path[:-1])
        direct_addends = [
            r for r in rows
            if r.sum_parent_path == sub_parent and r.row_type in ("item", "net", "contra_standalone")
        ]
        if not direct_addends:
            stem = sub.label.replace("合計", "").strip()
            if stem:
                stem_parent = sub_parent + (stem,)
                direct_addends = [
                    r for r in rows
                    if r.sum_parent_path == stem_parent and r.row_type in ("item", "net", "contra_standalone")
                ]
        if not direct_addends:
            # Dynamic composite discovery without hardcoded labels:
            # Find subordinate subtotals within this parent container at the immediate child level
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
            
        import math
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
            classification = "exact" if diff == 0.0 else ("source_rounding" if diff <= tol else ("suspect" if diff <= 10.0*tol else "parse_error"))
            check_type = "grand_total" if len(sub.structural_path) <= 2 else "subtotal"
            checks.append(consistency.AccountingCheck(
                check_id=f"{check_type}_{sub.label}_{p}", check_type=check_type, period=p,
                stated_path=sub.structural_path, n_terms=n_terms, tolerance=tol,
                addend_paths=[a.structural_path for a in direct_addends],
                computed=computed, stated=stated, diff=diff, classification=classification,
                passed=diff <= tol, notes=f"Sum of {n_terms} items feeding {sub.label}"
            ))
    return checks

orig_func = pipeline.run_accounting_checks
pipeline.run_accounting_checks = run_accounting_checks_agnostic

new_table = parse_pdf_page("balance_sheet.pdf", page_number=1)
new_json = new_table.to_dict()
pipeline.run_accounting_checks = orig_func

# Compare JSONs (excluding parsed_at)
b_clean = copy.deepcopy(baseline_json)
n_clean = copy.deepcopy(new_json)
del b_clean["meta"]["parsed_at"]
del n_clean["meta"]["parsed_at"]

diffs = []
if b_clean != n_clean:
    import pprint
    for k in b_clean:
        if b_clean[k] != n_clean[k]:
            diffs.append(f"Top-level key '{k}' differs")
            if k == "accounting_checks":
                for i, (bc, nc) in enumerate(zip(b_clean[k], n_clean[k])):
                    if bc != nc:
                        diffs.append(f"  Check {i}: {bc['check_id']} differs: bc={bc} vs nc={nc}")

print(f"Differences between baseline and proposed dynamic consistency: {len(diffs)}")
for d in diffs:
    print("  ", d)
if len(diffs) == 0:
    print("SUCCESS: JSON output is 100% IDENTICAL (excluding parsed_at)!")
