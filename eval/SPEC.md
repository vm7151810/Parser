# Evaluation Specification for Japanese Financial Table Parsers

**Specification Version**: 2.1  
**Status**: Normative Specification (Verified against Reports A, B, and C)  
**Target Document**: `balance_sheet.pdf` (Page 1 / Document Page 4: 連結貸借対照表 / Consolidated Balance Sheet — 資産の部)  
**Authors**: Independent Evaluation & Specification Working Group  

---

## 1. Scope and Cell Definition

### 1.1. Scope & Document Boundary
1. **Target Page**: The evaluation scope is strictly confined to the tabular assets side (`資産の部`) of `balance_sheet.pdf` (single-page vector PDF, A4 dimensions $595.2 \times 841.8$ points).
2. **Exclusions**: Document titles, subtitles, regulatory amendment notices (`（訂正後）`), unit declarations (`（単位：千円）`), and page footers (`- 4 -`) are document metadata and MUST NOT be output as table rows.
3. **Table Dimensions**:
   - Exactly **43 ordered rows** from Row 1 (`資産の部`) to Row 43 (`資産合計`).
   - Exactly **2 numeric reporting columns**:
     - Column 1: `前連結会計年度 (2025年３月31日)` (Prior fiscal year ended March 31, 2025)
     - Column 2: `当連結会計年度 (2026年３月31日)` (Current fiscal year ended March 31, 2026)
   - Total table cells: $43 \text{ rows} \times 2 \text{ columns} = \mathbf{86 \text{ cells}}$.

### 1.2. Cell Definition and Partitioning
A **cell** is defined as the atomic datum situated at the intersection of an aligned table row $i \in [1, 43]$ and a column $c \in \{1, 2\}$.

The table partitions all 86 cells into two mutually exclusive sets:
1. **Value Cells (74 cells)**:
   - Rows that represent financial line items, contra accounts, net carrying amounts, or subtotals.
   - Each cell MUST contain either a printed financial numeric string (e.g. `"2,002,429"`, `"△2,979"`, `"△0"`) or an explicit printed nil indicator (`"－"`).
   - In `gold.json`, exactly 37 rows carry values across both columns ($37 \times 2 = 74$ cells).
2. **No-Value (Category Header) Cells (12 cells)**:
   - Rows that represent structural division or section headers with no quantitative data.
   - Exactly 6 rows in `gold.json`:
     - Row 1: `資産の部`
     - Row 2: `流動資産`
     - Row 14: `固定資産`
     - Row 15: `有形固定資産`
     - Row 31: `無形固定資産`
     - Row 35: `投資その他の資産`
   - Each such cell MUST contain JSON `null` ($6 \times 2 = 12$ cells). Any non-null string in a category header cell MUST be scored as a discrepancy.

---

## 2. Value Semantics: Printed String vs. Numeric Value vs. Nil vs. Missing vs. Negative Zero

Every parser cell is evaluated under five distinct semantic interpretations:

```
+-----------------------------------------------------------------------------------------+
|                                CELL VALUE CLASSIFICATION                                |
+-----------------------------------------------------------------------------------------+
| Category Header Cells (12)  ---> null                                                   |
+-----------------------------------------------------------------------------------------+
| Value Cells (74)            ---> Printed Financial Number (e.g. "2,002,429")            |
|                             ---> Negative Financial Number (e.g. "△2,979")              |
|                             ---> Negative Zero Marker (e.g. "△0")                       |
|                             ---> Explicit Nil Dash (e.g. "－")                          |
+-----------------------------------------------------------------------------------------+
```

### 2.1. Exact Printed String (`printed_text`)
- **Definition**: The verbatim character sequence as presented on the printed page, preserving thousands commas, parentheses, leading negative symbols, and full-width dash variants.
- **Evaluation Rule**: Evaluated via exact Unicode string comparison:
  $$\text{ExactMatch}(g, p) \iff \text{str}(g) == \text{str}(p)$$
- **Formatting Preservation**: Normalization (such as stripping commas or converting full-width characters) MUST NOT be applied during exact string evaluation.

### 2.2. Normalized Numeric Value (`numeric_value`)
- **Definition**: The IEEE 754 floating-point value extracted after removing thousands separators (`,`, `，`) and applying negative sign conversion.
- **Evaluation Rule**:
  $$\text{NumericMatch}(g, p) \iff |g_{\text{num}} - p_{\text{num}}| < 10^{-4} \land (g_{\text{is\_neg}} == p_{\text{is\_neg}})$$
