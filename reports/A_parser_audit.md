# CHAT A: Parser Agnosticism Audit Report

## Commands run

```bash
# 1. Initial baseline status and tests
git status
python3 -m pytest tests/test_parser.py
# Output: 10 passed, 1 warning in 5.31s

# 2. Confirm no imports or references from eval/ or gold
PYTHONPATH=. python3 -c "
import sys
from parser import parse_pdf_page
table = parse_pdf_page('balance_sheet.pdf', page_number=1)
leaks = [m for m in sys.modules if 'eval' in m or 'gold' in m]
print('Imported eval/gold modules:', leaks)
assert len(leaks) == 0
"
# Output: Imported eval/gold modules: []

# 3. Static literal AST audit
python3 audit/find_literals.py
# Output: Extracted all numeric and string literals across parser/*.py and main.py

# 4. Detailed Ablation Runs on balance_sheet.pdf
PYTHONPATH=. python3 audit/run_ablations_correct.py
# Output summary:
#   • Disable Label-Stem Pairing: 57 differences (4 gross -> item, 4 contra -> contra_standalone, 8 net checks lost)
#   • Disable Flat-Indent Fallback: 0 differences (natural balance sheet has 5 discrete indent clusters)
#   • Disable Composite Subtotal Keywords: 5 differences (4 composite checks lost: 固定資産合計, 資産合計)
#   • Disable Header Keywords: 19 differences (dates unmapped, row count shifts from 43 to 44)

# 5. In-Memory Invariance Checks (shuffling, translation, scaling)
PYTHONPATH=. python3 audit/run_invariance_checks.py
# Output summary:
#   • Shuffled Word Order (5 random seeds: 42, 123, 999, 2026, 7): 0 differences across all seeds
#   • Translated Coordinates (dx, dy = 10, 50, -5): 0 differences when coordinate system is translated
#   • Scaled Coordinates (scale=2.0): 0 differences
#   • Scaled Coordinates (scale=0.5): 2 differences (43 rows collapsed into 1 row due to absolute y_band_tol_pts=2.0)

# 6. Debugging scale 0.5x failure
PYTHONPATH=. python3 audit/debug_scale_half.py
# Output: scaled inter-row gap < 2.0 pt causes y-band chain-merging; with scaled y_band_tol=1.0 pt, 44 y-bands preserved

# 7. Coordinate translation boundary test
PYTHONPATH=. python3 audit/test_translation.py
# Output: dy=250 causes header cutoff to fall back to 0.15 * page_height due to top < page_height * 0.40 bound

# 8. Verifying removals of class (c) hardcoded labels
PYTHONPATH=. python3 audit/verify_identity.py
# Output:
#   Total differences found: 0
#   VERIFIED: output/balance_sheet_p1.json is 100% IDENTICAL to baseline (excluding meta.parsed_at)!

# 9. Test suite verification after refactoring
python3 -m pytest tests/test_parser.py
# Output: 10 passed, 1 warning in 5.37s
```

---

## Findings

### 1. Assumption Inventory Table

Every stage of `parser/` and `main.py` was inspected line-by-line and categorized into:
- **(a) Language / Domain Convention**: standard Japanese typographic or financial accounting invariants (e.g. `△`/`▲` for negative numbers, `合計` for subtotals, standard rounding bounds).
- **(b) Derived from Page at Runtime**: dynamically computed from document elements (e.g. median glyph width, right-edge clustering, coordinate bounds).
- **(c) Fitted to This Page**: literal thresholds, expected counts, hardcoded account labels, or fixed geometric cutoffs.

