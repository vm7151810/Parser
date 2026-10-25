# CHAT C: Evaluator Discrepancy Ledger Report

## Commands run

```bash
# 1. Branch setup
git checkout -b chat-c
# Output: Switched to a new branch 'chat-c'

# 2. Existing fault tests baseline before modifications
pytest eval/test_fault_injections.py -v
# Output: 8 passed in 0.26s

# 3. Check row differences between Col 1 and Col 2 in gold.json
python3 -c "
import json
with open('eval/gold.json') as f:
    d = json.load(f)
diffs = [r for r in d['rows'] if len(r.get('values', [])) == 2 and r['values'][0] is not None and r['values'][0] != r['values'][1]]
print(f'Rows with differing col 1 and 2: {len(diffs)}')
"
# Output: Rows with differing col 1 and 2: 36 (Row 37 関係会社株式 has identical ['1,123', '1,123'])

# 4. Commit predictions for all 18 fault-injection scenarios BEFORE implementation
git add eval/test_fault_injections.py
git commit -m "predict: record expected discrepancy ledgers for 8 fault tests and 10 new scenarios"
# Output: [chat-c 69a5600] predict: record expected discrepancy ledgers for 8 fault tests and 10 new scenarios

# 5. Execute updated evaluate.py against full test suite
pytest eval/test_fault_injections.py -v
# Output: 18 passed in 0.70s

# 6. Verify synthetic regression tests in tests/
python3 -m pytest tests/
# Output: 10 passed, 1 warning in 6.76s

# 7. Evaluate gold against gold (self-evaluation)
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

# 8. Evaluate current real parser output (balance_sheet_p1.json)
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

# 9. Test deprecated --fail-under-* flags rejection
python3 eval/evaluate.py --gold eval/gold.json --input eval/gold.json --fail-under-cell 0.95
# Output exit code: 2
# Stderr: [HARNESS ERROR] Rate-based pass/fail gates (--fail-under-*) have been removed. Pass/fail is now strictly governed by the discrepancy ledger (exit 0 on empty/waived, exit 1 on unwaived).
```

---

## Findings

### 1. Closed Taxonomy of Discrepancies

The evaluator replaces rate-based metric gating with an enumerated discrepancy ledger. A closed taxonomy of 9 discrepancy types with explicit severities governs all evaluation findings:

| Discrepancy Type | Severity | Scope | Description / Trigger Condition |
|---|---|---|---|
| `missing_row` | `CRITICAL` | Row | A row defined in the gold standard is absent from the parser output sequence alignment. Subsumes its value cells (`subsumed_cells`) and records any child rows orphaned by its removal (`orphaned_children`). |
| `extra_row` | `CRITICAL` | Row | A row output by the parser that does not correspond to any row in the gold reference (spurious row insertion or duplicate). |
| `wrong_metadata` | `CRITICAL` | Document / Table | Metadata mismatch in unit (`META:unit`), column count (`META:columns`), or column header text (`META:col{n}`). A column count mismatch compares only shared columns and lists ignored columns in detail. |
| `wrong_label` | `ERROR` | Row | Within a gap between aligned anchor rows, an unmatched gold row and unmatched parser row share an identical, non-empty printed value tuple. The pair is aligned for hierarchy verification, emitting `wrong_label` on `R{n}:label`. |
| `wrong_parent` | `ERROR` | Hierarchy | An aligned row's visual parent (`parent_label` or resolved `parent_index`) does not match the gold parent. Judged strictly through alignment mapping (`parser_to_gold_map`). A row whose gold parent is a missing row produces no `wrong_parent` (it is recorded in `orphaned_children`). |
| `wrong_printed_value` | `ERROR` | Cell | Printed string or numeric value mismatch on an aligned cell (excluding pure sign differences, nil↔zero, or nil↔missing). Also catches spurious values in header cells. Always includes `detail.numeric_match`. |
| `sign_error` | `ERROR` | Cell | Magnitude matches (`abs(abs(g) - abs(p)) < 1e-4`), but sign marker or direction differs (e.g. missing `△`/`▲`, sign inversion, or negative zero marker `△0` vs `0`). |
| `nil_zero` | `ERROR` | Cell | Explicit nil dash (`－`, `-`, `—`, etc.) transcribed as numeric zero (`"0"` or `0.0`), or vice versa, conflating no-activity with an explicit zero amount. |
| `nil_missing` | `ERROR` | Cell | Explicit nil dash (`－`) transcribed as null/None/empty, or a null header cell transcribed as a nil dash. |

