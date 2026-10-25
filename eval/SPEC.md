# Evaluation Specification for Japanese Financial Table Parsers

**Version**: 1.1  
**Scope**: Parser-agnostic evaluation harness for Japanese financial filing table pages (e.g., 連結貸借対照表 / Balance Sheets).  
**Authors**: Independent Evaluation & Ground-Truth Team  

---

## 1. Design Principles & Architecture

This evaluation specification provides an objective, reproducible, and parser-agnostic benchmark for extracting tabular data from Japanese financial statements:

1. **Parser Agnostic**: The ground truth and evaluation interface do not encode internal parser concepts such as pixel/point coordinates, bounding boxes, character indices, indent cluster IDs, or internal row-type taxonomies (`gross`, `contra`, `net`, `item`).
2. **Human-Centric Hierarchy & Subtotal Rule**:
   - The hierarchy is defined purely by human visual perception: a row's parent is the row it is visually indented under.
   - Subtotal rows represent the closing roll-up of a section; per accounting standards and human reading convention, **the parent of a subtotal row is the specific section it closes** (e.g., `流動資産合計` has parent `流動資産`; `固定資産合計` has parent `固定資産`; `資産合計` has parent `資産の部`).
   - Hierarchy is strictly captured via **1-indexed `parent_index`** (row number 1..N) and `parent_label`. Root rows have `parent_index: null` and `parent_label: null`.
3. **Preservation of Page Order & Sequential Alignment**:
   - Financial statements frequently reuse generic line item labels (e.g., `減価償却累計額` appears 4 times, `その他` appears 4 times, `リース資産` appears twice).
   - Rows cannot be matched via unordered key sets. Row alignment is performed via **sequential sequence alignment** (Needleman-Wunsch / LCS) over normalized labels, strictly preserving page order.
   - Any gold row that has no aligned parser row scores **ALL of its cells as WRONG**, including no-value null cells.
4. **Value Fidelity & Strict Nil Distinction**:
   - Category and section header rows that carry no numeric values are transcribed as `null`.
   - Printed nil indicators (such as `－`, `—`, `-`) represent explicit zero balances and are transcribed as verbatim strings (`"－"`), **never as `null`**.
   - **Nil matches ONLY nil**: A gold nil marker `"－"` compared against parser `"0"` or `0.0` **fails** both exact string matching and normalized numeric matching.
   - Negative indicators (such as `△` or `▲`) are preserved verbatim in printed strings (e.g., `"△2,979"`).
   - Negative zero (`"△0"`) is preserved as a distinct printed token.
5. **Separation of Accuracy from Accounting Diagnostics**:
   - Accuracy benchmarks:
     1. Row Match (Order + Normalized Label F1)
     2. Hierarchy Accuracy (1-indexed Parent Index + Parent Label Match)
     3. Cell Accuracy (Reported separately for 74 Value Cells and 12 No-Value Cells; `--fail-under-cell` gates on Value Cells)
     4. Numeric-Token Coverage (Multiset Token Match F1)
   - Accounting checks (subtotals, gross vs. net reconciliations) are human-authored in the gold schema and evaluated on aligned parser output as **diagnostics only**, with explicit scaled rounding tolerance rationales.
   - Accounting checks use **signed printed values with `sign: +1` for all addends** (since contra accounts are printed with negative markers `△` and parse directly to negative floats).
   - Accounting checks do NOT alter accuracy scores.
6. **No Hidden Thresholds**:
   - The evaluation harness enforces zero hardcoded thresholds.
   - CI/CD pass/fail criteria are governed by explicit CLI flags (`--fail-under-cell`, `--fail-under-row`, etc.).

---

## 2. Neutral Data Formats

### 2.1. Minimal Gold Schema (`gold.json`)

```json
{
  "status": "pending_human_verification",
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
      "reason": "Printed as △0; denotes negative zero provision balance."
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
      "row_index": 26,
      "label": "建設仮勘定",
      "parent_index": 15,
      "parent_label": "有形固定資産",
      "values": ["－", "4,553"]
    }
  ],
  "checks": [
    {
      "check_id": "subtotal_current_assets",
      "name": "流動資産合計 roll-up",
      "target_row_index": 13,
      "addend_rows": [
        {"row_index": 3, "sign": 1},
        {"row_index": 12, "sign": 1}
      ],
      "tolerance_terms": 10,
      "tolerance_rationale": "Sum of 10 line items rounded independently to thousand yen; max expected drift is ceil(10/2) = 5 thousand yen."
    }
  ]
}
```

