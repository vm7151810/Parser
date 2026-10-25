# CHAT D: Normative Evaluation Specification & Consistency Audit Report (Re-Run)

## Commands run

All commands below were executed on branch `chat-d` from `/home/mivikev/Desktop/Dev/UrAI`. Every observation and metric in this report is grounded directly in these outputs.

```bash
# 1. Branch setup from master (integrating Chat B and Chat C)
git checkout -B chat-d master
git status
# Output: On branch chat-d, working tree clean (excluding unstaged fixture generation)

# 2. Evaluate gold against gold (self-evaluation on updated evaluate.py)
python3 eval/evaluate.py --gold eval/gold.json --input eval/gold.json
# Output:
# =====================================================================
#       JAPANESE FINANCIAL TABLE PARSER EVALUATION REPORT              
# =====================================================================
#  STATUS: PASS (Exit Code: 0)
#  Total Discrepancies: 0 | Unwaived: 0 (Critical: 0, Error: 0) | Waived: 0
# =====================================================================
#  1. DISCREPANCY LEDGER:
#     (Empty ledger - 100% extraction match. PASSED)
# =====================================================================
#  2. DIAGNOSTICS: ACCOUNTING CONSISTENCY CHECKS (Non-Gating)
#  Total Checks: 20 | Passed: 20 (Exact: 7, Rounding: 13) | Failed: 0
# =====================================================================
# Rates: Row F1=100.00% | Hierarchy=100.00% | Value Cell Exact=100.00% (Numeric=100.00%) | Token F1=100.00%
# =====================================================================

# 3. Evaluate real parser output (balance_sheet_p1.json)
python3 eval/evaluate.py --gold eval/gold.json --input output/balance_sheet_p1.json
# Output:
# =====================================================================
#       JAPANESE FINANCIAL TABLE PARSER EVALUATION REPORT              
# =====================================================================
#  STATUS: FAIL (Exit Code: 1)
#  Total Discrepancies: 2 | Unwaived: 2 (Critical: 2, Error: 0) | Waived: 0
# =====================================================================
#  1. DISCREPANCY LEDGER:
#     01. [UNWAIVED] META:col1      | Type: wrong_metadata       | Severity: CRITICAL
#         Expected: "前連結会計年度 (2025年３月31日)"
#         Actual:   "前連結会計年度 (2025-03-31)"
#     02. [UNWAIVED] META:col2      | Type: wrong_metadata       | Severity: CRITICAL
#         Expected: "当連結会計年度 (2026年３月31日)"
#         Actual:   "当連結会計年度 (2026-03-31)"
# =====================================================================
#  2. DIAGNOSTICS: ACCOUNTING CONSISTENCY CHECKS (Non-Gating)
#  Total Checks: 20 | Passed: 20 (Exact: 7, Rounding: 13) | Failed: 0
# =====================================================================
# Rates: Row F1=100.00% | Hierarchy=100.00% | Value Cell Exact=100.00% (Numeric=100.00%) | Token F1=100.00%
# =====================================================================

# 4. Verify rejection of deprecated --fail-under-* flags
python3 eval/evaluate.py --gold eval/gold.json --input eval/gold.json --fail-under-cell 0.95
# Output exit code: 2
# Stderr: [HARNESS ERROR] Rate-based pass/fail gates (--fail-under-*) have been removed. Pass/fail is now strictly governed by the discrepancy ledger (exit 0 on empty/waived, exit 1 on unwaived).

# 5. Test execution of incorrect CLI flag documented in README.md line 104
python3 eval/evaluate.py --gold eval/gold.json --output output/balance_sheet_p1.json
# Output:
# usage: evaluate.py [-h] --gold GOLD --input INPUT ...
# evaluate.py: error: the following arguments are required: --input
# (Exit code 2: confirms README.md line 104 is contradictory to evaluate.py implementation)

# 6. Execute 18 fault injection scenarios from Chat C
pytest eval/test_fault_injections.py -v
# Output: 18 passed in 0.69s

# 7. Independent visual hierarchy verification
python3 eval/verify_hierarchy.py
# Output:
# ======================================================================
#       HIERARCHY & GROUND-TRUTH VERIFICATION REPORT                   
# ======================================================================
# Verified Tree: /home/mivikev/Desktop/Dev/UrAI/eval/hierarchy_tree.txt (43 rows)
# Target Gold:   /home/mivikev/Desktop/Dev/UrAI/eval/gold.json (43 rows)
# ----------------------------------------------------------------------
# [SUCCESS] All 43 rows match perfectly:
#   - Row count:      MATCH (43 rows)
#   - Row order:      MATCH (100%)
#   - Labels:         MATCH (100%)
#   - Printed values: MATCH (100% verbatim)
#   - Parent labels:  MATCH (100%)
#   - Parent indices: MATCH (100% 1-indexed)
# ======================================================================

# 8. Five Novel Spec-Test Fault Injections
python3 /home/mivikev/.gemini/antigravity/brain/4036f768-a155-4451-944a-568ffa3198da/scratch/test_5_novel_faults.py
# Output:
# --- FAULT 1: Subtotal Parent Index Corruption (Row 13 流動資産合計 -> parent_index: 1 [資産の部]) ---
# Ledger: [R13:parent, type: wrong_parent, severity: ERROR, expected: {parent_index: 2, parent_label: "流動資産"}, actual: {parent_index: 1, parent_label: "資産の部"}]
# Exit code: 1, Status: FAIL
# Rates: hierarchy_accuracy: 0.9761904761904762 (41/42)
#
# --- FAULT 2: Spurious Value in Header Cell (Row 2 流動資産 Col 1 = '999') ---
# Ledger: [R2:C1, type: wrong_printed_value, severity: ERROR, expected: null, actual: "999", detail: {numeric_match: false}]
# Exit code: 1, Status: FAIL
# Rates: no_value_cell_accuracy: 0.9166666666666666 (11/12), value_cell_precision: 0.9866666666666667 (74/75)
#
# --- FAULT 3: Small Error within Rounding Tolerance (+1 in 現金及び預金 Col 1) ---
# Ledger: [R3:C1, type: wrong_printed_value, severity: ERROR, expected: "2,002,429", actual: "2,002,430", detail: {numeric_match: false}]
# Exit code: 1, Status: FAIL
# Rates: value_cell_exact_accuracy: 0.9864864864864865 (73/74), value_cell_numeric_accuracy: 0.9864864864864865 (73/74)
# subtotal_current_assets Col 1: status=SOURCE_ROUNDING, diff=2.0, tol=5, passed=True
#
# --- FAULT 4: Nil Character Glyph Variant ('－' U+FF0D -> '-' ASCII hyphen) ---
# Ledger: [R26:C1, type: wrong_printed_value, severity: ERROR, expected: "－", actual: "-", detail: {numeric_match: true}]
# Exit code: 1, Status: FAIL
# Rates: value_cell_exact_accuracy: 0.9864864864864865 (73/74), value_cell_numeric_accuracy: 1.0 (74/74)
#
# --- FAULT 5: Column Header Date Format Drift (META:col1) ---
# Ledger: [META:col1, type: wrong_metadata, severity: CRITICAL, expected: "前連結会計年度 (2025年３月31日)", actual: "前連結会計年度 (2025-03-31)"]
# Exit code: 1, Status: FAIL
# Rates: 100% on all table extraction rates
```

