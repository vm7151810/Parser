# 連結貸借対照表 (訂正後)

- **Source File**: `balance_sheet.pdf` (Page 1)
- **Unit (単位)**: `千円`
- **Columns Detected**: 2
- **Hierarchy Levels Detected**: 5
- **Token Coverage Ratio**: `1.0` (74 / 74 tokens)

## Financial Statement Table

| 項目 (Line Item) | 前連結会計年度<br><sub>(2025-03-31)</sub> | 当連結会計年度<br><sub>(2026-03-31)</sub> | Row Type | Flags |
| --- | :---: | :---: | :---: | :---: |
| **資産の部** | *missing* ⚑ | *missing* ⚑ | `section` | — |
| &nbsp;&nbsp;*流動資産* | *missing* ⚑ | *missing* ⚑ | `header` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;現金及び預金 | 2,002,429 | 608,281 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;受取手形 | 20,659 | 26,333 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;売掛金 | 2,019,476 | 884,339 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;電子記録債権 | 564,667 | 370,468 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;商品及び製品 | 589,488 | 1,019,663 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;仕掛品 | 186,748 | 55,344 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;原材料及び貯蔵品 | 370,403 | 136,082 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;短期貸付金 | 7,530 | 30,000 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;その他 | 105,260 | 246,895 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;貸倒引当金 | △2,979 | △0 ⚑ | `contra_standalone` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;**流動資産合計** | 5,863,684 | 3,377,407 | `subtotal` | — |
| &nbsp;&nbsp;*固定資産* | *missing* ⚑ | *missing* ⚑ | `header` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;*有形固定資産* | *missing* ⚑ | *missing* ⚑ | `header` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*建物及び構築物* | 2,121,360 | 1,880,082 | `gross` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;減価償却累計額 | △1,923,585 | △1,640,253 | `contra` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;建物及び構築物(純額) | 197,775 | 239,828 | `net` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*機械装置及び運搬具* | 4,024,922 | 2,250,799 | `gross` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;減価償却累計額 | △3,634,165 | △1,914,091 | `contra` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;機械装置及び運搬具(純額) | 390,757 | 336,708 | `net` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;土地 | 768,976 | 705,403 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*リース資産* | 210,746 | 213,939 | `gross` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;減価償却累計額 | △147,599 | △172,066 | `contra` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;リース資産(純額) | 63,146 | 41,872 | `net` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;建設仮勘定 | － | 4,553 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*その他* | 848,814 | 446,126 | `gross` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;減価償却累計額 | △840,375 | △421,883 | `contra` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;その他(純額) | 8,439 | 24,243 | `net` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**有形固定資産合計** | 1,429,094 | 1,352,610 | `subtotal` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;*無形固定資産* | *missing* ⚑ | *missing* ⚑ | `header` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;リース資産 | 34,190 | 21,402 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;その他 | 10,070 | 14,466 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**無形固定資産合計** | 44,261 | 35,869 | `subtotal` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;*投資その他の資産* | *missing* ⚑ | *missing* ⚑ | `header` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;投資有価証券 | 44,180 | 218,836 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;関係会社株式 | 1,123 | 1,123 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;長期貸付金 | － | 62,000 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;退職給付に係る資産 | 18,404 | 16,435 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;その他 | 133,361 | 70,967 | `item` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**投資その他の資産合計** | 197,069 | 369,362 | `subtotal` | — |
| &nbsp;&nbsp;&nbsp;&nbsp;**固定資産合計** | 1,670,426 | 1,757,841 | `subtotal` | — |
| &nbsp;&nbsp;**資産合計** | 7,534,110 | 5,135,249 | `subtotal` | — |

## Accounting Consistency Checks