*Note on Accounting Relations:* Per USER DECISION 1 / Decision A, accounting checks are strictly diagnostic, non-gating, and excluded from the discrepancy ledger.

---

### 2. Total Cell Classification Matrix

Cell kind domains:
- **Gold Cell Kind ($G$):** `{null, nil, unsigned number, negative number incl. △0}`
- **Parser Cell Kind ($P$):** `{null, nil, unsigned number, negative number incl. △0, missing}`

Precedence Rules:
1. Exact string match (`str(expected) == str(actual)`): No discrepancy emitted.
2. `nil_missing`: One side is `nil` and the other side is `null` or `missing`.
3. `nil_zero`: One side is `nil` and the other side is numeric 0 (`"0"`, `"△0"`, `0.0`).
4. `sign_error`: Both are numbers with identical magnitude (`abs(abs(g) - abs(p)) < 1e-4`), but differing sign marker or direction.
5. `wrong_printed_value`: Any other mismatch. Always records `detail.numeric_match: bool`.

| Gold Kind ($G$) | Parser Kind ($P$) | Discrepancy Type | Severity | Detail / Precedence Rules |
|---|---|---|---|---|
| `null` | `null` | **None** | - | Match (both header cells null) |
| `null` | `nil` | `nil_missing` | `ERROR` | `numeric_match: false` (dash in header cell) |
| `null` | `unsigned number` | `wrong_printed_value` | `ERROR` | `numeric_match: false` (spurious value in header) |
| `null` | `negative number` | `wrong_printed_value` | `ERROR` | `numeric_match: false` (spurious value in header) |
| `null` | `missing` | `wrong_printed_value` | `ERROR` | `numeric_match: false` (row truncated) |
| `nil` | `null` | `nil_missing` | `ERROR` | `numeric_match: false` (dash omitted) |
| `nil` | `nil` (same glyph) | **None** | - | Exact string match (`"－"` == `"－"`) |
| `nil` | `nil` (diff glyph) | `wrong_printed_value` | `ERROR` | `numeric_match: true` (e.g. `"－"` vs `"-"`) |
| `nil` | `unsigned number` ($0$) | `nil_zero` | `ERROR` | `numeric_match: false` (dash transcribed as `0`) |
| `nil` | `unsigned number` ($\ne 0$) | `wrong_printed_value` | `ERROR` | `numeric_match: false` |
| `nil` | `negative number` ($0$) | `nil_zero` | `ERROR` | `numeric_match: false` (dash transcribed as `△0`) |
| `nil` | `negative number` ($\ne 0$) | `wrong_printed_value` | `ERROR` | `numeric_match: false` |
| `nil` | `missing` | `nil_missing` | `ERROR` | `numeric_match: false` (cell omitted from row) |
| `unsigned number` | `null` | `wrong_printed_value` | `ERROR` | `numeric_match: false` (value emitted as null) |
| `unsigned number` ($0$) | `nil` | `nil_zero` | `ERROR` | `numeric_match: false` (`0` transcribed as dash) |
| `unsigned number` ($\ne 0$) | `nil` | `wrong_printed_value` | `ERROR` | `numeric_match: false` |
| `unsigned number` | `unsigned number` (exact) | **None** | - | Exact string match |
| `unsigned number` | `unsigned number` (diff str, same num) | `wrong_printed_value` | `ERROR` | `numeric_match: true` (formatting / comma drift) |
| `unsigned number` | `unsigned number` (diff num) | `wrong_printed_value` | `ERROR` | `numeric_match: false` |
| `unsigned number` | `negative number` (same mag) | `sign_error` | `ERROR` | `numeric_match: false` (positive vs negative) |
| `unsigned number` ($0$) | `negative number` (`△0`) | `sign_error` | `ERROR` | `numeric_match: true` (`0` vs `△0`) |
| `unsigned number` | `negative number` (diff mag) | `wrong_printed_value` | `ERROR` | `numeric_match: false` |
| `unsigned number` | `missing` | `wrong_printed_value` | `ERROR` | `numeric_match: false` (cell omitted from row) |
| `negative number` | `null` | `wrong_printed_value` | `ERROR` | `numeric_match: false` |
| `negative number` (`△0`) | `nil` | `nil_zero` | `ERROR` | `numeric_match: false` (`△0` transcribed as dash) |
| `negative number` ($\ne 0$) | `nil` | `wrong_printed_value` | `ERROR` | `numeric_match: false` |
| `negative number` | `unsigned number` (same mag) | `sign_error` | `ERROR` | `numeric_match: false` (e.g. `△2,979` vs `2,979`) |
| `negative number` (`△0`) | `unsigned number` (`0`) | `sign_error` | `ERROR` | `numeric_match: true` (`△0` vs `0`) |
| `negative number` | `unsigned number` (diff mag) | `wrong_printed_value` | `ERROR` | `numeric_match: false` |
| `negative number` | `negative number` (exact) | **None** | - | Exact string match |
| `negative number` | `negative number` (diff str, same num) | `wrong_printed_value` | `ERROR` | `numeric_match: true` (e.g. `▲` vs `△` or formatting) |
| `negative number` | `negative number` (diff num) | `wrong_printed_value` | `ERROR` | `numeric_match: false` |
| `negative number` | `missing` | `wrong_printed_value` | `ERROR` | `numeric_match: false` |