| Assumption | Location | Class | Action / Justification |
| :--- | :--- | :---: | :--- |
| `indent_gap_glyphs = 0.5` | `parser/config.py:12` | (b) | **Keep**. Scaled at runtime by `median_glyph_width` (~4.5 pt). Groups intra-cluster indent jitter. |
| `col_x1_gap_glyphs = 3.0` | `parser/config.py:13` | (b) | **Keep**. Scaled by `median_glyph_width` (~27 pt). Prevents distinct numeric columns from merging. |
| `col_assign_glyphs = 2.0` | `parser/config.py:14` | (b) | **Keep**. Scaled by `median_glyph_width` (~18 pt). Tolerance for matching cells to column centroids. |
| `y_band_tol_pts = 2.0` | `parser/config.py:17` | (c) | **Justify**. Fixed 2.0 pt vertical tolerance for row grouping. Standard for 72-dpi PDFs, but sensitive to <0.5x coordinate scaling. |
| `detach_merge_y_tol_pts = 2.0` | `parser/config.py:18` | (c) | **Justify**. Fixed 2.0 pt tolerance for merging detached negative markers. Not triggered on `balance_sheet.pdf`. |
| `rounding_per_term = 0.5` | `parser/config.py:21` | (a) | **Keep**. Half-up rounding error bound per term under standard Japanese GAAP rounding. |
| `suspect_multiplier = 10.0` | `parser/config.py:22` | (a) | **Keep**. Accounting check severity threshold distinguishing rounding drift from parsing failure. |
| `header_zone_fallback_fraction = 0.15` | `parser/config.py:25` | (c) | **Justify**. Fallback when no metadata patterns match. Not triggered on `balance_sheet.pdf`. |
| `NEG_MARKERS = {'△', '▲'}` | `parser/pdf_extractor.py:13` | (a) | **Keep**. Japanese financial reporting invariant for negative values. |
| `NUM_OR_SEP_RE = ^\d[\d,]*$` | `parser/pdf_extractor.py:14` | (a) | **Keep**. Standard numeric comma-separated format. |
| Non-digit median glyph width calculation | `parser/pdf_extractor.py:36-50` | (b) | **Keep**. Derived dynamically from `page.chars`; bounded between 3.0 and 30.0 pt. |
| Word extraction tolerances `(x=3, y=3)` | `parser/pdf_extractor.py:55-56` | (c) | **Justify**. Default pdfplumber word aggregation parameters. |
| Detached marker proximity `1.5 * median_glyph_width` | `parser/pdf_extractor.py:82` | (b) | **Keep**. Dynamically scaled horizontal search window for preceding negative triangle. |
| `METADATA_HEADER_PATTERNS` (regexes) | `parser/header_parser.py:13-20` | (a) | **Keep**. Standard Japanese filing terminology (年, 月, 連結, 会計年度, 単位, 貸借対照表) to delimit header. |
| `UNIT_RE = 単位[：:]\s*([^\s)）]+)` | `parser/header_parser.py:22` | (a) | **Keep**. Standard Japanese disclosure syntax for reporting units. |
| `PAGE_NOTE_RE = ^[-－—―]?\s*\d+\s*[-－—―]?$` | `parser/header_parser.py:23` | (a) | **Keep**. Standard pagination footer format. |
| `TITLE_RE` (balance sheet title variants) | `parser/header_parser.py:24` | (a) | **Keep**. Recognizes 連結貸借対照表, 個別貸借対照表, 貸借対照表. |
| `AMENDMENT_RE` (訂正, 訂正前, 訂正後) | `parser/header_parser.py:25` | (a) | **Keep**. Japanese regulatory amendment disclosure markers. |
| Upper 40% page limit for header tokens | `parser/header_parser.py:42` | (c) | **Justify**. Prevents false-positive header matches on body table rows or footnotes. |
| Header bottom margin `+ 2.0` pt | `parser/header_parser.py:50` | (c) | **Justify**. Small safety margin separating header zone from first data row. |
| Page note lower 25% bound (`top < 0.75 * height`) | `parser/header_parser.py:64` | (c) | **Justify**. Universal pagination convention; footers are placed at the bottom of the page. |
| Default title fallback `"貸借対照表"` | `parser/header_parser.py:80` | (c) | **Justify**. Fallback string if title regex does not match. Not triggered on `balance_sheet.pdf`. |
| Default unit fallback `"千円"` | `parser/header_parser.py:81` | (a) | **Keep**. Japanese statutory reporting standard default unit when omitted. |
| Header-to-column distance `<= 3.0 * col_assign` | `parser/header_parser.py:136` | (b) | **Keep**. Dynamically matches period headers to column centroids using scaled thresholds. |
| Financial number regex `FINANCIAL_NUM_RE` | `parser/column_detector.py:14` | (a) | **Keep**. Isolates financial numbers with commas from bare dates, years, or page notes. |
| Numeric right-edge clustering (`col_x1_gap`) | `parser/column_detector.py:73` | (b) | **Keep**. Discovers column count and column right edges dynamically without preset counts. |
| Column centroid median calculation | `parser/column_detector.py:84` | (b) | **Keep**. Derived from cluster median; robust against slight rendering variations. |
| Indent uncertainty threshold `min_dist > 4.0` | `parser/indent_clusterer.py:43` | (c) | **Justify**. Empirical threshold for flagging uncertain levels. Not triggered on `balance_sheet.pdf`. |
| Page height default `1000.0` pt | `parser/indent_clusterer.py:52` | (c) | **Justify**. Fallback default argument; always overridden by caller `page_height`. |
| Indent clustering footer filter (`0.88`, `0.75`) | `parser/indent_clusterer.py:62-64` | (c) | **Justify**. Filters page numbers from polluting label indentation clustering. |
| Indent clustering threshold (`indent_gap`) | `parser/indent_clusterer.py:77` | (b) | **Keep**. Discovers hierarchy levels dynamically from observed x0 distribution. |
| Flat indentation check `len(clusters) < 2` | `parser/indent_clusterer.py:82` | (b) | **Keep**. Data-driven condition to detect documents lacking visual indentation. |
| Reading order sorting `(top, x0)` | `parser/row_assembler.py:34` | (a) | **Keep**. Natural reading order for Japanese financial statements. |
| Y-band grouping tolerance `y_band_tol * 2.0` | `parser/row_assembler.py:50` | (c) | **Justify**. Row clustering threshold. Standard for non-scaled 72-dpi documents. |
| Label zone definition `x1 < first_col_x1 - col_assign` | `parser/row_assembler.py:75` | (b) | **Keep**. Derived dynamically from leftmost detected financial column. |
| Cell column assignment `abs(x1 - col_x1) <= col_assign` | `parser/row_assembler.py:111` | (b) | **Keep**. Dynamically matches values to nearest column centroid. |
| Missing cell vs nil marker distinction | `parser/row_assembler.py:138` | (a) | **Keep**. Preserves semantic difference between empty whitespace and explicit nil dash. |
| `NET_SUFFIXES = ("（純額）", "(純額)")` | `parser/row_typer.py:9` | (a) | **Keep**. Standard Japanese financial reporting convention for net presenting lines. |
| `CONTRA_KEYWORDS = ("累計額", "引当金")` | `parser/row_typer.py:10` | (a) | **Keep**. Standard Japanese accounting keywords for contra accounts. |
| Row ending in `合計` is subtotal | `parser/row_typer.py:33` | (a) | **Keep**. Standard Japanese terminology for totals and subtotals. |
| Triplet stem-pairing algorithm | `parser/row_typer.py:46-89` | (a) | **Keep**. Japanese GAAP presentation convention pairing gross, accumulated depreciation, and net. |
| Sum parent path assignment | `parser/row_typer.py:96-121` | (b) | **Keep**. Derived dynamically from row hierarchy paths and triplet structure. |
| Value sign sanity check flags | `parser/row_typer.py:133-138` | (a) | **Keep**. Non-destructive verification flags for unexpected negative items. |
| `NIL_CHARS` (dash variants) | `parser/value_parser.py:10-16` | (a) | **Keep**. Standard Japanese typography for zero/nil disclosure. |
| Japanese date regex `YYYY年MM月DD日` | `parser/value_parser.py:66-68` | (a) | **Keep**. Standard Japanese calendar date syntax. |
| Flat-indent keyword fallback | `parser/hierarchy_builder.py:18-36` | (c) | **Justify**. Fallback heuristic for flat-indent synthetic test PDFs. Inactive on `balance_sheet.pdf`. |
| Stack non-parenting filter (`合計`, `（純額）`, `累計額`) | `parser/hierarchy_builder.py:61` | (a) | **Keep**. Structural accounting rule: totals and leaf triplet lines do not parent subsequent items. |
| Parent assignment via nearest preceding shallower row | `parser/hierarchy_builder.py:66-76` | (b) | **Keep**. Standard tree construction from indentation depth. |
| Net-value check equation `gross + contra == net` | `parser/consistency.py:22-75` | (a) | **Keep**. Fundamental accounting equation with ±1.0 unit rounding tolerance. |
| Subtotal tolerance formula `max(1, ceil(n/2))` | `parser/consistency.py:126` | (a) | **Keep**. Mathematically proven half-up rounding error propagation bound. |
| Hardcoded composite subtotal names (`固定資産合計`, `資産合計`) | `parser/consistency.py:108-121` | (c) | **REMOVED (Commit a372a13)**. Replaced with dynamic immediate-subordinate level discovery among sibling subtotals. |
| Hardcoded section keywords in coverage auditor | `parser/coverage_auditor.py:46, 69` | (c) | **REMOVED (Commit e0246e8)**. Replaced with dynamic `section_labels` derived from extracted table rows at `level == 0`. |