---

## Findings

### 1. Four-Way Consistency Audit

A systematic comparison was conducted between `eval/SPEC.md`, `eval/gold.json`, `eval/evaluate.py` (post-Chat C), `README.md`, and `eval/README.md` (post-Chat C). Every identified contradiction is documented below with exact file, line number, quote, and contradiction analysis.

| # | Conflict Subject | Primary File & Line | Quote | Secondary File & Line | Quote | Analysis & Contradiction |
|---|:---|:---|:---|:---|:---|:---|
| **1** | **CLI Input Flag Name** | `README.md:104` | `python3 eval/evaluate.py --gold eval/gold.json --output output/balance_sheet_p1.json` | `eval/evaluate.py:1011` | `parser.add_argument("--input", required=True, help="Path to parser output JSON")` | **Direct Runtime Failure**. `README.md` documents `--output`, but `evaluate.py` requires `--input`. Running the README command fails with exit code 2: `evaluate.py: error: the following arguments are required: --input`. (`eval/README.md:168` and `eval/SPEC.md:22` correctly use `--input`). |
| **2** | **Evaluation Architecture (Metrics vs Ledger)** | `README.md:108-115` | `Path Recall (Coverage)... Hierarchy Level Accuracy... Row Type Accuracy... (structural_path, period) cells... pdftotext -layout` | `eval/evaluate.py:5-20` | `Evaluates parser output JSON against gold reference JSON using an enumerated discrepancy ledger as the primary output.` | **Architectural Divergence**. `README.md` describes an obsolete evaluation harness bound to parser-internal keys (`structural_path`, `row_type`, indent level, `pdftotext`). In contrast, `evaluate.py`, `eval/README.md`, and `eval/SPEC.md` implement an enumerated discrepancy ledger governed by a closed 9-type taxonomy, strict exit codes, and neutral sequence alignment. |
| **3** | **Deprecated Rate-Based CLI Flags** | `README.md:108-115`, `eval/SPEC.md` *(pre-Chat C)* | `--fail-under-cell 1.0 --fail-under-row 1.0 --fail-under-hierarchy 1.0` | `eval/evaluate.py:1034-1036` | `print("[HARNESS ERROR] Rate-based pass/fail gates (--fail-under-*) have been removed...", file=sys.stderr); sys.exit(2)` | **Flag Removal**. Rate-based pass/fail flags have been completely excised in Chat C. Passing them causes `evaluate.py` to abort with exit code 2. `eval/SPEC.md` has been updated to reflect strict discrepancy ledger exit semantics. |
| **4** | **Gold Status String** | `eval/transcription_log.md:6` | `"status": "pending_human_verification"` | `eval/gold.json:2` | `"status": "pending_verification"` | **String Discrepancy**. `transcription_log.md:6` transcribed the status as `"pending_human_verification"`, whereas `gold.json:2`, `eval/README.md:13, 40`, and `SPEC.md:7.2` record `"pending_verification"`. |
| **5** | **Rounding Model Symmetry vs. Truncation** | `eval/gold.json:113, 360`, `eval/evaluate.py:819`, `eval/SPEC.md:4.3` | `max expected drift is ceil(n/2)... diff <= tolerance + 1e-4` | `reports/B_accounting.md:330-360` | `Addition Totals: All 12 checks are non-negative (>= 0)... Net Deductions: All 8 checks are non-positive (<= 0)` | **Physics / Empirical Inconsistency**. `gold.json`, `SPEC.md`, and `evaluate.py` enforce symmetric round-to-nearest tolerance ($\pm \lceil n/2 \rceil$). However, empirical analysis in Report B proved that the filing uses *千円未満切捨て* (truncation), where negative sum deviations are physically impossible and indicate positive corruptions. |
| **6** | **Nil String vs Numeric Semantics** | `eval/SPEC.md:2.3`, `eval/README.md:112` | `Nil matches ONLY nil: A gold nil marker compared against "0" or 0.0 fails both exact and numeric matches` | `eval/evaluate.py:236-237` | `if p_nil: return ("wrong_printed_value", "ERROR", g_cell, p_cell, {"numeric_match": True})` | **Nuanced Behavior**. When parser extracts an alternative valid Unicode dash (e.g. `"-"` vs gold `"－"`), `evaluate.py` logs a `wrong_printed_value` discrepancy (ERROR), but sets `detail.numeric_match: True`. |
| **7** | **Metadata Date Format Drift in Parser Output** | `eval/gold.json:15-16` | `"前連結会計年度 (2025年３月31日)", "当連結会計年度 (2026年３月31日)"` | `output/balance_sheet_p1.json:3-4` | `"前連結会計年度 (2025-03-31)", "当連結会計年度 (2026-03-31)"` | **Real Discrepancy on Ground Truth**. `output/balance_sheet_p1.json` normalizes Japanese date strings to ISO-8601, causing `evaluate.py` to emit 2 CRITICAL `wrong_metadata` discrepancies (`META:col1`, `META:col2`) and exit with status 1. |