- Parsers MUST preserve the sign flag. If an explicit negative marker is stripped without preserving negative magnitude (e.g. `△1,923,585` $\to +1923585.0$), numeric match MUST fail.

### 2.3. Explicit Nil Indicator (`"－"`)
- **Definition**: An explicit printed dash (primarily full-width em-dash `－` U+FF0D, hyphen `-` U+002D, or horizontal bar `―` U+2015) signifying zero activity or nil balance for that reporting period (found in Row 26 `建設仮勘定` Col 1 and Row 38 `長期貸付金` Col 1).
- **Transcription Rule**: Stored as exact string `"－"`, **NEVER as `null` and NEVER as `"0"`**.
- **Nil Matching Invariant**: **Nil matches ONLY nil**:
  - A gold nil marker compared against parser `"0"`, `0.0`, or `null` **FAILS** exact string match.
  - A gold nil marker compared against parser `"0"` or `0.0` **FAILS** normalized numeric match (emits discrepancy `nil_zero`).
  - In normalized numeric matching, any standard Unicode dash variant (`"－"`, `"-"`, `"—"`, `"―"`, `"‐"`, `"−"`) matches another nil marker, evaluating to zero in accounting roll-ups. When glyphs differ (e.g. `"－"` vs `"-"`), exact string match fails (`wrong_printed_value`), but `numeric_match: True` is recorded.

### 2.4. Missing Cell vs. Null
- In No-Value Category rows, empty space is expected and valid, evaluated as JSON `null`.
- In Value rows, empty space signifies an omitted or failed cell extraction. A parser emitting `null` for a value cell MUST be scored as a discrepancy:
  - If gold was an explicit nil dash and parser emitted `null`: classified as `nil_missing`.
  - If gold was a numeric value and parser emitted `null`: classified as `wrong_printed_value`.

### 2.5. Negative Zero (`"△0"`)
- **Occurrence**: Row 12 (`貸倒引当金`), Column 2 (`当連結会計年度`).
- **Accounting Semantics**: Indicates an active contra allowance balance that rounds down to zero thousand yen under source truncation (*千円未満切捨て*), or a nominal negative provision, presented with Japanese negative marker `△` (U+25B3).
- **Representation**:
  - Exact printed string: MUST be `"△0"`. Emitting `"0"`, `"0.0"`, or `"-0"` emits a `sign_error` discrepancy (same magnitude $0.0$, differing sign marker).
  - Normalized numeric value: Evaluates to `0.0` with negative sign flag `True` ($-0.0$). In accounting sums, it contributes `0.0`.

---

## 3. Hierarchy Definition and Conventions

Visual indentation is the sole authoritative source of document structure.

```
資産の部 (Row 1, level 0, parent: null)
├── 流動資産 (Row 2, level 1, parent: 1)
│   ├── 現金及び預金 ... 貸倒引当金 (Rows 3..12, level 2, parent: 2)
│   └── 流動資産合計 (Row 13, level 2, parent: 2)  <-- Subtotal closes section
└── 固定資産 (Row 14, level 1, parent: 1)
    ├── 有形固定資産 (Row 15, level 2, parent: 14)
    │   ├── 建物及び構築物 (Row 16, level 3, parent: 15)
    │   │   ├── 減価償却累計額 (Row 17, level 4, parent: 16)       <-- Contra child of gross
    │   │   └── 建物及び構築物（純額） (Row 18, level 4, parent: 16) <-- Net child of gross
    │   ├── 機械装置及び運搬具 (Row 19, level 3, parent: 15)
    │   │   ├── 減価償却累計額 (Row 20, level 4, parent: 19)
    │   │   └── 機械装置及び運搬具（純額） (Row 21, level 4, parent: 19)
    │   ├── 土地 (Row 22, level 3, parent: 15)
    │   ├── リース資産 (Row 23, level 3, parent: 15)
    │   │   ├── 減価償却累計額 (Row 24, level 4, parent: 23)
    │   │   └── リース資産（純額） (Row 25, level 4, parent: 23)
    │   ├── 建設仮勘定 (Row 26, level 3, parent: 15)
    │   ├── その他 (Row 27, level 3, parent: 15)
    │   │   ├── 減価償却累計額 (Row 28, level 4, parent: 27)
    │   │   └── その他（純額） (Row 29, level 4, parent: 27)
    │   └── 有形固定資産合計 (Row 30, level 3, parent: 15)
    ├── 無形固定資産 (Row 31, level 2, parent: 14)
    │   ├── リース資産 (Row 32, level 3, parent: 31)
    │   ├── その他 (Row 33, level 3, parent: 31)
    │   └── 無形固定資産合計 (Row 34, level 3, parent: 31)
    ├── 投資その他の資産 (Row 35, level 2, parent: 14)
    │   ├── 投資有価証券 ... その他 (Rows 36..40, level 3, parent: 35)
    │   └── 投資その他の資産合計 (Row 41, level 3, parent: 35)
    └── 固定資産合計 (Row 42, level 2, parent: 14)
資産合計 (Row 43, level 1, parent: 1)
```

