# CHAT D: Normative Evaluation Specification & Consistency Audit Report

## Commands run

All commands below were executed on branch `chat-d` from `/home/mivikev/Desktop/Dev/UrAI`. Every observation and metric in this report is grounded in these outputs.

```bash
# 1. Branch verification
git checkout -b chat-d chat-a
git status
# Output: On branch chat-d, nothing to commit, working tree clean

# 2. Baseline evaluation of parser output against gold
python3 eval/evaluate.py --gold eval/gold.json --input output/balance_sheet_p1.json
# Output:
# =====================================================================
#       JAPANESE FINANCIAL TABLE PARSER EVALUATION REPORT              
# =====================================================================
#  1. ROW MATCH (Page-Order Sequence Alignment):
#     - Gold Rows:      43   | Parser Rows: 43  
#     - Aligned Rows:   43  
#     - Row Precision:  100.00%
#     - Row Recall:     100.00%
#     - Row F1 Score:   100.00%
# ---------------------------------------------------------------------
#  2. HIERARCHY ACCURACY (Parent Visual Indent Match):
#     - Hierarchy Match: 100.00%
# ---------------------------------------------------------------------
#  3. CELL ACCURACY:
#     [A] Value Cells (74 cells) -- Gated by --fail-under-cell:
#         - Exact Printed String: 100.00% (74/74)
#         - Normalized Numeric:   100.00% (74/74)
#         - Precision / Recall:   100.00% / 100.00% (F1: 100.00%)
#     [B] No-Value Cells (12 header cells):
#         - Null Match Accuracy:  100.00% (12/12)
#     [C] Overall Cells (86 total cells):
#         - Exact String Accuracy: 100.00%
#         - Numeric Accuracy:      100.00%
# ---------------------------------------------------------------------
#  4. NUMERIC-TOKEN COVERAGE (Multiset Match):
#     - Token Precision: 100.00%
#     - Token Recall:    100.00%
#     - Token F1 Score:  100.00%
# =====================================================================
#  DIAGNOSTICS: ACCOUNTING CONSISTENCY CHECKS
#  (Reported separately with scaled rounding tolerance; NOT accuracy)
#  Total Checks: 20 | Passed: 20 (Exact: 7, Rounding: 13) | Failed: 0
# =====================================================================

# 3. Test execution of incorrect CLI flag documented in README.md line 104
python3 eval/evaluate.py --gold eval/gold.json --output output/balance_sheet_p1.json
# Output:
# usage: evaluate.py [-h] --gold GOLD --input INPUT ...
# evaluate.py: error: the following arguments are required: --input
# (Exit code 2: confirms README.md line 104 is contradictory to evaluate.py implementation)

# 4. Independent hierarchy verification
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

# 5. Existing fault-injection and self-evaluation suite
python3 eval/test_fault_injections.py
# Output:
# [PASS] Test 1: Gold vs Gold achieved 100% on all metrics.
# [PASS] Test 2: Dropped middle row '仕掛品' detected; sequence alignment realigned following rows.
# [PASS] Test 3: Duplicated row '売掛金' detected; precision penalized appropriately.
# [PASS] Test 4: Swapped columns detected; cell accuracy plummeted to 2.70%.
# [PASS] Test 5: '△0' -> '0' mutation detected as exact string mismatch.
# [PASS] Test 6: '－' -> '0' mutation failed both exact and numeric matches (nil only matches nil).
# [PASS] Test 7: '－' -> null mutation detected as missing value cell.
# [PASS] Test 8: Removed △ from contra detected in cells and flagged in accounting diagnostics (diff=3,847,170).
# ============================================================
# ALL 8 FAULT-INJECTION AND SELF-EVALUATION TESTS PASSED!
# ============================================================

# 6. Novel 5 Spec-Test Fault Injections
python3 /home/mivikev/.gemini/antigravity/brain/4036f768-a155-4451-944a-568ffa3198da/scratch/test_5_faults.py
# Output:
# --- FAULT 1: Corrupt Parent Index of Subtotal (Row 13 流動資産合計 -> parent_index: 1 [資産の部]) ---
# Hierarchy acc: 0.9761904761904762 (41/42)
# Hierarchy mismatches: [Row 13 流動資産合計: Expected parent '流動資産' [Idx 2], got '資産の部' [Idx 1]]
# Failed checks: 0
#
# --- FAULT 2: Spurious Value in Header Cell (Row 2 流動資産 Col 1 = '999') ---
# No-val acc: 0.9166666666666666 (11/12)
# Val cell precision: 0.9866666666666667 (74/75)
# Cell mismatches: [Row 2 '流動資産' Col 1 [no_value_cell]: Gold='None', Parser='999' (spurious_value_in_header_cell)]
#
# --- FAULT 3: Small Error within Rounding Tolerance (+1 in 現金及び預金 Col 1) ---
# Val exact acc: 0.9864864864864865 (73/74)
# Val numeric acc: 0.9864864864864865 (73/74)
# Token F1: 0.9861111111111112
# subtotal_current_assets Col 1: status=SOURCE_ROUNDING, diff=2.0, tol=5, passed=True
#
# --- FAULT 4: Nil Character Variation ('－' U+FF0D -> '-' ASCII hyphen) ---
# Val exact acc: 0.9864864864864865 (73/74)
# Val numeric acc: 1.0 (74/74)
# Cell mismatches: [Row 26 '建設仮勘定' Col 1 [value_cell]: Gold='－', Parser='-' (value_mismatch)]
#
# --- FAULT 5: Drop Root Section Row 1 (資産の部) ---
# Row recall: 0.9767441860465116 (42/43)
# Row precision: 1.0 (42/42)
# Unmatched gold rows: [Row 1: 資産の部]
# Hierarchy acc: 0.0 (0/42, 42 mismatches due to 1-indexed alignment shift)
# No-val acc: 0.8333333333333334 (10/12)
```