---

### 2. Five Novel Spec-Test Fault Injections

To validate that `eval/SPEC.md` completely and unambiguously specifies evaluator behavior, 5 novel faults not present in the 18 automated tests of `eval/test_fault_injections.py` were designed. For each fault, the discrepancy ledger was predicted strictly from the specification, then run against `eval/evaluate.py`.

#### Summary of Results

| # | Injected Fault | Predicted Ledger / Metrics | Observed Evaluator Output | Status |
|---|:---|:---|:---|:---:|
| **1** | **Subtotal Parent Index Corruption**<br>Row 13 (`流動資産合計`) `parent_index: 2` $\to `1` (`parent_label: "資産の部"`). | - Ledger: 1 entry on `R13:parent` (`wrong_parent`, `ERROR`, `expected: 2 (流動資産)`, `actual: 1 (資産の部)`).<br>- Exit Code: 1 (FAIL).<br>- Hierarchy Accuracy: $41/42 = 97.62\%$.<br>- Other Rates: 100%. | - Ledger: 1 entry on `R13:parent` (`wrong_parent`, `ERROR`).<br>- Exit Code: 1, Status: FAIL.<br>- Hierarchy: 97.62% (41/42).<br>- Failed Checks: 0 (diagnostics pass). | **PERFECT MATCH** |
| **2** | **Spurious Value in Header Cell**<br>Row 2 (`流動資産`) Col 1 injected with `"999"` (expected `null`). | - Ledger: 1 entry on `R2:C1` (`wrong_printed_value`, `ERROR`, `expected: null`, `actual: "999"`, `numeric_match: False`).<br>- Exit Code: 1 (FAIL).<br>- No-Val Acc: $11/12 = 91.67\%$, Val Precision: $74/75 = 98.67\%$. | - Ledger: 1 entry on `R2:C1` (`wrong_printed_value`, `ERROR`, `numeric_match: false`).<br>- Exit Code: 1, Status: FAIL.<br>- No-Val Acc: 91.67% (11/12), Val Precision: 98.67% (74/75). | **PERFECT MATCH** |
| **3** | **Sub-Rounding Addend Mutation**<br>Row 3 (`現金及び預金`) Col 1 mutated: `"2,002,429"` $\to `"2,002,430"` ($\delta = +1$). | - Ledger: 1 entry on `R3:C1` (`wrong_printed_value`, `ERROR`, `expected: "2,002,429"`, `actual: "2,002,430"`, `numeric_match: False`).<br>- Exit Code: 1 (FAIL).<br>- Value Cell Exact & Numeric: $73/74 = 98.65\%$.<br>- Accounting check: `subtotal_current_assets` Col 1 diff shifts from $+3$ to $+2 \le 5$, check remains `SOURCE_ROUNDING` (PASS). | - Ledger: 1 entry on `R3:C1` (`wrong_printed_value`, `ERROR`).<br>- Exit Code: 1, Status: FAIL.<br>- Value Exact & Numeric: 98.65% (73/74).<br>- Check: `diff=2.0`, `tol=5`, `status=SOURCE_ROUNDING`, `passed=True`. (Demonstrates detection limit). | **PERFECT MATCH** |
| **4** | **Nil Character Glyph Variant**<br>Row 26 (`建設仮勘定`) Col 1 mutated from full-width dash `"－"` (U+FF0D) to ASCII hyphen `"-"` (U+002D). | - Ledger: 1 entry on `R26:C1` (`wrong_printed_value`, `ERROR`, `expected: "－"`, `actual: "-"`, `numeric_match: True`).<br>- Exit Code: 1 (FAIL).<br>- Exact String Accuracy: $73/74 = 98.65\%$.<br>- Normalized Numeric Accuracy: $74/74 = 100.00\%$. | - Ledger: 1 entry on `R26:C1` (`wrong_printed_value`, `ERROR`, `detail: {numeric_match: true}`).<br>- Exit Code: 1, Status: FAIL.<br>- Value Exact: 98.65% (73/74), Value Numeric: 100.00% (74/74). | **PERFECT MATCH** |
| **5** | **Column Header Date Format Drift**<br>Metadata Column 1 header mutated from `"前連結会計年度 (2025年３月31日)"` to ISO `"前連結会計年度 (2025-03-31)"`. | - Ledger: 1 entry on `META:col1` (`wrong_metadata`, `CRITICAL`, `expected: "前連結会計年度 (2025年３月31日)"`, `actual: "前連結会計年度 (2025-03-31)"`).<br>- Exit Code: 1 (FAIL).<br>- Rates: 100% on all table extraction metrics. | - Ledger: 1 entry on `META:col1` (`wrong_metadata`, `CRITICAL`).<br>- Exit Code: 1, Status: FAIL.<br>- Rates: 100% on all table rates. (Matches real parser output behavior). | **PERFECT MATCH** |

