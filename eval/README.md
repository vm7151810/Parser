# Japanese Financial Table Ground-Truth & Evaluation Harness

This directory contains the independent ground-truth ("gold") dataset, transcription protocol, formal specification, universal evaluation harness, and fault-injection test suite for evaluating PDF-to-table parsers on Japanese financial filing pages (連結貸借対照表 / Balance Sheets).

---

## 1. Zero-Leakage & Independent Transcription Guarantee

- **Target Document**: `balance_sheet.pdf` (Page 1 / Document Page 4: 資産の部).
- **Independent Transcription**: Transcribed purely by human visual inspection from the rendered page image (~200 DPI).
- **No Parser Code Consulted**: No parser code, extraction scripts, or parser outputs were read or referenced.
- **Verification Protocol**: Transcribed in two independent passes (top-to-bottom and bottom-to-top), diffed row-by-row, and reconciled. Full audit logs are recorded in [`transcription_log.md`](file:///home/mivikev/Desktop/Dev/UrAI/eval/transcription_log.md).
- **Status**: Marked as `"pending_verification"` with all ambiguous cells explicitly cataloged.

---

## 2. Directory Structure

```
eval/
├── gold.json                    # Minimal, parser-agnostic ground truth for balance_sheet.pdf
├── hierarchy_tree.txt           # Visually-verified indented tree (4 spaces per indent level)
├── verify_hierarchy.py          # Hierarchy verification script checking gold.json against tree
├── SPEC.md                      # Formal evaluation specification (metrics, alignment, schemas)
├── evaluate.py                  # Universal evaluation CLI harness
├── test_fault_injections.py     # Pytest suite with 8 automated fault injection tests
├── transcription_log.md         # 2-pass transcription, diff table, and accounting diagnostics
└── README.md                    # This documentation file
```

---

## 3. Minimal Parser-Agnostic Schema

The ground truth intentionally encodes **zero parser implementation concepts** (no bounding box coordinates, font sizes, indent cluster IDs, level numbers, or row-type taxonomies like `gross`/`contra`/`net`).

### 3.1. Document Structure (`gold.json`)
```json
{
  "status": "pending_verification",
  "eval_flags": {
    "score_hierarchy": true
  },
  "metadata": {
    "title": "連結貸借対照表",
    "subtitle": "３．連結財務諸表及び主な注記 （１）連結貸借対照表",
    "unit": "千円",
    "page_number": 4,
    "notes": ["（訂正後）"],
    "column_headers": [
      "前連結会計年度 (2025年３月31日)",
      "当連結会計年度 (2026年３月31日)"
    ]
  },
  "uncertain_cells": [
    {
      "row_index": 12,
      "column_index": 2,
      "label": "貸倒引当金",
      "printed_value": "△0",
      "reason": "Printed with triangle (△0); denotes negative zero provision balance."
    }
  ],
  "rows": [
    {
      "row_index": 1,
      "label": "資産の部",
      "parent_index": null,
      "parent_label": null,
      "values": [null, null]
    },
    {
      "row_index": 3,
      "label": "現金及び預金",
      "parent_index": 2,
      "parent_label": "流動資産",
      "values": ["2,002,429", "608,281"]
    },
    {
      "row_index": 12,
      "label": "貸倒引当金",
      "parent_index": 2,
      "parent_label": "流動資産",
      "values": ["△2,979", "△0"]
    },
    {
      "row_index": 13,
      "label": "流動資産合計",
      "parent_index": 2,
      "parent_label": "流動資産",
      "values": ["5,863,684", "3,377,407"]
    },
    {
      "row_index": 26,
      "label": "建設仮勘定",
      "parent_index": 15,
      "parent_label": "有形固定資産",
      "values": ["－", "4,553"]
    }
  ],
  "checks": [ ... ]
}
```

### 3.2. Core Design Invariants
1. **Value Cells (74 cells)** vs **No-Value Cells (12 cells)**:
   - Category and section header rows that carry no numeric values are stored as `null`.
   - Rows with printed values or nil indicators are stored as exact strings.
2. **Nil Indicator Fidelity (`"－"`)**:
   - Printed dashes (`－`, `—`, `-`) signify explicit zero balances.
   - Stored as verbatim strings (`"－"`), **never as `null`**.
   - **Nil matches ONLY nil**: A gold nil marker compared against `"0"` or `0.0` or `null` fails both exact and numeric matches.
3. **Negative Indicators**:
   - `△` (U+25B3) or `▲` (U+25B2) are preserved verbatim in printed strings (e.g., `"△2,979"`).
   - Negative zero is preserved as `"△0"`.
4. **Hierarchy Rules**:
   - `parent`: The row the human reader sees it indented under.
   - Subtotal rows close their section; therefore, the parent of a subtotal row is the specific section it closes (e.g., `流動資産合計` $\rightarrow$ `流動資産`).
   - Captured via **1-indexed `parent_index`** (1..N) and `parent_label`. Root items have `parent_index: null` and `parent_label: null`.

---

## 4. Evaluation Metrics & Logic

The evaluation harness strictly separates extraction accuracy from accounting diagnostics:

### 4.1. Row Sequence Alignment
- Because line item labels repeat (`減価償却累計額` 4 times, `その他` 4 times, `リース資産` 2 times), matching cannot be unordered.
- Rows are aligned via **Global Sequence Alignment (Needleman-Wunsch / LCS)** on normalized labels (`NFKC`, stripped whitespace and line breaks).
- Unmatched gold rows produce empty alignments; **all cells of an unmatched gold row fail automatically**, including null cells.

### 4.2. Accuracy Metrics
1. **Row Match Accuracy**:
   - Aligned rows matching normalized labels.
   - Reports Row Precision, Row Recall, and Row F1.
2. **Hierarchy Accuracy**:
   - For aligned rows, strictly checks that both `parent_label` (normalized) and 1-indexed `parent_index` match the aligned parent row.
3. **Cell Accuracy**:
   - **Value Cells (74 cells)**:
     - Exact Printed String Accuracy (verbatim string match).
     - Normalized Numeric Accuracy (signed float match within $10^{-4}$).
     - Precision, Recall, and F1.
     - `--fail-under-cell` gates specifically on Value Cells.
   - **No-Value Cells (12 cells)**:
     - Matches if and only if the row is aligned and the parser cell is `null`.
   - **Overall Cells (86 cells)**: Total combined accuracy.
4. **Numeric-Token Coverage (Multiset Match)**:
   - Multiset Counter comparison of all printed digit sequences (`\d+`).
   - Reports Token Precision, Token Recall, and Token F1.

### 4.3. Diagnostic Accounting Checks (Not Scored)
- Authored in `gold.json` under `"checks"` (10 checks across 2 periods = 20 total checks).
- Uses **signed printed values with `sign: 1` for all addends** (contra accounts parse directly to negative numbers).
- **Rounding Tolerance**: When $n$ figures rounded to thousand yen are summed:
  $$\text{Tolerance} = \max(1, \lceil n / 2 \rceil) \text{ thousand yen}$$
- Evaluated on aligned parser cells to diagnose parsing/OCR corruption. Differences within tolerance are classified as `SOURCE_ROUNDING` and pass. They do NOT affect accuracy scores.

---

## 5. Usage Guide

### 5.1. Evaluate Parser Output
Run the evaluation CLI with explicit pass/fail gates:

```bash
python3 eval/evaluate.py \
  --gold eval/gold.json \
  --input path/to/parser_output.json \
  --fail-under-cell 0.98 \
  --fail-under-row 0.95 \
  --fail-under-hierarchy 0.90 \
  --fail-under-numeric-token 0.95
```

### 5.2. Output Formats
- `--format text` (default): Human-readable terminal report with discrepancy breakdown.
- `--format markdown`: Clean Markdown table suitable for PR comments or CI summaries.
- `--format json`: Structured JSON dictionary for programmatic ingestion.

### 5.3. Exit Codes
- `0`: All specified `--fail-under-*` thresholds passed.
- `1`: One or more thresholds failed, or input parsing error occurred.
- Note: If no `--fail-under-*` flags are specified, the harness reports metrics and exits with `0` (zero hidden thresholds).

---

## 6. Self-Evaluation & Fault-Injection Tests

A comprehensive automated test suite (`eval/test_fault_injections.py`) validates the harness against 8 scenarios:

| # | Test Scenario | Expected Result | Verified By |
|---|---|---|---|
| 1 | **Gold vs. Gold** | 100% on all metrics, 20/20 accounting checks pass | `test_01_gold_vs_gold_self_eval` |
| 2 | **Drop Middle Row (`仕掛品`)** | Sequence alignment realigns; row & cell recall drop; dropped row listed | `test_02_fault_drop_middle_row` |
| 3 | **Duplicate Row (`売掛金`)** | Row precision drops (43/44); extra row detected | `test_03_fault_duplicate_row` |
| 4 | **Swap Columns** | Row match 100%; cell accuracy drops to ~2.7% | `test_04_fault_swap_columns` |
| 5 | **`"△0"` $\rightarrow$ `"0"`** | Detected as exact string mismatch on `貸倒引当金` col 2 | `test_05_fault_negative_zero_marker` |
| 6 | **`"－"` $\rightarrow$ `"0"`** | Fails exact and numeric match (nil only matches nil) | `test_06_fault_nil_to_zero` |
| 7 | **`"－"` $\rightarrow$ `null`** | Fails value cell match (missing cell) | `test_07_fault_nil_to_null` |
| 8 | **Remove `△` from Contra** | Fails cell match and triggers accounting check `INCONSISTENCY` | `test_08_fault_remove_delta_contra` |

Run the test suite:
```bash
python3 eval/test_fault_injections.py
# or via pytest:
pytest eval/test_fault_injections.py -v
```

---

## 7. Adapter Guide for External Parsers

External parsers can be evaluated by exporting their results to the neutral JSON format:

```python
import json

def export_to_neutral_eval_json(parser_result, output_path: str):
    data = {
        "column_headers": [
            "前連結会計年度 (2025年３月31日)",
            "当連結会計年度 (2026年３月31日)"
        ],
        "rows": []
    }
    for row in parser_result.rows:
        data["rows"].append({
            "label": row.label,                      # Raw printed label text
            "parent_index": row.parent_1_indexed,     # 1-indexed row number of parent, or None
            "parent_label": row.parent_label,         # Parent label text, or None
            "values": [                               # List of printed strings or None
                cell.printed_text if cell.has_value else None
                for cell in row.cells
            ]
        })
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## 8. Summary of Baseline Results on `balance_sheet.pdf`

Evaluating `eval/gold.json` against itself confirms the baseline ground-truth integrity:

```
=====================================================================
      JAPANESE FINANCIAL TABLE PARSER EVALUATION REPORT              
=====================================================================
 1. ROW MATCH (Page-Order Sequence Alignment):
    - Gold Rows:      43   | Parser Rows: 43  
    - Aligned Rows:   43  
    - Row Precision:  100.00%
    - Row Recall:     100.00%
    - Row F1 Score:   100.00%
---------------------------------------------------------------------
 2. HIERARCHY ACCURACY (Parent Visual Indent Match):
    - Hierarchy Match: 100.00%
---------------------------------------------------------------------
 3. CELL ACCURACY:
    [A] Value Cells (74 cells) -- Gated by --fail-under-cell:
        - Exact Printed String: 100.00% (74/74)
        - Normalized Numeric:   100.00% (74/74)
        - Precision / Recall:   100.00% / 100.00% (F1: 100.00%)
    [B] No-Value Cells (12 header cells):
        - Null Match Accuracy:  100.00% (12/12)
    [C] Overall Cells (86 total cells):
        - Exact String Accuracy: 100.00%
        - Numeric Accuracy:      100.00%
---------------------------------------------------------------------
 4. NUMERIC-TOKEN COVERAGE (Multiset Match):
    - Token Precision: 100.00%
    - Token Recall:    100.00%
    - Token F1 Score:  100.00%
=====================================================================
 DIAGNOSTICS: ACCOUNTING CONSISTENCY CHECKS
 (Reported separately with scaled rounding tolerance; NOT accuracy)
 Total Checks: 20 | Passed: 20 (Exact: 7, Rounding: 13) | Failed: 0
=====================================================================
```