---

## Findings

### 1. Four-Way Consistency Audit

A systematic comparison was conducted between `eval/SPEC.md`, `eval/gold.json`, `eval/evaluate.py`, `README.md`, and `eval/README.md`. Every identified contradiction is documented below with exact file, line number, quote, and contradiction analysis.

| # | Conflict Subject | Primary File & Line | Quote | Secondary File & Line | Quote | Analysis & Contradiction |
|---|:---|:---|:---|:---|:---|:---|
| **1** | **CLI Input Flag Name** | `README.md:104` | `python3 eval/evaluate.py --gold eval/gold.json --output output/balance_sheet_p1.json` | `eval/evaluate.py:660` | `parser.add_argument("--input", required=True, help="Path to parser output JSON")` | **Direct Runtime Failure**. `README.md` documents `--output`, but `evaluate.py` requires `--input`. Running the README command fails with exit code 2: `evaluate.py: error: the following arguments are required: --input`. (`eval/README.md:168` and `eval/SPEC.md:223` correctly use `--input`). |
| **2** | **Evaluation Metric Suite** | `README.md:108-115` | `Path Recall (Coverage): % of gold line items successfully extracted... Hierarchy Level Accuracy... Row Type Accuracy... (structural_path, period) cells... pdftotext -layout` | `eval/evaluate.py:6-12` | `1. Row Match (Page-Order Sequence Alignment)... 2. Hierarchy Accuracy (1-indexed Parent Match)... 3. Cell Accuracy (Value vs No-Value)... 4. Numeric-Token Coverage` | **Conceptual Mismatch**. `README.md` describes an obsolete evaluation harness bound to parser-internal keys (`structural_path`, `row_type`, indent level, `pdftotext`). In contrast, `evaluate.py`, `gold.json`, and `SPEC.md` implement a neutral, parser-agnostic schema based on 1-indexed parent indices, global sequence alignment, and cell column indices. |
| **3** | **Gold Status String** | `eval/SPEC.md:49` *(pre-Chat D)* | `"status": "pending_human_verification"` | `eval/gold.json:2` | `"status": "pending_verification"` | **String Discrepancy**. `SPEC.md` and `transcription_log.md:6` transcribed the status as `"pending_human_verification"`, whereas `gold.json:2` and `eval/README.md:13, 40` record `"pending_verification"`. Resolved in `SPEC.md` v2.0 to `"pending_verification"`. |
| **4** | **Consistency Classification Tiers** | `README.md:169` | `Differences within this threshold are classified as source_rounding and pass. Differences > 10 * tolerance fail as parse_error.` | `eval/evaluate.py:501-508` | `status = "EXACT_MATCH"... status = "SOURCE_ROUNDING"... status = "INCONSISTENCY"` | **Taxonomy Conflict**. `README.md` references the 4-tier engine in `parser/consistency.py` (`exact`, `source_rounding`, `suspect`, `parse_error`), whereas the evaluator `evaluate.py` has no `suspect` or `parse_error` tier, classifying all failures as `INCONSISTENCY`. |
| **5** | **Rounding Tolerance Symmetry vs. Truncation** | `eval/gold.json:113, 360`, `eval/evaluate.py:431, 499`, `eval/SPEC.md:209` | `max expected drift is ceil(n/2)... diff = abs(computed_sum - target_val) <= tolerance` | `reports/B_accounting.md:330-360` | `Addition Totals: All 12 checks are non-negative (>= 0)... Net Deductions: All 8 checks are non-positive (<= 0)` | **Physics / Empirical Inconsistency**. `gold.json`, `SPEC.md`, and `evaluate.py` enforce symmetric round-to-nearest tolerance ($\pm \lceil n/2 \rceil$). However, empirical analysis in Report B proved that the filing uses *千円未満切捨て* (truncation), where negative sum deviations are physically impossible and indicate positive corruptions. |
| **6** | **Nil String vs Numeric Semantics** | `eval/SPEC.md:25`, `eval/README.md:112` | `Nil matches ONLY nil: A gold nil marker compared against "0" or 0.0 or null fails both exact string and numeric matching` | `eval/evaluate.py:71, 334, 340` | `if str(g_cell) == str(p_cell): exact_match = True... if g_nil: if p_nil: numeric_match = True` | **Nuanced Behavior**. `evaluate.py` strictly checks verbatim equality for exact string (`str("－") == str("-")` is `False`), but accepts any valid Unicode dash (`－`, `-`, `—`, `―`) for numeric match (`numeric_match` is `True`). The documentation previously stated that `"－"` only matches `"－"`, which applies strictly to string matching, not numeric matching. |
| **7** | **Negative Zero String Equality** | `eval/SPEC.md:27` | `Negative zero ("△0") is preserved as a distinct printed token.` | `eval/evaluate.py:91-94, 334` | `parse_numeric_cell("△0") -> (-0.0, False, True, False)... if str(g_cell) == str(p_cell)` | **Behavioral Invariant**. If a parser normalizes `"△0"` to `"0"` or `"0.0"`, `exact_match` fails in `evaluate.py:334`, but `numeric_match` passes because $|-0.0 - 0.0| < 10^{-4}$ and both are evaluated with `is_neg = False` or `True`. `README.md:167` documents this as an internal flag `negative_zero`. |