### 2.2. Neutral Parser Input Schema

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
      "label": "現金及び預金",
      "parent_index": 2,
      "parent_label": "流動資産",
      "values": ["2,002,429", "608,281"]
    }
  ]
}
```

---

## 3. Row Sequence Alignment Specification

### 3.1. Label Normalization Function $N(\cdot)$
1. Unicode NFKC normalization: `unicodedata.normalize('NFKC', text)`.
2. Strip all whitespace, tabs, full-width spaces, and line breaks: `\s`, `\n`, `\r`, `\t`, `\u3000`.

### 3.2. Global Sequence Alignment (Needleman-Wunsch)
Given Gold row labels $G = [g_1, \dots, g_m]$ and Parser row labels $P = [p_1, \dots, p_k]$:
- Scoring function:
  $$S(g_i, p_j) = \begin{cases} +2.0 & \text{if } N(g_i) == N(p_j) \text{ and } N(g_i) \ne "" \\ +1.0 & \text{if } \text{LevSim}(N(g_i), N(p_j)) \ge 0.8 \\ -1.5 & \text{otherwise (mismatch penalty)} \end{cases}$$
- Gap penalty: $-1.0$ (insertion or deletion).
- Dynamic programming matrix aligns rows globally while strictly preserving page order.
- Result: Ordered pairs $(g_i, p_j)$, $(g_i, \emptyset)$ (missed gold row), or $(\emptyset, p_j)$ (spurious parser row).

---

## 4. Evaluation Metrics

### 4.1. Row Match Accuracy
- Let $M$ be the number of aligned pairs where normalized labels match ($N(g_i) == N(p_j)$).
- **Row Recall**: $\text{Recall}_{\text{row}} = M / |G|$
- **Row Precision**: $\text{Precision}_{\text{row}} = M / |P|$
- **Row F1**: $\text{F1}_{\text{row}} = 2 \cdot P \cdot R / (P + R)$

### 4.2. Hierarchy Accuracy (1-Indexed Parent Match)
For each aligned row pair where $g_i.\text{parent\_label}$ is not null:
- Gold parent index $g_i.\text{parent\_index}$ is 1-indexed. The expected parser index is the parser row aligned with $g_i.\text{parent\_index} - 1$.
- Parser parent index $p_j.\text{parent\_index}$ is strictly 1-indexed. It must satisfy:
  $$(p_j.\text{parent\_index} - 1) == \text{ExpectedParserIdx}$$
- $N(p_j.\text{parent\_label}) == N(g_i.\text{parent\_label})$
- **Hierarchy Accuracy**: Matches / Total rows with gold parent.
- If `eval_flags.score_hierarchy == false`, this metric is marked `N/A`.

### 4.3. Cell Accuracy (Value Cells vs. No-Value Cells)
Gold balance sheets partition cells into:
1. **Value Cells (74 in `gold.json`)**: Printed numeric values or explicit nil dashes.
   - **Exact String Accuracy**: Exact verbatim match ($g_{\text{str}} == p_{\text{str}}$).
   - **Normalized Numeric Accuracy**: Parses signed float values within $10^{-4}$.
   - **Nil Rule**: Gold `"－"` matches **only** parser nil (`"－"`, `"-"`, `"—"`). Parser `"0"` or `0.0` or `null` **fails**.
   - **Unaligned Gold Row Rule**: If a gold row has no aligned parser row, **all its cells fail**.
   - **Cell Value Precision**: $\text{ExactMatches} / N_{\text{parser\_val\_cells}}$.
   - **Cell Value Recall**: $\text{ExactMatches} / 74$.
   - **Cell Value F1**: Harmonic mean of precision and recall.
   - `--fail-under-cell` gates directly on Value Cell Exact Accuracy.
2. **No-Value Cells (12 in `gold.json`)**: Section/category headers with no printed values.
   - Matches if and only if row is aligned and parser cell is `null`. Any string in a header cell fails.
3. **All Cells (86 total)**: Overall accuracy across all 86 cells.

### 4.4. Numeric-Token Coverage (Multiset Match)
- Extract all digit sequences (`\d+`) from gold values into multiset Counter $\mathcal{T}_{\text{gold}}$.
- Extract all digit sequences from parser values into multiset Counter $\mathcal{T}_{\text{parser}}$.
- Token Precision = $\sum \min(\mathcal{T}_{\text{gold}}(t), \mathcal{T}_{\text{parser}}(t)) / \sum \mathcal{T}_{\text{parser}}(t)$.
- Token Recall = $\sum \min(\mathcal{T}_{\text{gold}}(t), \mathcal{T}_{\text{parser}}(t)) / \sum \mathcal{T}_{\text{gold}}(t)$.
- Token F1 = Harmonic mean.

---

## 5. Accounting Consistency Diagnostics

Checks are defined in `gold.json` under `"checks"`:
$$\text{Computed Sum} = \sum_{k} \text{sign}_k \cdot \text{ParsedValue}(\text{AlignedRow}(k))$$
where all addend signs are `+1` because contra printed values are already signed negative (e.g. `△2,979` $\implies -2979.0$).
$$\text{Discrepancy} = |\text{Computed Sum} - \text{ParsedValue}(\text{AlignedTarget})|$$
$$\text{Tolerance} = \max(1, \lceil n / 2 \rceil)$$
- If $\text{Discrepancy} == 0$: `EXACT_MATCH` (PASS)
- If $0 < \text{Discrepancy} \le \text{Tolerance}$: `SOURCE_ROUNDING` (PASS - diagnostic)
- If $\text{Discrepancy} > \text{Tolerance}$: `INCONSISTENCY` (FAIL - diagnostic flag)

Checks are strictly diagnostics and do NOT alter accuracy scores.

---

## 6. CLI Interface

```bash
python3 eval/evaluate.py \
  --gold eval/gold.json \
  --input output.json \
  --format [text|json|markdown] \
  --fail-under-cell 1.0 \
  --fail-under-row 1.0 \
  --fail-under-hierarchy 1.0 \
  --fail-under-numeric-token 1.0
```
