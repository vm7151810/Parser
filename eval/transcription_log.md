# Two-Pass Independent Transcription & Verification Log

**Target Document**: `balance_sheet.pdf` (Page 1 / Document Page 4)  
**Transcription Method**: Visual human inspection directly from rendered 200 DPI page image.  
**Parser Reference**: None. Zero parser source code, output files, or text extractors were consulted.  
**Status**: `pending_human_verification`  

---

## 1. Page Metadata Transcription

| Attribute | Pass 1 Reading | Pass 2 Reading | Reconciled Gold |
|---|---|---|---|
| **Title / Subtitle** | （訂正後）<br>３．連結財務諸表及び主な注記<br>（１）連結貸借対照表 | （訂正後）<br>３．連結財務諸表及び主な注記<br>（１）連結貸借対照表 | Title: `連結貸借対照表`<br>Subtitle: `３．連結財務諸表及び主な注記 （１）連結貸借対照表`<br>Note: `（訂正後）` |
| **Unit (単位)** | （単位：千円） | （単位：千円） | `千円` |
| **Page Number** | - 4 - | - 4 - | `4` |
| **Column 1 Header** | 前連結会計年度<br>(2025年３月31日) | 前連結会計年度<br>(2025年３月31日) | `前連結会計年度 (2025年３月31日)` |
| **Column 2 Header** | 当連結会計年度<br>(2026年３月31日) | 当連結会計年度<br>(2026年３月31日) | `当連結会計年度 (2026年３月31日)` |

---

## 2. Row-by-Row Transcription & Independent Pass Diff

Both passes were conducted independently:
- **Pass 1**: Top-to-bottom reading focusing on label orthography, visual indentation hierarchy, and column alignments.
- **Pass 2**: Bottom-to-top reading verifying digit sequences, comma placements, negative indicators (`△`), nil dashes (`－`), and subtotal boundaries.

### Comparison Table

