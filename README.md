# Japanese Financial Statement PDF Parser (連結財務諸表パーサー)

A local, auditable, and production-grade Python parser that converts Japanese public company filing pages (such as EDINET/TDnet balance sheets / 連結貸借対照表) into structured JSON and GitHub Flavored Markdown tables.

---

## Key Features & Inductive Architecture

The parser avoids hard-coding layout geometries, coordinate cutoffs, or indent counts. All layout properties are derived dynamically at runtime:

1. **Glyph-Relative Spatial Scaling**:
   All clustering gaps scale with the document's median character glyph width (measured dynamically from `page.chars`), automatically adapting across varied font sizes and resolutions.
2. **Unbiased Column Discovery**:
   Numeric columns are detected by clustering right-edges (`x1`) of financial tokens (numbers with thousands separators, negative prefixes, or nil markers). Header dates, bare 4-digit years, and page numbers are strictly isolated so they never corrupt column seeding.
3. **Adaptive Indentation Clustering & Fallback**:
   Left-edge (`x0`) coordinates are clustered dynamically into discrete hierarchy levels. If indentation is completely flat (0–1 cluster), the parser falls back to Japanese structural keywords (`部`, `資産`, `合計`, `純額`, `累計額`).
4. **Key Separation & Robust Addend Lookup**:
   - `structural_path`: Indent-stack path uniquely identifying every row (used as canonical evaluation key).
   - `sum_parent_path`: Direct target for subtotal roll-ups (net rows roll up to the parent section, bypassing the gross parent).
   - `block_id`: Couples gross, contra, and net triplets for direct net-value reconciliation.
5. **Label-Stem Triplet Pairing & Deterministic Row Typing**:
   Gross/contra/net triplets are paired via label-stem matching (e.g. `建物及び構築物` $\leftrightarrow$ `建物及び構築物（純額）`). Standalone contras like `貸倒引当金` (allowance for doubtful accounts) are typed as `contra_standalone` and are properly summed as negative addends in subtotals.
6. **Multi-Tier Accounting Consistency with Scaled Rounding Tolerance**:
   Computes subtotals, net values, and grand totals with a scaled tolerance formula $\max(1, \lceil n/2 \rceil)$ for $n$ terms, distinguishing harmless source rounding from parsing errors.
7. **Independent Dual-Engine Coverage Audit**:
   Assigned table tokens are cross-checked against an independent extraction engine (`pdftotext -layout` / `pymupdf`) to guarantee zero orphan or phantom tokens.
8. **100% Local Execution**:
   Zero external API calls or network dependencies.

---

## Directory Structure

```
UrAI/
├── parser/
│   ├── __init__.py               # Package exports
│   ├── config.py                 # ParserConfig with glyph-relative multipliers
│   ├── table_model.py            # Dataclasses (Provenance, CellValue, Row, AccountingCheck, ParsedTable)
│   ├── value_parser.py           # △/▲/－ parser, NFKC, Japanese date normalizer
│   ├── pdf_extractor.py          # pdfplumber word & char extraction, detached marker merge
│   ├── header_parser.py          # Header boundary detection, unit, and period headers
│   ├── column_detector.py        # Dynamic numeric right-edge (x1) clustering
│   ├── indent_clusterer.py       # Adaptive x0 clustering & flat indent detection
│   ├── row_assembler.py          # Row grouping by y-band, missing vs nil cell attribution
│   ├── hierarchy_builder.py      # Stack-based structural_path generation
│   ├── row_typer.py              # Stem-matching gross/contra/net triplet detection & standalone contras
│   ├── consistency.py            # Subtotal, net-value, and grand-total consistency engine
│   ├── coverage_auditor.py       # Independent dual-engine audit (pdftotext cross-check)
│   ├── renderer.py               # JSON serialization and GFM Markdown renderer (with ⚑ flags)
│   └── pipeline.py               # 12-stage pipeline coordinator
├── tests/
│   └── test_parser.py            # Pytest suite covering unit tests and live sample validation
├── eval/
│   ├── gold.json                 # Hand-built gold table (pending human verification)
│   ├── evaluate.py               # Evaluation harness comparing parser output against gold.json
│   ├── SPEC.md                   # Formal evaluation specification (metrics, alignment, schemas)
│   ├── README.md                 # Eval directory documentation & transcription protocol
│   ├── transcription_log.md      # Two-pass independent transcription & verification log
│   ├── hierarchy_tree.txt        # Visually-verified indented hierarchy tree
│   ├── verify_hierarchy.py       # Hierarchy verification script checking gold.json against tree
│   └── test_fault_injections.py  # Pytest suite with automated fault injection tests
├── output/
│   ├── balance_sheet_p1.json     # Sample output JSON for balance_sheet.pdf
│   └── balance_sheet_p1.md       # Sample output Markdown for balance_sheet.pdf
├── agent/
│   ├── README.md                 # Master index & methodology of AI collaboration logs
│   ├── 01_creation_eval_ground_truth.md
│   ├── 02_creation_parser_pipeline.md
│   ├── 03_audit_chat_a_parser_agnosticism.md
│   ├── 04_audit_chat_b_accounting_verification.md
│   ├── 05_audit_chat_c_evaluator_discrepancy_ledger.md
│   └── 06_audit_chat_d_specification_audit.md
├── main.py                       # CLI entry point
├── requirements.txt              # Pinned Python dependencies
└── README.md                     # Documentation
```

---

## Installation & Setup

Requirements:
- Python 3.10+
- `poppler-utils` (for `pdftotext` audit; standard on Linux: `sudo apt install poppler-utils`)