---

### 2. Ablations on `balance_sheet.pdf`

Each ablation was executed against `balance_sheet.pdf` and compared against the baseline output `output/balance_sheet_p1.json` (excluding `meta.parsed_at`).

#### Ablation 1: Japanese Keyword Fallbacks
- **1A. Consistency composite subtotal keywords (`parser/consistency.py:108-121`)**:
  - *Result*: 5 differences. 4 composite accounting checks were lost (`subtotal_固定資産合計` $\times 2$ periods, `grand_total_資産合計` $\times 2$ periods). Total checks dropped from 20 to 16.
  - *Finding*: Demonstrates that multi-tier subtotals rely on addend resolution; removing hardcoded keywords in favor of dynamic hierarchy-level discovery fully recovers all 20 checks with zero diffs.
- **1B. Header metadata regexes (`parser/header_parser.py:13-20`)**:
  - *Result*: 19 differences. Header boundary fell back to `page_height * 0.15` (126.3 pt), which cut through the header block. Header dates were unmapped (`date: None`), and the period date line was parsed as an extra row (row count shifted from 43 to 44).
  - *Finding*: The parser depends on standard Japanese metadata keywords to reliably distinguish the header zone from the data table.

#### Ablation 2: Label-Stem Triplet Pairing (`parser/row_typer.py:46-89`)
- *Result*: 57 structural differences.
  - 4 gross rows (`建物及び構築物`, `機械装置及び運搬具`, `リース資産`, `その他`) were classified as ordinary `item` rather than `gross`.
  - 4 contra rows (`減価償却累計額` $\times 4$) became `contra_standalone` instead of paired `contra`.
  - 4 net rows lost their `gross_parent` and `block_id`.
  - All 8 net-value accounting checks were eliminated (total checks dropped from 20 to 12).