| Row | Pass 1 Label | Pass 1 Parent (Label [Idx]) | Pass 1 Col 1 | Pass 1 Col 2 | Pass 2 Label | Pass 2 Parent (Label [Idx]) | Pass 2 Col 1 | Pass 2 Col 2 | Diff / Disagreement | Reconciled Status |
|:---:|---|---|:---:|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | 資産の部 | *None* | *None* | *None* | 資産の部 | *None* | *None* | *None* | None | Match |
| 2 | 流動資産 | 資産の部 [1] | *None* | *None* | 流動資産 | 資産の部 [1] | *None* | *None* | None | Match |
| 3 | 現金及び預金 | 流動資産 [2] | 2,002,429 | 608,281 | 現金及び預金 | 流動資産 [2] | 2,002,429 | 608,281 | None | Match |
| 4 | 受取手形 | 流動資産 [2] | 20,659 | 26,333 | 受取手形 | 流動資産 [2] | 20,659 | 26,333 | None | Match |
| 5 | 売掛金 | 流動資産 [2] | 2,019,476 | 884,339 | 売掛金 | 流動資産 [2] | 2,019,476 | 884,339 | None | Match |
| 6 | 電子記録債権 | 流動資産 [2] | 564,667 | 370,468 | 電子記録債権 | 流動資産 [2] | 564,667 | 370,468 | None | Match |
| 7 | 商品及び製品 | 流動資産 [2] | 589,488 | 1,019,663 | 商品及び製品 | 流動資産 [2] | 589,488 | 1,019,663 | None | Match |
| 8 | 仕掛品 | 流動資産 [2] | 186,748 | 55,344 | 仕掛品 | 流動資産 [2] | 186,748 | 55,344 | None | Match |
| 9 | 原材料及び貯蔵品 | 流動資産 [2] | 370,403 | 136,082 | 原材料及び貯蔵品 | 流動資産 [2] | 370,403 | 136,082 | None | Match |
| 10 | 短期貸付金 | 流動資産 [2] | 7,530 | 30,000 | 短期貸付金 | 流動資産 [2] | 7,530 | 30,000 | None | Match |
| 11 | その他 | 流動資産 [2] | 105,260 | 246,895 | その他 | 流動資産 [2] | 105,260 | 246,895 | None | Match |
| 12 | 貸倒引当金 | 流動資産 [2] | △2,979 | △0 | 貸倒引当金 | 流動資産 [2] | △2,979 | △0 | None | Match (See Note 1) |
| 13 | 流動資産合計 | 流動資産 [2] | 5,863,684 | 3,377,407 | 流動資産合計 | 流動資産 [2] | 5,863,684 | 3,377,407 | None | Match (See Note 2) |
| 14 | 固定資産 | 資産の部 [1] | *None* | *None* | 固定資産 | 資産の部 [1] | *None* | *None* | None | Match |
| 15 | 有形固定資産 | 固定資産 [14] | *None* | *None* | 有形固定資産 | 固定資産 [14] | *None* | *None* | None | Match |
| 16 | 建物及び構築物 | 有形固定資産 [15] | 2,121,360 | 1,880,082 | 建物及び構築物 | 有形固定資産 [15] | 2,121,360 | 1,880,082 | None | Match |
| 17 | 減価償却累計額 | 建物及び構築物 [16] | △1,923,585 | △1,640,253 | 減価償却累計額 | 建物及び構築物 [16] | △1,923,585 | △1,640,253 | None | Match |
| 18 | 建物及び構築物（純額） | 建物及び構築物 [16] | 197,775 | 239,828 | 建物及び構築物（純額） | 建物及び構築物 [16] | 197,775 | 239,828 | None | Match (See Note 2) |
| 19 | 機械装置及び運搬具 | 有形固定資産 [15] | 4,024,922 | 2,250,799 | 機械装置及び運搬具 | 有形固定資産 [15] | 4,024,922 | 2,250,799 | None | Match |
| 20 | 減価償却累計額 | 機械装置及び運搬具 [19] | △3,634,165 | △1,914,091 | 減価償却累計額 | 機械装置及び運搬具 [19] | △3,634,165 | △1,914,091 | None | Match |
| 21 | 機械装置及び運搬具（純額） | 機械装置及び運搬具 [19] | 390,757 | 336,708 | 機械装置及び運搬具（純額） | 機械装置及び運搬具 [19] | 390,757 | 336,708 | None | Match (See Note 2) |
| 22 | 土地 | 有形固定資産 [15] | 768,976 | 705,403 | 土地 | 有形固定資産 [15] | 768,976 | 705,403 | None | Match |
| 23 | リース資産 | 有形固定資産 [15] | 210,746 | 213,939 | リース資産 | 有形固定資産 [15] | 210,746 | 213,939 | None | Match |
| 24 | 減価償却累計額 | リース資産 [23] | △147,599 | △172,066 | 減価償却累計額 | リース資産 [23] | △147,599 | △172,066 | None | Match |
| 25 | リース資産（純額） | リース資産 [23] | 63,146 | 41,872 | リース資産（純額） | リース資産 [23] | 63,146 | 41,872 | None | Match (See Note 2) |
| 26 | 建設仮勘定 | 有形固定資産 [15] | － | 4,553 | 建設仮勘定 | 有形固定資産 [15] | － | 4,553 | None | Match (See Note 3) |
| 27 | その他 | 有形固定資産 [15] | 848,814 | 446,126 | その他 | 有形固定資産 [15] | 848,814 | 446,126 | None | Match |
| 28 | 減価償却累計額 | その他 [27] | △840,375 | △421,883 | 減価償却累計額 | その他 [27] | △840,375 | △421,883 | None | Match |
| 29 | その他（純額） | その他 [27] | 8,439 | 24,243 | その他（純額） | その他 [27] | 8,439 | 24,243 | None | Match (See Note 2) |
| 30 | 有形固定資産合計 | 有形固定資産 [15] | 1,429,094 | 1,352,610 | 有形固定資産合計 | 有形固定資産 [15] | 1,429,094 | 1,352,610 | None | Match |
| 31 | 無形固定資産 | 固定資産 [14] | *None* | *None* | 無形固定資産 | 固定資産 [14] | *None* | *None* | None | Match |
| 32 | リース資産 | 無形固定資産 [31] | 34,190 | 21,402 | リース資産 | 無形固定資産 [31] | 34,190 | 21,402 | None | Match |
| 33 | その他 | 無形固定資産 [31] | 10,070 | 14,466 | その他 | 無形固定資産 [31] | 10,070 | 14,466 | None | Match |
| 34 | 無形固定資産合計 | 無形固定資産 [31] | 44,261 | 35,869 | 無形固定資産合計 | 無形固定資産 [31] | 44,261 | 35,869 | None | Match |
| 35 | 投資その他の資産 | 固定資産 [14] | *None* | *None* | 投資その他の資産 | 固定資産 [14] | *None* | *None* | None | Match |
| 36 | 投資有価証券 | 投資その他の資産 [35] | 44,180 | 218,836 | 投資有価証券 | 投資その他の資産 [35] | 44,180 | 218,836 | None | Match |
| 37 | 関係会社株式 | 投資その他の資産 [35] | 1,123 | 1,123 | 関係会社株式 | 投資その他の資産 [35] | 1,123 | 1,123 | None | Match |
| 38 | 長期貸付金 | 投資その他の資産 [35] | － | 62,000 | 長期貸付金 | 投資その他の資産 [35] | － | 62,000 | None | Match (See Note 3) |
| 39 | 退職給付に係る資産 | 投資その他の資産 [35] | 18,404 | 16,435 | 退職給付に係る資産 | 投資その他の資産 [35] | 18,404 | 16,435 | None | Match |
| 40 | その他 | 投資その他の資産 [35] | 133,361 | 70,967 | その他 | 投資その他の資産 [35] | 133,361 | 70,967 | None | Match |
| 41 | 投資その他の資産合計 | 投資その他の資産 [35] | 197,069 | 369,362 | 投資その他の資産合計 | 投資その他の資産 [35] | 197,069 | 369,362 | None | Match |
| 42 | 固定資産合計 | 固定資産 [14] | 1,670,426 | 1,757,841 | 固定資産合計 | 固定資産 [14] | 1,670,426 | 1,757,841 | None | Match |
| 43 | 資産合計 | 資産の部 [1] | 7,534,110 | 5,135,249 | 資産合計 | 資産の部 [1] | 7,534,110 | 5,135,249 | None | Match |