---

### 3. Gold.json Field Coverage Table

Every field of `eval/gold.json` is categorized as scored (with associated discrepancy type and ID schema) or explicitly unscored:

| Field Path | Evaluation Status | Discrepancy Type | ID Schema | Rationale |
|---|---|---|---|---|
| `status` | **Unscored** | N/A | N/A | Human verification status (`"pending_verification"`); harness configuration only. |
| `eval_flags.score_hierarchy` | **Unscored** | N/A | N/A | Evaluation control flag enabling/disabling hierarchy scoring. |
| `metadata.title` | **Unscored** | N/A | N/A | Document title header (`"連結貸借対照表"`). Parsers focus on tabular data zone. |
| `metadata.subtitle` | **Unscored** | N/A | N/A | Section header notes. |
| `metadata.unit` | **Scored** | `wrong_metadata` | `META:unit` | Currency denomination unit (`"千円"`). Critical financial scaling metadata. |
| `metadata.page_number` | **Unscored** | N/A | N/A | Source PDF page number index. |
| `metadata.notes` | **Unscored** | N/A | N/A | Amendment notes (`["（訂正後）"]`). |
| `metadata.column_headers` (count) | **Scored** | `wrong_metadata` | `META:columns` | Number of reporting periods/columns. |
| `metadata.column_headers` (text) | **Scored** | `wrong_metadata` | `META:col{n}` | Column header labels (1-indexed). |
| `uncertain_cells` | **Unscored** | N/A | N/A | Human transcription log of visually ambiguous printed characters. |
| `rows[].row_index` | **Scored** (Structural) | `missing_row` / `extra_row` | `R{n}:row` / `EXTRA:P{n}` | Governs sequence alignment ordering and stable identifiers. |
| `rows[].label` | **Scored** | `missing_row`, `extra_row`, `wrong_label` | `R{n}:row`, `EXTRA:P{n}`, `R{n}:label` | Row alignment anchor and label fidelity. |
| `rows[].parent_index` | **Scored** | `wrong_parent` | `R{n}:parent` | Visual hierarchy tree structure (resolved through alignment). |
| `rows[].parent_label` | **Scored** | `wrong_parent` | `R{n}:parent` | Visual hierarchy parent label text. |
| `rows[].values` | **Scored** | `wrong_printed_value`, `sign_error`, `nil_zero`, `nil_missing` | `R{n}:C{col}` | Printed cell strings. Missing rows subsume cell errors into `subsumed_cells`. |
| `checks` | **Unscored in Ledger** | Diagnostics only | `CHK:{id}:C{col}` | Accounting equations evaluated in diagnostic section; non-gating. |