- *Finding*: Label-stem pairing is fundamental to Japanese GAAP balance sheet parsing; without it, gross/contra/net accounting triplets cannot be reconciled.

#### Ablation 3: Flat-Indent Fallback (`parser/hierarchy_builder.py:18-36`)
- *Result*: Exactly 0 differences on `balance_sheet.pdf`.
- *Finding*: `balance_sheet.pdf` contains 5 clean, distinct indentation levels (centroids: 62.28, 75.24, 88.20, 101.28, 114.24 pt). `is_flat_indent` evaluated to `False`. The flat-indent heuristic is completely dormant on standard indented filings and exists solely as a fallback for degraded/flattened PDFs.

---

### 3. Invariance Checks in Memory

All checks were executed in memory on `extract_page_tokens` outputs without creating or using any external PDFs.

#### (i) Shuffled Word Order Invariance
- *Test*: Shuffled `tokens` across 5 random seeds (`42, 123, 999, 2026, 7`).
- *Result*: **0 differences across all seeds**.
- *Cause*: `row_assembler.py:34` explicitly sorts data tokens by `(round(top, 1), x0)`, `header_parser.py:142` sorts header tokens by `top`, and column/indent clustering operate on unique sorted coordinate sets. The parser is completely invariant to word extraction order.

#### (ii) Translated Coordinates Invariance
- *Test*: Uniform translation by $(dx, dy)$ for $(10, 10)$, $(50, 20)$, and $(-5, 15)$ pt with coordinate system origin translation.
- *Result*: **0 structural differences** (excluding coordinates).
- *Boundary Finding*: If coordinates are translated within a fixed page canvas ($y \to y + \Delta y$) without shifting the page origin, translations where $dy > 200$ pt cause `find_header_boundary` to find 0 header tokens.
- *Root Cause*: `header_parser.py:42` enforces `t["top"] < page_height * 0.40`. If the entire document is shifted down, header tokens exceed 40% of the page canvas, triggering the fallback fraction.