---

## 3. Ambiguity & Uncertain Cells Analysis

### Note 1: Row 12 `貸倒引当金` Column 2 (`△0`)
- **Visual Appearance**: Printed clearly as the triangle character `△` followed immediately by `0`.
- **Accounting Meaning**: In Japanese accounting, when an allowance has a non-zero fractional amount rounded to zero thousand yen or has an active provision balance that rounds down to 0, it is explicitly rendered as `△0` to signify a negative / deduction item rather than nil (`－`) or positive zero.
- **Transcribed String**: `"△0"`.
- **Gold Status**: Listed in `uncertain_cells` for human verification to ensure downstream consumers note the negative-zero distinction.

### Note 2: Visual Indentation Hierarchy & Parent Assignment
- **Human-Verified Indented Tree**:
  - The hierarchy was explicitly verified from the rendered page image via an indented text tree (`eval/hierarchy_tree.txt`).
  - **Visual Indentation Rule**: A row's parent is the nearest preceding row with a smaller indent.
  - **Net-Value Rows (`（純額）`)**:
    Visual reading confirms that the four `（純額）` rows (rows 18, 21, 25, 29) are indented under their respective gross rows (`建物及び構築物`, `機械装置及び運搬具`, `リース資産`, `その他`), at the exact same indent as their `減価償却累計額` contra rows.
    Therefore, their parents are their gross parent rows:
    - Row 18: `建物及び構築物（純額）` $\rightarrow$ parent `建物及び構築物` (Row 16, `parent_index: 16`)
    - Row 21: `機械装置及び運搬具（純額）` $\rightarrow$ parent `機械装置及び運搬具` (Row 19, `parent_index: 19`)
    - Row 25: `リース資産（純額）` $\rightarrow$ parent `リース資産` (Row 23, `parent_index: 23`)
    - Row 29: `その他（純額）` $\rightarrow$ parent `その他` (Row 27, `parent_index: 27`)
  - **Subtotal Rows (`…合計`)**:
    Subtotal rows sit at the same indent as the items they total. Semantically and visually, they close their respective section. Therefore, the parent of each subtotal row is the section it closes:
    - Row 13: `流動資産合計` $\rightarrow$ parent `流動資産` (Row 2, `parent_index: 2`)
    - Row 30: `有形固定資産合計` $\rightarrow$ parent `有形固定資産` (Row 15, `parent_index: 15`)
    - Row 34: `無形固定資産合計` $\rightarrow$ parent `無形固定資産` (Row 31, `parent_index: 31`)
    - Row 41: `投資その他の資産合計` $\rightarrow$ parent `投資その他の資産` (Row 35, `parent_index: 35`)
    - Row 42: `固定資産合計` $\rightarrow$ parent `固定資産` (Row 14, `parent_index: 14`)
    - Row 43: `資産合計` $\rightarrow$ parent `資産の部` (Row 1, `parent_index: 1`)