---

### 4. Fault-Injection Tests: Predicted vs. Actual Ledger

Per Requirement D.1, predictions were committed to git prior to execution (commit `69a5600`). Below is the complete comparison:

| Test # | Test Name | Predicted Ledger | Actual Ledger | Match Status | Notes / Collateral Observations |
|:---:|---|---|---|:---:|---|
| **01** | `test_01_gold_vs_gold_self_eval` | `[]` (0 entries), exit 0 | `[]` (0 entries), exit 0 | **EXACT MATCH** | Baseline self-evaluation achieves 100% on all rates and passes all 20 accounting checks. |
| **02** | `test_02_fault_drop_middle_row` (`仕掛品`) | 1 entry: `R8:row` (`missing_row`, CRITICAL, `subsumed_cells=2`, `orphaned_children=[]`), exit 1 | 1 entry: `R8:row` (`missing_row`, CRITICAL, `subsumed_cells=2`, `orphaned_children=[]`), exit 1 | **EXACT MATCH** | Cells subsumed under `missing_row`. Alignment realigns subsequent rows without cascading parent errors. |
| **03** | `test_03_fault_duplicate_row` (`売掛金`) | 1 entry: `EXTRA:P6` (`extra_row`, CRITICAL), exit 1 | 1 entry: `EXTRA:P6` (`extra_row`, CRITICAL), exit 1 | **EXACT MATCH** | Earlier occurrence matches gold row 5; later duplicate is marked extra. |
| **04** | `test_04_fault_swap_columns` | 72 entries: all `wrong_printed_value` (ERROR), exit 1 | 72 entries: all `wrong_printed_value` (ERROR), exit 1 | **EXACT MATCH** | Exactly 36 rows differ between Col 1 and Col 2 ($36 \times 2 = 72$). Row 37 (`関係会社株式` `['1,123', '1,123']`) is unaffected. |
| **05** | `test_05_fault_negative_zero_marker` (`△0` $\rightarrow$ `0`) | 1 entry: `R12:C2` (`sign_error`, ERROR, `expected="△0"`, `actual="0"`, `numeric_match=True`), exit 1 | 1 entry: `R12:C2` (`sign_error`, ERROR, `expected="△0"`, `actual="0"`, `numeric_match=True`), exit 1 | **EXACT MATCH** | Same magnitude 0; sign marker absence triggers `sign_error`. |
| **06** | `test_06_fault_nil_to_zero` (`－` $\rightarrow$ `0`) | 1 entry: `R26:C1` (`nil_zero`, ERROR, `expected="－"`, `actual="0"`, `numeric_match=False`), exit 1 | 1 entry: `R26:C1` (`nil_zero`, ERROR, `expected="－"`, `actual="0"`, `numeric_match=False`), exit 1 | **EXACT MATCH** | Nil indicator mapped to numeric zero classified as `nil_zero`. |
| **07** | `test_07_fault_nil_to_null` (`－` $\rightarrow$ `null`) | 1 entry: `R26:C1` (`nil_missing`, ERROR, `expected="－"`, `actual=None`), exit 1 | 1 entry: `R26:C1` (`nil_missing`, ERROR, `expected="－"`, `actual=None`), exit 1 | **EXACT MATCH** | Dropped nil marker classified as `nil_missing`. |
| **08** | `test_08_fault_remove_delta_contra` | 1 entry: `R17:C1` (`sign_error`, ERROR, `expected="△1,923,585"`, `actual="1,923,585"`, `numeric_match=False`), exit 1 | 1 entry: `R17:C1` (`sign_error`, ERROR, `expected="△1,923,585"`, `actual="1,923,585"`, `numeric_match=False`), exit 1 | **EXACT MATCH** | Contra sign inversion triggers `sign_error`. Collateral: net buildings check fails in diagnostics, but produces NO ledger entry. |
| **09** | `test_09_fault_wrong_label` | 1 entry: `R5:label` (`wrong_label`, ERROR, `expected="売掛金"`, `actual="売掛金_modified"`), exit 1 | 1 entry: `R5:label` (`wrong_label`, ERROR, `expected="売掛金"`, `actual="売掛金_modified"`), exit 1 | **EXACT MATCH** | Gap pairing on identical value tuples pairs the rows; hierarchy is compared without emitting cell or parent discrepancies. |
| **10** | `test_10_fault_wrong_metadata_unit` | 1 entry: `META:unit` (`wrong_metadata`, CRITICAL, `expected="千円"`, `actual="百万円"`), exit 1 | 1 entry: `META:unit` (`wrong_metadata`, CRITICAL, `expected="千円"`, `actual="百万円"`), exit 1 | **EXACT MATCH** | Unit metadata mismatch flagged as CRITICAL. |
| **11** | `test_11_fault_wrong_metadata_columns` | 1 entry: `META:columns` (`wrong_metadata`, CRITICAL, `expected=2`, `actual=3`, `ignored_columns=[3]`), exit 1 | 1 entry: `META:columns` (`wrong_metadata`, CRITICAL, `expected=2`, `actual=3`, `ignored_columns=[3]`), exit 1 | **EXACT MATCH** | Column count mismatch is ONE entry; cell comparison is limited to first 2 shared columns. |
| **12** | `test_12_duplicate_row_tie_break` | 1 entry: `EXTRA:P6` (`extra_row`, CRITICAL), exit 1 | 1 entry: `EXTRA:P6` (`extra_row`, CRITICAL), exit 1 | **EXACT MATCH** | Deterministic tie-breaking confirms earlier duplicate matches gold row 5; later duplicate is extra. |
| **13** | `test_13_fault_drop_row_1_no_cascade` | 1 entry: `R1:row` (`missing_row`, CRITICAL, `subsumed_cells=2`, `orphaned_children=[2, 14, 43]`), exit 1 | 1 entry: `R1:row` (`missing_row`, CRITICAL, `subsumed_cells=2`, `orphaned_children=[2, 14, 43]`), exit 1 | **EXACT MATCH** | Dropping section root row 1 yields exactly ONE ledger entry; child rows 2, 14, 43 do not cascade into `wrong_parent`. |
| **14** | `test_14_waiver_applies` | 1 entry: `R12:C2` (`waived=True`, `waiver_reason="..."`), exit 0 | 1 entry: `R12:C2` (`waived=True`, `waiver_reason="..."`), exit 0 | **EXACT MATCH** | Matching waiver marks entry waived; exit code 0 achieved. |
| **15** | `test_15_waiver_does_not_apply_when_actual_changed` | 1 entry: `R12:C2` (`waived=False`), 1 stale waiver, exit 1 | 1 entry: `R12:C2` (`waived=False`), 1 stale waiver, exit 1 | **EXACT MATCH** | Actual value changed from waiver specification; waiver does not apply, non-zero exit enforced. |
| **16** | `test_16_malformed_waiver_exit_2` | Subprocess exit code 2, error message mentions "reason" | Subprocess exit code 2, error message mentions "reason" | **EXACT MATCH** | Empty waiver reason triggers immediate harness error (exit 2). |
| **17** | `test_17_malformed_input_exit_2` | Subprocess exit code 2 on missing 'rows' | Subprocess exit code 2 on missing 'rows' | **EXACT MATCH** | Schema-invalid input JSON triggers immediate harness error (exit 2). |
| **18** | `test_18_stale_waiver_listed` | `ledger=[]`, `len(stale_waivers)==1`, exit 0 | `ledger=[]`, `len(stale_waivers)==1`, exit 0 | **EXACT MATCH** | Unused waiver listed as non-gating warning under `stale_waivers`. |