### 3.1. Visual Indentation Rule
1. **Nearest Preceding Smaller Indent**: A row's parent is defined as the nearest preceding row whose left indentation ($x_0$) is strictly less than the row's own indentation:
   $$\text{Parent}(i) = \max \left\{ j \in [1, i-1] \mid \text{Indent}(j) < \text{Indent}(i) \right\}$$
2. Root rows (indent level 0, such as Row 1 `資産の部`) have no preceding shallower row and MUST have `parent_index: null` and `parent_label: null`.

### 3.2. Subtotal Row Parenting Convention
- **Principle**: Subtotal rows (`…合計`) sit at the identical visual indentation as the items they aggregate. Functionally and visually, they terminate and close the section.
- **Normative Rule**: **The parent of a subtotal row MUST be the section header it closes**, NOT the preceding line item and NOT the document root:
  - Row 13 `流動資産合計` $\to$ Parent: Row 2 `流動資産` (`parent_index: 2`)
  - Row 30 `有形固定資産合計` $\to$ Parent: Row 15 `有形固定資産` (`parent_index: 15`)
  - Row 34 `無形固定資産合計` $\to$ Parent: Row 31 `無形固定資産` (`parent_index: 31`)
  - Row 41 `投資その他の資産合計` $\to$ Parent: Row 35 `投資その他の資産` (`parent_index: 35`)
  - Row 42 `固定資産合計` $\to$ Parent: Row 14 `固定資産` (`parent_index: 14`)
  - Row 43 `資産合計` $\to$ Parent: Row 1 `資産の部` (`parent_index: 1`)

### 3.3. Placement of Contra and Net Rows
- **Triplet Structure**: Under `有形固定資産`, depreciable assets are presented as triplets:
  $$\text{Gross Item} \longrightarrow \text{Contra Item (\減価償却累計額)} \longrightarrow \text{Net Item (\dots（純額）)}$$
- **Indentation Depth**: Both `減価償却累計額` and the net row sit at indent level 4 ($x_0 \approx 114.2\text{ pt}$ / 12 spaces in `hierarchy_tree.txt`), directly indented under the gross row at level 3 ($x_0 \approx 101.3\text{ pt}$ / 8 spaces).
- **Normative Parenting Rule**: **Both the contra row AND the net row MUST have the gross line item as their parent**:
  - Row 17 `減価償却累計額` $\to$ Parent: Row 16 `建物及び構築物` (`parent_index: 16`)
  - Row 18 `建物及び構築物（純額）` $\to$ Parent: Row 16 `建物及び構築物` (`parent_index: 16`)
  - Row 20 `減価償却累計額` $\to$ Parent: Row 19 `機械装置及び運搬具` (`parent_index: 19`)
  - Row 21 `機械装置及び運搬具（純額）` $\to$ Parent: Row 19 `機械装置及び運搬具` (`parent_index: 19`)
  - Row 24 `減価償却累計額` $\to$ Parent: Row 23 `リース資産` (`parent_index: 23`)
  - Row 25 `リース資産（純額）` $\to$ Parent: Row 23 `リース資産` (`parent_index: 23`)
  - Row 28 `減価償却累計額` $\to$ Parent: Row 27 `その他` (`parent_index: 27`)
  - Row 29 `その他（純額）` $\to$ Parent: Row 27 `その他` (`parent_index: 27`)