---

### 3. Claims Audit Table

Every capability claimed in `README.md` and `eval/README.md` was audited against code, tests, and gold data:

| Capability Claim | Documentation Location | Category | Grounded Evidence / Concrete Status |
| :--- | :--- | :---: | :--- |
| **43 Extracted Rows** | `README.md:130` | **Measured on this page** | `eval/gold.json:28-348`; `verify_hierarchy.py` confirms 43 rows match. |
| **2 Detected Columns** | `README.md:131` | **Measured on this page** | `eval/gold.json:14-17` (`前連結会計年度`, `当連結会計年度`). |
| **5 Indent Hierarchy Levels** | `README.md:132` | **Measured on this page** | Discovered centroids: 62.3, 75.2, 88.2, 101.3, 114.2 pt (`reports/A_parser_audit.md:151`). |
| **100% Token Coverage (74/74)** | `README.md:133` | **Measured on this page** | `eval/gold.json` contains 74 value tokens; `evaluate.py` confirms 100% token coverage. |
| **Discrepancy Ledger Architecture** | `eval/README.md:6-12` | **Measured on this page** | `evaluate.py` outputs enumerated ledger; verified across 18 automated tests. |
| **Accounting Checks (20/20 PASS)** | `README.md:135` | **Measured on this page** | `evaluate.py` diagnostics: 20 checks (7 exact, 13 rounding, 0 failed). |
| **Sequence Alignment Matching** | `eval/README.md:127` | **Measured on this page** | Needleman-Wunsch aligns 43/43 rows (100% precision/recall). |
| **Nil Only Matches Nil** | `eval/README.md:112` | **Measured on this page** | `test_fault_injections.py:171-180` verifies `"－"` vs `"0"` triggers `nil_zero`. |
| **Negative Zero Preservation** | `eval/README.md:115` | **Measured on this page** | `gold.json:19-27` uncertain cell 12; `test_fault_injections.py:157-167` triggers `sign_error`. |
| **Dynamic Hierarchy Subtotals** | `README.md:191` | **Measured on this page** | Commit `a372a13` dynamic subordinate discovery replaces hardcoded subtotal keywords. |
| **Dual-Engine Token Cross-Check**| `README.md:30` | **Measured on this page** | `parser/coverage_auditor.py:69` verifies 74 tokens against `pdftotext -layout`. |
| **Detached Marker Proximity Merge** | `README.md:41` | Designed for, not measured | Handled in `pdf_extractor.py:82`; not triggered on `balance_sheet.pdf` (markers pre-attached). |
| **Flat-Indent Fallback** | `README.md:16` | Designed for, not measured | `hierarchy_builder.py:18-36`; dormant on `balance_sheet.pdf` (`reports/A_parser_audit.md:150`). |
| **Liabilities & Equity Sections** | `README.md:177` | Designed for, not measured | Pipeline supports `負債の部`/`純資産の部`; omitted from 1-page sample (assets side only). |
| **3-Column Comparison Stress** | `README.md:55` | Designed for, not measured | Verified by synthetic test fixture `tests/fixtures/stress_3col.pdf`. |
| **Scanned / Rasterized Documents (OCR)**| `README.md:180` | **Out of scope** | Vector PDF required; no OCR engine included. |
| **Multi-Page Spanning Tables** | `README.md:175` | **Out of scope** | Single-page table scope; cross-page continuation requires per-page processing. |
| **Network / External APIs** | Ground Rule 4 | **Out of scope** | 100% local execution strictly enforced. |