Install Python dependencies:
```bash
pip install -r requirements.txt
```

---

## Usage

### Run Parser CLI

Parse a PDF page and produce both structured JSON and Markdown outputs:
```bash
python3 main.py balance_sheet.pdf --page 1 --out output/
```

Options:
- `pdf_path`: Path to input PDF file.
- `--page N`: Page number to parse (1-indexed, default: `1`).
- `--out DIR`: Output directory (default: `output/`).
- `--print-md`: Print the generated Markdown table directly to stdout.

### Run Evaluation Script

Evaluate the parser's output against a gold reference table:
```bash
python3 eval/evaluate.py --gold eval/gold.json --input output/balance_sheet_p1.json
```

Output metrics reported:
- **Discrepancy Ledger**: Enumerated list of discrepancies (missing rows, wrong values, sign errors, nil mismatches, hierarchy errors, metadata mismatches) with severity levels.
- **Row F1**: Precision/Recall/F1 on extracted row sequence alignment.
- **Hierarchy Accuracy**: Parent label and parent index match rate on aligned rows.
- **Cell Exact Accuracy**: Verbatim printed string match on value cells (74 cells).
- **Cell Numeric Accuracy**: Signed float match on value cells.
- **Token F1**: Multiset match of all printed digit sequences against gold.
- **Accounting Consistency** (non-gating diagnostic): Subtotals and net values checked with scaled rounding tolerance $\max(1, \lceil n/2 
ceil)$.
- **Exit codes**: 0 = no unwaived discrepancies, 1 = discrepancies exist, 2 = harness error.

### Run Automated Tests

Run pytest across all unit tests and live sample validation:
```bash
python3 -m pytest tests/ -v
```

---

## Results on `balance_sheet.pdf`

| Metric | Result | Notes |
|---|---|---|
| **Rows Extracted** | 43 | Full assets side (資産の部) |
| **Columns Detected** | 2 | 前連結会計年度, 当連結会計年度 |
| **Indent Levels** | 5 | Automatically discovered without presets |
| **Token Coverage** | 100.0% | 74 / 74 financial tokens accounted for |
| **Independent Discrepancies** | 0 | 0 unassigned, 0 phantom |
| **Accounting Checks** | 20 / 20 PASS | 7 exact, 13 within source-rounding tolerance |

### Accounting Breakdown:
- **Net-Value Checks (8/8 PASS)**:
  - 建物及び構築物 (前期: exact, 当期: diff 1, tol ±1)
  - 機械装置及び運搬具 (前期: exact, 当期: exact)
  - リース資産 (前期: diff 1, tol ±1, 当期: diff 1, tol ±1)
  - その他 (前期: exact, 当期: exact)
- **Subsection Subtotals (8/8 PASS)**:
  - 流動資産合計 (10 terms, tol ±5, 前期 diff 3, 当期 diff 2)
  - 有形固定資産合計 (6 terms, tol ±3, 前期 diff 1, 当期 diff 3)
  - 無形固定資産合計 (2 terms, tol ±1, 前期 diff 1, 当期 diff 1)
  - 投資その他の資産合計 (5 terms, tol ±3, 前期 diff 1, 当期 diff 1)
- **Composite Section Totals (2/2 PASS)**:
  - 固定資産合計 (3 subsections, tol ±2, 前期 diff 2, 当期 diff 0)
- **Grand Total (2/2 PASS)**:
  - 資産合計 (2 sections, tol ±1, 前期 diff 0, 当期 diff 1)

---

## Assumptions & Design Decisions

1. **Language Invariants vs. Layout Inductive**:
   - `△` (U+25B3) and `▲` (U+25B2) are treated as negative indicators.
   - `－` (U+FF0D), `—` (U+2014), and `−` (U+2212) are treated as explicit nil markers.
   - Rows ending in `合計` are subtotals.
   - Rows ending in `（純額）` are net values; their base stem corresponds to a preceding gross row.
   - Rows containing `引当金` without a net pair are standalone contra accounts and enter subtotal sums as negative values.
2. **Missing Cells vs. Nil Markers**:
   - A cell with an explicit dash (`－`) has `nil: true, numeric: null, flags: []`.
   - A cell with empty whitespace has `nil: false, numeric: null, flags: ["cell_missing"]`.
3. **Negative Zero (`△0`)**:
   Stored as `numeric: 0.0, negative: true, flags: ["negative_zero"]` to preserve auditability while maintaining valid JSON float serialization.
4. **Source Rounding Tolerance**:
   Financial figures published in thousands of yen (千円) undergo truncation or rounding in the source filing. When $n$ independently rounded numbers are summed, maximum expected drift is $\lceil n/2 \rceil$. Differences within this threshold are classified as `source_rounding` and pass. Differences $> 10 \times \text{tolerance}$ fail as `parse_error`.

---

## Known Limitations & Untested Gaps

1. **Single-Page Scope**:
   The sample is page 4 of a filing (assets side only). Multi-page tables spanning continuous page breaks without repeating headers are currently flagged and must be processed per page.
2. **Liabilities and Net Assets Side**:
   Only `資産の部` is present in `balance_sheet.pdf`. While `負債の部` and `純資産の部` follow identical Japanese conventions and are handled by the inductive parser, they have not been field-tested on this specific filing.
3. **Scanned / Rasterized Documents**:
   The parser requires a vector text layer (`pdfplumber` / `poppler`). Scanned image PDFs without embedded OCR are not supported without an external OCR pre-processor.
4. **Rotated Headers / Multi-Row Spanning Headers**:
   Tables with 90-degree rotated text or complex multi-tier merged column headers will be flagged as `column_merge_uncertain`.