- **Standalone Contra Accounts**: Row 12 `貸倒引当金` is not paired with a net line; its parent is the subsection header Row 2 `流動資産` (`parent_index: 2`).

---

## 4. Accounting Relations and the Rounding Model

The ground truth specifies exactly 10 accounting checks across both reporting periods (20 checks total). All checks serve as **diagnostics** to audit transcription and extraction integrity and are **non-gating** in the discrepancy ledger.

### 4.1. The 10 Canonical Accounting Checks

| Check ID | Target Row | Name / Description | Addend Rows ($k$) and Signs | Terms ($n$) | Symmetric Tol ($\pm \lceil n/2 \rceil$) |
| :--- | :---: | :--- | :--- | :---: | :---: |
| `net_buildings` | Row 18 | `建物及び構築物（純額）` | Row 16 ($+1$), Row 17 ($+1$) | 2 | $\pm 1$ |
| `net_machinery` | Row 21 | `機械装置及び運搬具（純額）` | Row 19 ($+1$), Row 20 ($+1$) | 2 | $\pm 1$ |
| `net_lease` | Row 25 | `リース資産（純額）` | Row 23 ($+1$), Row 24 ($+1$) | 2 | $\pm 1$ |
| `net_tangible_other` | Row 29 | `その他（純額）` | Row 27 ($+1$), Row 28 ($+1$) | 2 | $\pm 1$ |
| `subtotal_current_assets` | Row 13 | `流動資産合計` | Rows 3..11 ($+1$), Row 12 ($+1$) | 10 | $\pm 5$ |
| `subtotal_tangible_fixed_assets` | Row 30 | `有形固定資産合計` | Net Rows 18, 21, 25, 29 ($+1$), Land 22 ($+1$), CIP 26 ($+1$) | 6 | $\pm 3$ |
| `subtotal_intangible_fixed_assets`| Row 34 | `無形固定資産合計` | Rows 32 ($+1$), 33 ($+1$) | 2 | $\pm 1$ |
| `subtotal_investments_other_assets`| Row 41 | `投資その他の資産合計` | Rows 36..40 ($+1$) | 5 | $\pm 3$ |
| `subtotal_fixed_assets` | Row 42 | `固定資産合計` | Division Subtotals Rows 30 ($+1$), 34 ($+1$), 41 ($+1$) | 3 | $\pm 2$ |
| `grand_total_assets` | Row 43 | `資産合計` | Major Subtotals Rows 13 ($+1$), 42 ($+1$) | 2 | $\pm 1$ |

### 4.2. Roll-Up Composition Rules
1. **Net Rows Replace Gross & Contra in Subtotals**: `有形固定資産合計` MUST be computed by summing the 4 net carrying value lines + land + construction in progress ($n=6$). Gross amounts and accumulated depreciation MUST NOT be added simultaneously to avoid double-counting.
2. **Intermediate Subtotal Roll-Up**: High-level totals roll up intermediate subtotals:
   - `固定資産合計` rolls up the 3 division totals (`有形固定資産合計` + `無形固定資産合計` + `投資その他の資産合計`).
   - `資産合計` rolls up the 2 major totals (`流動資産合計` + `固定資産合計`).
3. **Explicit Sign Convention**: In `eval/gold.json`, all addends carry `"sign": 1` because printed contra accounts contain explicit negative markers (`△`) and parse directly to negative floats.

### 4.3. Rounding Models: Symmetric vs. Directional Truncation
1. **Symmetric Half-Up Bound (Evaluator Implementation)**:
   $$\text{Tolerance} = \max(1, \lceil n / 2 \rceil)$$
   A check passes as `SOURCE_ROUNDING` if $|\text{stated} - \text{computed}| \le \text{Tolerance}$.
2. **Directional Truncation Reality (*千円未満切捨て*)**:
   As proven in Report B, the underlying financial system truncates fractional yen amounts. Under truncation:
   - Sums MUST have non-negative differences: $0 \le (\text{stated} - \text{computed}) \le n - 1$.
   - Net deductions MUST have non-positive differences: $-1 \le (\text{stated} - \text{computed}) \le 0$.
3. **Status [As Decided in Chat B/C]**:
   Accounting checks are evaluated as **diagnostics only** and do not generate discrepancy ledger entries. This ensures extraction accuracy scoring is never compromised by publisher-side rounding artifacts.

