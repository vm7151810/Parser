import copy
import random
from pathlib import Path
import pdfplumber

from parser.config import ParserConfig
from parser.pdf_extractor import extract_page_tokens
from parser.header_parser import find_header_boundary, extract_metadata, associate_period_headers
from parser.column_detector import detect_columns
from parser.indent_clusterer import cluster_indent_levels
from parser.row_assembler import assemble_rows
from parser.hierarchy_builder import build_hierarchy
from parser.row_typer import type_rows
from parser.consistency import run_accounting_checks
from parser.coverage_auditor import audit_token_coverage
from parser.table_model import ParsedTable

pdf_path = "balance_sheet.pdf"
config = ParserConfig()

# Pipeline runner from tokens
def run_pipeline_from_tokens(tokens, median_glyph_width, thresholds, page_info, page_number=1):
    page_height = page_info["height"]
    header_y_cutoff = find_header_boundary(tokens, page_height, config.header_zone_fallback_fraction)
    header_tokens = [t for t in tokens if t["top"] <= header_y_cutoff]
    
    meta = extract_metadata(header_tokens, "balance_sheet.pdf", page_number)
    meta["median_glyph_width_pts"] = round(median_glyph_width, 2)
    meta["parsed_at"] = "STATIC_TIMESTAMP"
    warnings = []
    
    column_centroids = detect_columns(tokens, header_y_cutoff, thresholds)
    if not column_centroids:
        warnings.append("no_financial_columns_detected")
    meta["n_columns"] = len(column_centroids)
    
    periods = associate_period_headers(header_tokens, column_centroids, thresholds.col_assign)
    meta["periods"] = periods
    period_labels = [p["label"] for p in periods]
    
    first_col_x1 = column_centroids[0] if column_centroids else page_info["width"]
    indent_clusterer = cluster_indent_levels(tokens, header_y_cutoff, thresholds, first_col_x1, page_height)
    meta["n_indent_levels"] = indent_clusterer.n_levels
    if indent_clusterer.is_flat:
        warnings.append("flat_indentation_detected_using_heuristic_hierarchy")
        
    rows = assemble_rows(
        tokens=tokens, header_y_cutoff=header_y_cutoff, page_height=page_height,
        column_centroids=column_centroids, period_labels=period_labels,
        indent_clusterer=indent_clusterer, thresholds=thresholds, page_number=page_number
    )
    
    rows = build_hierarchy(rows, is_flat_indent=indent_clusterer.is_flat)
    rows = type_rows(rows)
    checks = run_accounting_checks(rows, period_labels)
    # Coverage audit (independent)
    audit = audit_token_coverage(pdf_path, rows, page_number)
    meta["warnings"] = warnings
    return ParsedTable(meta=meta, rows=rows, accounting_checks=checks, audit=audit)

# Baseline run
with pdfplumber.open(pdf_path) as pdf:
    orig_tokens, orig_mgw, orig_thresh, orig_page_info = extract_page_tokens(pdf.pages[0], config, 1)

baseline_table = run_pipeline_from_tokens(
    copy.deepcopy(orig_tokens), orig_mgw, orig_thresh, copy.deepcopy(orig_page_info)
)
baseline_dict = baseline_table.to_dict()

def compare_to_baseline(name, test_dict, ignore_coords=False):
    diffs = []
    # Structural keys: column_headers, row count, row labels, row levels, row types, values
    # We compare structural output!
    b_rows = baseline_dict.get("rows", [])
    t_rows = test_dict.get("rows", [])
    if len(b_rows) != len(t_rows):
        diffs.append(f"Row count difference: baseline={len(b_rows)} vs test={len(t_rows)}")
    else:
        for i, (br, tr) in enumerate(zip(b_rows, t_rows)):
            for k in ["label", "level", "row_type", "gross_parent", "block_id", "structural_path", "flags", "values"]:
                if br.get(k) != tr.get(k):
                    diffs.append(f"Row {i} ({br['label']}) {k}: baseline={br.get(k)} vs test={tr.get(k)}")
            if not ignore_coords:
                if br.get("provenance_label") != tr.get("provenance_label"):
                    diffs.append(f"Row {i} ({br['label']}) provenance: baseline={br.get('provenance_label')} vs test={tr.get('provenance_label')}")
                    
    # Checks
    b_checks = baseline_dict.get("accounting_checks", [])
    t_checks = test_dict.get("accounting_checks", [])
    if len(b_checks) != len(t_checks):
        diffs.append(f"Checks count difference: baseline={len(b_checks)} vs test={len(t_checks)}")
    else:
        for i, (bc, tc) in enumerate(zip(b_checks, t_checks)):
            for k in ["check_id", "passed", "classification", "computed", "stated", "diff"]:
                if bc.get(k) != tc.get(k):
                    diffs.append(f"Check {i} ({bc['check_id']}) {k}: baseline={bc.get(k)} vs test={tc.get(k)}")
                    
    # Meta
    for k in ["title", "unit", "amendment", "n_columns", "n_indent_levels"]:
        if baseline_dict["meta"].get(k) != test_dict["meta"].get(k):
            diffs.append(f"meta.{k}: baseline={baseline_dict['meta'].get(k)} vs test={test_dict['meta'].get(k)}")
            
    print(f"\n--- INVARIANCE CHECK: {name} ---")
    print(f"Differences: {len(diffs)}")
    for d in diffs[:20]:
        print(f"  • {d}")
    if len(diffs) > 20:
        print(f"  ... and {len(diffs) - 20} more diffs")
    return diffs

print("1. Running Shuffled Word Order Invariance...")
# Test 5 different random shuffles
for seed in [42, 123, 999, 2026, 7]:
    shuffled_tokens = copy.deepcopy(orig_tokens)
    random.seed(seed)
    random.shuffle(shuffled_tokens)
    res_shuffled = run_pipeline_from_tokens(
        shuffled_tokens, orig_mgw, orig_thresh, copy.deepcopy(orig_page_info)
    )
    compare_to_baseline(f"Shuffle seed={seed}", res_shuffled.to_dict())

print("\n2. Running Translated Coordinates Invariance...")
for dx, dy in [(10.0, 10.0), (50.0, 20.0), (-5.0, 15.0)]:
    trans_tokens = copy.deepcopy(orig_tokens)
    for t in trans_tokens:
        t["x0"] += dx
        t["x1"] += dx
        t["top"] += dy
        t["bottom"] += dy
    trans_page = copy.deepcopy(orig_page_info)
    trans_page["width"] += dx
    trans_page["height"] += dy
    res_trans = run_pipeline_from_tokens(
        trans_tokens, orig_mgw, orig_thresh, trans_page
    )
    compare_to_baseline(f"Translate dx={dx}, dy={dy}", res_trans.to_dict(), ignore_coords=True)

print("\n3. Running Scaled Coordinates Invariance...")
for scale in [2.0, 0.5]:
    scaled_tokens = copy.deepcopy(orig_tokens)
    for t in scaled_tokens:
        t["x0"] *= scale
        t["x1"] *= scale
        t["top"] *= scale
        t["bottom"] *= scale
    scaled_page = copy.deepcopy(orig_page_info)
    scaled_page["width"] *= scale
    scaled_page["height"] *= scale
    scaled_mgw = orig_mgw * scale
    scaled_thresh = config.scale(scaled_mgw)
    
    res_scaled = run_pipeline_from_tokens(
        scaled_tokens, scaled_mgw, scaled_thresh, scaled_page
    )
    compare_to_baseline(f"Scale factor={scale}", res_scaled.to_dict(), ignore_coords=True)