### Note 3: Printed Nil Dash (`－`) vs `null`
- **Rows 26 and 38 Column 1**: Printed as a full-width em-dash/horizontal bar `－` (Unicode `U+FF0D`).
- **Semantic Meaning**: This signifies an explicit nil/zero balance for that period.
- **Representation**: Stored as exact printed string `"－"`.
- **Contrast with Category Rows**: Rows 1, 2, 14, 15, 31, 35 have no printed value cells at all (empty space). They are stored as `null`.

---

## 4. Diagnostic Accounting Reconciliation & Rounding Rationale

> [!IMPORTANT]
> **Cardinal Rule**: Printed values are **NEVER altered** to force an accounting sum to balance.
> Accounting checks are strictly diagnostics to audit transcription integrity and assess parser extraction quality.

### Rounding Tolerance Rationale
Financial filing figures published in thousands of yen (千円) are rounded/truncated from exact yen amounts in the source reporting system. When $n$ independently rounded numbers are summed:
$$\text{Expected Max Drift} = \lceil n / 2 \rceil \text{ thousand yen}$$
Differences within $\lceil n / 2 \rceil$ are classified as standard `source_rounding`.

### Diagnostic Calculations

#### 1. Net-Value Checks (Gross - Contra = Net)
Tolerance: $n=2 \implies \lceil 2/2 \rceil = \pm 1$ thousand yen.

1. **建物及び構築物（純額）** (Row 18 = Row 16 - Row 17):
   - 前期: $2,121,360 - 1,923,585 = 197,775$. Printed: $197,775$. **Diff: 0 (Exact)**
   - 当期: $1,880,082 - 1,640,253 = 239,829$. Printed: $239,828$. **Diff: -1 (Within Tol $\pm 1$)**
2. **機械装置及び運搬具（純額）** (Row 21 = Row 19 - Row 20):
   - 前期: $4,024,922 - 3,634,165 = 390,757$. Printed: $390,757$. **Diff: 0 (Exact)**
   - 当期: $2,250,799 - 1,914,091 = 336,708$. Printed: $336,708$. **Diff: 0 (Exact)**
3. **リース資産（純額）** (Row 25 = Row 23 - Row 24):
   - 前期: $210,746 - 147,599 = 63,147$. Printed: $63,146$. **Diff: -1 (Within Tol $\pm 1$)**
   - 当期: $213,939 - 172,066 = 41,873$. Printed: $41,872$. **Diff: -1 (Within Tol $\pm 1$)**