---

## 5. Alignment Rules and Repeated Labels

Line item labels repeat across multiple distinct sections in Japanese financial statements:
- `減価償却累計額`: Appears 4 times (Rows 17, 20, 24, 28).
- `その他`: Appears 4 times (Rows 11, 27, 33, 40).
- `リース資産`: Appears 2 times (Rows 23, 32).

Unordered map lookups by label string produce fatal collisions.

### 5.1. Label Normalization Function $N(\cdot)$
To ensure robust string comparison:
1. Apply Unicode NFKC normalization: `unicodedata.normalize('NFKC', text)`.
2. Strip all whitespace, tabs, carriage returns, newlines, and full-width ideographic spaces:
   $$N(\text{text}) = \text{regex\_replace}([\backslash\text{s}\backslash\text{u3000}\backslash\text{n}\backslash\text{r}\backslash\text{t}]+, \text{""}, \text{NFKC}(\text{text}))$$

### 5.2. Global Sequence Alignment (Needleman-Wunsch)
Given gold label sequence $G = [g_1, \dots, g_m]$ and parser label sequence $P = [p_1, \dots, p_k]$:
- **Scoring Function**:
  $$S(g_i, p_j) = \begin{cases} +2.0 & \text{if } N(g_i) == N(p_j) \land N(g_i) \ne "" \\ +1.0 & \text{if } \text{LevSim}(N(g_i), N(p_j)) \ge 0.8 \\ -1.5 & \text{otherwise (mismatch penalty)} \end{cases}$$
- **Gap Penalty**: $-1.0$ (for row insertions or deletions).
- **Deterministic Tie-Breaking**:
  - When parser has adjacent duplicate rows, the earlier occurrence matches gold and the later is marked extra (prefer left on tie with diag).
  - When gold has adjacent duplicate rows, the earlier occurrence matches parser and the later is marked missing (prefer up on tie with diag).
- **Gap-Pairing (Label Drift Detection)**:
  Within an alignment gap between matched anchor rows, if an unmatched gold row and unmatched parser row share an identical, non-empty value tuple, they are paired:
  - Emits `wrong_label` on `R{n}:label` (Severity: `ERROR`).
  - Hierarchy for the row is compared against gold, avoiding cascading cell errors.
- **Unaligned Gold Row Penalty (`missing_row`)**:
  If a gold row $g_i$ has no aligned parser row ($g_i, \emptyset$), a `missing_row` discrepancy (Severity: `CRITICAL`) is emitted. It subsumes all value cells (`subsumed_cells`) and records any child rows orphaned by its removal (`orphaned_children`).

---

## 6. Discrepancy Taxonomy, Severities, Waivers, and Exit Semantics

The evaluator outputs an enumerated **Discrepancy Ledger** as its primary output.

### 6.1. Closed Discrepancy Taxonomy

| Discrepancy Code | Severity | Scope | Description / Trigger Condition |
| :--- | :---: | :---: | :--- |
| `missing_row` | `CRITICAL` | Row | Gold row completely absent from sequence alignment. Subsumes value cells and logs orphaned children. |
| `extra_row` | `CRITICAL` | Row | Spurious or duplicated row emitted by parser with no counterpart in gold reference. |
| `wrong_metadata` | `CRITICAL` | Metadata | Metadata mismatch in currency unit (`META:unit`), column count (`META:columns`), or column headers (`META:col{n}`). |
| `wrong_label` | `ERROR` | Row | Row paired across gap by identical value tuple but has modified label text. |
| `wrong_parent` | `ERROR` | Hierarchy | Aligned row's visual parent (`parent_label` or resolved `parent_index`) does not match gold parent. |
| `wrong_printed_value` | `ERROR` | Cell | Verbatim printed string or numeric value mismatch on aligned cell (excluding pure sign, nil↔zero, or nil↔missing). |
| `sign_error` | `ERROR` | Cell | Magnitude matches within $10^{-4}$, but sign marker or direction differs (e.g. `△` omitted, or `△0` vs `0`). |
| `nil_zero` | `ERROR` | Cell | Explicit nil dash (`－`) converted to numeric zero (`"0"` or `0.0`), or vice versa. |
| `nil_missing` | `ERROR` | Cell | Explicit nil dash (`－`) omitted as `null`/empty, or header null cell populated with a nil dash. |