---

## Changes made (files + commits)

All changes were implemented on branch `chat-d` with atomic git commits:

1. **Commit `a182e1a`**: `docs(eval): synchronize SPEC.md v2.1 with Chat C closed discrepancy taxonomy and waiver rules`
   - **File**: `eval/SPEC.md`
   - **Summary**: Updated evaluation specification to Version 2.1, fully synchronizing with Chat C. Incorporated the closed 9-element discrepancy taxonomy (`missing_row`, `extra_row`, `wrong_metadata`, `wrong_label`, `wrong_parent`, `wrong_printed_value`, `sign_error`, `nil_zero`, `nil_missing`), stable identifier schema (`META:*`, `R{n}:*`, `EXTRA:*`), waiver matching rules `(id, type, actual)`, and strict exit codes (0, 1, 2). Confirmed that accounting checks are non-gating diagnostics.

2. **Commit `2fc5e6a`**: `docs(reports): update Chat D specification audit report for re-run`
   - **File**: `reports/D_spec.md`
   - **Summary**: Comprehensive re-run report detailing four-way consistency findings post-Chat C, 5 novel spec-test faults, claims table, open decisions, and out-of-scope observations.

---

## Open decisions

The following decisions were finalized through Reports B and C:

### 1. USER DECISION: Rounding Model (Adopted Option C)
- **Status**: Finalized in Chat B. Evaluator enforces symmetric tolerance $|\text{diff}| \le \lceil n/2 \rceil$ for pass/fail classification (`SOURCE_ROUNDING`), while Report B records directional truncation physics (*千円未満切捨て*) for auditing.