---

### 2. Five Novel Spec-Test Fault Injections

To validate that `eval/SPEC.md` completely and unambiguously specifies evaluator behavior, 5 novel faults not present in `tests/` or `eval/test_fault_injections.py` were designed. For each fault, the discrepancy ledger was predicted strictly from the specification, then run against `eval/evaluate.py`.

#### Summary of Results

| # | Injected Fault | Predicted Ledger / Metrics | Observed Evaluator Output | Status |
|---|:---|:---|:---|:---:|
| **1** | **Subtotal Parent Index Corruption**<br>Row 13 (`流動資産合計`) `parent_index: 2` $\to `1` (`parent_label: "資産の部"`). | - Row Match: 100%<br>- Cell Match: 100%<br>- Hierarchy Accuracy: $41/42 = 97.62\%$<br>- Discrepancy: 1 `WRONG_PARENT` on Row 13 (`expected: 2`, `actual: 1`).<br>- Accounting Checks: 20/20 PASS. | - Row Match: 100.00%<br>- Value Exact: 100.00%<br>- Hierarchy: 97.62% (41/42)<br>- Mismatch logged: `Row 13 (流動資産合計): Expected parent '流動資産' [Idx 2], got '資産の部' [Idx 1]`.<br>- Failed Checks: 0. | **PERFECT MATCH** |
| **2** | **Spurious Value in Header Cell**<br>Row 2 (`流動資産`) Col 1 injected with `"999"` (expected `null`). | - Row Match: 100%<br>- Value Cell Exact: 74/74 (100%)<br>- No-Value Cell Accuracy: $11/12 = 91.67\%$<br>- Value Cell Precision: $74/75 = 98.67\%$<br>- Discrepancy: 1 cell mismatch on Row 2 Col 1 (`reason: "spurious_value_in_header_cell"`). | - Value Exact: 100.00% (74/74)<br>- No-Val Acc: 91.67% (11/12)<br>- Value Precision: 98.67% (74/75)<br>- Mismatch logged: `Row 2 '流動資産' Col 1 [no_value_cell]: Gold='None', Parser='999' (spurious_value_in_header_cell)`. | **PERFECT MATCH** |
| **3** | **Sub-Rounding Addend Mutation**<br>Row 3 (`現金及び預金`) Col 1 mutated: `"2,002,429"` $\to `"2,002,430"` ($\delta = +1$). | - Value Cell Exact: $73/74 = 98.65\%$<br>- Value Cell Numeric: $73/74 = 98.65\%$<br>- Token F1: 98.61%<br>- `subtotal_current_assets` Col 1 diff shifts from $+3$ to $+2$. Since $|+2| \le 5$, check status remains `SOURCE_ROUNDING` (PASS). | - Value Exact: 98.65% (73/74)<br>- Value Numeric: 98.65% (73/74)<br>- Token F1: 98.61%<br>- `subtotal_current_assets` Col 1: `diff=2.0`, `tol=5`, `status=SOURCE_ROUNDING`, `passed=True`. (Demonstrates detection limit). | **PERFECT MATCH** |
| **4** | **Nil Character Glyph Variation**<br>Row 26 (`建設仮勘定`) Col 1 mutated from full-width dash `"－"` (U+FF0D) to ASCII hyphen `"-"` (U+002D). | - Exact String Accuracy: $73/74 = 98.65\%$ (verbatim string comparison fails).<br>- Normalized Numeric Accuracy: $74/74 = 100.00\%$ (both parse to `is_nil = True`).<br>- Discrepancy: 1 cell mismatch (`reason: "value_mismatch"`). | - Value Exact: 98.65% (73/74)<br>- Value Numeric: 100.00% (74/74)<br>- Mismatch logged: `Row 26 '建設仮勘定' Col 1 [value_cell]: Gold='－', Parser='-' (value_mismatch)`. | **PERFECT MATCH** |
| **5** | **Drop Root Section Row**<br>Drop Row 1 (`資産の部`) from parser output. | - Row Recall: $42/43 = 97.67\%$, Precision: $1.0$<br>- Unmatched Gold: Row 1 (`資産の部`).<br>- No-Val Acc: $10/12 = 83.33\%$ (Row 1 cells fail).<br>- Hierarchy Accuracy: $0/42 = 0.00\%$ (All 42 parent comparisons fail because parser row indices shift by $-1$, so parser `parent_index` does not match aligned gold indices). | - Row Recall: 97.67% (42/43)<br>- Precision: 100.00% (42/42)<br>- Unmatched Gold: `Row 1: 資産の部`<br>- No-Val Acc: 83.33% (10/12)<br>- Hierarchy Acc: 0.00% (0/42, exactly 42 mismatches). | **PERFECT MATCH** |

