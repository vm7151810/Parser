import copy
import json
from pathlib import Path
from parser.pipeline import parse_pdf_page
import parser.pipeline as pipeline
import parser.row_typer as row_typer
import parser.hierarchy_builder as hierarchy_builder
import parser.header_parser as header_parser
import parser.consistency as consistency

pdf_path = "balance_sheet.pdf"

# Baseline
base_table = parse_pdf_page(pdf_path, page_number=1)
base_dict = base_table.to_dict()

def clean_dict(d):
    d = copy.deepcopy(d)
    if "meta" in d and "parsed_at" in d["meta"]:
        del d["meta"]["parsed_at"]
    return d

base_clean = clean_dict(base_dict)

def diff_outputs(name, new_dict):
    new_clean = clean_dict(new_dict)
    diffs = []
    
    # 1. Meta diffs
    for k, v in base_clean["meta"].items():
        nv = new_clean["meta"].get(k)
        if nv != v:
            diffs.append(f"meta.{k}: baseline={v} != ablation={nv}")
    for k, v in new_clean["meta"].items():
        if k not in base_clean["meta"]:
            diffs.append(f"meta.{k}: extra in ablation={v}")
            
    # 2. Rows diffs
    brows = base_clean.get("rows", [])
    nrows = new_clean.get("rows", [])
    if len(brows) != len(nrows):
        diffs.append(f"Row count: baseline={len(brows)} != ablation={len(nrows)}")
    else:
        for i, (br, nr) in enumerate(zip(brows, nrows)):
            for f in ["label", "level", "parent_index", "parent_label", "row_type", "gross_parent", "block_id", "sum_parent_path", "structural_path", "flags", "values"]:
                if br.get(f) != nr.get(f):
                    diffs.append(f"Row {i} ({br['label']}) {f}: baseline={br.get(f)} != ablation={nr.get(f)}")
                    
    # 3. Accounting checks diffs
    bchecks = base_clean.get("accounting_checks", [])
    nchecks = new_clean.get("accounting_checks", [])
    if len(bchecks) != len(nchecks):
        diffs.append(f"Accounting checks count: baseline={len(bchecks)} != ablation={len(nchecks)}")
    b_ids = {c["check_id"]: c for c in bchecks}
    n_ids = {c["check_id"]: c for c in nchecks}
    for cid in b_ids:
        if cid not in n_ids:
            diffs.append(f"Check missing in ablation: {cid}")
        else:
            bc = b_ids[cid]
            nc = n_ids[cid]
            for f in ["passed", "classification", "computed", "stated", "diff", "tolerance"]:
                if bc.get(f) != nc.get(f):
                    diffs.append(f"Check {cid} {f}: baseline={bc.get(f)} != ablation={nc.get(f)}")
    for cid in n_ids:
        if cid not in b_ids:
            diffs.append(f"Extra check in ablation: {cid}")
            
    # 4. Audit diffs
    if base_clean.get("audit") != new_clean.get("audit"):
        diffs.append(f"audit: baseline={base_clean.get('audit')} != ablation={new_clean.get('audit')}")
        
    print(f"\n=======================================================")
    print(f"ABLATION: {name}")
    print(f"Total differences: {len(diffs)}")
    for d in diffs[:30]:
        print(f"  • {d}")
    if len(diffs) > 30:
        print(f"  ... and {len(diffs) - 30} more diffs")
    return diffs

# -------------------------------------------------------------
# ABLATION 2: Disable label-stem pairing
# In row_typer.py, skip pass 2 (triplet stem-pairing)
# -------------------------------------------------------------
orig_type_rows = pipeline.type_rows

