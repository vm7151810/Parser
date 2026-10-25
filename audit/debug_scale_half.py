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

scale = 0.5
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

page_height = scaled_page["height"]
header_y_cutoff = find_header_boundary(scaled_tokens, page_height, config.header_zone_fallback_fraction)
print(f"scaled_mgw: {scaled_mgw}")
print(f"scaled_thresh: {scaled_thresh}")
print(f"header_y_cutoff: {header_y_cutoff}")

data_tokens = [t for t in scaled_tokens if t["top"] > header_y_cutoff]
print(f"Total data tokens: {len(data_tokens)}")

data_tokens.sort(key=lambda t: (round(t["top"], 1), t["x0"]))

# Let's inspect grouping
y_bands = []
current_band = [data_tokens[0]]
for idx, t in enumerate(data_tokens[1:]):
    band_top = min(x["top"] for x in current_band)
    band_bottom = max(x["bottom"] for x in current_band)
    band_mid = (band_top + band_bottom) / 2.0
    t_mid = (t["top"] + t["bottom"]) / 2.0
    overlap = not (t["bottom"] < band_top - scaled_thresh.y_band_tol or
                   band_bottom < t["top"] - scaled_thresh.y_band_tol)
    close_mid = abs(t_mid - band_mid) <= scaled_thresh.y_band_tol * 2.0
    if overlap or close_mid:
        current_band.append(t)
    else:
        y_bands.append(current_band)
        current_band = [t]
if current_band:
    y_bands.append(current_band)

print(f"Number of y_bands: {len(y_bands)}")
for i, b in enumerate(y_bands[:5]):
    texts = [x["text"] for x in b]
    top_span = (min(x["top"] for x in b), max(x["bottom"] for x in b))
    print(f"Band {i}: {len(b)} tokens, span={top_span}, sample texts: {texts[:5]}")