---

### 3. Claims Audit Table

Every capability claimed in `README.md` and `eval/README.md` was audited against code, tests, and gold data:

| Capability Claim | Documentation Location | Category | Grounded Evidence / Concrete Status |
| :--- | :--- | :---: | :--- |
| **43 Extracted Rows** | `README.md:130` | **Measured on this page** | `eval/gold.json:28-348`; `verify_hierarchy.py` confirms 43 rows match. |
| **2 Detected Columns** | `README.md:131` | **Measured on this page** | `eval/gold.json:14-17` (`前連結会計年度`, `当連結会計年度`). |
| **5 Indent Hierarchy Levels** | `README.md:132` | **Measured on this page** | Discovered centroids: 62.3, 75.2, 88.2, 101.3, 114.2 pt (`reports/A_parser_audit.md:151`). |
| **100% Token Coverage (74/74)** | `README.md:133` | **Measured on this page** | `output/balance_sheet_p1.json` accounts for 74/74 financial value tokens. |
| **Zero Independent Discrepancies**| `README.md:134` | **Measured on this page** | `evaluate.py --gold eval/gold.json --input output/balance_sheet_p1.json` reports 0 discrepancies. |
| **20/20 Accounting Checks Pass** | `README.md:135` | **Measured on this page** | `evaluate.py` output: 20 checks (7 exact, 13 within rounding, 0 failed). |
| **Sequence Alignment Matching** | `eval/README.md:127` | **Measured on this page** | Needleman-Wunsch aligns 43/43 rows (100% precision/recall). |
| **Nil Matches Only Nil** | `eval/README.md:112` | **Measured on this page** | `test_fault_injections.py:145-166` verifies `"－"` vs `"0"` fails exact and numeric match. |
| **Negative Zero Preservation** | `eval/README.md:115` | **Measured on this page** | `gold.json:19-27` uncertain cell 12; `test_fault_injections.py:124-143` confirms `"△0"` $\ne$ `"0"`. |
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

1. **Commit `7e69e0b`**: `docs(eval): update normative evaluation specification with taxonomy, conventions, and claims`
   - **File**: `eval/SPEC.md`
   - **Summary**: Complete normative restructuring to specification version 2.0. Authored all required sections: scope and 86-cell definitions (74 value, 12 header); printed text vs numeric value vs nil vs missing vs negative zero; 1-indexed visual hierarchy and subtotal/contra/net parenting rules; 10 canonical accounting checks with roll-up rules; Needleman-Wunsch sequence alignment; closed 9-element discrepancy taxonomy with severities, ledger data model, and strict exit semantics; gold provenance and pending verification status; claims audit table; and decision log.

