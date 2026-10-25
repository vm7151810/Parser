#!/usr/bin/env python3
"""
Fault-Injection Test Suite for Japanese Table Parser Evaluation Harness.

Tests:
1. Gold vs. Gold (Expect 100% on all metrics and 0 failed accounting checks)
2. Drop a middle row (Verify sequence alignment realigns, flags dropped row and cell recall drop)
3. Duplicate a row (Verify row precision drop and spurious row detection)
4. Swap columns (Verify row match remains 100% but cell accuracy drops drastically)
5. "△0" -> "0" (Verify exact string detection of negative zero marker)
6. "－" -> "0" (Verify nil matches ONLY nil; numeric match fails)
7. "－" -> null (Verify explicit nil converted to null fails cell match)
8. Remove △ from contra value (Verify exact match, numeric match, and accounting check failure)
"""

from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from evaluate import evaluate_table

GOLD_PATH = Path(__file__).resolve().parent / "gold.json"


@pytest.fixture
def gold_data() -> dict:
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_01_gold_vs_gold_self_eval(gold_data):
    """Test 1: Gold compared to itself must achieve 100% on all metrics."""
    report = evaluate_table(gold_data, gold_data)
    s = report["summary"]
    vc = s["cell_metrics"]["value_cells"]
    nvc = s["cell_metrics"]["no_value_cells"]
    d = report["diagnostics"]

    assert s["row_f1"] == 1.0, "Row F1 should be 100%"
    assert s["row_precision"] == 1.0
    assert s["row_recall"] == 1.0
    assert s["hierarchy_accuracy"] == 1.0, "Hierarchy accuracy should be 100%"
    assert vc["exact_accuracy"] == 1.0, f"Value cell exact accuracy: {vc['exact_accuracy']}"
    assert vc["numeric_accuracy"] == 1.0, f"Value cell numeric accuracy: {vc['numeric_accuracy']}"
    assert vc["total"] == 74, "There must be exactly 74 value cells"
    assert nvc["total"] == 12, "There must be exactly 12 no-value cells"
    assert nvc["accuracy"] == 1.0
    assert s["token_f1"] == 1.0
    assert d["failed_checks"] == 0, "All 20 accounting checks must pass"
    print("\n[PASS] Test 1: Gold vs Gold achieved 100% on all metrics.")


def test_02_fault_drop_middle_row(gold_data):
    """Test 2: Drop a middle row (row 8: 仕掛品). Verify realignment and recall drop."""
    perturbed = copy.deepcopy(gold_data)
    # Drop row index 8 (0-indexed 7)
    dropped_row = perturbed["rows"].pop(7)
    assert dropped_row["label"] == "仕掛品"

    report = evaluate_table(gold_data, perturbed)
    s = report["summary"]
    vc = s["cell_metrics"]["value_cells"]
    disc = report["discrepancies"]

    # Gold had 43 rows, parser has 42
    assert s["row_recall"] == 42 / 43, f"Expected recall {42/43:.4f}, got {s['row_recall']:.4f}"
    assert s["row_precision"] == 1.0

    # Unmatched gold rows should list 仕掛品
    unmatched_labels = [r["label"] for r in disc["unmatched_gold_rows"]]
    assert "仕掛品" in unmatched_labels, f"Dropped row not found in unmatched gold: {unmatched_labels}"

    # Value cell recall drops because 2 cells were lost
    assert vc["exact_matches"] == 72
    assert vc["recall"] == 72 / 74

    # Diagnostic check for 流動資産合計 should flag missing addend
    subtotal_check = next(c for c in report["diagnostics"]["details"] if c["check_id"] == "subtotal_current_assets")
    assert subtotal_check["status"] == "MISSING_ADDEND_OR_TARGET"
    print("\n[PASS] Test 2: Dropped middle row '仕掛品' detected; sequence alignment realigned following rows.")


def test_03_fault_duplicate_row(gold_data):
    """Test 3: Duplicate a row (row 5: 売掛金). Verify precision drop and extra row detection."""
    perturbed = copy.deepcopy(gold_data)
    # Duplicate row 5 (0-indexed 4)
    dup_row = copy.deepcopy(perturbed["rows"][4])
    assert dup_row["label"] == "売掛金"
    perturbed["rows"].insert(5, dup_row)

    report = evaluate_table(gold_data, perturbed)
    s = report["summary"]
    disc = report["discrepancies"]

    assert s["row_recall"] == 1.0
    assert s["row_precision"] == 43 / 44
    assert len(disc["unmatched_parser_rows"]) == 1
    assert disc["unmatched_parser_rows"][0]["label"] == "売掛金"
    print("\n[PASS] Test 3: Duplicated row '売掛金' detected; precision penalized appropriately.")


def test_04_fault_swap_columns(gold_data):
    """Test 4: Swap columns (Col 1 <-> Col 2). Row match 100%, cell accuracy drops."""
    perturbed = copy.deepcopy(gold_data)
    for r in perturbed["rows"]:
        vals = r.get("values", [])
        if len(vals) == 2:
            r["values"] = [vals[1], vals[0]]

    report = evaluate_table(gold_data, perturbed)
    s = report["summary"]
    vc = s["cell_metrics"]["value_cells"]

    # Row match is still 100%
    assert s["row_f1"] == 1.0

    # But cell exact accuracy drops drastically
    assert vc["exact_accuracy"] < 0.20, f"Expected major cell drop, got {vc['exact_accuracy']:.2%}"
    assert len(report["discrepancies"]["cell_mismatches"]) > 50
    print(f"\n[PASS] Test 4: Swapped columns detected; cell accuracy plummeted to {vc['exact_accuracy']:.2%}.")


