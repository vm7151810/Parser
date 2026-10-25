import json
import copy
from pathlib import Path
from parser.pipeline import parse_pdf_page
import parser.row_typer as row_typer
import parser.hierarchy_builder as hierarchy_builder
import parser.header_parser as header_parser
import parser.consistency as consistency

pdf_path = "balance_sheet.pdf"

# 0. Baseline
baseline_table = parse_pdf_page(pdf_path, page_number=1)
baseline_dict = baseline_table.to_dict()

def clean_dict(d):
    d = copy.deepcopy(d)
    if "meta" in d and "parsed_at" in d["meta"]:
        del d["meta"]["parsed_at"]
    return d

base_clean = clean_dict(baseline_dict)

def compare_outputs(name, new_dict):
    new_clean = clean_dict(new_dict)
    diffs = []
    
    # Compare top-level keys
    for k in base_clean:
        if k not in new_clean:
            diffs.append(f"Missing key: {k}")
            
    # Compare meta
    for k, v in base_clean["meta"].items():
        nv = new_clean["meta"].get(k)
        if nv != v:
            diffs.append(f"meta[{k}]: baseline={v} vs new={nv}")
            
    # Compare rows
    base_rows = base_clean.get("rows", [])
    new_rows = new_clean.get("rows", [])
    if len(base_rows) != len(new_rows):
        diffs.append(f"Row count: baseline={len(base_rows)} vs new={len(new_rows)}")
    else:
        for i, (br, nr) in enumerate(zip(base_rows, new_rows)):
            for f in ["id", "label", "level", "row_type", "gross_parent", "block_id", "sum_parent_path", "structural_path", "flags"]:
                if br.get(f) != nr.get(f):
                    diffs.append(f"Row {i} ({br['label']}) {f}: baseline={br.get(f)} vs new={nr.get(f)}")
            if br.get("values") != nr.get("values"):
                diffs.append(f"Row {i} ({br['label']}) values: baseline={br.get('values')} vs new={nr.get('values')}")
                
    # Compare checks
    base_checks = base_clean.get("accounting_checks", [])
    new_checks = new_clean.get("accounting_checks", [])
    if len(base_checks) != len(new_checks):
        diffs.append(f"Checks count: baseline={len(base_checks)} vs new={len(new_checks)}")
    else:
        for i, (bc, nc) in enumerate(zip(base_checks, new_checks)):
            for f in ["check_id", "check_type", "passed", "classification", "computed", "stated", "diff", "tolerance"]:
                if bc.get(f) != nc.get(f):
                    diffs.append(f"Check {i} ({bc['check_id']}) {f}: baseline={bc.get(f)} vs new={nc.get(f)}")
                    
    # Compare audit
    if base_clean.get("audit") != new_clean.get("audit"):
        diffs.append(f"audit: baseline={base_clean.get('audit')} vs new={new_clean.get('audit')}")
        
    print(f"\n==========================================")
    print(f"ABLATION RESULT: {name}")
    print(f"Total differences found: {len(diffs)}")
    for d in diffs[:25]:
        print(f"  • {d}")
    if len(diffs) > 25:
        print(f"  ... and {len(diffs) - 25} more differences")
    return len(diffs) == 0

print("Running Ablations on balance_sheet.pdf...")

# --- ABLATION 1: Disable Japanese keyword fallbacks ---
# (a) In consistency.py: disable specific composite subtotal keyword matches (固定資産合計 and 資産合計)
orig_consistency_checks = consistency.run_accounting_checks
def run_accounting_checks_no_keywords(rows, period_labels):
    # Monkey-patch subtotal section in run_accounting_checks without the hardcoded label matches
    # Let's see what happens if child_subtotals keyword matches are disabled
    pass

# Let's test disabling consistency hardcoded label fallbacks
# And let's test disabling header_parser METADATA_HEADER_PATTERNS