---

### 5. Current Parser Output Evaluation (`output/balance_sheet_p1.json`)

Running the current parser output against `eval/gold.json` produces the following ledger:

```
=====================================================================
      JAPANESE FINANCIAL TABLE PARSER EVALUATION REPORT              
=====================================================================
 STATUS: FAIL (Exit Code: 1)
 Total Discrepancies: 2 | Unwaived: 2 (Critical: 2, Error: 0) | Waived: 0
=====================================================================
 1. DISCREPANCY LEDGER:
    01. [UNWAIVED] META:col1      | Type: wrong_metadata       | Severity: CRITICAL
        Expected: "前連結会計年度 (2025年３月31日)"
        Actual:   "前連結会計年度 (2025-03-31)"
    02. [UNWAIVED] META:col2      | Type: wrong_metadata       | Severity: CRITICAL
        Expected: "当連結会計年度 (2026年３月31日)"
        Actual:   "当連結会計年度 (2026-03-31)"
=====================================================================
 2. DIAGNOSTICS: ACCOUNTING CONSISTENCY CHECKS (Non-Gating)
 Total Checks: 20 | Passed: 20 (Exact: 7, Rounding: 13) | Failed: 0
=====================================================================
Rates: Row F1=100.00% | Hierarchy=100.00% | Value Cell Exact=100.00% (Numeric=100.00%) | Token F1=100.00%
=====================================================================
```