#### (iii) Scaled Coordinates Invariance
- *Test*: Uniform coordinate scaling by $S = 2.0\times$ and $S = 0.5\times$ with corresponding median glyph width scaling.
- *Result ($2.0\times$)*: **0 structural differences**. All rows, indent levels, columns, and accounting checks were preserved.
- *Result ($0.5\times$)*: **Catastrophic row collapse** (43 rows collapsed into 1 giant row).
- *Root Cause*: In `parser/config.py:17`, `y_band_tol_pts: float = 2.0` is an absolute point threshold that does not scale with glyph size. When coordinates were halved ($0.5\times$), the vertical gap between consecutive rows dropped below 2.0 pt. In `row_assembler.py:48-51`, `band_bottom < t["top"] - 2.0` evaluated to `False`, causing every row on the page to chain-merge into a single band. When `y_band_tol` was scaled proportionally ($1.0$ pt), all 43 rows and 20 checks were preserved.

---

### 4. Leakage and Isolation Verification

- A grep across all files in `parser/` and `main.py` found zero imports or read accesses to `eval/` or `gold`.
- Runtime module inspection during execution of `parse_pdf_page("balance_sheet.pdf")` confirmed `[m for m in sys.modules if 'eval' in m or 'gold' in m] == []`.
- Zero gold values, labels, or counts are used in any parser logic.

---

## Changes made (files + commits)

All changes were implemented on branch `chat-a` with atomic commits:

1. **Commit `a372a13`**: `refactor(consistency): dynamically discover composite subtotal addends by hierarchy depth`
   - **File**: `parser/consistency.py`
   - **Change**: Removed hardcoded Japanese label matches for composite subtotals (`固定資産合計`, `資産合計`, `有形固定資産合計`, `無形固定資産合計`, `投資その他の資産合計`, `流動資産合計`). Replaced with dynamic discovery of subordinate subtotals sharing the parent structural container at the immediate child indentation level (`target_level = child_levels[0]`). Replaced `sub.label == "資産合計"` with depth-based check `len(sub.structural_path) <= 2` for `grand_total`.
   - **Verification**: `output/balance_sheet_p1.json` is 100% byte-for-byte identical (excluding `meta.parsed_at`). All 20 accounting checks pass.

