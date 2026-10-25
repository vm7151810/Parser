import copy
import pdfplumber
from parser.config import ParserConfig
from parser.pdf_extractor import extract_page_tokens
from parser.header_parser import find_header_boundary
from parser.column_detector import detect_columns
from parser.indent_clusterer import cluster_indent_levels
from parser.row_assembler import assemble_rows

pdf_path = "balance_sheet.pdf"
config = ParserConfig()
with pdfplumber.open(pdf_path) as pdf:
    orig_tokens, orig_mgw, orig_thresh, orig_page_info = extract_page_tokens(pdf.pages[0], config, 1)

for dy in [50.0, 100.0, 250.0]:
    trans_tokens = copy.deepcopy(orig_tokens)
    for t in trans_tokens:
        t["top"] += dy
        t["bottom"] += dy
        t["x0"] += dy
        t["x1"] += dy
    page_height = orig_page_info["height"]
    cutoff = find_header_boundary(trans_tokens, page_height, config.header_zone_fallback_fraction)
    print(f"dy={dy}: header_y_cutoff={cutoff:.2f} (original was {find_header_boundary(orig_tokens, page_height, config.header_zone_fallback_fraction):.2f})")