| Check ID | Type | Period | Computed | Stated | Diff | Tol | Status | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `net_check_block_その他_26_前連結会計年度` | net_value | 前連結会計年度 | 8,439 | 8,439 | 0 | ±1 | ✅ PASS (`exact`) | Gross (その他) + Contra (減価償却累計額) vs Net (その他(純額)) |
| `net_check_block_その他_26_当連結会計年度` | net_value | 当連結会計年度 | 24,243 | 24,243 | 0 | ±1 | ✅ PASS (`exact`) | Gross (その他) + Contra (減価償却累計額) vs Net (その他(純額)) |
| `net_check_block_リース資産_22_前連結会計年度` | net_value | 前連結会計年度 | 63,147 | 63,146 | 1 | ±1 | ✅ PASS (`source_rounding`) | Gross (リース資産) + Contra (減価償却累計額) vs Net (リース資産(純額)) |
| `net_check_block_リース資産_22_当連結会計年度` | net_value | 当連結会計年度 | 41,873 | 41,872 | 1 | ±1 | ✅ PASS (`source_rounding`) | Gross (リース資産) + Contra (減価償却累計額) vs Net (リース資産(純額)) |
| `net_check_block_建物及び構築物_15_前連結会計年度` | net_value | 前連結会計年度 | 197,775 | 197,775 | 0 | ±1 | ✅ PASS (`exact`) | Gross (建物及び構築物) + Contra (減価償却累計額) vs Net (建物及び構築物(純額)) |
| `net_check_block_建物及び構築物_15_当連結会計年度` | net_value | 当連結会計年度 | 239,829 | 239,828 | 1 | ±1 | ✅ PASS (`source_rounding`) | Gross (建物及び構築物) + Contra (減価償却累計額) vs Net (建物及び構築物(純額)) |
| `net_check_block_機械装置及び運搬具_18_前連結会計年度` | net_value | 前連結会計年度 | 390,757 | 390,757 | 0 | ±1 | ✅ PASS (`exact`) | Gross (機械装置及び運搬具) + Contra (減価償却累計額) vs Net (機械装置及び運搬具(純額)) |
| `net_check_block_機械装置及び運搬具_18_当連結会計年度` | net_value | 当連結会計年度 | 336,708 | 336,708 | 0 | ±1 | ✅ PASS (`exact`) | Gross (機械装置及び運搬具) + Contra (減価償却累計額) vs Net (機械装置及び運搬具(純額)) |
| `subtotal_流動資産合計_前連結会計年度` | subtotal | 前連結会計年度 | 5,863,681 | 5,863,684 | 3 | ±5 | ✅ PASS (`source_rounding`) | Sum of 10 items feeding 流動資産合計 |
| `subtotal_流動資産合計_当連結会計年度` | subtotal | 当連結会計年度 | 3,377,405 | 3,377,407 | 2 | ±5 | ✅ PASS (`source_rounding`) | Sum of 10 items feeding 流動資産合計 |
| `subtotal_有形固定資産合計_前連結会計年度` | subtotal | 前連結会計年度 | 1,429,093 | 1,429,094 | 1 | ±3 | ✅ PASS (`source_rounding`) | Sum of 6 items feeding 有形固定資産合計 |
| `subtotal_有形固定資産合計_当連結会計年度` | subtotal | 当連結会計年度 | 1,352,607 | 1,352,610 | 3 | ±3 | ✅ PASS (`source_rounding`) | Sum of 6 items feeding 有形固定資産合計 |
| `subtotal_無形固定資産合計_前連結会計年度` | subtotal | 前連結会計年度 | 44,260 | 44,261 | 1 | ±1 | ✅ PASS (`source_rounding`) | Sum of 2 items feeding 無形固定資産合計 |
| `subtotal_無形固定資産合計_当連結会計年度` | subtotal | 当連結会計年度 | 35,868 | 35,869 | 1 | ±1 | ✅ PASS (`source_rounding`) | Sum of 2 items feeding 無形固定資産合計 |
| `subtotal_投資その他の資産合計_前連結会計年度` | subtotal | 前連結会計年度 | 197,068 | 197,069 | 1 | ±3 | ✅ PASS (`source_rounding`) | Sum of 5 items feeding 投資その他の資産合計 |
| `subtotal_投資その他の資産合計_当連結会計年度` | subtotal | 当連結会計年度 | 369,361 | 369,362 | 1 | ±3 | ✅ PASS (`source_rounding`) | Sum of 5 items feeding 投資その他の資産合計 |
| `subtotal_固定資産合計_前連結会計年度` | subtotal | 前連結会計年度 | 1,670,424 | 1,670,426 | 2 | ±2 | ✅ PASS (`source_rounding`) | Sum of 3 items feeding 固定資産合計 |
| `subtotal_固定資産合計_当連結会計年度` | subtotal | 当連結会計年度 | 1,757,841 | 1,757,841 | 0 | ±2 | ✅ PASS (`exact`) | Sum of 3 items feeding 固定資産合計 |
| `grand_total_資産合計_前連結会計年度` | grand_total | 前連結会計年度 | 7,534,110 | 7,534,110 | 0 | ±1 | ✅ PASS (`exact`) | Sum of 2 items feeding 資産合計 |
| `grand_total_資産合計_当連結会計年度` | grand_total | 当連結会計年度 | 5,135,248 | 5,135,249 | 1 | ±1 | ✅ PASS (`source_rounding`) | Sum of 2 items feeding 資産合計 |

## Audit & Quality Assurance

- **Independent Audit Discrepancies**: 0 unassigned, 0 phantom.
- **Notes**: `⚑` marks cells with uncertainty, missing values, or negative zero flags.