def test_05_fault_negative_zero_marker(gold_data):
    """Test 5: '△0' -> '0' in 貸倒引当金. Exact string mismatch detected."""
    perturbed = copy.deepcopy(gold_data)
    # Row 12 (0-indexed 11) is 貸倒引当金: values = ["△2,979", "△0"]
    assert perturbed["rows"][11]["label"] == "貸倒引当金"
    perturbed["rows"][11]["values"][1] = "0"

    report = evaluate_table(gold_data, perturbed)
    vc = report["summary"]["cell_metrics"]["value_cells"]
    disc = report["discrepancies"]

    assert vc["exact_matches"] == 73  # 73/74
    assert vc["exact_accuracy"] == 73 / 74

    mismatches = [c for c in disc["cell_mismatches"] if c["label"] == "貸倒引当金" and c["column_index"] == 2]
    assert len(mismatches) == 1
    assert mismatches[0]["gold_raw"] == "△0"
    assert mismatches[0]["parser_raw"] == "0"
    print("\n[PASS] Test 5: '△0' -> '0' mutation detected as exact string mismatch.")


def test_06_fault_nil_to_zero(gold_data):
    """Test 6: '－' -> '0' in 建設仮勘定. Nil must only match nil; numeric match fails."""
    perturbed = copy.deepcopy(gold_data)
    # Row 26 (0-indexed 25) is 建設仮勘定: values = ["－", "4,553"]
    assert perturbed["rows"][25]["label"] == "建設仮勘定"
    perturbed["rows"][25]["values"][0] = "0"

    report = evaluate_table(gold_data, perturbed)
    vc = report["summary"]["cell_metrics"]["value_cells"]
    disc = report["discrepancies"]

    # Fails both exact and numeric
    assert vc["exact_matches"] == 73
    assert vc["numeric_matches"] == 73

    mismatches = [c for c in disc["cell_mismatches"] if c["label"] == "建設仮勘定" and c["column_index"] == 1]
    assert len(mismatches) == 1
    assert mismatches[0]["gold_raw"] == "－"
    assert mismatches[0]["parser_raw"] == "0"
    assert not mismatches[0]["numeric_match"]
    print("\n[PASS] Test 6: '－' -> '0' mutation failed both exact and numeric matches (nil only matches nil).")


def test_07_fault_nil_to_null(gold_data):
    """Test 7: '－' -> null in 建設仮勘定. Missing cell value detected."""
    perturbed = copy.deepcopy(gold_data)
    assert perturbed["rows"][25]["label"] == "建設仮勘定"
    perturbed["rows"][25]["values"][0] = None

    report = evaluate_table(gold_data, perturbed)
    vc = report["summary"]["cell_metrics"]["value_cells"]
    disc = report["discrepancies"]

    assert vc["exact_matches"] == 73
    assert vc["numeric_matches"] == 73

    mismatches = [c for c in disc["cell_mismatches"] if c["label"] == "建設仮勘定" and c["column_index"] == 1]
    assert len(mismatches) == 1
    assert mismatches[0]["gold_raw"] == "－"
    assert mismatches[0]["parser_raw"] is None
    print("\n[PASS] Test 7: '－' -> null mutation detected as missing value cell.")


def test_08_fault_remove_delta_contra(gold_data):
    """Test 8: Remove △ from contra row (減価償却累計額: '△1,923,585' -> '1,923,585').
    Fails exact match, numeric match, and triggers accounting inconsistency."""
    perturbed = copy.deepcopy(gold_data)
    # Row 17 (0-indexed 16) is 減価償却累計額 under 建物及び構築物
    assert perturbed["rows"][16]["label"] == "減価償却累計額"
    perturbed["rows"][16]["values"][0] = "1,923,585"

    report = evaluate_table(gold_data, perturbed)
    vc = report["summary"]["cell_metrics"]["value_cells"]
    d = report["diagnostics"]

    # Cell accuracy fails
    assert vc["exact_matches"] == 73
    assert vc["numeric_matches"] == 73

    # Accounting check for net buildings must fail with INCONSISTENCY
    # Gross: 2,121,360 + Contra (+1,923,585) = 4,044,945 != Target 197,775
    net_building_check = next(c for c in d["details"] if c["check_id"] == "net_buildings" and "2025" in c["column"])
    assert not net_building_check["passed"]
    assert net_building_check["status"] == "INCONSISTENCY"
    assert net_building_check["diff"] > 1000000
    print(f"\n[PASS] Test 8: Removed △ from contra detected in cells and flagged in accounting diagnostics (diff={net_building_check['diff']:,.0f}).")


if __name__ == "__main__":
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_01_gold_vs_gold_self_eval(data)
    test_02_fault_drop_middle_row(data)
    test_03_fault_duplicate_row(data)
    test_04_fault_swap_columns(data)
    test_05_fault_negative_zero_marker(data)
    test_06_fault_nil_to_zero(data)
    test_07_fault_nil_to_null(data)
    test_08_fault_remove_delta_contra(data)
    print("\n" + "=" * 60)
    print("ALL 8 FAULT-INJECTION AND SELF-EVALUATION TESTS PASSED!")
    print("=" * 60)