#### Detailed Findings on Current Parser Output:
1. **Perfect Tabular Extraction:**
   - **Row Match:** 100.00% (43/43 rows aligned).
   - **Hierarchy Accuracy:** 100.00% (all parents match visual indentation).
   - **Value Cell Exact String Accuracy:** 100.00% (74/74 value cells verbatim match).
   - **No-Value Cell Accuracy:** 100.00% (12/12 header cells null).
   - **Numeric-Token Coverage F1:** 100.00%.
   - **Accounting Checks:** 20/20 Passed (7 Exact, 13 Source Rounding, 0 Inconsistencies).
2. **The 2 Unwaived Discrepancies:**
   - `META:col1` and `META:col2`: In `output/balance_sheet_p1.json`, the parser normalized Japanese date formats in header parentheses (e.g. `(2025年３月31日)` $\rightarrow$ `(2025-03-31)`). Under the new strict metadata taxonomy, verbatim header strings are required.
   - Per Ground Rule 3 and Scope Fence, `parser/` was left completely untouched.

---

### 6. Alignment Invariance & Moved Row Semantics

- **Deterministic Tie-Breaking:** In Needleman-Wunsch sequence alignment (`sequence_align`), when the score of extending a gap (left/up) ties with a diagonal match, the gap is preferred (`score_left` $\ge$ `score_diag`, `score_up` $\ge$ `score_diag`). For adjacent duplicate rows (e.g. `[売掛金, 売掛金]`), the earlier occurrence matches gold; the later occurrence is marked as `extra_row`.
- **Moved Row Semantics:** Because sequence alignment enforces page order strictly, a moved or transposed row (e.g. a row moved from position 5 to position 20) appears in the ledger as a pair: one `missing_row` at its expected position, and one `extra_row` at its actual position. This prevents out-of-order alignment corruption across subsequent rows.

---

## Changes made (files + commits)