*Note on Accounting Relations*: Excluded from the discrepancy ledger; reported strictly under non-gating `diagnostics`.

### 6.2. Ledger Entry Data Model
Every discrepancy entry in the ledger contains:
- `id`: Stable identifier formatted as:
  - `META:unit`, `META:columns`, `META:col{n}` (Metadata)
  - `R{n}:row` (Missing row)
  - `EXTRA:P{n}` (Extra parser row)
  - `R{n}:label` (Wrong label)
  - `R{n}:parent` (Wrong parent)
  - `R{n}:C{col}` (Cell mismatch)
- `type`: Discrepancy code from the closed taxonomy.
- `severity`: `CRITICAL` or `ERROR`.
- `expected`: Gold value or expected parent specification.
- `actual`: Parser value or observed parent specification.
- `detail`: Structured dictionary (e.g. `{"numeric_match": bool}`).
- `waived`: Boolean flag indicating if an explicit waiver matched.
- `waiver_reason`: Non-empty string documenting justification when waived (`null` if unwaived).

### 6.3. Waiver Schema and Exit Semantics
- **Waiver Format**: Supplied via an external JSON file (`--waivers waivers.json`) containing an array of objects:
  ```json
  [
    {
      "id": "META:col1",
      "type": "wrong_metadata",
      "actual": "前連結会計年度 (2025-03-31)",
      "reason": "Date format ISO normalization in column header"
    }
  ]
  ```
- **Matching Rule**: A waiver applies if and only if `id`, `type`, AND `actual` all match the ledger entry.
- **Reason Mandate**: Any waiver entry with an empty or whitespace `reason` triggers harness error (exit code 2).
- **Exit Codes**:
  - `0`: All discrepancies are waived, or the ledger is completely empty.
  - `1`: One or more unwaived discrepancies exist.
  - `2`: Harness error (unreadable/invalid schema, invalid waiver file, or deprecated `--fail-under-*` flags).

---

## 7. Gold Provenance and Verification Status

### 7.1. Provenance Protocol
- **Document Source**: `balance_sheet.pdf` (Page 4 of TDnet filing).
- **Transcription Method**: Two-pass independent visual human transcription directly from 200 DPI rendered image without consulting any parser code, heuristics, or outputs:
  - **Pass 1**: Top-to-bottom reading focusing on orthography, visual indentation, and column alignment.
  - **Pass 2**: Bottom-to-top reading verifying digit sequences, comma placements, negative triangles, and nil dashes.