2. **Commit `e0246e8`**: `refactor(coverage): derive data zone start from table row labels instead of hardcoded sections`
   - **File**: `parser/coverage_auditor.py`
   - **Change**: Removed hardcoded tuple `("資産の部", "負債の部", "純資産の部", "流動資産", "固定資産")`. Derived the data zone trigger dynamically from `section_labels = tuple(r.label for r in rows if r.level == 0) or ((rows[0].label,) if rows else ())`.
   - **Verification**: `output/balance_sheet_p1.json` is 100% byte-for-byte identical (excluding `meta.parsed_at`). Coverage ratio remains 100.0% (74/74 tokens).

---

## Open decisions

The following design decisions are surfaced for user approval:

### 1. USER DECISION: Scale-Invariant Row Assembly Threshold (`y_band_tol`)
- **Context**: `y_band_tol_pts: float = 2.0` in `parser/config.py` is currently defined in absolute points. Our invariance check proved that scaling coordinates by $0.5\times$ causes all rows to collapse because inter-row gaps drop below 2.0 pt.
- **Options**:
  - *Option A (Recommended)*: Convert `y_band_tol` to scale dynamically with median glyph width (e.g. `y_band_tol_glyphs: float = 0.22`, yielding ~2.0 pt at 9.0 pt glyph width). This achieves full scale invariance across arbitrary resolutions/DPIs.
  - *Option B*: Retain `y_band_tol_pts = 2.0` as an absolute point threshold with the documented assumption that input PDFs must be standard 72-dpi point-space documents.
- **Recommendation**: Option A.

### 2. USER DECISION: Origin-Independent Header Search Boundary
- **Context**: `header_parser.py:42` enforces `t["top"] < page_height * 0.40`. If a PDF has a large top margin, non-zero origin, or vertical offset ($dy > 200$ pt), header metadata tokens are missed.
- **Options**:
  - *Option A (Recommended)*: Make the upper bound relative to the observed token coordinate range (`min_top + (max_bottom - min_top) * 0.40`).
  - *Option B*: Retain `page_height * 0.40` assuming standard top-of-page placement.
- **Recommendation**: Option A.

### 3. USER DECISION: Retention of Flat-Indent Fallback Keywords
- **Context**: `hierarchy_builder.py:18-36` contains a heuristic hierarchy assignment based on Japanese keywords (`の部`, `流動資産`, `固定資産`, etc.) that only triggers when `is_flat_indent` is true. It is dormant on `balance_sheet.pdf` but required by `tests/fixtures/stress_flatindent.pdf`.
- **Options**:
  - *Option A (Recommended)*: Retain as an explicit, documented fallback for flattened documents where spatial indentation is missing.
  - *Option B*: Remove the fallback keywords, accepting that flattened PDFs will output single-level (level 0) items.
- **Recommendation**: Option A, as it preserves resilience without affecting standard indented filings.

---

## Out-of-scope observations

1. **PyMuPDF / Fitz Deprecation Warning**:
   Running PyMuPDF outputs:
   ```
   FutureWarning: The fitz API is deprecated and will be removed in future. Use import pymupdf instead.
   ```
   Present in `parser/coverage_auditor.py:10` and `main.py`. Should be modernized to `import pymupdf` in a future cleanup.

2. **Pytest PYTHONPATH Sensitivity**:
   Running `pytest tests/test_parser.py` without `python3 -m pytest` or `PYTHONPATH=.` fails with `ModuleNotFoundError: No module named 'parser'`. Adding a root `pyproject.toml` or `conftest.py` with `sys.path.insert(0, str(Path(__file__).parent))` would streamline developer execution.

3. **Synthetic Test Fixture Regeneration**:
   The autouse fixture in `tests/test_parser.py:13-17` calls `generate_all_fixtures()`, rewriting `tests/fixtures/*.pdf` on every test run. This creates unstaged git modifications in protected fixture files. The fixture generation should only run if the fixture files do not already exist.