4. **その他（純額）** (Row 29 = Row 27 - Row 28):
   - 前期: $848,814 - 840,375 = 8,439$. Printed: $8,439$. **Diff: 0 (Exact)**
   - 当期: $446,126 - 421,883 = 24,243$. Printed: $24,243$. **Diff: 0 (Exact)**

#### 2. Section Subtotal Checks
1. **流動資産合計** (Row 13 = Sum of Rows 3..11 minus Row 12, $n=10$, Tol: $\pm 5$):
   - 前期: $2,002,429 + 20,659 + 2,019,476 + 564,667 + 589,488 + 186,748 + 370,403 + 7,530 + 105,260 - 2,979 = 5,863,681$.  
     Printed: $5,863,684$. **Diff: +3 (Within Tol $\pm 5$)**
   - 当期: $608,281 + 26,333 + 884,339 + 370,468 + 1,019,663 + 55,344 + 136,082 + 30,000 + 246,895 - 0 = 3,377,405$.  
     Printed: $3,377,407$. **Diff: +2 (Within Tol $\pm 5$)**
2. **有形固定資産合計** (Row 30 = Net Rows 18, 21, 22, 25, 26, 29, $n=6$, Tol: $\pm 3$):
   - 前期: $197,775 + 390,757 + 768,976 + 63,146 + 0 + 8,439 = 1,429,093$.  
     Printed: $1,429,094$. **Diff: +1 (Within Tol $\pm 3$)**
   - 当期: $239,828 + 336,708 + 705,403 + 41,872 + 4,553 + 24,243 = 1,352,607$.  
     Printed: $1,352,610$. **Diff: +3 (Within Tol $\pm 3$)**
3. **無形固定資産合計** (Row 34 = Sum of Rows 32, 33, $n=2$, Tol: $\pm 1$):
   - 前期: $34,190 + 10,070 = 44,260$. Printed: $44,261$. **Diff: +1 (Within Tol $\pm 1$)**
   - 当期: $21,402 + 14,466 = 35,868$. Printed: $35,869$. **Diff: +1 (Within Tol $\pm 1$)**
4. **投資その他の資産合計** (Row 41 = Sum of Rows 36, 37, 38, 39, 40, $n=5$, Tol: $\pm 3$):
   - 前期: $44,180 + 1,123 + 0 + 18,404 + 133,361 = 197,068$. Printed: $197,069$. **Diff: +1 (Within Tol $\pm 3$)**
   - 当期: $218,836 + 1,123 + 62,000 + 16,435 + 70,967 = 369,361$. Printed: $369,362$. **Diff: +1 (Within Tol $\pm 3$)**

#### 3. Composite & Grand Total Checks
1. **固定資産合計** (Row 42 = Rows 30 + 34 + 41, $n=3$, Tol: $\pm 2$):
   - 前期: $1,429,094 + 44,261 + 197,069 = 1,670,424$. Printed: $1,670,426$. **Diff: +2 (Within Tol $\pm 2$)**
   - 当期: $1,352,610 + 35,869 + 369,362 = 1,757,841$. Printed: $1,757,841$. **Diff: 0 (Exact)**
2. **資産合計** (Row 43 = Row 13 + Row 42, $n=2$, Tol: $\pm 1$):
   - 前期: $5,863,684 + 1,670,426 = 7,534,110$. Printed: $7,534,110$. **Diff: 0 (Exact)**
   - 当期: $3,377,407 + 1,757,841 = 5,135,248$. Printed: $5,135,249$. **Diff: +1 (Within Tol $\pm 1$)**

**Reconciliation Conclusion**: All 20 accounting checks pass comfortably within source-rounding tolerance $\lceil n/2 \rceil$. Zero manual adjustments were made to transcribed figures.