def type_rows_without_stem_pairing(rows):
    # Pass 1:
    for r in rows:
        has_values = any(v.numeric is not None or v.nil for v in r.values.values())
        if not has_values:
            r.row_type = "section" if r.level == 0 else "header"
            r.sum_parent_path = None
        elif r.label.endswith("合計"):
            r.row_type = "subtotal"
            r.sum_parent_path = None
        elif any(r.label.endswith(sfx) for sfx in row_typer.NET_SUFFIXES):
            r.row_type = "net"
        elif any(kw in r.label for kw in row_typer.CONTRA_KEYWORDS):
            r.row_type = "contra_candidate"
        else:
            r.row_type = "item"

    # Pass 2 SKIPPED (no triplet stem-pairing)

    # Pass 3:
    for r in rows:
        if r.row_type == "contra_candidate":
            r.row_type = "contra_standalone"

    # Pass 4:
    for r in rows:
        if r.row_type in ("item", "contra_standalone"):
            if len(r.structural_path) >= 2:
                r.sum_parent_path = tuple(r.structural_path[:-1])
            else:
                r.sum_parent_path = tuple(r.structural_path)
        elif r.row_type in ("net", "net_orphan"):
            if len(r.structural_path) >= 2:
                r.sum_parent_path = tuple(r.structural_path[:-1])
            else:
                r.sum_parent_path = tuple(r.structural_path)
        elif r.row_type == "subtotal":
            if len(r.structural_path) >= 3:
                r.sum_parent_path = tuple(r.structural_path[:-2])
            elif len(r.structural_path) >= 2:
                r.sum_parent_path = tuple(r.structural_path[:-1])
            else:
                r.sum_parent_path = None
        else:
            r.sum_parent_path = None

    # Pass 5:
    for r in rows:
        non_nil_vals = [v.numeric for v in r.values.values() if v.numeric is not None and not v.nil]
        if not non_nil_vals:
            continue
        if r.row_type == "item" and all(v < 0 for v in non_nil_vals):
            r.flags.append("all_values_negative_unexpected")
        if r.row_type in ("contra", "contra_standalone") and any(v > 0 for v in non_nil_vals):
            r.flags.append("contra_has_positive_value")

    return rows

pipeline.type_rows = type_rows_without_stem_pairing
t2 = parse_pdf_page(pdf_path, page_number=1)
pipeline.type_rows = orig_type_rows
diff_outputs("Disable Label-Stem Pairing", t2.to_dict())

# -------------------------------------------------------------
# ABLATION 3: Disable flat-indent fallback
# -------------------------------------------------------------
orig_build_hierarchy = pipeline.build_hierarchy

def build_hierarchy_no_flat_fallback(rows, is_flat_indent=False):
    # Completely ignore is_flat_indent
    return orig_build_hierarchy(rows, is_flat_indent=False)

pipeline.build_hierarchy = build_hierarchy_no_flat_fallback
t3 = parse_pdf_page(pdf_path, page_number=1)
pipeline.build_hierarchy = orig_build_hierarchy
diff_outputs("Disable Flat-Indent Fallback (natural balance_sheet.pdf)", t3.to_dict())

# -------------------------------------------------------------
# ABLATION 1: Disable Japanese keyword fallbacks
# 1A: Disable composite subtotal keyword mapping in consistency.py
# -------------------------------------------------------------
orig_run_accounting = pipeline.run_accounting_checks

def run_accounting_no_composite_keywords(rows, period_labels):
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
                passed=diff <= tol, notes=f"Gross + Contra vs Net"
            ))

    # 2. Subtotals WITHOUT hardcoded Japanese composite keyword branches
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
        # In this ablation: NO lines 108-121 (no hardcoded 固定資産合計 / 資産合計 branch)
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
            check_type = "grand_total" if sub.label == "資産合計" else "subtotal"
            checks.append(consistency.AccountingCheck(
                check_id=f"{check_type}_{sub.label}_{p}", check_type=check_type, period=p,
                stated_path=sub.structural_path, n_terms=n_terms, tolerance=tol,
                addend_paths=[a.structural_path for a in direct_addends],
                computed=computed, stated=stated, diff=diff, classification=classification,
                passed=diff <= tol, notes=f"Sum of {n_terms} items feeding {sub.label}"
            ))
    return checks

pipeline.run_accounting_checks = run_accounting_no_composite_keywords
t1a = parse_pdf_page(pdf_path, page_number=1)
pipeline.run_accounting_checks = orig_run_accounting
diff_outputs("Disable Japanese Composite Subtotal Keywords in consistency.py", t1a.to_dict())

# 1B: Disable header metadata regexes (METADATA_HEADER_PATTERNS) in header_parser.py
orig_find_header = pipeline.find_header_boundary
def find_header_no_keywords(tokens, page_height, fallback_fraction=0.15):
    # Only fallback fraction
    return page_height * fallback_fraction

pipeline.find_header_boundary = find_header_no_keywords
t1b = parse_pdf_page(pdf_path, page_number=1)
pipeline.find_header_boundary = orig_find_header
diff_outputs("Disable Header Japanese Keyword Patterns (fallback to fraction 0.15)", t1b.to_dict())