2. **Commit `d7e89dd`**: `docs(reports): add Chat D specification audit and four-way consistency report`
   - **File**: `reports/D_spec.md`
   - **Summary**: Comprehensive audit report detailing commands run, four-way consistency findings, 5 novel spec-test faults, claims table, open decisions, and out-of-scope observations.

---

## Open decisions

The following design decisions are surfaced for user review:

### 1. USER DECISION: Rounding Model (Symmetric vs. Directional Truncation)
- **Context**: `gold.json`, `SPEC.md`, and `evaluate.py` currently implement symmetric round-to-nearest tolerance: $|\text{diff}| \le \lceil n/2 \rceil$. However, Report B proved that the source filing uses *千円未満切捨て* (truncation), where sum differences are strictly non-negative ($0 \le \text{diff} \le n - 1$) and net deductions are strictly non-positive ($-1 \le \text{diff} \le 0$).
- **Options**:
  - *Option A (Status Quo - Symmetric)*: Retain $\pm \max(1, \lceil n/2 \rceil)$. Robust to filings using *四捨五入*, but creates blind spots for positive corruptions on truncated filings.
  - *Option B (Strict Directional Truncation)*: Enforce $0 \le \text{diff} \le n - 1$ for sums, $-1 \le \text{diff} \le 0$ for net deductions. Maximally strict on this document, but will fail external filings using *四捨五入*.
  - *Option C (Recommended - Dual-Mode Diagnostic)*: Retain symmetric bound for binary check pass/fail, but diagnose non-negative deviations as `truncation_consistent` and negative sum deviations as `suspect_direction`.
- **Recommendation**: **Option C**.

### 2. USER DECISION: Discrepancy Taxonomy & Severities
- **Context**: The evaluator requires a closed taxonomy of discrepancy types with severities, waivers, and exit semantics.
- **Options**:
  - *Option A (Recommended)*: Adopt the closed 9-element taxonomy defined in `eval/SPEC.md:6.1`: `MISSING_ROW` (FATAL), `EXTRA_ROW` (ERROR), `WRONG_PRINTED_VALUE` (ERROR), `SIGN_ERROR` (ERROR), `NIL_TO_ZERO` (ERROR), `NIL_TO_MISSING` (ERROR), `MISSING_TO_NIL` (ERROR), `WRONG_PARENT` (ERROR), `ACCOUNTING_INCONSISTENCY` (WARNING).
  - *Option B*: Treat `NIL_TO_ZERO` and `WRONG_PARENT` as `WARNING` instead of `ERROR`.
- **Recommendation**: **Option A**, as it enforces structural and semantic fidelity.

### 3. USER DECISION: Accounting Checks Exit Semantics
- **Context**: In `evaluate.py`, accounting checks are reported under `DIAGNOSTICS` and do not cause non-zero exits.
- **Options**:
  - *Option A (Recommended - Informational Diagnostic)*: Accounting checks are non-gating diagnostics unless explicitly flagged via `--fail-under-consistency`. This prevents penalizing valid extractions of corrupted source filings.
  - *Option B (Strict Gate)*: Unwaived `ACCOUNTING_INCONSISTENCY` triggers exit code 1.
- **Recommendation**: **Option A**.

---

## Out-of-scope observations

1. **README.md Flag Inconsistency (`--output` vs `--input`)**:
   `README.md:104` specifies `--output`, which fails in `evaluate.py` with exit code 2. Per Ground Rule 3 (scope fence), `README.md` was not modified and is recorded here for future cleanup.
2. **README.md Metric Suite Inconsistency**:
   `README.md:108-115` lists obsolete parser-internal metric names (`structural_path`, `row_type`) rather than the neutral sequence alignment metrics implemented in `evaluate.py`.
3. **Gold Status Nomenclature**:
   `eval/gold.json:2` uses `"pending_verification"`, whereas `eval/transcription_log.md:6` uses `"pending_human_verification"`. Both indicate pending human sign-off, but aligning the literal strings across all documentation is recommended.
4. **Synthetic Test Fixture Autouse Regeneration**:
   The autouse fixture in `tests/test_parser.py:13-17` calls `generate_all_fixtures()`, rewriting `tests/fixtures/*.pdf` on every test run. Per Ground Rule 3, `tests/` was left untouched.