1. **Test Predictions Commit:**
   - File: `eval/test_fault_injections.py`
   - Commit: `69a5600`
   - Message: `predict: record expected discrepancy ledgers for 8 fault tests and 10 new scenarios`
   - Content: Added explicit expected ledgers and assertions for 8 existing fault tests and 10 new scenarios (wrong label, wrong metadata unit, wrong column count, duplicate row tie-break, drop row 1 no cascade, waiver applies, waiver fails on actual changed, malformed waiver, malformed input, stale waiver).

2. **Evaluator Implementation Commit:**
   - File: `eval/evaluate.py`
   - Commit: `329bc11`
   - Message: `feat(eval): implement discrepancy ledger, closed taxonomy, waivers, and exit codes`
   - Content:
     - Implemented closed taxonomy (`missing_row`, `extra_row`, `wrong_label`, `wrong_printed_value`, `sign_error`, `nil_zero`, `nil_missing`, `wrong_parent`, `wrong_metadata`).
     - Added total cell classification function and matrix.
     - Implemented gap pairing for `wrong_label` based on identical non-empty value tuples.
     - Added metadata checks for unit, column headers, and column count.
     - Added alignment-based parent resolution, supporting both explicit `row_index` and 1-indexed array offsets.
     - Implemented missing row child orphan tracking (`orphaned_children`) and cell subsumption (`subsumed_cells`), eliminating cascading errors.
     - Added `--waivers` CLI flag with strict `id`, `type`, `actual`, and non-empty `reason` matching.
     - Removed `--fail-under-*` flags, rejecting them with exit code 2.
     - Enforced exit codes: `0` (clean/waived), `1` (unwaived discrepancies), `2` (harness error).
     - Formatted Text, Markdown, and JSON outputs with ledger as primary section, accounting checks as non-gating diagnostics, and a single rates footer line.

3. **Documentation Commit:**
   - File: `eval/README.md`
   - Commit: `99b0f60`
   - Message: `docs(eval): update CLI usage, exit codes, and fault injection suite in README`
   - Content: Updated Section 5 (Usage Guide, Waivers File specification, Exit Codes) and Section 6 (18 automated fault injection tests table) to match new evaluator behavior.

---

## Open decisions

All architectural decisions for Chat C were resolved through user guidance:
1. **Accounting Checks in Ledger:** Excluded from discrepancy ledger; retained as non-gating diagnostics.
2. **Tolerance Model:** Symmetric tolerance $\max(1, \lceil n/2 \rceil)$ retained.
3. **Missing Row Subsumption:** Subsumed value cells under `missing_row` with `subsumed_cells` count and `orphaned_children` list.
4. **Header Date Normalization Waiver vs Parser Normalization:**
   - The parser currently normalizes header dates to ISO format `(YYYY-MM-DD)`, producing 2 CRITICAL `wrong_metadata` discrepancies against gold `(YYYY年M月D日)`.
   - *Options:*
     - A: Author a standard `waivers.json` for `META:col1` and `META:col2` explaining ISO date normalization.
     - B: Update parser in a subsequent chat to preserve verbatim printed header text.
   - Recommended: Option B in future parser refinements, keeping evaluator strict.

---

## Out-of-scope observations

1. **Pre-existing Working Tree Modifications in Synthetic Fixtures:**
   `git status` continues to show unstaged modifications in `tests/fixtures/stress_3col.pdf`, `tests/fixtures/stress_flatindent.pdf`, and `tests/fixtures/stress_neg_marker.pdf` from prior workspace operations. Per Ground Rule 3, these remain untouched.
2. **PyMuPDF Deprecation Notice:**
   Running tests invoking `fitz` outputs: `FutureWarning: The fitz API is deprecated and will be removed in future. Use import pymupdf instead.` Modernization should be scheduled in a separate maintenance task.
3. **Metadata Container Key Parity:**
   `eval/gold.json` stores document metadata under the key `"metadata"`, whereas `output/balance_sheet_p1.json` stores it under `"meta"`. `eval/evaluate.py` supports both keys seamlessly (`parser_data.get("metadata") or parser_data.get("meta")`). Aligning on a canonical schema key across all outputs would eliminate container ambiguity.