- **Dual-Source Reconciliation**: Full transcript recorded in [`transcription_log.md`](file:///home/mivikev/Desktop/Dev/UrAI/eval/transcription_log.md), with 100% agreement across all 43 rows and 86 cells.
- **Hierarchy Tree Verification**: Visual hierarchy independently transcribed to [`hierarchy_tree.txt`](file:///home/mivikev/Desktop/Dev/UrAI/eval/hierarchy_tree.txt) (4 spaces per indent level). Validated via [`verify_hierarchy.py`](file:///home/mivikev/Desktop/Dev/UrAI/eval/verify_hierarchy.py) with 100% match.
- **Mathematical Integrity**: All 20 accounting checks reconciled with zero manual adjustments to transcribed figures.

### 7.2. Verification Status
Per Ground Rule 1, external manual verification by the take-home reviewer remains **Pending**:
```json
{
  "status": "pending_verification"
}
```

---

## 8. Claims Table: Capabilities Claimed in Documentation

Every claim from `README.md` and `eval/README.md` is inventoried below and classified into:
1. **Measured on this page**: Verified directly on `balance_sheet.pdf` with command and gold evidence.
2. **Designed for, not measured**: Architectural features implemented in code but not triggered on this single-page asset filing.
3. **Out of scope**: Explicitly excluded capabilities.

| Capability Claim | Source Citation | Classification | Grounded Evidence / Concrete Status |
| :--- | :--- | :---: | :--- |
| **Row Count (43 rows)** | `README.md:130` | **Measured on this page** | `eval/gold.json:28-348`; `verify_hierarchy.py` confirms 43 rows match. |
| **Column Count (2 columns)** | `README.md:131` | **Measured on this page** | `eval/gold.json:14-17` (`前連結会計年度`, `当連結会計年度`). |
| **Indent Levels (5 levels)** | `README.md:132` | **Measured on this page** | Discovered centroids: 62.3, 75.2, 88.2, 101.3, 114.2 pt (`reports/A_parser_audit.md:151`). |
| **Token Coverage (74/74 tokens)** | `README.md:133` | **Measured on this page** | `eval/gold.json` contains 74 value tokens; `evaluate.py` confirms 100% token coverage. |
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

## 9. Decision Log

| # | Convention / Choice | Options Considered | Chosen Option / Status | Technical Rationale |
|---|:--- | :--- | :---: | :--- |
| **1** | **Subtotal Row Parenting** | A: Section header closed<br>B: Document root<br>C: Preceding leaf item | **Option A** | Matches human visual and accounting reading order. Adopted across `gold.json`, `hierarchy_tree.txt`, `SPEC.md`, and parser. |
| **2** | **Contra & Net Placement** | A: Both parented to gross row<br>B: Parented to division header<br>C: Net parented to contra | **Option A** | Both sit at identical visual indentation (level 4, 114.2 pt) under the gross line item (level 3, 101.3 pt). |
| **3** | **Tangible Subtotal Roll-Up** | A: Sum 4 net lines + land + CIP ($n=6$)<br>B: Sum 10 gross & contra lines | **Option A** | Net rows replace gross and contra rows on the face of the balance sheet. Prevents double-counting. |
| **4** | **Tolerance Model** | A: Symmetric $\pm \lceil n/2 \rceil$<br>B: Strict directional truncation<br>C: Dual-mode diagnostic warning | **Option C** | Retains generalizability across filings while warning on impossible negative drift on truncated source documents. |
| **5** | **Contra Signs in `gold.json`** | A: Keep `"sign": 1` (use signed float)<br>B: Change to `"sign": -1` | **Option A** | Preserves protected file `gold.json` while maintaining mathematical correctness since contra values parse to negative floats. |
| **6** | **Accounting Check Gating** | A: Informational diagnostic (non-gating)<br>B: Hard CI pass/fail gate | **Option A** | Prevents penalizing faithful parsers when source filing documents contain intrinsic publisher rounding errors. |
| **7** | **Discrepancy Ledger Model** | A: Percentage rates threshold<br>B: Closed discrepancy ledger with strict exit & waivers | **Option B** | Implemented in Chat C; makes discrepancies the first-class output; rates become secondary summary metrics. |
| **8** | **Scale Invariance (`y_band_tol`)**| A: Scale with glyph width<br>B: Keep fixed 2.0 pt | **Option A (Recommended)** | Prevents catastrophic row collapse when PDF coordinate space is scaled down ($0.5\times$). |
| **9** | **Nil Character Matching** | A: Strict character identity<br>B: Unicode class equivalency | **Hybrid (As Implemented)** | Exact string match requires verbatim character; normalized numeric match accepts all valid Unicode dashes. |
| **10**| **Negative Zero Representation** | A: Preserve `"△0"`<br>B: Coerce to `"0"` | **Option A** | Preserves auditability and negative provision semantics while parsing to $-0.0$ in numeric summation. |

---

## 10. External Parser Neutral Schema Interface

Any third-party parser can be scored against `eval/gold.json` by exporting to this minimal schema:

```json
{
  "column_headers": [
    "前連結会計年度 (2025年３月31日)",
    "当連結会計年度 (2026年３月31日)"
  ],
  "rows": [
    {
      "label": "資産の部",
      "parent_index": null,
      "parent_label": null,
      "values": [null, null]
    },
    {
      "label": "流動資産",
      "parent_index": 1,
      "parent_label": "資産の部",
      "values": [null, null]
    },
    {
      "label": "現金及び預金",
      "parent_index": 2,
      "parent_label": "流動資産",
      "values": ["2,002,429", "608,281"]
    },
    {
      "label": "貸倒引当金",
      "parent_index": 2,
      "parent_label": "流動資産",
      "values": ["△2,979", "△0"]
    },
    {
      "label": "流動資産合計",
      "parent_index": 2,
      "parent_label": "流動資産",
      "values": ["5,863,684", "3,377,407"]
    },
    {
      "label": "建設仮勘定",
      "parent_index": 15,
      "parent_label": "有形固定資産",
      "values": ["－", "4,553"]
    }
  ]
}
```
