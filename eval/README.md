# Japanese Financial Table Ground-Truth & Evaluation Harness

This directory contains the independent ground-truth ("gold") dataset, transcription protocol, formal specification, universal evaluation harness, and fault-injection test suite for evaluating PDF-to-table parsers on Japanese financial filing pages (Balance Sheets).

---

## 1. Ground-truth provenance

- **Target Document**: `balance_sheet.pdf`.
- **Transcription**: Transcribed from the rendered page image with AI assistance in two passes (top-down, bottom-up). Single author; not independently verified. The main validation is that all 20 accounting checks reconcile against the printed totals.
- **No Parser Code Consulted**: No parser code, extraction scripts, or parser outputs were read or referenced.
- **Audit Logs**: Full transcription records, diff table, and reconciliation details are recorded in [`transcription_log.md`](transcription_log.md).
- **Status**: Single-author ground truth, unverified by a second person; marked as `"pending_verification"` with all ambiguous cells explicitly cataloged.

---

## 2. Directory Structure

```
eval/
├── gold.json                    # Minimal, parser-agnostic ground truth for balance_sheet.pdf
├── hierarchy_tree.txt           # Visually-verified indented tree (4 spaces per indent level)
├── verify_hierarchy.py          # Hierarchy verification script checking gold.json against tree
├── SPEC.md                      # Formal evaluation specification (metrics, alignment, schemas)
├── evaluate.py                  # Universal evaluation CLI harness
├── test_fault_injections.py     # Pytest suite with 18 automated fault injection tests
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

Run the evaluation CLI with strict discrepancy ledger gating:

```bash
python3 eval/evaluate.py \
  --gold eval/gold.json \
  --input path/to/parser_output.json \
  --waivers path/to/waivers.json \
  --format text
```

### 5.2. Waivers Input File

Waivers allow known, reviewed discrepancies to pass CI without relaxing strict gating.
A waiver file is a JSON list of objects specifying `id`, `type`, `actual`, and a non-empty `reason`:

```json
[
  {
    "id": "R12:C2",
    "type": "sign_error",
    "actual": "0",
    "reason": "Source document uses triangle zero (△0); parser normalized to 0. Verified acceptable."
  }
]
```

- A waiver matches only if `id`, `type`, AND `actual` all match the ledger entry.
- Empty or whitespace reasons trigger a harness error (exit 2).
- Waived entries remain fully visible in the ledger.
- Unmatched (stale) waivers are listed as non-gating warnings.

### 5.3. Output Formats

- `--format text` (default): Human-readable terminal report: Discrepancy Ledger -> Stale Waivers -> Diagnostics -> Single Rates Footer.
- `--format markdown`: Clean Markdown table suitable for PR comments or CI summaries.
- `--format json`: Structured JSON dictionary for programmatic ingestion.

### 5.4. Exit Codes

- `0`: No unwaived discrepancies exist (empty ledger, or all entries waived).
- `1`: One or more unwaived discrepancies exist.
- `2`: Harness error (unreadable/schema-invalid input, malformed waiver file, or deprecated `--fail-under-*` flags).

---

## 6. Self-Evaluation & Fault-Injection Tests

The evaluation harness is validated against 18 automated fault-injection and self-consistency scenarios in `eval/test_fault_injections.py`.

Run the test suite (from the project root):

```bash
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