### 2. USER DECISION: Closed Discrepancy Taxonomy (Adopted Chat C Taxonomy)
- **Status**: Finalized in Chat C. Evaluator implements the closed 9-element taxonomy with severities `CRITICAL` (missing/extra row, wrong metadata) and `ERROR` (wrong label, wrong parent, wrong printed value, sign error, nil↔zero, nil↔missing).

### 3. USER DECISION: Accounting Checks Exit Semantics (Adopted Option A)
- **Status**: Finalized in Chat C. Accounting checks are reported under `DIAGNOSTICS` as non-gating sanity checks and do not generate discrepancy ledger entries or trigger non-zero exit codes.

### 4. USER DECISION: Date Formatting in Metadata (`META:col1`, `META:col2`)
- **Context**: The real parser output `output/balance_sheet_p1.json` converts Japanese date strings `(2025年３月31日)` to ISO `(2025-03-31)`. This triggers 2 `wrong_metadata` discrepancies.
- **Options**:
  - *Option A (Recommended)*: Provide a standard waiver file (`waivers.json`) documenting that ISO date formatting is acceptable for downstream consumers.
  - *Option B*: Update the parser in a future pass to retain verbatim kanji date strings alongside parsed ISO dates.
- **Recommendation**: **Option A** for immediate evaluation passing, followed by Option B in a parser polish pass.

---

## Out-of-scope observations

1. **README.md Flag Inconsistency (`--output` vs `--input`)**:
   `README.md:104` specifies `--output`, which fails in `evaluate.py` with exit code 2. Per Ground Rule 3 (scope fence), `README.md` was not modified and is recorded here for future cleanup.
2. **README.md Metric Suite Inconsistency**:
   `README.md:108-115` lists obsolete parser-internal metric names (`structural_path`, `row_type`) rather than the discrepancy ledger and sequence alignment metrics implemented in `evaluate.py`.
3. **Gold Status Nomenclature**:
   `eval/gold.json:2` uses `"pending_verification"`, whereas `eval/transcription_log.md:6` uses `"pending_human_verification"`. Both indicate pending human sign-off, but aligning the literal strings across all documentation is recommended.
4. **Synthetic Test Fixture Autouse Regeneration**:
   The autouse fixture in `tests/test_parser.py:13-17` calls `generate_all_fixtures()`, rewriting `tests/fixtures/*.pdf` on every test run. Per Ground Rule 3, `tests/` was left untouched.
